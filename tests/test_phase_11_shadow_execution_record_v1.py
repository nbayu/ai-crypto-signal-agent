"""RED specification for the immutable Phase 11 execution evidence record."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from engine.phase_11_shadow_execution_record_v1 import ShadowExecutionRecordV1
from engine.phase_11_shadow_input_contracts_v1 import (
    ApprovedNewsCaptureV1,
    Phase09ControlProjectionV1,
    ShadowEvaluationInputV1,
    ShadowSamplePlanV1,
)
from engine.phase_11_budget_control_v1 import (
    BudgetLedgerV1,
    Phase11BudgetPolicyV1,
    ProviderUsageRecordV1,
)
from engine.news_risk_object_v1 import NewsRiskObjectV1
from engine.signal_gate_v1 import SignalGateDecisionV1
from engine.deterministic_adjudication_v1 import DeterministicAdjudicationResultV1


IMPLEMENTATION_MODULE = "engine.phase_11_shadow_execution_record_v1"
UTC = timezone.utc
EVENT_ID = "a" * 64
OTHER_EVENT_ID = "b" * 64
PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
MODELS = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
FAILURE_CLASSES = (
    "NONE", "VALIDATION_FAILURE", "UNAUTHORIZED_INVOCATION", "BUDGET_DENIED",
    "TIMEOUT", "TRANSPORT_FAILURE", "PROVIDER_UNAVAILABLE", "CIRCUIT_OPEN",
    "MALFORMED_RESPONSE", "SCHEMA_MISMATCH", "IDENTITY_MISMATCH",
    "ADJUDICATION_FAILURE", "PERSISTENCE_FAILURE", "REPLAY_MISMATCH",
    "COMPARISON_FAILURE", "RECONCILIATION_REQUIRED",
)
EVENT_STATUSES = ("COMPLETED", "FAILED", "NO_CALL", "RECONCILIATION_REQUIRED")
TIMEOUT_STATES = ("NONE", "CONNECTION_TIMEOUT", "RESPONSE_TIMEOUT")
RETRY_STATES = ("NOT_ATTEMPTED", "NO_RETRY", "RETRIED")
CIRCUIT_STATES = ("CLOSED", "OPEN", "HALF_OPEN")
RECONCILIATION_STATES = ("NOT_REQUIRED", "RESOLVED", "RECONCILIATION_REQUIRED")
PROOF = "PROVEN_NONE"


def _canonical(value):
    if isinstance(value, Decimal):
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _bytes(value):
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _identity(value):
    for name in ("identity", "execution_record_id", "news_risk_object_id", "signal_gate_decision_id"):
        if hasattr(value, name):
            return getattr(value, name)
    raise AssertionError("child has no identity")


def _rejected(factory, **changes):
    with pytest.raises((TypeError, ValueError)):
        factory(**changes)


def _capture_values(**overrides):
    payload = {
        "event_class": "CLEAN_ROUTINE",
        "headline": "A bounded execution fixture",
        "facts": {"material": False, "entities": ["entity-alpha"]},
    }
    values = {
        "schema_version": "approved-news-capture-v1",
        "event_id": EVENT_ID,
        "event_version": 1,
        "source_id": "source-001",
        "source_type": "REGULATED_FEED",
        "source_timestamp": "2026-07-17T00:00:00Z",
        "captured_at": "2026-07-17T00:01:00Z",
        "point_in_time_cutoff": "2026-07-17T00:02:00Z",
        "normalized_payload": payload,
        "normalized_payload_hash": _sha(payload),
        "event_lineage": ({"event_id": EVENT_ID, "event_version": 1, "relation": "ORIGIN"},),
        "capture_classification": "FIXTURE",
        "content_origin": "SYNTHETIC_FIXTURE",
        "evidence_refs": ("evidence-001",),
    }
    values.update(overrides)
    material = {key: value for key, value in values.items() if key not in {"capture_id", "normalized_payload_hash"}}
    values.setdefault("capture_id", _sha(material))
    return values


def _capture(**overrides):
    return ApprovedNewsCaptureV1(**_capture_values(**overrides))


def _projection_values(**overrides):
    values = {
        "schema_version": "phase09-control-projection-v1",
        "projection_id": "projection-001",
        "production_evaluation_id": "evaluation-001",
        "event_id": EVENT_ID,
        "candidate_id": "candidate-001",
        "disposition": "NO_TRADE",
        "reason_codes": ("NO_ELIGIBLE_SETUP",),
        "evidence_refs": ("control-evidence-001",),
        "evaluated_at": "2026-07-17T00:03:00Z",
        "source_artifact_hash": "1" * 64,
    }
    values.update(overrides)
    return values


def _projection(**overrides):
    return Phase09ControlProjectionV1(**_projection_values(**overrides))


EVENT_CLASSES = (
    "CLEAN_ROUTINE", "MODERATE_AMBIGUITY", "CRITICAL_AMBIGUITY", "SOURCE_DISAGREEMENT",
    "MAPPING_AMBIGUITY", "EXPLOIT_SECURITY", "DELISTING", "LEGAL_REGULATORY",
    "SOLVENCY_EXCHANGE_RISK", "SUSPECTED_MANIPULATION", "SYSTEMIC_CROSS_MARKET",
    "MALFORMED_PROVIDER_OUTPUT", "TIMEOUT_OUTAGE", "BUDGET_EXHAUSTION",
    "DUPLICATE_UPDATE_LINEAGE", "PROMPT_INJECTION_ADVERSARIAL",
)


def _plan_values(**overrides):
    values = {
        "schema_version": "shadow-sample-plan-v1",
        "sample_plan_id": "sample-plan-001",
        "plan_version": 1,
        "status": "DRAFT",
        "event_class_targets": {item: 1 for item in EVENT_CLASSES},
        "minimum_l1_count": 1,
        "minimum_l2_count": 1,
        "maximum_total_samples": 32,
        "maximum_live_samples": 0,
        "allowed_capture_classifications": ("FIXTURE",),
        "stop_conditions": ("BUDGET_HARD_STOP", "CRITICAL_AUTHORITY_FAILURE", "MAXIMUM_SAMPLE_COUNT"),
        "starts_at": "2026-07-17T01:00:00Z",
        "ends_at": "2026-07-18T01:00:00Z",
        "owner_approval_reference": None,
    }
    values.update(overrides)
    return values


def _plan(**overrides):
    return ShadowSamplePlanV1(**_plan_values(**overrides))


def _shadow_values(**overrides):
    values = {
        "schema_version": "shadow-evaluation-input-v1",
        "shadow_input_id": "shadow-input-001",
        "approved_news_capture": _capture(),
        "phase_09_control_projection": _projection(),
        "sample_plan_id": "sample-plan-001",
        "policy_version": "phase11-policy-v1",
        "created_at": "2026-07-17T00:04:00Z",
    }
    values.update(overrides)
    return values


def _shadow(**overrides):
    return ShadowEvaluationInputV1(**_shadow_values(**overrides))


def _policy(**overrides):
    values = {
        "schema_version": "phase11-budget-policy-v1",
        "policy_id": "budget-policy-001",
        "policy_version": 1,
        "status": "ACTIVE",
        "currency": "USD_MICRO",
        "total_cost_cap": Decimal("1000000"),
        "provider_cost_caps": {"DEEPSEEK": Decimal("500000"), "ANTHROPIC": Decimal("500000")},
        "model_cost_caps": {
            "DEEPSEEK_PRIMARY": Decimal("500000"),
            "CLAUDE_SONNET_L1": Decimal("300000"),
            "CLAUDE_OPUS_L2": Decimal("300000"),
        },
        "per_run_cost_cap": Decimal("100000"),
        "maximum_call_count": 100,
        "maximum_calls_per_run": 10,
        "maximum_input_tokens": 100000,
        "maximum_output_tokens": 100000,
        "maximum_tokens_per_call": 10000,
        "allowed_providers": PROVIDERS,
        "allowed_models": MODELS,
        "starts_at": "2026-07-17T00:00:00Z",
        "ends_at": "2026-07-18T00:00:00Z",
        "owner_approval_reference": "owner-approval-001",
        "stop_conditions": ("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    }
    values.update(overrides)
    return Phase11BudgetPolicyV1(**values)


def _reservation_values(**overrides):
    values = {
        "schema_version": "phase11-budget-reservation-v1",
        "reservation_id": "reservation-001",
        "policy_id": "budget-policy-001",
        "run_id": "run-001",
        "call_id": "call-001",
        "provider": "DEEPSEEK",
        "model": "DEEPSEEK_PRIMARY",
        "reserved_cost": Decimal("1000"),
        "reserved_input_tokens": 100,
        "reserved_output_tokens": 200,
        "reserved_at": "2026-07-17T00:05:00Z",
        "expires_at": "2026-07-17T02:00:00Z",
        "status": "RESERVED",
        "reason_codes": ("L0_ROUTE",),
    }
    values.update(overrides)
    return values


def _reservation(**overrides):
    return __import__("engine.phase_11_budget_control_v1", fromlist=["BudgetReservationV1"]).BudgetReservationV1(**_reservation_values(**overrides))


def _usage_for(reservation, suffix="deepseek", **overrides):
    values = {
        "schema_version": "phase11-provider-usage-v1",
        "usage_record_id": f"usage-{suffix}",
        "reservation_id": reservation.reservation_id,
        "policy_id": reservation.policy_id,
        "run_id": reservation.run_id,
        "call_id": reservation.call_id,
        "provider": reservation.provider,
        "model": reservation.model,
        "request_hash": _text_hash(f"request-{suffix}"),
        "response_hash": _text_hash(f"response-{suffix}"),
        "input_tokens": min(80, reservation.reserved_input_tokens),
        "output_tokens": min(120, reservation.reserved_output_tokens),
        "estimated_cost": Decimal("900"),
        "actual_cost": Decimal("850"),
        "started_at": "2026-07-17T01:01:00Z",
        "completed_at": "2026-07-17T01:02:00Z",
        "latency_ms": 1000,
        "attempt_count": 1,
        "outcome": "SUCCESS",
        "reconciliation_status": "RESOLVED",
        "failure_class": "NONE",
        "reason_codes": ("COMPLETED",),
    }
    values.update(overrides)
    return ProviderUsageRecordV1(**values)


def _adjudication(route="L0"):
    values = {
        "policy_version": "deterministic-adjudication-policy-v1",
        "event_snapshot_id": EVENT_ID,
        "route": route,
        "router_decision_id": "3" * 64,
        "deepseek_semantic_result_id": "4" * 64,
        "claude_semantic_result_id": None if route == "L0" else "5" * 64,
        "adjudication_outcome": "ACCEPT_DEEPSEEK" if route == "L0" else "CONSENSUS_CONFIRMED",
        "agreement_state": "SINGLE_REVIEW" if route == "L0" else "AGREEMENT",
        "final_ambiguity_state": "NONE",
        "final_contradiction_state": "NONE",
        "final_evidence_state": "SUFFICIENT",
        "final_entity_state": "ACCEPTABLE",
        "final_source_state": "ACCEPTABLE",
        "final_material_risk_state": "NONE",
        "reason_codes": ("PROVIDERS_AGREE",) if route != "L0" else ("RISK_ASSESSMENTS_ALIGNED",),
        "evidence_refs": ("evidence-001",),
        "structured_explanation": "Inert deterministic adjudication fixture.",
        "adjudication_result_id": None,
    }
    return DeterministicAdjudicationResultV1(**values)


def _risk(route="L0", adjudication=None):
    adjudication = _adjudication(route) if adjudication is None else adjudication
    values = {
        "policy_version": "news-risk-policy-v1",
        "event_snapshot_id": EVENT_ID,
        "adjudication_policy_version": "deterministic-adjudication-policy-v1",
        "adjudication_result_id": adjudication.adjudication_result_id,
        "route": route,
        "risk_classification": "CLEAR",
        "news_gate_recommendation": "NO_NEWS_RESTRICTION",
        "final_ambiguity_state": "NONE",
        "final_contradiction_state": "NONE",
        "final_evidence_state": "SUFFICIENT",
        "final_entity_state": "ACCEPTABLE",
        "final_source_state": "ACCEPTABLE",
        "final_material_risk_state": "NONE",
        "reason_codes": ("ADJUDICATION_CONFIRMED", "EVIDENCE_SUFFICIENT", "NO_MATERIAL_NEWS_RISK"),
        "evidence_refs": ("evidence-001",),
        "structured_explanation": "Inert News Risk fixture.",
        "news_risk_object_id": None,
    }
    material = {
        key: value
        for key, value in values.items()
        if key not in {"news_risk_object_id", "structured_explanation"}
    }
    values["news_risk_object_id"] = _sha(material)
    return NewsRiskObjectV1(**values)


def _gate(route="L0", risk=None):
    risk = _risk(route) if risk is None else risk
    return SignalGateDecisionV1(
        policy_version="signal-gate-policy-v1",
        event_snapshot_id=EVENT_ID,
        news_risk_policy_version="news-risk-policy-v1",
        news_risk_object_id=risk.news_risk_object_id,
        route=route,
        gate_state="OPEN",
        eligibility_recommendation="ALLOW_NEWS_ELIGIBILITY",
        risk_classification="CLEAR",
        news_gate_recommendation="NO_NEWS_RESTRICTION",
        reason_codes=("NEWS_RISK_CLEAR", "NO_NEWS_RESTRICTION"),
        evidence_refs=("evidence-001",),
        structured_explanation="Inert Signal Gate fixture.",
        signal_gate_decision_id=None,
    )


def _context(route="L0", usage_overrides=None):
    policy = _policy()
    before = BudgetLedgerV1(policy=policy)
    if route == "L1_TO_L2":
        reserved = before.reserve_route("L1", "run-001", "call-001")
        reserved = reserved.reserve_escalation("L1_TO_L2", "call-002")
    elif route == "L0":
        reserved = before.reserve_call(_reservation())
    else:
        reserved = before.reserve_route(route, "run-001", "call-001")
    committed = reserved
    usages = []
    for index, item in enumerate(reserved.reservations):
        suffix = item.model.lower().replace("_", "-") + f"-{index}"
        usage = _usage_for(item, suffix, **(usage_overrides or {}))
        usages.append(usage)
        committed = committed.commit_usage(usage)
    return {
        "policy": policy,
        "before": before,
        "reserved": reserved,
        "after": committed,
        "usages": tuple(usages),
    }


def _record_identity(values):
    child_fields = {
        "shadow_input", "budget_ledger_before", "budget_ledger_after",
        "news_risk_object", "signal_gate_decision", "adjudication_result",
    }
    material = {
        key: value for key, value in values.items()
        if key not in child_fields and key != "execution_record_id"
    }
    return _sha(material)


def _record_values(route="L0", context=None, **overrides):
    context = _context(route) if context is None else context
    shadow = overrides.get("shadow_input", _shadow())
    capture = shadow.approved_news_capture
    projection = shadow.phase_09_control_projection
    child_route = "L2" if route == "L1_TO_L2" else route
    adjudication = overrides.get("adjudication_result", _adjudication(child_route))
    risk = overrides.get("news_risk_object", _risk(child_route, adjudication))
    gate = overrides.get("signal_gate_decision", _gate(child_route, risk))
    usages = context["usages"]
    reservations = context["reserved"].reservations
    route_label = "L2" if route == "L1_TO_L2" else route
    values = {
        "schema_version": "phase11-shadow-execution-record-v1",
        "shadow_input": shadow,
        "shadow_input_id": shadow.shadow_input_id,
        "shadow_input_identity": shadow.identity,
        "approved_news_capture_id": capture.identity,
        "phase09_control_projection_id": projection.identity,
        "sample_plan_id": shadow.sample_plan_id,
        "execution_record_id": None,
        "run_id": "run-001",
        "event_id": capture.event_id,
        "event_version": capture.event_version,
        "budget_policy_id": context["policy"].policy_id,
        "budget_ledger_before": context["before"],
        "budget_ledger_after": context["after"],
        "budget_ledger_before_id": context["before"].identity,
        "budget_ledger_after_id": context["after"].identity,
        "prompt_version": "phase11-prompt-v1",
        "provider_review_schema_version": "phase11-provider-review-schema-v1",
        "routing_policy_version": "deterministic-escalation-router-policy-v1",
        "adjudication_policy_version": "deterministic-adjudication-policy-v1",
        "news_risk_policy_version": "news-risk-policy-v1",
        "signal_gate_policy_version": "signal-gate-policy-v1",
        "route": route_label,
        "escalation_reason_codes": ("L1_TO_L2",) if route == "L1_TO_L2" else ("ROUTINE_COMPLETE",) if route == "L0" else ("MODERATE_AMBIGUITY",) if route == "L1" else ("CRITICAL_AMBIGUITY",),
        "provider_identities": tuple(item.provider for item in reservations),
        "model_identities": tuple(item.model for item in reservations),
        "model_versions": tuple("fictional-" + item.model.lower() + "-v1" for item in reservations),
        "reservation_ids": tuple(item.identity for item in reservations),
        "usage_record_ids": tuple(item.identity for item in usages),
        "request_hashes": tuple(item.request_hash for item in usages),
        "response_hashes": tuple(item.response_hash for item in usages),
        "provider_verdicts": tuple("DEEPSEEK_NEUTRAL" if item.provider == "DEEPSEEK" else "CLAUDE_NEUTRAL" for item in reservations),
        "input_tokens": sum(item.input_tokens for item in usages),
        "output_tokens": sum(item.output_tokens for item in usages),
        "estimated_cost": sum((item.estimated_cost for item in usages), Decimal("0")),
        "actual_cost": sum((item.actual_cost for item in usages), Decimal("0")),
        "latency_ms": sum(item.latency_ms for item in usages),
        "attempt_count": sum(item.attempt_count for item in usages),
        "timeout_state": "NONE",
        "retry_state": "NO_RETRY",
        "circuit_state": "CLOSED",
        "reconciliation_state": "RESOLVED",
        "reservation_statuses": tuple(item.status for item in reservations),
        "usage_statuses": tuple(item.reconciliation_status for item in usages),
        "execution_status": "COMPLETED",
        "started_at": "2026-07-17T01:00:00Z",
        "completed_at": "2026-07-17T01:02:00Z",
        "adjudication_result": adjudication,
        "adjudication_result_id": adjudication.adjudication_result_id,
        "adjudicated_news_risk_status": risk.risk_classification,
        "news_risk_object": risk,
        "news_risk_object_id": risk.news_risk_object_id,
        "signal_gate_decision": gate,
        "signal_gate_decision_id": gate.signal_gate_decision_id,
        "failure_class": "NONE",
        "reason_codes": ("EXECUTION_COMPLETED",),
        "evidence_refs": ("evidence-001",),
        "production_effect": "NONE",
        "no_candidate_mutation_proof": PROOF,
        "no_production_signal_mutation_proof": PROOF,
        "no_publication_proof": PROOF,
        "no_telegram_delivery_proof": PROOF,
        "no_quota_capacity_consumption_proof": PROOF,
        "no_account_exchange_order_trading_proof": PROOF,
        "detached_phase09_evidence_proof": "DETACHED_PHASE09_ONLY",
        "proof_version": "phase11-no-production-effect-proof-v1",
    }
    values.update(overrides)
    if values["execution_record_id"] is None:
        values["execution_record_id"] = _record_identity(values)
    return values


def _record(**overrides):
    return ShadowExecutionRecordV1(**_record_values(**overrides))


class TestShadowExecutionRecordV1:
    def test_positive_construction_and_immutability(self):
        value = _record()
        assert value.production_effect == "NONE"
        with pytest.raises((AttributeError, TypeError)):
            value.route = "L2"

    def test_unknown_and_missing_fields_are_rejected(self):
        _rejected(ShadowExecutionRecordV1, **_record_values(unknown_field="reject"))
        values = _record_values()
        del values["budget_policy_id"]
        _rejected(ShadowExecutionRecordV1, **values)

    def test_execution_identity_is_derived_and_forgery_is_rejected(self):
        values = _record_values()
        assert values["execution_record_id"] == _record_identity(values)
        _rejected(ShadowExecutionRecordV1, **_record_values(execution_record_id="f" * 64))

    def test_collections_are_defensively_normalized(self):
        values = _record_values(reason_codes=["EXECUTION_COMPLETED"], evidence_refs=["evidence-001"])
        value = ShadowExecutionRecordV1(**values)
        assert isinstance(value.reason_codes, tuple)
        assert isinstance(value.evidence_refs, tuple)
        with pytest.raises((AttributeError, TypeError)):
            value.reason_codes += ("OTHER",)

    def test_nested_values_must_be_bound_contracts_or_identities(self):
        _rejected(ShadowExecutionRecordV1, **_record_values(shadow_input_identity={"bad": True}))
        _rejected(ShadowExecutionRecordV1, **_record_values(news_risk_object_id="f" * 64))

    def test_valid_alternate_child_objects_are_rejected_when_bindings_conflict(self):
        alternate_shadow = _shadow(
            shadow_input_id="shadow-input-002",
            phase_09_control_projection=_projection(candidate_id="candidate-002"),
        )
        _rejected(
            ShadowExecutionRecordV1,
            **_record_values(
                shadow_input=alternate_shadow,
                shadow_input_identity=_shadow().identity,
            ),
        )
        alternate_context = _context("L1")
        _rejected(
            ShadowExecutionRecordV1,
            **_record_values(context=alternate_context),
        )
        alternate_adjudication = _adjudication("L1")
        alternate_risk = _risk("L1", alternate_adjudication)
        alternate_gate = _gate("L1", alternate_risk)
        _rejected(
            ShadowExecutionRecordV1,
            **_record_values(
                news_risk_object=alternate_risk,
                signal_gate_decision=alternate_gate,
                adjudication_result=alternate_adjudication,
            ),
        )

    @pytest.mark.parametrize("field", ("shadow_input_id", "sample_plan_id", "budget_policy_id", "event_id"))
    def test_redundant_child_binding_fields_are_rejected(self, field):
        replacement = "other-value" if field != "event_id" else OTHER_EVENT_ID
        _rejected(ShadowExecutionRecordV1, **_record_values(**{field: replacement}))

    def test_event_version_and_phase09_identity_are_bound(self):
        _rejected(ShadowExecutionRecordV1, **_record_values(event_version=2))
        _rejected(ShadowExecutionRecordV1, **_record_values(phase09_control_projection_id="f" * 64))

    def test_ledger_chain_and_budget_bindings_are_validated(self):
        values = _record_values(budget_ledger_before_id=_record().budget_ledger_after_id)
        _rejected(ShadowExecutionRecordV1, **values)
        _rejected(ShadowExecutionRecordV1, **_record_values(budget_policy_id="other-policy"))
        _rejected(ShadowExecutionRecordV1, **_record_values(reservation_ids=("f" * 64,)))
        _rejected(ShadowExecutionRecordV1, **_record_values(usage_record_ids=("f" * 64,)))

    @pytest.mark.parametrize("route", ("L0", "L1", "L2"))
    def test_locked_routes_have_expected_provider_tiers(self, route):
        context = _context(route)
        value = _record(**_record_values(route=route, context=context))
        assert value.route == route
        assert value.provider_identities[0] == "DEEPSEEK"
        if route == "L0":
            assert "CLAUDE_SONNET_L1" not in value.model_identities
            assert "CLAUDE_OPUS_L2" not in value.model_identities
        elif route == "L1":
            assert "CLAUDE_SONNET_L1" in value.model_identities
            assert "CLAUDE_OPUS_L2" not in value.model_identities
        else:
            assert "CLAUDE_OPUS_L2" in value.model_identities

    def test_l0_rejects_claude_evidence(self):
        context = _context("L0")
        _rejected(ShadowExecutionRecordV1, **_record_values(
            provider_identities=("DEEPSEEK", "ANTHROPIC"),
            model_identities=("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1"),
            reservation_ids=(_identity(context["reserved"].reservations[0]), "f" * 64),
        ))

    def test_l1_to_l2_requires_explicit_reason_and_opus_evidence(self):
        context = _context("L1_TO_L2")
        value = _record(**_record_values(route="L1_TO_L2", context=context))
        assert value.route == "L2"
        assert value.escalation_reason_codes == ("L1_TO_L2",)
        assert "CLAUDE_OPUS_L2" in value.model_identities
        _rejected(ShadowExecutionRecordV1, **_record_values(
            route="L2", context=context, escalation_reason_codes=(),
        ))

    def test_provider_usage_and_reservation_sequences_bind(self):
        value = _record()
        assert len(value.reservation_ids) == len(value.usage_record_ids) == 1
        assert value.request_hashes and value.response_hashes
        assert value.input_tokens == 80
        assert value.output_tokens == 120
        assert value.estimated_cost == Decimal("900")
        assert value.actual_cost == Decimal("850")

    @pytest.mark.parametrize("field", ("estimated_cost", "actual_cost"))
    def test_money_is_decimal_exact_and_nonnegative(self, field):
        _rejected(ShadowExecutionRecordV1, **_record_values(**{field: 850.0}))
        _rejected(ShadowExecutionRecordV1, **_record_values(**{field: Decimal("-0.01")}))
        zero_context = _context(usage_overrides={field: Decimal("-0")})
        plain_context = _context(usage_overrides={field: Decimal("0")})
        zero = _record(**_record_values(context=zero_context))
        plain = _record(**_record_values(context=plain_context))
        assert zero.identity == plain.identity

    def test_zero_parent_aggregate_cannot_bypass_nonzero_child_usage(self):
        values = _record_values()
        values["estimated_cost"] = Decimal("0")
        values["actual_cost"] = Decimal("0")
        values["execution_record_id"] = _record_identity(values)
        _rejected(ShadowExecutionRecordV1, **values)

    def test_timing_latency_attempts_and_operational_states_are_consistent(self):
        value = _record()
        assert value.latency_ms >= 0
        assert value.attempt_count > 0
        assert value.completed_at.endswith("Z")
        _rejected(ShadowExecutionRecordV1, **_record_values(completed_at="2026-07-17T00:59:00Z"))
        _rejected(ShadowExecutionRecordV1, **_record_values(timeout_state="RESPONSE_TIMEOUT", execution_status="COMPLETED"))
        _rejected(ShadowExecutionRecordV1, **_record_values(retry_state="RETRIED", attempt_count=1))

    def test_failure_vocabulary_is_closed_and_combinations_fail_closed(self):
        _rejected(ShadowExecutionRecordV1, **_record_values(failure_class="UNKNOWN"))
        _rejected(ShadowExecutionRecordV1, **_record_values(failure_class="TIMEOUT", execution_status="COMPLETED"))
        _rejected(ShadowExecutionRecordV1, **_record_values(failure_class="BUDGET_DENIED", response_hashes=()))

    def test_no_production_effect_proof_is_fixed_and_material(self):
        value = _record()
        assert value.production_effect == "NONE"
        for field in (
            "no_candidate_mutation_proof", "no_production_signal_mutation_proof",
            "no_publication_proof", "no_telegram_delivery_proof",
            "no_quota_capacity_consumption_proof", "no_account_exchange_order_trading_proof",
        ):
            assert getattr(value, field) == PROOF
        _rejected(ShadowExecutionRecordV1, **_record_values(production_effect="PUBLISHED"))
        _rejected(ShadowExecutionRecordV1, **_record_values(no_publication_proof="UNPROVEN"))
        try:
            changed = _record(no_publication_proof="PROVEN_DETACHED")
        except (TypeError, ValueError):
            changed = None
        if changed is not None:
            assert value.identity != changed.identity

    def test_authority_fields_are_rejected(self):
        for field in (
            "candidate_mutation", "publication", "telegram", "account", "balance",
            "position", "capital", "exchange", "order", "trading", "api_key",
            "credentials", "bearer_token", "authorization_header", "provider_transport",
            "http_client", "network_session", "filesystem_path", "persistence_handle",
        ):
            _rejected(ShadowExecutionRecordV1, **_record_values(**{field: "forbidden"}))

    def test_identity_is_deterministic_and_material_changes_diverge(self):
        first = _record()
        equivalent = _record(reason_codes=["EXECUTION_COMPLETED"], evidence_refs=["evidence-001"])
        assert first.identity == equivalent.identity
        for field, value in (
            ("route", "L1"),
            ("request_hashes", (_text_hash("different"),)),
            ("response_hashes", (_text_hash("different-response"),)),
            ("input_tokens", 81),
            ("actual_cost", Decimal("851")),
            ("timeout_state", "RESPONSE_TIMEOUT"),
            ("retry_state", "RETRIED"),
            ("circuit_state", "HALF_OPEN"),
            ("adjudication_result_id", "3" * 64),
            ("news_risk_object_id", "4" * 64),
            ("signal_gate_decision_id", "5" * 64),
            ("failure_class", "ADJUDICATION_FAILURE"),
        ):
            if field == "route":
                changed = _record(route="L1", context=_context("L1"))
            else:
                try:
                    changed = _record(**{field: value})
                except (TypeError, ValueError):
                    changed = None
            if changed is not None:
                assert first.identity != changed.identity

    def test_provider_prose_is_not_authority_identity(self):
        first = _record()
        second = _record(provider_verdicts=("DEEPSEEK_NEUTRAL",))
        assert first.identity == second.identity
        _rejected(ShadowExecutionRecordV1, **_record_values(provider_verdicts=("provider says publish",)))

    def test_replay_evidence_chain_is_present(self):
        value = _record()
        for field in (
            "shadow_input_identity", "approved_news_capture_id", "sample_plan_id",
            "budget_ledger_before_id", "budget_ledger_after_id", "request_hashes",
            "response_hashes", "usage_record_ids", "adjudication_result_id",
            "news_risk_object_id", "signal_gate_decision_id", "evidence_refs",
        ):
            assert getattr(value, field) not in (None, (), "")

    def test_identity_mismatch_is_fail_closed(self):
        _rejected(ShadowExecutionRecordV1, **_record_values(shadow_input_identity="f" * 64))
        _rejected(ShadowExecutionRecordV1, **_record_values(signal_gate_decision_id="f" * 64))


def _ast_dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _ast_identifiers(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return names


def test_implementation_has_only_allowed_deterministic_dependencies():
    module = __import__(IMPLEMENTATION_MODULE, fromlist=["*"])
    tree = ast.parse(inspect.getsource(module))
    allowed_roots = {
        "__future__", "ast", "dataclasses", "datetime", "decimal", "enum",
        "hashlib", "json", "re", "types", "typing", "engine",
    }
    forbidden = {
        "requests", "httpx", "urllib", "socket", "subprocess", "dotenv", "telegram",
        "ccxt", "master_engine_v4", "production_signal_service_v1", "telegram_sdk_runner_v4",
        "deepseek_validator_v4", "os",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root in allowed_roots
                assert root not in forbidden
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root in allowed_roots
            assert root not in forbidden


def test_implementation_has_no_authority_or_environment_access():
    module = __import__(IMPLEMENTATION_MODULE, fromlist=["*"])
    tree = ast.parse(inspect.getsource(module))
    forbidden_names = {
        "account", "balance", "position", "capital", "exchange", "order", "trading",
        "api_key", "credential", "credentials", "transport", "provider_transport",
        "telegram", "publication", "production_signal", "quota",
    }
    assert not (_ast_identifiers(tree) & forbidden_names)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert _ast_dotted_name(node) not in {"os.environ", "os.getenv"}
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            assert all(alias.name not in {"environ", "getenv"} for alias in node.names)
        elif isinstance(node, ast.Call):
            assert (_ast_dotted_name(node.func) or (node.func.id if isinstance(node.func, ast.Name) else None)) not in {"getenv", "load_dotenv"}


def test_disposition_is_not_a_forbidden_identifier():
    module = __import__(IMPLEMENTATION_MODULE, fromlist=["*"])
    tree = ast.parse(inspect.getsource(module))
    assert "disposition" in _ast_identifiers(tree)
