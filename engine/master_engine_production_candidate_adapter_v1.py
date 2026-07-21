"""Pure conversion of one selected engine setup into a production candidate."""
from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from engine.production_signal_service_v1 import validate_production_signal_input


PRODUCTION_CANDIDATE_READY = "PRODUCTION_CANDIDATE_READY"
NO_ELIGIBLE_SIGNAL = "NO_ELIGIBLE_SIGNAL"
INVALID_MASTER_ENGINE_RESULT = "INVALID_MASTER_ENGINE_RESULT"
UNSUPPORTED_SIGNAL_MODE = "UNSUPPORTED_SIGNAL_MODE"
UNSUPPORTED_DIRECTION = "UNSUPPORTED_DIRECTION"
INVALID_NUMERIC_FIELD = "INVALID_NUMERIC_FIELD"
INVALID_TARGET_STRUCTURE = "INVALID_TARGET_STRUCTURE"
INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
INVALID_PRODUCTION_PROVENANCE = "INVALID_PRODUCTION_PROVENANCE"
FAIL_CLOSED = "FAIL_CLOSED"

_MODES = frozenset({"SWING", "INTRADAY", "SCALP"})
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_PROVENANCE_FIELDS = frozenset(
    {
        "source_commit",
        "source_evaluation_id",
        "production_evidence_ref",
        "component_versions",
    }
)
_SETUP_AUTHORITY_FIELDS = frozenset(
    {"tp2", "valid_until", "strategy_version", "source_payload_hash"}
)
_FORBIDDEN_FIELDS = frozenset(
    {
        "active_ledger_revision",
        "artifact_path",
        "channel",
        "credential",
        "credentials",
        "delivery_id",
        "delivery_out",
        "delivery_receipt",
        "destination_id",
        "evidence_path",
        "exception",
        "outcome_path",
        "pine_bridge_artifact_path",
        "pine_delivery_payload_path",
        "publication_identity",
        "receipt",
        "results",
        "signal_id",
        "snapshot_path",
        "token",
        "tradingview_watchlist_path",
        "usage",
        "watchlist_path",
    }
)


@dataclass(frozen=True, slots=True)
class MasterEngineProductionCandidateAdapterResultV1:
    result: str
    candidate: dict[str, Any] | None
    mode: str | None
    symbol: str | None
    direction: str | None
    eligible: bool
    reason: str
    timestamp: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "result": self.result,
            "candidate": copy.deepcopy(self.candidate),
            "mode": self.mode,
            "symbol": self.symbol,
            "direction": self.direction,
            "eligible": self.eligible,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


def _result(
    classification: str,
    *,
    mode: str | None = None,
    symbol: str | None = None,
    direction: str | None = None,
    timestamp: str | None = None,
    candidate: Mapping[str, Any] | None = None,
) -> MasterEngineProductionCandidateAdapterResultV1:
    return MasterEngineProductionCandidateAdapterResultV1(
        result=classification,
        candidate=(copy.deepcopy(dict(candidate)) if candidate is not None else None),
        mode=mode,
        symbol=symbol,
        direction=direction,
        eligible=classification == PRODUCTION_CANDIDATE_READY,
        reason=classification,
        timestamp=timestamp,
    )


