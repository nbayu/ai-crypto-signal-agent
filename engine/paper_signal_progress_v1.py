"""Deterministic Phase 07 paper-signal progress aggregation."""

from __future__ import annotations

import copy
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from engine.paper_signal_contract_v1 import (
    PAPER_SIGNAL_CLASSIFICATION,
    PAPER_SIGNAL_EXECUTION_BOUNDARY,
    PaperSignalContractError,
    canonical_json_bytes,
)


PAPER_SIGNAL_PROGRESS_SCHEMA_VERSION = 1
PAPER_SIGNAL_PROGRESS_SCHEMA_NAME = "paper-signal-progress"

_MINIMUM_REQUIRED_TOTAL = 100
_MINIMUM_REQUIRED_PER_ENABLED_MODE = 30
_MODE_ORDER = ("SWING", "INTRADAY", "SCALP")
_ALLOWED_MODES = frozenset(_MODE_ORDER)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)

_SOURCE_PUBLICATION_FIELDS = frozenset(
    {
        "signal_id", "delivery_id", "mode", "published_at",
        "source_payload_hash", "classification",
    }
)
_EVALUATION_CYCLE_FIELDS = frozenset(
    {
        "schema_version", "source_evaluation_id", "mode", "evaluated_at",
        "official_alert_signal_ids", "rejection_reasons", "content_hash",
    }
)
_OBSERVATION_FIELDS = frozenset(
    {
        "signal_id", "mode", "observation_state", "acknowledgment",
        "classification",
    }
)
_ACKNOWLEDGMENT_FIELDS = frozenset(
    {
        "signal_id", "delivery_id", "event_id", "event_type",
        "published_at", "acknowledged_at", "acknowledgment_latency_ms",
        "source",
    }
)
_ALLOWED_ACKNOWLEDGMENT_TYPES = frozenset(
    {"ENTRY_REPORTED", "SKIP_REPORTED"}
)


def build_evaluation_cycle(
    *,
    source_evaluation_id: str,
    mode: str,
    evaluated_at: str,
    official_alert_signal_ids: Iterable[str],
    rejection_reasons: Mapping[str, int],
) -> dict[str, Any]:
    """Build one canonical paper evaluation-cycle record."""

    _require_nonempty_string(source_evaluation_id, "source_evaluation_id")
    _require_mode(mode)
    _parse_utc_timestamp(evaluated_at, "evaluated_at")
    payload = {
        "schema_version": 1,
        "source_evaluation_id": source_evaluation_id,
        "mode": mode,
        "evaluated_at": evaluated_at,
        "official_alert_signal_ids": _normalize_signal_ids(
            official_alert_signal_ids
        ),
        "rejection_reasons": _normalize_rejection_reasons(
            rejection_reasons
        ),
    }
    payload["content_hash"] = _hash_payload(payload)
    return payload


