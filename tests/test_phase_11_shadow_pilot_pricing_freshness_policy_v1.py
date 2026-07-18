"""RED contract for immutable Phase 11 zero-reuse pricing freshness policy."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_blocked_readiness_reconciliation_v1 import (
    get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1,
)
from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotPricingRevalidationStatusV1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)
from engine.phase_11_shadow_pilot_pricing_freshness_policy_v1 import (
    ShadowPhase11PricingFreshnessPolicyEvidenceV1,
    ShadowPhase11PricingFreshnessPolicyStateV1,
    ShadowPhase11PricingFreshnessPolicyValidationError,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1,
    sha256_hex,
)


LOCKED_REPOSITORY_BASELINE = "e896fc134a6b34d8dc146d6f1e307beab032df33"
LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRICING_FRESHNESS_POLICY_001"
PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
PRICING_IDENTITY = "9b986028159efa107da3d2625422ad937d19a65631e5ea95926e006f28329d31"
RECONCILIATION_REFERENCE = "PHASE_11_PILOT_BLOCKED_READINESS_RECONCILIATION_001"
RECONCILIATION_IDENTITY = "4cc8db3264a57480af050d286d9fd1acd5935841f94f4034d7a3cece661a9b4c"
GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
GATE_IDENTITY = "77b7bbb6782a4710b04abd16547ba5fd94e8311d09cad0cd0187fc7b8313c06b"
FUTURE_PATH = "engine/phase_11_shadow_pilot_pricing_freshness_policy_v1.py"

HARD_CAP = Decimal("5000000")
RESERVE = Decimal("500000")
SPENDABLE = Decimal("4500000")
WORST_CASE_ITEM = Decimal("216700")
CAPACITY = 20
POLICY_REASONS = tuple(sorted((
    "ZERO_REUSE_WINDOW_DEFINED",
    "CACHED_PRICING_EVIDENCE_REUSE_NOT_AUTHORIZED",
    "LAUNCH_TIME_PRICING_REVALIDATION_REQUIRED",
    "PRICING_REVALIDATION_NOT_COMPLETED",
    "CURRENT_TIME_ACCESS_NOT_REQUIRED",
    "NO_PRICING_LOOKUP_AUTHORITY",
    "NO_OPERATIONAL_AUTHORITY",
)))


def _evidence(**overrides: object) -> ShadowPhase11PricingFreshnessPolicyEvidenceV1:
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reconciliation = get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-pricing-freshness-policy-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": LOCKED_REPOSITORY_BASELINE,
        "locked_phase09_baseline": LOCKED_PHASE09_BASELINE,
        "pricing_evidence_reference": pricing.evidence_reference,
        "pricing_evidence_identity": pricing.identity,
        "blocked_readiness_reconciliation_reference": reconciliation.evidence_reference,
        "blocked_readiness_reconciliation_identity": reconciliation.identity,
        "credential_safe_gate_reference": gate.evidence_reference,
        "credential_safe_gate_identity": gate.identity,
        "policy_state": ShadowPhase11PricingFreshnessPolicyStateV1.ZERO_REUSE_WINDOW_REVALIDATION_REQUIRED,
        "maximum_reusable_pricing_evidence_age_seconds": 0,
        "positive_reuse_window_authorized": False,
        "cached_pricing_evidence_reusable_without_revalidation": False,
        "launch_time_pricing_revalidation_required": True,
        "pricing_revalidation_completed": False,
        "pricing_revalidation_execution_authorized": False,
        "current_time_access_required": False,
        "current_time_access_observed": False,
        "timestamp_bound": False,
        "historical_pricing_evidence_preserved": True,
        "historical_pricing_evidence_is_launch_current": False,
        "hard_cap_micro_usd": pricing.hard_cap_micro_usd,
        "reserve_micro_usd": pricing.safety_reserve_micro_usd,
        "maximum_spendable_micro_usd": pricing.spendable_cap_micro_usd,
        "worst_case_routed_item_micro_usd": pricing.conservative_worst_case_item_cost_micro_usd,
        "conservative_candidate_capacity": pricing.mathematical_safe_maximum_items,
        "budget_authority_modified": False,
        "pricing_values_revalidated": False,
        "provider_model_identifiers_revalidated": False,
        "credential_configuration_verified": False,
        "pre_call_reservation_created": False,
        "ledger_entry_created": False,
        "provider_pricing_request_created": False,
        "provider_request_created": False,
        "runtime_invocation_authorized": False,
        "provider_call_authorized": False,
        "provider_transmission_authorized": False,
        "run_size_authorized": False,
        "manifest_activation_authorized": False,
        "launch_authorized": False,
        "production_authorized": False,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
        "reason_codes": POLICY_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11PricingFreshnessPolicyEvidenceV1(**fields)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PricingFreshnessPolicyValidationError):
        _evidence(**overrides)


def test_closed_zero_reuse_policy_state_is_exact():
    assert tuple(ShadowPhase11PricingFreshnessPolicyStateV1) == (
        ShadowPhase11PricingFreshnessPolicyStateV1.ZERO_REUSE_WINDOW_REVALIDATION_REQUIRED,
    )


def test_zero_reuse_policy_is_static_and_never_authorizes_cached_pricing():
    evidence = _evidence()
    assert evidence.policy_state is ShadowPhase11PricingFreshnessPolicyStateV1.ZERO_REUSE_WINDOW_REVALIDATION_REQUIRED
    assert evidence.maximum_reusable_pricing_evidence_age_seconds == 0
    assert evidence.positive_reuse_window_authorized is False
    assert evidence.cached_pricing_evidence_reusable_without_revalidation is False
    assert evidence.launch_time_pricing_revalidation_required is True
    assert evidence.pricing_revalidation_completed is False
    assert evidence.pricing_revalidation_execution_authorized is False
    assert evidence.current_time_access_required is False
    assert evidence.current_time_access_observed is False
    assert evidence.timestamp_bound is False
    assert evidence.historical_pricing_evidence_preserved is True
    assert evidence.historical_pricing_evidence_is_launch_current is False


def test_policy_links_exact_evidence_and_preserves_cost_authority_without_revalidation():
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reconciliation = get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    evidence = _evidence()
    assert evidence.pricing_evidence_reference == pricing.evidence_reference == PRICING_REFERENCE
    assert evidence.pricing_evidence_identity == pricing.identity == PRICING_IDENTITY
    assert evidence.blocked_readiness_reconciliation_reference == reconciliation.evidence_reference == RECONCILIATION_REFERENCE
    assert evidence.blocked_readiness_reconciliation_identity == reconciliation.identity == RECONCILIATION_IDENTITY
    assert evidence.credential_safe_gate_reference == gate.evidence_reference == GATE_REFERENCE
    assert evidence.credential_safe_gate_identity == gate.identity == GATE_IDENTITY
    assert evidence.hard_cap_micro_usd == HARD_CAP
    assert evidence.reserve_micro_usd == RESERVE
    assert evidence.maximum_spendable_micro_usd == SPENDABLE
    assert evidence.worst_case_routed_item_micro_usd == WORST_CASE_ITEM
    assert evidence.conservative_candidate_capacity == CAPACITY
    assert evidence.budget_authority_modified is False
    assert evidence.pricing_values_revalidated is False
    assert evidence.provider_model_identifiers_revalidated is False


def test_policy_preserves_incomplete_revalidation_and_zero_operational_authority():
    evidence = _evidence()
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE"
    assert evidence.zero_production_effect_proof == "PROVEN_NONE"
    assert not any((
        evidence.credential_configuration_verified,
        evidence.pre_call_reservation_created,
        evidence.ledger_entry_created,
        evidence.provider_pricing_request_created,
        evidence.provider_request_created,
        evidence.runtime_invocation_authorized,
        evidence.provider_call_authorized,
        evidence.provider_transmission_authorized,
        evidence.run_size_authorized,
        evidence.manifest_activation_authorized,
        evidence.launch_authorized,
        evidence.production_authorized,
    ))


def test_constructor_rejects_reuse_time_linkage_cost_authority_and_identity_tampering():
    for name, value in (
        ("evidence_reference", "OTHER"),
        ("locked_repository_baseline", "0" * 40),
        ("locked_phase09_baseline", "0" * 40),
        ("pricing_evidence_reference", "OTHER"),
        ("pricing_evidence_identity", "0" * 64),
        ("blocked_readiness_reconciliation_reference", "OTHER"),
        ("blocked_readiness_reconciliation_identity", "0" * 64),
        ("credential_safe_gate_reference", "OTHER"),
        ("credential_safe_gate_identity", "0" * 64),
        ("policy_state", "FRESH"),
        ("maximum_reusable_pricing_evidence_age_seconds", -1),
        ("maximum_reusable_pricing_evidence_age_seconds", 1),
        ("positive_reuse_window_authorized", True),
        ("cached_pricing_evidence_reusable_without_revalidation", True),
        ("launch_time_pricing_revalidation_required", False),
        ("pricing_revalidation_completed", True),
        ("pricing_revalidation_execution_authorized", True),
        ("current_time_access_required", True),
        ("current_time_access_observed", True),
        ("timestamp_bound", True),
        ("historical_pricing_evidence_preserved", False),
        ("historical_pricing_evidence_is_launch_current", True),
        ("hard_cap_micro_usd", Decimal("1")),
        ("reserve_micro_usd", Decimal("1")),
        ("maximum_spendable_micro_usd", Decimal("1")),
        ("worst_case_routed_item_micro_usd", Decimal("1")),
        ("conservative_candidate_capacity", 19),
        ("budget_authority_modified", True),
        ("pricing_values_revalidated", True),
        ("provider_model_identifiers_revalidated", True),
        ("credential_configuration_verified", True),
        ("pre_call_reservation_created", True),
        ("ledger_entry_created", True),
        ("provider_pricing_request_created", True),
        ("provider_request_created", True),
        ("runtime_invocation_authorized", True),
        ("provider_call_authorized", True),
        ("provider_transmission_authorized", True),
        ("run_size_authorized", True),
        ("manifest_activation_authorized", True),
        ("launch_authorized", True),
        ("production_authorized", True),
        ("launch_readiness", "READY_FOR_LAUNCH"),
        ("production_effect", "SENT"),
        ("zero_production_effect_proof", "UNPROVEN"),
        ("evidence_id", "0" * 64),
    ):
        _reject(**{name: value})
    _reject(observed_at="2026-01-01T00:00:00Z")
    _reject(expiry_timestamp="2026-01-01T00:00:00Z")
    _reject(unknown_field="reject")


def test_reason_codes_are_exact_canonical_and_reject_missing_duplicate_or_authorizing_variants():
    evidence = _evidence(reason_codes=tuple(reversed(POLICY_REASONS)))
    assert evidence.reason_codes == POLICY_REASONS
    for reasons in (
        POLICY_REASONS[:-1],
        POLICY_REASONS + (POLICY_REASONS[0],),
        POLICY_REASONS + ("UNKNOWN_REASON",),
        POLICY_REASONS + ("PRICING_REVALIDATION_COMPLETED",),
        POLICY_REASONS + ("LAUNCH_AUTHORIZED",),
    ):
        _reject(reason_codes=reasons)


def test_canonical_identity_converges_diverges_and_future_module_has_no_time_or_side_effect_surface():
    first = _evidence(reason_codes=tuple(reversed(POLICY_REASONS)))
    second = _evidence(reason_codes=POLICY_REASONS)
    variant = _evidence(reason_codes=("MATERIAL_VARIANT",))
    assert first.identity == second.identity
    assert first.identity != variant.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    assert sha256_hex(b"zero-reuse-pricing-policy") == "9e194b63981d1f703dec7945339bab452d607d12362b80d6a0d5c4fdd19fcabe"
    evidence = get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1()
    assert type(evidence) is ShadowPhase11PricingFreshnessPolicyEvidenceV1
    assert evidence.identity == get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1().identity == _evidence().identity
    module = ast.parse(Path(FUTURE_PATH).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "zoneinfo", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "keyring", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "material_for_adapter", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
