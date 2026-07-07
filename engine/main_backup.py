from engine.ai_formatter import format_watchlist
from engine.scanner import scan_market

print("=" * 60)
print("                 AI MARKET SCANNER")
print("=" * 60)

results = scan_market()

if len(results) == 0:
    print("Tidak ada market yang lolos filter.")

else:

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    for i, r in enumerate(results[:20], start=1):

        print("-" * 60)

        print(f"{i}. {r['symbol']}")
        print(f"Score      : {r['score']}")
        print(f"Quality    : {r['quality']}")
        print(f"Trend      : {r['trend']}")
        print(f"BOS        : {r['bos']}")
        print(f"CHOCH      : {r['choch']}")
        print(f"FVG        : {r['fvg']}")
        print(f"OrderBlock : {r['order_blocks']}")
        print(f"Liquidity  : {r['liquidity']}")

    print()
    print("=" * 60)
    print("AI SUMMARY")
    print("=" * 60)

    try:
        summary = format_watchlist(results)
        print(summary)

    except Exception as e:
        print("AI Error :", e)
