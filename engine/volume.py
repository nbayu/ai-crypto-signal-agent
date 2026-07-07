import ccxt

exchange = ccxt.binance()

def get_volume(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return float(ticker.get("quoteVolume", 0))
    except:
        return 0

def volume_spike(df):
    """
    Hitung score Volume Spike (0-100)
    """

    if len(df) < 21:
        return 0

    current_volume = float(df["volume"].iloc[-1])
    average_volume = df["volume"].iloc[-21:-1].mean()

    if average_volume == 0:
        return 0

    ratio = current_volume / average_volume

    if ratio >= 3:
        return 100
    elif ratio >= 2:
        return 80
    elif ratio >= 1.5:
        return 60
    elif ratio >= 1.2:
        return 40
    else:
        return 0
