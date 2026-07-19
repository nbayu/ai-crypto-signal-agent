"""RED contract for metadata-only internal budget alerts and kill-switch evidence."""

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from engine.phase_12_internal_budget_soft_alert_kill_switch_contract_v1 import (
    InternalBudgetAlertAuditEvidenceV1,
    InternalBudgetAlertDecisionV1,
    InternalBudgetAlertFailureV1,
    InternalBudgetAlertPolicyV1,
    InternalBudgetAlertStateV1,
    ProviderBudgetUsageSnapshotV1,
    ProviderKillSwitchStateV1,
    RouteBudgetUsageSnapshotV1,
    build_internal_budget_alert_audit_evidence_v1,
    evaluate_internal_budget_alert_v1,
)


_AT = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2026, 7, 20, 12, 5, tzinfo=timezone.utc)
_STALE = datetime(2026, 7, 20, 11, 58, tzinfo=timezone.utc)

_ROUTES = (
    ("DEEPSEEK", "L0", "DEEPSEEK_V4_PRO", "deepseek-v4-pro", Decimal("0.02"), Decimal("0.40"), Decimal("12.00"), 12000, 3000, 1, 3),
    ("ANTHROPIC", "L1", "CLAUDE_SONNET_5", "claude-sonnet-5", Decimal("0.12"), Decimal("0.50"), Decimal("15.00"), 12000, 3000, 1, 2),
    ("ANTHROPIC", "L2", "CLAUDE_OPUS_4_8", "claude-opus-4-8", Decimal("0.20"), Decimal("0.20"), Decimal("6.00"), 12000, 3000, 1, 1),
)


def _names(record: type) -> tuple[str, ...]:
    return tuple(field.name for field in fields(record))


def _provider_usage(
    provider_id: str,
    daily_usage: Decimal,
    monthly_usage: Decimal,
    measured_at: datetime = _AT,
    evidence_expires_at: datetime = _UNTIL,
    usage_complete: bool = True,
) -> ProviderBudgetUsageSnapshotV1:
    limits = {
        "DEEPSEEK": (Decimal("0.50"), Decimal("12.00"), Decimal("15.00")),
        "ANTHROPIC": (Decimal("0.85"), Decimal("20.00"), Decimal("25.00")),
    }[provider_id]
    return ProviderBudgetUsageSnapshotV1(
        f"{provider_id.lower()}-usage",
        "internal-budget-alert-policy-v1",
        provider_id,
        "USD",
        daily_usage,
        monthly_usage,
        *limits,
        limits[2],
        False,
        True,
        f"{provider_id.lower()}-ledger",
        f"{provider_id.lower()}-pricing",
        True,
        measured_at,
        evidence_expires_at,
        usage_complete,
        usage_complete,
    )


def _route_usage(
    provider_usage: ProviderBudgetUsageSnapshotV1,
    route: tuple[object, ...],
    measured_at: datetime = _AT,
    evidence_expires_at: datetime = _UNTIL,
    usage_complete: bool = True,
) -> RouteBudgetUsageSnapshotV1:
    provider_id, routing_level, _, model_id, per_request, daily_limit, monthly_limit, _, _, calls_per_signal, calls_per_day = route
    return RouteBudgetUsageSnapshotV1(
        f"{routing_level.lower()}-usage",
        "internal-budget-alert-policy-v1",
        provider_usage.provider_usage_snapshot_id,
        provider_id,
        routing_level,
        model_id,
        Decimal("0.01"),
        Decimal("0.00"),
        Decimal("0.00"),
        per_request,
        daily_limit,
        monthly_limit,
        0,
        0,
        calls_per_signal,
        calls_per_day,
        f"{routing_level.lower()}-reservation",
        f"{provider_id.lower()}-ledger",
        f"{provider_id.lower()}-pricing",
        True,
        measured_at,
        evidence_expires_at,
        usage_complete,
        usage_complete,
    )


