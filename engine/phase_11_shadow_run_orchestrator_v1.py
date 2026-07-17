"""Deterministic Phase 11 shadow provider-run coordination.

This module composes immutable Phase 10 payloads, the Phase 11 budget ledger,
the generic shadow-provider runtime, and explicitly supplied transport
adapters.  It owns no credentials, provider clients, persistence, final
adjudication, comparison, or production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

from engine.ai_review_payload_projector_v1 import (
    ClaudeReviewPayloadV1,
    DeepSeekReviewPayloadV1,
)
from engine.phase_11_budget_control_v1 import (
    BudgetControlValidationError,
    BudgetLedgerV1,
    BudgetReservationV1,
)
from engine.phase_11_provider_transport_adapters_v1 import (
    AnthropicShadowTransportAdapterV1,
    DeepSeekShadowTransportAdapterV1,
)
from engine.phase_11_shadow_input_contracts_v1 import ShadowEvaluationInputV1
from engine.phase_11_shadow_provider_runtime_v1 import (
    ShadowProviderInvocationResultV1,
    ShadowProviderInvocationV1,
    ShadowProviderRuntimeV1,
)


UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_UTC_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)

_ADAPTER_TYPES = {
    ("DEEPSEEK", "DEEPSEEK_PRIMARY"): DeepSeekShadowTransportAdapterV1,
    ("ANTHROPIC", "CLAUDE_SONNET_L1"): AnthropicShadowTransportAdapterV1,
    ("ANTHROPIC", "CLAUDE_OPUS_L2"): AnthropicShadowTransportAdapterV1,
}
_PAYLOAD_TYPES = {
    "DEEPSEEK": DeepSeekReviewPayloadV1,
    "ANTHROPIC": ClaudeReviewPayloadV1,
}
_ROUTE_GRAPHS = {
    "L0": (("L0", "DEEPSEEK", "DEEPSEEK_PRIMARY"),),
    "L1": (
        ("L1", "DEEPSEEK", "DEEPSEEK_PRIMARY"),
        ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1"),
    ),
    "L2": (
        ("L2", "DEEPSEEK", "DEEPSEEK_PRIMARY"),
        ("L2", "ANTHROPIC", "CLAUDE_OPUS_L2"),
    ),
    "L1_TO_L2": (
        ("L1", "DEEPSEEK", "DEEPSEEK_PRIMARY"),
        ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1"),
        ("L1_TO_L2", "ANTHROPIC", "CLAUDE_OPUS_L2"),
    ),
}


class ShadowRunStatusV1(StrEnum):
    COMPLETED = "COMPLETED"
    DENIED = "DENIED"
    FAILED_CLOSED = "FAILED_CLOSED"
    PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class ShadowRunFailureV1(StrEnum):
    NONE = "NONE"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    INVALID_ROUTE_GRAPH = "INVALID_ROUTE_GRAPH"
    MISSING_ADAPTER = "MISSING_ADAPTER"
    ADAPTER_MISMATCH = "ADAPTER_MISMATCH"
    BUDGET_DENIED = "BUDGET_DENIED"
    HARD_STOP_ACTIVE = "HARD_STOP_ACTIVE"
    RESERVATION_MISSING = "RESERVATION_MISSING"
    PROVIDER_RUNTIME_FAILURE = "PROVIDER_RUNTIME_FAILURE"
    TIMEOUT = "TIMEOUT"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    USAGE_EXCEEDS_RESERVATION = "USAGE_EXCEEDS_RESERVATION"
    UNCERTAIN_TRANSPORT_OUTCOME = "UNCERTAIN_TRANSPORT_OUTCOME"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"


class ShadowRunReconciliationV1(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    RESOLVED = "RESOLVED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class ShadowProviderRunOrchestratorValidationError(ValueError):
    """Raised when immutable run evidence is malformed or inconsistent."""


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        return _timestamp(value, "timestamp")
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic canonical UTF-8 JSON."""

    try:
        return json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowProviderRunOrchestratorValidationError(
            "non-canonical run metadata"
        ) from error


