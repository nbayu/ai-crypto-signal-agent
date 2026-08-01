from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e6_publication_eligibility_v1 as eligibility_module
import engine.e6_publication_envelope_v1 as subject
from test_e6_python_final_strategy_gate_v1 import _evidence, _gate


def _envelope(
    tmp_path: Path,
    decision: str = "CLEAR",
    *,
    mode: str = "SWING",
    side: str = "LONG",
    name: str = "publication-envelope",
):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        decision,
        mode=mode,
        side=side,
        name=name,
    )
    gate = _gate(chain, inputs, payload, durable)
    eligibility = eligibility_module.evaluate_e6_publication_eligibility_v1(
        final_strategy_gate_result=gate,
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        duplicate_protection_result=inputs["duplicate_protection_result"],
    )
    envelope = subject.build_e6_publication_envelope_v1(
        publication_eligibility_result=eligibility,
        final_strategy_gate_result=gate,
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        duplicate_protection_result=inputs["duplicate_protection_result"],
        payload=payload,
        durable_review_execution=durable,
    )
    return envelope, chain, inputs, payload, durable, gate, eligibility


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _unsafe_clone(value, **changes):
    clone = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return clone


def test_public_contract_is_frozen_slotted_and_builder_is_keyword_only(tmp_path):
    envelope, *_ = _envelope(tmp_path)
    assert subject.E6_PUBLICATION_ENVELOPE_VERSION == (
        "e6-publication-envelope-v1"
    )
    assert subject.E6PublicationEnvelopeV1.__dataclass_params__.frozen
    assert "__dict__" not in subject.E6PublicationEnvelopeV1.__slots__
    with pytest.raises(FrozenInstanceError):
        envelope.mode = "SCALP"
    signature = inspect.signature(subject.build_e6_publication_envelope_v1)
    assert tuple(signature.parameters) == (
        "publication_eligibility_result",
        "final_strategy_gate_result",
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


def test_successful_envelope_preserves_signal_review_and_owner_evidence(tmp_path):
    envelope, chain, _, _, _, gate, eligibility = _envelope(tmp_path)
    assert envelope.signal_id.startswith("PSG-")
    assert envelope.publication_identity_sha256 == (
        eligibility.publication_identity_sha256
    )
    assert envelope.final_gate_sha256 == gate.final_gate_sha256
    assert eligibility.canonical_pair == "BTC/USDT"
    assert envelope.canonical_pair == eligibility.canonical_pair
    assert envelope.canonical_venue == "BINANCE_USDM"
    assert envelope.mode == "SWING"
    assert envelope.side == "LONG"
    assert envelope.bias_timeframe == "4h"
    assert envelope.structure_timeframe == "1h"
    assert envelope.trigger_timeframe == "15m"
    assert envelope.structure_generation_id == (
        chain["geometry"].structure_generation_id
    )
    assert envelope.trigger_generation_id == (
        chain["trigger"].trigger_generation_id
    )
    assert envelope.deepseek_d6_outcome == "CLEAR"
    assert envelope.claude_d7_route == "L0"
    assert envelope.d8_underlying_fail_closed_cause is None
    assert envelope.owner_action_state == (
        subject.OWNER_ACTION_AWAITING_MANUAL_DECISION
    )
    assert envelope.manual_owner_authority_statement == (
        subject.MANUAL_OWNER_AUTHORITY_STATEMENT
    )


def test_canonical_preimage_and_hash_are_reproducible(tmp_path):
    envelope, *_ = _envelope(tmp_path)
    preimage = json.loads(envelope.canonical_publication_envelope_json())
    assert "publication_envelope_sha256" not in preimage
    assert envelope.publication_envelope_sha256 == _canonical_hash(preimage)
    assert envelope.to_mapping() == {
        **preimage,
        "publication_envelope_sha256": envelope.publication_envelope_sha256,
    }


def test_identical_semantic_input_has_identical_identity(tmp_path):
    first, *_ = _envelope(tmp_path, name="same-a")
    second, *_ = _envelope(tmp_path, name="same-b")
    assert first.signal_id == second.signal_id
    assert first.publication_envelope_sha256 == second.publication_envelope_sha256
    assert first.canonical_publication_envelope_json() == (
        second.canonical_publication_envelope_json()
    )


def test_relevant_lineage_change_changes_identity(tmp_path):
    long_envelope, *_ = _envelope(tmp_path, name="identity-long")
    short_envelope, *_ = _envelope(
        tmp_path,
        decision="CAUTION",
        side="SHORT",
        name="identity-short",
    )
    assert long_envelope.thesis_fingerprint_sha256 != (
        short_envelope.thesis_fingerprint_sha256
    )
    assert long_envelope.signal_id != short_envelope.signal_id
    assert long_envelope.publication_envelope_sha256 != (
        short_envelope.publication_envelope_sha256
    )


def test_ineligible_final_gate_and_publication_decision_are_rejected(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        "HOLD",
        mode="INTRADAY",
        side="LONG",
        name="ineligible",
    )
    gate = _gate(chain, inputs, payload, durable)
    eligibility = eligibility_module.evaluate_e6_publication_eligibility_v1(
        final_strategy_gate_result=gate,
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        duplicate_protection_result=inputs["duplicate_protection_result"],
    )
    assert eligibility.eligible_to_build_publication_envelope is False
    with pytest.raises(ValueError, match="^invalid E6 publication envelope$"):
        subject.build_e6_publication_envelope_v1(
            publication_eligibility_result=eligibility,
            final_strategy_gate_result=gate,
            actionable_admission=chain["actionable"],
            candidate_authority=chain["authority"],
            duplicate_protection_result=inputs["duplicate_protection_result"],
            payload=payload,
            durable_review_execution=durable,
        )


def test_mixed_lineage_is_rejected(tmp_path):
    _, chain, inputs, payload, durable, gate, eligibility = _envelope(
        tmp_path,
        name="lineage-a",
    )
    other_chain, other_inputs, _, _, _, _ = _evidence(
        tmp_path,
        "CAUTION",
        side="SHORT",
        name="lineage-b",
    )
    with pytest.raises(ValueError, match="^invalid E6 publication envelope$"):
        subject.build_e6_publication_envelope_v1(
            publication_eligibility_result=eligibility,
            final_strategy_gate_result=gate,
            actionable_admission=other_chain["actionable"],
            candidate_authority=other_chain["authority"],
            duplicate_protection_result=(
                other_inputs["duplicate_protection_result"]
            ),
            payload=payload,
            durable_review_execution=durable,
        )
    assert chain["actionable"].actionable_admission_sha256 == (
        inputs["actionable_admission"].actionable_admission_sha256
    )


def test_unknown_code_and_malformed_value_fail_closed(tmp_path):
    envelope, *_ = _envelope(tmp_path)
    unknown = _unsafe_clone(envelope, deepseek_d6_outcome="UNKNOWN")
    malformed = _unsafe_clone(envelope, signal_id="not-a-signal-id")
    for value in (unknown, malformed):
        with pytest.raises(ValueError, match="^invalid E6 publication envelope$"):
            value.__post_init__()


def test_distinct_targets_and_freshness_are_preserved(tmp_path):
    envelope, chain, *_ = _envelope(tmp_path)
    assert envelope.tp1 != envelope.tp2
    assert envelope.tp1_destination_id == (
        chain["targets"].tp1_destination_id
    )
    assert envelope.tp2_destination_id == (
        chain["targets"].tp2_destination_id
    )
    assert envelope.executable_price_fresh is True
    assert envelope.trigger_fresh is True
    assert envelope.quote_age_seconds <= envelope.maximum_quote_age_seconds
    assert envelope.trigger_age_seconds <= envelope.maximum_trigger_age_seconds


def test_envelope_has_zero_effect_authority_and_no_sensitive_surface(tmp_path):
    envelope, *_ = _envelope(tmp_path)
    assert (
        envelope.publication_side_effect_allowed,
        envelope.telegram_send_allowed,
        envelope.ledger_mutation_allowed,
        envelope.entry_active_mutation_allowed,
        envelope.slot_mutation_allowed,
        envelope.pair_lock_mutation_allowed,
        envelope.exchange_order_allowed,
    ) == (False,) * 7
    forbidden_fields = {
        "credential",
        "password",
        "api_key",
        "api_secret",
        "bot_token",
        "chat_id",
        "headers",
        "transport",
        "client",
    }
    names = {field.name.casefold() for field in fields(envelope)}
    assert names.isdisjoint(forbidden_fields)
    serialized = envelope.canonical_publication_envelope_json().casefold()
    assert not any(
        marker in serialized
        for marker in ("bot_token", "api_secret", "private_key", "authorization")
    )


def test_module_has_no_network_telegram_or_effect_import_surface():
    source_path = Path(subject.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint(
        {"requests", "httpx", "aiohttp", "telegram", "telebot", "ccxt"}
    )
    source = source_path.read_text(encoding="utf-8")
    assert "publish(" not in source
    assert "send_message(" not in source
    assert "create_order(" not in source
    assert "reserve_slot(" not in source
    assert "acquire_pair_lock(" not in source
