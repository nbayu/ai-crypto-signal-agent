"""Immutable content-free Phase 11 integrity acceptance boundary.

This module materializes metadata-only request, absent-result, and aggregate
evidence contracts.  It performs no content access, hashing, inspection,
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
    ShadowPhase11PilotProviderRoleV1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    ShadowPhase11PilotRouteV1,
)


class ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
    ValueError
):
    """Raised when static integrity-boundary evidence is invalid."""


class ShadowPhase11ExecutableInputContentIntegrityBoundaryStateV1(StrEnum):
    ACCEPTANCE_BOUNDARY_DEFINED_RESULT_ABSENT_INSPECTION_NOT_AUTHORIZED = (
        "ACCEPTANCE_BOUNDARY_DEFINED_RESULT_ABSENT_INSPECTION_NOT_AUTHORIZED"
    )


class ShadowPhase11ExecutableInputContentIntegrityResultStateV1(StrEnum):
    RESULT_ABSENT_NOT_INSPECTED = "RESULT_ABSENT_NOT_INSPECTED"


class ShadowPhase11ExecutableInputContentIntegrityCheckKindV1(StrEnum):
    CANDIDATE_COUNT_AND_ORDINAL_MATCH = "CANDIDATE_COUNT_AND_ORDINAL_MATCH"
    ROUTE_ROLE_AND_BOUND_MATCH = "ROUTE_ROLE_AND_BOUND_MATCH"
    CONTENT_SCHEMA_CONFORMANCE = "CONTENT_SCHEMA_CONFORMANCE"
    CONTENT_TO_CANDIDATE_LINKAGE = "CONTENT_TO_CANDIDATE_LINKAGE"
    CONTENT_TO_MANIFEST_LINKAGE = "CONTENT_TO_MANIFEST_LINKAGE"
    CONTENT_IMMUTABILITY_IDENTITY = "CONTENT_IMMUTABILITY_IDENTITY"
    PROHIBITED_SECRET_AND_AUTHORITY_ABSENCE = (
        "PROHIBITED_SECRET_AND_AUTHORITY_ABSENCE"
    )


_CHECKS = tuple(ShadowPhase11ExecutableInputContentIntegrityCheckKindV1)
_ROLES = (
    ShadowPhase11PilotProviderRoleV1.PRIMARY,
    ShadowPhase11PilotProviderRoleV1.L1,
    ShadowPhase11PilotProviderRoleV1.L2,
)
_BLOCKERS = tuple(
    sorted(
        (
            "EXECUTABLE_INPUT_CONTENT_ABSENT",
            "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
            "INTEGRITY_RESULT_ABSENT",
            "CONTENT_INTEGRITY_NOT_VERIFIED",
            "CONTENT_NOT_ACCEPTED",
            "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
        )
    )
)
_REASONS = tuple(
    sorted(
        (
            "CONTENT_INTEGRITY_ACCEPTANCE_BOUNDARY_DEFINED",
            "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
            "INTEGRITY_RESULT_ABSENT",
            "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
            "CONTENT_INTEGRITY_NOT_VERIFIED",
            "CONTENT_NOT_ACCEPTED",
            "PROPOSED_MANIFEST_REMAINS_INACTIVE",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)
_LINKS = {
    "content_readiness_decision_reference": (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_READINESS_DECISION_001"
    ),
    "content_readiness_decision_identity": (
        "dee8284ca5fdadf414b04c0e689fc10c777759e18bf7954f7efce1f851652822"
    ),
    "current_successor_reconciliation_reference": (
        "PHASE_11_PILOT_SUCCESSOR_EXECUTABLE_INPUT_"
        "BOUNDARY_RECONCILIATION_001"
    ),
    "current_successor_reconciliation_identity": (
        "709c842c8f56135220ff9e68f68bc0693e48ae2047d25f72d9929295f8f90215"
    ),
    "executable_input_creation_boundary_reference": (
        "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001"
    ),
    "executable_input_creation_boundary_identity": (
        "f82aef927d6d0e4c0e021e597bd8fcba8ed9426e5c56ad551947ea1052f1c097"
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


def _canonical(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if type(value) in (
        ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1,
        ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1,
    ):
        return value.identity
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes."""

    try:
        return json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
            f"invalid {label}"
        )
    return value


