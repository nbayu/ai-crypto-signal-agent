"""Local durable replay check-and-record guard for Phase 12 owner approvals.

Unknown ordinary exceptions and BaseException subclasses intentionally propagate.
"""

from __future__ import annotations

import errno
import os
import re
import sqlite3
import stat
from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import quote


__all__ = ("check_and_record_phase_12_owner_approval_replay_v1",)


_SCHEMA = "PHASE12-OWNER-APPROVAL-REPLAY-STORE-V1"
_IDENTITY = re.compile(r"[0-9a-f]{64}\Z")
_DEPLOYMENT = re.compile(r"phase12-replay-deployment-[0-9a-f]{16}\Z")
_MAX_ROWS = 1000000
_PAGE_SIZE = 4096
_MAX_PAGE_COUNT = 262144
_PARENT_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
_LEAF_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
_METADATA_TABLE = "phase_12_owner_approval_replay_metadata_v1"
_CONSUMED_TABLE = "phase_12_owner_approval_replay_consumed_v1"
_TRANSACTION_ORDER = "BEGIN IMMEDIATE; INSERT; COMMIT"
_SCHEMA_DDL = """
CREATE TABLE phase_12_owner_approval_replay_metadata_v1 (
    singleton INTEGER NOT NULL PRIMARY KEY,
    schema_identifier TEXT NOT NULL,
    deployment_identifier TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE phase_12_owner_approval_replay_consumed_v1 (
    replay_identity TEXT NOT NULL PRIMARY KEY
) WITHOUT ROWID;
"""
_STABLE_CODES = (
    "PATH_TYPE_INVALID",
    "REPLAY_STORE_UNAVAILABLE",
    "REPLAY_STORE_PARENT_DIRECTORY_MISMATCH",
    "REPLAY_STORE_SYMLINK_REJECTED",
    "REPLAY_STORE_OWNER_MISMATCH",
    "REPLAY_STORE_MODE_MISMATCH",
    "REPLAY_STORE_NOT_REGULAR_FILE",
    "REPLAY_STORE_HARD_LINK_REJECTED",
    "REPLAY_STORE_CHANGED_DURING_OPERATION",
    "REPLAY_STORE_OPEN_FAILED",
    "REPLAY_STORE_BUSY",
    "REPLAY_STORE_CONNECTION_POLICY_MISMATCH",
    "REPLAY_STORE_PAGE_POLICY_MISMATCH",
    "REPLAY_STORE_SCHEMA_MISMATCH",
    "REPLAY_STORE_DEPLOYMENT_MISMATCH",
    "REPLAY_STORE_UNSUPPORTED_OBJECT",
    "REPLAY_STORE_CORRUPT",
    "REPLAY_STORE_CAPACITY_EXCEEDED",
    "REPLAY_IDENTITY_ALREADY_CONSUMED",
    "REPLAY_RECORD_FAILED",
    "REPLAY_DURABILITY_NOT_CONFIRMED",
)


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12OwnerApprovalDurableReplayGuardResultV1:
    is_recorded: bool
    was_already_consumed: bool
    failure_codes: tuple[str, ...]
    replay_identity: str | None
    schema_identifier: str | None
    deployment_identifier: str | None

    def __repr__(self) -> str:
        return (
            "_Phase12OwnerApprovalDurableReplayGuardResultV1("
            f"is_recorded={self.is_recorded!r}, "
            f"was_already_consumed={self.was_already_consumed!r}, "
            f"failure_count={len(self.failure_codes)})"
        )


class _ExpectedFailure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


def _failure(code: str) -> _Phase12OwnerApprovalDurableReplayGuardResultV1:
    return _Phase12OwnerApprovalDurableReplayGuardResultV1(
        is_recorded=False,
        was_already_consumed=False,
        failure_codes=(code,),
        replay_identity=None,
        schema_identifier=None,
        deployment_identifier=None,
    )


def _success(identity: str, deployment: str) -> _Phase12OwnerApprovalDurableReplayGuardResultV1:
    return _Phase12OwnerApprovalDurableReplayGuardResultV1(
        is_recorded=True,
        was_already_consumed=False,
        failure_codes=(),
        replay_identity=identity,
        schema_identifier=_SCHEMA,
        deployment_identifier=deployment,
    )


def _already(identity: str, deployment: str) -> _Phase12OwnerApprovalDurableReplayGuardResultV1:
    return _Phase12OwnerApprovalDurableReplayGuardResultV1(
        is_recorded=False,
        was_already_consumed=True,
        failure_codes=("REPLAY_IDENTITY_ALREADY_CONSUMED",),
        replay_identity=identity,
        schema_identifier=_SCHEMA,
        deployment_identifier=deployment,
    )


