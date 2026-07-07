import json
from datetime import datetime
from pathlib import Path

from engine.scanner import scan_market
from engine.validated_pipeline_v4 import run_validated_pipeline_v4
from engine.outcome_tracker_v4 import save_outcome_snapshot


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

print()
print("SNAPSHOT SAVED:", snapshot_path)

print()
print("=" * 120)
print("V4 FULL TOP 10 AUDIT")
print("=" * 120)

for i, row in enumerate(out["controlled_top10"], 1):
    ai = row["ai_validation"]

    print(
        f"{i}. {row['symbol']} | "
        f"PY {row['python_score']:.2f} | "
        f"ADJ {row['validation_adjustment']:+} | "
        f"FINAL {row['final_rank_score']:.2f} | "
        f"VOL {row['volume_ratio']} {row['volume_class']} | "
        f"OI {row['oi_change_pct']}% {row['oi_class']} | "
        f"PART {row['participation']} | "
        f"{ai['status']} | "
        f"{ai['false_breakout_risk']} | "
        f"{ai['confluence']} | "
        f"{ai['reason_code']}"
    )

print()
print("=" * 120)
print("V4 FINAL TOP 5")
print("=" * 120)

for i, row in enumerate(out["final_top5"], 1):
    ai = row["ai_validation"]

    print(
        f"{i}. {row['symbol']} | "
        f"PY {row['python_score']:.2f} | "
        f"ADJ {row['validation_adjustment']:+} | "
        f"FINAL {row['final_rank_score']:.2f} | "
        f"PART {row['participation']} | "
        f"{ai['status']} | "
        f"{ai['reason_code']}"
    )

print()
print("=" * 120)
print("V4 LLM USAGE")
print("=" * 120)
print(json.dumps(out["usage"], indent=2))