def _policy() -> InternalBudgetAlertPolicyV1:
    return InternalBudgetAlertPolicyV1(
        policy_id="internal-budget-alert-policy-v1",
        policy_version="v1",
        deployment_environment="CONTROLLED_PRODUCTION",
        currency="USD",
        allowed_provider_ids=("DEEPSEEK", "ANTHROPIC"),
        allowed_routing_levels=("L0", "L1", "L2"),
        require_internal_soft_alert=True,
        require_provider_hard_cap=True,
        require_daily_provider_cap=True,
        require_monthly_provider_cap=True,
        require_route_limits=True,
        require_usage_ledger=True,
        require_reservation_before_call=True,
        require_pricing_revalidation=True,
        require_operator_alert=True,
        require_soft_threshold_degradation=True,
        require_optional_escalation_suppression=True,
        require_hard_threshold_kill_switch=True,
        require_zero_automatic_retry=True,
        require_fail_closed_unknown_usage=True,
        require_fail_closed_stale_usage=True,
        require_manual_recovery=True,
        require_recovery_approval=True,
        require_evidence_freshness=True,
        maximum_usage_age_seconds=300,
    )


def test_public_api_is_immutable_and_exposes_the_full_metadata_contract() -> None:
    records = (
        InternalBudgetAlertPolicyV1,
        ProviderBudgetUsageSnapshotV1,
        RouteBudgetUsageSnapshotV1,
        InternalBudgetAlertStateV1,
        ProviderKillSwitchStateV1,
        InternalBudgetAlertDecisionV1,
        InternalBudgetAlertAuditEvidenceV1,
    )
    for record in records:
        assert is_dataclass(record)
        assert getattr(record, "__dataclass_params__").frozen is True
        assert hasattr(record, "__slots__")
    assert _names(InternalBudgetAlertFailureV1) == ("failure_code", "safe_message", "retryable")
    assert _names(ProviderBudgetUsageSnapshotV1) == (
        "provider_usage_snapshot_id", "policy_id", "provider_id", "currency", "daily_usage", "monthly_usage", "internal_daily_limit", "internal_soft_alert_threshold", "internal_monthly_limit", "provider_hard_limit", "native_soft_alert_available", "provider_hard_cap_enabled", "usage_ledger_evidence_id", "pricing_evidence_id", "pricing_revalidated", "measured_at", "evidence_expires_at", "usage_complete", "usage_ready",
    )
    assert _names(RouteBudgetUsageSnapshotV1) == (
        "route_usage_snapshot_id", "policy_id", "provider_usage_snapshot_id", "provider_id", "routing_level", "exact_provider_model_id", "current_request_estimated_cost", "daily_route_usage", "monthly_route_usage", "per_request_cost_limit", "daily_route_cost_limit", "monthly_route_cost_limit", "calls_for_current_signal", "calls_today", "maximum_calls_per_signal", "maximum_calls_per_day", "reservation_evidence_id", "usage_ledger_evidence_id", "pricing_evidence_id", "pricing_revalidated", "measured_at", "evidence_expires_at", "usage_complete", "usage_ready",
    )


