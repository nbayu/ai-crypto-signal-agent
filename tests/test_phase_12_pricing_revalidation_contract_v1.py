"""RED contract for pure, fail-closed Phase 12 pricing revalidation."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass
from decimal import Decimal
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from engine.phase_12_pricing_revalidation_contract_v1 import (
    PricingObservationV1,
    PricingPolicyV1,
    PricingRevalidationAuditEvidenceV1,
    PricingRevalidationFailureV1,
    PricingRevalidationResultV1,
    RequestCostEstimateV1,
    build_pricing_revalidation_audit_evidence_v1,
    estimate_request_cost_v1,
    revalidate_pricing_observation_v1,
)


_EVALUATION = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
_QUANTUM = Decimal("0.00000001")
_OBSERVATION_FIELDS = (
    "observation_id", "source_id", "source_version", "provider_id", "route_id", "model_id",
    "currency", "input_price_per_million_tokens", "output_price_per_million_tokens",
    "effective_at", "observed_at", "expires_at", "network_accessed", "provider_contacted",
)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "allowed_source_ids", "allowed_provider_ids",
    "allowed_route_ids", "allowed_model_ids", "required_currency",
    "maximum_observation_age_seconds", "maximum_future_effective_skew_seconds",
    "input_token_ceiling", "output_token_ceiling", "request_cost_ceiling", "run_cost_ceiling",
    "quantization_unit", "conservative_rounding", "fail_closed",
    "network_revalidation_authorized", "reservation_creation_authorized", "provider_execution_authorized",
)
_RESULT_FIELDS = (
    "observation_id", "policy_id", "valid", "failure_codes", "pricing_fresh", "source_allowed",
    "provider_allowed", "route_allowed", "model_allowed", "currency_allowed", "time_order_valid",
    "network_accessed", "provider_contacted", "reservation_authorized", "provider_execution_authorized",
)
_ESTIMATE_FIELDS = (
    "observation_id", "provider_id", "route_id", "model_id", "currency", "input_tokens",
    "output_tokens", "input_cost", "output_cost", "total_cost", "quantization_unit",
    "within_token_ceiling", "within_request_cost_ceiling", "within_run_cost_ceiling",
    "pricing_revalidated", "reservation_authorized", "provider_execution_authorized",
)
_FAILURES = {
    "OBSERVATION_ID_EMPTY", "SOURCE_ID_EMPTY", "SOURCE_VERSION_EMPTY", "PROVIDER_ID_EMPTY",
    "ROUTE_ID_EMPTY", "MODEL_ID_EMPTY", "IDENTIFIER_NOT_NORMALIZED", "CURRENCY_NOT_ALLOWED",
    "MONETARY_VALUE_INVALID", "INPUT_PRICE_INVALID", "OUTPUT_PRICE_INVALID", "EFFECTIVE_TIME_INVALID",
    "OBSERVED_TIME_INVALID", "EXPIRY_TIME_INVALID", "TIMEZONE_NOT_UTC", "TIME_ORDER_INVALID",
    "OBSERVATION_NOT_YET_EFFECTIVE", "OBSERVATION_EXPIRED", "OBSERVATION_TOO_OLD",
    "FUTURE_EFFECTIVE_SKEW_EXCEEDED", "SOURCE_NOT_ALLOWED", "PROVIDER_NOT_ALLOWED",
    "ROUTE_NOT_ALLOWED", "MODEL_NOT_ALLOWED", "NO_PRICING_SOURCE_APPROVED",
    "NO_PROVIDER_APPROVED", "NO_ROUTE_APPROVED", "NO_MODEL_APPROVED", "TOKEN_CEILINGS_ZERO",
    "REQUEST_COST_CEILING_ZERO", "RUN_COST_CEILING_ZERO", "NETWORK_REVALIDATION_NOT_AUTHORIZED",
    "RESERVATION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED",
}


def _observation() -> PricingObservationV1:
    return PricingObservationV1(
        "observation-v1", "source-v1", "version-v1", "provider-v1", "route-v1", "model-v1", "USD",
        Decimal("1.25"), Decimal("2.50"), _EVALUATION - timedelta(minutes=1),
        _EVALUATION, _EVALUATION + timedelta(minutes=5), False, False,
    )


def _policy() -> PricingPolicyV1:
    return PricingPolicyV1(
        "policy-v1", "V1", (), (), (), (), "USD", 300, 0, 0, 0,
        Decimal("0"), Decimal("0"), _QUANTUM, True, True, False, False, False,
    )


def _assert_frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_decimal_only_and_fail_closed() -> None:
    assert tuple(field.name for field in fields(PricingObservationV1)) == _OBSERVATION_FIELDS
    assert tuple(field.name for field in fields(PricingPolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(PricingRevalidationResultV1)) == _RESULT_FIELDS
    assert tuple(field.name for field in fields(RequestCostEstimateV1)) == _ESTIMATE_FIELDS
    observation, policy = _observation(), _policy()
    result = revalidate_pricing_observation_v1(observation, policy, _EVALUATION)
    evidence = build_pricing_revalidation_audit_evidence_v1(observation, policy, result, _EVALUATION)
    for value in (observation, policy, result, evidence):
        _assert_frozen_slotted(value)
    assert isinstance(observation.input_price_per_million_tokens, Decimal)
    assert isinstance(policy.request_cost_ceiling, Decimal)
    with pytest.raises(FrozenInstanceError):
        observation.network_accessed = True  # type: ignore[misc]
    with pytest.raises(ValueError):
        PricingObservationV1(
            "observation-v1", "source-v1", "version-v1", "provider-v1", "route-v1", "model-v1", "USD",
            1.25, Decimal("2.50"), _EVALUATION, _EVALUATION, _EVALUATION + timedelta(seconds=1), False, False,
        )


def test_empty_allowlists_and_zero_ceilings_are_valid_metadata_but_fail_closed() -> None:
    result = revalidate_pricing_observation_v1(_observation(), _policy(), _EVALUATION)
    assert result.valid is False
    assert {
        "NO_PRICING_SOURCE_APPROVED", "NO_PROVIDER_APPROVED", "NO_ROUTE_APPROVED", "NO_MODEL_APPROVED",
        "TOKEN_CEILINGS_ZERO", "REQUEST_COST_CEILING_ZERO", "RUN_COST_CEILING_ZERO",
        "NETWORK_REVALIDATION_NOT_AUTHORIZED", "RESERVATION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert (result.network_accessed, result.provider_contacted, result.reservation_authorized, result.provider_execution_authorized) == (False, False, False, False)


def test_time_boundaries_and_injected_freshness_are_deterministic() -> None:
    policy = _policy()
    exactly_expired = PricingObservationV1(
        "obs-expired", "source-v1", "version-v1", "provider-v1", "route-v1", "model-v1", "USD",
        Decimal("1"), Decimal("1"), _EVALUATION, _EVALUATION, _EVALUATION, False, False,
    )
    result = revalidate_pricing_observation_v1(exactly_expired, policy, _EVALUATION)
    assert "OBSERVATION_EXPIRED" in result.failure_codes
    too_old = PricingObservationV1(
        "obs-old", "source-v1", "version-v1", "provider-v1", "route-v1", "model-v1", "USD",
        Decimal("1"), Decimal("1"), _EVALUATION - timedelta(seconds=301),
        _EVALUATION - timedelta(seconds=301), _EVALUATION + timedelta(seconds=1), False, False,
    )
    assert "OBSERVATION_TOO_OLD" in revalidate_pricing_observation_v1(too_old, policy, _EVALUATION).failure_codes


def test_cost_estimation_requires_revalidated_pricing_and_never_authorizes_execution() -> None:
    observation, policy = _observation(), _policy()
    result = revalidate_pricing_observation_v1(observation, policy, _EVALUATION)
    with pytest.raises(ValueError):
        estimate_request_cost_v1(observation, policy, result, 1, 1)
    with pytest.raises(ValueError):
        estimate_request_cost_v1(observation, policy, result, True, 1)
    assert list(inspect.signature(estimate_request_cost_v1).parameters) == [
        "observation", "policy", "revalidation_result", "input_tokens", "output_tokens"
    ]


def test_module_has_no_operational_dependency_or_clock_surface() -> None:
    import engine.phase_12_pricing_revalidation_contract_v1 as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    prohibited = {"os", "pathlib", "subprocess", "socket", "urllib", "http", "requests", "httpx", "aiohttp", "openai", "ccxt", "telegram"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not prohibited.intersection(names | imports)
    assert not {"open", "print", "getenv", "environ", "now", "utcnow", "time", "monotonic", "__import__"}.intersection(names)