def lowercase_sha256(value: Any) -> str:
    """Return lowercase SHA-256 over canonical structured JSON."""

    return sha256(canonical_json_bytes(value)).hexdigest()


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ShadowProviderRunOrchestratorValidationError(f"invalid {label}")
    return value


def _hash_value(
    value: Any, label: str, *, optional: bool = False
) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ShadowProviderRunOrchestratorValidationError(f"invalid {label}")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ShadowProviderRunOrchestratorValidationError(f"invalid {label}")
    return value


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowProviderRunOrchestratorValidationError(
                f"invalid {label}"
            )
        parsed = value.astimezone(UTC)
    elif type(value) is str and _UTC_TEXT.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ShadowProviderRunOrchestratorValidationError(
                f"invalid {label}"
            ) from error
    else:
        raise ShadowProviderRunOrchestratorValidationError(f"invalid {label}")
    normalized = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return normalized.replace("+00:00", "Z").replace(".000000Z", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reasons(value: Any, label: str = "reason_codes") -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowProviderRunOrchestratorValidationError(f"invalid {label}")
    result = tuple(sorted(value))
    if len(set(result)) != len(result) or any(
        type(item) is not str or _REASON.fullmatch(item) is None
        for item in result
    ):
        raise ShadowProviderRunOrchestratorValidationError(f"invalid {label}")
    return result


_CALL_PLAN_FIELDS = frozenset(
    (
        "schema_version",
        "call_plan_id",
        "execution_id",
        "run_id",
        "call_index",
        "call_id",
        "route",
        "reviewer_tier",
        "provider",
        "model",
        "review_request",
        "request_hash",
        "attempt_reservations",
        "timeout_ms",
        "maximum_attempts",
        "circuit_state",
        "adapter_identity",
        "reason_codes",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowRunCallPlanV1:
    schema_version: str
    call_plan_id: str
    execution_id: str
    run_id: str
    call_index: int
    call_id: str
    route: str
    reviewer_tier: str
    provider: str
    model: str
    review_request: DeepSeekReviewPayloadV1 | ClaudeReviewPayloadV1
    request_hash: str
    attempt_reservations: tuple[BudgetReservationV1, ...]
    timeout_ms: int
    maximum_attempts: int
    circuit_state: str
    adapter_identity: str
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _CALL_PLAN_FIELDS:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid call-plan fields"
            )
        if values["schema_version"] != "phase11-shadow-run-call-plan-v1":
            raise ShadowProviderRunOrchestratorValidationError(
                "unsupported call-plan schema"
            )
        execution_id = _identifier(values["execution_id"], "execution_id")
        run_id = _identifier(values["run_id"], "run_id")
        call_index = _positive(values["call_index"], "call_index")
        call_id = _identifier(values["call_id"], "call_id")
        route = values["route"]
        provider = values["provider"]
        model = values["model"]
        if (
            route not in _ROUTE_GRAPHS
            or (provider, model) not in _ADAPTER_TYPES
            or (route, provider, model)
            not in {
                item
                for graph in _ROUTE_GRAPHS.values()
                for item in graph
            }
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid call route binding"
            )
        if values["reviewer_tier"] != model:
            raise ShadowProviderRunOrchestratorValidationError(
                "reviewer tier mismatch"
            )
        payload = values["review_request"]
        if type(payload) is not _PAYLOAD_TYPES[provider]:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid review payload"
            )
        request_hash = _hash_value(values["request_hash"], "request_hash")
        if request_hash != payload.payload_sha256:
            raise ShadowProviderRunOrchestratorValidationError(
                "request hash mismatch"
            )
        supplied = values["attempt_reservations"]
        if type(supplied) not in (tuple, list):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid attempt reservations"
            )
        reservations = tuple(supplied)
        maximum_attempts = _positive(
            values["maximum_attempts"], "maximum_attempts"
        )
        if (
            maximum_attempts > 2
            or len(reservations) != maximum_attempts
            or any(type(item) is not BudgetReservationV1 for item in reservations)
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid attempt reservation count"
            )
        if (
            len({item.identity for item in reservations}) != len(reservations)
            or len({item.call_id for item in reservations}) != len(reservations)
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "attempt reservation reuse"
            )
        for attempt_index, reservation in enumerate(reservations):
            if (
                reservation.run_id != run_id
                or reservation.provider != provider
                or reservation.model != model
                or reservation.status != "RESERVED"
                or (attempt_index == 0 and reservation.call_id != call_id)
            ):
                raise ShadowProviderRunOrchestratorValidationError(
                    "attempt reservation binding mismatch"
                )
        timeout_ms = _positive(values["timeout_ms"], "timeout_ms")
        circuit_state = values["circuit_state"]
        if circuit_state not in {"CLOSED", "OPEN", "HALF_OPEN"}:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid circuit state"
            )
        if circuit_state == "HALF_OPEN" and maximum_attempts != 1:
            raise ShadowProviderRunOrchestratorValidationError(
                "half-open call must be singular"
            )
        adapter_identity = _hash_value(
            values["adapter_identity"], "adapter_identity"
        )
        reason_codes = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "execution_id": execution_id,
            "run_id": run_id,
            "call_index": call_index,
            "call_id": call_id,
            "route": route,
            "reviewer_tier": model,
            "provider": provider,
            "model": model,
            "review_request_identity": request_hash,
            "attempt_reservation_ids": tuple(
                item.identity for item in reservations
            ),
            "timeout_ms": timeout_ms,
            "maximum_attempts": maximum_attempts,
            "circuit_state": circuit_state,
            "adapter_identity": adapter_identity,
            "reason_codes": reason_codes,
        }
        identity = lowercase_sha256(material)
        supplied_identity = _hash_value(
            values["call_plan_id"], "call_plan_id", optional=True
        )
        if supplied_identity is not None and supplied_identity != identity:
            raise ShadowProviderRunOrchestratorValidationError(
                "call-plan identity mismatch"
            )
        normalized = dict(values)
        normalized.update(
            call_plan_id=identity,
            execution_id=execution_id,
            run_id=run_id,
            call_index=call_index,
            call_id=call_id,
            reviewer_tier=model,
            request_hash=request_hash,
            attempt_reservations=reservations,
            timeout_ms=timeout_ms,
            maximum_attempts=maximum_attempts,
            adapter_identity=adapter_identity,
            reason_codes=reason_codes,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.call_plan_id


_RUN_PLAN_FIELDS = frozenset(
    (
        "schema_version",
        "run_plan_id",
        "execution_id",
        "run_id",
        "shadow_input",
        "shadow_input_identity",
        "route",
        "l1_to_l2_escalation_identity",
        "budget_ledger_before",
        "budget_ledger_before_id",
        "call_plans",
        "started_at",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowProviderRunPlanV1:
    schema_version: str
    run_plan_id: str
    execution_id: str
    run_id: str
    shadow_input: ShadowEvaluationInputV1
    shadow_input_identity: str
    route: str
    l1_to_l2_escalation_identity: str | None
    budget_ledger_before: BudgetLedgerV1
    budget_ledger_before_id: str
    call_plans: tuple[ShadowRunCallPlanV1, ...]
    started_at: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _RUN_PLAN_FIELDS:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid run-plan fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-provider-run-plan-v1"
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "unsupported run-plan schema"
            )
        execution_id = _identifier(values["execution_id"], "execution_id")
        run_id = _identifier(values["run_id"], "run_id")
        shadow_input = values["shadow_input"]
        ledger = values["budget_ledger_before"]
        if (
            type(shadow_input) is not ShadowEvaluationInputV1
            or type(ledger) is not BudgetLedgerV1
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid run-plan child evidence"
            )
        shadow_identity = _hash_value(
            values["shadow_input_identity"], "shadow_input_identity"
        )
        ledger_identity = _hash_value(
            values["budget_ledger_before_id"], "budget_ledger_before_id"
        )
        if shadow_identity != shadow_input.identity:
            raise ShadowProviderRunOrchestratorValidationError(
                "shadow input identity mismatch"
            )
        if ledger_identity != ledger.identity:
            raise ShadowProviderRunOrchestratorValidationError(
                "ledger identity mismatch"
            )
        route = values["route"]
        if route not in _ROUTE_GRAPHS:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid route graph"
            )
        supplied_calls = values["call_plans"]
        if type(supplied_calls) not in (tuple, list):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid call plans"
            )
        call_plans = tuple(supplied_calls)
        expected = _ROUTE_GRAPHS[route]
        actual = tuple(
            (item.route, item.provider, item.model)
            for item in call_plans
            if type(item) is ShadowRunCallPlanV1
        )
        if (
            len(actual) != len(call_plans)
            or actual != expected
            or tuple(item.call_index for item in call_plans)
            != tuple(range(1, len(call_plans) + 1))
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid route graph"
            )
        if any(
            item.execution_id != execution_id or item.run_id != run_id
            for item in call_plans
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "call-plan lineage mismatch"
            )
        if len({item.call_id for item in call_plans}) != len(call_plans):
            raise ShadowProviderRunOrchestratorValidationError(
                "duplicate call identity"
            )
        reservation_identities = tuple(
            reservation.identity
            for item in call_plans
            for reservation in item.attempt_reservations
        )
        if len(set(reservation_identities)) != len(reservation_identities):
            raise ShadowProviderRunOrchestratorValidationError(
                "reservation reused across calls"
            )
        escalation = _hash_value(
            values["l1_to_l2_escalation_identity"],
            "l1_to_l2_escalation_identity",
            optional=True,
        )
        if (route == "L1_TO_L2") != (escalation is not None):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid escalation evidence"
            )
        started_at = _timestamp(values["started_at"], "started_at")
        reasons = _reasons(values["reason_codes"])
        if (
            values["production_effect"] != "NONE"
            or values["zero_production_effect_proof"] != "PROVEN_NONE"
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid zero-effect proof"
            )
        material = {
            "schema_version": values["schema_version"],
            "execution_id": execution_id,
            "run_id": run_id,
            "shadow_input_identity": shadow_identity,
            "route": route,
            "l1_to_l2_escalation_identity": escalation,
            "budget_ledger_before_identity": ledger_identity,
            "call_plan_identities": tuple(item.identity for item in call_plans),
            "started_at": started_at,
            "reason_codes": reasons,
            "production_effect": "NONE",
            "zero_production_effect_proof": "PROVEN_NONE",
        }
        identity = lowercase_sha256(material)
        supplied_identity = _hash_value(
            values["run_plan_id"], "run_plan_id", optional=True
        )
        if supplied_identity is not None and supplied_identity != identity:
            raise ShadowProviderRunOrchestratorValidationError(
                "run-plan identity mismatch"
            )
        normalized = dict(values)
        normalized.update(
            run_plan_id=identity,
            execution_id=execution_id,
            run_id=run_id,
            shadow_input_identity=shadow_identity,
            l1_to_l2_escalation_identity=escalation,
            budget_ledger_before_id=ledger_identity,
            call_plans=call_plans,
            started_at=started_at,
            reason_codes=reasons,
            production_effect="NONE",
            zero_production_effect_proof="PROVEN_NONE",
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.run_plan_id


_RUN_RESULT_FIELDS = frozenset(
    (
        "schema_version",
        "run_result_id",
        "run_plan_id",
        "execution_id",
        "run_id",
        "route",
        "completed_call_plan_ids",
        "invocation_results",
        "ledger_before_id",
        "ledger_after",
        "ledger_after_id",
        "status",
        "failure_class",
        "reconciliation_state",
        "first_failed_call_plan_id",
        "started_at",
        "completed_at",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowProviderRunResultV1:
    schema_version: str
    run_result_id: str
    run_plan_id: str
    execution_id: str
    run_id: str
    route: str
    completed_call_plan_ids: tuple[str, ...]
    invocation_results: tuple[ShadowProviderInvocationResultV1, ...]
    ledger_before_id: str
    ledger_after: BudgetLedgerV1
    ledger_after_id: str
    status: str
    failure_class: str
    reconciliation_state: str
    first_failed_call_plan_id: str | None
    started_at: str
    completed_at: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _RUN_RESULT_FIELDS:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid run-result fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-provider-run-result-v1"
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "unsupported run-result schema"
            )
        run_plan_id = _hash_value(values["run_plan_id"], "run_plan_id")
        execution_id = _identifier(values["execution_id"], "execution_id")
        run_id = _identifier(values["run_id"], "run_id")
        route = values["route"]
        if route not in _ROUTE_GRAPHS:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid result route"
            )
        completed = values["completed_call_plan_ids"]
        invocation_results = values["invocation_results"]
        if type(completed) not in (tuple, list) or type(invocation_results) not in (
            tuple,
            list,
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid result children"
            )
        completed_ids = tuple(
            _hash_value(item, "completed_call_plan_id") for item in completed
        )
        results = tuple(invocation_results)
        if any(type(item) is not ShadowProviderInvocationResultV1 for item in results):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid invocation result"
            )
        ledger_before_id = _hash_value(
            values["ledger_before_id"], "ledger_before_id"
        )
        ledger_after = values["ledger_after"]
        if type(ledger_after) is not BudgetLedgerV1:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid ledger after"
            )
        ledger_after_id = _hash_value(
            values["ledger_after_id"], "ledger_after_id"
        )
        if ledger_after_id != ledger_after.identity:
            raise ShadowProviderRunOrchestratorValidationError(
                "ledger-after identity mismatch"
            )
        status = values["status"]
        failure = values["failure_class"]
        reconciliation = values["reconciliation_state"]
        if status not in {item.value for item in ShadowRunStatusV1}:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid run status"
            )
        if failure not in {item.value for item in ShadowRunFailureV1}:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid run failure"
            )
        if reconciliation not in {
            item.value for item in ShadowRunReconciliationV1
        }:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid run reconciliation"
            )
        first_failed = _hash_value(
            values["first_failed_call_plan_id"],
            "first_failed_call_plan_id",
            optional=True,
        )
        if status == "COMPLETED":
            if failure != "NONE" or first_failed is not None:
                raise ShadowProviderRunOrchestratorValidationError(
                    "invalid completed result"
                )
        elif failure == "NONE":
            raise ShadowProviderRunOrchestratorValidationError(
                "failed result lacks failure"
            )
        if status == "DENIED" and (completed_ids or results):
            raise ShadowProviderRunOrchestratorValidationError(
                "denied result contains invocation evidence"
            )
        if status == "RECONCILIATION_REQUIRED" and (
            reconciliation != "RECONCILIATION_REQUIRED"
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "uncertain result is falsely resolved"
            )
        started_at = _timestamp(values["started_at"], "started_at")
        completed_at = _timestamp(values["completed_at"], "completed_at")
        if _parsed(completed_at) < _parsed(started_at):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid result timing"
            )
        reasons = _reasons(values["reason_codes"])
        if (
            values["production_effect"] != "NONE"
            or values["zero_production_effect_proof"] != "PROVEN_NONE"
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid zero-effect proof"
            )
        material = {
            "run_plan_id": run_plan_id,
            "execution_id": execution_id,
            "run_id": run_id,
            "route": route,
            "completed_call_plan_ids": completed_ids,
            "invocation_result_ids": tuple(item.identity for item in results),
            "ledger_before_id": ledger_before_id,
            "ledger_after_id": ledger_after_id,
            "status": status,
            "failure_class": failure,
            "reconciliation_state": reconciliation,
            "first_failed_call_plan_id": first_failed,
            "started_at": started_at,
            "completed_at": completed_at,
            "reason_codes": reasons,
            "production_effect": "NONE",
            "zero_production_effect_proof": "PROVEN_NONE",
        }
        identity = lowercase_sha256(material)
        supplied_identity = _hash_value(
            values["run_result_id"], "run_result_id", optional=True
        )
        if supplied_identity is not None and supplied_identity != identity:
            raise ShadowProviderRunOrchestratorValidationError(
                "run-result identity mismatch"
            )
        normalized = dict(values)
        normalized.update(
            run_result_id=identity,
            run_plan_id=run_plan_id,
            execution_id=execution_id,
            run_id=run_id,
            completed_call_plan_ids=completed_ids,
            invocation_results=results,
            ledger_before_id=ledger_before_id,
            ledger_after_id=ledger_after_id,
            first_failed_call_plan_id=first_failed,
            started_at=started_at,
            completed_at=completed_at,
            reason_codes=reasons,
            production_effect="NONE",
            zero_production_effect_proof="PROVEN_NONE",
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.run_result_id


def _adapter_map(value: Any) -> Mapping[Any, Any]:
    if not isinstance(value, Mapping) or not value:
        raise ShadowProviderRunOrchestratorValidationError(
            "adapters must be a non-empty mapping"
        )
    normalized: dict[tuple[str, str], Any] = {}
    for key, adapter in value.items():
        if (
            type(key) is not tuple
            or len(key) != 2
            or key not in _ADAPTER_TYPES
            or type(adapter) is not _ADAPTER_TYPES[key]
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid adapter mapping"
            )
        endpoint = adapter.endpoint_binding
        if (
            endpoint.provider != key[0]
            or endpoint.contract_model != key[1]
            or type(adapter.identity) is not str
            or _HASH.fullmatch(adapter.identity) is None
        ):
            raise ShadowProviderRunOrchestratorValidationError(
                "adapter binding mismatch"
            )
        normalized[key] = adapter
    return MappingProxyType(normalized)


@dataclass(frozen=True, init=False, slots=True)
class ShadowProviderRunOrchestratorV1:
    adapters: Mapping[Any, Any]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != {"adapters"}:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid orchestrator fields"
            )
        object.__setattr__(self, "adapters", _adapter_map(values["adapters"]))

    def _preflight(
        self, plan: ShadowProviderRunPlanV1
    ) -> tuple[str | None, str | None]:
        ledger = plan.budget_ledger_before
        policy = ledger.policy
        if policy.status != "ACTIVE" or not policy.owner_approval_reference:
            return "BUDGET_DENIED", None
        if ledger.circuit_or_stop_state != "OPEN":
            return "HARD_STOP_ACTIVE", None
        moment = _parsed(plan.started_at)
        if not (_parsed(policy.starts_at) <= moment < _parsed(policy.ends_at)):
            return "BUDGET_DENIED", None
        ledger_reservations = {item.identity: item for item in ledger.reservations}
        for call_plan in plan.call_plans:
            key = (call_plan.provider, call_plan.model)
            adapter = self.adapters.get(key)
            if adapter is None:
                return "MISSING_ADAPTER", call_plan.identity
            if (
                type(adapter) is not _ADAPTER_TYPES[key]
                or adapter.identity != call_plan.adapter_identity
                or adapter.review_request.payload_sha256
                != call_plan.request_hash
                or adapter.endpoint_binding.provider != call_plan.provider
                or adapter.endpoint_binding.contract_model != call_plan.model
            ):
                return "ADAPTER_MISMATCH", call_plan.identity
            for reservation in call_plan.attempt_reservations:
                known = ledger_reservations.get(reservation.identity)
                authorization = ledger.evaluate_call_authorization(
                    provider=call_plan.provider,
                    model=call_plan.model,
                    run_id=plan.run_id,
                    call_id=reservation.call_id,
                )
                if (
                    known is None
                    or known.identity != reservation.identity
                    or reservation.policy_id != policy.policy_id
                    or reservation.run_id != plan.run_id
                    or reservation.provider != call_plan.provider
                    or reservation.model != call_plan.model
                    or reservation.status != "RESERVED"
                    or reservation.reservation_id
                    in ledger.released_reservations
                    or not (
                        _parsed(reservation.reserved_at)
                        <= moment
                        < _parsed(reservation.expires_at)
                    )
                    or not authorization.allowed
                    or authorization.reservation_id
                    != reservation.reservation_id
                ):
                    return "RESERVATION_MISSING", call_plan.identity
        return None, None

    def execute(
        self, plan: ShadowProviderRunPlanV1
    ) -> ShadowProviderRunResultV1:
        if type(plan) is not ShadowProviderRunPlanV1:
            raise ShadowProviderRunOrchestratorValidationError(
                "invalid run plan"
            )
        failure, failed_call = self._preflight(plan)
        if failure is not None:
            return _make_run_result(
                plan,
                ledger_after=plan.budget_ledger_before,
                invocation_results=(),
                completed_call_plan_ids=(),
                status="DENIED",
                failure=failure,
                reconciliation="NOT_REQUIRED",
                first_failed_call_plan_id=failed_call,
                reasons=(failure,),
            )
        ledger_after = plan.budget_ledger_before
        results: list[ShadowProviderInvocationResultV1] = []
        completed: list[str] = []
        for call_plan in plan.call_plans:
            adapter = self.adapters[(call_plan.provider, call_plan.model)]
            invocation = ShadowProviderInvocationV1(
                schema_version="phase11-shadow-provider-invocation-v1",
                invocation_id=None,
                execution_id=plan.execution_id,
                run_id=plan.run_id,
                call_id=call_plan.call_id,
                route=call_plan.route,
                provider=call_plan.provider,
                model=call_plan.model,
                prompt_version="phase11-prompt-v1",
                provider_review_schema_version="phase10-review-schema-v1",
                shadow_input=plan.shadow_input,
                shadow_input_identity=plan.shadow_input_identity,
                event_id=plan.shadow_input.approved_news_capture.event_id,
                event_version=(
                    plan.shadow_input.approved_news_capture.event_version
                ),
                budget_ledger=ledger_after,
                budget_policy_id=ledger_after.policy.policy_id,
                reservation=call_plan.attempt_reservations[0],
                reservation_id=call_plan.attempt_reservations[0].identity,
                attempt_reservations=call_plan.attempt_reservations,
                review_request=call_plan.review_request,
                request_hash=call_plan.request_hash,
                timeout_ms=call_plan.timeout_ms,
                maximum_attempts=call_plan.maximum_attempts,
                circuit_state=call_plan.circuit_state,
                requested_at=plan.started_at,
                reason_codes=call_plan.reason_codes,
                production_effect="NONE",
                zero_production_effect_proof="PROVEN_NONE",
            )
            runtime = ShadowProviderRuntimeV1(transport=adapter)
            runtime_result = runtime.invoke(invocation)
            results.append(runtime_result)
            usage = runtime_result.usage_record
            if runtime_result.status == "SUCCEEDED" and usage is not None:
                try:
                    ledger_after = ledger_after.commit_usage(usage)
                except BudgetControlValidationError:
                    return _make_run_result(
                        plan,
                        ledger_after=ledger_after,
                        invocation_results=tuple(results),
                        completed_call_plan_ids=tuple(completed),
                        status="PARTIAL_EVIDENCE",
                        failure="USAGE_EXCEEDS_RESERVATION",
                        reconciliation="NOT_REQUIRED",
                        first_failed_call_plan_id=call_plan.identity,
                        reasons=("USAGE_EXCEEDS_RESERVATION",),
                    )
                completed.append(call_plan.identity)
                continue
            if (
                runtime_result.transport_outcome
                == "UNCERTAIN_TRANSPORT_OUTCOME"
                and usage is not None
            ):
                try:
                    ledger_after = ledger_after.reconcile_uncertain_usage(usage)
                except BudgetControlValidationError:
                    return _make_run_result(
                        plan,
                        ledger_after=ledger_after,
                        invocation_results=tuple(results),
                        completed_call_plan_ids=tuple(completed),
                        status="PARTIAL_EVIDENCE",
                        failure="USAGE_EXCEEDS_RESERVATION",
                        reconciliation="RECONCILIATION_REQUIRED",
                        first_failed_call_plan_id=call_plan.identity,
                        reasons=("USAGE_EXCEEDS_RESERVATION",),
                    )
                return _make_run_result(
                    plan,
                    ledger_after=ledger_after,
                    invocation_results=tuple(results),
                    completed_call_plan_ids=tuple(completed),
                    status="RECONCILIATION_REQUIRED",
                    failure="UNCERTAIN_TRANSPORT_OUTCOME",
                    reconciliation="RECONCILIATION_REQUIRED",
                    first_failed_call_plan_id=call_plan.identity,
                    reasons=("RECONCILIATION_REQUIRED",),
                )
            mapped_failure = _runtime_failure(runtime_result.failure_class)
            return _make_run_result(
                plan,
                ledger_after=ledger_after,
                invocation_results=tuple(results),
                completed_call_plan_ids=tuple(completed),
                status="PARTIAL_EVIDENCE",
                failure=mapped_failure,
                reconciliation="NOT_REQUIRED",
                first_failed_call_plan_id=call_plan.identity,
                reasons=(mapped_failure,),
            )
        return _make_run_result(
            plan,
            ledger_after=ledger_after,
            invocation_results=tuple(results),
            completed_call_plan_ids=tuple(completed),
            status="COMPLETED",
            failure="NONE",
            reconciliation="RESOLVED",
            first_failed_call_plan_id=None,
            reasons=("RUN_COMPLETED",),
        )


