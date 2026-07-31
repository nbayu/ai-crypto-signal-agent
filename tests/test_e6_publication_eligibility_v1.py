from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import inspect
import json

import pytest

import engine.e6_publication_eligibility_v1 as subject
import engine.e6_python_final_strategy_gate_v1 as final_gate_module
from engine.e4_duplicate_protection_composition_v1 import (
    compose_e4_duplicate_protection_v1,
)
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)
from test_e6_python_final_strategy_gate_v1 import (
    _canonical_hash,
    _evidence,
    _gate,
)


RESULT_FIELDS = (
    "publication_eligibility_version",
    "final_gate_sha256",
    "actionable_admission_sha256",
    "candidate_authority_sha256",
    "duplicate_protection_sha256",
    "thesis_fingerprint_sha256",
    "publication_identity_sha256",
    "signal_geometry_sha256",
    "canonical_pair",
    "mode",
    "side",
    "structure_timeframe",
    "trigger_timeframe",
    "source_payload_hash",
    "strategy_version",
    "valid_until",
    "eligible_to_build_publication_envelope",
    "publication_eligibility_decision_code",
    "manual_owner_entry_required",
    "publication_side_effect_allowed",
    "telegram_send_allowed",
    "ledger_mutation_allowed",
    "entry_active_mutation_allowed",
    "slot_mutation_allowed",
    "pair_lock_mutation_allowed",
    "exchange_order_allowed",
    "publication_eligibility_sha256",
)


def _eligibility(gate, chain, inputs, *, authority=None, duplicate=None):
    return subject.evaluate_e6_publication_eligibility_v1(
        final_strategy_gate_result=gate,
        actionable_admission=chain["actionable"],
        candidate_authority=authority or chain["authority"],
        duplicate_protection_result=(
            duplicate or inputs["duplicate_protection_result"]
        ),
    )


def _rebuilt_gate(gate, **changes):
    mapping = gate.to_mapping()
    mapping.update(changes)
    mapping["final_gate_sha256"] = _canonical_hash(
        {
            key: value
            for key, value in mapping.items()
            if key != "final_gate_sha256"
        }
    )
    return final_gate_module.reconstruct_e6_python_final_strategy_gate_result_v1(
        mapping
    )


def _rebuilt_eligibility(result, **changes):
    mapping = result.to_mapping()
    mapping.update(changes)
    mapping["publication_eligibility_sha256"] = _canonical_hash(
        {
            key: value
            for key, value in mapping.items()
            if key != "publication_eligibility_sha256"
        }
    )
    return subject.reconstruct_e6_publication_eligibility_result_v1(mapping)


def _assert_invalid(call):
    with pytest.raises(
        ValueError,
        match="^invalid E6 publication eligibility$",
    ):
        call()


def test_exact_public_contract_field_order_and_signature(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="eligibility-contract",
    )
    gate = _gate(chain, inputs, payload, durable)
    result = _eligibility(gate, chain, inputs)
    assert subject.PUBLICATION_ELIGIBILITY_VERSION == (
        "e6-publication-eligibility-v1"
    )
    assert subject.PUBLICATION_ELIGIBILITY_FIELD_COUNT == 27
    assert tuple(field.name for field in fields(result)) == RESULT_FIELDS
    assert tuple(result.to_mapping()) == RESULT_FIELDS
    assert subject.E6PublicationEligibilityResultV1.__dataclass_params__.frozen
    assert "__dict__" not in subject.E6PublicationEligibilityResultV1.__slots__
    signature = inspect.signature(
        subject.evaluate_e6_publication_eligibility_v1
    )
    assert tuple(signature.parameters) == (
        "final_strategy_gate_result",
        "actionable_admission",
        "candidate_authority",
        "duplicate_protection_result",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


def test_exact_six_codes_and_owner_blueprint_placement():
    assert subject.PUBLICATION_ELIGIBILITY_DECISION_CODES == (
        "ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE",
        "INELIGIBLE_PYTHON_FINAL_STRATEGY",
        "INELIGIBLE_LINEAGE_OR_IDENTITY",
        "INELIGIBLE_DUPLICATE_PROTECTION",
        "INELIGIBLE_MISSING_PUBLICATION_PREREQUISITES",
        "INELIGIBLE_POLICY_OR_AMBIGUITY",
    )
    assert len(subject.PUBLICATION_ELIGIBILITY_DECISION_CODES) == 6
    assert subject.OWNER_BLUEPRINT_CAPACITY_GATE_PLACEMENT == (
        "SEPARATE_PREPUBLICATION_RUNTIME_GATE"
    )
    source = inspect.getsource(subject)
    assert "owner_blueprint_scanner_gate_v1" not in source
    assert "active_signal_ledger_v1" not in source


@pytest.mark.parametrize(
    ("decision", "mode", "side"),
    (
        ("CLEAR", "SWING", "LONG"),
        ("CAUTION", "SWING", "SHORT"),
    ),
)
def test_two_python_final_passes_are_eligible_only_to_build_envelope(
    tmp_path,
    decision,
    mode,
    side,
):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        decision,
        mode=mode,
        side=side,
        name=f"eligible-{decision}",
    )
    gate = _gate(chain, inputs, payload, durable)
    result = _eligibility(gate, chain, inputs)
    assert result.publication_eligibility_decision_code == (
        subject.ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE
    )
    assert result.eligible_to_build_publication_envelope is True
    assert result.final_gate_sha256 == gate.final_gate_sha256
    assert result.canonical_pair == gate.canonical_pair


