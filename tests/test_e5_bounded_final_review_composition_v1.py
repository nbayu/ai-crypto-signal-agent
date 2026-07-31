from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e5_bounded_final_review_composition_v1 as subject
import engine.e5_provider_invocation_boundary_v1 as provider
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


COMPOSITION_FIELDS = (
    "composition_version",
    "provider_binding_sha256",
    "payload_sha256",
    "deepseek_token_preflight",
    "deepseek_invocation_result",
    "accepted_deepseek_review",
    "deepseek_adjudication",
    "claude_route_result",
    "claude_token_preflight",
    "claude_invocation_result",
    "accepted_claude_review",
    "usage_before",
    "usage_after",
    "underlying_d8_cause",
    "final_outcome_code",
    "may_continue_to_python_final_gate",
    "publication_blocked",
    "deepseek_provider_attempt_count",
    "claude_provider_attempt_count",
    "retry_count",
    "publication_allowed",
    "telegram_send_allowed",
    "slot_mutation_allowed",
    "pair_lock_mutation_allowed",
    "composition_sha256",
)
MODE_SIDE_DECISION = (
    ("SWING", "LONG", "CLEAR", "L0"),
    ("SWING", "SHORT", "CAUTION", "L1"),
    ("INTRADAY", "LONG", "HOLD", "L2"),
    ("INTRADAY", "SHORT", "CLEAR", "L0"),
    ("SCALP", "LONG", "CAUTION", "L1"),
    ("SCALP", "SHORT", "HOLD", "L2"),
)

INJECTED_FAKE_DEEPSEEK_TRANSPORT_CALL_COUNT = 0
INJECTED_FAKE_CLAUDE_TRANSPORT_CALL_COUNT = 0