def _validate_inputs(path: str, identity: str, schema: str, deployment: str) -> None:
    if type(path) is not str or type(identity) is not str or type(schema) is not str or type(deployment) is not str:
        raise TypeError()
    if _IDENTITY.fullmatch(identity) is None or schema != _SCHEMA or _DEPLOYMENT.fullmatch(deployment) is None:
        raise TypeError()


def _valid_path(path: str) -> bool:
    if not path or path == "/" or not path.startswith("/") or path.startswith("//") or "\x00" in path:
        return False
    if path.endswith("/") or os.path.normpath(path) != path:
        return False
    return all(component not in ("", ".", "..") for component in path.split("/")[1:])


def _map_open_error(error: OSError, *, parent: bool) -> str:
    if error.errno in (errno.ENOENT, errno.EACCES):
        return "REPLAY_STORE_UNAVAILABLE"
    if parent and error.errno == errno.ENOTDIR:
        return "REPLAY_STORE_PARENT_DIRECTORY_MISMATCH"
    if error.errno == errno.ELOOP:
        return "REPLAY_STORE_SYMLINK_REJECTED"
    raise error


def _security_tuple(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_nlink)


def _validate_root(info: os.stat_result) -> None:
    if not stat.S_ISDIR(info.st_mode):
        raise _ExpectedFailure("REPLAY_STORE_PARENT_DIRECTORY_MISMATCH")
    if info.st_uid != 0:
        raise _ExpectedFailure("REPLAY_STORE_OWNER_MISMATCH")
    if info.st_mode & 0o022:
        raise _ExpectedFailure("REPLAY_STORE_MODE_MISMATCH")


def _validate_parent(info: os.stat_result) -> None:
    if not stat.S_ISDIR(info.st_mode):
        raise _ExpectedFailure("REPLAY_STORE_PARENT_DIRECTORY_MISMATCH")
    if info.st_uid != 0:
        raise _ExpectedFailure("REPLAY_STORE_OWNER_MISMATCH")
    if (info.st_mode & 0o7777) != 0o700:
        raise _ExpectedFailure("REPLAY_STORE_MODE_MISMATCH")


def _validate_leaf(info: os.stat_result) -> None:
    if not stat.S_ISREG(info.st_mode):
        raise _ExpectedFailure("REPLAY_STORE_NOT_REGULAR_FILE")
    if info.st_uid != 0:
        raise _ExpectedFailure("REPLAY_STORE_OWNER_MISMATCH")
    if (info.st_mode & 0o7777) != 0o600:
        raise _ExpectedFailure("REPLAY_STORE_MODE_MISMATCH")
    if info.st_nlink != 1:
        raise _ExpectedFailure("REPLAY_STORE_HARD_LINK_REJECTED")


def _open_descriptors(path: str) -> tuple[list[int], int, tuple[tuple[int, int, int, int, int, int], ...], str]:
    components = path.split("/")[1:]
    descriptors: list[int] = []
    try:
        root = os.open("/", _PARENT_FLAGS)
    except OSError as error:
        raise _ExpectedFailure(_map_open_error(error, parent=True)) from error
    descriptors.append(root)
    _validate_root(os.fstat(root))
    identities = [_security_tuple(os.fstat(root))]
    current = root
    for component in components[:-1]:
        try:
            child = os.open(component, _PARENT_FLAGS, dir_fd=current)
        except OSError as error:
            raise _ExpectedFailure(_map_open_error(error, parent=True)) from error
        descriptors.append(child)
        _validate_parent(os.fstat(child))
        identities.append(_security_tuple(os.fstat(child)))
        current = child
    leaf_name = components[-1]
    try:
        leaf = os.open(leaf_name, _LEAF_FLAGS, dir_fd=current)
    except OSError as error:
        raise _ExpectedFailure(_map_open_error(error, parent=False)) from error
    _validate_leaf(os.fstat(leaf))
    return descriptors, leaf, tuple(identities), leaf_name


def _close_descriptors(descriptors: list[int], leaf: int | None) -> None:
    if leaf is not None:
        os.close(leaf)
    for descriptor in reversed(descriptors):
        os.close(descriptor)


def _recheck_path(path: str, expected_parents: tuple[tuple[int, int, int, int, int, int], ...], held_leaf: int) -> None:
    descriptors, leaf, identities, _ = _open_descriptors(path)
    try:
        if identities != expected_parents:
            raise _ExpectedFailure("REPLAY_STORE_CHANGED_DURING_OPERATION")
        held_info = os.fstat(held_leaf)
        current_info = os.fstat(leaf)
        if _security_tuple(held_info) != _security_tuple(current_info):
            raise _ExpectedFailure("REPLAY_STORE_CHANGED_DURING_OPERATION")
    finally:
        _close_descriptors(descriptors, leaf)


def _sqlite_code(error: sqlite3.Error) -> int | None:
    value = getattr(error, "sqlite_errorcode", None)
    return value if type(value) is int else None


