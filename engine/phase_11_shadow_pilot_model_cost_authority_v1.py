"""Immutable Phase 11 pilot model-and-cost authority evidence.

These contracts record supplied owner authority only. They establish no
pricing or availability evidence and grant no execution, spending, launch,
publication, or production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_budget_control_v1 import PROVIDERS


_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_REFERENCE = re.compile(r"^[A-Z0-9][A-Z0-9_]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_MICRO_USD_PER_USD = Decimal("1000000")


class ShadowPhase11PilotAuthorityValidationError(ValueError):
    """Raised when pilot authority evidence is invalid or inconsistent."""


class ShadowPhase11PilotProviderRoleV1(StrEnum):
    PRIMARY = "PRIMARY"
    L1 = "L1"
    L2 = "L2"


class ShadowPhase11PilotRetryPolicyV1(StrEnum):
    FORBIDDEN = "FORBIDDEN"


class ShadowPhase11PilotPricingRevalidationStatusV1(StrEnum):
    REQUIRED_NOT_COMPLETED = "REQUIRED_NOT_COMPLETED"


class ShadowPhase11PilotLaunchReadinessV1(StrEnum):
    NOT_READY_FOR_LAUNCH = "NOT_READY_FOR_LAUNCH"


class ShadowPhase11PilotSpendScopeV1(StrEnum):
    SHADOW_EVIDENCE_ACQUISITION_ONLY = "SHADOW_EVIDENCE_ACQUISITION_ONLY"


_ROLE_BINDINGS = {
    ShadowPhase11PilotProviderRoleV1.PRIMARY: (
        "DEEPSEEK",
        "deepseek-v4-pro",
    ),
    ShadowPhase11PilotProviderRoleV1.L1: (
        "ANTHROPIC",
        "claude-sonnet-5",
    ),
    ShadowPhase11PilotProviderRoleV1.L2: (
        "ANTHROPIC",
        "claude-opus-4-8",
    ),
}


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowPhase11PilotAuthorityValidationError(
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
    raise ShadowPhase11PilotAuthorityValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic canonical UTF-8 JSON bytes."""

    try:
        return json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowPhase11PilotAuthorityValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11PilotAuthorityValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _derived_identity(material: Any) -> str:
    return sha256_hex(canonical_json_bytes(material))


def _identity(material: Any, supplied: Any, name: str) -> str:
    derived = _derived_identity(material)
    if supplied is not None and (
        type(supplied) is not str
        or not _HASH.fullmatch(supplied)
        or supplied != derived
    ):
        raise ShadowPhase11PilotAuthorityValidationError(f"invalid {name}")
    return derived


def _exact_enum(name: str, value: Any, expected: type[StrEnum]) -> Any:
    if type(value) is not expected:
        raise ShadowPhase11PilotAuthorityValidationError(f"invalid {name}")
    return value


def _positive_integer(name: str, value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise ShadowPhase11PilotAuthorityValidationError(
            f"{name} must be a positive integer"
        )
    return value


def _reference(name: str, value: Any) -> str:
    if type(value) is not str or not _REFERENCE.fullmatch(value):
        raise ShadowPhase11PilotAuthorityValidationError(f"invalid {name}")
    return value


def _baseline(value: Any) -> str:
    if type(value) is not str or not _COMMIT.fullmatch(value):
        raise ShadowPhase11PilotAuthorityValidationError(
            "invalid locked_baseline_commit"
        )
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or not value
        or len(value) > 32
        or any(
            type(item) is not str or not _REASON.fullmatch(item)
            for item in value
        )
        or len(set(value)) != len(value)
    ):
        raise ShadowPhase11PilotAuthorityValidationError(
            "invalid reason_codes"
        )
    return tuple(sorted(value))


def _money(name: str, value: Any) -> Decimal:
    if (
        type(value) is not Decimal
        or not value.is_finite()
        or value < 0
    ):
        raise ShadowPhase11PilotAuthorityValidationError(
            f"{name} must be a finite non-negative Decimal"
        )
    return value


def _exact_text(name: str, value: Any, expected: str) -> str:
    if type(value) is not str or value != expected:
        raise ShadowPhase11PilotAuthorityValidationError(f"invalid {name}")
    return value


