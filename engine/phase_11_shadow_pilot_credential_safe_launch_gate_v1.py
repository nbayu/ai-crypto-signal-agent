"""Immutable, secret-free Phase 11 credential-safe blocked launch gate.

This module contains static evidence only.  It does not inspect environment
state, resolve credentials, contact providers, access accounts, reserve
budget, mutate a ledger, select input, build a manifest, launch, or publish.
"""

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
    ShadowPhase11PilotPricingRevalidationStatusV1,
    ShadowPhase11PilotProviderRoleV1,
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    ShadowPhase11PreCallReservationStateV1,
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_REFERENCE = re.compile(r"^[A-Z0-9][A-Z0-9_]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")

_REQUIREMENT_SCHEMA = "phase11-shadow-pilot-credential-requirement-v1"
_GATE_SCHEMA = "phase11-shadow-pilot-credential-safe-launch-gate-v1"
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
_BUDGET_REFERENCE = "PHASE_11_SHADOW_PILOT_BUDGET_USD_5_001"
_MODEL_COST_REFERENCE = "PHASE_11_PILOT_MODEL_COST_BOUNDS_001"
_LOCKED_REPOSITORY_BASELINE = (
    "5ec5c39b542a573a142eff60c8c9bbc1ec7925b3"
)
_LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"

_PROVIDER_ROLES = {
    "DEEPSEEK": (ShadowPhase11PilotProviderRoleV1.PRIMARY,),
    "ANTHROPIC": (
        ShadowPhase11PilotProviderRoleV1.L1,
        ShadowPhase11PilotProviderRoleV1.L2,
    ),
}
_ROLE_ORDER = {
    ShadowPhase11PilotProviderRoleV1.PRIMARY: 0,
    ShadowPhase11PilotProviderRoleV1.L1: 1,
    ShadowPhase11PilotProviderRoleV1.L2: 2,
}
_PROVIDER_ORDER = {"DEEPSEEK": 0, "ANTHROPIC": 1}
_BLOCKERS = (
    "AUTHENTICATION_TERMINAL_CLASSIFICATION_NOT_VERIFIED",
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "PILOT_INPUT_ABSENT",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "RUN_MANIFEST_ABSENT",
    "RUNTIME_NO_RETRY_ENFORCEMENT_NOT_VERIFIED",
)


class ShadowPhase11CredentialSafeLaunchGateValidationError(ValueError):
    """Raised when blocked launch-gate evidence is invalid."""


class ShadowPhase11CredentialVerificationStateV1(StrEnum):
    """The only credential state represented by this blocked evidence."""

    NOT_VERIFIED = "NOT_VERIFIED"