def _canonical_hash(mapping):
    return hashlib.sha256(
        json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _assert_invalid(call):
    with pytest.raises(
        ValueError,
        match="^invalid E5 bounded final review composition$",
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


def _claude_response_mapping(request):
    canonical = json.loads(request.canonical_input_json)
    route = canonical["claude_route_result"]
    preimage = {
        "review_version": provider.E5_CLAUDE_ESCALATION_REVIEW_VERSION,
        "provider_binding_sha256": ACTIVE_BINDING_SHA256,
        "payload_sha256": request.payload_sha256,
        "route_sha256": request.upstream_identity_sha256,
        "route": request.route,
        "model_id": request.model_id,
        "review_summary": "Bounded advisory evidence.",
        "reviewed_evidence_fields": list(E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS),
    }
    assert route["route_sha256"] == request.upstream_identity_sha256
    return {**preimage, "review_sha256": _canonical_hash(preimage)}


def _transports(
    payload,
    decision,
    *,
    deep_outcome=provider.SUCCESS,
    claude_outcome=provider.SUCCESS,
    deep_raises=False,
    claude_raises=False,
    deep_provider=None,
    deep_model=None,
    claude_provider=None,
    claude_model=None,
    claude_measured_input=100,
    claude_measured_output=100,
    claude_billed_cost=100,
):
    deep_review, _ = _review_and_adjudication(payload, decision)
    deep_calls = []
    claude_calls = []

    def deepseek_transport(request):
        global INJECTED_FAKE_DEEPSEEK_TRANSPORT_CALL_COUNT
        INJECTED_FAKE_DEEPSEEK_TRANSPORT_CALL_COUNT += 1
        deep_calls.append(request.request_sha256)
        if deep_raises:
            raise RuntimeError("synthetic DeepSeek failure")
        response = (
            deep_review.to_mapping()
            if deep_outcome == provider.SUCCESS
            else None
        )
        return provider.build_e5_provider_attempt_observation_v1(
            request=request,
            transport_outcome=deep_outcome,
            response_mapping=response,
            measured_input_tokens=100,
            measured_output_tokens=100,
            billed_cost_micro_usd=100,
            provider=deep_provider,
            model_id=deep_model,
        )

    def claude_transport(request):
        global INJECTED_FAKE_CLAUDE_TRANSPORT_CALL_COUNT
        INJECTED_FAKE_CLAUDE_TRANSPORT_CALL_COUNT += 1
        claude_calls.append(request.request_sha256)
        if claude_raises:
            raise RuntimeError("synthetic Claude failure")
        response = (
            _claude_response_mapping(request)
            if claude_outcome == provider.SUCCESS
            else None
        )
        return provider.build_e5_provider_attempt_observation_v1(
            request=request,
            transport_outcome=claude_outcome,
            response_mapping=response,
            measured_input_tokens=claude_measured_input,
            measured_output_tokens=claude_measured_output,
            billed_cost_micro_usd=claude_billed_cost,
            provider=claude_provider,
            model_id=claude_model,
        )

    return deepseek_transport, claude_transport, deep_calls, claude_calls


def _compose_payload(
    payload,
    decision,
    *,
    usage=None,
    hard_gates=True,
    score=80,
    floor=70,
    deep_measured=100,
    deep_requested=100,
    claude_measured=100,
    claude_requested=100,
    claude_counts_required=None,
    **transport_options,
):
    if usage is None:
        usage = _usage()
    if claude_counts_required is None:
        claude_counts_required = decision in ("CAUTION", "HOLD") and hard_gates
        if decision == "CAUTION" and score - 3 <= floor:
            claude_counts_required = False
    deep_transport, claude_transport, deep_calls, claude_calls = _transports(
        payload,
        decision,
        **transport_options,
    )
    result = subject.compose_e5_bounded_final_review_v1(
        payload=payload,
        deterministic_hard_gates_passed=hard_gates,
        pre_review_score=score,
        mode_score_floor=floor,
        daily_usage=usage,
        deepseek_measured_input_tokens=deep_measured,
        deepseek_requested_output_tokens=deep_requested,
        deepseek_transport=deep_transport,
        claude_measured_input_tokens=(
            claude_measured if claude_counts_required else None
        ),
        claude_requested_output_tokens=(
            claude_requested if claude_counts_required else None
        ),
        claude_transport=claude_transport,
    )
    return result, deep_calls, claude_calls


def _compose(tmp_path, decision="CLEAR", **options):
    payload = _payload(
        tmp_path,
        options.pop("mode", "SWING"),
        options.pop("side", "LONG"),
        name=options.pop("name", f"composition-{decision}"),
    )
    return _compose_payload(payload, decision, **options)


def test_exact_version_outcomes_fields_and_frozen_contract():
    assert subject.E5_BOUNDED_FINAL_REVIEW_COMPOSITION_VERSION == (
        "e5-bounded-final-review-composition-v1"
    )
    assert subject.E5_BOUNDED_FINAL_REVIEW_OUTCOME_CODES == (
        "CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE",
        "CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE",
        "BLOCK_DEEPSEEK_TOKEN_PREFLIGHT",
        "BLOCK_DEEPSEEK_INVOCATION",
        "BLOCK_D6_DETERMINISTIC_POLICY",
        "BLOCK_D7_CLAUDE_ROUTING",
        "BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT",
        "BLOCK_D8_CLAUDE_INVOCATION",
        "BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE",
    )
    assert subject.FINAL_OUTCOME_CODE_COUNT == 9
    assert subject.COMPOSITION_FIELD_COUNT == 25
    assert is_dataclass(subject.E5BoundedFinalReviewCompositionV1)
    assert subject.E5BoundedFinalReviewCompositionV1.__dataclass_params__.frozen
    assert "__dict__" not in subject.E5BoundedFinalReviewCompositionV1.__slots__
    assert tuple(
        field.name for field in fields(subject.E5BoundedFinalReviewCompositionV1)
    ) == COMPOSITION_FIELDS


def test_mapping_hash_nulls_and_authority_are_deterministic(tmp_path):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        deep_measured=4001,
        claude_counts_required=False,
    )
    assert deep_calls == claude_calls == []
    assert tuple(result.to_mapping()) == COMPOSITION_FIELDS
    mapping = result.to_mapping()
    assert mapping["accepted_deepseek_review"] is None
    assert mapping["deepseek_adjudication"] is None
    assert mapping["claude_route_result"] is None
    assert "null" in json.dumps(mapping)
    assert _canonical_hash(json.loads(result.canonical_composition_json())) == (
        result.composition_sha256
    )
    assert all(
        value is False
        for value in (
            result.publication_allowed,
            result.telegram_send_allowed,
            result.slot_mutation_allowed,
            result.pair_lock_mutation_allowed,
        )
    )
    with pytest.raises(FrozenInstanceError):
        result.publication_allowed = True


@pytest.mark.parametrize(
    ("deep_measured", "deep_requested"),
    ((4001, 100), (100, 501)),
)
def test_deepseek_preflight_failures_block_with_zero_calls(
    tmp_path,
    deep_measured,
    deep_requested,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        deep_measured=deep_measured,
        deep_requested=deep_requested,
        claude_counts_required=False,
        name=f"deep-preflight-{deep_measured}-{deep_requested}",
    )
    assert deep_calls == claude_calls == []
    assert result.final_outcome_code == "BLOCK_DEEPSEEK_TOKEN_PREFLIGHT"
    assert result.underlying_d8_cause == "HOLD_TOKEN_LIMIT"
    assert result.deepseek_provider_attempt_count == 0
    assert result.claude_route_result is None
    assert result.usage_after == result.usage_before


@pytest.mark.parametrize(
    ("outcome", "cause"),
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
def test_deepseek_d8_failures_block_after_exactly_one_call(
    tmp_path,
    outcome,
    cause,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        deep_outcome=outcome,
        claude_counts_required=False,
        name=f"deep-d8-{outcome}",
    )
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.final_outcome_code == "BLOCK_DEEPSEEK_INVOCATION"
    assert result.underlying_d8_cause == cause
    assert result.accepted_deepseek_review is None
    assert result.deepseek_adjudication is None
    assert result.claude_route_result is None
    assert result.retry_count == 0


def test_unexpected_deepseek_exception_blocks_once_without_claude(tmp_path):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        deep_raises=True,
        claude_counts_required=False,
        name="deep-exception",
    )
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.underlying_d8_cause == "HOLD_PROVIDER_UNAVAILABLE"
    assert result.final_outcome_code == "BLOCK_DEEPSEEK_INVOCATION"


def test_clear_continuation_retains_l0_zero_attempt_evidence(tmp_path):
    result, deep_calls, claude_calls = _compose(tmp_path, "CLEAR", name="clear-l0")
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.final_outcome_code == (
        "CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE"
    )
    assert result.may_continue_to_python_final_gate is True
    assert result.publication_blocked is False
    assert result.claude_route_result.route == "L0"
    assert result.claude_token_preflight.decision_code == (
        "HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED"
    )
    assert result.claude_token_preflight.measured_input_tokens == 0
    assert result.claude_token_preflight.requested_output_tokens == 0
    assert result.claude_invocation_result.final_result_code == (
        "PASS_L0_NO_CLAUDE_REQUIRED"
    )
    assert result.claude_provider_attempt_count == 0
    assert result.accepted_claude_review is None


@pytest.mark.parametrize(
    ("decision", "hard_gates", "score", "floor"),
    (
        ("CLEAR", False, 80, 70),
        ("CAUTION", False, 80, 70),
        ("CAUTION", True, 73, 70),
        ("CAUTION", True, 72, 70),
    ),
)
def test_d6_deterministic_blocks_route_l0_without_claude(
    tmp_path,
    decision,
    hard_gates,
    score,
    floor,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        hard_gates=hard_gates,
        score=score,
        floor=floor,
        claude_counts_required=False,
        name=f"d6-{decision}-{hard_gates}-{score}",
    )
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.final_outcome_code == "BLOCK_D6_DETERMINISTIC_POLICY"
    assert result.claude_route_result.route == "L0"
    assert result.claude_invocation_result.provider_attempt_count == 0
    assert result.may_continue_to_python_final_gate is False
    assert result.publication_blocked is True
    assert result.usage_after == result.usage_before


@pytest.mark.parametrize("decision", ("CAUTION", "HOLD"))
def test_duplicate_l1_l2_route_is_non_none_and_blocks_without_call(
    tmp_path,
    decision,
):
    payload = _payload(tmp_path, name=f"duplicate-{decision}")
    usage = (
        _usage(l1=(payload.payload_sha256,))
        if decision == "CAUTION"
        else _usage(l2=(payload.payload_sha256,))
    )
    result, deep_calls, claude_calls = _compose_payload(
        payload,
        decision,
        usage=usage,
        claude_counts_required=False,
    )
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.claude_route_result is not None
    assert result.claude_route_result.decision_code == (
        "BLOCK_DUPLICATE_LOGICAL_REVIEW"
    )
    assert result.final_outcome_code == "BLOCK_D7_CLAUDE_ROUTING"
    assert result.underlying_d8_cause == "HOLD_ESCALATION_INCOMPLETE"
    assert result.claude_invocation_result.provider_attempt_count == 0
    assert result.usage_after == usage


@pytest.mark.parametrize("kind", ("shared", "l2"))
def test_daily_ceiling_routes_block_without_claude_call(tmp_path, kind):
    decision = "CAUTION" if kind == "shared" else "HOLD"
    usage = (
        _usage(l1=tuple(f"{index:064x}" for index in range(1, 10)))
        if kind == "shared"
        else _usage(l2=tuple(f"{index:064x}" for index in range(1, 4)))
    )
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        usage=usage,
        claude_counts_required=False,
        name=f"ceiling-{kind}",
    )
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.final_outcome_code == "BLOCK_D7_CLAUDE_ROUTING"
    assert result.underlying_d8_cause == "HOLD_BUDGET_BLOCKED"
    assert result.claude_route_result is not None
    assert result.claude_invocation_result.final_result_code == (
        "HOLD_BUDGET_BLOCKED"
    )
    assert result.usage_after == usage


