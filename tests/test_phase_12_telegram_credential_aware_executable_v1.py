"""RED contract for the Phase 12 systemd-credential executable boundary."""
from __future__ import annotations

import ast
import inspect
import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone

import pytest

import engine.phase_12_telegram_credential_aware_executable_v1 as module
from engine.phase_12_telegram_credential_aware_executable_v1 import (
    main,
    run_phase_12_telegram_credential_aware_executable,
)
from engine.phase_12_telegram_production_launcher_v1 import TelegramLauncherDependenciesV1
from engine.phase_12_activation_configuration_v1 import (
    Phase12ActivationConfigurationErrorV1,
    Phase12ActivationConfigurationV1,
    load_phase_12_activation_configuration,
)
from engine.systemd_telegram_credential_reader_v1 import (
    SystemdTelegramCredentialErrorV1,
    read_systemd_telegram_credential,
)


_DIRECTORY = "/run/credentials/phase-12-test.service"
_NAME = "telegram_bot_token"
_CREDENTIAL = "fixture-credential-value"
_MISUSE_JSON = '{"executable_result":"MISUSE"}'
_LOCATOR_FAILURE_JSON = '{"executable_result":"CREDENTIAL_LOCATOR_FAILURE"}'
_UNEXPECTED_JSON = '{"executable_result":"UNEXPECTED_FAILURE"}'
_ACTIVATION_CONFIGURATION_PATH = "/etc/ai-crypto-signal-agent/phase12-activation-v1.conf"
_CONFIGURATION_NOW = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)


class _EnvironmentReader:
    def __init__(self, value: object) -> None:
        self.value = value
        self.calls: list[str] = []

    def __call__(self, name: str) -> object:
        self.calls.append(name)
        if name != "CREDENTIALS_DIRECTORY":
            raise AssertionError("only the systemd credential directory locator is permitted")
        return self.value


class _CredentialReader:
    def __init__(self, result: str | BaseException = _CREDENTIAL) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def __call__(self, directory: str, filename: str) -> str:
        self.calls.append((directory, filename))
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _run_with_fake_activation_configuration(
    *,
    mode: str,
    environment_reader: _EnvironmentReader,
    credential_reader: _CredentialReader,
    launcher: Callable[..., tuple[int, str]],
) -> tuple[int, str]:
    return run_phase_12_telegram_credential_aware_executable(
        environment_reader=environment_reader,
        configuration_reader=_ActivationConfigurationReader(_activation_configuration(mode)),
        now_utc_provider=lambda: _CONFIGURATION_NOW,
        credential_reader=credential_reader,
        launcher=launcher,
    )


def _launcher_that_uses_reader(
    calls: list[TelegramLauncherDependenciesV1],
    *,
    repeat_reader: bool = False,
    result: tuple[int, str] = (0, '{"launcher_result":"SANITIZED"}'),
) -> Callable[..., tuple[int, str]]:
    def launcher(*, dependencies: TelegramLauncherDependenciesV1, **_: object) -> tuple[int, str]:
        calls.append(dependencies)
        assert isinstance(dependencies, TelegramLauncherDependenciesV1)
        assert dependencies.credential_reader(_DIRECTORY, _NAME) == _CREDENTIAL
        if repeat_reader:
            assert dependencies.credential_reader(_DIRECTORY, _NAME) == _CREDENTIAL
        return result

    return launcher


def _capture_bridge() -> tuple[list[TelegramLauncherDependenciesV1], Callable[..., tuple[int, str]]]:
    captured: list[TelegramLauncherDependenciesV1] = []

    def launcher(*, dependencies: TelegramLauncherDependenciesV1, **_: object) -> tuple[int, str]:
        captured.append(dependencies)
        return (0, '{"launcher_result":"SANITIZED"}')

    return captured, launcher


