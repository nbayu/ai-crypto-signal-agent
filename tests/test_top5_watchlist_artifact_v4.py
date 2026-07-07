import json

import engine.top5_watchlist_artifact_v4 as artifact_module
from engine.top5_watchlist_artifact_v4 import (
    build_top5_watchlist_artifact,
    save_top5_watchlist_artifact,
)


def _make_row(symbol, final_rank_score):
    golden_zone = {
        "direction": "BULLISH",
        "swing_low_index": 10,
        "swing_high_index": 20,
        "swing_low": 90.0,
        "swing_high": 110.0,
        "levels": {
            "-0.27": 115.4,
            "0.0": 110.0,
            "0.5": 100.0,
            "0.618": 97.64,
            "0.786": 94.28,
            "1.0": 90.0,
        },
        "entry_zone": {
            "level_from": 0.618,
            "level_to": 0.786,
            "price_low": 94.28,
            "price_high": 97.64,
        },
        "take_profit": {
            "level": -0.27,
            "price": 115.4,
        },
        "stop_loss": {
            "level": 1.0,
            "price": 90.0,
        },
    }

    return {
        "symbol": symbol,
        "final_rank_score": final_rank_score,
        "reference_price": 100.0,
        "reference_candle_at": "2026-07-07T08:00:00",
        "golden_zone": golden_zone,
    }


def test_build_preserves_final_top5_order_and_golden_zone():
    final_top5 = [
        _make_row("AAAUSDT", 95.0),
        _make_row("BBBUSDT", 90.0),
    ]

    artifact = build_top5_watchlist_artifact(final_top5)

    assert artifact["setup_count"] == 2
    assert artifact["setups"][0]["rank"] == 1
    assert artifact["setups"][0]["symbol"] == "AAAUSDT"
    assert artifact["setups"][1]["rank"] == 2
    assert artifact["setups"][1]["symbol"] == "BBBUSDT"

    assert (
        artifact["setups"][0]["golden_zone"]
        is final_top5[0]["golden_zone"]
    )


def test_save_writes_latest_json(tmp_path, monkeypatch):
    monkeypatch.setattr(
        artifact_module,
        "WATCHLIST_DIRECTORY",
        tmp_path,
    )

    final_top5 = [
        _make_row("TESTUSDT", 91.5),
    ]

    path = save_top5_watchlist_artifact(final_top5)

    assert path == tmp_path / "latest.json"
    assert path.exists()

    saved = json.loads(path.read_text())

    assert saved["setup_count"] == 1
    assert saved["setups"][0]["rank"] == 1
    assert saved["setups"][0]["symbol"] == "TESTUSDT"
    assert saved["setups"][0]["golden_zone"] == (
        final_top5[0]["golden_zone"]
    )


def test_save_serializes_swing_timestamps_as_iso_strings(
    tmp_path,
    monkeypatch,
):
    import pandas as pd

    monkeypatch.setattr(
        artifact_module,
        "WATCHLIST_DIRECTORY",
        tmp_path,
    )

    final_top5 = [
        _make_row("TESTUSDT", 91.5),
    ]
    golden_zone = final_top5[0]["golden_zone"]

    golden_zone["swing_low_at"] = pd.Timestamp(
        "2026-07-01T08:00:00"
    )
    golden_zone["swing_high_at"] = pd.Timestamp(
        "2026-07-01T16:00:00"
    )

    path = save_top5_watchlist_artifact(final_top5)

    saved = json.loads(path.read_text())
    saved_zone = saved["setups"][0]["golden_zone"]

    assert saved_zone["swing_low_at"] == (
        "2026-07-01T08:00:00"
    )
    assert saved_zone["swing_high_at"] == (
        "2026-07-01T16:00:00"
    )
