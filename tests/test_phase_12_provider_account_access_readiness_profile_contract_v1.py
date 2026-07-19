"""RED contract for redacted provider-account readiness metadata only."""

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone

import pytest

from engine.phase_12_provider_account_access_readiness_profile_contract_v1 import (
    ProviderAccountAccessFailureV1,
    ProviderAccountProfileV1,
    ProviderAccountReadinessAuditEvidenceV1,
    ProviderAccountReadinessDecisionV1,
    ProviderAccountReadinessPolicyV1,
    ProviderBillingQuotaEvidenceV1,
    ProviderPermissionScopeEvidenceV1,
    build_provider_account_readiness_audit_evidence_v1,
    evaluate_provider_account_readiness_v1,
)


_AT = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
_CODES = {
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "PROVIDER_NOT_ALLOWED", "REQUIRED_PROVIDER_MISSING", "REQUIRED_MODEL_ID_MISSING", "ACCOUNT_PROFILE_ID_EMPTY", "ACCOUNT_IDENTITY_REFERENCE_EMPTY", "ACCOUNT_IDENTITY_NOT_REDACTED", "ACCOUNT_OWNER_REQUIRED", "OPERATIONAL_OWNER_REQUIRED", "BILLING_OWNER_REQUIRED", "SECURITY_OWNER_REQUIRED", "ACCOUNT_NOT_VERIFIED", "ACCOUNT_NOT_ACTIVE", "BILLING_NOT_ENABLED", "SPEND_CONTROL_NOT_READY", "HARD_SPEND_LIMIT_REQUIRED", "SOFT_ALERT_THRESHOLD_REQUIRED", "PERMISSION_EVIDENCE_ID_EMPTY", "PERMISSION_SCOPE_REQUIRED", "LEAST_PRIVILEGE_REQUIRED", "MODEL_ENTITLEMENT_NOT_VERIFIED", "REQUIRED_MODEL_ENTITLEMENT_MISSING", "EXCESSIVE_PERMISSION_DETECTED", "BILLING_QUOTA_EVIDENCE_ID_EMPTY", "QUOTA_EVIDENCE_REQUIRED", "RATE_LIMIT_EVIDENCE_REQUIRED", "NUMERIC_LIMIT_INVALID", "REGION_COMPATIBILITY_NOT_PROVEN", "ENDPOINT_ACCESS_NOT_PROVEN", "TERMS_ACKNOWLEDGEMENT_REQUIRED", "ACCEPTABLE_USE_ACKNOWLEDGEMENT_REQUIRED", "PROVIDER_CONSOLE_REVOCATION_NOT_READY", "ACCOUNT_SUSPENSION_PROCEDURE_NOT_READY", "INCIDENT_CONTACT_NOT_READY", "SEPARATION_OF_DUTIES_REQUIRED", "VERIFICATION_TIMESTAMP_REQUIRED", "EVIDENCE_FROM_FUTURE", "EVIDENCE_EXPIRED", "SECRET_EVIDENCE_FORBIDDEN", "RAW_ACCOUNT_DATA_EXPOSURE_DETECTED", "RAW_BILLING_DATA_EXPOSURE_DETECTED", "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED", "ACCOUNT_VERIFICATION_NOT_AUTHORIZED", "CREDENTIAL_ONBOARDING_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
}


def _names(record: type) -> tuple[str, ...]:
    return tuple(item.name for item in fields(record))


def _policy() -> ProviderAccountReadinessPolicyV1:
    return ProviderAccountReadinessPolicyV1(
        policy_id="account-readiness-policy-v1", policy_version="v1", deployment_environment="CONTROLLED_PRODUCTION",
        allowed_provider_ids=("DEEPSEEK", "ANTHROPIC"), required_provider_ids=("DEEPSEEK", "ANTHROPIC"),
        required_exact_model_ids=("deepseek-v4-pro", "claude-sonnet-5", "claude-opus-4-8"),
        require_account_identity=True, require_account_owner=True, require_account_verified=True, require_billing_enabled=True,
        require_spend_control=True, require_permission_scope=True, require_model_entitlement=True, require_quota_evidence=True,
        require_rate_limit_evidence=True, require_region_compatibility=True, require_endpoint_access_evidence=True,
        require_terms_acknowledgement=True, require_acceptable_use_acknowledgement=True,
        require_provider_console_revocation=True, require_account_suspension_procedure=True, require_incident_contact=True,
        require_separation_of_duties=True, require_evidence_freshness=True, maximum_evidence_age_days=7,
        require_no_secret_evidence=True,
    )


