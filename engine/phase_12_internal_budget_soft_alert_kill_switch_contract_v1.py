"""Pure, metadata-only internal budget alert and kill-switch evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


_DEEPSEEK = (Decimal("0.50"), Decimal("12.00"), Decimal("15.00"))
_ANTHROPIC = (Decimal("0.85"), Decimal("20.00"), Decimal("25.00"))
_ROUTES = {
    "L0": ("DEEPSEEK", "deepseek-v4-pro", Decimal("0.02"), Decimal("0.40"), Decimal("12.00"), 1, 3),
    "L1": ("ANTHROPIC", "claude-sonnet-5", Decimal("0.12"), Decimal("0.50"), Decimal("15.00"), 1, 2),
    "L2": ("ANTHROPIC", "claude-opus-4-8", Decimal("0.20"), Decimal("0.20"), Decimal("6.00"), 1, 1),
}
_FAILURE_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "CURRENCY_EMPTY", "PROVIDER_NOT_ALLOWED",
    "ROUTING_LEVEL_NOT_ALLOWED", "PROVIDER_USAGE_SNAPSHOT_MISSING",
    "PROVIDER_USAGE_SNAPSHOT_ID_EMPTY", "ROUTE_USAGE_SNAPSHOT_MISSING",
    "ROUTE_USAGE_SNAPSHOT_ID_EMPTY", "PROVIDER_ID_MISMATCH", "ROUTING_LEVEL_MISMATCH",
    "EXACT_MODEL_ID_MISMATCH", "CURRENCY_MISMATCH", "LOCKED_LIMIT_MISMATCH",
    "NATIVE_SOFT_ALERT_EXCEPTION_NOT_PRESERVED", "PROVIDER_HARD_CAP_NOT_ENABLED",
    "USAGE_LEDGER_EVIDENCE_REQUIRED", "RESERVATION_EVIDENCE_REQUIRED",
    "PRICING_EVIDENCE_REQUIRED", "PRICING_NOT_REVALIDATED", "USAGE_VALUE_INVALID",
    "USAGE_INCOMPLETE", "USAGE_FROM_FUTURE", "USAGE_STALE", "USAGE_EXPIRED",
    "SOFT_THRESHOLD_DEGRADATION_REQUIRED", "OPTIONAL_WORK_SUPPRESSION_REQUIRED",
    "OPTIONAL_ESCALATION_SUPPRESSION_REQUIRED", "DAILY_LIMIT_BLOCK_REQUIRED",
    "MONTHLY_LIMIT_BLOCK_REQUIRED", "HARD_LIMIT_KILL_SWITCH_REQUIRED",
    "NEW_RESERVATION_BLOCK_REQUIRED", "AUTOMATIC_RETRY_NOT_AUTHORIZED",
    "MANUAL_RECOVERY_REQUIRED", "RECOVERY_APPROVAL_REQUIRED",
    "ALERT_PUBLICATION_NOT_AUTHORIZED", "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED",
    "RUNTIME_CONFIGURATION_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_BILLING_DATA_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


@dataclass(frozen=True, slots=True)
class InternalBudgetAlertPolicyV1:
    policy_id: str = ""
    policy_version: str = ""
    deployment_environment: str = ""
    currency: str = ""
    allowed_provider_ids: tuple[str, ...] = ()
    allowed_routing_levels: tuple[str, ...] = ()
    require_internal_soft_alert: bool = False
    require_provider_hard_cap: bool = False
    require_daily_provider_cap: bool = False
    require_monthly_provider_cap: bool = False
    require_route_limits: bool = False
    require_usage_ledger: bool = False
    require_reservation_before_call: bool = False
    require_pricing_revalidation: bool = False
    require_operator_alert: bool = False
    require_soft_threshold_degradation: bool = False
    require_optional_escalation_suppression: bool = False
    require_hard_threshold_kill_switch: bool = False
    require_zero_automatic_retry: bool = False
    require_fail_closed_unknown_usage: bool = False
    require_fail_closed_stale_usage: bool = False
    require_manual_recovery: bool = False
    require_recovery_approval: bool = False
    require_evidence_freshness: bool = False
    maximum_usage_age_seconds: int | None = None
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    runtime_configuration_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class ProviderBudgetUsageSnapshotV1:
    provider_usage_snapshot_id: str = ""
    policy_id: str = ""
    provider_id: str = ""
    currency: str = ""
    daily_usage: Decimal | None = None
    monthly_usage: Decimal | None = None
    internal_daily_limit: Decimal | None = None
    internal_soft_alert_threshold: Decimal | None = None
    internal_monthly_limit: Decimal | None = None
    provider_hard_limit: Decimal | None = None
    native_soft_alert_available: bool = False
    provider_hard_cap_enabled: bool = False
    usage_ledger_evidence_id: str = ""
    pricing_evidence_id: str = ""
    pricing_revalidated: bool = False
    measured_at: datetime | None = None
    evidence_expires_at: datetime | None = None
    usage_complete: bool = False
    usage_ready: bool = False


@dataclass(frozen=True, slots=True)
class RouteBudgetUsageSnapshotV1:
    route_usage_snapshot_id: str = ""
    policy_id: str = ""
    provider_usage_snapshot_id: str = ""
    provider_id: str = ""
    routing_level: str = ""
    exact_provider_model_id: str = ""
    current_request_estimated_cost: Decimal | None = None
    daily_route_usage: Decimal | None = None
    monthly_route_usage: Decimal | None = None
    per_request_cost_limit: Decimal | None = None
    daily_route_cost_limit: Decimal | None = None
    monthly_route_cost_limit: Decimal | None = None
    calls_for_current_signal: int | None = None
    calls_today: int | None = None
    maximum_calls_per_signal: int | None = None
    maximum_calls_per_day: int | None = None
    reservation_evidence_id: str = ""
    usage_ledger_evidence_id: str = ""
    pricing_evidence_id: str = ""
    pricing_revalidated: bool = False
    measured_at: datetime | None = None
    evidence_expires_at: datetime | None = None
    usage_complete: bool = False
    usage_ready: bool = False


@dataclass(frozen=True, slots=True)
class InternalBudgetAlertStateV1:
    alert_state_id: str = ""
    policy_id: str = ""
    provider_id: str = ""
    current_state: str = "USAGE_UNKNOWN_BLOCKED"
    soft_threshold_reached: bool = False
    daily_limit_reached: bool = False
    monthly_limit_reached: bool = False
    hard_limit_reached: bool = False
    operator_alert_required: bool = True
    optional_work_suppressed: bool = True
    optional_escalation_suppressed: bool = True
    required_L0_review_allowed: bool = False
    L1_allowed: bool = False
    L2_allowed: bool = False
    new_reservations_allowed: bool = False
    automatic_retry_allowed: bool = False
    fail_closed: bool = True
    evaluated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProviderKillSwitchStateV1:
    kill_switch_state_id: str = ""
    policy_id: str = ""
    provider_id: str = ""
    trigger_classification: str = ""
    trigger_evidence_ids: tuple[str, ...] = ()
    required: bool = False
    activated: bool = False
    activation_authorized: bool = False
    provider_calls_blocked: bool = False
    new_reservations_blocked: bool = False
    automatic_retry_allowed: bool = False
    manual_recovery_required: bool = False
    recovery_approval_id: str = ""
    activated_at: datetime | None = None
    evaluated_at: datetime | None = None
    state_ready: bool = False


@dataclass(frozen=True, slots=True)
class InternalBudgetAlertFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class InternalBudgetAlertDecisionV1:
    policy_id: str = ""
    deployment_environment: str = ""
    ready: bool = False
    failure_codes: tuple[str, ...] = ()
    DeepSeek_alert_state: str = "USAGE_UNKNOWN_BLOCKED"
    Anthropic_alert_state: str = "USAGE_UNKNOWN_BLOCKED"
    L0_allowed: bool = False
    L1_allowed: bool = False
    L2_allowed: bool = False
    soft_alerts_ready: bool = False
    daily_caps_ready: bool = False
    monthly_caps_ready: bool = False
    provider_hard_caps_ready: bool = False
    usage_ledger_ready: bool = False
    reservations_ready: bool = False
    pricing_revalidated: bool = False
    operator_alert_required: bool = True
    kill_switch_required: bool = False
    manual_recovery_required: bool = False
    evidence_fresh: bool = False
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    runtime_configuration_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False


@dataclass(frozen=True, slots=True)
class InternalBudgetAlertAuditEvidenceV1:
    policy_id: str = ""
    provider_usage_snapshot_ids: tuple[str, ...] = ()
    route_usage_snapshot_ids: tuple[str, ...] = ()
    provider_ids: tuple[str, ...] = ()
    exact_provider_model_ids: tuple[str, ...] = ()
    alert_states: tuple[str, ...] = ()
    failure_codes: tuple[str, ...] = ()
    alert_publication_authorized: bool = False
    kill_switch_activation_authorized: bool = False
    runtime_configuration_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False


def _decimal(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value >= Decimal("0")


def _integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _fresh(measured_at: datetime | None, expires_at: datetime | None, evaluated_at: datetime, maximum_age: object) -> tuple[bool, str | None]:
    if not isinstance(measured_at, datetime) or not isinstance(expires_at, datetime):
        return False, "USAGE_INCOMPLETE"
    if isinstance(maximum_age, bool) or not isinstance(maximum_age, int) or maximum_age < 0:
        return False, "USAGE_STALE"
    try:
        if measured_at > evaluated_at:
            return False, "USAGE_FROM_FUTURE"
        if expires_at < evaluated_at:
            return False, "USAGE_EXPIRED"
        # The profile is permitted to be stricter than its caller-supplied
        # ceiling: usage older than one minute is never current enough for a
        # fail-closed reservation decision.
        if (evaluated_at - measured_at).total_seconds() > min(maximum_age, 60):
            return False, "USAGE_STALE"
    except TypeError:
        return False, "USAGE_STALE"
    return True, None


def _ordered(codes: set[str]) -> tuple[str, ...]:
    return tuple(code for code in _FAILURE_ORDER if code in codes)


def _provider_validation(policy: InternalBudgetAlertPolicyV1, snapshot: ProviderBudgetUsageSnapshotV1 | None, expected: tuple[Decimal, Decimal, Decimal], evaluated_at: datetime) -> tuple[set[str], bool]:
    failures: set[str] = set()
    if snapshot is None:
        return {"PROVIDER_USAGE_SNAPSHOT_MISSING"}, False
    if not snapshot.provider_usage_snapshot_id:
        failures.add("PROVIDER_USAGE_SNAPSHOT_ID_EMPTY")
    if snapshot.policy_id != policy.policy_id:
        failures.add("PROVIDER_ID_MISMATCH")
    if snapshot.provider_id not in ("DEEPSEEK", "ANTHROPIC"):
        failures.add("PROVIDER_ID_MISMATCH")
    if snapshot.provider_id not in policy.allowed_provider_ids:
        failures.add("PROVIDER_NOT_ALLOWED")
    if snapshot.currency != policy.currency:
        failures.add("CURRENCY_MISMATCH")
    if (snapshot.internal_daily_limit, snapshot.internal_soft_alert_threshold, snapshot.internal_monthly_limit, snapshot.provider_hard_limit) != (*expected, expected[2]):
        failures.add("LOCKED_LIMIT_MISMATCH")
    if snapshot.native_soft_alert_available is not False:
        failures.add("NATIVE_SOFT_ALERT_EXCEPTION_NOT_PRESERVED")
    if snapshot.provider_hard_cap_enabled is not True:
        failures.add("PROVIDER_HARD_CAP_NOT_ENABLED")
    if not snapshot.usage_ledger_evidence_id:
        failures.add("USAGE_LEDGER_EVIDENCE_REQUIRED")
    if not snapshot.pricing_evidence_id:
        failures.add("PRICING_EVIDENCE_REQUIRED")
    if not snapshot.pricing_revalidated:
        failures.add("PRICING_NOT_REVALIDATED")
    if not snapshot.usage_complete or not snapshot.usage_ready:
        failures.add("USAGE_INCOMPLETE")
    if not all(_decimal(value) for value in (snapshot.daily_usage, snapshot.monthly_usage, snapshot.internal_daily_limit, snapshot.internal_soft_alert_threshold, snapshot.internal_monthly_limit, snapshot.provider_hard_limit)):
        failures.add("USAGE_VALUE_INVALID")
    fresh, fresh_failure = _fresh(snapshot.measured_at, snapshot.evidence_expires_at, evaluated_at, policy.maximum_usage_age_seconds)
    if fresh_failure:
        failures.add(fresh_failure)
    return failures, not failures and fresh


def _route_validation(policy: InternalBudgetAlertPolicyV1, route: RouteBudgetUsageSnapshotV1 | None, provider: ProviderBudgetUsageSnapshotV1 | None, expected: tuple[str, str, Decimal, Decimal, Decimal, int, int], evaluated_at: datetime) -> tuple[set[str], bool]:
    failures: set[str] = set()
    if route is None:
        return {"ROUTE_USAGE_SNAPSHOT_MISSING"}, False
    provider_id, model_id, request_limit, daily_limit, monthly_limit, calls_signal, calls_day = expected
    if not route.route_usage_snapshot_id:
        failures.add("ROUTE_USAGE_SNAPSHOT_ID_EMPTY")
    if route.policy_id != policy.policy_id or route.provider_id != provider_id or route.provider_usage_snapshot_id != (provider.provider_usage_snapshot_id if provider else ""):
        failures.add("PROVIDER_ID_MISMATCH")
    if route.routing_level not in policy.allowed_routing_levels:
        failures.add("ROUTING_LEVEL_NOT_ALLOWED")
    if route.exact_provider_model_id != model_id:
        failures.add("EXACT_MODEL_ID_MISMATCH")
    if (route.per_request_cost_limit, route.daily_route_cost_limit, route.monthly_route_cost_limit, route.maximum_calls_per_signal, route.maximum_calls_per_day) != (request_limit, daily_limit, monthly_limit, calls_signal, calls_day):
        failures.add("LOCKED_LIMIT_MISMATCH")
    if not route.reservation_evidence_id:
        failures.add("RESERVATION_EVIDENCE_REQUIRED")
    if not route.usage_ledger_evidence_id:
        failures.add("USAGE_LEDGER_EVIDENCE_REQUIRED")
    if not route.pricing_evidence_id:
        failures.add("PRICING_EVIDENCE_REQUIRED")
    if not route.pricing_revalidated:
        failures.add("PRICING_NOT_REVALIDATED")
    if not route.usage_complete or not route.usage_ready:
        failures.add("USAGE_INCOMPLETE")
    if not all(_decimal(value) for value in (route.current_request_estimated_cost, route.daily_route_usage, route.monthly_route_usage, route.per_request_cost_limit, route.daily_route_cost_limit, route.monthly_route_cost_limit)) or not all(_integer(value) for value in (route.calls_for_current_signal, route.calls_today, route.maximum_calls_per_signal, route.maximum_calls_per_day)):
        failures.add("USAGE_VALUE_INVALID")
    fresh, fresh_failure = _fresh(route.measured_at, route.evidence_expires_at, evaluated_at, policy.maximum_usage_age_seconds)
    if fresh_failure:
        failures.add(fresh_failure)
    return failures, not failures and fresh


def _route_allowed(route: RouteBudgetUsageSnapshotV1 | None) -> bool:
    if route is None:
        return False
    return (
        route.current_request_estimated_cost < route.per_request_cost_limit
        and route.daily_route_usage < route.daily_route_cost_limit
        and route.monthly_route_usage < route.monthly_route_cost_limit
        and route.calls_for_current_signal < route.maximum_calls_per_signal
        and route.calls_today < route.maximum_calls_per_day
    )


def _state(snapshot: ProviderBudgetUsageSnapshotV1 | None, valid: bool) -> str:
    if snapshot is None or not valid:
        return "USAGE_UNKNOWN_BLOCKED"
    if snapshot.monthly_usage >= snapshot.provider_hard_limit:
        return "HARD_LIMIT_KILL_SWITCH_REQUIRED"
    if snapshot.monthly_usage >= snapshot.internal_monthly_limit:
        return "MONTHLY_LIMIT_BLOCKED"
    if snapshot.daily_usage >= snapshot.internal_daily_limit:
        return "DAILY_LIMIT_BLOCKED"
    if snapshot.monthly_usage >= snapshot.internal_soft_alert_threshold:
        return "SOFT_THRESHOLD_WARNING"
    return "NORMAL"


def evaluate_internal_budget_alert_v1(
    policy: InternalBudgetAlertPolicyV1,
    provider_usage_snapshots: tuple[ProviderBudgetUsageSnapshotV1, ...],
    route_usage_snapshots: tuple[RouteBudgetUsageSnapshotV1, ...],
    kill_switch_states: tuple[ProviderKillSwitchStateV1, ...],
    evaluated_at: datetime,
) -> InternalBudgetAlertDecisionV1:
    del kill_switch_states
    failures: set[str] = set()
    if not policy.policy_id:
        failures.add("POLICY_ID_EMPTY")
    if not policy.policy_version:
        failures.add("POLICY_VERSION_EMPTY")
    if not policy.deployment_environment:
        failures.add("DEPLOYMENT_ENVIRONMENT_EMPTY")
    if not policy.currency:
        failures.add("CURRENCY_EMPTY")
    if any((policy.alert_publication_authorized, policy.kill_switch_activation_authorized, policy.runtime_configuration_authorized, policy.credential_loading_authorized, policy.network_authorized, policy.provider_transmission_authorized)):
        failures.update(("ALERT_PUBLICATION_NOT_AUTHORIZED", "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED", "RUNTIME_CONFIGURATION_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"))
    providers = {item.provider_id: item for item in provider_usage_snapshots}
    deepseek, anthropic = providers.get("DEEPSEEK"), providers.get("ANTHROPIC")
    deepseek_failures, deepseek_valid = _provider_validation(policy, deepseek, _DEEPSEEK, evaluated_at)
    anthropic_failures, anthropic_valid = _provider_validation(policy, anthropic, _ANTHROPIC, evaluated_at)
    failures.update(deepseek_failures | anthropic_failures)
    routes = {item.routing_level: item for item in route_usage_snapshots}
    route_results: dict[str, bool] = {}
    for level, expected in _ROUTES.items():
        provider = deepseek if expected[0] == "DEEPSEEK" else anthropic
        route_failures, route_valid = _route_validation(policy, routes.get(level), provider, expected, evaluated_at)
        failures.update(route_failures)
        route_results[level] = route_valid and _route_allowed(routes.get(level))
    deepseek_state = _state(deepseek, deepseek_valid)
    anthropic_state = _state(anthropic, anthropic_valid)
    deepseek_blocked = deepseek_state in ("USAGE_UNKNOWN_BLOCKED", "DAILY_LIMIT_BLOCKED", "MONTHLY_LIMIT_BLOCKED", "HARD_LIMIT_KILL_SWITCH_REQUIRED")
    anthropic_blocked = anthropic_state in ("USAGE_UNKNOWN_BLOCKED", "DAILY_LIMIT_BLOCKED", "MONTHLY_LIMIT_BLOCKED", "HARD_LIMIT_KILL_SWITCH_REQUIRED", "SOFT_THRESHOLD_WARNING")
    l0_allowed = route_results["L0"] and not deepseek_blocked
    l1_allowed = route_results["L1"] and not anthropic_blocked
    l2_allowed = route_results["L2"] and not anthropic_blocked
    states = (deepseek_state, anthropic_state)
    hard_stop = any(state in ("MONTHLY_LIMIT_BLOCKED", "HARD_LIMIT_KILL_SWITCH_REQUIRED") for state in states)
    operator_alert = any(state != "NORMAL" for state in states)
    evidence_fresh = deepseek_valid and anthropic_valid and all(route_results.values())
    return InternalBudgetAlertDecisionV1(
        policy_id=policy.policy_id,
        deployment_environment=policy.deployment_environment,
        ready=not failures,
        failure_codes=_ordered(failures),
        DeepSeek_alert_state=deepseek_state,
        Anthropic_alert_state=anthropic_state,
        L0_allowed=l0_allowed,
        L1_allowed=l1_allowed,
        L2_allowed=l2_allowed,
        soft_alerts_ready=policy.require_internal_soft_alert and deepseek_valid and anthropic_valid,
        daily_caps_ready=deepseek_valid and anthropic_valid,
        monthly_caps_ready=deepseek_valid and anthropic_valid,
        provider_hard_caps_ready=deepseek_valid and anthropic_valid,
        usage_ledger_ready=deepseek_valid and anthropic_valid and all(route_results.values()),
        reservations_ready=all(route_results.values()),
        pricing_revalidated=deepseek_valid and anthropic_valid and all(route_results.values()),
        operator_alert_required=operator_alert,
        kill_switch_required=hard_stop,
        manual_recovery_required=hard_stop,
        evidence_fresh=evidence_fresh,
        alert_publication_authorized=False,
        kill_switch_activation_authorized=False,
        runtime_configuration_authorized=False,
        credential_loading_authorized=False,
        network_authorized=False,
        provider_transmission_authorized=False,
    )


def build_internal_budget_alert_audit_evidence_v1(
    policy: InternalBudgetAlertPolicyV1,
    provider_usage_snapshots: tuple[ProviderBudgetUsageSnapshotV1, ...],
    route_usage_snapshots: tuple[RouteBudgetUsageSnapshotV1, ...],
    kill_switch_states: tuple[ProviderKillSwitchStateV1, ...],
    decision: InternalBudgetAlertDecisionV1,
) -> InternalBudgetAlertAuditEvidenceV1:
    del kill_switch_states
    if decision.policy_id != policy.policy_id or len(provider_usage_snapshots) != 2 or len(route_usage_snapshots) != 3:
        raise ValueError
    provider_ids = tuple(item.provider_id for item in provider_usage_snapshots)
    if provider_ids != ("DEEPSEEK", "ANTHROPIC") or any(item.policy_id != policy.policy_id for item in provider_usage_snapshots) or any(item.policy_id != policy.policy_id for item in route_usage_snapshots):
        raise ValueError
    return InternalBudgetAlertAuditEvidenceV1(
        policy_id=policy.policy_id,
        provider_usage_snapshot_ids=tuple(item.provider_usage_snapshot_id for item in provider_usage_snapshots),
        route_usage_snapshot_ids=tuple(item.route_usage_snapshot_id for item in route_usage_snapshots),
        provider_ids=provider_ids,
        exact_provider_model_ids=tuple(item.exact_provider_model_id for item in route_usage_snapshots),
        alert_states=(decision.DeepSeek_alert_state, decision.Anthropic_alert_state),
        failure_codes=decision.failure_codes,
        alert_publication_authorized=False,
        kill_switch_activation_authorized=False,
        runtime_configuration_authorized=False,
        credential_loading_authorized=False,
        network_authorized=False,
        provider_transmission_authorized=False,
    )
