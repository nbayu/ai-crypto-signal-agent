"""Canonical Phase 07 paper-signal acknowledgment handling."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime
from typing import Any, Mapping

from engine.paper_signal_contract_v1 import (
    PaperSignalContractError,
    canonical_json_bytes,
    validate_source_publication_ref,
)


ACKNOWLEDGMENT_ENTRY_REPORTED = "ENTRY_REPORTED"
ACKNOWLEDGMENT_SKIP_REPORTED = "SKIP_REPORTED"

_ALLOWED_EVENT_TYPES = frozenset(
    {
        ACKNOWLEDGMENT_ENTRY_REPORTED,
        ACKNOWLEDGMENT_SKIP_REPORTED,
    }
)

_EVENT_FIELDS = frozenset(
    {
        "event_id",
        "event_type",
        "acknowledged_at",
        "source",
    }
)

_ACKNOWLEDGMENT_FIELDS = frozenset(
    {
        "signal_id",
        "delivery_id",
        "event_id",
        "event_type",
        "published_at",
        "acknowledged_at",
        "acknowledgment_latency_ms",
        "source",
    }
)

_REQUIRED_OBSERVATION_FIELDS = frozenset(
    {
        "schema_version",
        "schema_name",
        "paper_observation_id",
        "signal_id",
        "mode",
        "classification",
        "execution_boundary",
        "capital_exposure",
        "order_execution",
        "position_authority",
        "source_publication_ref",
        "strategy_version",
        "orchestration_policy_version",
        "observer_version",
        "signal_geometry",
        "observed_from",
        "observed_until",
        "observation_state",
        "fill_observation_status",
        "entry_touched_at",
        "entry_touch_candle",
        "acknowledgment",
        "cancellation",
        "terminal_reason",
        "evidence",
        "created_at",
        "content_hash",
    }
)


def build_acknowledgment(
    *,
    source_publication_ref: Mapping[str, Any],
    event: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one canonical acknowledgment from a user-report event."""

    source = validate_source_publication_ref(source_publication_ref)
    event_copy = _require_exact_mapping(
        event,
        expected_fields=_EVENT_FIELDS,
        label="acknowledgment event",
    )

    _require_nonempty_string(event_copy["event_id"], "event_id")
    _require_nonempty_string(event_copy["source"], "source")

    event_type = event_copy["event_type"]
    if event_type not in _ALLOWED_EVENT_TYPES:
        raise PaperSignalContractError(
            "event_type must be ENTRY_REPORTED or SKIP_REPORTED"
        )

    published_at = _parse_utc(
        source["published_at"],
        "published_at",
    )
    acknowledged_at = _parse_utc(
        event_copy["acknowledged_at"],
        "acknowledged_at",
    )

    if acknowledged_at < published_at:
        raise PaperSignalContractError(
            "acknowledged_at must not precede published_at"
        )

    latency_delta = acknowledged_at - published_at
    latency_microseconds = (
        latency_delta.days * 86_400_000_000
        + latency_delta.seconds * 1_000_000
        + latency_delta.microseconds
    )

    if latency_microseconds % 1000 != 0:
        raise PaperSignalContractError(
            "acknowledgment latency must resolve to exact milliseconds"
        )

    latency_ms = latency_microseconds // 1000

    return {
        "signal_id": source["signal_id"],
        "delivery_id": source["delivery_id"],
        "event_id": event_copy["event_id"],
        "event_type": event_type,
        "published_at": source["published_at"],
        "acknowledged_at": event_copy["acknowledged_at"],
        "acknowledgment_latency_ms": latency_ms,
        "source": event_copy["source"],
    }


