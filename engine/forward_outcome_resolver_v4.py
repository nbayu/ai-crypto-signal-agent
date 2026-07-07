from pathlib import Path
import copy
import json
import os
from datetime import datetime, timezone, timedelta

from engine.binance_client import get_ohlcv


def normalize_reference_candle_utc(reference_candle_at):
    reference_dt = datetime.fromisoformat(reference_candle_at)

    if reference_dt.tzinfo is None:
        return reference_dt.replace(
            tzinfo=timezone.utc
        )

    return reference_dt.astimezone(
        timezone.utc
    )


def derive_resolution_path(entry_path):
    entry_path = Path(entry_path)

    prefix = "outcome_entry_v4_"

    if not entry_path.name.startswith(prefix):
        raise ValueError(
            "Invalid V4 outcome entry artifact name"
        )

    suffix = entry_path.name[len(prefix):]

    return entry_path.with_name(
        "outcome_resolved_v4_"
        + suffix
    )


def build_initial_resolution_state(entry_path, entry_state):
    entry_path = Path(entry_path)

    if list(entry_state.keys()) != [
        "snapshot_type",
        "schema_version",
        "captured_at",
        "candidates",
    ]:
        raise ValueError(
            "Invalid V4 outcome entry top-level schema"
        )

    if entry_state["snapshot_type"] != "v4_outcome_tracker_entry":
        raise ValueError(
            "Invalid V4 outcome entry snapshot type"
        )

    if entry_state["schema_version"] != 1:
        raise ValueError(
            "Invalid V4 outcome entry schema version"
        )

    candidates = entry_state["candidates"]

    if not isinstance(candidates, list) or not candidates:
        raise ValueError(
            "Invalid V4 outcome entry candidates"
        )

    expected_candidate_keys = [
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

    expected_ai_validation_keys = [
        "status",
        "false_breakout_risk",
        "confluence",
        "reason_code",
    ]

    for row in candidates:
        if list(row.keys()) != expected_candidate_keys:
            raise ValueError(
                "Invalid V4 outcome entry candidate schema"
            )

        if list(row["ai_validation"].keys()) != expected_ai_validation_keys:
            raise ValueError(
                "Invalid V4 outcome entry AI validation schema"
            )

    reference_times = {
        row["reference_candle_at"]
        for row in candidates
    }

    if len(reference_times) != 1:
        raise ValueError(
            "V4 outcome entry candidates do not share one reference candle"
        )

    reference_candle_at = next(
        iter(reference_times)
    )

    normalize_reference_candle_utc(
        reference_candle_at
    )

    return {
        "snapshot_type": "v4_forward_outcome_resolution",
        "schema_version": 1,
        "entry_artifact": entry_path.name,
        "entry_snapshot_type": entry_state["snapshot_type"],
        "entry_schema_version": entry_state["schema_version"],
        "entry_captured_at": entry_state["captured_at"],
        "reference_candle_at": reference_candle_at,
        "candidates": [
            {
                "symbol": row["symbol"],
                "reference_price": row["reference_price"],
                "resolved_horizons": {},
            }
            for row in candidates
        ],
    }


def validate_existing_resolution_state(
    resolution_state,
    entry_path,
    entry_state,
):
    expected_state = build_initial_resolution_state(
        entry_path,
        entry_state,
    )

    expected_top_keys = [
        "snapshot_type",
        "schema_version",
        "entry_artifact",
        "entry_snapshot_type",
        "entry_schema_version",
        "entry_captured_at",
        "reference_candle_at",
        "candidates",
    ]

    if list(resolution_state.keys()) != expected_top_keys:
        raise ValueError(
            "Existing resolution top-level schema mismatch"
        )

    identity_fields = [
        "snapshot_type",
        "schema_version",
        "entry_artifact",
        "entry_snapshot_type",
        "entry_schema_version",
        "entry_captured_at",
        "reference_candle_at",
    ]

    for field in identity_fields:
        if resolution_state[field] != expected_state[field]:
            raise ValueError(
                f"Existing resolution identity mismatch: {field}"
            )

    existing_candidates = resolution_state["candidates"]
    expected_candidates = expected_state["candidates"]

    if len(existing_candidates) != len(expected_candidates):
        raise ValueError(
            "Existing resolution candidate count mismatch"
        )

    expected_candidate_keys = [
        "symbol",
        "reference_price",
        "resolved_horizons",
    ]

    allowed_horizons = {
        "h4",
        "h8",
        "h12",
    }

    expected_horizon_keys = [
        "horizon",
        "target_at",
        "return_price",
        "return_pct",
        "mfe_price",
        "mfe_pct",
        "mae_price",
        "mae_pct",
    ]

    for existing, expected in zip(
        existing_candidates,
        expected_candidates,
    ):
        if list(existing.keys()) != expected_candidate_keys:
            raise ValueError(
                "Existing resolution candidate schema mismatch"
            )

        if existing["symbol"] != expected["symbol"]:
            raise ValueError(
                "Existing resolution candidate symbol mismatch"
            )

        if existing["reference_price"] != expected["reference_price"]:
            raise ValueError(
                "Existing resolution candidate reference price mismatch"
            )

        resolved_horizons = existing["resolved_horizons"]

        if not isinstance(resolved_horizons, dict):
            raise ValueError(
                "Existing resolved_horizons must be a dictionary"
            )

        for horizon_name, horizon_result in resolved_horizons.items():
            if horizon_name not in allowed_horizons:
                raise ValueError(
                    "Existing resolution contains unknown horizon"
                )

            if not isinstance(horizon_result, dict):
                raise ValueError(
                    "Existing horizon result must be a dictionary"
                )

            if list(horizon_result.keys()) != expected_horizon_keys:
                raise ValueError(
                    "Existing horizon result schema mismatch"
                )

            if horizon_result["horizon"] != horizon_name:
                raise ValueError(
                    "Existing horizon identity mismatch"
                )

    return True


def load_or_initialize_resolution_state(
    resolution_path,
    entry_path,
    entry_state,
):
    resolution_path = Path(resolution_path)

    if not resolution_path.exists():
        return build_initial_resolution_state(
            entry_path,
            entry_state,
        )

    resolution_state = json.loads(
        resolution_path.read_text()
    )

    validate_existing_resolution_state(
        resolution_state,
        entry_path,
        entry_state,
    )

    return resolution_state


def get_horizon_contracts(reference_candle_utc):
    reference_close_utc = (
        reference_candle_utc
        + timedelta(hours=4)
    )

    return {
        "h4": {
            "target_at": (
                reference_close_utc
                + timedelta(hours=4)
            ),
            "expected_candle_count": 1,
        },
        "h8": {
            "target_at": (
                reference_close_utc
                + timedelta(hours=8)
            ),
            "expected_candle_count": 2,
        },
        "h12": {
            "target_at": (
                reference_close_utc
                + timedelta(hours=12)
            ),
            "expected_candle_count": 3,
        },
    }


def get_eligible_unresolved_horizons(
    resolution_state,
    horizon_contracts,
    now_utc,
):
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(
            tzinfo=timezone.utc
        )
    else:
        now_utc = now_utc.astimezone(
            timezone.utc
        )

    eligible = {}

    for candidate_state in resolution_state["candidates"]:
        unresolved = []

        for horizon_name, contract in horizon_contracts.items():
            if horizon_name in candidate_state["resolved_horizons"]:
                continue

            if now_utc >= contract["target_at"]:
                unresolved.append(
                    horizon_name
                )

        if unresolved:
            eligible[candidate_state["symbol"]] = unresolved

    return eligible


def select_exact_closed_candle_window(
    df,
    reference_close_utc,
    horizon_target_utc,
):
    candle_size = timedelta(hours=4)

    expected_opens_utc = []
    cursor = reference_close_utc

    while cursor + candle_size <= horizon_target_utc:
        expected_opens_utc.append(
            cursor
        )
        cursor += candle_size

    expected_naive = [
        timestamp.replace(tzinfo=None)
        for timestamp in expected_opens_utc
    ]

    if int(df["timestamp"].duplicated().sum()) != 0:
        raise ValueError(
            "Duplicate OHLCV timestamps found"
        )

    window = df[
        df["timestamp"].isin(expected_naive)
    ].copy()

    actual_timestamps = list(
        window["timestamp"]
    )

    if len(actual_timestamps) != len(expected_naive):
        raise ValueError(
            "Exact closed-candle window count mismatch"
        )

    if actual_timestamps != expected_naive:
        raise ValueError(
            "Exact closed-candle timestamp set mismatch"
        )

    return window


def calculate_horizon_result(
    window,
    reference_price,
):
    if len(window) == 0:
        raise ValueError(
            "Cannot calculate horizon result from empty window"
        )

    reference_price = float(
        reference_price
    )

    if reference_price <= 0:
        raise ValueError(
            "Reference price must be positive"
        )

    return_price = float(
        window.iloc[-1]["close"]
    )

    mfe_price = float(
        window["high"].max()
    )

    mae_price = float(
        window["low"].min()
    )

    return {
        "return_price": return_price,
        "return_pct": (
            (return_price / reference_price)
            - 1
        ) * 100,
        "mfe_price": mfe_price,
        "mfe_pct": (
            (mfe_price / reference_price)
            - 1
        ) * 100,
        "mae_price": mae_price,
        "mae_pct": (
            (mae_price / reference_price)
            - 1
        ) * 100,
    }


def merge_horizon_once(
    candidate_state,
    horizon_name,
    horizon_result,
):
    resolved_horizons = candidate_state[
        "resolved_horizons"
    ]

    if horizon_name not in resolved_horizons:
        resolved_horizons[horizon_name] = copy.deepcopy(
            horizon_result
        )
        return True

    if resolved_horizons[horizon_name] == horizon_result:
        return False

    raise ValueError(
        f"Conflicting existing horizon result: {horizon_name}"
    )


def write_resolution_state_atomic(
    resolution_path,
    resolution_state,
):
    resolution_path = Path(
        resolution_path
    )

    temp_path = resolution_path.with_name(
        resolution_path.name
        + ".tmp"
    )

    serialized = json.dumps(
        resolution_state,
        indent=2,
    )

    try:
        temp_path.write_text(
            serialized
        )

        os.replace(
            temp_path,
            resolution_path,
        )
    except Exception:
        if temp_path.exists():
            temp_path.unlink()

        raise


def resolve_entry_artifact(
    entry_path,
    now_utc,
):
    entry_path = Path(
        entry_path
    )

    entry_state = json.loads(
        entry_path.read_text()
    )

    initial_state = build_initial_resolution_state(
        entry_path,
        entry_state,
    )

    resolution_path = derive_resolution_path(
        entry_path
    )

    resolution_state = load_or_initialize_resolution_state(
        resolution_path,
        entry_path,
        entry_state,
    )

    validate_existing_resolution_state(
        resolution_state,
        entry_path,
        entry_state,
    )

    reference_candle_utc = normalize_reference_candle_utc(
        initial_state["reference_candle_at"]
    )

    reference_close_utc = (
        reference_candle_utc
        + timedelta(hours=4)
    )

    horizon_contracts = get_horizon_contracts(
        reference_candle_utc
    )

    eligible = get_eligible_unresolved_horizons(
        resolution_state,
        horizon_contracts,
        now_utc,
    )

    if not eligible:
        if not resolution_path.exists():
            write_resolution_state_atomic(
                resolution_path,
                resolution_state,
            )

        return {
            "entry_path": str(entry_path),
            "resolution_path": str(resolution_path),
            "changed": False,
            "resolved_horizons_added": 0,
        }

    working_state = copy.deepcopy(
        resolution_state
    )

    changed = False
    resolved_horizons_added = 0

    for candidate_state in working_state["candidates"]:
        symbol = candidate_state["symbol"]

        if symbol not in eligible:
            continue

        df = get_ohlcv(
            symbol
        )

        pending_results = []

        for horizon_name in eligible[symbol]:
            contract = horizon_contracts[
                horizon_name
            ]

            window = select_exact_closed_candle_window(
                df,
                reference_close_utc,
                contract["target_at"],
            )

            if len(window) != contract["expected_candle_count"]:
                raise ValueError(
                    f"{horizon_name.upper()} exact closed-candle count mismatch"
                )

            calculated = calculate_horizon_result(
                window,
                candidate_state["reference_price"],
            )

            horizon_result = {
                "horizon": horizon_name,
                "target_at": contract["target_at"].isoformat(),
                "return_price": calculated["return_price"],
                "return_pct": calculated["return_pct"],
                "mfe_price": calculated["mfe_price"],
                "mfe_pct": calculated["mfe_pct"],
                "mae_price": calculated["mae_price"],
                "mae_pct": calculated["mae_pct"],
            }

            pending_results.append(
                (
                    horizon_name,
                    horizon_result,
                )
            )

        candidate_before = copy.deepcopy(
            candidate_state
        )

        try:
            for horizon_name, horizon_result in pending_results:
                added = merge_horizon_once(
                    candidate_state,
                    horizon_name,
                    horizon_result,
                )

                if added:
                    changed = True
                    resolved_horizons_added += 1
        except Exception:
            candidate_state.clear()
            candidate_state.update(
                candidate_before
            )
            raise

    if changed:
        write_resolution_state_atomic(
            resolution_path,
            working_state,
        )

    return {
        "entry_path": str(entry_path),
        "resolution_path": str(resolution_path),
        "changed": changed,
        "resolved_horizons_added": resolved_horizons_added,
    }