def _sqlite_failure(error: sqlite3.Error, *, phase: str) -> str:
    code = _sqlite_code(error)
    busy = {getattr(sqlite3, "SQLITE_BUSY", -1), getattr(sqlite3, "SQLITE_LOCKED", -2)}
    if code in busy:
        return "REPLAY_STORE_BUSY"
    if code == getattr(sqlite3, "SQLITE_CANTOPEN", -1):
        return "REPLAY_STORE_OPEN_FAILED"
    if code in {getattr(sqlite3, "SQLITE_CORRUPT", -1), getattr(sqlite3, "SQLITE_NOTADB", -2)}:
        return "REPLAY_STORE_CORRUPT"
    conflicts = {getattr(sqlite3, "SQLITE_CONSTRAINT_PRIMARYKEY", -1), getattr(sqlite3, "SQLITE_CONSTRAINT_UNIQUE", -2)}
    if phase == "insert" and code in conflicts:
        return "REPLAY_IDENTITY_ALREADY_CONSUMED"
    if phase == "commit":
        # A COMMIT exception is ambiguous: the replay identity may have persisted.
        return "REPLAY_DURABILITY_NOT_CONFIRMED"
    return "REPLAY_RECORD_FAILED"


def _configure(connection: sqlite3.Connection) -> None:
    try:
        connection.enable_load_extension(False)
        foreign = connection.execute("PRAGMA foreign_keys=ON").fetchone()
        journal = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
        connection.execute("PRAGMA synchronous=FULL")
        synchronous = connection.execute("PRAGMA synchronous").fetchone()
        connection.execute("PRAGMA temp_store=MEMORY")
        temporary = connection.execute("PRAGMA temp_store").fetchone()
        if sqlite3.sqlite_version_info < (3, 31, 0):
            raise _ExpectedFailure("REPLAY_STORE_CONNECTION_POLICY_MISMATCH")
        connection.execute("PRAGMA trusted_schema=OFF")
        trusted = connection.execute("PRAGMA trusted_schema").fetchone()
        connection.execute("PRAGMA busy_timeout=5000")
        busy = connection.execute("PRAGMA busy_timeout").fetchone()
        page_size = connection.execute("PRAGMA page_size").fetchone()
        maximum = connection.execute("PRAGMA max_page_count").fetchone()
    except _ExpectedFailure:
        raise
    except (AttributeError, sqlite3.Error) as error:
        raise _ExpectedFailure("REPLAY_STORE_CONNECTION_POLICY_MISMATCH") from error
    if (
        foreign != (1,) or journal is None or str(journal[0]).lower() != "delete"
        or synchronous != (2,) or temporary != (2,) or trusted != (0,) or busy != (5000,)
    ):
        raise _ExpectedFailure("REPLAY_STORE_CONNECTION_POLICY_MISMATCH")
    if page_size != (_PAGE_SIZE,) or maximum != (_MAX_PAGE_COUNT,):
        raise _ExpectedFailure("REPLAY_STORE_PAGE_POLICY_MISMATCH")


def _bounded_rows(cursor: sqlite3.Cursor, count: int) -> list[tuple[object, ...]]:
    return cursor.fetchmany(count)


def _validate_schema_objects(connection: sqlite3.Connection) -> None:
    rows = _bounded_rows(connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ), 3)
    if len(rows) != 2 or {row[1] for row in rows} != {_METADATA_TABLE, _CONSUMED_TABLE} or any(row[0] != "table" for row in rows):
        raise _ExpectedFailure("REPLAY_STORE_UNSUPPORTED_OBJECT")
    for table, columns in ((_METADATA_TABLE, ("singleton", "schema_identifier", "deployment_identifier")), (_CONSUMED_TABLE, ("replay_identity",))):
        info = _bounded_rows(connection.execute(f"PRAGMA table_info({table})"), 4)
        if tuple(row[1] for row in info) != columns:
            raise _ExpectedFailure("REPLAY_STORE_SCHEMA_MISMATCH")
        indexes = _bounded_rows(connection.execute(f"PRAGMA index_list({table})"), 3)
        if len(indexes) != 1 or indexes[0][2] != 1 or indexes[0][3] != "pk" or indexes[0][4] != 0:
            raise _ExpectedFailure("REPLAY_STORE_SCHEMA_MISMATCH")
        index_name = indexes[0][1]
        indexed = _bounded_rows(connection.execute(f"PRAGMA index_info({index_name})"), 2)
        if len(indexed) != 1 or indexed[0][2] != columns[0]:
            raise _ExpectedFailure("REPLAY_STORE_SCHEMA_MISMATCH")
        if _bounded_rows(connection.execute(f"PRAGMA foreign_key_list({table})"), 1):
            raise _ExpectedFailure("REPLAY_STORE_UNSUPPORTED_OBJECT")


