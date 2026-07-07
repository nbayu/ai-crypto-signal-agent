import numpy as np


def calculate_trendlines(df):
    """
    Menghitung garis support dan resistance sederhana
    menggunakan regresi linear.
    """

    x = np.arange(len(df))

    support = np.polyfit(x, df["low"], 1)
    resistance = np.polyfit(x, df["high"], 1)

    return {
        "support": {
            "slope": float(support[0]),
            "intercept": float(support[1])
        },
        "resistance": {
            "slope": float(resistance[0]),
            "intercept": float(resistance[1])
        }
    }
