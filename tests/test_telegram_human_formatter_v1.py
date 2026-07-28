"""Presentation-only contracts preserving canonical signal identity."""

import copy
import json

from engine.telegram_human_formatter_v1 import format_acknowledgement, format_signal_message


def _payload():
    return {
        "signal_id": "PSG-3b9b9190" + "a" * 56, "mode": "SWING",
        "symbol": "ena/usdt:usdt", "side": "LONG",
        "entry_zone": {"min": 0.08554582, "max": 0.08674366},
        "stop_loss": 0.08402,
        "take_profit": {"tp1": 0.0930751, "tp2": 0.0930751},
        "valid_until": "2026-07-29T00:00:00Z", "strategy_version": "v4",
        "source_evaluation_id": "evaluation-one",
    }


def test_signal_is_human_readable_and_canonical_payload_bytes_are_preserved():
    payload = _payload()
    canonical_before = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    snapshot = copy.deepcopy(payload)
    message = format_signal_message(payload, available_slots=3)
    assert not message.lstrip().startswith("{")
    for value in (
        "AI CRYPTO SIGNAL", "Style: SWING", "Pair: ENA/USDT", "Direction: LONG",
        "Entry Zone:", "Stop Loss:", "Take Profit:", "Valid Until:",
        "Available SWING Slots:", "3 / 3", "entry ENA/USDT",
        "tidak entry ENA/USDT", "PSG-3b9b9190...",
    ):
        assert value in message
    assert payload == snapshot
    assert json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() == canonical_before
    assert payload["signal_id"] == snapshot["signal_id"]


def test_all_required_acknowledgements_are_human_readable():
    outcomes = (
        "ENTRY_ACCEPTED", "ENTRY_REJECTED", "SIGNAL_REJECTED_BY_OWNER",
        "POSITION_CLOSED", "COMMAND_REJECTED_UNAUTHORIZED",
        "COMMAND_REJECTED_AMBIGUOUS", "COMMAND_ALREADY_PROCESSED", "STATUS_REPORT",
    )
    rendered = {outcome: format_acknowledgement(outcome) for outcome in outcomes}
    assert all(isinstance(text, str) and text for text in rendered.values())
    assert rendered["ENTRY_ACCEPTED"].startswith("Entry accepted")
    assert rendered["POSITION_CLOSED"].startswith("Position closed")
