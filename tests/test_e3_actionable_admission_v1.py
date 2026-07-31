import ast
import copy
import dataclasses
import hashlib
import inspect
import json
import re
from pathlib import Path

import pytest

import engine.e3_actionable_admission_v1 as actionable
from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_profile_v1 import get_mode_profile
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
    build_e3_golden_zone_geometry,
)
from engine.e3_structural_targets_v1 import (
    E3StructuralTargetsV1,
    build_e3_structural_targets,
)
from engine.e3_executable_price_snapshot_v1 import (
    E3ExecutablePriceSnapshotV1,
    build_e3_executable_price_snapshot,
)
from engine.e3_price_zone_admission_v1 import (
    E3PriceZoneAdmissionV1,
    build_e3_price_zone_admission,
)
from engine.e3_mode_trigger_evidence_v1 import (
    E3ModeTriggerEvidenceV1,
    build_e3_mode_trigger_evidence,
)
from engine.e3_setup_lifecycle_v1 import (
    E3LifecycleResultV1,
    build_e3_setup_lifecycle,
)


FIELDS = (
    "schema_version", "policy_version", "geometry", "structural_targets",
    "executable_price_snapshot", "price_zone_admission", "mode_trigger_evidence",
    "setup_lifecycle", "geometry_identity_matches", "targets_identity_matches",
    "snapshot_identity_matches", "admission_identity_matches", "trigger_identity_matches",
    "lifecycle_identity_matches", "mode_lineage_matches", "symbol_matches", "side_matches",
    "structure_timeframe_matches", "structure_generation_matches", "structure_valid",
    "targets_ready", "price_admission_pass", "trigger_evidence_pass",
    "lifecycle_actionable_pass", "actionable_admitted", "decision", "reason_code",
    "composition_id", "actionable_admission_sha256",
)


def _build_real_actionable_chain(mode, side):
    anchor_low_at = "2026-07-30T00:00:00Z" if side == "LONG" else "2026-07-30T01:00:00Z"
    anchor_high_at = "2026-07-30T01:00:00Z" if side == "LONG" else "2026-07-30T00:00:00Z"
    geometry = build_e3_golden_zone_geometry(
        mode=mode,
        mode_lineage_sha256=build_mode_audit_lineage(mode).lineage_sha256,
        canonical_symbol="BTC/USDT:USDT",
        side=side,
        structure_generation_id="structure:g1",
        anchor_low_at=anchor_low_at,
        anchor_low_tick=9000,
        anchor_high_at=anchor_high_at,
        anchor_high_tick=12000,
        tick_size="1",
    )
    ordered_destinations = (
        (
            "STRUCTURE", "destination:tp1",
            12146 if side == "LONG" else 8854,
            geometry.structure_timeframe, geometry.structure_generation_id,
        ),
        (
            "LIQUIDITY", "destination:tp2",
            12528 if side == "LONG" else 8472,
            geometry.structure_timeframe, geometry.structure_generation_id,
        ),
    )
    structural_targets = build_e3_structural_targets(
        geometry=geometry,
        ordered_destinations=ordered_destinations,
    )
    inside_tick = geometry.golden_zone_low_tick + (
        geometry.golden_zone_high_tick - geometry.golden_zone_low_tick
    ) // 2
    best_bid_tick = inside_tick - 1 if side == "LONG" else inside_tick
    best_ask_tick = inside_tick if side == "LONG" else inside_tick + 1
    executable_price_snapshot = build_e3_executable_price_snapshot(
        geometry=geometry,
        venue="BINANCE_USDM",
        quote_generation_id=f"quote:real-{mode.lower()}-{side.lower()}",
        exchange_timestamp="2026-07-30T00:15:00Z",
        best_bid_tick=best_bid_tick,
        best_ask_tick=best_ask_tick,
        last_price_tick=inside_tick,
        mark_price_tick=inside_tick,
        modeled_adverse_slippage_bps=0,
        tick_size=geometry.tick_size,
    )
    price_zone_admission = build_e3_price_zone_admission(
        geometry=geometry,
        snapshot=executable_price_snapshot,
        evaluation_timestamp="2026-07-30T00:15:00Z",
    )
    profile = get_mode_profile(mode)
    mode_trigger_evidence = build_e3_mode_trigger_evidence(
        geometry=geometry,
        mode=geometry.mode,
        mode_lineage_sha256=geometry.mode_lineage_sha256,
        canonical_symbol=geometry.canonical_symbol,
        side=geometry.side,
        structure_timeframe=geometry.structure_timeframe,
        structure_generation_id=geometry.structure_generation_id,
        trigger_timeframe=profile.trigger_timeframe,
        trigger_rule=profile.trigger_rule,
        trigger_candle_close_at="2026-07-30T00:15:00Z",
        trigger_candle_closed=True,
        trigger_rule_satisfied=True,
        evaluation_timestamp="2026-07-30T00:15:00Z",
    )
    setup_lifecycle = build_e3_setup_lifecycle(
        previous_state="DISCOVERED",
        requested_state="ACTIONABLE",
        geometry=geometry,
        structural_targets=structural_targets,
        price_zone_admission=price_zone_admission,
        mode_trigger_evidence=mode_trigger_evidence,
        structure_valid=True,
    )
    result = actionable.build_e3_actionable_admission(
        geometry=geometry,
        structural_targets=structural_targets,
        executable_price_snapshot=executable_price_snapshot,
        price_zone_admission=price_zone_admission,
        mode_trigger_evidence=mode_trigger_evidence,
        setup_lifecycle=setup_lifecycle,
    )
    assert type(geometry) is E3GoldenZoneGeometryV1
    assert type(structural_targets) is E3StructuralTargetsV1
    assert type(executable_price_snapshot) is E3ExecutablePriceSnapshotV1
    assert type(price_zone_admission) is E3PriceZoneAdmissionV1
    assert type(mode_trigger_evidence) is E3ModeTriggerEvidenceV1
    assert type(setup_lifecycle) is E3LifecycleResultV1
    assert structural_targets.geometry is geometry
    assert executable_price_snapshot.geometry is geometry
    assert price_zone_admission.geometry is geometry
    assert price_zone_admission.snapshot is executable_price_snapshot
    assert mode_trigger_evidence.geometry is geometry
    assert setup_lifecycle.geometry is geometry
    assert setup_lifecycle.structural_targets is structural_targets
    assert setup_lifecycle.price_zone_admission is price_zone_admission
    assert setup_lifecycle.mode_trigger_evidence is mode_trigger_evidence
    assert price_zone_admission.decision == "PASS_PRICE_ADMISSION"
    assert price_zone_admission.reason_code == "PASS_PRICE_ADMISSION"
    assert mode_trigger_evidence.decision == "PASS_TRIGGER_EVIDENCE"
    assert mode_trigger_evidence.reason_code == "PASS_TRIGGER_EVIDENCE"
    assert setup_lifecycle.expected_state == "ACTIONABLE"
    assert setup_lifecycle.resulting_state == "ACTIONABLE"
    assert setup_lifecycle.decision == "PASS_LIFECYCLE"
    assert setup_lifecycle.actionable_ready is True
    assert result.actionable_admitted is True
    assert result.decision == "PASS_ACTIONABLE_ADMISSION"
    assert result.reason_code == "PASS_ACTIONABLE_ADMISSION"
    assert result.reason_code not in {
        actionable.REASON_LIFECYCLE_IDENTITY,
        actionable.REASON_LIFECYCLE_IDENTITY_HOLD,
    }
    return {
        "geometry": geometry,
        "structural_targets": structural_targets,
        "executable_price_snapshot": executable_price_snapshot,
        "price_zone_admission": price_zone_admission,
        "mode_trigger_evidence": mode_trigger_evidence,
        "setup_lifecycle": setup_lifecycle,
        "result": result,
    }


