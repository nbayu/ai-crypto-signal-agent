from engine.validation_control import (
    calculate_validation_adjustment,
)
from engine.validation_semantic_guard_v4 import (
    normalize_impossible_reason_code,
)


def _candidate(
    *,
    bos=True,
    choch=False,
    participation="NEUTRAL",
):
    return {
        "symbol": "TEST/USDT:USDT",
        "bos": bos,
        "choch": choch,
        "participation": participation,
    }


def _validation(reason):
    return {
        "symbol": "TEST/USDT:USDT",
        "status": "CONFLICT",
        "false_breakout_risk": "MEDIUM",
        "confluence": "MODERATE",
        "reason_code": reason,
    }


def test_normalizes_only_deterministically_impossible_reasons():
    cases = [
        (
            _candidate(bos=True),
            "BREAKOUT_UNCONFIRMED",
        ),
        (
            _candidate(choch=False),
            "STRUCTURE_REVERSAL_CONFLICT",
        ),
        (
            _candidate(participation="NEUTRAL"),
            "MIXED_PARTICIPATION",
        ),
        (
            _candidate(participation="STRONG"),
            "WEAK_PARTICIPATION",
        ),
    ]

    for candidate, reason in cases:
        original = _validation(reason)

        normalized = normalize_impossible_reason_code(
            candidate,
            original,
        )

        assert normalized["reason_code"] == (
            "MULTIPLE_CONFLICTS"
        )
        assert original["reason_code"] == reason


def test_preserves_valid_reason_codes():
    cases = [
        (
            _candidate(bos=False),
            "BREAKOUT_UNCONFIRMED",
        ),
        (
            _candidate(choch=True),
            "STRUCTURE_REVERSAL_CONFLICT",
        ),
        (
            _candidate(participation="MIXED"),
            "MIXED_PARTICIPATION",
        ),
        (
            _candidate(participation="WEAK"),
            "WEAK_PARTICIPATION",
        ),
    ]

    for candidate, reason in cases:
        normalized = normalize_impossible_reason_code(
            candidate,
            _validation(reason),
        )

        assert normalized["reason_code"] == reason


def test_does_not_normalize_aligned():
    normalized = normalize_impossible_reason_code(
        _candidate(participation="UNKNOWN"),
        _validation("ALIGNED"),
    )

    assert normalized["reason_code"] == "ALIGNED"


def test_normalization_does_not_change_penalty_fields():
    original = _validation(
        "BREAKOUT_UNCONFIRMED"
    )

    normalized = normalize_impossible_reason_code(
        _candidate(bos=True),
        original,
    )

    assert normalized["status"] == original["status"]
    assert (
        normalized["false_breakout_risk"]
        == original["false_breakout_risk"]
    )
    assert (
        normalized["confluence"]
        == original["confluence"]
    )
    assert (
        calculate_validation_adjustment(normalized)
        == calculate_validation_adjustment(original)
    )
