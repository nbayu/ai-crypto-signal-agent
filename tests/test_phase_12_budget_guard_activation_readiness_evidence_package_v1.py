"""RED contract for a pure budget-guard activation-readiness evidence package."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from engine.phase_12_budget_guard_activation_readiness_evidence_package_v1 import (
    BudgetGuardBoundaryEvidenceBundleV1,
    BudgetGuardIndependentReviewEvidenceV1,
    BudgetGuardOperatorEvidenceAttestationV1,
    BudgetGuardOwnerActivationDecisionRecordV1,
    BudgetGuardReadinessEvidenceAuditV1,
    BudgetGuardReadinessEvidenceDecisionV1,
    BudgetGuardReadinessEvidenceFailureV1,
    BudgetGuardReadinessEvidencePolicyV1,
    build_budget_guard_readiness_evidence_audit_v1,
    evaluate_budget_guard_readiness_evidence_v1,
)


_AT = datetime(2026, 7, 20, 14, 0, tzinfo=UTC)
_UNTIL = datetime(2026, 7, 20, 14, 5, tzinfo=UTC)
_STALE = datetime(2026, 7, 20, 13, 54, tzinfo=UTC)
_FUTURE = datetime(2026, 7, 20, 14, 1, tzinfo=UTC)
_ROUTES = (
    ("DEEPSEEK", "L0", "DEEPSEEK_V4_PRO", "deepseek-v4-pro"),
    ("ANTHROPIC", "L1", "CLAUDE_SONNET_5", "claude-sonnet-5"),
    ("ANTHROPIC", "L2", "CLAUDE_OPUS_4_8", "claude-opus-4-8"),
)
_BUDGETS = (
    ("DEEPSEEK", True, Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00")),
    ("ANTHROPIC", True, Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00")),
)
_POLICY = (
    "policy_id", "policy_version", "deployment_environment", "required_activation_readiness_policy_id",
    "required_runtime_guard_policy_id", "required_budget_policy_id", "required_pricing_policy_id",
    "required_reservation_policy_id", "required_usage_ledger_policy_id", "required_alert_policy_id",
    "require_exact_provider_and_model_bindings", "require_exact_budget_profile",
    "require_provider_hard_caps_confirmed", "require_internal_soft_alerts_ready",
    "require_pre_reservation_guard", "require_pre_transmission_revalidation",
    "require_daily_monthly_hard_limit_blocks", "require_alert_intent", "require_kill_switch_intent",
    "require_manual_recovery", "require_zero_automatic_retry", "require_operator_attestation",
    "require_independent_reviewer", "require_owner_activation_decision_record",
    "require_evidence_freshness", "require_redacted_evidence", "require_pure_audit",
    "runtime_activation_authorized", "runtime_configuration_authorized",
    "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized",
    "provider_transmission_authorized", "alert_publication_authorized",
    "kill_switch_activation_authorized", "publication_authorized", "fail_closed",
)
_BUNDLE = (
    "boundary_bundle_id", "policy_id", "activation_readiness_policy_id", "runtime_guard_policy_id",
    "internal_alert_policy_id", "budget_policy_id", "pricing_policy_id", "reservation_policy_id",
    "usage_ledger_policy_id", "provider_budget_configuration_id", "provider_hard_cap_confirmation_id",
    "provider_id", "routing_level", "exact_provider_model_id", "locked_budget_target_id",
    "internal_soft_alert_substitution_id", "pre_reservation_guard_ready",
    "pre_transmission_revalidation_ready", "stale_usage_block_ready", "budget_change_block_ready",
    "daily_monthly_hard_blocks_ready", "alert_intent_ready", "kill_switch_intent_ready",
    "manual_recovery_ready", "automatic_retry_disabled", "authority_invariants_confirmed",
    "redaction_invariants_confirmed", "audit_purity_confirmed", "verified_at", "evidence_expires_at",
    "bundle_complete", "bundle_ready",
)
_OPERATOR = (
    "operator_attestation_id", "policy_id", "boundary_bundle_id", "operator_id", "operator_role",
    "provider_id", "routing_level", "exact_provider_model_id", "locked_budget_target_id",
    "routing_budget_confirmed", "hard_caps_confirmed", "internal_soft_alerts_confirmed",
    "pricing_confirmed", "reservation_ledger_confirmed", "runtime_guard_confirmed",
    "alert_kill_switch_confirmed", "manual_recovery_confirmed", "automatic_retry_disabled",
    "authority_invariants_confirmed", "redaction_confirmed", "audit_purity_confirmed",
    "verified_at", "evidence_expires_at", "attestation_complete", "attestation_ready",
)
_REVIEW = (
    "review_evidence_id", "policy_id", "boundary_bundle_id", "operator_attestation_id",
    "reviewer_id", "reviewer_role", "operator_id", "provider_id", "routing_level",
    "exact_provider_model_id", "locked_budget_target_id", "routing_budget_confirmed",
    "hard_caps_confirmed", "internal_soft_alerts_confirmed", "pricing_reservation_ledger_confirmed",
    "runtime_guard_confirmed", "alert_kill_switch_confirmed", "manual_recovery_confirmed",
    "automatic_retry_disabled", "authority_invariants_confirmed", "approved", "reviewed_at",
    "evidence_expires_at", "review_complete", "review_ready",
)
_OWNER = (
    "owner_decision_id", "policy_id", "boundary_bundle_id", "readiness_evidence_accepted",
    "runtime_activation_decision_state", "runtime_activation_approved", "credential_onboarding_state",
    "activation_scope", "owner_id", "decided_at", "evidence_expires_at", "rationale_classification",
    "runtime_activation_authorized", "runtime_configuration_authorized",
    "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized",
    "provider_transmission_authorized", "alert_publication_authorized",
    "kill_switch_activation_authorized", "publication_authorized",
)
_DECISION = (
    "policy_id", "boundary_bundle_id", "operator_attestation_id", "review_evidence_id",
    "owner_decision_id", "provider_id", "routing_level", "exact_provider_model_id",
    "locked_budget_target_id", "routing_ready", "budget_ready", "hard_cap_ready",
    "internal_soft_alert_ready", "pricing_ready", "reservation_ready", "usage_ledger_ready",
    "runtime_guard_ready", "alert_intent_ready", "kill_switch_intent_ready", "manual_recovery_ready",
    "operator_ready", "independent_review_ready", "owner_decision_state", "evidence_fresh",
    "failure_codes", "runtime_activation_authorized", "runtime_configuration_authorized",
    "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized",
    "provider_transmission_authorized", "alert_publication_authorized",
    "kill_switch_activation_authorized", "publication_authorized", "ready",
)
_AUDIT = (
    "policy_id", "boundary_bundle_id", "operator_attestation_id", "review_evidence_id",
    "owner_decision_id", "provider_id", "routing_level", "exact_provider_model_id",
    "locked_budget_target_id", "operator_id", "reviewer_id", "owner_decision_state",
    "routing_ready", "budget_ready", "hard_cap_ready", "internal_soft_alert_ready",
    "pricing_ready", "reservation_ready", "usage_ledger_ready", "runtime_guard_ready",
    "alert_intent_ready", "kill_switch_intent_ready", "manual_recovery_ready", "evidence_fresh",
    "failure_codes", "runtime_activation_authorized", "runtime_configuration_authorized",
    "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized",
    "provider_transmission_authorized", "alert_publication_authorized",
    "kill_switch_activation_authorized", "publication_authorized", "evidence_ready",
)
_FAILURES = {
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "ACTIVATION_READINESS_POLICY_ID_MISMATCH",
    "RUNTIME_GUARD_POLICY_ID_MISMATCH", "BUDGET_POLICY_ID_MISMATCH", "PRICING_POLICY_ID_MISMATCH",
    "RESERVATION_POLICY_ID_MISMATCH", "USAGE_LEDGER_POLICY_ID_MISMATCH", "ALERT_POLICY_ID_MISMATCH",
    "BOUNDARY_EVIDENCE_REQUIRED", "BOUNDARY_EVIDENCE_ID_MISMATCH", "PROVIDER_ID_MISMATCH",
    "ROUTING_LEVEL_MISMATCH", "EXACT_MODEL_ID_MISMATCH", "LOCKED_BUDGET_TARGET_MISMATCH",
    "PROVIDER_HARD_CAP_NOT_CONFIRMED", "INTERNAL_SOFT_ALERT_NOT_READY", "PRICING_NOT_REVALIDATED",
    "RESERVATION_NOT_READY", "USAGE_LEDGER_NOT_READY", "PRE_RESERVATION_GUARD_NOT_READY",
    "PRE_TRANSMISSION_REVALIDATION_NOT_READY", "STALE_USAGE_BLOCK_NOT_READY",
    "BUDGET_CHANGE_BLOCK_NOT_READY", "DAILY_LIMIT_BLOCK_NOT_READY", "MONTHLY_LIMIT_BLOCK_NOT_READY",
    "HARD_LIMIT_BLOCK_NOT_READY", "ALERT_INTENT_NOT_READY", "KILL_SWITCH_INTENT_NOT_READY",
    "AUTOMATIC_RETRY_NOT_AUTHORIZED", "MANUAL_RECOVERY_NOT_READY", "OPERATOR_ATTESTATION_REQUIRED",
    "OPERATOR_ATTESTATION_INCOMPLETE", "REVIEWER_EVIDENCE_REQUIRED", "REVIEWER_EVIDENCE_INCOMPLETE",
    "OPERATOR_REVIEWER_COLLISION", "OWNER_DECISION_RECORD_REQUIRED", "OWNER_ACTIVATION_NOT_GRANTED",
    "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE", "EVIDENCE_EXPIRED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "RUNTIME_CONFIGURATION_NOT_AUTHORIZED",
    "CREDENTIAL_ONBOARDING_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "ALERT_PUBLICATION_NOT_AUTHORIZED",
    "KILL_SWITCH_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_PROVIDER_RESPONSE_EXPOSURE_DETECTED",
    "RAW_BILLING_DATA_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


def _policy(**overrides: object) -> BudgetGuardReadinessEvidencePolicyV1:
    values = {name: True for name in _POLICY if name.startswith("require_")}
    values.update({
        "policy_id": "readiness-evidence-policy-v1", "policy_version": "v1",
        "deployment_environment": "CONTROLLED_PRODUCTION", "required_activation_readiness_policy_id": "activation-policy-v1",
        "required_runtime_guard_policy_id": "budget-guard-runtime-policy-v1", "required_budget_policy_id": "budget-policy-v1",
        "required_pricing_policy_id": "pricing-policy-v1", "required_reservation_policy_id": "reservation-policy-v1",
        "required_usage_ledger_policy_id": "ledger-policy-v1", "required_alert_policy_id": "alert-policy-v1",
        "runtime_activation_authorized": False, "runtime_configuration_authorized": False,
        "credential_onboarding_authorized": False, "credential_loading_authorized": False,
        "network_authorized": False, "provider_transmission_authorized": False,
        "alert_publication_authorized": False, "kill_switch_activation_authorized": False,
        "publication_authorized": False, "fail_closed": True,
    })
    values.update(overrides)
    return BudgetGuardReadinessEvidencePolicyV1(**values)


def _bundle(**overrides: object) -> BudgetGuardBoundaryEvidenceBundleV1:
    values = {name: True for name in _BUNDLE if name.endswith("ready") or name.endswith("confirmed") or name.endswith("disabled") or name.endswith("complete")}
    values.update({
        "boundary_bundle_id": "bundle-v1", "policy_id": "readiness-evidence-policy-v1",
        "activation_readiness_policy_id": "activation-policy-v1", "runtime_guard_policy_id": "budget-guard-runtime-policy-v1",
        "internal_alert_policy_id": "alert-policy-v1", "budget_policy_id": "budget-policy-v1",
        "pricing_policy_id": "pricing-policy-v1", "reservation_policy_id": "reservation-policy-v1",
        "usage_ledger_policy_id": "ledger-policy-v1", "provider_budget_configuration_id": "budget-config-v1",
        "provider_hard_cap_confirmation_id": "hard-cap-v1", "provider_id": "DEEPSEEK", "routing_level": "L0",
        "exact_provider_model_id": "deepseek-v4-pro", "locked_budget_target_id": "budget-target-v1",
        "internal_soft_alert_substitution_id": "internal-soft-alert-v1", "verified_at": _AT, "evidence_expires_at": _UNTIL,
    })
    values.update(overrides)
    return BudgetGuardBoundaryEvidenceBundleV1(**values)


def _operator(**overrides: object) -> BudgetGuardOperatorEvidenceAttestationV1:
    values = {name: True for name in _OPERATOR if name.endswith("confirmed") or name.endswith("disabled") or name.endswith("complete") or name.endswith("ready")}
    values.update({
        "operator_attestation_id": "operator-attestation-v1", "policy_id": "readiness-evidence-policy-v1",
        "boundary_bundle_id": "bundle-v1", "operator_id": "operator-v1", "operator_role": "BUDGET_GUARD_OPERATOR",
        "provider_id": "DEEPSEEK", "routing_level": "L0", "exact_provider_model_id": "deepseek-v4-pro",
        "locked_budget_target_id": "budget-target-v1", "verified_at": _AT, "evidence_expires_at": _UNTIL,
    })
    values.update(overrides)
    return BudgetGuardOperatorEvidenceAttestationV1(**values)


def _review(**overrides: object) -> BudgetGuardIndependentReviewEvidenceV1:
    values = {name: True for name in _REVIEW if name.endswith("confirmed") or name.endswith("disabled") or name.endswith("complete") or name.endswith("ready")}
    values.update({
        "review_evidence_id": "review-v1", "policy_id": "readiness-evidence-policy-v1", "boundary_bundle_id": "bundle-v1",
        "operator_attestation_id": "operator-attestation-v1", "reviewer_id": "reviewer-v1",
        "reviewer_role": "INDEPENDENT_REVIEWER", "operator_id": "operator-v1", "provider_id": "DEEPSEEK",
        "routing_level": "L0", "exact_provider_model_id": "deepseek-v4-pro", "locked_budget_target_id": "budget-target-v1",
        "approved": True, "reviewed_at": _AT, "evidence_expires_at": _UNTIL,
    })
    values.update(overrides)
    return BudgetGuardIndependentReviewEvidenceV1(**values)


def _owner(**overrides: object) -> BudgetGuardOwnerActivationDecisionRecordV1:
    values = {
        "owner_decision_id": "owner-decision-v1", "policy_id": "readiness-evidence-policy-v1", "boundary_bundle_id": "bundle-v1",
        "readiness_evidence_accepted": True, "runtime_activation_decision_state": "PENDING_SEPARATE_OWNER_DECISION",
        "runtime_activation_approved": False, "credential_onboarding_state": "SEPARATELY_PENDING", "activation_scope": "NONE",
        "owner_id": "owner-v1", "decided_at": _AT, "evidence_expires_at": _UNTIL,
        "rationale_classification": "READINESS_EVIDENCE_ACCEPTED_ONLY",
        "runtime_activation_authorized": False, "runtime_configuration_authorized": False,
        "credential_onboarding_authorized": False, "credential_loading_authorized": False, "network_authorized": False,
        "provider_transmission_authorized": False, "alert_publication_authorized": False,
        "kill_switch_activation_authorized": False, "publication_authorized": False,
    }
    values.update(overrides)
    return BudgetGuardOwnerActivationDecisionRecordV1(**values)


def _frozen(value: object) -> None:
    assert is_dataclass(value) and type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def _assert_no_authority(decision: BudgetGuardReadinessEvidenceDecisionV1) -> None:
    assert (
        decision.runtime_activation_authorized, decision.runtime_configuration_authorized,
        decision.credential_onboarding_authorized, decision.credential_loading_authorized,
        decision.network_authorized, decision.provider_transmission_authorized,
        decision.alert_publication_authorized, decision.kill_switch_activation_authorized,
        decision.publication_authorized,
    ) == (False,) * 9


def test_public_api_is_immutable_complete_and_fail_closed() -> None:
    assert tuple(field.name for field in fields(BudgetGuardReadinessEvidencePolicyV1)) == _POLICY
    assert tuple(field.name for field in fields(BudgetGuardBoundaryEvidenceBundleV1)) == _BUNDLE
    assert tuple(field.name for field in fields(BudgetGuardOperatorEvidenceAttestationV1)) == _OPERATOR
    assert tuple(field.name for field in fields(BudgetGuardIndependentReviewEvidenceV1)) == _REVIEW
    assert tuple(field.name for field in fields(BudgetGuardOwnerActivationDecisionRecordV1)) == _OWNER
    assert tuple(field.name for field in fields(BudgetGuardReadinessEvidenceDecisionV1)) == _DECISION
    assert tuple(field.name for field in fields(BudgetGuardReadinessEvidenceAuditV1)) == _AUDIT
    assert tuple(field.name for field in fields(BudgetGuardReadinessEvidenceFailureV1)) == ("failure_code", "safe_message", "retryable")
    for value in (_policy(), _bundle(), _operator(), _review(), _owner()):
        _frozen(value)
    defaults = BudgetGuardReadinessEvidencePolicyV1()
    assert defaults.fail_closed is True
    assert not any((defaults.runtime_activation_authorized, defaults.runtime_configuration_authorized, defaults.credential_onboarding_authorized, defaults.credential_loading_authorized, defaults.network_authorized, defaults.provider_transmission_authorized, defaults.alert_publication_authorized, defaults.kill_switch_activation_authorized, defaults.publication_authorized))
    with pytest.raises(FrozenInstanceError):
        _policy().policy_id = "other"  # type: ignore[misc]


def test_locked_routes_native_exception_and_exact_budget_limits_are_preserved() -> None:
    assert _ROUTES[0] == ("DEEPSEEK", "L0", "DEEPSEEK_V4_PRO", "deepseek-v4-pro")
    assert _ROUTES[1:] == (("ANTHROPIC", "L1", "CLAUDE_SONNET_5", "claude-sonnet-5"), ("ANTHROPIC", "L2", "CLAUDE_OPUS_4_8", "claude-opus-4-8"))
    assert _BUDGETS == (("DEEPSEEK", True, Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00")), ("ANTHROPIC", True, Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00")))


def test_complete_evidence_is_ready_only_for_a_separate_owner_decision() -> None:
    policy, bundle, operator, review, owner = _policy(), _bundle(), _operator(), _review(), _owner()
    decision = evaluate_budget_guard_readiness_evidence_v1(policy, bundle, operator, review, owner, _AT)
    audit = build_budget_guard_readiness_evidence_audit_v1(policy, bundle, operator, review, owner, decision)
    assert decision.ready is True and decision.failure_codes == ()
    assert decision.owner_decision_state == "PENDING_SEPARATE_OWNER_DECISION"
    assert owner.runtime_activation_approved is False
    _assert_no_authority(decision)
    _frozen(audit)


@pytest.mark.parametrize(
    ("bundle_changes", "expected_failure"),
    (({"provider_hard_cap_confirmation_id": ""}, "PROVIDER_HARD_CAP_NOT_CONFIRMED"), ({"pre_transmission_revalidation_ready": False}, "PRE_TRANSMISSION_REVALIDATION_NOT_READY"), ({"automatic_retry_disabled": False}, "AUTOMATIC_RETRY_NOT_AUTHORIZED"), ({"manual_recovery_ready": False}, "MANUAL_RECOVERY_NOT_READY")),
)
def test_boundary_failure_categories_are_deterministic_and_fail_closed(bundle_changes: dict[str, object], expected_failure: str) -> None:
    decision = evaluate_budget_guard_readiness_evidence_v1(_policy(), _bundle(**bundle_changes), _operator(), _review(), _owner(), _AT)
    assert decision.ready is False and expected_failure in decision.failure_codes
    assert tuple(decision.failure_codes) == tuple(sorted(decision.failure_codes))
    assert set(decision.failure_codes).issubset(_FAILURES)
    _assert_no_authority(decision)


def test_operator_reviewer_owner_and_freshness_gates_remain_fail_closed() -> None:
    missing_owner = evaluate_budget_guard_readiness_evidence_v1(_policy(), _bundle(), _operator(), _review(), _owner(owner_decision_id=""), _AT)
    collision = evaluate_budget_guard_readiness_evidence_v1(_policy(), _bundle(), _operator(), _review(reviewer_id="operator-v1"), _owner(), _AT)
    expired = evaluate_budget_guard_readiness_evidence_v1(_policy(), _bundle(verified_at=_STALE, evidence_expires_at=_STALE), _operator(verified_at=_STALE, evidence_expires_at=_STALE), _review(reviewed_at=_STALE, evidence_expires_at=_STALE), _owner(decided_at=_STALE, evidence_expires_at=_STALE), _AT)
    future = evaluate_budget_guard_readiness_evidence_v1(_policy(), _bundle(verified_at=_FUTURE), _operator(verified_at=_FUTURE), _review(reviewed_at=_FUTURE), _owner(decided_at=_FUTURE), _AT)
    assert "OWNER_DECISION_RECORD_REQUIRED" in missing_owner.failure_codes
    assert "OPERATOR_REVIEWER_COLLISION" in collision.failure_codes
    assert "EVIDENCE_EXPIRED" in expired.failure_codes
    assert "EVIDENCE_FROM_FUTURE" in future.failure_codes
    for decision in (missing_owner, collision, expired, future):
        assert decision.ready is False
        _assert_no_authority(decision)


def test_true_caller_authorities_never_grant_activation_and_audit_is_redacted() -> None:
    policy = _policy(runtime_activation_authorized=True, runtime_configuration_authorized=True, credential_onboarding_authorized=True, credential_loading_authorized=True, network_authorized=True, provider_transmission_authorized=True, alert_publication_authorized=True, kill_switch_activation_authorized=True, publication_authorized=True)
    decision = evaluate_budget_guard_readiness_evidence_v1(policy, _bundle(), _operator(), _review(), _owner(), _AT)
    assert {"RUNTIME_ACTIVATION_NOT_AUTHORIZED", "CREDENTIAL_ONBOARDING_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"}.issubset(decision.failure_codes)
    _assert_no_authority(decision)
    audit = build_budget_guard_readiness_evidence_audit_v1(_policy(), _bundle(), _operator(), _review(), _owner(), evaluate_budget_guard_readiness_evidence_v1(_policy(), _bundle(), _operator(), _review(), _owner(), _AT))
    assert not {"api_key", "credential", "authorization", "cookie", "account", "response", "exception", "trace"}.intersection(field.name for field in fields(BudgetGuardReadinessEvidenceAuditV1))
    assert audit.evidence_ready is True
