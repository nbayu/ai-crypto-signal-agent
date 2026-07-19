"""RED contract for fake-only, redacted authenticated provider-request assembly."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime

import pytest

from engine.phase_12_authenticated_provider_request_assembly_contract_v1 import (
    AuthenticatedProviderRequestAssemblyRequestV1,
    AuthenticatedProviderRequestAssemblyResultV1,
    AuthenticatedProviderRequestAuditEvidenceV1,
    AuthenticatedProviderRequestBindingV1,
    AuthenticatedProviderRequestDescriptorV1,
    AuthenticatedProviderRequestFailureV1,
    AuthenticatedProviderRequestPolicyV1,
    ProviderAuthenticationHeaderBinderV1,
    assemble_authenticated_provider_request_v1,
    build_authenticated_provider_request_audit_evidence_v1,
)


_NOW = datetime(2030, 1, 4, 12, 0, tzinfo=UTC)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "provider_id", "request_method", "allowed_methods",
    "transport_scheme", "require_https", "allowed_content_types", "allowed_accept_types",
    "authentication_scheme", "authentication_location", "authentication_field_name",
    "allowed_header_names", "prohibited_header_names", "require_request_id_header",
    "request_id_header_name", "require_idempotency_header", "idempotency_header_name",
    "require_content_type_header", "content_type_header_name", "require_accept_header",
    "accept_header_name", "maximum_header_count", "maximum_header_name_length", "maximum_body_bytes",
    "maximum_attempts", "maximum_redirects", "retry_allowed", "fallback_route_allowed",
    "header_binding_authorized", "request_assembly_authorized", "authentication_authorized",
    "transmission_authorized", "provider_execution_authorized", "fail_closed",
)
_BINDING_FIELDS = (
    "binding_id", "provider_id", "request_route_id", "endpoint_configuration_id",
    "connectivity_preflight_request_id", "authentication_request_id", "authentication_envelope_id",
    "authentication_policy_id", "credential_binding_id", "credential_reference_id", "provider_request_id",
    "provider_request_payload_identity", "reservation_id", "persistence_command_id", "idempotency_key",
    "pricing_evidence_id", "request_construction_policy_id", "authenticated_request_policy_id",
    "binding_verified", "connectivity_metadata_ready", "authentication_envelope_constructed",
    "reservation_persisted", "persistence_recovery_clear", "request_assembly_authorized",
    "transmission_authorized", "provider_execution_authorized",
)
_REQUEST_FIELDS = (
    "assembly_request_id", "binding_id", "provider_id", "request_route_id", "endpoint_configuration_id",
    "connectivity_preflight_request_id", "authentication_request_id", "authentication_envelope_id",
    "provider_request_id", "provider_request_payload_identity", "reservation_id", "persistence_command_id",
    "idempotency_key", "requested_at", "binding_valid", "provider_request_constructed",
    "pricing_revalidated", "reservation_persisted", "persistence_recovery_clear",
    "connectivity_metadata_ready", "authentication_envelope_constructed", "request_assembly_authorized",
)
_DESCRIPTOR_FIELDS = (
    "authenticated_request_descriptor_id", "assembly_request_id", "binding_id", "policy_id", "provider_id",
    "request_route_id", "endpoint_configuration_id", "provider_request_id", "payload_identity", "body_length",
    "request_method", "transport_scheme", "content_type", "accept_type", "ordered_header_names",
    "authentication_field_name", "request_id_header_name", "idempotency_header_name", "credential_reference_id",
    "authentication_envelope_id", "reservation_id", "persistence_command_id", "idempotency_key",
    "header_binder_invoked", "header_value_bound", "descriptor_constructed", "redaction_valid",
    "authenticated", "transmitted", "provider_executed", "retry_attempted", "redirect_attempted",
    "fallback_attempted",
)
_RESULT_FIELDS = (
    "assembly_request_id", "binding_id", "policy_id", "accepted", "failure_codes", "policy_valid",
    "binding_valid", "upstream_evidence_valid", "header_metadata_valid", "payload_metadata_valid",
    "idempotency_metadata_valid", "header_binder_invoked", "header_value_bound", "descriptor_constructed",
    "redaction_valid", "authenticated", "transmitted", "provider_executed", "retry_attempted",
    "redirect_attempted", "fallback_attempted",
)
_AUDIT_FIELDS = (
    "assembly_request_id", "binding_id", "policy_id", "provider_id", "request_route_id",
    "endpoint_configuration_id", "connectivity_preflight_request_id", "authentication_request_id",
    "authentication_envelope_id", "credential_reference_id", "provider_request_id", "payload_identity",
    "reservation_id", "persistence_command_id", "pricing_evidence_id", "request_construction_policy_id",
    "request_method", "transport_scheme", "content_type", "accept_type", "ordered_header_names",
    "body_length", "header_binder_invoked", "header_value_bound", "descriptor_constructed",
    "failure_codes", "authenticated", "transmitted", "provider_executed", "retry_attempted",
    "redirect_attempted", "fallback_attempted",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_FAILURES = {
    "ASSEMBLY_REQUEST_ID_EMPTY", "BINDING_ID_EMPTY", "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY",
    "PROVIDER_ID_EMPTY", "REQUEST_ROUTE_ID_EMPTY", "ENDPOINT_CONFIGURATION_ID_EMPTY",
    "CONNECTIVITY_PREFLIGHT_REQUEST_ID_EMPTY", "AUTHENTICATION_REQUEST_ID_EMPTY",
    "AUTHENTICATION_ENVELOPE_ID_EMPTY", "AUTHENTICATION_POLICY_ID_EMPTY", "CREDENTIAL_BINDING_ID_EMPTY",
    "CREDENTIAL_REFERENCE_ID_EMPTY", "PROVIDER_REQUEST_ID_EMPTY", "PAYLOAD_IDENTITY_EMPTY",
    "RESERVATION_ID_EMPTY", "PERSISTENCE_COMMAND_ID_EMPTY", "IDEMPOTENCY_KEY_EMPTY",
    "PRICING_EVIDENCE_ID_EMPTY", "REQUEST_CONSTRUCTION_POLICY_ID_EMPTY", "IDENTIFIER_NOT_NORMALIZED",
    "POLICY_IDENTITY_MISMATCH", "PROVIDER_IDENTITY_MISMATCH", "ROUTE_IDENTITY_MISMATCH",
    "ENDPOINT_IDENTITY_MISMATCH", "CONNECTIVITY_PREFLIGHT_IDENTITY_MISMATCH",
    "AUTHENTICATION_REQUEST_IDENTITY_MISMATCH", "AUTHENTICATION_ENVELOPE_IDENTITY_MISMATCH",
    "CREDENTIAL_REFERENCE_MISMATCH", "PROVIDER_REQUEST_IDENTITY_MISMATCH", "PAYLOAD_IDENTITY_MISMATCH",
    "RESERVATION_IDENTITY_MISMATCH", "PERSISTENCE_COMMAND_IDENTITY_MISMATCH",
    "IDEMPOTENCY_IDENTITY_MISMATCH", "BINDING_NOT_VERIFIED", "PROVIDER_REQUEST_NOT_CONSTRUCTED",
    "PRICING_NOT_REVALIDATED", "RESERVATION_NOT_PERSISTED", "PERSISTENCE_RECOVERY_UNRESOLVED",
    "CONNECTIVITY_METADATA_NOT_READY", "AUTHENTICATION_ENVELOPE_NOT_CONSTRUCTED",
    "REQUEST_ASSEMBLY_NOT_AUTHORIZED", "HEADER_BINDING_NOT_AUTHORIZED", "AUTHENTICATION_NOT_AUTHORIZED",
    "TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED", "REQUEST_METHOD_NOT_ALLOWED",
    "HTTPS_REQUIRED", "TRANSPORT_SCHEME_NOT_ALLOWED", "CONTENT_TYPE_NOT_ALLOWED", "ACCEPT_TYPE_NOT_ALLOWED",
    "AUTHENTICATION_FIELD_NAME_INVALID", "HEADER_NAME_INVALID", "HEADER_NAME_NOT_ALLOWED",
    "PROHIBITED_HEADER_PRESENT", "DUPLICATE_HEADER_NAME", "HEADER_COUNT_INVALID",
    "HEADER_NAME_LENGTH_INVALID", "REQUEST_ID_HEADER_REQUIRED", "IDEMPOTENCY_HEADER_REQUIRED",
    "CONTENT_TYPE_HEADER_REQUIRED", "ACCEPT_HEADER_REQUIRED", "BODY_LENGTH_INVALID", "BODY_LENGTH_EXCEEDED",
    "HEADER_BINDER_REQUIRED", "HEADER_BINDER_INVOCATION_FAILED", "HEADER_BINDING_FAILED",
    "HEADER_VALUE_EXPOSURE_DETECTED", "RAW_SECRET_EXPOSURE_DETECTED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "RAW_BODY_EXPOSURE_DETECTED", "RAW_ENDPOINT_EXPOSURE_DETECTED",
    "REQUEST_DESCRIPTOR_CONSTRUCTION_FAILED", "RETRY_NOT_AUTHORIZED", "REDIRECT_NOT_AUTHORIZED",
    "FALLBACK_ROUTE_NOT_AUTHORIZED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


class _RedactedBoundHeader:
    def __repr__(self) -> str:
        return "_RedactedBoundHeader(REDACTED)"


class _FakeHeaderBinder:
    def __init__(self) -> None:
        self.calls = 0

    def bind_header(self, authentication_envelope_id: str, field_name: str, consumer: object) -> object:
        self.calls += 1
        assert authentication_envelope_id == "authentication-envelope-v1"
        assert field_name == "X-Provider-Key"
        return consumer(_RedactedBoundHeader())  # type: ignore[operator]


def _policy(**overrides: object) -> AuthenticatedProviderRequestPolicyV1:
    values = {
        "policy_id": "authenticated-request-policy-v1", "policy_version": "V1", "provider_id": "provider-v1",
        "request_method": "POST", "allowed_methods": ("POST",), "transport_scheme": "HTTPS",
        "require_https": True, "allowed_content_types": ("application/json",),
        "allowed_accept_types": ("application/json",), "authentication_scheme": "API_KEY",
        "authentication_location": "HEADER", "authentication_field_name": "X-Provider-Key",
        "allowed_header_names": ("X-Provider-Key", "X-Request-Id", "Idempotency-Key", "Content-Type", "Accept"),
        "prohibited_header_names": ("Cookie", "Proxy-Authorization"), "require_request_id_header": True,
        "request_id_header_name": "X-Request-Id", "require_idempotency_header": True,
        "idempotency_header_name": "Idempotency-Key", "require_content_type_header": True,
        "content_type_header_name": "Content-Type", "require_accept_header": True,
        "accept_header_name": "Accept", "maximum_header_count": 5, "maximum_header_name_length": 64,
        "maximum_body_bytes": 1024, "maximum_attempts": 0, "maximum_redirects": 0, "retry_allowed": False,
        "fallback_route_allowed": False, "header_binding_authorized": True, "request_assembly_authorized": True,
        "authentication_authorized": True, "transmission_authorized": False,
        "provider_execution_authorized": False, "fail_closed": True,
    }
    values.update(overrides)
    return AuthenticatedProviderRequestPolicyV1(**values)


def _binding(**overrides: object) -> AuthenticatedProviderRequestBindingV1:
    values = {
        "binding_id": "authenticated-request-binding-v1", "provider_id": "provider-v1",
        "request_route_id": "provider-route-v1", "endpoint_configuration_id": "endpoint-config-v1",
        "connectivity_preflight_request_id": "connectivity-preflight-v1",
        "authentication_request_id": "authentication-request-v1",
        "authentication_envelope_id": "authentication-envelope-v1",
        "authentication_policy_id": "authentication-policy-v1", "credential_binding_id": "credential-binding-v1",
        "credential_reference_id": "credential-reference-v1", "provider_request_id": "provider-request-v1",
        "provider_request_payload_identity": "payload-identity-v1", "reservation_id": "reservation-v1",
        "persistence_command_id": "persistence-command-v1", "idempotency_key": "idempotency-key-v1",
        "pricing_evidence_id": "pricing-evidence-v1", "request_construction_policy_id": "request-policy-v1",
        "authenticated_request_policy_id": "authenticated-request-policy-v1", "binding_verified": True,
        "connectivity_metadata_ready": True, "authentication_envelope_constructed": True,
        "reservation_persisted": True, "persistence_recovery_clear": True,
        "request_assembly_authorized": True, "transmission_authorized": False,
        "provider_execution_authorized": False,
    }
    values.update(overrides)
    return AuthenticatedProviderRequestBindingV1(**values)


def _assembly(**overrides: object) -> AuthenticatedProviderRequestAssemblyRequestV1:
    values = {
        "assembly_request_id": "authenticated-assembly-request-v1", "binding_id": "authenticated-request-binding-v1",
        "provider_id": "provider-v1", "request_route_id": "provider-route-v1",
        "endpoint_configuration_id": "endpoint-config-v1", "connectivity_preflight_request_id": "connectivity-preflight-v1",
        "authentication_request_id": "authentication-request-v1", "authentication_envelope_id": "authentication-envelope-v1",
        "provider_request_id": "provider-request-v1", "provider_request_payload_identity": "payload-identity-v1",
        "reservation_id": "reservation-v1", "persistence_command_id": "persistence-command-v1",
        "idempotency_key": "idempotency-key-v1", "requested_at": _NOW, "binding_valid": True,
        "provider_request_constructed": True, "pricing_revalidated": True, "reservation_persisted": True,
        "persistence_recovery_clear": True, "connectivity_metadata_ready": True,
        "authentication_envelope_constructed": True, "request_assembly_authorized": True,
    }
    values.update(overrides)
    return AuthenticatedProviderRequestAssemblyRequestV1(**values)


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_narrow_and_redacted() -> None:
    assert tuple(field.name for field in fields(AuthenticatedProviderRequestPolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(AuthenticatedProviderRequestBindingV1)) == _BINDING_FIELDS
    assert tuple(field.name for field in fields(AuthenticatedProviderRequestAssemblyRequestV1)) == _REQUEST_FIELDS
    assert tuple(field.name for field in fields(AuthenticatedProviderRequestDescriptorV1)) == _DESCRIPTOR_FIELDS
    assert tuple(field.name for field in fields(AuthenticatedProviderRequestAssemblyResultV1)) == _RESULT_FIELDS
    assert tuple(field.name for field in fields(AuthenticatedProviderRequestAuditEvidenceV1)) == _AUDIT_FIELDS
    assert tuple(field.name for field in fields(AuthenticatedProviderRequestFailureV1)) == _FAILURE_FIELDS
    assert {"bind_header"}.issubset(dir(ProviderAuthenticationHeaderBinderV1))
    assert not {"headers", "authorization", "serialize", "send", "post", "request"}.intersection(
        dir(ProviderAuthenticationHeaderBinderV1)
    )
    result = assemble_authenticated_provider_request_v1(_policy(), _binding(), _assembly(), None)
    evidence = build_authenticated_provider_request_audit_evidence_v1(_policy(), _binding(), _assembly(), result)
    for value in (_policy(), _binding(), _assembly(), result, evidence):
        _frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        _policy().request_assembly_authorized = False  # type: ignore[misc]


def test_invalid_preconditions_fail_before_fake_header_binder() -> None:
    binder = _FakeHeaderBinder()
    result = assemble_authenticated_provider_request_v1(
        _policy(header_binding_authorized=False, authentication_authorized=False),
        _binding(binding_verified=False, reservation_persisted=False),
        _assembly(provider_request_constructed=False, pricing_revalidated=False, persistence_recovery_clear=False),
        binder,
    )
    assert {
        "BINDING_NOT_VERIFIED", "PROVIDER_REQUEST_NOT_CONSTRUCTED", "PRICING_NOT_REVALIDATED",
        "RESERVATION_NOT_PERSISTED", "PERSISTENCE_RECOVERY_UNRESOLVED",
        "HEADER_BINDING_NOT_AUTHORIZED", "AUTHENTICATION_NOT_AUTHORIZED",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert binder.calls == 0
    assert (result.header_binder_invoked, result.header_value_bound, result.descriptor_constructed,
            result.authenticated, result.transmitted, result.provider_executed, result.retry_attempted,
            result.redirect_attempted, result.fallback_attempted) == (False,) * 9


def test_fake_single_use_header_binding_builds_only_a_redacted_descriptor() -> None:
    binder = _FakeHeaderBinder()
    result = assemble_authenticated_provider_request_v1(_policy(), _binding(), _assembly(), binder)
    assert result.accepted is True and result.descriptor_constructed is True
    assert binder.calls == 1
    assert result.descriptor is not None
    assert result.descriptor.ordered_header_names == (
        "X-Provider-Key", "X-Request-Id", "Idempotency-Key", "Content-Type", "Accept",
    )
    assert "_RedactedBoundHeader" not in repr(result.descriptor)
    assert (result.authenticated, result.transmitted, result.provider_executed, result.retry_attempted,
            result.redirect_attempted, result.fallback_attempted) == (False,) * 6


def test_audit_is_identity_bound_deterministic_and_does_not_bind_again() -> None:
    binder = _FakeHeaderBinder()
    policy, binding, assembly = _policy(), _binding(), _assembly()
    result = assemble_authenticated_provider_request_v1(policy, binding, assembly, binder)
    evidence = build_authenticated_provider_request_audit_evidence_v1(policy, binding, assembly, result)
    assert evidence == build_authenticated_provider_request_audit_evidence_v1(policy, binding, assembly, result)
    assert binder.calls == 1
    assert evidence.authenticated is evidence.transmitted is evidence.provider_executed is False
    with pytest.raises(ValueError):
        build_authenticated_provider_request_audit_evidence_v1(
            policy, _binding(provider_id="other-provider-v1"), assembly, result,
        )
