from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e5_claude_review_router_v1 as router
import engine.e5_provider_invocation_boundary_v1 as subject
import engine.e5_technical_review_payload_v1 as payload_contract
from engine.e5_technical_review_payload_v1 import (
    E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    get_owner_frozen_e5_provider_model_price_binding_v1,
)
from test_e5_claude_review_router_v1 import (
    ACTIVE_BINDING_SHA256,
    UTC_DAY,
    _payload,
    _payload_with_registered_binding,
    _review_and_adjudication,
    _usage,
)


MODE_SIDE_DECISION = (
    ("SWING", "LONG", "CLEAR", "L0"),
    ("SWING", "SHORT", "CAUTION", "L1"),
    ("INTRADAY", "LONG", "HOLD", "L2"),
    ("INTRADAY", "SHORT", "CLEAR", "L0"),
    ("SCALP", "LONG", "CAUTION", "L1"),
    ("SCALP", "SHORT", "HOLD", "L2"),
)
REQUEST_FIELDS = (
    "request_version",
    "provider_binding_sha256",
    "provider",
    "invocation_role",
    "payload_sha256",
    "upstream_identity_sha256",
    "route",
    "model_id",
    "input_hard_limit_tokens",
    "output_hard_limit_tokens",
    "timeout_seconds",
    "provider_attempts",
    "retry_count",
    "maximum_review_cost_micro_usd",
    "expected_response_schema_version",
    "canonical_input_json",
    "request_sha256",
)
OBSERVATION_FIELDS = (
    "observation_version",
    "request_sha256",
    "provider",
    "model_id",
    "attempt_number",
    "transport_outcome",
    "response_mapping",
    "response_digest_sha256",
    "measured_input_tokens",
    "measured_output_tokens",
    "billed_cost_micro_usd",
    "observation_sha256",
)
CLAUDE_REVIEW_FIELDS = (
    "review_version",
    "provider_binding_sha256",
    "payload_sha256",
    "route_sha256",
    "route",
    "model_id",
    "review_summary",
    "reviewed_evidence_fields",
    "review_sha256",
)
RESULT_FIELDS = (
    "result_version",
    "provider_binding_sha256",
    "payload_sha256",
    "route_sha256",
    "provider",
    "invocation_role",
    "model_id",
    "request_sha256",
    "transport_invoked",
    "provider_attempt_count",
    "retry_count",
    "underlying_failure_code",
    "final_result_code",
    "accepted_response_sha256",
    "response_digest_sha256",
    "publication_allowed",
    "telegram_send_allowed",
    "slot_mutation_allowed",
    "pair_lock_mutation_allowed",
    "retry_allowed",
    "fallback_allowed",
    "stale_result_reuse_allowed",
    "result_sha256",
)
EXECUTION_FIELDS = (
    "execution_version",
    "invocation_result",
    "accepted_deepseek_review",
    "accepted_claude_review",
    "execution_sha256",
)


FAKE_TRANSPORT_CALL_COUNT = 0


def _assert_invalid(call):
    with pytest.raises(
        ValueError,
        match="^invalid E5 provider invocation boundary$",
    ):
        call()


def _unsafe_clone(value, **changes):
    clone = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return clone


def _canonical_hash(mapping):
    return hashlib.sha256(
        json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _deepseek_preflight(payload, *, measured=100, requested=100):
    return payload_contract.preflight_e5_technical_review_payload_v1(
        payload=payload,
        measured_input_tokens=measured,
        requested_output_tokens=requested,
    )


def _route_chain(
    tmp_path,
    decision="CAUTION",
    *,
    mode="SWING",
    side="LONG",
    name="provider",
    usage=None,
    hard_gates=True,
    score=80,
    floor=70,
):
    payload = _payload(tmp_path, mode, side, name=name)
    review, adjudication = _review_and_adjudication(
        payload,
        decision,
        hard_gates=hard_gates,
        score=score,
        floor=floor,
    )
    if usage is None:
        usage = router.create_empty_e5_claude_daily_usage_v1(utc_day=UTC_DAY)
    route = router.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=usage,
    )
    preflight = router.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=100,
        requested_output_tokens=100,
    )
    return payload, review, adjudication, route, preflight


def _claude_review_mapping(payload, route, *, summary="Bounded advisory evidence."):
    preimage = {
        "review_version": subject.E5_CLAUDE_ESCALATION_REVIEW_VERSION,
        "provider_binding_sha256": ACTIVE_BINDING_SHA256,
        "payload_sha256": payload.payload_sha256,
        "route_sha256": route.route_sha256,
        "route": route.route,
        "model_id": route.model_id,
        "review_summary": summary,
        "reviewed_evidence_fields": list(E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS),
    }
    return {**preimage, "review_sha256": _canonical_hash(preimage)}


def _claude_review(payload, route, **changes):
    mapping = _claude_review_mapping(payload, route)
    mapping.update(changes)
    return subject.reconstruct_e5_claude_escalation_review_v1(mapping)


def _fake_transport(
    *,
    outcome=subject.SUCCESS,
    response_mapping=None,
    provider=None,
    model_id=None,
    request_sha256=None,
    measured_input=100,
    measured_output=100,
    billed_cost=100,
    raises=False,
):
    local_calls = []

    def transport(request):
        global FAKE_TRANSPORT_CALL_COUNT
        FAKE_TRANSPORT_CALL_COUNT += 1
        local_calls.append(request.request_sha256)
        if raises:
            raise RuntimeError("synthetic transport failure")
        mapping = response_mapping(request) if callable(response_mapping) else response_mapping
        return subject.build_e5_provider_attempt_observation_v1(
            request=request,
            transport_outcome=outcome,
            response_mapping=mapping,
            measured_input_tokens=measured_input,
            measured_output_tokens=measured_output,
            billed_cost_micro_usd=billed_cost,
            provider=provider,
            model_id=model_id,
            request_sha256=request_sha256,
        )

    return transport, local_calls


