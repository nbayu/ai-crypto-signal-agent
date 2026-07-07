import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path


HORIZONS = [
    "h4",
    "h8",
    "h12",
]

RESOLVED_TOP_KEYS = [
    "snapshot_type",
    "schema_version",
    "entry_artifact",
    "entry_snapshot_type",
    "entry_schema_version",
    "entry_captured_at",
    "reference_candle_at",
    "candidates",
]

ENTRY_TOP_KEYS = [
    "snapshot_type",
    "schema_version",
    "captured_at",
    "candidates",
]

ENTRY_CANDIDATE_KEYS = [
    "symbol",
    "reference_price",
    "reference_candle_at",
    "python_score",
    "validation_adjustment",
    "final_rank_score",
    "trend",
    "bos",
    "choch",
    "volume_ratio",
    "volume_class",
    "oi_change_pct",
    "oi_class",
    "participation",
    "ai_validation",
]

AI_VALIDATION_KEYS = [
    "status",
    "false_breakout_risk",
    "confluence",
    "reason_code",
]

RESOLVED_CANDIDATE_KEYS = [
    "symbol",
    "reference_price",
    "resolved_horizons",
]

HORIZON_KEYS = [
    "horizon",
    "target_at",
    "return_price",
    "return_pct",
    "mfe_price",
    "mfe_pct",
    "mae_price",
    "mae_pct",
]

NUMERIC_HORIZON_FIELDS = [
    "return_price",
    "return_pct",
    "mfe_price",
    "mfe_pct",
    "mae_price",
    "mae_pct",
]

ALLOWED_TRENDS = {
    "UPTREND",
    "DOWNTREND",
}


def validate_resolved_artifact(resolved_path):
    resolved_path = Path(resolved_path)
    resolved = _load_json(resolved_path)

    _validate_resolved_schema(resolved)

    entry_path = resolved_path.parent / resolved["entry_artifact"]

    if not entry_path.exists():
        raise ValueError("Linked V4 outcome entry artifact is missing")

    entry = _load_json(entry_path)

    _validate_entry_schema(entry)
    _validate_resolved_entry_identity(resolved, entry)

    expected_targets = _expected_target_at(
        resolved["reference_candle_at"]
    )

    candidates = []
    counts = {
        "total": len(resolved["candidates"]),
        "pending": 0,
        "valid": 0,
        "invalid": 0,
        "inconclusive": 0,
    }

    for resolved_candidate, entry_candidate in zip(
        resolved["candidates"],
        entry["candidates"],
    ):
        candidate_report = _build_candidate_report(
            resolved_candidate,
            entry_candidate,
            expected_targets,
        )

        status = candidate_report["validation_status"]
        counts[status.lower()] += 1
        candidates.append(candidate_report)

    snapshot_status = (
        "PARTIAL"
        if counts["pending"] > 0
        else "COMPLETE"
    )

    return {
        "artifact_type": "forward_test_validation_report_v4",
        "schema_version": 1,
        "source_resolved_artifact": str(resolved_path),
        "linked_entry_artifact": str(entry_path),
        "snapshot_status": snapshot_status,
        "counts": counts,
        "candidates": candidates,
    }


def _load_json(path):
    try:
        return json.loads(
            Path(path).read_text()
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON artifact: {path}"
        ) from e


