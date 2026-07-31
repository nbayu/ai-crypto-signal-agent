import ast
import copy
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e3_setup_lifecycle_v1 as lifecycle
from engine.e3_golden_zone_geometry_v1 import E3GoldenZoneGeometryV1
from engine.e3_structural_targets_v1 import E3StructuralTargetsV1
from engine.e3_price_zone_admission_v1 import E3PriceZoneAdmissionV1
from engine.e3_mode_trigger_evidence_v1 import E3ModeTriggerEvidenceV1


FIELD_NAMES = (
    "schema_version",
    "policy_version",
    "previous_state",
    "requested_state",
    "expected_state",
    "resulting_state",
    "geometry",
    "structural_targets",
    "price_zone_admission",
    "mode_trigger_evidence",
    "structure_valid",
    "geometry_identity_matches",
    "targets_identity_matches",
    "admission_identity_matches",
    "trigger_identity_matches",
    "mode_lineage_matches",
    "symbol_matches",
    "side_matches",
    "structure_timeframe_matches",
    "structure_generation_matches",
    "targets_ready",
    "price_admission_pass",
    "trigger_evidence_pass",
    "transition_legal",
    "actionable_ready",
    "decision",
    "reason_code",
    "lifecycle_sha256",
)


class _Snapshot:
    def __init__(self, geometry):
        self.geometry = geometry


