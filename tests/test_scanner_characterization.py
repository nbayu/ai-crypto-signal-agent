from concurrent.futures import Future

import pandas as pd
import pytest

import engine.scanner as scanner


def _ohlcv_frame():
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03"]
            ),
            "open": [99, 109, 119],
            "high": [101, 111, 121],
            "low": [98, 108, 118],
            "close": [100, 110, 120],
        }
    )


def test_scan_symbol_quality_rejection_short_circuits(monkeypatch):
    calls = []
    monkeypatch.setattr(scanner, "get_ohlcv", lambda symbol: _ohlcv_frame())
    monkeypatch.setattr(
        scanner, "check_quality", lambda df: {"qualified": False, "score": 1}
    )

    for name in (
        "analyze_market_structure",
        "build_golden_zone_skill",
        "mtf_confirm",
        "calculate_score",
        "calculate_entry_score",
        "volume_metrics_v2",
        "detect_order_blocks",
        "detect_fvg",
        "detect_liquidity_sweep",
        "calculate_atr",
        "distance_to_order_block",
        "distance_to_fvg",
        "get_volume",
        "volume_spike",
        "get_open_interest",
        "open_interest_growth",
    ):
        monkeypatch.setattr(scanner, name, lambda *args, _name=name, **kwargs: calls.append(_name))

    assert scanner.scan_symbol("BTCUSDT") == (None, "QUALITY")
    assert calls == []


def test_scan_symbol_mtf_rejection_uses_closed_data(monkeypatch):
    df = _ohlcv_frame()
    seen = {}

    def analyze(frame):
        seen["structure"] = frame
        return {"trend": "UP", "bos": True, "choch": False}

    monkeypatch.setattr(scanner, "get_ohlcv", lambda symbol: df)
    monkeypatch.setattr(scanner, "check_quality", lambda frame: {"qualified": True, "score": 9})
    monkeypatch.setattr(scanner, "analyze_market_structure", analyze)
    monkeypatch.setattr(
        scanner,
        "build_golden_zone_skill",
        lambda frame, trend: seen.update(golden=(frame, trend)) or {"zone": "sentinel"},
    )
    monkeypatch.setattr(scanner, "volume_metrics_v2", lambda frame: {"volume_ratio": 1, "volume_score": 2, "data_status": "OK"})
    monkeypatch.setattr(scanner, "detect_order_blocks", lambda frame: [])
    monkeypatch.setattr(scanner, "mtf_confirm", lambda symbol: {"confirmed": False, "score": 0})
    monkeypatch.setattr(scanner, "calculate_score", lambda result: pytest.fail("score should not run"))
    monkeypatch.setattr(scanner, "calculate_entry_score", lambda result: pytest.fail("entry score should not run"))

    assert scanner.scan_symbol("ETHUSDT") == (None, "MTF")
    pd.testing.assert_frame_equal(seen["structure"], df.iloc[:-1])
    pd.testing.assert_frame_equal(seen["golden"][0], df.iloc[:-1])
    assert seen["structure"] is not df
    assert seen["golden"][0] is not df


def _patch_success_dependencies(monkeypatch, *, distance_ob=5, score=42):
    df = _ohlcv_frame()
    seen = {}
    monkeypatch.setattr(scanner, "get_ohlcv", lambda symbol: df)
    monkeypatch.setattr(scanner, "check_quality", lambda frame: {"qualified": True, "score": 9})
    monkeypatch.setattr(scanner, "analyze_market_structure", lambda frame: seen.update(structure=frame) or {"trend": "UP", "bos": True, "choch": False})
    monkeypatch.setattr(scanner, "build_golden_zone_skill", lambda frame, trend: seen.update(golden=(frame, trend)) or {"zone": "GZ"})
    monkeypatch.setattr(scanner, "volume_metrics_v2", lambda frame: seen.update(volume_v2=frame) or {"volume_ratio": 1.5, "volume_score": 7, "data_status": "OK"})
    monkeypatch.setattr(scanner, "detect_order_blocks", lambda frame: [{"mitigated": False}, {"mitigated": True}, {"mitigated": False}])
    monkeypatch.setattr(scanner, "mtf_confirm", lambda symbol: {"confirmed": True, "score": 6})
    monkeypatch.setattr(scanner, "detect_fvg", lambda frame: seen.update(fvg=frame) or [1, 2, 3])
    monkeypatch.setattr(scanner, "detect_liquidity_sweep", lambda frame: seen.update(liquidity=frame) or [1, 2])
    monkeypatch.setattr(scanner, "calculate_atr", lambda frame: seen.update(atr=frame) or 10)
    monkeypatch.setattr(scanner, "distance_to_order_block", lambda frame: seen.update(distance_ob=frame) or distance_ob)
    monkeypatch.setattr(scanner, "distance_to_fvg", lambda frame: seen.update(distance_fvg=frame) or 2)
    monkeypatch.setattr(scanner, "get_volume", lambda symbol: 60)
    monkeypatch.setattr(scanner, "volume_spike", lambda frame: seen.update(volume_spike=frame) or True)
    monkeypatch.setattr(scanner, "get_open_interest", lambda symbol: 70)
    monkeypatch.setattr(scanner, "open_interest_growth", lambda symbol: 8)
    monkeypatch.setattr(scanner, "calculate_score", lambda result: score)
    seen["entry"] = []
    monkeypatch.setattr(scanner, "calculate_entry_score", lambda result: seen["entry"].append(result.copy()) or 33)
    return df, seen


