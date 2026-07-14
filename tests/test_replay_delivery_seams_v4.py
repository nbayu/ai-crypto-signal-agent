import json
import socket
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import requests

import engine.pre_delivery_flow_v4 as flow_module
import engine.pre_delivery_market_data_v4 as market_data_module
import engine.pre_delivery_validator_v4 as validator_module
import engine.top5_watchlist_artifact_v4 as top5_module
from engine.pine_bridge_v4 import (
    build_pine_bridge_artifact,
    build_pine_bridge_delivery_payload,
)
from engine.pre_delivery_flow_v4 import run_pre_delivery_flow
from engine.top5_watchlist_artifact_v4 import (
    build_top5_watchlist_artifact,
)


SYMBOL_ELIGIBLE = "AAA/USDT:USDT"
SYMBOL_REJECTED = "BBB/USDT:USDT"
VALIDATED_AT = "2026-07-02T00:00:00+00:00"


def _golden_zone():
    return {
        "direction": "BULLISH",
        "swing_low_index": 10,
        "swing_high_index": 20,
        "swing_low_at": "2026-07-01T00:00:00+00:00",
        "swing_high_at": "2026-07-01T08:00:00+00:00",
        "swing_low": 90.0,
        "swing_high": 110.0,
        "levels": {
            "-0.27": 115.4,
            "0.0": 110.0,
            "0.5": 100.0,
            "0.618": 97.64,
            "0.786": 94.28,
            "1.0": 90.0,
        },
        "entry_zone": {
            "level_from": 0.618,
            "level_to": 0.786,
            "price_low": 94.28,
            "price_high": 97.64,
        },
        "take_profit": {
            "level": -0.27,
            "price": 115.4,
        },
        "stop_loss": {
            "level": 1.0,
            "price": 90.0,
        },
    }


def _setup(symbol, rank, score):
    return {
        "rank": rank,
        "symbol": symbol,
        "final_rank_score": score,
        "reference_price": 100.0,
        "reference_candle_at": "2026-07-01T08:00:00+00:00",
        "golden_zone": _golden_zone(),
    }


def _source_artifact():
    setups = [
        _setup(SYMBOL_ELIGIBLE, 1, 95.0),
        _setup(SYMBOL_REJECTED, 2, 90.0),
    ]
    return {
        "generated_at": "2026-07-01T12:00:00+00:00",
        "setup_count": len(setups),
        "setups": setups,
    }


def _write_source(tmp_path):
    source_path = tmp_path / "top5.json"
    source_path.write_text(json.dumps(_source_artifact()))
    return source_path


def _candles(symbol):
    if symbol == SYMBOL_ELIGIBLE:
        row = (
            "2026-07-01T20:00:00+00:00",
            105.0,
            110.0,
            100.0,
            106.0,
        )
    elif symbol == SYMBOL_REJECTED:
        row = (
            "2026-07-01T20:00:00+00:00",
            105.0,
            116.0,
            100.0,
            115.0,
        )
    else:
        raise AssertionError(f"unexpected symbol: {symbol}")

    return pd.DataFrame(
        [row],
        columns=["timestamp", "open", "high", "low", "close"],
    ).assign(
        timestamp=lambda frame: pd.to_datetime(frame["timestamp"])
    )


def _recorded_candle_provider(calls):
    def provider(symbol):
        calls.append(symbol)
        return _candles(symbol)

    return provider


def _fail_if_called(name):
    def fail(*args, **kwargs):
        raise AssertionError(f"unexpected dependency call: {name}")

    return fail


def _install_real_semantic_spies(monkeypatch, calls):
    real_detect_trend = validator_module.detect_trend
    real_lifecycle = validator_module.evaluate_setup_lifecycle
    real_supersession = validator_module.evaluate_swing_supersession

    def detect_trend(candles):
        calls.append("detect_trend")
        return real_detect_trend(candles)

    def evaluate_lifecycle(setup, candles):
        calls.append(("lifecycle", setup["symbol"]))
        return real_lifecycle(setup, candles)

    def evaluate_supersession(setup, candles, trend):
        calls.append(("supersession", setup["symbol"], trend))
        return real_supersession(setup, candles, trend)

    monkeypatch.setattr(validator_module, "detect_trend", detect_trend)
    monkeypatch.setattr(
        validator_module,
        "evaluate_setup_lifecycle",
        evaluate_lifecycle,
    )
    monkeypatch.setattr(
        validator_module,
        "evaluate_swing_supersession",
        evaluate_supersession,
    )


