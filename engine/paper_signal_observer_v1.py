"""Deterministic live-market paper-signal observation."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime
from typing import Any, Iterable, Mapping

from engine.paper_signal_contract_v1 import (
    PAPER_SIGNAL_CLASSIFICATION,
    PAPER_SIGNAL_EXECUTION_BOUNDARY,
    PAPER_SIGNAL_SCHEMA_NAME,
    PAPER_SIGNAL_SCHEMA_VERSION,
    PaperSignalContractError,
    build_paper_observation_id,
    canonical_json_bytes,
    validate_entry_touch_candle,
    validate_observation_window,
    validate_source_publication_ref,
)

OBSERVATION_OBSERVING = "OBSERVING"
OBSERVATION_ENTRY_ZONE_TOUCHED = "ENTRY_ZONE_TOUCHED"
OBSERVATION_TARGET_REACHED_BEFORE_ENTRY = (
    "TARGET_REACHED_BEFORE_ENTRY"
)
OBSERVATION_INVALIDATED_BEFORE_ENTRY = (
    "INVALIDATED_BEFORE_ENTRY"
)
OBSERVATION_EXPIRED_UNTOUCHED = "EXPIRED_UNTOUCHED"
OBSERVATION_CANCELLED = "CANCELLED"
OBSERVATION_AMBIGUOUS = "OBSERVATION_AMBIGUOUS"

FILL_OBSERVATION_NOT_OBSERVED = "NOT_OBSERVED"
FILL_OBSERVATION_ENTRY_ZONE_TOUCHED = "ENTRY_ZONE_TOUCHED"
FILL_OBSERVATION_TARGET_REACHED_BEFORE_ENTRY = (
    "TARGET_REACHED_BEFORE_ENTRY"
)
FILL_OBSERVATION_INVALIDATED_BEFORE_ENTRY = (
    "INVALIDATED_BEFORE_ENTRY"
)
FILL_OBSERVATION_EXPIRED_UNTOUCHED = "EXPIRED_UNTOUCHED"
FILL_OBSERVATION_AMBIGUOUS = "AMBIGUOUS"

_ALLOWED_SIDES = frozenset({"LONG", "SHORT"})

_PUBLICATION_FIELDS = frozenset(
    {
        "source_publication_ref",
        "symbol",
        "side",
        "valid_until",
        "entry_zone",
        "stop_loss",
        "take_profit",
        "signal_geometry_hash",
        "strategy_version",
        "orchestration_policy_version",
    }
)

_ENTRY_ZONE_FIELDS = frozenset({"min", "max"})
_TAKE_PROFIT_FIELDS = frozenset({"tp1", "tp2"})
_CANCELLATION_FIELDS = frozenset(
    {
        "event_id",
        "reason_code",
        "cancelled_at",
        "source",
    }
)


def observe_paper_signal(
    *,
    publication: Mapping[str, Any],
    closed_candles: Iterable[Mapping[str, Any]],
    observed_from: str,
    observed_until: str,
    created_at: str,
    observer_version: str,
    cancellation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Observe one official signal without creating execution state."""

    publication_copy = _validate_publication(publication)
    source_ref = validate_source_publication_ref(
        publication_copy["source_publication_ref"]
    )

    window = validate_observation_window(
        published_at=source_ref["published_at"],
        observed_from=observed_from,
        observed_until=observed_until,
        valid_until=publication_copy["valid_until"],
    )

    _parse_utc(created_at, "created_at")
    _require_nonempty_string(observer_version, "observer_version")

    validated_cancellation = (
        _validate_cancellation(
            cancellation,
            published_at=source_ref["published_at"],
        )
        if cancellation is not None
        else None
    )

    candles = _validate_and_order_candles(
        closed_candles,
        expected_symbol=publication_copy["symbol"],
        published_at=source_ref["published_at"],
        observed_until=observed_until,
    )

    state = OBSERVATION_OBSERVING
    fill_status = FILL_OBSERVATION_NOT_OBSERVED
    entry_touched_at = None
    entry_touch_candle = None
    terminal_reason = None
    selected_cancellation = None

    cancellation_time = (
        _parse_utc(
            validated_cancellation["cancelled_at"],
            "cancelled_at",
        )
        if validated_cancellation is not None
        else None
    )

    for candle in candles:
        close_time = _parse_utc(candle["close_time"], "close_time")

        if (
            validated_cancellation is not None
            and cancellation_time is not None
            and cancellation_time < close_time
        ):
            state = OBSERVATION_CANCELLED
            fill_status = FILL_OBSERVATION_NOT_OBSERVED
            terminal_reason = validated_cancellation["reason_code"]
            selected_cancellation = copy.deepcopy(
                validated_cancellation
            )
            break

        touched_entry = _touches_entry(
            candle,
            publication_copy["entry_zone"],
        )
        touched_target = _touches_target(
            candle,
            side=publication_copy["side"],
            tp1=publication_copy["take_profit"]["tp1"],
        )
        touched_invalidation = _touches_invalidation(
            candle,
            side=publication_copy["side"],
            stop_loss=publication_copy["stop_loss"],
        )

        touch_count = sum(
            (
                touched_entry,
                touched_target,
                touched_invalidation,
            )
        )

        if touch_count > 1:
            state = OBSERVATION_AMBIGUOUS
            fill_status = FILL_OBSERVATION_AMBIGUOUS
            terminal_reason = "MULTIPLE_FIRST_TOUCHES_SAME_CANDLE"
            break

        if touched_entry:
            state = OBSERVATION_ENTRY_ZONE_TOUCHED
            fill_status = FILL_OBSERVATION_ENTRY_ZONE_TOUCHED
            entry_touched_at = candle["close_time"]
            entry_touch_candle = copy.deepcopy(candle)
            terminal_reason = "ENTRY_ZONE_TOUCHED"
            break

        if touched_target:
            state = OBSERVATION_TARGET_REACHED_BEFORE_ENTRY
            fill_status = (
                FILL_OBSERVATION_TARGET_REACHED_BEFORE_ENTRY
            )
            terminal_reason = "TARGET_REACHED_BEFORE_ENTRY"
            break

        if touched_invalidation:
            state = OBSERVATION_INVALIDATED_BEFORE_ENTRY
            fill_status = (
                FILL_OBSERVATION_INVALIDATED_BEFORE_ENTRY
            )
            terminal_reason = "INVALIDATED_BEFORE_ENTRY"
            break

    if state == OBSERVATION_OBSERVING:
        if validated_cancellation is not None:
            if cancellation_time is not None and cancellation_time <= (
                _parse_utc(observed_until, "observed_until")
            ):
                state = OBSERVATION_CANCELLED
                terminal_reason = validated_cancellation["reason_code"]
                selected_cancellation = copy.deepcopy(
                    validated_cancellation
                )

    if state == OBSERVATION_OBSERVING:
        if _parse_utc(observed_until, "observed_until") > _parse_utc(
            publication_copy["valid_until"],
            "valid_until",
        ):
            state = OBSERVATION_EXPIRED_UNTOUCHED
            fill_status = FILL_OBSERVATION_EXPIRED_UNTOUCHED
            terminal_reason = "VALIDITY_EXPIRED"

    signal_geometry = {
        "symbol": publication_copy["symbol"],
        "side": publication_copy["side"],
        "entry_zone": copy.deepcopy(
            publication_copy["entry_zone"]
        ),
        "stop_loss": publication_copy["stop_loss"],
        "take_profit": copy.deepcopy(
            publication_copy["take_profit"]
        ),
        "valid_until": publication_copy["valid_until"],
    }

    evidence = {
        "signal_geometry_hash": publication_copy[
            "signal_geometry_hash"
        ],
        "closed_candle_hashes": [
            _hash_payload(candle) for candle in candles
        ],
        "observation_event_hashes": (
            [_hash_payload(selected_cancellation)]
            if selected_cancellation is not None
            else []
        ),
    }

    payload = {
        "schema_version": PAPER_SIGNAL_SCHEMA_VERSION,
        "schema_name": PAPER_SIGNAL_SCHEMA_NAME,
        "paper_observation_id": build_paper_observation_id(
            source_ref
        ),
        "signal_id": source_ref["signal_id"],
        "mode": source_ref["mode"],
        "classification": PAPER_SIGNAL_CLASSIFICATION,
        "execution_boundary": PAPER_SIGNAL_EXECUTION_BOUNDARY,
        "capital_exposure": "NONE",
        "order_execution": "PROHIBITED",
        "position_authority": "TELEGRAM_USER_REPORT",
        "source_publication_ref": copy.deepcopy(source_ref),
        "strategy_version": publication_copy["strategy_version"],
        "orchestration_policy_version": publication_copy[
            "orchestration_policy_version"
        ],
        "observer_version": observer_version,
        "signal_geometry": signal_geometry,
        "observed_from": window["observed_from"],
        "observed_until": window["observed_until"],
        "observation_state": state,
        "fill_observation_status": fill_status,
        "entry_touched_at": entry_touched_at,
        "entry_touch_candle": entry_touch_candle,
        "acknowledgment": None,
        "cancellation": selected_cancellation,
        "terminal_reason": terminal_reason,
        "evidence": evidence,
        "created_at": created_at,
    }

    payload["content_hash"] = _hash_payload(payload)
    return payload


