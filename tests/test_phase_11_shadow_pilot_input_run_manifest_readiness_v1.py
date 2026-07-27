"""RED contract for static Phase 11 pilot input/manifest readiness.

The fixtures below are deterministic metadata only.  They do not select live
input, create executable content, create a reservation, or activate a run.
"""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import (
    get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1,
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
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)
from engine.phase_11_shadow_pilot_input_run_manifest_readiness_v1 import (
    ShadowPhase11PilotInputItemV1,
    ShadowPhase11PilotInputReadinessStateV1,
    ShadowPhase11PilotInputRunManifestReadinessEvidenceV1,
    ShadowPhase11PilotInputRunManifestReadinessValidationError,
    ShadowPhase11PilotManifestReadinessStateV1,
    ShadowPhase11PilotRunManifestV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1,
    sha256_hex,
)


LOCKED_REPOSITORY_BASELINE = "9ba0927b5ad58e29a8dd9fd8c3416a871d5ed9db"
LOCKED_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
GATE_IDENTITY = "29a07dc2cb644aeb4dbdc9dc00e4da79b5fa3d1486e98dabdcadb1e40140debb"
RUNTIME_REFERENCE = "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
RUNTIME_IDENTITY = "45d1446eb173d399f748b3b11e616d51391947762d3b36848cbd4f3d5b3228ab"
PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
PRICING_IDENTITY = "2ffbb1d04538bbf481d287b9629757fcde17a3d59779a1cef367e1752d673014"
RESERVATION_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
RESERVATION_IDENTITY = "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4"
FUTURE_PATH = "engine/phase_11_shadow_pilot_input_run_manifest_readiness_v1.py"

CANDIDATE_COUNT = 20
MAXIMUM_INPUT_TOKENS = 16000
MAXIMUM_OUTPUT_TOKENS = 2000
MAXIMUM_ATTEMPTS = 1
WORST_CASE_ITEM_MICRO_USD = Decimal("216700")
HARD_CAP_MICRO_USD = Decimal("5000000")
SAFETY_RESERVE_MICRO_USD = Decimal("500000")
SPENDABLE_CAP_MICRO_USD = Decimal("4500000")
TOTAL_WORST_CASE_MICRO_USD = Decimal("4334000")
ROLES = (
    ShadowPhase11PilotProviderRoleV1.PRIMARY,
    ShadowPhase11PilotProviderRoleV1.L1,
    ShadowPhase11PilotProviderRoleV1.L2,
)


def _item(
    ordinal: int = 1,
    **overrides: object,
) -> ShadowPhase11PilotInputItemV1:
    fields = {
        "schema_version": "phase11-shadow-pilot-input-item-v1",
        "item_id": None,
        "item_reference": f"PHASE11_PILOT_READINESS_ITEM_{ordinal:03d}",
        "ordinal": ordinal,
        "intended_route": ShadowPhase11PilotRouteV1.L1_TO_L2,
        "required_provider_roles": ROLES,
        "maximum_input_tokens": MAXIMUM_INPUT_TOKENS,
        "maximum_output_tokens": MAXIMUM_OUTPUT_TOKENS,
        "maximum_attempts": MAXIMUM_ATTEMPTS,
        "conservative_maximum_micro_usd": WORST_CASE_ITEM_MICRO_USD,
        "input_content_present": False,
        "credential_reference_present": False,
        "credential_material_present": False,
        "provider_request_created": False,
        "provider_transmission_authorized": False,
        "reservation_bound": False,
        "reason_codes": ("CANDIDATE_METADATA_ONLY",),
    }
    fields.update(overrides)
    return ShadowPhase11PilotInputItemV1(**fields)


def _items() -> tuple[ShadowPhase11PilotInputItemV1, ...]:
    return tuple(_item(ordinal) for ordinal in range(1, CANDIDATE_COUNT + 1))


def _input_set_identity(items: tuple[ShadowPhase11PilotInputItemV1, ...]) -> str:
    ordered = tuple(sorted(items, key=lambda item: (item.ordinal, item.item_reference)))
    return sha256_hex(
        canonical_json_bytes(
            {"candidate_item_identities": tuple(item.identity for item in ordered)}
        )
    )


