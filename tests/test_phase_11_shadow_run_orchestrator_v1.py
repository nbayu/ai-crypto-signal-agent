"""RED contract for a network-free Phase 11 shadow provider run orchestrator."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from engine.ai_review_payload_projector_v1 import ClaudeReviewPayloadV1, DeepSeekReviewPayloadV1, PayloadTokenPolicyV1, project_ai_review_payloads
from engine.news_entity_mapping_v1 import ENTITY_MAPPING_POLICY_VERSION, EntityCandidateV1, map_entity_candidates
from engine.news_event_contract_v1 import EVENT_SCHEMA_VERSION, NormalizedNewsEventV1
from engine.news_source_policy_v1 import SourcePolicyDecisionV1
from engine.phase_11_budget_control_v1 import BudgetLedgerV1, BudgetReservationV1, Phase11BudgetPolicyV1
from engine.phase_11_provider_credential_boundary_v1 import EphemeralProviderCredentialV1, ProviderCredentialReferenceV1, ProviderCredentialResolutionV1
from engine.phase_11_provider_transport_adapters_v1 import AnthropicShadowTransportAdapterV1, DeepSeekShadowTransportAdapterV1, ProviderEndpointBindingV1
from engine.phase_11_shadow_input_contracts_v1 import ApprovedNewsCaptureV1, Phase09ControlProjectionV1, ShadowEvaluationInputV1
from engine.phase_11_shadow_run_orchestrator_v1 import (
    ShadowProviderRunOrchestratorV1,
    ShadowProviderRunOrchestratorValidationError,
    ShadowProviderRunPlanV1,
    ShadowProviderRunResultV1,
    ShadowRunCallPlanV1,
    ShadowRunFailureV1,
    ShadowRunReconciliationV1,
    ShadowRunStatusV1,
    canonical_json_bytes,
    lowercase_sha256,
)


UTC = timezone.utc
RAW_MATERIAL = b"synthetic-shadow-run-credential"
PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
MODELS = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
CALL_GRAPHS = {
    "L0": (("L0", "DEEPSEEK", "DEEPSEEK_PRIMARY"),),
    "L1": (("L1", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1")),
    "L2": (("L2", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L2", "ANTHROPIC", "CLAUDE_OPUS_L2")),
    "L1_TO_L2": (("L1", "DEEPSEEK", "DEEPSEEK_PRIMARY"), ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1"), ("L1_TO_L2", "ANTHROPIC", "CLAUDE_OPUS_L2")),
}


def _canonical(value):
    if isinstance(value, Decimal):
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _sha(value):
    return hashlib.sha256(json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _text_hash(value: str) -> str:
    if type(value) is not str:
        raise TypeError("raw text hash requires str")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reject(factory, **values):
    with pytest.raises((TypeError, ValueError, ShadowProviderRunOrchestratorValidationError)):
        factory(**values)


def _payloads():
    event = NormalizedNewsEventV1(
        event_namespace="news", authoritative_source_namespace="fixture-wire", authoritative_source_event_id="orchestrator-source-event-001", deterministic_source_key=None,
        normalized_primary_subject="asset:alpha", canonical_event_class="PROTOCOL_UPDATE", normalized_title="Alpha protocol announced", normalized_body="Alpha deterministic update.",
        normalized_language="en-US", publication_timestamp_utc=datetime(2026, 7, 17, 0, 0, tzinfo=UTC), point_in_time_timestamp_utc=datetime(2026, 7, 17, 0, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fixture-publisher"}, previous_event_version_id=None, event_version_number=1,
        source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"}, schema_version=EVENT_SCHEMA_VERSION,
    )
    policy = SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1", decision="ELIGIBLE", primary_reason_code="SOURCE_ELIGIBLE", reason_codes=("SOURCE_ELIGIBLE",),
        evaluated_source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        evaluation_timestamp_utc=datetime(2026, 7, 17, 0, 2, 30, tzinfo=UTC), source_namespace="fixture-wire", source_id="source-001",
    )
    excerpt = "Alpha deterministic update."
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha", entity_type="DIGITAL_ASSET", canonical_entity_id="asset:alpha", canonical_name="Alpha", canonical_symbol="ALPHA", source_text="Alpha protocol",
        source_text_sha256=_text_hash("Alpha protocol"), evidence_refs=[{"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "reference_type": "EVENT_FIELD", "field_name": "normalized_title"}],
        confidence_basis="EXPLICIT_CALLER_ASSERTION", supplied_confidence=None, ambiguity_group_id=None, candidate_status="ACCEPTED", rejection_reason_codes=[], mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    mapped = map_entity_candidates(event_snapshot_id=event.event_snapshot_id, source_policy_decision=policy, candidates=[candidate])
    projected = project_ai_review_payloads(
        normalized_event=event, source_policy_decision=policy, entity_mapping_result=mapped,
        bounded_evidence=({"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "source_field": "normalized_body", "excerpt": excerpt, "excerpt_sha256": _text_hash(excerpt)},),
        review_task="Assess bounded canonical facts.", token_policy=PayloadTokenPolicyV1(
            claude_input_hard_limit_tokens=8000, claude_target_input_min_tokens=2000, claude_target_input_max_tokens=5000, claude_output_hard_limit_tokens=1000,
            maximum_claude_logical_reviews_per_event=1, maximum_provider_attempts_per_review=2, maximum_retry_count=1,
        ), token_counter=lambda _: 100,
    )
    return event, policy, projected.deepseek_payload, projected.claude_payload


def _shadow_input(event):
    values = {
        "schema_version": "approved-news-capture-v1", "event_id": event.event_snapshot_id, "event_version": 1, "source_id": "source-001", "source_type": "REGULATED_FEED",
        "source_timestamp": "2026-07-17T00:00:00Z", "captured_at": "2026-07-17T00:01:00Z", "point_in_time_cutoff": "2026-07-17T00:02:00Z",
        "normalized_payload": {"headline": "Shadow orchestrator fixture"}, "normalized_payload_hash": _sha({"headline": "Shadow orchestrator fixture"}),
        "event_lineage": ({"event_id": event.event_snapshot_id, "event_version": 1, "relation": "ORIGIN"},), "capture_classification": "FIXTURE", "content_origin": "SYNTHETIC_FIXTURE", "evidence_refs": ("evidence-001",),
    }
    capture = ApprovedNewsCaptureV1(**values, capture_id=_sha({key: value for key, value in values.items() if key not in {"capture_id", "normalized_payload_hash"}}))
    control = Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1", projection_id="projection-001", production_evaluation_id="evaluation-001", event_id=event.event_snapshot_id,
        candidate_id="candidate-001", disposition="NO_TRADE", reason_codes=("NO_ELIGIBLE_SETUP",), evidence_refs=("control-evidence-001",), evaluated_at="2026-07-17T00:03:00Z", source_artifact_hash="1" * 64,
    )
    return ShadowEvaluationInputV1(schema_version="shadow-evaluation-input-v1", shadow_input_id="shadow-input-001", approved_news_capture=capture, phase_09_control_projection=control, sample_plan_id="sample-plan-001", policy_version="phase11-policy-v1", created_at="2026-07-17T00:04:00Z")


def _policy(status="ACTIVE"):
    return Phase11BudgetPolicyV1(
        schema_version="phase11-budget-policy-v1", policy_id="budget-policy-001", policy_version=1, status=status, currency="USD_MICRO", total_cost_cap=Decimal("10000000"),
        provider_cost_caps={"DEEPSEEK": Decimal("5000000"), "ANTHROPIC": Decimal("5000000")}, model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("5000000"), "CLAUDE_SONNET_L1": Decimal("3000000"), "CLAUDE_OPUS_L2": Decimal("3000000")},
        per_run_cost_cap=Decimal("5000000"), maximum_call_count=100, maximum_calls_per_run=10, maximum_input_tokens=100000, maximum_output_tokens=100000, maximum_tokens_per_call=10000,
        allowed_providers=PROVIDERS, allowed_models=MODELS, starts_at="2026-07-17T00:00:00Z", ends_at="2026-07-18T00:00:00Z", owner_approval_reference="owner-approval-001" if status == "ACTIVE" else None,
        stop_conditions=("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    )


def _reservation(policy, run_id, call_id, provider, model, index, expires_at="2026-07-17T02:00:00Z"):
    return BudgetReservationV1(
        schema_version="phase11-budget-reservation-v1", reservation_id=f"reservation-{index:03d}", policy_id=policy.policy_id, run_id=run_id, call_id=call_id,
        provider=provider, model=model, reserved_cost=Decimal("1000"), reserved_input_tokens=100, reserved_output_tokens=200,
        reserved_at="2026-07-17T00:05:00Z", expires_at=expires_at, status="RESERVED", reason_codes=("ROUTE_RESERVATION",),
    )


def _resolution(provider):
    reference = ProviderCredentialReferenceV1(
        schema_version="phase11-provider-credential-reference-v1", credential_reference_id=f"credential-reference-{provider.lower()}", provider=provider, credential_version=1,
        source_kind="TEST_FIXTURE", owner_approval_reference="owner-approval-001", created_at="2026-07-17T00:00:00Z", valid_from="2026-07-17T00:00:00Z", valid_until="2026-07-18T00:00:00Z", rotation_required=False, reference_identity=None,
    )
    credential = EphemeralProviderCredentialV1(schema_version="phase11-ephemeral-provider-credential-v1", provider=provider, credential_reference=reference, credential_reference_identity=reference.identity, credential_version=1, material=RAW_MATERIAL)
    return ProviderCredentialResolutionV1(
        schema_version="phase11-provider-credential-resolution-v1", resolution_identity=None, credential_reference=reference, credential_reference_identity=reference.identity,
        provider=provider, credential_version=1, status="RESOLVED", failure_class="NONE", resolved_at="2026-07-17T00:05:00Z", valid_until=reference.valid_until,
        rotation_required=False, reason_codes=("CREDENTIAL_RESOLVED",), ephemeral_credential=credential,
    )


class _FakeClient:
    def __init__(self, name, order, outcome="SUCCESS"):
        self.name, self.order, self.outcome, self.calls = name, order, outcome, []

    def complete(self, **values):
        self.calls.append({key: value for key, value in values.items() if key != "credential_material"})
        self.order.append(self.name)
        if self.outcome == "TIMEOUT":
            raise TimeoutError("synthetic timeout")
        if self.outcome == "TRANSPORT_FAILURE":
            raise ConnectionError("synthetic transport failure")
        return {
            "schema_version": "phase11-provider-client-response-v1", "status": self.outcome, "provider": "DEEPSEEK" if self.name == "deepseek" else "ANTHROPIC",
            "provider_model_identifier": values["provider_model_identifier"], "invocation_id": values["invocation_id"], "attempt_reservation_id": values["attempt_reservation_id"],
            "call_id": values["call_id"], "request_hash": values["request_hash"], "provider_review_identity": "c" * 64, "structured_verdict": {"verdict": "ADVISORY_REVIEW"},
            "reason_codes": ("STRUCTURED_REVIEW",), "input_tokens": 80, "output_tokens": 120, "estimated_cost": Decimal("900"), "actual_cost": Decimal("850"),
            "started_at": "2026-07-17T00:05:30Z", "completed_at": "2026-07-17T00:05:31Z", "provider_timestamp": "2026-07-17T00:05:31Z", "latency_ms": 1000,
        }


def _adapter(provider, model, payload, client):
    identifiers = {"DEEPSEEK_PRIMARY": "synthetic-deepseek-primary", "CLAUDE_SONNET_L1": "synthetic-anthropic-sonnet", "CLAUDE_OPUS_L2": "synthetic-anthropic-opus"}
    binding = ProviderEndpointBindingV1(schema_version="phase11-provider-endpoint-binding-v1", binding_identity=None, provider=provider, contract_model=model, provider_model_identifier=identifiers[model], adapter_version="phase11-provider-transport-adapter-v1", request_schema_version="phase10-review-schema-v1", response_schema_version="phase11-shadow-provider-transport-response-v1", valid_from="2026-07-17T00:00:00Z", valid_until="2026-07-18T00:00:00Z")
    values = {"endpoint_binding": binding, "review_request": payload, "credential_resolution": _resolution(provider), "attempted_at": "2026-07-17T00:05:30Z", "client": client}
    return (DeepSeekShadowTransportAdapterV1 if provider == "DEEPSEEK" else AnthropicShadowTransportAdapterV1)(**values)


def _context(route="L1", outcomes=None, policy_status="ACTIVE", ledger_state="OPEN", expires_at="2026-07-17T02:00:00Z"):
    event, source_policy, deepseek, claude = _payloads()
    shadow_input, policy, ledger = _shadow_input(event), _policy(policy_status), BudgetLedgerV1(policy=_policy(policy_status), circuit_or_stop_state=ledger_state)
    order, plans, adapters, clients = [], [], {}, []
    for index, (call_route, provider, model) in enumerate(CALL_GRAPHS[route], 1):
        reservation = _reservation(policy, "run-001", f"call-{index:03d}", provider, model, index, expires_at)
        if ledger_state == "OPEN":
            ledger = ledger.reserve_call(reservation)
        else:
            ledger = BudgetLedgerV1(policy=policy, circuit_or_stop_state=ledger_state, reservations=ledger.reservations + (reservation,))
        payload = deepseek if provider == "DEEPSEEK" else claude
        client = _FakeClient("deepseek" if provider == "DEEPSEEK" else model.lower(), order, (outcomes or {}).get(reservation.call_id, "SUCCESS"))
        adapter = _adapter(provider, model, payload, client)
        adapters[(provider, model)], clients[:] = adapter, clients + [client]
        plans.append(ShadowRunCallPlanV1(
            schema_version="phase11-shadow-run-call-plan-v1", call_plan_id=None, execution_id="execution-001", run_id="run-001", call_index=index, call_id=reservation.call_id,
            route=call_route, reviewer_tier=model, provider=provider, model=model, review_request=payload, request_hash=payload.payload_sha256, attempt_reservations=(reservation,),
            timeout_ms=1000, maximum_attempts=1, circuit_state="CLOSED", adapter_identity=adapter.identity, reason_codes=("ROUTE_REQUIRED",),
        ))
    return type("Context", (), {"event": event, "source_policy": source_policy, "shadow_input": shadow_input, "policy": policy, "ledger": ledger, "plans": tuple(plans), "adapters": adapters, "clients": tuple(clients), "order": order})()


def _plan_values(context, route, **overrides):
    values = {
        "schema_version": "phase11-shadow-provider-run-plan-v1", "run_plan_id": None, "execution_id": "execution-001", "run_id": "run-001", "shadow_input": context.shadow_input,
        "shadow_input_identity": context.shadow_input.identity, "route": route, "l1_to_l2_escalation_identity": "e" * 64 if route == "L1_TO_L2" else None,
        "budget_ledger_before": context.ledger, "budget_ledger_before_id": context.ledger.identity, "call_plans": context.plans, "started_at": "2026-07-17T00:05:30Z",
        "reason_codes": ("ROUTE_REQUIRED",), "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return values


def _run_plan(context, route, **overrides):
    return ShadowProviderRunPlanV1(**_plan_values(context, route, **overrides))


class TestPlansAndGraphs:
    @pytest.mark.parametrize("route,expected", [
        ("L0", (("DEEPSEEK", "DEEPSEEK_PRIMARY"),)),
        ("L1", (("DEEPSEEK", "DEEPSEEK_PRIMARY"), ("ANTHROPIC", "CLAUDE_SONNET_L1"))),
        ("L2", (("DEEPSEEK", "DEEPSEEK_PRIMARY"), ("ANTHROPIC", "CLAUDE_OPUS_L2"))),
        ("L1_TO_L2", (("DEEPSEEK", "DEEPSEEK_PRIMARY"), ("ANTHROPIC", "CLAUDE_SONNET_L1"), ("ANTHROPIC", "CLAUDE_OPUS_L2"))),
    ])
    def test_real_payload_plans_are_closed_immutable_and_follow_exact_graph(self, route, expected):
        context = _context(route)
        plan = _run_plan(context, route)
        assert type(context.source_policy.evaluation_timestamp_utc) is datetime and context.source_policy.evaluation_timestamp_utc.tzinfo is UTC
        assert tuple((item.provider, item.model) for item in plan.call_plans) == expected
        assert len({item.call_id for item in plan.call_plans}) == len(expected)
        assert len({item.attempt_reservations[0].identity for item in plan.call_plans}) == len(expected)
        assert all(item.request_hash == item.review_request.payload_sha256 for item in plan.call_plans)
        assert plan.identity == _run_plan(_context(route), route).identity
        with pytest.raises((AttributeError, TypeError)):
            plan.route = "L0"
        _reject(ShadowProviderRunPlanV1, **_plan_values(context, route, unknown="reject"))

    def test_invalid_graph_and_escalation_evidence_fail_closed(self):
        context = _context("L1_TO_L2")
        _reject(ShadowProviderRunPlanV1, **_plan_values(context, "L1_TO_L2", call_plans=context.plans[:-1]))
        _reject(ShadowProviderRunPlanV1, **_plan_values(context, "L1_TO_L2", call_plans=(context.plans[1], context.plans[0], context.plans[2])))
        _reject(ShadowProviderRunPlanV1, **_plan_values(context, "L1_TO_L2", l1_to_l2_escalation_identity=None))


class TestSequentialRuntimeOrchestration:
    @pytest.mark.parametrize("route,order", [
        ("L0", ("deepseek",)), ("L1", ("deepseek", "claude_sonnet_l1")), ("L2", ("deepseek", "claude_opus_l2")),
        ("L1_TO_L2", ("deepseek", "claude_sonnet_l1", "claude_opus_l2")),
    ])
    def test_execute_is_ordered_runtime_owned_and_append_only(self, route, order):
        context = _context(route)
        result = ShadowProviderRunOrchestratorV1(adapters=context.adapters).execute(_run_plan(context, route))
        assert type(result) is ShadowProviderRunResultV1
        assert result.status == "COMPLETED" and result.failure_class == "NONE"
        assert context.order == list(order)
        assert result.completed_call_plan_ids == tuple(item.identity for item in context.plans)
        assert result.ledger_after.sequence == context.ledger.sequence + len(order)
        assert result.ledger_after.reservations == context.ledger.reservations
        assert tuple(item.call_id for item in result.ledger_after.usage_records) == tuple(item.call_id for item in context.plans)
        assert result.production_effect == "NONE" and result.zero_production_effect_proof == "PROVEN_NONE"

    @pytest.mark.parametrize("state,failure", [("DRAFT", "BUDGET_DENIED"), ("HARD_STOP", "HARD_STOP_ACTIVE"), ("RECONCILIATION_REQUIRED", "HARD_STOP_ACTIVE")])
    def test_pre_call_denial_has_no_calls_and_unchanged_ledger(self, state, failure):
        context = _context("L0", policy_status=state if state == "DRAFT" else "ACTIVE", ledger_state="OPEN" if state == "DRAFT" else state)
        result = ShadowProviderRunOrchestratorV1(adapters=context.adapters).execute(_run_plan(context, "L0"))
        assert result.status == "DENIED" and result.failure_class == failure
        assert context.order == [] and result.ledger_after.identity == context.ledger.identity

    @pytest.mark.parametrize("outcome,failure,status", [
        ("TIMEOUT", "TIMEOUT", "PARTIAL_EVIDENCE"), ("TRANSPORT_FAILURE", "PROVIDER_RUNTIME_FAILURE", "PARTIAL_EVIDENCE"),
        ("PROVIDER_UNAVAILABLE", "PROVIDER_RUNTIME_FAILURE", "PARTIAL_EVIDENCE"), ("MALFORMED_RESPONSE", "MALFORMED_RESPONSE", "PARTIAL_EVIDENCE"),
        ("SCHEMA_MISMATCH", "SCHEMA_MISMATCH", "PARTIAL_EVIDENCE"),
    ])
    def test_terminal_outcome_stops_before_later_call(self, outcome, failure, status):
        context = _context("L1", outcomes={"call-001": outcome})
        result = ShadowProviderRunOrchestratorV1(adapters=context.adapters).execute(_run_plan(context, "L1"))
        assert result.status == status and result.failure_class == failure
        assert result.first_failed_call_plan_id == context.plans[0].identity and context.order == ["deepseek"]

    def test_uncertain_outcome_is_conservative_and_terminates(self):
        context = _context("L1", outcomes={"call-001": "UNCERTAIN_TRANSPORT_OUTCOME"})
        result = ShadowProviderRunOrchestratorV1(adapters=context.adapters).execute(_run_plan(context, "L1"))
        assert result.status == "RECONCILIATION_REQUIRED" and result.reconciliation_state == "RECONCILIATION_REQUIRED"
        assert result.ledger_after.circuit_or_stop_state == "RECONCILIATION_REQUIRED"
        assert len(result.ledger_after.usage_records) == 1 and context.order == ["deepseek"]


class TestBindingIdentityAndStaticBoundaries:
    def test_missing_adapter_expired_reservation_and_identity_are_fail_closed(self):
        context = _context("L1")
        orchestrator = ShadowProviderRunOrchestratorV1(
            adapters={("DEEPSEEK", "DEEPSEEK_PRIMARY"): context.adapters[("DEEPSEEK", "DEEPSEEK_PRIMARY")]}
        )
        result = orchestrator.execute(_run_plan(context, "L1"))
        assert result.status == "DENIED" and result.failure_class == "MISSING_ADAPTER"
        assert result.completed_call_plan_ids == ()
        assert result.ledger_after.identity == context.ledger.identity
        assert result.ledger_after.sequence == context.ledger.sequence
        assert result.ledger_after.usage_records == context.ledger.usage_records
        assert context.order == []
        assert result.production_effect == "NONE" and result.zero_production_effect_proof == "PROVEN_NONE"
        expired = _context("L0", expires_at="2026-07-17T00:05:29Z")
        result = ShadowProviderRunOrchestratorV1(adapters=expired.adapters).execute(_run_plan(expired, "L0"))
        assert result.status == "DENIED" and result.failure_class == "RESERVATION_MISSING" and expired.order == []
        assert lowercase_sha256({"route": "L0"}) == _sha({"route": "L0"})
        assert RAW_MATERIAL.decode() not in canonical_json_bytes({"safe": "metadata"}).decode()

    def test_closed_status_failure_and_reconciliation_vocabulary(self):
        assert {item.value for item in ShadowRunStatusV1} >= {"COMPLETED", "DENIED", "PARTIAL_EVIDENCE", "RECONCILIATION_REQUIRED"}
        assert {item.value for item in ShadowRunFailureV1} >= {"NONE", "BUDGET_DENIED", "TIMEOUT", "UNCERTAIN_TRANSPORT_OUTCOME"}
        assert {item.value for item in ShadowRunReconciliationV1} >= {"NOT_REQUIRED", "RESOLVED", "RECONCILIATION_REQUIRED"}


def test_future_orchestrator_excludes_adjudication_credentials_and_side_effects():
    path = Path(__file__).parents[1] / "engine" / "phase_11_shadow_run_orchestrator_v1.py"
    if not path.exists():
        pytest.skip("RED suite: shadow run orchestrator implementation is intentionally absent")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_imports = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "asyncio", "keyring", "boto3", "google", "azure", "telegram", "ccxt"}
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not imports & forbidden_imports
    forbidden_names = {"environ", "getenv", "open", "mkdir", "makedirs", "material_for_adapter", "credential_material", "account", "balance", "position", "capital", "exchange", "order", "trading", "publication", "telegram_client"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not names & forbidden_names
    forbidden_modules = {"deterministic_adjudication_v1", "news_risk_object_v1", "signal_gate_v1", "phase_11_shadow_execution_record_v1"}
    assert not {node.module.rsplit(".", 1)[-1] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module} & forbidden_modules
    assert "ShadowProviderRuntimeV1" in {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
