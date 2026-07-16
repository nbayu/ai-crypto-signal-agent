"""RED contract tests for the deterministic Claude escalation boundary."""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import datetime, timezone

import pytest

import engine.claude_escalated_review_provider_v1 as provider
from engine.ai_review_payload_projector_v1 import (
    AI_REVIEW_PAYLOAD_POLICY_VERSION,
    CLAUDE_PAYLOAD_VERSION,
    PayloadTokenPolicyV1,
    project_ai_review_payloads,
)
from engine.deterministic_escalation_router_v1 import (
    DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION,
    DeterministicEscalationDecisionV1,
)
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


UTC = timezone.utc
POLICY_VERSION = "claude-escalated-review-policy-v1"
EVENT_SNAPSHOT_ID = "a" * 64
OTHER_SNAPSHOT_ID = "b" * 64
PAYLOAD_SHA256 = "c" * 64
DECISION_ID = "d" * 64
AUTHORIZATION_ID = "e" * 64
L1_POLICY_ID = "fictional-claude-sonnet-policy-v1"
L2_POLICY_ID = "fictional-claude-opus-policy-v1"
L1_MODEL_ID = "fictional-claude-sonnet-model-v1"
L2_MODEL_ID = "fictional-claude-opus-model-v1"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_mapping(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _event(title: str = "Alpha protocol announced") -> NormalizedNewsEventV1:
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


def _source_policy() -> SourcePolicyDecisionV1:
    return SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1",
        decision="ELIGIBLE",
        primary_reason_code="SOURCE_ELIGIBLE",
        reason_codes=("SOURCE_ELIGIBLE",),
        evaluated_source_snapshot_ref={
            "source_namespace": "fictional-wire",
            "source_id": "source-001",
        },
        evaluation_timestamp_utc=datetime(2026, 7, 16, 12, 30, tzinfo=UTC),
        source_namespace="fictional-wire",
        source_id="source-001",
    )


def _mapping(event: NormalizedNewsEventV1):
    text = "Alpha protocol"
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha",
        entity_type="DIGITAL_ASSET",
        canonical_entity_id="asset:alpha",
        canonical_name="Alpha",
        canonical_symbol="ALPHA",
        source_text=text,
        source_text_sha256=_sha256_text(text),
        evidence_refs=(
            {
                "evidence_ref_id": "evidence-001",
                "event_snapshot_id": event.event_snapshot_id,
                "reference_type": "EVENT_FIELD",
                "field_name": "normalized_title",
            },
        ),
        confidence_basis="EXPLICIT_CALLER_ASSERTION",
        supplied_confidence=None,
        ambiguity_group_id=None,
        candidate_status="ACCEPTED",
        rejection_reason_codes=(),
        mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    return map_entity_candidates(
        event_snapshot_id=event.event_snapshot_id,
        source_policy_decision=_source_policy(),
        candidates=(candidate,),
    )


def _evidence(event_snapshot_id: str):
    excerpt = "Alpha protocol released a deterministic update."
    return (
        {
            "evidence_ref_id": "evidence-001",
            "event_snapshot_id": event_snapshot_id,
            "source_field": "normalized_body",
            "excerpt": excerpt,
            "excerpt_sha256": _sha256_text(excerpt),
        },
    )


def _payload(event: NormalizedNewsEventV1 | None = None):
    event = _event() if event is None else event
    token_policy = PayloadTokenPolicyV1(
        claude_input_hard_limit_tokens=8000,
        claude_target_input_min_tokens=2000,
        claude_target_input_max_tokens=5000,
        claude_output_hard_limit_tokens=1000,
        maximum_claude_logical_reviews_per_event=1,
        maximum_provider_attempts_per_review=2,
        maximum_retry_count=1,
    )
    return project_ai_review_payloads(
        normalized_event=event,
        source_policy_decision=_source_policy(),
        entity_mapping_result=_mapping(event),
        bounded_evidence=_evidence(event.event_snapshot_id),
        review_task="Resolve the bounded escalated review facts.",
        token_policy=token_policy,
        token_counter=lambda value: 100,
    ).claude_payload


