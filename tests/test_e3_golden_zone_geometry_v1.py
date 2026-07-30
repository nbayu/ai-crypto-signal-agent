import ast
import dataclasses
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path
import subprocess

import pytest

from engine.mode_data_plan_v1 import build_mode_audit_lineage
import engine.e3_golden_zone_geometry_v1 as geometry_module
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
    build_e3_golden_zone_geometry,
)


_FIELDS = [
    "schema_version",
    "policy_version",
    "mode",
    "mode_profile_version",
    "mode_lineage_sha256",
    "canonical_symbol",
    "side",
    "structure_timeframe",
    "structure_generation_id",
    "anchor_low_at",
    "anchor_low_tick",
    "anchor_high_at",
    "anchor_high_tick",
    "tick_size",
    "shallow_retracement_milli",
    "deep_retracement_milli",
    "golden_zone_low_tick",
    "golden_zone_high_tick",
    "stop_loss_tick",
    "geometry_sha256",
]
_ANNOTATIONS = [
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    int,
    str,
    int,
    str,
    int,
    int,
    int,
    int,
    int,
    str,
]
_STRUCTURE_TIMEFRAMES = {
    "SWING": "1h",
    "INTRADAY": "15m",
    "SCALP": "5m",
}
_ERROR = "invalid E3 Golden Zone geometry"
_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_PATH = (
    _ROOT / "engine" / "e3_golden_zone_geometry_v1.py"
)
_TEST_PATH = (
    _ROOT / "tests" / "test_e3_golden_zone_geometry_v1.py"
)


class _TextSubclass(str):
    pass


class _IntSubclass(int):
    pass


def _lineage(mode):
    return build_mode_audit_lineage(mode).lineage_sha256


def _kwargs(mode="SWING", side="LONG", **overrides):
    if side == "LONG":
        low_at = "2026-07-30T10:00:00Z"
        high_at = "2026-07-30T11:00:00Z"
    else:
        low_at = "2026-07-30T11:00:00Z"
        high_at = "2026-07-30T10:00:00Z"
    values = {
        "mode": mode,
        "mode_lineage_sha256": _lineage(mode),
        "canonical_symbol": "BTC/USDT:USDT",
        "side": side,
        "structure_generation_id": "structure:BTC_USDT+01",
        "anchor_low_at": low_at,
        "anchor_low_tick": 1000,
        "anchor_high_at": high_at,
        "anchor_high_tick": 2000,
        "tick_size": "0.1",
    }
    values.update(overrides)
    return values


def _build(mode="SWING", side="LONG", **overrides):
    return build_e3_golden_zone_geometry(
        **_kwargs(mode=mode, side=side, **overrides)
    )


def _required_hash(mapping):
    content = dict(mapping)
    content.pop("geometry_sha256", None)
    encoded = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _with_required_hash(mapping):
    value = dict(mapping)
    value["geometry_sha256"] = _required_hash(value)
    return value


def _assert_invalid(call):
    with pytest.raises(ValueError) as exc_info:
        call()
    assert type(exc_info.value) is ValueError
    assert str(exc_info.value) == _ERROR
    assert exc_info.value.__cause__ is None


def test_exact_all():
    assert geometry_module.__all__ == (
        "E3GoldenZoneGeometryV1",
        "build_e3_golden_zone_geometry",
    )


def test_exact_defined_public_class_and_function_inventory():
    inventory = {
        name
        for name, value in vars(geometry_module).items()
        if not name.startswith("_")
        and getattr(value, "__module__", None)
        == geometry_module.__name__
        and (
            inspect.isclass(value)
            or inspect.isfunction(value)
        )
    }
    assert inventory == {
        "E3GoldenZoneGeometryV1",
        "build_e3_golden_zone_geometry",
    }


def test_exact_dataclass_field_order_and_annotations():
    fields = dataclasses.fields(E3GoldenZoneGeometryV1)
    assert [field.name for field in fields] == _FIELDS
    assert [field.type for field in fields] == _ANNOTATIONS


def test_result_is_frozen():
    result = _build()
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.mode = "INTRADAY"


