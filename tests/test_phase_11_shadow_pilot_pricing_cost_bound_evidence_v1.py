"""RED contract for immutable Phase 11 official pricing cost-bound evidence.

This suite freezes public-documentation observations and conservative Decimal
cost arithmetic only.  It neither retrieves documentation nor grants any
credential, budget, provider, launch, production, or Phase 12 authority.
"""

from __future__ import annotations

import ast
import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotPricingRevalidationStatusV1,
    ShadowPhase11PilotProviderRoleV1,
    ShadowPhase11PilotRetryPolicyV1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    ShadowPhase11ModelPricingCostBoundV1,
    ShadowPhase11OfficialPricingSourcePurposeV1,
    ShadowPhase11OfficialPricingSourceV1,
    ShadowPhase11PilotPricingCostBoundEvidenceV1,
    ShadowPhase11PilotRouteV1,
    ShadowPhase11PricingCostBoundValidationError,
    ShadowPhase11RouteCostBoundV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
    sha256_hex,
)


LOCKED_REPOSITORY_BASELINE = "903184dc8fbf57bae1d6490135445d1c4e05bebf"
LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
BUDGET_AUTHORIZATION_REFERENCE = "PHASE_11_SHADOW_PILOT_BUDGET_USD_5_001"
MODEL_COST_AUTHORIZATION_REFERENCE = "PHASE_11_PILOT_MODEL_COST_BOUNDS_001"
HARD_CAP_MICRO_USD = Decimal("5000000")
SAFETY_RESERVE_MICRO_USD = Decimal("500000")
SPENDABLE_CAP_MICRO_USD = Decimal("4500000")
ZERO_MICRO_USD = Decimal("0")
AUTHORIZED_INPUT_TOKENS = 16000
AUTHORIZED_OUTPUT_TOKENS = 2000

DEEPSEEK_MODELS_SHA256 = "d2f1f6f3f4b67d764db0896375764266ceb24f953b775fae9c8fadc3ca3f83c7"
DEEPSEEK_PRICING_SHA256 = "5ed7309f6b8bf5dbae559a012341aa604d02b0cce2e20c48aaa6f0a0bf287f89"
CLAUDE_MODELS_SHA256 = "9671f1b06820119975799d5f768732aeca282f5a57b3c9fb7a446cdcc0be7378"
CLAUDE_PRICING_SHA256 = "f0f9bf9c4db1a859a023e3d35a6949ca0732461097d0c56545d7611d3696d191"


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _source(
    purpose: ShadowPhase11OfficialPricingSourcePurposeV1,
    **overrides: object,
) -> ShadowPhase11OfficialPricingSourceV1:
    values = {
        "schema_version": "phase11-official-pricing-source-v1",
        "source_id": None,
        "purpose": purpose,
        "provider": "DEEPSEEK",
        "requested_url": "https://api-docs.deepseek.com/quick_start/model_list",
        "final_url": "https://api-docs.deepseek.com/quick_start/model_list",
        "retrieved_at_utc": _utc("2026-07-18T09:37:02Z"),
        "http_method": "GET",
        "http_status": 200,
        "content_type": "text/html",
        "etag": '"21d3921829487b385a08d944eacc9979"',
        "last_modified": "Mon, 13 Jul 2026 03:34:30 GMT",
        "response_body_sha256": DEEPSEEK_MODELS_SHA256,
        "document_title": "Your First API Call | DeepSeek API Docs",
        "relevant_heading": "Your First API Call",
        "price_change_warning": False,
        "effective_date": None,
        "expiry_date": None,
        "reason_codes": ("OFFICIAL_PUBLIC_DOCUMENTATION",),
    }
    if purpose is ShadowPhase11OfficialPricingSourcePurposeV1.DEEPSEEK_PRICING:
        values.update(
            requested_url="https://api-docs.deepseek.com/quick_start/pricing",
            final_url="https://api-docs.deepseek.com/quick_start/pricing/",
            retrieved_at_utc=_utc("2026-07-18T09:37:03Z"),
            etag='"e2fb44396349e126364403c2db910464"',
            last_modified="Mon, 13 Jul 2026 03:34:36 GMT",
            response_body_sha256=DEEPSEEK_PRICING_SHA256,
            document_title="Models & Pricing | DeepSeek API Docs",
            relevant_heading="Models & Pricing",
            price_change_warning=True,
        )
    if purpose is ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_MODELS:
        values.update(
            provider="ANTHROPIC",
            requested_url="https://platform.claude.com/docs/en/about-claude/models/overview",
            final_url="https://platform.claude.com/docs/en/about-claude/models/overview",
            retrieved_at_utc=_utc("2026-07-18T09:37:06Z"),
            content_type="text/html; charset=utf-8",
            etag=None,
            last_modified=None,
            response_body_sha256=CLAUDE_MODELS_SHA256,
            document_title="Models overview - Claude Platform Docs",
            relevant_heading="Models overview",
        )
    if purpose is ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_PRICING:
        values.update(
            provider="ANTHROPIC",
            requested_url="https://platform.claude.com/docs/en/about-claude/pricing",
            final_url="https://platform.claude.com/docs/en/about-claude/pricing",
            retrieved_at_utc=_utc("2026-07-18T09:37:06Z"),
            content_type="text/html; charset=utf-8",
            etag=None,
            last_modified=None,
            response_body_sha256=CLAUDE_PRICING_SHA256,
            document_title="Pricing - Claude Platform Docs",
            relevant_heading="Pricing",
            expiry_date=date(2026, 8, 31),
        )
    values.update(overrides)
    return ShadowPhase11OfficialPricingSourceV1(**values)


