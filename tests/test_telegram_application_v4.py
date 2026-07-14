import importlib

import pytest

from engine.quota_slot_engine_v4 import QuotaSlotRejected
from engine.telegram_application_v4 import (
    TelegramApplicationV4,
    TelegramCommandRequest,
    map_telegram_user_to_subject_id,
)


TRUNCATION_MARKER = "\n[truncated]"
SAFE_MAX_RESPONSE_CHARS = 160


class _ReleaseFailure(Exception):
    pass


def _request(command, *, telegram_user_id=123456, arguments=()):
    return TelegramCommandRequest(
        command=command,
        telegram_user_id=telegram_user_id,
        chat_id=-100987654321,
        arguments=arguments,
    )


def _application(tmp_path, quota_slot_worker, *, worker=None, **overrides):
    if worker is None:
        worker = lambda *, state_path: {"state_path": state_path}

    config = {
        "window_id_provider": lambda request: "2026-W29",
        "quota_limit": 3,
        "slot_capacity": 2,
        "quota_state_path": tmp_path / "quota-state.json",
        "worker_state_path": tmp_path / "worker-state.json",
        "quota_now_provider": lambda: "2026-07-14T12:00:00",
        "reservation_id_provider": lambda: "reservation-001",
        "quota_slot_worker": quota_slot_worker,
        "worker": worker,
        "max_response_chars": SAFE_MAX_RESPONSE_CHARS,
    }
    config.update(overrides)
    return TelegramApplicationV4(**config)


def _assert_safe_response(response, *, category, command):
    assert response.category == category
    assert response.command == command
    assert isinstance(response.message, str)
    assert response.message
    assert "Traceback" not in response.message
    assert "sk-live-secret" not in response.message
    assert "/private/secret" not in response.message


def test_maps_immutable_telegram_user_id_to_namespaced_subject_only():
    assert map_telegram_user_to_subject_id(123456) == "telegram:user:123456"


@pytest.mark.parametrize("telegram_user_id", [None, "123456", True, 0, -1])
def test_rejects_invalid_telegram_user_ids(telegram_user_id):
    with pytest.raises(ValueError):
        map_telegram_user_to_subject_id(telegram_user_id)


def test_start_and_help_are_informational_and_do_not_invoke_worker(tmp_path):
    worker_calls = []

    def worker(**kwargs):
        worker_calls.append(kwargs)
        raise AssertionError("informational commands must not call worker")

    application = _application(tmp_path, worker)

    start = application.dispatch(_request("/start"))
    help_response = application.dispatch(_request("/help"))

    _assert_safe_response(start, category="INFO", command="/start")
    _assert_safe_response(help_response, category="INFO", command="/help")
    for command in ("/start", "/help", "/status", "/scan"):
        assert command in help_response.message
    assert "/unknown" not in help_response.message
    assert worker_calls == []
    assert list(tmp_path.iterdir()) == []


def test_status_is_non_mutating_and_reports_only_safe_readiness(tmp_path):
    worker_calls = []

    def worker(**kwargs):
        worker_calls.append(kwargs)
        raise AssertionError("status must not call worker")

    application = _application(tmp_path, worker)

    response = application.dispatch(_request("/status"))

    _assert_safe_response(response, category="STATUS", command="/status")
    assert "quota-state.json" not in response.message
    assert "worker-state.json" not in response.message
    assert worker_calls == []
    assert list(tmp_path.iterdir()) == []


def test_unknown_or_malformed_commands_are_rejected_without_worker_call(tmp_path):
    worker_calls = []

    def worker(**kwargs):
        worker_calls.append(kwargs)

    application = _application(tmp_path, worker)

    unknown = application.dispatch(_request("/unknown"))
    malformed = application.dispatch(_request("", telegram_user_id=123456))

    _assert_safe_response(unknown, category="INVALID_INPUT", command="/unknown")
    _assert_safe_response(malformed, category="INVALID_INPUT", command="")
    assert worker_calls == []


