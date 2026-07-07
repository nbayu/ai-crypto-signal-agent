from engine.validation_semantic_guard_v4 import (
    SemanticValidationError,
    validate_semantic_consistency,
)


print("=" * 110)
print("SEMANTIC GUARD V4 — FULL 24-CASE REGRESSION")
print("=" * 110)


def candidate(
    symbol,
    *,
    bos=True,
    choch=False,
    participation="STRONG",
):
    return {
        "symbol": symbol,
        "python_score": 90.0,
        "trend": "UPTREND",
        "bos": bos,
        "choch": choch,
        "volume_class": "STRONG",
        "oi_class": "STRONG",
        "participation": participation,
    }


def validation(
    symbol,
    *,
    status="CLEAR",
    risk="LOW",
    confluence="STRONG",
    reason="ALIGNED",
):
    return {
        "symbol": symbol,
        "status": status,
        "false_breakout_risk": risk,
        "confluence": confluence,
        "reason_code": reason,
    }


cases = [
    # --------------------------------------------------
    # 1–2: VALID ALIGNED
    # --------------------------------------------------
    (
        "01_VALID_STRONG_ALIGNED",
        candidate(
            "T01/USDT",
            participation="STRONG",
        ),
        validation(
            "T01/USDT",
        ),
        False,
    ),
    (
        "02_VALID_SUPPORTIVE_ALIGNED",
        candidate(
            "T02/USDT",
            participation="SUPPORTIVE",
        ),
        validation(
            "T02/USDT",
            confluence="MODERATE",
        ),
        False,
    ),

    # --------------------------------------------------
    # 3–4: BOS GUARDS
    # --------------------------------------------------
    (
        "03_BOS_TRUE_BREAKOUT_UNCONFIRMED",
        candidate(
            "T03/USDT",
            bos=True,
        ),
        validation(
            "T03/USDT",
            status="CONFLICT",
            risk="MEDIUM",
            confluence="MODERATE",
            reason="BREAKOUT_UNCONFIRMED",
        ),
        True,
    ),
    (
        "04_BOS_FALSE_LOW_RISK",
        candidate(
            "T04/USDT",
            bos=False,
        ),
        validation(
            "T04/USDT",
            status="CLEAR",
            risk="LOW",
            confluence="MODERATE",
            reason="ALIGNED",
        ),
        True,
    ),

    # --------------------------------------------------
    # 5–6: CHOCH FORWARD GUARDS
    # --------------------------------------------------
    (
        "05_CHOCH_TRUE_CLEAR",
        candidate(
            "T05/USDT",
            choch=True,
        ),
        validation(
            "T05/USDT",
            status="CLEAR",
            risk="HIGH",
            confluence="WEAK",
            reason="STRUCTURE_REVERSAL_CONFLICT",
        ),
        True,
    ),
    (
        "06_CHOCH_TRUE_ALIGNED",
        candidate(
            "T06/USDT",
            choch=True,
        ),
        validation(
            "T06/USDT",
            status="CONFLICT",
            risk="HIGH",
            confluence="WEAK",
            reason="ALIGNED",
        ),
        True,
    ),

    # --------------------------------------------------
    # 7–10: MIXED FORWARD + REVERSE
    # --------------------------------------------------
    (
        "07_VALID_MIXED",
        candidate(
            "T07/USDT",
            participation="MIXED",
        ),
        validation(
            "T07/USDT",
            status="CONFLICT",
            risk="MEDIUM",
            confluence="MODERATE",
            reason="MIXED_PARTICIPATION",
        ),
        False,
    ),
    (
        "08_MIXED_AS_CLEAR",
        candidate(
            "T08/USDT",
            participation="MIXED",
        ),
        validation(
            "T08/USDT",
            status="CLEAR",
            risk="MEDIUM",
            confluence="MODERATE",
            reason="MIXED_PARTICIPATION",
        ),
        True,
    ),
    (
        "09_MIXED_AS_LOW_RISK",
        candidate(
            "T09/USDT",
            participation="MIXED",
        ),
        validation(
            "T09/USDT",
            status="CONFLICT",
            risk="LOW",
            confluence="MODERATE",
            reason="MIXED_PARTICIPATION",
        ),
        True,
    ),
    (
        "10_NEUTRAL_WITH_MIXED_REASON",
        candidate(
            "T10/USDT",
            participation="NEUTRAL",
        ),
        validation(
            "T10/USDT",
            status="CONFLICT",
            risk="MEDIUM",
            confluence="MODERATE",
            reason="MIXED_PARTICIPATION",
        ),
        True,
    ),

    # --------------------------------------------------
    # 11–12: UNKNOWN WEAK-EVIDENCE GUARDS
    # --------------------------------------------------
    (
        "11_UNKNOWN_AS_WEAK_VOLUME",
        candidate(
            "T11/USDT",
            participation="UNKNOWN",
        ),
        validation(
            "T11/USDT",
            status="CONFLICT",
            risk="MEDIUM",
            confluence="WEAK",
            reason="WEAK_VOLUME",
        ),
        True,
    ),
    (
        "12_UNKNOWN_AS_WEAK_OI",
        candidate(
            "T12/USDT",
            participation="UNKNOWN",
        ),
        validation(
            "T12/USDT",
            status="CONFLICT",
            risk="MEDIUM",
            confluence="WEAK",
            reason="WEAK_OI",
        ),
        True,
    ),

    # --------------------------------------------------
    # 13–17: EXACT WEAK CONTRACT
    # --------------------------------------------------
    (
        "13_VALID_WEAK",
        candidate(
            "T13/USDT",
            participation="WEAK",
        ),
        validation(
            "T13/USDT",
            status="HIGH_RISK",
            risk="HIGH",
            confluence="WEAK",
            reason="WEAK_PARTICIPATION",
        ),
        False,
    ),
    (
        "14_WEAK_WRONG_STATUS",
        candidate(
            "T14/USDT",
            participation="WEAK",
        ),
        validation(
            "T14/USDT",
            status="CONFLICT",
            risk="HIGH",
            confluence="WEAK",
            reason="WEAK_PARTICIPATION",
        ),
        True,
    ),
    (
        "15_WEAK_WRONG_RISK",
        candidate(
            "T15/USDT",
            participation="WEAK",
        ),
        validation(
            "T15/USDT",
            status="HIGH_RISK",
            risk="MEDIUM",
            confluence="WEAK",
            reason="WEAK_PARTICIPATION",
        ),
        True,
    ),
    (
        "16_WEAK_WRONG_CONFLUENCE",
        candidate(
            "T16/USDT",
            participation="WEAK",
        ),
        validation(
            "T16/USDT",
            status="HIGH_RISK",
            risk="HIGH",
            confluence="MODERATE",
            reason="WEAK_PARTICIPATION",
        ),
        True,
    ),
    (
        "17_WEAK_WRONG_REASON",
        candidate(
            "T17/USDT",
            participation="WEAK",
        ),
        validation(
            "T17/USDT",
            status="HIGH_RISK",
            risk="HIGH",
            confluence="WEAK",
            reason="ALIGNED",
        ),
        True,
    ),

    # --------------------------------------------------
    # 18–19: STRUCTURE REVERSAL BIDIRECTIONAL
    # --------------------------------------------------
    (
        "18_VALID_STRUCTURE_REVERSAL",
        candidate(
            "T18/USDT",
            choch=True,
            participation="STRONG",
        ),
        validation(
            "T18/USDT",
            status="CONFLICT",
            risk="HIGH",
            confluence="WEAK",
            reason="STRUCTURE_REVERSAL_CONFLICT",
        ),
        False,
    ),
    (
        "19_FALSE_STRUCTURE_REVERSAL",
        candidate(
            "T19/USDT",
            choch=False,
            participation="STRONG",
        ),
        validation(
            "T19/USDT",
            status="CONFLICT",
            risk="HIGH",
            confluence="WEAK",
            reason="STRUCTURE_REVERSAL_CONFLICT",
        ),
        True,
    ),

    # --------------------------------------------------
    # 20: MIXED MUST NEVER BE ALIGNED
    # --------------------------------------------------
    (
        "20_MIXED_AS_ALIGNED",
        candidate(
            "T20/USDT",
            participation="MIXED",
        ),
        validation(
            "T20/USDT",
            status="CONFLICT",
            risk="MEDIUM",
            confluence="MODERATE",
            reason="ALIGNED",
        ),
        True,
    ),

    # --------------------------------------------------
    # 21–22: WEAK REASON REVERSE INVARIANT
    # --------------------------------------------------
    (
        "21_NEUTRAL_WITH_WEAK_REASON",
        candidate(
            "T21/USDT",
            participation="NEUTRAL",
        ),
        validation(
            "T21/USDT",
            status="HIGH_RISK",
            risk="HIGH",
            confluence="WEAK",
            reason="WEAK_PARTICIPATION",
        ),
        True,
    ),
    (
        "22_STRONG_WITH_WEAK_REASON",
        candidate(
            "T22/USDT",
            participation="STRONG",
        ),
        validation(
            "T22/USDT",
            status="HIGH_RISK",
            risk="HIGH",
            confluence="WEAK",
            reason="WEAK_PARTICIPATION",
        ),
        True,
    ),

    # --------------------------------------------------
    # 23–24: NEW UNKNOWN ↔ ALIGNED CONTRACT
    # --------------------------------------------------
    (
        "23_VALID_UNKNOWN_NON_ALIGNED",
        candidate(
            "T23/USDT",
            bos=False,
            participation="UNKNOWN",
        ),
        validation(
            "T23/USDT",
            status="CONFLICT",
            risk="MEDIUM",
            confluence="MODERATE",
            reason="BREAKOUT_UNCONFIRMED",
        ),
        False,
    ),
    (
        "24_UNKNOWN_AS_ALIGNED",
        candidate(
            "T24/USDT",
            participation="UNKNOWN",
        ),
        validation(
            "T24/USDT",
            status="CLEAR",
            risk="LOW",
            confluence="STRONG",
            reason="ALIGNED",
        ),
        True,
    ),
]


