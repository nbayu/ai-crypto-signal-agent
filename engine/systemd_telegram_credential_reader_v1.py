"""Bounded reader for one systemd-supplied Telegram credential."""
from __future__ import annotations

import errno
import os
import stat
from typing import BinaryIO, Callable


_CREDENTIAL_NAME = "telegram_bot_token"
_MAX_RAW_BYTES = 4096
_CODES = frozenset(
    (
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
)


class SystemdTelegramCredentialErrorV1(Exception):
    """A fixed code-only credential reader failure."""

    def __init__(self, code: str) -> None:
        if code not in _CODES:
            raise ValueError("INVALID_CREDENTIAL_ERROR_CODE")
        self.code = code
        super().__init__(code)

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"SystemdTelegramCredentialErrorV1({self.code!r})"


class _DescriptorReader:
    def __init__(self, directory_fd: int, credential_fd: int) -> None:
        self._directory_fd = directory_fd
        self._credential_fd = credential_fd
        self._closed = False

    def read(self, size: int) -> bytes:
        try:
            return os.read(self._credential_fd, size)
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            os.close(self._credential_fd)
        finally:
            os.close(self._directory_fd)


def _error(code: str) -> SystemdTelegramCredentialErrorV1:
    return SystemdTelegramCredentialErrorV1(code)


def _validated_directory(value: object) -> str:
    if type(value) is not str or not value or "\x00" in value:
        raise _error("INVALID_CREDENTIAL_DIRECTORY")
    if not os.path.isabs(value) or os.path.normpath(value) != value:
        raise _error("INVALID_CREDENTIAL_DIRECTORY")
    if any(component in (".", "..") for component in value.split("/")):
        raise _error("INVALID_CREDENTIAL_DIRECTORY")
    return value


def _validated_name(value: object) -> str:
    if type(value) is not str or value != _CREDENTIAL_NAME:
        raise _error("INVALID_CREDENTIAL_NAME")
    if "\x00" in value or "/" in value or "\\" in value or value in (".", ".."):
        raise _error("INVALID_CREDENTIAL_NAME")
    return value


def _directory_fd(credential_directory: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    current = os.open("/", flags)
    try:
        for component in credential_directory.split("/")[1:]:
            try:
                metadata = os.stat(component, dir_fd=current, follow_symlinks=False)
            except FileNotFoundError as error:
                raise _error("CREDENTIAL_DIRECTORY_UNAVAILABLE") from None
            except PermissionError:
                raise _error("CREDENTIAL_DIRECTORY_UNAVAILABLE") from None
            except OSError:
                raise _error("CREDENTIAL_DIRECTORY_UNAVAILABLE") from None
            if stat.S_ISLNK(metadata.st_mode):
                raise _error("CREDENTIAL_SYMLINK_REJECTED")
            if not stat.S_ISDIR(metadata.st_mode):
                raise _error("CREDENTIAL_DIRECTORY_UNAVAILABLE")
            try:
                next_fd = os.open(component, flags, dir_fd=current)
            except OSError as error:
                if error.errno == errno.ELOOP:
                    raise _error("CREDENTIAL_SYMLINK_REJECTED") from None
                raise _error("CREDENTIAL_DIRECTORY_UNAVAILABLE") from None
            os.close(current)
            current = next_fd
        return current
    except BaseException:
        os.close(current)
        raise


def _open_regular_credential(
    credential_directory: str,
    credential_name: str,
) -> BinaryIO:
    directory_fd = _directory_fd(credential_directory)
    try:
        try:
            metadata = os.stat(
                credential_name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            raise _error("CREDENTIAL_MISSING") from None
        except PermissionError:
            raise _error("CREDENTIAL_PERMISSION_DENIED") from None
        except OSError:
            raise _error("CREDENTIAL_READ_FAILED") from None
        if stat.S_ISLNK(metadata.st_mode):
            raise _error("CREDENTIAL_SYMLINK_REJECTED")
        if not stat.S_ISREG(metadata.st_mode):
            raise _error("CREDENTIAL_NOT_REGULAR_FILE")
        try:
            credential_fd = os.open(
                credential_name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
        except FileNotFoundError:
            raise _error("CREDENTIAL_MISSING") from None
        except PermissionError:
            raise _error("CREDENTIAL_PERMISSION_DENIED") from None
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise _error("CREDENTIAL_SYMLINK_REJECTED") from None
            raise _error("CREDENTIAL_READ_FAILED") from None
        try:
            if not stat.S_ISREG(os.fstat(credential_fd).st_mode):
                raise _error("CREDENTIAL_NOT_REGULAR_FILE")
            return _DescriptorReader(directory_fd, credential_fd)  # type: ignore[return-value]
        except BaseException:
            os.close(credential_fd)
            raise
    except BaseException:
        os.close(directory_fd)
        raise


def _read_once(reader: object) -> bytes:
    try:
        value = reader.read(_MAX_RAW_BYTES + 1)  # type: ignore[attr-defined]
    except Exception:
        raise _error("CREDENTIAL_READ_FAILED") from None
    finally:
        close = getattr(reader, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
    if not isinstance(value, bytes):
        raise _error("CREDENTIAL_READ_FAILED")
    return value


def _normalised_value(raw: bytes) -> str:
    if len(raw) > _MAX_RAW_BYTES:
        raise _error("CREDENTIAL_OVERSIZE")
    try:
        value = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise _error("CREDENTIAL_INVALID_UTF8") from None
    if value.endswith("\r\n") or "\r" in value or "\x00" in value:
        raise _error("CREDENTIAL_MALFORMED")
    if value.endswith("\n"):
        value = value[:-1]
    if "\n" in value:
        raise _error("CREDENTIAL_MALFORMED")
    if not value or value.isspace():
        raise _error("CREDENTIAL_EMPTY")
    return value


def read_systemd_telegram_credential(
    *,
    credential_directory: str,
    credential_name: str = _CREDENTIAL_NAME,
    file_opener: Callable[[str, str], BinaryIO] = _open_regular_credential,
) -> str:
    """Read and validate one credential through a caller-provided opener."""
    directory = _validated_directory(credential_directory)
    name = _validated_name(credential_name)
    if not callable(file_opener):
        raise _error("CREDENTIAL_READ_FAILED")
    try:
        reader = file_opener(directory, name)
    except SystemdTelegramCredentialErrorV1:
        raise
    except FileNotFoundError:
        raise _error("CREDENTIAL_DIRECTORY_UNAVAILABLE") from None
    except PermissionError:
        raise _error("CREDENTIAL_PERMISSION_DENIED") from None
    except Exception:
        raise _error("CREDENTIAL_READ_FAILED") from None
    return _normalised_value(_read_once(reader))
