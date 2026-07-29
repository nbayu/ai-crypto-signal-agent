"""Mock-only tests for bounded update polling."""

import pytest

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
    assert results[0]["response_required"] is True
    assert calls == [("fetch", 0), ("ack", 0, "STATUS_REPORT")]
    assert load_state(state_path)["last_update_id"] == 0


def test_poll_once_suppresses_duplicate_invalid_and_unauthorized_responses(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    state_path = tmp_path / "state.json"
    active.initialize_ledger(ledger_path, created_at=NOW)
    initialize_state(state_path, timestamp=NOW)
    ledger_before = ledger_path.read_bytes()
    acknowledgements = []
    invalid = {"update_id": 70, "message": {
        "message_id": 1070, "from": {"id": 100}, "chat": {"id": 200},
        "text": "unsupported",
    }}
    unauthorized = {"update_id": 71, "message": {
        "message_id": 1071, "from": {"id": 999}, "chat": {"id": 200},
        "text": "/status",
    }}

    first = poll_once(
        fetch_updates=lambda offset: [invalid, unauthorized],
        send_acknowledgement=lambda update, text: acknowledgements.append(
            (update["update_id"], text)
        ),
        owner_user_id="100", owner_chat_id="200", ledger_path=ledger_path,
        control_state_path=state_path, timestamp=NOW,
    )
    replay = poll_once(
        fetch_updates=lambda offset: [invalid, unauthorized],
        send_acknowledgement=lambda update, text: acknowledgements.append(
            (update["update_id"], text)
        ),
        owner_user_id="100", owner_chat_id="200", ledger_path=ledger_path,
        control_state_path=state_path, timestamp=NOW,
    )

    assert [result["response_required"] for result in first] == [True, True]
    assert [result["response_required"] for result in replay] == [False, False]
    assert [item[0] for item in acknowledgements] == [70, 71]
    assert load_state(state_path)["last_update_id"] == 71
    assert ledger_path.read_bytes() == ledger_before


def test_poll_once_send_failure_persists_cursor_and_restart_suppresses_retry(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    state_path = tmp_path / "state.json"
    active.initialize_ledger(ledger_path, created_at=NOW)
    initialize_state(state_path, timestamp=NOW)
    update = {"update_id": 80, "message": {
        "message_id": 1080, "from": {"id": 100}, "chat": {"id": 200},
        "text": "unsupported",
    }}
    attempts = []

    def fail_send(_update, _text):
        attempts.append("attempt")
        raise RuntimeError("fixture flood control failure")

    with pytest.raises(RuntimeError, match="flood control"):
        poll_once(
            fetch_updates=lambda offset: [update],
            send_acknowledgement=fail_send,
            owner_user_id="100", owner_chat_id="200", ledger_path=ledger_path,
            control_state_path=state_path, timestamp=NOW,
        )
    assert attempts == ["attempt"]
    assert load_state(state_path)["last_update_id"] == 80

    results = poll_once(
        fetch_updates=lambda offset: [update],
        send_acknowledgement=fail_send,
        owner_user_id="100", owner_chat_id="200", ledger_path=ledger_path,
        control_state_path=state_path, timestamp=NOW,
    )
    assert attempts == ["attempt"]
    assert results[0]["response_required"] is False
    assert load_state(state_path)["last_update_id"] + 1 == 81