@pytest.fixture
def evidence_factory(monkeypatch):
    store = {}
    classes = (
        E3GoldenZoneGeometryV1,
        E3StructuralTargetsV1,
        E3PriceZoneAdmissionV1,
        E3ModeTriggerEvidenceV1,
    )
    names = {
        E3GoldenZoneGeometryV1: (
            "golden_zone_low_tick", "golden_zone_high_tick", "mode",
            "mode_lineage_sha256", "canonical_symbol", "side",
            "structure_timeframe", "structure_generation_id",
        ),
        E3StructuralTargetsV1: (
            "geometry", "tp1_destination_id", "tp2_destination_id",
            "tp1_tick", "tp2_tick", "targets_sha256",
        ),
        E3PriceZoneAdmissionV1: (
            "geometry", "snapshot", "zone_low_tick", "zone_high_tick",
            "decision", "reason_code", "age_within_limit",
            "spread_within_limit", "slippage_within_limit", "inside_zone",
        ),
        E3ModeTriggerEvidenceV1: (
            "geometry", "mode", "mode_lineage_sha256", "mode_matches",
            "mode_lineage_matches", "canonical_symbol", "symbol_matches",
            "side", "side_matches", "structure_timeframe",
            "structure_timeframe_matches", "structure_generation_id",
            "structure_generation_matches", "trigger_candle_closed",
            "trigger_rule_satisfied", "trigger_close_aligned",
            "trigger_not_future", "trigger_fresh", "trigger_timeframe_matches",
            "trigger_rule_matches", "decision", "reason_code",
        ),
    }

    def invariant(self):
        if store[id(self)].get("corrupt", False):
            raise RuntimeError("dependency corruption detail")

    def to_mapping(self):
        return copy.deepcopy(store[id(self)]["mapping"])

    for cls in classes:
        monkeypatch.setattr(cls, "__post_init__", invariant, raising=False)
        monkeypatch.setattr(cls, "to_mapping", to_mapping, raising=False)
        for name in names[cls]:
            monkeypatch.setattr(
                cls,
                name,
                property(lambda self, attribute=name: store[id(self)][attribute]),
                raising=False,
            )

    def new(cls, values):
        obj = object.__new__(cls)
        store[id(obj)] = values
        return obj

    def make(**changes):
        geometry_mapping = {
            "schema_version": "geometry-v1",
            "canonical_symbol": "BTCUSDT",
            "side": "LONG",
            "structure_timeframe": "4h",
            "structure_generation_id": "structure-1",
            "geometry_sha256": changes.get("geometry_hash", "a" * 64),
        }
        geometry = new(E3GoldenZoneGeometryV1, {
            "golden_zone_low_tick": 100,
            "golden_zone_high_tick": 120,
            "mode": "RETRACEMENT",
            "mode_lineage_sha256": "b" * 64,
            "canonical_symbol": "BTCUSDT",
            "side": "LONG",
            "structure_timeframe": "4h",
            "structure_generation_id": "structure-1",
            "mapping": geometry_mapping,
        })

        def geometry_clone():
            values = dict(store[id(geometry)])
            values["mapping"] = copy.deepcopy(geometry_mapping)
            return new(E3GoldenZoneGeometryV1, values)

        targets_geometry = geometry_clone() if changes.get("targets_geometry_mismatch") else geometry
        targets_hash = changes.get("targets_hash", "c" * 64)
        structural_targets = new(E3StructuralTargetsV1, {
            "geometry": targets_geometry,
            "tp1_destination_id": "target-1",
            "tp2_destination_id": changes.get("tp2_destination_id", "target-2"),
            "tp1_tick": 140,
            "tp2_tick": changes.get("tp2_tick", 160),
            "targets_sha256": targets_hash,
            "mapping": {
                "schema_version": "targets-v1",
                "geometry": copy.deepcopy(geometry_mapping),
                "targets_sha256": targets_hash,
            },
        })

        admission_geometry = geometry_clone() if changes.get("admission_geometry_mismatch") else geometry
        snapshot_geometry = geometry_clone() if changes.get("snapshot_geometry_mismatch") else geometry
        admission_reason = changes.get("admission_reason", "PASS_PRICE_ADMISSION")
        admission_decision = "PASS_PRICE_ADMISSION" if admission_reason == "PASS_PRICE_ADMISSION" else "HOLD_PRICE_ADMISSION"
        age = admission_reason != "HOLD_PRICE_STALE"
        spread = admission_reason != "HOLD_PRICE_SPREAD"
        slippage = admission_reason != "HOLD_PRICE_SLIPPAGE"
        inside = admission_reason != "HOLD_PRICE_OUTSIDE_ZONE"
        age = changes.get("age_within_limit", age)
        spread = changes.get("spread_within_limit", spread)
        slippage = changes.get("slippage_within_limit", slippage)
        inside = changes.get("inside_zone", inside)
        snapshot = _Snapshot(snapshot_geometry)
        admission_hash = changes.get("admission_hash", "d" * 64)
        price_zone_admission = new(E3PriceZoneAdmissionV1, {
            "geometry": admission_geometry,
            "snapshot": snapshot,
            "zone_low_tick": changes.get("zone_low_tick", 100),
            "zone_high_tick": changes.get("zone_high_tick", 120),
            "decision": changes.get("admission_decision", admission_decision),
            "reason_code": admission_reason,
            "age_within_limit": age,
            "spread_within_limit": spread,
            "slippage_within_limit": slippage,
            "inside_zone": inside,
            "mapping": {
                "schema_version": "admission-v1",
                "geometry": copy.deepcopy(geometry_mapping),
                "snapshot": {"geometry": copy.deepcopy(geometry_mapping), "snapshot_sha256": "e" * 64},
                "admission_sha256": admission_hash,
                "decision": changes.get("admission_decision", admission_decision),
                "reason_code": admission_reason,
            },
        })

        trigger_geometry = geometry_clone() if changes.get("trigger_geometry_mismatch") else geometry
        trigger_reason = changes.get("trigger_reason", "PASS_TRIGGER_EVIDENCE")
        trigger_decision = "PASS_TRIGGER_EVIDENCE" if trigger_reason == "PASS_TRIGGER_EVIDENCE" else "HOLD_TRIGGER_EVIDENCE"
        gates = {
            "trigger_candle_closed": True,
            "trigger_rule_satisfied": True,
            "trigger_close_aligned": True,
            "trigger_not_future": trigger_reason != "HOLD_TRIGGER_FUTURE",
            "trigger_fresh": trigger_reason != "HOLD_TRIGGER_STALE",
            "trigger_timeframe_matches": True,
            "trigger_rule_matches": True,
        }
        lost_gate = changes.get("lost_gate")
        if lost_gate is not None:
            gates[lost_gate] = False
            trigger_reason = "HOLD_TRIGGER_EVIDENCE"
            trigger_decision = "HOLD_TRIGGER_EVIDENCE"
        for name in tuple(gates):
            gates[name] = changes.get(name, gates[name])
        trigger_hash = changes.get("trigger_hash", "f" * 64)
        trigger_values = {
            "geometry": trigger_geometry,
            "mode": changes.get("mode", "RETRACEMENT"),
            "mode_lineage_sha256": changes.get("mode_lineage_sha256", "b" * 64),
            "mode_matches": changes.get("mode_matches", True),
            "mode_lineage_matches": changes.get("mode_lineage_matches", True),
            "canonical_symbol": changes.get("canonical_symbol", "BTCUSDT"),
            "symbol_matches": changes.get("symbol_matches", True),
            "side": changes.get("side", "LONG"),
            "side_matches": changes.get("side_matches", True),
            "structure_timeframe": changes.get("structure_timeframe", "4h"),
            "structure_timeframe_matches": changes.get("structure_timeframe_matches", True),
            "structure_generation_id": changes.get("structure_generation_id", "structure-1"),
            "structure_generation_matches": changes.get("structure_generation_matches", True),
            "decision": changes.get("trigger_decision", trigger_decision),
            "reason_code": trigger_reason,
            "mapping": {
                "schema_version": "trigger-v1",
                "geometry": copy.deepcopy(geometry_mapping),
                "trigger_generation_id": changes.get("trigger_generation_id", "trigger-1"),
                "trigger_evidence_sha256": trigger_hash,
                "decision": changes.get("trigger_decision", trigger_decision),
                "reason_code": trigger_reason,
            },
            **gates,
        }
        mode_trigger_evidence = new(E3ModeTriggerEvidenceV1, trigger_values)
        return {
            "geometry": geometry,
            "structural_targets": structural_targets,
            "price_zone_admission": price_zone_admission,
            "mode_trigger_evidence": mode_trigger_evidence,
        }

    return {"make": make, "store": store}


