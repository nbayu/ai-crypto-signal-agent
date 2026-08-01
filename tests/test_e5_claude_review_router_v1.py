from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e5_claude_review_router_v1 as subject
import engine.e5_deepseek_technical_review_v1 as deepseek
from engine.e5_technical_review_payload_v1 import (
    E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    get_owner_frozen_e5_provider_model_price_binding_v1,
    get_owner_frozen_e5_provider_model_price_binding_v2,
    get_owner_frozen_e5_provider_model_price_binding_v3,
)
from test_e5_technical_review_payload_v1 import (
    _bundle as _payload_bundle,
    _payload_with_registered_binding,
)


UTC_DAY = "2026-07-30"
ACTIVE_BINDING_SHA256 = (
    "dc2454ffdc7f05978a168f88beaf892e7e04387053a0b91c89da79adccf3778e"
)
MODE_SIDE_DECISION = (
    ("SWING", "LONG", "CLEAR", "L0"),
    ("SWING", "SHORT", "CAUTION", "L1"),
    ("INTRADAY", "LONG", "HOLD", "L2"),
    ("INTRADAY", "SHORT", "CLEAR", "L0"),
    ("SCALP", "LONG", "CAUTION", "L1"),
    ("SCALP", "SHORT", "HOLD", "L2"),
)
REASONS = {
    "CLEAR": ("CLEAR_NO_MATERIAL_CONFLICT",),
    "CAUTION": ("CAUTION_LIMITED_EVIDENCE",),
    "HOLD": ("HOLD_MATERIAL_CONTRADICTION",),
}
USAGE_FIELDS = (
    "usage_version",
    "utc_day",
    "l1_reviewed_payload_sha256s",
    "l2_reviewed_payload_sha256s",
    "committed_maximum_cost_micro_usd",
    "usage_sha256",
)
ROUTE_FIELDS = (
    "router_version",
    "provider_binding_sha256",
    "payload_sha256",
    "deepseek_review_sha256",
    "deepseek_adjudication_sha256",
    "route",
    "claude_required",
    "model_id",
    "input_hard_limit_tokens",
    "output_hard_limit_tokens",
    "timeout_seconds",
    "provider_attempts",
    "retry_count",
    "maximum_review_cost_micro_usd",
    "deepseek_publication_block_preserved",
    "usage_before_sha256",
    "usage_after",
    "decision_code",
    "route_sha256",
)
PREFLIGHT_FIELDS = (
    "preflight_version",
    "provider_binding_sha256",
    "route_sha256",
    "payload_sha256",
    "route",
    "model_id",
    "measured_input_tokens",
    "requested_output_tokens",
    "input_hard_limit_tokens",
    "output_hard_limit_tokens",
    "within_limits",
    "decision_code",
    "preflight_sha256",
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _payload(tmp_path, mode="SWING", side="LONG", name="router"):
    return _payload_bundle(tmp_path, mode, side, name=name)[2]


def _review_and_adjudication(
    payload,
    decision="CLEAR",
    *,
    hard_gates=True,
    score=80,
    floor=70,
):
    review = deepseek.build_e5_deepseek_structured_review_v1(
        payload=payload,
        model_id="deepseek-v4-pro",
        decision=decision,
        reason_codes=REASONS[decision],
        concise_reason=f"Deterministic {decision.lower()} routing evidence.",
        reviewed_evidence_fields=E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    )
    adjudication = deepseek.adjudicate_e5_deepseek_technical_review_v1(
        payload=payload,
        review=review,
        deterministic_hard_gates_passed=hard_gates,
        pre_review_score=score,
        mode_score_floor=floor,
    )
    return review, adjudication


def _usage(*, l1=(), l2=(), utc_day=UTC_DAY):
    preimage = {
        "usage_version": subject.E5_CLAUDE_DAILY_USAGE_VERSION,
        "utc_day": utc_day,
        "l1_reviewed_payload_sha256s": list(l1),
        "l2_reviewed_payload_sha256s": list(l2),
        "committed_maximum_cost_micro_usd": (
            len(l1) * subject.CLAUDE_L1_MAXIMUM_REVIEW_COST_MICRO_USD
            + len(l2) * subject.CLAUDE_L2_MAXIMUM_REVIEW_COST_MICRO_USD
        ),
    }
    digest = hashlib.sha256(
        json.dumps(
            preimage,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return subject.reconstruct_e5_claude_daily_usage_v1(
        {**preimage, "usage_sha256": digest}
    )


def _route(
    tmp_path,
    decision="CLEAR",
    *,
    usage=None,
    hard_gates=True,
    score=80,
    floor=70,
    mode="SWING",
    side="LONG",
    name="router",
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
        usage = subject.create_empty_e5_claude_daily_usage_v1(utc_day=UTC_DAY)
    result = subject.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=usage,
    )
    return payload, review, adjudication, result


def _unsafe_clone(value, **changes):
    clone = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return clone


def _assert_invalid(call):
    with pytest.raises(ValueError, match="^invalid E5 Claude review router$"):
        call()


def test_exact_versions_routes_decision_codes_and_cost_authority():
    assert subject.E5_CLAUDE_REVIEW_ROUTER_VERSION == (
        "e5-claude-review-router-v1"
    )
    assert subject.E5_CLAUDE_DAILY_USAGE_VERSION == "e5-claude-daily-usage-v1"
    assert subject.E5_CLAUDE_TOKEN_PREFLIGHT_VERSION == (
        "e5-claude-token-preflight-v1"
    )
    assert subject.ACTIVE_PROVIDER_BINDING_SHA256 == ACTIVE_BINDING_SHA256
    assert subject.CLAUDE_ROUTES == ("L0", "L1", "L2")
    assert subject.E5_CLAUDE_ROUTER_DECISION_CODES == (
        "ROUTE_L0_NO_CLAUDE_REQUIRED",
        "ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE",
        "ROUTE_L1_CLAUDE_REVIEW_REQUIRED",
        "ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED",
        "BLOCK_DUPLICATE_LOGICAL_REVIEW",
        "BLOCK_SHARED_DAILY_REVIEW_CEILING",
        "BLOCK_L2_DAILY_REVIEW_CEILING",
    )
    assert subject.E5_CLAUDE_TOKEN_PREFLIGHT_DECISION_CODES == (
        "PASS_CLAUDE_TOKEN_BUDGET",
        "HOLD_CLAUDE_INPUT_TOKEN_LIMIT",
        "HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT",
        "HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED",
    )
    assert not hasattr(subject, "BLOCK_MAXIMUM_DAILY_COST")
    assert subject.CLAUDE_L1_MODEL_ID == "claude-opus-5"
    assert subject.CLAUDE_L2_MODEL_ID == "claude-fable-5"
    assert subject.CLAUDE_L1_MAXIMUM_REVIEW_COST_MICRO_USD == 32500
    assert subject.CLAUDE_L2_MAXIMUM_REVIEW_COST_MICRO_USD == 100000
    assert subject.SHARED_DAILY_LOGICAL_REVIEW_CEILING == 9
    assert subject.L2_DAILY_LOGICAL_REVIEW_CEILING == 3
    assert subject.MAXIMUM_DAILY_COST_MICRO_USD == 495000
    assert 6 * 32500 + 3 * 100000 == 495000


def test_active_binding_is_exact_v3_with_unchanged_v2_claude_policy():
    v2 = get_owner_frozen_e5_provider_model_price_binding_v2()
    binding = get_owner_frozen_e5_provider_model_price_binding_v3()
    assert binding.binding_version == "e5-provider-model-price-binding-v3"
    assert binding.binding_sha256 == ACTIVE_BINDING_SHA256
    assert (
        binding.claude_l1_model_id,
        binding.claude_l1_input_hard_limit_tokens,
        binding.claude_l1_output_hard_limit_tokens,
        binding.claude_l1_timeout_seconds,
        binding.claude_l1_provider_attempts,
        binding.claude_l1_retry_count,
        binding.claude_l1_max_cost_micro_usd,
    ) == ("claude-opus-5", 4000, 500, 10, 1, 0, 32500)
    assert (
        binding.claude_l2_model_id,
        binding.claude_l2_input_hard_limit_tokens,
        binding.claude_l2_output_hard_limit_tokens,
        binding.claude_l2_timeout_seconds,
        binding.claude_l2_provider_attempts,
        binding.claude_l2_retry_count,
        binding.claude_l2_max_cost_micro_usd,
    ) == ("claude-fable-5", 6000, 800, 20, 1, 0, 100000)
    claude_policy_fields = (
        "claude_l1_model_id",
        "claude_l1_input_hard_limit_tokens",
        "claude_l1_output_hard_limit_tokens",
        "claude_l1_timeout_seconds",
        "claude_l1_provider_attempts",
        "claude_l1_retry_count",
        "claude_l1_base_input_usd_per_mtok",
        "claude_l1_output_usd_per_mtok",
        "claude_l1_max_cost_micro_usd",
        "claude_l2_model_id",
        "claude_l2_input_hard_limit_tokens",
        "claude_l2_output_hard_limit_tokens",
        "claude_l2_timeout_seconds",
        "claude_l2_provider_attempts",
        "claude_l2_retry_count",
        "claude_l2_base_input_usd_per_mtok",
        "claude_l2_output_usd_per_mtok",
        "claude_l2_max_cost_micro_usd",
        "shared_l1_l2_daily_logical_review_ceiling",
        "l2_daily_logical_review_ceiling",
        "maximum_daily_cost_micro_usd",
    )
    assert tuple(getattr(binding, field) for field in claude_policy_fields) == tuple(
        getattr(v2, field) for field in claude_policy_fields
    )
    assert binding.latest_alias_allowed is False
    assert binding.cross_provider_substitution_allowed is False
    assert "claude-sonnet-5" != subject.CLAUDE_L1_MODEL_ID


def test_exact_public_field_inventories():
    assert tuple(field.name for field in fields(subject.E5ClaudeDailyUsageV1)) == (
        USAGE_FIELDS
    )
    assert tuple(
        field.name for field in fields(subject.E5ClaudeReviewRouteResultV1)
    ) == ROUTE_FIELDS
    assert tuple(
        field.name for field in fields(subject.E5ClaudeTokenPreflightResultV1)
    ) == PREFLIGHT_FIELDS


@pytest.mark.parametrize(
    "contract",
    (
        subject.E5ClaudeDailyUsageV1,
        subject.E5ClaudeReviewRouteResultV1,
        subject.E5ClaudeTokenPreflightResultV1,
    ),
)
def test_results_are_frozen_and_slotted(contract):
    assert is_dataclass(contract)
    assert contract.__dataclass_params__.frozen is True
    assert "__dict__" not in contract.__dict__


def test_v1_bound_payload_is_rejected_as_active_input(tmp_path):
    payload = _payload(tmp_path)
    historical = _payload_with_registered_binding(
        payload,
        get_owner_frozen_e5_provider_model_price_binding_v1().binding_sha256,
    )
    review, adjudication = _review_and_adjudication(payload)
    usage = subject.create_empty_e5_claude_daily_usage_v1(utc_day=UTC_DAY)
    _assert_invalid(
        lambda: subject.route_e5_claude_review_v1(
            payload=historical,
            deepseek_review=review,
            deepseek_adjudication=adjudication,
            daily_usage=usage,
        )
    )


def test_empty_usage_mapping_hash_and_reconstruction_are_deterministic():
    first = subject.create_empty_e5_claude_daily_usage_v1(utc_day=UTC_DAY)
    second = subject.create_empty_e5_claude_daily_usage_v1(utc_day=UTC_DAY)
    assert first == second
    assert first.l1_reviewed_payload_sha256s == ()
    assert first.l2_reviewed_payload_sha256s == ()
    assert first.committed_maximum_cost_micro_usd == 0
    assert hashlib.sha256(first.canonical_usage_json().encode()).hexdigest() == (
        first.usage_sha256
    )
    assert subject.reconstruct_e5_claude_daily_usage_v1(
        dict(reversed(tuple(first.to_mapping().items())))
    ) == first
    _assert_invalid(lambda: replace(first, usage_sha256="0" * 64))


@pytest.mark.parametrize(
    "utc_day",
    (
        "2026-7-30",
        "2026-07-30 ",
        " 2026-07-30",
        "2026-02-30",
        "2026-07-30T00:00:00Z",
        "",
    ),
)
def test_usage_requires_exact_canonical_utc_day(utc_day):
    _assert_invalid(
        lambda: subject.create_empty_e5_claude_daily_usage_v1(utc_day=utc_day)
    )


@pytest.mark.parametrize(
    ("l1", "l2"),
    (
        ((_sha(1), _sha(1)), ()),
        ((), (_sha(1), _sha(1))),
        ((_sha(1),), (_sha(1),)),
        (("A" * 64,), ()),
    ),
)
def test_usage_identities_are_lowercase_unique_and_disjoint(l1, l2):
    _assert_invalid(lambda: _usage(l1=l1, l2=l2))


@pytest.mark.parametrize(
    "mutation",
    ("cost", "too_many", "too_many_l2", "above_max", "bool_cost"),
)
def test_usage_fails_closed_on_arithmetic_or_ceiling_violation(mutation):
    usage = _usage(l1=(_sha(1),), l2=(_sha(2),))
    mapping = usage.to_mapping()
    if mutation == "cost":
        mapping["committed_maximum_cost_micro_usd"] = 1
    elif mutation == "too_many":
        mapping["l1_reviewed_payload_sha256s"] = [
            _sha(index) for index in range(1, 11)
        ]
        mapping["committed_maximum_cost_micro_usd"] = 325000
    elif mutation == "too_many_l2":
        mapping["l1_reviewed_payload_sha256s"] = []
        mapping["l2_reviewed_payload_sha256s"] = [
            _sha(index) for index in range(1, 5)
        ]
        mapping["committed_maximum_cost_micro_usd"] = 400000
    elif mutation == "above_max":
        mapping["l1_reviewed_payload_sha256s"] = [
            _sha(index) for index in range(1, 7)
        ]
        mapping["l2_reviewed_payload_sha256s"] = [
            _sha(index) for index in range(7, 10)
        ]
        mapping["committed_maximum_cost_micro_usd"] = 495001
    else:
        mapping["committed_maximum_cost_micro_usd"] = True
    _assert_invalid(lambda: subject.reconstruct_e5_claude_daily_usage_v1(mapping))


@pytest.mark.parametrize("l2_count", (0, 1, 2, 3))
def test_nine_review_valid_combinations_never_exceed_maximum_cost(l2_count):
    l1_count = 9 - l2_count
    usage = _usage(
        l1=tuple(_sha(index) for index in range(1, l1_count + 1)),
        l2=tuple(
            _sha(index) for index in range(l1_count + 1, 10)
        ),
    )
    assert len(usage.l1_reviewed_payload_sha256s) + len(
        usage.l2_reviewed_payload_sha256s
    ) == 9
    assert usage.committed_maximum_cost_micro_usd <= 495000
    if l2_count == 3:
        assert usage.committed_maximum_cost_micro_usd == 495000


@pytest.mark.parametrize("mutation", ("missing", "extra", "tuple"))
def test_usage_reconstruction_requires_exact_keys_and_json_array_types(mutation):
    mapping = _usage().to_mapping()
    if mutation == "missing":
        mapping.pop("utc_day")
    elif mutation == "extra":
        mapping["metadata"] = "forbidden"
    else:
        mapping["l1_reviewed_payload_sha256s"] = ()
    _assert_invalid(lambda: subject.reconstruct_e5_claude_daily_usage_v1(mapping))


def test_usage_day_must_match_payload_evaluation_utc_day(tmp_path):
    payload = _payload(tmp_path)
    review, adjudication = _review_and_adjudication(payload)
    usage = subject.create_empty_e5_claude_daily_usage_v1(
        utc_day="2026-07-31"
    )
    _assert_invalid(
        lambda: subject.route_e5_claude_review_v1(
            payload=payload,
            deepseek_review=review,
            deepseek_adjudication=adjudication,
            daily_usage=usage,
        )
    )


@pytest.mark.parametrize(
    (
        "decision",
        "route",
        "code",
        "required",
        "model",
        "input_limit",
        "output_limit",
        "timeout",
        "attempts",
        "retry",
        "cost",
        "block_preserved",
    ),
    (
        (
            "CLEAR", "L0", "ROUTE_L0_NO_CLAUDE_REQUIRED", False, None,
            0, 0, 0, 0, 0, 0, False,
        ),
        (
            "CAUTION", "L1", "ROUTE_L1_CLAUDE_REVIEW_REQUIRED", True,
            "claude-opus-5", 4000, 500, 10, 1, 0, 32500, False,
        ),
        (
            "HOLD", "L2",
            "ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED", True,
            "claude-fable-5", 6000, 800, 20, 1, 0, 100000, True,
        ),
    ),
)
def test_exact_primary_route_profiles(
    tmp_path,
    decision,
    route,
    code,
    required,
    model,
    input_limit,
    output_limit,
    timeout,
    attempts,
    retry,
    cost,
    block_preserved,
):
    _, _, adjudication, result = _route(tmp_path, decision)
    assert result.route == route
    assert result.decision_code == code
    assert result.claude_required is required
    assert result.model_id == model
    assert result.input_hard_limit_tokens == input_limit
    assert result.output_hard_limit_tokens == output_limit
    assert result.timeout_seconds == timeout
    assert result.provider_attempts == attempts
    assert result.retry_count == retry
    assert result.maximum_review_cost_micro_usd == cost
    assert result.deepseek_publication_block_preserved is block_preserved
    if route == "L0":
        assert result.usage_after.usage_sha256 == result.usage_before_sha256
    elif route == "L1":
        assert result.usage_after.l1_reviewed_payload_sha256s == (
            result.payload_sha256,
        )
    else:
        assert result.usage_after.l2_reviewed_payload_sha256s == (
            result.payload_sha256,
        )
        assert adjudication.may_continue_to_python_final_gate is False
        assert adjudication.publication_blocked is True


@pytest.mark.parametrize(
    ("decision", "hard_gates", "score", "floor", "outcome"),
    (
        ("CLEAR", False, 80, 70, "STOP_DETERMINISTIC_HARD_GATE"),
        ("CAUTION", False, 80, 70, "STOP_DETERMINISTIC_HARD_GATE"),
        ("CAUTION", True, 73, 70, "STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR"),
        ("CAUTION", True, 72, 70, "STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR"),
    ),
)
def test_deterministic_blocks_route_l0_without_usage_change(
    tmp_path, decision, hard_gates, score, floor, outcome
):
    _, _, adjudication, result = _route(
        tmp_path,
        decision,
        hard_gates=hard_gates,
        score=score,
        floor=floor,
    )
    assert adjudication.outcome_code == outcome
    assert result.route == "L0"
    assert result.decision_code == "ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE"
    assert result.claude_required is False
    assert result.model_id is None
    assert result.deepseek_publication_block_preserved is True
    assert result.usage_after.usage_sha256 == result.usage_before_sha256


def test_route_mapping_and_sha_are_deterministic_and_tamper_evident(tmp_path):
    first = _route(tmp_path, "CAUTION", name="first")[3]
    second = _route(tmp_path, "CAUTION", name="second")[3]
    assert first == second
    assert tuple(first.to_mapping()) == ROUTE_FIELDS
    assert hashlib.sha256(first.canonical_route_json().encode()).hexdigest() == (
        first.route_sha256
    )
    _assert_invalid(lambda: replace(first, route_sha256="0" * 64))
    _assert_invalid(lambda: replace(first, model_id="claude-opus-5-latest"))
    _assert_invalid(lambda: replace(first, provider_attempts=True))


def test_cross_payload_review_and_forged_adjudication_fail_closed(tmp_path):
    first = _payload(tmp_path, "SWING", "LONG", name="first")
    second = _payload(tmp_path, "SWING", "SHORT", name="second")
    review, adjudication = _review_and_adjudication(first)
    usage = subject.create_empty_e5_claude_daily_usage_v1(utc_day=UTC_DAY)
    _assert_invalid(
        lambda: subject.route_e5_claude_review_v1(
            payload=second,
            deepseek_review=review,
            deepseek_adjudication=adjudication,
            daily_usage=usage,
        )
    )
    forged = _unsafe_clone(adjudication, adjudication_sha256="0" * 64)
    _assert_invalid(
        lambda: subject.route_e5_claude_review_v1(
            payload=first,
            deepseek_review=review,
            deepseek_adjudication=forged,
            daily_usage=usage,
        )
    )


def test_contradictory_review_and_adjudication_combination_fails_closed(tmp_path):
    payload = _payload(tmp_path)
    clear_review, _ = _review_and_adjudication(payload, "CLEAR")
    _, caution_adjudication = _review_and_adjudication(payload, "CAUTION")
    usage = subject.create_empty_e5_claude_daily_usage_v1(utc_day=UTC_DAY)
    _assert_invalid(
        lambda: subject.route_e5_claude_review_v1(
            payload=payload,
            deepseek_review=clear_review,
            deepseek_adjudication=caution_adjudication,
            daily_usage=usage,
        )
    )


def test_router_signature_has_no_caller_controlled_route_or_authority():
    parameters = inspect.signature(subject.route_e5_claude_review_v1).parameters
    assert tuple(parameters) == (
        "payload",
        "deepseek_review",
        "deepseek_adjudication",
        "daily_usage",
    )
    assert {
        "route",
        "model_id",
        "timeout",
        "retry",
        "cost",
        "provider_client",
        "api_key",
    }.isdisjoint(parameters)


@pytest.mark.parametrize("decision", ("CAUTION", "HOLD"))
def test_duplicate_same_route_blocks_without_usage_mutation(tmp_path, decision):
    payload, _, _, first = _route(tmp_path, decision)
    review, adjudication = _review_and_adjudication(payload, decision)
    blocked = subject.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=first.usage_after,
    )
    assert blocked.decision_code == "BLOCK_DUPLICATE_LOGICAL_REVIEW"
    assert blocked.route == first.route
    assert blocked.claude_required is False
    assert blocked.model_id is None
    assert blocked.usage_after == first.usage_after
    assert blocked.deepseek_publication_block_preserved is (decision == "HOLD")


@pytest.mark.parametrize(
    ("decision", "existing_route"),
    (("CAUTION", "l2"), ("HOLD", "l1")),
)
def test_cross_route_duplicate_blocks(tmp_path, decision, existing_route):
    payload = _payload(tmp_path)
    review, adjudication = _review_and_adjudication(payload, decision)
    usage = _usage(
        l1=(payload.payload_sha256,) if existing_route == "l1" else (),
        l2=(payload.payload_sha256,) if existing_route == "l2" else (),
    )
    result = subject.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=usage,
    )
    assert result.decision_code == "BLOCK_DUPLICATE_LOGICAL_REVIEW"
    assert result.usage_after == usage


def test_ninth_shared_reservation_succeeds_and_tenth_blocks(tmp_path):
    payload = _payload(tmp_path)
    review, adjudication = _review_and_adjudication(payload, "CAUTION")
    eight = _usage(l1=tuple(_sha(index) for index in range(1, 9)))
    ninth = subject.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=eight,
    )
    assert ninth.decision_code == "ROUTE_L1_CLAUDE_REVIEW_REQUIRED"
    assert len(ninth.usage_after.l1_reviewed_payload_sha256s) == 9
    assert ninth.usage_after.l1_reviewed_payload_sha256s[:-1] == (
        eight.l1_reviewed_payload_sha256s
    )
    other_payload = _payload(tmp_path, "SWING", "SHORT", name="tenth")
    other_review, other_adjudication = _review_and_adjudication(
        other_payload, "CAUTION"
    )
    tenth = subject.route_e5_claude_review_v1(
        payload=other_payload,
        deepseek_review=other_review,
        deepseek_adjudication=other_adjudication,
        daily_usage=ninth.usage_after,
    )
    assert tenth.decision_code == "BLOCK_SHARED_DAILY_REVIEW_CEILING"
    assert tenth.route == "L1"
    assert tenth.model_id is None
    assert tenth.usage_after == ninth.usage_after


