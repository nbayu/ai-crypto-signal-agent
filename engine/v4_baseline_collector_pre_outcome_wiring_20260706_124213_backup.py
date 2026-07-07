import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from engine.scanner import scan_market
from engine.validated_pipeline_v4 import run_validated_pipeline_v4
from engine.validation_semantic_guard_v4 import (
    SemanticValidationError,
)


def build_summary(out):
    rows = out["controlled_top10"]

    participation = Counter()
    status = Counter()
    reason = Counter()
    penalties = Counter()

    evidence_pairs = Counter()

    for row in rows:
        ai = row["ai_validation"]

        participation[row["participation"]] += 1
        status[ai["status"]] += 1
        reason[ai["reason_code"]] += 1
        penalties[str(row["validation_adjustment"])] += 1

        pair = (
            f"{row['volume_class']}"
            f"+{row['oi_class']}"
            f"->{row['participation']}"
        )

        evidence_pairs[pair] += 1

    return {
        "timestamp": datetime.now().isoformat(),
        "candidate_count": len(rows),
        "participation": dict(participation),
        "status": dict(status),
        "reason": dict(reason),
        "penalties": dict(penalties),
        "evidence_pairs": dict(evidence_pairs),
        "controlled_top10": [
            {
                "symbol": row["symbol"],
                "python_score": row["python_score"],
                "validation_adjustment":
                    row["validation_adjustment"],
                "final_rank_score":
                    row["final_rank_score"],

                "trend": row["trend"],
                "bos": row["bos"],
                "choch": row["choch"],

                "volume_ratio": row["volume_ratio"],
                "volume_class": row["volume_class"],

                "oi_change_pct": row["oi_change_pct"],
                "oi_class": row["oi_class"],

                "participation": row["participation"],

                "status":
                    row["ai_validation"]["status"],
                "false_breakout_risk":
                    row["ai_validation"]["false_breakout_risk"],
                "confluence":
                    row["ai_validation"]["confluence"],
                "reason_code":
                    row["ai_validation"]["reason_code"],
            }
            for row in rows
        ],
        "final_top5": [
            {
                "symbol": row["symbol"],
                "python_score": row["python_score"],
                "validation_adjustment":
                    row["validation_adjustment"],
                "final_rank_score":
                    row["final_rank_score"],
                "volume_class": row["volume_class"],
                "oi_class": row["oi_class"],
                "participation": row["participation"],
                "status":
                    row["ai_validation"]["status"],
                "reason_code":
                    row["ai_validation"]["reason_code"],
            }
            for row in out["final_top5"]
        ],
        "usage": out["usage"],
    }



def main():
    results = scan_market()

    try:
        out = run_validated_pipeline_v4(results)

    except SemanticValidationError as e:
        directory = Path(
            "data/v4_semantic_rejections"
        )
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        path = directory / (
            f"semantic_rejection_v4_{timestamp}.json"
        )

        rejection = {
            "event_type":
                "SEMANTIC_VALIDATION_REJECTION",
            "symbol": e.symbol,
            "errors": e.errors,
            "candidate": e.candidate,
            "invalid_validation": e.validation,
        }

        path.write_text(
            json.dumps(
                rejection,
                indent=2,
                default=str,
            )
        )

        print("=" * 80)
        print("V4 SEMANTIC REJECTION CAPTURED")
        print("=" * 80)
        print("FILE   :", path)
        print("SYMBOL :", e.symbol)
        print("ERRORS :", e.errors)
        print()
        print("NO BASELINE CREATED ✅")
        print("NO FINAL RANKING CREATED ✅")

        raise

    summary = build_summary(out)

    directory = Path("data/v4_baselines")
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = directory / f"baseline_v4_{timestamp}.json"

    path.write_text(
        json.dumps(
            summary,
            indent=2,
            default=str,
        )
    )

    print("=" * 80)
    print("V4 BASELINE COLLECTED")
    print("=" * 80)

    print("FILE          :", path)
    print("CANDIDATES    :", summary["candidate_count"])
    print("PARTICIPATION :", summary["participation"])
    print("STATUS        :", summary["status"])
    print("REASON        :", summary["reason"])
    print("PENALTIES     :", summary["penalties"])

    print()
    print("EVIDENCE PAIRS")

    for pair, count in sorted(
        summary["evidence_pairs"].items()
    ):
        print(f"{count:>2}x  {pair}")

    print()
    print("V4 BASELINE COLLECTION PASS ✅")


if __name__ == "__main__":
    main()
