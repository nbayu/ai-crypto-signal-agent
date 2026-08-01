from dataclasses import FrozenInstanceError, fields, replace
import ast
from hashlib import sha256
import inspect
import json
from pathlib import Path
import subprocess

import pytest

from engine.e3_executable_price_snapshot_v1 import (
    E3ExecutablePriceSnapshotV1,
    build_e3_executable_price_snapshot,
)
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
    build_e3_golden_zone_geometry,
)
from engine.e3_price_zone_admission_v1 import (
    DECISION_HOLD,
    DECISION_PASS,
    EXECUTABLE_SOURCE_BEST_ASK,
    EXECUTABLE_SOURCE_BEST_BID,
    INTRADAY_MAX_QUOTE_AGE_SECONDS,
    INTRADAY_MAX_SLIPPAGE_BPS,
    INTRADAY_MAX_SPREAD_BPS,
    POLICY_VERSION,
    REASON_OUTSIDE_ZONE,
    REASON_PASS,
    REASON_SLIPPAGE,
    REASON_SPREAD,
    REASON_STALE,
    SCALP_MAX_QUOTE_AGE_SECONDS,
    SCALP_MAX_SLIPPAGE_BPS,
    SCALP_MAX_SPREAD_BPS,
    SCHEMA_VERSION,
    SWING_MAX_QUOTE_AGE_SECONDS,
    SWING_MAX_SLIPPAGE_BPS,
    SWING_MAX_SPREAD_BPS,
    ZONE_BOUNDARY_TOLERANCE_TICKS,
    E3PriceZoneAdmissionV1,
    build_e3_price_zone_admission,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage


ENGINE_PATH = Path("engine/e3_price_zone_admission_v1.py")
TEST_PATH = Path("tests/test_e3_price_zone_admission_v1.py")
FIELD_NAMES = [
    "schema_version",
    "policy_version",
    "geometry",
    "snapshot",
    "evaluation_timestamp",
    "executable_price_source",
    "executable_price_tick",
    "quote_age_seconds",
    "spread_bps_numerator",
    "spread_bps_denominator",
    "modeled_adverse_slippage_bps",
    "max_quote_age_seconds",
    "max_spread_bps",
    "max_slippage_bps",
    "zone_low_tick",
    "zone_high_tick",
    "zone_boundary_tolerance_ticks",
    "age_within_limit",
    "spread_within_limit",
    "slippage_within_limit",
    "inside_zone",
    "decision",
    "reason_code",
    "admission_sha256",
]
MODE_LIMITS = {
    "SWING": (15, 20, 10),
    "INTRADAY": (10, 12, 6),
    "SCALP": (3, 6, 3),
}


class StringSubclass(str):
    pass


class IntegerSubclass(int):
    pass


class BoolSubclass(int):
    pass


class GeometrySubclass(E3GoldenZoneGeometryV1):
    pass


class SnapshotSubclass(E3ExecutablePriceSnapshotV1):
    pass


class Lookalike:
    pass


def _geometry(
    *,
    mode="SWING",
    side="LONG",
    generation="structure:g1",
    symbol="BTC/USDT:USDT",
    anchor_low_tick=None,
    anchor_high_tick=None,
):
    if anchor_low_tick is None:
        anchor_low_tick = 9000 if side == "LONG" else 8000
    if anchor_high_tick is None:
        anchor_high_tick = 12000 if side == "LONG" else 11000
    if side == "LONG":
        low_at = "2026-07-30T00:00:00Z"
        high_at = "2026-07-30T01:00:00Z"
    else:
        low_at = "2026-07-30T01:00:00Z"
        high_at = "2026-07-30T00:00:00Z"
    return build_e3_golden_zone_geometry(
        mode=mode,
        mode_lineage_sha256=(
            build_mode_audit_lineage(mode).lineage_sha256
        ),
        canonical_symbol=symbol,
        side=side,
        structure_generation_id=generation,
        anchor_low_at=low_at,
        anchor_low_tick=anchor_low_tick,
        anchor_high_at=high_at,
        anchor_high_tick=anchor_high_tick,
        tick_size="1",
    )


def _snapshot(geometry, **overrides):
    values = {
        "geometry": geometry,
        "venue": "BINANCE_USDM",
        "quote_generation_id": "quote:g1",
        "exchange_timestamp": "2026-07-30T00:00:00Z",
        "best_bid_tick": 10000,
        "best_ask_tick": 10002,
        "last_price_tick": 10001,
        "mark_price_tick": 10001,
        "modeled_adverse_slippage_bps": 0,
        "tick_size": geometry.tick_size,
    }
    values.update(overrides)
    return build_e3_executable_price_snapshot(**values)


def _admission(
    geometry=None,
    snapshot=None,
    evaluation_timestamp="2026-07-30T00:00:00Z",
):
    selected_geometry = geometry or _geometry()
    selected_snapshot = snapshot or _snapshot(
        selected_geometry
    )
    return build_e3_price_zone_admission(
        geometry=selected_geometry,
        snapshot=selected_snapshot,
        evaluation_timestamp=evaluation_timestamp,
    )


def _constructor_mapping(result):
    mapping = result.to_mapping()
    mapping["geometry"] = result.geometry
    mapping["snapshot"] = result.snapshot
    return mapping


def _canonical_hash(mapping):
    return sha256(
        json.dumps(
            mapping,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _assert_sanitized(call):
    with pytest.raises(
        ValueError,
        match=r"^invalid E3 price-zone admission$",
    ) as caught:
        call()
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def _spread_case(mode, relation):
    values = {
        "SWING": (1700, 2700, 1998, 2002),
        "INTRADAY": (4700, 5700, 4997, 5003),
        "SCALP": (9700, 10700, 9997, 10003),
    }
    low, high, bid, ask = values[mode]
    if relation == "below":
        bid += 1
        ask -= 1
    elif relation == "above":
        bid -= 1
        ask += 1
    geometry = _geometry(
        mode=mode,
        anchor_low_tick=low,
        anchor_high_tick=high,
    )
    snapshot = _snapshot(
        geometry,
        best_bid_tick=bid,
        best_ask_tick=ask,
        last_price_tick=ask,
        mark_price_tick=ask,
    )
    return geometry, snapshot


def test_exact_public_exports():
    import engine.e3_price_zone_admission_v1 as module

    assert module.__all__ == (
        "E3PriceZoneAdmissionV1",
        "build_e3_price_zone_admission",
    )


def test_exact_defined_public_inventory():
    import engine.e3_price_zone_admission_v1 as module

    public = [
        name
        for name, value in vars(module).items()
        if not name.startswith("_")
        and (inspect.isclass(value) or inspect.isfunction(value))
        and getattr(value, "__module__", None) == module.__name__
    ]
    assert public == [
        "E3PriceZoneAdmissionV1",
        "build_e3_price_zone_admission",
    ]


def test_exact_dataclass_fields_and_annotations():
    assert [
        field.name
        for field in fields(E3PriceZoneAdmissionV1)
    ] == FIELD_NAMES
    assert list(E3PriceZoneAdmissionV1.__annotations__) == (
        FIELD_NAMES
    )
    assert E3PriceZoneAdmissionV1.__annotations__["geometry"] is (
        E3GoldenZoneGeometryV1
    )
    assert E3PriceZoneAdmissionV1.__annotations__["snapshot"] is (
        E3ExecutablePriceSnapshotV1
    )


def test_result_is_frozen_slotted_without_dict():
    result = _admission()
    assert tuple(result.__slots__) == tuple(FIELD_NAMES)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.decision = "OTHER"


def test_exact_one_public_method():
    public = [
        name
        for name, value in vars(E3PriceZoneAdmissionV1).items()
        if not name.startswith("_") and inspect.isfunction(value)
    ]
    assert public == ["to_mapping"]


def test_exact_builder_signature_and_return():
    signature = inspect.signature(
        build_e3_price_zone_admission
    )
    assert list(signature.parameters) == [
        "geometry",
        "snapshot",
        "evaluation_timestamp",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert signature.return_annotation is E3PriceZoneAdmissionV1


def test_exact_policy_decision_reason_and_source_constants():
    assert SCHEMA_VERSION == "e3-price-zone-admission-v1"
    assert (
        POLICY_VERSION
        == "d3-fresh-executable-side-price-admission-v1"
    )
    assert DECISION_PASS == "PASS_PRICE_ADMISSION"
    assert DECISION_HOLD == "HOLD_PRICE_ADMISSION"
    assert REASON_PASS == "PASS_PRICE_ADMISSION"
    assert REASON_STALE == "HOLD_PRICE_STALE"
    assert REASON_SPREAD == "HOLD_PRICE_SPREAD"
    assert REASON_SLIPPAGE == "HOLD_PRICE_SLIPPAGE"
    assert REASON_OUTSIDE_ZONE == "HOLD_PRICE_OUTSIDE_ZONE"
    assert EXECUTABLE_SOURCE_BEST_ASK == "BEST_ASK"
    assert EXECUTABLE_SOURCE_BEST_BID == "BEST_BID"
    assert ZONE_BOUNDARY_TOLERANCE_TICKS == 0


def test_exact_mode_limit_constants():
    assert (
        SWING_MAX_QUOTE_AGE_SECONDS,
        SWING_MAX_SPREAD_BPS,
        SWING_MAX_SLIPPAGE_BPS,
    ) == (15, 20, 10)
    assert (
        INTRADAY_MAX_QUOTE_AGE_SECONDS,
        INTRADAY_MAX_SPREAD_BPS,
        INTRADAY_MAX_SLIPPAGE_BPS,
    ) == (10, 12, 6)
    assert (
        SCALP_MAX_QUOTE_AGE_SECONDS,
        SCALP_MAX_SPREAD_BPS,
        SCALP_MAX_SLIPPAGE_BPS,
    ) == (3, 6, 3)


def test_mapping_key_order_and_nested_serialization():
    result = _admission()
    mapping = result.to_mapping()
    assert list(mapping) == FIELD_NAMES
    assert mapping["geometry"] == result.geometry.to_mapping()
    assert mapping["snapshot"] == result.snapshot.to_mapping()
    assert type(mapping["geometry"]) is dict
    assert type(mapping["snapshot"]) is dict


def test_exact_geometry_and_snapshot_identity_retained():
    geometry = _geometry()
    snapshot = _snapshot(geometry)
    result = _admission(geometry, snapshot)
    assert result.geometry is geometry
    assert result.snapshot is snapshot
    assert result.snapshot.geometry is result.geometry


@pytest.mark.parametrize(
    "invalid",
    [Lookalike(), None, {}, "object"],
)
def test_geometry_and_snapshot_lookalikes_rejected(invalid):
    geometry = _geometry()
    snapshot = _snapshot(geometry)
    _assert_sanitized(
        lambda: build_e3_price_zone_admission(
            geometry=invalid,
            snapshot=snapshot,
            evaluation_timestamp="2026-07-30T00:00:00Z",
        )
    )
    _assert_sanitized(
        lambda: build_e3_price_zone_admission(
            geometry=geometry,
            snapshot=invalid,
            evaluation_timestamp="2026-07-30T00:00:00Z",
        )
    )


def test_geometry_and_snapshot_subclasses_rejected():
    geometry = _geometry()
    snapshot = _snapshot(geometry)
    geometry_subclass = GeometrySubclass(
        **geometry.to_mapping()
    )
    snapshot_mapping = snapshot.to_mapping()
    snapshot_mapping["geometry"] = geometry
    snapshot_subclass = SnapshotSubclass(**snapshot_mapping)
    _assert_sanitized(
        lambda: _admission(geometry_subclass, snapshot)
    )
    _assert_sanitized(
        lambda: _admission(geometry, snapshot_subclass)
    )


def test_mismatched_geometry_identity_is_rejected():
    geometry = _geometry()
    equal_but_distinct = _geometry()
    snapshot = _snapshot(geometry)
    assert equal_but_distinct == geometry
    assert equal_but_distinct is not geometry
    _assert_sanitized(
        lambda: _admission(equal_but_distinct, snapshot)
    )


@pytest.mark.parametrize(
    "side,source,price",
    [
        ("LONG", "BEST_ASK", 10002),
        ("SHORT", "BEST_BID", 10000),
    ],
)
def test_best_side_execution_is_exact(side, source, price):
    geometry = _geometry(side=side)
    result = _admission(geometry)
    assert result.executable_price_source == source
    assert result.executable_price_tick == price


@pytest.mark.parametrize("field", ["last_price_tick", "mark_price_tick"])
def test_last_and_mark_never_replace_executable_side(field):
    geometry = _geometry()
    baseline = _snapshot(geometry)
    changed = _snapshot(geometry, **{field: 1})
    baseline_result = _admission(geometry, baseline)
    changed_result = _admission(geometry, changed)
    assert changed.snapshot_sha256 != baseline.snapshot_sha256
    assert changed_result.executable_price_tick == (
        baseline_result.executable_price_tick
    )


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
def test_mode_limits_come_from_geometry(mode):
    geometry = _geometry(mode=mode)
    result = _admission(geometry)
    assert (
        result.max_quote_age_seconds,
        result.max_spread_bps,
        result.max_slippage_bps,
    ) == MODE_LIMITS[mode]


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_age_limit_boundaries(mode, offset):
    limit = MODE_LIMITS[mode][0]
    age = limit + offset
    geometry = _geometry(mode=mode)
    result = _admission(
        geometry,
        evaluation_timestamp=(
            f"2026-07-30T00:00:{age:02d}Z"
        ),
    )
    assert result.quote_age_seconds == age
    assert result.age_within_limit is (age <= limit)
    assert result.reason_code == (
        REASON_PASS if age <= limit else REASON_STALE
    )


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
def test_zero_quote_age_passes(mode):
    result = _admission(_geometry(mode=mode))
    assert result.quote_age_seconds == 0
    assert result.age_within_limit is True


def test_future_quote_relative_to_evaluation_fails_closed():
    geometry = _geometry()
    snapshot = _snapshot(
        geometry,
        exchange_timestamp="2026-07-30T00:00:01Z",
    )
    _assert_sanitized(
        lambda: _admission(
            geometry,
            snapshot,
            "2026-07-30T00:00:00Z",
        )
    )


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-07-30T00:00:00.0Z",
        "2026-07-30T00:00:00+00:00",
        "2026-07-30T00:00:00z",
        " 2026-07-30T00:00:00Z",
        "2026-02-30T00:00:00Z",
        StringSubclass("2026-07-30T00:00:00Z"),
        None,
    ],
)
def test_invalid_evaluation_timestamp_rejected(timestamp):
    _assert_sanitized(
        lambda: _admission(
            evaluation_timestamp=timestamp
        )
    )


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
@pytest.mark.parametrize("relation", ["below", "equal", "above"])
def test_exact_rational_spread_boundaries(mode, relation):
    geometry, snapshot = _spread_case(mode, relation)
    result = _admission(geometry, snapshot)
    limit = MODE_LIMITS[mode][1]
    expected_within = relation != "above"
    assert result.spread_bps_numerator == (
        snapshot.best_ask_tick - snapshot.best_bid_tick
    ) * 20000
    assert result.spread_bps_denominator == (
        snapshot.best_ask_tick + snapshot.best_bid_tick
    )
    if relation == "equal":
        assert result.spread_bps_numerator == (
            limit * result.spread_bps_denominator
        )
    assert result.spread_within_limit is expected_within
    assert result.reason_code == (
        REASON_PASS if expected_within else REASON_SPREAD
    )


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_slippage_limit_boundaries(mode, offset):
    limit = MODE_LIMITS[mode][2]
    geometry = _geometry(mode=mode)
    snapshot = _snapshot(
        geometry,
        modeled_adverse_slippage_bps=limit + offset,
    )
    result = _admission(geometry, snapshot)
    expected_within = offset <= 0
    assert result.slippage_within_limit is expected_within
    assert result.reason_code == (
        REASON_PASS
        if expected_within
        else REASON_SLIPPAGE
    )


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
@pytest.mark.parametrize(
    "position",
    ["lower", "upper", "inside", "below", "above"],
)
def test_inclusive_zero_tolerance_zone_boundaries(side, position):
    geometry = _geometry(side=side)
    if position == "lower":
        executable = geometry.golden_zone_low_tick
    elif position == "upper":
        executable = geometry.golden_zone_high_tick
    elif position == "inside":
        executable = (
            geometry.golden_zone_low_tick
            + geometry.golden_zone_high_tick
        ) // 2
    elif position == "below":
        executable = geometry.golden_zone_low_tick - 1
    else:
        executable = geometry.golden_zone_high_tick + 1
    if side == "LONG":
        snapshot = _snapshot(
            geometry,
            best_bid_tick=executable - 1,
            best_ask_tick=executable,
            last_price_tick=1,
            mark_price_tick=1,
        )
    else:
        snapshot = _snapshot(
            geometry,
            best_bid_tick=executable,
            best_ask_tick=executable + 1,
            last_price_tick=1,
            mark_price_tick=1,
        )
    result = _admission(geometry, snapshot)
    expected_inside = position in ("lower", "upper", "inside")
    assert result.inside_zone is expected_inside
    assert result.zone_boundary_tolerance_ticks == 0
    assert result.reason_code == (
        REASON_PASS
        if expected_inside
        else REASON_OUTSIDE_ZONE
    )


def test_stale_reason_precedes_spread():
    geometry, snapshot = _spread_case("SWING", "above")
    result = _admission(
        geometry,
        snapshot,
        "2026-07-30T00:00:16Z",
    )
    assert result.age_within_limit is False
    assert result.spread_within_limit is False
    assert result.reason_code == REASON_STALE


def test_spread_reason_precedes_slippage():
    geometry, baseline = _spread_case("SWING", "above")
    snapshot = _snapshot(
        geometry,
        best_bid_tick=baseline.best_bid_tick,
        best_ask_tick=baseline.best_ask_tick,
        last_price_tick=baseline.last_price_tick,
        mark_price_tick=baseline.mark_price_tick,
        modeled_adverse_slippage_bps=11,
    )
    result = _admission(geometry, snapshot)
    assert result.spread_within_limit is False
    assert result.slippage_within_limit is False
    assert result.reason_code == REASON_SPREAD


def test_slippage_reason_precedes_outside_zone():
    geometry = _geometry()
    executable = geometry.golden_zone_high_tick + 1
    snapshot = _snapshot(
        geometry,
        best_bid_tick=executable - 1,
        best_ask_tick=executable,
        last_price_tick=1,
        mark_price_tick=1,
        modeled_adverse_slippage_bps=11,
    )
    result = _admission(geometry, snapshot)
    assert result.slippage_within_limit is False
    assert result.inside_zone is False
    assert result.reason_code == REASON_SLIPPAGE


@pytest.mark.parametrize(
    "reason",
    [
        REASON_STALE,
        REASON_SPREAD,
        REASON_SLIPPAGE,
        REASON_OUTSIDE_ZONE,
    ],
)
def test_gate_failures_return_typed_immutable_hold(reason):
    geometry = _geometry()
    if reason == REASON_STALE:
        result = _admission(
            geometry,
            evaluation_timestamp="2026-07-30T00:00:16Z",
        )
    elif reason == REASON_SPREAD:
        geometry, snapshot = _spread_case(
            "SWING",
            "above",
        )
        result = _admission(geometry, snapshot)
    elif reason == REASON_SLIPPAGE:
        snapshot = _snapshot(
            geometry,
            modeled_adverse_slippage_bps=11,
        )
        result = _admission(geometry, snapshot)
    else:
        executable = geometry.golden_zone_high_tick + 1
        snapshot = _snapshot(
            geometry,
            best_bid_tick=executable - 1,
            best_ask_tick=executable,
        )
        result = _admission(geometry, snapshot)
    assert type(result) is E3PriceZoneAdmissionV1
    assert result.decision == DECISION_HOLD
    assert result.reason_code == reason


def test_pass_requires_all_four_gates():
    result = _admission()
    assert (
        result.age_within_limit,
        result.spread_within_limit,
        result.slippage_within_limit,
        result.inside_zone,
    ) == (True, True, True, True)
    assert result.decision == DECISION_PASS
    assert result.reason_code == REASON_PASS


def test_result_has_no_later_slice_or_side_effect_fields():
    forbidden = {
        "telegram_send",
        "slot_change",
        "pair_lock_change",
        "publication",
        "trigger",
        "lifecycle",
        "target",
        "order",
    }
    assert forbidden.isdisjoint(FIELD_NAMES)


def test_deterministic_replay_and_layer_hash():
    geometry = _geometry()
    snapshot = _snapshot(geometry)
    first = _admission(geometry, snapshot)
    second = _admission(geometry, snapshot)
    assert first.to_mapping() == second.to_mapping()
    mapping = first.to_mapping()
    supplied = mapping.pop("admission_sha256")
    assert mapping["geometry"]["geometry_sha256"] == (
        geometry.geometry_sha256
    )
    assert mapping["snapshot"]["snapshot_sha256"] == (
        snapshot.snapshot_sha256
    )
    assert supplied == _canonical_hash(mapping)


def test_mapping_is_detached():
    result = _admission()
    mapping = result.to_mapping()
    mapping["geometry"]["mode"] = "BROKEN"
    mapping["snapshot"]["venue"] = "BROKEN"
    mapping["decision"] = "BROKEN"
    fresh = result.to_mapping()
    assert fresh["geometry"]["mode"] == "SWING"
    assert fresh["snapshot"]["venue"] == "BINANCE_USDM"
    assert fresh["decision"] == DECISION_PASS


def test_round_trip_with_original_layer_objects():
    result = _admission()
    reconstructed = E3PriceZoneAdmissionV1(
        **_constructor_mapping(result)
    )
    assert reconstructed == result
    assert reconstructed.geometry is result.geometry
    assert reconstructed.snapshot is result.snapshot


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "other"),
        ("policy_version", "other"),
        ("evaluation_timestamp", "2026-07-30T00:00:01Z"),
        ("executable_price_source", "BEST_BID"),
        ("executable_price_tick", 10001),
        ("quote_age_seconds", 1),
        ("spread_bps_numerator", 39999),
        ("spread_bps_denominator", 20001),
        ("modeled_adverse_slippage_bps", 1),
        ("max_quote_age_seconds", 14),
        ("max_spread_bps", 19),
        ("max_slippage_bps", 9),
        ("zone_low_tick", 9643),
        ("zone_high_tick", 10145),
        ("zone_boundary_tolerance_ticks", 1),
        ("age_within_limit", False),
        ("spread_within_limit", False),
        ("slippage_within_limit", False),
        ("inside_zone", False),
        ("decision", DECISION_HOLD),
        ("reason_code", REASON_STALE),
        ("admission_sha256", "0" * 64),
    ],
)
def test_direct_constructor_corruption_rejected(field, value):
    result = _admission()
    _assert_sanitized(
        lambda: replace(result, **{field: value})
    )


