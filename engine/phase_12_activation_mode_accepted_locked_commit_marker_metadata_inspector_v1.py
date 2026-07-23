"""Acquire immutable metadata facts for one caller-supplied marker path."""

import errno as _errno
import os
from dataclasses import dataclass as _dataclass


__all__ = (
    "Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1",
    "Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1",
    "inspect_phase_12_activation_accepted_locked_commit_marker_metadata_v1",
)


_ENTRY_KINDS = ("regular_file", "symbolic_link", "directory", "other")
_ERROR_TEXTS = (
    "INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH",
    "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH_ABSENT",
    "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PERMISSION_DENIED",
    "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_SYMBOLIC_LINK_LOOP",
    "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH_COMPONENT_NOT_DIRECTORY",
    "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_FILESYSTEM_INSPECTION_FAILED",
    "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_MALFORMED_RESULT",
)
_INVALID_PATH = _ERROR_TEXTS[0]
_PATH_ABSENT = _ERROR_TEXTS[1]
_PERMISSION_DENIED = _ERROR_TEXTS[2]
_SYMBOLIC_LINK_LOOP = _ERROR_TEXTS[3]
_PATH_COMPONENT_NOT_DIRECTORY = _ERROR_TEXTS[4]
_FILESYSTEM_INSPECTION_FAILED = _ERROR_TEXTS[5]
_MALFORMED_RESULT = _ERROR_TEXTS[6]
_FILE_TYPE_MASK = 0o170000
_REGULAR_FILE = 0o100000
_SYMBOLIC_LINK = 0o120000
_DIRECTORY = 0o040000
_PERMISSION_MASK = 0o7777


class Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1(Exception):
    """Fixed, sanitized inspection failure."""

    __slots__ = ()

    def __init__(self, text: str) -> None:
        if type(text) is not str or text not in _ERROR_TEXTS:
            raise ValueError("INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_INSPECTION_ERROR")
        super().__init__(text)

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1()"


def _error(text: str) -> Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1:
    return Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1(text)


def _require_nonnegative_int(value: object) -> None:
    if type(value) is not int or value < 0:
        raise _error(_MALFORMED_RESULT)


def _require_permission_mode(value: object) -> None:
    if type(value) is not int or value < 0 or value > _PERMISSION_MASK:
        raise _error(_MALFORMED_RESULT)


@_dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1:
    """Immutable metadata facts without source, trust, or authorization semantics."""

    entry_kind: str
    link_count: int
    owner_uid: int
    group_gid: int
    permission_mode: int
    size_bytes: int

    def __post_init__(self) -> None:
        if type(self.entry_kind) is not str or self.entry_kind not in _ENTRY_KINDS:
            raise _error(_MALFORMED_RESULT)
        _require_nonnegative_int(self.link_count)
        _require_nonnegative_int(self.owner_uid)
        _require_nonnegative_int(self.group_gid)
        _require_permission_mode(self.permission_mode)
        _require_nonnegative_int(self.size_bytes)

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1()"


def _require_path(path: object) -> str:
    if type(path) is not str or not path or not path.startswith("/") or "\x00" in path:
        raise _error(_INVALID_PATH)
    return path


def _entry_kind(mode: int) -> str:
    file_type = mode & _FILE_TYPE_MASK
    if file_type == _REGULAR_FILE:
        return "regular_file"
    if file_type == _SYMBOLIC_LINK:
        return "symbolic_link"
    if file_type == _DIRECTORY:
        return "directory"
    return "other"


def _metadata_values(metadata: object) -> tuple[int, int, int, int, int]:
    try:
        mode = metadata.st_mode
        link_count = metadata.st_nlink
        owner_uid = metadata.st_uid
        group_gid = metadata.st_gid
        size_bytes = metadata.st_size
    except AttributeError:
        raise _error(_MALFORMED_RESULT) from None
    _require_nonnegative_int(mode)
    _require_nonnegative_int(link_count)
    _require_nonnegative_int(owner_uid)
    _require_nonnegative_int(group_gid)
    _require_nonnegative_int(size_bytes)
    return mode, link_count, owner_uid, group_gid, size_bytes


def _filesystem_error(error: OSError) -> Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1:
    if isinstance(error, FileNotFoundError) or error.errno == _errno.ENOENT:
        return _error(_PATH_ABSENT)
    if isinstance(error, PermissionError) or error.errno in (_errno.EACCES, _errno.EPERM):
        return _error(_PERMISSION_DENIED)
    if error.errno == _errno.ELOOP:
        return _error(_SYMBOLIC_LINK_LOOP)
    if error.errno == _errno.ENOTDIR:
        return _error(_PATH_COMPONENT_NOT_DIRECTORY)
    return _error(_FILESYSTEM_INSPECTION_FAILED)


def inspect_phase_12_activation_accepted_locked_commit_marker_metadata_v1(
    *, path: str
) -> Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1:
    """Inspect one caller-selected path once without following a final symlink."""
    selected_path = _require_path(path)
    try:
        metadata = os.lstat(selected_path)
    except OSError as error:
        raise _filesystem_error(error) from None
    mode, link_count, owner_uid, group_gid, size_bytes = _metadata_values(metadata)
    return Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1(
        entry_kind=_entry_kind(mode),
        link_count=link_count,
        owner_uid=owner_uid,
        group_gid=group_gid,
        permission_mode=mode & _PERMISSION_MASK,
        size_bytes=size_bytes,
    )