@pytest.fixture
def evidence_factory(monkeypatch):
    store = {}
    classes = (
        E3GoldenZoneGeometryV1, E3StructuralTargetsV1, E3ExecutablePriceSnapshotV1,
        E3PriceZoneAdmissionV1, E3ModeTriggerEvidenceV1, E3LifecycleResultV1,
    )
    attributes = {
        E3GoldenZoneGeometryV1: (
            "geometry_sha256", "mode", "mode_lineage_sha256", "canonical_symbol", "side",
            "structure_timeframe", "structure_generation_id",
        ),
        E3StructuralTargetsV1: (
            "geometry", "targets_sha256", "tp1_destination_id", "tp2_destination_id",
            "tp1_tick", "tp2_tick",
        ),
        E3ExecutablePriceSnapshotV1: ("geometry", "snapshot_sha256"),
        E3PriceZoneAdmissionV1: (
            "geometry", "snapshot", "admission_sha256", "decision", "reason_code",
            "age_within_limit", "spread_within_limit", "slippage_within_limit", "inside_zone",
        ),
        E3ModeTriggerEvidenceV1: (
            "geometry", "trigger_generation_id", "trigger_evidence_sha256", "mode",
            "mode_lineage_sha256", "mode_matches", "mode_lineage_matches", "canonical_symbol",
            "symbol_matches", "side", "side_matches", "structure_timeframe",
            "structure_timeframe_matches", "structure_generation_id",
            "structure_generation_matches", "trigger_candle_closed", "trigger_rule_satisfied",
            "trigger_close_aligned", "trigger_not_future", "trigger_fresh",
            "trigger_timeframe_matches", "trigger_rule_matches", "decision", "reason_code",
        ),
        E3LifecycleResultV1: (
            "geometry", "structural_targets", "price_zone_admission", "mode_trigger_evidence",
            "structure_valid", "geometry_identity_matches", "targets_identity_matches",
            "admission_identity_matches", "trigger_identity_matches", "mode_lineage_matches",
            "symbol_matches", "side_matches", "structure_timeframe_matches",
            "structure_generation_matches", "targets_ready", "price_admission_pass",
            "trigger_evidence_pass", "transition_legal", "actionable_ready", "expected_state",
            "resulting_state", "decision", "reason_code", "lifecycle_sha256",
        ),
    }

    def invariant(self):
        if store[id(self)].get("corrupt", False):
            raise RuntimeError("private dependency corruption")

    def to_mapping(self):
        return copy.deepcopy(store[id(self)]["mapping"])

    for cls in classes:
        monkeypatch.setattr(cls, "__post_init__", invariant, raising=False)
        monkeypatch.setattr(cls, "to_mapping", to_mapping, raising=False)
        for name in attributes[cls]:
            monkeypatch.setattr(cls, name, property(lambda self, item=name: store[id(self)][item]), raising=False)

    def new(cls, values):
        obj = object.__new__(cls)
        store[id(obj)] = values
        return obj

    def make(**changes):
        mode = changes.get("mode", "SWING")
        side = changes.get("side", "LONG")
        geometry_hash = changes.get("geometry_hash", "a" * 64)
        geometry_map = {
            "schema_version": "geometry-v1", "mode": mode, "side": side,
            "canonical_symbol": "BTCUSDT", "geometry_sha256": geometry_hash,
        }
        geometry = new(E3GoldenZoneGeometryV1, {
            "geometry_sha256": geometry_hash, "mode": mode, "mode_lineage_sha256": "b" * 64,
            "canonical_symbol": "BTCUSDT", "side": side, "structure_timeframe": "4h",
            "structure_generation_id": "structure-1", "mapping": geometry_map,
        })

        def clone(obj):
            values = dict(store[id(obj)])
            values["mapping"] = copy.deepcopy(values["mapping"])
            return new(type(obj), values)

        targets_geometry = clone(geometry) if changes.get("targets_geometry_mismatch") else geometry
        targets_hash = changes.get("targets_hash", "c" * 64)
        targets = new(E3StructuralTargetsV1, {
            "geometry": targets_geometry, "targets_sha256": targets_hash,
            "tp1_destination_id": "tp1", "tp2_destination_id": changes.get("tp2_destination_id", "tp2"),
            "tp1_tick": 130, "tp2_tick": changes.get("tp2_tick", 150),
            "mapping": {"geometry": copy.deepcopy(geometry_map), "targets_sha256": targets_hash},
        })
        snapshot_geometry = clone(geometry) if changes.get("snapshot_geometry_mismatch") else geometry
        snapshot_hash = changes.get("snapshot_hash", "d" * 64)
        snapshot = new(E3ExecutablePriceSnapshotV1, {
            "geometry": snapshot_geometry, "snapshot_sha256": snapshot_hash,
            "mapping": {"geometry": copy.deepcopy(geometry_map), "snapshot_sha256": snapshot_hash},
        })
        admission_geometry = clone(geometry) if changes.get("admission_geometry_mismatch") else geometry
        admission_snapshot = clone(snapshot) if changes.get("admission_snapshot_mismatch") else snapshot
        price_reason = changes.get("price_reason", "PASS_PRICE_ADMISSION")
        price_decision = "PASS_PRICE_ADMISSION" if price_reason == "PASS_PRICE_ADMISSION" else "HOLD_PRICE_ADMISSION"
        age = changes.get("age_within_limit", price_reason != "HOLD_PRICE_STALE")
        spread = changes.get("spread_within_limit", price_reason != "HOLD_PRICE_SPREAD")
        slippage = changes.get("slippage_within_limit", price_reason != "HOLD_PRICE_SLIPPAGE")
        inside = changes.get("inside_zone", price_reason != "HOLD_PRICE_OUTSIDE_ZONE")
        admission_hash = changes.get("admission_hash", "e" * 64)
        admission = new(E3PriceZoneAdmissionV1, {
            "geometry": admission_geometry, "snapshot": admission_snapshot,
            "admission_sha256": admission_hash, "decision": changes.get("price_decision", price_decision),
            "reason_code": price_reason, "age_within_limit": age, "spread_within_limit": spread,
            "slippage_within_limit": slippage, "inside_zone": inside,
            "mapping": {"geometry": copy.deepcopy(geometry_map), "snapshot": copy.deepcopy(store[id(snapshot)]["mapping"]),
                        "admission_sha256": admission_hash, "reason_code": price_reason},
        })
        trigger_geometry = clone(geometry) if changes.get("trigger_geometry_mismatch") else geometry
        trigger_reason = changes.get("trigger_reason", "PASS_TRIGGER_EVIDENCE")
        trigger_decision = "PASS_TRIGGER_EVIDENCE" if trigger_reason == "PASS_TRIGGER_EVIDENCE" else "HOLD_TRIGGER_EVIDENCE"
        gates = {
            "trigger_candle_closed": True, "trigger_rule_satisfied": True,
            "trigger_close_aligned": True, "trigger_not_future": trigger_reason != "HOLD_TRIGGER_FUTURE",
            "trigger_fresh": trigger_reason != "HOLD_TRIGGER_STALE", "trigger_timeframe_matches": True,
            "trigger_rule_matches": True,
        }
        lost_gate = changes.get("lost_gate")
        if lost_gate:
            gates[lost_gate] = False
            trigger_reason = "HOLD_TRIGGER_EVIDENCE"
            trigger_decision = "HOLD_TRIGGER_EVIDENCE"
        trigger_hash = changes.get("trigger_hash", "f" * 64)
        trigger = new(E3ModeTriggerEvidenceV1, {
            "geometry": trigger_geometry, "trigger_generation_id": changes.get("trigger_generation_id", "trigger-1"),
            "trigger_evidence_sha256": trigger_hash, "mode": changes.get("trigger_mode", mode),
            "mode_lineage_sha256": changes.get("trigger_lineage", "b" * 64),
            "mode_matches": changes.get("mode_matches", True), "mode_lineage_matches": changes.get("mode_lineage_matches", True),
            "canonical_symbol": changes.get("canonical_symbol", "BTCUSDT"), "symbol_matches": changes.get("symbol_matches", True),
            "side": changes.get("trigger_side", side), "side_matches": changes.get("side_matches", True),
            "structure_timeframe": changes.get("trigger_structure_timeframe", "4h"),
            "structure_timeframe_matches": changes.get("structure_timeframe_matches", True),
            "structure_generation_id": changes.get("trigger_structure_generation", "structure-1"),
            "structure_generation_matches": changes.get("structure_generation_matches", True),
            "decision": changes.get("trigger_decision", trigger_decision), "reason_code": trigger_reason,
            "mapping": {"geometry": copy.deepcopy(geometry_map), "trigger_generation_id": changes.get("trigger_generation_id", "trigger-1"),
                        "trigger_evidence_sha256": trigger_hash, "reason_code": trigger_reason},
            **gates,
        })
        lifecycle_targets = clone(targets) if changes.get("lifecycle_targets_mismatch") else targets
        lifecycle_admission = clone(admission) if changes.get("lifecycle_admission_mismatch") else admission
        lifecycle_trigger = clone(trigger) if changes.get("lifecycle_trigger_mismatch") else trigger
        lifecycle_geometry = clone(geometry) if changes.get("lifecycle_geometry_mismatch") else geometry
        life_reason = changes.get("lifecycle_reason", "PASS_LIFECYCLE_ACTIONABLE")
        life_decision = changes.get("lifecycle_decision", "PASS_LIFECYCLE")
        life_actionable = changes.get("lifecycle_actionable", True)
        structure_valid = changes.get("structure_valid", True)
        lifecycle_hash = changes.get("lifecycle_hash", "1" * 64)
        life_flags = {
            "geometry_identity_matches": changes.get("life_geometry_identity", True),
            "targets_identity_matches": changes.get("life_targets_identity", True),
            "admission_identity_matches": changes.get("life_admission_identity", True),
            "trigger_identity_matches": changes.get("life_trigger_identity", True),
            "mode_lineage_matches": changes.get("life_mode_lineage", True),
            "symbol_matches": changes.get("life_symbol", True),
            "side_matches": changes.get("life_side", True),
            "structure_timeframe_matches": changes.get("life_timeframe", True),
            "structure_generation_matches": changes.get("life_generation", True),
            "targets_ready": changes.get("life_targets_ready", True),
            "price_admission_pass": changes.get("life_price_pass", price_reason == "PASS_PRICE_ADMISSION"),
            "trigger_evidence_pass": changes.get("life_trigger_pass", trigger_reason == "PASS_TRIGGER_EVIDENCE"),
            "transition_legal": changes.get("transition_legal", True),
            "actionable_ready": life_actionable,
        }
        lifecycle = new(E3LifecycleResultV1, {
            "geometry": lifecycle_geometry, "structural_targets": lifecycle_targets,
            "price_zone_admission": lifecycle_admission, "mode_trigger_evidence": lifecycle_trigger,
            "structure_valid": structure_valid, "expected_state": changes.get("expected_state", "ACTIONABLE"),
            "resulting_state": changes.get("resulting_state", "ACTIONABLE"), "decision": life_decision,
            "reason_code": life_reason, "lifecycle_sha256": lifecycle_hash,
            "mapping": {"geometry": copy.deepcopy(geometry_map), "structural_targets": copy.deepcopy(store[id(targets)]["mapping"]),
                        "price_zone_admission": copy.deepcopy(store[id(admission)]["mapping"]),
                        "mode_trigger_evidence": copy.deepcopy(store[id(trigger)]["mapping"]),
                        "lifecycle_sha256": lifecycle_hash, "reason_code": life_reason},
            **life_flags,
        })
        return {
            "geometry": geometry, "structural_targets": targets,
            "executable_price_snapshot": snapshot, "price_zone_admission": admission,
            "mode_trigger_evidence": trigger, "setup_lifecycle": lifecycle,
        }

    return {"make": make, "store": store}


