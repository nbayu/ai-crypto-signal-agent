import pandas as pd


def swing_high(df, left=3, right=3):
    highs = []

    for i in range(left, len(df) - right):
        current = df["high"].iloc[i]

        if current == max(df["high"].iloc[i-left:i+right+1]):
            highs.append(i)

    return highs


def swing_low(df, left=3, right=3):
    lows = []

    for i in range(left, len(df) - right):
        current = df["low"].iloc[i]

        if current == min(df["low"].iloc[i-left:i+right+1]):
            lows.append(i)

    return lows


def detect_trend(df):
    highs = swing_high(df)
    lows = swing_low(df)

    if len(highs) < 2 or len(lows) < 2:
        return "UNKNOWN"

    last_high = df["high"].iloc[highs[-1]]
    prev_high = df["high"].iloc[highs[-2]]

    last_low = df["low"].iloc[lows[-1]]
    prev_low = df["low"].iloc[lows[-2]]

    if last_high > prev_high and last_low > prev_low:
        return "UPTREND"

    if last_high < prev_high and last_low < prev_low:
        return "DOWNTREND"

    return "SIDEWAYS"


def detect_bos(df):
    highs = swing_high(df)

    if len(highs) < 2:
        return False

    previous_high = df["high"].iloc[highs[-2]]
    current_close = df["close"].iloc[-1]

    return current_close > previous_high


def detect_choch(df):
    lows = swing_low(df)

    if len(lows) < 2:
        return False

    previous_low = df["low"].iloc[lows[-2]]
    current_close = df["close"].iloc[-1]

    return current_close < previous_low


def analyze_market_structure(df):
    return {
        "trend": detect_trend(df),
        "bos": detect_bos(df),
        "choch": detect_choch(df),
    }
