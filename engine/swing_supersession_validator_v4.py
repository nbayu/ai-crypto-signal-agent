import pandas as pd

from engine.golden_zone_swing_resolver import (
    resolve_golden_zone_swing_pair,
)


def evaluate_swing_supersession(
    setup,
    closed_candles,
    current_trend,
):
    golden_zone = setup["golden_zone"]

    setup_direction = (
        golden_zone["direction"].upper()
    )
    setup_swing_low_at = pd.Timestamp(
        golden_zone["swing_low_at"]
    )
    setup_swing_high_at = pd.Timestamp(
        golden_zone["swing_high_at"]
    )

    latest_pair = resolve_golden_zone_swing_pair(
        closed_candles,
        current_trend,
    )

    if latest_pair is None:
        return {
            "symbol": setup["symbol"],
            "state": "NO_REPLACEMENT",
            "superseded": False,
        }

    latest_direction = (
        latest_pair["direction"].upper()
    )
    latest_swing_low_at = pd.Timestamp(
        latest_pair["swing_low_at"]
    )
    latest_swing_high_at = pd.Timestamp(
        latest_pair["swing_high_at"]
    )

    same_pair = (
        setup_direction == latest_direction
        and setup_swing_low_at == latest_swing_low_at
        and setup_swing_high_at == latest_swing_high_at
    )

    if same_pair:
        return {
            "symbol": setup["symbol"],
            "state": "CURRENT",
            "superseded": False,
        }

    setup_terminal_at = max(
        setup_swing_low_at,
        setup_swing_high_at,
    )
    latest_terminal_at = max(
        latest_swing_low_at,
        latest_swing_high_at,
    )

    if latest_terminal_at < setup_terminal_at:
        return {
            "symbol": setup["symbol"],
            "state": "OLDER_PAIR",
            "superseded": False,
        }

    return {
        "symbol": setup["symbol"],
        "state": "SUPERSEDED",
        "superseded": True,
    }
