import json
from datetime import datetime
from pathlib import Path

from engine.scanner import scan_market
from engine.validated_pipeline_v4 import run_validated_pipeline_v4
from engine.outcome_tracker_v4 import save_outcome_snapshot
from engine.final_reporter_v4 import print_final_report_v4


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

print_final_report_v4(
    out,
    snapshot_path=snapshot_path,
)
