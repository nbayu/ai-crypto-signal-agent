"""RED contract tests for the deterministic DeepSeek primary-review boundary."""

from __future__ import annotations

import hashlib
import inspect
from datetime import datetime, timezone

import pytest

import engine.deepseek_primary_review_provider_v1 as provider
from engine.ai_review_payload_projector_v1 import (
    DEEPSEEK_PAYLOAD_VERSION,
    DeepSeekReviewPayloadV1,
)
from engine.news_entity_mapping_v1 import (
    ENTITY_MAPPING_POLICY_VERSION,
    EntityCandidateV1,
    map_entity_candidates,
)
from engine.news_event_contract_v1 import EVENT_SCHEMA_VERSION, NormalizedNewsEventV1
from engine.news_source_policy_v1 import SourcePolicyDecisionV1


UTC = timezone.utc
POLICY_VERSION = "deepseek-primary-review-policy-v1"
EVENT_SNAPSHOT_ID = "a" * 64
OTHER_EVENT_SNAPSHOT_ID = "b" * 64
MODEL_POLICY_ID = "fictional-deepseek-policy-v1"
MODEL_ID = "fictional-deepseek-model-v1"
REQUEST_ID = "request-001"
EVALUATION_TIMESTAMP = datetime(2026, 7, 16, 12, 30, tzinfo=UTC)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _event(*, title: str = "Alpha protocol announced") -> NormalizedNewsEventV1:
    return NormalizedNewsEventV1(
        event_namespace="news",
        authoritative_source_namespace="fictional-wire",
        authoritative_source_event_id="source-event-001",
        deterministic_source_key=None,
        normalized_primary_subject="asset:alpha",
        canonical_event_class="PROTOCOL_UPDATE",
        normalized_title=title,
        normalized_body="Alpha protocol released a deterministic update.",
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


def _candidate(event_snapshot_id: str) -> EntityCandidateV1:
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


def _mapping(event: NormalizedNewsEventV1, policy=None):
    policy = _policy() if policy is None else policy
    return map_entity_candidates(
        event_snapshot_id=event.event_snapshot_id,
        source_policy_decision=policy,
        candidates=[_candidate(event.event_snapshot_id)],
    )


def _payload(*, event=None, policy=None, title="Assess the canonical event facts."):
    event = _event() if event is None else event
    policy = _policy() if policy is None else policy
    return DeepSeekReviewPayloadV1(
        payload_version=DEEPSEEK_PAYLOAD_VERSION,
        event_snapshot_id=event.event_snapshot_id,
        normalized_event=event,
        source_policy=policy,
        entity_mapping=_mapping(event, policy),
        bounded_evidence=(
            {
                "evidence_ref_id": "evidence-001",
                "event_snapshot_id": event.event_snapshot_id,
                "source_field": "normalized_body",
                "excerpt": "Alpha protocol released a deterministic update.",
                "excerpt_sha256": _sha256_text(
                    "Alpha protocol released a deterministic update."
                ),
            },
        ),
        review_task=title,
        payload_sha256=None,
    )


def _policy_values(**overrides):
    values = {
        "policy_version": POLICY_VERSION,
        "provider_name": "DEEPSEEK",
        "model_policy_id": MODEL_POLICY_ID,
        "model_id": MODEL_ID,
        "maximum_logical_reviews_per_event": 1,
        "maximum_provider_attempts": 2,
        "maximum_retry_count": 1,
        "timeout_seconds": 30,
        "budget_authorized": True,
        "maximum_authorized_cost_micro_usd": 5_000_000,
    }
    values.update(overrides)
    return values


def _execution_policy(**overrides):
    values = _policy_values(**overrides)
    return provider.DeepSeekExecutionPolicyV1(**values)


def _success_response(request, **overrides):
    values = {
        "policy_version": POLICY_VERSION,
        "event_snapshot_id": request["event_snapshot_id"],
        "request_payload_sha256": request["payload_sha256"],
        "logical_review_id": request["logical_review_id"],
        "review_status": "COMPLETED",
        "review_conclusion": "FACTUAL_REVIEW_COMPLETE",
        "ambiguity_level": "NONE",
        "contradiction_present": False,
        "evidence_sufficiency": "SUFFICIENT",
        "entity_confidence_state": "EXPLICIT",
        "source_policy_concern_state": "NONE",
        "material_risk_flags": ("NONE",),
        "reason_codes": ("REVIEW_COMPLETED",),
        "structured_explanation": "Bounded deterministic review explanation.",
        "escalation_evidence_refs": ("evidence-001",),
        "semantic_result_id": None,
    }
    values.update(overrides)
    return values


class _FakeTransport:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        return outcome(request) if callable(outcome) else outcome


def _run(*, payload=None, policy=None, transport=None, **overrides):
    payload = _payload() if payload is None else payload
    policy = _execution_policy() if policy is None else policy
    transport = _FakeTransport([_success_response]) if transport is None else transport
    values = {
        "payload": payload,
        "execution_policy": policy,
        "transport": transport,
    }
    values.update(overrides)
    return provider.execute_deepseek_primary_review(**values)


def _expect_provider_error(callable_object, *args, **kwargs):
    with pytest.raises(provider.DeepSeekPrimaryReviewProviderError):
        callable_object(*args, **kwargs)


def _expected_logical_review_id(payload, policy):
    from engine.news_event_contract_v1 import canonical_json_bytes

    semantic_identity = {
        "event_snapshot_id": payload.event_snapshot_id,
        "payload_version": payload.payload_version,
        "payload_sha256": payload.payload_sha256,
        "model_policy_id": policy.model_policy_id,
        "model_id": policy.model_id,
        "review_task": payload.review_task,
    }
    return hashlib.sha256(canonical_json_bytes(semantic_identity)).hexdigest()


def test_public_api_versions_and_module_surface_are_frozen():
    assert provider.DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION == POLICY_VERSION
    assert provider.__all__ == (
        "DeepSeekPrimaryReviewProviderError",
        "DEEPSEEK_PRIMARY_REVIEW_POLICY_VERSION",
        "DeepSeekExecutionPolicyV1",
        "DeepSeekPrimaryReviewResultV1",
        "DeepSeekProviderExecutionRecordV1",
        "DeepSeekPrimaryReviewRunV1",
        "execute_deepseek_primary_review",
    )
    assert type(provider.__all__) is tuple
    assert len(provider.__all__) == len(set(provider.__all__)) == 7
    assert all(hasattr(provider, name) for name in provider.__all__)


def test_execution_policy_is_closed_immutable_and_frozen():
    policy = _execution_policy()
    assert policy.provider_name == "DEEPSEEK"
    assert policy.maximum_logical_reviews_per_event == 1
    assert policy.maximum_provider_attempts == 2
    assert policy.maximum_retry_count == 1
    assert policy.budget_authorized is True
    with pytest.raises((AttributeError, TypeError)):
        policy.maximum_retry_count = 0
    _expect_provider_error(
        provider.DeepSeekExecutionPolicyV1,
        **_policy_values(unexpected="field"),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("maximum_logical_reviews_per_event", True),
        ("maximum_provider_attempts", 1),
        ("maximum_retry_count", 2),
        ("timeout_seconds", -1),
        ("maximum_authorized_cost_micro_usd", True),
        ("maximum_authorized_cost_micro_usd", -1),
        ("provider_name", "OTHER"),
    ],
)
def test_execution_policy_rejects_invalid_or_authority_raising_values(field, value):
    _expect_provider_error(provider.DeepSeekExecutionPolicyV1, **_policy_values(**{field: value}))