def test_public_api_is_exact_and_keyword_only() -> None:
    signature = inspect.signature(run_phase_12_telegram_credential_aware_executable)
    assert tuple(signature.parameters) == (
        "environment_reader",
        "configuration_reader",
        "now_utc_provider",
        "credential_reader",
        "launcher",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert signature.parameters["environment_reader"].default is inspect.Parameter.empty
    assert signature.parameters["configuration_reader"].default is load_phase_12_activation_configuration
    assert callable(signature.parameters["now_utc_provider"].default)
    assert signature.parameters["credential_reader"].default is read_systemd_telegram_credential
    assert signature.parameters["launcher"].default is module.run_phase_12_telegram_production_launcher
    assert inspect.signature(main).parameters == {}
    assert "tuple" in str(signature.return_annotation)
    assert "int" in str(inspect.signature(main).return_annotation)
    source = inspect.getsource(module)
    assert 'if __name__ == "__main__":' in source
    assert "raise SystemExit(main())" in source


@pytest.mark.parametrize("argv", (("program", "unexpected"), ("program", "one", "two")))
def test_main_rejects_each_nonzero_argument_count_without_downstream_calls(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: tuple[str, ...]
) -> None:
    called: list[object] = []
    monkeypatch.setattr(module.sys, "argv", list(argv))
    monkeypatch.setattr(module, "run_phase_12_telegram_credential_aware_executable", lambda **_: called.append(True))
    assert main() == 2
    assert called == []
    assert capsys.readouterr() == (_MISUSE_JSON + "\n", "")


def test_main_accepts_zero_arguments_and_prints_one_json_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(module.sys, "argv", ["program"])
    monkeypatch.setattr(
        module,
        "run_phase_12_telegram_credential_aware_executable",
        lambda **_: (0, '{"launcher_result":"SANITIZED"}'),
    )
    assert main() == 0
    assert capsys.readouterr() == ('{"launcher_result":"SANITIZED"}\n', "")


def test_valid_locator_is_read_once_and_forwarded_to_the_fixed_credential_name() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader()
    launcher_calls: list[TelegramLauncherDependenciesV1] = []
    result = _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment,
        credential_reader=reader,
        launcher=_launcher_that_uses_reader(launcher_calls),
    )
    assert result == (0, '{"launcher_result":"SANITIZED"}')
    assert environment.calls == ["CREDENTIALS_DIRECTORY"]
    assert reader.calls == [(_DIRECTORY, _NAME)]
    assert len(launcher_calls) == 1


def test_successful_credential_read_is_cached_only_within_the_invocation() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader()
    launcher_calls: list[TelegramLauncherDependenciesV1] = []
    result = _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment,
        credential_reader=reader,
        launcher=_launcher_that_uses_reader(launcher_calls, repeat_reader=True),
    )
    assert result[0] == 0
    assert reader.calls == [(_DIRECTORY, _NAME)]
    assert len(launcher_calls) == 1


@pytest.mark.parametrize("locator", (None, 7, "", "relative", "/run/../credentials"))
def test_invalid_or_absent_locator_fails_closed_before_reader_or_launcher(locator: object) -> None:
    environment = _EnvironmentReader(locator)
    reader = _CredentialReader()
    launcher_calls: list[object] = []
    result = _run_with_fake_activation_configuration(
        mode="CLOSED",
        environment_reader=environment,
        credential_reader=reader,
        launcher=lambda **_: launcher_calls.append(True),
    )
    assert result == (1, _LOCATOR_FAILURE_JSON)
    assert environment.calls == ["CREDENTIALS_DIRECTORY"]
    assert reader.calls == []
    assert launcher_calls == []
    if locator == "":
        assert json.loads(result[1]) == {
            "executable_result": "CREDENTIAL_LOCATOR_FAILURE"
        }
        assert tuple(json.loads(result[1])) == ("executable_result",)
    else:
        assert str(locator) not in result[1]


def test_bridge_rejects_wrong_directory_and_filename_without_reader_call() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader()
    captured, launcher = _capture_bridge()
    result = _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment, credential_reader=reader, launcher=launcher
    )
    assert result[0] == 0
    bridge = captured[0].credential_reader
    with pytest.raises(Exception):
        bridge("/other", _NAME)
    with pytest.raises(Exception):
        bridge(_DIRECTORY, "other")
    assert reader.calls == []


def test_ordinary_credential_failure_is_cached_and_sanitized_without_retry() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader(RuntimeError(_CREDENTIAL))
    captured, launcher = _capture_bridge()
    result = _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment, credential_reader=reader, launcher=launcher
    )
    assert result[0] == 0
    bridge = captured[0].credential_reader
    failures = []
    for _ in range(2):
        with pytest.raises(Exception) as raised:
            bridge(_DIRECTORY, _NAME)
        failures.append(raised.value)
    assert reader.calls == [(_DIRECTORY, _NAME)]
    assert all(_CREDENTIAL not in str(error) + repr(error) for error in failures)


def test_base_exception_from_credential_reader_propagates_unchanged() -> None:
    interruption = KeyboardInterrupt("fixture interruption")
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader(interruption)
    captured, launcher = _capture_bridge()
    assert _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment, credential_reader=reader, launcher=launcher
    )[0] == 0
    with pytest.raises(KeyboardInterrupt) as raised:
        captured[0].credential_reader(_DIRECTORY, _NAME)
    assert raised.value is interruption
    assert reader.calls == [(_DIRECTORY, _NAME)]