def _injected_flow_dependencies(tmp_path, calls):
    delivery_path = tmp_path / "delivery.json"
    watchlist_path = tmp_path / "watchlist.txt"
    bridge_path = tmp_path / "pine.json"
    payload_path = tmp_path / "pine.txt"

    def delivery_saver(artifact):
        calls.append(("save_delivery", artifact))
        return delivery_path

    def tradingview_exporter(source_path, output_path):
        calls.append(("export_tradingview", source_path, output_path))
        return watchlist_path

    def pine_saver(bridge_artifact, delivery_payload):
        calls.append(("save_pine", bridge_artifact, delivery_payload))
        return bridge_path, payload_path

    return {
        "delivery_artifact_saver": delivery_saver,
        "tradingview_exporter": tradingview_exporter,
        "pine_delivery_saver": pine_saver,
    }


def test_injected_savers_receive_real_artifacts_in_production_order(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    source_path = _write_source(tmp_path)
    candle_calls = []
    semantic_calls = []
    side_effect_calls = []
    _install_real_semantic_spies(monkeypatch, semantic_calls)
    dependencies = _injected_flow_dependencies(tmp_path, side_effect_calls)

    result = run_pre_delivery_flow(
        source_path,
        tmp_path / "requested-watchlist.txt",
        closed_candle_provider=_recorded_candle_provider(candle_calls),
        validated_at=VALIDATED_AT,
        **dependencies,
    )

    assert candle_calls == [SYMBOL_ELIGIBLE, SYMBOL_REJECTED]
    assert semantic_calls == [
        "detect_trend",
        ("lifecycle", SYMBOL_ELIGIBLE),
        ("supersession", SYMBOL_ELIGIBLE, "SIDEWAYS"),
        "detect_trend",
        ("lifecycle", SYMBOL_REJECTED),
        ("supersession", SYMBOL_REJECTED, "SIDEWAYS"),
    ]
    assert [call[0] for call in side_effect_calls] == [
        "save_delivery",
        "export_tradingview",
        "save_pine",
    ]

    delivery_artifact = side_effect_calls[0][1]
    assert delivery_artifact["eligible_setup_count"] == 1
    assert delivery_artifact["setup_count"] == 1
    assert [
        setup["symbol"] for setup in delivery_artifact["setups"]
    ] == [SYMBOL_ELIGIBLE]
    assert delivery_artifact["evaluations"][0]["lifecycle"]["state"] == (
        "WAITING_ENTRY"
    )
    assert delivery_artifact["evaluations"][0]["delivery_eligible"] is True
    rejected = delivery_artifact["evaluations"][1]
    assert rejected["lifecycle"]["state"] == "ENTRY_MISSED"
    assert rejected["supersession"]["state"] == "NO_REPLACEMENT"
    assert rejected["delivery_eligible"] is False
    assert rejected["rejection_reasons"] == ["ENTRY_MISSED"]

    assert side_effect_calls[1][1:] == (
        tmp_path / "delivery.json",
        tmp_path / "requested-watchlist.txt",
    )
    expected_bridge = build_pine_bridge_artifact(delivery_artifact)
    expected_payload = build_pine_bridge_delivery_payload(expected_bridge)
    assert side_effect_calls[2][1:] == (expected_bridge, expected_payload)
    assert result == {
        "delivery_artifact_path": tmp_path / "delivery.json",
        "tradingview_watchlist_path": tmp_path / "watchlist.txt",
        "pine_bridge_artifact_path": tmp_path / "pine.json",
        "pine_delivery_payload_path": tmp_path / "pine.txt",
    }
    assert not (tmp_path / "data").exists()


def test_delivery_saver_failure_stops_every_later_side_effect(tmp_path):
    source_path = _write_source(tmp_path)
    calls = []
    failure = RuntimeError("delivery saver failed")

    def delivery_saver(artifact):
        calls.append("delivery")
        raise failure

    with pytest.raises(RuntimeError) as exc_info:
        run_pre_delivery_flow(
            source_path,
            tmp_path / "watchlist.txt",
            closed_candle_provider=lambda symbol: _candles(symbol),
            validated_at=VALIDATED_AT,
            delivery_artifact_saver=delivery_saver,
            tradingview_exporter=lambda *args: calls.append("tradingview"),
            pine_delivery_saver=lambda *args: calls.append("pine"),
        )

    assert exc_info.value is failure
    assert calls == ["delivery"]


def test_tradingview_failure_occurs_after_delivery_and_stops_pine(tmp_path):
    source_path = _write_source(tmp_path)
    calls = []
    failure = LookupError("watchlist exporter failed")

    def delivery_saver(artifact):
        calls.append("delivery")
        return tmp_path / "delivery.json"

    def exporter(source_path, output_path):
        calls.append("tradingview")
        raise failure

    with pytest.raises(LookupError) as exc_info:
        run_pre_delivery_flow(
            source_path,
            tmp_path / "watchlist.txt",
            closed_candle_provider=lambda symbol: _candles(symbol),
            validated_at=VALIDATED_AT,
            delivery_artifact_saver=delivery_saver,
            tradingview_exporter=exporter,
            pine_delivery_saver=lambda *args: calls.append("pine"),
        )

    assert exc_info.value is failure
    assert calls == ["delivery", "tradingview"]


def test_pine_saver_failure_occurs_after_earlier_side_effects(tmp_path):
    source_path = _write_source(tmp_path)
    calls = []
    failure = OSError("pine saver failed")

    def delivery_saver(artifact):
        calls.append("delivery")
        return tmp_path / "delivery.json"

    def exporter(source_path, output_path):
        calls.append("tradingview")
        return tmp_path / "watchlist.txt"

    def pine_saver(bridge_artifact, delivery_payload):
        calls.append("pine")
        raise failure

    with pytest.raises(OSError) as exc_info:
        run_pre_delivery_flow(
            source_path,
            tmp_path / "watchlist.txt",
            closed_candle_provider=lambda symbol: _candles(symbol),
            validated_at=VALIDATED_AT,
            delivery_artifact_saver=delivery_saver,
            tradingview_exporter=exporter,
            pine_delivery_saver=pine_saver,
        )

    assert exc_info.value is failure
    assert calls == ["delivery", "tradingview", "pine"]


def test_omitted_savers_resolve_module_globals_at_call_time(
    tmp_path,
    monkeypatch,
):
    source_path = _write_source(tmp_path)
    calls = []

    monkeypatch.setattr(
        flow_module,
        "save_pre_delivery_artifact",
        lambda artifact: calls.append("delivery")
        or tmp_path / "delivery.json",
    )
    monkeypatch.setattr(
        flow_module,
        "export_tradingview_watchlist",
        lambda source, output: calls.append("tradingview")
        or tmp_path / "watchlist.txt",
    )
    monkeypatch.setattr(
        flow_module,
        "save_pine_delivery_artifact",
        lambda artifact, payload: calls.append("pine")
        or (tmp_path / "pine.json", tmp_path / "pine.txt"),
    )

    result = run_pre_delivery_flow(
        source_path,
        tmp_path / "requested-watchlist.txt",
        closed_candle_provider=lambda symbol: _candles(symbol),
        validated_at=VALIDATED_AT,
    )

    assert calls == ["delivery", "tradingview", "pine"]
    assert result["delivery_artifact_path"] == tmp_path / "delivery.json"
    assert result["tradingview_watchlist_path"] == tmp_path / "watchlist.txt"


def test_explicit_none_savers_resolve_module_globals_at_call_time(
    tmp_path,
    monkeypatch,
):
    source_path = _write_source(tmp_path)
    calls = []

    monkeypatch.setattr(
        flow_module,
        "save_pre_delivery_artifact",
        lambda artifact: calls.append("delivery")
        or tmp_path / "delivery.json",
    )
    monkeypatch.setattr(
        flow_module,
        "export_tradingview_watchlist",
        lambda source, output: calls.append("tradingview")
        or tmp_path / "watchlist.txt",
    )
    monkeypatch.setattr(
        flow_module,
        "save_pine_delivery_artifact",
        lambda artifact, payload: calls.append("pine")
        or (tmp_path / "pine.json", tmp_path / "pine.txt"),
    )

    run_pre_delivery_flow(
        source_path,
        tmp_path / "requested-watchlist.txt",
        closed_candle_provider=lambda symbol: _candles(symbol),
        validated_at=VALIDATED_AT,
        delivery_artifact_saver=None,
        tradingview_exporter=None,
        pine_delivery_saver=None,
    )

    assert calls == ["delivery", "tradingview", "pine"]


def test_saver_dependencies_are_keyword_only(tmp_path):
    source_path = _write_source(tmp_path)

    with pytest.raises(TypeError):
        run_pre_delivery_flow(
            source_path,
            tmp_path / "watchlist.txt",
            lambda symbol: _candles(symbol),
            VALIDATED_AT,
            object(),
            object(),
            object(),
        )


def test_injected_flow_avoids_default_paths_and_live_network(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    source_path = _write_source(tmp_path)
    side_effect_calls = []
    dependencies = _injected_flow_dependencies(tmp_path, side_effect_calls)

    monkeypatch.setattr(
        flow_module,
        "save_pre_delivery_artifact",
        _fail_if_called("default delivery saver"),
    )
    monkeypatch.setattr(
        flow_module,
        "export_tradingview_watchlist",
        _fail_if_called("default TradingView exporter"),
    )
    monkeypatch.setattr(
        flow_module,
        "save_pine_delivery_artifact",
        _fail_if_called("default Pine saver"),
    )
    monkeypatch.setattr(
        market_data_module,
        "get_ohlcv",
        _fail_if_called("live Binance market data"),
    )
    monkeypatch.setattr(requests, "get", _fail_if_called("requests.get"))
    monkeypatch.setattr(
        socket,
        "create_connection",
        _fail_if_called("socket.create_connection"),
    )

    result = run_pre_delivery_flow(
        source_path,
        tmp_path / "requested-watchlist.txt",
        closed_candle_provider=lambda symbol: _candles(symbol),
        validated_at=VALIDATED_AT,
        **dependencies,
    )

    assert result["delivery_artifact_path"].parent == tmp_path
    assert result["tradingview_watchlist_path"].parent == tmp_path
    assert result["pine_bridge_artifact_path"].parent == tmp_path
    assert result["pine_delivery_payload_path"].parent == tmp_path
    assert not (tmp_path / "data").exists()


def _top5_rows():
    return [
        _setup(SYMBOL_ELIGIBLE, 1, 95.0),
        _setup(SYMBOL_REJECTED, 2, 90.0),
    ]


def test_top5_injected_clock_is_called_once_and_preserves_payload():
    fixed = datetime(2026, 7, 14, 9, 30, tzinfo=timezone.utc)
    calls = []

    def now_provider():
        calls.append("now")
        return fixed

    artifact = build_top5_watchlist_artifact(
        _top5_rows(),
        now_provider=now_provider,
    )

    assert calls == ["now"]
    assert artifact["generated_at"] == fixed.isoformat()
    assert artifact["setup_count"] == 2
    assert [row["symbol"] for row in artifact["setups"]] == [
        SYMBOL_ELIGIBLE,
        SYMBOL_REJECTED,
    ]
    assert [row["rank"] for row in artifact["setups"]] == [1, 2]


def test_top5_fixed_clock_is_repeatable_and_changes_only_generated_at():
    first_time = datetime(2026, 7, 14, 9, 30, tzinfo=timezone.utc)
    second_time = datetime(2026, 7, 14, 10, 30, tzinfo=timezone.utc)

    first = build_top5_watchlist_artifact(
        _top5_rows(),
        now_provider=lambda: first_time,
    )
    repeated = build_top5_watchlist_artifact(
        _top5_rows(),
        now_provider=lambda: first_time,
    )
    changed = build_top5_watchlist_artifact(
        _top5_rows(),
        now_provider=lambda: second_time,
    )

    assert first == repeated
    assert first["generated_at"] != changed["generated_at"]
    assert first["setup_count"] == changed["setup_count"]
    assert first["setups"] == changed["setups"]


def test_top5_injected_clock_does_not_use_module_ambient_clock(monkeypatch):
    class ForbiddenDateTime:
        @classmethod
        def now(cls):
            raise AssertionError("ambient clock used")

    monkeypatch.setattr(top5_module, "datetime", ForbiddenDateTime)
    fixed = datetime(2026, 7, 14, 9, 30, tzinfo=timezone.utc)

    artifact = build_top5_watchlist_artifact(
        _top5_rows(),
        now_provider=lambda: fixed,
    )

    assert artifact["generated_at"] == fixed.isoformat()


def test_top5_omitted_clock_resolves_module_global_at_call_time(monkeypatch):
    fixed = datetime(2026, 7, 14, 9, 30, tzinfo=timezone.utc)
    calls = []

    class FixedDateTime:
        @classmethod
        def now(cls):
            calls.append("now")
            return fixed

    monkeypatch.setattr(top5_module, "datetime", FixedDateTime)

    artifact = build_top5_watchlist_artifact(_top5_rows())

    assert calls == ["now"]
    assert artifact["generated_at"] == fixed.isoformat()


def test_top5_explicit_none_clock_resolves_module_global_at_call_time(
    monkeypatch,
):
    fixed = datetime(2026, 7, 14, 9, 30, tzinfo=timezone.utc)
    calls = []

    class FixedDateTime:
        @classmethod
        def now(cls):
            calls.append("now")
            return fixed

    monkeypatch.setattr(top5_module, "datetime", FixedDateTime)

    artifact = build_top5_watchlist_artifact(
        _top5_rows(),
        now_provider=None,
    )

    assert calls == ["now"]
    assert artifact["generated_at"] == fixed.isoformat()


def test_top5_clock_dependency_is_keyword_only_and_must_be_callable():
    with pytest.raises(TypeError):
        build_top5_watchlist_artifact(_top5_rows(), lambda: datetime.now())

    with pytest.raises(TypeError):
        build_top5_watchlist_artifact(
            _top5_rows(),
            now_provider=object(),
        )
