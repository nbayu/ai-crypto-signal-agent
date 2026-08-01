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
    POLICY_VERSION,
    SCHEMA_VERSION,
    VENUE_BINANCE_USDM,
    build_e3_executable_price_snapshot,
)
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
    build_e3_golden_zone_geometry,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage


ENGINE_PATH = Path(
    "engine/e3_executable_price_snapshot_v1.py"
)
TEST_PATH = Path(
    "tests/test_e3_executable_price_snapshot_v1.py"
)
FIELD_NAMES = [
    "schema_version",
    "policy_version",
    "geometry",
    "venue",
    "quote_generation_id",
    "exchange_timestamp",
    "best_bid_tick",
    "best_ask_tick",
    "last_price_tick",
    "mark_price_tick",
    "modeled_adverse_slippage_bps",
    "tick_size",
    "snapshot_sha256",
]


class StringSubclass(str):
    pass


class IntegerSubclass(int):
    pass


class GeometrySubclass(E3GoldenZoneGeometryV1):
    pass


class GeometryLookalike:
    pass


class DecimalLike:
    pass


def _geometry(
    *,
    mode="SWING",
    side="LONG",
    symbol="BTC/USDT:USDT",
    generation="structure:g1",
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


_UNSET = object()


def _snapshot(geometry=_UNSET, **overrides):
    selected_geometry = _geometry() if geometry is _UNSET else geometry
    selected_tick_size = (
        selected_geometry.tick_size
        if isinstance(
            selected_geometry,
            E3GoldenZoneGeometryV1,
        )
        else "0.1"
    )
    values = {
        "geometry": selected_geometry,
        "venue": "BINANCE_USDM",
        "quote_generation_id": "quote:g1",
        "exchange_timestamp": "2026-07-30T00:00:00Z",
        "best_bid_tick": 1299,
        "best_ask_tick": 1301,
        "last_price_tick": 1300,
        "mark_price_tick": 1300,
        "modeled_adverse_slippage_bps": 0,
        "tick_size": selected_tick_size,
    }
    values.update(overrides)
    return build_e3_executable_price_snapshot(**values)


def _constructor_mapping(snapshot):
    mapping = snapshot.to_mapping()
    mapping["geometry"] = snapshot.geometry
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
        match=r"^invalid E3 executable price snapshot$",
    ) as caught:
        call()
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_exact_public_exports():
    import engine.e3_executable_price_snapshot_v1 as module

    assert module.__all__ == (
        "E3ExecutablePriceSnapshotV1",
        "build_e3_executable_price_snapshot",
    )


def test_exact_defined_public_inventory():
    import engine.e3_executable_price_snapshot_v1 as module

    public = [
        name
        for name, value in vars(module).items()
        if not name.startswith("_")
        and (inspect.isclass(value) or inspect.isfunction(value))
        and getattr(value, "__module__", None) == module.__name__
    ]
    assert public == [
        "E3ExecutablePriceSnapshotV1",
        "build_e3_executable_price_snapshot",
    ]


def test_exact_dataclass_fields_and_annotations():
    assert [
        field.name
        for field in fields(E3ExecutablePriceSnapshotV1)
    ] == FIELD_NAMES
    assert E3ExecutablePriceSnapshotV1.__annotations__ == {
        "schema_version": str,
        "policy_version": str,
        "geometry": E3GoldenZoneGeometryV1,
        "venue": str,
        "quote_generation_id": str,
        "exchange_timestamp": str,
        "best_bid_tick": int,
        "best_ask_tick": int,
        "last_price_tick": int,
        "mark_price_tick": int,
        "modeled_adverse_slippage_bps": int,
        "tick_size": str,
        "snapshot_sha256": str,
    }


def test_result_is_frozen_slotted_and_has_no_dict():
    snapshot = _snapshot()
    assert tuple(snapshot.__slots__) == tuple(FIELD_NAMES)
    assert not hasattr(snapshot, "__dict__")
    with pytest.raises(FrozenInstanceError):
        snapshot.best_bid_tick = 1


def test_exact_one_public_method():
    public = [
        name
        for name, value in vars(
            E3ExecutablePriceSnapshotV1
        ).items()
        if not name.startswith("_") and inspect.isfunction(value)
    ]
    assert public == ["to_mapping"]