def test_credential_failure_prevents_fake_runtime_effects() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader(SystemdTelegramCredentialErrorV1("CREDENTIAL_MISSING"))
    effects: list[str] = []

    def launcher(*, dependencies: TelegramLauncherDependenciesV1, **_: object) -> tuple[int, str]:
        with pytest.raises(SystemdTelegramCredentialErrorV1):
            dependencies.credential_reader(_DIRECTORY, _NAME)
        effects.append("launcher-after-reader")
        return (1, '{"launcher_result":"CREDENTIAL_FAILURE"}')

    result = _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment, credential_reader=reader, launcher=launcher
    )
    assert result == (1, '{"launcher_result":"CREDENTIAL_FAILURE"}')
    assert effects == ["launcher-after-reader"]
    assert reader.calls == [(_DIRECTORY, _NAME)]


def test_launcher_result_is_compact_deterministic_and_has_no_public_newline() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader()
    expected = '{"launcher_result":"CONTROLLED_NON_SUCCESS","detail":"SANITIZED"}'
    result = _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment,
        credential_reader=reader,
        launcher=_launcher_that_uses_reader([], result=(1, expected)),
    )
    assert result == (1, expected)
    assert "\n" not in result[1]
    assert json.dumps(json.loads(result[1]), separators=(",", ":")) == result[1]
    assert tuple(json.loads(result[1])) == ("launcher_result", "detail")


def test_unexpected_exception_is_normalized_and_base_exception_propagates() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader()
    unexpected = _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment,
        credential_reader=reader,
        launcher=lambda **_: (_ for _ in ()).throw(RuntimeError(_CREDENTIAL)),
    )
    assert unexpected == (70, _UNEXPECTED_JSON)
    assert _CREDENTIAL not in unexpected[1]
    interruption = KeyboardInterrupt("fixture interruption")
    with pytest.raises(KeyboardInterrupt) as raised:
        _run_with_fake_activation_configuration(
            mode="CONTROLLED_WORKLOAD",
            environment_reader=_EnvironmentReader(_DIRECTORY),
            credential_reader=_CredentialReader(),
            launcher=lambda **_: (_ for _ in ()).throw(interruption),
        )
    assert raised.value is interruption