def _runtime_failure(value: str) -> str:
    if value == "TIMEOUT":
        return "TIMEOUT"
    if value == "MALFORMED_RESPONSE":
        return "MALFORMED_RESPONSE"
    if value == "SCHEMA_MISMATCH":
        return "SCHEMA_MISMATCH"
    if value in {"BUDGET_DENIED", "CIRCUIT_OPEN"}:
        return "BUDGET_DENIED"
    return "PROVIDER_RUNTIME_FAILURE"


def _make_run_result(
    plan: ShadowProviderRunPlanV1,
    *,
    ledger_after: BudgetLedgerV1,
    invocation_results: tuple[ShadowProviderInvocationResultV1, ...],
    completed_call_plan_ids: tuple[str, ...],
    status: str,
    failure: str,
    reconciliation: str,
    first_failed_call_plan_id: str | None,
    reasons: tuple[str, ...],
) -> ShadowProviderRunResultV1:
    completed_at = (
        invocation_results[-1].completed_at
        if invocation_results
        else plan.started_at
    )
    return ShadowProviderRunResultV1(
        schema_version="phase11-shadow-provider-run-result-v1",
        run_result_id=None,
        run_plan_id=plan.identity,
        execution_id=plan.execution_id,
        run_id=plan.run_id,
        route=plan.route,
        completed_call_plan_ids=completed_call_plan_ids,
        invocation_results=invocation_results,
        ledger_before_id=plan.budget_ledger_before.identity,
        ledger_after=ledger_after,
        ledger_after_id=ledger_after.identity,
        status=status,
        failure_class=failure,
        reconciliation_state=reconciliation,
        first_failed_call_plan_id=first_failed_call_plan_id,
        started_at=plan.started_at,
        completed_at=completed_at,
        reason_codes=reasons,
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


__all__ = (
    "ShadowProviderRunOrchestratorV1",
    "ShadowProviderRunOrchestratorValidationError",
    "ShadowProviderRunPlanV1",
    "ShadowProviderRunResultV1",
    "ShadowRunCallPlanV1",
    "ShadowRunFailureV1",
    "ShadowRunReconciliationV1",
    "ShadowRunStatusV1",
    "canonical_json_bytes",
    "lowercase_sha256",
)
