"""RED contract for denied Phase 11 integrity-inspection readiness decisions."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_integrity_inspection_readiness_decision_v1 import (
    ShadowPhase11IntegrityInspectionAuthorizationStateV1,
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1,
    ShadowPhase11IntegrityInspectionReadinessDecisionEvidenceV1,
    ShadowPhase11IntegrityInspectionReadinessDecisionValidationError,
    ShadowPhase11IntegrityInspectionReadinessStateV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_integrity_inspection_readiness_decision_evidence_v1,
    sha256_hex,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import ShadowPhase11PilotLaunchReadinessV1


BASELINE = "799d4e1b2ec5f732c69d7b66924d281d27cf6eeb"
PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_INTEGRITY_INSPECTION_READINESS_DECISION_001"
CHECKS = (
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1.ACCEPTANCE_BOUNDARY_DEFINED,
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1.EXECUTABLE_CONTENT_PRESENT,
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1.EXECUTABLE_CONTENT_IDENTITY_PRESENT,
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1.CONTENT_ACCESS_AUTHORITY_GRANTED,
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1.FILESYSTEM_READ_AUTHORITY_GRANTED,
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1.CONTENT_HASHING_AUTHORITY_GRANTED,
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1.INTEGRITY_VERIFICATION_AUTHORITY_GRANTED,
    ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1.RESULT_ACCEPTANCE_AUTHORITY_GRANTED,
)
BLOCKERS = tuple(sorted((
    "EXECUTABLE_INPUT_CONTENT_ABSENT", "EXECUTABLE_CONTENT_IDENTITY_ABSENT",
    "CONTENT_ACCESS_NOT_AUTHORIZED", "FILESYSTEM_READ_NOT_AUTHORIZED",
    "CONTENT_HASHING_NOT_AUTHORIZED", "INTEGRITY_VERIFICATION_NOT_AUTHORIZED",
    "RESULT_ACCEPTANCE_NOT_AUTHORIZED",
)))
REASONS = tuple(sorted((
    "INSPECTION_READINESS_DECISION_DEFINED", "ACCEPTANCE_BOUNDARY_RECOGNIZED",
    "INSPECTION_PREREQUISITE_ASSESSMENT_NOT_PERFORMED",
    "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
    "EXECUTABLE_CONTENT_IDENTITY_REMAINS_ABSENT",
    "INTEGRITY_INSPECTION_NOT_AUTHORIZED", "CONTENT_INTEGRITY_NOT_VERIFIED",
    "CONTENT_NOT_ACCEPTED", "PROPOSED_MANIFEST_REMAINS_INACTIVE",
    "NO_OPERATIONAL_AUTHORITY",
)))
FALSE_FIELDS = (
    "inspection_prerequisite_assessment_execution_authorized", "inspection_prerequisite_assessment_performed", "integrity_inspection_ready", "integrity_inspection_authorized", "integrity_inspection_started", "integrity_inspection_completed", "integrity_result_present", "executable_input_content_present", "executable_content_identity_present", "content_access_authorized", "content_access_observed", "filesystem_read_authorized", "filesystem_read_observed", "content_hashing_authorized", "content_hashing_observed", "integrity_verification_authorized", "content_integrity_verified", "result_acceptance_authorized", "content_accepted", "content_creation_execution_authorized", "manifest_mutation_authorized", "proposed_manifest_modified", "manifest_activation_authorized", "proposed_manifest_activated", "pricing_revalidation_execution_authorized", "credential_verification_execution_authorized", "provider_request_created", "pre_call_reservation_created", "ledger_entry_created", "runtime_invocation_authorized", "provider_call_authorized", "provider_transmission_authorized", "run_size_authorized", "launch_authorized", "production_authorized",
)
LINKS = {
    "content_integrity_acceptance_boundary_reference": "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_001",
    "content_integrity_acceptance_boundary_identity": "fbbd47cce8a7a3208719e9caecf6d06c0ee38612ea109717bb7fe08d0c7003b1",
    "content_readiness_decision_reference": "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_READINESS_DECISION_001",
    "content_readiness_decision_identity": "437352460a8410929abd80a5548ff0ee2bf54bc81b6f2af50682efdebca2309b",
    "current_successor_reconciliation_reference": "PHASE_11_PILOT_SUCCESSOR_EXECUTABLE_INPUT_BOUNDARY_RECONCILIATION_001",
    "current_successor_reconciliation_identity": "b95dca79c2c140cd618d2239e7c1152268e063e9db23a67671782c4a7d66990a",
    "executable_input_creation_boundary_reference": "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001",
    "executable_input_creation_boundary_identity": "e6ea7eaf9dd0e79aaba718ef4412c418097236d20b1c435784fb64cfd3efd9a1",
    "input_run_manifest_readiness_reference": "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001",
    "input_run_manifest_readiness_identity": "30ea2ab4f8c3aef604358f3688cf88b348cad6cc98ec887ce98502acabc4e944",
    "candidate_input_set_identity": "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c",
    "proposed_manifest_reference": "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001",
    "proposed_manifest_identity": "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a",
    "pricing_revalidation_boundary_reference": "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001",
    "pricing_revalidation_boundary_identity": "fc34f6f222825f29669ce4f575314eabeb887135ef54bc3613836f4d46ccb0fc",
    "credential_verification_boundary_reference": "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_BOUNDARY_001",
    "credential_verification_boundary_identity": "91991bb1f7947eb43acca9983c53a686667f1ab58be21bd769224fec174a679c",
    "current_runtime_integrity_reference": "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001",
    "current_runtime_integrity_identity": "45d1446eb173d399f748b3b11e616d51391947762d3b36848cbd4f3d5b3228ab",
    "reservation_bound_reference": "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001",
    "reservation_bound_identity": "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4",
}


def _evidence(**overrides: object) -> ShadowPhase11IntegrityInspectionReadinessDecisionEvidenceV1:
    fields = {
        "schema_version": "phase11-shadow-pilot-integrity-inspection-readiness-decision-v1",
        "evidence_id": None, "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE, "locked_phase09_baseline": PHASE09,
        "readiness_state": ShadowPhase11IntegrityInspectionReadinessStateV1.NOT_READY_FOR_INTEGRITY_INSPECTION,
        "authorization_state": ShadowPhase11IntegrityInspectionAuthorizationStateV1.INTEGRITY_INSPECTION_NOT_AUTHORIZED,
        **LINKS, "prerequisite_checks": CHECKS,
        "inspection_readiness_decision_defined": True,
        "acceptance_boundary_defined": True,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE", "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": BLOCKERS, "reason_codes": REASONS,
    }
    fields.update({name: False for name in FALSE_FIELDS})
    fields.update(overrides)
    return ShadowPhase11IntegrityInspectionReadinessDecisionEvidenceV1(**fields)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11IntegrityInspectionReadinessDecisionValidationError):
        _evidence(**overrides)


def test_closed_states_checks_and_evidence_immutability_are_exact():
    assert tuple(ShadowPhase11IntegrityInspectionReadinessStateV1) == (ShadowPhase11IntegrityInspectionReadinessStateV1.NOT_READY_FOR_INTEGRITY_INSPECTION,)
    assert tuple(ShadowPhase11IntegrityInspectionAuthorizationStateV1) == (ShadowPhase11IntegrityInspectionAuthorizationStateV1.INTEGRITY_INSPECTION_NOT_AUTHORIZED,)
    assert tuple(ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1) == CHECKS
    evidence = _evidence()
    assert "__dict__" not in type(evidence).__slots__
    with pytest.raises(FrozenInstanceError): evidence.schema_version = "invalid"


def test_concrete_denied_decision_links_upstreams_and_preserves_all_absences():
    evidence = _evidence()
    assert evidence.locked_repository_baseline == BASELINE
    assert evidence.content_integrity_acceptance_boundary_identity == LINKS["content_integrity_acceptance_boundary_identity"]
    assert evidence.content_readiness_decision_identity == LINKS["content_readiness_decision_identity"]
    assert evidence.acceptance_boundary_defined is True and evidence.inspection_readiness_decision_defined is True
    assert evidence.prerequisite_checks == CHECKS
    assert not any(getattr(evidence, name) for name in FALSE_FIELDS)
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE" and evidence.zero_production_proof == "PROVEN_NONE"


def test_prerequisite_ordering_converges_and_only_acceptance_boundary_is_satisfied():
    assert _evidence(prerequisite_checks=tuple(reversed(CHECKS))).prerequisite_checks == CHECKS
    for value in (CHECKS[:-1], CHECKS + (CHECKS[0],), CHECKS[:-1] + ("INSPECTED",)):
        _reject(prerequisite_checks=value)
    for name in ("inspection_prerequisite_assessment_performed", "integrity_inspection_ready", "integrity_inspection_authorized", "executable_input_content_present", "executable_content_identity_present", "content_access_authorized", "filesystem_read_authorized", "content_hashing_authorized", "integrity_verification_authorized", "result_acceptance_authorized"):
        _reject(**{name: True})


def test_exact_blockers_reasons_and_tampered_or_operational_values_are_rejected():
    evidence = _evidence(blocker_codes=tuple(reversed(BLOCKERS)), reason_codes=tuple(reversed(REASONS)))
    assert evidence.blocker_codes == BLOCKERS and evidence.reason_codes == REASONS
    for value in (BLOCKERS[:-1], BLOCKERS + ("UNKNOWN",), BLOCKERS + (BLOCKERS[0],)):
        _reject(blocker_codes=value)
    for value in (REASONS[:-1], REASONS + ("UNKNOWN",), REASONS + (REASONS[0],)):
        _reject(reason_codes=value)
    for name, value in (("locked_repository_baseline", "0" * 40), ("locked_phase09_baseline", "0" * 40), ("readiness_state", "READY"), ("authorization_state", "AUTHORIZED"), ("content_integrity_acceptance_boundary_identity", "0" * 64), ("evidence_id", "0" * 64), ("inspection_readiness_decision_defined", False), ("acceptance_boundary_defined", False), ("launch_readiness", "READY"), ("production_effect", "SENT")):
        _reject(**{name: value})
    for name in FALSE_FIELDS: _reject(**{name: True})
    _reject(unknown_field="reject")


def test_identity_material_sensitivity_and_static_surface_are_inert():
    first = _evidence(prerequisite_checks=tuple(reversed(CHECKS)), blocker_codes=tuple(reversed(BLOCKERS)), reason_codes=tuple(reversed(REASONS)))
    payload = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "evidence_id"}
    variant = dict(payload); variant["integrity_inspection_ready"] = True
    assert first.identity == _evidence().identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    import engine.phase_11_shadow_pilot_integrity_inspection_readiness_decision_v1 as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "dotenv", "keyring", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules and not names & forbidden_names


def test_public_accessor_type_and_identity_are_stable():
    first = get_phase_11_shadow_pilot_integrity_inspection_readiness_decision_evidence_v1()
    second = get_phase_11_shadow_pilot_integrity_inspection_readiness_decision_evidence_v1()
    assert type(first) is ShadowPhase11IntegrityInspectionReadinessDecisionEvidenceV1
    assert first.identity == second.identity == _evidence().identity
