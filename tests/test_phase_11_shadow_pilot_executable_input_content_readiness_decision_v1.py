"""RED contract for immutable executable-input content readiness decisions."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_credential_configuration_verification_boundary_v1 import (
    get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1,
)
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import (
    get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1,
)
from engine.phase_11_shadow_pilot_executable_input_content_readiness_decision_v1 import (
    ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1,
    ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1,
    ShadowPhase11ExecutableInputContentReadinessDecisionValidationError,
    ShadowPhase11ExecutableInputContentReadinessStateV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_executable_input_content_readiness_decision_evidence_v1,
    sha256_hex,
)
from engine.phase_11_shadow_pilot_executable_input_creation_boundary_v1 import (
    get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1,
)
from engine.phase_11_shadow_pilot_input_run_manifest_readiness_v1 import (
    get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_revalidation_boundary_v1 import (
    get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1,
)
from engine.phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_v1 import (
    get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1,
)


BASELINE = "cc1127f57ebfc0a880fc22d57ded60fcbd59cc9f"
PHASE09 = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_READINESS_DECISION_001"
CHECKS = (
    ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1.CANDIDATE_METADATA_COMPLETE,
    ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1.ROUTE_ROLE_AND_BOUND_CONFIGURATION_FIXED,
    ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1.PRICING_REVALIDATION_COMPLETED,
    ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1.CREDENTIAL_CONFIGURATION_VERIFIED,
    ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1.CONTENT_CREATION_AUTHORITY_GRANTED,
    ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1.CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_DEFINED,
    ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1.MANIFEST_ACTIVATION_AUTHORITY_GRANTED,
)
BLOCKERS = tuple(sorted((
    "PRICING_REVALIDATION_INCOMPLETE",
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "CONTENT_CREATION_AUTHORITY_NOT_GRANTED",
    "CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_ABSENT",
    "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
)))
REASONS = tuple(sorted((
    "READINESS_ASSESSMENT_DEFINED",
    "READINESS_ASSESSMENT_NOT_PERFORMED",
    "CANDIDATE_METADATA_COMPLETE",
    "ROUTE_ROLE_AND_BOUNDS_FIXED",
    "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
    "CONTENT_CREATION_NOT_AUTHORIZED",
    "CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_NOT_DEFINED",
    "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
    "NO_OPERATIONAL_AUTHORITY",
)))

_FALSE_FIELDS = (
    "readiness_assessment_execution_authorized",
    "readiness_assessment_performed",
    "content_creation_ready",
    "content_creation_execution_authorized",
    "source_content_access_authorized",
    "source_content_access_observed",
    "filesystem_read_authorized",
    "filesystem_read_observed",
    "filesystem_write_authorized",
    "filesystem_write_observed",
    "executable_content_generation_authorized",
    "executable_content_generated",
    "executable_content_serialized",
    "executable_input_content_present",
    "content_integrity_acceptance_boundary_defined",
    "content_integrity_verified",
    "manifest_mutation_authorized",
    "proposed_manifest_modified",
    "manifest_activation_authorized",
    "proposed_manifest_activated",
    "pricing_revalidation_execution_authorized",
    "pricing_revalidation_completed",
    "credential_verification_execution_authorized",
    "credential_configuration_verified",
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


def _evidence(**overrides: object) -> ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1:
    successor = get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1()
    creation = get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1()
    readiness = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    manifest = readiness.proposed_manifest
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    credential = get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-executable-input-content-readiness-decision-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "readiness_state": ShadowPhase11ExecutableInputContentReadinessStateV1.NOT_READY_FOR_CONTENT_CREATION,
        "current_successor_reconciliation_reference": successor.evidence_reference,
        "current_successor_reconciliation_identity": successor.identity,
        "executable_input_creation_boundary_reference": creation.evidence_reference,
        "executable_input_creation_boundary_identity": creation.identity,
        "input_run_manifest_readiness_reference": readiness.evidence_reference,
        "input_run_manifest_readiness_identity": readiness.identity,
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
        "prerequisite_checks": CHECKS,
        "readiness_assessment_defined": True,
        "candidate_metadata_complete": True,
        "route_role_and_bounds_fixed": True,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": BLOCKERS,
        "reason_codes": REASONS,
    }
    fields.update({name: False for name in _FALSE_FIELDS})
    fields.update(overrides)
    return ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1(**fields)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11ExecutableInputContentReadinessDecisionValidationError):
        _evidence(**overrides)


def test_closed_state_and_prerequisite_vocabulary_are_exact_and_evidence_is_immutable():
    assert tuple(ShadowPhase11ExecutableInputContentReadinessStateV1) == (
        ShadowPhase11ExecutableInputContentReadinessStateV1.NOT_READY_FOR_CONTENT_CREATION,
    )
    assert tuple(ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1) == CHECKS
    evidence = _evidence()
    assert getattr(ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1, "__slots__")
    assert "__dict__" not in ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1.__slots__
    with pytest.raises(FrozenInstanceError):
        evidence.launch_authorized = True


def test_concrete_decision_links_exact_upstream_identity_and_is_conservatively_blocked():
    evidence = _evidence()
    assert evidence.locked_repository_baseline == BASELINE
    assert evidence.current_successor_reconciliation_identity == "709c842c8f56135220ff9e68f68bc0693e48ae2047d25f72d9929295f8f90215"
    assert evidence.executable_input_creation_boundary_identity == "f82aef927d6d0e4c0e021e597bd8fcba8ed9426e5c56ad551947ea1052f1c097"
    assert evidence.input_run_manifest_readiness_identity == "9dffc3370346370284fe5a630a32e78be6def065428060ce70eea8cddf0fd228"
    assert evidence.candidate_input_set_identity == "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
    assert evidence.proposed_manifest_identity == "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
    assert evidence.pricing_revalidation_boundary_identity == "33d25cac84df17608b41008b4c91160dd57354e059f1ae6f6a711db2a3beed59"
    assert evidence.credential_verification_boundary_identity == "f4b9ef09b6e17875a484d833525ccc3410049fc885f20c149f4df7445515fc91"
    assert evidence.current_runtime_integrity_identity == "72342b2390f32463f6d5104f47d3dc29ff5067349daec61a4fe5565de725b51e"
    assert evidence.reservation_bound_identity == "424a3a332c31a3143ee3a4b6ab8b37b7ec440ea0fcf3c6a01566e451bb11cb70"
    assert evidence.readiness_assessment_defined is True
    assert evidence.candidate_metadata_complete is True
    assert evidence.route_role_and_bounds_fixed is True
    assert evidence.prerequisite_checks == CHECKS
    assert not any(getattr(evidence, name) for name in _FALSE_FIELDS)
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE"
    assert evidence.zero_production_proof == "PROVEN_NONE"


def test_prerequisite_check_ordering_canonicalizes_and_only_metadata_and_bounds_are_satisfied():
    evidence = _evidence(prerequisite_checks=tuple(reversed(CHECKS)))
    assert evidence.prerequisite_checks == CHECKS
    for value in (
        CHECKS[:-1],
        CHECKS + (CHECKS[0],),
        CHECKS[:-1] + ("UNKNOWN_CHECK",),
    ):
        _reject(prerequisite_checks=value)
    for name in (
        "pricing_revalidation_completed",
        "credential_configuration_verified",
        "content_creation_execution_authorized",
        "content_integrity_acceptance_boundary_defined",
        "manifest_activation_authorized",
    ):
        _reject(**{name: True})


def test_exact_blockers_and_reasons_canonicalize_and_reject_obsolete_or_granting_values():
    evidence = _evidence(
        blocker_codes=tuple(reversed(BLOCKERS)),
        reason_codes=tuple(reversed(REASONS)),
    )
    assert evidence.blocker_codes == BLOCKERS
    assert evidence.reason_codes == REASONS
    for value in (
        BLOCKERS[:-1],
        BLOCKERS + ("UNKNOWN_BLOCKER",),
        BLOCKERS + (BLOCKERS[0],),
        BLOCKERS[:-1] + ("EXECUTABLE_INPUT_CONTENT_ABSENT",),
        BLOCKERS[:-1] + ("CONTENT_CREATION_AUTHORIZED",),
    ):
        _reject(blocker_codes=value)
    for value in (
        REASONS[:-1],
        REASONS + ("UNKNOWN_REASON",),
        REASONS + (REASONS[0],),
        REASONS[:-1] + ("READINESS_ASSESSMENT_COMPLETED",),
        REASONS[:-1] + ("CONTENT_CREATION_AUTHORIZED",),
    ):
        _reject(reason_codes=value)


def test_constructor_rejects_tampering_unknown_fields_and_all_execution_or_authority_claims():
    for name, value in (
        ("locked_repository_baseline", "0" * 40),
        ("locked_phase09_baseline", "0" * 40),
        ("readiness_state", "READY"),
        ("current_successor_reconciliation_identity", "0" * 64),
        ("executable_input_creation_boundary_identity", "0" * 64),
        ("candidate_input_set_identity", "0" * 64),
        ("proposed_manifest_identity", "0" * 64),
        ("pricing_revalidation_boundary_identity", "0" * 64),
        ("credential_verification_boundary_identity", "0" * 64),
        ("current_runtime_integrity_identity", "0" * 64),
        ("reservation_bound_identity", "0" * 64),
        ("readiness_assessment_defined", False),
        ("candidate_metadata_complete", False),
        ("route_role_and_bounds_fixed", False),
        ("launch_readiness", "READY"),
        ("production_effect", "SENT"),
        ("zero_production_proof", "NOT_PROVEN"),
        ("evidence_id", "0" * 64),
    ):
        _reject(**{name: value})
    for name in _FALSE_FIELDS:
        _reject(**{name: True})
    _reject(unknown_field="reject")


def test_identity_converges_detached_mutation_diverges_and_static_surface_is_inert():
    first = _evidence(
        prerequisite_checks=tuple(reversed(CHECKS)),
        blocker_codes=tuple(reversed(BLOCKERS)),
        reason_codes=tuple(reversed(REASONS)),
    )
    payload = {
        name: getattr(first, name)
        for name in first.__dataclass_fields__
        if name != "evidence_id"
    }
    variant = dict(payload)
    variant["content_creation_ready"] = True
    assert first.identity == _evidence().identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\xc3\xa9"}'

    import engine.phase_11_shadow_pilot_executable_input_content_readiness_decision_v1 as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "dotenv", "keyring", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names


def test_public_accessor_type_and_identity_are_exact_and_stable():
    first = get_phase_11_shadow_pilot_executable_input_content_readiness_decision_evidence_v1()
    second = get_phase_11_shadow_pilot_executable_input_content_readiness_decision_evidence_v1()
    assert type(first) is ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1
    assert first.identity == second.identity == _evidence().identity
