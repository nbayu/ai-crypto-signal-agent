"""RED contract for Phase 11 pilot-profile runtime one-attempt evidence.

The probes deliberately exercise the existing injected runtime only with
in-memory fixtures.  They prove a locked *pilot profile* cannot retry; they
do not remove generic runtime retry support or grant any execution authority.
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
from engine.phase_11_budget_control_v1 import (
    BudgetLedgerV1,
    BudgetReservationV1,
    Phase11BudgetPolicyV1,
)
from engine.phase_11_shadow_input_contracts_v1 import (
    ApprovedNewsCaptureV1,
    Phase09ControlProjectionV1,
    ShadowEvaluationInputV1,
)
from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotProviderRoleV1,
)
from engine.phase_11_shadow_provider_runtime_v1 import (
    ShadowProviderInvocationV1,
    ShadowProviderRuntimeV1,
    TransportOutcomeV1,
    lowercase_sha256,
)
from engine.phase_11_shadow_pilot_runtime_no_retry_enforcement_v1 import (
    ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1,
    ShadowPhase11RuntimeNoRetryEnforcementStateV1,
    ShadowPhase11RuntimeNoRetryEnforcementValidationError,
    ShadowPhase11RuntimeNoRetryProbeKindV1,
    ShadowPhase11RuntimeNoRetryProbeResultV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1,
    sha256_hex,
)


UTC = timezone.utc
LOCKED_REPOSITORY_BASELINE = "f4ff152d10c18cb41488c963eeb27c7db973f79a"
LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_RUNTIME_NO_RETRY_ENFORCEMENT_001"
GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
GATE_IDENTITY = "77b7bbb6782a4710b04abd16547ba5fd94e8311d09cad0cd0187fc7b8313c06b"
RUNTIME_PATH = "engine/phase_11_shadow_provider_runtime_v1.py"
RUNTIME_SHA256 = "853bd420bef56bd560abf2e65baccc8e33f17d549bfd60a4b4ace5917b56cf38"
RUNTIME_BLOB_ID = "572a6716836e723287b4aa2a835ed985378fbf6a"
RUNTIME_CLASS = "ShadowProviderRuntimeV1"
RUNTIME_METHOD = "invoke"
ZERO = Decimal("0")


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _event() -> NormalizedNewsEventV1:
    return NormalizedNewsEventV1(
        event_namespace="news", authoritative_source_namespace="fixture-wire",
        authoritative_source_event_id="runtime-no-retry-001",
        deterministic_source_key=None, normalized_primary_subject="asset:alpha",
        canonical_event_class="PROTOCOL_UPDATE", normalized_title="Runtime fixture",
        normalized_body="Deterministic runtime fixture.", normalized_language="en-US",
        publication_timestamp_utc=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
        point_in_time_timestamp_utc=datetime(2026, 7, 16, 12, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fixture"}, previous_event_version_id=None,
        event_version_number=1,
        source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        schema_version=EVENT_SCHEMA_VERSION,
    )


def _deepseek_payload() -> tuple[NormalizedNewsEventV1, DeepSeekReviewPayloadV1]:
    event = _event()
    source = SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1", decision="ELIGIBLE",
        primary_reason_code="SOURCE_ELIGIBLE", reason_codes=("SOURCE_ELIGIBLE",),
        evaluated_source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        evaluation_timestamp_utc=datetime(2026, 7, 16, 12, 30, tzinfo=UTC),
        source_namespace="fixture-wire", source_id="source-001",
    )
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha", entity_type="DIGITAL_ASSET",
        canonical_entity_id="asset:alpha", canonical_name="Alpha", canonical_symbol="ALPHA",
        source_text="Alpha", source_text_sha256=_text_hash("Alpha"),
        evidence_refs=[{"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id,
                        "reference_type": "EVENT_FIELD", "field_name": "normalized_title"}],
        confidence_basis="EXPLICIT_CALLER_ASSERTION", supplied_confidence=None,
        ambiguity_group_id=None, candidate_status="ACCEPTED", rejection_reason_codes=[],
        mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    mapping = map_entity_candidates(
        event_snapshot_id=event.event_snapshot_id, source_policy_decision=source,
        candidates=[candidate],
    )
    token_policy = PayloadTokenPolicyV1(
        claude_input_hard_limit_tokens=8000, claude_target_input_min_tokens=2000,
        claude_target_input_max_tokens=5000, claude_output_hard_limit_tokens=1000,
        maximum_claude_logical_reviews_per_event=1, maximum_provider_attempts_per_review=2,
        maximum_retry_count=1,
    )
    payloads = project_ai_review_payloads(
        normalized_event=event, source_policy_decision=source, entity_mapping_result=mapping,
        bounded_evidence=({"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id,
                           "source_field": "normalized_body", "excerpt": event.normalized_body,
                           "excerpt_sha256": _text_hash(event.normalized_body)},),
        review_task="Assess deterministic facts.", token_policy=token_policy,
        token_counter=lambda _: 100,
    )
    return event, payloads.deepseek_payload


def _shadow_input(event_id: str) -> ShadowEvaluationInputV1:
    payload = {"event_class": "FIXTURE", "headline": "No retry"}
    capture_values = {
        "schema_version": "approved-news-capture-v1", "event_id": event_id,
        "event_version": 1, "source_id": "source-001", "source_type": "REGULATED_FEED",
        "source_timestamp": "2026-07-17T00:00:00Z", "captured_at": "2026-07-17T00:01:00Z",
        "point_in_time_cutoff": "2026-07-17T00:02:00Z", "normalized_payload": payload,
        "normalized_payload_hash": _json_hash(payload),
        "event_lineage": ({"event_id": event_id, "event_version": 1, "relation": "ORIGIN"},),
        "capture_classification": "FIXTURE", "content_origin": "SYNTHETIC_FIXTURE",
        "evidence_refs": ("evidence-001",),
    }
    capture = ApprovedNewsCaptureV1(
        **capture_values,
        capture_id=_json_hash({key: value for key, value in capture_values.items()
                               if key not in {"capture_id", "normalized_payload_hash"}}),
    )
    projection = Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1", projection_id="projection-001",
        production_evaluation_id="evaluation-001", event_id=event_id,
        candidate_id="candidate-001", disposition="NO_TRADE",
        reason_codes=("NO_ELIGIBLE_SETUP",), evidence_refs=("control-evidence-001",),
        evaluated_at="2026-07-17T00:03:00Z", source_artifact_hash="1" * 64,
    )
    return ShadowEvaluationInputV1(
        schema_version="shadow-evaluation-input-v1", shadow_input_id="shadow-input-001",
        approved_news_capture=capture, phase_09_control_projection=projection,
        sample_plan_id="sample-plan-001", policy_version="phase11-policy-v1",
        created_at="2026-07-17T00:04:00Z",
    )


def _runtime_invocation() -> ShadowProviderInvocationV1:
    event, request = _deepseek_payload()
    policy = Phase11BudgetPolicyV1(
        schema_version="phase11-budget-policy-v1", policy_id="runtime-policy-001",
        policy_version=1, status="ACTIVE", currency="USD_MICRO",
        total_cost_cap=Decimal("1000000"),
        provider_cost_caps={"DEEPSEEK": Decimal("500000"), "ANTHROPIC": Decimal("500000")},
        model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("500000"),
                         "CLAUDE_SONNET_L1": Decimal("300000"),
                         "CLAUDE_OPUS_L2": Decimal("300000")},
        per_run_cost_cap=Decimal("100000"), maximum_call_count=100,
        maximum_calls_per_run=10, maximum_input_tokens=100000,
        maximum_output_tokens=100000, maximum_tokens_per_call=10000,
        allowed_providers=("DEEPSEEK", "ANTHROPIC"),
        allowed_models=("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2"),
        starts_at="2026-07-17T00:00:00Z", ends_at="2026-07-18T00:00:00Z",
        owner_approval_reference="owner-approval-001",
        stop_conditions=("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    )
    reservation = BudgetReservationV1(
        schema_version="phase11-budget-reservation-v1", reservation_id="runtime-reservation-001",
        policy_id=policy.policy_id, run_id="runtime-run-001", call_id="runtime-call-001",
        provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", reserved_cost=Decimal("1000"),
        reserved_input_tokens=100, reserved_output_tokens=200,
        reserved_at="2026-07-17T00:05:00Z", expires_at="2026-07-17T02:00:00Z",
        status="RESERVED", reason_codes=("ROUTE_RESERVATION",),
    )
    # BudgetLedgerV1 is an immutable test fixture; no external ledger is used.
    ledger = BudgetLedgerV1(policy=policy, circuit_or_stop_state="OPEN").reserve_call(reservation)
    return ShadowProviderInvocationV1(
        schema_version="phase11-shadow-provider-invocation-v1", invocation_id=None,
        execution_id="runtime-execution-001", run_id=reservation.run_id,
        call_id=reservation.call_id, route="L0", provider="DEEPSEEK",
        model="DEEPSEEK_PRIMARY", prompt_version="phase11-prompt-v1",
        provider_review_schema_version="phase10-review-schema-v1",
        shadow_input=_shadow_input(event.event_snapshot_id),
        shadow_input_identity=_shadow_input(event.event_snapshot_id).identity,
        event_id=event.event_snapshot_id, event_version=1, budget_ledger=ledger,
        budget_policy_id=policy.policy_id, reservation=reservation,
        reservation_id=reservation.identity, attempt_reservations=(reservation,),
        review_request=request, request_hash=request.payload_sha256, timeout_ms=1000,
        maximum_attempts=1, circuit_state="CLOSED", requested_at="2026-07-17T00:05:30Z",
        reason_codes=("PILOT_ONE_ATTEMPT",), production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


class _CounterTransport:
    def __init__(self, behavior: str) -> None:
        self.behavior = behavior
        self.calls: list[tuple[object, int]] = []

    def __call__(self, request: object, timeout_ms: int) -> object:
        self.calls.append((request, timeout_ms))
        if self.behavior == "TIMEOUT":
            raise TimeoutError("deterministic timeout")
        if self.behavior == "TRANSPORT_FAILURE":
            raise ConnectionError("deterministic transport failure")
        assert self.behavior == "SUCCESS"
        return _success_response(request)


def _success_response(request: object) -> dict[str, object]:
    mapping = dict(request)
    response = {
        "outcome": "SUCCESS", "provider": mapping["provider"], "model": mapping["model"],
        "invocation_id": mapping["invocation_id"],
        "attempt_reservation_id": mapping["attempt_reservation_id"],
        "attempt_count": mapping["attempt_number"], "request_hash": mapping["request_hash"],
        "prompt_version": "phase11-prompt-v1", "provider_review_schema_version": "phase10-review-schema-v1",
        "provider_review_identity": "2" * 64, "structured_verdict": {"verdict": "NO_TRADE"},
        "reason_codes": ("COMPLETED",), "input_tokens": 80, "output_tokens": 120,
        "estimated_cost": Decimal("900"), "actual_cost": Decimal("850"),
        "started_at": "2026-07-17T00:06:00Z", "completed_at": "2026-07-17T00:06:01Z",
        "latency_ms": 1000, "provider_timestamp": "2026-07-17T00:06:01Z",
    }
    return {**response, "response_hash": lowercase_sha256(response)}


def _probe_runtime(kind: ShadowPhase11RuntimeNoRetryProbeKindV1):
    behavior = {
        ShadowPhase11RuntimeNoRetryProbeKindV1.SUCCESS: "SUCCESS",
        ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TIMEOUT: "TIMEOUT",
        ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TRANSPORT_FAILURE: "TRANSPORT_FAILURE",
    }[kind]
    transport = _CounterTransport(behavior)
    result = ShadowProviderRuntimeV1(transport=transport).invoke(_runtime_invocation())
    return transport, result


def _probe(kind: ShadowPhase11RuntimeNoRetryProbeKindV1 = ShadowPhase11RuntimeNoRetryProbeKindV1.SUCCESS,
           **overrides: object) -> ShadowPhase11RuntimeNoRetryProbeResultV1:
    outcome = {
        ShadowPhase11RuntimeNoRetryProbeKindV1.SUCCESS: TransportOutcomeV1.SUCCESS,
        ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TIMEOUT: TransportOutcomeV1.TIMEOUT,
        ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TRANSPORT_FAILURE: TransportOutcomeV1.TRANSPORT_FAILURE,
    }.get(kind, TransportOutcomeV1.SUCCESS)
    values = {
        "schema_version": "phase11-shadow-pilot-runtime-no-retry-probe-result-v1",
        "probe_id": None, "probe_kind": kind, "provider": "DEEPSEEK",
        "role": ShadowPhase11PilotProviderRoleV1.PRIMARY, "runtime_outcome": outcome,
        "configured_maximum_attempts": 1, "observed_transport_invocation_count": 1,
        "observed_attempt_count": 1, "second_transport_invocation_observed": False,
        "retry_delay_observed": False, "network_access_observed": False,
        "credential_access_observed": False, "account_access_observed": False,
        "ledger_mutation_observed": False, "reservation_creation_observed": False,
        "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE",
        "reason_codes": ("ONE_ATTEMPT_NO_RETRY",),
    }
    values.update(overrides)
    return ShadowPhase11RuntimeNoRetryProbeResultV1(**values)


def _reject_probe(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11RuntimeNoRetryEnforcementValidationError):
        _probe(**overrides)


def _evidence(**overrides: object) -> ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    values = {
        "schema_version": "phase11-shadow-pilot-runtime-no-retry-enforcement-v1",
        "evidence_id": None, "evidence_reference": EVIDENCE_REFERENCE,
        "credential_safe_gate_reference": gate.evidence_reference,
        "credential_safe_gate_identity": gate.identity,
        "locked_repository_baseline": LOCKED_REPOSITORY_BASELINE,
        "locked_phase09_baseline": LOCKED_PHASE09_BASELINE,
        "runtime_source_path": RUNTIME_PATH, "runtime_source_sha256": RUNTIME_SHA256,
        "runtime_git_blob_identity": RUNTIME_BLOB_ID, "runtime_class_name": RUNTIME_CLASS,
        "runtime_invocation_method": RUNTIME_METHOD,
        "enforcement_state": ShadowPhase11RuntimeNoRetryEnforcementStateV1.VERIFIED_ONE_ATTEMPT_NO_RETRY_FOR_PILOT_PROFILE,
        "pilot_maximum_attempts": gate.maximum_attempts,
        "provider_retry_authorized": gate.provider_retry_authorized,
        "credential_retry_authorized": gate.credential_retry_authorized,
        "authentication_retry_authorized": gate.authentication_retry_authorized,
        "runtime_no_retry_enforcement_verified": True,
        "generic_runtime_retry_capability_removed": False,
        "authentication_terminal_classification_verified": False,
        "credential_configuration_verified": False,
        "pricing_revalidation_completed": False, "pre_call_reservation_created": False,
        "pilot_input_present": False, "run_manifest_present": False,
        "provider_call_authorized": False, "provider_transmission_authorized": False,
        "reservation_creation_authorized": False, "ledger_mutation_authorized": False,
        "run_size_authorized": False, "launch_authorized": False, "production_authorized": False,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "probe_results": (
            _probe(ShadowPhase11RuntimeNoRetryProbeKindV1.SUCCESS),
            _probe(ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TIMEOUT),
            _probe(ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TRANSPORT_FAILURE),
        ),
        "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE",
        "reason_codes": ("PILOT_PROFILE_ONE_ATTEMPT_VERIFIED",),
    }
    values.update(overrides)
    return ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1(**values)


def _reject_evidence(**overrides: object) -> None:
    with pytest.raises(ShadowPhase11RuntimeNoRetryEnforcementValidationError):
        _evidence(**overrides)


def test_closed_enforcement_and_probe_enums_are_pilot_profile_only():
    assert tuple(ShadowPhase11RuntimeNoRetryEnforcementStateV1) == (
        ShadowPhase11RuntimeNoRetryEnforcementStateV1.VERIFIED_ONE_ATTEMPT_NO_RETRY_FOR_PILOT_PROFILE,
    )
    assert tuple(ShadowPhase11RuntimeNoRetryProbeKindV1) == (
        ShadowPhase11RuntimeNoRetryProbeKindV1.SUCCESS,
        ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TIMEOUT,
        ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TRANSPORT_FAILURE,
    )


@pytest.mark.parametrize(
    ("kind", "outcome"),
    (
        (ShadowPhase11RuntimeNoRetryProbeKindV1.SUCCESS, TransportOutcomeV1.SUCCESS),
        (ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TIMEOUT, TransportOutcomeV1.TIMEOUT),
        (ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TRANSPORT_FAILURE, TransportOutcomeV1.TRANSPORT_FAILURE),
    ),
)
def test_deterministic_in_memory_runtime_probes_invoke_transport_once(kind, outcome):
    transport, runtime_result = _probe_runtime(kind)
    assert len(transport.calls) == 1
    assert runtime_result.attempt_count == 1
    assert runtime_result.transport_outcome == outcome.value
    assert runtime_result.retry_state == "NO_RETRY"
    assert _probe(kind).runtime_outcome is outcome
    assert _probe(kind).observed_transport_invocation_count == 1
    assert _probe(kind).observed_attempt_count == 1
    assert _probe(kind).second_transport_invocation_observed is False
    assert _probe(kind).retry_delay_observed is False


def test_probe_constructor_rejects_counts_retry_delay_access_and_authority_tampering():
    _reject_probe(probe_kind="UNKNOWN")
    _reject_probe(runtime_outcome=TransportOutcomeV1.TIMEOUT)
    for name, value in (
        ("configured_maximum_attempts", 2),
        ("observed_transport_invocation_count", 0),
        ("observed_transport_invocation_count", 2),
        ("observed_attempt_count", 0), ("observed_attempt_count", 2),
        ("second_transport_invocation_observed", True), ("retry_delay_observed", True),
        ("network_access_observed", True), ("credential_access_observed", True),
        ("account_access_observed", True), ("ledger_mutation_observed", True),
        ("reservation_creation_observed", True), ("production_effect", "SENT"),
        ("zero_production_effect_proof", "UNPROVEN"),
    ):
        _reject_probe(**{name: value})
    _reject_probe(probe_id="0" * 64)
    _reject_probe(unknown_field="reject")


def test_concrete_evidence_links_gate_runtime_integrity_and_three_exact_probes():
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    evidence = _evidence()
    assert evidence.evidence_reference == EVIDENCE_REFERENCE
    assert evidence.credential_safe_gate_reference == gate.evidence_reference == GATE_REFERENCE
    assert evidence.credential_safe_gate_identity == gate.identity == GATE_IDENTITY
    assert evidence.locked_repository_baseline == LOCKED_REPOSITORY_BASELINE
    assert evidence.locked_phase09_baseline == LOCKED_PHASE09_BASELINE
    assert evidence.runtime_source_path == RUNTIME_PATH
    assert evidence.runtime_source_sha256 == RUNTIME_SHA256
    assert evidence.runtime_git_blob_identity == RUNTIME_BLOB_ID
    assert evidence.runtime_class_name == RUNTIME_CLASS
    assert evidence.runtime_invocation_method == RUNTIME_METHOD
    assert evidence.pilot_maximum_attempts == gate.maximum_attempts == 1
    assert evidence.enforcement_state is ShadowPhase11RuntimeNoRetryEnforcementStateV1.VERIFIED_ONE_ATTEMPT_NO_RETRY_FOR_PILOT_PROFILE
    assert tuple(item.probe_kind for item in evidence.probe_results) == tuple(ShadowPhase11RuntimeNoRetryProbeKindV1)
    assert evidence.runtime_no_retry_enforcement_verified is True
    assert evidence.generic_runtime_retry_capability_removed is False
    assert evidence.authentication_terminal_classification_verified is False


def test_evidence_rejects_source_gate_policy_probe_authority_and_state_tampering():
    for name, value in (
        ("credential_safe_gate_reference", "OTHER_GATE"),
        ("credential_safe_gate_identity", "0" * 64),
        ("locked_repository_baseline", "0" * 40),
        ("locked_phase09_baseline", "0" * 40),
        ("runtime_source_path", "engine/other.py"),
        ("runtime_source_sha256", "f" * 63),
        ("runtime_source_sha256", "0" * 64),
        ("runtime_git_blob_identity", "0" * 40),
        ("runtime_class_name", "OtherRuntime"),
        ("runtime_invocation_method", "run"),
        ("enforcement_state", "GLOBAL"), ("pilot_maximum_attempts", 0),
        ("pilot_maximum_attempts", 2), ("provider_retry_authorized", True),
        ("credential_retry_authorized", True), ("authentication_retry_authorized", True),
        ("runtime_no_retry_enforcement_verified", False),
        ("generic_runtime_retry_capability_removed", True),
        ("authentication_terminal_classification_verified", True),
        ("credential_configuration_verified", True), ("pricing_revalidation_completed", True),
        ("pre_call_reservation_created", True), ("pilot_input_present", True),
        ("run_manifest_present", True), ("launch_readiness", "READY_FOR_LAUNCH"),
        ("production_effect", "SENT"), ("zero_production_effect_proof", "UNPROVEN"),
    ):
        _reject_evidence(**{name: value})
    for name in (
        "provider_call_authorized", "provider_transmission_authorized",
        "reservation_creation_authorized", "ledger_mutation_authorized",
        "run_size_authorized", "launch_authorized", "production_authorized",
    ):
        _reject_evidence(**{name: True})
    probes = _evidence().probe_results
    _reject_evidence(probe_results=probes[:2])
    _reject_evidence(probe_results=probes + (probes[0],))
    _reject_evidence(evidence_id="0" * 64)
    _reject_evidence(unknown_field="reject")


def test_probe_and_reason_order_converge_while_valid_material_changes_diverge():
    probes = _evidence().probe_results
    first = _evidence(probe_results=probes, reason_codes=("A_REASON", "Z_REASON"))
    second = _evidence(probe_results=tuple(reversed(probes)), reason_codes=("Z_REASON", "A_REASON"))
    variant = _evidence(reason_codes=("MATERIAL_VARIANT",))
    assert first.identity == second.identity
    assert first.identity != variant.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    assert sha256_hex(b"runtime-one-attempt") == hashlib.sha256(b"runtime-one-attempt").hexdigest()


def test_zero_argument_accessor_is_deterministic_and_remains_non_authorizing():
    first = get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1()
    second = get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1()
    assert type(first) is ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1
    assert first.identity == second.identity == _evidence().identity
    assert not any((
        first.provider_call_authorized, first.provider_transmission_authorized,
        first.reservation_creation_authorized, first.ledger_mutation_authorized,
        first.run_size_authorized, first.launch_authorized, first.production_authorized,
    ))
    assert first.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert first.production_effect == "NONE"
    assert first.zero_production_effect_proof == "PROVEN_NONE"


def test_existing_runtime_retry_branch_is_generic_and_has_no_delay_or_sleep_call():
    source = Path(RUNTIME_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "number < invocation.maximum_attempts" in source
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not {"sleep", "wait"} & calls


def test_future_implementation_static_dependency_and_side_effect_boundary():
    module = ast.parse(Path("engine/phase_11_shadow_pilot_runtime_no_retry_enforcement_v1.py").read_text(encoding="utf-8"))
    forbidden_modules = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket",
        "subprocess", "threading", "multiprocessing", "concurrent", "asyncio",
        "pytest", "keyring", "boto3", "google", "azure", "ccxt",
    }
    forbidden_names = {
        "open", "getenv", "environ", "load_dotenv", "resolve_provider_credential",
        "material_for_adapter", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1",
        "DeepSeekShadowTransportAdapterV1", "AnthropicShadowTransportAdapterV1", "reserve_call",
        "commit_usage", "release_reservation", "telegram", "account", "exchange", "order",
        "position", "trading", "publication", "deployment", "persistence", "utcnow", "float",
    }
    imported = {node.module.split(".")[0] for node in ast.walk(module)
                if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module)
                 if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.With)) for node in ast.walk(module))
