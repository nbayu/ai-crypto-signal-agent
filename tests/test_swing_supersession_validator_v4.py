import pandas as pd

import engine.swing_supersession_validator_v4 as validator_module
from engine.swing_supersession_validator_v4 import (
    evaluate_swing_supersession,
)


def make_setup(
    *,
    direction="BULLISH",
    swing_low_at="2026-07-01T00:00:00",
    swing_high_at="2026-07-01T08:00:00",
):
    return {
        "symbol": "TEST/USDT:USDT",
        "golden_zone": {
            "direction": direction,
            "swing_low_at": swing_low_at,
            "swing_high_at": swing_high_at,
        },
    }


def make_candles():
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2026-07-01T00:00:00",
            "2026-07-01T04:00:00",
        ]),
        "high": [100.0, 101.0],
        "low": [90.0, 91.0],
    })


def test_identical_pair_is_current(monkeypatch):
    setup = make_setup()

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: {
            "direction": "BULLISH",
            "swing_low_at": pd.Timestamp("2026-07-01T00:00:00"),
            "swing_high_at": pd.Timestamp("2026-07-01T08:00:00"),
        },
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "UPTREND",
    )

    assert result["state"] == "CURRENT"
    assert result["superseded"] is False


def test_newer_bullish_pair_supersedes_old_setup(monkeypatch):
    setup = make_setup()

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: {
            "direction": "BULLISH",
            "swing_low_at": pd.Timestamp("2026-07-01T12:00:00"),
            "swing_high_at": pd.Timestamp("2026-07-01T20:00:00"),
        },
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "UPTREND",
    )

    assert result["state"] == "SUPERSEDED"
    assert result["superseded"] is True


def test_changed_prior_anchor_supersedes_pair(monkeypatch):
    setup = make_setup()

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: {
            "direction": "BULLISH",
            "swing_low_at": pd.Timestamp("2026-07-01T04:00:00"),
            "swing_high_at": pd.Timestamp("2026-07-01T08:00:00"),
        },
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "UPTREND",
    )

    assert result["state"] == "SUPERSEDED"


def test_direction_change_supersedes_old_setup(monkeypatch):
    setup = make_setup()

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: {
            "direction": "BEARISH",
            "swing_low_at": pd.Timestamp("2026-07-01T20:00:00"),
            "swing_high_at": pd.Timestamp("2026-07-01T12:00:00"),
        },
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "DOWNTREND",
    )

    assert result["state"] == "SUPERSEDED"
    assert result["superseded"] is True


def test_no_resolved_replacement_pair_is_not_superseded(monkeypatch):
    setup = make_setup()

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: None,
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "UPTREND",
    )

    assert result["state"] == "NO_REPLACEMENT"
    assert result["superseded"] is False


def test_timestamp_identity_ignores_index_fields(monkeypatch):
    setup = make_setup()

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: {
            "direction": "BULLISH",
            "swing_low_index": 99,
            "swing_high_index": 123,
            "swing_low_at": pd.Timestamp("2026-07-01T00:00:00"),
            "swing_high_at": pd.Timestamp("2026-07-01T08:00:00"),
        },
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "UPTREND",
    )

    assert result["state"] == "CURRENT"
    assert result["superseded"] is False


def test_older_pair_does_not_supersede_setup(monkeypatch):
    setup = make_setup()

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: {
            "direction": "BULLISH",
            "swing_low_at": pd.Timestamp("2026-06-30T12:00:00"),
            "swing_high_at": pd.Timestamp("2026-06-30T20:00:00"),
        },
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "UPTREND",
    )

    assert result["state"] == "OLDER_PAIR"
    assert result["superseded"] is False


def test_same_terminal_anchor_with_newer_prior_anchor_supersedes(monkeypatch):
    setup = make_setup(
        swing_low_at="2026-07-01T00:00:00",
        swing_high_at="2026-07-01T08:00:00",
    )

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: {
            "direction": "BULLISH",
            "swing_low_at": pd.Timestamp("2026-07-01T04:00:00"),
            "swing_high_at": pd.Timestamp("2026-07-01T08:00:00"),
        },
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "UPTREND",
    )

    assert result["state"] == "SUPERSEDED"
    assert result["superseded"] is True


def test_older_opposite_direction_pair_does_not_supersede(monkeypatch):
    setup = make_setup()

    monkeypatch.setattr(
        validator_module,
        "resolve_golden_zone_swing_pair",
        lambda df, trend: {
            "direction": "BEARISH",
            "swing_low_at": pd.Timestamp("2026-06-30T20:00:00"),
            "swing_high_at": pd.Timestamp("2026-06-30T12:00:00"),
        },
    )

    result = evaluate_swing_supersession(
        setup,
        make_candles(),
        "DOWNTREND",
    )

    assert result["state"] == "OLDER_PAIR"
    assert result["superseded"] is False
