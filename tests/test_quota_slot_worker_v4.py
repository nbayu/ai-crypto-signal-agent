import importlib
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

import engine.quota_slot_worker_v4 as quota_worker
from engine.quota_slot_engine_v4 import (
    QuotaSlotRejected,
    acquire_quota_slot_v4,
    release_quota_slot_v4,
)
from engine.stateful_worker_v4 import run_master_engine_worker_v4


ACQUIRED_AT = datetime(2026, 7, 14, 17, 0, 0)
RELEASED_AT = datetime(2026, 7, 14, 17, 5, 0)


def _read_state(state_path):
    return json.loads(state_path.read_text())


def _core_acquire(
    state_path,
    *,
    subject_id="subject-001",
    window_id="window-001",
    quota_limit=1,
    slot_capacity=1,
    reservation_id="reservation-existing",
):
    return acquire_quota_slot_v4(
        subject_id=subject_id,
        window_id=window_id,
        quota_limit=quota_limit,
        slot_capacity=slot_capacity,
        state_path=state_path,
        now_provider=lambda: ACQUIRED_AT,
        reservation_id_provider=lambda: reservation_id,
    )


def _core_release(state_path, reservation_id="reservation-existing"):
    return release_quota_slot_v4(
        reservation_id=reservation_id,
        state_path=state_path,
        now_provider=lambda: RELEASED_AT,
    )


def _run_wrapper(
    *,
    quota_state_path,
    worker_state_path,
    quota_now_provider,
    reservation_id_provider,
    worker,
    subject_id="subject-001",
    window_id="window-001",
    quota_limit=1,
    slot_capacity=1,
    **dependencies,
):
    return quota_worker.run_quota_slot_worker_v4(
        subject_id=subject_id,
        window_id=window_id,
        quota_limit=quota_limit,
        slot_capacity=slot_capacity,
        quota_state_path=quota_state_path,
        worker_state_path=worker_state_path,
        quota_now_provider=quota_now_provider,
        reservation_id_provider=reservation_id_provider,
        worker=worker,
        **dependencies,
    )


def test_success_acquires_runs_worker_releases_and_returns_results(
    tmp_path,
):
    quota_state_path = tmp_path / "quota.json"
    worker_state_path = tmp_path / "worker.json"
    worker_result = {"state_path": worker_state_path, "run": "sentinel"}
    events = []
    now_values = iter(
        [
            ("acquired_at", ACQUIRED_AT),
            ("released_at", RELEASED_AT),
        ]
    )

    def quota_now_provider():
        label, value = next(now_values)
        events.append(label)
        return value

    def reservation_id_provider():
        events.append("reservation_id")
        return "reservation-001"

    def worker(*, state_path):
        events.append(("worker", state_path))
        return worker_result

    result = _run_wrapper(
        quota_state_path=quota_state_path,
        worker_state_path=worker_state_path,
        quota_now_provider=quota_now_provider,
        reservation_id_provider=reservation_id_provider,
        worker=worker,
        quota_limit=2,
        slot_capacity=1,
    )

    assert events == [
        "reservation_id",
        "acquired_at",
        ("worker", worker_state_path),
        "released_at",
    ]
    assert result["admission"]["admitted"] is True
    assert result["admission"]["reservation_id"] == "reservation-001"
    assert set(result) == {"admission", "worker_result", "release"}
    assert result["worker_result"] is worker_result
    assert result["release"]["released"] is True
    assert result["release"]["active_slot_count"] == 0

    state = _read_state(quota_state_path)
    assert state["quota_usage"] == {
        "subject-001": {"window-001": 1},
    }
    assert state["reservations"]["reservation-001"]["state"] == (
        "RELEASED"
    )
    assert state["reservations"]["reservation-001"]["released_at"] == (
        "2026-07-14T17:05:00"
    )


