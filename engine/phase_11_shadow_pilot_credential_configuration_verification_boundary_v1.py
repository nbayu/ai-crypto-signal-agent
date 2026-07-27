"""Immutable secret-free Phase 11 credential verification boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_blocked_readiness_reconciliation_v1 import (
    get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1,
)
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
from engine.phase_11_shadow_pilot_pricing_revalidation_boundary_v1 import (
    get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1,
)


_BASELINE = "7b0edf90cf5abbb7776a0e56058839543e8dc2ab"
_PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_REQUEST_REFERENCE = (
    "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_REQUEST_001"
)
_RESULT_REFERENCE = (
    "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_RESULT_BOUNDARY_001"
)
_EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_BOUNDARY_001"
)
_GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
_GATE_IDENTITY = (
    "29a07dc2cb644aeb4dbdc9dc00e4da79b5fa3d1486e98dabdcadb1e40140debb"
)
_RECONCILIATION_REFERENCE = (
    "PHASE_11_PILOT_BLOCKED_READINESS_RECONCILIATION_001"
)
_RECONCILIATION_IDENTITY = (
    "92e9773c94cf8263202976e9c6d6f9c62a7e66b8de59ada63992056a4e9a2bd0"
)
_RUNTIME_REFERENCE = "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
_RUNTIME_IDENTITY = (
    "45d1446eb173d399f748b3b11e616d51391947762d3b36848cbd4f3d5b3228ab"
)
_PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001"
_PRICING_IDENTITY = (
    "fc34f6f222825f29669ce4f575314eabeb887135ef54bc3613836f4d46ccb0fc"
)
_RESERVATION_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
_RESERVATION_IDENTITY = (
    "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4"
)
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
    ValueError
):
    """Raised when static credential verification evidence is invalid."""


class ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1(StrEnum):
    REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED = (
        "REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED"
    )


class ShadowPhase11CredentialConfigurationVerificationResultStateV1(StrEnum):
    RESULT_ABSENT_NOT_EXECUTED = "RESULT_ABSENT_NOT_EXECUTED"


class ShadowPhase11CredentialConfigurationVerificationCheckKindV1(StrEnum):
    PRIMARY_PROVIDER_CREDENTIAL_CONFIGURATION = (
        "PRIMARY_PROVIDER_CREDENTIAL_CONFIGURATION"
    )
    L1_PROVIDER_CREDENTIAL_CONFIGURATION = "L1_PROVIDER_CREDENTIAL_CONFIGURATION"
    L2_PROVIDER_CREDENTIAL_CONFIGURATION = "L2_PROVIDER_CREDENTIAL_CONFIGURATION"
    SECRET_MATERIAL_REPOSITORY_ABSENCE = "SECRET_MATERIAL_REPOSITORY_ABSENCE"
    RUNTIME_CREDENTIAL_INJECTION_BOUNDARY = "RUNTIME_CREDENTIAL_INJECTION_BOUNDARY"


_ROLES = tuple(ShadowPhase11PilotProviderRoleV1)
_ROLE_ORDER = {role: index for index, role in enumerate(_ROLES)}
_CHECKS = tuple(ShadowPhase11CredentialConfigurationVerificationCheckKindV1)
_CHECK_ORDER = {check: index for index, check in enumerate(_CHECKS)}
_REQUEST_REASONS = tuple(
    sorted(
        (
            "REQUIRED_CREDENTIAL_SLOTS_DEFINED",
            "CREDENTIAL_VERIFICATION_CHECKS_DEFINED",
            "VERIFICATION_EXECUTION_NOT_AUTHORIZED",
            "ENVIRONMENT_ACCESS_NOT_AUTHORIZED",
            "CREDENTIAL_ACCESS_NOT_AUTHORIZED",
            "SECRET_MATERIAL_ACCESS_NOT_AUTHORIZED",
            "NO_PROVIDER_AUTHENTICATION_REQUEST_AUTHORITY",
        )
    )
)
_RESULT_REASONS = tuple(
    sorted(
        (
            "RESULT_ABSENT",
            "VERIFICATION_NOT_STARTED",
            "VERIFICATION_NOT_COMPLETED",
            "CREDENTIAL_REFERENCES_NOT_RESOLVED",
            "NO_PROVIDER_AUTHENTICATION_OBSERVATION",
            "NO_CHECK_PASSED",
        )
    )
)
_EVIDENCE_REASONS = tuple(
    sorted(
        (
            "CREDENTIAL_VERIFICATION_REQUEST_DEFINED",
            "CREDENTIAL_VERIFICATION_EXECUTION_NOT_AUTHORIZED",
            "CREDENTIAL_VERIFICATION_RESULT_ABSENT",
            "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
            "NO_ENVIRONMENT_OR_CREDENTIAL_ACCESS",
            "NO_PROVIDER_AUTHENTICATION_REQUEST",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if type(value) in (
        ShadowPhase11CredentialConfigurationVerificationRequestV1,
        ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1,
    ):
        return value.identity
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
    raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic canonical UTF-8 JSON bytes."""

    try:
        encoded = json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return b"".join(
            bytes((item,))
            if item < 128
            else f"\\x{item:02x}".encode("ascii")
            for item in encoded
        )
    except (TypeError, ValueError) as error:
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _exact_fields(values: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if frozenset(values) != expected:
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            f"invalid {label} fields"
        )


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            f"invalid {label}"
        )
    return value


