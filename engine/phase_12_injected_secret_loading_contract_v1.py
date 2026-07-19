"""Pure injected secret-resolution boundary with redacted public evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


_CREDENTIAL_KINDS = ("API_KEY", "ACCESS_TOKEN")
_FAILURE_CODES = (
    "SECRET_RESOLUTION_NOT_AUTHORIZED",
    "REQUEST_ID_EMPTY",
    "CONFIGURATION_ID_EMPTY",
    "CREDENTIAL_REFERENCE_ID_EMPTY",
    "PROVIDER_ID_EMPTY",
    "SECRET_NAMESPACE_EMPTY",
    "SECRET_NAME_EMPTY",
    "VERSION_LABEL_EMPTY",
    "RESOLVER_ID_EMPTY",
    "IDENTIFIER_NOT_NORMALIZED",
    "CREDENTIAL_KIND_NOT_ALLOWED",
    "RESOLVER_REQUIRED",
    "RESOLVER_ID_MISMATCH",
    "RESOLVER_REJECTED_REQUEST",
    "SECRET_NOT_FOUND",
    "SECRET_EMPTY",
    "SECRET_TYPE_INVALID",
    "RESOLVER_FAILURE",
    "SECRET_EXPOSURE_DETECTED",
    "SECRET_PERSISTENCE_DETECTED",
)


def _require_normalized_identifier(value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or "*" in value:
        raise ValueError("identifier must be explicit and normalized")


def _require_strict_boolean(value: bool) -> None:
    if type(value) is not bool:
        raise ValueError("authorization state must be a strict boolean")


@dataclass(frozen=True, slots=True)
class SecretResolutionRequestV1:
    request_id: str
    configuration_id: str
    credential_reference_id: str
    provider_id: str
    secret_namespace: str
    secret_name: str
    credential_kind: str
    version_label: str
    resolver_id: str
    resolution_authorized: bool

    def __post_init__(self) -> None:
        for value in (
            self.request_id,
            self.configuration_id,
            self.credential_reference_id,
            self.provider_id,
            self.secret_namespace,
            self.secret_name,
            self.version_label,
            self.resolver_id,
        ):
            _require_normalized_identifier(value)
        if self.credential_kind not in _CREDENTIAL_KINDS:
            raise ValueError("credential kind is not allowed")
        _require_strict_boolean(self.resolution_authorized)


class SecretResolverV1(Protocol):
    resolver_id: str

    def resolve(self, request: SecretResolutionRequestV1) -> object: ...


@dataclass(frozen=True, slots=True)
class SecretResolutionFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool

    def __post_init__(self) -> None:
        if self.failure_code not in _FAILURE_CODES:
            raise ValueError("failure code is not canonical")
        _require_normalized_identifier(self.safe_message)
        _require_strict_boolean(self.retryable)
        if self.retryable:
            raise ValueError("retries are not authorized")


@dataclass(frozen=True, slots=True)
class SecretResolutionResultV1:
    request_id: str
    credential_reference_id: str
    resolver_id: str
    resolved: bool
    secret_present: bool
    failure: SecretResolutionFailureV1 | None
    resolver_invoked: bool
    credential_values_exposed: bool
    secret_persisted: bool
    environment_accessed: bool
    secret_files_accessed: bool
    external_secret_store_contacted: bool
    credential_verified: bool
    provider_authenticated: bool
    provider_contacted: bool
    execution_authorized: bool


@dataclass(frozen=True, slots=True)
class SecretResolutionAuditEvidenceV1:
    request_id: str
    configuration_id: str
    credential_reference_id: str
    provider_id: str
    credential_kind: str
    resolver_id: str
    resolution_authorized: bool
    resolver_invoked: bool
    resolved: bool
    failure_code: str | None
    credential_values_exposed: bool
    secret_persisted: bool
    environment_accessed: bool
    secret_files_accessed: bool
    external_secret_store_contacted: bool
    provider_contacted: bool
    execution_authorized: bool


def _failure_result(
    request: SecretResolutionRequestV1,
    code: str,
    message: str,
    *,
    resolver_invoked: bool,
) -> SecretResolutionResultV1:
    return SecretResolutionResultV1(
        request_id=request.request_id,
        credential_reference_id=request.credential_reference_id,
        resolver_id=request.resolver_id,
        resolved=False,
        secret_present=False,
        failure=SecretResolutionFailureV1(code, message, False),
        resolver_invoked=resolver_invoked,
        credential_values_exposed=False,
        secret_persisted=False,
        environment_accessed=False,
        secret_files_accessed=False,
        external_secret_store_contacted=False,
        credential_verified=False,
        provider_authenticated=False,
        provider_contacted=False,
        execution_authorized=False,
    )


def resolve_secret_reference_v1(
    request: SecretResolutionRequestV1, resolver: SecretResolverV1 | None
) -> SecretResolutionResultV1:
    """Invoke one explicitly supplied resolver, retaining no returned material."""

    if not request.resolution_authorized:
        return _failure_result(
            request,
            "SECRET_RESOLUTION_NOT_AUTHORIZED",
            "secret resolution is not authorized",
            resolver_invoked=False,
        )
    if resolver is None:
        return _failure_result(
            request, "RESOLVER_REQUIRED", "explicit resolver is required", resolver_invoked=False
        )
    if getattr(resolver, "resolver_id", None) != request.resolver_id:
        return _failure_result(
            request, "RESOLVER_ID_MISMATCH", "resolver identity does not match", resolver_invoked=False
        )

    try:
        resolution = resolver.resolve(request)
    except Exception:
        return _failure_result(
            request, "RESOLVER_FAILURE", "resolver failed", resolver_invoked=True
        )

    if isinstance(resolution, SecretResolutionFailureV1):
        return _failure_result(
            request,
            resolution.failure_code,
            resolution.safe_message,
            resolver_invoked=True,
        )
    if resolution is None:
        return _failure_result(
            request, "SECRET_NOT_FOUND", "secret was not found", resolver_invoked=True
        )
    if not isinstance(resolution, str):
        return _failure_result(
            request, "SECRET_TYPE_INVALID", "resolver returned invalid type", resolver_invoked=True
        )
    if not resolution:
        return _failure_result(
            request, "SECRET_EMPTY", "resolver returned empty secret", resolver_invoked=True
        )

    return SecretResolutionResultV1(
        request_id=request.request_id,
        credential_reference_id=request.credential_reference_id,
        resolver_id=request.resolver_id,
        resolved=True,
        secret_present=True,
        failure=None,
        resolver_invoked=True,
        credential_values_exposed=False,
        secret_persisted=False,
        environment_accessed=False,
        secret_files_accessed=False,
        external_secret_store_contacted=False,
        credential_verified=False,
        provider_authenticated=False,
        provider_contacted=False,
        execution_authorized=False,
    )


def build_secret_resolution_audit_evidence_v1(
    request: SecretResolutionRequestV1, result: SecretResolutionResultV1
) -> SecretResolutionAuditEvidenceV1:
    """Build immutable metadata-only audit evidence for a matching request/result pair."""

    if (
        request.request_id != result.request_id
        or request.credential_reference_id != result.credential_reference_id
        or request.resolver_id != result.resolver_id
    ):
        raise ValueError("request and result identities must match")
    return SecretResolutionAuditEvidenceV1(
        request_id=request.request_id,
        configuration_id=request.configuration_id,
        credential_reference_id=request.credential_reference_id,
        provider_id=request.provider_id,
        credential_kind=request.credential_kind,
        resolver_id=request.resolver_id,
        resolution_authorized=request.resolution_authorized,
        resolver_invoked=result.resolver_invoked,
        resolved=result.resolved,
        failure_code=result.failure.failure_code if result.failure else None,
        credential_values_exposed=False,
        secret_persisted=False,
        environment_accessed=False,
        secret_files_accessed=False,
        external_secret_store_contacted=False,
        provider_contacted=False,
        execution_authorized=False,
    )
