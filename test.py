from engine.binance_client import get_ohlcv
from engine.quality_filter import quality_filter

df = get_ohlcv("BTC/USDT:USDT")

print(quality_filter(df))
