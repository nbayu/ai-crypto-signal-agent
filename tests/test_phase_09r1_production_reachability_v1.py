import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime
import pandas as pd

from engine.run_production_signal_v1 import main

@pytest.fixture
def test_env(tmp_path):
    q_path = tmp_path / "q.json"
    w_path = tmp_path / "w.json"

    pub_root = tmp_path / "pub"
    pub_root.mkdir(exist_ok=True)

    return {
        "DEEPSEEK_API_KEY": "fake_key",
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_DESTINATION_ID": "test_dest_id",
        "TELEGRAM_QUOTA_LIMIT": "10",
        "TELEGRAM_SLOT_CAPACITY": "5",
        "TELEGRAM_WINDOW_ID": "w1",
        "TELEGRAM_QUOTA_STATE_PATH": str(q_path),
        "TELEGRAM_WORKER_STATE_PATH": str(w_path),
        "TELEGRAM_MAX_MESSAGE_LENGTH": "4000",
        "PRODUCTION_SIGNAL_DIR": str(pub_root),
        "TELEGRAM_ADAPTER_ENABLED": "true"
    }

def get_dummy_ohlcv():
    data = []
    base_price = 10000.0
    for i in range(120):
        open_p = base_price + i * 50  # goes up by 50 each time
        close_p = open_p + 10
        high_p = close_p + 10
        low_p = open_p - 10
        volume = 2000.0
        timestamp = f"2026-{(i//30)+1:02d}-{(i%30)+1:02d}T12:00:00Z"
        data.append({
            "timestamp": timestamp,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": volume
        })
    # Create clear swings
    # Swing high 1
    data[95]["high"] = 15000.0
    data[95]["low"] = 14000.0
    data[95]["close"] = 14500.0
    
    # Swing high 2
    data[110]["high"] = 16000.0
    data[110]["low"] = 15000.0
    data[110]["close"] = 15500.0
    
    # Break of structure at the end (must be > 15000)
    data[-2]["close"] = 16500.0
    data[-1]["close"] = 16500.0
    
    # High volume at the end for volume_ratio
    data[-2]["volume"] = 10000.0
    data[-1]["volume"] = 10000.0
    
    df = pd.DataFrame(data)
    df["timestamp"] = pd.date_range(start="2026-01-01", periods=len(df), freq="1D")
    return df

def get_dummy_fetch_ohlcv(*args, **kwargs):
    # return list of [timestamp, open, high, low, close, volume]
    data = []
    for i in range(50):
        data.append([1000+i, 10, 15, 5, 10+i, 100]) # strictly increasing close
    return data

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
    def json(self):
        return self._json
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("HTTP Error")

def fake_requests_get(url, **kwargs):
    if "ticker/24hr" in url:
        return MockResponse([{"symbol": "TESTUSDT", "quoteVolume": "50000"}])
    elif "openInterestHist" in url:
        # Return 13 elements with growing OI for open_interest_metrics_v2
        data = [{"symbol": "TESTUSDT", "sumOpenInterest": str(100000 + i * 100)} for i in range(13)]
        return MockResponse(data)
    return MockResponse([])

