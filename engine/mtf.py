import ccxt

exchange = ccxt.binance()

def get_trend(symbol, timeframe):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=50)

    closes = [x[4] for x in ohlcv]

    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes) / len(closes)

    return "UPTREND" if sma20 > sma50 else "DOWNTREND"


def mtf_confirm(symbol):
    trend15 = get_trend(symbol, "15m")
    trend1h = get_trend(symbol, "1h")
    trend4h = get_trend(symbol, "4h")

    score = 0

    if trend4h == trend1h:
        score += 80

    if trend15 == trend1h:
        score += 20

    return {
        "15m": trend15,
        "1h": trend1h,
        "4h": trend4h,
        "score": score,
        "confirmed": score >= 80
    }