def build(bundle, previous, requested, structure_valid=True):
    return lifecycle.build_e3_setup_lifecycle(
        previous_state=previous,
        requested_state=requested,
        geometry=bundle["geometry"],
        structural_targets=bundle["structural_targets"],
        price_zone_admission=bundle["price_zone_admission"],
        mode_trigger_evidence=bundle["mode_trigger_evidence"],
        structure_valid=structure_valid,
    )


def assert_sanitized(call):
    with pytest.raises(ValueError, match=r"^invalid E3 setup lifecycle$") as caught:
        call()
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_api_structure_signature_and_annotations():
    assert lifecycle.__all__ == ("E3LifecycleResultV1", "build_e3_setup_lifecycle")
    public_defined = {
        name for name, value in vars(lifecycle).items()
        if not name.startswith("_")
        and (inspect.isclass(value) or inspect.isfunction(value))
        and getattr(value, "__module__", None) == lifecycle.__name__
    }
    assert public_defined == {"E3LifecycleResultV1", "build_e3_setup_lifecycle"}
    assert tuple(field.name for field in dataclasses.fields(lifecycle.E3LifecycleResultV1)) == FIELD_NAMES
    expected_annotations = {
        "schema_version": str, "policy_version": str, "previous_state": str,
        "requested_state": str, "expected_state": str, "resulting_state": str,
        "geometry": E3GoldenZoneGeometryV1,
        "structural_targets": E3StructuralTargetsV1,
        "price_zone_admission": E3PriceZoneAdmissionV1,
        "mode_trigger_evidence": E3ModeTriggerEvidenceV1,
        "structure_valid": bool, "geometry_identity_matches": bool,
        "targets_identity_matches": bool, "admission_identity_matches": bool,
        "trigger_identity_matches": bool, "mode_lineage_matches": bool,
        "symbol_matches": bool, "side_matches": bool,
        "structure_timeframe_matches": bool, "structure_generation_matches": bool,
        "targets_ready": bool, "price_admission_pass": bool,
        "trigger_evidence_pass": bool, "transition_legal": bool,
        "actionable_ready": bool, "decision": str, "reason_code": str,
        "lifecycle_sha256": str,
    }
    assert lifecycle.E3LifecycleResultV1.__annotations__ == expected_annotations
    assert lifecycle.E3LifecycleResultV1.__dataclass_params__.frozen is True
    assert "__slots__" in lifecycle.E3LifecycleResultV1.__dict__
    methods = {
        name for name, value in lifecycle.E3LifecycleResultV1.__dict__.items()
        if not name.startswith("_") and inspect.isfunction(value)
    }
    assert methods == {"to_mapping"}
    signature = inspect.signature(lifecycle.build_e3_setup_lifecycle)
    assert tuple(signature.parameters) == (
        "previous_state", "requested_state", "geometry", "structural_targets",
        "price_zone_admission", "mode_trigger_evidence", "structure_valid",
    )
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in signature.parameters.values())
    assert all(parameter.default is inspect.Parameter.empty for parameter in signature.parameters.values())
    assert signature.return_annotation is lifecycle.E3LifecycleResultV1


