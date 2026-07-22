"""Pure parser for one Phase 12 accepted-locked-commit marker document."""
from __future__ import annotations

from dataclasses import dataclass
import re


__all__ = (
    "Phase12ActivationAcceptedLockedCommitMarkerV1",
    "Phase12ActivationAcceptedLockedCommitMarkerDocumentErrorV1",
    "parse_phase_12_activation_accepted_locked_commit_marker_v1",
)


_ERROR_TEXT = "INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_DOCUMENT"
_EXPECTED_KEYS = (
    "schema_version",
    "accepted_locked_commit",
)
_SCHEMA_VERSION = "phase12-activation-accepted-locked-commit-marker-v1"
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


@dataclass(frozen=True, slots=True, kw_only=True)
class Phase12ActivationAcceptedLockedCommitMarkerV1:
    """One immutable marker value without source or authorization semantics."""

    schema_version: str
    accepted_locked_commit: str

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerV1()"


class Phase12ActivationAcceptedLockedCommitMarkerDocumentErrorV1(ValueError):
    """Fixed, sanitized error for malformed accepted-commit marker documents."""

    def __init__(self) -> None:
        super().__init__(_ERROR_TEXT)


def _invalid_document() -> None:
    raise Phase12ActivationAcceptedLockedCommitMarkerDocumentErrorV1()


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


def parse_phase_12_activation_accepted_locked_commit_marker_v1(
    *, document: str
) -> Phase12ActivationAcceptedLockedCommitMarkerV1:
    """Parse one strict caller-supplied accepted-locked-commit marker document."""

    fields = _fields(document)
    if fields["schema_version"] != _SCHEMA_VERSION:
        _invalid_document()
    if _COMMIT.fullmatch(fields["accepted_locked_commit"]) is None:
        _invalid_document()
    return Phase12ActivationAcceptedLockedCommitMarkerV1(
        schema_version=fields["schema_version"],
        accepted_locked_commit=fields["accepted_locked_commit"],
    )