def test_direct_constructor_layer_replacement_rejected():
    result = _admission()
    other_geometry = _geometry(generation="structure:g2")
    other_snapshot = _snapshot(other_geometry)
    _assert_sanitized(
        lambda: replace(result, geometry=other_geometry)
    )
    _assert_sanitized(
        lambda: replace(result, snapshot=other_snapshot)
    )


@pytest.mark.parametrize(
    "field,value",
    [
        (
            "evaluation_timestamp",
            StringSubclass("2026-07-30T00:00:00Z"),
        ),
        (
            "executable_price_source",
            StringSubclass("BEST_ASK"),
        ),
        ("executable_price_tick", IntegerSubclass(10002)),
        ("quote_age_seconds", IntegerSubclass(0)),
        ("spread_bps_numerator", IntegerSubclass(40000)),
        ("spread_bps_denominator", IntegerSubclass(20002)),
        (
            "modeled_adverse_slippage_bps",
            IntegerSubclass(0),
        ),
        ("max_quote_age_seconds", IntegerSubclass(15)),
        ("max_spread_bps", IntegerSubclass(20)),
        ("max_slippage_bps", IntegerSubclass(10)),
        ("zone_low_tick", IntegerSubclass(9642)),
        ("zone_high_tick", IntegerSubclass(10146)),
        (
            "zone_boundary_tolerance_ticks",
            IntegerSubclass(0),
        ),
        ("age_within_limit", BoolSubclass(1)),
        ("spread_within_limit", BoolSubclass(1)),
        ("slippage_within_limit", BoolSubclass(1)),
        ("inside_zone", BoolSubclass(1)),
        ("decision", StringSubclass(DECISION_PASS)),
        ("reason_code", StringSubclass(REASON_PASS)),
        ("admission_sha256", StringSubclass("0" * 64)),
    ],
)
def test_direct_constructor_primitive_subclasses_rejected(
    field,
    value,
):
    result = _admission()
    mapping = _constructor_mapping(result)
    mapping[field] = value
    if field != "admission_sha256":
        hash_mapping = dict(mapping)
        hash_mapping["geometry"] = (
            result.geometry.to_mapping()
        )
        hash_mapping["snapshot"] = (
            result.snapshot.to_mapping()
        )
        hash_mapping.pop("admission_sha256")
        mapping["admission_sha256"] = _canonical_hash(
            hash_mapping
        )
    _assert_sanitized(
        lambda: E3PriceZoneAdmissionV1(**mapping)
    )


