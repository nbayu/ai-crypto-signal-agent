from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e5_deepseek_technical_review_v1 as subject
from engine.e5_technical_review_payload_v1 import (
    E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
)
from test_e5_technical_review_payload_v1 import _bundle as _payload_bundle


MODES_SIDES_DECISIONS = (
    ("SWING", "LONG", "CLEAR"),
    ("SWING", "SHORT", "CAUTION"),
    ("INTRADAY", "LONG", "HOLD"),
    ("INTRADAY", "SHORT", "CLEAR"),
    ("SCALP", "LONG", "CAUTION"),
    ("SCALP", "SHORT", "HOLD"),
)
REVIEW_FIELDS = (
    "review_version",
    "payload_sha256",
    "model_id",
    "decision",
    "reason_codes",
    "concise_reason",
    "reviewed_evidence_fields",
    "review_sha256",
)
ADJUDICATION_FIELDS = (
    "adjudication_version",
    "policy_version",
    "payload_sha256",
    "model_id",
    "review_decision",
    "reason_codes",
    "review_sha256",
    "pre_review_score",
    "score_penalty",
    "final_score",
    "mode_score_floor",
    "deterministic_hard_gates_passed",
    "may_continue_to_python_final_gate",
    "publication_blocked",
    "hold_blocks_current_trigger_generation",
    "hold_retains_armed_when_lifecycle_valid",
    "outcome_code",
    "adjudication_sha256",
)
REASONS_BY_DECISION = {
    "CLEAR": ("CLEAR_NO_MATERIAL_CONFLICT",),
    "CAUTION": ("CAUTION_LIMITED_EVIDENCE",),
    "HOLD": ("HOLD_MATERIAL_CONTRADICTION",),
}


def _payload(tmp_path, mode="SWING", side="LONG", name="review"):
    return _payload_bundle(tmp_path, mode, side, name=name)[2]


def _review(payload, decision="CLEAR", *, reasons=None, reviewed=None, text=None):
    return subject.build_e5_deepseek_structured_review_v1(
        payload=payload,
        model_id="deepseek-v4-pro",
        decision=decision,
        reason_codes=(
            REASONS_BY_DECISION[decision] if reasons is None else reasons
        ),
        concise_reason=(
            f"Deterministic {decision.lower()} technical review."
            if text is None
            else text
        ),
        reviewed_evidence_fields=(
            E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS
            if reviewed is None
            else reviewed
        ),
    )


def _adjudicate(
    payload,
    decision="CLEAR",
    *,
    hard_gates=True,
    score=80,
    floor=70,
):
    return subject.adjudicate_e5_deepseek_technical_review_v1(
        payload=payload,
        review=_review(payload, decision),
        deterministic_hard_gates_passed=hard_gates,
        pre_review_score=score,
        mode_score_floor=floor,
    )


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
    with pytest.raises(
        ValueError,
        match="^invalid E5 DeepSeek technical review$",
    ):
        call()


def test_exact_versions_decisions_reasons_and_outcomes():
    assert subject.E5_DEEPSEEK_STRUCTURED_REVIEW_VERSION == (
        "e5-deepseek-structured-review-v1"
    )
    assert subject.E5_DEEPSEEK_TECHNICAL_REVIEW_POLICY_VERSION == (
        "e5-deepseek-technical-review-policy-v1"
    )
    assert subject.E5_DEEPSEEK_ADJUDICATION_VERSION == (
        "e5-deepseek-adjudication-v1"
    )
    assert subject.DEEPSEEK_REVIEW_DECISIONS == ("CLEAR", "CAUTION", "HOLD")
    assert subject.DEEPSEEK_REASON_CODES == (
        "CLEAR_NO_MATERIAL_CONFLICT",
        "CAUTION_LIMITED_EVIDENCE",
        "CAUTION_NONCRITICAL_CONTRADICTION",
        "CAUTION_EVIDENCE_QUALITY_CONCERN",
        "HOLD_MATERIAL_CONTRADICTION",
        "HOLD_CRITICAL_AMBIGUITY",
        "HOLD_CRITICAL_EVIDENCE_DEFICIT",
        "HOLD_CRITICAL_MATERIAL_RISK",
    )
    assert subject.DEEPSEEK_ADJUDICATION_OUTCOME_CODES == (
        "CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE",
        "CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE",
        "STOP_DETERMINISTIC_HARD_GATE",
        "STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR",
        "STOP_DEEPSEEK_HOLD",
    )


