from dataclasses import FrozenInstanceError, fields, replace
import ast
from hashlib import sha256
import inspect
import json
from pathlib import Path
import re
import subprocess

import pytest

from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
    build_e3_golden_zone_geometry,
)
from engine.e3_structural_targets_v1 import (
    DESTINATION_KIND_LIQUIDITY,
    DESTINATION_KIND_STRUCTURE,
    E3StructuralTargetsV1,
    MAX_DESTINATION_EVIDENCE_COUNT,
    POLICY_VERSION,
    SCHEMA_VERSION,
    build_e3_structural_targets,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage


ENGINE_PATH = Path("engine/e3_structural_targets_v1.py")
TEST_PATH = Path("tests/test_e3_structural_targets_v1.py")
FIELD_NAMES = [
    "schema_version",
    "policy_version",
    "geometry",
    "worst_entry_tick",
    "stop_loss_tick",
    "risk_distance_ticks",
    "tp1_destination_kind",
    "tp1_destination_id",
    "tp1_tick",
    "tp1_reward_ticks",
    "tp1_rr_numerator",
    "tp1_rr_denominator",
    "tp2_destination_kind",
    "tp2_destination_id",
    "tp2_tick",
    "tp2_reward_ticks",
    "tp2_rr_numerator",
    "tp2_rr_denominator",
    "targets_sha256",
]
_UNSET = object()


class StringSubclass(str):
    pass


class IntegerSubclass(int):
    pass


class TupleSubclass(tuple):
    pass


class GeometrySubclass(E3GoldenZoneGeometryV1):
    pass


class GeometryLookalike:
    pass


def _geometry(
    *,
    mode="SWING",
    side="LONG",
    generation="structure-generation-1",
    symbol="BTC/USDT:USDT",
    anchor_low_tick=1000,
    anchor_high_tick=2000,
    tick_size="0.1",
):
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
        tick_size=tick_size,
    )


def _destinations(
    geometry,
    *,
    first_kind="STRUCTURE",
    first_id="destination:tp1",
    first_tick=_UNSET,
    second_kind="LIQUIDITY",
    second_id="destination:tp2",
    second_tick=_UNSET,
    extra=(),
):
    if geometry.side == "LONG":
        first_tick = 2146 if first_tick is _UNSET else first_tick
        second_tick = 2528 if second_tick is _UNSET else second_tick
    else:
        first_tick = 854 if first_tick is _UNSET else first_tick
        second_tick = 472 if second_tick is _UNSET else second_tick
    return (
        (
            first_kind,
            first_id,
            first_tick,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        ),
        (
            second_kind,
            second_id,
            second_tick,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        ),
        *extra,
    )


def _result(*, geometry=None, destinations=None):
    selected_geometry = geometry or _geometry()
    selected_destinations = (
        _destinations(selected_geometry)
        if destinations is None
        else destinations
    )
    return build_e3_structural_targets(
        geometry=selected_geometry,
        ordered_destinations=selected_destinations,
    )


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


def _constructor_mapping(result):
    mapping = result.to_mapping()
    mapping["geometry"] = result.geometry
    return mapping


def _geometry_subclass(geometry):
    return GeometrySubclass(**geometry.to_mapping())


def _assert_sanitized(call):
    with pytest.raises(
        ValueError,
        match=r"^invalid E3 structural targets$",
    ) as caught:
        call()
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_exact_public_exports():
    import engine.e3_structural_targets_v1 as module

    assert module.__all__ == (
        "E3StructuralTargetsV1",
        "build_e3_structural_targets",
    )


def test_exact_module_defined_public_class_and_function_inventory():
    import engine.e3_structural_targets_v1 as module

    public = [
        name
        for name, value in vars(module).items()
        if not name.startswith("_")
        and (inspect.isclass(value) or inspect.isfunction(value))
        and getattr(value, "__module__", None) == module.__name__
    ]
    assert public == [
        "E3StructuralTargetsV1",
        "build_e3_structural_targets",
    ]


def test_exact_result_field_order():
    assert [field.name for field in fields(E3StructuralTargetsV1)] == (
        FIELD_NAMES
    )


