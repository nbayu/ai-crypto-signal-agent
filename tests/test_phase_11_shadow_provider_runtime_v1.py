"""RED contract for the bounded, injected Phase 11 provider runtime.

The module under test deliberately does not exist yet.  These tests freeze a
data-only invocation boundary: it may call a caller-provided fake transport,
but it owns neither credentials nor a provider SDK.
"""

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
)
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


IMPLEMENTATION_MODULE = "engine.phase_11_shadow_provider_runtime_v1"
UTC = timezone.utc
PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
MODELS = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
ROUTES = ("L0", "L1", "L2", "L1_TO_L2")
FAILURES = (
    "NONE", "VALIDATION_FAILURE", "UNAUTHORIZED_INVOCATION", "BUDGET_DENIED",
    "RESERVATION_EXPIRED", "HARD_STOP_ACTIVE", "CIRCUIT_OPEN", "TIMEOUT",
    "TRANSPORT_FAILURE", "PROVIDER_UNAVAILABLE", "MALFORMED_RESPONSE",
    "SCHEMA_MISMATCH", "IDENTITY_MISMATCH", "USAGE_EXCEEDS_RESERVATION",
    "UNCERTAIN_TRANSPORT_OUTCOME", "RECONCILIATION_REQUIRED",
)
PROOF = "PROVEN_NONE"


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
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reject(factory, **values):
    with pytest.raises((TypeError, ValueError)):
        factory(**values)


