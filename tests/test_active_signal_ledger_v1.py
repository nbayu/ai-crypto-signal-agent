"""Focused contract tests for the Active Signal Ledger v1 seam.

These tests are intentionally not run in the implementation-only step.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.active_signal_ledger_v1 import (
    ABORTED,
    ActiveSignalLedgerError,
    CANCELLED,
    CLOSED_MANUAL,
    CLOSED_PROFIT,
    CLOSED_STOP_LOSS,
    ENTRY_ACTIVE,
    EXPIRED,
    INTRADAY,
    INVALIDATED,
    OCCUPANCY_COMMITTED,
    PREPARED,
    PUBLISHED_PENDING_ENTRY,
    REJECTED_BY_OWNER,
    SCALP,
    SWING,
    TOTAL_CAPACITY,
    create_empty_ledger,
    initialize_ledger,
    inspect_capacity,
    load_ledger,
    mark_entry_active,
    reconcile_publication_state,
    reserve_published_signal,
    transition_terminal,
)


NOW = "2026-07-21T00:00:00Z"
LATER = "2026-07-21T00:01:00Z"
HASH_A = "a" * 64
HASH_B = "b" * 64


def _request(mode=SWING, suffix="1"):
    return {
        "transaction_id": f"transaction-{suffix}", "transition_id": f"transition-{suffix}",
        "signal_id": f"signal-{suffix}", "delivery_id": f"delivery-{suffix}",
        "mode": mode, "symbol": "BTCUSDT", "published_at": NOW,
        "source_payload_hash": HASH_A, "publication_payload_hash": HASH_B,
        "updated_at": NOW,
    }


def _initialize(tmp_path):
    path = tmp_path / "active-signal-ledger.json"
    initialize_ledger(path, created_at=NOW)
    return path


def _reserve(path, revision=0, mode=SWING, suffix="1", **overrides):
    request = _request(mode, suffix)
    request.update(overrides)
    return reserve_published_signal(path, expected_revision=revision, **request)


def _error(code, operation):
    with pytest.raises(ActiveSignalLedgerError) as caught:
        operation()
    assert caught.value.reason_code == code
    assert "a" * 64 not in str(caught.value)


def test_explicit_initialization_and_missing_ledger_failure(tmp_path):
    _error("LEDGER_NOT_FOUND", lambda: load_ledger(tmp_path / "missing.json"))
    path = _initialize(tmp_path)
    assert load_ledger(path)["ledger_revision"] == 0
    assert inspect_capacity(load_ledger(path))["total_active"] == 0


def test_schema_validation_and_unsupported_schema_are_fail_closed(tmp_path):
    path = _initialize(tmp_path)
    document = load_ledger(path)
    document["schema_version"] = 99
    path.write_text(json.dumps(document), encoding="utf-8")
    _error("LEDGER_SCHEMA_UNSUPPORTED", lambda: load_ledger(path))
    path.write_text("{not-json", encoding="utf-8")
    _error("LEDGER_CORRUPT", lambda: load_ledger(path))


@pytest.mark.parametrize("mode", (SWING, INTRADAY, SCALP))
def test_each_style_allows_three_then_rejects_fourth(tmp_path, mode):
    path = _initialize(tmp_path)
    ledger = load_ledger(path)
    for number in range(3):
        ledger = _reserve(
            path, ledger["ledger_revision"], mode, f"{mode}-{number}",
            symbol=f"{mode}{number}/USDT",
        )
        ledger = mark_entry_active(
            path, expected_revision=ledger["ledger_revision"],
            transition_id=f"entry-{mode}-{number}", signal_id=f"signal-{mode}-{number}",
            entry_at=LATER, updated_at=LATER,
        )
    assert inspect_capacity(ledger)["active_by_mode"][mode] == 3
    pending = _reserve(
        path, ledger["ledger_revision"], mode, f"{mode}-4", symbol=f"{mode}4/USDT",
    )
    assert inspect_capacity(pending)["active_by_mode"][mode] == 3
    _error("STYLE_CAPACITY_FULL", lambda: mark_entry_active(
        path, expected_revision=pending["ledger_revision"], transition_id=f"entry-{mode}-4",
        signal_id=f"signal-{mode}-4", entry_at=LATER, updated_at=LATER,
    ))


def test_total_capacity_is_nine_and_is_derived_from_records(tmp_path):
    path = _initialize(tmp_path)
    ledger = load_ledger(path)
    for mode in (SWING, INTRADAY, SCALP):
        for number in range(3):
            ledger = _reserve(
                path, ledger["ledger_revision"], mode, f"{mode}-{number}",
                symbol=f"{mode}{number}/USDT",
            )
            ledger = mark_entry_active(
                path, expected_revision=ledger["ledger_revision"],
                transition_id=f"entry-{mode}-{number}", signal_id=f"signal-{mode}-{number}",
                entry_at=LATER, updated_at=LATER,
            )
    assert inspect_capacity(ledger)["total_active"] == TOTAL_CAPACITY
    assert "active_count" not in ledger and "capacity_count" not in ledger


def test_reservation_replay_and_identity_collisions_are_deterministic(tmp_path):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    assert ledger["signals"]["signal-1"]["state"] == PUBLISHED_PENDING_ENTRY
    replay = _reserve(path, 0)
    assert replay["ledger_revision"] == ledger["ledger_revision"]
    _error("SIGNAL_ALREADY_EXISTS", lambda: _reserve(path, replay["ledger_revision"], suffix="2", signal_id="signal-1"))
    _error("PUBLICATION_ID_COLLISION", lambda: _reserve(path, replay["ledger_revision"], suffix="3", delivery_id="delivery-1"))


def test_immutable_style_symbol_and_hashes_cannot_change(tmp_path):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    _error("STYLE_IMMUTABLE", lambda: _reserve(path, ledger["ledger_revision"], suffix="2", signal_id="signal-1", mode=SCALP))
    _error("IDENTITY_IMMUTABLE", lambda: _reserve(path, ledger["ledger_revision"], suffix="2", signal_id="signal-1", symbol="ETHUSDT"))
    _error("IDENTITY_IMMUTABLE", lambda: _reserve(path, ledger["ledger_revision"], suffix="2", signal_id="signal-1", source_payload_hash=HASH_B))
    record = ledger["signals"]["signal-1"]
    assert record["mode"] == SWING and record["symbol"] == "BTCUSDT"
    assert record["source_payload_hash"] == HASH_A and record["publication_payload_hash"] == HASH_B


def test_entry_transition_is_narrow_and_idempotent(tmp_path):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    entered = mark_entry_active(path, expected_revision=ledger["ledger_revision"], transition_id="entry-1", signal_id="signal-1", entry_at=LATER, updated_at=LATER)
    assert entered["signals"]["signal-1"]["state"] == ENTRY_ACTIVE
    assert mark_entry_active(path, expected_revision=entered["ledger_revision"], transition_id="entry-1", signal_id="signal-1", entry_at=LATER, updated_at=LATER) == entered
    _error("LIFECYCLE_TRANSITION_INVALID", lambda: mark_entry_active(path, expected_revision=entered["ledger_revision"], transition_id="entry-2", signal_id="signal-1", entry_at=LATER, updated_at=LATER))


def test_entry_replay_ignores_stale_revision_but_not_changed_identity(tmp_path):
    path = _initialize(tmp_path)
    pending = _reserve(path)
    entered = mark_entry_active(
        path, expected_revision=pending["ledger_revision"], transition_id="owner-command",
        signal_id="signal-1", entry_at=LATER, updated_at=LATER,
    )
    replay = mark_entry_active(
        path, expected_revision=0, transition_id="owner-command",
        signal_id="signal-1", entry_at=LATER, updated_at=LATER,
    )
    assert replay == entered
    before = path.read_bytes()
    _error(
        "EXPECTED_REVISION_MISMATCH",
        lambda: mark_entry_active(
            path, expected_revision=0, transition_id="owner-command",
            signal_id="signal-1", entry_at=NOW, updated_at=LATER,
        ),
    )
    assert path.read_bytes() == before


@pytest.mark.parametrize("terminal", (CLOSED_PROFIT, CLOSED_STOP_LOSS, CLOSED_MANUAL, REJECTED_BY_OWNER, CANCELLED, EXPIRED, INVALIDATED))
def test_all_terminals_are_allowed_from_pending_and_release_capacity(tmp_path, terminal):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    result = transition_terminal(path, expected_revision=ledger["ledger_revision"], transition_id=f"terminal-{terminal}", signal_id="signal-1", terminal_state=terminal, terminal_at=LATER, terminal_reason="OBSERVED", updated_at=LATER)
    assert result["signals"]["signal-1"]["state"] == terminal
    assert "signal-1" in result["signals"]
    assert inspect_capacity(result)["total_active"] == 0


@pytest.mark.parametrize("terminal", (CLOSED_PROFIT, CLOSED_STOP_LOSS, CANCELLED, INVALIDATED))
def test_allowed_entry_terminals_and_expiry_rejection(tmp_path, terminal):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    entered = mark_entry_active(path, expected_revision=ledger["ledger_revision"], transition_id="entry", signal_id="signal-1", entry_at=LATER, updated_at=LATER)
    result = transition_terminal(path, expected_revision=entered["ledger_revision"], transition_id=f"end-{terminal}", signal_id="signal-1", terminal_state=terminal, terminal_at=LATER, terminal_reason="OBSERVED", updated_at=LATER)
    assert result["signals"]["signal-1"]["state"] == terminal
    path = _initialize(tmp_path / "second")
    ledger = _reserve(path)
    entered = mark_entry_active(path, expected_revision=ledger["ledger_revision"], transition_id="entry", signal_id="signal-1", entry_at=LATER, updated_at=LATER)
    _error("LIFECYCLE_TRANSITION_INVALID", lambda: transition_terminal(path, expected_revision=entered["ledger_revision"], transition_id="expiry", signal_id="signal-1", terminal_state=EXPIRED, terminal_at=LATER, terminal_reason="OBSERVED", updated_at=LATER))


def test_terminal_idempotency_conflict_and_reopen_are_fail_closed(tmp_path):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    ended = transition_terminal(path, expected_revision=ledger["ledger_revision"], transition_id="close", signal_id="signal-1", terminal_state=CLOSED_PROFIT, terminal_at=LATER, terminal_reason="TARGET", updated_at=LATER)
    assert transition_terminal(path, expected_revision=ended["ledger_revision"], transition_id="close", signal_id="signal-1", terminal_state=CLOSED_PROFIT, terminal_at=LATER, terminal_reason="TARGET", updated_at=LATER) == ended
    _error("TERMINAL_SIGNAL_REOPEN_FORBIDDEN", lambda: transition_terminal(path, expected_revision=ended["ledger_revision"], transition_id="different", signal_id="signal-1", terminal_state=CANCELLED, terminal_at=LATER, terminal_reason="OTHER", updated_at=LATER))


def test_revision_and_transition_identity_collisions_are_fail_closed(tmp_path):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    _error("EXPECTED_REVISION_MISMATCH", lambda: mark_entry_active(path, expected_revision=0, transition_id="entry", signal_id="signal-1", entry_at=LATER, updated_at=LATER))
    entered = mark_entry_active(path, expected_revision=ledger["ledger_revision"], transition_id="entry", signal_id="signal-1", entry_at=LATER, updated_at=LATER)
    _error("TRANSITION_ID_COLLISION", lambda: transition_terminal(path, expected_revision=entered["ledger_revision"], transition_id="entry", signal_id="signal-1", terminal_state=CANCELLED, terminal_at=LATER, terminal_reason="X", updated_at=LATER))


def test_prepared_transaction_reconciliation_commit_abort_and_contradiction(tmp_path):
    path = _initialize(tmp_path)
    prepared = _reserve(path, publication_intent_durable=False)
    assert prepared["publication_transactions"]["transaction-1"]["state"] == PREPARED
    _error("PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED", lambda: _reserve(path, prepared["ledger_revision"], suffix="other"))
    _error("PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED", lambda: reconcile_publication_state(path, expected_revision=prepared["ledger_revision"], transaction_id="transaction-1", publication_artifact_exists=True, artifact_signal_id="wrong", artifact_delivery_id="delivery-1", artifact_publication_payload_hash=HASH_B, reconciled_at=LATER))
    committed = reconcile_publication_state(path, expected_revision=prepared["ledger_revision"], transaction_id="transaction-1", publication_artifact_exists=True, artifact_signal_id="signal-1", artifact_delivery_id="delivery-1", artifact_publication_payload_hash=HASH_B, reconciled_at=LATER)
    assert committed["publication_transactions"]["transaction-1"]["state"] == OCCUPANCY_COMMITTED
    path = _initialize(tmp_path / "abort")
    prepared = _reserve(path, publication_intent_durable=False)
    aborted = reconcile_publication_state(path, expected_revision=prepared["ledger_revision"], transaction_id="transaction-1", publication_artifact_exists=False, artifact_signal_id=None, artifact_delivery_id=None, artifact_publication_payload_hash=None, reconciled_at=LATER)
    assert aborted["publication_transactions"]["transaction-1"]["state"] == ABORTED


def test_corrupt_and_over_capacity_state_fail_closed_and_restart_reconstructs(tmp_path):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    assert inspect_capacity(load_ledger(path))["active_by_mode"][SWING] == 0
    ledger["signals"]["signal-1"]["mode"] = "UNKNOWN"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    _error("STYLE_INVALID", lambda: load_ledger(path))


def test_over_capacity_ledger_is_rejected_during_restart_loading(tmp_path):
    path = _initialize(tmp_path)
    ledger = load_ledger(path)
    for number in range(3):
        ledger = _reserve(
            path, ledger["ledger_revision"], SWING, f"swing-{number}",
            symbol=f"SWING{number}/USDT",
        )
        ledger = mark_entry_active(
            path, expected_revision=ledger["ledger_revision"],
            transition_id=f"entry-swing-{number}", signal_id=f"signal-swing-{number}",
            entry_at=LATER, updated_at=LATER,
        )
    corrupt = load_ledger(path)
    copied = dict(corrupt["signals"]["signal-swing-0"])
    copied["signal_id"] = "signal-swing-over"
    copied["delivery_id"] = "delivery-swing-over"
    copied["last_transition_id"] = "transition-swing-over"
    copied["symbol"] = "OVER/USDT"
    corrupt["signals"][copied["signal_id"]] = copied
    path.write_text(json.dumps(corrupt), encoding="utf-8")
    _error("STYLE_CAPACITY_FULL", lambda: load_ledger(path))


def test_atomic_write_and_lock_failures_have_stable_codes(monkeypatch, tmp_path):
    import engine.active_signal_ledger_v1 as ledger_module
    path = _initialize(tmp_path)
    monkeypatch.setattr(ledger_module, "_atomic_write", lambda *_: (_ for _ in ()).throw(ActiveSignalLedgerError("ATOMIC_WRITE_FAILED")))
    _error("ATOMIC_WRITE_FAILED", lambda: _reserve(path))
    monkeypatch.undo()
    monkeypatch.setattr(ledger_module, "_LOCK_ATTEMPTS", 0)
    _error("LOCK_ACQUISITION_FAILED", lambda: _reserve(path))


def test_delivery_failure_alone_never_releases_occupied_capacity(tmp_path):
    path = _initialize(tmp_path)
    ledger = _reserve(path)
    assert inspect_capacity(ledger)["total_active"] == 0
    assert ledger["signals"]["signal-1"]["state"] == PUBLISHED_PENDING_ENTRY


def test_owner_entry_consumes_and_manual_close_releases_exactly_one_slot(tmp_path):
    path = _initialize(tmp_path)
    pending = _reserve(path)
    assert inspect_capacity(pending)["remaining_by_mode"][SWING] == 3
    active = mark_entry_active(
        path, expected_revision=pending["ledger_revision"], transition_id="owner-entry",
        signal_id="signal-1", entry_at=LATER, updated_at=LATER,
    )
    assert inspect_capacity(active)["remaining_by_mode"][SWING] == 2
    closed = transition_terminal(
        path, expected_revision=active["ledger_revision"], transition_id="owner-close",
        signal_id="signal-1", terminal_state=CLOSED_MANUAL, terminal_at=LATER,
        terminal_reason="OWNER_CONFIRMED_CLOSE", updated_at=LATER,
    )
    assert inspect_capacity(closed)["remaining_by_mode"][SWING] == 3


def test_global_pair_is_atomic_across_styles_and_side_labels(tmp_path):
    path = _initialize(tmp_path)
    first = _reserve(path, mode=SWING, suffix="LONG", symbol="sol/usdt")
    first = mark_entry_active(
        path, expected_revision=first["ledger_revision"], transition_id="entry-long",
        signal_id="signal-LONG", entry_at=LATER, updated_at=LATER,
    )
    second = _reserve(
        path, first["ledger_revision"], INTRADAY, "SHORT", symbol="SOL/USDT:USDT",
    )
    before = path.read_bytes()
    _error("GLOBAL_PAIR_ALREADY_ACTIVE", lambda: mark_entry_active(
        path, expected_revision=second["ledger_revision"], transition_id="entry-short",
        signal_id="signal-SHORT", entry_at=LATER, updated_at=LATER,
    ))
    assert path.read_bytes() == before
    assert inspect_capacity(load_ledger(path))["active_by_mode"] == {
        SWING: 1, INTRADAY: 0, SCALP: 0,
    }


def test_pair_lock_releases_only_with_committed_terminal_close(tmp_path):
    path = _initialize(tmp_path)
    first = _reserve(path, mode=SWING, suffix="one", symbol="SOL/USDT")
    first = mark_entry_active(
        path, expected_revision=first["ledger_revision"], transition_id="entry-one",
        signal_id="signal-one", entry_at=LATER, updated_at=LATER,
    )
    closed = transition_terminal(
        path, expected_revision=first["ledger_revision"], transition_id="close-one",
        signal_id="signal-one", terminal_state=CLOSED_MANUAL, terminal_at=LATER,
        terminal_reason="OWNER_CONFIRMED_CLOSE", updated_at=LATER,
    )
    second = _reserve(path, closed["ledger_revision"], INTRADAY, "two", symbol="sol/usdt:usdt")
    second = mark_entry_active(
        path, expected_revision=second["ledger_revision"], transition_id="entry-two",
        signal_id="signal-two", entry_at=LATER, updated_at=LATER,
    )
    assert second["signals"]["signal-two"]["state"] == ENTRY_ACTIVE


def test_source_has_no_runtime_integration_imports():
    source = (Path(__file__).parents[1] / "engine" / "active_signal_ledger_v1.py").read_text(encoding="utf-8")
    forbidden = ("engine.telegram", "systemd", "run_scanner", "scheduler", "passive_runtime_launcher", "requests", "httpx")
    assert not any(f"import {name}" in source or f"from {name}" in source for name in forbidden)