def _manifest(
    items: tuple[ShadowPhase11PilotInputItemV1, ...] | None = None,
    **overrides: object,
) -> ShadowPhase11PilotRunManifestV1:
    candidate_items = _items() if items is None else items
    fields = {
        "schema_version": "phase11-shadow-pilot-run-manifest-v1",
        "manifest_id": None,
        "manifest_reference": "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001",
        "manifest_readiness_state": (
            ShadowPhase11PilotManifestReadinessStateV1
            .PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED
        ),
        "candidate_input_set_identity": _input_set_identity(candidate_items),
        "candidate_item_identities": tuple(item.identity for item in candidate_items),
        "candidate_count": CANDIDATE_COUNT,
        "maximum_worst_case_cost_per_item_micro_usd": WORST_CASE_ITEM_MICRO_USD,
        "total_worst_case_maximum_micro_usd": TOTAL_WORST_CASE_MICRO_USD,
        "hard_cap_micro_usd": HARD_CAP_MICRO_USD,
        "safety_reserve_micro_usd": SAFETY_RESERVE_MICRO_USD,
        "maximum_spendable_micro_usd": SPENDABLE_CAP_MICRO_USD,
        "reservation_required_before_transmission": True,
        "launch_time_pricing_revalidation_required": True,
        "pricing_revalidation_completed": False,
        "reservation_created": False,
        "ledger_entry_created": False,
        "provider_requests_created": False,
        "manifest_activated": False,
        "runtime_invocation_authorized": False,
        "provider_transmission_authorized": False,
        "launch_authorized": False,
        "production_authorized": False,
        "reason_codes": ("PROPOSED_MANIFEST_METADATA_ONLY",),
    }
    fields.update(overrides)
    return ShadowPhase11PilotRunManifestV1(**fields)


def _evidence(**overrides: object) -> ShadowPhase11PilotInputRunManifestReadinessEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    candidate_items = _items()
    manifest = _manifest(candidate_items)
    fields = {
        "schema_version": "phase11-shadow-pilot-input-run-manifest-readiness-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": LOCKED_REPOSITORY_BASELINE,
        "locked_phase09_baseline": LOCKED_PHASE09_BASELINE,
        "credential_safe_gate_reference": gate.evidence_reference,
        "credential_safe_gate_identity": gate.identity,
        "current_runtime_integrity_reference": runtime.evidence_reference,
        "current_runtime_integrity_identity": runtime.identity,
        "pricing_evidence_reference": pricing.evidence_reference,
        "pricing_evidence_identity": pricing.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "input_readiness_state": (
            ShadowPhase11PilotInputReadinessStateV1
            .CANDIDATE_INPUT_DEFINED_NOT_AUTHORIZED
        ),
        "manifest_readiness_state": manifest.manifest_readiness_state,
        "candidate_items": candidate_items,
        "proposed_manifest": manifest,
        "candidate_input_defined": True,
        "executable_input_content_present": False,
        "run_manifest_defined": True,
        "run_manifest_activated": False,
        "credential_configuration_verified": False,
        "pricing_revalidation_completed": False,
        "pre_call_reservation_created": False,
        "ledger_entry_created": False,
        "provider_request_created": False,
        "provider_call_authorized": False,
        "provider_transmission_authorized": False,
        "runtime_invocation_authorized": False,
        "run_size_authorized": False,
        "launch_authorized": False,
        "production_authorized": False,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
        "reason_codes": (
            "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
            "EXECUTABLE_INPUT_CONTENT_ABSENT",
            "LAUNCH_NOT_AUTHORIZED",
            "PRE_CALL_RESERVATION_NOT_CREATED",
            "PRICING_REVALIDATION_INCOMPLETE",
            "PROVIDER_REQUEST_NOT_CREATED",
            "RUN_MANIFEST_NOT_ACTIVATED",
        ),
    }
    fields.update(overrides)
    return ShadowPhase11PilotInputRunManifestReadinessEvidenceV1(**fields)


def _reject_item(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PilotInputRunManifestReadinessValidationError):
        _item(**overrides)


def _reject_manifest(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PilotInputRunManifestReadinessValidationError):
        _manifest(**overrides)


def _reject_evidence(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11PilotInputRunManifestReadinessValidationError):
        _evidence(**overrides)


def test_closed_readiness_states_are_exact():
    assert tuple(ShadowPhase11PilotInputReadinessStateV1) == (
        ShadowPhase11PilotInputReadinessStateV1.CANDIDATE_INPUT_DEFINED_NOT_AUTHORIZED,
    )
    assert tuple(ShadowPhase11PilotManifestReadinessStateV1) == (
        ShadowPhase11PilotManifestReadinessStateV1.PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED,
    )


