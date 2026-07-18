"""RED contract for Phase 11 pilot model-and-cost authority evidence.

This suite freezes only the Project Owner's bounded shadow-pilot authority.
It contains no pricing, credential, provider-availability, launch, or runtime
evidence, and it does not represent an executed pilot.
"""

from __future__ import annotations

import ast
import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_budget_control_v1 import PROVIDERS
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotAuthorityValidationError,
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotModelCostAuthorityV1,
    ShadowPhase11PilotPricingRevalidationStatusV1,
    ShadowPhase11PilotProviderBoundV1,
    ShadowPhase11PilotProviderRoleV1,
    ShadowPhase11PilotRetryPolicyV1,
    ShadowPhase11PilotSpendScopeV1,
    canonical_json_bytes,
    sha256_hex,
)


BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
AUTHORIZATION_REFERENCE = "PHASE_11_PILOT_MODEL_COST_BOUNDS_001"
BUDGET_AUTHORIZATION_REFERENCE = "PHASE_11_SHADOW_PILOT_BUDGET_USD_5_001"
HARD_CAP_USD = Decimal("5.00")
HARD_CAP_MICRO_USD = Decimal("5000000")
SAFETY_RESERVE_USD = Decimal("0.50")
SAFETY_RESERVE_MICRO_USD = Decimal("500000")
SPENDABLE_CAP_USD = Decimal("4.50")
SPENDABLE_CAP_MICRO_USD = Decimal("4500000")
ZERO_MICRO_USD = Decimal("0")


def _bound(
    role: ShadowPhase11PilotProviderRoleV1,
    **overrides: object,
) -> ShadowPhase11PilotProviderBoundV1:
    assignments = {
        ShadowPhase11PilotProviderRoleV1.PRIMARY: ("DEEPSEEK", "deepseek-v4-pro"),
        ShadowPhase11PilotProviderRoleV1.L1: ("ANTHROPIC", "claude-sonnet-5"),
        ShadowPhase11PilotProviderRoleV1.L2: ("ANTHROPIC", "claude-opus-4-8"),
    }
    provider, model_identifier = assignments.get(role, ("DEEPSEEK", "unknown"))
    values = {
        "schema_version": "phase11-shadow-pilot-provider-bound-v1",
        "provider_bound_id": None,
        "role": role,
        "provider": provider,
        "model_identifier": model_identifier,
        "maximum_input_tokens": 16000,
        "maximum_output_tokens": 2000,
        "maximum_attempts": 1,
        "provider_error_retry_policy": ShadowPhase11PilotRetryPolicyV1.FORBIDDEN,
        "credential_error_retry_policy": ShadowPhase11PilotRetryPolicyV1.FORBIDDEN,
        "authentication_error_retry_policy": ShadowPhase11PilotRetryPolicyV1.FORBIDDEN,
        "reason_codes": ("OWNER_AUTHORIZED_PILOT_BOUND",),
    }
    values.update(overrides)
    return ShadowPhase11PilotProviderBoundV1(**values)


