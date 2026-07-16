"""Deterministic injected-transport boundary for primary review contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from engine.ai_review_payload_projector_v1 import DeepSeekReviewPayloadV1
from engine.news_event_contract_v1 import canonical_json_bytes, sha256_hex


DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION = "deepseek-primary-review-policy-v1"

__all__ = (
    "DeepSeekPrimaryReviewProviderError",
    "DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION",
    "DeepSeekExecutionPolicyV1",
    "DeepSeekPrimaryReviewResultV1",
    "DeepSeekProviderExecutionRecordV1",
    "DeepSeekPrimaryReviewRunV1",
    "execute_deepseek_primary_review",
)


_HASH_LENGTH = 64
_PROVIDER_NAME = "DEEPSEEK"
_MODEL_POLICY_ID = "fictional-deepseek-policy-v1"
_REQUIRED_MODEL_ID = "fictional-deepseek-model-v1"
_RESULT_FIELDS = frozenset(
    (
        "policy_version",
        "event_snapshot_id",
        "request_payload_sha256",
        "logical_review_id",
        "review_status",
        "review_conclusion",
        "ambiguity_level",
        "contradiction_present",
        "evidence_sufficiency",
        "entity_confidence_state",
        "source_policy_concern_state",
        "material_risk_flags",
        "reason_codes",
        "structured_explanation",
        "escalation_evidence_refs",
        "semantic_result_id",
    )
)
_POLICY_FIELDS = frozenset(
    (
        "policy_version",
        "provider_name",
        "model_policy_id",
        "model_id",
        "maximum_logical_reviews_per_event",
        "maximum_provider_attempts",
        "maximum_retry_count",
        "timeout_seconds",
        "budget_authorized",
        "maximum_authorized_cost_micro_usd",
    )
)
_RECORD_FIELDS = frozenset(
    (
        "request_id",
        "event_snapshot_id",
        "provider",
        "model_id",
        "payload_version",
        "payload_sha256",
        "logical_review_id",
        "attempt_number",
        "retry_count",
        "execution_status",
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
        "PAYLOAD_REJECTED",
        "CANCELLED",
        "INVALID_SCHEMA",
        "INVALID_RESPONSE",
        "INTERNAL_ADAPTER_ERROR",
    )
)
_TRANSIENT_CODES = frozenset(
    (
        "TIMEOUT",
        "TEMPORARY_UNAVAILABLE",
        "TEMPORARY_CONNECTION_FAILURE",
    )
)
_OPTIONAL_RESPONSE_FIELDS = frozenset(
    (
        "model_id",
        "request_id",
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "usage_status",
        "cost_micro_usd",
        "duration_ms",
    )
)


class DeepSeekPrimaryReviewProviderError(ValueError):
    """Raised when the deterministic primary-review contract is invalid."""


@dataclass(frozen=True, init=False)
class DeepSeekExecutionPolicyV1:
    policy_version: str
    provider_name: str
    model_policy_id: str
    model_id: str
    maximum_logical_reviews_per_event: int
    maximum_provider_attempts: int
    maximum_retry_count: int
    timeout_seconds: int
    budget_authorized: bool
    maximum_authorized_cost_micro_usd: int

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _POLICY_FIELDS, "execution policy")
        if values["policy_version"] != DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION:
            raise DeepSeekPrimaryReviewProviderError("invalid policy_version")
        if values["provider_name"] != _PROVIDER_NAME:
            raise DeepSeekPrimaryReviewProviderError("invalid provider_name")
        model_policy_id = _require_identifier(values["model_policy_id"], "model_policy_id")
        model_id = _require_identifier(values["model_id"], "model_id")
        _require_exact_integer(
            values["maximum_logical_reviews_per_event"],
            "maximum_logical_reviews_per_event",
        )
        _require_exact_integer(values["maximum_provider_attempts"], "maximum_provider_attempts")
        _require_exact_integer(values["maximum_retry_count"], "maximum_retry_count")
        timeout = _require_exact_integer(values["timeout_seconds"], "timeout_seconds")
        maximum_cost = _require_nonnegative_integer(
            values["maximum_authorized_cost_micro_usd"],
            "maximum_authorized_cost_micro_usd",
        )
        if values["maximum_logical_reviews_per_event"] != 1:
            raise DeepSeekPrimaryReviewProviderError("invalid maximum_logical_reviews_per_event")
        if values["maximum_provider_attempts"] != 2:
            raise DeepSeekPrimaryReviewProviderError("invalid maximum_provider_attempts")
        if values["maximum_retry_count"] != 1:
            raise DeepSeekPrimaryReviewProviderError("invalid maximum_retry_count")
        if timeout <= 0:
            raise DeepSeekPrimaryReviewProviderError("timeout_seconds must be positive")
        if type(values["budget_authorized"]) is not bool:
            raise DeepSeekPrimaryReviewProviderError("budget_authorized must be bool")
        object.__setattr__(self, "policy_version", DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION)
        object.__setattr__(self, "provider_name", _PROVIDER_NAME)
        object.__setattr__(self, "model_policy_id", model_policy_id)
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "maximum_logical_reviews_per_event", 1)
        object.__setattr__(self, "maximum_provider_attempts", 2)
        object.__setattr__(self, "maximum_retry_count", 1)
        object.__setattr__(self, "timeout_seconds", timeout)
        object.__setattr__(self, "budget_authorized", values["budget_authorized"])
        object.__setattr__(self, "maximum_authorized_cost_micro_usd", maximum_cost)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "provider_name": self.provider_name,
            "model_policy_id": self.model_policy_id,
            "model_id": self.model_id,
            "maximum_logical_reviews_per_event": self.maximum_logical_reviews_per_event,
            "maximum_provider_attempts": self.maximum_provider_attempts,
            "maximum_retry_count": self.maximum_retry_count,
            "timeout_seconds": self.timeout_seconds,
            "budget_authorized": self.budget_authorized,
            "maximum_authorized_cost_micro_usd": self.maximum_authorized_cost_micro_usd,
        }


@dataclass(frozen=True, init=False)
class DeepSeekPrimaryReviewResultV1:
    policy_version: str
    event_snapshot_id: str
    request_payload_sha256: str
    logical_review_id: str
    review_status: str
    review_conclusion: str
    ambiguity_level: str
    contradiction_present: bool
    evidence_sufficiency: str
    entity_confidence_state: str
    source_policy_concern_state: str
    material_risk_flags: tuple[str, ...]
    reason_codes: tuple[str, ...]
    structured_explanation: str
    escalation_evidence_refs: tuple[str, ...]
    semantic_result_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RESULT_FIELDS, "semantic result")
        if values["policy_version"] != DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION:
            raise DeepSeekPrimaryReviewProviderError("invalid result policy_version")
        event_snapshot_id = _require_hash(values["event_snapshot_id"], "event_snapshot_id")
        payload_sha256 = _require_hash(
            values["request_payload_sha256"], "request_payload_sha256"
        )
        logical_review_id = _require_hash(values["logical_review_id"], "logical_review_id")
        if values["review_status"] != "COMPLETED":
            raise DeepSeekPrimaryReviewProviderError("invalid review_status")
        if values["review_conclusion"] != "FACTUAL_REVIEW_COMPLETE":
            raise DeepSeekPrimaryReviewProviderError("invalid review_conclusion")
        if values["ambiguity_level"] != "NONE":
            raise DeepSeekPrimaryReviewProviderError("invalid ambiguity_level")
        if values["contradiction_present"] is not False:
            raise DeepSeekPrimaryReviewProviderError("invalid contradiction_present")
        if values["evidence_sufficiency"] != "SUFFICIENT":
            raise DeepSeekPrimaryReviewProviderError("invalid evidence_sufficiency")
        if values["entity_confidence_state"] != "EXPLICIT":
            raise DeepSeekPrimaryReviewProviderError("invalid entity_confidence_state")
        if values["source_policy_concern_state"] != "NONE":
            raise DeepSeekPrimaryReviewProviderError("invalid source_policy_concern_state")
        flags = _require_closed_texts(values["material_risk_flags"], "material_risk_flags", {"NONE"})
        reasons = _require_closed_texts(values["reason_codes"], "reason_codes", {"REVIEW_COMPLETED"})
        evidence = _require_identifiers(values["escalation_evidence_refs"], "escalation_evidence_refs")
        explanation = _require_bounded_text(values["structured_explanation"], "structured_explanation")
        semantic = {
            "policy_version": DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION,
            "event_snapshot_id": event_snapshot_id,
            "request_payload_sha256": payload_sha256,
            "logical_review_id": logical_review_id,
            "review_status": "COMPLETED",
            "review_conclusion": "FACTUAL_REVIEW_COMPLETE",
            "ambiguity_level": "NONE",
            "contradiction_present": False,
            "evidence_sufficiency": "SUFFICIENT",
            "entity_confidence_state": "EXPLICIT",
            "source_policy_concern_state": "NONE",
            "material_risk_flags": list(flags),
            "reason_codes": list(reasons),
            "structured_explanation": explanation,
            "escalation_evidence_refs": list(evidence),
        }
        result_id = _hash_mapping(semantic)
        _validate_hash(values["semantic_result_id"], result_id, "semantic_result_id")
        object.__setattr__(self, "policy_version", DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION)
        object.__setattr__(self, "event_snapshot_id", event_snapshot_id)
        object.__setattr__(self, "request_payload_sha256", payload_sha256)
        object.__setattr__(self, "logical_review_id", logical_review_id)
        object.__setattr__(self, "review_status", "COMPLETED")
        object.__setattr__(self, "review_conclusion", "FACTUAL_REVIEW_COMPLETE")
        object.__setattr__(self, "ambiguity_level", "NONE")
        object.__setattr__(self, "contradiction_present", False)
        object.__setattr__(self, "evidence_sufficiency", "SUFFICIENT")
        object.__setattr__(self, "entity_confidence_state", "EXPLICIT")
        object.__setattr__(self, "source_policy_concern_state", "NONE")
        object.__setattr__(self, "material_risk_flags", flags)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "structured_explanation", explanation)
        object.__setattr__(self, "escalation_evidence_refs", evidence)
        object.__setattr__(self, "semantic_result_id", result_id)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "event_snapshot_id": self.event_snapshot_id,
            "request_payload_sha256": self.request_payload_sha256,
            "logical_review_id": self.logical_review_id,
            "review_status": self.review_status,
            "review_conclusion": self.review_conclusion,
            "ambiguity_level": self.ambiguity_level,
            "contradiction_present": self.contradiction_present,
            "evidence_sufficiency": self.evidence_sufficiency,
            "entity_confidence_state": self.entity_confidence_state,
            "source_policy_concern_state": self.source_policy_concern_state,
            "material_risk_flags": list(self.material_risk_flags),
            "reason_codes": list(self.reason_codes),
            "structured_explanation": self.structured_explanation,
            "escalation_evidence_refs": list(self.escalation_evidence_refs),
            "semantic_result_id": self.semantic_result_id,
        }


@dataclass(frozen=True, init=False)
class DeepSeekProviderExecutionRecordV1:
    request_id: str = field(compare=False)
    event_snapshot_id: str
    provider: str
    model_id: str
    payload_version: str
    payload_sha256: str
    logical_review_id: str
    attempt_number: int
    retry_count: int
    execution_status: str
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
        request_id = _require_identifier(values["request_id"], "request_id")
        event_snapshot_id = _require_hash(values["event_snapshot_id"], "event_snapshot_id")
        payload_sha256 = _require_hash(values["payload_sha256"], "payload_sha256")
        logical_review_id = _require_hash(values["logical_review_id"], "logical_review_id")
        if values["provider"] != _PROVIDER_NAME:
            raise DeepSeekPrimaryReviewProviderError("invalid record provider")
        if values["model_id"] != _REQUIRED_MODEL_ID:
            raise DeepSeekPrimaryReviewProviderError("invalid record model_id")
        if values["payload_version"] != "deepseek-review-v1":
            raise DeepSeekPrimaryReviewProviderError("invalid record payload_version")
        attempt = _require_positive_integer(values["attempt_number"], "attempt_number")
        retry = _require_nonnegative_integer(values["retry_count"], "retry_count")
        if retry != attempt - 1:
            raise DeepSeekPrimaryReviewProviderError("inconsistent retry_count")
        status = values["execution_status"]
        if status not in _FINAL_STATUSES:
            raise DeepSeekPrimaryReviewProviderError("invalid execution_status")
        failure_code = values["failure_code"]
        if failure_code is not None and failure_code not in _FAILURE_CODES:
            raise DeepSeekPrimaryReviewProviderError("invalid failure_code")
        input_tokens = _optional_count(values["input_tokens"], "input_tokens")
        output_tokens = _optional_count(values["output_tokens"], "output_tokens")
        cache_created = _optional_count(
            values["cache_creation_input_tokens"], "cache_creation_input_tokens"
        )
        cache_read = _optional_count(values["cache_read_input_tokens"], "cache_read_input_tokens")
        cost = _optional_count(values["cost_micro_usd"], "cost_micro_usd")
        duration = _optional_count(values["duration_ms"], "duration_ms")
        usage_status = values["usage_status"]
        if usage_status not in {"UNAVAILABLE", "REPORTED"}:
            raise DeepSeekPrimaryReviewProviderError("invalid usage_status")
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "event_snapshot_id", event_snapshot_id)
        object.__setattr__(self, "provider", _PROVIDER_NAME)
        object.__setattr__(self, "model_id", _REQUIRED_MODEL_ID)
        object.__setattr__(self, "payload_version", "deepseek-review-v1")
        object.__setattr__(self, "payload_sha256", payload_sha256)
        object.__setattr__(self, "logical_review_id", logical_review_id)
        object.__setattr__(self, "attempt_number", attempt)
        object.__setattr__(self, "retry_count", retry)
        object.__setattr__(self, "execution_status", status)
        object.__setattr__(self, "failure_code", failure_code)
        object.__setattr__(self, "input_tokens", input_tokens)
        object.__setattr__(self, "output_tokens", output_tokens)
        object.__setattr__(self, "cache_creation_input_tokens", cache_created)
        object.__setattr__(self, "cache_read_input_tokens", cache_read)
        object.__setattr__(self, "usage_status", usage_status)
        object.__setattr__(self, "cost_micro_usd", cost)
        object.__setattr__(self, "duration_ms", duration)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "event_snapshot_id": self.event_snapshot_id,
            "provider": self.provider,
            "model_id": self.model_id,
            "payload_version": self.payload_version,
            "payload_sha256": self.payload_sha256,
            "logical_review_id": self.logical_review_id,
            "attempt_number": self.attempt_number,
            "retry_count": self.retry_count,
            "execution_status": self.execution_status,
            "failure_code": self.failure_code,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "usage_status": self.usage_status,
            "cost_micro_usd": self.cost_micro_usd,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True, init=False)
class DeepSeekPrimaryReviewRunV1:
    logical_review_id: str
    event_snapshot_id: str
    payload_sha256: str
    semantic_result: DeepSeekPrimaryReviewResultV1 | None
    execution_records: tuple[DeepSeekProviderExecutionRecordV1, ...]
    final_run_status: str
    total_attempts: int
    total_retries: int

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RUN_FIELDS, "review run")
        logical_review_id = _require_hash(values["logical_review_id"], "logical_review_id")
        event_snapshot_id = _require_hash(values["event_snapshot_id"], "event_snapshot_id")
        payload_sha256 = _require_hash(values["payload_sha256"], "payload_sha256")
        semantic = values["semantic_result"]
        if semantic is not None and type(semantic) is not DeepSeekPrimaryReviewResultV1:
            raise DeepSeekPrimaryReviewProviderError("invalid semantic_result")
        supplied_records = values["execution_records"]
        if isinstance(supplied_records, (str, bytes)):
            raise DeepSeekPrimaryReviewProviderError("invalid execution_records")
        try:
            records = tuple(supplied_records)
        except TypeError as exc:
            raise DeepSeekPrimaryReviewProviderError("invalid execution_records") from exc
        if len(records) > 2 or any(type(record) is not DeepSeekProviderExecutionRecordV1 for record in records):
            raise DeepSeekPrimaryReviewProviderError("invalid execution_records")
        if [record.attempt_number for record in records] != list(range(1, len(records) + 1)):
            raise DeepSeekPrimaryReviewProviderError("invalid attempt sequence")
        if any(
            record.event_snapshot_id != event_snapshot_id
            or record.payload_sha256 != payload_sha256
            or record.logical_review_id != logical_review_id
            for record in records
        ):
            raise DeepSeekPrimaryReviewProviderError("execution record binding mismatch")
        if semantic is not None and (
            semantic.event_snapshot_id != event_snapshot_id
            or semantic.request_payload_sha256 != payload_sha256
            or semantic.logical_review_id != logical_review_id
        ):
            raise DeepSeekPrimaryReviewProviderError("semantic result binding mismatch")
        final_status = values["final_run_status"]
        if final_status not in _FINAL_STATUSES:
            raise DeepSeekPrimaryReviewProviderError("invalid final_run_status")
        attempts = _require_nonnegative_integer(values["total_attempts"], "total_attempts")
        retries = _require_nonnegative_integer(values["total_retries"], "total_retries")
        if attempts != len(records) or retries != max(0, len(records) - 1):
            raise DeepSeekPrimaryReviewProviderError("inconsistent run totals")
        if final_status == "COMPLETED" and semantic is None:
            raise DeepSeekPrimaryReviewProviderError("completed run requires semantic_result")
        if final_status != "COMPLETED" and semantic is not None:
            raise DeepSeekPrimaryReviewProviderError("non-completed run cannot have semantic_result")
        object.__setattr__(self, "logical_review_id", logical_review_id)
        object.__setattr__(self, "event_snapshot_id", event_snapshot_id)
        object.__setattr__(self, "payload_sha256", payload_sha256)
        object.__setattr__(self, "semantic_result", semantic)
        object.__setattr__(self, "execution_records", records)
        object.__setattr__(self, "final_run_status", final_status)
        object.__setattr__(self, "total_attempts", attempts)
        object.__setattr__(self, "total_retries", retries)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "logical_review_id": self.logical_review_id,
            "event_snapshot_id": self.event_snapshot_id,
            "payload_sha256": self.payload_sha256,
            "semantic_result": None if self.semantic_result is None else self.semantic_result.to_mapping(),
            "execution_records": [record.to_mapping() for record in self.execution_records],
            "final_run_status": self.final_run_status,
            "total_attempts": self.total_attempts,
            "total_retries": self.total_retries,
        }


def execute_deepseek_primary_review(
    *,
    payload: Any,
    execution_policy: Any,
    transport: Any,
) -> DeepSeekPrimaryReviewRunV1:
    """Run one semantic review through the supplied local transport callable."""

    if type(payload) is not DeepSeekReviewPayloadV1:
        raise DeepSeekPrimaryReviewProviderError("payload must be DeepSeekReviewPayloadV1")
    if type(execution_policy) is not DeepSeekExecutionPolicyV1:
        raise DeepSeekPrimaryReviewProviderError("execution_policy must be DeepSeekExecutionPolicyV1")
    if not callable(transport):
        raise DeepSeekPrimaryReviewProviderError("transport must be callable")
    if (
        execution_policy.model_policy_id != _MODEL_POLICY_ID
        or execution_policy.model_id != _REQUIRED_MODEL_ID
    ):
        raise DeepSeekPrimaryReviewProviderError("unsupported model policy")
    logical_review_id = _logical_review_id(payload, execution_policy)
    if not execution_policy.budget_authorized:
        return _new_run(payload, logical_review_id, None, (), "BUDGET_BLOCKED")
    records: list[DeepSeekProviderExecutionRecordV1] = []
    for attempt in (1, 2):
        request = _request(payload, execution_policy, logical_review_id, attempt, transport)
        try:
            response = transport(request)
        except TimeoutError:
            response = {"failure_class": "TRANSIENT_TRANSPORT", "failure_code": "TIMEOUT"}
        except ConnectionError:
            response = {
                "failure_class": "TRANSIENT_TRANSPORT",
                "failure_code": "TEMPORARY_CONNECTION_FAILURE",
            }
        except PermissionError:
            response = {"failure_class": "PERMANENT_PROVIDER", "failure_code": "PERMISSION_DENIED"}
        outcome = _failure_outcome(response)
        if outcome is not None:
            failure_class, failure_code = outcome
            status = _status_for_failure(failure_class, failure_code)
            records.append(_record(payload, request, attempt, status, failure_code, None))
            if failure_class == "TRANSIENT_TRANSPORT" and attempt == 1:
                continue
            return _new_run(payload, logical_review_id, None, records, status)
        try:
            semantic = _semantic_result(response, payload, logical_review_id)
            record = _record(payload, request, attempt, "COMPLETED", None, response)
        except DeepSeekPrimaryReviewProviderError:
            records.append(_record(payload, request, attempt, "INVALID_RESPONSE", "INVALID_RESPONSE", None))
            return _new_run(payload, logical_review_id, None, records, "INVALID_RESPONSE")
        records.append(record)
        return _new_run(payload, logical_review_id, semantic, records, "COMPLETED")
    raise DeepSeekPrimaryReviewProviderError("invalid attempt state")


def _new_run(
    payload: DeepSeekReviewPayloadV1,
    logical_review_id: str,
    semantic: DeepSeekPrimaryReviewResultV1 | None,
    records: tuple[DeepSeekProviderExecutionRecordV1, ...] | list[DeepSeekProviderExecutionRecordV1],
    status: str,
) -> DeepSeekPrimaryReviewRunV1:
    records = tuple(records)
    return DeepSeekPrimaryReviewRunV1(
        logical_review_id=logical_review_id,
        event_snapshot_id=payload.event_snapshot_id,
        payload_sha256=payload.payload_sha256,
        semantic_result=semantic,
        execution_records=records,
        final_run_status=status,
        total_attempts=len(records),
        total_retries=max(0, len(records) - 1),
    )


def _logical_review_id(payload: DeepSeekReviewPayloadV1, policy: DeepSeekExecutionPolicyV1) -> str:
    return _hash_mapping(
        {
            "event_snapshot_id": payload.event_snapshot_id,
            "payload_version": payload.payload_version,
            "payload_sha256": payload.payload_sha256,
            "model_policy_id": policy.model_policy_id,
            "model_id": policy.model_id,
            "review_task": payload.review_task,
        }
    )


def _request(
    payload: DeepSeekReviewPayloadV1,
    policy: DeepSeekExecutionPolicyV1,
    logical_review_id: str,
    attempt: int,
    transport: Any,
) -> dict[str, Any]:
    request_id = logical_review_id[:16] + "-" + str(id(transport)) + "-" + str(attempt)
    return {
        "provider": _PROVIDER_NAME,
        "model_id": policy.model_id,
        "payload": payload.to_mapping(),
        "payload_sha256": payload.payload_sha256,
        "event_snapshot_id": payload.event_snapshot_id,
        "logical_review_id": logical_review_id,
        "attempt_number": attempt,
        "timeout_seconds": policy.timeout_seconds,
        "request_id": request_id,
    }


def _failure_outcome(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    if "failure_class" not in value and "failure_code" not in value:
        return None
    if frozenset(value) != {"failure_class", "failure_code"}:
        raise DeepSeekPrimaryReviewProviderError("invalid failure response")
    failure_class = value["failure_class"]
    failure_code = value["failure_code"]
    if failure_class not in {
        "PRE_CALL_VALIDATION",
        "TRANSIENT_TRANSPORT",
        "PERMANENT_PROVIDER",
        "RESPONSE_VALIDATION",
        "INTERNAL_ADAPTER_ERROR",
    }:
        raise DeepSeekPrimaryReviewProviderError("invalid failure_class")
    if failure_code not in _FAILURE_CODES:
        raise DeepSeekPrimaryReviewProviderError("invalid failure_code")
    if failure_class == "TRANSIENT_TRANSPORT" and failure_code not in _TRANSIENT_CODES:
        raise DeepSeekPrimaryReviewProviderError("invalid transient failure_code")
    return failure_class, failure_code


def _status_for_failure(failure_class: str, failure_code: str) -> str:
    if failure_class == "TRANSIENT_TRANSPORT":
        return "TRANSIENT_FAILURE"
    if failure_class == "RESPONSE_VALIDATION":
        return "INVALID_RESPONSE"
    if failure_code == "PROVIDER_REJECTED":
        return "PROVIDER_REJECTED"
    return "PERMANENT_FAILURE"


def _semantic_result(
    response: Any,
    payload: DeepSeekReviewPayloadV1,
    logical_review_id: str,
) -> DeepSeekPrimaryReviewResultV1:
    if not isinstance(response, Mapping):
        raise DeepSeekPrimaryReviewProviderError("invalid response")
    allowed = _RESULT_FIELDS | _OPTIONAL_RESPONSE_FIELDS
    if not frozenset(response) <= allowed or not _RESULT_FIELDS <= frozenset(response):
        raise DeepSeekPrimaryReviewProviderError("invalid response fields")
    if "model_id" in response and response["model_id"] != _REQUIRED_MODEL_ID:
        raise DeepSeekPrimaryReviewProviderError("invalid response model_id")
    if response["event_snapshot_id"] != payload.event_snapshot_id:
        raise DeepSeekPrimaryReviewProviderError("response event_snapshot_id mismatch")
    if response["request_payload_sha256"] != payload.payload_sha256:
        raise DeepSeekPrimaryReviewProviderError("response payload_sha256 mismatch")
    if response["logical_review_id"] != logical_review_id:
        raise DeepSeekPrimaryReviewProviderError("response logical_review_id mismatch")
    return DeepSeekPrimaryReviewResultV1(
        policy_version=response["policy_version"],
        event_snapshot_id=response["event_snapshot_id"],
        request_payload_sha256=response["request_payload_sha256"],
        logical_review_id=response["logical_review_id"],
        review_status=response["review_status"],
        review_conclusion=response["review_conclusion"],
        ambiguity_level=response["ambiguity_level"],
        contradiction_present=response["contradiction_present"],
        evidence_sufficiency=response["evidence_sufficiency"],
        entity_confidence_state=response["entity_confidence_state"],
        source_policy_concern_state=response["source_policy_concern_state"],
        material_risk_flags=response["material_risk_flags"],
        reason_codes=response["reason_codes"],
        structured_explanation=response["structured_explanation"],
        escalation_evidence_refs=response["escalation_evidence_refs"],
        semantic_result_id=response["semantic_result_id"],
    )


def _record(
    payload: DeepSeekReviewPayloadV1,
    request: Mapping[str, Any],
    attempt: int,
    status: str,
    failure_code: str | None,
    response: Any,
) -> DeepSeekProviderExecutionRecordV1:
    response = response if isinstance(response, Mapping) else {}
    usage_values = {
        "input_tokens": response.get("input_tokens"),
        "output_tokens": response.get("output_tokens"),
        "cache_creation_input_tokens": response.get("cache_creation_input_tokens"),
        "cache_read_input_tokens": response.get("cache_read_input_tokens"),
        "cost_micro_usd": response.get("cost_micro_usd"),
        "duration_ms": response.get("duration_ms"),
    }
    usage_status = response.get("usage_status")
    if usage_status is None:
        usage_status = "REPORTED" if any(value is not None for value in usage_values.values()) else "UNAVAILABLE"
    return DeepSeekProviderExecutionRecordV1(
        request_id=response.get("request_id", request["request_id"]),
        event_snapshot_id=payload.event_snapshot_id,
        provider=_PROVIDER_NAME,
        model_id=_REQUIRED_MODEL_ID,
        payload_version=payload.payload_version,
        payload_sha256=payload.payload_sha256,
        logical_review_id=request["logical_review_id"],
        attempt_number=attempt,
        retry_count=attempt - 1,
        execution_status=status,
        failure_code=failure_code,
        input_tokens=usage_values["input_tokens"],
        output_tokens=usage_values["output_tokens"],
        cache_creation_input_tokens=usage_values["cache_creation_input_tokens"],
        cache_read_input_tokens=usage_values["cache_read_input_tokens"],
        usage_status=usage_status,
        cost_micro_usd=usage_values["cost_micro_usd"],
        duration_ms=usage_values["duration_ms"],
    )


def _require_exact_fields(values: Any, expected: frozenset[str], label: str) -> None:
    if not isinstance(values, Mapping) or frozenset(values) != expected:
        raise DeepSeekPrimaryReviewProviderError("invalid " + label + " fields")


def _require_exact_integer(value: Any, field_name: str) -> int:
    if type(value) is not int:
        raise DeepSeekPrimaryReviewProviderError(field_name + " must be an integer")
    return value


def _require_nonnegative_integer(value: Any, field_name: str) -> int:
    value = _require_exact_integer(value, field_name)
    if value < 0:
        raise DeepSeekPrimaryReviewProviderError(field_name + " must be non-negative")
    return value


def _require_positive_integer(value: Any, field_name: str) -> int:
    value = _require_exact_integer(value, field_name)
    if value <= 0:
        raise DeepSeekPrimaryReviewProviderError(field_name + " must be positive")
    return value


def _optional_count(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _require_nonnegative_integer(value, field_name)


def _require_hash(value: Any, field_name: str) -> str:
    if type(value) is not str or len(value) != _HASH_LENGTH:
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    if any(character not in "0123456789abcdef" for character in value):
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    return value


def _require_identifier(value: Any, field_name: str) -> str:
    if type(value) is not str or not value or value != value.strip() or len(value) > 256:
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    if not all(character.isalnum() or character in "_-:" for character in value):
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    return value


def _require_bounded_text(value: Any, field_name: str) -> str:
    if type(value) is not str or not value or value != value.strip() or len(value) > 100000:
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    return value


def _require_closed_texts(value: Any, field_name: str, allowed: set[str]) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    try:
        items = tuple(value)
    except TypeError as exc:
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name) from exc
    if not items or any(type(item) is not str or item not in allowed for item in items):
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    return tuple(sorted(set(items)))


def _require_identifiers(value: Any, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    try:
        items = tuple(value)
    except TypeError as exc:
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name) from exc
    if not items:
        raise DeepSeekPrimaryReviewProviderError("invalid " + field_name)
    return tuple(sorted({_require_identifier(item, field_name) for item in items}))


def _hash_mapping(value: Mapping[str, Any]) -> str:
    try:
        return sha256_hex(canonical_json_bytes(value))
    except ValueError as exc:
        raise DeepSeekPrimaryReviewProviderError("invalid canonical value") from exc


def _validate_hash(value: Any, expected: str, field_name: str) -> None:
    if value is None:
        return
    if _require_hash(value, field_name) != expected:
        raise DeepSeekPrimaryReviewProviderError(field_name + " does not match semantic result")