def _validate_resolved_schema(resolved):
    if not isinstance(resolved, dict):
        raise ValueError("Resolved artifact must be an object")

    if list(resolved.keys()) != RESOLVED_TOP_KEYS:
        raise ValueError("Malformed V4 resolved artifact top-level schema")

    if resolved["snapshot_type"] != "v4_forward_outcome_resolution":
        raise ValueError("Invalid V4 resolved artifact snapshot_type")

    if resolved["schema_version"] != 1:
        raise ValueError("Invalid V4 resolved artifact schema_version")

    if resolved["entry_snapshot_type"] != "v4_outcome_tracker_entry":
        raise ValueError("Invalid linked entry snapshot_type identity")

    if resolved["entry_schema_version"] != 1:
        raise ValueError("Invalid linked entry schema_version identity")

    candidates = resolved["candidates"]

    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Invalid V4 resolved artifact candidates")

    symbols = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Resolved candidate must be an object")

        if list(candidate.keys()) != RESOLVED_CANDIDATE_KEYS:
            raise ValueError("Malformed V4 resolved candidate schema")

        symbols.append(candidate["symbol"])

        _require_number(
            candidate["reference_price"],
            "reference_price",
        )

        resolved_horizons = candidate["resolved_horizons"]

        if not isinstance(resolved_horizons, dict):
            raise ValueError("resolved_horizons must be an object")

        _validate_resolved_horizons(resolved_horizons)

    _reject_duplicate_symbols(symbols)


def _validate_resolved_horizons(resolved_horizons):
    for horizon_name, horizon in resolved_horizons.items():
        if horizon_name not in HORIZONS:
            raise ValueError("Unknown V4 resolved horizon")

        if not isinstance(horizon, dict):
            raise ValueError("Resolved horizon must be an object")

        if list(horizon.keys()) != HORIZON_KEYS:
            raise ValueError("Malformed V4 horizon object")

        if horizon["horizon"] != horizon_name:
            raise ValueError("Resolved horizon identity mismatch")

        for field in NUMERIC_HORIZON_FIELDS:
            _require_number(
                horizon[field],
                field,
            )


def _validate_entry_schema(entry):
    if not isinstance(entry, dict):
        raise ValueError("Linked entry artifact must be an object")

    if list(entry.keys()) != ENTRY_TOP_KEYS:
        raise ValueError("Malformed V4 linked entry top-level schema")

    if entry["snapshot_type"] != "v4_outcome_tracker_entry":
        raise ValueError("Invalid V4 linked entry snapshot_type")

    if entry["schema_version"] != 1:
        raise ValueError("Invalid V4 linked entry schema_version")

    candidates = entry["candidates"]

    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Invalid V4 linked entry candidates")

    symbols = []
    reference_times = set()

    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Linked entry candidate must be an object")

        if list(candidate.keys()) != ENTRY_CANDIDATE_KEYS:
            raise ValueError("Malformed V4 linked entry candidate schema")

        if not isinstance(candidate["ai_validation"], dict):
            raise ValueError("Linked entry AI validation must be an object")

        if list(candidate["ai_validation"].keys()) != AI_VALIDATION_KEYS:
            raise ValueError("Malformed V4 linked entry AI validation schema")

        trend = candidate["trend"]

        if trend not in ALLOWED_TRENDS:
            raise ValueError("Unsupported V4 directional trend")

        symbols.append(candidate["symbol"])
        reference_times.add(candidate["reference_candle_at"])

        _require_number(
            candidate["reference_price"],
            "reference_price",
        )

    _reject_duplicate_symbols(symbols)

    if len(reference_times) != 1:
        raise ValueError("Linked entry candidates must share one reference candle")

    _normalize_reference_candle_utc(
        next(iter(reference_times))
    )


def _validate_resolved_entry_identity(resolved, entry):
    identity_pairs = [
        ("entry_snapshot_type", "snapshot_type"),
        ("entry_schema_version", "schema_version"),
        ("entry_captured_at", "captured_at"),
        ("reference_candle_at", None),
    ]

    for resolved_field, entry_field in identity_pairs:
        entry_value = (
            entry[entry_field]
            if entry_field is not None
            else entry["candidates"][0]["reference_candle_at"]
        )

        if resolved[resolved_field] != entry_value:
            raise ValueError(
                f"Resolved/entry identity mismatch: {resolved_field}"
            )

    if len(resolved["candidates"]) != len(entry["candidates"]):
        raise ValueError("Resolved/entry candidate count mismatch")

    for resolved_candidate, entry_candidate in zip(
        resolved["candidates"],
        entry["candidates"],
    ):
        if resolved_candidate["symbol"] != entry_candidate["symbol"]:
            raise ValueError("Resolved/entry candidate symbol mismatch")

        if resolved_candidate["reference_price"] != entry_candidate["reference_price"]:
            raise ValueError("Resolved/entry candidate reference_price mismatch")


