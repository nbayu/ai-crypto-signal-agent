"""RED contract for the Phase 12 non-secret activation configuration seam."""
from __future__ import annotations

import ast
import inspect
import io
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime, timedelta, timezone

import pytest

import engine.phase_12_activation_configuration_v1 as module
from engine.phase_12_activation_configuration_v1 import (
    Phase12ActivationConfigurationErrorV1,
    Phase12ActivationConfigurationV1,
    load_phase_12_activation_configuration,
    main,
)


_PATH = "/etc/ai-crypto-signal-agent/phase12-activation-v1.conf"
_NOW = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)
_FIELDS = (
    "schema_version",
    "activation_mode",
    "owner_authorization_id",
    "approval_checkpoint_id",
    "approved_locked_commit",
    "approved_at",
    "expires_at",
    "activation_gate_open",
    "credential_gate_open",
    "network_gate_open",
    "workload_gate_open",
    "telegram_start_authorized",
)
_CLOSED = (
    "schema_version=phase12-activation-v1\n"
    "activation_mode=CLOSED\n"
    "owner_authorization_id=NONE\n"
    "approval_checkpoint_id=NONE\n"
    "approved_locked_commit=NONE\n"
    "approved_at=NONE\n"
    "expires_at=NONE\n"
)
_COMMIT = "a" * 40
_MODE_GATES = {
    "CLOSED": (False, False, False, False, False),
    "CREDENTIAL_VALIDATION": (True, True, False, False, False),
    "TELEGRAM_CONNECTIVITY_VALIDATION": (True, True, True, False, False),
    "TELEGRAM_START_VALIDATION": (True, True, True, False, True),
    "CONTROLLED_WORKLOAD": (True, True, True, True, True),
}
_LIFETIMES = {
    "CREDENTIAL_VALIDATION": timedelta(minutes=15),
    "TELEGRAM_CONNECTIVITY_VALIDATION": timedelta(minutes=15),
    "TELEGRAM_START_VALIDATION": timedelta(minutes=10),
    "CONTROLLED_WORKLOAD": timedelta(minutes=5),
}


class _Reader(io.BytesIO):
    def __init__(self, payload: bytes | BaseException) -> None:
        super().__init__(b"" if isinstance(payload, BaseException) else payload)
        self.payload = payload
        self.read_calls = 0
        self.closed_once = False

    def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if isinstance(self.payload, BaseException):
            raise self.payload
        return super().read(size)

    def close(self) -> None:
        self.closed_once = True
        super().close()


class _Opener:
    def __init__(self, payload: bytes | BaseException) -> None:
        self.payload = payload
        self.calls: list[str] = []
        self.reader: _Reader | None = None

    def __call__(self, path: str) -> _Reader:
        self.calls.append(path)
        self.reader = _Reader(self.payload)
        return self.reader


class _Interrupt(BaseException):
    pass


