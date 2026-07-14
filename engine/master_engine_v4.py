import json
from datetime import datetime
from pathlib import Path

from engine.scanner import scan_market
from engine.validated_pipeline_v4 import run_validated_pipeline_v4
from engine.outcome_tracker_v4 import save_outcome_snapshot
from engine.top5_watchlist_artifact_v4 import (
    save_top5_watchlist_artifact,
)
from engine.pre_delivery_flow_v4 import (
    run_pre_delivery_flow,
)
from engine.pre_delivery_market_data_v4 import (
    get_closed_ohlcv_for_pre_delivery,
)
from engine.production_evidence_v4 import (
    save_production_evidence,
)


def save_validated_snapshot_v4(out, *, directory=None, now=None):
    if directory is None:
        directory = Path("data/validated_snapshots_v4")

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    if now is None:
        now = datetime.now()

    timestamp = now.strftime("%Y%m%d_%H%M%S")
    path = directory / f"validated_v4_{timestamp}.json"

    path.write_text(
        json.dumps(
            out,
            indent=2,
            default=str,
        )
    )

    return path


def run_master_engine_v4(
    *,
    scanner=scan_market,
    pipeline=run_validated_pipeline_v4,
    snapshot_saver=save_validated_snapshot_v4,
    outcome_saver=save_outcome_snapshot,
    watchlist_saver=save_top5_watchlist_artifact,
    pre_delivery_runner=run_pre_delivery_flow,
    closed_candle_provider=get_closed_ohlcv_for_pre_delivery,
    production_evidence_saver=save_production_evidence,
    now_provider=datetime.now,
):
    results = scanner()

    out = pipeline(results)

    now = now_provider()
    validated_at = now.isoformat()

    snapshot_path = snapshot_saver(
        out,
        now=now,
    )
    outcome_path = outcome_saver(
        out["final_top5"]
    )
    watchlist_path = watchlist_saver(
        out["final_top5"]
    )
    delivery_out = pre_delivery_runner(
        watchlist_path,
        "data/top5_watchlist_v4/tradingview_watchlist.txt",
        closed_candle_provider=(
            closed_candle_provider
        ),
        validated_at=validated_at,
    )

    delivery_artifact_path = delivery_out[
        "delivery_artifact_path"
    ]
    tradingview_watchlist_path = delivery_out[
        "tradingview_watchlist_path"
    ]

    evidence_path = production_evidence_saver(
        created_at=validated_at,
        validated_snapshot_path=snapshot_path,
        outcome_entry_path=outcome_path,
        raw_top5_path=watchlist_path,
        pre_delivery_path=delivery_artifact_path,
        tradingview_watchlist_path=(
            tradingview_watchlist_path
        ),
    )

    return {
        "results": results,
        "out": out,
        "snapshot_path": snapshot_path,
        "outcome_path": outcome_path,
        "watchlist_path": watchlist_path,
        "delivery_out": delivery_out,
        "evidence_path": evidence_path,
    }
