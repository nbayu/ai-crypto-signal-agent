from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import hashlib
import inspect
import json

import pytest

import engine.e6_claude_daily_usage_store_v1 as usage_store_module
import engine.e6_durable_review_execution_v1 as durable_module
import engine.e6_python_final_strategy_gate_v1 as subject
from engine.e4_duplicate_protection_composition_v1 import (
    compose_e4_duplicate_protection_v1,
)
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)
from test_e5_bounded_final_review_composition_v1 import _transports
from test_e5_technical_review_payload_v1 import (
    _bundle as _payload_bundle,
    _real_chain,
)


TIMESTAMP = "2026-07-30T12:00:00Z"
RESULT_FIELDS = (
    "final_gate_version",
    "provider_binding_sha256",
    "actionable_admission_sha256",
    "candidate_authority_sha256",
    "duplicate_protection_sha256",
    "thesis_fingerprint_sha256",
    "payload_sha256",
    "durable_execution_sha256",
    "final_composition_sha256",
    "canonical_pair",
    "mode",
    "side",
    "structure_timeframe",
    "trigger_timeframe",
    "structure_generation_id",
    "trigger_generation_id",
    "deterministic_hard_gates_passed",
    "actionable_admitted",
    "duplicate_protection_allows_publication_intent",
    "deepseek_review_decision",
    "claude_route",
    "final_score",
    "mode_score_floor",
    "source_e5_final_outcome_code",
    "final_gate_decision_code",
    "may_proceed_to_publication_eligibility",
    "publication_side_effect_allowed",
    "telegram_send_allowed",
    "ledger_mutation_allowed",
    "slot_mutation_allowed",
    "pair_lock_mutation_allowed",
    "exchange_order_allowed",
    "entry_active_mutation_allowed",
    "retry_count",
    "final_gate_sha256",
)