def _true(value: Any, label: str) -> bool:
    if type(value) is not bool or value is not True:
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            f"invalid {label}"
        )
    return value


def _false(value: Any, label: str) -> bool:
    if type(value) is not bool or value is not False:
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            f"invalid {label}"
        )
    return value


def _ordered_roles(value: Any) -> tuple[ShadowPhase11PilotProviderRoleV1, ...]:
    if (
        type(value) is not tuple
        or len(value) != len(_ROLES)
        or any(type(item) is not ShadowPhase11PilotProviderRoleV1 for item in value)
        or len(set(value)) != len(value)
        or set(value) != set(_ROLES)
    ):
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            "invalid provider_roles"
        )
    return tuple(sorted(value, key=lambda item: _ROLE_ORDER[item]))


def _ordered_checks(
    value: Any,
) -> tuple[ShadowPhase11CredentialConfigurationVerificationCheckKindV1, ...]:
    if (
        type(value) is not tuple
        or len(value) != len(_CHECKS)
        or any(
            type(item)
            is not ShadowPhase11CredentialConfigurationVerificationCheckKindV1
            for item in value
        )
        or len(set(value)) != len(value)
        or set(value) != set(_CHECKS)
    ):
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            "invalid check_kinds"
        )
    return tuple(sorted(value, key=lambda item: _CHECK_ORDER[item]))


def _codes(value: Any, expected: tuple[str, ...], label: str) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or len(value) != len(expected)
        or any(
            type(item) is not str or _REASON.fullmatch(item) is None
            for item in value
        )
        or len(set(value)) != len(value)
        or set(value) != set(expected)
    ):
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            f"invalid {label}"
        )
    return expected


def _identity(instance: Any, field: str, supplied: Any) -> None:
    material = {
        name: getattr(instance, name)
        for name in instance.__dataclass_fields__
        if name != field
    }
    derived = sha256_hex(canonical_json_bytes(material))
    if supplied is not None and (
        type(supplied) is not str
        or _HASH.fullmatch(supplied) is None
        or supplied != derived
    ):
        raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
            f"invalid {field}"
        )
    object.__setattr__(instance, field, derived)


