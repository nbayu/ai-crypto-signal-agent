import json

import pytest

from engine.tradingview_watchlist_export_v4 import (
    build_tradingview_symbol,
    build_tradingview_watchlist,
    export_tradingview_watchlist,
)


def _artifact(symbols):
    return {
        "generated_at": "2026-07-07T08:10:00",
        "setup_count": len(symbols),
        "setups": [
            {
                "rank": rank,
                "symbol": symbol,
            }
            for rank, symbol in enumerate(symbols, 1)
        ],
    }


def test_build_tradingview_symbol_normalizes_binance_perpetual():
    assert (
        build_tradingview_symbol("BTC/USDT:USDT")
        == "BINANCE:BTCUSDT.P"
    )


def test_build_watchlist_preserves_top5_order():
    artifact = _artifact([
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
        "SOL/USDT:USDT",
    ])

    watchlist = build_tradingview_watchlist(artifact)

    assert watchlist == [
        "BINANCE:BTCUSDT.P",
        "BINANCE:ETHUSDT.P",
        "BINANCE:SOLUSDT.P",
    ]


def test_build_watchlist_rejects_setup_count_mismatch():
    artifact = _artifact([
        "BTC/USDT:USDT",
    ])
    artifact["setup_count"] = 2

    with pytest.raises(ValueError):
        build_tradingview_watchlist(artifact)


def test_export_writes_comma_separated_symbols(tmp_path):
    source_path = tmp_path / "latest.json"
    output_path = tmp_path / "tradingview_watchlist.txt"

    source_path.write_text(
        json.dumps(
            _artifact([
                "BTC/USDT:USDT",
                "ETH/USDT:USDT",
            ])
        )
    )

    path = export_tradingview_watchlist(
        source_path,
        output_path,
    )

    assert path == output_path
    assert output_path.read_text() == (
        "BINANCE:BTCUSDT.P,"
        "BINANCE:ETHUSDT.P"
    )


@pytest.mark.parametrize(
    "symbol",
    [
        "BTCUSDT",
        "BTC/USDT",
        "BTC/USD:BTC",
        "",
    ],
)
def test_build_tradingview_symbol_rejects_unsupported_symbol(symbol):
    with pytest.raises(ValueError):
        build_tradingview_symbol(symbol)