def _invoke_deepseek(
    payload,
    review,
    *,
    outcome=subject.SUCCESS,
    response_mapping=None,
    **transport_options,
):
    if response_mapping is None and outcome == subject.SUCCESS:
        response_mapping = review.to_mapping()
    transport, calls = _fake_transport(
        outcome=outcome,
        response_mapping=response_mapping,
        **transport_options,
    )
    result = subject.invoke_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
        transport=transport,
    )
    return result, calls


def _invoke_claude(chain, *, outcome=subject.SUCCESS, response_mapping=None, **options):
    payload, review, adjudication, route, preflight = chain
    if response_mapping is None and outcome == subject.SUCCESS:
        response_mapping = _claude_review_mapping(payload, route)
    transport, calls = _fake_transport(
        outcome=outcome,
        response_mapping=response_mapping,
        **options,
    )
    result = subject.invoke_e5_claude_review_once_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route,
        token_preflight=preflight,
        transport=transport,
    )
    return result, calls


def test_exact_versions_providers_roles_codes_and_default():
    assert subject.E5_PROVIDER_REQUEST_VERSION == "e5-provider-request-v1"
    assert subject.E5_PROVIDER_ATTEMPT_OBSERVATION_VERSION == (
        "e5-provider-attempt-observation-v1"
    )
    assert subject.E5_CLAUDE_ESCALATION_REVIEW_VERSION == (
        "e5-claude-escalation-review-v1"
    )
    assert subject.E5_PROVIDER_INVOCATION_RESULT_VERSION == (
        "e5-provider-invocation-result-v1"
    )
    assert subject.E5_PROVIDER_ACCEPTED_RESPONSE_EXECUTION_VERSION == (
        "e5-provider-accepted-response-execution-v1"
    )
    assert subject.E5_PROVIDERS == ("DEEPSEEK", "ANTHROPIC")
    assert subject.PROVIDER_COUNT == 2
    assert subject.E5_INVOCATION_ROLES == (
        "DEEPSEEK_TECHNICAL_REVIEW",
        "CLAUDE_L1_ESCALATION_REVIEW",
        "CLAUDE_L2_ESCALATION_REVIEW",
    )
    assert subject.INVOCATION_ROLE_COUNT == 3
    assert subject.E5_D8_FAILURE_CODES == (
        "HOLD_PROVIDER_TIMEOUT",
        "HOLD_PROVIDER_UNAVAILABLE",
        "HOLD_PROVIDER_CONFIGURATION",
        "HOLD_MODEL_BINDING",
        "HOLD_INVALID_RESPONSE",
        "HOLD_TOKEN_LIMIT",
        "HOLD_BUDGET_BLOCKED",
        "HOLD_ESCALATION_INCOMPLETE",
    )
    assert subject.D8_FAILURE_CODE_COUNT == 8
    assert subject.E5_PROVIDER_INVOCATION_SUCCESS_CODES == (
        "PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED",
        "PASS_L0_NO_CLAUDE_REQUIRED",
        "PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED",
    )
    assert subject.SUCCESS_CODE_COUNT == 3
    assert subject.E5_TRANSPORT_OUTCOME_CODES == (
        "SUCCESS",
        "TIMEOUT",
        "TEMPORARILY_UNAVAILABLE",
        "AUTHENTICATION_OR_PERMISSION_FAILURE",
        "UNSUPPORTED_MODEL",
        "MALFORMED_OR_SCHEMA_INVALID_RESPONSE",
        "TOKEN_LIMIT_EXCEEDED",
    )
    assert subject.TRANSPORT_OUTCOME_CODE_COUNT == 7
    assert subject.MAXIMUM_PROVIDER_ATTEMPTS == 1
    assert subject.RETRY_COUNT == 0
    assert subject.PROVIDER_FAILURE_DEFAULT == "FAIL_CLOSED_NO_PUBLICATION"


@pytest.mark.parametrize(
    ("contract", "expected_fields"),
    (
        (subject.E5ProviderRequestV1, REQUEST_FIELDS),
        (subject.E5ProviderAttemptObservationV1, OBSERVATION_FIELDS),
        (subject.E5ClaudeEscalationReviewV1, CLAUDE_REVIEW_FIELDS),
        (subject.E5ProviderInvocationResultV1, RESULT_FIELDS),
        (subject.E5ProviderAcceptedResponseExecutionV1, EXECUTION_FIELDS),
    ),
)
def test_exact_frozen_slotted_contract_fields(contract, expected_fields):
    assert is_dataclass(contract)
    assert contract.__dataclass_params__.frozen is True
    assert "__dict__" not in contract.__slots__
    assert tuple(field.name for field in fields(contract)) == expected_fields


def test_deepseek_request_exact_authority_determinism_and_redaction(tmp_path):
    payload = _payload(tmp_path)
    preflight = _deepseek_preflight(payload)
    first = subject.build_e5_deepseek_provider_request_v1(
        payload=payload,
        token_preflight=preflight,
    )
    second = subject.build_e5_deepseek_provider_request_v1(
        payload=payload,
        token_preflight=preflight,
    )
    assert first == second
    assert first.request_version == subject.E5_PROVIDER_REQUEST_VERSION
    assert first.provider_binding_sha256 == ACTIVE_BINDING_SHA256
    assert (
        first.provider,
        first.invocation_role,
        first.route,
        first.model_id,
        first.input_hard_limit_tokens,
        first.output_hard_limit_tokens,
        first.timeout_seconds,
        first.provider_attempts,
        first.retry_count,
        first.maximum_review_cost_micro_usd,
    ) == (
        "DEEPSEEK",
        "DEEPSEEK_TECHNICAL_REVIEW",
        None,
        "deepseek-v4-pro",
        4000,
        500,
        60,
        1,
        0,
        0,
    )
    assert json.loads(first.canonical_input_json) == payload.to_mapping()
    serialized = json.dumps(first.to_mapping()).casefold()
    assert all(
        field not in serialized
        for field in ("api_key", "authorization", "credential", "secret")
    )
    assert tuple(first.to_mapping()) == REQUEST_FIELDS
    assert first.to_mapping()["timeout_seconds"] == 60
    request_preimage = first.to_mapping()
    request_preimage.pop("request_sha256")
    assert request_preimage["timeout_seconds"] == 60
    assert _canonical_hash(json.loads(first.canonical_request_json())) == (
        first.request_sha256
    )
    assert _canonical_hash(request_preimage) == first.request_sha256
    altered_timeout_preimage = dict(request_preimage)
    altered_timeout_preimage["timeout_seconds"] = 61
    assert _canonical_hash(altered_timeout_preimage) != first.request_sha256
    with pytest.raises(FrozenInstanceError):
        first.model_id = "other"


