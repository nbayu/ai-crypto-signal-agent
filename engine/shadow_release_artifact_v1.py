"""Fail-closed Phase 08 Shadow Release artifact publication."""

from __future__ import annotations

import copy
import hashlib
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from engine.shadow_release_contract_v1 import (
    SHADOW_RELEASE_CAPITAL_EXPOSURE,
    SHADOW_RELEASE_CLASSIFICATION,
    SHADOW_RELEASE_EXECUTION_BOUNDARY,
    SHADOW_RELEASE_ORDER_EXECUTION,
    SHADOW_RELEASE_SCHEMA_NAME,
    SHADOW_RELEASE_SCHEMA_VERSION,
    ShadowReleaseContractError,
    canonical_json_bytes,
    compare_semantic_projections,
)


SHADOW_RELEASE_RUN_DIRECTORY = "runs"
SHADOW_RELEASE_LOCK_DIRECTORY = ".locks"

_INPUT_SCHEMA_NAME = "shadow-release-input"
_ROOT_DIRECTORY = "shadow_release"
_ROOT_PARENT_DIRECTORY = "data"
_RUN_ID_PATTERN = re.compile(r"^SHR-[0-9a-f]{64}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
_ALLOWED_MODES = frozenset({"SWING", "INTRADAY", "SCALP"})
_ALLOWED_OUTCOME_KINDS = frozenset({"PUBLISHED_SIGNAL", "NO_TRADE"})
_FAILURE_CODES = frozenset(
    {
        "INPUT_CONTRACT_REJECTED",
        "SOURCE_AUTHORITY_MISSING",
        "COMPONENT_VERSION_UNSUPPORTED",
        "SHADOW_EXECUTION_FAILED",
        "ARTIFACT_PUBLICATION_FAILED",
        "ROOT_ISOLATION_VIOLATION",
        "IDENTITY_COLLISION",
        "CONCURRENCY_CONFLICT",
    }
)
_PROTECTED_ROOT_NAMES = frozenset(
    {
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
        "account",
        "account_state",
        "balance",
        "balance_state",
        "portfolio",
        "portfolio_state",
        "order",
        "orders",
        "exchange",
    }
)
_FORBIDDEN_FIELDS = frozenset(
    {
        "exchange_credentials",
        "private_endpoint",
        "order_payload",
        "position_size",
        "account_state",
        "balance_state",
        "portfolio_state",
        "exchange_execution",
        "api_secret",
        "private_key",
    }
)
_RUN_FIELDS = frozenset(
    {
        "schema_version",
        "schema_name",
        "classification",
        "execution_boundary",
        "capital_exposure",
        "order_execution",
        "position_authority",
        "shadow_run_id",
        "source_commit",
        "source_evaluation_id",
        "mode",
        "market_identity",
        "outcome_kind",
        "source_publication_ref",
        "serialized_input_hash",
        "expected_decision",
        "expected_decision_hash",
        "observed_decision",
        "observed_decision_hash",
        "comparison",
        "component_versions",
        "evaluation_started_at",
        "evaluation_completed_at",
        "started_at",
        "completed_at",
        "operational_duration_ms",
        "failure",
        "content_hash",
    }
)
_MARKET_FIELDS = frozenset(
    {"venue", "symbol", "interval", "market_data_source", "market_input_hash"}
)
_SOURCE_FIELDS = frozenset(
    {"signal_id", "delivery_id", "mode", "published_at", "source_payload_hash"}
)
_COMPARISON_FIELDS = frozenset(
    {"outcome", "primary_code", "secondary_codes"}
)
_COMPONENT_VERSION_FIELDS = frozenset(
    {
        "master_engine",
        "validated_pipeline",
        "pre_delivery",
        "shadow_contract",
        "shadow_runner",
    }
)
_FAILURE_FIELDS = frozenset({"primary_code", "component", "message"})


class ShadowReleaseArtifactError(RuntimeError):
    """Raised when Shadow Release evidence cannot be published safely."""


def publish_shadow_run_artifact(
    *,
    shadow_root: str | os.PathLike[str],
    payload: Mapping[str, Any],
) -> Path:
    """Publish one immutable completed Shadow Release run artifact."""

    completed = _validate_completed_run(payload)
    artifact_bytes = canonical_json_bytes(completed) + b"\n"
    root = _prepare_root(shadow_root)
    run_directory = _prepare_directory(root, SHADOW_RELEASE_RUN_DIRECTORY)
    lock_directory = _prepare_directory(root, SHADOW_RELEASE_LOCK_DIRECTORY)
    final_path = run_directory / f'{completed["shadow_run_id"]}.json'
    _require_beneath(final_path, root)

    lock_path = lock_directory / f'{completed["shadow_run_id"]}.lock'
    lock_descriptor: int | None = None
    try:
        lock_descriptor = _acquire_lock(lock_path)
        _assert_regular_or_absent(final_path)
        if final_path.exists():
            try:
                existing_bytes = final_path.read_bytes()
            except OSError as exc:
                raise ShadowReleaseArtifactError(
                    "completed artifact validation failed"
                ) from None
            if existing_bytes == artifact_bytes:
                return final_path.resolve(strict=True)
            raise ShadowReleaseArtifactError("identity collision")

        return _atomic_publish(
            run_directory=run_directory,
            final_path=final_path,
            artifact_bytes=artifact_bytes,
            identity=completed["shadow_run_id"],
        )
    except ShadowReleaseArtifactError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise ShadowReleaseArtifactError("artifact publication failed") from None
    finally:
        if lock_descriptor is not None:
            try:
                os.close(lock_descriptor)
            except OSError:
                pass
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass


def _validate_completed_run(value: Any) -> dict[str, Any]:
    try:
        run = _exact_mapping(value, _RUN_FIELDS, "completed run")
        _reject_forbidden_fields(run)
        if type(run["schema_version"]) is not int or (
            run["schema_version"] != SHADOW_RELEASE_SCHEMA_VERSION
        ):
            raise ShadowReleaseArtifactError("invalid run schema version")
        if run["schema_name"] != SHADOW_RELEASE_SCHEMA_NAME:
            raise ShadowReleaseArtifactError("invalid run schema name")
        if run["classification"] != SHADOW_RELEASE_CLASSIFICATION:
            raise ShadowReleaseArtifactError("invalid run classification")
        if run["execution_boundary"] != SHADOW_RELEASE_EXECUTION_BOUNDARY:
            raise ShadowReleaseArtifactError("invalid run execution boundary")
        if run["capital_exposure"] != SHADOW_RELEASE_CAPITAL_EXPOSURE:
            raise ShadowReleaseArtifactError("invalid capital boundary")
        if run["order_execution"] != SHADOW_RELEASE_ORDER_EXECUTION:
            raise ShadowReleaseArtifactError("invalid order boundary")
        if run["position_authority"] != "NONE":
            raise ShadowReleaseArtifactError("invalid position authority")

        _require_run_id(run["shadow_run_id"])
        _require_commit(run["source_commit"])
        _require_text(run["source_evaluation_id"], "source evaluation identity")
        if run["mode"] not in _ALLOWED_MODES:
            raise ShadowReleaseArtifactError("invalid run mode")
        _validate_market_identity(run["market_identity"])
        if run["outcome_kind"] not in _ALLOWED_OUTCOME_KINDS:
            raise ShadowReleaseArtifactError("invalid outcome kind")
        _validate_source_publication(
            run["source_publication_ref"], run["outcome_kind"]
        )
        _require_sha256(run["serialized_input_hash"], "serialized input hash")
        _require_sha256(run["expected_decision_hash"], "expected decision hash")
        _require_sha256(run["observed_decision_hash"], "observed decision hash")
        _validate_versions(run["component_versions"])

        comparison = compare_semantic_projections(
            run["expected_decision"], run["observed_decision"]
        )
        observed_hash = _hash_payload(
            _without_operational_metadata(run["observed_decision"])
        )
        if observed_hash != run["observed_decision_hash"]:
            raise ShadowReleaseArtifactError("observed decision hash mismatch")

        _validate_comparison_and_failure(
            run["comparison"], run["failure"], comparison
        )
        _validate_timestamps_and_duration(run)

        identity = {
            "schema_version": SHADOW_RELEASE_SCHEMA_VERSION,
            "source_commit": run["source_commit"],
            "source_evaluation_id": run["source_evaluation_id"],
            "mode": run["mode"],
            "market_identity": copy.deepcopy(run["market_identity"]),
            "outcome_kind": run["outcome_kind"],
            "source_publication_ref": copy.deepcopy(
                run["source_publication_ref"]
            ),
            "serialized_input_hash": run["serialized_input_hash"],
            "expected_decision_hash": run["expected_decision_hash"],
        }
        if run["shadow_run_id"] != "SHR-" + _hash_payload(identity):
            raise ShadowReleaseArtifactError("shadow identity mismatch")

        supplied_hash = run["content_hash"]
        _require_sha256(supplied_hash, "content hash")
        content = {
            key: copy.deepcopy(item)
            for key, item in run.items()
            if key != "content_hash"
        }
        if supplied_hash != _hash_payload(content):
            raise ShadowReleaseArtifactError("content hash mismatch")
        canonical_json_bytes(run)
        return copy.deepcopy(run)
    except ShadowReleaseArtifactError:
        raise
    except ShadowReleaseContractError as exc:
        raise ShadowReleaseArtifactError("completed run contract rejected") from None
    except (TypeError, ValueError, OverflowError) as exc:
        raise ShadowReleaseArtifactError("completed run contract rejected") from None


def _validate_market_identity(value: Any) -> None:
    market = _exact_mapping(value, _MARKET_FIELDS, "market identity")
    for field in ("venue", "symbol", "interval", "market_data_source"):
        _require_text(market[field], field)
    _require_sha256(market["market_input_hash"], "market input hash")


def _validate_source_publication(value: Any, outcome_kind: str) -> None:
    if outcome_kind == "NO_TRADE":
        if value is not None:
            raise ShadowReleaseArtifactError(
                "NO_TRADE contains publication identity"
            )
        return
    source = _exact_mapping(value, _SOURCE_FIELDS, "source publication")
    _require_text(source["signal_id"], "signal identity")
    _require_text(source["delivery_id"], "delivery identity")
    if source["mode"] not in _ALLOWED_MODES:
        raise ShadowReleaseArtifactError("invalid publication mode")
    _parse_utc(source["published_at"], "publication timestamp")
    _require_sha256(source["source_payload_hash"], "source payload hash")


def _validate_versions(value: Any) -> None:
    versions = _exact_mapping(
        value, _COMPONENT_VERSION_FIELDS, "component versions"
    )
    for field, version in versions.items():
        _require_text(version, f"component version {field}")


def _validate_comparison_and_failure(
    comparison_value: Any,
    failure_value: Any,
    semantic_comparison: Mapping[str, Any],
) -> None:
    comparison = _exact_mapping(
        comparison_value, _COMPARISON_FIELDS, "comparison"
    )
    secondary = comparison["secondary_codes"]
    if not isinstance(secondary, list) or secondary != []:
        raise ShadowReleaseArtifactError("invalid comparison secondary codes")
    if failure_value is None:
        if comparison != dict(semantic_comparison):
            raise ShadowReleaseArtifactError("comparison evidence mismatch")
        if comparison["outcome"] not in {"MATCH", "MISMATCH"}:
            raise ShadowReleaseArtifactError("run is not completed")
        return

    failure = _exact_mapping(failure_value, _FAILURE_FIELDS, "failure")
    if failure["primary_code"] not in _FAILURE_CODES:
        raise ShadowReleaseArtifactError("invalid failure classification")
    _require_text(failure["component"], "failure component")
    message = _require_text(failure["message"], "failure message")
    lowered = message.casefold()
    if any(marker in lowered for marker in ("token=", "secret", "credential")):
        raise ShadowReleaseArtifactError("unsafe failure evidence")
    if comparison != {
        "outcome": "FAILED",
        "primary_code": failure["primary_code"],
        "secondary_codes": [],
    }:
        raise ShadowReleaseArtifactError("failure comparison mismatch")


def _validate_timestamps_and_duration(run: Mapping[str, Any]) -> None:
    evaluation_started = _parse_utc(
        run["evaluation_started_at"], "evaluation start"
    )
    evaluation_completed = _parse_utc(
        run["evaluation_completed_at"], "evaluation completion"
    )
    if evaluation_completed < evaluation_started:
        raise ShadowReleaseArtifactError(
            "evaluation completion precedes evaluation start"
        )
    started = _parse_utc(run["started_at"], "operational start")
    completed = _parse_utc(run["completed_at"], "operational completion")
    if completed < started:
        raise ShadowReleaseArtifactError(
            "operational completion precedes operational start"
        )
    microseconds = _delta_microseconds(completed - started)
    if microseconds % 1000 != 0:
        raise ShadowReleaseArtifactError("operational duration is not exact")
    duration = run["operational_duration_ms"]
    if type(duration) is not int or duration != microseconds // 1000:
        raise ShadowReleaseArtifactError("operational duration mismatch")


def _prepare_root(value: str | os.PathLike[str]) -> Path:
    try:
        root = Path(value)
    except TypeError as exc:
        raise ShadowReleaseArtifactError("invalid shadow artifact root") from None
    if root.name != _ROOT_DIRECTORY or root.parent.name != _ROOT_PARENT_DIRECTORY:
        raise ShadowReleaseArtifactError("invalid shadow artifact root")
    if any(part.casefold() in _PROTECTED_ROOT_NAMES for part in root.parts):
        raise ShadowReleaseArtifactError("protected artifact root")
    _reject_symlink_ancestry(root)
    _assert_directory(root)
    resolved = root.resolve(strict=True)
    _reject_symlink_ancestry(resolved)
    return resolved


def _prepare_directory(root: Path, name: str) -> Path:
    directory = root / name
    _reject_symlink_ancestry(directory)
    if directory.exists():
        _assert_directory(directory)
    else:
        try:
            directory.mkdir()
        except OSError as exc:
            raise ShadowReleaseArtifactError(
                "artifact directory creation failed"
            ) from None
    _reject_symlink_ancestry(directory)
    _assert_directory(directory)
    resolved = directory.resolve(strict=True)
    _require_beneath(resolved, root)
    return resolved


def _acquire_lock(lock_path: Path) -> int:
    _assert_regular_or_absent(lock_path)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except FileExistsError as exc:
        raise ShadowReleaseArtifactError("concurrency conflict") from None
    except OSError as exc:
        raise ShadowReleaseArtifactError("publication lock failed") from None
    try:
        os.write(descriptor, b"shadow-release-lock-v1\n")
        os.fsync(descriptor)
    except OSError as exc:
        try:
            os.close(descriptor)
        finally:
            lock_path.unlink(missing_ok=True)
        raise ShadowReleaseArtifactError("publication lock failed") from None
    return descriptor


def _atomic_publish(
    *,
    run_directory: Path,
    final_path: Path,
    artifact_bytes: bytes,
    identity: str,
) -> Path:
    descriptor: int | None = None
    temporary_path: Path | None = None
    installed = False
    completed = False
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{identity}.", suffix=".tmp", dir=run_directory
        )
        temporary_path = Path(temporary_name)
        _require_beneath(temporary_path, run_directory)
        _assert_regular_file(temporary_path)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(artifact_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        _assert_regular_file(temporary_path)
        _assert_regular_or_absent(final_path)
        if final_path.exists():
            raise ShadowReleaseArtifactError("identity collision")
        os.replace(temporary_path, final_path)
        installed = True
        temporary_path = None
        _fsync_directory(run_directory)
        _assert_regular_file(final_path)
        completed = True
        return final_path.resolve(strict=True)
    except ShadowReleaseArtifactError:
        raise
    except OSError as exc:
        raise ShadowReleaseArtifactError("artifact publication failed") from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        if installed and not completed:
            try:
                final_path.unlink(missing_ok=True)
            except OSError:
                pass


def _exact_mapping(
    value: Any, fields: frozenset[str], label: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or frozenset(value.keys()) != fields:
        raise ShadowReleaseArtifactError(
            f"{label} fields do not match the frozen contract"
        )
    return copy.deepcopy(dict(value))


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShadowReleaseArtifactError(f"invalid {label}")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ShadowReleaseArtifactError(f"invalid {label}")
    return value


def _require_run_id(value: Any) -> str:
    if not isinstance(value, str) or _RUN_ID_PATTERN.fullmatch(value) is None:
        raise ShadowReleaseArtifactError("invalid shadow run identity")
    return value


def _require_commit(value: Any) -> str:
    if not isinstance(value, str) or _COMMIT_PATTERN.fullmatch(value) is None:
        raise ShadowReleaseArtifactError("invalid source commit")
    return value


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or _UTC_PATTERN.fullmatch(value) is None:
        raise ShadowReleaseArtifactError(f"invalid {label}")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ShadowReleaseArtifactError(f"invalid {label}") from None
    if parsed.tzinfo != timezone.utc:
        raise ShadowReleaseArtifactError(f"invalid {label}")
    return parsed


def _without_operational_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key != "operational_metadata"
    }


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _delta_microseconds(delta: Any) -> int:
    return (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.casefold() in _FORBIDDEN_FIELDS:
                raise ShadowReleaseArtifactError(
                    "forbidden execution authority field"
                )
            _reject_forbidden_fields(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_forbidden_fields(item)


def _reject_symlink_ancestry(path: Path) -> None:
    current = path
    while True:
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise ShadowReleaseArtifactError(
                "artifact path validation failed"
            ) from None
        else:
            if stat.S_ISLNK(mode):
                raise ShadowReleaseArtifactError(
                    "symlink artifact paths are prohibited"
                )
        parent = current.parent
        if parent == current:
            return
        current = parent


def _assert_directory(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ShadowReleaseArtifactError("artifact root is unavailable") from None
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise ShadowReleaseArtifactError("artifact root is not a directory")


def _assert_regular_or_absent(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ShadowReleaseArtifactError(
            "artifact destination validation failed"
        ) from None
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ShadowReleaseArtifactError(
            "artifact destination is not a regular file"
        )


def _assert_regular_file(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ShadowReleaseArtifactError("artifact file validation failed") from None
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ShadowReleaseArtifactError("artifact file is not regular")


def _require_beneath(path: Path, root: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ShadowReleaseArtifactError("artifact path escapes shadow root") from None


def _fsync_directory(directory: Path) -> None:
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        descriptor = os.open(directory, flags)
        os.fsync(descriptor)
    except OSError as exc:
        raise ShadowReleaseArtifactError(
            "artifact directory synchronization failed"
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
