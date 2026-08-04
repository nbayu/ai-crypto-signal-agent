from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import inspect

import pytest

import engine.e6_production_market_acquisition_v1 as module
from engine.mode_router_v1 import build_mode_scan_request
from engine.mode_scan_execution_plan_v1 import build_mode_scan_execution_plan


OBSERVED = "2026-08-03T08:01:00Z"
SECONDS = {
    "1w": 604800,
    "1d": 86400,
    "4h": 14400,
    "1h": 3600,
    "15m": 900,
    "5m": 300,
    "3m": 180,
}


def _ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _aligned_open(observed: datetime, timeframe: str) -> datetime:
    seconds = SECONDS[timeframe]
    epoch = datetime(1970, 1, 5 if timeframe == "1w" else 1, tzinfo=timezone.utc)
    elapsed = int((observed - epoch).total_seconds())
    return epoch + timedelta(seconds=(elapsed // seconds) * seconds)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.mark_payload = {
            "markPrice": 100.1,
            "time": _ms(datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc)),
        }

    def load_markets(self):
        self.calls.append(("load_markets",))
        return {
            "ZED/USDT:USDT": {
                "id": "ZEDUSDT", "active": True, "quote": "USDT", "settle": "USDT",
                "type": "swap", "linear": True, "swap": True, "precision": {"price": 0.1},
            },
            "AAA/USDT:USDT": {
                "id": "AAAUSDT", "active": True, "quote": "USDT", "settle": "USDT",
                "type": "swap", "linear": True, "swap": True, "precision": {"price": 0.1},
            },
            "SPOT/USDT:USDT": {
                "id": "SPOTUSDT", "active": True, "quote": "USDT", "settle": "USDT",
                "type": "spot", "linear": True, "swap": False, "precision": {"price": 0.1},
            },
            "INACTIVE/USDT:USDT": {
                "id": "INACTIVEUSDT", "active": False, "quote": "USDT", "settle": "USDT",
                "type": "swap", "linear": True, "swap": True, "precision": {"price": 0.1},
            },
        }

    def fetch_tickers(self):
        self.calls.append(("fetch_tickers",))
        return {
            "ZED/USDT:USDT": {"quoteVolume": 20.0},
            "AAA/USDT:USDT": {"quoteVolume": 20.0},
            "SPOT/USDT:USDT": {"quoteVolume": 999.0},
            "INACTIVE/USDT:USDT": {"quoteVolume": 999.0},
        }

    def fetch_ohlcv(self, symbol, *, timeframe, limit):
        self.calls.append(("fetch_ohlcv", symbol, timeframe, limit))
        observed = datetime.strptime(OBSERVED, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        current = _aligned_open(observed, timeframe)
        start = current - timedelta(seconds=SECONDS[timeframe] * (limit - 1))
        return [
            [_ms(start + timedelta(seconds=SECONDS[timeframe] * index)), 100.0, 102.0, 99.0, 101.0, 2000.0]
            for index in range(limit)
        ]

    def fetch_open_interest_history(self, symbol, *, timeframe, limit, params):
        self.calls.append(("fetch_open_interest_history", symbol, timeframe, limit, params))
        return [
            {"timestamp": _ms(datetime(2026, 8, 3, 7, 55, tzinfo=timezone.utc)), "openInterestAmount": 1000.0},
            {"timestamp": _ms(datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc)), "openInterestAmount": 1010.0},
        ]

    def fetch_order_book(self, symbol, *, limit):
        self.calls.append(("fetch_order_book", symbol, limit))
        return {
            "timestamp": _ms(datetime(2026, 8, 3, 7, 59, 58, tzinfo=timezone.utc)),
            "bids": [[100.0, 2.0]],
            "asks": [[100.2, 2.0]],
        }

    def fetch_ticker(self, symbol):
        self.calls.append(("fetch_ticker", symbol))
        return {
            "timestamp": _ms(datetime(2026, 8, 3, 7, 59, 59, tzinfo=timezone.utc)),
            "last": 100.1,
        }

    def fapiPublicGetPremiumIndex(self, params):
        self.calls.append(("fapiPublicGetPremiumIndex", params))
        return self.mark_payload