def _validate_publication(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    publication = _require_exact_mapping(
        value,
        _PUBLICATION_FIELDS,
        "publication",
    )

    validate_source_publication_ref(
        publication["source_publication_ref"]
    )

    _require_nonempty_string(publication["symbol"], "symbol")

    if publication["side"] not in _ALLOWED_SIDES:
        raise PaperSignalContractError(
            "side must be exactly LONG or SHORT"
        )

    _parse_utc(publication["valid_until"], "valid_until")
    _require_nonempty_string(
        publication["strategy_version"],
        "strategy_version",
    )
    _require_nonempty_string(
        publication["orchestration_policy_version"],
        "orchestration_policy_version",
    )
    _require_sha256(
        publication["signal_geometry_hash"],
        "signal_geometry_hash",
    )

    entry_zone = _require_exact_mapping(
        publication["entry_zone"],
        _ENTRY_ZONE_FIELDS,
        "entry_zone",
    )
    take_profit = _require_exact_mapping(
        publication["take_profit"],
        _TAKE_PROFIT_FIELDS,
        "take_profit",
    )

    entry_min = _require_number(entry_zone["min"], "entry_zone.min")
    entry_max = _require_number(entry_zone["max"], "entry_zone.max")
    stop_loss = _require_number(
        publication["stop_loss"],
        "stop_loss",
    )
    tp1 = _require_number(take_profit["tp1"], "take_profit.tp1")
    tp2 = _require_number(take_profit["tp2"], "take_profit.tp2")

    if entry_min > entry_max:
        raise PaperSignalContractError(
            "entry_zone.min must not exceed entry_zone.max"
        )

    if publication["side"] == "LONG":
        if not stop_loss < entry_min:
            raise PaperSignalContractError(
                "LONG stop_loss must be below entry zone"
            )
        if not entry_max < tp1 <= tp2:
            raise PaperSignalContractError(
                "LONG targets must be above entry zone"
            )
    else:
        if not stop_loss > entry_max:
            raise PaperSignalContractError(
                "SHORT stop_loss must be above entry zone"
            )
        if not entry_min > tp1 >= tp2:
            raise PaperSignalContractError(
                "SHORT targets must be below entry zone"
            )

    return copy.deepcopy(publication)


def _validate_and_order_candles(
    values: Iterable[Mapping[str, Any]],
    *,
    expected_symbol: str,
    published_at: str,
    observed_until: str,
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes, Mapping)):
        raise PaperSignalContractError(
            "closed_candles must be an iterable of candle objects"
        )

    result: list[dict[str, Any]] = []
    identities: set[tuple[str, str, str]] = set()

    for raw in values:
        candle = validate_entry_touch_candle(
            raw,
            expected_symbol=expected_symbol,
        )

        identity = (
            candle["symbol"],
            candle["open_time"],
            candle["close_time"],
        )
        if identity in identities:
            raise PaperSignalContractError(
                "duplicate candle identity"
            )
        identities.add(identity)

        if _parse_utc(candle["close_time"], "close_time") > (
            _parse_utc(observed_until, "observed_until")
        ):
            raise PaperSignalContractError(
                "candle closes after observed_until"
            )

        if _parse_utc(candle["close_time"], "close_time") < (
            _parse_utc(published_at, "published_at")
        ):
            continue

        result.append(candle)

    result.sort(
        key=lambda item: (
            _parse_utc(item["close_time"], "close_time"),
            _parse_utc(item["open_time"], "open_time"),
        )
    )
    return result


