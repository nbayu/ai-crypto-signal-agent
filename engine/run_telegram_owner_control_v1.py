"""Runtime configuration seam for the separate Telegram owner-control service."""

from __future__ import annotations

import os
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class TelegramOwnerControlConfigV1:
    owner_user_id: str
    owner_chat_id: str
    ledger_path: Path
    state_path: Path
    token_file: Path


def load_owner_control_config(environment: Mapping[str, str]) -> TelegramOwnerControlConfigV1:
    credentials_directory = environment.get("CREDENTIALS_DIRECTORY")
    values = {
        "owner_user_id": environment.get("TELEGRAM_OWNER_USER_ID"),
        "owner_chat_id": environment.get("TELEGRAM_OWNER_CHAT_ID"),
        "ledger_path": environment.get("ACTIVE_SIGNAL_LEDGER_PATH"),
        "state_path": environment.get("TELEGRAM_OWNER_CONTROL_STATE_PATH"),
        "token_file": str(Path(credentials_directory) / "telegram_bot_token") if credentials_directory else None,
    }
    if not all(isinstance(value, str) and value.strip() for value in values.values()):
        raise ValueError("OWNER_CONTROL_CONFIGURATION_INVALID")
    return TelegramOwnerControlConfigV1(
        owner_user_id=values["owner_user_id"], owner_chat_id=values["owner_chat_id"],
        ledger_path=Path(values["ledger_path"]), state_path=Path(values["state_path"]),
        token_file=Path(values["token_file"]),
    )


async def run_forever(config: TelegramOwnerControlConfigV1, token: str) -> None:
    """Poll continuously; any transport failure escapes for systemd supervision."""
    from telegram import Bot
    from engine.telegram_owner_control_service_v1 import process_owner_update
    from engine.telegram_owner_control_state_v1 import load_state

    bot = Bot(token=token)
    while True:
        offset = load_state(config.state_path)["last_update_id"] + 1
        updates = await bot.get_updates(offset=offset, timeout=25)
        for update in updates:
            raw = update.to_dict()
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            result = process_owner_update(
                raw, owner_user_id=config.owner_user_id, owner_chat_id=config.owner_chat_id,
                ledger_path=config.ledger_path, control_state_path=config.state_path,
                timestamp=timestamp,
            )
            message = raw.get("message", {})
            await bot.send_message(
                chat_id=config.owner_chat_id, text=result.acknowledgement,
                reply_to_message_id=message.get("message_id"),
            )


def main(environment: Mapping[str, str] | None = None) -> int:
    """Validate startup inputs and run the dedicated owner-control poller."""
    try:
        config = load_owner_control_config(environment or os.environ)
        token = config.token_file.read_text(encoding="utf-8").strip()
        if not token:
            return 2
    except Exception:
        return 2
    asyncio.run(run_forever(config, token))
    return 0
