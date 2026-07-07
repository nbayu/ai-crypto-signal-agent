import requests

def get_open_interest(symbol):
    try:
        symbol = symbol.replace("/", "").replace(":USDT", "")

        url = (
            "https://fapi.binance.com/futures/data/openInterestHist"
            f"?symbol={symbol}"
            "&period=5m"
            "&limit=1"
        )

        data = requests.get(url, timeout=5).json()

        if isinstance(data, list) and data:
            return float(data[0]["sumOpenInterest"])

    except:
        pass

    return 0

def open_interest_growth(symbol):
    try:
        symbol = symbol.replace("/", "").replace(":USDT", "")

        url = (
            "https://fapi.binance.com/futures/data/openInterestHist"
            f"?symbol={symbol}"
            "&period=5m"
            "&limit=2"
        )

        data = requests.get(url, timeout=5).json()

        if isinstance(data, list) and len(data) >= 2:
            prev_oi = float(data[0]["sumOpenInterest"])
            curr_oi = float(data[1]["sumOpenInterest"])

            if curr_oi > prev_oi:
                return 100
            elif curr_oi < prev_oi:
                return 0
            else:
                return 50

    except:
        pass

    return 50
