"""RED contract for a pure, fail-closed budget-guard activation readiness gate."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from engine.phase_12_internal_budget_guard_runtime_activation_readiness_gate_v1 import (
    BudgetGuardActivationAuditEvidenceV1,
    BudgetGuardActivationFailureV1,
    BudgetGuardActivationReadinessDecisionV1,
    BudgetGuardActivationReadinessPolicyV1,
    BudgetGuardBoundaryAttestationV1,
    BudgetGuardOperatorReadinessAttestationV1,
    BudgetGuardReviewerApprovalV1,
    BudgetGuardRuntimeIntegrationAttestationV1,
    build_budget_guard_activation_audit_evidence_v1,
    evaluate_budget_guard_activation_readiness_v1,
)


_AT = datetime(2026, 7, 20, 13, 0, tzinfo=UTC)
_UNTIL = datetime(2026, 7, 20, 13, 5, tzinfo=UTC)
_STALE = datetime(2026, 7, 20, 12, 54, tzinfo=UTC)
_FUTURE = datetime(2026, 7, 20, 13, 1, tzinfo=UTC)
_ROUTES = (
    ("DEEPSEEK", "L0", "DEEPSEEK_V4_PRO", "deepseek-v4-pro"),
    ("ANTHROPIC", "L1", "CLAUDE_SONNET_5", "claude-sonnet-5"),
    ("ANTHROPIC", "L2", "CLAUDE_OPUS_4_8", "claude-opus-4-8"),
)
_BUDGETS = (
    ("DEEPSEEK", True, Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00")),
    ("ANTHROPIC", True, Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00")),
)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "deployment_environment", "required_budget_policy_id",
    "required_runtime_integration_policy_id", "required_pricing_policy_id",
    "required_reservation_policy_id", "required_usage_ledger_policy_id",
    "required_alert_kill_switch_policy_id", "required_provider_route_bindings",
    "required_budget_target_id", "require_provider_hard_caps_confirmed",
    "require_internal_soft_alerts_implemented", "require_daily_monthly_caps",
    "require_pricing_revalidation", "require_pre_call_reservation",
    "require_usage_ledger_alignment", "require_pre_reservation_budget_evaluation",
    "require_pre_transmission_budget_revalidation", "require_alert_intent",
    "require_kill_switch_intent", "require_manual_recovery", "require_zero_automatic_retry",
    "require_deterministic_audit_evidence", "require_independent_reviewer",
    "require_evidence_freshness", "runtime_activation_authorized",
    "runtime_configuration_authorized", "credential_loading_authorized", "network_authorized",
    "provider_transmission_authorized", "alert_publication_authorized",
    "kill_switch_activation_authorized", "publication_authorized", "fail_closed",
)
_BOUNDARY_FIELDS = (
    "boundary_attestation_id", "policy_id", "budget_policy_id", "runtime_integration_policy_id",
    "pricing_policy_id", "reservation_policy_id", "usage_ledger_policy_id",
    "alert_kill_switch_policy_id", "provider_id", "routing_level", "exact_provider_model_id",
    "locked_budget_target_id", "provider_hard_caps_confirmed",
    "native_soft_alert_exception_preserved", "internal_soft_alerts_implemented",
    "daily_monthly_caps_confirmed", "route_limits_confirmed", "token_call_limits_confirmed",
    "escalation_limits_confirmed", "pricing_revalidation_ready", "reservation_boundary_ready",
    "usage_ledger_boundary_ready", "alert_kill_switch_boundary_ready",
    "runtime_integration_boundary_ready", "authority_invariants_confirmed",
    "redaction_invariants_confirmed", "deterministic_failures_confirmed", "audit_purity_confirmed",
    "attested_at", "evidence_expires_at", "attestation_complete", "attestation_ready",
)
_RUNTIME_FIELDS = (
    "runtime_integration_attestation_id", "policy_id", "runtime_integration_policy_id",
    "provider_id", "routing_level", "exact_provider_model_id", "pre_reservation_evaluation_ready",
    "pre_transmission_revalidation_ready", "stale_usage_block_ready",
    "budget_change_block_ready", "soft_threshold_suppression_ready", "daily_limit_block_ready",
    "monthly_hard_limit_block_ready", "alert_intent_nonexecuting", "kill_switch_intent_nonexecuting",
    "manual_recovery_ready", "automatic_retry_disabled", "reservation_mutation_absent",
    "provider_transmission_absent", "runtime_activation_absent", "attested_at",
    "evidence_expires_at", "attestation_complete", "attestation_ready",
)
_OPERATOR_FIELDS = (
    "operator_attestation_id", "policy_id", "boundary_attestation_id",
    "runtime_integration_attestation_id", "operator_id", "provider_id", "routing_level",
    "exact_provider_model_id", "locked_budget_target_id", "checklist_complete",
    "hard_caps_confirmed", "internal_soft_alerts_confirmed", "pricing_reservation_ledger_confirmed",
    "runtime_guard_confirmed", "alert_kill_switch_confirmed", "manual_recovery_confirmed",
    "authority_invariants_confirmed", "attested_at", "evidence_expires_at",
    "attestation_complete", "attestation_ready",
)
_REVIEW_FIELDS = (
    "review_id", "policy_id", "operator_attestation_id", "boundary_attestation_id",
    "runtime_integration_attestation_id", "reviewer_id", "operator_id", "provider_id",
    "routing_level", "exact_provider_model_id", "locked_budget_target_id",
    "hard_caps_confirmed", "internal_soft_alerts_confirmed",
    "pricing_reservation_ledger_confirmed", "runtime_guard_confirmed",
    "alert_kill_switch_confirmed", "manual_recovery_confirmed",
    "authority_invariants_confirmed", "approved", "reviewed_at", "evidence_expires_at",
    "review_complete", "review_ready",
)
_DECISION_FIELDS = (
    "policy_id", "boundary_attestation_id", "runtime_integration_attestation_id",
    "operator_attestation_id", "review_id", "provider_id", "routing_level",
    "exact_provider_model_id", "locked_budget_target_id", "provider_hard_cap_ready",
    "internal_soft_alert_ready", "pricing_ready", "reservation_ready", "usage_ledger_ready",
    "runtime_guard_ready", "alert_intent_ready", "kill_switch_intent_ready",
    "manual_recovery_ready", "operator_attestation_ready", "independent_review_ready",
    "evidence_fresh", "failure_codes", "runtime_activation_authorized",
    "runtime_configuration_authorized", "credential_loading_authorized", "network_authorized",
    "provider_transmission_authorized", "alert_publication_authorized",
    "kill_switch_activation_authorized", "publication_authorized", "ready",
)
_AUDIT_FIELDS = (
    "policy_id", "boundary_attestation_id", "runtime_integration_attestation_id",
    "operator_attestation_id", "review_id", "provider_id", "routing_level",
    "exact_provider_model_id", "locked_budget_target_id", "operator_id", "reviewer_id",
    "provider_hard_cap_ready", "internal_soft_alert_ready", "pricing_ready",
    "reservation_ready", "usage_ledger_ready", "runtime_guard_ready", "alert_intent_ready",
    "kill_switch_intent_ready", "manual_recovery_ready", "evidence_fresh", "failure_codes",
    "runtime_activation_authorized", "runtime_configuration_authorized",
    "credential_loading_authorized", "network_authorized", "provider_transmission_authorized",
    "alert_publication_authorized", "kill_switch_activation_authorized",
    "publication_authorized", "evidence_ready",
)
_FAILURES = {
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
}


def _policy(**overrides: object) -> BudgetGuardActivationReadinessPolicyV1:
    values = {
        "policy_id": "budget-guard-activation-policy-v1", "policy_version": "v1",
        "deployment_environment": "CONTROLLED_PRODUCTION",
        "required_budget_policy_id": "internal-budget-alert-policy-v1",
        "required_runtime_integration_policy_id": "budget-guard-runtime-policy-v1",
        "required_pricing_policy_id": "pricing-policy-v1", "required_reservation_policy_id": "reservation-policy-v1",
        "required_usage_ledger_policy_id": "usage-ledger-policy-v1",
        "required_alert_kill_switch_policy_id": "internal-budget-alert-policy-v1",
        "required_provider_route_bindings": _ROUTES, "required_budget_target_id": "budget-target-v1",
        "require_provider_hard_caps_confirmed": True, "require_internal_soft_alerts_implemented": True,
        "require_daily_monthly_caps": True, "require_pricing_revalidation": True,
        "require_pre_call_reservation": True, "require_usage_ledger_alignment": True,
        "require_pre_reservation_budget_evaluation": True,
        "require_pre_transmission_budget_revalidation": True, "require_alert_intent": True,
        "require_kill_switch_intent": True, "require_manual_recovery": True,
        "require_zero_automatic_retry": True, "require_deterministic_audit_evidence": True,
        "require_independent_reviewer": True, "require_evidence_freshness": True,
        "runtime_activation_authorized": False, "runtime_configuration_authorized": False,
        "credential_loading_authorized": False, "network_authorized": False,
        "provider_transmission_authorized": False, "alert_publication_authorized": False,
        "kill_switch_activation_authorized": False, "publication_authorized": False, "fail_closed": True,
    }
    values.update(overrides)
    return BudgetGuardActivationReadinessPolicyV1(**values)


def _boundary(**overrides: object) -> BudgetGuardBoundaryAttestationV1:
    values = {name: True for name in _BOUNDARY_FIELDS if name.endswith("confirmed") or name.endswith("ready") or name.endswith("complete")}
    values.update({
        "boundary_attestation_id": "boundary-attestation-v1", "policy_id": "budget-guard-activation-policy-v1",
        "budget_policy_id": "internal-budget-alert-policy-v1", "runtime_integration_policy_id": "budget-guard-runtime-policy-v1",
        "pricing_policy_id": "pricing-policy-v1", "reservation_policy_id": "reservation-policy-v1",
        "usage_ledger_policy_id": "usage-ledger-policy-v1", "alert_kill_switch_policy_id": "internal-budget-alert-policy-v1",
        "provider_id": "DEEPSEEK", "routing_level": "L0", "exact_provider_model_id": "deepseek-v4-pro",
        "locked_budget_target_id": "budget-target-v1", "attested_at": _AT, "evidence_expires_at": _UNTIL,
    })
    values.update(overrides)
    return BudgetGuardBoundaryAttestationV1(**values)


def _runtime(**overrides: object) -> BudgetGuardRuntimeIntegrationAttestationV1:
    values = {name: True for name in _RUNTIME_FIELDS if name.endswith("ready") or name.endswith("complete") or name.endswith("absent") or name.endswith("nonexecuting") or name.endswith("disabled")}
    values.update({
        "runtime_integration_attestation_id": "runtime-attestation-v1", "policy_id": "budget-guard-activation-policy-v1",
        "runtime_integration_policy_id": "budget-guard-runtime-policy-v1", "provider_id": "DEEPSEEK",
        "routing_level": "L0", "exact_provider_model_id": "deepseek-v4-pro", "attested_at": _AT,
        "evidence_expires_at": _UNTIL,
    })
    values.update(overrides)
    return BudgetGuardRuntimeIntegrationAttestationV1(**values)


def _operator(**overrides: object) -> BudgetGuardOperatorReadinessAttestationV1:
    values = {name: True for name in _OPERATOR_FIELDS if name.endswith("confirmed") or name.endswith("complete") or name.endswith("ready")}
    values.update({
        "operator_attestation_id": "operator-attestation-v1", "policy_id": "budget-guard-activation-policy-v1",
        "boundary_attestation_id": "boundary-attestation-v1", "runtime_integration_attestation_id": "runtime-attestation-v1",
        "operator_id": "operator-v1", "provider_id": "DEEPSEEK", "routing_level": "L0",
        "exact_provider_model_id": "deepseek-v4-pro", "locked_budget_target_id": "budget-target-v1",
        "attested_at": _AT, "evidence_expires_at": _UNTIL,
    })
    values.update(overrides)
    return BudgetGuardOperatorReadinessAttestationV1(**values)


def _review(**overrides: object) -> BudgetGuardReviewerApprovalV1:
    values = {name: True for name in _REVIEW_FIELDS if name.endswith("confirmed") or name.endswith("complete") or name.endswith("ready")}
    values.update({
        "review_id": "review-v1", "policy_id": "budget-guard-activation-policy-v1",
        "operator_attestation_id": "operator-attestation-v1", "boundary_attestation_id": "boundary-attestation-v1",
        "runtime_integration_attestation_id": "runtime-attestation-v1", "reviewer_id": "reviewer-v1",
        "operator_id": "operator-v1", "provider_id": "DEEPSEEK", "routing_level": "L0",
        "exact_provider_model_id": "deepseek-v4-pro", "locked_budget_target_id": "budget-target-v1",
        "approved": True, "reviewed_at": _AT, "evidence_expires_at": _UNTIL,
    })
    values.update(overrides)
    return BudgetGuardReviewerApprovalV1(**values)


def _frozen(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def _assert_no_authority(decision: BudgetGuardActivationReadinessDecisionV1) -> None:
    assert (
        decision.runtime_activation_authorized, decision.runtime_configuration_authorized,
        decision.credential_loading_authorized, decision.network_authorized,
        decision.provider_transmission_authorized, decision.alert_publication_authorized,
        decision.kill_switch_activation_authorized, decision.publication_authorized,
    ) == (False,) * 8


def test_public_api_is_immutable_complete_and_fail_closed() -> None:
    assert tuple(field.name for field in fields(BudgetGuardActivationReadinessPolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardBoundaryAttestationV1)) == _BOUNDARY_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardRuntimeIntegrationAttestationV1)) == _RUNTIME_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardOperatorReadinessAttestationV1)) == _OPERATOR_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardReviewerApprovalV1)) == _REVIEW_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardActivationReadinessDecisionV1)) == _DECISION_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardActivationAuditEvidenceV1)) == _AUDIT_FIELDS
    assert tuple(field.name for field in fields(BudgetGuardActivationFailureV1)) == ("failure_code", "safe_message", "retryable")
    for value in (_policy(), _boundary(), _runtime(), _operator(), _review()):
        _frozen(value)
    defaults = BudgetGuardActivationReadinessPolicyV1()
    assert defaults.fail_closed is True
    assert not any((
        defaults.runtime_activation_authorized, defaults.runtime_configuration_authorized,
        defaults.credential_loading_authorized, defaults.network_authorized,
        defaults.provider_transmission_authorized, defaults.alert_publication_authorized,
        defaults.kill_switch_activation_authorized, defaults.publication_authorized,
    ))
    with pytest.raises(FrozenInstanceError):
        _policy().policy_id = "other"  # type: ignore[misc]


def test_locked_routes_native_exception_and_exact_budget_limits_are_required() -> None:
    assert _ROUTES == (
        ("DEEPSEEK", "L0", "DEEPSEEK_V4_PRO", "deepseek-v4-pro"),
        ("ANTHROPIC", "L1", "CLAUDE_SONNET_5", "claude-sonnet-5"),
        ("ANTHROPIC", "L2", "CLAUDE_OPUS_4_8", "claude-opus-4-8"),
    )
    assert _BUDGETS == (
        ("DEEPSEEK", True, Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00")),
        ("ANTHROPIC", True, Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00")),
    )
    assert (False, True) == (False, _policy().require_internal_soft_alerts_implemented)


def test_complete_readiness_is_only_evidence_for_a_separate_owner_activation_decision() -> None:
    policy, boundary, runtime, operator, review = _policy(), _boundary(), _runtime(), _operator(), _review()
    decision = evaluate_budget_guard_activation_readiness_v1(policy, boundary, runtime, operator, review, _AT)
    audit = build_budget_guard_activation_audit_evidence_v1(policy, boundary, runtime, operator, review, decision)
    assert decision.ready is True
    assert decision.failure_codes == ()
    for value in (decision, audit):
        _frozen(value)
    _assert_no_authority(decision)
    assert audit.evidence_ready is True


@pytest.mark.parametrize(
    ("boundary_changes", "runtime_changes", "expected_failure"),
    (
        ({"provider_hard_caps_confirmed": False}, {}, "PROVIDER_HARD_CAP_NOT_CONFIRMED"),
        ({"native_soft_alert_exception_preserved": False}, {}, "NATIVE_SOFT_ALERT_EXCEPTION_MISMATCH"),
        ({"pricing_revalidation_ready": False, "reservation_boundary_ready": False}, {}, "PRICING_NOT_REVALIDATED"),
        ({}, {"pre_reservation_evaluation_ready": False, "pre_transmission_revalidation_ready": False}, "PRE_RESERVATION_EVALUATION_NOT_READY"),
        ({}, {"stale_usage_block_ready": False, "budget_change_block_ready": False, "daily_limit_block_ready": False, "monthly_hard_limit_block_ready": False}, "STALE_USAGE_BLOCK_NOT_READY"),
    ),
)
def test_cross_contract_boundary_failures_are_deterministic_and_fail_closed(
    boundary_changes: dict[str, object], runtime_changes: dict[str, object], expected_failure: str
) -> None:
    decision = evaluate_budget_guard_activation_readiness_v1(
        _policy(), _boundary(**boundary_changes), _runtime(**runtime_changes), _operator(), _review(), _AT
    )
    assert decision.ready is False
    assert expected_failure in decision.failure_codes
    assert tuple(decision.failure_codes) == tuple(sorted(decision.failure_codes))
    assert set(decision.failure_codes).issubset(_FAILURES)
    _assert_no_authority(decision)


@pytest.mark.parametrize(
    ("attested_at", "expires_at", "expected_failure"),
    ((_STALE, _STALE, "EVIDENCE_EXPIRED"), (_FUTURE, _UNTIL, "EVIDENCE_FROM_FUTURE")),
)
def test_stale_expired_and_future_evidence_block_readiness(
    attested_at: datetime, expires_at: datetime, expected_failure: str
) -> None:
    decision = evaluate_budget_guard_activation_readiness_v1(
        _policy(), _boundary(attested_at=attested_at, evidence_expires_at=expires_at),
        _runtime(attested_at=attested_at, evidence_expires_at=expires_at),
        _operator(attested_at=attested_at, evidence_expires_at=expires_at),
        _review(reviewed_at=attested_at, evidence_expires_at=expires_at), _AT,
    )
    assert decision.ready is False
    assert expected_failure in decision.failure_codes
    _assert_no_authority(decision)


def test_operator_reviewer_separation_and_true_caller_authorities_never_grant_activation() -> None:
    collision = evaluate_budget_guard_activation_readiness_v1(
        _policy(), _boundary(), _runtime(), _operator(), _review(reviewer_id="operator-v1"), _AT
    )
    asserted = evaluate_budget_guard_activation_readiness_v1(
        _policy(
            runtime_activation_authorized=True, runtime_configuration_authorized=True,
            credential_loading_authorized=True, network_authorized=True,
            provider_transmission_authorized=True, alert_publication_authorized=True,
            kill_switch_activation_authorized=True, publication_authorized=True,
        ),
        _boundary(), _runtime(), _operator(), _review(), _AT,
    )
    assert "OPERATOR_REVIEWER_COLLISION" in collision.failure_codes
    assert {
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "RUNTIME_CONFIGURATION_NOT_AUTHORIZED",
        "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "ALERT_PUBLICATION_NOT_AUTHORIZED",
        "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    }.issubset(asserted.failure_codes)
    _assert_no_authority(collision)
    _assert_no_authority(asserted)


def test_audit_is_identity_bound_redacted_deterministic_and_non_operational() -> None:
    policy, boundary, runtime, operator, review = _policy(), _boundary(), _runtime(), _operator(), _review()
    decision = evaluate_budget_guard_activation_readiness_v1(policy, boundary, runtime, operator, review, _AT)
    audit = build_budget_guard_activation_audit_evidence_v1(policy, boundary, runtime, operator, review, decision)
    assert audit == build_budget_guard_activation_audit_evidence_v1(policy, boundary, runtime, operator, review, decision)
    assert not {"api_key", "credential", "authorization", "cookie", "account", "response", "exception", "trace"}.intersection(
        field.name for field in fields(BudgetGuardActivationAuditEvidenceV1)
    )
    with pytest.raises(ValueError):
        build_budget_guard_activation_audit_evidence_v1(policy, _boundary(provider_id="ANTHROPIC"), runtime, operator, review, decision)
