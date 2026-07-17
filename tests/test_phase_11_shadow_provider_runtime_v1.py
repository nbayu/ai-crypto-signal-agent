"""RED contract for the bounded injected Phase 11 provider runtime."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from engine.ai_review_payload_projector_v1 import (
    ClaudeReviewPayloadV1,
    DeepSeekReviewPayloadV1,
    PayloadTokenPolicyV1,
    project_ai_review_payloads,
)
from engine.news_entity_mapping_v1 import (
    ENTITY_MAPPING_POLICY_VERSION,
    EntityCandidateV1,
    map_entity_candidates,
)
from engine.news_event_contract_v1 import EVENT_SCHEMA_VERSION, NormalizedNewsEventV1
from engine.news_source_policy_v1 import SourcePolicyDecisionV1
from engine.phase_11_budget_control_v1 import (
    BudgetLedgerV1,
    BudgetReservationV1,
    Phase11BudgetPolicyV1,
    ProviderUsageRecordV1,
)
from engine.phase_11_shadow_input_contracts_v1 import (
    ApprovedNewsCaptureV1,
    Phase09ControlProjectionV1,
    ShadowEvaluationInputV1,
)
from engine.phase_11_shadow_provider_runtime_v1 import (
    ShadowProviderInvocationResultV1,
    ShadowProviderInvocationV1,
    ShadowProviderRuntimeV1,
)


UTC = timezone.utc
PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
MODELS = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
PROOF = "PROVEN_NONE"
FAILURES = (
    "NONE", "VALIDATION_FAILURE", "UNAUTHORIZED_INVOCATION", "BUDGET_DENIED",
    "RESERVATION_EXPIRED", "HARD_STOP_ACTIVE", "CIRCUIT_OPEN", "TIMEOUT",
    "TRANSPORT_FAILURE", "PROVIDER_UNAVAILABLE", "MALFORMED_RESPONSE",
    "SCHEMA_MISMATCH", "IDENTITY_MISMATCH", "USAGE_EXCEEDS_RESERVATION",
    "UNCERTAIN_TRANSPORT_OUTCOME", "RECONCILIATION_REQUIRED",
)


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reject(factory, **values):
    with pytest.raises((TypeError, ValueError)):
        factory(**values)


def _event():
    return NormalizedNewsEventV1(
        event_namespace="news", authoritative_source_namespace="fixture-wire",
        authoritative_source_event_id="source-event-001", deterministic_source_key=None,
        normalized_primary_subject="asset:alpha", canonical_event_class="PROTOCOL_UPDATE",
        normalized_title="Alpha protocol announced", normalized_body="Alpha protocol released a deterministic update.",
        normalized_language="en-US", publication_timestamp_utc=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
        point_in_time_timestamp_utc=datetime(2026, 7, 16, 12, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fixture-publisher"}, previous_event_version_id=None,
        event_version_number=1, source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        schema_version=EVENT_SCHEMA_VERSION,
    )


def _source_policy():
    return SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1", decision="ELIGIBLE", primary_reason_code="SOURCE_ELIGIBLE",
        reason_codes=("SOURCE_ELIGIBLE",), evaluated_source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        evaluation_timestamp_utc=datetime(2026, 7, 16, 12, 30, tzinfo=UTC), source_namespace="fixture-wire", source_id="source-001",
    )


def _payloads():
    event = _event()
    source_policy = _source_policy()
    excerpt = "Alpha protocol released a deterministic update."
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha", entity_type="DIGITAL_ASSET", canonical_entity_id="asset:alpha",
        canonical_name="Alpha", canonical_symbol="ALPHA", source_text="Alpha protocol",
        source_text_sha256=_text_hash("Alpha protocol"),
        evidence_refs=[{"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "reference_type": "EVENT_FIELD", "field_name": "normalized_title"}],
        confidence_basis="EXPLICIT_CALLER_ASSERTION", supplied_confidence=None, ambiguity_group_id=None,
        candidate_status="ACCEPTED", rejection_reason_codes=[], mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    mapping = map_entity_candidates(event_snapshot_id=event.event_snapshot_id, source_policy_decision=source_policy, candidates=[candidate])
    token_policy = PayloadTokenPolicyV1(
        claude_input_hard_limit_tokens=8000, claude_target_input_min_tokens=2000,
        claude_target_input_max_tokens=5000, claude_output_hard_limit_tokens=1000,
        maximum_claude_logical_reviews_per_event=1, maximum_provider_attempts_per_review=2,
        maximum_retry_count=1,
    )
    projected = project_ai_review_payloads(
        normalized_event=event, source_policy_decision=source_policy, entity_mapping_result=mapping,
        bounded_evidence=({"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "source_field": "normalized_body", "excerpt": excerpt, "excerpt_sha256": _text_hash(excerpt)},),
        review_task="Assess bounded canonical facts.", token_policy=token_policy, token_counter=lambda _: 100,
    )
    return event, projected.deepseek_payload, projected.claude_payload


def _shadow_input(event_id):
    payload = {"event_class": "CLEAN_ROUTINE", "headline": "Provider boundary fixture"}
    capture_values = {
        "schema_version": "approved-news-capture-v1", "event_id": event_id, "event_version": 1,
        "source_id": "source-001", "source_type": "REGULATED_FEED", "source_timestamp": "2026-07-17T00:00:00Z",
        "captured_at": "2026-07-17T00:01:00Z", "point_in_time_cutoff": "2026-07-17T00:02:00Z",
        "normalized_payload": payload, "normalized_payload_hash": _sha(payload),
        "event_lineage": ({"event_id": event_id, "event_version": 1, "relation": "ORIGIN"},),
        "capture_classification": "FIXTURE", "content_origin": "SYNTHETIC_FIXTURE", "evidence_refs": ("evidence-001",),
    }
    capture = ApprovedNewsCaptureV1(**capture_values, capture_id=_sha({k: v for k, v in capture_values.items() if k not in {"capture_id", "normalized_payload_hash"}}))
    projection = Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1", projection_id="projection-001", production_evaluation_id="evaluation-001",
        event_id=event_id, candidate_id="candidate-001", disposition="NO_TRADE", reason_codes=("NO_ELIGIBLE_SETUP",),
        evidence_refs=("control-evidence-001",), evaluated_at="2026-07-17T00:03:00Z", source_artifact_hash="1" * 64,
    )
    return ShadowEvaluationInputV1(
        schema_version="shadow-evaluation-input-v1", shadow_input_id="shadow-input-001", approved_news_capture=capture,
        phase_09_control_projection=projection, sample_plan_id="sample-plan-001", policy_version="phase11-policy-v1", created_at="2026-07-17T00:04:00Z",
    )


def _policy(**overrides):
    values = {
        "schema_version": "phase11-budget-policy-v1", "policy_id": "budget-policy-001", "policy_version": 1,
        "status": "ACTIVE", "currency": "USD_MICRO", "total_cost_cap": Decimal("1000000"),
        "provider_cost_caps": {"DEEPSEEK": Decimal("500000"), "ANTHROPIC": Decimal("500000")},
        "model_cost_caps": {"DEEPSEEK_PRIMARY": Decimal("500000"), "CLAUDE_SONNET_L1": Decimal("300000"), "CLAUDE_OPUS_L2": Decimal("300000")},
        "per_run_cost_cap": Decimal("100000"), "maximum_call_count": 100, "maximum_calls_per_run": 10,
        "maximum_input_tokens": 100000, "maximum_output_tokens": 100000, "maximum_tokens_per_call": 10000,
        "allowed_providers": PROVIDERS, "allowed_models": MODELS, "starts_at": "2026-07-17T00:00:00Z",
        "ends_at": "2026-07-18T00:00:00Z", "owner_approval_reference": "owner-approval-001",
        "stop_conditions": ("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    }
    values.update(overrides)
    return Phase11BudgetPolicyV1(**values)


def _reservation(policy, provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", call_id="call-001", **overrides):
    values = {
        "schema_version": "phase11-budget-reservation-v1", "reservation_id": f"reservation-{call_id}", "policy_id": policy.policy_id,
        "run_id": "run-001", "call_id": call_id, "provider": provider, "model": model, "reserved_cost": Decimal("1000"),
        "reserved_input_tokens": 100, "reserved_output_tokens": 200, "reserved_at": "2026-07-17T00:05:00Z",
        "expires_at": "2026-07-17T02:00:00Z", "status": "RESERVED", "reason_codes": ("ROUTE_RESERVATION",),
    }
    values.update(overrides)
    return BudgetReservationV1(**values)


def _ledger(policy, reservations=(), state="OPEN"):
    result = BudgetLedgerV1(policy=policy, circuit_or_stop_state=state)
    for reservation in reservations:
        result = result.reserve_call(reservation)
    return result


def _usage(reservation, *, request_hash=None, actual=Decimal("850"), outcome="SUCCESS", reconciliation="RESOLVED", failure="NONE", **overrides):
    values = {
        "schema_version": "phase11-provider-usage-v1", "usage_record_id": f"usage-{reservation.call_id}",
        "reservation_id": reservation.reservation_id, "policy_id": reservation.policy_id, "run_id": reservation.run_id,
        "call_id": reservation.call_id, "provider": reservation.provider, "model": reservation.model,
        "request_hash": _text_hash("request") if request_hash is None else request_hash, "response_hash": _text_hash("response"), "input_tokens": 80,
        "output_tokens": 120, "estimated_cost": Decimal("900"), "actual_cost": actual,
        "started_at": "2026-07-17T00:06:00Z", "completed_at": "2026-07-17T00:06:01Z", "latency_ms": 1000,
        "attempt_count": 1, "outcome": outcome, "reconciliation_status": reconciliation, "failure_class": failure,
        "reason_codes": ("COMPLETED",),
    }
    values.update(overrides)
    return ProviderUsageRecordV1(**values)


def _uncertain_usage(reservation, request_hash):
    return _usage(
        reservation, request_hash=request_hash, actual=None, outcome="TRANSPORT_FAILURE", reconciliation="RECONCILIATION_REQUIRED",
        failure="UNCERTAIN_TRANSPORT_OUTCOME", response_hash=_text_hash("unresolved-response"), reason_codes=("TRANSPORT_UNCERTAIN",),
    )


def _context(provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", route="L0", retry=False):
    event, deepseek, claude = _payloads()
    policy = _policy()
    first = _reservation(policy, provider, model, "call-001-attempt-1" if retry else "call-001")
    attempts = (first,)
    if retry:
        second = _reservation(policy, provider, model, "call-001-attempt-2")
        attempts += (second,)
    ledger = _ledger(policy, attempts)
    request = deepseek if provider == "DEEPSEEK" else claude
    return {"event": event, "shadow_input": _shadow_input(event.event_snapshot_id), "policy": policy,
            "ledger": ledger, "reservation": first, "attempt_reservations": attempts, "request": request,
            "route": route}


def _invocation_values(context=None, **overrides):
    context = _context() if context is None else context
    reservation, request, ledger = context["reservation"], context["request"], context["ledger"]
    values = {
        "schema_version": "phase11-shadow-provider-invocation-v1", "invocation_id": None, "execution_id": "execution-001",
        "run_id": reservation.run_id, "call_id": reservation.call_id, "route": context["route"], "provider": reservation.provider,
        "model": reservation.model, "prompt_version": "phase11-prompt-v1", "provider_review_schema_version": "phase10-review-schema-v1",
        "shadow_input": context["shadow_input"], "shadow_input_identity": context["shadow_input"].identity,
        "event_id": context["event"].event_snapshot_id, "event_version": 1, "budget_ledger": ledger,
        "budget_policy_id": ledger.policy.policy_id, "reservation": reservation, "reservation_id": reservation.identity,
        "attempt_reservations": context["attempt_reservations"], "review_request": request, "request_hash": request.payload_sha256,
        "timeout_ms": 1000, "maximum_attempts": len(context["attempt_reservations"]), "circuit_state": "CLOSED",
        "requested_at": "2026-07-17T00:05:30Z", "reason_codes": ("ROUTE_REQUIRED",), "production_effect": "NONE",
        "zero_production_effect_proof": PROOF,
    }
    values.update(overrides)
    return values


def _invocation(context=None, **overrides):
    return ShadowProviderInvocationV1(**_invocation_values(context, **overrides))


class _FakeTransport:
    def __init__(self, outcomes):
        self.outcomes, self.calls = list(outcomes), []

    def __call__(self, request, timeout_ms):
        self.calls.append((request, timeout_ms))
        return self.outcomes.pop(0)


def _result_values(context=None, usage=None, **overrides):
    context = _context() if context is None else context
    invocation = overrides.pop("invocation", _invocation(context))
    usage = _usage(invocation.reservation, request_hash=invocation.request_hash) if usage is None else usage
    values = {
        "schema_version": "phase11-shadow-provider-invocation-result-v1", "result_id": None, "invocation": invocation,
        "invocation_id": invocation.identity, "status": "SUCCEEDED", "provider": invocation.provider, "model": invocation.model,
        "request_hash": invocation.request_hash, "response_hash": usage.response_hash, "provider_review_identity": "c" * 64,
        "reserved_cost": invocation.reservation.reserved_cost, "estimated_cost": usage.estimated_cost, "actual_cost": usage.actual_cost,
        "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "started_at": usage.started_at,
        "completed_at": usage.completed_at, "latency_ms": usage.latency_ms, "attempt_count": usage.attempt_count,
        "timeout_state": "NONE", "retry_state": "NO_RETRY", "circuit_state": "CLOSED", "transport_outcome": "SUCCESS",
        "failure_class": "NONE", "reconciliation_state": usage.reconciliation_status, "usage_record": usage,
        "reason_codes": ("COMPLETED",), "production_effect": "NONE", "zero_production_effect_proof": PROOF,
    }
    values.update(overrides)
    return values


def _result(context=None, usage=None, **overrides):
    return ShadowProviderInvocationResultV1(**_result_values(context, usage, **overrides))


class TestInvocationContract:
    def test_real_phase10_request_instances_and_hashes_bind_the_active_ledger(self):
        for provider, model, route, request_type in (("DEEPSEEK", "DEEPSEEK_PRIMARY", "L0", DeepSeekReviewPayloadV1), ("ANTHROPIC", "CLAUDE_SONNET_L1", "L1", ClaudeReviewPayloadV1), ("ANTHROPIC", "CLAUDE_OPUS_L2", "L2", ClaudeReviewPayloadV1)):
            context = _context(provider, model, route)
            value = _invocation(context)
            assert type(value.review_request) is request_type
            assert value.request_hash == value.review_request.payload_sha256
            assert value.budget_ledger.policy.status == "ACTIVE"
            assert value.budget_ledger.policy.owner_approval_reference
            assert value.reservation in value.budget_ledger.reservations
        with pytest.raises((AttributeError, TypeError)):
            _invocation().route = "L1"

    def test_invocation_rejects_opaque_or_unrelated_authority_evidence(self):
        context = _context()
        _reject(ShadowProviderInvocationV1, **_invocation_values(context, review_request=DeepSeekReviewPayloadV1))
        _reject(ShadowProviderInvocationV1, **_invocation_values(context, request_hash=_text_hash("forged")))
        _reject(ShadowProviderInvocationV1, **_invocation_values(context, budget_policy_id="other-policy"))
        absent = _ledger(context["policy"])
        _reject(ShadowProviderInvocationV1, **_invocation_values(context, budget_ledger=absent))
        stopped = context["ledger"].activate_hard_stop("TOTAL_CAP_HARD_STOP")
        _reject(ShadowProviderInvocationV1, **_invocation_values(context, budget_ledger=stopped))
        draft_policy = _policy(status="DRAFT", owner_approval_reference=None)
        draft_reservation = _reservation(draft_policy)
        draft_ledger = _ledger(draft_policy, (draft_reservation,))
        _reject(ShadowProviderInvocationV1, **_invocation_values(
            context, budget_ledger=draft_ledger, budget_policy_id=draft_policy.policy_id,
            reservation=draft_reservation, reservation_id=draft_reservation.identity,
            attempt_reservations=(draft_reservation,), run_id=draft_reservation.run_id,
            call_id=draft_reservation.call_id, provider=draft_reservation.provider, model=draft_reservation.model,
        ))

    def test_l0_rejects_claude_and_l1_to_l2_uses_distinct_ordered_reservations(self):
        claude = _context("ANTHROPIC", "CLAUDE_SONNET_L1", "L0")
        _reject(ShadowProviderInvocationV1, **_invocation_values(claude))
        sonnet = _context("ANTHROPIC", "CLAUDE_SONNET_L1", "L1")
        opus = _context("ANTHROPIC", "CLAUDE_OPUS_L2", "L1_TO_L2")
        first, second = sonnet["reservation"], opus["reservation"]
        assert first.reservation_id != second.reservation_id
        assert first.model == "CLAUDE_SONNET_L1" and second.model == "CLAUDE_OPUS_L2"

    def test_retry_requires_two_distinct_ledger_reservations(self):
        context = _context(retry=True)
        value = _invocation(context)
        assert tuple(item.reservation_id for item in value.attempt_reservations) == tuple(item.reservation_id for item in context["attempt_reservations"])
        assert len({item.reservation_id for item in value.attempt_reservations}) == 2
        _reject(ShadowProviderInvocationV1, **_invocation_values(context, attempt_reservations=(context["reservation"],), maximum_attempts=2))


class TestRuntimeBoundary:
    def test_denials_do_not_call_transport(self):
        context = _context()
        transport = _FakeTransport([{"outcome": "SUCCESS"}])
        denied = _invocation(context, circuit_state="OPEN")
        result = ShadowProviderRuntimeV1(transport=transport).invoke(denied)
        assert transport.calls == [] and result.failure_class == "CIRCUIT_OPEN"

    def test_transport_is_injected_sanitized_and_explicitly_timed(self):
        transport = _FakeTransport([{"outcome": "SUCCESS"}])
        ShadowProviderRuntimeV1(transport=transport).invoke(_invocation())
        request, timeout = transport.calls[0]
        assert timeout == 1000
        assert set(request).isdisjoint({"api_key", "credential", "authorization_header", "bearer_token"})
        assert "budget_ledger" not in request and "shadow_input" not in request

    def test_retry_maps_each_attempt_to_one_distinct_reservation(self):
        context = _context(retry=True)
        transport = _FakeTransport([{"outcome": "TIMEOUT"}, {"outcome": "TIMEOUT"}])
        result = ShadowProviderRuntimeV1(transport=transport).invoke(_invocation(context))
        assert result.attempt_count == 2
        assert len(transport.calls) == 2
        assert tuple(result.attempt_reservation_ids) == tuple(item.identity for item in context["attempt_reservations"])

    @pytest.mark.parametrize("outcome", ["MALFORMED_RESPONSE", "SCHEMA_MISMATCH", "PROVIDER_UNAVAILABLE"])
    def test_nonretryable_provider_evidence_fails_closed(self, outcome):
        transport = _FakeTransport([{"outcome": outcome}])
        result = ShadowProviderRuntimeV1(transport=transport).invoke(_invocation())
        assert result.status != "SUCCEEDED" and result.provider_review_identity is None


class TestResultContract:
    def test_success_result_is_immutable_and_exactly_matches_child_usage(self):
        result = _result()
        assert result.actual_cost == result.usage_record.actual_cost == Decimal("850")
        assert result.estimated_cost == result.usage_record.estimated_cost
        with pytest.raises((AttributeError, TypeError)):
            result.actual_cost = Decimal("0")

    def test_uncertain_parent_requires_matching_conservative_child_usage(self):
        context = _context()
        request_hash = _invocation(context).request_hash
        uncertain = _uncertain_usage(context["reservation"], request_hash)
        result = _result(context, uncertain, status="FAILED", response_hash=uncertain.response_hash, provider_review_identity=None,
                         actual_cost=None, transport_outcome="UNCERTAIN_TRANSPORT_OUTCOME", failure_class="UNCERTAIN_TRANSPORT_OUTCOME",
                         reconciliation_state="RECONCILIATION_REQUIRED")
        assert result.usage_record.reconciliation_status == result.reconciliation_state
        resolved = _usage(context["reservation"], request_hash=request_hash)
        _reject(ShadowProviderInvocationResultV1, **_result_values(context, resolved, status="FAILED", provider_review_identity=None,
                 transport_outcome="UNCERTAIN_TRANSPORT_OUTCOME", failure_class="UNCERTAIN_TRANSPORT_OUTCOME", reconciliation_state="RECONCILIATION_REQUIRED"))

    def test_cost_divergence_uses_complete_matching_child_evidence(self):
        context = _context()
        baseline = _result(context)
        alternate_usage = _usage(context["reservation"], request_hash=_invocation(context).request_hash, actual=Decimal("851"))
        alternate = _result(context, alternate_usage, actual_cost=Decimal("851"))
        assert alternate.actual_cost == alternate.usage_record.actual_cost == Decimal("851")
        assert alternate.identity != baseline.identity
        _reject(ShadowProviderInvocationResultV1, **_result_values(context, _usage(context["reservation"], request_hash=_invocation(context).request_hash), actual_cost=Decimal("851")))

    @pytest.mark.parametrize("field,value", [("estimated_cost", 0.0), ("actual_cost", Decimal("-0.01")), ("failure_class", "UNKNOWN"), ("production_effect", "TRADE")])
    def test_result_rejects_noncanonical_money_and_authority(self, field, value):
        _reject(ShadowProviderInvocationResultV1, **_result_values(**{field: value}))


def test_future_module_static_boundary_uses_exact_semantic_authority_names():
    path = Path(__file__).parents[1] / "engine" / "phase_11_shadow_provider_runtime_v1.py"
    if not path.exists():
        pytest.skip("RED suite: implementation module is intentionally absent")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_imports = {"requests", "httpx", "urllib", "socket", "subprocess", "dotenv", "telegram", "ccxt"}
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not imported & forbidden_imports
    forbidden = {"position", "positions", "open_position", "account", "balance", "capital", "exchange", "order", "trading", "publication", "telegram_client", "api_key", "credential", "bearer_token", "authorization_header"}
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    identifiers |= {node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)}
    identifiers |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not identifiers & forbidden
    allowed_identifiers = {
        node.arg for node in ast.walk(ast.parse("def fixture(disposition, input_tokens, output_tokens, token_limit): pass"))
        if isinstance(node, ast.arg)
    }
    forbidden_identifiers = {
        node.arg for node in ast.walk(ast.parse("def fixture(position): pass")) if isinstance(node, ast.arg)
    }
    assert not allowed_identifiers & forbidden
    assert forbidden_identifiers & forbidden == {"position"}