def build(bundle):
    return actionable.build_e3_actionable_admission(**bundle)


def assert_sanitized(call):
    with pytest.raises(ValueError, match=r"^invalid E3 actionable admission$") as caught:
        call()
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_api_structure_signature_annotations():
    assert actionable.__all__ == ("E3ActionableAdmissionResultV1", "build_e3_actionable_admission")
    public = {name for name, value in vars(actionable).items() if not name.startswith("_") and
              (inspect.isclass(value) or inspect.isfunction(value)) and getattr(value, "__module__", None) == actionable.__name__}
    assert public == {"E3ActionableAdmissionResultV1", "build_e3_actionable_admission"}
    assert tuple(field.name for field in dataclasses.fields(actionable.E3ActionableAdmissionResultV1)) == FIELDS
    annotations = actionable.E3ActionableAdmissionResultV1.__annotations__
    dependency_types = (E3GoldenZoneGeometryV1, E3StructuralTargetsV1, E3ExecutablePriceSnapshotV1,
                        E3PriceZoneAdmissionV1, E3ModeTriggerEvidenceV1, E3LifecycleResultV1)
    assert tuple(annotations[name] for name in FIELDS[2:8]) == dependency_types
    assert all(annotations[name] is str for name in (FIELDS[0], FIELDS[1], *FIELDS[25:29]))
    assert all(annotations[name] is bool for name in FIELDS[8:25])
    cls = actionable.E3ActionableAdmissionResultV1
    assert cls.__dataclass_params__.frozen is True and "__slots__" in cls.__dict__
    assert {name for name, value in cls.__dict__.items() if not name.startswith("_") and inspect.isfunction(value)} == {"to_mapping"}
    signature = inspect.signature(actionable.build_e3_actionable_admission)
    assert tuple(signature.parameters) == FIELDS[2:8]
    assert all(item.kind is inspect.Parameter.KEYWORD_ONLY and item.default is inspect.Parameter.empty for item in signature.parameters.values())
    assert signature.return_annotation is cls


