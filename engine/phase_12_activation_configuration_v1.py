"""Fail-closed reader for the non-secret Phase 12 activation configuration."""
from __future__ import annotations

import errno
import grp
import os
import re
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import BinaryIO, Callable


_MAX_BYTES = 4096
_EXPECTED_GROUP = "ai-crypto-signal-agent"
_EXPECTED_KEYS = (
    "schema_version",
    "activation_mode",
    "owner_authorization_id",
    "approval_checkpoint_id",
    "approved_locked_commit",
    "approved_at",
    "expires_at",
)
_SCHEMA_VERSION = "phase12-activation-v1"
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_GATES = {
    "CLOSED": (False, False, False, False, False),
    "CREDENTIAL_VALIDATION": (True, True, False, False, False),
    "TELEGRAM_CONNECTIVITY_VALIDATION": (True, True, True, False, False),
    "TELEGRAM_START_VALIDATION": (True, True, True, False, True),
    "CONTROLLED_WORKLOAD": (True, True, True, True, True),
    "STAGE_A_OBSERVE": (True, False, False, False, False),
    "STAGE_B_ADVISORY": (True, False, False, False, False),
    "STAGE_C_CAUTION_HOLD": (True, False, False, False, False),
}
_LIFETIMES = {
    "CREDENTIAL_VALIDATION": timedelta(minutes=15),
    "TELEGRAM_CONNECTIVITY_VALIDATION": timedelta(minutes=15),
    "TELEGRAM_START_VALIDATION": timedelta(minutes=10),
    "CONTROLLED_WORKLOAD": timedelta(minutes=5),
    "STAGE_A_OBSERVE": timedelta(hours=24),
    "STAGE_B_ADVISORY": timedelta(hours=24),
    "STAGE_C_CAUTION_HOLD": timedelta(hours=24),
}
_CODES = frozenset(
    (
        "CONFIGURATION_PATH_INVALID",
        "CONFIGURATION_MISSING",
        "CONFIGURATION_INACCESSIBLE",
        "CONFIGURATION_SYMLINK_REJECTED",
        "CONFIGURATION_NOT_REGULAR",
        "CONFIGURATION_LINK_COUNT_INVALID",
        "CONFIGURATION_OWNER_INVALID",
        "CONFIGURATION_GROUP_INVALID",
        "CONFIGURATION_MODE_INVALID",
        "CONFIGURATION_PARENT_INVALID",
        "CONFIGURATION_READ_FAILED",
        "CONFIGURATION_OVERSIZE",
        "CONFIGURATION_INVALID_UTF8",
        "CONFIGURATION_FORMAT_INVALID",
        "CONFIGURATION_SCHEMA_INVALID",
        "CONFIGURATION_MODE_INVALID_VALUE",
        "CONFIGURATION_EVIDENCE_INVALID",
        "CONFIGURATION_TIMESTAMP_INVALID",
        "CONFIGURATION_NOW_UTC_INVALID",
        "CONFIGURATION_TIME_ORDER_INVALID",
        "CONFIGURATION_EXPIRED",
        "CONFIGURATION_LIFETIME_INVALID",
        "CONFIGURATION_INVARIANT_INVALID",
    )
)


@dataclass(frozen=True, slots=True)
class Phase12ActivationConfigurationV1:
    schema_version: str
    activation_mode: str
    owner_authorization_id: str
    approval_checkpoint_id: str
    approved_locked_commit: str
    approved_at: str
    expires_at: str
    activation_gate_open: bool
    credential_gate_open: bool
    network_gate_open: bool
    workload_gate_open: bool
    telegram_start_authorized: bool


class Phase12ActivationConfigurationErrorV1(Exception):
    """Fixed-code configuration failure that never includes input material."""

    def __init__(self, code: str) -> None:
        if code not in _CODES:
            raise ValueError("INVALID_CONFIGURATION_ERROR_CODE")
        self.code = code
        super().__init__(code)

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"Phase12ActivationConfigurationErrorV1({self.code!r})"