@pytest.mark.parametrize(
    ("decision", "measured", "requested"),
    (
        ("CAUTION", 4001, 100),
        ("CAUTION", 100, 501),
        ("HOLD", 6001, 100),
        ("HOLD", 100, 801),
    ),
)
def test_claude_preflight_failure_retains_reservation_without_call(
    tmp_path,
    decision,
    measured,
    requested,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        claude_measured=measured,
        claude_requested=requested,
        name=f"claude-preflight-{decision}-{measured}-{requested}",
    )
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.final_outcome_code == "BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT"
    assert result.underlying_d8_cause == "HOLD_TOKEN_LIMIT"
    assert result.claude_provider_attempt_count == 0
    assert result.usage_after == result.claude_route_result.usage_after
    assert result.usage_after != result.usage_before


@pytest.mark.parametrize(
    ("decision", "outcome", "cause"),
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
        ("HOLD", "TOKEN_LIMIT_EXCEEDED", "HOLD_TOKEN_LIMIT"),
    ),
)
def test_claude_d8_failure_matrix_retains_reservation_once(
    tmp_path,
    decision,
    outcome,
    cause,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        claude_outcome=outcome,
        name=f"claude-d8-{decision}-{outcome}",
    )
    assert len(deep_calls) == len(claude_calls) == 1
    assert result.final_outcome_code == "BLOCK_D8_CLAUDE_INVOCATION"
    assert result.underlying_d8_cause == cause
    assert result.accepted_claude_review is None
    assert result.usage_after != result.usage_before
    assert result.retry_count == 0


