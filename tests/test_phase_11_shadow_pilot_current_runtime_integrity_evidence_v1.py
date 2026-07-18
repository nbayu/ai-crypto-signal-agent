"""RED contract for current adapter/runtime integrity evidence.

The behavioral probes execute only the already-committed runtime with
deterministic in-memory transports.  The future evidence module stores the
observations and metadata only; it must not execute these probes.
"""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from engine.ai_review_payload_projector_v1 import (
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
from engine.phase_11_budget_control_v1 import BudgetLedgerV1, BudgetReservationV1, Phase11BudgetPolicyV1
from engine.phase_11_provider_transport_adapters_v1 import AdapterFailureV1
from engine.phase_11_shadow_input_contracts_v1 import ApprovedNewsCaptureV1, Phase09ControlProjectionV1, ShadowEvaluationInputV1
from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import get_phase_11_shadow_pilot_credential_safe_launch_gate_v1
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import ShadowPhase11PilotLaunchReadinessV1, ShadowPhase11PilotProviderRoleV1
from engine.phase_11_shadow_pilot_runtime_no_retry_enforcement_v1 import get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1
from engine.phase_11_shadow_provider_runtime_v1 import RuntimeFailureV1, ShadowProviderInvocationV1, ShadowProviderRuntimeV1, TransportOutcomeV1, lowercase_sha256
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import (
    ShadowPhase11CurrentRuntimeIntegrityEvidenceV1,
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1,
    ShadowPhase11CurrentRuntimeIntegrityProbeResultV1,
    ShadowPhase11CurrentRuntimeIntegrityStateV1,
    ShadowPhase11CurrentRuntimeIntegrityValidationError,
    ShadowPhase11CurrentRuntimePredecessorStatusV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1,
    sha256_hex,
)


UTC = timezone.utc
LOCKED_REPOSITORY_BASELINE = "070ff7528df0ec16eb6ed01be5c43d9085408986"
LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
GATE_IDENTITY = "77b7bbb6782a4710b04abd16547ba5fd94e8311d09cad0cd0187fc7b8313c06b"
PREDECESSOR_REFERENCE = "PHASE_11_PILOT_RUNTIME_NO_RETRY_ENFORCEMENT_001"
PREDECESSOR_IDENTITY = "94e77016e839271eca11b3e4f0976249e63ca714fe4c708553f8dd5513d5d47e"
ADAPTER_PATH = "engine/phase_11_provider_transport_adapters_v1.py"
ADAPTER_SHA256 = "09e71d22926f8855813e238675336e0f426c9209659804a30ee3a6e0a4025d07"
ADAPTER_BLOB = "e7c42427159c8335d84de691cc2474852c8fcb99"
ADAPTER_BYTES = 25425
RUNTIME_PATH = "engine/phase_11_shadow_provider_runtime_v1.py"
RUNTIME_SHA256 = "f1c52caf771cfa5b753f6bc5f2ebda5024d677549ae6dc09c66318fd9ff72e1d"
RUNTIME_BLOB = "6e128cc66e0fd87179dad392d633364f425e965d"
RUNTIME_BYTES = 38679
HISTORICAL_RUNTIME_SHA256 = "853bd420bef56bd560abf2e65baccc8e33f17d549bfd60a4b4ace5917b56cf38"
HISTORICAL_RUNTIME_BLOB = "572a6716836e723287b4aa2a835ed985378fbf6a"
HISTORICAL_RUNTIME_BYTES = 38310
FUTURE_PATH = "engine/phase_11_shadow_pilot_current_runtime_integrity_evidence_v1.py"


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _event() -> NormalizedNewsEventV1:
    return NormalizedNewsEventV1(
        event_namespace="news", authoritative_source_namespace="fixture-wire",
        authoritative_source_event_id="current-runtime-integrity-001", deterministic_source_key=None,
        normalized_primary_subject="asset:alpha", canonical_event_class="PROTOCOL_UPDATE",
        normalized_title="Current runtime fixture", normalized_body="Deterministic fixture.",
        normalized_language="en-US", publication_timestamp_utc=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
        point_in_time_timestamp_utc=datetime(2026, 7, 16, 12, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fixture"}, previous_event_version_id=None,
        event_version_number=1, source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        schema_version=EVENT_SCHEMA_VERSION,
    )


def _deepseek_payload() -> tuple[NormalizedNewsEventV1, DeepSeekReviewPayloadV1]:
    event = _event()
    source = SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1", decision="ELIGIBLE", primary_reason_code="SOURCE_ELIGIBLE",
        reason_codes=("SOURCE_ELIGIBLE",), evaluated_source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        evaluation_timestamp_utc=datetime(2026, 7, 16, 12, 30, tzinfo=UTC), source_namespace="fixture-wire", source_id="source-001",
    )
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha", entity_type="DIGITAL_ASSET", canonical_entity_id="asset:alpha",
        canonical_name="Alpha", canonical_symbol="ALPHA", source_text="Alpha", source_text_sha256=_text_hash("Alpha"),
        evidence_refs=[{"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "reference_type": "EVENT_FIELD", "field_name": "normalized_title"}],
        confidence_basis="EXPLICIT_CALLER_ASSERTION", supplied_confidence=None, ambiguity_group_id=None,
        candidate_status="ACCEPTED", rejection_reason_codes=[], mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    mapping = map_entity_candidates(event_snapshot_id=event.event_snapshot_id, source_policy_decision=source, candidates=[candidate])
    policy = PayloadTokenPolicyV1(
        claude_input_hard_limit_tokens=8000, claude_target_input_min_tokens=2000, claude_target_input_max_tokens=5000,
        claude_output_hard_limit_tokens=1000, maximum_claude_logical_reviews_per_event=1,
        maximum_provider_attempts_per_review=2, maximum_retry_count=1,
    )
    payloads = project_ai_review_payloads(
        normalized_event=event, source_policy_decision=source, entity_mapping_result=mapping,
        bounded_evidence=({"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "source_field": "normalized_body", "excerpt": event.normalized_body, "excerpt_sha256": _text_hash(event.normalized_body)},),
        review_task="Assess deterministic facts.", token_policy=policy, token_counter=lambda _: 100,
    )
    return event, payloads.deepseek_payload


def _shadow_input(event_id: str) -> ShadowEvaluationInputV1:
    payload = {"event_class": "FIXTURE", "headline": "Current runtime integrity"}
    capture_fields = {
        "schema_version": "approved-news-capture-v1", "event_id": event_id, "event_version": 1,
        "source_id": "source-001", "source_type": "REGULATED_FEED", "source_timestamp": "2026-07-17T00:00:00Z",
        "captured_at": "2026-07-17T00:01:00Z", "point_in_time_cutoff": "2026-07-17T00:02:00Z",
        "normalized_payload": payload, "normalized_payload_hash": _json_hash(payload),
        "event_lineage": ({"event_id": event_id, "event_version": 1, "relation": "ORIGIN"},),
        "capture_classification": "FIXTURE", "content_origin": "SYNTHETIC_FIXTURE", "evidence_refs": ("evidence-001",),
    }
    capture = ApprovedNewsCaptureV1(**capture_fields, capture_id=_json_hash({key: value for key, value in capture_fields.items() if key not in {"capture_id", "normalized_payload_hash"}}))
    projection = Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1", projection_id="projection-001", production_evaluation_id="evaluation-001",
        event_id=event_id, candidate_id="candidate-001", disposition="NO_TRADE", reason_codes=("NO_ELIGIBLE_SETUP",),
        evidence_refs=("control-evidence-001",), evaluated_at="2026-07-17T00:03:00Z", source_artifact_hash="1" * 64,
    )
    return ShadowEvaluationInputV1(
        schema_version="shadow-evaluation-input-v1", shadow_input_id="shadow-input-001", approved_news_capture=capture,
        phase_09_control_projection=projection, sample_plan_id="sample-plan-001", policy_version="phase11-policy-v1",
        created_at="2026-07-17T00:04:00Z",
    )


def _runtime_invocation(maximum_attempts: int) -> ShadowProviderInvocationV1:
    event, request = _deepseek_payload()
    policy = Phase11BudgetPolicyV1(
        schema_version="phase11-budget-policy-v1", policy_id="current-runtime-policy-001", policy_version=1, status="ACTIVE",
        currency="USD_MICRO", total_cost_cap=Decimal("1000000"),
        provider_cost_caps={"DEEPSEEK": Decimal("500000"), "ANTHROPIC": Decimal("500000")},
        model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("500000"), "CLAUDE_SONNET_L1": Decimal("300000"), "CLAUDE_OPUS_L2": Decimal("300000")},
        per_run_cost_cap=Decimal("100000"), maximum_call_count=100, maximum_calls_per_run=10,
        maximum_input_tokens=100000, maximum_output_tokens=100000, maximum_tokens_per_call=10000,
        allowed_providers=("DEEPSEEK", "ANTHROPIC"), allowed_models=("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2"),
        starts_at="2026-07-17T00:00:00Z", ends_at="2026-07-18T00:00:00Z", owner_approval_reference="owner-approval-001",
        stop_conditions=("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    )
    reservations = tuple(
        BudgetReservationV1(
            schema_version="phase11-budget-reservation-v1", reservation_id=f"current-runtime-reservation-{number}",
            policy_id=policy.policy_id, run_id="current-runtime-run-001", call_id=f"current-runtime-call-{number}",
            provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", reserved_cost=Decimal("1000"),
            reserved_input_tokens=100, reserved_output_tokens=200, reserved_at="2026-07-17T00:05:00Z",
            expires_at="2026-07-17T02:00:00Z", status="RESERVED", reason_codes=("ROUTE_RESERVATION",),
        ) for number in range(1, maximum_attempts + 1)
    )
    ledger = BudgetLedgerV1(policy=policy, circuit_or_stop_state="OPEN")
    for reservation in reservations:
        ledger = ledger.reserve_call(reservation)
    first = reservations[0]
    shadow_input = _shadow_input(event.event_snapshot_id)
    return ShadowProviderInvocationV1(
        schema_version="phase11-shadow-provider-invocation-v1", invocation_id=None, execution_id="current-runtime-execution-001",
        run_id=first.run_id, call_id=first.call_id, route="L0", provider="DEEPSEEK", model="DEEPSEEK_PRIMARY",
        prompt_version="phase11-prompt-v1", provider_review_schema_version="phase10-review-schema-v1", shadow_input=shadow_input,
        shadow_input_identity=shadow_input.identity, event_id=event.event_snapshot_id, event_version=1, budget_ledger=ledger,
        budget_policy_id=policy.policy_id, reservation=first, reservation_id=first.identity, attempt_reservations=reservations,
        review_request=request, request_hash=request.payload_sha256, timeout_ms=1000, maximum_attempts=maximum_attempts,
        circuit_state="CLOSED", requested_at="2026-07-17T00:05:30Z", reason_codes=("CURRENT_RUNTIME_INTEGRITY",),
        production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
    )


def _success_response(request: object) -> dict[str, object]:
    values = dict(request)
    response = {
        "outcome": "SUCCESS", "provider": values["provider"], "model": values["model"], "invocation_id": values["invocation_id"],
        "attempt_reservation_id": values["attempt_reservation_id"], "attempt_count": values["attempt_number"],
        "request_hash": values["request_hash"], "prompt_version": "phase11-prompt-v1", "provider_review_schema_version": "phase10-review-schema-v1",
        "provider_review_identity": "2" * 64, "structured_verdict": {"verdict": "NO_TRADE"}, "reason_codes": ("COMPLETED",),
        "input_tokens": 80, "output_tokens": 120, "estimated_cost": Decimal("900"), "actual_cost": Decimal("850"),
        "started_at": "2026-07-17T00:06:00Z", "completed_at": "2026-07-17T00:06:01Z", "latency_ms": 1000,
        "provider_timestamp": "2026-07-17T00:06:01Z",
    }
    return {**response, "response_hash": lowercase_sha256(response)}


class _CounterTransport:
    def __init__(self, behavior: str) -> None:
        self.behavior = behavior
        self.calls: list[tuple[object, int]] = []

    def __call__(self, request: object, timeout_ms: int) -> object:
        self.calls.append((request, timeout_ms))
        if self.behavior == "TIMEOUT_EXCEPTION":
            raise TimeoutError("deterministic timeout")
        if self.behavior == "TRANSPORT_EXCEPTION":
            raise ConnectionError("deterministic transport failure")
        if self.behavior == "AUTHENTICATION_REJECTED":
            return {"outcome": AdapterFailureV1.AUTHENTICATION_REJECTED.value}
        if self.behavior == "UNRECOGNIZED_NORMALIZED_OUTCOME":
            return {"outcome": "UNRECOGNIZED_NORMALIZED_OUTCOME"}
        assert self.behavior == "SUCCESS_RESPONSE"
        return _success_response(request)


def _run_current_probe(kind: ShadowPhase11CurrentRuntimeIntegrityProbeKindV1, maximum_attempts: int = 1):
    behavior = {
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.SUCCESS: "SUCCESS_RESPONSE",
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TIMEOUT: "TIMEOUT_EXCEPTION",
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TRANSPORT_FAILURE: "TRANSPORT_EXCEPTION",
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.AUTHENTICATION_REJECTED: "AUTHENTICATION_REJECTED",
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.UNKNOWN_NORMALIZED_OUTCOME: "UNRECOGNIZED_NORMALIZED_OUTCOME",
    }[kind]
    transport = _CounterTransport(behavior)
    return transport, ShadowProviderRuntimeV1(transport=transport).invoke(_runtime_invocation(maximum_attempts))


def _probe(kind: ShadowPhase11CurrentRuntimeIntegrityProbeKindV1 = ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.SUCCESS, **overrides: object) -> ShadowPhase11CurrentRuntimeIntegrityProbeResultV1:
    mapping = {
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.SUCCESS: ("SUCCESS_RESPONSE", None, TransportOutcomeV1.SUCCESS, None, False, False, False),
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TIMEOUT: ("TIMEOUT_EXCEPTION", None, TransportOutcomeV1.TIMEOUT, RuntimeFailureV1.TIMEOUT, True, False, False),
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TRANSPORT_FAILURE: ("TRANSPORT_EXCEPTION", None, TransportOutcomeV1.TRANSPORT_FAILURE, RuntimeFailureV1.TRANSPORT_FAILURE, True, False, False),
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.AUTHENTICATION_REJECTED: ("AUTHENTICATION_REJECTED", AdapterFailureV1.AUTHENTICATION_REJECTED, TransportOutcomeV1.AUTHENTICATION_FAILURE, RuntimeFailureV1.AUTHENTICATION_FAILURE, False, False, True),
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.UNKNOWN_NORMALIZED_OUTCOME: ("UNRECOGNIZED_NORMALIZED_OUTCOME", None, TransportOutcomeV1.MALFORMED_RESPONSE, RuntimeFailureV1.MALFORMED_RESPONSE, False, True, False),
    }
    category, adapter_failure, outcome, failure, retryable, fallback, auth_mapping = mapping[kind]
    fields = {
        "schema_version": "phase11-shadow-pilot-current-runtime-integrity-probe-result-v1", "probe_id": None,
        "probe_kind": kind, "normalized_input_category": category, "adapter_failure": adapter_failure,
        "runtime_outcome": outcome, "runtime_failure": failure, "configured_maximum_attempts": 1,
        "observed_transport_invocation_count": 1, "observed_runtime_attempt_count": 1,
        "terminal_for_configured_profile": True, "retryable_under_generic_runtime_behavior": retryable,
        "second_transport_invocation_observed": False, "retry_delay_observed": False,
        "generic_fallback_observed": fallback, "authentication_terminal_mapping_observed": auth_mapping,
        "network_access_observed": False, "credential_access_observed": False, "environment_access_observed": False,
        "account_access_observed": False, "billing_access_observed": False, "ledger_mutation_observed": False,
        "reservation_creation_observed": False, "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE",
        "reason_codes": ("CURRENT_RUNTIME_PROBE",),
    }
    fields.update(overrides)
    return ShadowPhase11CurrentRuntimeIntegrityProbeResultV1(**fields)


def _reject_probe(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11CurrentRuntimeIntegrityValidationError):
        _probe(**overrides)


def _evidence(**overrides: object) -> ShadowPhase11CurrentRuntimeIntegrityEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    predecessor = get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-current-runtime-integrity-evidence-v1", "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE, "credential_safe_gate_reference": gate.evidence_reference,
        "credential_safe_gate_identity": gate.identity, "predecessor_evidence_reference": predecessor.evidence_reference,
        "predecessor_evidence_identity": predecessor.identity,
        "predecessor_status": ShadowPhase11CurrentRuntimePredecessorStatusV1.HISTORICAL_PREDECESSOR_ONLY,
        "predecessor_current_source_authority": False, "locked_repository_baseline": LOCKED_REPOSITORY_BASELINE,
        "locked_phase09_baseline": LOCKED_PHASE09_BASELINE, "adapter_source_path": ADAPTER_PATH,
        "adapter_source_sha256": ADAPTER_SHA256, "adapter_git_blob_identity": ADAPTER_BLOB,
        "adapter_source_byte_length": ADAPTER_BYTES, "adapter_failure_enum_name": "AdapterFailureV1",
        "adapter_terminal_boundary_name": "_TERMINAL_OUTCOMES", "runtime_source_path": RUNTIME_PATH,
        "runtime_source_sha256": RUNTIME_SHA256, "runtime_git_blob_identity": RUNTIME_BLOB,
        "runtime_source_byte_length": RUNTIME_BYTES, "runtime_outcome_enum_name": "TransportOutcomeV1",
        "runtime_failure_enum_name": "RuntimeFailureV1", "runtime_class_name": "ShadowProviderRuntimeV1",
        "runtime_invocation_method": "invoke",
        "integrity_state": ShadowPhase11CurrentRuntimeIntegrityStateV1.VERIFIED_CURRENT_ADAPTER_AND_RUNTIME_FOR_PILOT_PROFILE,
        "pilot_maximum_attempts": 1, "runtime_one_attempt_no_retry_verified": True,
        "authentication_terminal_classification_verified": True, "generic_unknown_fallback_verified": True,
        "generic_timeout_retry_capability_preserved": True, "generic_transport_failure_retry_capability_preserved": True,
        "generic_runtime_retry_capability_removed": False, "authentication_above_one_configured_maximum_attempts": 2,
        "authentication_above_one_observed_transport_invocation_count": 1,
        "authentication_above_one_observed_runtime_attempt_count": 1,
        "authentication_above_one_second_transport_invocation_observed": False,
        "authentication_above_one_retry_delay_observed": False,
        "probe_results": tuple(_probe(kind) for kind in ShadowPhase11CurrentRuntimeIntegrityProbeKindV1),
        "credential_configuration_verified": False, "pricing_revalidation_completed": False,
        "pre_call_reservation_created": False, "pilot_input_present": False, "run_manifest_present": False,
        "provider_call_authorized": False, "provider_transmission_authorized": False,
        "reservation_creation_authorized": False, "ledger_mutation_authorized": False,
        "run_size_authorized": False, "launch_authorized": False, "production_authorized": False,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE",
        "reason_codes": ("CURRENT_SOURCE_INTEGRITY_VERIFIED",),
    }
    fields.update(overrides)
    return ShadowPhase11CurrentRuntimeIntegrityEvidenceV1(**fields)


def _reject_evidence(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11CurrentRuntimeIntegrityValidationError):
        _evidence(**overrides)


def test_closed_current_integrity_enums_and_predecessor_state_are_exact():
    assert tuple(ShadowPhase11CurrentRuntimeIntegrityStateV1) == (ShadowPhase11CurrentRuntimeIntegrityStateV1.VERIFIED_CURRENT_ADAPTER_AND_RUNTIME_FOR_PILOT_PROFILE,)
    assert tuple(ShadowPhase11CurrentRuntimePredecessorStatusV1) == (ShadowPhase11CurrentRuntimePredecessorStatusV1.HISTORICAL_PREDECESSOR_ONLY,)
    assert tuple(ShadowPhase11CurrentRuntimeIntegrityProbeKindV1) == (
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.SUCCESS,
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TIMEOUT,
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TRANSPORT_FAILURE,
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.AUTHENTICATION_REJECTED,
        ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.UNKNOWN_NORMALIZED_OUTCOME,
    )


@pytest.mark.parametrize(
    ("kind", "expected_outcome", "expected_failure"),
    (
        (ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.SUCCESS, TransportOutcomeV1.SUCCESS, None),
        (ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TIMEOUT, TransportOutcomeV1.TIMEOUT, RuntimeFailureV1.TIMEOUT),
        (ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TRANSPORT_FAILURE, TransportOutcomeV1.TRANSPORT_FAILURE, RuntimeFailureV1.TRANSPORT_FAILURE),
        (ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.AUTHENTICATION_REJECTED, TransportOutcomeV1.AUTHENTICATION_FAILURE, RuntimeFailureV1.AUTHENTICATION_FAILURE),
        (ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.UNKNOWN_NORMALIZED_OUTCOME, TransportOutcomeV1.MALFORMED_RESPONSE, RuntimeFailureV1.MALFORMED_RESPONSE),
    ),
)
def test_current_runtime_deterministic_one_attempt_probes(kind, expected_outcome, expected_failure):
    transport, result = _run_current_probe(kind)
    assert len(transport.calls) == result.attempt_count == 1
    assert result.transport_outcome == expected_outcome.value
    assert result.failure_class == ("NONE" if expected_failure is None else expected_failure.value)
    assert result.retry_state == "NO_RETRY"
    probe = _probe(kind)
    assert probe.observed_transport_invocation_count == probe.observed_runtime_attempt_count == 1
    assert probe.second_transport_invocation_observed is False and probe.retry_delay_observed is False


def test_authentication_is_terminal_with_existing_generic_maximum_attempts_two():
    transport, result = _run_current_probe(ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.AUTHENTICATION_REJECTED, 2)
    assert len(transport.calls) == result.attempt_count == 1
    assert result.transport_outcome == TransportOutcomeV1.AUTHENTICATION_FAILURE.value
    assert result.failure_class == RuntimeFailureV1.AUTHENTICATION_FAILURE.value
    assert result.retry_state == "NO_RETRY"


def test_probe_contract_rejects_mapping_count_access_and_authority_tampering():
    _reject_probe(probe_kind="UNKNOWN")
    _reject_probe(runtime_outcome=TransportOutcomeV1.AUTHENTICATION_FAILURE)
    _reject_probe(adapter_failure=AdapterFailureV1.AUTHENTICATION_REJECTED)
    for name, value in (
        ("configured_maximum_attempts", 2), ("observed_transport_invocation_count", 0),
        ("observed_runtime_attempt_count", 2), ("second_transport_invocation_observed", True),
        ("retry_delay_observed", True), ("network_access_observed", True),
        ("credential_access_observed", True), ("environment_access_observed", True),
        ("account_access_observed", True), ("billing_access_observed", True),
        ("ledger_mutation_observed", True), ("reservation_creation_observed", True),
        ("production_effect", "SENT"), ("zero_production_effect_proof", "UNPROVEN"),
    ):
        _reject_probe(**{name: value})
    _reject_probe(probe_id="0" * 64)
    _reject_probe(unknown_field="reject")


def test_successor_evidence_links_current_sources_gate_and_historical_predecessor_only():
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    predecessor = get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1()
    evidence = _evidence()
    assert evidence.credential_safe_gate_reference == gate.evidence_reference == GATE_REFERENCE
    assert evidence.credential_safe_gate_identity == gate.identity == GATE_IDENTITY
    assert evidence.predecessor_evidence_reference == predecessor.evidence_reference == PREDECESSOR_REFERENCE
    assert evidence.predecessor_evidence_identity == predecessor.identity == PREDECESSOR_IDENTITY
    assert evidence.predecessor_status is ShadowPhase11CurrentRuntimePredecessorStatusV1.HISTORICAL_PREDECESSOR_ONLY
    assert evidence.predecessor_current_source_authority is False
    assert evidence.adapter_source_sha256 == ADAPTER_SHA256 and evidence.runtime_source_sha256 == RUNTIME_SHA256
    assert evidence.adapter_source_byte_length == ADAPTER_BYTES and evidence.runtime_source_byte_length == RUNTIME_BYTES
    assert tuple(item.probe_kind for item in evidence.probe_results) == tuple(ShadowPhase11CurrentRuntimeIntegrityProbeKindV1)
    assert evidence.authentication_above_one_configured_maximum_attempts == 2
    assert evidence.authentication_above_one_observed_transport_invocation_count == 1
    assert evidence.authentication_above_one_observed_runtime_attempt_count == 1


def test_evidence_rejects_identity_metadata_probe_policy_and_authority_tampering():
    for name, value in (
        ("credential_safe_gate_reference", "OTHER_GATE"), ("credential_safe_gate_identity", "0" * 64),
        ("predecessor_evidence_reference", "OTHER_PREDECESSOR"), ("predecessor_evidence_identity", "0" * 64),
        ("predecessor_status", "CURRENT"), ("predecessor_current_source_authority", True),
        ("locked_repository_baseline", "0" * 40), ("locked_phase09_baseline", "0" * 40),
        ("adapter_source_path", "engine/other.py"), ("adapter_source_sha256", "0" * 64),
        ("adapter_git_blob_identity", "0" * 40), ("adapter_source_byte_length", 1),
        ("adapter_failure_enum_name", "OtherEnum"), ("adapter_terminal_boundary_name", "OTHER_SET"),
        ("runtime_source_path", "engine/other.py"), ("runtime_source_sha256", "0" * 64),
        ("runtime_git_blob_identity", "0" * 40), ("runtime_source_byte_length", 1),
        ("runtime_outcome_enum_name", "OtherEnum"), ("runtime_failure_enum_name", "OtherFailure"),
        ("runtime_class_name", "OtherRuntime"), ("runtime_invocation_method", "run"),
        ("integrity_state", "GLOBAL"), ("pilot_maximum_attempts", 2),
        ("runtime_one_attempt_no_retry_verified", False), ("authentication_terminal_classification_verified", False),
        ("generic_unknown_fallback_verified", False), ("generic_timeout_retry_capability_preserved", False),
        ("generic_transport_failure_retry_capability_preserved", False), ("generic_runtime_retry_capability_removed", True),
        ("authentication_above_one_configured_maximum_attempts", 1),
        ("authentication_above_one_observed_transport_invocation_count", 2),
        ("authentication_above_one_observed_runtime_attempt_count", 2),
        ("authentication_above_one_second_transport_invocation_observed", True),
        ("authentication_above_one_retry_delay_observed", True),
        ("credential_configuration_verified", True), ("pricing_revalidation_completed", True),
        ("pre_call_reservation_created", True), ("pilot_input_present", True), ("run_manifest_present", True),
        ("launch_readiness", "READY_FOR_LAUNCH"), ("production_effect", "SENT"), ("zero_production_effect_proof", "UNPROVEN"),
    ):
        _reject_evidence(**{name: value})
    for name in ("provider_call_authorized", "provider_transmission_authorized", "reservation_creation_authorized", "ledger_mutation_authorized", "run_size_authorized", "launch_authorized", "production_authorized"):
        _reject_evidence(**{name: True})
    probes = _evidence().probe_results
    _reject_evidence(probe_results=probes[:4])
    _reject_evidence(probe_results=probes + (probes[0],))
    _reject_evidence(evidence_id="0" * 64)
    _reject_evidence(unknown_field="reject")


def test_probe_reason_order_converges_material_changes_diverge_and_accessor_is_stable():
    probes = _evidence().probe_results
    first = _evidence(probe_results=probes, reason_codes=("A_REASON", "Z_REASON"))
    second = _evidence(probe_results=tuple(reversed(probes)), reason_codes=("Z_REASON", "A_REASON"))
    variant = _evidence(reason_codes=("MATERIAL_VARIANT",))
    assert first.identity == second.identity and first.identity != variant.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    assert sha256_hex(b"current-runtime-integrity") == hashlib.sha256(b"current-runtime-integrity").hexdigest()
    concrete = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    assert type(concrete) is ShadowPhase11CurrentRuntimeIntegrityEvidenceV1
    assert concrete.identity == get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1().identity == _evidence().identity
    assert concrete.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH


def test_current_runtime_retry_boundary_and_future_static_side_effect_boundary():
    runtime_tree = ast.parse(Path(RUNTIME_PATH).read_text(encoding="utf-8"))
    retryable = next(node.value for node in ast.walk(runtime_tree) if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "retryable" for target in node.targets))
    assert {item.value for item in retryable.elts} == {"TIMEOUT", "TRANSPORT_FAILURE"}
    module = ast.parse(Path(FUTURE_PATH).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "keyring", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "material_for_adapter", "ShadowProviderRuntimeV1", "DeepSeekShadowTransportAdapterV1", "AnthropicShadowTransportAdapterV1", "reserve_call", "commit_usage", "sleep", "wait", "float"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules and not names & forbidden_names