def _contains_forbidden(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.casefold() in _FORBIDDEN_FIELDS:
                return True
            if _contains_forbidden(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden(item) for item in value)
    return False


def _utc_timestamp(value: object) -> str | None:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        return None
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return None
    return value


def _finite(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return value


def _nonblank(value: object) -> str | None:
    return value if isinstance(value, str) and bool(value.strip()) else None


def _final_top5(value: object) -> Sequence[Mapping[str, Any]] | None:
    if not isinstance(value, Mapping):
        return None
    out = value.get("out")
    if not isinstance(out, Mapping):
        return None
    setups = out.get("final_top5")
    if (
        not isinstance(setups, Sequence)
        or isinstance(setups, (str, bytes, bytearray, Mapping))
    ):
        return None
    if not all(isinstance(item, Mapping) for item in setups):
        return None
    return setups


def _provenance(value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or set(value) != _PROVENANCE_FIELDS:
        return None
    if _contains_forbidden(value):
        return None
    source_commit = value.get("source_commit")
    source_evaluation_id = _nonblank(value.get("source_evaluation_id"))
    evidence = value.get("production_evidence_ref")
    versions = value.get("component_versions")
    if (
        not isinstance(source_commit, str)
        or _COMMIT.fullmatch(source_commit) is None
        or source_evaluation_id is None
        or not isinstance(evidence, Mapping)
        or set(evidence) != {"manifest_hash", "manifest_path"}
        or not isinstance(evidence.get("manifest_hash"), str)
        or _SHA.fullmatch(evidence["manifest_hash"]) is None
        or _nonblank(evidence.get("manifest_path")) is None
        or not isinstance(versions, Mapping)
        or not versions
    ):
        return None
    if any(_nonblank(key) is None or _nonblank(item) is None for key, item in versions.items()):
        return None
    return copy.deepcopy(dict(value))


def _setup_authority(value: object) -> tuple[str, dict[str, Any] | None]:
    if not isinstance(value, Mapping) or set(value) != _SETUP_AUTHORITY_FIELDS:
        return INVALID_MASTER_ENGINE_RESULT, None
    if _contains_forbidden(value):
        return INVALID_MASTER_ENGINE_RESULT, None
    if _finite(value.get("tp2")) is None:
        return INVALID_TARGET_STRUCTURE, None
    if _utc_timestamp(value.get("valid_until")) is None:
        return INVALID_TIMESTAMP, None
    if (
        _nonblank(value.get("strategy_version")) is None
        or not isinstance(value.get("source_payload_hash"), str)
        or _SHA.fullmatch(value["source_payload_hash"]) is None
    ):
        return INVALID_MASTER_ENGINE_RESULT, None
    return PRODUCTION_CANDIDATE_READY, copy.deepcopy(dict(value))


def _selected_setup(
    setups: Sequence[Mapping[str, Any]],
    selected_symbol: object,
) -> Mapping[str, Any] | None:
    if _nonblank(selected_symbol) is None:
        return None
    matches = [setup for setup in setups if setup.get("symbol") == selected_symbol]
    if len(matches) != 1 or _contains_forbidden(matches[0]):
        return None
    return matches[0]


def _geometry(
    setup: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> tuple[str, str, dict[str, Any]] | str:
    symbol = _nonblank(setup.get("symbol"))
    golden_zone = setup.get("golden_zone")
    if symbol is None or not isinstance(golden_zone, Mapping):
        return INVALID_MASTER_ENGINE_RESULT
    direction = golden_zone.get("direction")
    sides = {"BULLISH": "LONG", "BEARISH": "SHORT"}
    if direction not in sides:
        return UNSUPPORTED_DIRECTION
    entry = golden_zone.get("entry_zone")
    stop = golden_zone.get("stop_loss")
    target = golden_zone.get("take_profit")
    if not isinstance(entry, Mapping) or not isinstance(stop, Mapping) or not isinstance(target, Mapping):
        return INVALID_MASTER_ENGINE_RESULT
    entry_min = _finite(entry.get("price_low"))
    entry_max = _finite(entry.get("price_high"))
    stop_loss = _finite(stop.get("price"))
    tp1 = _finite(target.get("price"))
    tp2 = _finite(authority.get("tp2"))
    if None in (entry_min, entry_max, stop_loss, tp1, tp2):
        return INVALID_NUMERIC_FIELD
    if entry_min > entry_max:
        return INVALID_TARGET_STRUCTURE
    side = sides[direction]
    if side == "LONG" and not (stop_loss < entry_min and entry_max <= tp1 < tp2):
        return INVALID_TARGET_STRUCTURE
    if side == "SHORT" and not (tp2 < tp1 <= entry_min and entry_max < stop_loss):
        return INVALID_TARGET_STRUCTURE
    return direction, side, {
        "symbol": symbol,
        "side": side,
        "entry_zone": {"min": entry_min, "max": entry_max},
        "stop_loss": stop_loss,
        "take_profit": {"tp1": tp1, "tp2": tp2},
        "valid_until": authority["valid_until"],
        "strategy_version": authority["strategy_version"],
        "source_payload_hash": authority["source_payload_hash"],
    }


def _adapt(
    *,
    master_engine_result: object,
    selected_symbol: object,
    mode: object,
    evaluated_at: object,
    production_provenance: object,
    setup_authority: object,
) -> MasterEngineProductionCandidateAdapterResultV1:
    timestamp = _utc_timestamp(evaluated_at)
    if timestamp is None:
        return _result(INVALID_TIMESTAMP)
    if not isinstance(mode, str) or mode not in _MODES:
        return _result(UNSUPPORTED_SIGNAL_MODE, timestamp=timestamp)
    setups = _final_top5(master_engine_result)
    if setups is None:
        return _result(INVALID_MASTER_ENGINE_RESULT, mode=mode, timestamp=timestamp)
    if not setups:
        return _result(NO_ELIGIBLE_SIGNAL, mode=mode, timestamp=timestamp)
    provenance = _provenance(production_provenance)
    if provenance is None:
        return _result(INVALID_PRODUCTION_PROVENANCE, mode=mode, timestamp=timestamp)
    authority_classification, authority = _setup_authority(setup_authority)
    if authority is None:
        return _result(authority_classification, mode=mode, timestamp=timestamp)
    setup = _selected_setup(setups, selected_symbol)
    if setup is None:
        return _result(INVALID_MASTER_ENGINE_RESULT, mode=mode, timestamp=timestamp)
    geometry = _geometry(setup, authority)
    if isinstance(geometry, str):
        return _result(
            geometry,
            mode=mode,
            symbol=_nonblank(setup.get("symbol")),
            timestamp=timestamp,
        )
    _source_direction, side, normalized_setup = geometry
    candidate = {
        "schema_version": 1,
        "schema_name": "production-signal-input",
        "source_commit": provenance["source_commit"],
        "source_evaluation_id": provenance["source_evaluation_id"],
        "mode": mode,
        "evaluated_at": timestamp,
        "production_evidence_ref": copy.deepcopy(provenance["production_evidence_ref"]),
        "outcome_kind": "PUBLISHED_SIGNAL",
        "eligible_setups": [normalized_setup],
        "component_versions": copy.deepcopy(provenance["component_versions"]),
    }
    try:
        validated = validate_production_signal_input(candidate)
    except Exception:
        return _result(
            FAIL_CLOSED,
            mode=mode,
            symbol=normalized_setup["symbol"],
            direction=side,
            timestamp=timestamp,
        )
    return _result(
        PRODUCTION_CANDIDATE_READY,
        candidate=validated,
        mode=mode,
        symbol=normalized_setup["symbol"],
        direction=side,
        timestamp=timestamp,
    )


def adapt_master_engine_result_to_production_candidate(
    *,
    master_engine_result: object,
    selected_symbol: object,
    mode: object,
    evaluated_at: object,
    production_provenance: object,
    setup_authority: object,
) -> MasterEngineProductionCandidateAdapterResultV1:
    """Adapt one explicitly selected detached setup without executing any dependency."""
    try:
        return _adapt(
            master_engine_result=master_engine_result,
            selected_symbol=selected_symbol,
            mode=mode,
            evaluated_at=evaluated_at,
            production_provenance=production_provenance,
            setup_authority=setup_authority,
        )
    except Exception:
        return _result(FAIL_CLOSED)
