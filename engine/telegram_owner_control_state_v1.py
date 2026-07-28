"""Atomic local state for Telegram owner-control idempotency and bindings."""

from __future__ import annotations

import copy
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping


SCHEMA_NAME = "telegram-owner-control-state"
SCHEMA_VERSION = 1


def create_empty_state(timestamp: str) -> dict[str, Any]:
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "updated_at": timestamp,
        "last_update_id": -1,
        "processed_updates": {},
        "processed_commands": {},
        "signal_message_bindings": {},
    }


def validate_state(value: Mapping[str, Any]) -> dict[str, Any]:
    state = copy.deepcopy(dict(value))
    required = {
        "schema_name", "schema_version", "revision", "updated_at", "last_update_id",
        "processed_updates", "processed_commands", "signal_message_bindings",
    }
    if set(state) != required or state["schema_name"] != SCHEMA_NAME or state["schema_version"] != 1:
        raise ValueError("OWNER_CONTROL_STATE_INVALID")
    if type(state["revision"]) is not int or type(state["last_update_id"]) is not int:
        raise ValueError("OWNER_CONTROL_STATE_INVALID")
    if not isinstance(state["updated_at"], str) or not all(
        isinstance(state[key], dict)
        for key in ("processed_updates", "processed_commands", "signal_message_bindings")
    ):
        raise ValueError("OWNER_CONTROL_STATE_INVALID")
    return state


def _payload(state: Mapping[str, Any]) -> bytes:
    return json.dumps(validate_state(state), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"


def _atomic_write(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_payload(state))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("OWNER_CONTROL_LOCK_UNAVAILABLE") from exc
        yield


def initialize_state(path: str | Path, *, timestamp: str) -> dict[str, Any]:
    target = Path(path)
    with _locked(target):
        if target.exists():
            raise FileExistsError(target)
        state = create_empty_state(timestamp)
        _atomic_write(target, state)
        return state


def load_state(path: str | Path) -> dict[str, Any]:
    return validate_state(json.loads(Path(path).read_text(encoding="utf-8")))


def mutate_state(
    path: str | Path, *, timestamp: str,
    mutation: Callable[[dict[str, Any]], tuple[dict[str, Any], Any]],
) -> Any:
    """Hold one nonblocking lock across resolution, ledger transition, and state write."""
    target = Path(path)
    with _locked(target):
        state = load_state(target)
        changed, result = mutation(copy.deepcopy(state))
        changed = validate_state(changed)
        if changed != state:
            changed["revision"] = state["revision"] + 1
            changed["updated_at"] = timestamp
            _atomic_write(target, changed)
        return result


def bind_signal_message(
    path: str | Path, *, signal_id: str, canonical_pair: str, style: str,
    telegram_chat_id: str, telegram_message_id: int, timestamp: str,
) -> dict[str, Any]:
    key = f"{telegram_chat_id}:{telegram_message_id}"

    def apply(state: dict[str, Any]):
        binding = {
            "signal_id": signal_id, "canonical_pair": canonical_pair, "style": style,
            "telegram_chat_id": telegram_chat_id,
            "telegram_message_id": telegram_message_id,
        }
        existing = state["signal_message_bindings"].get(key)
        if existing is not None and existing != binding:
            raise ValueError("SIGNAL_MESSAGE_BINDING_COLLISION")
        state["signal_message_bindings"][key] = binding
        return state, binding

    return mutate_state(path, timestamp=timestamp, mutation=apply)
