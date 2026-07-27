"""Immutable Phase 11 pre-call reservation-bound evidence.

This module derives a calculation-only bound from committed pricing evidence.
It creates no reservation, mutates no ledger, authorizes no run, and performs
no credential, provider, network, filesystem, launch, or production action.
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
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    ShadowPhase11PilotRouteV1,
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_REFERENCE = re.compile(r"^[A-Z0-9][A-Z0-9_]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")

_SCHEMA_VERSION = "phase11-shadow-pilot-pre-call-reservation-bound-v1"
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
_PRICING_EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
)
_BUDGET_AUTHORIZATION_REFERENCE = (
    "PHASE_11_SHADOW_PILOT_BUDGET_USD_5_001"
)
_MODEL_COST_AUTHORIZATION_REFERENCE = (
    "PHASE_11_PILOT_MODEL_COST_BOUNDS_001"
)
_LOCKED_REPOSITORY_BASELINE = (
    "6f6647d21a312a54ba14e764e3a81177c2ae0700"
)
_LOCKED_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_DEFAULT_REASON_CODES = ("CONSERVATIVE_PRE_CALL_RESERVATION_BOUND",)


class ShadowPhase11PreCallReservationValidationError(ValueError):
    """Raised when immutable pre-call reservation-bound evidence is invalid."""


class ShadowPhase11PreCallReservationStateV1(StrEnum):
    """The sole non-operational state represented by this evidence."""

    BOUND_NOT_RESERVED = "BOUND_NOT_RESERVED"


class ShadowPhase11ReservationCalculationModeV1(StrEnum):
    """The sole calculation mode authorized by the evidence contract."""

    CONSERVATIVE_WORST_CASE_PER_ITEM = (
        "CONSERVATIVE_WORST_CASE_PER_ITEM"
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
            raise ShadowPhase11PreCallReservationValidationError(
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
    raise ShadowPhase11PreCallReservationValidationError(
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
        raise ShadowPhase11PreCallReservationValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11PreCallReservationValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _identity(material: Any, supplied: Any) -> str:
    derived = sha256_hex(canonical_json_bytes(material))
    if supplied is not None and (
        type(supplied) is not str
        or _HASH.fullmatch(supplied) is None
        or supplied != derived
    ):
        raise ShadowPhase11PreCallReservationValidationError(
            "invalid reservation_bound_id"
        )
    return derived


def _exact_text(name: str, value: Any, expected: str) -> str:
    if type(value) is not str or value != expected:
        raise ShadowPhase11PreCallReservationValidationError(
            f"invalid {name}"
        )
    return value


def _exact_reference(name: str, value: Any, expected: str) -> str:
    if (
        type(value) is not str
        or _REFERENCE.fullmatch(value) is None
        or value != expected
    ):
        raise ShadowPhase11PreCallReservationValidationError(
            f"invalid {name}"
        )
    return value


def _exact_commit(name: str, value: Any, expected: str) -> str:
    if (
        type(value) is not str
        or _COMMIT.fullmatch(value) is None
        or value != expected
    ):
        raise ShadowPhase11PreCallReservationValidationError(
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
        raise ShadowPhase11PreCallReservationValidationError(
            f"invalid {name}"
        )
    return value


def _exact_bool(name: str, value: Any, expected: bool) -> bool:
    if type(value) is not bool or value is not expected:
        raise ShadowPhase11PreCallReservationValidationError(
            f"invalid {name}"
        )
    return value


def _exact_int(name: str, value: Any, expected: int) -> int:
    if type(value) is not int or value != expected:
        raise ShadowPhase11PreCallReservationValidationError(
            f"invalid {name}"
        )
    return value


def _exact_decimal(
    name: str,
    value: Any,
    expected: Decimal,
) -> Decimal:
    if (
        type(value) is not Decimal
        or not value.is_finite()
        or value < 0
        or value != expected
    ):
        raise ShadowPhase11PreCallReservationValidationError(
            f"invalid {name}"
        )
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise ShadowPhase11PreCallReservationValidationError(
            "invalid reason_codes"
        )
    if any(
        type(reason) is not str or _REASON.fullmatch(reason) is None
        for reason in value
    ):
        raise ShadowPhase11PreCallReservationValidationError(
            "invalid reason_codes"
        )
    normalized = tuple(sorted(value))
    if len(set(normalized)) != len(normalized):
        raise ShadowPhase11PreCallReservationValidationError(
            "invalid reason_codes"
        )
    return normalized


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11PreCallReservationBoundV1:
    """Immutable mathematical pre-call reservation-bound evidence."""

    schema_version: str
    reservation_bound_id: str
    evidence_reference: str
    pricing_evidence_reference: str
    pricing_evidence_identity: str
    budget_authorization_reference: str
    model_cost_authorization_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    reservation_state: ShadowPhase11PreCallReservationStateV1
    calculation_mode: ShadowPhase11ReservationCalculationModeV1
    conservative_worst_case_route: ShadowPhase11PilotRouteV1
    per_item_reservation_bound_micro_usd: Decimal
    hard_cap_micro_usd: Decimal
    safety_reserve_micro_usd: Decimal
    spendable_cap_micro_usd: Decimal
    mathematical_safe_maximum_items: int
    safe_capacity_total_micro_usd: Decimal
    next_item_total_micro_usd: Decimal
    reservation_required_before_provider_transmission: bool
    pricing_revalidation_required_before_reservation_use: bool
    launch_time_pricing_revalidation_required: bool
    fixed_freshness_window_defined: bool
    pricing_revalidation_status: (
        ShadowPhase11PilotPricingRevalidationStatusV1
    )
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    run_size_authorized: bool
    reservation_creation_authorized: bool
    ledger_mutation_authorized: bool
    provider_call_authorized: bool
    budget_reserved_micro_usd: Decimal
    budget_consumed_micro_usd: Decimal
    production_effect: str
    zero_production_effect_proof: str
    reason_codes: tuple[str, ...]

    def __init__(self, **fields: Any) -> None:
        expected_fields = {
            "schema_version",
            "reservation_bound_id",
            "evidence_reference",
            "pricing_evidence_reference",
            "pricing_evidence_identity",
            "budget_authorization_reference",
            "model_cost_authorization_reference",
            "locked_repository_baseline",
            "locked_phase09_baseline",
            "reservation_state",
            "calculation_mode",
            "conservative_worst_case_route",
            "per_item_reservation_bound_micro_usd",
            "hard_cap_micro_usd",
            "safety_reserve_micro_usd",
            "spendable_cap_micro_usd",
            "mathematical_safe_maximum_items",
            "safe_capacity_total_micro_usd",
            "next_item_total_micro_usd",
            "reservation_required_before_provider_transmission",
            "pricing_revalidation_required_before_reservation_use",
            "launch_time_pricing_revalidation_required",
            "fixed_freshness_window_defined",
            "pricing_revalidation_status",
            "launch_readiness",
            "run_size_authorized",
            "reservation_creation_authorized",
            "ledger_mutation_authorized",
            "provider_call_authorized",
            "budget_reserved_micro_usd",
            "budget_consumed_micro_usd",
            "production_effect",
            "zero_production_effect_proof",
            "reason_codes",
        }
        if set(fields) != expected_fields:
            raise ShadowPhase11PreCallReservationValidationError(
                "invalid constructor fields"
            )

        pricing_evidence = (
            get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
        )
        values: dict[str, Any] = {}
        values["schema_version"] = _exact_text(
            "schema_version",
            fields["schema_version"],
            _SCHEMA_VERSION,
        )
        values["evidence_reference"] = _exact_reference(
            "evidence_reference",
            fields["evidence_reference"],
            _EVIDENCE_REFERENCE,
        )
        values["pricing_evidence_reference"] = _exact_reference(
            "pricing_evidence_reference",
            fields["pricing_evidence_reference"],
            pricing_evidence.evidence_reference,
        )
        if (
            type(fields["pricing_evidence_identity"]) is not str
            or _HASH.fullmatch(fields["pricing_evidence_identity"]) is None
            or fields["pricing_evidence_identity"]
            != pricing_evidence.identity
        ):
            raise ShadowPhase11PreCallReservationValidationError(
                "invalid pricing_evidence_identity"
            )
        values["pricing_evidence_identity"] = fields[
            "pricing_evidence_identity"
        ]
        values["budget_authorization_reference"] = _exact_reference(
            "budget_authorization_reference",
            fields["budget_authorization_reference"],
            _BUDGET_AUTHORIZATION_REFERENCE,
        )
        values["model_cost_authorization_reference"] = _exact_reference(
            "model_cost_authorization_reference",
            fields["model_cost_authorization_reference"],
            _MODEL_COST_AUTHORIZATION_REFERENCE,
        )
        values["locked_repository_baseline"] = _exact_commit(
            "locked_repository_baseline",
            fields["locked_repository_baseline"],
            _LOCKED_REPOSITORY_BASELINE,
        )
        values["locked_phase09_baseline"] = _exact_commit(
            "locked_phase09_baseline",
            fields["locked_phase09_baseline"],
            _LOCKED_PHASE09_BASELINE,
        )
        values["reservation_state"] = _exact_enum(
            "reservation_state",
            fields["reservation_state"],
            ShadowPhase11PreCallReservationStateV1,
            ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED,
        )
        values["calculation_mode"] = _exact_enum(
            "calculation_mode",
            fields["calculation_mode"],
            ShadowPhase11ReservationCalculationModeV1,
            ShadowPhase11ReservationCalculationModeV1.CONSERVATIVE_WORST_CASE_PER_ITEM,
        )
        values["conservative_worst_case_route"] = _exact_enum(
            "conservative_worst_case_route",
            fields["conservative_worst_case_route"],
            ShadowPhase11PilotRouteV1,
            pricing_evidence.conservative_worst_case_route,
        )
        for name in (
            "per_item_reservation_bound_micro_usd",
            "hard_cap_micro_usd",
            "safety_reserve_micro_usd",
            "spendable_cap_micro_usd",
            "safe_capacity_total_micro_usd",
            "next_item_total_micro_usd",
            "budget_reserved_micro_usd",
            "budget_consumed_micro_usd",
        ):
            pricing_name = {
                "per_item_reservation_bound_micro_usd": (
                    "conservative_worst_case_item_cost_micro_usd"
                )
            }.get(name, name)
            values[name] = _exact_decimal(
                name,
                fields[name],
                getattr(pricing_evidence, pricing_name),
            )
        values["mathematical_safe_maximum_items"] = _exact_int(
            "mathematical_safe_maximum_items",
            fields["mathematical_safe_maximum_items"],
            pricing_evidence.mathematical_safe_maximum_items,
        )
        for name, expected in (
            ("reservation_required_before_provider_transmission", True),
            (
                "pricing_revalidation_required_before_reservation_use",
                True,
            ),
            (
                "launch_time_pricing_revalidation_required",
                pricing_evidence.launch_time_pricing_revalidation_required,
            ),
            (
                "fixed_freshness_window_defined",
                pricing_evidence.fixed_freshness_window_defined,
            ),
            ("run_size_authorized", False),
            ("reservation_creation_authorized", False),
            ("ledger_mutation_authorized", False),
            ("provider_call_authorized", False),
        ):
            values[name] = _exact_bool(name, fields[name], expected)
        values["pricing_revalidation_status"] = _exact_enum(
            "pricing_revalidation_status",
            fields["pricing_revalidation_status"],
            ShadowPhase11PilotPricingRevalidationStatusV1,
            pricing_evidence.pricing_revalidation_status,
        )
        values["launch_readiness"] = _exact_enum(
            "launch_readiness",
            fields["launch_readiness"],
            ShadowPhase11PilotLaunchReadinessV1,
            pricing_evidence.launch_readiness,
        )
        values["production_effect"] = _exact_text(
            "production_effect",
            fields["production_effect"],
            pricing_evidence.production_effect,
        )
        values["zero_production_effect_proof"] = _exact_text(
            "zero_production_effect_proof",
            fields["zero_production_effect_proof"],
            pricing_evidence.zero_production_effect_proof,
        )
        values["reason_codes"] = _reason_codes(fields["reason_codes"])

        per_item = values["per_item_reservation_bound_micro_usd"]
        safe_items = values["mathematical_safe_maximum_items"]
        if (
            Decimal(safe_items) * per_item
            != values["safe_capacity_total_micro_usd"]
            or Decimal(safe_items + 1) * per_item
            != values["next_item_total_micro_usd"]
            or values["safe_capacity_total_micro_usd"]
            > values["spendable_cap_micro_usd"]
            or values["next_item_total_micro_usd"]
            <= values["spendable_cap_micro_usd"]
        ):
            raise ShadowPhase11PreCallReservationValidationError(
                "invalid mathematical capacity proof"
            )

        identity_material = {
            **values,
            "reservation_bound_id": None,
        }
        values["reservation_bound_id"] = _identity(
            identity_material,
            fields["reservation_bound_id"],
        )
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def identity(self) -> str:
        """Return the canonical reservation-bound evidence identity."""

        return self.reservation_bound_id

    def calculate_mathematical_reservation_bound_micro_usd(
        self,
        item_count: int,
    ) -> Decimal:
        """Calculate hypothetical bound evidence without reserving budget."""

        if (
            type(item_count) is not int
            or item_count < 1
            or item_count > self.mathematical_safe_maximum_items
        ):
            raise ShadowPhase11PreCallReservationValidationError(
                "invalid item_count"
            )
        return (
            Decimal(item_count)
            * self.per_item_reservation_bound_micro_usd
        )


def _concrete_bound() -> ShadowPhase11PreCallReservationBoundV1:
    pricing_evidence = (
        get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    )
    return ShadowPhase11PreCallReservationBoundV1(
        schema_version=_SCHEMA_VERSION,
        reservation_bound_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        pricing_evidence_reference=pricing_evidence.evidence_reference,
        pricing_evidence_identity=pricing_evidence.identity,
        budget_authorization_reference=_BUDGET_AUTHORIZATION_REFERENCE,
        model_cost_authorization_reference=(
            _MODEL_COST_AUTHORIZATION_REFERENCE
        ),
        locked_repository_baseline=_LOCKED_REPOSITORY_BASELINE,
        locked_phase09_baseline=_LOCKED_PHASE09_BASELINE,
        reservation_state=(
            ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED
        ),
        calculation_mode=(
            ShadowPhase11ReservationCalculationModeV1.CONSERVATIVE_WORST_CASE_PER_ITEM
        ),
        conservative_worst_case_route=(
            pricing_evidence.conservative_worst_case_route
        ),
        per_item_reservation_bound_micro_usd=(
            pricing_evidence.conservative_worst_case_item_cost_micro_usd
        ),
        hard_cap_micro_usd=pricing_evidence.hard_cap_micro_usd,
        safety_reserve_micro_usd=(
            pricing_evidence.safety_reserve_micro_usd
        ),
        spendable_cap_micro_usd=pricing_evidence.spendable_cap_micro_usd,
        mathematical_safe_maximum_items=(
            pricing_evidence.mathematical_safe_maximum_items
        ),
        safe_capacity_total_micro_usd=(
            pricing_evidence.safe_capacity_total_micro_usd
        ),
        next_item_total_micro_usd=pricing_evidence.next_item_total_micro_usd,
        reservation_required_before_provider_transmission=True,
        pricing_revalidation_required_before_reservation_use=True,
        launch_time_pricing_revalidation_required=(
            pricing_evidence.launch_time_pricing_revalidation_required
        ),
        fixed_freshness_window_defined=(
            pricing_evidence.fixed_freshness_window_defined
        ),
        pricing_revalidation_status=(
            pricing_evidence.pricing_revalidation_status
        ),
        launch_readiness=pricing_evidence.launch_readiness,
        run_size_authorized=False,
        reservation_creation_authorized=False,
        ledger_mutation_authorized=False,
        provider_call_authorized=False,
        budget_reserved_micro_usd=pricing_evidence.budget_reserved_micro_usd,
        budget_consumed_micro_usd=(
            pricing_evidence.budget_consumed_micro_usd
        ),
        production_effect=pricing_evidence.production_effect,
        zero_production_effect_proof=(
            pricing_evidence.zero_production_effect_proof
        ),
        reason_codes=_DEFAULT_REASON_CODES,
    )


_BOUND = _concrete_bound()


def get_phase_11_shadow_pilot_pre_call_reservation_bound_v1(
) -> ShadowPhase11PreCallReservationBoundV1:
    """Return static, immutable, zero-authority reservation-bound evidence."""

    return _BOUND


__all__ = [
    "ShadowPhase11PreCallReservationBoundV1",
    "ShadowPhase11PreCallReservationStateV1",
    "ShadowPhase11PreCallReservationValidationError",
    "ShadowPhase11ReservationCalculationModeV1",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_pre_call_reservation_bound_v1",
    "sha256_hex",
]