def test_exact_constants():
    expected = {
        "SCHEMA_VERSION": "e3-setup-lifecycle-v1",
        "POLICY_VERSION": "e3-deterministic-setup-lifecycle-v1",
        "STATE_DISCOVERED": "DISCOVERED", "STATE_ARMED": "ARMED",
        "STATE_ACTIONABLE": "ACTIONABLE", "STATE_INVALIDATED": "INVALIDATED",
        "DECISION_PASS": "PASS_LIFECYCLE", "DECISION_HOLD": "HOLD_LIFECYCLE",
        "REASON_DISCOVERED": "PASS_LIFECYCLE_DISCOVERED",
        "REASON_ARMED_WAITING_PRICE": "PASS_LIFECYCLE_ARMED_WAITING_PRICE",
        "REASON_ARMED_WAITING_TRIGGER": "PASS_LIFECYCLE_ARMED_WAITING_TRIGGER",
        "REASON_ACTIONABLE": "PASS_LIFECYCLE_ACTIONABLE",
        "REASON_ACTIONABLE_STABLE": "PASS_LIFECYCLE_ACTIONABLE_STABLE",
        "REASON_INVALIDATED_TERMINAL": "PASS_LIFECYCLE_INVALIDATED_TERMINAL",
        "REASON_INVALIDATED_STRUCTURE": "PASS_LIFECYCLE_INVALIDATED_STRUCTURE",
        "REASON_INVALIDATED_PRICE_STALE": "PASS_LIFECYCLE_INVALIDATED_PRICE_STALE",
        "REASON_INVALIDATED_PRICE_SPREAD": "PASS_LIFECYCLE_INVALIDATED_PRICE_SPREAD",
        "REASON_INVALIDATED_PRICE_SLIPPAGE": "PASS_LIFECYCLE_INVALIDATED_PRICE_SLIPPAGE",
        "REASON_INVALIDATED_PRICE_LEFT_ZONE": "PASS_LIFECYCLE_INVALIDATED_PRICE_LEFT_ZONE",
        "REASON_INVALIDATED_TRIGGER_FUTURE": "PASS_LIFECYCLE_INVALIDATED_TRIGGER_FUTURE",
        "REASON_INVALIDATED_TRIGGER_STALE": "PASS_LIFECYCLE_INVALIDATED_TRIGGER_STALE",
        "REASON_INVALIDATED_TRIGGER_LOST": "PASS_LIFECYCLE_INVALIDATED_TRIGGER_LOST",
        "REASON_GEOMETRY_IDENTITY": "HOLD_LIFECYCLE_GEOMETRY_IDENTITY_MISMATCH",
        "REASON_TARGETS_IDENTITY": "HOLD_LIFECYCLE_TARGETS_IDENTITY_MISMATCH",
        "REASON_ADMISSION_IDENTITY": "HOLD_LIFECYCLE_PRICE_ADMISSION_IDENTITY_MISMATCH",
        "REASON_TRIGGER_IDENTITY": "HOLD_LIFECYCLE_TRIGGER_EVIDENCE_IDENTITY_MISMATCH",
        "REASON_MODE_LINEAGE": "HOLD_LIFECYCLE_MODE_LINEAGE_MISMATCH",
        "REASON_SYMBOL": "HOLD_LIFECYCLE_SYMBOL_MISMATCH",
        "REASON_SIDE": "HOLD_LIFECYCLE_SIDE_MISMATCH",
        "REASON_STRUCTURE_TIMEFRAME": "HOLD_LIFECYCLE_STRUCTURE_TIMEFRAME_MISMATCH",
        "REASON_STRUCTURE_GENERATION": "HOLD_LIFECYCLE_STRUCTURE_GENERATION_MISMATCH",
        "REASON_ILLEGAL_TRANSITION": "HOLD_LIFECYCLE_ILLEGAL_TRANSITION",
        "ERROR": "invalid E3 setup lifecycle",
    }
    assert {name: getattr(lifecycle, name) for name in expected} == expected


def test_identity_mapping_immutability_and_round_trip(evidence_factory):
    bundle = evidence_factory["make"]()
    result = build(bundle, "DISCOVERED", "ACTIONABLE")
    assert not hasattr(result, "__dict__")
    for name in ("geometry", "structural_targets", "price_zone_admission", "mode_trigger_evidence"):
        assert getattr(result, name) is bundle[name]
    mapping = result.to_mapping()
    assert tuple(mapping) == FIELD_NAMES
    assert mapping["geometry"] == bundle["geometry"].to_mapping()
    assert mapping["structural_targets"] == bundle["structural_targets"].to_mapping()
    assert mapping["price_zone_admission"] == bundle["price_zone_admission"].to_mapping()
    assert mapping["mode_trigger_evidence"] == bundle["mode_trigger_evidence"].to_mapping()
    mapping["geometry"]["canonical_symbol"] = "CHANGED"
    assert result.to_mapping()["geometry"]["canonical_symbol"] == "BTCUSDT"
    kwargs = {field.name: getattr(result, field.name) for field in dataclasses.fields(result)}
    replay = lifecycle.E3LifecycleResultV1(**kwargs)
    assert replay == result
    assert replay.geometry is bundle["geometry"]


