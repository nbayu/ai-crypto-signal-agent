"""RED contract for immutable exact provider-model binding metadata only."""

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from engine.phase_12_exact_provider_model_binding_profile_contract_v1 import (
    ExactProviderModelBindingAuditEvidenceV1,
    ExactProviderModelBindingDecisionV1,
    ExactProviderModelBindingFailureV1,
    ExactProviderModelBindingPolicyV1,
    ExactProviderModelBindingV1,
    ProviderDocumentationEvidenceV1,
    ProviderPricingEvidenceSnapshotV1,
    build_exact_provider_model_binding_audit_evidence_v1,
    evaluate_exact_provider_model_binding_v1,
)


_AT = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
_EARLIER = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
_L0_UNRESOLVED = (
    "API_VERSION_MECHANISM",
    "FIXED_SNAPSHOT_SEMANTICS",
    "FORMAL_GA_STATUS",
    "ACCOUNT_ACCESS_CLASSIFICATION",
)
_ANTHROPIC_UNRESOLVED = (
    "ACCOUNT_ENTITLEMENT",
    "RATE_LIMIT_TIER",
    "BILLING_CONFIGURATION",
    "REGION_OR_ENDPOINT_SELECTION",
    "PERMISSION_SCOPE",
)
_CODES = {
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "PROVIDER_NOT_ALLOWED", "ROUTING_LEVEL_NOT_ALLOWED",
    "BINDING_ID_EMPTY", "ROUTE_ID_EMPTY", "ROUTING_LEVEL_MISMATCH", "ROUTING_ROLE_MISMATCH",
    "PROVIDER_ID_MISMATCH", "OWNER_MODEL_SELECTION_MISMATCH", "EXACT_MODEL_ID_EMPTY",
    "EXACT_MODEL_ID_MISMATCH", "EXACT_MODEL_ID_NOT_PROVEN", "MODEL_SUBSTITUTION_DETECTED",
    "ALIAS_INFERENCE_FORBIDDEN", "PROVIDER_SUBSTITUTION_DETECTED", "DOCUMENTATION_EVIDENCE_REQUIRED",
    "DOCUMENTATION_EVIDENCE_IDENTITY_MISMATCH", "OFFICIAL_SOURCE_REQUIRED", "OFFICIAL_LABEL_NOT_PROVEN",
    "API_PRODUCT_NOT_PROVEN", "API_VERSION_UNRESOLVED", "ENDPOINT_CLASSIFICATION_NOT_PROVEN",
    "AVAILABILITY_NOT_PROVEN", "CONTEXT_LIMIT_NOT_PROVEN", "OUTPUT_LIMIT_NOT_PROVEN",
    "CAPABILITY_EVIDENCE_NOT_PROVEN", "ACCOUNT_ACCESS_UNRESOLVED", "UNRESOLVED_FIELD_NOT_DECLARED",
    "RETRIEVAL_TIMESTAMP_REQUIRED", "RETRIEVAL_TIME_INCOMPLETE", "EVIDENCE_FROM_FUTURE",
    "EVIDENCE_EXPIRED", "EVIDENCE_AGE_INVALID", "PRICING_EVIDENCE_REQUIRED",
    "PRICING_EVIDENCE_IDENTITY_MISMATCH", "PRICING_EFFECTIVE_DATE_REQUIRED",
    "PRICING_EFFECTIVE_WINDOW_INVALID", "PRICING_EVIDENCE_EXPIRED", "PRICING_REVALIDATION_REQUIRED",
    "EXACT_MODEL_BINDING_NOT_AUTHORIZED", "ACCOUNT_VERIFICATION_NOT_AUTHORIZED",
    "CREDENTIAL_ONBOARDING_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_ACCOUNT_DATA_EXPOSURE_DETECTED",
    "RAW_ENDPOINT_EXPOSURE_DETECTED", "RAW_DOCUMENT_CONTENT_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


def _field_names(record: type) -> tuple[str, ...]:
    return tuple(item.name for item in fields(record))


def _policy() -> ExactProviderModelBindingPolicyV1:
    return ExactProviderModelBindingPolicyV1(
        policy_id="exact-model-policy-v1",
        policy_version="v1",
        deployment_environment="CONTROLLED_PRODUCTION",
        allowed_provider_ids=("DEEPSEEK", "ANTHROPIC"),
        allowed_routing_levels=("L0", "L1", "L2"),
        required_L0_provider_id="DEEPSEEK",
        required_L1_provider_id="ANTHROPIC",
        required_L2_provider_id="ANTHROPIC",
        required_L0_owner_model_selection="DEEPSEEK_V4_PRO",
        required_L1_owner_model_selection="CLAUDE_SONNET_5",
        required_L2_owner_model_selection="CLAUDE_OPUS_4_8",
        required_L0_exact_model_id="deepseek-v4-pro",
        required_L1_exact_model_id="claude-sonnet-5",
        required_L2_exact_model_id="claude-opus-4-8",
        require_official_documentation_evidence=True,
        require_exact_model_id_proven=True,
        require_API_product_evidence=True,
        require_API_version_evidence_or_explicit_unresolved_state=True,
        require_endpoint_classification=True,
        require_availability_classification=True,
        require_context_limit_evidence=True,
        require_output_limit_evidence=True,
        require_capability_evidence=True,
        require_account_access_classification=True,
        require_pricing_evidence=True,
        require_pricing_effective_date=True,
        require_pricing_revalidation_before_use=True,
        require_evidence_retrieval_timestamp=True,
        require_evidence_freshness=True,
        maximum_evidence_age_days=7,
        require_fail_closed_expired_evidence=True,
        require_no_model_substitution=True,
        require_no_alias_inference=True,
        require_no_provider_substitution=True,
        require_no_live_authority=True,
    )


def _documentation(provider_id: str, evidence_id: str, *, complete_time: bool) -> ProviderDocumentationEvidenceV1:
    return ProviderDocumentationEvidenceV1(
        documentation_evidence_id=evidence_id,
        provider_id=provider_id,
        official_domain_classification="OFFICIAL_PROVIDER_DOCUMENTATION",
        page_title="public-model-documentation",
        page_category="API_REFERENCE",
        section_heading="model-binding",
        retrieval_timestamp=_EARLIER if complete_time else None,
        publication_or_effective_date=_EARLIER,
        current_or_archived="CURRENT",
        supports_model_label=True,
        supports_exact_model_id=True,
        supports_API_product=True,
        supports_API_version=provider_id == "ANTHROPIC",
        supports_endpoint_classification=True,
        supports_availability=True,
        supports_context_limit=True,
        supports_output_limit=True,
        supports_capabilities=True,
        supports_pricing=True,
        supports_account_access=provider_id == "ANTHROPIC",
        evidence_complete=True,
        evidence_expired=False,
        redacted=True,
    )


def _binding(level: str, *, complete_operational_metadata: bool = False, **changes: object) -> ExactProviderModelBindingV1:
    locked = {
        "L0": ("DEEPSEEK", "PRIMARY_LIVE_REVIEW", "DEEPSEEK_V4_PRO", "deepseek-v4-pro", "CHAT_COMPLETIONS", "OPENAI_COMPATIBLE_CHAT_COMPLETIONS", "UNRESOLVED", "UNRESOLVED", "PUBLIC_API_PREVIEW_DOCUMENTED", "NOT_PROVEN", _L0_UNRESOLVED, "ACCOUNT_REQUIREMENT_UNRESOLVED"),
        "L1": ("ANTHROPIC", "ESCALATED_REVIEW", "CLAUDE_SONNET_5", "claude-sonnet-5", "MESSAGES_API", "MESSAGES_API", "ANTHROPIC_VERSION_HEADER", "PROVEN", "PUBLICLY_DOCUMENTED_STANDARD_ACCESS", "PINNED_CANONICAL_ID", _ANTHROPIC_UNRESOLVED, "ACCOUNT_REQUIREMENT_UNRESOLVED"),
        "L2": ("ANTHROPIC", "HIGHEST_ESCALATION_REVIEW", "CLAUDE_OPUS_4_8", "claude-opus-4-8", "MESSAGES_API", "MESSAGES_API", "ANTHROPIC_VERSION_HEADER", "PROVEN", "PUBLIC_CURRENT_MODEL_DOCUMENTED", "PINNED_CANONICAL_ID", _ANTHROPIC_UNRESOLVED, "ACCOUNT_REQUIREMENT_UNRESOLVED"),
    }[level]
    provider, role, selection, model_id, product, interface, mechanism, status, availability, snapshot, unresolved, account = locked
    values: dict[str, object] = {
        "binding_id": f"binding-{level.lower()}", "policy_id": "exact-model-policy-v1",
        "route_id": f"route-{level.lower()}", "routing_level": level, "routing_role": role,
        "provider_id": provider, "owner_model_selection": selection, "exact_provider_model_id": model_id,
        "model_binding_classification": "EXACT_MODEL_ID_PROVEN", "official_label_proven": True,
        "exact_model_id_proven": True, "API_product": product, "API_interface_classification": interface,
        "API_version_mechanism": mechanism, "API_version_status": status,
        "endpoint_classification": "PUBLIC_API_ENDPOINT_CLASSIFICATION",
        "availability_classification": availability, "snapshot_or_alias_status": snapshot,
        "context_limit_tokens": 1000000, "maximum_output_tokens": 384000 if level == "L0" else 128000,
        "capability_classifications": ("STREAMING", "TOOL_USE", "STRUCTURED_OUTPUT"),
        "documentation_evidence_ids": (f"docs-{level.lower()}",), "account_access_classification": account,
        "unresolved_fields": () if complete_operational_metadata else unresolved,
        "pricing_evidence_snapshot_id": f"pricing-{level.lower()}", "pricing_revalidation_required": True,
        "account_verification_required": True, "binding_ready": complete_operational_metadata,
    }
    values.update(changes)
    return ExactProviderModelBindingV1(**values)


def _pricing(binding: ExactProviderModelBindingV1, *, expired: bool = False) -> ProviderPricingEvidenceSnapshotV1:
    prices = {
        "L0": ("0.435", "0.003625", None, None, None, "0.87"),
        "L1": ("2", "0.20", "2.50", "4", "0.20", "10"),
        "L2": ("5", "0.50", "6.25", "10", "0.50", "25"),
    }[binding.routing_level]
    return ProviderPricingEvidenceSnapshotV1(
        pricing_evidence_snapshot_id=binding.pricing_evidence_snapshot_id,
        provider_id=binding.provider_id,
        exact_provider_model_id=binding.exact_provider_model_id,
        currency="USD", pricing_unit="PER_MILLION_TOKENS",
        input_price=Decimal(prices[0]), cached_input_price=Decimal(prices[1]) if prices[1] else None,
        cache_write_price_short=Decimal(prices[2]) if prices[2] else None,
        cache_write_price_long=Decimal(prices[3]) if prices[3] else None,
        cache_read_price=Decimal(prices[4]) if prices[4] else None,
        output_price=Decimal(prices[5]), price_effective_from=_EARLIER,
        price_effective_until=_EARLIER if expired else datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc),
        evidence_retrieved_at=_EARLIER, provider_states_prices_may_change=True,
        pricing_complete=True, pricing_expired=expired, pricing_revalidation_required=True, redacted=True,
    )


