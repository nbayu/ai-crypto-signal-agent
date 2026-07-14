import json
from datetime import datetime
from pathlib import Path


WATCHLIST_DIRECTORY = Path("data/top5_watchlist_v4")
WATCHLIST_FILENAME = "latest.json"


def serialize_artifact_value(value):
    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return isoformat()

    return str(value)


def build_top5_watchlist_artifact(
    final_top5,
    *,
    now_provider=None,
):
    resolved_now_provider = (
        datetime.now
        if now_provider is None
        else now_provider
    )
    generated_at = resolved_now_provider().isoformat()

    setups = []

    for rank, row in enumerate(final_top5, 1):
        golden_zone = row.get("golden_zone")

        setups.append({
            "rank": rank,
            "symbol": row["symbol"],
            "final_rank_score": row["final_rank_score"],
            "reference_price": row["reference_price"],
            "reference_candle_at": row["reference_candle_at"],
            "golden_zone": golden_zone,
        })

    return {
        "generated_at": generated_at,
        "setup_count": len(setups),
        "setups": setups,
    }


def save_top5_watchlist_artifact(final_top5):
    WATCHLIST_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact = build_top5_watchlist_artifact(final_top5)
    path = WATCHLIST_DIRECTORY / WATCHLIST_FILENAME

    path.write_text(
        json.dumps(
            artifact,
            indent=2,
            default=serialize_artifact_value,
        )
    )

    return path