def test_candidate_items_are_metadata_only_canonical_and_worst_case_bounded():
    items = _items()
    assert len(items) == CANDIDATE_COUNT == 20
    assert tuple(item.ordinal for item in items) == tuple(range(1, 21))
    assert tuple(item.intended_route for item in items) == (ShadowPhase11PilotRouteV1.L1_TO_L2,) * 20
    assert all(item.required_provider_roles == ROLES for item in items)
    assert all(item.maximum_input_tokens == MAXIMUM_INPUT_TOKENS for item in items)
    assert all(item.maximum_output_tokens == MAXIMUM_OUTPUT_TOKENS for item in items)
    assert all(item.maximum_attempts == 1 for item in items)
    assert all(item.conservative_maximum_micro_usd == WORST_CASE_ITEM_MICRO_USD for item in items)
    assert all(item.input_content_present is False for item in items)
    assert all(item.credential_reference_present is False for item in items)
    assert all(item.credential_material_present is False for item in items)
    assert all(item.provider_request_created is False for item in items)
    assert all(item.provider_transmission_authorized is False for item in items)
    assert all(item.reservation_bound is False for item in items)
    assert CANDIDATE_COUNT * WORST_CASE_ITEM_MICRO_USD == TOTAL_WORST_CASE_MICRO_USD <= SPENDABLE_CAP_MICRO_USD


def test_candidate_item_rejects_route_role_tokens_attempts_content_and_identity_tampering():
    for name, value in (
        ("item_reference", "bad reference"),
        ("ordinal", 0),
        ("intended_route", ShadowPhase11PilotRouteV1.L0),
        ("required_provider_roles", (ShadowPhase11PilotProviderRoleV1.PRIMARY,)),
        ("maximum_input_tokens", 15999),
        ("maximum_output_tokens", 1999),
        ("maximum_attempts", 2),
        ("conservative_maximum_micro_usd", Decimal("216699")),
        ("input_content_present", True),
        ("credential_reference_present", True),
        ("credential_material_present", True),
        ("provider_request_created", True),
        ("provider_transmission_authorized", True),
        ("reservation_bound", True),
        ("item_id", "0" * 64),
    ):
        _reject_item(**{name: value})
    _reject_item(unknown_field="reject")


def test_proposed_manifest_is_non_activated_and_binds_exact_capacity():
    items = _items()
    manifest = _manifest(items)
    assert manifest.candidate_input_set_identity == _input_set_identity(items)
    assert manifest.candidate_item_identities == tuple(item.identity for item in items)
    assert manifest.candidate_count == 20
    assert manifest.total_worst_case_maximum_micro_usd == Decimal("4334000")
    assert manifest.hard_cap_micro_usd == Decimal("5000000")
    assert manifest.safety_reserve_micro_usd == Decimal("500000")
    assert manifest.maximum_spendable_micro_usd == Decimal("4500000")
    assert manifest.reservation_required_before_transmission is True
    assert manifest.launch_time_pricing_revalidation_required is True
    assert manifest.manifest_activated is False
    assert manifest.runtime_invocation_authorized is False
    assert manifest.provider_transmission_authorized is False


def test_manifest_rejects_count_bound_state_activation_and_authority_tampering():
    items = _items()
    for name, value in (
        ("manifest_readiness_state", "ACTIVATED"),
        ("candidate_input_set_identity", "0" * 64),
        ("candidate_item_identities", tuple(item.identity for item in items[:-1])),
        ("candidate_count", 0),
        ("candidate_count", 21),
        ("maximum_worst_case_cost_per_item_micro_usd", Decimal("1")),
        ("total_worst_case_maximum_micro_usd", Decimal("4500001")),
        ("hard_cap_micro_usd", Decimal("1")),
        ("safety_reserve_micro_usd", Decimal("1")),
        ("maximum_spendable_micro_usd", Decimal("1")),
        ("reservation_required_before_transmission", False),
        ("launch_time_pricing_revalidation_required", False),
        ("pricing_revalidation_completed", True),
        ("reservation_created", True),
        ("ledger_entry_created", True),
        ("provider_requests_created", True),
        ("manifest_activated", True),
        ("runtime_invocation_authorized", True),
        ("provider_transmission_authorized", True),
        ("launch_authorized", True),
        ("production_authorized", True),
        ("manifest_id", "0" * 64),
    ):
        _reject_manifest(**{name: value})
    _reject_manifest(unknown_field="reject")


