"""Pure, test-only passive runtime launcher state machine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "LAUNCHER_IMPLEMENTATION_NOT_AUTHORIZED",
    "PASSIVE_TEST_EXECUTION_NOT_AUTHORIZED", "SYNTHETIC_SIGNAL_TEST_NOT_AUTHORIZED",
    "EXECUTION_MODE_MISMATCH", "SERVICE_UNIT_MISMATCH", "SERVICE_USER_MISMATCH",
    "SERVICE_GROUP_MISMATCH", "INSTALLATION_PATH_MISMATCH", "WORKING_DIRECTORY_MISMATCH",
    "PYTHON_INTERPRETER_PATH_MISMATCH", "STATE_DIRECTORY_MISMATCH", "CACHE_DIRECTORY_MISMATCH",
    "RUNTIME_DIRECTORY_MISMATCH", "LOG_DESTINATION_MISMATCH", "LOG_DIRECTORY_NOT_ALLOWED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "FILESYSTEM_READ_NOT_AUTHORIZED", "FILESYSTEM_WRITE_NOT_AUTHORIZED",
    "ENVIRONMENT_READ_NOT_AUTHORIZED", "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED",
    "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "CREDENTIAL_VALIDATION_NOT_AUTHORIZED", "SYSTEMD_ACCESS_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED",
    "TRADING_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "INVALID_STATE_TRANSITION", "UNKNOWN_SYNTHETIC_SIGNAL", "RELOAD_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_ENDPOINT_EXPOSURE_DETECTED",
    "AUTHORIZATION_MATERIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)
_STATES = (
    "CREATED", "CONFIGURATION_VALIDATED", "PASSIVE_READY", "SHUTDOWN_REQUESTED",
    "GRACEFUL_SHUTDOWN_COMPLETE", "BLOCKED",
)
_MODULE = "engine.phase_12_passive_runtime_launcher_executable_contract_v1"


class _AuthorityView:
    passive_test_execution_authorized: ClassVar[bool] = True
    synthetic_signal_tests_authorized: ClassVar[bool] = True
    launcher_implementation_authorized: ClassVar[bool] = True
    real_signal_registration_authorized: ClassVar[bool] = False
    filesystem_read_authorized: ClassVar[bool] = False
    filesystem_write_authorized: ClassVar[bool] = False
    environment_read_authorized: ClassVar[bool] = False
    credential_access_authorized: ClassVar[bool] = False
    credential_loading_authorized: ClassVar[bool] = False
    credential_validation_authorized: ClassVar[bool] = False
    systemd_access_authorized: ClassVar[bool] = False
    network_authorized: ClassVar[bool] = False
    provider_transmission_authorized: ClassVar[bool] = False
    scanner_execution_authorized: ClassVar[bool] = False
    worker_start_authorized: ClassVar[bool] = False
    scheduler_start_authorized: ClassVar[bool] = False
    telegram_start_authorized: ClassVar[bool] = False
    database_mutation_authorized: ClassVar[bool] = False
    artifact_publication_authorized: ClassVar[bool] = False
    trading_authorized: ClassVar[bool] = False
    runtime_activation_authorized: ClassVar[bool] = False
    publication_authorized: ClassVar[bool] = False
    fail_closed: ClassVar[bool] = True


@dataclass(frozen=True, slots=True, kw_only=True)
class PassiveRuntimeLauncherPolicyV1(_AuthorityView):
    policy_id: str
    policy_version: str
    launcher_module: str
    launcher_mode: str
    expected_service_unit: str
    expected_service_user: str
    expected_service_group: str
    expected_installation_path: str
    expected_working_directory: str
    expected_python_interpreter: str
    passive_test_execution_authorized: bool
    synthetic_signal_tests_authorized: bool
    launcher_implementation_authorized: bool
    real_signal_registration_authorized: bool
    filesystem_read_authorized: bool
    filesystem_write_authorized: bool
    environment_read_authorized: bool
    credential_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    systemd_access_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    scanner_execution_authorized: bool
    worker_start_authorized: bool
    scheduler_start_authorized: bool
    telegram_start_authorized: bool
    database_mutation_authorized: bool
    artifact_publication_authorized: bool
    trading_authorized: bool
    runtime_activation_authorized: bool
    publication_authorized: bool
    fail_closed: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class PassiveRuntimeLauncherConfigurationV1(_AuthorityView):
    launcher_id: str
    invocation_id: str
    execution_mode: str
    service_unit: str
    service_user: str
    service_group: str
    installation_path: str
    working_directory: str
    python_interpreter: str
    state_directory_classification: str
    cache_directory_classification: str
    runtime_directory_classification: str
    log_destination: str
    log_directory: str
    credential_gate_open: bool
    network_gate_open: bool
    workload_gate_open: bool
    activation_gate_open: bool
    credential_exposure_detected: bool
    endpoint_exposure_detected: bool
    authorization_exposure_detected: bool
    real_process_control_requested: bool
    passive_configuration_complete: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class PassiveRuntimeLauncherStateV1(_AuthorityView):
    launcher_id: str
    invocation_id: str
    state_code: str
    supported_state_codes: ClassVar[tuple[str, ...]] = _STATES


@dataclass(frozen=True, slots=True, kw_only=True)
class PassiveRuntimeLauncherTransitionV1(_AuthorityView):
    from_state: str
    to_state: str
    transition_classification: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PassiveRuntimeLauncherSyntheticSignalV1(_AuthorityView):
    signal_id: str
    signal_classification: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PassiveRuntimeLauncherShutdownRequestV1(_AuthorityView):
    request_id: str
    shutdown_classification: str


@dataclass(frozen=True, slots=True)
class PassiveRuntimeLauncherFailureV1(_AuthorityView):
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class PassiveRuntimeLauncherResultV1(_AuthorityView):
    policy_id: str
    launcher_id: str
    invocation_id: str
    ready: bool
    result_classification: str
    current_state: PassiveRuntimeLauncherStateV1
    transitions: tuple[PassiveRuntimeLauncherTransitionV1, ...]
    failure_codes: tuple[str, ...]
    failures: tuple[PassiveRuntimeLauncherFailureV1, ...]
    passive_test_execution_authorized: bool
    synthetic_signal_tests_authorized: bool
    launcher_implementation_authorized: bool
    real_signal_registration_authorized: bool
    filesystem_read_authorized: bool
    filesystem_write_authorized: bool
    environment_read_authorized: bool
    credential_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    systemd_access_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    scanner_execution_authorized: bool
    worker_start_authorized: bool
    scheduler_start_authorized: bool
    telegram_start_authorized: bool
    database_mutation_authorized: bool
    artifact_publication_authorized: bool
    trading_authorized: bool
    runtime_activation_authorized: bool
    publication_authorized: bool
    fail_closed: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class PassiveRuntimeLauncherAuditEvidenceV1(_AuthorityView):
    audit_id: str
    policy_id: str
    launcher_id: str
    invocation_id: str
    execution_mode: str
    service_unit: str
    working_directory: str
    current_state: str
    requested_transition: str
    synthetic_signal_classification: str | None
    shutdown_classification: str
    gate_states: tuple[bool, bool, bool, bool]
    failure_codes: tuple[str, ...]
    passive_test_execution_authorized: bool
    synthetic_signal_tests_authorized: bool
    launcher_implementation_authorized: bool
    real_signal_registration_authorized: bool
    filesystem_read_authorized: bool
    filesystem_write_authorized: bool
    environment_read_authorized: bool
    credential_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    systemd_access_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    scanner_execution_authorized: bool
    worker_start_authorized: bool
    scheduler_start_authorized: bool
    telegram_start_authorized: bool
    database_mutation_authorized: bool
    artifact_publication_authorized: bool
    trading_authorized: bool
    runtime_activation_authorized: bool
    publication_authorized: bool
    fail_closed: bool


def _authorities() -> dict[str, bool]:
    return {
        "passive_test_execution_authorized": True, "synthetic_signal_tests_authorized": True,
        "launcher_implementation_authorized": True, "real_signal_registration_authorized": False,
        "filesystem_read_authorized": False, "filesystem_write_authorized": False,
        "environment_read_authorized": False, "credential_access_authorized": False,
        "credential_loading_authorized": False, "credential_validation_authorized": False,
        "systemd_access_authorized": False, "network_authorized": False,
        "provider_transmission_authorized": False, "scanner_execution_authorized": False,
        "worker_start_authorized": False, "scheduler_start_authorized": False,
        "telegram_start_authorized": False, "database_mutation_authorized": False,
        "artifact_publication_authorized": False, "trading_authorized": False,
        "runtime_activation_authorized": False, "publication_authorized": False, "fail_closed": True,
    }


def _blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _failure_records(codes: tuple[str, ...]) -> tuple[PassiveRuntimeLauncherFailureV1, ...]:
    return tuple(
        PassiveRuntimeLauncherFailureV1(
            failure_code=code, safe_message="fail-closed passive launcher rejection", retryable=False,
        )
        for code in codes
    )


def _ordered(conditions: dict[str, bool]) -> tuple[str, ...]:
    return tuple(code for code in _FAILURES if conditions.get(code, False))


def _state(configuration: object, state_code: str) -> PassiveRuntimeLauncherStateV1:
    return PassiveRuntimeLauncherStateV1(
        launcher_id=getattr(configuration, "launcher_id", ""),
        invocation_id=getattr(configuration, "invocation_id", ""),
        state_code=state_code,
    )


def _transition(from_state: str, to_state: str, classification: str) -> PassiveRuntimeLauncherTransitionV1:
    return PassiveRuntimeLauncherTransitionV1(
        from_state=from_state, to_state=to_state, transition_classification=classification,
    )


def _result(
    *,
    policy: object,
    configuration: object,
    state: PassiveRuntimeLauncherStateV1,
    transitions: tuple[PassiveRuntimeLauncherTransitionV1, ...] = (),
    codes: tuple[str, ...] = (),
    classification: str = "PASSIVE_RUNTIME_LAUNCHER_READY_IN_TEST_MODE",
) -> PassiveRuntimeLauncherResultV1:
    return PassiveRuntimeLauncherResultV1(
        policy_id=getattr(policy, "policy_id", ""), launcher_id=getattr(configuration, "launcher_id", ""),
        invocation_id=getattr(configuration, "invocation_id", ""), ready=not codes,
        result_classification=(classification if not codes else "PASSIVE_RUNTIME_LAUNCHER_BLOCKED"),
        current_state=state, transitions=transitions, failure_codes=codes,
        failures=_failure_records(codes), **_authorities(),
    )


def _validation_codes(policy: object, configuration: object) -> tuple[str, ...]:
    policy_ok = isinstance(policy, PassiveRuntimeLauncherPolicyV1)
    configuration_ok = isinstance(configuration, PassiveRuntimeLauncherConfigurationV1)
    value = lambda record, name, default=None: getattr(record, name, default)
    conditions = {
        "POLICY_ID_EMPTY": not policy_ok or _blank(value(policy, "policy_id")),
        "POLICY_VERSION_EMPTY": not policy_ok or _blank(value(policy, "policy_version")),
        "LAUNCHER_IMPLEMENTATION_NOT_AUTHORIZED": not policy_ok or value(policy, "launcher_implementation_authorized") is not True,
        "PASSIVE_TEST_EXECUTION_NOT_AUTHORIZED": not policy_ok or value(policy, "passive_test_execution_authorized") is not True,
        "SYNTHETIC_SIGNAL_TEST_NOT_AUTHORIZED": not policy_ok or value(policy, "synthetic_signal_tests_authorized") is not True,
        "EXECUTION_MODE_MISMATCH": not policy_ok or not configuration_ok or any((
            value(policy, "launcher_module") != _MODULE, value(policy, "launcher_mode") != "PASSIVE_TEST_MODE",
            value(configuration, "execution_mode") != "PASSIVE_TEST_MODE", not value(configuration, "passive_configuration_complete"),
        )),
        "SERVICE_UNIT_MISMATCH": not policy_ok or not configuration_ok or any((
            value(policy, "expected_service_unit") != "ai-crypto-signal-agent.service",
            value(configuration, "service_unit") != "ai-crypto-signal-agent.service",
        )),
        "SERVICE_USER_MISMATCH": not policy_ok or not configuration_ok or any((
            value(policy, "expected_service_user") != "ai-crypto-signal-agent",
            value(configuration, "service_user") != "ai-crypto-signal-agent",
        )),
        "SERVICE_GROUP_MISMATCH": not policy_ok or not configuration_ok or any((
            value(policy, "expected_service_group") != "ai-crypto-signal-agent",
            value(configuration, "service_group") != "ai-crypto-signal-agent",
        )),
        "INSTALLATION_PATH_MISMATCH": not policy_ok or not configuration_ok or any((
            value(policy, "expected_installation_path") != "/opt/ai-crypto-signal-agent",
            value(configuration, "installation_path") != "/opt/ai-crypto-signal-agent",
        )),
        "WORKING_DIRECTORY_MISMATCH": not policy_ok or not configuration_ok or any((
            value(policy, "expected_working_directory") != "/opt/ai-crypto-signal-agent",
            value(configuration, "working_directory") != "/opt/ai-crypto-signal-agent",
        )),
        "PYTHON_INTERPRETER_PATH_MISMATCH": not policy_ok or not configuration_ok or any((
            value(policy, "expected_python_interpreter") != "/opt/ai-crypto-signal-agent/.venv/bin/python",
            value(configuration, "python_interpreter") != "/opt/ai-crypto-signal-agent/.venv/bin/python",
        )),
        "STATE_DIRECTORY_MISMATCH": not configuration_ok or value(configuration, "state_directory_classification") != "/var/lib/ai-crypto-signal-agent",
        "CACHE_DIRECTORY_MISMATCH": not configuration_ok or value(configuration, "cache_directory_classification") != "/var/cache/ai-crypto-signal-agent",
        "RUNTIME_DIRECTORY_MISMATCH": not configuration_ok or value(configuration, "runtime_directory_classification") != "/run/ai-crypto-signal-agent",
        "LOG_DESTINATION_MISMATCH": not configuration_ok or value(configuration, "log_destination") != "JOURNALD_ONLY",
        "LOG_DIRECTORY_NOT_ALLOWED": not configuration_ok or value(configuration, "log_directory") != "NONE",
        "ACTIVATION_GATE_MUST_REMAIN_CLOSED": not configuration_ok or value(configuration, "activation_gate_open") is not False,
        "CREDENTIAL_GATE_MUST_REMAIN_CLOSED": not configuration_ok or value(configuration, "credential_gate_open") is not False,
        "NETWORK_GATE_MUST_REMAIN_CLOSED": not configuration_ok or value(configuration, "network_gate_open") is not False,
        "WORKLOAD_GATE_MUST_REMAIN_CLOSED": not configuration_ok or value(configuration, "workload_gate_open") is not False,
        "FILESYSTEM_READ_NOT_AUTHORIZED": not policy_ok or value(policy, "filesystem_read_authorized") is not False,
        "FILESYSTEM_WRITE_NOT_AUTHORIZED": not policy_ok or value(policy, "filesystem_write_authorized") is not False,
        "ENVIRONMENT_READ_NOT_AUTHORIZED": not policy_ok or value(policy, "environment_read_authorized") is not False,
        "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED": not policy_ok or value(policy, "real_signal_registration_authorized") is not False,
        "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED": not policy_ok or value(policy, "credential_access_authorized") is not False,
        "CREDENTIAL_LOADING_NOT_AUTHORIZED": not policy_ok or value(policy, "credential_loading_authorized") is not False,
        "CREDENTIAL_VALIDATION_NOT_AUTHORIZED": not policy_ok or value(policy, "credential_validation_authorized") is not False,
        "SYSTEMD_ACCESS_NOT_AUTHORIZED": not policy_ok or value(policy, "systemd_access_authorized") is not False,
        "NETWORK_NOT_AUTHORIZED": not policy_ok or value(policy, "network_authorized") is not False,
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED": not policy_ok or value(policy, "provider_transmission_authorized") is not False,
        "SCANNER_EXECUTION_NOT_AUTHORIZED": not policy_ok or value(policy, "scanner_execution_authorized") is not False,
        "WORKER_START_NOT_AUTHORIZED": not policy_ok or value(policy, "worker_start_authorized") is not False,
        "SCHEDULER_START_NOT_AUTHORIZED": not policy_ok or value(policy, "scheduler_start_authorized") is not False,
        "TELEGRAM_START_NOT_AUTHORIZED": not policy_ok or value(policy, "telegram_start_authorized") is not False,
        "DATABASE_MUTATION_NOT_AUTHORIZED": not policy_ok or value(policy, "database_mutation_authorized") is not False,
        "ARTIFACT_PUBLICATION_NOT_AUTHORIZED": not policy_ok or value(policy, "artifact_publication_authorized") is not False,
        "TRADING_NOT_AUTHORIZED": not policy_ok or value(policy, "trading_authorized") is not False,
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED": not policy_ok or value(policy, "runtime_activation_authorized") is not False,
        "PUBLICATION_NOT_AUTHORIZED": not policy_ok or value(policy, "publication_authorized") is not False,
        "RAW_CREDENTIAL_EXPOSURE_DETECTED": not configuration_ok or value(configuration, "credential_exposure_detected") is not False,
        "PROVIDER_ENDPOINT_EXPOSURE_DETECTED": not configuration_ok or value(configuration, "endpoint_exposure_detected") is not False,
        "AUTHORIZATION_MATERIAL_EXPOSURE_DETECTED": not configuration_ok or value(configuration, "authorization_exposure_detected") is not False,
        "RAW_EXCEPTION_EXPOSURE_DETECTED": not configuration_ok or value(configuration, "real_process_control_requested") is not False,
    }
    return _ordered(conditions)


def build_passive_runtime_launcher_v1(
    *, policy: PassiveRuntimeLauncherPolicyV1, configuration: PassiveRuntimeLauncherConfigurationV1,
) -> PassiveRuntimeLauncherStateV1:
    """Build only immutable in-memory passive launcher metadata."""
    return _state(configuration, "CREATED" if not _validation_codes(policy, configuration) else "BLOCKED")


def evaluate_passive_runtime_launcher_startup_v1(
    *,
    policy: PassiveRuntimeLauncherPolicyV1,
    configuration: PassiveRuntimeLauncherConfigurationV1,
    current_state: PassiveRuntimeLauncherStateV1,
) -> PassiveRuntimeLauncherResultV1:
    """Evaluate passive startup without performing a runtime operation."""
    codes = _validation_codes(policy, configuration)
    if codes:
        return _result(policy=policy, configuration=configuration, state=_state(configuration, "BLOCKED"), codes=codes)
    if not isinstance(current_state, PassiveRuntimeLauncherStateV1) or current_state.state_code != "CREATED":
        return _result(
            policy=policy, configuration=configuration, state=_state(configuration, "BLOCKED"),
            codes=("INVALID_STATE_TRANSITION",),
        )
    validated = _state(configuration, "CONFIGURATION_VALIDATED")
    ready = _state(configuration, "PASSIVE_READY")
    return _result(
        policy=policy, configuration=configuration, state=ready,
        transitions=(
            _transition("CREATED", "CONFIGURATION_VALIDATED", "PASSIVE_CONFIGURATION_VALIDATED"),
            _transition("CONFIGURATION_VALIDATED", "PASSIVE_READY", "PASSIVE_READY"),
        ),
    )


def _signal_result(
    *,
    policy: PassiveRuntimeLauncherPolicyV1,
    state: PassiveRuntimeLauncherStateV1,
    configuration: PassiveRuntimeLauncherConfigurationV1,
    codes: tuple[str, ...] = (),
    transitions: tuple[PassiveRuntimeLauncherTransitionV1, ...] = (),
) -> PassiveRuntimeLauncherResultV1:
    return _result(policy=policy, configuration=configuration, state=state, codes=codes, transitions=transitions)


def evaluate_passive_runtime_launcher_synthetic_signal_v1(
    *,
    policy: PassiveRuntimeLauncherPolicyV1,
    current_state: PassiveRuntimeLauncherStateV1,
    synthetic_signal: PassiveRuntimeLauncherSyntheticSignalV1,
) -> PassiveRuntimeLauncherResultV1:
    """Evaluate caller-supplied synthetic signal metadata only."""
    configuration = PassiveRuntimeLauncherConfigurationV1(
        launcher_id=getattr(current_state, "launcher_id", ""), invocation_id=getattr(current_state, "invocation_id", ""),
        execution_mode="PASSIVE_TEST_MODE", service_unit="ai-crypto-signal-agent.service",
        service_user="ai-crypto-signal-agent", service_group="ai-crypto-signal-agent",
        installation_path="/opt/ai-crypto-signal-agent", working_directory="/opt/ai-crypto-signal-agent",
        python_interpreter="/opt/ai-crypto-signal-agent/.venv/bin/python",
        state_directory_classification="/var/lib/ai-crypto-signal-agent",
        cache_directory_classification="/var/cache/ai-crypto-signal-agent",
        runtime_directory_classification="/run/ai-crypto-signal-agent", log_destination="JOURNALD_ONLY",
        log_directory="NONE", credential_gate_open=False, network_gate_open=False,
        workload_gate_open=False, activation_gate_open=False, credential_exposure_detected=False,
        endpoint_exposure_detected=False, authorization_exposure_detected=False,
        real_process_control_requested=False, passive_configuration_complete=True,
    )
    codes = _validation_codes(policy, configuration)
    if codes:
        return _signal_result(policy=policy, configuration=configuration, state=_state(configuration, "BLOCKED"), codes=codes)
    if not isinstance(synthetic_signal, PassiveRuntimeLauncherSyntheticSignalV1):
        return _signal_result(policy=policy, configuration=configuration, state=current_state, codes=("UNKNOWN_SYNTHETIC_SIGNAL",))
    signal = synthetic_signal.signal_classification
    if signal in ("SYNTHETIC_SIGTERM", "SYNTHETIC_SIGINT"):
        if current_state.state_code == "PASSIVE_READY":
            requested = _state(configuration, "SHUTDOWN_REQUESTED")
            return _signal_result(
                policy=policy, configuration=configuration, state=requested,
                transitions=(_transition("PASSIVE_READY", "SHUTDOWN_REQUESTED", signal),),
            )
        if current_state.state_code in ("SHUTDOWN_REQUESTED", "GRACEFUL_SHUTDOWN_COMPLETE"):
            return _signal_result(policy=policy, configuration=configuration, state=current_state)
        return _signal_result(policy=policy, configuration=configuration, state=_state(configuration, "BLOCKED"), codes=("INVALID_STATE_TRANSITION",))
    if signal == "SYNTHETIC_SIGHUP":
        return _signal_result(policy=policy, configuration=configuration, state=current_state, codes=("RELOAD_NOT_AUTHORIZED",))
    return _signal_result(policy=policy, configuration=configuration, state=current_state, codes=("UNKNOWN_SYNTHETIC_SIGNAL",))


def request_passive_runtime_launcher_shutdown_v1(
    *,
    policy: PassiveRuntimeLauncherPolicyV1,
    current_state: PassiveRuntimeLauncherStateV1,
    shutdown_request: PassiveRuntimeLauncherShutdownRequestV1,
) -> PassiveRuntimeLauncherResultV1:
    """Advance synthetic passive shutdown without timers, cleanup, or I/O."""
    configuration = PassiveRuntimeLauncherConfigurationV1(
        launcher_id=getattr(current_state, "launcher_id", ""), invocation_id=getattr(current_state, "invocation_id", ""),
        execution_mode="PASSIVE_TEST_MODE", service_unit="ai-crypto-signal-agent.service",
        service_user="ai-crypto-signal-agent", service_group="ai-crypto-signal-agent",
        installation_path="/opt/ai-crypto-signal-agent", working_directory="/opt/ai-crypto-signal-agent",
        python_interpreter="/opt/ai-crypto-signal-agent/.venv/bin/python",
        state_directory_classification="/var/lib/ai-crypto-signal-agent",
        cache_directory_classification="/var/cache/ai-crypto-signal-agent",
        runtime_directory_classification="/run/ai-crypto-signal-agent", log_destination="JOURNALD_ONLY",
        log_directory="NONE", credential_gate_open=False, network_gate_open=False,
        workload_gate_open=False, activation_gate_open=False, credential_exposure_detected=False,
        endpoint_exposure_detected=False, authorization_exposure_detected=False,
        real_process_control_requested=False, passive_configuration_complete=True,
    )
    codes = _validation_codes(policy, configuration)
    if codes:
        return _result(policy=policy, configuration=configuration, state=_state(configuration, "BLOCKED"), codes=codes)
    if not isinstance(shutdown_request, PassiveRuntimeLauncherShutdownRequestV1):
        return _result(policy=policy, configuration=configuration, state=_state(configuration, "BLOCKED"), codes=("INVALID_STATE_TRANSITION",))
    if current_state.state_code == "PASSIVE_READY":
        requested = _state(configuration, "SHUTDOWN_REQUESTED")
        return _result(
            policy=policy, configuration=configuration, state=requested,
            transitions=(_transition("PASSIVE_READY", "SHUTDOWN_REQUESTED", shutdown_request.shutdown_classification),),
        )
    if current_state.state_code == "SHUTDOWN_REQUESTED":
        complete = _state(configuration, "GRACEFUL_SHUTDOWN_COMPLETE")
        return _result(
            policy=policy, configuration=configuration, state=complete,
            transitions=(_transition("SHUTDOWN_REQUESTED", "GRACEFUL_SHUTDOWN_COMPLETE", shutdown_request.shutdown_classification),),
        )
    if current_state.state_code == "GRACEFUL_SHUTDOWN_COMPLETE":
        return _result(policy=policy, configuration=configuration, state=current_state)
    return _result(policy=policy, configuration=configuration, state=_state(configuration, "BLOCKED"), codes=("INVALID_STATE_TRANSITION",))


def build_passive_runtime_launcher_audit_evidence_v1(
    *,
    audit_id: str,
    policy: PassiveRuntimeLauncherPolicyV1,
    configuration: PassiveRuntimeLauncherConfigurationV1,
    result: PassiveRuntimeLauncherResultV1,
    requested_transition: str,
    synthetic_signal: PassiveRuntimeLauncherSyntheticSignalV1 | None,
    shutdown_classification: str,
) -> PassiveRuntimeLauncherAuditEvidenceV1:
    """Build redacted immutable audit metadata without external access."""
    return PassiveRuntimeLauncherAuditEvidenceV1(
        audit_id=audit_id, policy_id=policy.policy_id, launcher_id=configuration.launcher_id,
        invocation_id=configuration.invocation_id, execution_mode=configuration.execution_mode,
        service_unit=configuration.service_unit, working_directory=configuration.working_directory,
        current_state=result.current_state.state_code, requested_transition=requested_transition,
        synthetic_signal_classification=(None if synthetic_signal is None else synthetic_signal.signal_classification),
        shutdown_classification=shutdown_classification,
        gate_states=(configuration.activation_gate_open, configuration.credential_gate_open,
                     configuration.network_gate_open, configuration.workload_gate_open),
        failure_codes=result.failure_codes, **_authorities(),
    )


def main(
    *,
    policy: PassiveRuntimeLauncherPolicyV1,
    configuration: PassiveRuntimeLauncherConfigurationV1,
    current_state: PassiveRuntimeLauncherStateV1,
) -> PassiveRuntimeLauncherResultV1:
    """Caller-supplied passive entry point; it never reads process inputs."""
    return evaluate_passive_runtime_launcher_startup_v1(
        policy=policy, configuration=configuration, current_state=current_state,
    )
