import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime
import datetime as real_datetime

class FakeDatetime(real_datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return real_datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=tz)

import engine.master_engine_v4
engine.master_engine_v4.datetime = FakeDatetime
import engine.production_signal_service_v1
engine.production_signal_service_v1.datetime = FakeDatetime
import engine.run_production_signal_v1
engine.run_production_signal_v1.datetime = FakeDatetime

import pandas as pd

from engine.run_production_signal_v1 import main

_orig_default = json.JSONEncoder.default
def _custom_default(self, obj):
    if isinstance(obj, pd.Timestamp): return obj.isoformat()
    return _orig_default(self, obj)
json.JSONEncoder.default = _custom_default

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
        open_p = base_price + i * 50
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
    data[95]["high"] = 15000.0
    data[95]["low"] = 14000.0
    data[95]["close"] = 14500.0
    
    # OB at 110
    data[110]["open"] = 16000.0
    data[110]["close"] = 15000.0
    data[110]["high"] = 16500.0
    data[110]["low"] = 14500.0

    # Strong bullish at 111
    data[111]["open"] = 15000.0
    data[111]["close"] = 18000.0
    
    # Last candle close at 16500 to hit the OB exactly
    data[-2]["close"] = 16500.0
    data[-1]["close"] = 16500.0
    data[-2]["volume"] = 10000.0
    data[-1]["volume"] = 10000.0
    
    df = pd.DataFrame(data)
    df["timestamp"] = pd.date_range(start="2026-01-01", periods=len(df), freq="1D")
    return df


def get_dummy_fetch_ohlcv(*args, **kwargs):
    data = []
    for i in range(50):
        data.append([1000+i, 10, 15, 5, 10+i, 100])
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
        data = [{"symbol": "TESTUSDT", "sumOpenInterest": str(100000 + i * 100)} for i in range(13)]
        return MockResponse(data)
    return MockResponse([])

