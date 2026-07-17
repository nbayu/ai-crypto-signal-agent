"""Deterministic injected boundary for Phase 11 shadow provider calls.

The module owns immutable validation and bounded calls to one supplied
transport.  It performs no discovery, persistence, configuration lookup, or
production action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from engine.ai_review_payload_projector_v1 import (
    ClaudeReviewPayloadV1,
    DeepSeekReviewPayloadV1,
)
from engine.phase_11_budget_control_v1 import (
    BudgetLedgerV1,
    BudgetReservationV1,
    ProviderUsageRecordV1,
)
from engine.phase_11_shadow_input_contracts_v1 import ShadowEvaluationInputV1


UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_UTC_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)

PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
MODELS = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
ROUTES = ("L0", "L1", "L2", "L1_TO_L2")
_MODEL_PROVIDER = {
    "DEEPSEEK_PRIMARY": "DEEPSEEK",
    "CLAUDE_SONNET_L1": "ANTHROPIC",
    "CLAUDE_OPUS_L2": "ANTHROPIC",
}
_ROUTE_MODELS = {
    "L0": frozenset(("DEEPSEEK_PRIMARY",)),
    "L1": frozenset(("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1")),
    "L2": frozenset(("DEEPSEEK_PRIMARY", "CLAUDE_OPUS_L2")),
    "L1_TO_L2": frozenset(("CLAUDE_OPUS_L2",)),
}


class InvocationStatusV1(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DENIED = "DENIED"


class TransportOutcomeV1(StrEnum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    UNCERTAIN_TRANSPORT_OUTCOME = "UNCERTAIN_TRANSPORT_OUTCOME"


class TimeoutStateV1(StrEnum):
    NONE = "NONE"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    RESPONSE_TIMEOUT = "RESPONSE_TIMEOUT"


class RetryStateV1(StrEnum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    NO_RETRY = "NO_RETRY"
    RETRIED = "RETRIED"


class CircuitStateV1(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class RuntimeFailureV1(StrEnum):
    NONE = "NONE"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    UNAUTHORIZED_INVOCATION = "UNAUTHORIZED_INVOCATION"
    BUDGET_DENIED = "BUDGET_DENIED"
    RESERVATION_EXPIRED = "RESERVATION_EXPIRED"
    HARD_STOP_ACTIVE = "HARD_STOP_ACTIVE"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    USAGE_EXCEEDS_RESERVATION = "USAGE_EXCEEDS_RESERVATION"
    UNCERTAIN_TRANSPORT_OUTCOME = "UNCERTAIN_TRANSPORT_OUTCOME"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class ShadowProviderRuntimeValidationError(ValueError):
    """Raised when runtime evidence fails closed."""


class ShadowProviderTransportV1(Protocol):
    def __call__(self, request: Mapping[str, Any], timeout_ms: int) -> Any: ...


def _money_text(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _money_text(value)
    if isinstance(value, datetime):
        return _timestamp(value, "timestamp")
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _canonical(value), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowProviderRuntimeValidationError("non-canonical value") from error


def lowercase_sha256(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ShadowProviderRuntimeValidationError(f"invalid {label}")
    return value


def _hash_value(value: Any, label: str, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ShadowProviderRuntimeValidationError(f"invalid {label}")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ShadowProviderRuntimeValidationError(f"invalid {label}")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ShadowProviderRuntimeValidationError(f"invalid {label}")
    return value


def _money(value: Any, label: str, optional: bool = False) -> Decimal | None:
    if optional and value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ShadowProviderRuntimeValidationError(f"invalid {label}")
    return Decimal("0") if value == 0 else value.normalize()


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowProviderRuntimeValidationError(f"invalid {label}")
        parsed = value.astimezone(UTC)
    elif type(value) is str and _UTC_TEXT.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ShadowProviderRuntimeValidationError(f"invalid {label}") from error
    else:
        raise ShadowProviderRuntimeValidationError(f"invalid {label}")
    result = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return result.replace("+00:00", "Z").replace(".000000Z", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reasons(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowProviderRuntimeValidationError(f"invalid {label}")
    result = tuple(sorted(value))
    if len(set(result)) != len(result) or any(type(x) is not str or _REASON.fullmatch(x) is None for x in result):
        raise ShadowProviderRuntimeValidationError(f"invalid {label}")
    return result


_INVOCATION_FIELDS = frozenset((
    "schema_version", "invocation_id", "execution_id", "run_id", "call_id",
    "route", "provider", "model", "prompt_version",
    "provider_review_schema_version", "shadow_input", "shadow_input_identity",
    "event_id", "event_version", "budget_ledger", "budget_policy_id",
    "reservation", "reservation_id", "attempt_reservations", "review_request",
    "request_hash", "timeout_ms", "maximum_attempts", "circuit_state",
    "requested_at", "reason_codes", "production_effect",
    "zero_production_effect_proof",
))


@dataclass(frozen=True, init=False, slots=True)
class ShadowProviderInvocationV1:
    schema_version: str
    invocation_id: str
    execution_id: str
    run_id: str
    call_id: str
    route: str
    provider: str
    model: str
    prompt_version: str
    provider_review_schema_version: str
    shadow_input: ShadowEvaluationInputV1
    shadow_input_identity: str
    event_id: str
    event_version: int
    budget_ledger: BudgetLedgerV1
    budget_policy_id: str
    reservation: BudgetReservationV1
    reservation_id: str
    attempt_reservations: tuple[BudgetReservationV1, ...]
    review_request: DeepSeekReviewPayloadV1 | ClaudeReviewPayloadV1
    request_hash: str
    timeout_ms: int
    maximum_attempts: int
    circuit_state: str
    requested_at: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _INVOCATION_FIELDS:
            raise ShadowProviderRuntimeValidationError("invalid invocation fields")
        if values["schema_version"] != "phase11-shadow-provider-invocation-v1":
            raise ShadowProviderRuntimeValidationError("unsupported invocation schema")
        shadow_input = values["shadow_input"]
        ledger = values["budget_ledger"]
        reservation = values["reservation"]
        if type(shadow_input) is not ShadowEvaluationInputV1 or type(ledger) is not BudgetLedgerV1 or type(reservation) is not BudgetReservationV1:
            raise ShadowProviderRuntimeValidationError("invalid child evidence")
        execution_id = _identifier(values["execution_id"], "execution_id")
        run_id = _identifier(values["run_id"], "run_id")
        call_id = _identifier(values["call_id"], "call_id")
        route, provider, model = values["route"], values["provider"], values["model"]
        if route not in ROUTES or provider not in PROVIDERS or model not in MODELS:
            raise ShadowProviderRuntimeValidationError("unsupported route or reviewer")
        if _MODEL_PROVIDER[model] != provider or model not in _ROUTE_MODELS[route]:
            raise ShadowProviderRuntimeValidationError("route reviewer mismatch")
        prompt = _identifier(values["prompt_version"], "prompt_version")
        schema = _identifier(values["provider_review_schema_version"], "review schema")
        if prompt != "phase11-prompt-v1" or schema != "phase10-review-schema-v1":
            raise ShadowProviderRuntimeValidationError("unsupported prompt or schema")
        shadow_identity = _hash_value(values["shadow_input_identity"], "shadow input identity")
        event_id = _hash_value(values["event_id"], "event_id")
        event_version = _positive(values["event_version"], "event_version")
        capture = shadow_input.approved_news_capture
        if shadow_identity != shadow_input.identity or event_id != capture.event_id or event_version != capture.event_version:
            raise ShadowProviderRuntimeValidationError("shadow input mismatch")
        policy_id = _identifier(values["budget_policy_id"], "budget policy")
        policy = ledger.policy
        if policy_id != policy.policy_id or policy.status != "ACTIVE" or not policy.owner_approval_reference:
            raise ShadowProviderRuntimeValidationError("policy lacks authority")
        if ledger.circuit_or_stop_state != "OPEN":
            raise ShadowProviderRuntimeValidationError("ledger stop active")
        requested_at = _timestamp(values["requested_at"], "requested_at")
        moment = _parsed(requested_at)
        if not (_parsed(policy.starts_at) <= moment < _parsed(policy.ends_at)):
            raise ShadowProviderRuntimeValidationError("outside policy interval")
        supplied_attempts = values["attempt_reservations"]
        if type(supplied_attempts) not in (tuple, list):
            raise ShadowProviderRuntimeValidationError("invalid attempt reservations")
        attempts = tuple(supplied_attempts)
        maximum = _positive(values["maximum_attempts"], "maximum_attempts")
        if maximum > 2 or len(attempts) != maximum or any(type(x) is not BudgetReservationV1 for x in attempts):
            raise ShadowProviderRuntimeValidationError("invalid attempt count")
        if len({x.identity for x in attempts}) != len(attempts) or len({x.call_id for x in attempts}) != len(attempts):
            raise ShadowProviderRuntimeValidationError("attempt reservation reuse")
        if not attempts or attempts[0].identity != reservation.identity or values["reservation_id"] != reservation.identity or call_id != reservation.call_id:
            raise ShadowProviderRuntimeValidationError("primary reservation mismatch")
        ledger_ids = {x.identity for x in ledger.reservations}
        released = set(ledger.released_reservations)
        consumed = {x.reservation_id for x in ledger.usage_records}
        for item in attempts:
            if item.identity not in ledger_ids:
                raise ShadowProviderRuntimeValidationError("reservation missing from ledger")
            if item.policy_id != policy.policy_id or item.run_id != run_id or item.provider != provider or item.model != model:
                raise ShadowProviderRuntimeValidationError("reservation binding mismatch")
            if item.status != "RESERVED" or item.reservation_id in released or item.reservation_id in consumed:
                raise ShadowProviderRuntimeValidationError("reservation not invocable")
            if not (_parsed(item.reserved_at) <= moment < _parsed(item.expires_at)):
                raise ShadowProviderRuntimeValidationError("reservation expired")
            auth = ledger.evaluate_call_authorization(provider=provider, model=model, run_id=run_id, call_id=item.call_id)
            if not auth.allowed or auth.reservation_id != item.reservation_id:
                raise ShadowProviderRuntimeValidationError("reservation unauthorized")
        payload = values["review_request"]
        expected_type = DeepSeekReviewPayloadV1 if provider == "DEEPSEEK" else ClaudeReviewPayloadV1
        if type(payload) is not expected_type or payload.event_snapshot_id != event_id:
            raise ShadowProviderRuntimeValidationError("invalid review payload")
        request_hash = _hash_value(values["request_hash"], "request_hash")
        if request_hash != payload.payload_sha256:
            raise ShadowProviderRuntimeValidationError("request hash mismatch")
        timeout_ms = _positive(values["timeout_ms"], "timeout_ms")
        circuit = values["circuit_state"]
        if circuit not in {x.value for x in CircuitStateV1}:
            raise ShadowProviderRuntimeValidationError("invalid circuit state")
        if circuit == "HALF_OPEN" and maximum != 1:
            raise ShadowProviderRuntimeValidationError("half-open probe must be singular")
        reasons = _reasons(values["reason_codes"], "reason_codes")
        if values["production_effect"] != "NONE" or values["zero_production_effect_proof"] != "PROVEN_NONE":
            raise ShadowProviderRuntimeValidationError("invalid zero-effect proof")
        material = {
            "schema_version": values["schema_version"], "execution_id": execution_id,
            "run_id": run_id, "call_id": call_id, "route": route, "provider": provider,
            "model": model, "prompt_version": prompt, "provider_review_schema_version": schema,
            "shadow_input_identity": shadow_identity, "event_id": event_id,
            "event_version": event_version, "budget_ledger_identity": ledger.identity,
            "budget_policy_id": policy_id, "attempt_reservation_ids": tuple(x.identity for x in attempts),
            "request_hash": request_hash, "timeout_ms": timeout_ms,
            "maximum_attempts": maximum, "circuit_state": circuit,
            "requested_at": requested_at, "reason_codes": reasons,
            "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE",
        }
        identity = lowercase_sha256(material)
        supplied_identity = values["invocation_id"]
        if supplied_identity is not None and _hash_value(supplied_identity, "invocation_id") != identity:
            raise ShadowProviderRuntimeValidationError("invocation identity mismatch")
        normalized = dict(values)
        normalized.update(invocation_id=identity, execution_id=execution_id, run_id=run_id,
            call_id=call_id, prompt_version=prompt, provider_review_schema_version=schema,
            shadow_input_identity=shadow_identity, event_id=event_id, event_version=event_version,
            budget_policy_id=policy_id, reservation_id=reservation.identity,
            attempt_reservations=attempts, request_hash=request_hash, timeout_ms=timeout_ms,
            maximum_attempts=maximum, requested_at=requested_at, reason_codes=reasons,
            production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
        for name, item in normalized.items(): object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.invocation_id


_RESULT_FIELDS = frozenset((
    "schema_version", "result_id", "invocation", "invocation_id", "status",
    "provider", "model", "request_hash", "response_hash", "provider_review_identity",
    "reserved_cost", "estimated_cost", "actual_cost", "input_tokens", "output_tokens",
    "started_at", "completed_at", "latency_ms", "attempt_count", "timeout_state",
    "retry_state", "circuit_state", "transport_outcome", "failure_class",
    "reconciliation_state", "usage_record", "reason_codes", "production_effect",
    "zero_production_effect_proof",
))


@dataclass(frozen=True, init=False, slots=True)
class ShadowProviderInvocationResultV1:
    schema_version: str
    result_id: str
    invocation: ShadowProviderInvocationV1
    invocation_id: str
    status: str
    provider: str
    model: str
    request_hash: str
    response_hash: str | None
    provider_review_identity: str | None
    reserved_cost: Decimal
    estimated_cost: Decimal
    actual_cost: Decimal | None
    input_tokens: int
    output_tokens: int
    started_at: str
    completed_at: str
    latency_ms: int
    attempt_count: int
    timeout_state: str
    retry_state: str
    circuit_state: str
    transport_outcome: str
    failure_class: str
    reconciliation_state: str
    usage_record: ProviderUsageRecordV1 | None
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str
    attempt_reservation_ids: tuple[str, ...] = field(init=False)

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _RESULT_FIELDS or values["schema_version"] != "phase11-shadow-provider-invocation-result-v1":
            raise ShadowProviderRuntimeValidationError("invalid result fields")
        invocation = values["invocation"]
        if type(invocation) is not ShadowProviderInvocationV1:
            raise ShadowProviderRuntimeValidationError("invalid invocation")
        invocation_id = _hash_value(values["invocation_id"], "invocation_id")
        if invocation_id != invocation.identity:
            raise ShadowProviderRuntimeValidationError("result invocation mismatch")
        status = values["status"]
        if status not in {x.value for x in InvocationStatusV1}:
            raise ShadowProviderRuntimeValidationError("invalid status")
        provider, model = values["provider"], values["model"]
        request_hash = _hash_value(values["request_hash"], "request_hash")
        if provider != invocation.provider or model != invocation.model or request_hash != invocation.request_hash:
            raise ShadowProviderRuntimeValidationError("result reviewer mismatch")
        response_hash = _hash_value(values["response_hash"], "response_hash", True)
        review_identity = _hash_value(values["provider_review_identity"], "review identity", True)
        reserved_cost = _money(values["reserved_cost"], "reserved_cost")
        if reserved_cost != invocation.reservation.reserved_cost:
            raise ShadowProviderRuntimeValidationError("reserved cost mismatch")
        estimated = _money(values["estimated_cost"], "estimated_cost")
        actual = _money(values["actual_cost"], "actual_cost", True)
        input_tokens = _nonnegative(values["input_tokens"], "input_tokens")
        output_tokens = _nonnegative(values["output_tokens"], "output_tokens")
        started = _timestamp(values["started_at"], "started_at")
        completed = _timestamp(values["completed_at"], "completed_at")
        if _parsed(completed) < _parsed(started): raise ShadowProviderRuntimeValidationError("invalid timing")
        latency = _nonnegative(values["latency_ms"], "latency_ms")
        attempts = _nonnegative(values["attempt_count"], "attempt_count")
        if attempts > invocation.maximum_attempts: raise ShadowProviderRuntimeValidationError("too many attempts")
        timeout_state, retry_state, circuit = values["timeout_state"], values["retry_state"], values["circuit_state"]
        outcome, failure, reconciliation = values["transport_outcome"], values["failure_class"], values["reconciliation_state"]
        if timeout_state not in {x.value for x in TimeoutStateV1} or retry_state not in {x.value for x in RetryStateV1} or circuit not in {x.value for x in CircuitStateV1}:
            raise ShadowProviderRuntimeValidationError("invalid execution state")
        if outcome not in {x.value for x in TransportOutcomeV1} or failure not in {x.value for x in RuntimeFailureV1}:
            raise ShadowProviderRuntimeValidationError("invalid terminal state")
        if reconciliation not in {"NOT_REQUIRED", "RESOLVED", "RECONCILIATION_REQUIRED"}:
            raise ShadowProviderRuntimeValidationError("invalid reconciliation")
        expected_retry = "NOT_ATTEMPTED" if attempts == 0 else ("NO_RETRY" if attempts == 1 else "RETRIED")
        if retry_state != expected_retry: raise ShadowProviderRuntimeValidationError("retry evidence mismatch")
        usage = values["usage_record"]
        if usage is not None and type(usage) is not ProviderUsageRecordV1:
            raise ShadowProviderRuntimeValidationError("invalid usage evidence")
        if usage is not None:
            bound = next((x for x in invocation.attempt_reservations[:attempts] if x.reservation_id == usage.reservation_id), None)
            if bound is None: raise ShadowProviderRuntimeValidationError("usage reservation mismatch")
            if usage.policy_id != bound.policy_id or usage.run_id != bound.run_id or usage.call_id != bound.call_id or usage.provider != provider or usage.model != model or usage.request_hash != request_hash or usage.response_hash != response_hash:
                raise ShadowProviderRuntimeValidationError("usage binding mismatch")
            if estimated != usage.estimated_cost or actual != usage.actual_cost or input_tokens != usage.input_tokens or output_tokens != usage.output_tokens or started != usage.started_at or completed != usage.completed_at or latency != usage.latency_ms or attempts != usage.attempt_count or reconciliation != usage.reconciliation_status:
                raise ShadowProviderRuntimeValidationError("usage aggregate mismatch")
            if estimated > bound.reserved_cost or (actual is not None and actual > bound.reserved_cost) or input_tokens > bound.reserved_input_tokens or output_tokens > bound.reserved_output_tokens:
                raise ShadowProviderRuntimeValidationError("usage exceeds reservation")
        else:
            if estimated != 0 or actual is not None or input_tokens or output_tokens or latency:
                raise ShadowProviderRuntimeValidationError("missing usage aggregates")
        if status == "SUCCEEDED":
            if failure != "NONE" or outcome != "SUCCESS" or review_identity is None or response_hash is None or usage is None or usage.outcome != "SUCCESS" or usage.failure_class != "NONE" or reconciliation != "RESOLVED":
                raise ShadowProviderRuntimeValidationError("invalid success evidence")
        elif failure == "NONE" or review_identity is not None:
            raise ShadowProviderRuntimeValidationError("invalid failure evidence")
        if status == "DENIED" and (attempts != 0 or response_hash is not None or usage is not None or outcome != "NOT_ATTEMPTED"):
            raise ShadowProviderRuntimeValidationError("invalid denial evidence")
        if outcome == "UNCERTAIN_TRANSPORT_OUTCOME":
            if status != "FAILED" or failure != "UNCERTAIN_TRANSPORT_OUTCOME" or reconciliation != "RECONCILIATION_REQUIRED" or actual is not None or usage is None or usage.outcome not in {"TIMEOUT", "TRANSPORT_FAILURE"} or usage.failure_class != "UNCERTAIN_TRANSPORT_OUTCOME" or usage.reconciliation_status != "RECONCILIATION_REQUIRED":
                raise ShadowProviderRuntimeValidationError("uncertain evidence mismatch")
        if values["production_effect"] != "NONE" or values["zero_production_effect_proof"] != "PROVEN_NONE":
            raise ShadowProviderRuntimeValidationError("invalid zero-effect proof")
        reasons = _reasons(values["reason_codes"], "reason_codes")
        used_ids = tuple(x.identity for x in invocation.attempt_reservations[:attempts])
        material = {"invocation_id": invocation_id, "status": status, "provider": provider,
            "model": model, "request_hash": request_hash, "response_hash": response_hash,
            "provider_review_identity": review_identity, "reserved_cost": reserved_cost,
            "estimated_cost": estimated, "actual_cost": actual, "input_tokens": input_tokens,
            "output_tokens": output_tokens, "started_at": started, "completed_at": completed,
            "latency_ms": latency, "attempt_count": attempts, "attempt_reservation_ids": used_ids,
            "timeout_state": timeout_state, "retry_state": retry_state, "circuit_state": circuit,
            "transport_outcome": outcome, "failure_class": failure,
            "reconciliation_state": reconciliation, "usage_identity": None if usage is None else usage.identity,
            "reason_codes": reasons, "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE"}
        identity = lowercase_sha256(material)
        if values["result_id"] is not None and _hash_value(values["result_id"], "result_id") != identity:
            raise ShadowProviderRuntimeValidationError("result identity mismatch")
        normalized = dict(values); normalized.update(result_id=identity, invocation_id=invocation_id,
            request_hash=request_hash, response_hash=response_hash, provider_review_identity=review_identity,
            reserved_cost=reserved_cost, estimated_cost=estimated, actual_cost=actual,
            input_tokens=input_tokens, output_tokens=output_tokens, started_at=started,
            completed_at=completed, latency_ms=latency, attempt_count=attempts,
            reason_codes=reasons, production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
            attempt_reservation_ids=used_ids)
        for name, item in normalized.items(): object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.result_id


def _retry_state(count: int) -> str:
    return "NOT_ATTEMPTED" if count == 0 else ("NO_RETRY" if count == 1 else "RETRIED")


def _request(invocation: ShadowProviderInvocationV1, item: BudgetReservationV1, number: int) -> Mapping[str, Any]:
    return MappingProxyType({"provider": invocation.provider, "model": invocation.model,
        "route": invocation.route, "invocation_id": invocation.identity,
        "attempt_number": number, "attempt_reservation_id": item.identity,
        "call_id": item.call_id, "request_hash": invocation.request_hash,
        "review_request": invocation.review_request.to_mapping()})


_SUCCESS_FIELDS = frozenset((
    "outcome", "provider", "model", "invocation_id", "attempt_reservation_id",
    "attempt_count", "request_hash", "response_hash", "prompt_version",
    "provider_review_schema_version", "provider_review_identity",
    "structured_verdict", "reason_codes", "input_tokens", "output_tokens",
    "estimated_cost", "actual_cost", "started_at", "completed_at",
    "latency_ms", "provider_timestamp",
))
_BLOCKED_KEYS = frozenset((
    "api_key", "credential", "secret", "bearer_token", "authorization_header",
    "password", "private_key", "authenticated_client",
))


def _has_blocked_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(key in _BLOCKED_KEYS or _has_blocked_key(item) for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return any(_has_blocked_key(item) for item in value)
    return False


def _success_usage(response: Any, invocation: ShadowProviderInvocationV1,
                   item: BudgetReservationV1, number: int) -> tuple[ProviderUsageRecordV1, str]:
    if not isinstance(response, Mapping) or frozenset(response) != _SUCCESS_FIELDS or _has_blocked_key(response):
        raise ShadowProviderRuntimeValidationError("invalid success response fields")
    expected = {
        "outcome": "SUCCESS", "provider": invocation.provider, "model": invocation.model,
        "invocation_id": invocation.identity, "attempt_reservation_id": item.identity,
        "attempt_count": number, "request_hash": invocation.request_hash,
        "prompt_version": invocation.prompt_version,
        "provider_review_schema_version": invocation.provider_review_schema_version,
    }
    if any(response[name] != value for name, value in expected.items()):
        raise ShadowProviderRuntimeValidationError("success response identity mismatch")
    if not isinstance(response["structured_verdict"], Mapping):
        raise ShadowProviderRuntimeValidationError("invalid structured verdict")
    canonical_json_bytes(response["structured_verdict"])
    response_hash = _hash_value(response["response_hash"], "response_hash")
    hash_material = {name: value for name, value in response.items() if name != "response_hash"}
    if response_hash != lowercase_sha256(hash_material):
        raise ShadowProviderRuntimeValidationError("response hash mismatch")
    review_identity = _hash_value(response["provider_review_identity"], "review identity")
    input_tokens = _nonnegative(response["input_tokens"], "input_tokens")
    output_tokens = _nonnegative(response["output_tokens"], "output_tokens")
    estimated = _money(response["estimated_cost"], "estimated_cost")
    actual = _money(response["actual_cost"], "actual_cost")
    started = _timestamp(response["started_at"], "started_at")
    completed = _timestamp(response["completed_at"], "completed_at")
    _timestamp(response["provider_timestamp"], "provider_timestamp")
    latency = _nonnegative(response["latency_ms"], "latency_ms")
    reasons = _reasons(response["reason_codes"], "reason_codes")
    if _parsed(completed) < _parsed(started):
        raise ShadowProviderRuntimeValidationError("invalid response timing")
    if estimated > item.reserved_cost or actual > item.reserved_cost or input_tokens > item.reserved_input_tokens or output_tokens > item.reserved_output_tokens:
        raise ShadowProviderRuntimeValidationError("response usage exceeds reservation")
    usage = ProviderUsageRecordV1(schema_version="phase11-provider-usage-v1",
        usage_record_id=f"usage-{invocation.identity[:16]}-{number}",
        reservation_id=item.reservation_id, policy_id=item.policy_id, run_id=item.run_id,
        call_id=item.call_id, provider=item.provider, model=item.model,
        request_hash=invocation.request_hash, response_hash=response_hash,
        input_tokens=input_tokens, output_tokens=output_tokens, estimated_cost=estimated,
        actual_cost=actual, started_at=started, completed_at=completed,
        latency_ms=latency, attempt_count=number, outcome="SUCCESS",
        reconciliation_status="RESOLVED", failure_class="NONE", reason_codes=reasons)
    return usage, review_identity


def _result(invocation: ShadowProviderInvocationV1, *, status: str, count: int,
            outcome: str, failure: str, reasons: tuple[str, ...], timeout: str = "NONE",
            reconciliation: str = "NOT_REQUIRED", response_hash: str | None = None,
            review_identity: str | None = None, usage: ProviderUsageRecordV1 | None = None) -> ShadowProviderInvocationResultV1:
    if usage is None:
        estimated, actual, input_tokens, output_tokens, latency = Decimal("0"), None, 0, 0, 0
        started = completed = invocation.requested_at
    else:
        estimated, actual = usage.estimated_cost, usage.actual_cost
        input_tokens, output_tokens, latency = usage.input_tokens, usage.output_tokens, usage.latency_ms
        started, completed = usage.started_at, usage.completed_at
    return ShadowProviderInvocationResultV1(schema_version="phase11-shadow-provider-invocation-result-v1",
        result_id=None, invocation=invocation, invocation_id=invocation.identity, status=status,
        provider=invocation.provider, model=invocation.model, request_hash=invocation.request_hash,
        response_hash=response_hash, provider_review_identity=review_identity,
        reserved_cost=invocation.reservation.reserved_cost, estimated_cost=estimated,
        actual_cost=actual, input_tokens=input_tokens, output_tokens=output_tokens,
        started_at=started, completed_at=completed, latency_ms=latency, attempt_count=count,
        timeout_state=timeout, retry_state=_retry_state(count), circuit_state=invocation.circuit_state,
        transport_outcome=outcome, failure_class=failure, reconciliation_state=reconciliation,
        usage_record=usage, reason_codes=reasons, production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE")


@dataclass(frozen=True, slots=True)
class ShadowProviderRuntimeV1:
    transport: ShadowProviderTransportV1

    def __post_init__(self) -> None:
        if not callable(self.transport): raise ShadowProviderRuntimeValidationError("transport must be callable")

    def invoke(self, invocation: ShadowProviderInvocationV1) -> ShadowProviderInvocationResultV1:
        if type(invocation) is not ShadowProviderInvocationV1:
            raise ShadowProviderRuntimeValidationError("invalid invocation")
        if invocation.circuit_state == "OPEN":
            return _result(invocation, status="DENIED", count=0, outcome="NOT_ATTEMPTED",
                failure="CIRCUIT_OPEN", reasons=("CIRCUIT_OPEN",))
        retryable = {"TIMEOUT", "TRANSPORT_FAILURE"}
        for number, item in enumerate(invocation.attempt_reservations, 1):
            auth = invocation.budget_ledger.evaluate_call_authorization(provider=invocation.provider,
                model=invocation.model, run_id=invocation.run_id, call_id=item.call_id)
            if not auth.allowed or auth.reservation_id != item.reservation_id:
                return _result(invocation, status="DENIED", count=number-1,
                    outcome="NOT_ATTEMPTED" if number == 1 else "TRANSPORT_FAILURE",
                    failure="BUDGET_DENIED", reasons=("BUDGET_DENIED",))
            try:
                response = self.transport(_request(invocation, item, number), invocation.timeout_ms)
            except TimeoutError:
                response = {"outcome": "TIMEOUT"}
            except ConnectionError:
                response = {"outcome": "TRANSPORT_FAILURE"}
            except Exception:
                response = {"outcome": "TRANSPORT_FAILURE"}
            if not isinstance(response, Mapping):
                return _result(invocation, status="FAILED", count=number,
                    outcome="MALFORMED_RESPONSE", failure="MALFORMED_RESPONSE",
                    reasons=("MALFORMED_RESPONSE",))
            if set(response) == {"outcome"} and response["outcome"] in {x.value for x in TransportOutcomeV1} - {"NOT_ATTEMPTED", "SUCCESS", "IDENTITY_MISMATCH"}:
                terminal = response["outcome"]
                if terminal in retryable and number < invocation.maximum_attempts and invocation.circuit_state == "CLOSED":
                    continue
                if terminal == "UNCERTAIN_TRANSPORT_OUTCOME":
                    response_hash = lowercase_sha256({"invocation_id": invocation.identity, "attempt": item.identity, "outcome": terminal})
                    usage = ProviderUsageRecordV1(schema_version="phase11-provider-usage-v1",
                        usage_record_id=f"usage-{invocation.identity[:16]}-{number}", reservation_id=item.reservation_id,
                        policy_id=item.policy_id, run_id=item.run_id, call_id=item.call_id,
                        provider=item.provider, model=item.model, request_hash=invocation.request_hash,
                        response_hash=response_hash, input_tokens=0, output_tokens=0,
                        estimated_cost=item.reserved_cost, actual_cost=None,
                        started_at=invocation.requested_at, completed_at=invocation.requested_at,
                        latency_ms=0, attempt_count=number, outcome="TRANSPORT_FAILURE",
                        reconciliation_status="RECONCILIATION_REQUIRED",
                        failure_class="UNCERTAIN_TRANSPORT_OUTCOME", reason_codes=("TRANSPORT_UNCERTAIN",))
                    return _result(invocation, status="FAILED", count=number, outcome=terminal,
                        failure=terminal, reasons=("RECONCILIATION_REQUIRED",),
                        reconciliation="RECONCILIATION_REQUIRED", response_hash=response_hash, usage=usage)
                return _result(invocation, status="FAILED", count=number, outcome=terminal,
                    failure=terminal, reasons=(terminal,), timeout="RESPONSE_TIMEOUT" if terminal == "TIMEOUT" else "NONE")
            try:
                usage, review_identity = _success_usage(response, invocation, item, number)
            except ShadowProviderRuntimeValidationError:
                return _result(invocation, status="FAILED", count=number,
                    outcome="MALFORMED_RESPONSE", failure="MALFORMED_RESPONSE",
                    reasons=("MALFORMED_RESPONSE",))
            return _result(invocation, status="SUCCEEDED", count=number, outcome="SUCCESS",
                failure="NONE", reasons=usage.reason_codes, reconciliation="RESOLVED",
                response_hash=usage.response_hash, review_identity=review_identity, usage=usage)
        raise ShadowProviderRuntimeValidationError("invalid bounded attempt state")


__all__ = (
    "CircuitStateV1", "InvocationStatusV1", "RetryStateV1", "RuntimeFailureV1",
    "ShadowProviderInvocationResultV1", "ShadowProviderInvocationV1",
    "ShadowProviderRuntimeV1", "ShadowProviderRuntimeValidationError",
    "ShadowProviderTransportV1", "TimeoutStateV1", "TransportOutcomeV1",
    "canonical_json_bytes", "lowercase_sha256",
)
