"""Pure, fake-only, redacted provider transmission-attempt boundary."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderTransmissionPolicyV1:
    policy_id: str = ""; policy_version: str = ""; provider_id: str = ""; request_method: str = ""; transport_scheme: str = ""; allowed_provider_ids: tuple = (); allowed_methods: tuple = (); allowed_transport_schemes: tuple = (); allowed_status_codes: tuple = (); maximum_response_bytes: int = 0; connect_timeout_seconds: int = 0; response_timeout_seconds: int = 0; total_timeout_seconds: int = 0; maximum_attempts: int = 0; maximum_redirects: int = 0; require_confirmed_reservation: bool = True; require_confirmed_persistence: bool = True; require_connectivity_metadata: bool = True; require_authentication_envelope: bool = True; require_authenticated_request_descriptor: bool = True; require_request_redaction: bool = True; require_response_redaction: bool = True; transport_invocation_authorized: bool = False; transmission_attempt_authorized: bool = False; provider_execution_authorized: bool = False; retry_allowed: bool = False; redirect_allowed: bool = False; fallback_allowed: bool = False; fail_closed: bool = True

    def __post_init__(self) -> None:
        if not all(isinstance(value, tuple) for value in (self.allowed_provider_ids, self.allowed_methods, self.allowed_transport_schemes, self.allowed_status_codes)):
            raise ValueError("immutable policy collections required")


@dataclass(frozen=True, slots=True)
class ProviderTransmissionBindingV1:
    binding_id: str = ""; provider_id: str = ""; request_route_id: str = ""; endpoint_configuration_id: str = ""; connectivity_preflight_request_id: str = ""; authentication_request_id: str = ""; authentication_envelope_id: str = ""; authenticated_request_descriptor_id: str = ""; provider_request_id: str = ""; payload_identity: str = ""; reservation_id: str = ""; persistence_command_id: str = ""; idempotency_key: str = ""; transmission_policy_id: str = ""; request_assembly_policy_id: str = ""; binding_verified: bool = False; reservation_confirmed: bool = False; persistence_confirmed: bool = False; persistence_recovery_clear: bool = False; connectivity_metadata_ready: bool = False; authentication_envelope_constructed: bool = False; request_descriptor_constructed: bool = False; transmission_attempt_authorized: bool = False; provider_execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ProviderTransmissionAttemptRequestV1:
    transmission_attempt_id: str = ""; binding_id: str = ""; provider_id: str = ""; request_route_id: str = ""; endpoint_configuration_id: str = ""; authenticated_request_descriptor_id: str = ""; provider_request_id: str = ""; payload_identity: str = ""; reservation_id: str = ""; persistence_command_id: str = ""; idempotency_key: str = ""; requested_at: datetime | None = None; binding_valid: bool = False; reservation_confirmed: bool = False; persistence_confirmed: bool = False; persistence_recovery_clear: bool = False; connectivity_metadata_ready: bool = False; authentication_envelope_constructed: bool = False; request_descriptor_constructed: bool = False; transport_invocation_authorized: bool = False; transmission_attempt_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ProviderTransmissionFailureV1:
    failure_code: str; safe_message: str; retryable: bool


@dataclass(frozen=True, slots=True)
class ProviderTransmissionResponseEnvelopeV1:
    response_envelope_id: str; transmission_attempt_id: str; provider_id: str; provider_request_id: str; response_classification: str; status_code: int; response_body_identity: str; response_body_length: int; provider_request_reference_id: str; received_at: datetime; response_received: bool; provider_acknowledged: bool; provider_executed: bool; retryable: bool; redaction_valid: bool


@dataclass(frozen=True, slots=True)
class ProviderTransmissionAttemptResultV1:
    transmission_attempt_id: str; binding_id: str; policy_id: str; accepted: bool; failure_codes: tuple[str, ...]; outcome_classification: str; policy_valid: bool; binding_valid: bool; upstream_evidence_valid: bool; transport_invoked: bool; attempted: bool; response_received: bool; provider_acknowledged: bool; provider_executed: bool; response_redaction_valid: bool; retry_attempted: bool; redirect_attempted: bool; fallback_attempted: bool; recovery_required: bool


@dataclass(frozen=True, slots=True)
class ProviderTransmissionAuditEvidenceV1:
    transmission_attempt_id: str; binding_id: str; policy_id: str; provider_id: str; request_route_id: str; endpoint_configuration_id: str; authenticated_request_descriptor_id: str; provider_request_id: str; payload_identity: str; reservation_id: str; persistence_command_id: str; idempotency_key: str; transport_invocation_count: int; attempted: bool; outcome_classification: str; response_envelope_id: str; response_body_identity: str; response_body_length: int; provider_acknowledged: bool; recovery_required: bool; failure_codes: tuple[str, ...]; provider_executed: bool; retry_attempted: bool; redirect_attempted: bool; fallback_attempted: bool


class ProviderTransmissionTransportV1(Protocol):
    def attempt(self, transmission: object, consumer: object) -> object: ...


def _ident(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and not any(c.isspace() for c in value)


def _codes(policy: ProviderTransmissionPolicyV1, binding: ProviderTransmissionBindingV1, request: ProviderTransmissionAttemptRequestV1) -> tuple[str, ...]:
    codes: list[str] = []
    names = ((request.transmission_attempt_id, "TRANSMISSION_ATTEMPT_ID_EMPTY"), (binding.binding_id, "BINDING_ID_EMPTY"), (policy.policy_id, "POLICY_ID_EMPTY"), (policy.policy_version, "POLICY_VERSION_EMPTY"), (request.provider_id, "PROVIDER_ID_EMPTY"), (request.request_route_id, "REQUEST_ROUTE_ID_EMPTY"), (request.endpoint_configuration_id, "ENDPOINT_CONFIGURATION_ID_EMPTY"), (request.authenticated_request_descriptor_id, "AUTHENTICATED_REQUEST_DESCRIPTOR_ID_EMPTY"), (request.provider_request_id, "PROVIDER_REQUEST_ID_EMPTY"), (request.payload_identity, "PAYLOAD_IDENTITY_EMPTY"), (request.reservation_id, "RESERVATION_ID_EMPTY"), (request.persistence_command_id, "PERSISTENCE_COMMAND_ID_EMPTY"), (request.idempotency_key, "IDEMPOTENCY_KEY_EMPTY"))
    codes.extend(code for value, code in names if not _ident(value))
    if binding.transmission_policy_id != policy.policy_id: codes.append("POLICY_IDENTITY_MISMATCH")
    checks = ((binding.binding_id, request.binding_id, "BINDING_IDENTITY_MISMATCH"), (binding.provider_id, request.provider_id, "PROVIDER_IDENTITY_MISMATCH"), (binding.request_route_id, request.request_route_id, "ROUTE_IDENTITY_MISMATCH"), (binding.endpoint_configuration_id, request.endpoint_configuration_id, "ENDPOINT_IDENTITY_MISMATCH"), (binding.authenticated_request_descriptor_id, request.authenticated_request_descriptor_id, "REQUEST_DESCRIPTOR_IDENTITY_MISMATCH"), (binding.provider_request_id, request.provider_request_id, "PROVIDER_REQUEST_IDENTITY_MISMATCH"), (binding.payload_identity, request.payload_identity, "PAYLOAD_IDENTITY_MISMATCH"), (binding.reservation_id, request.reservation_id, "RESERVATION_IDENTITY_MISMATCH"), (binding.persistence_command_id, request.persistence_command_id, "PERSISTENCE_COMMAND_IDENTITY_MISMATCH"), (binding.idempotency_key, request.idempotency_key, "IDEMPOTENCY_IDENTITY_MISMATCH"))
    codes.extend(code for left, right, code in checks if left != right)
    if policy.provider_id != binding.provider_id or policy.provider_id != request.provider_id: codes.append("PROVIDER_IDENTITY_MISMATCH")
    for valid, code in ((binding.binding_verified and request.binding_valid, "BINDING_NOT_VERIFIED"), (binding.reservation_confirmed and request.reservation_confirmed, "RESERVATION_NOT_CONFIRMED"), (binding.persistence_confirmed and request.persistence_confirmed, "PERSISTENCE_NOT_CONFIRMED"), (binding.persistence_recovery_clear and request.persistence_recovery_clear, "PERSISTENCE_RECOVERY_UNRESOLVED"), (binding.connectivity_metadata_ready and request.connectivity_metadata_ready, "CONNECTIVITY_METADATA_NOT_READY"), (binding.authentication_envelope_constructed and request.authentication_envelope_constructed, "AUTHENTICATION_ENVELOPE_NOT_CONSTRUCTED"), (binding.request_descriptor_constructed and request.request_descriptor_constructed, "REQUEST_DESCRIPTOR_NOT_CONSTRUCTED"), (policy.transport_invocation_authorized and request.transport_invocation_authorized, "TRANSPORT_INVOCATION_NOT_AUTHORIZED"), (policy.transmission_attempt_authorized and binding.transmission_attempt_authorized and request.transmission_attempt_authorized, "TRANSMISSION_ATTEMPT_NOT_AUTHORIZED")):
        if not valid: codes.append(code)
    if policy.provider_id not in policy.allowed_provider_ids: codes.append("PROVIDER_NOT_ALLOWED")
    if policy.request_method not in policy.allowed_methods: codes.append("REQUEST_METHOD_NOT_ALLOWED")
    if policy.transport_scheme not in policy.allowed_transport_schemes: codes.append("TRANSPORT_SCHEME_NOT_ALLOWED")
    timeout_values = (policy.connect_timeout_seconds, policy.response_timeout_seconds, policy.total_timeout_seconds)
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in timeout_values): codes.append("TIMEOUT_INVALID")
    elif policy.total_timeout_seconds < policy.connect_timeout_seconds + policy.response_timeout_seconds: codes.append("TIMEOUT_ORDER_INVALID")
    if policy.maximum_attempts != 1: codes.append("ATTEMPT_LIMIT_ZERO")
    if policy.maximum_redirects != 0 or policy.redirect_allowed: codes.append("REDIRECT_NOT_AUTHORIZED")
    if policy.retry_allowed: codes.append("RETRY_NOT_AUTHORIZED")
    if policy.fallback_allowed: codes.append("FALLBACK_NOT_AUTHORIZED")
    return tuple(sorted(set(codes)))


def _result(policy: ProviderTransmissionPolicyV1, binding: ProviderTransmissionBindingV1, request: ProviderTransmissionAttemptRequestV1, codes: tuple[str, ...], classification: str = "NOT_ATTEMPTED", invoked: bool = False, received: bool = False, acknowledged: bool = False, redacted: bool = False, recovery: bool = False) -> ProviderTransmissionAttemptResultV1:
    accepted = classification == "FAKE_ACCEPTED" and not codes and acknowledged
    return ProviderTransmissionAttemptResultV1(request.transmission_attempt_id, binding.binding_id, policy.policy_id, accepted, tuple(sorted(set(codes))), classification, not any(c in codes for c in ("POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY")), "BINDING_NOT_VERIFIED" not in codes, not any(c in codes for c in ("RESERVATION_NOT_CONFIRMED", "PERSISTENCE_NOT_CONFIRMED", "PERSISTENCE_RECOVERY_UNRESOLVED", "CONNECTIVITY_METADATA_NOT_READY")), invoked, invoked, received, acknowledged, False, redacted, False, False, False, recovery)


def _response_codes(response: object, policy: ProviderTransmissionPolicyV1, request: ProviderTransmissionAttemptRequestV1) -> tuple[str, ...]:
    required = ("response_envelope_id", "transmission_attempt_id", "provider_id", "provider_request_id", "response_classification", "status_code", "response_body_identity", "response_body_length", "provider_request_reference_id", "received_at", "response_received", "provider_acknowledged", "provider_executed", "redaction_valid")
    if response is None: return ("RESPONSE_ENVELOPE_MISSING",)
    if not all(hasattr(response, name) for name in required): return ("RESPONSE_ENVELOPE_INVALID",)
    codes: list[str] = []
    if getattr(response, "transmission_attempt_id") != request.transmission_attempt_id or getattr(response, "provider_id") != request.provider_id or getattr(response, "provider_request_id") != request.provider_request_id or getattr(response, "provider_request_reference_id") != request.provider_request_id: codes.append("RESPONSE_IDENTITY_MISMATCH")
    status, length = getattr(response, "status_code"), getattr(response, "response_body_length")
    if not isinstance(status, int) or isinstance(status, bool) or status < 100: codes.append("STATUS_CODE_INVALID")
    elif status not in policy.allowed_status_codes: codes.append("STATUS_CODE_NOT_ALLOWED")
    if not isinstance(length, int) or isinstance(length, bool) or length < 0: codes.append("RESPONSE_BODY_LENGTH_INVALID")
    elif length > policy.maximum_response_bytes: codes.append("RESPONSE_BODY_LENGTH_EXCEEDED")
    if not getattr(response, "redaction_valid") or getattr(response, "provider_executed"): codes.append("RESPONSE_REDACTION_INVALID")
    classification = getattr(response, "response_classification")
    if classification not in {"FAKE_ACCEPTED", "FAKE_REJECTED", "FAKE_TIMEOUT", "FAKE_TRANSPORT_FAILURE", "FAKE_RESPONSE_MALFORMED", "ATTEMPT_OUTCOME_UNCERTAIN"}: codes.append("RESPONSE_ENVELOPE_INVALID")
    return tuple(sorted(set(codes)))


def attempt_provider_transmission_v1(policy: ProviderTransmissionPolicyV1, binding: ProviderTransmissionBindingV1, request: ProviderTransmissionAttemptRequestV1, transport: ProviderTransmissionTransportV1 | None) -> ProviderTransmissionAttemptResultV1:
    codes = _codes(policy, binding, request)
    if codes: return _result(policy, binding, request, codes)
    if transport is None or not callable(getattr(transport, "attempt", None)): return _result(policy, binding, request, ("TRANSPORT_REQUIRED",))
    try: response = transport.attempt(request, lambda envelope: envelope)
    except Exception: return _result(policy, binding, request, ("TRANSPORT_INVOCATION_FAILED",), invoked=True)
    response_codes = _response_codes(response, policy, request)
    classification = getattr(response, "response_classification", "FAKE_RESPONSE_MALFORMED")
    if classification == "ATTEMPT_OUTCOME_UNCERTAIN":
        return _result(policy, binding, request, tuple(sorted(set(response_codes + ("ATTEMPT_OUTCOME_UNCERTAIN",)))), classification, True, bool(getattr(response, "response_received", False)), False, bool(getattr(response, "redaction_valid", False)), True)
    if response_codes: return _result(policy, binding, request, response_codes, "FAKE_RESPONSE_MALFORMED", True, bool(getattr(response, "response_received", False)), False, False)
    return _result(policy, binding, request, (), classification, True, bool(getattr(response, "response_received")), bool(getattr(response, "provider_acknowledged")), bool(getattr(response, "redaction_valid")))


def build_provider_transmission_audit_evidence_v1(policy: ProviderTransmissionPolicyV1, binding: ProviderTransmissionBindingV1, request: ProviderTransmissionAttemptRequestV1, result: ProviderTransmissionAttemptResultV1) -> ProviderTransmissionAuditEvidenceV1:
    if not isinstance(policy, ProviderTransmissionPolicyV1) or not isinstance(binding, ProviderTransmissionBindingV1) or not isinstance(request, ProviderTransmissionAttemptRequestV1) or not isinstance(result, ProviderTransmissionAttemptResultV1) or result.transmission_attempt_id != request.transmission_attempt_id or result.binding_id != binding.binding_id or result.policy_id != policy.policy_id or binding.provider_id != request.provider_id: raise ValueError("transmission evidence identity mismatch")
    return ProviderTransmissionAuditEvidenceV1(request.transmission_attempt_id, binding.binding_id, policy.policy_id, binding.provider_id, binding.request_route_id, binding.endpoint_configuration_id, binding.authenticated_request_descriptor_id, binding.provider_request_id, binding.payload_identity, binding.reservation_id, binding.persistence_command_id, binding.idempotency_key, int(result.transport_invoked), result.attempted, result.outcome_classification, "redacted-response-envelope-v1", "", 0, result.provider_acknowledged, result.recovery_required, result.failure_codes, False, False, False, False)
