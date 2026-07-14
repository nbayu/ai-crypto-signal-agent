import ast
import copy
import errno
import hashlib
import inspect
import json
import os
import shutil
import socket
import sys
from dataclasses import FrozenInstanceError, replace
from importlib import util as importlib_util
from pathlib import Path
from types import MappingProxyType

import pytest
import requests

import engine.master_engine_v4 as master_module
import engine.replay_runner_v4 as runner_module
import engine.scanner as scanner_module
import engine.stateful_worker_v4 as stateful_worker_module
import engine.quota_slot_worker_v4 as quota_worker_module
import engine.telegram_sdk_runner_v4 as telegram_runner_module
import engine.replay_artifact_v4 as artifact_module
from engine.replay_artifact_v4 import (
    ReplayArtifactComparisonV4,
    ReplayArtifactError,
    ReplayArtifactPublicationV4,
    build_replay_manifest_v4,
    calculate_replay_result_hash_v4,
    compare_replay_artifacts_v4,
    publish_replay_artifacts_v4,
)
from engine.replay_contract_v4 import (
    REPLAY_BUNDLE_SCHEMA_VERSION,
    calculate_replay_bundle_hash_v4,
    derive_replay_fixture_id_v4,
    derive_replay_id_v4,
    load_replay_bundle_v4,
)
from engine.replay_runner_v4 import ReplayExecutionResultV4, run_replay_v4


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "replay_v4"
    / "valid_bundle_v2.json"
)
FIXTURE_SHA256 = (
    "5a91fc2edc25d09b88678c73353c0e0a"
    "b8ecedf79c22544489e9613dbc62290f"
)
CLASSIFICATION = "REPLAY"
BOUNDARY = "MASTER_ENGINE_RECORDED_INPUT"
MANIFEST_NAME = "replay_manifest.json"
NON_PRODUCTION_NOTICE = (
    "Deterministic replay output; not production evidence, live-market "
    "evidence, a backtest, or a profitability claim."
)
RUNNER_ARTIFACTS = {
    "replay_validated_snapshot.json": {
        "snapshot_type": "v4_validated_snapshot",
        "validated_at": "2026-01-15T12:00:00+00:00",
        "final_top5": [{"symbol": "BTC/USDT:USDT", "score": 91.0}],
    },
    "replay_outcome.json": {
        "captured_at": "2026-01-15T12:00:00+00:00",
        "setups": [{"symbol": "BTC/USDT:USDT", "score": 91.0}],
    },
    "replay_top5_watchlist.json": {
        "generated_at": "2026-01-15T12:00:00+00:00",
        "setups": [{"symbol": "BTC/USDT:USDT", "score": 91.0}],
    },
    "replay_pre_delivery.json": {
        "validated_at": "2026-01-15T12:00:00+00:00",
        "eligible_setup_count": 1,
        "evaluations": [{"symbol": "BTC/USDT:USDT", "eligible": True}],
    },
    "replay_tradingview_watchlist.txt": "BINANCE:BTCUSDT.P",
    "replay_pine_bridge.json": {
        "generated_at": "2026-01-15T12:00:00+00:00",
        "setups": [{"symbol": "BTCUSDT", "direction": "LONG"}],
    },
    "replay_pine_payload.txt": "BTCUSDT|LONG|61000|60000|63000",
    "replay_evidence.json": {
        "classification": CLASSIFICATION,
        "boundary": BOUNDARY,
        "created_at": "2026-01-15T12:00:00+00:00",
    },
}


@pytest.fixture
def bundle():
    return load_replay_bundle_v4(FIXTURE_PATH)


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze(nested) for key, nested in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(nested) for nested in value)
    return value


def _thaw(value):
    if isinstance(value, MappingProxyType) or isinstance(value, dict):
        return {key: _thaw(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw(nested) for nested in value]
    return value


def _write_runner_artifacts(root, *, suffix=""):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for relative_path, value in RUNNER_ARTIFACTS.items():
        path = root / relative_path
        if isinstance(value, str):
            payload = value + suffix
        else:
            payload = json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
            ) + suffix
        path.write_text(payload, encoding="utf-8")
    return root


def _make_result(bundle, output_root, *, normalized=None, **changes):
    if normalized is None:
        normalized = {
            "out": {
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 80,
                    "total_tokens": 200,
                    "cache_hit_tokens": 20,
                    "cache_miss_tokens": 100,
                },
                "final_top5": [
                    {"symbol": "BTC/USDT:USDT", "score": 91.0},
                    {"symbol": "ETH/USDT:USDT", "score": 88.0},
                ],
            },
            "evidence_path": "replay_evidence.json",
            "watchlist_path": "replay_top5_watchlist.json",
        }
    values = {
        "replay_id": derive_replay_id_v4(bundle),
        "fixture_id": derive_replay_fixture_id_v4(bundle),
        "bundle_hash": calculate_replay_bundle_hash_v4(bundle),
        "fixed_execution_time": bundle.fixed_execution_time,
        "output_root": Path(output_root),
        "normalized_master_result": _freeze(copy.deepcopy(normalized)),
        "classification": CLASSIFICATION,
        "boundary": BOUNDARY,
    }
    values.update(changes)
    return ReplayExecutionResultV4(**values)


@pytest.fixture
def replay_result(bundle, tmp_path):
    output_root = _write_runner_artifacts(tmp_path / "runner-output")
    return _make_result(bundle, output_root)


def _artifact_files(result):
    return tuple(
        sorted(
            path
            for path in Path(result.output_root).rglob("*")
            if path.is_file()
        )
    )