@pytest.mark.parametrize(
    "field",
    [
        "geometry",
        "snapshot",
        "evaluation_timestamp",
        "executable_price_source",
        "executable_price_tick",
        "quote_age_seconds",
        "spread_bps_numerator",
        "spread_bps_denominator",
        "modeled_adverse_slippage_bps",
        "max_quote_age_seconds",
        "max_spread_bps",
        "max_slippage_bps",
        "zone_low_tick",
        "zone_high_tick",
        "zone_boundary_tolerance_ticks",
        "age_within_limit",
        "spread_within_limit",
        "slippage_within_limit",
        "inside_zone",
        "decision",
        "reason_code",
    ],
)
def test_every_material_field_participates_in_hash(field):
    result = _admission()
    mapping = result.to_mapping()
    original = mapping.pop("admission_sha256")
    if field == "geometry":
        mapping[field]["canonical_symbol"] = "ETH/USDT:USDT"
    elif field == "snapshot":
        mapping[field]["quote_generation_id"] = "quote:g2"
    elif isinstance(mapping[field], bool):
        mapping[field] = not mapping[field]
    elif isinstance(mapping[field], int):
        mapping[field] += 1
    else:
        mapping[field] += "X"
    assert _canonical_hash(mapping) != original


def test_exact_project_import_inventory():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    project = [
        (
            node.module,
            tuple(alias.name for alias in node.names),
        )
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and (node.module or "").startswith("engine.")
    ]
    assert project == [
        (
            "engine.e3_executable_price_snapshot_v1",
            ("E3ExecutablePriceSnapshotV1",),
        ),
        (
            "engine.e3_golden_zone_geometry_v1",
            ("E3GoldenZoneGeometryV1",),
        ),
    ]