def _port():
    client = FakeClient()
    port = module.build_e6_production_binance_public_market_port_v1(
        client_factory=lambda: client
    )
    return port, client


def _plan(port, mode="SCALP"):
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    request = build_mode_scan_request(mode=mode, due_window_id="e6dw1:" + "a" * 64)
    return snapshot, build_mode_scan_execution_plan(
        request=request,
        market_snapshot=snapshot.entries,
        include_optional_context=False,
    )


def test_import_is_passive_and_ccxt_is_only_lazily_imported() -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    assert "engine.binance_client" not in source
    assert "import ccxt" not in source
    assert "importlib.import_module(\"ccxt\")" in source
    assert not any(
        isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "attr", "") in {"binance", "binanceusdm"}
        for node in tree.body
    )


def test_client_is_lazy_and_discovery_calls_are_exactly_once() -> None:
    created = []
    client = FakeClient()
    port = module.E6ProductionBinancePublicMarketPortV1(
        client_factory=lambda: created.append(True) or client
    )
    assert created == [] and client.calls == []
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    assert created == [True]
    assert [call[0] for call in client.calls] == ["load_markets", "fetch_tickers"]
    assert snapshot.load_markets_count == snapshot.fetch_tickers_count == 1
    with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1):
        port.acquire_market_snapshot(observed_at=OBSERVED)


def test_active_linear_usdt_perpetual_filter_and_deterministic_order() -> None:
    port, _client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    assert [item.canonical_symbol for item in snapshot.entries] == [
        "AAA/USDT:USDT",
        "ZED/USDT:USDT",
    ]
    assert all(
        item.active and item.linear and item.perpetual
        and item.quote_asset == item.settle_asset == "USDT"
        and item.market_kind == "swap"
        for item in snapshot.entries
    )
    assert snapshot.tick_size_for("AAA/USDT:USDT") == "0.1"


@pytest.mark.parametrize("mode", ("SWING", "INTRADAY", "SCALP"))
def test_exact_mode_fetch_limits_and_closed_candle_conversion(mode: str) -> None:
    port, client = _port()
    _snapshot, plan = _plan(port, mode)
    symbol = plan.full_evaluation_symbols[0]
    for timeframe_plan in symbol.candle_fetches:
        candles = port.fetch_candles(timeframe_plan=timeframe_plan, observed_at=OBSERVED)
        assert len(candles) == timeframe_plan.raw_fetch_limit
        assert candles[-1].open_time <= OBSERVED < candles[-1].close_time
        assert candles[-2].close_time == candles[-1].open_time
    calls = [item for item in client.calls if item[0] == "fetch_ohlcv"]
    assert [(item[2], item[3]) for item in calls] == [
        (item.timeframe, item.raw_fetch_limit) for item in symbol.candle_fetches
    ]


def test_open_interest_is_one_pinned_nonpaginated_request() -> None:
    port, client = _port()
    _snapshot, plan = _plan(port)
    observations = port.fetch_open_interest(
        symbol_plan=plan.full_evaluation_symbols[0],
        observed_at=OBSERVED,
        period="5m",
    )
    assert len(observations) == 2
    call = next(item for item in client.calls if item[0] == "fetch_open_interest_history")
    assert call[2:] == ("5m", 2, {"paginate": False})
    assert observations[-1].open_interest == 1010.0


def test_executable_quote_binds_oldest_timestamp_and_three_single_calls() -> None:
    port, client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    quote = port.fetch_executable_quote(
        canonical_symbol=snapshot.entries[0].canonical_symbol,
        observed_at=OBSERVED,
    )
    assert quote.exchange_timestamp == "2026-08-03T07:59:58Z"
    assert (quote.best_bid, quote.best_ask, quote.last_price, quote.mark_price) == (
        100.0, 100.2, 100.1, 100.1
    )
    assert quote.order_book_call_count == quote.ticker_call_count == quote.mark_call_count == 1
    assert [item[0] for item in client.calls].count("fetch_order_book") == 1
    assert [item[0] for item in client.calls].count("fetch_ticker") == 1
    assert [item[0] for item in client.calls].count("fapiPublicGetPremiumIndex") == 1


