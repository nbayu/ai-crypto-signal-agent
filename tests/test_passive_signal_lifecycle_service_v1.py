"""Focused contracts for owner-entry occupancy and terminal lifecycle."""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine import passive_terminal_refill_integration_v1 as terminal_integration
from engine import style_refill_request_ledger_v1 as refill


NOW = "2026-07-21T00:00:00Z"
ENTRY_AT = "2026-07-21T00:01:00Z"
TERMINAL_AT = "2026-07-21T00:02:00Z"
NOW_LATER = "2026-07-21T00:03:00Z"
HASH_A = "a" * 64
HASH_B = "b" * 64
_REFILL_MAP = "req" "uests"


def _paths(tmp_path, suffix="one"):
    return tmp_path / f"active-{suffix}.json", tmp_path / f"refill-{suffix}.json"


def _reserve(path, *, mode=active.SWING, suffix="one"):
    active.initialize_ledger(path, created_at=NOW)
    return active.reserve_published_signal(
        path, expected_revision=0, transaction_id=f"transaction-{suffix}",
        transition_id=f"reserve-{suffix}", signal_id=f"signal-{suffix}",
        delivery_id=f"delivery-{suffix}", mode=mode, symbol="BTCUSDT",
        published_at=NOW, source_payload_hash=HASH_A,
        publication_payload_hash=HASH_B, updated_at=NOW,
    )


def _activate(path, ledger, suffix="one"):
    return lifecycle.activate_signal_entry(
        active_ledger_path=path, expected_active_ledger_revision=ledger["ledger_revision"],
        entry_transition_id=f"entry-{suffix}", signal_id=f"signal-{suffix}",
        entry_at=ENTRY_AT, timestamp=ENTRY_AT,
    )


def _terminate(path, refill_path, ledger, *, suffix="one", terminal=active.CLOSED_PROFIT, refill_revision=None):
    return lifecycle.terminate_signal_and_reconcile_refill(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=ledger["ledger_revision"],
        expected_refill_ledger_revision=refill_revision,
        terminal_transition_id=f"terminal-{suffix}", signal_id=f"signal-{suffix}",
        terminal_state=terminal, terminal_at=TERMINAL_AT,
        terminal_reason="OBSERVED", timestamp=NOW_LATER,
    )


def test_pending_signal_activates_with_complete_result_schema(tmp_path):
    path, _ = _paths(tmp_path)
    reserved = _reserve(path)
    result = _activate(path, reserved)
    assert result.result == lifecycle.ENTRY_ACTIVATED
    assert result.entry_applied and not result.terminal_applied
    assert result.current_state == active.ENTRY_ACTIVE
    assert result.active_ledger_revision == reserved["ledger_revision"] + 1
    assert tuple(result.to_dict()) == (
        "result", "operation", "signal_id", "mode", "previous_state", "current_state",
        "entry_transition_id", "terminal_transition_id", "active_ledger_revision",
        "refill_request_id", "refill_ledger_revision", "entry_applied",
        "terminal_applied", "refill_reconciled", "partial_success", "replay",
        "reason", "timestamp",
    )


@pytest.mark.parametrize("mode", active.STYLES)
def test_entry_preserves_all_modes_and_transition_identity(tmp_path, mode):
    path, _ = _paths(tmp_path, mode)
    reserved = _reserve(path, mode=mode, suffix=mode)
    result = _activate(path, reserved, mode)
    document = active.load_ledger(path)
    assert result.mode == mode and result.entry_transition_id == f"entry-{mode}"
    assert document["transitions"][f"entry-{mode}"]["operation"] == "ENTRY"


def test_equivalent_entry_replay_is_non_mutating(tmp_path):
    path, _ = _paths(tmp_path)
    reserved = _reserve(path)
    first = _activate(path, reserved)
    replay = _activate(path, active.load_ledger(path))
    assert replay.result == lifecycle.ENTRY_REPLAYED
    assert replay.replay and not replay.entry_applied
    assert replay.active_ledger_revision == first.active_ledger_revision
    assert len(active.load_ledger(path)["transitions"]) == 2


def test_distinct_entry_id_already_active_terminal_missing_and_stale_fail_closed(tmp_path):
    path, _ = _paths(tmp_path)
    reserved = _reserve(path)
    _activate(path, reserved)
    active_doc = active.load_ledger(path)
    distinct = lifecycle.activate_signal_entry(
        active_ledger_path=path, expected_active_ledger_revision=active_doc["ledger_revision"],
        entry_transition_id="entry-other", signal_id="signal-one", entry_at=ENTRY_AT, timestamp=ENTRY_AT,
    )
    missing = lifecycle.activate_signal_entry(
        active_ledger_path=path, expected_active_ledger_revision=active_doc["ledger_revision"],
        entry_transition_id="entry-missing", signal_id="missing", entry_at=ENTRY_AT, timestamp=ENTRY_AT,
    )
    stale = lifecycle.activate_signal_entry(
        active_ledger_path=path, expected_active_ledger_revision=0,
        entry_transition_id="entry-stale", signal_id="signal-one", entry_at=ENTRY_AT, timestamp=ENTRY_AT,
    )
    assert distinct.result == lifecycle.INVALID_STATE_TRANSITION
    assert missing.result == lifecycle.NO_SIGNAL
    assert stale.result == lifecycle.ACTIVE_REVISION_CONFLICT


