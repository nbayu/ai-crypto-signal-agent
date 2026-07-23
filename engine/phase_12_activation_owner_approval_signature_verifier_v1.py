"""Pure Ed25519 verification of a caller-supplied Phase 12 owner approval."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


__all__ = ("verify_phase_12_activation_owner_approval_signature_v1",)

_FIELDS = (
    "payload_schema_version", "signature_algorithm_identifier", "signing_key_identifier",
    "activation_mode", "owner_authorization_id", "checkpoint_id",
    "approved_locked_commit", "accepted_locked_commit", "approval_timestamp", "expiry",
    "environment_identifier", "deployment_identifier", "replay_control_value",
    "repository_identity", "repository_commit", "approval_scope",
)
_SCHEMA = "phase12-owner-approval-signature-v1"
_ALGORITHM = "PHASE12-ED25519-SHA512-RAW-V1"
_ENVIRONMENT = "ai-crypto-signal-agent-production-v1"
_SCOPE = "EXACT_ACTIVATION_ATTEMPT"
_MODES = frozenset((
    "CREDENTIAL_VALIDATION", "TELEGRAM_CONNECTIVITY_VALIDATION",
    "TELEGRAM_START_VALIDATION", "CONTROLLED_WORKLOAD",
))
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_KEY_IDENTIFIER = re.compile(r"ed25519-sha256:[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_ALGORITHM_VALUE = re.compile(r"[A-Z0-9-]{1,64}\Z")


@dataclass(frozen=True, slots=True, kw_only=True)
class _Phase12VerifiedOwnerApprovalFactsV1:
    payload_schema_version: str
    signature_algorithm_identifier: str
    signing_key_identifier: str
    activation_mode: str
    owner_authorization_id: str
    checkpoint_id: str
    approved_locked_commit: str
    accepted_locked_commit: str
    approval_timestamp_utc: datetime
    expiry_utc: datetime
    environment_identifier: str
    deployment_identifier: str
    replay_control_value: str
    repository_identity: str
    repository_commit: str
    approval_scope: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _Phase12OwnerApprovalSignatureVerificationResultV1:
    is_valid: bool
    failure_codes: tuple[str, ...]
    verified_approval: _Phase12VerifiedOwnerApprovalFactsV1 | None


def _failure(code: str) -> _Phase12OwnerApprovalSignatureVerificationResultV1:
    return _Phase12OwnerApprovalSignatureVerificationResultV1(
        is_valid=False, failure_codes=(code,), verified_approval=None
    )


def _identifier(value: object) -> bool:
    return type(value) is str and _IDENTIFIER.fullmatch(value) is not None


def _key_identifier(value: object) -> bool:
    return type(value) is str and _KEY_IDENTIFIER.fullmatch(value) is not None


def _timestamp(value: str) -> datetime | None:
    if _TIMESTAMP.fullmatch(value) is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _canonical_fields(payload: bytes) -> dict[str, str] | None:
    if (
        len(payload) > 2048 or payload.startswith(b"\xef\xbb\xbf") or b"\r" in payload
        or not payload.endswith(b"\n") or any(byte > 127 for byte in payload)
    ):
        return None
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError:
        return None
    lines = text.split("\n")
    if len(lines) != len(_FIELDS) + 1 or lines[-1] != "":
        return None
    result: dict[str, str] = {}
    for expected, line in zip(_FIELDS, lines[:-1]):
        if line.count("=") != 1:
            return None
        name, value = line.split("=")
        if name != expected or not value or value != value.strip() or any(ord(char) < 32 for char in value):
            return None
        result[name] = value
    if _IDENTIFIER.fullmatch(result["payload_schema_version"]) is None:
        return None
    if _ALGORITHM_VALUE.fullmatch(result["signature_algorithm_identifier"]) is None:
        return None
    if not _key_identifier(result["signing_key_identifier"]):
        return None
    if result["activation_mode"] not in _MODES:
        return None
    if any(not _identifier(result[name]) for name in (
        "owner_authorization_id", "checkpoint_id", "deployment_identifier",
        "replay_control_value", "repository_identity",
    )):
        return None
    if any(_COMMIT.fullmatch(result[name]) is None for name in (
        "approved_locked_commit", "accepted_locked_commit", "repository_commit",
    )):
        return None
    if _timestamp(result["approval_timestamp"]) is None or _timestamp(result["expiry"]) is None:
        return None
    if result["environment_identifier"] != _ENVIRONMENT or result["approval_scope"] != _SCOPE:
        return None
    return result


def _caller_inputs_are_valid(
    *, canonical_payload_bytes: object, signature_bytes: object, public_key_bytes: object,
    expected_signing_key_identifier: object, revocation_state_available: object,
    active_signing_key_identifier: object, revoked_signing_key_identifiers: object,
    revocation_state_checkpoint_identifier: object, expected_environment_identifier: object,
    expected_deployment_identifier: object, expected_checkpoint_identifier: object,
    now_utc: object,
) -> bool:
    if (
        type(canonical_payload_bytes) is not bytes or type(signature_bytes) is not bytes
        or public_key_bytes is not None and type(public_key_bytes) is not bytes
        or not _key_identifier(expected_signing_key_identifier)
        or type(revocation_state_available) is not bool
        or not _identifier(expected_environment_identifier)
        or not _identifier(expected_deployment_identifier)
        or not _identifier(expected_checkpoint_identifier)
    ):
        return False
    if now_utc is not None and (type(now_utc) is not datetime or now_utc.tzinfo is not timezone.utc):
        return False
    if revocation_state_available:
        if (
            not _key_identifier(active_signing_key_identifier)
            or type(revoked_signing_key_identifiers) is not tuple
            or not _identifier(revocation_state_checkpoint_identifier)
            or any(not _key_identifier(value) for value in revoked_signing_key_identifiers)
            or len(set(revoked_signing_key_identifiers)) != len(revoked_signing_key_identifiers)
            or active_signing_key_identifier in revoked_signing_key_identifiers
        ):
            return False
    elif (
        active_signing_key_identifier is not None or revoked_signing_key_identifiers is not None
        or revocation_state_checkpoint_identifier is not None
    ):
        return False
    return True


def verify_phase_12_activation_owner_approval_signature_v1(
    *,
    canonical_payload_bytes: bytes,
    signature_bytes: bytes,
    public_key_bytes: bytes | None,
    expected_signing_key_identifier: str,
    revocation_state_available: bool,
    active_signing_key_identifier: str | None,
    revoked_signing_key_identifiers: tuple[str, ...] | None,
    revocation_state_checkpoint_identifier: str | None,
    expected_environment_identifier: str,
    expected_deployment_identifier: str,
    expected_checkpoint_identifier: str,
    now_utc: datetime | None,
) -> _Phase12OwnerApprovalSignatureVerificationResultV1:
    """Verify one caller-supplied owner approval without external side effects."""
    if not _caller_inputs_are_valid(
        canonical_payload_bytes=canonical_payload_bytes, signature_bytes=signature_bytes,
        public_key_bytes=public_key_bytes,
        expected_signing_key_identifier=expected_signing_key_identifier,
        revocation_state_available=revocation_state_available,
        active_signing_key_identifier=active_signing_key_identifier,
        revoked_signing_key_identifiers=revoked_signing_key_identifiers,
        revocation_state_checkpoint_identifier=revocation_state_checkpoint_identifier,
        expected_environment_identifier=expected_environment_identifier,
        expected_deployment_identifier=expected_deployment_identifier,
        expected_checkpoint_identifier=expected_checkpoint_identifier, now_utc=now_utc,
    ):
        raise TypeError()
    fields = _canonical_fields(canonical_payload_bytes)
    if fields is None:
        return _failure("MALFORMED_CANONICAL_PAYLOAD")
    if fields["payload_schema_version"] != _SCHEMA:
        return _failure("UNKNOWN_PAYLOAD_SCHEMA")
    if fields["signature_algorithm_identifier"] != _ALGORITHM:
        return _failure("UNKNOWN_SIGNATURE_ALGORITHM")
    if public_key_bytes is None:
        return _failure("TRUST_MATERIAL_UNAVAILABLE")
    if len(public_key_bytes) != 32:
        return _failure("MALFORMED_PUBLIC_KEY")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    except ValueError:
        return _failure("MALFORMED_PUBLIC_KEY")
    derived_key_identifier = "ed25519-sha256:" + sha256(public_key_bytes).hexdigest()
    if derived_key_identifier != expected_signing_key_identifier:
        return _failure("PUBLIC_KEY_FINGERPRINT_MISMATCH")
    if fields["signing_key_identifier"] != expected_signing_key_identifier:
        return _failure("UNKNOWN_SIGNING_KEY_ID")
    if revocation_state_available and active_signing_key_identifier != expected_signing_key_identifier:
        return _failure("UNKNOWN_SIGNING_KEY_ID")
    if not revocation_state_available:
        return _failure("REVOCATION_STATE_UNAVAILABLE")
    if fields["signing_key_identifier"] in revoked_signing_key_identifiers:
        return _failure("SIGNING_KEY_REVOKED")
    if len(signature_bytes) != 64:
        return _failure("MALFORMED_SIGNATURE")
    try:
        public_key.verify(signature_bytes, canonical_payload_bytes)
    except InvalidSignature:
        return _failure("SIGNATURE_MISMATCH")
    if fields["approved_locked_commit"] != fields["accepted_locked_commit"]:
        return _failure("APPROVED_ACCEPTED_COMMIT_MISMATCH")
    if fields["environment_identifier"] != expected_environment_identifier:
        return _failure("WRONG_ENVIRONMENT")
    if fields["deployment_identifier"] != expected_deployment_identifier:
        return _failure("WRONG_DEPLOYMENT")
    if fields["checkpoint_id"] != expected_checkpoint_identifier:
        return _failure("WRONG_CHECKPOINT")
    if fields["approval_scope"] != _SCOPE:
        return _failure("WRONG_APPROVAL_SCOPE")
    if now_utc is None:
        return _failure("CLOCK_EVIDENCE_UNAVAILABLE")
    approval_timestamp = _timestamp(fields["approval_timestamp"])
    expiry = _timestamp(fields["expiry"])
    if approval_timestamp is None or expiry is None:
        return _failure("MALFORMED_CANONICAL_PAYLOAD")
    if approval_timestamp > now_utc + timedelta(seconds=60):
        return _failure("APPROVAL_TIMESTAMP_IN_FUTURE")
    if now_utc >= expiry:
        return _failure("APPROVAL_EXPIRED")
    if expiry <= approval_timestamp or expiry - approval_timestamp > timedelta(minutes=15):
        return _failure("EXCESSIVE_APPROVAL_LIFETIME")
    return _Phase12OwnerApprovalSignatureVerificationResultV1(
        is_valid=True,
        failure_codes=(),
        verified_approval=_Phase12VerifiedOwnerApprovalFactsV1(
            payload_schema_version=fields["payload_schema_version"],
            signature_algorithm_identifier=fields["signature_algorithm_identifier"],
            signing_key_identifier=fields["signing_key_identifier"],
            activation_mode=fields["activation_mode"],
            owner_authorization_id=fields["owner_authorization_id"],
            checkpoint_id=fields["checkpoint_id"],
            approved_locked_commit=fields["approved_locked_commit"],
            accepted_locked_commit=fields["accepted_locked_commit"],
            approval_timestamp_utc=approval_timestamp,
            expiry_utc=expiry,
            environment_identifier=fields["environment_identifier"],
            deployment_identifier=fields["deployment_identifier"],
            replay_control_value=fields["replay_control_value"],
            repository_identity=fields["repository_identity"],
            repository_commit=fields["repository_commit"],
            approval_scope=fields["approval_scope"],
        ),
    )