def test_historical_v1_payload_and_failed_preflight_cannot_build_request(tmp_path):
    payload = _payload(tmp_path)
    v1 = _payload_with_registered_binding(
        payload,
        get_owner_frozen_e5_provider_model_price_binding_v1().binding_sha256,
    )
    preflight = _deepseek_preflight(payload)
    _assert_invalid(
        lambda: subject.build_e5_deepseek_provider_request_v1(
            payload=v1,
            token_preflight=preflight,
        )
    )
    failed = _deepseek_preflight(payload, measured=4001)
    _assert_invalid(
        lambda: subject.build_e5_deepseek_provider_request_v1(
            payload=payload,
            token_preflight=failed,
        )
    )


@pytest.mark.parametrize(
    ("decision", "route_name", "model", "input_limit", "output_limit", "timeout", "cost"),
    (
        ("CAUTION", "L1", "claude-opus-5", 4000, 500, 10, 32500),
        ("HOLD", "L2", "claude-fable-5", 6000, 800, 20, 100000),
    ),
)
def test_claude_request_exact_route_authority(
    tmp_path,
    decision,
    route_name,
    model,
    input_limit,
    output_limit,
    timeout,
    cost,
):
    payload, review, adjudication, route, preflight = _route_chain(
        tmp_path,
        decision,
        name=f"request-{route_name}",
    )
    request = subject.build_e5_claude_provider_request_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route,
        token_preflight=preflight,
    )
    assert request.provider == "ANTHROPIC"
    assert request.route == route_name
    assert request.model_id == model
    assert request.input_hard_limit_tokens == input_limit
    assert request.output_hard_limit_tokens == output_limit
    assert request.timeout_seconds == timeout
    assert request.provider_attempts == 1
    assert request.retry_count == 0
    assert request.maximum_review_cost_micro_usd == cost
    assert request.upstream_identity_sha256 == route.route_sha256
    canonical = json.loads(request.canonical_input_json)
    assert tuple(sorted(canonical)) == (
        "claude_route_result",
        "deepseek_adjudication",
        "deepseek_review",
        "payload",
    )
    assert canonical["claude_route_result"] == route.to_mapping()


def test_l0_and_blocked_routes_cannot_build_claude_request(tmp_path):
    clear = _route_chain(tmp_path, "CLEAR", name="clear-request")
    _assert_invalid(
        lambda: subject.build_e5_claude_provider_request_v1(
            payload=clear[0],
            deepseek_review=clear[1],
            deepseek_adjudication=clear[2],
            route_result=clear[3],
            token_preflight=clear[4],
        )
    )
    payload = _payload(tmp_path, name="duplicate-request")
    review, adjudication = _review_and_adjudication(payload, "CAUTION")
    usage = _usage(l1=(payload.payload_sha256,))
    route = router.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=usage,
    )
    preflight = router.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=100,
        requested_output_tokens=100,
    )
    _assert_invalid(
        lambda: subject.build_e5_claude_provider_request_v1(
            payload=payload,
            deepseek_review=review,
            deepseek_adjudication=adjudication,
            route_result=route,
            token_preflight=preflight,
        )
    )


@pytest.mark.parametrize(
    ("changes"),
    (
        {"model_id": "deepseek-v4-pro-latest"},
        {"timeout_seconds": None},
        {"timeout_seconds": True},
        {"timeout_seconds": 0},
        {"timeout_seconds": -1},
        {"timeout_seconds": 61},
        {"provider_attempts": True},
        {"retry_count": 1},
        {"canonical_input_json": '{"api_key":"forbidden"}'},
        {"request_sha256": "0" * 64},
    ),
)
def test_request_tampering_fails_closed(tmp_path, changes):
    payload = _payload(tmp_path)
    request = subject.build_e5_deepseek_provider_request_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
    )
    _assert_invalid(lambda: replace(request, **changes))


def test_public_request_builders_expose_no_model_policy_or_envelope_inputs():
    forbidden = {
        "model_id",
        "provider",
        "timeout_seconds",
        "retry_count",
        "api_key",
        "signal_id",
        "delivery_id",
        "publication_timestamp",
        "telegram_message_id",
        "score",
        "llm_result",
        "valid_until",
        "ledger_revision",
    }
    for builder in (
        subject.build_e5_deepseek_provider_request_v1,
        subject.build_e5_claude_provider_request_v1,
    ):
        assert forbidden.isdisjoint(inspect.signature(builder).parameters)


def test_attempt_observation_contract_and_deterministic_response_digest(tmp_path):
    payload = _payload(tmp_path)
    review, _ = _review_and_adjudication(payload)
    request = subject.build_e5_deepseek_provider_request_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
    )
    first = subject.build_e5_provider_attempt_observation_v1(
        request=request,
        transport_outcome="SUCCESS",
        response_mapping=review.to_mapping(),
        measured_input_tokens=100,
        measured_output_tokens=50,
        billed_cost_micro_usd=10,
    )
    second = subject.build_e5_provider_attempt_observation_v1(
        request=request,
        transport_outcome="SUCCESS",
        response_mapping=review.to_mapping(),
        measured_input_tokens=100,
        measured_output_tokens=50,
        billed_cost_micro_usd=10,
    )
    assert first == second
    assert tuple(first.to_mapping()) == OBSERVATION_FIELDS
    assert first.attempt_number == 1
    assert first.response_digest_sha256 == _canonical_hash(review.to_mapping())
    assert _canonical_hash(json.loads(first.canonical_observation_json())) == (
        first.observation_sha256
    )
    with pytest.raises(TypeError):
        first.response_mapping["new"] = "forbidden"
    with pytest.raises(FrozenInstanceError):
        first.model_id = "other"