def _validate_cancellation(
    value: Mapping[str, Any],
    *,
    published_at: str,
) -> dict[str, Any]:
    cancellation = _require_exact_mapping(
        value,
        _CANCELLATION_FIELDS,
        "cancellation",
    )

    for field in ("event_id", "reason_code", "source"):
        _require_nonempty_string(cancellation[field], field)

    cancelled_at = _parse_utc(
        cancellation["cancelled_at"],
        "cancelled_at",
    )
    if cancelled_at < _parse_utc(published_at, "published_at"):
        raise PaperSignalContractError(
            "cancelled_at must not precede published_at"
        )

    return copy.deepcopy(cancellation)


def _touches_entry(
    candle: Mapping[str, Any],
    entry_zone: Mapping[str, Any],
) -> bool:
    return (
        candle["high"] >= entry_zone["min"]
        and candle["low"] <= entry_zone["max"]
    )


def _touches_target(
    candle: Mapping[str, Any],
    *,
    side: str,
    tp1: float,
) -> bool:
    if side == "LONG":
        return candle["high"] >= tp1
    return candle["low"] <= tp1


def _touches_invalidation(
    candle: Mapping[str, Any],
    *,
    side: str,
    stop_loss: float,
) -> bool:
    if side == "LONG":
        return candle["low"] <= stop_loss
    return candle["high"] >= stop_loss


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require_exact_mapping(
    value: Mapping[str, Any],
    fields: frozenset[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PaperSignalContractError(f"{label} must be an object")

    actual = frozenset(value.keys())
    if actual != fields:
        raise PaperSignalContractError(
            f"{label} fields do not match the frozen contract"
        )

    return dict(value)


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperSignalContractError(
            f"{field} must be a non-empty string"
        )
    return value


def _require_number(value: Any, field: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PaperSignalContractError(
            f"{field} must be numeric"
        )
    if value != value or value in (float("inf"), float("-inf")):
        raise PaperSignalContractError(
            f"{field} must be finite"
        )
    return value


def _require_sha256(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PaperSignalContractError(
            f"{field} must be lowercase SHA-256"
        )
    return value


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PaperSignalContractError(
            f"{field} must be ISO-8601 UTC"
        )

    try:
        parsed = datetime.fromisoformat(
            value.removesuffix("Z") + "+00:00"
        )
    except ValueError as exc:
        raise PaperSignalContractError(
            f"{field} must be valid ISO-8601 UTC"
        ) from exc

    return parsed
