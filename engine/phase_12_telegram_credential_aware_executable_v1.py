"""Fail-closed executable boundary for a systemd-supplied Telegram credential."""
from __future__ import annotations

import json
import os
import posixpath
import sys
from collections.abc import Callable

from engine.phase_12_telegram_production_launcher_v1 import (
    TelegramCredentialSourceMetadataV1,
    TelegramLauncherDependenciesV1,
    TelegramProductionGateStateV1,
    TelegramProductionLauncherPolicyV1,
    TelegramProductionRuntimeConfigurationV1,
    prepare_telegram_production_launcher_v1,
)
from engine.systemd_telegram_credential_reader_v1 import (
    SystemdTelegramCredentialErrorV1,
    read_systemd_telegram_credential,
)


_DIRECTORY_KEY = "CREDENTIALS_DIRECTORY"
_CREDENTIAL_NAME = "telegram_bot_token"
_MISUSE_JSON = '{"executable_result":"MISUSE"}'
_LOCATOR_FAILURE_JSON = '{"executable_result":"CREDENTIAL_LOCATOR_FAILURE"}'
_UNEXPECTED_JSON = '{"executable_result":"UNEXPECTED_FAILURE"}'


def _compact_result(value: str) -> str:
    return json.dumps({"launcher_result": value}, separators=(",", ":"))


def _locator_is_valid(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and "\x00" not in value
        and posixpath.isabs(value)
        and value != "/"
        and posixpath.normpath(value) == value
        and all(component not in (".", "..") for component in value.split("/"))
    )


def _safe_reader_failure() -> SystemdTelegramCredentialErrorV1:
    return SystemdTelegramCredentialErrorV1("CREDENTIAL_READ_FAILED")


def _invoke_credential_reader(
    reader: Callable[..., object], directory: str, name: str
) -> str:
    if reader is read_systemd_telegram_credential:
        value = reader(credential_directory=directory, credential_name=name)
    else:
        value = reader(directory, name)
    if type(value) is not str:
        raise _safe_reader_failure()
    return value


def _credential_bridge(
    *, directory: str, reader: Callable[..., object]
) -> Callable[[str, str], str]:
    unread = object()
    cached_value: object = unread
    cached_failure: SystemdTelegramCredentialErrorV1 | None = None

    def bridge(selected_directory: str, selected_name: str) -> str:
        nonlocal cached_value, cached_failure
        if selected_directory != directory or selected_name != _CREDENTIAL_NAME:
            raise _safe_reader_failure()
        if cached_failure is not None:
            raise cached_failure
        if cached_value is not unread:
            return cached_value  # type: ignore[return-value]
        try:
            value = _invoke_credential_reader(reader, selected_directory, selected_name)
        except SystemdTelegramCredentialErrorV1 as error:
            cached_failure = error
            raise
        except Exception:
            cached_failure = _safe_reader_failure()
            raise cached_failure from None
        cached_value = value
        return value

    return bridge


def _no_action(*_: object, **__: object) -> None:
    return None


def _zero() -> int:
    return 0


def _reservation() -> str:
    return ""


def run_phase_12_telegram_production_launcher(
    *, dependencies: TelegramLauncherDependenciesV1, credential_directory: str
) -> tuple[int, str]:
    """Bind existing launcher preparation behind permanently closed execution gates."""
    result = prepare_telegram_production_launcher_v1(
        policy=TelegramProductionLauncherPolicyV1(
            launcher_implementation_authorized=True,
            execution_authorized=False,
            fail_closed=True,
        ),
        configuration=TelegramProductionRuntimeConfigurationV1(
            bot_username=None,
            quota_limit=1,
            slot_capacity=1,
            window_id="phase-12-systemd-credential",
            quota_state_path="/var/lib/ai-crypto-signal-agent/phase-12-quota.json",
            worker_state_path="/var/lib/ai-crypto-signal-agent/phase-12-worker.json",
            max_response_chars=64,
            expected_credential_filename=_CREDENTIAL_NAME,
            expected_credential_directory_classification="SYSTEMD_CREDENTIALS",
        ),
        gates=TelegramProductionGateStateV1(
            activation_gate_open=False,
            credential_gate_open=False,
            network_gate_open=False,
            workload_gate_open=False,
            telegram_start_authorized=False,
        ),
        credential_source=TelegramCredentialSourceMetadataV1(
            credential_directory=credential_directory,
            directory_classification="SYSTEMD_CREDENTIALS",
            credential_filename=_CREDENTIAL_NAME,
        ),
        dependencies=dependencies,
    )
    return (0 if result.prepared else 1, _compact_result("PREPARED" if result.prepared else "BLOCKED"))


def run_phase_12_telegram_credential_aware_executable(
    *,
    environment_reader,
    credential_reader=read_systemd_telegram_credential,
    launcher=run_phase_12_telegram_production_launcher,
) -> tuple[int, str]:
    """Prepare one credential-aware launcher boundary without process activation."""
    try:
        directory = environment_reader(_DIRECTORY_KEY)
    except Exception:
        return (1, _LOCATOR_FAILURE_JSON)
    if not _locator_is_valid(directory):
        return (1, _LOCATOR_FAILURE_JSON)

    bridge = _credential_bridge(directory=directory, reader=credential_reader)
    dependencies = TelegramLauncherDependenciesV1(
        credential_reader=bridge,
        sender=_no_action,
        worker=_no_action,
        quota_now_provider=_zero,
        reservation_id_provider=_reservation,
    )
    try:
        result = launcher(dependencies=dependencies, credential_directory=directory)
    except Exception:
        return (70, _UNEXPECTED_JSON)
    if (
        not isinstance(result, tuple)
        or len(result) != 2
        or type(result[0]) is not int
        or type(result[1]) is not str
        or "\n" in result[1]
    ):
        return (70, _UNEXPECTED_JSON)
    return result


def _environment_metadata(name: str) -> object:
    if name != _DIRECTORY_KEY:
        raise ValueError("INVALID_METADATA_KEY")
    return os.environ.get(_DIRECTORY_KEY)


def main() -> int:
    """Provide the zero-argument executable boundary."""
    if len(sys.argv) != 1:
        sys.stdout.write(_MISUSE_JSON + "\n")
        return 2
    exit_code, rendered = run_phase_12_telegram_credential_aware_executable(
        environment_reader=_environment_metadata,
    )
    sys.stdout.write(rendered + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