def test_exact_public_field_inventories():
    assert tuple(field.name for field in fields(subject.E5DeepSeekStructuredReviewV1)) == (
        REVIEW_FIELDS
    )
    assert tuple(
        field.name
        for field in fields(subject.E5DeepSeekTechnicalReviewAdjudicationV1)
    ) == ADJUDICATION_FIELDS


@pytest.mark.parametrize(
    "contract",
    (
        subject.E5DeepSeekStructuredReviewV1,
        subject.E5DeepSeekTechnicalReviewAdjudicationV1,
    ),
)
def test_results_are_frozen_and_slotted(contract):
    assert is_dataclass(contract)
    assert contract.__dataclass_params__.frozen is True
    assert "__dict__" not in contract.__dict__


@pytest.mark.parametrize("model_id", ("deepseek-v4-flash", "deepseek-chat", "latest"))
def test_alternate_or_latest_model_fails_closed(tmp_path, model_id):
    payload = _payload(tmp_path)
    _assert_invalid(
        lambda: subject.build_e5_deepseek_structured_review_v1(
            payload=payload,
            model_id=model_id,
            decision="CLEAR",
            reason_codes=("CLEAR_NO_MATERIAL_CONFLICT",),
            concise_reason="No material technical conflict.",
            reviewed_evidence_fields=E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
        )
    )


def test_exact_model_and_payload_binding_are_retained(tmp_path):
    payload = _payload(tmp_path)
    review = _review(payload)
    assert review.model_id == "deepseek-v4-pro"
    assert review.payload_sha256 == payload.payload_sha256
    assert review.reviewed_evidence_fields == E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS


def test_wrong_or_forged_payload_sha_fails_closed(tmp_path):
    payload = _payload(tmp_path)
    forged = _unsafe_clone(payload, payload_sha256="0" * 64)
    _assert_invalid(lambda: _review(forged))


def test_review_mapping_keys_are_exact_and_arrays_are_json_lists(tmp_path):
    mapping = _review(_payload(tmp_path)).to_mapping()
    assert tuple(mapping) == REVIEW_FIELDS
    assert type(mapping["reason_codes"]) is list
    assert type(mapping["reviewed_evidence_fields"]) is list


@pytest.mark.parametrize("mutation", ("missing", "extra", "wrong_hash", "tuple_array"))
def test_reconstruction_fails_closed_on_schema_or_hash_mutation(tmp_path, mutation):
    mapping = _review(_payload(tmp_path)).to_mapping()
    if mutation == "missing":
        mapping.pop("decision")
    elif mutation == "extra":
        mapping["metadata"] = "forbidden"
    elif mutation == "wrong_hash":
        mapping["review_sha256"] = "0" * 64
    else:
        mapping["reason_codes"] = tuple(mapping["reason_codes"])
    _assert_invalid(
        lambda: subject.reconstruct_e5_deepseek_structured_review_v1(mapping)
    )


def test_review_canonical_json_hash_and_reconstruction_are_deterministic(tmp_path):
    review = _review(_payload(tmp_path))
    reconstructed = subject.reconstruct_e5_deepseek_structured_review_v1(
        dict(reversed(tuple(review.to_mapping().items())))
    )
    assert reconstructed == review
    assert reconstructed.canonical_review_json() == review.canonical_review_json()
    assert hashlib.sha256(review.canonical_review_json().encode()).hexdigest() == (
        review.review_sha256
    )


