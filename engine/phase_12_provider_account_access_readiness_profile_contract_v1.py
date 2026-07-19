"""Pure validation of redacted provider-account readiness metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProviderAccountReadinessPolicyV1:
    policy_id: str = ""
    policy_version: str = ""
    deployment_environment: str = ""
    allowed_provider_ids: tuple[str, ...] = ()
    required_provider_ids: tuple[str, ...] = ()
    required_exact_model_ids: tuple[str, ...] = ()
    require_account_identity: bool = True
    require_account_owner: bool = True
    require_account_verified: bool = True
    require_billing_enabled: bool = True
    require_spend_control: bool = True
    require_permission_scope: bool = True
    require_model_entitlement: bool = True
    require_quota_evidence: bool = True
    require_rate_limit_evidence: bool = True
    require_region_compatibility: bool = True
    require_endpoint_access_evidence: bool = True
    require_terms_acknowledgement: bool = True
    require_acceptable_use_acknowledgement: bool = True
    require_provider_console_revocation: bool = True
    require_account_suspension_procedure: bool = True
    require_incident_contact: bool = True
    require_separation_of_duties: bool = True
    require_evidence_freshness: bool = True
    maximum_evidence_age_days: int = 0
    require_no_secret_evidence: bool = True
    account_verification_authorized: bool = False
    credential_onboarding_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class ProviderAccountProfileV1:
    account_profile_id: str
    policy_id: str
    provider_id: str
    account_identity_reference: str
    account_identity_redacted: bool
    account_owner_role: str
    operational_owner_role: str
    billing_owner_role: str
    security_owner_role: str
    account_verified: bool
    account_active: bool
    billing_enabled: bool
    spend_control_ready: bool
    region_classification: str
    region_compatible: bool
    endpoint_access_classification: str
    endpoint_access_ready: bool
    terms_acknowledged: bool
    acceptable_use_acknowledged: bool
    provider_console_revocation_procedure_id: str
    provider_console_revocation_ready: bool
    account_suspension_procedure_id: str
    account_suspension_ready: bool
    incident_contact_id: str
    incident_contact_ready: bool
    separation_of_duties_ready: bool
    verified_at: datetime | None
    evidence_expires_at: datetime | None
    profile_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderPermissionScopeEvidenceV1:
    permission_evidence_id: str
    account_profile_id: str
    provider_id: str
    permission_scope_id: str
    permission_scope_classifications: tuple[str, ...]
    least_privilege_confirmed: bool
    model_entitlement_ids: tuple[str, ...]
    entitled_exact_model_ids: tuple[str, ...]
    required_model_ids_present: bool
    model_list_source_classification: str
    entitlement_verified: bool
    account_admin_permission_avoided: bool
    billing_admin_permission_avoided: bool
    unrelated_permissions_absent: bool
    verified_at: datetime | None
    evidence_expires_at: datetime | None
    evidence_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderBillingQuotaEvidenceV1:
    billing_quota_evidence_id: str
    account_profile_id: str
    provider_id: str
    billing_enabled: bool
    billing_currency: str
    hard_spend_limit_present: bool
    hard_spend_limit_reference_id: str
    soft_alert_threshold_present: bool
    soft_alert_threshold_reference_id: str
    provider_quota_classification: str
    rate_limit_classification: str
    concurrent_request_limit: int
    requests_per_minute_limit: int
    input_tokens_per_minute_limit: int
    output_tokens_per_minute_limit: int
    daily_usage_limit_reference_id: str
    billing_failure_behavior: str
    quota_exhaustion_behavior: str
    no_automatic_retry_on_quota_failure: bool
    verified_at: datetime | None
    evidence_expires_at: datetime | None
    evidence_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderAccountAccessFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class ProviderAccountReadinessDecisionV1:
    policy_id: str
    deployment_environment: str
    ready: bool
    failure_codes: tuple[str, ...]
    DeepSeek_account_ready: bool
    Anthropic_account_ready: bool
    all_accounts_verified: bool
    all_accounts_active: bool
    billing_ready: bool
    spend_controls_ready: bool
    permissions_ready: bool
    model_entitlements_ready: bool
    quotas_ready: bool
    rate_limits_ready: bool
    region_ready: bool
    endpoint_access_ready: bool
    terms_ready: bool
    revocation_ready: bool
    suspension_procedure_ready: bool
    incident_contact_ready: bool
    separation_of_duties_ready: bool
    evidence_fresh: bool
    account_verification_authorized: bool
    credential_onboarding_authorized: bool
    credential_loading_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool


@dataclass(frozen=True, slots=True)
class ProviderAccountReadinessAuditEvidenceV1:
    policy_id: str
    deployment_environment: str
    provider_ids: tuple[str, ...]
    account_profile_ids: tuple[str, ...]
    account_owner_roles: tuple[str, ...]
    accounts_verified: bool
    accounts_active: bool
    permission_scopes_ready: bool
    exact_model_entitlements_ready: bool
    billing_ready: bool
    spend_controls_ready: bool
    quotas_ready: bool
    rate_limits_ready: bool
    region_ready: bool
    endpoint_access_ready: bool
    terms_ready: bool
    revocation_ready: bool
    suspension_procedure_ready: bool
    incident_contact_ready: bool
    evidence_fresh: bool
    failure_codes: tuple[str, ...]
    account_verification_authorized: bool
    credential_onboarding_authorized: bool
    credential_loading_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool


_REQUIRED_MODELS = {
    "DEEPSEEK": ("deepseek-v4-pro",),
    "ANTHROPIC": ("claude-sonnet-5", "claude-opus-4-8"),
}
_REQUIRED_PROVIDERS = ("DEEPSEEK", "ANTHROPIC")


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _add(codes: list[str], condition: bool, code: str) -> None:
    if not condition:
        codes.append(code)


def _timestamps_valid(
    verified_at: datetime | None,
    expires_at: datetime | None,
    evaluated_at: datetime,
    maximum_age_days: int,
    codes: list[str],
) -> bool:
    if not isinstance(verified_at, datetime) or not isinstance(expires_at, datetime):
        codes.append("VERIFICATION_TIMESTAMP_REQUIRED")
        return False
    if verified_at > evaluated_at:
        codes.append("EVIDENCE_FROM_FUTURE")
        return False
    if expires_at < verified_at or expires_at < evaluated_at:
        codes.append("EVIDENCE_EXPIRED")
        return False
    age_days = (evaluated_at - verified_at).days
    if age_days < 0 or age_days > maximum_age_days:
        codes.append("EVIDENCE_EXPIRED")
        return False
    return True


def _profile_validity(
    policy: ProviderAccountReadinessPolicyV1,
    profile: ProviderAccountProfileV1 | None,
    evaluated_at: datetime,
    codes: list[str],
) -> tuple[bool, dict[str, bool]]:
    state = {name: False for name in (
        "verified", "active", "billing", "spend", "region", "endpoint", "terms",
        "revocation", "suspension", "incident", "separation", "fresh",
    )}
    if profile is None:
        codes.append("REQUIRED_PROVIDER_MISSING")
        return False, state
    _add(codes, _identifier(profile.account_profile_id), "ACCOUNT_PROFILE_ID_EMPTY")
    _add(codes, profile.policy_id == policy.policy_id, "REQUIRED_PROVIDER_MISSING")
    _add(codes, _identifier(profile.account_identity_reference), "ACCOUNT_IDENTITY_REFERENCE_EMPTY")
    _add(codes, profile.account_identity_redacted, "ACCOUNT_IDENTITY_NOT_REDACTED")
    roles = (
        (profile.account_owner_role, "ACCOUNT_OWNER_REQUIRED"),
        (profile.operational_owner_role, "OPERATIONAL_OWNER_REQUIRED"),
        (profile.billing_owner_role, "BILLING_OWNER_REQUIRED"),
        (profile.security_owner_role, "SECURITY_OWNER_REQUIRED"),
    )
    for role, code in roles:
        _add(codes, _identifier(role), code)
    state["verified"] = profile.account_verified
    state["active"] = profile.account_active
    state["billing"] = profile.billing_enabled
    state["spend"] = profile.spend_control_ready
    state["region"] = profile.region_compatible and _identifier(profile.region_classification)
    state["endpoint"] = profile.endpoint_access_ready and _identifier(profile.endpoint_access_classification)
    state["terms"] = profile.terms_acknowledged and profile.acceptable_use_acknowledged
    state["revocation"] = _identifier(profile.provider_console_revocation_procedure_id) and profile.provider_console_revocation_ready
    state["suspension"] = _identifier(profile.account_suspension_procedure_id) and profile.account_suspension_ready
    state["incident"] = _identifier(profile.incident_contact_id) and profile.incident_contact_ready
    state["separation"] = profile.separation_of_duties_ready and len({role for role, _ in roles}) == 4
    _add(codes, state["verified"], "ACCOUNT_NOT_VERIFIED")
    _add(codes, state["active"], "ACCOUNT_NOT_ACTIVE")
    _add(codes, state["billing"], "BILLING_NOT_ENABLED")
    _add(codes, state["spend"], "SPEND_CONTROL_NOT_READY")
    _add(codes, state["region"], "REGION_COMPATIBILITY_NOT_PROVEN")
    _add(codes, state["endpoint"], "ENDPOINT_ACCESS_NOT_PROVEN")
    _add(codes, profile.terms_acknowledged, "TERMS_ACKNOWLEDGEMENT_REQUIRED")
    _add(codes, profile.acceptable_use_acknowledged, "ACCEPTABLE_USE_ACKNOWLEDGEMENT_REQUIRED")
    _add(codes, state["revocation"], "PROVIDER_CONSOLE_REVOCATION_NOT_READY")
    _add(codes, state["suspension"], "ACCOUNT_SUSPENSION_PROCEDURE_NOT_READY")
    _add(codes, state["incident"], "INCIDENT_CONTACT_NOT_READY")
    _add(codes, state["separation"], "SEPARATION_OF_DUTIES_REQUIRED")
    state["fresh"] = _timestamps_valid(profile.verified_at, profile.evidence_expires_at, evaluated_at, policy.maximum_evidence_age_days, codes)
    return all(state.values()), state


def _permission_validity(
    policy: ProviderAccountReadinessPolicyV1,
    profile: ProviderAccountProfileV1,
    evidence: ProviderPermissionScopeEvidenceV1 | None,
    evaluated_at: datetime,
    codes: list[str],
) -> tuple[bool, bool, bool]:
    if evidence is None:
        codes.extend(("PERMISSION_EVIDENCE_ID_EMPTY", "PERMISSION_SCOPE_REQUIRED", "MODEL_ENTITLEMENT_NOT_VERIFIED"))
        return False, False, False
    _add(codes, _identifier(evidence.permission_evidence_id), "PERMISSION_EVIDENCE_ID_EMPTY")
    _add(codes, evidence.account_profile_id == profile.account_profile_id and evidence.provider_id == profile.provider_id, "REQUIRED_PROVIDER_MISSING")
    permission_ready = _identifier(evidence.permission_scope_id) and bool(evidence.permission_scope_classifications) and evidence.least_privilege_confirmed
    _add(codes, _identifier(evidence.permission_scope_id), "PERMISSION_SCOPE_REQUIRED")
    _add(codes, evidence.least_privilege_confirmed, "LEAST_PRIVILEGE_REQUIRED")
    excessive = not (evidence.account_admin_permission_avoided and evidence.billing_admin_permission_avoided and evidence.unrelated_permissions_absent)
    _add(codes, not excessive, "EXCESSIVE_PERMISSION_DETECTED")
    models = _REQUIRED_MODELS[profile.provider_id]
    entitlement_ready = (
        evidence.required_model_ids_present
        and set(models).issubset(evidence.entitled_exact_model_ids)
        and evidence.entitlement_verified
        and bool(evidence.model_entitlement_ids)
    )
    _add(codes, evidence.entitlement_verified, "MODEL_ENTITLEMENT_NOT_VERIFIED")
    _add(codes, evidence.required_model_ids_present and set(models).issubset(evidence.entitled_exact_model_ids), "REQUIRED_MODEL_ENTITLEMENT_MISSING")
    fresh = _timestamps_valid(evidence.verified_at, evidence.evidence_expires_at, evaluated_at, policy.maximum_evidence_age_days, codes)
    return permission_ready and not excessive and fresh, entitlement_ready and fresh, fresh


def _billing_validity(
    policy: ProviderAccountReadinessPolicyV1,
    profile: ProviderAccountProfileV1,
    evidence: ProviderBillingQuotaEvidenceV1 | None,
    evaluated_at: datetime,
    codes: list[str],
) -> tuple[bool, bool, bool, bool]:
    if evidence is None:
        codes.extend(("BILLING_QUOTA_EVIDENCE_ID_EMPTY", "QUOTA_EVIDENCE_REQUIRED", "RATE_LIMIT_EVIDENCE_REQUIRED"))
        return False, False, False, False
    _add(codes, _identifier(evidence.billing_quota_evidence_id), "BILLING_QUOTA_EVIDENCE_ID_EMPTY")
    _add(codes, evidence.account_profile_id == profile.account_profile_id and evidence.provider_id == profile.provider_id, "REQUIRED_PROVIDER_MISSING")
    billing_ready = evidence.billing_enabled and _identifier(evidence.billing_currency)
    spend_ready = evidence.hard_spend_limit_present and _identifier(evidence.hard_spend_limit_reference_id) and evidence.soft_alert_threshold_present and _identifier(evidence.soft_alert_threshold_reference_id)
    quota_ready = _identifier(evidence.provider_quota_classification) and evidence.provider_quota_classification not in {"NOT_VERIFIED", "EXPIRED", "REVOKED", "SUSPENDED"}
    rate_ready = _identifier(evidence.rate_limit_classification) and evidence.rate_limit_classification not in {"NOT_VERIFIED", "EXPIRED", "REVOKED", "SUSPENDED"}
    _add(codes, billing_ready, "BILLING_NOT_ENABLED")
    _add(codes, evidence.hard_spend_limit_present and _identifier(evidence.hard_spend_limit_reference_id), "HARD_SPEND_LIMIT_REQUIRED")
    _add(codes, evidence.soft_alert_threshold_present and _identifier(evidence.soft_alert_threshold_reference_id), "SOFT_ALERT_THRESHOLD_REQUIRED")
    _add(codes, quota_ready, "QUOTA_EVIDENCE_REQUIRED")
    _add(codes, rate_ready, "RATE_LIMIT_EVIDENCE_REQUIRED")
    numbers = (
        evidence.concurrent_request_limit, evidence.requests_per_minute_limit,
        evidence.input_tokens_per_minute_limit, evidence.output_tokens_per_minute_limit,
    )
    valid_numbers = all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in numbers)
    _add(codes, valid_numbers, "NUMERIC_LIMIT_INVALID")
    _add(codes, evidence.no_automatic_retry_on_quota_failure, "RATE_LIMIT_EVIDENCE_REQUIRED")
    fresh = _timestamps_valid(evidence.verified_at, evidence.evidence_expires_at, evaluated_at, policy.maximum_evidence_age_days, codes)
    return billing_ready and fresh, spend_ready and fresh, quota_ready and fresh, rate_ready and valid_numbers and fresh


def evaluate_provider_account_readiness_v1(
    policy: ProviderAccountReadinessPolicyV1,
    profiles: tuple[ProviderAccountProfileV1, ...],
    permission_evidence: tuple[ProviderPermissionScopeEvidenceV1, ...],
    billing_quota_evidence: tuple[ProviderBillingQuotaEvidenceV1, ...],
    evaluated_at: datetime,
) -> ProviderAccountReadinessDecisionV1:
    codes: list[str] = []
    _add(codes, _identifier(policy.policy_id), "POLICY_ID_EMPTY")
    _add(codes, _identifier(policy.policy_version), "POLICY_VERSION_EMPTY")
    _add(codes, _identifier(policy.deployment_environment), "DEPLOYMENT_ENVIRONMENT_EMPTY")
    _add(codes, policy.deployment_environment == "CONTROLLED_PRODUCTION", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED")
    _add(codes, set(_REQUIRED_PROVIDERS).issubset(policy.allowed_provider_ids), "PROVIDER_NOT_ALLOWED")
    _add(codes, set(_REQUIRED_PROVIDERS).issubset(policy.required_provider_ids), "REQUIRED_PROVIDER_MISSING")
    _add(codes, set(sum((list(item) for item in _REQUIRED_MODELS.values()), [])).issubset(policy.required_exact_model_ids), "REQUIRED_MODEL_ID_MISSING")
    maximum_valid = isinstance(policy.maximum_evidence_age_days, int) and not isinstance(policy.maximum_evidence_age_days, bool) and policy.maximum_evidence_age_days >= 0
    _add(codes, maximum_valid, "NUMERIC_LIMIT_INVALID")
    profile_by_provider = {item.provider_id: item for item in profiles if item.provider_id in _REQUIRED_PROVIDERS}
    permission_by_provider = {item.provider_id: item for item in permission_evidence if item.provider_id in _REQUIRED_PROVIDERS}
    billing_by_provider = {item.provider_id: item for item in billing_quota_evidence if item.provider_id in _REQUIRED_PROVIDERS}
    states: dict[str, dict[str, bool]] = {}
    permissions_ready: list[bool] = []
    entitlements_ready: list[bool] = []
    quotas_ready: list[bool] = []
    rates_ready: list[bool] = []
    for provider in _REQUIRED_PROVIDERS:
        profile = profile_by_provider.get(provider)
        profile_complete, state = _profile_validity(policy, profile, evaluated_at, codes)
        states[provider] = state
        if profile is None:
            permissions_ready.append(False); entitlements_ready.append(False); quotas_ready.append(False); rates_ready.append(False)
            continue
        permission_ready, entitlement_ready, permission_fresh = _permission_validity(policy, profile, permission_by_provider.get(provider), evaluated_at, codes)
        billing_ready, spend_ready, quota_ready, rate_ready = _billing_validity(policy, profile, billing_by_provider.get(provider), evaluated_at, codes)
        permissions_ready.append(permission_ready)
        entitlements_ready.append(entitlement_ready)
        quotas_ready.append(quota_ready)
        rates_ready.append(rate_ready)
        state["billing"] = state["billing"] and billing_ready
        state["spend"] = state["spend"] and spend_ready
        state["fresh"] = state["fresh"] and permission_fresh and all((billing_ready or not policy.require_billing_enabled, quota_ready or not policy.require_quota_evidence, rate_ready or not policy.require_rate_limit_evidence))
    all_verified = all(states[item]["verified"] for item in _REQUIRED_PROVIDERS)
    all_active = all(states[item]["active"] for item in _REQUIRED_PROVIDERS)
    billing_ready = all(states[item]["billing"] for item in _REQUIRED_PROVIDERS)
    spend_ready = all(states[item]["spend"] for item in _REQUIRED_PROVIDERS)
    region_ready = all(states[item]["region"] for item in _REQUIRED_PROVIDERS)
    endpoint_ready = all(states[item]["endpoint"] for item in _REQUIRED_PROVIDERS)
    terms_ready = all(states[item]["terms"] for item in _REQUIRED_PROVIDERS)
    revocation_ready = all(states[item]["revocation"] for item in _REQUIRED_PROVIDERS)
    suspension_ready = all(states[item]["suspension"] for item in _REQUIRED_PROVIDERS)
    incident_ready = all(states[item]["incident"] for item in _REQUIRED_PROVIDERS)
    separation_ready = all(states[item]["separation"] for item in _REQUIRED_PROVIDERS)
    evidence_fresh = maximum_valid and all(states[item]["fresh"] for item in _REQUIRED_PROVIDERS)
    failure_codes = tuple(sorted(set(codes)))
    return ProviderAccountReadinessDecisionV1(
        policy_id=policy.policy_id, deployment_environment=policy.deployment_environment,
        ready=not failure_codes, failure_codes=failure_codes,
        DeepSeek_account_ready=all(states["DEEPSEEK"].values()), Anthropic_account_ready=all(states["ANTHROPIC"].values()),
        all_accounts_verified=all_verified, all_accounts_active=all_active, billing_ready=billing_ready,
        spend_controls_ready=spend_ready, permissions_ready=all(permissions_ready), model_entitlements_ready=all(entitlements_ready),
        quotas_ready=all(quotas_ready), rate_limits_ready=all(rates_ready), region_ready=region_ready,
        endpoint_access_ready=endpoint_ready, terms_ready=terms_ready, revocation_ready=revocation_ready,
        suspension_procedure_ready=suspension_ready, incident_contact_ready=incident_ready,
        separation_of_duties_ready=separation_ready, evidence_fresh=evidence_fresh,
        account_verification_authorized=False, credential_onboarding_authorized=False,
        credential_loading_authorized=False, network_authorized=False, provider_transmission_authorized=False,
    )


def build_provider_account_readiness_audit_evidence_v1(
    policy: ProviderAccountReadinessPolicyV1,
    profiles: tuple[ProviderAccountProfileV1, ...],
    permission_evidence: tuple[ProviderPermissionScopeEvidenceV1, ...],
    billing_quota_evidence: tuple[ProviderBillingQuotaEvidenceV1, ...],
    decision: ProviderAccountReadinessDecisionV1,
) -> ProviderAccountReadinessAuditEvidenceV1:
    profile_by_provider = {item.provider_id: item for item in profiles}
    if set(profile_by_provider) != set(_REQUIRED_PROVIDERS) or len(profiles) != 2:
        raise ValueError("account profile identity alignment failed")
    ordered_profiles = tuple(profile_by_provider[item] for item in _REQUIRED_PROVIDERS)
    if decision.policy_id != policy.policy_id or decision.deployment_environment != policy.deployment_environment:
        raise ValueError("decision identity alignment failed")
    for item in permission_evidence:
        profile = profile_by_provider.get(item.provider_id)
        if profile is None or item.account_profile_id != profile.account_profile_id:
            raise ValueError("permission identity alignment failed")
    for item in billing_quota_evidence:
        profile = profile_by_provider.get(item.provider_id)
        if profile is None or item.account_profile_id != profile.account_profile_id:
            raise ValueError("billing identity alignment failed")
    return ProviderAccountReadinessAuditEvidenceV1(
        policy_id=policy.policy_id, deployment_environment=policy.deployment_environment,
        provider_ids=_REQUIRED_PROVIDERS, account_profile_ids=tuple(item.account_profile_id for item in ordered_profiles),
        account_owner_roles=tuple(item.account_owner_role for item in ordered_profiles),
        accounts_verified=decision.all_accounts_verified, accounts_active=decision.all_accounts_active,
        permission_scopes_ready=decision.permissions_ready, exact_model_entitlements_ready=decision.model_entitlements_ready,
        billing_ready=decision.billing_ready, spend_controls_ready=decision.spend_controls_ready,
        quotas_ready=decision.quotas_ready, rate_limits_ready=decision.rate_limits_ready,
        region_ready=decision.region_ready, endpoint_access_ready=decision.endpoint_access_ready,
        terms_ready=decision.terms_ready, revocation_ready=decision.revocation_ready,
        suspension_procedure_ready=decision.suspension_procedure_ready,
        incident_contact_ready=decision.incident_contact_ready, evidence_fresh=decision.evidence_fresh,
        failure_codes=decision.failure_codes, account_verification_authorized=False,
        credential_onboarding_authorized=False, credential_loading_authorized=False,
        network_authorized=False, provider_transmission_authorized=False,
    )
