"""RED contract for final static Phase 11 successor-lineage reconciliation."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_final_successor_lineage_reconciliation_v1 import (
    ShadowPhase11FinalSuccessorLineagePredecessorStatusV1,
    ShadowPhase11FinalSuccessorLineageReconciliationEvidenceV1,
    ShadowPhase11FinalSuccessorLineageReconciliationStateV1,
    ShadowPhase11FinalSuccessorLineageReconciliationValidationError,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_final_successor_lineage_reconciliation_evidence_v1,
    sha256_hex,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)


BASELINE = "d1c583ec3284e6626bd499d23d7ba15a6dae1b60"
PHASE09 = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_FINAL_SUCCESSOR_LINEAGE_RECONCILIATION_001"
BLOCKERS = tuple(
    sorted(
        (
            "PRICING_REVALIDATION_INCOMPLETE",
            "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
            "CONTENT_CREATION_AUTHORITY_NOT_GRANTED",
            "EXECUTABLE_INPUT_CONTENT_ABSENT",
            "EXECUTABLE_CONTENT_IDENTITY_ABSENT",
            "CONTENT_ACCESS_NOT_AUTHORIZED",
            "FILESYSTEM_READ_NOT_AUTHORIZED",
            "CONTENT_HASHING_NOT_AUTHORIZED",
            "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
            "INTEGRITY_VERIFICATION_NOT_AUTHORIZED",
            "RESULT_ACCEPTANCE_NOT_AUTHORIZED",
            "INTEGRITY_RESULT_ABSENT",
            "CONTENT_INTEGRITY_NOT_VERIFIED",
            "CONTENT_NOT_ACCEPTED",
            "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
            "PRE_CALL_RESERVATION_NOT_CREATED",
            "PROVIDER_REQUEST_NOT_CREATED",
            "RUNTIME_INVOCATION_NOT_AUTHORIZED",
            "RUN_SIZE_NOT_AUTHORIZED",
            "LAUNCH_NOT_AUTHORIZED",
        )
    )
)
REASONS = tuple(
    sorted(
        (
            "PREDECESSOR_SUCCESSOR_LINEAGE_PRESERVED",
            "INSPECTION_READINESS_DECISION_LINKED",
            "CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_LINKED",
            "CONTENT_READINESS_DECISION_LINKED",
            "EXECUTABLE_INPUT_CREATION_BOUNDARY_LINKED",
            "INSPECTION_REMAINS_UNAUTHORIZED",
            "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
            "CONTENT_INTEGRITY_REMAINS_UNVERIFIED",
            "CONTENT_REMAINS_UNACCEPTED",
            "PROPOSED_MANIFEST_REMAINS_INACTIVE",
            "ALL_OPERATIONAL_BLOCKERS_PRESERVED",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)
LINKS = {
    "predecessor_successor_reconciliation_reference": "PHASE_11_PILOT_SUCCESSOR_EXECUTABLE_INPUT_BOUNDARY_RECONCILIATION_001",
    "predecessor_successor_reconciliation_identity": "709c842c8f56135220ff9e68f68bc0693e48ae2047d25f72d9929295f8f90215",
    "inspection_readiness_decision_reference": "PHASE_11_PILOT_INTEGRITY_INSPECTION_READINESS_DECISION_001",
    "inspection_readiness_decision_identity": "e376ac0f07a34ea4f23f5892175669aea8ef0938061995a162a4012ad06e58fb",
    "content_integrity_acceptance_boundary_reference": "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_001",
    "content_integrity_acceptance_boundary_identity": "762a122c406ccd3b1bc9b2b3bb00d438f292fc530a5cef33024e759140dd136d",
    "content_readiness_decision_reference": "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_READINESS_DECISION_001",
    "content_readiness_decision_identity": "dee8284ca5fdadf414b04c0e689fc10c777759e18bf7954f7efce1f851652822",
    "executable_input_creation_boundary_reference": "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001",
    "executable_input_creation_boundary_identity": "f82aef927d6d0e4c0e021e597bd8fcba8ed9426e5c56ad551947ea1052f1c097",
    "pricing_revalidation_boundary_reference": "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001",
    "pricing_revalidation_boundary_identity": "33d25cac84df17608b41008b4c91160dd57354e059f1ae6f6a711db2a3beed59",
    "credential_verification_boundary_reference": "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_BOUNDARY_001",
    "credential_verification_boundary_identity": "f4b9ef09b6e17875a484d833525ccc3410049fc885f20c149f4df7445515fc91",
    "input_run_manifest_readiness_reference": "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001",
    "input_run_manifest_readiness_identity": "9dffc3370346370284fe5a630a32e78be6def065428060ce70eea8cddf0fd228",
    "candidate_input_set_identity": "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c",
    "proposed_manifest_reference": "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001",
    "proposed_manifest_identity": "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a",
    "current_runtime_integrity_reference": "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001",
    "current_runtime_integrity_identity": "72342b2390f32463f6d5104f47d3dc29ff5067349daec61a4fe5565de725b51e",
    "reservation_bound_reference": "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001",
    "reservation_bound_identity": "424a3a332c31a3143ee3a4b6ab8b37b7ec440ea0fcf3c6a01566e451bb11cb70",
}
TRUE_FIELDS = (
    "inspection_readiness_decision_defined",
    "acceptance_boundary_defined",
    "executable_input_creation_descriptor_defined",
    "pricing_revalidation_descriptor_defined",
    "credential_verification_descriptor_defined",
    "candidate_input_metadata_defined",
    "proposed_manifest_defined",
)
FALSE_FIELDS = (
    "predecessor_successor_reconciliation_mutated",
    "predecessor_successor_reconciliation_transitioned",
    "predecessor_successor_reconciliation_current_authority",
    "inspection_prerequisite_assessment_execution_authorized",
    "inspection_prerequisite_assessment_performed",
    "integrity_inspection_ready",
    "integrity_inspection_authorized",
    "integrity_inspection_started",
    "integrity_inspection_completed",
    "integrity_result_present",
    "content_creation_execution_authorized",
    "content_access_authorized",
    "content_access_observed",
    "filesystem_read_authorized",
    "filesystem_read_observed",
    "filesystem_write_authorized",
    "filesystem_write_observed",
    "content_hashing_authorized",
    "content_hashing_observed",
    "integrity_verification_authorized",
    "content_integrity_verified",
    "result_acceptance_authorized",
    "content_accepted",
    "executable_input_content_present",
    "executable_content_identity_present",
    "proposed_manifest_modified",
    "manifest_mutation_authorized",
    "proposed_manifest_activated",
    "manifest_activation_authorized",
    "pricing_revalidation_execution_authorized",
    "pricing_revalidation_started",
    "pricing_revalidation_result_present",
    "pricing_revalidation_completed",
    "credential_verification_execution_authorized",
    "credential_verification_started",
    "credential_verification_result_present",
    "credential_verification_completed",
    "credential_configuration_verified",
    "credential_or_secret_access_observed",
    "environment_access_observed",
    "provider_request_created",
    "pre_call_reservation_created",
    "ledger_entry_created",
    "runtime_invocation_authorized",
    "provider_call_authorized",
    "provider_transmission_authorized",
    "run_size_authorized",
    "launch_authorized",
    "production_authorized",
)


def _evidence(
    **overrides: object,
) -> ShadowPhase11FinalSuccessorLineageReconciliationEvidenceV1:
    values = {
        "schema_version": "phase11-shadow-pilot-final-successor-lineage-reconciliation-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "reconciliation_state": ShadowPhase11FinalSuccessorLineageReconciliationStateV1.FINAL_STATIC_LINEAGE_RECONCILED_READINESS_BLOCKED,
        "predecessor_status": ShadowPhase11FinalSuccessorLineagePredecessorStatusV1.PREDECESSOR_SUCCESSOR_LINEAGE_PRESERVED,
        **LINKS,
        **{name: True for name in TRUE_FIELDS},
        **{name: False for name in FALSE_FIELDS},
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": BLOCKERS,
        "reason_codes": REASONS,
    }
    values.update(overrides)
    return ShadowPhase11FinalSuccessorLineageReconciliationEvidenceV1(**values)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11FinalSuccessorLineageReconciliationValidationError):
        _evidence(**overrides)


def test_closed_states_predecessor_and_evidence_immutability_are_exact():
    assert tuple(ShadowPhase11FinalSuccessorLineageReconciliationStateV1) == (
        ShadowPhase11FinalSuccessorLineageReconciliationStateV1.FINAL_STATIC_LINEAGE_RECONCILED_READINESS_BLOCKED,
    )
    assert tuple(ShadowPhase11FinalSuccessorLineagePredecessorStatusV1) == (
        ShadowPhase11FinalSuccessorLineagePredecessorStatusV1.PREDECESSOR_SUCCESSOR_LINEAGE_PRESERVED,
    )
    evidence = _evidence()
    assert "__dict__" not in type(evidence).__slots__
    with pytest.raises(FrozenInstanceError):
        evidence.schema_version = "invalid"


def test_concrete_final_lineage_preserves_predecessor_and_current_truth():
    evidence = _evidence()
    assert evidence.locked_repository_baseline == BASELINE
    assert evidence.predecessor_successor_reconciliation_identity == LINKS["predecessor_successor_reconciliation_identity"]
    assert evidence.inspection_readiness_decision_identity == LINKS["inspection_readiness_decision_identity"]
    assert evidence.content_integrity_acceptance_boundary_identity == LINKS["content_integrity_acceptance_boundary_identity"]
    assert evidence.content_readiness_decision_identity == LINKS["content_readiness_decision_identity"]
    assert all(getattr(evidence, name) for name in TRUE_FIELDS)
    assert not any(getattr(evidence, name) for name in FALSE_FIELDS)
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE"
    assert evidence.zero_production_proof == "PROVEN_NONE"


def test_exact_consolidated_blockers_and_final_reasons_are_canonical():
    evidence = _evidence(
        blocker_codes=tuple(reversed(BLOCKERS)),
        reason_codes=tuple(reversed(REASONS)),
    )
    assert evidence.blocker_codes == BLOCKERS
    assert evidence.reason_codes == REASONS
    for value in (
        BLOCKERS[:-1],
        BLOCKERS + ("UNKNOWN",),
        BLOCKERS + (BLOCKERS[0],),
        tuple(code for code in BLOCKERS if code != "INTEGRITY_RESULT_ABSENT")
        + ("CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_ABSENT",),
        tuple(code for code in BLOCKERS if code != "MANIFEST_ACTIVATION_NOT_AUTHORIZED")
        + ("PROPOSED_MANIFEST_NOT_ACTIVATED",),
    ):
        _reject(blocker_codes=value)
    for value in (REASONS[:-1], REASONS + ("UNKNOWN",), REASONS + (REASONS[0],)):
        _reject(reason_codes=value)


def test_tampering_and_all_execution_or_authority_claims_are_rejected():
    for name, value in (
        ("locked_repository_baseline", "0" * 40),
        ("locked_phase09_baseline", "0" * 40),
        ("reconciliation_state", "READY"),
        ("predecessor_status", "CURRENT"),
        ("predecessor_successor_reconciliation_identity", "0" * 64),
        ("inspection_readiness_decision_identity", "0" * 64),
        ("evidence_id", "0" * 64),
        ("inspection_readiness_decision_defined", False),
        ("acceptance_boundary_defined", False),
        ("launch_readiness", "READY"),
        ("production_effect", "SENT"),
    ):
        _reject(**{name: value})
    for name in FALSE_FIELDS:
        _reject(**{name: True})
    _reject(unknown_field="rejected")


def test_identity_is_canonical_materially_sensitive_and_static():
    first = _evidence(
        blocker_codes=tuple(reversed(BLOCKERS)),
        reason_codes=tuple(reversed(REASONS)),
    )
    payload = {
        name: getattr(first, name)
        for name in first.__dataclass_fields__
        if name != "evidence_id"
    }
    variant = dict(payload)
    variant["integrity_inspection_authorized"] = True
    assert first.identity == _evidence().identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    import engine.phase_11_shadow_pilot_final_successor_lineage_reconciliation_v1 as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "dotenv", "keyring", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names


def test_public_accessor_is_stable_and_returns_exact_evidence_type():
    first = get_phase_11_shadow_pilot_final_successor_lineage_reconciliation_evidence_v1()
    second = get_phase_11_shadow_pilot_final_successor_lineage_reconciliation_evidence_v1()
    assert type(first) is ShadowPhase11FinalSuccessorLineageReconciliationEvidenceV1
    assert first.identity == second.identity == _evidence().identity