def test_exact_constants():
    expected = {
        "SCHEMA_VERSION": "e3-actionable-admission-v1", "POLICY_VERSION": "e3-detached-actionable-admission-v1",
        "DECISION_PASS": "PASS_ACTIONABLE_ADMISSION", "DECISION_HOLD": "HOLD_ACTIONABLE_ADMISSION",
        "REASON_PASS": "PASS_ACTIONABLE_ADMISSION", "REASON_GEOMETRY_IDENTITY": "HOLD_ACTIONABLE_GEOMETRY_IDENTITY_MISMATCH",
        "REASON_TARGETS_IDENTITY": "HOLD_ACTIONABLE_TARGETS_IDENTITY_MISMATCH", "REASON_SNAPSHOT_IDENTITY": "HOLD_ACTIONABLE_SNAPSHOT_IDENTITY_MISMATCH",
        "REASON_ADMISSION_IDENTITY": "HOLD_ACTIONABLE_PRICE_ADMISSION_IDENTITY_MISMATCH", "REASON_TRIGGER_IDENTITY": "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_IDENTITY_MISMATCH",
        "REASON_LIFECYCLE_IDENTITY": "HOLD_ACTIONABLE_LIFECYCLE_IDENTITY_MISMATCH", "REASON_MODE_LINEAGE": "HOLD_ACTIONABLE_MODE_LINEAGE_MISMATCH",
        "REASON_SYMBOL": "HOLD_ACTIONABLE_SYMBOL_MISMATCH", "REASON_SIDE": "HOLD_ACTIONABLE_SIDE_MISMATCH",
        "REASON_STRUCTURE_TIMEFRAME": "HOLD_ACTIONABLE_STRUCTURE_TIMEFRAME_MISMATCH", "REASON_STRUCTURE_GENERATION": "HOLD_ACTIONABLE_STRUCTURE_GENERATION_MISMATCH",
        "REASON_TARGETS_NOT_READY": "HOLD_ACTIONABLE_TARGETS_NOT_READY", "REASON_PRICE_OUTSIDE_ZONE": "HOLD_ACTIONABLE_PRICE_OUTSIDE_ZONE",
        "REASON_PRICE_STALE": "HOLD_ACTIONABLE_PRICE_STALE", "REASON_PRICE_SPREAD": "HOLD_ACTIONABLE_PRICE_SPREAD",
        "REASON_PRICE_SLIPPAGE": "HOLD_ACTIONABLE_PRICE_SLIPPAGE", "REASON_PRICE_NOT_PASS": "HOLD_ACTIONABLE_PRICE_ADMISSION_NOT_PASS",
        "REASON_TRIGGER_FUTURE": "HOLD_ACTIONABLE_TRIGGER_FUTURE", "REASON_TRIGGER_STALE": "HOLD_ACTIONABLE_TRIGGER_STALE",
        "REASON_TRIGGER_NOT_PASS": "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_NOT_PASS", "REASON_STRUCTURE_INVALIDATED": "HOLD_ACTIONABLE_STRUCTURE_INVALIDATED",
        "REASON_PRICE_LEFT_ZONE": "HOLD_ACTIONABLE_PRICE_LEFT_ZONE", "REASON_TRIGGER_LOST": "HOLD_ACTIONABLE_TRIGGER_LOST",
        "REASON_LIFECYCLE_IDENTITY_HOLD": "HOLD_ACTIONABLE_LIFECYCLE_IDENTITY_HOLD", "REASON_ILLEGAL_TRANSITION": "HOLD_ACTIONABLE_ILLEGAL_TRANSITION",
        "REASON_LIFECYCLE_NOT_ACTIONABLE": "HOLD_ACTIONABLE_LIFECYCLE_NOT_ACTIONABLE", "ERROR": "invalid E3 actionable admission",
    }
    assert {name: getattr(actionable, name) for name in expected} == expected