def test_third_l2_reservation_succeeds_and_fourth_blocks_without_downgrade(
    tmp_path,
):
    payload = _payload(tmp_path)
    review, adjudication = _review_and_adjudication(payload, "HOLD")
    two = _usage(l2=(_sha(1), _sha(2)))
    third = subject.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=two,
    )
    assert third.decision_code == (
        "ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED"
    )
    assert len(third.usage_after.l2_reviewed_payload_sha256s) == 3
    assert third.usage_after.l2_reviewed_payload_sha256s[:-1] == (
        two.l2_reviewed_payload_sha256s
    )
    other_payload = _payload(tmp_path, "SWING", "SHORT", name="fourth")
    other_review, other_adjudication = _review_and_adjudication(
        other_payload, "HOLD"
    )
    fourth = subject.route_e5_claude_review_v1(
        payload=other_payload,
        deepseek_review=other_review,
        deepseek_adjudication=other_adjudication,
        daily_usage=third.usage_after,
    )
    assert fourth.decision_code == "BLOCK_L2_DAILY_REVIEW_CEILING"
    assert fourth.route == "L2"
    assert fourth.claude_required is False
    assert fourth.model_id is None
    assert fourth.usage_after == third.usage_after
    assert fourth.deepseek_publication_block_preserved is True