def test_worker_failure_releases_slot_and_reraises_original_exception(
    tmp_path,
):
    quota_state_path = tmp_path / "quota.json"
    worker_state_path = tmp_path / "worker.json"
    worker_error = RuntimeError("worker boom")
    events = []
    now_values = iter([ACQUIRED_AT, RELEASED_AT])

    def quota_now_provider():
        value = next(now_values)
        events.append(("quota_time", value))
        return value

    def worker(*, state_path):
        events.append(("worker", state_path))
        raise worker_error

    with pytest.raises(RuntimeError) as exc_info:
        _run_wrapper(
            quota_state_path=quota_state_path,
            worker_state_path=worker_state_path,
            quota_now_provider=quota_now_provider,
            reservation_id_provider=lambda: "reservation-failed",
            worker=worker,
        )

    assert exc_info.value is worker_error
    assert events == [
        ("quota_time", ACQUIRED_AT),
        ("worker", worker_state_path),
        ("quota_time", RELEASED_AT),
    ]
    state = _read_state(quota_state_path)
    assert state["quota_usage"]["subject-001"]["window-001"] == 1
    reservation = state["reservations"]["reservation-failed"]
    assert reservation["state"] == "RELEASED"
    assert reservation["released_at"] == "2026-07-14T17:05:00"


def test_quota_rejection_never_calls_worker_or_creates_reservation(
    tmp_path,
):
    quota_state_path = tmp_path / "quota.json"
    worker_state_path = tmp_path / "worker.json"
    _core_acquire(quota_state_path)
    _core_release(quota_state_path)
    state_before_rejection = quota_state_path.read_text()
    worker_calls = []

    def worker(*, state_path):
        worker_calls.append(state_path)

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _run_wrapper(
            quota_state_path=quota_state_path,
            worker_state_path=worker_state_path,
            quota_now_provider=lambda: ACQUIRED_AT,
            reservation_id_provider=lambda: "reservation-rejected",
            worker=worker,
        )

    assert exc_info.value.reason_code == "QUOTA_EXHAUSTED"
    assert worker_calls == []
    assert quota_state_path.read_text() == state_before_rejection
    state = _read_state(quota_state_path)
    assert state["quota_usage"]["subject-001"]["window-001"] == 1
    assert list(state["reservations"]) == ["reservation-existing"]


def test_slot_rejection_never_calls_worker_or_consumes_rejected_quota(
    tmp_path,
):
    quota_state_path = tmp_path / "quota.json"
    worker_state_path = tmp_path / "worker.json"
    _core_acquire(quota_state_path)
    state_before_rejection = quota_state_path.read_text()
    worker_calls = []

    def worker(*, state_path):
        worker_calls.append(state_path)

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _run_wrapper(
            quota_state_path=quota_state_path,
            worker_state_path=worker_state_path,
            quota_now_provider=lambda: ACQUIRED_AT,
            reservation_id_provider=lambda: "reservation-rejected",
            worker=worker,
            subject_id="subject-002",
        )

    assert exc_info.value.reason_code == "SLOTS_FULL"
    assert worker_calls == []
    assert quota_state_path.read_text() == state_before_rejection
    state = _read_state(quota_state_path)
    assert "subject-002" not in state["quota_usage"]
    assert list(state["reservations"]) == ["reservation-existing"]


def test_worker_receives_worker_state_path_by_keyword(tmp_path):
    quota_state_path = tmp_path / "quota.json"
    worker_state_path = tmp_path / "worker.json"
    received = []

    def fake_acquire(**kwargs):
        return {"reservation_id": "reservation-001"}

    def fake_release(**kwargs):
        return {"released": True}

    def worker(*, state_path):
        received.append(state_path)
        return "worker-result"

    result = _run_wrapper(
        quota_state_path=quota_state_path,
        worker_state_path=worker_state_path,
        quota_now_provider=lambda: ACQUIRED_AT,
        reservation_id_provider=lambda: "reservation-001",
        worker=worker,
        acquire=fake_acquire,
        release=fake_release,
    )

    assert received == [worker_state_path]
    assert result["worker_result"] == "worker-result"


