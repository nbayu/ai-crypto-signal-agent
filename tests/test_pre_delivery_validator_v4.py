import copy

import pandas as pd

import engine.pre_delivery_validator_v4 as validator_module
from engine.pre_delivery_validator_v4 import (
    build_pre_delivery_artifact,
)


def make_setup(rank, symbol):
    return {
        "rank": rank,
        "symbol": symbol,
        "final_rank_score": 90.0 - rank,
        "reference_price": 100.0,
        "reference_candle_at": "2026-07-01T08:00:00",
        "golden_zone": {
            "direction": "BULLISH",
            "swing_low_at": "2026-07-01T00:00:00",
            "swing_high_at": "2026-07-01T08:00:00",
            "entry_zone": {
                "price_low": 94.0,
                "price_high": 97.0,
            },
            "take_profit": {
                "price": 115.0,
            },
            "stop_loss": {
                "price": 90.0,
            },
        },
    }


def make_artifact():
    setups = [
        make_setup(1, "AAA/USDT:USDT"),
        make_setup(2, "BBB/USDT:USDT"),
        make_setup(3, "CCC/USDT:USDT"),
    ]

    return {
        "generated_at": "2026-07-01T12:00:00",
        "setup_count": len(setups),
        "setups": setups,
    }


def make_closed_candles():
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2026-07-01T20:00:00",
        ]),
        "open": [100.0],
        "high": [101.0],
        "low": [99.0],
        "close": [100.0],
    })


def test_build_filters_ineligible_setups_without_reranking(monkeypatch):
    artifact = make_artifact()

    lifecycle_by_symbol = {
        "AAA/USDT:USDT": {
            "state": "ENTRY_MISSED",
            "actionable": False,
        },
        "BBB/USDT:USDT": {
            "state": "ACTIVE",
            "actionable": True,
        },
        "CCC/USDT:USDT": {
            "state": "WAITING_ENTRY",
            "actionable": True,
        },
    }

    supersession_by_symbol = {
        "AAA/USDT:USDT": {
            "state": "CURRENT",
            "superseded": False,
        },
        "BBB/USDT:USDT": {
            "state": "CURRENT",
            "superseded": False,
        },
        "CCC/USDT:USDT": {
            "state": "SUPERSEDED",
            "superseded": True,
        },
    }

    monkeypatch.setattr(
        validator_module,
        "evaluate_setup_lifecycle",
        lambda setup, candles: lifecycle_by_symbol[
            setup["symbol"]
        ],
    )
    monkeypatch.setattr(
        validator_module,
        "evaluate_swing_supersession",
        lambda setup, candles, trend: supersession_by_symbol[
            setup["symbol"]
        ],
    )
    monkeypatch.setattr(
        validator_module,
        "detect_trend",
        lambda candles: "UPTREND",
    )

    result = build_pre_delivery_artifact(
        artifact,
        closed_candle_provider=lambda symbol: make_closed_candles(),
        validated_at="2026-07-02T00:00:00",
    )

    assert result["source_generated_at"] == artifact["generated_at"]
    assert result["validated_at"] == "2026-07-02T00:00:00"
    assert result["source_setup_count"] == 3
    assert result["eligible_setup_count"] == 1
    assert [
        setup["symbol"]
        for setup in result["setups"]
    ] == ["BBB/USDT:USDT"]
    assert result["setups"][0]["rank"] == 2


def test_build_preserves_eligible_setup_payload_without_mutation(
    monkeypatch,
):
    artifact = make_artifact()
    original = copy.deepcopy(artifact)

    monkeypatch.setattr(
        validator_module,
        "evaluate_setup_lifecycle",
        lambda setup, candles: {
            "state": "WAITING_ENTRY",
            "actionable": True,
        },
    )
    monkeypatch.setattr(
        validator_module,
        "evaluate_swing_supersession",
        lambda setup, candles, trend: {
            "state": "CURRENT",
            "superseded": False,
        },
    )
    monkeypatch.setattr(
        validator_module,
        "detect_trend",
        lambda candles: "UPTREND",
    )

    result = build_pre_delivery_artifact(
        artifact,
        closed_candle_provider=lambda symbol: make_closed_candles(),
        validated_at="2026-07-02T00:00:00",
    )

    assert result["setups"] == original["setups"]
    assert artifact == original


def test_build_records_all_evaluations_and_rejection_reasons(
    monkeypatch,
):
    artifact = make_artifact()

    lifecycle_by_symbol = {
        "AAA/USDT:USDT": {
            "state": "TP_HIT",
            "actionable": False,
        },
        "BBB/USDT:USDT": {
            "state": "ACTIVE",
            "actionable": True,
        },
        "CCC/USDT:USDT": {
            "state": "SL_HIT",
            "actionable": False,
        },
    }

    supersession_by_symbol = {
        "AAA/USDT:USDT": {
            "state": "CURRENT",
            "superseded": False,
        },
        "BBB/USDT:USDT": {
            "state": "CURRENT",
            "superseded": False,
        },
        "CCC/USDT:USDT": {
            "state": "SUPERSEDED",
            "superseded": True,
        },
    }

    monkeypatch.setattr(
        validator_module,
        "evaluate_setup_lifecycle",
        lambda setup, candles: lifecycle_by_symbol[
            setup["symbol"]
        ],
    )
    monkeypatch.setattr(
        validator_module,
        "evaluate_swing_supersession",
        lambda setup, candles, trend: supersession_by_symbol[
            setup["symbol"]
        ],
    )
    monkeypatch.setattr(
        validator_module,
        "detect_trend",
        lambda candles: "UPTREND",
    )

    result = build_pre_delivery_artifact(
        artifact,
        closed_candle_provider=lambda symbol: make_closed_candles(),
        validated_at="2026-07-02T00:00:00",
    )

    assert len(result["evaluations"]) == 3

    assert result["evaluations"][0]["delivery_eligible"] is False
    assert result["evaluations"][0]["rejection_reasons"] == [
        "TP_HIT",
    ]

    assert result["evaluations"][1]["delivery_eligible"] is True
    assert result["evaluations"][1]["rejection_reasons"] == []

    assert result["evaluations"][2]["delivery_eligible"] is False
    assert result["evaluations"][2]["rejection_reasons"] == [
        "SL_HIT",
        "SUPERSEDED",
    ]