def _policy(**overrides):
    values = {
        "schema_version": "phase11-budget-policy-v1", "policy_id": "budget-policy-001",
        "policy_version": 1, "status": "ACTIVE", "currency": "USD_MICRO",
        "total_cost_cap": Decimal("1000000"),
        "provider_cost_caps": {"DEEPSEEK": Decimal("500000"), "ANTHROPIC": Decimal("500000")},
        "model_cost_caps": {"DEEPSEEK_PRIMARY": Decimal("500000"), "CLAUDE_SONNET_L1": Decimal("300000"), "CLAUDE_OPUS_L2": Decimal("300000")},
        "per_run_cost_cap": Decimal("100000"), "maximum_call_count": 100,
        "maximum_calls_per_run": 10, "maximum_input_tokens": 100000,
        "maximum_output_tokens": 100000, "maximum_tokens_per_call": 10000,
        "allowed_providers": PROVIDERS, "allowed_models": MODELS,
        "starts_at": "2026-07-17T00:00:00Z", "ends_at": "2026-07-18T00:00:00Z",
        "owner_approval_reference": "owner-approval-001",
        "stop_conditions": ("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    }
    values.update(overrides)
    return Phase11BudgetPolicyV1(**values)


def _reservation(provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", call_id="call-001", **overrides):
    values = {
        "schema_version": "phase11-budget-reservation-v1", "reservation_id": f"reservation-{call_id}",
        "policy_id": "budget-policy-001", "run_id": "run-001", "call_id": call_id,
        "provider": provider, "model": model, "reserved_cost": Decimal("1000"),
        "reserved_input_tokens": 100, "reserved_output_tokens": 200,
        "reserved_at": "2026-07-17T00:05:00Z", "expires_at": "2026-07-17T02:00:00Z",
        "status": "RESERVED", "reason_codes": ("L0_ROUTE",),
    }
    values.update(overrides)
    return BudgetReservationV1(**values)


def _ledger(reservation=None, **policy_changes):
    ledger = BudgetLedgerV1(policy=_policy(**policy_changes))
    return ledger if reservation is None else ledger.reserve_call(reservation)


def _usage(reservation, **overrides):
    values = {
        "schema_version": "phase11-provider-usage-v1", "usage_record_id": "usage-001",
        "reservation_id": reservation.reservation_id, "policy_id": reservation.policy_id,
        "run_id": reservation.run_id, "call_id": reservation.call_id,
        "provider": reservation.provider, "model": reservation.model,
        "request_hash": _text_hash("request"), "response_hash": _text_hash("response"),
        "input_tokens": 80, "output_tokens": 120, "estimated_cost": Decimal("900"),
        "actual_cost": Decimal("850"), "started_at": "2026-07-17T00:06:00Z",
        "completed_at": "2026-07-17T00:06:01Z", "latency_ms": 1000, "attempt_count": 1,
        "outcome": "SUCCESS", "reconciliation_status": "RESOLVED", "failure_class": "NONE",
        "reason_codes": ("COMPLETED",),
    }
    values.update(overrides)
    return ProviderUsageRecordV1(**values)


def _shadow_input():
    """A real immutable Phase 11 input, never an opaque input hash."""
    event_id = "a" * 64
    payload = {"event_class": "CLEAN_ROUTINE", "headline": "Provider boundary fixture"}
    capture_values = {
        "schema_version": "approved-news-capture-v1", "event_id": event_id,
        "event_version": 1, "source_id": "source-001", "source_type": "REGULATED_FEED",
        "source_timestamp": "2026-07-17T00:00:00Z", "captured_at": "2026-07-17T00:01:00Z",
        "point_in_time_cutoff": "2026-07-17T00:02:00Z", "normalized_payload": payload,
        "normalized_payload_hash": _sha(payload),
        "event_lineage": ({"event_id": event_id, "event_version": 1, "relation": "ORIGIN"},),
        "capture_classification": "FIXTURE", "content_origin": "SYNTHETIC_FIXTURE",
        "evidence_refs": ("evidence-001",),
    }
    material = {k: v for k, v in capture_values.items() if k not in {"capture_id", "normalized_payload_hash"}}
    capture = ApprovedNewsCaptureV1(**capture_values, capture_id=_sha(material))
    projection = Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1", projection_id="projection-001",
        production_evaluation_id="evaluation-001", event_id=event_id, candidate_id="candidate-001",
        disposition="NO_TRADE", reason_codes=("NO_ELIGIBLE_SETUP",),
        evidence_refs=("control-evidence-001",), evaluated_at="2026-07-17T00:03:00Z",
        source_artifact_hash="1" * 64,
    )
    return ShadowEvaluationInputV1(
        schema_version="shadow-evaluation-input-v1", shadow_input_id="shadow-input-001",
        approved_news_capture=capture, phase_09_control_projection=projection,
        sample_plan_id="sample-plan-001", policy_version="phase11-policy-v1",
        created_at="2026-07-17T00:04:00Z",
    )


def _request(provider="DEEPSEEK"):
    # Positive fixtures use the canonical Phase 10 request classes in the
    # implementation tests.  This sentinel intentionally asserts that runtime
    # construction must reject arbitrary mappings or the wrong payload class.
    return DeepSeekReviewPayloadV1 if provider == "DEEPSEEK" else ClaudeReviewPayloadV1


def _invocation_values(**overrides):
    reservation = overrides.pop("reservation", _reservation())
    shadow_input = overrides.pop("shadow_input", _shadow_input())
    values = {
        "schema_version": "phase11-shadow-provider-invocation-v1",
        "invocation_id": None, "execution_id": "execution-001", "run_id": reservation.run_id,
        "call_id": reservation.call_id, "route": "L0", "provider": reservation.provider,
        "model": reservation.model, "prompt_version": "phase11-prompt-v1",
        "provider_review_schema_version": "phase10-review-schema-v1",
        "shadow_input": shadow_input, "shadow_input_identity": getattr(shadow_input, "identity", None),
        "event_id": "a" * 64, "event_version": 1, "budget_policy_id": reservation.policy_id,
        "reservation": reservation, "reservation_id": reservation.identity,
        "review_request": _request(reservation.provider), "request_hash": _text_hash("request"),
        "timeout_ms": 1000, "maximum_attempts": 2, "circuit_state": "CLOSED",
        "requested_at": "2026-07-17T00:05:30Z", "reason_codes": ("L0_ROUTE",),
        "production_effect": "NONE", "zero_production_effect_proof": PROOF,
    }
    values.update(overrides)
    return values


def _invocation(**overrides):
    return ShadowProviderInvocationV1(**_invocation_values(**overrides))


class _FakeTransport:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def __call__(self, request, timeout_ms):
        self.calls.append((request, timeout_ms))
        if self.error is not None:
            raise self.error
        return self.response


def _result_values(**overrides):
    invocation = overrides.pop("invocation", _invocation())
    values = {
        "schema_version": "phase11-shadow-provider-invocation-result-v1", "result_id": None,
        "invocation": invocation, "invocation_id": invocation.identity, "status": "SUCCEEDED",
        "provider": invocation.provider, "model": invocation.model,
        "request_hash": invocation.request_hash, "response_hash": _text_hash("response"),
        "provider_review_identity": "c" * 64, "reserved_cost": invocation.reservation.reserved_cost,
        "estimated_cost": Decimal("900"), "actual_cost": Decimal("850"), "input_tokens": 80,
        "output_tokens": 120, "started_at": "2026-07-17T00:06:00Z",
        "completed_at": "2026-07-17T00:06:01Z", "latency_ms": 1000, "attempt_count": 1,
        "timeout_state": "NONE", "retry_state": "NO_RETRY", "circuit_state": "CLOSED",
        "transport_outcome": "SUCCESS", "failure_class": "NONE", "reconciliation_state": "RESOLVED",
        "usage_record": _usage(invocation.reservation), "reason_codes": ("COMPLETED",),
        "production_effect": "NONE", "zero_production_effect_proof": PROOF,
    }
    values.update(overrides)
    return values


def _result(**overrides):
    return ShadowProviderInvocationResultV1(**_result_values(**overrides))


class TestInvocationContract:
    def test_closed_immutable_canonical_invocation_binds_reservation_before_transport(self):
        value = _invocation()
        assert value.provider == "DEEPSEEK"
        assert value.model == "DEEPSEEK_PRIMARY"
        assert value.reservation_id == value.reservation.identity
        assert value.invocation_id == value.identity
        with pytest.raises((AttributeError, TypeError)):
            value.route = "L1"
        _reject(ShadowProviderInvocationV1, **_invocation_values(unknown="reject"))

    @pytest.mark.parametrize("field,value", [
        ("provider", "UNKNOWN"), ("model", "unknown"), ("route", "L9"),
        ("request_hash", "A" * 64), ("timeout_ms", 0), ("maximum_attempts", 0),
        ("requested_at", "2026-07-17T00:05:30"), ("production_effect", "PUBLISHED"),
    ])
    def test_invocation_rejects_invalid_canonical_material(self, field, value):
        _reject(ShadowProviderInvocationV1, **_invocation_values(**{field: value}))

    def test_validated_reservation_binding_rejects_policy_run_call_provider_model_and_expiry_mismatch(self):
        for change in (
            {"budget_policy_id": "other-policy"}, {"run_id": "other-run"},
            {"call_id": "other-call"}, {"provider": "ANTHROPIC"},
            {"model": "CLAUDE_SONNET_L1"}, {"reservation_id": "d" * 64},
        ):
            _reject(ShadowProviderInvocationV1, **_invocation_values(**change))
        expired = _reservation(expires_at="2026-07-17T00:05:20Z")
        _reject(ShadowProviderInvocationV1, **_invocation_values(reservation=expired))

    def test_provider_payloads_are_existing_phase10_contracts_not_arbitrary_maps(self):
        _reject(ShadowProviderInvocationV1, **_invocation_values(review_request={"payload": "forged"}))
        claude = _reservation("ANTHROPIC", "CLAUDE_SONNET_L1")
        _reject(ShadowProviderInvocationV1, **_invocation_values(reservation=claude, review_request=DeepSeekReviewPayloadV1))

    @pytest.mark.parametrize("route,provider,model", [
        ("L0", "DEEPSEEK", "DEEPSEEK_PRIMARY"),
        ("L1", "ANTHROPIC", "CLAUDE_SONNET_L1"),
        ("L2", "ANTHROPIC", "CLAUDE_OPUS_L2"),
    ])
    def test_route_model_contracts_are_exact(self, route, provider, model):
        reservation = _reservation(provider, model)
        value = _invocation(reservation=reservation, route=route, review_request=_request(provider), reason_codes=(f"{route}_ROUTE",))
        assert value.route == route
        assert value.provider == provider

    def test_l0_rejects_claude_and_l1_to_l2_requires_separate_opus_reservation(self):
        claude = _reservation("ANTHROPIC", "CLAUDE_SONNET_L1")
        _reject(ShadowProviderInvocationV1, **_invocation_values(reservation=claude, route="L0", review_request=ClaudeReviewPayloadV1))
        sonnet = _invocation(reservation=claude, route="L1", review_request=ClaudeReviewPayloadV1, reason_codes=("L1_ROUTE",))
        opus = _reservation("ANTHROPIC", "CLAUDE_OPUS_L2", "call-002")
        escalation = _invocation(reservation=opus, route="L1_TO_L2", review_request=ClaudeReviewPayloadV1, reason_codes=("L1_TO_L2_ESCALATION",))
        assert sonnet.reservation_id != escalation.reservation_id
        _reject(ShadowProviderInvocationV1, **_invocation_values(reservation=claude, route="L1_TO_L2", review_request=ClaudeReviewPayloadV1, reason_codes=("L1_TO_L2_ESCALATION",)))


class TestRuntimeBoundary:
    def test_denied_invocation_never_calls_injected_transport(self):
        transport = _FakeTransport(response={})
        runtime = ShadowProviderRuntimeV1(transport=transport)
        denied = _invocation(circuit_state="OPEN")
        result = runtime.invoke(denied)
        assert transport.calls == []
        assert result.status == "DENIED"
        assert result.failure_class == "CIRCUIT_OPEN"
        assert result.response_hash is None

    def test_transport_receives_only_sanitized_request_and_explicit_timeout(self):
        transport = _FakeTransport(response={"outcome": "SUCCESS"})
        runtime = ShadowProviderRuntimeV1(transport=transport)
        runtime.invoke(_invocation())
        request, timeout = transport.calls[0]
        assert timeout == 1000
        assert "reservation" not in request and "shadow_input" not in request
        assert set(request).isdisjoint({"api_key", "credential", "authorization_header", "token"})

    @pytest.mark.parametrize("failure", ["TIMEOUT", "TRANSPORT_FAILURE", "PROVIDER_UNAVAILABLE", "MALFORMED_RESPONSE", "SCHEMA_MISMATCH", "UNCERTAIN_TRANSPORT_OUTCOME"])
    def test_fake_transport_failures_are_bounded_and_fail_closed(self, failure):
        transport = _FakeTransport(response={"outcome": failure})
        result = ShadowProviderRuntimeV1(transport=transport).invoke(_invocation())
        assert result.failure_class == failure
        assert result.status != "SUCCEEDED"
        if failure == "UNCERTAIN_TRANSPORT_OUTCOME":
            assert result.reconciliation_state == "RECONCILIATION_REQUIRED"

    def test_retry_is_explicit_bounded_and_circuit_open_has_zero_attempts(self):
        transport = _FakeTransport(response={"outcome": "TIMEOUT"})
        result = ShadowProviderRuntimeV1(transport=transport).invoke(_invocation(maximum_attempts=2))
        assert result.attempt_count == 2
        assert len(transport.calls) == 2
        open_result = ShadowProviderRuntimeV1(transport=_FakeTransport()).invoke(_invocation(circuit_state="OPEN"))
        assert open_result.attempt_count == 0
        assert open_result.circuit_state == "OPEN"

    def test_runtime_has_no_credential_or_authority_parameters(self):
        names = set(inspect.signature(ShadowProviderRuntimeV1).parameters)
        forbidden = {"api_key", "credential", "secret", "bearer", "authorization_header", "password", "private_key", "candidate", "publication", "telegram", "account", "exchange", "order", "trading"}
        assert not names & forbidden
        assert "transport" in names


class TestResultContract:
    def test_result_is_closed_immutable_and_binds_usage_exactly(self):
        result = _result()
        assert result.usage_record.reservation_id == result.invocation.reservation.reservation_id
        assert result.actual_cost == Decimal("850")
        with pytest.raises((AttributeError, TypeError)):
            result.actual_cost = Decimal("0")
        _reject(ShadowProviderInvocationResultV1, **_result_values(extra="reject"))

    @pytest.mark.parametrize("field,value", [
        ("estimated_cost", 0.0), ("actual_cost", Decimal("-0.01")),
        ("response_hash", "B" * 64), ("attempt_count", 0),
        ("failure_class", "UNKNOWN"), ("production_effect", "TRADE"),
    ])
    def test_result_rejects_noncanonical_or_authority_material(self, field, value):
        _reject(ShadowProviderInvocationResultV1, **_result_values(**{field: value}))

    def test_result_enforces_success_failure_and_reconciliation_combinations(self):
        _reject(ShadowProviderInvocationResultV1, **_result_values(failure_class="TIMEOUT"))
        _reject(ShadowProviderInvocationResultV1, **_result_values(status="DENIED", response_hash=_text_hash("response")))
        uncertain = _result(status="FAILED", response_hash=None, provider_review_identity=None,
                            actual_cost=Decimal("1000"), transport_outcome="UNCERTAIN_TRANSPORT_OUTCOME",
                            failure_class="UNCERTAIN_TRANSPORT_OUTCOME", reconciliation_state="RECONCILIATION_REQUIRED")
        assert uncertain.reconciliation_state == "RECONCILIATION_REQUIRED"

    def test_usage_cannot_exceed_reservation_or_duplicate_charge(self):
        _reject(ShadowProviderInvocationResultV1, **_result_values(actual_cost=Decimal("1001")))
        invocation = _invocation()
        first = _result(invocation=invocation)
        duplicate = _result(invocation=invocation)
        assert first.identity == duplicate.identity
        _reject(ShadowProviderInvocationResultV1, **_result_values(invocation=invocation, request_hash=_text_hash("different")))

    def test_identity_is_canonical_and_binds_material_evidence_but_not_prose(self):
        assert _invocation().identity == _invocation().identity
        assert _invocation(timeout_ms=1001).identity != _invocation().identity
        assert _result(actual_cost=Decimal("850.0")).identity == _result(actual_cost=Decimal("850")).identity
        assert _result(actual_cost=Decimal("851")).identity != _result().identity


def test_future_module_static_boundary_is_semantic_and_disposition_remains_valid():
    path = Path(__file__).parents[1] / "engine" / "phase_11_shadow_provider_runtime_v1.py"
    if not path.exists():
        pytest.skip("RED suite: implementation module is intentionally absent")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_imports = {"requests", "httpx", "urllib", "socket", "subprocess", "dotenv", "telegram", "ccxt"}
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not imports & forbidden_imports
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not {"requests", "httpx", "socket", "subprocess"} & names
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not {"environ", "getenv", "open", "mkdir", "makedirs"} & attributes
    source = path.read_text(encoding="utf-8")
    assert "disposition" not in source or "disposition" in source