def test_manifest_and_evidence_converge_when_candidate_order_is_reversed():
    items = _items()
    manifest = _manifest(items)
    reordered = _manifest(tuple(reversed(items)))
    assert manifest.identity == reordered.identity
    first = _evidence(candidate_items=items, proposed_manifest=manifest, reason_codes=("A_REASON", "Z_REASON"))
    second = _evidence(candidate_items=tuple(reversed(items)), proposed_manifest=reordered, reason_codes=("Z_REASON", "A_REASON"))
    variant = _evidence(reason_codes=("MATERIAL_VARIANT",))
    assert first.identity == second.identity
    assert first.identity != variant.identity


def test_evidence_links_exact_upstream_contracts_and_preserves_all_blockers():
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    evidence = _evidence()
    assert evidence.credential_safe_gate_reference == gate.evidence_reference == GATE_REFERENCE
    assert evidence.credential_safe_gate_identity == gate.identity == GATE_IDENTITY
    assert evidence.current_runtime_integrity_reference == runtime.evidence_reference == RUNTIME_REFERENCE
    assert evidence.current_runtime_integrity_identity == runtime.identity == RUNTIME_IDENTITY
    assert evidence.pricing_evidence_reference == pricing.evidence_reference == PRICING_REFERENCE
    assert evidence.pricing_evidence_identity == pricing.identity == PRICING_IDENTITY
    assert evidence.reservation_bound_reference == reservation.evidence_reference == RESERVATION_REFERENCE
    assert evidence.reservation_bound_identity == reservation.identity == RESERVATION_IDENTITY
    assert evidence.candidate_input_defined is True and evidence.executable_input_content_present is False
    assert evidence.run_manifest_defined is True and evidence.run_manifest_activated is False
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.provider_call_authorized is False and evidence.launch_authorized is False


def test_evidence_rejects_linkage_flags_items_manifest_authority_and_identity_tampering():
    items = _items()
    for name, value in (
        ("evidence_reference", "OTHER"),
        ("locked_repository_baseline", "0" * 40),
        ("locked_phase09_baseline", "0" * 40),
        ("credential_safe_gate_reference", "OTHER"),
        ("credential_safe_gate_identity", "0" * 64),
        ("current_runtime_integrity_reference", "OTHER"),
        ("current_runtime_integrity_identity", "0" * 64),
        ("pricing_evidence_reference", "OTHER"),
        ("pricing_evidence_identity", "0" * 64),
        ("reservation_bound_reference", "OTHER"),
        ("reservation_bound_identity", "0" * 64),
        ("input_readiness_state", "SELECTED"),
        ("manifest_readiness_state", "ACTIVATED"),
        ("candidate_items", items[:-1]),
        ("candidate_items", items[:-1] + (items[0],)),
        ("candidate_items", items[:-1] + (_item(21),)),
        ("candidate_input_defined", False),
        ("executable_input_content_present", True),
        ("run_manifest_defined", False),
        ("run_manifest_activated", True),
        ("credential_configuration_verified", True),
        ("pricing_revalidation_completed", True),
        ("pre_call_reservation_created", True),
        ("ledger_entry_created", True),
        ("provider_request_created", True),
        ("runtime_invocation_authorized", True),
        ("run_size_authorized", True),
        ("launch_readiness", "READY_FOR_LAUNCH"),
        ("production_effect", "SENT"),
        ("zero_production_effect_proof", "UNPROVEN"),
        ("evidence_id", "0" * 64),
    ):
        _reject_evidence(**{name: value})
    for name in (
        "provider_call_authorized",
        "provider_transmission_authorized",
        "launch_authorized",
        "production_authorized",
    ):
        _reject_evidence(**{name: True})
    _reject_evidence(unknown_field="reject")


def test_canonical_helpers_accessor_stability_and_future_static_boundary():
    evidence = get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    assert type(evidence) is ShadowPhase11PilotInputRunManifestReadinessEvidenceV1
    assert evidence.identity == get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1().identity == _evidence().identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    assert sha256_hex(b"pilot-input-manifest") == "65c1326578ecde5f42f6dde5f84bf4792809f95754fe2a85fbcba02bbb9906c1"
    module = ast.parse(Path(FUTURE_PATH).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "keyring", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "material_for_adapter", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1", "reserve_call", "commit_usage", "sleep", "wait", "float"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules and not names & forbidden_names