def test_entry_request_against_terminal_is_invalid(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    _terminate(path, refill_path, reserved)
    result = lifecycle.activate_signal_entry(
        active_ledger_path=path, expected_active_ledger_revision=active.load_ledger(path)["ledger_revision"],
        entry_transition_id="entry-after-terminal", signal_id="signal-one", entry_at=ENTRY_AT, timestamp=NOW_LATER,
    )
    assert result.result == lifecycle.INVALID_STATE_TRANSITION


def test_entry_lock_and_atomic_failures_are_sanitized(tmp_path, monkeypatch):
    path, _ = _paths(tmp_path)
    reserved = _reserve(path)

    @contextmanager
    def unavailable(_):
        raise active.ActiveSignalLedgerError(active.LOCK_ACQUISITION_FAILED)
        yield

    monkeypatch.setattr(active, "_ledger_lock", unavailable)
    locked = _activate(path, reserved)
    monkeypatch.undo()
    monkeypatch.setattr(active, "_atomic_write", lambda *_: (_ for _ in ()).throw(OSError()))
    atomic = _activate(path, reserved)
    assert locked.reason == lifecycle.ACTIVE_LOCK_UNAVAILABLE
    assert atomic.reason == lifecycle.ACTIVE_PERSISTENCE_FAILURE


@pytest.mark.parametrize("terminal", tuple(
    state for state in active.TERMINAL_STATES
    if state not in {active.CLOSED_MANUAL, active.REJECTED_BY_OWNER}
))
def test_terminal_delegation_supports_all_terminal_states(tmp_path, terminal):
    path, refill_path = _paths(tmp_path, terminal)
    reserved = _reserve(path, suffix=terminal)
    result = _terminate(path, refill_path, reserved, suffix=terminal, terminal=terminal)
    assert result.result == lifecycle.TERMINAL_AND_REFILL_RECONCILED
    assert result.current_state == terminal and result.refill_reconciled


@pytest.mark.parametrize("mode", active.STYLES)
def test_terminal_delegation_preserves_persisted_mode(tmp_path, mode):
    path, refill_path = _paths(tmp_path, mode)
    reserved = _reserve(path, mode=mode, suffix=mode)
    assert _terminate(path, refill_path, reserved, suffix=mode).mode == mode


def test_terminal_replay_and_revision_conflicts_are_preserved(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    first = _terminate(path, refill_path, reserved)
    replay = _terminate(path, refill_path, active.load_ledger(path), refill_revision=first.refill_ledger_revision)
    stale_active = _terminate(path, refill_path, reserved, suffix="stale")
    assert replay.result == lifecycle.REFILL_ALREADY_RECONCILED
    assert replay.replay and len(refill.load_refill_ledger(refill_path)[_REFILL_MAP]) == 1
    assert stale_active.result == lifecycle.ACTIVE_REVISION_CONFLICT


def test_terminal_partial_success_and_refill_revision_conflict_map_unchanged(tmp_path, monkeypatch):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    monkeypatch.setattr(
        lifecycle.terminal_integration, "transition_and_reconcile_refill",
        lambda **_: terminal_integration.PassiveTerminalRefillResultV1(
            result=terminal_integration.TRANSITION_APPLIED_REFILL_PENDING,
            terminal_transition_id="terminal-one", signal_id="signal-one", mode=active.SWING,
            terminal_state=active.CLOSED_PROFIT, active_ledger_revision=2,
            refill_request_id="a" * 64, refill_ledger_revision=None,
            transition_applied=True, refill_reconciled=False, partial_success=True,
            replay=False, reason=terminal_integration.REFILL_PERSISTENCE_FAILURE, timestamp=NOW_LATER,
        ),
    )
    partial = _terminate(path, refill_path, reserved)
    assert partial.result == lifecycle.TERMINAL_APPLIED_REFILL_PENDING
    assert partial.partial_success and not partial.refill_reconciled


def test_restart_repair_creates_once_and_preserves_active_document(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    terminal = active.transition_terminal(
        path, expected_revision=reserved["ledger_revision"], transition_id="terminal-one",
        signal_id="signal-one", terminal_state=active.CLOSED_PROFIT,
        terminal_at=TERMINAL_AT, terminal_reason="OBSERVED", updated_at=NOW_LATER,
    )
    repaired = lifecycle.reconcile_terminal_refill_after_restart(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"], expected_refill_ledger_revision=None,
        terminal_transition_id="terminal-one", timestamp=NOW_LATER,
    )
    replay = lifecycle.reconcile_terminal_refill_after_restart(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"],
        expected_refill_ledger_revision=repaired.refill_ledger_revision,
        terminal_transition_id="terminal-one", timestamp=NOW_LATER,
    )
    assert repaired.result == lifecycle.TERMINAL_AND_REFILL_RECONCILED
    assert replay.result == lifecycle.REFILL_ALREADY_RECONCILED
    assert active.load_ledger(path) == terminal


def test_restart_repair_preserves_refill_revision_conflict(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    terminal = active.transition_terminal(
        path, expected_revision=reserved["ledger_revision"], transition_id="terminal-one",
        signal_id="signal-one", terminal_state=active.CLOSED_PROFIT,
        terminal_at=TERMINAL_AT, terminal_reason="OBSERVED", updated_at=NOW_LATER,
    )
    refill.reconcile_terminal_transition(
        refill_path, terminal_transition_id="other-terminal", signal_id="other-signal",
        mode=active.SWING, terminal_state=active.CLOSED_PROFIT,
        source_ledger_revision=1, timestamp=NOW_LATER,
    )
    result = lifecycle.reconcile_terminal_refill_after_restart(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"], expected_refill_ledger_revision=0,
        terminal_transition_id="terminal-one", timestamp=NOW_LATER,
    )
    assert result.result == lifecycle.REFILL_REVISION_CONFLICT


def test_pure_inspection_covers_pending_entry_and_terminal_relationships(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    pending = lifecycle.inspect_signal_lifecycle(
        active_ledger=reserved, signal_id="signal-one", timestamp=NOW,
    )
    entered = _activate(path, reserved)
    entry = lifecycle.inspect_signal_lifecycle(
        active_ledger=active.load_ledger(path), signal_id="signal-one",
        entry_transition_id="entry-one", timestamp=NOW_LATER,
    )
    terminal_result = _terminate(path, refill_path, active.load_ledger(path))
    active_snapshot = active.load_ledger(path)
    pending_refill = lifecycle.inspect_signal_lifecycle(
        active_ledger=active_snapshot, signal_id="signal-one",
        terminal_transition_id="terminal-one", refill_ledger=refill.load_refill_ledger(refill_path), timestamp=NOW_LATER,
    )
    before = json.dumps(active_snapshot, sort_keys=True)
    assert pending.result == lifecycle.PUBLISHED_ENTRY_INSPECTED
    assert entry.result == lifecycle.ENTRY_ALREADY_ACTIVE and entered.entry_applied
    assert pending_refill.result == lifecycle.REFILL_ALREADY_RECONCILED
    assert json.dumps(active_snapshot, sort_keys=True) == before and terminal_result.refill_reconciled


def test_pure_inspection_reports_terminal_refill_pending_without_mutation(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    terminal = active.transition_terminal(
        path, expected_revision=reserved["ledger_revision"], transition_id="terminal-one",
        signal_id="signal-one", terminal_state=active.CLOSED_PROFIT,
        terminal_at=TERMINAL_AT, terminal_reason="OBSERVED", updated_at=NOW_LATER,
    )
    empty = refill.load_refill_ledger(refill_path, created_at=NOW_LATER)
    result = lifecycle.inspect_signal_lifecycle(
        active_ledger=terminal, signal_id="signal-one", terminal_transition_id="terminal-one",
        refill_ledger=empty, timestamp=NOW_LATER,
    )
    assert result.result == lifecycle.TERMINAL_APPLIED_REFILL_PENDING
    assert result.partial_success and not result.refill_reconciled


def test_inspection_rejects_malformed_state_without_mutation(tmp_path):
    path, _ = _paths(tmp_path)
    reserved = _reserve(path)
    malformed = copy.deepcopy(reserved)
    malformed["signals"]["signal-one"]["state"] = "BROKEN"
    result = lifecycle.inspect_signal_lifecycle(active_ledger=malformed, signal_id="signal-one", timestamp=NOW)
    assert result.result == lifecycle.FAIL_CLOSED


def test_failure_reasons_are_fixed_and_do_not_expose_exception_material(tmp_path, monkeypatch):
    path, _ = _paths(tmp_path)
    reserved = _reserve(path)
    monkeypatch.setattr(active, "_atomic_write", lambda *_: (_ for _ in ()).throw(OSError("/private/path")))
    result = _activate(path, reserved)
    assert result.reason == lifecycle.ACTIVE_PERSISTENCE_FAILURE
    assert "/" not in result.reason and "OSError" not in result.reason


def test_static_passive_boundaries_are_explicit():
    source = (Path(__file__).parents[1] / "engine" / "passive_signal_lifecycle_service_v1.py").read_text(encoding="utf-8")
    forbidden = (
        "telegram", "scanner", "master_engine", "quota_slot_worker", "stateful_worker",
        "scheduler", "evaluate_refill_dispatch(", "claim_eligible_refill(",
        "claim_refill_request(", "requests.", "httpx.", "urllib.", "socket.",
        "systemd", "subprocess", "str(exc)", "repr(exc)", "BaseException",
    )
    assert all(value not in source for value in forbidden)
