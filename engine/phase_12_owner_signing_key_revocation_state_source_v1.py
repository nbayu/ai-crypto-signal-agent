"""Bounded local owner signing-key revocation-state loading from one explicit path."""
from __future__ import annotations

import errno as _errno
import hashlib as _hashlib
import os as _os
import re as _re
import stat as _stat
from dataclasses import dataclass as _dataclass

__all__ = ("load_phase_12_owner_signing_key_revocation_state_v1",)

_MAXIMUM_SIZE = 65536
_READ_LIMIT = 65537
_SCHEMA = "PHASE12-OWNER-SIGNING-KEY-REVOCATION-STATE-V1"
_HEX = _re.compile(r"[0-9a-f]{64}\Z")
_CHECKPOINT = _re.compile(r"phase12-revocation-checkpoint-[0-9a-f]{16}\Z")
_IDENTIFIER = _re.compile(r"ed25519-sha256:[0-9a-f]{64}\Z")
_SCHEMA_TOKEN = _re.compile(r"PHASE12-OWNER-SIGNING-KEY-REVOCATION-STATE-V[0-9]+\Z")
_COUNT = _re.compile(r"(?:0|[1-9][0-9]*)\Z")
_DIRECTORY_FLAGS = _os.O_RDONLY | _os.O_DIRECTORY | _os.O_CLOEXEC | _os.O_NOFOLLOW
_LEAF_FLAGS = _os.O_RDONLY | _os.O_CLOEXEC | _os.O_NOFOLLOW | _os.O_NONBLOCK
_METADATA_NAMES = (
    "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size",
    "st_mtime_ns", "st_ctime_ns",
)

_PATH_TYPE_INVALID = "PATH_TYPE_INVALID"
_UNAVAILABLE = "REVOCATION_STATE_UNAVAILABLE"
_PARENT_MISMATCH = "REVOCATION_STATE_PARENT_DIRECTORY_MISMATCH"
_NOT_REGULAR = "REVOCATION_STATE_NOT_REGULAR_FILE"
_SYMLINK = "REVOCATION_STATE_SYMLINK_REJECTED"
_OWNER = "REVOCATION_STATE_OWNER_MISMATCH"
_MODE = "REVOCATION_STATE_MODE_MISMATCH"
_HARD_LINK = "REVOCATION_STATE_HARD_LINK_REJECTED"
_TOO_LARGE = "REVOCATION_STATE_TOO_LARGE"
_EMPTY = "REVOCATION_STATE_EMPTY"
_CHANGED = "REVOCATION_STATE_CHANGED_DURING_READ"
_MALFORMED = "MALFORMED_REVOCATION_STATE"
_FINGERPRINT = "REVOCATION_STATE_ARTIFACT_FINGERPRINT_MISMATCH"
_UNSUPPORTED_SCHEMA = "UNSUPPORTED_REVOCATION_STATE_SCHEMA"
_CHECKPOINT_MISMATCH = "REVOCATION_STATE_CHECKPOINT_MISMATCH"
_TOO_MANY = "REVOCATION_STATE_TOO_MANY_IDENTIFIERS"
_DUPLICATE = "REVOCATION_STATE_DUPLICATE_IDENTIFIER"
_UNSORTED = "REVOCATION_STATE_IDENTIFIERS_NOT_SORTED"
_ACTIVE_REVOKED = "ACTIVE_SIGNING_KEY_REVOKED"


@_dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12OwnerSigningKeyRevocationStateLoadResultV1:
    is_loaded: bool
    failure_codes: tuple[str, ...]
    schema_identifier: str | None
    checkpoint_identifier: str | None
    revoked_signing_key_identifiers: tuple[str, ...]
    artifact_fingerprint: str | None

    def __repr__(self) -> str:
        return "_Phase12OwnerSigningKeyRevocationStateLoadResultV1()"


def _failure(code: str) -> _Phase12OwnerSigningKeyRevocationStateLoadResultV1:
    return _Phase12OwnerSigningKeyRevocationStateLoadResultV1(
        is_loaded=False, failure_codes=(code,), schema_identifier=None,
        checkpoint_identifier=None, revoked_signing_key_identifiers=(),
        artifact_fingerprint=None,
    )