def build_paper_signal_progress(
    *,
    enabled_modes: Iterable[str],
    source_publications: Iterable[Mapping[str, Any]],
    evaluation_cycles: Iterable[Mapping[str, Any]],
    observations: Iterable[Mapping[str, Any]],
    critical_lifecycle_defect_count: int,
    generated_at: str,
) -> dict[str, Any]:
    """Build deterministic Phase 07 progress and promotion evidence."""

    modes = _normalize_enabled_modes(enabled_modes)
    _parse_utc_timestamp(generated_at, "generated_at")
    if (
        isinstance(critical_lifecycle_defect_count, bool)
        or not isinstance(critical_lifecycle_defect_count, int)
        or critical_lifecycle_defect_count < 0
    ):
        raise PaperSignalContractError(
            "critical_lifecycle_defect_count must be a non-negative integer"
        )

    publications = _deduplicate_publications(source_publications)
    cycles = _deduplicate_evaluation_cycles(evaluation_cycles)
    normalized_observations = _deduplicate_observations(observations)
    count_by_mode = {mode: 0 for mode in _MODE_ORDER}
    for publication in publications:
        count_by_mode[publication["mode"]] += 1

    total = sum(count_by_mode.values())
    payload = {
        "schema_version": PAPER_SIGNAL_PROGRESS_SCHEMA_VERSION,
        "schema_name": PAPER_SIGNAL_PROGRESS_SCHEMA_NAME,
        "classification": PAPER_SIGNAL_CLASSIFICATION,
        "execution_boundary": PAPER_SIGNAL_EXECUTION_BOUNDARY,
        "enabled_modes": modes,
        "official_signal_total": total,
        "official_signal_count_by_mode": count_by_mode,
        "minimum_required_total": _MINIMUM_REQUIRED_TOTAL,
        "minimum_required_per_enabled_mode": (
            _MINIMUM_REQUIRED_PER_ENABLED_MODE
        ),
        "evaluation_coverage_by_mode": _build_evaluation_coverage(cycles),
        "observation_state_distribution": (
            _build_observation_state_distribution(normalized_observations)
        ),
        "acknowledgment_summary": _build_acknowledgment_summary(
            publications=publications,
            observations=normalized_observations,
        ),
        "critical_lifecycle_defect_count": critical_lifecycle_defect_count,
        "promotion_readiness": (
            total >= _MINIMUM_REQUIRED_TOTAL
            and all(
                count_by_mode[mode] >= _MINIMUM_REQUIRED_PER_ENABLED_MODE
                for mode in modes
            )
            and critical_lifecycle_defect_count == 0
        ),
        "generated_at": generated_at,
    }
    payload["content_hash"] = _hash_payload(payload)
    return payload


