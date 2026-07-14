"""Deterministic Replay V4 artifact publication and comparison."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping

from engine.replay_contract_v4 import REPLAY_BUNDLE_SCHEMA_VERSION
from engine.replay_runner_v4 import ReplayExecutionResultV4


_CLASSIFICATION = "REPLAY"
_BOUNDARY = "MASTER_ENGINE_RECORDED_INPUT"
_MANIFEST_NAME = "replay_manifest.json"
_MANIFEST_VERSION = 1
_COMPLETION_STATE = "COMPLETE"
_NON_PRODUCTION_NOTICE = (
    "Deterministic replay output; not production evidence, live-market "
    "evidence, a backtest, or a profitability claim."
)
_REPLAY_ID_PATTERN = re.compile(r"^replay-v4-[a-z0-9-]+$")
_PROTECTED_PATH_PARTS = frozenset(
    {
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
    }
)
_MANIFEST_FIELDS = frozenset(
    {
        "manifest_version",
        "classification",
        "boundary",
        "replay_id",
        "fixture_id",
        "bundle_hash",
        "result_hash",
        "fixed_execution_time",
        "source_replay_schema_version",
        "artifacts",
        "completion_state",
        "non_production_notice",
    }
)
_INVENTORY_FIELDS = frozenset({"relative_path", "sha256", "size_bytes"})
_SEMANTIC_MANIFEST_FIELDS = (
    "manifest_version",
    "classification",
    "boundary",
    "replay_id",
    "fixture_id",
    "bundle_hash",
    "result_hash",
    "fixed_execution_time",
    "source_replay_schema_version",
    "completion_state",
    "non_production_notice",
)


class ReplayArtifactError(RuntimeError):
    """Raised when replay artifacts cannot be handled safely."""


@dataclass(frozen=True)
class ReplayArtifactComparisonV4:
    matches: bool
    expected_hash: str
    actual_hash: str
    mismatched_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]
    unexpected_paths: tuple[str, ...]
    semantic_mismatches: tuple[str, ...]
    safe_summary: str


@dataclass(frozen=True)
class ReplayArtifactPublicationV4:
    replay_id: str
    fixture_id: str
    bundle_hash: str
    result_hash: str
    final_path: Path
    manifest_path: Path
    artifact_count: int
    reused_existing: bool
    classification: str
    boundary: str


def calculate_replay_result_hash_v4(result):
    """Return a canonical semantic hash for a replay execution result."""
    _require_result_type(result)
    payload = {
        "replay_id": result.replay_id,
        "fixture_id": result.fixture_id,
        "bundle_hash": result.bundle_hash,
        "fixed_execution_time": result.fixed_execution_time,
        "classification": result.classification,
        "boundary": result.boundary,
        "normalized_master_result": _thaw(result.normalized_master_result),
    }
    try:
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    except ReplayArtifactError:
        raise
    except Exception as exc:
        raise ReplayArtifactError("Replay artifact hashing failed") from exc


def build_replay_manifest_v4(replay_result, artifact_files):
    """Build an immutable deterministic manifest without writing it."""
    _require_result_type(replay_result)
    try:
        root = _validate_source_root(replay_result.output_root)
        inventory = _build_inventory(root, artifact_files)
        manifest = {
            "manifest_version": _MANIFEST_VERSION,
            "classification": _CLASSIFICATION,
            "boundary": _BOUNDARY,
            "replay_id": replay_result.replay_id,
            "fixture_id": replay_result.fixture_id,
            "bundle_hash": replay_result.bundle_hash,
            "result_hash": calculate_replay_result_hash_v4(replay_result),
            "fixed_execution_time": replay_result.fixed_execution_time,
            "source_replay_schema_version": REPLAY_BUNDLE_SCHEMA_VERSION,
            "artifacts": inventory,
            "completion_state": _COMPLETION_STATE,
            "non_production_notice": _NON_PRODUCTION_NOTICE,
        }
        return _freeze(manifest)
    except ReplayArtifactError:
        raise
    except Exception as exc:
        raise ReplayArtifactError("Replay manifest creation failed") from exc


def compare_replay_artifacts_v4(expected, actual):
    """Compare two completed publication directories without modifying either."""
    try:
        expected_root = _validate_completed_root(expected)
        actual_root = _validate_completed_root(actual)
        expected_manifest = _load_manifest(expected_root)
        actual_manifest = _load_manifest(actual_root)
        _validate_manifest_shape(expected_manifest)
        _validate_manifest_shape(actual_manifest)

        semantic_mismatches = tuple(
            field
            for field in _SEMANTIC_MANIFEST_FIELDS
            if expected_manifest[field] != actual_manifest[field]
        )
        expected_inventory = _inventory_by_path(expected_manifest["artifacts"])
        actual_inventory = _inventory_by_path(actual_manifest["artifacts"])
        expected_paths = set(expected_inventory)
        actual_files = _publication_files(actual_root)
        missing_paths = tuple(sorted(expected_paths - actual_files))
        unexpected_paths = tuple(sorted(actual_files - expected_paths))
        mismatched_paths = tuple(
            sorted(
                path
                for path in expected_paths & actual_files
                if _hash_file(actual_root / path)
                != expected_inventory[path]["sha256"]
            )
        )
        expected_hash = _manifest_hash(expected_manifest)
        actual_hash = _manifest_hash(actual_manifest)
        matches = not (
            semantic_mismatches
            or missing_paths
            or unexpected_paths
            or mismatched_paths
            or expected_hash != actual_hash
        )
        return ReplayArtifactComparisonV4(
            matches=matches,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            mismatched_paths=mismatched_paths,
            missing_paths=missing_paths,
            unexpected_paths=unexpected_paths,
            semantic_mismatches=semantic_mismatches,
            safe_summary=(
                "Replay artifacts match"
                if matches
                else "Replay artifacts differ"
            ),
        )
    except ReplayArtifactError:
        raise
    except Exception as exc:
        raise ReplayArtifactError("Replay artifact comparison failed") from exc


def publish_replay_artifacts_v4(
    replay_result,
    staging_root,
    final_root,
):
    """Publish runner-local replay artifacts through deterministic staging."""
    _validate_publish_result(replay_result)
    try:
        staging_parent = _validate_publication_root(staging_root)
        final_parent = _validate_publication_root(final_root)
        source_root = _validate_source_root(replay_result.output_root)
        final_path = _publication_path(final_parent, replay_result.replay_id)
        staging_path = _publication_path(
            staging_parent,
            f"{replay_result.replay_id}.incomplete",
        )
        source_files = _collect_source_files(source_root)
        source_manifest = build_replay_manifest_v4(replay_result, source_files)

        if _lexists(staging_path):
            raise ReplayArtifactError("Incomplete replay staging exists")
        if _lexists(final_path):
            return _reuse_existing_publication(
                replay_result,
                final_path,
                source_manifest,
            )

        staging_parent.mkdir(parents=True, exist_ok=True)
        final_parent.mkdir(parents=True, exist_ok=True)
        _ensure_same_filesystem(staging_parent, final_parent)
        staging_path.mkdir()
        _copy_artifacts(source_root, staging_path, source_manifest["artifacts"])
        manifest_bytes = _canonical_bytes(_thaw(source_manifest))
        manifest_path = staging_path / _MANIFEST_NAME
        manifest_path.write_bytes(manifest_bytes)
        _fsync_file(manifest_path)
        _fsync_directory(staging_path)
        os.replace(staging_path, final_path)
        return _publication_result(
            replay_result,
            final_path,
            source_manifest,
            reused_existing=False,
        )
    except ReplayArtifactError:
        raise
    except Exception as exc:
        raise ReplayArtifactError("Replay artifact publication failed") from exc


def _require_result_type(result) -> None:
    if not isinstance(result, ReplayExecutionResultV4):
        raise ReplayArtifactError("Invalid replay artifact input")


def _validate_publish_result(result) -> None:
    _require_result_type(result)
    if (
        result.classification != _CLASSIFICATION
        or result.boundary != _BOUNDARY
        or not _is_valid_replay_id(result.replay_id)
    ):
        raise ReplayArtifactError("Invalid replay artifact input")


def _is_valid_replay_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_REPLAY_ID_PATTERN.fullmatch(value))


def _validate_publication_root(value) -> Path:
    if isinstance(value, bool) or not isinstance(value, (str, Path)):
        raise ReplayArtifactError("Invalid replay artifact path")
    if isinstance(value, str) and not value.strip():
        raise ReplayArtifactError("Invalid replay artifact path")
    path = Path(value)
    if _has_protected_path_part(path):
        raise ReplayArtifactError("Invalid replay artifact path")
    absolute_path = path if path.is_absolute() else Path.cwd() / path
    _validate_existing_publication_ancestry(absolute_path)
    try:
        resolved_path = absolute_path.resolve(strict=False)
    except OSError as exc:
        raise ReplayArtifactError("Invalid replay artifact path") from exc
    if _has_protected_path_part(resolved_path):
        raise ReplayArtifactError("Invalid replay artifact path")
    return resolved_path


def _validate_existing_publication_ancestry(path: Path) -> None:
    existing_ancestor = path
    while not _lexists(existing_ancestor):
        parent = existing_ancestor.parent
        if parent == existing_ancestor:
            raise ReplayArtifactError("Invalid replay artifact path")
        existing_ancestor = parent

    components = []
    component = existing_ancestor
    while True:
        components.append(component)
        if component.parent == component:
            break
        component = component.parent

    try:
        for component in reversed(components):
            if stat.S_ISLNK(component.lstat().st_mode):
                raise ReplayArtifactError("Invalid replay artifact path")
        if not stat.S_ISDIR(existing_ancestor.lstat().st_mode):
            raise ReplayArtifactError("Invalid replay artifact path")
    except ReplayArtifactError:
        raise
    except OSError as exc:
        raise ReplayArtifactError("Invalid replay artifact path") from exc


def _validate_source_root(value) -> Path:
    if isinstance(value, bool) or not isinstance(value, (str, Path)):
        raise ReplayArtifactError("Invalid replay artifact input")
    path = Path(value)
    if path.is_symlink() or not path.is_dir():
        raise ReplayArtifactError("Invalid replay artifact input")
    return path.resolve()


def _validate_completed_root(value) -> Path:
    if isinstance(value, bool) or not isinstance(value, (str, Path)):
        raise ReplayArtifactError("Replay artifact comparison failed")
    path = Path(value)
    if path.is_symlink() or not path.is_dir():
        raise ReplayArtifactError("Replay artifact comparison failed")
    return path.resolve()


def _has_protected_path_part(path: Path) -> bool:
    return any(part.casefold() in _PROTECTED_PATH_PARTS for part in path.parts)


def _publication_path(parent: Path, name: str) -> Path:
    if not _is_valid_replay_id(name.removesuffix(".incomplete")):
        raise ReplayArtifactError("Invalid replay artifact input")
    path = parent / name
    try:
        path.resolve().relative_to(parent)
    except ValueError as exc:
        raise ReplayArtifactError("Invalid replay artifact path") from exc
    return path


def _collect_source_files(root: Path) -> tuple[Path, ...]:
    entries = tuple(sorted(root.rglob("*")))
    for entry in entries:
        if entry.is_symlink():
            raise ReplayArtifactError("Invalid replay artifact input")
    files = tuple(entry for entry in entries if entry.is_file())
    if not files:
        raise ReplayArtifactError("Invalid replay artifact input")
    return files


def _build_inventory(root: Path, artifact_files) -> tuple[dict[str, Any], ...]:
    try:
        files = tuple(artifact_files)
    except TypeError as exc:
        raise ReplayArtifactError("Invalid replay artifact input") from exc
    inventory = []
    seen = set()
    for value in files:
        if isinstance(value, bool) or not isinstance(value, (str, Path)):
            raise ReplayArtifactError("Invalid replay artifact input")
        path = Path(value)
        if path.is_symlink() or not path.is_file():
            raise ReplayArtifactError("Invalid replay artifact input")
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise ReplayArtifactError("Invalid replay artifact input") from exc
        if relative.is_absolute() or ".." in relative.parts:
            raise ReplayArtifactError("Invalid replay artifact input")
        relative_path = relative.as_posix()
        if relative_path in seen:
            raise ReplayArtifactError("Invalid replay artifact input")
        seen.add(relative_path)
        inventory.append(
            {
                "relative_path": relative_path,
                "sha256": _hash_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return tuple(sorted(inventory, key=lambda item: item["relative_path"]))


def _hash_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ReplayArtifactError("Invalid replay artifact input")
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except ReplayArtifactError:
        raise
    except Exception as exc:
        raise ReplayArtifactError("Replay artifact hashing failed") from exc


def _copy_artifacts(
    source_root: Path,
    staging_path: Path,
    inventory,
) -> None:
    for entry in inventory:
        relative = Path(entry["relative_path"])
        source = source_root / relative
        destination = staging_path / relative
        if source.is_symlink() or not source.is_file():
            raise ReplayArtifactError("Invalid replay artifact input")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if _lexists(destination):
            raise ReplayArtifactError("Replay artifact publication failed")
        destination.write_bytes(source.read_bytes())
        if _hash_file(destination) != entry["sha256"]:
            raise ReplayArtifactError("Replay artifact publication failed")
        _fsync_file(destination)


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_same_filesystem(staging_parent: Path, final_parent: Path) -> None:
    if staging_parent.stat().st_dev != final_parent.stat().st_dev:
        raise ReplayArtifactError("Invalid replay artifact path")


def _reuse_existing_publication(
    replay_result: ReplayExecutionResultV4,
    final_path: Path,
    source_manifest,
) -> ReplayArtifactPublicationV4:
    if final_path.is_symlink() or not final_path.is_dir():
        raise ReplayArtifactError("Replay artifact collision")
    try:
        existing_manifest = _load_manifest(final_path)
        _validate_manifest_shape(existing_manifest)
        expected_manifest = _thaw(source_manifest)
        if any(
            existing_manifest[field] != expected_manifest[field]
            for field in _SEMANTIC_MANIFEST_FIELDS
        ):
            raise ReplayArtifactError("Replay artifact collision")
        expected_inventory = _inventory_by_path(expected_manifest["artifacts"])
        existing_inventory = _inventory_by_path(existing_manifest["artifacts"])
        if expected_inventory != existing_inventory:
            raise ReplayArtifactError("Replay artifact collision")
        expected_paths = set(expected_inventory)
        physical_files = _publication_files(final_path)
        if physical_files != expected_paths:
            raise ReplayArtifactError("Replay artifact collision")
        for relative_path, entry in expected_inventory.items():
            path = final_path / relative_path
            if (
                _hash_file(path) != entry["sha256"]
                or path.stat().st_size != entry["size_bytes"]
            ):
                raise ReplayArtifactError("Replay artifact collision")
        return _publication_result(
            replay_result,
            final_path,
            source_manifest,
            reused_existing=True,
        )
    except ReplayArtifactError:
        raise
    except Exception as exc:
        raise ReplayArtifactError("Replay artifact comparison failed") from exc


def _publication_result(
    replay_result: ReplayExecutionResultV4,
    final_path: Path,
    manifest,
    *,
    reused_existing: bool,
) -> ReplayArtifactPublicationV4:
    manifest_data = _thaw(manifest)
    resolved_final = final_path.resolve()
    return ReplayArtifactPublicationV4(
        replay_id=replay_result.replay_id,
        fixture_id=replay_result.fixture_id,
        bundle_hash=replay_result.bundle_hash,
        result_hash=manifest_data["result_hash"],
        final_path=resolved_final,
        manifest_path=(resolved_final / _MANIFEST_NAME).resolve(),
        artifact_count=len(manifest_data["artifacts"]),
        reused_existing=reused_existing,
        classification=_CLASSIFICATION,
        boundary=_BOUNDARY,
    )


def _load_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / _MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ReplayArtifactError("Replay artifact collision")
    try:
        value = json.loads(manifest_path.read_bytes().decode("utf-8"))
    except ReplayArtifactError:
        raise
    except Exception as exc:
        raise ReplayArtifactError("Replay artifact comparison failed") from exc
    if not isinstance(value, dict):
        raise ReplayArtifactError("Replay artifact collision")
    return value


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    if set(manifest) != _MANIFEST_FIELDS:
        raise ReplayArtifactError("Replay artifact collision")
    if (
        manifest["manifest_version"] != _MANIFEST_VERSION
        or manifest["classification"] != _CLASSIFICATION
        or manifest["boundary"] != _BOUNDARY
        or manifest["source_replay_schema_version"]
        != REPLAY_BUNDLE_SCHEMA_VERSION
        or manifest["completion_state"] != _COMPLETION_STATE
        or manifest["non_production_notice"] != _NON_PRODUCTION_NOTICE
        or not _is_valid_replay_id(manifest["replay_id"])
    ):
        raise ReplayArtifactError("Replay artifact collision")
    for field in (
        "fixture_id",
        "bundle_hash",
        "result_hash",
        "fixed_execution_time",
    ):
        if not isinstance(manifest[field], str) or not manifest[field]:
            raise ReplayArtifactError("Replay artifact collision")
    _inventory_by_path(manifest["artifacts"])


def _inventory_by_path(inventory) -> dict[str, dict[str, Any]]:
    if not isinstance(inventory, (list, tuple)):
        raise ReplayArtifactError("Replay artifact collision")
    by_path = {}
    for entry in inventory:
        if not isinstance(entry, Mapping) or set(entry) != _INVENTORY_FIELDS:
            raise ReplayArtifactError("Replay artifact collision")
        relative_path = entry["relative_path"]
        digest = entry["sha256"]
        size = entry["size_bytes"]
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or Path(relative_path).is_absolute()
            or ".." in Path(relative_path).parts
            or relative_path in by_path
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise ReplayArtifactError("Replay artifact collision")
        by_path[relative_path] = {
            "relative_path": relative_path,
            "sha256": digest,
            "size_bytes": size,
        }
    return by_path


def _publication_files(root: Path) -> set[str]:
    files = set()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ReplayArtifactError("Replay artifact collision")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative != _MANIFEST_NAME:
                files.add(relative)
    return files


def _manifest_hash(manifest: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(manifest)).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _thaw(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _freeze(value: Any):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(nested) for key, nested in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(nested) for nested in value)
    return value


def _thaw(value: Any):
    if isinstance(value, Mapping):
        return {key: _thaw(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw(nested) for nested in value]
    return value


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)
