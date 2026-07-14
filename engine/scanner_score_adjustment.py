def apply_scanner_score_adjustment(score, distance_ob, atr):
    if distance_ob > atr * 2:
        score -= 8
    elif distance_ob > atr:
        score -= 4

    return max(0, score)