def _decision(route: str = "L1", payload=None, **overrides):
    payload = _payload() if payload is None else payload
    model_policy = L1_POLICY_ID if route == "L1" else L2_POLICY_ID
    reasons = ("MODERATE_AMBIGUITY",) if route == "L1" else ("CRITICAL_AMBIGUITY",)
    values = {
        "policy_version": DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION,
        "event_snapshot_id": payload.event_snapshot_id,
        "deepseek_semantic_result_id": "f" * 64,
        "deepseek_payload_sha256": "1" * 64,
        "route": route,
        "route_name": "MODERATE_AMBIGUITY" if route == "L1" else "CRITICAL_AMBIGUITY",
        "claude_review_required": True,
        "claude_model_policy_id": model_policy,
        "reason_codes": reasons,
        "escalation_evidence_refs": ("evidence-001",),
        "decision_id": DECISION_ID,
    }
    values.update(overrides)
    decision = object.__new__(DeterministicEscalationDecisionV1)
    for name, value in values.items():
        object.__setattr__(decision, name, value)
    return decision


def _budget(route: str = "L1", **overrides):
    model_policy = L1_POLICY_ID if route == "L1" else L2_POLICY_ID
    values = {
        "authorization_id": AUTHORIZATION_ID,
        "policy_version": POLICY_VERSION,
        "event_snapshot_id": _payload().event_snapshot_id,
        "router_decision_id": DECISION_ID,
        "route": route,
        "model_policy_id": model_policy,
        "authorized": True,
        "maximum_authorized_cost_micro_usd": 5_000_000,
        "authorization_reason_code": "OWNER_APPROVED_TEST_BUDGET",
    }
    values.update(overrides)
    return provider.ClaudeBudgetAuthorizationV1(**values)


def _execution_policy(route: str = "L1", **overrides):
    model_policy = L1_POLICY_ID if route == "L1" else L2_POLICY_ID
    model_id = L1_MODEL_ID if route == "L1" else L2_MODEL_ID
    values = {
        "policy_version": POLICY_VERSION,
        "provider_name": "ANTHROPIC",
        "route": route,
        "model_policy_id": model_policy,
        "model_id": model_id,
        "maximum_logical_reviews_per_event": 1,
        "maximum_provider_attempts": 2,
        "maximum_retry_count": 1,
        "timeout_seconds": 30,
        "input_token_hard_limit": 8000,
        "target_input_token_minimum": 2000,
        "target_input_token_maximum": 5000,
        "output_token_hard_limit": 1000,
        "prompt_cache_mode": "EPHEMERAL",
        "prompt_cache_ttl_seconds": 300,
        "prompt_cache_breakpoint_count": 1,
        "budget_authorized": True,
        "maximum_authorized_cost_micro_usd": 5_000_000,
    }
    values.update(overrides)
    return provider.ClaudeExecutionPolicyV1(**values)


