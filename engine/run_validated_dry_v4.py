import json
from datetime import datetime
from pathlib import Path

from engine.scanner import scan_market
from engine.validated_pipeline_v4 import run_validated_pipeline_v4
from engine.outcome_tracker_v4 import save_outcome_snapshot
from engine.final_reporter_v4 import print_final_report_v4
from engine.top5_watchlist_artifact_v4 import (
    save_top5_watchlist_artifact,
)
from engine.pre_delivery_flow_v4 import (
    run_pre_delivery_flow,
)
from engine.pre_delivery_market_data_v4 import (
    get_closed_ohlcv_for_pre_delivery,
)


def save_snapshot(out):
    directory = Path("data/validated_snapshots_v4")
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = directory / f"validated_v4_{timestamp}.json"

    path.write_text(
        json.dumps(
            out,
            indent=2,
            default=str,
        )
    )

    return path


results = scan_market()

out = run_validated_pipeline_v4(results)

snapshot_path = save_snapshot(out)
outcome_path = save_outcome_snapshot(
    out["final_top5"]
)
watchlist_path = save_top5_watchlist_artifact(
    out["final_top5"]
)
delivery_out = run_pre_delivery_flow(
    watchlist_path,
    "data/top5_watchlist_v4/tradingview_watchlist.txt",
    closed_candle_provider=(
        get_closed_ohlcv_for_pre_delivery
    ),
    validated_at=datetime.now().isoformat(),
)

delivery_artifact_path = delivery_out[
    "delivery_artifact_path"
]
tradingview_watchlist_path = delivery_out[
    "tradingview_watchlist_path"
]

print_final_report_v4(
    out,
    snapshot_path=snapshot_path,
)