def test_exact_result_annotations():
    assert E3StructuralTargetsV1.__annotations__ == {
        "schema_version": str,
        "policy_version": str,
        "geometry": E3GoldenZoneGeometryV1,
        "worst_entry_tick": int,
        "stop_loss_tick": int,
        "risk_distance_ticks": int,
        "tp1_destination_kind": str,
        "tp1_destination_id": str,
        "tp1_tick": int,
        "tp1_reward_ticks": int,
        "tp1_rr_numerator": int,
        "tp1_rr_denominator": int,
        "tp2_destination_kind": str,
        "tp2_destination_id": str,
        "tp2_tick": int,
        "tp2_reward_ticks": int,
        "tp2_rr_numerator": int,
        "tp2_rr_denominator": int,
        "targets_sha256": str,
    }


def test_result_is_frozen():
    result = _result()
    with pytest.raises(FrozenInstanceError):
        result.tp1_tick = 1


def test_result_is_slotted_without_dict():
    result = _result()
    assert not hasattr(result, "__dict__")
    assert tuple(result.__slots__) == tuple(FIELD_NAMES)


def test_exact_one_public_result_method():
    public = [
        name
        for name, value in vars(E3StructuralTargetsV1).items()
        if not name.startswith("_") and inspect.isfunction(value)
    ]
    assert public == ["to_mapping"]


def test_builder_signature_is_exact_keyword_only_without_defaults():
    signature = inspect.signature(build_e3_structural_targets)
    assert list(signature.parameters) == [
        "geometry",
        "ordered_destinations",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_builder_return_annotation_is_exact():
    assert (
        inspect.signature(
            build_e3_structural_targets
        ).return_annotation
        is E3StructuralTargetsV1
    )


def test_exact_contract_constants():
    assert SCHEMA_VERSION == "e3-structural-targets-v1"
    assert POLICY_VERSION == "structure-destination-targets-v1"
    assert DESTINATION_KIND_STRUCTURE == "STRUCTURE"
    assert DESTINATION_KIND_LIQUIDITY == "LIQUIDITY"
    assert MAX_DESTINATION_EVIDENCE_COUNT == 256


def test_mapping_key_order_is_exact():
    assert list(_result().to_mapping()) == FIELD_NAMES


def test_nested_geometry_is_serialized_as_mapping():
    result = _result()
    mapping = result.to_mapping()
    assert type(mapping["geometry"]) is dict
    assert mapping["geometry"] == result.geometry.to_mapping()
    assert mapping["geometry"] is not result.geometry


def test_exact_geometry_is_accepted_and_retained_by_identity():
    geometry = _geometry()
    result = _result(geometry=geometry)
    assert result.geometry is geometry


@pytest.mark.parametrize(
    "invalid_geometry",
    [
        GeometryLookalike(),
        None,
        {},
        "geometry",
    ],
)
def test_geometry_lookalikes_are_rejected(invalid_geometry):
    _assert_sanitized(
        lambda: build_e3_structural_targets(
            geometry=invalid_geometry,
            ordered_destinations=(),
        )
    )


def test_geometry_subclass_is_rejected():
    geometry = _geometry()
    subclass = _geometry_subclass(geometry)
    _assert_sanitized(
        lambda: build_e3_structural_targets(
            geometry=subclass,
            ordered_destinations=_destinations(geometry),
        )
    )


def test_geometry_hash_is_nested_in_target_hash_input():
    result = _result()
    mapping = result.to_mapping()
    supplied = mapping.pop("targets_sha256")
    assert mapping["geometry"]["geometry_sha256"] == (
        result.geometry.geometry_sha256
    )
    assert supplied == _canonical_hash(mapping)


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
def test_all_modes_are_accepted(mode):
    geometry = _geometry(mode=mode)
    result = _result(geometry=geometry)
    assert result.geometry.mode == mode
    assert result.geometry.structure_timeframe == {
        "SWING": "1h",
        "INTRADAY": "15m",
        "SCALP": "5m",
    }[mode]


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_both_sides_are_accepted(side):
    geometry = _geometry(side=side)
    result = _result(geometry=geometry)
    assert result.geometry.side == side


@pytest.mark.parametrize(
    "container_factory",
    [
        lambda records: list(records),
        lambda records: iter(records),
        lambda records: (record for record in records),
        lambda records: set(records),
        lambda records: {0: records[0], 1: records[1]},
        lambda records: "records",
        lambda records: None,
    ],
)
def test_non_tuple_destination_containers_are_rejected(
    container_factory,
):
    geometry = _geometry()
    records = _destinations(geometry)
    invalid = container_factory(records)
    _assert_sanitized(
        lambda: build_e3_structural_targets(
            geometry=geometry,
            ordered_destinations=invalid,
        )
    )


def test_tuple_subclass_container_is_rejected():
    geometry = _geometry()
    invalid = TupleSubclass(_destinations(geometry))
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=invalid,
        )
    )