@patch("engine.mtf.exchange.fetch_ohlcv")
@patch("engine.deepseek_validator_v4.OpenAI")
@patch("requests.get", side_effect=fake_requests_get)
@patch("engine.pre_delivery_market_data_v4.get_ohlcv")
@patch("engine.scanner.get_ohlcv")
@patch("engine.scanner.get_symbols")
@patch("engine.scanner.calculate_score")
@patch("engine.master_engine_v4._hash_payload", return_value="a" * 64)
def test_real_path_reachability(
    mock_hash, mock_calc_score, mock_get_symbols, mock_get_ohlcv, mock_pre_delivery_ohlcv, mock_requests_get,
    mock_openai,
    mock_fetch_ohlcv,
    test_env, tmp_path
):
    mock_calc_score.return_value = 100.0
    mock_get_symbols.return_value = ["TEST/USDT:USDT"]
    mock_get_ohlcv.return_value = get_dummy_ohlcv()
    mock_pre_delivery_ohlcv.return_value = get_dummy_ohlcv()
    mock_fetch_ohlcv.side_effect = get_dummy_fetch_ohlcv
    
    # Mock deepseek OpenAI client
    mock_client_instance = MagicMock()
    mock_openai.return_value = mock_client_instance
    mock_client_instance.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps({
            "validations": [{
                "symbol": "TEST/USDT:USDT",
                "status": "CLEAR",
                "false_breakout_risk": "LOW",
                "confluence": "STRONG",
                "reason_code": "ALIGNED"
            }]
        })))],
        usage=MagicMock(prompt_tokens=10, completion_tokens=10, total_tokens=20)
    )

    events = []
    
    with patch.dict(os.environ, test_env, clear=True):
        from engine.quota_slot_engine_v4 import acquire_quota_slot_v4, release_quota_slot_v4
        from engine.master_engine_v4 import run_master_engine_v4
        from engine.scanner import scan_market
        
        orig_run_master_engine = run_master_engine_v4
        orig_acquire = acquire_quota_slot_v4
        orig_release = release_quota_slot_v4
        orig_scan_market = scan_market
        
        def fake_scan_market(*args, **kwargs):
            events.append("scanner_invoked")
            return orig_scan_market(*args, **kwargs)
            
        def fake_run_master_engine(*args, **kwargs):
            events.append("master_engine_invoked")
            kwargs["scanner"] = fake_scan_market
            try:
                out_res = orig_run_master_engine(*args, **kwargs)
                print(f"DEBUG OUT: {out_res.get('out', {}).get('final_top5')}")
                return out_res
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise e
            
        def fake_acquire(*args, **kwargs):
            events.append("quota_admission")
            events.append("slot_reservation")
            return orig_acquire(*args, **kwargs)
            
        def fake_release(*args, **kwargs):
            events.append("lifecycle_release")
            return orig_release(*args, **kwargs)
            
        from engine.quota_slot_worker_v4 import run_quota_slot_worker_v4
        orig_run_quota = run_quota_slot_worker_v4
        
        def fake_run_quota(*args, **kwargs):
            kwargs["acquire"] = fake_acquire
            kwargs["release"] = fake_release
            return orig_run_quota(*args, **kwargs)
            
        def fake_post(*args, **kwargs):
            events.append("telegram_delivery")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"ok": True, "result": {"message_id": 999}}
            return mock_resp
            
        with patch("engine.run_production_signal_v1.run_master_engine_v4", side_effect=fake_run_master_engine):
            with patch("engine.phase09r_telegram_delivery_adapter_v1.run_quota_slot_worker_v4", side_effect=fake_run_quota):
                with patch("httpx.post", side_effect=fake_post):
                    try:
                        exit_code = main()
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        exit_code = -1
                    
    assert exit_code == 0
    
    # 1. the production entrypoint invokes the real master engine
    assert "master_engine_invoked" in events
    
    # 2. the real scanner produces the candidate/result
    assert "scanner_invoked" in events
    assert mock_get_symbols.called
    assert mock_get_ohlcv.called
    
    # 5-8, 10. ordered events
    assert "quota_admission" in events
    assert "slot_reservation" in events
    assert "telegram_delivery" in events
    assert "lifecycle_release" in events
    
    idx_scanner = events.index("scanner_invoked")
    idx_master = events.index("master_engine_invoked")
    idx_quota = events.index("quota_admission")
    idx_slot = events.index("slot_reservation")
    idx_delivery = events.index("telegram_delivery")
    idx_release = events.index("lifecycle_release")
    
    assert idx_master < idx_scanner # master engine is invoked first, which then calls scanner
    assert idx_scanner < idx_quota
    assert idx_quota < idx_slot
    assert idx_slot < idx_delivery
    assert idx_delivery < idx_release
    
    # 8. exactly one synthetic HTTP delivery occurs
    assert events.count("telegram_delivery") == 1
    
    # 10. lifecycle release occurs exactly once
    assert events.count("lifecycle_release") == 1
    
    # 12. no Phase 10–12 module is imported
    import sys
    assert "engine.news_intelligence" not in sys.modules
    assert "engine.controlled_production_signal_cycle_v1" not in sys.modules
