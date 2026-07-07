import pandas as pd


def detect_fvg(df):
    fvg = []

    for i in range(2, len(df)):
        high1 = df["high"].iloc[i - 2]
        low1 = df["low"].iloc[i - 2]

        high3 = df["high"].iloc[i]
        low3 = df["low"].iloc[i]

        # Bullish FVG
        if low3 > high1:
            fvg.append({
                "type": "bullish",
                "index": i,
                "top": low3,
                "bottom": high1
            })

        # Bearish FVG
        elif high3 < low1:
            fvg.append({
                "type": "bearish",
                "index": i,
                "top": low1,
                "bottom": high3
            })

    return fvg


def detect_order_blocks(df):
    """
    Order Block sederhana:
    Bullish OB = candle bearish sebelum impuls bullish kuat.
    Bearish OB = candle bullish sebelum impuls bearish kuat.
    """

    obs = []

    body_multiplier = 1.5

    for i in range(2, len(df) - 1):
        prev_open = df["open"].iloc[i - 1]
        prev_close = df["close"].iloc[i - 1]

        curr_open = df["open"].iloc[i]
        curr_close = df["close"].iloc[i]

        prev_body = abs(prev_close - prev_open)
        curr_body = abs(curr_close - curr_open)

        # Bullish Order Block
        if (
            prev_close < prev_open
            and curr_close > curr_open
            and curr_body > prev_body * body_multiplier
        ):
            obs.append({
                "type": "bullish",
                "index": i,
                "high": float(df["high"].iloc[i - 1]),
                "low": float(df["low"].iloc[i - 1]),
                "mitigated": False,
            })

        # Bearish Order Block
        elif (
            prev_close > prev_open
            and curr_close < curr_open
            and curr_body > prev_body * body_multiplier
        ):
            obs.append({
                "type": "bearish",
                "index": i,
                "high": float(df["high"].iloc[i - 1]),
                "low": float(df["low"].iloc[i - 1]),
                "mitigated": False,
            })

    # Cek apakah Order Block sudah dimitigasi
    last_close = float(df["close"].iloc[-1])

    for ob in obs:
        if ob["type"] == "bullish":
            if last_close < ob["low"]:
                ob["mitigated"] = True
        else:
            if last_close > ob["high"]:
                ob["mitigated"] = True

    return obs


def detect_liquidity_sweep(df):
    sweeps = []

    for i in range(2, len(df)):
        current_high = df["high"].iloc[i]
        current_low = df["low"].iloc[i]

        previous_high = max(df["high"].iloc[max(0, i - 5):i])
        previous_low = min(df["low"].iloc[max(0, i - 5):i])

        if current_high > previous_high:
            sweeps.append({
                "type": "buy_side",
                "index": i
            })

        elif current_low < previous_low:
            sweeps.append({
                "type": "sell_side",
                "index": i
            })

    return sweeps


def distance_to_fvg(df):
    current_price = float(df["close"].iloc[-1])

    fvgs = detect_fvg(df)

    if not fvgs:
        return 999999.0

    nearest = min(
        fvgs,
        key=lambda fvg: min(
            abs(current_price - fvg["top"]),
            abs(current_price - fvg["bottom"])
        )
    )

    if current_price > nearest["top"]:
        return current_price - nearest["top"]
    elif current_price < nearest["bottom"]:
        return nearest["bottom"] - current_price
    else:
        return 0.0
