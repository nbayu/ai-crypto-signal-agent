"""RED contract for immutable Phase 11 pre-call reservation-bound evidence.

This suite freezes calculation-only reservation bounds derived solely from
committed pricing evidence.  It grants no reservation, spend, provider,
credential, manifest, launch, production, or Phase 12 authority.
"""

from __future__ import annotations

import ast
import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotPricingRevalidationStatusV1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    ShadowPhase11PilotRouteV1,
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    ShadowPhase11PreCallReservationBoundV1,
    ShadowPhase11PreCallReservationStateV1,
    ShadowPhase11PreCallReservationValidationError,
    ShadowPhase11ReservationCalculationModeV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
    sha256_hex,
)


LOCKED_REPOSITORY_BASELINE = "6f6647d21a312a54ba14e764e3a81177c2ae0700"
LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
BUDGET_AUTHORIZATION_REFERENCE = "PHASE_11_SHADOW_PILOT_BUDGET_USD_5_001"
MODEL_COST_AUTHORIZATION_REFERENCE = "PHASE_11_PILOT_MODEL_COST_BOUNDS_001"
PRICING_EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
PER_ITEM_BOUND_MICRO_USD = Decimal("216700")
HARD_CAP_MICRO_USD = Decimal("5000000")
SAFETY_RESERVE_MICRO_USD = Decimal("500000")
SPENDABLE_CAP_MICRO_USD = Decimal("4500000")
ZERO_MICRO_USD = Decimal("0")


def _pricing_evidence():
    return get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()


def _bound(**overrides: object) -> ShadowPhase11PreCallReservationBoundV1:
    pricing_evidence = _pricing_evidence()
    values = {
        "schema_version": "phase11-shadow-pilot-pre-call-reservation-bound-v1",
        "reservation_bound_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "pricing_evidence_reference": pricing_evidence.evidence_reference,
        "pricing_evidence_identity": pricing_evidence.identity,
        "budget_authorization_reference": BUDGET_AUTHORIZATION_REFERENCE,
        "model_cost_authorization_reference": MODEL_COST_AUTHORIZATION_REFERENCE,
        "locked_repository_baseline": LOCKED_REPOSITORY_BASELINE,
        "locked_phase09_baseline": LOCKED_PHASE09_BASELINE,
        "reservation_state": ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED,
        "calculation_mode": ShadowPhase11ReservationCalculationModeV1.CONSERVATIVE_WORST_CASE_PER_ITEM,
        "conservative_worst_case_route": pricing_evidence.conservative_worst_case_route,
        "per_item_reservation_bound_micro_usd": pricing_evidence.conservative_worst_case_item_cost_micro_usd,
        "hard_cap_micro_usd": pricing_evidence.hard_cap_micro_usd,
        "safety_reserve_micro_usd": pricing_evidence.safety_reserve_micro_usd,
        "spendable_cap_micro_usd": pricing_evidence.spendable_cap_micro_usd,
        "mathematical_safe_maximum_items": pricing_evidence.mathematical_safe_maximum_items,
        "safe_capacity_total_micro_usd": pricing_evidence.safe_capacity_total_micro_usd,
        "next_item_total_micro_usd": pricing_evidence.next_item_total_micro_usd,
        "reservation_required_before_provider_transmission": True,
        "pricing_revalidation_required_before_reservation_use": True,
        "launch_time_pricing_revalidation_required": pricing_evidence.launch_time_pricing_revalidation_required,
        "fixed_freshness_window_defined": pricing_evidence.fixed_freshness_window_defined,
        "pricing_revalidation_status": pricing_evidence.pricing_revalidation_status,
        "launch_readiness": pricing_evidence.launch_readiness,
        "run_size_authorized": False,
        "reservation_creation_authorized": False,
        "ledger_mutation_authorized": False,
        "provider_call_authorized": False,
        "budget_reserved_micro_usd": pricing_evidence.budget_reserved_micro_usd,
        "budget_consumed_micro_usd": pricing_evidence.budget_consumed_micro_usd,
        "production_effect": pricing_evidence.production_effect,
        "zero_production_effect_proof": pricing_evidence.zero_production_effect_proof,
        "reason_codes": ("CONSERVATIVE_PRE_CALL_RESERVATION_BOUND",),
    }
    values.update(overrides)
    return ShadowPhase11PreCallReservationBoundV1(**values)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PreCallReservationValidationError):
        _bound(**overrides)


