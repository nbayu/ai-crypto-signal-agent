"""RED contract for owner-selected provider routing metadata only."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime

import pytest

from engine.phase_12_provider_selection_model_routing_profile_contract_v1 import (
    ProviderEscalationPolicyV1,
    ProviderModelRouteV1,
    ProviderProfileV1,
    ProviderSelectionAuditEvidenceV1,
    ProviderSelectionFailureV1,
    ProviderSelectionPolicyV1,
    ProviderSelectionReadinessDecisionV1,
    build_provider_selection_audit_evidence_v1,
    evaluate_provider_selection_readiness_v1,
)


_NOW = datetime(2030, 1, 7, 12, 0, tzinfo=UTC)
_POLICY = (
    "policy_id", "policy_version", "deployment_environment", "allowed_provider_ids", "allowed_routing_levels",
    "required_primary_provider_id", "required_escalation_provider_id", "require_distinct_primary_and_escalation_providers",
    "require_exact_model_id_verification", "require_api_product_verification", "require_api_version_verification",
    "require_endpoint_verification", "require_account_verification", "require_permission_scope_verification",
    "require_pricing_verification", "require_quota_verification", "require_budget_policy",
    "require_credential_governance", "require_provider_console_revocation_procedure", "require_zero_retry_initially",
    "require_fail_closed_routing", "provider_selection_authorized", "exact_model_binding_authorized",
    "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized",
    "provider_transmission_authorized", "fail_closed",
)
_PROFILE = (
    "provider_profile_id", "policy_id", "provider_id", "provider_role", "owner_selected", "owner_selection_id",
    "API_product_classification", "exact_API_product_id", "API_product_verified", "exact_API_version",
    "API_version_verified", "endpoint_configuration_id", "endpoint_verified", "account_evidence_id",
    "account_verified", "permission_scope_id", "permission_scope_verified", "pricing_evidence_id",
    "pricing_verified", "quota_evidence_id", "quota_verified", "budget_policy_id", "budget_policy_ready",
    "credential_governance_policy_id", "credential_governance_ready", "provider_console_revocation_procedure_id",
    "provider_console_revocation_ready", "profile_ready",
)
_ROUTE = (
    "route_id", "policy_id", "provider_profile_id", "provider_id", "routing_level", "routing_role",
    "owner_model_selection", "exact_provider_model_id", "exact_model_id_verified", "model_family",
    "API_product_classification", "context_limit_evidence_id", "context_limit_verified", "capability_evidence_id",
    "capability_verified", "pricing_evidence_id", "pricing_verified", "quota_evidence_id", "quota_verified",
    "per_request_budget_policy_id", "per_request_budget_ready", "period_budget_policy_id",
    "period_budget_ready", "route_enabled", "route_ready",
)
_ESCALATION = (
    "escalation_policy_id", "policy_id", "L0_route_id", "L1_route_id", "L2_route_id", "L0_provider_id",
    "L1_provider_id", "L2_provider_id", "L0_to_L1_allowed", "L1_to_L2_allowed", "L0_to_L2_direct_allowed",
    "downgrade_allowed", "fallback_provider_allowed", "retry_same_level_allowed", "maximum_escalation_level",
    "require_explicit_escalation_reason", "require_budget_revalidation_before_escalation",
    "require_reservation_before_each_provider_call", "require_separate_provider_budget",
    "require_separate_provider_credential_profile", "require_fail_closed_unavailable_route", "escalation_policy_ready",
)
_DECISION = (
    "policy_id", "deployment_environment", "ready", "failure_codes", "owner_selection_valid",
    "primary_provider_ready", "escalation_provider_ready", "L0_route_ready", "L1_route_ready", "L2_route_ready",
    "escalation_policy_ready", "exact_model_ids_verified", "API_products_verified", "API_versions_verified",
    "endpoints_verified", "accounts_verified", "permission_scopes_verified", "pricing_verified", "quotas_verified",
    "budgets_ready", "credential_governance_ready", "provider_console_revocation_ready",
    "provider_selection_authorized", "exact_model_binding_authorized", "credential_onboarding_authorized",
    "credential_loading_authorized", "network_authorized", "provider_transmission_authorized",
)
_AUDIT = (
    "policy_id", "deployment_environment", "primary_provider_profile_id", "escalation_provider_profile_id",
    "L0_route_id", "L1_route_id", "L2_route_id", "L0_owner_model_selection", "L1_owner_model_selection",
    "L2_owner_model_selection", "exact_model_ids_verified", "API_products_verified", "API_versions_verified",
    "endpoints_verified", "accounts_verified", "permission_scopes_verified", "pricing_verified", "quotas_verified",
    "budgets_ready", "credential_governance_ready", "provider_console_revocation_ready", "escalation_policy_ready",
    "failure_codes", "provider_selection_authorized", "exact_model_binding_authorized",
    "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized",
    "provider_transmission_authorized",
)
_FAILURE = ("failure_code", "safe_message", "retryable")
_CODES = {
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED",
    "PRIMARY_PROVIDER_ID_EMPTY", "ESCALATION_PROVIDER_ID_EMPTY", "PRIMARY_PROVIDER_MISMATCH",
    "ESCALATION_PROVIDER_MISMATCH", "PROVIDER_NOT_ALLOWED", "PROVIDER_PROFILE_ID_EMPTY", "PROVIDER_ROLE_INVALID",
    "OWNER_SELECTION_ID_EMPTY", "OWNER_SELECTION_NOT_APPROVED", "ROUTE_ID_EMPTY", "ROUTING_LEVEL_EMPTY",
    "ROUTING_LEVEL_INVALID", "ROUTING_LEVEL_DUPLICATE", "ROUTING_ROLE_INVALID", "OWNER_MODEL_SELECTION_EMPTY",
    "OWNER_MODEL_SELECTION_MISMATCH", "ROUTE_PROVIDER_MISMATCH", "L0_ROUTE_REQUIRED", "L1_ROUTE_REQUIRED",
    "L2_ROUTE_REQUIRED", "EXACT_MODEL_ID_EMPTY", "EXACT_MODEL_ID_NOT_VERIFIED", "API_PRODUCT_NOT_VERIFIED",
    "API_VERSION_NOT_VERIFIED", "ENDPOINT_NOT_VERIFIED", "PROVIDER_ACCOUNT_NOT_VERIFIED",
    "PERMISSION_SCOPE_NOT_VERIFIED", "PRICING_NOT_VERIFIED", "QUOTA_NOT_VERIFIED", "BUDGET_POLICY_NOT_READY",
    "CREDENTIAL_GOVERNANCE_NOT_READY", "PROVIDER_CONSOLE_REVOCATION_NOT_READY", "ESCALATION_POLICY_ID_EMPTY",
    "ESCALATION_ROUTE_IDENTITY_MISMATCH", "DIRECT_L0_TO_L2_NOT_AUTHORIZED", "DOWNGRADE_NOT_AUTHORIZED",
    "FALLBACK_PROVIDER_NOT_AUTHORIZED", "SAME_LEVEL_RETRY_NOT_AUTHORIZED", "ESCALATION_REASON_REQUIRED",
    "ESCALATION_BUDGET_REVALIDATION_REQUIRED", "PROVIDER_CALL_RESERVATION_REQUIRED",
    "SEPARATE_PROVIDER_BUDGET_REQUIRED", "SEPARATE_PROVIDER_CREDENTIAL_REQUIRED",
    "UNAVAILABLE_ROUTE_MUST_FAIL_CLOSED", "PROVIDER_SELECTION_NOT_AUTHORIZED",
    "EXACT_MODEL_BINDING_NOT_AUTHORIZED", "CREDENTIAL_ONBOARDING_NOT_AUTHORIZED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_ENDPOINT_EXPOSURE_DETECTED", "RAW_ACCOUNT_DATA_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
}
_FORBIDDEN = {"api_key", "credential", "token", "authorization", "header", "secret", "response", "exception"}


def _frozen(value: object) -> None:
    assert is_dataclass(value) and type(value).__dataclass_params__.frozen
    assert "__dict__" not in type(value).__slots__


def _policy(**changes: object) -> ProviderSelectionPolicyV1:
    values = dict(policy_id="provider-selection-policy-v1", policy_version="V1", deployment_environment="CONTROLLED_PRODUCTION",
                  allowed_provider_ids=("DEEPSEEK", "ANTHROPIC"), allowed_routing_levels=("L0", "L1", "L2"),
                  required_primary_provider_id="DEEPSEEK", required_escalation_provider_id="ANTHROPIC",
                  require_distinct_primary_and_escalation_providers=True, require_exact_model_id_verification=True,
                  require_api_product_verification=True, require_api_version_verification=True, require_endpoint_verification=True,
                  require_account_verification=True, require_permission_scope_verification=True, require_pricing_verification=True,
                  require_quota_verification=True, require_budget_policy=True, require_credential_governance=True,
                  require_provider_console_revocation_procedure=True, require_zero_retry_initially=True,
                  require_fail_closed_routing=True, provider_selection_authorized=False, exact_model_binding_authorized=False,
                  credential_onboarding_authorized=False, credential_loading_authorized=False, network_authorized=False,
                  provider_transmission_authorized=False, fail_closed=True)
    values.update(changes)
    return ProviderSelectionPolicyV1(**values)


def _profile(provider: str, role: str, **changes: object) -> ProviderProfileV1:
    values = dict(provider_profile_id=f"{provider.lower()}-profile-v1", policy_id="provider-selection-policy-v1", provider_id=provider,
                  provider_role=role, owner_selected=True, owner_selection_id="owner-provider-routing-v1",
                  API_product_classification="UNVERIFIED_API_PRODUCT", exact_API_product_id="", API_product_verified=False,
                  exact_API_version="", API_version_verified=False, endpoint_configuration_id="endpoint-metadata-v1",
                  endpoint_verified=False, account_evidence_id="account-evidence-v1", account_verified=False,
                  permission_scope_id="permission-scope-v1", permission_scope_verified=False,
                  pricing_evidence_id="pricing-evidence-v1", pricing_verified=False, quota_evidence_id="quota-evidence-v1",
                  quota_verified=False, budget_policy_id="budget-policy-v1", budget_policy_ready=False,
                  credential_governance_policy_id="credential-governance-policy-v1", credential_governance_ready=False,
                  provider_console_revocation_procedure_id="console-revocation-v1", provider_console_revocation_ready=False,
                  profile_ready=False)
    values.update(changes)
    return ProviderProfileV1(**values)


def _route(level: str, provider: str, role: str, selection: str, **changes: object) -> ProviderModelRouteV1:
    values = dict(route_id=f"{level.lower()}-route-v1", policy_id="provider-selection-policy-v1",
                  provider_profile_id=f"{provider.lower()}-profile-v1", provider_id=provider, routing_level=level,
                  routing_role=role, owner_model_selection=selection, exact_provider_model_id="",
                  exact_model_id_verified=False, model_family=selection, API_product_classification="UNVERIFIED_API_PRODUCT",
                  context_limit_evidence_id="context-evidence-v1", context_limit_verified=False,
                  capability_evidence_id="capability-evidence-v1", capability_verified=False,
                  pricing_evidence_id="pricing-evidence-v1", pricing_verified=False, quota_evidence_id="quota-evidence-v1",
                  quota_verified=False, per_request_budget_policy_id="request-budget-v1", per_request_budget_ready=False,
                  period_budget_policy_id="period-budget-v1", period_budget_ready=False, route_enabled=True, route_ready=False)
    values.update(changes)
    return ProviderModelRouteV1(**values)


def _routes(**changes: object) -> tuple[ProviderModelRouteV1, ...]:
    routes = (
        _route("L0", "DEEPSEEK", "PRIMARY_LIVE_REVIEW", "DEEPSEEK_V4_PRO"),
        _route("L1", "ANTHROPIC", "ESCALATED_REVIEW", "CLAUDE_SONNET_5"),
        _route("L2", "ANTHROPIC", "HIGHEST_ESCALATION_REVIEW", "CLAUDE_OPUS_4_8"),
    )
    return changes.get("routes", routes)  # type: ignore[return-value]


def _escalation(**changes: object) -> ProviderEscalationPolicyV1:
    values = dict(escalation_policy_id="escalation-policy-v1", policy_id="provider-selection-policy-v1",
                  L0_route_id="l0-route-v1", L1_route_id="l1-route-v1", L2_route_id="l2-route-v1",
                  L0_provider_id="DEEPSEEK", L1_provider_id="ANTHROPIC", L2_provider_id="ANTHROPIC",
                  L0_to_L1_allowed=True, L1_to_L2_allowed=True, L0_to_L2_direct_allowed=False,
                  downgrade_allowed=False, fallback_provider_allowed=False, retry_same_level_allowed=False,
                  maximum_escalation_level="L2", require_explicit_escalation_reason=True,
                  require_budget_revalidation_before_escalation=True, require_reservation_before_each_provider_call=True,
                  require_separate_provider_budget=True, require_separate_provider_credential_profile=True,
                  require_fail_closed_unavailable_route=True, escalation_policy_ready=True)
    values.update(changes)
    return ProviderEscalationPolicyV1(**values)


def _evaluate(**changes: object) -> ProviderSelectionReadinessDecisionV1:
    return evaluate_provider_selection_readiness_v1(_policy(**changes), _profile("DEEPSEEK", "PRIMARY"), _profile("ANTHROPIC", "ESCALATION"), _routes(), _escalation())


def test_public_contract_is_immutable_redacted_and_zero_authority() -> None:
    schemas = ((ProviderSelectionPolicyV1, _POLICY), (ProviderProfileV1, _PROFILE), (ProviderModelRouteV1, _ROUTE),
               (ProviderEscalationPolicyV1, _ESCALATION), (ProviderSelectionReadinessDecisionV1, _DECISION),
               (ProviderSelectionAuditEvidenceV1, _AUDIT), (ProviderSelectionFailureV1, _FAILURE))
    decision = _evaluate()
    audit = build_provider_selection_audit_evidence_v1(_policy(), _profile("DEEPSEEK", "PRIMARY"), _profile("ANTHROPIC", "ESCALATION"), _routes(), _escalation(), decision)
    for schema, expected in schemas:
        assert tuple(field.name for field in fields(schema)) == expected
        assert not _FORBIDDEN.intersection(field.name for field in fields(schema))
    for value in (_policy(), _profile("DEEPSEEK", "PRIMARY"), _routes()[0], _escalation(), decision, audit):
        _frozen(value)
    with pytest.raises(FrozenInstanceError):
        decision.network_authorized = True  # type: ignore[misc]


def test_owner_selection_is_frozen_but_initial_operational_evidence_is_not_ready() -> None:
    routes = _routes()
    assert tuple((route.routing_level, route.provider_id, route.routing_role, route.owner_model_selection) for route in routes) == (
        ("L0", "DEEPSEEK", "PRIMARY_LIVE_REVIEW", "DEEPSEEK_V4_PRO"),
        ("L1", "ANTHROPIC", "ESCALATED_REVIEW", "CLAUDE_SONNET_5"),
        ("L2", "ANTHROPIC", "HIGHEST_ESCALATION_REVIEW", "CLAUDE_OPUS_4_8"),
    )
    decision = _evaluate()
    assert decision.owner_selection_valid and not decision.ready
    assert not any((decision.primary_provider_ready, decision.escalation_provider_ready, decision.L0_route_ready,
                    decision.L1_route_ready, decision.L2_route_ready, decision.exact_model_ids_verified,
                    decision.API_products_verified, decision.API_versions_verified, decision.endpoints_verified,
                    decision.accounts_verified, decision.permission_scopes_verified, decision.pricing_verified,
                    decision.quotas_verified, decision.budgets_ready, decision.credential_governance_ready,
                    decision.provider_console_revocation_ready))
    assert {"EXACT_MODEL_ID_NOT_VERIFIED", "API_PRODUCT_NOT_VERIFIED", "API_VERSION_NOT_VERIFIED",
            "ENDPOINT_NOT_VERIFIED", "PROVIDER_ACCOUNT_NOT_VERIFIED", "PRICING_NOT_VERIFIED"}.issubset(decision.failure_codes)


def test_substitution_duplicate_route_and_escalation_weakening_fail_closed() -> None:
    wrong_routes = _routes(routes=(
        _route("L0", "ANTHROPIC", "PRIMARY_LIVE_REVIEW", "DEEPSEEK_V4_PRO"),
        _route("L1", "ANTHROPIC", "ESCALATED_REVIEW", "CLAUDE_SONNET_5"),
        _route("L1", "ANTHROPIC", "HIGHEST_ESCALATION_REVIEW", "CLAUDE_OPUS_4_8"),
    ))
    decision = evaluate_provider_selection_readiness_v1(_policy(), _profile("DEEPSEEK", "PRIMARY"), _profile("ANTHROPIC", "ESCALATION"), wrong_routes, _escalation(fallback_provider_allowed=True, retry_same_level_allowed=True, require_budget_revalidation_before_escalation=False))
    required = {"ROUTE_PROVIDER_MISMATCH", "ROUTING_LEVEL_DUPLICATE", "L2_ROUTE_REQUIRED",
                "FALLBACK_PROVIDER_NOT_AUTHORIZED", "SAME_LEVEL_RETRY_NOT_AUTHORIZED",
                "ESCALATION_BUDGET_REVALIDATION_REQUIRED"}
    assert required.issubset(decision.failure_codes)
    assert decision.failure_codes == tuple(sorted(decision.failure_codes))
    assert set(decision.failure_codes).issubset(_CODES)
    assert not decision.ready


def test_verified_synthetic_profile_is_only_ready_for_separate_authorization_and_audit_is_bound() -> None:
    verified = dict(exact_API_product_id="api-product-v1", API_product_verified=True, exact_API_version="api-version-v1",
                    API_version_verified=True, endpoint_verified=True, account_verified=True, permission_scope_verified=True,
                    pricing_verified=True, quota_verified=True, budget_policy_ready=True, credential_governance_ready=True,
                    provider_console_revocation_ready=True, profile_ready=True)
    route_changes = dict(exact_provider_model_id="provider-model-v1", exact_model_id_verified=True,
                         context_limit_verified=True, capability_verified=True, pricing_verified=True, quota_verified=True,
                         per_request_budget_ready=True, period_budget_ready=True, route_ready=True)
    policy, primary, escalation = _policy(), _profile("DEEPSEEK", "PRIMARY", **verified), _profile("ANTHROPIC", "ESCALATION", **verified)
    routes = tuple(_route(level, provider, role, selection, **route_changes) for level, provider, role, selection in (
        ("L0", "DEEPSEEK", "PRIMARY_LIVE_REVIEW", "DEEPSEEK_V4_PRO"),
        ("L1", "ANTHROPIC", "ESCALATED_REVIEW", "CLAUDE_SONNET_5"),
        ("L2", "ANTHROPIC", "HIGHEST_ESCALATION_REVIEW", "CLAUDE_OPUS_4_8"),
    ))
    decision = evaluate_provider_selection_readiness_v1(policy, primary, escalation, routes, _escalation())
    assert decision.ready and not any((decision.provider_selection_authorized, decision.exact_model_binding_authorized,
                                       decision.credential_onboarding_authorized, decision.credential_loading_authorized,
                                       decision.network_authorized, decision.provider_transmission_authorized))
    first = build_provider_selection_audit_evidence_v1(policy, primary, escalation, routes, _escalation(), decision)
    assert first == build_provider_selection_audit_evidence_v1(policy, primary, escalation, routes, _escalation(), decision)
    with pytest.raises(ValueError):
        build_provider_selection_audit_evidence_v1(policy, _profile("ANTHROPIC", "PRIMARY", **verified), escalation, routes, _escalation(), decision)
