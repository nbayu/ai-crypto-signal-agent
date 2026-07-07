from engine.ai_research import research_market
from engine.ai_formatter import format_watchlist
from engine.scanner import scan_market
from engine.research_journal import create_research_call


print("=" * 60)
print("                 AI MARKET SCANNER")
print("=" * 60)

results = scan_market()

if len(results) == 0:
    print("Tidak ada market yang lolos filter.")

else:
    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    for i, r in enumerate(results[:5], start=1):
        research = research_market(r)

        journal_record = create_research_call(r, research)

        print("-" * 60)

        print(f"{i}. {r['symbol']}")
        print(f"Call ID         : {journal_record['call_id']}")
        print(f"Score           : {r['score']}")
        print(f"Entry Score     : {r['entry_score']}")
        print(f"Quality         : {r['quality']}")
        print(f"Trend           : {r['trend']}")
        print(f"BOS             : {r['bos']}")
        print(f"CHOCH           : {r['choch']}")
        print(f"FVG             : {r['fvg']}")
        print(f"OrderBlock      : {r['order_blocks']}")
        print(f"Liquidity       : {r['liquidity']}")
        print(f"ATR             : {r['atr']:.4f}")
        print(f"Distance OB     : {r['distance_ob']:.4f}")
        print(f"Distance FVG    : {r['distance_fvg']:.4f}")
        print(f"Volume          : {r['volume']:.2f}")
        print(f"Volume Spike    : {r['volume_spike']}")
        print(f"OpenInterest    : {r['open_interest']}")
        print(f"OI Growth       : {r['oi_growth']}")
        print(f"Research Status : {research['research_status']}")
        print(f"Confidence      : {research['confidence']}")
        print(f"Strengths       : {' | '.join(research['strengths'])}")
        print(f"Risks           : {' | '.join(research['risks'])}")

    print()
    print("=" * 60)
    print("AI SUMMARY")
    print("=" * 60)

    try:
        summary = format_watchlist(results)
        print(summary)

    except Exception as e:
        print("AI Error :", e)
