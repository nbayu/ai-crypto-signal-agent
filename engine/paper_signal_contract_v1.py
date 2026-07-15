"""Frozen Phase 07 paper-signal contract primitives."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Mapping


PAPER_SIGNAL_SCHEMA_VERSION = 1
PAPER_SIGNAL_SCHEMA_NAME = "paper-signal-observation"
PAPER_SIGNAL_CLASSIFICATION = "PAPER_SIGNAL"
PAPER_SIGNAL_EXECUTION_BOUNDARY = (
    "LIVE_MARKET_OBSERVATION_NO_CAPITAL"
)

_ALLOWED_MODES = frozenset({"SWING", "INTRADAY", "SCALP"})
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?Z$"
)

_SOURCE_PUBLICATION_FIELDS = frozenset(
    {
        "signal_id",
        "delivery_id",
        "mode",
        "published_at",
        "source_payload_hash",
    }
)

_ENTRY_TOUCH_CANDLE_FIELDS = frozenset(
    {
        "symbol",
        "interval",
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "is_closed",
        "source",
    }
)

_EVIDENCE_FIELDS = frozenset(
    {
        "signal_geometry_hash",
        "closed_candle_hashes",
        "observation_event_hashes",
    }
)


class PaperSignalContractError(ValueError):
    """Raised when a Phase 07 paper-signal contract is invalid."""


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize a value using the frozen canonical JSON rules."""

    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise PaperSignalContractError(
            "payload is not valid canonical JSON"
        ) from exc

    return encoded.encode("utf-8")


def validate_source_publication_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and copy the canonical source-publication identity."""

    source = _require_exact_mapping(
        value,
        expected_fields=_SOURCE_PUBLICATION_FIELDS,
        label="source publication reference",
    )

    _require_nonempty_string(source["signal_id"], "signal_id")
    _require_nonempty_string(source["delivery_id"], "delivery_id")

    mode = source["mode"]
    if not isinstance(mode, str) or mode not in _ALLOWED_MODES:
        raise PaperSignalContractError(
            "mode must be exactly SWING, INTRADAY, or SCALP"
        )

    _parse_utc_timestamp(source["published_at"], "published_at")
    _require_sha256(
        source["source_payload_hash"],
        "source_payload_hash",
    )

    return copy.deepcopy(source)


def build_paper_observation_id(
    source_publication_ref: Mapping[str, Any],
) -> str:
    """Build the deterministic Phase 07 paper-observation identity."""

    source = validate_source_publication_ref(source_publication_ref)

    identity_payload = {
        "schema_version": PAPER_SIGNAL_SCHEMA_VERSION,
        "signal_id": source["signal_id"],
        "delivery_id": source["delivery_id"],
        "mode": source["mode"],
        "source_payload_hash": source["source_payload_hash"],
    }

    digest = hashlib.sha256(
        canonical_json_bytes(identity_payload)
    ).hexdigest()

    return f"PSO-{digest}"


def validate_observation_window(
    *,
    published_at: str,
    observed_from: str,
    observed_until: str,
    valid_until: str,
) -> dict[str, str]:
    """Validate deterministic publication and observation timestamps."""

    published = _parse_utc_timestamp(
        published_at,
        "published_at",
    )
    start = _parse_utc_timestamp(
        observed_from,
        "observed_from",
    )
    end = _parse_utc_timestamp(
        observed_until,
        "observed_until",
    )
    _parse_utc_timestamp(valid_until, "valid_until")

    if start < published:
        raise PaperSignalContractError(
            "observed_from must not precede published_at"
        )

    if end < start:
        raise PaperSignalContractError(
            "observed_until must not precede observed_from"
        )

    return {
        "published_at": published_at,
        "observed_from": observed_from,
        "observed_until": observed_until,
        "valid_until": valid_until,
    }


def validate_entry_touch_candle(
    value: Mapping[str, Any],
    *,
    expected_symbol: str,
) -> dict[str, Any]:
    """Validate a closed candle used as entry-touch evidence."""

    _require_nonempty_string(expected_symbol, "expected_symbol")

    candle = _require_exact_mapping(
        value,
        expected_fields=_ENTRY_TOUCH_CANDLE_FIELDS,
        label="entry touch candle",
    )

    for field in ("symbol", "interval", "source"):
        _require_nonempty_string(candle[field], field)

    if candle["symbol"] != expected_symbol:
        raise PaperSignalContractError(
            "entry touch candle symbol does not match signal symbol"
        )

    open_time = _parse_utc_timestamp(
        candle["open_time"],
        "open_time",
    )
    close_time = _parse_utc_timestamp(
        candle["close_time"],
        "close_time",
    )

    if close_time <= open_time:
        raise PaperSignalContractError(
            "close_time must be later than open_time"
        )

    if candle["is_closed"] is not True:
        raise PaperSignalContractError(
            "entry touch candle must be closed"
        )

    open_price = _require_finite_number(candle["open"], "open")
    high_price = _require_finite_number(candle["high"], "high")
    low_price = _require_finite_number(candle["low"], "low")
    close_price = _require_finite_number(candle["close"], "close")

    if high_price < max(open_price, close_price, low_price):
        raise PaperSignalContractError(
            "high is inconsistent with OHLC geometry"
        )

    if low_price > min(open_price, close_price, high_price):
        raise PaperSignalContractError(
            "low is inconsistent with OHLC geometry"
        )

    return copy.deepcopy(candle)


def validate_evidence(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate immutable paper-observation evidence hashes."""

    evidence = _require_exact_mapping(
        value,
        expected_fields=_EVIDENCE_FIELDS,
        label="evidence",
    )

    _require_sha256(
        evidence["signal_geometry_hash"],
        "signal_geometry_hash",
    )

    for field in (
        "closed_candle_hashes",
        "observation_event_hashes",
    ):
        hashes = evidence[field]

        if not isinstance(hashes, list):
            raise PaperSignalContractError(
                f"{field} must be an array"
            )

        for index, hash_value in enumerate(hashes):
            _require_sha256(
                hash_value,
                f"{field}[{index}]",
            )

        if len(hashes) != len(set(hashes)):
            raise PaperSignalContractError(
                f"{field} must not contain duplicates"
            )

    return copy.deepcopy(evidence)


