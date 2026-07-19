"""Pure metadata-only owner provider-selection and routing boundary."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderSelectionPolicyV1:
    policy_id: str = ""; policy_version: str = ""; deployment_environment: str = ""; allowed_provider_ids: tuple = (); allowed_routing_levels: tuple = ()
    required_primary_provider_id: str = ""; required_escalation_provider_id: str = ""; require_distinct_primary_and_escalation_providers: bool = True
    require_exact_model_id_verification: bool = True; require_api_product_verification: bool = True; require_api_version_verification: bool = True
    require_endpoint_verification: bool = True; require_account_verification: bool = True; require_permission_scope_verification: bool = True
    require_pricing_verification: bool = True; require_quota_verification: bool = True; require_budget_policy: bool = True
    require_credential_governance: bool = True; require_provider_console_revocation_procedure: bool = True; require_zero_retry_initially: bool = True
    require_fail_closed_routing: bool = True; provider_selection_authorized: bool = False; exact_model_binding_authorized: bool = False
    credential_onboarding_authorized: bool = False; credential_loading_authorized: bool = False; network_authorized: bool = False
    provider_transmission_authorized: bool = False; fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class ProviderProfileV1:
    provider_profile_id: str; policy_id: str; provider_id: str; provider_role: str; owner_selected: bool; owner_selection_id: str
    API_product_classification: str; exact_API_product_id: str; API_product_verified: bool; exact_API_version: str
    API_version_verified: bool; endpoint_configuration_id: str; endpoint_verified: bool; account_evidence_id: str
    account_verified: bool; permission_scope_id: str; permission_scope_verified: bool; pricing_evidence_id: str
    pricing_verified: bool; quota_evidence_id: str; quota_verified: bool; budget_policy_id: str; budget_policy_ready: bool
    credential_governance_policy_id: str; credential_governance_ready: bool; provider_console_revocation_procedure_id: str
    provider_console_revocation_ready: bool; profile_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderModelRouteV1:
    route_id: str; policy_id: str; provider_profile_id: str; provider_id: str; routing_level: str; routing_role: str
    owner_model_selection: str; exact_provider_model_id: str; exact_model_id_verified: bool; model_family: str
    API_product_classification: str; context_limit_evidence_id: str; context_limit_verified: bool; capability_evidence_id: str
    capability_verified: bool; pricing_evidence_id: str; pricing_verified: bool; quota_evidence_id: str; quota_verified: bool
    per_request_budget_policy_id: str; per_request_budget_ready: bool; period_budget_policy_id: str
    period_budget_ready: bool; route_enabled: bool; route_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderEscalationPolicyV1:
    escalation_policy_id: str; policy_id: str; L0_route_id: str; L1_route_id: str; L2_route_id: str; L0_provider_id: str
    L1_provider_id: str; L2_provider_id: str; L0_to_L1_allowed: bool; L1_to_L2_allowed: bool; L0_to_L2_direct_allowed: bool
    downgrade_allowed: bool; fallback_provider_allowed: bool; retry_same_level_allowed: bool; maximum_escalation_level: str
    require_explicit_escalation_reason: bool; require_budget_revalidation_before_escalation: bool
    require_reservation_before_each_provider_call: bool; require_separate_provider_budget: bool
    require_separate_provider_credential_profile: bool; require_fail_closed_unavailable_route: bool; escalation_policy_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderSelectionFailureV1:
    failure_code: str; safe_message: str; retryable: bool


@dataclass(frozen=True, slots=True)
class ProviderSelectionReadinessDecisionV1:
    policy_id: str; deployment_environment: str; ready: bool; failure_codes: tuple[str, ...]; owner_selection_valid: bool
    primary_provider_ready: bool; escalation_provider_ready: bool; L0_route_ready: bool; L1_route_ready: bool; L2_route_ready: bool
    escalation_policy_ready: bool; exact_model_ids_verified: bool; API_products_verified: bool; API_versions_verified: bool
    endpoints_verified: bool; accounts_verified: bool; permission_scopes_verified: bool; pricing_verified: bool; quotas_verified: bool
    budgets_ready: bool; credential_governance_ready: bool; provider_console_revocation_ready: bool
    provider_selection_authorized: bool; exact_model_binding_authorized: bool; credential_onboarding_authorized: bool
    credential_loading_authorized: bool; network_authorized: bool; provider_transmission_authorized: bool


@dataclass(frozen=True, slots=True)
class ProviderSelectionAuditEvidenceV1:
    policy_id: str; deployment_environment: str; primary_provider_profile_id: str; escalation_provider_profile_id: str
    L0_route_id: str; L1_route_id: str; L2_route_id: str; L0_owner_model_selection: str; L1_owner_model_selection: str
    L2_owner_model_selection: str; exact_model_ids_verified: bool; API_products_verified: bool; API_versions_verified: bool
    endpoints_verified: bool; accounts_verified: bool; permission_scopes_verified: bool; pricing_verified: bool; quotas_verified: bool
    budgets_ready: bool; credential_governance_ready: bool; provider_console_revocation_ready: bool; escalation_policy_ready: bool
    failure_codes: tuple[str, ...]; provider_selection_authorized: bool; exact_model_binding_authorized: bool
    credential_onboarding_authorized: bool; credential_loading_authorized: bool; network_authorized: bool
    provider_transmission_authorized: bool


def _id(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _add(codes: list[str], valid: bool, code: str) -> None:
    if not valid:
        codes.append(code)


_EXPECTED = {
    "L0": ("DEEPSEEK", "PRIMARY_LIVE_REVIEW", "DEEPSEEK_V4_PRO"),
    "L1": ("ANTHROPIC", "ESCALATED_REVIEW", "CLAUDE_SONNET_5"),
    "L2": ("ANTHROPIC", "HIGHEST_ESCALATION_REVIEW", "CLAUDE_OPUS_4_8"),
}


def evaluate_provider_selection_readiness_v1(
    policy: ProviderSelectionPolicyV1,
    primary_profile: ProviderProfileV1,
    escalation_profile: ProviderProfileV1,
    routes: tuple[ProviderModelRouteV1, ...],
    escalation_policy: ProviderEscalationPolicyV1,
) -> ProviderSelectionReadinessDecisionV1:
    codes: list[str] = []
    _add(codes, _id(policy.policy_id), "POLICY_ID_EMPTY")
    _add(codes, _id(policy.policy_version), "POLICY_VERSION_EMPTY")
    _add(codes, _id(policy.deployment_environment), "DEPLOYMENT_ENVIRONMENT_EMPTY")
    _add(codes, policy.deployment_environment == "CONTROLLED_PRODUCTION", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED")
    _add(codes, _id(policy.required_primary_provider_id), "PRIMARY_PROVIDER_ID_EMPTY")
    _add(codes, _id(policy.required_escalation_provider_id), "ESCALATION_PROVIDER_ID_EMPTY")
    _add(codes, policy.required_primary_provider_id == "DEEPSEEK", "PRIMARY_PROVIDER_MISMATCH")
    _add(codes, policy.required_escalation_provider_id == "ANTHROPIC", "ESCALATION_PROVIDER_MISMATCH")
    _add(codes, all(item in policy.allowed_provider_ids for item in ("DEEPSEEK", "ANTHROPIC")), "PROVIDER_NOT_ALLOWED")
    _add(codes, primary_profile.provider_id == "DEEPSEEK", "PRIMARY_PROVIDER_MISMATCH")
    _add(codes, escalation_profile.provider_id == "ANTHROPIC", "ESCALATION_PROVIDER_MISMATCH")
    for profile in (primary_profile, escalation_profile):
        _add(codes, _id(profile.provider_profile_id), "PROVIDER_PROFILE_ID_EMPTY")
        _add(codes, profile.provider_role in ("PRIMARY", "ESCALATION"), "PROVIDER_ROLE_INVALID")
        _add(codes, _id(profile.owner_selection_id), "OWNER_SELECTION_ID_EMPTY")
        _add(codes, profile.owner_selected, "OWNER_SELECTION_NOT_APPROVED")
        _add(codes, profile.policy_id == policy.policy_id, "PROVIDER_PROFILE_ID_EMPTY")
    by_level: dict[str, ProviderModelRouteV1] = {}
    for route in routes:
        _add(codes, _id(route.route_id), "ROUTE_ID_EMPTY")
        _add(codes, _id(route.routing_level), "ROUTING_LEVEL_EMPTY")
        _add(codes, route.routing_level in _EXPECTED and route.routing_level in policy.allowed_routing_levels, "ROUTING_LEVEL_INVALID")
        if route.routing_level in by_level:
            codes.append("ROUTING_LEVEL_DUPLICATE")
        else:
            by_level[route.routing_level] = route
        _add(codes, route.policy_id == policy.policy_id, "ROUTE_PROVIDER_MISMATCH")
    for level, expected in _EXPECTED.items():
        route = by_level.get(level)
        if route is None:
            codes.append(f"{level}_ROUTE_REQUIRED")
            continue
        provider, role, selection = expected
        _add(codes, route.provider_id == provider, "ROUTE_PROVIDER_MISMATCH")
        _add(codes, route.routing_role == role, "ROUTING_ROLE_INVALID")
        _add(codes, _id(route.owner_model_selection), "OWNER_MODEL_SELECTION_EMPTY")
        _add(codes, route.owner_model_selection == selection, "OWNER_MODEL_SELECTION_MISMATCH")
        expected_profile = primary_profile if level == "L0" else escalation_profile
        _add(codes, route.provider_profile_id == expected_profile.provider_profile_id, "ROUTE_PROVIDER_MISMATCH")
    route_values = tuple(by_level.get(level) for level in ("L0", "L1", "L2"))
    for route in route_values:
        if route is None:
            continue
        _add(codes, _id(route.exact_provider_model_id) or not policy.require_exact_model_id_verification, "EXACT_MODEL_ID_EMPTY")
        _add(codes, route.exact_model_id_verified or not policy.require_exact_model_id_verification, "EXACT_MODEL_ID_NOT_VERIFIED")
    profile_values = (primary_profile, escalation_profile)
    _add(codes, all(profile.API_product_verified for profile in profile_values), "API_PRODUCT_NOT_VERIFIED")
    _add(codes, all(profile.API_version_verified for profile in profile_values), "API_VERSION_NOT_VERIFIED")
    _add(codes, all(profile.endpoint_verified for profile in profile_values), "ENDPOINT_NOT_VERIFIED")
    _add(codes, all(profile.account_verified for profile in profile_values), "PROVIDER_ACCOUNT_NOT_VERIFIED")
    _add(codes, all(profile.permission_scope_verified for profile in profile_values), "PERMISSION_SCOPE_NOT_VERIFIED")
    _add(codes, all(profile.pricing_verified for profile in profile_values), "PRICING_NOT_VERIFIED")
    _add(codes, all(profile.quota_verified for profile in profile_values), "QUOTA_NOT_VERIFIED")
    _add(codes, all(profile.budget_policy_ready for profile in profile_values) and all(route is not None and route.per_request_budget_ready and route.period_budget_ready for route in route_values), "BUDGET_POLICY_NOT_READY")
    _add(codes, all(profile.credential_governance_ready for profile in profile_values), "CREDENTIAL_GOVERNANCE_NOT_READY")
    _add(codes, all(profile.provider_console_revocation_ready for profile in profile_values), "PROVIDER_CONSOLE_REVOCATION_NOT_READY")
    _add(codes, _id(escalation_policy.escalation_policy_id), "ESCALATION_POLICY_ID_EMPTY")
    _add(codes, escalation_policy.policy_id == policy.policy_id and all(route is not None for route in route_values) and (escalation_policy.L0_route_id, escalation_policy.L1_route_id, escalation_policy.L2_route_id) == tuple(route.route_id for route in route_values) and (escalation_policy.L0_provider_id, escalation_policy.L1_provider_id, escalation_policy.L2_provider_id) == ("DEEPSEEK", "ANTHROPIC", "ANTHROPIC"), "ESCALATION_ROUTE_IDENTITY_MISMATCH")
    _add(codes, escalation_policy.L0_to_L2_direct_allowed is False, "DIRECT_L0_TO_L2_NOT_AUTHORIZED")
    _add(codes, escalation_policy.downgrade_allowed is False, "DOWNGRADE_NOT_AUTHORIZED")
    _add(codes, escalation_policy.fallback_provider_allowed is False, "FALLBACK_PROVIDER_NOT_AUTHORIZED")
    _add(codes, escalation_policy.retry_same_level_allowed is False, "SAME_LEVEL_RETRY_NOT_AUTHORIZED")
    _add(codes, escalation_policy.require_explicit_escalation_reason, "ESCALATION_REASON_REQUIRED")
    _add(codes, escalation_policy.require_budget_revalidation_before_escalation, "ESCALATION_BUDGET_REVALIDATION_REQUIRED")
    _add(codes, escalation_policy.require_reservation_before_each_provider_call, "PROVIDER_CALL_RESERVATION_REQUIRED")
    _add(codes, escalation_policy.require_separate_provider_budget, "SEPARATE_PROVIDER_BUDGET_REQUIRED")
    _add(codes, escalation_policy.require_separate_provider_credential_profile, "SEPARATE_PROVIDER_CREDENTIAL_REQUIRED")
    _add(codes, escalation_policy.require_fail_closed_unavailable_route, "UNAVAILABLE_ROUTE_MUST_FAIL_CLOSED")
    owner_valid = not any(code in codes for code in ("PRIMARY_PROVIDER_ID_EMPTY", "ESCALATION_PROVIDER_ID_EMPTY", "PRIMARY_PROVIDER_MISMATCH", "ESCALATION_PROVIDER_MISMATCH", "ROUTE_PROVIDER_MISMATCH", "ROUTING_ROLE_INVALID", "OWNER_MODEL_SELECTION_EMPTY", "OWNER_MODEL_SELECTION_MISMATCH", "L0_ROUTE_REQUIRED", "L1_ROUTE_REQUIRED", "L2_ROUTE_REQUIRED", "ROUTING_LEVEL_DUPLICATE"))
    primary_ready = primary_profile.profile_ready and primary_profile.API_product_verified and primary_profile.API_version_verified and primary_profile.endpoint_verified and primary_profile.account_verified and primary_profile.permission_scope_verified and primary_profile.pricing_verified and primary_profile.quota_verified and primary_profile.budget_policy_ready and primary_profile.credential_governance_ready and primary_profile.provider_console_revocation_ready
    escalation_ready = escalation_profile.profile_ready and primary_ready is not None and all((escalation_profile.API_product_verified, escalation_profile.API_version_verified, escalation_profile.endpoint_verified, escalation_profile.account_verified, escalation_profile.permission_scope_verified, escalation_profile.pricing_verified, escalation_profile.quota_verified, escalation_profile.budget_policy_ready, escalation_profile.credential_governance_ready, escalation_profile.provider_console_revocation_ready))
    route_ready = tuple(route is not None and route.route_ready and route.exact_model_id_verified and route.context_limit_verified and route.capability_verified and route.pricing_verified and route.quota_verified and route.per_request_budget_ready and route.period_budget_ready for route in route_values)
    exact_verified = all(route is not None and route.exact_model_id_verified and _id(route.exact_provider_model_id) for route in route_values)
    products = all(profile.API_product_verified for profile in profile_values); versions = all(profile.API_version_verified for profile in profile_values); endpoints = all(profile.endpoint_verified for profile in profile_values)
    accounts = all(profile.account_verified for profile in profile_values); permissions = all(profile.permission_scope_verified for profile in profile_values); pricing = all(profile.pricing_verified for profile in profile_values); quotas = all(profile.quota_verified for profile in profile_values)
    budgets = all(profile.budget_policy_ready for profile in profile_values) and all(route_ready)
    governance = all(profile.credential_governance_ready for profile in profile_values); revocation = all(profile.provider_console_revocation_ready for profile in profile_values)
    escalation_ready = escalation_ready and escalation_policy.escalation_policy_ready and not any(code in codes for code in ("ESCALATION_POLICY_ID_EMPTY", "ESCALATION_ROUTE_IDENTITY_MISMATCH", "DIRECT_L0_TO_L2_NOT_AUTHORIZED", "DOWNGRADE_NOT_AUTHORIZED", "FALLBACK_PROVIDER_NOT_AUTHORIZED", "SAME_LEVEL_RETRY_NOT_AUTHORIZED", "ESCALATION_REASON_REQUIRED", "ESCALATION_BUDGET_REVALIDATION_REQUIRED", "PROVIDER_CALL_RESERVATION_REQUIRED", "SEPARATE_PROVIDER_BUDGET_REQUIRED", "SEPARATE_PROVIDER_CREDENTIAL_REQUIRED", "UNAVAILABLE_ROUTE_MUST_FAIL_CLOSED"))
    ordered = tuple(sorted(set(codes)))
    return ProviderSelectionReadinessDecisionV1(policy.policy_id, policy.deployment_environment, not ordered, ordered, owner_valid, primary_ready, escalation_ready, route_ready[0], route_ready[1], route_ready[2], escalation_ready, exact_verified, products, versions, endpoints, accounts, permissions, pricing, quotas, budgets, governance, revocation, False, False, False, False, False, False)


def build_provider_selection_audit_evidence_v1(
    policy: ProviderSelectionPolicyV1,
    primary_profile: ProviderProfileV1,
    escalation_profile: ProviderProfileV1,
    routes: tuple[ProviderModelRouteV1, ...],
    escalation_policy: ProviderEscalationPolicyV1,
    decision: ProviderSelectionReadinessDecisionV1,
) -> ProviderSelectionAuditEvidenceV1:
    by_level = {route.routing_level: route for route in routes}
    required = tuple(by_level.get(level) for level in ("L0", "L1", "L2"))
    aligned = (all(route is not None for route in required) and primary_profile.policy_id == policy.policy_id and escalation_profile.policy_id == policy.policy_id and primary_profile.provider_id == "DEEPSEEK" and escalation_profile.provider_id == "ANTHROPIC" and required[0].provider_profile_id == primary_profile.provider_profile_id and required[1].provider_profile_id == escalation_profile.provider_profile_id and required[2].provider_profile_id == escalation_profile.provider_profile_id and escalation_policy.policy_id == policy.policy_id and decision.policy_id == policy.policy_id and decision.deployment_environment == policy.deployment_environment)
    if not aligned:
        raise ValueError("provider selection identity mismatch")
    return ProviderSelectionAuditEvidenceV1(policy.policy_id, policy.deployment_environment, primary_profile.provider_profile_id, escalation_profile.provider_profile_id, required[0].route_id, required[1].route_id, required[2].route_id, required[0].owner_model_selection, required[1].owner_model_selection, required[2].owner_model_selection, decision.exact_model_ids_verified, decision.API_products_verified, decision.API_versions_verified, decision.endpoints_verified, decision.accounts_verified, decision.permission_scopes_verified, decision.pricing_verified, decision.quotas_verified, decision.budgets_ready, decision.credential_governance_ready, decision.provider_console_revocation_ready, decision.escalation_policy_ready, decision.failure_codes, False, False, False, False, False, False)