def test_result_is_slotted_without_dict():
    result = _build()
    assert E3GoldenZoneGeometryV1.__slots__ == tuple(_FIELDS)
    assert not hasattr(result, "__dict__")


def test_result_exposes_exactly_one_public_method():
    public_methods = {
        name
        for name, value in E3GoldenZoneGeometryV1.__dict__.items()
        if not name.startswith("_") and callable(value)
    }
    assert public_methods == {"to_mapping"}


def test_builder_signature_is_exact():
    signature = inspect.signature(
        build_e3_golden_zone_geometry
    )
    assert list(signature.parameters) == [
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "side",
        "structure_generation_id",
        "anchor_low_at",
        "anchor_low_tick",
        "anchor_high_at",
        "anchor_high_tick",
        "tick_size",
    ]
    assert all(
        parameter.kind
        is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert (
        signature.return_annotation
        is E3GoldenZoneGeometryV1
    )


def test_exact_constant_values():
    assert (
        geometry_module.SCHEMA_VERSION
        == "e3-golden-zone-geometry-v1"
    )
    assert (
        geometry_module.POLICY_VERSION
        == "e3-golden-zone-geometry-policy-v1"
    )
    assert geometry_module.SHALLOW_RETRACEMENT_MILLI == 618
    assert geometry_module.DEEP_RETRACEMENT_MILLI == 786
    assert geometry_module.RETRACEMENT_DENOMINATOR == 1000


def test_to_mapping_key_order_matches_fields():
    result = _build()
    assert list(result.to_mapping()) == _FIELDS


@pytest.mark.parametrize(
    ("mode", "structure_timeframe"),
    [
        ("SWING", "1h"),
        ("INTRADAY", "15m"),
        ("SCALP", "5m"),
    ],
)
def test_all_modes_bind_lineage_and_structure_timeframe(
    mode,
    structure_timeframe,
):
    result = _build(mode=mode)
    assert result.mode == mode
    assert result.mode_lineage_sha256 == _lineage(mode)
    assert result.structure_timeframe == structure_timeframe
    assert (
        result.mode_profile_version
        == "mode-profile-policy-v1"
    )


@pytest.mark.parametrize(
    ("mode", "other_mode"),
    [
        ("SWING", "INTRADAY"),
        ("INTRADAY", "SCALP"),
        ("SCALP", "SWING"),
    ],
)
def test_cross_mode_lineage_is_rejected(mode, other_mode):
    values = _kwargs(mode=mode)
    values["mode_lineage_sha256"] = _lineage(other_mode)
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


def test_random_valid_looking_lineage_is_rejected():
    values = _kwargs()
    values["mode_lineage_sha256"] = "a" * 64
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


@pytest.mark.parametrize(
    "mode",
    [
        _TextSubclass("SWING"),
        "swing",
        "Swing",
        "DAY",
        "UNKNOWN",
        "",
        None,
    ],
)
def test_invalid_modes_are_rejected(mode):
    values = _kwargs()
    values["mode"] = mode
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


def test_long_exact_geometry():
    result = _build(side="LONG")
    assert result.anchor_low_tick == 1000
    assert result.anchor_high_tick == 2000
    assert result.golden_zone_low_tick == 1214
    assert result.golden_zone_high_tick == 1382
    assert result.stop_loss_tick == 1000


def test_short_exact_geometry():
    result = _build(side="SHORT")
    assert result.anchor_low_tick == 1000
    assert result.anchor_high_tick == 2000
    assert result.golden_zone_low_tick == 1618
    assert result.golden_zone_high_tick == 1786
    assert result.stop_loss_tick == 2000


def test_long_nondivisible_conservative_rounding():
    result = _build(
        side="LONG",
        anchor_high_tick=2001,
    )
    assert result.golden_zone_low_tick == 1215
    assert result.golden_zone_high_tick == 1382
    exact_low = Fraction(2001) - Fraction(1001 * 786, 1000)
    exact_high = (
        Fraction(2001) - Fraction(1001 * 618, 1000)
    )
    assert result.golden_zone_low_tick >= exact_low
    assert result.golden_zone_high_tick <= exact_high


def test_short_nondivisible_conservative_rounding():
    result = _build(
        side="SHORT",
        anchor_high_tick=2001,
    )
    assert result.golden_zone_low_tick == 1619
    assert result.golden_zone_high_tick == 1786
    exact_low = Fraction(1000) + Fraction(1001 * 618, 1000)
    exact_high = Fraction(1000) + Fraction(1001 * 786, 1000)
    assert result.golden_zone_low_tick >= exact_low
    assert result.golden_zone_high_tick <= exact_high


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_integer_zone_never_expands_exact_zone(side):
    result = _build(
        side=side,
        anchor_low_tick=137,
        anchor_high_tick=9372,
    )
    span = 9372 - 137
    if side == "LONG":
        exact_low = Fraction(9372) - Fraction(
            span * 786,
            1000,
        )
        exact_high = Fraction(9372) - Fraction(
            span * 618,
            1000,
        )
    else:
        exact_low = Fraction(137) + Fraction(
            span * 618,
            1000,
        )
        exact_high = Fraction(137) + Fraction(
            span * 786,
            1000,
        )
    assert result.golden_zone_low_tick >= exact_low
    assert result.golden_zone_high_tick <= exact_high


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_too_small_span_fails_closed(side):
    _assert_invalid(
        lambda: _build(
            side=side,
            anchor_low_tick=1000,
            anchor_high_tick=1001,
        )
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("anchor_low_tick", True),
        ("anchor_high_tick", False),
        ("anchor_low_tick", _IntSubclass(1000)),
        ("anchor_high_tick", _IntSubclass(2000)),
        ("anchor_low_tick", 0),
        ("anchor_low_tick", -1),
        ("anchor_high_tick", 0),
        ("anchor_high_tick", -1),
        ("anchor_low_tick", "1000"),
        ("anchor_high_tick", 2000.0),
    ],
)
def test_anchor_ticks_require_exact_positive_ints(field, value):
    values = _kwargs()
    values[field] = value
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


