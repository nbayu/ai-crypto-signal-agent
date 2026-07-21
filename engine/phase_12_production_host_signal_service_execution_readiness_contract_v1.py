"""Pure readiness metadata for future production host-signal service execution."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PRODUCTION_HOST_SIGNAL_READINESS_DESIGN_NOT_AUTHORIZED",
    "MAIN_THREAD_REGISTRATION_READINESS_DESIGN_NOT_AUTHORIZED", "HANDLER_RESTORATION_READINESS_DESIGN_NOT_AUTHORIZED",
    "PROCESS_EXIT_READINESS_DESIGN_NOT_AUTHORIZED", "SYSTEMD_SERVICE_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED",
    "LIFECYCLE_EVIDENCE_PACKAGE_DESIGN_NOT_AUTHORIZED", "PRODUCTION_HOST_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
    "DIRECT_HOST_SIGNAL_REGISTRATION_NOT_AUTHORIZED", "PRODUCTION_HANDLER_INSTALLATION_NOT_AUTHORIZED",
    "PRODUCTION_HANDLER_RESTORATION_EXECUTION_NOT_AUTHORIZED", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED",
    "PROCESS_TERMINATION_NOT_AUTHORIZED", "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED",
    "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED", "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED",
    "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED", "SERVICE_UNIT_MISMATCH", "SERVICE_MANAGER_SCOPE_MISMATCH",
    "DEPLOYMENT_STATE_MISMATCH", "SERVICE_USER_MISMATCH", "SERVICE_GROUP_MISMATCH",
    "WORKING_DIRECTORY_MISMATCH", "PYTHON_INTERPRETER_MISMATCH", "LAUNCHER_MODULE_MISMATCH",
    "PASSIVE_CLI_ARGUMENT_MISMATCH", "PASSIVE_DEFAULT_REQUIRED", "ISOLATED_SIGNAL_ADAPTER_GREEN_REQUIRED",
    "MAIN_THREAD_REGISTRATION_REQUIRED", "SIGNAL_SET_MISMATCH", "DUPLICATE_REGISTRATION_NOT_ALLOWED",
    "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED", "PREVIOUS_HANDLER_REDACTION_REQUIRED",
    "HANDLER_IO_NOT_AUTHORIZED", "HANDLER_LIVE_ACTION_NOT_AUTHORIZED", "HANDLER_RESTORATION_REQUIRED",
    "HANDLER_RESTORATION_ORDER_INVALID", "HANDLER_RESTORATION_NOT_IDEMPOTENT",
    "GRACEFUL_SHUTDOWN_REQUIRED", "BOUNDED_SHUTDOWN_REQUIRED", "SHUTDOWN_TIMEOUT_REQUIRED",
    "SHUTDOWN_NOT_IDEMPOTENT", "PROCESS_EXIT_CLASSIFICATION_OVERLAP", "SYS_EXIT_NOT_AUTHORIZED",
    "SYSTEM_EXIT_NOT_AUTHORIZED", "OS_EXIT_NOT_AUTHORIZED", "PROCESS_SIGNAL_SEND_NOT_AUTHORIZED",
    "DEPLOYMENT_PREREQUISITES_INCOMPLETE", "SYSTEMD_ACCESS_NOT_AUTHORIZED",
    "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED", "SYSTEMD_DROP_IN_GENERATION_NOT_AUTHORIZED",
    "SERVICE_INSTALLATION_NOT_AUTHORIZED", "DAEMON_RELOAD_NOT_AUTHORIZED",
    "SERVICE_ENABLEMENT_NOT_AUTHORIZED", "SERVICE_START_NOT_AUTHORIZED",
    "CREDENTIAL_PRESENCE_NOT_CONFIRMED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "SUBPROCESS_NOT_AUTHORIZED", "THREAD_CREATION_NOT_AUTHORIZED", "EVENT_LOOP_START_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION",
    "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "PROVIDER_MATERIAL_EXPOSURE_DETECTED", "RAW_HANDLER_REPRESENTATION_EXPOSURE_DETECTED",
    "PROCESS_METADATA_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
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


class ProductionHostSignalServiceReadinessPolicyV1(_Record): __slots__ = ()
class ProductionHostSignalRuntimeIdentityV1(_Record): __slots__ = ()
class ProductionMainThreadRegistrationReadinessV1(_Record): __slots__ = ()
class ProductionHandlerInstallationReadinessV1(_Record): __slots__ = ()
class ProductionHandlerRestorationReadinessV1(_Record): __slots__ = ()
class ProductionSignalDispatchReadinessV1(_Record): __slots__ = ()
class ProductionGracefulShutdownReadinessV1(_Record): __slots__ = ()
class ProductionProcessExitReadinessV1(_Record): __slots__ = ()
class SystemdServiceExecutionIdentityV1(_Record): __slots__ = ()
class SystemdServiceDeploymentPrerequisiteV1(_Record): __slots__ = ()
class SystemdServiceExecutionReadinessV1(_Record): __slots__ = ()
class ProductionLifecycleEvidencePackageV1(_Record): __slots__ = ()
class ProductionLifecycleOperatorAttestationV1(_Record): __slots__ = ()
class ProductionLifecycleIndependentReviewerApprovalV1(_Record): __slots__ = ()
class ProductionHostSignalServiceReadinessChecklistV1(_Record): __slots__ = ()


@dataclass(frozen=True, slots=True)
class ProductionHostSignalServiceReadinessFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


class ProductionHostSignalServiceReadinessDecisionV1(_Record): __slots__ = ()
class ProductionHostSignalServiceReadinessAuditEvidenceV1(_Record): __slots__ = ()


def _get(record: object, name: str, default: object = False) -> object:
    return getattr(record, name, default)


def _codes(*codes: str) -> tuple[str, ...]:
    present = set(codes)
    return tuple(code for code in _ORDER if code in present)


def _closed() -> dict[str, bool]:
    return {
        "activation_gate_open": False, "credential_gate_open": False,
        "network_gate_open": False, "workload_gate_open": False,
        "production_host_signal_implementation_authorized": False,
        "direct_host_signal_registration_authorized": False,
        "production_handler_installation_authorized": False,
        "production_handler_restoration_execution_authorized": False,
        "process_exit_execution_authorized": False, "process_termination_authorized": False,
        "process_signal_transmission_authorized": False, "production_cli_execution_authorized": False,
        "production_service_execution_authorized": False, "production_runtime_execution_authorized": False,
        "credential_loading_authorized": False, "systemd_access_authorized": False,
        "network_authorized": False, "runtime_activation_authorized": False,
        "publication_authorized": False, "fail_closed": True,
    }


def _failures(codes: tuple[str, ...]) -> tuple[ProductionHostSignalServiceReadinessFailureV1, ...]:
    return tuple(ProductionHostSignalServiceReadinessFailureV1(code, "fail-closed readiness rejection", False) for code in codes)


def _validate_policy(policy: _Record) -> list[str]:
    codes: list[str] = []
    if not _get(policy, "policy_id", ""): codes.append("POLICY_ID_EMPTY")
    if not _get(policy, "policy_version", ""): codes.append("POLICY_VERSION_EMPTY")
    for name, code in (
        ("production_host_global_signal_readiness_design_authorized", "PRODUCTION_HOST_SIGNAL_READINESS_DESIGN_NOT_AUTHORIZED"),
        ("production_main_thread_registration_readiness_design_authorized", "MAIN_THREAD_REGISTRATION_READINESS_DESIGN_NOT_AUTHORIZED"),
        ("production_handler_restoration_readiness_design_authorized", "HANDLER_RESTORATION_READINESS_DESIGN_NOT_AUTHORIZED"),
        ("production_process_exit_readiness_design_authorized", "PROCESS_EXIT_READINESS_DESIGN_NOT_AUTHORIZED"),
        ("systemd_service_execution_readiness_design_authorized", "SYSTEMD_SERVICE_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED"),
        ("production_lifecycle_evidence_package_design_authorized", "LIFECYCLE_EVIDENCE_PACKAGE_DESIGN_NOT_AUTHORIZED"),
    ):
        if not _get(policy, name): codes.append(code)
    for name, code in (
        ("production_host_global_signal_implementation_authorized", "PRODUCTION_HOST_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("direct_host_signal_registration_authorized", "DIRECT_HOST_SIGNAL_REGISTRATION_NOT_AUTHORIZED"),
        ("production_handler_installation_authorized", "PRODUCTION_HANDLER_INSTALLATION_NOT_AUTHORIZED"),
        ("production_handler_restoration_execution_authorized", "PRODUCTION_HANDLER_RESTORATION_EXECUTION_NOT_AUTHORIZED"),
        ("process_exit_execution_authorized", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
        ("process_termination_authorized", "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        ("process_signal_transmission_authorized", "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
        ("production_cli_execution_authorized", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED"),
        ("production_service_execution_authorized", "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED"),
        ("production_runtime_execution_authorized", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED"),
        ("credential_loading_authorized", "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ("systemd_access_authorized", "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        ("network_authorized", "NETWORK_NOT_AUTHORIZED"),
        ("runtime_activation_authorized", "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ("publication_authorized", "PUBLICATION_NOT_AUTHORIZED"),
        ("activation_gate_open", "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
        ("credential_gate_open", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
        ("network_gate_open", "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ("workload_gate_open", "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
    ):
        if _get(policy, name): codes.append(code)
    return codes


def evaluate_production_host_signal_service_execution_readiness_v1(
    *, policy: ProductionHostSignalServiceReadinessPolicyV1,
    runtime_identity: ProductionHostSignalRuntimeIdentityV1,
    registration_readiness: ProductionMainThreadRegistrationReadinessV1,
    handler_installation_readiness: ProductionHandlerInstallationReadinessV1,
    handler_restoration_readiness: ProductionHandlerRestorationReadinessV1,
    dispatch_readiness: ProductionSignalDispatchReadinessV1,
    shutdown_readiness: ProductionGracefulShutdownReadinessV1,
    exit_readiness: ProductionProcessExitReadinessV1,
    service_identity: SystemdServiceExecutionIdentityV1,
    deployment_prerequisites: SystemdServiceDeploymentPrerequisiteV1,
    service_execution_readiness: SystemdServiceExecutionReadinessV1,
    lifecycle_evidence: ProductionLifecycleEvidencePackageV1,
    checklist: ProductionHostSignalServiceReadinessChecklistV1,
    operator_attestation: ProductionLifecycleOperatorAttestationV1 | None,
    reviewer_approval: ProductionLifecycleIndependentReviewerApprovalV1 | None,
    evaluation_time: object,
    **aliases: object,
) -> ProductionHostSignalServiceReadinessDecisionV1:
    handler_installation_readiness = aliases.get("installation_readiness", handler_installation_readiness)
    handler_restoration_readiness = aliases.get("restoration_readiness", handler_restoration_readiness)
    codes = _validate_policy(policy)
    if not _get(runtime_identity, "isolated_adapter_green"): codes.append("ISOLATED_SIGNAL_ADAPTER_GREEN_REQUIRED")
    if _get(runtime_identity, "supported_signal_names") != ("SIGTERM", "SIGINT"): codes.append("SIGNAL_SET_MISMATCH")
    if not _get(runtime_identity, "main_thread_registration_required"): codes.append("MAIN_THREAD_REGISTRATION_REQUIRED")
    if not _get(registration_readiness, "caller_supplied_main_thread_contract_green"): codes.append("MAIN_THREAD_REGISTRATION_REQUIRED")
    if not _get(registration_readiness, "duplicate_registration_prohibited"): codes.append("DUPLICATE_REGISTRATION_NOT_ALLOWED")
    if not _get(registration_readiness, "partial_registration_rollback_green"): codes.append("PARTIAL_REGISTRATION_ROLLBACK_REQUIRED")
    if not _get(registration_readiness, "previous_handler_redaction_green"): codes.append("PREVIOUS_HANDLER_REDACTION_REQUIRED")
    if _get(handler_installation_readiness, "filesystem_access_allowed") or _get(handler_installation_readiness, "environment_access_allowed"):
        codes.append("HANDLER_IO_NOT_AUTHORIZED")
    if any(_get(handler_installation_readiness, name) for name in ("credential_access_allowed", "provider_network_action_allowed", "workload_direct_action_allowed", "database_mutation_allowed", "publication_allowed", "process_exit_allowed")):
        codes.append("HANDLER_LIVE_ACTION_NOT_AUTHORIZED")
    if _get(handler_restoration_readiness, "restoration_order") != ("SIGINT", "SIGTERM"):
        codes.append("HANDLER_RESTORATION_ORDER_INVALID")
    if not _get(handler_restoration_readiness, "restoration_idempotent"): codes.append("HANDLER_RESTORATION_NOT_IDEMPOTENT")
    if not _get(shutdown_readiness, "graceful_shutdown_required"): codes.append("GRACEFUL_SHUTDOWN_REQUIRED")
    if not _get(shutdown_readiness, "bounded_shutdown_required"): codes.append("BOUNDED_SHUTDOWN_REQUIRED")
    if not isinstance(_get(shutdown_readiness, "shutdown_timeout_seconds"), int) or _get(shutdown_readiness, "shutdown_timeout_seconds") <= 0:
        codes.append("SHUTDOWN_TIMEOUT_REQUIRED")
    exits = _get(exit_readiness, "exit_codes", ())
    if not isinstance(exits, tuple) or not all(isinstance(code, int) for code in exits) or len(set(exits)) != len(exits):
        codes.append("PROCESS_EXIT_CLASSIFICATION_OVERLAP")
    for name, code in (("sys_exit_allowed", "SYS_EXIT_NOT_AUTHORIZED"), ("system_exit_raise_allowed", "SYSTEM_EXIT_NOT_AUTHORIZED"), ("os_exit_allowed", "OS_EXIT_NOT_AUTHORIZED"), ("process_signal_send_allowed", "PROCESS_SIGNAL_SEND_NOT_AUTHORIZED")):
        if _get(exit_readiness, name): codes.append(code)
    for name, expected, code in (
        ("service_unit", "ai-crypto-signal-agent.service", "SERVICE_UNIT_MISMATCH"),
        ("service_manager_scope", "SYSTEM", "SERVICE_MANAGER_SCOPE_MISMATCH"),
        ("deployment_state", "NOT_YET_INSTALLED", "DEPLOYMENT_STATE_MISMATCH"),
        ("service_user", "ai-crypto-signal-agent", "SERVICE_USER_MISMATCH"),
        ("service_group", "ai-crypto-signal-agent", "SERVICE_GROUP_MISMATCH"),
        ("working_directory", "/opt/ai-crypto-signal-agent", "WORKING_DIRECTORY_MISMATCH"),
        ("python_interpreter", "/opt/ai-crypto-signal-agent/.venv/bin/python", "PYTHON_INTERPRETER_MISMATCH"),
        ("launcher_module", "engine.phase_12_passive_runtime_launcher_executable_contract_v1", "LAUNCHER_MODULE_MISMATCH"),
        ("passive_cli_arguments", ("--mode", "passive"), "PASSIVE_CLI_ARGUMENT_MISMATCH"),
    ):
        if _get(service_identity, name) != expected: codes.append(code)
    if not _get(service_identity, "passive_default"): codes.append("PASSIVE_DEFAULT_REQUIRED")
    if not _get(deployment_prerequisites, "deployment_prerequisites_documented"): codes.append("DEPLOYMENT_PREREQUISITES_INCOMPLETE")
    if _get(service_execution_readiness, "systemd_access_authorized"): codes.append("SYSTEMD_ACCESS_NOT_AUTHORIZED")
    if operator_attestation is None: codes.append("OPERATOR_ATTESTATION_REQUIRED")
    if reviewer_approval is None: codes.append("REVIEWER_APPROVAL_REQUIRED")
    if operator_attestation is not None and reviewer_approval is not None:
        if operator_attestation.operator_identity == reviewer_approval.reviewer_identity: codes.append("OPERATOR_REVIEWER_COLLISION")
        if operator_attestation.attested_at > evaluation_time or reviewer_approval.reviewed_at > evaluation_time: codes.append("EVIDENCE_FROM_FUTURE")
        if operator_attestation.expires_at < evaluation_time or reviewer_approval.expires_at < evaluation_time: codes.append("EVIDENCE_EXPIRED")
        age = _get(policy, "evidence_max_age_seconds", 0)
        if isinstance(age, int) and (operator_attestation.attested_at < evaluation_time - timedelta(seconds=age) or reviewer_approval.reviewed_at < evaluation_time - timedelta(seconds=age)):
            codes.append("EVIDENCE_STALE")
    if not _get(checklist, "checklist_complete") or not _get(lifecycle_evidence, "evidence_complete"):
        codes.append("RAW_EXCEPTION_EXPOSURE_DETECTED")
    ordered = _codes(*codes)
    values: dict[str, object] = {
        "ready": not ordered,
        "decision_classification": ("PRODUCTION_HOST_SIGNAL_AND_SERVICE_EXECUTION_READY_FOR_SEPARATE_IMPLEMENTATION_AND_EXECUTION_DECISIONS" if not ordered else "NOT_READY"),
        "failure_codes": ordered, "failures": tuple(ProductionHostSignalServiceReadinessFailureV1(code, "fail-closed readiness rejection", False) for code in ordered),
        "states": (
            "PRODUCTION_HOST_SIGNAL_READINESS_DESIGN_AUTHORIZED", "PRODUCTION_HOST_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
            "MAIN_THREAD_REGISTRATION_READINESS_COMPLETE", "DIRECT_HOST_REGISTRATION_NOT_AUTHORIZED",
            "HANDLER_INSTALLATION_READINESS_COMPLETE", "HANDLER_INSTALLATION_NOT_AUTHORIZED",
            "HANDLER_RESTORATION_READINESS_COMPLETE", "HANDLER_RESTORATION_EXECUTION_NOT_AUTHORIZED",
            "PROCESS_EXIT_READINESS_COMPLETE", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED",
            "SYSTEMD_SERVICE_EXECUTION_READINESS_COMPLETE", "SERVICE_EXECUTION_NOT_AUTHORIZED",
            "SERVICE_UNIT_NOT_INSTALLED", "CREDENTIAL_NOT_ENTERED", "PRODUCTION_RUNTIME_NOT_AUTHORIZED",
            "DEPLOYMENT_BLOCKED", "ACTIVATION_GATE_CLOSED", "CREDENTIAL_GATE_CLOSED",
            "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED",
        ),
    }
    values.update(_closed())
    return ProductionHostSignalServiceReadinessDecisionV1(**values)


def build_production_host_signal_service_execution_readiness_audit_evidence_v1(
    *, audit_evidence_id: str, policy: ProductionHostSignalServiceReadinessPolicyV1,
    runtime_identity: ProductionHostSignalRuntimeIdentityV1,
    registration_readiness: ProductionMainThreadRegistrationReadinessV1,
    handler_installation_readiness: ProductionHandlerInstallationReadinessV1,
    handler_restoration_readiness: ProductionHandlerRestorationReadinessV1,
    dispatch_readiness: ProductionSignalDispatchReadinessV1,
    shutdown_readiness: ProductionGracefulShutdownReadinessV1,
    exit_readiness: ProductionProcessExitReadinessV1,
    service_identity: SystemdServiceExecutionIdentityV1,
    deployment_prerequisites: SystemdServiceDeploymentPrerequisiteV1,
    service_execution_readiness: SystemdServiceExecutionReadinessV1,
    lifecycle_evidence: ProductionLifecycleEvidencePackageV1,
    checklist: ProductionHostSignalServiceReadinessChecklistV1,
    operator_attestation: ProductionLifecycleOperatorAttestationV1 | None,
    reviewer_approval: ProductionLifecycleIndependentReviewerApprovalV1 | None,
    decision: ProductionHostSignalServiceReadinessDecisionV1, evaluation_time: object,
) -> ProductionHostSignalServiceReadinessAuditEvidenceV1:
    del registration_readiness, handler_installation_readiness, handler_restoration_readiness
    del dispatch_readiness, shutdown_readiness, exit_readiness, deployment_prerequisites
    del service_execution_readiness, lifecycle_evidence, checklist, operator_attestation, reviewer_approval, evaluation_time
    values: dict[str, object] = {
        "audit_evidence_id": audit_evidence_id, "policy_id": policy.policy_id,
        "runtime_id": runtime_identity.runtime_id, "service_id": service_identity.service_id,
        "ready_for_separate_implementation_and_execution_decisions": decision.ready,
        "service_execution_authorized": False,
        "failure_codes": decision.failure_codes,
    }
    values.update(_closed())
    return ProductionHostSignalServiceReadinessAuditEvidenceV1(**values)