class _DescriptorReader:
    def __init__(self, directory_fd: int, configuration_fd: int) -> None:
        self._directory_fd = directory_fd
        self._configuration_fd = configuration_fd
        self._closed = False

    def read(self, size: int) -> bytes:
        try:
            return os.read(self._configuration_fd, size)
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            os.close(self._configuration_fd)
        finally:
            os.close(self._directory_fd)


def _error(code: str) -> Phase12ActivationConfigurationErrorV1:
    return Phase12ActivationConfigurationErrorV1(code)


def _configuration_parts(value: object) -> tuple[str, ...]:
    if type(value) is not str or not value or "\x00" in value:
        raise _error("CONFIGURATION_PATH_INVALID")
    if not os.path.isabs(value) or os.path.normpath(value) != value or value == "/":
        raise _error("CONFIGURATION_PATH_INVALID")
    parts = tuple(value.split("/")[1:])
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise _error("CONFIGURATION_PATH_INVALID")
    return parts


def _expected_gid() -> int:
    try:
        return grp.getgrnam(_EXPECTED_GROUP).gr_gid
    except KeyError:
        raise _error("CONFIGURATION_GROUP_INVALID") from None


def _open_parent(parts: tuple[str, ...]) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    current = os.open("/", flags)
    try:
        for part in parts:
            try:
                metadata = os.stat(part, dir_fd=current, follow_symlinks=False)
            except FileNotFoundError:
                raise _error("CONFIGURATION_MISSING") from None
            except PermissionError:
                raise _error("CONFIGURATION_INACCESSIBLE") from None
            except OSError:
                raise _error("CONFIGURATION_INACCESSIBLE") from None
            if stat.S_ISLNK(metadata.st_mode):
                raise _error("CONFIGURATION_SYMLINK_REJECTED")
            if not stat.S_ISDIR(metadata.st_mode):
                raise _error("CONFIGURATION_PARENT_INVALID")
            try:
                next_fd = os.open(part, flags, dir_fd=current)
            except OSError as exc:
                if exc.errno == errno.ELOOP:
                    raise _error("CONFIGURATION_SYMLINK_REJECTED") from None
                raise _error("CONFIGURATION_INACCESSIBLE") from None
            os.close(current)
            current = next_fd
        return current
    except BaseException:
        os.close(current)
        raise


def _metadata_is_expected(metadata: os.stat_result, *, parent: bool) -> bool:
    expected_mode = 0o750 if parent else 0o640
    if metadata.st_uid != 0 or metadata.st_gid != _expected_gid():
        return False
    return stat.S_IMODE(metadata.st_mode) == expected_mode


