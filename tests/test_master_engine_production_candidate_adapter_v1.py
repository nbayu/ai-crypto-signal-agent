"""Focused pure contracts for the Phase 12 production candidate adapter."""
from __future__ import annotations

import copy
from dataclasses import fields
from pathlib import Path

import pytest

from engine import master_engine_production_candidate_adapter_v1 as adapter
from engine.production_signal_service_v1 import validate_production_signal_input


NOW = "2026-07-21T12:00:00Z"
VALID_UNTIL = "2026-07-22T12:00:00Z"


def _setup(symbol="BTCUSDT", direction="BULLISH", **changes):
    golden_zone = {
        "direction": "BULLISH",
        "entry_zone": {"price_low": 100.0, "price_high": 101.0},
        "stop_loss": {"price": 95.0},
        "take_profit": {"price": 110.0},
    }
    if direction == "BEARISH":
        golden_zone = {
            "direction": "BEARISH",
            "entry_zone": {"price_low": 100.0, "price_high": 101.0},
            "stop_loss": {"price": 105.0},
            "take_profit": {"price": 90.0},
        }
    elif direction != "BULLISH":
        golden_zone["direction"] = direction
    value = {
        "symbol": symbol,
        "final_rank_score": 90.0,
        "golden_zone": golden_zone,
    }
    value.update(changes)
    return value


def _master(setups=None, **changes):
    value = {"out": {"final_top5": [_setup()] if setups is None else setups}}
    value.update(changes)
    return value


def _provenance(**changes):
    value = {
        "source_commit": "a" * 40,
        "source_evaluation_id": "evaluation-one",
        "production_evidence_ref": {
            "manifest_hash": "b" * 64,
            "manifest_path": "sealed/manifest.json",
        },
        "component_versions": {"candidate_adapter": "v1"},
    }
    value.update(changes)
    return value


def _authority(**changes):
    value = {
        "tp2": 120.0,
        "valid_until": VALID_UNTIL,
        "strategy_version": "master-engine-v4",
        "source_payload_hash": "c" * 64,
    }
    value.update(changes)
    return value


def _call(**changes):
    values = {
        "master_engine_result": _master(),
        "selected_symbol": "BTCUSDT",
        "mode": "SWING",
        "evaluated_at": NOW,
        "production_provenance": _provenance(),
        "setup_authority": _authority(),
    }
    values.update(changes)
    return adapter.adapt_master_engine_result_to_production_candidate(**values)


def _mutate_setup(setup, path, value):
    item = setup
    for key in path[:-1]:
        item = item[key]
    item[path[-1]] = value


def test_result_type_is_frozen_slotted_and_deterministic():
    result = _call()
    assert adapter.MasterEngineProductionCandidateAdapterResultV1.__dataclass_params__.frozen
    assert hasattr(adapter.MasterEngineProductionCandidateAdapterResultV1, "__slots__")
    assert tuple(field.name for field in fields(adapter.MasterEngineProductionCandidateAdapterResultV1)) == (
        "result", "candidate", "mode", "symbol", "direction", "eligible", "reason", "timestamp",
    )
    assert tuple(result.to_dict()) == tuple(field.name for field in fields(result))


@pytest.mark.parametrize(
    "direction, authority, expected_side",
    (
        ("BULLISH", _authority(), "LONG"),
        ("BEARISH", _authority(tp2=80.0), "SHORT"),
    ),
)
def test_eligible_setup_adapts_to_exact_locked_candidate(direction, authority, expected_side):
    result = _call(master_engine_result=_master([_setup(direction=direction)]), setup_authority=authority)
    assert result.result == adapter.PRODUCTION_CANDIDATE_READY
    assert result.reason == adapter.PRODUCTION_CANDIDATE_READY
    assert result.eligible and result.direction == expected_side
    assert result.candidate is not None
    assert set(result.candidate) == {
        "schema_version", "schema_name", "source_commit", "source_evaluation_id", "mode",
        "evaluated_at", "production_evidence_ref", "outcome_kind", "eligible_setups",
        "component_versions",
    }
    setup = result.candidate["eligible_setups"][0]
    assert set(setup) == {
        "symbol", "side", "entry_zone", "stop_loss", "take_profit", "valid_until",
        "strategy_version", "source_payload_hash",
    }
    assert result.candidate["schema_version"] == 1
    assert result.candidate["schema_name"] == "production-signal-input"
    assert result.candidate["outcome_kind"] == "PUBLISHED_SIGNAL"
    assert setup["side"] == expected_side
    assert validate_production_signal_input(result.candidate) == result.candidate
    forbidden = {
        "channel", "destination_id", "credential", "delivery_id", "signal_id",
        "publication_identity", "active_ledger_revision", "receipt", "usage",
    }
    assert not (set(result.candidate) | set(setup)) & forbidden