def test_exact_builder_signature():
    signature = inspect.signature(
        build_e3_executable_price_snapshot
    )
    assert list(signature.parameters) == [
        "geometry",
        "venue",
        "quote_generation_id",
        "exchange_timestamp",
        "best_bid_tick",
        "best_ask_tick",
        "last_price_tick",
        "mark_price_tick",
        "modeled_adverse_slippage_bps",
        "tick_size",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert (
        signature.return_annotation
        is E3ExecutablePriceSnapshotV1
    )


def test_exact_constants():
    assert SCHEMA_VERSION == "e3-executable-price-snapshot-v1"
    assert (
        POLICY_VERSION
        == "d3-executable-side-price-snapshot-v1"
    )
    assert VENUE_BINANCE_USDM == "BINANCE_USDM"


def test_mapping_key_order_and_nested_geometry():
    snapshot = _snapshot()
    mapping = snapshot.to_mapping()
    assert list(mapping) == FIELD_NAMES
    assert type(mapping["geometry"]) is dict
    assert mapping["geometry"] == snapshot.geometry.to_mapping()


def test_exact_geometry_is_retained():
    geometry = _geometry()
    snapshot = _snapshot(geometry)
    assert snapshot.geometry is geometry


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
def test_all_modes_are_accepted(mode):
    geometry = _geometry(mode=mode)
    assert _snapshot(geometry).geometry.mode == mode


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_both_sides_are_accepted(side):
    geometry = _geometry(side=side)
    assert _snapshot(geometry).geometry.side == side


def test_geometry_subclass_is_rejected():
    geometry = _geometry()
    subclass = GeometrySubclass(**geometry.to_mapping())
    _assert_sanitized(lambda: _snapshot(subclass))


@pytest.mark.parametrize(
    "geometry",
    [GeometryLookalike(), None, {}, "geometry"],
)
def test_geometry_lookalikes_are_rejected(geometry):
    _assert_sanitized(lambda: _snapshot(geometry))


@pytest.mark.parametrize(
    "venue",
    [
        "BINANCE",
        "binance_usdm",
        " BINANCE_USDM",
        StringSubclass("BINANCE_USDM"),
        1,
        None,
    ],
)
def test_invalid_venue_is_rejected(venue):
    _assert_sanitized(lambda: _snapshot(venue=venue))


@pytest.mark.parametrize(
    "quote_id",
    [
        "A",
        "quote.1",
        "quote_1",
        "quote:1",
        "quote+1",
        "quote-1",
        "a" * 128,
    ],
)
def test_safe_quote_generation_ids_are_accepted(quote_id):
    assert (
        _snapshot(quote_generation_id=quote_id).quote_generation_id
        == quote_id
    )


@pytest.mark.parametrize(
    "quote_id",
    [
        "",
        " ",
        "quote 1",
        "quote/1",
        "quote@1",
        "a" * 129,
        StringSubclass("quote"),
        1,
        None,
    ],
)
def test_invalid_quote_generation_ids_are_rejected(quote_id):
    _assert_sanitized(
        lambda: _snapshot(quote_generation_id=quote_id)
    )


def test_canonical_exchange_timestamp_is_accepted():
    assert (
        _snapshot().exchange_timestamp
        == "2026-07-30T00:00:00Z"
    )


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-07-30T00:00:00.0Z",
        "2026-07-30T00:00:00+00:00",
        "2026-07-30T00:00:00z",
        " 2026-07-30T00:00:00Z",
        "2026-02-30T00:00:00Z",
        "2026-07-30 00:00:00Z",
        StringSubclass("2026-07-30T00:00:00Z"),
        None,
    ],
)
def test_invalid_exchange_timestamps_are_rejected(timestamp):
    _assert_sanitized(
        lambda: _snapshot(exchange_timestamp=timestamp)
    )


@pytest.mark.parametrize(
    "field",
    [
        "best_bid_tick",
        "best_ask_tick",
        "last_price_tick",
        "mark_price_tick",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        True,
        IntegerSubclass(1),
        1.0,
        "1",
        0,
        -1,
        None,
    ],
)
def test_invalid_price_ticks_are_rejected(field, value):
    _assert_sanitized(lambda: _snapshot(**{field: value}))


@pytest.mark.parametrize(
    "bid,ask",
    [(1301, 1301), (1302, 1301)],
)
def test_crossed_or_locked_book_is_rejected(bid, ask):
    _assert_sanitized(
        lambda: _snapshot(
            best_bid_tick=bid,
            best_ask_tick=ask,
        )
    )


def test_last_and_mark_need_not_be_inside_spread():
    snapshot = _snapshot(
        last_price_tick=1,
        mark_price_tick=9999,
    )
    assert snapshot.last_price_tick == 1
    assert snapshot.mark_price_tick == 9999


@pytest.mark.parametrize("slippage", [0, 1, 10000])
def test_valid_slippage_bounds_are_accepted(slippage):
    assert (
        _snapshot(
            modeled_adverse_slippage_bps=slippage
        ).modeled_adverse_slippage_bps
        == slippage
    )


@pytest.mark.parametrize(
    "slippage",
    [
        -1,
        10001,
        True,
        IntegerSubclass(1),
        1.0,
        "1",
        None,
    ],
)
def test_invalid_slippage_is_rejected(slippage):
    _assert_sanitized(
        lambda: _snapshot(
            modeled_adverse_slippage_bps=slippage
        )
    )


@pytest.mark.parametrize(
    "tick_size",
    [
        "0.01",
        "1e-1",
        "0.10",
        DecimalLike(),
        0.1,
        StringSubclass("0.1"),
        None,
    ],
)
def test_tick_size_mismatch_or_noncanonical_type_rejected(
    tick_size,
):
    _assert_sanitized(lambda: _snapshot(tick_size=tick_size))


