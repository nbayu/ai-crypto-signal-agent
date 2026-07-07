import requests

_cache = {
    "volume": {},
    "open_interest": {},
}


def refresh_cache():
    # 24H Volume
    data = requests.get(
        "https://fapi.binance.com/fapi/v1/ticker/24hr",
        timeout=10,
    ).json()

    _cache["volume"] = {
        item["symbol"]: float(item["quoteVolume"])
        for item in data
    }

    # Open Interest
    oi = requests.get(
        "https://fapi.binance.com/futures/data/openInterestHist?period=5m&limit=1",
        timeout=10,
    ).json()

    if isinstance(oi, list):
        for item in oi:
            if "symbol" in item:
                _cache["open_interest"][item["symbol"]] = float(
                    item["sumOpenInterest"]
                )


def normalize(symbol):
    return (
        symbol.replace("/", "")
        .replace(":USDT", "")
    )


def get_volume(symbol):
    return _cache["volume"].get(normalize(symbol), 0)


def get_open_interest(symbol):
    return _cache["open_interest"].get(normalize(symbol), 0)
