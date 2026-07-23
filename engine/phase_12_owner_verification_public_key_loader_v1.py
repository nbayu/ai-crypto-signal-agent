"""Bounded owner verification public-key loading from one explicit path."""
from __future__ import annotations

import errno as _errno
import hashlib as _hashlib
import os as _os
import re as _re
import stat as _stat
from dataclasses import dataclass as _dataclass

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_public_key

__all__ = ("load_phase_12_owner_verification_public_key_v1",)

_MAXIMUM_SIZE = 4096
_KEY_PREFIX = "ed25519-sha256:"
_HEX = _re.compile(r"[0-9a-f]{64}\Z")
_KEY_IDENTIFIER = _re.compile(r"ed25519-sha256:[0-9a-f]{64}\Z")
_DIRECTORY_FLAGS = _os.O_RDONLY | _os.O_DIRECTORY | _os.O_CLOEXEC | _os.O_NOFOLLOW
_LEAF_FLAGS = _os.O_RDONLY | _os.O_CLOEXEC | _os.O_NOFOLLOW | _os.O_NONBLOCK
_METADATA_NAMES = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
_PATH_TYPE_INVALID = "PATH_TYPE_INVALID"
_TRUST_MATERIAL_UNAVAILABLE = "TRUST_MATERIAL_UNAVAILABLE"
_TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH = "TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH"
_TRUST_MATERIAL_NOT_REGULAR_FILE = "TRUST_MATERIAL_NOT_REGULAR_FILE"
_TRUST_MATERIAL_SYMLINK_REJECTED = "TRUST_MATERIAL_SYMLINK_REJECTED"
_TRUST_MATERIAL_OWNER_MISMATCH = "TRUST_MATERIAL_OWNER_MISMATCH"
_TRUST_MATERIAL_MODE_MISMATCH = "TRUST_MATERIAL_MODE_MISMATCH"
_TRUST_MATERIAL_HARD_LINK_REJECTED = "TRUST_MATERIAL_HARD_LINK_REJECTED"
_TRUST_MATERIAL_TOO_LARGE = "TRUST_MATERIAL_TOO_LARGE"
_TRUST_MATERIAL_EMPTY = "TRUST_MATERIAL_EMPTY"
_TRUST_MATERIAL_CHANGED_DURING_READ = "TRUST_MATERIAL_CHANGED_DURING_READ"
_MALFORMED_PUBLIC_KEY_CONTAINER = "MALFORMED_PUBLIC_KEY_CONTAINER"
_UNSUPPORTED_PUBLIC_KEY_TYPE = "UNSUPPORTED_PUBLIC_KEY_TYPE"
_MALFORMED_PUBLIC_KEY = "MALFORMED_PUBLIC_KEY"
_PUBLIC_KEY_FINGERPRINT_MISMATCH = "PUBLIC_KEY_FINGERPRINT_MISMATCH"
_PUBLIC_KEY_IDENTIFIER_MISMATCH = "PUBLIC_KEY_IDENTIFIER_MISMATCH"

@_dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12OwnerVerificationPublicKeyLoadResultV1:
    is_loaded: bool
    failure_codes: tuple[str, ...]
    raw_public_key_bytes: bytes | None
    derived_signing_key_identifier: str | None
    def __repr__(self) -> str:
        return "_Phase12OwnerVerificationPublicKeyLoadResultV1()"

def _failure(code: str) -> _Phase12OwnerVerificationPublicKeyLoadResultV1:
    return _Phase12OwnerVerificationPublicKeyLoadResultV1(is_loaded=False, failure_codes=(code,), raw_public_key_bytes=None, derived_signing_key_identifier=None)

def _valid_expected_facts(fingerprint: str, identifier: str) -> bool:
    return _HEX.fullmatch(fingerprint) is not None and _KEY_IDENTIFIER.fullmatch(identifier) is not None

def _path_parts(path: str) -> tuple[str, ...] | None:
    if not path or path == "/" or not path.startswith("/") or "\x00" in path or path.endswith("/"):
        return None
    parts = tuple(path.split("/")[1:])
    if not parts or any(part in ("", ".", "..") for part in parts):
        return None
    return parts

def _parent_open_code(error: OSError) -> str | None:
    if error.errno in (_errno.ELOOP, _errno.ENOTDIR):
        return _TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH
    if error.errno in (_errno.ENOENT, _errno.EACCES, _errno.EPERM):
        return _TRUST_MATERIAL_UNAVAILABLE
    return None

def _leaf_open_code(error: OSError) -> str | None:
    if error.errno == _errno.ELOOP:
        return _TRUST_MATERIAL_SYMLINK_REJECTED
    if error.errno in (_errno.ENOENT, _errno.EACCES, _errno.EPERM):
        return _TRUST_MATERIAL_UNAVAILABLE
    return None

def _directory_code(metadata: object) -> str | None:
    if not _stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o022:
        return _TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH
    return None

