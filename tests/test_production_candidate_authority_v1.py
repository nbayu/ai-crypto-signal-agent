"""Focused contracts for detached Phase 12 candidate authority and source wiring."""
from __future__ import annotations

import copy
import math
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine import controlled_production_signal_cycle_v1 as cycle
from engine import production_candidate_authority_v1 as subject


NOW = "2026-07-22T12:00:00Z"
VALID_UNTIL = "2026-07-23T12:00:00Z"


def _authority_values(**changes):
    value = {
        "source_commit": "a" * 40,
        "source_evaluation_id": "evaluation-one",
        "production_evidence_ref": {
            "manifest_hash": "b" * 64,
            "manifest_path": "sealed/manifest.json",
        },
        "component_versions": {"adapter": "v1", "master": "v4"},
        "tp2": 120.0,
        "valid_until": VALID_UNTIL,
        "strategy_version": "master-engine-v4",
        "source_payload_hash": "c" * 64,
    }
    value.update(changes)
    return value


def _authority(**changes):
    return subject.ProductionCandidateAuthorityV1(**_authority_values(**changes))


def _master(**changes):
    value = {"out": {"final_top5": [{"symbol": "BTCUSDT"}]}}
    value.update(changes)
    return value


def _candidate():
    return {
        "schema_version": 1,
        "schema_name": "production-signal-input",
        "source_commit": "a" * 40,
        "source_evaluation_id": "evaluation-one",
        "mode": "SWING",
        "evaluated_at": NOW,
        "production_evidence_ref": {
            "manifest_hash": "b" * 64,
            "manifest_path": "sealed/manifest.json",
        },
        "outcome_kind": "PUBLISHED_SIGNAL",
        "eligible_setups": [{
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_zone": {"min": 100.0, "max": 101.0},
            "stop_loss": 95.0,
            "take_profit": {"tp1": 110.0, "tp2": 120.0},
            "valid_until": VALID_UNTIL,
            "strategy_version": "master-engine-v4",
            "source_payload_hash": "c" * 64,
        }],
        "component_versions": {"adapter": "v1", "master": "v4"},
    }


def _source(**changes):
    values = {
        "master_engine_result": _master(),
        "selected_symbol": "BTCUSDT",
        "mode": "SWING",
        "evaluated_at": NOW,
        "authority": _authority(),
    }
    values.update(changes)
    return subject.build_adapter_backed_production_candidate_source(**values)


def _outcome(result, candidate=None):
    return SimpleNamespace(result=result, candidate=candidate)


def test_authority_type_is_frozen_slotted_ordered_and_deterministic():
    authority = _authority(component_versions={"master": "v4", "adapter": "v1"})
    assert subject.ProductionCandidateAuthorityV1.__dataclass_params__.frozen
    assert hasattr(subject.ProductionCandidateAuthorityV1, "__slots__")
    assert tuple(field.name for field in fields(subject.ProductionCandidateAuthorityV1)) == (
        "source_commit", "source_evaluation_id", "production_evidence_ref", "component_versions",
        "tp2", "valid_until", "strategy_version", "source_payload_hash",
    )
    assert tuple(authority.to_dict()) == tuple(field.name for field in fields(authority))
    assert tuple(authority.to_dict()["component_versions"]) == ("adapter", "master")


def test_authority_detaches_nested_inputs_and_each_serialization():
    values = _authority_values()
    authority = subject.ProductionCandidateAuthorityV1(**values)
    values["production_evidence_ref"]["manifest_path"] = "changed"
    values["component_versions"]["adapter"] = "changed"
    first = authority.to_dict()
    first["production_evidence_ref"]["manifest_path"] = "changed-again"
    first["component_versions"]["adapter"] = "changed-again"
    second = authority.to_dict()
    assert second["production_evidence_ref"]["manifest_path"] == "sealed/manifest.json"
    assert second["component_versions"]["adapter"] == "v1"


@pytest.mark.parametrize(
    "field,value",
    (
        ("source_commit", None), ("source_commit", "a" * 39),
        ("source_commit", "A" * 40), ("source_commit", "g" * 40),
        ("source_evaluation_id", ""), ("source_evaluation_id", " evaluation"),
        ("source_evaluation_id", "bad/name"), ("source_evaluation_id", "bad\nname"),
        ("source_evaluation_id", "token-value"), ("valid_until", "2026-07-22T12:00:00+00:00"),
        ("valid_until", object()), ("strategy_version", ""),
        ("strategy_version", "bad\nversion"), ("source_payload_hash", "C" * 64),
        ("source_payload_hash", "not-a-hash"), ("tp2", True), ("tp2", "120"),
        ("tp2", math.nan), ("tp2", math.inf),
    ),
)
def test_authority_rejects_malformed_scalar_values(field, value):
    with pytest.raises(subject.ProductionCandidateAuthorityValidationError) as error:
        _authority(**{field: value})
    assert str(error.value) == subject.INVALID_SOURCE_AUTHORITY