def test_observation_success_and_failure_shape_and_bool_validation(tmp_path):
    payload = _payload(tmp_path)
    request = subject.build_e5_deepseek_provider_request_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
    )
    _assert_invalid(
        lambda: subject.build_e5_provider_attempt_observation_v1(
            request=request,
            transport_outcome="SUCCESS",
            response_mapping=None,
            measured_input_tokens=1,
            measured_output_tokens=1,
            billed_cost_micro_usd=0,
        )
    )
    _assert_invalid(
        lambda: subject.build_e5_provider_attempt_observation_v1(
            request=request,
            transport_outcome="TIMEOUT",
            response_mapping={"unexpected": True},
            measured_input_tokens=1,
            measured_output_tokens=1,
            billed_cost_micro_usd=0,
        )
    )
    _assert_invalid(
        lambda: subject.build_e5_provider_attempt_observation_v1(
            request=request,
            transport_outcome="TIMEOUT",
            response_mapping=None,
            measured_input_tokens=True,
            measured_output_tokens=1,
            billed_cost_micro_usd=0,
        )
    )


def test_claude_review_l1_and_l2_reconstruct_deterministically(tmp_path):
    for decision in ("CAUTION", "HOLD"):
        chain = _route_chain(tmp_path, decision, name=f"review-{decision}")
        payload, _, _, route, _ = chain
        mapping = _claude_review_mapping(payload, route)
        first = subject.reconstruct_e5_claude_escalation_review_v1(mapping)
        second = subject.reconstruct_e5_claude_escalation_review_v1(dict(mapping))
        assert first == second
        assert first.route == route.route
        assert first.model_id == route.model_id
        assert tuple(first.to_mapping()) == CLAUDE_REVIEW_FIELDS
        assert _canonical_hash(json.loads(first.canonical_review_json())) == (
            first.review_sha256
        )


@pytest.mark.parametrize(
    ("mutation"),
    (
        "model",
        "route",
        "empty_summary",
        "whitespace_summary",
        "control_summary",
        "empty_fields",
        "unknown_field",
        "duplicate_field",
        "wrong_order",
        "missing_key",
        "extra_key",
        "wrong_hash",
    ),
)
def test_claude_review_schema_fail_closed(tmp_path, mutation):
    payload, _, _, route, _ = _route_chain(tmp_path, name=f"schema-{mutation}")
    mapping = _claude_review_mapping(payload, route)
    if mutation == "model":
        mapping["model_id"] = "claude-fable-5"
    elif mutation == "route":
        mapping["route"] = "L2"
    elif mutation == "empty_summary":
        mapping["review_summary"] = ""
    elif mutation == "whitespace_summary":
        mapping["review_summary"] = " padded "
    elif mutation == "control_summary":
        mapping["review_summary"] = "line\nbreak"
    elif mutation == "empty_fields":
        mapping["reviewed_evidence_fields"] = []
    elif mutation == "unknown_field":
        mapping["reviewed_evidence_fields"] = ["unknown"]
    elif mutation == "duplicate_field":
        mapping["reviewed_evidence_fields"] = ["mode", "mode"]
    elif mutation == "wrong_order":
        mapping["reviewed_evidence_fields"] = ["anchors", "mode"]
    elif mutation == "missing_key":
        mapping.pop("review_summary")
    elif mutation == "extra_key":
        mapping["decision"] = "CLEAR"
    else:
        mapping["review_sha256"] = "0" * 64
    _assert_invalid(
        lambda: subject.reconstruct_e5_claude_escalation_review_v1(mapping)
    )


def test_claude_review_has_no_score_geometry_or_publication_authority(tmp_path):
    payload, _, _, route, _ = _route_chain(tmp_path)
    review = _claude_review(payload, route)
    assert {
        "decision",
        "score",
        "side",
        "entry",
        "stop_loss",
        "tp1",
        "tp2",
        "publication_allowed",
        "telegram_send_allowed",
        "lifecycle_state",
    }.isdisjoint(review.to_mapping())


def test_deepseek_failed_preflight_holds_without_transport_call(tmp_path):
    payload = _payload(tmp_path)
    transport, calls = _fake_transport(raises=True)
    result = subject.invoke_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload, measured=4001),
        transport=transport,
    )
    assert calls == []
    assert result.final_result_code == "HOLD_TOKEN_LIMIT"
    assert result.provider_attempt_count == 0
    assert result.transport_invoked is False
    assert result.retry_count == 0


@pytest.mark.parametrize(
    ("outcome", "expected"),
    (
        ("TIMEOUT", "HOLD_PROVIDER_TIMEOUT"),
        ("TEMPORARILY_UNAVAILABLE", "HOLD_PROVIDER_UNAVAILABLE"),
        (
            "AUTHENTICATION_OR_PERMISSION_FAILURE",
            "HOLD_PROVIDER_CONFIGURATION",
        ),
        ("UNSUPPORTED_MODEL", "HOLD_MODEL_BINDING"),
        ("MALFORMED_OR_SCHEMA_INVALID_RESPONSE", "HOLD_INVALID_RESPONSE"),
        ("TOKEN_LIMIT_EXCEEDED", "HOLD_TOKEN_LIMIT"),
    ),
)
def test_deepseek_exact_d8_transport_failure_matrix(tmp_path, outcome, expected):
    payload = _payload(tmp_path, name=f"deepseek-{outcome}")
    review, _ = _review_and_adjudication(payload)
    result, calls = _invoke_deepseek(payload, review, outcome=outcome)
    assert len(calls) == 1
    assert result.underlying_failure_code == expected
    assert result.final_result_code == expected
    assert result.provider_attempt_count == 1
    assert result.retry_count == 0
    assert result.fallback_allowed is False


def test_deepseek_unexpected_transport_exception_maps_unavailable_once(tmp_path):
    payload = _payload(tmp_path)
    transport, calls = _fake_transport(raises=True)
    result = subject.invoke_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
        transport=transport,
    )
    assert len(calls) == 1
    assert result.final_result_code == "HOLD_PROVIDER_UNAVAILABLE"
    assert result.provider_attempt_count == 1
    assert result.retry_count == 0