@pytest.mark.parametrize("decision", ("CAUTION", "HOLD"))
def test_unexpected_claude_exception_blocks_once_and_retains_usage(
    tmp_path,
    decision,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        claude_raises=True,
        name=f"claude-exception-{decision}",
    )
    assert len(deep_calls) == len(claude_calls) == 1
    assert result.underlying_d8_cause == "HOLD_PROVIDER_UNAVAILABLE"
    assert result.final_outcome_code == "BLOCK_D8_CLAUDE_INVOCATION"
    assert result.usage_after != result.usage_before


@pytest.mark.parametrize(
    ("decision", "cost"),
    (("CAUTION", 32501), ("HOLD", 100001)),
)
def test_claude_billed_cost_excess_blocks_without_rollback(
    tmp_path,
    decision,
    cost,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        claude_billed_cost=cost,
        name=f"claude-cost-{decision}",
    )
    assert len(deep_calls) == len(claude_calls) == 1
    assert result.final_outcome_code == "BLOCK_D8_CLAUDE_INVOCATION"
    assert result.underlying_d8_cause == "HOLD_BUDGET_BLOCKED"
    assert result.usage_after != result.usage_before


@pytest.mark.parametrize(
    ("decision", "measured_input", "measured_output"),
    (
        ("CAUTION", 4001, 100),
        ("CAUTION", 100, 501),
        ("HOLD", 6001, 100),
        ("HOLD", 100, 801),
    ),
)
def test_claude_observed_token_excess_blocks_without_retry(
    tmp_path,
    decision,
    measured_input,
    measured_output,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        claude_measured_input=measured_input,
        claude_measured_output=measured_output,
        name=f"claude-observed-{decision}-{measured_input}-{measured_output}",
    )
    assert len(deep_calls) == len(claude_calls) == 1
    assert result.final_outcome_code == "BLOCK_D8_CLAUDE_INVOCATION"
    assert result.underlying_d8_cause == "HOLD_TOKEN_LIMIT"
    assert result.retry_count == 0


