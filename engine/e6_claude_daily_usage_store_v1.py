"""Durable compare-and-set storage for one bounded Claude usage day."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from typing import Final, Protocol, runtime_checkable

from engine.e5_claude_review_router_v1 import (
    ACTIVE_PROVIDER_BINDING_SHA256,
    E5ClaudeDailyUsageV1,
    L2_DAILY_LOGICAL_REVIEW_CEILING,
    MAXIMUM_DAILY_COST_MICRO_USD,
    SHARED_DAILY_LOGICAL_REVIEW_CEILING,
    create_empty_e5_claude_daily_usage_v1,
    reconstruct_e5_claude_daily_usage_v1,
)


E6_CLAUDE_DAILY_USAGE_STORE_VERSION: Final = (
    "e6-claude-daily-usage-store-v1"
)
STORE_FORMAT: Final = "ONE_CANONICAL_JSON_FILE_PER_UTC_DAY"
STORE_RECORD_FIELD_COUNT: Final = 9

_ERROR: Final = "invalid E6 Claude daily usage store"
_STORE_SUFFIX: Final = ".e6-claude-daily-usage.json"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_UTC_DAY_PATTERN: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_UTC_TIMESTAMP_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_RECORD_KEYS: Final = frozenset(
    (
        "store_version",
        "utc_day",
        "provider_binding_sha256",
        "store_generation",
        "prior_usage_sha256",
        "usage",
        "usage_sha256",
        "committed_at",
        "record_sha256",
    )
)


def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _canonical_json(mapping: Mapping[str, object]) -> str:
    try:
        return json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except Exception:
        _fail()


def _hash_mapping(mapping: Mapping[str, object]) -> str:
    return sha256(_canonical_json(mapping).encode("utf-8")).hexdigest()


def _valid_sha256(value: object) -> bool:
    return type(value) is str and _SHA256_PATTERN.fullmatch(value) is not None


def _validate_utc_day(value: object) -> str:
    _require(type(value) is str)
    _require(_UTC_DAY_PATTERN.fullmatch(value) is not None)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except Exception:
        _fail()
    _require(parsed.strftime("%Y-%m-%d") == value)
    return value


def _validate_timestamp(value: object) -> str:
    _require(type(value) is str)
    _require(_UTC_TIMESTAMP_PATTERN.fullmatch(value) is not None)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        _fail()
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return value


def _validate_usage(value: object, *, utc_day: str) -> E5ClaudeDailyUsageV1:
    _require(type(value) is E5ClaudeDailyUsageV1)
    value.__post_init__()
    _require(value.utc_day == utc_day)
    return value


def _record_preimage(
    record: "E6ClaudeDailyUsageStoreRecordV1",
) -> dict[str, object]:
    return {
        "store_version": record.store_version,
        "utc_day": record.utc_day,
        "provider_binding_sha256": record.provider_binding_sha256,
        "store_generation": record.store_generation,
        "prior_usage_sha256": record.prior_usage_sha256,
        "usage": record.usage.to_mapping(),
        "usage_sha256": record.usage_sha256,
        "committed_at": record.committed_at,
    }


@dataclass(frozen=True, slots=True)
class E6ClaudeDailyUsageStoreRecordV1:
    store_version: str
    utc_day: str
    provider_binding_sha256: str
    store_generation: int
    prior_usage_sha256: str
    usage: E5ClaudeDailyUsageV1
    usage_sha256: str
    committed_at: str
    record_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                self.store_version == E6_CLAUDE_DAILY_USAGE_STORE_VERSION
            )
            day = _validate_utc_day(self.utc_day)
            _require(
                self.provider_binding_sha256
                == ACTIVE_PROVIDER_BINDING_SHA256
            )
            _require(
                type(self.store_generation) is int
                and self.store_generation > 0
            )
            _require(_valid_sha256(self.prior_usage_sha256))
            usage = _validate_usage(self.usage, utc_day=day)
            _require(self.usage_sha256 == usage.usage_sha256)
            committed_at = _validate_timestamp(self.committed_at)
            _require(committed_at[:10] == day)
            _require(_valid_sha256(self.record_sha256))
            _require(
                self.record_sha256 == _hash_mapping(_record_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {**_record_preimage(self), "record_sha256": self.record_sha256}

    def canonical_record_json(self) -> str:
        return _canonical_json(_record_preimage(self))


def reconstruct_e6_claude_daily_usage_store_record_v1(
    mapping: Mapping[str, object],
) -> E6ClaudeDailyUsageStoreRecordV1:
    try:
        _require(type(mapping) is dict)
        _require(frozenset(mapping) == _RECORD_KEYS)
        data = dict(mapping)
        data["usage"] = reconstruct_e5_claude_daily_usage_v1(mapping["usage"])
        return E6ClaudeDailyUsageStoreRecordV1(**data)
    except Exception:
        _fail()


@runtime_checkable
class E6ClaudeDailyUsageStorePortV1(Protocol):
    def load(
        self,
        *,
        utc_day: str,
        observed_at: str,
    ) -> E6ClaudeDailyUsageStoreRecordV1 | None: ...

    def compare_and_commit(
        self,
        *,
        utc_day: str,
        expected_store_generation: int,
        expected_record_sha256: str | None,
        expected_usage_sha256: str,
        proposed_usage_after: E5ClaudeDailyUsageV1,
        committed_at: str,
    ) -> E6ClaudeDailyUsageStoreRecordV1: ...


@dataclass(frozen=True, slots=True)
class _AuthorizedStorePaths:
    root: Path
    store: Path
    lock: Path
    temporary: Path


def _authorize_paths(
    *, authorized_store_root: Path, utc_day: str
) -> _AuthorizedStorePaths:
    try:
        day = _validate_utc_day(utc_day)
        _require(isinstance(authorized_store_root, Path))
        _require(authorized_store_root.is_absolute())
        _require(".." not in authorized_store_root.parts)
        _require(authorized_store_root.exists())
        _require(authorized_store_root.is_dir())
        _require(not authorized_store_root.is_symlink())
        root = authorized_store_root.resolve(strict=True)
        store = root / f"{day}{_STORE_SUFFIX}"
        lock = Path(str(store) + ".lock")
        temporary = Path(str(store) + ".tmp")
        for path in (store, lock, temporary):
            _require(path.parent == root)
            if path.exists() or path.is_symlink():
                _require(not path.is_symlink())
                _require(not path.is_dir())
        return _AuthorizedStorePaths(root, store, lock, temporary)
    except Exception:
        _fail()


@contextmanager
def _exclusive_lock(paths: _AuthorizedStorePaths) -> Iterator[None]:
    descriptor = None
    lock_file = None
    try:
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(paths.lock, flags, 0o600)
        lock_file = os.fdopen(descriptor, "r+b", buffering=0)
        descriptor = None
        _require(stat.S_ISREG(os.fstat(lock_file.fileno()).st_mode))
        os.fchmod(lock_file.fileno(), 0o600)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    except Exception:
        _fail()
    finally:
        if lock_file is not None:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()
        elif descriptor is not None:
            os.close(descriptor)


def _read_regular(path: Path) -> bytes:
    descriptor = None
    file_object = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        file_object = os.fdopen(descriptor, "rb")
        descriptor = None
        metadata = os.fstat(file_object.fileno())
        _require(stat.S_ISREG(metadata.st_mode))
        _require(stat.S_IMODE(metadata.st_mode) == 0o600)
        return file_object.read()
    except Exception:
        _fail()
    finally:
        if file_object is not None:
            file_object.close()
        elif descriptor is not None:
            os.close(descriptor)


def _record_from_bytes(value: bytes) -> E6ClaudeDailyUsageStoreRecordV1:
    try:
        _require(type(value) is bytes and bool(value))
        text = value.decode("utf-8", errors="strict")
        _require(text.endswith("\n"))
        _require(not text.endswith("\n\n"))
        parsed = json.loads(text)
        return reconstruct_e6_claude_daily_usage_store_record_v1(parsed)
    except Exception:
        _fail()


def _load_locked(
    paths: _AuthorizedStorePaths,
    *,
    utc_day: str,
    observed_at: str,
) -> E6ClaudeDailyUsageStoreRecordV1 | None:
    _require(not paths.temporary.exists())
    _require(not paths.temporary.is_symlink())
    if not paths.store.exists():
        _require(not paths.store.is_symlink())
        return None
    record = _record_from_bytes(_read_regular(paths.store))
    _require(record.utc_day == utc_day)
    _require(record.committed_at <= observed_at)
    return record


def _build_record(
    *,
    utc_day: str,
    store_generation: int,
    prior_usage_sha256: str,
    usage: E5ClaudeDailyUsageV1,
    committed_at: str,
) -> E6ClaudeDailyUsageStoreRecordV1:
    temporary = object.__new__(E6ClaudeDailyUsageStoreRecordV1)
    data: dict[str, object] = {
        "store_version": E6_CLAUDE_DAILY_USAGE_STORE_VERSION,
        "utc_day": utc_day,
        "provider_binding_sha256": ACTIVE_PROVIDER_BINDING_SHA256,
        "store_generation": store_generation,
        "prior_usage_sha256": prior_usage_sha256,
        "usage": usage,
        "usage_sha256": usage.usage_sha256,
        "committed_at": committed_at,
    }
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E6ClaudeDailyUsageStoreRecordV1(
        **data,
        record_sha256=_hash_mapping(_record_preimage(temporary)),
    )


def _validate_single_append(
    before: E5ClaudeDailyUsageV1,
    after: E5ClaudeDailyUsageV1,
) -> None:
    _require(before.utc_day == after.utc_day)
    l1_delta = len(after.l1_reviewed_payload_sha256s) - len(
        before.l1_reviewed_payload_sha256s
    )
    l2_delta = len(after.l2_reviewed_payload_sha256s) - len(
        before.l2_reviewed_payload_sha256s
    )
    _require((l1_delta, l2_delta) in ((1, 0), (0, 1)))
    _require(
        after.l1_reviewed_payload_sha256s[
            : len(before.l1_reviewed_payload_sha256s)
        ]
        == before.l1_reviewed_payload_sha256s
    )
    _require(
        after.l2_reviewed_payload_sha256s[
            : len(before.l2_reviewed_payload_sha256s)
        ]
        == before.l2_reviewed_payload_sha256s
    )
    appended = (
        after.l1_reviewed_payload_sha256s[-1]
        if l1_delta == 1
        else after.l2_reviewed_payload_sha256s[-1]
    )
    _require(
        appended
        not in (
            before.l1_reviewed_payload_sha256s
            + before.l2_reviewed_payload_sha256s
        )
    )
    _require(
        len(
            after.l1_reviewed_payload_sha256s
            + after.l2_reviewed_payload_sha256s
        )
        <= SHARED_DAILY_LOGICAL_REVIEW_CEILING
    )
    _require(
        len(after.l2_reviewed_payload_sha256s)
        <= L2_DAILY_LOGICAL_REVIEW_CEILING
    )
    _require(
        after.committed_maximum_cost_micro_usd
        <= MAXIMUM_DAILY_COST_MICRO_USD
    )


def _write_locked(
    paths: _AuthorizedStorePaths,
    record: E6ClaudeDailyUsageStoreRecordV1,
) -> E6ClaudeDailyUsageStoreRecordV1:
    _require(not paths.temporary.exists())
    _require(not paths.temporary.is_symlink())
    encoded = (_canonical_json(record.to_mapping()) + "\n").encode("utf-8")
    descriptor = None
    file_object = None
    created = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(paths.temporary, flags, 0o600)
        created = True
        file_object = os.fdopen(descriptor, "wb")
        descriptor = None
        _require(file_object.write(encoded) == len(encoded))
        file_object.flush()
        os.fsync(file_object.fileno())
        os.fchmod(file_object.fileno(), 0o600)
        file_object.close()
        file_object = None
        _require(_record_from_bytes(_read_regular(paths.temporary)) == record)
        os.replace(paths.temporary, paths.store)
        created = False
        directory_descriptor = os.open(
            paths.root, os.O_RDONLY | os.O_DIRECTORY
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        committed = _record_from_bytes(_read_regular(paths.store))
        _require(committed == record)
        return committed
    except Exception:
        if created and paths.temporary.exists() and not paths.temporary.is_symlink():
            paths.temporary.unlink()
        _fail()
    finally:
        if file_object is not None:
            file_object.close()
        elif descriptor is not None:
            os.close(descriptor)


def load_e6_claude_daily_usage_store_v1(
    *,
    authorized_store_root: Path,
    utc_day: str,
    observed_at: str,
) -> E6ClaudeDailyUsageStoreRecordV1 | None:
    try:
        day = _validate_utc_day(utc_day)
        observed = _validate_timestamp(observed_at)
        _require(observed[:10] == day)
        paths = _authorize_paths(
            authorized_store_root=authorized_store_root,
            utc_day=day,
        )
        with _exclusive_lock(paths):
            return _load_locked(paths, utc_day=day, observed_at=observed)
    except Exception:
        _fail()


def resolve_e6_claude_daily_usage_before_v1(
    *,
    record: E6ClaudeDailyUsageStoreRecordV1 | None,
    utc_day: str,
) -> E5ClaudeDailyUsageV1:
    try:
        day = _validate_utc_day(utc_day)
        if record is None:
            return create_empty_e5_claude_daily_usage_v1(utc_day=day)
        _require(type(record) is E6ClaudeDailyUsageStoreRecordV1)
        record.__post_init__()
        _require(record.utc_day == day)
        return record.usage
    except Exception:
        _fail()


def compare_and_commit_e6_claude_daily_usage_store_v1(
    *,
    authorized_store_root: Path,
    utc_day: str,
    expected_store_generation: int,
    expected_record_sha256: str | None,
    expected_usage_sha256: str,
    proposed_usage_after: E5ClaudeDailyUsageV1,
    committed_at: str,
) -> E6ClaudeDailyUsageStoreRecordV1:
    try:
        day = _validate_utc_day(utc_day)
        timestamp = _validate_timestamp(committed_at)
        _require(timestamp[:10] == day)
        _require(type(expected_store_generation) is int)
        _require(expected_store_generation >= 0)
        _require(
            expected_record_sha256 is None
            or _valid_sha256(expected_record_sha256)
        )
        _require(_valid_sha256(expected_usage_sha256))
        after = _validate_usage(proposed_usage_after, utc_day=day)
        paths = _authorize_paths(
            authorized_store_root=authorized_store_root,
            utc_day=day,
        )
        with _exclusive_lock(paths):
            current = _load_locked(
                paths, utc_day=day, observed_at=timestamp
            )
            if current is None:
                before = create_empty_e5_claude_daily_usage_v1(utc_day=day)
                _require(expected_store_generation == 0)
                _require(expected_record_sha256 is None)
                _require(expected_usage_sha256 == before.usage_sha256)
                generation = 1
            else:
                before = current.usage
                _require(
                    expected_store_generation == current.store_generation
                )
                _require(expected_record_sha256 == current.record_sha256)
                _require(expected_usage_sha256 == current.usage_sha256)
                generation = current.store_generation + 1
            _validate_single_append(before, after)
            record = _build_record(
                utc_day=day,
                store_generation=generation,
                prior_usage_sha256=before.usage_sha256,
                usage=after,
                committed_at=timestamp,
            )
            return _write_locked(paths, record)
    except Exception:
        _fail()


class E6ClaudeDailyUsageFileStoreV1:
    __slots__ = ("_authorized_store_root",)

    def __init__(self, *, authorized_store_root: Path) -> None:
        paths = _authorize_paths(
            authorized_store_root=authorized_store_root,
            utc_day="2000-01-01",
        )
        self._authorized_store_root = paths.root

    def load(
        self,
        *,
        utc_day: str,
        observed_at: str,
    ) -> E6ClaudeDailyUsageStoreRecordV1 | None:
        return load_e6_claude_daily_usage_store_v1(
            authorized_store_root=self._authorized_store_root,
            utc_day=utc_day,
            observed_at=observed_at,
        )

    def compare_and_commit(
        self,
        *,
        utc_day: str,
        expected_store_generation: int,
        expected_record_sha256: str | None,
        expected_usage_sha256: str,
        proposed_usage_after: E5ClaudeDailyUsageV1,
        committed_at: str,
    ) -> E6ClaudeDailyUsageStoreRecordV1:
        return compare_and_commit_e6_claude_daily_usage_store_v1(
            authorized_store_root=self._authorized_store_root,
            utc_day=utc_day,
            expected_store_generation=expected_store_generation,
            expected_record_sha256=expected_record_sha256,
            expected_usage_sha256=expected_usage_sha256,
            proposed_usage_after=proposed_usage_after,
            committed_at=committed_at,
        )


__all__ = (
    "E6_CLAUDE_DAILY_USAGE_STORE_VERSION",
    "STORE_FORMAT",
    "STORE_RECORD_FIELD_COUNT",
    "E6ClaudeDailyUsageStoreRecordV1",
    "E6ClaudeDailyUsageStorePortV1",
    "E6ClaudeDailyUsageFileStoreV1",
    "reconstruct_e6_claude_daily_usage_store_record_v1",
    "load_e6_claude_daily_usage_store_v1",
    "resolve_e6_claude_daily_usage_before_v1",
    "compare_and_commit_e6_claude_daily_usage_store_v1",
)