def test_no_locator_or_credential_detail_reaches_result_stdout_stderr_or_logging(
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader(RuntimeError(_CREDENTIAL))
    captured, launcher = _capture_bridge()
    root = logging.getLogger()
    handlers_before = tuple(root.handlers)
    level_before = root.level
    result = _run_with_fake_activation_configuration(
        mode="CONTROLLED_WORKLOAD",
        environment_reader=environment, credential_reader=reader, launcher=launcher
    )
    with pytest.raises(Exception):
        captured[0].credential_reader(_DIRECTORY, _NAME)
    rendered = result[1] + capsys.readouterr().out + capsys.readouterr().err + caplog.text
    assert _DIRECTORY not in rendered
    assert _CREDENTIAL not in rendered
    assert tuple(root.handlers) == handlers_before
    assert root.level == level_before


def test_source_has_only_the_directory_metadata_boundary_and_no_runtime_surface() -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not imported.intersection({"telegram", "httpx", "httpcore", "requests", "socket", "subprocess", "getpass"})
    for forbidden in (
        "TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TELEGRAM_TOKEN", "getpass", "sys.stdin",
        "input(", "print(", "logging", "systemctl", "curl", "wget", "Popen", "shell=True",
        "/etc/credstore.encrypted", ".token",
    ):
        assert forbidden not in source
    assert not any(value in source for value in ("open(", "os.open(", "glob(", "scandir("))
    assert "CREDENTIALS_DIRECTORY" in source
    assert "environ" not in source or "CREDENTIALS_DIRECTORY" in source
    assert _CREDENTIAL not in source


def test_module_has_no_direct_sdk_or_unsafe_public_surface() -> None:
    public = {name for name in module.__dict__ if not name.startswith("_")}
    assert not public.intersection({"Bot", "HTTPXRequest", "getpass", "socket", "subprocess", "requests"})
    assert callable(run_phase_12_telegram_credential_aware_executable)
    assert callable(main)



def _activation_configuration(mode: str) -> Phase12ActivationConfigurationV1:
    gate_values = {
        "CLOSED": (False, False, False, False, False),
        "CREDENTIAL_VALIDATION": (True, True, False, False, False),
        "TELEGRAM_CONNECTIVITY_VALIDATION": (True, True, True, False, False),
        "TELEGRAM_START_VALIDATION": (True, True, True, False, True),
        "CONTROLLED_WORKLOAD": (True, True, True, True, True),
    }[mode]
    evidence = ("NONE", "NONE", "NONE", "NONE", "NONE") if mode == "CLOSED" else (
        "owner-authorization-v1", "checkpoint-v1", "a" * 40,
        "2026-07-22T12:00:00Z", "2026-07-22T12:05:00Z",
    )
    return Phase12ActivationConfigurationV1(
        schema_version="phase12-activation-v1", activation_mode=mode,
        owner_authorization_id=evidence[0], approval_checkpoint_id=evidence[1],
        approved_locked_commit=evidence[2], approved_at=evidence[3], expires_at=evidence[4],
        activation_gate_open=gate_values[0], credential_gate_open=gate_values[1],
        network_gate_open=gate_values[2], workload_gate_open=gate_values[3],
        telegram_start_authorized=gate_values[4],
    )


class _ActivationConfigurationReader:
    def __init__(self, result: object, events: list[str] | None = None) -> None:
        self.result = result
        self.events = events
        self.calls: list[tuple[str, datetime]] = []

    def __call__(self, *, configuration_path: str, now_utc: datetime) -> Phase12ActivationConfigurationV1:
        self.calls.append((configuration_path, now_utc))
        if self.events is not None:
            self.events.append("configuration")
        if isinstance(self.result, BaseException):
            raise self.result
        assert isinstance(self.result, Phase12ActivationConfigurationV1)
        return self.result


def _run_with_activation_configuration(
    *, configuration_reader: _ActivationConfigurationReader,
    environment_reader: _EnvironmentReader, launcher: Callable[..., tuple[int, str]],
    credential_reader: _CredentialReader | None = None,
) -> tuple[int, str]:
    return run_phase_12_telegram_credential_aware_executable(
        environment_reader=environment_reader, configuration_reader=configuration_reader,
        now_utc_provider=lambda: _CONFIGURATION_NOW,
        credential_reader=credential_reader or _CredentialReader(), launcher=launcher,
    )


def _gate_values(gates: object) -> tuple[object, object, object, object, object]:
    return (
        gates.activation_gate_open, gates.credential_gate_open, gates.network_gate_open,
        gates.workload_gate_open, gates.telegram_start_authorized,
    )


def test_activation_configuration_loads_before_locator_and_forwards_only_gate_state() -> None:
    events: list[str] = []
    configuration_reader = _ActivationConfigurationReader(_activation_configuration("CLOSED"), events)

    class Environment:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def __call__(self, name: str) -> object:
            self.calls.append(name)
            events.append("locator")
            return _DIRECTORY

    environment = Environment()
    received: dict[str, object] = {}

    def launcher(**kwargs: object) -> tuple[int, str]:
        events.append("launcher")
        received.update(kwargs)
        return (1, "{\"launcher_result\":\"BLOCKED\"}")

    result = _run_with_activation_configuration(
        configuration_reader=configuration_reader, environment_reader=environment, launcher=launcher,
    )
    assert result == (1, "{\"launcher_result\":\"BLOCKED\"}")
    assert configuration_reader.calls == [(_ACTIVATION_CONFIGURATION_PATH, _CONFIGURATION_NOW)]
    assert environment.calls == ["CREDENTIALS_DIRECTORY"]
    assert events == ["configuration", "locator", "launcher"]
    assert set(received) == {"dependencies", "credential_directory", "gates"}
    assert _gate_values(received["gates"]) == (False, False, False, False, False)
    assert "owner-authorization-v1" not in repr(received)


def test_activation_configuration_failures_stop_before_locator_bridge_or_launcher() -> None:
    configuration_reader = _ActivationConfigurationReader(
        Phase12ActivationConfigurationErrorV1("CONFIGURATION_FORMAT_INVALID")
    )
    environment = _EnvironmentReader(_DIRECTORY)
    credentials = _CredentialReader()
    calls: list[object] = []
    result = _run_with_activation_configuration(
        configuration_reader=configuration_reader, environment_reader=environment,
        credential_reader=credentials, launcher=lambda **_: calls.append(True),
    )
    assert result == (1, "{\"executable_result\":\"ACTIVATION_CONFIGURATION_FAILURE\"}")
    assert configuration_reader.calls == [(_ACTIVATION_CONFIGURATION_PATH, _CONFIGURATION_NOW)]
    assert environment.calls == [] and credentials.calls == [] and calls == []
    assert "CONFIGURATION_FORMAT_INVALID" not in result[1]
    assert _ACTIVATION_CONFIGURATION_PATH not in result[1]


def test_unexpected_configuration_failure_is_normalized_and_baseexception_propagates() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    result = _run_with_activation_configuration(
        configuration_reader=_ActivationConfigurationReader(RuntimeError("dynamic configuration detail")),
        environment_reader=environment, launcher=lambda **_: (0, "{\"launcher_result\":\"SANITIZED\"}"),
    )
    assert result == (70, _UNEXPECTED_JSON)
    assert environment.calls == [] and "dynamic configuration detail" not in result[1]
    interruption = KeyboardInterrupt("configuration interruption")
    with pytest.raises(KeyboardInterrupt) as raised:
        _run_with_activation_configuration(
            configuration_reader=_ActivationConfigurationReader(interruption),
            environment_reader=_EnvironmentReader(_DIRECTORY),
            launcher=lambda **_: (0, "{\"launcher_result\":\"SANITIZED\"}"),
        )
    assert raised.value is interruption


@pytest.mark.parametrize(
    ("mode", "expected"),
    (
        ("CREDENTIAL_VALIDATION", (True, True, False, False, False)),
        ("TELEGRAM_CONNECTIVITY_VALIDATION", (True, True, True, False, False)),
        ("TELEGRAM_START_VALIDATION", (True, True, True, False, True)),
    ),
)
def test_partial_modes_forward_exact_gates_and_preserve_blocked_result(
    mode: str, expected: tuple[bool, bool, bool, bool, bool]
) -> None:
    received: list[object] = []
    credentials = _CredentialReader()

    def launcher(**kwargs: object) -> tuple[int, str]:
        received.append(kwargs["gates"])
        return (1, "{\"launcher_result\":\"BLOCKED\"}")

    result = _run_with_activation_configuration(
        configuration_reader=_ActivationConfigurationReader(_activation_configuration(mode)),
        environment_reader=_EnvironmentReader(_DIRECTORY), credential_reader=credentials, launcher=launcher,
    )
    assert result == (1, "{\"launcher_result\":\"BLOCKED\"}")
    assert _gate_values(received[0]) == expected
    assert credentials.calls == []


def test_controlled_workload_wires_deferred_credential_bridge_and_passes_launcher_tuple() -> None:
    credentials = _CredentialReader()
    received: list[object] = []

    def launcher(**kwargs: object) -> tuple[int, str]:
        received.append(kwargs["gates"])
        dependencies = kwargs["dependencies"]
        assert dependencies.credential_reader(_DIRECTORY, _NAME) == _CREDENTIAL
        return (7, "{\"launcher_result\":\"CONTROLLED_NON_SUCCESS\"}")

    result = _run_with_activation_configuration(
        configuration_reader=_ActivationConfigurationReader(_activation_configuration("CONTROLLED_WORKLOAD")),
        environment_reader=_EnvironmentReader(_DIRECTORY), credential_reader=credentials, launcher=launcher,
    )
    assert result == (7, "{\"launcher_result\":\"CONTROLLED_NON_SUCCESS\"}")
    assert _gate_values(received[0]) == (True, True, True, True, True)
    assert credentials.calls == [(_DIRECTORY, _NAME)]


def test_locator_failure_occurs_only_after_valid_configuration_loading() -> None:
    configuration_reader = _ActivationConfigurationReader(_activation_configuration("CLOSED"))
    credentials = _CredentialReader()
    calls: list[object] = []
    result = _run_with_activation_configuration(
        configuration_reader=configuration_reader, environment_reader=_EnvironmentReader(None),
        credential_reader=credentials, launcher=lambda **_: calls.append(True),
    )
    assert result == (1, _LOCATOR_FAILURE_JSON)
    assert configuration_reader.calls == [(_ACTIVATION_CONFIGURATION_PATH, _CONFIGURATION_NOW)]
    assert credentials.calls == [] and calls == []


def test_activation_integration_source_has_fixed_path_default_reader_and_no_configuration_environment() -> None:
    source = inspect.getsource(module)
    assert _ACTIVATION_CONFIGURATION_PATH in source
    assert "load_phase_12_activation_configuration" in source
    assert "PHASE12_ACTIVATION_CONFIG" not in source
    assert "EnvironmentFile" not in source
    assert "ACTIVATION_CONFIGURATION=" not in source
    assert "os.environ.get(_DIRECTORY_KEY)" in source
    assert not any(value in source for value in (
        "PHASE12_ACTIVATION_CONFIG", "ACTIVATION_CONFIGURATION=", "os.getenv",
        "os.environ.items", "os.environ.keys", "os.environ.values",
        "configuration_path=sys.argv", "configuration_path = sys.argv",
    ))
    assert "systemctl" not in source
    assert not any(value in source for value in ("socket", "requests", "httpx", "subprocess", "logging"))
