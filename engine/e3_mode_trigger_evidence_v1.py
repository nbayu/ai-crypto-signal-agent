from dataclasses import dataclass, fields
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Final

from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
)
from engine.mode_profile_v1 import (
    MODE_PROFILE_POLICY_VERSION,
    ModeProfileV1,
    get_mode_profile,
)


__all__ = (
    "E3ModeTriggerEvidenceV1",
    "build_e3_mode_trigger_evidence",
)

_SCHEMA_VERSION: Final[str] = "e3-mode-trigger-evidence-v1"
_POLICY_VERSION: Final[str] = "d4-mode-trigger-evidence-v1"
_TRIGGER_GENERATION_POLICY_VERSION: Final[str] = "trigger-generation-v1"
_DECISION_PASS: Final[str] = "PASS_TRIGGER_EVIDENCE"
_DECISION_HOLD: Final[str] = "HOLD_TRIGGER_EVIDENCE"
_REASON_PASS: Final[str] = "PASS_TRIGGER_EVIDENCE"
_REASON_MODE: Final[str] = "HOLD_TRIGGER_MODE_MISMATCH"
_REASON_MODE_LINEAGE: Final[str] = "HOLD_TRIGGER_MODE_LINEAGE_MISMATCH"
_REASON_SYMBOL: Final[str] = "HOLD_TRIGGER_SYMBOL_MISMATCH"
_REASON_SIDE: Final[str] = "HOLD_TRIGGER_SIDE_MISMATCH"
_REASON_STRUCTURE_TIMEFRAME: Final[str] = "HOLD_TRIGGER_STRUCTURE_TIMEFRAME_MISMATCH"
_REASON_STRUCTURE_GENERATION: Final[str] = "HOLD_TRIGGER_STRUCTURE_GENERATION_MISMATCH"
_REASON_TRIGGER_TIMEFRAME: Final[str] = "HOLD_TRIGGER_TIMEFRAME_MISMATCH"
_REASON_TRIGGER_RULE: Final[str] = "HOLD_TRIGGER_RULE_MISMATCH"
_REASON_UNCLOSED: Final[str] = "HOLD_TRIGGER_CANDLE_UNCLOSED"
_REASON_UNCONFIRMED: Final[str] = "HOLD_TRIGGER_RULE_UNCONFIRMED"
_REASON_CLOSE_ALIGNMENT: Final[str] = "HOLD_TRIGGER_CLOSE_MISALIGNED"
_REASON_FUTURE: Final[str] = "HOLD_TRIGGER_FUTURE"
_REASON_STALE: Final[str] = "HOLD_TRIGGER_STALE"
_ERROR: Final[str] = "invalid E3 mode trigger evidence"
_TIMESTAMP_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%SZ"
_ALLOWED_MODES: Final[tuple[str, ...]] = ("SWING", "INTRADAY", "SCALP")
_ALLOWED_SIDES: Final[tuple[str, ...]] = ("LONG", "SHORT")
_ALLOWED_TIMEFRAMES: Final[tuple[str, ...]] = (
    "1w",
    "1d",
    "4h",
    "1h",
    "15m",
    "5m",
    "3m",
)
_SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
_TRIGGER_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"trg-[0-9a-f]{64}")
_SYMBOL_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._:/+-]{1,64}")
_GENERATION_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._:+-]{1,128}")
_TIMESTAMP_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError(_ERROR) from None


