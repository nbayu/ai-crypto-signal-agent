import pandas as pd

import engine.pre_delivery_market_data_v4 as market_data_module
from engine.pre_delivery_market_data_v4 import (
    get_closed_ohlcv_for_pre_delivery,
)


def make_ohlcv():
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2026-07-01T08:00:00",
            "2026-07-01T12:00:00",
            "2026-07-01T16:00:00",
        ]),
        "open": [100.0, 101.0, 102.0],
        "high": [101.0, 102.0, 103.0],
        "low": [99.0, 100.0, 101.0],
        "close": [100.5, 101.5, 102.5],
        "volume": [10.0, 11.0, 12.0],
    })


def test_provider_returns_only_closed_4h_candles(monkeypatch):
    monkeypatch.setattr(
        market_data_module,
        "get_ohlcv",
        lambda symbol: make_ohlcv(),
    )

    result = get_closed_ohlcv_for_pre_delivery(
        "TEST/USDT:USDT",
        now="2026-07-01T18:00:00",
    )

    assert list(result["timestamp"]) == list(
        pd.to_datetime([
            "2026-07-01T08:00:00",
            "2026-07-01T12:00:00",
        ])
    )


def test_candle_becomes_eligible_exactly_at_close_boundary(
    monkeypatch,
):
    monkeypatch.setattr(
        market_data_module,
        "get_ohlcv",
        lambda symbol: make_ohlcv(),
    )

    result = get_closed_ohlcv_for_pre_delivery(
        "TEST/USDT:USDT",
        now="2026-07-01T20:00:00",
    )

    assert list(result["timestamp"]) == list(
        pd.to_datetime([
            "2026-07-01T08:00:00",
            "2026-07-01T12:00:00",
            "2026-07-01T16:00:00",
        ])
    )


def test_provider_does_not_mutate_raw_ohlcv(monkeypatch):
    raw = make_ohlcv()
    original = raw.copy(deep=True)

    monkeypatch.setattr(
        market_data_module,
        "get_ohlcv",
        lambda symbol: raw,
    )

    get_closed_ohlcv_for_pre_delivery(
        "TEST/USDT:USDT",
        now="2026-07-01T18:00:00",
    )

    pd.testing.assert_frame_equal(
        raw,
        original,
    )