def test_scan_symbol_success_contract_and_data_flow(monkeypatch):
    df, seen = _patch_success_dependencies(monkeypatch, distance_ob=15, score=42)

    result, reason = scanner.scan_symbol("BTCUSDT")

    assert reason is None
    assert result == {
        "symbol": "BTCUSDT",
        "reference_price": 110.0,
        "reference_candle_at": "2024-01-02T00:00:00",
        "trend": "UP",
        "mtf": {"confirmed": True, "score": 6},
        "mtf_score": 6,
        "bos": True,
        "choch": False,
        "golden_zone": {"zone": "GZ"},
        "quality": 9,
        "fvg": 3,
        "order_blocks": 2,
        "liquidity": 2,
        "atr": 10,
        "distance_ob": 15,
        "distance_fvg": 2,
        "volume": 60,
        "volume_spike": True,
        "volume_ratio": 1.5,
        "volume_v2_score": 7,
        "volume_v2_status": "OK",
        "open_interest": 70,
        "oi_growth": 8,
        "score": 38,
        "entry_score": 33,
    }
    pd.testing.assert_frame_equal(seen["structure"], df.iloc[:-1])
    pd.testing.assert_frame_equal(seen["golden"][0], df.iloc[:-1])
    for name in ("volume_v2", "fvg", "liquidity", "atr", "distance_ob", "distance_fvg", "volume_spike"):
        assert seen[name] is df
    assert seen["entry"][0]["score"] == 38


@pytest.mark.parametrize(
    ("distance_ob", "base_score", "expected"),
    [(25, 20, 12), (15, 20, 16), (10, 20, 20), (25, 5, 0)],
)
def test_scan_symbol_score_penalty_contract(monkeypatch, distance_ob, base_score, expected):
    _patch_success_dependencies(monkeypatch, distance_ob=distance_ob, score=base_score)
    result, reason = scanner.scan_symbol("BTCUSDT")
    assert reason is None
    assert result["score"] == expected


def test_scan_symbol_exception_contract(monkeypatch, capsys):
    monkeypatch.setattr(scanner, "get_ohlcv", lambda symbol: (_ for _ in ()).throw(RuntimeError("boom")))
    assert scanner.scan_symbol("BTCUSDT") == (None, "ERROR")
    output = capsys.readouterr().out
    assert "BTCUSDT" in output
    assert "boom" in output


class _ImmediateExecutor:
    def __init__(self, events, submissions, max_workers):
        self.events = events
        self.submissions = submissions
        events.append(("executor", max_workers))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, function, symbol):
        self.events.append(("submit", symbol))
        self.submissions.append((function, symbol))
        future = Future()
        future.set_result(function(symbol))
        return future


def test_scan_market_orchestration_and_summary(monkeypatch, capsys):
    scan_results = {
        "AAA": ({"symbol": "AAA", "score": 2}, None),
        "BBB": (None, "QUALITY"),
        "CCC": ({"symbol": "CCC", "score": 9}, None),
    }
    events = []
    submissions = []
    scan_calls = []

    def fake_scan_symbol(symbol):
        scan_calls.append(symbol)
        return scan_results[symbol]

    monkeypatch.setattr(scanner, "get_symbols", lambda: ["AAA", "BBB", "CCC"])
    monkeypatch.setattr(scanner, "refresh_cache", lambda: events.append(("refresh",)))
    monkeypatch.setattr(scanner, "scan_symbol", fake_scan_symbol)
    monkeypatch.setattr(
        scanner,
        "ThreadPoolExecutor",
        lambda max_workers: _ImmediateExecutor(events, submissions, max_workers),
    )
    monkeypatch.setattr(scanner, "as_completed", lambda futures: list(futures))

    assert scanner.scan_market() == [scan_results["CCC"][0], scan_results["AAA"][0]]
    assert events == [("refresh",), ("executor", 20), ("submit", "AAA"), ("submit", "BBB"), ("submit", "CCC")]
    assert scan_calls == ["AAA", "BBB", "CCC"]
    assert [symbol for function, symbol in submissions] == ["AAA", "BBB", "CCC"]
    assert all(function is scanner.scan_symbol for function, symbol in submissions)
    output = capsys.readouterr().out
    assert "========== MARKET SUMMARY ==========" in output
    assert "Scanned  : 3" in output
    assert "Rejected : 1" in output
    assert "Qualified: 2" in output
    assert "===================================" in output