_REQUEST_FALSE_FIELDS = (
    "verification_execution_authorized",
    "credential_reference_access_authorized",
    "secret_material_access_authorized",
    "environment_access_authorized",
    "filesystem_access_authorized",
    "network_access_authorized",
    "provider_authentication_probe_authorized",
    "provider_authentication_request_created",
    "credential_configuration_write_authorized",
    "actual_credential_reference_names_present",
    "secret_material_present",
)
_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "request_reference",
        "credential_safe_gate_reference",
        "credential_safe_gate_identity",
        "blocked_readiness_reconciliation_reference",
        "blocked_readiness_reconciliation_identity",
        "current_runtime_integrity_reference",
        "current_runtime_integrity_identity",
        "pricing_revalidation_boundary_reference",
        "pricing_revalidation_boundary_identity",
        "reservation_bound_reference",
        "reservation_bound_identity",
        "provider_roles",
        "primary_model_identifier",
        "l1_model_identifier",
        "l2_model_identifier",
        "check_kinds",
        "verification_descriptor_defined",
        *_REQUEST_FALSE_FIELDS,
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11CredentialConfigurationVerificationRequestV1:
    schema_version: str
    request_id: str
    request_reference: str
    credential_safe_gate_reference: str
    credential_safe_gate_identity: str
    blocked_readiness_reconciliation_reference: str
    blocked_readiness_reconciliation_identity: str
    current_runtime_integrity_reference: str
    current_runtime_integrity_identity: str
    pricing_revalidation_boundary_reference: str
    pricing_revalidation_boundary_identity: str
    reservation_bound_reference: str
    reservation_bound_identity: str
    provider_roles: tuple[ShadowPhase11PilotProviderRoleV1, ...]
    primary_model_identifier: str
    l1_model_identifier: str
    l2_model_identifier: str
    check_kinds: tuple[
        ShadowPhase11CredentialConfigurationVerificationCheckKindV1, ...
    ]
    verification_descriptor_defined: bool
    verification_execution_authorized: bool
    credential_reference_access_authorized: bool
    secret_material_access_authorized: bool
    environment_access_authorized: bool
    filesystem_access_authorized: bool
    network_access_authorized: bool
    provider_authentication_probe_authorized: bool
    provider_authentication_request_created: bool
    credential_configuration_write_authorized: bool
    actual_credential_reference_names_present: bool
    secret_material_present: bool
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _REQUEST_FIELDS, "request")
        normalized = dict(values)
        for name, expected in (
            (
                "schema_version",
                "phase11-shadow-pilot-credential-configuration-verification-request-v1",
            ),
            ("request_reference", _REQUEST_REFERENCE),
            ("credential_safe_gate_reference", _GATE_REFERENCE),
            ("credential_safe_gate_identity", _GATE_IDENTITY),
            (
                "blocked_readiness_reconciliation_reference",
                _RECONCILIATION_REFERENCE,
            ),
            (
                "blocked_readiness_reconciliation_identity",
                _RECONCILIATION_IDENTITY,
            ),
            ("current_runtime_integrity_reference", _RUNTIME_REFERENCE),
            ("current_runtime_integrity_identity", _RUNTIME_IDENTITY),
            ("pricing_revalidation_boundary_reference", _PRICING_REFERENCE),
            ("pricing_revalidation_boundary_identity", _PRICING_IDENTITY),
            ("reservation_bound_reference", _RESERVATION_REFERENCE),
            ("reservation_bound_identity", _RESERVATION_IDENTITY),
            ("primary_model_identifier", "deepseek-v4-pro"),
            ("l1_model_identifier", "claude-sonnet-5"),
            ("l2_model_identifier", "claude-opus-4-8"),
        ):
            normalized[name] = _exact(values[name], expected, name)
        normalized["provider_roles"] = _ordered_roles(values["provider_roles"])
        normalized["check_kinds"] = _ordered_checks(values["check_kinds"])
        normalized["verification_descriptor_defined"] = _true(
            values["verification_descriptor_defined"],
            "verification_descriptor_defined",
        )
        for name in _REQUEST_FALSE_FIELDS:
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


