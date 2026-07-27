"""Immutable non-executing Phase 11 content-readiness decision.

This module records repository-owned prerequisite and blocked-readiness facts
only.  It does not perform the assessment, access or create content, inspect
credentials or pricing, mutate a manifest or ledger, contact a provider, or
grant runtime, transmission, run-size, launch, or production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)


_SCHEMA = (
    "phase11-shadow-pilot-executable-input-content-readiness-decision-v1"
)
_EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_READINESS_DECISION_001"
)
_REPOSITORY_BASELINE = "cc1127f57ebfc0a880fc22d57ded60fcbd59cc9f"
_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_SUCCESSOR_REFERENCE = (
    "PHASE_11_PILOT_SUCCESSOR_EXECUTABLE_INPUT_"
    "BOUNDARY_RECONCILIATION_001"
)
_SUCCESSOR_IDENTITY = (
    "b95dca79c2c140cd618d2239e7c1152268e063e9db23a67671782c4a7d66990a"
)
_CREATION_BOUNDARY_REFERENCE = (
    "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001"
)
_CREATION_BOUNDARY_IDENTITY = (
    "e6ea7eaf9dd0e79aaba718ef4412c418097236d20b1c435784fb64cfd3efd9a1"
)
_READINESS_REFERENCE = "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
_READINESS_IDENTITY = (
    "30ea2ab4f8c3aef604358f3688cf88b348cad6cc98ec887ce98502acabc4e944"
)
_CANDIDATE_INPUT_SET_IDENTITY = (
    "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
)
_PROPOSED_MANIFEST_REFERENCE = "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001"
_PROPOSED_MANIFEST_IDENTITY = (
    "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
)
_PRICING_BOUNDARY_REFERENCE = (
    "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001"
)
_PRICING_BOUNDARY_IDENTITY = (
    "fc34f6f222825f29669ce4f575314eabeb887135ef54bc3613836f4d46ccb0fc"
)
_CREDENTIAL_BOUNDARY_REFERENCE = (
    "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_"
    "VERIFICATION_BOUNDARY_001"
)
_CREDENTIAL_BOUNDARY_IDENTITY = (
    "91991bb1f7947eb43acca9983c53a686667f1ab58be21bd769224fec174a679c"
)
_RUNTIME_REFERENCE = "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
_RUNTIME_IDENTITY = (
    "45d1446eb173d399f748b3b11e616d51391947762d3b36848cbd4f3d5b3228ab"
)
_RESERVATION_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
_RESERVATION_IDENTITY = (
    "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4"
)
_BLOCKERS = tuple(
    sorted(
        (
            "PRICING_REVALIDATION_INCOMPLETE",
            "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
            "CONTENT_CREATION_AUTHORITY_NOT_GRANTED",
            "CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_ABSENT",
            "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
        )
    )
)
_REASONS = tuple(
    sorted(
        (
            "READINESS_ASSESSMENT_DEFINED",
            "READINESS_ASSESSMENT_NOT_PERFORMED",
            "CANDIDATE_METADATA_COMPLETE",
            "ROUTE_ROLE_AND_BOUNDS_FIXED",
            "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
            "CONTENT_CREATION_NOT_AUTHORIZED",
            "CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_NOT_DEFINED",
            "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
    ValueError
):
    """Raised when a content-readiness decision violates its contract."""


class ShadowPhase11ExecutableInputContentReadinessStateV1(StrEnum):
    """The sole permitted executable-input content-readiness state."""

    NOT_READY_FOR_CONTENT_CREATION = "NOT_READY_FOR_CONTENT_CREATION"


class ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1(StrEnum):
    """Closed prerequisite-check vocabulary in canonical order."""

    CANDIDATE_METADATA_COMPLETE = "CANDIDATE_METADATA_COMPLETE"
    ROUTE_ROLE_AND_BOUND_CONFIGURATION_FIXED = (
        "ROUTE_ROLE_AND_BOUND_CONFIGURATION_FIXED"
    )
    PRICING_REVALIDATION_COMPLETED = "PRICING_REVALIDATION_COMPLETED"
    CREDENTIAL_CONFIGURATION_VERIFIED = "CREDENTIAL_CONFIGURATION_VERIFIED"
    CONTENT_CREATION_AUTHORITY_GRANTED = (
        "CONTENT_CREATION_AUTHORITY_GRANTED"
    )
    CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_DEFINED = (
        "CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_DEFINED"
    )
    MANIFEST_ACTIVATION_AUTHORITY_GRANTED = (
        "MANIFEST_ACTIVATION_AUTHORITY_GRANTED"
    )


_CHECKS = tuple(ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1)


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
    raise ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
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
        raise ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
            f"invalid {label}"
        )
    return value


def _checks(
    value: Any,
) -> tuple[ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(_CHECKS)
        or any(
            type(item)
            is not ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1
            for item in value
        )
        or len(set(value)) != len(value)
        or set(value) != set(_CHECKS)
    ):
        raise ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
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
        or any(
            type(item) is not str or _CODE.fullmatch(item) is None
            for item in value
        )
        or len(set(value)) != len(value)
        or set(value) != set(expected)
    ):
        raise ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
            f"invalid {label}"
        )
    return expected


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1:
    """Immutable non-executing content-readiness decision evidence."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    readiness_state: ShadowPhase11ExecutableInputContentReadinessStateV1
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
        ShadowPhase11ExecutableInputContentPrerequisiteCheckKindV1,
        ...,
    ]
    readiness_assessment_defined: bool
    readiness_assessment_execution_authorized: bool
    readiness_assessment_performed: bool
    content_creation_ready: bool
    content_creation_execution_authorized: bool
    source_content_access_authorized: bool
    source_content_access_observed: bool
    filesystem_read_authorized: bool
    filesystem_read_observed: bool
    filesystem_write_authorized: bool
    filesystem_write_observed: bool
    executable_content_generation_authorized: bool
    executable_content_generated: bool
    executable_content_serialized: bool
    executable_input_content_present: bool
    content_integrity_acceptance_boundary_defined: bool
    content_integrity_verified: bool
    manifest_mutation_authorized: bool
    proposed_manifest_modified: bool
    manifest_activation_authorized: bool
    proposed_manifest_activated: bool
    pricing_revalidation_execution_authorized: bool
    pricing_revalidation_completed: bool
    credential_verification_execution_authorized: bool
    credential_configuration_verified: bool
    provider_request_created: bool
    pre_call_reservation_created: bool
    ledger_entry_created: bool
    runtime_invocation_authorized: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    run_size_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    candidate_metadata_complete: bool
    route_role_and_bounds_fixed: bool
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    production_effect: str
    zero_production_proof: str
    blocker_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        expected_fields = frozenset(self.__dataclass_fields__)
        if frozenset(values) != expected_fields:
            raise (
                ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
                    "invalid evidence fields"
                )
            )

        locked_values = {
            "schema_version": _SCHEMA,
            "evidence_reference": _EVIDENCE_REFERENCE,
            "locked_repository_baseline": _REPOSITORY_BASELINE,
            "locked_phase09_baseline": _PHASE09_BASELINE,
            "readiness_state": (
                ShadowPhase11ExecutableInputContentReadinessStateV1
                .NOT_READY_FOR_CONTENT_CREATION
            ),
            "current_successor_reconciliation_reference": (
                _SUCCESSOR_REFERENCE
            ),
            "current_successor_reconciliation_identity": _SUCCESSOR_IDENTITY,
            "executable_input_creation_boundary_reference": (
                _CREATION_BOUNDARY_REFERENCE
            ),
            "executable_input_creation_boundary_identity": (
                _CREATION_BOUNDARY_IDENTITY
            ),
            "input_run_manifest_readiness_reference": _READINESS_REFERENCE,
            "input_run_manifest_readiness_identity": _READINESS_IDENTITY,
            "candidate_input_set_identity": _CANDIDATE_INPUT_SET_IDENTITY,
            "proposed_manifest_reference": _PROPOSED_MANIFEST_REFERENCE,
            "proposed_manifest_identity": _PROPOSED_MANIFEST_IDENTITY,
            "pricing_revalidation_boundary_reference": (
                _PRICING_BOUNDARY_REFERENCE
            ),
            "pricing_revalidation_boundary_identity": (
                _PRICING_BOUNDARY_IDENTITY
            ),
            "credential_verification_boundary_reference": (
                _CREDENTIAL_BOUNDARY_REFERENCE
            ),
            "credential_verification_boundary_identity": (
                _CREDENTIAL_BOUNDARY_IDENTITY
            ),
            "current_runtime_integrity_reference": _RUNTIME_REFERENCE,
            "current_runtime_integrity_identity": _RUNTIME_IDENTITY,
            "reservation_bound_reference": _RESERVATION_REFERENCE,
            "reservation_bound_identity": _RESERVATION_IDENTITY,
            "readiness_assessment_defined": True,
            "candidate_metadata_complete": True,
            "route_role_and_bounds_fixed": True,
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
            raise (
                ShadowPhase11ExecutableInputContentReadinessDecisionValidationError(
                    "supplied evidence identity does not match"
                )
            )
        object.__setattr__(self, "evidence_id", identity)

    @property
    def identity(self) -> str:
        """Return the canonical evidence identity."""

        return self.evidence_id


def get_phase_11_shadow_pilot_executable_input_content_readiness_decision_evidence_v1(
) -> ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1:
    """Return the immutable non-executing content-readiness decision."""

    fields: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "evidence_id": None,
        "evidence_reference": _EVIDENCE_REFERENCE,
        "locked_repository_baseline": _REPOSITORY_BASELINE,
        "locked_phase09_baseline": _PHASE09_BASELINE,
        "readiness_state": (
            ShadowPhase11ExecutableInputContentReadinessStateV1
            .NOT_READY_FOR_CONTENT_CREATION
        ),
        "current_successor_reconciliation_reference": _SUCCESSOR_REFERENCE,
        "current_successor_reconciliation_identity": _SUCCESSOR_IDENTITY,
        "executable_input_creation_boundary_reference": (
            _CREATION_BOUNDARY_REFERENCE
        ),
        "executable_input_creation_boundary_identity": (
            _CREATION_BOUNDARY_IDENTITY
        ),
        "input_run_manifest_readiness_reference": _READINESS_REFERENCE,
        "input_run_manifest_readiness_identity": _READINESS_IDENTITY,
        "candidate_input_set_identity": _CANDIDATE_INPUT_SET_IDENTITY,
        "proposed_manifest_reference": _PROPOSED_MANIFEST_REFERENCE,
        "proposed_manifest_identity": _PROPOSED_MANIFEST_IDENTITY,
        "pricing_revalidation_boundary_reference": (
            _PRICING_BOUNDARY_REFERENCE
        ),
        "pricing_revalidation_boundary_identity": _PRICING_BOUNDARY_IDENTITY,
        "credential_verification_boundary_reference": (
            _CREDENTIAL_BOUNDARY_REFERENCE
        ),
        "credential_verification_boundary_identity": (
            _CREDENTIAL_BOUNDARY_IDENTITY
        ),
        "current_runtime_integrity_reference": _RUNTIME_REFERENCE,
        "current_runtime_integrity_identity": _RUNTIME_IDENTITY,
        "reservation_bound_reference": _RESERVATION_REFERENCE,
        "reservation_bound_identity": _RESERVATION_IDENTITY,
        "prerequisite_checks": _CHECKS,
        "readiness_assessment_defined": True,
        "candidate_metadata_complete": True,
        "route_role_and_bounds_fixed": True,
        "launch_readiness": (
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": _BLOCKERS,
        "reason_codes": _REASONS,
    }
    for name in (
        ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1
        .__dataclass_fields__
    ):
        fields.setdefault(name, False)
    return ShadowPhase11ExecutableInputContentReadinessDecisionEvidenceV1(
        **fields
    )