def _identity(instance: Any, field: str, supplied: Any) -> str:
    payload = {
        name: getattr(instance, name)
        for name in instance.__dataclass_fields__
        if name != field
    }
    computed = sha256_hex(canonical_json_bytes(payload))
    if supplied is not None and (
        type(supplied) is not str or supplied != computed
    ):
        raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
            f"supplied {field} does not match"
        )
    object.__setattr__(instance, field, computed)
    return computed


def _sequence(
    value: Any,
    expected: tuple[Any, ...],
    item_type: type,
    label: str,
) -> tuple[Any, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(expected)
        or any(type(item) is not item_type for item in value)
        or len(set(value)) != len(value)
        or set(value) != set(expected)
    ):
        raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
            f"invalid {label}"
        )
    return expected


def _codes(value: Any, expected: tuple[str, ...], label: str) -> tuple[str, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(expected)
        or any(type(item) is not str for item in value)
        or len(set(value)) != len(value)
        or set(value) != set(expected)
    ):
        raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
            f"invalid {label}"
        )
    return expected


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1:
    schema_version: str
    request_id: str
    request_reference: str
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
    check_kinds: tuple[ShadowPhase11ExecutableInputContentIntegrityCheckKindV1, ...]
    expected_candidate_count: int
    expected_first_ordinal: int
    expected_last_ordinal: int
    expected_route: ShadowPhase11PilotRouteV1
    expected_provider_roles: tuple[ShadowPhase11PilotProviderRoleV1, ...]
    maximum_input_tokens: int
    maximum_output_tokens: int
    maximum_attempts: int
    maximum_routed_item_cost_micro_usd: int
    maximum_total_cost_micro_usd: int
    acceptance_boundary_defined: bool
    integrity_inspection_authorized: bool
    content_access_authorized: bool
    filesystem_read_authorized: bool
    content_hashing_authorized: bool
    content_serialization_authorized: bool
    integrity_verification_authorized: bool
    result_acceptance_authorized: bool
    manifest_mutation_authorized: bool
    manifest_activation_authorized: bool
    provider_request_creation_authorized: bool
    runtime_input_submission_authorized: bool
    executable_content_present: bool
    executable_content_identity_present: bool

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != frozenset(self.__dataclass_fields__):
            raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
                "invalid request fields"
            )
        locked = {
            "schema_version": (
                "phase11-shadow-pilot-executable-input-content-integrity-"
                "acceptance-request-v1"
            ),
            "request_reference": (
                "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_"
                "ACCEPTANCE_REQUEST_001"
            ),
            **_LINKS,
            "expected_candidate_count": 20,
            "expected_first_ordinal": 1,
            "expected_last_ordinal": 20,
            "expected_route": ShadowPhase11PilotRouteV1.L1_TO_L2,
            "maximum_input_tokens": 16000,
            "maximum_output_tokens": 2000,
            "maximum_attempts": 1,
            "maximum_routed_item_cost_micro_usd": 216700,
            "maximum_total_cost_micro_usd": 4334000,
            "acceptance_boundary_defined": True,
        }
        normalized = {
            name: _exact(values[name], expected, name)
            for name, expected in locked.items()
        }
        normalized["check_kinds"] = _sequence(
            values["check_kinds"],
            _CHECKS,
            ShadowPhase11ExecutableInputContentIntegrityCheckKindV1,
            "check_kinds",
        )
        normalized["expected_provider_roles"] = _sequence(
            values["expected_provider_roles"],
            _ROLES,
            ShadowPhase11PilotProviderRoleV1,
            "expected_provider_roles",
        )
        excluded = {
            "request_id",
            "check_kinds",
            "expected_provider_roles",
        }
        false_fields = set(self.__dataclass_fields__) - set(locked) - excluded
        for name in false_fields:
            normalized[name] = _exact(values[name], False, name)
        for name, value in normalized.items():
            object.__setattr__(self, name, value)
        _identity(self, "request_id", values["request_id"])

    @property
    def identity(self) -> str:
        return self.request_id


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1:
    schema_version: str
    result_boundary_id: str
    result_boundary_reference: str
    request_reference: str
    request_identity: str
    result_state: ShadowPhase11ExecutableInputContentIntegrityResultStateV1
    result_present: bool
    result_reference: str | None
    result_identity: str | None
    integrity_inspection_started: bool
    integrity_inspection_completed: bool
    executable_content_observed: bool
    executable_content_identity_observed: bool
    candidate_count_match_verified: bool
    ordinal_match_verified: bool
    route_role_bound_match_verified: bool
    content_schema_verified: bool
    content_candidate_linkage_verified: bool
    content_manifest_linkage_verified: bool
    content_immutability_identity_verified: bool
    prohibited_secret_and_authority_absence_verified: bool
    content_integrity_verified: bool
    content_accepted: bool
    all_checks_passed: bool

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != frozenset(self.__dataclass_fields__):
            raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
                "invalid result fields"
            )
        request = _make_request()
        locked = {
            "schema_version": (
                "phase11-shadow-pilot-executable-input-content-integrity-"
                "result-boundary-v1"
            ),
            "result_boundary_reference": (
                "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_"
                "RESULT_BOUNDARY_001"
            ),
            "request_reference": request.request_reference,
            "request_identity": request.identity,
            "result_state": (
                ShadowPhase11ExecutableInputContentIntegrityResultStateV1
                .RESULT_ABSENT_NOT_INSPECTED
            ),
            "result_present": False,
            "result_reference": None,
            "result_identity": None,
        }
        normalized = {
            name: _exact(values[name], expected, name)
            for name, expected in locked.items()
        }
        false_fields = (
            set(self.__dataclass_fields__)
            - set(locked)
            - {"result_boundary_id"}
        )
        for name in false_fields:
            normalized[name] = _exact(values[name], False, name)
        for name, value in normalized.items():
            object.__setattr__(self, name, value)
        _identity(self, "result_boundary_id", values["result_boundary_id"])

    @property
    def identity(self) -> str:
        return self.result_boundary_id


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryEvidenceV1:
    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    boundary_state: ShadowPhase11ExecutableInputContentIntegrityBoundaryStateV1
    request: ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1
    result_boundary: ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1
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
    acceptance_boundary_defined: bool
    integrity_inspection_authorized: bool
    integrity_inspection_started: bool
    integrity_result_present: bool
    integrity_inspection_completed: bool
    content_access_authorized: bool
    content_access_observed: bool
    filesystem_read_authorized: bool
    filesystem_read_observed: bool
    content_hashing_authorized: bool
    content_hashing_observed: bool
    executable_content_observed: bool
    executable_content_identity_present: bool
    content_integrity_verified: bool
    content_accepted: bool
    content_creation_execution_authorized: bool
    executable_input_content_present: bool
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
        if frozenset(values) != frozenset(self.__dataclass_fields__):
            raise ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryValidationError(
                "invalid evidence fields"
            )
        request = _make_request()
        result = _make_result()
        locked = {
            "schema_version": (
                "phase11-shadow-pilot-executable-input-content-integrity-"
                "acceptance-boundary-v1"
            ),
            "evidence_reference": (
                "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_"
                "ACCEPTANCE_BOUNDARY_001"
            ),
            "locked_repository_baseline": (
                "408f1c66c0092e48d4aa02e8ef6459c174f7c52f"
            ),
            "locked_phase09_baseline": (
                "a84375fa85c2f318944adfe57aaabac6e43c219c"
            ),
            "boundary_state": (
                ShadowPhase11ExecutableInputContentIntegrityBoundaryStateV1
                .ACCEPTANCE_BOUNDARY_DEFINED_RESULT_ABSENT_INSPECTION_NOT_AUTHORIZED
            ),
            "request": request,
            "result_boundary": result,
            **_LINKS,
            "acceptance_boundary_defined": True,
            "launch_readiness": (
                ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
            ),
            "production_effect": "NONE",
            "zero_production_proof": "PROVEN_NONE",
        }
        normalized = {
            name: _exact(values[name], expected, name)
            for name, expected in locked.items()
        }
        normalized["blocker_codes"] = _codes(
            values["blocker_codes"], _BLOCKERS, "blocker_codes"
        )
        normalized["reason_codes"] = _codes(
            values["reason_codes"], _REASONS, "reason_codes"
        )
        excluded = {"evidence_id", "blocker_codes", "reason_codes"}
        false_fields = set(self.__dataclass_fields__) - set(locked) - excluded
        for name in false_fields:
            normalized[name] = _exact(values[name], False, name)
        for name, value in normalized.items():
            object.__setattr__(self, name, value)
        _identity(self, "evidence_id", values["evidence_id"])

    @property
    def identity(self) -> str:
        return self.evidence_id