def test_shared_ceiling_has_priority_over_l2_ceiling(tmp_path):
    payload = _payload(tmp_path)
    review, adjudication = _review_and_adjudication(payload, "HOLD")
    full = _usage(
        l1=tuple(_sha(index) for index in range(1, 7)),
        l2=tuple(_sha(index) for index in range(7, 10)),
    )
    result = subject.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=full,
    )
    assert result.decision_code == "BLOCK_SHARED_DAILY_REVIEW_CEILING"
    assert result.route == "L2"
    assert result.model_id is None
    assert result.usage_after == full


@pytest.mark.parametrize(
    ("decision", "measured", "requested", "within", "code"),
    (
        ("CAUTION", 3999, 499, True, "PASS_CLAUDE_TOKEN_BUDGET"),
        ("CAUTION", 4000, 500, True, "PASS_CLAUDE_TOKEN_BUDGET"),
        ("CAUTION", 4001, 500, False, "HOLD_CLAUDE_INPUT_TOKEN_LIMIT"),
        ("CAUTION", 4000, 501, False, "HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT"),
        ("CAUTION", 4001, 501, False, "HOLD_CLAUDE_INPUT_TOKEN_LIMIT"),
        ("HOLD", 5999, 799, True, "PASS_CLAUDE_TOKEN_BUDGET"),
        ("HOLD", 6000, 800, True, "PASS_CLAUDE_TOKEN_BUDGET"),
        ("HOLD", 6001, 800, False, "HOLD_CLAUDE_INPUT_TOKEN_LIMIT"),
        ("HOLD", 6000, 801, False, "HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT"),
        ("HOLD", 6001, 801, False, "HOLD_CLAUDE_INPUT_TOKEN_LIMIT"),
    ),
)
def test_exact_l1_l2_token_boundaries_and_input_priority(
    tmp_path, decision, measured, requested, within, code
):
    route = _route(tmp_path, decision)[3]
    result = subject.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=measured,
        requested_output_tokens=requested,
    )
    assert result.within_limits is within
    assert result.decision_code == code
    assert result.model_id == route.model_id
    assert result.input_hard_limit_tokens == route.input_hard_limit_tokens
    assert result.output_hard_limit_tokens == route.output_hard_limit_tokens