def test_scan_forwards_resolved_policy_to_canonical_worker_once(tmp_path):
    wrapper_calls = []
    underlying_worker_calls = []
    quota_now_provider = lambda: "2026-07-14T12:00:00"
    reservation_id_provider = lambda: "reservation-001"

    def underlying_worker(*, state_path):
        underlying_worker_calls.append(state_path)
        return {"score": 99}

    def quota_slot_worker(**kwargs):
        wrapper_calls.append(kwargs)
        worker_result = kwargs["worker"](
            state_path=kwargs["worker_state_path"]
        )
        return {
            "admission": {"reservation_id": "reservation-001"},
            "worker_result": worker_result,
            "release": {"released": True},
        }

    application = _application(
        tmp_path,
        quota_slot_worker,
        worker=underlying_worker,
        quota_now_provider=quota_now_provider,
        reservation_id_provider=reservation_id_provider,
    )

    response = application.dispatch(_request("/scan"))

    _assert_safe_response(response, category="SCAN_SUCCESS", command="/scan")
    assert len(wrapper_calls) == 1
    forwarded = wrapper_calls[0]
    assert set(forwarded) == {
        "subject_id",
        "window_id",
        "quota_limit",
        "slot_capacity",
        "quota_state_path",
        "worker_state_path",
        "quota_now_provider",
        "reservation_id_provider",
        "worker",
    }
    assert forwarded | {"worker": None} == {
        "subject_id": "telegram:user:123456",
        "window_id": "2026-W29",
        "quota_limit": 3,
        "slot_capacity": 2,
        "quota_state_path": tmp_path / "quota-state.json",
        "worker_state_path": tmp_path / "worker-state.json",
        "quota_now_provider": quota_now_provider,
        "reservation_id_provider": reservation_id_provider,
        "worker": None,
    }
    assert forwarded["worker"] is not underlying_worker
    assert underlying_worker_calls == [tmp_path / "worker-state.json"]


def test_scan_maps_phase_04_rejections_before_failure_classification(tmp_path):
    wrapper_calls = []

    def quota_slot_worker(**kwargs):
        wrapper_calls.append(kwargs)
        raise QuotaSlotRejected("QUOTA_EXHAUSTED", "sk-live-secret")

    response = _application(tmp_path, quota_slot_worker).dispatch(
        _request("/scan")
    )

    _assert_safe_response(response, category="QUOTA_EXHAUSTED", command="/scan")
    assert len(wrapper_calls) == 1


@pytest.mark.parametrize(
    ("reason_code", "category"),
    [
        ("SLOTS_FULL", "SLOTS_FULL"),
        ("STATE_CORRUPT", "STATE_UNAVAILABLE"),
        ("INVALID_POLICY", "ADMISSION_REJECTED"),
        ("INVALID_REQUEST", "ADMISSION_REJECTED"),
    ],
)
def test_scan_maps_other_phase_04_rejections_without_retry(
    tmp_path, reason_code, category
):
    wrapper_calls = []

    def quota_slot_worker(**kwargs):
        wrapper_calls.append(kwargs)
        raise QuotaSlotRejected(reason_code, "sk-live-secret")

    response = _application(tmp_path, quota_slot_worker).dispatch(
        _request("/scan")
    )

    _assert_safe_response(response, category=category, command="/scan")
    assert len(wrapper_calls) == 1


def test_worker_failure_uses_decorated_worker_marker_without_retry(tmp_path):
    wrapper_calls = []
    underlying_worker_calls = []

    def underlying_worker(*, state_path):
        underlying_worker_calls.append(state_path)
        raise RuntimeError("worker failed: sk-live-secret /private/secret")

    def quota_slot_worker(**kwargs):
        wrapper_calls.append(kwargs)
        return kwargs["worker"](state_path=kwargs["worker_state_path"])

    response = _application(
        tmp_path,
        quota_slot_worker,
        worker=underlying_worker,
    ).dispatch(_request("/scan"))

    _assert_safe_response(response, category="WORKER_FAILED", command="/scan")
    assert len(wrapper_calls) == 1
    assert underlying_worker_calls == [tmp_path / "worker-state.json"]