def _evaluate(*, complete_time: bool = False, complete_operational_metadata: bool = False, **changes: object) -> tuple[object, ...]:
    bindings = tuple(_binding(level, complete_operational_metadata=complete_operational_metadata) for level in ("L0", "L1", "L2"))
    documents = tuple(_documentation(item.provider_id, item.documentation_evidence_ids[0], complete_time=complete_time) for item in bindings)
    pricing = tuple(_pricing(item) for item in bindings)
    values = {
        "policy": _policy(), "documentation_evidence": documents, "bindings": bindings,
        "pricing_evidence": pricing, "evaluated_at": _AT,
    }
    values.update(changes)
    decision = evaluate_exact_provider_model_binding_v1(**values)
    return values["policy"], documents, bindings, pricing, decision


def test_public_records_are_immutable_and_exactly_redacted() -> None:
    expected = {
        ExactProviderModelBindingPolicyV1: ("policy_id", "policy_version", "deployment_environment", "allowed_provider_ids", "allowed_routing_levels", "required_L0_provider_id", "required_L1_provider_id", "required_L2_provider_id", "required_L0_owner_model_selection", "required_L1_owner_model_selection", "required_L2_owner_model_selection", "required_L0_exact_model_id", "required_L1_exact_model_id", "required_L2_exact_model_id", "require_official_documentation_evidence", "require_exact_model_id_proven", "require_API_product_evidence", "require_API_version_evidence_or_explicit_unresolved_state", "require_endpoint_classification", "require_availability_classification", "require_context_limit_evidence", "require_output_limit_evidence", "require_capability_evidence", "require_account_access_classification", "require_pricing_evidence", "require_pricing_effective_date", "require_pricing_revalidation_before_use", "require_evidence_retrieval_timestamp", "require_evidence_freshness", "maximum_evidence_age_days", "require_fail_closed_expired_evidence", "require_no_model_substitution", "require_no_alias_inference", "require_no_provider_substitution", "require_no_live_authority", "exact_model_binding_authorized", "account_verification_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized", "fail_closed"),
        ProviderDocumentationEvidenceV1: ("documentation_evidence_id", "provider_id", "official_domain_classification", "page_title", "page_category", "section_heading", "retrieval_timestamp", "publication_or_effective_date", "current_or_archived", "supports_model_label", "supports_exact_model_id", "supports_API_product", "supports_API_version", "supports_endpoint_classification", "supports_availability", "supports_context_limit", "supports_output_limit", "supports_capabilities", "supports_pricing", "supports_account_access", "evidence_complete", "evidence_expired", "redacted"),
        ExactProviderModelBindingV1: ("binding_id", "policy_id", "route_id", "routing_level", "routing_role", "provider_id", "owner_model_selection", "exact_provider_model_id", "model_binding_classification", "official_label_proven", "exact_model_id_proven", "API_product", "API_interface_classification", "API_version_mechanism", "API_version_status", "endpoint_classification", "availability_classification", "snapshot_or_alias_status", "context_limit_tokens", "maximum_output_tokens", "capability_classifications", "documentation_evidence_ids", "account_access_classification", "unresolved_fields", "pricing_evidence_snapshot_id", "pricing_revalidation_required", "account_verification_required", "binding_ready"),
        ProviderPricingEvidenceSnapshotV1: ("pricing_evidence_snapshot_id", "provider_id", "exact_provider_model_id", "currency", "pricing_unit", "input_price", "cached_input_price", "cache_write_price_short", "cache_write_price_long", "cache_read_price", "output_price", "price_effective_from", "price_effective_until", "evidence_retrieved_at", "provider_states_prices_may_change", "pricing_complete", "pricing_expired", "pricing_revalidation_required", "redacted"),
        ExactProviderModelBindingDecisionV1: ("policy_id", "deployment_environment", "ready", "failure_codes", "owner_routing_preserved", "L0_exact_model_binding_proven", "L1_exact_model_binding_proven", "L2_exact_model_binding_proven", "all_exact_model_ids_proven", "API_products_proven", "API_versions_resolved", "endpoint_classifications_proven", "availability_classifications_proven", "context_limits_proven", "output_limits_proven", "capabilities_proven", "pricing_evidence_present", "pricing_evidence_fresh", "account_requirements_resolved", "unresolved_fields_present", "evidence_fresh", "exact_model_binding_authorized", "account_verification_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized"),
        ExactProviderModelBindingAuditEvidenceV1: ("policy_id", "deployment_environment", "L0_provider_id", "L1_provider_id", "L2_provider_id", "L0_owner_model_selection", "L1_owner_model_selection", "L2_owner_model_selection", "L0_exact_provider_model_id", "L1_exact_provider_model_id", "L2_exact_provider_model_id", "all_exact_model_ids_proven", "documentation_evidence_ids", "API_products_proven", "API_versions_resolved", "endpoint_classifications_proven", "availability_classifications_proven", "context_limits_proven", "output_limits_proven", "capabilities_proven", "unresolved_fields", "pricing_evidence_snapshot_ids", "pricing_evidence_fresh", "account_access_classifications", "failure_codes", "exact_model_binding_authorized", "account_verification_authorized", "credential_onboarding_authorized", "credential_loading_authorized", "network_authorized", "provider_transmission_authorized"),
    }
    for record, names in expected.items():
        assert is_dataclass(record)
        assert _field_names(record) == names
        assert getattr(record, "__dataclass_params__").frozen is True
        assert hasattr(record, "__slots__")
    assert _field_names(ExactProviderModelBindingFailureV1) == ("failure_code", "safe_message", "retryable")
    defaults = ExactProviderModelBindingPolicyV1()
    assert defaults.allowed_provider_ids == ()
    assert defaults.allowed_routing_levels == ()
    assert defaults.fail_closed is True
    assert not any((defaults.exact_model_binding_authorized, defaults.account_verification_authorized, defaults.credential_onboarding_authorized, defaults.credential_loading_authorized, defaults.network_authorized, defaults.provider_transmission_authorized))
    forbidden = ("api_key", "credential", "token", "authorization", "cookie", "html", "content", "exception")
    assert not any(item in forbidden for item in _field_names(ExactProviderModelBindingAuditEvidenceV1))