def test_l0_and_blocked_route_preflight_are_unauthorized(tmp_path):
    l0 = _route(tmp_path, "CLEAR")[3]
    l0_result = subject.preflight_e5_claude_review_v1(
        route_result=l0,
        measured_input_tokens=0,
        requested_output_tokens=0,
    )
    assert l0_result.decision_code == "HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED"
    payload, _, _, first = _route(tmp_path, "CAUTION", name="blocked")
    review, adjudication = _review_and_adjudication(payload, "CAUTION")
    blocked = subject.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=first.usage_after,
    )
    blocked_result = subject.preflight_e5_claude_review_v1(
        route_result=blocked,
        measured_input_tokens=1,
        requested_output_tokens=1,
    )
    assert blocked_result.decision_code == "HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED"
    assert blocked_result.model_id is None
    assert blocked_result.input_hard_limit_tokens == 0
    assert blocked_result.output_hard_limit_tokens == 0


@pytest.mark.parametrize(
    ("measured", "requested"),
    ((-1, 1), (1, -1), (True, 1), (1, False)),
)
def test_token_preflight_rejects_negative_and_bool_counts(
    tmp_path, measured, requested
):
    route = _route(tmp_path, "CAUTION")[3]
    _assert_invalid(
        lambda: subject.preflight_e5_claude_review_v1(
            route_result=route,
            measured_input_tokens=measured,
            requested_output_tokens=requested,
        )
    )