@pytest.mark.parametrize("count", [0, 1])
def test_fewer_than_two_records_are_rejected(count):
    geometry = _geometry()
    records = _destinations(geometry)[:count]
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=records,
        )
    )


def test_exactly_two_records_are_accepted():
    geometry = _geometry()
    assert _result(geometry=geometry).tp2_tick == 2528


def test_three_records_are_accepted_without_replacing_targets():
    geometry = _geometry()
    extra = (
        (
            "STRUCTURE",
            "destination:tp3",
            3000,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        ),
    )
    result = _result(
        geometry=geometry,
        destinations=_destinations(geometry, extra=extra),
    )
    assert (result.tp1_tick, result.tp2_tick) == (2146, 2528)


def test_256_records_are_accepted():
    geometry = _geometry()
    records = tuple(
        (
            "STRUCTURE" if index % 2 == 0 else "LIQUIDITY",
            f"destination:{index}",
            2146 + index,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        )
        for index in range(256)
    )
    result = _result(geometry=geometry, destinations=records)
    assert result.tp1_tick == 2146
    assert result.tp2_tick == 2147


def test_257_records_are_rejected():
    geometry = _geometry()
    records = tuple(
        (
            "STRUCTURE",
            f"destination:{index}",
            2146 + index,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        )
        for index in range(257)
    )
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=records,
        )
    )


def test_record_tuple_subclass_is_rejected():
    geometry = _geometry()
    records = list(_destinations(geometry))
    records[0] = TupleSubclass(records[0])
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=tuple(records),
        )
    )


@pytest.mark.parametrize("record_length", [0, 1, 2, 3, 4, 6])
def test_wrong_record_cardinality_is_rejected(record_length):
    geometry = _geometry()
    records = list(_destinations(geometry))
    if record_length == 6:
        records[0] = records[0] + ("extra",)
    else:
        records[0] = records[0][:record_length]
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=tuple(records),
        )
    )


@pytest.mark.parametrize(
    "first_kind,second_kind",
    [
        ("STRUCTURE", "STRUCTURE"),
        ("LIQUIDITY", "LIQUIDITY"),
        ("STRUCTURE", "LIQUIDITY"),
        ("LIQUIDITY", "STRUCTURE"),
    ],
)
def test_allowed_destination_kind_combinations(
    first_kind,
    second_kind,
):
    geometry = _geometry()
    result = _result(
        geometry=geometry,
        destinations=_destinations(
            geometry,
            first_kind=first_kind,
            second_kind=second_kind,
        ),
    )
    assert result.tp1_destination_kind == first_kind
    assert result.tp2_destination_kind == second_kind


@pytest.mark.parametrize(
    "invalid_kind",
    [
        "structure",
        "LIQ",
        "TARGET",
        "",
        StringSubclass("STRUCTURE"),
        1,
        None,
    ],
)
def test_invalid_destination_kinds_are_rejected(invalid_kind):
    geometry = _geometry()
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_kind=invalid_kind,
            ),
        )
    )


@pytest.mark.parametrize(
    "destination_id",
    [
        "A",
        "target.1",
        "target_1",
        "target:1",
        "target+1",
        "target-1",
        "a" * 128,
    ],
)
def test_safe_destination_ids_are_accepted(destination_id):
    geometry = _geometry()
    result = _result(
        geometry=geometry,
        destinations=_destinations(
            geometry,
            first_id=destination_id,
        ),
    )
    assert result.tp1_destination_id == destination_id


@pytest.mark.parametrize(
    "invalid_id",
    [
        "",
        " ",
        "target 1",
        "target/1",
        "target@1",
        "a" * 129,
        StringSubclass("target"),
        1,
        None,
    ],
)
def test_invalid_destination_ids_are_rejected(invalid_id):
    geometry = _geometry()
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_id=invalid_id,
            ),
        )
    )