def _make_request(
) -> ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1:
    values: dict[str, Any] = {
        "schema_version": (
            "phase11-shadow-pilot-executable-input-content-integrity-"
            "acceptance-request-v1"
        ),
        "request_id": None,
        "request_reference": (
            "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_"
            "ACCEPTANCE_REQUEST_001"
        ),
        **_LINKS,
        "check_kinds": _CHECKS,
        "expected_candidate_count": 20,
        "expected_first_ordinal": 1,
        "expected_last_ordinal": 20,
        "expected_route": ShadowPhase11PilotRouteV1.L1_TO_L2,
        "expected_provider_roles": _ROLES,
        "maximum_input_tokens": 16000,
        "maximum_output_tokens": 2000,
        "maximum_attempts": 1,
        "maximum_routed_item_cost_micro_usd": 216700,
        "maximum_total_cost_micro_usd": 4334000,
        "acceptance_boundary_defined": True,
    }
    for name in (
        ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1
        .__dataclass_fields__
    ):
        values.setdefault(name, False)
    return ShadowPhase11ExecutableInputContentIntegrityAcceptanceRequestV1(
        **values
    )


def _make_result(
) -> ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1:
    request = _make_request()
    values: dict[str, Any] = {
        "schema_version": (
            "phase11-shadow-pilot-executable-input-content-integrity-"
            "result-boundary-v1"
        ),
        "result_boundary_id": None,
        "result_boundary_reference": (
            "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_"
            "RESULT_BOUNDARY_001"
        ),
        "request_reference": request.request_reference,
        "request_identity": request.identity,
        "result_state": (
            ShadowPhase11ExecutableInputContentIntegrityResultStateV1
            .RESULT_ABSENT_NOT_INSPECTED
        ),
        "result_present": False,
        "result_reference": None,
        "result_identity": None,
    }
    for name in (
        ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1
        .__dataclass_fields__
    ):
        values.setdefault(name, False)
    return ShadowPhase11ExecutableInputContentIntegrityResultBoundaryV1(
        **values
    )


