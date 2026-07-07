from engine.validated_pipeline_v4 import build_final_top5
from engine.final_reporter_v4 import render_final_report_v4


def _row(symbol, final_rank_score):
    return {
        "symbol": symbol,
        "final_rank_score": final_rank_score,
    }


def test_final_top5_requires_minimum_final_rank_score():
    controlled = [
        _row("AAAUSDT", 95.0),
        _row("BBBUSDT", 80.0),
        _row("CCCUSDT", 79.99),
    ]

    final_top5 = build_final_top5(controlled)

    assert [
        row["symbol"]
        for row in final_top5
    ] == [
        "AAAUSDT",
        "BBBUSDT",
    ]


def test_final_top5_is_limited_to_five():
    controlled = [
        _row(f"COIN{i}USDT", 100.0 - i)
        for i in range(7)
    ]

    final_top5 = build_final_top5(controlled)

    assert len(final_top5) == 5
    assert final_top5 == controlled[:5]


def test_empty_final_top5_renders_quality_message():
    out = {
        "controlled_top10": [],
        "final_top5": [],
        "usage": {},
    }

    report = render_final_report_v4(out)

    assert (
        "Tidak ditemukan setup berkualitas hari ini."
        in report
    )