def test_duplicate_destination_id_in_selected_records_is_rejected():
    geometry = _geometry()
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                second_id="destination:tp1",
            ),
        )
    )


def test_duplicate_destination_id_in_later_record_is_rejected():
    geometry = _geometry()
    extra = (
        (
            "STRUCTURE",
            "destination:tp1",
            3000,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        ),
    )
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                extra=extra,
            ),
        )
    )


@pytest.mark.parametrize(
    "invalid_tick",
    [
        True,
        IntegerSubclass(2146),
        2146.0,
        "2146",
        0,
        -1,
        None,
    ],
)
def test_invalid_destination_ticks_are_rejected(invalid_tick):
    geometry = _geometry()
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_tick=invalid_tick,
            ),
        )
    )


def test_duplicate_destination_tick_in_selected_records_is_rejected():
    geometry = _geometry()
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                second_tick=2146,
            ),
        )
    )


def test_duplicate_destination_tick_in_later_record_is_rejected():
    geometry = _geometry()
    extra = (
        (
            "STRUCTURE",
            "destination:tp3",
            2146,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        ),
    )
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                extra=extra,
            ),
        )
    )


def test_target_ticks_are_preserved_exactly():
    geometry = _geometry()
    records = _destinations(
        geometry,
        first_tick=2201,
        second_tick=2603,
    )
    result = _result(geometry=geometry, destinations=records)
    assert result.tp1_tick is records[0][2]
    assert result.tp2_tick is records[1][2]


@pytest.mark.parametrize(
    "field_index,invalid_value",
    [
        (3, "15m"),
        (3, "1H"),
        (3, " "),
        (3, ""),
        (3, StringSubclass("1h")),
        (3, None),
        (4, "other-generation"),
        (4, " "),
        (4, ""),
        (4, StringSubclass("structure-generation-1")),
        (4, None),
    ],
)
def test_structure_binding_mismatches_are_rejected(
    field_index,
    invalid_value,
):
    geometry = _geometry()
    records = list(_destinations(geometry))
    record = list(records[0])
    record[field_index] = invalid_value
    records[0] = tuple(record)
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=tuple(records),
        )
    )


def test_long_resolution_exact_values():
    result = _result()
    assert result.worst_entry_tick == 1382
    assert result.stop_loss_tick == 1000
    assert result.risk_distance_ticks == 382
    assert result.tp1_tick == 2146
    assert result.tp1_reward_ticks == 764
    assert result.tp1_rr_numerator == 764
    assert result.tp1_rr_denominator == 382
    assert result.tp2_tick == 2528
    assert result.tp2_reward_ticks == 1146
    assert result.tp2_rr_numerator == 1146
    assert result.tp2_rr_denominator == 382


def test_short_resolution_exact_values():
    geometry = _geometry(side="SHORT")
    result = _result(geometry=geometry)
    assert result.worst_entry_tick == 1618
    assert result.stop_loss_tick == 2000
    assert result.risk_distance_ticks == 382
    assert result.tp1_tick == 854
    assert result.tp1_reward_ticks == 764
    assert result.tp1_rr_numerator == 764
    assert result.tp1_rr_denominator == 382
    assert result.tp2_tick == 472
    assert result.tp2_reward_ticks == 1146
    assert result.tp2_rr_numerator == 1146
    assert result.tp2_rr_denominator == 382


@pytest.mark.parametrize(
    "first_tick,second_tick",
    [
        (1382, 2528),
        (1300, 2528),
        (2146, 2145),
        (2528, 2146),
    ],
)
def test_invalid_long_directional_order_is_rejected(
    first_tick,
    second_tick,
):
    geometry = _geometry()
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_tick=first_tick,
                second_tick=second_tick,
            ),
        )
    )


@pytest.mark.parametrize(
    "first_tick,second_tick",
    [
        (1618, 472),
        (1700, 472),
        (854, 855),
        (472, 854),
    ],
)
def test_invalid_short_directional_order_is_rejected(
    first_tick,
    second_tick,
):
    geometry = _geometry(side="SHORT")
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_tick=first_tick,
                second_tick=second_tick,
            ),
        )
    )


