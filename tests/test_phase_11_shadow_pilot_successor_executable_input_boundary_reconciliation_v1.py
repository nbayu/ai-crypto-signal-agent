"""RED contract for Phase 11 executable-input successor reconciliation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_credential_configuration_verification_boundary_v1 import (
    get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1,
)
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import (
    get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1,
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
from engine.phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_v1 import (
    get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1,
)
from engine.phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_v1 import (
    ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1,
    ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError,
    ShadowPhase11SuccessorExecutableInputPredecessorStatusV1,
    ShadowPhase11SuccessorExecutableInputBoundaryReconciliationStateV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1,
    sha256_hex,
)


BASELINE = "55c9fda8c6decc974528f86b3306ff7a9dfa8200"
PHASE09 = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_SUCCESSOR_EXECUTABLE_INPUT_BOUNDARY_RECONCILIATION_001"
)
BLOCKERS = tuple(sorted((
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "EXECUTABLE_INPUT_CONTENT_ABSENT",
    "LAUNCH_NOT_AUTHORIZED",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "PROPOSED_MANIFEST_NOT_ACTIVATED",
    "PROVIDER_REQUEST_NOT_CREATED",
    "RUN_SIZE_NOT_AUTHORIZED",
    "RUNTIME_INVOCATION_NOT_AUTHORIZED",
)))
REASONS = tuple(sorted((
    "PREDECESSOR_SUCCESSOR_RECONCILIATION_PRESERVED",
    "EXECUTABLE_INPUT_BOUNDARY_LINKED",
    "EXECUTABLE_INPUT_DESCRIPTOR_RECOGNIZED",
    "EXECUTABLE_INPUT_CREATION_NOT_EXECUTED",
    "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
    "PROPOSED_MANIFEST_REMAINS_INACTIVE",
    "NO_OPERATIONAL_AUTHORITY",
)))
FUTURE_PATH = (
    "engine/phase_11_shadow_pilot_successor_executable_input_"
    "boundary_reconciliation_v1.py"
)


def _evidence(
    **overrides: object,
) -> ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1:
    predecessor = (
        get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1()
    )
    executable = get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    credential = (
        get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1()
    )
    readiness = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    manifest = readiness.proposed_manifest
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-successor-executable-input-boundary-reconciliation-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "reconciliation_state": ShadowPhase11SuccessorExecutableInputBoundaryReconciliationStateV1.EXECUTABLE_INPUT_BOUNDARY_RECONCILED_READINESS_BLOCKED,
        "predecessor_status": ShadowPhase11SuccessorExecutableInputPredecessorStatusV1.PREDECESSOR_SUCCESSOR_RECONCILIATION_PRESERVED,
        "predecessor_successor_reconciliation_reference": predecessor.evidence_reference,
        "predecessor_successor_reconciliation_identity": predecessor.identity,
        "predecessor_successor_reconciliation_mutated": False,
        "predecessor_successor_reconciliation_transitioned": False,
        "predecessor_successor_reconciliation_current_authority": False,
        "executable_input_creation_boundary_reference": executable.evidence_reference,
        "executable_input_creation_boundary_identity": executable.identity,
        "executable_input_creation_descriptor_defined": True,
        "executable_input_creation_execution_authorized": False,
        "executable_input_creation_started": False,
        "executable_input_creation_result_present": False,
        "executable_input_creation_completed": False,
        "source_content_access_observed": False,
        "filesystem_write_observed": False,
        "executable_content_generated": False,
        "executable_content_serialized": False,
        "executable_input_content_present": False,
        "content_integrity_verified": False,
        "proposed_manifest_modified": False,
        "proposed_manifest_activated": False,
        "pricing_revalidation_boundary_reference": pricing.evidence_reference,
        "pricing_revalidation_boundary_identity": pricing.identity,
        "pricing_revalidation_descriptor_defined": True,
        "pricing_revalidation_execution_authorized": False,
        "pricing_revalidation_started": False,
        "pricing_revalidation_result_present": False,
        "pricing_revalidation_completed": False,
        "fresh_provider_pricing_observed": False,
        "credential_verification_boundary_reference": credential.evidence_reference,
        "credential_verification_boundary_identity": credential.identity,
        "credential_verification_descriptor_defined": True,
        "credential_verification_execution_authorized": False,
        "credential_verification_started": False,
        "credential_verification_result_present": False,
        "credential_verification_completed": False,
        "credential_configuration_verified": False,
        "credential_or_secret_access_observed": False,
        "environment_access_observed": False,
        "filesystem_access_observed": False,
        "network_access_observed": False,
        "provider_authentication_probe_performed": False,
        "input_run_manifest_readiness_reference": readiness.evidence_reference,
        "input_run_manifest_readiness_identity": readiness.identity,
        "candidate_input_set_identity": manifest.candidate_input_set_identity,
        "proposed_manifest_reference": manifest.manifest_reference,
        "proposed_manifest_identity": manifest.identity,
        "current_runtime_integrity_reference": runtime.evidence_reference,
        "current_runtime_integrity_identity": runtime.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "candidate_input_metadata_defined": True,
        "proposed_manifest_defined": True,
        "pre_call_reservation_created": False,
        "ledger_entry_created": False,
        "provider_request_created": False,
        "runtime_invocation_authorized": False,
        "provider_call_authorized": False,
        "provider_transmission_authorized": False,
        "run_size_authorized": False,
        "manifest_activation_authorized": False,
        "launch_authorized": False,
        "production_authorized": False,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": BLOCKERS,
        "reason_codes": REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1(
        **fields
    )


def _reject(**overrides: object) -> None:
    with pytest.raises(
        ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError
    ):
        _evidence(**overrides)


def test_closed_reconciliation_and_predecessor_states_are_exact_and_evidence_is_closed():
    assert tuple(ShadowPhase11SuccessorExecutableInputBoundaryReconciliationStateV1) == (
        ShadowPhase11SuccessorExecutableInputBoundaryReconciliationStateV1.EXECUTABLE_INPUT_BOUNDARY_RECONCILED_READINESS_BLOCKED,
    )
    assert tuple(ShadowPhase11SuccessorExecutableInputPredecessorStatusV1) == (
        ShadowPhase11SuccessorExecutableInputPredecessorStatusV1.PREDECESSOR_SUCCESSOR_RECONCILIATION_PRESERVED,
    )
    assert getattr(
        ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1,
        "__slots__",
    )
    assert (
        "__dict__"
        not in ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1.__slots__
    )


def test_predecessor_and_executable_input_boundary_are_exactly_linked_and_preserved():
    evidence = _evidence()
    assert (
        evidence.predecessor_successor_reconciliation_reference,
        evidence.predecessor_successor_reconciliation_identity,
    ) == (
        "PHASE_11_PILOT_SUCCESSOR_BLOCKED_READINESS_BOUNDARY_RECONCILIATION_001",
        "e5873183a2d289283d9fc2849cb28e86aaf1a69bbd8ac5e9f7709877c9496446",
    )
    assert (
        evidence.executable_input_creation_boundary_reference,
        evidence.executable_input_creation_boundary_identity,
    ) == (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001",
        "f82aef927d6d0e4c0e021e597bd8fcba8ed9426e5c56ad551947ea1052f1c097",
    )
    assert evidence.executable_input_creation_descriptor_defined is True
    assert not any(getattr(evidence, field) for field in (
        "predecessor_successor_reconciliation_mutated",
        "predecessor_successor_reconciliation_transitioned",
        "predecessor_successor_reconciliation_current_authority",
        "executable_input_creation_execution_authorized",
        "executable_input_creation_started",
        "executable_input_creation_result_present",
        "executable_input_creation_completed",
        "source_content_access_observed",
        "filesystem_write_observed",
        "executable_content_generated",
        "executable_content_serialized",
        "executable_input_content_present",
        "content_integrity_verified",
        "proposed_manifest_modified",
        "proposed_manifest_activated",
    ))


def test_pricing_credential_and_other_current_state_linkage_remain_blocked():
    evidence = _evidence()
    assert evidence.pricing_revalidation_descriptor_defined is True
    assert evidence.credential_verification_descriptor_defined is True
    assert evidence.candidate_input_metadata_defined is True
    assert evidence.proposed_manifest_defined is True
    assert evidence.input_run_manifest_readiness_identity == (
        "9dffc3370346370284fe5a630a32e78be6def065428060ce70eea8cddf0fd228"
    )
    assert evidence.candidate_input_set_identity == (
        "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
    )
    assert evidence.proposed_manifest_identity == (
        "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
    )
    assert not any(getattr(evidence, field) for field in (
        "pricing_revalidation_execution_authorized",
        "pricing_revalidation_started",
        "pricing_revalidation_result_present",
        "pricing_revalidation_completed",
        "fresh_provider_pricing_observed",
        "credential_verification_execution_authorized",
        "credential_verification_started",
        "credential_verification_result_present",
        "credential_verification_completed",
        "credential_configuration_verified",
        "credential_or_secret_access_observed",
        "environment_access_observed",
        "filesystem_access_observed",
        "network_access_observed",
        "provider_authentication_probe_performed",
        "pre_call_reservation_created",
        "ledger_entry_created",
        "provider_request_created",
        "runtime_invocation_authorized",
        "provider_call_authorized",
        "provider_transmission_authorized",
        "run_size_authorized",
        "manifest_activation_authorized",
        "launch_authorized",
        "production_authorized",
    ))
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE"
    assert evidence.zero_production_proof == "PROVEN_NONE"


def test_exact_active_blockers_and_reasons_canonicalize_and_reject_obsolete_values():
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
        tuple(code for code in BLOCKERS if code != "EXECUTABLE_INPUT_CONTENT_ABSENT") + (
            "EXECUTABLE_INPUT_BOUNDARY_ABSENT",
        ),
        tuple(code for code in BLOCKERS if code != "EXECUTABLE_INPUT_CONTENT_ABSENT") + (
            "EXECUTABLE_INPUT_DESCRIPTOR_ABSENT",
        ),
        tuple(code for code in BLOCKERS if code != "EXECUTABLE_INPUT_CONTENT_ABSENT") + (
            "CANDIDATE_INPUT_METADATA_ABSENT",
        ),
        tuple(code for code in BLOCKERS if code != "PROPOSED_MANIFEST_NOT_ACTIVATED") + (
            "PROPOSED_MANIFEST_DEFINITION_ABSENT",
        ),
        tuple(code for code in BLOCKERS if code != "PRICING_REVALIDATION_INCOMPLETE") + (
            "PRICING_REVALIDATION_BOUNDARY_ABSENT",
        ),
        tuple(code for code in BLOCKERS if code != "CREDENTIAL_CONFIGURATION_NOT_VERIFIED") + (
            "CREDENTIAL_VERIFICATION_BOUNDARY_ABSENT",
        ),
    ):
        _reject(blocker_codes=value)
    for value in (REASONS[:-1], REASONS + ("UNKNOWN_REASON",), REASONS + (REASONS[0],)):
        _reject(reason_codes=value)


def test_constructor_rejects_tampering_unknown_fields_and_all_completion_or_authority_claims():
    for name, value in (
        ("locked_repository_baseline", "0" * 40),
        ("locked_phase09_baseline", "0" * 40),
        ("reconciliation_state", "READY"),
        ("predecessor_status", "AUTHORIZED"),
        ("predecessor_successor_reconciliation_reference", "OTHER"),
        ("predecessor_successor_reconciliation_identity", "0" * 64),
        ("executable_input_creation_boundary_reference", "OTHER"),
        ("executable_input_creation_boundary_identity", "0" * 64),
        ("executable_input_creation_descriptor_defined", False),
        ("pricing_revalidation_boundary_identity", "0" * 64),
        ("credential_verification_boundary_identity", "0" * 64),
        ("input_run_manifest_readiness_identity", "0" * 64),
        ("candidate_input_set_identity", "0" * 64),
        ("proposed_manifest_identity", "0" * 64),
        ("current_runtime_integrity_identity", "0" * 64),
        ("reservation_bound_identity", "0" * 64),
        ("candidate_input_metadata_defined", False),
        ("proposed_manifest_defined", False),
        ("launch_readiness", "READY"),
        ("production_effect", "SENT"),
        ("zero_production_proof", "NOT_PROVEN"),
        ("evidence_id", "0" * 64),
    ):
        _reject(**{name: value})
    for name in (
        "predecessor_successor_reconciliation_mutated",
        "predecessor_successor_reconciliation_transitioned",
        "predecessor_successor_reconciliation_current_authority",
        "executable_input_creation_execution_authorized",
        "executable_input_creation_started",
        "executable_input_creation_result_present",
        "executable_input_creation_completed",
        "source_content_access_observed",
        "filesystem_write_observed",
        "executable_content_generated",
        "executable_content_serialized",
        "executable_input_content_present",
        "content_integrity_verified",
        "proposed_manifest_modified",
        "proposed_manifest_activated",
        "pricing_revalidation_execution_authorized",
        "pricing_revalidation_started",
        "pricing_revalidation_result_present",
        "pricing_revalidation_completed",
        "fresh_provider_pricing_observed",
        "credential_verification_execution_authorized",
        "credential_verification_started",
        "credential_verification_result_present",
        "credential_verification_completed",
        "credential_configuration_verified",
        "credential_or_secret_access_observed",
        "environment_access_observed",
        "filesystem_access_observed",
        "network_access_observed",
        "provider_authentication_probe_performed",
        "pre_call_reservation_created",
        "ledger_entry_created",
        "provider_request_created",
        "runtime_invocation_authorized",
        "provider_call_authorized",
        "provider_transmission_authorized",
        "run_size_authorized",
        "manifest_activation_authorized",
        "launch_authorized",
        "production_authorized",
    ):
        _reject(**{name: True})
    _reject(unknown_field="reject")


def test_canonical_identity_converges_and_detached_material_mutation_diverges_without_operational_dependencies():
    first = _evidence(
        blocker_codes=tuple(reversed(BLOCKERS)),
        reason_codes=tuple(reversed(REASONS)),
    )
    second = _evidence()
    payload = {
        name: getattr(first, name)
        for name in first.__dataclass_fields__
        if name != "evidence_id"
    }
    variant = dict(payload)
    variant["executable_input_content_present"] = True
    assert first.identity == second.identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\xc3\xa9"}'
    module = ast.parse(Path(FUTURE_PATH).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "datetime", "time", "dotenv", "keyring", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules and not names & forbidden_names


def test_public_accessor_type_and_identity_are_exact_and_stable():
    first = get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1()
    second = get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1()
    assert type(first) is ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1
    assert first.identity == second.identity == _evidence().identity