def test_valid_deepseek_response_succeeds_once_with_no_authority(tmp_path):
    payload = _payload(tmp_path)
    review, _ = _review_and_adjudication(payload)
    result, calls = _invoke_deepseek(payload, review)
    assert len(calls) == 1
    assert result.final_result_code == (
        "PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED"
    )
    assert result.accepted_response_sha256 == review.review_sha256
    assert result.provider_attempt_count == 1
    assert tuple(result.to_mapping()) == RESULT_FIELDS
    assert _canonical_hash(json.loads(result.canonical_result_json())) == (
        result.result_sha256
    )
    assert all(
        value is False
        for value in (
            result.publication_allowed,
            result.telegram_send_allowed,
            result.slot_mutation_allowed,
            result.pair_lock_mutation_allowed,
            result.retry_allowed,
            result.fallback_allowed,
            result.stale_result_reuse_allowed,
        )
    )
    with pytest.raises(FrozenInstanceError):
        result.publication_allowed = True


@pytest.mark.parametrize(
    ("mutation", "expected"),
    (
        ("request", "HOLD_INVALID_RESPONSE"),
        ("payload", "HOLD_INVALID_RESPONSE"),
        ("model", "HOLD_MODEL_BINDING"),
        ("provider", "HOLD_MODEL_BINDING"),
        ("digest", "HOLD_INVALID_RESPONSE"),
        ("input", "HOLD_TOKEN_LIMIT"),
        ("output", "HOLD_TOKEN_LIMIT"),
    ),
)
def test_deepseek_stale_substitution_digest_and_token_rejection(
    tmp_path,
    mutation,
    expected,
):
    payload = _payload(tmp_path, name=f"deep-invalid-{mutation}")
    review, _ = _review_and_adjudication(payload)
    response_mapping = review.to_mapping()
    options = {}
    if mutation == "request":
        options["request_sha256"] = "1" * 64
    elif mutation == "payload":
        response_mapping = dict(response_mapping)
        response_mapping["payload_sha256"] = "2" * 64
    elif mutation == "model":
        response_mapping = dict(response_mapping)
        response_mapping["model_id"] = "claude-opus-5"
    elif mutation == "provider":
        options.update(provider="ANTHROPIC", model_id="claude-opus-5")
    elif mutation == "input":
        options["measured_input"] = 4001
    elif mutation == "output":
        options["measured_output"] = 501
    transport, calls = _fake_transport(
        response_mapping=response_mapping,
        **options,
    )
    if mutation == "digest":
        original = transport

        def transport(request):
            observation = original(request)
            return _unsafe_clone(
                observation,
                response_digest_sha256="3" * 64,
            )

    result = subject.invoke_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
        transport=transport,
    )
    assert len(calls) == 1
    assert result.final_result_code == expected
    assert result.retry_count == 0


def test_cross_payload_deepseek_response_is_rejected_as_stale(tmp_path):
    first = _payload(tmp_path, "SWING", "LONG", name="deep-first")
    second = _payload(tmp_path, "SWING", "SHORT", name="deep-second")
    stale_review, _ = _review_and_adjudication(first)
    current_review, _ = _review_and_adjudication(second)
    result, calls = _invoke_deepseek(
        second,
        current_review,
        response_mapping=stale_review.to_mapping(),
    )
    assert len(calls) == 1
    assert result.final_result_code == "HOLD_INVALID_RESPONSE"
    assert result.stale_result_reuse_allowed is False


@pytest.mark.parametrize(
    ("decision", "hard_gates", "score", "floor"),
    (
        ("CLEAR", True, 80, 70),
        ("CLEAR", False, 80, 70),
        ("CAUTION", True, 73, 70),
    ),
)
def test_l0_normal_and_deterministic_blocks_make_zero_calls(
    tmp_path,
    decision,
    hard_gates,
    score,
    floor,
):
    chain = _route_chain(
        tmp_path,
        decision,
        hard_gates=hard_gates,
        score=score,
        floor=floor,
        name=f"l0-{decision}-{hard_gates}-{score}",
    )
    transport, calls = _fake_transport(raises=True)
    result = subject.invoke_e5_claude_review_once_v1(
        payload=chain[0],
        deepseek_review=chain[1],
        deepseek_adjudication=chain[2],
        route_result=chain[3],
        token_preflight=chain[4],
        transport=transport,
    )
    assert calls == []
    assert result.final_result_code == "PASS_L0_NO_CLAUDE_REQUIRED"
    assert result.provider_attempt_count == 0
    assert result.publication_allowed is False


def test_duplicate_route_blocks_without_reusing_stale_review(tmp_path):
    payload = _payload(tmp_path, name="duplicate")
    review, adjudication = _review_and_adjudication(payload, "CAUTION")
    route = router.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=_usage(l1=(payload.payload_sha256,)),
    )
    preflight = router.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=100,
        requested_output_tokens=100,
    )
    transport, calls = _fake_transport(raises=True)
    result = subject.invoke_e5_claude_review_once_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route,
        token_preflight=preflight,
        transport=transport,
    )
    assert calls == []
    assert result.final_result_code == "HOLD_ESCALATION_INCOMPLETE"
    assert result.stale_result_reuse_allowed is False
    assert result.accepted_response_sha256 is None


@pytest.mark.parametrize(("decision", "usage"), (("CAUTION", "shared"), ("HOLD", "l2")))
def test_daily_ceiling_routes_hold_budget_without_call(tmp_path, decision, usage):
    payload = _payload(tmp_path, name=f"ceiling-{usage}")
    review, adjudication = _review_and_adjudication(payload, decision)
    daily_usage = (
        _usage(l1=tuple(f"{index:064x}" for index in range(1, 10)))
        if usage == "shared"
        else _usage(l2=tuple(f"{index:064x}" for index in range(1, 4)))
    )
    route = router.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=daily_usage,
    )
    preflight = router.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=100,
        requested_output_tokens=100,
    )
    transport, calls = _fake_transport(raises=True)
    result = subject.invoke_e5_claude_review_once_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route,
        token_preflight=preflight,
        transport=transport,
    )
    assert calls == []
    assert result.final_result_code == "HOLD_BUDGET_BLOCKED"
    assert result.provider_attempt_count == 0


