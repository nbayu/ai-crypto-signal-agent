"""Pure injected credential-verification metadata boundary for Phase 12."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


_KINDS = ("API_KEY", "ACCESS_TOKEN")
_CODES = (
    "VERIFICATION_REQUEST_ID_EMPTY", "SECRET_RESOLUTION_REQUEST_ID_EMPTY", "CONFIGURATION_ID_EMPTY", "CREDENTIAL_REFERENCE_ID_EMPTY", "PROVIDER_ID_EMPTY", "VERSION_LABEL_EMPTY", "VERIFIER_ID_EMPTY", "IDENTIFIER_NOT_NORMALIZED", "CREDENTIAL_KIND_NOT_ALLOWED", "SECRET_RESOLUTION_NOT_SUCCESSFUL", "SECRET_NOT_PRESENT", "CREDENTIAL_VERIFICATION_NOT_AUTHORIZED", "VERIFIER_REQUIRED", "VERIFIER_ID_MISMATCH", "VERIFIER_REJECTED_REQUEST", "CREDENTIAL_INVALID", "CREDENTIAL_DISABLED", "CREDENTIAL_EXPIRED", "CREDENTIAL_SCOPE_INSUFFICIENT", "VERIFIER_FAILURE", "CREDENTIAL_EXPOSURE_DETECTED", "SECRET_PERSISTENCE_DETECTED",
)


def _text(value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or "*" in value:
        raise ValueError("identity must be explicit and normalized")


def _boolean(value: bool) -> None:
    if type(value) is not bool:
        raise ValueError("boolean must be strict")


@dataclass(frozen=True, slots=True)
class CredentialVerificationRequestV1:
    verification_request_id: str
    secret_resolution_request_id: str
    configuration_id: str
    credential_reference_id: str
    provider_id: str
    credential_kind: str
    version_label: str
    verifier_id: str
    secret_resolution_succeeded: bool
    secret_present: bool
    verification_authorized: bool

    def __post_init__(self) -> None:
        for value in (self.verification_request_id, self.secret_resolution_request_id, self.configuration_id, self.credential_reference_id, self.provider_id, self.version_label, self.verifier_id):
            _text(value)
        if self.credential_kind not in _KINDS:
            raise ValueError("credential kind is not allowed")
        for value in (self.secret_resolution_succeeded, self.secret_present, self.verification_authorized):
            _boolean(value)


class CredentialVerifierV1(Protocol):
    verifier_id: str

    def verify(self, request: CredentialVerificationRequestV1) -> object: ...


@dataclass(frozen=True, slots=True)
class CredentialVerificationFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool

    def __post_init__(self) -> None:
        if self.failure_code not in _CODES:
            raise ValueError("failure code is not canonical")
        _text(self.safe_message)
        _boolean(self.retryable)
        if self.retryable:
            raise ValueError("retry is not authorized")


@dataclass(frozen=True, slots=True)
class CredentialVerificationResultV1:
    verification_request_id: str
    credential_reference_id: str
    verifier_id: str
    verification_attempted: bool
    verifier_invoked: bool
    credential_verified: bool
    failure: CredentialVerificationFailureV1 | None
    credential_values_exposed: bool
    secret_persisted: bool
    environment_accessed: bool
    secret_files_accessed: bool
    external_secret_store_contacted: bool
    provider_authenticated: bool
    provider_contacted: bool
    provider_connectivity_proven: bool
    request_creation_authorized: bool
    provider_execution_authorized: bool
    execution_authorized: bool


@dataclass(frozen=True, slots=True)
class CredentialVerificationAuditEvidenceV1:
    verification_request_id: str
    secret_resolution_request_id: str
    configuration_id: str
    credential_reference_id: str
    provider_id: str
    credential_kind: str
    verifier_id: str
    secret_resolution_succeeded: bool
    secret_present: bool
    verification_authorized: bool
    verification_attempted: bool
    verifier_invoked: bool
    credential_verified: bool
    failure_code: str | None
    credential_values_exposed: bool
    secret_persisted: bool
    environment_accessed: bool
    secret_files_accessed: bool
    external_secret_store_contacted: bool
    provider_contacted: bool
    provider_connectivity_proven: bool
    request_creation_authorized: bool
    provider_execution_authorized: bool
    execution_authorized: bool


def _failure(request: CredentialVerificationRequestV1, code: str, message: str, attempted: bool, invoked: bool) -> CredentialVerificationResultV1:
    return CredentialVerificationResultV1(request.verification_request_id, request.credential_reference_id, request.verifier_id, attempted, invoked, False, CredentialVerificationFailureV1(code, message, False), False, False, False, False, False, False, False, False, False, False, False)


def verify_credential_reference_v1(request: CredentialVerificationRequestV1, verifier: CredentialVerifierV1 | None) -> CredentialVerificationResultV1:
    """Perform one injected abstract verification without provider behavior."""
    if not request.secret_resolution_succeeded:
        return _failure(request, "SECRET_RESOLUTION_NOT_SUCCESSFUL", "secret resolution was not successful", False, False)
    if not request.secret_present:
        return _failure(request, "SECRET_NOT_PRESENT", "secret is not present", False, False)
    if not request.verification_authorized:
        return _failure(request, "CREDENTIAL_VERIFICATION_NOT_AUTHORIZED", "credential verification is not authorized", False, False)
    if verifier is None:
        return _failure(request, "VERIFIER_REQUIRED", "explicit verifier is required", False, False)
    if getattr(verifier, "verifier_id", None) != request.verifier_id:
        return _failure(request, "VERIFIER_ID_MISMATCH", "verifier identity does not match", False, False)
    try:
        outcome = verifier.verify(request)
    except Exception:
        return _failure(request, "VERIFIER_FAILURE", "verifier failed", True, True)
    if isinstance(outcome, CredentialVerificationFailureV1):
        return _failure(request, outcome.failure_code, outcome.safe_message, True, True)
    if outcome is True:
        return CredentialVerificationResultV1(request.verification_request_id, request.credential_reference_id, request.verifier_id, True, True, True, None, False, False, False, False, False, False, False, False, False, False, False)
    return _failure(request, "VERIFIER_REJECTED_REQUEST", "verifier rejected request", True, True)


def build_credential_verification_audit_evidence_v1(request: CredentialVerificationRequestV1, result: CredentialVerificationResultV1) -> CredentialVerificationAuditEvidenceV1:
    """Return immutable non-secret evidence for an identity-aligned result."""
    if request.verification_request_id != result.verification_request_id or request.credential_reference_id != result.credential_reference_id or request.verifier_id != result.verifier_id:
        raise ValueError("request and result identities must match")
    return CredentialVerificationAuditEvidenceV1(request.verification_request_id, request.secret_resolution_request_id, request.configuration_id, request.credential_reference_id, request.provider_id, request.credential_kind, request.verifier_id, request.secret_resolution_succeeded, request.secret_present, request.verification_authorized, result.verification_attempted, result.verifier_invoked, result.credential_verified, result.failure.failure_code if result.failure else None, False, False, False, False, False, False, False, False, False, False)
