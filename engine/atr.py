import pandas as pd


def calculate_atr(df, period=14):
    """
    Menghitung ATR (Average True Range)
    """

    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    return float(atr.iloc[-1])