def _authority(**overrides: object) -> ShadowPhase11PilotModelCostAuthorityV1:
    values = {
        "schema_version": "phase11-shadow-pilot-model-cost-authority-v1",
        "authority_id": None,
        "authorization_reference": AUTHORIZATION_REFERENCE,
        "budget_authorization_reference": BUDGET_AUTHORIZATION_REFERENCE,
        "locked_baseline_commit": BASELINE,
        "provider_bounds": tuple(_bound(role) for role in ShadowPhase11PilotProviderRoleV1),
        "currency": "USD_MICRO",
        "hard_cap_usd": HARD_CAP_USD,
        "hard_cap_micro_usd": HARD_CAP_MICRO_USD,
        "safety_reserve_usd": SAFETY_RESERVE_USD,
        "safety_reserve_micro_usd": SAFETY_RESERVE_MICRO_USD,
        "spendable_cap_usd": SPENDABLE_CAP_USD,
        "spendable_cap_micro_usd": SPENDABLE_CAP_MICRO_USD,
        "reserved_micro_usd": ZERO_MICRO_USD,
        "committed_micro_usd": ZERO_MICRO_USD,
        "remaining_authorized_micro_usd": HARD_CAP_MICRO_USD,
        "spend_scope": ShadowPhase11PilotSpendScopeV1.SHADOW_EVIDENCE_ACQUISITION_ONLY,
        "pricing_revalidation_status": ShadowPhase11PilotPricingRevalidationStatusV1.REQUIRED_NOT_COMPLETED,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "account_order_trading_authority": "NONE",
        "phase_12_activation_authority": "NOT_AUTHORIZED",
        "reason_codes": ("EXPLICIT_OWNER_PILOT_AUTHORITY",),
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowPhase11PilotModelCostAuthorityV1(**values)


def _reject_bound(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PilotAuthorityValidationError):
        _bound(ShadowPhase11PilotProviderRoleV1.PRIMARY, **overrides)


def _reject_authority(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PilotAuthorityValidationError):
        _authority(**overrides)


def test_contracts_are_closed_immutable_and_authority_only():
    for contract in (ShadowPhase11PilotProviderBoundV1, ShadowPhase11PilotModelCostAuthorityV1):
        assert getattr(contract, "__slots__") and "__dict__" not in contract.__slots__
    authority_fields = set(ShadowPhase11PilotModelCostAuthorityV1.__dataclass_fields__)
    forbidden_fields = {
        "input_price", "output_price", "cache_price", "batch_price", "discount",
        "worst_case_call_cost", "safe_pilot_item_count", "provider_availability",
        "credential_reference", "provider_call", "run_manifest", "launch", "phase11_completion",
        "phase11_pass", "phase12_enabled", "approved_budget", "spending_authorization",
        "publication", "deployment", "telegram", "persistence",
    }
    assert not authority_fields & forbidden_fields
    with pytest.raises((AttributeError, TypeError)):
        _authority().hard_cap_micro_usd = Decimal("1")


def test_exact_owner_authority_binds_three_canonical_model_roles():
    authority = _authority()
    assert authority.authorization_reference == AUTHORIZATION_REFERENCE
    assert authority.budget_authorization_reference == BUDGET_AUTHORIZATION_REFERENCE
    assert authority.locked_baseline_commit == BASELINE
    assert tuple(item.role for item in authority.provider_bounds) == tuple(ShadowPhase11PilotProviderRoleV1)
    assert tuple((item.provider, item.model_identifier) for item in authority.provider_bounds) == (
        ("DEEPSEEK", "deepseek-v4-pro"),
        ("ANTHROPIC", "claude-sonnet-5"),
        ("ANTHROPIC", "claude-opus-4-8"),
    )
    assert set(item.provider for item in authority.provider_bounds) <= set(PROVIDERS)


def test_every_provider_bound_has_exact_token_one_attempt_and_no_retry_rules():
    for bound in _authority().provider_bounds:
        assert bound.maximum_input_tokens == 16000
        assert bound.maximum_output_tokens == 2000
        assert bound.maximum_attempts == 1
        assert bound.provider_error_retry_policy is ShadowPhase11PilotRetryPolicyV1.FORBIDDEN
        assert bound.credential_error_retry_policy is ShadowPhase11PilotRetryPolicyV1.FORBIDDEN
        assert bound.authentication_error_retry_policy is ShadowPhase11PilotRetryPolicyV1.FORBIDDEN


def test_provider_bound_rejects_role_model_provider_token_attempt_and_retry_variance():
    _reject_bound(role="UNKNOWN")
    _reject_bound(provider="ANTHROPIC")
    _reject_bound(model_identifier="claude-opus-4-8")
    _reject_bound(model_identifier="")
    for field, value in (("maximum_input_tokens", 0), ("maximum_output_tokens", -1), ("maximum_attempts", 2)):
        _reject_bound(**{field: value})
    _reject_bound(provider_error_retry_policy="ALLOWED")
    _reject_bound(unknown_field="reject")


def test_authority_requires_each_role_exactly_once_and_canonicalizes_reversed_bounds():
    bounds = _authority().provider_bounds
    assert _authority(provider_bounds=tuple(reversed(bounds))).identity == _authority().identity
    _reject_authority(provider_bounds=bounds[:-1])
    _reject_authority(provider_bounds=(bounds[0], bounds[0], bounds[2]))


def test_exact_usd_and_micro_usd_money_reconciliation_is_decimal_only():
    authority = _authority()
    assert authority.currency == "USD_MICRO"
    assert authority.hard_cap_usd == HARD_CAP_USD
    assert authority.hard_cap_micro_usd == HARD_CAP_MICRO_USD
    assert authority.safety_reserve_usd == SAFETY_RESERVE_USD
    assert authority.safety_reserve_micro_usd == SAFETY_RESERVE_MICRO_USD
    assert authority.spendable_cap_usd == SPENDABLE_CAP_USD
    assert authority.spendable_cap_micro_usd == SPENDABLE_CAP_MICRO_USD
    assert authority.hard_cap_usd - authority.safety_reserve_usd == authority.spendable_cap_usd
    assert authority.hard_cap_micro_usd - authority.safety_reserve_micro_usd == authority.spendable_cap_micro_usd
    assert authority.reserved_micro_usd == authority.committed_micro_usd == ZERO_MICRO_USD
    assert authority.remaining_authorized_micro_usd == HARD_CAP_MICRO_USD


def test_money_validation_rejects_float_negative_zero_cap_reserve_over_cap_and_inconsistent_scales():
    _reject_authority(hard_cap_usd=5.0)
    _reject_authority(hard_cap_usd=Decimal("0"))
    _reject_authority(safety_reserve_usd=Decimal("5.00"))
    _reject_authority(hard_cap_micro_usd=Decimal("4999999"))
    _reject_authority(safety_reserve_micro_usd=Decimal("500001"))
    _reject_authority(currency="USD")
    _reject_authority(reserved_micro_usd=Decimal("1"))
    _reject_authority(committed_micro_usd=Decimal("1"))


def test_pricing_revalidation_is_required_but_incomplete_and_launch_is_not_ready():
    authority = _authority()
    assert authority.pricing_revalidation_status is ShadowPhase11PilotPricingRevalidationStatusV1.REQUIRED_NOT_COMPLETED
    assert authority.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    _reject_authority(pricing_revalidation_status="COMPLETED")
    _reject_authority(launch_readiness="READY_FOR_LAUNCH")
    assert not hasattr(ShadowPhase11PilotModelCostAuthorityV1, "authorize_launch")


def test_identity_converges_for_equivalent_bounds_and_diverges_for_material_authority_changes():
    first = _authority()
    assert first.identity == _authority().identity
    assert first.identity != _authority(authorization_reference="PHASE_11_PILOT_MODEL_COST_BOUNDS_002").identity
    changed_bounds = list(first.provider_bounds)
    changed_bounds[0] = _bound(
        ShadowPhase11PilotProviderRoleV1.PRIMARY,
        reason_codes=("OWNER_AUTHORIZED_PILOT_BOUND_VARIANT",),
    )
    assert first.identity != _authority(provider_bounds=tuple(changed_bounds)).identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\xc3\xa9"}'
    assert sha256_hex(b"pilot-authority") == hashlib.sha256(b"pilot-authority").hexdigest()


def test_static_dependency_and_side_effect_boundary():
    module = ast.parse(Path("engine/phase_11_shadow_pilot_model_cost_authority_v1.py").read_text(encoding="utf-8"))
    forbidden_modules = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess",
        "threading", "multiprocessing", "concurrent", "asyncio", "pytest",
    }
    forbidden_names = {
        "open", "float", "resolve_provider_credential", "DeepSeekShadowTransportAdapterV1",
        "AnthropicShadowTransportAdapterV1", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1",
        "BudgetLedgerV1", "reserve_call", "commit_usage", "publication", "telegram", "account",
        "exchange", "order", "position", "trading", "deployment", "persistence",
    }
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.With)) for node in ast.walk(module))