def test_invalid_first_record_does_not_select_later_records():
    geometry = _geometry()
    records = (
        (
            "STRUCTURE",
            "invalid:first",
            1300,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        ),
        *_destinations(geometry),
    )
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=records,
        )
    )


def test_invalid_second_record_does_not_select_third_record():
    geometry = _geometry()
    records = (
        _destinations(geometry)[0],
        (
            "LIQUIDITY",
            "invalid:second",
            2000,
            geometry.structure_timeframe,
            geometry.structure_generation_id,
        ),
        _destinations(geometry)[1],
    )
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=records,
        )
    )


def test_unreduced_integer_rr_is_preserved():
    result = _result()
    assert (result.tp1_rr_numerator, result.tp1_rr_denominator) == (
        764,
        382,
    )
    assert (result.tp2_rr_numerator, result.tp2_rr_denominator) == (
        1146,
        382,
    )


def test_rewards_are_positive_and_strictly_increasing():
    result = _result()
    assert 0 < result.tp1_reward_ticks < result.tp2_reward_ticks


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "other-schema"),
        ("policy_version", "other-policy"),
        ("worst_entry_tick", 1383),
        ("stop_loss_tick", 999),
        ("risk_distance_ticks", 381),
        ("tp1_destination_kind", "LIQUIDITY"),
        ("tp1_destination_id", "other:tp1"),
        ("tp1_tick", 2200),
        ("tp1_reward_ticks", 765),
        ("tp1_rr_numerator", 382),
        ("tp1_rr_denominator", 191),
        ("tp2_destination_kind", "STRUCTURE"),
        ("tp2_destination_id", "other:tp2"),
        ("tp2_tick", 2600),
        ("tp2_reward_ticks", 1145),
        ("tp2_rr_numerator", 573),
        ("tp2_rr_denominator", 191),
        ("targets_sha256", "0" * 64),
    ],
)
def test_direct_constructor_corruption_is_rejected(field, value):
    result = _result()
    _assert_sanitized(lambda: replace(result, **{field: value}))


def test_direct_constructor_geometry_replacement_mismatch_rejected():
    result = _result()
    replacement = _geometry(
        generation="other-generation",
        symbol="ETH/USDT:USDT",
    )
    _assert_sanitized(
        lambda: replace(result, geometry=replacement)
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", StringSubclass(SCHEMA_VERSION)),
        ("policy_version", StringSubclass(POLICY_VERSION)),
        (
            "tp1_destination_kind",
            StringSubclass("STRUCTURE"),
        ),
        ("tp1_destination_id", StringSubclass("destination:tp1")),
        ("tp1_tick", IntegerSubclass(2146)),
        ("tp1_reward_ticks", IntegerSubclass(764)),
        ("tp1_rr_numerator", IntegerSubclass(764)),
        ("tp1_rr_denominator", IntegerSubclass(382)),
        (
            "tp2_destination_kind",
            StringSubclass("LIQUIDITY"),
        ),
        ("tp2_destination_id", StringSubclass("destination:tp2")),
        ("tp2_tick", IntegerSubclass(2528)),
        ("tp2_reward_ticks", IntegerSubclass(1146)),
        ("tp2_rr_numerator", IntegerSubclass(1146)),
        ("tp2_rr_denominator", IntegerSubclass(382)),
        ("targets_sha256", StringSubclass("0" * 64)),
    ],
)
def test_direct_constructor_subclass_values_are_rejected(
    field,
    value,
):
    result = _result()
    mapping = _constructor_mapping(result)
    mapping[field] = value
    if field != "targets_sha256":
        hash_mapping = dict(mapping)
        hash_mapping["geometry"] = result.geometry.to_mapping()
        hash_mapping.pop("targets_sha256")
        mapping["targets_sha256"] = _canonical_hash(hash_mapping)
    _assert_sanitized(lambda: E3StructuralTargetsV1(**mapping))


def test_direct_constructor_round_trip_with_original_geometry():
    result = _result()
    reconstructed = E3StructuralTargetsV1(
        **_constructor_mapping(result)
    )
    assert reconstructed == result
    assert reconstructed.geometry is result.geometry