def test_accepted_exact_ids_remain_proven_while_step_44_unresolved_metadata_blocks_readiness() -> None:
    _policy_value, _documents, bindings, _pricing_values, decision = _evaluate()
    assert tuple((item.provider_id, item.owner_model_selection, item.exact_provider_model_id) for item in bindings) == (
        ("DEEPSEEK", "DEEPSEEK_V4_PRO", "deepseek-v4-pro"),
        ("ANTHROPIC", "CLAUDE_SONNET_5", "claude-sonnet-5"),
        ("ANTHROPIC", "CLAUDE_OPUS_4_8", "claude-opus-4-8"),
    )
    assert decision.owner_routing_preserved is True
    assert decision.all_exact_model_ids_proven is True
    assert decision.ready is False
    assert decision.unresolved_fields_present is True
    assert {"API_VERSION_UNRESOLVED", "ACCOUNT_ACCESS_UNRESOLVED", "RETRIEVAL_TIME_INCOMPLETE"} <= set(decision.failure_codes)
    assert tuple(sorted(decision.failure_codes)) == decision.failure_codes
    assert set(decision.failure_codes) <= _CODES
    assert not any((decision.exact_model_binding_authorized, decision.account_verification_authorized, decision.credential_onboarding_authorized, decision.credential_loading_authorized, decision.network_authorized, decision.provider_transmission_authorized))


