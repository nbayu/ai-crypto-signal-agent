"""RED contract for the Phase 12 systemd-credential executable boundary."""
from __future__ import annotations

import ast
import inspect
import json
import logging
from collections.abc import Callable

import pytest

import engine.phase_12_telegram_credential_aware_executable_v1 as module
from engine.phase_12_telegram_credential_aware_executable_v1 import (
    main,
    run_phase_12_telegram_credential_aware_executable,
)
from engine.phase_12_telegram_production_launcher_v1 import TelegramLauncherDependenciesV1
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
    assert tuple(signature.parameters) == ("environment_reader", "credential_reader", "launcher")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert signature.parameters["environment_reader"].default is inspect.Parameter.empty
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
    result = run_phase_12_telegram_credential_aware_executable(
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
    result = run_phase_12_telegram_credential_aware_executable(
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
    result = run_phase_12_telegram_credential_aware_executable(
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
    result = run_phase_12_telegram_credential_aware_executable(
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
    result = run_phase_12_telegram_credential_aware_executable(
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
    assert run_phase_12_telegram_credential_aware_executable(
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

    result = run_phase_12_telegram_credential_aware_executable(
        environment_reader=environment, credential_reader=reader, launcher=launcher
    )
    assert result == (1, '{"launcher_result":"CREDENTIAL_FAILURE"}')
    assert effects == ["launcher-after-reader"]
    assert reader.calls == [(_DIRECTORY, _NAME)]


def test_launcher_result_is_compact_deterministic_and_has_no_public_newline() -> None:
    environment = _EnvironmentReader(_DIRECTORY)
    reader = _CredentialReader()
    expected = '{"launcher_result":"CONTROLLED_NON_SUCCESS","detail":"SANITIZED"}'
    result = run_phase_12_telegram_credential_aware_executable(
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
    unexpected = run_phase_12_telegram_credential_aware_executable(
        environment_reader=environment,
        credential_reader=reader,
        launcher=lambda **_: (_ for _ in ()).throw(RuntimeError(_CREDENTIAL)),
    )
    assert unexpected == (70, _UNEXPECTED_JSON)
    assert _CREDENTIAL not in unexpected[1]
    interruption = KeyboardInterrupt("fixture interruption")
    with pytest.raises(KeyboardInterrupt) as raised:
        run_phase_12_telegram_credential_aware_executable(
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
    result = run_phase_12_telegram_credential_aware_executable(
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
        "/etc/credstore.encrypted", ".token", ".credential",
    ):
        assert forbidden not in source
    assert "CREDENTIALS_DIRECTORY" in source
    assert "environ" not in source or "CREDENTIALS_DIRECTORY" in source
    assert _CREDENTIAL not in source


def test_module_has_no_direct_sdk_or_unsafe_public_surface() -> None:
    public = {name for name in module.__dict__ if not name.startswith("_")}
    assert not public.intersection({"Bot", "HTTPXRequest", "getpass", "socket", "subprocess", "requests"})
    assert callable(run_phase_12_telegram_credential_aware_executable)
    assert callable(main)
