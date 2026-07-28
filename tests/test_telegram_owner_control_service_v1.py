"""Mock-update contracts for owner-only lifecycle commands."""

from engine import active_signal_ledger_v1 as active
from engine.telegram_owner_control_service_v1 import (
    COMMAND_ALREADY_PROCESSED, COMMAND_REJECTED_AMBIGUOUS,
    COMMAND_REJECTED_UNAUTHORIZED, ENTRY_ACCEPTED, POSITION_CLOSED,
    SIGNAL_REJECTED_BY_OWNER, STATUS_REPORT, process_owner_update,
)
from engine.telegram_owner_control_state_v1 import bind_signal_message, initialize_state


NOW = "2026-07-28T00:00:00Z"
OWNER = "100"
CHAT = "200"


def _update(number, text, *, user=OWNER, chat=CHAT, reply=None):
    message = {
        "message_id": number + 1000, "from": {"id": int(user)},
        "chat": {"id": int(chat)}, "text": text,
    }
    if reply is not None:
        message["reply_to_message"] = {"message_id": reply}
    return {"update_id": number, "message": message}


def _pending(path, ledger, *, suffix, pair="SOL/USDT", style=active.SWING):
    return active.reserve_published_signal(
        path, expected_revision=ledger["ledger_revision"],
        transaction_id=f"tx-{suffix}", transition_id=f"reserve-{suffix}",
        signal_id=f"signal-{suffix}", delivery_id=f"delivery-{suffix}",
        mode=style, symbol=pair, published_at=NOW, source_payload_hash="a" * 64,
        publication_payload_hash="b" * 64, updated_at=NOW,
    )


def _paths(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    state_path = tmp_path / "control.json"
    ledger = active.initialize_ledger(ledger_path, created_at=NOW)
    initialize_state(state_path, timestamp=NOW)
    return ledger_path, state_path, ledger


def _process(update, ledger_path, state_path):
    return process_owner_update(
        update, owner_user_id=OWNER, owner_chat_id=CHAT, ledger_path=ledger_path,
        control_state_path=state_path, timestamp=NOW,
    )


def test_reply_bound_entry_duplicate_update_and_close(tmp_path):
    ledger_path, state_path, ledger = _paths(tmp_path)
    ledger = _pending(ledger_path, ledger, suffix="one")
    bind_signal_message(
        state_path, signal_id="signal-one", canonical_pair="SOL/USDT", style="SWING",
        telegram_chat_id=CHAT, telegram_message_id=50, timestamp=NOW,
    )
    accepted = _process(_update(1, "entry SOL/USDT", reply=50), ledger_path, state_path)
    assert accepted.outcome == ENTRY_ACCEPTED and accepted.slot_change == -1
    assert accepted.acknowledgement.startswith("Entry accepted")
    revision = active.load_ledger(ledger_path)["ledger_revision"]
    duplicate = _process(_update(1, "entry SOL/USDT", reply=50), ledger_path, state_path)
    assert duplicate.outcome == COMMAND_ALREADY_PROCESSED
    assert active.load_ledger(ledger_path)["ledger_revision"] == revision
    closed = _process(_update(2, "close sol/usdt"), ledger_path, state_path)
    assert closed.outcome == POSITION_CLOSED and closed.slot_change == 1
    assert closed.acknowledgement.startswith("Position closed")
    assert active.inspect_capacity(active.load_ledger(ledger_path))["total_active"] == 0


def test_owner_rejection_and_status_mutate_capacity_zero(tmp_path):
    ledger_path, state_path, ledger = _paths(tmp_path)
    ledger = _pending(ledger_path, ledger, suffix="one")
    rejected = _process(_update(3, "tidak entry SOL/USDT"), ledger_path, state_path)
    assert rejected.outcome == SIGNAL_REJECTED_BY_OWNER and rejected.slot_change == 0
    assert active.inspect_capacity(active.load_ledger(ledger_path))["total_active"] == 0
    revision = active.load_ledger(ledger_path)["ledger_revision"]
    status = _process(_update(4, "/status"), ledger_path, state_path)
    assert status.outcome == STATUS_REPORT and not status.ledger_mutated
    assert active.load_ledger(ledger_path)["ledger_revision"] == revision


def test_ambiguous_and_unauthorized_commands_mutate_no_ledger(tmp_path):
    ledger_path, state_path, ledger = _paths(tmp_path)
    ledger = _pending(ledger_path, ledger, suffix="one")
    ledger = _pending(ledger_path, ledger, suffix="two", style=active.INTRADAY)
    before = ledger_path.read_bytes()
    ambiguous = _process(_update(5, "entry SOL/USDT"), ledger_path, state_path)
    assert ambiguous.outcome == COMMAND_REJECTED_AMBIGUOUS
    assert ledger_path.read_bytes() == before
    unauthorized = _process(
        _update(6, "entry SOL/USDT", user="999"), ledger_path, state_path,
    )
    assert unauthorized.outcome == COMMAND_REJECTED_UNAUTHORIZED
    assert ledger_path.read_bytes() == before
