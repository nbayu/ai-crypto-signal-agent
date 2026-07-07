import pandas as pd


def swing_high(df, left=2, right=2):
    highs = []

    for i in range(left, len(df) - right):
        if df["high"].iloc[i] == max(df["high"].iloc[i-left:i+right+1]):
            highs.append(i)

    return highs


def swing_low(df, left=2, right=2):
    lows = []

    for i in range(left, len(df) - right):
        if df["low"].iloc[i] == min(df["low"].iloc[i-left:i+right+1]):
            lows.append(i)

    return lows


def detect_bos(df):
    highs = swing_high(df)

    if len(highs) < 2:
        return False

    previous = df["high"].iloc[highs[-2]]

    return bool(df["close"].iloc[-1] > previous)


def detect_choch(df):
    lows = swing_low(df)

    if len(lows) < 2:
        return False

    previous = df["low"].iloc[lows[-2]]

    return bool(df["close"].iloc[-1] < previous)


def detect_trend(df):
    close = df["close"]

    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]

    if ema20 > ema50:
        return "UPTREND"

    elif ema20 < ema50:
        return "DOWNTREND"

    return "SIDEWAYS"


def analyze_market_structure(df):
    return {
        "trend": detect_trend(df),
        "bos": detect_bos(df),
        "choch": detect_choch(df)
    }