@pytest.mark.parametrize(
    ("decision", "route", "model", "outcome", "continues", "blocked"),
    (
        (
            "CAUTION",
            "L1",
            "claude-opus-5",
            "CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE",
            True,
            False,
        ),
        (
            "HOLD",
            "L2",
            "claude-fable-5",
            "BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE",
            False,
            True,
        ),
    ),
)
def test_l1_and_l2_success_preserve_exact_authority(
    tmp_path,
    decision,
    route,
    model,
    outcome,
    continues,
    blocked,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        name=f"success-{decision}",
    )
    assert len(deep_calls) == len(claude_calls) == 1
    assert result.claude_route_result.route == route
    assert result.claude_invocation_result.model_id == model
    assert result.accepted_claude_review is not None
    assert result.final_outcome_code == outcome
    assert result.may_continue_to_python_final_gate is continues
    assert result.publication_blocked is blocked
    assert result.publication_allowed is False


@pytest.mark.parametrize(
    ("mode", "side", "decision", "route"),
    MODE_SIDE_DECISION,
)
def test_six_real_v2_mode_side_composition_chains(
    tmp_path,
    mode,
    side,
    decision,
    route,
):
    result, deep_calls, claude_calls = _compose(
        tmp_path,
        decision,
        mode=mode,
        side=side,
        name=f"real-{mode}-{side}",
    )
    assert result.provider_binding_sha256 == ACTIVE_BINDING_SHA256
    assert len(deep_calls) == 1
    assert len(claude_calls) == (0 if route == "L0" else 1)
    assert result.claude_route_result.route == route
    assert result.retry_count == 0
    assert result.publication_allowed is False
    if decision == "HOLD":
        assert result.final_outcome_code == (
            "BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE"
        )
        assert result.may_continue_to_python_final_gate is False


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("deepseek_provider_attempt_count", True),
        ("claude_provider_attempt_count", True),
        ("retry_count", True),
        ("publication_allowed", True),
        ("telegram_send_allowed", True),
        ("slot_mutation_allowed", True),
        ("pair_lock_mutation_allowed", True),
        ("composition_sha256", "0" * 64),
    ),
)
def test_composition_tampering_and_bool_as_int_fail_closed(tmp_path, field, value):
    result, _, _ = _compose(
        tmp_path,
        "CLEAR",
        name=f"tamper-{field}",
    )
    _assert_invalid(lambda: replace(result, **{field: value}))


def test_constructor_rejects_missing_and_additional_fields(tmp_path):
    result, _, _ = _compose(tmp_path, "CLEAR", name="constructor-keys")
    values = {
        field.name: getattr(result, field.name)
        for field in fields(subject.E5BoundedFinalReviewCompositionV1)
    }
    missing = dict(values)
    missing.pop("payload_sha256")
    additional = {**values, "extra": "forbidden"}
    with pytest.raises(TypeError):
        subject.E5BoundedFinalReviewCompositionV1(**missing)
    with pytest.raises(TypeError):
        subject.E5BoundedFinalReviewCompositionV1(**additional)