def _profile(provider: str, **changes: object) -> ProviderAccountProfileV1:
    values = dict(
        account_profile_id=f"profile-{provider.lower()}", policy_id="account-readiness-policy-v1", provider_id=provider,
        account_identity_reference=f"redacted-{provider.lower()}-account", account_identity_redacted=True,
        account_owner_role="ACCOUNT_OWNER", operational_owner_role="OPERATIONS_OWNER", billing_owner_role="BILLING_OWNER", security_owner_role="SECURITY_OWNER",
        account_verified=False, account_active=False, billing_enabled=False, spend_control_ready=False,
        region_classification="UNRESOLVED", region_compatible=False, endpoint_access_classification="UNRESOLVED", endpoint_access_ready=False,
        terms_acknowledged=False, acceptable_use_acknowledged=False,
        provider_console_revocation_procedure_id=f"revoke-{provider.lower()}", provider_console_revocation_ready=False,
        account_suspension_procedure_id=f"suspend-{provider.lower()}", account_suspension_ready=False,
        incident_contact_id=f"incident-{provider.lower()}", incident_contact_ready=False,
        separation_of_duties_ready=True, verified_at=_AT, evidence_expires_at=_UNTIL, profile_ready=False,
    )
    values.update(changes)
    return ProviderAccountProfileV1(**values)


def _permission(profile: ProviderAccountProfileV1, **changes: object) -> ProviderPermissionScopeEvidenceV1:
    required = ("deepseek-v4-pro",) if profile.provider_id == "DEEPSEEK" else ("claude-sonnet-5", "claude-opus-4-8")
    values = dict(
        permission_evidence_id=f"permission-{profile.provider_id.lower()}", account_profile_id=profile.account_profile_id,
        provider_id=profile.provider_id, permission_scope_id="LEAST_PRIVILEGE_SCOPE",
        permission_scope_classifications=("INFERENCE_ONLY",), least_privilege_confirmed=True,
        model_entitlement_ids=required, entitled_exact_model_ids=required, required_model_ids_present=True,
        model_list_source_classification="OPERATOR_ATTESTED", entitlement_verified=False,
        account_admin_permission_avoided=True, billing_admin_permission_avoided=True, unrelated_permissions_absent=True,
        verified_at=_AT, evidence_expires_at=_UNTIL, evidence_ready=False,
    )
    values.update(changes)
    return ProviderPermissionScopeEvidenceV1(**values)


def _billing(profile: ProviderAccountProfileV1, **changes: object) -> ProviderBillingQuotaEvidenceV1:
    values = dict(
        billing_quota_evidence_id=f"billing-{profile.provider_id.lower()}", account_profile_id=profile.account_profile_id,
        provider_id=profile.provider_id, billing_enabled=False, billing_currency="USD", hard_spend_limit_present=False,
        hard_spend_limit_reference_id="hard-limit", soft_alert_threshold_present=False, soft_alert_threshold_reference_id="soft-alert",
        provider_quota_classification="NOT_VERIFIED", rate_limit_classification="NOT_VERIFIED", concurrent_request_limit=0,
        requests_per_minute_limit=0, input_tokens_per_minute_limit=0, output_tokens_per_minute_limit=0,
        daily_usage_limit_reference_id="daily-limit", billing_failure_behavior="FAIL_CLOSED", quota_exhaustion_behavior="FAIL_CLOSED",
        no_automatic_retry_on_quota_failure=True, verified_at=_AT, evidence_expires_at=_UNTIL, evidence_ready=False,
    )
    values.update(changes)
    return ProviderBillingQuotaEvidenceV1(**values)


