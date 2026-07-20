"""Pure, non-executing internal budget guard runtime-integration boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


_ROUTES = {
    "L0": ("DEEPSEEK", "DEEPSEEK_V4_PRO", "deepseek-v4-pro"),
    "L1": ("ANTHROPIC", "CLAUDE_SONNET_5", "claude-sonnet-5"),
    "L2": ("ANTHROPIC", "CLAUDE_OPUS_4_8", "claude-opus-4-8"),
}
_PROVIDER_LIMITS = {
    "DEEPSEEK": (True, Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00"), False),
    "ANTHROPIC": (True, Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00"), False),
}
_ROUTE_LIMITS = {
    "L0": (Decimal("0.02"), Decimal("0.40"), Decimal("12.00"), 12000, 3000, 1, 3),
    "L1": (Decimal("0.12"), Decimal("0.50"), Decimal("15.00"), 12000, 3000, 1, 2),
    "L2": (Decimal("0.20"), Decimal("0.20"), Decimal("6.00"), 12000, 3000, 1, 1),
}
_ESCALATION_LIMITS = (Decimal("0.34"), Decimal("0.32"), True)
_CANONICAL_FAILURES = frozenset((
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "RUNTIME_INPUT_ID_EMPTY", "CORRELATION_ID_EMPTY",
    "BUDGET_POLICY_ID_MISMATCH", "PROVIDER_ID_MISMATCH", "ROUTING_LEVEL_MISMATCH",
    "EXACT_MODEL_ID_MISMATCH", "PROVIDER_USAGE_EVIDENCE_REQUIRED",
    "ROUTE_USAGE_EVIDENCE_REQUIRED", "USAGE_EVIDENCE_STALE", "USAGE_EVIDENCE_EXPIRED",
    "USAGE_EVIDENCE_INCOMPLETE", "PRICING_EVIDENCE_REQUIRED", "PRICING_NOT_REVALIDATED",
    "USAGE_LEDGER_EVIDENCE_REQUIRED", "RESERVATION_EVIDENCE_REQUIRED",
    "RESERVATION_IDENTITY_MISMATCH", "RESERVATION_NOT_ACTIVE", "RESERVATION_EXPIRED",
    "BUDGET_CHANGED_AFTER_RESERVATION", "PROVIDER_ROUTE_NOT_ALLOWED",
    "SOFT_THRESHOLD_SUPPRESSION_REQUIRED", "DAILY_LIMIT_BLOCK_REQUIRED",
    "MONTHLY_LIMIT_BLOCK_REQUIRED", "HARD_LIMIT_BLOCK_REQUIRED", "ALERT_INTENT_REQUIRED",
    "ALERT_PUBLICATION_NOT_AUTHORIZED", "KILL_SWITCH_INTENT_REQUIRED",
    "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED", "AUTOMATIC_RETRY_NOT_AUTHORIZED",
    "MANUAL_RECOVERY_REQUIRED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_PROVIDER_RESPONSE_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
))


@dataclass(frozen=True, slots=True)
class InternalBudgetGuardRuntimePolicyV1:
    policy_id: str = ""
    policy_version: str = ""
    deployment_environment: str = ""
    required_budget_policy_id: str = ""
    require_budget_evaluation_before_reservation: bool = False
    require_budget_evaluation_before_transmission: bool = False
    require_fresh_provider_usage: bool = False
    require_fresh_route_usage: bool = False
    require_pricing_revalidation: bool = False
    require_usage_ledger_alignment: bool = False
    require_reservation_alignment: bool = False
    require_route_allowance: bool = False
    require_provider_allowance: bool = False
    require_soft_threshold_degradation: bool = False
    require_optional_escalation_suppression: bool = False
    require_daily_limit_blocking: bool = False
    require_monthly_limit_blocking: bool = False
    require_hard_limit_kill_switch_intent: bool = False
    require_zero_automatic_retry: bool = False
    require_manual_recovery: bool = False
    require_deterministic_audit_evidence: bool = False
    runtime_activation_authorized: bool = False
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    publication_authorized: bool = False
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class BudgetGuardRuntimeInputV1:
    runtime_input_id: str = ""
    correlation_id: str = ""
    policy_id: str = ""
    budget_policy_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    provider_usage_snapshot_id: str = ""
    route_usage_snapshot_id: str = ""
    pricing_evidence_id: str = ""
    usage_ledger_evidence_id: str = ""
    requested_reservation_id: str = ""
    existing_reservation_state: str = ""
    transmission_attempt_id: str = ""
    current_budget_alert_state: str = ""
    current_kill_switch_state: str = ""
    requested_at: datetime | None = None
    evidence_expires_at: datetime | None = None
    input_complete: bool = False
    input_ready: bool = False
    provider_usage_fresh: bool = False
    route_usage_fresh: bool = False
    pricing_revalidated: bool = False
    usage_ledger_aligned: bool = False
    reservation_aligned: bool = False
    provider_allowance: bool = False
    route_allowance: bool = False
    escalation_allowance: bool = False
    automatic_retry_requested: bool = False
    manual_recovery_resolved: bool = False
    budget_changed_after_reservation: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardReservationDecisionV1:
    reservation_id: str = ""
    may_create_reservation: bool = False
    provider_allowance: bool = False
    route_allowance: bool = False
    escalation_allowance: bool = False
    pricing_ready: bool = False
    ledger_ready: bool = False
    usage_fresh: bool = False
    failure_codes: tuple[str, ...] = ()
    decision_ready: bool = False
    reservation_written: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardTransmissionDecisionV1:
    transmission_attempt_id: str = ""
    may_transmit: bool = False
    reservation_ready: bool = False
    pricing_ready: bool = False
    usage_fresh: bool = False
    failure_codes: tuple[str, ...] = ()
    decision_ready: bool = False
    transmission_attempted: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardAlertIntentV1:
    alert_intent_id: str = ""
    policy_id: str = ""
    correlation_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    alert_classification: str = ""
    severity: str = ""
    reason_codes: tuple[str, ...] = ()
    publication_required: bool = False
    publication_attempted: bool = False
    publication_authorized: bool = False
    created_at: datetime | None = None
    intent_ready: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardKillSwitchIntentV1:
    kill_switch_intent_id: str = ""
    policy_id: str = ""
    correlation_id: str = ""
    provider_id: str = ""
    trigger_classification: str = ""
    trigger_evidence_ids: tuple[str, ...] = ()
    activation_required: bool = False
    activation_attempted: bool = False
    activation_authorized: bool = False
    provider_calls_blocked: bool = False
    new_reservations_blocked: bool = False
    manual_recovery_required: bool = False
    recovery_approval_id: str = ""
    created_at: datetime | None = None
    intent_ready: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardRuntimeFailureV1:
    failure_code: str = ""
    safe_message: str = ""
    retryable: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardRuntimeDecisionV1:
    policy_id: str = ""
    runtime_input_id: str = ""
    correlation_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    reservation_decision: BudgetGuardReservationDecisionV1 = BudgetGuardReservationDecisionV1()
    transmission_decision: BudgetGuardTransmissionDecisionV1 = BudgetGuardTransmissionDecisionV1()
    alert_intent: BudgetGuardAlertIntentV1 = BudgetGuardAlertIntentV1()
    kill_switch_intent: BudgetGuardKillSwitchIntentV1 = BudgetGuardKillSwitchIntentV1()
    provider_allowance: bool = False
    route_allowance: bool = False
    escalation_allowance: bool = False
    pricing_ready: bool = False
    ledger_ready: bool = False
    reservation_ready: bool = False
    usage_fresh: bool = False
    manual_recovery_required: bool = False
    failure_codes: tuple[str, ...] = ()
    runtime_activation_authorized: bool = False
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    publication_authorized: bool = False
    ready: bool = False


@dataclass(frozen=True, slots=True)
class BudgetGuardRuntimeAuditEvidenceV1:
    policy_id: str = ""
    runtime_input_id: str = ""
    correlation_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    provider_usage_snapshot_id: str = ""
    route_usage_snapshot_id: str = ""
    pricing_evidence_id: str = ""
    usage_ledger_evidence_id: str = ""
    requested_reservation_id: str = ""
    transmission_attempt_id: str = ""
    reservation_decision: BudgetGuardReservationDecisionV1 = BudgetGuardReservationDecisionV1()
    transmission_decision: BudgetGuardTransmissionDecisionV1 = BudgetGuardTransmissionDecisionV1()
    alert_intent: BudgetGuardAlertIntentV1 = BudgetGuardAlertIntentV1()
    kill_switch_intent: BudgetGuardKillSwitchIntentV1 = BudgetGuardKillSwitchIntentV1()
    provider_allowance: bool = False
    route_allowance: bool = False
    escalation_allowance: bool = False
    manual_recovery_required: bool = False
    failure_codes: tuple[str, ...] = ()
    runtime_activation_authorized: bool = False
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    publication_authorized: bool = False
    evidence_ready: bool = False


def _ordered(codes: set[str]) -> tuple[str, ...]:
    return tuple(sorted(code for code in codes if code in _CANONICAL_FAILURES))


def _blank(value: str) -> bool:
    return not isinstance(value, str) or not value.strip()


def _authority_failures(policy: InternalBudgetGuardRuntimePolicyV1) -> set[str]:
    values = (
        (policy.runtime_activation_authorized, "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        (policy.alert_publication_authorized, "ALERT_PUBLICATION_NOT_AUTHORIZED"),
        (policy.kill_switch_activation_authorized, "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED"),
        (policy.credential_loading_authorized, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        (policy.network_authorized, "NETWORK_NOT_AUTHORIZED"),
        (policy.provider_transmission_authorized, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        (policy.publication_authorized, "PUBLICATION_NOT_AUTHORIZED"),
    )
    return {code for asserted, code in values if asserted}


def evaluate_budget_guard_runtime_v1(
    policy: InternalBudgetGuardRuntimePolicyV1,
    runtime_input: BudgetGuardRuntimeInputV1,
) -> BudgetGuardRuntimeDecisionV1:
    """Evaluate supplied metadata without activating, writing, or contacting anything."""
    failures: set[str] = _authority_failures(policy)
    if _blank(policy.policy_id):
        failures.add("POLICY_ID_EMPTY")
    if _blank(policy.policy_version):
        failures.add("POLICY_VERSION_EMPTY")
    if _blank(policy.deployment_environment):
        failures.add("DEPLOYMENT_ENVIRONMENT_EMPTY")
    elif policy.deployment_environment != "CONTROLLED_PRODUCTION":
        failures.add("DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED")
    if _blank(runtime_input.runtime_input_id):
        failures.add("RUNTIME_INPUT_ID_EMPTY")
    if _blank(runtime_input.correlation_id):
        failures.add("CORRELATION_ID_EMPTY")
    if runtime_input.policy_id != policy.policy_id or runtime_input.budget_policy_id != policy.required_budget_policy_id:
        failures.add("BUDGET_POLICY_ID_MISMATCH")

    expected = _ROUTES.get(runtime_input.routing_level)
    if expected is None:
        failures.update(("ROUTING_LEVEL_MISMATCH", "PROVIDER_ROUTE_NOT_ALLOWED"))
    else:
        expected_provider, _, expected_model = expected
        if runtime_input.provider_id != expected_provider:
            failures.add("PROVIDER_ID_MISMATCH")
        if runtime_input.exact_provider_model_id != expected_model:
            failures.add("EXACT_MODEL_ID_MISMATCH")
        if not any(
            provider_id == runtime_input.provider_id and model_id == runtime_input.exact_provider_model_id
            for provider_id, _, model_id in _ROUTES.values()
        ):
            failures.add("EXACT_MODEL_ID_MISMATCH")
    if runtime_input.provider_id not in _PROVIDER_LIMITS:
        failures.add("PROVIDER_ROUTE_NOT_ALLOWED")

    if _blank(runtime_input.provider_usage_snapshot_id):
        failures.add("PROVIDER_USAGE_EVIDENCE_REQUIRED")
    if _blank(runtime_input.route_usage_snapshot_id):
        failures.add("ROUTE_USAGE_EVIDENCE_REQUIRED")
    if _blank(runtime_input.pricing_evidence_id):
        failures.add("PRICING_EVIDENCE_REQUIRED")
    if _blank(runtime_input.usage_ledger_evidence_id) or not runtime_input.usage_ledger_aligned:
        failures.add("USAGE_LEDGER_EVIDENCE_REQUIRED")
    if _blank(runtime_input.requested_reservation_id):
        failures.add("RESERVATION_EVIDENCE_REQUIRED")
    if _blank(runtime_input.transmission_attempt_id):
        failures.add("RESERVATION_EVIDENCE_REQUIRED")
    if not runtime_input.input_complete or not runtime_input.input_ready:
        failures.add("USAGE_EVIDENCE_INCOMPLETE")
    if not runtime_input.provider_usage_fresh or not runtime_input.route_usage_fresh:
        failures.add("USAGE_EVIDENCE_STALE")
    if runtime_input.requested_at is None or runtime_input.evidence_expires_at is None:
        failures.add("USAGE_EVIDENCE_INCOMPLETE")
    elif runtime_input.evidence_expires_at <= runtime_input.requested_at:
        failures.add("USAGE_EVIDENCE_EXPIRED")
    if not runtime_input.pricing_revalidated:
        failures.add("PRICING_NOT_REVALIDATED")
    if not runtime_input.reservation_aligned:
        failures.add("RESERVATION_IDENTITY_MISMATCH")

    state = runtime_input.current_budget_alert_state
    daily = state == "DAILY_LIMIT_REACHED"
    monthly = state == "MONTHLY_LIMIT_REACHED"
    hard = state == "HARD_LIMIT_REACHED"
    deepseek_warning = state == "DEEPSEEK_SOFT_THRESHOLD_WARNING"
    anthropic_warning = state == "ANTHROPIC_SOFT_THRESHOLD_WARNING"
    kill_required = monthly or hard or runtime_input.current_kill_switch_state not in ("", "CLEAR")
    manual_recovery_required = kill_required or not runtime_input.manual_recovery_resolved
    if daily:
        failures.add("DAILY_LIMIT_BLOCK_REQUIRED")
    if monthly:
        failures.add("MONTHLY_LIMIT_BLOCK_REQUIRED")
    if hard:
        failures.add("HARD_LIMIT_BLOCK_REQUIRED")
    if kill_required:
        failures.add("KILL_SWITCH_INTENT_REQUIRED")
    if not runtime_input.manual_recovery_resolved:
        failures.add("MANUAL_RECOVERY_REQUIRED")
    if runtime_input.automatic_retry_requested:
        failures.add("AUTOMATIC_RETRY_NOT_AUTHORIZED")
    if runtime_input.budget_changed_after_reservation:
        failures.add("BUDGET_CHANGED_AFTER_RESERVATION")
    if runtime_input.existing_reservation_state != "ACTIVE":
        if runtime_input.existing_reservation_state == "EXPIRED":
            failures.add("RESERVATION_EXPIRED")
        else:
            failures.add("RESERVATION_NOT_ACTIVE")

    provider_allowance = runtime_input.provider_allowance and not (daily or monthly or hard)
    route_allowance = runtime_input.route_allowance and not (daily or monthly or hard)
    escalation_allowance = runtime_input.escalation_allowance
    if deepseek_warning:
        route_allowance = route_allowance and runtime_input.routing_level == "L0"
    if anthropic_warning:
        escalation_allowance = False
        if runtime_input.routing_level in ("L1", "L2"):
            route_allowance = False
            failures.add("SOFT_THRESHOLD_SUPPRESSION_REQUIRED")
    if not provider_allowance or not route_allowance:
        if daily or monthly or hard:
            pass
        elif anthropic_warning:
            pass
        else:
            failures.add("PROVIDER_ROUTE_NOT_ALLOWED")

    pricing_ready = bool(runtime_input.pricing_evidence_id) and runtime_input.pricing_revalidated
    ledger_ready = bool(runtime_input.usage_ledger_evidence_id) and runtime_input.usage_ledger_aligned
    usage_fresh = runtime_input.provider_usage_fresh and runtime_input.route_usage_fresh
    reservation_ready = (
        bool(runtime_input.requested_reservation_id)
        and runtime_input.reservation_aligned
        and runtime_input.existing_reservation_state == "ACTIVE"
    )
    reservation_blockers = {
        "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
        "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "RUNTIME_INPUT_ID_EMPTY", "CORRELATION_ID_EMPTY",
        "BUDGET_POLICY_ID_MISMATCH", "PROVIDER_ID_MISMATCH", "ROUTING_LEVEL_MISMATCH",
        "EXACT_MODEL_ID_MISMATCH", "PROVIDER_USAGE_EVIDENCE_REQUIRED",
        "ROUTE_USAGE_EVIDENCE_REQUIRED", "USAGE_EVIDENCE_STALE", "USAGE_EVIDENCE_EXPIRED",
        "USAGE_EVIDENCE_INCOMPLETE", "PRICING_EVIDENCE_REQUIRED", "PRICING_NOT_REVALIDATED",
        "USAGE_LEDGER_EVIDENCE_REQUIRED", "RESERVATION_IDENTITY_MISMATCH",
        "PROVIDER_ROUTE_NOT_ALLOWED", "SOFT_THRESHOLD_SUPPRESSION_REQUIRED",
        "DAILY_LIMIT_BLOCK_REQUIRED", "MONTHLY_LIMIT_BLOCK_REQUIRED",
        "HARD_LIMIT_BLOCK_REQUIRED", "KILL_SWITCH_INTENT_REQUIRED", "MANUAL_RECOVERY_REQUIRED",
        "AUTOMATIC_RETRY_NOT_AUTHORIZED",
    }
    may_create = not bool(failures.intersection(reservation_blockers))
    reservation_failures = _ordered(failures.intersection(reservation_blockers))
    transmission_blockers = reservation_blockers | {
        "RESERVATION_EVIDENCE_REQUIRED", "RESERVATION_NOT_ACTIVE", "RESERVATION_EXPIRED",
        "BUDGET_CHANGED_AFTER_RESERVATION",
    }
    transmission_failures = _ordered(failures.intersection(transmission_blockers) | {"PROVIDER_TRANSMISSION_NOT_AUTHORIZED"})

    alert_required = daily or monthly or hard or deepseek_warning or anthropic_warning
    alert_reasons = set()
    if alert_required:
        alert_reasons.add("ALERT_INTENT_REQUIRED")
    alert_reasons.update(code for code in failures if code in {
        "DAILY_LIMIT_BLOCK_REQUIRED", "MONTHLY_LIMIT_BLOCK_REQUIRED", "HARD_LIMIT_BLOCK_REQUIRED",
        "SOFT_THRESHOLD_SUPPRESSION_REQUIRED", "KILL_SWITCH_INTENT_REQUIRED",
    })
    classification = state if alert_required else "NORMAL"
    alert = BudgetGuardAlertIntentV1(
        runtime_input.runtime_input_id, policy.policy_id, runtime_input.correlation_id,
        runtime_input.provider_id, runtime_input.routing_level, classification,
        "WARNING" if deepseek_warning or anthropic_warning or daily else "CRITICAL" if monthly or hard else "NONE",
        _ordered(alert_reasons), alert_required, False, False, runtime_input.requested_at,
        bool(runtime_input.runtime_input_id and policy.policy_id and runtime_input.correlation_id and runtime_input.requested_at),
    )
    trigger_evidence = tuple(value for value in (
        runtime_input.provider_usage_snapshot_id, runtime_input.route_usage_snapshot_id,
        runtime_input.usage_ledger_evidence_id, runtime_input.requested_reservation_id,
    ) if value)
    kill = BudgetGuardKillSwitchIntentV1(
        runtime_input.runtime_input_id, policy.policy_id, runtime_input.correlation_id,
        runtime_input.provider_id, state if kill_required else "CLEAR", trigger_evidence,
        kill_required, False, False, kill_required, kill_required, manual_recovery_required, "",
        runtime_input.requested_at,
        bool(runtime_input.runtime_input_id and policy.policy_id and runtime_input.correlation_id and runtime_input.requested_at),
    )
    reservation = BudgetGuardReservationDecisionV1(
        runtime_input.requested_reservation_id, may_create, provider_allowance, route_allowance,
        escalation_allowance, pricing_ready, ledger_ready, usage_fresh, reservation_failures,
        not reservation_failures, False,
    )
    transmission = BudgetGuardTransmissionDecisionV1(
        runtime_input.transmission_attempt_id, False, reservation_ready, pricing_ready, usage_fresh,
        transmission_failures, not transmission_failures, False,
    )
    ordered_failures = _ordered(failures)
    return BudgetGuardRuntimeDecisionV1(
        policy.policy_id, runtime_input.runtime_input_id, runtime_input.correlation_id,
        runtime_input.provider_id, runtime_input.routing_level, runtime_input.exact_provider_model_id,
        reservation, transmission, alert, kill, provider_allowance, route_allowance,
        escalation_allowance, pricing_ready, ledger_ready, reservation_ready, usage_fresh,
        manual_recovery_required, ordered_failures, False, False, False, False, False, False, False,
        not ordered_failures,
    )


def build_budget_guard_runtime_audit_evidence_v1(
    policy: InternalBudgetGuardRuntimePolicyV1,
    runtime_input: BudgetGuardRuntimeInputV1,
    decision: BudgetGuardRuntimeDecisionV1,
) -> BudgetGuardRuntimeAuditEvidenceV1:
    """Build redacted immutable evidence from already supplied metadata only."""
    aligned = (
        decision.policy_id == policy.policy_id
        and decision.runtime_input_id == runtime_input.runtime_input_id
        and decision.correlation_id == runtime_input.correlation_id
        and decision.provider_id == runtime_input.provider_id
        and decision.routing_level == runtime_input.routing_level
        and decision.exact_provider_model_id == runtime_input.exact_provider_model_id
    )
    return BudgetGuardRuntimeAuditEvidenceV1(
        policy.policy_id, runtime_input.runtime_input_id, runtime_input.correlation_id,
        runtime_input.provider_id, runtime_input.routing_level, runtime_input.exact_provider_model_id,
        runtime_input.provider_usage_snapshot_id, runtime_input.route_usage_snapshot_id,
        runtime_input.pricing_evidence_id, runtime_input.usage_ledger_evidence_id,
        runtime_input.requested_reservation_id, runtime_input.transmission_attempt_id,
        decision.reservation_decision, decision.transmission_decision, decision.alert_intent,
        decision.kill_switch_intent, decision.provider_allowance, decision.route_allowance,
        decision.escalation_allowance, decision.manual_recovery_required, decision.failure_codes,
        False, False, False, False, False, False, False,
        aligned and not any((
            decision.runtime_activation_authorized, decision.alert_publication_authorized,
            decision.kill_switch_activation_authorized, decision.credential_loading_authorized,
            decision.network_authorized, decision.provider_transmission_authorized,
            decision.publication_authorized,
        )),
    )