def _leaf_code(metadata: object) -> str | None:
    if not _stat.S_ISREG(metadata.st_mode): return _TRUST_MATERIAL_NOT_REGULAR_FILE
    if metadata.st_uid != 0: return _TRUST_MATERIAL_OWNER_MISMATCH
    if metadata.st_mode & 0o022: return _TRUST_MATERIAL_MODE_MISMATCH
    if metadata.st_nlink != 1: return _TRUST_MATERIAL_HARD_LINK_REJECTED
    if metadata.st_size > _MAXIMUM_SIZE: return _TRUST_MATERIAL_TOO_LARGE
    if metadata.st_size == 0: return _TRUST_MATERIAL_EMPTY
    return None

def _same_metadata(before: object, after: object) -> bool:
    return all(getattr(before, name) == getattr(after, name) for name in _METADATA_NAMES)

def _bounded_content(descriptor: int) -> bytes | None:
    content = bytearray()
    while len(content) <= _MAXIMUM_SIZE:
        block = _os.read(descriptor, _MAXIMUM_SIZE + 1 - len(content))
        if type(block) is not bytes or len(content) + len(block) > _MAXIMUM_SIZE: return None
        if not block: break
        content.extend(block)
    return bytes(content)

def _close_descriptors(descriptors: list[int]) -> None:
    while descriptors: _os.close(descriptors.pop())

def load_phase_12_owner_verification_public_key_v1(
    *, path: str, expected_public_key_fingerprint: str, expected_signing_key_identifier: str,
) -> _Phase12OwnerVerificationPublicKeyLoadResultV1:
    if (type(path) is not str or type(expected_public_key_fingerprint) is not str or type(expected_signing_key_identifier) is not str or not _valid_expected_facts(expected_public_key_fingerprint, expected_signing_key_identifier)):
        raise TypeError()
    parts = _path_parts(path)
    if parts is None: return _failure(_PATH_TYPE_INVALID)
    descriptors: list[int] = []
    try:
        try: directory_descriptor = _os.open("/", _DIRECTORY_FLAGS)
        except OSError as error:
            code = _parent_open_code(error)
            if code is not None: return _failure(code)
            raise
        descriptors.append(directory_descriptor)
        code = _directory_code(_os.fstat(directory_descriptor))
        if code is not None: return _failure(code)
        for part in parts[:-1]:
            try: next_descriptor = _os.open(part, _DIRECTORY_FLAGS, dir_fd=directory_descriptor)
            except OSError as error:
                code = _parent_open_code(error)
                if code is not None: return _failure(code)
                raise
            descriptors.append(next_descriptor)
            code = _directory_code(_os.fstat(next_descriptor))
            if code is not None: return _failure(code)
            directory_descriptor = next_descriptor
        try: leaf_descriptor = _os.open(parts[-1], _LEAF_FLAGS, dir_fd=directory_descriptor)
        except OSError as error:
            code = _leaf_open_code(error)
            if code is not None: return _failure(code)
            raise
        descriptors.append(leaf_descriptor)
        before = _os.fstat(leaf_descriptor)
        code = _leaf_code(before)
        if code is not None: return _failure(code)
        content = _bounded_content(leaf_descriptor)
        if content is None: return _failure(_TRUST_MATERIAL_TOO_LARGE)
        after = _os.fstat(leaf_descriptor)
        if not _same_metadata(before, after): return _failure(_TRUST_MATERIAL_CHANGED_DURING_READ)
        try: named = _os.stat(parts[-1], dir_fd=directory_descriptor, follow_symlinks=False)
        except OSError: return _failure(_TRUST_MATERIAL_CHANGED_DURING_READ)
        if named.st_dev != before.st_dev or named.st_ino != before.st_ino: return _failure(_TRUST_MATERIAL_CHANGED_DURING_READ)
        try: decoded = load_pem_public_key(content)
        except ValueError: return _failure(_MALFORMED_PUBLIC_KEY_CONTAINER)
        except UnsupportedAlgorithm: return _failure(_UNSUPPORTED_PUBLIC_KEY_TYPE)
        if not isinstance(decoded, Ed25519PublicKey): return _failure(_UNSUPPORTED_PUBLIC_KEY_TYPE)
        if decoded.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo) != content: return _failure(_MALFORMED_PUBLIC_KEY_CONTAINER)
        try: raw = decoded.public_bytes(Encoding.Raw, PublicFormat.Raw)
        except ValueError: return _failure(_MALFORMED_PUBLIC_KEY)
        if type(raw) is not bytes or len(raw) != 32: return _failure(_MALFORMED_PUBLIC_KEY)
        fingerprint = _hashlib.sha256(raw).hexdigest()
        if fingerprint != expected_public_key_fingerprint: return _failure(_PUBLIC_KEY_FINGERPRINT_MISMATCH)
        identifier = _KEY_PREFIX + fingerprint
        if identifier != expected_signing_key_identifier: return _failure(_PUBLIC_KEY_IDENTIFIER_MISMATCH)
        return _Phase12OwnerVerificationPublicKeyLoadResultV1(is_loaded=True, failure_codes=(), raw_public_key_bytes=raw, derived_signing_key_identifier=identifier)
    finally:
        _close_descriptors(descriptors)