class ShadowPhase11CredentialSafeLaunchGateStateV1(StrEnum):
    """The only launch-gate state represented by this evidence."""

    BLOCKED = "BLOCKED"


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowPhase11CredentialSafeLaunchGateValidationError(
                "canonical Decimal must be finite"
            )
        return _canonical_decimal(value)
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
    if type(value) is ShadowPhase11CredentialRequirementV1:
        return value.identity_material
    raise ShadowPhase11CredentialSafeLaunchGateValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes for deterministic evidence."""

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
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _identity(material: Any, supplied: Any, label: str) -> str:
    derived = sha256_hex(canonical_json_bytes(material))
    if supplied is not None and (
        type(supplied) is not str
        or _HASH.fullmatch(supplied) is None
        or supplied != derived
    ):
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            f"invalid {label}"
        )
    return derived


def _exact_text(name: str, value: Any, expected: str) -> str:
    if type(value) is not str or value != expected:
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            f"invalid {name}"
        )
    return value


def _exact_reference(name: str, value: Any, expected: str) -> str:
    if (
        type(value) is not str
        or _REFERENCE.fullmatch(value) is None
        or value != expected
    ):
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            f"invalid {name}"
        )
    return value


def _exact_commit(name: str, value: Any, expected: str) -> str:
    if (
        type(value) is not str
        or _COMMIT.fullmatch(value) is None
        or value != expected
    ):
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            f"invalid {name}"
        )
    return value


def _exact_bool(name: str, value: Any, expected: bool) -> bool:
    if type(value) is not bool or value is not expected:
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            f"invalid {name}"
        )
    return value


def _exact_int(name: str, value: Any, expected: int) -> int:
    if type(value) is not int or value != expected:
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            f"invalid {name}"
        )
    return value


def _exact_decimal(name: str, value: Any, expected: Decimal) -> Decimal:
    if (
        type(value) is not Decimal
        or not value.is_finite()
        or value < 0
        or value != expected
    ):
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            f"invalid {name}"
        )
    return value


def _exact_enum(
    name: str,
    value: Any,
    enum_type: type[StrEnum],
    expected: StrEnum,
) -> StrEnum:
    if type(value) is not enum_type or value is not expected:
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            f"invalid {name}"
        )
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            "invalid reason_codes"
        )
    if any(
        type(reason) is not str or _REASON.fullmatch(reason) is None
        for reason in value
    ):
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            "invalid reason_codes"
        )
    normalized = tuple(sorted(value))
    if len(set(normalized)) != len(normalized):
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            "invalid reason_codes"
        )
    return normalized


def _roles(value: Any, provider: str) -> tuple[ShadowPhase11PilotProviderRoleV1, ...]:
    if type(value) is not tuple or not value:
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            "invalid roles"
        )
    if any(type(role) is not ShadowPhase11PilotProviderRoleV1 for role in value):
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            "invalid roles"
        )
    normalized = tuple(sorted(value, key=lambda role: _ROLE_ORDER[role]))
    if (
        len(set(normalized)) != len(normalized)
        or normalized != _PROVIDER_ROLES[provider]
    ):
        raise ShadowPhase11CredentialSafeLaunchGateValidationError(
            "invalid provider roles"
        )
    return normalized


_REQUIREMENT_FIELDS = {
    "schema_version",
    "requirement_id",
    "provider",
    "roles",
    "credential_required",
    "verification_state",
    "credential_reference_present",
    "credential_material_present",
    "credential_access_attempted",
    "account_access_attempted",
    "credential_validation_endpoint_called",
    "provider_call_authorized",
    "maximum_attempts",
    "provider_retry_authorized",
    "credential_retry_authorized",
    "authentication_retry_authorized",
    "credential_failure_terminal_required",
    "authentication_failure_terminal_required",
    "reason_codes",
}


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11CredentialRequirementV1:
    """Secret-free logical credential requirement evidence."""

    schema_version: str
    requirement_id: str
    provider: str
    roles: tuple[ShadowPhase11PilotProviderRoleV1, ...]
    credential_required: bool
    verification_state: ShadowPhase11CredentialVerificationStateV1
    credential_reference_present: bool
    credential_material_present: bool
    credential_access_attempted: bool
    account_access_attempted: bool
    credential_validation_endpoint_called: bool
    provider_call_authorized: bool
    maximum_attempts: int
    provider_retry_authorized: bool
    credential_retry_authorized: bool
    authentication_retry_authorized: bool
    credential_failure_terminal_required: bool
    authentication_failure_terminal_required: bool
    reason_codes: tuple[str, ...]

    def __init__(self, **fields: Any) -> None:
        if set(fields) != _REQUIREMENT_FIELDS:
            raise ShadowPhase11CredentialSafeLaunchGateValidationError(
                "invalid requirement fields"
            )
        provider = fields["provider"]
        if type(provider) is not str or provider not in _PROVIDER_ROLES:
            raise ShadowPhase11CredentialSafeLaunchGateValidationError(
                "invalid provider"
            )
        values: dict[str, Any] = {
            "schema_version": _exact_text(
                "schema_version",
                fields["schema_version"],
                _REQUIREMENT_SCHEMA,
            ),
            "provider": provider,
            "roles": _roles(fields["roles"], provider),
            "credential_required": _exact_bool(
                "credential_required",
                fields["credential_required"],
                True,
            ),
            "verification_state": _exact_enum(
                "verification_state",
                fields["verification_state"],
                ShadowPhase11CredentialVerificationStateV1,
                ShadowPhase11CredentialVerificationStateV1.NOT_VERIFIED,
            ),
            "maximum_attempts": _exact_int(
                "maximum_attempts",
                fields["maximum_attempts"],
                1,
            ),
            "reason_codes": _reason_codes(fields["reason_codes"]),
        }
        for name in (
            "credential_reference_present",
            "credential_material_present",
            "credential_access_attempted",
            "account_access_attempted",
            "credential_validation_endpoint_called",
            "provider_call_authorized",
            "provider_retry_authorized",
            "credential_retry_authorized",
            "authentication_retry_authorized",
        ):
            values[name] = _exact_bool(name, fields[name], False)
        for name in (
            "credential_failure_terminal_required",
            "authentication_failure_terminal_required",
        ):
            values[name] = _exact_bool(name, fields[name], True)
        values["requirement_id"] = _identity(
            {**values, "requirement_id": None},
            fields["requirement_id"],
            "requirement_id",
        )
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def identity(self) -> str:
        return self.requirement_id

    @property
    def identity_material(self) -> Mapping[str, Any]:
        return {
            name: getattr(self, name)
            for name in _REQUIREMENT_FIELDS
            if name != "requirement_id"
        }


_GATE_FIELDS = {
    "schema_version",
    "gate_id",
    "evidence_reference",
    "pricing_evidence_reference",
    "pricing_evidence_identity",
    "reservation_bound_reference",
    "reservation_bound_identity",
    "budget_authorization_reference",
    "model_cost_authorization_reference",
    "locked_repository_baseline",
    "locked_phase09_baseline",
    "credential_requirements",
    "gate_state",
    "credential_configuration_verified",
    "credential_material_accessed",
    "account_state_accessed",
    "credential_validation_endpoint_called",
    "provider_call_authorized",
    "provider_transmission_authorized",
    "run_size_authorized",
    "reservation_creation_authorized",
    "ledger_mutation_authorized",
    "launch_authorized",
    "production_authorized",
    "maximum_attempts",
    "provider_retry_authorized",
    "credential_retry_authorized",
    "authentication_retry_authorized",
    "credential_failure_terminal_required",
    "authentication_failure_terminal_required",
    "pricing_revalidation_required_before_reservation_use",
    "launch_time_pricing_revalidation_required",
    "fixed_freshness_window_defined",
    "pricing_revalidation_status",
    "reservation_state",
    "reservation_required_before_provider_transmission",
    "budget_reserved_micro_usd",
    "budget_consumed_micro_usd",
    "pilot_input_present",
    "run_manifest_present",
    "runtime_no_retry_enforcement_verified",
    "authentication_terminal_classification_verified",
    "launch_readiness",
    "production_effect",
    "zero_production_effect_proof",
    "blocker_codes",
    "reason_codes",
}


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11CredentialSafeLaunchGateV1:
    """Immutable blocked launch-gate evidence with no operational authority."""

    schema_version: str
    gate_id: str
    evidence_reference: str
    pricing_evidence_reference: str
    pricing_evidence_identity: str
    reservation_bound_reference: str
    reservation_bound_identity: str
    budget_authorization_reference: str
    model_cost_authorization_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    credential_requirements: tuple[ShadowPhase11CredentialRequirementV1, ...]
    gate_state: ShadowPhase11CredentialSafeLaunchGateStateV1
    credential_configuration_verified: bool
    credential_material_accessed: bool
    account_state_accessed: bool
    credential_validation_endpoint_called: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    run_size_authorized: bool
    reservation_creation_authorized: bool
    ledger_mutation_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    maximum_attempts: int
    provider_retry_authorized: bool
    credential_retry_authorized: bool
    authentication_retry_authorized: bool
    credential_failure_terminal_required: bool
    authentication_failure_terminal_required: bool
    pricing_revalidation_required_before_reservation_use: bool
    launch_time_pricing_revalidation_required: bool
    fixed_freshness_window_defined: bool
    pricing_revalidation_status: ShadowPhase11PilotPricingRevalidationStatusV1
    reservation_state: ShadowPhase11PreCallReservationStateV1
    reservation_required_before_provider_transmission: bool
    budget_reserved_micro_usd: Decimal
    budget_consumed_micro_usd: Decimal
    pilot_input_present: bool
    run_manifest_present: bool
    runtime_no_retry_enforcement_verified: bool
    authentication_terminal_classification_verified: bool
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    production_effect: str
    zero_production_effect_proof: str
    blocker_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **fields: Any) -> None:
        if set(fields) != _GATE_FIELDS:
            raise ShadowPhase11CredentialSafeLaunchGateValidationError(
                "invalid gate fields"
            )
        pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
        reservation = (
            get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
        )
        requirements = fields["credential_requirements"]
        if (
            type(requirements) is not tuple
            or len(requirements) != 2
            or any(
                type(item) is not ShadowPhase11CredentialRequirementV1
                for item in requirements
            )
            or {item.provider for item in requirements}
            != set(_PROVIDER_ROLES)
        ):
            raise ShadowPhase11CredentialSafeLaunchGateValidationError(
                "invalid credential_requirements"
            )
        normalized_requirements = tuple(
            sorted(
                requirements,
                key=lambda item: _PROVIDER_ORDER[item.provider],
            )
        )
        blockers = fields["blocker_codes"]
        if (
            type(blockers) is not tuple
            or any(
                type(item) is not str or _REASON.fullmatch(item) is None
                for item in blockers
            )
            or len(blockers) != len(_BLOCKERS)
            or set(blockers) != set(_BLOCKERS)
        ):
            raise ShadowPhase11CredentialSafeLaunchGateValidationError(
                "invalid blocker_codes"
            )

        values: dict[str, Any] = {
            "schema_version": _exact_text(
                "schema_version",
                fields["schema_version"],
                _GATE_SCHEMA,
            ),
            "evidence_reference": _exact_reference(
                "evidence_reference",
                fields["evidence_reference"],
                _EVIDENCE_REFERENCE,
            ),
            "pricing_evidence_reference": _exact_reference(
                "pricing_evidence_reference",
                fields["pricing_evidence_reference"],
                pricing.evidence_reference,
            ),
            "reservation_bound_reference": _exact_reference(
                "reservation_bound_reference",
                fields["reservation_bound_reference"],
                reservation.evidence_reference,
            ),
            "budget_authorization_reference": _exact_reference(
                "budget_authorization_reference",
                fields["budget_authorization_reference"],
                _BUDGET_REFERENCE,
            ),
            "model_cost_authorization_reference": _exact_reference(
                "model_cost_authorization_reference",
                fields["model_cost_authorization_reference"],
                _MODEL_COST_REFERENCE,
            ),
            "locked_repository_baseline": _exact_commit(
                "locked_repository_baseline",
                fields["locked_repository_baseline"],
                _LOCKED_REPOSITORY_BASELINE,
            ),
            "locked_phase09_baseline": _exact_commit(
                "locked_phase09_baseline",
                fields["locked_phase09_baseline"],
                _LOCKED_PHASE09_BASELINE,
            ),
            "credential_requirements": normalized_requirements,
            "gate_state": _exact_enum(
                "gate_state",
                fields["gate_state"],
                ShadowPhase11CredentialSafeLaunchGateStateV1,
                ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED,
            ),
            "maximum_attempts": _exact_int(
                "maximum_attempts",
                fields["maximum_attempts"],
                1,
            ),
            "blocker_codes": _BLOCKERS,
            "reason_codes": _reason_codes(fields["reason_codes"]),
        }
        for name, evidence_identity in (
            ("pricing_evidence_identity", pricing.identity),
            ("reservation_bound_identity", reservation.identity),
        ):
            candidate = fields[name]
            if (
                type(candidate) is not str
                or _HASH.fullmatch(candidate) is None
                or candidate != evidence_identity
            ):
                raise ShadowPhase11CredentialSafeLaunchGateValidationError(
                    f"invalid {name}"
                )
            values[name] = candidate
        for name in (
            "credential_configuration_verified",
            "credential_material_accessed",
            "account_state_accessed",
            "credential_validation_endpoint_called",
            "provider_call_authorized",
            "provider_transmission_authorized",
            "run_size_authorized",
            "reservation_creation_authorized",
            "ledger_mutation_authorized",
            "launch_authorized",
            "production_authorized",
            "provider_retry_authorized",
            "credential_retry_authorized",
            "authentication_retry_authorized",
            "fixed_freshness_window_defined",
            "pilot_input_present",
            "run_manifest_present",
            "runtime_no_retry_enforcement_verified",
            "authentication_terminal_classification_verified",
        ):
            values[name] = _exact_bool(name, fields[name], False)
        for name in (
            "credential_failure_terminal_required",
            "authentication_failure_terminal_required",
            "pricing_revalidation_required_before_reservation_use",
            "launch_time_pricing_revalidation_required",
            "reservation_required_before_provider_transmission",
        ):
            values[name] = _exact_bool(name, fields[name], True)
        values["pricing_revalidation_status"] = _exact_enum(
            "pricing_revalidation_status",
            fields["pricing_revalidation_status"],
            ShadowPhase11PilotPricingRevalidationStatusV1,
            pricing.pricing_revalidation_status,
        )
        values["reservation_state"] = _exact_enum(
            "reservation_state",
            fields["reservation_state"],
            ShadowPhase11PreCallReservationStateV1,
            reservation.reservation_state,
        )
        values["launch_readiness"] = _exact_enum(
            "launch_readiness",
            fields["launch_readiness"],
            ShadowPhase11PilotLaunchReadinessV1,
            pricing.launch_readiness,
        )
        values["budget_reserved_micro_usd"] = _exact_decimal(
            "budget_reserved_micro_usd",
            fields["budget_reserved_micro_usd"],
            reservation.budget_reserved_micro_usd,
        )
        values["budget_consumed_micro_usd"] = _exact_decimal(
            "budget_consumed_micro_usd",
            fields["budget_consumed_micro_usd"],
            reservation.budget_consumed_micro_usd,
        )
        values["production_effect"] = _exact_text(
            "production_effect",
            fields["production_effect"],
            pricing.production_effect,
        )
        values["zero_production_effect_proof"] = _exact_text(
            "zero_production_effect_proof",
            fields["zero_production_effect_proof"],
            pricing.zero_production_effect_proof,
        )
        values["gate_id"] = _identity(
            {**values, "gate_id": None},
            fields["gate_id"],
            "gate_id",
        )
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def identity(self) -> str:
        return self.gate_id


def _requirement(
    provider: str,
    roles: tuple[ShadowPhase11PilotProviderRoleV1, ...],
) -> ShadowPhase11CredentialRequirementV1:
    return ShadowPhase11CredentialRequirementV1(
        schema_version=_REQUIREMENT_SCHEMA,
        requirement_id=None,
        provider=provider,
        roles=roles,
        credential_required=True,
        verification_state=(
            ShadowPhase11CredentialVerificationStateV1.NOT_VERIFIED
        ),
        credential_reference_present=False,
        credential_material_present=False,
        credential_access_attempted=False,
        account_access_attempted=False,
        credential_validation_endpoint_called=False,
        provider_call_authorized=False,
        maximum_attempts=1,
        provider_retry_authorized=False,
        credential_retry_authorized=False,
        authentication_retry_authorized=False,
        credential_failure_terminal_required=True,
        authentication_failure_terminal_required=True,
        reason_codes=("CREDENTIAL_CONFIGURATION_NOT_VERIFIED",),
    )


_REQUIREMENTS = (
    _requirement("DEEPSEEK", _PROVIDER_ROLES["DEEPSEEK"]),
    _requirement("ANTHROPIC", _PROVIDER_ROLES["ANTHROPIC"]),
)


def _concrete_gate() -> ShadowPhase11CredentialSafeLaunchGateV1:
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    return ShadowPhase11CredentialSafeLaunchGateV1(
        schema_version=_GATE_SCHEMA,
        gate_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        pricing_evidence_reference=pricing.evidence_reference,
        pricing_evidence_identity=pricing.identity,
        reservation_bound_reference=reservation.evidence_reference,
        reservation_bound_identity=reservation.identity,
        budget_authorization_reference=_BUDGET_REFERENCE,
        model_cost_authorization_reference=_MODEL_COST_REFERENCE,
        locked_repository_baseline=_LOCKED_REPOSITORY_BASELINE,
        locked_phase09_baseline=_LOCKED_PHASE09_BASELINE,
        credential_requirements=_REQUIREMENTS,
        gate_state=ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED,
        credential_configuration_verified=False,
        credential_material_accessed=False,
        account_state_accessed=False,
        credential_validation_endpoint_called=False,
        provider_call_authorized=False,
        provider_transmission_authorized=False,
        run_size_authorized=False,
        reservation_creation_authorized=False,
        ledger_mutation_authorized=False,
        launch_authorized=False,
        production_authorized=False,
        maximum_attempts=1,
        provider_retry_authorized=False,
        credential_retry_authorized=False,
        authentication_retry_authorized=False,
        credential_failure_terminal_required=True,
        authentication_failure_terminal_required=True,
        pricing_revalidation_required_before_reservation_use=True,
        launch_time_pricing_revalidation_required=True,
        fixed_freshness_window_defined=False,
        pricing_revalidation_status=pricing.pricing_revalidation_status,
        reservation_state=reservation.reservation_state,
        reservation_required_before_provider_transmission=True,
        budget_reserved_micro_usd=reservation.budget_reserved_micro_usd,
        budget_consumed_micro_usd=reservation.budget_consumed_micro_usd,
        pilot_input_present=False,
        run_manifest_present=False,
        runtime_no_retry_enforcement_verified=False,
        authentication_terminal_classification_verified=False,
        launch_readiness=pricing.launch_readiness,
        production_effect=pricing.production_effect,
        zero_production_effect_proof=pricing.zero_production_effect_proof,
        blocker_codes=_BLOCKERS,
        reason_codes=("CREDENTIAL_SAFE_GATE_BLOCKED",),
    )


_GATE = _concrete_gate()


def get_phase_11_shadow_pilot_credential_safe_launch_gate_v1(
) -> ShadowPhase11CredentialSafeLaunchGateV1:
    """Return deterministic blocked gate evidence with no launch authority."""

    return _GATE


__all__ = [
    "ShadowPhase11CredentialRequirementV1",
    "ShadowPhase11CredentialSafeLaunchGateStateV1",
    "ShadowPhase11CredentialSafeLaunchGateV1",
    "ShadowPhase11CredentialSafeLaunchGateValidationError",
    "ShadowPhase11CredentialVerificationStateV1",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_credential_safe_launch_gate_v1",
    "sha256_hex",
]
