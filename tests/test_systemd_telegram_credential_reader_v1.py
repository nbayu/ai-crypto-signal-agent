"""Contract tests for the future systemd Telegram credential reader."""
from __future__ import annotations

from dataclasses import dataclass
import ast
import inspect
import io
import os
from pathlib import Path
import stat

import pytest

import engine.systemd_telegram_credential_reader_v1 as module
from engine.systemd_telegram_credential_reader_v1 import (
    SystemdTelegramCredentialErrorV1,
    read_systemd_telegram_credential,
)


_DIRECTORY = "/run/credentials/ai-crypto-signal-agent.service"
_NAME = "telegram_bot_token"
_VALUE = "opaque-reader-fixture"
_MAX_BYTES = 4096
_CODES = (
    "INVALID_CREDENTIAL_DIRECTORY",
    "INVALID_CREDENTIAL_NAME",
    "CREDENTIAL_DIRECTORY_UNAVAILABLE",
    "CREDENTIAL_MISSING",
    "CREDENTIAL_SYMLINK_REJECTED",
    "CREDENTIAL_NOT_REGULAR_FILE",
    "CREDENTIAL_PERMISSION_DENIED",
    "CREDENTIAL_READ_FAILED",
    "CREDENTIAL_INVALID_UTF8",
    "CREDENTIAL_EMPTY",
    "CREDENTIAL_MALFORMED",
    "CREDENTIAL_OVERSIZE",
)


@dataclass
class _Opener:
    payload: bytes | BaseException

    def __post_init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.read_calls = 0

    def __call__(self, credential_directory: str, credential_name: str) -> io.BytesIO:
        self.calls.append((credential_directory, credential_name))
        if isinstance(self.payload, BaseException):
            raise self.payload
        reader = io.BytesIO(self.payload)
        original_read = reader.read

        def read_once(*args: object, **kwargs: object) -> bytes:
            self.read_calls += 1
            return original_read(*args, **kwargs)

        reader.read = read_once  # type: ignore[method-assign]
        return reader


def _read(payload: bytes | BaseException) -> tuple[str, _Opener]:
    opener = _Opener(payload)
    value = read_systemd_telegram_credential(
        credential_directory=_DIRECTORY,
        file_opener=opener,
    )
    return value, opener


def _error(
    payload: bytes | BaseException,
    *,
    credential_directory: object = _DIRECTORY,
    credential_name: object = _NAME,
) -> tuple[SystemdTelegramCredentialErrorV1, _Opener]:
    opener = _Opener(payload)
    with pytest.raises(SystemdTelegramCredentialErrorV1) as caught:
        read_systemd_telegram_credential(
            credential_directory=credential_directory,  # type: ignore[arg-type]
            credential_name=credential_name,  # type: ignore[arg-type]
            file_opener=opener,
        )
    return caught.value, opener


def _assert_code(error: SystemdTelegramCredentialErrorV1, code: str) -> None:
    assert error.code == code
    assert str(error) == code
    assert repr(error) == f"SystemdTelegramCredentialErrorV1({code!r})"


def test_public_api_is_exact_and_keyword_only() -> None:
    assert hasattr(module, "SystemdTelegramCredentialErrorV1")
    assert hasattr(module, "read_systemd_telegram_credential")
    assert hasattr(module, "_open_regular_credential")
    signature = inspect.signature(read_systemd_telegram_credential)
    assert tuple(signature.parameters) == (
        "credential_directory",
        "credential_name",
        "file_opener",
    )
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in signature.parameters.values())
    assert signature.parameters["credential_name"].default == _NAME
    assert signature.parameters["file_opener"].default is module._open_regular_credential
    assert signature.return_annotation in (str, "str")


@pytest.mark.parametrize(
    "credential_directory",
    (None, 1, b"/run/credentials", "", "relative", "/run//credentials", "/run/./credentials", "/run/../credentials", "/run/credentials\x00x"),
)
def test_invalid_directory_is_rejected_before_open(credential_directory: object) -> None:
    error, opener = _error(b"unused", credential_directory=credential_directory)
    _assert_code(error, "INVALID_CREDENTIAL_DIRECTORY")
    assert opener.calls == []