def _final_path(final_root, result):
    return Path(final_root) / result.replay_id


def _incomplete_path(staging_root, result):
    return Path(staging_root) / f"{result.replay_id}.incomplete"


def _read_manifest(publication_root):
    return json.loads(
        (Path(publication_root) / MANIFEST_NAME).read_text(encoding="utf-8")
    )


def _publication_file_state(publication_root):
    return {
        path.relative_to(publication_root).as_posix(): (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(Path(publication_root).rglob("*"))
        if path.is_file()
    }


def _directory_tree_state(root):
    root = Path(root)
    state = []
    for path in (root, *sorted(root.rglob("*"))):
        relative = "." if path == root else path.relative_to(root).as_posix()
        metadata = path.lstat()
        if path.is_symlink():
            kind = "symlink"
            content = os.readlink(path)
        elif path.is_file():
            kind = "file"
            content = path.read_bytes()
        elif path.is_dir():
            kind = "directory"
            content = None
        else:
            kind = "other"
            content = None
        state.append((relative, kind, content, metadata.st_mtime_ns))
    return tuple(state)


def _assert_destination_alias_is_rejected(
    replay_result,
    staging_root,
    final_root,
    alias_target,
    monkeypatch,
):
    monkeypatch.setattr(
        runner_module,
        "run_replay_v4",
        _fail_if_called("replay runner"),
    )
    monkeypatch.setattr(
        master_module,
        "run_master_engine_v4",
        _fail_if_called("master engine"),
    )
    before = _directory_tree_state(alias_target)

    with pytest.raises(ReplayArtifactError) as exc_info:
        publish_replay_artifacts_v4(
            replay_result,
            staging_root,
            final_root,
        )

    message = str(exc_info.value)
    assert message == "Invalid replay artifact path"
    assert str(staging_root) not in message
    assert str(final_root) not in message
    assert str(alias_target) not in message
    assert not Path(staging_root).exists()
    assert not Path(final_root).exists()
    assert not _incomplete_path(staging_root, replay_result).exists()
    assert not _final_path(final_root, replay_result).exists()
    assert _directory_tree_state(alias_target) == before
    assert not tuple(Path(alias_target).rglob(MANIFEST_NAME))
    assert not tuple(Path(alias_target).rglob("latest*"))


def _publish(replay_result, tmp_path):
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"
    publication = publish_replay_artifacts_v4(
        replay_result,
        staging_root,
        final_root,
    )
    return publication, staging_root, final_root


def _fail_if_called(name):
    def fail(*args, **kwargs):
        raise AssertionError(f"protected dependency called: {name}")

    return fail


def test_public_api_and_signatures_are_frozen():
    assert issubclass(ReplayArtifactError, Exception)
    assert inspect.isclass(ReplayArtifactComparisonV4)
    assert inspect.isclass(ReplayArtifactPublicationV4)
    assert str(inspect.signature(calculate_replay_result_hash_v4)) == "(result)"
    assert str(inspect.signature(build_replay_manifest_v4)) == (
        "(replay_result, artifact_files)"
    )
    assert str(inspect.signature(compare_replay_artifacts_v4)) == (
        "(expected, actual)"
    )
    assert str(inspect.signature(publish_replay_artifacts_v4)) == (
        "(replay_result, staging_root, final_root)"
    )


def test_result_hash_is_lowercase_sha256_and_deterministic(replay_result):
    first = calculate_replay_result_hash_v4(replay_result)
    second = calculate_replay_result_hash_v4(replay_result)

    assert first == second
    assert len(first) == 64
    assert first == first.casefold()
    assert set(first) <= set("0123456789abcdef")


def test_result_hash_excludes_caller_local_output_root(bundle, tmp_path):
    first = _make_result(bundle, tmp_path / "one")
    second = _make_result(bundle, tmp_path / "elsewhere" / "two")

    assert first.output_root != second.output_root
    assert calculate_replay_result_hash_v4(first) == (
        calculate_replay_result_hash_v4(second)
    )


def test_result_hash_ignores_mapping_order_and_mutability(bundle, tmp_path):
    ordered = {
        "out": {
            "final_top5": [{"symbol": "BTC/USDT:USDT", "score": 91.0}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1},
        },
        "evidence_path": "replay_evidence.json",
    }
    reversed_order = {
        "evidence_path": "replay_evidence.json",
        "out": {
            "usage": {"completion_tokens": 1, "prompt_tokens": 2},
            "final_top5": [{"score": 91.0, "symbol": "BTC/USDT:USDT"}],
        },
    }
    first = _make_result(bundle, tmp_path / "one", normalized=ordered)
    second = _make_result(bundle, tmp_path / "two", normalized=reversed_order)

    assert calculate_replay_result_hash_v4(first) == (
        calculate_replay_result_hash_v4(second)
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("replay_id", "replay-v4-different"),
        ("fixture_id", "fixture-v4-different"),
        ("bundle_hash", "f" * 64),
        ("fixed_execution_time", "2026-01-15T12:00:01+00:00"),
        ("classification", "NOT_REPLAY"),
        ("boundary", "DIFFERENT_BOUNDARY"),
    ],
)
def test_result_hash_changes_for_every_identity_domain(
    replay_result,
    field,
    replacement,
):
    changed = replace(replay_result, **{field: replacement})

    assert calculate_replay_result_hash_v4(changed) != (
        calculate_replay_result_hash_v4(replay_result)
    )


