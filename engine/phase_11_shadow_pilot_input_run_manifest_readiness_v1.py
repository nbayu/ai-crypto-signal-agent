"""Immutable Phase 11 pilot input and proposed-manifest readiness evidence.

This module stores deterministic repository-owned metadata only.  It creates
no executable input, provider request, reservation, ledger entry, active
manifest, runtime invocation, or operational authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

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


_ITEM_SCHEMA = "phase11-shadow-pilot-input-item-v1"
_MANIFEST_SCHEMA = "phase11-shadow-pilot-run-manifest-v1"
_EVIDENCE_SCHEMA = (
    "phase11-shadow-pilot-input-run-manifest-readiness-v1"
)
_MANIFEST_REFERENCE = "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001"
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
_REPOSITORY_BASELINE = "9ba0927b5ad58e29a8dd9fd8c3416a871d5ed9db"
_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"

_GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
_GATE_IDENTITY = (
    "29a07dc2cb644aeb4dbdc9dc00e4da79b5fa3d1486e98dabdcadb1e40140debb"
)
_RUNTIME_REFERENCE = (
    "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
)
_RUNTIME_IDENTITY = (
    "45d1446eb173d399f748b3b11e616d51391947762d3b36848cbd4f3d5b3228ab"
)
_PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
_PRICING_IDENTITY = (
    "2ffbb1d04538bbf481d287b9629757fcde17a3d59779a1cef367e1752d673014"
)
_RESERVATION_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
_RESERVATION_IDENTITY = (
    "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4"
)

_CANDIDATE_COUNT = 20
_MAXIMUM_INPUT_TOKENS = 16000
_MAXIMUM_OUTPUT_TOKENS = 2000
_MAXIMUM_ATTEMPTS = 1
_ITEM_MAXIMUM_MICRO_USD = Decimal("216700")
_TOTAL_MAXIMUM_MICRO_USD = Decimal("4334000")
_HARD_CAP_MICRO_USD = Decimal("5000000")
_SAFETY_RESERVE_MICRO_USD = Decimal("500000")
_MAXIMUM_SPENDABLE_MICRO_USD = Decimal("4500000")
_ROLES = (
    ShadowPhase11PilotProviderRoleV1.PRIMARY,
    ShadowPhase11PilotProviderRoleV1.L1,
    ShadowPhase11PilotProviderRoleV1.L2,
)
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ShadowPhase11PilotInputRunManifestReadinessValidationError(ValueError):
    """Raised when immutable input/manifest readiness evidence is invalid."""


class ShadowPhase11PilotInputReadinessStateV1(StrEnum):
    """The sole input-readiness state authorized by this evidence."""

    CANDIDATE_INPUT_DEFINED_NOT_AUTHORIZED = (
        "CANDIDATE_INPUT_DEFINED_NOT_AUTHORIZED"
    )


class ShadowPhase11PilotManifestReadinessStateV1(StrEnum):
    """The sole proposed-manifest state authorized by this evidence."""

    PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED = (
        "PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED"
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
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
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
    raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
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
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest for exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            "sha256 input must be bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, field_name: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            f"{field_name} must equal the locked value"
        )


def _exact_bool(value: Any, expected: bool, field_name: str) -> None:
    if type(value) is not bool or value is not expected:
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            f"{field_name} must be {expected}"
        )


def _exact_int(value: Any, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            f"{field_name} must equal {expected}"
        )


def _exact_decimal(
    value: Any,
    expected: Decimal,
    field_name: str,
) -> None:
    if type(value) is not Decimal or value != expected or not value.is_finite():
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            f"{field_name} must equal the locked micro-USD value"
        )


def _reason_codes(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            "reason_codes must be a non-empty sequence"
        )
    if any(type(code) is not str or _REASON.fullmatch(code) is None for code in value):
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            "reason_codes contain an invalid value"
        )
    if len(set(value)) != len(value):
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            "reason_codes must be unique"
        )
    return tuple(sorted(value))


def _supplied_identity(value: Any, computed: str, field_name: str) -> str:
    if _HASH.fullmatch(computed) is None:
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            f"{field_name} computation failed"
        )
    if value is not None and (type(value) is not str or value != computed):
        raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
            f"{field_name} does not match canonical material"
        )
    return computed


def _item_payload(item: "ShadowPhase11PilotInputItemV1") -> dict[str, Any]:
    return {
        "schema_version": item.schema_version,
        "item_reference": item.item_reference,
        "ordinal": item.ordinal,
        "intended_route": item.intended_route,
        "required_provider_roles": item.required_provider_roles,
        "maximum_input_tokens": item.maximum_input_tokens,
        "maximum_output_tokens": item.maximum_output_tokens,
        "maximum_attempts": item.maximum_attempts,
        "conservative_maximum_micro_usd": (
            item.conservative_maximum_micro_usd
        ),
        "input_content_present": item.input_content_present,
        "credential_reference_present": item.credential_reference_present,
        "credential_material_present": item.credential_material_present,
        "provider_request_created": item.provider_request_created,
        "provider_transmission_authorized": (
            item.provider_transmission_authorized
        ),
        "reservation_bound": item.reservation_bound,
        "reason_codes": item.reason_codes,
    }


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11PilotInputItemV1:
    """One deterministic metadata-only candidate pilot input item."""

    schema_version: str
    item_id: str
    item_reference: str
    ordinal: int
    intended_route: ShadowPhase11PilotRouteV1
    required_provider_roles: tuple[ShadowPhase11PilotProviderRoleV1, ...]
    maximum_input_tokens: int
    maximum_output_tokens: int
    maximum_attempts: int
    conservative_maximum_micro_usd: Decimal
    input_content_present: bool
    credential_reference_present: bool
    credential_material_present: bool
    provider_request_created: bool
    provider_transmission_authorized: bool
    reservation_bound: bool
    reason_codes: tuple[str, ...]

    def __init__(
        self,
        *,
        schema_version: str,
        item_id: str | None,
        item_reference: str,
        ordinal: int,
        intended_route: ShadowPhase11PilotRouteV1,
        required_provider_roles: tuple[
            ShadowPhase11PilotProviderRoleV1, ...
        ],
        maximum_input_tokens: int,
        maximum_output_tokens: int,
        maximum_attempts: int,
        conservative_maximum_micro_usd: Decimal,
        input_content_present: bool,
        credential_reference_present: bool,
        credential_material_present: bool,
        provider_request_created: bool,
        provider_transmission_authorized: bool,
        reservation_bound: bool,
        reason_codes: tuple[str, ...],
        **unknown_fields: Any,
    ) -> None:
        if unknown_fields:
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "unknown candidate item fields are forbidden"
            )
        _exact(schema_version, _ITEM_SCHEMA, "schema_version")
        if type(ordinal) is not int or ordinal < 1:
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "ordinal must be a positive integer"
            )
        expected_reference = (
            f"PHASE11_PILOT_READINESS_ITEM_{ordinal:03d}"
        )
        _exact(item_reference, expected_reference, "item_reference")
        if intended_route is not ShadowPhase11PilotRouteV1.L1_TO_L2:
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "intended_route must be L1_TO_L2"
            )
        if type(required_provider_roles) not in (tuple, list):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "required_provider_roles must be a sequence"
            )
        roles = tuple(required_provider_roles)
        if len(roles) != len(_ROLES) or any(
            actual is not expected
            for actual, expected in zip(roles, _ROLES, strict=True)
        ):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "required_provider_roles must be PRIMARY, L1, L2"
            )
        _exact_int(
            maximum_input_tokens,
            _MAXIMUM_INPUT_TOKENS,
            "maximum_input_tokens",
        )
        _exact_int(
            maximum_output_tokens,
            _MAXIMUM_OUTPUT_TOKENS,
            "maximum_output_tokens",
        )
        _exact_int(maximum_attempts, _MAXIMUM_ATTEMPTS, "maximum_attempts")
        _exact_decimal(
            conservative_maximum_micro_usd,
            _ITEM_MAXIMUM_MICRO_USD,
            "conservative_maximum_micro_usd",
        )
        for field_name, value in (
            ("input_content_present", input_content_present),
            ("credential_reference_present", credential_reference_present),
            ("credential_material_present", credential_material_present),
            ("provider_request_created", provider_request_created),
            (
                "provider_transmission_authorized",
                provider_transmission_authorized,
            ),
            ("reservation_bound", reservation_bound),
        ):
            _exact_bool(value, False, field_name)
        normalized_reasons = _reason_codes(reason_codes)

        for name, value in (
            ("schema_version", schema_version),
            ("item_reference", item_reference),
            ("ordinal", ordinal),
            ("intended_route", intended_route),
            ("required_provider_roles", roles),
            ("maximum_input_tokens", maximum_input_tokens),
            ("maximum_output_tokens", maximum_output_tokens),
            ("maximum_attempts", maximum_attempts),
            (
                "conservative_maximum_micro_usd",
                conservative_maximum_micro_usd,
            ),
            ("input_content_present", input_content_present),
            ("credential_reference_present", credential_reference_present),
            ("credential_material_present", credential_material_present),
            ("provider_request_created", provider_request_created),
            (
                "provider_transmission_authorized",
                provider_transmission_authorized,
            ),
            ("reservation_bound", reservation_bound),
            ("reason_codes", normalized_reasons),
        ):
            object.__setattr__(self, name, value)
        computed = sha256_hex(canonical_json_bytes(_item_payload(self)))
        object.__setattr__(
            self,
            "item_id",
            _supplied_identity(item_id, computed, "item_id"),
        )

    @property
    def identity(self) -> str:
        return self.item_id


def _make_item(ordinal: int) -> ShadowPhase11PilotInputItemV1:
    return ShadowPhase11PilotInputItemV1(
        schema_version=_ITEM_SCHEMA,
        item_id=None,
        item_reference=f"PHASE11_PILOT_READINESS_ITEM_{ordinal:03d}",
        ordinal=ordinal,
        intended_route=ShadowPhase11PilotRouteV1.L1_TO_L2,
        required_provider_roles=_ROLES,
        maximum_input_tokens=_MAXIMUM_INPUT_TOKENS,
        maximum_output_tokens=_MAXIMUM_OUTPUT_TOKENS,
        maximum_attempts=_MAXIMUM_ATTEMPTS,
        conservative_maximum_micro_usd=_ITEM_MAXIMUM_MICRO_USD,
        input_content_present=False,
        credential_reference_present=False,
        credential_material_present=False,
        provider_request_created=False,
        provider_transmission_authorized=False,
        reservation_bound=False,
        reason_codes=("CANDIDATE_METADATA_ONLY",),
    )


_CANDIDATE_ITEMS = tuple(
    _make_item(ordinal) for ordinal in range(1, _CANDIDATE_COUNT + 1)
)
_CANDIDATE_IDENTITIES = tuple(item.identity for item in _CANDIDATE_ITEMS)
_CANDIDATE_IDENTITY_ORDER = {
    identity: index for index, identity in enumerate(_CANDIDATE_IDENTITIES)
}
_CANDIDATE_INPUT_SET_IDENTITY = sha256_hex(
    canonical_json_bytes(
        {"candidate_item_identities": _CANDIDATE_IDENTITIES}
    )
)


def _manifest_payload(
    manifest: "ShadowPhase11PilotRunManifestV1",
) -> dict[str, Any]:
    return {
        "schema_version": manifest.schema_version,
        "manifest_reference": manifest.manifest_reference,
        "manifest_readiness_state": manifest.manifest_readiness_state,
        "candidate_input_set_identity": (
            manifest.candidate_input_set_identity
        ),
        "candidate_item_identities": manifest.candidate_item_identities,
        "candidate_count": manifest.candidate_count,
        "maximum_worst_case_cost_per_item_micro_usd": (
            manifest.maximum_worst_case_cost_per_item_micro_usd
        ),
        "total_worst_case_maximum_micro_usd": (
            manifest.total_worst_case_maximum_micro_usd
        ),
        "hard_cap_micro_usd": manifest.hard_cap_micro_usd,
        "safety_reserve_micro_usd": manifest.safety_reserve_micro_usd,
        "maximum_spendable_micro_usd": (
            manifest.maximum_spendable_micro_usd
        ),
        "reservation_required_before_transmission": (
            manifest.reservation_required_before_transmission
        ),
        "launch_time_pricing_revalidation_required": (
            manifest.launch_time_pricing_revalidation_required
        ),
        "pricing_revalidation_completed": (
            manifest.pricing_revalidation_completed
        ),
        "reservation_created": manifest.reservation_created,
        "ledger_entry_created": manifest.ledger_entry_created,
        "provider_requests_created": manifest.provider_requests_created,
        "manifest_activated": manifest.manifest_activated,
        "runtime_invocation_authorized": (
            manifest.runtime_invocation_authorized
        ),
        "provider_transmission_authorized": (
            manifest.provider_transmission_authorized
        ),
        "launch_authorized": manifest.launch_authorized,
        "production_authorized": manifest.production_authorized,
        "reason_codes": manifest.reason_codes,
    }


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11PilotRunManifestV1:
    """One deterministic, proposed, non-activated pilot manifest."""

    schema_version: str
    manifest_id: str
    manifest_reference: str
    manifest_readiness_state: ShadowPhase11PilotManifestReadinessStateV1
    candidate_input_set_identity: str
    candidate_item_identities: tuple[str, ...]
    candidate_count: int
    maximum_worst_case_cost_per_item_micro_usd: Decimal
    total_worst_case_maximum_micro_usd: Decimal
    hard_cap_micro_usd: Decimal
    safety_reserve_micro_usd: Decimal
    maximum_spendable_micro_usd: Decimal
    reservation_required_before_transmission: bool
    launch_time_pricing_revalidation_required: bool
    pricing_revalidation_completed: bool
    reservation_created: bool
    ledger_entry_created: bool
    provider_requests_created: bool
    manifest_activated: bool
    runtime_invocation_authorized: bool
    provider_transmission_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    reason_codes: tuple[str, ...]

    def __init__(
        self,
        *,
        schema_version: str,
        manifest_id: str | None,
        manifest_reference: str,
        manifest_readiness_state: ShadowPhase11PilotManifestReadinessStateV1,
        candidate_input_set_identity: str,
        candidate_item_identities: tuple[str, ...],
        candidate_count: int,
        maximum_worst_case_cost_per_item_micro_usd: Decimal,
        total_worst_case_maximum_micro_usd: Decimal,
        hard_cap_micro_usd: Decimal,
        safety_reserve_micro_usd: Decimal,
        maximum_spendable_micro_usd: Decimal,
        reservation_required_before_transmission: bool,
        launch_time_pricing_revalidation_required: bool,
        pricing_revalidation_completed: bool,
        reservation_created: bool,
        ledger_entry_created: bool,
        provider_requests_created: bool,
        manifest_activated: bool,
        runtime_invocation_authorized: bool,
        provider_transmission_authorized: bool,
        launch_authorized: bool,
        production_authorized: bool,
        reason_codes: tuple[str, ...],
        **unknown_fields: Any,
    ) -> None:
        if unknown_fields:
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "unknown proposed manifest fields are forbidden"
            )
        _exact(schema_version, _MANIFEST_SCHEMA, "schema_version")
        _exact(manifest_reference, _MANIFEST_REFERENCE, "manifest_reference")
        if (
            manifest_readiness_state
            is not ShadowPhase11PilotManifestReadinessStateV1
            .PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED
        ):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "manifest_readiness_state is not the proposed state"
            )
        _exact(
            candidate_input_set_identity,
            _CANDIDATE_INPUT_SET_IDENTITY,
            "candidate_input_set_identity",
        )
        if type(candidate_item_identities) not in (tuple, list):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "candidate_item_identities must be a sequence"
            )
        identities = tuple(candidate_item_identities)
        if (
            len(identities) != _CANDIDATE_COUNT
            or len(set(identities)) != _CANDIDATE_COUNT
            or set(identities) != set(_CANDIDATE_IDENTITIES)
        ):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "candidate_item_identities must bind the exact candidate set"
            )
        normalized_identities = tuple(
            sorted(
                identities,
                key=lambda identity: _CANDIDATE_IDENTITY_ORDER[identity],
            )
        )
        _exact_int(candidate_count, _CANDIDATE_COUNT, "candidate_count")
        _exact_decimal(
            maximum_worst_case_cost_per_item_micro_usd,
            _ITEM_MAXIMUM_MICRO_USD,
            "maximum_worst_case_cost_per_item_micro_usd",
        )
        _exact_decimal(
            total_worst_case_maximum_micro_usd,
            _TOTAL_MAXIMUM_MICRO_USD,
            "total_worst_case_maximum_micro_usd",
        )
        _exact_decimal(
            hard_cap_micro_usd,
            _HARD_CAP_MICRO_USD,
            "hard_cap_micro_usd",
        )
        _exact_decimal(
            safety_reserve_micro_usd,
            _SAFETY_RESERVE_MICRO_USD,
            "safety_reserve_micro_usd",
        )
        _exact_decimal(
            maximum_spendable_micro_usd,
            _MAXIMUM_SPENDABLE_MICRO_USD,
            "maximum_spendable_micro_usd",
        )
        _exact_bool(
            reservation_required_before_transmission,
            True,
            "reservation_required_before_transmission",
        )
        _exact_bool(
            launch_time_pricing_revalidation_required,
            True,
            "launch_time_pricing_revalidation_required",
        )
        for field_name, value in (
            ("pricing_revalidation_completed", pricing_revalidation_completed),
            ("reservation_created", reservation_created),
            ("ledger_entry_created", ledger_entry_created),
            ("provider_requests_created", provider_requests_created),
            ("manifest_activated", manifest_activated),
            ("runtime_invocation_authorized", runtime_invocation_authorized),
            (
                "provider_transmission_authorized",
                provider_transmission_authorized,
            ),
            ("launch_authorized", launch_authorized),
            ("production_authorized", production_authorized),
        ):
            _exact_bool(value, False, field_name)
        normalized_reasons = _reason_codes(reason_codes)

        values = {
            "schema_version": schema_version,
            "manifest_reference": manifest_reference,
            "manifest_readiness_state": manifest_readiness_state,
            "candidate_input_set_identity": candidate_input_set_identity,
            "candidate_item_identities": normalized_identities,
            "candidate_count": candidate_count,
            "maximum_worst_case_cost_per_item_micro_usd": (
                maximum_worst_case_cost_per_item_micro_usd
            ),
            "total_worst_case_maximum_micro_usd": (
                total_worst_case_maximum_micro_usd
            ),
            "hard_cap_micro_usd": hard_cap_micro_usd,
            "safety_reserve_micro_usd": safety_reserve_micro_usd,
            "maximum_spendable_micro_usd": maximum_spendable_micro_usd,
            "reservation_required_before_transmission": (
                reservation_required_before_transmission
            ),
            "launch_time_pricing_revalidation_required": (
                launch_time_pricing_revalidation_required
            ),
            "pricing_revalidation_completed": pricing_revalidation_completed,
            "reservation_created": reservation_created,
            "ledger_entry_created": ledger_entry_created,
            "provider_requests_created": provider_requests_created,
            "manifest_activated": manifest_activated,
            "runtime_invocation_authorized": runtime_invocation_authorized,
            "provider_transmission_authorized": (
                provider_transmission_authorized
            ),
            "launch_authorized": launch_authorized,
            "production_authorized": production_authorized,
            "reason_codes": normalized_reasons,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)
        computed = sha256_hex(canonical_json_bytes(_manifest_payload(self)))
        object.__setattr__(
            self,
            "manifest_id",
            _supplied_identity(manifest_id, computed, "manifest_id"),
        )

    @property
    def identity(self) -> str:
        return self.manifest_id


def _make_manifest() -> ShadowPhase11PilotRunManifestV1:
    return ShadowPhase11PilotRunManifestV1(
        schema_version=_MANIFEST_SCHEMA,
        manifest_id=None,
        manifest_reference=_MANIFEST_REFERENCE,
        manifest_readiness_state=(
            ShadowPhase11PilotManifestReadinessStateV1
            .PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED
        ),
        candidate_input_set_identity=_CANDIDATE_INPUT_SET_IDENTITY,
        candidate_item_identities=_CANDIDATE_IDENTITIES,
        candidate_count=_CANDIDATE_COUNT,
        maximum_worst_case_cost_per_item_micro_usd=(
            _ITEM_MAXIMUM_MICRO_USD
        ),
        total_worst_case_maximum_micro_usd=_TOTAL_MAXIMUM_MICRO_USD,
        hard_cap_micro_usd=_HARD_CAP_MICRO_USD,
        safety_reserve_micro_usd=_SAFETY_RESERVE_MICRO_USD,
        maximum_spendable_micro_usd=_MAXIMUM_SPENDABLE_MICRO_USD,
        reservation_required_before_transmission=True,
        launch_time_pricing_revalidation_required=True,
        pricing_revalidation_completed=False,
        reservation_created=False,
        ledger_entry_created=False,
        provider_requests_created=False,
        manifest_activated=False,
        runtime_invocation_authorized=False,
        provider_transmission_authorized=False,
        launch_authorized=False,
        production_authorized=False,
        reason_codes=("PROPOSED_MANIFEST_METADATA_ONLY",),
    )


_PROPOSED_MANIFEST = _make_manifest()


def _evidence_payload(
    evidence: "ShadowPhase11PilotInputRunManifestReadinessEvidenceV1",
) -> dict[str, Any]:
    return {
        "schema_version": evidence.schema_version,
        "evidence_reference": evidence.evidence_reference,
        "locked_repository_baseline": evidence.locked_repository_baseline,
        "locked_phase09_baseline": evidence.locked_phase09_baseline,
        "credential_safe_gate_reference": (
            evidence.credential_safe_gate_reference
        ),
        "credential_safe_gate_identity": (
            evidence.credential_safe_gate_identity
        ),
        "current_runtime_integrity_reference": (
            evidence.current_runtime_integrity_reference
        ),
        "current_runtime_integrity_identity": (
            evidence.current_runtime_integrity_identity
        ),
        "pricing_evidence_reference": evidence.pricing_evidence_reference,
        "pricing_evidence_identity": evidence.pricing_evidence_identity,
        "reservation_bound_reference": evidence.reservation_bound_reference,
        "reservation_bound_identity": evidence.reservation_bound_identity,
        "input_readiness_state": evidence.input_readiness_state,
        "manifest_readiness_state": evidence.manifest_readiness_state,
        "candidate_item_identities": tuple(
            item.identity for item in evidence.candidate_items
        ),
        "proposed_manifest_identity": evidence.proposed_manifest.identity,
        "candidate_input_defined": evidence.candidate_input_defined,
        "executable_input_content_present": (
            evidence.executable_input_content_present
        ),
        "run_manifest_defined": evidence.run_manifest_defined,
        "run_manifest_activated": evidence.run_manifest_activated,
        "credential_configuration_verified": (
            evidence.credential_configuration_verified
        ),
        "pricing_revalidation_completed": (
            evidence.pricing_revalidation_completed
        ),
        "pre_call_reservation_created": (
            evidence.pre_call_reservation_created
        ),
        "ledger_entry_created": evidence.ledger_entry_created,
        "provider_request_created": evidence.provider_request_created,
        "provider_call_authorized": evidence.provider_call_authorized,
        "provider_transmission_authorized": (
            evidence.provider_transmission_authorized
        ),
        "runtime_invocation_authorized": (
            evidence.runtime_invocation_authorized
        ),
        "run_size_authorized": evidence.run_size_authorized,
        "launch_authorized": evidence.launch_authorized,
        "production_authorized": evidence.production_authorized,
        "launch_readiness": evidence.launch_readiness,
        "production_effect": evidence.production_effect,
        "zero_production_effect_proof": (
            evidence.zero_production_effect_proof
        ),
        "reason_codes": evidence.reason_codes,
    }


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11PilotInputRunManifestReadinessEvidenceV1:
    """Static evidence for candidate metadata and a proposed manifest."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    credential_safe_gate_reference: str
    credential_safe_gate_identity: str
    current_runtime_integrity_reference: str
    current_runtime_integrity_identity: str
    pricing_evidence_reference: str
    pricing_evidence_identity: str
    reservation_bound_reference: str
    reservation_bound_identity: str
    input_readiness_state: ShadowPhase11PilotInputReadinessStateV1
    manifest_readiness_state: ShadowPhase11PilotManifestReadinessStateV1
    candidate_items: tuple[ShadowPhase11PilotInputItemV1, ...]
    proposed_manifest: ShadowPhase11PilotRunManifestV1
    candidate_input_defined: bool
    executable_input_content_present: bool
    run_manifest_defined: bool
    run_manifest_activated: bool
    credential_configuration_verified: bool
    pricing_revalidation_completed: bool
    pre_call_reservation_created: bool
    ledger_entry_created: bool
    provider_request_created: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    runtime_invocation_authorized: bool
    run_size_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    production_effect: str
    zero_production_effect_proof: str
    reason_codes: tuple[str, ...]

    def __init__(
        self,
        *,
        schema_version: str,
        evidence_id: str | None,
        evidence_reference: str,
        locked_repository_baseline: str,
        locked_phase09_baseline: str,
        credential_safe_gate_reference: str,
        credential_safe_gate_identity: str,
        current_runtime_integrity_reference: str,
        current_runtime_integrity_identity: str,
        pricing_evidence_reference: str,
        pricing_evidence_identity: str,
        reservation_bound_reference: str,
        reservation_bound_identity: str,
        input_readiness_state: ShadowPhase11PilotInputReadinessStateV1,
        manifest_readiness_state: ShadowPhase11PilotManifestReadinessStateV1,
        candidate_items: tuple[ShadowPhase11PilotInputItemV1, ...],
        proposed_manifest: ShadowPhase11PilotRunManifestV1,
        candidate_input_defined: bool,
        executable_input_content_present: bool,
        run_manifest_defined: bool,
        run_manifest_activated: bool,
        credential_configuration_verified: bool,
        pricing_revalidation_completed: bool,
        pre_call_reservation_created: bool,
        ledger_entry_created: bool,
        provider_request_created: bool,
        provider_call_authorized: bool,
        provider_transmission_authorized: bool,
        runtime_invocation_authorized: bool,
        run_size_authorized: bool,
        launch_authorized: bool,
        production_authorized: bool,
        launch_readiness: ShadowPhase11PilotLaunchReadinessV1,
        production_effect: str,
        zero_production_effect_proof: str,
        reason_codes: tuple[str, ...],
        **unknown_fields: Any,
    ) -> None:
        if unknown_fields:
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "unknown readiness evidence fields are forbidden"
            )
        for field_name, value, expected in (
            ("schema_version", schema_version, _EVIDENCE_SCHEMA),
            ("evidence_reference", evidence_reference, _EVIDENCE_REFERENCE),
            (
                "locked_repository_baseline",
                locked_repository_baseline,
                _REPOSITORY_BASELINE,
            ),
            ("locked_phase09_baseline", locked_phase09_baseline, _PHASE09_BASELINE),
            (
                "credential_safe_gate_reference",
                credential_safe_gate_reference,
                _GATE_REFERENCE,
            ),
            (
                "credential_safe_gate_identity",
                credential_safe_gate_identity,
                _GATE_IDENTITY,
            ),
            (
                "current_runtime_integrity_reference",
                current_runtime_integrity_reference,
                _RUNTIME_REFERENCE,
            ),
            (
                "current_runtime_integrity_identity",
                current_runtime_integrity_identity,
                _RUNTIME_IDENTITY,
            ),
            (
                "pricing_evidence_reference",
                pricing_evidence_reference,
                _PRICING_REFERENCE,
            ),
            (
                "pricing_evidence_identity",
                pricing_evidence_identity,
                _PRICING_IDENTITY,
            ),
            (
                "reservation_bound_reference",
                reservation_bound_reference,
                _RESERVATION_REFERENCE,
            ),
            (
                "reservation_bound_identity",
                reservation_bound_identity,
                _RESERVATION_IDENTITY,
            ),
        ):
            _exact(value, expected, field_name)
        if (
            input_readiness_state
            is not ShadowPhase11PilotInputReadinessStateV1
            .CANDIDATE_INPUT_DEFINED_NOT_AUTHORIZED
        ):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "input_readiness_state is not the candidate state"
            )
        if (
            manifest_readiness_state
            is not ShadowPhase11PilotManifestReadinessStateV1
            .PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED
        ):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "manifest_readiness_state is not the proposed state"
            )
        if type(candidate_items) not in (tuple, list):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "candidate_items must be a sequence"
            )
        items = tuple(candidate_items)
        if (
            len(items) != _CANDIDATE_COUNT
            or any(
                type(item) is not ShadowPhase11PilotInputItemV1
                for item in items
            )
            or len({item.item_reference for item in items}) != _CANDIDATE_COUNT
            or len({item.ordinal for item in items}) != _CANDIDATE_COUNT
        ):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "candidate_items must contain 20 unique input items"
            )
        normalized_items = tuple(
            sorted(items, key=lambda item: (item.ordinal, item.item_reference))
        )
        if tuple(item.identity for item in normalized_items) != _CANDIDATE_IDENTITIES:
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "candidate_items do not match the locked candidate set"
            )
        if (
            type(proposed_manifest) is not ShadowPhase11PilotRunManifestV1
            or proposed_manifest.identity != _PROPOSED_MANIFEST.identity
        ):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "proposed_manifest does not match the locked manifest"
            )
        _exact_bool(candidate_input_defined, True, "candidate_input_defined")
        _exact_bool(
            executable_input_content_present,
            False,
            "executable_input_content_present",
        )
        _exact_bool(run_manifest_defined, True, "run_manifest_defined")
        for field_name, value in (
            ("run_manifest_activated", run_manifest_activated),
            (
                "credential_configuration_verified",
                credential_configuration_verified,
            ),
            ("pricing_revalidation_completed", pricing_revalidation_completed),
            ("pre_call_reservation_created", pre_call_reservation_created),
            ("ledger_entry_created", ledger_entry_created),
            ("provider_request_created", provider_request_created),
            ("provider_call_authorized", provider_call_authorized),
            (
                "provider_transmission_authorized",
                provider_transmission_authorized,
            ),
            ("runtime_invocation_authorized", runtime_invocation_authorized),
            ("run_size_authorized", run_size_authorized),
            ("launch_authorized", launch_authorized),
            ("production_authorized", production_authorized),
        ):
            _exact_bool(value, False, field_name)
        if (
            launch_readiness
            is not ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ):
            raise ShadowPhase11PilotInputRunManifestReadinessValidationError(
                "launch_readiness must remain NOT_READY_FOR_LAUNCH"
            )
        _exact(production_effect, "NONE", "production_effect")
        _exact(
            zero_production_effect_proof,
            "PROVEN_NONE",
            "zero_production_effect_proof",
        )
        normalized_reasons = _reason_codes(reason_codes)

        values = {
            "schema_version": schema_version,
            "evidence_reference": evidence_reference,
            "locked_repository_baseline": locked_repository_baseline,
            "locked_phase09_baseline": locked_phase09_baseline,
            "credential_safe_gate_reference": credential_safe_gate_reference,
            "credential_safe_gate_identity": credential_safe_gate_identity,
            "current_runtime_integrity_reference": (
                current_runtime_integrity_reference
            ),
            "current_runtime_integrity_identity": (
                current_runtime_integrity_identity
            ),
            "pricing_evidence_reference": pricing_evidence_reference,
            "pricing_evidence_identity": pricing_evidence_identity,
            "reservation_bound_reference": reservation_bound_reference,
            "reservation_bound_identity": reservation_bound_identity,
            "input_readiness_state": input_readiness_state,
            "manifest_readiness_state": manifest_readiness_state,
            "candidate_items": normalized_items,
            "proposed_manifest": proposed_manifest,
            "candidate_input_defined": candidate_input_defined,
            "executable_input_content_present": (
                executable_input_content_present
            ),
            "run_manifest_defined": run_manifest_defined,
            "run_manifest_activated": run_manifest_activated,
            "credential_configuration_verified": (
                credential_configuration_verified
            ),
            "pricing_revalidation_completed": pricing_revalidation_completed,
            "pre_call_reservation_created": pre_call_reservation_created,
            "ledger_entry_created": ledger_entry_created,
            "provider_request_created": provider_request_created,
            "provider_call_authorized": provider_call_authorized,
            "provider_transmission_authorized": (
                provider_transmission_authorized
            ),
            "runtime_invocation_authorized": runtime_invocation_authorized,
            "run_size_authorized": run_size_authorized,
            "launch_authorized": launch_authorized,
            "production_authorized": production_authorized,
            "launch_readiness": launch_readiness,
            "production_effect": production_effect,
            "zero_production_effect_proof": zero_production_effect_proof,
            "reason_codes": normalized_reasons,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)
        computed = sha256_hex(canonical_json_bytes(_evidence_payload(self)))
        object.__setattr__(
            self,
            "evidence_id",
            _supplied_identity(evidence_id, computed, "evidence_id"),
        )

    @property
    def identity(self) -> str:
        return self.evidence_id