def _require_exact_mapping(
    value: Mapping[str, Any],
    *,
    expected_fields: frozenset[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PaperSignalContractError(
            f"{label} must be an object"
        )

    actual_fields = frozenset(value.keys())

    if actual_fields != expected_fields:
        missing = sorted(expected_fields - actual_fields)
        unknown = sorted(actual_fields - expected_fields)

        details: list[str] = []
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown fields: {', '.join(unknown)}")

        raise PaperSignalContractError(
            f"invalid {label}: {'; '.join(details)}"
        )

    return dict(value)


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperSignalContractError(
            f"{field} must be a non-empty string"
        )

    return value


def _require_sha256(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or _SHA256_PATTERN.fullmatch(value) is None
    ):
        raise PaperSignalContractError(
            f"{field} must be a lowercase SHA-256 hex value"
        )

    return value


def _parse_utc_timestamp(value: Any, field: str) -> datetime:
    if (
        not isinstance(value, str)
        or _UTC_TIMESTAMP_PATTERN.fullmatch(value) is None
    ):
        raise PaperSignalContractError(
            f"{field} must be an ISO-8601 UTC timestamp"
        )

    try:
        parsed = datetime.fromisoformat(
            value.removesuffix("Z") + "+00:00"
        )
    except ValueError as exc:
        raise PaperSignalContractError(
            f"{field} must be a valid ISO-8601 UTC timestamp"
        ) from exc

    if parsed.tzinfo != timezone.utc:
        raise PaperSignalContractError(
            f"{field} must use UTC"
        )

    return parsed


def _require_finite_number(value: Any, field: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PaperSignalContractError(
            f"{field} must be a finite numeric value"
        )

    if not math.isfinite(value):
        raise PaperSignalContractError(
            f"{field} must be a finite numeric value"
        )

    return value