def test_result_hash_changes_for_normalized_master_semantics(
    bundle,
    tmp_path,
):
    first = _make_result(
        bundle,
        tmp_path / "one",
        normalized={"out": {"final_top5": [{"symbol": "BTC", "score": 91}]}},
    )
    second = _make_result(
        bundle,
        tmp_path / "two",
        normalized={"out": {"final_top5": [{"symbol": "BTC", "score": 90}]}},
    )

    assert calculate_replay_result_hash_v4(first) != (
        calculate_replay_result_hash_v4(second)
    )


def test_result_hash_uses_no_filesystem_metadata(replay_result):
    before = calculate_replay_result_hash_v4(replay_result)
    for index, path in enumerate(_artifact_files(replay_result), start=1):
        os.utime(path, ns=(index, index))

    assert calculate_replay_result_hash_v4(replay_result) == before


def test_manifest_is_complete_explicitly_replay_and_non_production(
    replay_result,
):
    manifest = build_replay_manifest_v4(
        replay_result,
        _artifact_files(replay_result),
    )

    assert manifest["manifest_version"] == 1
    assert manifest["classification"] == CLASSIFICATION
    assert manifest["boundary"] == BOUNDARY
    assert manifest["replay_id"] == replay_result.replay_id
    assert manifest["fixture_id"] == replay_result.fixture_id
    assert manifest["bundle_hash"] == replay_result.bundle_hash
    assert manifest["result_hash"] == calculate_replay_result_hash_v4(
        replay_result
    )
    assert manifest["fixed_execution_time"] == (
        replay_result.fixed_execution_time
    )
    assert manifest["source_replay_schema_version"] == (
        REPLAY_BUNDLE_SCHEMA_VERSION
    )
    assert manifest["completion_state"] == "COMPLETE"
    assert manifest["non_production_notice"] == NON_PRODUCTION_NOTICE
    assert "production_run_v4" not in json.dumps(_thaw(manifest))
    assert "profitability" in manifest["non_production_notice"]


