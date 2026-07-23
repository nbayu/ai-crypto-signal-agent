"""Contract tests for the bounded accepted-locked-commit marker reader."""

from __future__ import annotations

import dataclasses
import errno
import importlib
import inspect
import os
import sys

import pytest


MODULE_NAME = "engine.phase_12_activation_mode_accepted_locked_commit_marker_reader_v1"
FACTS_NAME = "Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1"
ERROR_NAME = "Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1"
READER_NAME = "read_phase_12_activation_accepted_locked_commit_marker_v1"
PUBLIC_SURFACE = (FACTS_NAME, ERROR_NAME, READER_NAME)
MAXIMUM_SIZE = 4096
READ_SIZE = 4097
VALID_PATH = "/caller-supplied-marker"
NONNORMALIZED_PATH = "/caller//./nested/../marker"
ERRORS = {
    "invalid_path": "INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH",
    "absent": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH_ABSENT",
    "denied": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_PERMISSION_DENIED",
    "symlink": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_SYMBOLIC_LINK_REJECTED",
    "not_directory": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH_COMPONENT_NOT_DIRECTORY",
    "open": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_OPEN_FAILED",
    "read": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_FAILED",
    "close": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_CLOSE_FAILED",
    "too_large": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_TOO_LARGE",
    "malformed": "ACCEPTED_LOCKED_COMMIT_MARKER_READ_MALFORMED_RESULT",
}
EXPECTED_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK


def _module() -> object:
    return importlib.import_module(MODULE_NAME)


def _reader(module: object, *, path: str) -> object:
    return getattr(module, READER_NAME)(path=path)


def _facts(module: object) -> type[object]:
    return getattr(module, FACTS_NAME)


def _error_type(module: object) -> type[BaseException]:
    return getattr(module, ERROR_NAME)


def _assert_reader_error(caught: pytest.ExceptionInfo[BaseException], code: str) -> None:
    assert type(caught.value).__name__ == ERROR_NAME
    assert str(caught.value) == code
    assert repr(caught.value) == f"{ERROR_NAME}()"


def _patch_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    *,
    open_result: object = 17,
    read_result: object = b"",
    close_result: object = None,
) -> dict[str, list[object]]:
    calls: dict[str, list[object]] = {"open": [], "read": [], "close": []}
    boundary = getattr(module, "_os")

    def fake_open(path: object, flags: object) -> object:
        calls["open"].append((path, flags))
        if isinstance(open_result, BaseException):
            raise open_result
        return open_result

    def fake_read(descriptor: object, size: object) -> object:
        calls["read"].append((descriptor, size))
        if isinstance(read_result, BaseException):
            raise read_result
        return read_result

    def fake_close(descriptor: object) -> object:
        calls["close"].append(descriptor)
        if isinstance(close_result, BaseException):
            raise close_result
        return close_result

    monkeypatch.setattr(boundary, "open", fake_open)
    monkeypatch.setattr(boundary, "read", fake_read)
    monkeypatch.setattr(boundary, "close", fake_close)
    return calls


def test_exact_public_surface_and_no_combined_api() -> None:
    module = _module()
    assert module.__all__ == PUBLIC_SURFACE
    public_names = {name for name in module.__dict__ if not name.startswith("_")}
    assert public_names == set(PUBLIC_SURFACE)


def test_facts_model_is_exact_immutable_slotted_keyword_only_and_sanitized() -> None:
    module = _module()
    facts_type = _facts(module)
    assert dataclasses.is_dataclass(facts_type)
    assert [field.name for field in dataclasses.fields(facts_type)] == ["content_bytes"]
    assert facts_type.__dataclass_params__.frozen is True
    assert facts_type.__dataclass_params__.init is True
    assert "__dict__" not in facts_type.__slots__
    with pytest.raises(TypeError):
        facts_type(b"x")
    value = facts_type(content_bytes=b"x")
    assert repr(value) == f"{FACTS_NAME}()"
    assert value == facts_type(content_bytes=b"x")
    assert hash(value) == hash(facts_type(content_bytes=b"x"))
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        value.content_bytes = b"changed"