@pytest.mark.parametrize(
    "mutation",
    (
        "review_without_route",
        "route_without_review",
        "adjudication_without_route",
        "cross_payload_route",
        "cross_review_route",
        "cross_adjudication_route",
        "cross_binding_route",
    ),
)
def test_field_presence_and_route_lineage_fail_closed(tmp_path, mutation):
    first, _, _ = _compose(tmp_path, "CLEAR", name=f"presence-first-{mutation}")
    second, _, _ = _compose(
        tmp_path,
        "CLEAR",
        mode="SWING",
        side="SHORT",
        name=f"presence-second-{mutation}",
    )
    changes = {}
    if mutation == "review_without_route":
        changes["claude_route_result"] = None
    elif mutation == "route_without_review":
        changes["accepted_deepseek_review"] = None
    elif mutation == "adjudication_without_route":
        changes["deepseek_adjudication"] = None
    else:
        route = second.claude_route_result
        if mutation == "cross_review_route":
            route = _unsafe_clone(
                route,
                deepseek_review_sha256=first.accepted_deepseek_review.review_sha256,
            )
        elif mutation == "cross_adjudication_route":
            route = _unsafe_clone(
                route,
                deepseek_adjudication_sha256=(
                    first.deepseek_adjudication.adjudication_sha256
                ),
            )
        elif mutation == "cross_binding_route":
            route = _unsafe_clone(route, provider_binding_sha256="0" * 64)
        changes["claude_route_result"] = route
    _assert_invalid(lambda: replace(first, **changes))


def test_historical_v1_payload_fails_before_transport(tmp_path):
    payload = _payload(tmp_path, name="historical-v1")
    v1 = _payload_with_registered_binding(
        payload,
        get_owner_frozen_e5_provider_model_price_binding_v1().binding_sha256,
    )
    deep_transport, claude_transport, deep_calls, claude_calls = _transports(
        payload,
        "CLEAR",
    )
    _assert_invalid(
        lambda: subject.compose_e5_bounded_final_review_v1(
            payload=v1,
            deterministic_hard_gates_passed=True,
            pre_review_score=80,
            mode_score_floor=70,
            daily_usage=_usage(),
            deepseek_measured_input_tokens=100,
            deepseek_requested_output_tokens=100,
            deepseek_transport=deep_transport,
            claude_measured_input_tokens=None,
            claude_requested_output_tokens=None,
            claude_transport=claude_transport,
        )
    )
    assert deep_calls == claude_calls == []


@pytest.mark.parametrize(
    "mutation",
    (
        "hard_gate_bool",
        "score_bool",
        "floor_bool",
        "deep_input_bool",
        "deep_output_bool",
        "claude_partial_none",
        "daily_day",
        "deep_transport",
        "claude_transport",
    ),
)
def test_invalid_inputs_fail_before_any_transport(tmp_path, mutation):
    payload = _payload(tmp_path, name=f"invalid-input-{mutation}")
    deep_transport, claude_transport, deep_calls, claude_calls = _transports(
        payload,
        "CLEAR",
    )
    values = {
        "payload": payload,
        "deterministic_hard_gates_passed": True,
        "pre_review_score": 80,
        "mode_score_floor": 70,
        "daily_usage": _usage(),
        "deepseek_measured_input_tokens": 100,
        "deepseek_requested_output_tokens": 100,
        "deepseek_transport": deep_transport,
        "claude_measured_input_tokens": None,
        "claude_requested_output_tokens": None,
        "claude_transport": claude_transport,
    }
    if mutation == "hard_gate_bool":
        values["deterministic_hard_gates_passed"] = 1
    elif mutation == "score_bool":
        values["pre_review_score"] = True
    elif mutation == "floor_bool":
        values["mode_score_floor"] = False
    elif mutation == "deep_input_bool":
        values["deepseek_measured_input_tokens"] = True
    elif mutation == "deep_output_bool":
        values["deepseek_requested_output_tokens"] = False
    elif mutation == "claude_partial_none":
        values["claude_measured_input_tokens"] = 100
    elif mutation == "daily_day":
        values["daily_usage"] = _usage(utc_day="2026-08-01")
    elif mutation == "deep_transport":
        values["deepseek_transport"] = None
    else:
        values["claude_transport"] = None
    _assert_invalid(lambda: subject.compose_e5_bounded_final_review_v1(**values))
    assert deep_calls == claude_calls == []


