"""Mock-only tests for bounded update polling."""

from engine import active_signal_ledger_v1 as active
from engine.telegram_owner_control_state_v1 import initialize_state, load_state
from engine.telegram_owner_polling_v1 import poll_once


NOW = "2026-07-28T00:00:00Z"


def test_poll_once_uses_persisted_offset_and_injected_adapters(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    state_path = tmp_path / "state.json"
    active.initialize_ledger(ledger_path, created_at=NOW)
    initialize_state(state_path, timestamp=NOW)
    calls = []

    def fetch(offset):
        calls.append(("fetch", offset))
        return [{"update_id": 0, "message": {
            "message_id": 10, "from": {"id": 100}, "chat": {"id": 200},
            "text": "/status",
        }}]

    results = poll_once(
        fetch_updates=fetch,
        send_acknowledgement=lambda update, text: calls.append(("ack", update["update_id"], text)),
        owner_user_id="100", owner_chat_id="200", ledger_path=ledger_path,
        control_state_path=state_path, timestamp=NOW,
    )
    assert results[0]["outcome"] == "STATUS_REPORT"
    assert calls == [("fetch", 0), ("ack", 0, "STATUS_REPORT")]
    assert load_state(state_path)["last_update_id"] == 0