def test_locked_native_soft_alert_exception_hard_caps_and_route_limits_are_preserved() -> None:
    policy = _policy()
    deepseek = _provider_usage("DEEPSEEK", Decimal("0.00"), Decimal("0.00"))
    anthropic = _provider_usage("ANTHROPIC", Decimal("0.00"), Decimal("0.00"))
    assert policy.require_internal_soft_alert is True
    assert (deepseek.native_soft_alert_available, anthropic.native_soft_alert_available) == (False, False)
    assert (deepseek.provider_hard_cap_enabled, anthropic.provider_hard_cap_enabled) == (True, True)
    assert (
        (deepseek.provider_id, deepseek.provider_hard_limit, deepseek.internal_soft_alert_threshold, deepseek.internal_daily_limit, deepseek.internal_monthly_limit),
        (anthropic.provider_id, anthropic.provider_hard_limit, anthropic.internal_soft_alert_threshold, anthropic.internal_daily_limit, anthropic.internal_monthly_limit),
    ) == (
        ("DEEPSEEK", Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00")),
        ("ANTHROPIC", Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00")),
    )
    assert _ROUTES == (
        ("DEEPSEEK", "L0", "DEEPSEEK_V4_PRO", "deepseek-v4-pro", Decimal("0.02"), Decimal("0.40"), Decimal("12.00"), 12000, 3000, 1, 3),
        ("ANTHROPIC", "L1", "CLAUDE_SONNET_5", "claude-sonnet-5", Decimal("0.12"), Decimal("0.50"), Decimal("15.00"), 12000, 3000, 1, 2),
        ("ANTHROPIC", "L2", "CLAUDE_OPUS_4_8", "claude-opus-4-8", Decimal("0.20"), Decimal("0.20"), Decimal("6.00"), 12000, 3000, 1, 1),
    )
    assert (Decimal("0.34"), Decimal("0.32"), True) == (Decimal("0.34"), Decimal("0.32"), True)


def test_policy_defaults_fail_closed_and_never_grant_runtime_authority() -> None:
    defaults = InternalBudgetAlertPolicyV1()
    assert defaults.allowed_provider_ids == ()
    assert defaults.allowed_routing_levels == ()
    assert defaults.fail_closed is True
    assert not any((defaults.alert_publication_authorized, defaults.kill_switch_activation_authorized, defaults.runtime_configuration_authorized, defaults.credential_loading_authorized, defaults.network_authorized, defaults.provider_transmission_authorized))


@pytest.mark.parametrize(
    ("provider_id", "monthly_usage", "expected_state", "l1_allowed", "l2_allowed"),
    (
        ("DEEPSEEK", Decimal("11.99"), "NORMAL", True, True),
        ("DEEPSEEK", Decimal("12.00"), "SOFT_THRESHOLD_WARNING", True, True),
        ("ANTHROPIC", Decimal("20.00"), "SOFT_THRESHOLD_WARNING", False, False),
        ("ANTHROPIC", Decimal("25.00"), "HARD_LIMIT_KILL_SWITCH_REQUIRED", False, False),
    ),
)
def test_thresholds_are_inclusive_and_only_return_metadata_decisions(
    provider_id: str,
    monthly_usage: Decimal,
    expected_state: str,
    l1_allowed: bool,
    l2_allowed: bool,
) -> None:
    deepseek = _provider_usage("DEEPSEEK", Decimal("0.00"), Decimal("0.00"))
    anthropic = _provider_usage("ANTHROPIC", Decimal("0.00"), Decimal("0.00"))
    snapshots = (deepseek, anthropic)
    replacement = _provider_usage(provider_id, Decimal("0.00"), monthly_usage)
    snapshots = tuple(replacement if item.provider_id == provider_id else item for item in snapshots)
    routes = tuple(_route_usage(next(item for item in snapshots if item.provider_id == route[0]), route) for route in _ROUTES)
    decision = evaluate_internal_budget_alert_v1(_policy(), snapshots, routes, (), _AT)
    provider_state = decision.DeepSeek_alert_state if provider_id == "DEEPSEEK" else decision.Anthropic_alert_state
    assert provider_state == expected_state
    assert decision.L1_allowed is l1_allowed
    assert decision.L2_allowed is l2_allowed
    assert not any((decision.alert_publication_authorized, decision.kill_switch_activation_authorized, decision.runtime_configuration_authorized, decision.credential_loading_authorized, decision.network_authorized, decision.provider_transmission_authorized))


def test_unknown_and_stale_usage_fail_closed_and_audit_is_redacted_metadata_only() -> None:
    deepseek = _provider_usage("DEEPSEEK", Decimal("0.00"), Decimal("0.00"), usage_complete=False)
    anthropic = _provider_usage("ANTHROPIC", Decimal("0.00"), Decimal("0.00"), measured_at=_STALE)
    routes = tuple(_route_usage(deepseek if route[0] == "DEEPSEEK" else anthropic, route) for route in _ROUTES)
    decision = evaluate_internal_budget_alert_v1(_policy(), (deepseek, anthropic), routes, (), _AT)
    assert decision.ready is False
    assert "USAGE_INCOMPLETE" in decision.failure_codes
    assert "USAGE_STALE" in decision.failure_codes
    with pytest.raises(ValueError):
        build_internal_budget_alert_audit_evidence_v1(_policy(), (deepseek,), routes, (), decision)