def test_manifest_inventory_is_sorted_relative_hashed_and_sized(
    replay_result,
):
    artifact_files = tuple(reversed(_artifact_files(replay_result)))
    manifest = build_replay_manifest_v4(replay_result, artifact_files)
    inventory = manifest["artifacts"]
    paths = [item["relative_path"] for item in inventory]

    assert paths == sorted(RUNNER_ARTIFACTS)
    assert all(not Path(path).is_absolute() for path in paths)
    assert all(".." not in Path(path).parts for path in paths)
    for item in inventory:
        source = Path(replay_result.output_root) / item["relative_path"]
        assert item["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert item["size_bytes"] == source.stat().st_size


def test_manifest_is_deeply_immutable_and_canonical_order_stable(
    replay_result,
):
    files = _artifact_files(replay_result)
    first = build_replay_manifest_v4(replay_result, files)
    second = build_replay_manifest_v4(replay_result, reversed(files))

    assert isinstance(first, MappingProxyType)
    assert isinstance(first["artifacts"], tuple)
    assert all(isinstance(item, MappingProxyType) for item in first["artifacts"])
    assert _thaw(first) == _thaw(second)
    canonical_first = json.dumps(
        _thaw(first),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    canonical_second = json.dumps(
        _thaw(second),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert canonical_first == canonical_second
    with pytest.raises(TypeError):
        first["classification"] = "PRODUCTION"
    with pytest.raises(TypeError):
        first["artifacts"][0]["relative_path"] = "changed"


def test_manifest_builder_does_not_mutate_inputs(replay_result):
    files = list(_artifact_files(replay_result))
    original_files = list(files)
    normalized_before = _thaw(replay_result.normalized_master_result)

    build_replay_manifest_v4(replay_result, files)

    assert files == original_files
    assert _thaw(replay_result.normalized_master_result) == normalized_before


@pytest.mark.parametrize("invalid", [None, {}, [], object()])
def test_manifest_rejects_non_runner_result(invalid, tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}", encoding="utf-8")

    with pytest.raises(ReplayArtifactError):
        build_replay_manifest_v4(invalid, [artifact])


def test_manifest_rejects_duplicate_inventory_entries(replay_result):
    artifact = _artifact_files(replay_result)[0]

    with pytest.raises(ReplayArtifactError):
        build_replay_manifest_v4(replay_result, [artifact, artifact])


def test_manifest_rejects_files_outside_runner_root(replay_result, tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ReplayArtifactError):
        build_replay_manifest_v4(replay_result, [outside])


def test_manifest_rejects_directory_and_symlink_inventory(
    replay_result,
    tmp_path,
):
    nested = Path(replay_result.output_root) / "nested"
    nested.mkdir()
    target = tmp_path / "external.txt"
    target.write_text("external", encoding="utf-8")
    link = Path(replay_result.output_root) / "linked.txt"
    link.symlink_to(target)

    with pytest.raises(ReplayArtifactError):
        build_replay_manifest_v4(replay_result, [nested])
    with pytest.raises(ReplayArtifactError):
        build_replay_manifest_v4(replay_result, [link])


def test_exact_comparison_reports_match_and_is_immutable(replay_result, tmp_path):
    publication, _, _ = _publish(replay_result, tmp_path)
    mirror = tmp_path / "mirror"
    shutil.copytree(publication.final_path, mirror)

    comparison = compare_replay_artifacts_v4(publication.final_path, mirror)

    assert isinstance(comparison, ReplayArtifactComparisonV4)
    assert comparison.matches is True
    assert comparison.expected_hash == comparison.actual_hash
    assert comparison.mismatched_paths == ()
    assert comparison.missing_paths == ()
    assert comparison.unexpected_paths == ()
    assert comparison.semantic_mismatches == ()
    assert comparison.safe_summary == "Replay artifacts match"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        comparison.matches = False


def test_comparison_reports_byte_missing_and_unexpected_paths(
    replay_result,
    tmp_path,
):
    publication, _, _ = _publish(replay_result, tmp_path)
    actual = tmp_path / "actual"
    shutil.copytree(publication.final_path, actual)
    changed = actual / "replay_outcome.json"
    changed.write_text("changed", encoding="utf-8")
    (actual / "replay_pine_payload.txt").unlink()
    (actual / "unexpected.txt").write_text("unexpected", encoding="utf-8")

    comparison = compare_replay_artifacts_v4(publication.final_path, actual)

    assert comparison.matches is False
    assert comparison.mismatched_paths == ("replay_outcome.json",)
    assert comparison.missing_paths == ("replay_pine_payload.txt",)
    assert comparison.unexpected_paths == ("unexpected.txt",)
    assert comparison.safe_summary == "Replay artifacts differ"
    assert "changed" not in comparison.safe_summary
    assert "unexpected" not in comparison.safe_summary


def test_comparison_reports_manifest_and_result_hash_semantics(
    replay_result,
    tmp_path,
):
    publication, _, _ = _publish(replay_result, tmp_path)
    actual = tmp_path / "actual"
    shutil.copytree(publication.final_path, actual)
    manifest_path = actual / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["bundle_hash"] = "f" * 64
    manifest["result_hash"] = "e" * 64
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    comparison = compare_replay_artifacts_v4(publication.final_path, actual)

    assert comparison.matches is False
    assert comparison.semantic_mismatches == ("bundle_hash", "result_hash")
    assert comparison.expected_hash != comparison.actual_hash


def test_comparison_ignores_file_order_mtime_inode_and_host_root(
    replay_result,
    tmp_path,
):
    publication, _, _ = _publish(replay_result, tmp_path)
    actual = tmp_path / "different-host-root" / "actual"
    shutil.copytree(publication.final_path, actual)
    for index, path in enumerate(sorted(actual.rglob("*")), start=10):
        if path.is_file():
            os.utime(path, ns=(index, index))

    comparison = compare_replay_artifacts_v4(publication.final_path, actual)

    assert comparison.matches is True
    assert comparison.expected_hash == comparison.actual_hash


def test_comparison_does_not_mutate_either_publication(replay_result, tmp_path):
    publication, _, _ = _publish(replay_result, tmp_path)
    actual = tmp_path / "actual"
    shutil.copytree(publication.final_path, actual)
    expected_before = _publication_file_state(publication.final_path)
    actual_before = _publication_file_state(actual)

    compare_replay_artifacts_v4(publication.final_path, actual)

    assert _publication_file_state(publication.final_path) == expected_before
    assert _publication_file_state(actual) == actual_before


def test_first_publication_is_deterministic_complete_and_immutable(
    replay_result,
    tmp_path,
):
    publication, staging_root, final_root = _publish(replay_result, tmp_path)
    expected_final = _final_path(final_root, replay_result)

    assert isinstance(publication, ReplayArtifactPublicationV4)
    assert publication.replay_id == replay_result.replay_id
    assert publication.fixture_id == replay_result.fixture_id
    assert publication.bundle_hash == replay_result.bundle_hash
    assert publication.result_hash == calculate_replay_result_hash_v4(
        replay_result
    )
    assert publication.final_path == expected_final.resolve()
    assert publication.manifest_path == (
        expected_final / MANIFEST_NAME
    ).resolve()
    assert publication.artifact_count == len(RUNNER_ARTIFACTS)
    assert publication.reused_existing is False
    assert publication.classification == CLASSIFICATION
    assert publication.boundary == BOUNDARY
    assert expected_final.name == replay_result.replay_id
    assert expected_final.is_dir()
    assert publication.manifest_path.is_file()
    assert not _incomplete_path(staging_root, replay_result).exists()
    assert list(final_root.iterdir()) == [expected_final]
    with pytest.raises((FrozenInstanceError, AttributeError)):
        publication.reused_existing = True


def test_publication_manifest_is_written_last_and_inventories_no_temps(
    replay_result,
    tmp_path,
):
    publication, _, _ = _publish(replay_result, tmp_path)
    manifest = _read_manifest(publication.final_path)
    inventory_paths = [item["relative_path"] for item in manifest["artifacts"]]
    manifest_mtime = publication.manifest_path.stat().st_mtime_ns

    assert inventory_paths == sorted(RUNNER_ARTIFACTS)
    assert MANIFEST_NAME not in inventory_paths
    assert all(not Path(path).name.startswith(".") for path in inventory_paths)
    assert all(
        manifest_mtime >= (publication.final_path / path).stat().st_mtime_ns
        for path in inventory_paths
    )
    assert all(
        not path.name.endswith((".tmp", ".partial", ".incomplete"))
        for path in publication.final_path.rglob("*")
    )


def test_identical_repeated_publication_reuses_without_rewrite(
    bundle,
    tmp_path,
):
    first_source = _write_runner_artifacts(tmp_path / "runner-one")
    first_result = _make_result(bundle, first_source)
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"
    first = publish_replay_artifacts_v4(first_result, staging_root, final_root)
    before = _publication_file_state(first.final_path)

    second_source = _write_runner_artifacts(tmp_path / "runner-two")
    second_result = _make_result(bundle, second_source)
    second = publish_replay_artifacts_v4(
        second_result,
        staging_root,
        final_root,
    )

    assert second.reused_existing is True
    assert second.final_path == first.final_path
    assert second.manifest_path == first.manifest_path
    assert _publication_file_state(first.final_path) == before
    assert list(final_root.iterdir()) == [first.final_path]
    assert not _incomplete_path(staging_root, second_result).exists()


def test_same_identity_with_different_artifact_fails_without_overwrite(
    bundle,
    tmp_path,
):
    first_source = _write_runner_artifacts(tmp_path / "runner-one")
    first_result = _make_result(bundle, first_source)
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"
    first = publish_replay_artifacts_v4(first_result, staging_root, final_root)
    before = _publication_file_state(first.final_path)
    second_source = _write_runner_artifacts(
        tmp_path / "runner-two",
        suffix="different",
    )
    second_result = _make_result(bundle, second_source)

    with pytest.raises(ReplayArtifactError) as exc_info:
        publish_replay_artifacts_v4(second_result, staging_root, final_root)

    assert "collision" in str(exc_info.value).casefold()
    assert _publication_file_state(first.final_path) == before
    assert list(final_root.iterdir()) == [first.final_path]
    assert not (final_root / f"{first_result.replay_id}-1").exists()
    assert not (final_root / "latest.json").exists()


def test_stale_incomplete_staging_fails_closed_without_cleanup(
    replay_result,
    tmp_path,
):
    staging_root = tmp_path / "staging"
    incomplete = _incomplete_path(staging_root, replay_result)
    incomplete.mkdir(parents=True)
    sentinel = incomplete / "partial.bin"
    sentinel.write_bytes(b"partial")
    final_root = tmp_path / "published"

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, staging_root, final_root)

    assert sentinel.read_bytes() == b"partial"
    assert not _final_path(final_root, replay_result).exists()


@pytest.mark.parametrize("existing_kind", ["file", "symlink"])
def test_existing_final_file_or_symlink_fails_closed(
    replay_result,
    tmp_path,
    existing_kind,
):
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"
    final_root.mkdir()
    final_path = _final_path(final_root, replay_result)
    if existing_kind == "file":
        final_path.write_text("sentinel", encoding="utf-8")
    else:
        target = tmp_path / "outside"
        target.mkdir()
        final_path.symlink_to(target, target_is_directory=True)

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, staging_root, final_root)

    assert not _incomplete_path(staging_root, replay_result).exists()


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_manifest",
        "malformed_manifest",
        "missing_artifact",
        "hash_mismatch",
        "unexpected_artifact",
        "bundle_collision",
        "result_collision",
    ],
)
def test_corrupt_or_colliding_existing_publication_fails_closed(
    replay_result,
    tmp_path,
    corruption,
):
    publication, staging_root, final_root = _publish(replay_result, tmp_path)
    final_path = publication.final_path
    before_source = _publication_file_state(replay_result.output_root)
    manifest_path = final_path / MANIFEST_NAME
    if corruption == "missing_manifest":
        manifest_path.unlink()
    elif corruption == "malformed_manifest":
        manifest_path.write_text("{", encoding="utf-8")
    elif corruption == "missing_artifact":
        (final_path / "replay_outcome.json").unlink()
    elif corruption == "hash_mismatch":
        (final_path / "replay_outcome.json").write_text(
            "changed",
            encoding="utf-8",
        )
    elif corruption == "unexpected_artifact":
        (final_path / "unexpected.txt").write_text(
            "unexpected",
            encoding="utf-8",
        )
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        key = "bundle_hash" if corruption == "bundle_collision" else "result_hash"
        manifest[key] = "f" * 64
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
    corrupted_state = _publication_file_state(final_path)

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, staging_root, final_root)

    assert _publication_file_state(final_path) == corrupted_state
    assert _publication_file_state(replay_result.output_root) == before_source


