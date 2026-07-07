import json


SEPARATOR_WIDTH = 120


def render_final_report_v4(out, snapshot_path=None):
    controlled_top10 = out["controlled_top10"]
    final_top5 = out["final_top5"]
    usage = out["usage"]

    lines = []

    if snapshot_path is not None:
        lines.extend([
            "",
            f"SNAPSHOT SAVED: {snapshot_path}",
        ])

    lines.extend([
        "",
        "=" * SEPARATOR_WIDTH,
        "V4 FULL TOP 10 AUDIT",
        "=" * SEPARATOR_WIDTH,
    ])

    for i, row in enumerate(controlled_top10, 1):
        ai = row["ai_validation"]

        lines.append(
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

    lines.extend([
        "",
        "=" * SEPARATOR_WIDTH,
        "V4 FINAL TOP 5",
        "=" * SEPARATOR_WIDTH,
    ])

    for i, row in enumerate(final_top5, 1):
        ai = row["ai_validation"]

        lines.append(
            f"{i}. {row['symbol']} | "
            f"PY {row['python_score']:.2f} | "
            f"ADJ {row['validation_adjustment']:+} | "
            f"FINAL {row['final_rank_score']:.2f} | "
            f"PART {row['participation']} | "
            f"{ai['status']} | "
            f"{ai['reason_code']}"
        )

    lines.extend([
        "",
        "=" * SEPARATOR_WIDTH,
        "V4 LLM USAGE",
        "=" * SEPARATOR_WIDTH,
        json.dumps(usage, indent=2),
    ])

    return "\n".join(lines)


def print_final_report_v4(out, snapshot_path=None):
    print(
        render_final_report_v4(
            out,
            snapshot_path=snapshot_path,
        )
    )
