"""Pure parser for one Phase 12 authorization-record document."""
from __future__ import annotations

from datetime import datetime, timezone
import re

from engine.phase_12_activation_mode_authorization_verifier_v1 import (
    Phase12ActivationAuthorizationRecordV1,
)


__all__ = (
    "Phase12ActivationAuthorizationRecordDocumentErrorV1",
    "parse_phase_12_activation_authorization_record_v1",
)

_ERROR_TEXT = "INVALID_AUTHORIZATION_RECORD_DOCUMENT"
_EXPECTED_KEYS = (
    "schema_version",
    "mode",
    "owner_authorization_id",
    "checkpoint_id",
    "approved_locked_commit",
    "approval_timestamp_utc",
    "expires_at_utc",
    "accepted_locked_commit",
)
_SCHEMA_VERSION = "phase12-activation-authorization-record-v1"
_ACCEPTED_MODES = frozenset(
    (
        "CREDENTIAL_VALIDATION",
        "TELEGRAM_CONNECTIVITY_VALIDATION",
        "TELEGRAM_START_VALIDATION",
        "CONTROLLED_WORKLOAD",
    )
)
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")


class Phase12ActivationAuthorizationRecordDocumentErrorV1(ValueError):
    """Fixed, sanitized error for malformed authorization-record documents."""

    def __init__(self) -> None:
        super().__init__(_ERROR_TEXT)


def _invalid_document() -> None:
    raise Phase12ActivationAuthorizationRecordDocumentErrorV1()


def _fields(document: str) -> dict[str, str]:
    if not isinstance(document, str):
        _invalid_document()
    if (
        not document.endswith("\n")
        or "\r" in document
        or "\ufeff" in document
        or any(ord(character) < 32 and character != "\n" for character in document)
    ):
        _invalid_document()
    lines = document.split("\n")
    if len(lines) != len(_EXPECTED_KEYS) + 1 or lines[-1] != "":
        _invalid_document()
    parsed: dict[str, str] = {}
    for expected, line in zip(_EXPECTED_KEYS, lines[:-1]):
        if line.count("=") != 1:
            _invalid_document()
        key, value = line.split("=")
        if key != expected or not value or value != value.strip():
            _invalid_document()
        parsed[key] = value
    return parsed


def _timestamp(value: str) -> datetime:
    if _TIMESTAMP.fullmatch(value) is None:
        _invalid_document()
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        _invalid_document()
    raise AssertionError("unreachable")


def parse_phase_12_activation_authorization_record_v1(
    *, document: str
) -> Phase12ActivationAuthorizationRecordV1:
    """Parse one strict caller-supplied authorization-record document."""

    fields = _fields(document)
    if fields["schema_version"] != _SCHEMA_VERSION:
        _invalid_document()
    if fields["mode"] not in _ACCEPTED_MODES:
        _invalid_document()
    if _IDENTIFIER.fullmatch(fields["owner_authorization_id"]) is None:
        _invalid_document()
    if _IDENTIFIER.fullmatch(fields["checkpoint_id"]) is None:
        _invalid_document()
    if _COMMIT.fullmatch(fields["approved_locked_commit"]) is None:
        _invalid_document()
    if _COMMIT.fullmatch(fields["accepted_locked_commit"]) is None:
        _invalid_document()
    approved_at = _timestamp(fields["approval_timestamp_utc"])
    expires_at = _timestamp(fields["expires_at_utc"])
    if approved_at >= expires_at:
        _invalid_document()
    return Phase12ActivationAuthorizationRecordV1(
        mode=fields["mode"],
        owner_authorization_id=fields["owner_authorization_id"],
        checkpoint_id=fields["checkpoint_id"],
        approved_locked_commit=fields["approved_locked_commit"],
        approval_timestamp_utc=approved_at,
        expires_at_utc=expires_at,
        accepted_locked_commit=fields["accepted_locked_commit"],
    )
