"""Focused contracts for non-occupying published-signal registration."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import passive_published_signal_registration_v1 as registration


NOW = "2026-07-21T00:00:00Z"
LATER = "2026-07-21T00:01:00Z"
SOURCE_HASH = "a" * 64
PUBLICATION_HASH = "b" * 64
CONTENT_HASH = "c" * 64


def _evidence(mode: str = active.SWING, suffix: str = "one", **overrides: object) -> dict[str, object]:
    evidence: dict[str, object] = {
        "delivery_state": "DELIVERY_SUCCEEDED",
        "signal_id": f"signal-{suffix}",
        "delivery_id": f"delivery-{suffix}",
        "mode": mode,
        "published_at": NOW,
        "source_payload_hash": SOURCE_HASH,
        "publication_payload_hash": PUBLICATION_HASH,
        "content_hash": CONTENT_HASH,
        "publication_payload": {
            "signal_id": f"signal-{suffix}",
            "mode": mode,
            "symbol": "BTCUSDT",
        },
    }
    evidence.update(overrides)
    return evidence


def _path(tmp_path: Path) -> Path:
    path = tmp_path / "active-ledger.json"
    active.initialize_ledger(path, created_at=NOW)
    return path


def _register(path: Path, revision: int = 0, **overrides: object):
    evidence = _evidence(**overrides.pop("evidence_overrides", {}))
    return registration.register_published_signal(
        active_ledger_path=path,
        expected_active_ledger_revision=revision,
        publication_evidence=evidence,
        reservation_transition_id=overrides.pop("transition_id", "reserve-one"),
        timestamp=overrides.pop("timestamp", NOW),
    )


def test_valid_registration_persists_pending_signal_transaction_and_transition(tmp_path):
    result = _register(_path(tmp_path))
    assert result.result == registration.PUBLISHED_SIGNAL_REGISTERED
    assert result.current_state == active.PUBLISHED_PENDING_ENTRY
    assert result.registration_applied is True


@pytest.mark.parametrize("mode", (active.SWING, active.INTRADAY, active.SCALP))
def test_each_mode_and_symbol_are_preserved(tmp_path, mode):
    path = _path(tmp_path)
    result = _register(path, evidence_overrides={"mode": mode, "publication_payload": {"signal_id": "signal-one", "mode": mode, "symbol": "ETHUSDT"}})
    document = active.load_ledger(path)
    record = document["signals"][result.signal_id]
    assert (result.mode, result.symbol, record["mode"], record["symbol"]) == (mode, "ETHUSDT", mode, "ETHUSDT")


def test_canonical_identity_fields_and_transaction_derivation_are_persisted(tmp_path):
    path = _path(tmp_path)
    result = _register(path)
    document = active.load_ledger(path)
    transaction = document["publication_transactions"][result.reservation_transaction_id]
    transition = document["transitions"]["reserve-one"]
    assert result.reservation_transaction_id == registration._derive_reservation_transaction_id(
        signal_id="signal-one", delivery_id="delivery-one", mode=active.SWING,
        symbol="BTCUSDT", published_at=NOW, source_payload_hash=SOURCE_HASH,
        publication_payload_hash=PUBLICATION_HASH,
    )
    assert transaction["state"] == active.OCCUPANCY_COMMITTED
    assert transition["operation"] == "RESERVE"
    assert transaction["reservation_transition_id"] == result.reservation_transition_id
    record = document["signals"]["signal-one"]
    assert record["delivery_id"] == transaction["delivery_id"] == "delivery-one"
    assert record["source_payload_hash"] == transaction["source_payload_hash"] == SOURCE_HASH
    assert record["publication_payload_hash"] == transaction["publication_payload_hash"] == PUBLICATION_HASH
    assert result.signal_payload_hash == result.source_payload_hash == SOURCE_HASH


def test_replay_is_idempotent_and_preserves_revision_and_records(tmp_path):
    path = _path(tmp_path)
    created = _register(path)
    replay = _register(path, revision=created.active_ledger_revision)
    document = active.load_ledger(path)
    assert replay.result == registration.PUBLISHED_SIGNAL_REGISTRATION_REPLAYED
    assert replay.replay is True and replay.registration_applied is False
    assert document["ledger_revision"] == created.active_ledger_revision
    assert len(document["signals"]) == len(document["transitions"]) == len(document["publication_transactions"]) == 1


@pytest.mark.parametrize(
    ("evidence_overrides", "expected"),
    (
        ({"publication_payload": {"signal_id": "signal-one", "mode": active.SWING, "symbol": "ETHUSDT"}}, registration.SIGNAL_IDENTITY_CONFLICT),
        ({"delivery_id": "delivery-other"}, registration.SIGNAL_IDENTITY_CONFLICT),
    ),
)
def test_conflicting_signal_evidence_fails_closed(tmp_path, evidence_overrides, expected):
    path = _path(tmp_path)
    created = _register(path)
    result = _register(path, revision=created.active_ledger_revision, evidence_overrides=evidence_overrides)
    assert result.result == expected


def test_same_transaction_with_changed_transition_is_reservation_conflict(tmp_path):
    path = _path(tmp_path)
    created = _register(path)
    result = _register(path, revision=created.active_ledger_revision, transition_id="reserve-other")
    assert result.result == registration.RESERVATION_IDENTITY_CONFLICT


def test_same_derived_transaction_with_changed_immutable_evidence_is_signal_conflict(tmp_path, monkeypatch):
    path = _path(tmp_path)
    monkeypatch.setattr(registration, "_transaction_id", lambda _context: "fixed-transaction")
    created = _register(path)
    before = active.load_ledger(path)
    result = _register(
        path,
        revision=created.active_ledger_revision,
        evidence_overrides={"publication_payload_hash": "d" * 64},
    )
    after = active.load_ledger(path)
    assert result.result == result.reason == registration.SIGNAL_IDENTITY_CONFLICT
    assert result.publication_confirmed is True
    assert result.registration_applied is False
    assert result.partial_success is False and result.replay is False
    assert after == before
    assert len(after["signals"]) == len(after["transitions"]) == len(after["publication_transactions"]) == 1


def test_pure_inspection_with_equivalent_signal_and_conflicting_transaction_is_transaction_conflict(tmp_path):
    path = _path(tmp_path)
    created = _register(path)
    snapshot = active.load_ledger(path)
    transaction = snapshot["publication_transactions"][created.reservation_transaction_id]
    transaction["state"] = active.PREPARED
    transaction["source_payload_hash"] = "d" * 64
    before = copy.deepcopy(snapshot)
    result = registration.inspect_published_signal_registration(
        active_ledger=snapshot,
        publication_evidence=_evidence(),
        reservation_transition_id="reserve-one",
        timestamp=NOW,
    )
    signal = snapshot["signals"]["signal-one"]
    assert result.result == result.reason == registration.TRANSACTION_IDENTITY_CONFLICT
    assert result.publication_confirmed is True
    assert result.registration_applied is False
    assert result.partial_success is False and result.replay is False
    assert signal["source_payload_hash"] == SOURCE_HASH
    assert transaction["reservation_transition_id"] == "reserve-one"
    assert snapshot == before


def test_existing_transition_for_different_registration_is_a_reservation_conflict(tmp_path):
    path = _path(tmp_path)
    created = _register(path)
    result = _register(
        path,
        revision=created.active_ledger_revision,
        transition_id="reserve-one",
        evidence_overrides={
            "signal_id": "signal-two",
            "delivery_id": "delivery-two",
            "publication_payload": {"signal_id": "signal-two", "mode": active.SWING, "symbol": "BTCUSDT"},
        },
    )
    assert result.result == registration.RESERVATION_IDENTITY_CONFLICT


def test_stale_revision_is_specific_and_does_not_mutate(tmp_path):
    path = _path(tmp_path)
    result = _register(path, revision=1)
    assert result.result == registration.ACTIVE_REVISION_CONFLICT
    assert active.load_ledger(path)["ledger_revision"] == 0


@pytest.mark.parametrize(
    "evidence_overrides",
    (
        {"delivery_state": "DELIVERY_FAILED"},
        {"signal_id": ""},
        {"delivery_id": ""},
        {"mode": "swing"},
        {"published_at": "not-a-time"},
        {"source_payload_hash": "bad"},
        {"publication_payload_hash": "bad"},
        {"publication_payload": {}},
    ),
)
def test_malformed_evidence_is_rejected_before_mutation(tmp_path, evidence_overrides):
    path = _path(tmp_path)
    result = _register(path, evidence_overrides=evidence_overrides)
    assert result.result == registration.INVALID_PUBLICATION_EVIDENCE
    assert active.load_ledger(path)["ledger_revision"] == 0


def test_content_hash_is_optional_reporting_metadata(tmp_path):
    path = _path(tmp_path)
    with_hash = _register(path)
    other = _path(tmp_path / "other")
    without_hash = _register(other, evidence_overrides={"content_hash": None})
    assert with_hash.publication_identity_hash == CONTENT_HASH
    assert without_hash.publication_identity_hash is None
    assert without_hash.signal_payload_hash == SOURCE_HASH


def test_lock_and_atomic_failures_return_confirmed_partial_success(tmp_path, monkeypatch):
    path = _path(tmp_path)
    monkeypatch.setattr(active, "_LOCK_ATTEMPTS", 0)
    locked = _register(path)
    assert (locked.result, locked.reason, locked.partial_success) == (
        registration.PUBLICATION_SUCCEEDED_REGISTRATION_PENDING,
        registration.ACTIVE_LOCK_UNAVAILABLE,
        True,
    )
    monkeypatch.undo()
    monkeypatch.setattr(active, "_atomic_write", lambda *_: (_ for _ in ()).throw(active.ActiveSignalLedgerError(active.ATOMIC_WRITE_FAILED)))
    failed = _register(path)
    assert (failed.result, failed.reason, failed.partial_success) == (
        registration.PUBLICATION_SUCCEEDED_REGISTRATION_PENDING,
        registration.ACTIVE_PERSISTENCE_FAILURE,
        True,
    )
    assert failed.signal_id == "signal-one" and failed.registration_applied is False


def test_restart_repair_is_idempotent_and_never_changes_publication(tmp_path):
    path = _path(tmp_path)
    repaired = registration.reconcile_published_signal_registration(
        active_ledger_path=path, expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=LATER,
    )
    again = registration.reconcile_published_signal_registration(
        active_ledger_path=path, expected_active_ledger_revision=repaired.active_ledger_revision,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=LATER,
    )
    assert repaired.result == registration.PUBLISHED_SIGNAL_REGISTERED
    assert again.result == registration.REGISTRATION_ALREADY_PRESENT
    assert active.load_ledger(path)["ledger_revision"] == repaired.active_ledger_revision


def test_pure_inspection_reports_present_pending_and_identity_conflicts(tmp_path):
    path = _path(tmp_path)
    before = active.load_ledger(path)
    pending = registration.inspect_published_signal_registration(
        active_ledger=before, publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    created = _register(path)
    present = registration.inspect_published_signal_registration(
        active_ledger=active.load_ledger(path), publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    conflict = registration.inspect_published_signal_registration(
        active_ledger=active.load_ledger(path),
        publication_evidence=_evidence(publication_payload={"signal_id": "signal-one", "mode": active.SWING, "symbol": "ETHUSDT"}),
        reservation_transition_id="reserve-one", timestamp=NOW,
    )
    assert (pending.result, present.result, conflict.result) == (
        registration.NO_REGISTRATION,
        registration.REGISTRATION_ALREADY_PRESENT,
        registration.SIGNAL_IDENTITY_CONFLICT,
    )
    assert active.load_ledger(path)["ledger_revision"] == created.active_ledger_revision


def test_pure_inspection_detects_transaction_and_transition_conflicts(tmp_path):
    path = _path(tmp_path)
    created = _register(path)
    ledger = active.load_ledger(path)
    transaction = registration.inspect_published_signal_registration(
        active_ledger=ledger, publication_evidence=_evidence(), reservation_transition_id="reserve-one-other", timestamp=NOW,
    )
    transition = registration.inspect_published_signal_registration(
        active_ledger=ledger, publication_evidence=_evidence(), reservation_transition_id="reserve-other", timestamp=NOW,
    )
    assert transaction.result == registration.RESERVATION_IDENTITY_CONFLICT
    assert transition.result == registration.RESERVATION_IDENTITY_CONFLICT
    assert created.active_ledger_revision == ledger["ledger_revision"]


def test_pure_inspection_rejects_malformed_ledger_without_mutation(tmp_path):
    path = _path(tmp_path)
    snapshot = active.load_ledger(path)
    before = copy.deepcopy(snapshot)
    result = registration.inspect_published_signal_registration(
        active_ledger={"invalid": True}, publication_evidence=_evidence(),
        reservation_transition_id="reserve-one", timestamp=NOW,
    )
    assert result.result == registration.FAIL_CLOSED
    assert active.load_ledger(path) == before


def test_result_schema_boolean_consistency_and_sanitization(tmp_path):
    result = _register(_path(tmp_path))
    assert tuple(result.to_dict()) == tuple(registration.PassivePublishedSignalRegistrationResultV1.__dataclass_fields__)
    assert result.publication_confirmed and result.registration_applied
    bad = registration.register_published_signal(
        active_ledger_path=tmp_path / "not-disclosed.json", expected_active_ledger_revision=0,
        publication_evidence=_evidence(), reservation_transition_id="reserve-one", timestamp=NOW,
    )
    assert bad.result == registration.PUBLICATION_SUCCEEDED_REGISTRATION_PENDING
    assert "/" not in (bad.reason or "")


def test_source_has_no_operational_import_or_execution_surface():
    source = (Path(__file__).parents[1] / "engine" / "passive_published_signal_registration_v1.py").read_text(encoding="utf-8")
    forbidden = (
        "run_" + "production_signal_service", "engine.telegram", "engine.scanner",
        "master" + "_engine", "quota" + "_slot_worker", "stateful" + "_worker",
        "evaluate_" + "refill_dispatch", "claim_" + "refill_request", "subprocess",
    )
    assert not any(item in source for item in forbidden)