results = []


for name, cand, val, should_reject in cases:
    rejected = False
    message = None

    try:
        validate_semantic_consistency(
            cand,
            val,
        )

    except SemanticValidationError as e:
        rejected = True
        message = str(e)

    matched = (
        should_reject
        == rejected
    )

    results.append({
        "name": name,
        "should_reject": should_reject,
        "rejected": rejected,
        "matched": matched,
        "message": message,
    })

    print()
    print("CASE     :", name)
    print(
        "EXPECTED :",
        "REJECT" if should_reject else "PASS",
    )
    print(
        "ACTUAL   :",
        "REJECT" if rejected else "PASS",
    )
    print(
        "RESULT   :",
        "MATCH ✅" if matched else "FAILED ❌",
    )

    if message:
        print("MESSAGE  :", message)


total = len(results)
matched_count = sum(
    result["matched"]
    for result in results
)
failed = [
    result
    for result in results
    if not result["matched"]
]


print()
print("=" * 110)
print("REGRESSION RESULT")
print("=" * 110)

print("TOTAL CASES :", total)
print("MATCHED     :", matched_count)
print("FAILED      :", len(failed))


if failed:
    print()
    print("FAILED CASES")
    print("-" * 110)

    for result in failed:
        print(result["name"])
        print(
            "EXPECTED :",
            "REJECT"
            if result["should_reject"]
            else "PASS",
        )
        print(
            "ACTUAL   :",
            "REJECT"
            if result["rejected"]
            else "PASS",
        )
        print(
            "MESSAGE  :",
            result["message"],
        )


assert total == 24
assert matched_count == 24
assert len(failed) == 0


print()
print("VALID ALIGNED PRESERVED ✅")
print("BOS GUARDS PRESERVED ✅")
print("CHOCH GUARDS PRESERVED ✅")
print("MIXED FORWARD GUARDS PRESERVED ✅")
print("MIXED REVERSE INVARIANT PRESERVED ✅")
print("UNKNOWN WEAK-EVIDENCE GUARDS PRESERVED ✅")
print("WEAK CONTRACT PRESERVED ✅")
print("STRUCTURE REVERSAL VALID PATH PRESERVED ✅")
print("STRUCTURE REVERSAL REVERSE INVARIANT PRESERVED ✅")
print("MIXED AS ALIGNED GUARD PRESERVED ✅")
print("WEAK REASON REVERSE INVARIANT PRESERVED ✅")
print("VALID UNKNOWN NON-ALIGNED PATH PRESERVED ✅")
print("UNKNOWN AS ALIGNED GUARD PRESERVED ✅")
print("NO BINANCE CALL ✅")
print("NO DEEPSEEK CALL ✅")
print()
print("SEMANTIC GUARD V4 FULL 24-CASE REGRESSION PASS ✅")
