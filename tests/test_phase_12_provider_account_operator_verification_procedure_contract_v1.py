"""RED contract for redacted manual provider-account verification metadata."""

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone

import pytest

from engine.phase_12_provider_account_operator_verification_procedure_contract_v1 import (
    ProviderAccountOperatorAttestationV1,
    ProviderAccountReviewerApprovalV1,
    ProviderAccountVerificationAuditEvidenceV1,
    ProviderAccountVerificationChecklistV1,
    ProviderAccountVerificationDecisionV1,
    ProviderAccountVerificationFailureV1,
    ProviderAccountVerificationPolicyV1,
    build_provider_account_verification_audit_evidence_v1,
    evaluate_provider_account_verification_v1,
)


_AT = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
_CODES = {
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "PROVIDER_NOT_ALLOWED", "REQUIRED_PROVIDER_MISSING", "REQUIRED_MODEL_ID_MISSING", "CHECKLIST_ID_EMPTY", "CHECKLIST_NOT_READY", "ATTESTATION_ID_EMPTY", "OPERATOR_ID_EMPTY", "OPERATOR_ROLE_EMPTY", "REVIEWER_ID_EMPTY", "REVIEWER_ROLE_EMPTY", "OPERATOR_REVIEWER_MUST_BE_DISTINCT", "VERIFICATION_METHOD_INVALID", "ACCOUNT_ACTIVE_NOT_CONFIRMED", "MODEL_ENTITLEMENTS_NOT_CONFIRMED", "REQUIRED_MODEL_ENTITLEMENT_MISSING", "BILLING_NOT_CONFIRMED", "HARD_SPEND_LIMIT_NOT_CONFIRMED", "SOFT_ALERT_NOT_CONFIRMED", "QUOTA_CLASSIFICATION_NOT_CONFIRMED", "RATE_LIMIT_CLASSIFICATION_NOT_CONFIRMED", "REGION_COMPATIBILITY_NOT_CONFIRMED", "ENDPOINT_ACCESS_NOT_CONFIRMED", "TERMS_NOT_ACKNOWLEDGED", "ACCEPTABLE_USE_NOT_ACKNOWLEDGED", "CONSOLE_REVOCATION_NOT_CONFIRMED", "ACCOUNT_SUSPENSION_NOT_CONFIRMED", "INCIDENT_CONTACT_NOT_CONFIRMED", "SECRET_CAPTURE_DETECTED", "RAW_ACCOUNT_IDENTITY_CAPTURE_DETECTED", "SCREENSHOT_RETENTION_DETECTED", "BALANCE_CAPTURE_DETECTED", "INVOICE_CAPTURE_DETECTED", "PAYMENT_DATA_CAPTURE_DETECTED", "COOKIE_CAPTURE_DETECTED", "AUTHORIZATION_HEADER_CAPTURE_DETECTED", "APPROVAL_ID_EMPTY", "REVIEW_IDENTITY_MISMATCH", "REVIEWER_APPROVAL_REQUIRED", "VERIFICATION_TIMESTAMP_REQUIRED", "EVIDENCE_FROM_FUTURE", "EVIDENCE_EXPIRED", "ACCOUNT_INSPECTION_NOT_AUTHORIZED", "ACCOUNT_VERIFICATION_RECORDING_NOT_AUTHORIZED", "CREDENTIAL_ONBOARDING_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


def _names(record: type) -> tuple[str, ...]:
    return tuple(item.name for item in fields(record))


def _policy() -> ProviderAccountVerificationPolicyV1:
    return ProviderAccountVerificationPolicyV1(
        policy_id="operator-verification-policy-v1", policy_version="v1", deployment_environment="CONTROLLED_PRODUCTION",
        allowed_provider_ids=("DEEPSEEK", "ANTHROPIC"), required_provider_ids=("DEEPSEEK", "ANTHROPIC"),
        required_exact_model_ids=("deepseek-v4-pro", "claude-sonnet-5", "claude-opus-4-8"), maximum_evidence_age_days=7,
    )


def _checklist(provider: str, **changes: object) -> ProviderAccountVerificationChecklistV1:
    models = ("deepseek-v4-pro",) if provider == "DEEPSEEK" else ("claude-sonnet-5", "claude-opus-4-8")
    values = dict(
        checklist_id=f"checklist-{provider.lower()}", policy_id="operator-verification-policy-v1", provider_id=provider,
        required_exact_model_ids=models, confirm_account_active=True, confirm_model_entitlements=True,
        confirm_billing_enabled=True, confirm_hard_spend_limit=True, confirm_soft_alert_threshold=True,
        confirm_quota_classification=True, confirm_rate_limit_classification=True, confirm_region_compatibility=True,
        confirm_endpoint_access=True, confirm_terms_acknowledged=True, confirm_acceptable_use_acknowledged=True,
        confirm_console_revocation_procedure=True, confirm_account_suspension_procedure=True, confirm_incident_contact=True,
        prohibit_secret_capture=True, prohibit_account_identity_capture=True, prohibit_screenshot_retention=True,
        prohibit_balance_capture=True, prohibit_invoice_capture=True, prohibit_payment_data_capture=True,
        prohibit_cookie_capture=True, prohibit_authorization_header_capture=True, checklist_ready=True,
    )
    values.update(changes)
    return ProviderAccountVerificationChecklistV1(**values)


def _attestation(checklist: ProviderAccountVerificationChecklistV1, **changes: object) -> ProviderAccountOperatorAttestationV1:
    values = dict(
        attestation_id=f"attestation-{checklist.provider_id.lower()}", checklist_id=checklist.checklist_id,
        policy_id="operator-verification-policy-v1", provider_id=checklist.provider_id,
        operator_id=f"operator-{checklist.provider_id.lower()}", operator_role="VERIFICATION_OPERATOR",
        verification_method_classification="MANUAL_PROVIDER_CONSOLE_REVIEW", account_active_confirmed=False,
        model_entitlements_confirmed=False, entitled_exact_model_ids=checklist.required_exact_model_ids,
        billing_enabled_confirmed=False, hard_spend_limit_confirmed=False, soft_alert_threshold_confirmed=False,
        quota_classification_confirmed=False, rate_limit_classification_confirmed=False,
        region_compatibility_confirmed=False, endpoint_access_confirmed=False, terms_acknowledged=False,
        acceptable_use_acknowledged=False, console_revocation_confirmed=False, account_suspension_confirmed=False,
        incident_contact_confirmed=False, no_secret_captured=True, no_account_identity_captured=True,
        no_screenshot_retained=True, no_balance_captured=True, no_invoice_captured=True,
        no_payment_data_captured=True, no_cookie_captured=True, no_authorization_header_captured=True,
        verified_at=_AT, evidence_expires_at=_UNTIL, attestation_ready=False,
    )
    values.update(changes)
    return ProviderAccountOperatorAttestationV1(**values)


def _approval(attestation: ProviderAccountOperatorAttestationV1, **changes: object) -> ProviderAccountReviewerApprovalV1:
    values = dict(
        approval_id=f"approval-{attestation.provider_id.lower()}", attestation_id=attestation.attestation_id,
        checklist_id=attestation.checklist_id, policy_id="operator-verification-policy-v1", provider_id=attestation.provider_id,
        reviewer_id=f"reviewer-{attestation.provider_id.lower()}", reviewer_role="INDEPENDENT_REVIEWER",
        operator_reviewer_distinct=True, required_models_confirmed=False, billing_controls_confirmed=False,
        quota_and_rate_limit_classifications_confirmed=False, operational_procedures_confirmed=False,
        prohibited_evidence_absent=True, attestation_identity_verified=True, approved=False,
        reviewed_at=_AT, evidence_expires_at=_UNTIL, approval_ready=False,
    )
    values.update(changes)
    return ProviderAccountReviewerApprovalV1(**values)


def _evaluate(**changes: object) -> tuple[object, ...]:
    checklists = (_checklist("DEEPSEEK"), _checklist("ANTHROPIC"))
    attestations = tuple(_attestation(item) for item in checklists)
    approvals = tuple(_approval(item) for item in attestations)
    values = dict(policy=_policy(), checklists=checklists, attestations=attestations, approvals=approvals, evaluated_at=_AT)
    values.update(changes)
    decision = evaluate_provider_account_verification_v1(**values)
    return values["policy"], checklists, attestations, approvals, decision


def test_public_records_are_immutable_redacted_and_fail_closed_by_default() -> None:
    expected = {
        ProviderAccountVerificationPolicyV1: ("policy_id", "policy_version", "deployment_environment", "allowed_provider_ids", "required_provider_ids", "required_exact_model_ids", "require_manual_console_verification", "require_operator_identity", "require_reviewer_identity", "require_distinct_operator_and_reviewer", "require_provider_account_active", "require_model_entitlement_confirmation", "require_billing_enabled_confirmation", "require_hard_spend_limit_confirmation", "require_soft_alert_confirmation", "require_quota_classification", "require_rate_limit_classification", "require_region_compatibility_confirmation", "require_endpoint_access_confirmation", "require_terms_acknowledgement", "require_provider_console_revocation_confirmation", "require_account_suspension_confirmation", "require_incident_contact_confirmation", "require_no_secret_capture", "require_no_raw_account_identity", "require_no_screenshot_retention", "require_no_balance_capture", "require_no_invoice_capture", "require_no_cookie_capture", "require_evidence_freshness", "maximum_evidence_age_days", "account_inspection_authorized", "account_verification_recording_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized", "fail_closed"),
        ProviderAccountVerificationChecklistV1: ("checklist_id", "policy_id", "provider_id", "required_exact_model_ids", "confirm_account_active", "confirm_model_entitlements", "confirm_billing_enabled", "confirm_hard_spend_limit", "confirm_soft_alert_threshold", "confirm_quota_classification", "confirm_rate_limit_classification", "confirm_region_compatibility", "confirm_endpoint_access", "confirm_terms_acknowledged", "confirm_acceptable_use_acknowledged", "confirm_console_revocation_procedure", "confirm_account_suspension_procedure", "confirm_incident_contact", "prohibit_secret_capture", "prohibit_account_identity_capture", "prohibit_screenshot_retention", "prohibit_balance_capture", "prohibit_invoice_capture", "prohibit_payment_data_capture", "prohibit_cookie_capture", "prohibit_authorization_header_capture", "checklist_ready"),
        ProviderAccountOperatorAttestationV1: ("attestation_id", "checklist_id", "policy_id", "provider_id", "operator_id", "operator_role", "verification_method_classification", "account_active_confirmed", "model_entitlements_confirmed", "entitled_exact_model_ids", "billing_enabled_confirmed", "hard_spend_limit_confirmed", "soft_alert_threshold_confirmed", "quota_classification_confirmed", "rate_limit_classification_confirmed", "region_compatibility_confirmed", "endpoint_access_confirmed", "terms_acknowledged", "acceptable_use_acknowledged", "console_revocation_confirmed", "account_suspension_confirmed", "incident_contact_confirmed", "no_secret_captured", "no_account_identity_captured", "no_screenshot_retained", "no_balance_captured", "no_invoice_captured", "no_payment_data_captured", "no_cookie_captured", "no_authorization_header_captured", "verified_at", "evidence_expires_at", "attestation_ready"),
        ProviderAccountReviewerApprovalV1: ("approval_id", "attestation_id", "checklist_id", "policy_id", "provider_id", "reviewer_id", "reviewer_role", "operator_reviewer_distinct", "required_models_confirmed", "billing_controls_confirmed", "quota_and_rate_limit_classifications_confirmed", "operational_procedures_confirmed", "prohibited_evidence_absent", "attestation_identity_verified", "approved", "reviewed_at", "evidence_expires_at", "approval_ready"),
        ProviderAccountVerificationDecisionV1: ("policy_id", "deployment_environment", "ready", "failure_codes", "DeepSeek_verification_procedure_ready", "Anthropic_verification_procedure_ready", "operator_attestations_ready", "reviewer_approvals_ready", "model_entitlements_confirmed", "billing_controls_confirmed", "quota_and_rate_limits_confirmed", "region_and_endpoint_confirmed", "terms_confirmed", "revocation_and_suspension_confirmed", "incident_contacts_confirmed", "prohibited_evidence_absent", "evidence_fresh", "account_inspection_authorized", "account_verification_recording_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized"),
        ProviderAccountVerificationAuditEvidenceV1: ("policy_id", "deployment_environment", "provider_ids", "checklist_ids", "operator_roles", "reviewer_roles", "model_entitlements_confirmed", "billing_controls_confirmed", "quota_and_rate_limits_confirmed", "region_and_endpoint_confirmed", "terms_confirmed", "revocation_and_suspension_confirmed", "incident_contacts_confirmed", "prohibited_evidence_absent", "evidence_fresh", "failure_codes", "account_inspection_authorized", "account_verification_recording_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized"),
    }
    for record, names in expected.items():
        assert is_dataclass(record) and _names(record) == names
        assert getattr(record, "__dataclass_params__").frozen is True and hasattr(record, "__slots__")
    assert _names(ProviderAccountVerificationFailureV1) == ("failure_code", "safe_message", "retryable")
    defaults = ProviderAccountVerificationPolicyV1()
    assert defaults.allowed_provider_ids == defaults.required_provider_ids == defaults.required_exact_model_ids == ()
    assert defaults.fail_closed is True
    assert not any((defaults.account_inspection_authorized, defaults.account_verification_recording_authorized, defaults.credential_onboarding_authorized, defaults.credential_loading_authorized, defaults.network_authorized, defaults.provider_transmission_authorized))


def test_locked_model_bindings_remain_explicit_while_unexecuted_attestations_fail_closed() -> None:
    _policy_value, checklists, attestations, _approvals, decision = _evaluate()
    assert tuple((item.provider_id, item.required_exact_model_ids) for item in checklists) == (("DEEPSEEK", ("deepseek-v4-pro",)), ("ANTHROPIC", ("claude-sonnet-5", "claude-opus-4-8")))
    assert tuple(item.no_secret_captured for item in attestations) == (True, True)
    assert decision.ready is False
    assert {"ACCOUNT_ACTIVE_NOT_CONFIRMED", "BILLING_NOT_CONFIRMED", "MODEL_ENTITLEMENTS_NOT_CONFIRMED", "REVIEWER_APPROVAL_REQUIRED"} <= set(decision.failure_codes)
    assert tuple(sorted(decision.failure_codes)) == decision.failure_codes
    assert set(decision.failure_codes) <= _CODES
    assert not any((decision.account_inspection_authorized, decision.account_verification_recording_authorized, decision.credential_onboarding_authorized, decision.credential_loading_authorized, decision.network_authorized, decision.provider_transmission_authorized))


def test_missing_entitlement_captured_prohibited_evidence_and_nonindependent_review_fail_closed() -> None:
    policy, checklists, attestations, approvals, _decision = _evaluate()
    unsafe = _attestation(checklists[1], entitled_exact_model_ids=("claude-sonnet-5",), model_entitlements_confirmed=True, no_cookie_captured=False)
    nonindependent = _approval(unsafe, reviewer_id=unsafe.operator_id, operator_reviewer_distinct=False)
    decision = evaluate_provider_account_verification_v1(policy, checklists, (attestations[0], unsafe), (approvals[0], nonindependent), _AT)
    assert {"REQUIRED_MODEL_ENTITLEMENT_MISSING", "COOKIE_CAPTURE_DETECTED", "OPERATOR_REVIEWER_MUST_BE_DISTINCT"} <= set(decision.failure_codes)
    assert tuple(sorted(decision.failure_codes)) == decision.failure_codes
    assert decision.ready is False


def test_audit_is_redacted_immutable_and_rejects_cross_provider_identity() -> None:
    policy, checklists, attestations, approvals, decision = _evaluate()
    audit = build_provider_account_verification_audit_evidence_v1(policy, checklists, attestations, approvals, decision)
    assert audit.provider_ids == ("DEEPSEEK", "ANTHROPIC")
    assert audit.failure_codes == decision.failure_codes
    assert not any((audit.account_inspection_authorized, audit.account_verification_recording_authorized, audit.credential_onboarding_authorized, audit.credential_loading_authorized, audit.network_authorized, audit.provider_transmission_authorized))
    with pytest.raises(ValueError):
        build_provider_account_verification_audit_evidence_v1(policy, (_checklist("ANTHROPIC"), checklists[1]), attestations, approvals, decision)