@pytest.mark.parametrize(
    ("low_tick", "high_tick"),
    [(1000, 1000), (2000, 1000)],
)
def test_equal_or_reversed_anchor_ticks_are_rejected(
    low_tick,
    high_tick,
):
    _assert_invalid(
        lambda: _build(
            anchor_low_tick=low_tick,
            anchor_high_tick=high_tick,
        )
    )


def test_long_timestamp_order_is_enforced():
    _assert_invalid(
        lambda: _build(
            side="LONG",
            anchor_low_at="2026-07-30T11:00:00Z",
            anchor_high_at="2026-07-30T10:00:00Z",
        )
    )


def test_short_timestamp_order_is_enforced():
    _assert_invalid(
        lambda: _build(
            side="SHORT",
            anchor_low_at="2026-07-30T10:00:00Z",
            anchor_high_at="2026-07-30T11:00:00Z",
        )
    )


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-07-30T10:00:00.000Z",
        "2026-07-30T10:00:00+00:00",
        " 2026-07-30T10:00:00Z",
        "2026-07-30T10:00:00Z ",
        "2026-07-30T10:00:00z",
        "2026-02-30T10:00:00Z",
        "2026-13-01T10:00:00Z",
        "2026-07-30 10:00:00Z",
        "",
        None,
        _TextSubclass("2026-07-30T10:00:00Z"),
    ],
)
def test_invalid_anchor_timestamp_forms_are_rejected(timestamp):
    values = _kwargs()
    values["anchor_low_at"] = timestamp
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_equal_anchor_timestamps_are_rejected(side):
    same = "2026-07-30T10:00:00Z"
    _assert_invalid(
        lambda: _build(
            side=side,
            anchor_low_at=same,
            anchor_high_at=same,
        )
    )


@pytest.mark.parametrize(
    "tick_size",
    ["1", "0.1", "0.0001", "1.25", "10", "10.01"],
)
def test_canonical_tick_sizes_are_accepted(tick_size):
    result = _build(tick_size=tick_size)
    assert result.tick_size == tick_size
    assert result.to_mapping()["tick_size"] == tick_size
    assert result.geometry_sha256 == _required_hash(
        result.to_mapping()
    )