def get_phase_11_shadow_pilot_executable_input_content_integrity_acceptance_boundary_evidence_v1(
) -> ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryEvidenceV1:
    """Return the immutable content-free integrity acceptance boundary."""

    request = _make_request()
    result = _make_result()
    values: dict[str, Any] = {
        "schema_version": (
            "phase11-shadow-pilot-executable-input-content-integrity-"
            "acceptance-boundary-v1"
        ),
        "evidence_id": None,
        "evidence_reference": (
            "PHASE_11_PILOT_EXECUTABLE_INPUT_CONTENT_INTEGRITY_"
            "ACCEPTANCE_BOUNDARY_001"
        ),
        "locked_repository_baseline": (
            "408f1c66c0092e48d4aa02e8ef6459c174f7c52f"
        ),
        "locked_phase09_baseline": (
            "a84375fa85c2f318944adfe57aaabac6e43c219c"
        ),
        "boundary_state": (
            ShadowPhase11ExecutableInputContentIntegrityBoundaryStateV1
            .ACCEPTANCE_BOUNDARY_DEFINED_RESULT_ABSENT_INSPECTION_NOT_AUTHORIZED
        ),
        "request": request,
        "result_boundary": result,
        **_LINKS,
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
        ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryEvidenceV1
        .__dataclass_fields__
    ):
        values.setdefault(name, False)
    return (
        ShadowPhase11ExecutableInputContentIntegrityAcceptanceBoundaryEvidenceV1(
            **values
        )
    )
