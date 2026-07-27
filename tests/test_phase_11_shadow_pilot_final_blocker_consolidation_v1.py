"""RED contract for static Phase 11 final blocker consolidation."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_final_blocker_consolidation_v1 import (
    ShadowPhase11FinalBlockerClassV1,
    ShadowPhase11FinalBlockerConsolidationEvidenceV1,
    ShadowPhase11FinalBlockerConsolidationStateV1,
    ShadowPhase11FinalBlockerConsolidationValidationError,
    ShadowPhase11FinalBlockerDispositionV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_final_blocker_consolidation_evidence_v1,
    sha256_hex,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)


BASELINE = "ea3091b4487643cc9333372e3c02bc40611da066"
PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_FINAL_BLOCKER_CONSOLIDATION_001"
LINEAGE_REFERENCE = "PHASE_11_PILOT_FINAL_SUCCESSOR_LINEAGE_RECONCILIATION_001"
LINEAGE_IDENTITY = "146c73bd52e996c84d094ea70b2d783875c216bced2828e1fe61bbf6396b5f92"
BLOCKER_CLASS_BY_CODE = {
    "CONTENT_ACCESS_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER,
    "CONTENT_HASHING_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER,
    "FILESYSTEM_READ_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER,
    "INTEGRITY_INSPECTION_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER,
    "INTEGRITY_VERIFICATION_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER,
    "RESULT_ACCEPTANCE_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER,
    "CONTENT_CREATION_AUTHORITY_NOT_GRANTED": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "CONTENT_INTEGRITY_NOT_VERIFIED": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "CONTENT_NOT_ACCEPTED": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "EXECUTABLE_CONTENT_IDENTITY_ABSENT": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "EXECUTABLE_INPUT_CONTENT_ABSENT": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "INTEGRITY_RESULT_ABSENT": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "MANIFEST_ACTIVATION_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "PRE_CALL_RESERVATION_NOT_CREATED": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "PRICING_REVALIDATION_INCOMPLETE": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "PROVIDER_REQUEST_NOT_CREATED": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "RUNTIME_INVOCATION_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
    "LAUNCH_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY,
    "RUN_SIZE_NOT_AUTHORIZED": ShadowPhase11FinalBlockerClassV1.EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY,
}
BLOCKERS = tuple(sorted(BLOCKER_CLASS_BY_CODE))
REASONS = tuple(sorted((
    "FINAL_SUCCESSOR_LINEAGE_LINKED",
    "ALL_ACTIVE_BLOCKERS_CLASSIFIED",
    "NO_BLOCKER_RESOLVED_BY_CLASSIFICATION",
    "SHADOW_GOVERNANCE_BOUNDARIES_PRESERVED",
    "POST_PHASE_11_PREREQUISITES_DEFERRED",
    "LAUNCH_AND_PRODUCTION_AUTHORITIES_EXPLICITLY_ABSENT",
    "NO_EXECUTION_AUTHORITY_GRANTED",
    "PHASE_11_COMPLETION_NOT_IMPLIED",
    "PHASE_12_ACTIVATION_NOT_IMPLIED",
    "READINESS_REMAINS_BLOCKED",
    "NO_PRODUCTION_EFFECT",
)))
FALSE_FIELDS = (
    "classification_changes_current_state",
    "classification_grants_operational_authority",
    "classification_grants_launch_authority",
    "classification_grants_production_authority",
    "phase_11_completion_implied",
    "phase_12_activation_implied",
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


def _rationale(blocker_class: ShadowPhase11FinalBlockerClassV1) -> str:
    return {
        ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER: "SHADOW_GOVERNANCE_BOUNDARY_PRESERVED",
        ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE: "POST_PHASE_11_PREREQUISITE_DEFERRED",
        ShadowPhase11FinalBlockerClassV1.EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY: "LAUNCH_OR_PRODUCTION_AUTHORITY_ABSENT",
    }[blocker_class]


def _disposition(
    blocker_code: str,
    blocker_class: ShadowPhase11FinalBlockerClassV1 | None = None,
    **overrides: object,
) -> ShadowPhase11FinalBlockerDispositionV1:
    classification = blocker_class or BLOCKER_CLASS_BY_CODE[blocker_code]
    values = {
        "blocker_code": blocker_code,
        "blocker_class": classification,
        "blocker_active": True,
        "blocker_resolved": False,
        "execution_deferred": classification is ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
        "execution_authorized": False,
        "grants_launch_authority": False,
        "grants_production_authority": False,
        "rationale_code": _rationale(classification),
    }
    values.update(overrides)
    return ShadowPhase11FinalBlockerDispositionV1(**values)


def _evidence(
    **overrides: object,
) -> ShadowPhase11FinalBlockerConsolidationEvidenceV1:
    values = {
        "schema_version": "phase11-shadow-pilot-final-blocker-consolidation-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "final_successor_lineage_reference": LINEAGE_REFERENCE,
        "final_successor_lineage_identity": LINEAGE_IDENTITY,
        "consolidation_state": ShadowPhase11FinalBlockerConsolidationStateV1.ACTIVE_BLOCKERS_CLASSIFIED_NO_AUTHORITY_GRANTED,
        "blocker_codes": BLOCKERS,
        "dispositions": tuple(_disposition(code) for code in BLOCKERS),
        "total_active_blockers": 20,
        "total_classified_blockers": 20,
        "total_resolved_blockers": 0,
        "total_execution_authorized_blockers": 0,
        "all_blockers_classified": True,
        "all_blockers_remain_active": True,
        **{name: False for name in FALSE_FIELDS},
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "reason_codes": REASONS,
    }
    values.update(overrides)
    return ShadowPhase11FinalBlockerConsolidationEvidenceV1(**values)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11FinalBlockerConsolidationValidationError):
        _evidence(**overrides)


def test_exact_classes_state_and_immutable_disposition_contract():
    assert tuple(ShadowPhase11FinalBlockerClassV1) == (
        ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER,
        ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE,
        ShadowPhase11FinalBlockerClassV1.EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY,
    )
    assert tuple(ShadowPhase11FinalBlockerConsolidationStateV1) == (
        ShadowPhase11FinalBlockerConsolidationStateV1.ACTIVE_BLOCKERS_CLASSIFIED_NO_AUTHORITY_GRANTED,
    )
    disposition = _disposition(BLOCKERS[0])
    assert "__dict__" not in type(disposition).__slots__
    with pytest.raises(FrozenInstanceError):
        disposition.blocker_code = "INVALID"


def test_concrete_consolidation_classifies_each_exact_active_blocker_once():
    evidence = _evidence()
    assert evidence.final_successor_lineage_reference == LINEAGE_REFERENCE
    assert evidence.final_successor_lineage_identity == LINEAGE_IDENTITY
    assert evidence.blocker_codes == BLOCKERS
    assert tuple(item.blocker_code for item in evidence.dispositions) == BLOCKERS
    assert {item.blocker_code: item.blocker_class for item in evidence.dispositions} == BLOCKER_CLASS_BY_CODE
    assert all(item.blocker_active and not item.blocker_resolved for item in evidence.dispositions)
    assert all(not item.execution_authorized and not item.grants_launch_authority and not item.grants_production_authority for item in evidence.dispositions)
    assert all(item.execution_deferred is (item.blocker_class is ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE) for item in evidence.dispositions)


def test_exact_totals_reasons_and_convergent_ordering_are_enforced():
    evidence = _evidence(
        blocker_codes=tuple(reversed(BLOCKERS)),
        dispositions=tuple(reversed(tuple(_disposition(code) for code in BLOCKERS))),
        reason_codes=tuple(reversed(REASONS)),
    )
    assert evidence.blocker_codes == BLOCKERS
    assert tuple(item.blocker_code for item in evidence.dispositions) == BLOCKERS
    assert evidence.reason_codes == REASONS
    assert (evidence.total_active_blockers, evidence.total_classified_blockers, evidence.total_resolved_blockers, evidence.total_execution_authorized_blockers) == (20, 20, 0, 0)
    assert evidence.all_blockers_classified and evidence.all_blockers_remain_active
    for value in (BLOCKERS[:-1], BLOCKERS + ("UNKNOWN",), BLOCKERS + (BLOCKERS[0],)):
        _reject(blocker_codes=value)
    for value in (REASONS[:-1], REASONS + ("UNKNOWN",), REASONS + (REASONS[0],)):
        _reject(reason_codes=value)


def test_invalid_dispositions_and_authority_or_resolution_claims_are_rejected():
    duplicate = (_disposition(BLOCKERS[0]),) * 20
    wrong_class = _disposition(BLOCKERS[0], ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE)
    for value in (duplicate, tuple(_disposition(code) for code in BLOCKERS[:-1]), (wrong_class,) + tuple(_disposition(code) for code in BLOCKERS[1:])):
        _reject(dispositions=value)
    for name, value in (("blocker_active", False), ("blocker_resolved", True), ("execution_authorized", True), ("grants_launch_authority", True), ("grants_production_authority", True)):
        with pytest.raises(ShadowPhase11FinalBlockerConsolidationValidationError):
            _disposition(BLOCKERS[0], **{name: value})
    for name in FALSE_FIELDS:
        _reject(**{name: True})
    for name, value in (("locked_repository_baseline", "0" * 40), ("final_successor_lineage_identity", "0" * 64), ("consolidation_state", "RESOLVED"), ("total_active_blockers", 19), ("evidence_id", "0" * 64), ("launch_readiness", "READY"), ("production_effect", "SENT")):
        _reject(**{name: value})
    _reject(unknown_field="rejected")


def test_identity_material_sensitivity_evidence_immutability_and_static_surface():
    first = _evidence()
    payload = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "evidence_id"}
    variant = dict(payload)
    variant["classification_changes_current_state"] = True
    assert "__dict__" not in type(first).__slots__
    with pytest.raises(FrozenInstanceError):
        first.schema_version = "invalid"
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    import engine.phase_11_shadow_pilot_final_blocker_consolidation_v1 as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "dotenv", "keyring", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules and not names & forbidden_names


def test_public_accessor_is_stable_and_returns_exact_evidence_type():
    first = get_phase_11_shadow_pilot_final_blocker_consolidation_evidence_v1()
    second = get_phase_11_shadow_pilot_final_blocker_consolidation_evidence_v1()
    assert type(first) is ShadowPhase11FinalBlockerConsolidationEvidenceV1
    assert first.identity == second.identity == _evidence().identity
