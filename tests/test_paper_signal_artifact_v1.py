import copy
import json
import os
from pathlib import Path

import pytest

from engine.paper_signal_artifact_v1 import (
    PAPER_EVALUATION_DIRECTORY,
    PAPER_OBSERVATION_DIRECTORY,
    PAPER_PROGRESS_DIRECTORY,
    PaperSignalArtifactError,
    publish_evaluation_cycle_artifact,
    publish_observation_artifact,
    publish_progress_artifact,
)


def observation_payload(**overrides):
    value = {
        "schema_version": 1,
        "schema_name": "paper-signal-observation",
        "paper_observation_id": "PSO-" + ("a" * 64),
        "signal_id": "SCP-20260715-001",
        "mode": "SCALP",
        "classification": "PAPER_SIGNAL",
        "execution_boundary": "LIVE_MARKET_OBSERVATION_NO_CAPITAL",
        "capital_exposure": "NONE",
        "order_execution": "PROHIBITED",
        "position_authority": "TELEGRAM_USER_REPORT",
        "source_publication_ref": {
            "signal_id": "SCP-20260715-001",
            "delivery_id": "delivery-001",
            "mode": "SCALP",
            "published_at": "2026-07-15T12:00:00Z",
            "source_payload_hash": "b" * 64,
        },
        "strategy_version": "master-engine-v2",
        "orchestration_policy_version": "signal-agent-blueprint-v1",
        "observer_version": "paper-observer-v1",
        "signal_geometry": {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_zone": {"min": 100.0, "max": 102.0},
            "stop_loss": 95.0,
            "take_profit": {"tp1": 110.0, "tp2": 120.0},
            "valid_until": "2026-07-15T13:00:00Z",
        },
        "observed_from": "2026-07-15T12:00:00Z",
        "observed_until": "2026-07-15T12:10:00Z",
        "observation_state": "ENTRY_ZONE_TOUCHED",
        "fill_observation_status": "ENTRY_ZONE_TOUCHED",
        "entry_touched_at": "2026-07-15T12:05:00Z",
        "entry_touch_candle": None,
        "acknowledgment": None,
        "cancellation": None,
        "terminal_reason": "ENTRY_ZONE_TOUCHED",
        "evidence": {
            "signal_geometry_hash": "c" * 64,
            "closed_candle_hashes": [],
            "observation_event_hashes": [],
        },
        "created_at": "2026-07-15T12:10:00Z",
        "content_hash": "d" * 64,
    }
    value.update(overrides)
    return value


def evaluation_cycle_payload(**overrides):
    value = {
        "schema_version": 1,
        "source_evaluation_id": "eval-001",
        "mode": "SCALP",
        "evaluated_at": "2026-07-15T12:00:00Z",
        "official_alert_signal_ids": [],
        "rejection_reasons": {"REJECT_NO_TRIGGER": 2},
        "content_hash": "e" * 64,
    }
    value.update(overrides)
    return value


def progress_payload(**overrides):
    empty = {
        "evaluation_cycles": 0,
        "official_alert_cycles": 0,
        "no_trade_cycles": 0,
        "no_trade_coverage_ratio": None,
        "top_rejection_reasons": {},
    }
    value = {
        "schema_version": 1,
        "schema_name": "paper-signal-progress",
        "classification": "PAPER_SIGNAL",
        "execution_boundary": "LIVE_MARKET_OBSERVATION_NO_CAPITAL",
        "enabled_modes": ["SCALP"],
        "official_signal_total": 1,
        "official_signal_count_by_mode": {"SWING": 0, "INTRADAY": 0, "SCALP": 1},
        "minimum_required_total": 100,
        "minimum_required_per_enabled_mode": 30,
        "evaluation_coverage_by_mode": {
            "SWING": copy.deepcopy(empty),
            "INTRADAY": copy.deepcopy(empty),
            "SCALP": {
                "evaluation_cycles": 1,
                "official_alert_cycles": 0,
                "no_trade_cycles": 1,
                "no_trade_coverage_ratio": 1.0,
                "top_rejection_reasons": {"REJECT_NO_TRIGGER": 2},
            },
        },
        "observation_state_distribution": {"ENTRY_ZONE_TOUCHED": 1},
        "acknowledgment_summary": {
            "official_signal_count": 1,
            "acknowledged_signal_count": 0,
            "acknowledgment_coverage_ratio": 0.0,
            "latency_ms": {"minimum": None, "maximum": None, "mean": None},
        },
        "critical_lifecycle_defect_count": 0,
        "promotion_readiness": False,
        "generated_at": "2026-07-15T13:00:00Z",
        "content_hash": "f" * 64,
    }
    value.update(overrides)
    return value


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_frozen_artifact_directories():
    assert PAPER_OBSERVATION_DIRECTORY == "observations"
    assert PAPER_EVALUATION_DIRECTORY == "evaluation_cycles"
    assert PAPER_PROGRESS_DIRECTORY == "progress"


