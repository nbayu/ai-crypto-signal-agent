"""RED specification for deterministic Phase 10 AI-review payload projection."""

from __future__ import annotations

import hashlib
import inspect
from datetime import datetime, timezone

import pytest
import engine.ai_review_payload_projector_v1 as projector

from engine.news_entity_mapping_v1 import (
    ENTITY_MAPPING_POLICY_VERSION,
    EntityCandidateV1,
    map_entity_candidates,
)
from engine.news_event_contract_v1 import (
    EVENT_SCHEMA_VERSION,
    NormalizedNewsEventV1,
    canonical_json_bytes,
)
from engine.news_source_policy_v1 import SourcePolicyDecisionV1
from engine.ai_review_payload_projector_v1 import (
    AI_REVIEW_PAYLOAD_POLICY_VERSION,
    CLAUDE_PAYLOAD_VERSION,
    DEEPSEEK_PAYLOAD_VERSION,
    AIReviewPayloadProjectionError,
    AIReviewPayloadProjectionV1,
    ClaudeReviewPayloadV1,
    DeepSeekReviewPayloadV1,
    PayloadTokenPolicyV1,
    project_ai_review_payloads,
)


UTC = timezone.utc
EVENT_SNAPSHOT_ID = "a" * 64
OTHER_EVENT_SNAPSHOT_ID = "b" * 64
EVALUATION_TIMESTAMP = datetime(2026, 7, 16, 12, 30, tzinfo=UTC)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _event(*, title: str = "Alpha protocol announced", body: str = "Alpha protocol released a deterministic update."):
    return NormalizedNewsEventV1(
        event_namespace="news",
        authoritative_source_namespace="fictional-wire",
        authoritative_source_event_id="source-event-001",
        deterministic_source_key=None,
        normalized_primary_subject="asset:alpha",
        canonical_event_class="PROTOCOL_UPDATE",
        normalized_title=title,
        normalized_body=body,
        normalized_language="en-US",
        publication_timestamp_utc=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
        point_in_time_timestamp_utc=datetime(2026, 7, 16, 12, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fictional-publisher"},
        previous_event_version_id=None,
        event_version_number=1,
        source_snapshot_ref={
            "source_namespace": "fictional-wire",
            "source_id": "source-001",
        },
        schema_version=EVENT_SCHEMA_VERSION,
    )


def _policy(decision: str = "ELIGIBLE") -> SourcePolicyDecisionV1:
    reason = "SOURCE_ELIGIBLE" if decision == "ELIGIBLE" else "SOURCE_TYPE_BLOCKED"
    return SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1",
        decision=decision,
        primary_reason_code=reason,
        reason_codes=(reason,),
        evaluated_source_snapshot_ref={
            "source_namespace": "fictional-wire",
            "source_id": "source-001",
        },
        evaluation_timestamp_utc=EVALUATION_TIMESTAMP,
        source_namespace="fictional-wire",
        source_id="source-001",
    )


def _candidate(event_snapshot_id: str):
    source_text = "Alpha protocol"
    return EntityCandidateV1(
        candidate_id="candidate-alpha",
        entity_type="DIGITAL_ASSET",
        canonical_entity_id="asset:alpha",
        canonical_name="Alpha",
        canonical_symbol="ALPHA",
        source_text=source_text,
        source_text_sha256=_sha256_text(source_text),
        evidence_refs=[
            {
                "evidence_ref_id": "evidence-001",
                "event_snapshot_id": event_snapshot_id,
                "reference_type": "EVENT_FIELD",
                "field_name": "normalized_title",
            }
        ],
        confidence_basis="EXPLICIT_CALLER_ASSERTION",
        supplied_confidence=None,
        ambiguity_group_id=None,
        candidate_status="ACCEPTED",
        rejection_reason_codes=[],
        mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )


def _mapping(event, *, decision=None, event_snapshot_id=None):
    snapshot_id = event.event_snapshot_id if event_snapshot_id is None else event_snapshot_id
    return map_entity_candidates(
        event_snapshot_id=snapshot_id,
        source_policy_decision=_policy() if decision is None else decision,
        candidates=[_candidate(snapshot_id)],
    )


