from datetime import timedelta

import pandas as pd


TERMINAL_STATES = {
    "TP_HIT",
    "SL_HIT",
    "ENTRY_MISSED",
    "INVALIDATED_BEFORE_ENTRY",
    "AMBIGUOUS",
}


def evaluate_setup_lifecycle(
    setup,
    candles,
):
    golden_zone = setup["golden_zone"]
    direction = golden_zone["direction"].upper()

    if direction not in {
        "BULLISH",
        "BEARISH",
    }:
        raise ValueError(
            f"Unsupported setup direction: {direction}"
        )

    swing_low_at = pd.Timestamp(
        golden_zone["swing_low_at"]
    )
    swing_high_at = pd.Timestamp(
        golden_zone["swing_high_at"]
    )

    terminal_swing_at = max(
        swing_low_at,
        swing_high_at,
    )

    lifecycle_start_at = (
        terminal_swing_at
        + timedelta(hours=12)
    )

    entry_low = float(
        golden_zone["entry_zone"]["price_low"]
    )
    entry_high = float(
        golden_zone["entry_zone"]["price_high"]
    )
    tp_price = float(
        golden_zone["take_profit"]["price"]
    )
    sl_price = float(
        golden_zone["stop_loss"]["price"]
    )

    if entry_low > entry_high:
        raise ValueError(
            "Invalid entry zone"
        )

    if direction == "BULLISH":
        if not (
            sl_price < entry_low
            <= entry_high < tp_price
        ):
            raise ValueError(
                "Invalid bullish lifecycle levels"
            )
    else:
        if not (
            tp_price < entry_low
            <= entry_high < sl_price
        ):
            raise ValueError(
                "Invalid bearish lifecycle levels"
            )

    if int(candles["timestamp"].duplicated().sum()) != 0:
        raise ValueError(
            "Duplicate OHLCV timestamps found"
        )

    history = candles[
        candles["timestamp"] >= lifecycle_start_at
    ].copy()

    history = history.sort_values(
        "timestamp"
    )

    state = "WAITING_ENTRY"
    entry_touched_at = None
    resolved_at = None

    for _, candle in history.iterrows():
        timestamp = candle["timestamp"]

        entry_touched = (
            float(candle["high"]) >= entry_low
            and float(candle["low"]) <= entry_high
        )

        if direction == "BULLISH":
            tp_touched = (
                float(candle["high"]) >= tp_price
            )
            sl_touched = (
                float(candle["low"]) <= sl_price
            )
        else:
            tp_touched = (
                float(candle["low"]) <= tp_price
            )
            sl_touched = (
                float(candle["high"]) >= sl_price
            )

        if state == "WAITING_ENTRY":
            touched_count = sum([
                entry_touched,
                tp_touched,
                sl_touched,
            ])

            if entry_touched and touched_count > 1:
                state = "AMBIGUOUS"
                resolved_at = timestamp
                break

            if tp_touched:
                state = "ENTRY_MISSED"
                resolved_at = timestamp
                break

            if sl_touched:
                state = "INVALIDATED_BEFORE_ENTRY"
                resolved_at = timestamp
                break

            if entry_touched:
                state = "ACTIVE"
                entry_touched_at = timestamp

            continue

        if state == "ACTIVE":
            if tp_touched and sl_touched:
                state = "AMBIGUOUS"
                resolved_at = timestamp
                break

            if tp_touched:
                state = "TP_HIT"
                resolved_at = timestamp
                break

            if sl_touched:
                state = "SL_HIT"
                resolved_at = timestamp
                break

    result = {
        "symbol": setup["symbol"],
        "state": state,
        "actionable": state not in TERMINAL_STATES,
        "lifecycle_start_at": lifecycle_start_at.isoformat(),
        "entry_touched_at": (
            None
            if entry_touched_at is None
            else entry_touched_at.isoformat()
        ),
        "resolved_at": (
            None
            if resolved_at is None
            else resolved_at.isoformat()
        ),
    }

    return result
