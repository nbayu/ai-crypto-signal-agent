"""Bounded local repository remote-expectation policy reader."""
from __future__ import annotations

from dataclasses import dataclass
import errno
import json
import os
import re
import stat

__all__ = ("load_phase_12_repository_remote_expectation_source_v1",)

_CODES = ("PATH_TYPE_INVALID", "SOURCE_UNAVAILABLE", "SOURCE_SYMLINK_REJECTED", "SOURCE_OWNER_MISMATCH", "SOURCE_MODE_MISMATCH", "SOURCE_TYPE_INVALID", "SOURCE_LINK_COUNT_INVALID", "SOURCE_SIZE_INVALID", "SOURCE_ENCODING_INVALID", "SOURCE_SCHEMA_INVALID", "SOURCE_FETCH_URL_INVALID", "SOURCE_PUSH_URL_INVALID", "SOURCE_CHANGED_DURING_READ")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
_URL = re.compile(r"git@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?:[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*\.git\Z")


@dataclass(frozen=True, slots=True, kw_only=True)
class _Phase12RepositoryRemoteExpectationSourceResultV1:
    is_loaded: bool
    failure_codes: tuple[str, ...]
    expected_origin_fetch_url: str | None
    expected_origin_push_url: str | None

    def __repr__(self) -> str:
        return f"_Phase12RepositoryRemoteExpectationSourceResultV1(is_loaded={self.is_loaded!r}, failure_count={len(self.failure_codes)})"


class _Known(RuntimeError):
    pass


def _failure(code: str) -> _Phase12RepositoryRemoteExpectationSourceResultV1:
    return _Phase12RepositoryRemoteExpectationSourceResultV1(is_loaded=False, failure_codes=(code,), expected_origin_fetch_url=None, expected_origin_push_url=None)


def _path_ok(value: str) -> bool:
    return bool(value) and value.startswith("/") and not value.startswith("//") and value != "/" and "\0" not in value and not value.endswith("/") and all(x not in ("", ".", "..") for x in value.split("/")[1:])


def _snapshot(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_nlink, info.st_size


def _url_ok(value: str) -> bool:
    return value.isascii() and _URL.fullmatch(value) is not None


def _pairs(pairs: list[tuple[object, object]]) -> dict[str, object]:
    names = ("schema_version", "expected_origin_fetch_url", "expected_origin_push_url")
    if len(pairs) != 3 or tuple(k for k, _ in pairs) != names:
        raise ValueError
    return dict(pairs)


def load_phase_12_repository_remote_expectation_source_v1(*, source_path: str) -> _Phase12RepositoryRemoteExpectationSourceResultV1:
    if type(source_path) is not str:
        raise TypeError()
    if not _path_ok(source_path):
        return _failure("PATH_TYPE_INVALID")
    fds: list[int] = []
    selected: str | None = None
    propagated = False
    try:
        try:
            root = os.open("/", _DIR_FLAGS); fds.append(root); current = root
            pieces = source_path.split("/")[1:]
            for piece in pieces[:-1]:
                current = os.open(piece, _DIR_FLAGS, dir_fd=current); fds.append(current)
            fd = os.open(pieces[-1], _FILE_FLAGS, dir_fd=current); fds.append(fd)
        except OSError as exc:
            return _failure("SOURCE_SYMLINK_REJECTED" if exc.errno == errno.ELOOP else "SOURCE_UNAVAILABLE")
        try:
            before = os.fstat(fd)
        except OSError:
            return _failure("SOURCE_UNAVAILABLE")
        if not stat.S_ISREG(before.st_mode): return _failure("SOURCE_TYPE_INVALID")
        if before.st_uid != 0: return _failure("SOURCE_OWNER_MISMATCH")
        if stat.S_IMODE(before.st_mode) != 0o644: return _failure("SOURCE_MODE_MISMATCH")
        if before.st_nlink != 1: return _failure("SOURCE_LINK_COUNT_INVALID")
        if not 1 <= before.st_size <= 4096: return _failure("SOURCE_SIZE_INVALID")
        try:
            raw = os.read(fd, 4097)
        except InterruptedError:
            return _failure("SOURCE_CHANGED_DURING_READ")
        except OSError:
            return _failure("SOURCE_UNAVAILABLE")
        if len(raw) == 4097: return _failure("SOURCE_SIZE_INVALID")
        if len(raw) != before.st_size: return _failure("SOURCE_CHANGED_DURING_READ")
        try:
            if raw.startswith(b"\xef\xbb\xbf"): return _failure("SOURCE_ENCODING_INVALID")
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError:
            return _failure("SOURCE_ENCODING_INVALID")
        if not raw.endswith(b"\n") or raw.count(b"\n") != 1 or b"\r" in raw or text[:-1].strip() != text[:-1]: return _failure("SOURCE_SCHEMA_INVALID")
        try:
            value = json.loads(text, object_pairs_hook=_pairs)
            if type(value) is not dict: raise ValueError
            schema = value["schema_version"]; fetch = value["expected_origin_fetch_url"]; push = value["expected_origin_push_url"]
            if type(schema) is not int or schema != 1 or type(fetch) is not str or type(push) is not str: raise ValueError
            canonical = json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n"
            if canonical.encode("utf-8") != raw: raise ValueError
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return _failure("SOURCE_SCHEMA_INVALID")
        if not _url_ok(fetch): return _failure("SOURCE_FETCH_URL_INVALID")
        if not _url_ok(push): return _failure("SOURCE_PUSH_URL_INVALID")
        try:
            if _snapshot(os.fstat(fd)) != _snapshot(before): return _failure("SOURCE_CHANGED_DURING_READ")
        except OSError:
            return _failure("SOURCE_UNAVAILABLE")
        return _Phase12RepositoryRemoteExpectationSourceResultV1(is_loaded=True, failure_codes=(), expected_origin_fetch_url=fetch, expected_origin_push_url=push)
    except BaseException:
        propagated = True
        raise
    finally:
        while fds:
            try:
                os.close(fds.pop())
            except OSError:
                if selected is None and not propagated:
                    selected = "SOURCE_UNAVAILABLE"
