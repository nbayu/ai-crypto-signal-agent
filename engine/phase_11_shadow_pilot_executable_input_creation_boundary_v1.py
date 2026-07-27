"""Immutable static Phase 11 executable-input creation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotProviderRoleV1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    ShadowPhase11PilotRouteV1,
)


_BASELINE = "43ec5abb8112ff95c9b7e1109cc698a81a386ee3"
_PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_REQUEST_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_REQUEST_001"
_RESULT_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_RESULT_BOUNDARY_001"
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001"

_SUCCESSOR_REFERENCE = (
    "PHASE_11_PILOT_SUCCESSOR_BLOCKED_READINESS_BOUNDARY_RECONCILIATION_001"
)
_SUCCESSOR_IDENTITY = (
    "e64fa932cc399903d947d68828854c63b7a955eb1b6ce83c7cfef648f73a96be"
)
_READINESS_REFERENCE = "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
_READINESS_IDENTITY = (
    "30ea2ab4f8c3aef604358f3688cf88b348cad6cc98ec887ce98502acabc4e944"
)
_CANDIDATE_IDENTITY = (
    "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
)
_MANIFEST_REFERENCE = "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001"
_MANIFEST_IDENTITY = (
    "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
)
_PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001"
_PRICING_IDENTITY = (
    "fc34f6f222825f29669ce4f575314eabeb887135ef54bc3613836f4d46ccb0fc"
)
_CREDENTIAL_REFERENCE = (
    "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_BOUNDARY_001"
)
_CREDENTIAL_IDENTITY = (
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

_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")

_REQUEST_REASONS = tuple(
    sorted(
        (
            "EXECUTABLE_INPUT_CREATION_DESCRIPTOR_DEFINED",
            "EXACT_CREATION_CHECKS_DEFINED",
            "SOURCE_CONTENT_ACCESS_NOT_AUTHORIZED",
            "NO_FILESYSTEM_WRITE_AUTHORITY",
            "NO_CONTENT_SERIALIZATION_AUTHORITY",
            "NO_MANIFEST_ACTIVATION_AUTHORITY",
            "NO_PROVIDER_OR_RUNTIME_REQUEST_AUTHORITY",
        )
    )
)
_RESULT_REASONS = tuple(
    sorted(
        (
            "RESULT_ABSENT_NOT_EXECUTED",
            "CREATION_NOT_STARTED",
            "CREATION_NOT_COMPLETED",
            "EXECUTABLE_CONTENT_NOT_GENERATED",
            "EXECUTABLE_CONTENT_NOT_PRESENT",
            "NO_CONTENT_INTEGRITY_VERIFICATION",
            "NO_CHECK_PASSED",
        )
    )
)
_EVIDENCE_REASONS = tuple(
    sorted(
        (
            "EXECUTABLE_INPUT_CREATION_REQUEST_DEFINED",
            "EXECUTABLE_INPUT_CREATION_EXECUTION_NOT_AUTHORIZED",
            "EXECUTABLE_INPUT_CREATION_RESULT_ABSENT",
            "EXECUTABLE_INPUT_CONTENT_ABSENT",
            "PROPOSED_MANIFEST_NOT_ACTIVATED",
            "NO_PROVIDER_OR_RUNTIME_REQUEST_AUTHORITY",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)


class ShadowPhase11ExecutableInputCreationBoundaryValidationError(ValueError):
    """Raised when static creation-boundary evidence is invalid."""


class ShadowPhase11ExecutableInputCreationBoundaryStateV1(StrEnum):
    REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED = (
        "REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED"
    )


class ShadowPhase11ExecutableInputCreationResultStateV1(StrEnum):
    RESULT_ABSENT_NOT_EXECUTED = "RESULT_ABSENT_NOT_EXECUTED"


class ShadowPhase11ExecutableInputCreationCheckKindV1(StrEnum):
    CANDIDATE_COUNT_AND_ORDINAL_CONTINUITY = (
        "CANDIDATE_COUNT_AND_ORDINAL_CONTINUITY"
    )
    ROUTE_AND_PROVIDER_ROLE_BINDINGS = "ROUTE_AND_PROVIDER_ROLE_BINDINGS"
    TOKEN_ATTEMPT_AND_COST_BOUNDS = "TOKEN_ATTEMPT_AND_COST_BOUNDS"
    EXECUTABLE_CONTENT_SCHEMA = "EXECUTABLE_CONTENT_SCHEMA"
    MANIFEST_CONTENT_LINKAGE = "MANIFEST_CONTENT_LINKAGE"


_CHECKS = tuple(ShadowPhase11ExecutableInputCreationCheckKindV1)
_ROLES = (
    ShadowPhase11PilotProviderRoleV1.PRIMARY,
    ShadowPhase11PilotProviderRoleV1.L1,
    ShadowPhase11PilotProviderRoleV1.L2,
)


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
                "canonical decimal must be finite"
            )
        return _canonical_decimal(value)
    if type(value) in (
        ShadowPhase11ExecutableInputCreationRequestV1,
        ShadowPhase11ExecutableInputCreationResultBoundaryV1,
    ):
        return value.identity
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if type(value) in (tuple, list):
        return [_canonical_value(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
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
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    if type(value) is not bytes:
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            "sha256 input must be bytes"
        )
    return sha256(value).hexdigest()


def _exact_fields(
    values: dict[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    if frozenset(values) != expected:
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            f"invalid {label} fields"
        )


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            f"invalid {label}"
        )
    return value


def _false(value: Any, label: str) -> bool:
    return _exact(value, False, label)


def _true(value: Any, label: str) -> bool:
    return _exact(value, True, label)


def _codes(value: Any, expected: tuple[str, ...], label: str) -> tuple[str, ...]:
    if (
        type(value) not in (tuple, list)
        or any(
            type(item) is not str or _REASON.fullmatch(item) is None
            for item in value
        )
        or len(value) != len(expected)
        or len(set(value)) != len(value)
        or set(value) != set(expected)
    ):
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            f"invalid {label}"
        )
    return expected


def _checks(
    value: Any,
) -> tuple[ShadowPhase11ExecutableInputCreationCheckKindV1, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(_CHECKS)
        or any(
            type(item) is not ShadowPhase11ExecutableInputCreationCheckKindV1
            for item in value
        )
        or len(set(value)) != len(value)
        or set(value) != set(_CHECKS)
    ):
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            "invalid check_kinds"
        )
    return _CHECKS


def _roles(value: Any) -> tuple[ShadowPhase11PilotProviderRoleV1, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(_ROLES)
        or any(
            type(item) is not ShadowPhase11PilotProviderRoleV1 for item in value
        )
        or len(set(value)) != len(value)
        or set(value) != set(_ROLES)
    ):
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            "invalid expected_provider_roles"
        )
    return _ROLES


def _identity(instance: Any, identity_field: str, supplied: Any) -> str:
    payload = {
        name: getattr(instance, name)
        for name in instance.__dataclass_fields__
        if name != identity_field
    }
    computed = sha256_hex(canonical_json_bytes(payload))
    if supplied is not None and (
        type(supplied) is not str or supplied != computed
    ):
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            f"{identity_field} does not match canonical material"
        )
    if _HASH.fullmatch(computed) is None:
        raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
            "identity computation failed"
        )
    object.__setattr__(instance, identity_field, computed)
    return computed


_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "request_reference",
        "successor_reconciliation_reference",
        "successor_reconciliation_identity",
        "input_manifest_readiness_reference",
        "input_manifest_readiness_identity",
        "candidate_input_set_identity",
        "proposed_manifest_reference",
        "proposed_manifest_identity",
        "pricing_revalidation_boundary_reference",
        "pricing_revalidation_boundary_identity",
        "credential_verification_boundary_reference",
        "credential_verification_boundary_identity",
        "current_runtime_integrity_reference",
        "current_runtime_integrity_identity",
        "reservation_bound_reference",
        "reservation_bound_identity",
        "check_kinds",
        "expected_candidate_count",
        "expected_first_ordinal",
        "expected_last_ordinal",
        "expected_route",
        "expected_provider_roles",
        "maximum_input_tokens",
        "maximum_output_tokens",
        "maximum_attempts",
        "maximum_routed_item_cost_micro_usd",
        "maximum_total_cost_micro_usd",
        "creation_descriptor_defined",
        "creation_execution_authorized",
        "source_content_access_authorized",
        "filesystem_write_authorized",
        "executable_content_serialization_authorized",
        "manifest_content_mutation_authorized",
        "manifest_activation_authorized",
        "provider_request_creation_authorized",
        "runtime_input_submission_authorized",
        "raw_executable_content_present",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11ExecutableInputCreationRequestV1:
    schema_version: str
    request_id: str
    request_reference: str
    successor_reconciliation_reference: str
    successor_reconciliation_identity: str
    input_manifest_readiness_reference: str
    input_manifest_readiness_identity: str
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
    check_kinds: tuple[ShadowPhase11ExecutableInputCreationCheckKindV1, ...]
    expected_candidate_count: int
    expected_first_ordinal: int
    expected_last_ordinal: int
    expected_route: ShadowPhase11PilotRouteV1
    expected_provider_roles: tuple[ShadowPhase11PilotProviderRoleV1, ...]
    maximum_input_tokens: int
    maximum_output_tokens: int
    maximum_attempts: int
    maximum_routed_item_cost_micro_usd: Decimal
    maximum_total_cost_micro_usd: Decimal
    creation_descriptor_defined: bool
    creation_execution_authorized: bool
    source_content_access_authorized: bool
    filesystem_write_authorized: bool
    executable_content_serialization_authorized: bool
    manifest_content_mutation_authorized: bool
    manifest_activation_authorized: bool
    provider_request_creation_authorized: bool
    runtime_input_submission_authorized: bool
    raw_executable_content_present: bool
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _REQUEST_FIELDS, "request")
        normalized = dict(values)
        for name, expected in (
            (
                "schema_version",
                "phase11-shadow-pilot-executable-input-creation-request-v1",
            ),
            ("request_reference", _REQUEST_REFERENCE),
            ("successor_reconciliation_reference", _SUCCESSOR_REFERENCE),
            ("successor_reconciliation_identity", _SUCCESSOR_IDENTITY),
            ("input_manifest_readiness_reference", _READINESS_REFERENCE),
            ("input_manifest_readiness_identity", _READINESS_IDENTITY),
            ("candidate_input_set_identity", _CANDIDATE_IDENTITY),
            ("proposed_manifest_reference", _MANIFEST_REFERENCE),
            ("proposed_manifest_identity", _MANIFEST_IDENTITY),
            ("pricing_revalidation_boundary_reference", _PRICING_REFERENCE),
            ("pricing_revalidation_boundary_identity", _PRICING_IDENTITY),
            ("credential_verification_boundary_reference", _CREDENTIAL_REFERENCE),
            ("credential_verification_boundary_identity", _CREDENTIAL_IDENTITY),
            ("current_runtime_integrity_reference", _RUNTIME_REFERENCE),
            ("current_runtime_integrity_identity", _RUNTIME_IDENTITY),
            ("reservation_bound_reference", _RESERVATION_REFERENCE),
            ("reservation_bound_identity", _RESERVATION_IDENTITY),
            ("expected_candidate_count", 20),
            ("expected_first_ordinal", 1),
            ("expected_last_ordinal", 20),
            ("expected_route", ShadowPhase11PilotRouteV1.L1_TO_L2),
            ("maximum_input_tokens", 16000),
            ("maximum_output_tokens", 2000),
            ("maximum_attempts", 1),
            ("maximum_routed_item_cost_micro_usd", Decimal("216700")),
            ("maximum_total_cost_micro_usd", Decimal("4334000")),
        ):
            normalized[name] = _exact(values[name], expected, name)
        normalized["check_kinds"] = _checks(values["check_kinds"])
        normalized["expected_provider_roles"] = _roles(
            values["expected_provider_roles"]
        )
        normalized["creation_descriptor_defined"] = _true(
            values["creation_descriptor_defined"], "creation_descriptor_defined"
        )
        for name in (
            "creation_execution_authorized",
            "source_content_access_authorized",
            "filesystem_write_authorized",
            "executable_content_serialization_authorized",
            "manifest_content_mutation_authorized",
            "manifest_activation_authorized",
            "provider_request_creation_authorized",
            "runtime_input_submission_authorized",
            "raw_executable_content_present",
        ):
            normalized[name] = _false(values[name], name)
        normalized["reason_codes"] = _codes(
            values["reason_codes"], _REQUEST_REASONS, "request reason_codes"
        )
        supplied = values["request_id"]
        for name in self.__dataclass_fields__:
            if name != "request_id":
                object.__setattr__(self, name, normalized[name])
        _identity(self, "request_id", supplied)

    @property
    def identity(self) -> str:
        return self.request_id


_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "result_boundary_id",
        "result_boundary_reference",
        "request_reference",
        "request_identity",
        "result_state",
        "result_present",
        "result_reference",
        "result_identity",
        "creation_started",
        "creation_completed",
        "executable_content_generated",
        "executable_content_serialized",
        "executable_content_present",
        "candidate_count_verified",
        "ordinal_continuity_verified",
        "route_role_bindings_verified",
        "token_attempt_cost_bounds_verified",
        "executable_content_schema_verified",
        "manifest_content_linkage_verified",
        "content_integrity_verified",
        "all_checks_passed",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11ExecutableInputCreationResultBoundaryV1:
    schema_version: str
    result_boundary_id: str
    result_boundary_reference: str
    request_reference: str
    request_identity: str
    result_state: ShadowPhase11ExecutableInputCreationResultStateV1
    result_present: bool
    result_reference: None
    result_identity: None
    creation_started: bool
    creation_completed: bool
    executable_content_generated: bool
    executable_content_serialized: bool
    executable_content_present: bool
    candidate_count_verified: bool
    ordinal_continuity_verified: bool
    route_role_bindings_verified: bool
    token_attempt_cost_bounds_verified: bool
    executable_content_schema_verified: bool
    manifest_content_linkage_verified: bool
    content_integrity_verified: bool
    all_checks_passed: bool
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _RESULT_FIELDS, "result boundary")
        normalized = dict(values)
        for name, expected in (
            (
                "schema_version",
                "phase11-shadow-pilot-executable-input-creation-result-boundary-v1",
            ),
            ("result_boundary_reference", _RESULT_REFERENCE),
            ("request_reference", _REQUEST_REFERENCE),
            ("request_identity", _REQUEST.identity),
            (
                "result_state",
                ShadowPhase11ExecutableInputCreationResultStateV1
                .RESULT_ABSENT_NOT_EXECUTED,
            ),
            ("result_reference", None),
            ("result_identity", None),
        ):
            normalized[name] = _exact(values[name], expected, name)
        for name in (
            "result_present",
            "creation_started",
            "creation_completed",
            "executable_content_generated",
            "executable_content_serialized",
            "executable_content_present",
            "candidate_count_verified",
            "ordinal_continuity_verified",
            "route_role_bindings_verified",
            "token_attempt_cost_bounds_verified",
            "executable_content_schema_verified",
            "manifest_content_linkage_verified",
            "content_integrity_verified",
            "all_checks_passed",
        ):
            normalized[name] = _false(values[name], name)
        normalized["reason_codes"] = _codes(
            values["reason_codes"], _RESULT_REASONS, "result reason_codes"
        )
        supplied = values["result_boundary_id"]
        for name in self.__dataclass_fields__:
            if name != "result_boundary_id":
                object.__setattr__(self, name, normalized[name])
        _identity(self, "result_boundary_id", supplied)

    @property
    def identity(self) -> str:
        return self.result_boundary_id


_EVIDENCE_FALSE_FIELDS = (
    "creation_execution_authorized",
    "creation_started",
    "creation_result_present",
    "creation_completed",
    "source_content_access_authorized",
    "source_content_access_observed",
    "filesystem_write_authorized",
    "filesystem_write_observed",
    "executable_content_generation_authorized",
    "executable_content_generated",
    "executable_content_serialized",
    "executable_input_content_present",
    "content_integrity_verified",
    "manifest_content_mutation_authorized",
    "proposed_manifest_modified",
    "manifest_activation_authorized",
    "proposed_manifest_activated",
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
_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_id",
        "evidence_reference",
        "locked_repository_baseline",
        "locked_phase09_baseline",
        "successor_reconciliation_reference",
        "successor_reconciliation_identity",
        "input_manifest_readiness_reference",
        "input_manifest_readiness_identity",
        "candidate_input_set_identity",
        "proposed_manifest_reference",
        "proposed_manifest_identity",
        "pricing_revalidation_boundary_reference",
        "pricing_revalidation_boundary_identity",
        "credential_verification_boundary_reference",
        "credential_verification_boundary_identity",
        "current_runtime_integrity_reference",
        "current_runtime_integrity_identity",
        "reservation_bound_reference",
        "reservation_bound_identity",
        "boundary_state",
        "request",
        "result_boundary",
        "creation_descriptor_defined",
        *_EVIDENCE_FALSE_FIELDS,
        "launch_readiness",
        "production_effect",
        "zero_production_proof",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1:
    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    successor_reconciliation_reference: str
    successor_reconciliation_identity: str
    input_manifest_readiness_reference: str
    input_manifest_readiness_identity: str
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
    boundary_state: ShadowPhase11ExecutableInputCreationBoundaryStateV1
    request: ShadowPhase11ExecutableInputCreationRequestV1
    result_boundary: ShadowPhase11ExecutableInputCreationResultBoundaryV1
    creation_descriptor_defined: bool
    creation_execution_authorized: bool
    creation_started: bool
    creation_result_present: bool
    creation_completed: bool
    source_content_access_authorized: bool
    source_content_access_observed: bool
    filesystem_write_authorized: bool
    filesystem_write_observed: bool
    executable_content_generation_authorized: bool
    executable_content_generated: bool
    executable_content_serialized: bool
    executable_input_content_present: bool
    content_integrity_verified: bool
    manifest_content_mutation_authorized: bool
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
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _EVIDENCE_FIELDS, "evidence")
        normalized = dict(values)
        for name, expected in (
            (
                "schema_version",
                "phase11-shadow-pilot-executable-input-creation-boundary-v1",
            ),
            ("evidence_reference", _EVIDENCE_REFERENCE),
            ("locked_repository_baseline", _BASELINE),
            ("locked_phase09_baseline", _PHASE09),
            ("successor_reconciliation_reference", _SUCCESSOR_REFERENCE),
            ("successor_reconciliation_identity", _SUCCESSOR_IDENTITY),
            ("input_manifest_readiness_reference", _READINESS_REFERENCE),
            ("input_manifest_readiness_identity", _READINESS_IDENTITY),
            ("candidate_input_set_identity", _CANDIDATE_IDENTITY),
            ("proposed_manifest_reference", _MANIFEST_REFERENCE),
            ("proposed_manifest_identity", _MANIFEST_IDENTITY),
            ("pricing_revalidation_boundary_reference", _PRICING_REFERENCE),
            ("pricing_revalidation_boundary_identity", _PRICING_IDENTITY),
            ("credential_verification_boundary_reference", _CREDENTIAL_REFERENCE),
            ("credential_verification_boundary_identity", _CREDENTIAL_IDENTITY),
            ("current_runtime_integrity_reference", _RUNTIME_REFERENCE),
            ("current_runtime_integrity_identity", _RUNTIME_IDENTITY),
            ("reservation_bound_reference", _RESERVATION_REFERENCE),
            ("reservation_bound_identity", _RESERVATION_IDENTITY),
            (
                "boundary_state",
                ShadowPhase11ExecutableInputCreationBoundaryStateV1
                .REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED,
            ),
            (
                "launch_readiness",
                ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
            ),
            ("production_effect", "NONE"),
            ("zero_production_proof", "PROVEN_NONE"),
        ):
            normalized[name] = _exact(values[name], expected, name)
        if (
            type(values["request"]) is not ShadowPhase11ExecutableInputCreationRequestV1
            or values["request"].identity != _REQUEST.identity
        ):
            raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
                "invalid request"
            )
        if (
            type(values["result_boundary"])
            is not ShadowPhase11ExecutableInputCreationResultBoundaryV1
            or values["result_boundary"].identity != _RESULT.identity
        ):
            raise ShadowPhase11ExecutableInputCreationBoundaryValidationError(
                "invalid result_boundary"
            )
        normalized["request"] = values["request"]
        normalized["result_boundary"] = values["result_boundary"]
        normalized["creation_descriptor_defined"] = _true(
            values["creation_descriptor_defined"], "creation_descriptor_defined"
        )
        for name in _EVIDENCE_FALSE_FIELDS:
            normalized[name] = _false(values[name], name)
        normalized["reason_codes"] = _codes(
            values["reason_codes"], _EVIDENCE_REASONS, "evidence reason_codes"
        )
        supplied = values["evidence_id"]
        for name in self.__dataclass_fields__:
            if name != "evidence_id":
                object.__setattr__(self, name, normalized[name])
        _identity(self, "evidence_id", supplied)

    @property
    def identity(self) -> str:
        return self.evidence_id


def _make_request() -> ShadowPhase11ExecutableInputCreationRequestV1:
    return ShadowPhase11ExecutableInputCreationRequestV1(
        schema_version="phase11-shadow-pilot-executable-input-creation-request-v1",
        request_id=None,
        request_reference=_REQUEST_REFERENCE,
        successor_reconciliation_reference=_SUCCESSOR_REFERENCE,
        successor_reconciliation_identity=_SUCCESSOR_IDENTITY,
        input_manifest_readiness_reference=_READINESS_REFERENCE,
        input_manifest_readiness_identity=_READINESS_IDENTITY,
        candidate_input_set_identity=_CANDIDATE_IDENTITY,
        proposed_manifest_reference=_MANIFEST_REFERENCE,
        proposed_manifest_identity=_MANIFEST_IDENTITY,
        pricing_revalidation_boundary_reference=_PRICING_REFERENCE,
        pricing_revalidation_boundary_identity=_PRICING_IDENTITY,
        credential_verification_boundary_reference=_CREDENTIAL_REFERENCE,
        credential_verification_boundary_identity=_CREDENTIAL_IDENTITY,
        current_runtime_integrity_reference=_RUNTIME_REFERENCE,
        current_runtime_integrity_identity=_RUNTIME_IDENTITY,
        reservation_bound_reference=_RESERVATION_REFERENCE,
        reservation_bound_identity=_RESERVATION_IDENTITY,
        check_kinds=_CHECKS,
        expected_candidate_count=20,
        expected_first_ordinal=1,
        expected_last_ordinal=20,
        expected_route=ShadowPhase11PilotRouteV1.L1_TO_L2,
        expected_provider_roles=_ROLES,
        maximum_input_tokens=16000,
        maximum_output_tokens=2000,
        maximum_attempts=1,
        maximum_routed_item_cost_micro_usd=Decimal("216700"),
        maximum_total_cost_micro_usd=Decimal("4334000"),
        creation_descriptor_defined=True,
        creation_execution_authorized=False,
        source_content_access_authorized=False,
        filesystem_write_authorized=False,
        executable_content_serialization_authorized=False,
        manifest_content_mutation_authorized=False,
        manifest_activation_authorized=False,
        provider_request_creation_authorized=False,
        runtime_input_submission_authorized=False,
        raw_executable_content_present=False,
        reason_codes=_REQUEST_REASONS,
    )


_REQUEST = _make_request()


def _make_result() -> ShadowPhase11ExecutableInputCreationResultBoundaryV1:
    return ShadowPhase11ExecutableInputCreationResultBoundaryV1(
        schema_version=(
            "phase11-shadow-pilot-executable-input-creation-result-boundary-v1"
        ),
        result_boundary_id=None,
        result_boundary_reference=_RESULT_REFERENCE,
        request_reference=_REQUEST.request_reference,
        request_identity=_REQUEST.identity,
        result_state=(
            ShadowPhase11ExecutableInputCreationResultStateV1
            .RESULT_ABSENT_NOT_EXECUTED
        ),
        result_present=False,
        result_reference=None,
        result_identity=None,
        creation_started=False,
        creation_completed=False,
        executable_content_generated=False,
        executable_content_serialized=False,
        executable_content_present=False,
        candidate_count_verified=False,
        ordinal_continuity_verified=False,
        route_role_bindings_verified=False,
        token_attempt_cost_bounds_verified=False,
        executable_content_schema_verified=False,
        manifest_content_linkage_verified=False,
        content_integrity_verified=False,
        all_checks_passed=False,
        reason_codes=_RESULT_REASONS,
    )


_RESULT = _make_result()


def _make_evidence() -> ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1:
    return ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1(
        schema_version="phase11-shadow-pilot-executable-input-creation-boundary-v1",
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        locked_repository_baseline=_BASELINE,
        locked_phase09_baseline=_PHASE09,
        successor_reconciliation_reference=_SUCCESSOR_REFERENCE,
        successor_reconciliation_identity=_SUCCESSOR_IDENTITY,
        input_manifest_readiness_reference=_READINESS_REFERENCE,
        input_manifest_readiness_identity=_READINESS_IDENTITY,
        candidate_input_set_identity=_CANDIDATE_IDENTITY,
        proposed_manifest_reference=_MANIFEST_REFERENCE,
        proposed_manifest_identity=_MANIFEST_IDENTITY,
        pricing_revalidation_boundary_reference=_PRICING_REFERENCE,
        pricing_revalidation_boundary_identity=_PRICING_IDENTITY,
        credential_verification_boundary_reference=_CREDENTIAL_REFERENCE,
        credential_verification_boundary_identity=_CREDENTIAL_IDENTITY,
        current_runtime_integrity_reference=_RUNTIME_REFERENCE,
        current_runtime_integrity_identity=_RUNTIME_IDENTITY,
        reservation_bound_reference=_RESERVATION_REFERENCE,
        reservation_bound_identity=_RESERVATION_IDENTITY,
        boundary_state=(
            ShadowPhase11ExecutableInputCreationBoundaryStateV1
            .REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED
        ),
        request=_REQUEST,
        result_boundary=_RESULT,
        creation_descriptor_defined=True,
        creation_execution_authorized=False,
        creation_started=False,
        creation_result_present=False,
        creation_completed=False,
        source_content_access_authorized=False,
        source_content_access_observed=False,
        filesystem_write_authorized=False,
        filesystem_write_observed=False,
        executable_content_generation_authorized=False,
        executable_content_generated=False,
        executable_content_serialized=False,
        executable_input_content_present=False,
        content_integrity_verified=False,
        manifest_content_mutation_authorized=False,
        proposed_manifest_modified=False,
        manifest_activation_authorized=False,
        proposed_manifest_activated=False,
        pricing_revalidation_execution_authorized=False,
        credential_verification_execution_authorized=False,
        provider_request_created=False,
        pre_call_reservation_created=False,
        ledger_entry_created=False,
        runtime_invocation_authorized=False,
        provider_call_authorized=False,
        provider_transmission_authorized=False,
        run_size_authorized=False,
        launch_authorized=False,
        production_authorized=False,
        launch_readiness=ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        production_effect="NONE",
        zero_production_proof="PROVEN_NONE",
        reason_codes=_EVIDENCE_REASONS,
    )


_EVIDENCE = _make_evidence()


def get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1(
) -> ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1:
    """Return immutable static executable-input creation boundary evidence."""

    return _EVIDENCE


__all__ = (
    "ShadowPhase11ExecutableInputCreationBoundaryEvidenceV1",
    "ShadowPhase11ExecutableInputCreationBoundaryStateV1",
    "ShadowPhase11ExecutableInputCreationBoundaryValidationError",
    "ShadowPhase11ExecutableInputCreationCheckKindV1",
    "ShadowPhase11ExecutableInputCreationRequestV1",
    "ShadowPhase11ExecutableInputCreationResultBoundaryV1",
    "ShadowPhase11ExecutableInputCreationResultStateV1",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1",
    "sha256_hex",
)
