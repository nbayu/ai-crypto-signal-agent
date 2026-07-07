import ccxt
import pandas as pd
from engine.config import TIMEFRAME, LOOKBACK

exchange = ccxt.binance({
    "options": {
        "defaultType": "future"
    },
    "enableRateLimit": True
})


def get_symbols():
    markets = exchange.load_markets()

    symbols = []

    for symbol in markets:
        market = markets[symbol]

        if (
            market["quote"] == "USDT"
            and market["active"]
            and market["swap"]
        ):
            symbols.append(symbol)

    return sorted(symbols)


def get_ohlcv(symbol):

    ohlcv = exchange.fetch_ohlcv(
        symbol,
        timeframe=TIMEFRAME,
        limit=LOOKBACK
    )

    df = pd.DataFrame(
        ohlcv,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    return df