def _sources() -> tuple[ShadowPhase11OfficialPricingSourceV1, ...]:
    return tuple(_source(purpose) for purpose in ShadowPhase11OfficialPricingSourcePurposeV1)


def _model_bound(
    role: ShadowPhase11PilotProviderRoleV1,
    **overrides: object,
) -> ShadowPhase11ModelPricingCostBoundV1:
    assignments = {
        ShadowPhase11PilotProviderRoleV1.PRIMARY: {
            "provider": "DEEPSEEK",
            "model_identifier": "deepseek-v4-pro",
            "official_context_limit": 1000000,
            "official_maximum_output_tokens": 384000,
            "current_input_price_usd_per_million": Decimal("0.435"),
            "current_output_price_usd_per_million": Decimal("0.87"),
            "conservative_input_price_usd_per_million": Decimal("0.435"),
            "conservative_output_price_usd_per_million": Decimal("0.87"),
            "current_maximum_input_cost_micro_usd": Decimal("6960"),
            "current_maximum_output_cost_micro_usd": Decimal("1740"),
            "current_maximum_call_cost_micro_usd": Decimal("8700"),
            "maximum_input_cost_micro_usd": Decimal("6960"),
            "maximum_output_cost_micro_usd": Decimal("1740"),
            "maximum_call_cost_micro_usd": Decimal("8700"),
            "source_ids": (_source(ShadowPhase11OfficialPricingSourcePurposeV1.DEEPSEEK_PRICING).identity,),
            "promotional_end_date": None,
            "scheduled_standard_start_date": None,
        },
        ShadowPhase11PilotProviderRoleV1.L1: {
            "provider": "ANTHROPIC",
            "model_identifier": "claude-sonnet-5",
            "official_context_limit": 1000000,
            "official_maximum_output_tokens": 128000,
            "current_input_price_usd_per_million": Decimal("2"),
            "current_output_price_usd_per_million": Decimal("10"),
            "conservative_input_price_usd_per_million": Decimal("3"),
            "conservative_output_price_usd_per_million": Decimal("15"),
            "current_maximum_input_cost_micro_usd": Decimal("32000"),
            "current_maximum_output_cost_micro_usd": Decimal("20000"),
            "current_maximum_call_cost_micro_usd": Decimal("52000"),
            "maximum_input_cost_micro_usd": Decimal("48000"),
            "maximum_output_cost_micro_usd": Decimal("30000"),
            "maximum_call_cost_micro_usd": Decimal("78000"),
            "source_ids": (_source(ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_MODELS).identity, _source(ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_PRICING).identity),
            "promotional_end_date": date(2026, 8, 31),
            "scheduled_standard_start_date": date(2026, 9, 1),
        },
        ShadowPhase11PilotProviderRoleV1.L2: {
            "provider": "ANTHROPIC",
            "model_identifier": "claude-opus-4-8",
            "official_context_limit": 1000000,
            "official_maximum_output_tokens": 128000,
            "current_input_price_usd_per_million": Decimal("5"),
            "current_output_price_usd_per_million": Decimal("25"),
            "conservative_input_price_usd_per_million": Decimal("5"),
            "conservative_output_price_usd_per_million": Decimal("25"),
            "current_maximum_input_cost_micro_usd": Decimal("80000"),
            "current_maximum_output_cost_micro_usd": Decimal("50000"),
            "current_maximum_call_cost_micro_usd": Decimal("130000"),
            "maximum_input_cost_micro_usd": Decimal("80000"),
            "maximum_output_cost_micro_usd": Decimal("50000"),
            "maximum_call_cost_micro_usd": Decimal("130000"),
            "source_ids": (_source(ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_PRICING).identity,),
            "promotional_end_date": None,
            "scheduled_standard_start_date": None,
        },
    }
    values = {
        "schema_version": "phase11-model-pricing-cost-bound-v1",
        "model_bound_id": None,
        "role": role,
        "documented_available": True,
        "authorized_input_tokens": AUTHORIZED_INPUT_TOKENS,
        "authorized_output_tokens": AUTHORIZED_OUTPUT_TOKENS,
        "maximum_attempts": 1,
        "provider_error_retry_policy": ShadowPhase11PilotRetryPolicyV1.FORBIDDEN,
        "credential_error_retry_policy": ShadowPhase11PilotRetryPolicyV1.FORBIDDEN,
        "authentication_error_retry_policy": ShadowPhase11PilotRetryPolicyV1.FORBIDDEN,
        "discount_exclusion_assumptions": (
            "NO_CACHE_HIT_DISCOUNT",
            "NO_CACHE_WRITE_ASSUMPTION",
            "NO_BATCH_DISCOUNT",
            "NO_NEGOTIATED_DISCOUNT",
            "NO_ACCOUNT_CREDIT_ASSUMPTION",
        ),
        "premium_tool_exclusion_assumptions": (
            "NO_SERVER_SIDE_TOOL",
            "NO_FAST_OR_PREMIUM_MODE",
            "NO_TOOL_CALL",
        ),
        "reason_codes": ("OFFICIAL_PRICE_CONSERVATIVE_BOUND",),
        **assignments[role],
    }
    values.update(overrides)
    return ShadowPhase11ModelPricingCostBoundV1(**values)