@pytest.mark.parametrize(
    "tick_size",
    [
        "0",
        "00.1",
        "01",
        "1.0",
        "0.10",
        "1e-3",
        "+0.1",
        "-0.1",
        "1.",
        ".1",
        "NaN",
        "Infinity",
        "",
        1,
        0.1,
        _TextSubclass("0.1"),
        None,
    ],
)
def test_noncanonical_tick_sizes_are_rejected(tick_size):
    values = _kwargs()
    values["tick_size"] = tick_size
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


@pytest.mark.parametrize(
    "symbol",
    [
        "BTC/USDT:USDT",
        "1000PEPE/USDT:USDT",
        "A/B:C",
        "ABC123/USDT:USDT",
    ],
)
def test_canonical_symbols_are_accepted(symbol):
    assert _build(canonical_symbol=symbol).canonical_symbol == symbol


@pytest.mark.parametrize(
    "symbol",
    [
        "btc/USDT:USDT",
        "BTCUSDT",
        "BTC-USDT",
        "BTC/USDT",
        "BTC/USDT:",
        "/USDT:USDT",
        " BTC/USDT:USDT",
        "BTC/USDT:USDT ",
        "BTC//USDT:USDT",
        "A" * 33 + "/USDT:USDT",
        "BTC/" + "U" * 33 + ":USDT",
        "BTC/USDT:" + "U" * 33,
        _TextSubclass("BTC/USDT:USDT"),
        None,
    ],
)
def test_malformed_symbols_are_rejected(symbol):
    values = _kwargs()
    values["canonical_symbol"] = symbol
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_exact_sides_are_accepted(side):
    assert _build(side=side).side == side


@pytest.mark.parametrize(
    "side",
    [
        "long",
        "BUY",
        "SELL",
        "",
        _TextSubclass("LONG"),
        None,
    ],
)
def test_invalid_sides_are_rejected(side):
    values = _kwargs()
    values["side"] = side
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


@pytest.mark.parametrize(
    "generation_id",
    [
        "A",
        "structure.1",
        "structure_1",
        "structure:1",
        "structure+1",
        "structure-1",
        "a" * 128,
    ],
)
def test_safe_structure_generation_ids_are_accepted(
    generation_id,
):
    assert (
        _build(
            structure_generation_id=generation_id
        ).structure_generation_id
        == generation_id
    )


@pytest.mark.parametrize(
    "generation_id",
    [
        "",
        "structure/1",
        "structure 1",
        "structure\t1",
        "structure\n1",
        "a" * 129,
        _TextSubclass("structure:1"),
        None,
    ],
)
def test_unsafe_structure_generation_ids_are_rejected(
    generation_id,
):
    values = _kwargs()
    values["structure_generation_id"] = generation_id
    _assert_invalid(
        lambda: build_e3_golden_zone_geometry(**values)
    )


def test_deterministic_replay_has_identical_mapping_and_hash():
    first = _build()
    second = _build()
    assert first is not second
    assert first == second
    assert first.to_mapping() == second.to_mapping()
    assert first.geometry_sha256 == second.geometry_sha256


def test_mapping_round_trip_reconstructs_same_result():
    result = _build()
    reconstructed = E3GoldenZoneGeometryV1(
        **result.to_mapping()
    )
    assert reconstructed == result
    assert reconstructed.to_mapping() == result.to_mapping()


def test_mapping_is_detached():
    result = _build()
    mapping = result.to_mapping()
    mapping["mode"] = "INTRADAY"
    assert result.mode == "SWING"