def test_canonical_geometry_tick_size_is_preserved():
    geometry = _geometry(tick_size="0.0001")
    snapshot = _snapshot(geometry)
    assert snapshot.tick_size == "0.0001"


def test_deterministic_replay_and_hash():
    geometry = _geometry()
    first = _snapshot(geometry)
    second = _snapshot(geometry)
    assert first.to_mapping() == second.to_mapping()
    assert first.snapshot_sha256 == second.snapshot_sha256
    mapping = first.to_mapping()
    supplied = mapping.pop("snapshot_sha256")
    assert supplied == _canonical_hash(mapping)


def test_mapping_is_detached():
    snapshot = _snapshot()
    mapping = snapshot.to_mapping()
    mapping["best_bid_tick"] = 1
    mapping["geometry"]["mode"] = "BROKEN"
    fresh = snapshot.to_mapping()
    assert fresh["best_bid_tick"] == 1299
    assert fresh["geometry"]["mode"] == "SWING"


def test_round_trip_with_original_geometry():
    snapshot = _snapshot()
    reconstructed = E3ExecutablePriceSnapshotV1(
        **_constructor_mapping(snapshot)
    )
    assert reconstructed == snapshot
    assert reconstructed.geometry is snapshot.geometry


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "other"),
        ("policy_version", "other"),
        ("venue", "OTHER"),
        ("quote_generation_id", "other:g"),
        ("exchange_timestamp", "2026-07-30T00:00:01Z"),
        ("best_bid_tick", 1298),
        ("best_ask_tick", 1302),
        ("last_price_tick", 1301),
        ("mark_price_tick", 1301),
        ("modeled_adverse_slippage_bps", 1),
        ("tick_size", "1"),
        ("snapshot_sha256", "0" * 64),
    ],
)
def test_direct_constructor_corruption_is_rejected(field, value):
    snapshot = _snapshot()
    _assert_sanitized(
        lambda: replace(snapshot, **{field: value})
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", StringSubclass(SCHEMA_VERSION)),
        ("policy_version", StringSubclass(POLICY_VERSION)),
        ("venue", StringSubclass("BINANCE_USDM")),
        ("quote_generation_id", StringSubclass("quote:g1")),
        (
            "exchange_timestamp",
            StringSubclass("2026-07-30T00:00:00Z"),
        ),
        ("best_bid_tick", IntegerSubclass(1299)),
        ("best_ask_tick", IntegerSubclass(1301)),
        ("last_price_tick", IntegerSubclass(1300)),
        ("mark_price_tick", IntegerSubclass(1300)),
        (
            "modeled_adverse_slippage_bps",
            IntegerSubclass(0),
        ),
        ("tick_size", StringSubclass("0.1")),
        ("snapshot_sha256", StringSubclass("0" * 64)),
    ],
)
def test_direct_constructor_subclasses_are_rejected(
    field,
    value,
):
    snapshot = _snapshot()
    mapping = _constructor_mapping(snapshot)
    mapping[field] = value
    if field != "snapshot_sha256":
        hash_mapping = dict(mapping)
        hash_mapping["geometry"] = (
            snapshot.geometry.to_mapping()
        )
        hash_mapping.pop("snapshot_sha256")
        mapping["snapshot_sha256"] = _canonical_hash(
            hash_mapping
        )
    _assert_sanitized(
        lambda: E3ExecutablePriceSnapshotV1(**mapping)
    )


def test_corrupted_geometry_is_rejected_and_sanitized():
    geometry = _geometry()
    object.__setattr__(geometry, "geometry_sha256", "0" * 64)
    _assert_sanitized(lambda: _snapshot(geometry))


@pytest.mark.parametrize(
    "field",
    [
        "geometry",
        "venue",
        "quote_generation_id",
        "exchange_timestamp",
        "best_bid_tick",
        "best_ask_tick",
        "last_price_tick",
        "mark_price_tick",
        "modeled_adverse_slippage_bps",
        "tick_size",
    ],
)
def test_every_material_field_participates_in_hash(field):
    snapshot = _snapshot()
    mapping = snapshot.to_mapping()
    original = mapping.pop("snapshot_sha256")
    if field == "geometry":
        mapping["geometry"]["canonical_symbol"] = (
            "ETH/USDT:USDT"
        )
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
            "engine.e3_golden_zone_geometry_v1",
            ("E3GoldenZoneGeometryV1",),
        )
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
        "engine.e3_golden_zone_geometry_v1",
    }


def test_qualified_regex_calls_are_static_validation_only():
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
    assert len(calls) == 4
    assert all(
        len(call.args) == 1
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
        and not call.keywords
        for call in calls
    )


def test_no_float_true_division_or_current_clock():
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
        {"float", "Decimal", "Fraction", "now", "utcnow"}
    )


def test_no_effect_or_concurrency_surface():
    source = ENGINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports = {
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
    assert imported.isdisjoint(forbidden_imports)
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
