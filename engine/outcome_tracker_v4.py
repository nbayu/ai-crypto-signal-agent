from datetime import datetime
from pathlib import Path
import json


OUTCOME_DIRECTORY = Path("data/v4_outcomes")
SCHEMA_VERSION = 1
SNAPSHOT_TYPE = "v4_outcome_tracker_entry"


def build_outcome_snapshot_row(row):
    ai = row["ai_validation"]

    return {
        "symbol": row["symbol"],
        "reference_price": row["reference_price"],
        "reference_candle_at": row["reference_candle_at"],
        "python_score": row["python_score"],
        "validation_adjustment": row["validation_adjustment"],
        "final_rank_score": row["final_rank_score"],
        "trend": row["trend"],
        "bos": row["bos"],
        "choch": row["choch"],
        "volume_ratio": row["volume_ratio"],
        "volume_class": row["volume_class"],
        "oi_change_pct": row["oi_change_pct"],
        "oi_class": row["oi_class"],
        "participation": row["participation"],
        "ai_validation": {
            "status": ai["status"],
            "false_breakout_risk": ai["false_breakout_risk"],
            "confluence": ai["confluence"],
            "reason_code": ai["reason_code"],
        },
    }


def build_outcome_snapshot(final_top5, captured_at=None):
    if captured_at is None:
        captured_at = datetime.now().isoformat()

    return {
        "snapshot_type": SNAPSHOT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at,
        "candidates": [
            build_outcome_snapshot_row(row)
            for row in final_top5
        ],
    }


def save_outcome_snapshot(final_top5):
    snapshot = build_outcome_snapshot(final_top5)

    OUTCOME_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    path = (
        OUTCOME_DIRECTORY
        / f"outcome_entry_v4_{timestamp}.json"
    )

    path.write_text(
        json.dumps(
            snapshot,
            indent=2,
        )
    )

    return path