@pytest.mark.parametrize(("mode", "side"), (
    ("SWING", "LONG"),
    ("SWING", "SHORT"),
    ("INTRADAY", "LONG"),
    ("INTRADAY", "SHORT"),
    ("SCALP", "LONG"),
    ("SCALP", "SHORT"),
))
def test_complete_mode_side_passes(mode, side):
    chain = _build_real_actionable_chain(mode, side)
    result = chain["result"]
    geometry = chain["geometry"]
    trigger = chain["mode_trigger_evidence"]
    profile = get_mode_profile(mode)
    assert result.actionable_admitted is True
    assert result.decision == "PASS_ACTIONABLE_ADMISSION"
    assert result.reason_code == "PASS_ACTIONABLE_ADMISSION"
    assert result.geometry is geometry
    assert result.structural_targets is chain["structural_targets"]
    assert result.executable_price_snapshot is chain["executable_price_snapshot"]
    assert result.price_zone_admission is chain["price_zone_admission"]
    assert result.mode_trigger_evidence is trigger
    assert result.setup_lifecycle is chain["setup_lifecycle"]
    assert geometry.mode == mode
    assert geometry.side == side
    assert trigger.mode == mode
    assert trigger.side == side
    assert trigger.trigger_timeframe == profile.trigger_timeframe
    assert geometry.structure_timeframe == profile.structure_timeframe


def test_mapping_identity_detachment_and_round_trip(evidence_factory):
    bundle = evidence_factory["make"]()
    result = build(bundle)
    assert not hasattr(result, "__dict__")
    mapping = result.to_mapping()
    assert tuple(mapping) == FIELDS
    for name in FIELDS[2:8]:
        assert mapping[name] == bundle[name].to_mapping()
    mapping["geometry"]["mode"] = "CHANGED"
    assert result.to_mapping()["geometry"]["mode"] == "SWING"
    values = {field.name: getattr(result, field.name) for field in dataclasses.fields(result)}
    replay = actionable.E3ActionableAdmissionResultV1(**values)
    assert replay == result
    assert all(getattr(replay, name) is bundle[name] for name in FIELDS[2:8])


def test_exact_dependency_types_subclasses_and_corruption(evidence_factory):
    bundle = evidence_factory["make"]()
    for name in FIELDS[2:8]:
        changed = dict(bundle); changed[name] = object()
        assert_sanitized(lambda changed=changed: build(changed))
    class GeometrySubclass(E3GoldenZoneGeometryV1):
        pass
    changed = dict(bundle); changed["geometry"] = object.__new__(GeometrySubclass)
    assert_sanitized(lambda: build(changed))
    evidence_factory["store"][id(bundle["setup_lifecycle"])]["corrupt"] = True
    assert_sanitized(lambda: build(bundle))


@pytest.mark.parametrize(("changes", "reason", "field"), (
    ({"targets_geometry_mismatch": True}, "HOLD_ACTIONABLE_GEOMETRY_IDENTITY_MISMATCH", "geometry_identity_matches"),
    ({"lifecycle_targets_mismatch": True}, "HOLD_ACTIONABLE_TARGETS_IDENTITY_MISMATCH", "targets_identity_matches"),
    ({"admission_snapshot_mismatch": True}, "HOLD_ACTIONABLE_SNAPSHOT_IDENTITY_MISMATCH", "snapshot_identity_matches"),
    ({"lifecycle_admission_mismatch": True}, "HOLD_ACTIONABLE_PRICE_ADMISSION_IDENTITY_MISMATCH", "admission_identity_matches"),
    ({"lifecycle_trigger_mismatch": True}, "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_IDENTITY_MISMATCH", "trigger_identity_matches"),
    ({"trigger_mode": "INTRADAY"}, "HOLD_ACTIONABLE_MODE_LINEAGE_MISMATCH", "mode_lineage_matches"),
    ({"canonical_symbol": "ETHUSDT"}, "HOLD_ACTIONABLE_SYMBOL_MISMATCH", "symbol_matches"),
    ({"trigger_side": "SHORT"}, "HOLD_ACTIONABLE_SIDE_MISMATCH", "side_matches"),
    ({"trigger_structure_timeframe": "1h"}, "HOLD_ACTIONABLE_STRUCTURE_TIMEFRAME_MISMATCH", "structure_timeframe_matches"),
    ({"trigger_structure_generation": "other"}, "HOLD_ACTIONABLE_STRUCTURE_GENERATION_MISMATCH", "structure_generation_matches"),
))
def test_identity_typed_holds(evidence_factory, changes, reason, field):
    result = build(evidence_factory["make"](**changes))
    assert result.decision == "HOLD_ACTIONABLE_ADMISSION"
    assert result.reason_code == reason
    assert result.actionable_admitted is False
    assert getattr(result, field) is False


def test_identity_priority_and_independent_values(evidence_factory):
    cases = (
        ({"targets_geometry_mismatch": True, "canonical_symbol": "ETHUSDT"}, "HOLD_ACTIONABLE_GEOMETRY_IDENTITY_MISMATCH"),
        ({"lifecycle_targets_mismatch": True, "admission_snapshot_mismatch": True}, "HOLD_ACTIONABLE_TARGETS_IDENTITY_MISMATCH"),
        ({"admission_snapshot_mismatch": True, "lifecycle_admission_mismatch": True}, "HOLD_ACTIONABLE_SNAPSHOT_IDENTITY_MISMATCH"),
        ({"lifecycle_admission_mismatch": True, "lifecycle_trigger_mismatch": True}, "HOLD_ACTIONABLE_PRICE_ADMISSION_IDENTITY_MISMATCH"),
        ({"trigger_mode": "INTRADAY", "canonical_symbol": "ETHUSDT"}, "HOLD_ACTIONABLE_MODE_LINEAGE_MISMATCH"),
        ({"canonical_symbol": "ETHUSDT", "trigger_side": "SHORT"}, "HOLD_ACTIONABLE_SYMBOL_MISMATCH"),
    )
    for changes, reason in cases:
        assert build(evidence_factory["make"](**changes)).reason_code == reason
    multiple = build(evidence_factory["make"](trigger_mode="INTRADAY", canonical_symbol="ETHUSDT", trigger_side="SHORT"))
    assert multiple.mode_lineage_matches is False and multiple.symbol_matches is False and multiple.side_matches is False