def test_token_preflight_mapping_hash_is_deterministic_and_tamper_evident(
    tmp_path,
):
    route = _route(tmp_path, "HOLD")[3]
    first = subject.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=6000,
        requested_output_tokens=800,
    )
    second = subject.preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=6000,
        requested_output_tokens=800,
    )
    assert first == second
    assert tuple(first.to_mapping()) == PREFLIGHT_FIELDS
    assert hashlib.sha256(first.canonical_preflight_json().encode()).hexdigest() == (
        first.preflight_sha256
    )
    _assert_invalid(lambda: replace(first, preflight_sha256="0" * 64))
    _assert_invalid(lambda: replace(first, model_id="claude-opus-5"))


@pytest.mark.parametrize(
    ("mode", "side", "decision", "route"),
    MODE_SIDE_DECISION,
)
def test_six_real_v2_mode_side_payloads_route_exactly(
    tmp_path, mode, side, decision, route
):
    payload, _, adjudication, result = _route(
        tmp_path,
        decision,
        mode=mode,
        side=side,
        name=f"{mode.lower()}-{side.lower()}",
    )
    assert payload.provider_binding_sha256 == ACTIVE_BINDING_SHA256
    assert result.payload_sha256 == payload.payload_sha256
    assert result.route == route
    if route == "L1":
        assert result.model_id == "claude-opus-5"
    elif route == "L2":
        assert result.model_id == "claude-fable-5"
        assert result.deepseek_publication_block_preserved is True
        assert adjudication.may_continue_to_python_final_gate is False
    else:
        assert result.claude_required is False


