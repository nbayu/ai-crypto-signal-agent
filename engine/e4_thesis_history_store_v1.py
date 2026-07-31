"""Caller-authorized atomic durable storage for immutable E4 history."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from typing import Final

from engine.canonical_pair_v1 import normalize_pair
from engine.e4_thesis_history_v1 import (
    E4ThesisHistoryV1,
    reconstruct_e4_thesis_history_v1,
)


__all__ = (
    "E4_THESIS_HISTORY_STORE_VERSION",
    "E4ThesisHistoryStoreDocumentV1",
    "load_e4_thesis_history_store_v1",
    "compare_and_write_e4_thesis_history_store_v1",
)


E4_THESIS_HISTORY_STORE_VERSION: Final = "e4-thesis-history-store-v1"

_ERROR: Final = "invalid E4 thesis history store"
_STORE_SUFFIX: Final = ".e4-thesis-history.json"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_DOCUMENT_KEYS: Final = (
    "store_version",
    "canonical_pair",
    "store_revision",
    "history",
    "document_sha256",
)


def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _canonical_json(mapping: dict[str, object]) -> str:
    return json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash_mapping(mapping: dict[str, object]) -> str:
    return sha256(_canonical_json(mapping).encode("utf-8")).hexdigest()


def _history(value: object) -> E4ThesisHistoryV1:
    _require(type(value) is E4ThesisHistoryV1)
    value.__post_init__()
    return value


def _document_preimage(
    document: "E4ThesisHistoryStoreDocumentV1",
) -> dict[str, object]:
    return {
        "store_version": document.store_version,
        "canonical_pair": document.canonical_pair,
        "store_revision": document.store_revision,
        "history": document.history.to_mapping(),
    }


@dataclass(frozen=True, slots=True)
class E4ThesisHistoryStoreDocumentV1:
    store_version: str
    canonical_pair: str
    store_revision: int
    history: E4ThesisHistoryV1
    document_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.store_version) is str)
            _require(self.store_version == E4_THESIS_HISTORY_STORE_VERSION)
            retained_history = _history(self.history)
            _require(type(self.canonical_pair) is str)
            _require(bool(self.canonical_pair))
            _require(normalize_pair(self.canonical_pair) == self.canonical_pair)
            _require(type(self.store_revision) is int)
            _require(self.store_revision > 0)
            _require(self.store_revision == retained_history.revision)
            _require(
                self.canonical_pair
                == retained_history.events[-1].fingerprint.canonical_pair
            )
            _require(
                all(
                    event.fingerprint.canonical_pair == self.canonical_pair
                    for event in retained_history.events
                )
            )
            _require(type(self.document_sha256) is str)
            _require(
                _SHA256_PATTERN.fullmatch(self.document_sha256) is not None
            )
            _require(
                self.document_sha256
                == _hash_mapping(_document_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_document_preimage(self),
            "document_sha256": self.document_sha256,
        }

    def canonical_document_json(self) -> str:
        return _canonical_json(_document_preimage(self))


@dataclass(frozen=True, slots=True)
class _AuthorizedStorePaths:
    root: Path
    store: Path
    lock: Path
    temporary: Path


def _authorize_store_paths_v1(
    *,
    authorized_store_root: Path,
    store_path: Path,
) -> _AuthorizedStorePaths:
    try:
        _require(isinstance(authorized_store_root, Path))
        _require(isinstance(store_path, Path))
        _require(authorized_store_root.is_absolute())
        _require(store_path.is_absolute())
        _require(".." not in authorized_store_root.parts)
        _require(".." not in store_path.parts)
        _require(authorized_store_root.exists())
        _require(authorized_store_root.is_dir())
        _require(not authorized_store_root.is_symlink())
        root = authorized_store_root.resolve(strict=True)
        _require(store_path.name.endswith(_STORE_SUFFIX))
        _require(store_path.parent.resolve(strict=True) == root)
        store = store_path
        _require(not store.is_dir())
        if store.exists() or store.is_symlink():
            _require(not store.is_symlink())
        lock = Path(str(store) + ".lock")
        temporary = Path(str(store) + ".tmp")
        _require(lock.parent.resolve(strict=True) == root)
        _require(temporary.parent.resolve(strict=True) == root)
        if lock.exists() or lock.is_symlink():
            _require(not lock.is_symlink())
            _require(not lock.is_dir())
        if temporary.exists() or temporary.is_symlink():
            _require(not temporary.is_symlink())
            _require(not temporary.is_dir())
        return _AuthorizedStorePaths(
            root=root,
            store=store,
            lock=lock,
            temporary=temporary,
        )
    except Exception:
        _fail()


@contextmanager
def _locked_store_v1(
    paths: _AuthorizedStorePaths,
    *,
    exclusive: bool,
) -> Iterator[None]:
    descriptor = None
    lock_file = None
    try:
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(paths.lock, flags, 0o600)
        lock_file = os.fdopen(descriptor, "r+b", buffering=0)
        descriptor = None
        fcntl.flock(
            lock_file.fileno(),
            fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH,
        )
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


def _exact_document_mapping(value: object) -> dict[str, object]:
    _require(isinstance(value, Mapping))
    mapping = dict(value)
    _require(len(mapping) == len(_DOCUMENT_KEYS))
    _require(set(mapping) == set(_DOCUMENT_KEYS))
    return mapping


def _reconstruct_document_v1(value: object) -> E4ThesisHistoryStoreDocumentV1:
    mapping = _exact_document_mapping(value)
    mapping["history"] = reconstruct_e4_thesis_history_v1(mapping["history"])
    return E4ThesisHistoryStoreDocumentV1(**mapping)


def _document_from_bytes_v1(value: bytes) -> E4ThesisHistoryStoreDocumentV1:
    try:
        _require(type(value) is bytes)
        _require(len(value) > 0)
        text = value.decode("utf-8", errors="strict")
        _require(bool(text.strip()))
        parsed = json.loads(text)
        return _reconstruct_document_v1(parsed)
    except Exception:
        _fail()


def _read_regular_file_bytes_v1(path: Path) -> bytes:
    descriptor = None
    file_object = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        file_object = os.fdopen(descriptor, "rb")
        descriptor = None
        _require(stat.S_ISREG(os.fstat(file_object.fileno()).st_mode))
        return file_object.read()
    except Exception:
        _fail()
    finally:
        if file_object is not None:
            file_object.close()
        elif descriptor is not None:
            os.close(descriptor)


def _load_document_locked_v1(
    paths: _AuthorizedStorePaths,
) -> E4ThesisHistoryStoreDocumentV1 | None:
    if not paths.store.exists():
        _require(not paths.store.is_symlink())
        return None
    _require(not paths.store.is_symlink())
    _require(not paths.store.is_dir())
    return _document_from_bytes_v1(
        _read_regular_file_bytes_v1(paths.store)
    )


def _build_document_v1(
    history: E4ThesisHistoryV1,
) -> E4ThesisHistoryStoreDocumentV1:
    retained_history = _history(history)
    mapping: dict[str, object] = {
        "store_version": E4_THESIS_HISTORY_STORE_VERSION,
        "canonical_pair": (
            retained_history.events[-1].fingerprint.canonical_pair
        ),
        "store_revision": retained_history.revision,
        "history": retained_history,
    }
    preimage = {
        "store_version": E4_THESIS_HISTORY_STORE_VERSION,
        "canonical_pair": (
            retained_history.events[-1].fingerprint.canonical_pair
        ),
        "store_revision": retained_history.revision,
        "history": retained_history.to_mapping(),
    }
    return E4ThesisHistoryStoreDocumentV1(
        **mapping,
        document_sha256=_hash_mapping(preimage),
    )


def _write_document_locked_v1(
    paths: _AuthorizedStorePaths,
    document: E4ThesisHistoryStoreDocumentV1,
) -> E4ThesisHistoryStoreDocumentV1:
    document.__post_init__()
    _require(not paths.temporary.exists())
    _require(not paths.temporary.is_symlink())
    encoded = (
        _canonical_json(document.to_mapping()) + "\n"
    ).encode("utf-8")
    descriptor = None
    file_object = None
    created_temporary = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(paths.temporary, flags, 0o600)
        created_temporary = True
        file_object = os.fdopen(descriptor, "wb")
        descriptor = None
        written = file_object.write(encoded)
        _require(written == len(encoded))
        file_object.flush()
        os.fsync(file_object.fileno())
        file_object.close()
        file_object = None
        verified = _document_from_bytes_v1(
            _read_regular_file_bytes_v1(paths.temporary)
        )
        _require(verified == document)
        os.replace(paths.temporary, paths.store)
        created_temporary = False
        directory_descriptor = os.open(paths.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        committed = _load_document_locked_v1(paths)
        _require(committed is not None)
        _require(committed == document)
        return committed
    except Exception:
        if created_temporary and paths.temporary.exists() and not paths.temporary.is_symlink():
            paths.temporary.unlink()
        _fail()
    finally:
        if file_object is not None:
            file_object.close()
        elif descriptor is not None:
            os.close(descriptor)


def _write_history_locked_v1(
    paths: _AuthorizedStorePaths,
    history: E4ThesisHistoryV1,
) -> E4ThesisHistoryStoreDocumentV1:
    return _write_document_locked_v1(paths, _build_document_v1(history))


def _validate_history_extension_v1(
    current: E4ThesisHistoryStoreDocumentV1,
    candidate: E4ThesisHistoryV1,
) -> None:
    _require(candidate.revision > current.store_revision)
    _require(
        candidate.events[: current.store_revision]
        == current.history.events
    )
    _require(
        candidate.fingerprint_history[: len(current.history.fingerprint_history)]
        == current.history.fingerprint_history
    )
    _require(
        candidate.events[-1].fingerprint.canonical_pair
        == current.canonical_pair
    )


def load_e4_thesis_history_store_v1(
    *,
    authorized_store_root: Path,
    store_path: Path,
) -> E4ThesisHistoryStoreDocumentV1 | None:
    try:
        paths = _authorize_store_paths_v1(
            authorized_store_root=authorized_store_root,
            store_path=store_path,
        )
        with _locked_store_v1(paths, exclusive=False):
            return _load_document_locked_v1(paths)
    except Exception:
        _fail()


def compare_and_write_e4_thesis_history_store_v1(
    *,
    authorized_store_root: Path,
    store_path: Path,
    expected_store_revision: int | None,
    expected_document_sha256: str | None,
    history: E4ThesisHistoryV1,
) -> E4ThesisHistoryStoreDocumentV1:
    try:
        candidate = _history(history)
        absent_expectation = (
            expected_store_revision is None
            and expected_document_sha256 is None
        )
        existing_expectation = (
            type(expected_store_revision) is int
            and expected_store_revision > 0
            and type(expected_document_sha256) is str
            and _SHA256_PATTERN.fullmatch(expected_document_sha256)
            is not None
        )
        _require(absent_expectation is not existing_expectation)
        paths = _authorize_store_paths_v1(
            authorized_store_root=authorized_store_root,
            store_path=store_path,
        )
        with _locked_store_v1(paths, exclusive=True):
            current = _load_document_locked_v1(paths)
            if current is None:
                _require(absent_expectation)
                _require(candidate.revision == 1)
            else:
                _require(existing_expectation)
                _require(expected_store_revision == current.store_revision)
                _require(
                    expected_document_sha256 == current.document_sha256
                )
                _validate_history_extension_v1(current, candidate)
            return _write_history_locked_v1(paths, candidate)
    except Exception:
        _fail()
