"""RED contract for the sanitized Phase 11 authentication-classification seam.

This suite intentionally uses only an in-memory normalized transport outcome.
It neither constructs an adapter nor supplies credential material.  The future
change is constrained to the adapter and runtime vocabulary/mapping seam.
"""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

import engine.phase_11_provider_transport_adapters_v1 as adapter_module
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
from engine.phase_11_provider_transport_adapters_v1 import AdapterFailureV1
from engine.phase_11_shadow_input_contracts_v1 import (
    ApprovedNewsCaptureV1,
    Phase09ControlProjectionV1,
    ShadowEvaluationInputV1,
)
from engine.phase_11_shadow_provider_runtime_v1 import (
    ShadowProviderInvocationV1,
    ShadowProviderRuntimeV1,
    TransportOutcomeV1,
)


UTC = timezone.utc
ADAPTER_PATH = Path("engine/phase_11_provider_transport_adapters_v1.py")
RUNTIME_PATH = Path("engine/phase_11_shadow_provider_runtime_v1.py")
AUTHENTICATION_REJECTED = "AUTHENTICATION_REJECTED"
AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _event() -> NormalizedNewsEventV1:
    return NormalizedNewsEventV1(
        event_namespace="news",
        authoritative_source_namespace="fixture-wire",
        authoritative_source_event_id="authentication-seam-001",
        deterministic_source_key=None,
        normalized_primary_subject="asset:alpha",
        canonical_event_class="PROTOCOL_UPDATE",
        normalized_title="Authentication classification fixture",
        normalized_body="Deterministic sanitized fixture.",
        normalized_language="en-US",
        publication_timestamp_utc=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
        point_in_time_timestamp_utc=datetime(2026, 7, 16, 12, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fixture"},
        previous_event_version_id=None,
        event_version_number=1,
        source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        schema_version=EVENT_SCHEMA_VERSION,
    )


def _deepseek_payload() -> tuple[NormalizedNewsEventV1, DeepSeekReviewPayloadV1]:
    event = _event()
    source = SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1",
        decision="ELIGIBLE",
        primary_reason_code="SOURCE_ELIGIBLE",
        reason_codes=("SOURCE_ELIGIBLE",),
        evaluated_source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        evaluation_timestamp_utc=datetime(2026, 7, 16, 12, 30, tzinfo=UTC),
        source_namespace="fixture-wire",
        source_id="source-001",
    )
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha",
        entity_type="DIGITAL_ASSET",
        canonical_entity_id="asset:alpha",
        canonical_name="Alpha",
        canonical_symbol="ALPHA",
        source_text="Alpha",
        source_text_sha256=_text_hash("Alpha"),
        evidence_refs=[{
            "evidence_ref_id": "evidence-001",
            "event_snapshot_id": event.event_snapshot_id,
            "reference_type": "EVENT_FIELD",
            "field_name": "normalized_title",
        }],
        confidence_basis="EXPLICIT_CALLER_ASSERTION",
        supplied_confidence=None,
        ambiguity_group_id=None,
        candidate_status="ACCEPTED",
        rejection_reason_codes=[],
        mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    mapping = map_entity_candidates(
        event_snapshot_id=event.event_snapshot_id,
        source_policy_decision=source,
        candidates=[candidate],
    )
    token_policy = PayloadTokenPolicyV1(
        claude_input_hard_limit_tokens=8000,
        claude_target_input_min_tokens=2000,
        claude_target_input_max_tokens=5000,
        claude_output_hard_limit_tokens=1000,
        maximum_claude_logical_reviews_per_event=1,
        maximum_provider_attempts_per_review=2,
        maximum_retry_count=1,
    )
    payloads = project_ai_review_payloads(
        normalized_event=event,
        source_policy_decision=source,
        entity_mapping_result=mapping,
        bounded_evidence=({
            "evidence_ref_id": "evidence-001",
            "event_snapshot_id": event.event_snapshot_id,
            "source_field": "normalized_body",
            "excerpt": event.normalized_body,
            "excerpt_sha256": _text_hash(event.normalized_body),
        },),
        review_task="Assess deterministic sanitized facts.",
        token_policy=token_policy,
        token_counter=lambda _: 100,
    )
    return event, payloads.deepseek_payload


