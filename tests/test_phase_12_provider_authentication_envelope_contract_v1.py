"""RED contract for a fake-only, redacted provider authentication envelope."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime

import pytest

from engine.phase_12_provider_authentication_envelope_contract_v1 import (
    ProviderAuthenticationAuditEvidenceV1,
    ProviderAuthenticationEnvelopeV1,
    ProviderAuthenticationFailureV1,
    ProviderAuthenticationPolicyV1,
    ProviderAuthenticationRequestV1,
    ProviderAuthenticationResultV1,
    ProviderCredentialBindingV1,
    ProviderSecretHandleV1,
    ProviderSecretProviderV1,
    build_provider_authentication_audit_evidence_v1,
    build_provider_authentication_envelope_v1,
)


_NOW = datetime(2030, 1, 3, 12, 0, tzinfo=UTC)
_EXPIRES = datetime(2030, 1, 4, 12, 0, tzinfo=UTC)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "provider_id", "authentication_scheme", "authentication_location",
    "authentication_field_name", "allowed_authentication_schemes", "allowed_authentication_locations",
    "allowed_field_names", "require_https", "require_verified_credential", "require_verified_secret_source",
    "require_single_secret_load", "require_single_secret_consumption", "require_secret_redaction",
    "require_nonempty_secret", "minimum_secret_length", "maximum_secret_length", "fingerprint_algorithm",
    "fingerprint_prefix_length", "secret_provider_invocation_limit", "secret_consumption_limit",
    "retry_allowed", "fallback_credential_allowed", "authentication_authorized", "transmission_authorized",
    "provider_execution_authorized", "fail_closed",
)
_BINDING_FIELDS = (
    "credential_binding_id", "provider_id", "credential_reference_id", "credential_verification_id",
    "secret_source_id", "secret_version_id", "authentication_policy_id", "endpoint_configuration_id",
    "request_route_id", "provider_request_id", "reservation_id", "persistence_command_id",
    "connectivity_preflight_request_id", "verified_at", "expires_at", "credential_verified",
    "secret_source_verified", "credential_active", "credential_expired", "credential_revoked",
    "authentication_authorized", "transmission_authorized", "provider_execution_authorized",
)
_REQUEST_FIELDS = (
    "authentication_request_id", "authentication_policy_id", "credential_binding_id", "provider_id",
    "credential_reference_id", "endpoint_configuration_id", "request_route_id", "provider_request_id",
    "reservation_id", "persistence_command_id", "connectivity_preflight_request_id", "requested_at",
    "credential_verified", "credential_binding_valid", "connectivity_metadata_ready", "persistence_confirmed",
    "persistence_recovery_clear", "authentication_envelope_authorized",
)
_ENVELOPE_FIELDS = (
    "authentication_envelope_id", "authentication_request_id", "authentication_policy_id",
    "credential_binding_id", "provider_id", "credential_reference_id", "secret_source_id",
    "secret_version_id", "authentication_scheme", "authentication_location", "authentication_field_name",
    "secret_fingerprint", "secret_length", "envelope_constructed", "secret_provider_invoked",
    "secret_handle_received", "secret_consumed", "authenticated", "transmitted", "provider_executed",
    "retry_attempted", "fallback_attempted",
)
_RESULT_FIELDS = (
    "authentication_request_id", "authentication_policy_id", "credential_binding_id", "accepted",
    "failure_codes", "secret_provider_invoked", "secret_handle_received", "secret_consumed",
    "envelope_constructed", "credential_binding_valid", "authentication_policy_valid",
    "connectivity_evidence_valid", "persistence_evidence_valid", "fingerprint_valid", "redaction_valid",
    "authenticated", "transmitted", "provider_executed", "retry_attempted", "fallback_attempted",
)
_AUDIT_FIELDS = (
    "authentication_request_id", "authentication_policy_id", "credential_binding_id", "provider_id",
    "credential_reference_id", "secret_source_id", "secret_version_id", "endpoint_configuration_id",
    "request_route_id", "provider_request_id", "reservation_id", "persistence_command_id",
    "connectivity_preflight_request_id", "authentication_scheme", "authentication_location",
    "authentication_field_name", "secret_fingerprint", "secret_length", "secret_provider_invoked",
    "secret_consumed", "envelope_constructed", "failure_codes", "authenticated", "transmitted",
    "provider_executed", "retry_attempted", "fallback_attempted",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_FAILURES = {
    "AUTHENTICATION_REQUEST_ID_EMPTY", "AUTHENTICATION_POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY",
    "CREDENTIAL_BINDING_ID_EMPTY", "PROVIDER_ID_EMPTY", "CREDENTIAL_REFERENCE_ID_EMPTY",
    "CREDENTIAL_VERIFICATION_ID_EMPTY", "SECRET_SOURCE_ID_EMPTY", "SECRET_VERSION_ID_EMPTY",
    "ENDPOINT_CONFIGURATION_ID_EMPTY", "REQUEST_ROUTE_ID_EMPTY", "PROVIDER_REQUEST_ID_EMPTY",
    "RESERVATION_ID_EMPTY", "PERSISTENCE_COMMAND_ID_EMPTY", "CONNECTIVITY_PREFLIGHT_REQUEST_ID_EMPTY",
    "IDENTIFIER_NOT_NORMALIZED", "PROVIDER_IDENTITY_MISMATCH", "CREDENTIAL_REFERENCE_MISMATCH",
    "POLICY_IDENTITY_MISMATCH", "ENDPOINT_IDENTITY_MISMATCH", "ROUTE_IDENTITY_MISMATCH",
    "PROVIDER_REQUEST_IDENTITY_MISMATCH", "RESERVATION_IDENTITY_MISMATCH",
    "PERSISTENCE_COMMAND_IDENTITY_MISMATCH", "CONNECTIVITY_PREFLIGHT_IDENTITY_MISMATCH",
    "CREDENTIAL_NOT_VERIFIED", "CREDENTIAL_BINDING_INVALID", "SECRET_SOURCE_NOT_VERIFIED",
    "CREDENTIAL_INACTIVE", "CREDENTIAL_EXPIRED", "CREDENTIAL_REVOKED", "CONNECTIVITY_METADATA_NOT_READY",
    "PERSISTENCE_NOT_CONFIRMED", "PERSISTENCE_RECOVERY_UNRESOLVED",
    "AUTHENTICATION_ENVELOPE_NOT_AUTHORIZED", "AUTHENTICATION_NOT_AUTHORIZED",
    "TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED",
    "AUTHENTICATION_SCHEME_NOT_ALLOWED", "AUTHENTICATION_LOCATION_NOT_ALLOWED",
    "AUTHENTICATION_FIELD_NAME_EMPTY", "AUTHENTICATION_FIELD_NAME_NOT_ALLOWED",
    "AUTHENTICATION_FIELD_NAME_INVALID", "HTTPS_REQUIRED", "VERIFIED_CREDENTIAL_REQUIRED",
    "VERIFIED_SECRET_SOURCE_REQUIRED", "SECRET_PROVIDER_REQUIRED", "SECRET_PROVIDER_INVOCATION_LIMIT_INVALID",
    "SECRET_CONSUMPTION_LIMIT_INVALID", "SECRET_PROVIDER_INVOCATION_FAILED", "SECRET_HANDLE_INVALID",
    "SECRET_EMPTY", "SECRET_LENGTH_INVALID", "SECRET_ALREADY_CONSUMED", "SECRET_CONSUMPTION_FAILED",
    "SECRET_FINGERPRINT_FAILURE", "SECRET_REDACTION_REQUIRED", "ENVELOPE_CONSTRUCTION_FAILED",
    "RETRY_NOT_AUTHORIZED", "FALLBACK_CREDENTIAL_NOT_AUTHORIZED", "RAW_SECRET_EXPOSURE_DETECTED",
    "RAW_HEADER_VALUE_EXPOSURE_DETECTED", "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


class _FakeSecretHandle:
    def __init__(self) -> None:
        self.calls = 0
        self._synthetic_value = "synthetic-contract-material-not-a-credential"

    def secret_identity(self) -> str:
        return "synthetic-secret-identity-v1"

    def secret_length(self) -> int:
        return len(self._synthetic_value)

    def use_once_for_authentication(self, consumer: object) -> object:
        self.calls += 1
        return consumer(self._synthetic_value)  # type: ignore[operator]

    def __repr__(self) -> str:
        return "_FakeSecretHandle(REDACTED)"


class _FakeSecretProvider:
    def __init__(self, handle: _FakeSecretHandle) -> None:
        self.handle = handle
        self.calls = 0

    def load_verified_secret(self, credential_reference_id: str) -> _FakeSecretHandle:
        self.calls += 1
        assert credential_reference_id == "credential-reference-v1"
        return self.handle


def _policy(**overrides: object) -> ProviderAuthenticationPolicyV1:
    values = {
        "policy_id": "authentication-policy-v1", "policy_version": "V1", "provider_id": "provider-v1",
        "authentication_scheme": "API_KEY", "authentication_location": "HEADER",
        "authentication_field_name": "X-Provider-Key", "allowed_authentication_schemes": ("API_KEY",),
        "allowed_authentication_locations": ("HEADER",), "allowed_field_names": ("X-Provider-Key",),
        "require_https": True, "require_verified_credential": True, "require_verified_secret_source": True,
        "require_single_secret_load": True, "require_single_secret_consumption": True,
        "require_secret_redaction": True, "require_nonempty_secret": True, "minimum_secret_length": 8,
        "maximum_secret_length": 128, "fingerprint_algorithm": "SHA256", "fingerprint_prefix_length": 12,
        "secret_provider_invocation_limit": 1, "secret_consumption_limit": 1, "retry_allowed": False,
        "fallback_credential_allowed": False, "authentication_authorized": True,
        "transmission_authorized": False, "provider_execution_authorized": False, "fail_closed": True,
    }
    values.update(overrides)
    return ProviderAuthenticationPolicyV1(**values)


def _binding(**overrides: object) -> ProviderCredentialBindingV1:
    values = {
        "credential_binding_id": "credential-binding-v1", "provider_id": "provider-v1",
        "credential_reference_id": "credential-reference-v1", "credential_verification_id": "credential-verification-v1",
        "secret_source_id": "synthetic-secret-source-v1", "secret_version_id": "synthetic-secret-version-v1",
        "authentication_policy_id": "authentication-policy-v1", "endpoint_configuration_id": "endpoint-config-v1",
        "request_route_id": "provider-route-v1", "provider_request_id": "provider-request-v1",
        "reservation_id": "reservation-v1", "persistence_command_id": "persistence-command-v1",
        "connectivity_preflight_request_id": "connectivity-preflight-v1", "verified_at": _NOW,
        "expires_at": _EXPIRES, "credential_verified": True, "secret_source_verified": True,
        "credential_active": True, "credential_expired": False, "credential_revoked": False,
        "authentication_authorized": True, "transmission_authorized": False,
        "provider_execution_authorized": False,
    }
    values.update(overrides)
    return ProviderCredentialBindingV1(**values)


def _authentication(**overrides: object) -> ProviderAuthenticationRequestV1:
    values = {
        "authentication_request_id": "authentication-request-v1", "authentication_policy_id": "authentication-policy-v1",
        "credential_binding_id": "credential-binding-v1", "provider_id": "provider-v1",
        "credential_reference_id": "credential-reference-v1", "endpoint_configuration_id": "endpoint-config-v1",
        "request_route_id": "provider-route-v1", "provider_request_id": "provider-request-v1",
        "reservation_id": "reservation-v1", "persistence_command_id": "persistence-command-v1",
        "connectivity_preflight_request_id": "connectivity-preflight-v1", "requested_at": _NOW,
        "credential_verified": True, "credential_binding_valid": True, "connectivity_metadata_ready": True,
        "persistence_confirmed": True, "persistence_recovery_clear": True,
        "authentication_envelope_authorized": True,
    }
    values.update(overrides)
    return ProviderAuthenticationRequestV1(**values)


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_narrow_and_secret_redacted() -> None:
    assert tuple(field.name for field in fields(ProviderAuthenticationPolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(ProviderCredentialBindingV1)) == _BINDING_FIELDS
    assert tuple(field.name for field in fields(ProviderAuthenticationRequestV1)) == _REQUEST_FIELDS
    assert tuple(field.name for field in fields(ProviderAuthenticationEnvelopeV1)) == _ENVELOPE_FIELDS
    assert tuple(field.name for field in fields(ProviderAuthenticationResultV1)) == _RESULT_FIELDS
    assert tuple(field.name for field in fields(ProviderAuthenticationAuditEvidenceV1)) == _AUDIT_FIELDS
    assert tuple(field.name for field in fields(ProviderAuthenticationFailureV1)) == _FAILURE_FIELDS
    assert {"load_verified_secret"}.issubset(dir(ProviderSecretProviderV1))
    assert {"secret_identity", "secret_length", "use_once_for_authentication"}.issubset(dir(ProviderSecretHandleV1))
    forbidden = {"plaintext", "bytes", "serialize", "clone", "headers", "authorization"}
    assert not forbidden.intersection(dir(ProviderSecretHandleV1))
    result = build_provider_authentication_envelope_v1(_policy(), _binding(), _authentication(), None)
    evidence = build_provider_authentication_audit_evidence_v1(_policy(), _binding(), _authentication(), result)
    for value in (_policy(), _binding(), _authentication(), result, evidence):
        _frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        _policy().authentication_authorized = False  # type: ignore[misc]


def test_invalid_preconditions_fail_before_fake_secret_provider() -> None:
    provider = _FakeSecretProvider(_FakeSecretHandle())
    result = build_provider_authentication_envelope_v1(
        _policy(authentication_authorized=False), _binding(credential_active=False),
        _authentication(credential_verified=False, persistence_confirmed=False), provider,
    )
    assert {"CREDENTIAL_NOT_VERIFIED", "CREDENTIAL_INACTIVE", "PERSISTENCE_NOT_CONFIRMED",
            "AUTHENTICATION_NOT_AUTHORIZED"}.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert provider.calls == 0
    assert (result.secret_provider_invoked, result.secret_handle_received, result.secret_consumed,
            result.envelope_constructed, result.authenticated, result.transmitted, result.provider_executed,
            result.retry_attempted, result.fallback_attempted) == (False,) * 9


def test_fake_single_use_envelope_is_redacted_and_never_authenticates() -> None:
    handle = _FakeSecretHandle()
    provider = _FakeSecretProvider(handle)
    result = build_provider_authentication_envelope_v1(_policy(), _binding(), _authentication(), provider)
    assert result.accepted is True and result.envelope_constructed is True
    assert provider.calls == handle.calls == 1
    assert (result.authenticated, result.transmitted, result.provider_executed,
            result.retry_attempted, result.fallback_attempted) == (False,) * 5
    assert result.envelope is not None
    assert "synthetic-contract-material-not-a-credential" not in repr(result.envelope)


def test_audit_is_deterministic_identity_bound_and_does_not_consume_again() -> None:
    handle = _FakeSecretHandle()
    provider = _FakeSecretProvider(handle)
    policy, binding, authentication = _policy(), _binding(), _authentication()
    result = build_provider_authentication_envelope_v1(policy, binding, authentication, provider)
    evidence = build_provider_authentication_audit_evidence_v1(policy, binding, authentication, result)
    assert evidence == build_provider_authentication_audit_evidence_v1(policy, binding, authentication, result)
    assert handle.calls == 1 and provider.calls == 1
    assert evidence.authenticated is evidence.transmitted is evidence.provider_executed is False
    with pytest.raises(ValueError):
        build_provider_authentication_audit_evidence_v1(policy, _binding(provider_id="other-provider-v1"), authentication, result)