def _canonical_sha256(mapping: dict[str, object]) -> str:
    encoded = json.dumps(
        mapping,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return sha256(encoded).hexdigest()


def _geometry(value: object) -> E3GoldenZoneGeometryV1:
    _require(type(value) is E3GoldenZoneGeometryV1)
    value.__post_init__()
    return value


def _profile_binding(mode: str) -> tuple[str, str, str, int, int]:
    if mode == "SWING":
        return (
            "1h",
            "15m",
            "closed 15m BOS/CHOCH or reclaim aligned with 1h structure and 4h bias",
            900,
            15,
        )
    if mode == "INTRADAY":
        return (
            "15m",
            "5m",
            "closed 5m BOS/CHOCH or reclaim aligned with 15m structure and 1h bias",
            300,
            5,
        )
    if mode == "SCALP":
        return (
            "5m",
            "3m",
            "closed 3m liquidity sweep/reclaim followed by micro-BOS aligned with 5m structure and 15m bias",
            180,
            3,
        )
    raise ValueError(_ERROR) from None


def _profile(geometry: E3GoldenZoneGeometryV1) -> ModeProfileV1:
    profile = get_mode_profile(geometry.mode)
    _require(type(profile) is ModeProfileV1)
    profile.__post_init__()
    structure_timeframe, trigger_timeframe, trigger_rule, maximum_age, _ = (
        _profile_binding(geometry.mode)
    )
    _require(type(profile.policy_version) is str)
    _require(profile.policy_version == MODE_PROFILE_POLICY_VERSION)
    _require(profile.mode == geometry.mode)
    _require(profile.structure_timeframe == geometry.structure_timeframe)
    _require(profile.structure_timeframe == structure_timeframe)
    _require(profile.trigger_timeframe == trigger_timeframe)
    _require(profile.trigger_rule == trigger_rule)
    _require(profile.maximum_trigger_age_seconds == maximum_age)
    _require(profile.trigger_candle_closed_only is True)
    _require(profile.developing_candle_allowed is False)
    return profile


def _mode(value: object) -> str:
    _require(type(value) is str)
    _require(value in _ALLOWED_MODES)
    return value


def _lineage(value: object) -> str:
    _require(type(value) is str)
    _require(_SHA256_PATTERN.fullmatch(value) is not None)
    return value


def _symbol(value: object) -> str:
    _require(type(value) is str)
    _require(_SYMBOL_PATTERN.fullmatch(value) is not None)
    return value


def _side(value: object) -> str:
    _require(type(value) is str)
    _require(value in _ALLOWED_SIDES)
    return value


def _timeframe(value: object) -> str:
    _require(type(value) is str)
    _require(value in _ALLOWED_TIMEFRAMES)
    return value


def _generation(value: object) -> str:
    _require(type(value) is str)
    _require(_GENERATION_PATTERN.fullmatch(value) is not None)
    return value


def _trigger_rule(value: object) -> str:
    _require(type(value) is str)
    _require(1 <= len(value) <= 256)
    _require(value == value.strip())
    return value


def _timestamp(value: object) -> tuple[str, datetime]:
    _require(type(value) is str)
    _require(_TIMESTAMP_PATTERN.fullmatch(value) is not None)
    parsed = datetime.strptime(value, _TIMESTAMP_FORMAT)
    _require(parsed.strftime(_TIMESTAMP_FORMAT) == value)
    return value, parsed


def _closed_flag(value: object) -> bool:
    _require(type(value) is bool)
    return value


def _trigger_generation_id(
    *,
    geometry: E3GoldenZoneGeometryV1,
    mode: str,
    mode_lineage_sha256: str,
    canonical_symbol: str,
    side: str,
    structure_timeframe: str,
    structure_generation_id: str,
    trigger_timeframe: str,
    trigger_rule: str,
    trigger_candle_close_at: str,
) -> str:
    identity = {
        "trigger_generation_policy_version": _TRIGGER_GENERATION_POLICY_VERSION,
        "geometry_sha256": geometry.geometry_sha256,
        "mode_profile_policy_version": MODE_PROFILE_POLICY_VERSION,
        "mode": mode,
        "mode_lineage_sha256": mode_lineage_sha256,
        "canonical_symbol": canonical_symbol,
        "side": side,
        "structure_timeframe": structure_timeframe,
        "structure_generation_id": structure_generation_id,
        "trigger_timeframe": trigger_timeframe,
        "trigger_rule": trigger_rule,
        "trigger_candle_close_at": trigger_candle_close_at,
    }
    return "trg-" + _canonical_sha256(identity)


def _derived_values(
    *,
    geometry: E3GoldenZoneGeometryV1,
    profile: ModeProfileV1,
    mode: str,
    mode_lineage_sha256: str,
    canonical_symbol: str,
    side: str,
    structure_timeframe: str,
    structure_generation_id: str,
    trigger_timeframe: str,
    trigger_rule: str,
    trigger_candle_close_at: str,
    trigger_close: datetime,
    trigger_candle_closed: bool,
    trigger_rule_satisfied: bool,
    evaluation_at: datetime,
) -> dict[str, object]:
    _, _, _, maximum_age, alignment_minutes = _profile_binding(geometry.mode)
    delta = evaluation_at - trigger_close
    trigger_age_seconds = delta.days * 86400 + delta.seconds
    mode_matches = mode == geometry.mode
    mode_lineage_matches = mode_lineage_sha256 == geometry.mode_lineage_sha256
    symbol_matches = canonical_symbol == geometry.canonical_symbol
    side_matches = side == geometry.side
    structure_timeframe_matches = (
        structure_timeframe == geometry.structure_timeframe
        and structure_timeframe == profile.structure_timeframe
    )
    structure_generation_matches = (
        structure_generation_id == geometry.structure_generation_id
    )
    trigger_timeframe_matches = trigger_timeframe == profile.trigger_timeframe
    trigger_rule_matches = trigger_rule == profile.trigger_rule
    trigger_close_aligned = (
        trigger_close.second == 0
        and trigger_close.minute % alignment_minutes == 0
    )
    trigger_not_future = trigger_age_seconds >= 0
    trigger_fresh = (
        trigger_not_future
        and trigger_age_seconds <= profile.maximum_trigger_age_seconds
    )
    decision = _DECISION_PASS
    reason_code = _REASON_PASS
    if not mode_matches:
        decision = _DECISION_HOLD
        reason_code = _REASON_MODE
    elif not mode_lineage_matches:
        decision = _DECISION_HOLD
        reason_code = _REASON_MODE_LINEAGE
    elif not symbol_matches:
        decision = _DECISION_HOLD
        reason_code = _REASON_SYMBOL
    elif not side_matches:
        decision = _DECISION_HOLD
        reason_code = _REASON_SIDE
    elif not structure_timeframe_matches:
        decision = _DECISION_HOLD
        reason_code = _REASON_STRUCTURE_TIMEFRAME
    elif not structure_generation_matches:
        decision = _DECISION_HOLD
        reason_code = _REASON_STRUCTURE_GENERATION
    elif not trigger_timeframe_matches:
        decision = _DECISION_HOLD
        reason_code = _REASON_TRIGGER_TIMEFRAME
    elif not trigger_rule_matches:
        decision = _DECISION_HOLD
        reason_code = _REASON_TRIGGER_RULE
    elif not trigger_candle_closed:
        decision = _DECISION_HOLD
        reason_code = _REASON_UNCLOSED
    elif not trigger_rule_satisfied:
        decision = _DECISION_HOLD
        reason_code = _REASON_UNCONFIRMED
    elif not trigger_close_aligned:
        decision = _DECISION_HOLD
        reason_code = _REASON_CLOSE_ALIGNMENT
    elif not trigger_not_future:
        decision = _DECISION_HOLD
        reason_code = _REASON_FUTURE
    elif not trigger_fresh:
        decision = _DECISION_HOLD
        reason_code = _REASON_STALE
    generation_id = _trigger_generation_id(
        geometry=geometry,
        mode=mode,
        mode_lineage_sha256=mode_lineage_sha256,
        canonical_symbol=canonical_symbol,
        side=side,
        structure_timeframe=structure_timeframe,
        structure_generation_id=structure_generation_id,
        trigger_timeframe=trigger_timeframe,
        trigger_rule=trigger_rule,
        trigger_candle_close_at=trigger_candle_close_at,
    )
    return {
        "trigger_age_seconds": trigger_age_seconds,
        "maximum_trigger_age_seconds": maximum_age,
        "mode_matches": mode_matches,
        "mode_lineage_matches": mode_lineage_matches,
        "symbol_matches": symbol_matches,
        "side_matches": side_matches,
        "structure_timeframe_matches": structure_timeframe_matches,
        "structure_generation_matches": structure_generation_matches,
        "trigger_timeframe_matches": trigger_timeframe_matches,
        "trigger_rule_matches": trigger_rule_matches,
        "trigger_close_aligned": trigger_close_aligned,
        "trigger_not_future": trigger_not_future,
        "trigger_fresh": trigger_fresh,
        "decision": decision,
        "reason_code": reason_code,
        "trigger_generation_id": generation_id,
    }


@dataclass(frozen=True, slots=True)
class E3ModeTriggerEvidenceV1:
    schema_version: str
    policy_version: str
    trigger_generation_policy_version: str
    geometry: E3GoldenZoneGeometryV1
    mode_profile_policy_version: str
    mode: str
    mode_lineage_sha256: str
    canonical_symbol: str
    side: str
    structure_timeframe: str
    structure_generation_id: str
    trigger_timeframe: str
    trigger_rule: str
    trigger_candle_close_at: str
    trigger_candle_closed: bool
    trigger_rule_satisfied: bool
    evaluation_timestamp: str
    trigger_age_seconds: int
    maximum_trigger_age_seconds: int
    mode_matches: bool
    mode_lineage_matches: bool
    symbol_matches: bool
    side_matches: bool
    structure_timeframe_matches: bool
    structure_generation_matches: bool
    trigger_timeframe_matches: bool
    trigger_rule_matches: bool
    trigger_close_aligned: bool
    trigger_not_future: bool
    trigger_fresh: bool
    decision: str
    reason_code: str
    trigger_generation_id: str
    trigger_evidence_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.schema_version) is str)
            _require(self.schema_version == _SCHEMA_VERSION)
            _require(type(self.policy_version) is str)
            _require(self.policy_version == _POLICY_VERSION)
            _require(type(self.trigger_generation_policy_version) is str)
            _require(
                self.trigger_generation_policy_version
                == _TRIGGER_GENERATION_POLICY_VERSION
            )
            geometry = _geometry(self.geometry)
            profile = _profile(geometry)
            _require(type(self.mode_profile_policy_version) is str)
            _require(
                self.mode_profile_policy_version == MODE_PROFILE_POLICY_VERSION
            )
            mode = _mode(self.mode)
            lineage = _lineage(self.mode_lineage_sha256)
            symbol = _symbol(self.canonical_symbol)
            side = _side(self.side)
            structure_timeframe = _timeframe(self.structure_timeframe)
            structure_generation = _generation(self.structure_generation_id)
            trigger_timeframe = _timeframe(self.trigger_timeframe)
            trigger_rule = _trigger_rule(self.trigger_rule)
            close_text, close_at = _timestamp(self.trigger_candle_close_at)
            closed = _closed_flag(self.trigger_candle_closed)
            confirmed = _closed_flag(self.trigger_rule_satisfied)
            evaluation_text, evaluation_at = _timestamp(self.evaluation_timestamp)
            _require(type(self.trigger_age_seconds) is int)
            _require(type(self.maximum_trigger_age_seconds) is int)
            for value in (
                self.mode_matches,
                self.mode_lineage_matches,
                self.symbol_matches,
                self.side_matches,
                self.structure_timeframe_matches,
                self.structure_generation_matches,
                self.trigger_timeframe_matches,
                self.trigger_rule_matches,
                self.trigger_close_aligned,
                self.trigger_not_future,
                self.trigger_fresh,
            ):
                _require(type(value) is bool)
            _require(type(self.decision) is str)
            _require(type(self.reason_code) is str)
            _require(type(self.trigger_generation_id) is str)
            _require(
                _TRIGGER_ID_PATTERN.fullmatch(self.trigger_generation_id)
                is not None
            )
            derived = _derived_values(
                geometry=geometry,
                profile=profile,
                mode=mode,
                mode_lineage_sha256=lineage,
                canonical_symbol=symbol,
                side=side,
                structure_timeframe=structure_timeframe,
                structure_generation_id=structure_generation,
                trigger_timeframe=trigger_timeframe,
                trigger_rule=trigger_rule,
                trigger_candle_close_at=close_text,
                trigger_close=close_at,
                trigger_candle_closed=closed,
                trigger_rule_satisfied=confirmed,
                evaluation_at=evaluation_at,
            )
            _require(evaluation_text == self.evaluation_timestamp)
            for key, value in derived.items():
                _require(getattr(self, key) == value)
            _require(type(self.trigger_evidence_sha256) is str)
            _require(
                _SHA256_PATTERN.fullmatch(self.trigger_evidence_sha256)
                is not None
            )
            mapping = self.to_mapping()
            mapping.pop("trigger_evidence_sha256")
            _require(
                self.trigger_evidence_sha256 == _canonical_sha256(mapping)
            )
        except Exception:
            raise ValueError(_ERROR) from None

    def to_mapping(self) -> dict[str, object]:
        mapping = {item.name: getattr(self, item.name) for item in fields(self)}
        mapping["geometry"] = self.geometry.to_mapping()
        return mapping


