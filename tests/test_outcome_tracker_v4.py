import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

import engine.outcome_tracker_v4 as tracker


INVOCATION_A = "a" * 32
INVOCATION_B = "b" * 32
CAPTURED_AT = "2026-07-28T09:00:00"


def _row(*, symbol="BTC/USDT", score=91):
    return {
        "symbol": symbol,
        "reference_price": 100.0,
        "reference_candle_at": "2026-07-28T08:59:00Z",
        "python_score": score,
        "validation_adjustment": 0,
        "final_rank_score": score,
        "trend": "UP",
        "bos": True,
        "choch": False,
        "volume_ratio": 1.5,
        "volume_class": "HIGH",
        "oi_change_pct": 2.0,
        "oi_class": "RISING",
        "participation": "CONFIRMED",
        "ai_validation": {
            "status": "APPROVED",
            "false_breakout_risk": "LOW",
            "confluence": "HIGH",
            "reason_code": "PASS",
        },
    }


@pytest.fixture
def outcome_root(monkeypatch, tmp_path):
    root = tmp_path / "outcomes"
    monkeypatch.setattr(tracker, "OUTCOME_DIRECTORY", root)
    return root


def _save(rows, invocation_id):
    return tracker.save_outcome_snapshot(
        rows,
        outcome_invocation_id=invocation_id,
        captured_at=CAPTURED_AT,
    )


def test_same_second_distinct_invocation_ids_publish_distinct_paths_without_overwrite(
    outcome_root,
):
    first = _save([_row(symbol="BTC/USDT")], INVOCATION_A)
    first_bytes = first.read_bytes()
    second = _save([_row(symbol="ETH/USDT")], INVOCATION_B)

    assert first != second
    assert first.name == f"outcome_entry_v4_{INVOCATION_A}.json"
    assert second.name == f"outcome_entry_v4_{INVOCATION_B}.json"
    assert first.read_bytes() == first_bytes
    assert json.loads(first.read_text())["candidates"][0]["symbol"] == "BTC/USDT"
    assert json.loads(second.read_text())["candidates"][0]["symbol"] == "ETH/USDT"
    assert len(list(outcome_root.glob("outcome_entry_v4_*.json"))) == 2


def test_filenames_bind_exactly_to_validated_invocation_identity(outcome_root):
    path = _save([_row()], INVOCATION_A)

    assert path.parent == outcome_root
    assert path.name == f"outcome_entry_v4_{INVOCATION_A}.json"
    assert CAPTURED_AT not in path.name


def test_existing_identical_canonical_bytes_returns_existing_path(outcome_root):
    first = _save([_row()], INVOCATION_A)
    first_stat = first.stat()
    first_bytes = first.read_bytes()

    second = _save([_row()], INVOCATION_A)

    assert second == first
    assert second.stat().st_ino == first_stat.st_ino
    assert second.read_bytes() == first_bytes
    assert len(list(outcome_root.glob("outcome_entry_v4_*.json"))) == 1


def test_existing_different_canonical_bytes_fails_closed_without_replacement(
    outcome_root,
):
    path = _save([_row()], INVOCATION_A)
    committed = path.read_bytes()

    with pytest.raises(
        tracker.OutcomeSnapshotConflictError,
        match="OUTCOME_ARTIFACT_CONFLICT",
    ):
        _save([_row(score=92)], INVOCATION_A)

    assert path.read_bytes() == committed
    assert len(list(outcome_root.glob("outcome_entry_v4_*.json"))) == 1
    assert list(outcome_root.glob(".*.tmp")) == []


def test_concurrent_same_id_writer_race_commits_once_and_reuses_identical_bytes(
    outcome_root,
    monkeypatch,
):
    barrier = Barrier(2)
    real_link = tracker.os.link

    def synchronized_link(*args, **kwargs):
        barrier.wait()
        return real_link(*args, **kwargs)

    monkeypatch.setattr(tracker.os, "link", synchronized_link)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_save, [_row()], INVOCATION_A)
            for _ in range(2)
        ]
        paths = [future.result() for future in futures]

    assert paths[0] == paths[1]
    assert len(list(outcome_root.glob("outcome_entry_v4_*.json"))) == 1
    assert list(outcome_root.glob(".*.tmp")) == []


def test_concurrent_same_id_different_bytes_commits_once_and_conflicts_once(
    outcome_root,
    monkeypatch,
):
    barrier = Barrier(2)
    real_link = tracker.os.link

    def synchronized_link(*args, **kwargs):
        barrier.wait()
        return real_link(*args, **kwargs)

    monkeypatch.setattr(tracker.os, "link", synchronized_link)

    def attempt(rows):
        try:
            return _save(rows, INVOCATION_A)
        except tracker.OutcomeSnapshotConflictError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                attempt,
                ([_row(score=91)], [_row(score=92)]),
            )
        )

    assert sum(isinstance(value, Path) for value in results) == 1
    assert sum(
        isinstance(value, tracker.OutcomeSnapshotConflictError)
        for value in results
    ) == 1
    assert len(list(outcome_root.glob("outcome_entry_v4_*.json"))) == 1
    assert list(outcome_root.glob(".*.tmp")) == []


def test_temporary_write_or_fsync_failure_exposes_no_final_path(
    outcome_root,
    monkeypatch,
):
    def fail_fsync(_fd):
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(tracker.os, "fsync", fail_fsync)

    with pytest.raises(
        tracker.OutcomeSnapshotPersistenceError,
        match="OUTCOME_ARTIFACT_TEMPORARY_WRITE_FAILED",
    ):
        _save([_row()], INVOCATION_A)

    assert not (
        outcome_root / f"outcome_entry_v4_{INVOCATION_A}.json"
    ).exists()
    assert list(outcome_root.glob(".*.tmp")) == []


def test_final_link_collision_never_replaces_existing_bytes(outcome_root):
    outcome_root.mkdir()
    path = outcome_root / f"outcome_entry_v4_{INVOCATION_A}.json"
    path.write_bytes(b"committed-sentinel")

    with pytest.raises(
        tracker.OutcomeSnapshotConflictError,
        match="OUTCOME_ARTIFACT_CONFLICT",
    ):
        _save([_row()], INVOCATION_A)

    assert path.read_bytes() == b"committed-sentinel"
    assert list(outcome_root.glob(".*.tmp")) == []


@pytest.mark.parametrize(
    "invalid_identity",
    [
        None,
        "",
        "a" * 31,
        "a" * 33,
        "A" * 32,
        "g" * 32,
        "../" + "a" * 29,
        "a/b" + "c" * 29,
        " " + "a" * 31,
        123,
        False,
    ],
)
def test_invalid_identity_and_path_traversal_forms_fail_before_filesystem_mutation(
    outcome_root,
    invalid_identity,
):
    with pytest.raises(tracker.OutcomeSnapshotIdentityError):
        tracker.save_outcome_snapshot(
            [_row()],
            outcome_invocation_id=invalid_identity,
            captured_at=CAPTURED_AT,
        )

    assert not outcome_root.exists()