def test_retained_reservation_blocks_second_logical_review(tmp_path):
    payload = _payload(tmp_path, name="retained-reservation")
    first, first_deep, first_claude = _compose_payload(
        payload,
        "CAUTION",
        claude_outcome="TIMEOUT",
    )
    assert len(first_deep) == len(first_claude) == 1
    assert first.usage_after != first.usage_before
    second, second_deep, second_claude = _compose_payload(
        payload,
        "CAUTION",
        usage=first.usage_after,
        claude_counts_required=False,
    )
    assert len(second_deep) == 1
    assert second_claude == []
    assert second.final_outcome_code == "BLOCK_D7_CLAUDE_ROUTING"
    assert second.claude_route_result.decision_code == (
        "BLOCK_DUPLICATE_LOGICAL_REVIEW"
    )
    assert second.usage_after == first.usage_after


def test_public_signature_has_no_prebuilt_review_route_or_result_inputs():
    parameters = inspect.signature(
        subject.compose_e5_bounded_final_review_v1
    ).parameters
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in parameters.values()
    )
    assert {
        "deepseek_review",
        "deepseek_adjudication",
        "claude_route_result",
        "deepseek_invocation_result",
        "claude_invocation_result",
        "accepted_claude_review",
    }.isdisjoint(parameters)


def test_no_provider_publication_cache_secret_or_production_reachability():
    source = Path(subject.__file__).read_text(encoding="utf-8")
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
        "random",
        "uuid",
        "time",
        "datetime",
    }
    assert all(
        module.casefold().split(".", 1)[0] not in forbidden_roots
        for module in imported_modules
    )
    fields_and_parameters = set(COMPOSITION_FIELDS).union(
        inspect.signature(subject.compose_e5_bounded_final_review_v1).parameters
    )
    assert {
        "api_key",
        "credential",
        "authorization",
        "transport_observation",
        "raw_response_mapping",
        "exception_text",
        "response_cache",
        "stale_result_registry",
        "publication_intent",
        "telegram_message_id",
        "ledger_revision",
        "slot_identity",
        "pair_lock_identity",
    }.isdisjoint(fields_and_parameters)
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert {
        "send",
        "publish",
        "sleep",
        "getenv",
        "urlopen",
        "claim_e4_publication_intent_v1",
        "record_e4_publication_success_v1",
    }.isdisjoint(call_names)


def test_injected_fake_transport_counts_are_exact():
    assert INJECTED_FAKE_DEEPSEEK_TRANSPORT_CALL_COUNT == 69
    assert INJECTED_FAKE_CLAUDE_TRANSPORT_CALL_COUNT == 23


PREPARED_STAGE_FIELDS = (
    "prepared_stage_version",
    "provider_binding_sha256",
    "payload",
    "payload_sha256",
    "deepseek_token_preflight",
    "deepseek_invocation_result",
    "accepted_deepseek_review",
    "deepseek_adjudication",
    "claude_route_result",
    "usage_before",
    "usage_after",
    "pre_claude_outcome_code",
    "deepseek_provider_attempt_count",
    "retry_count",
    "prepared_stage_sha256",
)


def _prepare_and_resume(tmp_path, decision, *, name):
    payload = _payload(tmp_path, name=name)
    deep_transport, claude_transport, deep_calls, claude_calls = _transports(
        payload,
        decision,
    )
    stage = subject.prepare_e5_bounded_final_review_v1(
        payload=payload,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
        daily_usage=_usage(),
        deepseek_measured_input_tokens=100,
        deepseek_requested_output_tokens=100,
        deepseek_transport=deep_transport,
    )
    allowed = decision in ("CAUTION", "HOLD")
    result = subject.resume_e5_bounded_final_review_v1(
        prepared_stage=stage,
        confirmed_usage_after_sha256=(
            stage.usage_after.usage_sha256 if allowed else None
        ),
        claude_measured_input_tokens=100 if allowed else None,
        claude_requested_output_tokens=100 if allowed else None,
        claude_transport=claude_transport,
    )
    return payload, stage, result, deep_calls, claude_calls


