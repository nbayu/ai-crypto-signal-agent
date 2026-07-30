"""Detached immutable mode-bound Golden Zone geometry evidence."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Final, NoReturn

from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_profile_v1 import ModeProfileV1, get_mode_profile


SCHEMA_VERSION: Final = "e3-golden-zone-geometry-v1"
POLICY_VERSION: Final = "e3-golden-zone-geometry-policy-v1"
SHALLOW_RETRACEMENT_MILLI: Final = 618
DEEP_RETRACEMENT_MILLI: Final = 786
RETRACEMENT_DENOMINATOR: Final = 1000

_ERROR: Final = "invalid E3 Golden Zone geometry"
_SYMBOL_PATTERN: Final = re.compile(
    r"[A-Z0-9]{1,32}/[A-Z0-9]{1,32}:[A-Z0-9]{1,32}"
)
_GENERATION_PATTERN: Final = re.compile(r"[A-Za-z0-9._:+-]{1,128}")
_TIMESTAMP_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_TICK_SIZE_PATTERN: Final = re.compile(
    r"(?:[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])"
)
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")

__all__ = (
    "E3GoldenZoneGeometryV1",
    "build_e3_golden_zone_geometry",
)


def _invalid() -> NoReturn:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError(_ERROR)


def _exact_string(value: object) -> str:
    _require(type(value) is str)
    return value


def _profile(mode: object) -> ModeProfileV1:
    canonical_mode = _exact_string(mode)
    profile = get_mode_profile(canonical_mode)
    _require(type(profile) is ModeProfileV1)
    _require(profile.mode == canonical_mode)
    return profile


def _lineage(mode: str, supplied: object) -> str:
    value = _exact_string(supplied)
    lineage = build_mode_audit_lineage(mode)
    expected = lineage.lineage_sha256
    _require(type(expected) is str)
    _require(value == expected)
    return value


def _canonical_symbol(value: object) -> str:
    symbol = _exact_string(value)
    _require(_SYMBOL_PATTERN.fullmatch(symbol) is not None)
    return symbol


def _side(value: object) -> str:
    side = _exact_string(value)
    _require(side in ("LONG", "SHORT"))
    return side


def _generation_id(value: object) -> str:
    generation_id = _exact_string(value)
    _require(_GENERATION_PATTERN.fullmatch(generation_id) is not None)
    return generation_id


def _timestamp(value: object) -> tuple[str, datetime]:
    canonical = _exact_string(value)
    _require(_TIMESTAMP_PATTERN.fullmatch(canonical) is not None)
    parsed = datetime.strptime(canonical, "%Y-%m-%dT%H:%M:%SZ")
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == canonical)
    return canonical, parsed


def _tick(value: object) -> int:
    _require(type(value) is int)
    _require(value > 0)
    return value


def _tick_size(value: object) -> str:
    canonical = _exact_string(value)
    _require(_TICK_SIZE_PATTERN.fullmatch(canonical) is not None)
    return canonical


def _ceil_div(numerator: int, denominator: int) -> int:
    return -((-numerator) // denominator)


def _geometry(
    *,
    side: str,
    anchor_low_tick: int,
    anchor_high_tick: int,
) -> tuple[int, int, int]:
    span_ticks = anchor_high_tick - anchor_low_tick
    _require(span_ticks > 0)

    if side == "LONG":
        low_numerator = (
            anchor_high_tick * RETRACEMENT_DENOMINATOR
            - span_ticks * DEEP_RETRACEMENT_MILLI
        )
        high_numerator = (
            anchor_high_tick * RETRACEMENT_DENOMINATOR
            - span_ticks * SHALLOW_RETRACEMENT_MILLI
        )
        golden_zone_low_tick = _ceil_div(
            low_numerator,
            RETRACEMENT_DENOMINATOR,
        )
        golden_zone_high_tick = (
            high_numerator // RETRACEMENT_DENOMINATOR
        )
        stop_loss_tick = anchor_low_tick
    else:
        low_numerator = (
            anchor_low_tick * RETRACEMENT_DENOMINATOR
            + span_ticks * SHALLOW_RETRACEMENT_MILLI
        )
        high_numerator = (
            anchor_low_tick * RETRACEMENT_DENOMINATOR
            + span_ticks * DEEP_RETRACEMENT_MILLI
        )
        golden_zone_low_tick = _ceil_div(
            low_numerator,
            RETRACEMENT_DENOMINATOR,
        )
        golden_zone_high_tick = (
            high_numerator // RETRACEMENT_DENOMINATOR
        )
        stop_loss_tick = anchor_high_tick

    _require(
        anchor_low_tick
        < golden_zone_low_tick
        <= golden_zone_high_tick
        < anchor_high_tick
    )
    if side == "LONG":
        _require(stop_loss_tick < golden_zone_low_tick)
    else:
        _require(stop_loss_tick > golden_zone_high_tick)

    return (
        golden_zone_low_tick,
        golden_zone_high_tick,
        stop_loss_tick,
    )


def _canonical_json(mapping: dict[str, object]) -> bytes:
    return json.dumps(
        mapping,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _hash_mapping(mapping: dict[str, object]) -> str:
    return sha256(_canonical_json(mapping)).hexdigest()


@dataclass(frozen=True, slots=True)
class E3GoldenZoneGeometryV1:
    schema_version: str
    policy_version: str
    mode: str
    mode_profile_version: str
    mode_lineage_sha256: str
    canonical_symbol: str
    side: str
    structure_timeframe: str
    structure_generation_id: str
    anchor_low_at: str
    anchor_low_tick: int
    anchor_high_at: str
    anchor_high_tick: int
    tick_size: str
    shallow_retracement_milli: int
    deep_retracement_milli: int
    golden_zone_low_tick: int
    golden_zone_high_tick: int
    stop_loss_tick: int
    geometry_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                type(self.schema_version) is str
                and self.schema_version == SCHEMA_VERSION
            )
            _require(
                type(self.policy_version) is str
                and self.policy_version == POLICY_VERSION
            )
            profile = _profile(self.mode)
            _require(
                type(self.mode_profile_version) is str
                and self.mode_profile_version == profile.policy_version
            )
            _lineage(profile.mode, self.mode_lineage_sha256)
            _canonical_symbol(self.canonical_symbol)
            canonical_side = _side(self.side)
            _require(
                type(self.structure_timeframe) is str
                and self.structure_timeframe
                == profile.structure_timeframe
            )
            _generation_id(self.structure_generation_id)
            _low_at, low_timestamp = _timestamp(
                self.anchor_low_at
            )
            _high_at, high_timestamp = _timestamp(
                self.anchor_high_at
            )
            _require(low_timestamp != high_timestamp)
            if canonical_side == "LONG":
                _require(low_timestamp < high_timestamp)
            else:
                _require(high_timestamp < low_timestamp)

            low_tick = _tick(self.anchor_low_tick)
            high_tick = _tick(self.anchor_high_tick)
            _require(low_tick < high_tick)
            _tick_size(self.tick_size)
            _require(
                type(self.shallow_retracement_milli) is int
                and self.shallow_retracement_milli
                == SHALLOW_RETRACEMENT_MILLI
            )
            _require(
                type(self.deep_retracement_milli) is int
                and self.deep_retracement_milli
                == DEEP_RETRACEMENT_MILLI
            )

            expected_low, expected_high, expected_stop = (
                _geometry(
                    side=canonical_side,
                    anchor_low_tick=low_tick,
                    anchor_high_tick=high_tick,
                )
            )
            _require(
                type(self.golden_zone_low_tick) is int
                and self.golden_zone_low_tick == expected_low
            )
            _require(
                type(self.golden_zone_high_tick) is int
                and self.golden_zone_high_tick == expected_high
            )
            _require(
                type(self.stop_loss_tick) is int
                and self.stop_loss_tick == expected_stop
            )
            _require(
                type(self.geometry_sha256) is str
                and _SHA256_PATTERN.fullmatch(
                    self.geometry_sha256
                )
                is not None
            )
            mapping = self.to_mapping()
            supplied_hash = mapping.pop("geometry_sha256")
            _require(
                supplied_hash == _hash_mapping(mapping)
            )
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "mode_profile_version":
                self.mode_profile_version,
            "mode_lineage_sha256":
                self.mode_lineage_sha256,
            "canonical_symbol": self.canonical_symbol,
            "side": self.side,
            "structure_timeframe":
                self.structure_timeframe,
            "structure_generation_id":
                self.structure_generation_id,
            "anchor_low_at": self.anchor_low_at,
            "anchor_low_tick": self.anchor_low_tick,
            "anchor_high_at": self.anchor_high_at,
            "anchor_high_tick": self.anchor_high_tick,
            "tick_size": self.tick_size,
            "shallow_retracement_milli":
                self.shallow_retracement_milli,
            "deep_retracement_milli":
                self.deep_retracement_milli,
            "golden_zone_low_tick":
                self.golden_zone_low_tick,
            "golden_zone_high_tick":
                self.golden_zone_high_tick,
            "stop_loss_tick": self.stop_loss_tick,
            "geometry_sha256": self.geometry_sha256,
        }


def build_e3_golden_zone_geometry(
    *,
    mode: object,
    mode_lineage_sha256: object,
    canonical_symbol: object,
    side: object,
    structure_generation_id: object,
    anchor_low_at: object,
    anchor_low_tick: object,
    anchor_high_at: object,
    anchor_high_tick: object,
    tick_size: object,
) -> E3GoldenZoneGeometryV1:
    try:
        profile = _profile(mode)
        lineage = _lineage(
            profile.mode,
            mode_lineage_sha256,
        )
        symbol = _canonical_symbol(canonical_symbol)
        canonical_side = _side(side)
        generation_id = _generation_id(
            structure_generation_id
        )
        low_at, low_timestamp = _timestamp(anchor_low_at)
        high_at, high_timestamp = _timestamp(anchor_high_at)
        _require(low_timestamp != high_timestamp)
        if canonical_side == "LONG":
            _require(low_timestamp < high_timestamp)
        else:
            _require(high_timestamp < low_timestamp)

        low_tick = _tick(anchor_low_tick)
        high_tick = _tick(anchor_high_tick)
        _require(low_tick < high_tick)
        canonical_tick_size = _tick_size(tick_size)
        zone_low, zone_high, stop_tick = _geometry(
            side=canonical_side,
            anchor_low_tick=low_tick,
            anchor_high_tick=high_tick,
        )
        content: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "mode": profile.mode,
            "mode_profile_version": profile.policy_version,
            "mode_lineage_sha256": lineage,
            "canonical_symbol": symbol,
            "side": canonical_side,
            "structure_timeframe":
                profile.structure_timeframe,
            "structure_generation_id": generation_id,
            "anchor_low_at": low_at,
            "anchor_low_tick": low_tick,
            "anchor_high_at": high_at,
            "anchor_high_tick": high_tick,
            "tick_size": canonical_tick_size,
            "shallow_retracement_milli":
                SHALLOW_RETRACEMENT_MILLI,
            "deep_retracement_milli":
                DEEP_RETRACEMENT_MILLI,
            "golden_zone_low_tick": zone_low,
            "golden_zone_high_tick": zone_high,
            "stop_loss_tick": stop_tick,
        }
        return E3GoldenZoneGeometryV1(
            **content,
            geometry_sha256=_hash_mapping(content),
        )
    except Exception:
        _invalid()
