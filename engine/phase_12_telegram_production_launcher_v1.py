"""Fail-closed, non-executing Phase 12 Telegram launcher preparation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from engine.telegram_runtime_v4 import TelegramRuntimeConfig, build_telegram_runtime
from engine.telegram_sdk_runner_v4 import build_runtime_sdk_runner_v4


_STATE_ROOT = "/var/lib/ai-crypto-signal-agent/"
_CREDENTIAL_FILENAME = "telegram_bot_token"
_TRUNCATION_MARKER_LENGTH = len("\n[truncated]")
_FAILURE_ORDER = (
    "POLICY_INVALID",
    "IMPLEMENTATION_NOT_AUTHORIZED",
    "ACTIVATION_GATE_CLOSED",
    "CREDENTIAL_GATE_CLOSED",
    "NETWORK_GATE_CLOSED",
    "WORKLOAD_GATE_CLOSED",
    "TELEGRAM_START_NOT_AUTHORIZED",
    "CREDENTIAL_DIRECTORY_INVALID",
    "CREDENTIAL_FILENAME_MISMATCH",
    "CREDENTIAL_READER_INVALID",
    "CREDENTIAL_VALUE_INVALID",
    "BOT_USERNAME_INVALID",
    "QUOTA_LIMIT_INVALID",
    "SLOT_CAPACITY_INVALID",
    "WINDOW_ID_INVALID",
    "QUOTA_STATE_PATH_INVALID",
    "WORKER_STATE_PATH_INVALID",
    "MAX_RESPONSE_CHARS_INVALID",
    "DEPENDENCY_INVALID",
    "COMPOSITION_FAILED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "INVALID_STATE_TRANSITION",
)


class TelegramShutdownStateV1(str, Enum):
    """Pure lifecycle classifications; none cause process actions."""

    NOT_STARTED = "NOT_STARTED"
    PREPARED = "PREPARED"
    SHUTDOWN_REQUESTED = "SHUTDOWN_REQUESTED"
    GRACEFUL_SHUTDOWN_COMPLETE = "GRACEFUL_SHUTDOWN_COMPLETE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class TelegramProductionLauncherPolicyV1:
    launcher_implementation_authorized: bool
    execution_authorized: bool = False
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class TelegramProductionRuntimeConfigurationV1:
    """Caller-supplied, non-secret configuration only."""

    bot_username: str | None
    quota_limit: int
    slot_capacity: int
    window_id: str
    quota_state_path: str
    worker_state_path: str
    max_response_chars: int
    expected_credential_filename: str
    expected_credential_directory_classification: str


@dataclass(frozen=True, slots=True)
class TelegramProductionGateStateV1:
    activation_gate_open: object
    credential_gate_open: object
    network_gate_open: object
    workload_gate_open: object
    telegram_start_authorized: object


@dataclass(frozen=True, slots=True)
class TelegramCredentialSourceMetadataV1:
    """Metadata for the systemd credential directory, never its content."""

    credential_directory: str
    directory_classification: str
    credential_filename: str


@dataclass(frozen=True, slots=True)
class TelegramLauncherDependenciesV1:
    credential_reader: Callable[..., object] = field(repr=False)
    sender: Callable[..., object] = field(repr=False)
    worker: Callable[..., object] = field(repr=False)
    quota_now_provider: Callable[..., object] = field(repr=False)
    reservation_id_provider: Callable[..., object] = field(repr=False)
    sdk_runner_builder: Callable[..., object] = field(
        default=build_runtime_sdk_runner_v4,
        repr=False,
    )
    runtime_builder: Callable[..., object] = field(
        default=build_telegram_runtime,
        repr=False,
    )


@dataclass(frozen=True, slots=True)
class TelegramSanitizedAuditEvidenceV1:
    policy_valid: bool
    gate_state: TelegramShutdownStateV1
    credential_filename: str | None
    credential_directory_classification: str | None
    failure_codes: tuple[str, ...]
    runtime_prepared: bool
    sdk_runner_prepared: bool
    execution_performed: bool
    polling_started: bool
    worker_invoked: bool
    network_accessed: bool


@dataclass(frozen=True, slots=True)
class TelegramProductionLaunchResultV1:
    prepared: bool
    shutdown_state: TelegramShutdownStateV1
    failure_codes: tuple[str, ...]
    audit_evidence: TelegramSanitizedAuditEvidenceV1
    runtime_prepared: bool
    sdk_runner_prepared: bool
    execution_performed: bool = False
    polling_started: bool = False
    worker_invoked: bool = False
    network_accessed: bool = False


@dataclass(frozen=True, slots=True)
class TelegramShutdownClassificationV1:
    state: TelegramShutdownStateV1
    transition_valid: bool
    failure_codes: tuple[str, ...] = ()


def prepare_telegram_production_launcher_v1(
    *,
    policy: TelegramProductionLauncherPolicyV1,
    configuration: TelegramProductionRuntimeConfigurationV1,
    gates: TelegramProductionGateStateV1,
    credential_source: TelegramCredentialSourceMetadataV1,
    dependencies: TelegramLauncherDependenciesV1,
) -> TelegramProductionLaunchResultV1:
    """Prepare Phase 05 composition only; polling and runtime execution are absent."""

    failures = _validate_before_credential_read(
        policy=policy,
        configuration=configuration,
        gates=gates,
        credential_source=credential_source,
        dependencies=dependencies,
    )
    if failures:
        return _failure_result(
            failures,
            credential_source=credential_source,
            policy_valid=_policy_is_valid(policy),
        )

    try:
        token = dependencies.credential_reader(
            credential_source.credential_directory,
            credential_source.credential_filename,
        )
    except Exception:
        return _failure_result(
            ("COMPOSITION_FAILED",),
            credential_source=credential_source,
            policy_valid=True,
        )
    if not isinstance(token, str) or not token.strip():
        return _failure_result(
            ("CREDENTIAL_VALUE_INVALID",),
            credential_source=credential_source,
            policy_valid=True,
        )

    try:
        runtime_config = TelegramRuntimeConfig(
            bot_token=token,
            bot_username=configuration.bot_username,
            quota_limit=configuration.quota_limit,
            slot_capacity=configuration.slot_capacity,
            window_id=configuration.window_id,
            quota_state_path=configuration.quota_state_path,
            worker_state_path=configuration.worker_state_path,
            max_response_chars=configuration.max_response_chars,
        )
        runtime = dependencies.runtime_builder(
            runtime_config,
            sender=dependencies.sender,
            worker=dependencies.worker,
            quota_now_provider=dependencies.quota_now_provider,
            reservation_id_provider=dependencies.reservation_id_provider,
        )
        dependencies.sdk_runner_builder(runtime=runtime)
    except Exception:
        return _failure_result(
            ("COMPOSITION_FAILED",),
            credential_source=credential_source,
            policy_valid=True,
        )

    evidence = TelegramSanitizedAuditEvidenceV1(
        policy_valid=True,
        gate_state=TelegramShutdownStateV1.PREPARED,
        credential_filename=credential_source.credential_filename,
        credential_directory_classification=credential_source.directory_classification,
        failure_codes=(),
        runtime_prepared=True,
        sdk_runner_prepared=True,
        execution_performed=False,
        polling_started=False,
        worker_invoked=False,
        network_accessed=False,
    )
    return TelegramProductionLaunchResultV1(
        prepared=True,
        shutdown_state=TelegramShutdownStateV1.PREPARED,
        failure_codes=(),
        audit_evidence=evidence,
        runtime_prepared=True,
        sdk_runner_prepared=True,
    )


def transition_telegram_shutdown_v1(
    *, current: TelegramShutdownStateV1, target: TelegramShutdownStateV1
) -> TelegramShutdownClassificationV1:
    """Classify a shutdown transition without touching a runtime or process."""

    allowed = {
        (TelegramShutdownStateV1.NOT_STARTED, TelegramShutdownStateV1.PREPARED),
        (TelegramShutdownStateV1.PREPARED, TelegramShutdownStateV1.SHUTDOWN_REQUESTED),
        (
            TelegramShutdownStateV1.SHUTDOWN_REQUESTED,
            TelegramShutdownStateV1.GRACEFUL_SHUTDOWN_COMPLETE,
        ),
    }
    if (current, target) in allowed:
        return TelegramShutdownClassificationV1(target, True)
    return TelegramShutdownClassificationV1(
        TelegramShutdownStateV1.BLOCKED,
        False,
        ("INVALID_STATE_TRANSITION",),
    )


def _validate_before_credential_read(
    *,
    policy: TelegramProductionLauncherPolicyV1,
    configuration: TelegramProductionRuntimeConfigurationV1,
    gates: TelegramProductionGateStateV1,
    credential_source: TelegramCredentialSourceMetadataV1,
    dependencies: TelegramLauncherDependenciesV1,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not _policy_is_valid(policy):
        failures.append("POLICY_INVALID")
    if not isinstance(policy, TelegramProductionLauncherPolicyV1) or (
        policy.launcher_implementation_authorized is not True
    ):
        failures.append("IMPLEMENTATION_NOT_AUTHORIZED")
    if not isinstance(gates, TelegramProductionGateStateV1):
        failures.extend(
            (
                "ACTIVATION_GATE_CLOSED",
                "CREDENTIAL_GATE_CLOSED",
                "NETWORK_GATE_CLOSED",
                "WORKLOAD_GATE_CLOSED",
                "TELEGRAM_START_NOT_AUTHORIZED",
            )
        )
    else:
        for field_name, code in (
            ("activation_gate_open", "ACTIVATION_GATE_CLOSED"),
            ("credential_gate_open", "CREDENTIAL_GATE_CLOSED"),
            ("network_gate_open", "NETWORK_GATE_CLOSED"),
            ("workload_gate_open", "WORKLOAD_GATE_CLOSED"),
            ("telegram_start_authorized", "TELEGRAM_START_NOT_AUTHORIZED"),
        ):
            if getattr(gates, field_name) is not True:
                failures.append(code)
    failures.extend(_configuration_failures(configuration))
    failures.extend(_credential_source_failures(configuration, credential_source))
    failures.extend(_dependency_failures(dependencies))
    return _ordered_failures(failures)


def _policy_is_valid(policy: object) -> bool:
    return (
        isinstance(policy, TelegramProductionLauncherPolicyV1)
        and policy.launcher_implementation_authorized is True
        and policy.execution_authorized is False
        and policy.fail_closed is True
    )


def _configuration_failures(
    configuration: object,
) -> tuple[str, ...]:
    if not isinstance(configuration, TelegramProductionRuntimeConfigurationV1):
        return (
            "BOT_USERNAME_INVALID",
            "QUOTA_LIMIT_INVALID",
            "SLOT_CAPACITY_INVALID",
            "WINDOW_ID_INVALID",
            "QUOTA_STATE_PATH_INVALID",
            "WORKER_STATE_PATH_INVALID",
            "MAX_RESPONSE_CHARS_INVALID",
            "CREDENTIAL_FILENAME_MISMATCH",
            "CREDENTIAL_DIRECTORY_INVALID",
        )
    failures: list[str] = []
    if configuration.bot_username is not None and (
        not isinstance(configuration.bot_username, str)
        or not configuration.bot_username.strip()
    ):
        failures.append("BOT_USERNAME_INVALID")
    if not _positive_integer(configuration.quota_limit):
        failures.append("QUOTA_LIMIT_INVALID")
    if not _positive_integer(configuration.slot_capacity):
        failures.append("SLOT_CAPACITY_INVALID")
    if not _nonblank_string(configuration.window_id):
        failures.append("WINDOW_ID_INVALID")
    if not _valid_state_path(configuration.quota_state_path):
        failures.append("QUOTA_STATE_PATH_INVALID")
    if not _valid_state_path(configuration.worker_state_path):
        failures.append("WORKER_STATE_PATH_INVALID")
    if (
        type(configuration.max_response_chars) is not int
        or configuration.max_response_chars <= _TRUNCATION_MARKER_LENGTH
    ):
        failures.append("MAX_RESPONSE_CHARS_INVALID")
    if configuration.expected_credential_filename != _CREDENTIAL_FILENAME:
        failures.append("CREDENTIAL_FILENAME_MISMATCH")
    if not _nonblank_string(configuration.expected_credential_directory_classification):
        failures.append("CREDENTIAL_DIRECTORY_INVALID")
    return tuple(failures)


def _credential_source_failures(
    configuration: object, credential_source: object
) -> tuple[str, ...]:
    if not isinstance(credential_source, TelegramCredentialSourceMetadataV1):
        return ("CREDENTIAL_DIRECTORY_INVALID",)
    failures: list[str] = []
    if not _valid_credential_directory(credential_source.credential_directory):
        failures.append("CREDENTIAL_DIRECTORY_INVALID")
    expected_classification = getattr(
        configuration,
        "expected_credential_directory_classification",
        None,
    )
    if credential_source.directory_classification != expected_classification:
        failures.append("CREDENTIAL_DIRECTORY_INVALID")
    if credential_source.credential_filename != _CREDENTIAL_FILENAME or (
        credential_source.credential_filename
        != getattr(configuration, "expected_credential_filename", None)
    ):
        failures.append("CREDENTIAL_FILENAME_MISMATCH")
    return tuple(failures)


def _dependency_failures(dependencies: object) -> tuple[str, ...]:
    if not isinstance(dependencies, TelegramLauncherDependenciesV1):
        return ("DEPENDENCY_INVALID",)
    if not callable(dependencies.credential_reader):
        return ("CREDENTIAL_READER_INVALID",)
    if not all(
        callable(value)
        for value in (
            dependencies.sender,
            dependencies.worker,
            dependencies.quota_now_provider,
            dependencies.reservation_id_provider,
            dependencies.sdk_runner_builder,
            dependencies.runtime_builder,
        )
    ):
        return ("DEPENDENCY_INVALID",)
    return ()


def _valid_state_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(_STATE_ROOT)
        and value != _STATE_ROOT
        and ".." not in value.split("/")
        and "//" not in value
    )


def _valid_credential_directory(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("/")
        and value != "/"
        and ".." not in value.split("/")
        and "//" not in value
    )


def _positive_integer(value: object) -> bool:
    return type(value) is int and value > 0


def _nonblank_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _ordered_failures(failures: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    present = set(failures)
    return tuple(code for code in _FAILURE_ORDER if code in present)


def _failure_result(
    failures: tuple[str, ...],
    *,
    credential_source: object,
    policy_valid: bool,
) -> TelegramProductionLaunchResultV1:
    ordered = _ordered_failures(failures)
    filename = getattr(credential_source, "credential_filename", None)
    classification = getattr(credential_source, "directory_classification", None)
    evidence = TelegramSanitizedAuditEvidenceV1(
        policy_valid=policy_valid,
        gate_state=TelegramShutdownStateV1.BLOCKED,
        credential_filename=filename if filename == _CREDENTIAL_FILENAME else None,
        credential_directory_classification=(
            classification if _nonblank_string(classification) else None
        ),
        failure_codes=ordered,
        runtime_prepared=False,
        sdk_runner_prepared=False,
        execution_performed=False,
        polling_started=False,
        worker_invoked=False,
        network_accessed=False,
    )
    return TelegramProductionLaunchResultV1(
        prepared=False,
        shutdown_state=TelegramShutdownStateV1.BLOCKED,
        failure_codes=ordered,
        audit_evidence=evidence,
        runtime_prepared=False,
        sdk_runner_prepared=False,
    )