def test_facts_reject_nonexact_bytes_before_hostile_interaction() -> None:
    module = _module()
    facts_type = _facts(module)
    calls = {"len": 0, "repr": 0}

    class HostileBytes(bytes):
        def __len__(self) -> int:
            calls["len"] += 1
            raise AssertionError("unexpected length")

        def __repr__(self) -> str:
            calls["repr"] += 1
            raise AssertionError("unexpected repr")

    for value in (bytearray(b"x"), memoryview(b"x"), HostileBytes(b"x"), object()):
        with pytest.raises(TypeError) as caught:
            facts_type(content_bytes=value)
        assert type(caught.value) is TypeError
        assert caught.value.args == ()
        assert str(caught.value) == ""
        assert repr(caught.value) == "TypeError()"
    assert calls == {"len": 0, "repr": 0}


def test_facts_preserve_raw_empty_and_bounded_bytes() -> None:
    module = _module()
    facts_type = _facts(module)
    for content in (b"", b"\x00\r\n", b"x" * MAXIMUM_SIZE):
        facts = facts_type(content_bytes=content)
        assert type(facts.content_bytes) is bytes
        assert facts.content_bytes == content


def test_facts_reject_oversized_bytes_without_disclosure() -> None:
    module = _module()
    facts_type = _facts(module)
    oversized = b"s" * READ_SIZE
    with pytest.raises(ValueError) as caught:
        facts_type(content_bytes=oversized)
    assert type(caught.value) is ValueError
    assert caught.value.args == ()
    assert str(caught.value) == ""
    assert repr(caught.value) == "ValueError()"
    assert "s" * 32 not in str(caught.value) + repr(caught.value)


def test_error_type_is_fixed_sanitized_and_fieldless() -> None:
    module = _module()
    error_type = _error_type(module)
    error = error_type(ERRORS["invalid_path"])
    assert str(error) == ERRORS["invalid_path"]
    assert repr(error) == f"{ERROR_NAME}()"
    assert not getattr(error, "__dict__", {})


