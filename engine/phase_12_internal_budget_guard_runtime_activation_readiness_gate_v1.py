"""Pure, fail-closed readiness evidence for a separately authorized activation decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


_FAILURES = frozenset((
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "BUDGET_POLICY_ID_MISMATCH",
    "RUNTIME_POLICY_ID_MISMATCH", "PRICING_POLICY_ID_MISMATCH",
    "RESERVATION_POLICY_ID_MISMATCH", "USAGE_LEDGER_POLICY_ID_MISMATCH",
    "ALERT_POLICY_ID_MISMATCH", "PROVIDER_ID_MISMATCH", "ROUTING_LEVEL_MISMATCH",
    "EXACT_MODEL_ID_MISMATCH", "LOCKED_BUDGET_TARGET_MISMATCH",
    "PROVIDER_HARD_CAP_NOT_CONFIRMED", "NATIVE_SOFT_ALERT_EXCEPTION_MISMATCH",
    "INTERNAL_SOFT_ALERT_NOT_READY", "PRICING_NOT_REVALIDATED",
    "RESERVATION_BOUNDARY_NOT_READY", "USAGE_LEDGER_BOUNDARY_NOT_READY",
    "PRE_RESERVATION_EVALUATION_NOT_READY", "PRE_TRANSMISSION_REVALIDATION_NOT_READY",
    "STALE_USAGE_BLOCK_NOT_READY", "BUDGET_CHANGE_BLOCK_NOT_READY",
    "DAILY_LIMIT_BLOCK_NOT_READY", "MONTHLY_LIMIT_BLOCK_NOT_READY",
    "HARD_LIMIT_BLOCK_NOT_READY", "ALERT_INTENT_NOT_READY", "KILL_SWITCH_INTENT_NOT_READY",
    "AUTOMATIC_RETRY_NOT_AUTHORIZED", "MANUAL_RECOVERY_NOT_READY",
    "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED",
    "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE",
    "EVIDENCE_EXPIRED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "RUNTIME_CONFIGURATION_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "ALERT_PUBLICATION_NOT_AUTHORIZED", "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED",
    "PUBLICATION_NOT_AUTHORIZED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "RAW_PROVIDER_RESPONSE_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
))


@dataclass(frozen=True, slots=True)
class BudgetGuardActivationReadinessPolicyV1:
    policy_id: str = ""
    policy_version: str = ""
    deployment_environment: str = ""
    required_budget_policy_id: str = ""
    required_runtime_integration_policy_id: str = ""
    required_pricing_policy_id: str = ""
    required_reservation_policy_id: str = ""
    required_usage_ledger_policy_id: str = ""
    required_alert_kill_switch_policy_id: str = ""
    required_provider_route_bindings: tuple[tuple[str, str, str, str], ...] = ()
    required_budget_target_id: str = ""
    require_provider_hard_caps_confirmed: bool = False
    require_internal_soft_alerts_implemented: bool = False
    require_daily_monthly_caps: bool = False
    require_pricing_revalidation: bool = False
    require_pre_call_reservation: bool = False
    require_usage_ledger_alignment: bool = False
    require_pre_reservation_budget_evaluation: bool = False
    require_pre_transmission_budget_revalidation: bool = False
    require_alert_intent: bool = False
    require_kill_switch_intent: bool = False
    require_manual_recovery: bool = False
    require_zero_automatic_retry: bool = False
    require_deterministic_audit_evidence: bool = False
    require_independent_reviewer: bool = False
    require_evidence_freshness: bool = False
    runtime_activation_authorized: bool = False
    runtime_configuration_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    publication_authorized: bool = False
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class BudgetGuardBoundaryAttestationV1:
    boundary_attestation_id: str = ""
    policy_id: str = ""
    budget_policy_id: str = ""
    runtime_integration_policy_id: str = ""
    pricing_policy_id: str = ""
    reservation_policy_id: str = ""
    usage_ledger_policy_id: str = ""
    alert_kill_switch_policy_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    locked_budget_target_id: str = ""
    provider_hard_caps_confirmed: bool = False
    native_soft_alert_exception_preserved: bool = True
    internal_soft_alerts_implemented: bool = True
    daily_monthly_caps_confirmed: bool = False
    route_limits_confirmed: bool = False
    token_call_limits_confirmed: bool = False
    escalation_limits_confirmed: bool = False
    pricing_revalidation_ready: bool = False
    reservation_boundary_ready: bool = False
    usage_ledger_boundary_ready: bool = False
    alert_kill_switch_boundary_ready: bool = False
    runtime_integration_boundary_ready: bool = False
    authority_invariants_confirmed: bool = False
    redaction_invariants_confirmed: bool = False
    deterministic_failures_confirmed: bool = False
    audit_purity_confirmed: bool = False
    attested_at: datetime | None = None
    evidence_expires_at: datetime | None = None
    attestation_complete: bool = False
    attestation_ready: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardRuntimeIntegrationAttestationV1:
    runtime_integration_attestation_id: str = ""
    policy_id: str = ""
    runtime_integration_policy_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    pre_reservation_evaluation_ready: bool = False
    pre_transmission_revalidation_ready: bool = False
    stale_usage_block_ready: bool = False
    budget_change_block_ready: bool = False
    soft_threshold_suppression_ready: bool = False
    daily_limit_block_ready: bool = False
    monthly_hard_limit_block_ready: bool = False
    alert_intent_nonexecuting: bool = False
    kill_switch_intent_nonexecuting: bool = False
    manual_recovery_ready: bool = False
    automatic_retry_disabled: bool = False
    reservation_mutation_absent: bool = False
    provider_transmission_absent: bool = False
    runtime_activation_absent: bool = False
    attested_at: datetime | None = None
    evidence_expires_at: datetime | None = None
    attestation_complete: bool = False
    attestation_ready: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardOperatorReadinessAttestationV1:
    operator_attestation_id: str = ""
    policy_id: str = ""
    boundary_attestation_id: str = ""
    runtime_integration_attestation_id: str = ""
    operator_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    locked_budget_target_id: str = ""
    checklist_complete: bool = False
    hard_caps_confirmed: bool = False
    internal_soft_alerts_confirmed: bool = False
    pricing_reservation_ledger_confirmed: bool = False
    runtime_guard_confirmed: bool = False
    alert_kill_switch_confirmed: bool = False
    manual_recovery_confirmed: bool = False
    authority_invariants_confirmed: bool = False
    attested_at: datetime | None = None
    evidence_expires_at: datetime | None = None
    attestation_complete: bool = False
    attestation_ready: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardReviewerApprovalV1:
    review_id: str = ""
    policy_id: str = ""
    operator_attestation_id: str = ""
    boundary_attestation_id: str = ""
    runtime_integration_attestation_id: str = ""
    reviewer_id: str = ""
    operator_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    locked_budget_target_id: str = ""
    hard_caps_confirmed: bool = False
    internal_soft_alerts_confirmed: bool = False
    pricing_reservation_ledger_confirmed: bool = False
    runtime_guard_confirmed: bool = False
    alert_kill_switch_confirmed: bool = False
    manual_recovery_confirmed: bool = False
    authority_invariants_confirmed: bool = False
    approved: bool = False
    reviewed_at: datetime | None = None
    evidence_expires_at: datetime | None = None
    review_complete: bool = False
    review_ready: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardActivationFailureV1:
    failure_code: str = ""
    safe_message: str = ""
    retryable: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardActivationReadinessDecisionV1:
    policy_id: str = ""
    boundary_attestation_id: str = ""
    runtime_integration_attestation_id: str = ""
    operator_attestation_id: str = ""
    review_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    locked_budget_target_id: str = ""
    provider_hard_cap_ready: bool = False
    internal_soft_alert_ready: bool = False
    pricing_ready: bool = False
    reservation_ready: bool = False
    usage_ledger_ready: bool = False
    runtime_guard_ready: bool = False
    alert_intent_ready: bool = False
    kill_switch_intent_ready: bool = False
    manual_recovery_ready: bool = False
    operator_attestation_ready: bool = False
    independent_review_ready: bool = False
    evidence_fresh: bool = False
    failure_codes: tuple[str, ...] = ()
    runtime_activation_authorized: bool = False
    runtime_configuration_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    publication_authorized: bool = False
    ready: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardActivationAuditEvidenceV1:
    policy_id: str = ""
    boundary_attestation_id: str = ""
    runtime_integration_attestation_id: str = ""
    operator_attestation_id: str = ""
    review_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    locked_budget_target_id: str = ""
    operator_id: str = ""
    reviewer_id: str = ""
    provider_hard_cap_ready: bool = False
    internal_soft_alert_ready: bool = False
    pricing_ready: bool = False
    reservation_ready: bool = False
    usage_ledger_ready: bool = False
    runtime_guard_ready: bool = False
    alert_intent_ready: bool = False
    kill_switch_intent_ready: bool = False
    manual_recovery_ready: bool = False
    evidence_fresh: bool = False
    failure_codes: tuple[str, ...] = ()
    runtime_activation_authorized: bool = False
    runtime_configuration_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    publication_authorized: bool = False
    evidence_ready: bool = False


def _blank(value: str) -> bool:
    return not isinstance(value, str) or not value.strip()


def _ordered(codes: set[str]) -> tuple[str, ...]:
    return tuple(sorted(code for code in codes if code in _FAILURES))


def _authority_failures(policy: BudgetGuardActivationReadinessPolicyV1) -> set[str]:
    values = (
        (policy.runtime_activation_authorized, "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        (policy.runtime_configuration_authorized, "RUNTIME_CONFIGURATION_NOT_AUTHORIZED"),
        (policy.credential_loading_authorized, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        (policy.network_authorized, "NETWORK_NOT_AUTHORIZED"),
        (policy.provider_transmission_authorized, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        (policy.alert_publication_authorized, "ALERT_PUBLICATION_NOT_AUTHORIZED"),
        (policy.kill_switch_activation_authorized, "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED"),
        (policy.publication_authorized, "PUBLICATION_NOT_AUTHORIZED"),
    )
    return {code for asserted, code in values if asserted}


def _freshness(failures: set[str], evaluated_at: datetime, *values: tuple[datetime | None, datetime | None]) -> bool:
    fresh = True
    for attested_at, expires_at in values:
        if attested_at is None or expires_at is None:
            failures.add("EVIDENCE_STALE")
            fresh = False
        elif attested_at > evaluated_at:
            failures.add("EVIDENCE_FROM_FUTURE")
            fresh = False
        elif expires_at <= evaluated_at:
            failures.add("EVIDENCE_EXPIRED")
            fresh = False
    return fresh


def evaluate_budget_guard_activation_readiness_v1(
    policy: BudgetGuardActivationReadinessPolicyV1,
    boundary: BudgetGuardBoundaryAttestationV1,
    runtime: BudgetGuardRuntimeIntegrationAttestationV1,
    operator: BudgetGuardOperatorReadinessAttestationV1,
    review: BudgetGuardReviewerApprovalV1,
    evaluated_at: datetime,
) -> BudgetGuardActivationReadinessDecisionV1:
    """Evaluate supplied, immutable evidence without activating anything."""
    failures = _authority_failures(policy)
    if _blank(policy.policy_id): failures.add("POLICY_ID_EMPTY")
    if _blank(policy.policy_version): failures.add("POLICY_VERSION_EMPTY")
    if _blank(policy.deployment_environment): failures.add("DEPLOYMENT_ENVIRONMENT_EMPTY")
    elif policy.deployment_environment != "CONTROLLED_PRODUCTION": failures.add("DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED")
    if boundary.policy_id != policy.policy_id or runtime.policy_id != policy.policy_id or operator.policy_id != policy.policy_id or review.policy_id != policy.policy_id:
        failures.add("BUDGET_POLICY_ID_MISMATCH")
    if boundary.budget_policy_id != policy.required_budget_policy_id: failures.add("BUDGET_POLICY_ID_MISMATCH")
    if boundary.runtime_integration_policy_id != policy.required_runtime_integration_policy_id or runtime.runtime_integration_policy_id != policy.required_runtime_integration_policy_id:
        failures.add("RUNTIME_POLICY_ID_MISMATCH")
    if boundary.pricing_policy_id != policy.required_pricing_policy_id: failures.add("PRICING_POLICY_ID_MISMATCH")
    if boundary.reservation_policy_id != policy.required_reservation_policy_id: failures.add("RESERVATION_POLICY_ID_MISMATCH")
    if boundary.usage_ledger_policy_id != policy.required_usage_ledger_policy_id: failures.add("USAGE_LEDGER_POLICY_ID_MISMATCH")
    if boundary.alert_kill_switch_policy_id != policy.required_alert_kill_switch_policy_id: failures.add("ALERT_POLICY_ID_MISMATCH")

    identities = (boundary.boundary_attestation_id, runtime.runtime_integration_attestation_id, operator.operator_attestation_id, review.review_id)
    if any(_blank(value) for value in identities): failures.add("OPERATOR_ATTESTATION_REQUIRED")
    binding = (boundary.provider_id, boundary.routing_level, boundary.exact_provider_model_id)
    expected_bindings = {(provider, route, model) for provider, route, _, model in policy.required_provider_route_bindings}
    if binding not in expected_bindings:
        failures.add("PROVIDER_ID_MISMATCH")
    if runtime.provider_id != boundary.provider_id or operator.provider_id != boundary.provider_id or review.provider_id != boundary.provider_id:
        failures.add("PROVIDER_ID_MISMATCH")
    if runtime.routing_level != boundary.routing_level or operator.routing_level != boundary.routing_level or review.routing_level != boundary.routing_level:
        failures.add("ROUTING_LEVEL_MISMATCH")
    if runtime.exact_provider_model_id != boundary.exact_provider_model_id or operator.exact_provider_model_id != boundary.exact_provider_model_id or review.exact_provider_model_id != boundary.exact_provider_model_id:
        failures.add("EXACT_MODEL_ID_MISMATCH")
    if any(value != policy.required_budget_target_id for value in (boundary.locked_budget_target_id, operator.locked_budget_target_id, review.locked_budget_target_id)):
        failures.add("LOCKED_BUDGET_TARGET_MISMATCH")

    if not boundary.provider_hard_caps_confirmed: failures.add("PROVIDER_HARD_CAP_NOT_CONFIRMED")
    if not boundary.native_soft_alert_exception_preserved: failures.add("NATIVE_SOFT_ALERT_EXCEPTION_MISMATCH")
    if not boundary.internal_soft_alerts_implemented: failures.add("INTERNAL_SOFT_ALERT_NOT_READY")
    if not boundary.pricing_revalidation_ready: failures.add("PRICING_NOT_REVALIDATED")
    if not boundary.reservation_boundary_ready: failures.add("RESERVATION_BOUNDARY_NOT_READY")
    if not boundary.usage_ledger_boundary_ready: failures.add("USAGE_LEDGER_BOUNDARY_NOT_READY")
    if not runtime.pre_reservation_evaluation_ready: failures.add("PRE_RESERVATION_EVALUATION_NOT_READY")
    if not runtime.pre_transmission_revalidation_ready: failures.add("PRE_TRANSMISSION_REVALIDATION_NOT_READY")
    if not runtime.stale_usage_block_ready: failures.add("STALE_USAGE_BLOCK_NOT_READY")
    if not runtime.budget_change_block_ready: failures.add("BUDGET_CHANGE_BLOCK_NOT_READY")
    if not runtime.daily_limit_block_ready: failures.add("DAILY_LIMIT_BLOCK_NOT_READY")
    if not runtime.monthly_hard_limit_block_ready:
        failures.update(("MONTHLY_LIMIT_BLOCK_NOT_READY", "HARD_LIMIT_BLOCK_NOT_READY"))
    if not runtime.alert_intent_nonexecuting: failures.add("ALERT_INTENT_NOT_READY")
    if not runtime.kill_switch_intent_nonexecuting: failures.add("KILL_SWITCH_INTENT_NOT_READY")
    if not runtime.automatic_retry_disabled: failures.add("AUTOMATIC_RETRY_NOT_AUTHORIZED")
    if not runtime.manual_recovery_ready: failures.add("MANUAL_RECOVERY_NOT_READY")
    if not all((boundary.daily_monthly_caps_confirmed, boundary.route_limits_confirmed, boundary.token_call_limits_confirmed, boundary.escalation_limits_confirmed, boundary.alert_kill_switch_boundary_ready, boundary.runtime_integration_boundary_ready, boundary.authority_invariants_confirmed, boundary.redaction_invariants_confirmed, boundary.deterministic_failures_confirmed, boundary.audit_purity_confirmed, boundary.attestation_complete, boundary.attestation_ready)):
        failures.add("INTERNAL_SOFT_ALERT_NOT_READY")
    if not all((runtime.soft_threshold_suppression_ready, runtime.reservation_mutation_absent, runtime.provider_transmission_absent, runtime.runtime_activation_absent, runtime.attestation_complete, runtime.attestation_ready)):
        failures.add("PRE_TRANSMISSION_REVALIDATION_NOT_READY")
    if not all((operator.checklist_complete, operator.hard_caps_confirmed, operator.internal_soft_alerts_confirmed, operator.pricing_reservation_ledger_confirmed, operator.runtime_guard_confirmed, operator.alert_kill_switch_confirmed, operator.manual_recovery_confirmed, operator.authority_invariants_confirmed, operator.attestation_complete, operator.attestation_ready)) or _blank(operator.operator_id):
        failures.add("OPERATOR_ATTESTATION_REQUIRED")
    if not all((review.hard_caps_confirmed, review.internal_soft_alerts_confirmed, review.pricing_reservation_ledger_confirmed, review.runtime_guard_confirmed, review.alert_kill_switch_confirmed, review.manual_recovery_confirmed, review.authority_invariants_confirmed, review.approved, review.review_complete, review.review_ready)) or _blank(review.reviewer_id):
        failures.add("REVIEWER_APPROVAL_REQUIRED")
    if review.operator_attestation_id != operator.operator_attestation_id or review.boundary_attestation_id != boundary.boundary_attestation_id or review.runtime_integration_attestation_id != runtime.runtime_integration_attestation_id:
        failures.add("REVIEWER_APPROVAL_REQUIRED")
    if review.operator_id != operator.operator_id or review.reviewer_id == operator.operator_id:
        failures.add("OPERATOR_REVIEWER_COLLISION")
    evidence_fresh = _freshness(failures, evaluated_at, (boundary.attested_at, boundary.evidence_expires_at), (runtime.attested_at, runtime.evidence_expires_at), (operator.attested_at, operator.evidence_expires_at), (review.reviewed_at, review.evidence_expires_at))

    provider_hard_cap_ready = boundary.provider_hard_caps_confirmed
    internal_soft_alert_ready = boundary.native_soft_alert_exception_preserved and boundary.internal_soft_alerts_implemented
    pricing_ready = boundary.pricing_revalidation_ready
    reservation_ready = boundary.reservation_boundary_ready
    usage_ledger_ready = boundary.usage_ledger_boundary_ready
    runtime_guard_ready = runtime.pre_reservation_evaluation_ready and runtime.pre_transmission_revalidation_ready and runtime.runtime_activation_absent
    alert_intent_ready = boundary.alert_kill_switch_boundary_ready and runtime.alert_intent_nonexecuting
    kill_switch_intent_ready = boundary.alert_kill_switch_boundary_ready and runtime.kill_switch_intent_nonexecuting
    manual_recovery_ready = runtime.manual_recovery_ready
    operator_ready = operator.attestation_ready and operator.attestation_complete and bool(operator.operator_id)
    review_ready = review.review_ready and review.review_complete and review.approved and bool(review.reviewer_id) and review.reviewer_id != operator.operator_id
    ordered = _ordered(failures)
    return BudgetGuardActivationReadinessDecisionV1(
        policy.policy_id, boundary.boundary_attestation_id, runtime.runtime_integration_attestation_id,
        operator.operator_attestation_id, review.review_id, boundary.provider_id, boundary.routing_level,
        boundary.exact_provider_model_id, boundary.locked_budget_target_id, provider_hard_cap_ready,
        internal_soft_alert_ready, pricing_ready, reservation_ready, usage_ledger_ready,
        runtime_guard_ready, alert_intent_ready, kill_switch_intent_ready, manual_recovery_ready,
        operator_ready, review_ready, evidence_fresh, ordered, False, False, False, False, False,
        False, False, False, not ordered,
    )


def build_budget_guard_activation_audit_evidence_v1(
    policy: BudgetGuardActivationReadinessPolicyV1,
    boundary: BudgetGuardBoundaryAttestationV1,
    runtime: BudgetGuardRuntimeIntegrationAttestationV1,
    operator: BudgetGuardOperatorReadinessAttestationV1,
    review: BudgetGuardReviewerApprovalV1,
    decision: BudgetGuardActivationReadinessDecisionV1,
) -> BudgetGuardActivationAuditEvidenceV1:
    """Return redacted, immutable caller-supplied metadata without I/O."""
    aligned = (
        decision.policy_id == policy.policy_id
        and decision.boundary_attestation_id == boundary.boundary_attestation_id
        and decision.runtime_integration_attestation_id == runtime.runtime_integration_attestation_id
        and decision.operator_attestation_id == operator.operator_attestation_id
        and decision.review_id == review.review_id
        and decision.provider_id == boundary.provider_id
        and decision.routing_level == boundary.routing_level
        and decision.exact_provider_model_id == boundary.exact_provider_model_id
    )
    if not aligned:
        raise ValueError("readiness identities must align")
    return BudgetGuardActivationAuditEvidenceV1(
        policy.policy_id, boundary.boundary_attestation_id, runtime.runtime_integration_attestation_id,
        operator.operator_attestation_id, review.review_id, boundary.provider_id, boundary.routing_level,
        boundary.exact_provider_model_id, boundary.locked_budget_target_id, operator.operator_id,
        review.reviewer_id, decision.provider_hard_cap_ready, decision.internal_soft_alert_ready,
        decision.pricing_ready, decision.reservation_ready, decision.usage_ledger_ready,
        decision.runtime_guard_ready, decision.alert_intent_ready, decision.kill_switch_intent_ready,
        decision.manual_recovery_ready, decision.evidence_fresh, decision.failure_codes,
        False, False, False, False, False, False, False, False,
        not any((decision.runtime_activation_authorized, decision.runtime_configuration_authorized,
                 decision.credential_loading_authorized, decision.network_authorized,
                 decision.provider_transmission_authorized, decision.alert_publication_authorized,
                 decision.kill_switch_activation_authorized, decision.publication_authorized)),
    )