def test_deterministic_replay():
    geometry = _geometry()
    records = _destinations(geometry)
    first = _result(geometry=geometry, destinations=records)
    second = _result(geometry=geometry, destinations=records)
    assert first.to_mapping() == second.to_mapping()
    assert first.targets_sha256 == second.targets_sha256


def test_mapping_serialization_is_detached():
    result = _result()
    first = result.to_mapping()
    first["tp1_tick"] = 1
    first["geometry"]["mode"] = "BROKEN"
    second = result.to_mapping()
    assert second["tp1_tick"] == 2146
    assert second["geometry"]["mode"] == "SWING"


@pytest.mark.parametrize(
    "variant",
    [
        "geometry_symbol",
        "geometry_generation",
        "geometry_tick_size",
        "mode",
        "side",
        "tp1_kind",
        "tp2_kind",
        "tp1_id",
        "tp2_id",
        "tp1_tick",
        "tp2_tick",
        "anchor_span",
    ],
)
def test_hash_changes_for_valid_material_variants(variant):
    baseline = _result()
    if variant == "geometry_symbol":
        geometry = _geometry(symbol="ETH/USDT:USDT")
        changed = _result(geometry=geometry)
    elif variant == "geometry_generation":
        geometry = _geometry(generation="generation:two")
        changed = _result(geometry=geometry)
    elif variant == "geometry_tick_size":
        geometry = _geometry(tick_size="0.01")
        changed = _result(geometry=geometry)
    elif variant == "mode":
        geometry = _geometry(mode="SCALP")
        changed = _result(geometry=geometry)
    elif variant == "side":
        geometry = _geometry(side="SHORT")
        changed = _result(geometry=geometry)
    elif variant == "tp1_kind":
        geometry = _geometry()
        changed = _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_kind="LIQUIDITY",
            ),
        )
    elif variant == "tp2_kind":
        geometry = _geometry()
        changed = _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                second_kind="STRUCTURE",
            ),
        )
    elif variant == "tp1_id":
        geometry = _geometry()
        changed = _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_id="changed:tp1",
            ),
        )
    elif variant == "tp2_id":
        geometry = _geometry()
        changed = _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                second_id="changed:tp2",
            ),
        )
    elif variant == "tp1_tick":
        geometry = _geometry()
        changed = _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_tick=2200,
            ),
        )
    elif variant == "tp2_tick":
        geometry = _geometry()
        changed = _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                second_tick=2600,
            ),
        )
    else:
        geometry = _geometry(anchor_high_tick=2100)
        changed = _result(
            geometry=geometry,
            destinations=_destinations(
                geometry,
                first_tick=2300,
                second_tick=2700,
            ),
        )
    assert changed.targets_sha256 != baseline.targets_sha256


@pytest.mark.parametrize(
    "field",
    [
        "geometry",
        "worst_entry_tick",
        "stop_loss_tick",
        "risk_distance_ticks",
        "tp1_destination_kind",
        "tp1_destination_id",
        "tp1_tick",
        "tp1_reward_ticks",
        "tp1_rr_numerator",
        "tp1_rr_denominator",
        "tp2_destination_kind",
        "tp2_destination_id",
        "tp2_tick",
        "tp2_reward_ticks",
        "tp2_rr_numerator",
        "tp2_rr_denominator",
    ],
)
def test_every_material_field_changes_required_hash(field):
    result = _result()
    mapping = result.to_mapping()
    original_hash = mapping.pop("targets_sha256")
    if field == "geometry":
        mapping[field]["canonical_symbol"] = "ETH/USDT:USDT"
    elif isinstance(mapping[field], int):
        mapping[field] += 1
    else:
        mapping[field] += "X"
    assert _canonical_hash(mapping) != original_hash


def test_output_equals_caller_records_zero_and_one():
    geometry = _geometry()
    records = _destinations(geometry)
    result = _result(geometry=geometry, destinations=records)
    assert (
        result.tp1_destination_kind,
        result.tp1_destination_id,
        result.tp1_tick,
    ) == records[0][:3]
    assert (
        result.tp2_destination_kind,
        result.tp2_destination_id,
        result.tp2_tick,
    ) == records[1][:3]


def test_complete_evidence_is_not_sorted():
    geometry = _geometry()
    records = (
        _destinations(geometry)[1],
        _destinations(geometry)[0],
    )
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=records,
        )
    )


