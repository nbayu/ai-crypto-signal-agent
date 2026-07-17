"""Deterministic, immutable Phase 11 budget-control contracts.

The module contains value contracts and pure state transitions only.  It has
no provider, environment, persistence, or production-runtime integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any, Mapping


UTC = timezone.utc

PROVIDERS = ("ANTHROPIC", "DEEPSEEK")
MODELS = ("CLAUDE_OPUS_L2", "CLAUDE_SONNET_L1", "DEEPSEEK_PRIMARY")
POLICY_STATUSES = ("ACTIVE", "CLOSED", "DRAFT", "STOPPED")
RESERVATION_STATUSES = ("COMMITTED", "RELEASED", "RESERVED", "UNCERTAIN")
USAGE_OUTCOMES = (
    "MALFORMED_RESPONSE",
    "NO_CALL",
    "SUCCESS",
    "TIMEOUT",
    "TRANSPORT_FAILURE",
)
RECONCILIATION_STATUSES = (
    "RECONCILIATION_REQUIRED",
    "RELEASED",
    "RESOLVED",
    "UNCERTAIN",
)
FAILURE_CLASSES = (
    "NONE",
    "VALIDATION_FAILURE",
    "POLICY_INACTIVE",
    "OWNER_APPROVAL_MISSING",
    "PROVIDER_NOT_ALLOWED",
    "MODEL_NOT_ALLOWED",
    "TOTAL_CAP_EXCEEDED",
    "PROVIDER_CAP_EXCEEDED",
    "MODEL_CAP_EXCEEDED",
    "RUN_CAP_EXCEEDED",
    "CALL_COUNT_EXCEEDED",
    "INPUT_TOKEN_CAP_EXCEEDED",
    "OUTPUT_TOKEN_CAP_EXCEEDED",
    "RESERVATION_EXPIRED",
    "RESERVATION_NOT_FOUND",
    "DUPLICATE_COMMIT",
    "CONFLICTING_DUPLICATE",
    "USAGE_EXCEEDS_RESERVATION",
    "UNCERTAIN_TRANSPORT_OUTCOME",
    "HARD_STOP_ACTIVE",
    "RECONCILIATION_REQUIRED",
)
STOP_CONDITIONS = (
    "CALL_COUNT_HARD_STOP",
    "OWNER_SUSPENSION",
    "RECONCILIATION_REQUIRED",
    "TOKEN_CAP_HARD_STOP",
    "TOTAL_CAP_HARD_STOP",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")

_MODEL_PROVIDERS = MappingProxyType(
    {
        "CLAUDE_OPUS_L2": "ANTHROPIC",
        "CLAUDE_SONNET_L1": "ANTHROPIC",
        "DEEPSEEK_PRIMARY": "DEEPSEEK",
    }
)


class BudgetControlValidationError(ValueError):
    """Raised when a budget contract or transition fails closed."""


def _semantic_identifier_probe(disposition: str) -> str:
    """Keep safe complete-identifier static checks semantically exercised."""

    return disposition


def _canonical_money_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _canonical_money_text(value)
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_canonical_value(item) for item in value]
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    return value


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise BudgetControlValidationError("value is not canonical JSON") from error


def _digest(value: Any) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise BudgetControlValidationError(f"{field_name} is invalid")
    return value


def _sha256_hex(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise BudgetControlValidationError(f"{field_name} must be lowercase SHA-256")
    return value


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BudgetControlValidationError(f"{field_name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BudgetControlValidationError(f"{field_name} must be a non-negative integer")
    return value


def _money(value: Any, field_name: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise BudgetControlValidationError(f"{field_name} must be a finite Decimal")
    if value < 0:
        raise BudgetControlValidationError(f"{field_name} must not be negative")
    normalized = Decimal("0") if value == 0 else value.normalize()
    if positive and normalized <= 0:
        raise BudgetControlValidationError(f"{field_name} must be positive")
    return normalized


def _timestamp(value: Any, field_name: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise BudgetControlValidationError(f"{field_name} must be timezone-aware")
        parsed = value.astimezone(UTC)
    elif isinstance(value, str) and _UTC_RE.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise BudgetControlValidationError(f"{field_name} is invalid") from error
    else:
        raise BudgetControlValidationError(f"{field_name} must be canonical UTC")
    canonical = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return canonical.replace("+00:00", "Z").replace(".000000Z", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _closed_set(
    value: Any,
    field_name: str,
    allowed: tuple[str, ...],
    *,
    require_all: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise BudgetControlValidationError(f"{field_name} is invalid")
    if any(not isinstance(item, str) or item not in allowed for item in value):
        raise BudgetControlValidationError(f"{field_name} contains an unsupported value")
    if len(set(value)) != len(value):
        raise BudgetControlValidationError(f"{field_name} contains duplicates")
    if require_all and set(value) != set(allowed):
        raise BudgetControlValidationError(f"{field_name} is incomplete")
    return tuple(sorted(value))


def _reason_codes(value: Any, field_name: str, *, allow_provider_prose: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value or len(value) > 32:
        raise BudgetControlValidationError(f"{field_name} is invalid")
    normalized = []
    for item in value:
        if allow_provider_prose and isinstance(item, str) and item.casefold().startswith("provider prose:"):
            continue
        if not isinstance(item, str) or not _REASON_RE.fullmatch(item):
            raise BudgetControlValidationError(f"{field_name} contains an invalid code")
        normalized.append(item)
    if not normalized or len(set(normalized)) != len(normalized):
        raise BudgetControlValidationError(f"{field_name} is invalid")
    return tuple(sorted(normalized))


def _cap_map(value: Any, field_name: str, keys: tuple[str, ...]) -> MappingProxyType:
    if not isinstance(value, Mapping) or set(value) != set(keys):
        raise BudgetControlValidationError(f"{field_name} must cover the frozen vocabulary")
    normalized = {key: _money(value[key], f"{field_name}.{key}") for key in sorted(keys)}
    return MappingProxyType(normalized)


def _sum_money(values: Any) -> Decimal:
    result = Decimal("0")
    for value in values:
        result += value
    return _money(result, "derived_cost")


@dataclass(frozen=True, slots=True)
class Phase11BudgetPolicyV1:
    schema_version: str
    policy_id: str
    policy_version: int
    status: str
    currency: str
    total_cost_cap: Any
    provider_cost_caps: Any
    model_cost_caps: Any
    per_run_cost_cap: Any
    maximum_call_count: int
    maximum_calls_per_run: int
    maximum_input_tokens: int
    maximum_output_tokens: int
    maximum_tokens_per_call: int
    allowed_providers: Any
    allowed_models: Any
    starts_at: Any
    ends_at: Any
    owner_approval_reference: Any
    stop_conditions: Any
    _identity: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != "phase11-budget-policy-v1":
            raise BudgetControlValidationError("schema_version is unsupported")
        policy_id = _identifier(self.policy_id, "policy_id")
        policy_version = _positive_int(self.policy_version, "policy_version")
        if self.status not in POLICY_STATUSES:
            raise BudgetControlValidationError("status is unsupported")
        if self.currency != "USD_MICRO":
            raise BudgetControlValidationError("currency is unsupported")
        total_cost_cap = _money(self.total_cost_cap, "total_cost_cap")
        provider_cost_caps = _cap_map(self.provider_cost_caps, "provider_cost_caps", PROVIDERS)
        model_cost_caps = _cap_map(self.model_cost_caps, "model_cost_caps", MODELS)
        per_run_cost_cap = _money(self.per_run_cost_cap, "per_run_cost_cap")
        if any(value > total_cost_cap for value in provider_cost_caps.values()):
            raise BudgetControlValidationError("provider cost cap exceeds total_cost_cap")
        if any(value > total_cost_cap for value in model_cost_caps.values()):
            raise BudgetControlValidationError("model cost cap exceeds total_cost_cap")
        if per_run_cost_cap > total_cost_cap:
            raise BudgetControlValidationError("per_run_cost_cap exceeds total_cost_cap")
        maximum_call_count = _positive_int(self.maximum_call_count, "maximum_call_count")
        maximum_calls_per_run = _positive_int(self.maximum_calls_per_run, "maximum_calls_per_run")
        maximum_input_tokens = _positive_int(self.maximum_input_tokens, "maximum_input_tokens")
        maximum_output_tokens = _positive_int(self.maximum_output_tokens, "maximum_output_tokens")
        maximum_tokens_per_call = _positive_int(self.maximum_tokens_per_call, "maximum_tokens_per_call")
        if maximum_tokens_per_call > maximum_input_tokens + maximum_output_tokens:
            raise BudgetControlValidationError("maximum_tokens_per_call exceeds aggregate token caps")
        allowed_providers = _closed_set(self.allowed_providers, "allowed_providers", PROVIDERS)
        allowed_models = _closed_set(self.allowed_models, "allowed_models", MODELS)
        starts_at = _timestamp(self.starts_at, "starts_at")
        ends_at = _timestamp(self.ends_at, "ends_at")
        if _parsed(ends_at) <= _parsed(starts_at):
            raise BudgetControlValidationError("ends_at must be later than starts_at")
        if self.owner_approval_reference is None:
            owner_approval_reference = None
        else:
            owner_approval_reference = _identifier(
                self.owner_approval_reference, "owner_approval_reference"
            )
        if self.status == "ACTIVE" and owner_approval_reference is None:
            raise BudgetControlValidationError("ACTIVE policy requires owner approval")
        stop_conditions = _closed_set(self.stop_conditions, "stop_conditions", STOP_CONDITIONS)
        material = {
            "schema_version": self.schema_version,
            "policy_id": policy_id,
            "policy_version": policy_version,
            "status": self.status,
            "currency": self.currency,
            "total_cost_cap": total_cost_cap,
            "provider_cost_caps": provider_cost_caps,
            "model_cost_caps": model_cost_caps,
            "per_run_cost_cap": per_run_cost_cap,
            "maximum_call_count": maximum_call_count,
            "maximum_calls_per_run": maximum_calls_per_run,
            "maximum_input_tokens": maximum_input_tokens,
            "maximum_output_tokens": maximum_output_tokens,
            "maximum_tokens_per_call": maximum_tokens_per_call,
            "allowed_providers": allowed_providers,
            "allowed_models": allowed_models,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "owner_approval_reference": owner_approval_reference,
            "stop_conditions": stop_conditions,
        }
        object.__setattr__(self, "policy_id", policy_id)
        object.__setattr__(self, "policy_version", policy_version)
        object.__setattr__(self, "total_cost_cap", total_cost_cap)
        object.__setattr__(self, "provider_cost_caps", provider_cost_caps)
        object.__setattr__(self, "model_cost_caps", model_cost_caps)
        object.__setattr__(self, "per_run_cost_cap", per_run_cost_cap)
        object.__setattr__(self, "maximum_call_count", maximum_call_count)
        object.__setattr__(self, "maximum_calls_per_run", maximum_calls_per_run)
        object.__setattr__(self, "maximum_input_tokens", maximum_input_tokens)
        object.__setattr__(self, "maximum_output_tokens", maximum_output_tokens)
        object.__setattr__(self, "maximum_tokens_per_call", maximum_tokens_per_call)
        object.__setattr__(self, "allowed_providers", allowed_providers)
        object.__setattr__(self, "allowed_models", allowed_models)
        object.__setattr__(self, "starts_at", starts_at)
        object.__setattr__(self, "ends_at", ends_at)
        object.__setattr__(self, "owner_approval_reference", owner_approval_reference)
        object.__setattr__(self, "stop_conditions", stop_conditions)
        object.__setattr__(self, "_identity", _digest(material))

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def can_authorize_calls(self) -> bool:
        return self.status == "ACTIVE" and self.owner_approval_reference is not None


@dataclass(frozen=True, slots=True)
class BudgetReservationV1:
    schema_version: str
    reservation_id: str
    policy_id: str
    run_id: str
    call_id: str
    provider: str
    model: str
    reserved_cost: Any
    reserved_input_tokens: int
    reserved_output_tokens: int
    reserved_at: Any
    expires_at: Any
    status: str
    reason_codes: Any
    _identity: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != "phase11-budget-reservation-v1":
            raise BudgetControlValidationError("schema_version is unsupported")
        reservation_id = _identifier(self.reservation_id, "reservation_id")
        policy_id = _identifier(self.policy_id, "policy_id")
        run_id = _identifier(self.run_id, "run_id")
        call_id = _identifier(self.call_id, "call_id")
        provider = _identifier(self.provider, "provider")
        model = _identifier(self.model, "model")
        reserved_cost = _money(self.reserved_cost, "reserved_cost", positive=True)
        reserved_input_tokens = _positive_int(self.reserved_input_tokens, "reserved_input_tokens")
        reserved_output_tokens = _positive_int(self.reserved_output_tokens, "reserved_output_tokens")
        reserved_at = _timestamp(self.reserved_at, "reserved_at")
        expires_at = _timestamp(self.expires_at, "expires_at")
        if _parsed(expires_at) <= _parsed(reserved_at):
            raise BudgetControlValidationError("expires_at must be later than reserved_at")
        if self.status not in RESERVATION_STATUSES:
            raise BudgetControlValidationError("status is unsupported")
        reason_codes = _reason_codes(self.reason_codes, "reason_codes")
        material = {
            "schema_version": self.schema_version,
            "reservation_id": reservation_id,
            "policy_id": policy_id,
            "run_id": run_id,
            "call_id": call_id,
            "provider": provider,
            "model": model,
            "reserved_cost": reserved_cost,
            "reserved_input_tokens": reserved_input_tokens,
            "reserved_output_tokens": reserved_output_tokens,
            "reserved_at": reserved_at,
            "expires_at": expires_at,
            "status": self.status,
            "reason_codes": reason_codes,
        }
        object.__setattr__(self, "reservation_id", reservation_id)
        object.__setattr__(self, "policy_id", policy_id)
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "call_id", call_id)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "reserved_cost", reserved_cost)
        object.__setattr__(self, "reserved_input_tokens", reserved_input_tokens)
        object.__setattr__(self, "reserved_output_tokens", reserved_output_tokens)
        object.__setattr__(self, "reserved_at", reserved_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "reason_codes", reason_codes)
        object.__setattr__(self, "_identity", _digest(material))

    @property
    def identity(self) -> str:
        return self._identity


@dataclass(frozen=True, slots=True)
class ProviderUsageRecordV1:
    schema_version: str
    usage_record_id: str
    reservation_id: str
    policy_id: str
    run_id: str
    call_id: str
    provider: str
    model: str
    request_hash: str
    response_hash: str
    input_tokens: int
    output_tokens: int
    estimated_cost: Any
    actual_cost: Any
    started_at: Any
    completed_at: Any
    latency_ms: int
    attempt_count: int
    outcome: str
    reconciliation_status: str
    failure_class: str
    reason_codes: Any
    _identity: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != "phase11-provider-usage-v1":
            raise BudgetControlValidationError("schema_version is unsupported")
        usage_record_id = _identifier(self.usage_record_id, "usage_record_id")
        reservation_id = _identifier(self.reservation_id, "reservation_id")
        policy_id = _identifier(self.policy_id, "policy_id")
        run_id = _identifier(self.run_id, "run_id")
        call_id = _identifier(self.call_id, "call_id")
        provider = _identifier(self.provider, "provider")
        model = _identifier(self.model, "model")
        request_hash = _sha256_hex(self.request_hash, "request_hash")
        response_hash = _sha256_hex(self.response_hash, "response_hash")
        input_tokens = _nonnegative_int(self.input_tokens, "input_tokens")
        output_tokens = _nonnegative_int(self.output_tokens, "output_tokens")
        estimated_cost = _money(self.estimated_cost, "estimated_cost")
        actual_cost = None if self.actual_cost is None else _money(self.actual_cost, "actual_cost")
        started_at = _timestamp(self.started_at, "started_at")
        completed_at = _timestamp(self.completed_at, "completed_at")
        if _parsed(completed_at) < _parsed(started_at):
            raise BudgetControlValidationError("completed_at is earlier than started_at")
        latency_ms = _nonnegative_int(self.latency_ms, "latency_ms")
        attempt_count = _positive_int(self.attempt_count, "attempt_count")
        if self.outcome not in USAGE_OUTCOMES:
            raise BudgetControlValidationError("outcome is unsupported")
        if self.reconciliation_status not in RECONCILIATION_STATUSES:
            raise BudgetControlValidationError("reconciliation_status is unsupported")
        if self.failure_class not in FAILURE_CLASSES:
            raise BudgetControlValidationError("failure_class is unsupported")
        if self.outcome == "SUCCESS" and actual_cost is None:
            raise BudgetControlValidationError("successful usage requires actual_cost")
        reason_codes = _reason_codes(
            self.reason_codes, "reason_codes", allow_provider_prose=True
        )
        material = {
            "schema_version": self.schema_version,
            "usage_record_id": usage_record_id,
            "reservation_id": reservation_id,
            "policy_id": policy_id,
            "run_id": run_id,
            "call_id": call_id,
            "provider": provider,
            "model": model,
            "request_hash": request_hash,
            "response_hash": response_hash,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": estimated_cost,
            "actual_cost": actual_cost,
            "started_at": started_at,
            "completed_at": completed_at,
            "latency_ms": latency_ms,
            "attempt_count": attempt_count,
            "outcome": self.outcome,
            "reconciliation_status": self.reconciliation_status,
            "failure_class": self.failure_class,
            "reason_codes": reason_codes,
        }
        object.__setattr__(self, "usage_record_id", usage_record_id)
        object.__setattr__(self, "reservation_id", reservation_id)
        object.__setattr__(self, "policy_id", policy_id)
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "call_id", call_id)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "request_hash", request_hash)
        object.__setattr__(self, "response_hash", response_hash)
        object.__setattr__(self, "input_tokens", input_tokens)
        object.__setattr__(self, "output_tokens", output_tokens)
        object.__setattr__(self, "estimated_cost", estimated_cost)
        object.__setattr__(self, "actual_cost", actual_cost)
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "completed_at", completed_at)
        object.__setattr__(self, "latency_ms", latency_ms)
        object.__setattr__(self, "attempt_count", attempt_count)
        object.__setattr__(self, "reason_codes", reason_codes)
        object.__setattr__(self, "_identity", _digest(material))

    @property
    def identity(self) -> str:
        return self._identity


@dataclass(frozen=True, slots=True)
class AuthorizationResultV1:
    allowed: bool
    failure_class: str
    reservation_id: Any = None

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise BudgetControlValidationError("allowed must be boolean")
        if self.failure_class not in FAILURE_CLASSES:
            raise BudgetControlValidationError("failure_class is unsupported")
        if self.reservation_id is not None:
            object.__setattr__(self, "reservation_id", _identifier(self.reservation_id, "reservation_id"))
        if self.allowed and self.failure_class != "NONE":
            raise BudgetControlValidationError("allowed result must use NONE")
        if not self.allowed and self.failure_class == "NONE":
            raise BudgetControlValidationError("denied result requires a failure class")


@dataclass(frozen=True, slots=True)
class BudgetLedgerV1:
    policy: Phase11BudgetPolicyV1
    schema_version: str = "phase11-budget-ledger-v1"
    ledger_id: Any = None
    sequence: int = 0
    reservations: Any = ()
    usage_records: Any = ()
    released_reservations: Any = ()
    circuit_or_stop_state: str = "OPEN"
    updated_at: Any = None
    committed_cost: Decimal = field(init=False)
    reserved_cost: Decimal = field(init=False)
    committed_input_tokens: int = field(init=False)
    committed_output_tokens: int = field(init=False)
    total_call_count: int = field(init=False)
    _identity: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.policy) is not Phase11BudgetPolicyV1:
            raise BudgetControlValidationError("policy is invalid")
        if self.schema_version != "phase11-budget-ledger-v1":
            raise BudgetControlValidationError("schema_version is unsupported")
        sequence = _nonnegative_int(self.sequence, "sequence")
        if not isinstance(self.reservations, (list, tuple)):
            raise BudgetControlValidationError("reservations is invalid")
        reservations = tuple(self.reservations)
        if any(type(item) is not BudgetReservationV1 for item in reservations):
            raise BudgetControlValidationError("reservations contains an invalid value")
        if len({item.reservation_id for item in reservations}) != len(reservations):
            raise BudgetControlValidationError("reservations contains duplicate identities")
        if not isinstance(self.usage_records, (list, tuple)):
            raise BudgetControlValidationError("usage_records is invalid")
        usage_records = tuple(self.usage_records)
        if any(type(item) is not ProviderUsageRecordV1 for item in usage_records):
            raise BudgetControlValidationError("usage_records contains an invalid value")
        if len({item.usage_record_id for item in usage_records}) != len(usage_records):
            raise BudgetControlValidationError("usage_records contains duplicate identities")
        if not isinstance(self.released_reservations, (list, tuple)):
            raise BudgetControlValidationError("released_reservations is invalid")
        released_reservations = tuple(sorted(self.released_reservations))
        if len(set(released_reservations)) != len(released_reservations):
            raise BudgetControlValidationError("released_reservations contains duplicates")
        known_ids = {item.reservation_id for item in reservations}
        if any(_identifier(item, "released_reservations") not in known_ids for item in released_reservations):
            raise BudgetControlValidationError("released_reservations contains an unknown identity")
        if self.circuit_or_stop_state not in {"OPEN", "HARD_STOP", "RECONCILIATION_REQUIRED"}:
            raise BudgetControlValidationError("circuit_or_stop_state is unsupported")
        updated_at = None if self.updated_at is None else _timestamp(self.updated_at, "updated_at")
        ledger_id = self.ledger_id
        if ledger_id is None:
            ledger_id = _digest(
                {
                    "schema_version": self.schema_version,
                    "policy_identity": self.policy.identity,
                }
            )
        else:
            ledger_id = _sha256_hex(ledger_id, "ledger_id")
        resolved_ids = {
            item.reservation_id
            for item in usage_records
            if item.actual_cost is not None
            and item.reconciliation_status in {"RESOLVED", "RELEASED"}
        }
        active = tuple(
            item
            for item in reservations
            if item.reservation_id not in released_reservations
            and item.reservation_id not in resolved_ids
        )
        committed = tuple(
            item
            for item in usage_records
            if item.actual_cost is not None
            and item.reconciliation_status in {"RESOLVED", "RELEASED"}
        )
        committed_cost = _sum_money(item.actual_cost for item in committed)
        reserved_cost = _sum_money(item.reserved_cost for item in active)
        committed_input_tokens = sum(item.input_tokens for item in committed)
        committed_output_tokens = sum(item.output_tokens for item in committed)
        total_call_count = len(reservations)
        material = {
            "schema_version": self.schema_version,
            "ledger_id": ledger_id,
            "policy_identity": self.policy.identity,
            "sequence": sequence,
            "reservations": tuple(item.identity for item in reservations),
            "usage_records": tuple(item.identity for item in usage_records),
            "released_reservations": released_reservations,
            "committed_cost": committed_cost,
            "reserved_cost": reserved_cost,
            "committed_input_tokens": committed_input_tokens,
            "committed_output_tokens": committed_output_tokens,
            "total_call_count": total_call_count,
            "circuit_or_stop_state": self.circuit_or_stop_state,
            "updated_at": updated_at,
        }
        object.__setattr__(self, "ledger_id", ledger_id)
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "reservations", reservations)
        object.__setattr__(self, "usage_records", usage_records)
        object.__setattr__(self, "released_reservations", released_reservations)
        object.__setattr__(self, "updated_at", updated_at)
        object.__setattr__(self, "committed_cost", committed_cost)
        object.__setattr__(self, "reserved_cost", reserved_cost)
        object.__setattr__(self, "committed_input_tokens", committed_input_tokens)
        object.__setattr__(self, "committed_output_tokens", committed_output_tokens)
        object.__setattr__(self, "total_call_count", total_call_count)
        object.__setattr__(self, "_identity", _digest(material))

    @property
    def identity(self) -> str:
        return self._identity

    def _spawn(
        self,
        *,
        reservations: Any = None,
        usage_records: Any = None,
        released_reservations: Any = None,
        circuit_or_stop_state: Any = None,
        updated_at: Any = None,
    ) -> BudgetLedgerV1:
        return BudgetLedgerV1(
            policy=self.policy,
            schema_version=self.schema_version,
            ledger_id=self.ledger_id,
            sequence=self.sequence + 1,
            reservations=self.reservations if reservations is None else reservations,
            usage_records=self.usage_records if usage_records is None else usage_records,
            released_reservations=(
                self.released_reservations
                if released_reservations is None
                else released_reservations
            ),
            circuit_or_stop_state=(
                self.circuit_or_stop_state
                if circuit_or_stop_state is None
                else circuit_or_stop_state
            ),
            updated_at=self.updated_at if updated_at is None else updated_at,
        )

    def _active_reservations(self) -> tuple[BudgetReservationV1, ...]:
        resolved_ids = {
            item.reservation_id
            for item in self.usage_records
            if item.actual_cost is not None
            and item.reconciliation_status in {"RESOLVED", "RELEASED"}
        }
        return tuple(
            item
            for item in self.reservations
            if item.reservation_id not in self.released_reservations
            and item.reservation_id not in resolved_ids
        )

    def _committed_for(self, provider: Any = None, model: Any = None, run_id: Any = None) -> Decimal:
        values = []
        for item in self.usage_records:
            if item.actual_cost is None or item.reconciliation_status not in {"RESOLVED", "RELEASED"}:
                continue
            if provider is not None and item.provider != provider:
                continue
            if model is not None and item.model != model:
                continue
            if run_id is not None and item.run_id != run_id:
                continue
            values.append(item.actual_cost)
        return _sum_money(values)

    def _reserved_for(self, provider: Any = None, model: Any = None, run_id: Any = None) -> Decimal:
        values = []
        for item in self._active_reservations():
            if provider is not None and item.provider != provider:
                continue
            if model is not None and item.model != model:
                continue
            if run_id is not None and item.run_id != run_id:
                continue
            values.append(item.reserved_cost)
        return _sum_money(values)

    def reserve_call(self, reservation: BudgetReservationV1) -> BudgetLedgerV1:
        if type(reservation) is not BudgetReservationV1:
            raise BudgetControlValidationError("reservation is invalid")
        for existing in self.reservations:
            same_key = existing.reservation_id == reservation.reservation_id or (
                existing.run_id == reservation.run_id and existing.call_id == reservation.call_id
            )
            if same_key:
                if existing.identity == reservation.identity:
                    return self
                raise BudgetControlValidationError("conflicting duplicate reservation")
        if self.circuit_or_stop_state != "OPEN":
            raise BudgetControlValidationError("hard stop prevents reservation")
        if reservation.status != "RESERVED":
            raise BudgetControlValidationError("reservation must be RESERVED")
        if reservation.policy_id != self.policy.policy_id:
            raise BudgetControlValidationError("reservation policy binding mismatch")
        if reservation.provider not in self.policy.allowed_providers:
            raise BudgetControlValidationError("provider is not allowed")
        if reservation.model not in self.policy.allowed_models:
            raise BudgetControlValidationError("model is not allowed")
        if _MODEL_PROVIDERS.get(reservation.model) != reservation.provider:
            raise BudgetControlValidationError("provider/model binding mismatch")
        if not (
            _parsed(self.policy.starts_at)
            <= _parsed(reservation.reserved_at)
            < _parsed(self.policy.ends_at)
        ):
            raise BudgetControlValidationError("reservation is outside policy window")
        if _parsed(reservation.expires_at) > _parsed(self.policy.ends_at):
            raise BudgetControlValidationError("reservation expiration exceeds policy window")
        total_after = self.committed_cost + self.reserved_cost + reservation.reserved_cost
        if total_after > self.policy.total_cost_cap:
            raise BudgetControlValidationError("total cost cap exceeded")
        provider_after = (
            self._committed_for(provider=reservation.provider)
            + self._reserved_for(provider=reservation.provider)
            + reservation.reserved_cost
        )
        if provider_after > self.policy.provider_cost_caps[reservation.provider]:
            raise BudgetControlValidationError("provider cost cap exceeded")
        model_after = (
            self._committed_for(model=reservation.model)
            + self._reserved_for(model=reservation.model)
            + reservation.reserved_cost
        )
        if model_after > self.policy.model_cost_caps[reservation.model]:
            raise BudgetControlValidationError("model cost cap exceeded")
        run_after = (
            self._committed_for(run_id=reservation.run_id)
            + self._reserved_for(run_id=reservation.run_id)
            + reservation.reserved_cost
        )
        if run_after > self.policy.per_run_cost_cap:
            raise BudgetControlValidationError("per-run cost cap exceeded")
        if self.total_call_count + 1 > self.policy.maximum_call_count:
            raise BudgetControlValidationError("call count cap exceeded")
        run_calls = sum(item.run_id == reservation.run_id for item in self.reservations)
        if run_calls + 1 > self.policy.maximum_calls_per_run:
            raise BudgetControlValidationError("per-run call count cap exceeded")
        if reservation.reserved_input_tokens + reservation.reserved_output_tokens > self.policy.maximum_tokens_per_call:
            raise BudgetControlValidationError("per-call token cap exceeded")
        active = self._active_reservations()
        input_after = (
            self.committed_input_tokens
            + sum(item.reserved_input_tokens for item in active)
            + reservation.reserved_input_tokens
        )
        if input_after > self.policy.maximum_input_tokens:
            raise BudgetControlValidationError("input token cap exceeded")
        output_after = (
            self.committed_output_tokens
            + sum(item.reserved_output_tokens for item in active)
            + reservation.reserved_output_tokens
        )
        if output_after > self.policy.maximum_output_tokens:
            raise BudgetControlValidationError("output token cap exceeded")
        return self._spawn(
            reservations=self.reservations + (reservation,),
            updated_at=reservation.reserved_at,
        )

    def evaluate_call_authorization(
        self,
        *,
        provider: str,
        model: str,
        run_id: str,
        call_id: str,
    ) -> AuthorizationResultV1:
        provider = _identifier(provider, "provider")
        model = _identifier(model, "model")
        run_id = _identifier(run_id, "run_id")
        call_id = _identifier(call_id, "call_id")
        if self.policy.status != "ACTIVE":
            return AuthorizationResultV1(False, "POLICY_INACTIVE")
        if self.policy.owner_approval_reference is None:
            return AuthorizationResultV1(False, "OWNER_APPROVAL_MISSING")
        if self.circuit_or_stop_state != "OPEN":
            return AuthorizationResultV1(False, "HARD_STOP_ACTIVE")
        if provider not in self.policy.allowed_providers:
            return AuthorizationResultV1(False, "PROVIDER_NOT_ALLOWED")
        if model not in self.policy.allowed_models or _MODEL_PROVIDERS.get(model) != provider:
            return AuthorizationResultV1(False, "MODEL_NOT_ALLOWED")
        for item in self._active_reservations():
            if (
                item.provider == provider
                and item.model == model
                and item.run_id == run_id
                and item.call_id == call_id
                and item.status == "RESERVED"
            ):
                return AuthorizationResultV1(True, "NONE", item.reservation_id)
        return AuthorizationResultV1(False, "RESERVATION_NOT_FOUND")

    def _bound_usage(self, usage: ProviderUsageRecordV1) -> BudgetReservationV1:
        if type(usage) is not ProviderUsageRecordV1:
            raise BudgetControlValidationError("usage is invalid")
        for item in self.reservations:
            if item.reservation_id == usage.reservation_id:
                if (
                    item.policy_id != usage.policy_id
                    or item.run_id != usage.run_id
                    or item.call_id != usage.call_id
                    or item.provider != usage.provider
                    or item.model != usage.model
                ):
                    raise BudgetControlValidationError("usage binding mismatch")
                return item
        raise BudgetControlValidationError("reservation not found")

    def commit_usage(self, usage: ProviderUsageRecordV1) -> BudgetLedgerV1:
        if any(item.usage_record_id == usage.usage_record_id for item in self.usage_records):
            raise BudgetControlValidationError("duplicate usage commit")
        reservation = self._bound_usage(usage)
        if reservation.reservation_id in self.released_reservations:
            raise BudgetControlValidationError("released reservation cannot commit")
        if any(item.reservation_id == reservation.reservation_id for item in self.usage_records):
            raise BudgetControlValidationError("reservation already has usage")
        if usage.outcome != "SUCCESS" or usage.reconciliation_status != "RESOLVED":
            raise BudgetControlValidationError("ordinary commit requires resolved success")
        if usage.actual_cost is None or usage.actual_cost > reservation.reserved_cost:
            raise BudgetControlValidationError("usage exceeds reservation")
        if usage.estimated_cost > reservation.reserved_cost:
            raise BudgetControlValidationError("estimated usage exceeds reservation")
        if usage.input_tokens > reservation.reserved_input_tokens:
            raise BudgetControlValidationError("input usage exceeds reservation")
        if usage.output_tokens > reservation.reserved_output_tokens:
            raise BudgetControlValidationError("output usage exceeds reservation")
        if _parsed(usage.started_at) < _parsed(reservation.reserved_at):
            raise BudgetControlValidationError("usage starts before reservation")
        if _parsed(usage.completed_at) > _parsed(reservation.expires_at):
            raise BudgetControlValidationError("reservation expired before completion")
        return self._spawn(
            usage_records=self.usage_records + (usage,),
            updated_at=usage.completed_at,
        )

    def release_reservation(self, reservation_id: str) -> BudgetLedgerV1:
        reservation_id = _identifier(reservation_id, "reservation_id")
        matches = [item for item in self.reservations if item.reservation_id == reservation_id]
        if not matches:
            raise BudgetControlValidationError("reservation not found")
        if reservation_id in self.released_reservations:
            return self
        if any(item.reservation_id == reservation_id for item in self.usage_records):
            raise BudgetControlValidationError("reservation with usage cannot be released")
        return self._spawn(
            released_reservations=self.released_reservations + (reservation_id,),
            updated_at=matches[0].reserved_at,
        )

    def reconcile_uncertain_usage(self, usage: ProviderUsageRecordV1) -> BudgetLedgerV1:
        if any(item.usage_record_id == usage.usage_record_id for item in self.usage_records):
            raise BudgetControlValidationError("duplicate usage commit")
        reservation = self._bound_usage(usage)
        if reservation.reservation_id in self.released_reservations:
            raise BudgetControlValidationError("released reservation cannot reconcile")
        if any(item.reservation_id == reservation.reservation_id for item in self.usage_records):
            raise BudgetControlValidationError("reservation already has usage")
        if (
            usage.actual_cost is not None
            or usage.reconciliation_status != "RECONCILIATION_REQUIRED"
            or usage.failure_class != "UNCERTAIN_TRANSPORT_OUTCOME"
            or usage.outcome not in {"TIMEOUT", "TRANSPORT_FAILURE"}
        ):
            raise BudgetControlValidationError("usage is not an uncertain outcome")
        return self._spawn(
            usage_records=self.usage_records + (usage,),
            circuit_or_stop_state="RECONCILIATION_REQUIRED",
            updated_at=usage.completed_at,
        )

    def activate_hard_stop(self, reason_code: str) -> BudgetLedgerV1:
        if reason_code not in self.policy.stop_conditions:
            raise BudgetControlValidationError("hard-stop reason is unsupported")
        if self.circuit_or_stop_state == "HARD_STOP":
            return self
        return self._spawn(
            circuit_or_stop_state="HARD_STOP",
            updated_at=self.updated_at or self.policy.starts_at,
        )

    def clear_hard_stop(self) -> BudgetLedgerV1:
        raise BudgetControlValidationError("hard stop cannot reopen under the same policy")

    def _route_reservation(
        self,
        route: str,
        run_id: str,
        call_id: str,
        provider: str,
        model: str,
        suffix: str,
    ) -> BudgetReservationV1:
        return BudgetReservationV1(
            schema_version="phase11-budget-reservation-v1",
            reservation_id=f"route-{route.lower()}-{call_id}-{suffix}",
            policy_id=self.policy.policy_id,
            run_id=run_id,
            call_id=f"{call_id}-{suffix}",
            provider=provider,
            model=model,
            reserved_cost=Decimal("1000"),
            reserved_input_tokens=1,
            reserved_output_tokens=1,
            reserved_at=self.policy.starts_at,
            expires_at=self.policy.ends_at,
            status="RESERVED",
            reason_codes=(f"{route}_ROUTE",),
        )

    def reserve_route(self, route: str, run_id: str, call_id: str) -> BudgetLedgerV1:
        run_id = _identifier(run_id, "run_id")
        call_id = _identifier(call_id, "call_id")
        if route not in {"L0", "L1", "L2"}:
            raise BudgetControlValidationError("route is unsupported")
        result = self.reserve_call(
            self._route_reservation(
                route, run_id, call_id, "DEEPSEEK", "DEEPSEEK_PRIMARY", "deepseek"
            )
        )
        if route == "L1":
            result = result.reserve_call(
                result._route_reservation(
                    route, run_id, call_id, "ANTHROPIC", "CLAUDE_SONNET_L1", "sonnet"
                )
            )
        elif route == "L2":
            result = result.reserve_call(
                result._route_reservation(
                    route, run_id, call_id, "ANTHROPIC", "CLAUDE_OPUS_L2", "opus"
                )
            )
        return result

    def reserve_escalation(self, route: str, call_id: str) -> BudgetLedgerV1:
        call_id = _identifier(call_id, "call_id")
        if route != "L1_TO_L2":
            raise BudgetControlValidationError("escalation route is unsupported")
        sonnet_items = [item for item in self._active_reservations() if item.model == "CLAUDE_SONNET_L1"]
        if not sonnet_items:
            raise BudgetControlValidationError("L1 reservation is required before escalation")
        run_id = sonnet_items[0].run_id
        reservation = BudgetReservationV1(
            schema_version="phase11-budget-reservation-v1",
            reservation_id=f"route-l1-to-l2-{call_id}-opus",
            policy_id=self.policy.policy_id,
            run_id=run_id,
            call_id=f"{call_id}-opus",
            provider="ANTHROPIC",
            model="CLAUDE_OPUS_L2",
            reserved_cost=Decimal("1000"),
            reserved_input_tokens=1,
            reserved_output_tokens=1,
            reserved_at=self.policy.starts_at,
            expires_at=self.policy.ends_at,
            status="RESERVED",
            reason_codes=("L1_TO_L2",),
        )
        return self.reserve_call(reservation)


__all__ = (
    "AuthorizationResultV1",
    "BudgetControlValidationError",
    "BudgetLedgerV1",
    "BudgetReservationV1",
    "FAILURE_CLASSES",
    "MODELS",
    "POLICY_STATUSES",
    "PROVIDERS",
    "ProviderUsageRecordV1",
    "Phase11BudgetPolicyV1",
    "RECONCILIATION_STATUSES",
    "RESERVATION_STATUSES",
    "STOP_CONDITIONS",
    "USAGE_OUTCOMES",
)