def test_execution_policy_requires_explicit_budget_and_model_policy():
    values = _policy_values()
    values.pop("budget_authorized")
    _expect_provider_error(provider.DeepSeekExecutionPolicyV1, **values)
    _expect_provider_error(
        provider.DeepSeekExecutionPolicyV1,
        **_policy_values(model_id=""),
    )


def test_exact_payload_type_is_required():
    payload = _payload()
    _run(payload=payload)
    for lookalike in (payload.to_mapping(), {}, payload.normalized_event, payload.source_policy):
        _expect_provider_error(_run, payload=lookalike)


def test_non_callable_transport_is_rejected_before_call():
    _expect_provider_error(_run, transport=object())


def test_request_schema_and_semantic_binding_are_deterministic():
    payload = _payload()
    transport = _FakeTransport([_success_response])
    result = _run(payload=payload, transport=transport)
    request = transport.requests[0]
    assert set(request) == {
        "provider", "model_id", "payload", "payload_sha256",
        "event_snapshot_id", "logical_review_id", "attempt_number",
        "timeout_seconds", "request_id",
    }
    assert request["provider"] == "DEEPSEEK"
    assert request["model_id"] == MODEL_ID
    assert request["payload"] == payload.to_mapping()
    assert request["payload_sha256"] == payload.payload_sha256
    assert request["event_snapshot_id"] == payload.event_snapshot_id
    assert request["attempt_number"] == 1
    assert request["timeout_seconds"] == 30
    assert result.event_snapshot_id == payload.event_snapshot_id


