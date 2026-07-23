"""Bounded raw-byte reader for one caller-supplied marker path."""

import errno as _errno
import os as _os
from dataclasses import dataclass as _dataclass


__all__ = (
    "Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1",
    "Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1",
    "read_phase_12_activation_accepted_locked_commit_marker_v1",
)


_MAXIMUM_SIZE = 4096
_READ_SIZE = _MAXIMUM_SIZE + 1
_OPEN_FLAGS = _os.O_RDONLY | _os.O_CLOEXEC | _os.O_NOFOLLOW | _os.O_NONBLOCK
_ERROR_TEXTS = (
    "INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH_ABSENT",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_PERMISSION_DENIED",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_SYMBOLIC_LINK_REJECTED",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH_COMPONENT_NOT_DIRECTORY",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_OPEN_FAILED",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_FAILED",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_CLOSE_FAILED",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_TOO_LARGE",
    "ACCEPTED_LOCKED_COMMIT_MARKER_READ_MALFORMED_RESULT",
)
_INVALID_PATH = _ERROR_TEXTS[0]
_PATH_ABSENT = _ERROR_TEXTS[1]
_PERMISSION_DENIED = _ERROR_TEXTS[2]
_SYMBOLIC_LINK_REJECTED = _ERROR_TEXTS[3]
_PATH_COMPONENT_NOT_DIRECTORY = _ERROR_TEXTS[4]
_OPEN_FAILED = _ERROR_TEXTS[5]
_READ_FAILED = _ERROR_TEXTS[6]
_CLOSE_FAILED = _ERROR_TEXTS[7]
_TOO_LARGE = _ERROR_TEXTS[8]
_MALFORMED_RESULT = _ERROR_TEXTS[9]


class Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1(Exception):
    """One fixed, sanitized marker-read failure."""

    __slots__ = ()

    def __init__(self, text: str) -> None:
        if type(text) is not str or text not in _ERROR_TEXTS:
            raise ValueError()
        super().__init__(text)

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1()"


def _error(text: str) -> Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1:
    return Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1(text)


@_dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1:
    """Immutable raw marker bytes without interpretation or trust semantics."""

    content_bytes: bytes

    def __post_init__(self) -> None:
        if type(self.content_bytes) is not bytes:
            raise TypeError()
        if len(self.content_bytes) > _MAXIMUM_SIZE:
            raise ValueError()

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1()"


def _require_path(path: object) -> str:
    if type(path) is not str or not path or not path.startswith("/") or "\x00" in path:
        raise _error(_INVALID_PATH)
    return path


def _open_error(error: OSError) -> Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1:
    if isinstance(error, FileNotFoundError) or error.errno == _errno.ENOENT:
        return _error(_PATH_ABSENT)
    if isinstance(error, PermissionError) or error.errno in (_errno.EACCES, _errno.EPERM):
        return _error(_PERMISSION_DENIED)
    if error.errno == _errno.ELOOP:
        return _error(_SYMBOLIC_LINK_REJECTED)
    if error.errno == _errno.ENOTDIR:
        return _error(_PATH_COMPONENT_NOT_DIRECTORY)
    return _error(_OPEN_FAILED)


def _validated_descriptor(value: object) -> int:
    if type(value) is not int or value < 0:
        raise _error(_MALFORMED_RESULT)
    return value


def _read_outcome(descriptor: int) -> bytes:
    try:
        content = _os.read(descriptor, _READ_SIZE)
    except OSError:
        raise _error(_READ_FAILED) from None
    if type(content) is not bytes:
        raise _error(_MALFORMED_RESULT)
    if len(content) > _MAXIMUM_SIZE:
        raise _error(_TOO_LARGE)
    return content


def read_phase_12_activation_accepted_locked_commit_marker_v1(
    *, path: str
) -> Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1:
    """Read at most 4096 raw bytes from one explicit caller-selected path."""
    selected_path = _require_path(path)
    try:
        opened_descriptor = _os.open(selected_path, _OPEN_FLAGS)
    except OSError as error:
        raise _open_error(error) from None
    descriptor = _validated_descriptor(opened_descriptor)
    primary: BaseException | None = None
    content: bytes | None = None
    try:
        try:
            content = _read_outcome(descriptor)
        except BaseException as error:
            primary = error
    finally:
        try:
            close_result = _os.close(descriptor)
            if close_result is not None and primary is None:
                primary = _error(_MALFORMED_RESULT)
        except OSError:
            if primary is None:
                primary = _error(_CLOSE_FAILED)
        except BaseException as error:
            if primary is None:
                primary = error
    if primary is not None:
        raise primary
    return Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1(content_bytes=content)
