"""Mock-update contracts for owner-only lifecycle commands."""

import hashlib

import pytest

from engine import active_signal_ledger_v1 as active
from engine import telegram_owner_control_service_v1 as service
from engine.telegram_owner_control_service_v1 import (
    COMMAND_ALREADY_PROCESSED, COMMAND_REJECTED_AMBIGUOUS,
    COMMAND_REJECTED_INVALID, COMMAND_REJECTED_UNAUTHORIZED, ENTRY_ACCEPTED,
    POSITION_CLOSED, SIGNAL_REJECTED_BY_OWNER, STATUS_REPORT,
    process_owner_update, record_response_success,
)
from engine.telegram_owner_control_state_v1 import (
    bind_signal_message,
    initialize_state,
    load_state,
)


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
    assert accepted.response_required is True
    assert accepted.acknowledgement.startswith("Entry accepted")
    revision = active.load_ledger(ledger_path)["ledger_revision"]
    duplicate = _process(_update(1, "entry SOL/USDT", reply=50), ledger_path, state_path)
    assert duplicate.outcome == COMMAND_ALREADY_PROCESSED
    assert duplicate.response_required is False
    assert duplicate.ledger_mutated is False
    assert duplicate.slot_change == 0 and duplicate.pair_lock_change == 0
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
    assert unauthorized.response_required is True
    assert ledger_path.read_bytes() == before


def test_invalid_and_unauthorized_updates_persist_once_and_advance_cursor(tmp_path):
    ledger_path, state_path, _ledger = _paths(tmp_path)
    ledger_before = ledger_path.read_bytes()
    malformed = {"update_id": 10, "message": {"from": {"id": 100}}}

    first_invalid = _process(malformed, ledger_path, state_path)
    replay_invalid = _process(malformed, ledger_path, state_path)
    first_unauthorized = _process(
        _update(11, "/status", user="999"), ledger_path, state_path,
    )
    replay_unauthorized = _process(
        _update(11, "/status", user="999"), ledger_path, state_path,
    )

    assert first_invalid.outcome == COMMAND_REJECTED_INVALID
    assert first_invalid.response_required is True
    assert replay_invalid.outcome == COMMAND_ALREADY_PROCESSED
    assert replay_invalid.response_required is False
    assert first_unauthorized.outcome == COMMAND_REJECTED_UNAUTHORIZED
    assert first_unauthorized.response_required is True
    assert replay_unauthorized.outcome == COMMAND_ALREADY_PROCESSED
    assert replay_unauthorized.response_required is False
    state = load_state(state_path)
    assert state["last_update_id"] == 11
    assert set(state["processed_updates"]) == {"10", "11"}
    assert ledger_path.read_bytes() == ledger_before


def test_out_of_order_distinct_updates_remain_sendable_and_cursor_is_monotonic(tmp_path):
    ledger_path, state_path, _ledger = _paths(tmp_path)

    newer = _process(_update(20, "/status"), ledger_path, state_path)
    historical = _process(_update(15, "unsupported"), ledger_path, state_path)

    assert newer.response_required is True
    assert historical.response_required is True
    assert load_state(state_path)["last_update_id"] == 20
    assert load_state(state_path)["last_update_id"] + 1 == 21


@pytest.mark.parametrize("update_id", [None, "12", True])
def test_missing_or_noninteger_update_id_fails_closed_without_state_change(
    tmp_path, update_id,
):
    ledger_path, state_path, _ledger = _paths(tmp_path)
    before = state_path.read_bytes()
    update = _update(12, "/status")
    if update_id is None:
        update.pop("update_id")
    else:
        update["update_id"] = update_id

    result = _process(update, ledger_path, state_path)

    assert result.outcome == COMMAND_REJECTED_INVALID
    assert result.response_required is False
    assert result.update_id is None
    assert state_path.read_bytes() == before


def test_state_write_failure_fails_closed_without_sendable_response(
    tmp_path, monkeypatch,
):
    ledger_path, state_path, _ledger = _paths(tmp_path)
    before = state_path.read_bytes()

    def fail_state_write(*_args, **_kwargs):
        raise OSError("fixture state write failure")

    monkeypatch.setattr(service.control_state, "mutate_state", fail_state_write)
    result = _process(_update(30, "invalid"), ledger_path, state_path)

    assert result.outcome == COMMAND_REJECTED_INVALID
    assert result.response_required is False
    assert state_path.read_bytes() == before


def test_handler_failure_becomes_durable_fail_closed_decision(tmp_path, monkeypatch):
    ledger_path, state_path, _ledger = _paths(tmp_path)

    def fail_ledger_load(_path):
        raise OSError("fixture handler failure")

    monkeypatch.setattr(service.active, "load_ledger", fail_ledger_load)
    first = _process(_update(31, "/status"), ledger_path, state_path)
    replay = _process(_update(31, "/status"), ledger_path, state_path)

    assert first.outcome == COMMAND_REJECTED_INVALID
    assert first.response_required is True
    assert replay.outcome == COMMAND_ALREADY_PROCESSED
    assert replay.response_required is False
    assert load_state(state_path)["last_update_id"] == 31


def test_response_receipt_is_nonsecret_bound_and_idempotent(tmp_path):
    ledger_path, state_path, _ledger = _paths(tmp_path)
    result = _process(_update(40, "invalid"), ledger_path, state_path)
    expected_key = hashlib.sha256(
        f"40\0{COMMAND_REJECTED_INVALID}".encode()
    ).hexdigest()
    assert result.response_idempotency_key == expected_key

    record_response_success(
        state_path, update_id=40, outcome=result.outcome,
        response_message_id=4000, timestamp=NOW,
    )
    record_response_success(
        state_path, update_id=40, outcome=result.outcome,
        response_message_id=4000, timestamp=NOW,
    )

    decision = load_state(state_path)["processed_updates"]["40"]
    assert decision["response_idempotency_key"] == expected_key
    assert decision["response_message_id"] == 4000
    assert set(decision) == {
        "command_id", "outcome", "processed_at", "response_idempotency_key",
        "response_message_id", "response_sent_at",
    }
    with pytest.raises(ValueError, match="RECEIPT_COLLISION"):
        record_response_success(
            state_path, update_id=40, outcome=result.outcome,
            response_message_id=4001, timestamp=NOW,
        )
