"""Fixture-only tests for active-signal ledger v2 migration."""

from __future__ import annotations

import json

import pytest

from engine import active_signal_ledger_v1 as active
from engine.active_signal_ledger_migration_v2 import (
    DUPLICATE_ACTIVE_CANONICAL_PAIR,
    migrate_document,
    migrate_path,
)


NOW = "2026-07-28T00:00:00Z"


def _v1_document():
    document = active.create_empty_ledger(NOW)
    document["schema_version"] = 1
    document["capacity_policy"]["occupying_states"] = [
        active.PUBLISHED_PENDING_ENTRY, active.ENTRY_ACTIVE,
    ]
    document["capacity_policy"]["terminal_states"] = [
        state for state in active.TERMINAL_STATES
        if state not in {active.CLOSED_MANUAL, active.REJECTED_BY_OWNER}
    ]
    return document


def test_dry_run_is_non_mutating_and_idempotent(tmp_path):
    path = tmp_path / "ledger.json"
    source = _v1_document()
    path.write_text(json.dumps(source), encoding="utf-8")
    before = path.read_bytes()
    result = migrate_path(path, backup_directory=tmp_path / "backups", timestamp="20260728T000000Z")
    assert result["dry_run"] is True
    assert path.read_bytes() == before
    migrated = migrate_document(source)
    assert migrate_document(migrated) == migrated
    assert migrated["capacity_policy"]["occupying_states"] == [active.ENTRY_ACTIVE]


def test_duplicate_active_canonical_pair_fails_closed():
    source = _v1_document()
    template = {
        "delivery_id": "delivery", "mode": active.SWING, "symbol": "sol/usdt",
        "state": active.ENTRY_ACTIVE, "published_at": NOW, "entry_at": NOW,
        "terminal_at": None, "terminal_reason": None, "last_transition_id": "entry",
        "source_payload_hash": "a" * 64, "publication_payload_hash": "b" * 64,
        "created_at": NOW, "updated_at": NOW,
    }
    first = {**template, "signal_id": "one"}
    second = {**template, "signal_id": "two", "delivery_id": "delivery-two", "symbol": "SOL/USDT:USDT", "last_transition_id": "entry-two"}
    source["signals"] = {"one": first, "two": second}
    with pytest.raises(ValueError, match=DUPLICATE_ACTIVE_CANONICAL_PAIR):
        migrate_document(source)
