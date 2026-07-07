import json

from engine.scanner import scan_market
from engine.validated_pipeline import run_validated_pipeline


print("=" * 60)
print("VALIDATED PIPELINE — LIVE DRY RUN")
print("=" * 60)

results = scan_market()

if not results:
    print("NO_RESULTS")
    raise SystemExit(0)

out = run_validated_pipeline(results)

print()
print("=" * 60)
print("FULL TOP 10 AUDIT")
print("=" * 60)

for i, row in enumerate(out["controlled_top10"], 1):
    validation = row["ai_validation"]

    print(
        f"{i}. {row['symbol']} | "
        f"PY {row['python_score']:.2f} | "
        f"ADJ {row['validation_adjustment']:+.0f} | "
        f"FINAL {row['final_rank_score']:.2f} | "
        f"{validation['status']} | "
        f"{validation['false_breakout_risk']} | "
        f"{validation['confluence']} | "
        f"{validation['reason_code']}"
    )

print()
print("=" * 60)
print("FINAL TOP 5")
print("=" * 60)

for i, row in enumerate(out["final_top5"], 1):
    validation = row["ai_validation"]

    print(
        f"{i}. {row['symbol']} | "
        f"PY {row['python_score']:.2f} | "
        f"ADJ {row['validation_adjustment']:+.0f} | "
        f"FINAL {row['final_rank_score']:.2f} | "
        f"{validation['status']} | "
        f"{validation['reason_code']}"
    )

print()
print("=" * 60)
print("LLM USAGE")
print("=" * 60)
print(json.dumps(out["usage"], indent=2))