def test_target_readiness_fail_closed(evidence_factory):
    valid = build(evidence_factory["make"]())
    assert valid.targets_ready is True
    held = build(evidence_factory["make"](life_targets_ready=False))
    assert held.reason_code == "HOLD_ACTIONABLE_TARGETS_NOT_READY"
    assert held.actionable_admitted is False


@pytest.mark.parametrize(("reason", "expected"), (
    ("HOLD_PRICE_OUTSIDE_ZONE", "HOLD_ACTIONABLE_PRICE_OUTSIDE_ZONE"),
    ("HOLD_PRICE_STALE", "HOLD_ACTIONABLE_PRICE_STALE"),
    ("HOLD_PRICE_SPREAD", "HOLD_ACTIONABLE_PRICE_SPREAD"),
    ("HOLD_PRICE_SLIPPAGE", "HOLD_ACTIONABLE_PRICE_SLIPPAGE"),
    ("HOLD_PRICE_ADMISSION", "HOLD_ACTIONABLE_PRICE_ADMISSION_NOT_PASS"),
))
def test_price_classification(evidence_factory, reason, expected):
    result = build(evidence_factory["make"](price_reason=reason))
    assert result.reason_code == expected
    assert result.decision == "HOLD_ACTIONABLE_ADMISSION"
    assert result.actionable_admitted is False


@pytest.mark.parametrize(("changes", "expected"), (
    ({"trigger_reason": "HOLD_TRIGGER_FUTURE"}, "HOLD_ACTIONABLE_TRIGGER_FUTURE"),
    ({"trigger_reason": "HOLD_TRIGGER_STALE"}, "HOLD_ACTIONABLE_TRIGGER_STALE"),
    ({"lost_gate": "trigger_candle_closed"}, "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_NOT_PASS"),
    ({"lost_gate": "trigger_rule_satisfied"}, "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_NOT_PASS"),
    ({"lost_gate": "trigger_close_aligned"}, "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_NOT_PASS"),
    ({"lost_gate": "trigger_timeframe_matches"}, "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_NOT_PASS"),
    ({"lost_gate": "trigger_rule_matches"}, "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_NOT_PASS"),
    ({"trigger_reason": "HOLD_TRIGGER_EVIDENCE"}, "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_NOT_PASS"),
))
def test_trigger_classification(evidence_factory, changes, expected):
    result = build(evidence_factory["make"](**changes))
    assert result.reason_code == expected
    assert result.decision == "HOLD_ACTIONABLE_ADMISSION" and result.actionable_admitted is False


@pytest.mark.parametrize(("changes", "expected"), (
    ({"structure_valid": False, "lifecycle_actionable": False, "lifecycle_reason": "PASS_LIFECYCLE_INVALIDATED_STRUCTURE", "expected_state": "INVALIDATED", "resulting_state": "INVALIDATED"}, "HOLD_ACTIONABLE_STRUCTURE_INVALIDATED"),
    ({"lifecycle_actionable": False, "lifecycle_reason": "PASS_LIFECYCLE_INVALIDATED_PRICE_LEFT_ZONE", "expected_state": "INVALIDATED", "resulting_state": "INVALIDATED"}, "HOLD_ACTIONABLE_PRICE_LEFT_ZONE"),
    ({"lifecycle_actionable": False, "lifecycle_reason": "PASS_LIFECYCLE_INVALIDATED_TRIGGER_LOST", "expected_state": "INVALIDATED", "resulting_state": "INVALIDATED"}, "HOLD_ACTIONABLE_TRIGGER_LOST"),
    ({"lifecycle_actionable": False, "lifecycle_decision": "HOLD_LIFECYCLE", "lifecycle_reason": "HOLD_LIFECYCLE_ILLEGAL_TRANSITION", "transition_legal": False}, "HOLD_ACTIONABLE_ILLEGAL_TRANSITION"),
    ({"lifecycle_actionable": False, "lifecycle_reason": "PASS_LIFECYCLE_DISCOVERED", "expected_state": "DISCOVERED", "resulting_state": "DISCOVERED"}, "HOLD_ACTIONABLE_LIFECYCLE_NOT_ACTIONABLE"),
    ({"lifecycle_actionable": False, "lifecycle_reason": "PASS_LIFECYCLE_ARMED_WAITING_TRIGGER", "expected_state": "ARMED", "resulting_state": "ARMED"}, "HOLD_ACTIONABLE_LIFECYCLE_NOT_ACTIONABLE"),
))
def test_lifecycle_classification(evidence_factory, changes, expected):
    result = build(evidence_factory["make"](**changes))
    assert result.reason_code == expected and result.actionable_admitted is False