def _metadata(connection: sqlite3.Connection, deployment: str) -> None:
    rows = _bounded_rows(connection.execute(
        f"SELECT singleton, schema_identifier, deployment_identifier FROM {_METADATA_TABLE} ORDER BY singleton"
    ), 2)
    if len(rows) != 1 or rows[0][0] != 1:
        raise _ExpectedFailure("REPLAY_STORE_SCHEMA_MISMATCH")
    if rows[0][1] != _SCHEMA:
        raise _ExpectedFailure("REPLAY_STORE_SCHEMA_MISMATCH")
    if rows[0][2] != deployment:
        raise _ExpectedFailure("REPLAY_STORE_DEPLOYMENT_MISMATCH")


def _quick_check(connection: sqlite3.Connection) -> None:
    rows = _bounded_rows(connection.execute("PRAGMA quick_check(1)"), 2)
    if rows != [("ok",)]:
        raise _ExpectedFailure("REPLAY_STORE_CORRUPT")


def check_and_record_phase_12_owner_approval_replay_v1(
    *,
    path: str,
    replay_identity: str,
    expected_schema_identifier: str,
    expected_deployment_identifier: str,
) -> _Phase12OwnerApprovalDurableReplayGuardResultV1:
    _validate_inputs(path, replay_identity, expected_schema_identifier, expected_deployment_identifier)
    if not _valid_path(path):
        return _failure("PATH_TYPE_INVALID")
    descriptors: list[int] = []
    leaf: int | None = None
    connection: sqlite3.Connection | None = None
    committed = False
    result: _Phase12OwnerApprovalDurableReplayGuardResultV1 | None = None
    try:
        descriptors, leaf, parent_identities, _ = _open_descriptors(path)
        _recheck_path(path, parent_identities, leaf)
        try:
            connection = sqlite3.connect(
                f"file:{quote(path, safe='/')}?mode=rw",
                uri=True,
                timeout=5.0,
                isolation_level=None,
                detect_types=0,
                check_same_thread=True,
                factory=sqlite3.Connection,
                cached_statements=0,
            )
        except sqlite3.Error as error:
            return _failure(_sqlite_failure(error, phase="open"))
        _configure(connection)
        try:
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as error:
            return _failure(_sqlite_failure(error, phase="begin"))
        _recheck_path(path, parent_identities, leaf)
        _validate_schema_objects(connection)
        _metadata(connection, expected_deployment_identifier)
        _quick_check(connection)
        existing = connection.execute(
            f"SELECT replay_identity FROM {_CONSUMED_TABLE} WHERE replay_identity = ?", (replay_identity,)
        ).fetchone()
        if existing is not None:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                return _failure("REPLAY_RECORD_FAILED")
            result = _already(replay_identity, expected_deployment_identifier)
        else:
            count = connection.execute(f"SELECT COUNT(*) FROM {_CONSUMED_TABLE}").fetchone()
            pages = connection.execute("PRAGMA page_count").fetchone()
            if count != (None,) and (count is None or type(count[0]) is not int or count[0] >= _MAX_ROWS):
                return _failure("REPLAY_STORE_CAPACITY_EXCEEDED")
            if pages is None or type(pages[0]) is not int or pages[0] >= _MAX_PAGE_COUNT:
                return _failure("REPLAY_STORE_CAPACITY_EXCEEDED")
            try:
                connection.execute(f"INSERT INTO {_CONSUMED_TABLE} (replay_identity) VALUES (?)", (replay_identity,))
            except sqlite3.IntegrityError as error:
                if _sqlite_failure(error, phase="insert") == "REPLAY_IDENTITY_ALREADY_CONSUMED":
                    connection.execute("ROLLBACK")
                    result = _already(replay_identity, expected_deployment_identifier)
                else:
                    return _failure("REPLAY_RECORD_FAILED")
            if result is None:
                try:
                    connection.execute("COMMIT")
                except sqlite3.Error:
                    return _failure("REPLAY_DURABILITY_NOT_CONFIRMED")
                committed = True
                try:
                    _recheck_path(path, parent_identities, leaf)
                except _ExpectedFailure:
                    return _failure("REPLAY_STORE_CHANGED_DURING_OPERATION")
                result = _success(replay_identity, expected_deployment_identifier)
        return result
    except _ExpectedFailure as failure:
        return _failure(failure.code)
    except sqlite3.Error as error:
        return _failure(_sqlite_failure(error, phase="operation"))
    finally:
        close_failed = False
        if connection is not None:
            try:
                connection.close()
            except sqlite3.Error:
                close_failed = True
        _close_descriptors(descriptors, leaf)
        if close_failed and committed:
            # Return cannot be changed here; the next guard call resolves the ambiguous state.
            pass
