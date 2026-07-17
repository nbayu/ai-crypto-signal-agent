"""RED contract for deterministic Phase 11 shadow finalization."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from engine.ai_review_payload_projector_v1 import (
    PayloadTokenPolicyV1,
    project_ai_review_payloads,
)
from engine.claude_escalated_review_provider_v1 import ClaudeEscalatedReviewResultV1
from engine.deepseek_primary_review_provider_v1 import DeepSeekPrimaryReviewResultV1
from engine.deterministic_adjudication_v1 import (
    DeterministicAdjudicationPolicyV1,
    DeterministicAdjudicationResultV1,
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
from engine.news_event_contract_v1 import EVENT_SCHEMA_VERSION, NormalizedNewsEventV1
from engine.news_source_policy_v1 import SourcePolicyDecisionV1
from engine.phase_11_budget_control_v1 import (
    BudgetLedgerV1,
    BudgetReservationV1,
    Phase11BudgetPolicyV1,
    ProviderUsageRecordV1,
)
from engine.phase_11_finalization_evidence_bridge_v1 import (
    ShadowAdjudicationEvidenceBundleV1,
    ShadowAdjudicationRouteLineageV1,
    ShadowTerminalAdjudicationStateV1,
    ShadowTerminalExecutionRecordV1,
    ShadowTypedProviderReviewEvidenceV1,
)
from engine.phase_11_shadow_input_contracts_v1 import (
    ApprovedNewsCaptureV1,
    Phase09ControlProjectionV1,
    ShadowEvaluationInputV1,
)
from engine.phase_11_shadow_provider_runtime_v1 import (
    ShadowProviderInvocationResultV1,
    ShadowProviderInvocationV1,
)
from engine.phase_11_shadow_run_orchestrator_v1 import (
    ShadowProviderRunPlanV1,
    ShadowProviderRunResultV1,
    ShadowRunCallPlanV1,
)
from engine.phase_11_shadow_adjudication_finalizer_v1 import (
    ShadowAdjudicationFinalizationFailureV1,
    ShadowAdjudicationFinalizationPathV1,
    ShadowAdjudicationFinalizationPlanV1,
    ShadowAdjudicationFinalizationResultV1,
    ShadowAdjudicationFinalizerV1,
    ShadowAdjudicationFinalizerValidationError,
    ShadowAdjudicationFinalizationStatusV1,
    canonical_json_bytes,
    lowercase_sha256,
)


def _sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _payloads():
    event = NormalizedNewsEventV1(
        event_namespace="news", authoritative_source_namespace="fixture-wire",
        authoritative_source_event_id="finalizer-event-001", deterministic_source_key=None,
        normalized_primary_subject="asset:alpha", canonical_event_class="PROTOCOL_UPDATE",
        normalized_title="Alpha protocol announced", normalized_body="Alpha deterministic update.",
        normalized_language="en-US", publication_timestamp_utc=datetime(2026, 7, 17, tzinfo=UTC),
        point_in_time_timestamp_utc=datetime(2026, 7, 17, 0, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fixture-publisher"}, previous_event_version_id=None,
        event_version_number=1, source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        schema_version=EVENT_SCHEMA_VERSION,
    )
    decision = SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1", decision="ELIGIBLE", primary_reason_code="SOURCE_ELIGIBLE",
        reason_codes=("SOURCE_ELIGIBLE",), evaluated_source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        evaluation_timestamp_utc=datetime(2026, 7, 17, 0, 2, 30, tzinfo=UTC), source_namespace="fixture-wire", source_id="source-001",
    )
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha", entity_type="DIGITAL_ASSET", canonical_entity_id="asset:alpha", canonical_name="Alpha", canonical_symbol="ALPHA",
        source_text="Alpha protocol", source_text_sha256=_text_hash("Alpha protocol"),
        evidence_refs=[{"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "reference_type": "EVENT_FIELD", "field_name": "normalized_title"}],
        confidence_basis="EXPLICIT_CALLER_ASSERTION", supplied_confidence=None, ambiguity_group_id=None, candidate_status="ACCEPTED",
        rejection_reason_codes=[], mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    mapped = map_entity_candidates(event_snapshot_id=event.event_snapshot_id, source_policy_decision=decision, candidates=[candidate])
    projected = project_ai_review_payloads(
        normalized_event=event, source_policy_decision=decision, entity_mapping_result=mapped,
        bounded_evidence=({"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "source_field": "normalized_body", "excerpt": "Alpha deterministic update.", "excerpt_sha256": _text_hash("Alpha deterministic update.")},),
        review_task="Assess bounded canonical facts.", token_policy=PayloadTokenPolicyV1(
            claude_input_hard_limit_tokens=8000, claude_target_input_min_tokens=2000, claude_target_input_max_tokens=5000,
            claude_output_hard_limit_tokens=1000, maximum_claude_logical_reviews_per_event=1, maximum_provider_attempts_per_review=2,
            maximum_retry_count=1,
        ), token_counter=lambda _: 100,
    )
    return event, projected.deepseek_payload, projected.claude_payload


def _shadow_input(event):
    payload = {"headline": "Finalizer fixture"}
    capture = ApprovedNewsCaptureV1(
        schema_version="approved-news-capture-v1", event_id=event.event_snapshot_id, event_version=1, source_id="source-001", source_type="REGULATED_FEED",
        source_timestamp="2026-07-17T00:00:00Z", captured_at="2026-07-17T00:01:00Z", point_in_time_cutoff="2026-07-17T00:02:00Z",
        normalized_payload=payload, normalized_payload_hash=_sha(payload), event_lineage=({"event_id": event.event_snapshot_id, "event_version": 1, "relation": "ORIGIN"},),
        capture_classification="FIXTURE", content_origin="SYNTHETIC_FIXTURE", evidence_refs=("evidence-001",),
        capture_id=_sha({"schema_version": "approved-news-capture-v1", "event_id": event.event_snapshot_id, "event_version": 1, "source_id": "source-001", "source_type": "REGULATED_FEED", "source_timestamp": "2026-07-17T00:00:00Z", "captured_at": "2026-07-17T00:01:00Z", "point_in_time_cutoff": "2026-07-17T00:02:00Z", "normalized_payload": payload, "event_lineage": ({"event_id": event.event_snapshot_id, "event_version": 1, "relation": "ORIGIN"},), "capture_classification": "FIXTURE", "content_origin": "SYNTHETIC_FIXTURE", "evidence_refs": ("evidence-001",)}),
    )
    control = Phase09ControlProjectionV1(schema_version="phase09-control-projection-v1", projection_id="projection-001", production_evaluation_id="evaluation-001", event_id=event.event_snapshot_id, candidate_id="candidate-001", disposition="NO_TRADE", reason_codes=("NO_ELIGIBLE_SETUP",), evidence_refs=("control-evidence-001",), evaluated_at="2026-07-17T00:03:00Z", source_artifact_hash="1" * 64)
    return ShadowEvaluationInputV1(schema_version="shadow-evaluation-input-v1", shadow_input_id="shadow-input-001", approved_news_capture=capture, phase_09_control_projection=control, sample_plan_id="sample-plan-001", policy_version="phase11-policy-v1", created_at="2026-07-17T00:04:00Z")


def _policy():
    return Phase11BudgetPolicyV1(
        schema_version="phase11-budget-policy-v1", policy_id="budget-policy-001", policy_version=1, status="ACTIVE", currency="USD_MICRO", total_cost_cap=Decimal("10000000"),
        provider_cost_caps={"DEEPSEEK": Decimal("5000000"), "ANTHROPIC": Decimal("5000000")}, model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("5000000"), "CLAUDE_SONNET_L1": Decimal("3000000"), "CLAUDE_OPUS_L2": Decimal("3000000")},
        per_run_cost_cap=Decimal("5000000"), maximum_call_count=100, maximum_calls_per_run=10, maximum_input_tokens=100000, maximum_output_tokens=100000, maximum_tokens_per_call=10000,
        allowed_providers=("DEEPSEEK", "ANTHROPIC"), allowed_models=("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2"), starts_at="2026-07-17T00:00:00Z", ends_at="2026-07-18T00:00:00Z", owner_approval_reference="owner-approval-001", stop_conditions=("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    )


_GRAPH = {
    "L0": (("L0", "DEEPSEEK", "DEEPSEEK_PRIMARY"),),
    "L1": (("L1", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1")),
    "L2": (("L2", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L2", "ANTHROPIC", "CLAUDE_OPUS_L2")),
    "L1_TO_L2": (("L1", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1"), ("L1_TO_L2", "ANTHROPIC", "CLAUDE_OPUS_L2")),
}


def _semantic_deepseek(event_id, request_hash):
    return DeepSeekPrimaryReviewResultV1(policy_version="deepseek-primary-review-policy-v1", event_snapshot_id=event_id, request_payload_sha256=request_hash, logical_review_id="a" * 64, review_status="COMPLETED", review_conclusion="FACTUAL_REVIEW_COMPLETE", ambiguity_level="NONE", contradiction_present=False, evidence_sufficiency="SUFFICIENT", entity_confidence_state="EXPLICIT", source_policy_concern_state="NONE", material_risk_flags=("NONE",), reason_codes=("REVIEW_COMPLETED",), structured_explanation="bounded semantic review", escalation_evidence_refs=("evidence-001",), semantic_result_id=None)


def _router(result, route):
    name = {"L0": "CLEAN_OR_ROUTINE", "L1": "MODERATE_AMBIGUITY", "L2": "CRITICAL_AMBIGUITY"}[route]
    model = {"L0": None, "L1": "claude-sonnet-policy", "L2": "claude-opus-policy"}[route]
    reason = {"L0": "ROUTINE_COMPLETE", "L1": "MODERATE_AMBIGUITY", "L2": "CRITICAL_AMBIGUITY"}[route]
    return DeterministicEscalationDecisionV1(policy_version=DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION, event_snapshot_id=result.event_snapshot_id, deepseek_semantic_result_id=result.semantic_result_id, deepseek_payload_sha256=result.request_payload_sha256, route=route, route_name=name, claude_review_required=route != "L0", claude_model_policy_id=model, reason_codes=(reason,), escalation_evidence_refs=("evidence-001",), decision_id=None)


def _semantic_claude(event_id, request_hash, decision):
    return ClaudeEscalatedReviewResultV1(policy_version="claude-escalated-review-policy-v1", event_snapshot_id=event_id, request_payload_sha256=request_hash, router_decision_id=decision.decision_id, logical_review_id=("b" if decision.route == "L1" else "c") * 64, route=decision.route, model_policy_id=decision.claude_model_policy_id, review_status="COMPLETED", review_conclusion="ESCALATED_REVIEW_COMPLETE", ambiguity_resolution="RESOLVED", contradiction_resolution="NONE", evidence_assessment="SUFFICIENT", entity_assessment="CONFIRMED", source_assessment="ACCEPTABLE", material_risk_assessment="NONE", agreement_state_with_deepseek="AGREES", reason_codes=("CLAUDE_REVIEW_COMPLETED",), structured_explanation="bounded semantic review", adjudication_evidence_refs=("evidence-001",), semantic_result_id=None)


def _clean_bundle(route="L0"):
    event, deep_payload, claude_payload = _payloads()
    shadow_input, policy = _shadow_input(event), _policy()
    reservations = tuple(BudgetReservationV1(schema_version="phase11-budget-reservation-v1", reservation_id=f"reservation-{index:03d}", policy_id=policy.policy_id, run_id="run-001", call_id=f"call-{index:03d}", provider=provider, model=model, reserved_cost=Decimal("1000"), reserved_input_tokens=100, reserved_output_tokens=200, reserved_at="2026-07-17T00:05:00Z", expires_at="2026-07-17T02:00:00Z", status="RESERVED", reason_codes=("ROUTE_RESERVATION",)) for index, (_, provider, model) in enumerate(_GRAPH[route], 1))
    ledger_before = BudgetLedgerV1(policy=policy, reservations=reservations)
    calls = tuple(ShadowRunCallPlanV1(schema_version="phase11-shadow-run-call-plan-v1", call_plan_id=None, execution_id="execution-001", run_id="run-001", call_index=index, call_id=reservation.call_id, route=child_route, reviewer_tier=model, provider=provider, model=model, review_request=deep_payload if provider == "DEEPSEEK" else claude_payload, request_hash=(deep_payload if provider == "DEEPSEEK" else claude_payload).payload_sha256, attempt_reservations=(reservation,), timeout_ms=1000, maximum_attempts=1, circuit_state="CLOSED", adapter_identity=f"{index:x}" * 64, reason_codes=("ROUTE_REQUIRED",)) for index, ((child_route, provider, model), reservation) in enumerate(zip(_GRAPH[route], reservations, strict=True), 1))
    plan = ShadowProviderRunPlanV1(schema_version="phase11-shadow-provider-run-plan-v1", run_plan_id=None, execution_id="execution-001", run_id="run-001", shadow_input=shadow_input, shadow_input_identity=shadow_input.identity, route=route, l1_to_l2_escalation_identity="e" * 64 if route == "L1_TO_L2" else None, budget_ledger_before=ledger_before, budget_ledger_before_id=ledger_before.identity, call_plans=calls, started_at="2026-07-17T00:05:30Z", reason_codes=("ROUTE_REQUIRED",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
    deepseek = _semantic_deepseek(event.event_snapshot_id, calls[0].request_hash)
    first_decision = _router(deepseek, "L1" if route == "L1_TO_L2" else route)
    second_decision = _router(deepseek, "L2") if route == "L1_TO_L2" else None
    semantic = [deepseek] + [_semantic_claude(event.event_snapshot_id, call.request_hash, second_decision if route == "L1_TO_L2" and call.model == "CLAUDE_OPUS_L2" else first_decision) for call in calls[1:]]
    ledger_after, runtime_results, typed = ledger_before, [], []
    for index, (call, result) in enumerate(zip(calls, semantic, strict=True), 1):
        reservation = call.attempt_reservations[0]
        invocation = ShadowProviderInvocationV1(schema_version="phase11-shadow-provider-invocation-v1", invocation_id=None, execution_id=plan.execution_id, run_id=plan.run_id, call_id=call.call_id, route=call.route, provider=call.provider, model=call.model, prompt_version="phase11-prompt-v1", provider_review_schema_version="phase10-review-schema-v1", shadow_input=shadow_input, shadow_input_identity=shadow_input.identity, event_id=event.event_snapshot_id, event_version=1, budget_ledger=ledger_after, budget_policy_id=policy.policy_id, reservation=reservation, reservation_id=reservation.identity, attempt_reservations=(reservation,), review_request=call.review_request, request_hash=call.request_hash, timeout_ms=1000, maximum_attempts=1, circuit_state="CLOSED", requested_at=plan.started_at, reason_codes=("ROUTE_REQUIRED",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
        usage = ProviderUsageRecordV1(schema_version="phase11-provider-usage-v1", usage_record_id=f"usage-{index:03d}", reservation_id=reservation.reservation_id, policy_id=policy.policy_id, run_id=plan.run_id, call_id=call.call_id, provider=call.provider, model=call.model, request_hash=call.request_hash, response_hash=f"{index:x}" * 64, input_tokens=80, output_tokens=120, estimated_cost=Decimal("900"), actual_cost=Decimal("850"), started_at="2026-07-17T00:05:30Z", completed_at="2026-07-17T00:05:31Z", latency_ms=1000, attempt_count=1, outcome="SUCCESS", reconciliation_status="RESOLVED", failure_class="NONE", reason_codes=("COMPLETED",))
        runtime = ShadowProviderInvocationResultV1(schema_version="phase11-shadow-provider-invocation-result-v1", result_id=None, invocation=invocation, invocation_id=invocation.identity, status="SUCCEEDED", provider=call.provider, model=call.model, request_hash=call.request_hash, response_hash=usage.response_hash, provider_review_identity=result.semantic_result_id, reserved_cost=reservation.reserved_cost, estimated_cost=usage.estimated_cost, actual_cost=usage.actual_cost, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, started_at=usage.started_at, completed_at=usage.completed_at, latency_ms=usage.latency_ms, attempt_count=1, timeout_state="NONE", retry_state="NO_RETRY", circuit_state="CLOSED", transport_outcome="SUCCESS", failure_class="NONE", reconciliation_state="RESOLVED", usage_record=usage, reason_codes=("TRANSPORT_SUCCEEDED",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
        ledger_after = ledger_after.commit_usage(usage)
        runtime_results.append(runtime)
        typed.append(ShadowTypedProviderReviewEvidenceV1(schema_version="phase11-shadow-typed-provider-review-evidence-v1", typed_evidence_id=None, execution_id=plan.execution_id, run_id=plan.run_id, call_plan_id=call.identity, invocation_result_id=runtime.identity, call_id=call.call_id, provider=call.provider, model=call.model, request_hash=call.request_hash, provider_review_identity=result.semantic_result_id, typed_review_result=result, typed_review_identity=result.semantic_result_id, event_id=event.event_snapshot_id, event_version=1, prompt_version="phase11-prompt-v1", provider_review_schema_version="phase10-review-schema-v1", structured_verdict={"verdict": "ADVISORY_REVIEW"}, reason_codes=("TYPED_REVIEW_BOUND",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE"))
    run_result = ShadowProviderRunResultV1(schema_version="phase11-shadow-provider-run-result-v1", run_result_id=None, run_plan_id=plan.identity, execution_id=plan.execution_id, run_id=plan.run_id, route=route, completed_call_plan_ids=tuple(call.identity for call in calls), invocation_results=tuple(runtime_results), ledger_before_id=ledger_before.identity, ledger_after=ledger_after, ledger_after_id=ledger_after.identity, status="COMPLETED", failure_class="NONE", reconciliation_state="RESOLVED", first_failed_call_plan_id=None, started_at=plan.started_at, completed_at="2026-07-17T00:05:31Z", reason_codes=("RUN_COMPLETED",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
    lineage = ShadowAdjudicationRouteLineageV1(schema_version="phase11-shadow-adjudication-route-lineage-v1", route_lineage_id=None, execution_id=plan.execution_id, run_id=plan.run_id, run_route=route, adjudication_route="L2" if route == "L1_TO_L2" else route, clean_record_route="L2" if route == "L1_TO_L2" else route, router_decisions=(first_decision, second_decision) if second_decision else (first_decision,), call_plan_ids=tuple(item.call_plan_id for item in typed), typed_review_ids=tuple(item.identity for item in typed), escalation_required=route != "L0", escalation_proven=route != "L0", reason_codes=("L1_TO_L2",) if route == "L1_TO_L2" else first_decision.reason_codes, production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
    bundle = ShadowAdjudicationEvidenceBundleV1(schema_version="phase11-shadow-adjudication-evidence-bundle-v1", bundle_id=None, shadow_input=shadow_input, run_plan=plan, run_result=run_result, route_lineage=lineage, typed_review_evidence=tuple(typed), reason_codes=("FINALIZATION_READY",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
    return plan, run_result, bundle


def _terminal_plan(status="DENIED"):
    plan, _, _ = _clean_bundle("L0")
    failure, reconciliation = {
        "DENIED": ("BUDGET_DENIED", "NOT_REQUIRED"), "FAILED_CLOSED": ("PROVIDER_RUNTIME_FAILURE", "NOT_REQUIRED"),
        "PARTIAL_EVIDENCE": ("TIMEOUT", "NOT_REQUIRED"), "RECONCILIATION_REQUIRED": ("UNCERTAIN_TRANSPORT_OUTCOME", "RECONCILIATION_REQUIRED"),
    }[status]
    result = ShadowProviderRunResultV1(schema_version="phase11-shadow-provider-run-result-v1", run_result_id=None, run_plan_id=plan.identity, execution_id=plan.execution_id, run_id=plan.run_id, route=plan.route, completed_call_plan_ids=(), invocation_results=(), ledger_before_id=plan.budget_ledger_before_id, ledger_after=plan.budget_ledger_before, ledger_after_id=plan.budget_ledger_before.identity, status=status, failure_class=failure, reconciliation_state=reconciliation, first_failed_call_plan_id=None, started_at=plan.started_at, completed_at=plan.started_at, reason_codes=(failure,), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
    terminal = ShadowTerminalExecutionRecordV1(schema_version="phase11-shadow-terminal-execution-record-v1", terminal_record_id=None, shadow_input=plan.shadow_input, run_plan=plan, run_result=result, route_lineage=None, finalized_at=plan.started_at, adjudication_state=ShadowTerminalAdjudicationStateV1.NOT_PERFORMED, reason_codes=(failure,), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
    return plan, result, terminal


def _finalization_values(route="L0"):
    plan, result, bundle = _clean_bundle(route)
    return {"schema_version": "phase11-shadow-adjudication-finalization-plan-v1", "finalization_plan_id": None, "shadow_input": plan.shadow_input, "run_plan": plan, "run_result": result, "clean_bundle": bundle, "finalized_at": "2026-07-17T00:06:00Z", "reason_codes": ("FINALIZATION_REQUESTED",), "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE"}


class TestFinalizationPlanAndPaths:
    @pytest.mark.parametrize("route,canonical,count", [("L0", "L0", 1), ("L1", "L1", 2), ("L2", "L2", 2), ("L1_TO_L2", "L2", 3)])
    def test_clean_plan_reuses_real_bundle_and_preserves_route_lineage(self, route, canonical, count):
        values = _finalization_values(route)
        plan = ShadowAdjudicationFinalizationPlanV1(**values)
        assert plan.run_result.status == "COMPLETED"
        assert plan.clean_bundle.route_lineage.adjudication_route == canonical
        assert len(plan.clean_bundle.typed_review_evidence) == count
        assert plan.identity == ShadowAdjudicationFinalizationPlanV1(**_finalization_values(route)).identity

    @pytest.mark.parametrize("status", ["DENIED", "FAILED_CLOSED", "PARTIAL_EVIDENCE", "RECONCILIATION_REQUIRED"])
    def test_terminal_plan_uses_terminal_record_and_excludes_clean_bundle(self, status):
        run_plan, run_result, terminal = _terminal_plan(status)
        plan = ShadowAdjudicationFinalizationPlanV1(schema_version="phase11-shadow-adjudication-finalization-plan-v1", finalization_plan_id=None, shadow_input=run_plan.shadow_input, run_plan=run_plan, run_result=run_result, clean_bundle=None, finalized_at="2026-07-17T00:06:00Z", reason_codes=("FINALIZATION_REQUESTED",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE")
        result = ShadowAdjudicationFinalizerV1().finalize(plan, terminal_record=terminal)
        assert result.path == ShadowAdjudicationFinalizationPathV1.TERMINAL
        assert result.status == ShadowAdjudicationFinalizationStatusV1.FINALIZED
        assert result.failure == ShadowAdjudicationFinalizationFailureV1.NONE
        assert result.terminal_record is terminal
        assert result.adjudication_result is None and result.news_risk_object is None and result.signal_gate_decision is None and result.clean_execution_record is None


class TestFutureFinalizerBehavior:
    @pytest.mark.parametrize("route,canonical", [("L0", "L0"), ("L1", "L1"), ("L2", "L2"), ("L1_TO_L2", "L2")])
    def test_clean_finalization_reuses_existing_algorithms_and_clean_record(self, route, canonical):
        plan = ShadowAdjudicationFinalizationPlanV1(**_finalization_values(route))
        result = ShadowAdjudicationFinalizerV1().finalize(plan)
        assert result.path == ShadowAdjudicationFinalizationPathV1.CLEAN
        assert result.status == ShadowAdjudicationFinalizationStatusV1.FINALIZED
        assert result.failure == ShadowAdjudicationFinalizationFailureV1.NONE
        assert type(result) is ShadowAdjudicationFinalizationResultV1
        assert type(result.adjudication_result) is DeterministicAdjudicationResultV1
        assert result.clean_execution_record.route == canonical
        assert result.route_lineage is plan.clean_bundle.route_lineage
        assert result.clean_bundle is plan.clean_bundle
        assert result.terminal_record is None
        assert result.news_risk_object is not None
        assert result.signal_gate_decision is not None

    def test_l1_to_l2_clean_finalization_retains_full_escalation_lineage(self):
        plan = ShadowAdjudicationFinalizationPlanV1(**_finalization_values("L1_TO_L2"))
        result = ShadowAdjudicationFinalizerV1().finalize(plan)
        assert result.clean_execution_record.route == "L2"
        assert result.route_lineage.run_route == "L1_TO_L2"
        assert result.route_lineage.adjudication_route == "L2"
        assert result.route_lineage.clean_record_route == "L2"
        assert len(result.clean_bundle.typed_review_evidence) == 3
        assert len(result.route_lineage.router_decisions) == 2
        assert result.terminal_record is None

    def test_plan_rejects_clean_terminal_mixing_and_lineage_mismatch(self):
        values = _finalization_values("L0")
        values["clean_bundle"] = None
        with pytest.raises((TypeError, ValueError, ShadowAdjudicationFinalizerValidationError)):
            ShadowAdjudicationFinalizationPlanV1(**values)

    def test_finalization_plan_identity_is_canonical_and_binds_finalized_at(self):
        first = ShadowAdjudicationFinalizationPlanV1(**_finalization_values("L2"))
        equivalent = ShadowAdjudicationFinalizationPlanV1(**_finalization_values("L2"))
        changed = _finalization_values("L2")
        changed["finalized_at"] = "2026-07-17T00:06:01Z"
        assert first.identity == equivalent.identity
        assert first.identity != ShadowAdjudicationFinalizationPlanV1(**changed).identity
        plan, result, _ = _terminal_plan("DENIED")
        values = {"schema_version": "phase11-shadow-adjudication-finalization-plan-v1", "finalization_plan_id": None, "shadow_input": plan.shadow_input, "run_plan": plan, "run_result": result, "clean_bundle": _clean_bundle("L0")[2], "finalized_at": "2026-07-17T00:06:00Z", "reason_codes": ("FINALIZATION_REQUESTED",), "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE"}
        with pytest.raises((TypeError, ValueError, ShadowAdjudicationFinalizerValidationError)):
            ShadowAdjudicationFinalizationPlanV1(**values)

    def test_static_exclusions_and_canonical_helpers(self):
        assert lowercase_sha256({"route": "L2"}) == _sha({"route": "L2"})
        assert canonical_json_bytes({"safe": "metadata"}) == b'{"safe":"metadata"}'
        path = Path(__file__).parents[1] / "engine" / "phase_11_shadow_adjudication_finalizer_v1.py"
        if not path.exists():
            pytest.skip("RED suite: finalizer implementation is intentionally absent")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert not imports & {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "asyncio", "keyring", "boto3", "google", "azure", "telegram", "ccxt"}
        assert not names & {"invoke", "material_for_adapter", "credential_material", "commit_usage", "reconcile_uncertain_usage", "open", "mkdir", "makedirs", "environ", "getenv", "account", "exchange", "order", "trading", "publication"}