def test_failed_claude_token_preflight_holds_without_call(tmp_path):
    payload, review, adjudication, route, _ = _route_chain(tmp_path)
    failed = router.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=4001,
        requested_output_tokens=100,
    )
    transport, calls = _fake_transport(raises=True)
    result = subject.invoke_e5_claude_review_once_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route,
        token_preflight=failed,
        transport=transport,
    )
    assert calls == []
    assert result.final_result_code == "HOLD_TOKEN_LIMIT"
    assert result.provider_attempt_count == 0


@pytest.mark.parametrize(
    ("decision", "outcome", "underlying"),
    (
        ("CAUTION", "TIMEOUT", "HOLD_PROVIDER_TIMEOUT"),
        ("HOLD", "TIMEOUT", "HOLD_PROVIDER_TIMEOUT"),
        ("CAUTION", "TEMPORARILY_UNAVAILABLE", "HOLD_PROVIDER_UNAVAILABLE"),
        (
            "CAUTION",
            "AUTHENTICATION_OR_PERMISSION_FAILURE",
            "HOLD_PROVIDER_CONFIGURATION",
        ),
        ("HOLD", "UNSUPPORTED_MODEL", "HOLD_MODEL_BINDING"),
        (
            "HOLD",
            "MALFORMED_OR_SCHEMA_INVALID_RESPONSE",
            "HOLD_INVALID_RESPONSE",
        ),
        ("CAUTION", "TOKEN_LIMIT_EXCEEDED", "HOLD_TOKEN_LIMIT"),
    ),
)
def test_claude_provider_failures_end_escalation_incomplete_once(
    tmp_path,
    decision,
    outcome,
    underlying,
):
    chain = _route_chain(tmp_path, decision, name=f"claude-{decision}-{outcome}")
    result, calls = _invoke_claude(chain, outcome=outcome)
    assert len(calls) == 1
    assert result.underlying_failure_code == underlying
    assert result.final_result_code == "HOLD_ESCALATION_INCOMPLETE"
    assert result.provider_attempt_count == 1
    assert result.retry_count == 0
    assert result.fallback_allowed is False


def test_claude_unexpected_exception_ends_escalation_incomplete_once(tmp_path):
    chain = _route_chain(tmp_path)
    result, calls = _invoke_claude(chain, raises=True)
    assert len(calls) == 1
    assert result.underlying_failure_code == "HOLD_PROVIDER_UNAVAILABLE"
    assert result.final_result_code == "HOLD_ESCALATION_INCOMPLETE"
    assert result.retry_count == 0


@pytest.mark.parametrize("decision", ("CAUTION", "HOLD"))
def test_valid_claude_opus_and_fable_responses_succeed_once(tmp_path, decision):
    chain = _route_chain(tmp_path, decision, name=f"success-{decision}")
    result, calls = _invoke_claude(chain)
    assert len(calls) == 1
    assert result.final_result_code == (
        "PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED"
    )
    assert result.model_id == (
        "claude-opus-5" if decision == "CAUTION" else "claude-fable-5"
    )
    assert result.provider_attempt_count == 1
    assert result.publication_allowed is False
    assert result.telegram_send_allowed is False
    assert result.retry_allowed is False


@pytest.mark.parametrize(
    ("decision", "cost"),
    (("CAUTION", 32501), ("HOLD", 100001)),
)
def test_claude_billed_cost_above_route_maximum_holds_budget(
    tmp_path,
    decision,
    cost,
):
    chain = _route_chain(tmp_path, decision, name=f"cost-{decision}")
    result, calls = _invoke_claude(chain, billed_cost=cost)
    assert len(calls) == 1
    assert result.underlying_failure_code == "HOLD_BUDGET_BLOCKED"
    assert result.final_result_code == "HOLD_BUDGET_BLOCKED"


@pytest.mark.parametrize(
    ("decision", "measured_input", "measured_output"),
    (
        ("CAUTION", 4001, 100),
        ("CAUTION", 100, 501),
        ("HOLD", 6001, 100),
        ("HOLD", 100, 801),
    ),
)
def test_claude_observed_token_overage_fails_escalation(
    tmp_path,
    decision,
    measured_input,
    measured_output,
):
    chain = _route_chain(tmp_path, decision, name=f"tokens-{decision}-{measured_input}")
    result, calls = _invoke_claude(
        chain,
        measured_input=measured_input,
        measured_output=measured_output,
    )
    assert len(calls) == 1
    assert result.underlying_failure_code == "HOLD_TOKEN_LIMIT"
    assert result.final_result_code == "HOLD_ESCALATION_INCOMPLETE"
    assert result.retry_count == 0


@pytest.mark.parametrize(
    ("mutation", "underlying"),
    (
        ("request", "HOLD_INVALID_RESPONSE"),
        ("provider", "HOLD_MODEL_BINDING"),
        ("model", "HOLD_MODEL_BINDING"),
        ("route_sha", "HOLD_INVALID_RESPONSE"),
        ("payload", "HOLD_INVALID_RESPONSE"),
        ("digest", "HOLD_INVALID_RESPONSE"),
    ),
)
def test_claude_stale_substitution_and_digest_rejection(
    tmp_path,
    mutation,
    underlying,
):
    chain = _route_chain(tmp_path, name=f"claude-invalid-{mutation}")
    payload, _, _, route, _ = chain
    mapping = _claude_review_mapping(payload, route)
    options = {}
    if mutation == "request":
        options["request_sha256"] = "4" * 64
    elif mutation == "provider":
        options.update(provider="DEEPSEEK", model_id="deepseek-v4-pro")
    elif mutation == "model":
        options.update(provider="ANTHROPIC", model_id="claude-fable-5")
    elif mutation == "route_sha":
        mapping["route_sha256"] = "5" * 64
    elif mutation == "payload":
        mapping["payload_sha256"] = "6" * 64
    transport, calls = _fake_transport(response_mapping=mapping, **options)
    if mutation == "digest":
        original = transport

        def transport(request):
            observation = original(request)
            return _unsafe_clone(
                observation,
                response_digest_sha256="7" * 64,
            )

    result = subject.invoke_e5_claude_review_once_v1(
        payload=chain[0],
        deepseek_review=chain[1],
        deepseek_adjudication=chain[2],
        route_result=chain[3],
        token_preflight=chain[4],
        transport=transport,
    )
    assert len(calls) == 1
    assert result.underlying_failure_code == underlying
    assert result.final_result_code == "HOLD_ESCALATION_INCOMPLETE"
    assert result.stale_result_reuse_allowed is False