_PROVIDER_BOUND_FIELDS = frozenset(
    {
        "schema_version",
        "provider_bound_id",
        "role",
        "provider",
        "model_identifier",
        "maximum_input_tokens",
        "maximum_output_tokens",
        "maximum_attempts",
        "provider_error_retry_policy",
        "credential_error_retry_policy",
        "authentication_error_retry_policy",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11PilotProviderBoundV1:
    schema_version: str
    provider_bound_id: str
    role: ShadowPhase11PilotProviderRoleV1
    provider: str
    model_identifier: str
    maximum_input_tokens: int
    maximum_output_tokens: int
    maximum_attempts: int
    provider_error_retry_policy: ShadowPhase11PilotRetryPolicyV1
    credential_error_retry_policy: ShadowPhase11PilotRetryPolicyV1
    authentication_error_retry_policy: ShadowPhase11PilotRetryPolicyV1
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PROVIDER_BOUND_FIELDS:
            raise ShadowPhase11PilotAuthorityValidationError(
                "invalid provider-bound fields"
            )
        if values["schema_version"] != (
            "phase11-shadow-pilot-provider-bound-v1"
        ):
            raise ShadowPhase11PilotAuthorityValidationError(
                "unsupported provider-bound schema"
            )
        role = _exact_enum(
            "role",
            values["role"],
            ShadowPhase11PilotProviderRoleV1,
        )
        provider = values["provider"]
        model_identifier = values["model_identifier"]
        expected_provider, expected_model = _ROLE_BINDINGS[role]
        if (
            type(provider) is not str
            or provider not in PROVIDERS
            or provider != expected_provider
        ):
            raise ShadowPhase11PilotAuthorityValidationError(
                "provider does not match the authorized role"
            )
        if (
            type(model_identifier) is not str
            or model_identifier != expected_model
        ):
            raise ShadowPhase11PilotAuthorityValidationError(
                "model_identifier does not match the authorized role"
            )
        maximum_input_tokens = _positive_integer(
            "maximum_input_tokens",
            values["maximum_input_tokens"],
        )
        maximum_output_tokens = _positive_integer(
            "maximum_output_tokens",
            values["maximum_output_tokens"],
        )
        maximum_attempts = _positive_integer(
            "maximum_attempts",
            values["maximum_attempts"],
        )
        if maximum_input_tokens != 16000:
            raise ShadowPhase11PilotAuthorityValidationError(
                "maximum_input_tokens must equal 16000"
            )
        if maximum_output_tokens != 2000:
            raise ShadowPhase11PilotAuthorityValidationError(
                "maximum_output_tokens must equal 2000"
            )
        if maximum_attempts != 1:
            raise ShadowPhase11PilotAuthorityValidationError(
                "maximum_attempts must equal one"
            )
        provider_retry = _exact_enum(
            "provider_error_retry_policy",
            values["provider_error_retry_policy"],
            ShadowPhase11PilotRetryPolicyV1,
        )
        credential_retry = _exact_enum(
            "credential_error_retry_policy",
            values["credential_error_retry_policy"],
            ShadowPhase11PilotRetryPolicyV1,
        )
        authentication_retry = _exact_enum(
            "authentication_error_retry_policy",
            values["authentication_error_retry_policy"],
            ShadowPhase11PilotRetryPolicyV1,
        )
        reasons = _reason_codes(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "role": role,
            "provider": provider,
            "model_identifier": model_identifier,
            "maximum_input_tokens": maximum_input_tokens,
            "maximum_output_tokens": maximum_output_tokens,
            "maximum_attempts": maximum_attempts,
            "provider_error_retry_policy": provider_retry,
            "credential_error_retry_policy": credential_retry,
            "authentication_error_retry_policy": authentication_retry,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["provider_bound_id"],
            "provider_bound_id",
        )
        normalized = {
            **material,
            "provider_bound_id": identity,
        }
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.provider_bound_id


_AUTHORITY_FIELDS = frozenset(
    {
        "schema_version",
        "authority_id",
        "authorization_reference",
        "budget_authorization_reference",
        "locked_baseline_commit",
        "provider_bounds",
        "currency",
        "hard_cap_usd",
        "hard_cap_micro_usd",
        "safety_reserve_usd",
        "safety_reserve_micro_usd",
        "spendable_cap_usd",
        "spendable_cap_micro_usd",
        "reserved_micro_usd",
        "committed_micro_usd",
        "remaining_authorized_micro_usd",
        "spend_scope",
        "pricing_revalidation_status",
        "launch_readiness",
        "production_effect",
        "account_order_trading_authority",
        "phase_12_activation_authority",
        "reason_codes",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11PilotModelCostAuthorityV1:
    schema_version: str
    authority_id: str
    authorization_reference: str
    budget_authorization_reference: str
    locked_baseline_commit: str
    provider_bounds: tuple[ShadowPhase11PilotProviderBoundV1, ...]
    currency: str
    hard_cap_usd: Decimal
    hard_cap_micro_usd: Decimal
    safety_reserve_usd: Decimal
    safety_reserve_micro_usd: Decimal
    spendable_cap_usd: Decimal
    spendable_cap_micro_usd: Decimal
    reserved_micro_usd: Decimal
    committed_micro_usd: Decimal
    remaining_authorized_micro_usd: Decimal
    spend_scope: ShadowPhase11PilotSpendScopeV1
    pricing_revalidation_status: (
        ShadowPhase11PilotPricingRevalidationStatusV1
    )
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    production_effect: str
    account_order_trading_authority: str
    phase_12_activation_authority: str
    reason_codes: tuple[str, ...]
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _AUTHORITY_FIELDS:
            raise ShadowPhase11PilotAuthorityValidationError(
                "invalid pilot-authority fields"
            )
        if values["schema_version"] != (
            "phase11-shadow-pilot-model-cost-authority-v1"
        ):
            raise ShadowPhase11PilotAuthorityValidationError(
                "unsupported pilot-authority schema"
            )
        authorization_reference = _reference(
            "authorization_reference",
            values["authorization_reference"],
        )
        budget_authorization_reference = _reference(
            "budget_authorization_reference",
            values["budget_authorization_reference"],
        )
        baseline = _baseline(values["locked_baseline_commit"])
        supplied_bounds = values["provider_bounds"]
        if (
            type(supplied_bounds) is not tuple
            or len(supplied_bounds) != len(
                ShadowPhase11PilotProviderRoleV1
            )
            or any(
                type(item) is not ShadowPhase11PilotProviderBoundV1
                for item in supplied_bounds
            )
        ):
            raise ShadowPhase11PilotAuthorityValidationError(
                "exactly three provider bounds are required"
            )
        by_role: dict[
            ShadowPhase11PilotProviderRoleV1,
            ShadowPhase11PilotProviderBoundV1,
        ] = {}
        for item in supplied_bounds:
            if item.role in by_role:
                raise ShadowPhase11PilotAuthorityValidationError(
                    "duplicate provider role"
                )
            by_role[item.role] = item
        roles = tuple(ShadowPhase11PilotProviderRoleV1)
        if set(by_role) != set(roles):
            raise ShadowPhase11PilotAuthorityValidationError(
                "provider roles are incomplete"
            )
        provider_bounds = tuple(by_role[role] for role in roles)
        currency = _exact_text(
            "currency",
            values["currency"],
            "USD_MICRO",
        )
        hard_cap_usd = _money("hard_cap_usd", values["hard_cap_usd"])
        hard_cap_micro_usd = _money(
            "hard_cap_micro_usd",
            values["hard_cap_micro_usd"],
        )
        safety_reserve_usd = _money(
            "safety_reserve_usd",
            values["safety_reserve_usd"],
        )
        safety_reserve_micro_usd = _money(
            "safety_reserve_micro_usd",
            values["safety_reserve_micro_usd"],
        )
        spendable_cap_usd = _money(
            "spendable_cap_usd",
            values["spendable_cap_usd"],
        )
        spendable_cap_micro_usd = _money(
            "spendable_cap_micro_usd",
            values["spendable_cap_micro_usd"],
        )
        reserved_micro_usd = _money(
            "reserved_micro_usd",
            values["reserved_micro_usd"],
        )
        committed_micro_usd = _money(
            "committed_micro_usd",
            values["committed_micro_usd"],
        )
        remaining_authorized_micro_usd = _money(
            "remaining_authorized_micro_usd",
            values["remaining_authorized_micro_usd"],
        )
        if hard_cap_usd <= 0 or hard_cap_micro_usd <= 0:
            raise ShadowPhase11PilotAuthorityValidationError(
                "hard cap must be positive"
            )
        if safety_reserve_usd >= hard_cap_usd:
            raise ShadowPhase11PilotAuthorityValidationError(
                "safety reserve must be less than hard cap"
            )
        if spendable_cap_usd != hard_cap_usd - safety_reserve_usd:
            raise ShadowPhase11PilotAuthorityValidationError(
                "spendable USD cap is inconsistent"
            )
        if (
            hard_cap_micro_usd
            != hard_cap_usd * _MICRO_USD_PER_USD
            or safety_reserve_micro_usd
            != safety_reserve_usd * _MICRO_USD_PER_USD
            or spendable_cap_micro_usd
            != spendable_cap_usd * _MICRO_USD_PER_USD
            or spendable_cap_micro_usd
            != hard_cap_micro_usd - safety_reserve_micro_usd
        ):
            raise ShadowPhase11PilotAuthorityValidationError(
                "USD and micro-USD values are inconsistent"
            )
        if reserved_micro_usd != 0 or committed_micro_usd != 0:
            raise ShadowPhase11PilotAuthorityValidationError(
                "reserved and committed amounts must remain zero"
            )
        if remaining_authorized_micro_usd != hard_cap_micro_usd:
            raise ShadowPhase11PilotAuthorityValidationError(
                "remaining authorization must equal the hard cap"
            )
        spend_scope = _exact_enum(
            "spend_scope",
            values["spend_scope"],
            ShadowPhase11PilotSpendScopeV1,
        )
        pricing_status = _exact_enum(
            "pricing_revalidation_status",
            values["pricing_revalidation_status"],
            ShadowPhase11PilotPricingRevalidationStatusV1,
        )
        launch_readiness = _exact_enum(
            "launch_readiness",
            values["launch_readiness"],
            ShadowPhase11PilotLaunchReadinessV1,
        )
        production_effect = _exact_text(
            "production_effect",
            values["production_effect"],
            "NONE",
        )
        no_trading_authority = _exact_text(
            "account_order_trading_authority",
            values["account_order_trading_authority"],
            "NONE",
        )
        no_phase_12_authority = _exact_text(
            "phase_12_activation_authority",
            values["phase_12_activation_authority"],
            "NOT_AUTHORIZED",
        )
        reasons = _reason_codes(values["reason_codes"])
        zero_proof = _exact_text(
            "zero_production_effect_proof",
            values["zero_production_effect_proof"],
            "PROVEN_NONE",
        )
        material = {
            "schema_version": values["schema_version"],
            "authorization_reference": authorization_reference,
            "budget_authorization_reference": (
                budget_authorization_reference
            ),
            "locked_baseline_commit": baseline,
            "provider_bounds": tuple(
                item.identity for item in provider_bounds
            ),
            "currency": currency,
            "hard_cap_usd": hard_cap_usd,
            "hard_cap_micro_usd": hard_cap_micro_usd,
            "safety_reserve_usd": safety_reserve_usd,
            "safety_reserve_micro_usd": safety_reserve_micro_usd,
            "spendable_cap_usd": spendable_cap_usd,
            "spendable_cap_micro_usd": spendable_cap_micro_usd,
            "reserved_micro_usd": reserved_micro_usd,
            "committed_micro_usd": committed_micro_usd,
            "remaining_authorized_micro_usd": (
                remaining_authorized_micro_usd
            ),
            "spend_scope": spend_scope,
            "pricing_revalidation_status": pricing_status,
            "launch_readiness": launch_readiness,
            "production_effect": production_effect,
            "account_order_trading_authority": no_trading_authority,
            "phase_12_activation_authority": no_phase_12_authority,
            "reason_codes": reasons,
            "zero_production_effect_proof": zero_proof,
        }
        identity = _identity(
            material,
            values["authority_id"],
            "authority_id",
        )
        normalized = {
            **material,
            "authority_id": identity,
            "provider_bounds": provider_bounds,
        }
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.authority_id


__all__ = (
    "ShadowPhase11PilotAuthorityValidationError",
    "ShadowPhase11PilotLaunchReadinessV1",
    "ShadowPhase11PilotModelCostAuthorityV1",
    "ShadowPhase11PilotPricingRevalidationStatusV1",
    "ShadowPhase11PilotProviderBoundV1",
    "ShadowPhase11PilotProviderRoleV1",
    "ShadowPhase11PilotRetryPolicyV1",
    "ShadowPhase11PilotSpendScopeV1",
    "canonical_json_bytes",
    "sha256_hex",
)