def test_substitution_alias_inference_and_expired_pricing_fail_closed_without_authority() -> None:
    policy, documents, bindings, pricing, _decision = _evaluate(complete_time=True)
    bad_l0 = _binding("L0", exact_provider_model_id="deepseek-chat", snapshot_or_alias_status="INFERRED_ALIAS")
    bad_pricing = _pricing(bindings[1], expired=True)
    decision = evaluate_exact_provider_model_binding_v1(
        policy=policy,
        documentation_evidence=documents,
        bindings=(bad_l0, bindings[1], bindings[2]),
        pricing_evidence=(pricing[0], bad_pricing, pricing[2]),
        evaluated_at=_AT,
    )
    assert {"EXACT_MODEL_ID_MISMATCH", "MODEL_SUBSTITUTION_DETECTED", "ALIAS_INFERENCE_FORBIDDEN", "PRICING_EVIDENCE_EXPIRED"} <= set(decision.failure_codes)
    assert tuple(sorted(decision.failure_codes)) == decision.failure_codes
    assert decision.ready is False
    assert not any((decision.exact_model_binding_authorized, decision.account_verification_authorized, decision.credential_onboarding_authorized, decision.credential_loading_authorized, decision.network_authorized, decision.provider_transmission_authorized))


def test_audit_is_immutable_redacted_and_performs_no_second_evaluation() -> None:
    policy, documents, bindings, pricing, decision = _evaluate()
    audit = build_exact_provider_model_binding_audit_evidence_v1(policy, documents, bindings, pricing, decision)
    assert audit.L0_exact_provider_model_id == "deepseek-v4-pro"
    assert audit.L1_exact_provider_model_id == "claude-sonnet-5"
    assert audit.L2_exact_provider_model_id == "claude-opus-4-8"
    assert audit.failure_codes == decision.failure_codes
    assert not any((audit.exact_model_binding_authorized, audit.account_verification_authorized, audit.credential_onboarding_authorized, audit.credential_loading_authorized, audit.network_authorized, audit.provider_transmission_authorized))
    with pytest.raises(ValueError):
        build_exact_provider_model_binding_audit_evidence_v1(policy, documents, (_binding("L0", provider_id="ANTHROPIC"), bindings[1], bindings[2]), pricing, decision)