def test_supplied_geometry_hash_corruption_is_rejected():
    mapping = _build().to_mapping()
    mapping["geometry_sha256"] = "0" * 64
    _assert_invalid(
        lambda: E3GoldenZoneGeometryV1(**mapping)
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "wrong"),
        ("policy_version", "wrong"),
        ("mode_profile_version", "wrong"),
        ("mode_lineage_sha256", "a" * 64),
        ("structure_timeframe", "4h"),
        ("shallow_retracement_milli", 619),
        ("deep_retracement_milli", 787),
        ("golden_zone_low_tick", 1213),
        ("golden_zone_high_tick", 1383),
        ("stop_loss_tick", 999),
    ],
)
def test_direct_constructor_corruption_fails_closed(field, value):
    mapping = _build().to_mapping()
    mapping[field] = value
    mapping = _with_required_hash(mapping)
    _assert_invalid(
        lambda: E3GoldenZoneGeometryV1(**mapping)
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", _TextSubclass("e3-golden-zone-geometry-v1")),
        (
            "policy_version",
            _TextSubclass(
                "e3-golden-zone-geometry-policy-v1"
            ),
        ),
        ("golden_zone_low_tick", _IntSubclass(1214)),
        ("golden_zone_high_tick", True),
        ("stop_loss_tick", _IntSubclass(1000)),
        ("shallow_retracement_milli", True),
        ("deep_retracement_milli", _IntSubclass(786)),
        ("geometry_sha256", _TextSubclass("a" * 64)),
    ],
)
def test_direct_constructor_rejects_field_subclasses(
    field,
    value,
):
    mapping = _build().to_mapping()
    mapping[field] = value
    if field != "geometry_sha256":
        mapping = _with_required_hash(mapping)
    _assert_invalid(
        lambda: E3GoldenZoneGeometryV1(**mapping)
    )


@pytest.mark.parametrize(
    "variant",
    [
        {"canonical_symbol": "ETH/USDT:USDT"},
        {"structure_generation_id": "structure:BTC_USDT+02"},
        {
            "anchor_low_at": "2026-07-30T09:59:59Z",
        },
        {
            "anchor_low_tick": 900,
            "anchor_high_tick": 2000,
        },
        {"tick_size": "0.01"},
    ],
)
def test_hash_changes_for_valid_material_input_changes(variant):
    baseline = _build()
    changed = _build(**variant)
    assert changed.geometry_sha256 != baseline.geometry_sha256


def test_hash_changes_across_valid_modes_and_lineages():
    hashes = {
        _build(mode=mode).geometry_sha256
        for mode in ("SWING", "INTRADAY", "SCALP")
    }
    assert len(hashes) == 3


def test_hash_changes_across_valid_side_geometry_and_stop():
    long_result = _build(side="LONG")
    short_result = _build(side="SHORT")
    assert long_result.geometry_sha256 != short_result.geometry_sha256
    assert (
        long_result.golden_zone_low_tick
        != short_result.golden_zone_low_tick
    )
    assert long_result.stop_loss_tick != short_result.stop_loss_tick


@pytest.mark.parametrize(
    "field",
    [
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "side",
        "structure_generation_id",
        "anchor_low_at",
        "anchor_low_tick",
        "tick_size",
        "golden_zone_low_tick",
        "stop_loss_tick",
    ],
)
def test_every_material_field_participates_in_required_hash(field):
    mapping = _build().to_mapping()
    original_hash = mapping["geometry_sha256"]
    if field.endswith("_tick"):
        mapping[field] += 1
    elif field == "mode_lineage_sha256":
        mapping[field] = "f" * 64
    else:
        mapping[field] = str(mapping[field]) + "X"
    assert _required_hash(mapping) != original_hash


def test_all_invalid_builder_paths_have_same_sanitized_error():
    invalid_variants = [
        {"mode": "UNKNOWN"},
        {"mode_lineage_sha256": "0" * 64},
        {"canonical_symbol": "btc/usdt"},
        {"side": "BUY"},
        {"structure_generation_id": "bad/value"},
        {"anchor_low_at": "bad"},
        {"anchor_low_tick": 0},
        {"anchor_high_tick": 1000},
        {"tick_size": "1.0"},
    ]
    for variant in invalid_variants:
        values = _kwargs()
        values.update(variant)
        _assert_invalid(
            lambda values=values:
                build_e3_golden_zone_geometry(**values)
        )


def test_project_import_inventory_is_exact():
    tree = ast.parse(
        _SOURCE_PATH.read_text(encoding="utf-8")
    )
    project_imports = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("engine.")
        ):
            project_imports.append(
                (
                    node.module,
                    tuple(alias.name for alias in node.names),
                )
            )
    assert project_imports == [
        (
            "engine.mode_data_plan_v1",
            ("build_mode_audit_lineage",),
        ),
        (
            "engine.mode_profile_v1",
            ("ModeProfileV1", "get_mode_profile"),
        ),
    ]


