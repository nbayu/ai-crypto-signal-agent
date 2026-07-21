"""Focused contract tests for the passive Style Refill Request Ledger v1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import engine.style_refill_request_ledger_v1 as refill


NOW = "2026-07-21T00:00:00Z"
LATER = "2026-07-21T00:01:00Z"
LATERER = "2026-07-21T00:02:00Z"


def _path(tmp_path):
    return tmp_path / "style-refill.json"


def _transition(mode=refill.SWING, suffix="1"):
    return {
        "terminal_transition_id": f"terminal-{suffix}",
        "signal_id": f"signal-{suffix}",
        "mode": mode,
        "terminal_state": "CLOSED_PROFIT",
        "source_ledger_revision": 7,
        "timestamp": NOW,
    }


def _identity_values(**overrides):
    values = _transition()
    values.update(overrides)
    return {key: values[key] for key in ("terminal_transition_id", "signal_id", "mode", "terminal_state")}


def _reconcile(path, revision=None, **overrides):
    suffix = overrides.pop("suffix", "1")
    values = _transition(suffix=suffix)
    values.update(overrides)
    if revision is not None:
        values["expected_revision"] = revision
    return refill.reconcile_terminal_transition(path, **values)


def _error(code, operation):
    with pytest.raises(refill.StyleRefillRequestLedgerError) as caught:
        operation()
    assert caught.value.reason_code == code
    assert "secret" not in str(caught.value).casefold()


def _request_id(ledger):
    return next(iter(ledger["requests"]))


def _snapshot(mode, remaining):
    values = {item: 0 for item in refill.MODES}
    values[mode] = remaining
    return {"remaining_by_mode": values}


def test_missing_file_returns_caller_timestamped_empty_ledger(tmp_path):
    ledger = refill.load_refill_ledger(_path(tmp_path), created_at=NOW)
    assert ledger["schema"] == refill.SCHEMA and ledger["ledger_revision"] == 0
    assert ledger["requests"] == {} and ledger["source_transitions"] == {}


def test_identity_is_deterministic_and_uses_canonical_key_order():
    first = refill.derive_refill_request_id(**_identity_values())
    values = _identity_values()
    reordered = {key: values[key] for key in reversed(tuple(values))}
    second = refill.derive_refill_request_id(**reordered)
    assert first == second and len(first) == 64


@pytest.mark.parametrize("bad_mode", ("", "OTHER", None))
def test_invalid_mode_is_rejected(bad_mode):
    _error("INVALID_MODE", lambda: refill.derive_refill_request_id(**_identity_values(mode=bad_mode)))


@pytest.mark.parametrize("state", ("", "ENTRY_ACTIVE", None))
def test_invalid_terminal_state_is_rejected(state):
    _error("INVALID_TERMINAL_STATE", lambda: refill.derive_refill_request_id(**_identity_values(terminal_state=state)))


def test_one_terminal_transition_creates_one_pending_request_and_replay_is_idempotent(tmp_path):
    path = _path(tmp_path)
    created = _reconcile(path)
    request_id = _request_id(created)
    assert created["requests"][request_id]["status"] == refill.PENDING
    replay = _reconcile(path, revision=created["ledger_revision"])
    assert replay == created


def test_non_equivalent_source_transition_and_revision_conflicts_fail_closed(tmp_path):
    path = _path(tmp_path)
    created = _reconcile(path)
    _error("REQUEST_ID_COLLISION", lambda: _reconcile(path, revision=created["ledger_revision"], signal_id="other"))
    _error("REVISION_CONFLICT", lambda: _reconcile(path, revision=0, suffix="other"))


def test_revision_increments_once_and_inspection_derives_mode_counts(tmp_path):
    path = _path(tmp_path)
    ledger = _reconcile(path)
    ledger = _reconcile(path, ledger["ledger_revision"], mode=refill.INTRADAY, suffix="two")
    inspection = refill.inspect_refill_requests(ledger)
    assert ledger["ledger_revision"] == 2 and inspection["total_requests"] == 2
    assert inspection["pending_by_mode"] == {refill.SWING: 1, refill.INTRADAY: 1, refill.SCALP: 0}


def test_eligibility_is_mode_isolated_and_never_exceeds_one_unit(tmp_path):
    ledger = _reconcile(_path(tmp_path), mode=refill.SCALP)
    request_id = _request_id(ledger)
    assert refill.evaluate_dispatch_eligibility(ledger, refill_request_id=request_id, capacity_snapshot=_snapshot(refill.SCALP, 0))["status"] == refill.STYLE_FULL
    eligible = refill.evaluate_dispatch_eligibility(ledger, refill_request_id=request_id, capacity_snapshot=_snapshot(refill.SCALP, 3))
    assert eligible == {"status": "ELIGIBLE_ONE_SCAN_UNIT", "scan_units": 1, "mode": refill.SCALP}


def test_invalid_capacity_snapshot_fails_closed(tmp_path):
    ledger = _reconcile(_path(tmp_path))
    _error("INVALID_CAPACITY_SNAPSHOT", lambda: refill.evaluate_dispatch_eligibility(ledger, refill_request_id=_request_id(ledger), capacity_snapshot={}))


def test_claim_is_idempotent_and_increments_attempt_once(tmp_path):
    path = _path(tmp_path)
    ledger = _reconcile(path)
    request_id = _request_id(ledger)
    claimed = refill.claim_refill_request(path, refill_request_id=request_id, claim_token="claim-a", timestamp=LATER, expected_revision=ledger["ledger_revision"])
    assert claimed["requests"][request_id]["attempt_count"] == 1
    replay = refill.claim_refill_request(path, refill_request_id=request_id, claim_token="claim-a", timestamp=LATER, expected_revision=claimed["ledger_revision"])
    assert replay == claimed
    _error("CLAIM_TOKEN_CONFLICT", lambda: refill.claim_refill_request(path, refill_request_id=request_id, claim_token="claim-b", timestamp=LATER, expected_revision=claimed["ledger_revision"]))


@pytest.mark.parametrize("outcome,status", ((refill.DISPATCHED, refill.COMPLETED), (refill.STYLE_FULL, refill.COMPLETED), (refill.CANCELLED_OUTCOME, refill.CANCELLED)))
def test_completion_outcomes_are_idempotent_and_prevent_reclaim(tmp_path, outcome, status):
    path = _path(tmp_path)
    ledger = _reconcile(path)
    request_id = _request_id(ledger)
    claimed = refill.claim_refill_request(path, refill_request_id=request_id, claim_token="claim", timestamp=LATER, expected_revision=ledger["ledger_revision"])
    completed = refill.complete_refill_request(path, refill_request_id=request_id, claim_token="claim", completion_outcome=outcome, timestamp=LATERER, expected_revision=claimed["ledger_revision"])
    assert completed["requests"][request_id]["status"] == status
    assert refill.complete_refill_request(path, refill_request_id=request_id, claim_token="claim", completion_outcome=outcome, timestamp=LATERER, expected_revision=completed["ledger_revision"]) == completed
    _error("REQUEST_NOT_PENDING", lambda: refill.claim_refill_request(path, refill_request_id=request_id, claim_token="again", timestamp=LATERER, expected_revision=completed["ledger_revision"]))


def test_interrupted_claim_recovery_retains_attempt_count_and_reloads(tmp_path):
    path = _path(tmp_path)
    ledger = _reconcile(path)
    request_id = _request_id(ledger)
    claimed = refill.claim_refill_request(path, refill_request_id=request_id, claim_token="claim", timestamp=NOW, expected_revision=ledger["ledger_revision"])
    recovered = refill.recover_interrupted_claims(path, recovery_before_timestamp=LATER, timestamp=LATERER, expected_revision=claimed["ledger_revision"])
    assert recovered["recovered_request_ids"] == (request_id,)
    assert recovered["ledger"]["requests"][request_id]["attempt_count"] == 1
    assert refill.load_refill_ledger(path) == recovered["ledger"]
    no_op = refill.recover_interrupted_claims(path, recovery_before_timestamp=LATER, timestamp=LATERER, expected_revision=recovered["ledger"]["ledger_revision"])
    assert no_op["recovered_request_ids"] == ()


def test_malformed_schema_and_identity_are_rejected(tmp_path):
    path = _path(tmp_path)
    path.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
    _error("INVALID_LEDGER", lambda: refill.load_refill_ledger(path))
    ledger = _reconcile(tmp_path / "valid.json")
    request_id = _request_id(ledger)
    ledger["requests"][request_id]["refill_request_id"] = "0" * 64
    (tmp_path / "valid.json").write_text(json.dumps(ledger), encoding="utf-8")
    _error("INVALID_LEDGER", lambda: refill.load_refill_ledger(tmp_path / "valid.json"))


def test_atomic_write_and_lock_failures_are_sanitized(monkeypatch, tmp_path):
    path = _path(tmp_path)
    monkeypatch.setattr(refill, "_write_atomic", lambda *_: (_ for _ in ()).throw(refill.StyleRefillRequestLedgerError("PERSISTENCE_FAILURE")))
    _error("PERSISTENCE_FAILURE", lambda: _reconcile(path))
    monkeypatch.undo()
    monkeypatch.setattr(refill, "_LOCK_ATTEMPTS", 0)
    _error("LOCK_UNAVAILABLE", lambda: _reconcile(path))


def test_source_isolated_from_external_execution_surfaces():
    source = (Path(__file__).parents[1] / "engine" / "style_refill_request_ledger_v1.py").read_text(encoding="utf-8")
    forbidden = ("telegram", "scanner", "provider", "systemd", "requests", "httpx", "urllib", "socket")
    assert not any(f"import {item}" in source or f"from {item}" in source for item in forbidden)