def _non_closed(mode: str, *, approved_at: datetime = _NOW, expires_at: datetime | None = None) -> str:
    if expires_at is None:
        expires_at = approved_at + _LIFETIMES[mode]
    return (
        "schema_version=phase12-activation-v1\n"
        f"activation_mode={mode}\n"
        "owner_authorization_id=owner-authorization-v1\n"
        "approval_checkpoint_id=checkpoint-v1\n"
        f"approved_locked_commit={_COMMIT}\n"
        f"approved_at={approved_at.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        f"expires_at={expires_at.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
    )


def _load(text: str, *, now: datetime = _NOW, opener: _Opener | None = None):
    selected = opener or _Opener(text.encode("utf-8"))
    result = load_phase_12_activation_configuration(
        configuration_path=_PATH,
        now_utc=now,
        file_opener=selected,
    )
    return result, selected


def _assert_error(text: str | bytes | BaseException, *, now: datetime = _NOW) -> None:
    payload = text if isinstance(text, (bytes, BaseException)) else text.encode("utf-8")
    opener = _Opener(payload)
    with pytest.raises(Phase12ActivationConfigurationErrorV1) as raised:
        _load(_CLOSED, now=now, opener=opener)
    rendered = str(raised.value) + repr(raised.value)
    assert isinstance(getattr(raised.value, "code", None), str)
    assert rendered == str(raised.value) + repr(raised.value)
    for value in (_PATH, "owner-authorization-v1", "checkpoint-v1", _COMMIT, "2026-07-22"):
        assert value not in rendered


def _replace(text: str, old: str, new: str) -> str:
    assert old in text
    return text.replace(old, new, 1)


def test_public_surface_and_immutable_model_are_exact() -> None:
    assert all(
        hasattr(module, name)
        for name in (
            "Phase12ActivationConfigurationV1",
            "Phase12ActivationConfigurationErrorV1",
            "load_phase_12_activation_configuration",
            "main",
        )
    )
    assert is_dataclass(Phase12ActivationConfigurationV1)
    assert Phase12ActivationConfigurationV1.__dataclass_params__.frozen is True
    assert "__dict__" not in Phase12ActivationConfigurationV1.__slots__
    assert tuple(field.name for field in fields(Phase12ActivationConfigurationV1)) == _FIELDS
    assert "launcher_implementation_authorized" not in _FIELDS
    result, _ = _load(_CLOSED)
    assert result == result
    with pytest.raises(FrozenInstanceError):
        result.activation_mode = "CONTROLLED_WORKLOAD"  # type: ignore[misc]


def test_closed_file_is_exact_and_derives_all_closed_gates() -> None:
    result, opener = _load(_CLOSED)
    assert opener.calls == [_PATH]
    assert opener.reader is not None and opener.reader.read_calls == 1
    assert result.schema_version == "phase12-activation-v1"
    assert result.activation_mode == "CLOSED"
    assert (
        result.owner_authorization_id,
        result.approval_checkpoint_id,
        result.approved_locked_commit,
        result.approved_at,
        result.expires_at,
    ) == ("NONE", "NONE", "NONE", "NONE", "NONE")
    assert (
        result.activation_gate_open,
        result.credential_gate_open,
        result.network_gate_open,
        result.workload_gate_open,
        result.telegram_start_authorized,
    ) == _MODE_GATES["CLOSED"]


@pytest.mark.parametrize("mode, expected", tuple(_MODE_GATES.items()))
def test_each_exact_mode_derives_the_frozen_gate_mapping(mode: str, expected: tuple[bool, ...]) -> None:
    text = _CLOSED if mode == "CLOSED" else _non_closed(mode)
    result, _ = _load(text)
    assert result.activation_mode == mode
    assert (
        result.activation_gate_open,
        result.credential_gate_open,
        result.network_gate_open,
        result.workload_gate_open,
        result.telegram_start_authorized,
    ) == expected


@pytest.mark.parametrize("mode", ("PRODUCTION", "closed", "Closed", "", "OTHER"))
def test_only_the_exact_mode_enumeration_is_accepted(mode: str) -> None:
    _assert_error(_replace(_CLOSED, "activation_mode=CLOSED", f"activation_mode={mode}"))


@pytest.mark.parametrize(
    "text",
    (
        _CLOSED.rstrip("\n"),
        _CLOSED + "\n",
        _CLOSED.replace("approval_checkpoint_id=NONE\n", "\napproval_checkpoint_id=NONE\n"),
        _CLOSED + "# comment\n",
        _CLOSED.replace("schema_version=", " schema_version="),
        _CLOSED.replace("schema_version=phase12-activation-v1", "schema_version=phase12-activation-v1 "),
        _CLOSED.replace("schema_version=", "schema_version ="),
        _CLOSED.replace("schema_version=phase12-activation-v1\n", "activation_mode=CLOSED\nschema_version=phase12-activation-v1\n"),
        _CLOSED.replace("expires_at=NONE\n", ""),
        _CLOSED + "expires_at=NONE\n",
        _CLOSED + "unknown_key=NONE\n",
        _CLOSED.replace("schema_version", "Schema_version"),
        _CLOSED + "extra=NONE\n",
        _CLOSED.replace("owner_authorization_id=NONE", "owner_authorization_id="),
        _CLOSED.replace("owner_authorization_id=NONE", "owner_authorization_id=${VALUE}"),
        _CLOSED.replace("owner_authorization_id=NONE", "owner_authorization_id=$VALUE"),
    ),
)
def test_file_format_is_exactly_seven_ordered_nonblank_lines(text: str) -> None:
    _assert_error(text)


@pytest.mark.parametrize(
    "version",
    ("phase12-activation-v2", "PHASE12-ACTIVATION-V1", " phase12-activation-v1", "", "phase12-activation-v1 "),
)
def test_schema_version_is_exact(version: str) -> None:
    _assert_error(_replace(_CLOSED, "schema_version=phase12-activation-v1", f"schema_version={version}"))


@pytest.mark.parametrize(
    "key",
    ("owner_authorization_id", "approval_checkpoint_id", "approved_locked_commit", "approved_at", "expires_at"),
)
def test_closed_mode_requires_every_evidence_sentinel_to_be_exactly_none(key: str) -> None:
    _assert_error(_replace(_CLOSED, f"{key}=NONE", f"{key}=not-none"))


@pytest.mark.parametrize(
    "key, value",
    (
        ("owner_authorization_id", "Owner-v1"),
        ("owner_authorization_id", "owner_v1"),
        ("owner_authorization_id", " owner-v1"),
        ("owner_authorization_id", "-owner-v1"),
        ("owner_authorization_id", "owner-v1!"),
        ("owner_authorization_id", "a" * 65),
        ("owner_authorization_id", "NONE"),
        ("approval_checkpoint_id", "checkpoint_v1"),
        ("approval_checkpoint_id", "NONE"),
        ("approved_locked_commit", "A" * 40),
        ("approved_locked_commit", "a" * 39),
        ("approved_locked_commit", "a" * 41),
        ("approved_locked_commit", "g" * 40),
        ("approved_locked_commit", "NONE"),
    ),
)
def test_non_closed_evidence_identifiers_are_strict(key: str, value: str) -> None:
    _assert_error(_replace(_non_closed("CREDENTIAL_VALIDATION"), f"{key}=" + (_COMMIT if key == "approved_locked_commit" else "owner-authorization-v1" if key == "owner_authorization_id" else "checkpoint-v1"), f"{key}={value}"))


@pytest.mark.parametrize(
    "key, value",
    (
        ("approved_at", "2026-07-22T12:00:00.000Z"),
        ("approved_at", "2026-07-22T12:00:00+00:00"),
        ("approved_at", "2026-07-22T12:00:00z"),
        ("approved_at", "2026-07-22T12:00:00"),
        ("approved_at", "2026-02-30T12:00:00Z"),
        ("approved_at", " NONE"),
        ("expires_at", "NONE"),
    ),
)
def test_non_closed_timestamps_are_strict_utc_seconds(key: str, value: str) -> None:
    original = "2026-07-22T12:00:00Z" if key == "approved_at" else "2026-07-22T12:15:00Z"
    _assert_error(_replace(_non_closed("CREDENTIAL_VALIDATION"), f"{key}={original}", f"{key}={value}"))


@pytest.mark.parametrize("mode, lifetime", tuple(_LIFETIMES.items()))
def test_exact_maximum_lifetime_is_accepted_and_one_second_over_is_rejected(mode: str, lifetime: timedelta) -> None:
    approved = _NOW - timedelta(seconds=1)
    accepted, _ = _load(_non_closed(mode, approved_at=approved, expires_at=approved + lifetime))
    assert accepted.activation_mode == mode
    _assert_error(_non_closed(mode, approved_at=approved, expires_at=approved + lifetime + timedelta(seconds=1)))


@pytest.mark.parametrize(
    "approved, expires, now",
    (
        (_NOW + timedelta(seconds=1), _NOW + timedelta(minutes=2), _NOW),
        (_NOW, _NOW, _NOW),
        (_NOW, _NOW - timedelta(seconds=1), _NOW),
        (_NOW - timedelta(minutes=2), _NOW, _NOW),
    ),
)
def test_future_and_expiration_boundaries_fail_closed(approved: datetime, expires: datetime, now: datetime) -> None:
    _assert_error(_non_closed("CREDENTIAL_VALIDATION", approved_at=approved, expires_at=expires), now=now)


def test_now_must_be_timezone_aware_utc() -> None:
    _assert_error(_non_closed("CREDENTIAL_VALIDATION"), now=datetime(2026, 7, 22, 12, 0, 0))
    _assert_error(_non_closed("CREDENTIAL_VALIDATION"), now=_NOW.astimezone(timezone(timedelta(hours=1))))


def test_reader_is_single_read_bounded_and_has_no_retry_after_ordinary_failure() -> None:
    accepted = _Opener(_CLOSED.encode("utf-8"))
    _load(_CLOSED, opener=accepted)
    assert accepted.calls == [_PATH]
    assert accepted.reader is not None and accepted.reader.read_calls == 1
    assert accepted.reader.closed_once
    _assert_error(b"x" * 4097)
    failed = _Opener(OSError("dynamic read detail"))
    with pytest.raises(Phase12ActivationConfigurationErrorV1) as raised:
        _load(_CLOSED, opener=failed)
    assert "dynamic read detail" not in str(raised.value) + repr(raised.value)
    assert failed.calls == [_PATH]
    assert failed.reader is not None and failed.reader.read_calls == 1


def test_invalid_utf8_and_baseexception_contracts_are_distinct() -> None:
    _assert_error(b"\xff")
    interrupted = _Opener(_Interrupt())
    with pytest.raises(_Interrupt):
        _load(_CLOSED, opener=interrupted)
    assert interrupted.calls == [_PATH]
    assert interrupted.reader is not None and interrupted.reader.read_calls == 1


def test_filesystem_safety_contract_is_present_without_real_privileged_files() -> None:
    source = inspect.getsource(module)
    required = (
        "_open_regular_configuration",
        "O_NOFOLLOW",
        "O_CLOEXEC",
        "fstat",
        "S_ISREG",
        "st_nlink",
        "st_uid",
        "st_gid",
        "0o640",
        "0o750",
        "ai-crypto-signal-agent",
    )
    assert all(marker in source for marker in required)
    assert not any(marker in source for marker in ("listdir", "scandir", "glob", "rglob", "walk(", "iterdir("))


def test_all_ordinary_defects_are_sanitized_and_never_return_partial_configuration() -> None:
    for payload in (_CLOSED.rstrip("\n"), b"\xff", OSError("path=/private/detail")):
        _assert_error(payload)


def test_module_has_no_side_effect_or_credential_runtime_surface() -> None:
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
    assert not imported.intersection({"logging", "requests", "httpx", "socket", "subprocess", "telegram"})
    forbidden = (
        "systemctl",
        "read_systemd_telegram_credential",
        "CREDENTIALS_DIRECTORY",
        "os.environ",
        "getenv",
        "cache",
        "print(",
    )
    assert not any(value in source for value in forbidden)
    assert not any(isinstance(node, ast.Global) for node in ast.walk(tree))


def test_parser_only_main_has_fixed_outputs_and_strict_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    valid, _ = _load(_CLOSED)
    monkeypatch.setattr(module, "load_phase_12_activation_configuration", lambda **_: valid)
    assert main(["--check", "--configuration-path", _PATH]) == 0
    assert capsys.readouterr() == ('{"activation_configuration_result":"VALID"}\n', "")

    def rejected(**_: object):
        raise Phase12ActivationConfigurationErrorV1("CONFIGURATION_FORMAT_INVALID")

    monkeypatch.setattr(module, "load_phase_12_activation_configuration", rejected)
    assert main(["--check", "--configuration-path", _PATH]) == 1
    assert capsys.readouterr() == ('{"activation_configuration_result":"FAILURE"}\n', "")

    monkeypatch.setattr(module, "load_phase_12_activation_configuration", lambda **_: (_ for _ in ()).throw(RuntimeError("dynamic")))
    assert main(["--check", "--configuration-path", _PATH]) == 70
    assert capsys.readouterr() == ('{"activation_configuration_result":"UNEXPECTED_FAILURE"}\n', "")

    for argv in (
        [],
        ["--configuration-path", _PATH],
        ["--check", "--unknown"],
        ["--check", "--configuration-path", _PATH, "--configuration-path", _PATH],
        ["--check", "--configuration-path", _PATH, "positional"],
    ):
        assert main(argv) == 2
        rendered = capsys.readouterr()
        assert rendered.err == ""
        assert rendered.out == '{"activation_configuration_result":"FAILURE"}\n'
