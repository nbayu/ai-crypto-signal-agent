"""RED contract for Phase 11 successor blocked-readiness reconciliation.

The future artifact is static lineage evidence only.  It must recognize later
readiness metadata without mutating the historical blocked gate or granting
any execution authority.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    ShadowPhase11CredentialSafeLaunchGateStateV1,
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import (
    get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1,
)
from engine.phase_11_shadow_pilot_input_run_manifest_readiness_v1 import (
    ShadowPhase11PilotInputReadinessStateV1,
    ShadowPhase11PilotManifestReadinessStateV1,
    get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotPricingRevalidationStatusV1,
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    ShadowPhase11PreCallReservationStateV1,
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)
from engine.phase_11_shadow_pilot_blocked_readiness_reconciliation_v1 import (
    ShadowPhase11BlockedReadinessPredecessorStatusV1,
    ShadowPhase11BlockedReadinessReconciliationEvidenceV1,
    ShadowPhase11BlockedReadinessReconciliationStateV1,
    ShadowPhase11BlockedReadinessReconciliationValidationError,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1,
    sha256_hex,
)


LOCKED_REPOSITORY_BASELINE = "b4ddee91d1eae0ffe5ce4597aace61449a154491"
LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_BLOCKED_READINESS_RECONCILIATION_001"
GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
GATE_IDENTITY = "77b7bbb6782a4710b04abd16547ba5fd94e8311d09cad0cd0187fc7b8313c06b"
RUNTIME_REFERENCE = "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
RUNTIME_IDENTITY = "72342b2390f32463f6d5104f47d3dc29ff5067349daec61a4fe5565de725b51e"
READINESS_REFERENCE = "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
READINESS_IDENTITY = "9dffc3370346370284fe5a630a32e78be6def065428060ce70eea8cddf0fd228"
INPUT_SET_IDENTITY = "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
MANIFEST_IDENTITY = "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
PRICING_IDENTITY = "9b986028159efa107da3d2625422ad937d19a65631e5ea95926e006f28329d31"
RESERVATION_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
RESERVATION_IDENTITY = "424a3a332c31a3143ee3a4b6ab8b37b7ec440ea0fcf3c6a01566e451bb11cb70"
FUTURE_PATH = "engine/phase_11_shadow_pilot_blocked_readiness_reconciliation_v1.py"

HISTORICAL_GATE_BLOCKERS = (
    "AUTHENTICATION_TERMINAL_CLASSIFICATION_NOT_VERIFIED",
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "PILOT_INPUT_ABSENT",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "RUN_MANIFEST_ABSENT",
    "RUNTIME_NO_RETRY_ENFORCEMENT_NOT_VERIFIED",
)
SUCCESSOR_BLOCKERS = (
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "EXECUTABLE_INPUT_CONTENT_ABSENT",
    "LAUNCH_NOT_AUTHORIZED",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "PROPOSED_MANIFEST_NOT_ACTIVATED",
    "PROVIDER_REQUEST_NOT_CREATED",
    "RUN_SIZE_NOT_AUTHORIZED",
    "RUNTIME_INVOCATION_NOT_AUTHORIZED",
)


def _evidence(**overrides: object) -> ShadowPhase11BlockedReadinessReconciliationEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    readiness = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-blocked-readiness-reconciliation-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": LOCKED_REPOSITORY_BASELINE,
        "locked_phase09_baseline": LOCKED_PHASE09_BASELINE,
        "historical_gate_reference": gate.evidence_reference,
        "historical_gate_identity": gate.identity,
        "historical_gate_state": gate.gate_state,
        "historical_gate_blocker_codes": gate.blocker_codes,
        "historical_pilot_input_present": gate.pilot_input_present,
        "historical_run_manifest_present": gate.run_manifest_present,
        "predecessor_status": (
            ShadowPhase11BlockedReadinessPredecessorStatusV1
            .HISTORICAL_BLOCKED_GATE_PREDECESSOR_ONLY
        ),
        "historical_gate_mutated": False,
        "historical_gate_transitioned": False,
        "historical_gate_current_readiness_authority": False,
        "current_runtime_integrity_reference": runtime.evidence_reference,
        "current_runtime_integrity_identity": runtime.identity,
        "readiness_evidence_reference": readiness.evidence_reference,
        "readiness_evidence_identity": readiness.identity,
        "candidate_input_set_identity": (
            readiness.proposed_manifest.candidate_input_set_identity
        ),
        "proposed_manifest_identity": readiness.proposed_manifest.identity,
        "input_readiness_state": readiness.input_readiness_state,
        "manifest_readiness_state": readiness.manifest_readiness_state,
        "successor_current_runtime_integrity_recognized": True,
        "successor_candidate_input_metadata_defined": readiness.candidate_input_defined,
        "successor_proposed_manifest_defined": readiness.run_manifest_defined,
        "executable_input_content_present": readiness.executable_input_content_present,
        "proposed_manifest_activated": readiness.run_manifest_activated,
        "credential_configuration_verified": False,
        "pricing_evidence_reference": pricing.evidence_reference,
        "pricing_evidence_identity": pricing.identity,
        "pricing_revalidation_required": True,
        "pricing_revalidation_status": pricing.pricing_revalidation_status,
        "pricing_revalidation_completed": False,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "pre_call_reservation_required": True,
        "pre_call_reservation_state": reservation.reservation_state,
        "pre_call_reservation_created": False,
        "ledger_entry_created": False,
        "provider_request_created": False,
        "runtime_invocation_authorized": False,
        "provider_call_authorized": False,
        "provider_transmission_authorized": False,
        "run_size_authorized": False,
        "launch_authorized": False,
        "production_authorized": False,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "successor_blocker_codes": SUCCESSOR_BLOCKERS,
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
        "reason_codes": ("SUCCESSOR_READINESS_RECONCILED_BLOCKED",),
    }
    fields.update(overrides)
    return ShadowPhase11BlockedReadinessReconciliationEvidenceV1(**fields)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11BlockedReadinessReconciliationValidationError):
        _evidence(**overrides)


def test_closed_reconciliation_and_predecessor_enums_are_exact():
    assert tuple(ShadowPhase11BlockedReadinessReconciliationStateV1) == (
        ShadowPhase11BlockedReadinessReconciliationStateV1
        .RECONCILED_SUCCESSOR_READINESS_BLOCKED,
    )
    assert tuple(ShadowPhase11BlockedReadinessPredecessorStatusV1) == (
        ShadowPhase11BlockedReadinessPredecessorStatusV1
        .HISTORICAL_BLOCKED_GATE_PREDECESSOR_ONLY,
    )


def test_historical_gate_is_linked_preserved_and_predecessor_only():
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    evidence = _evidence()
    assert evidence.historical_gate_reference == gate.evidence_reference == GATE_REFERENCE
    assert evidence.historical_gate_identity == gate.identity == GATE_IDENTITY
    assert evidence.historical_gate_state is ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED
    assert evidence.historical_gate_blocker_codes == HISTORICAL_GATE_BLOCKERS
    assert evidence.historical_pilot_input_present is False
    assert evidence.historical_run_manifest_present is False
    assert evidence.predecessor_status is ShadowPhase11BlockedReadinessPredecessorStatusV1.HISTORICAL_BLOCKED_GATE_PREDECESSOR_ONLY
    assert evidence.historical_gate_mutated is False
    assert evidence.historical_gate_transitioned is False
    assert evidence.historical_gate_current_readiness_authority is False


def test_successor_artifacts_are_exactly_linked_and_recognized_without_activation():
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    readiness = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    evidence = _evidence()
    assert evidence.current_runtime_integrity_reference == runtime.evidence_reference == RUNTIME_REFERENCE
    assert evidence.current_runtime_integrity_identity == runtime.identity == RUNTIME_IDENTITY
    assert evidence.readiness_evidence_reference == readiness.evidence_reference == READINESS_REFERENCE
    assert evidence.readiness_evidence_identity == readiness.identity == READINESS_IDENTITY
    assert evidence.candidate_input_set_identity == INPUT_SET_IDENTITY
    assert evidence.proposed_manifest_identity == MANIFEST_IDENTITY
    assert evidence.input_readiness_state is ShadowPhase11PilotInputReadinessStateV1.CANDIDATE_INPUT_DEFINED_NOT_AUTHORIZED
    assert evidence.manifest_readiness_state is ShadowPhase11PilotManifestReadinessStateV1.PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED
    assert evidence.successor_current_runtime_integrity_recognized is True
    assert evidence.successor_candidate_input_metadata_defined is True
    assert evidence.successor_proposed_manifest_defined is True
    assert evidence.executable_input_content_present is False
    assert evidence.proposed_manifest_activated is False


def test_pricing_reservation_and_all_authorities_remain_blocked():
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    evidence = _evidence()
    assert evidence.pricing_evidence_reference == pricing.evidence_reference == PRICING_REFERENCE
    assert evidence.pricing_evidence_identity == pricing.identity == PRICING_IDENTITY
    assert evidence.pricing_revalidation_required is True
    assert evidence.pricing_revalidation_status is ShadowPhase11PilotPricingRevalidationStatusV1.REQUIRED_NOT_COMPLETED
    assert evidence.pricing_revalidation_completed is False
    assert evidence.reservation_bound_reference == reservation.evidence_reference == RESERVATION_REFERENCE
    assert evidence.reservation_bound_identity == reservation.identity == RESERVATION_IDENTITY
    assert evidence.pre_call_reservation_required is True
    assert evidence.pre_call_reservation_state is ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED
    assert evidence.pre_call_reservation_created is False
    assert evidence.ledger_entry_created is False
    assert evidence.provider_request_created is False
    assert not any((
        evidence.runtime_invocation_authorized,
        evidence.provider_call_authorized,
        evidence.provider_transmission_authorized,
        evidence.run_size_authorized,
        evidence.launch_authorized,
        evidence.production_authorized,
    ))
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE"
    assert evidence.zero_production_effect_proof == "PROVEN_NONE"


def test_successor_blockers_are_exact_and_obsolete_absence_blockers_are_rejected():
    evidence = _evidence(successor_blocker_codes=tuple(reversed(SUCCESSOR_BLOCKERS)))
    assert evidence.successor_blocker_codes == SUCCESSOR_BLOCKERS
    for blockers in (
        SUCCESSOR_BLOCKERS[:-1],
        SUCCESSOR_BLOCKERS + ("UNKNOWN_BLOCKER",),
        SUCCESSOR_BLOCKERS + (SUCCESSOR_BLOCKERS[0],),
        SUCCESSOR_BLOCKERS + ("CANDIDATE_INPUT_METADATA_ABSENT",),
        SUCCESSOR_BLOCKERS + ("PROPOSED_MANIFEST_DEFINITION_ABSENT",),
    ):
        _reject(successor_blocker_codes=blockers)


def test_constructor_rejects_lineage_state_authority_and_identity_tampering():
    for name, value in (
        ("evidence_reference", "OTHER"),
        ("locked_repository_baseline", "0" * 40),
        ("locked_phase09_baseline", "0" * 40),
        ("historical_gate_reference", "OTHER"),
        ("historical_gate_identity", "0" * 64),
        ("historical_gate_state", "READY"),
        ("historical_gate_blocker_codes", ("OTHER",)),
        ("historical_pilot_input_present", True),
        ("historical_run_manifest_present", True),
        ("predecessor_status", "CURRENT"),
        ("historical_gate_mutated", True),
        ("historical_gate_transitioned", True),
        ("historical_gate_current_readiness_authority", True),
        ("current_runtime_integrity_reference", "OTHER"),
        ("current_runtime_integrity_identity", "0" * 64),
        ("readiness_evidence_reference", "OTHER"),
        ("readiness_evidence_identity", "0" * 64),
        ("candidate_input_set_identity", "0" * 64),
        ("proposed_manifest_identity", "0" * 64),
        ("input_readiness_state", "SELECTED"),
        ("manifest_readiness_state", "ACTIVATED"),
        ("successor_current_runtime_integrity_recognized", False),
        ("successor_candidate_input_metadata_defined", False),
        ("successor_proposed_manifest_defined", False),
        ("executable_input_content_present", True),
        ("proposed_manifest_activated", True),
        ("credential_configuration_verified", True),
        ("pricing_evidence_reference", "OTHER"),
        ("pricing_evidence_identity", "0" * 64),
        ("pricing_revalidation_required", False),
        ("pricing_revalidation_status", "COMPLETED"),
        ("pricing_revalidation_completed", True),
        ("reservation_bound_reference", "OTHER"),
        ("reservation_bound_identity", "0" * 64),
        ("pre_call_reservation_required", False),
        ("pre_call_reservation_state", "RESERVED"),
        ("pre_call_reservation_created", True),
        ("ledger_entry_created", True),
        ("provider_request_created", True),
        ("runtime_invocation_authorized", True),
        ("provider_call_authorized", True),
        ("provider_transmission_authorized", True),
        ("run_size_authorized", True),
        ("launch_authorized", True),
        ("production_authorized", True),
        ("launch_readiness", "READY_FOR_LAUNCH"),
        ("production_effect", "SENT"),
        ("zero_production_effect_proof", "UNPROVEN"),
        ("evidence_id", "0" * 64),
    ):
        _reject(**{name: value})
    _reject(unknown_field="reject")


def test_canonical_identity_converges_diverges_and_future_module_is_static():
    first = _evidence(reason_codes=("A_REASON", "Z_REASON"))
    second = _evidence(reason_codes=("Z_REASON", "A_REASON"))
    variant = _evidence(reason_codes=("MATERIAL_VARIANT",))
    assert first.identity == second.identity
    assert first.identity != variant.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    assert sha256_hex(b"blocked-readiness-reconciliation") == "1fd01fe7f5f9a59d576652abf4d2d62a1ebc48189fc1c262b11f6288b2b94c0d"
    evidence = get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    assert type(evidence) is ShadowPhase11BlockedReadinessReconciliationEvidenceV1
    assert evidence.identity == get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1().identity == _evidence().identity
    module = ast.parse(Path(FUTURE_PATH).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "keyring", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "material_for_adapter", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1", "reserve_call", "commit_usage", "sleep", "wait", "float"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