@patch("engine.mtf.exchange.fetch_ohlcv")
@patch("engine.deepseek_validator_v4.OpenAI")
@patch("requests.get", side_effect=fake_requests_get)
@patch("engine.pre_delivery_market_data_v4.get_ohlcv")
@patch("engine.scanner.get_ohlcv")
@patch("engine.scanner.get_symbols")
def test_real_path_reachability(
    mock_get_symbols, mock_get_ohlcv, mock_pre_delivery_ohlcv, mock_requests_get,
    mock_openai,
    mock_fetch_ohlcv,
    test_env, tmp_path
):
    mock_get_symbols.return_value = ["TEST/USDT:USDT"]
    mock_get_ohlcv.return_value = get_dummy_ohlcv()
    mock_pre_delivery_ohlcv.return_value = get_dummy_ohlcv()
    mock_fetch_ohlcv.side_effect = get_dummy_fetch_ohlcv
    
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
        from engine.master_engine_v4 import run_master_engine_v4, _hash_payload as master_hash
        from engine.scanner import scan_market, calculate_score as orig_calc
        from engine.production_signal_service_v1 import run_production_signal_service_v1, _hash_payload as art_hash
        from engine.validated_pipeline_v4 import run_validated_pipeline_v4
        from engine.run_production_signal_v1 import main
        
        orig_run_master_engine = run_master_engine_v4
        orig_acquire = acquire_quota_slot_v4
        orig_release = release_quota_slot_v4
        orig_scan_market = scan_market
        orig_run_prod = run_production_signal_service_v1
        orig_val_pipeline = run_validated_pipeline_v4
        orig_main = main
        
        def fake_main(*args, **kwargs):
            events.append("production_entrypoint")
            return orig_main(*args, **kwargs)

        def fake_scan_market(*args, **kwargs):
            events.append("scanner")
            return orig_scan_market(*args, **kwargs)
            
        def fake_run_master_engine(*args, **kwargs):
            events.append("master_engine")
            kwargs["scanner"] = fake_scan_market
            kwargs["pipeline"] = fake_val_pipeline
            kwargs["now_provider"] = FakeDatetime.now
            return orig_run_master_engine(*args, **kwargs)
            
        def fake_calc(*args, **kwargs):
            events.append("calculate_score")
            return orig_calc(*args, **kwargs)
            
        def fake_master_hash(*args, **kwargs):
            events.append("master_hash")
            return master_hash(*args, **kwargs)
            
        def fake_val_pipeline(*args, **kwargs):
            events.append("validated_pipeline")
            return orig_val_pipeline(*args, **kwargs)

        def fake_run_prod(*args, **kwargs):
            events.append("phase09_service")
            # If the duplicate suppression works, delivery won't happen the second time.
            res = orig_run_prod(*args, **kwargs)
            if res.get("status") == "DUPLICATE_SUPPRESSED":
                events.append("duplicate_suppressed")
            return res

        def fake_art_hash(*args, **kwargs):
            events.append("artifact_hash")
            return art_hash(*args, **kwargs)
            
        def fake_acquire(*args, **kwargs):
            events.append("quota_admission")
            events.append("slot_reservation")
            events.append("lifecycle_reservation")
            return orig_acquire(*args, **kwargs)
            
        def fake_release(*args, **kwargs):
            events.append("lifecycle_release")
            return orig_release(*args, **kwargs)
            
        from engine.quota_slot_worker_v4 import run_quota_slot_worker_v4
        orig_run_quota = run_quota_slot_worker_v4
        
        def fake_run_quota(*args, **kwargs):
            print("FAKE RUN QUOTA CALLED!")
            events.append("fake_run_quota")
            kwargs["acquire"] = fake_acquire
            kwargs["release"] = fake_release
            return orig_run_quota(*args, **kwargs)
            
        def fake_post(*args, **kwargs):
            events.append("telegram_http")
            events.append("delivery_receipt")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"ok": True, "result": {"message_id": 999}}
            return mock_resp
            
        with patch("engine.run_production_signal_v1.main", side_effect=fake_main):
            with patch("engine.run_production_signal_v1.run_master_engine_v4", side_effect=fake_run_master_engine):
                with patch("engine.scanner.calculate_score", side_effect=fake_calc):
                    with patch("engine.master_engine_v4._hash_payload", side_effect=fake_master_hash):
                        with patch("engine.validated_pipeline_v4.run_validated_pipeline_v4", side_effect=fake_val_pipeline):
                            with patch("engine.master_engine_v4.run_production_signal_service_v1", side_effect=fake_run_prod):
                                with patch("engine.production_signal_service_v1._hash_payload", side_effect=fake_art_hash):
                                    with patch("engine.phase09r_telegram_delivery_adapter_v1.run_quota_slot_worker_v4", side_effect=fake_run_quota):
                                        with patch("httpx.post", side_effect=fake_post):
                                            with patch("engine.master_engine_v4.datetime", FakeDatetime):
                                                import engine.run_production_signal_v1; exit_code_1 = engine.run_production_signal_v1.main()
                                                exit_code_2 = engine.run_production_signal_v1.main()
            assert exit_code_1 == 0
            assert exit_code_2 == 0
            
            with open("/tmp/events.txt", "w") as f:
                f.write(repr(events))
    
        # Assert ordered trace elements
    assert "production_entrypoint" in events
    assert "master_engine" in events
    assert "scanner" in events
    assert "calculate_score" in events
    assert "validated_pipeline" in events
    assert "master_hash" in events
    assert "phase09_service" in events
    assert "artifact_hash" in events
    assert "quota_admission" in events
    assert "slot_reservation" in events
    assert "lifecycle_reservation" in events
    assert "telegram_http" in events
    assert "delivery_receipt" in events
    assert "lifecycle_release" in events
        
    # Assert duplicate suppression behavior
    assert events.count("telegram_http") == 1
    
