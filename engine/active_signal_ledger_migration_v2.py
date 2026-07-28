"""Offline, idempotent active-signal ledger v1-to-v2 migration.

The migration never selects between duplicate active canonical pairs. It fails
closed, preserves every historical record, and writes only when explicitly run
with ``dry_run=False`` against a caller-provided path.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as ledger_v2


MIGRATION_NAME = "active-signal-ledger-v1-to-v2"
DUPLICATE_ACTIVE_CANONICAL_PAIR = "DUPLICATE_ACTIVE_CANONICAL_PAIR"
UNSUPPORTED_LEDGER = "UNSUPPORTED_LEDGER"


def _canonical_pair(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(UNSUPPORTED_LEDGER)
    compact = re.sub(r"\s+", "", value).upper()
    if ":" in compact:
        compact, settlement = compact.split(":", 1)
        if not compact.endswith("/" + settlement):
            raise ValueError(UNSUPPORTED_LEDGER)
    if "/" not in compact and compact.endswith("USDT") and len(compact) > 4:
        compact = compact[:-4] + "/USDT"
    parts = compact.split("/")
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Z0-9]{2,20}", part) for part in parts):
        raise ValueError(UNSUPPORTED_LEDGER)
    return "/".join(parts)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def migrate_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return a v2 document or validate and copy an already migrated document."""
    source = json.loads(json.dumps(document))
    if source.get("schema_name") != ledger_v2.SCHEMA_NAME:
        raise ValueError(UNSUPPORTED_LEDGER)
    if source.get("schema_version") == ledger_v2.SCHEMA_VERSION:
        return ledger_v2.validate_ledger(source)
    if source.get("schema_version") != 1:
        raise ValueError(UNSUPPORTED_LEDGER)
    signals = source.get("signals")
    if not isinstance(signals, dict):
        raise ValueError(UNSUPPORTED_LEDGER)
    active_pairs: set[str] = set()
    for record in signals.values():
        if not isinstance(record, dict):
            raise ValueError(UNSUPPORTED_LEDGER)
        if record.get("state") == ledger_v2.ENTRY_ACTIVE:
            pair = _canonical_pair(record.get("symbol"))
            if pair in active_pairs:
                raise ValueError(DUPLICATE_ACTIVE_CANONICAL_PAIR)
            active_pairs.add(pair)
    source["schema_version"] = ledger_v2.SCHEMA_VERSION
    source["capacity_policy"] = {
        "scope": ledger_v2.CAPACITY_SCOPE,
        "by_mode": dict(ledger_v2.CAPACITY_BY_MODE),
        "total_capacity": ledger_v2.TOTAL_CAPACITY,
        "occupying_states": list(ledger_v2.OCCUPYING_STATES),
        "terminal_states": list(ledger_v2.TERMINAL_STATES),
    }
    return ledger_v2.validate_ledger(source)


def migrate_path(
    ledger_path: str | Path, *, backup_directory: str | Path,
    timestamp: str, dry_run: bool = True,
) -> dict[str, Any]:
    """Validate a migration and optionally commit it with backup metadata."""
    path = Path(ledger_path)
    before = path.read_bytes()
    document = json.loads(before.decode("utf-8"))
    migrated = migrate_document(document)
    after = json.dumps(migrated, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    result = {
        "migration": MIGRATION_NAME, "dry_run": bool(dry_run),
        "before_sha256": _sha256(before), "after_sha256": _sha256(after),
        "record_count": len(migrated["signals"]), "backup_path": None,
        "rollback_record_path": None,
    }
    if dry_run:
        return result
    backup_root = Path(backup_directory)
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / f"{path.name}.{timestamp}.bak"
    rollback_path = backup_root / f"{path.name}.{timestamp}.rollback.json"
    if backup_path.exists() or rollback_path.exists():
        raise FileExistsError("migration backup already exists")
    backup_path.write_bytes(before)
    os.chmod(backup_path, 0o400)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    rollback = {**result, "dry_run": False, "backup_path": str(backup_path)}
    rollback_path.write_text(json.dumps(rollback, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    result.update(backup_path=str(backup_path), rollback_record_path=str(rollback_path), dry_run=False)
    return result