def test_exact_types_lookalikes_subclasses_and_corruption_rejected(evidence_factory):
    bundle = evidence_factory["make"]()
    for field, wrong in (
        ("geometry", object()), ("structural_targets", object()),
        ("price_zone_admission", object()), ("mode_trigger_evidence", object()),
    ):
        changed = dict(bundle)
        changed[field] = wrong
        assert_sanitized(lambda changed=changed: build(changed, "DISCOVERED", "ACTIONABLE"))

    class GeometrySubclass(E3GoldenZoneGeometryV1):
        pass
    changed = dict(bundle)
    changed["geometry"] = object.__new__(GeometrySubclass)
    assert_sanitized(lambda: build(changed, "DISCOVERED", "ACTIONABLE"))

    evidence_factory["store"][id(bundle["mode_trigger_evidence"])]["corrupt"] = True
    assert_sanitized(lambda: build(bundle, "DISCOVERED", "ACTIONABLE"))
    assert_sanitized(lambda: lifecycle.build_e3_setup_lifecycle(
        previous_state=" discovered ", requested_state="ACTIONABLE",
        geometry=bundle["geometry"], structural_targets=bundle["structural_targets"],
        price_zone_admission=bundle["price_zone_admission"],
        mode_trigger_evidence=bundle["mode_trigger_evidence"], structure_valid=True,
    ))


@pytest.mark.parametrize(("previous", "changes", "structure_valid", "expected", "reason"), (
    ("DISCOVERED", {"admission_reason": "HOLD_PRICE_OUTSIDE_ZONE"}, True, "DISCOVERED", "PASS_LIFECYCLE_DISCOVERED"),
    ("DISCOVERED", {"lost_gate": "trigger_rule_satisfied"}, True, "ARMED", "PASS_LIFECYCLE_ARMED_WAITING_TRIGGER"),
    ("DISCOVERED", {}, True, "ACTIONABLE", "PASS_LIFECYCLE_ACTIONABLE"),
    ("DISCOVERED", {}, False, "INVALIDATED", "PASS_LIFECYCLE_INVALIDATED_STRUCTURE"),
    ("ARMED", {"admission_reason": "HOLD_PRICE_OUTSIDE_ZONE"}, True, "ARMED", "PASS_LIFECYCLE_ARMED_WAITING_PRICE"),
    ("ARMED", {}, True, "ACTIONABLE", "PASS_LIFECYCLE_ACTIONABLE"),
    ("ARMED", {}, False, "INVALIDATED", "PASS_LIFECYCLE_INVALIDATED_STRUCTURE"),
    ("ACTIONABLE", {}, True, "ACTIONABLE", "PASS_LIFECYCLE_ACTIONABLE_STABLE"),
    ("ACTIONABLE", {"admission_reason": "HOLD_PRICE_OUTSIDE_ZONE"}, True, "INVALIDATED", "PASS_LIFECYCLE_INVALIDATED_PRICE_LEFT_ZONE"),
    ("INVALIDATED", {}, True, "INVALIDATED", "PASS_LIFECYCLE_INVALIDATED_TERMINAL"),
))
def test_complete_legal_transition_matrix(evidence_factory, previous, changes, structure_valid, expected, reason):
    result = build(evidence_factory["make"](**changes), previous, expected, structure_valid)
    assert result.expected_state == expected
    assert result.resulting_state == expected
    assert result.transition_legal is True
    assert result.decision == "PASS_LIFECYCLE"
    assert result.reason_code == reason


@pytest.mark.parametrize(("previous", "changes", "structure_valid", "expected"), (
    ("DISCOVERED", {}, True, "ACTIONABLE"),
    ("ARMED", {}, True, "ACTIONABLE"),
    ("ACTIONABLE", {}, True, "ACTIONABLE"),
    ("INVALIDATED", {}, True, "INVALIDATED"),
    ("DISCOVERED", {}, False, "INVALIDATED"),
    ("ARMED", {}, False, "INVALIDATED"),
    ("ACTIONABLE", {}, False, "INVALIDATED"),
))
def test_every_illegal_requested_state_is_typed_hold(evidence_factory, previous, changes, structure_valid, expected):
    states = ("DISCOVERED", "ARMED", "ACTIONABLE", "INVALIDATED")
    for requested in states:
        if requested == expected:
            continue
        result = build(evidence_factory["make"](**changes), previous, requested, structure_valid)
        assert result.expected_state == expected
        assert result.transition_legal is False
        assert result.decision == "HOLD_LIFECYCLE"
        assert result.reason_code == "HOLD_LIFECYCLE_ILLEGAL_TRANSITION"
        authoritative = "INVALIDATED" if expected == "INVALIDATED" else previous
        assert result.resulting_state == authoritative


