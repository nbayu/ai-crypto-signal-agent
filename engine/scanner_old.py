from engine.binance_client import get_symbols, get_ohlcv
from engine.market_structure import analyze_market_structure
from engine.smc import (
    detect_fvg,
    detect_order_blocks,
    detect_liquidity_sweep,
)
from engine.scoring import calculate_score
from engine.quality_filter import check_quality
from engine.mtf import mtf_confirm

def scan_market(limit=10):

    symbols = get_symbols()

    results = []

    total_scanned = 0
    total_rejected = 0

    for symbol in symbols[:limit]:

        try:

            df = get_ohlcv(symbol)

            total_scanned += 1

            quality = check_quality(df)

            if not quality["qualified"]:
                total_rejected += 1
                continue

            structure = analyze_market_structure(df)

            mtf = mtf_confirm(symbol)


        if not mtf["confirmed"]:
            total_rejected += 1
            print(symbol, "Rejected (MTF)")
            continue

         result = {
                "symbol": symbol,
                "trend": structure["trend"],
                "mtf": mtf,
                "bos": structure["bos"],
                "choch": structure["choch"],
                "quality": quality["score"],
                "fvg": len(detect_fvg(df)),
                "order_blocks": len(detect_order_blocks(df)),
                "liquidity": len(detect_liquidity_sweep(df)),
            }

            result["score"] = calculate_score(result)

            results.append(result)

            print(symbol, "OK")

        except Exception as e:
            print(symbol, e)

    results.sort(key=lambda x: x["score"], reverse=True)

    print()
    print("========== MARKET SUMMARY ==========")
    print("Scanned  :", total_scanned)
    print("Rejected :", total_rejected)
    print("Qualified:", len(results))
    print("===================================")
    print()

    return results