@pytest.mark.parametrize("invalid_root", [None, "", 0, False, object()])
def test_invalid_publication_roots_fail_before_mutation(
    replay_result,
    tmp_path,
    invalid_root,
):
    valid = tmp_path / "valid"

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, invalid_root, valid)
    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, valid, invalid_root)

    assert not valid.exists()


def test_regular_file_publication_root_is_rejected(replay_result, tmp_path):
    root_file = tmp_path / "root-file"
    root_file.write_text("sentinel", encoding="utf-8")
    other = tmp_path / "other"

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, root_file, other)
    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, other, root_file)

    assert root_file.read_text(encoding="utf-8") == "sentinel"
    assert not other.exists()


@pytest.mark.parametrize(
    "protected_name",
    [
        "production_run_v4",
        "production_evidence_v4",
        "validated_snapshots_v4",
        "v4_outcomes",
        "top5_watchlist_v4",
        "pre_delivery_v4",
        "pine_delivery_v4",
        "quota_slot_v4",
        "worker_state_v4",
        "forward-test",
        "telegram",
    ],
)
def test_production_and_state_path_aliases_are_rejected(
    replay_result,
    tmp_path,
    protected_name,
):
    protected = tmp_path / protected_name
    safe = tmp_path / "safe"

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, protected, safe)
    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(replay_result, safe, protected)

    assert not protected.exists()
    assert not safe.exists()


def test_symlink_staging_and_final_roots_are_rejected(
    replay_result,
    tmp_path,
):
    external = tmp_path / "external"
    external.mkdir()
    staging_link = tmp_path / "staging-link"
    final_link = tmp_path / "final-link"
    staging_link.symlink_to(external, target_is_directory=True)
    final_link.symlink_to(external, target_is_directory=True)

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(
            replay_result,
            staging_link,
            tmp_path / "final",
        )
    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(
            replay_result,
            tmp_path / "staging",
            final_link,
        )

    assert list(external.iterdir()) == []