def test_release_failure_after_decorated_worker_success_is_not_retried(tmp_path):
    wrapper_calls = []
    underlying_worker_calls = []
    release_error = _ReleaseFailure("release failed: sk-live-secret")

    def underlying_worker(*, state_path):
        underlying_worker_calls.append(state_path)
        return "worker-completed"

    def quota_slot_worker(**kwargs):
        wrapper_calls.append(kwargs)
        kwargs["worker"](state_path=kwargs["worker_state_path"])
        raise release_error

    response = _application(
        tmp_path,
        quota_slot_worker,
        worker=underlying_worker,
    ).dispatch(_request("/scan"))

    _assert_safe_response(response, category="RELEASE_FAILED", command="/scan")
    assert len(wrapper_calls) == 1
    assert underlying_worker_calls == [tmp_path / "worker-state.json"]


def test_dual_failure_preserves_marker_primary_and_release_as_cause(tmp_path):
    wrapper_calls = []
    underlying_worker_calls = []
    marker_observations = []
    release_error = _ReleaseFailure("release failed: sk-live-secret")

    def underlying_worker(*, state_path):
        underlying_worker_calls.append(state_path)
        raise RuntimeError("worker failed: sk-live-secret /private/secret")

    def quota_slot_worker(**kwargs):
        wrapper_calls.append(kwargs)
        try:
            kwargs["worker"](state_path=kwargs["worker_state_path"])
        except BaseException as marker:
            marker_observations.append(marker)
            raise marker from release_error

    response = _application(
        tmp_path,
        quota_slot_worker,
        worker=underlying_worker,
    ).dispatch(_request("/scan"))

    _assert_safe_response(
        response,
        category="WORKER_AND_RELEASE_FAILED",
        command="/scan",
    )
    assert len(wrapper_calls) == 1
    assert underlying_worker_calls == [tmp_path / "worker-state.json"]
    assert len(marker_observations) == 1
    assert marker_observations[0].__cause__ is release_error


def test_unknown_wrapper_failure_is_not_labeled_as_release_failure(tmp_path):
    wrapper_calls = []

    def quota_slot_worker(**kwargs):
        wrapper_calls.append(kwargs)
        raise ValueError("unexpected: sk-live-secret /private/secret")

    response = _application(tmp_path, quota_slot_worker).dispatch(
        _request("/scan")
    )

    _assert_safe_response(response, category="INTERNAL_ERROR", command="/scan")
    assert len(wrapper_calls) == 1


@pytest.mark.parametrize(
    ("command_request", "overrides"),
    [
        (_request("/scan", telegram_user_id=True), {}),
        (_request("/scan", arguments=("BTCUSDT",)), {}),
        (_request("/scan"), {"quota_limit": 0}),
        (_request("/scan"), {"slot_capacity": False}),
        (_request("/scan"), {"window_id_provider": lambda request: "   "}),
    ],
)
def test_invalid_scan_input_or_policy_is_rejected_before_worker(
    tmp_path, command_request, overrides
):
    worker_calls = []

    def worker(**kwargs):
        worker_calls.append(kwargs)

    response = _application(tmp_path, worker, **overrides).dispatch(
        command_request
    )

    _assert_safe_response(response, category="INVALID_INPUT", command="/scan")
    assert worker_calls == []
    assert list(tmp_path.iterdir()) == []




def test_response_bound_truncates_deterministically_without_worker_call(
    tmp_path,
):
    worker_calls = []

    def worker(**kwargs):
        worker_calls.append(kwargs)

    application = _application(tmp_path, worker, max_response_chars=13)

    response = application.dispatch(_request("/help"))

    assert worker_calls == []
    assert len(response.message) <= 13
    assert response.message.endswith(TRUNCATION_MARKER)


@pytest.mark.parametrize("max_response_chars", [None, 0, 12, True])
def test_invalid_response_limit_rejects_before_worker(tmp_path, max_response_chars):
    worker_calls = []

    def worker(**kwargs):
        worker_calls.append(kwargs)

    response = _application(
        tmp_path,
        worker,
        max_response_chars=max_response_chars,
    ).dispatch(_request("/scan"))

    _assert_safe_response(response, category="INVALID_INPUT", command="/scan")
    assert worker_calls == []


def test_import_is_side_effect_free_in_an_empty_working_directory(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)

    module = importlib.import_module("engine.telegram_application_v4")
    importlib.reload(module)

    assert list(tmp_path.iterdir()) == []
