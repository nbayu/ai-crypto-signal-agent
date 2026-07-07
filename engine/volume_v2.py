def volume_metrics_v2(df):
    """
    Volume quality metrics using CLOSED 4H candles only.

    Returns:
        volume_ratio : closed candle volume / previous 20 closed candles average
        volume_score : granular 0-100 score
        data_status  : OK / INSUFFICIENT_DATA / INVALID_AVERAGE
    """

    if df is None or len(df) < 22:
        return {
            "volume_ratio": None,
            "volume_score": None,
            "data_status": "INSUFFICIENT_DATA",
        }

    closed_volume = float(df["volume"].iloc[-2])

    average_volume = float(
        df["volume"].iloc[-22:-2].mean()
    )

    if average_volume <= 0:
        return {
            "volume_ratio": None,
            "volume_score": None,
            "data_status": "INVALID_AVERAGE",
        }

    ratio = closed_volume / average_volume

    # Continuous score:
    # ratio 0.0x -> 0
    # ratio 1.0x -> 33.33
    # ratio 1.5x -> 50
    # ratio 2.0x -> 66.67
    # ratio 3.0x+ -> 100
    score = min(100.0, max(0.0, (ratio / 3.0) * 100.0))

    return {
        "volume_ratio": round(ratio, 4),
        "volume_score": round(score, 2),
        "data_status": "OK",
    }
