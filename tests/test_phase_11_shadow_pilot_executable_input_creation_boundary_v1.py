"""RED contract for immutable Phase 11 executable-input creation boundary."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_credential_configuration_verification_boundary_v1 import (
    get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1,
)
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import (
    get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1,
)
from engine.phase_11_shadow_pilot_input_run_manifest_readiness_v1 import (
    get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotProviderRoleV1,
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    ShadowPhase11PilotRouteV1,
)
from engine.phase_11_shadow_pilot_pricing_revalidation_boundary_v1 import (
    get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1,
)
from engine.phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_v1 import (
    get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1,
)
from engine.phase_11_shadow_pilot_executable_input_creation_boundary_v1 import (
    ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1,
    ShadowPhase11ExecutableInputCreationBoundaryStateV1,
    ShadowPhase11ExecutableInputCreationBoundaryValidationError,
    ShadowPhase11ExecutableInputCreationCheckKindV1,
    ShadowPhase11ExecutableInputCreationRequestV1,
    ShadowPhase11ExecutableInputCreationResultBoundaryV1,
    ShadowPhase11ExecutableInputCreationResultStateV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1,
    sha256_hex,
)


BASELINE = "43ec5abb8112ff95c9b7e1109cc698a81a386ee3"
PHASE09 = "a84375fa85c2f318944adfe57aaabac6e43c219c"
REQUEST_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_REQUEST_001"
RESULT_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_RESULT_BOUNDARY_001"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001"
ROLES = (
    ShadowPhase11PilotProviderRoleV1.PRIMARY,
    ShadowPhase11PilotProviderRoleV1.L1,
    ShadowPhase11PilotProviderRoleV1.L2,
)
CHECKS = (
    ShadowPhase11ExecutableInputCreationCheckKindV1.CANDIDATE_COUNT_AND_ORDINAL_CONTINUITY,
    ShadowPhase11ExecutableInputCreationCheckKindV1.ROUTE_AND_PROVIDER_ROLE_BINDINGS,
    ShadowPhase11ExecutableInputCreationCheckKindV1.TOKEN_ATTEMPT_AND_COST_BOUNDS,
    ShadowPhase11ExecutableInputCreationCheckKindV1.EXECUTABLE_CONTENT_SCHEMA,
    ShadowPhase11ExecutableInputCreationCheckKindV1.MANIFEST_CONTENT_LINKAGE,
)
REQUEST_REASONS = tuple(sorted((
    "EXECUTABLE_INPUT_CREATION_DESCRIPTOR_DEFINED",
    "EXACT_CREATION_CHECKS_DEFINED",
    "SOURCE_CONTENT_ACCESS_NOT_AUTHORIZED",
    "NO_FILESYSTEM_WRITE_AUTHORITY",
    "NO_CONTENT_SERIALIZATION_AUTHORITY",
    "NO_MANIFEST_ACTIVATION_AUTHORITY",
    "NO_PROVIDER_OR_RUNTIME_REQUEST_AUTHORITY",
)))
RESULT_REASONS = tuple(sorted((
    "RESULT_ABSENT_NOT_EXECUTED",
    "CREATION_NOT_STARTED",
    "CREATION_NOT_COMPLETED",
    "EXECUTABLE_CONTENT_NOT_GENERATED",
    "EXECUTABLE_CONTENT_NOT_PRESENT",
    "NO_CONTENT_INTEGRITY_VERIFICATION",
    "NO_CHECK_PASSED",
)))
EVIDENCE_REASONS = tuple(sorted((
    "EXECUTABLE_INPUT_CREATION_REQUEST_DEFINED",
    "EXECUTABLE_INPUT_CREATION_EXECUTION_NOT_AUTHORIZED",
    "EXECUTABLE_INPUT_CREATION_RESULT_ABSENT",
    "EXECUTABLE_INPUT_CONTENT_ABSENT",
    "PROPOSED_MANIFEST_NOT_ACTIVATED",
    "NO_PROVIDER_OR_RUNTIME_REQUEST_AUTHORITY",
    "NO_OPERATIONAL_AUTHORITY",
)))
FUTURE_PATH = "engine/phase_11_shadow_pilot_executable_input_creation_boundary_v1.py"


def _request(**overrides: object) -> ShadowPhase11ExecutableInputCreationRequestV1:
    successor = get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1()
    readiness = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    manifest = readiness.proposed_manifest
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    credential = get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-executable-input-creation-request-v1",
        "request_id": None,
        "request_reference": REQUEST_REFERENCE,
        "successor_reconciliation_reference": successor.evidence_reference,
        "successor_reconciliation_identity": successor.identity,
        "input_manifest_readiness_reference": readiness.evidence_reference,
        "input_manifest_readiness_identity": readiness.identity,
        "candidate_input_set_identity": manifest.candidate_input_set_identity,
        "proposed_manifest_reference": manifest.manifest_reference,
        "proposed_manifest_identity": manifest.identity,
        "pricing_revalidation_boundary_reference": pricing.evidence_reference,
        "pricing_revalidation_boundary_identity": pricing.identity,
        "credential_verification_boundary_reference": credential.evidence_reference,
        "credential_verification_boundary_identity": credential.identity,
        "current_runtime_integrity_reference": runtime.evidence_reference,
        "current_runtime_integrity_identity": runtime.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "check_kinds": CHECKS,
        "expected_candidate_count": 20,
        "expected_first_ordinal": 1,
        "expected_last_ordinal": 20,
        "expected_route": ShadowPhase11PilotRouteV1.L1_TO_L2,
        "expected_provider_roles": ROLES,
        "maximum_input_tokens": 16000,
        "maximum_output_tokens": 2000,
        "maximum_attempts": 1,
        "maximum_routed_item_cost_micro_usd": Decimal("216700"),
        "maximum_total_cost_micro_usd": Decimal("4334000"),
        "creation_descriptor_defined": True,
        "creation_execution_authorized": False,
        "source_content_access_authorized": False,
        "filesystem_write_authorized": False,
        "executable_content_serialization_authorized": False,
        "manifest_content_mutation_authorized": False,
        "manifest_activation_authorized": False,
        "provider_request_creation_authorized": False,
        "runtime_input_submission_authorized": False,
        "raw_executable_content_present": False,
        "reason_codes": REQUEST_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11ExecutableInputCreationRequestV1(**fields)


def _result(**overrides: object) -> ShadowPhase11ExecutableInputCreationResultBoundaryV1:
    request = _request()
    fields = {
        "schema_version": "phase11-shadow-pilot-executable-input-creation-result-boundary-v1",
        "result_boundary_id": None,
        "result_boundary_reference": RESULT_REFERENCE,
        "request_reference": request.request_reference,
        "request_identity": request.identity,
        "result_state": ShadowPhase11ExecutableInputCreationResultStateV1.RESULT_ABSENT_NOT_EXECUTED,
        "result_present": False,
        "result_reference": None,
        "result_identity": None,
        "creation_started": False,
        "creation_completed": False,
        "executable_content_generated": False,
        "executable_content_serialized": False,
        "executable_content_present": False,
        "candidate_count_verified": False,
        "ordinal_continuity_verified": False,
        "route_role_bindings_verified": False,
        "token_attempt_cost_bounds_verified": False,
        "executable_content_schema_verified": False,
        "manifest_content_linkage_verified": False,
        "content_integrity_verified": False,
        "all_checks_passed": False,
        "reason_codes": RESULT_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11ExecutableInputCreationResultBoundaryV1(**fields)


def _evidence(**overrides: object) -> ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1:
    successor = get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1()
    readiness = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    manifest = readiness.proposed_manifest
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    credential = get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-executable-input-creation-boundary-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "successor_reconciliation_reference": successor.evidence_reference,
        "successor_reconciliation_identity": successor.identity,
        "input_manifest_readiness_reference": readiness.evidence_reference,
        "input_manifest_readiness_identity": readiness.identity,
        "candidate_input_set_identity": manifest.candidate_input_set_identity,
        "proposed_manifest_reference": manifest.manifest_reference,
        "proposed_manifest_identity": manifest.identity,
        "pricing_revalidation_boundary_reference": pricing.evidence_reference,
        "pricing_revalidation_boundary_identity": pricing.identity,
        "credential_verification_boundary_reference": credential.evidence_reference,
        "credential_verification_boundary_identity": credential.identity,
        "current_runtime_integrity_reference": runtime.evidence_reference,
        "current_runtime_integrity_identity": runtime.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "boundary_state": ShadowPhase11ExecutableInputCreationBoundaryStateV1.REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED,
        "request": _request(),
        "result_boundary": _result(),
        "creation_descriptor_defined": True,
        "creation_execution_authorized": False,
        "creation_started": False,
        "creation_result_present": False,
        "creation_completed": False,
        "source_content_access_authorized": False,
        "source_content_access_observed": False,
        "filesystem_write_authorized": False,
        "filesystem_write_observed": False,
        "executable_content_generation_authorized": False,
        "executable_content_generated": False,
        "executable_content_serialized": False,
        "executable_input_content_present": False,
        "content_integrity_verified": False,
        "manifest_content_mutation_authorized": False,
        "proposed_manifest_modified": False,
        "manifest_activation_authorized": False,
        "proposed_manifest_activated": False,
        "pricing_revalidation_execution_authorized": False,
        "credential_verification_execution_authorized": False,
        "provider_request_created": False,
        "pre_call_reservation_created": False,
        "ledger_entry_created": False,
        "runtime_invocation_authorized": False,
        "provider_call_authorized": False,
        "provider_transmission_authorized": False,
        "run_size_authorized": False,
        "launch_authorized": False,
        "production_authorized": False,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "reason_codes": EVIDENCE_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1(**fields)


def _reject(factory: object, **overrides: object) -> None:
    with pytest.raises(ShadowPhase11ExecutableInputCreationBoundaryValidationError):
        factory(**overrides)


def test_closed_states_and_check_kinds_are_exact_and_contracts_are_closed():
    assert tuple(ShadowPhase11ExecutableInputCreationBoundaryStateV1) == (
        ShadowPhase11ExecutableInputCreationBoundaryStateV1.REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED,
    )
    assert tuple(ShadowPhase11ExecutableInputCreationResultStateV1) == (
        ShadowPhase11ExecutableInputCreationResultStateV1.RESULT_ABSENT_NOT_EXECUTED,
    )
    assert tuple(ShadowPhase11ExecutableInputCreationCheckKindV1) == CHECKS
    for contract in (
        ShadowPhase11ExecutableInputCreationRequestV1,
        ShadowPhase11ExecutableInputCreationResultBoundaryV1,
        ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1,
    ):
        assert getattr(contract, "__slots__") and "__dict__" not in contract.__slots__


def test_request_is_content_free_and_binds_exact_lineage_shape_roles_and_bounds():
    request = _request(
        check_kinds=tuple(reversed(CHECKS)),
        expected_provider_roles=tuple(reversed(ROLES)),
        reason_codes=tuple(reversed(REQUEST_REASONS)),
    )
    assert request.check_kinds == CHECKS and request.expected_provider_roles == ROLES
    assert request.reason_codes == REQUEST_REASONS
    assert (
        request.expected_candidate_count,
        request.expected_first_ordinal,
        request.expected_last_ordinal,
        request.expected_route,
    ) == (20, 1, 20, ShadowPhase11PilotRouteV1.L1_TO_L2)
    assert (
        request.maximum_input_tokens,
        request.maximum_output_tokens,
        request.maximum_attempts,
        request.maximum_routed_item_cost_micro_usd,
        request.maximum_total_cost_micro_usd,
    ) == (16000, 2000, 1, Decimal("216700"), Decimal("4334000"))
    assert request.creation_descriptor_defined is True
    assert not any(getattr(request, name) for name in (
        "creation_execution_authorized", "source_content_access_authorized",
        "filesystem_write_authorized", "executable_content_serialization_authorized",
        "manifest_content_mutation_authorized", "manifest_activation_authorized",
        "provider_request_creation_authorized", "runtime_input_submission_authorized",
        "raw_executable_content_present",
    ))


def test_result_boundary_is_absent_unexecuted_and_contains_no_content_or_acceptance_claim():
    result = _result(reason_codes=tuple(reversed(RESULT_REASONS)))
    assert result.result_state is ShadowPhase11ExecutableInputCreationResultStateV1.RESULT_ABSENT_NOT_EXECUTED
    assert result.result_reference is None and result.result_identity is None
    assert result.reason_codes == RESULT_REASONS
    assert not any(getattr(result, name) for name in (
        "result_present", "creation_started", "creation_completed",
        "executable_content_generated", "executable_content_serialized",
        "executable_content_present", "candidate_count_verified",
        "ordinal_continuity_verified", "route_role_bindings_verified",
        "token_attempt_cost_bounds_verified", "executable_content_schema_verified",
        "manifest_content_linkage_verified", "content_integrity_verified",
        "all_checks_passed",
    ))


def test_evidence_links_exact_upstreams_and_preserves_absent_content_inactive_manifest_and_zero_authority():
    evidence = _evidence(reason_codes=tuple(reversed(EVIDENCE_REASONS)))
    assert evidence.locked_repository_baseline == BASELINE
    assert evidence.request.identity == _request().identity
    assert evidence.result_boundary.identity == _result().identity
    assert evidence.creation_descriptor_defined is True
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE" and evidence.zero_production_proof == "PROVEN_NONE"
    assert not any(getattr(evidence, name) for name in (
        "creation_execution_authorized", "creation_started", "creation_result_present",
        "creation_completed", "source_content_access_authorized",
        "source_content_access_observed", "filesystem_write_authorized",
        "filesystem_write_observed", "executable_content_generation_authorized",
        "executable_content_generated", "executable_content_serialized",
        "executable_input_content_present", "content_integrity_verified",
        "manifest_content_mutation_authorized", "proposed_manifest_modified",
        "manifest_activation_authorized", "proposed_manifest_activated",
        "pricing_revalidation_execution_authorized",
        "credential_verification_execution_authorized", "provider_request_created",
        "pre_call_reservation_created", "ledger_entry_created",
        "runtime_invocation_authorized", "provider_call_authorized",
        "provider_transmission_authorized", "run_size_authorized",
        "launch_authorized", "production_authorized",
    ))


def test_constructors_reject_tampering_unknown_fields_and_every_content_execution_or_authority_claim():
    for name, value in (
        ("successor_reconciliation_identity", "0" * 64),
        ("input_manifest_readiness_identity", "0" * 64),
        ("candidate_input_set_identity", "0" * 64),
        ("proposed_manifest_identity", "0" * 64),
        ("pricing_revalidation_boundary_identity", "0" * 64),
        ("credential_verification_boundary_identity", "0" * 64),
        ("current_runtime_integrity_identity", "0" * 64),
        ("reservation_bound_identity", "0" * 64),
        ("check_kinds", CHECKS[:-1]), ("check_kinds", CHECKS + (CHECKS[0],)),
        ("check_kinds", ("UNKNOWN",)), ("expected_candidate_count", 19),
        ("expected_first_ordinal", 0), ("expected_last_ordinal", 21),
        ("expected_route", "OTHER"), ("expected_provider_roles", ROLES[:-1]),
        ("maximum_input_tokens", 1), ("maximum_output_tokens", 1),
        ("maximum_attempts", 2), ("maximum_routed_item_cost_micro_usd", Decimal("1")),
        ("maximum_total_cost_micro_usd", Decimal("1")),
        ("creation_descriptor_defined", False),
        ("reason_codes", REQUEST_REASONS[:-1]),
        ("reason_codes", REQUEST_REASONS + ("UNKNOWN",)),
        ("request_id", "0" * 64),
    ):
        _reject(_request, **{name: value})
    for name in (
        "creation_execution_authorized", "source_content_access_authorized",
        "filesystem_write_authorized", "executable_content_serialization_authorized",
        "manifest_content_mutation_authorized", "manifest_activation_authorized",
        "provider_request_creation_authorized", "runtime_input_submission_authorized",
        "raw_executable_content_present",
    ):
        _reject(_request, **{name: True})
    _reject(_request, unknown_field="reject")
    for name, value in (
        ("result_state", "COMPLETED"), ("result_present", True),
        ("result_reference", "RESULT"), ("result_identity", "0" * 64),
        ("reason_codes", RESULT_REASONS[:-1]),
        ("reason_codes", RESULT_REASONS + ("UNKNOWN",)),
        ("result_boundary_id", "0" * 64),
    ):
        _reject(_result, **{name: value})
    for name in (
        "creation_started", "creation_completed", "executable_content_generated",
        "executable_content_serialized", "executable_content_present",
        "candidate_count_verified", "ordinal_continuity_verified",
        "route_role_bindings_verified", "token_attempt_cost_bounds_verified",
        "executable_content_schema_verified", "manifest_content_linkage_verified",
        "content_integrity_verified", "all_checks_passed",
    ):
        _reject(_result, **{name: True})
    _reject(_result, unknown_field="reject")
    for name, value in (
        ("locked_repository_baseline", "0" * 40), ("locked_phase09_baseline", "0" * 40),
        ("boundary_state", "AUTHORIZED"), ("successor_reconciliation_identity", "0" * 64),
        ("input_manifest_readiness_identity", "0" * 64), ("candidate_input_set_identity", "0" * 64),
        ("proposed_manifest_identity", "0" * 64), ("pricing_revalidation_boundary_identity", "0" * 64),
        ("credential_verification_boundary_identity", "0" * 64), ("current_runtime_integrity_identity", "0" * 64),
        ("reservation_bound_identity", "0" * 64), ("creation_descriptor_defined", False),
        ("launch_readiness", "READY"), ("production_effect", "SENT"),
        ("zero_production_proof", "NOT_PROVEN"), ("reason_codes", EVIDENCE_REASONS[:-1]),
        ("reason_codes", EVIDENCE_REASONS + ("UNKNOWN",)), ("evidence_id", "0" * 64),
    ):
        _reject(_evidence, **{name: value})
    for name in (
        "creation_execution_authorized", "creation_started", "creation_result_present",
        "creation_completed", "source_content_access_authorized",
        "source_content_access_observed", "filesystem_write_authorized",
        "filesystem_write_observed", "executable_content_generation_authorized",
        "executable_content_generated", "executable_content_serialized",
        "executable_input_content_present", "content_integrity_verified",
        "manifest_content_mutation_authorized", "proposed_manifest_modified",
        "manifest_activation_authorized", "proposed_manifest_activated",
        "pricing_revalidation_execution_authorized",
        "credential_verification_execution_authorized", "provider_request_created",
        "pre_call_reservation_created", "ledger_entry_created",
        "runtime_invocation_authorized", "provider_call_authorized",
        "provider_transmission_authorized", "run_size_authorized",
        "launch_authorized", "production_authorized",
    ):
        _reject(_evidence, **{name: True})
    _reject(_evidence, unknown_field="reject")


def test_canonical_identity_converges_diverges_and_future_module_has_no_content_or_operational_surface():
    first = _evidence(reason_codes=tuple(reversed(EVIDENCE_REASONS)))
    second = _evidence()
    payload = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "evidence_id"}
    variant = dict(payload)
    variant["executable_input_content_present"] = True
    assert first.identity == second.identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\xc3\xa9"}'
    module = ast.parse(Path(FUTURE_PATH).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "read_text", "write_text", "read_bytes", "write_bytes", "serialize", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    content_fragments = {"prompt", "article", "market_payload", "provider_message", "authorization", "bearer", "api_key", "password", ".env"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    strings = {node.value.lower() for node in ast.walk(module) if isinstance(node, ast.Constant) and type(node.value) is str}
    assert not imported & forbidden_modules and not names & forbidden_names
    assert not any(fragment in value for fragment in content_fragments for value in strings)


def test_public_accessor_type_and_identity_are_exact_and_stable():
    first = get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1()
    second = get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1()
    assert type(first) is ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1
    assert first.identity == second.identity == _evidence().identity