def _open_regular_configuration(configuration_path: str) -> BinaryIO:
    """Open the configured file through verified, no-follow descriptors."""

    parts = _configuration_parts(configuration_path)
    directory_fd = _open_parent(parts[:-1])
    try:
        try:
            parent_metadata = os.fstat(directory_fd)
        except OSError:
            raise _error("CONFIGURATION_PARENT_INVALID") from None
        if not _metadata_is_expected(parent_metadata, parent=True):
            raise _error("CONFIGURATION_PARENT_INVALID")
        name = parts[-1]
        try:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            raise _error("CONFIGURATION_MISSING") from None
        except PermissionError:
            raise _error("CONFIGURATION_INACCESSIBLE") from None
        except OSError:
            raise _error("CONFIGURATION_READ_FAILED") from None
        if stat.S_ISLNK(metadata.st_mode):
            raise _error("CONFIGURATION_SYMLINK_REJECTED")
        if not stat.S_ISREG(metadata.st_mode):
            raise _error("CONFIGURATION_NOT_REGULAR")
        if metadata.st_nlink != 1:
            raise _error("CONFIGURATION_LINK_COUNT_INVALID")
        if metadata.st_uid != 0:
            raise _error("CONFIGURATION_OWNER_INVALID")
        if metadata.st_gid != _expected_gid():
            raise _error("CONFIGURATION_GROUP_INVALID")
        if stat.S_IMODE(metadata.st_mode) != 0o640:
            raise _error("CONFIGURATION_MODE_INVALID")
        try:
            configuration_fd = os.open(
                name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
        except FileNotFoundError:
            raise _error("CONFIGURATION_MISSING") from None
        except PermissionError:
            raise _error("CONFIGURATION_INACCESSIBLE") from None
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise _error("CONFIGURATION_SYMLINK_REJECTED") from None
            raise _error("CONFIGURATION_READ_FAILED") from None
        try:
            opened = os.fstat(configuration_fd)
            if not stat.S_ISREG(opened.st_mode):
                raise _error("CONFIGURATION_NOT_REGULAR")
            if opened.st_nlink != 1:
                raise _error("CONFIGURATION_LINK_COUNT_INVALID")
            if opened.st_uid != 0:
                raise _error("CONFIGURATION_OWNER_INVALID")
            if opened.st_gid != _expected_gid():
                raise _error("CONFIGURATION_GROUP_INVALID")
            if stat.S_IMODE(opened.st_mode) != 0o640:
                raise _error("CONFIGURATION_MODE_INVALID")
            return _DescriptorReader(directory_fd, configuration_fd)  # type: ignore[return-value]
        except BaseException:
            os.close(configuration_fd)
            raise
    except BaseException:
        os.close(directory_fd)
        raise


def _read_once(reader: object) -> bytes:
    try:
        value = reader.read(_MAX_BYTES + 1)  # type: ignore[attr-defined]
    except Exception:
        raise _error("CONFIGURATION_READ_FAILED") from None
    finally:
        close = getattr(reader, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
    if not isinstance(value, bytes):
        raise _error("CONFIGURATION_READ_FAILED")
    if len(value) > _MAX_BYTES:
        raise _error("CONFIGURATION_OVERSIZE")
    return value


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise _error("CONFIGURATION_INVALID_UTF8") from None


def _parse_lines(value: str) -> dict[str, str]:
    if not value.endswith("\n") or value.endswith("\n\n") or "\r" in value:
        raise _error("CONFIGURATION_FORMAT_INVALID")
    lines = value[:-1].split("\n")
    if len(lines) != len(_EXPECTED_KEYS):
        raise _error("CONFIGURATION_FORMAT_INVALID")
    parsed: dict[str, str] = {}
    for expected, line in zip(_EXPECTED_KEYS, lines):
        prefix = expected + "="
        if not line.startswith(prefix):
            raise _error("CONFIGURATION_FORMAT_INVALID")
        item = line[len(prefix) :]
        if not item or item != item.strip() or "$" in item or "{" in item or "}" in item:
            raise _error("CONFIGURATION_FORMAT_INVALID")
        parsed[expected] = item
    return parsed


def _utc_timestamp(value: str) -> datetime:
    if _TIMESTAMP.fullmatch(value) is None:
        raise _error("CONFIGURATION_TIMESTAMP_INVALID")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise _error("CONFIGURATION_TIMESTAMP_INVALID") from None


def _valid_now(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise _error("CONFIGURATION_NOW_UTC_INVALID")
    return value


def _validate_invariants(gates: tuple[bool, bool, bool, bool, bool]) -> None:
    activation, credential, network, workload, telegram_start = gates
    if credential and not activation:
        raise _error("CONFIGURATION_INVARIANT_INVALID")
    if network and not (activation and credential):
        raise _error("CONFIGURATION_INVARIANT_INVALID")
    if telegram_start and not (activation and credential and network):
        raise _error("CONFIGURATION_INVARIANT_INVALID")
    if workload and not (activation and credential and network and telegram_start):
        raise _error("CONFIGURATION_INVARIANT_INVALID")


def _configuration_from_text(value: str, *, now_utc: datetime) -> Phase12ActivationConfigurationV1:
    parsed = _parse_lines(value)
    if parsed["schema_version"] != _SCHEMA_VERSION:
        raise _error("CONFIGURATION_SCHEMA_INVALID")
    mode = parsed["activation_mode"]
    gates = _GATES.get(mode)
    if gates is None:
        raise _error("CONFIGURATION_MODE_INVALID_VALUE")
    evidence = tuple(parsed[key] for key in _EXPECTED_KEYS[2:])
    if mode == "CLOSED":
        if evidence != ("NONE",) * 5:
            raise _error("CONFIGURATION_EVIDENCE_INVALID")
    else:
        owner, checkpoint, commit, approved_text, expires_text = evidence
        if _IDENTIFIER.fullmatch(owner) is None or _IDENTIFIER.fullmatch(checkpoint) is None:
            raise _error("CONFIGURATION_EVIDENCE_INVALID")
        if _COMMIT.fullmatch(commit) is None:
            raise _error("CONFIGURATION_EVIDENCE_INVALID")
        approved = _utc_timestamp(approved_text)
        expires = _utc_timestamp(expires_text)
        current = _valid_now(now_utc)
        if approved > current or expires <= approved:
            raise _error("CONFIGURATION_TIME_ORDER_INVALID")
        if expires <= current:
            raise _error("CONFIGURATION_EXPIRED")
        if expires - approved > _LIFETIMES[mode]:
            raise _error("CONFIGURATION_LIFETIME_INVALID")
    _validate_invariants(gates)
    return Phase12ActivationConfigurationV1(
        schema_version=parsed["schema_version"],
        activation_mode=mode,
        owner_authorization_id=parsed["owner_authorization_id"],
        approval_checkpoint_id=parsed["approval_checkpoint_id"],
        approved_locked_commit=parsed["approved_locked_commit"],
        approved_at=parsed["approved_at"],
        expires_at=parsed["expires_at"],
        activation_gate_open=gates[0],
        credential_gate_open=gates[1],
        network_gate_open=gates[2],
        workload_gate_open=gates[3],
        telegram_start_authorized=gates[4],
    )


def load_phase_12_activation_configuration(
    *,
    configuration_path: str,
    now_utc: datetime,
    file_opener: Callable[[str], BinaryIO] = _open_regular_configuration,
) -> Phase12ActivationConfigurationV1:
    """Load one complete configuration or raise a fixed safe error."""

    if not callable(file_opener):
        raise _error("CONFIGURATION_READ_FAILED")
    _valid_now(now_utc)
    try:
        reader = file_opener(configuration_path)
    except Phase12ActivationConfigurationErrorV1:
        raise
    except FileNotFoundError:
        raise _error("CONFIGURATION_MISSING") from None
    except PermissionError:
        raise _error("CONFIGURATION_INACCESSIBLE") from None
    except Exception:
        raise _error("CONFIGURATION_READ_FAILED") from None
    return _configuration_from_text(_decode(_read_once(reader)), now_utc=now_utc)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _write_result(value: str) -> None:
    sys.stdout.write('{"activation_configuration_result":"' + value + '"}\n')


def main(argv: list[str] | None = None) -> int:
    """Validate only the supplied configuration; no runtime is invoked."""

    values = sys.argv[1:] if argv is None else argv
    if (
        not isinstance(values, list)
        or len(values) != 3
        or values[0] != "--check"
        or values[1] != "--configuration-path"
        or not isinstance(values[2], str)
        or not values[2]
    ):
        _write_result("FAILURE")
        return 2
    try:
        load_phase_12_activation_configuration(
            configuration_path=values[2],
            now_utc=_now_utc(),
        )
    except Phase12ActivationConfigurationErrorV1:
        _write_result("FAILURE")
        return 1
    except Exception:
        _write_result("UNEXPECTED_FAILURE")
        return 70
    _write_result("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
