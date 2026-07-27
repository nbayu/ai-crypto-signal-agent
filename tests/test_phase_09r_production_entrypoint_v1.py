import os
import pytest
from unittest.mock import patch
from engine.run_production_signal_v1 import main

@pytest.fixture
def valid_env():
    return {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_DESTINATION_ID": "test_dest_id",
        "TELEGRAM_QUOTA_LIMIT": "10",
        "TELEGRAM_SLOT_CAPACITY": "5",
        "TELEGRAM_WINDOW_ID": "w1",
        "TELEGRAM_QUOTA_STATE_PATH": "tmp/q.json",
        "TELEGRAM_WORKER_STATE_PATH": "tmp/w.json",
        "TELEGRAM_MAX_MESSAGE_LENGTH": "4000",
    }

def test_missing_config_returns_2():
    with patch.dict(os.environ, {}, clear=True):
        assert main() == 2

def test_missing_destination_returns_2(valid_env):
    env = dict(valid_env)
    del env["TELEGRAM_DESTINATION_ID"]
    with patch.dict(os.environ, env, clear=True):
        assert main() == 2

@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_production_entrypoint_calls_master_engine_once(mock_run, valid_env):
    mock_run.return_value = {
        "production_signal_out": {
            "status": "OK",
            "publication": {"delivery_state": "DELIVERY_SUCCEEDED"}
        }
    }
    with patch.dict(os.environ, valid_env, clear=True):
        assert main() == 0
    mock_run.assert_called_once()
    assert mock_run.call_args[1]["enable_publication"] is True

@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_no_credentials_in_logs_and_returns_7_on_failure(mock_run, valid_env):
    mock_run.side_effect = Exception("General error")
    with patch.dict(os.environ, valid_env, clear=True):
        assert main() == 7

@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_quota_exhausted_returns_3(mock_run, valid_env):
    def fake_run(*args, **kwargs):
        adapter = kwargs["delivery_adapter"]
        adapter.rejection_reason = "QUOTA_EXHAUSTED"
        return {"production_signal_out": {"status": "OK", "publication": {"delivery_state": "DELIVERY_FAILED"}}}
    mock_run.side_effect = fake_run
    with patch.dict(os.environ, valid_env, clear=True):
        assert main() == 3

@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_slots_full_returns_4(mock_run, valid_env):
    def fake_run(*args, **kwargs):
        adapter = kwargs["delivery_adapter"]
        adapter.rejection_reason = "SLOTS_FULL"
        return {"production_signal_out": {"status": "OK", "publication": {"delivery_state": "DELIVERY_FAILED"}}}
    mock_run.side_effect = fake_run
    with patch.dict(os.environ, valid_env, clear=True):
        assert main() == 4

@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_delivery_failed_returns_5(mock_run, valid_env):
    def fake_run(*args, **kwargs):
        return {"production_signal_out": {"status": "OK", "publication": {"delivery_state": "DELIVERY_FAILED"}}}
    mock_run.side_effect = fake_run
    with patch.dict(os.environ, valid_env, clear=True):
        assert main() == 5

@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_malformed_receipt_returns_6(mock_run, valid_env):
    def fake_run(*args, **kwargs):
        adapter = kwargs["delivery_adapter"]
        adapter.malformed_receipt = True
        return {"production_signal_out": {"status": "OK", "publication": {"delivery_state": "DELIVERY_FAILED"}}}
    mock_run.side_effect = fake_run
    with patch.dict(os.environ, valid_env, clear=True):
        assert main() == 6