def _route(route: ShadowPhase11PilotRouteV1, **overrides: object) -> ShadowPhase11RouteCostBoundV1:
    bounds = {item.role: item for item in (_model_bound(role) for role in ShadowPhase11PilotProviderRoleV1)}
    assignments = {
        ShadowPhase11PilotRouteV1.L0: ((bounds[ShadowPhase11PilotProviderRoleV1.PRIMARY].identity,), 1, Decimal("8700"), Decimal("8700")),
        ShadowPhase11PilotRouteV1.L1: ((bounds[ShadowPhase11PilotProviderRoleV1.PRIMARY].identity, bounds[ShadowPhase11PilotProviderRoleV1.L1].identity), 2, Decimal("60700"), Decimal("86700")),
        ShadowPhase11PilotRouteV1.DIRECT_L2: ((bounds[ShadowPhase11PilotProviderRoleV1.PRIMARY].identity, bounds[ShadowPhase11PilotProviderRoleV1.L2].identity), 2, Decimal("138700"), Decimal("138700")),
        ShadowPhase11PilotRouteV1.L1_TO_L2: ((bounds[ShadowPhase11PilotProviderRoleV1.PRIMARY].identity, bounds[ShadowPhase11PilotProviderRoleV1.L1].identity, bounds[ShadowPhase11PilotProviderRoleV1.L2].identity), 3, Decimal("190700"), Decimal("216700")),
    }
    sequence, calls, current, conservative = assignments[route]
    values = {
        "schema_version": "phase11-route-cost-bound-v1",
        "route_bound_id": None,
        "route": route,
        "model_bound_ids": sequence,
        "billable_call_count": calls,
        "maximum_attempts_per_call": 1,
        "current_total_micro_usd": current,
        "conservative_total_micro_usd": conservative,
        "reachability": "REACHABLE",
        "reason_codes": ("COMMITTED_ROUTE_TOPOLOGY",),
    }
    values.update(overrides)
    return ShadowPhase11RouteCostBoundV1(**values)


