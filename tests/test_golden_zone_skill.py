import pandas as pd

import engine.golden_zone_skill as skill_module
from engine.golden_zone_skill import (
    build_golden_zone_skill,
)


def test_skill_preserves_scanner_swing_timestamps(monkeypatch):
    swing_low_at = pd.Timestamp("2026-07-01T08:00:00")
    swing_high_at = pd.Timestamp("2026-07-01T16:00:00")

    monkeypatch.setattr(
        skill_module,
        "resolve_golden_zone_swing_pair",
        lambda closed_df, trend: {
            "direction": "BULLISH",
            "swing_low_index": 2,
            "swing_high_index": 4,
            "swing_low_at": swing_low_at,
            "swing_high_at": swing_high_at,
            "swing_low": 10.0,
            "swing_high": 20.0,
        },
    )

    result = build_golden_zone_skill(
        closed_df=pd.DataFrame(),
        trend="UPTREND",
    )

    assert result["swing_low_at"] == swing_low_at
    assert result["swing_high_at"] == swing_high_at
