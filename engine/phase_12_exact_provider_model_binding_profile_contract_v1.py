"""Pure, redacted metadata validation for exact provider model bindings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExactProviderModelBindingPolicyV1:
    policy_id: str = ""
    policy_version: str = ""
    deployment_environment: str = ""
    allowed_provider_ids: tuple[str, ...] = ()
    allowed_routing_levels: tuple[str, ...] = ()
    required_L0_provider_id: str = ""
    required_L1_provider_id: str = ""
    required_L2_provider_id: str = ""
    required_L0_owner_model_selection: str = ""
    required_L1_owner_model_selection: str = ""
    required_L2_owner_model_selection: str = ""
    required_L0_exact_model_id: str = ""
    required_L1_exact_model_id: str = ""
    required_L2_exact_model_id: str = ""
    require_official_documentation_evidence: bool = True
    require_exact_model_id_proven: bool = True
    require_API_product_evidence: bool = True
    require_API_version_evidence_or_explicit_unresolved_state: bool = True
    require_endpoint_classification: bool = True
    require_availability_classification: bool = True
    require_context_limit_evidence: bool = True
    require_output_limit_evidence: bool = True
    require_capability_evidence: bool = True
    require_account_access_classification: bool = True
    require_pricing_evidence: bool = True
    require_pricing_effective_date: bool = True
    require_pricing_revalidation_before_use: bool = True
    require_evidence_retrieval_timestamp: bool = True
    require_evidence_freshness: bool = True
    maximum_evidence_age_days: int = 0
    require_fail_closed_expired_evidence: bool = True
    require_no_model_substitution: bool = True
    require_no_alias_inference: bool = True
    require_no_provider_substitution: bool = True
    require_no_live_authority: bool = True
    exact_model_binding_authorized: bool = False
    account_verification_authorized: bool = False
    credential_onboarding_authorized: bool = False
    credential_loading_authorized: bool = False
    network_authorized: bool = False
    provider_transmission_authorized: bool = False
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class ProviderDocumentationEvidenceV1:
    documentation_evidence_id: str
    provider_id: str
    official_domain_classification: str
    page_title: str
    page_category: str
    section_heading: str
    retrieval_timestamp: datetime | None
    publication_or_effective_date: datetime | None
    current_or_archived: str
    supports_model_label: bool
    supports_exact_model_id: bool
    supports_API_product: bool
    supports_API_version: bool
    supports_endpoint_classification: bool
    supports_availability: bool
    supports_context_limit: bool
    supports_output_limit: bool
    supports_capabilities: bool
    supports_pricing: bool
    supports_account_access: bool
    evidence_complete: bool
    evidence_expired: bool
    redacted: bool


@dataclass(frozen=True, slots=True)
class ExactProviderModelBindingV1:
    binding_id: str
    policy_id: str
    route_id: str
    routing_level: str
    routing_role: str
    provider_id: str
    owner_model_selection: str
    exact_provider_model_id: str
    model_binding_classification: str
    official_label_proven: bool
    exact_model_id_proven: bool
    API_product: str
    API_interface_classification: str
    API_version_mechanism: str
    API_version_status: str
    endpoint_classification: str
    availability_classification: str
    snapshot_or_alias_status: str
    context_limit_tokens: int
    maximum_output_tokens: int
    capability_classifications: tuple[str, ...]
    documentation_evidence_ids: tuple[str, ...]
    account_access_classification: str
    unresolved_fields: tuple[str, ...]
    pricing_evidence_snapshot_id: str
    pricing_revalidation_required: bool
    account_verification_required: bool
    binding_ready: bool


@dataclass(frozen=True, slots=True)
class ProviderPricingEvidenceSnapshotV1:
    pricing_evidence_snapshot_id: str
    provider_id: str
    exact_provider_model_id: str
    currency: str
    pricing_unit: str
    input_price: Decimal
    cached_input_price: Decimal | None
    cache_write_price_short: Decimal | None
    cache_write_price_long: Decimal | None
    cache_read_price: Decimal | None
    output_price: Decimal
    price_effective_from: datetime | None
    price_effective_until: datetime | None
    evidence_retrieved_at: datetime | None
    provider_states_prices_may_change: bool
    pricing_complete: bool
    pricing_expired: bool
    pricing_revalidation_required: bool
    redacted: bool


@dataclass(frozen=True, slots=True)
class ExactProviderModelBindingFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class ExactProviderModelBindingDecisionV1:
    policy_id: str
    deployment_environment: str
    ready: bool
    failure_codes: tuple[str, ...]
    owner_routing_preserved: bool
    L0_exact_model_binding_proven: bool
    L1_exact_model_binding_proven: bool
    L2_exact_model_binding_proven: bool
    all_exact_model_ids_proven: bool
    API_products_proven: bool
    API_versions_resolved: bool
    endpoint_classifications_proven: bool
    availability_classifications_proven: bool
    context_limits_proven: bool
    output_limits_proven: bool
    capabilities_proven: bool
    pricing_evidence_present: bool
    pricing_evidence_fresh: bool
    account_requirements_resolved: bool
    unresolved_fields_present: bool
    evidence_fresh: bool
    exact_model_binding_authorized: bool
    account_verification_authorized: bool
    credential_onboarding_authorized: bool
    credential_loading_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool


@dataclass(frozen=True, slots=True)
class ExactProviderModelBindingAuditEvidenceV1:
    policy_id: str
    deployment_environment: str
    L0_provider_id: str
    L1_provider_id: str
    L2_provider_id: str
    L0_owner_model_selection: str
    L1_owner_model_selection: str
    L2_owner_model_selection: str
    L0_exact_provider_model_id: str
    L1_exact_provider_model_id: str
    L2_exact_provider_model_id: str
    all_exact_model_ids_proven: bool
    documentation_evidence_ids: tuple[str, ...]
    API_products_proven: bool
    API_versions_resolved: bool
    endpoint_classifications_proven: bool
    availability_classifications_proven: bool
    context_limits_proven: bool
    output_limits_proven: bool
    capabilities_proven: bool
    unresolved_fields: tuple[tuple[str, tuple[str, ...]], ...]
    pricing_evidence_snapshot_ids: tuple[str, ...]
    pricing_evidence_fresh: bool
    account_access_classifications: tuple[str, ...]
    failure_codes: tuple[str, ...]
    exact_model_binding_authorized: bool
    account_verification_authorized: bool
    credential_onboarding_authorized: bool
    credential_loading_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool


_EXPECTED = {
    "L0": ("DEEPSEEK", "PRIMARY_LIVE_REVIEW", "DEEPSEEK_V4_PRO", "deepseek-v4-pro", "CHAT_COMPLETIONS", "OPENAI_COMPATIBLE_CHAT_COMPLETIONS", "UNRESOLVED", "UNRESOLVED", "PUBLIC_API_PREVIEW_DOCUMENTED", "NOT_PROVEN", 1000000, 384000),
    "L1": ("ANTHROPIC", "ESCALATED_REVIEW", "CLAUDE_SONNET_5", "claude-sonnet-5", "MESSAGES_API", "MESSAGES_API", "ANTHROPIC_VERSION_HEADER", "PROVEN", "PUBLICLY_DOCUMENTED_STANDARD_ACCESS", "PINNED_CANONICAL_ID", 1000000, 128000),
    "L2": ("ANTHROPIC", "HIGHEST_ESCALATION_REVIEW", "CLAUDE_OPUS_4_8", "claude-opus-4-8", "MESSAGES_API", "MESSAGES_API", "ANTHROPIC_VERSION_HEADER", "PROVEN", "PUBLIC_CURRENT_MODEL_DOCUMENTED", "PINNED_CANONICAL_ID", 1000000, 128000),
}
_REQUIRED_UNRESOLVED = {
    "L0": ("API_VERSION_MECHANISM", "FIXED_SNAPSHOT_SEMANTICS", "FORMAL_GA_STATUS", "ACCOUNT_ACCESS_CLASSIFICATION"),
    "L1": ("ACCOUNT_ENTITLEMENT", "RATE_LIMIT_TIER", "BILLING_CONFIGURATION", "REGION_OR_ENDPOINT_SELECTION", "PERMISSION_SCOPE"),
    "L2": ("ACCOUNT_ENTITLEMENT", "RATE_LIMIT_TIER", "BILLING_CONFIGURATION", "REGION_OR_ENDPOINT_SELECTION", "PERMISSION_SCOPE"),
}


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _add(codes: list[str], condition: bool, code: str) -> None:
    if not condition:
        codes.append(code)


def _policy_expected(policy: ExactProviderModelBindingPolicyV1, codes: list[str]) -> None:
    _add(codes, _identifier(policy.policy_id), "POLICY_ID_EMPTY")
    _add(codes, _identifier(policy.policy_version), "POLICY_VERSION_EMPTY")
    _add(codes, _identifier(policy.deployment_environment), "DEPLOYMENT_ENVIRONMENT_EMPTY")
    _add(codes, policy.deployment_environment == "CONTROLLED_PRODUCTION", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED")
    _add(codes, set(("DEEPSEEK", "ANTHROPIC")).issubset(policy.allowed_provider_ids), "PROVIDER_NOT_ALLOWED")
    _add(codes, set(("L0", "L1", "L2")).issubset(policy.allowed_routing_levels), "ROUTING_LEVEL_NOT_ALLOWED")
    values = (
        policy.required_L0_provider_id, policy.required_L1_provider_id, policy.required_L2_provider_id,
        policy.required_L0_owner_model_selection, policy.required_L1_owner_model_selection, policy.required_L2_owner_model_selection,
        policy.required_L0_exact_model_id, policy.required_L1_exact_model_id, policy.required_L2_exact_model_id,
    )
    expected = ("DEEPSEEK", "ANTHROPIC", "ANTHROPIC", "DEEPSEEK_V4_PRO", "CLAUDE_SONNET_5", "CLAUDE_OPUS_4_8", "deepseek-v4-pro", "claude-sonnet-5", "claude-opus-4-8")
    _add(codes, values == expected, "PROVIDER_ID_MISMATCH")
    _add(codes, isinstance(policy.maximum_evidence_age_days, int) and not isinstance(policy.maximum_evidence_age_days, bool) and policy.maximum_evidence_age_days >= 0, "EVIDENCE_AGE_INVALID")


def _binding_validity(
    policy: ExactProviderModelBindingPolicyV1,
    binding: ExactProviderModelBindingV1,
    codes: list[str],
) -> bool:
    expected = _EXPECTED.get(binding.routing_level)
    _add(codes, _identifier(binding.binding_id), "BINDING_ID_EMPTY")
    _add(codes, _identifier(binding.route_id), "ROUTE_ID_EMPTY")
    _add(codes, binding.policy_id == policy.policy_id, "DOCUMENTATION_EVIDENCE_IDENTITY_MISMATCH")
    _add(codes, expected is not None, "ROUTING_LEVEL_MISMATCH")
    if expected is None:
        return False
    provider, role, selection, model_id, product, interface, mechanism, version_status, availability, snapshot, context, output = expected
    _add(codes, binding.provider_id == provider, "PROVIDER_ID_MISMATCH")
    _add(codes, binding.routing_role == role, "ROUTING_ROLE_MISMATCH")
    _add(codes, binding.owner_model_selection == selection, "OWNER_MODEL_SELECTION_MISMATCH")
    _add(codes, _identifier(binding.exact_provider_model_id), "EXACT_MODEL_ID_EMPTY")
    exact_match = binding.exact_provider_model_id == model_id
    _add(codes, exact_match, "EXACT_MODEL_ID_MISMATCH")
    _add(codes, exact_match, "MODEL_SUBSTITUTION_DETECTED")
    _add(codes, binding.exact_model_id_proven and binding.model_binding_classification == "EXACT_MODEL_ID_PROVEN", "EXACT_MODEL_ID_NOT_PROVEN")
    _add(codes, binding.snapshot_or_alias_status != "INFERRED_ALIAS", "ALIAS_INFERENCE_FORBIDDEN")
    _add(codes, binding.API_product == product and binding.API_interface_classification == interface, "API_PRODUCT_NOT_PROVEN")
    _add(codes, binding.endpoint_classification == "PUBLIC_API_ENDPOINT_CLASSIFICATION", "ENDPOINT_CLASSIFICATION_NOT_PROVEN")
    _add(codes, binding.availability_classification == availability, "AVAILABILITY_NOT_PROVEN")
    _add(codes, binding.context_limit_tokens == context and not isinstance(binding.context_limit_tokens, bool), "CONTEXT_LIMIT_NOT_PROVEN")
    _add(codes, binding.maximum_output_tokens == output and not isinstance(binding.maximum_output_tokens, bool), "OUTPUT_LIMIT_NOT_PROVEN")
    _add(codes, bool(binding.capability_classifications), "CAPABILITY_EVIDENCE_NOT_PROVEN")
    return exact_match and binding.exact_model_id_proven


def _documentation_validity(
    policy: ExactProviderModelBindingPolicyV1,
    evidence: ProviderDocumentationEvidenceV1,
    evaluated_at: datetime,
    codes: list[str],
) -> bool:
    _add(codes, _identifier(evidence.documentation_evidence_id), "DOCUMENTATION_EVIDENCE_REQUIRED")
    _add(codes, evidence.official_domain_classification == "OFFICIAL_PROVIDER_DOCUMENTATION", "OFFICIAL_SOURCE_REQUIRED")
    _add(codes, evidence.evidence_complete and evidence.redacted, "DOCUMENTATION_EVIDENCE_REQUIRED")
    _add(codes, evidence.supports_model_label, "OFFICIAL_LABEL_NOT_PROVEN")
    _add(codes, evidence.supports_exact_model_id, "EXACT_MODEL_ID_NOT_PROVEN")
    _add(codes, evidence.supports_API_product, "API_PRODUCT_NOT_PROVEN")
    _add(codes, evidence.supports_endpoint_classification, "ENDPOINT_CLASSIFICATION_NOT_PROVEN")
    _add(codes, evidence.supports_availability, "AVAILABILITY_NOT_PROVEN")
    _add(codes, evidence.supports_context_limit, "CONTEXT_LIMIT_NOT_PROVEN")
    _add(codes, evidence.supports_output_limit, "OUTPUT_LIMIT_NOT_PROVEN")
    _add(codes, evidence.supports_capabilities, "CAPABILITY_EVIDENCE_NOT_PROVEN")
    if evidence.retrieval_timestamp is None:
        codes.append("RETRIEVAL_TIME_INCOMPLETE")
        if policy.require_evidence_retrieval_timestamp:
            codes.append("RETRIEVAL_TIMESTAMP_REQUIRED")
        return False
    if evidence.retrieval_timestamp > evaluated_at:
        codes.append("EVIDENCE_FROM_FUTURE")
        return False
    age = (evaluated_at - evidence.retrieval_timestamp).days
    _add(codes, age >= 0 and age <= policy.maximum_evidence_age_days, "EVIDENCE_AGE_INVALID")
    _add(codes, not evidence.evidence_expired, "EVIDENCE_EXPIRED")
    return age >= 0 and age <= policy.maximum_evidence_age_days and not evidence.evidence_expired


def _pricing_validity(
    binding: ExactProviderModelBindingV1,
    pricing: ProviderPricingEvidenceSnapshotV1 | None,
    evaluated_at: datetime,
    codes: list[str],
) -> bool:
    if pricing is None:
        codes.append("PRICING_EVIDENCE_REQUIRED")
        return False
    _add(codes, pricing.pricing_evidence_snapshot_id == binding.pricing_evidence_snapshot_id and pricing.provider_id == binding.provider_id and pricing.exact_provider_model_id == binding.exact_provider_model_id, "PRICING_EVIDENCE_IDENTITY_MISMATCH")
    _add(codes, _identifier(pricing.currency) and _identifier(pricing.pricing_unit), "PRICING_EVIDENCE_REQUIRED")
    values = (pricing.input_price, pricing.cached_input_price, pricing.cache_write_price_short, pricing.cache_write_price_long, pricing.cache_read_price, pricing.output_price)
    valid_prices = all(value is None or (isinstance(value, Decimal) and value >= Decimal("0")) for value in values)
    _add(codes, valid_prices, "PRICING_EVIDENCE_REQUIRED")
    if pricing.price_effective_from is None or pricing.price_effective_until is None or pricing.evidence_retrieved_at is None:
        codes.append("PRICING_EFFECTIVE_DATE_REQUIRED")
        return False
    _add(codes, pricing.price_effective_from <= pricing.price_effective_until, "PRICING_EFFECTIVE_WINDOW_INVALID")
    _add(codes, pricing.evidence_retrieved_at <= evaluated_at, "EVIDENCE_FROM_FUTURE")
    expired = pricing.pricing_expired or evaluated_at > pricing.price_effective_until
    _add(codes, not expired, "PRICING_EVIDENCE_EXPIRED")
    _add(codes, pricing.pricing_complete and pricing.redacted, "PRICING_EVIDENCE_REQUIRED")
    _add(codes, pricing.pricing_revalidation_required and binding.pricing_revalidation_required, "PRICING_REVALIDATION_REQUIRED")
    return valid_prices and pricing.price_effective_from <= pricing.price_effective_until and not expired and pricing.pricing_complete and pricing.redacted


def evaluate_exact_provider_model_binding_v1(
    policy: ExactProviderModelBindingPolicyV1,
    documentation_evidence: tuple[ProviderDocumentationEvidenceV1, ...],
    bindings: tuple[ExactProviderModelBindingV1, ...],
    pricing_evidence: tuple[ProviderPricingEvidenceSnapshotV1, ...],
    evaluated_at: datetime,
) -> ExactProviderModelBindingDecisionV1:
    codes: list[str] = []
    _policy_expected(policy, codes)
    _add(codes, isinstance(evaluated_at, datetime), "EVIDENCE_AGE_INVALID")
    by_level: dict[str, ExactProviderModelBindingV1] = {}
    for binding in bindings:
        if binding.routing_level in by_level:
            codes.append("ROUTING_LEVEL_MISMATCH")
        else:
            by_level[binding.routing_level] = binding
    levels = tuple(by_level.get(level) for level in ("L0", "L1", "L2"))
    binding_proven: list[bool] = []
    for binding in levels:
        if binding is None:
            codes.append("ROUTING_LEVEL_MISMATCH")
            binding_proven.append(False)
        else:
            binding_proven.append(_binding_validity(policy, binding, codes))
    evidence_by_id = {item.documentation_evidence_id: item for item in documentation_evidence}
    freshness: list[bool] = []
    for binding in levels:
        if binding is None:
            freshness.append(False)
            continue
        _add(codes, bool(binding.documentation_evidence_ids), "DOCUMENTATION_EVIDENCE_REQUIRED")
        referenced = tuple(evidence_by_id.get(item) for item in binding.documentation_evidence_ids)
        _add(codes, all(item is not None for item in referenced), "DOCUMENTATION_EVIDENCE_IDENTITY_MISMATCH")
        valid = True
        for item in referenced:
            if item is None:
                valid = False
            else:
                _add(codes, item.provider_id == binding.provider_id, "DOCUMENTATION_EVIDENCE_IDENTITY_MISMATCH")
                valid = _documentation_validity(policy, item, evaluated_at, codes) and valid
        freshness.append(valid)
    pricing_by_id = {item.pricing_evidence_snapshot_id: item for item in pricing_evidence}
    pricing_fresh = [
        _pricing_validity(binding, pricing_by_id.get(binding.pricing_evidence_snapshot_id), evaluated_at, codes) if binding is not None else False
        for binding in levels
    ]
    unresolved_present = False
    accounts_resolved = True
    versions_resolved = True
    for binding in levels:
        if binding is None:
            unresolved_present = True
            accounts_resolved = False
            versions_resolved = False
            continue
        required = _REQUIRED_UNRESOLVED[binding.routing_level]
        fields_normalized = tuple(sorted(set(binding.unresolved_fields))) == binding.unresolved_fields and all(_identifier(item) for item in binding.unresolved_fields)
        _add(codes, fields_normalized, "UNRESOLVED_FIELD_NOT_DECLARED")
        if binding.routing_level == "L0":
            _add(codes, set(required).issubset(binding.unresolved_fields), "UNRESOLVED_FIELD_NOT_DECLARED")
            _add(codes, binding.API_version_status == "UNRESOLVED", "API_VERSION_UNRESOLVED")
        else:
            _add(codes, set(required).issubset(binding.unresolved_fields), "UNRESOLVED_FIELD_NOT_DECLARED")
            _add(codes, binding.API_version_status == "PROVEN" and binding.API_version_mechanism == "ANTHROPIC_VERSION_HEADER", "API_VERSION_UNRESOLVED")
        if binding.unresolved_fields:
            unresolved_present = True
            accounts_resolved = False
            codes.append("ACCOUNT_ACCESS_UNRESOLVED")
        if binding.API_version_status != "PROVEN":
            versions_resolved = False
            codes.append("API_VERSION_UNRESOLVED")
        _add(codes, binding.account_access_classification != "ACCOUNT_ACCESS_VERIFIED", "ACCOUNT_ACCESS_UNRESOLVED")
    all_exact = all(binding_proven)
    products = all(binding is not None and binding.API_product == _EXPECTED[binding.routing_level][4] for binding in levels)
    endpoints = all(binding is not None and binding.endpoint_classification == "PUBLIC_API_ENDPOINT_CLASSIFICATION" for binding in levels)
    availability = all(binding is not None and binding.availability_classification == _EXPECTED[binding.routing_level][8] for binding in levels)
    contexts = all(binding is not None and binding.context_limit_tokens == _EXPECTED[binding.routing_level][10] for binding in levels)
    outputs = all(binding is not None and binding.maximum_output_tokens == _EXPECTED[binding.routing_level][11] for binding in levels)
    capabilities = all(binding is not None and bool(binding.capability_classifications) for binding in levels)
    evidence_fresh = all(freshness)
    pricing_present = all(binding is not None and binding.pricing_evidence_snapshot_id in pricing_by_id for binding in levels)
    pricing_is_fresh = all(pricing_fresh)
    owner_routing = all_exact and not any(code in codes for code in ("ROUTING_LEVEL_MISMATCH", "ROUTING_ROLE_MISMATCH", "PROVIDER_ID_MISMATCH", "OWNER_MODEL_SELECTION_MISMATCH", "EXACT_MODEL_ID_MISMATCH"))
    ordered = tuple(sorted(set(codes)))
    return ExactProviderModelBindingDecisionV1(
        policy.policy_id, policy.deployment_environment, not ordered, ordered, owner_routing,
        binding_proven[0], binding_proven[1], binding_proven[2], all_exact, products,
        versions_resolved, endpoints, availability, contexts, outputs, capabilities,
        pricing_present, pricing_is_fresh, accounts_resolved, unresolved_present, evidence_fresh,
        False, False, False, False, False, False,
    )


def build_exact_provider_model_binding_audit_evidence_v1(
    policy: ExactProviderModelBindingPolicyV1,
    documentation_evidence: tuple[ProviderDocumentationEvidenceV1, ...],
    bindings: tuple[ExactProviderModelBindingV1, ...],
    pricing_evidence: tuple[ProviderPricingEvidenceSnapshotV1, ...],
    decision: ExactProviderModelBindingDecisionV1,
) -> ExactProviderModelBindingAuditEvidenceV1:
    by_level = {item.routing_level: item for item in bindings}
    levels = tuple(by_level.get(level) for level in ("L0", "L1", "L2"))
    valid = all(item is not None for item in levels) and decision.policy_id == policy.policy_id and decision.deployment_environment == policy.deployment_environment
    if valid:
        for item in levels:
            if item is None:
                valid = False
                continue
            valid = valid and item.policy_id == policy.policy_id and item.provider_id == _EXPECTED[item.routing_level][0]
        evidence_ids = {item.documentation_evidence_id for item in documentation_evidence}
        pricing_ids = {item.pricing_evidence_snapshot_id: item for item in pricing_evidence}
        for item in levels:
            if item is None:
                valid = False
                continue
            valid = valid and set(item.documentation_evidence_ids).issubset(evidence_ids)
            snapshot = pricing_ids.get(item.pricing_evidence_snapshot_id)
            valid = valid and snapshot is not None and snapshot.provider_id == item.provider_id and snapshot.exact_provider_model_id == item.exact_provider_model_id
    if not valid:
        raise ValueError("exact model binding identity mismatch")
    assert all(item is not None for item in levels)
    selected = tuple(item for item in levels if item is not None)
    return ExactProviderModelBindingAuditEvidenceV1(
        policy.policy_id, policy.deployment_environment,
        selected[0].provider_id, selected[1].provider_id, selected[2].provider_id,
        selected[0].owner_model_selection, selected[1].owner_model_selection, selected[2].owner_model_selection,
        selected[0].exact_provider_model_id, selected[1].exact_provider_model_id, selected[2].exact_provider_model_id,
        decision.all_exact_model_ids_proven,
        tuple(item.documentation_evidence_id for item in documentation_evidence),
        decision.API_products_proven, decision.API_versions_resolved, decision.endpoint_classifications_proven,
        decision.availability_classifications_proven, decision.context_limits_proven, decision.output_limits_proven,
        decision.capabilities_proven,
        tuple((item.routing_level, item.unresolved_fields) for item in selected),
        tuple(item.pricing_evidence_snapshot_id for item in pricing_evidence), decision.pricing_evidence_fresh,
        tuple(item.account_access_classification for item in selected), decision.failure_codes,
        False, False, False, False, False, False,
    )
