"""Pure metadata contract for a future, non-operational CLI and signal boundary."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


_MODULE = "engine.phase_12_passive_runtime_launcher_executable_contract_v1"
_PYTHON = "/opt/ai-crypto-signal-agent/.venv/bin/python"
_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PRODUCTION_CLI_DESIGN_NOT_AUTHORIZED",
    "REAL_SIGNAL_DESIGN_NOT_AUTHORIZED", "CLI_IDENTITY_MISMATCH", "PYTHON_INTERPRETER_MISMATCH",
    "LAUNCHER_MODULE_MISMATCH", "ARGV_CONTRACT_REQUIRED", "PASSIVE_ARGV_CONTRACT_MISMATCH",
    "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED", "SHELL_PARSING_NOT_AUTHORIZED",
    "ENVIRONMENT_ARGUMENT_NOT_ALLOWED", "CREDENTIAL_ARGUMENT_NOT_ALLOWED",
    "PROVIDER_ENDPOINT_ARGUMENT_NOT_ALLOWED", "AUTHORIZATION_ARGUMENT_NOT_ALLOWED",
    "PROXY_ARGUMENT_NOT_ALLOWED", "ACTIVATION_ARGUMENT_NOT_ALLOWED", "NETWORK_ARGUMENT_NOT_ALLOWED",
    "WORKLOAD_ARGUMENT_NOT_ALLOWED", "PUBLICATION_ARGUMENT_NOT_ALLOWED", "TRADING_ARGUMENT_NOT_ALLOWED",
    "PASSIVE_MODE_REQUIRED", "ACTIVE_MODE_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED",
    "WORKLOAD_GATE_MUST_REMAIN_CLOSED", "ENVIRONMENT_READ_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PRODUCTION_CLI_IMPLEMENTATION_NOT_AUTHORIZED", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED",
    "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED", "REAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
    "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED", "PROCESS_CONTROL_NOT_AUTHORIZED", "SIGNAL_SET_MISMATCH",
    "SIGNAL_HANDLER_IO_NOT_AUTHORIZED", "SIGNAL_HANDLER_LIVE_ACTION_NOT_AUTHORIZED",
    "INVALID_SIGNAL_TRANSITION", "RELOAD_NOT_AUTHORIZED", "UNKNOWN_REAL_SIGNAL",
    "GRACEFUL_SHUTDOWN_REQUIRED", "SHUTDOWN_TIMEOUT_REQUIRED", "OPERATOR_ATTESTATION_REQUIRED",
    "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE",
    "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED",
    "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED", "DAEMON_RELOAD_NOT_AUTHORIZED",
    "SERVICE_ENABLEMENT_NOT_AUTHORIZED", "SERVICE_START_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_MATERIAL_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


@dataclass(frozen=True, slots=True, init=False)
class _MetadataRecord:
    """Frozen caller-supplied metadata with no generated or external values."""

    values: tuple[tuple[str, object], ...]

    def __init__(self, **values: object) -> None:
        object.__setattr__(self, "values", tuple(values.items()))

    def __getattr__(self, name: str) -> object:
        for key, value in self.values:
            if key == name:
                return value
        raise AttributeError(name)


class ProductionCliRealSignalBoundaryPolicyV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliIdentityV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliArgumentContractV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliInvocationModeV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliExitClassificationV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliEnvironmentBoundaryV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliCredentialBoundaryV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliActivationBoundaryV1(_MetadataRecord):
    __slots__ = ()


class RealSignalBoundaryIdentityV1(_MetadataRecord):
    __slots__ = ()


class RealSignalRegistrationPolicyV1(_MetadataRecord):
    __slots__ = ()


class RealSignalTransitionPolicyV1(_MetadataRecord):
    __slots__ = ()


class RealSignalShutdownPolicyV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliRealSignalReadinessChecklistV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliRealSignalOperatorAttestationV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliRealSignalIndependentReviewerApprovalV1(_MetadataRecord):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ProductionCliRealSignalFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


class ProductionCliRealSignalDecisionV1(_MetadataRecord):
    __slots__ = ()


class ProductionCliRealSignalAuditEvidenceV1(_MetadataRecord):
    __slots__ = ()


def _codes(*codes: str) -> tuple[str, ...]:
    selected = set(codes)
    return tuple(code for code in _ORDER if code in selected)


def _flag(record: object, name: str) -> bool:
    return bool(getattr(record, name))


def _add(codes: list[str], condition: bool, code: str) -> None:
    if condition:
        codes.append(code)


def _authorities() -> dict[str, bool]:
    return {
        "production_cli_boundary_design_authorized": True,
        "real_signal_handling_boundary_design_authorized": True,
        "argv_contract_design_authorized": True,
        "production_cli_implementation_authorized": False,
        "real_signal_registration_implementation_authorized": False,
        "production_cli_execution_authorized": False,
        "production_runtime_execution_authorized": False,
        "argv_access_authorized": False,
        "environment_read_authorized": False,
        "filesystem_read_authorized": False,
        "filesystem_write_authorized": False,
        "systemd_access_authorized": False,
        "process_control_authorized": False,
        "subprocess_authorized": False,
        "thread_start_authorized": False,
        "event_loop_start_authorized": False,
        "credential_value_access_authorized": False,
        "credential_loading_authorized": False,
        "credential_validation_authorized": False,
        "provider_transmission_authorized": False,
        "scanner_execution_authorized": False,
        "worker_start_authorized": False,
        "scheduler_start_authorized": False,
        "telegram_start_authorized": False,
        "database_mutation_authorized": False,
        "artifact_publication_authorized": False,
        "trading_authorized": False,
        "systemd_unit_file_generation_authorized": False,
        "systemd_drop_in_generation_authorized": False,
        "service_unit_installation_authorized": False,
        "daemon_reload_authorized": False,
        "service_enablement_authorized": False,
        "service_start_restart_authorized": False,
        "runtime_activation_authorized": False,
        "publication_authorized": False,
        "fail_closed": True,
    }


def _valid_evidence(
    policy: ProductionCliRealSignalBoundaryPolicyV1,
    cli: ProductionCliIdentityV1,
    signal: RealSignalBoundaryIdentityV1,
    checklist: ProductionCliRealSignalReadinessChecklistV1,
    operator: ProductionCliRealSignalOperatorAttestationV1,
    reviewer: ProductionCliRealSignalIndependentReviewerApprovalV1,
) -> bool:
    return (
        operator.operator_identity != "" and operator.operator_role == "OPERATOR"
        and reviewer.reviewer_identity != "" and reviewer.reviewer_role == "INDEPENDENT_REVIEWER"
        and operator.policy_id == policy.policy_id == reviewer.policy_id
        and operator.cli_id == cli.cli_id == reviewer.cli_id
        and operator.signal_boundary_id == signal.signal_boundary_id == reviewer.signal_boundary_id
        and operator.checklist_id == checklist.checklist_id == reviewer.checklist_id
        and reviewer.attestation_id == operator.attestation_id
        and _flag(operator, "passive_only_confirmed")
        and _flag(operator, "argv_access_unauthorized_confirmed")
        and _flag(operator, "signal_registration_unauthorized_confirmed")
        and _flag(operator, "all_gates_closed_confirmed")
        and _flag(operator, "live_authorities_false_confirmed")
        and not _flag(operator, "sensitive_evidence_retained") and _flag(operator, "attestation_complete")
        and _flag(reviewer, "passive_only_confirmed")
        and _flag(reviewer, "argv_access_unauthorized_confirmed")
        and _flag(reviewer, "signal_registration_unauthorized_confirmed")
        and _flag(reviewer, "all_gates_closed_confirmed")
        and _flag(reviewer, "live_authorities_false_confirmed")
        and not _flag(reviewer, "sensitive_evidence_retained") and _flag(reviewer, "approved")
        and _flag(reviewer, "review_complete") and _flag(checklist, "checklist_complete")
        and _flag(checklist, "evidence_fresh")
    )


def _validate(
    policy: ProductionCliRealSignalBoundaryPolicyV1,
    cli: ProductionCliIdentityV1,
    argv: ProductionCliArgumentContractV1,
    mode: ProductionCliInvocationModeV1,
    exits: ProductionCliExitClassificationV1,
    environment: ProductionCliEnvironmentBoundaryV1,
    credential: ProductionCliCredentialBoundaryV1,
    activation: ProductionCliActivationBoundaryV1,
    signal: RealSignalBoundaryIdentityV1,
    registration: RealSignalRegistrationPolicyV1,
    transitions: RealSignalTransitionPolicyV1,
    shutdown: RealSignalShutdownPolicyV1,
    checklist: ProductionCliRealSignalReadinessChecklistV1,
    operator: ProductionCliRealSignalOperatorAttestationV1 | None,
    reviewer: ProductionCliRealSignalIndependentReviewerApprovalV1 | None,
    evaluation_time: datetime,
) -> tuple[str, ...]:
    codes: list[str] = []
    _add(codes, not isinstance(policy.policy_id, str) or not policy.policy_id, "POLICY_ID_EMPTY")
    _add(codes, not isinstance(policy.policy_version, str) or not policy.policy_version, "POLICY_VERSION_EMPTY")
    _add(codes, not _flag(policy, "production_cli_boundary_design_authorized"), "PRODUCTION_CLI_DESIGN_NOT_AUTHORIZED")
    _add(codes, not _flag(policy, "real_signal_handling_boundary_design_authorized"), "REAL_SIGNAL_DESIGN_NOT_AUTHORIZED")
    _add(codes, cli.service_unit != "ai-crypto-signal-agent.service" or cli.service_user != "ai-crypto-signal-agent" or cli.service_group != "ai-crypto-signal-agent" or cli.working_directory != "/opt/ai-crypto-signal-agent" or cli.invocation_kind != "PYTHON_MODULE_CLI" or not _flag(cli, "passive_default") or not _flag(cli, "production_cli_design_authorized"), "CLI_IDENTITY_MISMATCH")
    _add(codes, cli.interpreter_path != _PYTHON, "PYTHON_INTERPRETER_MISMATCH")
    _add(codes, cli.launcher_module != _MODULE, "LAUNCHER_MODULE_MISMATCH")
    _add(codes, not _flag(argv, "argv_contract_defined"), "ARGV_CONTRACT_REQUIRED")
    _add(codes, argv.canonical_arguments != ("--mode", "passive"), "PASSIVE_ARGV_CONTRACT_MISMATCH")
    _add(codes, _flag(argv, "argv_access_authorized") or _flag(argv, "implicit_argv_read_allowed"), "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED")
    _add(codes, _flag(argv, "shell_parsing_allowed"), "SHELL_PARSING_NOT_AUTHORIZED")
    _add(codes, _flag(argv, "environment_argument_allowed"), "ENVIRONMENT_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "credential_argument_allowed"), "CREDENTIAL_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "provider_endpoint_argument_allowed"), "PROVIDER_ENDPOINT_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "authorization_argument_allowed"), "AUTHORIZATION_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "proxy_argument_allowed"), "PROXY_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "activation_argument_allowed"), "ACTIVATION_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "network_argument_allowed"), "NETWORK_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "workload_argument_allowed"), "WORKLOAD_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "publication_argument_allowed"), "PUBLICATION_ARGUMENT_NOT_ALLOWED")
    _add(codes, _flag(argv, "trading_argument_allowed"), "TRADING_ARGUMENT_NOT_ALLOWED")
    _add(codes, mode.requested_mode != "PASSIVE" or mode.default_mode != "PASSIVE" or not _flag(mode, "passive_mode_supported") or not _flag(mode, "passive_mode_required") or not _flag(policy, "passive_default_required"), "PASSIVE_MODE_REQUIRED")
    _add(codes, _flag(mode, "active_mode_supported"), "ACTIVE_MODE_NOT_AUTHORIZED")
    _add(codes, _flag(mode, "activation_gate_open") or _flag(activation, "activation_gate_open"), "ACTIVATION_GATE_MUST_REMAIN_CLOSED")
    _add(codes, _flag(mode, "credential_gate_open") or _flag(credential, "credential_gate_open"), "CREDENTIAL_GATE_MUST_REMAIN_CLOSED")
    _add(codes, _flag(mode, "network_gate_open") or _flag(activation, "network_gate_open"), "NETWORK_GATE_MUST_REMAIN_CLOSED")
    _add(codes, _flag(mode, "workload_gate_open") or _flag(activation, "workload_gate_open"), "WORKLOAD_GATE_MUST_REMAIN_CLOSED")
    _add(codes, any(_flag(environment, name) for name in ("environment_read_authorized", "environment_file_allowed", "dotenv_allowed", "secret_environment_allowed", "environment_dump_allowed", "implicit_locale_read_allowed", "implicit_terminal_read_allowed")) or not _flag(environment, "environment_boundary_ready"), "ENVIRONMENT_READ_NOT_AUTHORIZED")
    _add(codes, _flag(credential, "credential_access_authorized") or _flag(policy, "credential_value_access_authorized"), "CREDENTIAL_ACCESS_NOT_AUTHORIZED")
    _add(codes, _flag(credential, "credential_loading_authorized") or _flag(credential, "credential_validation_authorized") or _flag(policy, "credential_loading_authorized") or _flag(policy, "credential_validation_authorized"), "CREDENTIAL_LOADING_NOT_AUTHORIZED")
    _add(codes, _flag(cli, "production_cli_implementation_authorized") or _flag(policy, "production_cli_implementation_authorized"), "PRODUCTION_CLI_IMPLEMENTATION_NOT_AUTHORIZED")
    _add(codes, _flag(cli, "production_cli_execution_authorized") or _flag(policy, "production_cli_execution_authorized"), "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED")
    _add(codes, _flag(cli, "production_runtime_execution_authorized"), "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED")
    _add(codes, _flag(signal, "registration_implementation_authorized") or _flag(policy, "real_signal_registration_implementation_authorized"), "REAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED")
    _add(codes, _flag(signal, "real_signal_registration_authorized") or _flag(registration, "real_signal_registration_authorized"), "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED")
    _add(codes, _flag(signal, "process_control_authorized") or _flag(policy, "process_control_authorized"), "PROCESS_CONTROL_NOT_AUTHORIZED")
    _add(codes, signal.supported_signal_names != ("SIGTERM", "SIGINT"), "SIGNAL_SET_MISMATCH")
    _add(codes, _flag(registration, "handlers_blocking_io_allowed"), "SIGNAL_HANDLER_IO_NOT_AUTHORIZED")
    _add(codes, any(_flag(registration, name) for name in ("handlers_credential_loading_allowed", "handlers_provider_access_allowed", "handlers_network_activation_allowed", "handlers_workload_start_allowed", "handlers_publication_allowed", "handlers_database_mutation_allowed")), "SIGNAL_HANDLER_LIVE_ACTION_NOT_AUTHORIZED")
    _add(codes, not _flag(transitions, "transitions_idempotent") or not _flag(transitions, "transitions_keep_gates_closed") or not _flag(transitions, "transitions_keep_live_authorities_false") or transitions.sigterm_transition != ("PASSIVE_READY", "SHUTDOWN_REQUESTED") or transitions.sigint_transition != ("PASSIVE_READY", "SHUTDOWN_REQUESTED"), "INVALID_SIGNAL_TRANSITION")
    _add(codes, transitions.sighup_classification != "RELOAD_NOT_AUTHORIZED", "RELOAD_NOT_AUTHORIZED")
    _add(codes, transitions.unknown_signal_classification != "UNKNOWN_REAL_SIGNAL", "UNKNOWN_REAL_SIGNAL")
    _add(codes, not _flag(shutdown, "graceful_shutdown_required"), "GRACEFUL_SHUTDOWN_REQUIRED")
    _add(codes, not isinstance(shutdown.shutdown_timeout_seconds, int) or shutdown.shutdown_timeout_seconds <= 0, "SHUTDOWN_TIMEOUT_REQUIRED")
    _add(codes, operator is None, "OPERATOR_ATTESTATION_REQUIRED")
    _add(codes, reviewer is None, "REVIEWER_APPROVAL_REQUIRED")
    if operator is not None and reviewer is not None:
        _add(codes, operator.operator_identity == reviewer.reviewer_identity, "OPERATOR_REVIEWER_COLLISION")
        _add(codes, operator.attested_at > evaluation_time or reviewer.reviewed_at > evaluation_time, "EVIDENCE_FROM_FUTURE")
        maximum_age = policy.evidence_max_age_seconds if isinstance(policy.evidence_max_age_seconds, int) and policy.evidence_max_age_seconds >= 0 else 0
        _add(codes, operator.attested_at < evaluation_time - timedelta(seconds=maximum_age) or reviewer.reviewed_at < evaluation_time - timedelta(seconds=maximum_age), "EVIDENCE_STALE")
        _add(codes, operator.expires_at < evaluation_time or reviewer.expires_at < evaluation_time, "EVIDENCE_EXPIRED")
        _add(codes, not _valid_evidence(policy, cli, signal, checklist, operator, reviewer), "RAW_EXCEPTION_EXPOSURE_DETECTED")
    _add(codes, _flag(policy, "systemd_unit_file_generation_authorized") or _flag(policy, "systemd_drop_in_generation_authorized"), "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "service_unit_installation_authorized"), "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "daemon_reload_authorized"), "DAEMON_RELOAD_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "service_enablement_authorized"), "SERVICE_ENABLEMENT_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "service_start_restart_authorized"), "SERVICE_START_NOT_AUTHORIZED")
    _add(codes, _flag(activation, "network_authorized") or _flag(activation, "provider_transmission_authorized") or _flag(policy, "provider_transmission_authorized"), "NETWORK_NOT_AUTHORIZED")
    _add(codes, _flag(activation, "runtime_activation_authorized") or _flag(policy, "runtime_activation_authorized"), "RUNTIME_ACTIVATION_NOT_AUTHORIZED")
    _add(codes, _flag(activation, "publication_authorized") or _flag(policy, "publication_authorized"), "PUBLICATION_NOT_AUTHORIZED")
    _add(codes, _flag(credential, "credential_exposure_detected"), "RAW_CREDENTIAL_EXPOSURE_DETECTED")
    _add(codes, _flag(argv, "provider_endpoint_argument_allowed") or _flag(argv, "authorization_argument_allowed") or _flag(argv, "proxy_argument_allowed"), "PROVIDER_MATERIAL_EXPOSURE_DETECTED")
    _add(codes, not _flag(checklist, "checklist_complete"), "RAW_EXCEPTION_EXPOSURE_DETECTED")
    return _codes(*codes)


def _states() -> tuple[str, ...]:
    return (
        "PRODUCTION_CLI_DESIGN_AUTHORIZED", "PRODUCTION_CLI_IMPLEMENTATION_NOT_AUTHORIZED",
        "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED", "ARGV_CONTRACT_DEFINED",
        "ARGV_ACCESS_NOT_AUTHORIZED", "PASSIVE_MODE_REQUIRED", "REAL_SIGNAL_DESIGN_AUTHORIZED",
        "REAL_SIGNAL_REGISTRATION_NOT_IMPLEMENTED", "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED",
        "PRODUCTION_RUNTIME_NOT_AUTHORIZED", "ACTIVATION_GATE_CLOSED", "CREDENTIAL_GATE_CLOSED",
        "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED", "DEPLOYMENT_BLOCKED",
    )


def evaluate_production_cli_real_signal_boundary_design_v1(
    *, policy: ProductionCliRealSignalBoundaryPolicyV1, cli_identity: ProductionCliIdentityV1,
    argument_contract: ProductionCliArgumentContractV1, invocation_mode: ProductionCliInvocationModeV1,
    exit_classification: ProductionCliExitClassificationV1, environment_boundary: ProductionCliEnvironmentBoundaryV1,
    credential_boundary: ProductionCliCredentialBoundaryV1, activation_boundary: ProductionCliActivationBoundaryV1,
    signal_identity: RealSignalBoundaryIdentityV1, registration_policy: RealSignalRegistrationPolicyV1,
    transition_policy: RealSignalTransitionPolicyV1, shutdown_policy: RealSignalShutdownPolicyV1,
    checklist: ProductionCliRealSignalReadinessChecklistV1,
    operator_attestation: ProductionCliRealSignalOperatorAttestationV1 | None,
    reviewer_approval: ProductionCliRealSignalIndependentReviewerApprovalV1 | None,
    evaluation_time: datetime,
) -> ProductionCliRealSignalDecisionV1:
    codes = _validate(policy, cli_identity, argument_contract, invocation_mode, exit_classification, environment_boundary, credential_boundary, activation_boundary, signal_identity, registration_policy, transition_policy, shutdown_policy, checklist, operator_attestation, reviewer_approval, evaluation_time)
    ready = not codes
    values: dict[str, object] = {
        "policy_id": policy.policy_id, "cli_id": cli_identity.cli_id,
        "signal_boundary_id": signal_identity.signal_boundary_id, "ready": ready,
        "decision_classification": ("PRODUCTION_CLI_AND_REAL_SIGNAL_BOUNDARY_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION" if ready else "NOT_READY"),
        "production_cli_execution_ready": False, "real_signal_registration_ready": False,
        "states": _states(), "failure_codes": codes,
        "failures": tuple(ProductionCliRealSignalFailureV1(code, "fail-closed design rejection", False) for code in codes),
        "deployment_blocked": True,
    }
    values.update(_authorities())
    return ProductionCliRealSignalDecisionV1(**values)


def build_production_cli_real_signal_boundary_design_audit_evidence_v1(
    *, audit_id: str, policy: ProductionCliRealSignalBoundaryPolicyV1,
    cli_identity: ProductionCliIdentityV1, argument_contract: ProductionCliArgumentContractV1,
    invocation_mode: ProductionCliInvocationModeV1, exit_classification: ProductionCliExitClassificationV1,
    environment_boundary: ProductionCliEnvironmentBoundaryV1, credential_boundary: ProductionCliCredentialBoundaryV1,
    activation_boundary: ProductionCliActivationBoundaryV1, signal_identity: RealSignalBoundaryIdentityV1,
    registration_policy: RealSignalRegistrationPolicyV1, transition_policy: RealSignalTransitionPolicyV1,
    shutdown_policy: RealSignalShutdownPolicyV1, checklist: ProductionCliRealSignalReadinessChecklistV1,
    operator_attestation: ProductionCliRealSignalOperatorAttestationV1 | None,
    reviewer_approval: ProductionCliRealSignalIndependentReviewerApprovalV1 | None,
    decision: ProductionCliRealSignalDecisionV1, evaluation_time: datetime,
) -> ProductionCliRealSignalAuditEvidenceV1:
    del argument_contract, invocation_mode, exit_classification, environment_boundary, credential_boundary
    del activation_boundary, registration_policy, transition_policy, shutdown_policy, checklist
    del operator_attestation, reviewer_approval, evaluation_time
    values: dict[str, object] = {
        "audit_id": audit_id, "policy_id": policy.policy_id, "cli_id": cli_identity.cli_id,
        "signal_boundary_id": signal_identity.signal_boundary_id,
        "ready_for_separate_implementation_decision": decision.ready,
        "production_cli_execution_ready": False, "real_signal_registration_ready": False,
        "failure_codes": decision.failure_codes, "deployment_blocked": True,
    }
    values.update(_authorities())
    return ProductionCliRealSignalAuditEvidenceV1(**values)