def _expected_is_valid(fingerprint: str, schema: str, checkpoint: str, active: str) -> bool:
    return (
        _HEX.fullmatch(fingerprint) is not None
        and schema == _SCHEMA
        and _CHECKPOINT.fullmatch(checkpoint) is not None
        and _IDENTIFIER.fullmatch(active) is not None
    )


def _parts(path: str) -> tuple[str, ...] | None:
    if not path or path == "/" or not path.startswith("/") or "\x00" in path or path.endswith("/"):
        return None
    parts = tuple(path.split("/")[1:])
    return None if not parts or any(part in ("", ".", "..") for part in parts) else parts


def _parent_open_code(error: OSError) -> str | None:
    if error.errno == _errno.ELOOP:
        return _SYMLINK
    if error.errno == _errno.ENOTDIR:
        return _PARENT_MISMATCH
    if error.errno in (_errno.ENOENT, _errno.EACCES):
        return _UNAVAILABLE
    return None


def _leaf_open_code(error: OSError) -> str | None:
    if error.errno == _errno.ELOOP:
        return _SYMLINK
    if error.errno in (_errno.ENOENT, _errno.EACCES):
        return _UNAVAILABLE
    return None


def _parent_code(metadata: object) -> str | None:
    if not _stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o022:
        return _PARENT_MISMATCH
    return None


def _leaf_code(metadata: object) -> str | None:
    if not _stat.S_ISREG(metadata.st_mode):
        return _NOT_REGULAR
    if metadata.st_uid != 0:
        return _OWNER
    if metadata.st_mode & 0o022:
        return _MODE
    if metadata.st_nlink != 1:
        return _HARD_LINK
    if metadata.st_size > _MAXIMUM_SIZE:
        return _TOO_LARGE
    if metadata.st_size == 0:
        return _EMPTY
    return None


def _same_metadata(before: object, after: object) -> bool:
    return all(getattr(before, name) == getattr(after, name) for name in _METADATA_NAMES)


def _read_bounded(descriptor: int) -> bytes | None:
    content = bytearray()
    while len(content) < _READ_LIMIT:
        block = _os.read(descriptor, _READ_LIMIT - len(content))
        content.extend(block)
        if not block:
            break
    return None if len(content) > _MAXIMUM_SIZE else bytes(content)


def _framed_text(content: bytes) -> str | None:
    if (
        content.startswith(b"\xef\xbb\xbf")
        or any(item > 0x7f for item in content)
        or b"\r" in content
        or not content.endswith(b"\n")
        or content.endswith(b"\n\n")
    ):
        return None
    try:
        text = content.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None
    lines = text[:-1].split("\n")
    if not lines or any(not line or " " in line or "\t" in line for line in lines):
        return None
    return text


def _field(line: str) -> tuple[str, str] | None:
    if line.count("=") != 1:
        return None
    key, value = line.split("=", 1)
    return None if not key or not value else (key, value)


def _close(descriptors: list[int]) -> None:
    while descriptors:
        _os.close(descriptors.pop())