def test_final_root_rejects_nonexistent_leaf_beneath_protected_symlink(
    replay_result,
    tmp_path,
    monkeypatch,
):
    protected_target = tmp_path / "data" / "production_evidence_v4"
    protected_target.mkdir(parents=True)
    sentinel = protected_target / "sentinel.bin"
    sentinel.write_bytes(b"preserve-production-evidence")
    caller = tmp_path / "caller"
    caller.mkdir()
    alias = caller / "cache"
    alias.symlink_to(protected_target, target_is_directory=True)
    final_root = alias / "new-final-root"
    staging_root = tmp_path / "safe-staging-root"
    assert not final_root.exists()

    _assert_destination_alias_is_rejected(
        replay_result,
        staging_root,
        final_root,
        protected_target,
        monkeypatch,
    )

    assert sentinel.read_bytes() == b"preserve-production-evidence"


def test_pre_delivery_alias_is_rejected_without_target_mutation(
    replay_result,
    tmp_path,
    monkeypatch,
):
    protected_target = tmp_path / "data" / "pre_delivery_v4"
    protected_target.mkdir(parents=True)
    sentinel = protected_target / "sentinel.json"
    sentinel.write_text('{"production":"sentinel"}', encoding="utf-8")
    caller = tmp_path / "caller"
    caller.mkdir()
    alias = caller / "cache"
    alias.symlink_to(protected_target, target_is_directory=True)
    final_root = alias / "new-final-root"
    staging_root = tmp_path / "safe-staging-root"
    assert not final_root.exists()

    _assert_destination_alias_is_rejected(
        replay_result,
        staging_root,
        final_root,
        protected_target,
        monkeypatch,
    )

    assert sentinel.read_text(encoding="utf-8") == (
        '{"production":"sentinel"}'
    )


def test_staging_root_rejects_nonexistent_leaf_beneath_quota_symlink(
    replay_result,
    tmp_path,
    monkeypatch,
):
    protected_target = tmp_path / "state" / "quota_slot_v4"
    protected_target.mkdir(parents=True)
    sentinel = protected_target / "quota-state.json"
    sentinel.write_bytes(b'{"remaining":7}')
    caller = tmp_path / "caller"
    caller.mkdir()
    alias = caller / "scratch"
    alias.symlink_to(protected_target, target_is_directory=True)
    staging_root = alias / "new-staging-root"
    final_root = tmp_path / "safe-final-root"
    assert not staging_root.exists()

    _assert_destination_alias_is_rejected(
        replay_result,
        staging_root,
        final_root,
        protected_target,
        monkeypatch,
    )

    assert sentinel.read_bytes() == b'{"remaining":7}'


def test_destination_root_rejects_nonprotected_ancestor_symlink(
    replay_result,
    tmp_path,
    monkeypatch,
):
    external_target = tmp_path / "external-target"
    external_target.mkdir()
    sentinel = external_target / "sentinel.txt"
    sentinel.write_text("external bytes stay unchanged", encoding="utf-8")
    caller = tmp_path / "caller"
    caller.mkdir()
    alias = caller / "ordinary-cache"
    alias.symlink_to(external_target, target_is_directory=True)
    final_root = alias / "publication-root"
    staging_root = tmp_path / "safe-staging-root"
    assert not final_root.exists()

    _assert_destination_alias_is_rejected(
        replay_result,
        staging_root,
        final_root,
        external_target,
        monkeypatch,
    )

    assert sentinel.read_text(encoding="utf-8") == (
        "external bytes stay unchanged"
    )


def test_nested_destination_ancestry_checks_every_symlink_component(
    replay_result,
    tmp_path,
    monkeypatch,
):
    protected_target = tmp_path / "state" / "worker_state_v4"
    protected_target.mkdir(parents=True)
    sentinel = protected_target / "worker-state.json"
    sentinel.write_text('{"status":"idle"}', encoding="utf-8")
    nested_caller = tmp_path / "caller" / "safe" / "level-two"
    nested_caller.mkdir(parents=True)
    alias = nested_caller / "archive"
    alias.symlink_to(protected_target, target_is_directory=True)
    final_root = alias / "nested" / "nonexistent-leaf"
    staging_root = tmp_path / "safe" / "nested" / "staging-root"
    assert not final_root.exists()

    _assert_destination_alias_is_rejected(
        replay_result,
        staging_root,
        final_root,
        protected_target,
        monkeypatch,
    )

    assert sentinel.read_text(encoding="utf-8") == '{"status":"idle"}'


def test_ordinary_nested_publication_roots_without_symlinks_are_allowed(
    replay_result,
    tmp_path,
):
    staging_root = tmp_path / "caller" / "safe" / "nested-staging"
    final_root = tmp_path / "caller" / "safe" / "nested-final"

    publication = publish_replay_artifacts_v4(
        replay_result,
        staging_root,
        final_root,
    )

    assert isinstance(publication, ReplayArtifactPublicationV4)
    assert publication.classification == CLASSIFICATION
    assert publication.boundary == BOUNDARY
    assert publication.final_path == _final_path(
        final_root,
        replay_result,
    ).resolve()
    assert publication.final_path.is_dir()
    assert publication.manifest_path.is_file()
    assert not _incomplete_path(staging_root, replay_result).exists()


