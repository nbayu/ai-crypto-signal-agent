def calculate_entry_score(result):
    score = 100

    # Dekat dengan Order Block lebih baik
    if result["distance_ob"] > result["atr"]:
        score -= 20
    elif result["distance_ob"] > result["atr"] * 0.5:
        score -= 10

    # Dekat dengan FVG lebih baik
    if result["distance_fvg"] > result["atr"]:
        score -= 15
    elif result["distance_fvg"] > result["atr"] * 0.5:
        score -= 8

    # Likuiditas
    if result["liquidity"] < 100:
        score -= 10

    # Market Structure
    if not result["bos"]:
        score -= 10

    if result["choch"]:
        score -= 5

    # Jumlah Order Block
    if result["order_blocks"] < 30:
        score -= 10
    elif result["order_blocks"] < 50:
        score -= 5

    # Jumlah FVG
    if result["fvg"] < 20:
        score -= 8
    elif result["fvg"] < 40:
        score -= 4

    # Volume
    volume = result.get("volume", 0)

    if volume < 10_000_000:
        score -= 8
    elif volume < 50_000_000:
        score -= 4


    # Open Interest
    oi = result.get("open_interest", 0)

    if oi < 10_000_000:
        score -= 8
    elif oi < 50_000_000:
        score -= 4

    return max(0, min(score, 100))
