"""Pure deterministic projection of canonical news facts into review payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Callable, Mapping

from engine.news_entity_mapping_v1 import EntityMappingResultV1
from engine.news_event_contract_v1 import (
    NormalizedNewsEventV1,
    canonical_json_bytes,
    sha256_hex,
)
from engine.news_source_policy_v1 import SourcePolicyDecisionV1


AI_REVIEW_PAYLOAD_POLICY_VERSION = "ai-review-payload-policy-v1"
DEEPSEEK_PAYLOAD_VERSION = "deepseek-review-v1"
CLAUDE_PAYLOAD_VERSION = "claude-review-v1"

__all__ = (
    "AIReviewPayloadProjectionError",
    "AI_REVIEW_PAYLOAD_POLICY_VERSION",
    "DEEPSEEK_PAYLOAD_VERSION",
    "CLAUDE_PAYLOAD_VERSION",
    "PayloadTokenPolicyV1",
    "DeepSeekReviewPayloadV1",
    "ClaudeReviewPayloadV1",
    "AIReviewPayloadProjectionV1",
    "project_ai_review_payloads",
)


_HASH_LENGTH = 64
_CACHE_POLICY_VERSION = "news-prompt-cache-v1"
_CACHE_TTL_SECONDS = 300
_TOKEN_DECISIONS = frozenset(
    (
        "BELOW_TARGET_COMPLETE",
        "WITHIN_TARGET",
        "ABOVE_TARGET_WITHIN_HARD_LIMIT",
        "HARD_LIMIT_EXCEEDED",
    )
)
_EVIDENCE_FIELDS = frozenset(
    (
        "evidence_ref_id",
        "event_snapshot_id",
        "source_field",
        "excerpt",
        "excerpt_sha256",
    )
)
_TOKEN_POLICY_FIELDS = frozenset(
    (
        "claude_input_hard_limit_tokens",
        "claude_target_input_min_tokens",
        "claude_target_input_max_tokens",
        "claude_output_hard_limit_tokens",
        "maximum_claude_logical_reviews_per_event",
        "maximum_provider_attempts_per_review",
        "maximum_retry_count",
    )
)
_DEEPSEEK_FIELDS = frozenset(
    (
        "payload_version",
        "event_snapshot_id",
        "normalized_event",
        "source_policy",
        "entity_mapping",
        "bounded_evidence",
        "review_task",
        "payload_sha256",
    )
)
_CLAUDE_FIELDS = _DEEPSEEK_FIELDS | frozenset(
    (
        "stable_prefix_identity",
        "dynamic_payload_identity",
        "cache_policy_version",
        "cache_ttl_seconds",
        "cache_breakpoint_count",
        "stable_prefix",
        "dynamic_suffix",
    )
)
_PROJECTION_FIELDS = frozenset(
    (
        "policy_version",
        "event_snapshot_id",
        "deepseek_payload",
        "claude_payload",
        "token_policy",
        "deepseek_estimated_input_tokens",
        "claude_estimated_input_tokens",
        "claude_token_budget_decision",
        "entity_mapping_result",
        "projection_id",
    )
)


class AIReviewPayloadProjectionError(ValueError):
    """Raised when a deterministic review-payload contract is invalid."""


@dataclass(frozen=True, init=False)
class PayloadTokenPolicyV1:
    claude_input_hard_limit_tokens: int
    claude_target_input_min_tokens: int
    claude_target_input_max_tokens: int
    claude_output_hard_limit_tokens: int
    maximum_claude_logical_reviews_per_event: int
    maximum_provider_attempts_per_review: int
    maximum_retry_count: int

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _TOKEN_POLICY_FIELDS, "token policy")
        for field in _TOKEN_POLICY_FIELDS:
            _require_nonnegative_integer(values[field], field)
        required = {
            "claude_input_hard_limit_tokens": 8000,
            "claude_target_input_min_tokens": 2000,
            "claude_target_input_max_tokens": 5000,
            "claude_output_hard_limit_tokens": 1000,
            "maximum_claude_logical_reviews_per_event": 1,
            "maximum_provider_attempts_per_review": 2,
            "maximum_retry_count": 1,
        }
        if any(values[field] != expected for field, expected in required.items()):
            raise AIReviewPayloadProjectionError("invalid frozen token policy")
        object.__setattr__(self, "claude_input_hard_limit_tokens", 8000)
        object.__setattr__(self, "claude_target_input_min_tokens", 2000)
        object.__setattr__(self, "claude_target_input_max_tokens", 5000)
        object.__setattr__(self, "claude_output_hard_limit_tokens", 1000)
        object.__setattr__(self, "maximum_claude_logical_reviews_per_event", 1)
        object.__setattr__(self, "maximum_provider_attempts_per_review", 2)
        object.__setattr__(self, "maximum_retry_count", 1)

    def to_mapping(self) -> dict[str, int]:
        return {
            "claude_input_hard_limit_tokens": self.claude_input_hard_limit_tokens,
            "claude_target_input_min_tokens": self.claude_target_input_min_tokens,
            "claude_target_input_max_tokens": self.claude_target_input_max_tokens,
            "claude_output_hard_limit_tokens": self.claude_output_hard_limit_tokens,
            "maximum_claude_logical_reviews_per_event": self.maximum_claude_logical_reviews_per_event,
            "maximum_provider_attempts_per_review": self.maximum_provider_attempts_per_review,
            "maximum_retry_count": self.maximum_retry_count,
        }


@dataclass(frozen=True, init=False)
class DeepSeekReviewPayloadV1:
    payload_version: str
    event_snapshot_id: str
    normalized_event: NormalizedNewsEventV1
    source_policy: SourcePolicyDecisionV1
    entity_mapping: EntityMappingResultV1
    bounded_evidence: tuple[Mapping[str, str], ...]
    review_task: str
    payload_sha256: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _DEEPSEEK_FIELDS, "DeepSeek payload")
        if values["payload_version"] != DEEPSEEK_PAYLOAD_VERSION:
            raise AIReviewPayloadProjectionError("invalid DeepSeek payload_version")
        event = _require_event(values["normalized_event"])
        policy = _require_policy(values["source_policy"])
        mapping = _require_mapping(values["entity_mapping"])
        snapshot = _require_hash(values["event_snapshot_id"], "event_snapshot_id")
        _validate_input_binding(event, policy, mapping, snapshot)
        evidence = _freeze_evidence(values["bounded_evidence"], snapshot)
        task = _require_task(values["review_task"])
        payload = _deepseek_semantic_mapping(event, policy, mapping, evidence, task)
        derived = _hash_mapping(payload)
        _validate_supplied_hash(values["payload_sha256"], derived, "payload_sha256")
        object.__setattr__(self, "payload_version", DEEPSEEK_PAYLOAD_VERSION)
        object.__setattr__(self, "event_snapshot_id", snapshot)
        object.__setattr__(self, "normalized_event", event)
        object.__setattr__(self, "source_policy", policy)
        object.__setattr__(self, "entity_mapping", mapping)
        object.__setattr__(self, "bounded_evidence", evidence)
        object.__setattr__(self, "review_task", task)
        object.__setattr__(self, "payload_sha256", derived)

    def to_mapping(self) -> dict[str, Any]:
        payload = _deepseek_semantic_mapping(
            self.normalized_event,
            self.source_policy,
            self.entity_mapping,
            self.bounded_evidence,
            self.review_task,
        )
        payload["payload_sha256"] = self.payload_sha256
        return payload


@dataclass(frozen=True, init=False)
class ClaudeReviewPayloadV1:
    payload_version: str
    event_snapshot_id: str
    normalized_event: NormalizedNewsEventV1
    source_policy: SourcePolicyDecisionV1
    entity_mapping: EntityMappingResultV1
    bounded_evidence: tuple[Mapping[str, str], ...]
    review_task: str
    stable_prefix_identity: str
    dynamic_payload_identity: str
    cache_policy_version: str
    cache_ttl_seconds: int
    cache_breakpoint_count: int
    stable_prefix: tuple[str, ...]
    dynamic_suffix: Mapping[str, Any]
    payload_sha256: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _CLAUDE_FIELDS, "Claude payload")
        if values["payload_version"] != CLAUDE_PAYLOAD_VERSION:
            raise AIReviewPayloadProjectionError("invalid Claude payload_version")
        event = _require_event(values["normalized_event"])
        policy = _require_policy(values["source_policy"])
        mapping = _require_mapping(values["entity_mapping"])
        snapshot = _require_hash(values["event_snapshot_id"], "event_snapshot_id")
        _validate_input_binding(event, policy, mapping, snapshot)
        evidence = _freeze_evidence(values["bounded_evidence"], snapshot)
        task = _require_task(values["review_task"])
        stable_prefix = _freeze_prefix(values["stable_prefix"])
        dynamic_suffix = _freeze_json_mapping(values["dynamic_suffix"], "dynamic_suffix")
        if values["cache_policy_version"] != _CACHE_POLICY_VERSION:
            raise AIReviewPayloadProjectionError("invalid cache_policy_version")
        if values["cache_ttl_seconds"] != _CACHE_TTL_SECONDS:
            raise AIReviewPayloadProjectionError("invalid cache_ttl_seconds")
        if values["cache_breakpoint_count"] != 1:
            raise AIReviewPayloadProjectionError("invalid cache_breakpoint_count")
        expected_dynamic = _dynamic_suffix(event, policy, mapping, evidence, task)
        if _thaw_json(dynamic_suffix) != expected_dynamic:
            raise AIReviewPayloadProjectionError("dynamic_suffix does not match canonical inputs")
        stable_identity = _hash_mapping({"stable_prefix": list(stable_prefix)})
        dynamic_identity = _hash_mapping(expected_dynamic)
        _validate_supplied_hash(
            values["stable_prefix_identity"], stable_identity, "stable_prefix_identity"
        )
        _validate_supplied_hash(
            values["dynamic_payload_identity"], dynamic_identity, "dynamic_payload_identity"
        )
        payload = _claude_semantic_mapping(
            event,
            policy,
            mapping,
            evidence,
            task,
            stable_prefix,
            expected_dynamic,
            stable_identity,
            dynamic_identity,
        )
        derived = _hash_mapping(payload)
        _validate_supplied_hash(values["payload_sha256"], derived, "payload_sha256")
        object.__setattr__(self, "payload_version", CLAUDE_PAYLOAD_VERSION)
        object.__setattr__(self, "event_snapshot_id", snapshot)
        object.__setattr__(self, "normalized_event", event)
        object.__setattr__(self, "source_policy", policy)
        object.__setattr__(self, "entity_mapping", mapping)
        object.__setattr__(self, "bounded_evidence", evidence)
        object.__setattr__(self, "review_task", task)
        object.__setattr__(self, "stable_prefix_identity", stable_identity)
        object.__setattr__(self, "dynamic_payload_identity", dynamic_identity)
        object.__setattr__(self, "cache_policy_version", _CACHE_POLICY_VERSION)
        object.__setattr__(self, "cache_ttl_seconds", _CACHE_TTL_SECONDS)
        object.__setattr__(self, "cache_breakpoint_count", 1)
        object.__setattr__(self, "stable_prefix", stable_prefix)
        object.__setattr__(self, "dynamic_suffix", dynamic_suffix)
        object.__setattr__(self, "payload_sha256", derived)

    def to_mapping(self) -> dict[str, Any]:
        payload = _claude_semantic_mapping(
            self.normalized_event,
            self.source_policy,
            self.entity_mapping,
            self.bounded_evidence,
            self.review_task,
            self.stable_prefix,
            _thaw_json(self.dynamic_suffix),
            self.stable_prefix_identity,
            self.dynamic_payload_identity,
        )
        payload["payload_sha256"] = self.payload_sha256
        return payload


@dataclass(frozen=True, init=False)
class AIReviewPayloadProjectionV1:
    policy_version: str
    event_snapshot_id: str
    deepseek_payload: DeepSeekReviewPayloadV1
    claude_payload: ClaudeReviewPayloadV1
    token_policy: PayloadTokenPolicyV1
    deepseek_estimated_input_tokens: int
    claude_estimated_input_tokens: int
    claude_token_budget_decision: str
    entity_mapping_result: EntityMappingResultV1
    projection_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _PROJECTION_FIELDS, "payload projection")
        if values["policy_version"] != AI_REVIEW_PAYLOAD_POLICY_VERSION:
            raise AIReviewPayloadProjectionError("invalid projection policy_version")
        snapshot = _require_hash(values["event_snapshot_id"], "event_snapshot_id")
        deepseek = values["deepseek_payload"]
        claude = values["claude_payload"]
        token_policy = values["token_policy"]
        mapping = values["entity_mapping_result"]
        if type(deepseek) is not DeepSeekReviewPayloadV1:
            raise AIReviewPayloadProjectionError("deepseek_payload must be DeepSeekReviewPayloadV1")
        if type(claude) is not ClaudeReviewPayloadV1:
            raise AIReviewPayloadProjectionError("claude_payload must be ClaudeReviewPayloadV1")
        if type(token_policy) is not PayloadTokenPolicyV1:
            raise AIReviewPayloadProjectionError("token_policy must be PayloadTokenPolicyV1")
        mapping = _require_mapping(mapping)
        if any(
            identifier != snapshot
            for identifier in (
                deepseek.event_snapshot_id,
                claude.event_snapshot_id,
                mapping.event_snapshot_id,
            )
        ):
            raise AIReviewPayloadProjectionError("projection snapshot mismatch")
        deepseek_tokens = _require_nonnegative_integer(
            values["deepseek_estimated_input_tokens"],
            "deepseek_estimated_input_tokens",
        )
        claude_tokens = _require_nonnegative_integer(
            values["claude_estimated_input_tokens"],
            "claude_estimated_input_tokens",
        )
        decision = values["claude_token_budget_decision"]
        if decision not in _TOKEN_DECISIONS - {"HARD_LIMIT_EXCEEDED"}:
            raise AIReviewPayloadProjectionError("invalid claude_token_budget_decision")
        if _budget_decision(claude_tokens, token_policy) != decision:
            raise AIReviewPayloadProjectionError("claude_token_budget_decision is inconsistent")
        derived = _projection_id(snapshot, deepseek, claude, token_policy, mapping)
        _validate_supplied_hash(values["projection_id"], derived, "projection_id")
        object.__setattr__(self, "policy_version", AI_REVIEW_PAYLOAD_POLICY_VERSION)
        object.__setattr__(self, "event_snapshot_id", snapshot)
        object.__setattr__(self, "deepseek_payload", deepseek)
        object.__setattr__(self, "claude_payload", claude)
        object.__setattr__(self, "token_policy", token_policy)
        object.__setattr__(self, "deepseek_estimated_input_tokens", deepseek_tokens)
        object.__setattr__(self, "claude_estimated_input_tokens", claude_tokens)
        object.__setattr__(self, "claude_token_budget_decision", decision)
        object.__setattr__(self, "entity_mapping_result", mapping)
        object.__setattr__(self, "projection_id", derived)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "event_snapshot_id": self.event_snapshot_id,
            "deepseek_payload": self.deepseek_payload.to_mapping(),
            "claude_payload": self.claude_payload.to_mapping(),
            "token_policy": self.token_policy.to_mapping(),
            "deepseek_estimated_input_tokens": self.deepseek_estimated_input_tokens,
            "claude_estimated_input_tokens": self.claude_estimated_input_tokens,
            "claude_token_budget_decision": self.claude_token_budget_decision,
            "entity_mapping_result": _entity_mapping_mapping(self.entity_mapping_result),
            "projection_id": self.projection_id,
        }


def project_ai_review_payloads(
    *,
    normalized_event: Any,
    source_policy_decision: Any,
    entity_mapping_result: Any,
    bounded_evidence: Any,
    review_task: Any,
    token_policy: Any,
    token_counter: Any,
    cache_ttl_seconds: Any = _CACHE_TTL_SECONDS,
) -> AIReviewPayloadProjectionV1:
    """Project canonical review facts without invoking a reviewer."""

    event = _require_event(normalized_event)
    policy = _require_policy(source_policy_decision)
    mapping = _require_mapping(entity_mapping_result)
    if type(token_policy) is not PayloadTokenPolicyV1:
        raise AIReviewPayloadProjectionError("token_policy must be PayloadTokenPolicyV1")
    if policy.decision != "ELIGIBLE":
        raise AIReviewPayloadProjectionError("source_policy_decision must be ELIGIBLE")
    _validate_input_binding(event, policy, mapping, event.event_snapshot_id)
    if cache_ttl_seconds != _CACHE_TTL_SECONDS:
        raise AIReviewPayloadProjectionError("invalid cache_ttl_seconds")
    evidence = _freeze_evidence(bounded_evidence, event.event_snapshot_id)
    task = _require_task(review_task)
    stable_prefix = _stable_prefix()
    dynamic_suffix = _dynamic_suffix(event, policy, mapping, evidence, task)
    stable_identity = _hash_mapping({"stable_prefix": list(stable_prefix)})
    dynamic_identity = _hash_mapping(dynamic_suffix)
    deepseek = DeepSeekReviewPayloadV1(
        payload_version=DEEPSEEK_PAYLOAD_VERSION,
        event_snapshot_id=event.event_snapshot_id,
        normalized_event=event,
        source_policy=policy,
        entity_mapping=mapping,
        bounded_evidence=evidence,
        review_task=task,
        payload_sha256=None,
    )
    claude = ClaudeReviewPayloadV1(
        payload_version=CLAUDE_PAYLOAD_VERSION,
        event_snapshot_id=event.event_snapshot_id,
        normalized_event=event,
        source_policy=policy,
        entity_mapping=mapping,
        bounded_evidence=evidence,
        review_task=task,
        stable_prefix_identity=stable_identity,
        dynamic_payload_identity=dynamic_identity,
        cache_policy_version=_CACHE_POLICY_VERSION,
        cache_ttl_seconds=_CACHE_TTL_SECONDS,
        cache_breakpoint_count=1,
        stable_prefix=stable_prefix,
        dynamic_suffix=dynamic_suffix,
        payload_sha256=None,
    )
    deepseek_tokens = _estimated_count(token_counter, deepseek.to_mapping())
    claude_tokens = _estimated_count(token_counter, claude.to_mapping())
    decision = _budget_decision(claude_tokens, token_policy)
    if decision == "HARD_LIMIT_EXCEEDED":
        raise AIReviewPayloadProjectionError("claude input hard limit exceeded")
    return _new_projection(
        event,
        deepseek,
        claude,
        token_policy,
        mapping,
        deepseek_tokens,
        claude_tokens,
        decision,
    )


def _new_projection(
    event: NormalizedNewsEventV1,
    deepseek: DeepSeekReviewPayloadV1,
    claude: ClaudeReviewPayloadV1,
    token_policy: PayloadTokenPolicyV1,
    mapping: EntityMappingResultV1,
    deepseek_count: int,
    claude_count: int,
    classification: str,
) -> AIReviewPayloadProjectionV1:
    return AIReviewPayloadProjectionV1(
        policy_version=AI_REVIEW_PAYLOAD_POLICY_VERSION,
        event_snapshot_id=event.event_snapshot_id,
        deepseek_payload=deepseek,
        claude_payload=claude,
        token_policy=token_policy,
        deepseek_estimated_input_tokens=deepseek_count,
        claude_estimated_input_tokens=claude_count,
        claude_token_budget_decision=classification,
        entity_mapping_result=mapping,
        projection_id=None,
    )


def _require_exact_fields(values: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if not isinstance(values, Mapping) or frozenset(values) != expected:
        raise AIReviewPayloadProjectionError("invalid " + label + " fields")


def _require_nonnegative_integer(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise AIReviewPayloadProjectionError(field + " must be a non-negative integer")
    return value


def _require_hash(value: Any, field: str) -> str:
    if type(value) is not str or len(value) != _HASH_LENGTH:
        raise AIReviewPayloadProjectionError("invalid " + field)
    if any(character not in "0123456789abcdef" for character in value):
        raise AIReviewPayloadProjectionError("invalid " + field)
    return value


def _require_task(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise AIReviewPayloadProjectionError("review_task must be a non-empty string")
    return value


def _require_event(value: Any) -> NormalizedNewsEventV1:
    if type(value) is not NormalizedNewsEventV1:
        raise AIReviewPayloadProjectionError("normalized_event must be NormalizedNewsEventV1")
    return value


def _require_policy(value: Any) -> SourcePolicyDecisionV1:
    if type(value) is not SourcePolicyDecisionV1:
        raise AIReviewPayloadProjectionError(
            "source_policy_decision must be SourcePolicyDecisionV1"
        )
    return value


def _require_mapping(value: Any) -> EntityMappingResultV1:
    if type(value) is not EntityMappingResultV1:
        raise AIReviewPayloadProjectionError(
            "entity_mapping_result must be EntityMappingResultV1"
        )
    return value


def _validate_input_binding(
    event: NormalizedNewsEventV1,
    policy: SourcePolicyDecisionV1,
    mapping: EntityMappingResultV1,
    event_snapshot_id: str,
) -> None:
    if event.event_snapshot_id != event_snapshot_id:
        raise AIReviewPayloadProjectionError("normalized_event snapshot mismatch")
    if mapping.event_snapshot_id != event_snapshot_id:
        raise AIReviewPayloadProjectionError("entity_mapping_result snapshot mismatch")
    if mapping.source_policy_decision != policy:
        raise AIReviewPayloadProjectionError("entity_mapping_result source policy mismatch")
    if policy.decision != "ELIGIBLE":
        raise AIReviewPayloadProjectionError("source_policy_decision must be ELIGIBLE")


def _freeze_evidence(value: Any, event_snapshot_id: str) -> tuple[Mapping[str, str], ...]:
    if isinstance(value, (str, bytes)):
        raise AIReviewPayloadProjectionError("bounded_evidence must be a collection")
    try:
        supplied = tuple(value)
    except TypeError as exc:
        raise AIReviewPayloadProjectionError("bounded_evidence must be a collection") from exc
    records: dict[str, Mapping[str, str]] = {}
    for item in supplied:
        if not isinstance(item, Mapping) or frozenset(item) != _EVIDENCE_FIELDS:
            raise AIReviewPayloadProjectionError("invalid bounded evidence")
        evidence_id = _require_identifier(item["evidence_ref_id"], "evidence_ref_id")
        snapshot = _require_hash(item["event_snapshot_id"], "evidence event_snapshot_id")
        if snapshot != event_snapshot_id:
            raise AIReviewPayloadProjectionError("evidence snapshot mismatch")
        source_field = _require_identifier(item["source_field"], "source_field")
        excerpt = _require_task(item["excerpt"])
        excerpt_hash = _require_hash(item["excerpt_sha256"], "excerpt_sha256")
        if excerpt_hash != sha256_hex(excerpt.encode("utf-8")):
            raise AIReviewPayloadProjectionError("excerpt_sha256 does not match excerpt")
        frozen = MappingProxyType(
            {
                "evidence_ref_id": evidence_id,
                "event_snapshot_id": snapshot,
                "source_field": source_field,
                "excerpt": excerpt,
                "excerpt_sha256": excerpt_hash,
            }
        )
        prior = records.get(evidence_id)
        if prior is not None and dict(prior) != dict(frozen):
            raise AIReviewPayloadProjectionError("conflicting evidence_ref_id")
        records[evidence_id] = frozen
    if not records:
        raise AIReviewPayloadProjectionError("bounded_evidence must not be empty")
    return tuple(records[key] for key in sorted(records))


def _require_identifier(value: Any, field: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise AIReviewPayloadProjectionError("invalid " + field)
    if not all(character.isalnum() or character in "_-:" for character in value):
        raise AIReviewPayloadProjectionError("invalid " + field)
    return value


def _stable_prefix() -> tuple[str, ...]:
    return (
        "phase-10-review-authority-v1",
        "closed-output-schema-v1",
        "deterministic-review-rubric-v1",
        CLAUDE_PAYLOAD_VERSION,
    )


def _freeze_prefix(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise AIReviewPayloadProjectionError("stable_prefix must be a collection")
    try:
        prefix = tuple(value)
    except TypeError as exc:
        raise AIReviewPayloadProjectionError("stable_prefix must be a collection") from exc
    if prefix != _stable_prefix():
        raise AIReviewPayloadProjectionError("invalid stable_prefix")
    return prefix


def _dynamic_suffix(
    event: NormalizedNewsEventV1,
    policy: SourcePolicyDecisionV1,
    mapping: EntityMappingResultV1,
    evidence: tuple[Mapping[str, str], ...],
    task: str,
) -> dict[str, Any]:
    return {
        "event_snapshot_id": event.event_snapshot_id,
        "normalized_event": event.to_mapping(),
        "source_policy": _source_policy_mapping(policy),
        "entity_mapping": _entity_mapping_mapping(mapping),
        "bounded_evidence": [dict(item) for item in evidence],
        "review_task": task,
    }


def _deepseek_semantic_mapping(
    event: NormalizedNewsEventV1,
    policy: SourcePolicyDecisionV1,
    mapping: EntityMappingResultV1,
    evidence: tuple[Mapping[str, str], ...],
    task: str,
) -> dict[str, Any]:
    return {
        "payload_version": DEEPSEEK_PAYLOAD_VERSION,
        "event_snapshot_id": event.event_snapshot_id,
        "normalized_event": event.to_mapping(),
        "source_policy": _source_policy_mapping(policy),
        "entity_mapping": _entity_mapping_mapping(mapping),
        "bounded_evidence": [dict(item) for item in evidence],
        "review_task": task,
    }


def _claude_semantic_mapping(
    event: NormalizedNewsEventV1,
    policy: SourcePolicyDecisionV1,
    mapping: EntityMappingResultV1,
    evidence: tuple[Mapping[str, str], ...],
    task: str,
    stable_prefix: tuple[str, ...],
    dynamic_suffix: Mapping[str, Any],
    stable_identity: str,
    dynamic_identity: str,
) -> dict[str, Any]:
    return {
        "payload_version": CLAUDE_PAYLOAD_VERSION,
        "event_snapshot_id": event.event_snapshot_id,
        "normalized_event": event.to_mapping(),
        "source_policy": _source_policy_mapping(policy),
        "entity_mapping": _entity_mapping_mapping(mapping),
        "bounded_evidence": [dict(item) for item in evidence],
        "review_task": task,
        "stable_prefix_identity": stable_identity,
        "dynamic_payload_identity": dynamic_identity,
        "cache_policy_version": _CACHE_POLICY_VERSION,
        "cache_ttl_seconds": _CACHE_TTL_SECONDS,
        "cache_breakpoint_count": 1,
        "stable_prefix": list(stable_prefix),
        "dynamic_suffix": _thaw_json(dynamic_suffix),
    }


def _source_policy_mapping(value: SourcePolicyDecisionV1) -> dict[str, Any]:
    payload = value.to_mapping()
    payload["reason_codes"] = list(value.reason_codes)
    return payload


def _entity_mapping_mapping(value: EntityMappingResultV1) -> dict[str, Any]:
    return {
        "mapping_policy_version": value.mapping_policy_version,
        "event_snapshot_id": value.event_snapshot_id,
        "source_policy_decision": _source_policy_mapping(value.source_policy_decision),
        "accepted_candidates": [_candidate_mapping(item) for item in value.accepted_candidates],
        "rejected_candidates": [_candidate_mapping(item) for item in value.rejected_candidates],
        "ambiguous_candidates": [_candidate_mapping(item) for item in value.ambiguous_candidates],
        "unresolved_candidates": [_candidate_mapping(item) for item in value.unresolved_candidates],
        "mapping_status": value.mapping_status,
        "reason_codes": list(value.reason_codes),
        "mapping_result_id": value.mapping_result_id,
    }


def _candidate_mapping(value: Any) -> dict[str, Any]:
    payload = value.to_mapping()
    payload["evidence_refs"] = [dict(item) for item in value.evidence_refs]
    payload["rejection_reason_codes"] = list(value.rejection_reason_codes)
    return payload


def _freeze_json_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AIReviewPayloadProjectionError(field + " must be a mapping")
    return _freeze_json(value, field)


def _freeze_json(value: Any, field: str) -> Any:
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, datetime):
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise AIReviewPayloadProjectionError("invalid " + field)
            frozen[key] = _freeze_json(item, field)
        return MappingProxyType(frozen)
    if isinstance(value, list):
        return tuple(_freeze_json(item, field) for item in value)
    raise AIReviewPayloadProjectionError("invalid " + field)


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _hash_mapping(value: Mapping[str, Any]) -> str:
    try:
        return sha256_hex(canonical_json_bytes(value))
    except ValueError as exc:
        raise AIReviewPayloadProjectionError("payload is not canonical") from exc


def _validate_supplied_hash(value: Any, derived: str, field: str) -> None:
    if value is None:
        return
    if _require_hash(value, field) != derived:
        raise AIReviewPayloadProjectionError(field + " does not match payload")


def _estimated_count(counter: Any, payload: Mapping[str, Any]) -> int:
    if not callable(counter):
        raise AIReviewPayloadProjectionError("token_counter must be callable")
    count = counter(canonical_json_bytes(payload))
    return _require_nonnegative_integer(count, "estimated token count")


def _budget_decision(count: int, policy: PayloadTokenPolicyV1) -> str:
    if count > policy.claude_input_hard_limit_tokens:
        return "HARD_LIMIT_EXCEEDED"
    if count < policy.claude_target_input_min_tokens:
        return "BELOW_TARGET_COMPLETE"
    if count <= policy.claude_target_input_max_tokens:
        return "WITHIN_TARGET"
    return "ABOVE_TARGET_WITHIN_HARD_LIMIT"


def _projection_id(
    event_snapshot_id: str,
    deepseek: DeepSeekReviewPayloadV1,
    claude: ClaudeReviewPayloadV1,
    policy: PayloadTokenPolicyV1,
    mapping: EntityMappingResultV1,
) -> str:
    return _hash_mapping(
        {
            "policy_version": AI_REVIEW_PAYLOAD_POLICY_VERSION,
            "event_snapshot_id": event_snapshot_id,
            "deepseek_payload_sha256": deepseek.payload_sha256,
            "claude_payload_sha256": claude.payload_sha256,
            "token_policy": policy.to_mapping(),
            "entity_mapping_result_id": mapping.mapping_result_id,
        }
    )