def _evaluate(**changes: object) -> tuple[object, ...]:
    profiles = (_profile("DEEPSEEK"), _profile("ANTHROPIC"))
    permissions = tuple(_permission(item) for item in profiles)
    billing = tuple(_billing(item) for item in profiles)
    values = dict(policy=_policy(), profiles=profiles, permission_evidence=permissions, billing_quota_evidence=billing, evaluated_at=_AT)
    values.update(changes)
    decision = evaluate_provider_account_readiness_v1(**values)
    return values["policy"], profiles, permissions, billing, decision


def test_public_records_are_immutable_redacted_and_fail_closed_by_default() -> None:
    expected = {
        ProviderAccountReadinessPolicyV1: ("policy_id", "policy_version", "deployment_environment", "allowed_provider_ids", "required_provider_ids", "required_exact_model_ids", "require_account_identity", "require_account_owner", "require_account_verified", "require_billing_enabled", "require_spend_control", "require_permission_scope", "require_model_entitlement", "require_quota_evidence", "require_rate_limit_evidence", "require_region_compatibility", "require_endpoint_access_evidence", "require_terms_acknowledgement", "require_acceptable_use_acknowledgement", "require_provider_console_revocation", "require_account_suspension_procedure", "require_incident_contact", "require_separation_of_duties", "require_evidence_freshness", "maximum_evidence_age_days", "require_no_secret_evidence", "account_verification_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized", "fail_closed"),
        ProviderAccountProfileV1: ("account_profile_id", "policy_id", "provider_id", "account_identity_reference", "account_identity_redacted", "account_owner_role", "operational_owner_role", "billing_owner_role", "security_owner_role", "account_verified", "account_active", "billing_enabled", "spend_control_ready", "region_classification", "region_compatible", "endpoint_access_classification", "endpoint_access_ready", "terms_acknowledged", "acceptable_use_acknowledged", "provider_console_revocation_procedure_id", "provider_console_revocation_ready", "account_suspension_procedure_id", "account_suspension_ready", "incident_contact_id", "incident_contact_ready", "separation_of_duties_ready", "verified_at", "evidence_expires_at", "profile_ready"),
        ProviderPermissionScopeEvidenceV1: ("permission_evidence_id", "account_profile_id", "provider_id", "permission_scope_id", "permission_scope_classifications", "least_privilege_confirmed", "model_entitlement_ids", "entitled_exact_model_ids", "required_model_ids_present", "model_list_source_classification", "entitlement_verified", "account_admin_permission_avoided", "billing_admin_permission_avoided", "unrelated_permissions_absent", "verified_at", "evidence_expires_at", "evidence_ready"),
        ProviderBillingQuotaEvidenceV1: ("billing_quota_evidence_id", "account_profile_id", "provider_id", "billing_enabled", "billing_currency", "hard_spend_limit_present", "hard_spend_limit_reference_id", "soft_alert_threshold_present", "soft_alert_threshold_reference_id", "provider_quota_classification", "rate_limit_classification", "concurrent_request_limit", "requests_per_minute_limit", "input_tokens_per_minute_limit", "output_tokens_per_minute_limit", "daily_usage_limit_reference_id", "billing_failure_behavior", "quota_exhaustion_behavior", "no_automatic_retry_on_quota_failure", "verified_at", "evidence_expires_at", "evidence_ready"),
        ProviderAccountReadinessDecisionV1: ("policy_id", "deployment_environment", "ready", "failure_codes", "DeepSeek_account_ready", "Anthropic_account_ready", "all_accounts_verified", "all_accounts_active", "billing_ready", "spend_controls_ready", "permissions_ready", "model_entitlements_ready", "quotas_ready", "rate_limits_ready", "region_ready", "endpoint_access_ready", "terms_ready", "revocation_ready", "suspension_procedure_ready", "incident_contact_ready", "separation_of_duties_ready", "evidence_fresh", "account_verification_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized"),
        ProviderAccountReadinessAuditEvidenceV1: ("policy_id", "deployment_environment", "provider_ids", "account_profile_ids", "account_owner_roles", "accounts_verified", "accounts_active", "permission_scopes_ready", "exact_model_entitlements_ready", "billing_ready", "spend_controls_ready", "quotas_ready", "rate_limits_ready", "region_ready", "endpoint_access_ready", "terms_ready", "revocation_ready", "suspension_procedure_ready", "incident_contact_ready", "evidence_fresh", "failure_codes", "account_verification_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized"),
    }
    for record, names in expected.items():
        assert is_dataclass(record) and _names(record) == names
        assert getattr(record, "__dataclass_params__").frozen is True and hasattr(record, "__slots__")
    assert _names(ProviderAccountAccessFailureV1) == ("failure_code", "safe_message", "retryable")
    defaults = ProviderAccountReadinessPolicyV1()
    assert defaults.allowed_provider_ids == defaults.required_provider_ids == defaults.required_exact_model_ids == ()
    assert defaults.fail_closed is True
    assert not any((defaults.account_verification_authorized, defaults.credential_onboarding_authorized, defaults.credential_loading_authorized, defaults.network_authorized, defaults.provider_transmission_authorized))