def build_e3_mode_trigger_evidence(
    *,
    geometry,
    mode,
    mode_lineage_sha256,
    canonical_symbol,
    side,
    structure_timeframe,
    structure_generation_id,
    trigger_timeframe,
    trigger_rule,
    trigger_candle_close_at,
    trigger_candle_closed,
    trigger_rule_satisfied,
    evaluation_timestamp,
) -> E3ModeTriggerEvidenceV1:
    try:
        canonical_geometry = _geometry(geometry)
        profile = _profile(canonical_geometry)
        canonical_mode = _mode(mode)
        canonical_lineage = _lineage(mode_lineage_sha256)
        canonical_symbol_value = _symbol(canonical_symbol)
        canonical_side = _side(side)
        canonical_structure_timeframe = _timeframe(structure_timeframe)
        canonical_structure_generation = _generation(structure_generation_id)
        canonical_trigger_timeframe = _timeframe(trigger_timeframe)
        canonical_trigger_rule = _trigger_rule(trigger_rule)
        close_text, close_at = _timestamp(trigger_candle_close_at)
        canonical_closed = _closed_flag(trigger_candle_closed)
        canonical_confirmed = _closed_flag(trigger_rule_satisfied)
        evaluation_text, evaluation_at = _timestamp(evaluation_timestamp)
        derived = _derived_values(
            geometry=canonical_geometry,
            profile=profile,
            mode=canonical_mode,
            mode_lineage_sha256=canonical_lineage,
            canonical_symbol=canonical_symbol_value,
            side=canonical_side,
            structure_timeframe=canonical_structure_timeframe,
            structure_generation_id=canonical_structure_generation,
            trigger_timeframe=canonical_trigger_timeframe,
            trigger_rule=canonical_trigger_rule,
            trigger_candle_close_at=close_text,
            trigger_close=close_at,
            trigger_candle_closed=canonical_closed,
            trigger_rule_satisfied=canonical_confirmed,
            evaluation_at=evaluation_at,
        )
        content = {
            "schema_version": _SCHEMA_VERSION,
            "policy_version": _POLICY_VERSION,
            "trigger_generation_policy_version": _TRIGGER_GENERATION_POLICY_VERSION,
            "geometry": canonical_geometry.to_mapping(),
            "mode_profile_policy_version": MODE_PROFILE_POLICY_VERSION,
            "mode": canonical_mode,
            "mode_lineage_sha256": canonical_lineage,
            "canonical_symbol": canonical_symbol_value,
            "side": canonical_side,
            "structure_timeframe": canonical_structure_timeframe,
            "structure_generation_id": canonical_structure_generation,
            "trigger_timeframe": canonical_trigger_timeframe,
            "trigger_rule": canonical_trigger_rule,
            "trigger_candle_close_at": close_text,
            "trigger_candle_closed": canonical_closed,
            "trigger_rule_satisfied": canonical_confirmed,
            "evaluation_timestamp": evaluation_text,
            **derived,
        }
        evidence_hash = _canonical_sha256(content)
        return E3ModeTriggerEvidenceV1(
            schema_version=_SCHEMA_VERSION,
            policy_version=_POLICY_VERSION,
            trigger_generation_policy_version=_TRIGGER_GENERATION_POLICY_VERSION,
            geometry=canonical_geometry,
            mode_profile_policy_version=MODE_PROFILE_POLICY_VERSION,
            mode=canonical_mode,
            mode_lineage_sha256=canonical_lineage,
            canonical_symbol=canonical_symbol_value,
            side=canonical_side,
            structure_timeframe=canonical_structure_timeframe,
            structure_generation_id=canonical_structure_generation,
            trigger_timeframe=canonical_trigger_timeframe,
            trigger_rule=canonical_trigger_rule,
            trigger_candle_close_at=close_text,
            trigger_candle_closed=canonical_closed,
            trigger_rule_satisfied=canonical_confirmed,
            evaluation_timestamp=evaluation_text,
            trigger_age_seconds=derived["trigger_age_seconds"],
            maximum_trigger_age_seconds=derived[
                "maximum_trigger_age_seconds"
            ],
            mode_matches=derived["mode_matches"],
            mode_lineage_matches=derived["mode_lineage_matches"],
            symbol_matches=derived["symbol_matches"],
            side_matches=derived["side_matches"],
            structure_timeframe_matches=derived[
                "structure_timeframe_matches"
            ],
            structure_generation_matches=derived[
                "structure_generation_matches"
            ],
            trigger_timeframe_matches=derived["trigger_timeframe_matches"],
            trigger_rule_matches=derived["trigger_rule_matches"],
            trigger_close_aligned=derived["trigger_close_aligned"],
            trigger_not_future=derived["trigger_not_future"],
            trigger_fresh=derived["trigger_fresh"],
            decision=derived["decision"],
            reason_code=derived["reason_code"],
            trigger_generation_id=derived["trigger_generation_id"],
            trigger_evidence_sha256=evidence_hash,
        )
    except Exception:
        raise ValueError(_ERROR) from None