def test_bounded_standard_library_imports():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    modules = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module)
    assert modules == {
        "dataclasses",
        "datetime",
        "hashlib",
        "json",
        "re",
        "typing",
        "engine.e3_executable_price_snapshot_v1",
        "engine.e3_golden_zone_geometry_v1",
    }


def test_qualified_regex_calls_are_allowed_static_validation():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "re"
        and node.func.attr == "compile"
    ]
    assert len(calls) == 2
    assert all(
        len(call.args) == 1
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
        and not call.keywords
        for call in calls
    )


def test_no_float_decimal_fraction_true_division_or_clock():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, float)
        for node in ast.walk(tree)
    )
    assert not any(
        isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
        for node in ast.walk(tree)
    )
    calls = {
        (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else node.func.id
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert calls.isdisjoint(
        {
            "float",
            "Decimal",
            "Fraction",
            "now",
            "utcnow",
        }
    )


def test_no_midpoint_or_alternate_executable_selection():
    source = ENGINE_PATH.read_text(encoding="utf-8").lower()
    assert "midpoint" not in source
    tree = ast.parse(source)
    derived = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_derived_values"
    )
    price_assignments = [
        node
        for node in ast.walk(derived)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "price_tick"
            for target in node.targets
        )
    ]
    assert len(price_assignments) == 2
    attributes = {
        assignment.value.attr
        for assignment in price_assignments
        if isinstance(assignment.value, ast.Attribute)
    }
    assert attributes == {"best_ask_tick", "best_bid_tick"}