def test_reserved_lifecycle_catch_all_reasons_are_nonemittable_for_real_chains():
    chain = _build_real_actionable_chain("SWING", "LONG")
    geometry = chain["geometry"]
    targets = chain["structural_targets"]
    snapshot = chain["executable_price_snapshot"]
    admission = chain["price_zone_admission"]
    trigger = chain["mode_trigger_evidence"]
    lifecycle = chain["setup_lifecycle"]
    reserved_reasons = {
        actionable.REASON_LIFECYCLE_IDENTITY,
        actionable.REASON_LIFECYCLE_IDENTITY_HOLD,
    }

    def compose(*, candidate_geometry=geometry, candidate_targets=targets,
                candidate_snapshot=snapshot, candidate_admission=admission,
                candidate_trigger=trigger, candidate_lifecycle=lifecycle):
        return actionable.build_e3_actionable_admission(
            geometry=candidate_geometry,
            structural_targets=candidate_targets,
            executable_price_snapshot=candidate_snapshot,
            price_zone_admission=candidate_admission,
            mode_trigger_evidence=candidate_trigger,
            setup_lifecycle=candidate_lifecycle,
        )

    second_geometry = _build_real_actionable_chain("SWING", "LONG")["geometry"]
    geometry_result = compose(candidate_geometry=second_geometry)
    second_targets = build_e3_structural_targets(
        geometry=geometry,
        ordered_destinations=(
            ("STRUCTURE", "destination:tp1-alt", 12146, geometry.structure_timeframe, geometry.structure_generation_id),
            ("LIQUIDITY", "destination:tp2-alt", 12528, geometry.structure_timeframe, geometry.structure_generation_id),
        ),
    )
    targets_result = compose(candidate_targets=second_targets)
    inside_tick = geometry.golden_zone_low_tick + (
        geometry.golden_zone_high_tick - geometry.golden_zone_low_tick
    ) // 2
    second_snapshot = build_e3_executable_price_snapshot(
        geometry=geometry,
        venue="BINANCE_USDM",
        quote_generation_id="quote:real-swing-long-second",
        exchange_timestamp="2026-07-30T00:15:00Z",
        best_bid_tick=inside_tick - 1,
        best_ask_tick=inside_tick,
        last_price_tick=inside_tick,
        mark_price_tick=inside_tick,
        modeled_adverse_slippage_bps=0,
        tick_size=geometry.tick_size,
    )
    snapshot_result = compose(candidate_snapshot=second_snapshot)
    second_admission = build_e3_price_zone_admission(
        geometry=geometry,
        snapshot=snapshot,
        evaluation_timestamp="2026-07-30T00:15:00Z",
    )
    admission_result = compose(candidate_admission=second_admission)
    profile = get_mode_profile("SWING")

    def build_trigger(**overrides):
        arguments = {
            "geometry": geometry,
            "mode": geometry.mode,
            "mode_lineage_sha256": geometry.mode_lineage_sha256,
            "canonical_symbol": geometry.canonical_symbol,
            "side": geometry.side,
            "structure_timeframe": geometry.structure_timeframe,
            "structure_generation_id": geometry.structure_generation_id,
            "trigger_timeframe": profile.trigger_timeframe,
            "trigger_rule": profile.trigger_rule,
            "trigger_candle_close_at": "2026-07-30T00:15:00Z",
            "trigger_candle_closed": True,
            "trigger_rule_satisfied": True,
            "evaluation_timestamp": "2026-07-30T00:15:00Z",
        }
        arguments.update(overrides)
        return build_e3_mode_trigger_evidence(**arguments)

    trigger_result = compose(candidate_trigger=build_trigger())

    def mismatch_result(mismatched_trigger):
        mismatched_lifecycle = build_e3_setup_lifecycle(
            previous_state="DISCOVERED",
            requested_state="DISCOVERED",
            geometry=geometry,
            structural_targets=targets,
            price_zone_admission=admission,
            mode_trigger_evidence=mismatched_trigger,
            structure_valid=True,
        )
        return compose(candidate_trigger=mismatched_trigger, candidate_lifecycle=mismatched_lifecycle)

    intraday_profile = get_mode_profile("INTRADAY")
    mode_result = mismatch_result(build_trigger(
        mode="INTRADAY",
        mode_lineage_sha256=build_mode_audit_lineage("INTRADAY").lineage_sha256,
        trigger_timeframe=intraday_profile.trigger_timeframe,
        trigger_rule=intraday_profile.trigger_rule,
    ))
    symbol_result = mismatch_result(build_trigger(canonical_symbol="ETH/USDT:USDT"))
    side_result = mismatch_result(build_trigger(side="SHORT"))
    alternate_timeframe = get_mode_profile("INTRADAY").structure_timeframe
    assert alternate_timeframe != geometry.structure_timeframe
    timeframe_result = mismatch_result(build_trigger(structure_timeframe=alternate_timeframe))
    generation_result = mismatch_result(build_trigger(structure_generation_id="structure:g2"))
    results_and_reasons = (
        (geometry_result, actionable.REASON_GEOMETRY_IDENTITY),
        (targets_result, actionable.REASON_TARGETS_IDENTITY),
        (snapshot_result, actionable.REASON_SNAPSHOT_IDENTITY),
        (admission_result, actionable.REASON_ADMISSION_IDENTITY),
        (trigger_result, actionable.REASON_TRIGGER_IDENTITY),
        (mode_result, actionable.REASON_MODE_LINEAGE),
        (symbol_result, actionable.REASON_SYMBOL),
        (side_result, actionable.REASON_SIDE),
        (timeframe_result, actionable.REASON_STRUCTURE_TIMEFRAME),
        (generation_result, actionable.REASON_STRUCTURE_GENERATION),
    )
    emitted_reasons = set()
    for result, expected_reason in results_and_reasons:
        assert type(result) is actionable.E3ActionableAdmissionResultV1
        assert result.actionable_admitted is False
        assert result.decision == actionable.DECISION_HOLD
        assert result.reason_code == expected_reason
        assert result.reason_code not in reserved_reasons
        emitted_reasons.add(result.reason_code)
    assert reserved_reasons == {
        "HOLD_ACTIONABLE_LIFECYCLE_IDENTITY_MISMATCH",
        "HOLD_ACTIONABLE_LIFECYCLE_IDENTITY_HOLD",
    }
    assert emitted_reasons.isdisjoint(reserved_reasons)


def test_complete_actionable_conjunction_fail_closed(evidence_factory):
    passed = build(evidence_factory["make"]())
    gates = tuple(getattr(passed, name) for name in FIELDS[8:25])
    assert all(gate is True for gate in gates)
    mutations = (
        {"targets_geometry_mismatch": True}, {"lifecycle_targets_mismatch": True},
        {"admission_snapshot_mismatch": True}, {"lifecycle_admission_mismatch": True},
        {"lifecycle_trigger_mismatch": True}, {"trigger_mode": "INTRADAY"},
        {"canonical_symbol": "ETHUSDT"}, {"trigger_side": "SHORT"},
        {"trigger_structure_timeframe": "1h"}, {"trigger_structure_generation": "other"},
        {"life_targets_ready": False}, {"price_reason": "HOLD_PRICE_STALE"},
        {"trigger_reason": "HOLD_TRIGGER_STALE"}, {"lifecycle_actionable": False},
    )
    for changes in mutations:
        result = build(evidence_factory["make"](**changes))
        assert not (result.actionable_admitted and result.decision == "PASS_ACTIONABLE_ADMISSION" and result.reason_code == "PASS_ACTIONABLE_ADMISSION")


def test_composition_id_and_hash_sensitivity(evidence_factory):
    bundle = evidence_factory["make"]()
    first = build(bundle); replay = build(bundle)
    assert first.composition_id == replay.composition_id
    assert first.actionable_admission_sha256 == replay.actionable_admission_sha256
    assert re.fullmatch(r"adm-[0-9a-f]{64}", first.composition_id)
    hashes = {first.actionable_admission_sha256}
    ids = {first.composition_id}
    for changes in ({"geometry_hash": "2" * 64}, {"targets_hash": "3" * 64}, {"snapshot_hash": "4" * 64},
                    {"admission_hash": "5" * 64}, {"trigger_hash": "6" * 64}, {"lifecycle_hash": "7" * 64},
                    {"trigger_generation_id": "trigger-2"}):
        result = build(evidence_factory["make"](**changes)); hashes.add(result.actionable_admission_sha256); ids.add(result.composition_id)
    assert len(hashes) == 8 and len(ids) == 8
    payload = first.to_mapping(); digest = payload.pop("actionable_admission_sha256")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    assert hashlib.sha256(encoded).hexdigest() == digest


