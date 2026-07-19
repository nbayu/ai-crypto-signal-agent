"""Immutable final Phase 11 successor-lineage reconciliation.

This module records static lineage and blocked-readiness facts only.  It
performs no assessment, content access, hashing, inspection, verification,
acceptance, manifest mutation, provider request, reservation, or runtime
operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)


_SCHEMA = "phase11-shadow-pilot-final-successor-lineage-reconciliation-v1"
_EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_FINAL_SUCCESSOR_LINEAGE_RECONCILIATION_001"
)
_REPOSITORY_BASELINE = "d1c583ec3284e6626bd499d23d7ba15a6dae1b60"
_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_LINKS = {
    "predecessor_successor_reconciliation_reference": (
        "PHASE_11_PILOT_SUCCESSOR_EXECUTABLE_INPUT_"
        "BOUNDARY_RECONCILIATION_001"
    ),
    "predecessor_successor_reconciliation_identity": (
        "709c842c8f56135220ff9e68f68bc0693e48ae2047d25f72d9929295f8f90215"
    ),
    "inspection_readiness_decision_reference": (
        "PHASE_11_PILOT_INTEGRITY_INSPECTION_READINESS_DECISION_001"
    ),
    "inspection_readiness_decision_identity": (
        "e376ac0f07a34ea4f23f5892175669aea8ef0938061995a162a4012ad06e58fb"
    ),
    "content_integrity_acceptance_boundary_reference": (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_"
        "ACCEPTANCE_BOUNDARY_001"
    ),
    "content_integrity_acceptance_boundary_identity": (
        "762a122c406ccd3b1bc9b2b3bb00d438f292fc530a5cef33024e759140dd136d"
    ),
    "content_readiness_decision_reference": (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_READINESS_DECISION_001"
    ),
    "content_readiness_decision_identity": (
        "dee8284ca5fdadf414b04c0e689fc10c777759e18bf7954f7efce1f851652822"
    ),
    "executable_input_creation_boundary_reference": (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001"
    ),
    "executable_input_creation_boundary_identity": (
        "f82aef927d6d0e4c0e021e597bd8fcba8ed9426e5c56ad551947ea1052f1c097"
    ),
    "pricing_revalidation_boundary_reference": (
        "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001"
    ),
    "pricing_revalidation_boundary_identity": (
        "33d25cac84df17608b41008b4c91160dd57354e059f1ae6f6a711db2a3beed59"
    ),
    "credential_verification_boundary_reference": (
        "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_"
        "VERIFICATION_BOUNDARY_001"
    ),
    "credential_verification_boundary_identity": (
        "f4b9ef09b6e17875a484d833525ccc3410049fc885f20c149f4df7445515fc91"
    ),
    "input_run_manifest_readiness_reference": (
        "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
    ),
    "input_run_manifest_readiness_identity": (
        "9dffc3370346370284fe5a630a32e78be6def065428060ce70eea8cddf0fd228"
    ),
    "candidate_input_set_identity": (
        "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
    ),
    "proposed_manifest_reference": "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001",
    "proposed_manifest_identity": (
        "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
    ),
    "current_runtime_integrity_reference": (
        "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
    ),
    "current_runtime_integrity_identity": (
        "72342b2390f32463f6d5104f47d3dc29ff5067349daec61a4fe5565de725b51e"
    ),
    "reservation_bound_reference": (
        "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
    ),
    "reservation_bound_identity": (
        "424a3a332c31a3143ee3a4b6ab8b37b7ec440ea0fcf3c6a01566e451bb11cb70"
    ),
}
_TRUE_FIELDS = (
    "inspection_readiness_decision_defined",
    "acceptance_boundary_defined",
    "executable_input_creation_descriptor_defined",
    "pricing_revalidation_descriptor_defined",
    "credential_verification_descriptor_defined",
    "candidate_input_metadata_defined",
    "proposed_manifest_defined",
)
_BLOCKERS = tuple(
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
_REASONS = tuple(
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


class ShadowPhase11FinalSuccessorLineageReconciliationValidationError(
    ValueError
):
    """Raised when final successor-lineage evidence is invalid."""


class ShadowPhase11FinalSuccessorLineageReconciliationStateV1(StrEnum):
    """The sole permitted final reconciliation state."""

    FINAL_STATIC_LINEAGE_RECONCILED_READINESS_BLOCKED = (
        "FINAL_STATIC_LINEAGE_RECONCILED_READINESS_BLOCKED"
    )


class ShadowPhase11FinalSuccessorLineagePredecessorStatusV1(StrEnum):
    """The sole permitted predecessor-lineage status."""

    PREDECESSOR_SUCCESSOR_LINEAGE_PRESERVED = (
        "PREDECESSOR_SUCCESSOR_LINEAGE_PRESERVED"
    )


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if type(value) in (tuple, list):
        return [_canonical_value(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShadowPhase11FinalSuccessorLineageReconciliationValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes."""

    try:
        return json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowPhase11FinalSuccessorLineageReconciliationValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11FinalSuccessorLineageReconciliationValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11FinalSuccessorLineageReconciliationValidationError(
            f"invalid {label}"
        )
    return value


