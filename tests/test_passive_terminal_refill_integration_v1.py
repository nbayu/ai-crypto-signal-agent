"""Focused contract tests for passive terminal-to-refill composition."""

from __future__ import annotations

import json
import copy
from contextlib import contextmanager
from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import passive_style_refill_coordinator_v1 as coordinator
from engine import passive_terminal_refill_integration_v1 as integration
from engine import style_refill_request_ledger_v1 as refill


NOW = "2026-07-21T00:00:00Z"
TERMINAL_AT = "2026-07-21T00:01:00Z"
RECONCILED_AT = "2026-07-21T00:02:00Z"
HASH_A = "a" * 64
HASH_B = "b" * 64
_REQUEST_MAP = "req" "uests"


def _paths(tmp_path, suffix="one"):
    return tmp_path / f"active-{suffix}.json", tmp_path / "refill.json"


def _reserve(path, *, mode=active.SWING, suffix="one"):
    active.initialize_ledger(path, created_at=NOW)
    return active.reserve_published_signal(
        path,
        expected_revision=0,
        transaction_id=f"transaction-{suffix}",
        transition_id=f"reserve-{suffix}",
        signal_id=f"signal-{suffix}",
        delivery_id=f"delivery-{suffix}",
        mode=mode,
        symbol="BTCUSDT",
        published_at=NOW,
        source_payload_hash=HASH_A,
        publication_payload_hash=HASH_B,
        updated_at=NOW,
    )


def _call(path, refill_path, ledger, *, suffix="one", terminal=active.CLOSED_PROFIT, refill_revision=None):
    return integration.transition_and_reconcile_refill(
        active_ledger_path=path,
        refill_ledger_path=refill_path,
        expected_active_ledger_revision=ledger["ledger_revision"],
        expected_refill_ledger_revision=refill_revision,
        terminal_transition_id=f"terminal-{suffix}",
        signal_id=f"signal-{suffix}",
        terminal_state=terminal,
        terminal_at=TERMINAL_AT,
        terminal_reason="OBSERVED",
        timestamp=RECONCILED_AT,
    )


def _terminal_document(tmp_path, *, mode=active.SWING, suffix="one", terminal=active.CLOSED_PROFIT):
    path, refill_path = _paths(tmp_path, suffix)
    reserved = _reserve(path, mode=mode, suffix=suffix)
    result = _call(path, refill_path, reserved, suffix=suffix, terminal=terminal)
    return path, refill_path, active.load_ledger(path), result


