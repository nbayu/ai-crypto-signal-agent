"""Immutable deterministic E4 thesis fingerprint evidence."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Final

from engine.canonical_pair_v1 import normalize_pair
from engine.e3_executable_price_snapshot_v1 import (
    E3ExecutablePriceSnapshotV1,
)
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
)
from engine.e3_mode_trigger_evidence_v1 import (
    E3ModeTriggerEvidenceV1,
)
from engine.e3_structural_targets_v1 import (
    E3StructuralTargetsV1,
)
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)


__all__ = (
    "THESIS_FINGERPRINT_VERSION",
    "THESIS_IDENTITY_FIELDS",
    "THESIS_EXCLUDED_FIELDS",
    "E4ThesisFingerprintV1",
    "build_e4_thesis_fingerprint",
)


THESIS_FINGERPRINT_VERSION: Final = "thesis-fingerprint-v1"

THESIS_IDENTITY_FIELDS: Final = (
    "venue",
    "canonical_pair",
    "mode",
    "side",
    "strategy_version",
    "mode_profile_version",
    "structure_timeframe",
    "structure_generation_id",
    "anchor_low_at",
    "anchor_low_tick",
    "anchor_high_at",
    "anchor_high_tick",
    "golden_zone_low_tick",
    "golden_zone_high_tick",
    "stop_loss_tick",
    "target_policy_version",
    "tp1_destination_id",
    "tp1_tick",
    "tp2_destination_id",
    "tp2_tick",
    "trigger_type",
    "trigger_timeframe",
    "trigger_generation_id",
    "trigger_candle_close_at",
)

THESIS_EXCLUDED_FIELDS: Final = (
    "signal_id",
    "delivery_id",
    "publication_timestamp",
    "telegram_message_id",
    "current_price",
    "score",
    "llm_result",
    "valid_until",
    "ledger_revision",
)


_ERROR: Final = "invalid E4 thesis fingerprint"
_MODES: Final = ("SWING", "INTRADAY", "SCALP")
_SIDES: Final = ("LONG", "SHORT")
_TIMESTAMP_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_TRIGGER_GENERATION_PATTERN: Final = re.compile(r"trg-[0-9a-f]{64}")
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_TIMESTAMP_FIELDS: Final = (
    "anchor_low_at",
    "anchor_high_at",
    "trigger_candle_close_at",
)
_TICK_FIELDS: Final = (
    "anchor_low_tick",
    "anchor_high_tick",
    "golden_zone_low_tick",
    "golden_zone_high_tick",
    "stop_loss_tick",
    "tp1_tick",
    "tp2_tick",
)
_STRING_FIELDS: Final = tuple(
    field for field in THESIS_IDENTITY_FIELDS if field not in _TICK_FIELDS
)


def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _timestamp(value: object) -> str:
    _require(type(value) is str)
    _require(_TIMESTAMP_PATTERN.fullmatch(value) is not None)
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return value


def _validate_identity_mapping(mapping: object) -> dict[str, object]:
    _require(type(mapping) is dict)
    identity = dict(mapping)
    _require(len(identity) == len(THESIS_IDENTITY_FIELDS))
    _require(set(identity) == set(THESIS_IDENTITY_FIELDS))

    for field in _STRING_FIELDS:
        value = identity[field]
        _require(type(value) is str)
        _require(bool(value.strip()))
    for field in _TICK_FIELDS:
        value = identity[field]
        _require(type(value) is int)
        _require(value > 0)

    _require(identity["venue"] == "BINANCE_USDM")
    _require(identity["mode"] in _MODES)
    _require(identity["side"] in _SIDES)
    canonical_pair = identity["canonical_pair"]
    _require(normalize_pair(canonical_pair) == canonical_pair)
    for field in _TIMESTAMP_FIELDS:
        _timestamp(identity[field])
    _require(
        _TRIGGER_GENERATION_PATTERN.fullmatch(identity["trigger_generation_id"])
        is not None
    )
    return {field: identity[field] for field in THESIS_IDENTITY_FIELDS}


def _canonical_identity_json(mapping: object) -> str:
    identity = _validate_identity_mapping(mapping)
    return json.dumps(
        {
            "fingerprint_version": THESIS_FINGERPRINT_VERSION,
            "identity": identity,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _identity_sha256(mapping: object) -> str:
    return sha256(_canonical_identity_json(mapping).encode("utf-8")).hexdigest()


def _validate_dependency(value: object, expected_type: type[object]) -> None:
    _require(type(value) is expected_type)
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class E4ThesisFingerprintV1:
    fingerprint_version: str
    venue: str
    canonical_pair: str
    mode: str
    side: str
    strategy_version: str
    mode_profile_version: str
    structure_timeframe: str
    structure_generation_id: str
    anchor_low_at: str
    anchor_low_tick: int
    anchor_high_at: str
    anchor_high_tick: int
    golden_zone_low_tick: int
    golden_zone_high_tick: int
    stop_loss_tick: int
    target_policy_version: str
    tp1_destination_id: str
    tp1_tick: int
    tp2_destination_id: str
    tp2_tick: int
    trigger_type: str
    trigger_timeframe: str
    trigger_generation_id: str
    trigger_candle_close_at: str
    identity_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.fingerprint_version) is str)
            _require(self.fingerprint_version == THESIS_FINGERPRINT_VERSION)
            identity = self.to_identity_mapping()
            _validate_identity_mapping(identity)
            _require(type(self.identity_sha256) is str)
            _require(_SHA256_PATTERN.fullmatch(self.identity_sha256) is not None)
            _require(self.identity_sha256 == _identity_sha256(identity))
        except Exception:
            _fail()

    def to_identity_mapping(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in THESIS_IDENTITY_FIELDS
        }

    def to_mapping(self) -> dict[str, object]:
        return {
            "fingerprint_version": self.fingerprint_version,
            **self.to_identity_mapping(),
            "identity_sha256": self.identity_sha256,
        }

    def canonical_identity_json(self) -> str:
        return _canonical_identity_json(self.to_identity_mapping())


def build_e4_thesis_fingerprint(
    *,
    geometry: object,
    structural_targets: object,
    executable_price_snapshot: object,
    mode_trigger_evidence: object,
    production_candidate_authority: object,
) -> E4ThesisFingerprintV1:
    try:
        _validate_dependency(geometry, E3GoldenZoneGeometryV1)
        _validate_dependency(structural_targets, E3StructuralTargetsV1)
        _validate_dependency(
            executable_price_snapshot,
            E3ExecutablePriceSnapshotV1,
        )
        _validate_dependency(mode_trigger_evidence, E3ModeTriggerEvidenceV1)
        _validate_dependency(
            production_candidate_authority,
            ProductionCandidateAuthorityV1,
        )

        _require(structural_targets.geometry is geometry)
        _require(executable_price_snapshot.geometry is geometry)
        _require(mode_trigger_evidence.geometry is geometry)
        _require(structural_targets.stop_loss_tick == geometry.stop_loss_tick)
        _require(executable_price_snapshot.tick_size == geometry.tick_size)
        _require(mode_trigger_evidence.mode == geometry.mode)
        _require(mode_trigger_evidence.mode_matches is True)
        _require(
            mode_trigger_evidence.mode_profile_policy_version
            == geometry.mode_profile_version
        )
        _require(
            mode_trigger_evidence.mode_lineage_sha256
            == geometry.mode_lineage_sha256
        )
        _require(mode_trigger_evidence.mode_lineage_matches is True)
        _require(
            mode_trigger_evidence.canonical_symbol
            == geometry.canonical_symbol
        )
        _require(mode_trigger_evidence.symbol_matches is True)
        _require(mode_trigger_evidence.side == geometry.side)
        _require(mode_trigger_evidence.side_matches is True)
        _require(
            mode_trigger_evidence.structure_timeframe
            == geometry.structure_timeframe
        )
        _require(mode_trigger_evidence.structure_timeframe_matches is True)
        _require(
            mode_trigger_evidence.structure_generation_id
            == geometry.structure_generation_id
        )
        _require(mode_trigger_evidence.structure_generation_matches is True)
        _require(mode_trigger_evidence.trigger_timeframe_matches is True)
        _require(mode_trigger_evidence.trigger_rule_matches is True)

        identity: dict[str, object] = {
            "venue": executable_price_snapshot.venue,
            "canonical_pair": normalize_pair(geometry.canonical_symbol),
            "mode": geometry.mode,
            "side": geometry.side,
            "strategy_version": production_candidate_authority.strategy_version,
            "mode_profile_version": geometry.mode_profile_version,
            "structure_timeframe": geometry.structure_timeframe,
            "structure_generation_id": geometry.structure_generation_id,
            "anchor_low_at": geometry.anchor_low_at,
            "anchor_low_tick": geometry.anchor_low_tick,
            "anchor_high_at": geometry.anchor_high_at,
            "anchor_high_tick": geometry.anchor_high_tick,
            "golden_zone_low_tick": geometry.golden_zone_low_tick,
            "golden_zone_high_tick": geometry.golden_zone_high_tick,
            "stop_loss_tick": geometry.stop_loss_tick,
            "target_policy_version": structural_targets.policy_version,
            "tp1_destination_id": structural_targets.tp1_destination_id,
            "tp1_tick": structural_targets.tp1_tick,
            "tp2_destination_id": structural_targets.tp2_destination_id,
            "tp2_tick": structural_targets.tp2_tick,
            "trigger_type": mode_trigger_evidence.trigger_rule,
            "trigger_timeframe": mode_trigger_evidence.trigger_timeframe,
            "trigger_generation_id": mode_trigger_evidence.trigger_generation_id,
            "trigger_candle_close_at": (
                mode_trigger_evidence.trigger_candle_close_at
            ),
        }
        canonical_identity = _validate_identity_mapping(identity)
        return E4ThesisFingerprintV1(
            fingerprint_version=THESIS_FINGERPRINT_VERSION,
            **canonical_identity,
            identity_sha256=_identity_sha256(canonical_identity),
        )
    except Exception:
        _fail()