def test_empty_final_top5_is_the_only_no_candidate_path():
    result = _call(master_engine_result=_master([]), selected_symbol=None)
    assert result.to_dict() == {
        "result": adapter.NO_ELIGIBLE_SIGNAL,
        "candidate": None,
        "mode": "SWING",
        "symbol": None,
        "direction": None,
        "eligible": False,
        "reason": adapter.NO_ELIGIBLE_SIGNAL,
        "timestamp": NOW,
    }


@pytest.mark.parametrize(
    "selected_symbol, setups",
    (
        (None, [_setup()]),
        ("", [_setup()]),
        ("ETHUSDT", [_setup()]),
        ("BTCUSDT", [_setup(), _setup()]),
    ),
)
def test_selection_is_explicit_unique_and_never_rank_based(selected_symbol, setups):
    result = _call(selected_symbol=selected_symbol, master_engine_result=_master(setups))
    assert result.result == adapter.INVALID_MASTER_ENGINE_RESULT
    assert result.candidate is None and not result.eligible


def test_explicit_selection_is_independent_of_final_top5_order():
    selected = _setup("BTCUSDT")
    other = _setup("ETHUSDT")
    first = _call(master_engine_result=_master([other, selected]))
    second = _call(master_engine_result=_master([selected, other]))
    assert first.to_dict() == second.to_dict()
    assert first.symbol == "BTCUSDT"


@pytest.mark.parametrize(
    "master",
    (
        None,
        {},
        {"out": {}},
        {"out": {"final_top5": {}}},
        {"out": {"final_top5": ["not-a-setup"]}},
        _master([{"symbol": "BTCUSDT"}]),
    ),
)
def test_master_shape_and_selected_geometry_fail_closed(master):
    result = _call(master_engine_result=master)
    assert result.result == adapter.INVALID_MASTER_ENGINE_RESULT
    assert result.candidate is None and not result.eligible


@pytest.mark.parametrize("mode", (None, "swing", "LONG", ""))
def test_mode_is_exact_and_never_coerced(mode):
    result = _call(mode=mode)
    assert result.result == adapter.UNSUPPORTED_SIGNAL_MODE
    assert result.candidate is None and result.mode is None


@pytest.mark.parametrize("direction", ("BUY", "SELL", "UP", "DOWN", "LONG", "SHORT", "bullish", None))
def test_direction_is_exact_and_never_coerced(direction):
    result = _call(master_engine_result=_master([_setup(direction=direction)]))
    assert result.result == adapter.UNSUPPORTED_DIRECTION
    assert result.candidate is None and result.direction is None


@pytest.mark.parametrize(
    "path, value",
    (
        (("golden_zone", "entry_zone", "price_low"), True),
        (("golden_zone", "entry_zone", "price_high"), "101"),
        (("golden_zone", "stop_loss", "price"), float("nan")),
        (("golden_zone", "take_profit", "price"), float("inf")),
    ),
)
def test_invalid_numeric_values_are_rejected(path, value):
    setup = _setup()
    _mutate_setup(setup, path, value)
    result = _call(master_engine_result=_master([setup]))
    assert result.result == adapter.INVALID_NUMERIC_FIELD
    assert result.candidate is None


@pytest.mark.parametrize(
    "direction, setup_changes, authority, expected",
    (
        ("BULLISH", {"golden_zone": {"direction": "BULLISH", "entry_zone": {"price_low": 102.0, "price_high": 101.0}, "stop_loss": {"price": 95.0}, "take_profit": {"price": 110.0}}}, _authority(), adapter.INVALID_TARGET_STRUCTURE),
        ("BULLISH", {"golden_zone": {"direction": "BULLISH", "entry_zone": {"price_low": 100.0, "price_high": 101.0}, "stop_loss": {"price": 100.0}, "take_profit": {"price": 110.0}}}, _authority(), adapter.INVALID_TARGET_STRUCTURE),
        ("BULLISH", {}, _authority(tp2=110.0), adapter.INVALID_TARGET_STRUCTURE),
        ("BEARISH", {"golden_zone": {"direction": "BEARISH", "entry_zone": {"price_low": 100.0, "price_high": 101.0}, "stop_loss": {"price": 105.0}, "take_profit": {"price": 110.0}}}, _authority(tp2=80.0), adapter.INVALID_TARGET_STRUCTURE),
        ("BEARISH", {}, _authority(tp2=120.0), adapter.INVALID_TARGET_STRUCTURE),
    ),
)
def test_entry_stop_and_target_ordering_are_explicit(direction, setup_changes, authority, expected):
    result = _call(master_engine_result=_master([_setup(direction=direction, **setup_changes)]), setup_authority=authority)
    assert result.result == expected
    assert result.candidate is None


