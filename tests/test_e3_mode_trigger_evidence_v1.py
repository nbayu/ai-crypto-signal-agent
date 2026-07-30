import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta
import hashlib
import inspect
import json
from pathlib import Path
import re
import subprocess

import pytest

import engine.e3_mode_trigger_evidence_v1 as trigger_module
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
    build_e3_golden_zone_geometry,
)
from engine.e3_mode_trigger_evidence_v1 import (
    E3ModeTriggerEvidenceV1,
    build_e3_mode_trigger_evidence,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_profile_v1 import (
    MODE_PROFILE_POLICY_VERSION,
    ModeProfileV1,
    get_mode_profile,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "engine/e3_mode_trigger_evidence_v1.py"
TEST_PATH = ROOT / "tests/test_e3_mode_trigger_evidence_v1.py"
ERROR = "invalid E3 mode trigger evidence"
MODES = ("SWING", "INTRADAY", "SCALP")
SIDES = ("LONG", "SHORT")
PROFILE_VALUES = {
    "SWING": (
        "1h",
        "15m",
        "closed 15m BOS/CHOCH or reclaim aligned with 1h structure and 4h bias",
        900,
        "2026-07-30T00:15:00Z",
    ),
    "INTRADAY": (
        "15m",
        "5m",
        "closed 5m BOS/CHOCH or reclaim aligned with 15m structure and 1h bias",
        300,
        "2026-07-30T00:05:00Z",
    ),
    "SCALP": (
        "5m",
        "3m",
        "closed 3m liquidity sweep/reclaim followed by micro-BOS aligned with 5m structure and 15m bias",
        180,
        "2026-07-30T00:03:00Z",
    ),
}
FIELD_NAMES = [
    "schema_version",
    "policy_version",
    "trigger_generation_policy_version",
    "geometry",
    "mode_profile_policy_version",
    "mode",
    "mode_lineage_sha256",
    "canonical_symbol",
    "side",
    "structure_timeframe",
    "structure_generation_id",
    "trigger_timeframe",
    "trigger_rule",
    "trigger_candle_close_at",
    "trigger_candle_closed",
    "trigger_rule_satisfied",
    "evaluation_timestamp",
    "trigger_age_seconds",
    "maximum_trigger_age_seconds",
    "mode_matches",
    "mode_lineage_matches",
    "symbol_matches",
    "side_matches",
    "structure_timeframe_matches",
    "structure_generation_matches",
    "trigger_timeframe_matches",
    "trigger_rule_matches",
    "trigger_close_aligned",
    "trigger_not_future",
    "trigger_fresh",
    "decision",
    "reason_code",
    "trigger_generation_id",
    "trigger_evidence_sha256",
]


class StringSubclass(str):
    pass


class IntegerSubclass(int):
    pass


class GeometrySubclass(E3GoldenZoneGeometryV1):
    pass


class GeometryLookalike:
    pass


def _iso_add(value, seconds):
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return (parsed + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _geometry(mode="SWING", side="LONG", generation="structure:g1", **overrides):
    if side == "LONG":
        low_at = "2026-07-29T00:00:00Z"
        high_at = "2026-07-29T01:00:00Z"
    else:
        high_at = "2026-07-29T00:00:00Z"
        low_at = "2026-07-29T01:00:00Z"
    values = {
        "mode": mode,
        "mode_lineage_sha256": build_mode_audit_lineage(mode).lineage_sha256,
        "canonical_symbol": "BTC/USDT:USDT",
        "side": side,
        "structure_generation_id": generation,
        "anchor_low_at": low_at,
        "anchor_low_tick": 1000,
        "anchor_high_at": high_at,
        "anchor_high_tick": 2000,
        "tick_size": "0.1",
    }
    values.update(overrides)
    return build_e3_golden_zone_geometry(**values)


def _values(geometry):
    profile = get_mode_profile(geometry.mode)
    close_at = PROFILE_VALUES[geometry.mode][4]
    return {
        "geometry": geometry,
        "mode": geometry.mode,
        "mode_lineage_sha256": geometry.mode_lineage_sha256,
        "canonical_symbol": geometry.canonical_symbol,
        "side": geometry.side,
        "structure_timeframe": geometry.structure_timeframe,
        "structure_generation_id": geometry.structure_generation_id,
        "trigger_timeframe": profile.trigger_timeframe,
        "trigger_rule": profile.trigger_rule,
        "trigger_candle_close_at": close_at,
        "trigger_candle_closed": True,
        "trigger_rule_satisfied": True,
        "evaluation_timestamp": close_at,
    }


def _evidence(geometry=None, **overrides):
    selected = _geometry() if geometry is None else geometry
    values = _values(selected)
    values.update(overrides)
    return build_e3_mode_trigger_evidence(**values)


def _constructor_values(result):
    mapping = result.to_mapping()
    mapping["geometry"] = result.geometry
    return mapping


def _assert_sanitized(call):
    with pytest.raises(ValueError, match=f"^{re.escape(ERROR)}$") as captured:
        call()
    assert captured.value.__cause__ is None


def _other_mode(mode):
    return {"SWING": "INTRADAY", "INTRADAY": "SCALP", "SCALP": "SWING"}[mode]


def test_exact_public_api_and_inventory():
    assert trigger_module.__all__ == (
        "E3ModeTriggerEvidenceV1",
        "build_e3_mode_trigger_evidence",
    )
    public = [
        name
        for name, value in vars(trigger_module).items()
        if not name.startswith("_")
        and getattr(value, "__module__", None) == trigger_module.__name__
        and (inspect.isclass(value) or inspect.isfunction(value))
    ]
    assert public == [
        "E3ModeTriggerEvidenceV1",
        "build_e3_mode_trigger_evidence",
    ]


def test_exact_dataclass_structure_and_annotations():
    assert [field.name for field in fields(E3ModeTriggerEvidenceV1)] == FIELD_NAMES
    annotations = E3ModeTriggerEvidenceV1.__annotations__
    assert list(annotations) == FIELD_NAMES
    assert annotations["geometry"] is E3GoldenZoneGeometryV1
    assert all(
        annotations[name] is bool
        for name in (
            "mode_matches",
            "mode_lineage_matches",
            "symbol_matches",
            "side_matches",
            "structure_timeframe_matches",
            "structure_generation_matches",
            "trigger_timeframe_matches",
            "trigger_rule_matches",
            "trigger_close_aligned",
            "trigger_not_future",
            "trigger_fresh",
        )
    )


def test_frozen_slots_mapping_and_one_public_method():
    result = _evidence()
    with pytest.raises(FrozenInstanceError):
        result.mode = "SCALP"
    assert not hasattr(result, "__dict__")
    public_methods = [
        name
        for name, value in vars(E3ModeTriggerEvidenceV1).items()
        if callable(value) and not name.startswith("_")
    ]
    assert public_methods == ["to_mapping"]
    assert list(result.to_mapping()) == FIELD_NAMES
    assert result.to_mapping()["geometry"] == result.geometry.to_mapping()
    assert result.to_mapping()["geometry"] is not result.geometry


def test_exact_builder_signature_and_return_annotation():
    signature = inspect.signature(build_e3_mode_trigger_evidence)
    assert list(signature.parameters) == [
        "geometry",
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "side",
        "structure_timeframe",
        "structure_generation_id",
        "trigger_timeframe",
        "trigger_rule",
        "trigger_candle_close_at",
        "trigger_candle_closed",
        "trigger_rule_satisfied",
        "evaluation_timestamp",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert signature.return_annotation is E3ModeTriggerEvidenceV1


def test_exact_constants():
    assert trigger_module._SCHEMA_VERSION == "e3-mode-trigger-evidence-v1"
    assert trigger_module._POLICY_VERSION == "d4-mode-trigger-evidence-v1"
    assert trigger_module._TRIGGER_GENERATION_POLICY_VERSION == "trigger-generation-v1"
    assert trigger_module._DECISION_PASS == "PASS_TRIGGER_EVIDENCE"
    assert trigger_module._DECISION_HOLD == "HOLD_TRIGGER_EVIDENCE"
    assert trigger_module._REASON_STALE == "HOLD_TRIGGER_STALE"
    assert trigger_module._REASON_FUTURE == "HOLD_TRIGGER_FUTURE"


@pytest.mark.parametrize("mode", MODES)
def test_exact_profile_binding_for_all_modes(mode):
    geometry = _geometry(mode=mode)
    result = _evidence(geometry)
    structure, trigger, rule, maximum_age, _ = PROFILE_VALUES[mode]
    assert result.mode == mode
    assert result.structure_timeframe == structure
    assert result.trigger_timeframe == trigger
    assert result.trigger_rule == rule
    assert result.maximum_trigger_age_seconds == maximum_age
    assert result.mode_profile_policy_version == MODE_PROFILE_POLICY_VERSION
    assert result.geometry is geometry


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("side", SIDES)
def test_pass_fixture_for_every_mode_and_side(mode, side):
    result = _evidence(_geometry(mode=mode, side=side))
    assert result.decision == "PASS_TRIGGER_EVIDENCE"
    assert result.reason_code == "PASS_TRIGGER_EVIDENCE"
    assert all(
        (
            result.mode_matches,
            result.mode_lineage_matches,
            result.symbol_matches,
            result.side_matches,
            result.structure_timeframe_matches,
            result.structure_generation_matches,
            result.trigger_timeframe_matches,
            result.trigger_rule_matches,
            result.trigger_close_aligned,
            result.trigger_not_future,
            result.trigger_fresh,
        )
    )


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("age_selector", ("zero", "below", "exact"))
def test_inclusive_freshness_pass_boundaries(mode, age_selector):
    geometry = _geometry(mode=mode)
    close_at = PROFILE_VALUES[mode][4]
    maximum = PROFILE_VALUES[mode][3]
    age = {"zero": 0, "below": maximum - 1, "exact": maximum}[age_selector]
    result = _evidence(geometry, evaluation_timestamp=_iso_add(close_at, age))
    assert result.trigger_age_seconds == age
    assert result.trigger_fresh is True
    assert result.decision == "PASS_TRIGGER_EVIDENCE"


@pytest.mark.parametrize("mode", MODES)
def test_one_second_stale_returns_typed_hold(mode):
    geometry = _geometry(mode=mode)
    close_at = PROFILE_VALUES[mode][4]
    result = _evidence(
        geometry,
        evaluation_timestamp=_iso_add(close_at, PROFILE_VALUES[mode][3] + 1),
    )
    assert isinstance(result, E3ModeTriggerEvidenceV1)
    assert result.trigger_fresh is False
    assert result.reason_code == "HOLD_TRIGGER_STALE"
    assert result.decision == "HOLD_TRIGGER_EVIDENCE"


@pytest.mark.parametrize("mode", MODES)
def test_negative_age_returns_typed_future_hold(mode):
    geometry = _geometry(mode=mode)
    close_at = PROFILE_VALUES[mode][4]
    result = _evidence(geometry, evaluation_timestamp=_iso_add(close_at, -1))
    assert result.trigger_age_seconds == -1
    assert result.trigger_not_future is False
    assert result.trigger_fresh is False
    assert result.reason_code == "HOLD_TRIGGER_FUTURE"


@pytest.mark.parametrize(
    ("closed", "confirmed", "reason"),
    (
        (False, True, "HOLD_TRIGGER_CANDLE_UNCLOSED"),
        (True, False, "HOLD_TRIGGER_RULE_UNCONFIRMED"),
        (False, False, "HOLD_TRIGGER_CANDLE_UNCLOSED"),
    ),
)
def test_closed_candle_and_rule_confirmation_gates(closed, confirmed, reason):
    result = _evidence(
        trigger_candle_closed=closed,
        trigger_rule_satisfied=confirmed,
    )
    assert result.reason_code == reason
    assert result.decision == "HOLD_TRIGGER_EVIDENCE"


@pytest.mark.parametrize("field", ("trigger_candle_closed", "trigger_rule_satisfied"))
@pytest.mark.parametrize("value", (1, "true", IntegerSubclass(1)))
def test_trigger_boolean_malformed_values_fail_closed(field, value):
    _assert_sanitized(lambda: _evidence(**{field: value}))


@pytest.mark.parametrize("mode", MODES)
def test_trigger_close_alignment_and_one_minute_off_grid(mode):
    geometry = _geometry(mode=mode)
    aligned = PROFILE_VALUES[mode][4]
    passing = _evidence(geometry)
    assert passing.trigger_close_aligned is True
    off_grid = _iso_add(aligned, 60)
    held = _evidence(
        geometry,
        trigger_candle_close_at=off_grid,
        evaluation_timestamp=off_grid,
    )
    assert held.trigger_close_aligned is False
    assert held.reason_code == "HOLD_TRIGGER_CLOSE_MISALIGNED"


@pytest.mark.parametrize(
    "timestamp",
    (
        "2026-07-30T00:15:00.000Z",
        "2026-07-30T00:15:00+00:00",
        "2026-07-30T00:15:00z",
        " 2026-07-30T00:15:00Z",
        "2026-02-30T00:15:00Z",
        StringSubclass("2026-07-30T00:15:00Z"),
    ),
)
def test_malformed_trigger_timestamp_is_sanitized(timestamp):
    _assert_sanitized(lambda: _evidence(trigger_candle_close_at=timestamp))


@pytest.mark.parametrize(
    ("overrides", "reason", "boolean_field"),
    (
        ({"mode": "INTRADAY"}, "HOLD_TRIGGER_MODE_MISMATCH", "mode_matches"),
        ({"mode_lineage_sha256": "0" * 64}, "HOLD_TRIGGER_MODE_LINEAGE_MISMATCH", "mode_lineage_matches"),
        ({"canonical_symbol": "ETH/USDT:USDT"}, "HOLD_TRIGGER_SYMBOL_MISMATCH", "symbol_matches"),
        ({"side": "SHORT"}, "HOLD_TRIGGER_SIDE_MISMATCH", "side_matches"),
        ({"structure_timeframe": "15m"}, "HOLD_TRIGGER_STRUCTURE_TIMEFRAME_MISMATCH", "structure_timeframe_matches"),
        ({"structure_generation_id": "structure:g2"}, "HOLD_TRIGGER_STRUCTURE_GENERATION_MISMATCH", "structure_generation_matches"),
        ({"trigger_timeframe": "5m"}, "HOLD_TRIGGER_TIMEFRAME_MISMATCH", "trigger_timeframe_matches"),
        ({"trigger_rule": "altered valid trigger rule"}, "HOLD_TRIGGER_RULE_MISMATCH", "trigger_rule_matches"),
    ),
)
def test_identity_mismatches_return_typed_holds(overrides, reason, boolean_field):
    result = _evidence(**overrides)
    assert isinstance(result, E3ModeTriggerEvidenceV1)
    assert result.decision == "HOLD_TRIGGER_EVIDENCE"
    assert result.reason_code == reason
    assert getattr(result, boolean_field) is False


@pytest.mark.parametrize("mode", MODES)
def test_no_mode_trigger_or_freshness_borrowing(mode):
    geometry = _geometry(mode=mode)
    other = _other_mode(mode)
    other_profile = get_mode_profile(other)
    maximum = PROFILE_VALUES[mode][3]
    close_at = PROFILE_VALUES[mode][4]
    result = _evidence(
        geometry,
        mode=other,
        trigger_timeframe=other_profile.trigger_timeframe,
        trigger_rule=other_profile.trigger_rule,
        evaluation_timestamp=_iso_add(close_at, maximum),
    )
    assert result.maximum_trigger_age_seconds == maximum
    assert result.mode_matches is False
    assert result.trigger_timeframe_matches is False
    assert result.trigger_rule_matches is False
    assert result.reason_code == "HOLD_TRIGGER_MODE_MISMATCH"


def test_complete_reason_priority_chain():
    base = _values(_geometry())
    cases = [
        ({"mode": "INTRADAY", "mode_lineage_sha256": "0" * 64}, "HOLD_TRIGGER_MODE_MISMATCH"),
        ({"mode_lineage_sha256": "0" * 64, "canonical_symbol": "ETH/USDT:USDT"}, "HOLD_TRIGGER_MODE_LINEAGE_MISMATCH"),
        ({"canonical_symbol": "ETH/USDT:USDT", "side": "SHORT"}, "HOLD_TRIGGER_SYMBOL_MISMATCH"),
        ({"side": "SHORT", "structure_timeframe": "15m"}, "HOLD_TRIGGER_SIDE_MISMATCH"),
        ({"structure_timeframe": "15m", "structure_generation_id": "structure:g2"}, "HOLD_TRIGGER_STRUCTURE_TIMEFRAME_MISMATCH"),
        ({"structure_generation_id": "structure:g2", "trigger_timeframe": "5m"}, "HOLD_TRIGGER_STRUCTURE_GENERATION_MISMATCH"),
        ({"trigger_timeframe": "5m", "trigger_rule": "altered valid trigger rule"}, "HOLD_TRIGGER_TIMEFRAME_MISMATCH"),
        ({"trigger_rule": "altered valid trigger rule", "trigger_candle_closed": False}, "HOLD_TRIGGER_RULE_MISMATCH"),
        ({"trigger_candle_closed": False, "trigger_rule_satisfied": False}, "HOLD_TRIGGER_CANDLE_UNCLOSED"),
    ]
    for overrides, reason in cases:
        values = dict(base)
        values.update(overrides)
        assert build_e3_mode_trigger_evidence(**values).reason_code == reason
    off_grid = "2026-07-30T00:16:00Z"
    unconfirmed = dict(base, trigger_rule_satisfied=False, trigger_candle_close_at=off_grid, evaluation_timestamp=off_grid)
    assert build_e3_mode_trigger_evidence(**unconfirmed).reason_code == "HOLD_TRIGGER_RULE_UNCONFIRMED"
    future = dict(base, trigger_candle_close_at=off_grid, evaluation_timestamp="2026-07-30T00:15:59Z")
    assert build_e3_mode_trigger_evidence(**future).reason_code == "HOLD_TRIGGER_CLOSE_MISALIGNED"
    negative = dict(base, evaluation_timestamp="2026-07-30T00:14:59Z")
    negative_result = build_e3_mode_trigger_evidence(**negative)
    assert negative_result.reason_code == "HOLD_TRIGGER_FUTURE"
    assert negative_result.trigger_fresh is False


def test_trigger_generation_id_format_and_deterministic_replay():
    first = _evidence()
    second = _evidence()
    assert first.to_mapping() == second.to_mapping()
    assert re.fullmatch(r"trg-[0-9a-f]{64}", first.trigger_generation_id)
    assert first.trigger_generation_id == second.trigger_generation_id
    assert first.trigger_evidence_sha256 == second.trigger_evidence_sha256


def test_trigger_generation_id_identity_sensitivity():
    base = _evidence()
    identity_changes = (
        {"mode": "INTRADAY"},
        {"mode_lineage_sha256": "0" * 64},
        {"canonical_symbol": "ETH/USDT:USDT"},
        {"side": "SHORT"},
        {"structure_timeframe": "15m"},
        {"structure_generation_id": "structure:g2"},
        {"trigger_timeframe": "5m"},
        {"trigger_rule": "altered valid trigger rule"},
        {"trigger_candle_close_at": "2026-07-30T00:30:00Z", "evaluation_timestamp": "2026-07-30T00:30:00Z"},
    )
    for changes in identity_changes:
        assert _evidence(**changes).trigger_generation_id != base.trigger_generation_id
    changed_geometry = _geometry(anchor_low_tick=900)
    assert _evidence(changed_geometry).trigger_generation_id != base.trigger_generation_id


def test_generation_id_excludes_evaluation_and_gate_results():
    base = _evidence()
    variants = (
        _evidence(evaluation_timestamp="2026-07-30T00:15:01Z"),
        _evidence(trigger_candle_closed=False),
        _evidence(trigger_rule_satisfied=False),
    )
    for variant in variants:
        assert variant.trigger_generation_id == base.trigger_generation_id
        assert variant.trigger_evidence_sha256 != base.trigger_evidence_sha256


def test_geometry_subclass_lookalike_and_corruption_are_sanitized():
    geometry = _geometry()
    subclass = GeometrySubclass(**_constructor_geometry_values(geometry))
    _assert_sanitized(lambda: _evidence(subclass))
    _assert_sanitized(lambda: build_e3_mode_trigger_evidence(**dict(_values(geometry), geometry=GeometryLookalike())))
    corrupt = object.__new__(E3GoldenZoneGeometryV1)
    for field in fields(E3GoldenZoneGeometryV1):
        object.__setattr__(corrupt, field.name, getattr(geometry, field.name))
    object.__setattr__(corrupt, "geometry_sha256", "0" * 64)
    _assert_sanitized(lambda: _evidence(corrupt))


def _constructor_geometry_values(geometry):
    mapping = geometry.to_mapping()
    return mapping


def test_profile_type_and_policy_corruption_are_sanitized(monkeypatch):
    monkeypatch.setattr(trigger_module, "get_mode_profile", lambda mode: object())
    _assert_sanitized(lambda: _evidence())


def test_profile_policy_constant_mismatch_is_sanitized(monkeypatch):
    monkeypatch.setattr(trigger_module, "MODE_PROFILE_POLICY_VERSION", "wrong-policy")
    _assert_sanitized(lambda: _evidence())


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("mode", "swing"),
        ("mode", StringSubclass("SWING")),
        ("mode_lineage_sha256", "A" * 64),
        ("mode_lineage_sha256", StringSubclass("0" * 64)),
        ("canonical_symbol", "bad symbol"),
        ("side", "BUY"),
        ("structure_timeframe", "2m"),
        ("structure_generation_id", "bad/id"),
        ("trigger_timeframe", "2m"),
        ("trigger_rule", " altered "),
        ("evaluation_timestamp", "2026-07-30T00:15:00+00:00"),
    ),
)
def test_malformed_primitives_fail_closed(field, value):
    _assert_sanitized(lambda: _evidence(**{field: value}))


def test_direct_constructor_round_trip_retains_geometry_identity():
    result = _evidence()
    rebuilt = E3ModeTriggerEvidenceV1(**_constructor_values(result))
    assert rebuilt == result
    assert rebuilt.geometry is result.geometry


def test_direct_constructor_rejects_every_field_corruption():
    result = _evidence()
    base = _constructor_values(result)
    other_geometry = _geometry(anchor_low_tick=900)
    corruptions = {
        "schema_version": "bad-schema",
        "policy_version": "bad-policy",
        "trigger_generation_policy_version": "bad-generation-policy",
        "geometry": other_geometry,
        "mode_profile_policy_version": "bad-profile-policy",
        "mode": "INTRADAY",
        "mode_lineage_sha256": "0" * 64,
        "canonical_symbol": "ETH/USDT:USDT",
        "side": "SHORT",
        "structure_timeframe": "15m",
        "structure_generation_id": "structure:g2",
        "trigger_timeframe": "5m",
        "trigger_rule": "altered valid trigger rule",
        "trigger_candle_close_at": "2026-07-30T00:30:00Z",
        "trigger_candle_closed": False,
        "trigger_rule_satisfied": False,
        "evaluation_timestamp": "2026-07-30T00:15:01Z",
        "trigger_age_seconds": 1,
        "maximum_trigger_age_seconds": 901,
        "mode_matches": False,
        "mode_lineage_matches": False,
        "symbol_matches": False,
        "side_matches": False,
        "structure_timeframe_matches": False,
        "structure_generation_matches": False,
        "trigger_timeframe_matches": False,
        "trigger_rule_matches": False,
        "trigger_close_aligned": False,
        "trigger_not_future": False,
        "trigger_fresh": False,
        "decision": "HOLD_TRIGGER_EVIDENCE",
        "reason_code": "HOLD_TRIGGER_STALE",
        "trigger_generation_id": "trg-" + "0" * 64,
        "trigger_evidence_sha256": "0" * 64,
    }
    assert set(corruptions) == set(FIELD_NAMES)
    for field, value in corruptions.items():
        changed = dict(base)
        changed[field] = value
        _assert_sanitized(lambda changed=changed: E3ModeTriggerEvidenceV1(**changed))


def test_direct_constructor_rejects_primitive_subclasses():
    result = _evidence()
    for field, value in (
        ("mode", StringSubclass(result.mode)),
        ("trigger_age_seconds", IntegerSubclass(result.trigger_age_seconds)),
        ("mode_matches", 1),
    ):
        changed = _constructor_values(result)
        changed[field] = value
        _assert_sanitized(lambda changed=changed: E3ModeTriggerEvidenceV1(**changed))


def test_mapping_is_detached_and_hash_covers_every_content_field():
    result = _evidence()
    mapping = result.to_mapping()
    mapping["mode"] = "SCALP"
    mapping["geometry"]["canonical_symbol"] = "ETH/USDT:USDT"
    assert result.mode == "SWING"
    assert result.geometry.canonical_symbol == "BTC/USDT:USDT"
    canonical = result.to_mapping()
    stored_hash = canonical.pop("trigger_evidence_sha256")
    assert hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest() == stored_hash
    for field in canonical:
        altered = result.to_mapping()
        altered.pop("trigger_evidence_sha256")
        if field == "geometry":
            altered[field]["anchor_low_tick"] -= 1
        elif isinstance(altered[field], bool):
            altered[field] = not altered[field]
        elif isinstance(altered[field], int):
            altered[field] += 1
        else:
            altered[field] = str(altered[field]) + "x"
        changed_hash = hashlib.sha256(
            json.dumps(altered, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
        ).hexdigest()
        assert changed_hash != stored_hash


def test_typed_hold_has_no_later_slice_or_production_fields():
    held = _evidence(mode="INTRADAY")
    assert isinstance(held, E3ModeTriggerEvidenceV1)
    assert held.decision == "HOLD_TRIGGER_EVIDENCE"
    forbidden = {"telegram", "publication", "slot", "pair_lock", "lifecycle", "target", "provider", "order", "trading"}
    assert not forbidden.intersection(held.to_mapping())


def _project_imports(tree):
    result = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("engine."):
            result.append((node.module, tuple(alias.name for alias in node.names)))
    return result


def _dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def test_mode_lineage_and_profile_authority_static_contract():
    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert _project_imports(tree) == [
        ("engine.e3_golden_zone_geometry_v1", ("E3GoldenZoneGeometryV1",)),
        ("engine.mode_profile_v1", ("MODE_PROFILE_POLICY_VERSION", "ModeProfileV1", "get_mode_profile")),
    ]
    assert "get_mode_profile(geometry.mode)" in source
    for attribute in (
        "profile.structure_timeframe",
        "profile.trigger_timeframe",
        "profile.trigger_rule",
        "profile.maximum_trigger_age_seconds",
        "profile.trigger_candle_closed_only is True",
        "profile.developing_candle_allowed is False",
        "geometry.mode_lineage_sha256",
    ):
        assert attribute in source
    for mode, trigger, age in (("SWING", "15m", 900), ("INTRADAY", "5m", 300), ("SCALP", "3m", 180)):
        assert f'if mode == "{mode}"' in source
        assert f'"{trigger}"' in source
        assert str(age) in source
    builder = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_e3_mode_trigger_evidence")
    assert "SWING" not in ast.get_source_segment(source, builder)


def test_trigger_generation_identity_exact_static_contract():
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_trigger_generation_id")
    dictionaries = [node for node in ast.walk(function) if isinstance(node, ast.Dict)]
    assert len(dictionaries) == 1
    keys = tuple(key.value for key in dictionaries[0].keys)
    assert keys == (
        "trigger_generation_policy_version",
        "geometry_sha256",
        "mode_profile_policy_version",
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "side",
        "structure_timeframe",
        "structure_generation_id",
        "trigger_timeframe",
        "trigger_rule",
        "trigger_candle_close_at",
    )
    forbidden = {"evaluation_timestamp", "trigger_age_seconds", "trigger_candle_closed", "trigger_rule_satisfied", "decision", "reason_code", "signal_id", "publication", "score", "uuid", "random"}
    assert not forbidden.intersection(keys)


def test_forbidden_surface_static_contract_and_qualified_calls():
    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots == {"dataclasses", "datetime", "hashlib", "json", "re", "typing", "engine"}
    forbidden = {"ccxt", "requests", "httpx", "aiohttp", "urllib", "socket", "subprocess", "pathlib", "os", "time", "asyncio", "threading", "multiprocessing", "decimal", "fractions"}
    assert not forbidden.intersection(imported_roots)
    calls = {_dotted(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    assert not {"datetime.now", "datetime.utcnow", "date.today", "float", "sorted", "filter", "min", "max"}.intersection(calls)
    assert not any(
        isinstance(node, ast.Constant)
        and type(node.value) is float
        for node in ast.walk(tree)
    )
    assert not any(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) for node in ast.walk(tree))
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom)) for node in ast.walk(tree))
    assert ".total_seconds(" not in source
    assert "retry" not in source.lower()
    assert "backoff" not in source.lower()


def test_exact_two_file_authorized_mutation_inventory():
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "?? engine/e3_mode_trigger_evidence_v1.py",
        "?? tests/test_e3_mode_trigger_evidence_v1.py",
    ]


def test_no_committed_production_reference():
    result = subprocess.run(
        ["git", "grep", "-n", "e3_mode_trigger_evidence_v1", "HEAD", "--", "."],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == ""


def test_no_skip_xfail_todo_or_weakened_expectations():
    source = TEST_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    todo_marker = "TO" + "DO"
    assert todo_marker not in source
    type_ignore_marker = "# type:" + " ignore"
    assert type_ignore_marker not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            assert _dotted(node.func) not in {"pytest.skip", "pytest.xfail"}
        if isinstance(node, ast.Attribute):
            assert _dotted(node) not in {"pytest.mark.skip", "pytest.mark.skipif", "pytest.mark.xfail"}
    assert ERROR in source
    assert "PASS_TRIGGER_EVIDENCE" in source
    assert "HOLD_TRIGGER_EVIDENCE" in source
