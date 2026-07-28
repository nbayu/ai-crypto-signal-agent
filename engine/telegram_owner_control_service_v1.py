"""Owner-authorized Telegram command resolution with no order-execution path."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as active
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine.canonical_pair_v1 import CanonicalPairError, normalize_pair
from engine import telegram_owner_control_state_v1 as control_state


ENTRY_ACCEPTED = "ENTRY_ACCEPTED"
SIGNAL_REJECTED_BY_OWNER = "SIGNAL_REJECTED_BY_OWNER"
POSITION_CLOSED = "POSITION_CLOSED"
STATUS_REPORT = "STATUS_REPORT"
COMMAND_REJECTED_UNAUTHORIZED = "COMMAND_REJECTED_UNAUTHORIZED"
COMMAND_REJECTED_AMBIGUOUS = "COMMAND_REJECTED_AMBIGUOUS"
COMMAND_ALREADY_PROCESSED = "COMMAND_ALREADY_PROCESSED"
COMMAND_REJECTED_INVALID = "COMMAND_REJECTED_INVALID"


@dataclass(frozen=True, slots=True)
class OwnerCommandResultV1:
    outcome: str
    command_id: str | None
    update_id: int | None
    signal_id: str | None
    canonical_pair: str | None
    style: str | None
    ledger_mutated: bool
    slot_change: int
    pair_lock_change: int
    acknowledgement: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _result(outcome: str, *, update_id=None, command_id=None, record=None, mutated=False, slot=0, pair=0):
    return OwnerCommandResultV1(
        outcome=outcome, command_id=command_id, update_id=update_id,
        signal_id=record.get("signal_id") if isinstance(record, Mapping) else None,
        canonical_pair=normalize_pair(record["symbol"]) if isinstance(record, Mapping) else None,
        style=record.get("mode") if isinstance(record, Mapping) else None,
        ledger_mutated=mutated, slot_change=slot, pair_lock_change=pair,
        acknowledgement=outcome,
    )


def _message(update: Mapping[str, Any]) -> tuple[int, str, str, str, int | None]:
    update_id = update.get("update_id")
    message = update.get("message")
    if type(update_id) is not int or not isinstance(message, Mapping):
        raise ValueError
    user = message.get("from")
    chat = message.get("chat")
    text = message.get("text")
    if not isinstance(user, Mapping) or not isinstance(chat, Mapping) or not isinstance(text, str):
        raise ValueError
    reply = message.get("reply_to_message")
    reply_id = reply.get("message_id") if isinstance(reply, Mapping) else None
    if reply_id is not None and type(reply_id) is not int:
        raise ValueError
    return update_id, str(user.get("id")), str(chat.get("id")), text.strip(), reply_id


def _parse(text: str) -> tuple[str, str | None]:
    folded = " ".join(text.casefold().split())
    if folded == "/status":
        return "STATUS", None
    for prefix, command in (("tidak entry ", "REJECT"), ("entry ", "ENTRY"), ("close ", "CLOSE")):
        if folded.startswith(prefix):
            pair_text = text.strip()[len(prefix):].strip()
            return command, normalize_pair(pair_text)
    raise ValueError


def _command_id(update_id: int, user_id: str, chat_id: str, text: str) -> str:
    raw = f"{update_id}\0{user_id}\0{chat_id}\0{text}".encode()
    return hashlib.sha256(raw).hexdigest()


def _resolve(
    state: Mapping[str, Any], ledger: Mapping[str, Any], *, command: str,
    pair: str | None, chat_id: str, reply_message_id: int | None,
) -> Mapping[str, Any] | None:
    expected = {"ENTRY": active.PUBLISHED_PENDING_ENTRY, "REJECT": active.PUBLISHED_PENDING_ENTRY, "CLOSE": active.ENTRY_ACTIVE}[command]
    if reply_message_id is not None:
        binding = state["signal_message_bindings"].get(f"{chat_id}:{reply_message_id}")
        record = ledger["signals"].get(binding.get("signal_id")) if isinstance(binding, Mapping) else None
        if isinstance(record, Mapping) and record.get("state") == expected:
            if pair is None or normalize_pair(record["symbol"]) == pair:
                return record
        return None
    matches = [
        record for record in ledger["signals"].values()
        if record["state"] == expected and normalize_pair(record["symbol"]) == pair
    ]
    return matches[0] if len(matches) == 1 else None


def process_owner_update(
    update: Mapping[str, Any], *, owner_user_id: str, owner_chat_id: str,
    ledger_path: str | Path, control_state_path: str | Path, timestamp: str,
) -> OwnerCommandResultV1:
    """Process one injected update; authorization precedes every state mutation."""
    try:
        update_id, user_id, chat_id, text, reply_id = _message(update)
    except (TypeError, ValueError):
        return _result(COMMAND_REJECTED_INVALID)
    if user_id != str(owner_user_id) or chat_id != str(owner_chat_id):
        return _result(COMMAND_REJECTED_UNAUTHORIZED, update_id=update_id)
    command_id = _command_id(update_id, user_id, chat_id, text)
    try:
        command, pair = _parse(text)
    except (CanonicalPairError, ValueError):
        return _result(COMMAND_REJECTED_INVALID, update_id=update_id, command_id=command_id)

    def apply(state: dict[str, Any]):
        if str(update_id) in state["processed_updates"] or command_id in state["processed_commands"]:
            return state, _result(COMMAND_ALREADY_PROCESSED, update_id=update_id, command_id=command_id)
        ledger = active.load_ledger(ledger_path)
        record = None
        outcome = STATUS_REPORT
        changed = ledger
        slot_change = pair_change = 0
        if command != "STATUS":
            record = _resolve(
                state, ledger, command=command, pair=pair, chat_id=chat_id,
                reply_message_id=reply_id,
            )
            if record is None:
                outcome = COMMAND_REJECTED_AMBIGUOUS
            elif command == "ENTRY":
                changed = lifecycle.commit_owner_confirmed_entry(
                    ledger_path=ledger_path, expected_revision=ledger["ledger_revision"],
                    transition_id=f"owner-entry-{command_id}", signal_id=record["signal_id"],
                    timestamp=timestamp,
                )
                outcome, slot_change, pair_change = ENTRY_ACCEPTED, -1, 1
            elif command == "REJECT":
                changed = lifecycle.commit_owner_terminal(
                    ledger_path=ledger_path, expected_revision=ledger["ledger_revision"],
                    transition_id=f"owner-reject-{command_id}", signal_id=record["signal_id"],
                    terminal_state=active.REJECTED_BY_OWNER, timestamp=timestamp,
                    reason="OWNER_REJECTION",
                )
                outcome = SIGNAL_REJECTED_BY_OWNER
            else:
                changed = lifecycle.commit_owner_terminal(
                    ledger_path=ledger_path, expected_revision=ledger["ledger_revision"],
                    transition_id=f"owner-close-{command_id}", signal_id=record["signal_id"],
                    terminal_state=active.CLOSED_MANUAL, timestamp=timestamp,
                    reason="OWNER_CONFIRMED_CLOSE",
                )
                outcome, slot_change, pair_change = POSITION_CLOSED, 1, -1
        state["processed_updates"][str(update_id)] = command_id
        state["processed_commands"][command_id] = {"outcome": outcome, "processed_at": timestamp}
        state["last_update_id"] = max(state["last_update_id"], update_id)
        result_record = changed["signals"].get(record["signal_id"]) if record is not None else None
        return state, _result(
            outcome, update_id=update_id, command_id=command_id, record=result_record,
            mutated=changed["ledger_revision"] != ledger["ledger_revision"],
            slot=slot_change, pair=pair_change,
        )

    try:
        return control_state.mutate_state(control_state_path, timestamp=timestamp, mutation=apply)
    except Exception:
        return _result(COMMAND_REJECTED_INVALID, update_id=update_id, command_id=command_id)