def test_cross_payload_claude_response_is_rejected(tmp_path):
    first = _route_chain(tmp_path, name="claude-first")
    second = _route_chain(tmp_path, mode="SWING", side="SHORT", name="claude-second")
    stale_mapping = _claude_review_mapping(first[0], first[3])
    result, calls = _invoke_claude(second, response_mapping=stale_mapping)
    assert len(calls) == 1
    assert result.underlying_failure_code == "HOLD_INVALID_RESPONSE"
    assert result.final_result_code == "HOLD_ESCALATION_INCOMPLETE"


@pytest.mark.parametrize(
    ("mode", "side", "decision", "expected_route"),
    MODE_SIDE_DECISION,
)
def test_six_real_v2_invocation_chains(
    tmp_path,
    mode,
    side,
    decision,
    expected_route,
):
    chain = _route_chain(
        tmp_path,
        decision,
        mode=mode,
        side=side,
        name=f"real-{mode}-{side}",
    )
    assert chain[0].provider_binding_sha256 == ACTIVE_BINDING_SHA256
    assert chain[3].route == expected_route
    result, calls = _invoke_claude(chain)
    if expected_route == "L0":
        assert calls == []
        assert result.final_result_code == "PASS_L0_NO_CLAUDE_REQUIRED"
    else:
        assert len(calls) == 1
        assert result.final_result_code == (
            "PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED"
        )
    if decision == "HOLD":
        assert chain[3].deepseek_publication_block_preserved is True
        assert result.publication_allowed is False
    assert result.publication_allowed is False


def test_deepseek_execution_envelope_exposes_only_validated_review(tmp_path):
    payload = _payload(tmp_path, name="execution-deep-success")
    review, _ = _review_and_adjudication(payload)
    transport, calls = _fake_transport(response_mapping=review.to_mapping())
    execution = subject.execute_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
        transport=transport,
    )
    assert len(calls) == 1
    assert execution.accepted_deepseek_review == review
    assert execution.accepted_claude_review is None
    assert execution.invocation_result.accepted_response_sha256 == (
        review.review_sha256
    )
    assert tuple(execution.to_mapping()) == EXECUTION_FIELDS
    assert _canonical_hash(json.loads(execution.canonical_execution_json())) == (
        execution.execution_sha256
    )
    with pytest.raises(FrozenInstanceError):
        execution.accepted_deepseek_review = None


@pytest.mark.parametrize(
    ("outcome", "raises"),
    (
        ("TIMEOUT", False),
        ("MALFORMED_OR_SCHEMA_INVALID_RESPONSE", False),
        ("SUCCESS", True),
    ),
)
def test_deepseek_execution_failures_expose_no_review_once(
    tmp_path,
    outcome,
    raises,
):
    payload = _payload(tmp_path, name=f"execution-deep-fail-{outcome}-{raises}")
    transport, calls = _fake_transport(outcome=outcome, raises=raises)
    execution = subject.execute_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
        transport=transport,
    )
    assert len(calls) == 1
    assert execution.accepted_deepseek_review is None
    assert execution.accepted_claude_review is None
    assert execution.invocation_result.retry_count == 0


@pytest.mark.parametrize("decision", ("CAUTION", "HOLD"))
def test_claude_execution_envelope_exposes_exact_opus_or_fable_review(
    tmp_path,
    decision,
):
    chain = _route_chain(tmp_path, decision, name=f"execution-{decision}")
    expected = _claude_review(chain[0], chain[3])
    transport, calls = _fake_transport(response_mapping=expected.to_mapping())
    execution = subject.execute_e5_claude_review_once_v1(
        payload=chain[0],
        deepseek_review=chain[1],
        deepseek_adjudication=chain[2],
        route_result=chain[3],
        token_preflight=chain[4],
        transport=transport,
    )
    assert len(calls) == 1
    assert execution.accepted_deepseek_review is None
    assert execution.accepted_claude_review == expected
    assert execution.invocation_result.accepted_response_sha256 == (
        expected.review_sha256
    )


def test_l0_and_blocked_execution_envelopes_expose_no_review_or_call(tmp_path):
    clear = _route_chain(tmp_path, "CLEAR", name="execution-l0")
    transport, calls = _fake_transport(raises=True)
    l0 = subject.execute_e5_claude_review_once_v1(
        payload=clear[0],
        deepseek_review=clear[1],
        deepseek_adjudication=clear[2],
        route_result=clear[3],
        token_preflight=clear[4],
        transport=transport,
    )
    assert calls == []
    assert l0.invocation_result.final_result_code == "PASS_L0_NO_CLAUDE_REQUIRED"
    assert l0.accepted_deepseek_review is None
    assert l0.accepted_claude_review is None

    payload = _payload(tmp_path, name="execution-duplicate")
    review, adjudication = _review_and_adjudication(payload, "CAUTION")
    route = router.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=_usage(l1=(payload.payload_sha256,)),
    )
    preflight = router.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=0,
        requested_output_tokens=0,
    )
    blocked = subject.execute_e5_claude_review_once_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route,
        token_preflight=preflight,
        transport=transport,
    )
    assert calls == []
    assert blocked.invocation_result.final_result_code == (
        "HOLD_ESCALATION_INCOMPLETE"
    )
    assert blocked.accepted_deepseek_review is None
    assert blocked.accepted_claude_review is None


