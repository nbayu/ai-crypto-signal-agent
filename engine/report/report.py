def generate_report(results):
    lines = []

    lines.append("=" * 50)
    lines.append("TOP MARKET SETUP")
    lines.append("=" * 50)

    for i, item in enumerate(results, start=1):
        lines.append(f"{i}. {item['symbol']}")
        lines.append(f"Score      : {item['score']}")
        lines.append(f"Trend      : {item['trend']}")
        lines.append(f"BOS        : {item['bos']}")
        lines.append(f"CHOCH      : {item['choch']}")
        lines.append(f"FVG        : {item['fvg']}")
        lines.append(f"OrderBlock : {item['order_blocks']}")
        lines.append(f"Liquidity  : {item['liquidity']}")
        lines.append("-" * 50)

    return "\n".join(lines)
