"""Fail-closed executable boundary for a systemd-supplied Telegram credential."""
from __future__ import annotations

import json
import os
import posixpath
import sys
from datetime import datetime, timezone
from collections.abc import Callable

from engine.phase_12_activation_configuration_v1 import (
    Phase12ActivationConfigurationErrorV1,
    load_phase_12_activation_configuration,
)
from engine.phase_12_activation_mode_validation_coordinator_v1 import (
    run_phase_12_activation_mode_validation_coordinator,
)
from engine.phase_12_activation_mode_authorization_verifier_v1 import (
    Phase12ActivationModeAuthorizationVerifierV1,
)
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
_ACTIVATION_CONFIGURATION_PATH = "/etc/ai-crypto-signal-agent/phase12-activation-v1.conf"
_ACCEPTED_LOCKED_COMMIT = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_NON_CLOSED_MODES = frozenset((
    "CREDENTIAL_VALIDATION",
    "TELEGRAM_CONNECTIVITY_VALIDATION",
    "TELEGRAM_START_VALIDATION",
    "CONTROLLED_WORKLOAD",
))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


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


def _authorization_rejected(**_: object) -> bool:
    return False


_EMPTY_AUTHORIZATION_VERIFIER = Phase12ActivationModeAuthorizationVerifierV1(records=())


def _credential_lexically_valid(*, credential: object) -> bool:
    return isinstance(credential, str) and bool(credential)


def _no_identity_client(**_: object) -> None:
    return None


def _no_identity_probe(**_: object) -> bool:
    return False


def _no_application_initializer(**_: object) -> None:
    return None


def _no_launcher() -> tuple[int, str]:
    return (70, _UNEXPECTED_JSON)


def run_phase_12_telegram_production_launcher(
    *, dependencies: TelegramLauncherDependenciesV1, credential_directory: str, gates: TelegramProductionGateStateV1
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
        gates=gates,
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
    configuration_reader=load_phase_12_activation_configuration,
    now_utc_provider=_now_utc,
    credential_reader=read_systemd_telegram_credential,
    launcher=run_phase_12_telegram_production_launcher,
    coordinator=run_phase_12_activation_mode_validation_coordinator,
    accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT,
    authorization_verifier=_EMPTY_AUTHORIZATION_VERIFIER,
    credential_validator=_credential_lexically_valid,
    identity_probe_client_factory=_no_identity_client,
    authenticated_identity_probe=_no_identity_probe,
    application_initializer=_no_application_initializer,
    application_shutdown=_no_action,
) -> tuple[int, str]:
    """Dispatch one validated activation mode through the bounded coordinator."""
    try:
        now_utc = now_utc_provider()
        configuration = configuration_reader(
            configuration_path=_ACTIVATION_CONFIGURATION_PATH, now_utc=now_utc
        )
    except Phase12ActivationConfigurationErrorV1:
        return (1, '{"executable_result":"ACTIVATION_CONFIGURATION_FAILURE"}')
    except Exception:
        return (70, _UNEXPECTED_JSON)

    mode = getattr(configuration, "activation_mode", None)
    credential_locator = _no_identity_client
    deferred_credential_reader = _no_identity_client
    production_launcher = _no_launcher

    if mode in _NON_CLOSED_MODES:
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

        def credential_locator() -> str:
            return directory

        def deferred_credential_reader(*, locator: object) -> str:
            if locator != directory:
                raise _safe_reader_failure()
            return bridge(directory, _CREDENTIAL_NAME)

        def production_launcher() -> tuple[int, str]:
            return launcher(
                dependencies=dependencies,
                credential_directory=directory,
                gates=TelegramProductionGateStateV1(
                    activation_gate_open=configuration.activation_gate_open,
                    credential_gate_open=configuration.credential_gate_open,
                    network_gate_open=configuration.network_gate_open,
                    workload_gate_open=configuration.workload_gate_open,
                    telegram_start_authorized=configuration.telegram_start_authorized,
                ),
            )

    try:
        return coordinator(
            configuration=configuration,
            accepted_locked_commit=accepted_locked_commit,
            now_utc=now_utc,
            authorization_verifier=authorization_verifier,
            credential_locator=credential_locator,
            credential_reader=deferred_credential_reader,
            credential_validator=credential_validator,
            identity_probe_client_factory=identity_probe_client_factory,
            authenticated_identity_probe=authenticated_identity_probe,
            application_initializer=application_initializer,
            application_shutdown=application_shutdown,
            production_launcher=production_launcher,
        )
    except Exception:
        return (70, _UNEXPECTED_JSON)


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