def load_phase_12_owner_signing_key_revocation_state_v1(
    *,
    path: str,
    expected_artifact_fingerprint: str,
    expected_schema_identifier: str,
    expected_checkpoint_identifier: str,
    active_signing_key_identifier: str,
) -> _Phase12OwnerSigningKeyRevocationStateLoadResultV1:
    if (
        type(path) is not str
        or type(expected_artifact_fingerprint) is not str
        or type(expected_schema_identifier) is not str
        or type(expected_checkpoint_identifier) is not str
        or type(active_signing_key_identifier) is not str
        or not _expected_is_valid(
            expected_artifact_fingerprint, expected_schema_identifier,
            expected_checkpoint_identifier, active_signing_key_identifier,
        )
    ):
        raise TypeError()
    parts = _parts(path)
    if parts is None:
        return _failure(_PATH_TYPE_INVALID)
    descriptors: list[int] = []
    try:
        try:
            parent_descriptor = _os.open("/", _DIRECTORY_FLAGS)
        except OSError as error:
            code = _parent_open_code(error)
            if code is not None:
                return _failure(code)
            raise
        descriptors.append(parent_descriptor)
        code = _parent_code(_os.fstat(parent_descriptor))
        if code is not None:
            return _failure(code)
        for part in parts[:-1]:
            try:
                next_descriptor = _os.open(part, _DIRECTORY_FLAGS, dir_fd=parent_descriptor)
            except OSError as error:
                code = _parent_open_code(error)
                if code is not None:
                    return _failure(code)
                raise
            descriptors.append(next_descriptor)
            code = _parent_code(_os.fstat(next_descriptor))
            if code is not None:
                return _failure(code)
            parent_descriptor = next_descriptor
        try:
            leaf_descriptor = _os.open(parts[-1], _LEAF_FLAGS, dir_fd=parent_descriptor)
        except OSError as error:
            code = _leaf_open_code(error)
            if code is not None:
                return _failure(code)
            raise
        descriptors.append(leaf_descriptor)
        before = _os.fstat(leaf_descriptor)
        code = _leaf_code(before)
        if code is not None:
            return _failure(code)
        content = _read_bounded(leaf_descriptor)
        if content is None:
            return _failure(_TOO_LARGE)
        after = _os.fstat(leaf_descriptor)
        if not _same_metadata(before, after):
            return _failure(_CHANGED)
        try:
            named = _os.stat(parts[-1], dir_fd=parent_descriptor, follow_symlinks=False)
        except OSError:
            return _failure(_CHANGED)
        if (
            not _stat.S_ISREG(named.st_mode)
            or named.st_dev != before.st_dev
            or named.st_ino != before.st_ino
        ):
            return _failure(_CHANGED)
        text = _framed_text(content)
        if text is None:
            return _failure(_MALFORMED)
        fingerprint = _hashlib.sha256(content).hexdigest()
        if fingerprint != expected_artifact_fingerprint:
            return _failure(_FINGERPRINT)
        fields = [_field(line) for line in text[:-1].split("\n")]
        if any(field is None for field in fields) or len(fields) < 3:
            return _failure(_MALFORMED)
        schema_field, checkpoint_field, count_field = fields[:3]
        if (
            schema_field[0] != "schema_identifier"
            or checkpoint_field[0] != "checkpoint_identifier"
            or count_field[0] != "revoked_signing_key_count"
            or any(field[0] != "revoked_signing_key_identifier" for field in fields[3:])
        ):
            return _failure(_MALFORMED)
        schema_identifier = schema_field[1]
        if _SCHEMA_TOKEN.fullmatch(schema_identifier) is None:
            return _failure(_MALFORMED)
        if schema_identifier != expected_schema_identifier:
            return _failure(_UNSUPPORTED_SCHEMA)
        checkpoint_identifier = checkpoint_field[1]
        if _CHECKPOINT.fullmatch(checkpoint_identifier) is None:
            return _failure(_MALFORMED)
        if checkpoint_identifier != expected_checkpoint_identifier:
            return _failure(_CHECKPOINT_MISMATCH)
        count_text = count_field[1]
        if _COUNT.fullmatch(count_text) is None:
            return _failure(_MALFORMED)
        count = int(count_text)
        if count > 512:
            return _failure(_TOO_MANY)
        identifiers = tuple(field[1] for field in fields[3:])
        if len(identifiers) != count:
            return _failure(_MALFORMED)
        if any(_IDENTIFIER.fullmatch(identifier) is None for identifier in identifiers):
            return _failure(_MALFORMED)
        if len(set(identifiers)) != len(identifiers):
            return _failure(_DUPLICATE)
        if any(left >= right for left, right in zip(identifiers, identifiers[1:])):
            return _failure(_UNSORTED)
        if active_signing_key_identifier in identifiers:
            return _failure(_ACTIVE_REVOKED)
        return _Phase12OwnerSigningKeyRevocationStateLoadResultV1(
            is_loaded=True, failure_codes=(), schema_identifier=schema_identifier,
            checkpoint_identifier=checkpoint_identifier,
            revoked_signing_key_identifiers=identifiers, artifact_fingerprint=fingerprint,
        )
    finally:
        _close(descriptors)
