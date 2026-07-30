"""Detached immutable structural target evidence."""

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Final, NoReturn

from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
)


SCHEMA_VERSION: Final = "e3-structural-targets-v1"
POLICY_VERSION: Final = "structure-destination-targets-v1"
DESTINATION_KIND_STRUCTURE: Final = "STRUCTURE"
DESTINATION_KIND_LIQUIDITY: Final = "LIQUIDITY"
MAX_DESTINATION_EVIDENCE_COUNT: Final = 256

_ERROR: Final = "invalid E3 structural targets"
_DESTINATION_ID_PATTERN: Final = re.compile(
    r"[A-Za-z0-9._:+-]{1,128}"
)
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")

__all__ = (
    "E3StructuralTargetsV1",
    "build_e3_structural_targets",
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


def _destination_kind(value: object) -> str:
    kind = _exact_string(value)
    _require(
        kind
        in (
            DESTINATION_KIND_STRUCTURE,
            DESTINATION_KIND_LIQUIDITY,
        )
    )
    return kind


def _destination_id(value: object) -> str:
    destination_id = _exact_string(value)
    _require(
        _DESTINATION_ID_PATTERN.fullmatch(destination_id)
        is not None
    )
    return destination_id


def _positive_tick(value: object) -> int:
    _require(type(value) is int)
    _require(value > 0)
    return value


def _same_string(value: object, expected: str) -> str:
    candidate = _exact_string(value)
    _require(candidate == expected)
    return candidate


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


def _selected_values(
    *,
    geometry: E3GoldenZoneGeometryV1,
    tp1_kind: object,
    tp1_id: object,
    tp1_tick: object,
    tp2_kind: object,
    tp2_id: object,
    tp2_tick: object,
) -> tuple[
    int,
    int,
    int,
    str,
    str,
    int,
    int,
    str,
    str,
    int,
    int,
]:
    first_kind = _destination_kind(tp1_kind)
    first_id = _destination_id(tp1_id)
    first_tick = _positive_tick(tp1_tick)
    second_kind = _destination_kind(tp2_kind)
    second_id = _destination_id(tp2_id)
    second_tick = _positive_tick(tp2_tick)
    _require(first_id != second_id)
    _require(first_tick != second_tick)

    stop_tick = geometry.stop_loss_tick
    if geometry.side == "LONG":
        worst_entry_tick = geometry.golden_zone_high_tick
        _require(
            stop_tick
            < worst_entry_tick
            < first_tick
            < second_tick
        )
        risk_ticks = worst_entry_tick - stop_tick
        first_reward = first_tick - worst_entry_tick
        second_reward = second_tick - worst_entry_tick
    else:
        worst_entry_tick = geometry.golden_zone_low_tick
        _require(
            stop_tick
            > worst_entry_tick
            > first_tick
            > second_tick
        )
        risk_ticks = stop_tick - worst_entry_tick
        first_reward = worst_entry_tick - first_tick
        second_reward = worst_entry_tick - second_tick

    _require(risk_ticks > 0)
    _require(first_reward > 0)
    _require(second_reward > first_reward)
    return (
        worst_entry_tick,
        stop_tick,
        risk_ticks,
        first_kind,
        first_id,
        first_tick,
        first_reward,
        second_kind,
        second_id,
        second_tick,
        second_reward,
    )


def _ordered_evidence(
    *,
    geometry: E3GoldenZoneGeometryV1,
    value: object,
) -> tuple[tuple[object, ...], ...]:
    _require(type(value) is tuple)
    _require(2 <= len(value) <= MAX_DESTINATION_EVIDENCE_COUNT)
    seen_ids: list[str] = []
    seen_ticks: list[int] = []
    previous_tick: int | None = None

    for record in value:
        _require(type(record) is tuple)
        _require(len(record) == 5)
        kind = _destination_kind(record[0])
        destination_id = _destination_id(record[1])
        destination_tick = _positive_tick(record[2])
        _same_string(
            record[3],
            geometry.structure_timeframe,
        )
        _same_string(
            record[4],
            geometry.structure_generation_id,
        )
        _require(destination_id not in seen_ids)
        _require(destination_tick not in seen_ticks)
        if geometry.side == "LONG":
            _require(
                destination_tick
                > geometry.golden_zone_high_tick
            )
            if previous_tick is not None:
                _require(destination_tick > previous_tick)
        else:
            _require(
                destination_tick
                < geometry.golden_zone_low_tick
            )
            if previous_tick is not None:
                _require(destination_tick < previous_tick)
        seen_ids.append(destination_id)
        seen_ticks.append(destination_tick)
        previous_tick = destination_tick
        _require(
            kind
            in (
                DESTINATION_KIND_STRUCTURE,
                DESTINATION_KIND_LIQUIDITY,
            )
        )

    return value


@dataclass(frozen=True, slots=True)
class E3StructuralTargetsV1:
    schema_version: str
    policy_version: str
    geometry: E3GoldenZoneGeometryV1
    worst_entry_tick: int
    stop_loss_tick: int
    risk_distance_ticks: int
    tp1_destination_kind: str
    tp1_destination_id: str
    tp1_tick: int
    tp1_reward_ticks: int
    tp1_rr_numerator: int
    tp1_rr_denominator: int
    tp2_destination_kind: str
    tp2_destination_id: str
    tp2_tick: int
    tp2_reward_ticks: int
    tp2_rr_numerator: int
    tp2_rr_denominator: int
    targets_sha256: str

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
            selected = _selected_values(
                geometry=geometry,
                tp1_kind=self.tp1_destination_kind,
                tp1_id=self.tp1_destination_id,
                tp1_tick=self.tp1_tick,
                tp2_kind=self.tp2_destination_kind,
                tp2_id=self.tp2_destination_id,
                tp2_tick=self.tp2_tick,
            )
            _require(
                type(self.worst_entry_tick) is int
                and self.worst_entry_tick == selected[0]
            )
            _require(
                type(self.stop_loss_tick) is int
                and self.stop_loss_tick == selected[1]
            )
            _require(
                type(self.risk_distance_ticks) is int
                and self.risk_distance_ticks == selected[2]
            )
            _require(self.tp1_destination_kind == selected[3])
            _require(self.tp1_destination_id == selected[4])
            _require(self.tp1_tick == selected[5])
            _require(
                type(self.tp1_reward_ticks) is int
                and self.tp1_reward_ticks == selected[6]
            )
            _require(
                type(self.tp1_rr_numerator) is int
                and self.tp1_rr_numerator == selected[6]
            )
            _require(
                type(self.tp1_rr_denominator) is int
                and self.tp1_rr_denominator == selected[2]
            )
            _require(self.tp2_destination_kind == selected[7])
            _require(self.tp2_destination_id == selected[8])
            _require(self.tp2_tick == selected[9])
            _require(
                type(self.tp2_reward_ticks) is int
                and self.tp2_reward_ticks == selected[10]
            )
            _require(
                type(self.tp2_rr_numerator) is int
                and self.tp2_rr_numerator == selected[10]
            )
            _require(
                type(self.tp2_rr_denominator) is int
                and self.tp2_rr_denominator == selected[2]
            )
            _require(
                type(self.targets_sha256) is str
                and _SHA256_PATTERN.fullmatch(
                    self.targets_sha256
                )
                is not None
            )
            mapping = self.to_mapping()
            supplied_hash = mapping.pop("targets_sha256")
            _require(supplied_hash == _hash_mapping(mapping))
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "geometry": self.geometry.to_mapping(),
            "worst_entry_tick": self.worst_entry_tick,
            "stop_loss_tick": self.stop_loss_tick,
            "risk_distance_ticks": self.risk_distance_ticks,
            "tp1_destination_kind":
                self.tp1_destination_kind,
            "tp1_destination_id": self.tp1_destination_id,
            "tp1_tick": self.tp1_tick,
            "tp1_reward_ticks": self.tp1_reward_ticks,
            "tp1_rr_numerator": self.tp1_rr_numerator,
            "tp1_rr_denominator":
                self.tp1_rr_denominator,
            "tp2_destination_kind":
                self.tp2_destination_kind,
            "tp2_destination_id": self.tp2_destination_id,
            "tp2_tick": self.tp2_tick,
            "tp2_reward_ticks": self.tp2_reward_ticks,
            "tp2_rr_numerator": self.tp2_rr_numerator,
            "tp2_rr_denominator":
                self.tp2_rr_denominator,
            "targets_sha256": self.targets_sha256,
        }


