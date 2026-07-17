"""RED contract for deterministic Phase 11 provider transport adapters."""

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
)
from engine.phase_11_provider_credential_boundary_v1 import (
    EphemeralProviderCredentialV1,
    ProviderCredentialReferenceV1,
    ProviderCredentialResolutionV1,
)
from engine.phase_11_provider_transport_adapters_v1 import (
    AdapterFailureV1,
    AdapterStatusV1,
    AnthropicClientProtocolV1,
    AnthropicShadowTransportAdapterV1,
    DeepSeekClientProtocolV1,
    DeepSeekShadowTransportAdapterV1,
    ProviderEndpointBindingV1,
    ProviderTransportAdapterValidationError,
    canonical_json_bytes,
    lowercase_sha256,
)
from engine.phase_11_shadow_input_contracts_v1 import (
    ApprovedNewsCaptureV1,
    Phase09ControlProjectionV1,
    ShadowEvaluationInputV1,
)
from engine.phase_11_shadow_provider_runtime_v1 import (
    ShadowProviderInvocationV1,
    ShadowProviderRuntimeV1,
)


UTC = timezone.utc
RAW_MATERIAL = b"synthetic-provider-adapter-credential"
PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
MODELS = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
RUNTIME_RESPONSE_FIELDS = frozenset((
    "outcome", "provider", "model", "invocation_id", "attempt_reservation_id",
    "attempt_count", "request_hash", "response_hash", "prompt_version",
    "provider_review_schema_version", "provider_review_identity",
    "structured_verdict", "reason_codes", "input_tokens", "output_tokens",
    "estimated_cost", "actual_cost", "started_at", "completed_at",
    "latency_ms", "provider_timestamp",
))


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
    return hashlib.sha256(json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _reject(factory, **values):
    with pytest.raises((TypeError, ValueError, ProviderTransportAdapterValidationError)):
        factory(**values)


def _event():
    return NormalizedNewsEventV1(
        event_namespace="news", authoritative_source_namespace="fixture-wire",
        authoritative_source_event_id="adapter-source-event-001", deterministic_source_key=None,
        normalized_primary_subject="asset:alpha", canonical_event_class="PROTOCOL_UPDATE",
        normalized_title="Alpha protocol announced", normalized_body="Alpha deterministic update.",
        normalized_language="en-US", publication_timestamp_utc=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
        point_in_time_timestamp_utc=datetime(2026, 7, 16, 12, 2, tzinfo=UTC),
        material_source_metadata={"publisher": "fixture-publisher"}, previous_event_version_id=None,
        event_version_number=1, source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        schema_version=EVENT_SCHEMA_VERSION,
    )


def _payloads():
    event = _event()
    policy = SourcePolicyDecisionV1(
        policy_version="news-source-policy-v1", decision="ELIGIBLE", primary_reason_code="SOURCE_ELIGIBLE",
        reason_codes=("SOURCE_ELIGIBLE",), evaluated_source_snapshot_ref={"source_namespace": "fixture-wire", "source_id": "source-001"},
        evaluation_timestamp_utc=datetime(2026, 7, 16, 12, 30, tzinfo=UTC), source_namespace="fixture-wire", source_id="source-001",
    )
    excerpt = "Alpha deterministic update."
    candidate = EntityCandidateV1(
        candidate_id="candidate-alpha", entity_type="DIGITAL_ASSET", canonical_entity_id="asset:alpha",
        canonical_name="Alpha", canonical_symbol="ALPHA", source_text="Alpha protocol",
        source_text_sha256=_sha("Alpha protocol"), evidence_refs=[{"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "reference_type": "EVENT_FIELD", "field_name": "normalized_title"}],
        confidence_basis="EXPLICIT_CALLER_ASSERTION", supplied_confidence=None, ambiguity_group_id=None,
        candidate_status="ACCEPTED", rejection_reason_codes=[], mapping_policy_version=ENTITY_MAPPING_POLICY_VERSION,
    )
    mapped = map_entity_candidates(event_snapshot_id=event.event_snapshot_id, source_policy_decision=policy, candidates=[candidate])
    projected = project_ai_review_payloads(
        normalized_event=event, source_policy_decision=policy, entity_mapping_result=mapped,
        bounded_evidence=({"evidence_ref_id": "evidence-001", "event_snapshot_id": event.event_snapshot_id, "source_field": "normalized_body", "excerpt": excerpt, "excerpt_sha256": _sha(excerpt)},),
        review_task="Assess bounded canonical facts.", token_policy=PayloadTokenPolicyV1(
            claude_input_hard_limit_tokens=8000, claude_target_input_min_tokens=2000,
            claude_target_input_max_tokens=5000, claude_output_hard_limit_tokens=1000,
            maximum_claude_logical_reviews_per_event=1, maximum_provider_attempts_per_review=2,
            maximum_retry_count=1,
        ), token_counter=lambda _: 100,
    )
    return event, projected.deepseek_payload, projected.claude_payload


def _binding_values(provider="DEEPSEEK", contract_model="DEEPSEEK_PRIMARY", **overrides):
    identifiers = {
        "DEEPSEEK_PRIMARY": "synthetic-deepseek-primary",
        "CLAUDE_SONNET_L1": "synthetic-anthropic-sonnet",
        "CLAUDE_OPUS_L2": "synthetic-anthropic-opus",
    }
    values = {
        "schema_version": "phase11-provider-endpoint-binding-v1", "binding_identity": None,
        "provider": provider, "contract_model": contract_model,
        "provider_model_identifier": identifiers[contract_model],
        "adapter_version": "phase11-provider-transport-adapter-v1",
        "request_schema_version": "phase10-review-schema-v1",
        "response_schema_version": "phase11-shadow-provider-transport-response-v1",
        "valid_from": "2026-07-17T00:00:00Z", "valid_until": "2026-07-18T00:00:00Z",
    }
    values.update(overrides)
    return values


def _binding(provider="DEEPSEEK", contract_model="DEEPSEEK_PRIMARY", **overrides):
    return ProviderEndpointBindingV1(**_binding_values(provider, contract_model, **overrides))


def _resolution(provider="DEEPSEEK", *, status="RESOLVED", failure="NONE", **overrides):
    reference = ProviderCredentialReferenceV1(
        schema_version="phase11-provider-credential-reference-v1", credential_reference_id=f"credential-reference-{provider.lower()}",
        provider=provider, credential_version=1, source_kind="TEST_FIXTURE", owner_approval_reference="owner-approval-001",
        created_at="2026-07-17T00:00:00Z", valid_from="2026-07-17T00:00:00Z", valid_until="2026-07-18T00:00:00Z",
        rotation_required=False, reference_identity=None,
    )
    credential = EphemeralProviderCredentialV1(
        schema_version="phase11-ephemeral-provider-credential-v1", provider=provider, credential_reference=reference,
        credential_reference_identity=reference.identity, credential_version=1, material=RAW_MATERIAL,
    )
    values = {
        "schema_version": "phase11-provider-credential-resolution-v1", "resolution_identity": None,
        "credential_reference": reference, "credential_reference_identity": reference.identity, "provider": provider,
        "credential_version": 1, "status": status, "failure_class": failure,
        "resolved_at": "2026-07-17T00:05:00Z", "valid_until": reference.valid_until,
        "rotation_required": False, "reason_codes": ("CREDENTIAL_RESOLVED",) if status == "RESOLVED" else (failure,),
        "ephemeral_credential": credential if status == "RESOLVED" else None,
    }
    values.update(overrides)
    return ProviderCredentialResolutionV1(**values)


def _transport_request(payload, provider, model, route, *, invocation_id="a" * 64, attempt_id="b" * 64, call_id="call-001", attempt=1):
    return {
        "provider": provider, "model": model, "route": route, "invocation_id": invocation_id,
        "attempt_number": attempt, "attempt_reservation_id": attempt_id, "call_id": call_id,
        "request_hash": payload.payload_sha256, "review_request": payload.to_mapping(),
    }


def _client_success(request, binding, *, status="SUCCESS", **overrides):
    values = {
        "schema_version": "phase11-provider-client-response-v1", "status": status,
        "provider": binding.provider, "provider_model_identifier": binding.provider_model_identifier,
        "invocation_id": request["invocation_id"], "attempt_reservation_id": request["attempt_reservation_id"],
        "call_id": request["call_id"], "request_hash": request["request_hash"],
        "provider_review_identity": "c" * 64, "structured_verdict": {"verdict": "ADVISORY_REVIEW"},
        "reason_codes": ("STRUCTURED_REVIEW",), "input_tokens": 80, "output_tokens": 120,
        "estimated_cost": Decimal("900"), "actual_cost": Decimal("850"),
        "started_at": "2026-07-17T00:05:30Z", "completed_at": "2026-07-17T00:05:31Z",
        "provider_timestamp": "2026-07-17T00:05:31Z", "latency_ms": 1000,
    }
    values.update(overrides)
    return values


class _FakeClient:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls, self.material_received = response, error, [], []

    def complete(self, **values):
        self.material_received.append(values.get("credential_material") == RAW_MATERIAL)
        self.calls.append({key: value for key, value in values.items() if key != "credential_material"})
        if self.error is not None:
            raise self.error
        return self.response(values) if callable(self.response) else self.response


def _adapter(provider, model, payload, client, **overrides):
    binding = _binding(provider, model)
    values = {
        "endpoint_binding": binding, "review_request": payload,
        "credential_resolution": _resolution(provider), "attempted_at": "2026-07-17T00:05:30Z",
        "client": client,
    }
    values.update(overrides)
    adapter_type = DeepSeekShadowTransportAdapterV1 if provider == "DEEPSEEK" else AnthropicShadowTransportAdapterV1
    return adapter_type(**values)


def _runtime_invocation():
    event, payload, _ = _payloads()
    capture_values = {
        "schema_version": "approved-news-capture-v1", "event_id": event.event_snapshot_id, "event_version": 1,
        "source_id": "source-001", "source_type": "REGULATED_FEED", "source_timestamp": "2026-07-17T00:00:00Z",
        "captured_at": "2026-07-17T00:01:00Z", "point_in_time_cutoff": "2026-07-17T00:02:00Z",
        "normalized_payload": {"headline": "Provider adapter fixture"}, "normalized_payload_hash": _sha({"headline": "Provider adapter fixture"}),
        "event_lineage": ({"event_id": event.event_snapshot_id, "event_version": 1, "relation": "ORIGIN"},),
        "capture_classification": "FIXTURE", "content_origin": "SYNTHETIC_FIXTURE", "evidence_refs": ("evidence-001",),
    }
    capture = ApprovedNewsCaptureV1(**capture_values, capture_id=_sha({key: value for key, value in capture_values.items() if key not in {"capture_id", "normalized_payload_hash"}}))
    control = Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1", projection_id="projection-001", production_evaluation_id="evaluation-001",
        event_id=event.event_snapshot_id, candidate_id="candidate-001", disposition="NO_TRADE", reason_codes=("NO_ELIGIBLE_SETUP",),
        evidence_refs=("control-evidence-001",), evaluated_at="2026-07-17T00:03:00Z", source_artifact_hash="1" * 64,
    )
    shadow_input = ShadowEvaluationInputV1(
        schema_version="shadow-evaluation-input-v1", shadow_input_id="shadow-input-001", approved_news_capture=capture,
        phase_09_control_projection=control, sample_plan_id="sample-plan-001", policy_version="phase11-policy-v1", created_at="2026-07-17T00:04:00Z",
    )
    policy = Phase11BudgetPolicyV1(
        schema_version="phase11-budget-policy-v1", policy_id="budget-policy-001", policy_version=1, status="ACTIVE", currency="USD_MICRO",
        total_cost_cap=Decimal("1000000"), provider_cost_caps={"DEEPSEEK": Decimal("500000"), "ANTHROPIC": Decimal("500000")},
        model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("500000"), "CLAUDE_SONNET_L1": Decimal("300000"), "CLAUDE_OPUS_L2": Decimal("300000")},
        per_run_cost_cap=Decimal("100000"), maximum_call_count=100, maximum_calls_per_run=10,
        maximum_input_tokens=100000, maximum_output_tokens=100000, maximum_tokens_per_call=10000,
        allowed_providers=PROVIDERS, allowed_models=MODELS, starts_at="2026-07-17T00:00:00Z", ends_at="2026-07-18T00:00:00Z",
        owner_approval_reference="owner-approval-001", stop_conditions=("TOTAL_CAP_HARD_STOP", "RECONCILIATION_REQUIRED"),
    )
    reservation = BudgetReservationV1(
        schema_version="phase11-budget-reservation-v1", reservation_id="reservation-call-001", policy_id=policy.policy_id,
        run_id="run-001", call_id="call-001", provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", reserved_cost=Decimal("1000"),
        reserved_input_tokens=100, reserved_output_tokens=200, reserved_at="2026-07-17T00:05:00Z", expires_at="2026-07-17T02:00:00Z",
        status="RESERVED", reason_codes=("ROUTE_RESERVATION",),
    )
    ledger = BudgetLedgerV1(policy=policy, circuit_or_stop_state="OPEN").reserve_call(reservation)
    return ShadowProviderInvocationV1(
        schema_version="phase11-shadow-provider-invocation-v1", invocation_id=None, execution_id="execution-001", run_id=reservation.run_id,
        call_id=reservation.call_id, route="L0", provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", prompt_version="phase11-prompt-v1",
        provider_review_schema_version="phase10-review-schema-v1", shadow_input=shadow_input, shadow_input_identity=shadow_input.identity,
        event_id=event.event_snapshot_id, event_version=1, budget_ledger=ledger, budget_policy_id=policy.policy_id,
        reservation=reservation, reservation_id=reservation.identity, attempt_reservations=(reservation,), review_request=payload,
        request_hash=payload.payload_sha256, timeout_ms=1000, maximum_attempts=1, circuit_state="CLOSED",
        requested_at="2026-07-17T00:05:30Z", reason_codes=("ROUTE_REQUIRED",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
    )


class TestEndpointBinding:
    def test_binding_is_closed_immutable_and_canonical(self):
        deepseek = _binding()
        sonnet = _binding("ANTHROPIC", "CLAUDE_SONNET_L1")
        opus = _binding("ANTHROPIC", "CLAUDE_OPUS_L2")
        assert deepseek.identity == _binding().identity
        assert len({deepseek.identity, sonnet.identity, opus.identity}) == 3
        assert sonnet.provider_model_identifier == "synthetic-anthropic-sonnet"
        with pytest.raises((AttributeError, TypeError)):
            deepseek.provider = "ANTHROPIC"
        _reject(ProviderEndpointBindingV1, **_binding_values(unknown="reject"))

    @pytest.mark.parametrize("provider,model,identifier", [
        ("ANTHROPIC", "DEEPSEEK_PRIMARY", "synthetic-deepseek-primary"),
        ("DEEPSEEK", "CLAUDE_SONNET_L1", "synthetic-anthropic-sonnet"),
        ("ANTHROPIC", "CLAUDE_OPUS_L2", ""),
        ("UNKNOWN", "DEEPSEEK_PRIMARY", "synthetic-deepseek-primary"),
    ])
    def test_binding_rejects_provider_model_and_identifier_substitution(self, provider, model, identifier):
        _reject(ProviderEndpointBindingV1, **_binding_values(provider, model, provider_model_identifier=identifier))

    def test_binding_rejects_invalid_time_and_forged_identity(self):
        _reject(ProviderEndpointBindingV1, **_binding_values(valid_until="2026-07-16T23:59:59Z"))
        _reject(ProviderEndpointBindingV1, **_binding_values(valid_from="2026-07-17T00:00:00"))
        _reject(ProviderEndpointBindingV1, **_binding_values(binding_identity="0" * 64))


class TestAdapterTransportBoundary:
    @pytest.mark.parametrize("provider,model,route,payload_type", [
        ("DEEPSEEK", "DEEPSEEK_PRIMARY", "L0", DeepSeekReviewPayloadV1),
        ("ANTHROPIC", "CLAUDE_SONNET_L1", "L1", ClaudeReviewPayloadV1),
        ("ANTHROPIC", "CLAUDE_OPUS_L2", "L2", ClaudeReviewPayloadV1),
    ])
    def test_adapter_projects_real_payload_and_returns_exact_runtime_response(self, provider, model, route, payload_type):
        _, deepseek, claude = _payloads()
        payload = deepseek if provider == "DEEPSEEK" else claude
        assert type(payload) is payload_type
        request = _transport_request(payload, provider, model, route)
        binding = _binding(provider, model)
        client = _FakeClient(_client_success(request, binding))
        adapter = _adapter(provider, model, payload, client)
        assert callable(adapter)
        assert client.calls == [] and RAW_MATERIAL.decode() not in repr(adapter) + str(adapter)
        response = adapter(request, 1000)
        assert len(client.calls) == 1
        assert frozenset(response) == RUNTIME_RESPONSE_FIELDS
        assert response["outcome"] == "SUCCESS"
        assert response["provider"] == provider and response["model"] == model
        assert response["request_hash"] == payload.payload_sha256
        assert response["attempt_reservation_id"] == request["attempt_reservation_id"]
        assert response["response_hash"] == _sha({key: value for key, value in response.items() if key != "response_hash"})
        client_args = client.calls[0]
        assert client_args["provider_model_identifier"] == binding.provider_model_identifier
        assert client_args["timeout_ms"] == 1000
        assert client_args["invocation_id"] == request["invocation_id"]
        assert client_args["attempt_reservation_id"] == request["attempt_reservation_id"]
        assert client.material_received == [True]
        assert set(client_args).isdisjoint({"budget_ledger", "reservation", "shadow_input", "candidate", "publication", "account", "order", "trading"})

    def test_adapter_is_directly_compatible_with_runtime_transport_signature(self):
        _, deepseek, _ = _payloads()
        request = _transport_request(deepseek, "DEEPSEEK", "DEEPSEEK_PRIMARY", "L0")
        client = _FakeClient(_client_success(request, _binding()))
        adapter = _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", deepseek, client)
        parameters = tuple(inspect.signature(adapter).parameters)
        assert parameters == ("request", "timeout_ms")
        assert "transport" in inspect.signature(ShadowProviderRuntimeV1).parameters

    def test_deepseek_adapter_runs_as_the_generic_runtime_transport(self):
        invocation = _runtime_invocation()
        binding = _binding()

        def response(values):
            request = {
                "invocation_id": values["invocation_id"],
                "attempt_reservation_id": values["attempt_reservation_id"],
                "call_id": values["call_id"],
                "request_hash": values["request_hash"],
            }
            return _client_success(request, binding)

        client = _FakeClient(response)
        adapter = _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", invocation.review_request, client)
        result = ShadowProviderRuntimeV1(transport=adapter).invoke(invocation)
        assert result.status == "SUCCEEDED" and result.transport_outcome == "SUCCESS"
        assert len(client.calls) == 1 and client.material_received == [True]

    def test_failed_credential_or_binding_denies_without_client_call(self):
        _, deepseek, _ = _payloads()
        request = _transport_request(deepseek, "DEEPSEEK", "DEEPSEEK_PRIMARY", "L0")
        client = _FakeClient(_client_success(request, _binding()))
        denied = _resolution("DEEPSEEK", status="DENIED", failure="EXPIRED")
        _reject(DeepSeekShadowTransportAdapterV1, endpoint_binding=_binding(), review_request=deepseek, credential_resolution=denied, attempted_at="2026-07-17T00:05:30Z", client=client)
        assert client.calls == []
        _reject(DeepSeekShadowTransportAdapterV1, endpoint_binding=_binding("ANTHROPIC", "CLAUDE_SONNET_L1"), review_request=deepseek, credential_resolution=_resolution(), attempted_at="2026-07-17T00:05:30Z", client=client)
        _reject(DeepSeekShadowTransportAdapterV1, endpoint_binding=_binding(), review_request=deepseek, credential_resolution=_resolution(), attempted_at="2026-07-18T00:00:01Z", client=client)

    def test_payload_and_runtime_request_mismatch_fails_closed_without_client_call(self):
        _, deepseek, claude = _payloads()
        request = _transport_request(deepseek, "DEEPSEEK", "DEEPSEEK_PRIMARY", "L0")
        client = _FakeClient()
        adapter = _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", deepseek, client)
        forged = dict(request, request_hash="d" * 64)
        assert adapter(forged, 1000) == {"outcome": "MALFORMED_RESPONSE"}
        assert client.calls == []
        _reject(DeepSeekShadowTransportAdapterV1, endpoint_binding=_binding(), review_request=claude, credential_resolution=_resolution(), attempted_at="2026-07-17T00:05:30Z", client=client)
        _reject(AnthropicShadowTransportAdapterV1, endpoint_binding=_binding("ANTHROPIC", "CLAUDE_SONNET_L1"), review_request=deepseek, credential_resolution=_resolution("ANTHROPIC"), attempted_at="2026-07-17T00:05:30Z", client=client)


class TestResponseAndFailureTranslation:
    @pytest.mark.parametrize("status,outcome", [
        ("PROVIDER_UNAVAILABLE", "PROVIDER_UNAVAILABLE"),
        ("MALFORMED_RESPONSE", "MALFORMED_RESPONSE"),
        ("SCHEMA_MISMATCH", "SCHEMA_MISMATCH"),
        ("UNCERTAIN_TRANSPORT_OUTCOME", "UNCERTAIN_TRANSPORT_OUTCOME"),
    ])
    def test_terminal_client_status_maps_without_retry_or_second_client_call(self, status, outcome):
        _, payload, _ = _payloads()
        request = _transport_request(payload, "DEEPSEEK", "DEEPSEEK_PRIMARY", "L0")
        client = _FakeClient(_client_success(request, _binding(), status=status))
        assert _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", payload, client)(request, 1000) == {"outcome": outcome}
        assert len(client.calls) == 1

    @pytest.mark.parametrize("error,outcome", [
        (TimeoutError("synthetic-provider-adapter-credential"), "TIMEOUT"),
        (ConnectionError("synthetic-provider-adapter-credential"), "TRANSPORT_FAILURE"),
        (RuntimeError("synthetic-provider-adapter-credential"), "TRANSPORT_FAILURE"),
    ])
    def test_client_exceptions_are_redacted_and_map_safely(self, error, outcome):
        _, payload, _ = _payloads()
        request = _transport_request(payload, "DEEPSEEK", "DEEPSEEK_PRIMARY", "L0")
        client = _FakeClient(error=error)
        adapter = _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", payload, client)
        result = adapter(request, 1000)
        assert result == {"outcome": outcome} and len(client.calls) == 1
        assert RAW_MATERIAL.decode() not in repr(adapter) + str(adapter) + repr(result)

    @pytest.mark.parametrize("field,value", [
        ("provider", "ANTHROPIC"), ("provider_model_identifier", "synthetic-anthropic-sonnet"),
        ("request_hash", "d" * 64), ("input_tokens", -1), ("estimated_cost", 0.1),
        ("started_at", "2026-07-17T00:05:30"), ("provider_timestamp", "2026-07-17T00:05:31"),
        ("reason_codes", ("invalid",)), ("structured_verdict", {"verdict": "UNKNOWN"}),
        ("unexpected", "reject"),
    ])
    def test_invalid_client_success_response_fails_closed(self, field, value):
        _, payload, _ = _payloads()
        request = _transport_request(payload, "DEEPSEEK", "DEEPSEEK_PRIMARY", "L0")
        values = _client_success(request, _binding())
        values[field] = value
        client = _FakeClient(values)
        assert _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", payload, client)(request, 1000) == {"outcome": "MALFORMED_RESPONSE"}
        assert len(client.calls) == 1


def test_adapter_identity_is_safe_and_excludes_client_and_credential_material():
    _, payload, _ = _payloads()
    first = _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", payload, _FakeClient())
    second = _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", payload, _FakeClient())
    assert first.identity == second.identity
    assert first.identity != _adapter("DEEPSEEK", "DEEPSEEK_PRIMARY", payload, _FakeClient(), attempted_at="2026-07-17T00:05:31Z").identity
    for rendered in (repr(first), str(first), repr(first.endpoint_binding), str(first.endpoint_binding), first.identity, first.endpoint_binding.identity):
        assert RAW_MATERIAL.decode() not in rendered
    assert lowercase_sha256({"provider": "DEEPSEEK"}) == _sha({"provider": "DEEPSEEK"})
    assert RAW_MATERIAL.decode() not in canonical_json_bytes({"adapter_identity": first.identity}).decode()


def test_public_protocols_and_future_module_static_boundary_are_narrow():
    assert hasattr(DeepSeekClientProtocolV1, "complete")
    assert hasattr(AnthropicClientProtocolV1, "complete")
    assert {item.value for item in AdapterStatusV1} >= {"SUCCESS", "FAILED"}
    assert {item.value for item in AdapterFailureV1} >= {"NONE", "VALIDATION_FAILURE", "TRANSPORT_FAILURE"}
    path = Path(__file__).parents[1] / "engine" / "phase_11_provider_transport_adapters_v1.py"
    if not path.exists():
        pytest.skip("RED suite: transport adapter implementation is intentionally absent")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_imports = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "keyring", "boto3", "google", "azure", "telegram", "ccxt"}
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not imports & forbidden_imports
    forbidden = {"environ", "getenv", "open", "mkdir", "makedirs", "account", "balance", "position", "capital", "exchange", "order", "trading", "publication", "telegram_client"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not names & forbidden
    allowed = {node.arg for node in ast.walk(ast.parse("def fixture(disposition, input_tokens, output_tokens, token_limit): pass")) if isinstance(node, ast.arg)}
    assert not allowed & forbidden