def _shadow_input(event_id: str) -> ShadowEvaluationInputV1:
    payload = {"event_class": "FIXTURE", "headline": "Authentication seam"}
    capture_values = {
        "schema_version": "approved-news-capture-v1",
        "event_id": event_id,
        "event_version": 1,
        "source_id": "source-001",
        "source_type": "REGULATED_FEED",
        "source_timestamp": "2026-07-17T00:00:00Z",
        "captured_at": "2026-07-17T00:01:00Z",
        "point_in_time_cutoff": "2026-07-17T00:02:00Z",
        "normalized_payload": payload,
        "normalized_payload_hash": _json_hash(payload),
        "event_lineage": ({"event_id": event_id, "event_version": 1, "relation": "ORIGIN"},),
        "capture_classification": "FIXTURE",
        "content_origin": "SYNTHETIC_FIXTURE",
        "evidence_refs": ("evidence-001",),
    }
    capture = ApprovedNewsCaptureV1(
        **capture_values,
        capture_id=_json_hash({
            key: value for key, value in capture_values.items()
            if key not in {"capture_id", "normalized_payload_hash"}
        }),
    )
    projection = Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1",
        projection_id="projection-001",
        production_evaluation_id="evaluation-001",
        event_id=event_id,
        candidate_id="candidate-001",
        disposition="NO_TRADE",
        reason_codes=("NO_ELIGIBLE_SETUP",),
        evidence_refs=("control-evidence-001",),
        evaluated_at="2026-07-17T00:03:00Z",
        source_artifact_hash="1" * 64,
    )
    return ShadowEvaluationInputV1(
        schema_version="shadow-evaluation-input-v1",
        shadow_input_id="shadow-input-001",
        approved_news_capture=capture,
        phase_09_control_projection=projection,
        sample_plan_id="sample-plan-001",
        policy_version="phase11-policy-v1",
        created_at="2026-07-17T00:04:00Z",
    )