def test_direct_constructor_revalidates_every_field(evidence_factory):
    result = build(evidence_factory["make"]())
    base = {field.name: getattr(result, field.name) for field in dataclasses.fields(result)}
    for name in FIELDS:
        changed = dict(base); value = changed[name]
        if name in FIELDS[2:8]: changed[name] = object()
        elif type(value) is bool: changed[name] = not value
        elif name == "actionable_admission_sha256": changed[name] = "0" * 64
        elif name == "composition_id": changed[name] = "adm-" + "0" * 64
        else: changed[name] = value + "-corrupt"
        assert_sanitized(lambda changed=changed: actionable.E3ActionableAdmissionResultV1(**changed))
    class StringSubclass(str):
        pass
    changed = dict(base); changed["decision"] = StringSubclass(base["decision"])
    assert_sanitized(lambda: actionable.E3ActionableAdmissionResultV1(**changed))
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.decision = "HOLD_ACTIONABLE_ADMISSION"


def test_one_candidate_and_effect_free_surface(evidence_factory):
    bundle = evidence_factory["make"]()
    for collection in ([bundle["geometry"]], (bundle["geometry"],), {"geometry": bundle["geometry"]}, iter((bundle["geometry"],))):
        changed = dict(bundle); changed["geometry"] = collection
        assert_sanitized(lambda changed=changed: build(changed))
    single_token_authorities = {
        "rank", "score", "selected", "publication", "signal", "telegram", "slot",
        "order", "trading", "position", "persistence", "provider", "owner", "service",
        "deployment",
    }

    def has_authority_field(field_name):
        field_tokens = tuple(
            token
            for token in field_name.lower().split("_")
            if token
        )
        single_token_match = any(token in single_token_authorities for token in field_tokens)
        pair_lock_match = any(
            pair == ("pair", "lock")
            for pair in zip(field_tokens, field_tokens[1:])
        )
        return single_token_match or pair_lock_match

    forbidden_examples = (
        "rank", "candidate_rank", "score", "selected_index", "publication_intent",
        "signal_id", "telegram_send", "slot_change", "pair_lock", "pair_lock_change",
        "order_change", "trading", "position_state", "persistence_write",
        "provider_result", "owner_command", "service_call", "deployment_state",
    )
    assert not has_authority_field("composition_id")
    assert has_authority_field("position_state")
    assert has_authority_field("pair_lock")
    assert all(has_authority_field(field_name) for field_name in forbidden_examples)
    assert all(not has_authority_field(field_name) for field_name in FIELDS)


def test_zero_effect_ast_and_e2_nonintegration():
    source = Path(actionable.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    standard = set(); project = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): standard.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): project.append((node.module, tuple(alias.name for alias in node.names)))
        assert not isinstance(node, ast.Constant) or type(node.value) is not float
        assert not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div)
    assert standard == {"dataclasses", "hashlib", "json", "re", "typing"}
    assert {module for module, names in project} == {
        "engine.e3_golden_zone_geometry_v1", "engine.e3_structural_targets_v1",
        "engine.e3_executable_price_snapshot_v1", "engine.e3_price_zone_admission_v1",
        "engine.e3_mode_trigger_evidence_v1", "engine.e3_setup_lifecycle_v1",
    }
    def dotted_name(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = dotted_name(node.value)
            return f"{parent}.{node.attr}" if parent else None
        return None

    forbidden_import_roots = {
        "aiohttp", "asyncio", "ccxt", "datetime", "httpx", "multiprocessing", "os",
        "pathlib", "psycopg", "random", "redis", "requests", "socket", "sqlalchemy",
        "sqlite3", "subprocess", "threading", "time", "urllib", "uuid",
    }
    expected_project_imports = {
        ("engine.e3_golden_zone_geometry_v1", ("E3GoldenZoneGeometryV1",)),
        ("engine.e3_structural_targets_v1", ("E3StructuralTargetsV1",)),
        ("engine.e3_executable_price_snapshot_v1", ("E3ExecutablePriceSnapshotV1",)),
        ("engine.e3_price_zone_admission_v1", ("E3PriceZoneAdmissionV1",)),
        ("engine.e3_mode_trigger_evidence_v1", ("E3ModeTriggerEvidenceV1",)),
        ("engine.e3_setup_lifecycle_v1", ("E3LifecycleResultV1",)),
    }
    assert set(project) == expected_project_imports
    current_clock_calls = {
        "datetime.now", "datetime.utcnow", "date.today", "time.time",
        "time.monotonic", "time.perf_counter",
    }
    dangerous_calls = {"open", "eval", "exec", "compile", "__import__", "sorted", "filter", "float"}
    effect_suffixes = (
        ".send", ".publish", ".create_order", ".place_order", ".execute_trade",
        ".write_text", ".write_bytes", ".unlink", ".rename",
    )
    resolved_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden_import_roots
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module is not None
            root = node.module.split(".")[0]
            assert root not in forbidden_import_roots
            assert node.module != "engine.e2"
            assert not node.module.startswith("engine.e2.")
            assert node.module != "engine.mode_scan_composition_v1"
            assert not node.module.startswith("engine.mode_scan_composition_v1.")
        elif isinstance(node, ast.Call):
            call_name = dotted_name(node.func)
            if call_name is not None:
                resolved_calls.append(call_name)
                assert call_name.split(".")[0] not in forbidden_import_roots
                assert call_name not in current_clock_calls
                assert call_name not in dangerous_calls
                assert call_name != "importlib.import_module"
                assert not call_name.startswith("engine.e2.")
                assert not call_name.startswith("engine.mode_scan_composition_v1.")
                assert not any(call_name.endswith(suffix) for suffix in effect_suffixes)
        assert not isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom))
    assert "__import__" not in resolved_calls
    assert "importlib.import_module" not in resolved_calls
    assert "float(" not in source and "Decimal" not in source and "Fraction" not in source