def _deduplicate_publications(
    values: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_identity: dict[tuple[str, str, str], dict[str, Any]] = {}
    for raw in _materialize_iterable(values, "source_publications"):
        publication = _validate_source_publication(raw)
        identity = (
            publication["mode"], publication["signal_id"],
            publication["delivery_id"],
        )
        _accept_identity(
            by_identity, identity, publication,
            "conflicting official publication identity",
        )
    return [copy.deepcopy(by_identity[key]) for key in sorted(by_identity)]


def _validate_source_publication(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    publication = _require_exact_mapping(
        value, _SOURCE_PUBLICATION_FIELDS, "source publication"
    )
    _require_nonempty_string(publication["signal_id"], "signal_id")
    _require_nonempty_string(publication["delivery_id"], "delivery_id")
    _require_mode(publication["mode"])
    _parse_utc_timestamp(publication["published_at"], "published_at")
    _require_sha256(publication["source_payload_hash"], "source_payload_hash")
    if publication["classification"] != PAPER_SIGNAL_CLASSIFICATION:
        raise PaperSignalContractError(
            "only PAPER_SIGNAL publications may be counted"
        )
    return copy.deepcopy(publication)


def _deduplicate_evaluation_cycles(
    values: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in _materialize_iterable(values, "evaluation_cycles"):
        cycle = _validate_evaluation_cycle(raw)
        identity = (cycle["mode"], cycle["source_evaluation_id"])
        _accept_identity(
            by_identity, identity, cycle,
            "conflicting evaluation-cycle identity",
        )
    return [copy.deepcopy(by_identity[key]) for key in sorted(by_identity)]


def _validate_evaluation_cycle(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    cycle = _require_exact_mapping(
        value, _EVALUATION_CYCLE_FIELDS, "evaluation cycle"
    )
    if cycle["schema_version"] != 1 or isinstance(
        cycle["schema_version"], bool
    ):
        raise PaperSignalContractError(
            "evaluation-cycle schema_version must be integer 1"
        )
    _require_nonempty_string(
        cycle["source_evaluation_id"], "source_evaluation_id"
    )
    _require_mode(cycle["mode"])
    _parse_utc_timestamp(cycle["evaluated_at"], "evaluated_at")
    canonical = {
        "schema_version": 1,
        "source_evaluation_id": cycle["source_evaluation_id"],
        "mode": cycle["mode"],
        "evaluated_at": cycle["evaluated_at"],
        "official_alert_signal_ids": _normalize_signal_ids(
            cycle["official_alert_signal_ids"]
        ),
        "rejection_reasons": _normalize_rejection_reasons(
            cycle["rejection_reasons"]
        ),
    }
    _require_sha256(cycle["content_hash"], "content_hash")
    expected = _hash_payload(canonical)
    if cycle["content_hash"] != expected:
        raise PaperSignalContractError("evaluation-cycle content hash mismatch")
    canonical["content_hash"] = expected
    return canonical


def _deduplicate_observations(
    values: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in _materialize_iterable(values, "observations"):
        observation = _validate_observation(raw)
        identity = (observation["mode"], observation["signal_id"])
        _accept_identity(
            by_identity, identity, observation,
            "conflicting paper observation identity",
        )
    return [copy.deepcopy(by_identity[key]) for key in sorted(by_identity)]


def _validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    observation = _require_exact_mapping(
        value, _OBSERVATION_FIELDS, "progress observation"
    )
    _require_nonempty_string(observation["signal_id"], "observation.signal_id")
    _require_mode(observation["mode"])
    _require_nonempty_string(
        observation["observation_state"], "observation_state"
    )
    if observation["classification"] != PAPER_SIGNAL_CLASSIFICATION:
        raise PaperSignalContractError(
            "observation classification must be PAPER_SIGNAL"
        )
    acknowledgment = observation["acknowledgment"]
    if acknowledgment is not None:
        acknowledgment = _validate_acknowledgment(acknowledgment)
        if acknowledgment["signal_id"] != observation["signal_id"]:
            raise PaperSignalContractError(
                "observation acknowledgment signal mismatch"
            )
    result = copy.deepcopy(observation)
    result["acknowledgment"] = acknowledgment
    return result


def _validate_acknowledgment(value: Mapping[str, Any]) -> dict[str, Any]:
    acknowledgment = _require_exact_mapping(
        value, _ACKNOWLEDGMENT_FIELDS, "acknowledgment"
    )
    for field in ("signal_id", "delivery_id", "event_id", "source"):
        _require_nonempty_string(acknowledgment[field], field)
    if acknowledgment["event_type"] not in _ALLOWED_ACKNOWLEDGMENT_TYPES:
        raise PaperSignalContractError("invalid acknowledgment event_type")
    published = _parse_utc_timestamp(
        acknowledgment["published_at"], "published_at"
    )
    acknowledged = _parse_utc_timestamp(
        acknowledgment["acknowledged_at"], "acknowledged_at"
    )
    if acknowledged < published:
        raise PaperSignalContractError(
            "acknowledged_at must not precede published_at"
        )
    latency = acknowledgment["acknowledgment_latency_ms"]
    if isinstance(latency, bool) or not isinstance(latency, int) or latency < 0:
        raise PaperSignalContractError(
            "acknowledgment latency must be a non-negative integer"
        )
    delta = acknowledged - published
    microseconds = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )
    if microseconds % 1000 != 0 or latency != microseconds // 1000:
        raise PaperSignalContractError(
            "acknowledgment latency does not match timestamps"
        )
    return copy.deepcopy(acknowledgment)


def _build_evaluation_coverage(
    cycles: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for mode in _MODE_ORDER:
        mode_cycles = [cycle for cycle in cycles if cycle["mode"] == mode]
        alert_count = sum(bool(cycle["official_alert_signal_ids"]) for cycle in mode_cycles)
        no_trade_count = len(mode_cycles) - alert_count
        reasons: dict[str, int] = {}
        for cycle in mode_cycles:
            if cycle["official_alert_signal_ids"]:
                continue
            for reason, count in cycle["rejection_reasons"].items():
                reasons[reason] = reasons.get(reason, 0) + count
        result[mode] = {
            "evaluation_cycles": len(mode_cycles),
            "official_alert_cycles": alert_count,
            "no_trade_cycles": no_trade_count,
            "no_trade_coverage_ratio": (
                None if not mode_cycles else no_trade_count / len(mode_cycles)
            ),
            "top_rejection_reasons": {
                reason: reasons[reason] for reason in sorted(reasons)
            },
        }
    return result


def _build_observation_state_distribution(
    observations: list[dict[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for observation in observations:
        state = observation["observation_state"]
        counts[state] = counts.get(state, 0) + 1
    return {state: counts[state] for state in sorted(counts)}


def _build_acknowledgment_summary(
    *,
    publications: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    identities = {
        (publication["mode"], publication["signal_id"])
        for publication in publications
    }
    latencies = [
        observation["acknowledgment"]["acknowledgment_latency_ms"]
        for observation in observations
        if (observation["mode"], observation["signal_id"]) in identities
        and observation["acknowledgment"] is not None
    ]
    official_count = len(publications)
    if latencies:
        total = sum(latencies)
        mean: int | float = total / len(latencies)
        if total % len(latencies) == 0:
            mean = total // len(latencies)
        latency_summary = {
            "minimum": min(latencies),
            "maximum": max(latencies),
            "mean": mean,
        }
    else:
        latency_summary = {"minimum": None, "maximum": None, "mean": None}
    return {
        "official_signal_count": official_count,
        "acknowledged_signal_count": len(latencies),
        "acknowledgment_coverage_ratio": (
            None if official_count == 0 else len(latencies) / official_count
        ),
        "latency_ms": latency_summary,
    }


def _normalize_enabled_modes(values: Iterable[str]) -> list[str]:
    items = _materialize_iterable(values, "enabled_modes")
    if not items:
        raise PaperSignalContractError("at least one mode must be enabled")
    for mode in items:
        _require_mode(mode)
    if len(items) != len(set(items)):
        raise PaperSignalContractError("enabled_modes must be unique")
    enabled = set(items)
    return [mode for mode in _MODE_ORDER if mode in enabled]


def _normalize_signal_ids(values: Iterable[str]) -> list[str]:
    items = _materialize_iterable(values, "official_alert_signal_ids")
    for index, value in enumerate(items):
        _require_nonempty_string(value, f"official_alert_signal_ids[{index}]")
    if len(items) != len(set(items)):
        raise PaperSignalContractError("official alert signal IDs must be unique")
    return sorted(items)


def _normalize_rejection_reasons(values: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(values, Mapping):
        raise PaperSignalContractError("rejection_reasons must be an object")
    result: dict[str, int] = {}
    for reason, count in values.items():
        reason = _require_nonempty_string(reason, "rejection reason")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise PaperSignalContractError(
                "rejection counts must be non-negative integers"
            )
        result[reason] = count
    return {reason: result[reason] for reason in sorted(result)}


def _materialize_iterable(values: Iterable[Any], label: str) -> list[Any]:
    if isinstance(values, (str, bytes, Mapping)):
        raise PaperSignalContractError(f"{label} must be an iterable collection")
    try:
        return list(values)
    except TypeError as exc:
        raise PaperSignalContractError(f"{label} must be iterable") from exc


def _accept_identity(
    records: dict[Any, dict[str, Any]],
    identity: Any,
    value: dict[str, Any],
    message: str,
) -> None:
    existing = records.get(identity)
    if existing is None:
        records[identity] = value
    elif existing != value:
        raise PaperSignalContractError(message)


def _require_exact_mapping(
    value: Mapping[str, Any],
    expected_fields: frozenset[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PaperSignalContractError(f"{label} must be an object")
    if frozenset(value.keys()) != expected_fields:
        raise PaperSignalContractError(
            f"{label} fields do not match the frozen contract"
        )
    return copy.deepcopy(dict(value))


def _require_mode(value: Any) -> str:
    if not isinstance(value, str) or value not in _ALLOWED_MODES:
        raise PaperSignalContractError(
            "mode must be exactly SWING, INTRADAY, or SCALP"
        )
    return value


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperSignalContractError(f"{field} must be a non-empty string")
    return value


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise PaperSignalContractError(f"{field} must be lowercase SHA-256")
    return value


def _parse_utc_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or _UTC_TIMESTAMP_PATTERN.fullmatch(value) is None:
        raise PaperSignalContractError(
            f"{field} must be an ISO-8601 UTC timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise PaperSignalContractError(
            f"{field} must be a valid ISO-8601 UTC timestamp"
        ) from exc
    if parsed.tzinfo != timezone.utc:
        raise PaperSignalContractError(f"{field} must use UTC")
    return parsed


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