@pytest.mark.parametrize(
    "evidence",
    (
        {}, {"manifest_hash": "b" * 64}, {"manifest_path": "sealed/manifest.json"},
        {"manifest_hash": "b" * 64, "manifest_path": "sealed/manifest.json", "extra": "x"},
        {"manifest_hash": "B" * 64, "manifest_path": "sealed/manifest.json"},
        {"manifest_hash": "b" * 64, "manifest_path": Path("sealed/manifest.json")},
        {"manifest_hash": "b" * 64, "manifest_path": "/absolute/manifest.json"},
        {"manifest_hash": "b" * 64, "manifest_path": "../manifest.json"},
    ),
)
def test_authority_rejects_malformed_or_nonlogical_evidence(evidence):
    with pytest.raises(subject.ProductionCandidateAuthorityValidationError):
        _authority(production_evidence_ref=evidence)


@pytest.mark.parametrize(
    "versions",
    (
        {}, {"": "v1"}, {"adapter": ""}, {"adapter": 1}, {"adapter": True},
        {"adapter": {"nested": "v1"}}, {"adapter": ["v1"]},
    ),
)
def test_authority_rejects_invalid_component_versions(versions):
    with pytest.raises(subject.ProductionCandidateAuthorityValidationError):
        _authority(component_versions=versions)


def test_valid_finite_tp2_is_preserved_without_generation():
    assert _authority(tp2=120).to_dict()["tp2"] == 120


def test_source_type_is_frozen_slotted_and_builder_is_adapter_free(monkeypatch):
    calls = []
    monkeypatch.setattr(subject, "adapt_master_engine_result_to_production_candidate", lambda **_: calls.append(1))
    source = _source()
    assert subject.AdapterBackedProductionCandidateSourceV1.__dataclass_params__.frozen
    assert hasattr(subject.AdapterBackedProductionCandidateSourceV1, "__slots__")
    assert tuple(field.name for field in fields(subject.AdapterBackedProductionCandidateSourceV1)) == (
        "master_engine_result", "selected_symbol", "mode", "evaluated_at", "authority",
    )
    assert calls == []
    assert source.authority is not None


@pytest.mark.parametrize(
    "changes",
    (
        {"master_engine_result": []}, {"selected_symbol": None}, {"mode": None},
        {"evaluated_at": None}, {"authority": object()},
    ),
)
def test_builder_requires_detached_mapping_scalars_and_authority_type(changes):
    with pytest.raises(subject.AdapterBackedProductionCandidateSourceValidationError) as error:
        _source(**changes)
    assert str(error.value) == subject.INVALID_CANDIDATE_SOURCE


def test_builder_detaches_master_input_and_does_not_mutate_authority():
    master = _master()
    authority = _authority()
    before = authority.to_dict()
    source = _source(master_engine_result=master, authority=authority)
    master["out"]["final_top5"][0]["symbol"] = "ETHUSDT"
    assert source.master_engine_result["out"]["final_top5"][0]["symbol"] == "BTCUSDT"
    assert authority.to_dict() == before