@pytest.mark.parametrize(
    "text",
    (
        "",
        " leading",
        "trailing ",
        "two\nlines",
        "tab\there",
        "nul\x00here",
        "x" * 281,
        "Cafe\u0301",
    ),
)
def test_concise_reason_invalid_text_fails_closed(tmp_path, text):
    payload = _payload(tmp_path)
    _assert_invalid(lambda: _review(payload, text=text))


@pytest.mark.parametrize(
    "reviewed",
    (
        (),
        ("mode", "mode"),
        ("mode", "publication_timestamp"),
        ("golden_zone", "mode"),
        ["mode"],
    ),
)
def test_reviewed_evidence_fields_are_nonempty_unique_known_and_ordered(
    tmp_path, reviewed
):
    payload = _payload(tmp_path)
    _assert_invalid(lambda: _review(payload, reviewed=reviewed))


@pytest.mark.parametrize(
    ("decision", "reasons"),
    (
        ("CLEAR", ("CLEAR_NO_MATERIAL_CONFLICT",)),
        ("CAUTION", ("CAUTION_LIMITED_EVIDENCE",)),
        (
            "CAUTION",
            (
                "CAUTION_LIMITED_EVIDENCE",
                "CAUTION_NONCRITICAL_CONTRADICTION",
                "CAUTION_EVIDENCE_QUALITY_CONCERN",
            ),
        ),
        ("HOLD", ("HOLD_MATERIAL_CONTRADICTION",)),
        (
            "HOLD",
            (
                "HOLD_MATERIAL_CONTRADICTION",
                "HOLD_CRITICAL_AMBIGUITY",
                "HOLD_CRITICAL_EVIDENCE_DEFICIT",
                "HOLD_CRITICAL_MATERIAL_RISK",
            ),
        ),
    ),
)
def test_decisions_accept_only_their_canonical_reason_sets(
    tmp_path, decision, reasons
):
    review = _review(_payload(tmp_path), decision, reasons=reasons)
    assert review.decision == decision
    assert review.reason_codes == reasons


@pytest.mark.parametrize(
    ("decision", "reasons"),
    (
        ("CLEAR", ("CAUTION_LIMITED_EVIDENCE",)),
        ("CLEAR", ("HOLD_MATERIAL_CONTRADICTION",)),
        ("CLEAR", ("CLEAR_NO_MATERIAL_CONFLICT", "CLEAR_NO_MATERIAL_CONFLICT")),
        ("CAUTION", ("CLEAR_NO_MATERIAL_CONFLICT",)),
        ("CAUTION", ("HOLD_CRITICAL_AMBIGUITY",)),
        ("CAUTION", ("CAUTION_LIMITED_EVIDENCE", "CAUTION_LIMITED_EVIDENCE")),
        (
            "CAUTION",
            ("CAUTION_NONCRITICAL_CONTRADICTION", "CAUTION_LIMITED_EVIDENCE"),
        ),
        ("HOLD", ("CLEAR_NO_MATERIAL_CONFLICT",)),
        ("HOLD", ("CAUTION_LIMITED_EVIDENCE",)),
        ("HOLD", ("HOLD_CRITICAL_AMBIGUITY", "HOLD_CRITICAL_AMBIGUITY")),
        (
            "HOLD",
            ("HOLD_CRITICAL_AMBIGUITY", "HOLD_MATERIAL_CONTRADICTION"),
        ),
        ("HOLD", ("UNKNOWN_REASON",)),
        ("CAUTION", (" caution_limited_evidence",)),
        ("CAUTION", ("caution_limited_evidence",)),
    ),
)
def test_inconsistent_unknown_duplicate_or_noncanonical_reasons_fail_closed(
    tmp_path, decision, reasons
):
    payload = _payload(tmp_path)
    _assert_invalid(lambda: _review(payload, decision, reasons=reasons))


