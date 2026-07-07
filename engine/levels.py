import json
from engine.binance_client import get_ohlcv, exchange
from engine.market_structure import swing_high, swing_low

symbols = ["TRX/USDT:USDT", "MEGA/USDT:USDT", "HMSTR/USDT:USDT", "VANRY/USDT:USDT", "JST/USDT:USDT"]

out = {}
for s in symbols:
    df = get_ohlcv(s)
    last_price = float(df["close"].iloc[-1])

    highs = swing_high(df)
    lows = swing_low(df)

    recent_res = float(df["high"].tail(30).max())
    major_res = float(df["high"].tail(100).max())
    recent_sup = float(df["low"].tail(30).min())
    major_sup = float(df["low"].tail(100).min())

    ticker = exchange.fetch_ticker(s)
    change24h = ticker.get("percentage")

    out[s] = {
        "last_price": last_price,
        "change24h_pct": change24h,
        "recent_resistance": recent_res,
        "major_resistance": major_res,
        "recent_support": recent_sup,
        "major_support": major_sup,
    }

print(json.dumps(out, indent=2))