def test_reader_signature_is_exact_keyword_only_path() -> None:
    module = _module()
    reader = getattr(module, READER_NAME)
    signature = inspect.signature(reader)
    parameter = signature.parameters["path"]
    assert list(signature.parameters) == ["path"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    assert signature.return_annotation == _facts(module)
    with pytest.raises(TypeError):
        reader(VALID_PATH)
    with pytest.raises(TypeError):
        reader(path=VALID_PATH, extra=True)


def test_invalid_and_hostile_paths_make_zero_boundary_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    error_type = _error_type(module)
    calls = _patch_boundaries(monkeypatch, module)
    hostile_calls = {"startswith": 0, "contains": 0, "repr": 0}

    class HostilePath(str):
        def startswith(self, value: object, *args: object) -> bool:
            hostile_calls["startswith"] += 1
            raise AssertionError("unexpected startswith")

        def __contains__(self, value: object) -> bool:
            hostile_calls["contains"] += 1
            raise AssertionError("unexpected contains")

        def __repr__(self) -> str:
            hostile_calls["repr"] += 1
            raise AssertionError("unexpected repr")

    for path in ("", "relative", "\x00", HostilePath(VALID_PATH), b"/bytes", object()):
        with pytest.raises(error_type) as caught:
            _reader(module, path=path)
        _assert_reader_error(caught, ERRORS["invalid_path"])
    assert calls == {"open": [], "read": [], "close": []}
    assert hostile_calls == {"startswith": 0, "contains": 0, "repr": 0}


def test_open_uses_verbatim_path_exact_flags_and_single_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    calls = _patch_boundaries(monkeypatch, module, open_result=23, read_result=b"raw")
    facts = _reader(module, path=NONNORMALIZED_PATH)
    assert facts.content_bytes == b"raw"
    assert calls == {
        "open": [(NONNORMALIZED_PATH, EXPECTED_FLAGS)],
        "read": [(23, READ_SIZE)],
        "close": [23],
    }


def test_malformed_open_results_never_read_or_close(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    error_type = _error_type(module)

    class IntegerSubclass(int):
        pass

    for descriptor in (True, IntegerSubclass(3), -1, None, object()):
        calls = _patch_boundaries(monkeypatch, module, open_result=descriptor)
        with pytest.raises(error_type) as caught:
            _reader(module, path=VALID_PATH)
        _assert_reader_error(caught, ERRORS["malformed"])
        assert len(calls["open"]) == 1
        assert calls["read"] == []
        assert calls["close"] == []


def test_one_read_preserves_empty_and_one_byte_results(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    for content in (b"", b"\x00"):
        calls = _patch_boundaries(monkeypatch, module, read_result=content)
        facts = _reader(module, path=VALID_PATH)
        assert facts.content_bytes == content
        assert len(calls["read"]) == 1
        assert calls["read"][0][1] == READ_SIZE
        assert len(calls["close"]) == 1


def test_4096_byte_read_is_returned_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    content = b"a" * MAXIMUM_SIZE
    calls = _patch_boundaries(monkeypatch, module, read_result=content)
    facts = _reader(module, path=VALID_PATH)
    assert facts.content_bytes == content
    assert calls["read"] == [(17, READ_SIZE)]
    assert calls["close"] == [17]


def test_4097_byte_read_is_too_large_and_still_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    error_type = _error_type(module)
    calls = _patch_boundaries(monkeypatch, module, read_result=b"a" * READ_SIZE)
    with pytest.raises(error_type) as caught:
        _reader(module, path=VALID_PATH)
    _assert_reader_error(caught, ERRORS["too_large"])
    assert calls["read"] == [(17, READ_SIZE)]
    assert calls["close"] == [17]


def test_malformed_read_results_are_rejected_before_interaction(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    error_type = _error_type(module)
    calls_by_value: list[dict[str, list[object]]] = []
    hostile_calls = {"len": 0, "repr": 0}

    class HostileBytes(bytes):
        def __len__(self) -> int:
            hostile_calls["len"] += 1
            raise AssertionError("unexpected length")

        def __repr__(self) -> str:
            hostile_calls["repr"] += 1
            raise AssertionError("unexpected repr")

    for value in (bytearray(b"x"), memoryview(b"x"), HostileBytes(b"x"), None, object()):
        calls = _patch_boundaries(monkeypatch, module, read_result=value)
        calls_by_value.append(calls)
        with pytest.raises(error_type) as caught:
            _reader(module, path=VALID_PATH)
        _assert_reader_error(caught, ERRORS["malformed"])
        assert calls["close"] == [17]
    assert hostile_calls == {"len": 0, "repr": 0}
    assert len(calls_by_value) == 5


def test_close_runs_once_after_successful_read(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    calls = _patch_boundaries(monkeypatch, module, open_result=31, read_result=b"ok", close_result=None)
    assert _reader(module, path=VALID_PATH).content_bytes == b"ok"
    assert calls == {"open": [(VALID_PATH, EXPECTED_FLAGS)], "read": [(31, READ_SIZE)], "close": [31]}


def test_malformed_close_result_controls_successful_read(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    error_type = _error_type(module)
    calls = _patch_boundaries(monkeypatch, module, read_result=b"ok", close_result=0)
    with pytest.raises(error_type) as caught:
        _reader(module, path=VALID_PATH)
    _assert_reader_error(caught, ERRORS["malformed"])
    assert calls["close"] == [17]


def test_open_errno_mapping_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    error_type = _error_type(module)
    mappings = (
        (FileNotFoundError(errno.ENOENT, "hidden"), ERRORS["absent"]),
        (PermissionError(errno.EACCES, "hidden"), ERRORS["denied"]),
        (OSError(errno.EPERM, "hidden"), ERRORS["denied"]),
        (OSError(errno.ELOOP, "hidden"), ERRORS["symlink"]),
        (OSError(errno.ENOTDIR, "hidden"), ERRORS["not_directory"]),
        (OSError(errno.EIO, "hidden"), ERRORS["open"]),
    )
    for failure, code in mappings:
        calls = _patch_boundaries(monkeypatch, module, open_result=failure)
        with pytest.raises(error_type) as caught:
            _reader(module, path=VALID_PATH)
        _assert_reader_error(caught, code)
        assert calls["read"] == []
        assert calls["close"] == []


def test_read_and_close_oserrors_map_to_distinct_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    error_type = _error_type(module)
    calls = _patch_boundaries(monkeypatch, module, read_result=OSError(errno.EIO, "hidden"))
    with pytest.raises(error_type) as caught:
        _reader(module, path=VALID_PATH)
    _assert_reader_error(caught, ERRORS["read"])
    assert calls["close"] == [17]
    calls = _patch_boundaries(monkeypatch, module, read_result=b"ok", close_result=OSError(errno.EIO, "hidden"))
    with pytest.raises(error_type) as caught:
        _reader(module, path=VALID_PATH)
    _assert_reader_error(caught, ERRORS["close"])
    assert calls["close"] == [17]


def test_prior_controlled_read_outcomes_win_over_close_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    error_type = _error_type(module)
    cases = (
        (OSError(errno.EIO, "hidden"), ERRORS["read"]),
        (b"a" * READ_SIZE, ERRORS["too_large"]),
        (bytearray(b"x"), ERRORS["malformed"]),
    )
    for read_result, code in cases:
        calls = _patch_boundaries(
            monkeypatch,
            module,
            read_result=read_result,
            close_result=OSError(errno.EIO, "hidden"),
        )
        with pytest.raises(error_type) as caught:
            _reader(module, path=VALID_PATH)
        _assert_reader_error(caught, code)
        assert calls["close"] == [17]


def test_ordinary_exceptions_propagate_with_read_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    primary = RuntimeError("read-primary")
    calls = _patch_boundaries(monkeypatch, module, read_result=primary, close_result=RuntimeError("close-secondary"))
    with pytest.raises(RuntimeError) as caught:
        _reader(module, path=VALID_PATH)
    assert caught.value is primary
    assert calls["close"] == [17]
    open_primary = RuntimeError("open-primary")
    calls = _patch_boundaries(monkeypatch, module, open_result=open_primary)
    with pytest.raises(RuntimeError) as caught:
        _reader(module, path=VALID_PATH)
    assert caught.value is open_primary
    assert calls["read"] == []
    assert calls["close"] == []


def test_baseexceptions_propagate_with_read_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    primary = KeyboardInterrupt()
    calls = _patch_boundaries(monkeypatch, module, read_result=primary, close_result=SystemExit())
    with pytest.raises(KeyboardInterrupt) as caught:
        _reader(module, path=VALID_PATH)
    assert caught.value is primary
    assert calls["close"] == [17]
    close_primary = SystemExit()
    _patch_boundaries(monkeypatch, module, read_result=b"ok", close_result=close_primary)
    with pytest.raises(SystemExit) as caught:
        _reader(module, path=VALID_PATH)
    assert caught.value is close_primary


def test_reader_has_no_canonical_path_component_coupling() -> None:
    module = _module()
    source = inspect.getsource(module)
    assert "accepted_locked_commit_marker_path_v1" not in source
    assert "get_phase_12_activation_accepted_locked_commit_marker_path_v1" not in source


def test_reader_has_no_metadata_inspector_or_validator_coupling() -> None:
    module = _module()
    source = inspect.getsource(module)
    assert "accepted_locked_commit_marker_metadata_inspector_v1" not in source
    assert "accepted_locked_commit_marker_metadata_validator_v1" not in source
    for token in ("lstat", "st_mode", "st_uid", "st_gid", "st_nlink"):
        assert token not in source


def test_reader_has_no_parser_or_content_interpretation_coupling() -> None:
    module = _module()
    source = inspect.getsource(module)
    assert "accepted_locked_commit_marker_parser_v1" not in source
    for token in (
        "parse_phase_12_activation_accepted_locked_commit_marker_v1",
        "Phase12ActivationAcceptedLockedCommitMarkerV1",
        "Phase12ActivationAcceptedLockedCommitMarkerDocumentErrorV1",
        ".decode(",
        ".strip(",
        ".splitlines(",
        ".split(",
    ):
        assert token not in source


def test_reader_source_is_pure_and_test_uses_only_narrow_boundary_fakes() -> None:
    module = _module()
    source = inspect.getsource(module)
    forbidden = (
        "pathlib",
        "subprocess",
        "environ",
        "argv",
        "logging",
        "socket",
        "requests",
        "telegram",
        "systemctl",
        "time.",
        "random",
        "uuid",
        "sleep(",
        "realpath",
        "abspath",
        "readlink",
        "scandir",
        "listdir",
        ".stat(",
        ".lstat(",
        "builtins.open",
    )
    for token in forbidden:
        assert token not in source
    assert "_os.open" in source
    assert "_os.read" in source
    assert "_os.close" in source
    test_source = inspect.getsource(sys.modules[__name__])
    forbidden_global_patch = "monkeypatch.setattr(" + "os."
    assert forbidden_global_patch not in test_source
