"""Immutable Phase 11 official pricing and conservative cost-bound evidence.

The contracts in this module contain static, repository-owned evidence only.
They perform no retrieval, credential access, budget mutation, provider call,
launch, publication, or production action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_CEILING
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_budget_control_v1 import PROVIDERS
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotPricingRevalidationStatusV1,
    ShadowPhase11PilotProviderRoleV1,
    ShadowPhase11PilotRetryPolicyV1,
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_REFERENCE = re.compile(r"^[A-Z0-9][A-Z0-9_]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_HTTPS_URL = re.compile(r"^https://([A-Za-z0-9.-]+)(?:/[^\s]*)?$")

_APPROVED_DOCUMENTATION_HOSTS = {
    "DEEPSEEK": frozenset({"api-docs.deepseek.com"}),
    "ANTHROPIC": frozenset(
        {
            "docs.anthropic.com",
            "platform.claude.com",
            "www.anthropic.com",
        }
    ),
}


class ShadowPhase11PricingCostBoundValidationError(ValueError):
    """Raised when immutable pricing or cost-bound evidence is invalid."""


class ShadowPhase11OfficialPricingSourcePurposeV1(StrEnum):
    DEEPSEEK_MODELS = "DEEPSEEK_MODELS"
    DEEPSEEK_PRICING = "DEEPSEEK_PRICING"
    CLAUDE_MODELS = "CLAUDE_MODELS"
    CLAUDE_PRICING = "CLAUDE_PRICING"


class ShadowPhase11PilotRouteV1(StrEnum):
    L0 = "L0"
    L1 = "L1"
    DIRECT_L2 = "DIRECT_L2"
    L1_TO_L2 = "L1_TO_L2"


_PURPOSE_PROVIDERS = {
    ShadowPhase11OfficialPricingSourcePurposeV1.DEEPSEEK_MODELS: "DEEPSEEK",
    ShadowPhase11OfficialPricingSourcePurposeV1.DEEPSEEK_PRICING: "DEEPSEEK",
    ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_MODELS: "ANTHROPIC",
    ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_PRICING: "ANTHROPIC",
}

_MODEL_BINDINGS = {
    ShadowPhase11PilotProviderRoleV1.PRIMARY: {
        "provider": "DEEPSEEK",
        "model_identifier": "deepseek-v4-pro",
        "official_context_limit": 1000000,
        "official_maximum_output_tokens": 384000,
        "current_input_price_usd_per_million": Decimal("0.435"),
        "current_output_price_usd_per_million": Decimal("0.87"),
        "conservative_input_price_usd_per_million": Decimal("0.435"),
        "conservative_output_price_usd_per_million": Decimal("0.87"),
        "promotional_end_date": None,
        "scheduled_standard_start_date": None,
    },
    ShadowPhase11PilotProviderRoleV1.L1: {
        "provider": "ANTHROPIC",
        "model_identifier": "claude-sonnet-5",
        "official_context_limit": 1000000,
        "official_maximum_output_tokens": 128000,
        "current_input_price_usd_per_million": Decimal("2"),
        "current_output_price_usd_per_million": Decimal("10"),
        "conservative_input_price_usd_per_million": Decimal("3"),
        "conservative_output_price_usd_per_million": Decimal("15"),
        "promotional_end_date": date(2026, 8, 31),
        "scheduled_standard_start_date": date(2026, 9, 1),
    },
    ShadowPhase11PilotProviderRoleV1.L2: {
        "provider": "ANTHROPIC",
        "model_identifier": "claude-opus-4-8",
        "official_context_limit": 1000000,
        "official_maximum_output_tokens": 128000,
        "current_input_price_usd_per_million": Decimal("5"),
        "current_output_price_usd_per_million": Decimal("25"),
        "conservative_input_price_usd_per_million": Decimal("5"),
        "conservative_output_price_usd_per_million": Decimal("25"),
        "promotional_end_date": None,
        "scheduled_standard_start_date": None,
    },
}


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical_datetime(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    )
    return normalized.replace("+00:00", "Z").replace(".000000Z", "Z")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowPhase11PricingCostBoundValidationError(
                "canonical Decimal must be finite"
            )
        return _canonical_decimal(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowPhase11PricingCostBoundValidationError(
                "canonical datetime must be timezone-aware"
            )
        return _canonical_datetime(value)
    if type(value) is date:
        return value.isoformat()
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
    raise ShadowPhase11PricingCostBoundValidationError(
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
        raise ShadowPhase11PricingCostBoundValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11PricingCostBoundValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _derived_identity(material: Any) -> str:
    return sha256_hex(canonical_json_bytes(material))


def _identity(material: Any, supplied: Any, label: str) -> str:
    derived = _derived_identity(material)
    if supplied is not None and (
        type(supplied) is not str
        or _HASH.fullmatch(supplied) is None
        or supplied != derived
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {label}"
        )
    return derived


def _exact_enum(name: str, value: Any, enum_type: type[StrEnum]) -> Any:
    if type(value) is not enum_type:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value


def _exact_text(name: str, value: Any, expected: str) -> str:
    if type(value) is not str or value != expected:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value


def _nonempty_text(name: str, value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value


def _positive_integer(name: str, value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"{name} must be a positive integer"
        )
    return value


def _nonnegative_money(name: str, value: Any) -> Decimal:
    if (
        type(value) is not Decimal
        or not value.is_finite()
        or value < 0
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            f"{name} must be a finite non-negative Decimal"
        )
    return value


def _positive_price(name: str, value: Any) -> Decimal:
    result = _nonnegative_money(name, value)
    if result <= 0:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"{name} must be positive"
        )
    return result


def _hash_value(name: str, value: Any) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value


def _reference(name: str, value: Any) -> str:
    if type(value) is not str or _REFERENCE.fullmatch(value) is None:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value


def _baseline(name: str, value: Any) -> str:
    if type(value) is not str or _COMMIT.fullmatch(value) is None:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or not value
        or len(value) > 32
        or any(
            type(item) is not str or _REASON.fullmatch(item) is None
            for item in value
        )
        or len(set(value)) != len(value)
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            "invalid reason_codes"
        )
    return tuple(sorted(value))


def _canonical_codes(
    name: str,
    value: Any,
    required: frozenset[str],
) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or len(value) != len(required)
        or set(value) != set(required)
        or any(type(item) is not str for item in value)
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return tuple(sorted(value))


def _optional_text(name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _nonempty_text(name, value)


def _optional_date(name: str, value: Any) -> date | None:
    if value is None:
        return None
    if type(value) is not date:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value


def _utc_datetime(name: str, value: Any) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() is None
        or value.utcoffset() != timezone.utc.utcoffset(None)
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value.astimezone(timezone.utc)


def _official_url(name: str, value: Any, provider: str) -> str:
    if type(value) is not str:
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    match = _HTTPS_URL.fullmatch(value)
    if (
        match is None
        or match.group(1).lower()
        not in _APPROVED_DOCUMENTATION_HOSTS[provider]
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            f"invalid {name}"
        )
    return value


def _ceil_cost(tokens: int, rate: Decimal) -> Decimal:
    return (Decimal(tokens) * rate).to_integral_value(
        rounding=ROUND_CEILING
    )


_SOURCE_FIELDS = frozenset(
    {
        "schema_version",
        "source_id",
        "purpose",
        "provider",
        "requested_url",
        "final_url",
        "retrieved_at_utc",
        "http_method",
        "http_status",
        "content_type",
        "etag",
        "last_modified",
        "response_body_sha256",
        "document_title",
        "relevant_heading",
        "price_change_warning",
        "effective_date",
        "expiry_date",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11OfficialPricingSourceV1:
    schema_version: str
    source_id: str
    purpose: ShadowPhase11OfficialPricingSourcePurposeV1
    provider: str
    requested_url: str
    final_url: str
    retrieved_at_utc: datetime
    http_method: str
    http_status: int
    content_type: str
    etag: str | None
    last_modified: str | None
    response_body_sha256: str
    document_title: str
    relevant_heading: str
    price_change_warning: bool
    effective_date: date | None
    expiry_date: date | None
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _SOURCE_FIELDS:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid official-source fields"
            )
        schema_version = _exact_text(
            "schema_version",
            values["schema_version"],
            "phase11-official-pricing-source-v1",
        )
        purpose = _exact_enum(
            "purpose",
            values["purpose"],
            ShadowPhase11OfficialPricingSourcePurposeV1,
        )
        expected_provider = _PURPOSE_PROVIDERS[purpose]
        provider = values["provider"]
        if (
            type(provider) is not str
            or provider not in PROVIDERS
            or provider != expected_provider
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "provider does not match source purpose"
            )
        requested_url = _official_url(
            "requested_url",
            values["requested_url"],
            provider,
        )
        final_url = _official_url(
            "final_url",
            values["final_url"],
            provider,
        )
        retrieved_at = _utc_datetime(
            "retrieved_at_utc",
            values["retrieved_at_utc"],
        )
        method = values["http_method"]
        if type(method) is not str or method not in {"GET", "HEAD"}:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid http_method"
            )
        if type(values["http_status"]) is not int or values["http_status"] != 200:
            raise ShadowPhase11PricingCostBoundValidationError(
                "retained official source must have HTTP status 200"
            )
        content_type = _nonempty_text(
            "content_type",
            values["content_type"],
        )
        etag = _optional_text("etag", values["etag"])
        last_modified = _optional_text(
            "last_modified",
            values["last_modified"],
        )
        response_hash = _hash_value(
            "response_body_sha256",
            values["response_body_sha256"],
        )
        title = _nonempty_text(
            "document_title",
            values["document_title"],
        )
        heading = _nonempty_text(
            "relevant_heading",
            values["relevant_heading"],
        )
        warning = values["price_change_warning"]
        if type(warning) is not bool:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid price_change_warning"
            )
        effective_date = _optional_date(
            "effective_date",
            values["effective_date"],
        )
        expiry_date = _optional_date(
            "expiry_date",
            values["expiry_date"],
        )
        if (
            effective_date is not None
            and expiry_date is not None
            and expiry_date < effective_date
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "source expiry precedes effective date"
            )
        reasons = _reason_codes(values["reason_codes"])
        material = {
            "schema_version": schema_version,
            "purpose": purpose,
            "provider": provider,
            "requested_url": requested_url,
            "final_url": final_url,
            "retrieved_at_utc": retrieved_at,
            "http_method": method,
            "http_status": 200,
            "content_type": content_type,
            "etag": etag,
            "last_modified": last_modified,
            "response_body_sha256": response_hash,
            "document_title": title,
            "relevant_heading": heading,
            "price_change_warning": warning,
            "effective_date": effective_date,
            "expiry_date": expiry_date,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["source_id"],
            "source_id",
        )
        normalized = {**material, "source_id": identity}
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.source_id


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _make_official_sources(
) -> tuple[ShadowPhase11OfficialPricingSourceV1, ...]:
    shared = {
        "schema_version": "phase11-official-pricing-source-v1",
        "source_id": None,
        "http_method": "GET",
        "http_status": 200,
        "effective_date": None,
        "reason_codes": ("OFFICIAL_PUBLIC_DOCUMENTATION",),
    }
    return (
        ShadowPhase11OfficialPricingSourceV1(
            **shared,
            purpose=(
                ShadowPhase11OfficialPricingSourcePurposeV1.DEEPSEEK_MODELS
            ),
            provider="DEEPSEEK",
            requested_url=(
                "https://api-docs.deepseek.com/quick_start/model_list"
            ),
            final_url=(
                "https://api-docs.deepseek.com/quick_start/model_list"
            ),
            retrieved_at_utc=_utc("2026-07-18T09:37:02Z"),
            content_type="text/html",
            etag='"21d3921829487b385a08d944eacc9979"',
            last_modified="Mon, 13 Jul 2026 03:34:30 GMT",
            response_body_sha256=(
                "d2f1f6f3f4b67d764db0896375764266"
                "ceb24f953b775fae9c8fadc3ca3f83c7"
            ),
            document_title="Your First API Call | DeepSeek API Docs",
            relevant_heading="Your First API Call",
            price_change_warning=False,
            expiry_date=None,
        ),
        ShadowPhase11OfficialPricingSourceV1(
            **shared,
            purpose=(
                ShadowPhase11OfficialPricingSourcePurposeV1.DEEPSEEK_PRICING
            ),
            provider="DEEPSEEK",
            requested_url=(
                "https://api-docs.deepseek.com/quick_start/pricing"
            ),
            final_url=(
                "https://api-docs.deepseek.com/quick_start/pricing/"
            ),
            retrieved_at_utc=_utc("2026-07-18T09:37:03Z"),
            content_type="text/html",
            etag='"e2fb44396349e126364403c2db910464"',
            last_modified="Mon, 13 Jul 2026 03:34:36 GMT",
            response_body_sha256=(
                "5ed7309f6b8bf5dbae559a012341aa604"
                "d02b0cce2e20c48aaa6f0a0bf287f89"
            ),
            document_title="Models & Pricing | DeepSeek API Docs",
            relevant_heading="Models & Pricing",
            price_change_warning=True,
            expiry_date=None,
        ),
        ShadowPhase11OfficialPricingSourceV1(
            **shared,
            purpose=(
                ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_MODELS
            ),
            provider="ANTHROPIC",
            requested_url=(
                "https://platform.claude.com/docs/en/about-claude/"
                "models/overview"
            ),
            final_url=(
                "https://platform.claude.com/docs/en/about-claude/"
                "models/overview"
            ),
            retrieved_at_utc=_utc("2026-07-18T09:37:06Z"),
            content_type="text/html; charset=utf-8",
            etag=None,
            last_modified=None,
            response_body_sha256=(
                "9671f1b06820119975799d5f768732ae"
                "ca282f5a57b3c9fb7a446cdcc0be7378"
            ),
            document_title="Models overview - Claude Platform Docs",
            relevant_heading="Models overview",
            price_change_warning=False,
            expiry_date=None,
        ),
        ShadowPhase11OfficialPricingSourceV1(
            **shared,
            purpose=(
                ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_PRICING
            ),
            provider="ANTHROPIC",
            requested_url=(
                "https://platform.claude.com/docs/en/about-claude/pricing"
            ),
            final_url=(
                "https://platform.claude.com/docs/en/about-claude/pricing"
            ),
            retrieved_at_utc=_utc("2026-07-18T09:37:06Z"),
            content_type="text/html; charset=utf-8",
            etag=None,
            last_modified=None,
            response_body_sha256=(
                "f0f9bf9c4db1a859a023e3d35a6949c"
                "a0732461097d0c56545d7611d3696d191"
            ),
            document_title="Pricing - Claude Platform Docs",
            relevant_heading="Pricing",
            price_change_warning=False,
            expiry_date=date(2026, 8, 31),
        ),
    )


_OFFICIAL_SOURCES = _make_official_sources()
_SOURCE_BY_PURPOSE = {
    item.purpose: item
    for item in _OFFICIAL_SOURCES
}

_DISCOUNT_EXCLUSIONS = frozenset(
    {
        "NO_CACHE_HIT_DISCOUNT",
        "NO_CACHE_WRITE_ASSUMPTION",
        "NO_BATCH_DISCOUNT",
        "NO_NEGOTIATED_DISCOUNT",
        "NO_ACCOUNT_CREDIT_ASSUMPTION",
    }
)
_PREMIUM_TOOL_EXCLUSIONS = frozenset(
    {
        "NO_SERVER_SIDE_TOOL",
        "NO_FAST_OR_PREMIUM_MODE",
        "NO_TOOL_CALL",
    }
)

_MODEL_FIELDS = frozenset(
    {
        "schema_version",
        "model_bound_id",
        "role",
        "provider",
        "model_identifier",
        "documented_available",
        "official_context_limit",
        "official_maximum_output_tokens",
        "authorized_input_tokens",
        "authorized_output_tokens",
        "current_input_price_usd_per_million",
        "current_output_price_usd_per_million",
        "conservative_input_price_usd_per_million",
        "conservative_output_price_usd_per_million",
        "current_maximum_input_cost_micro_usd",
        "current_maximum_output_cost_micro_usd",
        "current_maximum_call_cost_micro_usd",
        "maximum_input_cost_micro_usd",
        "maximum_output_cost_micro_usd",
        "maximum_call_cost_micro_usd",
        "source_ids",
        "maximum_attempts",
        "provider_error_retry_policy",
        "credential_error_retry_policy",
        "authentication_error_retry_policy",
        "discount_exclusion_assumptions",
        "premium_tool_exclusion_assumptions",
        "promotional_end_date",
        "scheduled_standard_start_date",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11ModelPricingCostBoundV1:
    schema_version: str
    model_bound_id: str
    role: ShadowPhase11PilotProviderRoleV1
    provider: str
    model_identifier: str
    documented_available: bool
    official_context_limit: int
    official_maximum_output_tokens: int
    authorized_input_tokens: int
    authorized_output_tokens: int
    current_input_price_usd_per_million: Decimal
    current_output_price_usd_per_million: Decimal
    conservative_input_price_usd_per_million: Decimal
    conservative_output_price_usd_per_million: Decimal
    current_maximum_input_cost_micro_usd: Decimal
    current_maximum_output_cost_micro_usd: Decimal
    current_maximum_call_cost_micro_usd: Decimal
    maximum_input_cost_micro_usd: Decimal
    maximum_output_cost_micro_usd: Decimal
    maximum_call_cost_micro_usd: Decimal
    source_ids: tuple[str, ...]
    maximum_attempts: int
    provider_error_retry_policy: ShadowPhase11PilotRetryPolicyV1
    credential_error_retry_policy: ShadowPhase11PilotRetryPolicyV1
    authentication_error_retry_policy: ShadowPhase11PilotRetryPolicyV1
    discount_exclusion_assumptions: tuple[str, ...]
    premium_tool_exclusion_assumptions: tuple[str, ...]
    promotional_end_date: date | None
    scheduled_standard_start_date: date | None
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _MODEL_FIELDS:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid model-cost-bound fields"
            )
        schema_version = _exact_text(
            "schema_version",
            values["schema_version"],
            "phase11-model-pricing-cost-bound-v1",
        )
        role = _exact_enum(
            "role",
            values["role"],
            ShadowPhase11PilotProviderRoleV1,
        )
        expected = _MODEL_BINDINGS[role]
        provider = _exact_text(
            "provider",
            values["provider"],
            expected["provider"],
        )
        if provider not in PROVIDERS:
            raise ShadowPhase11PricingCostBoundValidationError(
                "unsupported provider"
            )
        model_identifier = _exact_text(
            "model_identifier",
            values["model_identifier"],
            expected["model_identifier"],
        )
        if values["documented_available"] is not True:
            raise ShadowPhase11PricingCostBoundValidationError(
                "documented availability must be proven"
            )
        official_context = _positive_integer(
            "official_context_limit",
            values["official_context_limit"],
        )
        official_output = _positive_integer(
            "official_maximum_output_tokens",
            values["official_maximum_output_tokens"],
        )
        authorized_input = _positive_integer(
            "authorized_input_tokens",
            values["authorized_input_tokens"],
        )
        authorized_output = _positive_integer(
            "authorized_output_tokens",
            values["authorized_output_tokens"],
        )
        if (
            official_context != expected["official_context_limit"]
            or official_output
            != expected["official_maximum_output_tokens"]
            or authorized_input != 16000
            or authorized_output != 2000
            or authorized_input > official_context
            or authorized_output > official_output
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "token limits do not match official owner bounds"
            )
        current_input_price = _positive_price(
            "current_input_price_usd_per_million",
            values["current_input_price_usd_per_million"],
        )
        current_output_price = _positive_price(
            "current_output_price_usd_per_million",
            values["current_output_price_usd_per_million"],
        )
        conservative_input_price = _positive_price(
            "conservative_input_price_usd_per_million",
            values["conservative_input_price_usd_per_million"],
        )
        conservative_output_price = _positive_price(
            "conservative_output_price_usd_per_million",
            values["conservative_output_price_usd_per_million"],
        )
        if (
            current_input_price
            != expected["current_input_price_usd_per_million"]
            or current_output_price
            != expected["current_output_price_usd_per_million"]
            or conservative_input_price
            != expected["conservative_input_price_usd_per_million"]
            or conservative_output_price
            != expected["conservative_output_price_usd_per_million"]
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "pricing does not match the frozen conservative selection"
            )
        current_input_cost = _nonnegative_money(
            "current_maximum_input_cost_micro_usd",
            values["current_maximum_input_cost_micro_usd"],
        )
        current_output_cost = _nonnegative_money(
            "current_maximum_output_cost_micro_usd",
            values["current_maximum_output_cost_micro_usd"],
        )
        current_call_cost = _nonnegative_money(
            "current_maximum_call_cost_micro_usd",
            values["current_maximum_call_cost_micro_usd"],
        )
        maximum_input_cost = _nonnegative_money(
            "maximum_input_cost_micro_usd",
            values["maximum_input_cost_micro_usd"],
        )
        maximum_output_cost = _nonnegative_money(
            "maximum_output_cost_micro_usd",
            values["maximum_output_cost_micro_usd"],
        )
        maximum_call_cost = _nonnegative_money(
            "maximum_call_cost_micro_usd",
            values["maximum_call_cost_micro_usd"],
        )
        if (
            current_input_cost
            != _ceil_cost(authorized_input, current_input_price)
            or current_output_cost
            != _ceil_cost(authorized_output, current_output_price)
            or current_call_cost
            != current_input_cost + current_output_cost
            or maximum_input_cost
            != _ceil_cost(authorized_input, conservative_input_price)
            or maximum_output_cost
            != _ceil_cost(authorized_output, conservative_output_price)
            or maximum_call_cost
            != maximum_input_cost + maximum_output_cost
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "model call costs are inconsistent"
            )
        supplied_source_ids = values["source_ids"]
        if type(supplied_source_ids) is not tuple:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid source_ids"
            )
        source_ids = tuple(
            _hash_value("source_id", item)
            for item in supplied_source_ids
        )
        expected_source_ids = _model_source_ids(role)
        if source_ids != expected_source_ids:
            raise ShadowPhase11PricingCostBoundValidationError(
                "incorrect source identity relationship"
            )
        maximum_attempts = _positive_integer(
            "maximum_attempts",
            values["maximum_attempts"],
        )
        if maximum_attempts != 1:
            raise ShadowPhase11PricingCostBoundValidationError(
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
        discounts = _canonical_codes(
            "discount_exclusion_assumptions",
            values["discount_exclusion_assumptions"],
            _DISCOUNT_EXCLUSIONS,
        )
        premium_tools = _canonical_codes(
            "premium_tool_exclusion_assumptions",
            values["premium_tool_exclusion_assumptions"],
            _PREMIUM_TOOL_EXCLUSIONS,
        )
        promotional_end = _optional_date(
            "promotional_end_date",
            values["promotional_end_date"],
        )
        standard_start = _optional_date(
            "scheduled_standard_start_date",
            values["scheduled_standard_start_date"],
        )
        if (
            promotional_end != expected["promotional_end_date"]
            or standard_start != expected["scheduled_standard_start_date"]
            or (
                promotional_end is not None
                and standard_start is not None
                and standard_start.toordinal()
                != promotional_end.toordinal() + 1
            )
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid promotional transition dates"
            )
        reasons = _reason_codes(values["reason_codes"])
        material = {
            "schema_version": schema_version,
            "role": role,
            "provider": provider,
            "model_identifier": model_identifier,
            "documented_available": True,
            "official_context_limit": official_context,
            "official_maximum_output_tokens": official_output,
            "authorized_input_tokens": authorized_input,
            "authorized_output_tokens": authorized_output,
            "current_input_price_usd_per_million": current_input_price,
            "current_output_price_usd_per_million": current_output_price,
            "conservative_input_price_usd_per_million": (
                conservative_input_price
            ),
            "conservative_output_price_usd_per_million": (
                conservative_output_price
            ),
            "current_maximum_input_cost_micro_usd": current_input_cost,
            "current_maximum_output_cost_micro_usd": current_output_cost,
            "current_maximum_call_cost_micro_usd": current_call_cost,
            "maximum_input_cost_micro_usd": maximum_input_cost,
            "maximum_output_cost_micro_usd": maximum_output_cost,
            "maximum_call_cost_micro_usd": maximum_call_cost,
            "source_ids": source_ids,
            "maximum_attempts": maximum_attempts,
            "provider_error_retry_policy": provider_retry,
            "credential_error_retry_policy": credential_retry,
            "authentication_error_retry_policy": authentication_retry,
            "discount_exclusion_assumptions": discounts,
            "premium_tool_exclusion_assumptions": premium_tools,
            "promotional_end_date": promotional_end,
            "scheduled_standard_start_date": standard_start,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["model_bound_id"],
            "model_bound_id",
        )
        normalized = {**material, "model_bound_id": identity}
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.model_bound_id


def _model_source_ids(
    role: ShadowPhase11PilotProviderRoleV1,
) -> tuple[str, ...]:
    if role is ShadowPhase11PilotProviderRoleV1.PRIMARY:
        return (
            _SOURCE_BY_PURPOSE[
                ShadowPhase11OfficialPricingSourcePurposeV1.DEEPSEEK_PRICING
            ].identity,
        )
    if role is ShadowPhase11PilotProviderRoleV1.L1:
        return (
            _SOURCE_BY_PURPOSE[
                ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_MODELS
            ].identity,
            _SOURCE_BY_PURPOSE[
                ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_PRICING
            ].identity,
        )
    return (
        _SOURCE_BY_PURPOSE[
            ShadowPhase11OfficialPricingSourcePurposeV1.CLAUDE_PRICING
        ].identity,
    )


def _make_model_cost_bound(
    role: ShadowPhase11PilotProviderRoleV1,
) -> ShadowPhase11ModelPricingCostBoundV1:
    expected = _MODEL_BINDINGS[role]
    current_input_cost = _ceil_cost(
        16000,
        expected["current_input_price_usd_per_million"],
    )
    current_output_cost = _ceil_cost(
        2000,
        expected["current_output_price_usd_per_million"],
    )
    maximum_input_cost = _ceil_cost(
        16000,
        expected["conservative_input_price_usd_per_million"],
    )
    maximum_output_cost = _ceil_cost(
        2000,
        expected["conservative_output_price_usd_per_million"],
    )
    return ShadowPhase11ModelPricingCostBoundV1(
        schema_version="phase11-model-pricing-cost-bound-v1",
        model_bound_id=None,
        role=role,
        provider=expected["provider"],
        model_identifier=expected["model_identifier"],
        documented_available=True,
        official_context_limit=expected["official_context_limit"],
        official_maximum_output_tokens=(
            expected["official_maximum_output_tokens"]
        ),
        authorized_input_tokens=16000,
        authorized_output_tokens=2000,
        current_input_price_usd_per_million=(
            expected["current_input_price_usd_per_million"]
        ),
        current_output_price_usd_per_million=(
            expected["current_output_price_usd_per_million"]
        ),
        conservative_input_price_usd_per_million=(
            expected["conservative_input_price_usd_per_million"]
        ),
        conservative_output_price_usd_per_million=(
            expected["conservative_output_price_usd_per_million"]
        ),
        current_maximum_input_cost_micro_usd=current_input_cost,
        current_maximum_output_cost_micro_usd=current_output_cost,
        current_maximum_call_cost_micro_usd=(
            current_input_cost + current_output_cost
        ),
        maximum_input_cost_micro_usd=maximum_input_cost,
        maximum_output_cost_micro_usd=maximum_output_cost,
        maximum_call_cost_micro_usd=(
            maximum_input_cost + maximum_output_cost
        ),
        source_ids=_model_source_ids(role),
        maximum_attempts=1,
        provider_error_retry_policy=(
            ShadowPhase11PilotRetryPolicyV1.FORBIDDEN
        ),
        credential_error_retry_policy=(
            ShadowPhase11PilotRetryPolicyV1.FORBIDDEN
        ),
        authentication_error_retry_policy=(
            ShadowPhase11PilotRetryPolicyV1.FORBIDDEN
        ),
        discount_exclusion_assumptions=tuple(
            sorted(_DISCOUNT_EXCLUSIONS)
        ),
        premium_tool_exclusion_assumptions=tuple(
            sorted(_PREMIUM_TOOL_EXCLUSIONS)
        ),
        promotional_end_date=expected["promotional_end_date"],
        scheduled_standard_start_date=(
            expected["scheduled_standard_start_date"]
        ),
        reason_codes=("OFFICIAL_PRICE_CONSERVATIVE_BOUND",),
    )


_MODEL_COST_BOUNDS = tuple(
    _make_model_cost_bound(role)
    for role in ShadowPhase11PilotProviderRoleV1
)
_MODEL_BY_ROLE = {
    item.role: item
    for item in _MODEL_COST_BOUNDS
}

_ROUTE_FIELDS = frozenset(
    {
        "schema_version",
        "route_bound_id",
        "route",
        "model_bound_ids",
        "billable_call_count",
        "maximum_attempts_per_call",
        "current_total_micro_usd",
        "conservative_total_micro_usd",
        "reachability",
        "reason_codes",
    }
)


def _route_roles(
    route: ShadowPhase11PilotRouteV1,
) -> tuple[ShadowPhase11PilotProviderRoleV1, ...]:
    if route is ShadowPhase11PilotRouteV1.L0:
        return (ShadowPhase11PilotProviderRoleV1.PRIMARY,)
    if route is ShadowPhase11PilotRouteV1.L1:
        return (
            ShadowPhase11PilotProviderRoleV1.PRIMARY,
            ShadowPhase11PilotProviderRoleV1.L1,
        )
    if route is ShadowPhase11PilotRouteV1.DIRECT_L2:
        return (
            ShadowPhase11PilotProviderRoleV1.PRIMARY,
            ShadowPhase11PilotProviderRoleV1.L2,
        )
    return (
        ShadowPhase11PilotProviderRoleV1.PRIMARY,
        ShadowPhase11PilotProviderRoleV1.L1,
        ShadowPhase11PilotProviderRoleV1.L2,
    )


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11RouteCostBoundV1:
    schema_version: str
    route_bound_id: str
    route: ShadowPhase11PilotRouteV1
    model_bound_ids: tuple[str, ...]
    billable_call_count: int
    maximum_attempts_per_call: int
    current_total_micro_usd: Decimal
    conservative_total_micro_usd: Decimal
    reachability: str
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _ROUTE_FIELDS:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid route-cost-bound fields"
            )
        schema_version = _exact_text(
            "schema_version",
            values["schema_version"],
            "phase11-route-cost-bound-v1",
        )
        route = _exact_enum(
            "route",
            values["route"],
            ShadowPhase11PilotRouteV1,
        )
        expected_roles = _route_roles(route)
        expected_ids = tuple(
            _MODEL_BY_ROLE[role].identity
            for role in expected_roles
        )
        supplied_ids = values["model_bound_ids"]
        if type(supplied_ids) is not tuple:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid model_bound_ids"
            )
        model_bound_ids = tuple(
            _hash_value("model_bound_id", item)
            for item in supplied_ids
        )
        if model_bound_ids != expected_ids:
            raise ShadowPhase11PricingCostBoundValidationError(
                "route model sequence mismatch"
            )
        billable_calls = _positive_integer(
            "billable_call_count",
            values["billable_call_count"],
        )
        if billable_calls != len(expected_roles):
            raise ShadowPhase11PricingCostBoundValidationError(
                "incorrect billable call count"
            )
        maximum_attempts = _positive_integer(
            "maximum_attempts_per_call",
            values["maximum_attempts_per_call"],
        )
        if maximum_attempts != 1:
            raise ShadowPhase11PricingCostBoundValidationError(
                "maximum_attempts_per_call must equal one"
            )
        current_total = _nonnegative_money(
            "current_total_micro_usd",
            values["current_total_micro_usd"],
        )
        conservative_total = _nonnegative_money(
            "conservative_total_micro_usd",
            values["conservative_total_micro_usd"],
        )
        expected_current = sum(
            (
                _MODEL_BY_ROLE[role].current_maximum_call_cost_micro_usd
                for role in expected_roles
            ),
            Decimal("0"),
        )
        expected_conservative = sum(
            (
                _MODEL_BY_ROLE[role].maximum_call_cost_micro_usd
                for role in expected_roles
            ),
            Decimal("0"),
        )
        if (
            current_total != expected_current
            or conservative_total != expected_conservative
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "route totals are inconsistent"
            )
        reachability = _exact_text(
            "reachability",
            values["reachability"],
            "REACHABLE",
        )
        reasons = _reason_codes(values["reason_codes"])
        material = {
            "schema_version": schema_version,
            "route": route,
            "model_bound_ids": model_bound_ids,
            "billable_call_count": billable_calls,
            "maximum_attempts_per_call": maximum_attempts,
            "current_total_micro_usd": current_total,
            "conservative_total_micro_usd": conservative_total,
            "reachability": reachability,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["route_bound_id"],
            "route_bound_id",
        )
        normalized = {**material, "route_bound_id": identity}
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.route_bound_id


def _make_route_cost_bound(
    route: ShadowPhase11PilotRouteV1,
) -> ShadowPhase11RouteCostBoundV1:
    roles = _route_roles(route)
    current_total = sum(
        (
            _MODEL_BY_ROLE[role].current_maximum_call_cost_micro_usd
            for role in roles
        ),
        Decimal("0"),
    )
    conservative_total = sum(
        (
            _MODEL_BY_ROLE[role].maximum_call_cost_micro_usd
            for role in roles
        ),
        Decimal("0"),
    )
    return ShadowPhase11RouteCostBoundV1(
        schema_version="phase11-route-cost-bound-v1",
        route_bound_id=None,
        route=route,
        model_bound_ids=tuple(
            _MODEL_BY_ROLE[role].identity
            for role in roles
        ),
        billable_call_count=len(roles),
        maximum_attempts_per_call=1,
        current_total_micro_usd=current_total,
        conservative_total_micro_usd=conservative_total,
        reachability="REACHABLE",
        reason_codes=("COMMITTED_ROUTE_TOPOLOGY",),
    )


_ROUTE_COST_BOUNDS = tuple(
    _make_route_cost_bound(route)
    for route in ShadowPhase11PilotRouteV1
)

_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_id",
        "evidence_reference",
        "budget_authorization_reference",
        "model_cost_authorization_reference",
        "locked_repository_baseline",
        "locked_phase09_baseline",
        "official_sources",
        "model_cost_bounds",
        "route_cost_bounds",
        "conservative_worst_case_route",
        "conservative_worst_case_item_cost_micro_usd",
        "hard_cap_micro_usd",
        "safety_reserve_micro_usd",
        "spendable_cap_micro_usd",
        "mathematical_safe_maximum_items",
        "safe_capacity_total_micro_usd",
        "next_item_total_micro_usd",
        "fixed_freshness_window_defined",
        "launch_time_pricing_revalidation_required",
        "pricing_revalidation_status",
        "launch_readiness",
        "run_size_authorized",
        "budget_reserved_micro_usd",
        "budget_consumed_micro_usd",
        "production_effect",
        "zero_production_effect_proof",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11PilotPricingCostBoundEvidenceV1:
    schema_version: str
    evidence_id: str
    evidence_reference: str
    budget_authorization_reference: str
    model_cost_authorization_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    official_sources: tuple[ShadowPhase11OfficialPricingSourceV1, ...]
    model_cost_bounds: tuple[ShadowPhase11ModelPricingCostBoundV1, ...]
    route_cost_bounds: tuple[ShadowPhase11RouteCostBoundV1, ...]
    conservative_worst_case_route: ShadowPhase11PilotRouteV1
    conservative_worst_case_item_cost_micro_usd: Decimal
    hard_cap_micro_usd: Decimal
    safety_reserve_micro_usd: Decimal
    spendable_cap_micro_usd: Decimal
    mathematical_safe_maximum_items: int
    safe_capacity_total_micro_usd: Decimal
    next_item_total_micro_usd: Decimal
    fixed_freshness_window_defined: bool
    launch_time_pricing_revalidation_required: bool
    pricing_revalidation_status: (
        ShadowPhase11PilotPricingRevalidationStatusV1
    )
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    run_size_authorized: bool
    budget_reserved_micro_usd: Decimal
    budget_consumed_micro_usd: Decimal
    production_effect: str
    zero_production_effect_proof: str
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _EVIDENCE_FIELDS:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid pricing-evidence fields"
            )
        schema_version = _exact_text(
            "schema_version",
            values["schema_version"],
            "phase11-shadow-pilot-pricing-cost-bound-evidence-v1",
        )
        evidence_reference = _reference(
            "evidence_reference",
            values["evidence_reference"],
        )
        budget_reference = _reference(
            "budget_authorization_reference",
            values["budget_authorization_reference"],
        )
        model_reference = _reference(
            "model_cost_authorization_reference",
            values["model_cost_authorization_reference"],
        )
        if (
            evidence_reference
            != "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
            or budget_reference
            != "PHASE_11_SHADOW_PILOT_BUDGET_USD_5_001"
            or model_reference
            != "PHASE_11_PILOT_MODEL_COST_BOUNDS_001"
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "authority reference mismatch"
            )
        repository_baseline = _baseline(
            "locked_repository_baseline",
            values["locked_repository_baseline"],
        )
        phase09_baseline = _baseline(
            "locked_phase09_baseline",
            values["locked_phase09_baseline"],
        )
        if (
            repository_baseline
            != "903184dc8fbf57bae1d6490135445d1c4e05bebf"
            or phase09_baseline
            != "a84375fa85c2f318944adfe57aaabac6e43c219c"
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "locked baseline mismatch"
            )
        official_sources = _ordered_sources(values["official_sources"])
        model_cost_bounds = _ordered_models(values["model_cost_bounds"])
        route_cost_bounds = _ordered_routes(values["route_cost_bounds"])
        if tuple(item.identity for item in official_sources) != tuple(
            item.identity for item in _OFFICIAL_SOURCES
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "official source evidence does not match frozen capture"
            )
        model_by_role = {
            item.role: item
            for item in model_cost_bounds
        }
        for route_bound in route_cost_bounds:
            expected_model_ids = tuple(
                model_by_role[role].identity
                for role in _route_roles(route_bound.route)
            )
            if route_bound.model_bound_ids != expected_model_ids:
                raise ShadowPhase11PricingCostBoundValidationError(
                    "route and model evidence identities are inconsistent"
                )
        worst_route = _exact_enum(
            "conservative_worst_case_route",
            values["conservative_worst_case_route"],
            ShadowPhase11PilotRouteV1,
        )
        if worst_route is not ShadowPhase11PilotRouteV1.L1_TO_L2:
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid worst-case route"
            )
        worst_cost = _nonnegative_money(
            "conservative_worst_case_item_cost_micro_usd",
            values["conservative_worst_case_item_cost_micro_usd"],
        )
        route_by_name = {
            item.route: item
            for item in route_cost_bounds
        }
        if (
            worst_cost != Decimal("216700")
            or worst_cost
            != route_by_name[worst_route].conservative_total_micro_usd
            or worst_cost
            != max(
                item.conservative_total_micro_usd
                for item in route_cost_bounds
            )
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid worst-case item cost"
            )
        hard_cap = _nonnegative_money(
            "hard_cap_micro_usd",
            values["hard_cap_micro_usd"],
        )
        safety_reserve = _nonnegative_money(
            "safety_reserve_micro_usd",
            values["safety_reserve_micro_usd"],
        )
        spendable_cap = _nonnegative_money(
            "spendable_cap_micro_usd",
            values["spendable_cap_micro_usd"],
        )
        if (
            hard_cap != Decimal("5000000")
            or safety_reserve != Decimal("500000")
            or spendable_cap != Decimal("4500000")
            or spendable_cap != hard_cap - safety_reserve
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid monetary authority"
            )
        safe_items = _positive_integer(
            "mathematical_safe_maximum_items",
            values["mathematical_safe_maximum_items"],
        )
        safe_total = _nonnegative_money(
            "safe_capacity_total_micro_usd",
            values["safe_capacity_total_micro_usd"],
        )
        next_total = _nonnegative_money(
            "next_item_total_micro_usd",
            values["next_item_total_micro_usd"],
        )
        if (
            safe_items != 20
            or safe_total != Decimal(safe_items) * worst_cost
            or safe_total != Decimal("4334000")
            or safe_total > spendable_cap
            or next_total != Decimal(safe_items + 1) * worst_cost
            or next_total != Decimal("4550700")
            or next_total <= spendable_cap
        ):
            raise ShadowPhase11PricingCostBoundValidationError(
                "invalid mathematical capacity proof"
            )
        if values["fixed_freshness_window_defined"] is not False:
            raise ShadowPhase11PricingCostBoundValidationError(
                "fixed freshness window must remain undefined"
            )
        if values["launch_time_pricing_revalidation_required"] is not True:
            raise ShadowPhase11PricingCostBoundValidationError(
                "launch-time pricing revalidation remains required"
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
        if values["run_size_authorized"] is not False:
            raise ShadowPhase11PricingCostBoundValidationError(
                "run size is not authorized"
            )
        reserved = _nonnegative_money(
            "budget_reserved_micro_usd",
            values["budget_reserved_micro_usd"],
        )
        consumed = _nonnegative_money(
            "budget_consumed_micro_usd",
            values["budget_consumed_micro_usd"],
        )
        if reserved != 0 or consumed != 0:
            raise ShadowPhase11PricingCostBoundValidationError(
                "reservation and consumption must remain zero"
            )
        production_effect = _exact_text(
            "production_effect",
            values["production_effect"],
            "NONE",
        )
        zero_proof = _exact_text(
            "zero_production_effect_proof",
            values["zero_production_effect_proof"],
            "PROVEN_NONE",
        )
        reasons = _reason_codes(values["reason_codes"])
        material = {
            "schema_version": schema_version,
            "evidence_reference": evidence_reference,
            "budget_authorization_reference": budget_reference,
            "model_cost_authorization_reference": model_reference,
            "locked_repository_baseline": repository_baseline,
            "locked_phase09_baseline": phase09_baseline,
            "official_sources": tuple(
                item.identity for item in official_sources
            ),
            "model_cost_bounds": tuple(
                item.identity for item in model_cost_bounds
            ),
            "route_cost_bounds": tuple(
                item.identity for item in route_cost_bounds
            ),
            "conservative_worst_case_route": worst_route,
            "conservative_worst_case_item_cost_micro_usd": worst_cost,
            "hard_cap_micro_usd": hard_cap,
            "safety_reserve_micro_usd": safety_reserve,
            "spendable_cap_micro_usd": spendable_cap,
            "mathematical_safe_maximum_items": safe_items,
            "safe_capacity_total_micro_usd": safe_total,
            "next_item_total_micro_usd": next_total,
            "fixed_freshness_window_defined": False,
            "launch_time_pricing_revalidation_required": True,
            "pricing_revalidation_status": pricing_status,
            "launch_readiness": launch_readiness,
            "run_size_authorized": False,
            "budget_reserved_micro_usd": reserved,
            "budget_consumed_micro_usd": consumed,
            "production_effect": production_effect,
            "zero_production_effect_proof": zero_proof,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["evidence_id"],
            "evidence_id",
        )
        normalized = {
            **material,
            "evidence_id": identity,
            "official_sources": official_sources,
            "model_cost_bounds": model_cost_bounds,
            "route_cost_bounds": route_cost_bounds,
        }
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.evidence_id


def _ordered_sources(
    value: Any,
) -> tuple[ShadowPhase11OfficialPricingSourceV1, ...]:
    expected = tuple(ShadowPhase11OfficialPricingSourcePurposeV1)
    if (
        type(value) is not tuple
        or len(value) != len(expected)
        or any(
            type(item) is not ShadowPhase11OfficialPricingSourceV1
            for item in value
        )
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            "exactly four official sources are required"
        )
    by_purpose: dict[
        ShadowPhase11OfficialPricingSourcePurposeV1,
        ShadowPhase11OfficialPricingSourceV1,
    ] = {}
    for item in value:
        if item.purpose in by_purpose:
            raise ShadowPhase11PricingCostBoundValidationError(
                "duplicate official source purpose"
            )
        by_purpose[item.purpose] = item
    if set(by_purpose) != set(expected):
        raise ShadowPhase11PricingCostBoundValidationError(
            "official source purposes are incomplete"
        )
    return tuple(by_purpose[purpose] for purpose in expected)


def _ordered_models(
    value: Any,
) -> tuple[ShadowPhase11ModelPricingCostBoundV1, ...]:
    expected = tuple(ShadowPhase11PilotProviderRoleV1)
    if (
        type(value) is not tuple
        or len(value) != len(expected)
        or any(
            type(item) is not ShadowPhase11ModelPricingCostBoundV1
            for item in value
        )
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            "exactly three model cost bounds are required"
        )
    by_role: dict[
        ShadowPhase11PilotProviderRoleV1,
        ShadowPhase11ModelPricingCostBoundV1,
    ] = {}
    for item in value:
        if item.role in by_role:
            raise ShadowPhase11PricingCostBoundValidationError(
                "duplicate model role"
            )
        by_role[item.role] = item
    if set(by_role) != set(expected):
        raise ShadowPhase11PricingCostBoundValidationError(
            "model roles are incomplete"
        )
    return tuple(by_role[role] for role in expected)


def _ordered_routes(
    value: Any,
) -> tuple[ShadowPhase11RouteCostBoundV1, ...]:
    expected = tuple(ShadowPhase11PilotRouteV1)
    if (
        type(value) is not tuple
        or len(value) != len(expected)
        or any(
            type(item) is not ShadowPhase11RouteCostBoundV1
            for item in value
        )
    ):
        raise ShadowPhase11PricingCostBoundValidationError(
            "exactly four route cost bounds are required"
        )
    by_route: dict[
        ShadowPhase11PilotRouteV1,
        ShadowPhase11RouteCostBoundV1,
    ] = {}
    for item in value:
        if item.route in by_route:
            raise ShadowPhase11PricingCostBoundValidationError(
                "duplicate route"
            )
        by_route[item.route] = item
    if set(by_route) != set(expected):
        raise ShadowPhase11PricingCostBoundValidationError(
            "routes are incomplete"
        )
    return tuple(by_route[route] for route in expected)


def _make_evidence(
) -> ShadowPhase11PilotPricingCostBoundEvidenceV1:
    return ShadowPhase11PilotPricingCostBoundEvidenceV1(
        schema_version=(
            "phase11-shadow-pilot-pricing-cost-bound-evidence-v1"
        ),
        evidence_id=None,
        evidence_reference=(
            "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
        ),
        budget_authorization_reference=(
            "PHASE_11_SHADOW_PILOT_BUDGET_USD_5_001"
        ),
        model_cost_authorization_reference=(
            "PHASE_11_PILOT_MODEL_COST_BOUNDS_001"
        ),
        locked_repository_baseline=(
            "903184dc8fbf57bae1d6490135445d1c4e05bebf"
        ),
        locked_phase09_baseline=(
            "a84375fa85c2f318944adfe57aaabac6e43c219c"
        ),
        official_sources=_OFFICIAL_SOURCES,
        model_cost_bounds=_MODEL_COST_BOUNDS,
        route_cost_bounds=_ROUTE_COST_BOUNDS,
        conservative_worst_case_route=(
            ShadowPhase11PilotRouteV1.L1_TO_L2
        ),
        conservative_worst_case_item_cost_micro_usd=Decimal("216700"),
        hard_cap_micro_usd=Decimal("5000000"),
        safety_reserve_micro_usd=Decimal("500000"),
        spendable_cap_micro_usd=Decimal("4500000"),
        mathematical_safe_maximum_items=20,
        safe_capacity_total_micro_usd=Decimal("4334000"),
        next_item_total_micro_usd=Decimal("4550700"),
        fixed_freshness_window_defined=False,
        launch_time_pricing_revalidation_required=True,
        pricing_revalidation_status=(
            ShadowPhase11PilotPricingRevalidationStatusV1
            .REQUIRED_NOT_COMPLETED
        ),
        launch_readiness=(
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        run_size_authorized=False,
        budget_reserved_micro_usd=Decimal("0"),
        budget_consumed_micro_usd=Decimal("0"),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
        reason_codes=("OFFICIAL_PRICING_EVIDENCE_ONLY",),
    )


_EVIDENCE = _make_evidence()


def get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1(
) -> ShadowPhase11PilotPricingCostBoundEvidenceV1:
    """Return the static immutable pricing and cost-bound evidence."""

    return _EVIDENCE


__all__ = (
    "ShadowPhase11ModelPricingCostBoundV1",
    "ShadowPhase11OfficialPricingSourcePurposeV1",
    "ShadowPhase11OfficialPricingSourceV1",
    "ShadowPhase11PilotPricingCostBoundEvidenceV1",
    "ShadowPhase11PilotRouteV1",
    "ShadowPhase11PricingCostBoundValidationError",
    "ShadowPhase11RouteCostBoundV1",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1",
    "sha256_hex",
)