def test_publish_observation_to_authorized_root(tmp_path):
    payload = observation_payload()
    path = publish_observation_artifact(paper_root=tmp_path, payload=payload)
    assert path.parent == tmp_path / "observations"
    assert path.name == "PSO-" + ("a" * 64) + ".json"
    assert read_json(path) == payload


def test_publish_evaluation_cycle_to_authorized_root(tmp_path):
    payload = evaluation_cycle_payload()
    path = publish_evaluation_cycle_artifact(paper_root=tmp_path, payload=payload)
    assert path.parent == tmp_path / "evaluation_cycles"
    assert path.name == "SCALP__eval-001.json"
    assert read_json(path) == payload


def test_publish_progress_to_authorized_root(tmp_path):
    payload = progress_payload()
    path = publish_progress_artifact(paper_root=tmp_path, payload=payload)
    assert path.parent == tmp_path / "progress"
    assert path.name == "paper-signal-progress.json"
    assert read_json(path) == payload


def test_artifact_bytes_are_canonical_and_end_with_newline(tmp_path):
    payload = observation_payload()
    path = publish_observation_artifact(paper_root=tmp_path, payload=payload)
    expected = json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8") + b"\n"
    assert path.read_bytes() == expected


def test_publication_does_not_mutate_payload(tmp_path):
    payload = observation_payload()
    original = copy.deepcopy(payload)
    publish_observation_artifact(paper_root=tmp_path, payload=payload)
    assert payload == original


def test_identical_observation_reuse_is_idempotent(tmp_path):
    payload = observation_payload()
    first = publish_observation_artifact(paper_root=tmp_path, payload=payload)
    first_stat = first.stat()
    second = publish_observation_artifact(
        paper_root=tmp_path, payload=copy.deepcopy(payload)
    )
    assert first == second
    assert first.read_bytes() == second.read_bytes()
    assert first_stat.st_ino == second.stat().st_ino


def test_conflicting_observation_reuse_is_rejected(tmp_path):
    payload = observation_payload()
    publish_observation_artifact(paper_root=tmp_path, payload=payload)
    conflicting = copy.deepcopy(payload)
    conflicting["terminal_reason"] = "CONFLICT"
    with pytest.raises(PaperSignalArtifactError):
        publish_observation_artifact(paper_root=tmp_path, payload=conflicting)


def test_identical_evaluation_cycle_reuse_is_idempotent(tmp_path):
    payload = evaluation_cycle_payload()
    first = publish_evaluation_cycle_artifact(paper_root=tmp_path, payload=payload)
    second = publish_evaluation_cycle_artifact(
        paper_root=tmp_path, payload=copy.deepcopy(payload)
    )
    assert first == second


def test_conflicting_evaluation_cycle_reuse_is_rejected(tmp_path):
    payload = evaluation_cycle_payload()
    publish_evaluation_cycle_artifact(paper_root=tmp_path, payload=payload)
    conflicting = copy.deepcopy(payload)
    conflicting["evaluated_at"] = "2026-07-15T12:01:00Z"
    with pytest.raises(PaperSignalArtifactError):
        publish_evaluation_cycle_artifact(paper_root=tmp_path, payload=conflicting)


def test_identical_progress_reuse_is_idempotent(tmp_path):
    payload = progress_payload()
    first = publish_progress_artifact(paper_root=tmp_path, payload=payload)
    second = publish_progress_artifact(
        paper_root=tmp_path, payload=copy.deepcopy(payload)
    )
    assert first == second


def test_conflicting_progress_reuse_is_rejected(tmp_path):
    payload = progress_payload()
    publish_progress_artifact(paper_root=tmp_path, payload=payload)
    conflicting = copy.deepcopy(payload)
    conflicting["generated_at"] = "2026-07-15T13:01:00Z"
    with pytest.raises(PaperSignalArtifactError):
        publish_progress_artifact(paper_root=tmp_path, payload=conflicting)


@pytest.mark.parametrize(
    "forbidden_name",
    [
        "replay", "replay_artifacts", "production_evidence",
        "validated_snapshots_v4", "pre_delivery", "pine_delivery",
        "telegram_state", "position_ledger",
    ],
)
def test_rejects_forbidden_root_identity(tmp_path, forbidden_name):
    with pytest.raises(PaperSignalArtifactError):
        publish_observation_artifact(
            paper_root=tmp_path / forbidden_name, payload=observation_payload()
        )


def test_rejects_output_path_outside_paper_root(tmp_path):
    paper_root = tmp_path / "paper"
    outside = tmp_path / "outside"
    outside.mkdir()
    paper_root.mkdir()
    (paper_root / "observations").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PaperSignalArtifactError):
        publish_observation_artifact(paper_root=paper_root, payload=observation_payload())


def test_rejects_symlink_paper_root(tmp_path):
    physical = tmp_path / "physical"
    physical.mkdir()
    linked = tmp_path / "paper_link"
    linked.symlink_to(physical, target_is_directory=True)
    with pytest.raises(PaperSignalArtifactError):
        publish_progress_artifact(paper_root=linked, payload=progress_payload())