def test_successful_terminal_transition_reconciles_one_request_and_result_schema(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    result = _call(path, refill_path, reserved)
    assert result.result == integration.TRANSITION_AND_REFILL_RECONCILED
    assert result.transition_applied and result.refill_reconciled
    assert not result.partial_success and not result.replay
    assert len(refill.load_refill_ledger(refill_path)[_REQUEST_MAP]) == 1
    assert tuple(result.to_dict()) == (
        "result", "terminal_transition_id", "signal_id", "mode", "terminal_state",
        "active_ledger_revision", "refill_request_id", "refill_ledger_revision",
        "transition_applied", "refill_reconciled", "partial_success", "replay",
        "reason", "timestamp",
    )


@pytest.mark.parametrize("mode", (active.SWING, active.INTRADAY, active.SCALP))
def test_persisted_signal_mode_is_propagated(tmp_path, mode):
    path, refill_path = _paths(tmp_path, mode)
    reserved = _reserve(path, mode=mode, suffix=mode)
    result = _call(path, refill_path, reserved, suffix=mode)
    assert result.mode == mode


@pytest.mark.parametrize("terminal", active.TERMINAL_STATES)
def test_every_terminal_state_is_supported_from_pending(tmp_path, terminal):
    path, refill_path = _paths(tmp_path, terminal)
    reserved = _reserve(path, suffix=terminal)
    result = _call(path, refill_path, reserved, suffix=terminal, terminal=terminal)
    assert result.terminal_state == terminal
    assert result.refill_reconciled


def test_equivalent_replay_creates_no_duplicate_transition_or_refill(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    first = _call(path, refill_path, reserved)
    replay = _call(
        path, refill_path, active.load_ledger(path), suffix="one",
        refill_revision=first.refill_ledger_revision,
    )
    assert replay.result == integration.REFILL_ALREADY_RECONCILED
    assert replay.replay and replay.refill_reconciled
    assert replay.active_ledger_revision == first.active_ledger_revision
    assert replay.refill_ledger_revision == first.refill_ledger_revision
    assert len(refill.load_refill_ledger(refill_path)[_REQUEST_MAP]) == 1


def test_distinct_terminal_identifiers_for_distinct_signals_create_distinct_records(tmp_path):
    path, refill_path = _paths(tmp_path)
    first = _reserve(path, suffix="one")
    _call(path, refill_path, first, suffix="one")
    second = active.reserve_published_signal(
        path, expected_revision=active.load_ledger(path)["ledger_revision"],
        transaction_id="transaction-two", transition_id="reserve-two", signal_id="signal-two",
        delivery_id="delivery-two", mode=active.SWING, symbol="BTCUSDT", published_at=NOW,
        source_payload_hash=HASH_A, publication_payload_hash=HASH_B, updated_at=NOW,
    )
    result = _call(path, refill_path, second, suffix="two", refill_revision=1)
    assert result.result == integration.TRANSITION_AND_REFILL_RECONCILED
    assert len(refill.load_refill_ledger(refill_path)[_REQUEST_MAP]) == 2


def test_distinct_terminal_identifier_for_already_terminal_signal_fails_closed(tmp_path):
    path, refill_path, ledger, _ = _terminal_document(tmp_path)
    result = _call(path, refill_path, ledger, suffix="different", refill_revision=1)
    assert result.result == integration.FAIL_CLOSED
    assert result.reason == integration.NO_TERMINAL_TRANSITION


def test_active_and_refill_revisions_increment_once_only_for_their_mutations(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    result = _call(path, refill_path, reserved)
    assert result.active_ledger_revision == reserved["ledger_revision"] + 1
    assert result.refill_ledger_revision == 1


def test_missing_signal_invalid_terminal_and_stale_active_revision_fail_closed(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    missing = integration.transition_and_reconcile_refill(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=reserved["ledger_revision"], expected_refill_ledger_revision=None,
        terminal_transition_id="terminal-missing", signal_id="missing", terminal_state=active.CLOSED_PROFIT,
        terminal_at=TERMINAL_AT, terminal_reason="OBSERVED", timestamp=RECONCILED_AT,
    )
    invalid = _call(path, refill_path, reserved, terminal="NOT_A_TERMINAL")
    stale = integration.transition_and_reconcile_refill(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=0, expected_refill_ledger_revision=None,
        terminal_transition_id="terminal-stale", signal_id="signal-one",
        terminal_state=active.CLOSED_PROFIT, terminal_at=TERMINAL_AT,
        terminal_reason="OBSERVED", timestamp=RECONCILED_AT,
    )
    assert missing.result == integration.ACTIVE_LEDGER_FAILURE
    assert invalid.result == integration.FAIL_CLOSED
    assert stale.result == integration.ACTIVE_REVISION_CONFLICT


def test_stale_refill_revision_does_not_undo_the_committed_terminal_transition(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    refill.reconcile_terminal_transition(
        refill_path, terminal_transition_id="other", signal_id="other", mode=active.SWING,
        terminal_state=active.CLOSED_PROFIT, source_ledger_revision=1, timestamp=NOW,
    )
    result = _call(path, refill_path, reserved, refill_revision=0)
    assert result.result == integration.TRANSITION_APPLIED_REFILL_PENDING
    assert result.reason == integration.REFILL_REVISION_CONFLICT
    assert active.load_ledger(path)["signals"]["signal-one"]["state"] == active.CLOSED_PROFIT


@pytest.mark.parametrize("failure_reason", (coordinator.REFILL_LOCK_UNAVAILABLE, coordinator.REFILL_PERSISTENCE_FAILURE))
def test_refill_failure_after_active_commit_is_sanitized_partial_success(tmp_path, monkeypatch, failure_reason):
    path, refill_path = _paths(tmp_path, failure_reason)
    reserved = _reserve(path, suffix=failure_reason)
    monkeypatch.setattr(
        integration.coordinator, "reconcile_terminal_refill",
        lambda **_: coordinator.PassiveStyleRefillDecisionV1(
            decision=coordinator.FAIL_CLOSED, refill_request_id=None, terminal_transition_id=None,
            signal_id=None, mode=None, terminal_state=None, request_status=None, eligibility=None,
            scan_units=0, active_ledger_revision=None, refill_ledger_revision=None,
            claim_token=None, reason=failure_reason, timestamp=RECONCILED_AT,
        ),
    )
    result = _call(path, refill_path, reserved, suffix=failure_reason)
    assert result.result == integration.TRANSITION_APPLIED_REFILL_PENDING
    assert result.partial_success and not result.refill_reconciled
    assert active.load_ledger(path)["signals"][f"signal-{failure_reason}"]["state"] == active.CLOSED_PROFIT


def test_explicit_repair_creates_missing_request_then_replays_without_active_mutation(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    terminal = active.transition_terminal(
        path, expected_revision=reserved["ledger_revision"], transition_id="terminal-one",
        signal_id="signal-one", terminal_state=active.CLOSED_PROFIT, terminal_at=TERMINAL_AT,
        terminal_reason="OBSERVED", updated_at=RECONCILED_AT,
    )
    repaired = integration.reconcile_existing_terminal_refill(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"], expected_refill_ledger_revision=None,
        terminal_transition_id="terminal-one", timestamp=RECONCILED_AT,
    )
    replay = integration.reconcile_existing_terminal_refill(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"],
        expected_refill_ledger_revision=repaired.refill_ledger_revision,
        terminal_transition_id="terminal-one", timestamp=RECONCILED_AT,
    )
    assert repaired.result == integration.TRANSITION_AND_REFILL_RECONCILED
    assert replay.result == integration.REFILL_ALREADY_RECONCILED
    assert active.load_ledger(path) == terminal


def test_restart_repair_missing_transition_and_malformed_persistence_are_fail_closed(tmp_path):
    path, refill_path, terminal, _ = _terminal_document(tmp_path)
    missing = integration.reconcile_existing_terminal_refill(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"], expected_refill_ledger_revision=None,
        terminal_transition_id="missing", timestamp=RECONCILED_AT,
    )
    path.write_text("{invalid", encoding="utf-8")
    malformed = integration.reconcile_existing_terminal_refill(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"], expected_refill_ledger_revision=None,
        terminal_transition_id="terminal-one", timestamp=RECONCILED_AT,
    )
    assert missing.result == integration.NO_TERMINAL_TRANSITION
    assert malformed.result == integration.ACTIVE_LEDGER_FAILURE


def test_pure_inspection_distinguishes_pending_and_reconciled_without_mutation(tmp_path):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    terminal = active.transition_terminal(
        path, expected_revision=reserved["ledger_revision"], transition_id="terminal-one",
        signal_id="signal-one", terminal_state=active.CLOSED_PROFIT, terminal_at=TERMINAL_AT,
        terminal_reason="OBSERVED", updated_at=RECONCILED_AT,
    )
    empty = refill.load_refill_ledger(refill_path, created_at=RECONCILED_AT)
    pending = integration.inspect_terminal_refill_result(
        active_ledger=terminal, refill_ledger=empty, terminal_transition_id="terminal-one", timestamp=RECONCILED_AT,
    )
    refill.reconcile_terminal_transition(
        refill_path, terminal_transition_id="terminal-one", signal_id="signal-one", mode=active.SWING,
        terminal_state=active.CLOSED_PROFIT, source_ledger_revision=terminal["transitions"]["terminal-one"]["ledger_revision"],
        timestamp=RECONCILED_AT,
    )
    before = (json.dumps(terminal, sort_keys=True), json.dumps(refill.load_refill_ledger(refill_path), sort_keys=True))
    reconciled = integration.inspect_terminal_refill_result(
        active_ledger=terminal, refill_ledger=refill.load_refill_ledger(refill_path),
        terminal_transition_id="terminal-one", timestamp=RECONCILED_AT,
    )
    after = (json.dumps(terminal, sort_keys=True), json.dumps(refill.load_refill_ledger(refill_path), sort_keys=True))
    assert pending.result == integration.TRANSITION_APPLIED_REFILL_PENDING
    assert reconciled.result == integration.REFILL_ALREADY_RECONCILED
    assert before == after


def test_pure_inspection_rejects_non_terminal_missing_signal_and_state_mismatch(tmp_path):
    _, refill_path, terminal, _ = _terminal_document(tmp_path)
    refill_document = refill.load_refill_ledger(refill_path)
    non_terminal = copy.deepcopy(terminal)
    non_terminal["transitions"]["terminal-one"]["operation"] = "ENTRY"
    missing_signal = copy.deepcopy(terminal)
    del missing_signal["signals"]["signal-one"]
    mismatch = copy.deepcopy(terminal)
    mismatch["signals"]["signal-one"]["state"] = active.CANCELLED
    for document in (non_terminal, missing_signal, mismatch):
        result = integration.inspect_terminal_refill_result(
            active_ledger=document, refill_ledger=refill_document,
            terminal_transition_id="terminal-one", timestamp=RECONCILED_AT,
        )
        assert result.result == integration.FAIL_CLOSED


def test_lock_and_atomic_failures_preserve_authoritative_state(tmp_path, monkeypatch):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    before = active.load_ledger(path)
    monkeypatch.setattr(active, "_atomic_write", lambda *_: (_ for _ in ()).throw(OSError()))
    atomic = _call(path, refill_path, reserved)
    assert atomic.result == integration.ACTIVE_LEDGER_FAILURE
    assert active.load_ledger(path) == before


def test_active_lock_contention_fails_before_transition_mutation(tmp_path, monkeypatch):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)

    @contextmanager
    def unavailable(_):
        raise active.ActiveSignalLedgerError(active.LOCK_ACQUISITION_FAILED)
        yield

    monkeypatch.setattr(active, "_ledger_lock", unavailable)
    result = _call(path, refill_path, reserved)
    assert result.result == integration.ACTIVE_LEDGER_FAILURE
    assert result.reason == integration.ACTIVE_LOCK_UNAVAILABLE
    assert active.load_ledger(path)["signals"]["signal-one"]["state"] == active.PUBLISHED_PENDING_ENTRY


def test_refill_atomic_and_malformed_failures_preserve_committed_terminal(tmp_path, monkeypatch):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    monkeypatch.setattr(refill, "_write_atomic", lambda *_: (_ for _ in ()).throw(OSError()))
    partial = _call(path, refill_path, reserved)
    assert partial.result == integration.TRANSITION_APPLIED_REFILL_PENDING
    assert active.load_ledger(path)["signals"]["signal-one"]["state"] == active.CLOSED_PROFIT
    monkeypatch.undo()
    refill_path.write_text("{invalid", encoding="utf-8")
    malformed = integration.reconcile_existing_terminal_refill(
        active_ledger_path=path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=partial.active_ledger_revision,
        expected_refill_ledger_revision=None, terminal_transition_id="terminal-one", timestamp=RECONCILED_AT,
    )
    assert malformed.result == integration.REFILL_LEDGER_FAILURE


def test_failure_reasons_are_sanitized_and_boolean_flags_remain_consistent(tmp_path, monkeypatch):
    path, refill_path = _paths(tmp_path)
    reserved = _reserve(path)
    monkeypatch.setattr(
        integration.coordinator, "reconcile_terminal_refill",
        lambda **_: coordinator.PassiveStyleRefillDecisionV1(
            decision=coordinator.FAIL_CLOSED, refill_request_id=None, terminal_transition_id=None,
            signal_id=None, mode=None, terminal_state=None, request_status=None, eligibility=None,
            scan_units=0, active_ledger_revision=None, refill_ledger_revision=None,
            claim_token=None, reason=coordinator.REFILL_PERSISTENCE_FAILURE, timestamp=RECONCILED_AT,
        ),
    )
    result = _call(path, refill_path, reserved)
    assert result.reason == integration.REFILL_PERSISTENCE_FAILURE
    assert "/" not in result.reason and "OSError" not in result.reason
    assert result.partial_success == (result.transition_applied and not result.refill_reconciled)


def test_static_passive_boundaries_are_explicit():
    source = (Path(__file__).parents[1] / "engine" / "passive_terminal_refill_integration_v1.py").read_text(encoding="utf-8")
    forbidden = (
        "telegram", "scanner", "master_engine", "quota_slot_worker", "stateful_worker",
        "scheduler", "evaluate_refill_dispatch(", "claim_eligible_refill(",
        "claim_refill_request(", "requests.", "httpx.", "urllib.", "socket.",
        "systemd", "subprocess",
    )
    assert all(item not in source for item in forbidden)
