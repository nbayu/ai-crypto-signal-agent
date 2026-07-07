def detect_fvg(df):
    fvg = []

    for i in range(2, len(df)):
        prev_high = df["high"].iloc[i - 2]
        prev_low = df["low"].iloc[i - 2]

        current_high = df["high"].iloc[i]
        current_low = df["low"].iloc[i]

        if current_low > prev_high:
            fvg.append({
                "type": "bullish",
                "index": i,
                "top": float(current_low),
                "bottom": float(prev_high)
            })

        elif current_high < prev_low:
            fvg.append({
                "type": "bearish",
                "index": i,
                "top": float(prev_low),
                "bottom": float(current_high)
            })

    return fvg


def detect_order_blocks(df):
    obs = []

    for i in range(1, len(df) - 1):

        if (
            df["close"].iloc[i] < df["open"].iloc[i]
            and df["close"].iloc[i + 1] > df["high"].iloc[i]
        ):

            obs.append({
                "type": "bullish",
                "index": i,
                "high": float(df["high"].iloc[i]),
                "low": float(df["low"].iloc[i])
            })

        elif (
            df["close"].iloc[i] > df["open"].iloc[i]
            and df["close"].iloc[i + 1] < df["low"].iloc[i]
        ):

            obs.append({
                "type": "bearish",
                "index": i,
                "high": float(df["high"].iloc[i]),
                "low": float(df["low"].iloc[i])
            })

    return obs


def detect_liquidity_sweep(df):
    sweeps = []

    for i in range(2, len(df)):

        prev_high = df["high"].iloc[i - 1]
        prev_low = df["low"].iloc[i - 1]

        high = df["high"].iloc[i]
        low = df["low"].iloc[i]
        close = df["close"].iloc[i]

        # Buy-side liquidity sweep
        if high > prev_high and close < prev_high:
            sweeps.append({
                "type": "buy_side",
                "index": i,
                "level": float(prev_high)
            })

        # Sell-side liquidity sweep
        elif low < prev_low and close > prev_low:
            sweeps.append({
                "type": "sell_side",
                "index": i,
                "level": float(prev_low)
            })

    return sweeps
