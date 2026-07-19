"""Pure validation for redacted provider-account verification procedures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProviderAccountVerificationPolicyV1:
    policy_id: str = ""
    policy_version: str = ""
    deployment_environment: str = ""
    allowed_provider_ids: tuple[str, ...] = ()
    required_provider_ids: tuple[str, ...] = ()
    required_exact_model_ids: tuple[str, ...] = ()
    require_manual_console_verification: bool = True
    require_operator_identity: bool = True
    require_reviewer_identity: bool = True
    require_distinct_operator_and_reviewer: bool = True
    require_provider_account_active: bool = True
    require_model_entitlement_confirmation: bool = True
    require_billing_enabled_confirmation: bool = True
    require_hard_spend_limit_confirmation: bool = True
    require_soft_alert_confirmation: bool = True
    require_quota_classification: bool = True
    require_rate_limit_classification: bool = True
    require_region_compatibility_confirmation: bool = True
    require_endpoint_access_confirmation: bool = True
    require_terms_acknowledgement: bool = True
    require_provider_console_revocation_confirmation: bool = True
    require_account_suspension_confirmation: bool = True
    require_incident_contact_confirmation: bool = True
    require_no_secret_capture: bool = True
    require_no_raw_account_identity: bool = True
    require_no_screenshot_retention: bool = True
    require_no_balance_capture: bool = True
    require_no_invoice_capture: bool = True
    require_no_cookie_capture: bool = True
    require_evidence_freshness: bool = True
    maximum_evidence_age_days: int = 0
    account_inspection_authorized: bool = False
    account_verification_recording_authorized: bool = False
    credential_onboarding_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class ProviderAccountVerificationChecklistV1:
    checklist_id: str
    policy_id: str
    provider_id: str
    required_exact_model_ids: tuple[str, ...]
    confirm_account_active: bool
    confirm_model_entitlements: bool
    confirm_billing_enabled: bool
    confirm_hard_spend_limit: bool
    confirm_soft_alert_threshold: bool
    confirm_quota_classification: bool
    confirm_rate_limit_classification: bool
    confirm_region_compatibility: bool
    confirm_endpoint_access: bool
    confirm_terms_acknowledged: bool
    confirm_acceptable_use_acknowledged: bool
    confirm_console_revocation_procedure: bool
    confirm_account_suspension_procedure: bool
    confirm_incident_contact: bool
    prohibit_secret_capture: bool
    prohibit_account_identity_capture: bool
    prohibit_screenshot_retention: bool
    prohibit_balance_capture: bool
    prohibit_invoice_capture: bool
    prohibit_payment_data_capture: bool
    prohibit_cookie_capture: bool
    prohibit_authorization_header_capture: bool
    checklist_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderAccountOperatorAttestationV1:
    attestation_id: str
    checklist_id: str
    policy_id: str
    provider_id: str
    operator_id: str
    operator_role: str
    verification_method_classification: str
    account_active_confirmed: bool
    model_entitlements_confirmed: bool
    entitled_exact_model_ids: tuple[str, ...]
    billing_enabled_confirmed: bool
    hard_spend_limit_confirmed: bool
    soft_alert_threshold_confirmed: bool
    quota_classification_confirmed: bool
    rate_limit_classification_confirmed: bool
    region_compatibility_confirmed: bool
    endpoint_access_confirmed: bool
    terms_acknowledged: bool
    acceptable_use_acknowledged: bool
    console_revocation_confirmed: bool
    account_suspension_confirmed: bool
    incident_contact_confirmed: bool
    no_secret_captured: bool
    no_account_identity_captured: bool
    no_screenshot_retained: bool
    no_balance_captured: bool
    no_invoice_captured: bool
    no_payment_data_captured: bool
    no_cookie_captured: bool
    no_authorization_header_captured: bool
    verified_at: datetime | None
    evidence_expires_at: datetime | None
    attestation_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderAccountReviewerApprovalV1:
    approval_id: str
    attestation_id: str
    checklist_id: str
    policy_id: str
    provider_id: str
    reviewer_id: str
    reviewer_role: str
    operator_reviewer_distinct: bool
    required_models_confirmed: bool
    billing_controls_confirmed: bool
    quota_and_rate_limit_classifications_confirmed: bool
    operational_procedures_confirmed: bool
    prohibited_evidence_absent: bool
    attestation_identity_verified: bool
    approved: bool
    reviewed_at: datetime | None
    evidence_expires_at: datetime | None
    approval_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderAccountVerificationFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class ProviderAccountVerificationDecisionV1:
    policy_id: str
    deployment_environment: str
    ready: bool
    failure_codes: tuple[str, ...]
    DeepSeek_verification_procedure_ready: bool
    Anthropic_verification_procedure_ready: bool
    operator_attestations_ready: bool
    reviewer_approvals_ready: bool
    model_entitlements_confirmed: bool
    billing_controls_confirmed: bool
    quota_and_rate_limits_confirmed: bool
    region_and_endpoint_confirmed: bool
    terms_confirmed: bool
    revocation_and_suspension_confirmed: bool
    incident_contacts_confirmed: bool
    prohibited_evidence_absent: bool
    evidence_fresh: bool
    account_inspection_authorized: bool
    account_verification_recording_authorized: bool
    credential_onboarding_authorized: bool
    credential_loading_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool


@dataclass(frozen=True, slots=True)
class ProviderAccountVerificationAuditEvidenceV1:
    policy_id: str
    deployment_environment: str
    provider_ids: tuple[str, ...]
    checklist_ids: tuple[str, ...]
    operator_roles: tuple[str, ...]
    reviewer_roles: tuple[str, ...]
    model_entitlements_confirmed: bool
    billing_controls_confirmed: bool
    quota_and_rate_limits_confirmed: bool
    region_and_endpoint_confirmed: bool
    terms_confirmed: bool
    revocation_and_suspension_confirmed: bool
    incident_contacts_confirmed: bool
    prohibited_evidence_absent: bool
    evidence_fresh: bool
    failure_codes: tuple[str, ...]
    account_inspection_authorized: bool
    account_verification_recording_authorized: bool
    credential_onboarding_authorized: bool
    credential_loading_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool


_PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
_MODELS = {
    "DEEPSEEK": ("deepseek-v4-pro",),
    "ANTHROPIC": ("claude-sonnet-5", "claude-opus-4-8"),
}
_METHODS = {
    "MANUAL_PROVIDER_CONSOLE_REVIEW",
    "OWNER_ATTESTED_PROVIDER_CONSOLE_REVIEW",
    "INDEPENDENT_REVIEWED_PROVIDER_CONSOLE_REVIEW",
    "NOT_VERIFIED", "EXPIRED", "REVOKED", "SUSPENDED",
}


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _add(codes: list[str], condition: bool, code: str) -> None:
    if not condition:
        codes.append(code)


def _fresh(
    observed_at: datetime | None,
    expires_at: datetime | None,
    evaluated_at: datetime,
    maximum_age_days: int,
    codes: list[str],
) -> bool:
    if not isinstance(observed_at, datetime) or not isinstance(expires_at, datetime):
        codes.append("VERIFICATION_TIMESTAMP_REQUIRED")
        return False
    if observed_at > evaluated_at:
        codes.append("EVIDENCE_FROM_FUTURE")
        return False
    if expires_at < observed_at or expires_at < evaluated_at:
        codes.append("EVIDENCE_EXPIRED")
        return False
    age_days = (evaluated_at - observed_at).days
    if age_days < 0 or age_days > maximum_age_days:
        codes.append("EVIDENCE_EXPIRED")
        return False
    return True


def _checklist_valid(
    policy: ProviderAccountVerificationPolicyV1,
    checklist: ProviderAccountVerificationChecklistV1 | None,
    provider: str,
    codes: list[str],
) -> bool:
    if checklist is None:
        codes.append("REQUIRED_PROVIDER_MISSING")
        return False
    _add(codes, _identifier(checklist.checklist_id), "CHECKLIST_ID_EMPTY")
    _add(codes, checklist.policy_id == policy.policy_id and checklist.provider_id == provider, "REQUIRED_PROVIDER_MISSING")
    _add(codes, checklist.required_exact_model_ids == _MODELS[provider], "REQUIRED_MODEL_ID_MISSING")
    requirements = (
        checklist.confirm_account_active, checklist.confirm_model_entitlements,
        checklist.confirm_billing_enabled, checklist.confirm_hard_spend_limit,
        checklist.confirm_soft_alert_threshold, checklist.confirm_quota_classification,
        checklist.confirm_rate_limit_classification, checklist.confirm_region_compatibility,
        checklist.confirm_endpoint_access, checklist.confirm_terms_acknowledged,
        checklist.confirm_acceptable_use_acknowledged, checklist.confirm_console_revocation_procedure,
        checklist.confirm_account_suspension_procedure, checklist.confirm_incident_contact,
        checklist.prohibit_secret_capture, checklist.prohibit_account_identity_capture,
        checklist.prohibit_screenshot_retention, checklist.prohibit_balance_capture,
        checklist.prohibit_invoice_capture, checklist.prohibit_payment_data_capture,
        checklist.prohibit_cookie_capture, checklist.prohibit_authorization_header_capture,
    )
    complete = all(requirements)
    _add(codes, complete and checklist.checklist_ready, "CHECKLIST_NOT_READY")
    return complete and checklist.checklist_ready


def _attestation_valid(
    policy: ProviderAccountVerificationPolicyV1,
    checklist: ProviderAccountVerificationChecklistV1,
    attestation: ProviderAccountOperatorAttestationV1 | None,
    evaluated_at: datetime,
    codes: list[str],
) -> tuple[bool, dict[str, bool]]:
    state = {key: False for key in ("account", "models", "billing", "quota", "region", "terms", "procedures", "incident", "prohibited", "fresh")}
    if attestation is None:
        codes.append("ATTESTATION_ID_EMPTY")
        return False, state
    _add(codes, _identifier(attestation.attestation_id), "ATTESTATION_ID_EMPTY")
    _add(codes, attestation.checklist_id == checklist.checklist_id and attestation.policy_id == policy.policy_id and attestation.provider_id == checklist.provider_id, "REVIEW_IDENTITY_MISMATCH")
    _add(codes, _identifier(attestation.operator_id), "OPERATOR_ID_EMPTY")
    _add(codes, _identifier(attestation.operator_role), "OPERATOR_ROLE_EMPTY")
    _add(codes, attestation.verification_method_classification in _METHODS and attestation.verification_method_classification not in {"NOT_VERIFIED", "EXPIRED", "REVOKED", "SUSPENDED"}, "VERIFICATION_METHOD_INVALID")
    state["account"] = attestation.account_active_confirmed
    state["models"] = attestation.model_entitlements_confirmed and attestation.entitled_exact_model_ids == _MODELS[checklist.provider_id]
    state["billing"] = attestation.billing_enabled_confirmed and attestation.hard_spend_limit_confirmed and attestation.soft_alert_threshold_confirmed
    state["quota"] = attestation.quota_classification_confirmed and attestation.rate_limit_classification_confirmed
    state["region"] = attestation.region_compatibility_confirmed and attestation.endpoint_access_confirmed
    state["terms"] = attestation.terms_acknowledged and attestation.acceptable_use_acknowledged
    state["procedures"] = attestation.console_revocation_confirmed and attestation.account_suspension_confirmed
    state["incident"] = attestation.incident_contact_confirmed
    state["prohibited"] = all((attestation.no_secret_captured, attestation.no_account_identity_captured, attestation.no_screenshot_retained, attestation.no_balance_captured, attestation.no_invoice_captured, attestation.no_payment_data_captured, attestation.no_cookie_captured, attestation.no_authorization_header_captured))
    _add(codes, state["account"], "ACCOUNT_ACTIVE_NOT_CONFIRMED")
    _add(codes, attestation.model_entitlements_confirmed, "MODEL_ENTITLEMENTS_NOT_CONFIRMED")
    _add(codes, attestation.entitled_exact_model_ids == _MODELS[checklist.provider_id], "REQUIRED_MODEL_ENTITLEMENT_MISSING")
    _add(codes, attestation.billing_enabled_confirmed, "BILLING_NOT_CONFIRMED")
    _add(codes, attestation.hard_spend_limit_confirmed, "HARD_SPEND_LIMIT_NOT_CONFIRMED")
    _add(codes, attestation.soft_alert_threshold_confirmed, "SOFT_ALERT_NOT_CONFIRMED")
    _add(codes, attestation.quota_classification_confirmed, "QUOTA_CLASSIFICATION_NOT_CONFIRMED")
    _add(codes, attestation.rate_limit_classification_confirmed, "RATE_LIMIT_CLASSIFICATION_NOT_CONFIRMED")
    _add(codes, attestation.region_compatibility_confirmed, "REGION_COMPATIBILITY_NOT_CONFIRMED")
    _add(codes, attestation.endpoint_access_confirmed, "ENDPOINT_ACCESS_NOT_CONFIRMED")
    _add(codes, attestation.terms_acknowledged, "TERMS_NOT_ACKNOWLEDGED")
    _add(codes, attestation.acceptable_use_acknowledged, "ACCEPTABLE_USE_NOT_ACKNOWLEDGED")
    _add(codes, attestation.console_revocation_confirmed, "CONSOLE_REVOCATION_NOT_CONFIRMED")
    _add(codes, attestation.account_suspension_confirmed, "ACCOUNT_SUSPENSION_NOT_CONFIRMED")
    _add(codes, attestation.incident_contact_confirmed, "INCIDENT_CONTACT_NOT_CONFIRMED")
    capture_codes = (
        (attestation.no_secret_captured, "SECRET_CAPTURE_DETECTED"),
        (attestation.no_account_identity_captured, "RAW_ACCOUNT_IDENTITY_CAPTURE_DETECTED"),
        (attestation.no_screenshot_retained, "SCREENSHOT_RETENTION_DETECTED"),
        (attestation.no_balance_captured, "BALANCE_CAPTURE_DETECTED"),
        (attestation.no_invoice_captured, "INVOICE_CAPTURE_DETECTED"),
        (attestation.no_payment_data_captured, "PAYMENT_DATA_CAPTURE_DETECTED"),
        (attestation.no_cookie_captured, "COOKIE_CAPTURE_DETECTED"),
        (attestation.no_authorization_header_captured, "AUTHORIZATION_HEADER_CAPTURE_DETECTED"),
    )
    for safe, code in capture_codes:
        _add(codes, safe, code)
    state["fresh"] = _fresh(attestation.verified_at, attestation.evidence_expires_at, evaluated_at, policy.maximum_evidence_age_days, codes)
    complete = all(state.values()) and attestation.attestation_ready
    return complete, state


def _approval_valid(
    policy: ProviderAccountVerificationPolicyV1,
    checklist: ProviderAccountVerificationChecklistV1,
    attestation: ProviderAccountOperatorAttestationV1 | None,
    approval: ProviderAccountReviewerApprovalV1 | None,
    evaluated_at: datetime,
    codes: list[str],
) -> tuple[bool, bool]:
    if approval is None:
        codes.append("APPROVAL_ID_EMPTY")
        return False, False
    _add(codes, _identifier(approval.approval_id), "APPROVAL_ID_EMPTY")
    _add(codes, _identifier(approval.reviewer_id), "REVIEWER_ID_EMPTY")
    _add(codes, _identifier(approval.reviewer_role), "REVIEWER_ROLE_EMPTY")
    aligned = attestation is not None and approval.attestation_id == attestation.attestation_id and approval.checklist_id == checklist.checklist_id and approval.policy_id == policy.policy_id and approval.provider_id == checklist.provider_id
    _add(codes, aligned and approval.attestation_identity_verified, "REVIEW_IDENTITY_MISMATCH")
    distinct = attestation is not None and approval.operator_reviewer_distinct and approval.reviewer_id != attestation.operator_id
    _add(codes, distinct, "OPERATOR_REVIEWER_MUST_BE_DISTINCT")
    _add(codes, approval.required_models_confirmed, "MODEL_ENTITLEMENTS_NOT_CONFIRMED")
    _add(codes, approval.billing_controls_confirmed, "BILLING_NOT_CONFIRMED")
    _add(codes, approval.quota_and_rate_limit_classifications_confirmed, "QUOTA_CLASSIFICATION_NOT_CONFIRMED")
    _add(codes, approval.operational_procedures_confirmed, "CONSOLE_REVOCATION_NOT_CONFIRMED")
    _add(codes, approval.prohibited_evidence_absent, "SECRET_CAPTURE_DETECTED")
    _add(codes, approval.approved and approval.approval_ready, "REVIEWER_APPROVAL_REQUIRED")
    fresh = _fresh(approval.reviewed_at, approval.evidence_expires_at, evaluated_at, policy.maximum_evidence_age_days, codes)
    return aligned and distinct and approval.required_models_confirmed and approval.billing_controls_confirmed and approval.quota_and_rate_limit_classifications_confirmed and approval.operational_procedures_confirmed and approval.prohibited_evidence_absent and approval.approved and approval.approval_ready and fresh, fresh


def evaluate_provider_account_verification_v1(
    policy: ProviderAccountVerificationPolicyV1,
    checklists: tuple[ProviderAccountVerificationChecklistV1, ...],
    attestations: tuple[ProviderAccountOperatorAttestationV1, ...],
    approvals: tuple[ProviderAccountReviewerApprovalV1, ...],
    evaluated_at: datetime,
) -> ProviderAccountVerificationDecisionV1:
    codes: list[str] = []
    _add(codes, _identifier(policy.policy_id), "POLICY_ID_EMPTY")
    _add(codes, _identifier(policy.policy_version), "POLICY_VERSION_EMPTY")
    _add(codes, _identifier(policy.deployment_environment), "DEPLOYMENT_ENVIRONMENT_EMPTY")
    _add(codes, policy.deployment_environment == "CONTROLLED_PRODUCTION", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED")
    _add(codes, set(_PROVIDERS).issubset(policy.allowed_provider_ids), "PROVIDER_NOT_ALLOWED")
    _add(codes, set(_PROVIDERS).issubset(policy.required_provider_ids), "REQUIRED_PROVIDER_MISSING")
    _add(codes, set(sum((list(models) for models in _MODELS.values()), [])).issubset(policy.required_exact_model_ids), "REQUIRED_MODEL_ID_MISSING")
    maximum_valid = isinstance(policy.maximum_evidence_age_days, int) and not isinstance(policy.maximum_evidence_age_days, bool) and policy.maximum_evidence_age_days >= 0
    _add(codes, maximum_valid, "VERIFICATION_TIMESTAMP_REQUIRED")
    checklist_by_provider = {item.provider_id: item for item in checklists}
    attestation_by_provider = {item.provider_id: item for item in attestations}
    approval_by_provider = {item.provider_id: item for item in approvals}
    procedure_ready: dict[str, bool] = {}
    attestation_ready: list[bool] = []
    approval_ready: list[bool] = []
    states: dict[str, dict[str, bool]] = {}
    for provider in _PROVIDERS:
        checklist = checklist_by_provider.get(provider)
        checklist_ready = _checklist_valid(policy, checklist, provider, codes)
        if checklist is None:
            procedure_ready[provider] = False
            attestation_ready.append(False); approval_ready.append(False)
            states[provider] = {key: False for key in ("models", "billing", "quota", "region", "terms", "procedures", "incident", "prohibited", "fresh")}
            continue
        attestation_complete, state = _attestation_valid(policy, checklist, attestation_by_provider.get(provider), evaluated_at, codes)
        approval_complete, approval_fresh = _approval_valid(policy, checklist, attestation_by_provider.get(provider), approval_by_provider.get(provider), evaluated_at, codes)
        state["fresh"] = state["fresh"] and approval_fresh
        procedure_ready[provider] = checklist_ready and attestation_complete and approval_complete
        attestation_ready.append(attestation_complete)
        approval_ready.append(approval_complete)
        states[provider] = state
    failure_codes = tuple(sorted(set(codes)))
    all_state = lambda key: all(states[provider][key] for provider in _PROVIDERS)
    return ProviderAccountVerificationDecisionV1(
        policy_id=policy.policy_id, deployment_environment=policy.deployment_environment,
        ready=not failure_codes, failure_codes=failure_codes,
        DeepSeek_verification_procedure_ready=procedure_ready["DEEPSEEK"], Anthropic_verification_procedure_ready=procedure_ready["ANTHROPIC"],
        operator_attestations_ready=all(attestation_ready), reviewer_approvals_ready=all(approval_ready),
        model_entitlements_confirmed=all_state("models"), billing_controls_confirmed=all_state("billing"),
        quota_and_rate_limits_confirmed=all_state("quota"), region_and_endpoint_confirmed=all_state("region"),
        terms_confirmed=all_state("terms"), revocation_and_suspension_confirmed=all_state("procedures"),
        incident_contacts_confirmed=all_state("incident"), prohibited_evidence_absent=all_state("prohibited"),
        evidence_fresh=maximum_valid and all_state("fresh"), account_inspection_authorized=False,
        account_verification_recording_authorized=False, credential_onboarding_authorized=False,
        credential_loading_authorized=False, network_authorized=False, provider_transmission_authorized=False,
    )


def build_provider_account_verification_audit_evidence_v1(
    policy: ProviderAccountVerificationPolicyV1,
    checklists: tuple[ProviderAccountVerificationChecklistV1, ...],
    attestations: tuple[ProviderAccountOperatorAttestationV1, ...],
    approvals: tuple[ProviderAccountReviewerApprovalV1, ...],
    decision: ProviderAccountVerificationDecisionV1,
) -> ProviderAccountVerificationAuditEvidenceV1:
    checklist_by_provider = {item.provider_id: item for item in checklists}
    attestation_by_provider = {item.provider_id: item for item in attestations}
    approval_by_provider = {item.provider_id: item for item in approvals}
    if set(checklist_by_provider) != set(_PROVIDERS) or len(checklists) != 2:
        raise ValueError("checklist identity alignment failed")
    if decision.policy_id != policy.policy_id or decision.deployment_environment != policy.deployment_environment:
        raise ValueError("decision identity alignment failed")
    for provider in _PROVIDERS:
        checklist = checklist_by_provider[provider]
        attestation = attestation_by_provider.get(provider)
        approval = approval_by_provider.get(provider)
        if attestation is None or approval is None or attestation.checklist_id != checklist.checklist_id or approval.attestation_id != attestation.attestation_id or approval.checklist_id != checklist.checklist_id:
            raise ValueError("attestation or approval identity alignment failed")
    ordered_checklists = tuple(checklist_by_provider[provider] for provider in _PROVIDERS)
    ordered_attestations = tuple(attestation_by_provider[provider] for provider in _PROVIDERS)
    ordered_approvals = tuple(approval_by_provider[provider] for provider in _PROVIDERS)
    return ProviderAccountVerificationAuditEvidenceV1(
        policy_id=policy.policy_id, deployment_environment=policy.deployment_environment, provider_ids=_PROVIDERS,
        checklist_ids=tuple(item.checklist_id for item in ordered_checklists),
        operator_roles=tuple(item.operator_role for item in ordered_attestations),
        reviewer_roles=tuple(item.reviewer_role for item in ordered_approvals),
        model_entitlements_confirmed=decision.model_entitlements_confirmed,
        billing_controls_confirmed=decision.billing_controls_confirmed,
        quota_and_rate_limits_confirmed=decision.quota_and_rate_limits_confirmed,
        region_and_endpoint_confirmed=decision.region_and_endpoint_confirmed,
        terms_confirmed=decision.terms_confirmed,
        revocation_and_suspension_confirmed=decision.revocation_and_suspension_confirmed,
        incident_contacts_confirmed=decision.incident_contacts_confirmed,
        prohibited_evidence_absent=decision.prohibited_evidence_absent, evidence_fresh=decision.evidence_fresh,
        failure_codes=decision.failure_codes, account_inspection_authorized=False,
        account_verification_recording_authorized=False, credential_onboarding_authorized=False,
        credential_loading_authorized=False, network_authorized=False, provider_transmission_authorized=False,
    )
