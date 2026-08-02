import pytest
import json
from unittest.mock import patch, MagicMock
from engine.telegram_runtime_v4 import TelegramRuntimeConfig
from engine.phase09r_telegram_delivery_adapter_v1 import (
    E6TelegramDeliveryRequestV1,
    Phase09RTelegramDeliveryAdapterV1,
)
from test_e6_integrated_orchestrator_v1 import _run, _scenario


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

def test_static_operational_quota_does_not_gate_autonomous_delivery(config):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_post.return_value = mock_resp

        adapter(_payload(), "TELEGRAM", "dest1")
        adapter(_payload(), "TELEGRAM", "dest1")
        assert mock_post.call_count == 2
        assert adapter.rejection_reason is None
        assert not (config.quota_state_path and __import__("pathlib").Path(config.quota_state_path).exists())


def test_e6_delivery_uses_exact_rendered_message_and_typed_identity(config, tmp_path):
    orchestrator = _run(_scenario(tmp_path, name="adapter-e6"))
    request = E6TelegramDeliveryRequestV1(
        rendered_message=orchestrator.rendered_message,
        publication_eligibility=orchestrator.publication_eligibility,
        publication_envelope=orchestrator.publication_envelope,
        owner_lifecycle_binding=orchestrator.owner_lifecycle_binding,
        delivery_id=orchestrator.owner_lifecycle_binding.binding.delivery_id,
    )
    attempts = []

    def post(url, *, json, timeout):
        attempts.append((url, json, timeout))
        response = MagicMock()
        response.json.return_value = {"ok": True, "result": {"message_id": 808}}
        return response

    adapter = Phase09RTelegramDeliveryAdapterV1(config, http_post=post)
    receipt = adapter(request, "TELEGRAM", "isolated-owner-state-test")

    assert receipt["external_delivery_id"] == "808"
    assert len(attempts) == 1
    assert attempts[0][1]["text"] == orchestrator.rendered_message
    assert "Manual owner confirmation is required before ENTRY_ACTIVE." in attempts[0][1]["text"]
    assert attempts[0][1]["text"] != json.dumps(
        orchestrator.publication_envelope.to_mapping(), sort_keys=True
    )
