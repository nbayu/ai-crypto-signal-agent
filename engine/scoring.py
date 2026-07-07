def calculate_score(result):
    score = 0.0

    # Trend
    if result["trend"] == "UPTREND":
        score += 25
    elif result["trend"] == "DOWNTREND":
        score += 20

    # Structure
    if result["bos"]:
        score += 20

    if result["choch"]:
        score += 10

    # SMC Features (gunakan nilai asli, bukan pembulatan)
    score += min(result["fvg"] / 10, 10)
    score += min(result["order_blocks"] / 10, 10)
    score += min(result["liquidity"] / 15, 10)

    # Quality
    score += result.get("quality", 0) / 10

    # Volume
    volume = result.get("volume", 0)

    if volume > 100_000_000:
        score += 3
    elif volume > 50_000_000:
        score += 2
    elif volume > 10_000_000:
        score += 1

    # Open Interest
    oi = result.get("oi", result.get("open_interest", 0))

    if oi > 100_000_000:
        score += 2
    elif oi > 20_000_000:
        score += 1

    # Distance Order Block
    distance_ob = result.get("distance_ob", 999999)

    if distance_ob < 0.001:
        score += 8
    elif distance_ob < 0.005:
        score += 5
    elif distance_ob < 0.01:
        score += 2


    # Distance FVG
    distance_fvg = result.get("distance_fvg", 999999)

    if distance_fvg < 0.001:
        score += 7
    elif distance_fvg < 0.005:
        score += 4
    elif distance_fvg < 0.01:
        score += 2

    score = max(0, min(score, 100))
    return round(score, 2)