def test_default_worker_and_core_dependencies_are_canonical():
    parameters = inspect.signature(
        quota_worker.run_quota_slot_worker_v4
    ).parameters

    assert parameters["worker"].default is run_master_engine_worker_v4
    assert parameters["acquire"].default is acquire_quota_slot_v4
    assert parameters["release"].default is release_quota_slot_v4


def test_release_failure_after_worker_success_fails_closed_without_retry(
    tmp_path,
):
    quota_state_path = tmp_path / "quota.json"
    worker_state_path = tmp_path / "worker.json"
    release_error = RuntimeError("release boom")
    events = []

    def worker(*, state_path):
        events.append(("worker", state_path))
        return "completed-worker-result"

    def failing_release(**kwargs):
        events.append(("release", kwargs["reservation_id"]))
        raise release_error

    with pytest.raises(RuntimeError) as exc_info:
        _run_wrapper(
            quota_state_path=quota_state_path,
            worker_state_path=worker_state_path,
            quota_now_provider=lambda: ACQUIRED_AT,
            reservation_id_provider=lambda: "reservation-001",
            worker=worker,
            release=failing_release,
        )

    assert exc_info.value is release_error
    assert events == [
        ("worker", worker_state_path),
        ("release", "reservation-001"),
    ]
    state = _read_state(quota_state_path)
    assert state["quota_usage"]["subject-001"]["window-001"] == 1
    assert state["reservations"]["reservation-001"]["state"] == "ACTIVE"


def test_worker_failure_remains_primary_when_release_also_fails(tmp_path):
    quota_state_path = tmp_path / "quota.json"
    worker_state_path = tmp_path / "worker.json"
    worker_error = RuntimeError("worker boom")
    release_error = RuntimeError("release boom")
    events = []

    def fake_acquire(**kwargs):
        events.append("acquire")
        return {"reservation_id": "reservation-001"}

    def worker(*, state_path):
        events.append(("worker", state_path))
        raise worker_error

    def failing_release(**kwargs):
        events.append(("release", kwargs["reservation_id"]))
        raise release_error

    with pytest.raises(RuntimeError) as exc_info:
        _run_wrapper(
            quota_state_path=quota_state_path,
            worker_state_path=worker_state_path,
            quota_now_provider=lambda: ACQUIRED_AT,
            reservation_id_provider=lambda: "reservation-001",
            worker=worker,
            acquire=fake_acquire,
            release=failing_release,
        )

    assert exc_info.value is worker_error
    assert exc_info.value.__cause__ is release_error
    assert events == [
        "acquire",
        ("worker", worker_state_path),
        ("release", "reservation-001"),
    ]


def test_admission_failure_precedes_worker_and_release(tmp_path):
    quota_state_path = tmp_path / "quota.json"
    worker_state_path = tmp_path / "worker.json"
    rejection = QuotaSlotRejected("QUOTA_EXHAUSTED", "quota exhausted")
    events = []

    def failing_acquire(**kwargs):
        events.append("acquire")
        raise rejection

    def worker(*, state_path):
        events.append("worker")

    def release(**kwargs):
        events.append("release")

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _run_wrapper(
            quota_state_path=quota_state_path,
            worker_state_path=worker_state_path,
            quota_now_provider=lambda: ACQUIRED_AT,
            reservation_id_provider=lambda: "reservation-001",
            worker=worker,
            acquire=failing_acquire,
            release=release,
        )

    assert exc_info.value is rejection
    assert events == ["acquire"]
    assert not quota_state_path.exists()
    assert not worker_state_path.exists()


def test_importing_quota_slot_worker_has_no_side_effects(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delitem(
        sys.modules,
        "engine.quota_slot_worker_v4",
        raising=False,
    )

    module = importlib.import_module("engine.quota_slot_worker_v4")

    assert hasattr(module, "run_quota_slot_worker_v4")
    assert not Path("data").exists()
