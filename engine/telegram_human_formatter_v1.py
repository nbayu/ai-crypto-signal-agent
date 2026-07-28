"""Deterministic human-readable Telegram presentation over canonical artifacts."""

from __future__ import annotations

from typing import Any, Mapping

from engine.canonical_pair_v1 import normalize_pair


_ACKNOWLEDGEMENTS = {
    "ENTRY_ACCEPTED": "Entry accepted. The position now occupies one active slot.",
    "ENTRY_REJECTED": "Entry rejected. No slot or pair lock was changed.",
    "SIGNAL_REJECTED_BY_OWNER": "Signal rejected by owner. No active slot was consumed.",
    "POSITION_CLOSED": "Position closed. Its active slot and pair lock were released.",
    "COMMAND_REJECTED_UNAUTHORIZED": "Command rejected: this user or chat is not authorized.",
    "COMMAND_REJECTED_AMBIGUOUS": "Command rejected: reply to the signal or specify one unique pair.",
    "COMMAND_ALREADY_PROCESSED": "Command already processed. No state was changed again.",
    # Kept as the stable heading consumed by the polling seam; status detail may follow it.
    "STATUS_REPORT": "STATUS_REPORT",
    "COMMAND_REJECTED_INVALID": "Command rejected: invalid command or pair.",
}


def format_acknowledgement(outcome: str) -> str:
    """Render one stable owner-facing lifecycle acknowledgement."""
    try:
        return _ACKNOWLEDGEMENTS[outcome]
    except KeyError as exc:
        raise ValueError("ACKNOWLEDGEMENT_OUTCOME_INVALID") from exc


def format_signal_message(payload: Mapping[str, Any], *, available_slots: int) -> str:
    """Render a signal without changing or serializing its canonical payload."""
    if not isinstance(payload, Mapping) or type(available_slots) is not int or not 0 <= available_slots <= 3:
        raise ValueError("SIGNAL_FORMAT_INPUT_INVALID")
    required = {
        "signal_id", "mode", "symbol", "side", "entry_zone", "stop_loss",
        "take_profit", "valid_until", "strategy_version", "source_evaluation_id",
    }
    if set(payload) != required:
        raise ValueError("SIGNAL_FORMAT_INPUT_INVALID")
    entry = payload["entry_zone"]
    take_profit = payload["take_profit"]
    if not isinstance(entry, Mapping) or not isinstance(take_profit, Mapping):
        raise ValueError("SIGNAL_FORMAT_INPUT_INVALID")
    pair = normalize_pair(payload["symbol"])
    style = str(payload["mode"])
    signal_id = str(payload["signal_id"])
    abbreviated_id = signal_id[:12] + "..." if len(signal_id) > 12 else signal_id
    return "\n".join((
        "AI CRYPTO SIGNAL",
        "",
        f"Style: {style}",
        f"Pair: {pair}",
        f"Direction: {payload['side']}",
        "",
        "Entry Zone:",
        f"{entry['min']} - {entry['max']}",
        "",
        "Stop Loss:",
        str(payload["stop_loss"]),
        "",
        "Take Profit:",
        f"TP1: {take_profit['tp1']}",
        f"TP2: {take_profit.get('tp2', take_profit['tp1'])}",
        "",
        "Valid Until:",
        str(payload["valid_until"]),
        "",
        f"Available {style} Slots:",
        f"{available_slots} / 3",
        "",
        "Reply:",
        f"entry {pair}",
        f"tidak entry {pair}",
        "",
        "Signal ID:",
        abbreviated_id,
    ))