@pytest.mark.parametrize("decision", ("CAUTION", "HOLD"))
def test_claude_execution_failure_exposes_no_review_and_zero_retry(
    tmp_path,
    decision,
):
    chain = _route_chain(tmp_path, decision, name=f"execution-fail-{decision}")
    transport, calls = _fake_transport(outcome="TIMEOUT")
    execution = subject.execute_e5_claude_review_once_v1(
        payload=chain[0],
        deepseek_review=chain[1],
        deepseek_adjudication=chain[2],
        route_result=chain[3],
        token_preflight=chain[4],
        transport=transport,
    )
    assert len(calls) == 1
    assert execution.accepted_deepseek_review is None
    assert execution.accepted_claude_review is None
    assert execution.invocation_result.retry_count == 0


def test_execution_envelope_rejects_cross_lineage_and_mutual_reviews(tmp_path):
    first = _payload(tmp_path, name="execution-lineage-first")
    second = _payload(tmp_path, mode="SWING", side="SHORT", name="execution-lineage-second")
    first_review, _ = _review_and_adjudication(first)
    second_review, _ = _review_and_adjudication(second)
    transport, _ = _fake_transport(response_mapping=first_review.to_mapping())
    execution = subject.execute_e5_deepseek_review_once_v1(
        payload=first,
        token_preflight=_deepseek_preflight(first),
        transport=transport,
    )
    _assert_invalid(
        lambda: replace(execution, accepted_deepseek_review=second_review)
    )
    chain = _route_chain(tmp_path, name="execution-mutual")
    claude = _claude_review(chain[0], chain[3])
    _assert_invalid(lambda: replace(execution, accepted_claude_review=claude))
    _assert_invalid(lambda: replace(execution, execution_sha256="0" * 64))


def test_execute_and_invoke_deepseek_paths_are_result_compatible(tmp_path):
    payload = _payload(tmp_path, name="execution-wrapper-deep")
    review, _ = _review_and_adjudication(payload)
    first_transport, first_calls = _fake_transport(
        response_mapping=review.to_mapping()
    )
    second_transport, second_calls = _fake_transport(
        response_mapping=review.to_mapping()
    )
    execution = subject.execute_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
        transport=first_transport,
    )
    result = subject.invoke_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=_deepseek_preflight(payload),
        transport=second_transport,
    )
    assert len(first_calls) == len(second_calls) == 1
    assert result == execution.invocation_result


def test_execute_and_invoke_claude_paths_are_result_compatible(tmp_path):
    chain = _route_chain(tmp_path, name="execution-wrapper-claude")
    response = _claude_review_mapping(chain[0], chain[3])
    first_transport, first_calls = _fake_transport(response_mapping=response)
    second_transport, second_calls = _fake_transport(response_mapping=response)
    execution = subject.execute_e5_claude_review_once_v1(
        payload=chain[0],
        deepseek_review=chain[1],
        deepseek_adjudication=chain[2],
        route_result=chain[3],
        token_preflight=chain[4],
        transport=first_transport,
    )
    result = subject.invoke_e5_claude_review_once_v1(
        payload=chain[0],
        deepseek_review=chain[1],
        deepseek_adjudication=chain[2],
        route_result=chain[3],
        token_preflight=chain[4],
        transport=second_transport,
    )
    assert len(first_calls) == len(second_calls) == 1
    assert result == execution.invocation_result


def test_execution_envelope_exposes_no_raw_transport_or_secret_fields():
    assert {
        "transport_observation",
        "response_mapping",
        "exception",
        "exception_text",
        "credential",
        "api_key",
        "authorization",
        "provider_endpoint",
        "cache",
        "registry",
    }.isdisjoint(EXECUTION_FIELDS)


def test_result_tampering_and_bool_as_int_fail_closed(tmp_path):
    payload = _payload(tmp_path)
    review, _ = _review_and_adjudication(payload)
    result, _ = _invoke_deepseek(payload, review)
    _assert_invalid(lambda: replace(result, provider_attempt_count=True))
    _assert_invalid(lambda: replace(result, retry_count=1))
    _assert_invalid(lambda: replace(result, publication_allowed=True))
    _assert_invalid(lambda: replace(result, result_sha256="0" * 64))


def test_no_provider_retry_fallback_repair_or_secret_surface():
    source_path = Path(subject.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            imported_modules.add(node.module)
    forbidden_roots = {
        "requests",
        "httpx",
        "anthropic",
        "deepseek",
        "openai",
        "socket",
        "subprocess",
        "os",
        "dotenv",
        "keyring",
        "secrets",
    }
    assert all(
        module.casefold().split(".", 1)[0] not in forbidden_roots
        for module in imported_modules
    )
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert {
        "sleep",
        "getenv",
        "urlopen",
        "request",
        "post",
        "send",
        "publish",
        "claim_e4_publication_intent_v1",
        "record_e4_publication_success_v1",
    }.isdisjoint(call_names)
    invoke_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id
        in (
            "invoke_e5_deepseek_review_once_v1",
            "invoke_e5_claude_review_once_v1",
        )
    ]
    assert invoke_calls == []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            names = {
                child.id
                for child in ast.walk(node)
                if isinstance(child, ast.Name)
            }
            assert "transport" not in names


def test_no_publication_or_production_authority_in_public_contracts():
    all_fields = set(REQUEST_FIELDS).union(
        OBSERVATION_FIELDS,
        CLAUDE_REVIEW_FIELDS,
        RESULT_FIELDS,
        EXECUTION_FIELDS,
    )
    assert {
        "api_key",
        "authorization_header",
        "account_identifier",
        "signal_id",
        "telegram_message_id",
        "ledger_revision",
        "slot_identity",
        "pair_lock_identity",
        "publication_approved",
    }.isdisjoint(all_fields)
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for function in (
            subject.build_e5_deepseek_provider_request_v1,
            subject.build_e5_claude_provider_request_v1,
            subject.execute_e5_deepseek_review_once_v1,
            subject.execute_e5_claude_review_once_v1,
            subject.invoke_e5_deepseek_review_once_v1,
            subject.invoke_e5_claude_review_once_v1,
        )
        for parameter in inspect.signature(function).parameters.values()
    )


def test_injected_fake_transport_call_count_is_exact():
    assert FAKE_TRANSPORT_CALL_COUNT == 57
