import pandas as pd


def fibonacci_levels(df):
    high = df["high"].max()
    low = df["low"].min()

    diff = high - low

    return {
        "0.236": high - diff * 0.236,
        "0.382": high - diff * 0.382,
        "0.5": high - diff * 0.5,
        "0.618": high - diff * 0.618,
        "0.786": high - diff * 0.786,
    }


def premium_discount(df):
    high = df["high"].max()
    low = df["low"].min()

    midpoint = (high + low) / 2

    current = df["close"].iloc[-1]

    return {
        "premium": current > midpoint,
        "discount": current < midpoint,
        "mid": midpoint,
    }
