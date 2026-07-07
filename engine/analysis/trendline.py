import numpy as np

def trendline_support(df, lows):
    if len(lows) < 2:
        return None

    x = np.array(lows)
    y = df["low"].iloc[lows].values

    slope, intercept = np.polyfit(x, y, 1)

    return {
        "slope": float(slope),
        "intercept": float(intercept)
    }


def trendline_resistance(df, highs):
    if len(highs) < 2:
        return None

    x = np.array(highs)
    y = df["high"].iloc[highs].values

    slope, intercept = np.polyfit(x, y, 1)

    return {
        "slope": float(slope),
        "intercept": float(intercept)
    }
