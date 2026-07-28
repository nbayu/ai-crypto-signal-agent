"""Focused contracts for non-occupying publication and owner lifecycle."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import passive_production_signal_flow_v1 as flow
from engine import passive_published_signal_registration_v1 as registration
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine import style_refill_request_ledger_v1 as refill


NOW = "2026-07-21T00:00:00Z"
ENTRY_AT = "2026-07-21T00:01:00Z"
TERMINAL_AT = "2026-07-21T00:02:00Z"
LATER = "2026-07-21T00:03:00Z"
SOURCE_HASH = "a" * 64
PUBLICATION_HASH = "b" * 64
CONTENT_HASH = "c" * 64


def _evidence(mode=active.SWING, suffix="one", **overrides):
    evidence = {
        "delivery_state": "DELIVERY_SUCCEEDED",
        "signal_id": f"signal-{suffix}",
        "delivery_id": f"delivery-{suffix}",
        "mode": mode,
        "published_at": NOW,
        "source_payload_hash": SOURCE_HASH,
        "publication_payload_hash": PUBLICATION_HASH,
        "content_hash": CONTENT_HASH,
        "publication_payload": {
            "signal_id": f"signal-{suffix}", "mode": mode, "symbol": "BTCUSDT",
        },
    }
    evidence.update(overrides)
    return evidence


def _paths(tmp_path):
    active_path = tmp_path / "active.json"
    refill_path = tmp_path / "refill.json"
    active.initialize_ledger(active_path, created_at=NOW)
    return active_path, refill_path


def _register(tmp_path, *, revision=0, **kwargs):
    active_path, _ = _paths(tmp_path)
    return flow.register_completed_publication(
        active_ledger_path=active_path,
        expected_active_ledger_revision=revision,
        publication_evidence=_evidence(**kwargs.pop("evidence", {})),
        reservation_transition_id=kwargs.pop("reservation_transition_id", "reserve-one"),
        timestamp=kwargs.pop("timestamp", NOW),
    )


def _registered_paths(tmp_path):
    active_path, refill_path = _paths(tmp_path)
    created = flow.register_completed_publication(
        active_ledger_path=active_path,
        expected_active_ledger_revision=0,
        publication_evidence=_evidence(),
        reservation_transition_id="reserve-one",
        timestamp=NOW,
    )
    return active_path, refill_path, created


def _entry(active_path, revision):
    return flow.activate_registered_signal(
        active_ledger_path=active_path,
        expected_active_ledger_revision=revision,
        entry_transition_id="entry-one",
        signal_id="signal-one",
        entry_at=ENTRY_AT,
        timestamp=ENTRY_AT,
    )


def _terminal(active_path, refill_path, revision, *, refill_revision=None):
    return flow.terminate_active_signal(
        active_ledger_path=active_path,
        refill_ledger_path=refill_path,
        expected_active_ledger_revision=revision,
        expected_refill_ledger_revision=refill_revision,
        terminal_transition_id="terminal-one",
        signal_id="signal-one",
        terminal_state=active.CLOSED_PROFIT,
        terminal_at=TERMINAL_AT,
        terminal_reason="OBSERVED",
        timestamp=LATER,
    )


def test_result_type_schema_is_frozen_slotted_and_ordered():
    fields = tuple(flow.PassiveProductionSignalFlowResultV1.__dataclass_fields__)
    assert fields == (
        "result", "operation", "signal_id", "mode", "symbol", "delivery_id",
        "publication_identity_hash", "signal_payload_hash", "reservation_transaction_id",
        "reservation_transition_id", "entry_transition_id", "terminal_transition_id",
        "active_ledger_revision", "refill_request_id", "refill_ledger_revision",
        "previous_state", "current_state", "publication_confirmed",
        "registration_applied", "entry_applied", "terminal_applied", "refill_reconciled",
        "partial_success", "replay", "reason", "timestamp",
    )
    assert flow.PassiveProductionSignalFlowResultV1.__dataclass_params__.frozen
    assert hasattr(flow.PassiveProductionSignalFlowResultV1, "__slots__")


def test_registration_delegates_once_and_normalizes(tmp_path, monkeypatch):
    active_path, _ = _paths(tmp_path)
    calls = []
    original = flow.registration.register_published_signal

    def delegated(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(flow.registration, "register_published_signal", delegated)
    result = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    assert len(calls) == 1
    assert result.result == flow.PUBLISHED_SIGNAL_REGISTERED
    assert result.operation == flow.REGISTER_COMPLETED_PUBLICATION
    assert result.symbol == "BTCUSDT" and result.delivery_id == "delivery-one"
    assert result.publication_confirmed and result.registration_applied
    assert tuple(result.to_dict()) == tuple(flow.PassiveProductionSignalFlowResultV1.__dataclass_fields__)


def test_registration_replay_conflicts_revision_and_partial_success_are_preserved(tmp_path, monkeypatch):
    active_path, _ = _paths(tmp_path)
    first = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    replay = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=first.active_ledger_revision,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    conflict = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=first.active_ledger_revision,
        publication_evidence=_evidence(publication_payload={"signal_id": "signal-one", "mode": active.SWING, "symbol": "ETHUSDT"}),
        reservation_transition_id="reserve-one", timestamp=NOW,
    )
    stale = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    pending_path = tmp_path / "pending.json"
    active.initialize_ledger(pending_path, created_at=NOW)
    monkeypatch.setattr(active, "_LOCK_ATTEMPTS", 0)
    pending = flow.register_completed_publication(
        active_ledger_path=pending_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-pending", timestamp=NOW,
    )
    assert replay.result == flow.PUBLISHED_SIGNAL_REGISTRATION_REPLAYED and replay.replay
    assert replay.active_ledger_revision == first.active_ledger_revision
    assert conflict.result == flow.SIGNAL_IDENTITY_CONFLICT
    assert stale.result == flow.ACTIVE_REVISION_CONFLICT
    assert pending.result == flow.PUBLICATION_SUCCEEDED_REGISTRATION_PENDING
    assert pending.publication_confirmed and pending.partial_success and not pending.registration_applied


def test_registration_transaction_and_reservation_conflicts_are_preserved(tmp_path):
    active_path, _ = _paths(tmp_path)
    created = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    snapshot = active.load_ledger(active_path)
    transaction_record = snapshot["publication_transactions"][created.reservation_transaction_id]
    transaction_record["state"] = active.PREPARED
    transaction_record["source_payload_hash"] = "d" * 64
    transaction = flow.inspect_production_signal_flow(
        active_ledger=snapshot, signal_id="signal-one", timestamp=NOW,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one",
    )
    reservation = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=created.active_ledger_revision,
        publication_evidence=_evidence(), reservation_transition_id="reserve-other", timestamp=NOW,
    )
    assert transaction.result == flow.TRANSACTION_IDENTITY_CONFLICT
    assert reservation.result == flow.RESERVATION_IDENTITY_CONFLICT


@pytest.mark.parametrize("mode", active.STYLES)
def test_registration_preserves_each_mode_and_deterministic_identity(tmp_path, mode):
    active_path, _ = _paths(tmp_path)
    result = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(mode=mode), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    assert result.result == flow.PUBLISHED_SIGNAL_REGISTERED
    assert result.mode == mode and result.reservation_transaction_id is not None


def test_entry_delegates_once_normalizes_replay_and_failures(tmp_path, monkeypatch):
    active_path, _, created = _registered_paths(tmp_path)
    calls = []
    original = flow.lifecycle.activate_signal_entry

    def delegated(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(flow.lifecycle, "activate_signal_entry", delegated)
    first = _entry(active_path, created.active_ledger_revision)
    replay = _entry(active_path, first.active_ledger_revision)
    invalid = flow.activate_registered_signal(
        active_ledger_path=active_path, expected_active_ledger_revision=first.active_ledger_revision,
        entry_transition_id="entry-other", signal_id="signal-one", entry_at=ENTRY_AT, timestamp=ENTRY_AT,
    )
    stale = _entry(active_path, 0)
    assert len(calls) == 4
    assert first.result == flow.ENTRY_ACTIVATED and first.entry_applied
    assert first.symbol is None and first.delivery_id is None
    assert replay.result == flow.ENTRY_REPLAYED and replay.replay
    assert invalid.result == flow.INVALID_STATE_TRANSITION
    assert stale.result == flow.ACTIVE_REVISION_CONFLICT


def test_terminal_delegates_once_and_preserves_replay_partial_and_conflicts(tmp_path, monkeypatch):
    active_path, refill_path, created = _registered_paths(tmp_path)
    calls = []
    original = flow.lifecycle.terminate_signal_and_reconcile_refill

    def delegated(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(flow.lifecycle, "terminate_signal_and_reconcile_refill", delegated)
    first = _terminal(active_path, refill_path, created.active_ledger_revision)
    replay = _terminal(active_path, refill_path, first.active_ledger_revision, refill_revision=first.refill_ledger_revision)
    stale = _terminal(active_path, refill_path, created.active_ledger_revision)
    assert len(calls) == 3
    assert first.result == flow.TERMINAL_AND_REFILL_RECONCILED
    assert first.terminal_applied and first.refill_reconciled
    assert replay.result == flow.REFILL_ALREADY_RECONCILED and replay.replay
    assert stale.result == flow.ACTIVE_REVISION_CONFLICT


def test_terminal_partial_success_and_refill_revision_conflict_are_normalized(tmp_path, monkeypatch):
    active_path, refill_path, created = _registered_paths(tmp_path)
    partial = lifecycle.PassiveSignalLifecycleResultV1(
        result=lifecycle.TERMINAL_APPLIED_REFILL_PENDING, operation="TERMINAL_TRANSITION",
        signal_id="signal-one", mode=active.SWING, previous_state=None,
        current_state=active.CLOSED_PROFIT, entry_transition_id=None,
        terminal_transition_id="terminal-one", active_ledger_revision=2,
        refill_request_id="d" * 64, refill_ledger_revision=None, entry_applied=False,
        terminal_applied=True, refill_reconciled=False, partial_success=True, replay=False,
        reason="REFILL_PERSISTENCE_FAILURE", timestamp=LATER,
    )
    monkeypatch.setattr(flow.lifecycle, "terminate_signal_and_reconcile_refill", lambda **_: partial)
    pending = _terminal(active_path, refill_path, created.active_ledger_revision)
    assert pending.result == flow.TERMINAL_APPLIED_REFILL_PENDING
    assert pending.terminal_applied and pending.partial_success and not pending.refill_reconciled


@pytest.mark.parametrize("terminal_state", tuple(
    state for state in active.TERMINAL_STATES
    if state not in {active.CLOSED_MANUAL, active.REJECTED_BY_OWNER}
))
def test_terminal_preserves_each_supported_terminal_state(tmp_path, terminal_state):
    active_path, refill_path, created = _registered_paths(tmp_path)
    result = flow.terminate_active_signal(
        active_ledger_path=active_path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=created.active_ledger_revision,
        expected_refill_ledger_revision=None, terminal_transition_id="terminal-one",
        signal_id="signal-one", terminal_state=terminal_state, terminal_at=TERMINAL_AT,
        terminal_reason="OBSERVED", timestamp=LATER,
    )
    assert result.result == flow.TERMINAL_AND_REFILL_RECONCILED
    assert result.current_state == terminal_state


def test_terminal_refill_revision_conflict_is_preserved(tmp_path, monkeypatch):
    active_path, refill_path, created = _registered_paths(tmp_path)
    outcome = lifecycle.PassiveSignalLifecycleResultV1(
        result=lifecycle.REFILL_REVISION_CONFLICT, operation="TERMINAL_TRANSITION",
        signal_id="signal-one", mode=active.SWING, previous_state=None,
        current_state=active.CLOSED_PROFIT, entry_transition_id=None,
        terminal_transition_id="terminal-one", active_ledger_revision=created.active_ledger_revision,
        refill_request_id="d" * 64, refill_ledger_revision=1, entry_applied=False,
        terminal_applied=False, refill_reconciled=False, partial_success=False, replay=False,
        reason=lifecycle.REFILL_REVISION_CONFLICT, timestamp=LATER,
    )
    monkeypatch.setattr(flow.lifecycle, "terminate_signal_and_reconcile_refill", lambda **_: outcome)
    result = _terminal(active_path, refill_path, created.active_ledger_revision, refill_revision=0)
    assert result.result == flow.REFILL_REVISION_CONFLICT
    assert result.refill_ledger_revision == 1


def test_registration_repair_delegates_once_and_is_idempotent(tmp_path, monkeypatch):
    active_path, _ = _paths(tmp_path)
    calls = []
    original = flow.registration.reconcile_published_signal_registration

    def delegated(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(flow.registration, "reconcile_published_signal_registration", delegated)
    repaired = flow.repair_publication_registration(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    again = flow.repair_publication_registration(
        active_ledger_path=active_path, expected_active_ledger_revision=repaired.active_ledger_revision,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    assert len(calls) == 2
    assert repaired.result == flow.PUBLISHED_SIGNAL_REGISTERED
    assert again.result == flow.REGISTRATION_ALREADY_PRESENT and not again.registration_applied


def test_terminal_repair_delegates_once_and_does_not_repeat_terminal(tmp_path, monkeypatch):
    active_path, refill_path, created = _registered_paths(tmp_path)
    terminal = active.transition_terminal(
        active_path, expected_revision=created.active_ledger_revision, transition_id="terminal-one",
        signal_id="signal-one", terminal_state=active.CLOSED_PROFIT,
        terminal_at=TERMINAL_AT, terminal_reason="OBSERVED", updated_at=LATER,
    )
    before = copy.deepcopy(terminal)
    calls = []
    original = flow.lifecycle.reconcile_terminal_refill_after_restart

    def delegated(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(flow.lifecycle, "reconcile_terminal_refill_after_restart", delegated)
    repaired = flow.repair_terminal_refill(
        active_ledger_path=active_path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"],
        expected_refill_ledger_revision=None, terminal_transition_id="terminal-one", timestamp=LATER,
    )
    again = flow.repair_terminal_refill(
        active_ledger_path=active_path, refill_ledger_path=refill_path,
        expected_active_ledger_revision=terminal["ledger_revision"],
        expected_refill_ledger_revision=repaired.refill_ledger_revision,
        terminal_transition_id="terminal-one", timestamp=LATER,
    )
    assert len(calls) == 2
    assert repaired.result == flow.TERMINAL_AND_REFILL_RECONCILED
    assert again.result == flow.REFILL_ALREADY_RECONCILED
    assert active.load_ledger(active_path) == before


def test_inspection_covers_pending_entry_active_and_terminal_states(tmp_path):
    active_path, refill_path, created = _registered_paths(tmp_path)
    pending = flow.inspect_production_signal_flow(
        active_ledger=active.load_ledger(active_path), signal_id="signal-one", timestamp=NOW,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one",
    )
    entry = _entry(active_path, created.active_ledger_revision)
    active_state = flow.inspect_production_signal_flow(
        active_ledger=active.load_ledger(active_path), signal_id="signal-one", timestamp=LATER,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one",
        entry_transition_id="entry-one",
    )
    terminal = _terminal(active_path, refill_path, entry.active_ledger_revision)
    reconciled = flow.inspect_production_signal_flow(
        active_ledger=active.load_ledger(active_path), signal_id="signal-one", timestamp=LATER,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one",
        terminal_transition_id="terminal-one", refill_ledger=refill.load_refill_ledger(refill_path),
    )
    assert pending.result == flow.PUBLISHED_ENTRY_INSPECTED
    assert active_state.result == flow.ENTRY_ALREADY_ACTIVE
    assert reconciled.result == flow.REFILL_ALREADY_RECONCILED and terminal.refill_reconciled


def test_inspection_registration_pending_terminal_pending_and_snapshot_nonmutation(tmp_path):
    active_path, refill_path = _paths(tmp_path)
    before = active.load_ledger(active_path)
    missing = flow.inspect_production_signal_flow(
        active_ledger=before, signal_id="signal-one", timestamp=NOW,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one",
    )
    created = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    terminal = active.transition_terminal(
        active_path, expected_revision=created.active_ledger_revision, transition_id="terminal-one",
        signal_id="signal-one", terminal_state=active.CLOSED_PROFIT,
        terminal_at=TERMINAL_AT, terminal_reason="OBSERVED", updated_at=LATER,
    )
    empty = refill.load_refill_ledger(refill_path, created_at=LATER)
    snapshot = copy.deepcopy(terminal)
    pending = flow.inspect_production_signal_flow(
        active_ledger=terminal, signal_id="signal-one", timestamp=LATER,
        terminal_transition_id="terminal-one", refill_ledger=empty,
    )
    assert missing.result == flow.NO_REGISTRATION
    assert pending.result == flow.TERMINAL_APPLIED_REFILL_PENDING
    assert terminal == snapshot


@pytest.mark.parametrize(
    ("publication_evidence", "reservation_transition_id", "terminal_transition_id", "refill_ledger"),
    (
        (_evidence(), None, None, None),
        (None, "reserve-one", None, None),
        (None, None, None, {"invalid": True}),
        (None, None, "terminal-one", None),
    ),
)
def test_inspection_rejects_invalid_optional_combinations(publication_evidence, reservation_transition_id, terminal_transition_id, refill_ledger):
    result = flow.inspect_production_signal_flow(
        active_ledger={"invalid": True}, signal_id="signal-one", timestamp=NOW,
        publication_evidence=publication_evidence, reservation_transition_id=reservation_transition_id,
        terminal_transition_id=terminal_transition_id, refill_ledger=refill_ledger,
    )
    assert result.result == flow.INVALID_OPERATION
    assert result.reason == flow.INVALID_INSPECTION_ARGUMENTS


@pytest.mark.parametrize("mismatch", ("signal", "mode"))
def test_inspection_cross_component_identity_mismatch_fails_closed(tmp_path, monkeypatch, mismatch):
    active_path, _, created = _registered_paths(tmp_path)
    snapshot = active.load_ledger(active_path)
    original = flow.registration.inspect_published_signal_registration

    def mismatched(**kwargs):
        outcome = original(**kwargs)
        return registration.PassivePublishedSignalRegistrationResultV1(
            result=registration.REGISTRATION_ALREADY_PRESENT,
            signal_id="other-signal" if mismatch == "signal" else outcome.signal_id,
            reservation_transaction_id=outcome.reservation_transaction_id,
            reservation_transition_id=outcome.reservation_transition_id,
            delivery_id=outcome.delivery_id,
            mode="SCALP" if mismatch == "mode" else outcome.mode,
            symbol=outcome.symbol,
            published_at=outcome.published_at, publication_identity_hash=outcome.publication_identity_hash,
            signal_payload_hash=outcome.signal_payload_hash, source_payload_hash=outcome.source_payload_hash,
            publication_payload_hash=outcome.publication_payload_hash,
            active_ledger_revision=outcome.active_ledger_revision, current_state=outcome.current_state,
            publication_confirmed=True, registration_applied=False, partial_success=False,
            replay=False, reason=registration.REGISTRATION_ALREADY_PRESENT, timestamp=NOW,
        )

    monkeypatch.setattr(flow.registration, "inspect_published_signal_registration", mismatched)
    result = flow.inspect_production_signal_flow(
        active_ledger=snapshot, signal_id="signal-one", timestamp=NOW,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one",
    )
    assert created.registration_applied
    assert result.result == flow.FAIL_CLOSED
    assert result.reason == flow.CROSS_COMPONENT_IDENTITY_MISMATCH


def test_inspection_malformed_snapshots_and_unexpected_failure_fail_closed(tmp_path, monkeypatch):
    malformed = flow.inspect_production_signal_flow(
        active_ledger={"invalid": True}, signal_id="signal-one", timestamp=NOW,
    )
    monkeypatch.setattr(flow.lifecycle, "inspect_signal_lifecycle", lambda **_: (_ for _ in ()).throw(RuntimeError()))
    unexpected = flow.inspect_production_signal_flow(
        active_ledger={"invalid": True}, signal_id="signal-one", timestamp=NOW,
    )
    assert malformed.result == flow.FAIL_CLOSED
    assert unexpected.result == flow.FAIL_CLOSED and unexpected.reason == flow.FAIL_CLOSED


def test_inspection_malformed_refill_snapshot_fails_closed(tmp_path):
    active_path, _, created = _registered_paths(tmp_path)
    terminal = active.transition_terminal(
        active_path, expected_revision=created.active_ledger_revision, transition_id="terminal-one",
        signal_id="signal-one", terminal_state=active.CLOSED_PROFIT,
        terminal_at=TERMINAL_AT, terminal_reason="OBSERVED", updated_at=LATER,
    )
    result = flow.inspect_production_signal_flow(
        active_ledger=terminal, signal_id="signal-one", timestamp=LATER,
        terminal_transition_id="terminal-one", refill_ledger={"invalid": True},
    )
    assert result.result == flow.FAIL_CLOSED


def test_unexpected_delegate_failure_is_sanitized(tmp_path, monkeypatch):
    active_path, _ = _paths(tmp_path)
    monkeypatch.setattr(
        flow.registration,
        "register_published_signal",
        lambda **_: (_ for _ in ()).throw(RuntimeError("/not-disclosed")),
    )
    result = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    assert result.result == flow.FAIL_CLOSED and result.reason == flow.FAIL_CLOSED
    assert "/" not in (result.reason or "")


def test_public_operations_do_not_advance_more_than_one_state(tmp_path, monkeypatch):
    active_path, _ = _paths(tmp_path)
    monkeypatch.setattr(flow.lifecycle, "activate_signal_entry", lambda **_: pytest.fail("unexpected"))
    result = flow.register_completed_publication(
        active_ledger_path=active_path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    assert result.result == flow.PUBLISHED_SIGNAL_REGISTERED


def test_result_booleans_and_nullable_fields_are_consistent(tmp_path):
    result = _register(tmp_path)
    assert result.registration_applied and result.publication_confirmed
    assert not result.entry_applied and not result.terminal_applied and not result.refill_reconciled
    assert result.entry_transition_id is None and result.terminal_transition_id is None


def test_source_has_no_forbidden_operational_or_direct_mutation_surface():
    source = (Path(__file__).parents[1] / "engine" / "passive_production_signal_flow_v1.py").read_text(encoding="utf-8")
    forbidden = (
        "active" + "_signal_ledger", "style" + "_refill_request_ledger",
        "passive" + "_terminal_refill_integration", "production" + "_signal_service",
        "tele" + "gram", "scan" + "_market", "master" + "_engine",
        "quota" + "_slot_worker", "stateful" + "_worker", "sub" + "process",
        "evaluate" + "_refill_dispatch", "claim" + "_eligible_refill",
        "reserve" + "_published_signal", "mark" + "_entry_active",
    )
    assert not any(value in source for value in forbidden)
    assert "str(exc)" not in source and "repr(exc)" not in source and "BaseException" not in source
