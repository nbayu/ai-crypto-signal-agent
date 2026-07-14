from concurrent.futures import ThreadPoolExecutor, as_completed

from engine.binance_client import get_symbols, get_ohlcv
from engine.market_structure import analyze_market_structure
from engine.binance_cache import (
    refresh_cache,
    get_volume,
    get_open_interest,
)
from engine.volume import volume_spike
from engine.volume_v2 import volume_metrics_v2
from engine.open_interest import open_interest_growth
from engine.atr import calculate_atr
from engine.entry_score import calculate_entry_score
from engine.order_block import distance_to_order_block
from engine.smc import (
    detect_fvg,
    detect_order_blocks,
    detect_liquidity_sweep,
    distance_to_fvg,
)
from engine.scoring import calculate_score
from engine.quality_filter import check_quality
from engine.mtf import mtf_confirm
from engine.golden_zone_skill import build_golden_zone_skill
from engine.scanner_score_adjustment import apply_scanner_score_adjustment
from engine.scanner_result_builder import build_scanner_result


def scan_symbol(symbol):
    try:
        df = get_ohlcv(symbol)

        quality = check_quality(df)
        if not quality["qualified"]:
            return None, "QUALITY"

        closed_df = df.iloc[:-1]

        structure = analyze_market_structure(closed_df)

        golden_zone = build_golden_zone_skill(
            closed_df,
            structure["trend"],
        )

        volume_v2 = volume_metrics_v2(df)

        obs = detect_order_blocks(df)
        active_obs = [ob for ob in obs if not ob["mitigated"]]

        mtf = mtf_confirm(symbol)
        if not mtf["confirmed"]:
            return None, "MTF"

        result = build_scanner_result(
            symbol=symbol,
            reference_price=float(df["close"].iloc[-2]),
            reference_candle_at=df["timestamp"].iloc[-2].isoformat(),
            trend=structure["trend"],
            mtf=mtf,
            mtf_score=mtf["score"],
            bos=structure["bos"],
            choch=structure["choch"],
            golden_zone=golden_zone,
            quality=quality["score"],
            fvg=len(detect_fvg(df)),
            order_blocks=len(active_obs),
            liquidity=len(detect_liquidity_sweep(df)),
            atr=calculate_atr(df),
            distance_ob=distance_to_order_block(df),
            distance_fvg=distance_to_fvg(df),
            volume=get_volume(symbol),
            volume_spike=volume_spike(df),
            volume_ratio=volume_v2["volume_ratio"],
            volume_v2_score=volume_v2["volume_score"],
            volume_v2_status=volume_v2["data_status"],
            open_interest=get_open_interest(symbol),
            oi_growth=open_interest_growth(symbol),
        )

        result["score"] = calculate_score(result)
        result["score"] = apply_scanner_score_adjustment(
            result["score"],
            result["distance_ob"],
            result["atr"],
        )

        result["entry_score"] = calculate_entry_score(result)

        return result, None

    except Exception as e:
        print(symbol, e)
        return None, "ERROR"


def scan_market():
    symbols = get_symbols()
    refresh_cache()

    results = []

    total_scanned = 0
    total_rejected = 0

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(scan_symbol, symbol): symbol
            for symbol in symbols
        }

        for future in as_completed(futures):
            result, reason = future.result()

            total_scanned += 1

            if result:
                results.append(result)
            else:
                total_rejected += 1

    results.sort(key=lambda x: x["score"], reverse=True)

    print()
    print("========== MARKET SUMMARY ==========")
    print("Scanned  :", total_scanned)
    print("Rejected :", total_rejected)
    print("Qualified:", len(results))
    print("===================================")
    print()

    return results
