"""Fail-closed Phase 07 paper-signal artifact publication."""

from __future__ import annotations

import copy
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping


PAPER_OBSERVATION_DIRECTORY = "observations"
PAPER_EVALUATION_DIRECTORY = "evaluation_cycles"
PAPER_PROGRESS_DIRECTORY = "progress"

_PAPER_CLASSIFICATION = "PAPER_SIGNAL"
_PAPER_EXECUTION_BOUNDARY = "LIVE_MARKET_OBSERVATION_NO_CAPITAL"
_FORBIDDEN_ROOT_NAMES = frozenset(
    {
        "replay",
        "replay_artifacts",
        "production_evidence",
        "validated_snapshots_v4",
        "pre_delivery",
        "pine_delivery",
        "telegram_state",
        "position_ledger",
    }
)
_OBSERVATION_ID_PATTERN = re.compile(r"^PSO-[0-9a-f]{64}$")
_SAFE_EVALUATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ALLOWED_MODES = frozenset({"SWING", "INTRADAY", "SCALP"})


class PaperSignalArtifactError(RuntimeError):
    """Raised when paper-signal artifact publication fails safely."""


def publish_observation_artifact(
    *,
    paper_root: str | os.PathLike[str],
    payload: Mapping[str, Any],
) -> Path:
    """Publish one immutable paper-observation artifact."""

    copied = _require_mapping(payload)
    _require_paper_envelope(copied)
    observation_id = copied.get("paper_observation_id")
    if (
        not isinstance(observation_id, str)
        or _OBSERVATION_ID_PATTERN.fullmatch(observation_id) is None
    ):
        raise PaperSignalArtifactError("invalid paper observation identity")
    return _publish(
        paper_root=paper_root,
        directory_name=PAPER_OBSERVATION_DIRECTORY,
        filename=f"{observation_id}.json",
        payload=copied,
    )


def publish_evaluation_cycle_artifact(
    *,
    paper_root: str | os.PathLike[str],
    payload: Mapping[str, Any],
) -> Path:
    """Publish one immutable paper evaluation-cycle artifact."""

    copied = _require_mapping(payload)
    mode = copied.get("mode")
    if not isinstance(mode, str) or mode not in _ALLOWED_MODES:
        raise PaperSignalArtifactError("invalid evaluation-cycle mode")
    identity = copied.get("source_evaluation_id")
    if (
        not isinstance(identity, str)
        or not identity.strip()
        or _SAFE_EVALUATION_ID_PATTERN.fullmatch(identity) is None
        or identity in {".", ".."}
    ):
        raise PaperSignalArtifactError("invalid evaluation-cycle identity")
    return _publish(
        paper_root=paper_root,
        directory_name=PAPER_EVALUATION_DIRECTORY,
        filename=f"{mode}__{identity}.json",
        payload=copied,
    )


def publish_progress_artifact(
    *,
    paper_root: str | os.PathLike[str],
    payload: Mapping[str, Any],
) -> Path:
    """Publish the canonical Phase 07 progress artifact."""

    copied = _require_mapping(payload)
    _require_paper_envelope(copied)
    if copied.get("schema_name") != "paper-signal-progress":
        raise PaperSignalArtifactError("invalid progress schema")
    return _publish(
        paper_root=paper_root,
        directory_name=PAPER_PROGRESS_DIRECTORY,
        filename="paper-signal-progress.json",
        payload=copied,
    )


def _publish(
    *,
    paper_root: str | os.PathLike[str],
    directory_name: str,
    filename: str,
    payload: Mapping[str, Any],
) -> Path:
    try:
        artifact_bytes = _canonical_artifact_bytes(payload)
        root = _prepare_root(paper_root)
        directory = _prepare_directory(root, directory_name)
        final_path = directory / filename
        _assert_regular_or_absent(final_path)
        if final_path.exists():
            if final_path.read_bytes() == artifact_bytes:
                return final_path.resolve(strict=True)
            raise PaperSignalArtifactError("conflicting artifact already exists")

        temporary_path: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{filename}.", suffix=".tmp", dir=directory
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(artifact_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            _assert_regular_file(temporary_path)
            os.replace(temporary_path, final_path)
            temporary_path = None
            _fsync_directory(directory)
            _assert_regular_file(final_path)
            return final_path.resolve(strict=True)
        except PaperSignalArtifactError:
            raise
        except OSError as exc:
            raise PaperSignalArtifactError("artifact publication failed") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
    except PaperSignalArtifactError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise PaperSignalArtifactError("artifact publication failed") from exc


def _prepare_root(paper_root: str | os.PathLike[str]) -> Path:
    try:
        root = Path(paper_root)
    except TypeError as exc:
        raise PaperSignalArtifactError("invalid paper artifact root") from exc
    if not root.name:
        raise PaperSignalArtifactError("invalid paper artifact root")
    if root.name.lower() in _FORBIDDEN_ROOT_NAMES:
        raise PaperSignalArtifactError("forbidden paper artifact root")
    _reject_symlink_ancestry(root)
    if root.exists():
        _assert_directory(root)
    else:
        try:
            root.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise PaperSignalArtifactError("paper artifact root creation failed") from exc
    _reject_symlink_ancestry(root)
    _assert_directory(root)
    return root.resolve(strict=True)


def _prepare_directory(root: Path, directory_name: str) -> Path:
    directory = root / directory_name
    _reject_symlink_ancestry(directory)
    if directory.exists():
        _assert_directory(directory)
    else:
        try:
            directory.mkdir()
        except OSError as exc:
            raise PaperSignalArtifactError("artifact directory creation failed") from exc
    _reject_symlink_ancestry(directory)
    _assert_directory(directory)
    resolved = directory.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PaperSignalArtifactError("artifact path escapes paper root") from exc
    return resolved


def _canonical_artifact_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise PaperSignalArtifactError("payload is not canonical JSON") from exc
    return encoded + b"\n"


def _require_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise PaperSignalArtifactError("artifact payload must be an object")
    return copy.deepcopy(dict(payload))


def _require_paper_envelope(payload: Mapping[str, Any]) -> None:
    if payload.get("classification") != _PAPER_CLASSIFICATION:
        raise PaperSignalArtifactError("artifact classification must be PAPER_SIGNAL")
    if payload.get("execution_boundary") != _PAPER_EXECUTION_BOUNDARY:
        raise PaperSignalArtifactError("invalid paper artifact execution boundary")


def _reject_symlink_ancestry(path: Path) -> None:
    current = path
    while True:
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise PaperSignalArtifactError("artifact path validation failed") from exc
        else:
            if stat.S_ISLNK(mode):
                raise PaperSignalArtifactError("symlink artifact paths are prohibited")
        parent = current.parent
        if parent == current:
            return
        current = parent


def _assert_directory(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise PaperSignalArtifactError("artifact directory validation failed") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise PaperSignalArtifactError("paper artifact root must be a directory")


def _assert_regular_or_absent(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    except OSError as exc:
        raise PaperSignalArtifactError("artifact destination validation failed") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise PaperSignalArtifactError("artifact destination is not a regular file")


def _assert_regular_file(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise PaperSignalArtifactError("artifact file validation failed") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise PaperSignalArtifactError("published artifact is not a regular file")


def _fsync_directory(directory: Path) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        os.fsync(descriptor)
    except OSError as exc:
        raise PaperSignalArtifactError("artifact directory synchronization failed") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
