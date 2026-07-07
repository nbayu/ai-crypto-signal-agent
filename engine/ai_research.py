def research_market(data):
    """
    Mengubah hasil scanner menjadi ringkasan riset market.
    Tidak menghasilkan sinyal BUY / SELL.
    """

    strengths = []
    risks = []

    trend = data.get("trend", "UNKNOWN")
    bos = data.get("bos", False)
    choch = data.get("choch", False)

    score = data.get("score", 0)
    entry_score = data.get("entry_score", 0)

    order_blocks = data.get("order_blocks", 0)
    fvg = data.get("fvg", 0)

    distance_ob = data.get("distance_ob", 999999)
    distance_fvg = data.get("distance_fvg", 999999)
    atr = data.get("atr", 0)

    volume_spike = data.get("volume_spike", 0)
    oi_growth = data.get("oi_growth", 50)

    # MARKET STRUCTURE
    if trend == "UPTREND":
        strengths.append("Strong bullish structure")
    elif trend == "DOWNTREND":
        strengths.append("Strong bearish structure")
    else:
        risks.append("Unclear market direction")

    if bos:
        strengths.append("Structure breakout confirmed")

    if choch:
        risks.append("Possible structure reversal")

    # SETUP QUALITY
    if score >= 80 and entry_score >= 80:
        strengths.append("High-quality setup")
    elif score >= 60 and entry_score >= 60:
        strengths.append("Good setup quality")
    else:
        risks.append("Setup quality is weak")

    # KEY ZONES
    near_ob = atr > 0 and order_blocks > 0 and distance_ob <= atr
    near_fvg = atr > 0 and fvg > 0 and distance_fvg <= atr

    if near_ob or near_fvg:
        strengths.append("Near key market zone")

    if atr > 0 and distance_ob > atr * 2 and distance_fvg > atr * 2:
        risks.append("Price far from key zones")

    # VOLUME
    if volume_spike >= 80:
        strengths.append("Strong volume confirmation")
    elif volume_spike < 60:
        risks.append("No volume confirmation")

    # OPEN INTEREST
    if oi_growth >= 80:
        strengths.append("Open interest expanding")
    elif oi_growth <= 20:
        risks.append("Open interest not supportive")

    # RESEARCH CONFIDENCE
    confidence = int((score + entry_score) / 2)

    if confidence >= 85 and not choch:
        research_status = "STRONG CANDIDATE"
    elif confidence >= 70:
        research_status = "WORTH REVIEWING"
    else:
        research_status = "LOW PRIORITY"

    return {
        "symbol": data.get("symbol"),
        "research_status": research_status,
        "confidence": confidence,
        "strengths": strengths[:3],
        "risks": risks[:2],
    }