def test_logical_review_identity_matches_manual_canonical_digest():
    payload = _payload()
    policy = _execution_policy()
    transport = _FakeTransport([_success_response])
    _run(payload=payload, policy=policy, transport=transport)
    request = transport.requests[0]
    assert request["logical_review_id"] == _expected_logical_review_id(payload, policy)


def test_logical_review_identity_excludes_operational_request_id():
    payload = _payload()
    first_transport = _FakeTransport([_success_response])
    second_transport = _FakeTransport([_success_response])
    first = _run(payload=payload, transport=first_transport)
    second = _run(payload=payload, transport=second_transport)
    assert first.logical_review_id == second.logical_review_id
    assert first_transport.requests[0]["request_id"] != second_transport.requests[0]["request_id"]


def test_successful_single_attempt_returns_separate_immutable_result_record_and_run():
    transport = _FakeTransport([_success_response])
    run = _run(transport=transport)
    assert run.final_run_status == "COMPLETED"
    assert run.total_attempts == 1
    assert run.total_retries == 0
    assert run.semantic_result.review_status == "COMPLETED"
    assert len(run.execution_records) == 1
    record = run.execution_records[0]
    assert record.attempt_number == 1
    assert record.retry_count == 0
    assert record.event_snapshot_id == run.event_snapshot_id
    assert record.payload_sha256 == run.payload_sha256
    with pytest.raises((AttributeError, TypeError)):
        run.final_run_status = "PERMANENT_FAILURE"


def test_semantic_result_identity_is_manual_and_telemetry_independent():
    transport = _FakeTransport([lambda request: _success_response(
        request,
        input_tokens=100,
        output_tokens=20,
        cost_micro_usd=123,
        request_id="provider-request-a",
    )])
    run = _run(transport=transport)
    semantic = run.semantic_result.to_mapping()
    supplied = semantic.pop("semantic_result_id")
    from engine.news_event_contract_v1 import canonical_json_bytes

    assert supplied == hashlib.sha256(canonical_json_bytes(semantic)).hexdigest()
    assert "request_id" not in semantic
    assert "input_tokens" not in semantic
    assert "cost_micro_usd" not in semantic


def test_transient_failure_then_success_reuses_exact_semantic_request():
    def transient(request):
        return {
            "failure_class": "TRANSIENT_TRANSPORT",
            "failure_code": "TIMEOUT",
        }

    transport = _FakeTransport([transient, _success_response])
    run = _run(transport=transport)
    assert len(transport.requests) == 2
    assert transport.requests[0]["payload"] == transport.requests[1]["payload"]
    assert transport.requests[0]["payload_sha256"] == transport.requests[1]["payload_sha256"]
    assert transport.requests[0]["logical_review_id"] == transport.requests[1]["logical_review_id"]
    assert transport.requests[0]["model_id"] == transport.requests[1]["model_id"]
    assert [request["attempt_number"] for request in transport.requests] == [1, 2]
    assert run.final_run_status == "COMPLETED"
    assert run.semantic_result is not None
    assert len(run.execution_records) == 2


def test_transient_failure_exhaustion_does_not_fabricate_semantic_result():
    failure = {
        "failure_class": "TRANSIENT_TRANSPORT",
        "failure_code": "TEMPORARY_UNAVAILABLE",
    }
    transport = _FakeTransport([failure, failure])
    run = _run(transport=transport)
    assert len(transport.requests) == 2
    assert run.semantic_result is None
    assert run.final_run_status == "TRANSIENT_FAILURE"
    assert len(run.execution_records) == 2
    assert all(record.input_tokens is None for record in run.execution_records)


