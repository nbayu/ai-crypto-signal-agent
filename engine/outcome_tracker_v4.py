from datetime import datetime
from pathlib import Path
import json
import os
import re
import stat
import tempfile
import uuid


OUTCOME_DIRECTORY = Path("data/v4_outcomes")
SCHEMA_VERSION = 1
SNAPSHOT_TYPE = "v4_outcome_tracker_entry"
OUTCOME_INVOCATION_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class OutcomeSnapshotIdentityError(ValueError):
    """Raised when an outcome invocation identity is missing or invalid."""


class OutcomeSnapshotConflictError(RuntimeError):
    """Raised when an invocation path already contains different bytes."""


class OutcomeSnapshotPersistenceError(RuntimeError):
    """Raised when an outcome snapshot cannot be durably persisted."""


def generate_outcome_invocation_id():
    return uuid.uuid4().hex


def validate_outcome_invocation_id(outcome_invocation_id):
    if outcome_invocation_id is None:
        raise OutcomeSnapshotIdentityError(
            "MISSING_OUTCOME_INVOCATION_ID"
        )
    if (
        type(outcome_invocation_id) is not str
        or len(outcome_invocation_id) != 32
        or OUTCOME_INVOCATION_ID_PATTERN.fullmatch(
            outcome_invocation_id
        ) is None
    ):
        raise OutcomeSnapshotIdentityError(
            "INVALID_OUTCOME_INVOCATION_ID"
        )
    return outcome_invocation_id


def build_outcome_snapshot_row(row):
    ai = row["ai_validation"]

    return {
        "symbol": row["symbol"],
        "reference_price": row["reference_price"],
        "reference_candle_at": row["reference_candle_at"],
        "python_score": row["python_score"],
        "validation_adjustment": row["validation_adjustment"],
        "final_rank_score": row["final_rank_score"],
        "trend": row["trend"],
        "bos": row["bos"],
        "choch": row["choch"],
        "volume_ratio": row["volume_ratio"],
        "volume_class": row["volume_class"],
        "oi_change_pct": row["oi_change_pct"],
        "oi_class": row["oi_class"],
        "participation": row["participation"],
        "ai_validation": {
            "status": ai["status"],
            "false_breakout_risk": ai["false_breakout_risk"],
            "confluence": ai["confluence"],
            "reason_code": ai["reason_code"],
        },
    }


def build_outcome_snapshot(final_top5, captured_at=None):
    if captured_at is None:
        captured_at = datetime.now().isoformat()

    return {
        "snapshot_type": SNAPSHOT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at,
        "candidates": [
            build_outcome_snapshot_row(row)
            for row in final_top5
        ],
    }


def _fsync_directory(directory):
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    directory_fd = os.open(directory, flags)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _read_existing_regular_artifact(path):
    try:
        path_stat = path.lstat()
    except OSError as exc:
        raise OutcomeSnapshotPersistenceError(
            "OUTCOME_ARTIFACT_PERSISTENCE_FAILED"
        ) from exc
    if (
        not stat.S_ISREG(path_stat.st_mode)
        or stat.S_ISLNK(path_stat.st_mode)
    ):
        raise OutcomeSnapshotConflictError(
            "OUTCOME_ARTIFACT_CONFLICT"
        )

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as existing_file:
            return existing_file.read()
    except OSError as exc:
        raise OutcomeSnapshotPersistenceError(
            "OUTCOME_ARTIFACT_PERSISTENCE_FAILED"
        ) from exc


def save_outcome_snapshot(
    final_top5,
    *,
    outcome_invocation_id,
    captured_at,
):
    validated_identity = validate_outcome_invocation_id(
        outcome_invocation_id
    )
    snapshot = build_outcome_snapshot(
        final_top5,
        captured_at=captured_at,
    )
    canonical_bytes = json.dumps(
        snapshot,
        indent=2,
    ).encode("utf-8")

    OUTCOME_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = OUTCOME_DIRECTORY / (
        f"outcome_entry_v4_{validated_identity}.json"
    )
    temp_path = None
    committed = False
    primary_failure = None

    try:
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=OUTCOME_DIRECTORY,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(temp_fd, "wb") as temp_file:
                temp_file.write(canonical_bytes)
                temp_file.flush()
                os.fsync(temp_file.fileno())
        except Exception as exc:
            try:
                os.close(temp_fd)
            except OSError:
                pass
            raise OutcomeSnapshotPersistenceError(
                "OUTCOME_ARTIFACT_TEMPORARY_WRITE_FAILED"
            ) from exc

        try:
            os.link(
                temp_path,
                path,
                follow_symlinks=False,
            )
        except FileExistsError:
            existing_bytes = _read_existing_regular_artifact(
                path
            )
            if existing_bytes != canonical_bytes:
                raise OutcomeSnapshotConflictError(
                    "OUTCOME_ARTIFACT_CONFLICT"
                )
            return path

        committed = True
        _fsync_directory(OUTCOME_DIRECTORY)
        return path
    except (
        OutcomeSnapshotConflictError,
        OutcomeSnapshotIdentityError,
        OutcomeSnapshotPersistenceError,
    ) as exc:
        primary_failure = exc
        raise
    except OSError as exc:
        primary_failure = OutcomeSnapshotPersistenceError(
            "OUTCOME_ARTIFACT_PERSISTENCE_FAILED"
        )
        raise primary_failure from exc
    except Exception as exc:
        primary_failure = OutcomeSnapshotPersistenceError(
            "OUTCOME_ARTIFACT_TEMPORARY_WRITE_FAILED"
        )
        raise primary_failure from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
                if committed:
                    _fsync_directory(OUTCOME_DIRECTORY)
            except OSError as cleanup_exc:
                if primary_failure is None:
                    raise OutcomeSnapshotPersistenceError(
                        "OUTCOME_ARTIFACT_TEMPORARY_CLEANUP_FAILED"
                    ) from cleanup_exc
