"""Lazy, public-only Binance USD-M market acquisition for one P2 job."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib
import json
import math
import re
from typing import Callable, Final, Mapping

from engine.mode_scan_execution_evidence_v1 import (
    MODE_OI_OBSERVATION_SCHEMA_VERSION,
    MODE_UTC_CANDLE_SCHEMA_VERSION,
    ModeOiObservationV1,
    ModeUtcCandleV1,
    _TIMEFRAME_SECONDS as MODE_TIMEFRAME_SECONDS_V1,
)
from engine.mode_scan_execution_plan_v1 import (
    MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
    ModeMarketSnapshotEntryV1,
    ModeSymbolExecutionPlanV1,
    ModeTimeframeFetchPlanV1,
)


E6_PRODUCTION_MARKET_ACQUISITION_POLICY_V1: Final = (
    "e6-production-binance-public-market-policy-v1"
)
CCXT_PINNED_VERSION_V1: Final = "4.5.65"
BINANCE_USDM_VENUE_V1: Final = "BINANCE_USDM"
_UTC: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z"
)
_SYMBOL: Final = re.compile(r"[A-Z0-9]+/[A-Z0-9]+:[A-Z0-9]+\Z")
_TICK_SIZE: Final = re.compile(
    r"(?:[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])\Z"
)
_RAW_DECIMAL: Final = re.compile(r"[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?\Z")
_ERROR: Final = "INVALID_E6_PRODUCTION_MARKET_ACQUISITION"


class E6ProductionMarketAcquisitionErrorV1(ValueError):
    """Fixed-code boundary failure with an optional safe NO_TRADE reason."""

    def __init__(self, reason_code: str = "E2_ALL_INPUTS_UNAVAILABLE") -> None:
        self.code = _ERROR
        self.reason_code = reason_code
        super().__init__(_ERROR)


def _invalid(reason_code: str = "E2_ALL_INPUTS_UNAVAILABLE") -> None:
    raise E6ProductionMarketAcquisitionErrorV1(reason_code) from None


def _require(condition: bool, reason_code: str = "E2_ALL_INPUTS_UNAVAILABLE") -> None:
    if not condition:
        _invalid(reason_code)


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        _invalid()


def _digest(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _utc(value: object) -> tuple[str, datetime]:
    _require(type(value) is str and _UTC.fullmatch(value) is not None)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        _invalid()
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return value, parsed


def _milliseconds(value: object) -> tuple[str, datetime]:
    _require(type(value) in (int, float) and not isinstance(value, bool))
    numeric = float(value)
    _require(math.isfinite(numeric) and numeric >= 0 and numeric.is_integer())
    parsed = datetime.fromtimestamp(numeric / 1000, tz=timezone.utc)
    _require(parsed.microsecond == 0)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ"), parsed


def _finite(value: object, *, positive: bool = False) -> float:
    _require(type(value) in (int, float) and not isinstance(value, bool))
    numeric = float(value)
    _require(math.isfinite(numeric) and (numeric > 0 if positive else numeric >= 0))
    return numeric


def _parse_raw_decimal_number(value: object, *, positive: bool = False) -> float:
    if type(value) in (int, float):
        if positive or value >= 0:
            return _finite(value, positive=positive)
        _require(not isinstance(value, bool) and math.isfinite(float(value)))
        return float(value)
    if type(value) is not str or not value:
        _invalid()
    if _RAW_DECIMAL.fullmatch(value) is None:
        _invalid()
    import decimal
    try:
        dec = decimal.Decimal(value)
    except Exception:
        _invalid()
    if not dec.is_finite():
        _invalid()
    num = float(dec)
    if positive or num >= 0:
        return _finite(num, positive=positive)
    return num


def _symbol(value: object) -> str:
    _require(type(value) is str and _SYMBOL.fullmatch(value) is not None)
    return value


def _tick_size(value: object) -> str:
    canonical = str(value)
    _require(_TICK_SIZE.fullmatch(canonical) is not None)
    return canonical


@dataclass(frozen=True, slots=True)
class E6ProductionMarketSnapshotV1:
    policy_version: str
    observed_at: str
    entries: tuple[ModeMarketSnapshotEntryV1, ...]
    tick_sizes: tuple[tuple[str, str], ...]
    market_ids: tuple[tuple[str, str], ...]
    load_markets_count: int
    fetch_tickers_count: int
    snapshot_sha256: str

    def __post_init__(self) -> None:
        _require(self.policy_version == E6_PRODUCTION_MARKET_ACQUISITION_POLICY_V1)
        _utc(self.observed_at)
        _require(type(self.entries) in (tuple, list))
        entries = tuple(self.entries)
        _require(all(type(item) is ModeMarketSnapshotEntryV1 for item in entries))
        _require(
            tuple((item.canonical_symbol for item in entries))
            == tuple(sorted((item.canonical_symbol for item in entries), key=lambda symbol: (-next(entry.quote_volume_24h for entry in entries if entry.canonical_symbol == symbol), symbol)))
        )
        object.__setattr__(self, "entries", entries)
        ticks = tuple(tuple(item) for item in self.tick_sizes)
        ids = tuple(tuple(item) for item in self.market_ids)
        _require(tuple(sorted(ticks)) == ticks and tuple(sorted(ids)) == ids)
        _require(all(_symbol(item[0]) and _tick_size(item[1]) for item in ticks))
        _require(all(_symbol(item[0]) and type(item[1]) is str and item[1] for item in ids))
        _require({item.canonical_symbol for item in entries} == {item[0] for item in ticks} == {item[0] for item in ids})
        object.__setattr__(self, "tick_sizes", ticks)
        object.__setattr__(self, "market_ids", ids)
        _require(type(self.load_markets_count) is int and self.load_markets_count == 1)
        _require(type(self.fetch_tickers_count) is int and self.fetch_tickers_count == 1)
        _require(type(self.snapshot_sha256) is str and self.snapshot_sha256 == _digest(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "observed_at": self.observed_at,
            "entries": [item.to_mapping() for item in self.entries],
            "tick_sizes": [{"symbol": key, "tick_size": value} for key, value in self.tick_sizes],
            "market_ids": [{"symbol": key, "market_id": value} for key, value in self.market_ids],
            "load_markets_count": self.load_markets_count,
            "fetch_tickers_count": self.fetch_tickers_count,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["snapshot_sha256"] = self.snapshot_sha256
        return mapping

    def tick_size_for(self, symbol: str) -> str:
        _symbol(symbol)
        try:
            return dict(self.tick_sizes)[symbol]
        except KeyError:
            _invalid()


@dataclass(frozen=True, slots=True)
class E6ProductionExecutableQuoteEvidenceV1:
    policy_version: str
    venue: str
    canonical_symbol: str
    observed_at: str
    exchange_timestamp: str
    best_bid: float
    best_ask: float
    last_price: float
    mark_price: float
    tick_size: str
    order_book_sha256: str
    ticker_sha256: str
    mark_sha256: str
    order_book_call_count: int
    ticker_call_count: int
    mark_call_count: int
    quote_sha256: str

    def __post_init__(self) -> None:
        _require(self.policy_version == E6_PRODUCTION_MARKET_ACQUISITION_POLICY_V1)
        _require(self.venue == BINANCE_USDM_VENUE_V1)
        _symbol(self.canonical_symbol)
        _observed_text, observed = _utc(self.observed_at)
        _exchange_text, exchanged = _utc(self.exchange_timestamp)
        _require(exchanged <= observed, "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE")
        bid = _finite(self.best_bid, positive=True)
        ask = _finite(self.best_ask, positive=True)
        _require(bid < ask, "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE")
        _finite(self.last_price, positive=True)
        _finite(self.mark_price, positive=True)
        _tick_size(self.tick_size)
        for digest in (self.order_book_sha256, self.ticker_sha256, self.mark_sha256):
            _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest) is not None)
        for count in (self.order_book_call_count, self.ticker_call_count, self.mark_call_count):
            _require(type(count) is int and count == 1)
        _require(self.quote_sha256 == _digest(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "venue": self.venue,
            "canonical_symbol": self.canonical_symbol,
            "observed_at": self.observed_at,
            "exchange_timestamp": self.exchange_timestamp,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "last_price": self.last_price,
            "mark_price": self.mark_price,
            "tick_size": self.tick_size,
            "order_book_sha256": self.order_book_sha256,
            "ticker_sha256": self.ticker_sha256,
            "mark_sha256": self.mark_sha256,
            "order_book_call_count": self.order_book_call_count,
            "ticker_call_count": self.ticker_call_count,
            "mark_call_count": self.mark_call_count,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["quote_sha256"] = self.quote_sha256
        return mapping


def _default_ccxt_client_factory_v1():
    ccxt = importlib.import_module("ccxt")
    _require(getattr(ccxt, "__version__", None) == CCXT_PINNED_VERSION_V1)
    return ccxt.binance(
        {
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        }
    )


class E6ProductionBinancePublicMarketPortV1:
    """One-job lazy CCXT adapter; construction performs no external call."""

    __slots__ = (
        "_client_factory",
        "_client",
        "_snapshot",
        "_load_markets_count",
        "_fetch_tickers_count",
        "_order_book_count",
        "_ticker_count",
        "_mark_count",
    )

    def __init__(self, *, client_factory: Callable[[], object] = _default_ccxt_client_factory_v1) -> None:
        _require(callable(client_factory))
        self._client_factory = client_factory
        self._client = None
        self._snapshot = None
        self._load_markets_count = 0
        self._fetch_tickers_count = 0
        self._order_book_count = 0
        self._ticker_count = 0
        self._mark_count = 0

    def _selected_client(self):
        if self._client is None:
            client = self._client_factory()
            _require(client is not None)
            self._client = client
        return self._client

    def acquire_market_snapshot(self, *, observed_at: str) -> E6ProductionMarketSnapshotV1:
        canonical_observed, _parsed = _utc(observed_at)
        _require(self._snapshot is None and self._load_markets_count == 0 and self._fetch_tickers_count == 0)
        client = self._selected_client()
        try:
            self._load_markets_count += 1
            markets = client.load_markets()
            self._fetch_tickers_count += 1
            tickers = client.fetch_tickers()
        except Exception:
            _invalid()
        _require(isinstance(markets, Mapping) and isinstance(tickers, Mapping))
        rows: list[tuple[ModeMarketSnapshotEntryV1, str, str]] = []
        for symbol, market in markets.items():
            if not isinstance(market, Mapping) or type(symbol) is not str:
                continue
            if not (
                market.get("active") is True
                and market.get("quote") == "USDT"
                and market.get("settle") == "USDT"
                and market.get("type") == "swap"
                and market.get("linear") is True
                and market.get("swap") is True
            ):
                continue
            try:
                canonical_symbol = _symbol(symbol)
                ticker = tickers[canonical_symbol]
                _require(isinstance(ticker, Mapping))
                volume = _finite(ticker.get("quoteVolume", 0))
                precision = market.get("precision")
                _require(isinstance(precision, Mapping))
                tick = _tick_size(precision.get("price"))
                market_id = market.get("id")
                _require(type(market_id) is str and market_id)
                row = ModeMarketSnapshotEntryV1(
                    schema_version=MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
                    canonical_symbol=canonical_symbol,
                    quote_asset="USDT",
                    settle_asset="USDT",
                    market_kind="swap",
                    active=True,
                    linear=True,
                    perpetual=True,
                    quote_volume_24h=volume,
                )
            except Exception:
                continue
            rows.append((row, tick, market_id))
        rows.sort(key=lambda item: (-item[0].quote_volume_24h, item[0].canonical_symbol))
        content = {
            "policy_version": E6_PRODUCTION_MARKET_ACQUISITION_POLICY_V1,
            "observed_at": canonical_observed,
            "entries": tuple(item[0] for item in rows),
            "tick_sizes": tuple(sorted((item[0].canonical_symbol, item[1]) for item in rows)),
            "market_ids": tuple(sorted((item[0].canonical_symbol, item[2]) for item in rows)),
            "load_markets_count": 1,
            "fetch_tickers_count": 1,
        }
        provisional = E6ProductionMarketSnapshotV1.__new__(E6ProductionMarketSnapshotV1)
        for key, value in content.items():
            object.__setattr__(provisional, key, value)
        object.__setattr__(provisional, "snapshot_sha256", "0" * 64)
        snapshot = E6ProductionMarketSnapshotV1(**content, snapshot_sha256=_digest(provisional._content_mapping()))
        self._snapshot = snapshot
        return snapshot

    def fetch_candles(
        self, *, timeframe_plan: ModeTimeframeFetchPlanV1, observed_at: str
    ) -> tuple[ModeUtcCandleV1, ...]:
        _require(type(timeframe_plan) is ModeTimeframeFetchPlanV1)
        _canonical_observed, _observed_at = _utc(observed_at)
        client = self._selected_client()
        try:
            rows = client.fetch_ohlcv(
                timeframe_plan.canonical_symbol,
                timeframe=timeframe_plan.timeframe,
                limit=timeframe_plan.raw_fetch_limit,
            )
        except Exception:
            _invalid()
        _require(type(rows) in (tuple, list) and len(rows) == timeframe_plan.raw_fetch_limit)
        seconds = MODE_TIMEFRAME_SECONDS_V1.get(timeframe_plan.timeframe)
        _require(type(seconds) is int)
        candles = []
        for row in rows:
            _require(type(row) in (tuple, list) and len(row) >= 6)
            open_text, opened = _milliseconds(row[0])
            close_text = (opened + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
            candles.append(
                ModeUtcCandleV1(
                    schema_version=MODE_UTC_CANDLE_SCHEMA_VERSION,
                    timeframe=timeframe_plan.timeframe,
                    open_time=open_text,
                    close_time=close_text,
                    open=_finite(row[1], positive=True),
                    high=_finite(row[2], positive=True),
                    low=_finite(row[3], positive=True),
                    close=_finite(row[4], positive=True),
                    volume=_finite(row[5]),
                )
            )
        return tuple(candles)

    def fetch_open_interest(
        self, *, symbol_plan: ModeSymbolExecutionPlanV1, observed_at: str, period: str
    ) -> tuple[ModeOiObservationV1, ...]:
        _require(type(symbol_plan) is ModeSymbolExecutionPlanV1 and period == "5m")
        _utc(observed_at)
        client = self._selected_client()
        try:
            rows = client.fetch_open_interest_history(
                symbol_plan.canonical_symbol,
                timeframe="5m",
                limit=2,
                params={"paginate": False},
            )
        except Exception:
            _invalid()
        _require(type(rows) in (tuple, list) and len(rows) == 2)
        observations = []
        for row in rows:
            _require(isinstance(row, Mapping))
            timestamp = row.get("timestamp")
            close_text, _parsed = _milliseconds(timestamp)
            amount = row.get("openInterestAmount", row.get("openInterestValue"))
            observations.append(
                ModeOiObservationV1(
                    schema_version=MODE_OI_OBSERVATION_SCHEMA_VERSION,
                    close_time=close_text,
                    open_interest=_finite(amount),
                )
            )
        return tuple(observations)

    def fetch_executable_quote(
        self, *, canonical_symbol: str, observed_at: str
    ) -> E6ProductionExecutableQuoteEvidenceV1:
        symbol = _symbol(canonical_symbol)
        canonical_observed, observed = _utc(observed_at)
        _require(type(self._snapshot) is E6ProductionMarketSnapshotV1)
        _require(self._order_book_count == self._ticker_count == self._mark_count == 0)
        client = self._selected_client()
        market_id = dict(self._snapshot.market_ids).get(symbol)
        _require(type(market_id) is str)
        try:
            self._order_book_count += 1
            order_book = client.fetch_order_book(symbol, limit=5)
            self._ticker_count += 1
            ticker = client.fetch_ticker(symbol)
            self._mark_count += 1
            mark = client.fapiPublicGetPremiumIndex({"symbol": market_id})
        except Exception:
            _invalid("E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE")
        _require(
            isinstance(order_book, Mapping)
            and isinstance(ticker, Mapping)
            and isinstance(mark, Mapping),
            "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE",
        )
        try:
            bids = order_book["bids"]
            asks = order_book["asks"]
            _require(type(bids) in (tuple, list) and bids and type(asks) in (tuple, list) and asks)
            best_bid = _finite(bids[0][0], positive=True)
            best_ask = _finite(asks[0][0], positive=True)
            last_price = _finite(ticker["last"], positive=True)
            mark_price = _parse_raw_decimal_number(mark["markPrice"], positive=True)
            timestamps = []
            for raw in (order_book.get("timestamp"), ticker.get("timestamp"), mark.get("time", mark.get("timestamp"))):
                text_value, parsed = _milliseconds(raw)
                _require(parsed <= observed, "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE")
                timestamps.append((text_value, parsed))
            oldest = min(timestamps, key=lambda item: item[1])[0]
            content = {
                "policy_version": E6_PRODUCTION_MARKET_ACQUISITION_POLICY_V1,
                "venue": BINANCE_USDM_VENUE_V1,
                "canonical_symbol": symbol,
                "observed_at": canonical_observed,
                "exchange_timestamp": oldest,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "last_price": last_price,
                "mark_price": mark_price,
                "tick_size": self._snapshot.tick_size_for(symbol),
                "order_book_sha256": _digest(order_book),
                "ticker_sha256": _digest(ticker),
                "mark_sha256": _digest(mark),
                "order_book_call_count": 1,
                "ticker_call_count": 1,
                "mark_call_count": 1,
            }
            provisional = E6ProductionExecutableQuoteEvidenceV1.__new__(E6ProductionExecutableQuoteEvidenceV1)
            for key, value in content.items():
                object.__setattr__(provisional, key, value)
            object.__setattr__(provisional, "quote_sha256", "0" * 64)
            return E6ProductionExecutableQuoteEvidenceV1(
                **content, quote_sha256=_digest(provisional._content_mapping())
            )
        except E6ProductionMarketAcquisitionErrorV1:
            raise
        except Exception:
            _invalid("E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE")


def build_e6_production_binance_public_market_port_v1(
    *, client_factory: Callable[[], object] = _default_ccxt_client_factory_v1
) -> E6ProductionBinancePublicMarketPortV1:
    return E6ProductionBinancePublicMarketPortV1(client_factory=client_factory)


__all__ = (
    "E6ProductionBinancePublicMarketPortV1",
    "E6ProductionExecutableQuoteEvidenceV1",
    "E6ProductionMarketAcquisitionErrorV1",
    "E6ProductionMarketSnapshotV1",
    "build_e6_production_binance_public_market_port_v1",
)
