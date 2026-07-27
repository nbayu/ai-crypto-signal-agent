"""Immutable denied Phase 11 integrity-inspection readiness decision.

This module records static repository-owned prerequisite and authorization
facts only.  It performs no assessment, content access, hashing, inspection,
verification, acceptance, manifest mutation, provider request, or runtime
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


_SCHEMA = "phase11-shadow-pilot-integrity-inspection-readiness-decision-v1"
_EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_INTEGRITY_INSPECTION_READINESS_DECISION_001"
)
_REPOSITORY_BASELINE = "799d4e1b2ec5f732c69d7b66924d281d27cf6eeb"
_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_LINKS = {
    "content_integrity_acceptance_boundary_reference": (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_"
        "ACCEPTANCE_BOUNDARY_001"
    ),
    "content_integrity_acceptance_boundary_identity": (
        "fbbd47cce8a7a3208719e9caecf6d06c0ee38612ea109717bb7fe08d0c7003b1"
    ),
    "content_readiness_decision_reference": (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_READINESS_DECISION_001"
    ),
    "content_readiness_decision_identity": (
        "437352460a8410929abd80a5548ff0ee2bf54bc81b6f2af50682efdebca2309b"
    ),
    "current_successor_reconciliation_reference": (
        "PHASE_11_PILOT_SUCCESSOR_EXECUTABLE_INPUT_"
        "BOUNDARY_RECONCILIATION_001"
    ),
    "current_successor_reconciliation_identity": (
        "b95dca79c2c140cd618d2239e7c1152268e063e9db23a67671782c4a7d66990a"
    ),
    "executable_input_creation_boundary_reference": (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001"
    ),
    "executable_input_creation_boundary_identity": (
        "e6ea7eaf9dd0e79aaba718ef4412c418097236d20b1c435784fb64cfd3efd9a1"
    ),
    "input_run_manifest_readiness_reference": (
        "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
    ),
    "input_run_manifest_readiness_identity": (
        "30ea2ab4f8c3aef604358f3688cf88b348cad6cc98ec887ce98502acabc4e944"
    ),
    "candidate_input_set_identity": (
        "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
    ),
    "proposed_manifest_reference": "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001",
    "proposed_manifest_identity": (
        "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
    ),
    "pricing_revalidation_boundary_reference": (
        "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001"
    ),
    "pricing_revalidation_boundary_identity": (
        "fc34f6f222825f29669ce4f575314eabeb887135ef54bc3613836f4d46ccb0fc"
    ),
    "credential_verification_boundary_reference": (
        "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_"
        "VERIFICATION_BOUNDARY_001"
    ),
    "credential_verification_boundary_identity": (
        "91991bb1f7947eb43acca9983c53a686667f1ab58be21bd769224fec174a679c"
    ),
    "current_runtime_integrity_reference": (
        "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
    ),
    "current_runtime_integrity_identity": (
        "45d1446eb173d399f748b3b11e616d51391947762d3b36848cbd4f3d5b3228ab"
    ),
    "reservation_bound_reference": (
        "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
    ),
    "reservation_bound_identity": (
        "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4"
    ),
}
_BLOCKERS = tuple(
    sorted(
        (
            "EXECUTABLE_INPUT_CONTENT_ABSENT",
            "EXECUTABLE_CONTENT_IDENTITY_ABSENT",
            "CONTENT_ACCESS_NOT_AUTHORIZED",
            "FILESYSTEM_READ_NOT_AUTHORIZED",
            "CONTENT_HASHING_NOT_AUTHORIZED",
            "INTEGRITY_VERIFICATION_NOT_AUTHORIZED",
            "RESULT_ACCEPTANCE_NOT_AUTHORIZED",
        )
    )
)
_REASONS = tuple(
    sorted(
        (
            "INSPECTION_READINESS_DECISION_DEFINED",
            "ACCEPTANCE_BOUNDARY_RECOGNIZED",
            "INSPECTION_PREREQUISITE_ASSESSMENT_NOT_PERFORMED",
            "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
            "EXECUTABLE_CONTENT_IDENTITY_REMAINS_ABSENT",
            "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
            "CONTENT_INTEGRITY_NOT_VERIFIED",
            "CONTENT_NOT_ACCEPTED",
            "PROPOSED_MANIFEST_REMAINS_INACTIVE",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)


class ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
    ValueError
):
    """Raised when denied inspection-readiness evidence is invalid."""


class ShadowPhase11IntegrityInspectionReadinessStateV1(StrEnum):
    """The sole permitted inspection-readiness state."""

    NOT_READY_FOR_INTEGRITY_INSPECTION = (
        "NOT_READY_FOR_INTEGRITY_INSPECTION"
    )


class ShadowPhase11IntegrityInspectionAuthorizationStateV1(StrEnum):
    """The sole permitted inspection-authorization state."""

    INTEGRITY_INSPECTION_NOT_AUTHORIZED = (
        "INTEGRITY_INSPECTION_NOT_AUTHORIZED"
    )


class ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1(StrEnum):
    """Closed prerequisite-check vocabulary in canonical order."""

    ACCEPTANCE_BOUNDARY_DEFINED = "ACCEPTANCE_BOUNDARY_DEFINED"
    EXECUTABLE_CONTENT_PRESENT = "EXECUTABLE_CONTENT_PRESENT"
    EXECUTABLE_CONTENT_IDENTITY_PRESENT = (
        "EXECUTABLE_CONTENT_IDENTITY_PRESENT"
    )
    CONTENT_ACCESS_AUTHORITY_GRANTED = "CONTENT_ACCESS_AUTHORITY_GRANTED"
    FILESYSTEM_READ_AUTHORITY_GRANTED = "FILESYSTEM_READ_AUTHORITY_GRANTED"
    CONTENT_HASHING_AUTHORITY_GRANTED = "CONTENT_HASHING_AUTHORITY_GRANTED"
    INTEGRITY_VERIFICATION_AUTHORITY_GRANTED = (
        "INTEGRITY_VERIFICATION_AUTHORITY_GRANTED"
    )
    RESULT_ACCEPTANCE_AUTHORITY_GRANTED = (
        "RESULT_ACCEPTANCE_AUTHORITY_GRANTED"
    )


_CHECKS = tuple(ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1)


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
    raise ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
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
        raise ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
            f"invalid {label}"
        )
    return value


def _checks(
    value: Any,
) -> tuple[ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(_CHECKS)
        or any(
            type(item)
            is not ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1
            for item in value
        )
        or len(set(value)) != len(value)
        or set(value) != set(_CHECKS)
    ):
        raise ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
            "invalid prerequisite_checks"
        )
    return _CHECKS


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
        raise ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
            f"invalid {label}"
        )
    return expected


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11IntegrityInspectionReadinessDecisionEvidenceV1:
    """Immutable denied integrity-inspection readiness evidence."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    readiness_state: ShadowPhase11IntegrityInspectionReadinessStateV1
    authorization_state: ShadowPhase11IntegrityInspectionAuthorizationStateV1
    content_integrity_acceptance_boundary_reference: str
    content_integrity_acceptance_boundary_identity: str
    content_readiness_decision_reference: str
    content_readiness_decision_identity: str
    current_successor_reconciliation_reference: str
    current_successor_reconciliation_identity: str
    executable_input_creation_boundary_reference: str
    executable_input_creation_boundary_identity: str
    input_run_manifest_readiness_reference: str
    input_run_manifest_readiness_identity: str
    candidate_input_set_identity: str
    proposed_manifest_reference: str
    proposed_manifest_identity: str
    pricing_revalidation_boundary_reference: str
    pricing_revalidation_boundary_identity: str
    credential_verification_boundary_reference: str
    credential_verification_boundary_identity: str
    current_runtime_integrity_reference: str
    current_runtime_integrity_identity: str
    reservation_bound_reference: str
    reservation_bound_identity: str
    prerequisite_checks: tuple[
        ShadowPhase11IntegrityInspectionPrerequisiteCheckKindV1,
        ...,
    ]
    inspection_readiness_decision_defined: bool
    acceptance_boundary_defined: bool
    inspection_prerequisite_assessment_execution_authorized: bool
    inspection_prerequisite_assessment_performed: bool
    integrity_inspection_ready: bool
    integrity_inspection_authorized: bool
    integrity_inspection_started: bool
    integrity_inspection_completed: bool
    integrity_result_present: bool
    executable_input_content_present: bool
    executable_content_identity_present: bool
    content_access_authorized: bool
    content_access_observed: bool
    filesystem_read_authorized: bool
    filesystem_read_observed: bool
    content_hashing_authorized: bool
    content_hashing_observed: bool
    integrity_verification_authorized: bool
    content_integrity_verified: bool
    result_acceptance_authorized: bool
    content_accepted: bool
    content_creation_execution_authorized: bool
    manifest_mutation_authorized: bool
    proposed_manifest_modified: bool
    manifest_activation_authorized: bool
    proposed_manifest_activated: bool
    pricing_revalidation_execution_authorized: bool
    credential_verification_execution_authorized: bool
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
            raise ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
                "invalid evidence fields"
            )

        locked_values = {
            "schema_version": _SCHEMA,
            "evidence_reference": _EVIDENCE_REFERENCE,
            "locked_repository_baseline": _REPOSITORY_BASELINE,
            "locked_phase09_baseline": _PHASE09_BASELINE,
            "readiness_state": (
                ShadowPhase11IntegrityInspectionReadinessStateV1
                .NOT_READY_FOR_INTEGRITY_INSPECTION
            ),
            "authorization_state": (
                ShadowPhase11IntegrityInspectionAuthorizationStateV1
                .INTEGRITY_INSPECTION_NOT_AUTHORIZED
            ),
            **_LINKS,
            "inspection_readiness_decision_defined": True,
            "acceptance_boundary_defined": True,
            "launch_readiness": (
                ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
            ),
            "production_effect": "NONE",
            "zero_production_proof": "PROVEN_NONE",
        }
        excluded_fields = {
            "evidence_id",
            "prerequisite_checks",
            "blocker_codes",
            "reason_codes",
        }
        false_fields = expected_fields - set(locked_values) - excluded_fields
        normalized = {
            name: _exact(values[name], expected, name)
            for name, expected in locked_values.items()
        }
        for name in false_fields:
            normalized[name] = _exact(values[name], False, name)
        normalized["prerequisite_checks"] = _checks(
            values["prerequisite_checks"]
        )
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
            raise ShadowPhase11IntegrityInspectionReadinessDecisionValidationError(
                "supplied evidence identity does not match"
            )
        object.__setattr__(self, "evidence_id", identity)

    @property
    def identity(self) -> str:
        """Return the canonical evidence identity."""

        return self.evidence_id


