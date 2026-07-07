import requests


OI_URL = (
    "https://fapi.binance.com/futures/data/openInterestHist"
)


def open_interest_metrics_v2(symbol):
    """
    Measure real OI percentage change over approximately 1 hour.

    13 points at 5m provide 12 intervals = ~60 minutes.

    Returns:
        oi_change_pct : real percentage change
        oi_score      : granular 0-100 support score
        data_status   : OK / API_ERROR / INVALID_RESPONSE / INVALID_BASE
    """

    clean_symbol = (
        symbol
        .replace("/", "")
        .replace(":USDT", "")
    )

    try:
        response = requests.get(
            OI_URL,
            params={
                "symbol": clean_symbol,
                "period": "5m",
                "limit": 13,
            },
            timeout=5,
        )

        response.raise_for_status()
        data = response.json()

    except Exception as e:
        return {
            "oi_change_pct": None,
            "oi_score": None,
            "data_status": "API_ERROR",
            "error": str(e)[:120],
        }

    if not isinstance(data, list) or len(data) < 13:
        return {
            "oi_change_pct": None,
            "oi_score": None,
            "data_status": "INVALID_RESPONSE",
        }

    try:
        start_oi = float(data[0]["sumOpenInterest"])
        end_oi = float(data[-1]["sumOpenInterest"])
    except (KeyError, TypeError, ValueError):
        return {
            "oi_change_pct": None,
            "oi_score": None,
            "data_status": "INVALID_RESPONSE",
        }

    if start_oi <= 0:
        return {
            "oi_change_pct": None,
            "oi_score": None,
            "data_status": "INVALID_BASE",
        }

    change_pct = ((end_oi - start_oi) / start_oi) * 100.0

    # Continuous support score centered at 50:
    # -2.0% or lower -> 0
    # -1.0%          -> 25
    #  0.0%          -> 50
    # +1.0%          -> 75
    # +2.0% or higher-> 100
    score = 50.0 + (change_pct * 25.0)
    score = min(100.0, max(0.0, score))

    return {
        "oi_change_pct": round(change_pct, 4),
        "oi_score": round(score, 2),
        "data_status": "OK",
    }
