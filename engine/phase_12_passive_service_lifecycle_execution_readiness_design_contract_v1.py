"""Pure metadata-only passive lifecycle execution-readiness design."""
from __future__ import annotations

from dataclasses import dataclass


_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY",
    "PASSIVE_LIFECYCLE_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED",
    "PASSIVE_CLI_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED",
    "HOST_SIGNAL_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED",
    "GRACEFUL_SHUTDOWN_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED",
    "PROCESS_EXIT_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED",
    "SYSTEMD_SERVICE_LIFECYCLE_READINESS_DESIGN_NOT_AUTHORIZED",
    "CREDENTIAL_ONBOARDING_READINESS_DESIGN_NOT_AUTHORIZED",
    "PROVIDER_BUDGET_GATE_READINESS_DESIGN_NOT_AUTHORIZED",
    "PRODUCTION_EXECUTION_EVIDENCE_PACKAGE_DESIGN_NOT_AUTHORIZED",
    "PASSIVE_LIFECYCLE_EXECUTION_IMPLEMENTATION_NOT_AUTHORIZED",
    "PASSIVE_CLI_EXECUTION_NOT_AUTHORIZED", "PASSIVE_LAUNCHER_EXECUTION_NOT_AUTHORIZED",
    "COMPONENT_ADAPTER_INVOCATION_NOT_AUTHORIZED",
    "HOST_SIGNAL_BOUNDARY_EVIDENCE_REQUIRED", "LIVE_SIGNAL_ACTION_NOT_AUTHORIZED",
    "GRACEFUL_SHUTDOWN_EVIDENCE_REQUIRED", "HANDLER_RESTORATION_EVIDENCE_REQUIRED",
    "PROCESS_EXIT_BOUNDARY_EVIDENCE_REQUIRED", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED",
    "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED", "SERVICE_UNIT_MISMATCH",
    "SERVICE_MANAGER_SCOPE_MISMATCH", "DEPLOYMENT_STATE_MISMATCH",
    "EXECSTART_METADATA_MISMATCH", "SYSTEMD_ACCESS_NOT_AUTHORIZED",
    "SERVICE_INSTALLATION_NOT_AUTHORIZED", "SERVICE_ENABLEMENT_NOT_AUTHORIZED",
    "SERVICE_START_NOT_AUTHORIZED", "SERVICE_EXECUTION_NOT_AUTHORIZED",
    "PROVIDER_ROUTING_MISMATCH", "MODEL_BINDING_MISMATCH",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "BUDGET_PROFILE_MISMATCH", "PROVIDER_HARD_CAP_EVIDENCE_REQUIRED",
    "INTERNAL_SOFT_ALERT_EVIDENCE_REQUIRED", "ESCALATION_COST_EXCEEDS_LIMIT",
    "CREDENTIAL_STORE_MISMATCH", "OWNER_SECRET_ENTRY_NOT_EXECUTED",
    "OWNER_SECRET_ENTRY_EXECUTION_NOT_AUTHORIZED", "API_KEY_NOT_ENTERED",
    "API_KEY_NOT_STORED", "API_KEY_NOT_LOADED", "API_KEY_NOT_VALIDATED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED",
    "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE",
    "EVIDENCE_EXPIRED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "PROVIDER_MATERIAL_EXPOSURE_DETECTED", "RAW_HANDLER_EXPOSURE_DETECTED",
    "PROCESS_METADATA_EXPOSURE_DETECTED", "SYSTEMD_HANDLE_EXPOSURE_DETECTED",
    "AUTHORIZATION_MATERIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)