def test_budget_blocked_occurs_before_transport_and_fabrication():
    transport = _FakeTransport([_success_response])
    run = _run(
        policy=_execution_policy(budget_authorized=False),
        transport=transport,
    )
    assert transport.requests == []
    assert run.final_run_status == "BUDGET_BLOCKED"
    assert run.semantic_result is None
    assert run.execution_records == ()
    assert run.total_attempts == 0
    assert run.total_retries == 0


@pytest.mark.parametrize(
    "failure_class,failure_code,expected_status",
    [
        ("PERMANENT_PROVIDER", "AUTHENTICATION_FAILURE", "PERMANENT_FAILURE"),
        ("PERMANENT_PROVIDER", "PERMISSION_DENIED", "PERMANENT_FAILURE"),
        ("PERMANENT_PROVIDER", "UNSUPPORTED_MODEL", "PERMANENT_FAILURE"),
        ("PERMANENT_PROVIDER", "PROVIDER_REJECTED", "PROVIDER_REJECTED"),
        ("RESPONSE_VALIDATION", "INVALID_SCHEMA", "INVALID_RESPONSE"),
    ],
)
def test_non_retryable_failures_stop_after_one_call(failure_class, failure_code, expected_status):
    transport = _FakeTransport([{
        "failure_class": failure_class,
        "failure_code": failure_code,
    }])
    run = _run(transport=transport)
    assert len(transport.requests) == 1
    assert run.final_run_status == expected_status
    assert run.semantic_result is None or run.semantic_result.review_status == expected_status


@pytest.mark.parametrize(
    "change",
    [
        {"event_snapshot_id": OTHER_EVENT_SNAPSHOT_ID},
        {"request_payload_sha256": "c" * 64},
        {"logical_review_id": "d" * 64},
        {"review_status": "UNKNOWN"},
        {"contradiction_present": True},
        {"structured_explanation": "x" * 100_001},
        {"unexpected_authority": "route-to-claude"},
    ],
)
def test_malformed_response_is_invalid_and_not_repaired(change):
    calls = []

    def response(request):
        calls.append(request)
        values = _success_response(request)
        values.update(change)
        return values

    transport = _FakeTransport([response])
    run = _run(transport=transport)
    assert len(calls) == 1
    assert run.semantic_result is None
    assert run.final_run_status == "INVALID_RESPONSE"


def test_malformed_response_does_not_trigger_second_model_or_retry_call():
    transport = _FakeTransport([lambda request: {"review_status": "COMPLETED"}, _success_response])
    run = _run(transport=transport)
    assert len(transport.requests) == 1
    assert run.final_run_status == "INVALID_RESPONSE"


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_tokens", True),
        ("output_tokens", -1),
        ("cost_micro_usd", 1.5),
        ("cache_creation_input_tokens", False),
        ("cache_read_input_tokens", -1),
    ],
)
def test_provider_usage_and_cost_require_closed_integer_values(field, value):
    def response(request):
        values = _success_response(request)
        values[field] = value
        return values

    run = _run(transport=_FakeTransport([response]))
    assert run.final_run_status == "INVALID_RESPONSE"


def test_unavailable_usage_remains_unavailable_and_cache_miss_is_not_failure():
    def response(request):
        values = _success_response(request)
        values.update({
            "input_tokens": None,
            "output_tokens": None,
            "cache_creation_input_tokens": None,
            "cache_read_input_tokens": None,
            "usage_status": "UNAVAILABLE",
        })
        return values

    run = _run(transport=_FakeTransport([response]))
    assert run.final_run_status == "COMPLETED"
    record = run.execution_records[0]
    assert record.input_tokens is None
    assert record.output_tokens is None
    assert record.usage_status == "UNAVAILABLE"


def test_model_policy_mismatch_fails_before_transport():
    transport = _FakeTransport([_success_response])
    _expect_provider_error(
        _run,
        policy=_execution_policy(model_policy_id="unapproved-policy"),
        transport=transport,
    )
    assert transport.requests == []