def test_required_enums_are_closed_calculation_only_states():
    assert tuple(ShadowPhase11PreCallReservationStateV1) == (
        ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED,
    )
    assert tuple(ShadowPhase11ReservationCalculationModeV1) == (
        ShadowPhase11ReservationCalculationModeV1.CONSERVATIVE_WORST_CASE_PER_ITEM,
    )
    assert tuple(item.value for item in ShadowPhase11PreCallReservationStateV1) == (
        "BOUND_NOT_RESERVED",
    )
    assert tuple(item.value for item in ShadowPhase11ReservationCalculationModeV1) == (
        "CONSERVATIVE_WORST_CASE_PER_ITEM",
    )


def test_concrete_bound_links_exact_committed_pricing_evidence_and_zero_authority():
    pricing_evidence = _pricing_evidence()
    bound = _bound()
    assert bound.evidence_reference == EVIDENCE_REFERENCE
    assert bound.pricing_evidence_reference == pricing_evidence.evidence_reference == PRICING_EVIDENCE_REFERENCE
    assert bound.pricing_evidence_identity == pricing_evidence.identity
    assert bound.budget_authorization_reference == BUDGET_AUTHORIZATION_REFERENCE
    assert bound.model_cost_authorization_reference == MODEL_COST_AUTHORIZATION_REFERENCE
    assert bound.locked_repository_baseline == LOCKED_REPOSITORY_BASELINE
    assert bound.locked_phase09_baseline == LOCKED_PHASE09_BASELINE
    assert bound.reservation_state is ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED
    assert bound.calculation_mode is ShadowPhase11ReservationCalculationModeV1.CONSERVATIVE_WORST_CASE_PER_ITEM
    assert bound.conservative_worst_case_route is ShadowPhase11PilotRouteV1.L1_TO_L2
    assert bound.per_item_reservation_bound_micro_usd == PER_ITEM_BOUND_MICRO_USD
    assert bound.hard_cap_micro_usd == HARD_CAP_MICRO_USD
    assert bound.safety_reserve_micro_usd == SAFETY_RESERVE_MICRO_USD
    assert bound.spendable_cap_micro_usd == SPENDABLE_CAP_MICRO_USD
    assert bound.mathematical_safe_maximum_items == 20
    assert bound.safe_capacity_total_micro_usd == Decimal("4334000")
    assert bound.next_item_total_micro_usd == Decimal("4550700")
    assert bound.reservation_required_before_provider_transmission is True
    assert bound.pricing_revalidation_required_before_reservation_use is True
    assert bound.launch_time_pricing_revalidation_required is True
    assert bound.fixed_freshness_window_defined is False
    assert bound.pricing_revalidation_status is ShadowPhase11PilotPricingRevalidationStatusV1.REQUIRED_NOT_COMPLETED
    assert bound.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert bound.run_size_authorized is False
    assert bound.reservation_creation_authorized is False
    assert bound.ledger_mutation_authorized is False
    assert bound.provider_call_authorized is False
    assert bound.budget_reserved_micro_usd == ZERO_MICRO_USD
    assert bound.budget_consumed_micro_usd == ZERO_MICRO_USD
    assert bound.production_effect == "NONE"
    assert bound.zero_production_effect_proof == "PROVEN_NONE"
    forbidden_fields = {
        "selected_item_count", "authorized_item_count", "pilot_item_ids", "candidate_ids",
        "selected_route", "event_id", "input_payload", "run_id", "manifest_id",
        "credential_reference", "fixed_freshness_window",
        "reservation_id", "ledger_transaction_id", "reserve", "commit", "release",
        "refund", "consume", "provider_call", "authorize_launch", "phase11_completion",
        "phase12_activation", "telegram", "account", "order", "trading", "publication",
        "deployment",
    }
    assert not set(bound.__dataclass_fields__) & forbidden_fields
    with pytest.raises((AttributeError, TypeError)):
        bound.budget_consumed_micro_usd = Decimal("1")