def _evidence(**overrides: object) -> ShadowPhase11PilotPricingCostBoundEvidenceV1:
    values = {
        "schema_version": "phase11-shadow-pilot-pricing-cost-bound-evidence-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "budget_authorization_reference": BUDGET_AUTHORIZATION_REFERENCE,
        "model_cost_authorization_reference": MODEL_COST_AUTHORIZATION_REFERENCE,
        "locked_repository_baseline": LOCKED_REPOSITORY_BASELINE,
        "locked_phase09_baseline": LOCKED_PHASE09_BASELINE,
        "official_sources": _sources(),
        "model_cost_bounds": tuple(_model_bound(role) for role in ShadowPhase11PilotProviderRoleV1),
        "route_cost_bounds": tuple(_route(route) for route in ShadowPhase11PilotRouteV1),
        "conservative_worst_case_route": ShadowPhase11PilotRouteV1.L1_TO_L2,
        "conservative_worst_case_item_cost_micro_usd": Decimal("216700"),
        "hard_cap_micro_usd": HARD_CAP_MICRO_USD,
        "safety_reserve_micro_usd": SAFETY_RESERVE_MICRO_USD,
        "spendable_cap_micro_usd": SPENDABLE_CAP_MICRO_USD,
        "mathematical_safe_maximum_items": 20,
        "safe_capacity_total_micro_usd": Decimal("4334000"),
        "next_item_total_micro_usd": Decimal("4550700"),
        "fixed_freshness_window_defined": False,
        "launch_time_pricing_revalidation_required": True,
        "pricing_revalidation_status": ShadowPhase11PilotPricingRevalidationStatusV1.REQUIRED_NOT_COMPLETED,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "run_size_authorized": False,
        "budget_reserved_micro_usd": ZERO_MICRO_USD,
        "budget_consumed_micro_usd": ZERO_MICRO_USD,
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
        "reason_codes": ("OFFICIAL_PRICING_EVIDENCE_ONLY",),
    }
    values.update(overrides)
    return ShadowPhase11PilotPricingCostBoundEvidenceV1(**values)