def _canonical_hash(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _evidence(
    tmp_path,
    decision="CLEAR",
    *,
    mode="SWING",
    side="LONG",
    name="final-gate",
    score=80,
    floor=70,
    hard_gates=True,
):
    chain, inputs, payload = _payload_bundle(
        tmp_path,
        mode,
        side,
        name=name,
    )
    deep_transport, claude_transport, deep_calls, claude_calls = _transports(
        payload,
        decision,
    )
    usage_root = tmp_path / f"{name}-usage"
    usage_root.mkdir()
    store = usage_store_module.E6ClaudeDailyUsageFileStoreV1(
        authorized_store_root=usage_root
    )
    claude_required = decision in ("CAUTION", "HOLD")
    durable = durable_module.execute_e6_durable_review_v1(
        payload=payload,
        deterministic_hard_gates_passed=hard_gates,
        pre_review_score=score,
        mode_score_floor=floor,
        usage_store=store,
        commit_timestamp=TIMESTAMP,
        deepseek_measured_input_tokens=100,
        deepseek_requested_output_tokens=100,
        deepseek_transport=deep_transport,
        claude_measured_input_tokens=100 if claude_required else None,
        claude_requested_output_tokens=100 if claude_required else None,
        claude_transport=claude_transport,
    )
    return chain, inputs, payload, durable, deep_calls, claude_calls


def _gate(chain, inputs, payload, durable, *, authority=None, duplicate=None):
    return subject.evaluate_e6_python_final_strategy_gate_v1(
        actionable_admission=chain["actionable"],
        candidate_authority=authority or chain["authority"],
        duplicate_protection_result=(
            duplicate or inputs["duplicate_protection_result"]
        ),
        payload=payload,
        durable_review_execution=durable,
    )


def _assert_invalid(call):
    with pytest.raises(
        ValueError,
        match="^invalid E6 Python final strategy gate$",
    ):
        call()


def test_exact_public_contract_field_order_and_signature(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(tmp_path)
    result = _gate(chain, inputs, payload, durable)
    assert subject.FINAL_GATE_VERSION == "e6-python-final-strategy-gate-v1"
    assert subject.FINAL_GATE_FIELD_COUNT == 35
    assert tuple(field.name for field in fields(result)) == RESULT_FIELDS
    assert tuple(result.to_mapping()) == RESULT_FIELDS
    assert subject.E6PythonFinalStrategyGateResultV1.__dataclass_params__.frozen
    assert "__dict__" not in subject.E6PythonFinalStrategyGateResultV1.__slots__
    signature = inspect.signature(
        subject.evaluate_e6_python_final_strategy_gate_v1
    )
    assert tuple(signature.parameters) == (
        "actionable_admission",
        "candidate_authority",
        "duplicate_protection_result",
        "payload",
        "durable_review_execution",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


def test_exact_eight_decision_codes_and_exports():
    assert subject.FINAL_GATE_DECISION_CODES == (
        "PASS_CLEAR_L0_FINAL_STRATEGY",
        "PASS_CAUTION_L1_FINAL_STRATEGY",
        "BLOCK_E5_FINAL_REVIEW_NOT_CONTINUABLE",
        "BLOCK_E3_ACTIONABLE_ADMISSION",
        "BLOCK_E4_DUPLICATE_PROTECTION",
        "BLOCK_CANDIDATE_AUTHORITY",
        "BLOCK_CROSS_LINEAGE",
        "BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR",
    )
    assert len(subject.FINAL_GATE_DECISION_CODES) == 8
    assert all(code in subject.__all__ for code in subject.FINAL_GATE_DECISION_CODES)
    assert "E6PythonFinalStrategyGateResultV1" in subject.__all__
    assert "evaluate_e6_python_final_strategy_gate_v1" in subject.__all__


def test_clear_l0_is_python_final_pass_only(tmp_path):
    chain, inputs, payload, durable, deep_calls, claude_calls = _evidence(
        tmp_path,
        "CLEAR",
    )
    result = _gate(chain, inputs, payload, durable)
    assert result.final_gate_decision_code == (
        subject.PASS_CLEAR_L0_FINAL_STRATEGY
    )
    assert result.may_proceed_to_publication_eligibility is True
    assert result.deepseek_review_decision == "CLEAR"
    assert result.claude_route == "L0"
    assert len(deep_calls) == 1 and claude_calls == []
    assert result.provider_binding_sha256 == (
        "b6dec84a88151e465cff5ea0a4166b43e93653bcc7fb1668fb72ae65878650a8"
    )


def test_caution_l1_requires_committed_reservation_and_passes(tmp_path):
    chain, inputs, payload, durable, deep_calls, claude_calls = _evidence(
        tmp_path,
        "CAUTION",
        mode="SWING",
        side="SHORT",
        name="caution",
    )
    result = _gate(chain, inputs, payload, durable)
    assert result.final_gate_decision_code == (
        subject.PASS_CAUTION_L1_FINAL_STRATEGY
    )
    assert result.deepseek_review_decision == "CAUTION"
    assert result.claude_route == "L1"
    assert durable.persistence_outcome == "DURABLE_RESERVATION_COMMITTED"
    assert durable.committed_usage_after == durable.proposed_usage_after
    assert len(deep_calls) == len(claude_calls) == 1


def test_hold_l2_never_rescues_strategy(tmp_path):
    chain, inputs, payload, durable, _, claude_calls = _evidence(
        tmp_path,
        "HOLD",
        mode="INTRADAY",
        side="LONG",
        name="hold",
    )
    result = _gate(chain, inputs, payload, durable)
    assert result.final_gate_decision_code == (
        subject.BLOCK_E5_FINAL_REVIEW_NOT_CONTINUABLE
    )
    assert not result.may_proceed_to_publication_eligibility
    assert result.claude_route == "L2"
    assert len(claude_calls) == 1


def test_d6_deterministic_policy_block_is_a_valid_closed_result(tmp_path):
    chain, inputs, payload, durable, _, claude_calls = _evidence(
        tmp_path,
        "CLEAR",
        name="d6-block",
        hard_gates=False,
    )
    result = _gate(chain, inputs, payload, durable)
    assert result.final_gate_decision_code == (
        subject.BLOCK_E5_FINAL_REVIEW_NOT_CONTINUABLE
    )
    assert result.deterministic_hard_gates_passed is False
    assert result.claude_route == "L0"
    assert result.may_proceed_to_publication_eligibility is False
    assert result.publication_side_effect_allowed is False
    assert result.telegram_send_allowed is False
    assert result.ledger_mutation_allowed is False
    assert result.slot_mutation_allowed is False
    assert result.pair_lock_mutation_allowed is False
    assert result.exchange_order_allowed is False
    assert result.entry_active_mutation_allowed is False
    assert result.retry_count == 0
    assert claude_calls == []


def test_clear_at_mode_floor_is_blocked_by_final_python_score(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        "CLEAR",
        name="floor",
        score=70,
        floor=70,
    )
    result = _gate(chain, inputs, payload, durable)
    assert result.final_gate_decision_code == (
        subject.BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR
    )
    assert result.final_score == result.mode_score_floor == 70


def test_clear_below_mode_floor_is_blocked_by_final_python_score(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        "CLEAR",
        name="below-floor",
        score=69,
        floor=70,
    )
    result = _gate(chain, inputs, payload, durable)
    assert result.final_gate_decision_code == (
        subject.BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR
    )


def test_candidate_authority_mismatch_has_exact_precedence(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="authority",
    )
    mapping = chain["authority"].to_dict()
    mapping["strategy_version"] = "different-strategy-v1"
    other = ProductionCandidateAuthorityV1(**mapping)
    result = _gate(
        chain,
        inputs,
        payload,
        durable,
        authority=other,
    )
    assert result.final_gate_decision_code == (
        subject.BLOCK_CANDIDATE_AUTHORITY
    )


def test_cross_payload_lineage_fails_closed(tmp_path):
    chain, inputs, _, _, _, _ = _evidence(tmp_path, name="lineage-source")
    _, _, other_payload, other_durable, _, _ = _evidence(
        tmp_path,
        mode="INTRADAY",
        side="SHORT",
        name="lineage-other",
    )
    result = _gate(chain, inputs, other_payload, other_durable)
    assert result.final_gate_decision_code == subject.BLOCK_CROSS_LINEAGE


def test_nonactionable_e3_has_dedicated_block(tmp_path):
    accepted_chain, accepted_inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="accepted-for-e3",
    )
    blocked_chain = _real_chain(actionable=False)
    root = tmp_path / "blocked-e3"
    root.mkdir()
    duplicate = compose_e4_duplicate_protection_v1(
        actionable_admission=blocked_chain["actionable"],
        candidate_authority=blocked_chain["authority"],
        authorized_store_root=root,
        store_path=root / "BTC-USDT.e4-thesis-history.json",
        price_exited_zone=False,
    )
    result = _gate(
        blocked_chain,
        accepted_inputs,
        payload,
        durable,
        duplicate=duplicate,
    )
    assert result.final_gate_decision_code == (
        subject.BLOCK_E3_ACTIONABLE_ADMISSION
    )
    assert not result.actionable_admitted
    assert accepted_chain["geometry"].to_mapping() == (
        blocked_chain["geometry"].to_mapping()
    )


def test_suppressed_e4_duplicate_has_dedicated_block(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="duplicate",
    )
    root = tmp_path / "duplicate"
    suppressed = compose_e4_duplicate_protection_v1(
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        authorized_store_root=root,
        store_path=root / "BTC-USDT.e4-thesis-history.json",
        price_exited_zone=False,
    )
    assert suppressed.publication_intent_allowed is False
    result = _gate(
        chain,
        inputs,
        payload,
        durable,
        duplicate=suppressed,
    )
    assert result.final_gate_decision_code == (
        subject.BLOCK_E4_DUPLICATE_PROTECTION
    )


def test_canonical_hash_reconstruction_and_authority_flags(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="mapping",
    )
    result = _gate(chain, inputs, payload, durable)
    mapping = result.to_mapping()
    reconstructed = subject.reconstruct_e6_python_final_strategy_gate_result_v1(
        mapping
    )
    assert reconstructed == result
    assert _canonical_hash(json.loads(result.canonical_final_gate_json())) == (
        result.final_gate_sha256
    )
    assert all(
        value is False
        for value in (
            result.publication_side_effect_allowed,
            result.telegram_send_allowed,
            result.ledger_mutation_allowed,
            result.slot_mutation_allowed,
            result.pair_lock_mutation_allowed,
            result.exchange_order_allowed,
            result.entry_active_mutation_allowed,
        )
    )
    assert result.retry_count == 0
    with pytest.raises(FrozenInstanceError):
        result.retry_count = 1


@pytest.mark.parametrize("mutation", ("missing", "unknown", "hash", "code"))
def test_strict_reconstruction_rejects_noncanonical_mapping(tmp_path, mutation):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name=f"reconstruct-{mutation}",
    )
    mapping = _gate(chain, inputs, payload, durable).to_mapping()
    if mutation == "missing":
        mapping.pop("side")
    elif mutation == "unknown":
        mapping["unknown"] = False
    elif mutation == "hash":
        mapping["final_gate_sha256"] = "0" * 64
    else:
        mapping["final_gate_decision_code"] = "UNKNOWN"
    _assert_invalid(
        lambda: subject.reconstruct_e6_python_final_strategy_gate_result_v1(
            mapping
        )
    )


def test_nonzero_retry_durable_input_is_rejected_without_result(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="retry",
    )
    object.__setattr__(durable, "retry_count", 1)
    _assert_invalid(lambda: _gate(chain, inputs, payload, durable))