def _response(request, **overrides):
    values = {
        "policy_version": POLICY_VERSION,
        "event_snapshot_id": request["event_snapshot_id"],
        "request_payload_sha256": request["payload_sha256"],
        "router_decision_id": request["router_decision_id"],
        "logical_review_id": request["logical_review_id"],
        "route": request["route"],
        "model_policy_id": request["model_policy_id"],
        "review_status": "COMPLETED",
        "review_conclusion": "ESCALATED_REVIEW_COMPLETE",
        "ambiguity_resolution": "RESOLVED",
        "contradiction_resolution": "NONE",
        "evidence_assessment": "SUFFICIENT",
        "entity_assessment": "CONFIRMED",
        "source_assessment": "ACCEPTABLE",
        "material_risk_assessment": "NONE",
        "agreement_state_with_deepseek": "AGREES",
        "reason_codes": ("CLAUDE_REVIEW_COMPLETED",),
        "structured_explanation": "Bounded fictional escalation review.",
        "adjudication_evidence_refs": ("evidence-001",),
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


def _run(*, route="L1", payload=None, decision=None, execution_policy=None, budget=None, transport=None, **overrides):
    payload = _payload() if payload is None else payload
    decision = _decision(route, payload) if decision is None else decision
    execution_policy = _execution_policy(route) if execution_policy is None else execution_policy
    budget = (
        _budget(
            route,
            event_snapshot_id=decision.event_snapshot_id,
            router_decision_id=decision.decision_id,
            model_policy_id=decision.claude_model_policy_id,
        )
        if budget is None
        else budget
    )
    transport = _FakeTransport([_response]) if transport is None else transport
    values = {
        "payload": payload,
        "router_decision": decision,
        "execution_policy": execution_policy,
        "budget_authorization": budget,
        "transport": transport,
    }
    values.update(overrides)
    return provider.execute_claude_escalated_review(**values)


def _error(callable_object, *args, **kwargs):
    with pytest.raises(provider.ClaudeEscalatedReviewProviderError):
        callable_object(*args, **kwargs)


def test_public_api_and_constant_are_frozen():
    assert provider.CLAUDE_ESCALATED_REVIEW_POLICY_VERSION == POLICY_VERSION
    assert provider.__all__ == (
        "ClaudeEscalatedReviewProviderError",
        "CLAUDE_ESCALATED_REVIEW_POLICY_VERSION",
        "ClaudeBudgetAuthorizationV1",
        "ClaudeExecutionPolicyV1",
        "ClaudeEscalatedReviewResultV1",
        "ClaudeProviderExecutionRecordV1",
        "ClaudeEscalatedReviewRunV1",
        "execute_claude_escalated_review",
    )
    assert type(provider.__all__) is tuple
    assert len(set(provider.__all__)) == 8


def test_budget_authorization_is_closed_immutable_and_detached():
    authorization = _budget()
    assert authorization.authorized is True
    with pytest.raises((AttributeError, TypeError)):
        authorization.authorized = False
    _error(provider.ClaudeBudgetAuthorizationV1, **{
        **{name: getattr(authorization, name) for name in authorization.__dataclass_fields__},
        "unknown": True,
    })


@pytest.mark.parametrize("value", [True, False, 1.0, -1])
def test_budget_rejects_invalid_integer_cost(value):
    _error(_budget, maximum_authorized_cost_micro_usd=value)


@pytest.mark.parametrize("route", ["L0", "UNKNOWN", ""])
def test_budget_rejects_non_escalated_routes(route):
    _error(_budget, route=route)


def test_execution_policy_freezes_limits_and_cache_structure():
    policy = _execution_policy()
    assert policy.maximum_provider_attempts == 2
    assert policy.maximum_retry_count == 1
    assert policy.input_token_hard_limit == 8000
    assert policy.target_input_token_minimum == 2000
    assert policy.target_input_token_maximum == 5000
    assert policy.output_token_hard_limit == 1000
    assert policy.prompt_cache_mode == "EPHEMERAL"
    assert policy.prompt_cache_ttl_seconds == 300
    assert policy.prompt_cache_breakpoint_count == 1
    with pytest.raises((AttributeError, TypeError)):
        policy.model_id = "changed"


@pytest.mark.parametrize(
    "overrides",
    [
        {"route": "L0"},
        {"target_input_token_maximum": 8001},
        {"target_input_token_minimum": 5001},
        {"output_token_hard_limit": 1001},
        {"prompt_cache_ttl_seconds": 3600},
        {"prompt_cache_breakpoint_count": 2},
        {"prompt_cache_mode": "PERSISTENT"},
    ],
)
def test_execution_policy_rejects_invalid_limits(overrides):
    _error(_execution_policy, **overrides)


@pytest.mark.parametrize("bad", [None, {}, "payload", object()])
def test_exact_input_types_are_required(bad):
    _error(provider.execute_claude_escalated_review, bad, _decision(), _execution_policy(), _budget(), lambda _: {})


def test_l0_is_blocked_before_transport():
    transport = _FakeTransport([_response])
    decision = _decision("L0")
    _error(_run, decision=decision, execution_policy=_execution_policy("L1"), transport=transport)
    assert transport.requests == []


@pytest.mark.parametrize(
    ("route", "policy_id", "model_id"),
    [("L1", L1_POLICY_ID, L1_MODEL_ID), ("L2", L2_POLICY_ID, L2_MODEL_ID)],
)
def test_route_and_model_policy_binding(route, policy_id, model_id):
    execution = _execution_policy(route)
    budget = _budget(route)
    assert execution.model_policy_id == policy_id
    assert execution.model_id == model_id
    assert budget.model_policy_id == policy_id
    assert _decision(route).claude_model_policy_id == policy_id


@pytest.mark.parametrize(
    "kwargs",
    [
        {"execution_policy": _execution_policy("L2")},
        {"budget": _budget("L2")},
        {"decision": _decision("L2")},
        {"budget": _budget(event_snapshot_id=OTHER_SNAPSHOT_ID)},
    ],
)
def test_route_binding_mismatch_fails_before_transport(kwargs):
    transport = _FakeTransport([_response])
    _error(_run, transport=transport, **kwargs)
    assert transport.requests == []


def test_payload_snapshot_and_router_decision_binding_mismatch_fail_before_transport():
    payload = _payload(_event(title="Beta protocol announced"))
    transport = _FakeTransport([_response])
    _error(
        _run,
        payload=payload,
        decision=_decision(),
        transport=transport,
    )
    assert transport.requests == []


@pytest.mark.parametrize("estimate", [None, True, 1.5, -1])
def test_token_limit_authority_is_closed_before_transport(estimate):
    transport = _FakeTransport([_response])
    _error(_run, transport=transport, claude_input_estimate=estimate)
    assert transport.requests == []


def test_token_limit_authority_blocks_over_hard_limit_without_transport():
    transport = _FakeTransport([_response])
    run = _run(transport=transport, claude_input_estimate=8001)
    assert type(run) is provider.ClaudeEscalatedReviewRunV1
    assert run.final_run_status == "TOKEN_LIMIT_BLOCKED"
    assert run.total_attempts == 0
    assert run.total_retries == 0
    assert run.execution_records == ()
    assert run.semantic_result is None
    assert run.event_snapshot_id == _payload().event_snapshot_id
    assert run.payload_sha256 == _payload().payload_sha256
    assert run.router_decision_id == _decision().decision_id
    assert run.route == "L1"
    assert transport.requests == []


def test_token_limit_authority_accepts_exact_hard_boundary():
    transport = _FakeTransport([_response])
    run = _run(transport=transport, claude_input_estimate=8000)
    assert run.final_run_status == "COMPLETED"
    assert len(transport.requests) == 1


def test_cache_structure_is_stable_and_semantic_identity_excludes_cache_state():
    first = _FakeTransport([_response])
    second = _FakeTransport([_response])
    run_one = _run(transport=first)
    run_two = _run(transport=second)
    assert first.requests[0]["cache_control"] == second.requests[0]["cache_control"]
    assert run_one.semantic_result.semantic_result_id == run_two.semantic_result.semantic_result_id


def test_transport_must_be_callable_and_is_observable():
    _error(_run, transport=object())
    transport = _FakeTransport([_response])
    _run(transport=transport)
    assert len(transport.requests) == 1


def test_successful_l1_single_attempt():
    transport = _FakeTransport([_response])
    run = _run(transport=transport)
    assert run.final_run_status == "COMPLETED"
    assert run.total_attempts == 1
    assert run.total_retries == 0
    assert run.semantic_result.review_status == "COMPLETED"
    assert len(run.execution_records) == 1
    assert transport.requests[0]["attempt_number"] == 1


def test_successful_l2_single_attempt():
    transport = _FakeTransport([_response])
    run = _run(route="L2", transport=transport)
    assert run.final_run_status == "COMPLETED"
    assert run.semantic_result.route == "L2"
    assert run.semantic_result.model_policy_id == L2_POLICY_ID


def test_transient_failure_then_success_reuses_semantic_request():
    def transient(request):
        raise provider.ClaudeEscalatedReviewProviderError("transient")

    transport = _FakeTransport([transient, _response])
    run = _run(transport=transport)
    assert len(transport.requests) == 2
    assert run.final_run_status == "COMPLETED"
    assert run.total_retries == 1
    first, second = transport.requests
    for field in (
        "provider", "route", "model_id", "model_policy_id", "event_snapshot_id",
        "payload_version", "payload_sha256", "router_decision_id",
        "logical_review_id", "semantic_payload", "timeout_seconds",
        "output_token_limit", "cache_control",
    ):
        assert first[field] == second[field]
    assert (first["attempt_number"], second["attempt_number"]) == (1, 2)


def test_transient_failure_exhaustion_has_no_semantic_result():
    def transient(request):
        raise provider.ClaudeEscalatedReviewProviderError("temporary")

    transport = _FakeTransport([transient, transient])
    run = _run(transport=transport)
    assert len(transport.requests) == 2
    assert run.semantic_result is None
    assert run.final_run_status == "TRANSIENT_FAILURE"


@pytest.mark.parametrize("failure", ["AUTHENTICATION_FAILURE", "PERMISSION_DENIED", "UNSUPPORTED_MODEL"])
def test_non_retryable_provider_failures_do_not_retry(failure):
    transport = _FakeTransport([{"failure_code": failure}])
    run = _run(transport=transport)
    assert len(transport.requests) == 1
    assert run.semantic_result is None


@pytest.mark.parametrize("authorized", [False])
def test_budget_denial_precedes_transport(authorized):
    transport = _FakeTransport([_response])
    budget = _budget(authorized=authorized)
    run = _run(budget=budget, transport=transport)
    assert type(run) is provider.ClaudeEscalatedReviewRunV1
    assert run.final_run_status == "BUDGET_BLOCKED"
    assert run.total_attempts == 0
    assert run.total_retries == 0
    assert run.execution_records == ()
    assert run.semantic_result is None
    assert run.event_snapshot_id == _payload().event_snapshot_id
    assert run.payload_sha256 == _payload().payload_sha256
    assert run.router_decision_id == _decision().decision_id
    assert run.route == "L1"
    assert transport.requests == []


def test_budget_authorization_rejects_non_boolean_authorized_during_construction():
    with pytest.raises(provider.ClaudeEscalatedReviewProviderError):
        _budget(authorized=None)


def test_semantic_result_is_closed_and_telemetry_free():
    transport = _FakeTransport([_response])
    run = _run(transport=transport)
    fields = set(run.semantic_result.__dataclass_fields__)
    forbidden = {
        "request_id", "attempt_number", "retry_count", "input_tokens", "output_tokens",
        "cache_hit", "cache_miss", "cost_micro_usd", "duration_ms", "publication",
        "trading", "adjudication_outcome",
    }
    assert fields.isdisjoint(forbidden)


def test_execution_record_is_separate_from_semantic_result():
    run = _run()
    assert type(run.execution_records[0]) is provider.ClaudeProviderExecutionRecordV1
    assert run.semantic_result is not run.execution_records[0]


def test_run_aggregate_is_immutable_and_closed():
    run = _run()
    with pytest.raises((AttributeError, TypeError)):
        run.final_run_status = "TRANSIENT_FAILURE"
    _error(provider.ClaudeEscalatedReviewRunV1, **{
        **{name: getattr(run, name) for name in run.__dataclass_fields__},
        "unknown": True,
    })


def test_provider_source_has_no_external_execution_authority():
    source = inspect.getsource(provider)
    for forbidden in (
        "anthropic", "openai", "httpx", "requests", "aiohttp", "urllib.request",
        "socket", "os.environ", "getenv", "subprocess", "pathlib", "random", "secrets",
        "uuid", "MasterEngine", "publication", "trading", "account", "capital",
    ):
        assert forbidden not in source


def test_errors_are_bounded_and_do_not_retain_payload_text():
    secret = "sk-test-secret-value"
    with pytest.raises(provider.ClaudeEscalatedReviewProviderError) as caught:
        _run(budget=_budget(authorization_reason_code=secret))
    message = str(caught.value)
    assert secret not in message
    assert len(message) < 200
