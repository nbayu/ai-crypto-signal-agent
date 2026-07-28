import importlib
import json
from datetime import datetime
from pathlib import Path

import pytest


def test_run_master_engine_worker_records_started_then_completed(tmp_path):
    import engine.stateful_worker_v4 as worker

    calls = []
    now_values = iter(
        [
            datetime(2026, 7, 14, 15, 30, 0),
            datetime(2026, 7, 14, 15, 30, 5),
        ]
    )

    def now_provider():
        return next(now_values)

    def run_id_provider():
        return "run-001"

    def fake_master_engine(*, outcome_invocation_id):
        assert len(outcome_invocation_id) == 32
        calls.append("master_engine")
        return {
            "snapshot_path": Path("validated.json"),
            "outcome_path": Path("outcome.json"),
            "watchlist_path": Path("raw_top5.json"),
            "evidence_path": Path("manifest.json"),
            "delivery_out": {
                "delivery_artifact_path": Path("pre_delivery.json"),
                "tradingview_watchlist_path": Path(
                    "tradingview_watchlist.txt"
                ),
                "pine_bridge_artifact_path": Path("pine_bridge.json"),
                "pine_delivery_payload_path": Path("payload.txt"),
            },
        }

    state_path = tmp_path / "master_engine_v4_latest.json"

    result = worker.run_master_engine_worker_v4(
        master_engine=fake_master_engine,
        state_path=state_path,
        now_provider=now_provider,
        run_id_provider=run_id_provider,
    )

    assert calls == ["master_engine"]
    assert result["state_path"] == state_path
    assert result["run"]["evidence_path"] == Path("manifest.json")

    saved = json.loads(state_path.read_text())

    assert saved == {
        "schema_version": 1,
        "worker_name": "master_engine_v4",
        "run_id": "run-001",
        "state": "COMPLETED",
        "started_at": "2026-07-14T15:30:00",
        "completed_at": "2026-07-14T15:30:05",
        "failed_at": None,
        "error": None,
        "artifacts": {
            "snapshot_path": "validated.json",
            "outcome_path": "outcome.json",
            "watchlist_path": "raw_top5.json",
            "evidence_path": "manifest.json",
            "delivery_artifact_path": "pre_delivery.json",
            "tradingview_watchlist_path": "tradingview_watchlist.txt",
            "pine_bridge_artifact_path": "pine_bridge.json",
            "pine_delivery_payload_path": "payload.txt",
        },
    }


def test_run_master_engine_worker_records_failed_and_reraises(tmp_path):
    import engine.stateful_worker_v4 as worker

    now_values = iter(
        [
            datetime(2026, 7, 14, 15, 31, 0),
            datetime(2026, 7, 14, 15, 31, 3),
        ]
    )

    def now_provider():
        return next(now_values)

    def run_id_provider():
        return "run-failed"

    def failing_master_engine(*, outcome_invocation_id):
        assert len(outcome_invocation_id) == 32
        raise RuntimeError("boom")

    state_path = tmp_path / "master_engine_v4_latest.json"

    with pytest.raises(RuntimeError, match="boom"):
        worker.run_master_engine_worker_v4(
            master_engine=failing_master_engine,
            state_path=state_path,
            now_provider=now_provider,
            run_id_provider=run_id_provider,
        )

    saved = json.loads(state_path.read_text())

    assert saved == {
        "schema_version": 1,
        "worker_name": "master_engine_v4",
        "run_id": "run-failed",
        "state": "FAILED",
        "started_at": "2026-07-14T15:31:00",
        "completed_at": None,
        "failed_at": "2026-07-14T15:31:03",
        "error": {
            "type": "RuntimeError",
            "message": "boom",
        },
        "artifacts": {},
    }


def test_write_worker_state_atomic_replaces_target(tmp_path):
    import engine.stateful_worker_v4 as worker

    state_path = tmp_path / "state.json"
    state_path.write_text("old")

    event = {
        "schema_version": 1,
        "worker_name": "master_engine_v4",
        "run_id": "run-atomic",
        "state": "STARTED",
        "started_at": "2026-07-14T15:32:00",
        "completed_at": None,
        "failed_at": None,
        "error": None,
        "artifacts": {},
    }

    path = worker.write_worker_state_atomic(event, state_path)

    assert path == state_path
    assert json.loads(state_path.read_text()) == event
    assert not (tmp_path / "state.json.tmp").exists()


def test_importing_stateful_worker_has_no_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    module = importlib.import_module("engine.stateful_worker_v4")

    assert hasattr(module, "run_master_engine_worker_v4")
    assert not Path("data").exists()


def test_worker_generates_outcome_invocation_identity_once_and_passes_to_master(
    tmp_path,
):
    import engine.stateful_worker_v4 as worker

    provider_calls = []
    master_calls = []
    identity = "c" * 32
    now_values = iter(
        [
            datetime(2026, 7, 28, 9, 0, 0),
            datetime(2026, 7, 28, 9, 0, 1),
        ]
    )

    def provider():
        provider_calls.append(True)
        return identity

    def master_engine(*, outcome_invocation_id):
        master_calls.append(outcome_invocation_id)
        return {"delivery_out": {}}

    worker.run_master_engine_worker_v4(
        master_engine=master_engine,
        state_path=tmp_path / "worker.json",
        now_provider=lambda: next(now_values),
        run_id_provider=lambda: "worker-run-id",
        outcome_invocation_id_provider=provider,
    )

    assert provider_calls == [True]
    assert master_calls == [identity]