def test_valid_absolute_directory_reaches_injected_opener_once() -> None:
    value, opener = _read(_VALUE.encode())
    assert value == _VALUE
    assert opener.calls == [(_DIRECTORY, _NAME)]
    assert opener.read_calls == 1


@pytest.mark.parametrize(
    "credential_name",
    (None, 1, "", "other", "/telegram_bot_token", "a/b", "a\\b", ".", "..", "a/../b", "telegram_bot_token\x00x"),
)
def test_invalid_credential_name_is_rejected_before_open(credential_name: object) -> None:
    error, opener = _error(b"unused", credential_name=credential_name)
    _assert_code(error, "INVALID_CREDENTIAL_NAME")
    assert opener.calls == []


def test_explicit_exact_credential_name_is_accepted() -> None:
    opener = _Opener(_VALUE.encode())
    assert read_systemd_telegram_credential(
        credential_directory=_DIRECTORY,
        credential_name=_NAME,
        file_opener=opener,
    ) == _VALUE
    assert opener.calls == [(_DIRECTORY, _NAME)]


def test_reader_has_no_global_cache_across_independent_calls() -> None:
    first = _Opener(b"first-fixture")
    second = _Opener(b"second-fixture")
    assert read_systemd_telegram_credential(
        credential_directory=_DIRECTORY, file_opener=first
    ) == "first-fixture"
    assert read_systemd_telegram_credential(
        credential_directory=_DIRECTORY, file_opener=second
    ) == "second-fixture"
    assert first.calls == second.calls == [(_DIRECTORY, _NAME)]


@pytest.mark.parametrize(
    ("payload", "expected"),
    (
        (b"valid-utf8", "valid-utf8"),
        (b"valid-utf8\n", "valid-utf8"),
        (b" leading-space", " leading-space"),
        (b"trailing-space ", "trailing-space "),
        (b"tab\tvalue", "tab\tvalue"),
        (b"a" * _MAX_BYTES, "a" * _MAX_BYTES),
    ),
)
def test_valid_representation_is_returned_exactly(payload: bytes, expected: str) -> None:
    value, opener = _read(payload)
    assert value == expected
    assert opener.calls == [(_DIRECTORY, _NAME)]
    assert opener.read_calls == 1


@pytest.mark.parametrize(
    ("payload", "code"),
    (
        (b"\xff", "CREDENTIAL_INVALID_UTF8"),
        (b"", "CREDENTIAL_EMPTY"),
        (b"\n", "CREDENTIAL_EMPTY"),
        (b" \t ", "CREDENTIAL_EMPTY"),
        (b"\t\t", "CREDENTIAL_EMPTY"),
        (b"\n\n", "CREDENTIAL_MALFORMED"),
        (b"embedded\nline", "CREDENTIAL_MALFORMED"),
        (b"carriage\rreturn", "CREDENTIAL_MALFORMED"),
        (b"windows\r\n", "CREDENTIAL_MALFORMED"),
        (b"nul\x00byte", "CREDENTIAL_MALFORMED"),
        (b"a" * (_MAX_BYTES + 1), "CREDENTIAL_OVERSIZE"),
    ),
)
def test_invalid_representation_is_sanitized(payload: bytes, code: str) -> None:
    error, opener = _error(payload)
    _assert_code(error, code)
    assert opener.calls == [(_DIRECTORY, _NAME)]
    assert opener.read_calls == 1
    rendered = str(error) + repr(error)
    assert _VALUE not in rendered
    assert not any(
        marker in rendered
        for marker in (
            f"length={len(payload)}",
            f"size={len(payload)}",
            f"bytes={len(payload)}",
            f"{len(payload)} byte",
            f"{len(payload)}-byte",
        )
    )


@pytest.mark.parametrize("code", _CODES)
def test_each_error_code_has_only_safe_fixed_rendering(code: str) -> None:
    error = SystemdTelegramCredentialErrorV1(code)
    _assert_code(error, code)
    rendered = str(error) + repr(error)
    for forbidden in (_DIRECTORY, _VALUE, "source-exception-detail", "telegram_bot_token_alt", "4096"):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    ("failure", "code"),
    (
        (FileNotFoundError("directory-hidden"), "CREDENTIAL_DIRECTORY_UNAVAILABLE"),
        (PermissionError("permission-hidden"), "CREDENTIAL_PERMISSION_DENIED"),
        (OSError("open-hidden"), "CREDENTIAL_READ_FAILED"),
    ),
)
def test_open_failures_are_sanitized(failure: Exception, code: str) -> None:
    error, opener = _error(failure)
    _assert_code(error, code)
    assert opener.calls == [(_DIRECTORY, _NAME)]
    assert "hidden" not in str(error) + repr(error)