@pytest.mark.parametrize(
    (
        "decision",
        "hard_gates",
        "score",
        "floor",
        "penalty",
        "final",
        "continues",
        "blocked",
        "trigger_block",
        "retains_armed",
        "outcome",
    ),
    (
        (
            "CLEAR", True, 80, 70, 0, 80, True, False, False, False,
            "CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE",
        ),
        (
            "CLEAR", True, 60, 70, 0, 60, True, False, False, False,
            "CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE",
        ),
        (
            "CLEAR", False, 80, 70, 0, 80, False, True, False, False,
            "STOP_DETERMINISTIC_HARD_GATE",
        ),
        (
            "CAUTION", True, 80, 70, -3, 77, True, False, False, False,
            "CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE",
        ),
        (
            "CAUTION", True, 73, 70, -3, 70, False, True, False, False,
            "STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR",
        ),
        (
            "CAUTION", True, 72, 70, -3, 69, False, True, False, False,
            "STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR",
        ),
        (
            "CAUTION", False, 80, 70, -3, 77, False, True, False, False,
            "STOP_DETERMINISTIC_HARD_GATE",
        ),
        (
            "HOLD", True, 100, 70, 0, 100, False, True, True, True,
            "STOP_DEEPSEEK_HOLD",
        ),
        (
            "HOLD", False, 1, 70, 0, 1, False, True, True, True,
            "STOP_DEEPSEEK_HOLD",
        ),
    ),
)
def test_exact_d6_effect_matrix(
    tmp_path,
    decision,
    hard_gates,
    score,
    floor,
    penalty,
    final,
    continues,
    blocked,
    trigger_block,
    retains_armed,
    outcome,
):
    result = _adjudicate(
        _payload(tmp_path),
        decision,
        hard_gates=hard_gates,
        score=score,
        floor=floor,
    )
    assert result.score_penalty == penalty
    assert result.final_score == final
    assert result.may_continue_to_python_final_gate is continues
    assert result.publication_blocked is blocked
    assert result.hold_blocks_current_trigger_generation is trigger_block
    assert result.hold_retains_armed_when_lifecycle_valid is retains_armed
    assert result.outcome_code == outcome
    assert result.final_score <= result.pre_review_score


def test_clear_continuation_is_only_to_python_final_gate(tmp_path):
    result = _adjudicate(_payload(tmp_path), "CLEAR", score=1, floor=100)
    assert result.may_continue_to_python_final_gate is True
    assert result.publication_blocked is False
    assert "publication_allowed" not in result.to_mapping()
    assert "publication_approved" not in result.to_mapping()


def test_hold_records_conditional_armed_policy_without_lifecycle_mutation(tmp_path):
    payload = _payload(tmp_path)
    before = payload.to_mapping()
    result = _adjudicate(payload, "HOLD")
    assert result.hold_retains_armed_when_lifecycle_valid is True
    assert payload.to_mapping() == before
    assert "lifecycle_state" not in result.to_mapping()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("score_penalty", 1),
        ("final_score", 999),
        ("may_continue_to_python_final_gate", False),
        ("publication_blocked", True),
        ("outcome_code", "STOP_DEEPSEEK_HOLD"),
        ("adjudication_sha256", "0" * 64),
        ("pre_review_score", True),
        ("mode_score_floor", False),
    ),
)
def test_contradictory_arithmetic_boolean_outcome_or_bool_score_fails_closed(
    tmp_path, field, value
):
    result = _adjudicate(_payload(tmp_path))
    _assert_invalid(lambda: replace(result, **{field: value}))


def test_review_and_adjudication_canonical_hashes_are_deterministic(tmp_path):
    payload = _payload(tmp_path)
    first_review = _review(payload, "CAUTION")
    second_review = _review(payload, "CAUTION")
    assert first_review == second_review
    first = subject.adjudicate_e5_deepseek_technical_review_v1(
        payload=payload,
        review=first_review,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
    )
    second = subject.adjudicate_e5_deepseek_technical_review_v1(
        payload=payload,
        review=second_review,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
    )
    assert first == second
    assert first.canonical_adjudication_json() == second.canonical_adjudication_json()
    assert hashlib.sha256(first.canonical_adjudication_json().encode()).hexdigest() == (
        first.adjudication_sha256
    )


