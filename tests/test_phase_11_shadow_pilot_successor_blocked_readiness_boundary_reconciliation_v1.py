"""RED contract for immutable Phase 11 successor boundary reconciliation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_blocked_readiness_reconciliation_v1 import (
    get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1,
)
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
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_freshness_policy_v1 import (
    get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1,
)
from engine.phase_11_shadow_pilot_pricing_revalidation_boundary_v1 import (
    get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1,
)
from engine.phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_v1 import (
    ShadowPhase11SuccessorBlockedReadinessBoundaryReconciliationEvidenceV1,
    ShadowPhase11SuccessorBoundaryPredecessorStatusV1,
    ShadowPhase11SuccessorBoundaryReconciliationStateV1,
    ShadowPhase11SuccessorBlockedReadinessBoundaryReconciliationValidationError,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1,
    sha256_hex,
)


BASELINE = "df062d6192acd4f750c4f9757f2694fbde93e72a"
PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_SUCCESSOR_BLOCKED_READINESS_BOUNDARY_RECONCILIATION_001"
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
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "CREDENTIAL_VERIFICATION_BOUNDARY_RECOGNIZED",
    "NO_OPERATIONAL_AUTHORITY",
    "PREDECESSOR_RECONCILIATION_PRESERVED",
    "PRICING_REVALIDATION_BOUNDARY_RECOGNIZED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "SUCCESSOR_BOUNDARIES_RECONCILED_BLOCKED",
)))
FUTURE_PATH = "engine/phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_v1.py"


def _evidence(**overrides: object) -> ShadowPhase11SuccessorBlockedReadinessBoundaryReconciliationEvidenceV1:
    predecessor = get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    credential = get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1()
    policy = get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1()
    readiness = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-successor-blocked-readiness-boundary-reconciliation-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "reconciliation_state": ShadowPhase11SuccessorBoundaryReconciliationStateV1.SUCCESSOR_BOUNDARIES_RECONCILED_READINESS_BLOCKED,
        "predecessor_status": ShadowPhase11SuccessorBoundaryPredecessorStatusV1.PREDECESSOR_RECONCILIATION_PRESERVED,
        "predecessor_reconciliation_reference": predecessor.evidence_reference,
        "predecessor_reconciliation_identity": predecessor.identity,
        "predecessor_reconciliation_mutated": False,
        "predecessor_reconciliation_transitioned": False,
        "predecessor_reconciliation_current_authority": False,
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
        "pricing_freshness_policy_reference": policy.evidence_reference,
        "pricing_freshness_policy_identity": policy.identity,
        "input_run_manifest_readiness_reference": readiness.evidence_reference,
        "input_run_manifest_readiness_identity": readiness.identity,
        "current_runtime_integrity_reference": runtime.evidence_reference,
        "current_runtime_integrity_identity": runtime.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "candidate_input_metadata_defined": True,
        "proposed_manifest_defined": True,
        "executable_input_content_present": False,
        "proposed_manifest_activated": False,
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
    return ShadowPhase11SuccessorBlockedReadinessBoundaryReconciliationEvidenceV1(**fields)


def _reject(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11SuccessorBlockedReadinessBoundaryReconciliationValidationError):
        _evidence(**overrides)


def test_closed_reconciliation_and_predecessor_states_are_exact_and_evidence_is_closed():
    assert tuple(ShadowPhase11SuccessorBoundaryReconciliationStateV1) == (
        ShadowPhase11SuccessorBoundaryReconciliationStateV1.SUCCESSOR_BOUNDARIES_RECONCILED_READINESS_BLOCKED,
    )
    assert tuple(ShadowPhase11SuccessorBoundaryPredecessorStatusV1) == (
        ShadowPhase11SuccessorBoundaryPredecessorStatusV1.PREDECESSOR_RECONCILIATION_PRESERVED,
    )
    assert getattr(ShadowPhase11SuccessorBlockedReadinessBoundaryReconciliationEvidenceV1, "__slots__")
    assert "__dict__" not in ShadowPhase11SuccessorBlockedReadinessBoundaryReconciliationEvidenceV1.__slots__


def test_predecessor_is_exactly_linked_preserved_unmutated_untransitioned_and_non_authoritative():
    evidence = _evidence()
    assert evidence.predecessor_reconciliation_reference == "PHASE_11_PILOT_BLOCKED_READINESS_RECONCILIATION_001"
    assert evidence.predecessor_reconciliation_identity == "92e9773c94cf8263202976e9c6d6f9c62a7e66b8de59ada63992056a4e9a2bd0"
    assert evidence.predecessor_status is ShadowPhase11SuccessorBoundaryPredecessorStatusV1.PREDECESSOR_RECONCILIATION_PRESERVED
    assert not any(getattr(evidence, field) for field in (
        "predecessor_reconciliation_mutated",
        "predecessor_reconciliation_transitioned",
        "predecessor_reconciliation_current_authority",
    ))


def test_pricing_and_credential_boundaries_are_exactly_recognized_without_execution_results_or_completion():
    evidence = _evidence()
    assert (evidence.pricing_revalidation_boundary_reference, evidence.pricing_revalidation_boundary_identity) == (
        "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001",
        "fc34f6f222825f29669ce4f575314eabeb887135ef54bc3613836f4d46ccb0fc",
    )
    assert (evidence.credential_verification_boundary_reference, evidence.credential_verification_boundary_identity) == (
        "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_BOUNDARY_001",
        "91991bb1f7947eb43acca9983c53a686667f1ab58be21bd769224fec174a679c",
    )
    assert evidence.pricing_revalidation_descriptor_defined is True
    assert evidence.credential_verification_descriptor_defined is True
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
    ))


def test_current_readiness_lineage_is_exactly_linked_and_remains_non_executable_non_activated_and_blocked():
    evidence = _evidence()
    assert (evidence.pricing_freshness_policy_reference, evidence.pricing_freshness_policy_identity) == (
        "PHASE_11_PILOT_PRICING_FRESHNESS_POLICY_001",
        "2e63c1ee2b4912d9361a1b4793fbb1f866bdada4bbfd89a1691074d92757d603",
    )
    assert evidence.input_run_manifest_readiness_identity == "30ea2ab4f8c3aef604358f3688cf88b348cad6cc98ec887ce98502acabc4e944"
    assert evidence.current_runtime_integrity_identity == "45d1446eb173d399f748b3b11e616d51391947762d3b36848cbd4f3d5b3228ab"
    assert evidence.reservation_bound_identity == "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4"
    assert evidence.candidate_input_metadata_defined is True and evidence.proposed_manifest_defined is True
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE" and evidence.zero_production_proof == "PROVEN_NONE"
    assert not any(getattr(evidence, field) for field in (
        "executable_input_content_present", "proposed_manifest_activated",
        "pre_call_reservation_created", "ledger_entry_created", "provider_request_created",
        "runtime_invocation_authorized", "provider_call_authorized", "provider_transmission_authorized",
        "run_size_authorized", "manifest_activation_authorized", "launch_authorized", "production_authorized",
    ))


def test_exact_successor_blockers_and_reasons_canonicalize_and_reject_obsolete_or_authority_granting_values():
    evidence = _evidence(blocker_codes=tuple(reversed(BLOCKERS)), reason_codes=tuple(reversed(REASONS)))
    assert evidence.blocker_codes == BLOCKERS and evidence.reason_codes == REASONS
    for value in (
        BLOCKERS[:-1], BLOCKERS + ("UNKNOWN_BLOCKER",), BLOCKERS + (BLOCKERS[0],),
        tuple(code for code in BLOCKERS if code != "PRICING_REVALIDATION_INCOMPLETE") + ("PRICING_REVALIDATION_BOUNDARY_ABSENT",),
        tuple(code for code in BLOCKERS if code != "CREDENTIAL_CONFIGURATION_NOT_VERIFIED") + ("CREDENTIAL_VERIFICATION_BOUNDARY_ABSENT",),
        tuple(code for code in BLOCKERS if code != "EXECUTABLE_INPUT_CONTENT_ABSENT") + ("CANDIDATE_INPUT_METADATA_ABSENT",),
        tuple(code for code in BLOCKERS if code != "PROPOSED_MANIFEST_NOT_ACTIVATED") + ("PROPOSED_MANIFEST_DEFINITION_ABSENT",),
    ):
        _reject(blocker_codes=value)
    for value in (REASONS[:-1], REASONS + ("UNKNOWN_REASON",), REASONS + (REASONS[0],)):
        _reject(reason_codes=value)


def test_constructor_rejects_tampering_unknown_fields_and_all_completion_or_operational_authority_claims():
    for name, value in (
        ("locked_repository_baseline", "0" * 40), ("locked_phase09_baseline", "0" * 40),
        ("reconciliation_state", "READY"), ("predecessor_status", "AUTHORIZED"),
        ("predecessor_reconciliation_reference", "OTHER"), ("predecessor_reconciliation_identity", "0" * 64),
        ("predecessor_reconciliation_mutated", True), ("predecessor_reconciliation_transitioned", True), ("predecessor_reconciliation_current_authority", True),
        ("pricing_revalidation_boundary_reference", "OTHER"), ("pricing_revalidation_boundary_identity", "0" * 64), ("pricing_revalidation_descriptor_defined", False),
        ("credential_verification_boundary_reference", "OTHER"), ("credential_verification_boundary_identity", "0" * 64), ("credential_verification_descriptor_defined", False),
        ("pricing_freshness_policy_identity", "0" * 64), ("input_run_manifest_readiness_identity", "0" * 64), ("current_runtime_integrity_identity", "0" * 64), ("reservation_bound_identity", "0" * 64),
        ("candidate_input_metadata_defined", False), ("proposed_manifest_defined", False),
        ("launch_readiness", "READY"), ("production_effect", "SENT"), ("zero_production_proof", "NOT_PROVEN"), ("evidence_id", "0" * 64),
    ):
        _reject(**{name: value})
    for name in (
        "pricing_revalidation_execution_authorized", "pricing_revalidation_started", "pricing_revalidation_result_present", "pricing_revalidation_completed", "fresh_provider_pricing_observed",
        "credential_verification_execution_authorized", "credential_verification_started", "credential_verification_result_present", "credential_verification_completed", "credential_configuration_verified", "credential_or_secret_access_observed", "environment_access_observed", "filesystem_access_observed", "network_access_observed", "provider_authentication_probe_performed",
        "executable_input_content_present", "proposed_manifest_activated", "pre_call_reservation_created", "ledger_entry_created", "provider_request_created", "runtime_invocation_authorized", "provider_call_authorized", "provider_transmission_authorized", "run_size_authorized", "manifest_activation_authorized", "launch_authorized", "production_authorized",
    ):
        _reject(**{name: True})
    _reject(unknown_field="reject")


def test_canonical_identity_converges_and_detached_material_mutation_diverges_without_operational_dependencies():
    first = _evidence(blocker_codes=tuple(reversed(BLOCKERS)), reason_codes=tuple(reversed(REASONS)))
    second = _evidence()
    payload = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "evidence_id"}
    variant = dict(payload)
    variant["pricing_revalidation_completed"] = True
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
    first = get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1()
    second = get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1()
    assert type(first) is ShadowPhase11SuccessorBlockedReadinessBoundaryReconciliationEvidenceV1
    assert first.identity == second.identity == _evidence().identity
