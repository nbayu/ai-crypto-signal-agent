"""Detached immutable executable-side price snapshot evidence."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Final, NoReturn

from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
)


SCHEMA_VERSION: Final = "e3-executable-price-snapshot-v1"
POLICY_VERSION: Final = (
    "d3-executable-side-price-snapshot-v1"
)
VENUE_BINANCE_USDM: Final = "BINANCE_USDM"

_ERROR: Final = "invalid E3 executable price snapshot"
_GENERATION_PATTERN: Final = re.compile(
    r"[A-Za-z0-9._:+-]{1,128}"
)
_TIMESTAMP_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_TICK_SIZE_PATTERN: Final = re.compile(
    r"(?:[1-9][0-9]*|0\.[0-9]*[1-9]|"
    r"[1-9][0-9]*\.[0-9]*[1-9])"
)
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")

__all__ = (
    "E3ExecutablePriceSnapshotV1",
    "build_e3_executable_price_snapshot",
)


def _invalid() -> NoReturn:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError(_ERROR)


def _geometry(value: object) -> E3GoldenZoneGeometryV1:
    _require(type(value) is E3GoldenZoneGeometryV1)
    value.__post_init__()
    return value


def _exact_string(value: object) -> str:
    _require(type(value) is str)
    return value


def _venue(value: object) -> str:
    venue = _exact_string(value)
    _require(venue == VENUE_BINANCE_USDM)
    return venue


def _generation_id(value: object) -> str:
    generation_id = _exact_string(value)
    _require(
        _GENERATION_PATTERN.fullmatch(generation_id)
        is not None
    )
    return generation_id


def _timestamp(value: object) -> str:
    canonical = _exact_string(value)
    _require(_TIMESTAMP_PATTERN.fullmatch(canonical) is not None)
    parsed = datetime.strptime(
        canonical,
        "%Y-%m-%dT%H:%M:%SZ",
    )
    _require(
        parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
        == canonical
    )
    return canonical


def _positive_tick(value: object) -> int:
    _require(type(value) is int)
    _require(value > 0)
    return value


def _slippage(value: object) -> int:
    _require(type(value) is int)
    _require(0 <= value <= 10000)
    return value


def _tick_size(
    value: object,
    geometry: E3GoldenZoneGeometryV1,
) -> str:
    canonical = _exact_string(value)
    _require(_TICK_SIZE_PATTERN.fullmatch(canonical) is not None)
    _require(canonical == geometry.tick_size)
    return canonical


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
class E3ExecutablePriceSnapshotV1:
    schema_version: str
    policy_version: str
    geometry: E3GoldenZoneGeometryV1
    venue: str
    quote_generation_id: str
    exchange_timestamp: str
    best_bid_tick: int
    best_ask_tick: int
    last_price_tick: int
    mark_price_tick: int
    modeled_adverse_slippage_bps: int
    tick_size: str
    snapshot_sha256: str

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
            geometry = _geometry(self.geometry)
            _venue(self.venue)
            _generation_id(self.quote_generation_id)
            _timestamp(self.exchange_timestamp)
            bid_tick = _positive_tick(self.best_bid_tick)
            ask_tick = _positive_tick(self.best_ask_tick)
            _require(bid_tick < ask_tick)
            _positive_tick(self.last_price_tick)
            _positive_tick(self.mark_price_tick)
            _slippage(self.modeled_adverse_slippage_bps)
            _tick_size(self.tick_size, geometry)
            _require(
                type(self.snapshot_sha256) is str
                and _SHA256_PATTERN.fullmatch(
                    self.snapshot_sha256
                )
                is not None
            )
            mapping = self.to_mapping()
            supplied_hash = mapping.pop("snapshot_sha256")
            _require(supplied_hash == _hash_mapping(mapping))
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "geometry": self.geometry.to_mapping(),
            "venue": self.venue,
            "quote_generation_id": self.quote_generation_id,
            "exchange_timestamp": self.exchange_timestamp,
            "best_bid_tick": self.best_bid_tick,
            "best_ask_tick": self.best_ask_tick,
            "last_price_tick": self.last_price_tick,
            "mark_price_tick": self.mark_price_tick,
            "modeled_adverse_slippage_bps":
                self.modeled_adverse_slippage_bps,
            "tick_size": self.tick_size,
            "snapshot_sha256": self.snapshot_sha256,
        }


def build_e3_executable_price_snapshot(
    *,
    geometry: object,
    venue: object,
    quote_generation_id: object,
    exchange_timestamp: object,
    best_bid_tick: object,
    best_ask_tick: object,
    last_price_tick: object,
    mark_price_tick: object,
    modeled_adverse_slippage_bps: object,
    tick_size: object,
) -> E3ExecutablePriceSnapshotV1:
    try:
        canonical_geometry = _geometry(geometry)
        canonical_venue = _venue(venue)
        generation_id = _generation_id(
            quote_generation_id
        )
        timestamp = _timestamp(exchange_timestamp)
        bid_tick = _positive_tick(best_bid_tick)
        ask_tick = _positive_tick(best_ask_tick)
        _require(bid_tick < ask_tick)
        last_tick = _positive_tick(last_price_tick)
        mark_tick = _positive_tick(mark_price_tick)
        slippage_bps = _slippage(
            modeled_adverse_slippage_bps
        )
        canonical_tick_size = _tick_size(
            tick_size,
            canonical_geometry,
        )
        content: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "geometry": canonical_geometry,
            "venue": canonical_venue,
            "quote_generation_id": generation_id,
            "exchange_timestamp": timestamp,
            "best_bid_tick": bid_tick,
            "best_ask_tick": ask_tick,
            "last_price_tick": last_tick,
            "mark_price_tick": mark_tick,
            "modeled_adverse_slippage_bps":
                slippage_bps,
            "tick_size": canonical_tick_size,
        }
        hash_content = dict(content)
        hash_content["geometry"] = (
            canonical_geometry.to_mapping()
        )
        return E3ExecutablePriceSnapshotV1(
            **content,
            snapshot_sha256=_hash_mapping(hash_content),
        )
    except Exception:
        _invalid()