def test_discovered_and_armed_semantics(evidence_factory):
    outside = build(evidence_factory["make"](admission_reason="HOLD_PRICE_OUTSIDE_ZONE"), "DISCOVERED", "DISCOVERED")
    assert outside.actionable_ready is False
    waiting = build(evidence_factory["make"](lost_gate="trigger_candle_closed"), "DISCOVERED", "ARMED")
    assert waiting.trigger_evidence_pass is False
    armed_outside = build(evidence_factory["make"](admission_reason="HOLD_PRICE_OUTSIDE_ZONE"), "ARMED", "ARMED")
    assert armed_outside.reason_code == "PASS_LIFECYCLE_ARMED_WAITING_PRICE"
    armed_waiting = build(evidence_factory["make"](lost_gate="trigger_close_aligned"), "ARMED", "ARMED")
    assert armed_waiting.reason_code == "PASS_LIFECYCLE_ARMED_WAITING_TRIGGER"
    direct = build(evidence_factory["make"](), "DISCOVERED", "ACTIONABLE")
    assert direct.actionable_ready is True
    forbidden_fields = ("telegram", "publication", "slot", "pair_lock", "order", "trading", "persistence")
    assert all(not any(token in name.lower() for token in forbidden_fields) for name in FIELD_NAMES)


@pytest.mark.parametrize(("reason", "success_reason"), (
    ("HOLD_PRICE_STALE", "PASS_LIFECYCLE_INVALIDATED_PRICE_STALE"),
    ("HOLD_PRICE_SPREAD", "PASS_LIFECYCLE_INVALIDATED_PRICE_SPREAD"),
    ("HOLD_PRICE_SLIPPAGE", "PASS_LIFECYCLE_INVALIDATED_PRICE_SLIPPAGE"),
))
def test_price_quality_invalidation(evidence_factory, reason, success_reason):
    for previous in ("DISCOVERED", "ARMED", "ACTIONABLE"):
        result = build(evidence_factory["make"](admission_reason=reason), previous, "INVALIDATED")
        assert result.reason_code == success_reason
        assert result.resulting_state == "INVALIDATED"


@pytest.mark.parametrize(("reason", "success_reason"), (
    ("HOLD_TRIGGER_FUTURE", "PASS_LIFECYCLE_INVALIDATED_TRIGGER_FUTURE"),
    ("HOLD_TRIGGER_STALE", "PASS_LIFECYCLE_INVALIDATED_TRIGGER_STALE"),
))
def test_trigger_freshness_invalidation(evidence_factory, reason, success_reason):
    for previous in ("DISCOVERED", "ARMED", "ACTIONABLE"):
        result = build(evidence_factory["make"](trigger_reason=reason), previous, "INVALIDATED")
        assert result.reason_code == success_reason


@pytest.mark.parametrize("gate", (
    "trigger_candle_closed", "trigger_rule_satisfied", "trigger_close_aligned",
    "trigger_timeframe_matches", "trigger_rule_matches",
))
def test_nonfreshness_confirmation_loss_classification(evidence_factory, gate):
    discovered = build(evidence_factory["make"](lost_gate=gate), "DISCOVERED", "ARMED")
    armed = build(evidence_factory["make"](lost_gate=gate), "ARMED", "ARMED")
    actionable = build(evidence_factory["make"](lost_gate=gate), "ACTIONABLE", "INVALIDATED")
    assert discovered.reason_code == "PASS_LIFECYCLE_ARMED_WAITING_TRIGGER"
    assert armed.reason_code == "PASS_LIFECYCLE_ARMED_WAITING_TRIGGER"
    assert actionable.reason_code == "PASS_LIFECYCLE_INVALIDATED_TRIGGER_LOST"


def test_structure_invalidation_priority_and_terminal_state(evidence_factory):
    changes = {"admission_reason": "HOLD_PRICE_STALE", "trigger_reason": "HOLD_TRIGGER_STALE"}
    for previous in ("DISCOVERED", "ARMED", "ACTIONABLE"):
        result = build(evidence_factory["make"](**changes), previous, "INVALIDATED", False)
        assert result.reason_code == "PASS_LIFECYCLE_INVALIDATED_STRUCTURE"
    terminal = build(evidence_factory["make"](**changes), "INVALIDATED", "INVALIDATED", False)
    assert terminal.reason_code == "PASS_LIFECYCLE_INVALIDATED_TERMINAL"
    for requested in ("DISCOVERED", "ARMED", "ACTIONABLE"):
        held = build(evidence_factory["make"](), "INVALIDATED", requested)
        assert held.resulting_state == "INVALIDATED"
        assert held.reason_code == "HOLD_LIFECYCLE_ILLEGAL_TRANSITION"