def test_same_real_payload_cannot_reserve_twice(tmp_path):
    payload, _, _, first = _route(tmp_path, "CAUTION")
    review, adjudication = _review_and_adjudication(payload, "CAUTION")
    second = subject.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=first.usage_after,
    )
    assert second.decision_code == "BLOCK_DUPLICATE_LOGICAL_REVIEW"
    assert second.usage_after == first.usage_after


def test_no_provider_publication_clock_randomness_or_production_reachability():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    assert "BLOCK_MAXIMUM_DAILY_COST" not in source
    assert "claude-sonnet-5" not in source
    assert "tokenizer" not in source.casefold()
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
        "subprocess",
        "socket",
        "os",
        "uuid",
        "random",
        "secrets",
    }
    assert all(
        module.casefold().split(".", 1)[0] not in forbidden_roots
        for module in imported_modules
    )
    forbidden_components = (
        "telegram",
        "exchange",
        "active_signal_ledger",
        "provider_transport",
        "service",
        "deployment",
        "slot",
        "pair_lock",
    )
    assert not any(
        component == forbidden or component.startswith(f"{forbidden}_")
        for module in imported_modules
        for component in module.casefold().split(".")
        for forbidden in forbidden_components
    )
    call_names = {
        node.func.id
        if isinstance(node.func, ast.Name)
        else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert {
        "now",
        "today",
        "time",
        "sleep",
        "getenv",
        "environ",
        "request",
        "post",
        "send",
        "publish",
        "order",
        "claim_e4_publication_intent_v1",
        "record_e4_publication_success_v1",
        "build_e5_deepseek_structured_review_v1",
        "adjudicate_e5_deepseek_technical_review_v1",
    }.isdisjoint(call_names)
    public_fields = set(USAGE_FIELDS).union(ROUTE_FIELDS, PREFLIGHT_FIELDS)
    assert {
        "publication_allowed",
        "publication_approved",
        "telegram_message",
        "ledger_revision",
        "slot",
        "pair_lock",
    }.isdisjoint(public_fields)


def test_public_functions_are_pure_keyword_only_without_provider_inputs():
    functions = (
        subject.create_empty_e5_claude_daily_usage_v1,
        subject.route_e5_claude_review_v1,
        subject.preflight_e5_claude_review_v1,
    )
    forbidden = {
        "api_key",
        "client",
        "provider",
        "timeout",
        "retry",
        "fallback",
        "model_id",
        "route",
        "cost",
        "telegram",
        "ledger",
        "slot",
        "pair_lock",
        "publication",
    }
    for function in functions:
        parameters = inspect.signature(function).parameters
        assert forbidden.isdisjoint(parameters)
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            and parameter.default is inspect.Parameter.empty
            for parameter in parameters.values()
        )