_DESIGN_AUTHORITIES = (
    ("passive_lifecycle_execution_readiness_design_authorized", "PASSIVE_LIFECYCLE_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("passive_cli_execution_readiness_design_authorized", "PASSIVE_CLI_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("host_signal_execution_readiness_design_authorized", "HOST_SIGNAL_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("graceful_shutdown_execution_readiness_design_authorized", "GRACEFUL_SHUTDOWN_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("handler_restoration_execution_readiness_design_authorized", "HANDLER_RESTORATION_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("process_exit_execution_readiness_design_authorized", "PROCESS_EXIT_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("systemd_service_lifecycle_readiness_design_authorized", "SYSTEMD_SERVICE_LIFECYCLE_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("credential_onboarding_readiness_composition_design_authorized", "CREDENTIAL_ONBOARDING_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("provider_budget_gate_readiness_composition_design_authorized", "PROVIDER_BUDGET_GATE_READINESS_DESIGN_NOT_AUTHORIZED"),
    ("production_execution_evidence_package_design_authorized", "PRODUCTION_EXECUTION_EVIDENCE_PACKAGE_DESIGN_NOT_AUTHORIZED"),
)

_TRUE_REQUIREMENTS = (
    "metadata_only_readiness_evaluation", "caller_supplied_evidence_only",
    "independent_review_required", "all_operational_authorities_must_remain_false",
    "all_gates_must_remain_closed", "deployment_must_remain_blocked", "fail_closed",
)

_FORBIDDEN_AUTHORITIES = (
    ("passive_lifecycle_execution_implementation_authorized", "PASSIVE_LIFECYCLE_EXECUTION_IMPLEMENTATION_NOT_AUTHORIZED"),
    ("passive_cli_execution_authorized", "PASSIVE_CLI_EXECUTION_NOT_AUTHORIZED"),
    ("passive_launcher_execution_authorized", "PASSIVE_LAUNCHER_EXECUTION_NOT_AUTHORIZED"),
    ("component_adapter_invocation_authorized", "COMPONENT_ADAPTER_INVOCATION_NOT_AUTHORIZED"),
    ("production_service_execution_authorized", "SERVICE_EXECUTION_NOT_AUTHORIZED"),
    ("production_runtime_execution_authorized", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
    ("credential_loading_authorized", "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
    ("credential_value_access_authorized", "CREDENTIAL_ACCESS_NOT_AUTHORIZED"),
    ("systemd_access_authorized", "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
    ("provider_transmission_authorized", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
    ("operating_system_exit_code_return_authorized", "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED"),
    ("production_process_exit_execution_authorized", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
    ("process_termination_authorized", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
    ("process_signal_transmission_authorized", "LIVE_SIGNAL_ACTION_NOT_AUTHORIZED"),
)

_GATES = (
    ("activation_gate_open", "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
    ("credential_gate_open", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
    ("network_gate_open", "NETWORK_GATE_MUST_REMAIN_CLOSED"),
    ("workload_gate_open", "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
)


@dataclass(frozen=True, slots=True, init=False)
class _Record:
    """A frozen, slotted caller-supplied metadata record."""

    values: tuple[tuple[str, object], ...]

    def __init__(self, **values: object) -> None:
        object.__setattr__(self, "values", tuple(values.items()))

    def __getattr__(self, name: str) -> object:
        for key, value in self.values:
            if key == name:
                return value
        raise AttributeError(name)


class PassiveLifecycleExecutionReadinessPolicyV1(_Record):
    __slots__ = ()


class PassiveLifecycleExecutionReadinessIdentityV1(_Record):
    __slots__ = ()


class PassiveCliExecutionReadinessEvidenceV1(_Record):
    __slots__ = ()


class HostSignalExecutionReadinessEvidenceV1(_Record):
    __slots__ = ()


class GracefulShutdownExecutionReadinessEvidenceV1(_Record):
    __slots__ = ()


class HandlerRestorationExecutionReadinessEvidenceV1(_Record):
    __slots__ = ()


class ProcessExitExecutionReadinessEvidenceV1(_Record):
    __slots__ = ()


class SystemdServiceLifecycleReadinessEvidenceV1(_Record):
    __slots__ = ()


class CredentialOnboardingReadinessEvidenceV1(_Record):
    __slots__ = ()


class ProviderBudgetGateReadinessEvidenceV1(_Record):
    __slots__ = ()


class ProductionExecutionReadinessChecklistV1(_Record):
    __slots__ = ()


class ProductionExecutionOperatorAttestationV1(_Record):
    __slots__ = ()


class ProductionExecutionIndependentReviewerApprovalV1(_Record):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class PassiveLifecycleExecutionReadinessFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


class PassiveLifecycleExecutionReadinessDecisionV1(_Record):
    __slots__ = ()


class PassiveLifecycleExecutionReadinessAuditEvidenceV1(_Record):
    __slots__ = ()


def _value(record: object, name: str, default: object = False) -> object:
    return getattr(record, name, default)


def _ordered_codes(codes: tuple[str, ...]) -> tuple[str, ...]:
    present = set(codes)
    return tuple(code for code in _ORDER if code in present)


def _closed_metadata(codes: tuple[str, ...]) -> dict[str, object]:
    return {
        "failure_codes": codes,
        "failures": tuple(
            PassiveLifecycleExecutionReadinessFailureV1(
                failure_code=code,
                safe_message="fail-closed metadata-only readiness rejection",
                retryable=False,
            )
            for code in codes
        ),
        "activation_gate_open": False,
        "credential_gate_open": False,
        "network_gate_open": False,
        "workload_gate_open": False,
        "passive_lifecycle_execution_implementation_authorized": False,
        "passive_cli_execution_authorized": False,
        "passive_launcher_execution_authorized": False,
        "component_adapter_invocation_authorized": False,
        "production_service_execution_authorized": False,
        "production_runtime_execution_authorized": False,
        "credential_loading_authorized": False,
        "credential_value_access_authorized": False,
        "systemd_access_authorized": False,
        "provider_transmission_authorized": False,
        "operating_system_exit_code_returned": False,
        "process_exit_executed": False,
        "process_terminated": False,
        "signal_transmitted": False,
        "systemd_contacted": False,
        "service_executed": False,
        "production_runtime_executed": False,
        "owner_secret_entry_authorized": True,
        "owner_secret_entry_executed": False,
        "api_key_entered": False,
        "api_key_stored": False,
        "api_key_loaded": False,
        "api_key_validated": False,
        "deployment_blocked": True,
        "fail_closed": True,
    }


def _policy_codes(policy: PassiveLifecycleExecutionReadinessPolicyV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not _value(policy, "policy_id", ""):
        codes.append("POLICY_ID_EMPTY")
    if not _value(policy, "policy_version", ""):
        codes.append("POLICY_VERSION_EMPTY")
    for field, code in _DESIGN_AUTHORITIES:
        if not _value(policy, field):
            codes.append(code)
    for field in _TRUE_REQUIREMENTS:
        if not _value(policy, field):
            codes.append("PASSIVE_LIFECYCLE_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED")
    for field, code in _FORBIDDEN_AUTHORITIES:
        if _value(policy, field):
            codes.append(code)
    for field, code in _GATES:
        if _value(policy, field):
            codes.append(code)
    return _ordered_codes(tuple(codes))


def evaluate_passive_lifecycle_execution_readiness_design_v1(
    *, policy: PassiveLifecycleExecutionReadinessPolicyV1, evidence: tuple[object, ...]
) -> PassiveLifecycleExecutionReadinessDecisionV1:
    """Evaluate supplied evidence without executing, loading, or contacting anything."""

    codes = list(_policy_codes(policy))
    if not evidence:
        codes.append("HOST_SIGNAL_BOUNDARY_EVIDENCE_REQUIRED")
    ordered = _ordered_codes(tuple(codes))
    metadata = _closed_metadata(ordered)
    metadata.update(
        ready=not ordered,
        readiness_classification=(
            "PASSIVE_SERVICE_LIFECYCLE_READY_FOR_SEPARATE_OWNER_EXECUTION_AUTHORIZATION_DECISION"
            if not ordered else "BLOCKED"
        ),
        production_execution_classification=(
            "BLOCKED_PENDING_OWNER_SECRET_ENTRY_AND_SEPARATE_EXECUTION_AUTHORIZATION"
        ),
        accepted_evidence=tuple(evidence),
        credential_readiness_classification="PROCEDURE_READY_BUT_SECRET_NOT_ENTERED",
    )
    return PassiveLifecycleExecutionReadinessDecisionV1(**metadata)


def compose_passive_lifecycle_execution_readiness_without_execution_v1(
    *, decision: PassiveLifecycleExecutionReadinessDecisionV1, composition_id: str
) -> PassiveLifecycleExecutionReadinessDecisionV1:
    """Wrap a decision in immutable composition metadata; no component is invoked."""

    codes = _ordered_codes(tuple(_value(decision, "failure_codes", ())))
    metadata = _closed_metadata(codes)
    metadata.update(
        composition_id=composition_id,
        ready=_value(decision, "ready", False),
        readiness_classification=_value(decision, "readiness_classification", "BLOCKED"),
        production_execution_classification=_value(
            decision,
            "production_execution_classification",
            "BLOCKED_PENDING_OWNER_SECRET_ENTRY_AND_SEPARATE_EXECUTION_AUTHORIZATION",
        ),
    )
    return PassiveLifecycleExecutionReadinessDecisionV1(**metadata)


def build_passive_lifecycle_execution_readiness_audit_evidence_v1(
    *, evidence_id: str,
    decision: PassiveLifecycleExecutionReadinessDecisionV1,
    composition: PassiveLifecycleExecutionReadinessDecisionV1,
) -> PassiveLifecycleExecutionReadinessAuditEvidenceV1:
    """Build redacted, immutable audit metadata from already-supplied records."""

    codes = _ordered_codes(
        tuple(_value(decision, "failure_codes", ()))
        + tuple(_value(composition, "failure_codes", ()))
    )
    metadata = _closed_metadata(codes)
    metadata.update(
        evidence_id=evidence_id,
        ready=_value(decision, "ready", False),
        readiness_classification=_value(decision, "readiness_classification", "BLOCKED"),
        production_execution_classification=_value(
            decision,
            "production_execution_classification",
            "BLOCKED_PENDING_OWNER_SECRET_ENTRY_AND_SEPARATE_EXECUTION_AUTHORIZATION",
        ),
        composition_id=_value(composition, "composition_id", ""),
    )
    return PassiveLifecycleExecutionReadinessAuditEvidenceV1(**metadata)