def test_final_gate_block_is_ineligible(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        "HOLD",
        mode="INTRADAY",
        side="LONG",
        name="blocked-final",
    )
    gate = _gate(chain, inputs, payload, durable)
    result = _eligibility(gate, chain, inputs)
    assert result.publication_eligibility_decision_code == (
        subject.INELIGIBLE_PYTHON_FINAL_STRATEGY
    )
    assert result.eligible_to_build_publication_envelope is False


def test_final_gate_to_source_identity_mismatch_is_ineligible(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="identity",
    )
    gate = _gate(chain, inputs, payload, durable)
    mismatched = _rebuilt_gate(
        gate,
        actionable_admission_sha256="f" * 64,
    )
    result = _eligibility(mismatched, chain, inputs)
    assert result.publication_eligibility_decision_code == (
        subject.INELIGIBLE_LINEAGE_OR_IDENTITY
    )


def test_duplicate_protection_block_is_ineligible(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="duplicate-eligibility",
    )
    gate = _gate(chain, inputs, payload, durable)
    root = tmp_path / "duplicate-eligibility"
    suppressed = compose_e4_duplicate_protection_v1(
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        authorized_store_root=root,
        store_path=root / "BTC-USDT.e4-thesis-history.json",
        price_exited_zone=False,
    )
    gate = _rebuilt_gate(
        gate,
        duplicate_protection_sha256=suppressed.composition_sha256,
    )
    result = _eligibility(
        gate,
        chain,
        inputs,
        duplicate=suppressed,
    )
    assert result.publication_eligibility_decision_code == (
        subject.INELIGIBLE_DUPLICATE_PROTECTION
    )


def test_mismatched_tp2_is_missing_publication_prerequisite(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="missing-prerequisite",
    )
    mapping = chain["authority"].to_dict()
    mapping["tp2"] += 1
    altered = ProductionCandidateAuthorityV1(**mapping)
    gate = _gate(
        chain,
        inputs,
        payload,
        durable,
        authority=altered,
    )
    assert gate.final_gate_decision_code == (
        final_gate_module.PASS_CLEAR_L0_FINAL_STRATEGY
    )
    result = _eligibility(
        gate,
        chain,
        inputs,
        authority=altered,
    )
    assert result.publication_eligibility_decision_code == (
        subject.INELIGIBLE_MISSING_PUBLICATION_PREREQUISITES
    )


def test_policy_ambiguity_code_is_closed_and_never_eligible(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="policy-code",
    )
    result = _eligibility(
        _gate(chain, inputs, payload, durable),
        chain,
        inputs,
    )
    ambiguous = _rebuilt_eligibility(
        result,
        eligible_to_build_publication_envelope=False,
        publication_eligibility_decision_code=(
            subject.INELIGIBLE_POLICY_OR_AMBIGUITY
        ),
    )
    assert not ambiguous.eligible_to_build_publication_envelope
    assert ambiguous.publication_eligibility_decision_code == (
        subject.INELIGIBLE_POLICY_OR_AMBIGUITY
    )


def test_hash_reconstruction_manual_owner_and_zero_authority(tmp_path):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name="eligibility-hash",
    )
    result = _eligibility(
        _gate(chain, inputs, payload, durable),
        chain,
        inputs,
    )
    reconstructed = subject.reconstruct_e6_publication_eligibility_result_v1(
        result.to_mapping()
    )
    assert reconstructed == result
    assert _canonical_hash(
        json.loads(result.canonical_publication_eligibility_json())
    ) == result.publication_eligibility_sha256
    assert result.manual_owner_entry_required is True
    assert all(
        value is False
        for value in (
            result.publication_side_effect_allowed,
            result.telegram_send_allowed,
            result.ledger_mutation_allowed,
            result.entry_active_mutation_allowed,
            result.slot_mutation_allowed,
            result.pair_lock_mutation_allowed,
            result.exchange_order_allowed,
        )
    )
    with pytest.raises(FrozenInstanceError):
        result.manual_owner_entry_required = False


@pytest.mark.parametrize("mutation", ("missing", "unknown", "hash", "code"))
def test_malformed_or_unknown_mapping_produces_no_result(tmp_path, mutation):
    chain, inputs, payload, durable, _, _ = _evidence(
        tmp_path,
        name=f"invalid-eligibility-{mutation}",
    )
    mapping = _eligibility(
        _gate(chain, inputs, payload, durable),
        chain,
        inputs,
    ).to_mapping()
    if mutation == "missing":
        mapping.pop("canonical_pair")
    elif mutation == "unknown":
        mapping["owner_blueprint"] = True
    elif mutation == "hash":
        mapping["publication_eligibility_sha256"] = "0" * 64
    else:
        mapping["publication_eligibility_decision_code"] = "UNKNOWN"
    _assert_invalid(
        lambda: subject.reconstruct_e6_publication_eligibility_result_v1(
            mapping
        )
    )