def _reject_source(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _source(ShadowPhase11OfficialPricingSourcePurposeV1.DEEPSEEK_MODELS, **overrides)


def _reject_model(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _model_bound(ShadowPhase11PilotProviderRoleV1.PRIMARY, **overrides)


def _reject_route(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _route(ShadowPhase11PilotRouteV1.L0, **overrides)


def _reject_evidence(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _evidence(**overrides)


def test_official_source_records_are_concrete_complete_closed_and_metadata_only():
    sources = _sources()
    assert len(sources) == 4
    assert tuple(item.purpose for item in sources) == tuple(ShadowPhase11OfficialPricingSourcePurposeV1)
    assert tuple(item.purpose.value for item in sources) == (
        "DEEPSEEK_MODELS", "DEEPSEEK_PRICING", "CLAUDE_MODELS", "CLAUDE_PRICING",
    )
    assert tuple((item.requested_url, item.final_url, item.retrieved_at_utc, item.document_title, item.relevant_heading) for item in sources) == (
        ("https://api-docs.deepseek.com/quick_start/model_list", "https://api-docs.deepseek.com/quick_start/model_list", _utc("2026-07-18T09:37:02Z"), "Your First API Call | DeepSeek API Docs", "Your First API Call"),
        ("https://api-docs.deepseek.com/quick_start/pricing", "https://api-docs.deepseek.com/quick_start/pricing/", _utc("2026-07-18T09:37:03Z"), "Models & Pricing | DeepSeek API Docs", "Models & Pricing"),
        ("https://platform.claude.com/docs/en/about-claude/models/overview", "https://platform.claude.com/docs/en/about-claude/models/overview", _utc("2026-07-18T09:37:06Z"), "Models overview - Claude Platform Docs", "Models overview"),
        ("https://platform.claude.com/docs/en/about-claude/pricing", "https://platform.claude.com/docs/en/about-claude/pricing", _utc("2026-07-18T09:37:06Z"), "Pricing - Claude Platform Docs", "Pricing"),
    )
    assert tuple(item.response_body_sha256 for item in sources) == (
        DEEPSEEK_MODELS_SHA256, DEEPSEEK_PRICING_SHA256, CLAUDE_MODELS_SHA256, CLAUDE_PRICING_SHA256,
    )
    assert all(len(item.response_body_sha256) == 64 and item.response_body_sha256.islower() for item in sources)
    assert all(item.http_method == "GET" and item.http_status == 200 for item in sources)
    assert all(item.retrieved_at_utc.tzinfo is timezone.utc for item in sources)
    assert not any("response_body" in name and name != "response_body_sha256" for name in ShadowPhase11OfficialPricingSourceV1.__dataclass_fields__)
    _reject_source(final_url="https://api.deepseek.com/v1/chat/completions")
    _reject_source(response_body_sha256="abc")
    _reject_source(retrieved_at_utc=datetime(2026, 7, 18, 9, 37, 2))
    _reject_source(http_status=201)
    _reject_source(source_id="0" * 64)
    _reject_source(unknown_field="reject")


def test_exact_model_price_token_and_no_retry_bounds_are_frozen_with_decimal_ceiling_costs():
    primary, l1, l2 = (_model_bound(role) for role in ShadowPhase11PilotProviderRoleV1)
    assert (primary.provider, primary.model_identifier, primary.official_context_limit, primary.official_maximum_output_tokens) == ("DEEPSEEK", "deepseek-v4-pro", 1000000, 384000)
    assert (l1.provider, l1.model_identifier, l1.current_maximum_call_cost_micro_usd, l1.maximum_call_cost_micro_usd) == ("ANTHROPIC", "claude-sonnet-5", Decimal("52000"), Decimal("78000"))
    assert (l2.provider, l2.model_identifier, l2.maximum_input_cost_micro_usd, l2.maximum_output_cost_micro_usd, l2.maximum_call_cost_micro_usd) == ("ANTHROPIC", "claude-opus-4-8", Decimal("80000"), Decimal("50000"), Decimal("130000"))
    assert l1.promotional_end_date == date(2026, 8, 31)
    assert l1.scheduled_standard_start_date == date(2026, 9, 1)
    for bound in (primary, l1, l2):
        assert bound.authorized_input_tokens == AUTHORIZED_INPUT_TOKENS
        assert bound.authorized_output_tokens == AUTHORIZED_OUTPUT_TOKENS
        assert bound.maximum_attempts == 1
        assert bound.provider_error_retry_policy is ShadowPhase11PilotRetryPolicyV1.FORBIDDEN
        assert bound.credential_error_retry_policy is ShadowPhase11PilotRetryPolicyV1.FORBIDDEN
        assert bound.authentication_error_retry_policy is ShadowPhase11PilotRetryPolicyV1.FORBIDDEN
        assert bound.maximum_input_cost_micro_usd + bound.maximum_output_cost_micro_usd == bound.maximum_call_cost_micro_usd
    _reject_model(model_identifier="deepseek-v4-pro-alt")
    _reject_model(provider="ANTHROPIC")
    _reject_model(authorized_input_tokens=1000001)
    _reject_model(official_context_limit=15999)
    _reject_model(current_input_price_usd_per_million=0.435)
    _reject_model(current_input_price_usd_per_million=Decimal("NaN"))
    _reject_model(maximum_call_cost_micro_usd=Decimal("8701"))
    _reject_model(maximum_attempts=2)
    _reject_model(provider_error_retry_policy="ALLOWED")


def test_sonnet_promotion_cannot_reduce_the_conservative_cost_bound():
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _model_bound(
            ShadowPhase11PilotProviderRoleV1.L1,
            conservative_input_price_usd_per_million=Decimal("2"),
            conservative_output_price_usd_per_million=Decimal("10"),
            maximum_input_cost_micro_usd=Decimal("32000"),
            maximum_output_cost_micro_usd=Decimal("20000"),
            maximum_call_cost_micro_usd=Decimal("52000"),
        )
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _model_bound(
            ShadowPhase11PilotProviderRoleV1.L1,
            current_maximum_call_cost_micro_usd=Decimal("52001"),
        )
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _model_bound(
            ShadowPhase11PilotProviderRoleV1.L2,
            maximum_call_cost_micro_usd=Decimal("130001"),
        )


def test_routes_bind_committed_order_one_attempt_and_exact_current_and_conservative_totals():
    routes = tuple(_route(route) for route in ShadowPhase11PilotRouteV1)
    assert tuple(item.route for item in routes) == tuple(ShadowPhase11PilotRouteV1)
    assert tuple(item.route.value for item in routes) == ("L0", "L1", "DIRECT_L2", "L1_TO_L2")
    assert tuple((item.billable_call_count, item.current_total_micro_usd, item.conservative_total_micro_usd) for item in routes) == (
        (1, Decimal("8700"), Decimal("8700")),
        (2, Decimal("60700"), Decimal("86700")),
        (2, Decimal("138700"), Decimal("138700")),
        (3, Decimal("190700"), Decimal("216700")),
    )
    assert all(item.maximum_attempts_per_call == 1 for item in routes)
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _route(
            ShadowPhase11PilotRouteV1.L1,
            model_bound_ids=tuple(
                reversed(_route(ShadowPhase11PilotRouteV1.L1).model_bound_ids)
            ),
        )
    _reject_route(conservative_total_micro_usd=Decimal("8701"))
    _reject_route(route_bound_id="0" * 64)
    with pytest.raises(ShadowPhase11PricingCostBoundValidationError):
        _route("UNKNOWN")


def test_concrete_evidence_binds_exact_capacity_freshness_revalidation_and_zero_authority():
    evidence = _evidence()
    assert evidence.evidence_reference == EVIDENCE_REFERENCE
    assert evidence.locked_repository_baseline == LOCKED_REPOSITORY_BASELINE
    assert evidence.locked_phase09_baseline == LOCKED_PHASE09_BASELINE
    assert evidence.conservative_worst_case_route is ShadowPhase11PilotRouteV1.L1_TO_L2
    assert evidence.conservative_worst_case_item_cost_micro_usd == Decimal("216700")
    assert evidence.mathematical_safe_maximum_items == 20
    assert evidence.safe_capacity_total_micro_usd == Decimal("4334000")
    assert evidence.next_item_total_micro_usd == Decimal("4550700")
    assert evidence.safe_capacity_total_micro_usd <= evidence.spendable_cap_micro_usd
    assert evidence.next_item_total_micro_usd > evidence.spendable_cap_micro_usd
    assert evidence.fixed_freshness_window_defined is False
    assert evidence.launch_time_pricing_revalidation_required is True
    assert evidence.pricing_revalidation_status is ShadowPhase11PilotPricingRevalidationStatusV1.REQUIRED_NOT_COMPLETED
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.run_size_authorized is False
    assert evidence.budget_reserved_micro_usd == evidence.budget_consumed_micro_usd == ZERO_MICRO_USD
    assert evidence.production_effect == "NONE"
    assert evidence.zero_production_effect_proof == "PROVEN_NONE"
    _reject_evidence(mathematical_safe_maximum_items=21)
    _reject_evidence(next_item_total_micro_usd=Decimal("4500000"))
    _reject_evidence(run_size_authorized=True)
    _reject_evidence(budget_reserved_micro_usd=Decimal("1"))
    _reject_evidence(budget_consumed_micro_usd=Decimal("1"))
    _reject_evidence(launch_readiness="READY_FOR_LAUNCH")


def test_evidence_rejects_missing_duplicate_or_tampered_sources_models_routes_and_capacity():
    sources = _sources()
    models = tuple(_model_bound(role) for role in ShadowPhase11PilotProviderRoleV1)
    routes = tuple(_route(route) for route in ShadowPhase11PilotRouteV1)
    _reject_evidence(official_sources=sources[:-1])
    _reject_evidence(official_sources=(sources[0], sources[0], sources[2], sources[3]))
    _reject_evidence(model_cost_bounds=models[:-1])
    _reject_evidence(model_cost_bounds=(models[0], models[0], models[2]))
    _reject_evidence(route_cost_bounds=routes[:-1])
    _reject_evidence(route_cost_bounds=(routes[0], routes[0], routes[2], routes[3]))
    _reject_evidence(conservative_worst_case_route=ShadowPhase11PilotRouteV1.L1)
    _reject_evidence(conservative_worst_case_item_cost_micro_usd=Decimal("216701"))
    _reject_evidence(safe_capacity_total_micro_usd=Decimal("4334001"))
    _reject_evidence(evidence_id="0" * 64)


def test_identity_converges_for_canonical_order_and_diverges_for_valid_material_evidence_changes():
    evidence = _evidence()
    assert evidence.identity == _evidence(
        official_sources=tuple(reversed(_sources())),
        model_cost_bounds=tuple(reversed(tuple(_model_bound(role) for role in ShadowPhase11PilotProviderRoleV1))),
        route_cost_bounds=tuple(reversed(tuple(_route(route) for route in ShadowPhase11PilotRouteV1))),
    ).identity
    assert evidence.identity != _evidence(reason_codes=("OFFICIAL_PRICING_EVIDENCE_VARIANT",)).identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    assert sha256_hex(b"pricing-cost-bound") == hashlib.sha256(b"pricing-cost-bound").hexdigest()


def test_zero_argument_accessor_is_deterministic_closed_and_evidence_only():
    first = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    second = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    assert type(first) is ShadowPhase11PilotPricingCostBoundEvidenceV1
    assert first.identity == second.identity
    forbidden_fields = {
        "response_body", "fixed_freshness_window", "credential_reference", "provider_call",
        "run_manifest", "pilot_input", "reserve_budget", "commit_usage", "authorize_launch",
        "phase11_completion", "phase11_pass", "phase12_enabled", "publication", "deployment",
        "telegram", "account", "order", "trading",
    }
    assert not set(first.__dataclass_fields__) & forbidden_fields
    with pytest.raises((AttributeError, TypeError)):
        first.budget_consumed_micro_usd = Decimal("1")


def test_static_dependency_and_side_effect_boundary():
    module = ast.parse(Path("engine/phase_11_shadow_pilot_pricing_cost_bound_evidence_v1.py").read_text(encoding="utf-8"))
    forbidden_modules = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess",
        "threading", "multiprocessing", "concurrent", "asyncio", "pytest",
    }
    forbidden_names = {
        "open", "float", "resolve_provider_credential", "DeepSeekShadowTransportAdapterV1",
        "AnthropicShadowTransportAdapterV1", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1",
        "BudgetLedgerV1", "reserve_call", "commit_usage", "requests", "http", "telegram",
        "account", "exchange", "order", "position", "trading", "publication", "deployment",
        "persistence", "datetime_now", "utcnow",
    }
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.With)) for node in ast.walk(module))
