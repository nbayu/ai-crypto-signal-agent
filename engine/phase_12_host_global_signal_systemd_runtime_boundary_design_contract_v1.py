"""Pure metadata validation for a future host-global signal/systemd boundary."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


_PYTHON = "/opt/ai-crypto-signal-agent/.venv/bin/python"
_MODULE = "engine.phase_12_passive_runtime_launcher_executable_contract_v1"
_ADAPTER = "engine.phase_12_passive_production_cli_real_signal_adapter_contract_v1"
_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "HOST_GLOBAL_SIGNAL_DESIGN_NOT_AUTHORIZED",
    "SYSTEMD_RUNTIME_DESIGN_NOT_AUTHORIZED", "MAIN_THREAD_REGISTRATION_DESIGN_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_DESIGN_NOT_AUTHORIZED", "PROCESS_EXIT_DESIGN_NOT_AUTHORIZED",
    "HOST_GLOBAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
    "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED",
    "SYSTEMD_RUNTIME_IMPLEMENTATION_NOT_AUTHORIZED", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED",
    "PROCESS_TERMINATION_NOT_AUTHORIZED", "SERVICE_UNIT_MISMATCH",
    "SERVICE_MANAGER_SCOPE_MISMATCH", "DEPLOYMENT_STATE_MISMATCH", "SERVICE_USER_MISMATCH",
    "SERVICE_GROUP_MISMATCH", "WORKING_DIRECTORY_MISMATCH", "PYTHON_INTERPRETER_MISMATCH",
    "LAUNCHER_MODULE_MISMATCH", "CLI_ADAPTER_MODULE_MISMATCH", "PASSIVE_CLI_ARGUMENT_MISMATCH",
    "PASSIVE_DEFAULT_REQUIRED", "MAIN_THREAD_REGISTRATION_REQUIRED", "SIGNAL_SET_MISMATCH",
    "DUPLICATE_REGISTRATION_NOT_ALLOWED", "UNSUPPORTED_SIGNAL_REGISTRATION",
    "SIGHUP_RELOAD_NOT_AUTHORIZED", "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED",
    "HANDLER_IO_NOT_AUTHORIZED", "HANDLER_LIVE_ACTION_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_REQUIRED", "HANDLER_RESTORATION_ORDER_INVALID",
    "HANDLER_RESTORATION_NOT_IDEMPOTENT", "GRACEFUL_SHUTDOWN_REQUIRED",
    "BOUNDED_SHUTDOWN_REQUIRED", "SHUTDOWN_TIMEOUT_REQUIRED", "SHUTDOWN_NOT_IDEMPOTENT",
    "PROCESS_EXIT_CLASSIFICATION_OVERLAP", "SYS_EXIT_NOT_AUTHORIZED", "SYSTEM_EXIT_NOT_AUTHORIZED",
    "OS_EXIT_NOT_AUTHORIZED", "PROCESS_SIGNAL_SEND_NOT_AUTHORIZED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED", "ENVIRONMENT_READ_NOT_AUTHORIZED",
    "FILESYSTEM_READ_NOT_AUTHORIZED", "FILESYSTEM_WRITE_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "SYSTEMD_ACCESS_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED", "WORKER_START_NOT_AUTHORIZED",
    "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED",
    "TRADING_NOT_AUTHORIZED", "SUBPROCESS_NOT_AUTHORIZED", "THREAD_START_NOT_AUTHORIZED",
    "EVENT_LOOP_START_NOT_AUTHORIZED", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED",
    "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE", "EVIDENCE_EXPIRED",
    "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED", "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED",
    "DAEMON_RELOAD_NOT_AUTHORIZED", "SERVICE_ENABLEMENT_NOT_AUTHORIZED", "SERVICE_START_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_MATERIAL_EXPOSURE_DETECTED",
    "RAW_HANDLER_REPRESENTATION_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


@dataclass(frozen=True, slots=True, init=False)
class _Record:
    values: tuple[tuple[str, object], ...]

    def __init__(self, **values: object) -> None:
        object.__setattr__(self, "values", tuple(values.items()))

    def __getattr__(self, name: str) -> object:
        for key, value in self.values:
            if key == name:
                return value
        raise AttributeError(name)


class HostGlobalSignalSystemdRuntimeBoundaryPolicyV1(_Record):
    __slots__ = ()


class HostGlobalSignalRuntimeIdentityV1(_Record):
    __slots__ = ()


class HostGlobalSignalRegistrationDesignV1(_Record):
    __slots__ = ()


class HostGlobalSignalHandlerDesignV1(_Record):
    __slots__ = ()


class HostGlobalSignalRestorationDesignV1(_Record):
    __slots__ = ()


class HostGlobalSignalDispatchDesignV1(_Record):
    __slots__ = ()


class HostGlobalSignalShutdownDesignV1(_Record):
    __slots__ = ()


class DeterministicProcessExitDesignV1(_Record):
    __slots__ = ()


class SystemdServiceRuntimeIdentityV1(_Record):
    __slots__ = ()


class SystemdServiceStartupLifecycleV1(_Record):
    __slots__ = ()


class SystemdServiceShutdownLifecycleV1(_Record):
    __slots__ = ()


class SystemdServiceRestartBoundaryV1(_Record):
    __slots__ = ()


class SystemdServiceFailureBoundaryV1(_Record):
    __slots__ = ()


class SystemdServiceRuntimeReadinessChecklistV1(_Record):
    __slots__ = ()


class HostGlobalSignalSystemdRuntimeOperatorAttestationV1(_Record):
    __slots__ = ()


class HostGlobalSignalSystemdRuntimeIndependentReviewerApprovalV1(_Record):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class HostGlobalSignalSystemdRuntimeFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


class HostGlobalSignalSystemdRuntimeDecisionV1(_Record):
    __slots__ = ()


class HostGlobalSignalSystemdRuntimeAuditEvidenceV1(_Record):
    __slots__ = ()


def _codes(*codes: str) -> tuple[str, ...]:
    selected = set(codes)
    return tuple(code for code in _ORDER if code in selected)


def _add(codes: list[str], condition: bool, code: str) -> None:
    if condition:
        codes.append(code)


def _flag(record: object, name: str) -> bool:
    return bool(getattr(record, name))


def _authority() -> dict[str, bool]:
    return {
        "host_global_signal_boundary_design_authorized": True,
        "systemd_service_runtime_lifecycle_design_authorized": True,
        "main_thread_signal_registration_design_authorized": True,
        "handler_restoration_design_authorized": True,
        "deterministic_process_exit_design_authorized": True,
        "host_global_signal_implementation_authorized": False,
        "systemd_service_runtime_implementation_authorized": False,
        "main_thread_signal_registration_implementation_authorized": False,
        "process_termination_implementation_authorized": False,
        "process_exit_execution_authorized": False,
        "credential_loading_authorized": False, "systemd_access_authorized": False,
        "network_authorized": False, "production_runtime_execution_authorized": False,
        "runtime_activation_authorized": False, "publication_authorized": False,
        "fail_closed": True,
    }


def _gates() -> dict[str, bool]:
    return {"activation_gate_open": False, "credential_gate_open": False,
            "network_gate_open": False, "workload_gate_open": False}


def _valid_evidence(policy: _Record, signal: _Record, handler: _Record, restoration: _Record,
                    service: _Record, checklist: _Record, operator: _Record, reviewer: _Record) -> bool:
    return (
        operator.operator_identity != "" and operator.operator_role == "OPERATOR"
        and reviewer.reviewer_identity != "" and reviewer.reviewer_role == "INDEPENDENT_REVIEWER"
        and operator.policy_id == policy.policy_id == reviewer.policy_id
        and operator.signal_runtime_id == signal.signal_runtime_id == reviewer.signal_runtime_id
        and operator.handler_id == handler.handler_id == reviewer.handler_id
        and operator.restoration_id == restoration.restoration_id == reviewer.restoration_id
        and operator.service_id == service.service_id == reviewer.service_id
        and operator.checklist_id == checklist.checklist_id == reviewer.checklist_id
        and reviewer.attestation_id == operator.attestation_id
        and _flag(operator, "design_only_authority_confirmed")
        and _flag(operator, "implementation_execution_unauthorized_confirmed")
        and _flag(operator, "all_gates_closed_confirmed")
        and not _flag(operator, "sensitive_evidence_retained") and _flag(operator, "attestation_complete")
        and _flag(reviewer, "design_only_authority_confirmed")
        and _flag(reviewer, "implementation_execution_unauthorized_confirmed")
        and _flag(reviewer, "all_gates_closed_confirmed")
        and not _flag(reviewer, "sensitive_evidence_retained") and _flag(reviewer, "approved")
        and _flag(reviewer, "review_complete") and _flag(checklist, "checklist_complete")
        and _flag(checklist, "evidence_fresh")
    )


def _validate(
    policy: _Record, signal: _Record, registration: _Record, handler: _Record, restoration: _Record,
    dispatch: _Record, shutdown: _Record, exit_design: _Record, service: _Record, startup: _Record,
    service_shutdown: _Record, restart: _Record, failure_boundary: _Record, checklist: _Record,
    operator: _Record | None, reviewer: _Record | None, evaluation_time: datetime,
) -> tuple[str, ...]:
    codes: list[str] = []
    _add(codes, not isinstance(policy.policy_id, str) or not policy.policy_id, "POLICY_ID_EMPTY")
    _add(codes, not isinstance(policy.policy_version, str) or not policy.policy_version, "POLICY_VERSION_EMPTY")
    for name, code in (
        ("host_global_signal_boundary_design_authorized", "HOST_GLOBAL_SIGNAL_DESIGN_NOT_AUTHORIZED"),
        ("systemd_service_runtime_lifecycle_design_authorized", "SYSTEMD_RUNTIME_DESIGN_NOT_AUTHORIZED"),
        ("main_thread_signal_registration_design_authorized", "MAIN_THREAD_REGISTRATION_DESIGN_NOT_AUTHORIZED"),
        ("handler_restoration_design_authorized", "HANDLER_RESTORATION_DESIGN_NOT_AUTHORIZED"),
        ("deterministic_process_exit_design_authorized", "PROCESS_EXIT_DESIGN_NOT_AUTHORIZED"),
    ):
        _add(codes, not _flag(policy, name), code)
    for name, code in (
        ("host_global_signal_implementation_authorized", "HOST_GLOBAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("main_thread_signal_registration_implementation_authorized", "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("systemd_service_runtime_implementation_authorized", "SYSTEMD_RUNTIME_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("process_exit_execution_authorized", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
        ("process_termination_implementation_authorized", "PROCESS_TERMINATION_NOT_AUTHORIZED"),
    ):
        _add(codes, _flag(policy, name), code)
    _add(codes, signal.process_role != "SYSTEMD_SERVICE_MAIN_PROCESS" or signal.registration_scope != "HOST_GLOBAL_MAIN_THREAD", "MAIN_THREAD_REGISTRATION_REQUIRED")
    _add(codes, not _flag(signal, "main_thread_registration_required"), "MAIN_THREAD_REGISTRATION_REQUIRED")
    _add(codes, signal.supported_signal_names != ("SIGTERM", "SIGINT"), "SIGNAL_SET_MISMATCH")
    _add(codes, not _flag(registration, "duplicate_registration_prohibited"), "DUPLICATE_REGISTRATION_NOT_ALLOWED")
    _add(codes, not _flag(registration, "unsupported_registration_prohibited"), "UNSUPPORTED_SIGNAL_REGISTRATION")
    _add(codes, not _flag(registration, "partial_registration_rollback_defined"), "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED")
    _add(codes, _flag(handler, "blocking_operation_allowed"), "HANDLER_IO_NOT_AUTHORIZED")
    _add(codes, any(_flag(handler, name) for name in ("filesystem_access_allowed", "environment_access_allowed", "credential_access_allowed", "provider_network_access_allowed", "workload_direct_action_allowed", "publication_allowed", "database_mutation_allowed", "process_exit_allowed")), "HANDLER_LIVE_ACTION_NOT_AUTHORIZED")
    _add(codes, not _flag(restoration, "restoration_on_normal_shutdown"), "HANDLER_RESTORATION_REQUIRED")
    _add(codes, restoration.restoration_order != "SIGTERM_THEN_SIGINT", "HANDLER_RESTORATION_ORDER_INVALID")
    _add(codes, not _flag(restoration, "restoration_idempotent"), "HANDLER_RESTORATION_NOT_IDEMPOTENT")
    _add(codes, not _flag(shutdown, "graceful_shutdown_required"), "GRACEFUL_SHUTDOWN_REQUIRED")
    _add(codes, not _flag(shutdown, "bounded_shutdown_required"), "BOUNDED_SHUTDOWN_REQUIRED")
    _add(codes, not isinstance(shutdown.shutdown_timeout_seconds, int) or shutdown.shutdown_timeout_seconds <= 0, "SHUTDOWN_TIMEOUT_REQUIRED")
    _add(codes, not _flag(shutdown, "repeated_shutdown_idempotent"), "SHUTDOWN_NOT_IDEMPOTENT")
    exits = exit_design.exit_codes
    _add(codes, not isinstance(exits, tuple) or not all(isinstance(item, int) for item in exits) or len(set(exits)) != len(exits), "PROCESS_EXIT_CLASSIFICATION_OVERLAP")
    _add(codes, _flag(exit_design, "sys_exit_allowed"), "SYS_EXIT_NOT_AUTHORIZED")
    _add(codes, _flag(exit_design, "system_exit_raise_allowed"), "SYSTEM_EXIT_NOT_AUTHORIZED")
    _add(codes, _flag(exit_design, "os_exit_allowed"), "OS_EXIT_NOT_AUTHORIZED")
    _add(codes, _flag(exit_design, "process_signal_send_allowed"), "PROCESS_SIGNAL_SEND_NOT_AUTHORIZED")
    for attribute, expected, code in (
        ("service_unit", "ai-crypto-signal-agent.service", "SERVICE_UNIT_MISMATCH"),
        ("service_manager_scope", "SYSTEM", "SERVICE_MANAGER_SCOPE_MISMATCH"),
        ("deployment_state", "NOT_YET_INSTALLED", "DEPLOYMENT_STATE_MISMATCH"),
        ("service_user", "ai-crypto-signal-agent", "SERVICE_USER_MISMATCH"),
        ("service_group", "ai-crypto-signal-agent", "SERVICE_GROUP_MISMATCH"),
        ("working_directory", "/opt/ai-crypto-signal-agent", "WORKING_DIRECTORY_MISMATCH"),
        ("python_interpreter", _PYTHON, "PYTHON_INTERPRETER_MISMATCH"),
        ("launcher_module", _MODULE, "LAUNCHER_MODULE_MISMATCH"),
        ("cli_adapter_module", _ADAPTER, "CLI_ADAPTER_MODULE_MISMATCH"),
        ("passive_cli_arguments", ("--mode", "passive"), "PASSIVE_CLI_ARGUMENT_MISMATCH"),
    ):
        _add(codes, getattr(service, attribute) != expected, code)
    _add(codes, not _flag(service, "passive_default"), "PASSIVE_DEFAULT_REQUIRED")
    _add(codes, _flag(startup, "implicit_sys_argv_access_allowed"), "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED")
    _add(codes, _flag(startup, "environment_read_allowed"), "ENVIRONMENT_READ_NOT_AUTHORIZED")
    _add(codes, _flag(startup, "credential_loading_allowed"), "CREDENTIAL_LOADING_NOT_AUTHORIZED")
    _add(codes, _flag(startup, "network_activation_allowed"), "NETWORK_NOT_AUTHORIZED")
    _add(codes, _flag(startup, "workload_start_allowed"), "SCANNER_EXECUTION_NOT_AUTHORIZED")
    _add(codes, _flag(service_shutdown, "sighup_reload_allowed"), "SIGHUP_RELOAD_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "filesystem_read_authorized"), "FILESYSTEM_READ_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "filesystem_write_authorized"), "FILESYSTEM_WRITE_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "credential_access_authorized"), "CREDENTIAL_ACCESS_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "systemd_access_authorized") or _flag(restart, "systemd_access_authorized"), "SYSTEMD_ACCESS_NOT_AUTHORIZED")
    for name, code in (
        ("provider_transmission_authorized", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        ("scanner_execution_authorized", "SCANNER_EXECUTION_NOT_AUTHORIZED"),
        ("worker_start_authorized", "WORKER_START_NOT_AUTHORIZED"),
        ("scheduler_start_authorized", "SCHEDULER_START_NOT_AUTHORIZED"),
        ("telegram_start_authorized", "TELEGRAM_START_NOT_AUTHORIZED"),
        ("database_mutation_authorized", "DATABASE_MUTATION_NOT_AUTHORIZED"),
        ("artifact_publication_authorized", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED"),
        ("trading_authorized", "TRADING_NOT_AUTHORIZED"),
        ("subprocess_authorized", "SUBPROCESS_NOT_AUTHORIZED"),
        ("thread_start_authorized", "THREAD_START_NOT_AUTHORIZED"),
        ("event_loop_start_authorized", "EVENT_LOOP_START_NOT_AUTHORIZED"),
        ("runtime_activation_authorized", "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ("publication_authorized", "PUBLICATION_NOT_AUTHORIZED"),
    ):
        _add(codes, _flag(policy, name), code)
    _add(codes, _flag(service, "production_runtime_execution_authorized"), "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED")
    _add(codes, operator is None, "OPERATOR_ATTESTATION_REQUIRED")
    _add(codes, reviewer is None, "REVIEWER_APPROVAL_REQUIRED")
    if operator is not None and reviewer is not None:
        _add(codes, operator.operator_identity == reviewer.reviewer_identity, "OPERATOR_REVIEWER_COLLISION")
        _add(codes, operator.attested_at > evaluation_time or reviewer.reviewed_at > evaluation_time, "EVIDENCE_FROM_FUTURE")
        age = policy.evidence_max_age_seconds if isinstance(policy.evidence_max_age_seconds, int) and policy.evidence_max_age_seconds >= 0 else 0
        _add(codes, operator.attested_at < evaluation_time - timedelta(seconds=age) or reviewer.reviewed_at < evaluation_time - timedelta(seconds=age), "EVIDENCE_STALE")
        _add(codes, operator.expires_at < evaluation_time or reviewer.expires_at < evaluation_time, "EVIDENCE_EXPIRED")
        _add(codes, not _valid_evidence(policy, signal, handler, restoration, service, checklist, operator, reviewer), "RAW_EXCEPTION_EXPOSURE_DETECTED")
    _add(codes, _flag(policy, "systemd_unit_file_generation_authorized") or _flag(policy, "systemd_drop_in_generation_authorized"), "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "service_unit_installation_authorized"), "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "daemon_reload_authorized"), "DAEMON_RELOAD_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "service_enablement_authorized"), "SERVICE_ENABLEMENT_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "service_start_restart_authorized"), "SERVICE_START_NOT_AUTHORIZED")
    _add(codes, not _flag(failure_boundary, "failure_boundary_ready") or not _flag(checklist, "checklist_complete"), "RAW_EXCEPTION_EXPOSURE_DETECTED")
    return _codes(*codes)


def _states() -> tuple[str, ...]:
    return (
        "HOST_GLOBAL_SIGNAL_DESIGN_AUTHORIZED", "HOST_GLOBAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
        "MAIN_THREAD_REGISTRATION_DESIGN_READY", "MAIN_THREAD_REGISTRATION_NOT_IMPLEMENTED",
        "HANDLER_RESTORATION_DESIGN_READY", "HANDLER_RESTORATION_NOT_IMPLEMENTED",
        "PROCESS_EXIT_DESIGN_READY", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED",
        "SYSTEMD_SERVICE_RUNTIME_DESIGN_READY", "SYSTEMD_SERVICE_RUNTIME_NOT_IMPLEMENTED",
        "SERVICE_UNIT_NOT_INSTALLED", "SERVICE_EXECUTION_NOT_AUTHORIZED",
        "PRODUCTION_RUNTIME_NOT_AUTHORIZED", "ACTIVATION_GATE_CLOSED", "CREDENTIAL_GATE_CLOSED",
        "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED", "DEPLOYMENT_BLOCKED",
    )


def evaluate_host_global_signal_systemd_runtime_boundary_design_v1(
    *, policy: HostGlobalSignalSystemdRuntimeBoundaryPolicyV1,
    signal_identity: HostGlobalSignalRuntimeIdentityV1, registration_design: HostGlobalSignalRegistrationDesignV1,
    handler_design: HostGlobalSignalHandlerDesignV1, restoration_design: HostGlobalSignalRestorationDesignV1,
    dispatch_design: HostGlobalSignalDispatchDesignV1, shutdown_design: HostGlobalSignalShutdownDesignV1,
    exit_design: DeterministicProcessExitDesignV1, service_identity: SystemdServiceRuntimeIdentityV1,
    startup_lifecycle: SystemdServiceStartupLifecycleV1, shutdown_lifecycle: SystemdServiceShutdownLifecycleV1,
    restart_boundary: SystemdServiceRestartBoundaryV1, failure_boundary: SystemdServiceFailureBoundaryV1,
    checklist: SystemdServiceRuntimeReadinessChecklistV1,
    operator_attestation: HostGlobalSignalSystemdRuntimeOperatorAttestationV1 | None,
    reviewer_approval: HostGlobalSignalSystemdRuntimeIndependentReviewerApprovalV1 | None,
    evaluation_time: datetime,
) -> HostGlobalSignalSystemdRuntimeDecisionV1:
    codes = _validate(policy, signal_identity, registration_design, handler_design, restoration_design,
                      dispatch_design, shutdown_design, exit_design, service_identity, startup_lifecycle,
                      shutdown_lifecycle, restart_boundary, failure_boundary, checklist,
                      operator_attestation, reviewer_approval, evaluation_time)
    ready = not codes
    values: dict[str, object] = {
        "policy_id": policy.policy_id, "signal_runtime_id": signal_identity.signal_runtime_id,
        "service_id": service_identity.service_id, "ready": ready,
        "decision_classification": ("HOST_GLOBAL_SIGNAL_AND_SYSTEMD_SERVICE_RUNTIME_BOUNDARY_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION" if ready else "NOT_READY"),
        "states": _states(), "failure_codes": codes,
        "failures": tuple(HostGlobalSignalSystemdRuntimeFailureV1(code, "fail-closed design rejection", False) for code in codes),
        "service_execution_authorized": False, "deployment_blocked": True,
    }
    values.update(_gates())
    values.update(_authority())
    return HostGlobalSignalSystemdRuntimeDecisionV1(**values)


def build_host_global_signal_systemd_runtime_boundary_audit_evidence_v1(
    *, evidence_id: str, policy: HostGlobalSignalSystemdRuntimeBoundaryPolicyV1,
    signal_identity: HostGlobalSignalRuntimeIdentityV1, registration_design: HostGlobalSignalRegistrationDesignV1,
    handler_design: HostGlobalSignalHandlerDesignV1, restoration_design: HostGlobalSignalRestorationDesignV1,
    dispatch_design: HostGlobalSignalDispatchDesignV1, shutdown_design: HostGlobalSignalShutdownDesignV1,
    exit_design: DeterministicProcessExitDesignV1, service_identity: SystemdServiceRuntimeIdentityV1,
    startup_lifecycle: SystemdServiceStartupLifecycleV1, shutdown_lifecycle: SystemdServiceShutdownLifecycleV1,
    restart_boundary: SystemdServiceRestartBoundaryV1, failure_boundary: SystemdServiceFailureBoundaryV1,
    checklist: SystemdServiceRuntimeReadinessChecklistV1,
    operator_attestation: HostGlobalSignalSystemdRuntimeOperatorAttestationV1 | None,
    reviewer_approval: HostGlobalSignalSystemdRuntimeIndependentReviewerApprovalV1 | None,
    decision: HostGlobalSignalSystemdRuntimeDecisionV1, evaluation_time: datetime,
) -> HostGlobalSignalSystemdRuntimeAuditEvidenceV1:
    del registration_design, handler_design, restoration_design, dispatch_design, shutdown_design, exit_design
    del startup_lifecycle, shutdown_lifecycle, restart_boundary, failure_boundary, checklist
    del operator_attestation, reviewer_approval, evaluation_time
    values: dict[str, object] = {
        "evidence_id": evidence_id, "policy_id": policy.policy_id,
        "signal_runtime_id": signal_identity.signal_runtime_id, "service_id": service_identity.service_id,
        "ready_for_separate_implementation_decision": decision.ready,
        "service_execution_authorized": False, "failure_codes": decision.failure_codes,
    }
    values.update(_gates())
    values.update(_authority())
    return HostGlobalSignalSystemdRuntimeAuditEvidenceV1(**values)
