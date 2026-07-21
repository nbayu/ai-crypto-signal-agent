"""Focused contract tests for the passive Style Refill Coordinator v1."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import passive_style_refill_coordinator_v1 as coordinator
from engine import style_refill_request_ledger_v1 as refill


NOW = "2026-07-21T00:00:00Z"
LATER = "2026-07-21T00:01:00Z"
LATERER = "2026-07-21T00:02:00Z"
HASH_A = "a" * 64
HASH_B = "b" * 64


def _active_path(tmp_path, suffix):
    return tmp_path / f"active-{suffix}.json"


def _refill_path(tmp_path):
    return tmp_path / "refill.json"


def _terminal_snapshot(tmp_path, mode=active.SWING, suffix="1"):
    path = _active_path(tmp_path, suffix)
    active.initialize_ledger(path, created_at=NOW)
    reserved = active.reserve_published_signal(
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
    return active.transition_terminal(
        path,
        expected_revision=reserved["ledger_revision"],
        transition_id=f"terminal-{suffix}",
        signal_id=f"signal-{suffix}",
        terminal_state=active.CLOSED_PROFIT,
        terminal_at=LATER,
        terminal_reason="OBSERVED",
        updated_at=LATER,
    )


def _pending_snapshot(tmp_path, mode=active.SWING, suffix="pending"):
    path = _active_path(tmp_path, suffix)
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


def _capacity(mode, remaining):
    values = {item: 0 for item in active.STYLES}
    values[mode] = remaining
    return {"remaining_by_mode": values}


def _reconcile(tmp_path, snapshot, suffix="1", revision=None):
    return coordinator.reconcile_terminal_refill(
        active_ledger=snapshot,
        terminal_transition_id=f"terminal-{suffix}",
        expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=revision,
        timestamp=LATERER,
    )


def _request(snapshot, tmp_path, suffix="1"):
    decision = _reconcile(tmp_path, snapshot, suffix)
    return decision, refill.load_refill_ledger(_refill_path(tmp_path))


def test_terminal_creates_one_refill_request_with_all_decision_fields(tmp_path):
    snapshot = _terminal_snapshot(tmp_path)
    decision, ledger = _request(snapshot, tmp_path)
    assert decision.decision == coordinator.REQUEST_RECONCILED
    assert set(decision.to_dict()) == {
        "decision", "refill_request_id", "terminal_transition_id", "signal_id", "mode",
        "terminal_state", "request_status", "eligibility", "scan_units",
        "active_ledger_revision", "refill_ledger_revision", "claim_token", "reason", "timestamp",
    }
    assert len(ledger["requests"]) == 1 and decision.scan_units == 0


def test_equivalent_replay_is_idempotent_without_refill_revision_increment(tmp_path):
    snapshot = _terminal_snapshot(tmp_path)
    first, ledger = _request(snapshot, tmp_path)
    replay = _reconcile(tmp_path, snapshot, revision=ledger["ledger_revision"])
    assert replay.decision == coordinator.REQUEST_ALREADY_RECONCILED
    assert replay.refill_ledger_revision == first.refill_ledger_revision


def test_distinct_terminal_transitions_create_distinct_requests(tmp_path):
    first = _terminal_snapshot(tmp_path, suffix="one")
    _reconcile(tmp_path, first, "one")
    second = _terminal_snapshot(tmp_path, suffix="two")
    decision = _reconcile(tmp_path, second, "two", revision=1)
    assert decision.decision == coordinator.REQUEST_RECONCILED
    assert len(refill.load_refill_ledger(_refill_path(tmp_path))["requests"]) == 2


@pytest.mark.parametrize("mode", (active.SWING, active.INTRADAY, active.SCALP))
def test_terminal_mode_is_taken_from_persisted_signal(tmp_path, mode):
    snapshot = _terminal_snapshot(tmp_path, mode=mode, suffix=mode)
    decision, _ = _request(snapshot, tmp_path, mode)
    assert decision.mode == mode


def test_missing_and_non_terminal_transition_are_rejected_without_mutation(tmp_path):
    empty = active.create_empty_ledger(NOW)
    missing = coordinator.reconcile_terminal_refill(
        active_ledger=empty,
        terminal_transition_id="missing",
        expected_active_ledger_revision=0,
        refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=None,
        timestamp=NOW,
    )
    pending = _pending_snapshot(tmp_path)
    non_terminal = coordinator.reconcile_terminal_refill(
        active_ledger=pending,
        terminal_transition_id="reserve-pending",
        expected_active_ledger_revision=pending["ledger_revision"],
        refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=None,
        timestamp=NOW,
    )
    assert missing.decision == coordinator.NO_TERMINAL_TRANSITION
    assert non_terminal.decision == coordinator.FAIL_CLOSED


def test_invalid_terminal_evidence_and_stale_active_revision_fail_closed(tmp_path):
    snapshot = _terminal_snapshot(tmp_path)
    stale = coordinator.reconcile_terminal_refill(
        active_ledger=snapshot,
        terminal_transition_id="terminal-1",
        expected_active_ledger_revision=0,
        refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=None,
        timestamp=NOW,
    )
    malformed = coordinator.reconcile_terminal_refill(
        active_ledger={"bad": "state"},
        terminal_transition_id="terminal-1",
        expected_active_ledger_revision=0,
        refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=None,
        timestamp=NOW,
    )
    assert stale.decision == coordinator.REVISION_CONFLICT
    assert malformed.decision == coordinator.FAIL_CLOSED


def test_missing_referenced_signal_and_state_mismatch_fail_closed(tmp_path):
    snapshot = _terminal_snapshot(tmp_path)
    missing_signal = {**snapshot, "signals": {}}
    missing = coordinator.reconcile_terminal_refill(
        active_ledger=missing_signal, terminal_transition_id="terminal-1",
        expected_active_ledger_revision=snapshot["ledger_revision"], refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=None, timestamp=NOW,
    )
    transitions = {key: dict(value) for key, value in snapshot["transitions"].items()}
    transitions["terminal-1"]["to_state"] = active.CANCELLED
    mismatched = coordinator.reconcile_terminal_refill(
        active_ledger={**snapshot, "transitions": transitions}, terminal_transition_id="terminal-1",
        expected_active_ledger_revision=snapshot["ledger_revision"], refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=None, timestamp=NOW,
    )
    assert missing.decision == coordinator.FAIL_CLOSED
    assert mismatched.decision == coordinator.FAIL_CLOSED


def test_style_full_is_non_mutating_and_one_slot_is_one_unit(tmp_path):
    snapshot = _terminal_snapshot(tmp_path, mode=active.SCALP)
    request, ledger = _request(snapshot, tmp_path)
    full = coordinator.evaluate_refill_dispatch(
        active_ledger=snapshot,
        expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger=ledger,
        refill_request_id=request.refill_request_id,
        capacity_snapshot=_capacity(active.SCALP, 0),
        capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"],
        timestamp=LATERER,
    )
    eligible = coordinator.evaluate_refill_dispatch(
        active_ledger=snapshot,
        expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger=ledger,
        refill_request_id=request.refill_request_id,
        capacity_snapshot=_capacity(active.SCALP, 1),
        capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"],
        timestamp=LATERER,
    )
    assert full.decision == coordinator.STYLE_FULL and full.scan_units == 0
    assert refill.load_refill_ledger(_refill_path(tmp_path))["requests"][request.refill_request_id]["status"] == refill.PENDING
    assert eligible.decision == coordinator.ELIGIBLE_ONE_SCAN_UNIT and eligible.scan_units == 1


def test_wrong_mode_and_malformed_or_stale_capacity_fail_closed(tmp_path):
    snapshot = _terminal_snapshot(tmp_path, mode=active.SCALP)
    request, ledger = _request(snapshot, tmp_path)
    wrong_mode = coordinator.evaluate_refill_dispatch(
        active_ledger=snapshot, expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger=ledger, refill_request_id=request.refill_request_id,
        capacity_snapshot=_capacity(active.SWING, 1),
        capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"], timestamp=LATERER,
    )
    malformed = coordinator.evaluate_refill_dispatch(
        active_ledger=snapshot, expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger=ledger, refill_request_id=request.refill_request_id,
        capacity_snapshot={}, capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"], timestamp=LATERER,
    )
    stale = coordinator.evaluate_refill_dispatch(
        active_ledger=snapshot, expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger=ledger, refill_request_id=request.refill_request_id,
        capacity_snapshot=_capacity(active.SCALP, 1),
        capacity_snapshot_active_ledger_revision=0, timestamp=LATERER,
    )
    assert wrong_mode.decision == coordinator.STYLE_FULL
    assert malformed.decision == coordinator.FAIL_CLOSED
    assert stale.decision == coordinator.REVISION_CONFLICT


@pytest.mark.parametrize("outcome", (refill.DISPATCHED, refill.CANCELLED_OUTCOME))
def test_completed_and_cancelled_requests_are_not_eligible(tmp_path, outcome):
    snapshot = _terminal_snapshot(tmp_path)
    request, ledger = _request(snapshot, tmp_path)
    claimed = refill.claim_refill_request(
        _refill_path(tmp_path), refill_request_id=request.refill_request_id,
        claim_token="claim", timestamp=NOW, expected_revision=ledger["ledger_revision"],
    )
    terminal = refill.complete_refill_request(
        _refill_path(tmp_path), refill_request_id=request.refill_request_id, claim_token="claim",
        completion_outcome=outcome, timestamp=LATER, expected_revision=claimed["ledger_revision"],
    )
    decision = coordinator.evaluate_refill_dispatch(
        active_ledger=snapshot, expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger=terminal, refill_request_id=request.refill_request_id,
        capacity_snapshot=_capacity(active.SWING, 1),
        capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"], timestamp=LATERER,
    )
    assert decision.decision == coordinator.REQUEST_NOT_ELIGIBLE


def test_claim_success_replay_conflict_and_stale_revision(tmp_path):
    snapshot = _terminal_snapshot(tmp_path)
    request, ledger = _request(snapshot, tmp_path)
    kwargs = dict(
        active_ledger=snapshot, expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger_path=_refill_path(tmp_path), refill_request_id=request.refill_request_id,
        expected_refill_ledger_revision=ledger["ledger_revision"],
        capacity_snapshot=_capacity(active.SWING, 1),
        capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"], timestamp=LATER,
    )
    claimed = coordinator.claim_eligible_refill(**kwargs, claim_token="claim")
    replay = coordinator.claim_eligible_refill(
        **{**kwargs, "expected_refill_ledger_revision": claimed.refill_ledger_revision}, claim_token="claim"
    )
    conflict = coordinator.claim_eligible_refill(
        **{**kwargs, "expected_refill_ledger_revision": claimed.refill_ledger_revision}, claim_token="other"
    )
    stale = coordinator.claim_eligible_refill(**kwargs, claim_token="stale")
    assert claimed.decision == coordinator.ELIGIBLE_ONE_SCAN_UNIT and claimed.scan_units == 1
    assert replay.decision == coordinator.REQUEST_ALREADY_CLAIMED
    assert conflict.reason == coordinator.CLAIM_TOKEN_CONFLICT
    assert stale.decision == coordinator.REVISION_CONFLICT


def test_capacity_change_before_claim_prevents_mutation(tmp_path):
    snapshot = _terminal_snapshot(tmp_path)
    request, ledger = _request(snapshot, tmp_path)
    decision = coordinator.claim_eligible_refill(
        active_ledger=snapshot, expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger_path=_refill_path(tmp_path), refill_request_id=request.refill_request_id,
        expected_refill_ledger_revision=ledger["ledger_revision"],
        capacity_snapshot=_capacity(active.SWING, 1), capacity_snapshot_active_ledger_revision=0,
        claim_token="claim", timestamp=LATER,
    )
    assert decision.decision == coordinator.REVISION_CONFLICT
    assert refill.load_refill_ledger(_refill_path(tmp_path))["requests"][request.refill_request_id]["status"] == refill.PENDING


def test_combined_reconcile_evaluate_and_restart_replay_are_one_unit(tmp_path):
    snapshot = _terminal_snapshot(tmp_path)
    first = coordinator.reconcile_and_evaluate_refill(
        active_ledger=snapshot, terminal_transition_id="terminal-1",
        expected_active_ledger_revision=snapshot["ledger_revision"], refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=None, capacity_snapshot=_capacity(active.SWING, 1),
        capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"], timestamp=LATERER,
    )
    replay = coordinator.reconcile_and_evaluate_refill(
        active_ledger=snapshot, terminal_transition_id="terminal-1",
        expected_active_ledger_revision=snapshot["ledger_revision"], refill_ledger_path=_refill_path(tmp_path),
        expected_refill_ledger_revision=first.refill_ledger_revision, capacity_snapshot=_capacity(active.SWING, 1),
        capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"], timestamp=LATERER,
    )
    assert first.scan_units == replay.scan_units == 1
    assert len(refill.load_refill_ledger(_refill_path(tmp_path))["requests"]) == 1


def test_selection_is_ordered_filtered_and_non_mutating(tmp_path):
    first = _terminal_snapshot(tmp_path, mode=active.SWING, suffix="a")
    second = _terminal_snapshot(tmp_path, mode=active.INTRADAY, suffix="b")
    _reconcile(tmp_path, second, "b")
    _reconcile(tmp_path, first, "a", revision=1)
    ledger = refill.load_refill_ledger(_refill_path(tmp_path))
    selected = coordinator.select_next_pending_refill(refill_ledger=ledger, timestamp=LATERER)
    filtered = coordinator.select_next_pending_refill(refill_ledger=ledger, mode=active.INTRADAY, timestamp=LATERER)
    assert selected.refill_request_id == min(ledger["requests"])
    assert filtered.mode == active.INTRADAY and filtered.scan_units == 0


def test_selection_prefers_created_at_before_request_id(tmp_path):
    first = _terminal_snapshot(tmp_path, suffix="first")
    second = _terminal_snapshot(tmp_path, suffix="second")
    refill.reconcile_terminal_transition(
        _refill_path(tmp_path), terminal_transition_id="terminal-first", signal_id="signal-first",
        mode=active.SWING, terminal_state=active.CLOSED_PROFIT,
        source_ledger_revision=first["transitions"]["terminal-first"]["ledger_revision"],
        timestamp=LATER, expected_revision=None,
    )
    refill.reconcile_terminal_transition(
        _refill_path(tmp_path), terminal_transition_id="terminal-second", signal_id="signal-second",
        mode=active.SWING, terminal_state=active.CLOSED_PROFIT,
        source_ledger_revision=second["transitions"]["terminal-second"]["ledger_revision"],
        timestamp=NOW, expected_revision=1,
    )
    ledger = refill.load_refill_ledger(_refill_path(tmp_path))
    selected = coordinator.select_next_pending_refill(refill_ledger=ledger, timestamp=LATERER)
    assert selected.terminal_transition_id == "terminal-second"


def test_no_pending_and_interrupted_claim_recovery_remain_external(tmp_path):
    empty = refill.create_empty_refill_ledger(created_at=NOW)
    selected = coordinator.select_next_pending_refill(refill_ledger=empty, timestamp=NOW)
    snapshot = _terminal_snapshot(tmp_path)
    request, ledger = _request(snapshot, tmp_path)
    claimed = refill.claim_refill_request(
        _refill_path(tmp_path), refill_request_id=request.refill_request_id,
        claim_token="claim", timestamp=NOW, expected_revision=ledger["ledger_revision"],
    )
    decision = coordinator.evaluate_refill_dispatch(
        active_ledger=snapshot, expected_active_ledger_revision=snapshot["ledger_revision"],
        refill_ledger=claimed, refill_request_id=request.refill_request_id,
        capacity_snapshot=_capacity(active.SWING, 1),
        capacity_snapshot_active_ledger_revision=snapshot["ledger_revision"], timestamp=LATER,
    )
    assert selected.decision == coordinator.REQUEST_NOT_ELIGIBLE
    assert decision.decision == coordinator.REQUEST_ALREADY_CLAIMED


def test_decision_is_sanitized_and_source_is_passive():
    failure = coordinator.select_next_pending_refill(refill_ledger={"bad": "state"}, timestamp=NOW)
    assert failure.decision == coordinator.FAIL_CLOSED
    assert "/" not in (failure.reason or "") and "ValueError" not in (failure.reason or "")
    source = (Path(__file__).parents[1] / "engine" / "passive_style_refill_coordinator_v1.py").read_text(encoding="utf-8")
    forbidden = ("telegram", "scanner", "worker", "scheduler", "provider", "systemd", "requests", "httpx", "urllib", "socket", "subprocess")
    assert not any(f"import {item}" in source or f"from {item}" in source for item in forbidden)
    assert "while True" not in source and "deque(" not in source
    assert "recover_interrupted_claims(" not in source and "_lock(" not in source
