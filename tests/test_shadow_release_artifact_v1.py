"""Frozen RED tests for Phase 08 Shadow Release artifact publication."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from engine.shadow_release_artifact_v1 import (
    SHADOW_RELEASE_LOCK_DIRECTORY,
    SHADOW_RELEASE_RUN_DIRECTORY,
    ShadowReleaseArtifactError,
    publish_shadow_run_artifact,
)
from engine.shadow_release_contract_v1 import build_shadow_run_contract


def source_publication_ref(**overrides):
    value = {
        "signal_id": "SCP-20260716-001",
        "delivery_id": "delivery-001",
        "mode": "SCALP",
        "published_at": "2026-07-16T12:00:00Z",
        "source_payload_hash": "a" * 64,
    }
    value.update(overrides)
    return value


def lifecycle(**overrides):
    value = {
        "publication": "PUBLISHED",
        "entry_eligibility": "ELIGIBLE",
        "cancellation": None,
        "entry_touch": "NOT_OBSERVED",
        "tp_sl_ordering": "NOT_APPLICABLE",
        "acknowledgment": None,
        "terminal_state": "OBSERVING",
    }
    value.update(overrides)
    return value


def semantic_projection(**overrides):
    value = {
        "validated_pipeline": {"final_top5": [{"symbol": "BTCUSDT"}]},
        "outcome_snapshot": {"candidates": ["BTCUSDT"]},
        "watchlist": {"setups": [{"rank": 1, "symbol": "BTCUSDT"}]},
        "pre_delivery": {"disposition": "PUBLISHED"},
        "tradingview_watchlist": "BTCUSDT",
        "pine_bridge": {"symbol": "BTCUSDT"},
        "pine_delivery_payload": "BTCUSDT,LONG",
        "publication": source_publication_ref(),
        "lifecycle": lifecycle(),
    }
    value.update(overrides)
    return value


def source_envelope(**overrides):
    value = {
        "schema_version": 1,
        "schema_name": "shadow-release-input",
        "classification": "SHADOW_RELEASE",
        "execution_boundary": (
            "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
        ),
        "source_commit": "b" * 40,
        "source_evaluation_id": "evaluation-20260716-1200",
        "mode": "SCALP",
        "market_identity": {
            "venue": "BINANCE_FUTURES_PUBLIC",
            "symbol": "BTCUSDT",
            "interval": "5m",
            "market_data_source": "PUBLIC_CLOSED_CANDLE_CAPTURE",
            "market_input_hash": "c" * 64,
        },
        "captured_at": "2026-07-16T12:00:02Z",
        "evaluation_started_at": "2026-07-16T12:00:00Z",
        "evaluation_completed_at": "2026-07-16T12:00:02Z",
        "serialized_inputs": {
            "scanner_results": [{"symbol": "BTCUSDT"}],
            "open_interest": {"BTCUSDT": {"change_pct": 1.0}},
            "validator_response": {"content": "approved", "usage": {}},
            "closed_candles": {"BTCUSDT": []},
        },
        "serialized_input_hash": "d" * 64,
        "expected_decision": semantic_projection(),
        "expected_decision_hash": "e" * 64,
        "source_publication_ref": source_publication_ref(),
        "signal_geometry": {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_zone": {"min": 100.0, "max": 102.0},
            "stop_loss": 95.0,
            "take_profit": {"tp1": 110.0, "tp2": 120.0},
            "valid_until": "2026-07-16T13:00:00Z",
        },
        "lifecycle_trace": lifecycle(),
        "outcome_kind": "PUBLISHED_SIGNAL",
    }
    value.update(overrides)
    return value


def component_versions(**overrides):
    value = {
        "master_engine": "master-engine-v4",
        "validated_pipeline": "validated-pipeline-v4",
        "pre_delivery": "pre-delivery-v4",
        "shadow_contract": "shadow-release-contract-v1",
        "shadow_runner": "shadow-release-runner-v1",
    }
    value.update(overrides)
    return value


def completed_run(*, observed=None, failure=None, **overrides):
    value = {
        "source_envelope": source_envelope(),
        "observed_decision": (
            semantic_projection() if observed is None else observed
        ),
        "component_versions": component_versions(),
        "started_at": "2026-07-16T12:00:03Z",
        "completed_at": "2026-07-16T12:00:05Z",
        "failure": failure,
    }
    value.update(overrides)
    return build_shadow_run_contract(**value)


def shadow_root(tmp_path):
    root = tmp_path / "data" / "shadow_release"
    root.mkdir(parents=True)
    return root


def canonical_bytes(payload):
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def test_frozen_shadow_artifact_directories():
    assert SHADOW_RELEASE_RUN_DIRECTORY == "runs"
    assert SHADOW_RELEASE_LOCK_DIRECTORY == ".locks"


def test_publishes_a_valid_match_to_the_canonical_identity_path(tmp_path):
    root = shadow_root(tmp_path)
    payload = completed_run()

    path = publish_shadow_run_artifact(shadow_root=root, payload=payload)

    assert path == (root / "runs" / f'{payload["shadow_run_id"]}.json').resolve()
    assert path.is_absolute()
    assert path.is_file()
    assert not path.is_symlink()
    assert (root / ".locks").is_dir()
    assert json.loads(path.read_text(encoding="utf-8")) == payload


@pytest.mark.parametrize(
    "payload",
    [
        completed_run(),
        completed_run(
            observed=semantic_projection(
                validated_pipeline={"final_top5": []},
            )
        ),
        completed_run(
            failure={
                "primary_code": "SHADOW_EXECUTION_FAILED",
                "component": "observed_adapter",
                "message": "adapter execution failed",
            }
        ),
    ],
)
def test_publishes_every_completed_shadow_outcome(tmp_path, payload):
    path = publish_shadow_run_artifact(
        shadow_root=shadow_root(tmp_path), payload=payload
    )

    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_artifact_bytes_are_canonical_utf8_and_newline_terminated(tmp_path):
    payload = completed_run()
    path = publish_shadow_run_artifact(
        shadow_root=shadow_root(tmp_path), payload=payload
    )

    assert path.read_bytes() == canonical_bytes(payload)


def test_mapping_insertion_order_does_not_change_bytes_or_identity(tmp_path):
    payload = completed_run()
    reordered = {
        key: copy.deepcopy(payload[key])
        for key in reversed(tuple(payload.keys()))
    }
    first = publish_shadow_run_artifact(
        shadow_root=shadow_root(tmp_path / "first"), payload=payload
    )
    second = publish_shadow_run_artifact(
        shadow_root=shadow_root(tmp_path / "second"), payload=reordered
    )

    assert first.name == second.name
    assert first.read_bytes() == second.read_bytes()


def test_same_identity_and_same_bytes_reuses_existing_completed_evidence(tmp_path):
    root = shadow_root(tmp_path)
    payload = completed_run()
    first = publish_shadow_run_artifact(shadow_root=root, payload=payload)
    inode = first.stat().st_ino
    second = publish_shadow_run_artifact(
        shadow_root=root, payload=copy.deepcopy(payload)
    )

    assert first == second
    assert second.stat().st_ino == inode
    assert second.read_bytes() == canonical_bytes(payload)


def test_same_identity_with_different_completed_bytes_fails_closed(tmp_path):
    root = shadow_root(tmp_path)
    first = completed_run()
    conflicting = completed_run(completed_at="2026-07-16T12:00:06Z")
    assert first["shadow_run_id"] == conflicting["shadow_run_id"]

    publish_shadow_run_artifact(shadow_root=root, payload=first)
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(shadow_root=root, payload=conflicting)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.__setitem__("content_hash", "0" * 64),
        lambda payload: payload.__setitem__("shadow_run_id", "SHR-" + "0" * 64),
        lambda payload: payload["comparison"].__setitem__("outcome", "PENDING"),
        lambda payload: payload.__setitem__("unexpected", "forbidden"),
    ],
)
def test_rejects_malformed_or_noncanonical_completed_contracts(tmp_path, mutation):
    payload = completed_run()
    mutation(payload)
    root = shadow_root(tmp_path)

    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(shadow_root=root, payload=payload)

    assert not (root / "runs").exists()


def test_rejects_non_mapping_payload_and_missing_explicit_root(tmp_path):
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(
            shadow_root=shadow_root(tmp_path), payload=["not", "a", "run"]
        )
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(
            shadow_root=tmp_path / "missing" / "shadow_release",
            payload=completed_run(),
        )


@pytest.mark.parametrize(
    "protected_name",
    [
        "replay",
        "replay_artifacts",
        "production_evidence",
        "production_evidence_v4",
        "production_run_v4",
        "validated_snapshots_v4",
        "v4_outcomes",
        "top5_watchlist_v4",
        "pre_delivery_v4",
        "pine_delivery_v4",
        "telegram_state",
        "worker_state_v4",
        "quota_slot_v4",
        "position_ledger",
        "paper_signal",
    ],
)
def test_rejects_protected_root_names_without_leaking_paths(
    tmp_path, protected_name
):
    root = tmp_path / protected_name

    with pytest.raises(ShadowReleaseArtifactError) as exc_info:
        publish_shadow_run_artifact(shadow_root=root, payload=completed_run())

    assert str(tmp_path) not in str(exc_info.value)


def test_rejects_shadow_root_nested_beneath_a_protected_root(tmp_path):
    protected = tmp_path / "paper_signal"
    protected.mkdir()
    root = protected / "shadow_release"

    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(shadow_root=root, payload=completed_run())


def test_rejects_file_and_symlink_roots_and_symlink_ancestors(tmp_path):
    file_root = tmp_path / "data" / "shadow_release"
    file_root.parent.mkdir()
    file_root.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(
            shadow_root=file_root, payload=completed_run()
        )

    physical = tmp_path / "physical"
    physical.mkdir()
    linked_root = tmp_path / "linked_shadow_release"
    linked_root.symlink_to(physical, target_is_directory=True)
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(
            shadow_root=linked_root, payload=completed_run()
        )

    linked_ancestor = tmp_path / "linked_data"
    linked_ancestor.symlink_to(physical, target_is_directory=True)
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(
            shadow_root=linked_ancestor / "shadow_release",
            payload=completed_run(),
        )


def test_rejects_symlink_run_directory_and_destination(tmp_path):
    root = shadow_root(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "runs").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(shadow_root=root, payload=completed_run())

    root = shadow_root(tmp_path / "destination")
    payload = completed_run()
    run_directory = root / "runs"
    run_directory.mkdir()
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    (run_directory / f'{payload["shadow_run_id"]}.json').symlink_to(target)
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(shadow_root=root, payload=payload)


def test_existing_directory_or_malformed_file_is_not_completed_evidence(tmp_path):
    root = shadow_root(tmp_path)
    payload = completed_run()
    run_directory = root / "runs"
    run_directory.mkdir()
    final_path = run_directory / f'{payload["shadow_run_id"]}.json'
    final_path.mkdir()
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(shadow_root=root, payload=payload)

    final_path.rmdir()
    final_path.write_bytes(b"not canonical json\n")
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(shadow_root=root, payload=payload)


def test_publisher_forwards_no_caller_mutation_and_no_return_mutation(tmp_path):
    payload = completed_run()
    original = copy.deepcopy(payload)
    path = publish_shadow_run_artifact(
        shadow_root=shadow_root(tmp_path), payload=payload
    )
    returned = json.loads(path.read_text(encoding="utf-8"))
    returned["comparison"]["outcome"] = "MUTATED_IN_MEMORY"

    assert payload == original
    assert json.loads(path.read_text(encoding="utf-8")) == original


def test_temporary_file_is_created_in_run_directory_and_cleaned_after_success(
    tmp_path, monkeypatch
):
    import engine.shadow_release_artifact_v1 as artifact_module

    root = shadow_root(tmp_path)
    payload = completed_run()
    original_mkstemp = artifact_module.tempfile.mkstemp
    directories = []

    def recording_mkstemp(*args, **kwargs):
        directories.append(Path(kwargs["dir"]))
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(artifact_module.tempfile, "mkstemp", recording_mkstemp)
    publish_shadow_run_artifact(shadow_root=root, payload=payload)

    assert directories == [root / "runs"]
    assert [path for path in root.rglob("*") if ".tmp" in path.name] == []


def test_atomic_replace_failure_leaves_no_final_or_temporary_file(
    tmp_path, monkeypatch
):
    import engine.shadow_release_artifact_v1 as artifact_module

    root = shadow_root(tmp_path)
    payload = completed_run()

    def fail_replace(source, destination):
        raise OSError("replace failed token=secret")

    monkeypatch.setattr(artifact_module.os, "replace", fail_replace)
    with pytest.raises(ShadowReleaseArtifactError) as exc_info:
        publish_shadow_run_artifact(shadow_root=root, payload=payload)

    assert "secret" not in str(exc_info.value).casefold()
    assert not (root / "runs" / f'{payload["shadow_run_id"]}.json').exists()
    assert [path for path in root.rglob("*") if ".tmp" in path.name] == []


def test_rejects_a_symlink_temporary_target_without_following_it(
    tmp_path, monkeypatch
):
    import engine.shadow_release_artifact_v1 as artifact_module

    root = shadow_root(tmp_path)
    payload = completed_run()
    run_directory = root / "runs"
    run_directory.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"outside evidence")
    temporary = run_directory / ".forced.tmp"
    temporary.symlink_to(outside)

    def symlink_mkstemp(*args, **kwargs):
        return os.open(outside, os.O_WRONLY), str(temporary)

    monkeypatch.setattr(
        artifact_module.tempfile, "mkstemp", symlink_mkstemp
    )
    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(shadow_root=root, payload=payload)

    assert outside.read_bytes() == b"outside evidence"
    assert not temporary.exists()
    assert not (run_directory / f'{payload["shadow_run_id"]}.json').exists()


def test_rejects_security_authority_in_completed_payload(tmp_path):
    payload = completed_run()
    payload["exchange_credentials"] = {"token": "forbidden"}

    with pytest.raises(ShadowReleaseArtifactError):
        publish_shadow_run_artifact(
            shadow_root=shadow_root(tmp_path), payload=payload
        )


def test_import_has_no_ambient_root_or_publication_side_effect(tmp_path):
    root = tmp_path / "data" / "shadow_release"

    assert not root.exists()
