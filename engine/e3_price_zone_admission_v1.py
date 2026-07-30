"""Detached immutable fresh-price Golden Zone admission evidence."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Final, NoReturn

from engine.e3_executable_price_snapshot_v1 import (
    E3ExecutablePriceSnapshotV1,
)
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
)


SCHEMA_VERSION: Final = "e3-price-zone-admission-v1"
POLICY_VERSION: Final = (
    "d3-fresh-executable-side-price-admission-v1"
)

DECISION_PASS: Final = "PASS_PRICE_ADMISSION"
DECISION_HOLD: Final = "HOLD_PRICE_ADMISSION"
REASON_PASS: Final = "PASS_PRICE_ADMISSION"
REASON_STALE: Final = "HOLD_PRICE_STALE"
REASON_SPREAD: Final = "HOLD_PRICE_SPREAD"
REASON_SLIPPAGE: Final = "HOLD_PRICE_SLIPPAGE"
REASON_OUTSIDE_ZONE: Final = "HOLD_PRICE_OUTSIDE_ZONE"

EXECUTABLE_SOURCE_BEST_ASK: Final = "BEST_ASK"
EXECUTABLE_SOURCE_BEST_BID: Final = "BEST_BID"
ZONE_BOUNDARY_TOLERANCE_TICKS: Final = 0

SWING_MAX_QUOTE_AGE_SECONDS: Final = 15
SWING_MAX_SPREAD_BPS: Final = 20
SWING_MAX_SLIPPAGE_BPS: Final = 10
INTRADAY_MAX_QUOTE_AGE_SECONDS: Final = 10
INTRADAY_MAX_SPREAD_BPS: Final = 12
INTRADAY_MAX_SLIPPAGE_BPS: Final = 6
SCALP_MAX_QUOTE_AGE_SECONDS: Final = 3
SCALP_MAX_SPREAD_BPS: Final = 6
SCALP_MAX_SLIPPAGE_BPS: Final = 3

_ERROR: Final = "invalid E3 price-zone admission"
_TIMESTAMP_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")

__all__ = (
    "E3PriceZoneAdmissionV1",
    "build_e3_price_zone_admission",
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


def _snapshot(value: object) -> E3ExecutablePriceSnapshotV1:
    _require(type(value) is E3ExecutablePriceSnapshotV1)
    value.__post_init__()
    return value


def _timestamp(value: object) -> tuple[str, datetime]:
    _require(type(value) is str)
    _require(_TIMESTAMP_PATTERN.fullmatch(value) is not None)
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    _require(
        parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value
    )
    return value, parsed


def _mode_limits(mode: str) -> tuple[int, int, int]:
    if mode == "SWING":
        return (
            SWING_MAX_QUOTE_AGE_SECONDS,
            SWING_MAX_SPREAD_BPS,
            SWING_MAX_SLIPPAGE_BPS,
        )
    if mode == "INTRADAY":
        return (
            INTRADAY_MAX_QUOTE_AGE_SECONDS,
            INTRADAY_MAX_SPREAD_BPS,
            INTRADAY_MAX_SLIPPAGE_BPS,
        )
    if mode == "SCALP":
        return (
            SCALP_MAX_QUOTE_AGE_SECONDS,
            SCALP_MAX_SPREAD_BPS,
            SCALP_MAX_SLIPPAGE_BPS,
        )
    _require(False)
    raise ValueError(_ERROR)


def _derived_values(
    *,
    geometry: E3GoldenZoneGeometryV1,
    snapshot: E3ExecutablePriceSnapshotV1,
    evaluation_timestamp: object,
) -> tuple[
    str,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    bool,
    bool,
    bool,
    bool,
    str,
    str,
]:
    _evaluation, evaluation_at = _timestamp(
        evaluation_timestamp
    )
    _exchange, exchange_at = _timestamp(
        snapshot.exchange_timestamp
    )
    _require(evaluation_at >= exchange_at)
    age = evaluation_at - exchange_at
    _require(age.microseconds == 0)
    quote_age_seconds = age.days * 86400 + age.seconds

    max_age, max_spread, max_slippage = _mode_limits(
        geometry.mode
    )
    if geometry.side == "LONG":
        price_source = EXECUTABLE_SOURCE_BEST_ASK
        price_tick = snapshot.best_ask_tick
    else:
        price_source = EXECUTABLE_SOURCE_BEST_BID
        price_tick = snapshot.best_bid_tick

    spread_numerator = (
        snapshot.best_ask_tick - snapshot.best_bid_tick
    ) * 20000
    spread_denominator = (
        snapshot.best_ask_tick + snapshot.best_bid_tick
    )
    _require(spread_numerator > 0)
    _require(spread_denominator > 0)

    zone_low = geometry.golden_zone_low_tick
    zone_high = geometry.golden_zone_high_tick
    age_within = quote_age_seconds <= max_age
    spread_within = (
        spread_numerator
        <= max_spread * spread_denominator
    )
    slippage_within = (
        snapshot.modeled_adverse_slippage_bps
        <= max_slippage
    )
    inside_zone = zone_low <= price_tick <= zone_high

    if not age_within:
        decision = DECISION_HOLD
        reason = REASON_STALE
    elif not spread_within:
        decision = DECISION_HOLD
        reason = REASON_SPREAD
    elif not slippage_within:
        decision = DECISION_HOLD
        reason = REASON_SLIPPAGE
    elif not inside_zone:
        decision = DECISION_HOLD
        reason = REASON_OUTSIDE_ZONE
    else:
        decision = DECISION_PASS
        reason = REASON_PASS

    return (
        price_source,
        price_tick,
        quote_age_seconds,
        spread_numerator,
        spread_denominator,
        snapshot.modeled_adverse_slippage_bps,
        max_age,
        max_spread,
        max_slippage,
        zone_low,
        zone_high,
        ZONE_BOUNDARY_TOLERANCE_TICKS,
        age_within,
        spread_within,
        slippage_within,
        inside_zone,
        decision,
        reason,
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
class E3PriceZoneAdmissionV1:
    schema_version: str
    policy_version: str
    geometry: E3GoldenZoneGeometryV1
    snapshot: E3ExecutablePriceSnapshotV1
    evaluation_timestamp: str
    executable_price_source: str
    executable_price_tick: int
    quote_age_seconds: int
    spread_bps_numerator: int
    spread_bps_denominator: int
    modeled_adverse_slippage_bps: int
    max_quote_age_seconds: int
    max_spread_bps: int
    max_slippage_bps: int
    zone_low_tick: int
    zone_high_tick: int
    zone_boundary_tolerance_ticks: int
    age_within_limit: bool
    spread_within_limit: bool
    slippage_within_limit: bool
    inside_zone: bool
    decision: str
    reason_code: str
    admission_sha256: str

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
            snapshot = _snapshot(self.snapshot)
            _require(snapshot.geometry is geometry)
            evaluation, _parsed = _timestamp(
                self.evaluation_timestamp
            )
            expected = _derived_values(
                geometry=geometry,
                snapshot=snapshot,
                evaluation_timestamp=evaluation,
            )
            values = (
                self.executable_price_source,
                self.executable_price_tick,
                self.quote_age_seconds,
                self.spread_bps_numerator,
                self.spread_bps_denominator,
                self.modeled_adverse_slippage_bps,
                self.max_quote_age_seconds,
                self.max_spread_bps,
                self.max_slippage_bps,
                self.zone_low_tick,
                self.zone_high_tick,
                self.zone_boundary_tolerance_ticks,
                self.age_within_limit,
                self.spread_within_limit,
                self.slippage_within_limit,
                self.inside_zone,
                self.decision,
                self.reason_code,
            )
            _require(values == expected)
            _require(
                type(self.executable_price_source) is str
            )
            _require(type(self.executable_price_tick) is int)
            _require(type(self.quote_age_seconds) is int)
            _require(type(self.spread_bps_numerator) is int)
            _require(type(self.spread_bps_denominator) is int)
            _require(
                type(self.modeled_adverse_slippage_bps) is int
            )
            _require(type(self.max_quote_age_seconds) is int)
            _require(type(self.max_spread_bps) is int)
            _require(type(self.max_slippage_bps) is int)
            _require(type(self.zone_low_tick) is int)
            _require(type(self.zone_high_tick) is int)
            _require(
                type(self.zone_boundary_tolerance_ticks) is int
            )
            _require(type(self.age_within_limit) is bool)
            _require(type(self.spread_within_limit) is bool)
            _require(type(self.slippage_within_limit) is bool)
            _require(type(self.inside_zone) is bool)
            _require(type(self.decision) is str)
            _require(type(self.reason_code) is str)
            _require(
                type(self.admission_sha256) is str
                and _SHA256_PATTERN.fullmatch(
                    self.admission_sha256
                )
                is not None
            )
            mapping = self.to_mapping()
            supplied_hash = mapping.pop("admission_sha256")
            _require(supplied_hash == _hash_mapping(mapping))
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "geometry": self.geometry.to_mapping(),
            "snapshot": self.snapshot.to_mapping(),
            "evaluation_timestamp":
                self.evaluation_timestamp,
            "executable_price_source":
                self.executable_price_source,
            "executable_price_tick":
                self.executable_price_tick,
            "quote_age_seconds": self.quote_age_seconds,
            "spread_bps_numerator":
                self.spread_bps_numerator,
            "spread_bps_denominator":
                self.spread_bps_denominator,
            "modeled_adverse_slippage_bps":
                self.modeled_adverse_slippage_bps,
            "max_quote_age_seconds":
                self.max_quote_age_seconds,
            "max_spread_bps": self.max_spread_bps,
            "max_slippage_bps": self.max_slippage_bps,
            "zone_low_tick": self.zone_low_tick,
            "zone_high_tick": self.zone_high_tick,
            "zone_boundary_tolerance_ticks":
                self.zone_boundary_tolerance_ticks,
            "age_within_limit": self.age_within_limit,
            "spread_within_limit":
                self.spread_within_limit,
            "slippage_within_limit":
                self.slippage_within_limit,
            "inside_zone": self.inside_zone,
            "decision": self.decision,
            "reason_code": self.reason_code,
            "admission_sha256": self.admission_sha256,
        }


def build_e3_price_zone_admission(
    *,
    geometry: object,
    snapshot: object,
    evaluation_timestamp: object,
) -> E3PriceZoneAdmissionV1:
    try:
        canonical_geometry = _geometry(geometry)
        canonical_snapshot = _snapshot(snapshot)
        _require(
            canonical_snapshot.geometry
            is canonical_geometry
        )
        evaluation, _parsed = _timestamp(
            evaluation_timestamp
        )
        derived = _derived_values(
            geometry=canonical_geometry,
            snapshot=canonical_snapshot,
            evaluation_timestamp=evaluation,
        )
        content: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "geometry": canonical_geometry,
            "snapshot": canonical_snapshot,
            "evaluation_timestamp": evaluation,
            "executable_price_source": derived[0],
            "executable_price_tick": derived[1],
            "quote_age_seconds": derived[2],
            "spread_bps_numerator": derived[3],
            "spread_bps_denominator": derived[4],
            "modeled_adverse_slippage_bps": derived[5],
            "max_quote_age_seconds": derived[6],
            "max_spread_bps": derived[7],
            "max_slippage_bps": derived[8],
            "zone_low_tick": derived[9],
            "zone_high_tick": derived[10],
            "zone_boundary_tolerance_ticks": derived[11],
            "age_within_limit": derived[12],
            "spread_within_limit": derived[13],
            "slippage_within_limit": derived[14],
            "inside_zone": derived[15],
            "decision": derived[16],
            "reason_code": derived[17],
        }
        hash_content = dict(content)
        hash_content["geometry"] = (
            canonical_geometry.to_mapping()
        )
        hash_content["snapshot"] = (
            canonical_snapshot.to_mapping()
        )
        return E3PriceZoneAdmissionV1(
            **content,
            admission_sha256=_hash_mapping(hash_content),
        )
    except Exception:
        _invalid()
