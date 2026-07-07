import pandas as pd

import engine.golden_zone_swing_resolver as resolver_module
from engine.golden_zone_swing_resolver import (
    resolve_golden_zone_swing_pair,
)


def build_df():
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-07-01T00:00:00",
                    "2026-07-01T04:00:00",
                    "2026-07-01T08:00:00",
                    "2026-07-01T12:00:00",
                    "2026-07-01T16:00:00",
                    "2026-07-01T20:00:00",
                ]
            ),
            "high": [10.0, 11.0, 12.0, 13.0, 15.0, 14.0],
            "low": [9.0, 8.0, 7.0, 9.0, 10.0, 11.0],
        }
    )


def test_bullish_pair_includes_swing_timestamps(monkeypatch):
    df = build_df()

    monkeypatch.setattr(
        resolver_module,
        "swing_high",
        lambda frame: [4],
    )
    monkeypatch.setattr(
        resolver_module,
        "swing_low",
        lambda frame: [2],
    )

    result = resolve_golden_zone_swing_pair(
        df,
        "UPTREND",
    )

    assert result["swing_low_index"] == 2
    assert result["swing_high_index"] == 4
    assert result["swing_low_at"] == df["timestamp"].iloc[2]
    assert result["swing_high_at"] == df["timestamp"].iloc[4]


def test_bearish_pair_includes_swing_timestamps(monkeypatch):
    df = build_df()

    monkeypatch.setattr(
        resolver_module,
        "swing_high",
        lambda frame: [1],
    )
    monkeypatch.setattr(
        resolver_module,
        "swing_low",
        lambda frame: [4],
    )

    result = resolve_golden_zone_swing_pair(
        df,
        "DOWNTREND",
    )

    assert result["swing_high_index"] == 1
    assert result["swing_low_index"] == 4
    assert result["swing_high_at"] == df["timestamp"].iloc[1]
    assert result["swing_low_at"] == df["timestamp"].iloc[4]