def test_no_replacement_and_older_pair_remain_eligible(
    monkeypatch,
):
    artifact = make_artifact()
    artifact["setups"] = artifact["setups"][:2]
    artifact["setup_count"] = 2

    supersession_states = iter([
        {
            "state": "NO_REPLACEMENT",
            "superseded": False,
        },
        {
            "state": "OLDER_PAIR",
            "superseded": False,
        },
    ])

    monkeypatch.setattr(
        validator_module,
        "evaluate_setup_lifecycle",
        lambda setup, candles: {
            "state": "WAITING_ENTRY",
            "actionable": True,
        },
    )
    monkeypatch.setattr(
        validator_module,
        "evaluate_swing_supersession",
        lambda setup, candles, trend: next(
            supersession_states
        ),
    )
    monkeypatch.setattr(
        validator_module,
        "detect_trend",
        lambda candles: "UPTREND",
    )

    result = build_pre_delivery_artifact(
        artifact,
        closed_candle_provider=lambda symbol: make_closed_candles(),
        validated_at="2026-07-02T00:00:00",
    )

    assert result["eligible_setup_count"] == 2


def test_setup_count_mismatch_is_rejected():
    artifact = make_artifact()
    artifact["setup_count"] = 99

    try:
        build_pre_delivery_artifact(
            artifact,
            closed_candle_provider=lambda symbol: make_closed_candles(),
            validated_at="2026-07-02T00:00:00",
        )
    except ValueError as exc:
        assert str(exc) == (
            "setup_count does not match setups length"
        )
    else:
        raise AssertionError(
            "Expected malformed source artifact to be rejected"
        )


def test_closed_candle_provider_is_called_once_per_symbol(
    monkeypatch,
):
    artifact = make_artifact()
    calls = []

    def provider(symbol):
        calls.append(symbol)
        return make_closed_candles()

    monkeypatch.setattr(
        validator_module,
        "evaluate_setup_lifecycle",
        lambda setup, candles: {
            "state": "WAITING_ENTRY",
            "actionable": True,
        },
    )
    monkeypatch.setattr(
        validator_module,
        "evaluate_swing_supersession",
        lambda setup, candles, trend: {
            "state": "CURRENT",
            "superseded": False,
        },
    )
    monkeypatch.setattr(
        validator_module,
        "detect_trend",
        lambda candles: "UPTREND",
    )

    build_pre_delivery_artifact(
        artifact,
        closed_candle_provider=provider,
        validated_at="2026-07-02T00:00:00",
    )

    assert calls == [
        "AAA/USDT:USDT",
        "BBB/USDT:USDT",
        "CCC/USDT:USDT",
    ]


def test_duplicate_source_symbols_are_rejected():
    artifact = make_artifact()
    artifact["setups"][1]["symbol"] = (
        artifact["setups"][0]["symbol"]
    )

    try:
        build_pre_delivery_artifact(
            artifact,
            closed_candle_provider=lambda symbol: (
                make_closed_candles()
            ),
            validated_at="2026-07-02T00:00:00",
        )
    except ValueError as exc:
        assert str(exc) == (
            "Duplicate source setup symbols found"
        )
    else:
        raise AssertionError(
            "Expected duplicate symbols to be rejected"
        )


def test_delivery_setup_count_matches_eligible_setups(
    monkeypatch,
):
    artifact = make_artifact()

    lifecycle_states = iter([
        {
            "state": "TP_HIT",
            "actionable": False,
        },
        {
            "state": "ACTIVE",
            "actionable": True,
        },
        {
            "state": "WAITING_ENTRY",
            "actionable": True,
        },
    ])

    monkeypatch.setattr(
        validator_module,
        "evaluate_setup_lifecycle",
        lambda setup, candles: next(
            lifecycle_states
        ),
    )
    monkeypatch.setattr(
        validator_module,
        "evaluate_swing_supersession",
        lambda setup, candles, trend: {
            "state": "CURRENT",
            "superseded": False,
        },
    )
    monkeypatch.setattr(
        validator_module,
        "detect_trend",
        lambda candles: "UPTREND",
    )

    result = build_pre_delivery_artifact(
        artifact,
        closed_candle_provider=lambda symbol: (
            make_closed_candles()
        ),
        validated_at="2026-07-02T00:00:00",
    )

    assert result["source_setup_count"] == 3
    assert result["eligible_setup_count"] == 2
    assert result["setup_count"] == 2
    assert result["setup_count"] == len(
        result["setups"]
    )