def _runtime_invocation(maximum_attempts: int) -> ShadowProviderInvocationV1:
    """Build only immutable local fixtures required by the existing runtime API."""

    event, request = _deepseek_payload()
    policy = Phase11BudgetPolicyV1(
        schema_version="phase11-budget-policy-v1",
        policy_id="authentication-runtime-policy-001",
        policy_version=1,
        status="ACTIVE",
        currency="USD_MICRO",
        total_cost_cap=Decimal("1000000"),
        provider_cost_caps={"DEEPSEEK": Decimal("500000"), "ANTHROPIC": Decimal("500000")},
        model_cost_caps={
            "DEEPSEEK_PRIMARY": Decimal("500000"),
            "CLAUDE_SONNET_L1": Decimal("300000"),
            "CLAUDE_OPUS_L2": Decimal("300000"),
        },
        per_run_cost_cap=Decimal("100000"),
        maximum_call_count=100,
        maximum_calls_per_run=10,
        maximum_input_tokens=100000,
        maximum_output_tokens=100000,
        maximum_tokens_per_call=10000,
        allowed_providers=("DEEPSEEK", "ANTHROPIC"),
        allowed_models=("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2"),
        starts_at="2026-07-17T00:00:00Z",
        ends_at="2026-07-18T00:00:00Z",
        owner_approval_reference="owner-approval-001",
        stop_conditions=("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    )
    reservations = tuple(
        BudgetReservationV1(
            schema_version="phase11-budget-reservation-v1",
            reservation_id=f"authentication-reservation-{number}",
            policy_id=policy.policy_id,
            run_id="authentication-run-001",
            call_id=f"authentication-call-{number}",
            provider="DEEPSEEK",
            model="DEEPSEEK_PRIMARY",
            reserved_cost=Decimal("1000"),
            reserved_input_tokens=100,
            reserved_output_tokens=200,
            reserved_at="2026-07-17T00:05:00Z",
            expires_at="2026-07-17T02:00:00Z",
            status="RESERVED",
            reason_codes=("ROUTE_RESERVATION",),
        )
        for number in range(1, maximum_attempts + 1)
    )
    # BudgetLedgerV1 is a purely immutable fixture; no external ledger exists.
    ledger = BudgetLedgerV1(policy=policy, circuit_or_stop_state="OPEN")
    for reservation in reservations:
        ledger = ledger.reserve_call(reservation)
    first = reservations[0]
    shadow_input = _shadow_input(event.event_snapshot_id)
    return ShadowProviderInvocationV1(
        schema_version="phase11-shadow-provider-invocation-v1",
        invocation_id=None,
        execution_id="authentication-runtime-execution-001",
        run_id=first.run_id,
        call_id=first.call_id,
        route="L0",
        provider="DEEPSEEK",
        model="DEEPSEEK_PRIMARY",
        prompt_version="phase11-prompt-v1",
        provider_review_schema_version="phase10-review-schema-v1",
        shadow_input=shadow_input,
        shadow_input_identity=shadow_input.identity,
        event_id=event.event_snapshot_id,
        event_version=1,
        budget_ledger=ledger,
        budget_policy_id=policy.policy_id,
        reservation=first,
        reservation_id=first.identity,
        attempt_reservations=reservations,
        review_request=request,
        request_hash=request.payload_sha256,
        timeout_ms=1000,
        maximum_attempts=maximum_attempts,
        circuit_state="CLOSED",
        requested_at="2026-07-17T00:05:30Z",
        reason_codes=("SANITIZED_AUTHENTICATION_CLASSIFICATION",),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


class _SanitizedAuthenticationTransport:
    """A counter-only fake: no HTTP client, credential, or account state."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, int]] = []

    def __call__(self, request: object, timeout_ms: int) -> object:
        self.calls.append((request, timeout_ms))
        return {"outcome": AUTHENTICATION_REJECTED}


def _enum_values(enum_type: type[object]) -> set[str]:
    return {member.value for member in enum_type}  # type: ignore[union-attr]


def _invoke_authentication_fixture(maximum_attempts: int):
    transport = _SanitizedAuthenticationTransport()
    result = ShadowProviderRuntimeV1(transport=transport).invoke(
        _runtime_invocation(maximum_attempts)
    )
    return transport, result


def _require_runtime_authentication_outcome() -> str:
    values = _enum_values(TransportOutcomeV1)
    assert AUTHENTICATION_FAILURE in values, (
        "requires TransportOutcomeV1.AUTHENTICATION_FAILURE before the "
        "normalized adapter outcome can be terminally classified"
    )
    return AUTHENTICATION_FAILURE


def _assigned_retryable_outcomes() -> set[str]:
    tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "retryable"
            for target in node.targets
        ) and isinstance(node.value, ast.Set):
            return {
                element.value for element in node.value.elts
                if isinstance(element, ast.Constant) and type(element.value) is str
            }
    raise AssertionError("runtime invoke retryable-outcome boundary is absent")


def test_adapter_failure_enum_requires_sanitized_authentication_rejected_member():
    assert AUTHENTICATION_REJECTED in _enum_values(AdapterFailureV1)


def test_adapter_authentication_rejection_requires_terminal_boundary_membership():
    assert AUTHENTICATION_REJECTED in adapter_module._TERMINAL_OUTCOMES


def test_runtime_outcome_enum_requires_dedicated_authentication_failure_member():
    assert AUTHENTICATION_FAILURE in _enum_values(TransportOutcomeV1)


def test_current_unknown_authentication_category_proves_the_generic_malformed_response_gap():
    transport, result = _invoke_authentication_fixture(1)
    assert len(transport.calls) == result.attempt_count == 1
    assert result.transport_outcome == TransportOutcomeV1.MALFORMED_RESPONSE.value
    assert result.failure_class == TransportOutcomeV1.MALFORMED_RESPONSE.value
    assert result.retry_state == "NO_RETRY"


@pytest.mark.parametrize("maximum_attempts", (1, 2))
def test_authentication_rejection_maps_before_response_parsing_and_stops_without_retry(
    maximum_attempts: int,
):
    expected_outcome = _require_runtime_authentication_outcome()
    transport, result = _invoke_authentication_fixture(maximum_attempts)
    assert result.transport_outcome == expected_outcome
    assert result.failure_class == expected_outcome
    assert result.status == "FAILED"
    assert result.attempt_count == len(transport.calls) == 1
    assert result.retry_state == "NO_RETRY"
    assert result.timeout_state == "NONE"
    assert len(transport.calls) == 1


def test_authentication_failure_is_not_added_to_the_existing_retryable_boundary():
    retryable = _assigned_retryable_outcomes()
    assert retryable == {"TIMEOUT", "TRANSPORT_FAILURE"}
    assert AUTHENTICATION_FAILURE not in retryable


def test_sanitized_fixture_has_no_secret_or_operational_authority_surface():
    transport = _SanitizedAuthenticationTransport()
    assert set(vars(transport)) == {"calls"}
    assert transport.calls == []
    assert not {
        "api_key", "token", "password", "authorization_header", "credential",
        "credential_reference", "environment_variable_name", "account_id", "billing_id",
    } & set(vars(transport))


def test_future_two_file_scope_has_no_forbidden_dependency_additions():
    forbidden = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket",
        "subprocess", "threading", "multiprocessing", "concurrent", "telegram",
    }
    for path in (ADAPTER_PATH, RUNTIME_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert forbidden.isdisjoint(imported), path