_RESULT_FALSE_FIELDS = (
    "result_present",
    "verification_started",
    "verification_completed",
    "credential_references_resolved",
    "secret_material_loaded",
    "environment_configuration_observed",
    "filesystem_configuration_observed",
    "primary_provider_configuration_verified",
    "l1_provider_configuration_verified",
    "l2_provider_configuration_verified",
    "secret_material_repository_absence_verified",
    "runtime_credential_injection_boundary_verified",
    "provider_authentication_probe_performed",
    "provider_authentication_observation_present",
    "provider_authentication_accepted",
    "all_checks_passed",
)
_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "result_boundary_id",
        "result_boundary_reference",
        "request_reference",
        "request_identity",
        "result_state",
        *_RESULT_FALSE_FIELDS,
        "result_reference",
        "result_identity",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1:
    schema_version: str
    result_boundary_id: str
    result_boundary_reference: str
    request_reference: str
    request_identity: str
    result_state: ShadowPhase11CredentialConfigurationVerificationResultStateV1
    result_present: bool
    result_reference: None
    result_identity: None
    verification_started: bool
    verification_completed: bool
    credential_references_resolved: bool
    secret_material_loaded: bool
    environment_configuration_observed: bool
    filesystem_configuration_observed: bool
    primary_provider_configuration_verified: bool
    l1_provider_configuration_verified: bool
    l2_provider_configuration_verified: bool
    secret_material_repository_absence_verified: bool
    runtime_credential_injection_boundary_verified: bool
    provider_authentication_probe_performed: bool
    provider_authentication_observation_present: bool
    provider_authentication_accepted: bool
    all_checks_passed: bool
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _RESULT_FIELDS, "result boundary")
        normalized = dict(values)
        for name, expected in (
            (
                "schema_version",
                "phase11-shadow-pilot-credential-configuration-verification-result-boundary-v1",
            ),
            ("result_boundary_reference", _RESULT_REFERENCE),
            ("request_reference", _REQUEST_REFERENCE),
            ("request_identity", _REQUEST.identity),
            (
                "result_state",
                ShadowPhase11CredentialConfigurationVerificationResultStateV1
                .RESULT_ABSENT_NOT_EXECUTED,
            ),
            ("result_reference", None),
            ("result_identity", None),
        ):
            normalized[name] = _exact(values[name], expected, name)
        for name in _RESULT_FALSE_FIELDS:
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


def _make_request() -> ShadowPhase11CredentialConfigurationVerificationRequestV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    reconciliation = (
        get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    )
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    return ShadowPhase11CredentialConfigurationVerificationRequestV1(
        schema_version=(
            "phase11-shadow-pilot-credential-configuration-verification-request-v1"
        ),
        request_id=None,
        request_reference=_REQUEST_REFERENCE,
        credential_safe_gate_reference=gate.evidence_reference,
        credential_safe_gate_identity=gate.identity,
        blocked_readiness_reconciliation_reference=reconciliation.evidence_reference,
        blocked_readiness_reconciliation_identity=reconciliation.identity,
        current_runtime_integrity_reference=runtime.evidence_reference,
        current_runtime_integrity_identity=runtime.identity,
        pricing_revalidation_boundary_reference=pricing.evidence_reference,
        pricing_revalidation_boundary_identity=pricing.identity,
        reservation_bound_reference=reservation.evidence_reference,
        reservation_bound_identity=reservation.identity,
        provider_roles=_ROLES,
        primary_model_identifier="deepseek-v4-pro",
        l1_model_identifier="claude-sonnet-5",
        l2_model_identifier="claude-opus-4-8",
        check_kinds=_CHECKS,
        verification_descriptor_defined=True,
        verification_execution_authorized=False,
        credential_reference_access_authorized=False,
        secret_material_access_authorized=False,
        environment_access_authorized=False,
        filesystem_access_authorized=False,
        network_access_authorized=False,
        provider_authentication_probe_authorized=False,
        provider_authentication_request_created=False,
        credential_configuration_write_authorized=False,
        actual_credential_reference_names_present=False,
        secret_material_present=False,
        reason_codes=_REQUEST_REASONS,
    )


_REQUEST = _make_request()


def _make_result() -> ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1:
    return ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1(
        schema_version=(
            "phase11-shadow-pilot-credential-configuration-verification-result-boundary-v1"
        ),
        result_boundary_id=None,
        result_boundary_reference=_RESULT_REFERENCE,
        request_reference=_REQUEST.request_reference,
        request_identity=_REQUEST.identity,
        result_state=(
            ShadowPhase11CredentialConfigurationVerificationResultStateV1
            .RESULT_ABSENT_NOT_EXECUTED
        ),
        result_present=False,
        result_reference=None,
        result_identity=None,
        verification_started=False,
        verification_completed=False,
        credential_references_resolved=False,
        secret_material_loaded=False,
        environment_configuration_observed=False,
        filesystem_configuration_observed=False,
        primary_provider_configuration_verified=False,
        l1_provider_configuration_verified=False,
        l2_provider_configuration_verified=False,
        secret_material_repository_absence_verified=False,
        runtime_credential_injection_boundary_verified=False,
        provider_authentication_probe_performed=False,
        provider_authentication_observation_present=False,
        provider_authentication_accepted=False,
        all_checks_passed=False,
        reason_codes=_RESULT_REASONS,
    )