def test_source_calls_adapter_once_with_exact_detached_authority(monkeypatch):
    calls = []
    candidate = _candidate()

    def adapted(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        return _outcome(subject.PRODUCTION_CANDIDATE_READY, candidate)

    monkeypatch.setattr(subject, "adapt_master_engine_result_to_production_candidate", adapted)
    source = _source()
    result = source()
    assert len(calls) == 1
    assert calls[0]["selected_symbol"] == "BTCUSDT"
    assert calls[0]["mode"] == "SWING"
    assert calls[0]["evaluated_at"] == NOW
    assert calls[0]["production_provenance"] == {
        "source_commit": "a" * 40,
        "source_evaluation_id": "evaluation-one",
        "production_evidence_ref": {"manifest_hash": "b" * 64, "manifest_path": "sealed/manifest.json"},
        "component_versions": {"adapter": "v1", "master": "v4"},
    }
    assert calls[0]["setup_authority"] == {
        "tp2": 120.0, "valid_until": VALID_UNTIL,
        "strategy_version": "master-engine-v4", "source_payload_hash": "c" * 64,
    }
    assert result == candidate and result is not candidate


def test_successful_candidate_is_detached_from_adapter_result(monkeypatch):
    candidate = _candidate()
    monkeypatch.setattr(
        subject,
        "adapt_master_engine_result_to_production_candidate",
        lambda **_: _outcome(subject.PRODUCTION_CANDIDATE_READY, candidate),
    )
    returned = _source()()
    returned["eligible_setups"][0]["symbol"] = "ETHUSDT"
    assert candidate["eligible_setups"][0]["symbol"] == "BTCUSDT"


@pytest.mark.parametrize(
    "outcome",
    (
        _outcome(subject.NO_ELIGIBLE_SIGNAL),
        _outcome("INVALID_MASTER_ENGINE_RESULT"),
        _outcome(subject.PRODUCTION_CANDIDATE_READY, None),
        object(),
    ),
)
def test_source_normalizes_no_candidate_and_all_invalid_adapter_results(monkeypatch, outcome):
    monkeypatch.setattr(subject, "adapt_master_engine_result_to_production_candidate", lambda **_: outcome)
    result = _source()()
    expected = {"result": subject.NO_ELIGIBLE_SIGNAL} if getattr(outcome, "result", None) == subject.NO_ELIGIBLE_SIGNAL else {"result": subject.INVALID_SIGNAL_CANDIDATE}
    assert result == expected


def test_adapter_exception_is_sanitized_and_never_retried(monkeypatch):
    calls = []

    def failing(**_):
        calls.append(1)
        raise RuntimeError("credential=/hidden/path")

    monkeypatch.setattr(subject, "adapt_master_engine_result_to_production_candidate", failing)
    result = _source()()
    assert result == {"result": subject.INVALID_SIGNAL_CANDIDATE}
    assert len(calls) == 1
    assert "credential" not in repr(result) and "hidden" not in repr(result)


def test_each_source_invocation_has_one_adapter_call(monkeypatch):
    calls = []
    monkeypatch.setattr(
        subject,
        "adapt_master_engine_result_to_production_candidate",
        lambda **_: calls.append(1) or _outcome(subject.NO_ELIGIBLE_SIGNAL),
    )
    source = _source()
    assert source() == {"result": subject.NO_ELIGIBLE_SIGNAL}
    assert source() == {"result": subject.NO_ELIGIBLE_SIGNAL}
    assert len(calls) == 2


def test_candidate_source_values_are_compatible_with_locked_cycle(monkeypatch):
    monkeypatch.setattr(
        subject,
        "adapt_master_engine_result_to_production_candidate",
        lambda **_: _outcome(subject.PRODUCTION_CANDIDATE_READY, _candidate()),
    )
    state, candidate = cycle._candidate(_source()())
    assert state == "VALID" and candidate is not None

    monkeypatch.setattr(
        subject,
        "adapt_master_engine_result_to_production_candidate",
        lambda **_: _outcome(subject.NO_ELIGIBLE_SIGNAL),
    )
    assert cycle._candidate(_source()()) == (cycle.NO_ELIGIBLE_SIGNAL, None)

    monkeypatch.setattr(
        subject,
        "adapt_master_engine_result_to_production_candidate",
        lambda **_: _outcome("INVALID_MASTER_ENGINE_RESULT"),
    )
    assert cycle._candidate(_source()())[0] == cycle.INVALID_SIGNAL_CANDIDATE


def test_closed_gate_dry_run_has_zero_downstream_calls(monkeypatch):
    calls = []

    def sentinel(name):
        def blocked(*_args, **_kwargs):
            calls.append(name)
            raise AssertionError(name)
        return blocked

    monkeypatch.setattr(cycle.production, "run_production_signal_service_v1", sentinel("publication"))
    monkeypatch.setattr(cycle.flow, "register_completed_publication", sentinel("registration"))
    result = cycle.run_controlled_production_signal_cycle(
        authorization=cycle.ControlledProductionSignalCycleAuthorizationV1(),
        credential_loader=sentinel("credential"),
        candidate_source=sentinel("candidate"),
        delivery_adapter_factory=sentinel("adapter"),
        publication_root="not-used",
        channel="not-used",
        destination_id="not-used",
        component_versions={"not": "used"},
        active_ledger_path="not-used",
        expected_active_ledger_revision=0,
        reservation_transition_id="not-used",
        timestamp=NOW,
    )
    assert result.result == result.gate == cycle.ACTIVATION_GATE_CLOSED
    assert calls == []
    assert not any((
        result.candidate_generated, result.publication_attempted, result.delivery_attempted,
        result.registration_attempted, result.publication_confirmed, result.registration_applied,
        result.partial_success, result.replay,
    ))
    assert "not-used" not in repr(result) and "credential" not in repr(result).casefold()


def test_source_contains_no_generation_or_operational_surface():
    source = Path(subject.__file__).read_text()
    forbidden = (
        "scanner", "run_master_engine", "master_engine_v4", "subprocess", "hashlib",
        "sha256(", "uuid", "datetime.now", "utcnow", "time.time", "os.environ",
        "getenv", "open(", "Path(", "read_", "write_", "flock", "retry",
        "while True", "production_signal_service", "telegram", "provider", "systemd",
    )
    assert not any(value in source for value in forbidden)