def _codes(
    value: Any,
    expected: tuple[str, ...],
    label: str,
) -> tuple[str, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(expected)
        or any(type(item) is not str for item in value)
        or len(set(value)) != len(value)
        or set(value) != set(expected)
    ):
        raise ShadowPhase11FinalSuccessorLineageReconciliationValidationError(
            f"invalid {label}"
        )
    return expected


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11FinalSuccessorLineageReconciliationEvidenceV1:
    """Immutable final successor-lineage reconciliation evidence."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    reconciliation_state: ShadowPhase11FinalSuccessorLineageReconciliationStateV1
    predecessor_status: ShadowPhase11FinalSuccessorLineagePredecessorStatusV1
    predecessor_successor_reconciliation_reference: str
    predecessor_successor_reconciliation_identity: str
    predecessor_successor_reconciliation_mutated: bool
    predecessor_successor_reconciliation_transitioned: bool
    predecessor_successor_reconciliation_current_authority: bool
    inspection_readiness_decision_reference: str
    inspection_readiness_decision_identity: str
    content_integrity_acceptance_boundary_reference: str
    content_integrity_acceptance_boundary_identity: str
    content_readiness_decision_reference: str
    content_readiness_decision_identity: str
    executable_input_creation_boundary_reference: str
    executable_input_creation_boundary_identity: str
    pricing_revalidation_boundary_reference: str
    pricing_revalidation_boundary_identity: str
    credential_verification_boundary_reference: str
    credential_verification_boundary_identity: str
    input_run_manifest_readiness_reference: str
    input_run_manifest_readiness_identity: str
    candidate_input_set_identity: str
    proposed_manifest_reference: str
    proposed_manifest_identity: str
    current_runtime_integrity_reference: str
    current_runtime_integrity_identity: str
    reservation_bound_reference: str
    reservation_bound_identity: str
    inspection_readiness_decision_defined: bool
    acceptance_boundary_defined: bool
    executable_input_creation_descriptor_defined: bool
    pricing_revalidation_descriptor_defined: bool
    credential_verification_descriptor_defined: bool
    candidate_input_metadata_defined: bool
    proposed_manifest_defined: bool
    inspection_prerequisite_assessment_execution_authorized: bool
    inspection_prerequisite_assessment_performed: bool
    integrity_inspection_ready: bool
    integrity_inspection_authorized: bool
    integrity_inspection_started: bool
    integrity_inspection_completed: bool
    integrity_result_present: bool
    content_creation_execution_authorized: bool
    content_access_authorized: bool
    content_access_observed: bool
    filesystem_read_authorized: bool
    filesystem_read_observed: bool
    filesystem_write_authorized: bool
    filesystem_write_observed: bool
    content_hashing_authorized: bool
    content_hashing_observed: bool
    integrity_verification_authorized: bool
    content_integrity_verified: bool
    result_acceptance_authorized: bool
    content_accepted: bool
    executable_input_content_present: bool
    executable_content_identity_present: bool
    proposed_manifest_modified: bool
    manifest_mutation_authorized: bool
    proposed_manifest_activated: bool
    manifest_activation_authorized: bool
    pricing_revalidation_execution_authorized: bool
    pricing_revalidation_started: bool
    pricing_revalidation_result_present: bool
    pricing_revalidation_completed: bool
    credential_verification_execution_authorized: bool
    credential_verification_started: bool
    credential_verification_result_present: bool
    credential_verification_completed: bool
    credential_configuration_verified: bool
    credential_or_secret_access_observed: bool
    environment_access_observed: bool
    provider_request_created: bool
    pre_call_reservation_created: bool
    ledger_entry_created: bool
    runtime_invocation_authorized: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    run_size_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    production_effect: str
    zero_production_proof: str
    blocker_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        expected_fields = frozenset(self.__dataclass_fields__)
        if frozenset(values) != expected_fields:
            raise ShadowPhase11FinalSuccessorLineageReconciliationValidationError(
                "invalid evidence fields"
            )

        locked_values = {
            "schema_version": _SCHEMA,
            "evidence_reference": _EVIDENCE_REFERENCE,
            "locked_repository_baseline": _REPOSITORY_BASELINE,
            "locked_phase09_baseline": _PHASE09_BASELINE,
            "reconciliation_state": (
                ShadowPhase11FinalSuccessorLineageReconciliationStateV1
                .FINAL_STATIC_LINEAGE_RECONCILED_READINESS_BLOCKED
            ),
            "predecessor_status": (
                ShadowPhase11FinalSuccessorLineagePredecessorStatusV1
                .PREDECESSOR_SUCCESSOR_LINEAGE_PRESERVED
            ),
            **_LINKS,
            "launch_readiness": (
                ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
            ),
            "production_effect": "NONE",
            "zero_production_proof": "PROVEN_NONE",
        }
        excluded_fields = {
            "evidence_id",
            "blocker_codes",
            "reason_codes",
            *_TRUE_FIELDS,
        }
        false_fields = expected_fields - set(locked_values) - excluded_fields
        normalized = {
            name: _exact(values[name], expected, name)
            for name, expected in locked_values.items()
        }
        for name in _TRUE_FIELDS:
            normalized[name] = _exact(values[name], True, name)
        for name in false_fields:
            normalized[name] = _exact(values[name], False, name)
        normalized["blocker_codes"] = _codes(
            values["blocker_codes"],
            _BLOCKERS,
            "blocker_codes",
        )
        normalized["reason_codes"] = _codes(
            values["reason_codes"],
            _REASONS,
            "reason_codes",
        )

        for name, value in normalized.items():
            object.__setattr__(self, name, value)
        payload = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "evidence_id"
        }
        identity = sha256_hex(canonical_json_bytes(payload))
        supplied_identity = values["evidence_id"]
        if supplied_identity is not None and (
            type(supplied_identity) is not str
            or supplied_identity != identity
        ):
            raise ShadowPhase11FinalSuccessorLineageReconciliationValidationError(
                "supplied evidence identity does not match"
            )
        object.__setattr__(self, "evidence_id", identity)

    @property
    def identity(self) -> str:
        """Return the canonical evidence identity."""

        return self.evidence_id

    @property
    def content_readiness_decision_defined(self) -> bool:
        """Record recognition of the linked immutable readiness decision."""

        return True


def get_phase_11_shadow_pilot_final_successor_lineage_reconciliation_evidence_v1(
) -> ShadowPhase11FinalSuccessorLineageReconciliationEvidenceV1:
    """Return the immutable final successor-lineage reconciliation."""

    values: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "evidence_id": None,
        "evidence_reference": _EVIDENCE_REFERENCE,
        "locked_repository_baseline": _REPOSITORY_BASELINE,
        "locked_phase09_baseline": _PHASE09_BASELINE,
        "reconciliation_state": (
            ShadowPhase11FinalSuccessorLineageReconciliationStateV1
            .FINAL_STATIC_LINEAGE_RECONCILED_READINESS_BLOCKED
        ),
        "predecessor_status": (
            ShadowPhase11FinalSuccessorLineagePredecessorStatusV1
            .PREDECESSOR_SUCCESSOR_LINEAGE_PRESERVED
        ),
        **_LINKS,
        **{name: True for name in _TRUE_FIELDS},
        "launch_readiness": (
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": _BLOCKERS,
        "reason_codes": _REASONS,
    }
    for name in (
        ShadowPhase11FinalSuccessorLineageReconciliationEvidenceV1
        .__dataclass_fields__
    ):
        values.setdefault(name, False)
    return ShadowPhase11FinalSuccessorLineageReconciliationEvidenceV1(
        **values
    )
