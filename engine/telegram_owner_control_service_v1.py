"""Owner-authorized Telegram command resolution with no order-execution path."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as active
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine.canonical_pair_v1 import CanonicalPairError, normalize_pair
from engine import telegram_owner_control_state_v1 as control_state
from engine.telegram_human_formatter_v1 import format_acknowledgement


ENTRY_ACCEPTED = "ENTRY_ACCEPTED"
SIGNAL_REJECTED_BY_OWNER = "SIGNAL_REJECTED_BY_OWNER"
POSITION_CLOSED = "POSITION_CLOSED"
STATUS_REPORT = "STATUS_REPORT"
COMMAND_REJECTED_UNAUTHORIZED = "COMMAND_REJECTED_UNAUTHORIZED"
COMMAND_REJECTED_AMBIGUOUS = "COMMAND_REJECTED_AMBIGUOUS"
COMMAND_ALREADY_PROCESSED = "COMMAND_ALREADY_PROCESSED"
COMMAND_REJECTED_INVALID = "COMMAND_REJECTED_INVALID"

_LOGGER = logging.getLogger(__name__)


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
    response_required: bool
    response_idempotency_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _result(
    outcome: str, *, update_id=None, command_id=None, record=None,
    mutated=False, slot=0, pair=0, response_required=False,
):
    response_idempotency_key = (
        hashlib.sha256(f"{update_id}\0{outcome}".encode()).hexdigest()
        if type(update_id) is int else None
    )
    return OwnerCommandResultV1(
        outcome=outcome, command_id=command_id, update_id=update_id,
        signal_id=record.get("signal_id") if isinstance(record, Mapping) else None,
        canonical_pair=normalize_pair(record["symbol"]) if isinstance(record, Mapping) else None,
        style=record.get("mode") if isinstance(record, Mapping) else None,
        ledger_mutated=mutated, slot_change=slot, pair_lock_change=pair,
        acknowledgement=format_acknowledgement(outcome),
        response_required=response_required,
        response_idempotency_key=response_idempotency_key,
    )


def _message(update: Mapping[str, Any]) -> tuple[str, str, str, int | None]:
    message = update.get("message")
    if not isinstance(message, Mapping):
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
    return str(user.get("id")), str(chat.get("id")), text.strip(), reply_id


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


def _record_decision(
    state: dict[str, Any], *, result: OwnerCommandResultV1, timestamp: str,
) -> tuple[dict[str, Any], OwnerCommandResultV1]:
    update_id = result.update_id
    if type(update_id) is not int or not result.response_required:
        raise ValueError("OWNER_CONTROL_DECISION_INVALID")
    state["processed_updates"][str(update_id)] = {
        "command_id": result.command_id,
        "outcome": result.outcome,
        "processed_at": timestamp,
        "response_idempotency_key": result.response_idempotency_key,
    }
    if result.command_id is not None:
        state["processed_commands"][result.command_id] = {
            "outcome": result.outcome,
            "processed_at": timestamp,
        }
    state["last_update_id"] = max(state["last_update_id"], update_id)
    return state, result


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
    """Persist one terminal update decision before exposing a sendable response."""
    update_id = update.get("update_id") if isinstance(update, Mapping) else None
    if type(update_id) is not int:
        result = _result(COMMAND_REJECTED_INVALID)
        _LOGGER.info(
            "telegram_owner_update_decision",
            extra={
                "update_id": None,
                "outcome": result.outcome,
                "response_required": result.response_required,
            },
        )
        return result

    def apply(state: dict[str, Any]):
        existing = state["processed_updates"].get(str(update_id))
        if existing is not None:
            existing_command_id = (
                existing.get("command_id") if isinstance(existing, Mapping) else existing
            )
            return state, _result(
                COMMAND_ALREADY_PROCESSED,
                update_id=update_id,
                command_id=existing_command_id,
            )
        try:
            user_id, chat_id, text, reply_id = _message(update)
        except (TypeError, ValueError):
            return _record_decision(
                state,
                result=_result(
                    COMMAND_REJECTED_INVALID,
                    update_id=update_id,
                    response_required=True,
                ),
                timestamp=timestamp,
            )
        if user_id != str(owner_user_id) or chat_id != str(owner_chat_id):
            return _record_decision(
                state,
                result=_result(
                    COMMAND_REJECTED_UNAUTHORIZED,
                    update_id=update_id,
                    response_required=True,
                ),
                timestamp=timestamp,
            )
        command_id = _command_id(update_id, user_id, chat_id, text)
        try:
            command, pair = _parse(text)
        except (CanonicalPairError, ValueError):
            return _record_decision(
                state,
                result=_result(
                    COMMAND_REJECTED_INVALID,
                    update_id=update_id,
                    command_id=command_id,
                    response_required=True,
                ),
                timestamp=timestamp,
            )
        if command_id in state["processed_commands"]:
            return _record_decision(
                state,
                result=_result(
                    COMMAND_ALREADY_PROCESSED,
                    update_id=update_id,
                    command_id=command_id,
                    response_required=True,
                ),
                timestamp=timestamp,
            )
        try:
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
            result_record = changed["signals"].get(record["signal_id"]) if record is not None else None
            result = _result(
                outcome, update_id=update_id, command_id=command_id, record=result_record,
                mutated=changed["ledger_revision"] != ledger["ledger_revision"],
                slot=slot_change, pair=pair_change, response_required=True,
            )
        except Exception:
            result = _result(
                COMMAND_REJECTED_INVALID, update_id=update_id,
                command_id=command_id, response_required=True,
            )
        return _record_decision(
            state,
            result=result,
            timestamp=timestamp,
        )

    try:
        result = control_state.mutate_state(
            control_state_path, timestamp=timestamp, mutation=apply,
        )
    except Exception:
        result = _result(COMMAND_REJECTED_INVALID, update_id=update_id)
    _LOGGER.info(
        "telegram_owner_update_decision",
        extra={
            "update_id": result.update_id,
            "outcome": result.outcome,
            "response_required": result.response_required,
        },
    )
    return result


def record_response_success(
    control_state_path: str | Path, *, update_id: int, outcome: str,
    response_message_id: int, timestamp: str,
) -> None:
    """Attach a non-secret send receipt to an existing durable decision."""
    if type(update_id) is not int or type(response_message_id) is not int:
        raise ValueError("OWNER_CONTROL_RESPONSE_RECEIPT_INVALID")

    def apply(state: dict[str, Any]):
        decision = state["processed_updates"].get(str(update_id))
        if not isinstance(decision, Mapping):
            raise ValueError("OWNER_CONTROL_RESPONSE_DECISION_MISSING")
        expected_key = hashlib.sha256(f"{update_id}\0{outcome}".encode()).hexdigest()
        if (
            decision.get("outcome") != outcome
            or decision.get("response_idempotency_key") != expected_key
        ):
            raise ValueError("OWNER_CONTROL_RESPONSE_DECISION_MISMATCH")
        existing = decision.get("response_message_id")
        if existing is not None and existing != response_message_id:
            raise ValueError("OWNER_CONTROL_RESPONSE_RECEIPT_COLLISION")
        changed = dict(decision)
        changed["response_message_id"] = response_message_id
        changed["response_sent_at"] = timestamp
        state["processed_updates"][str(update_id)] = changed
        return state, None

    control_state.mutate_state(
        control_state_path, timestamp=timestamp, mutation=apply,
    )