def test_rejects_symlink_ancestor(tmp_path):
    physical = tmp_path / "physical"
    physical.mkdir()
    ancestor = tmp_path / "linked_parent"
    ancestor.symlink_to(physical, target_is_directory=True)
    with pytest.raises(PaperSignalArtifactError):
        publish_progress_artifact(
            paper_root=ancestor / "paper", payload=progress_payload()
        )


def test_rejects_file_as_paper_root(tmp_path):
    root = tmp_path / "paper-file"
    root.write_text("not a directory", encoding="utf-8")
    with pytest.raises(PaperSignalArtifactError):
        publish_progress_artifact(paper_root=root, payload=progress_payload())


def test_rejects_non_mapping_payload(tmp_path):
    with pytest.raises(PaperSignalArtifactError):
        publish_progress_artifact(paper_root=tmp_path, payload=["not", "mapping"])


def test_rejects_nonfinite_payload_before_publication(tmp_path):
    payload = progress_payload()
    payload["acknowledgment_summary"]["latency_ms"]["mean"] = float("nan")
    with pytest.raises(PaperSignalArtifactError):
        publish_progress_artifact(paper_root=tmp_path, payload=payload)
    assert not (tmp_path / "progress").exists()


def test_observation_requires_paper_classification(tmp_path):
    with pytest.raises(PaperSignalArtifactError):
        publish_observation_artifact(
            paper_root=tmp_path,
            payload=observation_payload(classification="REPLAY"),
        )


def test_progress_requires_paper_classification(tmp_path):
    with pytest.raises(PaperSignalArtifactError):
        publish_progress_artifact(
            paper_root=tmp_path, payload=progress_payload(classification="REPLAY")
        )


def test_observation_requires_no_capital_boundary(tmp_path):
    with pytest.raises(PaperSignalArtifactError):
        publish_observation_artifact(
            paper_root=tmp_path,
            payload=observation_payload(
                execution_boundary="MASTER_ENGINE_RECORDED_INPUT"
            ),
        )


def test_progress_requires_no_capital_boundary(tmp_path):
    with pytest.raises(PaperSignalArtifactError):
        publish_progress_artifact(
            paper_root=tmp_path,
            payload=progress_payload(
                execution_boundary="MASTER_ENGINE_RECORDED_INPUT"
            ),
        )


def test_observation_filename_rejects_path_traversal(tmp_path):
    with pytest.raises(PaperSignalArtifactError):
        publish_observation_artifact(
            paper_root=tmp_path,
            payload=observation_payload(paper_observation_id="../escape"),
        )
    assert not (tmp_path.parent / "escape.json").exists()


@pytest.mark.parametrize(
    "source_evaluation_id",
    ["../escape", "folder/eval", r"folder\eval", "", "   "],
)
def test_evaluation_filename_rejects_unsafe_identity(tmp_path, source_evaluation_id):
    with pytest.raises(PaperSignalArtifactError):
        publish_evaluation_cycle_artifact(
            paper_root=tmp_path,
            payload=evaluation_cycle_payload(
                source_evaluation_id=source_evaluation_id
            ),
        )


def test_atomic_replace_failure_publishes_no_completed_artifact(tmp_path, monkeypatch):
    payload = observation_payload()

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(PaperSignalArtifactError):
        publish_observation_artifact(paper_root=tmp_path, payload=payload)
    final_path = tmp_path / "observations" / (payload["paper_observation_id"] + ".json")
    assert not final_path.exists()


def test_completed_artifact_has_no_incomplete_suffix(tmp_path):
    path = publish_observation_artifact(
        paper_root=tmp_path, payload=observation_payload()
    )
    assert ".incomplete" not in path.name
    assert ".tmp" not in path.name


def test_no_temporary_file_remains_after_success(tmp_path):
    publish_observation_artifact(paper_root=tmp_path, payload=observation_payload())
    temporary = [
        path for path in tmp_path.rglob("*")
        if path.is_file() and (".tmp" in path.name or ".incomplete" in path.name)
    ]
    assert temporary == []


def test_existing_artifact_symlink_is_rejected(tmp_path):
    payload = observation_payload()
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    directory = tmp_path / "observations"
    directory.mkdir()
    final_path = directory / (payload["paper_observation_id"] + ".json")
    final_path.symlink_to(target)
    with pytest.raises(PaperSignalArtifactError):
        publish_observation_artifact(paper_root=tmp_path, payload=payload)


def test_public_errors_do_not_include_absolute_root_path(tmp_path):
    with pytest.raises(PaperSignalArtifactError) as exc_info:
        publish_progress_artifact(
            paper_root=tmp_path / "replay", payload=progress_payload()
        )
    assert str(tmp_path) not in str(exc_info.value)


def test_publish_returns_resolved_regular_file(tmp_path):
    path = publish_progress_artifact(paper_root=tmp_path, payload=progress_payload())
    assert path.is_absolute()
    assert path.is_file()
    assert not path.is_symlink()