_RESULT = _make_result()


_EVIDENCE_FALSE_FIELDS = (
    "verification_execution_authorized",
    "verification_started",
    "verification_result_present",
    "verification_completed",
    "credential_configuration_verified",
    "credential_reference_access_authorized",
    "credential_reference_access_observed",
    "secret_material_access_authorized",
    "secret_material_access_observed",
    "secret_material_present",
    "environment_access_authorized",
    "environment_access_observed",
    "filesystem_access_authorized",
    "filesystem_access_observed",
    "network_access_authorized",
    "network_access_observed",
    "provider_authentication_probe_authorized",
    "provider_authentication_probe_performed",
    "provider_authentication_request_created",
    "provider_authentication_observation_present",
    "provider_authentication_accepted",
    "credential_configuration_write_authorized",
    "credential_configuration_modified",
    "pricing_revalidation_execution_authorized",
    "provider_request_created",
    "pre_call_reservation_created",
    "ledger_entry_created",
    "runtime_invocation_authorized",
    "provider_call_authorized",
    "provider_transmission_authorized",
    "run_size_authorized",
    "manifest_activation_authorized",
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
        "credential_safe_gate_reference",
        "credential_safe_gate_identity",
        "blocked_readiness_reconciliation_reference",
        "blocked_readiness_reconciliation_identity",
        "current_runtime_integrity_reference",
        "current_runtime_integrity_identity",
        "pricing_revalidation_boundary_reference",
        "pricing_revalidation_boundary_identity",
        "reservation_bound_reference",
        "reservation_bound_identity",
        "boundary_state",
        "request",
        "result_boundary",
        "verification_descriptor_defined",
        *_EVIDENCE_FALSE_FIELDS,
        "launch_readiness",
        "production_effect",
        "zero_production_proof",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1:
    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    credential_safe_gate_reference: str
    credential_safe_gate_identity: str
    blocked_readiness_reconciliation_reference: str
    blocked_readiness_reconciliation_identity: str
    current_runtime_integrity_reference: str
    current_runtime_integrity_identity: str
    pricing_revalidation_boundary_reference: str
    pricing_revalidation_boundary_identity: str
    reservation_bound_reference: str
    reservation_bound_identity: str
    boundary_state: ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1
    request: ShadowPhase11CredentialConfigurationVerificationRequestV1
    result_boundary: ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1
    verification_descriptor_defined: bool
    verification_execution_authorized: bool
    verification_started: bool
    verification_result_present: bool
    verification_completed: bool
    credential_configuration_verified: bool
    credential_reference_access_authorized: bool
    credential_reference_access_observed: bool
    secret_material_access_authorized: bool
    secret_material_access_observed: bool
    secret_material_present: bool
    environment_access_authorized: bool
    environment_access_observed: bool
    filesystem_access_authorized: bool
    filesystem_access_observed: bool
    network_access_authorized: bool
    network_access_observed: bool
    provider_authentication_probe_authorized: bool
    provider_authentication_probe_performed: bool
    provider_authentication_request_created: bool
    provider_authentication_observation_present: bool
    provider_authentication_accepted: bool
    credential_configuration_write_authorized: bool
    credential_configuration_modified: bool
    pricing_revalidation_execution_authorized: bool
    provider_request_created: bool
    pre_call_reservation_created: bool
    ledger_entry_created: bool
    runtime_invocation_authorized: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    run_size_authorized: bool
    manifest_activation_authorized: bool
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
                "phase11-shadow-pilot-credential-configuration-verification-boundary-v1",
            ),
            ("evidence_reference", _EVIDENCE_REFERENCE),
            ("locked_repository_baseline", _BASELINE),
            ("locked_phase09_baseline", _PHASE09),
            ("credential_safe_gate_reference", _GATE_REFERENCE),
            ("credential_safe_gate_identity", _GATE_IDENTITY),
            (
                "blocked_readiness_reconciliation_reference",
                _RECONCILIATION_REFERENCE,
            ),
            (
                "blocked_readiness_reconciliation_identity",
                _RECONCILIATION_IDENTITY,
            ),
            ("current_runtime_integrity_reference", _RUNTIME_REFERENCE),
            ("current_runtime_integrity_identity", _RUNTIME_IDENTITY),
            ("pricing_revalidation_boundary_reference", _PRICING_REFERENCE),
            ("pricing_revalidation_boundary_identity", _PRICING_IDENTITY),
            ("reservation_bound_reference", _RESERVATION_REFERENCE),
            ("reservation_bound_identity", _RESERVATION_IDENTITY),
            (
                "boundary_state",
                ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1
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
            type(values["request"])
            is not ShadowPhase11CredentialConfigurationVerificationRequestV1
            or values["request"].identity != _REQUEST.identity
        ):
            raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
                "invalid request"
            )
        if (
            type(values["result_boundary"])
            is not ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1
            or values["result_boundary"].identity != _RESULT.identity
        ):
            raise ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError(
                "invalid result_boundary"
            )
        normalized["verification_descriptor_defined"] = _true(
            values["verification_descriptor_defined"],
            "verification_descriptor_defined",
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


def _make_evidence() -> ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    reconciliation = (
        get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    )
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    return ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1(
        schema_version=(
            "phase11-shadow-pilot-credential-configuration-verification-boundary-v1"
        ),
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        locked_repository_baseline=_BASELINE,
        locked_phase09_baseline=_PHASE09,
        credential_safe_gate_reference=gate.evidence_reference,
        credential_safe_gate_identity=gate.identity,
        blocked_readiness_reconciliation_reference=reconciliation.evidence_reference,
        blocked_readiness_reconciliation_identity=reconciliation.identity,
        current_runtime_integrity_reference=runtime.evidence_reference,
        current_runtime_integrity_identity=runtime.identity,
        pricing_revalidation_boundary_reference=pricing.evidence_reference,
        pricing_revalidation_boundary_identity=pricing.identity,
        reservation_bound_reference=reservation.evidence_reference,
        reservation_bound_identity=reservation.identity,
        boundary_state=(
            ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1
            .REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED
        ),
        request=_REQUEST,
        result_boundary=_RESULT,
        verification_descriptor_defined=True,
        verification_execution_authorized=False,
        verification_started=False,
        verification_result_present=False,
        verification_completed=False,
        credential_configuration_verified=False,
        credential_reference_access_authorized=False,
        credential_reference_access_observed=False,
        secret_material_access_authorized=False,
        secret_material_access_observed=False,
        secret_material_present=False,
        environment_access_authorized=False,
        environment_access_observed=False,
        filesystem_access_authorized=False,
        filesystem_access_observed=False,
        network_access_authorized=False,
        network_access_observed=False,
        provider_authentication_probe_authorized=False,
        provider_authentication_probe_performed=False,
        provider_authentication_request_created=False,
        provider_authentication_observation_present=False,
        provider_authentication_accepted=False,
        credential_configuration_write_authorized=False,
        credential_configuration_modified=False,
        pricing_revalidation_execution_authorized=False,
        provider_request_created=False,
        pre_call_reservation_created=False,
        ledger_entry_created=False,
        runtime_invocation_authorized=False,
        provider_call_authorized=False,
        provider_transmission_authorized=False,
        run_size_authorized=False,
        manifest_activation_authorized=False,
        launch_authorized=False,
        production_authorized=False,
        launch_readiness=ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        production_effect="NONE",
        zero_production_proof="PROVEN_NONE",
        reason_codes=_EVIDENCE_REASONS,
    )


_EVIDENCE = _make_evidence()


def get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1(
) -> ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1:
    """Return immutable static credential verification boundary evidence."""

    return _EVIDENCE


__all__ = (
    "ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1",
    "ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1",
    "ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError",
    "ShadowPhase11CredentialConfigurationVerificationCheckKindV1",
    "ShadowPhase11CredentialConfigurationVerificationRequestV1",
    "ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1",
    "ShadowPhase11CredentialConfigurationVerificationResultStateV1",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1",
    "sha256_hex",
)