def get_phase_11_shadow_pilot_integrity_inspection_readiness_decision_evidence_v1(
) -> ShadowPhase11IntegrityInspectionReadinessDecisionEvidenceV1:
    """Return the immutable denied integrity-inspection readiness decision."""

    values: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "evidence_id": None,
        "evidence_reference": _EVIDENCE_REFERENCE,
        "locked_repository_baseline": _REPOSITORY_BASELINE,
        "locked_phase09_baseline": _PHASE09_BASELINE,
        "readiness_state": (
            ShadowPhase11IntegrityInspectionReadinessStateV1
            .NOT_READY_FOR_INTEGRITY_INSPECTION
        ),
        "authorization_state": (
            ShadowPhase11IntegrityInspectionAuthorizationStateV1
            .INTEGRITY_INSPECTION_NOT_AUTHORIZED
        ),
        **_LINKS,
        "prerequisite_checks": _CHECKS,
        "inspection_readiness_decision_defined": True,
        "acceptance_boundary_defined": True,
        "launch_readiness": (
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": _BLOCKERS,
        "reason_codes": _REASONS,
    }
    for name in (
        ShadowPhase11IntegrityInspectionReadinessDecisionEvidenceV1
        .__dataclass_fields__
    ):
        values.setdefault(name, False)
    return ShadowPhase11IntegrityInspectionReadinessDecisionEvidenceV1(
        **values
    )
