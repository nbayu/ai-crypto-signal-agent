"""RED contract for deterministic Phase 11 event-level comparison.

The implementation is deliberately absent.  The evaluator consumes detached
Phase 09 control evidence and an already-finalized Phase 11 treatment result;
it does not run either system.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
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
from engine.news_risk_object_v1 import NewsRiskObjectV1
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
    ShadowTerminalRecordStatusV1,
    ShadowTypedProviderReviewEvidenceV1,
)
from engine.phase_11_shadow_execution_record_v1 import ShadowExecutionRecordV1
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
    ShadowAdjudicationFinalizationPlanV1,
    ShadowAdjudicationFinalizationPathV1,
    ShadowAdjudicationFinalizationResultV1,
    ShadowAdjudicationFinalizationStatusV1,
)
from engine.signal_gate_v1 import SignalGateDecisionV1

from engine.phase_11_shadow_comparative_evaluator_v1 import (
    ComparisonComparabilityV1,
    ControlTreatmentDecisionDeltaV1,
    MetricAvailabilityV1,
    Phase09ControlSnapshotV1,
    ShadowComparativeEvaluationPlanV1,
    ShadowComparativeEvaluationValidationError,
    ShadowComparativeEvaluatorV1,
    ShadowComparativeObservationV1,
    StructuredProviderDisagreementV1,
    TreatmentAvailabilityV1,
    canonical_json_bytes,
    lowercase_sha256,
)


LOCKED_PHASE09_COMMIT = "e50041f7296bd9e042f749b6a98393b3df9747a1"
UTC_NOW = datetime(2026, 7, 17, 0, 7, tzinfo=UTC)


def _canonical(value):
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _sha(value):
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _control(disposition="NO_TRADE", candidate_id="candidate-001"):
    return Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1",
        projection_id="projection-001",
        production_evaluation_id="evaluation-001",
        event_id="event-001",
        candidate_id=candidate_id,
        disposition=disposition,
        reason_codes=("NO_ELIGIBLE_SETUP",) if disposition == "NO_TRADE" else ("ELIGIBLE_SETUP",),
        evidence_refs=("control-evidence-001",),
        evaluated_at="2026-07-17T00:03:00Z",
        source_artifact_hash="a" * 64,
    )


def _snapshot(**overrides):
    control = overrides.pop("control_projection", _control())
    values = {
        "schema_version": "phase09-control-snapshot-v1",
        "control_snapshot_id": None,
        "locked_baseline_commit": LOCKED_PHASE09_COMMIT,
        "control_projection": control,
        "control_artifact_type": "PHASE09_CONTROL_PROJECTION",
        "control_artifact_identity": control.identity,
        "candidate_id": control.candidate_id,
        "event_id": control.event_id,
        "control_decision": "HOLD" if control.disposition == "NO_TRADE" else "ALLOW",
        "control_reason_codes": control.reason_codes,
        "captured_at": "2026-07-17T00:04:00Z",
        "control_evaluated_at": control.evaluated_at,
        "publication_state": "NO_TRADE" if control.disposition == "NO_TRADE" else "PUBLISHED_SIGNAL",
        "reason_codes": ("DETACHED_PHASE09_EVIDENCE",),
        "comparison_authority": "EVIDENCE_ONLY",
    }
    values.update(overrides)
    return Phase09ControlSnapshotV1(**values)


_GRAPH = {
    "L0": (("L0", "DEEPSEEK", "DEEPSEEK_PRIMARY"),),
    "L1": (("L1", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1")),
    "L2": (("L2", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L2", "ANTHROPIC", "CLAUDE_OPUS_L2")),
    "L1_TO_L2": (("L1", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1"), ("L1_TO_L2", "ANTHROPIC", "CLAUDE_OPUS_L2")),
}


def _payloads():
    event = NormalizedNewsEventV1(
        event_namespace="news", authoritative_source_namespace="fixture-wire",
        authoritative_source_event_id="comparative-event-001", deterministic_source_key=None,
        normalized_primary_subject="asset:alpha", canonical_event_class="PROTOCOL_UPDATE",
        normalized_title="Alpha protocol announced", normalized_body="Alpha deterministic update.",
        normalized_language="en-US", publication_timestamp_utc=datetime(2026, 7, 17, tzinfo=UTC),
        point_in_time_timestamp_utc=datetime(2026, 7, 17, 0, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fixture-publisher"}, previous_event_version_id=None,
        event_version_number=1, source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        schema_version=EVENT_SCHEMA_VERSION,
    )
    source = SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1", decision="ELIGIBLE", primary_reason_code="SOURCE_ELIGIBLE",
        reason_codes=("SOURCE_ELIGIBLE",), evaluated_source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        evaluation_timestamp_utc=datetime(2026, 7, 17, 0, 2, 30, tzinfo=UTC), source_namespace="fixture-wire", source_id="source-001",
    )
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha", entity_type="DIGITAL_ASSET", canonical_entity_id="asset:alpha",
        canonical_name="Alpha", canonical_symbol="ALPHA", source_text="Alpha protocol",
        source_text_sha256=hashlib.sha256(b"Alpha protocol").hexdigest(),
        evidence_refs=[{"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "reference_type": "EVENT_FIELD", "field_name": "normalized_title"}],
        confidence_basis="EXPLICIT_CALLER_ASSERTION", supplied_confidence=None, ambiguity_group_id=None,
        candidate_status="ACCEPTED", rejection_reason_codes=[], mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    mapped = map_entity_candidates(event_snapshot_id=event.event_snapshot_id, source_policy_decision=source, candidates=[candidate])
    projected = project_ai_review_payloads(
        normalized_event=event, source_policy_decision=source, entity_mapping_result=mapped,
        bounded_evidence=({"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "source_field": "normalized_body", "excerpt": "Alpha deterministic update.", "excerpt_sha256": hashlib.sha256(b"Alpha deterministic update.").hexdigest()},),
        review_task="Assess bounded canonical facts.",
        token_policy=PayloadTokenPolicyV1(
            claude_input_hard_limit_tokens=8000, claude_target_input_min_tokens=2000,
            claude_target_input_max_tokens=5000, claude_output_hard_limit_tokens=1000,
            maximum_claude_logical_reviews_per_event=1, maximum_provider_attempts_per_review=2,
            maximum_retry_count=1,
        ), token_counter=lambda _: 100,
    )
    return event, projected.deepseek_payload, projected.claude_payload


def _shadow_input(event):
    payload = {"headline": "Comparative fixture"}
    capture_values = {
        "schema_version": "approved-news-capture-v1", "event_id": event.event_snapshot_id,
        "event_version": 1, "source_id": "source-001", "source_type": "REGULATED_FEED",
        "source_timestamp": "2026-07-17T00:00:00Z", "captured_at": "2026-07-17T00:01:00Z",
        "point_in_time_cutoff": "2026-07-17T00:02:00Z", "normalized_payload": payload,
        "normalized_payload_hash": _sha(payload),
        "event_lineage": ({"event_id": event.event_snapshot_id, "event_version": 1, "relation": "ORIGIN"},),
        "capture_classification": "FIXTURE", "content_origin": "SYNTHETIC_FIXTURE",
        "evidence_refs": ("evidence-001",),
    }
    capture = ApprovedNewsCaptureV1(
        capture_id=_sha({
            key: value
            for key, value in capture_values.items()
            if key != "normalized_payload_hash"
        }),
        **capture_values,
    )
    control = Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1", projection_id="projection-001",
        production_evaluation_id="evaluation-001", event_id=event.event_snapshot_id,
        candidate_id="candidate-001", disposition="NO_TRADE",
        reason_codes=("NO_ELIGIBLE_SETUP",), evidence_refs=("control-evidence-001",),
        evaluated_at="2026-07-17T00:03:00Z", source_artifact_hash="a" * 64,
    )
    return ShadowEvaluationInputV1(
        schema_version="shadow-evaluation-input-v1", shadow_input_id="shadow-input-001",
        approved_news_capture=capture, phase_09_control_projection=control,
        sample_plan_id="sample-plan-001", policy_version="phase11-policy-v1",
        created_at="2026-07-17T00:04:00Z",
    )


def _budget_policy():
    return Phase11BudgetPolicyV1(
        schema_version="phase11-budget-policy-v1", policy_id="budget-policy-001",
        policy_version=1, status="ACTIVE", currency="USD_MICRO",
        total_cost_cap=Decimal("10000000"),
        provider_cost_caps={"DEEPSEEK": Decimal("5000000"), "ANTHROPIC": Decimal("5000000")},
        model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("5000000"), "CLAUDE_SONNET_L1": Decimal("3000000"), "CLAUDE_OPUS_L2": Decimal("3000000")},
        per_run_cost_cap=Decimal("5000000"), maximum_call_count=100, maximum_calls_per_run=10,
        maximum_input_tokens=100000, maximum_output_tokens=100000, maximum_tokens_per_call=10000,
        allowed_providers=("DEEPSEEK", "ANTHROPIC"),
        allowed_models=("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2"),
        starts_at="2026-07-17T00:00:00Z", ends_at="2026-07-18T00:00:00Z",
        owner_approval_reference="owner-approval-001",
        stop_conditions=("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    )


def _deepseek(event_id, request_hash):
    return DeepSeekPrimaryReviewResultV1(
        policy_version="deepseek-primary-review-policy-v1", event_snapshot_id=event_id,
        request_payload_sha256=request_hash, logical_review_id="a" * 64,
        review_status="COMPLETED", review_conclusion="FACTUAL_REVIEW_COMPLETE",
        ambiguity_level="NONE", contradiction_present=False, evidence_sufficiency="SUFFICIENT",
        entity_confidence_state="EXPLICIT", source_policy_concern_state="NONE",
        material_risk_flags=("NONE",), reason_codes=("REVIEW_COMPLETED",),
        structured_explanation="bounded semantic review", escalation_evidence_refs=("evidence-001",),
        semantic_result_id=None,
    )


def _router(result, route):
    return DeterministicEscalationDecisionV1(
        policy_version=DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION,
        event_snapshot_id=result.event_snapshot_id, deepseek_semantic_result_id=result.semantic_result_id,
        deepseek_payload_sha256=result.request_payload_sha256, route=route,
        route_name={"L0": "CLEAN_OR_ROUTINE", "L1": "MODERATE_AMBIGUITY", "L2": "CRITICAL_AMBIGUITY"}[route],
        claude_review_required=route != "L0",
        claude_model_policy_id={"L0": None, "L1": "claude-sonnet-policy", "L2": "claude-opus-policy"}[route],
        reason_codes=({"L0": "ROUTINE_COMPLETE", "L1": "MODERATE_AMBIGUITY", "L2": "CRITICAL_AMBIGUITY"}[route],),
        escalation_evidence_refs=("evidence-001",), decision_id=None,
    )


def _claude(event_id, request_hash, decision):
    return ClaudeEscalatedReviewResultV1(
        policy_version="claude-escalated-review-policy-v1", event_snapshot_id=event_id,
        request_payload_sha256=request_hash, router_decision_id=decision.decision_id,
        logical_review_id=("b" if decision.route == "L1" else "c") * 64,
        route=decision.route, model_policy_id=decision.claude_model_policy_id,
        review_status="COMPLETED", review_conclusion="ESCALATED_REVIEW_COMPLETE",
        ambiguity_resolution="RESOLVED", contradiction_resolution="NONE",
        evidence_assessment="SUFFICIENT", entity_assessment="CONFIRMED",
        source_assessment="ACCEPTABLE", material_risk_assessment="NONE",
        agreement_state_with_deepseek="AGREES", reason_codes=("CLAUDE_REVIEW_COMPLETED",),
        structured_explanation="bounded semantic review", adjudication_evidence_refs=("evidence-001",),
        semantic_result_id=None,
    )


def _bundle(route):
    event, deep_payload, claude_payload = _payloads()
    shadow_input, policy = _shadow_input(event), _budget_policy()
    reservations = tuple(
        BudgetReservationV1(
            schema_version="phase11-budget-reservation-v1", reservation_id=f"reservation-{index:03d}",
            policy_id=policy.policy_id, run_id="run-001", call_id=f"call-{index:03d}",
            provider=provider, model=model, reserved_cost=Decimal("1000"),
            reserved_input_tokens=100, reserved_output_tokens=200,
            reserved_at="2026-07-17T00:05:00Z", expires_at="2026-07-17T02:00:00Z",
            status="RESERVED", reason_codes=("ROUTE_RESERVATION",),
        )
        for index, (_, provider, model) in enumerate(_GRAPH[route], 1)
    )
    before = BudgetLedgerV1(policy=policy, reservations=reservations)
    calls = tuple(
        ShadowRunCallPlanV1(
            schema_version="phase11-shadow-run-call-plan-v1", call_plan_id=None,
            execution_id="execution-001", run_id="run-001", call_index=index,
            call_id=reservation.call_id, route=child_route, reviewer_tier=model,
            provider=provider, model=model,
            review_request=deep_payload if provider == "DEEPSEEK" else claude_payload,
            request_hash=(deep_payload if provider == "DEEPSEEK" else claude_payload).payload_sha256,
            attempt_reservations=(reservation,), timeout_ms=1000, maximum_attempts=1,
            circuit_state="CLOSED", adapter_identity=f"{index:x}" * 64,
            reason_codes=("ROUTE_REQUIRED",),
        )
        for index, ((child_route, provider, model), reservation)
        in enumerate(zip(_GRAPH[route], reservations, strict=True), 1)
    )
    plan = ShadowProviderRunPlanV1(
        schema_version="phase11-shadow-provider-run-plan-v1", run_plan_id=None,
        execution_id="execution-001", run_id="run-001", shadow_input=shadow_input,
        shadow_input_identity=shadow_input.identity, route=route,
        l1_to_l2_escalation_identity="e" * 64 if route == "L1_TO_L2" else None,
        budget_ledger_before=before, budget_ledger_before_id=before.identity,
        call_plans=calls, started_at="2026-07-17T00:05:30Z",
        reason_codes=("ROUTE_REQUIRED",), production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )
    deep = _deepseek(event.event_snapshot_id, calls[0].request_hash)
    first = _router(deep, "L1" if route == "L1_TO_L2" else route)
    second = _router(deep, "L2") if route == "L1_TO_L2" else None
    semantic = [deep] + [
        _claude(
            event.event_snapshot_id, call.request_hash,
            second if route == "L1_TO_L2" and call.model == "CLAUDE_OPUS_L2" else first,
        )
        for call in calls[1:]
    ]
    after, invocations, typed, committed_usage = before, [], [], []
    for index, (call, result) in enumerate(zip(calls, semantic, strict=True), 1):
        reservation = call.attempt_reservations[0]
        invocation = ShadowProviderInvocationV1(
            schema_version="phase11-shadow-provider-invocation-v1", invocation_id=None,
            execution_id=plan.execution_id, run_id=plan.run_id, call_id=call.call_id,
            route=call.route, provider=call.provider, model=call.model,
            prompt_version="phase11-prompt-v1",
            provider_review_schema_version="phase10-review-schema-v1",
            shadow_input=shadow_input, shadow_input_identity=shadow_input.identity,
            event_id=event.event_snapshot_id, event_version=1, budget_ledger=after,
            budget_policy_id=policy.policy_id, reservation=reservation,
            reservation_id=reservation.identity, attempt_reservations=(reservation,),
            review_request=call.review_request, request_hash=call.request_hash,
            timeout_ms=1000, maximum_attempts=1, circuit_state="CLOSED",
            requested_at=plan.started_at, reason_codes=("ROUTE_REQUIRED",),
            production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
        )
        usage = ProviderUsageRecordV1(
            schema_version="phase11-provider-usage-v1", usage_record_id=f"usage-{index:03d}",
            reservation_id=reservation.reservation_id, policy_id=policy.policy_id,
            run_id=plan.run_id, call_id=call.call_id, provider=call.provider, model=call.model,
            request_hash=call.request_hash, response_hash=f"{index:x}" * 64,
            input_tokens=80, output_tokens=120, estimated_cost=Decimal("900"),
            actual_cost=Decimal("850"), started_at="2026-07-17T00:05:30Z",
            completed_at="2026-07-17T00:05:31Z", latency_ms=1000, attempt_count=1,
            outcome="SUCCESS", reconciliation_status="RESOLVED", failure_class="NONE",
            reason_codes=("COMPLETED",),
        )
        runtime = ShadowProviderInvocationResultV1(
            schema_version="phase11-shadow-provider-invocation-result-v1", result_id=None,
            invocation=invocation, invocation_id=invocation.identity, status="SUCCEEDED",
            provider=call.provider, model=call.model, request_hash=call.request_hash,
            response_hash=usage.response_hash, provider_review_identity=result.semantic_result_id,
            reserved_cost=reservation.reserved_cost, estimated_cost=usage.estimated_cost,
            actual_cost=usage.actual_cost, input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens, started_at=usage.started_at,
            completed_at=usage.completed_at, latency_ms=usage.latency_ms, attempt_count=1,
            timeout_state="NONE", retry_state="NO_RETRY", circuit_state="CLOSED",
            transport_outcome="SUCCESS", failure_class="NONE",
            reconciliation_state="RESOLVED", usage_record=usage,
            reason_codes=("TRANSPORT_SUCCEEDED",), production_effect="NONE",
            zero_production_effect_proof="PROVEN_NONE",
        )
        committed_usage.append(usage)
        after = BudgetLedgerV1(
            policy=policy,
            schema_version="phase11-budget-ledger-v1",
            ledger_id=before.ledger_id,
            sequence=index,
            reservations=reservations,
            usage_records=tuple(committed_usage),
            released_reservations=(),
            circuit_or_stop_state="OPEN",
            updated_at=usage.completed_at,
        )
        invocations.append(runtime)
        typed.append(ShadowTypedProviderReviewEvidenceV1(
            schema_version="phase11-shadow-typed-provider-review-evidence-v1",
            typed_evidence_id=None, execution_id=plan.execution_id, run_id=plan.run_id,
            call_plan_id=call.identity, invocation_result_id=runtime.identity,
            call_id=call.call_id, provider=call.provider, model=call.model,
            request_hash=call.request_hash, provider_review_identity=result.semantic_result_id,
            typed_review_result=result, typed_review_identity=result.semantic_result_id,
            event_id=event.event_snapshot_id, event_version=1,
            prompt_version="phase11-prompt-v1",
            provider_review_schema_version="phase10-review-schema-v1",
            structured_verdict={"verdict": "ADVISORY_REVIEW"},
            reason_codes=("TYPED_REVIEW_BOUND",), production_effect="NONE",
            zero_production_effect_proof="PROVEN_NONE",
        ))
    run_result = ShadowProviderRunResultV1(
        schema_version="phase11-shadow-provider-run-result-v1", run_result_id=None,
        run_plan_id=plan.identity, execution_id=plan.execution_id, run_id=plan.run_id,
        route=route, completed_call_plan_ids=tuple(call.identity for call in calls),
        invocation_results=tuple(invocations), ledger_before_id=before.identity,
        ledger_after=after, ledger_after_id=after.identity, status="COMPLETED",
        failure_class="NONE", reconciliation_state="RESOLVED",
        first_failed_call_plan_id=None, started_at=plan.started_at,
        completed_at="2026-07-17T00:05:31Z", reason_codes=("RUN_COMPLETED",),
        production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
    )
    lineage = ShadowAdjudicationRouteLineageV1(
        schema_version="phase11-shadow-adjudication-route-lineage-v1",
        route_lineage_id=None, execution_id=plan.execution_id, run_id=plan.run_id,
        run_route=route, adjudication_route="L2" if route == "L1_TO_L2" else route,
        clean_record_route="L2" if route == "L1_TO_L2" else route,
        router_decisions=(first, second) if second else (first,),
        call_plan_ids=tuple(item.call_plan_id for item in typed),
        typed_review_ids=tuple(item.identity for item in typed),
        escalation_required=route != "L0", escalation_proven=route != "L0",
        reason_codes=("L1_TO_L2",) if route == "L1_TO_L2" else first.reason_codes,
        production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
    )
    bundle = ShadowAdjudicationEvidenceBundleV1(
        schema_version="phase11-shadow-adjudication-evidence-bundle-v1",
        bundle_id=None, shadow_input=shadow_input, run_plan=plan, run_result=run_result,
        route_lineage=lineage, typed_review_evidence=tuple(typed),
        reason_codes=("FINALIZATION_READY",), production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )
    return plan, run_result, bundle


def _semantic_outputs(bundle):
    lineage = bundle.route_lineage
    deep = bundle.deepseek_result
    claude = None if lineage.adjudication_route == "L0" else bundle.claude_results[-1]
    decision = lineage.router_decisions[-1]
    adjudication = DeterministicAdjudicationResultV1(
        policy_version="deterministic-adjudication-policy-v1",
        event_snapshot_id=deep.event_snapshot_id, route=lineage.adjudication_route,
        router_decision_id=decision.decision_id,
        deepseek_semantic_result_id=deep.semantic_result_id,
        claude_semantic_result_id=None if claude is None else claude.semantic_result_id,
        adjudication_outcome="ACCEPT_DEEPSEEK" if claude is None else "CONSENSUS_CONFIRMED",
        agreement_state="SINGLE_REVIEW" if claude is None else "AGREEMENT",
        final_ambiguity_state="NONE", final_contradiction_state="NONE",
        final_evidence_state="SUFFICIENT", final_entity_state="ACCEPTABLE",
        final_source_state="ACCEPTABLE", final_material_risk_state="NONE",
        reason_codes=("MATERIAL_FACTS_ALIGNED",), evidence_refs=("evidence-001",),
        structured_explanation="deterministic comparative fixture",
        adjudication_result_id=None,
    )
    risk = NewsRiskObjectV1(
        policy_version="news-risk-policy-v1", event_snapshot_id=deep.event_snapshot_id,
        adjudication_policy_version=adjudication.policy_version,
        adjudication_result_id=adjudication.adjudication_result_id,
        route=lineage.adjudication_route, risk_classification="CLEAR",
        news_gate_recommendation="NO_NEWS_RESTRICTION",
        final_ambiguity_state="NONE", final_contradiction_state="NONE",
        final_evidence_state="SUFFICIENT", final_entity_state="ACCEPTABLE",
        final_source_state="ACCEPTABLE", final_material_risk_state="NONE",
        reason_codes=("ADJUDICATION_CONFIRMED", "NO_MATERIAL_NEWS_RISK", "EVIDENCE_SUFFICIENT"),
        evidence_refs=("evidence-001",), structured_explanation="news-risk:CLEAR",
        news_risk_object_id=None,
    )
    gate = SignalGateDecisionV1(
        policy_version="signal-gate-policy-v1", event_snapshot_id=deep.event_snapshot_id,
        news_risk_policy_version=risk.policy_version,
        news_risk_object_id=risk.news_risk_object_id, route=lineage.adjudication_route,
        gate_state="OPEN", eligibility_recommendation="ALLOW_NEWS_ELIGIBILITY",
        risk_classification="CLEAR", news_gate_recommendation="NO_NEWS_RESTRICTION",
        reason_codes=("NEWS_RISK_CLEAR", "NO_NEWS_RESTRICTION"),
        evidence_refs=("evidence-001",), structured_explanation="signal-gate:OPEN",
        signal_gate_decision_id=None,
    )
    return adjudication, risk, gate


def _clean_record(bundle, adjudication, risk, gate):
    run_plan, run_result = bundle.run_plan, bundle.run_result
    before, after = run_plan.budget_ledger_before, run_result.ledger_after
    reservations, usages = before.reservations, after.usage_records
    actual = sum((item.actual_cost for item in usages), Decimal("0"))
    capture = bundle.shadow_input.approved_news_capture
    control = bundle.shadow_input.phase_09_control_projection
    return ShadowExecutionRecordV1(
        schema_version="phase11-shadow-execution-record-v1",
        shadow_input=bundle.shadow_input, shadow_input_id=bundle.shadow_input.shadow_input_id,
        shadow_input_identity=bundle.shadow_input.identity,
        approved_news_capture_id=capture.identity,
        phase09_control_projection_id=control.identity,
        sample_plan_id=bundle.shadow_input.sample_plan_id, execution_record_id=None,
        run_id=run_plan.run_id, event_id=capture.event_id, event_version=capture.event_version,
        budget_policy_id=before.policy.policy_id, budget_ledger_before=before,
        budget_ledger_after=after, budget_ledger_before_id=before.identity,
        budget_ledger_after_id=after.identity,
        prompt_version=bundle.typed_review_evidence[0].prompt_version,
        provider_review_schema_version=bundle.typed_review_evidence[0].provider_review_schema_version,
        routing_policy_version=bundle.route_lineage.router_decisions[0].policy_version,
        adjudication_policy_version=adjudication.policy_version,
        news_risk_policy_version=risk.policy_version,
        signal_gate_policy_version=gate.policy_version,
        route=bundle.route_lineage.clean_record_route,
        escalation_reason_codes=bundle.route_lineage.reason_codes,
        provider_identities=tuple(item.provider for item in reservations),
        model_identities=tuple(item.model for item in reservations),
        model_versions=tuple(item.model for item in reservations),
        reservation_ids=tuple(item.identity for item in reservations),
        usage_record_ids=tuple(item.identity for item in usages),
        request_hashes=tuple(item.request_hash for item in usages),
        response_hashes=tuple(item.response_hash for item in usages),
        provider_verdicts=tuple("DEEPSEEK_NEUTRAL" if item.provider == "DEEPSEEK" else "CLAUDE_NEUTRAL" for item in reservations),
        input_tokens=sum(item.input_tokens for item in usages),
        output_tokens=sum(item.output_tokens for item in usages),
        estimated_cost=sum((item.estimated_cost for item in usages), Decimal("0")),
        actual_cost=actual, latency_ms=sum(item.latency_ms for item in usages),
        attempt_count=sum(item.attempt_count for item in usages),
        timeout_state="NONE", retry_state="NO_RETRY", circuit_state="CLOSED",
        reconciliation_state="RESOLVED",
        reservation_statuses=tuple(item.status for item in reservations),
        usage_statuses=tuple(item.reconciliation_status for item in usages),
        execution_status="COMPLETED", started_at=run_result.started_at,
        completed_at=run_result.completed_at, adjudication_result=adjudication,
        adjudication_result_id=adjudication.adjudication_result_id,
        adjudicated_news_risk_status=risk.risk_classification, news_risk_object=risk,
        news_risk_object_id=risk.news_risk_object_id, signal_gate_decision=gate,
        signal_gate_decision_id=gate.signal_gate_decision_id, failure_class="NONE",
        reason_codes=("EXECUTION_COMPLETED",), evidence_refs=adjudication.evidence_refs,
        production_effect="NONE", no_candidate_mutation_proof="PROVEN_NONE",
        no_production_signal_mutation_proof="PROVEN_NONE",
        no_publication_proof="PROVEN_NONE", no_telegram_delivery_proof="PROVEN_NONE",
        no_quota_capacity_consumption_proof="PROVEN_NONE",
        no_account_exchange_order_trading_proof="PROVEN_NONE",
        detached_phase09_evidence_proof="DETACHED_PHASE09_ONLY",
        proof_version="phase11-no-production-effect-proof-v1",
    )


def _finalized(route="L0", terminal=None):
    """Construct already-finalized immutable evidence directly."""
    if terminal is None:
        run_plan, run_result, bundle = _bundle(route)
        finalization_plan = ShadowAdjudicationFinalizationPlanV1(
            schema_version="phase11-shadow-adjudication-finalization-plan-v1",
            finalization_plan_id=None, shadow_input=run_plan.shadow_input,
            run_plan=run_plan, run_result=run_result, clean_bundle=bundle,
            finalized_at="2026-07-17T00:06:00Z",
            reason_codes=("FINALIZATION_REQUESTED",), production_effect="NONE",
            zero_production_effect_proof="PROVEN_NONE",
        )
        adjudication, risk, gate = _semantic_outputs(bundle)
        record = _clean_record(bundle, adjudication, risk, gate)
        return ShadowAdjudicationFinalizationResultV1(
            schema_version="phase11-shadow-adjudication-finalization-result-v1",
            finalization_result_id=None, finalization_plan_id=finalization_plan.identity,
            execution_id=run_plan.execution_id, run_id=run_plan.run_id,
            original_run_route=route,
            canonical_record_route=bundle.route_lineage.clean_record_route,
            route_lineage=bundle.route_lineage, clean_bundle=bundle,
            path=ShadowAdjudicationFinalizationPathV1.CLEAN,
            status=ShadowAdjudicationFinalizationStatusV1.FINALIZED,
            failure=ShadowAdjudicationFinalizationFailureV1.NONE,
            adjudication_result=adjudication, news_risk_object=risk,
            signal_gate_decision=gate, clean_execution_record=record,
            terminal_record=None, finalized_at=finalization_plan.finalized_at,
            reason_codes=("CLEAN_FINALIZATION_COMPLETED",), production_effect="NONE",
            zero_production_effect_proof="PROVEN_NONE",
        )
    run_plan, _, _ = _bundle("L0")
    failure, reconciliation = {
        "DENIED": ("BUDGET_DENIED", "NOT_REQUIRED"),
        "FAILED_CLOSED": ("PROVIDER_RUNTIME_FAILURE", "NOT_REQUIRED"),
        "PARTIAL_EVIDENCE": ("TIMEOUT", "NOT_REQUIRED"),
        "RECONCILIATION_REQUIRED": ("UNCERTAIN_TRANSPORT_OUTCOME", "RECONCILIATION_REQUIRED"),
    }[terminal]
    run_result = ShadowProviderRunResultV1(
        schema_version="phase11-shadow-provider-run-result-v1", run_result_id=None,
        run_plan_id=run_plan.identity, execution_id=run_plan.execution_id,
        run_id=run_plan.run_id, route=run_plan.route, completed_call_plan_ids=(),
        invocation_results=(), ledger_before_id=run_plan.budget_ledger_before_id,
        ledger_after=run_plan.budget_ledger_before,
        ledger_after_id=run_plan.budget_ledger_before.identity, status=terminal,
        failure_class=failure, reconciliation_state=reconciliation,
        first_failed_call_plan_id=None, started_at=run_plan.started_at,
        completed_at=run_plan.started_at, reason_codes=(failure,),
        production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
    )
    terminal_record = ShadowTerminalExecutionRecordV1(
        schema_version="phase11-shadow-terminal-execution-record-v1",
        terminal_record_id=None, shadow_input=run_plan.shadow_input, run_plan=run_plan,
        run_result=run_result, route_lineage=None, finalized_at=run_plan.started_at,
        adjudication_state=ShadowTerminalAdjudicationStateV1.NOT_PERFORMED,
        reason_codes=(failure,), production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )
    finalization_plan = ShadowAdjudicationFinalizationPlanV1(
        schema_version="phase11-shadow-adjudication-finalization-plan-v1",
        finalization_plan_id=None, shadow_input=run_plan.shadow_input,
        run_plan=run_plan, run_result=run_result, clean_bundle=None,
        finalized_at="2026-07-17T00:06:00Z",
        reason_codes=("FINALIZATION_REQUESTED",), production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )
    return ShadowAdjudicationFinalizationResultV1(
        schema_version="phase11-shadow-adjudication-finalization-result-v1",
        finalization_result_id=None, finalization_plan_id=finalization_plan.identity,
        execution_id=run_plan.execution_id, run_id=run_plan.run_id,
        original_run_route=run_plan.route, canonical_record_route=None,
        route_lineage=None, clean_bundle=None,
        path=ShadowAdjudicationFinalizationPathV1.TERMINAL,
        status=ShadowAdjudicationFinalizationStatusV1.FINALIZED,
        failure=ShadowAdjudicationFinalizationFailureV1.NONE,
        adjudication_result=None, news_risk_object=None, signal_gate_decision=None,
        clean_execution_record=None, terminal_record=terminal_record,
        finalized_at=finalization_plan.finalized_at,
        reason_codes=("TERMINAL_FINALIZATION_COMPLETED",), production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


def _plan(**overrides):
    treatment = overrides.pop("treatment", _finalized())
    control = overrides.pop("control_snapshot", _snapshot())
    values = {
        "schema_version": "phase11-shadow-comparative-evaluation-plan-v1",
        "comparison_plan_id": None,
        "control_snapshot": control,
        "treatment_finalization": treatment,
        "candidate_id": control.candidate_id,
        "event_id": control.event_id,
        "compared_at": UTC_NOW,
        "reason_codes": ("EVENT_LEVEL_COMPARISON",),
        "comparison_scope": "EVENT_LEVEL",
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowComparativeEvaluationPlanV1(**values)


class TestControlSnapshot:
    def test_snapshot_binds_locked_phase09_projection_as_evidence_only(self):
        snapshot = _snapshot()
        assert snapshot.locked_baseline_commit == LOCKED_PHASE09_COMMIT
        assert snapshot.control_projection.identity == snapshot.control_artifact_identity
        assert snapshot.comparison_authority == "EVIDENCE_ONLY"
        assert snapshot.identity == _snapshot().identity

    @pytest.mark.parametrize("field,value", [
        ("locked_baseline_commit", "b" * 40), ("candidate_id", "candidate-foreign"),
        ("comparison_authority", "PUBLISH"),
    ])
    def test_snapshot_rejects_foreign_or_authoritative_control(self, field, value):
        values = _snapshot().__dict__ if hasattr(_snapshot(), "__dict__") else None
        assert values is None  # frozen slots: malformed inputs must be supplied fresh.
        with pytest.raises((TypeError, ValueError, ShadowComparativeEvaluationValidationError)):
            _snapshot(**{field: value})


class TestComparisonPlanAndObservation:
    @pytest.mark.parametrize("route,canonical", [("L0", "L0"), ("L1", "L1"), ("L2", "L2"), ("L1_TO_L2", "L2")])
    def test_clean_routes_compare_real_finalized_gate_evidence(self, route, canonical):
        treatment = _finalized(route)
        control = _snapshot(control_projection=treatment.clean_bundle.shadow_input.phase_09_control_projection)
        plan = _plan(treatment=treatment, control_snapshot=control, event_id=control.event_id)
        observation = ShadowComparativeEvaluatorV1().compare(plan)
        assert type(observation) is ShadowComparativeObservationV1
        assert observation.comparability is ComparisonComparabilityV1.COMPARABLE
        assert observation.treatment_availability is TreatmentAvailabilityV1.AVAILABLE
        assert observation.treatment_decision is treatment.signal_gate_decision.eligibility_recommendation
        assert observation.original_treatment_route == route
        assert observation.canonical_treatment_route == canonical
        assert observation.locked_baseline_commit == LOCKED_PHASE09_COMMIT
        assert observation.locked_baseline_commit == control.locked_baseline_commit
        assert observation.terminal_status is None

    @pytest.mark.parametrize("status", ["DENIED", "FAILED_CLOSED", "PARTIAL_EVIDENCE", "RECONCILIATION_REQUIRED"])
    def test_terminal_treatment_has_no_fabricated_gate_or_decision(self, status):
        treatment = _finalized(terminal=status)
        control = _snapshot(control_projection=treatment.terminal_record.shadow_input.phase_09_control_projection)
        observation = ShadowComparativeEvaluatorV1().compare(_plan(treatment=treatment, control_snapshot=control, event_id=control.event_id))
        assert treatment.path is ShadowAdjudicationFinalizationPathV1.TERMINAL
        assert treatment.signal_gate_decision is None
        assert observation.treatment_decision is None
        assert observation.treatment_availability is TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE
        assert observation.decision_delta is ControlTreatmentDecisionDeltaV1.TREATMENT_UNAVAILABLE
        assert observation.locked_baseline_commit == LOCKED_PHASE09_COMMIT
        assert observation.locked_baseline_commit == control.locked_baseline_commit
        assert observation.terminal_status is ShadowTerminalRecordStatusV1[status]
        assert observation.terminal_status is treatment.terminal_record.status
        assert observation.terminal_status.value == treatment.terminal_record.run_result.status

    def test_plan_rejects_candidate_event_timestamp_and_effect_mismatch(self):
        treatment = _finalized("L1")
        control = _snapshot(control_projection=treatment.clean_bundle.shadow_input.phase_09_control_projection)
        for changed in (
            {"candidate_id": "candidate-foreign"}, {"event_id": "event-foreign"},
            {"compared_at": "2026-07-17T00:00:00Z"}, {"production_effect": "PUBLISHED"},
        ):
            with pytest.raises((TypeError, ValueError, ShadowComparativeEvaluationValidationError)):
                _plan(treatment=treatment, control_snapshot=control, **changed)

    @pytest.mark.parametrize("baseline", ["b" * 40, "not-a-commit"])
    def test_observation_rejects_foreign_or_malformed_baseline(self, baseline):
        treatment = _finalized("L0")
        control = _snapshot(control_projection=treatment.clean_bundle.shadow_input.phase_09_control_projection)
        observation = ShadowComparativeEvaluatorV1().compare(
            _plan(treatment=treatment, control_snapshot=control, event_id=control.event_id)
        )
        with pytest.raises(ShadowComparativeEvaluationValidationError):
            replace(observation, locked_baseline_commit=baseline)

    @pytest.mark.parametrize(
        "fixture,changed",
        [
            (("clean", "L0"), {"terminal_status": ShadowTerminalRecordStatusV1.DENIED}),
            (("terminal", "DENIED"), {"terminal_status": None}),
            (("terminal", "DENIED"), {"terminal_status": "DENIED"}),
            (
                ("terminal", "DENIED"),
                {"terminal_status": ShadowTerminalRecordStatusV1.FAILED_CLOSED},
            ),
        ],
    )
    def test_observation_rejects_terminal_status_contradictions(self, fixture, changed):
        kind, value = fixture
        treatment = _finalized(value) if kind == "clean" else _finalized(terminal=value)
        shadow_input = (
            treatment.clean_bundle.shadow_input
            if kind == "clean"
            else treatment.terminal_record.shadow_input
        )
        control = _snapshot(control_projection=shadow_input.phase_09_control_projection)
        observation = ShadowComparativeEvaluatorV1().compare(
            _plan(treatment=treatment, control_snapshot=control, event_id=control.event_id)
        )
        with pytest.raises(ShadowComparativeEvaluationValidationError):
            replace(observation, **changed)

    def test_observation_identity_recomputes_with_exact_new_fields(self):
        treatment = _finalized(terminal="PARTIAL_EVIDENCE")
        control = _snapshot(
            control_projection=treatment.terminal_record.shadow_input.phase_09_control_projection
        )
        observation = ShadowComparativeEvaluatorV1().compare(
            _plan(treatment=treatment, control_snapshot=control, event_id=control.event_id)
        )
        assert replace(observation, observation_id=None).identity == observation.identity
        with pytest.raises(ShadowComparativeEvaluationValidationError):
            replace(
                observation,
                terminal_status=ShadowTerminalRecordStatusV1.FAILED_CLOSED,
            )

    def test_structured_disagreement_metrics_identity_and_static_boundaries(self):
        treatment = _finalized("L1_TO_L2")
        control = _snapshot(control_projection=treatment.clean_bundle.shadow_input.phase_09_control_projection)
        observation = ShadowComparativeEvaluatorV1().compare(_plan(treatment=treatment, control_snapshot=control, event_id=control.event_id))
        assert observation.structured_disagreement in {
            StructuredProviderDisagreementV1.UNANIMOUS,
            StructuredProviderDisagreementV1.PARTIAL_DISAGREEMENT,
            StructuredProviderDisagreementV1.COMPLETE_DISAGREEMENT,
            StructuredProviderDisagreementV1.UNRESOLVED,
        }
        assert observation.cost_availability is MetricAvailabilityV1.AVAILABLE
        assert isinstance(observation.total_actual_cost, Decimal)
        assert observation.identity == ShadowComparativeEvaluatorV1().compare(_plan(treatment=treatment, control_snapshot=control, event_id=control.event_id)).identity
        assert lowercase_sha256({"route": "L2"}) == _sha({"route": "L2"})
        assert canonical_json_bytes({"safe": "evidence"}) == b'{"safe":"evidence"}'
        source = Path(__file__).parents[1] / "engine" / "phase_11_shadow_comparative_evaluator_v1.py"
        if not source.exists():
            pytest.skip("RED suite: comparative evaluator implementation is intentionally absent")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert not imports & {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "asyncio", "keyring", "boto3", "google", "azure", "telegram", "ccxt"}
        assert not names & {"run_production_signal_service_v1", "finalize", "invoke", "material_for_adapter", "commit_usage", "reconcile_uncertain_usage", "open", "environ", "getenv", "publication", "replay", "aggregate"}