def _evidence(
    event_snapshot_id: str,
    *,
    evidence_ref_id: str = "evidence-001",
    excerpt: str = "Alpha protocol released a deterministic update.",
    source_field: str = "normalized_body",
):
    return {
        "evidence_ref_id": evidence_ref_id,
        "event_snapshot_id": event_snapshot_id,
        "source_field": source_field,
        "excerpt": excerpt,
        "excerpt_sha256": _sha256_text(excerpt),
    }


def _token_policy(**overrides):
    values = _token_policy_values()
    values.update(overrides)
    return PayloadTokenPolicyV1(**values)


def _token_policy_values():
    return {
        "claude_input_hard_limit_tokens": 8000,
        "claude_target_input_min_tokens": 2000,
        "claude_target_input_max_tokens": 5000,
        "claude_output_hard_limit_tokens": 1000,
        "maximum_claude_logical_reviews_per_event": 1,
        "maximum_provider_attempts_per_review": 2,
        "maximum_retry_count": 1,
    }


def _project(
    *,
    event=None,
    decision=None,
    mapping=None,
    evidence=None,
    review_task="Assess the canonical event facts for review.",
    token_policy=None,
    token_count=1200,
    **overrides,
):
    event = _event() if event is None else event
    decision = _policy() if decision is None else decision
    mapping = _mapping(event, decision=decision) if mapping is None else mapping
    evidence = (
        [_evidence(event.event_snapshot_id)] if evidence is None else evidence
    )
    values = {
        "normalized_event": event,
        "source_policy_decision": decision,
        "entity_mapping_result": mapping,
        "bounded_evidence": evidence,
        "review_task": review_task,
        "token_policy": _token_policy() if token_policy is None else token_policy,
        "token_counter": lambda _: token_count,
        "cache_ttl_seconds": 300,
    }
    values.update(overrides)
    return project_ai_review_payloads(**values)


def expect_projection_error(callable_object, *args, **kwargs):
    with pytest.raises(AIReviewPayloadProjectionError):
        callable_object(*args, **kwargs)


