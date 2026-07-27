"""RED contract for immutable formal Phase 11 closure evidence."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_formal_closure_evidence_v1 import (
    ShadowPhase11FormalClosureEvidenceV1,
    ShadowPhase11FormalClosureEvidenceValidationError,
    ShadowPhase11FormalClosureOutcomeV1,
    ShadowPhase11FormalClosureStateV1,
    ShadowPhase11FormalClosureSuccessCriterionV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_formal_closure_evidence_v1,
    sha256_hex,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)


BASELINE = "33cef0fa294b02aa9472013010cb63faef3f581a"
PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_FORMAL_CLOSURE_EVIDENCE_001"
LINEAGE_REFERENCE = "PHASE_11_PILOT_FINAL_SUCCESSOR_LINEAGE_RECONCILIATION_001"
LINEAGE_IDENTITY = "146c73bd52e996c84d094ea70b2d783875c216bced2828e1fe61bbf6396b5f92"
CONSOLIDATION_REFERENCE = "PHASE_11_PILOT_FINAL_BLOCKER_CONSOLIDATION_001"
CONSOLIDATION_IDENTITY = "0d67bab3b15d7ebf9aa542046f797fb39c24a1c6e2b03cd21b20769fa6228bba"
SUCCESS_CRITERIA = tuple(sorted((
    "IMMUTABLE_GOVERNANCE_EVIDENCE_COMPLETE",
    "OPERATIONAL_EXECUTION_EXCLUDED",
    "BUDGET_COST_ATTEMPT_AND_ROUTE_BOUNDS_EXPLICIT",
    "PROVIDER_AND_CREDENTIAL_ACCESS_SEPARATED",
    "EXECUTABLE_CONTENT_AND_IDENTITY_ABSENT",
    "INSPECTION_VERIFICATION_AND_ACCEPTANCE_DENIED",
    "PROPOSED_MANIFEST_DEFINED_AND_INACTIVE",
    "RESERVATION_PROVIDER_REQUEST_AND_RUNTIME_ABSENT",
    "LAUNCH_AND_PRODUCTION_AUTHORITY_ABSENT",
    "ACTIVE_BLOCKER_DISPOSITIONS_COMPLETE",
    "FINAL_STATIC_LINEAGE_COMPLETE",
    "ZERO_PRODUCTION_PROOF_INTACT",
)))
BLOCKERS = tuple(sorted((
    "CONTENT_ACCESS_NOT_AUTHORIZED",
    "CONTENT_CREATION_AUTHORITY_NOT_GRANTED",
    "CONTENT_HASHING_NOT_AUTHORIZED",
    "CONTENT_INTEGRITY_NOT_VERIFIED",
    "CONTENT_NOT_ACCEPTED",
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "EXECUTABLE_CONTENT_IDENTITY_ABSENT",
    "EXECUTABLE_INPUT_CONTENT_ABSENT",
    "FILESYSTEM_READ_NOT_AUTHORIZED",
    "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
    "INTEGRITY_RESULT_ABSENT",
    "INTEGRITY_VERIFICATION_NOT_AUTHORIZED",
    "LAUNCH_NOT_AUTHORIZED",
    "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "PROVIDER_REQUEST_NOT_CREATED",
    "RESULT_ACCEPTANCE_NOT_AUTHORIZED",
    "RUNTIME_INVOCATION_NOT_AUTHORIZED",
    "RUN_SIZE_NOT_AUTHORIZED",
)))
REASONS = tuple(sorted((
    "CLOSURE_READINESS_AUDIT_PASSED",
    "SHADOW_GOVERNANCE_OBJECTIVES_SATISFIED",
    "FINAL_SUCCESSOR_LINEAGE_RECONCILED",
    "FINAL_BLOCKER_CONSOLIDATION_COMPLETE",
    "ALL_ACTIVE_BLOCKERS_REMAIN_CLASSIFIED",
    "NO_BLOCKER_RESOLVED_BY_CLOSURE_EVIDENCE",
    "DEFERRED_PREREQUISITES_REMAIN_UNAUTHORIZED",
    "LAUNCH_READINESS_REMAINS_BLOCKED",
    "PRODUCTION_EFFECT_REMAINS_NONE",
    "PHASE_11_COMPLETION_NOT_AUTHORIZED",
    "PHASE_12_ACTIVATION_NOT_AUTHORIZED",
    "NO_OPERATIONAL_AUTHORITY",
)))
TRUE_FIELDS = (
    "phase_11_shadow_governance_objectives_satisfied",
    "closure_readiness_audit_passed",
    "formal_closure_evidence_recorded",
    "final_lineage_reconciled",
    "final_blocker_consolidation_complete",
    "all_active_blockers_classified",
    "zero_production_proof_intact",
)
FALSE_FIELDS = (
    "operational_launch_ready",
    "production_ready",
    "phase_11_completion_authorized",
    "phase_11_completion_recorded",
    "phase_12_activation_ready",
    "phase_12_activation_authorized",
    "phase_12_activated",
    "blocker_resolution_authorized",
    "deferred_prerequisite_execution_authorized",
    "classification_changes_current_state",
    "content_creation_execution_authorized",
    "content_access_authorized",
    "filesystem_read_authorized",
    "filesystem_write_authorized",
    "content_hashing_authorized",
    "integrity_inspection_authorized",
    "integrity_verification_authorized",
    "result_acceptance_authorized",
    "manifest_mutation_authorized",
    "manifest_activation_authorized",
    "pricing_revalidation_execution_authorized",
    "credential_verification_execution_authorized",
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


def _criterion(
    criterion_code: str,
    **overrides: object,
) -> ShadowPhase11FormalClosureSuccessCriterionV1:
    values = {
        "criterion_code": criterion_code,
        "satisfied": True,
        "evidence_recorded": True,
        "grants_operational_authority": False,
        "grants_launch_authority": False,
        "grants_production_authority": False,
    }
    values.update(overrides)
    return ShadowPhase11FormalClosureSuccessCriterionV1(**values)


def _evidence(**overrides: object) -> ShadowPhase11FormalClosureEvidenceV1:
    values = {
        "schema_version": "phase11-shadow-pilot-formal-closure-evidence-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "closure_state": ShadowPhase11FormalClosureStateV1.CLOSURE_EVIDENCE_RECORDED_COMPLETION_NOT_AUTHORIZED,
        "closure_outcome": ShadowPhase11FormalClosureOutcomeV1.SHADOW_GOVERNANCE_OBJECTIVES_SATISFIED,
        "final_successor_lineage_reference": LINEAGE_REFERENCE,
        "final_successor_lineage_identity": LINEAGE_IDENTITY,
        "final_blocker_consolidation_reference": CONSOLIDATION_REFERENCE,
        "final_blocker_consolidation_identity": CONSOLIDATION_IDENTITY,
        "success_criteria": tuple(_criterion(code) for code in SUCCESS_CRITERIA),
        **{name: True for name in TRUE_FIELDS},
        "total_shadow_governance_objectives": 12,
        "total_satisfied_shadow_governance_objectives": 12,
        "total_active_blockers": 20,
        "total_classified_blockers": 20,
        "total_resolved_blockers": 0,
        "total_execution_authorized_blockers": 0,
        "total_shadow_governance_blockers": 6,
        "total_deferred_post_phase_11_prerequisites": 12,
        "total_explicitly_absent_launch_or_production_authorities": 2,
        **{name: False for name in FALSE_FIELDS},
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": BLOCKERS,
        "reason_codes": REASONS,
    }
    values.update(overrides)
    return ShadowPhase11FormalClosureEvidenceV1(**values)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11FormalClosureEvidenceValidationError):
        _evidence(**overrides)


def test_exact_closed_states_criteria_and_immutable_records():
    assert tuple(ShadowPhase11FormalClosureStateV1) == (
        ShadowPhase11FormalClosureStateV1.CLOSURE_EVIDENCE_RECORDED_COMPLETION_NOT_AUTHORIZED,
    )
    assert tuple(ShadowPhase11FormalClosureOutcomeV1) == (
        ShadowPhase11FormalClosureOutcomeV1.SHADOW_GOVERNANCE_OBJECTIVES_SATISFIED,
    )
    criterion = _criterion(SUCCESS_CRITERIA[0])
    evidence = _evidence()
    assert "__dict__" not in type(criterion).__slots__
    assert "__dict__" not in type(evidence).__slots__
    with pytest.raises(FrozenInstanceError):
        criterion.satisfied = False
    with pytest.raises(FrozenInstanceError):
        evidence.closure_state = "CLOSED"


def test_concrete_closure_evidence_records_success_without_completion_or_launch():
    evidence = _evidence()
    assert evidence.locked_repository_baseline == BASELINE
    assert evidence.final_successor_lineage_reference == LINEAGE_REFERENCE
    assert evidence.final_successor_lineage_identity == LINEAGE_IDENTITY
    assert evidence.final_blocker_consolidation_reference == CONSOLIDATION_REFERENCE
    assert evidence.final_blocker_consolidation_identity == CONSOLIDATION_IDENTITY
    assert all(getattr(evidence, name) for name in TRUE_FIELDS)
    assert not any(getattr(evidence, name) for name in FALSE_FIELDS)
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE"
    assert evidence.zero_production_proof == "PROVEN_NONE"
    assert (evidence.total_shadow_governance_objectives, evidence.total_satisfied_shadow_governance_objectives) == (12, 12)
    assert (evidence.total_active_blockers, evidence.total_classified_blockers, evidence.total_resolved_blockers, evidence.total_execution_authorized_blockers) == (20, 20, 0, 0)
    assert (evidence.total_shadow_governance_blockers, evidence.total_deferred_post_phase_11_prerequisites, evidence.total_explicitly_absent_launch_or_production_authorities) == (6, 12, 2)


def test_exact_satisfied_criteria_blockers_and_reasons_are_canonical():
    evidence = _evidence(
        success_criteria=tuple(reversed(tuple(_criterion(code) for code in SUCCESS_CRITERIA))),
        blocker_codes=tuple(reversed(BLOCKERS)),
        reason_codes=tuple(reversed(REASONS)),
    )
    assert tuple(item.criterion_code for item in evidence.success_criteria) == SUCCESS_CRITERIA
    assert evidence.blocker_codes == BLOCKERS
    assert evidence.reason_codes == REASONS
    assert all(item.satisfied and item.evidence_recorded for item in evidence.success_criteria)
    assert all(not item.grants_operational_authority and not item.grants_launch_authority and not item.grants_production_authority for item in evidence.success_criteria)
    for value in (SUCCESS_CRITERIA[:-1], SUCCESS_CRITERIA + (SUCCESS_CRITERIA[0],)):
        _reject(success_criteria=tuple(_criterion(code) for code in value))
    with pytest.raises(ShadowPhase11FormalClosureEvidenceValidationError):
        _criterion("UNKNOWN")
    for value in (BLOCKERS[:-1], BLOCKERS + ("UNKNOWN",), BLOCKERS + (BLOCKERS[0],)):
        _reject(blocker_codes=value)
    for value in (REASONS[:-1], REASONS + ("UNKNOWN",), REASONS + (REASONS[0],)):
        _reject(reason_codes=value)


def test_tampering_completion_and_authority_claims_are_rejected():
    for name, value in (
        ("locked_repository_baseline", "0" * 40),
        ("final_successor_lineage_identity", "0" * 64),
        ("final_blocker_consolidation_identity", "0" * 64),
        ("closure_state", "PHASE_11_COMPLETE"),
        ("closure_outcome", "OPERATIONALLY_READY"),
        ("total_active_blockers", 19),
        ("evidence_id", "0" * 64),
        ("launch_readiness", "READY"),
        ("production_effect", "SENT"),
    ):
        _reject(**{name: value})
    for name in TRUE_FIELDS:
        _reject(**{name: False})
    for name in FALSE_FIELDS:
        _reject(**{name: True})
    for name, value in (("satisfied", False), ("evidence_recorded", False), ("grants_operational_authority", True), ("grants_launch_authority", True), ("grants_production_authority", True)):
        with pytest.raises(ShadowPhase11FormalClosureEvidenceValidationError):
            _criterion(SUCCESS_CRITERIA[0], **{name: value})
    _reject(unknown_field="rejected")


def test_identity_is_canonical_materially_sensitive_and_has_no_operational_surface():
    first = _evidence(
        success_criteria=tuple(reversed(tuple(_criterion(code) for code in SUCCESS_CRITERIA))),
        blocker_codes=tuple(reversed(BLOCKERS)),
        reason_codes=tuple(reversed(REASONS)),
    )
    payload = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "evidence_id"}
    variant = dict(payload)
    variant["phase_11_completion_authorized"] = True
    assert first.identity == _evidence().identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    import engine.phase_11_shadow_pilot_formal_closure_evidence_v1 as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "dotenv", "keyring", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names


def test_public_accessor_is_stable_and_returns_exact_evidence_type():
    first = get_phase_11_shadow_pilot_formal_closure_evidence_v1()
    second = get_phase_11_shadow_pilot_formal_closure_evidence_v1()
    assert type(first) is ShadowPhase11FormalClosureEvidenceV1
    assert first.identity == second.identity == _evidence().identity
