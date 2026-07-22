"""Focused fake-only tests for the one-shot Telegram probe operator entrypoint."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import inspect
import io
import json
import logging

import pytest

import engine.one_shot_telegram_identity_probe_operator_v1 as module
from engine.one_shot_telegram_identity_probe_harness_v1 import (
    run_one_shot_telegram_identity_probe,
)


_CLOCK_VALUE = datetime(2026, 7, 22, 1, 2, 3, 456789, tzinfo=timezone.utc)
_TIMESTAMP = "2026-07-22T01:02:03.456789Z"
_RESULT_MAPPING = {
    "result": "TELEGRAM_IDENTITY_CONFIRMED",
    "gate": "",
    "configuration_valid": True,
    "credential_metadata_valid": True,
    "credential_resolution_attempted": True,
    "credential_resolved": True,
    "network_probe_attempted": True,
    "bot_identity_confirmed": True,
    "probe_timestamp": _TIMESTAMP,
    "reason": "TELEGRAM_IDENTITY_CONFIRMED",
}


class _FakeResult:
    def __init__(self, *, confirmed: bool, mapping: dict[str, object] | None = None) -> None:
        self.bot_identity_confirmed = confirmed
        self._mapping = dict(_RESULT_MAPPING if mapping is None else mapping)
        self.to_dict_calls = 0

    def to_dict(self) -> dict[str, object]:
        self.to_dict_calls += 1
        return dict(self._mapping)


def _clock() -> datetime:
    return _CLOCK_VALUE


def test_public_operator_function_exists() -> None:
    assert callable(module.run_one_shot_telegram_identity_probe_operator)


def test_public_operator_has_the_exact_keyword_only_signature() -> None:
    signature = inspect.signature(module.run_one_shot_telegram_identity_probe_operator)
    assert tuple(signature.parameters) == ("secret_reader", "clock", "harness")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert signature.parameters["harness"].default is run_one_shot_telegram_identity_probe


def test_public_operator_has_no_forbidden_inputs() -> None:
    names = set(inspect.signature(module.run_one_shot_telegram_identity_probe_operator).parameters)
    forbidden = {
        "token", "authorization", "credential_metadata", "probed_at",
        "credential_resolver", "adapter", "destination", "message", "output",
        "logger", "argv", "environment", "runtime", "launcher", "service", "systemd",
    }
    assert not names.intersection(forbidden)


def test_operator_applies_exact_logger_safeguards_before_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int]] = []
    order: list[str] = []
    emitted: list[object] = []
    original_get_logger = module.logging.getLogger
    root = original_get_logger()
    root_level = root.level
    root_handlers = tuple(root.handlers)
    root_propagate = root.propagate

    class FakeLogger:
        def __init__(self, name: str) -> None:
            self.name = name
            self.handlers = [object()]
            self.propagate = True

        def setLevel(self, level: int) -> None:
            calls.append((self.name, level))
            order.append(f"logger:{self.name}")

    fake_loggers: dict[str, FakeLogger] = {}

    def fake_get_logger(name: str | None = None) -> object:
        if name is None:
            return original_get_logger()
        if name not in ("telegram", "httpx", "httpcore", "asyncio"):
            raise AssertionError("unexpected named logger request")
        if name not in fake_loggers:
            fake_loggers[name] = FakeLogger(name)
        return fake_loggers[name]

    monkeypatch.setattr(module.logging, "getLogger", fake_get_logger)

    def authorization(**_: object) -> object:
        order.append("authorization")
        return object()

    def metadata(**_: object) -> object:
        order.append("metadata")
        return object()

    def clock() -> datetime:
        order.append("clock")
        return _CLOCK_VALUE

    def harness(**_: object) -> _FakeResult:
        order.append("harness")
        return _FakeResult(confirmed=True)

    monkeypatch.setattr(module, "ControlledTelegramIdentityProbeAuthorizationV1", authorization)
    monkeypatch.setattr(module, "ControlledCredentialMetadataV1", metadata)
    module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=lambda: "opaque-fake-secret",
        clock=clock,
        harness=harness,
    )
    assert calls == [
        ("telegram", logging.WARNING),
        ("httpx", logging.WARNING),
        ("httpcore", logging.WARNING),
        ("asyncio", logging.WARNING),
    ]
    assert order == [
        "logger:telegram", "logger:httpx", "logger:httpcore", "logger:asyncio",
        "authorization", "metadata", "clock", "harness",
    ]
    assert fake_get_logger() is root
    assert root.level == root_level
    assert tuple(root.handlers) == root_handlers
    assert root.propagate is root_propagate
    assert all(logger.handlers for logger in fake_loggers.values())
    assert all(logger.propagate is True for logger in fake_loggers.values())
    assert emitted == []


def test_operator_configures_logging_before_constructing_controlled_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    original_get_logger = module.logging.getLogger

    class FakeLogger:
        def setLevel(self, _: int) -> None:
            order.append("logger")

    def authorization(**_: object) -> object:
        order.append("authorization")
        return object()

    def metadata(**_: object) -> object:
        order.append("metadata")
        return object()

    def fake_get_logger(name: str | None = None) -> object:
        if name is None:
            return original_get_logger()
        return FakeLogger()

    monkeypatch.setattr(module.logging, "getLogger", fake_get_logger)
    monkeypatch.setattr(module, "ControlledTelegramIdentityProbeAuthorizationV1", authorization)
    monkeypatch.setattr(module, "ControlledCredentialMetadataV1", metadata)
    module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=lambda: "opaque-fake-secret",
        clock=_clock,
        harness=lambda **_: _FakeResult(confirmed=True),
    )
    assert order == ["logger", "logger", "logger", "logger", "authorization", "metadata"]


def test_operator_does_not_mutate_root_logger_or_handlers() -> None:
    root = logging.getLogger()
    level = root.level
    handlers = tuple(root.handlers)

    module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=lambda: "opaque-fake-secret",
        clock=_clock,
        harness=lambda **_: _FakeResult(confirmed=True),
    )
    assert root.level == level
    assert tuple(root.handlers) == handlers


def test_operator_constructs_exact_authorization_metadata_and_forwarding() -> None:
    received: dict[str, object] = {}
    secret_reader = object()

    def harness(**kwargs: object) -> _FakeResult:
        received.update(kwargs)
        return _FakeResult(confirmed=True)

    exit_code, json_text = module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=secret_reader,
        clock=_clock,
        harness=harness,
    )
    authorization = received["authorization"]
    metadata = received["credential_metadata"]
    assert authorization.to_dict() == {
        "activation_authorized": True,
        "workload_authorized": True,
        "credential_authorized": True,
        "network_authorized": True,
    }
    assert metadata.to_dict() == {
        "credential_name": "telegram_bot_token",
        "source_kind": "INJECTED_SECRET_RESOLVER",
        "required": True,
        "available": True,
        "readable": True,
        "non_empty": True,
        "reason": "CONTROLLED_CREDENTIAL_METADATA_VALID",
    }
    assert received["secret_reader"] is secret_reader
    assert received["probed_at"] == _TIMESTAMP
    assert exit_code == 0
    assert json.loads(json_text) == _RESULT_MAPPING


def test_operator_calls_clock_once_and_uses_exact_microsecond_utc_timestamp() -> None:
    calls: list[object] = []
    received: dict[str, object] = {}

    def clock() -> datetime:
        calls.append(object())
        return _CLOCK_VALUE

    def harness(**kwargs: object) -> _FakeResult:
        received.update(kwargs)
        return _FakeResult(confirmed=True)

    module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=lambda: "opaque-fake-secret",
        clock=clock,
        harness=harness,
    )
    assert len(calls) == 1
    assert received["probed_at"] == _TIMESTAMP


@pytest.mark.parametrize(
    "clock_value",
    (
        datetime(2026, 7, 22, 1, 2, 3),
        datetime(2026, 7, 22, 1, 2, 3, tzinfo=timezone(timedelta(hours=7))),
        object(),
    ),
)
def test_operator_rejects_invalid_clock_values_before_harness(clock_value: object) -> None:
    harness_calls: list[object] = []

    with pytest.raises(ValueError):
        module.run_one_shot_telegram_identity_probe_operator(
            secret_reader=lambda: "opaque-fake-secret",
            clock=lambda: clock_value,
            harness=lambda **_: harness_calls.append(object()),
        )
    assert harness_calls == []


def test_operator_calls_harness_and_result_to_dict_once_without_reading_secret() -> None:
    harness_calls: list[dict[str, object]] = []
    reader_calls: list[object] = []
    result = _FakeResult(confirmed=True)

    def harness(**kwargs: object) -> _FakeResult:
        harness_calls.append(kwargs)
        return result

    exit_code, _ = module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=lambda: reader_calls.append(object()),
        clock=_clock,
        harness=harness,
    )
    assert exit_code == 0
    assert len(harness_calls) == result.to_dict_calls == 1
    assert reader_calls == []
    assert tuple(harness_calls[0]) == (
        "authorization", "credential_metadata", "secret_reader", "probed_at",
    )


def test_operator_uses_the_supplied_harness_once_without_fallback() -> None:
    calls: list[object] = []
    error = RuntimeError("fake-harness-failure")

    def harness(**_: object) -> object:
        calls.append(object())
        raise error

    with pytest.raises(RuntimeError) as caught:
        module.run_one_shot_telegram_identity_probe_operator(
            secret_reader=lambda: "opaque-fake-secret",
            clock=_clock,
            harness=harness,
        )
    assert caught.value is error
    assert len(calls) == 1


def test_operator_serializes_compact_ascii_json_in_locked_mapping_order() -> None:
    mapping = dict(_RESULT_MAPPING)
    mapping["reason"] = "non-ascii-\u00e9"
    result = _FakeResult(confirmed=True, mapping=mapping)

    _, json_text = module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=lambda: "opaque-fake-secret",
        clock=_clock,
        harness=lambda **_: result,
    )
    assert json_text == json.dumps(mapping, separators=(",", ":"), ensure_ascii=True)
    assert "\\u00e9" in json_text
    assert "\n" not in json_text
    assert tuple(json.loads(json_text)) == tuple(mapping)


@pytest.mark.parametrize("confirmed", (False, object()))
def test_operator_maps_only_literal_confirmed_true_to_success(confirmed: object) -> None:
    result = _FakeResult(confirmed=confirmed is True)
    result.bot_identity_confirmed = confirmed

    exit_code, _ = module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=lambda: "opaque-fake-secret",
        clock=_clock,
        harness=lambda **_: result,
    )
    assert exit_code == 1


def test_operator_does_not_inspect_failure_reason() -> None:
    class Result:
        bot_identity_confirmed = False

        @property
        def reason(self) -> object:
            raise AssertionError("reason must not be inspected")

        def to_dict(self) -> dict[str, object]:
            return dict(_RESULT_MAPPING)

    exit_code, _ = module.run_one_shot_telegram_identity_probe_operator(
        secret_reader=lambda: "opaque-fake-secret",
        clock=_clock,
        harness=lambda **_: Result(),
    )
    assert exit_code == 1


@pytest.mark.parametrize("error", (RuntimeError("ordinary"), KeyboardInterrupt()))
def test_public_operator_propagates_harness_exceptions(error: BaseException) -> None:
    def harness(**_: object) -> object:
        raise error

    with pytest.raises(type(error)) as caught:
        module.run_one_shot_telegram_identity_probe_operator(
            secret_reader=lambda: "opaque-fake-secret",
            clock=_clock,
            harness=harness,
        )
    assert caught.value is error


def test_public_operator_propagates_clock_exception_before_harness() -> None:
    error = RuntimeError("fake-clock-failure")
    harness_calls: list[object] = []

    def clock() -> datetime:
        raise error

    with pytest.raises(RuntimeError) as caught:
        module.run_one_shot_telegram_identity_probe_operator(
            secret_reader=lambda: "opaque-fake-secret",
            clock=clock,
            harness=lambda **_: harness_calls.append(object()),
        )
    assert caught.value is error
    assert harness_calls == []


def test_main_rejects_arguments_before_reader_or_operator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    monkeypatch.setattr(module.sys, "argv", ["operator", "unexpected"])
    monkeypatch.setattr(module.sys, "stdout", stdout)
    monkeypatch.setattr(
        module,
        "run_one_shot_telegram_identity_probe_operator",
        lambda **_: (_ for _ in ()).throw(AssertionError("operator must not run")),
    )
    monkeypatch.setattr(
        module.getpass,
        "getpass",
        lambda prompt: (_ for _ in ()).throw(AssertionError("reader must not run")),
    )
    assert module.main() == 2
    assert stdout.getvalue() == '{"operator_result":"MISUSE"}\n'


def test_main_misuse_keeps_stderr_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(module.sys, "argv", ["operator", "unexpected"])
    monkeypatch.setattr(module.sys, "stdout", stdout)
    monkeypatch.setattr(module.sys, "stderr", stderr)
    assert module.main() == 2
    assert stderr.getvalue() == ""


def test_main_injects_fixed_getpass_reader_clock_and_writes_one_json_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    reader_calls: list[str] = []
    received: dict[str, object] = {}
    monkeypatch.setattr(module.sys, "argv", ["operator"])
    monkeypatch.setattr(module.sys, "stdout", stdout)

    def fake_getpass(prompt: str) -> str:
        reader_calls.append(prompt)
        return "opaque-fake-secret"

    def operator(**kwargs: object) -> tuple[int, str]:
        received.update(kwargs)
        assert kwargs["clock"]() == _CLOCK_VALUE
        assert kwargs["secret_reader"]() == "opaque-fake-secret"
        return 1, '{"result":"CONTROLLED_FAILURE"}'

    monkeypatch.setattr(module.getpass, "getpass", fake_getpass)
    monkeypatch.setattr(module, "_main_clock", _clock)
    monkeypatch.setattr(module, "run_one_shot_telegram_identity_probe_operator", operator)
    assert module.main() == 1
    assert reader_calls == ["Telegram bot token: "]
    assert stdout.getvalue() == '{"result":"CONTROLLED_FAILURE"}\n'
    assert set(received) == {"secret_reader", "clock"}


def test_main_sanitizes_getpass_exception_without_a_second_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    reader_calls: list[str] = []
    monkeypatch.setattr(module.sys, "argv", ["operator"])
    monkeypatch.setattr(module.sys, "stdout", stdout)

    def fake_getpass(prompt: str) -> str:
        reader_calls.append(prompt)
        raise RuntimeError("opaque-fake-secret")

    def operator(**kwargs: object) -> tuple[int, str]:
        kwargs["secret_reader"]()
        raise AssertionError("unreachable")

    monkeypatch.setattr(module.getpass, "getpass", fake_getpass)
    monkeypatch.setattr(module, "run_one_shot_telegram_identity_probe_operator", operator)
    assert module.main() == 70
    assert reader_calls == ["Telegram bot token: "]
    assert stdout.getvalue() == '{"operator_result":"UNEXPECTED_FAILURE"}\n'


def test_main_sanitizes_ordinary_exception_without_leaking_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    monkeypatch.setattr(module.sys, "argv", ["operator"])
    monkeypatch.setattr(module.sys, "stdout", stdout)
    error = RuntimeError("opaque-fake-secret exception detail")

    def operator(**_: object) -> tuple[int, str]:
        raise error

    monkeypatch.setattr(module, "run_one_shot_telegram_identity_probe_operator", operator)
    assert module.main() == 70
    assert stdout.getvalue() == '{"operator_result":"UNEXPECTED_FAILURE"}\n'
    assert "opaque-fake-secret" not in stdout.getvalue()


def test_main_controlled_failure_keeps_stderr_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(module.sys, "argv", ["operator"])
    monkeypatch.setattr(module.sys, "stdout", stdout)
    monkeypatch.setattr(module.sys, "stderr", stderr)
    monkeypatch.setattr(
        module,
        "run_one_shot_telegram_identity_probe_operator",
        lambda **_: (1, '{"result":"CONTROLLED_FAILURE"}'),
    )
    assert module.main() == 1
    assert stdout.getvalue() == '{"result":"CONTROLLED_FAILURE"}\n'
    assert stderr.getvalue() == ""


@pytest.mark.parametrize("error", (KeyboardInterrupt(), SystemExit(3)))
def test_main_does_not_catch_base_exceptions(
    monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    monkeypatch.setattr(module.sys, "argv", ["operator"])

    def operator(**_: object) -> tuple[int, str]:
        raise error

    monkeypatch.setattr(module, "run_one_shot_telegram_identity_probe_operator", operator)
    with pytest.raises(type(error)) as caught:
        module.main()
    assert caught.value is error


def test_module_has_the_exact_executable_guard_and_no_operational_surfaces() -> None:
    source = inspect.getsource(module)
    assert 'if __name__ == "__main__":\n    raise SystemExit(main())' in source
    forbidden = (
        "argparse", "os.environ", "getenv", "sys.stdin", "input(", "open(",
        "tempfile", "subprocess", "requests", "urllib", "socket", "send_message",
        "active_signal_ledger", "production_signal_service", "scanner", "master_engine",
        "provider", "launcher", "runtime", "systemd", "Bot(", "HTTPXRequest",
    )
    assert not any(value in source for value in forbidden)
