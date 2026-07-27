"""RED contract for immutable executable-input integrity acceptance boundaries."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_executable_input_content_integrity_acceptance_boundary_v1 import (
    ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryEvidenceV1,
    ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError,
    ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1,
    ShadowPhase11ExecutableInputContentIntegrityBoundaryStateV1,
    ShadowPhase11ExecutableInputContentIntegrityCheckKindV1,
    ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1,
    ShadowPhase11ExecutableInputContentIntegrityResultStateV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_executable_input_content_integrity_acceptance_boundary_evidence_v1,
    sha256_hex,
)
from engine.phase_11_shadow_pilot_credential_configuration_verification_boundary_v1 import get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1
from engine.phase_11_shadow_pilot_executable_input_content_readiness_decision_v1 import get_phase_11_shadow_pilot_executable_input_content_readiness_decision_evidence_v1
from engine.phase_11_shadow_pilot_executable_input_creation_boundary_v1 import get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1
from engine.phase_11_shadow_pilot_input_run_manifest_readiness_v1 import get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import ShadowPhase11PilotLaunchReadinessV1, ShadowPhase11PilotProviderRoleV1
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import get_phase_11_shadow_pilot_pre_call_reservation_bound_v1
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import ShadowPhase11PilotRouteV1
from engine.phase_11_shadow_pilot_pricing_revalidation_boundary_v1 import get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1
from engine.phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_v1 import get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1


BASELINE = "408f1c66c0092e48d4aa02e8ef6459c174f7c52f"
PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
REQUEST_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_ACCEPTANCE_REQUEST_001"
RESULT_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_RESULT_BOUNDARY_001"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_001"
CHECKS = (
    ShadowPhase11ExecutableInputContentIntegrityCheckKindV1.CANDIDATE_COUNT_AND_ORDINAL_MATCH,
    ShadowPhase11ExecutableInputContentIntegrityCheckKindV1.ROUTE_ROLE_AND_BOUND_MATCH,
    ShadowPhase11ExecutableInputContentIntegrityCheckKindV1.CONTENT_SCHEMA_CONFORMANCE,
    ShadowPhase11ExecutableInputContentIntegrityCheckKindV1.CONTENT_TO_CANDIDATE_LINKAGE,
    ShadowPhase11ExecutableInputContentIntegrityCheckKindV1.CONTENT_TO_MANIFEST_LINKAGE,
    ShadowPhase11ExecutableInputContentIntegrityCheckKindV1.CONTENT_IMMUTABILITY_IDENTITY,
    ShadowPhase11ExecutableInputContentIntegrityCheckKindV1.PROHIBITED_SECRET_AND_AUTHORITY_ABSENCE,
)
ROLES = (
    ShadowPhase11PilotProviderRoleV1.PRIMARY,
    ShadowPhase11PilotProviderRoleV1.L1,
    ShadowPhase11PilotProviderRoleV1.L2,
)
BLOCKERS = tuple(sorted((
    "EXECUTABLE_INPUT_CONTENT_ABSENT",
    "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
    "INTEGRITY_RESULT_ABSENT",
    "CONTENT_INTEGRITY_NOT_VERIFIED",
    "CONTENT_NOT_ACCEPTED",
    "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
)))
REASONS = tuple(sorted((
    "CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_DEFINED",
    "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
    "INTEGRITY_RESULT_ABSENT",
    "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
    "CONTENT_INTEGRITY_NOT_VERIFIED",
    "CONTENT_NOT_ACCEPTED",
    "PROPOSED_MANIFEST_REMAINS_INACTIVE",
    "NO_OPERATIONAL_AUTHORITY",
)))


def _request(**overrides: object) -> ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1:
    readiness = get_phase_11_shadow_pilot_executable_input_content_readiness_decision_evidence_v1()
    successor = get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1()
    creation = get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1()
    manifest_readiness = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    manifest = manifest_readiness.proposed_manifest
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    credential = get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-executable-input-content-integrity-acceptance-request-v1",
        "request_id": None,
        "request_reference": REQUEST_REFERENCE,
        "content_readiness_decision_reference": readiness.evidence_reference,
        "content_readiness_decision_identity": readiness.identity,
        "current_successor_reconciliation_reference": successor.evidence_reference,
        "current_successor_reconciliation_identity": successor.identity,
        "executable_input_creation_boundary_reference": creation.evidence_reference,
        "executable_input_creation_boundary_identity": creation.identity,
        "input_run_manifest_readiness_reference": manifest_readiness.evidence_reference,
        "input_run_manifest_readiness_identity": manifest_readiness.identity,
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
        "maximum_routed_item_cost_micro_usd": 216700,
        "maximum_total_cost_micro_usd": 4334000,
        "acceptance_boundary_defined": True,
        "integrity_inspection_authorized": False,
        "content_access_authorized": False,
        "filesystem_read_authorized": False,
        "content_hashing_authorized": False,
        "content_serialization_authorized": False,
        "integrity_verification_authorized": False,
        "result_acceptance_authorized": False,
        "manifest_mutation_authorized": False,
        "manifest_activation_authorized": False,
        "provider_request_creation_authorized": False,
        "runtime_input_submission_authorized": False,
        "executable_content_present": False,
        "executable_content_identity_present": False,
    }
    fields.update(overrides)
    return ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1(**fields)


def _result(**overrides: object) -> ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1:
    request = _request()
    fields = {
        "schema_version": "phase11-shadow-pilot-executable-input-content-integrity-result-boundary-v1",
        "result_boundary_id": None,
        "result_boundary_reference": RESULT_REFERENCE,
        "request_reference": request.request_reference,
        "request_identity": request.identity,
        "result_state": ShadowPhase11ExecutableInputContentIntegrityResultStateV1.RESULT_ABSENT_NOT_INSPECTED,
        "result_present": False,
        "result_reference": None,
        "result_identity": None,
        "integrity_inspection_started": False,
        "integrity_inspection_completed": False,
        "executable_content_observed": False,
        "executable_content_identity_observed": False,
        "candidate_count_match_verified": False,
        "ordinal_match_verified": False,
        "route_role_bound_match_verified": False,
        "content_schema_verified": False,
        "content_candidate_linkage_verified": False,
        "content_manifest_linkage_verified": False,
        "content_immutability_identity_verified": False,
        "prohibited_secret_and_authority_absence_verified": False,
        "content_integrity_verified": False,
        "content_accepted": False,
        "all_checks_passed": False,
    }
    fields.update(overrides)
    return ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1(**fields)


def _evidence(**overrides: object) -> ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryEvidenceV1:
    request = _request()
    result = _result()
    fields = {
        "schema_version": "phase11-shadow-pilot-executable-input-content-integrity-acceptance-boundary-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "boundary_state": ShadowPhase11ExecutableInputContentIntegrityBoundaryStateV1.ACCEPTANCE_BOUNDARY_DEFINED_RESULT_ABSENT_INSPECTION_NOT_AUTHORIZED,
        "request": request,
        "result_boundary": result,
        "content_readiness_decision_reference": request.content_readiness_decision_reference,
        "content_readiness_decision_identity": request.content_readiness_decision_identity,
        "current_successor_reconciliation_reference": request.current_successor_reconciliation_reference,
        "current_successor_reconciliation_identity": request.current_successor_reconciliation_identity,
        "executable_input_creation_boundary_reference": request.executable_input_creation_boundary_reference,
        "executable_input_creation_boundary_identity": request.executable_input_creation_boundary_identity,
        "input_run_manifest_readiness_reference": request.input_run_manifest_readiness_reference,
        "input_run_manifest_readiness_identity": request.input_run_manifest_readiness_identity,
        "candidate_input_set_identity": request.candidate_input_set_identity,
        "proposed_manifest_reference": request.proposed_manifest_reference,
        "proposed_manifest_identity": request.proposed_manifest_identity,
        "pricing_revalidation_boundary_reference": request.pricing_revalidation_boundary_reference,
        "pricing_revalidation_boundary_identity": request.pricing_revalidation_boundary_identity,
        "credential_verification_boundary_reference": request.credential_verification_boundary_reference,
        "credential_verification_boundary_identity": request.credential_verification_boundary_identity,
        "current_runtime_integrity_reference": request.current_runtime_integrity_reference,
        "current_runtime_integrity_identity": request.current_runtime_integrity_identity,
        "reservation_bound_reference": request.reservation_bound_reference,
        "reservation_bound_identity": request.reservation_bound_identity,
        "acceptance_boundary_defined": True,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": BLOCKERS,
        "reason_codes": REASONS,
    }
    for name in (
        "integrity_inspection_authorized", "integrity_inspection_started", "integrity_result_present", "integrity_inspection_completed", "content_access_authorized", "content_access_observed", "filesystem_read_authorized", "filesystem_read_observed", "content_hashing_authorized", "content_hashing_observed", "executable_content_observed", "executable_content_identity_present", "content_integrity_verified", "content_accepted", "content_creation_execution_authorized", "executable_input_content_present", "manifest_mutation_authorized", "proposed_manifest_modified", "manifest_activation_authorized", "proposed_manifest_activated", "pricing_revalidation_execution_authorized", "credential_verification_execution_authorized", "provider_request_created", "pre_call_reservation_created", "ledger_entry_created", "runtime_invocation_authorized", "provider_call_authorized", "provider_transmission_authorized", "run_size_authorized", "launch_authorized", "production_authorized",
    ):
        fields[name] = False
    fields.update(overrides)
    return ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryEvidenceV1(**fields)


def _reject(factory, **overrides: object) -> None:
    with pytest.raises(ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError):
        factory(**overrides)


def test_closed_states_checks_and_all_records_are_frozen_slotted_and_closed():
    assert tuple(ShadowPhase11ExecutableInputContentIntegrityBoundaryStateV1) == (ShadowPhase11ExecutableInputContentIntegrityBoundaryStateV1.ACCEPTANCE_BOUNDARY_DEFINED_RESULT_ABSENT_INSPECTION_NOT_AUTHORIZED,)
    assert tuple(ShadowPhase11ExecutableInputContentIntegrityResultStateV1) == (ShadowPhase11ExecutableInputContentIntegrityResultStateV1.RESULT_ABSENT_NOT_INSPECTED,)
    assert tuple(ShadowPhase11ExecutableInputContentIntegrityCheckKindV1) == CHECKS
    request, result, evidence = _request(), _result(), _evidence()
    for item in (request, result, evidence):
        assert "__dict__" not in type(item).__slots__
    with pytest.raises(FrozenInstanceError):
        request.schema_version = "invalid"
    with pytest.raises(FrozenInstanceError):
        result.schema_version = "invalid"
    with pytest.raises(FrozenInstanceError):
        evidence.schema_version = "invalid"


def test_content_free_request_has_exact_metadata_bounds_and_no_operational_authority():
    request = _request(check_kinds=tuple(reversed(CHECKS)), expected_provider_roles=tuple(reversed(ROLES)))
    assert request.check_kinds == CHECKS
    assert request.expected_provider_roles == ROLES
    assert (request.expected_candidate_count, request.expected_first_ordinal, request.expected_last_ordinal) == (20, 1, 20)
    assert request.expected_route is ShadowPhase11PilotRouteV1.L1_TO_L2
    assert (request.maximum_input_tokens, request.maximum_output_tokens, request.maximum_attempts, request.maximum_routed_item_cost_micro_usd, request.maximum_total_cost_micro_usd) == (16000, 2000, 1, 216700, 4334000)
    assert request.acceptance_boundary_defined is True
    assert not any(getattr(request, name) for name in ("integrity_inspection_authorized", "content_access_authorized", "filesystem_read_authorized", "content_hashing_authorized", "content_serialization_authorized", "integrity_verification_authorized", "result_acceptance_authorized", "manifest_mutation_authorized", "manifest_activation_authorized", "provider_request_creation_authorized", "runtime_input_submission_authorized", "executable_content_present", "executable_content_identity_present"))


def test_absent_result_and_concrete_evidence_are_exactly_blocked_and_linked():
    result = _result()
    assert result.result_state is ShadowPhase11ExecutableInputContentIntegrityResultStateV1.RESULT_ABSENT_NOT_INSPECTED
    assert result.result_present is False and result.result_reference is None and result.result_identity is None
    assert not any(getattr(result, name) for name in result.__dataclass_fields__ if name not in {"schema_version", "result_boundary_id", "result_boundary_reference", "request_reference", "request_identity", "result_state", "result_present", "result_reference", "result_identity"})
    evidence = _evidence()
    assert evidence.locked_repository_baseline == BASELINE
    assert evidence.content_readiness_decision_identity == "437352460a8410929abd80a5548ff0ee2bf54bc81b6f2af50682efdebca2309b"
    assert evidence.executable_input_creation_boundary_identity == "e6ea7eaf9dd0e79aaba718ef4412c418097236d20b1c435784fb64cfd3efd9a1"
    assert evidence.acceptance_boundary_defined is True
    assert evidence.blocker_codes == BLOCKERS and evidence.reason_codes == REASONS
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH


def test_constructors_reject_check_result_content_access_and_authority_claims():
    for value in (CHECKS[:-1], CHECKS + (CHECKS[0],), CHECKS[:-1] + ("CONTENT_HASH_VERIFIED",)):
        _reject(_request, check_kinds=value)
    for name in ("expected_candidate_count", "expected_first_ordinal", "expected_last_ordinal", "maximum_input_tokens", "maximum_output_tokens", "maximum_attempts", "maximum_routed_item_cost_micro_usd", "maximum_total_cost_micro_usd", "acceptance_boundary_defined"):
        _reject(_request, **{name: False if name == "acceptance_boundary_defined" else 0})
    for name in ("integrity_inspection_authorized", "content_access_authorized", "filesystem_read_authorized", "content_hashing_authorized", "content_serialization_authorized", "integrity_verification_authorized", "result_acceptance_authorized", "manifest_mutation_authorized", "manifest_activation_authorized", "provider_request_creation_authorized", "runtime_input_submission_authorized", "executable_content_present", "executable_content_identity_present"):
        _reject(_request, **{name: True})
    for name in ("result_present", "integrity_inspection_started", "integrity_inspection_completed", "executable_content_observed", "executable_content_identity_observed", "candidate_count_match_verified", "ordinal_match_verified", "route_role_bound_match_verified", "content_schema_verified", "content_candidate_linkage_verified", "content_manifest_linkage_verified", "content_immutability_identity_verified", "prohibited_secret_and_authority_absence_verified", "content_integrity_verified", "content_accepted", "all_checks_passed"):
        _reject(_result, **{name: True})


def test_evidence_rejects_tampering_unknown_fields_and_all_operational_claims():
    for name, value in (("locked_repository_baseline", "0" * 40), ("locked_phase09_baseline", "0" * 40), ("boundary_state", "VERIFIED"), ("content_readiness_decision_identity", "0" * 64), ("proposed_manifest_identity", "0" * 64), ("evidence_id", "0" * 64), ("launch_readiness", "READY"), ("production_effect", "SENT")):
        _reject(_evidence, **{name: value})
    for name in ("integrity_inspection_authorized", "integrity_inspection_started", "integrity_result_present", "integrity_inspection_completed", "content_access_authorized", "content_access_observed", "filesystem_read_authorized", "filesystem_read_observed", "content_hashing_authorized", "content_hashing_observed", "executable_content_observed", "executable_content_identity_present", "content_integrity_verified", "content_accepted", "content_creation_execution_authorized", "executable_input_content_present", "manifest_mutation_authorized", "proposed_manifest_modified", "manifest_activation_authorized", "proposed_manifest_activated", "pricing_revalidation_execution_authorized", "credential_verification_execution_authorized", "provider_request_created", "pre_call_reservation_created", "ledger_entry_created", "runtime_invocation_authorized", "provider_call_authorized", "provider_transmission_authorized", "run_size_authorized", "launch_authorized", "production_authorized"):
        _reject(_evidence, **{name: True})
    _reject(_evidence, unknown_field="reject")


def test_codes_identity_ordering_and_static_surface_are_exact_and_inert():
    first = _evidence(blocker_codes=tuple(reversed(BLOCKERS)), reason_codes=tuple(reversed(REASONS)))
    payload = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "evidence_id"}
    variant = dict(payload)
    variant["content_accepted"] = True
    assert first.identity == _evidence().identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    for value in (BLOCKERS[:-1], BLOCKERS + ("UNKNOWN",), BLOCKERS + (BLOCKERS[0],)):
        _reject(_evidence, blocker_codes=value)
    for value in (REASONS[:-1], REASONS + ("UNKNOWN",), REASONS + (REASONS[0],)):
        _reject(_evidence, reason_codes=value)
    import engine.phase_11_shadow_pilot_executable_input_content_integrity_acceptance_boundary_v1 as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "dotenv", "keyring", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules and not names & forbidden_names


def test_public_accessor_type_and_identity_are_stable():
    first = get_phase_11_shadow_pilot_executable_input_content_integrity_acceptance_boundary_evidence_v1()
    second = get_phase_11_shadow_pilot_executable_input_content_integrity_acceptance_boundary_evidence_v1()
    assert type(first) is ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryEvidenceV1
    assert first.identity == second.identity == _evidence().identity
