import pandas as pd


def quality_filter(df):
    """
    Mengembalikan:
    {
        qualified: bool,
        score: int,
        reasons: list
    }
    """

    reasons = []
    score = 100

    # =========================
    # Data cukup?
    # =========================
    if len(df) < 100:
        reasons.append("Not Enough Candles")
        score -= 30

    # =========================
    # Volume
    # =========================
    volume = float(df["volume"].tail(20).mean())

    if volume < 1000:
        reasons.append("Low Volume")
        score -= 25

    # =========================
    # ATR sederhana
    # =========================
    atr = float((df["high"] - df["low"]).tail(14).mean())

    if atr <= 0:
        reasons.append("Low Volatility")
        score -= 20

    # =========================
    # Candle body
    # =========================
    body = abs(df["close"] - df["open"]).tail(20).mean()

    if body <= 0:
        reasons.append("Flat Market")
        score -= 20

    qualified = score >= 70

    return {
        "qualified": qualified,
        "score": score,
        "reasons": reasons
    }

check_quality = quality_filter