_DEFAULT_BLOCKERS = (
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "EXECUTABLE_INPUT_CONTENT_ABSENT",
    "LAUNCH_NOT_AUTHORIZED",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "PROVIDER_REQUEST_NOT_CREATED",
    "RUN_MANIFEST_NOT_ACTIVATED",
)


def _make_evidence(
) -> ShadowPhase11PilotInputRunManifestReadinessEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    return ShadowPhase11PilotInputRunManifestReadinessEvidenceV1(
        schema_version=_EVIDENCE_SCHEMA,
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        locked_repository_baseline=_REPOSITORY_BASELINE,
        locked_phase09_baseline=_PHASE09_BASELINE,
        credential_safe_gate_reference=gate.evidence_reference,
        credential_safe_gate_identity=gate.identity,
        current_runtime_integrity_reference=runtime.evidence_reference,
        current_runtime_integrity_identity=runtime.identity,
        pricing_evidence_reference=pricing.evidence_reference,
        pricing_evidence_identity=pricing.identity,
        reservation_bound_reference=reservation.evidence_reference,
        reservation_bound_identity=reservation.identity,
        input_readiness_state=(
            ShadowPhase11PilotInputReadinessStateV1
            .CANDIDATE_INPUT_DEFINED_NOT_AUTHORIZED
        ),
        manifest_readiness_state=(
            ShadowPhase11PilotManifestReadinessStateV1
            .PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED
        ),
        candidate_items=_CANDIDATE_ITEMS,
        proposed_manifest=_PROPOSED_MANIFEST,
        candidate_input_defined=True,
        executable_input_content_present=False,
        run_manifest_defined=True,
        run_manifest_activated=False,
        credential_configuration_verified=False,
        pricing_revalidation_completed=False,
        pre_call_reservation_created=False,
        ledger_entry_created=False,
        provider_request_created=False,
        provider_call_authorized=False,
        provider_transmission_authorized=False,
        runtime_invocation_authorized=False,
        run_size_authorized=False,
        launch_authorized=False,
        production_authorized=False,
        launch_readiness=(
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
        reason_codes=_DEFAULT_BLOCKERS,
    )


_EVIDENCE = _make_evidence()


def get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1(
) -> ShadowPhase11PilotInputRunManifestReadinessEvidenceV1:
    """Return immutable metadata-only pilot input/manifest readiness."""

    return _EVIDENCE


__all__ = (
    "ShadowPhase11PilotInputItemV1",
    "ShadowPhase11PilotInputReadinessStateV1",
    "ShadowPhase11PilotInputRunManifestReadinessEvidenceV1",
    "ShadowPhase11PilotInputRunManifestReadinessValidationError",
    "ShadowPhase11PilotManifestReadinessStateV1",
    "ShadowPhase11PilotRunManifestV1",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1",
    "sha256_hex",
)
