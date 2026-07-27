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


def test_public_api_exposes_exact_keyword_only_coordinator_dispatch_seams() -> None:
    signature = inspect.signature(run_phase_12_telegram_credential_aware_executable)
    assert tuple(signature.parameters) == (
        "environment_reader", "configuration_reader", "now_utc_provider",
        "credential_reader", "launcher", "coordinator", "accepted_locked_commit",
        "authorization_verifier", "credential_validator",
        "identity_probe_client_factory", "authenticated_identity_probe",
        "application_initializer", "application_shutdown",
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
    assert callable(signature.parameters["coordinator"].default)
    assert inspect.signature(main).parameters == {}
    assert "tuple" in str(signature.return_annotation)
    assert "int" in str(inspect.signature(main).return_annotation)
    source = inspect.getsource(module)
    assert "phase_12_activation_mode_validation_coordinator_v1" in source
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


def test_non_closed_invalid_locator_fails_before_coordinator_or_launcher() -> None:
    coordinator = _Coordinator((0, "{\"activation_mode_validation_result\":\"CREDENTIAL_VALID\"}"))
    environment = _EnvironmentReader(None)
    result = _run_with_coordinator(
        configuration=_activation_configuration("CREDENTIAL_VALIDATION"),
        coordinator=coordinator,
        environment_reader=environment,
    )
    assert result == (1, _LOCATOR_FAILURE_JSON)
    assert environment.calls == ["CREDENTIALS_DIRECTORY"]
    assert coordinator.calls == []


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


_ACCEPTED_LOCKED_COMMIT = "e50041f7296bd9e042f749b6a98393b3df9747a1"


class _Coordinator:
    def __init__(self, result: tuple[int, str] | BaseException) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> tuple[int, str]:
        self.calls.append(kwargs)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _run_with_coordinator(
    *,
    configuration: Phase12ActivationConfigurationV1,
    coordinator: _Coordinator,
    environment_reader: _EnvironmentReader,
    launcher: Callable[..., tuple[int, str]] = lambda **_: (_ for _ in ()).throw(
        AssertionError("the executable must not call the production launcher directly")
    ),
) -> tuple[int, str]:
    return run_phase_12_telegram_credential_aware_executable(
        environment_reader=environment_reader,
        configuration_reader=_ActivationConfigurationReader(configuration),
        now_utc_provider=lambda: _CONFIGURATION_NOW,
        credential_reader=_CredentialReader(),
        launcher=launcher,
        coordinator=coordinator,
        accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT,
        authorization_verifier=lambda **_: True,
        credential_validator=lambda **_: True,
        identity_probe_client_factory=lambda **_: object(),
        authenticated_identity_probe=lambda **_: True,
        application_initializer=lambda **_: object(),
        application_shutdown=lambda **_: None,
    )


def test_executable_source_requires_coordinator_without_new_environment_or_argv_surface() -> None:
    source = inspect.getsource(module)
    assert "phase_12_activation_mode_validation_coordinator_v1" in source
    assert "PHASE12_ACTIVATION_CONFIG" not in source
    assert "os.getenv" not in source
    assert "os.environ.items" not in source
    assert "configuration_path=sys.argv" not in source


def test_closed_dispatches_once_before_locator_or_launcher_and_passes_result_through() -> None:
    events: list[str] = []
    coordinator = _Coordinator((1, "{\"launcher_result\":\"BLOCKED\"}"))

    class Environment(_EnvironmentReader):
        def __call__(self, name: str) -> object:
            events.append("locator")
            return super().__call__(name)

    result = _run_with_coordinator(
        configuration=_activation_configuration("CLOSED"),
        coordinator=coordinator,
        environment_reader=Environment(_DIRECTORY),
    )
    assert result == (1, "{\"launcher_result\":\"BLOCKED\"}")
    assert events == []
    assert len(coordinator.calls) == 1
    received = coordinator.calls[0]
    assert received["configuration"] == _activation_configuration("CLOSED")
    assert received["accepted_locked_commit"] == _ACCEPTED_LOCKED_COMMIT


@pytest.mark.parametrize(
    ("mode", "result"),
    (
        ("CREDENTIAL_VALIDATION", (0, "{\"activation_mode_validation_result\":\"CREDENTIAL_VALID\"}")),
        ("TELEGRAM_CONNECTIVITY_VALIDATION", (0, "{\"activation_mode_validation_result\":\"TELEGRAM_CONNECTIVITY_VALID\"}")),
        ("TELEGRAM_START_VALIDATION", (0, "{\"activation_mode_validation_result\":\"TELEGRAM_START_VALID\"}")),
    ),
)
def test_partial_modes_dispatch_once_to_coordinator_and_never_directly_to_launcher(
    mode: str, result: tuple[int, str]
) -> None:
    coordinator = _Coordinator(result)
    assert _run_with_coordinator(
        configuration=_activation_configuration(mode),
        coordinator=coordinator,
        environment_reader=_EnvironmentReader(_DIRECTORY),
    ) == result
    assert len(coordinator.calls) == 1
    received = coordinator.calls[0]
    assert received["configuration"].activation_mode == mode
    assert received["accepted_locked_commit"] == _ACCEPTED_LOCKED_COMMIT
    for required in (
        "authorization_verifier", "credential_locator", "credential_reader",
        "credential_validator", "identity_probe_client_factory", "authenticated_identity_probe",
        "application_initializer", "application_shutdown", "production_launcher",
    ):
        assert callable(received[required])


def test_coordinator_authorization_and_controlled_mode_results_pass_through_unchanged() -> None:
    authorization = _Coordinator((1, "{\"executable_result\":\"ACTIVATION_MODE_AUTHORIZATION_FAILURE\"}"))
    assert _run_with_coordinator(
        configuration=_activation_configuration("CREDENTIAL_VALIDATION"),
        coordinator=authorization,
        environment_reader=_EnvironmentReader(_DIRECTORY),
    ) == (1, "{\"executable_result\":\"ACTIVATION_MODE_AUTHORIZATION_FAILURE\"}")
    workload = _Coordinator((7, "{\"launcher_result\":\"CONTROLLED_NON_SUCCESS\"}"))
    assert _run_with_coordinator(
        configuration=_activation_configuration("CONTROLLED_WORKLOAD"),
        coordinator=workload,
        environment_reader=_EnvironmentReader(_DIRECTORY),
    ) == (7, "{\"launcher_result\":\"CONTROLLED_NON_SUCCESS\"}")
    assert len(authorization.calls) == len(workload.calls) == 1


def test_coordinator_ordinary_exception_is_sanitized_and_baseexception_propagates() -> None:
    ordinary = _Coordinator(RuntimeError("dynamic coordinator detail"))
    assert _run_with_coordinator(
        configuration=_activation_configuration("CLOSED"),
        coordinator=ordinary,
        environment_reader=_EnvironmentReader(_DIRECTORY),
    ) == (70, _UNEXPECTED_JSON)
    interruption = KeyboardInterrupt("coordinator interruption")
    with pytest.raises(KeyboardInterrupt) as raised:
        _run_with_coordinator(
            configuration=_activation_configuration("CLOSED"),
            coordinator=_Coordinator(interruption),
            environment_reader=_EnvironmentReader(_DIRECTORY),
        )
    assert raised.value is interruption


def test_configuration_failure_remains_executable_owned_before_coordinator_dispatch() -> None:
    coordinator = _Coordinator((0, "{\"activation_mode_validation_result\":\"CREDENTIAL_VALID\"}"))
    configuration_reader = _ActivationConfigurationReader(
        Phase12ActivationConfigurationErrorV1("CONFIGURATION_FORMAT_INVALID")
    )
    result = run_phase_12_telegram_credential_aware_executable(
        environment_reader=_EnvironmentReader(_DIRECTORY),
        configuration_reader=configuration_reader,
        now_utc_provider=lambda: _CONFIGURATION_NOW,
        credential_reader=_CredentialReader(),
        launcher=lambda **_: (0, "{\"launcher_result\":\"UNUSED\"}"),
        coordinator=coordinator,
        accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT,
        authorization_verifier=lambda **_: True,
        credential_validator=lambda **_: True,
        identity_probe_client_factory=lambda **_: object(),
        authenticated_identity_probe=lambda **_: True,
        application_initializer=lambda **_: object(),
        application_shutdown=lambda **_: None,
    )
    assert result == (1, "{\"executable_result\":\"ACTIVATION_CONFIGURATION_FAILURE\"}")
    assert coordinator.calls == []


def test_production_authorization_default_is_one_empty_immutable_verifier_policy() -> None:
    signature = inspect.signature(run_phase_12_telegram_credential_aware_executable)
    default = signature.parameters["authorization_verifier"].default
    source = inspect.getsource(module)
    assert "phase_12_activation_mode_authorization_verifier_v1" in source
    assert default.__class__.__name__ == "Phase12ActivationModeAuthorizationVerifierV1"
    assert default.records == ()
    assert default is not module._authorization_rejected