def test_nested_symlink_escape_in_runner_inventory_is_rejected(
    replay_result,
    tmp_path,
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.json").write_text("{}", encoding="utf-8")
    linked_directory = Path(replay_result.output_root) / "linked-directory"
    linked_directory.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(
            replay_result,
            tmp_path / "staging",
            tmp_path / "published",
        )

    assert (outside / "external.json").read_text(encoding="utf-8") == "{}"


def test_publication_rejects_raw_mutable_result(tmp_path):
    output_root = _write_runner_artifacts(tmp_path / "runner-output")
    raw = {
        "replay_id": "replay-v4-raw",
        "output_root": output_root,
        "classification": CLASSIFICATION,
        "boundary": BOUNDARY,
    }

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(
            raw,
            tmp_path / "staging",
            tmp_path / "published",
        )

    assert not (tmp_path / "staging").exists()
    assert not (tmp_path / "published").exists()


def test_invalid_replay_classification_fails_before_publication(
    replay_result,
    tmp_path,
):
    invalid = replace(replay_result, classification="PRODUCTION")

    with pytest.raises(ReplayArtifactError):
        publish_replay_artifacts_v4(
            invalid,
            tmp_path / "staging",
            tmp_path / "published",
        )

    assert not (tmp_path / "staging").exists()
    assert not (tmp_path / "published").exists()


@pytest.mark.parametrize("failure_point", ["hash", "read"])
def test_hash_and_artifact_read_failures_are_chained_without_completion(
    replay_result,
    tmp_path,
    monkeypatch,
    failure_point,
):
    failure = OSError(f"synthetic {failure_point} failure")
    if failure_point == "hash":
        def failing_hash(*args, **kwargs):
            del args, kwargs
            raise failure

        monkeypatch.setattr(
            artifact_module.hashlib,
            "sha256",
            failing_hash,
        )
    else:
        original_read_bytes = Path.read_bytes

        def failing_read(path):
            if path.name == "replay_outcome.json":
                raise failure
            return original_read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", failing_read)
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"

    with pytest.raises(ReplayArtifactError) as exc_info:
        publish_replay_artifacts_v4(replay_result, staging_root, final_root)

    assert exc_info.value.__cause__ is failure
    assert "synthetic" not in str(exc_info.value)
    assert not _final_path(final_root, replay_result).exists()
    incomplete = _incomplete_path(staging_root, replay_result)
    assert not (incomplete / MANIFEST_NAME).exists()


def test_manifest_serialization_failure_is_chained_and_not_completed(
    replay_result,
    tmp_path,
    monkeypatch,
):
    failure = TypeError("synthetic manifest serialization failure")

    def failing_dumps(*args, **kwargs):
        raise failure

    monkeypatch.setattr(artifact_module.json, "dumps", failing_dumps)
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"

    with pytest.raises(ReplayArtifactError) as exc_info:
        publish_replay_artifacts_v4(replay_result, staging_root, final_root)

    assert exc_info.value.__cause__ is failure
    assert not _final_path(final_root, replay_result).exists()
    assert not (
        _incomplete_path(staging_root, replay_result) / MANIFEST_NAME
    ).exists()


def test_manifest_write_failure_does_not_claim_completion(
    replay_result,
    tmp_path,
    monkeypatch,
):
    failure = OSError("synthetic manifest write failure")
    original_write_bytes = Path.write_bytes

    def failing_manifest_write(path, data):
        if MANIFEST_NAME in path.name:
            raise failure
        return original_write_bytes(path, data)

    monkeypatch.setattr(Path, "write_bytes", failing_manifest_write)
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"

    with pytest.raises(ReplayArtifactError) as exc_info:
        publish_replay_artifacts_v4(replay_result, staging_root, final_root)

    assert exc_info.value.__cause__ is failure
    assert not _final_path(final_root, replay_result).exists()
    assert not (
        _incomplete_path(staging_root, replay_result) / MANIFEST_NAME
    ).exists()


def test_file_flush_failure_is_chained_without_atomic_rename(
    replay_result,
    tmp_path,
    monkeypatch,
):
    failure = OSError("synthetic fsync failure")
    rename_calls = []

    def failing_fsync(fd):
        del fd
        raise failure

    monkeypatch.setattr(artifact_module.os, "fsync", failing_fsync)
    monkeypatch.setattr(
        artifact_module.os,
        "replace",
        lambda *args: rename_calls.append(args),
    )

    with pytest.raises(ReplayArtifactError) as exc_info:
        publish_replay_artifacts_v4(
            replay_result,
            tmp_path / "staging",
            tmp_path / "published",
        )

    assert exc_info.value.__cause__ is failure
    assert rename_calls == []
    assert not _final_path(tmp_path / "published", replay_result).exists()


def test_cross_device_atomic_rename_fails_without_copy_fallback(
    replay_result,
    tmp_path,
    monkeypatch,
):
    failure = OSError(errno.EXDEV, "synthetic cross-device rename")
    calls = []

    def failing_replace(source, target):
        calls.append((source, target))
        raise failure

    monkeypatch.setattr(artifact_module.os, "replace", failing_replace)
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"

    with pytest.raises(ReplayArtifactError) as exc_info:
        publish_replay_artifacts_v4(replay_result, staging_root, final_root)

    assert exc_info.value.__cause__ is failure
    assert len(calls) == 1
    assert not _final_path(final_root, replay_result).exists()
    incomplete = _incomplete_path(staging_root, replay_result)
    assert incomplete.exists()
    assert (incomplete / MANIFEST_NAME).is_file()


def test_existing_publication_verification_failure_is_chained_and_safe(
    replay_result,
    tmp_path,
    monkeypatch,
):
    publication, staging_root, final_root = _publish(replay_result, tmp_path)
    failure = OSError("synthetic existing verification failure")
    original_read_bytes = Path.read_bytes

    def failing_existing_read(path):
        if Path(path).is_relative_to(publication.final_path):
            raise failure
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", failing_existing_read)

    with pytest.raises(ReplayArtifactError) as exc_info:
        publish_replay_artifacts_v4(replay_result, staging_root, final_root)

    assert exc_info.value.__cause__ is failure
    assert "synthetic" not in str(exc_info.value)
    assert publication.final_path.exists()


def test_runner_result_can_be_published_without_rerunning_execution(
    bundle,
    tmp_path,
    monkeypatch,
):
    replay_result = run_replay_v4(bundle, tmp_path / "runner-output")
    fixture_before = FIXTURE_PATH.read_bytes()
    monkeypatch.setattr(
        runner_module,
        "run_replay_v4",
        _fail_if_called("replay execution"),
    )
    monkeypatch.setattr(
        master_module,
        "run_master_engine_v4",
        _fail_if_called("master engine"),
    )

    publication = publish_replay_artifacts_v4(
        replay_result,
        tmp_path / "staging",
        tmp_path / "published",
    )

    manifest = _read_manifest(publication.final_path)
    assert publication.replay_id == replay_result.replay_id
    assert publication.fixture_id == replay_result.fixture_id
    assert publication.bundle_hash == replay_result.bundle_hash
    assert manifest["source_replay_schema_version"] == 2
    assert len(manifest["artifacts"]) == 8
    assert FIXTURE_PATH.read_bytes() == fixture_before


def test_publication_and_comparison_do_not_cross_protected_boundaries(
    replay_result,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        master_module,
        "run_master_engine_v4",
        _fail_if_called("master engine"),
    )
    monkeypatch.setattr(
        runner_module,
        "run_replay_v4",
        _fail_if_called("replay runner"),
    )
    monkeypatch.setattr(scanner_module, "scan_market", _fail_if_called("scanner"))
    monkeypatch.setattr(
        stateful_worker_module,
        "run_master_engine_worker_v4",
        _fail_if_called("stateful worker"),
    )
    monkeypatch.setattr(
        quota_worker_module,
        "run_quota_slot_worker_v4",
        _fail_if_called("quota worker"),
    )
    monkeypatch.setattr(
        telegram_runner_module,
        "run_telegram_polling_v4",
        _fail_if_called("Telegram"),
    )
    monkeypatch.setattr(
        master_module,
        "save_production_evidence",
        _fail_if_called("production evidence"),
    )
    monkeypatch.setattr(requests, "get", _fail_if_called("requests.get"))
    monkeypatch.setattr(
        socket,
        "create_connection",
        _fail_if_called("socket"),
    )

    publication, _, _ = _publish(replay_result, tmp_path)
    comparison = compare_replay_artifacts_v4(
        publication.final_path,
        publication.final_path,
    )

    assert comparison.matches is True
    assert all(
        path.resolve().is_relative_to(tmp_path.resolve())
        for path in tmp_path.rglob("*")
    )


def test_safe_errors_do_not_expose_artifact_content_or_paths(
    bundle,
    tmp_path,
):
    secret_marker = "api" + "_key=" + "sensitive-value"
    source = _write_runner_artifacts(tmp_path / "runner-output")
    (source / "replay_outcome.json").write_text(
        secret_marker,
        encoding="utf-8",
    )
    result = _make_result(bundle, source)
    staging_root = tmp_path / "staging"
    final_root = tmp_path / "published"
    publish_replay_artifacts_v4(result, staging_root, final_root)
    (source / "replay_outcome.json").write_text("different", encoding="utf-8")

    with pytest.raises(ReplayArtifactError) as first:
        publish_replay_artifacts_v4(result, staging_root, final_root)
    with pytest.raises(ReplayArtifactError) as repeated:
        publish_replay_artifacts_v4(result, staging_root, final_root)

    assert str(first.value) == str(repeated.value)
    assert secret_marker not in str(first.value)
    assert str(source) not in str(first.value)
    assert str(final_root) not in str(first.value)


def test_import_is_side_effect_free_and_has_no_execution_dependencies(
    tmp_path,
    monkeypatch,
):
    source_path = Path(artifact_module.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.casefold() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.casefold())

    forbidden_imports = {
        "engine.master_engine_v4",
        "engine.scanner",
        "engine.stateful_worker_v4",
        "engine.quota_slot_worker_v4",
        "engine.telegram_application_v4",
        "engine.telegram_runtime_v4",
        "engine.telegram_sdk_runner_v4",
        "requests",
        "socket",
        "ccxt",
        "openai",
    }
    assert imported.isdisjoint(forbidden_imports)
    assert "datetime.now" not in source
    assert "datetime.utcnow" not in source
    assert "time.time" not in source
    assert "uuid4" not in source
    assert "random." not in source
    assert "os.environ" not in source
    assert "getenv" not in source

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "getenv", _fail_if_called("environment"))
    monkeypatch.setattr(
        socket,
        "create_connection",
        _fail_if_called("network"),
    )
    probe_name = "_replay_artifact_v4_import_safety_probe"
    spec = importlib_util.spec_from_file_location(probe_name, source_path)
    assert spec is not None and spec.loader is not None
    probe_module = importlib_util.module_from_spec(spec)
    sys.modules[probe_name] = probe_module
    try:
        spec.loader.exec_module(probe_module)
    finally:
        sys.modules.pop(probe_name, None)

    assert list(tmp_path.iterdir()) == []


def test_fixture_integrity_is_preserved():
    assert hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest() == (
        FIXTURE_SHA256
    )