def test_pure_mathematical_calculation_is_exact_bounded_and_does_not_change_evidence():
    bound = _bound()
    identity = bound.identity
    assert bound.calculate_mathematical_reservation_bound_micro_usd(1) == Decimal("216700")
    assert bound.calculate_mathematical_reservation_bound_micro_usd(2) == Decimal("433400")
    assert bound.calculate_mathematical_reservation_bound_micro_usd(20) == Decimal("4334000")
    assert bound.identity == identity
    assert bound.reservation_state is ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED
    assert bound.budget_reserved_micro_usd == bound.budget_consumed_micro_usd == ZERO_MICRO_USD
    for invalid_count in (0, -1, 21, True, False, Decimal("1"), 1.0, "1"):
        with pytest.raises(ShadowPhase11PreCallReservationValidationError):
            bound.calculate_mathematical_reservation_bound_micro_usd(invalid_count)


def test_constructor_rejects_tampered_pricing_linkage_caps_capacity_revalidation_and_authority():
    _reject(pricing_evidence_reference="PHASE_11_OTHER_PRICING_EVIDENCE_001")
    _reject(pricing_evidence_identity="0" * 64)
    _reject(locked_repository_baseline="0" * 40)
    _reject(conservative_worst_case_route=ShadowPhase11PilotRouteV1.L1)
    _reject(per_item_reservation_bound_micro_usd=Decimal("216701"))
    _reject(hard_cap_micro_usd=Decimal("4999999"))
    _reject(safety_reserve_micro_usd=Decimal("499999"))
    _reject(spendable_cap_micro_usd=Decimal("4499999"))
    _reject(mathematical_safe_maximum_items=19)
    _reject(safe_capacity_total_micro_usd=Decimal("4334001"))
    _reject(next_item_total_micro_usd=Decimal("4550699"))
    _reject(pricing_revalidation_status="COMPLETED")
    _reject(launch_time_pricing_revalidation_required=False)
    _reject(pricing_revalidation_required_before_reservation_use=False)
    _reject(fixed_freshness_window_defined=True)
    _reject(launch_readiness="READY_FOR_LAUNCH")
    _reject(run_size_authorized=True)
    _reject(reservation_creation_authorized=True)
    _reject(ledger_mutation_authorized=True)
    _reject(provider_call_authorized=True)
    _reject(budget_reserved_micro_usd=Decimal("1"))
    _reject(budget_consumed_micro_usd=Decimal("1"))
    _reject(reservation_state="RESERVED")
    _reject(production_effect="SENT")
    _reject(zero_production_effect_proof="UNPROVEN")
    _reject(reservation_bound_id="0" * 64)
    _reject(unknown_field="reject")


def test_identity_converges_for_canonical_reason_order_and_diverges_for_valid_material_change():
    first = _bound(reason_codes=("BOUND_EVIDENCE", "PRE_CALL_REQUIRED"))
    second = _bound(reason_codes=("PRE_CALL_REQUIRED", "BOUND_EVIDENCE"))
    variant = _bound(reason_codes=("CONSERVATIVE_PRE_CALL_RESERVATION_VARIANT",))
    assert first.identity == second.identity
    assert first.identity != variant.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    assert sha256_hex(b"pre-call-reservation-bound") == hashlib.sha256(b"pre-call-reservation-bound").hexdigest()


def test_zero_argument_accessor_is_deterministic_and_matches_concrete_bound():
    first = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    second = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    assert type(first) is ShadowPhase11PreCallReservationBoundV1
    assert first.identity == second.identity == _bound().identity
    assert first.pricing_evidence_identity == _pricing_evidence().identity
    assert first.calculate_mathematical_reservation_bound_micro_usd(20) == Decimal("4334000")


def test_static_dependency_and_side_effect_boundary():
    module = ast.parse(Path("engine/phase_11_shadow_pilot_pre_call_reservation_bound_v1.py").read_text(encoding="utf-8"))
    forbidden_modules = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess",
        "threading", "multiprocessing", "concurrent", "asyncio", "pytest",
    }
    forbidden_names = {
        "open", "float", "resolve_provider_credential", "DeepSeekShadowTransportAdapterV1",
        "AnthropicShadowTransportAdapterV1", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1",
        "reserve_call", "commit_usage", "release_reservation", "reconcile_uncertain_usage",
        "requests", "http", "telegram", "account", "exchange", "order", "position", "trading",
        "publication", "deployment", "persistence", "datetime_now", "utcnow",
    }
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.With)) for node in ast.walk(module))