@pytest.mark.parametrize(
    "authority, expected",
    (
        ({"valid_until": VALID_UNTIL, "strategy_version": "v1", "source_payload_hash": "c" * 64}, adapter.INVALID_MASTER_ENGINE_RESULT),
        (_authority(tp2="120"), adapter.INVALID_TARGET_STRUCTURE),
        (_authority(valid_until="2026-07-22 12:00:00"), adapter.INVALID_TIMESTAMP),
        (_authority(strategy_version=""), adapter.INVALID_MASTER_ENGINE_RESULT),
        (_authority(source_payload_hash="not-a-hash"), adapter.INVALID_MASTER_ENGINE_RESULT),
    ),
)
def test_setup_authority_is_explicit_and_never_synthesized(authority, expected):
    result = _call(setup_authority=authority)
    assert result.result == expected
    assert result.candidate is None


@pytest.mark.parametrize(
    "evaluated_at",
    (None, "2026-07-21 12:00:00", "2026-07-21T12:00:00+00:00", "not-a-time"),
)
def test_evaluated_at_is_canonical_utc_only(evaluated_at):
    result = _call(evaluated_at=evaluated_at)
    assert result.result == adapter.INVALID_TIMESTAMP
    assert result.timestamp is None and result.candidate is None


@pytest.mark.parametrize(
    "provenance",
    (
        {},
        _provenance(source_commit="short"),
        _provenance(source_evaluation_id=""),
        _provenance(production_evidence_ref={"manifest_hash": "b" * 64}),
        _provenance(component_versions={}),
        _provenance(extra="forbidden"),
    ),
)
def test_provenance_is_detached_explicit_and_well_formed(provenance):
    result = _call(production_provenance=provenance)
    assert result.result == adapter.INVALID_PRODUCTION_PROVENANCE
    assert result.candidate is None


def test_operational_values_are_not_converted_or_trusted():
    setup = _setup(snapshot_path="ignored")
    result = _call(master_engine_result=_master([setup]))
    assert result.result == adapter.INVALID_MASTER_ENGINE_RESULT
    logical = _provenance()
    success = _call(master_engine_result=_master(evidence_path="never-opened"), production_provenance=logical)
    assert success.candidate is not None
    assert success.candidate["production_evidence_ref"] == logical["production_evidence_ref"]
    assert success.candidate["production_evidence_ref"]["manifest_path"] != "never-opened"


def test_validator_is_called_once_and_failure_is_sanitized(monkeypatch):
    calls = []
    original = adapter.validate_production_signal_input

    def once(value):
        calls.append(copy.deepcopy(value))
        return original(value)

    monkeypatch.setattr(adapter, "validate_production_signal_input", once)
    assert _call().result == adapter.PRODUCTION_CANDIDATE_READY
    assert len(calls) == 1
    monkeypatch.setattr(adapter, "validate_production_signal_input", lambda _value: (_ for _ in ()).throw(ValueError("sensitive detail")))
    result = _call()
    assert result.result == adapter.FAIL_CLOSED and result.reason == adapter.FAIL_CLOSED
    assert "sensitive detail" not in repr(result)


def test_inputs_remain_immutable_and_candidate_is_detached():
    master = _master()
    provenance = _provenance()
    authority = _authority()
    original = copy.deepcopy((master, provenance, authority))
    result = _call(master_engine_result=master, production_provenance=provenance, setup_authority=authority)
    assert (master, provenance, authority) == original
    assert result.candidate is not None
    result.candidate["eligible_setups"][0]["entry_zone"]["min"] = 1.0
    assert master["out"]["final_top5"][0]["golden_zone"]["entry_zone"]["price_low"] == 100.0
    assert provenance["production_evidence_ref"]["manifest_hash"] == "b" * 64


def test_source_has_no_operational_import_or_execution_surface():
    source = Path(adapter.__file__).read_text()
    forbidden = (
        "import requests", "import httpx", "import urllib", "import socket", "import subprocess",
        "os.environ", "os.getenv", "open(", "Path(", "read_", "write_", "flock",
        "while True", "run_forever", "start_polling",
    )
    assert not any(item in source for item in forbidden)
