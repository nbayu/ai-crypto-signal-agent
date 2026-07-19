"""RED contract for one fake-only, redacted provider transmission attempt."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime

import pytest

from engine.phase_12_provider_transmission_attempt_contract_v1 import (
    ProviderTransmissionAttemptRequestV1,
    ProviderTransmissionAttemptResultV1,
    ProviderTransmissionAuditEvidenceV1,
    ProviderTransmissionBindingV1,
    ProviderTransmissionFailureV1,
    ProviderTransmissionPolicyV1,
    ProviderTransmissionResponseEnvelopeV1,
    ProviderTransmissionTransportV1,
    attempt_provider_transmission_v1,
    build_provider_transmission_audit_evidence_v1,
)


_NOW = datetime(2030, 1, 5, 12, 0, tzinfo=UTC)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "provider_id", "request_method", "transport_scheme",
    "allowed_provider_ids", "allowed_methods", "allowed_transport_schemes", "allowed_status_codes",
    "maximum_response_bytes", "connect_timeout_seconds", "response_timeout_seconds",
    "total_timeout_seconds", "maximum_attempts", "maximum_redirects", "require_confirmed_reservation",
    "require_confirmed_persistence", "require_connectivity_metadata", "require_authentication_envelope",
    "require_authenticated_request_descriptor", "require_request_redaction", "require_response_redaction",
    "transport_invocation_authorized", "transmission_attempt_authorized", "provider_execution_authorized",
    "retry_allowed", "redirect_allowed", "fallback_allowed", "fail_closed",
)
_BINDING_FIELDS = (
    "binding_id", "provider_id", "request_route_id", "endpoint_configuration_id",
    "connectivity_preflight_request_id", "authentication_request_id", "authentication_envelope_id",
    "authenticated_request_descriptor_id", "provider_request_id", "payload_identity", "reservation_id",
    "persistence_command_id", "idempotency_key", "transmission_policy_id", "request_assembly_policy_id",
    "binding_verified", "reservation_confirmed", "persistence_confirmed", "persistence_recovery_clear",
    "connectivity_metadata_ready", "authentication_envelope_constructed", "request_descriptor_constructed",
    "transmission_attempt_authorized", "provider_execution_authorized",
)
_REQUEST_FIELDS = (
    "transmission_attempt_id", "binding_id", "provider_id", "request_route_id", "endpoint_configuration_id",
    "authenticated_request_descriptor_id", "provider_request_id", "payload_identity", "reservation_id",
    "persistence_command_id", "idempotency_key", "requested_at", "binding_valid", "reservation_confirmed",
    "persistence_confirmed", "persistence_recovery_clear", "connectivity_metadata_ready",
    "authentication_envelope_constructed", "request_descriptor_constructed", "transport_invocation_authorized",
    "transmission_attempt_authorized",
)
_RESPONSE_FIELDS = (
    "response_envelope_id", "transmission_attempt_id", "provider_id", "provider_request_id",
    "response_classification", "status_code", "response_body_identity", "response_body_length",
    "provider_request_reference_id", "received_at", "response_received", "provider_acknowledged",
    "provider_executed", "retryable", "redaction_valid",
)
_RESULT_FIELDS = (
    "transmission_attempt_id", "binding_id", "policy_id", "accepted", "failure_codes",
    "outcome_classification", "policy_valid", "binding_valid", "upstream_evidence_valid",
    "transport_invoked", "attempted", "response_received", "provider_acknowledged", "provider_executed",
    "response_redaction_valid", "retry_attempted", "redirect_attempted", "fallback_attempted",
    "recovery_required",
)
_AUDIT_FIELDS = (
    "transmission_attempt_id", "binding_id", "policy_id", "provider_id", "request_route_id",
    "endpoint_configuration_id", "authenticated_request_descriptor_id", "provider_request_id",
    "payload_identity", "reservation_id", "persistence_command_id", "idempotency_key",
    "transport_invocation_count", "attempted", "outcome_classification", "response_envelope_id",
    "response_body_identity", "response_body_length", "provider_acknowledged", "recovery_required",
    "failure_codes", "provider_executed", "retry_attempted", "redirect_attempted", "fallback_attempted",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_FAILURES = {
    "TRANSMISSION_ATTEMPT_ID_EMPTY", "BINDING_ID_EMPTY", "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY",
    "PROVIDER_ID_EMPTY", "REQUEST_ROUTE_ID_EMPTY", "ENDPOINT_CONFIGURATION_ID_EMPTY",
    "AUTHENTICATED_REQUEST_DESCRIPTOR_ID_EMPTY", "PROVIDER_REQUEST_ID_EMPTY", "PAYLOAD_IDENTITY_EMPTY",
    "RESERVATION_ID_EMPTY", "PERSISTENCE_COMMAND_ID_EMPTY", "IDEMPOTENCY_KEY_EMPTY",
    "IDENTIFIER_NOT_NORMALIZED", "POLICY_IDENTITY_MISMATCH", "BINDING_IDENTITY_MISMATCH",
    "PROVIDER_IDENTITY_MISMATCH", "ROUTE_IDENTITY_MISMATCH", "ENDPOINT_IDENTITY_MISMATCH",
    "REQUEST_DESCRIPTOR_IDENTITY_MISMATCH", "PROVIDER_REQUEST_IDENTITY_MISMATCH", "PAYLOAD_IDENTITY_MISMATCH",
    "RESERVATION_IDENTITY_MISMATCH", "PERSISTENCE_COMMAND_IDENTITY_MISMATCH", "IDEMPOTENCY_IDENTITY_MISMATCH",
    "BINDING_NOT_VERIFIED", "RESERVATION_NOT_CONFIRMED", "PERSISTENCE_NOT_CONFIRMED",
    "PERSISTENCE_RECOVERY_UNRESOLVED", "CONNECTIVITY_METADATA_NOT_READY",
    "AUTHENTICATION_ENVELOPE_NOT_CONSTRUCTED", "REQUEST_DESCRIPTOR_NOT_CONSTRUCTED",
    "TRANSPORT_INVOCATION_NOT_AUTHORIZED", "TRANSMISSION_ATTEMPT_NOT_AUTHORIZED",
    "PROVIDER_EXECUTION_NOT_AUTHORIZED", "PROVIDER_NOT_ALLOWED", "REQUEST_METHOD_NOT_ALLOWED",
    "TRANSPORT_SCHEME_NOT_ALLOWED", "TIMEOUT_INVALID", "TIMEOUT_ORDER_INVALID", "ATTEMPT_LIMIT_ZERO",
    "REDIRECT_NOT_AUTHORIZED", "RETRY_NOT_AUTHORIZED", "FALLBACK_NOT_AUTHORIZED", "TRANSPORT_REQUIRED",
    "TRANSPORT_INVOCATION_FAILED", "TRANSPORT_INVOKED_MORE_THAN_ONCE", "RESPONSE_ENVELOPE_MISSING",
    "RESPONSE_ENVELOPE_INVALID", "RESPONSE_IDENTITY_MISMATCH", "STATUS_CODE_INVALID",
    "STATUS_CODE_NOT_ALLOWED", "RESPONSE_BODY_LENGTH_INVALID", "RESPONSE_BODY_LENGTH_EXCEEDED",
    "RESPONSE_REDACTION_INVALID", "ATTEMPT_OUTCOME_UNCERTAIN", "RAW_REQUEST_EXPOSURE_DETECTED",
    "RAW_RESPONSE_EXPOSURE_DETECTED", "RAW_SECRET_EXPOSURE_DETECTED", "RAW_HEADER_EXPOSURE_DETECTED",
    "RAW_ENDPOINT_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


class _FakeResponseEnvelope:
    def __init__(self, classification: str = "FAKE_ACCEPTED") -> None:
        self.response_envelope_id = "fake-response-envelope-v1"
        self.transmission_attempt_id = "transmission-attempt-v1"
        self.provider_id = "provider-v1"
        self.provider_request_id = "provider-request-v1"
        self.response_classification = classification
        self.status_code = 202
        self.response_body_identity = "fake-response-body-identity-v1"
        self.response_body_length = 32
        self.provider_request_reference_id = "provider-request-v1"
        self.received_at = _NOW
        self.response_received = True
        self.provider_acknowledged = classification == "FAKE_ACCEPTED"
        self.provider_executed = False
        self.retryable = False
        self.redaction_valid = True

    def __repr__(self) -> str:
        return "_FakeResponseEnvelope(REDACTED)"


class _FakeTransport:
    def __init__(self, response: _FakeResponseEnvelope) -> None:
        self.response = response
        self.calls = 0

    def attempt(self, transmission: object, consumer: object) -> object:
        self.calls += 1
        return consumer(self.response)  # type: ignore[operator]


def _policy(**overrides: object) -> ProviderTransmissionPolicyV1:
    values = {
        "policy_id": "transmission-policy-v1", "policy_version": "V1", "provider_id": "provider-v1",
        "request_method": "POST", "transport_scheme": "HTTPS", "allowed_provider_ids": ("provider-v1",),
        "allowed_methods": ("POST",), "allowed_transport_schemes": ("HTTPS",),
        "allowed_status_codes": (202,), "maximum_response_bytes": 1024, "connect_timeout_seconds": 5,
        "response_timeout_seconds": 5, "total_timeout_seconds": 20, "maximum_attempts": 1,
        "maximum_redirects": 0, "require_confirmed_reservation": True, "require_confirmed_persistence": True,
        "require_connectivity_metadata": True, "require_authentication_envelope": True,
        "require_authenticated_request_descriptor": True, "require_request_redaction": True,
        "require_response_redaction": True, "transport_invocation_authorized": True,
        "transmission_attempt_authorized": True, "provider_execution_authorized": False,
        "retry_allowed": False, "redirect_allowed": False, "fallback_allowed": False, "fail_closed": True,
    }
    values.update(overrides)
    return ProviderTransmissionPolicyV1(**values)


def _binding(**overrides: object) -> ProviderTransmissionBindingV1:
    values = {
        "binding_id": "transmission-binding-v1", "provider_id": "provider-v1",
        "request_route_id": "provider-route-v1", "endpoint_configuration_id": "endpoint-config-v1",
        "connectivity_preflight_request_id": "connectivity-preflight-v1",
        "authentication_request_id": "authentication-request-v1",
        "authentication_envelope_id": "authentication-envelope-v1",
        "authenticated_request_descriptor_id": "authenticated-request-descriptor-v1",
        "provider_request_id": "provider-request-v1", "payload_identity": "payload-identity-v1",
        "reservation_id": "reservation-v1", "persistence_command_id": "persistence-command-v1",
        "idempotency_key": "idempotency-key-v1", "transmission_policy_id": "transmission-policy-v1",
        "request_assembly_policy_id": "authenticated-request-policy-v1", "binding_verified": True,
        "reservation_confirmed": True, "persistence_confirmed": True, "persistence_recovery_clear": True,
        "connectivity_metadata_ready": True, "authentication_envelope_constructed": True,
        "request_descriptor_constructed": True, "transmission_attempt_authorized": True,
        "provider_execution_authorized": False,
    }
    values.update(overrides)
    return ProviderTransmissionBindingV1(**values)


def _attempt(**overrides: object) -> ProviderTransmissionAttemptRequestV1:
    values = {
        "transmission_attempt_id": "transmission-attempt-v1", "binding_id": "transmission-binding-v1",
        "provider_id": "provider-v1", "request_route_id": "provider-route-v1",
        "endpoint_configuration_id": "endpoint-config-v1",
        "authenticated_request_descriptor_id": "authenticated-request-descriptor-v1",
        "provider_request_id": "provider-request-v1", "payload_identity": "payload-identity-v1",
        "reservation_id": "reservation-v1", "persistence_command_id": "persistence-command-v1",
        "idempotency_key": "idempotency-key-v1", "requested_at": _NOW, "binding_valid": True,
        "reservation_confirmed": True, "persistence_confirmed": True, "persistence_recovery_clear": True,
        "connectivity_metadata_ready": True, "authentication_envelope_constructed": True,
        "request_descriptor_constructed": True, "transport_invocation_authorized": True,
        "transmission_attempt_authorized": True,
    }
    values.update(overrides)
    return ProviderTransmissionAttemptRequestV1(**values)


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_narrow_and_transport_free() -> None:
    assert tuple(field.name for field in fields(ProviderTransmissionPolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(ProviderTransmissionBindingV1)) == _BINDING_FIELDS
    assert tuple(field.name for field in fields(ProviderTransmissionAttemptRequestV1)) == _REQUEST_FIELDS
    assert tuple(field.name for field in fields(ProviderTransmissionResponseEnvelopeV1)) == _RESPONSE_FIELDS
    assert tuple(field.name for field in fields(ProviderTransmissionAttemptResultV1)) == _RESULT_FIELDS
    assert tuple(field.name for field in fields(ProviderTransmissionAuditEvidenceV1)) == _AUDIT_FIELDS
    assert tuple(field.name for field in fields(ProviderTransmissionFailureV1)) == _FAILURE_FIELDS
    assert {"attempt"}.issubset(dir(ProviderTransmissionTransportV1))
    assert not {"get", "post", "send", "request", "headers", "socket", "session"}.intersection(
        dir(ProviderTransmissionTransportV1)
    )
    result = attempt_provider_transmission_v1(_policy(), _binding(), _attempt(), None)
    evidence = build_provider_transmission_audit_evidence_v1(_policy(), _binding(), _attempt(), result)
    for value in (_policy(), _binding(), _attempt(), result, evidence):
        _frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        _policy().transport_invocation_authorized = False  # type: ignore[misc]


def test_failed_preconditions_do_not_invoke_fake_transport() -> None:
    transport = _FakeTransport(_FakeResponseEnvelope())
    result = attempt_provider_transmission_v1(
        _policy(transport_invocation_authorized=False),
        _binding(binding_verified=False, reservation_confirmed=False),
        _attempt(persistence_confirmed=False, persistence_recovery_clear=False),
        transport,
    )
    assert {
        "BINDING_NOT_VERIFIED", "RESERVATION_NOT_CONFIRMED", "PERSISTENCE_NOT_CONFIRMED",
        "PERSISTENCE_RECOVERY_UNRESOLVED", "TRANSPORT_INVOCATION_NOT_AUTHORIZED",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert transport.calls == 0
    assert (result.transport_invoked, result.attempted, result.response_received, result.provider_acknowledged,
            result.provider_executed, result.retry_attempted, result.redirect_attempted,
            result.fallback_attempted) == (False,) * 8


def test_one_fake_accepted_attempt_is_redacted_and_non_executing() -> None:
    transport = _FakeTransport(_FakeResponseEnvelope())
    result = attempt_provider_transmission_v1(_policy(), _binding(), _attempt(), transport)
    assert result.accepted is True and result.outcome_classification == "FAKE_ACCEPTED"
    assert transport.calls == 1
    assert (result.transport_invoked, result.attempted, result.response_received,
            result.provider_acknowledged) == (True,) * 4
    assert (result.provider_executed, result.retry_attempted, result.redirect_attempted,
            result.fallback_attempted, result.recovery_required) == (False,) * 5


def test_uncertain_fake_outcome_requires_recovery_without_reinvocation() -> None:
    transport = _FakeTransport(_FakeResponseEnvelope("ATTEMPT_OUTCOME_UNCERTAIN"))
    result = attempt_provider_transmission_v1(_policy(), _binding(), _attempt(), transport)
    assert result.accepted is False
    assert result.outcome_classification == "ATTEMPT_OUTCOME_UNCERTAIN"
    assert "ATTEMPT_OUTCOME_UNCERTAIN" in result.failure_codes
    assert result.recovery_required is True and transport.calls == 1


def test_audit_is_identity_bound_deterministic_and_never_reinvokes_transport() -> None:
    transport = _FakeTransport(_FakeResponseEnvelope())
    policy, binding, attempt = _policy(), _binding(), _attempt()
    result = attempt_provider_transmission_v1(policy, binding, attempt, transport)
    evidence = build_provider_transmission_audit_evidence_v1(policy, binding, attempt, result)
    assert evidence == build_provider_transmission_audit_evidence_v1(policy, binding, attempt, result)
    assert transport.calls == 1
    assert evidence.provider_executed is evidence.retry_attempted is evidence.redirect_attempted is False
    with pytest.raises(ValueError):
        build_provider_transmission_audit_evidence_v1(policy, _binding(provider_id="other-provider-v1"), attempt, result)