def test_standard_library_import_inventory_is_bounded():
    tree = ast.parse(
        _SOURCE_PATH.read_text(encoding="utf-8")
    )
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and not node.module.startswith("engine.")
    }
    modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert modules == {
        "dataclasses",
        "datetime",
        "hashlib",
        "json",
        "re",
        "typing",
    }


def test_forbidden_imports_are_absent():
    source = _SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name.split(".")[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    forbidden = {
        "aiohttp",
        "asyncio",
        "ccxt",
        "httpx",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "time",
        "urllib",
    }
    assert imported.isdisjoint(forbidden)
    forbidden_project_tokens = {
        "golden_zone_fibonacci",
        "golden_zone_swing_resolver",
        "scanner",
        "executor",
        "composition",
        "lifecycle",
        "target",
        "binance",
        "cache",
        "production",
        "publication",
        "provider",
        "telegram",
        "exchange",
    }
    project_modules = {
        node.module.lower()
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("engine.")
    }
    assert all(
        token not in module
        for module in project_modules
        for token in forbidden_project_tokens
    )


def test_no_filesystem_network_clock_cache_or_retry_calls():
    tree = ast.parse(
        _SOURCE_PATH.read_text(encoding="utf-8")
    )
    call_names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            call_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            call_names.add(node.func.attr)
    forbidden = {
        "open",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
        "mkdir",
        "unlink",
        "replace",
        "now",
        "utcnow",
        "today",
        "sleep",
        "retry",
        "backoff",
        "get",
        "post",
        "fetch",
        "send",
        "publish",
    }
    assert call_names.isdisjoint(forbidden)


def test_no_async_thread_process_or_concurrency_structure():
    tree = ast.parse(
        _SOURCE_PATH.read_text(encoding="utf-8")
    )
    assert not any(
        isinstance(
            node,
            (
                ast.AsyncFunctionDef,
                ast.Await,
                ast.AsyncFor,
                ast.AsyncWith,
            ),
        )
        for node in ast.walk(tree)
    )


def test_no_module_global_mutable_execution_state():
    tree = ast.parse(
        _SOURCE_PATH.read_text(encoding="utf-8")
    )
    for node in tree.body:
        if isinstance(node, ast.Assign):
            assert not isinstance(
                node.value,
                (ast.Dict, ast.List, ast.Set),
            )
        elif isinstance(node, ast.AnnAssign):
            assert not isinstance(
                node.value,
                (ast.Dict, ast.List, ast.Set),
            )


def test_geometry_arithmetic_has_no_float_authority():
    source = _SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not any(
        isinstance(node, ast.Constant)
        and type(node.value) is float
        for node in ast.walk(tree)
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(tree)
    )
    geometry_function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_geometry"
    )
    operators = {
        type(node.op)
        for node in ast.walk(geometry_function)
        if isinstance(node, ast.BinOp)
    }
    assert operators <= {
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.FloorDiv,
    }
    assert ast.Div not in operators


def test_no_hardcoded_swing_fallback():
    source = _SOURCE_PATH.read_text(encoding="utf-8")
    assert '"SWING"' not in source
    assert "'SWING'" not in source


def test_result_has_no_later_slice_authority_fields():
    forbidden_fragments = (
        "target",
        "trigger",
        "quote",
        "lifecycle",
        "publication",
        "slot",
        "pair_lock",
    )
    assert all(
        all(fragment not in field for fragment in forbidden_fragments)
        for field in _FIELDS
    )


def test_exact_two_file_repository_mutation_inventory():
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert status == [
        "?? engine/e3_golden_zone_geometry_v1.py",
        "?? tests/test_e3_golden_zone_geometry_v1.py",
    ]
    assert subprocess.run(
        ["git", "diff", "--quiet"],
        cwd=_ROOT,
        check=False,
    ).returncode == 0
    assert subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=_ROOT,
        check=False,
    ).returncode == 0


def test_source_and_test_are_utf8_lf_and_ast_parseable():
    for path in (_SOURCE_PATH, _TEST_PATH):
        data = path.read_bytes()
        assert b"\r" not in data
        text = data.decode("utf-8", errors="strict")
        assert ast.parse(text)
        assert data.endswith(b"\n")