@pytest.mark.parametrize(("mode", "side", "decision"), MODES_SIDES_DECISIONS)
def test_six_real_slice02_mode_side_payloads_support_exact_reviews(
    tmp_path, mode, side, decision
):
    payload = _payload(
        tmp_path,
        mode,
        side,
        name=f"{mode.lower()}-{side.lower()}",
    )
    review = _review(payload, decision)
    result = subject.adjudicate_e5_deepseek_technical_review_v1(
        payload=payload,
        review=review,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
    )
    assert review.payload_sha256 == payload.payload_sha256
    assert result.payload_sha256 == payload.payload_sha256
    assert result.review_sha256 == review.review_sha256


def test_cross_payload_review_reuse_fails_closed(tmp_path):
    first = _payload(tmp_path, "SWING", "LONG", name="first")
    second = _payload(tmp_path, "SWING", "SHORT", name="second")
    review = _review(first)
    _assert_invalid(
        lambda: subject.adjudicate_e5_deepseek_technical_review_v1(
            payload=second,
            review=review,
            deterministic_hard_gates_passed=True,
            pre_review_score=80,
            mode_score_floor=70,
        )
    )


@pytest.mark.parametrize(
    ("hard_gates", "score", "floor"),
    ((1, 80, 70), (True, False, 70), (True, 80, True)),
)
def test_adjudicator_requires_exact_bool_and_integer_inputs(
    tmp_path, hard_gates, score, floor
):
    payload = _payload(tmp_path)
    review = _review(payload)
    _assert_invalid(
        lambda: subject.adjudicate_e5_deepseek_technical_review_v1(
            payload=payload,
            review=review,
            deterministic_hard_gates_passed=hard_gates,
            pre_review_score=score,
            mode_score_floor=floor,
        )
    )


def test_public_functions_have_no_provider_or_mutation_inputs():
    signatures = (
        inspect.signature(subject.build_e5_deepseek_structured_review_v1),
        inspect.signature(subject.adjudicate_e5_deepseek_technical_review_v1),
    )
    forbidden = {
        "api_key",
        "client",
        "timeout",
        "retry",
        "fallback",
        "geometry",
        "side",
        "entry",
        "stop_loss",
        "targets",
        "telegram",
        "ledger",
        "slot",
        "pair_lock",
        "publication",
    }
    for signature in signatures:
        assert forbidden.isdisjoint(signature.parameters)
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            and parameter.default is inspect.Parameter.empty
            for parameter in signature.parameters.values()
        )


def test_no_raw_provider_text_parsing_repair_retry_or_fallback_surface():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    assert "json.loads" not in source
    assert "prompt_repair" not in source
    tree = ast.parse(source)
    calls = {
        node.func.id
        if isinstance(node.func, ast.Name)
        else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert {
        "getenv",
        "environ",
        "sleep",
        "request",
        "post",
        "send",
        "publish",
        "order",
        "claim_e4_publication_intent_v1",
        "record_e4_publication_success_v1",
        "now",
        "utcnow",
        "time",
    }.isdisjoint(calls)


def test_zero_provider_publication_and_production_import_reachability():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            modules.add(node.module)
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
    assert all(module.split(".", 1)[0].casefold() not in forbidden_roots for module in modules)
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
        for module in modules
        for component in module.casefold().split(".")
        for forbidden in forbidden_components
    )


def test_module_does_not_retain_geometry_setup_or_publication_authority_fields():
    retained_fields = set(REVIEW_FIELDS).union(ADJUDICATION_FIELDS)
    assert {
        "geometry",
        "setup",
        "side",
        "entry",
        "stop_loss",
        "tp1",
        "tp2",
        "lifecycle_state",
        "publication_allowed",
        "publication_approved",
        "telegram_message",
        "ledger_revision",
        "slot",
        "pair_lock",
    }.isdisjoint(retained_fields)