@pytest.mark.parametrize(("changes", "reason", "false_field"), (
    ({"targets_geometry_mismatch": True}, "HOLD_LIFECYCLE_GEOMETRY_IDENTITY_MISMATCH", "geometry_identity_matches"),
    ({"targets_hash": "not-a-hash"}, "HOLD_LIFECYCLE_TARGETS_IDENTITY_MISMATCH", "targets_identity_matches"),
    ({"zone_low_tick": 99}, "HOLD_LIFECYCLE_PRICE_ADMISSION_IDENTITY_MISMATCH", "admission_identity_matches"),
    ({"trigger_geometry_mismatch": True}, "HOLD_LIFECYCLE_GEOMETRY_IDENTITY_MISMATCH", "trigger_identity_matches"),
    ({"mode": "BREAKOUT"}, "HOLD_LIFECYCLE_MODE_LINEAGE_MISMATCH", "mode_lineage_matches"),
    ({"canonical_symbol": "ETHUSDT"}, "HOLD_LIFECYCLE_SYMBOL_MISMATCH", "symbol_matches"),
    ({"side": "SHORT"}, "HOLD_LIFECYCLE_SIDE_MISMATCH", "side_matches"),
    ({"structure_timeframe": "1h"}, "HOLD_LIFECYCLE_STRUCTURE_TIMEFRAME_MISMATCH", "structure_timeframe_matches"),
    ({"structure_generation_id": "structure-2"}, "HOLD_LIFECYCLE_STRUCTURE_GENERATION_MISMATCH", "structure_generation_matches"),
))
def test_identity_mismatch_typed_holds(evidence_factory, changes, reason, false_field):
    result = build(evidence_factory["make"](**changes), "DISCOVERED", "ACTIONABLE")
    assert isinstance(result, lifecycle.E3LifecycleResultV1)
    assert result.decision == "HOLD_LIFECYCLE"
    assert result.reason_code == reason
    assert result.expected_state == "DISCOVERED"
    assert result.resulting_state == "DISCOVERED"
    assert result.transition_legal is False
    assert result.actionable_ready is False
    assert getattr(result, false_field) is False


def test_complete_identity_priority_and_independent_booleans(evidence_factory):
    cases = (
        ({"targets_geometry_mismatch": True, "mode": "BREAKOUT"}, "HOLD_LIFECYCLE_GEOMETRY_IDENTITY_MISMATCH"),
        ({"targets_hash": "bad", "zone_low_tick": 99}, "HOLD_LIFECYCLE_TARGETS_IDENTITY_MISMATCH"),
        ({"zone_low_tick": 99, "mode": "BREAKOUT"}, "HOLD_LIFECYCLE_PRICE_ADMISSION_IDENTITY_MISMATCH"),
        ({"mode": "BREAKOUT", "canonical_symbol": "ETHUSDT"}, "HOLD_LIFECYCLE_MODE_LINEAGE_MISMATCH"),
        ({"canonical_symbol": "ETHUSDT", "side": "SHORT"}, "HOLD_LIFECYCLE_SYMBOL_MISMATCH"),
        ({"side": "SHORT", "structure_timeframe": "1h"}, "HOLD_LIFECYCLE_SIDE_MISMATCH"),
        ({"structure_timeframe": "1h", "structure_generation_id": "structure-2"}, "HOLD_LIFECYCLE_STRUCTURE_TIMEFRAME_MISMATCH"),
    )
    for changes, reason in cases:
        result = build(evidence_factory["make"](**changes), "DISCOVERED", "ACTIONABLE")
        assert result.reason_code == reason
    combined = build(evidence_factory["make"](mode="BREAKOUT", canonical_symbol="ETHUSDT", side="SHORT"), "DISCOVERED", "ACTIONABLE")
    assert combined.mode_lineage_matches is False
    assert combined.symbol_matches is False
    assert combined.side_matches is False


def test_actionable_gate_conjunction_fail_closed(evidence_factory):
    valid = build(evidence_factory["make"](), "DISCOVERED", "ACTIONABLE")
    required = (
        valid.structure_valid, valid.geometry_identity_matches, valid.targets_identity_matches,
        valid.admission_identity_matches, valid.trigger_identity_matches,
        valid.mode_lineage_matches, valid.symbol_matches, valid.side_matches,
        valid.structure_timeframe_matches, valid.structure_generation_matches,
        valid.targets_ready, valid.price_admission_pass, valid.trigger_evidence_pass,
    )
    assert all(value is True for value in required)
    mutations = (
        {"mode": "BREAKOUT"}, {"canonical_symbol": "ETHUSDT"}, {"side": "SHORT"},
        {"structure_timeframe": "1h"}, {"structure_generation_id": "other"},
        {"targets_geometry_mismatch": True}, {"zone_low_tick": 99},
        {"lost_gate": "trigger_rule_satisfied"}, {"admission_reason": "HOLD_PRICE_OUTSIDE_ZONE"},
    )
    for changes in mutations:
        result = build(evidence_factory["make"](**changes), "DISCOVERED", "ACTIONABLE")
        assert not (
            result.actionable_ready is True
            and result.resulting_state == "ACTIONABLE"
            and result.decision == "PASS_LIFECYCLE"
        )


