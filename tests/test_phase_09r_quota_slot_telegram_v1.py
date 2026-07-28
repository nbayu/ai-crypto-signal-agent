import pytest
import json
from unittest.mock import patch, MagicMock
from engine.telegram_runtime_v4 import TelegramRuntimeConfig
from engine.phase09r_telegram_delivery_adapter_v1 import Phase09RTelegramDeliveryAdapterV1
from engine.quota_slot_engine_v4 import QuotaSlotRejected


def _payload():
    return {
        "signal_id": "PSG-" + "a" * 64, "mode": "SWING", "symbol": "BTCUSDT",
        "side": "LONG", "entry_zone": {"min": 100.0, "max": 101.0},
        "stop_loss": 95.0, "take_profit": {"tp1": 110.0, "tp2": 120.0},
        "valid_until": "2026-07-29T00:00:00Z", "strategy_version": "v4",
        "source_evaluation_id": "evaluation-one",
    }

@pytest.fixture
def config(tmp_path):
    return TelegramRuntimeConfig(
        bot_token="test_token",
        bot_username=None,
        quota_limit=1,
        slot_capacity=1,
        window_id="w1",
        quota_state_path=str(tmp_path / "q.json"),
        worker_state_path=str(tmp_path / "w.json"),
        max_response_chars=4000
    )

def test_telegram_network_faked_successful(config):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 12345}}
        mock_post.return_value = mock_resp

        result = adapter(_payload(), "TELEGRAM", "dest1")
        assert result["external_delivery_id"] == "12345"
        mock_post.assert_called_once()
        assert "bottest_token" in mock_post.call_args[0][0]
        assert mock_post.call_args[1]["json"]["chat_id"] == "dest1"
        assert mock_post.call_args[1]["json"]["text"].startswith("AI CRYPTO SIGNAL")
        assert not mock_post.call_args[1]["json"]["text"].startswith("{")

def test_telegram_network_faked_malformed(config):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {}} # missing message_id
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="Malformed receipt"):
            adapter(_payload(), "TELEGRAM", "dest1")
        assert adapter.malformed_receipt is True

def test_telegram_network_faked_failure(config):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False}
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="Telegram delivery failed"):
            adapter(_payload(), "TELEGRAM", "dest1")

def test_quota_denial_makes_zero_telegram_calls(config):
    config = TelegramRuntimeConfig(
        bot_token="test_token", bot_username=None, quota_limit=1, slot_capacity=1,
        window_id="w1", quota_state_path=config.quota_state_path, worker_state_path=config.worker_state_path,
        max_response_chars=4000
    )
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_post.return_value = mock_resp

        # First call succeeds and consumes the quota
        adapter(_payload(), "TELEGRAM", "dest1")
        assert mock_post.call_count == 1

        # Second call fails quota
        with pytest.raises(QuotaSlotRejected):
            adapter(_payload(), "TELEGRAM", "dest1")

        # Call count is still 1
        assert mock_post.call_count == 1
        assert adapter.rejection_reason == "QUOTA_EXHAUSTED"
