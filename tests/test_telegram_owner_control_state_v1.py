"""Offline persistence contracts for owner-control idempotency state."""

import pytest

from engine.telegram_owner_control_state_v1 import (
    bind_signal_message, initialize_state, load_state,
)


NOW = "2026-07-28T00:00:00Z"


def test_signal_message_binding_is_durable_and_idempotent(tmp_path):
    path = tmp_path / "owner-control.json"
    initialize_state(path, timestamp=NOW)
    binding = bind_signal_message(
        path, signal_id="PSG-one", canonical_pair="SOL/USDT", style="SWING",
        telegram_chat_id="200", telegram_message_id=50, timestamp=NOW,
    )
    revision = load_state(path)["revision"]
    assert binding["signal_id"] == "PSG-one"
    assert bind_signal_message(
        path, signal_id="PSG-one", canonical_pair="SOL/USDT", style="SWING",
        telegram_chat_id="200", telegram_message_id=50, timestamp=NOW,
    ) == binding
    assert load_state(path)["revision"] == revision


def test_binding_collision_fails_closed(tmp_path):
    path = tmp_path / "owner-control.json"
    initialize_state(path, timestamp=NOW)
    bind_signal_message(
        path, signal_id="one", canonical_pair="SOL/USDT", style="SWING",
        telegram_chat_id="200", telegram_message_id=50, timestamp=NOW,
    )
    with pytest.raises(ValueError, match="SIGNAL_MESSAGE_BINDING_COLLISION"):
        bind_signal_message(
            path, signal_id="two", canonical_pair="ETH/USDT", style="SCALP",
            telegram_chat_id="200", telegram_message_id=50, timestamp=NOW,
        )