def _build_candidate_report(
    resolved_candidate,
    entry_candidate,
    expected_targets,
):
    resolved_horizons = resolved_candidate["resolved_horizons"]

    present = [
        horizon
        for horizon in HORIZONS
        if horizon in resolved_horizons
    ]

    missing = [
        horizon
        for horizon in HORIZONS
        if horizon not in resolved_horizons
    ]

    horizon_votes = {}
    horizon_facts = {}
    trend = entry_candidate["trend"]

    for horizon_name in present:
        horizon = resolved_horizons[horizon_name]

        if horizon["target_at"] != expected_targets[horizon_name]:
            raise ValueError("Resolved horizon target_at contract mismatch")

        horizon_votes[horizon_name] = _vote_horizon(
            trend,
            horizon["return_pct"],
        )

        horizon_facts[horizon_name] = {
            "target_at": horizon["target_at"],
            "return_pct": horizon["return_pct"],
            "mfe_pct": horizon["mfe_pct"],
            "mae_pct": horizon["mae_pct"],
        }

    validation_status = _candidate_status(
        horizon_votes
    )

    return {
        "symbol": resolved_candidate["symbol"],
        "reference_price": resolved_candidate["reference_price"],
        "trend": trend,
        "resolved_horizons_present": present,
        "missing_horizons": missing,
        "horizon_votes": horizon_votes,
        "validation_status": validation_status,
        "horizon_facts": horizon_facts,
    }


def _candidate_status(horizon_votes):
    if "h12" not in horizon_votes:
        return "PENDING"

    support = sum(
        1
        for vote in horizon_votes.values()
        if vote == "SUPPORT"
    )

    oppose = sum(
        1
        for vote in horizon_votes.values()
        if vote == "OPPOSE"
    )

    if support > oppose:
        return "VALID"

    if oppose > support:
        return "INVALID"

    return "INCONCLUSIVE"


def _vote_horizon(trend, return_pct):
    if return_pct == 0:
        return "FLAT"

    if trend == "UPTREND":
        return (
            "SUPPORT"
            if return_pct > 0
            else "OPPOSE"
        )

    if trend == "DOWNTREND":
        return (
            "SUPPORT"
            if return_pct < 0
            else "OPPOSE"
        )

    raise ValueError("Unsupported V4 directional trend")


def _expected_target_at(reference_candle_at):
    reference_candle_utc = _normalize_reference_candle_utc(
        reference_candle_at
    )

    reference_close_utc = (
        reference_candle_utc
        + timedelta(hours=4)
    )

    return {
        "h4": (
            reference_close_utc
            + timedelta(hours=4)
        ).isoformat(),
        "h8": (
            reference_close_utc
            + timedelta(hours=8)
        ).isoformat(),
        "h12": (
            reference_close_utc
            + timedelta(hours=12)
        ).isoformat(),
    }


def _normalize_reference_candle_utc(reference_candle_at):
    try:
        reference_dt = datetime.fromisoformat(
            reference_candle_at
        )
    except (TypeError, ValueError) as e:
        raise ValueError("Invalid V4 reference_candle_at") from e

    if reference_dt.tzinfo is None:
        return reference_dt.replace(
            tzinfo=timezone.utc
        )

    return reference_dt.astimezone(
        timezone.utc
    )


def _require_number(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be a finite number"
        )

    if not math.isfinite(value):
        raise ValueError(
            f"{field_name} must be a finite number"
        )


def _reject_duplicate_symbols(symbols):
    if len(symbols) != len(set(symbols)):
        raise ValueError("Duplicate V4 candidate symbols")