def build_e3_structural_targets(
    *,
    geometry: object,
    ordered_destinations: object,
) -> E3StructuralTargetsV1:
    try:
        canonical_geometry = _geometry(geometry)
        records = _ordered_evidence(
            geometry=canonical_geometry,
            value=ordered_destinations,
        )
        first = records[0]
        second = records[1]
        selected = _selected_values(
            geometry=canonical_geometry,
            tp1_kind=first[0],
            tp1_id=first[1],
            tp1_tick=first[2],
            tp2_kind=second[0],
            tp2_id=second[1],
            tp2_tick=second[2],
        )
        content: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "geometry": canonical_geometry,
            "worst_entry_tick": selected[0],
            "stop_loss_tick": selected[1],
            "risk_distance_ticks": selected[2],
            "tp1_destination_kind": selected[3],
            "tp1_destination_id": selected[4],
            "tp1_tick": selected[5],
            "tp1_reward_ticks": selected[6],
            "tp1_rr_numerator": selected[6],
            "tp1_rr_denominator": selected[2],
            "tp2_destination_kind": selected[7],
            "tp2_destination_id": selected[8],
            "tp2_tick": selected[9],
            "tp2_reward_ticks": selected[10],
            "tp2_rr_numerator": selected[10],
            "tp2_rr_denominator": selected[2],
        }
        hash_content = dict(content)
        hash_content["geometry"] = (
            canonical_geometry.to_mapping()
        )
        return E3StructuralTargetsV1(
            **content,
            targets_sha256=_hash_mapping(hash_content),
        )
    except Exception:
        _invalid()
