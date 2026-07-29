"""Injectable Telegram update polling; imports and tests perform no network I/O."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from engine.telegram_owner_control_service_v1 import process_owner_update
from engine.telegram_owner_control_state_v1 import load_state


def poll_once(
    *, fetch_updates: Callable[[int], list[Mapping[str, Any]]],
    send_acknowledgement: Callable[[Mapping[str, Any], str], None],
    owner_user_id: str, owner_chat_id: str, ledger_path: str | Path,
    control_state_path: str | Path, timestamp: str,
) -> list[dict[str, Any]]:
    """Fetch and process one bounded batch through injected adapters."""
    offset = load_state(control_state_path)["last_update_id"] + 1
    results = []
    for update in fetch_updates(offset):
        outcome = process_owner_update(
            update, owner_user_id=owner_user_id, owner_chat_id=owner_chat_id,
            ledger_path=ledger_path, control_state_path=control_state_path,
            timestamp=timestamp,
        )
        if outcome.response_required:
            send_acknowledgement(update, outcome.acknowledgement)
        results.append(outcome.to_dict())
    return results
