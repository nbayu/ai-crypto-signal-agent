"""RED contract for immutable Phase 11 pricing-revalidation boundary."""

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
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)
from engine.phase_11_shadow_pilot_pricing_freshness_policy_v1 import (
    get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1,
)
from engine.phase_11_shadow_pilot_pricing_revalidation_boundary_v1 import (
    ShadowPhase11PricingRevalidationBoundaryEvidenceV1,
    ShadowPhase11PricingRevalidationBoundaryStateV1,
    ShadowPhase11PricingRevalidationBoundaryValidationError,
    ShadowPhase11PricingRevalidationCheckKindV1,
    ShadowPhase11PricingRevalidationRequestV1,
    ShadowPhase11PricingRevalidationResultBoundaryV1,
    ShadowPhase11PricingRevalidationResultStateV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1,
    sha256_hex,
)


BASELINE = "a664af4f6efdc32e1b669bc9931d5850ae5c9a3f"
PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
REQUEST_REFERENCE = "PHASE_11_PILOT_PRICING_REVALIDATION_REQUEST_001"
RESULT_REFERENCE = "PHASE_11_PILOT_PRICING_REVALIDATION_RESULT_BOUNDARY_001"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001"
CHECKS = (
    ShadowPhase11PricingRevalidationCheckKindV1.PROVIDER_MODEL_IDENTIFIERS,
    ShadowPhase11PricingRevalidationCheckKindV1.PROVIDER_CONTEXT_AND_OUTPUT_LIMITS,
    ShadowPhase11PricingRevalidationCheckKindV1.PROVIDER_INPUT_AND_OUTPUT_PRICING,
    ShadowPhase11PricingRevalidationCheckKindV1.WORST_CASE_ROUTE_COST,
    ShadowPhase11PricingRevalidationCheckKindV1.CONSERVATIVE_CANDIDATE_CAPACITY,
)
REQUEST_REASONS = tuple(sorted((
    "EXACT_REVALIDATION_CHECKS_DEFINED",
    "NO_CREDENTIAL_AUTHORITY",
    "NO_CURRENT_TIME_AUTHORITY",
    "NO_NETWORK_AUTHORITY",
    "NO_PROVIDER_PRICING_REQUEST",
    "PRICING_REVALIDATION_EXECUTION_NOT_AUTHORIZED",
    "REPOSITORY_OWNED_REQUEST_DESCRIPTOR",
)))
RESULT_REASONS = tuple(sorted((
    "NO_FRESH_SOURCE_OBSERVATION",
    "NO_RESULT_IDENTITY",
    "NO_RESULT_REFERENCE",
    "PRICING_REVALIDATION_NOT_STARTED",
    "RESULT_ABSENT_NOT_EXECUTED",
)))
EVIDENCE_REASONS = tuple(sorted((
    "NO_OPERATIONAL_AUTHORITY",
    "NO_PRICING_LOOKUP_AUTHORITY",
    "PRICING_REVALIDATION_EXECUTION_NOT_AUTHORIZED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "PRICING_REVALIDATION_REQUEST_DEFINED",
    "PRICING_REVALIDATION_RESULT_ABSENT",
    "ZERO_REUSE_POLICY_ACTIVE",
)))
FUTURE_PATH = "engine/phase_11_shadow_pilot_pricing_revalidation_boundary_v1.py"


def _request(**overrides: object) -> ShadowPhase11PricingRevalidationRequestV1:
    policy = get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-pricing-revalidation-request-v1",
        "request_id": None,
        "request_reference": REQUEST_REFERENCE,
        "pricing_freshness_policy_reference": policy.evidence_reference,
        "pricing_freshness_policy_identity": policy.identity,
        "pricing_evidence_reference": pricing.evidence_reference,
        "pricing_evidence_identity": pricing.identity,
        "check_kinds": CHECKS,
        "primary_model_identifier": "deepseek-v4-pro",
        "l1_model_identifier": "claude-sonnet-5",
        "l2_model_identifier": "claude-opus-4-8",
        "maximum_input_tokens": 16000,
        "maximum_output_tokens": 2000,
        "maximum_attempts": 1,
        "hard_cap_micro_usd": Decimal("5000000"),
        "reserve_micro_usd": Decimal("500000"),
        "maximum_spendable_micro_usd": Decimal("4500000"),
        "worst_case_routed_item_micro_usd": Decimal("216700"),
        "conservative_candidate_capacity": 20,
        "request_defined": True,
        "execution_authorized": False,
        "network_access_authorized": False,
        "credential_access_authorized": False,
        "current_time_access_authorized": False,
        "provider_pricing_request_created": False,
        "reason_codes": REQUEST_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11PricingRevalidationRequestV1(**fields)