def test_error_does_not_expose_nested_geometry_message():
    geometry = _geometry()
    object.__setattr__(geometry, "geometry_sha256", "0" * 64)
    _assert_sanitized(
        lambda: _result(
            geometry=geometry,
            destinations=_destinations(geometry),
        )
    )


def test_project_import_inventory_is_exact():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    project_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").startswith("engine."):
                project_imports.append(
                    (
                        node.module,
                        tuple(alias.name for alias in node.names),
                    )
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("engine."):
                    project_imports.append((alias.name, ()))
    assert project_imports == [
        (
            "engine.e3_golden_zone_geometry_v1",
            ("E3GoldenZoneGeometryV1",),
        )
    ]


def test_standard_library_import_inventory_is_bounded():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module)
    assert modules == {
        "dataclasses",
        "hashlib",
        "json",
        "re",
        "typing",
        "engine.e3_golden_zone_geometry_v1",
    }


def test_no_forbidden_imports():
    source = ENGINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "aiohttp",
        "asyncio",
        "ccxt",
        "concurrent",
        "datetime",
        "decimal",
        "fractions",
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
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported.isdisjoint(forbidden)


def test_no_float_decimal_fraction_or_true_division_authority():
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
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint({"float", "Decimal", "Fraction"})


def test_no_sort_filter_or_selection_search_calls():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    assert called.isdisjoint(
        {"sorted", "sort", "filter", "min", "max"}
    )


def test_no_async_concurrency_or_generator_contract():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
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


def test_no_filesystem_network_cache_or_runtime_calls():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    forbidden = {
        "open",
        "read",
        "read_text",
        "read_bytes",
        "write",
        "write_text",
        "write_bytes",
        "touch",
        "mkdir",
        "unlink",
        "rename",
        "replace",
        "socket",
        "request",
        "get",
        "post",
        "send",
        "publish",
        "order",
        "sleep",
        "retry",
        "backoff",
        "now",
        "utcnow",
        "cache_get",
        "cache_set",
    }
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    assert called.isdisjoint(forbidden)


def test_no_module_global_mutable_execution_state():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign):
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            value = node.value
        assert not isinstance(
            value,
            (
                ast.List,
                ast.Dict,
                ast.Set,
                ast.ListComp,
                ast.DictComp,
                ast.SetComp,
            ),
        )


def test_no_forbidden_policy_or_authority_fields():
    tree = ast.parse(ENGINE_PATH.read_text(encoding="utf-8"))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "E3StructuralTargetsV1"
    )
    field_names = {
        node.target.id
        for node in class_node.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
    }
    forbidden_fragments = {
        "quote",
        "trigger",
        "lifecycle",
        "publication",
        "slot",
        "pair_lock",
        "trailing",
        "actionable",
        "mode_floor",
    }
    assert all(
        all(fragment not in field for fragment in forbidden_fragments)
        for field in field_names
    )


def test_source_has_no_legacy_extension_or_target_manufacturing():
    source = ENGINE_PATH.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "-0.27" not in source
    assert "fibonacci" not in lowered
    assert "interpol" not in lowered
    assert "average" not in lowered
    assert "clamp" not in lowered
    assert "trailing" not in lowered


def test_no_production_reference_to_new_contract():
    result = subprocess.run(
        [
            "git",
            "grep",
            "-n",
            "-E",
            (
                "e3_structural_targets_v1|"
                "build_e3_structural_targets|"
                "E3StructuralTargetsV1"
            ),
            "HEAD",
            "--",
            "engine",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""


def test_exact_two_file_mutation_inventory():
    result = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--untracked-files=all",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert sorted(result.stdout.splitlines()) == [
        "?? engine/e3_structural_targets_v1.py",
        "?? tests/test_e3_structural_targets_v1.py",
    ]


@pytest.mark.parametrize("path", [ENGINE_PATH, TEST_PATH])
def test_authorized_files_are_strict_utf8_lf_and_ast_parse(path):
    raw = path.read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    source = raw.decode("utf-8", "strict")
    ast.parse(source, filename=str(path))


def test_no_skip_or_xfail_markers():
    tree = ast.parse(TEST_PATH.read_text(encoding="utf-8"))
    attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    assert "skip" not in attributes
    assert "xfail" not in attributes