def test_public_api_and_versions_are_frozen():
    assert AI_REVIEW_PAYLOAD_POLICY_VERSION == "ai-review-payload-policy-v1"
    assert DEEPSEEK_PAYLOAD_VERSION == "deepseek-review-v1"
    assert CLAUDE_PAYLOAD_VERSION == "claude-review-v1"
    assert tuple(projector.__all__) == (
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
    assert tuple(project_ai_review_payloads.__module__.split("."))[-1] == (
        "ai_review_payload_projector_v1"
    )


def test_token_policy_is_closed_immutable_and_frozen():
    policy = _token_policy()
    assert policy.claude_input_hard_limit_tokens == 8000
    assert policy.claude_target_input_min_tokens == 2000
    assert policy.claude_target_input_max_tokens == 5000
    assert policy.claude_output_hard_limit_tokens == 1000
    assert policy.maximum_claude_logical_reviews_per_event == 1
    assert policy.maximum_provider_attempts_per_review == 2
    assert policy.maximum_retry_count == 1
    with pytest.raises((AttributeError, TypeError)):
        policy.maximum_retry_count = 0
    expect_projection_error(PayloadTokenPolicyV1, **{
        **_token_policy_values(),
        "unexpected": "field",
    })


@pytest.mark.parametrize(
    "field,value",
    [
        ("claude_input_hard_limit_tokens", True),
        ("claude_output_hard_limit_tokens", -1),
        ("maximum_retry_count", 2),
        ("maximum_provider_attempts_per_review", 1),
        ("maximum_claude_logical_reviews_per_event", 2),
        ("claude_input_hard_limit_tokens", 9000),
    ],
)
def test_token_policy_rejects_invalid_or_authority_raising_values(field, value):
    values = _token_policy_values()
    values[field] = value
    expect_projection_error(PayloadTokenPolicyV1, **values)


def test_canonical_inputs_bind_to_one_event_snapshot():
    result = _project()
    assert result.event_snapshot_id == result.deepseek_payload.event_snapshot_id
    assert result.event_snapshot_id == result.claude_payload.event_snapshot_id
    assert result.event_snapshot_id == result.deepseek_payload.normalized_event.event_snapshot_id
    assert result.entity_mapping_result.event_snapshot_id == result.event_snapshot_id


def test_projection_result_is_closed_immutable_and_versioned():
    result = _project()
    assert result.policy_version == AI_REVIEW_PAYLOAD_POLICY_VERSION
    assert isinstance(result, AIReviewPayloadProjectionV1)
    with pytest.raises((AttributeError, TypeError)):
        result.event_snapshot_id = OTHER_EVENT_SNAPSHOT_ID
    values = result.to_mapping()
    values["unexpected"] = "field"
    expect_projection_error(AIReviewPayloadProjectionV1, **values)


def test_lookalike_canonical_inputs_are_rejected():
    event = _event()
    mapping = _mapping(event)
    expect_projection_error(
        project_ai_review_payloads,
        normalized_event=event.to_mapping(),
        source_policy_decision=_policy(),
        entity_mapping_result=mapping,
        bounded_evidence=[_evidence(event.event_snapshot_id)],
        review_task="Assess facts.",
        token_policy=_token_policy(),
        token_counter=lambda _: 100,
    )


def test_non_eligible_source_policy_cannot_project():
    event = _event()
    decision = _policy("BLOCKED")
    mapping = _mapping(event, decision=decision)
    expect_projection_error(
        _project,
        event=event,
        decision=decision,
        mapping=mapping,
    )


def test_cross_snapshot_state_is_rejected():
    event = _event()
    mapping = _mapping(event, event_snapshot_id=OTHER_EVENT_SNAPSHOT_ID)
    expect_projection_error(
        _project,
        event=event,
        mapping=mapping,
    )


def test_projection_does_not_repair_inconsistent_mapping_snapshot():
    event = _event()
    mapping = _mapping(event, event_snapshot_id=OTHER_EVENT_SNAPSHOT_ID)
    expect_projection_error(
        project_ai_review_payloads,
        normalized_event=event,
        source_policy_decision=_policy(),
        entity_mapping_result=mapping,
        bounded_evidence=[_evidence(event.event_snapshot_id)],
        review_task="Assess facts.",
        token_policy=_token_policy(),
        token_counter=lambda _: 100,
    )


def test_deepseek_payload_is_closed_and_provider_neutral():
    result = _project()
    payload = result.deepseek_payload
    assert isinstance(payload, DeepSeekReviewPayloadV1)
    assert payload.payload_version == DEEPSEEK_PAYLOAD_VERSION
    assert payload.event_snapshot_id == result.event_snapshot_id
    assert payload.payload_sha256.islower()
    assert len(payload.payload_sha256) == 64
    fields = payload.to_mapping()
    for forbidden in (
        "candles", "ohlcv", "order_book", "bids", "asks", "trades",
        "balances", "positions", "open_orders", "account", "capital",
        "provider_execution_id", "attempt_number", "retry_count", "cost",
        "latency_ms", "cache_hit", "input_tokens", "output_tokens",
    ):
        assert forbidden not in fields


def test_claude_payload_is_separate_and_escalation_specific():
    result = _project(review_task="Challenge the canonical event evidence.")
    payload = result.claude_payload
    assert isinstance(payload, ClaudeReviewPayloadV1)
    assert payload.payload_version == CLAUDE_PAYLOAD_VERSION
    assert payload.event_snapshot_id == result.event_snapshot_id
    assert payload.review_task == "Challenge the canonical event evidence."
    assert payload.payload_sha256 != result.deepseek_payload.payload_sha256
    assert type(payload) is not type(result.deepseek_payload)


@pytest.mark.parametrize("payload_type", [DeepSeekReviewPayloadV1, ClaudeReviewPayloadV1])
def test_payload_unknown_market_and_execution_fields_are_rejected(payload_type):
    result = _project()
    payload = (
        result.deepseek_payload if payload_type is DeepSeekReviewPayloadV1
        else result.claude_payload
    )
    values = payload.to_mapping()
    for field, value in (
        ("candles", []),
        ("order_book", {}),
        ("positions", []),
        ("api_key", "secret"),
        ("provider_execution_id", "execution-001"),
        ("cache_hit", True),
    ):
        candidate_values = dict(values)
        candidate_values[field] = value
        expect_projection_error(payload_type, **candidate_values)


def test_bounded_evidence_is_closed_hash_valid_and_deterministically_ordered():
    first = _evidence(EVENT_SNAPSHOT_ID, evidence_ref_id="evidence-b", excerpt="B")
    second = _evidence(EVENT_SNAPSHOT_ID, evidence_ref_id="evidence-a", excerpt="A")
    result = _project(evidence=[first, second, first])
    evidence = result.deepseek_payload.bounded_evidence
    assert [item["evidence_ref_id"] for item in evidence] == [
        "evidence-a", "evidence-b"
    ]
    assert all(len(item["excerpt_sha256"]) == 64 for item in evidence)
    assert result == _project(evidence=[second, first])


def test_bounded_evidence_rejects_forged_hash_and_unknown_fields():
    item = _evidence(EVENT_SNAPSHOT_ID)
    item["excerpt_sha256"] = "0" * 64
    expect_projection_error(_project, evidence=[item])
    item = _evidence(EVENT_SNAPSHOT_ID)
    item["unknown"] = "field"
    expect_projection_error(_project, evidence=[item])


def test_event_specific_data_is_not_in_stable_prefix():
    first = _project(event=_event(title="Alpha headline"))
    second = _project(event=_event(title="Beta headline"))
    assert first.claude_payload.stable_prefix_identity == second.claude_payload.stable_prefix_identity
    assert first.claude_payload.dynamic_payload_identity != second.claude_payload.dynamic_payload_identity
    assert first.claude_payload.cache_policy_version == "news-prompt-cache-v1"
    assert first.claude_payload.cache_ttl_seconds == 300
    assert first.claude_payload.cache_breakpoint_count == 1
    assert first.claude_payload.stable_prefix_identity != first.event_snapshot_id


def test_one_hour_cache_ttl_is_rejected():
    expect_projection_error(_project, cache_ttl_seconds=3600)


def test_payload_sha256_is_recomputed_from_semantic_payload():
    result = _project()
    values = result.deepseek_payload.to_mapping()
    supplied = values.pop("payload_sha256")
    expected = hashlib.sha256(canonical_json_bytes(values)).hexdigest()
    assert supplied == expected


def test_manual_canonical_digest_is_independent_of_projector():
    canonical = (
        b'{"event_snapshot_id":"'
        + EVENT_SNAPSHOT_ID.encode("ascii")
        + b'","payload_version":"deepseek-review-v1"}'
    )
    assert hashlib.sha256(canonical).hexdigest() == (
        "24b5be44be2093e0ecdbb4836900900fe799edc0eb10dffe6d0ffbd980112c0f"
    )


@pytest.mark.parametrize(
    "estimated_tokens,decision",
    [
        (100, "BELOW_TARGET_COMPLETE"),
        (2000, "WITHIN_TARGET"),
        (5000, "WITHIN_TARGET"),
        (5001, "ABOVE_TARGET_WITHIN_HARD_LIMIT"),
        (8000, "ABOVE_TARGET_WITHIN_HARD_LIMIT"),
    ],
)
def test_token_budget_boundaries_are_deterministic(estimated_tokens, decision):
    result = _project(token_count=estimated_tokens)
    assert result.claude_token_budget_decision == decision
    assert result.claude_estimated_input_tokens == estimated_tokens


def test_token_hard_limit_is_fail_closed():
    expect_projection_error(_project, token_count=8001)


@pytest.mark.parametrize("counter", [lambda _: True, lambda _: -1, lambda _: "100"])
def test_token_counter_must_return_nonnegative_exact_integer(counter):
    expect_projection_error(_project, token_counter=counter)


def test_token_classification_is_not_payload_identity():
    below = _project(token_count=100)
    within = _project(token_count=4000)
    assert below.deepseek_payload.payload_sha256 == within.deepseek_payload.payload_sha256
    assert below.claude_payload.payload_sha256 == within.claude_payload.payload_sha256
    assert below.projection_id == within.projection_id
    assert below.claude_token_budget_decision != within.claude_token_budget_decision


def test_estimated_tokens_are_not_provider_usage_telemetry():
    result = _project()
    aggregate = result.to_mapping()
    for field in (
        "input_tokens", "output_tokens", "cache_creation_input_tokens",
        "cache_read_input_tokens", "cost_micro_usd", "latency_ms",
        "request_id", "provider_execution_id", "attempt_number", "retry_count",
    ):
        assert field not in aggregate
    assert "estimated_input_tokens" not in result.deepseek_payload.to_mapping()


def test_projection_identity_excludes_counter_and_cache_execution_state():
    first = _project(token_count=100)
    second = _project(token_count=5000)
    assert first.projection_id == second.projection_id
    assert first.claude_payload.payload_sha256 == second.claude_payload.payload_sha256
    assert first.deepseek_payload.payload_sha256 == second.deepseek_payload.payload_sha256


def test_projection_result_is_immutable_and_deeply_detached():
    evidence = [_evidence(EVENT_SNAPSHOT_ID)]
    task = "Assess canonical facts."
    result = _project(evidence=evidence, review_task=task)
    evidence[0]["excerpt"] = "mutated"
    evidence.append(_evidence(EVENT_SNAPSHOT_ID, evidence_ref_id="extra"))
    assert result.claude_payload.bounded_evidence[0]["excerpt"] != "mutated"
    assert result.claude_payload.review_task == task
    with pytest.raises((AttributeError, TypeError)):
        result.deepseek_payload.bounded_evidence[0]["excerpt"] = "mutated"


def test_payload_input_objects_are_not_mutated():
    event = _event()
    decision = _policy()
    mapping = _mapping(event, decision=decision)
    before = (event.to_mapping(), decision.to_mapping(), mapping.to_mapping())
    _project(event=event, decision=decision, mapping=mapping)
    assert (event.to_mapping(), decision.to_mapping(), mapping.to_mapping()) == before


def test_payload_versions_diverge_and_are_identity_material():
    result = _project()
    assert result.deepseek_payload.payload_version != result.claude_payload.payload_version
    assert result.deepseek_payload.payload_sha256 != result.claude_payload.payload_sha256


def test_projection_identity_changes_for_material_event_change():
    first = _project(event=_event(title="Alpha headline"))
    changed = _project(event=_event(title="Changed headline"))
    assert first.projection_id != changed.projection_id
    assert first.deepseek_payload.payload_sha256 != changed.deepseek_payload.payload_sha256


def test_payloads_contain_only_allowlisted_canonical_sections():
    result = _project()
    allowed = {
        "payload_version", "event_snapshot_id", "normalized_event",
        "source_policy", "entity_mapping", "bounded_evidence", "review_task",
        "payload_sha256", "stable_prefix_identity", "dynamic_payload_identity",
        "cache_policy_version", "cache_ttl_seconds", "cache_breakpoint_count",
        "stable_prefix", "dynamic_suffix",
    }
    assert set(result.deepseek_payload.to_mapping()) <= allowed
    assert set(result.claude_payload.to_mapping()) <= allowed


def test_projection_rejects_empty_or_malformed_review_task():
    expect_projection_error(_project, review_task="")
    expect_projection_error(_project, review_task="  review task  ")
    expect_projection_error(_project, review_task=123)


def test_projection_rejects_malformed_evidence_snapshot():
    expect_projection_error(
        _project,
        evidence=[_evidence(OTHER_EVENT_SNAPSHOT_ID)],
    )


def test_no_provider_or_runtime_authority_is_present_in_source():
    source = inspect.getsource(project_ai_review_payloads)
    for forbidden in (
        "anthropic", "openai", "requests", "httpx", "socket", "os.environ",
        "datetime.now", "time.time", "random", "subprocess", "uuid",
        "api_key", "provider_execution_id", "input_tokens", "output_tokens",
    ):
        assert forbidden not in source
