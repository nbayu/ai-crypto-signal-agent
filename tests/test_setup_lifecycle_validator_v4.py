import pandas as pd

from engine.setup_lifecycle_validator_v4 import (
    evaluate_setup_lifecycle,
)


def make_setup(
    *,
    direction="BULLISH",
    swing_low_at="2026-07-01T00:00:00",
    swing_high_at="2026-07-01T08:00:00",
    entry_low=94.0,
    entry_high=97.0,
    tp=115.0,
    sl=90.0,
):
    return {
        "symbol": "TEST/USDT:USDT",
        "golden_zone": {
            "direction": direction,
            "swing_low_at": swing_low_at,
            "swing_high_at": swing_high_at,
            "entry_zone": {
                "price_low": entry_low,
                "price_high": entry_high,
            },
            "take_profit": {
                "price": tp,
            },
            "stop_loss": {
                "price": sl,
            },
        },
    }


def make_candles(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        ],
    ).assign(
        timestamp=lambda df: pd.to_datetime(df["timestamp"])
    )


def test_waiting_entry_when_no_lifecycle_level_is_touched():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 105, 110, 100, 108),
        ("2026-07-02T00:00:00", 108, 112, 99, 105),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "WAITING_ENTRY"
    assert result["actionable"] is True


def test_entry_touch_activates_setup():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 105, 106, 95, 100),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "ACTIVE"
    assert result["actionable"] is True
    assert result["entry_touched_at"] == "2026-07-01T20:00:00"


def test_tp_after_entry_is_terminal():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 105, 106, 95, 100),
        ("2026-07-02T00:00:00", 100, 116, 99, 115),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "TP_HIT"
    assert result["actionable"] is False
    assert result["resolved_at"] == "2026-07-02T00:00:00"


def test_sl_after_entry_is_terminal():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 105, 106, 95, 100),
        ("2026-07-02T00:00:00", 100, 101, 89, 90),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "SL_HIT"
    assert result["actionable"] is False


def test_tp_before_entry_is_entry_missed():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 105, 116, 100, 115),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "ENTRY_MISSED"
    assert result["actionable"] is False


def test_sl_before_entry_invalidates_setup():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 92, 93, 89, 91),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "INVALIDATED_BEFORE_ENTRY"
    assert result["actionable"] is False


def test_entry_and_tp_same_candle_is_ambiguous():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 105, 116, 95, 110),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "AMBIGUOUS"
    assert result["actionable"] is False


def test_entry_and_sl_same_candle_is_ambiguous():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 100, 101, 89, 95),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "AMBIGUOUS"
    assert result["actionable"] is False


def test_tp_and_sl_same_candle_after_active_is_ambiguous():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 105, 106, 95, 100),
        ("2026-07-02T00:00:00", 100, 116, 89, 105),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "AMBIGUOUS"
    assert result["actionable"] is False


def test_candles_before_lifecycle_start_are_ignored():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T12:00:00", 105, 116, 89, 100),
        ("2026-07-01T16:00:00", 105, 116, 89, 100),
        ("2026-07-01T20:00:00", 105, 110, 100, 108),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["lifecycle_start_at"] == "2026-07-01T20:00:00"
    assert result["state"] == "WAITING_ENTRY"
    assert result["actionable"] is True


def test_bearish_setup_uses_symmetric_level_semantics():
    setup = make_setup(
        direction="BEARISH",
        swing_high_at="2026-07-01T00:00:00",
        swing_low_at="2026-07-01T08:00:00",
        entry_low=103.0,
        entry_high=106.0,
        tp=85.0,
        sl=110.0,
    )

    candles = make_candles([
        ("2026-07-01T20:00:00", 100, 105, 99, 104),
        ("2026-07-02T00:00:00", 104, 105, 84, 86),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "TP_HIT"
    assert result["actionable"] is False


def test_unordered_candles_are_evaluated_chronologically():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-02T00:00:00", 100, 116, 99, 115),
        ("2026-07-01T20:00:00", 105, 106, 95, 100),
    ])

    result = evaluate_setup_lifecycle(setup, candles)

    assert result["state"] == "TP_HIT"
    assert result["entry_touched_at"] == "2026-07-01T20:00:00"
    assert result["resolved_at"] == "2026-07-02T00:00:00"


def test_duplicate_candle_timestamps_are_rejected():
    setup = make_setup()

    candles = make_candles([
        ("2026-07-01T20:00:00", 105, 106, 95, 100),
        ("2026-07-01T20:00:00", 100, 116, 99, 115),
    ])

    try:
        evaluate_setup_lifecycle(setup, candles)
    except ValueError as exc:
        assert str(exc) == "Duplicate OHLCV timestamps found"
    else:
        raise AssertionError("Expected duplicate timestamps to be rejected")


def test_invalid_entry_zone_is_rejected():
    setup = make_setup(
        entry_low=98.0,
        entry_high=97.0,
    )

    candles = make_candles([])

    try:
        evaluate_setup_lifecycle(setup, candles)
    except ValueError as exc:
        assert str(exc) == "Invalid entry zone"
    else:
        raise AssertionError("Expected invalid entry zone to be rejected")


def test_invalid_bullish_level_order_is_rejected():
    setup = make_setup(
        entry_low=94.0,
        entry_high=97.0,
        tp=96.0,
        sl=90.0,
    )

    candles = make_candles([])

    try:
        evaluate_setup_lifecycle(setup, candles)
    except ValueError as exc:
        assert str(exc) == "Invalid bullish lifecycle levels"
    else:
        raise AssertionError("Expected invalid bullish levels to be rejected")


def test_invalid_bearish_level_order_is_rejected():
    setup = make_setup(
        direction="BEARISH",
        swing_high_at="2026-07-01T00:00:00",
        swing_low_at="2026-07-01T08:00:00",
        entry_low=103.0,
        entry_high=106.0,
        tp=105.0,
        sl=110.0,
    )

    candles = make_candles([])

    try:
        evaluate_setup_lifecycle(setup, candles)
    except ValueError as exc:
        assert str(exc) == "Invalid bearish lifecycle levels"
    else:
        raise AssertionError("Expected invalid bearish levels to be rejected")
