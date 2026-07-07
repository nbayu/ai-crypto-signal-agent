import requests
import ccxt

exchange = ccxt.binance()

def get_market_volume(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker.get("quoteVolume", 0)
    except:
        return 0

def get_open_interest(symbol):
    try:
        futures_symbol = symbol.replace("/", "").replace(":USDT", "")

        url = (
            "https://fapi.binance.com/fapi/v1/openInterest"
            f"?symbol={futures_symbol}"
        )

        data = requests.get(url, timeout=5).json()

        return float(data["openInterest"])

    except Exception:
        return 0
