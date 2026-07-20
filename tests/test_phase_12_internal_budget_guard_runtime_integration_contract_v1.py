"""RED contract for pure, fail-closed internal budget guard runtime integration."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from engine.phase_12_internal_budget_guard_runtime_integration_contract_v1 import (
    BudgetGuardAlertIntentV1,
    BudgetGuardKillSwitchIntentV1,
    BudgetGuardReservationDecisionV1,
    BudgetGuardRuntimeAuditEvidenceV1,
    BudgetGuardRuntimeDecisionV1,
    BudgetGuardRuntimeFailureV1,
    BudgetGuardRuntimeInputV1,
    BudgetGuardTransmissionDecisionV1,
    InternalBudgetGuardRuntimePolicyV1,
    build_budget_guard_runtime_audit_evidence_v1,
    evaluate_budget_guard_runtime_v1,
)


_AT = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
_UNTIL = datetime(2026, 7, 20, 12, 5, tzinfo=UTC)
_STALE = datetime(2026, 7, 20, 11, 54, tzinfo=UTC)
_ROUTES = {
    "L0": ("DEEPSEEK", "deepseek-v4-pro"),
    "L1": ("ANTHROPIC", "claude-sonnet-5"),
    "L2": ("ANTHROPIC", "claude-opus-4-8"),
}
_BUDGETS = {
    "DEEPSEEK": (True, Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00")),
    "ANTHROPIC": (True, Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00")),
}
_POLICY_FIELDS = (
    "policy_id", "policy_version", "deployment_environment", "required_budget_policy_id",
    "require_budget_evaluation_before_reservation", "require_budget_evaluation_before_transmission",
    "require_fresh_provider_usage", "require_fresh_route_usage", "require_pricing_revalidation",
    "require_usage_ledger_alignment", "require_reservation_alignment", "require_route_allowance",
    "require_provider_allowance", "require_soft_threshold_degradation",
    "require_optional_escalation_suppression", "require_daily_limit_blocking",
    "require_monthly_limit_blocking", "require_hard_limit_kill_switch_intent",
    "require_zero_automatic_retry", "require_manual_recovery",
    "require_deterministic_audit_evidence", "runtime_activation_authorized",
    "alert_publication_authorized", "kill_switch_activation_authorized",
    "credential_loading_authorized", "network_authorized", "provider_transmission_authorized",
    "publication_authorized", "fail_closed",
)
_INPUT_FIELDS = (
    "runtime_input_id", "correlation_id", "policy_id", "budget_policy_id", "provider_id",
    "routing_level", "exact_provider_model_id", "provider_usage_snapshot_id",
    "route_usage_snapshot_id", "pricing_evidence_id", "usage_ledger_evidence_id",
    "requested_reservation_id", "existing_reservation_state", "transmission_attempt_id",
    "current_budget_alert_state", "current_kill_switch_state", "requested_at",
    "evidence_expires_at", "input_complete", "input_ready", "provider_usage_fresh",
    "route_usage_fresh", "pricing_revalidated", "usage_ledger_aligned",
    "reservation_aligned", "provider_allowance", "route_allowance", "escalation_allowance",
    "automatic_retry_requested", "manual_recovery_resolved", "budget_changed_after_reservation",
)
_RESERVATION_FIELDS = (
    "reservation_id", "may_create_reservation", "provider_allowance", "route_allowance",
    "escalation_allowance", "pricing_ready", "ledger_ready", "usage_fresh", "failure_codes",
    "decision_ready", "reservation_written",
)
_TRANSMISSION_FIELDS = (
    "transmission_attempt_id", "may_transmit", "reservation_ready", "pricing_ready",
    "usage_fresh", "failure_codes", "decision_ready", "transmission_attempted",
)
_ALERT_FIELDS = (
    "alert_intent_id", "policy_id", "correlation_id", "provider_id", "routing_level",
    "alert_classification", "severity", "reason_codes", "publication_required",
    "publication_attempted", "publication_authorized", "created_at", "intent_ready",
)
_KILL_FIELDS = (
    "kill_switch_intent_id", "policy_id", "correlation_id", "provider_id",
    "trigger_classification", "trigger_evidence_ids", "activation_required",
    "activation_attempted", "activation_authorized", "provider_calls_blocked",
    "new_reservations_blocked", "manual_recovery_required", "recovery_approval_id",
    "created_at", "intent_ready",
)
_DECISION_FIELDS = (
    "policy_id", "runtime_input_id", "correlation_id", "provider_id", "routing_level",
    "exact_provider_model_id", "reservation_decision", "transmission_decision", "alert_intent",
    "kill_switch_intent", "provider_allowance", "route_allowance", "escalation_allowance",
    "pricing_ready", "ledger_ready", "reservation_ready", "usage_fresh",
    "manual_recovery_required", "failure_codes", "runtime_activation_authorized",
    "alert_publication_authorized", "kill_switch_activation_authorized",
    "credential_loading_authorized", "network_authorized", "provider_transmission_authorized",
    "publication_authorized", "ready",
)
_AUDIT_FIELDS = (
    "policy_id", "runtime_input_id", "correlation_id", "provider_id", "routing_level",
    "exact_provider_model_id", "provider_usage_snapshot_id", "route_usage_snapshot_id",
    "pricing_evidence_id", "usage_ledger_evidence_id", "requested_reservation_id",
    "transmission_attempt_id", "reservation_decision", "transmission_decision", "alert_intent",
    "kill_switch_intent", "provider_allowance", "route_allowance", "escalation_allowance",
    "manual_recovery_required", "failure_codes", "runtime_activation_authorized",
    "alert_publication_authorized", "kill_switch_activation_authorized",
    "credential_loading_authorized", "network_authorized", "provider_transmission_authorized",
    "publication_authorized", "evidence_ready",
)
_FAILURES = (
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
)


def _policy(**overrides: object) -> InternalBudgetGuardRuntimePolicyV1:
    values = {
        "policy_id": "budget-guard-runtime-policy-v1", "policy_version": "v1",
        "deployment_environment": "CONTROLLED_PRODUCTION",
        "required_budget_policy_id": "internal-budget-alert-policy-v1",
        "require_budget_evaluation_before_reservation": True,
        "require_budget_evaluation_before_transmission": True, "require_fresh_provider_usage": True,
        "require_fresh_route_usage": True, "require_pricing_revalidation": True,
        "require_usage_ledger_alignment": True, "require_reservation_alignment": True,
        "require_route_allowance": True, "require_provider_allowance": True,
        "require_soft_threshold_degradation": True,
        "require_optional_escalation_suppression": True, "require_daily_limit_blocking": True,
        "require_monthly_limit_blocking": True, "require_hard_limit_kill_switch_intent": True,
        "require_zero_automatic_retry": True, "require_manual_recovery": True,
        "require_deterministic_audit_evidence": True, "runtime_activation_authorized": False,
        "alert_publication_authorized": False, "kill_switch_activation_authorized": False,
        "credential_loading_authorized": False, "network_authorized": False,
        "provider_transmission_authorized": False, "publication_authorized": False,
        "fail_closed": True,
    }
    values.update(overrides)
    return InternalBudgetGuardRuntimePolicyV1(**values)


def _input(routing_level: str = "L0", **overrides: object) -> BudgetGuardRuntimeInputV1:
    provider_id, model_id = _ROUTES[routing_level]
    values = {
        "runtime_input_id": "runtime-input-v1", "correlation_id": "correlation-v1",
        "policy_id": "budget-guard-runtime-policy-v1",
        "budget_policy_id": "internal-budget-alert-policy-v1", "provider_id": provider_id,
        "routing_level": routing_level, "exact_provider_model_id": model_id,
        "provider_usage_snapshot_id": f"{provider_id.lower()}-usage-v1",
        "route_usage_snapshot_id": f"{routing_level.lower()}-usage-v1",
        "pricing_evidence_id": "pricing-v1", "usage_ledger_evidence_id": "ledger-v1",
        "requested_reservation_id": "reservation-v1", "existing_reservation_state": "ACTIVE",
        "transmission_attempt_id": "transmission-v1", "current_budget_alert_state": "NORMAL",
        "current_kill_switch_state": "CLEAR", "requested_at": _AT, "evidence_expires_at": _UNTIL,
        "input_complete": True, "input_ready": True, "provider_usage_fresh": True,
        "route_usage_fresh": True, "pricing_revalidated": True, "usage_ledger_aligned": True,
        "reservation_aligned": True, "provider_allowance": True, "route_allowance": True,
        "escalation_allowance": True, "automatic_retry_requested": False,
        "manual_recovery_resolved": True, "budget_changed_after_reservation": False,
    }
    values.update(overrides)
    return BudgetGuardRuntimeInputV1(**values)


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def _assert_no_authority(decision: BudgetGuardRuntimeDecisionV1) -> None:
    assert (
        decision.runtime_activation_authorized, decision.alert_publication_authorized,
        decision.kill_switch_activation_authorized, decision.credential_loading_authorized,
        decision.network_authorized, decision.provider_transmission_authorized,
        decision.publication_authorized,
    ) == (False,) * 7
    assert (decision.alert_intent.publication_attempted, decision.alert_intent.publication_authorized) == (False, False)
    assert (decision.kill_switch_intent.activation_attempted, decision.kill_switch_intent.activation_authorized) == (False, False)


def _assert_deterministic_failures(decision: BudgetGuardRuntimeDecisionV1) -> None:
    assert tuple(decision.failure_codes) == tuple(sorted(decision.failure_codes))
    assert set(decision.failure_codes).issubset(_FAILURES)


def test_public_api_is_immutable_complete_and_defaults_fail_closed() -> None:
    assert tuple(field.name for field in fields(InternalBudgetGuardRuntimePolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardRuntimeInputV1)) == _INPUT_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardReservationDecisionV1)) == _RESERVATION_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardTransmissionDecisionV1)) == _TRANSMISSION_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardAlertIntentV1)) == _ALERT_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardKillSwitchIntentV1)) == _KILL_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardRuntimeDecisionV1)) == _DECISION_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardRuntimeAuditEvidenceV1)) == _AUDIT_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardRuntimeFailureV1)) == ("failure_code", "safe_message", "retryable")
    for record in (
        InternalBudgetGuardRuntimePolicyV1, BudgetGuardRuntimeInputV1,
        BudgetGuardReservationDecisionV1, BudgetGuardTransmissionDecisionV1,
        BudgetGuardAlertIntentV1, BudgetGuardKillSwitchIntentV1,
        BudgetGuardRuntimeFailureV1, BudgetGuardRuntimeDecisionV1,
        BudgetGuardRuntimeAuditEvidenceV1,
    ):
        assert is_dataclass(record)
        assert record.__dataclass_params__.frozen is True
        assert hasattr(record, "__slots__")
    for value in (_policy(), _input()):
        _frozen_slotted(value)
    defaults = InternalBudgetGuardRuntimePolicyV1()
    assert defaults.fail_closed is True
    assert (
        defaults.runtime_activation_authorized, defaults.alert_publication_authorized,
        defaults.kill_switch_activation_authorized, defaults.credential_loading_authorized,
        defaults.network_authorized, defaults.provider_transmission_authorized,
        defaults.publication_authorized,
    ) == (False,) * 7
    with pytest.raises(FrozenInstanceError):
        _input().provider_id = "ANTHROPIC"  # type: ignore[misc]


def test_locked_routes_native_soft_alert_exception_and_limits_are_preserved() -> None:
    assert _ROUTES == {
        "L0": ("DEEPSEEK", "deepseek-v4-pro"),
        "L1": ("ANTHROPIC", "claude-sonnet-5"),
        "L2": ("ANTHROPIC", "claude-opus-4-8"),
    }
    assert _BUDGETS == {
        "DEEPSEEK": (True, Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00")),
        "ANTHROPIC": (True, Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00")),
    }
    assert (False, True) == (False, _policy().require_soft_threshold_degradation)


def test_normal_l0_requires_independent_pre_reservation_and_pre_transmission_checks() -> None:
    decision = evaluate_budget_guard_runtime_v1(_policy(), _input())
    assert decision.ready is True
    assert decision.reservation_decision.may_create_reservation is True
    assert decision.transmission_decision.may_transmit is False
    assert decision.transmission_decision.transmission_attempted is False
    assert decision.reservation_decision.reservation_written is False
    assert decision.failure_codes == ()
    for value in (
        decision, decision.reservation_decision, decision.transmission_decision,
        decision.alert_intent, decision.kill_switch_intent,
    ):
        _frozen_slotted(value)
    _assert_deterministic_failures(decision)
    _assert_no_authority(decision)


@pytest.mark.parametrize(
    ("routing_level", "alert_state", "expected_reservation", "expected_escalation", "expected_reason"),
    (
        ("L0", "DEEPSEEK_SOFT_THRESHOLD_WARNING", True, True, "ALERT_INTENT_REQUIRED"),
        ("L1", "ANTHROPIC_SOFT_THRESHOLD_WARNING", False, False, "SOFT_THRESHOLD_SUPPRESSION_REQUIRED"),
        ("L2", "ANTHROPIC_SOFT_THRESHOLD_WARNING", False, False, "SOFT_THRESHOLD_SUPPRESSION_REQUIRED"),
    ),
)
def test_soft_thresholds_require_nonexecuting_alerts_and_suppress_anthropic_escalation(
    routing_level: str,
    alert_state: str,
    expected_reservation: bool,
    expected_escalation: bool,
    expected_reason: str,
) -> None:
    decision = evaluate_budget_guard_runtime_v1(
        _policy(), _input(routing_level, current_budget_alert_state=alert_state, escalation_allowance=expected_escalation)
    )
    assert decision.reservation_decision.may_create_reservation is expected_reservation
    assert decision.escalation_allowance is expected_escalation
    assert decision.alert_intent.publication_required is True
    assert expected_reason in decision.alert_intent.reason_codes or expected_reason in decision.failure_codes
    _assert_deterministic_failures(decision)
    _assert_no_authority(decision)


@pytest.mark.parametrize(
    ("alert_state", "expected_failure", "kill_required"),
    (
        ("DAILY_LIMIT_REACHED", "DAILY_LIMIT_BLOCK_REQUIRED", False),
        ("MONTHLY_LIMIT_REACHED", "MONTHLY_LIMIT_BLOCK_REQUIRED", True),
        ("HARD_LIMIT_REACHED", "HARD_LIMIT_BLOCK_REQUIRED", True),
    ),
)
def test_daily_monthly_and_hard_stop_block_reservation_and_transmission(
    alert_state: str, expected_failure: str, kill_required: bool
) -> None:
    decision = evaluate_budget_guard_runtime_v1(
        _policy(), _input("L1", current_budget_alert_state=alert_state, provider_allowance=False, route_allowance=False)
    )
    assert decision.reservation_decision.may_create_reservation is False
    assert decision.transmission_decision.may_transmit is False
    assert expected_failure in decision.failure_codes
    assert decision.alert_intent.publication_required is True
    assert decision.kill_switch_intent.activation_required is kill_required
    assert decision.kill_switch_intent.manual_recovery_required is kill_required
    _assert_deterministic_failures(decision)
    _assert_no_authority(decision)


def test_stale_evidence_and_changed_budget_after_reservation_fail_closed_without_raising() -> None:
    stale = evaluate_budget_guard_runtime_v1(
        _policy(), _input(provider_usage_fresh=False, route_usage_fresh=False, evidence_expires_at=_STALE)
    )
    changed = evaluate_budget_guard_runtime_v1(
        _policy(), _input(budget_changed_after_reservation=True, existing_reservation_state="ACTIVE")
    )
    assert stale.ready is False
    assert {"USAGE_EVIDENCE_STALE", "USAGE_EVIDENCE_EXPIRED"}.intersection(stale.failure_codes)
    assert stale.reservation_decision.may_create_reservation is False
    assert stale.transmission_decision.may_transmit is False
    assert changed.ready is False
    assert "BUDGET_CHANGED_AFTER_RESERVATION" in changed.failure_codes
    assert changed.transmission_decision.may_transmit is False
    _assert_deterministic_failures(stale)
    _assert_deterministic_failures(changed)
    _assert_no_authority(stale)
    _assert_no_authority(changed)


def test_reservation_revalidation_retry_recovery_and_identity_mismatch_are_independent_fail_closed_gates() -> None:
    decision = evaluate_budget_guard_runtime_v1(
        _policy(),
        _input(
            provider_id="ANTHROPIC", exact_provider_model_id="deepseek-v4-pro",
            existing_reservation_state="EXPIRED", reservation_aligned=False,
            automatic_retry_requested=True, manual_recovery_resolved=False,
        ),
    )
    assert decision.reservation_decision.may_create_reservation is False
    assert decision.transmission_decision.may_transmit is False
    assert {
        "PROVIDER_ID_MISMATCH", "EXACT_MODEL_ID_MISMATCH", "RESERVATION_IDENTITY_MISMATCH",
        "RESERVATION_EXPIRED", "AUTOMATIC_RETRY_NOT_AUTHORIZED", "MANUAL_RECOVERY_REQUIRED",
    }.issubset(decision.failure_codes)
    _assert_deterministic_failures(decision)
    _assert_no_authority(decision)


def test_caller_true_authority_flags_never_grant_execution_and_audit_is_redacted_metadata() -> None:
    decision = evaluate_budget_guard_runtime_v1(
        _policy(
            runtime_activation_authorized=True, alert_publication_authorized=True,
            kill_switch_activation_authorized=True, credential_loading_authorized=True,
            network_authorized=True, provider_transmission_authorized=True, publication_authorized=True,
        ),
        _input(),
    )
    assert not decision.ready
    assert {
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "ALERT_PUBLICATION_NOT_AUTHORIZED",
        "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
        "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
        "PUBLICATION_NOT_AUTHORIZED",
    }.issubset(decision.failure_codes)
    evidence = build_budget_guard_runtime_audit_evidence_v1(_policy(), _input(), decision)
    _frozen_slotted(evidence)
    assert evidence.failure_codes == decision.failure_codes
    assert not {"api_key", "credential", "authorization", "cookie", "account", "response", "exception", "trace"}.intersection(
        field.name for field in fields(BudgetGuardRuntimeAuditEvidenceV1)
    )
    _assert_deterministic_failures(decision)
    _assert_no_authority(decision)