def test_read_failure_is_sanitized_without_source_exception_text() -> None:
    class ReadFailure(io.BytesIO):
        def read(self, *args: object, **kwargs: object) -> bytes:
            raise OSError("read-hidden")

    calls: list[tuple[str, str]] = []

    def opener(directory: str, name: str) -> ReadFailure:
        calls.append((directory, name))
        return ReadFailure(b"unused")

    with pytest.raises(SystemdTelegramCredentialErrorV1) as caught:
        read_systemd_telegram_credential(
            credential_directory=_DIRECTORY,
            file_opener=opener,
        )
    _assert_code(caught.value, "CREDENTIAL_READ_FAILED")
    assert calls == [(_DIRECTORY, _NAME)]
    assert "read-hidden" not in str(caught.value) + repr(caught.value)


def test_base_exception_from_opener_propagates_unchanged() -> None:
    interrupt = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt) as caught:
        read_systemd_telegram_credential(
            credential_directory=_DIRECTORY,
            file_opener=lambda *_: (_ for _ in ()).throw(interrupt),
        )
    assert caught.value is interrupt


def test_symlinked_directory_and_file_are_rejected(tmp_path: Path) -> None:
    target_directory = tmp_path / "target"
    target_directory.mkdir()
    (target_directory / _NAME).write_bytes(b"safe-fixture")
    directory_link = tmp_path / "directory-link"
    directory_link.symlink_to(target_directory, target_is_directory=True)
    with pytest.raises(SystemdTelegramCredentialErrorV1) as directory_error:
        read_systemd_telegram_credential(credential_directory=str(directory_link))
    _assert_code(directory_error.value, "CREDENTIAL_SYMLINK_REJECTED")

    credential_link = target_directory / _NAME
    credential_link.unlink()
    credential_link.symlink_to(tmp_path / "other")
    with pytest.raises(SystemdTelegramCredentialErrorV1) as file_error:
        read_systemd_telegram_credential(credential_directory=str(target_directory))
    _assert_code(file_error.value, "CREDENTIAL_SYMLINK_REJECTED")


def test_non_regular_file_is_rejected_without_fifo_read(tmp_path: Path) -> None:
    directory = tmp_path / "credentials"
    directory.mkdir()
    (directory / _NAME).mkdir()
    with pytest.raises(SystemdTelegramCredentialErrorV1) as caught:
        read_systemd_telegram_credential(credential_directory=str(directory))
    _assert_code(caught.value, "CREDENTIAL_NOT_REGULAR_FILE")

    source = inspect.getsource(module)
    assert "S_ISREG" in source
    assert "S_ISFIFO" in source or "fstat" in source
    assert "O_NOFOLLOW" in source


def test_default_opener_requires_regular_file_and_no_directory_enumeration() -> None:
    source = inspect.getsource(module)
    forbidden = ("listdir", "scandir", "glob", "rglob", "walk(", "iterdir(")
    assert not any(item in source for item in forbidden)


def test_module_has_no_environment_argv_logging_sdk_or_network_surface(capsys: pytest.CaptureFixture[str]) -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not imported.intersection({"telegram", "httpx", "httpcore", "requests", "socket", "subprocess"})
    assert "environ" not in source
    assert "getenv" not in source
    assert "sys.argv" not in source
    assert "print(" not in source
    assert "logging" not in source
    assert capsys.readouterr() == ("", "")


def test_reader_uses_no_real_credential_paths() -> None:
    source = inspect.getsource(module)
    assert "/etc/credstore.encrypted" not in source
    assert "/run/credentials" not in source
    assert _VALUE not in source


def test_no_unsafe_public_runtime_surface_is_required() -> None:
    public = {name for name in module.__dict__ if not name.startswith("_")}
    forbidden = {"Bot", "HTTPXRequest", "getpass", "socket", "subprocess", "requests"}
    assert not public.intersection(forbidden)
    assert "stat" in module.__dict__ or "os" in module.__dict__
