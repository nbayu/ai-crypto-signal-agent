def classify_volume_ratio(volume_ratio, data_status="OK"):
    """
    Classify raw closed-candle volume ratio.

    Thresholds calibrated from Data Quality V2 sample:
    WEAK        : < 0.80x
    NORMAL      : 0.80x to < 1.20x
    SUPPORTIVE  : 1.20x to < 1.50x
    STRONG      : >= 1.50x
    """

    if data_status != "OK" or volume_ratio is None:
        return "UNKNOWN"

    if volume_ratio < 0.80:
        return "WEAK"
    elif volume_ratio < 1.20:
        return "NORMAL"
    elif volume_ratio < 1.50:
        return "SUPPORTIVE"
    else:
        return "STRONG"


def classify_oi_change(oi_change_pct, data_status="OK"):
    """
    Classify raw 1-hour open-interest change.

    Thresholds calibrated from Data Quality V2 sample:
    WEAK        : <= -0.30%
    SOFT        : > -0.30% to < 0.00%
    SUPPORTIVE  : 0.00% to < +0.30%
    STRONG      : >= +0.30%
    """

    if data_status != "OK" or oi_change_pct is None:
        return "UNKNOWN"

    if oi_change_pct <= -0.30:
        return "WEAK"
    elif oi_change_pct < 0.00:
        return "SOFT"
    elif oi_change_pct < 0.30:
        return "SUPPORTIVE"
    else:
        return "STRONG"


def classify_participation(
    volume_ratio,
    volume_status,
    oi_change_pct,
    oi_status,
):
    """
    Deterministic participation evidence.

    Python owns threshold interpretation.
    AI receives both raw evidence and these classifications.
    """

    volume_class = classify_volume_ratio(
        volume_ratio,
        volume_status,
    )

    oi_class = classify_oi_change(
        oi_change_pct,
        oi_status,
    )

    if "UNKNOWN" in (volume_class, oi_class):
        participation = "UNKNOWN"

    elif volume_class == "WEAK" and oi_class == "WEAK":
        participation = "WEAK"

    elif (
        volume_class == "STRONG"
        and oi_class in ("SUPPORTIVE", "STRONG")
    ):
        participation = "STRONG"

    elif (
        volume_class in ("SUPPORTIVE", "STRONG")
        and oi_class in ("SOFT", "SUPPORTIVE", "STRONG")
    ):
        participation = "SUPPORTIVE"

    elif (
        volume_class in ("NORMAL", "SUPPORTIVE", "STRONG")
        and oi_class == "WEAK"
    ):
        participation = "MIXED"

    else:
        participation = "NEUTRAL"

    return {
        "volume_class": volume_class,
        "oi_class": oi_class,
        "participation": participation,
    }