def test_model_id_is_fixed_across_retry_and_provider_substitution_is_rejected():
    def substituted(request):
        values = _success_response(request)
        values["model_id"] = "provider-selected-other-model"
        return values

    run = _run(transport=_FakeTransport([substituted]))
    assert run.final_run_status == "INVALID_RESPONSE"


def test_execution_does_not_mutate_payload_policy_or_transport_response():
    payload = _payload()
    policy = _execution_policy()
    response = {}

    def response_for(request):
        response.update(_success_response(request))
        return response

    transport = _FakeTransport([response_for])
    run = _run(payload=payload, policy=policy, transport=transport)
    assert run.payload_sha256 == payload.payload_sha256
    assert response == _success_response(transport.requests[0])
    assert policy.model_id == MODEL_ID


def test_run_aggregate_requires_contiguous_attempts_and_one_payload():
    transport = _FakeTransport([lambda request: {
        "failure_class": "TRANSIENT_TRANSPORT",
        "failure_code": "TIMEOUT",
    }, _success_response])
    run = _run(transport=transport)
    assert [record.attempt_number for record in run.execution_records] == [1, 2]
    assert {record.payload_sha256 for record in run.execution_records} == {run.payload_sha256}
    assert {record.event_snapshot_id for record in run.execution_records} == {run.event_snapshot_id}
    assert run.total_attempts == 2
    assert run.total_retries == 1


def test_timeout_can_use_only_the_single_transient_retry():
    timeout = {"failure_class": "TRANSIENT_TRANSPORT", "failure_code": "TIMEOUT"}
    transport = _FakeTransport([timeout, _success_response])
    run = _run(transport=transport, policy=_execution_policy(timeout_seconds=7))
    assert run.final_run_status == "COMPLETED"
    assert all(request["timeout_seconds"] == 7 for request in transport.requests)


def test_cancellation_is_closed_non_fabricated_and_not_a_model_fallback():
    transport = _FakeTransport([{
        "failure_class": "PERMANENT_PROVIDER",
        "failure_code": "CANCELLED",
    }])
    run = _run(transport=transport)
    assert run.semantic_result is None
    assert run.final_run_status == "PERMANENT_FAILURE"
    assert len(transport.requests) == 1


def test_semantic_result_has_no_routing_publication_or_trading_authority():
    run = _run()
    fields = set(run.semantic_result.to_mapping())
    for forbidden in (
        "route", "routing_decision", "claude_model", "publication",
        "delivery", "side", "entry", "stop_loss", "take_profit", "order",
        "position", "account", "capital", "score",
    ):
        assert forbidden not in fields


def test_errors_are_sanitized_and_bounded():
    secret = "sk-test-secret-value"
    response = {
        "failure_class": "PERMANENT_PROVIDER",
        "failure_code": secret + " /full/article/body and /tmp/private/path",
    }
    with pytest.raises(provider.DeepSeekPrimaryReviewProviderError) as caught:
        _run(transport=_FakeTransport([response]))
    message = str(caught.value)
    assert secret not in message
    assert "/full/article/body" not in message
    assert "/tmp/private/path" not in message
    assert len(message) < 500


def test_input_permutation_and_repeated_execution_are_structurally_equal():
    first = _run()
    second = _run(payload=_payload())
    assert first == second
    assert first.logical_review_id == second.logical_review_id
    assert first.semantic_result.semantic_result_id == second.semantic_result.semantic_result_id


def test_provider_source_has_no_live_authority():
    source = inspect.getsource(provider)
    for forbidden in (
        "anthropic", "openai", "httpx", "requests", "aiohttp", "urllib.request",
        "socket", "os.environ", "getenv", "subprocess", "pathlib", "ccxt",
        "telegram", "datetime.now", "time.time", "random", "uuid",
        "MasterEngine", "production_signal", "paper_signal", "shadow_release",
        "routing", "adjudication", "publication", "trading",
    ):
        assert forbidden not in source.lower()


def test_no_real_transport_or_credentials_are_constructed_by_contract():
    source = inspect.getsource(provider.execute_deepseek_primary_review)
    for forbidden in (
        "api_key", "authorization", "http", "network", "credential", "os.environ",
        "client()", "requests.", "openai", "anthropic",
    ):
        assert forbidden not in source.lower()
