"""RED contract for the unwired Phase 12 owner signing-key revocation-state source."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
import errno
import hashlib
import inspect
import os

import pytest

import engine.phase_12_owner_signing_key_revocation_state_source_v1 as source_module


SCHEMA = "PHASE12-OWNER-SIGNING-KEY-REVOCATION-STATE-V1"
CHECKPOINT = "phase12-revocation-checkpoint-0123456789abcdef"
KEY_A = "ed25519-sha256:" + "1" * 64
KEY_B = "ed25519-sha256:" + "2" * 64
KEY_C = "ed25519-sha256:" + "3" * 64


@dataclass(frozen=True, slots=True)
class _FixtureMetadata:
    st_dev: int
    st_ino: int
    st_mode: int
    st_uid: int
    st_gid: int
    st_nlink: int
    st_size: int
    st_mtime_ns: int
    st_ctime_ns: int


def _artifact(*ids: str, schema: str = SCHEMA, checkpoint: str = CHECKPOINT, count: str | None = None) -> bytes:
    lines = [f"schema_identifier={schema}", f"checkpoint_identifier={checkpoint}", f"revoked_signing_key_count={len(ids) if count is None else count}"]
    lines.extend(f"revoked_signing_key_identifier={item}" for item in ids)
    return ("\n".join(lines) + "\n").encode("ascii")


def _write(tmp_path, content: bytes | None = None) -> tuple[str, bytes, str]:
    value = _artifact() if content is None else content
    path = tmp_path / "revocation-state.v1"
    path.write_bytes(value)
    return str(path), value, hashlib.sha256(value).hexdigest()


def _load(path: str, fingerprint: str, *, schema: str = SCHEMA, checkpoint: str = CHECKPOINT, active: str = KEY_A):
    return source_module.load_phase_12_owner_signing_key_revocation_state_v1(path=path, expected_artifact_fingerprint=fingerprint, expected_schema_identifier=schema, expected_checkpoint_identifier=checkpoint, active_signing_key_identifier=active)


def _failure(value, code: str) -> None:
    assert value.is_loaded is False and value.failure_codes == (code,)
    assert value.schema_identifier is None and value.checkpoint_identifier is None
    assert value.revoked_signing_key_identifiers == () and value.artifact_fingerprint is None


def _secure(monkeypatch, *, preserve_nlink_for=None) -> None:
    real_fstat, real_stat = os.fstat, os.stat
    def secure(item, descriptor=None):
        fields = list(item); fields[0] &= ~0o022
        if preserve_nlink_for is None or not preserve_nlink_for(descriptor):
            fields[3] = 1
        fields[4] = 0
        return os.stat_result(fields)
    monkeypatch.setattr(os, "fstat", lambda fd: secure(real_fstat(fd), fd))
    monkeypatch.setattr(os, "stat", lambda *args, **kwargs: secure(real_stat(*args, **kwargs)))


# 5 public surface/signature/type tests.
def test_public_all_is_exact():
    assert source_module.__all__ == ("load_phase_12_owner_signing_key_revocation_state_v1",)


def test_function_name_is_exact():
    assert source_module.load_phase_12_owner_signing_key_revocation_state_v1.__name__ == "load_phase_12_owner_signing_key_revocation_state_v1"


def test_signature_is_exact_and_keyword_only():
    signature = inspect.signature(source_module.load_phase_12_owner_signing_key_revocation_state_v1)
    assert tuple(signature.parameters) == ("path", "expected_artifact_fingerprint", "expected_schema_identifier", "expected_checkpoint_identifier", "active_signing_key_identifier")
    assert all(item.kind is inspect.Parameter.KEYWORD_ONLY for item in signature.parameters.values())


def test_public_surface_exports_no_private_result_type():
    assert not {name for name in source_module.__all__ if "Result" in name or "Failure" in name}


def test_wrong_runtime_type_raises_empty_type_error():
    with pytest.raises(TypeError) as caught: _load(1, "0" * 64)
    assert caught.value.args == ()


# 10 caller grammar/path tests.
def test_relative_path_is_rejected(): _failure(_load("relative", "0" * 64), "PATH_TYPE_INVALID")
def test_root_path_is_rejected(): _failure(_load("/", "0" * 64), "PATH_TYPE_INVALID")
def test_dot_component_is_rejected(): _failure(_load("/tmp/./state", "0" * 64), "PATH_TYPE_INVALID")
def test_dotdot_component_is_rejected(): _failure(_load("/tmp/a/../state", "0" * 64), "PATH_TYPE_INVALID")
def test_trailing_slash_is_rejected(): _failure(_load("/tmp/state/", "0" * 64), "PATH_TYPE_INVALID")
def test_nul_path_is_rejected(): _failure(_load("/tmp/state\x00", "0" * 64), "PATH_TYPE_INVALID")


def test_bad_fingerprint_raises_empty_type_error():
    with pytest.raises(TypeError) as caught: _load("/tmp/state", "A" * 64)
    assert caught.value.args == ()


def test_bad_schema_expectation_raises_empty_type_error():
    with pytest.raises(TypeError) as caught: _load("/tmp/state", "0" * 64, schema="phase12")
    assert caught.value.args == ()


def test_bad_checkpoint_expectation_raises_empty_type_error():
    with pytest.raises(TypeError) as caught: _load("/tmp/state", "0" * 64, checkpoint="PHASE12")
    assert caught.value.args == ()


def test_bad_active_key_expectation_raises_empty_type_error():
    with pytest.raises(TypeError) as caught: _load("/tmp/state", "0" * 64, active="ed25519-sha256:ABC")
    assert caught.value.args == ()


# 14 parent/leaf metadata and filesystem error tests.
def test_final_symlink_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); link = tmp_path / "link"; link.symlink_to(path); _secure(monkeypatch); _failure(_load(str(link), fingerprint), "REVOCATION_STATE_SYMLINK_REJECTED")


def test_parent_symlink_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path)
    link = tmp_path.parent / "revocation-link"
    link.symlink_to(tmp_path, target_is_directory=True)
    _secure(monkeypatch)
    original_open = os.open
    def parent_loop(name, flags, mode=0o777, *, dir_fd=None):
        if name == "revocation-link" and flags & os.O_DIRECTORY:
            raise OSError(errno.ELOOP, "parent symlink")
        if dir_fd is None:
            return original_open(name, flags, mode)
        return original_open(name, flags, mode, dir_fd=dir_fd)
    monkeypatch.setattr(os, "open", parent_loop)
    _failure(_load(str(link / os.path.basename(path)), fingerprint), "REVOCATION_STATE_SYMLINK_REJECTED")


def test_non_directory_parent_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); parent = tmp_path / "not-directory"; parent.write_bytes(b"x"); _secure(monkeypatch); _failure(_load(str(parent / os.path.basename(path)), fingerprint), "REVOCATION_STATE_PARENT_DIRECTORY_MISMATCH")


def test_parent_uid_mismatch_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); original = os.fstat
    def changed(fd): fields = list(original(fd)); fields[4] = 1; return os.stat_result(fields)
    monkeypatch.setattr(os, "fstat", changed); _failure(_load(path, fingerprint), "REVOCATION_STATE_PARENT_DIRECTORY_MISMATCH")


def test_parent_mode_mismatch_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); original = os.fstat
    def changed(fd): fields = list(original(fd)); fields[0] |= 0o022; return os.stat_result(fields)
    monkeypatch.setattr(os, "fstat", changed); _failure(_load(path, fingerprint), "REVOCATION_STATE_PARENT_DIRECTORY_MISMATCH")


def test_leaf_must_be_regular(tmp_path, monkeypatch):
    directory = tmp_path / "directory"; directory.mkdir(); _, _, fingerprint = _write(tmp_path); _secure(monkeypatch); _failure(_load(str(directory), fingerprint), "REVOCATION_STATE_NOT_REGULAR_FILE")


def test_leaf_uid_mismatch_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path)
    leaf_fd = None
    original_open = os.open
    def record_leaf(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal leaf_fd
        if dir_fd is None:
            opened = original_open(name, flags, mode)
        else:
            opened = original_open(name, flags, mode, dir_fd=dir_fd)
        if not flags & os.O_DIRECTORY:
            leaf_fd = opened
        return opened
    monkeypatch.setattr(os, "open", record_leaf)
    _secure(monkeypatch)
    original_fstat = os.fstat
    def changed(fd):
        fields = list(original_fstat(fd))
        if fd == leaf_fd:
            fields[4] = 1
        return os.stat_result(fields)
    monkeypatch.setattr(os, "fstat", changed); _failure(_load(path, fingerprint), "REVOCATION_STATE_OWNER_MISMATCH")


def test_leaf_mode_mismatch_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path)
    leaf_fd = None
    original_open = os.open
    def record_leaf(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal leaf_fd
        if dir_fd is None:
            opened = original_open(name, flags, mode)
        else:
            opened = original_open(name, flags, mode, dir_fd=dir_fd)
        if not flags & os.O_DIRECTORY:
            leaf_fd = opened
        return opened
    monkeypatch.setattr(os, "open", record_leaf)
    _secure(monkeypatch)
    original_fstat = os.fstat
    def changed(fd):
        fields = list(original_fstat(fd))
        if fd == leaf_fd:
            fields[0] |= 0o022
        return os.stat_result(fields)
    monkeypatch.setattr(os, "fstat", changed); _failure(_load(path, fingerprint), "REVOCATION_STATE_MODE_MISMATCH")


def test_leaf_hard_link_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path)
    os.link(path, tmp_path / "other")
    leaf_fd = None
    original_open = os.open
    def record_leaf(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal leaf_fd
        if dir_fd is None:
            opened = original_open(name, flags, mode)
        else:
            opened = original_open(name, flags, mode, dir_fd=dir_fd)
        if not flags & os.O_DIRECTORY:
            leaf_fd = opened
        return opened
    monkeypatch.setattr(os, "open", record_leaf)
    _secure(monkeypatch, preserve_nlink_for=lambda fd: fd == leaf_fd)
    _failure(_load(path, fingerprint), "REVOCATION_STATE_HARD_LINK_REJECTED")


def test_initial_oversize_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, b"x" * 65537); _secure(monkeypatch); _failure(_load(path, fingerprint), "REVOCATION_STATE_TOO_LARGE")


def test_empty_leaf_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, b""); _secure(monkeypatch); _failure(_load(path, fingerprint), "REVOCATION_STATE_EMPTY")


def test_missing_leaf_is_unavailable(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); os.unlink(path); _secure(monkeypatch); _failure(_load(path, fingerprint), "REVOCATION_STATE_UNAVAILABLE")


def test_parent_enotdir_is_mapped(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); parent = tmp_path / "plain"; parent.write_bytes(b"x"); _failure(_load(str(parent / os.path.basename(path)), fingerprint), "REVOCATION_STATE_PARENT_DIRECTORY_MISMATCH")


def test_initial_leaf_eloop_is_symlink_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); original = os.open
    def loop(name, flags, mode=0o777, *, dir_fd=None):
        if not flags & os.O_DIRECTORY: raise OSError(40, "loop")
        return original(name, flags, mode) if dir_fd is None else original(name, flags, mode, dir_fd=dir_fd)
    monkeypatch.setattr(os, "open", loop); _failure(_load(path, fingerprint), "REVOCATION_STATE_SYMLINK_REJECTED")


# 10 bounded-read/mutation/name-restat tests.
def test_read_is_bounded_to_65537(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); seen, original = [], os.read
    monkeypatch.setattr(os, "read", lambda fd, size: (seen.append(size), original(fd, size))[1]); _load(path, fingerprint); assert max(seen) <= 65537


def test_short_reads_are_accumulated(tmp_path, monkeypatch):
    path, content, fingerprint = _write(tmp_path); _secure(monkeypatch); original = os.read
    monkeypatch.setattr(os, "read", lambda fd, size: original(fd, min(size, 5))); assert _load(path, fingerprint).artifact_fingerprint == hashlib.sha256(content).hexdigest()


def test_read_overflow_is_detected_even_if_size_lies(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); monkeypatch.setattr(os, "read", lambda fd, size: b"x" * 65537); _failure(_load(path, fingerprint), "REVOCATION_STATE_TOO_LARGE")


def test_mutated_mtime_ns_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path)
    leaf_fd = None
    original_open = os.open
    def record_leaf(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal leaf_fd
        if dir_fd is None:
            opened = original_open(name, flags, mode)
        else:
            opened = original_open(name, flags, mode, dir_fd=dir_fd)
        if not flags & os.O_DIRECTORY:
            leaf_fd = opened
        return opened
    monkeypatch.setattr(os, "open", record_leaf)
    _secure(monkeypatch)
    original_fstat = os.fstat
    snapshots = 0
    def changed(fd):
        nonlocal snapshots
        value = original_fstat(fd)
        if fd != leaf_fd:
            return value
        snapshots += 1
        return _FixtureMetadata(
            value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_nlink, value.st_size,
            1_000_000_000 + int(snapshots == 2), 2_000_000_000,
        )
    monkeypatch.setattr(os, "fstat", changed)
    _failure(_load(path, fingerprint), "REVOCATION_STATE_CHANGED_DURING_READ")


def test_mutated_ctime_ns_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path)
    leaf_fd = None
    original_open = os.open
    def record_leaf(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal leaf_fd
        if dir_fd is None:
            opened = original_open(name, flags, mode)
        else:
            opened = original_open(name, flags, mode, dir_fd=dir_fd)
        if not flags & os.O_DIRECTORY:
            leaf_fd = opened
        return opened
    monkeypatch.setattr(os, "open", record_leaf)
    _secure(monkeypatch)
    original_fstat = os.fstat
    snapshots = 0
    def changed(fd):
        nonlocal snapshots
        value = original_fstat(fd)
        if fd != leaf_fd:
            return value
        snapshots += 1
        return _FixtureMetadata(
            value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_nlink, value.st_size,
            1_000_000_000, 2_000_000_000 + int(snapshots == 2),
        )
    monkeypatch.setattr(os, "fstat", changed)
    _failure(_load(path, fingerprint), "REVOCATION_STATE_CHANGED_DURING_READ")


def test_source_does_not_depend_on_float_timestamps():
    text = inspect.getsource(source_module); assert "st_mtime" not in text.replace("st_mtime_ns", "") and "st_ctime" not in text.replace("st_ctime_ns", "")


def test_name_inode_replacement_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); original = os.stat
    def replaced(*args, **kwargs):
        value = original(*args, **kwargs); fields = list(value)
        if kwargs.get("follow_symlinks") is False: fields[1] += 1
        return os.stat_result(fields)
    monkeypatch.setattr(os, "stat", replaced); _failure(_load(path, fingerprint), "REVOCATION_STATE_CHANGED_DURING_READ")


def test_post_read_name_symlink_is_changed_during_read(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); original = os.stat
    def replaced(*args, **kwargs):
        value = original(*args, **kwargs); fields = list(value)
        if kwargs.get("follow_symlinks") is False: fields[0] = 0o120777
        return os.stat_result(fields)
    monkeypatch.setattr(os, "stat", replaced); _failure(_load(path, fingerprint), "REVOCATION_STATE_CHANGED_DURING_READ")


def test_leaf_fstat_occurs_before_and_after_read(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); observed = []; original = os.fstat
    monkeypatch.setattr(os, "fstat", lambda fd: (observed.append(fd), original(fd))[1]); _load(path, fingerprint); assert len(observed) >= 2


def test_name_restat_requires_regular_file(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); original = os.stat
    def replaced(*args, **kwargs):
        value = original(*args, **kwargs); fields = list(value)
        if kwargs.get("follow_symlinks") is False: fields[0] = 0o040755
        return os.stat_result(fields)
    monkeypatch.setattr(os, "stat", replaced); _failure(_load(path, fingerprint), "REVOCATION_STATE_CHANGED_DURING_READ")


# 12 byte framing and canonical parser tests.
def test_canonical_artifact_is_accepted(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(KEY_B)); _secure(monkeypatch); assert _load(path, fingerprint).revoked_signing_key_identifiers == (KEY_B,)
def test_bom_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, b"\xef\xbb\xbf" + _artifact()); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_non_ascii_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact() + b"\x80"); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_cr_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact().replace(b"\n", b"\r\n")); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_missing_final_lf_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact()[:-1]); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_blank_line_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact() + b"\n"); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_whitespace_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact().replace(b"count=", b"count= ")); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_multiple_equals_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact().replace(b"schema_identifier=", b"schema_identifier==")); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_field_order_is_malformed(tmp_path, monkeypatch):
    lines = _artifact().splitlines(); path, _, fingerprint = _write(tmp_path, b"\n".join((lines[1], lines[0], lines[2])) + b"\n"); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_unknown_field_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact() + b"unknown=x\n"); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_duplicate_header_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact() + b"checkpoint_identifier=" + CHECKPOINT.encode() + b"\n"); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_comment_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact() + b"#comment\n"); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")


# 9 count/identifier/duplicate/order tests.
def test_zero_entries_are_valid(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); assert _load(path, fingerprint).revoked_signing_key_identifiers == ()
def test_leading_zero_count_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(count="00")); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_count_mismatch_is_malformed(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(KEY_B, count="0")); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_count_above_limit_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(count="513")); _secure(monkeypatch); _failure(_load(path, fingerprint), "REVOCATION_STATE_TOO_MANY_IDENTIFIERS")
def test_malformed_identifier_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact("ed25519-sha256:ABC")); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_duplicate_identifier_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(KEY_B, KEY_B)); _secure(monkeypatch); _failure(_load(path, fingerprint), "REVOCATION_STATE_DUPLICATE_IDENTIFIER")
def test_unsorted_identifier_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(KEY_C, KEY_B)); _secure(monkeypatch); _failure(_load(path, fingerprint), "REVOCATION_STATE_IDENTIFIERS_NOT_SORTED")
def test_sorted_identifiers_are_returned_as_tuple(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(KEY_B, KEY_C)); _secure(monkeypatch); assert _load(path, fingerprint).revoked_signing_key_identifiers == (KEY_B, KEY_C)
def test_identifier_grammar_precedes_duplicate_and_order(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact("broken", "broken")); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")


# 5 fingerprint/schema/checkpoint tests.
def test_fingerprint_is_sha256_of_raw_bytes(tmp_path, monkeypatch):
    path, content, fingerprint = _write(tmp_path); _secure(monkeypatch); assert _load(path, fingerprint).artifact_fingerprint == hashlib.sha256(content).hexdigest()
def test_fingerprint_precedes_semantic_parsing(tmp_path, monkeypatch):
    path, _, _ = _write(tmp_path, b"not=canonical\n"); _secure(monkeypatch); _failure(_load(path, "0" * 64), "REVOCATION_STATE_ARTIFACT_FINGERPRINT_MISMATCH")
def test_unsupported_canonical_schema_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(schema="PHASE12-OWNER-SIGNING-KEY-REVOCATION-STATE-V2")); _secure(monkeypatch); _failure(_load(path, fingerprint), "UNSUPPORTED_REVOCATION_STATE_SCHEMA")
def test_malformed_schema_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(schema="not-a-schema")); _secure(monkeypatch); _failure(_load(path, fingerprint), "MALFORMED_REVOCATION_STATE")
def test_checkpoint_mismatch_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(checkpoint="phase12-revocation-checkpoint-fedcba9876543210")); _secure(monkeypatch); _failure(_load(path, fingerprint), "REVOCATION_STATE_CHECKPOINT_MISMATCH")


# 3 active-key/result tests.
def test_active_key_listed_as_revoked_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(KEY_A)); _secure(monkeypatch); _failure(_load(path, fingerprint), "ACTIVE_SIGNING_KEY_REVOKED")
def test_result_is_frozen_slotted_and_exact(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); result = _load(path, fingerprint)
    assert tuple(type(result).__dataclass_fields__) == ("is_loaded", "failure_codes", "schema_identifier", "checkpoint_identifier", "revoked_signing_key_identifiers", "artifact_fingerprint") and not hasattr(result, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)): result.is_loaded = False
def test_failure_repr_is_fixed_and_non_disclosing(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path, _artifact(KEY_A)); _secure(monkeypatch); result = _load(path, fingerprint); _failure(result, "ACTIVE_SIGNING_KEY_REVOKED")
    assert path not in repr(result) and KEY_A not in repr(result) and fingerprint not in repr(result)


# 4 purity/non-disclosure/trust-boundary tests.
def test_source_has_no_write_or_install_surface():
    text = inspect.getsource(source_module); assert not any(word in text for word in ("chmod", "chown", "mkdir", "rename", "replace", "write"))
def test_source_has_no_configuration_network_or_service_surface():
    text = inspect.getsource(source_module); assert not any(word in text for word in ("git", "config", "credential", "environ", "socket", "requests", "subprocess", "systemctl", "telegram"))
def test_source_has_no_clock_replay_or_authorization_surface():
    text = inspect.getsource(source_module); assert not any(word in text for word in ("datetime.now", "time.time", "replay", "activate", "authorize", "verify_phase_12"))
def test_success_does_not_claim_trust_or_freshness(tmp_path, monkeypatch):
    path, _, fingerprint = _write(tmp_path); _secure(monkeypatch); result = _load(path, fingerprint)
    assert not any(hasattr(result, name) for name in ("authorized", "trust_bootstrapped", "revocation_fresh", "toctou_safe"))