def test_no_effect_import_or_concurrency_surface():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    forbidden = {
        "aiohttp",
        "asyncio",
        "ccxt",
        "httpx",
        "multiprocessing",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "threading",
        "time",
        "urllib",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name.split(".")[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported.isdisjoint(forbidden)
    assert not any(
        isinstance(
            node,
            (
                ast.AsyncFunctionDef,
                ast.Await,
                ast.Yield,
                ast.YieldFrom,
            ),
        )
        for node in ast.walk(tree)
    )


def test_no_later_slice_authority_fields_or_effects():
    source = ENGINE_PATH.read_text(encoding="utf-8").lower()
    for forbidden in (
        "telegram",
        "pair_lock",
        "slot_change",
        "publish(",
        "execute_trade",
        "target_resolver",
        "trigger_result",
        "lifecycle_result",
    ):
        assert forbidden not in source


@pytest.mark.parametrize("path", [ENGINE_PATH, TEST_PATH])
def test_files_are_strict_utf8_lf_and_ast_parse(path):
    raw = path.read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    ast.parse(raw.decode("utf-8", "strict"), filename=str(path))


def test_no_skip_or_xfail_marker():
    tree = ast.parse(TEST_PATH.read_text(encoding="utf-8"))
    attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    assert "skip" not in attributes
    assert "xfail" not in attributes