def test_locked_entitlements_remain_explicit_while_synthetic_unverified_evidence_blocks_readiness() -> None:
    _policy_value, profiles, permissions, _billing_values, decision = _evaluate()
    assert tuple((item.provider_id, item.entitled_exact_model_ids) for item in permissions) == (("DEEPSEEK", ("deepseek-v4-pro",)), ("ANTHROPIC", ("claude-sonnet-5", "claude-opus-4-8")))
    assert tuple(item.account_identity_redacted for item in profiles) == (True, True)
    assert decision.ready is False
    assert {"ACCOUNT_NOT_VERIFIED", "BILLING_NOT_ENABLED", "MODEL_ENTITLEMENT_NOT_VERIFIED", "QUOTA_EVIDENCE_REQUIRED"} <= set(decision.failure_codes)
    assert tuple(sorted(decision.failure_codes)) == decision.failure_codes
    assert set(decision.failure_codes) <= _CODES
    assert not any((decision.account_verification_authorized, decision.credential_onboarding_authorized, decision.credential_loading_authorized, decision.network_authorized, decision.provider_transmission_authorized))


def test_missing_model_entitlement_invalid_numeric_limit_and_excessive_permission_fail_closed() -> None:
    policy, profiles, permissions, billing, _decision = _evaluate()
    bad_permission = _permission(profiles[1], entitled_exact_model_ids=("claude-sonnet-5",), required_model_ids_present=False, account_admin_permission_avoided=False)
    bad_billing = _billing(profiles[0], concurrent_request_limit=True)
    decision = evaluate_provider_account_readiness_v1(policy, profiles, (permissions[0], bad_permission), (bad_billing, billing[1]), _AT)
    assert {"REQUIRED_MODEL_ENTITLEMENT_MISSING", "EXCESSIVE_PERMISSION_DETECTED", "NUMERIC_LIMIT_INVALID"} <= set(decision.failure_codes)
    assert tuple(sorted(decision.failure_codes)) == decision.failure_codes
    assert decision.ready is False


def test_audit_is_redacted_immutable_and_rejects_cross_provider_identity() -> None:
    policy, profiles, permissions, billing, decision = _evaluate()
    audit = build_provider_account_readiness_audit_evidence_v1(policy, profiles, permissions, billing, decision)
    assert audit.provider_ids == ("DEEPSEEK", "ANTHROPIC")
    assert audit.failure_codes == decision.failure_codes
    assert not any((audit.account_verification_authorized, audit.credential_onboarding_authorized, audit.credential_loading_authorized, audit.network_authorized, audit.provider_transmission_authorized))
    with pytest.raises(ValueError):
        build_provider_account_readiness_audit_evidence_v1(policy, (_profile("ANTHROPIC"), profiles[1]), permissions, billing, decision)