def _result(**overrides: object) -> ShadowPhase11PricingRevalidationResultBoundaryV1:
    request = _request()
    fields = {
        "schema_version": "phase11-shadow-pilot-pricing-revalidation-result-boundary-v1",
        "result_boundary_id": None,
        "result_boundary_reference": RESULT_REFERENCE,
        "request_reference": request.request_reference,
        "request_identity": request.identity,
        "result_state": ShadowPhase11PricingRevalidationResultStateV1.RESULT_ABSENT_NOT_EXECUTED,
        "result_present": False,
        "result_reference": None,
        "result_identity": None,
        "pricing_revalidation_started": False,
        "pricing_revalidation_completed": False,
        "fresh_source_observations_present": False,
        "source_observation_timestamp_present": False,
        "provider_model_identifiers_revalidated": False,
        "context_and_output_limits_revalidated": False,
        "pricing_values_revalidated": False,
        "worst_case_route_cost_revalidated": False,
        "conservative_candidate_capacity_revalidated": False,
        "all_checks_passed": False,
        "reason_codes": RESULT_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11PricingRevalidationResultBoundaryV1(**fields)


def _evidence(**overrides: object) -> ShadowPhase11PricingRevalidationBoundaryEvidenceV1:
    policy = get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reconciliation = get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    request = _request()
    result = _result()
    fields = {
        "schema_version": "phase11-shadow-pilot-pricing-revalidation-boundary-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "pricing_freshness_policy_reference": policy.evidence_reference,
        "pricing_freshness_policy_identity": policy.identity,
        "pricing_evidence_reference": pricing.evidence_reference,
        "pricing_evidence_identity": pricing.identity,
        "blocked_readiness_reconciliation_reference": reconciliation.evidence_reference,
        "blocked_readiness_reconciliation_identity": reconciliation.identity,
        "credential_safe_gate_reference": gate.evidence_reference,
        "credential_safe_gate_identity": gate.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "boundary_state": ShadowPhase11PricingRevalidationBoundaryStateV1.REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED,
        "request": request,
        "result_boundary": result,
        "pricing_revalidation_request_defined": True,
        "pricing_revalidation_execution_authorized": False,
        "pricing_revalidation_started": False,
        "pricing_revalidation_result_present": False,
        "pricing_revalidation_completed": False,
        "current_time_access_required": False,
        "current_time_access_observed": False,
        "timestamp_bound": False,
        "fresh_provider_pricing_observed": False,
        "credential_configuration_verified": False,
        "provider_pricing_request_created": False,
        "provider_request_created": False,
        "pre_call_reservation_created": False,
        "ledger_entry_created": False,
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
        "reason_codes": EVIDENCE_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11PricingRevalidationBoundaryEvidenceV1(**fields)


def _reject_request(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PricingRevalidationBoundaryValidationError):
        _request(**overrides)


def _reject_result(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PricingRevalidationBoundaryValidationError):
        _result(**overrides)


def _reject_evidence(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PricingRevalidationBoundaryValidationError):
        _evidence(**overrides)


def test_closed_states_and_check_kinds_are_exact():
    assert tuple(ShadowPhase11PricingRevalidationBoundaryStateV1) == (
        ShadowPhase11PricingRevalidationBoundaryStateV1.REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED,
    )
    assert tuple(ShadowPhase11PricingRevalidationResultStateV1) == (
        ShadowPhase11PricingRevalidationResultStateV1.RESULT_ABSENT_NOT_EXECUTED,
    )
    assert tuple(ShadowPhase11PricingRevalidationCheckKindV1) == CHECKS


def test_request_is_metadata_only_and_binds_exact_checks_models_and_bounds():
    request = _request(check_kinds=tuple(reversed(CHECKS)), reason_codes=tuple(reversed(REQUEST_REASONS)))
    assert request.check_kinds == CHECKS
    assert request.reason_codes == REQUEST_REASONS
    assert (request.primary_model_identifier, request.l1_model_identifier, request.l2_model_identifier) == ("deepseek-v4-pro", "claude-sonnet-5", "claude-opus-4-8")
    assert (request.maximum_input_tokens, request.maximum_output_tokens, request.maximum_attempts) == (16000, 2000, 1)
    assert (request.hard_cap_micro_usd, request.reserve_micro_usd, request.maximum_spendable_micro_usd, request.worst_case_routed_item_micro_usd, request.conservative_candidate_capacity) == (Decimal("5000000"), Decimal("500000"), Decimal("4500000"), Decimal("216700"), 20)
    assert request.request_defined is True
    assert not any((request.execution_authorized, request.network_access_authorized, request.credential_access_authorized, request.current_time_access_authorized, request.provider_pricing_request_created))


def test_result_boundary_is_absent_unexecuted_and_has_no_observation_or_completion():
    result = _result(reason_codes=tuple(reversed(RESULT_REASONS)))
    assert result.result_state is ShadowPhase11PricingRevalidationResultStateV1.RESULT_ABSENT_NOT_EXECUTED
    assert result.reason_codes == RESULT_REASONS
    assert result.result_reference is None and result.result_identity is None
    assert not any((result.result_present, result.pricing_revalidation_started, result.pricing_revalidation_completed, result.fresh_source_observations_present, result.source_observation_timestamp_present, result.provider_model_identifiers_revalidated, result.context_and_output_limits_revalidated, result.pricing_values_revalidated, result.worst_case_route_cost_revalidated, result.conservative_candidate_capacity_revalidated, result.all_checks_passed))


def test_evidence_links_exact_upstreams_and_preserves_zero_authority():
    evidence = _evidence(reason_codes=tuple(reversed(EVIDENCE_REASONS)))
    assert evidence.locked_repository_baseline == BASELINE
    assert evidence.reason_codes == EVIDENCE_REASONS
    assert evidence.request.identity == _request().identity
    assert evidence.result_boundary.identity == _result().identity
    assert evidence.pricing_revalidation_request_defined is True
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE" and evidence.zero_production_effect_proof == "PROVEN_NONE"
    assert not any(getattr(evidence, name) for name in (
        "pricing_revalidation_execution_authorized", "pricing_revalidation_started", "pricing_revalidation_result_present", "pricing_revalidation_completed", "current_time_access_required", "current_time_access_observed", "timestamp_bound", "fresh_provider_pricing_observed", "credential_configuration_verified", "provider_pricing_request_created", "provider_request_created", "pre_call_reservation_created", "ledger_entry_created", "runtime_invocation_authorized", "provider_call_authorized", "provider_transmission_authorized", "run_size_authorized", "manifest_activation_authorized", "launch_authorized", "production_authorized",
    ))


def test_constructors_reject_tampering_unknown_fields_and_all_execution_or_result_claims():
    for name, value in (("check_kinds", CHECKS[:-1]), ("check_kinds", CHECKS + (CHECKS[0],)), ("check_kinds", ("UNKNOWN",)), ("primary_model_identifier", "other"), ("maximum_input_tokens", 1), ("maximum_output_tokens", 1), ("maximum_attempts", 2), ("hard_cap_micro_usd", Decimal("1")), ("request_defined", False), ("execution_authorized", True), ("network_access_authorized", True), ("credential_access_authorized", True), ("current_time_access_authorized", True), ("provider_pricing_request_created", True), ("reason_codes", REQUEST_REASONS[:-1]), ("reason_codes", REQUEST_REASONS + ("UNKNOWN",)), ("request_id", "0" * 64)):
        _reject_request(**{name: value})
    _reject_request(unknown_field="reject")
    for name, value in (("result_state", "COMPLETED"), ("result_present", True), ("result_reference", "RESULT"), ("result_identity", "0" * 64), ("pricing_revalidation_started", True), ("pricing_revalidation_completed", True), ("fresh_source_observations_present", True), ("source_observation_timestamp_present", True), ("provider_model_identifiers_revalidated", True), ("context_and_output_limits_revalidated", True), ("pricing_values_revalidated", True), ("worst_case_route_cost_revalidated", True), ("conservative_candidate_capacity_revalidated", True), ("all_checks_passed", True), ("reason_codes", RESULT_REASONS[:-1]), ("result_boundary_id", "0" * 64)):
        _reject_result(**{name: value})
    _reject_result(unknown_field="reject")
    for name, value in (("locked_repository_baseline", "0" * 40), ("pricing_freshness_policy_identity", "0" * 64), ("boundary_state", "AUTHORIZED"), ("pricing_revalidation_request_defined", False), ("pricing_revalidation_execution_authorized", True), ("pricing_revalidation_started", True), ("pricing_revalidation_result_present", True), ("pricing_revalidation_completed", True), ("current_time_access_required", True), ("current_time_access_observed", True), ("timestamp_bound", True), ("fresh_provider_pricing_observed", True), ("credential_configuration_verified", True), ("provider_pricing_request_created", True), ("provider_request_created", True), ("pre_call_reservation_created", True), ("ledger_entry_created", True), ("runtime_invocation_authorized", True), ("provider_call_authorized", True), ("provider_transmission_authorized", True), ("run_size_authorized", True), ("manifest_activation_authorized", True), ("launch_authorized", True), ("production_authorized", True), ("launch_readiness", "READY"), ("production_effect", "SENT"), ("reason_codes", EVIDENCE_REASONS[:-1]), ("evidence_id", "0" * 64)):
        _reject_evidence(**{name: value})
    _reject_evidence(unknown_field="reject")


def test_canonical_identity_converges_diverges_and_future_module_has_no_operational_surface():
    first = _evidence(reason_codes=tuple(reversed(EVIDENCE_REASONS)))
    second = _evidence(reason_codes=EVIDENCE_REASONS)
    payload = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "evidence_id"}
    variant = dict(payload)
    variant["pricing_revalidation_execution_authorized"] = True
    assert first.identity == second.identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    evidence = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    assert evidence.identity == get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1().identity == _evidence().identity
    module = ast.parse(Path(FUTURE_PATH).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "zoneinfo", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "keyring", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "material_for_adapter", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names


def test_public_accessor_type_is_exact():
    assert type(get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()) is ShadowPhase11PricingRevalidationBoundaryEvidenceV1
