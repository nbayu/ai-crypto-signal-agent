"""Deterministic injected-transport boundary for escalated review contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from engine.ai_review_payload_projector_v1 import ClaudeReviewPayloadV1
from engine.deterministic_escalation_router_v1 import DeterministicEscalationDecisionV1
from engine.news_event_contract_v1 import canonical_json_bytes, sha256_hex


CLAUDE_ESCALATED_REVIEW_POLICY_VERSION = "claude-escalated-review-policy-v1"

__all__ = (
    "ClaudeEscalatedReviewProviderError",
    "CLAUDE_ESCALATED_REVIEW_POLICY_VERSION",
    "ClaudeBudgetAuthorizationV1",
    "ClaudeExecutionPolicyV1",
    "ClaudeEscalatedReviewResultV1",
    "ClaudeProviderExecutionRecordV1",
    "ClaudeEscalatedReviewRunV1",
    "execute_claude_escalated_review",
)


_PROVIDER_NAME = "ANTHROPIC"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_ROUTE_NAMES = {"L0": "CLEAN_OR_ROUTINE", "L1": "MODERATE_AMBIGUITY", "L2": "CRITICAL_AMBIGUITY"}
_ESCALATED_ROUTES = frozenset(("L1", "L2"))
_CACHE_CONTROL = {"mode": "EPHEMERAL", "ttl_seconds": 300, "breakpoint_count": 1, "breakpoint_after": "stable_prefix"}
_UNSET = object()

_BUDGET_FIELDS = frozenset(
    (
        "authorization_id",
        "policy_version",
        "event_snapshot_id",
        "router_decision_id",
        "route",
        "model_policy_id",
        "authorized",
        "maximum_authorized_cost_micro_usd",
        "authorization_reason_code",
    )
)
_POLICY_FIELDS = frozenset(
    (
        "policy_version",
        "provider_name",
        "route",
        "model_policy_id",
        "model_id",
        "maximum_logical_reviews_per_event",
        "maximum_provider_attempts",
        "maximum_retry_count",
        "timeout_seconds",
        "input_token_hard_limit",
        "target_input_token_minimum",
        "target_input_token_maximum",
        "output_token_hard_limit",
        "prompt_cache_mode",
        "prompt_cache_ttl_seconds",
        "prompt_cache_breakpoint_count",
        "budget_authorized",
        "maximum_authorized_cost_micro_usd",
    )
)
_RESULT_FIELDS = frozenset(
    (
        "policy_version",
        "event_snapshot_id",
        "request_payload_sha256",
        "router_decision_id",
        "logical_review_id",
        "route",
        "model_policy_id",
        "review_status",
        "review_conclusion",
        "ambiguity_resolution",
        "contradiction_resolution",
        "evidence_assessment",
        "entity_assessment",
        "source_assessment",
        "material_risk_assessment",
        "agreement_state_with_deepseek",
        "reason_codes",
        "structured_explanation",
        "adjudication_evidence_refs",
        "semantic_result_id",
    )
)
_RECORD_FIELDS = frozenset(
    (
        "request_id",
        "event_snapshot_id",
        "provider",
        "route",
        "model_id",
        "model_policy_id",
        "payload_version",
        "payload_sha256",
        "router_decision_id",
        "logical_review_id",
        "attempt_number",
        "retry_count",
        "execution_status",
        "failure_class",
        "failure_code",
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "usage_status",
        "cost_micro_usd",
        "duration_ms",
    )
)
_RUN_FIELDS = frozenset(
    (
        "logical_review_id",
        "event_snapshot_id",
        "payload_sha256",
        "router_decision_id",
        "route",
        "semantic_result",
        "execution_records",
        "final_run_status",
        "total_attempts",
        "total_retries",
    )
)
_FINAL_STATUSES = frozenset(
    (
        "COMPLETED",
        "PROVIDER_REJECTED",
        "INVALID_RESPONSE",
        "TRANSIENT_FAILURE",
        "PERMANENT_FAILURE",
        "BUDGET_BLOCKED",
        "ROUTE_BLOCKED",
        "TOKEN_LIMIT_BLOCKED",
    )
)
_FAILURE_CLASSES = frozenset(
    (
        "PRE_CALL_VALIDATION",
        "ROUTE_AUTHORIZATION",
        "TOKEN_LIMIT_VALIDATION",
        "BUDGET_AUTHORIZATION",
        "TRANSIENT_TRANSPORT",
        "PERMANENT_PROVIDER",
        "RESPONSE_VALIDATION",
        "INTERNAL_ADAPTER_ERROR",
    )
)
_FAILURE_CODES = frozenset(
    (
        "TIMEOUT",
        "TEMPORARY_UNAVAILABLE",
        "TEMPORARY_CONNECTION_FAILURE",
        "AUTHENTICATION_FAILURE",
        "PERMISSION_DENIED",
        "UNSUPPORTED_MODEL",
        "PROVIDER_REJECTED",
        "CANCELLED",
        "INVALID_RESPONSE",
        "INTERNAL_ADAPTER_ERROR",
    )
)
_TRANSIENT_CODES = frozenset(("TIMEOUT", "TEMPORARY_UNAVAILABLE", "TEMPORARY_CONNECTION_FAILURE"))
_PERMANENT_CODES = frozenset(("AUTHENTICATION_FAILURE", "PERMISSION_DENIED", "UNSUPPORTED_MODEL", "PROVIDER_REJECTED", "CANCELLED"))
_OPTIONAL_RESPONSE_FIELDS = frozenset(
    (
        "model_id",
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "cost_micro_usd",
        "duration_ms",
    )
)
_RESULT_REASON_CODES = frozenset(("CLAUDE_REVIEW_COMPLETED",))
_APPROVED_AUTHORIZATION_CODES = frozenset(("OWNER_APPROVED_TEST_BUDGET",))


class ClaudeEscalatedReviewProviderError(ValueError):
    """Raised when an escalated-review contract is invalid."""


def _require_exact_fields(values: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(values) != expected:
        raise ClaudeEscalatedReviewProviderError(f"invalid {label} fields")


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ClaudeEscalatedReviewProviderError(f"invalid {label}")
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ClaudeEscalatedReviewProviderError(f"invalid {label}")
    return value


def _require_nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ClaudeEscalatedReviewProviderError(f"invalid {label}")
    return value


def _require_positive_integer(value: Any, label: str) -> int:
    value = _require_nonnegative_integer(value, label)
    if value == 0:
        raise ClaudeEscalatedReviewProviderError(f"invalid {label}")
    return value


def _require_bounded_text(value: Any, label: str) -> str:
    if type(value) is not str or not value or len(value) > 1000:
        raise ClaudeEscalatedReviewProviderError(f"invalid {label}")
    return value


def _require_identifiers(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ClaudeEscalatedReviewProviderError(f"invalid {label}")
    return tuple(sorted({_require_identifier(item, label) for item in value}))


def _require_closed_texts(value: Any, label: str, allowed: frozenset[str]) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ClaudeEscalatedReviewProviderError(f"invalid {label}")
    result: list[str] = []
    for item in value:
        if type(item) is not str or item not in allowed:
            raise ClaudeEscalatedReviewProviderError(f"invalid {label}")
        result.append(item)
    return tuple(sorted(set(result)))


def _optional_count(value: Any, label: str) -> int | None:
    if value is None:
        return None
    return _require_nonnegative_integer(value, label)


def _hash_mapping(value: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(value))


@dataclass(frozen=True, init=False)
class ClaudeBudgetAuthorizationV1:
    authorization_id: str
    policy_version: str
    event_snapshot_id: str
    router_decision_id: str
    route: str
    model_policy_id: str
    authorized: bool
    maximum_authorized_cost_micro_usd: int
    authorization_reason_code: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _BUDGET_FIELDS, "budget authorization")
        if values["policy_version"] != CLAUDE_ESCALATED_REVIEW_POLICY_VERSION:
            raise ClaudeEscalatedReviewProviderError("invalid policy_version")
        route = values["route"]
        if route not in _ESCALATED_ROUTES:
            raise ClaudeEscalatedReviewProviderError("invalid route")
        if type(values["authorized"]) is not bool:
            raise ClaudeEscalatedReviewProviderError("authorized must be bool")
        reason = values["authorization_reason_code"]
        if reason not in _APPROVED_AUTHORIZATION_CODES:
            raise ClaudeEscalatedReviewProviderError("invalid authorization_reason_code")
        object.__setattr__(self, "authorization_id", _require_hash(values["authorization_id"], "authorization_id"))
        object.__setattr__(self, "policy_version", CLAUDE_ESCALATED_REVIEW_POLICY_VERSION)
        object.__setattr__(self, "event_snapshot_id", _require_hash(values["event_snapshot_id"], "event_snapshot_id"))
        object.__setattr__(self, "router_decision_id", _require_hash(values["router_decision_id"], "router_decision_id"))
        object.__setattr__(self, "route", route)
        object.__setattr__(self, "model_policy_id", _require_identifier(values["model_policy_id"], "model_policy_id"))
        object.__setattr__(self, "authorized", values["authorized"])
        object.__setattr__(self, "maximum_authorized_cost_micro_usd", _require_nonnegative_integer(values["maximum_authorized_cost_micro_usd"], "maximum_authorized_cost_micro_usd"))
        object.__setattr__(self, "authorization_reason_code", reason)


@dataclass(frozen=True, init=False)
class ClaudeExecutionPolicyV1:
    policy_version: str
    provider_name: str
    route: str
    model_policy_id: str
    model_id: str
    maximum_logical_reviews_per_event: int
    maximum_provider_attempts: int
    maximum_retry_count: int
    timeout_seconds: int
    input_token_hard_limit: int
    target_input_token_minimum: int
    target_input_token_maximum: int
    output_token_hard_limit: int
    prompt_cache_mode: str
    prompt_cache_ttl_seconds: int
    prompt_cache_breakpoint_count: int
    budget_authorized: bool
    maximum_authorized_cost_micro_usd: int

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _POLICY_FIELDS, "execution policy")
        if values["policy_version"] != CLAUDE_ESCALATED_REVIEW_POLICY_VERSION:
            raise ClaudeEscalatedReviewProviderError("invalid policy_version")
        if values["provider_name"] != _PROVIDER_NAME:
            raise ClaudeEscalatedReviewProviderError("invalid provider_name")
        if values["route"] not in _ESCALATED_ROUTES:
            raise ClaudeEscalatedReviewProviderError("invalid route")
        for name in (
            "maximum_logical_reviews_per_event",
            "maximum_provider_attempts",
            "maximum_retry_count",
            "timeout_seconds",
            "input_token_hard_limit",
            "target_input_token_minimum",
            "target_input_token_maximum",
            "output_token_hard_limit",
            "prompt_cache_ttl_seconds",
            "prompt_cache_breakpoint_count",
            "maximum_authorized_cost_micro_usd",
        ):
            _require_nonnegative_integer(values[name], name)
        if (
            values["maximum_logical_reviews_per_event"] != 1
            or values["maximum_provider_attempts"] != 2
            or values["maximum_retry_count"] != 1
            or values["input_token_hard_limit"] != 8000
            or values["target_input_token_minimum"] != 2000
            or values["target_input_token_maximum"] != 5000
            or values["output_token_hard_limit"] != 1000
            or values["prompt_cache_ttl_seconds"] != 300
            or values["prompt_cache_breakpoint_count"] != 1
        ):
            raise ClaudeEscalatedReviewProviderError("invalid frozen execution policy")
        if values["timeout_seconds"] <= 0:
            raise ClaudeEscalatedReviewProviderError("invalid timeout_seconds")
        if values["prompt_cache_mode"] != "EPHEMERAL":
            raise ClaudeEscalatedReviewProviderError("invalid prompt_cache_mode")
        if type(values["budget_authorized"]) is not bool:
            raise ClaudeEscalatedReviewProviderError("budget_authorized must be bool")
        object.__setattr__(self, "policy_version", CLAUDE_ESCALATED_REVIEW_POLICY_VERSION)
        object.__setattr__(self, "provider_name", _PROVIDER_NAME)
        object.__setattr__(self, "route", values["route"])
        object.__setattr__(self, "model_policy_id", _require_identifier(values["model_policy_id"], "model_policy_id"))
        object.__setattr__(self, "model_id", _require_identifier(values["model_id"], "model_id"))
        for name in (
            "maximum_logical_reviews_per_event",
            "maximum_provider_attempts",
            "maximum_retry_count",
            "timeout_seconds",
            "input_token_hard_limit",
            "target_input_token_minimum",
            "target_input_token_maximum",
            "output_token_hard_limit",
            "prompt_cache_ttl_seconds",
            "prompt_cache_breakpoint_count",
            "maximum_authorized_cost_micro_usd",
        ):
            object.__setattr__(self, name, values[name])
        object.__setattr__(self, "prompt_cache_mode", "EPHEMERAL")
        object.__setattr__(self, "budget_authorized", values["budget_authorized"])


def _semantic_result_id(values: Mapping[str, Any]) -> str:
    return _hash_mapping(
        {
            "policy_version": values["policy_version"],
            "event_snapshot_id": values["event_snapshot_id"],
            "request_payload_sha256": values["request_payload_sha256"],
            "router_decision_id": values["router_decision_id"],
            "logical_review_id": values["logical_review_id"],
            "route": values["route"],
            "model_policy_id": values["model_policy_id"],
            "review_status": values["review_status"],
            "review_conclusion": values["review_conclusion"],
            "ambiguity_resolution": values["ambiguity_resolution"],
            "contradiction_resolution": values["contradiction_resolution"],
            "evidence_assessment": values["evidence_assessment"],
            "entity_assessment": values["entity_assessment"],
            "source_assessment": values["source_assessment"],
            "material_risk_assessment": values["material_risk_assessment"],
            "agreement_state_with_deepseek": values["agreement_state_with_deepseek"],
            "reason_codes": list(values["reason_codes"]),
            "structured_explanation": values["structured_explanation"],
            "adjudication_evidence_refs": list(values["adjudication_evidence_refs"]),
        }
    )


@dataclass(frozen=True, init=False)
class ClaudeEscalatedReviewResultV1:
    policy_version: str
    event_snapshot_id: str
    request_payload_sha256: str
    router_decision_id: str
    logical_review_id: str
    route: str
    model_policy_id: str
    review_status: str
    review_conclusion: str
    ambiguity_resolution: str
    contradiction_resolution: str
    evidence_assessment: str
    entity_assessment: str
    source_assessment: str
    material_risk_assessment: str
    agreement_state_with_deepseek: str
    reason_codes: tuple[str, ...]
    structured_explanation: str
    adjudication_evidence_refs: tuple[str, ...]
    semantic_result_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RESULT_FIELDS, "semantic result")
        if values["policy_version"] != CLAUDE_ESCALATED_REVIEW_POLICY_VERSION:
            raise ClaudeEscalatedReviewProviderError("invalid result policy_version")
        route = values["route"]
        if route not in _ESCALATED_ROUTES:
            raise ClaudeEscalatedReviewProviderError("invalid result route")
        fixed = {
            "review_status": "COMPLETED",
            "review_conclusion": "ESCALATED_REVIEW_COMPLETE",
            "ambiguity_resolution": "RESOLVED",
            "contradiction_resolution": "NONE",
            "evidence_assessment": "SUFFICIENT",
            "entity_assessment": "CONFIRMED",
            "source_assessment": "ACCEPTABLE",
            "material_risk_assessment": "NONE",
            "agreement_state_with_deepseek": "AGREES",
        }
        if any(values[name] != expected for name, expected in fixed.items()):
            raise ClaudeEscalatedReviewProviderError("invalid semantic result value")
        canonical = {
            "policy_version": CLAUDE_ESCALATED_REVIEW_POLICY_VERSION,
            "event_snapshot_id": _require_hash(values["event_snapshot_id"], "event_snapshot_id"),
            "request_payload_sha256": _require_hash(values["request_payload_sha256"], "request_payload_sha256"),
            "router_decision_id": _require_hash(values["router_decision_id"], "router_decision_id"),
            "logical_review_id": _require_hash(values["logical_review_id"], "logical_review_id"),
            "route": route,
            "model_policy_id": _require_identifier(values["model_policy_id"], "model_policy_id"),
            **fixed,
            "reason_codes": _require_closed_texts(values["reason_codes"], "reason_codes", _RESULT_REASON_CODES),
            "structured_explanation": _require_bounded_text(values["structured_explanation"], "structured_explanation"),
            "adjudication_evidence_refs": _require_identifiers(values["adjudication_evidence_refs"], "adjudication_evidence_refs"),
        }
        semantic_result_id = _semantic_result_id(canonical)
        supplied = values["semantic_result_id"]
        if supplied is not None and supplied != semantic_result_id:
            raise ClaudeEscalatedReviewProviderError("invalid semantic_result_id")
        for name, value in canonical.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "semantic_result_id", semantic_result_id)


@dataclass(frozen=True, init=False)
class ClaudeProviderExecutionRecordV1:
    request_id: str = field(compare=False)
    event_snapshot_id: str
    provider: str
    route: str
    model_id: str
    model_policy_id: str
    payload_version: str
    payload_sha256: str
    router_decision_id: str
    logical_review_id: str
    attempt_number: int
    retry_count: int
    execution_status: str
    failure_class: str | None
    failure_code: str | None
    input_tokens: int | None
    output_tokens: int | None
    cache_creation_input_tokens: int | None
    cache_read_input_tokens: int | None
    usage_status: str
    cost_micro_usd: int | None
    duration_ms: int | None

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RECORD_FIELDS, "execution record")
        if values["provider"] != _PROVIDER_NAME:
            raise ClaudeEscalatedReviewProviderError("invalid record provider")
        if values["route"] not in _ESCALATED_ROUTES:
            raise ClaudeEscalatedReviewProviderError("invalid record route")
        if values["payload_version"] != "claude-review-v1":
            raise ClaudeEscalatedReviewProviderError("invalid record payload_version")
        attempt = _require_positive_integer(values["attempt_number"], "attempt_number")
        retry = _require_nonnegative_integer(values["retry_count"], "retry_count")
        if retry != attempt - 1:
            raise ClaudeEscalatedReviewProviderError("inconsistent retry_count")
        status = values["execution_status"]
        if status not in _FINAL_STATUSES:
            raise ClaudeEscalatedReviewProviderError("invalid execution_status")
        failure_class = values["failure_class"]
        failure_code = values["failure_code"]
        if failure_class is not None and failure_class not in _FAILURE_CLASSES:
            raise ClaudeEscalatedReviewProviderError("invalid failure_class")
        if failure_code is not None and failure_code not in _FAILURE_CODES:
            raise ClaudeEscalatedReviewProviderError("invalid failure_code")
        counts = {
            "input_tokens": _optional_count(values["input_tokens"], "input_tokens"),
            "output_tokens": _optional_count(values["output_tokens"], "output_tokens"),
            "cache_creation_input_tokens": _optional_count(values["cache_creation_input_tokens"], "cache_creation_input_tokens"),
            "cache_read_input_tokens": _optional_count(values["cache_read_input_tokens"], "cache_read_input_tokens"),
            "cost_micro_usd": _optional_count(values["cost_micro_usd"], "cost_micro_usd"),
            "duration_ms": _optional_count(values["duration_ms"], "duration_ms"),
        }
        usage_status = values["usage_status"]
        if usage_status not in {"UNAVAILABLE", "REPORTED"}:
            raise ClaudeEscalatedReviewProviderError("invalid usage_status")
        if usage_status == "UNAVAILABLE" and any(value is not None for value in counts.values()):
            raise ClaudeEscalatedReviewProviderError("inconsistent usage_status")
        object.__setattr__(self, "request_id", _require_identifier(values["request_id"], "request_id"))
        object.__setattr__(self, "event_snapshot_id", _require_hash(values["event_snapshot_id"], "event_snapshot_id"))
        object.__setattr__(self, "provider", _PROVIDER_NAME)
        object.__setattr__(self, "route", values["route"])
        object.__setattr__(self, "model_id", _require_identifier(values["model_id"], "model_id"))
        object.__setattr__(self, "model_policy_id", _require_identifier(values["model_policy_id"], "model_policy_id"))
        object.__setattr__(self, "payload_version", "claude-review-v1")
        object.__setattr__(self, "payload_sha256", _require_hash(values["payload_sha256"], "payload_sha256"))
        object.__setattr__(self, "router_decision_id", _require_hash(values["router_decision_id"], "router_decision_id"))
        object.__setattr__(self, "logical_review_id", _require_hash(values["logical_review_id"], "logical_review_id"))
        object.__setattr__(self, "attempt_number", attempt)
        object.__setattr__(self, "retry_count", retry)
        object.__setattr__(self, "execution_status", status)
        object.__setattr__(self, "failure_class", failure_class)
        object.__setattr__(self, "failure_code", failure_code)
        for name, value in counts.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "usage_status", usage_status)


@dataclass(frozen=True, init=False)
class ClaudeEscalatedReviewRunV1:
    logical_review_id: str
    event_snapshot_id: str
    payload_sha256: str
    router_decision_id: str
    route: str
    semantic_result: ClaudeEscalatedReviewResultV1 | None
    execution_records: tuple[ClaudeProviderExecutionRecordV1, ...]
    final_run_status: str
    total_attempts: int
    total_retries: int

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RUN_FIELDS, "review run")
        route = values["route"]
        if route not in _ROUTE_NAMES:
            raise ClaudeEscalatedReviewProviderError("invalid run route")
        logical_review_id = _require_hash(values["logical_review_id"], "logical_review_id")
        event_snapshot_id = _require_hash(values["event_snapshot_id"], "event_snapshot_id")
        payload_sha256 = _require_hash(values["payload_sha256"], "payload_sha256")
        router_decision_id = _require_hash(values["router_decision_id"], "router_decision_id")
        semantic = values["semantic_result"]
        if semantic is not None and type(semantic) is not ClaudeEscalatedReviewResultV1:
            raise ClaudeEscalatedReviewProviderError("invalid semantic_result")
        supplied_records = values["execution_records"]
        if isinstance(supplied_records, (str, bytes)):
            raise ClaudeEscalatedReviewProviderError("invalid execution_records")
        try:
            records = tuple(supplied_records)
        except TypeError as exc:
            raise ClaudeEscalatedReviewProviderError("invalid execution_records") from exc
        if len(records) > 2 or any(type(record) is not ClaudeProviderExecutionRecordV1 for record in records):
            raise ClaudeEscalatedReviewProviderError("invalid execution_records")
        if [record.attempt_number for record in records] != list(range(1, len(records) + 1)):
            raise ClaudeEscalatedReviewProviderError("invalid attempt sequence")
        if any(
            record.event_snapshot_id != event_snapshot_id
            or record.payload_sha256 != payload_sha256
            or record.router_decision_id != router_decision_id
            or record.logical_review_id != logical_review_id
            or record.route != route
            for record in records
        ):
            raise ClaudeEscalatedReviewProviderError("execution record binding mismatch")
        if semantic is not None and (
            semantic.event_snapshot_id != event_snapshot_id
            or semantic.request_payload_sha256 != payload_sha256
            or semantic.router_decision_id != router_decision_id
            or semantic.logical_review_id != logical_review_id
            or semantic.route != route
        ):
            raise ClaudeEscalatedReviewProviderError("semantic result binding mismatch")
        final_status = values["final_run_status"]
        if final_status not in _FINAL_STATUSES:
            raise ClaudeEscalatedReviewProviderError("invalid final_run_status")
        attempts = _require_nonnegative_integer(values["total_attempts"], "total_attempts")
        retries = _require_nonnegative_integer(values["total_retries"], "total_retries")
        if attempts != len(records) or retries != max(0, len(records) - 1):
            raise ClaudeEscalatedReviewProviderError("inconsistent run totals")
        if final_status == "COMPLETED" and semantic is None:
            raise ClaudeEscalatedReviewProviderError("completed run requires semantic_result")
        if final_status != "COMPLETED" and semantic is not None:
            raise ClaudeEscalatedReviewProviderError("non-completed run cannot have semantic_result")
        if final_status in {"ROUTE_BLOCKED", "TOKEN_LIMIT_BLOCKED", "BUDGET_BLOCKED"} and records:
            raise ClaudeEscalatedReviewProviderError("blocked run cannot have records")
        object.__setattr__(self, "logical_review_id", logical_review_id)
        object.__setattr__(self, "event_snapshot_id", event_snapshot_id)
        object.__setattr__(self, "payload_sha256", payload_sha256)
        object.__setattr__(self, "router_decision_id", router_decision_id)
        object.__setattr__(self, "route", route)
        object.__setattr__(self, "semantic_result", semantic)
        object.__setattr__(self, "execution_records", records)
        object.__setattr__(self, "final_run_status", final_status)
        object.__setattr__(self, "total_attempts", attempts)
        object.__setattr__(self, "total_retries", retries)


def _logical_review_id(payload: ClaudeReviewPayloadV1, decision: DeterministicEscalationDecisionV1, policy: ClaudeExecutionPolicyV1) -> str:
    return _hash_mapping(
        {
            "policy_version": CLAUDE_ESCALATED_REVIEW_POLICY_VERSION,
            "event_snapshot_id": payload.event_snapshot_id,
            "payload_version": payload.payload_version,
            "payload_sha256": payload.payload_sha256,
            "router_decision_id": decision.decision_id,
            "route": decision.route,
            "model_policy_id": policy.model_policy_id,
            "model_id": policy.model_id,
            "review_task": payload.review_task,
        }
    )


def _validate_decision(decision: DeterministicEscalationDecisionV1) -> None:
    _require_hash(decision.event_snapshot_id, "decision event_snapshot_id")
    _require_hash(decision.decision_id, "decision_id")
    if decision.route not in _ROUTE_NAMES or decision.route_name != _ROUTE_NAMES[decision.route]:
        raise ClaudeEscalatedReviewProviderError("invalid router decision")
    if type(decision.claude_review_required) is not bool:
        raise ClaudeEscalatedReviewProviderError("invalid router decision")
    if decision.route == "L0":
        if decision.claude_review_required or decision.claude_model_policy_id is not None:
            raise ClaudeEscalatedReviewProviderError("invalid L0 decision")
        return
    if not decision.claude_review_required:
        raise ClaudeEscalatedReviewProviderError("invalid escalated decision")
    _require_identifier(decision.claude_model_policy_id, "decision model_policy_id")


def _validate_bindings(payload: ClaudeReviewPayloadV1, decision: DeterministicEscalationDecisionV1, policy: ClaudeExecutionPolicyV1, budget: ClaudeBudgetAuthorizationV1) -> None:
    if payload.event_snapshot_id != decision.event_snapshot_id or payload.event_snapshot_id != budget.event_snapshot_id:
        raise ClaudeEscalatedReviewProviderError("event snapshot binding mismatch")
    if decision.decision_id != budget.router_decision_id:
        raise ClaudeEscalatedReviewProviderError("router decision binding mismatch")
    if decision.route != policy.route or decision.route != budget.route:
        raise ClaudeEscalatedReviewProviderError("route binding mismatch")
    if decision.claude_model_policy_id != policy.model_policy_id or decision.claude_model_policy_id != budget.model_policy_id:
        raise ClaudeEscalatedReviewProviderError("model policy binding mismatch")


def _new_run(payload: ClaudeReviewPayloadV1, decision: DeterministicEscalationDecisionV1, logical_review_id: str, semantic: ClaudeEscalatedReviewResultV1 | None, records: tuple[ClaudeProviderExecutionRecordV1, ...] | list[ClaudeProviderExecutionRecordV1], status: str) -> ClaudeEscalatedReviewRunV1:
    records = tuple(records)
    return ClaudeEscalatedReviewRunV1(
        logical_review_id=logical_review_id,
        event_snapshot_id=payload.event_snapshot_id,
        payload_sha256=payload.payload_sha256,
        router_decision_id=decision.decision_id,
        route=decision.route,
        semantic_result=semantic,
        execution_records=records,
        final_run_status=status,
        total_attempts=len(records),
        total_retries=max(0, len(records) - 1),
    )


def _request(payload: ClaudeReviewPayloadV1, decision: DeterministicEscalationDecisionV1, policy: ClaudeExecutionPolicyV1, logical_review_id: str, attempt: int) -> dict[str, Any]:
    return {
        "provider": _PROVIDER_NAME,
        "route": decision.route,
        "model_id": policy.model_id,
        "model_policy_id": policy.model_policy_id,
        "event_snapshot_id": payload.event_snapshot_id,
        "payload_version": payload.payload_version,
        "payload_sha256": payload.payload_sha256,
        "router_decision_id": decision.decision_id,
        "logical_review_id": logical_review_id,
        "semantic_payload": payload.to_mapping(),
        "attempt_number": attempt,
        "timeout_seconds": policy.timeout_seconds,
        "output_token_limit": policy.output_token_hard_limit,
        "cache_control": dict(_CACHE_CONTROL),
        "request_id": logical_review_id[:16] + "-attempt-" + str(attempt),
    }


def _failure_outcome(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    if "failure_code" not in value and "failure_class" not in value:
        return None
    if set(value) == {"failure_code"}:
        code = value["failure_code"]
        if code not in _PERMANENT_CODES:
            raise ClaudeEscalatedReviewProviderError("invalid failure_code")
        return "PERMANENT_PROVIDER", code
    if set(value) != {"failure_class", "failure_code"}:
        raise ClaudeEscalatedReviewProviderError("invalid failure response")
    failure_class = value["failure_class"]
    failure_code = value["failure_code"]
    if failure_class not in _FAILURE_CLASSES or failure_code not in _FAILURE_CODES:
        raise ClaudeEscalatedReviewProviderError("invalid failure response")
    if failure_class == "TRANSIENT_TRANSPORT" and failure_code not in _TRANSIENT_CODES:
        raise ClaudeEscalatedReviewProviderError("invalid transient failure")
    return failure_class, failure_code


def _status_for_failure(failure_class: str, failure_code: str) -> str:
    if failure_class == "TRANSIENT_TRANSPORT":
        return "TRANSIENT_FAILURE"
    if failure_code == "PROVIDER_REJECTED":
        return "PROVIDER_REJECTED"
    return "PERMANENT_FAILURE"


def _response_result(response: Any, payload: ClaudeReviewPayloadV1, decision: DeterministicEscalationDecisionV1, policy: ClaudeExecutionPolicyV1, logical_review_id: str) -> ClaudeEscalatedReviewResultV1:
    if not isinstance(response, Mapping):
        raise ClaudeEscalatedReviewProviderError("invalid response")
    response_values = dict(response)
    allowed = _RESULT_FIELDS | _OPTIONAL_RESPONSE_FIELDS
    if not _RESULT_FIELDS.issubset(response_values) or not set(response_values).issubset(allowed):
        raise ClaudeEscalatedReviewProviderError("invalid response fields")
    if response_values["event_snapshot_id"] != payload.event_snapshot_id:
        raise ClaudeEscalatedReviewProviderError("response snapshot mismatch")
    if response_values["request_payload_sha256"] != payload.payload_sha256:
        raise ClaudeEscalatedReviewProviderError("response payload binding mismatch")
    if response_values["router_decision_id"] != decision.decision_id:
        raise ClaudeEscalatedReviewProviderError("response decision binding mismatch")
    if response_values["logical_review_id"] != logical_review_id:
        raise ClaudeEscalatedReviewProviderError("response logical review binding mismatch")
    if response_values["route"] != decision.route or response_values["model_policy_id"] != policy.model_policy_id:
        raise ClaudeEscalatedReviewProviderError("response route binding mismatch")
    if "model_id" in response_values and response_values["model_id"] != policy.model_id:
        raise ClaudeEscalatedReviewProviderError("response model binding mismatch")
    return ClaudeEscalatedReviewResultV1(**{name: response_values[name] for name in _RESULT_FIELDS})


def _record(payload: ClaudeReviewPayloadV1, decision: DeterministicEscalationDecisionV1, policy: ClaudeExecutionPolicyV1, request: Mapping[str, Any], attempt: int, status: str, failure_class: str | None, failure_code: str | None, response: Any) -> ClaudeProviderExecutionRecordV1:
    telemetry = {name: None for name in _OPTIONAL_RESPONSE_FIELDS - {"model_id"}}
    if isinstance(response, Mapping):
        for name in telemetry:
            if name in response:
                telemetry[name] = response[name]
    counts = {
        "input_tokens": _optional_count(telemetry["input_tokens"], "input_tokens"),
        "output_tokens": _optional_count(telemetry["output_tokens"], "output_tokens"),
        "cache_creation_input_tokens": _optional_count(telemetry["cache_creation_input_tokens"], "cache_creation_input_tokens"),
        "cache_read_input_tokens": _optional_count(telemetry["cache_read_input_tokens"], "cache_read_input_tokens"),
        "cost_micro_usd": _optional_count(telemetry["cost_micro_usd"], "cost_micro_usd"),
        "duration_ms": _optional_count(telemetry["duration_ms"], "duration_ms"),
    }
    return ClaudeProviderExecutionRecordV1(
        request_id=request["request_id"],
        event_snapshot_id=payload.event_snapshot_id,
        provider=_PROVIDER_NAME,
        route=decision.route,
        model_id=policy.model_id,
        model_policy_id=policy.model_policy_id,
        payload_version=payload.payload_version,
        payload_sha256=payload.payload_sha256,
        router_decision_id=decision.decision_id,
        logical_review_id=request["logical_review_id"],
        attempt_number=attempt,
        retry_count=attempt - 1,
        execution_status=status,
        failure_class=failure_class,
        failure_code=failure_code,
        usage_status="REPORTED" if any(value is not None for value in counts.values()) else "UNAVAILABLE",
        **counts,
    )


def execute_claude_escalated_review(payload: Any, router_decision: Any, execution_policy: Any, budget_authorization: Any, transport: Any, *, claude_input_estimate: Any = _UNSET) -> ClaudeEscalatedReviewRunV1:
    """Run a deterministic escalated review through the supplied callable."""

    if type(payload) is not ClaudeReviewPayloadV1:
        raise ClaudeEscalatedReviewProviderError("payload must be ClaudeReviewPayloadV1")
    if type(router_decision) is not DeterministicEscalationDecisionV1:
        raise ClaudeEscalatedReviewProviderError("router_decision must be DeterministicEscalationDecisionV1")
    if type(execution_policy) is not ClaudeExecutionPolicyV1:
        raise ClaudeEscalatedReviewProviderError("execution_policy must be ClaudeExecutionPolicyV1")
    if type(budget_authorization) is not ClaudeBudgetAuthorizationV1:
        raise ClaudeEscalatedReviewProviderError("budget_authorization must be ClaudeBudgetAuthorizationV1")
    if not callable(transport):
        raise ClaudeEscalatedReviewProviderError("transport must be callable")
    _validate_decision(router_decision)
    logical_review_id = _logical_review_id(payload, router_decision, execution_policy)
    if router_decision.route == "L0":
        return _new_run(payload, router_decision, logical_review_id, None, (), "ROUTE_BLOCKED")
    _validate_bindings(payload, router_decision, execution_policy, budget_authorization)
    if claude_input_estimate is not _UNSET:
        estimate = _require_nonnegative_integer(claude_input_estimate, "claude_input_estimate")
        if estimate > execution_policy.input_token_hard_limit:
            return _new_run(payload, router_decision, logical_review_id, None, (), "TOKEN_LIMIT_BLOCKED")
    if not execution_policy.budget_authorized or not budget_authorization.authorized:
        return _new_run(payload, router_decision, logical_review_id, None, (), "BUDGET_BLOCKED")
    records: list[ClaudeProviderExecutionRecordV1] = []
    for attempt in (1, 2):
        request = _request(payload, router_decision, execution_policy, logical_review_id, attempt)
        try:
            response = transport(request)
        except TimeoutError:
            response = {"failure_class": "TRANSIENT_TRANSPORT", "failure_code": "TIMEOUT"}
        except ConnectionError:
            response = {"failure_class": "TRANSIENT_TRANSPORT", "failure_code": "TEMPORARY_CONNECTION_FAILURE"}
        except PermissionError:
            response = {"failure_class": "PERMANENT_PROVIDER", "failure_code": "PERMISSION_DENIED"}
        except ClaudeEscalatedReviewProviderError:
            response = {"failure_class": "TRANSIENT_TRANSPORT", "failure_code": "TEMPORARY_UNAVAILABLE"}
        try:
            outcome = _failure_outcome(response)
        except ClaudeEscalatedReviewProviderError:
            records.append(_record(payload, router_decision, execution_policy, request, attempt, "PERMANENT_FAILURE", "INTERNAL_ADAPTER_ERROR", "INTERNAL_ADAPTER_ERROR", None))
            return _new_run(payload, router_decision, logical_review_id, None, records, "PERMANENT_FAILURE")
        if outcome is not None:
            failure_class, failure_code = outcome
            status = _status_for_failure(failure_class, failure_code)
            records.append(_record(payload, router_decision, execution_policy, request, attempt, status, failure_class, failure_code, None))
            if failure_class == "TRANSIENT_TRANSPORT" and attempt == 1:
                continue
            return _new_run(payload, router_decision, logical_review_id, None, records, status)
        try:
            semantic = _response_result(response, payload, router_decision, execution_policy, logical_review_id)
            record = _record(payload, router_decision, execution_policy, request, attempt, "COMPLETED", None, None, response)
        except ClaudeEscalatedReviewProviderError:
            records.append(_record(payload, router_decision, execution_policy, request, attempt, "INVALID_RESPONSE", "RESPONSE_VALIDATION", "INVALID_RESPONSE", None))
            return _new_run(payload, router_decision, logical_review_id, None, records, "INVALID_RESPONSE")
        records.append(record)
        return _new_run(payload, router_decision, logical_review_id, semantic, records, "COMPLETED")
    raise ClaudeEscalatedReviewProviderError("invalid attempt state")