def test_prepared_stage_exact_contract_mapping_hash_and_reconstruction(tmp_path):
    _, stage, _, deep_calls, claude_calls = _prepare_and_resume(
        tmp_path,
        "CAUTION",
        name="prepared-contract",
    )
    assert subject.E5_BOUNDED_FINAL_REVIEW_PREPARED_STAGE_VERSION == (
        "e5-bounded-final-review-prepared-stage-v1"
    )
    assert subject.PREPARED_STAGE_FIELD_COUNT == 15
    assert subject.PRE_CLAUDE_OUTCOME_CODE_COUNT == 7
    assert subject.E5_PRE_CLAUDE_OUTCOME_CODES == (
        "PRE_CLAUDE_BLOCK_DEEPSEEK_TOKEN_PREFLIGHT",
        "PRE_CLAUDE_BLOCK_DEEPSEEK_INVOCATION",
        "PRE_CLAUDE_BLOCK_D6_DETERMINISTIC_POLICY",
        "PRE_CLAUDE_BLOCK_D7_CLAUDE_ROUTING",
        "PRE_CLAUDE_L0_NO_CLAUDE",
        "PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED",
        "PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED",
    )
    assert tuple(
        field.name
        for field in fields(subject.E5BoundedFinalReviewPreparedStageV1)
    ) == PREPARED_STAGE_FIELDS
    assert subject.E5BoundedFinalReviewPreparedStageV1.__dataclass_params__.frozen
    assert "__dict__" not in subject.E5BoundedFinalReviewPreparedStageV1.__slots__
    assert tuple(stage.to_mapping()) == PREPARED_STAGE_FIELDS
    assert _canonical_hash(json.loads(stage.canonical_prepared_stage_json())) == (
        stage.prepared_stage_sha256
    )
    assert (
        subject.reconstruct_e5_bounded_final_review_prepared_stage_v1(
            stage.to_mapping()
        )
        == stage
    )
    assert len(deep_calls) == len(claude_calls) == 1
    with pytest.raises(FrozenInstanceError):
        stage.retry_count = 1


@pytest.mark.parametrize(
    ("decision", "pre_code", "claude_count"),
    (
        ("CLEAR", "PRE_CLAUDE_L0_NO_CLAUDE", 0),
        ("CAUTION", "PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED", 1),
        ("HOLD", "PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED", 1),
    ),
)
def test_prepare_resume_single_attempt_and_compose_hash_parity(
    tmp_path,
    decision,
    pre_code,
    claude_count,
):
    payload, stage, staged, deep_calls, claude_calls = _prepare_and_resume(
        tmp_path,
        decision,
        name=f"staged-{decision}",
    )
    assert stage.pre_claude_outcome_code == pre_code
    assert len(deep_calls) == 1
    assert len(claude_calls) == claude_count
    deep_transport, claude_transport, wrapper_deep, wrapper_claude = _transports(
        payload,
        decision,
    )
    wrapped = subject.compose_e5_bounded_final_review_v1(
        payload=payload,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
        daily_usage=_usage(),
        deepseek_measured_input_tokens=100,
        deepseek_requested_output_tokens=100,
        deepseek_transport=deep_transport,
        claude_measured_input_tokens=100 if claude_count else None,
        claude_requested_output_tokens=100 if claude_count else None,
        claude_transport=claude_transport,
    )
    assert staged.to_mapping() == wrapped.to_mapping()
    assert staged.composition_sha256 == wrapped.composition_sha256
    assert len(wrapper_deep) == 1
    assert len(wrapper_claude) == claude_count


def test_resume_confirmation_and_prepared_hash_fail_closed(tmp_path):
    payload = _payload(tmp_path, name="resume-confirmation")
    deep_transport, claude_transport, _, claude_calls = _transports(
        payload,
        "CAUTION",
    )
    stage = subject.prepare_e5_bounded_final_review_v1(
        payload=payload,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
        daily_usage=_usage(),
        deepseek_measured_input_tokens=100,
        deepseek_requested_output_tokens=100,
        deepseek_transport=deep_transport,
    )
    _assert_invalid(
        lambda: subject.resume_e5_bounded_final_review_v1(
            prepared_stage=stage,
            confirmed_usage_after_sha256="0" * 64,
            claude_measured_input_tokens=100,
            claude_requested_output_tokens=100,
            claude_transport=claude_transport,
        )
    )
    mapping = stage.to_mapping()
    mapping["prepared_stage_sha256"] = "0" * 64
    _assert_invalid(
        lambda: subject.reconstruct_e5_bounded_final_review_prepared_stage_v1(
            mapping
        )
    )
    assert claude_calls == []
