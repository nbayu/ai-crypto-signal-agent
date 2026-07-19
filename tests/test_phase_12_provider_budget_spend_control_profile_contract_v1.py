"""RED contract for immutable redacted provider budget controls."""

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from engine.phase_12_provider_budget_spend_control_profile_contract_v1 import (
    ProviderBudgetAuditEvidenceV1,
    ProviderBudgetFailureV1,
    ProviderBudgetPolicyV1,
    ProviderBudgetReadinessDecisionV1,
    ProviderEscalationBudgetProfileV1,
    ProviderRouteBudgetProfileV1,
    ProviderSpendControlProfileV1,
    build_provider_budget_audit_evidence_v1,
    evaluate_provider_budget_readiness_v1,
)


_AT = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
_LIMIT = Decimal("10.00")
_CODES = {
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "CURRENCY_EMPTY", "PROVIDER_NOT_ALLOWED", "ROUTING_LEVEL_NOT_ALLOWED", "PROVIDER_BUDGET_PROFILE_MISSING", "PROVIDER_BUDGET_PROFILE_ID_EMPTY", "HARD_SPEND_CONTROL_NOT_AVAILABLE", "HARD_SPEND_CONTROL_NOT_ENABLED", "HARD_SPEND_LIMIT_REQUIRED", "SOFT_ALERT_NOT_AVAILABLE", "SOFT_ALERT_NOT_ENABLED", "SOFT_ALERT_THRESHOLD_REQUIRED", "SOFT_ALERT_THRESHOLD_INVALID", "DAILY_SPEND_LIMIT_REQUIRED", "MONTHLY_SPEND_LIMIT_REQUIRED", "SPEND_LIMIT_ORDER_INVALID", "ROUTE_BUDGET_PROFILE_MISSING", "ROUTE_BUDGET_PROFILE_ID_EMPTY", "PROVIDER_ID_MISMATCH", "ROUTING_LEVEL_MISMATCH", "EXACT_MODEL_ID_MISMATCH", "PER_REQUEST_LIMIT_REQUIRED", "ROUTE_DAILY_LIMIT_REQUIRED", "ROUTE_MONTHLY_LIMIT_REQUIRED", "ROUTE_LIMIT_EXCEEDS_PROVIDER_LIMIT", "TOKEN_LIMIT_INVALID", "CALL_LIMIT_INVALID", "PRICING_EVIDENCE_REQUIRED", "PRICING_NOT_REVALIDATED", "RESERVATION_POLICY_REQUIRED", "USAGE_LEDGER_POLICY_REQUIRED", "UNKNOWN_COST_MUST_FAIL_CLOSED", "BUDGET_EXHAUSTION_MUST_FAIL_CLOSED", "AUTOMATIC_RETRY_NOT_AUTHORIZED", "ESCALATION_BUDGET_PROFILE_REQUIRED", "ESCALATION_REVALIDATION_REQUIRED", "DIRECT_L0_TO_L2_NOT_AUTHORIZED", "SEPARATE_PROVIDER_RESERVATION_REQUIRED", "SEPARATE_ROUTE_RESERVATION_REQUIRED", "HARD_THRESHOLD_STOP_REQUIRED", "OPERATOR_OVERRIDE_NOT_AUTHORIZED", "ALERTING_POLICY_REQUIRED", "KILL_SWITCH_POLICY_REQUIRED", "BUDGET_CHANGE_APPROVAL_REQUIRED", "MONETARY_VALUE_INVALID", "CURRENCY_MISMATCH", "VERIFICATION_TIMESTAMP_REQUIRED", "EVIDENCE_FROM_FUTURE", "EVIDENCE_EXPIRED", "BUDGET_CONFIGURATION_NOT_AUTHORIZED", "SPEND_CONTROL_ACTIVATION_NOT_AUTHORIZED", "CREDENTIAL_ONBOARDING_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "RAW_BILLING_DATA_EXPOSURE_DETECTED", "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


def _names(record: type) -> tuple[str, ...]:
    return tuple(item.name for item in fields(record))


def _policy() -> ProviderBudgetPolicyV1:
    return ProviderBudgetPolicyV1(
        policy_id="budget-policy-v1", policy_version="v1", deployment_environment="CONTROLLED_PRODUCTION", currency="USD",
        allowed_provider_ids=("DEEPSEEK", "ANTHROPIC"), allowed_routing_levels=("L0", "L1", "L2"), maximum_evidence_age_days=7,
    )


def _spend(provider: str, **changes: object) -> ProviderSpendControlProfileV1:
    values = dict(
        provider_budget_profile_id=f"provider-budget-{provider.lower()}", policy_id="budget-policy-v1", provider_id=provider,
        billing_currency="USD", hard_spend_control_available=True, hard_spend_control_enabled=False, hard_spend_limit=_LIMIT,
        soft_alert_available=True, soft_alert_enabled=False, soft_alert_threshold=Decimal("8.00"), daily_spend_limit=_LIMIT,
        monthly_spend_limit=Decimal("100.00"), provider_budget_reference_id=f"budget-ref-{provider.lower()}",
        alerting_policy_id="alert-policy", kill_switch_policy_id="kill-policy", budget_change_approval_id="approval-policy",
        pricing_evidence_id=f"pricing-{provider.lower()}", pricing_revalidated=False, verified_at=_AT,
        evidence_expires_at=_UNTIL, profile_ready=False,
    )
    values.update(changes)
    return ProviderSpendControlProfileV1(**values)


def _route(level: str, provider: str, model: str, **changes: object) -> ProviderRouteBudgetProfileV1:
    values = dict(
        route_budget_profile_id=f"route-budget-{level.lower()}", policy_id="budget-policy-v1",
        provider_budget_profile_id=f"provider-budget-{provider.lower()}", provider_id=provider, routing_level=level,
        exact_provider_model_id=model, per_request_cost_limit=Decimal("1.00"), daily_route_cost_limit=Decimal("5.00"),
        monthly_route_cost_limit=Decimal("50.00"), maximum_input_tokens_per_request=1000,
        maximum_output_tokens_per_request=1000, maximum_calls_per_signal=1, maximum_calls_per_day=1,
        pricing_evidence_id=f"pricing-{provider.lower()}", pricing_revalidated=False,
        reservation_policy_id="reservation-policy", usage_ledger_policy_id="usage-ledger-policy",
        fail_closed_on_unknown_cost=True, fail_closed_on_budget_exhaustion=True,
        automatic_retry_allowed=False, route_budget_ready=False,
    )
    values.update(changes)
    return ProviderRouteBudgetProfileV1(**values)


def _escalation(**changes: object) -> ProviderEscalationBudgetProfileV1:
    values = dict(
        escalation_budget_profile_id="escalation-budget", policy_id="budget-policy-v1",
        L0_route_budget_profile_id="route-budget-l0", L1_route_budget_profile_id="route-budget-l1", L2_route_budget_profile_id="route-budget-l2",
        L0_to_L1_budget_revalidation_required=True, L1_to_L2_budget_revalidation_required=True,
        L0_to_L2_direct_budget_allowed=False, cumulative_signal_budget_limit=Decimal("3.00"), maximum_escalation_cost=Decimal("2.00"),
        separate_provider_reservation_required=True, separate_route_reservation_required=True,
        stop_on_soft_threshold=True, stop_on_hard_threshold=True, operator_override_allowed=False, escalation_budget_ready=False,
    )
    values.update(changes)
    return ProviderEscalationBudgetProfileV1(**values)


def _evaluate(**changes: object) -> tuple[object, ...]:
    spend = (_spend("DEEPSEEK"), _spend("ANTHROPIC"))
    routes = (_route("L0", "DEEPSEEK", "deepseek-v4-pro"), _route("L1", "ANTHROPIC", "claude-sonnet-5"), _route("L2", "ANTHROPIC", "claude-opus-4-8"))
    values = dict(policy=_policy(), spend_profiles=spend, route_profiles=routes, escalation_profile=_escalation(), evaluated_at=_AT)
    values.update(changes)
    decision = evaluate_provider_budget_readiness_v1(**values)
    return values["policy"], spend, routes, values["escalation_profile"], decision


def test_public_records_are_immutable_and_fail_closed_by_default() -> None:
    expected = {
        ProviderBudgetPolicyV1: ("policy_id", "policy_version", "deployment_environment", "currency", "allowed_provider_ids", "allowed_routing_levels", "require_hard_provider_limit", "require_soft_provider_alert", "require_daily_provider_limit", "require_monthly_provider_limit", "require_per_request_route_limit", "require_daily_route_limit", "require_monthly_route_limit", "require_separate_provider_budgets", "require_separate_route_budgets", "require_escalation_budget", "require_pricing_revalidation", "require_reservation_before_call", "require_usage_ledger", "require_zero_automatic_retry", "require_fail_closed_budget_exhaustion", "require_operator_alert_on_soft_threshold", "require_kill_switch_on_hard_threshold", "require_budget_change_approval", "require_evidence_freshness", "maximum_evidence_age_days", "budget_configuration_authorized", "spend_control_activation_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized", "fail_closed"),
        ProviderSpendControlProfileV1: ("provider_budget_profile_id", "policy_id", "provider_id", "billing_currency", "hard_spend_control_available", "hard_spend_control_enabled", "hard_spend_limit", "soft_alert_available", "soft_alert_enabled", "soft_alert_threshold", "daily_spend_limit", "monthly_spend_limit", "provider_budget_reference_id", "alerting_policy_id", "kill_switch_policy_id", "budget_change_approval_id", "pricing_evidence_id", "pricing_revalidated", "verified_at", "evidence_expires_at", "profile_ready"),
        ProviderRouteBudgetProfileV1: ("route_budget_profile_id", "policy_id", "provider_budget_profile_id", "provider_id", "routing_level", "exact_provider_model_id", "per_request_cost_limit", "daily_route_cost_limit", "monthly_route_cost_limit", "maximum_input_tokens_per_request", "maximum_output_tokens_per_request", "maximum_calls_per_signal", "maximum_calls_per_day", "pricing_evidence_id", "pricing_revalidated", "reservation_policy_id", "usage_ledger_policy_id", "fail_closed_on_unknown_cost", "fail_closed_on_budget_exhaustion", "automatic_retry_allowed", "route_budget_ready"),
        ProviderEscalationBudgetProfileV1: ("escalation_budget_profile_id", "policy_id", "L0_route_budget_profile_id", "L1_route_budget_profile_id", "L2_route_budget_profile_id", "L0_to_L1_budget_revalidation_required", "L1_to_L2_budget_revalidation_required", "L0_to_L2_direct_budget_allowed", "cumulative_signal_budget_limit", "maximum_escalation_cost", "separate_provider_reservation_required", "separate_route_reservation_required", "stop_on_soft_threshold", "stop_on_hard_threshold", "operator_override_allowed", "escalation_budget_ready"),
        ProviderBudgetReadinessDecisionV1: ("policy_id", "deployment_environment", "ready", "failure_codes", "DeepSeek_spend_control_ready", "Anthropic_spend_control_ready", "L0_budget_ready", "L1_budget_ready", "L2_budget_ready", "escalation_budget_ready", "hard_limits_enabled", "soft_alerts_enabled", "daily_limits_ready", "monthly_limits_ready", "per_request_limits_ready", "pricing_revalidated", "reservations_ready", "usage_ledger_ready", "alerting_ready", "kill_switch_ready", "evidence_fresh", "budget_configuration_authorized", "spend_control_activation_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized"),
        ProviderBudgetAuditEvidenceV1: ("policy_id", "deployment_environment", "provider_budget_profile_ids", "route_budget_profile_ids", "exact_model_ids", "hard_limits_enabled", "soft_alerts_enabled", "daily_limits_ready", "monthly_limits_ready", "per_request_limits_ready", "escalation_budget_ready", "pricing_revalidated", "reservations_ready", "usage_ledger_ready", "alerting_ready", "kill_switch_ready", "evidence_fresh", "failure_codes", "budget_configuration_authorized", "spend_control_activation_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized"),
    }
    for record, names in expected.items():
        assert is_dataclass(record) and _names(record) == names
        assert getattr(record, "__dataclass_params__").frozen is True and hasattr(record, "__slots__")
    assert _names(ProviderBudgetFailureV1) == ("failure_code", "safe_message", "retryable")
    defaults = ProviderBudgetPolicyV1()
    assert defaults.allowed_provider_ids == defaults.allowed_routing_levels == () and defaults.fail_closed is True
    assert not any((defaults.budget_configuration_authorized, defaults.spend_control_activation_authorized, defaults.credential_onboarding_authorized, defaults.credential_loading_authorized, defaults.network_authorized, defaults.provider_transmission_authorized))


def test_available_but_disabled_controls_are_not_ready_and_locked_routes_remain_exact() -> None:
    _policy_value, spend, routes, _escalation_value, decision = _evaluate()
    assert tuple((item.provider_id, item.hard_spend_control_available, item.hard_spend_control_enabled, item.soft_alert_available, item.soft_alert_enabled) for item in spend) == (("DEEPSEEK", True, False, True, False), ("ANTHROPIC", True, False, True, False))
    assert tuple((item.routing_level, item.provider_id, item.exact_provider_model_id) for item in routes) == (("L0", "DEEPSEEK", "deepseek-v4-pro"), ("L1", "ANTHROPIC", "claude-sonnet-5"), ("L2", "ANTHROPIC", "claude-opus-4-8"))
    assert decision.ready is False
    assert {"HARD_SPEND_CONTROL_NOT_ENABLED", "SOFT_ALERT_NOT_ENABLED", "PRICING_NOT_REVALIDATED"} <= set(decision.failure_codes)
    assert tuple(sorted(decision.failure_codes)) == decision.failure_codes and set(decision.failure_codes) <= _CODES


def test_invalid_money_retry_and_direct_escalation_fail_closed() -> None:
    policy, spend, routes, escalation, _decision = _evaluate()
    invalid_route = _route("L0", "DEEPSEEK", "deepseek-v4-pro", per_request_cost_limit=1.0, automatic_retry_allowed=True)
    invalid_escalation = _escalation(L0_to_L2_direct_budget_allowed=True, operator_override_allowed=True)
    decision = evaluate_provider_budget_readiness_v1(policy, spend, (invalid_route, routes[1], routes[2]), invalid_escalation, _AT)
    assert {"MONETARY_VALUE_INVALID", "AUTOMATIC_RETRY_NOT_AUTHORIZED", "DIRECT_L0_TO_L2_NOT_AUTHORIZED", "OPERATOR_OVERRIDE_NOT_AUTHORIZED"} <= set(decision.failure_codes)
    assert decision.ready is False


def test_audit_is_redacted_immutable_and_rejects_cross_provider_identity() -> None:
    policy, spend, routes, escalation, decision = _evaluate()
    audit = build_provider_budget_audit_evidence_v1(policy, spend, routes, escalation, decision)
    assert audit.exact_model_ids == ("deepseek-v4-pro", "claude-sonnet-5", "claude-opus-4-8")
    assert audit.failure_codes == decision.failure_codes
    with pytest.raises(ValueError):
        build_provider_budget_audit_evidence_v1(policy, (_spend("ANTHROPIC"), spend[1]), routes, escalation, decision)
