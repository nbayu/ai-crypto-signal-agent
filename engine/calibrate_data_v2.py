import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from engine.binance_client import get_ohlcv
from engine.volume_v2 import volume_metrics_v2
from engine.open_interest_v2 import open_interest_metrics_v2


SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "BNB/USDT:USDT",
    "SOL/USDT:USDT",
    "XRP/USDT:USDT",
    "DOGE/USDT:USDT",
    "ADA/USDT:USDT",
    "TRX/USDT:USDT",
    "LINK/USDT:USDT",
    "AVAX/USDT:USDT",
    "SUI/USDT:USDT",
    "LTC/USDT:USDT",
    "BCH/USDT:USDT",
    "DOT/USDT:USDT",
    "NEAR/USDT:USDT",
    "APT/USDT:USDT",
    "ARB/USDT:USDT",
    "OP/USDT:USDT",
    "UNI/USDT:USDT",
    "AAVE/USDT:USDT",
    "ETC/USDT:USDT",
    "FIL/USDT:USDT",
    "ATOM/USDT:USDT",
    "INJ/USDT:USDT",
    "SEI/USDT:USDT",
    "PEPE/USDT:USDT",
    "WIF/USDT:USDT",
    "PUMP/USDT:USDT",
    "CAKE/USDT:USDT",
    "CELO/USDT:USDT",
]


rows = []

for i, symbol in enumerate(SYMBOLS, 1):
    print(f"[{i:02d}/{len(SYMBOLS)}] {symbol}")

    try:
        df = get_ohlcv(symbol)
        vol = volume_metrics_v2(df)
        oi = open_interest_metrics_v2(symbol)

        rows.append({
            "symbol": symbol,
            "volume_ratio": vol["volume_ratio"],
            "volume_score": vol["volume_score"],
            "volume_status": vol["data_status"],
            "oi_change_pct": oi["oi_change_pct"],
            "oi_score": oi["oi_score"],
            "oi_status": oi["data_status"],
        })

    except Exception as e:
        rows.append({
            "symbol": symbol,
            "volume_ratio": None,
            "volume_score": None,
            "volume_status": "ERROR",
            "oi_change_pct": None,
            "oi_score": None,
            "oi_status": "ERROR",
            "error": str(e)[:120],
        })


valid_vol = [
    r["volume_ratio"]
    for r in rows
    if r["volume_ratio"] is not None
]

valid_oi = [
    r["oi_change_pct"]
    for r in rows
    if r["oi_change_pct"] is not None
]


def summary(values):
    if not values:
        return None

    ordered = sorted(values)

    return {
        "count": len(ordered),
        "min": round(min(ordered), 4),
        "median": round(statistics.median(ordered), 4),
        "mean": round(statistics.mean(ordered), 4),
        "max": round(max(ordered), 4),
    }


report = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "sample_size": len(SYMBOLS),
    "volume_ratio_summary": summary(valid_vol),
    "oi_change_pct_summary": summary(valid_oi),
    "rows": rows,
}

out_dir = Path("data/calibration")
out_dir.mkdir(parents=True, exist_ok=True)

path = out_dir / (
    datetime.now(timezone.utc).strftime(
        "data_v2_calibration_%Y%m%d_%H%M%S.json"
    )
)

path.write_text(
    json.dumps(report, indent=2, default=str)
)

print()
print("=" * 70)
print("CALIBRATION SUMMARY")
print("=" * 70)
print("VOLUME:", report["volume_ratio_summary"])
print("OI    :", report["oi_change_pct_summary"])
print("FILE  :", path)
