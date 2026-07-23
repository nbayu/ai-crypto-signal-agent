"""RED contract for the unwired Phase 12 owner verification public-key loader."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import inspect
import os

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
import pytest

import engine.phase_12_owner_verification_public_key_loader_v1 as loader_module


_PREFIX = "ed25519-sha256:"


def _key_material() -> tuple[bytes, bytes, str, str]:
    private = Ed25519PrivateKey.from_private_bytes(b"\x01" * 32)
    public = private.public_key()
    raw = public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    pem = public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    fingerprint = hashlib.sha256(raw).hexdigest()
    return pem, raw, fingerprint, _PREFIX + fingerprint


def _write_key(tmp_path, content: bytes | None = None) -> tuple[str, bytes, str, str]:
    pem, raw, fingerprint, key_id = _key_material()
    selected = tmp_path / "owner-public-key.pem"
    selected.write_bytes(pem if content is None else content)
    return str(selected), raw, fingerprint, key_id


def _root_secure_metadata(monkeypatch, *, preserve_nlink_for=None) -> None:
    real_fstat, real_stat = os.fstat, os.stat

    def secured(value, descriptor=None):
        fields = list(value)
        fields[0] &= ~0o022
        if preserve_nlink_for is None or not preserve_nlink_for(descriptor):
            fields[3] = 1
        fields[4] = 0
        return os.stat_result(fields)

    monkeypatch.setattr(os, "fstat", lambda descriptor: secured(real_fstat(descriptor), descriptor))
    monkeypatch.setattr(os, "stat", lambda *args, **kwargs: secured(real_stat(*args, **kwargs)))


def _load(path: str, fingerprint: str, key_id: str):
    return loader_module.load_phase_12_owner_verification_public_key_v1(
        path=path,
        expected_public_key_fingerprint=fingerprint,
        expected_signing_key_identifier=key_id,
    )


def _failure(result, code: str) -> None:
    assert result.is_loaded is False
    assert result.failure_codes == (code,)
    assert result.raw_public_key_bytes is None
    assert result.derived_signing_key_identifier is None


# 4 public-surface/signature/type tests.
def test_public_all_is_exact():
    assert loader_module.__all__ == ("load_phase_12_owner_verification_public_key_v1",)


def test_function_name_is_exact():
    assert loader_module.load_phase_12_owner_verification_public_key_v1.__name__ == "load_phase_12_owner_verification_public_key_v1"


def test_function_signature_is_keyword_only_and_exact():
    signature = inspect.signature(loader_module.load_phase_12_owner_verification_public_key_v1)
    assert tuple(signature.parameters) == ("path", "expected_public_key_fingerprint", "expected_signing_key_identifier")
    assert all(item.kind is inspect.Parameter.KEYWORD_ONLY for item in signature.parameters.values())


def test_result_types_are_not_publicly_exported():
    assert not {name for name in loader_module.__all__ if "Result" in name or "Failure" in name}


# 12 path, symlink, parent, and metadata tests.
def test_relative_path_is_rejected():
    _, _, fingerprint, key_id = _key_material()
    _failure(_load("relative.pem", fingerprint, key_id), "PATH_TYPE_INVALID")


def test_root_path_is_rejected():
    _, _, fingerprint, key_id = _key_material()
    _failure(_load("/", fingerprint, key_id), "PATH_TYPE_INVALID")


def test_dot_component_is_rejected():
    _, _, fingerprint, key_id = _key_material()
    _failure(_load("/tmp/./key.pem", fingerprint, key_id), "PATH_TYPE_INVALID")


def test_dotdot_component_is_rejected():
    _, _, fingerprint, key_id = _key_material()
    _failure(_load("/tmp/a/../key.pem", fingerprint, key_id), "PATH_TYPE_INVALID")


def test_final_symlink_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    link = tmp_path / "link.pem"
    link.symlink_to(path)
    _root_secure_metadata(monkeypatch)
    _failure(_load(str(link), fingerprint, key_id), "TRUST_MATERIAL_SYMLINK_REJECTED")


def test_parent_symlink_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    linked = tmp_path.parent / "phase12-loader-link"
    linked.symlink_to(tmp_path, target_is_directory=True)
    _root_secure_metadata(monkeypatch)
    _failure(_load(str(linked / os.path.basename(path)), fingerprint, key_id), "TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH")


def test_non_directory_parent_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    file_parent = tmp_path / "not-a-directory"
    file_parent.write_bytes(b"x")
    _root_secure_metadata(monkeypatch)
    _failure(_load(str(file_parent / os.path.basename(path)), fingerprint, key_id), "TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH")


def test_parent_uid_mismatch_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    original = os.fstat
    def wrong_uid(descriptor):
        fields = list(original(descriptor)); fields[4] = 1; return os.stat_result(fields)
    monkeypatch.setattr(os, "fstat", wrong_uid)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH")


def test_parent_group_or_other_write_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    original = os.fstat
    def unsafe_mode(descriptor):
        fields = list(original(descriptor)); fields[0] |= 0o022; return os.stat_result(fields)
    monkeypatch.setattr(os, "fstat", unsafe_mode)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH")


def test_leaf_must_be_regular_file(tmp_path, monkeypatch):
    directory = tmp_path / "directory.pem"
    directory.mkdir()
    _, _, fingerprint, key_id = _key_material()
    _root_secure_metadata(monkeypatch)
    _failure(_load(str(directory), fingerprint, key_id), "TRUST_MATERIAL_NOT_REGULAR_FILE")


def test_leaf_owner_mismatch_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    leaf_descriptor = None
    original_open = os.open

    def record_leaf_descriptor(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal leaf_descriptor
        if dir_fd is None:
            descriptor = original_open(name, flags, mode)
        else:
            descriptor = original_open(name, flags, mode, dir_fd=dir_fd)
        if not flags & os.O_DIRECTORY:
            leaf_descriptor = descriptor
        return descriptor

    monkeypatch.setattr(os, "open", record_leaf_descriptor)
    _root_secure_metadata(monkeypatch)
    original = os.fstat

    def wrong_leaf_uid(descriptor):
        fields = list(original(descriptor))
        if descriptor == leaf_descriptor:
            fields[4] = 1
        return os.stat_result(fields)

    monkeypatch.setattr(os, "fstat", wrong_leaf_uid)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_OWNER_MISMATCH")


def test_leaf_mode_and_hard_link_contract_is_enforced(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    leaf_descriptor = None
    original_open = os.open

    def record_leaf_descriptor(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal leaf_descriptor
        if dir_fd is None:
            descriptor = original_open(name, flags, mode)
        else:
            descriptor = original_open(name, flags, mode, dir_fd=dir_fd)
        if not flags & os.O_DIRECTORY:
            leaf_descriptor = descriptor
        return descriptor

    monkeypatch.setattr(os, "open", record_leaf_descriptor)
    _root_secure_metadata(monkeypatch, preserve_nlink_for=lambda descriptor: descriptor == leaf_descriptor)
    linked = tmp_path / "other.pem"
    os.link(path, linked)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_HARD_LINK_REJECTED")


# 9 bounded-read and mutation-detection tests.
def test_oversized_source_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path, b"x" * 4097)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_TOO_LARGE")


def test_empty_source_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path, b"")
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_EMPTY")


def test_read_is_bounded_to_maximum_plus_one(tmp_path, monkeypatch):
    path, raw, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    observed, original = [], os.read
    monkeypatch.setattr(os, "read", lambda descriptor, size: (observed.append(size), original(descriptor, size))[1])
    result = _load(path, fingerprint, key_id)
    assert result.raw_public_key_bytes == raw and max(observed) <= 4097


def test_short_reads_are_accumulated(tmp_path, monkeypatch):
    path, raw, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    original = os.read
    monkeypatch.setattr(os, "read", lambda descriptor, size: original(descriptor, min(size, 7)))
    assert _load(path, fingerprint, key_id).raw_public_key_bytes == raw


def test_mutation_during_read_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    original, changed = os.read, False
    def mutate(descriptor, size):
        nonlocal changed
        value = original(descriptor, size)
        if not changed:
            changed = True
            os.utime(path, None)
        return value
    monkeypatch.setattr(os, "read", mutate)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_CHANGED_DURING_READ")


def test_descriptor_metadata_change_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    original, calls = os.fstat, 0
    def changed(descriptor):
        nonlocal calls
        calls += 1
        fields = list(original(descriptor))
        if calls > 1:
            fields[8] += 1
        return os.stat_result(fields)
    monkeypatch.setattr(os, "fstat", changed)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_CHANGED_DURING_READ")


def test_name_to_descriptor_inode_mismatch_is_rejected(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    original = os.stat
    def swapped(*args, **kwargs):
        fields = list(original(*args, **kwargs))
        if kwargs.get("follow_symlinks") is False:
            fields[1] += 1
        return os.stat_result(fields)
    monkeypatch.setattr(os, "stat", swapped)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_CHANGED_DURING_READ")


def test_unavailable_leaf_is_fail_closed(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    os.unlink(path)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "TRUST_MATERIAL_UNAVAILABLE")


def test_descriptor_read_returns_raw_key_not_pem(tmp_path, monkeypatch):
    path, raw, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    assert _load(path, fingerprint, key_id).raw_public_key_bytes == raw


# 8 strict PEM/container/key-type tests.
def test_canonical_ed25519_pem_is_accepted(tmp_path, monkeypatch):
    path, raw, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    assert _load(path, fingerprint, key_id).raw_public_key_bytes == raw


def test_alternate_pem_newlines_are_rejected(tmp_path, monkeypatch):
    pem, _, fingerprint, key_id = _key_material()
    path, _, _, _ = _write_key(tmp_path, pem.replace(b"\n", b"\r\n"))
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "MALFORMED_PUBLIC_KEY_CONTAINER")


def test_trailing_pem_data_is_rejected(tmp_path, monkeypatch):
    pem, _, fingerprint, key_id = _key_material()
    path, _, _, _ = _write_key(tmp_path, pem + b"x")
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "MALFORMED_PUBLIC_KEY_CONTAINER")


def test_multiple_pem_blocks_are_rejected(tmp_path, monkeypatch):
    pem, _, fingerprint, key_id = _key_material()
    path, _, _, _ = _write_key(tmp_path, pem + pem)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "MALFORMED_PUBLIC_KEY_CONTAINER")


def test_private_key_container_is_rejected(tmp_path, monkeypatch):
    private = Ed25519PrivateKey.from_private_bytes(b"\x02" * 32)
    content = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    _, _, fingerprint, key_id = _key_material()
    path, _, _, _ = _write_key(tmp_path, content)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "MALFORMED_PUBLIC_KEY_CONTAINER")


def test_openssh_container_is_rejected(tmp_path, monkeypatch):
    private = Ed25519PrivateKey.from_private_bytes(b"\x03" * 32)
    content = private.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
    _, _, fingerprint, key_id = _key_material()
    path, _, _, _ = _write_key(tmp_path, content)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "MALFORMED_PUBLIC_KEY_CONTAINER")


def test_rsa_public_key_is_unsupported(tmp_path, monkeypatch):
    private = generate_private_key(public_exponent=65537, key_size=2048)
    content = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    _, _, fingerprint, key_id = _key_material()
    path, _, _, _ = _write_key(tmp_path, content)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, key_id), "UNSUPPORTED_PUBLIC_KEY_TYPE")


def test_parser_value_error_maps_to_malformed_container(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    monkeypatch.setattr(loader_module, "load_pem_public_key", lambda value: (_ for _ in ()).throw(ValueError()))
    _failure(_load(path, fingerprint, key_id), "MALFORMED_PUBLIC_KEY_CONTAINER")


# 8 raw-key/fingerprint/key-ID tests.
def test_success_returns_exact_raw_32_byte_key(tmp_path, monkeypatch):
    path, raw, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    result = _load(path, fingerprint, key_id)
    assert type(result.raw_public_key_bytes) is bytes and result.raw_public_key_bytes == raw and len(raw) == 32


def test_fingerprint_is_sha256_lowercase_hex(tmp_path, monkeypatch):
    path, raw, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    result = _load(path, fingerprint, key_id)
    assert hashlib.sha256(raw).hexdigest() == fingerprint and result.derived_signing_key_identifier == key_id


def test_derived_key_id_has_exact_prefix(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    assert _load(path, fingerprint, key_id).derived_signing_key_identifier == _PREFIX + fingerprint


def test_fingerprint_mismatch_is_fail_closed(tmp_path, monkeypatch):
    path, _, _, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, "0" * 64, key_id), "PUBLIC_KEY_FINGERPRINT_MISMATCH")


def test_key_id_mismatch_is_fail_closed(tmp_path, monkeypatch):
    path, _, fingerprint, _ = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, fingerprint, _PREFIX + "0" * 64), "PUBLIC_KEY_IDENTIFIER_MISMATCH")


def test_expected_fingerprint_requires_lowercase_hex(tmp_path):
    path, _, _, key_id = _write_key(tmp_path)
    with pytest.raises(TypeError) as caught:
        _load(path, "A" * 64, key_id)
    assert caught.value.args == ()


def test_expected_key_id_requires_exact_grammar(tmp_path):
    path, _, fingerprint, _ = _write_key(tmp_path)
    with pytest.raises(TypeError) as caught:
        _load(path, fingerprint, "ed25519-sha256:ABC")
    assert caught.value.args == ()


def test_raw_key_bytes_are_not_pem_bytes(tmp_path, monkeypatch):
    path, raw, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    assert _load(path, fingerprint, key_id).raw_public_key_bytes == raw and b"BEGIN" not in raw


# 7 exception/precedence tests.
def test_wrong_caller_type_raises_empty_type_error():
    _, _, fingerprint, key_id = _key_material()
    with pytest.raises(TypeError) as caught:
        _load(1, fingerprint, key_id)
    assert caught.value.args == ()


def test_path_form_precedes_unavailable_open():
    _, _, fingerprint, key_id = _key_material()
    _failure(_load("relative", fingerprint, key_id), "PATH_TYPE_INVALID")


def test_parser_unsupported_algorithm_maps_to_unsupported_type(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    monkeypatch.setattr(loader_module, "load_pem_public_key", lambda value: (_ for _ in ()).throw(UnsupportedAlgorithm("blocked")))
    _failure(_load(path, fingerprint, key_id), "UNSUPPORTED_PUBLIC_KEY_TYPE")


def test_non_ed25519_object_is_unsupported_after_parsing(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    rsa = generate_private_key(public_exponent=65537, key_size=2048).public_key()
    monkeypatch.setattr(loader_module, "load_pem_public_key", lambda value: rsa)
    _failure(_load(path, fingerprint, key_id), "UNSUPPORTED_PUBLIC_KEY_TYPE")


def test_parser_type_error_propagates(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    monkeypatch.setattr(loader_module, "load_pem_public_key", lambda value: (_ for _ in ()).throw(TypeError()))
    with pytest.raises(TypeError):
        _load(path, fingerprint, key_id)


def test_unrelated_exception_propagates(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    monkeypatch.setattr(loader_module, "load_pem_public_key", lambda value: (_ for _ in ()).throw(RuntimeError("unexpected")))
    with pytest.raises(RuntimeError):
        _load(path, fingerprint, key_id)


def test_base_exception_propagates(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    monkeypatch.setattr(loader_module, "load_pem_public_key", lambda value: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        _load(path, fingerprint, key_id)


# 6 immutable result/no-bytes-on-failure tests.
def test_success_result_has_exact_field_shape(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    result = _load(path, fingerprint, key_id)
    assert tuple(type(result).__dataclass_fields__) == ("is_loaded", "failure_codes", "raw_public_key_bytes", "derived_signing_key_identifier")


def test_result_is_frozen_and_slotted(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    result = _load(path, fingerprint, key_id)
    assert not hasattr(result, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        result.is_loaded = False


def test_success_result_has_no_failure_code(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    result = _load(path, fingerprint, key_id)
    assert result.is_loaded is True and result.failure_codes == () and result.derived_signing_key_identifier == key_id


def test_failure_has_one_code_and_no_sensitive_fields(tmp_path, monkeypatch):
    path, _, _, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    _failure(_load(path, "0" * 64, key_id), "PUBLIC_KEY_FINGERPRINT_MISMATCH")


def test_failure_repr_does_not_disclose_path_or_key_facts(tmp_path, monkeypatch):
    path, _, _, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    result = _load(path, "0" * 64, key_id)
    rendered = repr(result)
    assert path not in rendered and key_id not in rendered and "owner-public-key" not in rendered


def test_failure_codes_are_immutable_tuple(tmp_path, monkeypatch):
    path, _, _, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    assert type(_load(path, "0" * 64, key_id).failure_codes) is tuple


# 6 no-write/no-network/no-Git/no-config/no-credential/no-service/non-overclaim tests.
def test_module_source_has_no_write_or_install_surface():
    source = inspect.getsource(loader_module)
    assert not any(name in source for name in ("chmod", "chown", "mkdir", "write", "install"))


def test_module_source_has_no_network_or_service_surface():
    source = inspect.getsource(loader_module)
    assert not any(name in source for name in ("socket", "requests", "telegram", "subprocess", "systemctl"))


def test_module_source_has_no_git_or_configuration_surface():
    source = inspect.getsource(loader_module)
    assert not any(name in source for name in ("git", "config", "credential", "environ"))


def test_module_source_has_no_clock_or_mutable_registry_surface():
    source = inspect.getsource(loader_module)
    assert not any(name in source for name in ("datetime.now", "time.time", "cache", "registry", "setter", "override"))


def test_success_does_not_claim_trust_bootstrap_or_authorization(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    result = _load(path, fingerprint, key_id)
    assert not hasattr(result, "authorized") and not hasattr(result, "trust_bootstrapped")


def test_success_does_not_claim_toctou_or_revocation_freshness(tmp_path, monkeypatch):
    path, _, fingerprint, key_id = _write_key(tmp_path)
    _root_secure_metadata(monkeypatch)
    result = _load(path, fingerprint, key_id)
    assert not hasattr(result, "toctou_safe") and not hasattr(result, "revocation_fresh")