def test_incomplete_or_future_quote_fails_with_exact_no_trade_reason() -> None:
    port, client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    client.mark_payload = {
        "markPrice": 100.1,
        "time": _ms(datetime(2026, 8, 3, 8, 2, tzinfo=timezone.utc)),
    }
    with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1) as raised:
        port.fetch_executable_quote(
            canonical_symbol=snapshot.entries[0].canonical_symbol,
            observed_at=OBSERVED,
        )
    assert raised.value.reason_code == "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE"


def test_source_has_zero_retry_private_or_order_authority() -> None:
    source = inspect.getsource(module).casefold()
    for prohibited in (
        "api_key", "secret", "password", "fetch_balance", "fetch_positions",
        "create_order", "cancel_order", "while true", "retry(",
    ):
        assert prohibited not in source


def test_parse_raw_decimal_number_accepted_cases() -> None:
    assert module._parse_raw_decimal_number(1) == 1.0
    assert module._parse_raw_decimal_number(1.5) == 1.5
    assert module._parse_raw_decimal_number("1.5") == 1.5
    assert module._parse_raw_decimal_number("-1.5", positive=False) == -1.5
    assert module._parse_raw_decimal_number("1.5e2") == 150.0
    assert module._parse_raw_decimal_number("63677.44", positive=True) == 63677.44


def test_parse_raw_decimal_number_rejected_cases() -> None:
    rejects = [
        True, False, None, "", " 1.5", "1.5 ", "1 5", "1,500.0",
        "1.5.5", "NaN", "Infinity", "-Infinity", "nan", "inf",
        [], {}, b"1.5",
    ]
    for invalid in rejects:
        with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1):
            module._parse_raw_decimal_number(invalid)

    # Reject zero/negative when positive is required
    with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1):
        module._parse_raw_decimal_number(0, positive=True)
    with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1):
        module._parse_raw_decimal_number(-1.5, positive=True)


def test_integration_string_mark_price_produces_valid_quote() -> None:
    # A. String markPrice
    port, client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    client.mark_payload = {"markPrice": "63677.44", "time": _ms(datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc))}
    quote = port.fetch_executable_quote(canonical_symbol=snapshot.entries[0].canonical_symbol, observed_at=OBSERVED)
    assert quote.mark_price == 63677.44

    # B. Numeric markPrice remains valid
    port, client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    client.mark_payload = {"markPrice": 63677.44, "time": _ms(datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc))}
    quote2 = port.fetch_executable_quote(canonical_symbol=snapshot.entries[0].canonical_symbol, observed_at=OBSERVED)
    assert quote2.mark_price == 63677.44

    # C. Malformed string fails
    port, client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    client.mark_payload = {"markPrice": "1,000", "time": _ms(datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc))}
    with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1):
        port.fetch_executable_quote(canonical_symbol=snapshot.entries[0].canonical_symbol, observed_at=OBSERVED)

    # D. Missing field fails
    port, client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    client.mark_payload = {"time": _ms(datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc))}
    with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1):
        port.fetch_executable_quote(canonical_symbol=snapshot.entries[0].canonical_symbol, observed_at=OBSERVED)

    # E. NaN string fails
    port, client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    client.mark_payload = {"markPrice": "NaN", "time": _ms(datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc))}
    with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1):
        port.fetch_executable_quote(canonical_symbol=snapshot.entries[0].canonical_symbol, observed_at=OBSERVED)

    # F. Bool fails
    port, client = _port()
    snapshot = port.acquire_market_snapshot(observed_at=OBSERVED)
    client.mark_payload = {"markPrice": True, "time": _ms(datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc))}
    with pytest.raises(module.E6ProductionMarketAcquisitionErrorV1):
        port.fetch_executable_quote(canonical_symbol=snapshot.entries[0].canonical_symbol, observed_at=OBSERVED)