def merge_acknowledgment(
    *,
    existing: Mapping[str, Any] | None,
    incoming: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge one canonical acknowledgment using strict idempotency."""

    validated_existing = (
        _validate_canonical_acknowledgment(existing)
        if existing is not None
        else None
    )
    validated_incoming = (
        _validate_canonical_acknowledgment(incoming)
        if incoming is not None
        else None
    )

    if validated_existing is None:
        return copy.deepcopy(validated_incoming)

    if validated_incoming is None:
        return copy.deepcopy(validated_existing)

    if validated_existing != validated_incoming:
        raise PaperSignalContractError(
            "conflicting acknowledgment already exists"
        )

    return copy.deepcopy(validated_existing)


def apply_acknowledgment_to_observation(
    *,
    observation: Mapping[str, Any],
    acknowledgment: Mapping[str, Any],
    updated_at: str,
) -> dict[str, Any]:
    """Attach an acknowledgment without changing observation lifecycle."""

    observation_copy = _validate_observation_envelope(observation)
    incoming = _validate_canonical_acknowledgment(acknowledgment)

    updated_time = _parse_utc(updated_at, "updated_at")
    acknowledged_time = _parse_utc(
        incoming["acknowledged_at"],
        "acknowledged_at",
    )

    if updated_time < acknowledged_time:
        raise PaperSignalContractError(
            "updated_at must not precede acknowledged_at"
        )

    source = validate_source_publication_ref(
        observation_copy["source_publication_ref"]
    )

    if observation_copy["signal_id"] != source["signal_id"]:
        raise PaperSignalContractError(
            "observation signal identity is inconsistent"
        )

    if incoming["signal_id"] != observation_copy["signal_id"]:
        raise PaperSignalContractError(
            "acknowledgment signal_id does not match observation"
        )

    if incoming["delivery_id"] != source["delivery_id"]:
        raise PaperSignalContractError(
            "acknowledgment delivery_id does not match observation"
        )

    if incoming["published_at"] != source["published_at"]:
        raise PaperSignalContractError(
            "acknowledgment published_at does not match observation"
        )

    merged = merge_acknowledgment(
        existing=observation_copy["acknowledgment"],
        incoming=incoming,
    )

    if observation_copy["acknowledgment"] is not None:
        return copy.deepcopy(observation_copy)

    result = copy.deepcopy(observation_copy)
    result["acknowledgment"] = merged
    result["created_at"] = updated_at

    payload_without_hash = {
        key: copy.deepcopy(value)
        for key, value in result.items()
        if key != "content_hash"
    }

    result["content_hash"] = hashlib.sha256(
        canonical_json_bytes(payload_without_hash)
    ).hexdigest()

    return result


def _validate_canonical_acknowledgment(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    acknowledgment = _require_exact_mapping(
        value,
        expected_fields=_ACKNOWLEDGMENT_FIELDS,
        label="acknowledgment",
    )

    for field in (
        "signal_id",
        "delivery_id",
        "event_id",
        "source",
    ):
        _require_nonempty_string(acknowledgment[field], field)

    if acknowledgment["event_type"] not in _ALLOWED_EVENT_TYPES:
        raise PaperSignalContractError(
            "event_type must be ENTRY_REPORTED or SKIP_REPORTED"
        )

    published_at = _parse_utc(
        acknowledgment["published_at"],
        "published_at",
    )
    acknowledged_at = _parse_utc(
        acknowledgment["acknowledged_at"],
        "acknowledged_at",
    )

    if acknowledged_at < published_at:
        raise PaperSignalContractError(
            "acknowledged_at must not precede published_at"
        )

    latency = acknowledgment["acknowledgment_latency_ms"]
    if (
        isinstance(latency, bool)
        or not isinstance(latency, int)
        or latency < 0
    ):
        raise PaperSignalContractError(
            "acknowledgment_latency_ms must be a non-negative integer"
        )

    delta = acknowledged_at - published_at
    expected_microseconds = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )

    if expected_microseconds % 1000 != 0:
        raise PaperSignalContractError(
            "timestamp difference is not an exact millisecond value"
        )

    if latency != expected_microseconds // 1000:
        raise PaperSignalContractError(
            "acknowledgment latency does not match timestamps"
        )

    return copy.deepcopy(acknowledgment)


def _validate_observation_envelope(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PaperSignalContractError(
            "observation must be an object"
        )

    actual_fields = frozenset(value.keys())
    if actual_fields != _REQUIRED_OBSERVATION_FIELDS:
        raise PaperSignalContractError(
            "observation fields do not match the frozen contract"
        )

    observation = copy.deepcopy(dict(value))

    if observation["schema_version"] != 1 or isinstance(
        observation["schema_version"],
        bool,
    ):
        raise PaperSignalContractError(
            "observation schema_version must be integer 1"
        )

    if observation["schema_name"] != "paper-signal-observation":
        raise PaperSignalContractError(
            "invalid observation schema_name"
        )

    if observation["classification"] != "PAPER_SIGNAL":
        raise PaperSignalContractError(
            "invalid observation classification"
        )

    if (
        observation["execution_boundary"]
        != "LIVE_MARKET_OBSERVATION_NO_CAPITAL"
    ):
        raise PaperSignalContractError(
            "invalid observation execution boundary"
        )

    _require_nonempty_string(
        observation["signal_id"],
        "observation.signal_id",
    )
    _require_sha256(
        observation["content_hash"],
        "observation.content_hash",
    )
    _parse_utc(observation["created_at"], "created_at")

    source = validate_source_publication_ref(
        observation["source_publication_ref"]
    )

    if source["signal_id"] != observation["signal_id"]:
        raise PaperSignalContractError(
            "observation source signal identity mismatch"
        )

    existing = observation["acknowledgment"]
    if existing is not None:
        _validate_canonical_acknowledgment(existing)

    return observation


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
        raise PaperSignalContractError(
            f"{label} fields do not match the frozen contract"
        )

    return copy.deepcopy(dict(value))


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperSignalContractError(
            f"{field} must be a non-empty string"
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
    if (
        not isinstance(value, str)
        or not value.endswith("Z")
        or "T" not in value
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

    return parsed