def test_direct_constructor_revalidates_every_field(evidence_factory):
    result = build(evidence_factory["make"](), "DISCOVERED", "ACTIONABLE")
    base = {field.name: getattr(result, field.name) for field in dataclasses.fields(result)}
    for name in FIELD_NAMES:
        changed = dict(base)
        value = changed[name]
        if name in ("geometry", "structural_targets", "price_zone_admission", "mode_trigger_evidence"):
            changed[name] = object()
        elif type(value) is bool:
            changed[name] = not value
        elif name == "lifecycle_sha256":
            changed[name] = "0" * 64
        else:
            changed[name] = value + "-corrupt"
        assert_sanitized(lambda changed=changed: lifecycle.E3LifecycleResultV1(**changed))

    class StringSubclass(str):
        pass
    changed = dict(base)
    changed["previous_state"] = StringSubclass("DISCOVERED")
    assert_sanitized(lambda: lifecycle.E3LifecycleResultV1(**changed))
    frozen = result
    with pytest.raises(dataclasses.FrozenInstanceError):
        frozen.decision = "HOLD_LIFECYCLE"


def test_hash_determinism_sensitivity_and_complete_payload(evidence_factory):
    bundle = evidence_factory["make"]()
    first = build(bundle, "DISCOVERED", "ACTIONABLE")
    second = build(bundle, "DISCOVERED", "ACTIONABLE")
    assert first.lifecycle_sha256 == second.lifecycle_sha256
    payload = first.to_mapping()
    digest = payload.pop("lifecycle_sha256")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    assert hashlib.sha256(encoded).hexdigest() == digest
    variants = (
        evidence_factory["make"](geometry_hash="0" * 64),
        evidence_factory["make"](targets_hash="1" * 64),
        evidence_factory["make"](admission_hash="2" * 64),
        evidence_factory["make"](trigger_hash="3" * 64),
        evidence_factory["make"](trigger_generation_id="trigger-2"),
    )
    hashes = {first.lifecycle_sha256}
    for variant in variants:
        hashes.add(build(variant, "DISCOVERED", "ACTIONABLE").lifecycle_sha256)
    held = build(bundle, "DISCOVERED", "ARMED")
    invalidated = build(bundle, "DISCOVERED", "INVALIDATED", False)
    hashes.update((held.lifecycle_sha256, invalidated.lifecycle_sha256))
    assert len(hashes) == 8
    assert held.decision != first.decision and held.reason_code != first.reason_code


def test_malformed_primitives_are_sanitized(evidence_factory):
    bundle = evidence_factory["make"]()
    for previous in (None, 1, True, "discovered", " DISCOVERED", "UNKNOWN"):
        assert_sanitized(lambda previous=previous: lifecycle.build_e3_setup_lifecycle(
            previous_state=previous, requested_state="ACTIONABLE", structure_valid=True, **bundle
        ))
    for structure_valid in (0, 1, None, "true"):
        assert_sanitized(lambda structure_valid=structure_valid: lifecycle.build_e3_setup_lifecycle(
            previous_state="DISCOVERED", requested_state="ACTIONABLE",
            structure_valid=structure_valid, **bundle
        ))


def test_static_effect_and_authority_surface():
    source_path = Path(lifecycle.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    project = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            project.append((node.module, tuple(alias.name for alias in node.names)))
        assert not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div)
        assert not isinstance(node, ast.Constant) or not isinstance(node.value, float)
    assert imported == {"dataclasses", "hashlib", "json", "re", "typing"}
    assert project == [
        ("engine.e3_golden_zone_geometry_v1", ("E3GoldenZoneGeometryV1",)),
        ("engine.e3_structural_targets_v1", ("E3StructuralTargetsV1",)),
        ("engine.e3_price_zone_admission_v1", ("E3PriceZoneAdmissionV1",)),
        ("engine.e3_mode_trigger_evidence_v1", ("E3ModeTriggerEvidenceV1",)),
    ]
    forbidden = {
        "ccxt", "requests", "httpx", "aiohttp", "urllib", "socket", "subprocess",
        "pathlib", "os", "time", "datetime", "asyncio", "threading",
        "multiprocessing", "random", "uuid", "sqlite", "sqlalchemy", "psycopg", "redis",
    }
    assert imported.isdisjoint(forbidden)
    assert "float(" not in source
    assert "Decimal" not in source and "Fraction" not in source
    authority = ("telegram", "publication", "slot", "pair_lock", "order", "trading", "persistence", "provider", "exchange")
    assert all(not any(token in name.lower() for token in authority) for name in FIELD_NAMES)
