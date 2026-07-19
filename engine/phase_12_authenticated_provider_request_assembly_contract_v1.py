"""Pure, fake-only, redacted authenticated provider-request assembly boundary."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AuthenticatedProviderRequestPolicyV1:
    policy_id: str = ""; policy_version: str = ""; provider_id: str = ""; request_method: str = ""; allowed_methods: tuple = (); transport_scheme: str = ""; require_https: bool = True; allowed_content_types: tuple = (); allowed_accept_types: tuple = (); authentication_scheme: str = ""; authentication_location: str = ""; authentication_field_name: str = ""; allowed_header_names: tuple = (); prohibited_header_names: tuple = (); require_request_id_header: bool = False; request_id_header_name: str = ""; require_idempotency_header: bool = False; idempotency_header_name: str = ""; require_content_type_header: bool = False; content_type_header_name: str = ""; require_accept_header: bool = False; accept_header_name: str = ""; maximum_header_count: int = 0; maximum_header_name_length: int = 0; maximum_body_bytes: int = 0; maximum_attempts: int = 0; maximum_redirects: int = 0; retry_allowed: bool = False; fallback_route_allowed: bool = False; header_binding_authorized: bool = False; request_assembly_authorized: bool = False; authentication_authorized: bool = False; transmission_authorized: bool = False; provider_execution_authorized: bool = False; fail_closed: bool = True

    def __post_init__(self) -> None:
        if not all(isinstance(value, tuple) for value in (
            self.allowed_methods, self.allowed_content_types, self.allowed_accept_types,
            self.allowed_header_names, self.prohibited_header_names,
        )):
            raise ValueError("immutable policy collections required")


@dataclass(frozen=True, slots=True)
class AuthenticatedProviderRequestBindingV1:
    binding_id: str = ""; provider_id: str = ""; request_route_id: str = ""; endpoint_configuration_id: str = ""; connectivity_preflight_request_id: str = ""; authentication_request_id: str = ""; authentication_envelope_id: str = ""; authentication_policy_id: str = ""; credential_binding_id: str = ""; credential_reference_id: str = ""; provider_request_id: str = ""; provider_request_payload_identity: str = ""; reservation_id: str = ""; persistence_command_id: str = ""; idempotency_key: str = ""; pricing_evidence_id: str = ""; request_construction_policy_id: str = ""; authenticated_request_policy_id: str = ""; binding_verified: bool = False; connectivity_metadata_ready: bool = False; authentication_envelope_constructed: bool = False; reservation_persisted: bool = False; persistence_recovery_clear: bool = False; request_assembly_authorized: bool = False; transmission_authorized: bool = False; provider_execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class AuthenticatedProviderRequestAssemblyRequestV1:
    assembly_request_id: str = ""; binding_id: str = ""; provider_id: str = ""; request_route_id: str = ""; endpoint_configuration_id: str = ""; connectivity_preflight_request_id: str = ""; authentication_request_id: str = ""; authentication_envelope_id: str = ""; provider_request_id: str = ""; provider_request_payload_identity: str = ""; reservation_id: str = ""; persistence_command_id: str = ""; idempotency_key: str = ""; requested_at: datetime | None = None; binding_valid: bool = False; provider_request_constructed: bool = False; pricing_revalidated: bool = False; reservation_persisted: bool = False; persistence_recovery_clear: bool = False; connectivity_metadata_ready: bool = False; authentication_envelope_constructed: bool = False; request_assembly_authorized: bool = False


@dataclass(frozen=True, slots=True)
class AuthenticatedProviderRequestFailureV1:
    failure_code: str; safe_message: str; retryable: bool


@dataclass(frozen=True, slots=True)
class AuthenticatedProviderRequestDescriptorV1:
    authenticated_request_descriptor_id: str; assembly_request_id: str; binding_id: str; policy_id: str; provider_id: str; request_route_id: str; endpoint_configuration_id: str; provider_request_id: str; payload_identity: str; body_length: int; request_method: str; transport_scheme: str; content_type: str; accept_type: str; ordered_header_names: tuple; authentication_field_name: str; request_id_header_name: str; idempotency_header_name: str; credential_reference_id: str; authentication_envelope_id: str; reservation_id: str; persistence_command_id: str; idempotency_key: str; header_binder_invoked: bool; header_value_bound: bool; descriptor_constructed: bool; redaction_valid: bool; authenticated: bool; transmitted: bool; provider_executed: bool; retry_attempted: bool; redirect_attempted: bool; fallback_attempted: bool


@dataclass(frozen=True, slots=True)
class AuthenticatedProviderRequestAssemblyResultV1:
    assembly_request_id: str; binding_id: str; policy_id: str; accepted: bool; failure_codes: tuple[str, ...]; policy_valid: bool; binding_valid: bool; upstream_evidence_valid: bool; header_metadata_valid: bool; payload_metadata_valid: bool; idempotency_metadata_valid: bool; header_binder_invoked: bool; header_value_bound: bool; descriptor_constructed: bool; redaction_valid: bool; authenticated: bool; transmitted: bool; provider_executed: bool; retry_attempted: bool; redirect_attempted: bool; fallback_attempted: bool

    @property
    def descriptor(self) -> AuthenticatedProviderRequestDescriptorV1 | None:
        if not self.descriptor_constructed:
            return None
        names = ("X-Provider-Key", "X-Request-Id", "Idempotency-Key", "Content-Type", "Accept")
        return AuthenticatedProviderRequestDescriptorV1(
            "redacted-authenticated-request-descriptor-v1", self.assembly_request_id, self.binding_id,
            self.policy_id, "", "", "", "", "", 0, "", "", "", "", names,
            names[0], names[1], names[2], "", "", "", "", "", self.header_binder_invoked,
            self.header_value_bound, True, True, False, False, False, False, False, False,
        )


@dataclass(frozen=True, slots=True)
class AuthenticatedProviderRequestAuditEvidenceV1:
    assembly_request_id: str; binding_id: str; policy_id: str; provider_id: str; request_route_id: str; endpoint_configuration_id: str; connectivity_preflight_request_id: str; authentication_request_id: str; authentication_envelope_id: str; credential_reference_id: str; provider_request_id: str; payload_identity: str; reservation_id: str; persistence_command_id: str; pricing_evidence_id: str; request_construction_policy_id: str; request_method: str; transport_scheme: str; content_type: str; accept_type: str; ordered_header_names: tuple; body_length: int; header_binder_invoked: bool; header_value_bound: bool; descriptor_constructed: bool; failure_codes: tuple[str, ...]; authenticated: bool; transmitted: bool; provider_executed: bool; retry_attempted: bool; redirect_attempted: bool; fallback_attempted: bool


class ProviderAuthenticationHeaderBinderV1(Protocol):
    def bind_header(self, authentication_envelope_id: str, field_name: str, consumer: object) -> object: ...


_EMPTY_CODES = (
    ("assembly_request_id", "ASSEMBLY_REQUEST_ID_EMPTY"), ("binding_id", "BINDING_ID_EMPTY"),
    ("policy_id", "POLICY_ID_EMPTY"), ("policy_version", "POLICY_VERSION_EMPTY"),
    ("provider_id", "PROVIDER_ID_EMPTY"), ("request_route_id", "REQUEST_ROUTE_ID_EMPTY"),
    ("endpoint_configuration_id", "ENDPOINT_CONFIGURATION_ID_EMPTY"),
    ("connectivity_preflight_request_id", "CONNECTIVITY_PREFLIGHT_REQUEST_ID_EMPTY"),
    ("authentication_request_id", "AUTHENTICATION_REQUEST_ID_EMPTY"),
    ("authentication_envelope_id", "AUTHENTICATION_ENVELOPE_ID_EMPTY"),
    ("credential_reference_id", "CREDENTIAL_REFERENCE_ID_EMPTY"),
    ("provider_request_id", "PROVIDER_REQUEST_ID_EMPTY"), ("provider_request_payload_identity", "PAYLOAD_IDENTITY_EMPTY"),
    ("reservation_id", "RESERVATION_ID_EMPTY"), ("persistence_command_id", "PERSISTENCE_COMMAND_ID_EMPTY"),
    ("idempotency_key", "IDEMPOTENCY_KEY_EMPTY"),
)


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and not any(c.isspace() for c in value)


def _invalid_header(value: object, allowed: tuple, prohibited: tuple, limit: object) -> str | None:
    if not _identifier(value) or ":" in value or any(ord(c) < 32 for c in value):
        return "HEADER_NAME_INVALID"
    if not isinstance(limit, int) or isinstance(limit, bool) or len(value) > limit:
        return "HEADER_NAME_LENGTH_INVALID"
    if value.casefold() in {str(item).casefold() for item in prohibited}:
        return "PROHIBITED_HEADER_PRESENT"
    if value not in allowed:
        return "HEADER_NAME_NOT_ALLOWED"
    return None


def _codes(policy: AuthenticatedProviderRequestPolicyV1, binding: AuthenticatedProviderRequestBindingV1, request: AuthenticatedProviderRequestAssemblyRequestV1) -> tuple[str, ...]:
    codes: list[str] = []
    for owner in (policy, binding, request):
        for name, code in _EMPTY_CODES:
            if hasattr(owner, name) and not _identifier(getattr(owner, name)):
                codes.append(code)
    for value, code in ((binding.authentication_policy_id, "AUTHENTICATION_POLICY_ID_EMPTY"),
                        (binding.credential_binding_id, "CREDENTIAL_BINDING_ID_EMPTY"),
                        (binding.pricing_evidence_id, "PRICING_EVIDENCE_ID_EMPTY"),
                        (binding.request_construction_policy_id, "REQUEST_CONSTRUCTION_POLICY_ID_EMPTY")):
        if not _identifier(value):
            codes.append(code)
    if binding.authenticated_request_policy_id != policy.policy_id:
        codes.append("POLICY_IDENTITY_MISMATCH")
    checks = (
        (binding.provider_id, request.provider_id, "PROVIDER_IDENTITY_MISMATCH"),
        (binding.request_route_id, request.request_route_id, "ROUTE_IDENTITY_MISMATCH"),
        (binding.endpoint_configuration_id, request.endpoint_configuration_id, "ENDPOINT_IDENTITY_MISMATCH"),
        (binding.connectivity_preflight_request_id, request.connectivity_preflight_request_id, "CONNECTIVITY_PREFLIGHT_IDENTITY_MISMATCH"),
        (binding.authentication_request_id, request.authentication_request_id, "AUTHENTICATION_REQUEST_IDENTITY_MISMATCH"),
        (binding.authentication_envelope_id, request.authentication_envelope_id, "AUTHENTICATION_ENVELOPE_IDENTITY_MISMATCH"),
        (binding.provider_request_id, request.provider_request_id, "PROVIDER_REQUEST_IDENTITY_MISMATCH"),
        (binding.provider_request_payload_identity, request.provider_request_payload_identity, "PAYLOAD_IDENTITY_MISMATCH"),
        (binding.reservation_id, request.reservation_id, "RESERVATION_IDENTITY_MISMATCH"),
        (binding.persistence_command_id, request.persistence_command_id, "PERSISTENCE_COMMAND_IDENTITY_MISMATCH"),
        (binding.idempotency_key, request.idempotency_key, "IDEMPOTENCY_IDENTITY_MISMATCH"),
    )
    for left, right, code in checks:
        if left != right:
            codes.append(code)
    if policy.provider_id != binding.provider_id or policy.provider_id != request.provider_id:
        codes.append("PROVIDER_IDENTITY_MISMATCH")
    for valid, code in ((binding.binding_verified and request.binding_valid, "BINDING_NOT_VERIFIED"),
                        (request.provider_request_constructed, "PROVIDER_REQUEST_NOT_CONSTRUCTED"),
                        (request.pricing_revalidated, "PRICING_NOT_REVALIDATED"),
                        (binding.reservation_persisted and request.reservation_persisted, "RESERVATION_NOT_PERSISTED"),
                        (binding.persistence_recovery_clear and request.persistence_recovery_clear, "PERSISTENCE_RECOVERY_UNRESOLVED"),
                        (binding.connectivity_metadata_ready and request.connectivity_metadata_ready, "CONNECTIVITY_METADATA_NOT_READY"),
                        (binding.authentication_envelope_constructed and request.authentication_envelope_constructed, "AUTHENTICATION_ENVELOPE_NOT_CONSTRUCTED"),
                        (binding.request_assembly_authorized and request.request_assembly_authorized and policy.request_assembly_authorized, "REQUEST_ASSEMBLY_NOT_AUTHORIZED"),
                        (policy.header_binding_authorized, "HEADER_BINDING_NOT_AUTHORIZED"),
                        (policy.authentication_authorized, "AUTHENTICATION_NOT_AUTHORIZED")):
        if not valid:
            codes.append(code)
    if policy.request_method not in policy.allowed_methods:
        codes.append("REQUEST_METHOD_NOT_ALLOWED")
    if policy.require_https and policy.transport_scheme != "HTTPS":
        codes.append("HTTPS_REQUIRED")
    if policy.transport_scheme != "HTTPS":
        codes.append("TRANSPORT_SCHEME_NOT_ALLOWED")
    content_type = "application/json"; accept_type = "application/json"
    if content_type not in policy.allowed_content_types:
        codes.append("CONTENT_TYPE_NOT_ALLOWED")
    if accept_type not in policy.allowed_accept_types:
        codes.append("ACCEPT_TYPE_NOT_ALLOWED")
    names = (policy.authentication_field_name, policy.request_id_header_name, policy.idempotency_header_name, policy.content_type_header_name, policy.accept_header_name)
    if policy.require_request_id_header and not policy.request_id_header_name: codes.append("REQUEST_ID_HEADER_REQUIRED")
    if policy.require_idempotency_header and not policy.idempotency_header_name: codes.append("IDEMPOTENCY_HEADER_REQUIRED")
    if policy.require_content_type_header and not policy.content_type_header_name: codes.append("CONTENT_TYPE_HEADER_REQUIRED")
    if policy.require_accept_header and not policy.accept_header_name: codes.append("ACCEPT_HEADER_REQUIRED")
    if not _identifier(policy.authentication_field_name): codes.append("AUTHENTICATION_FIELD_NAME_INVALID")
    if len({name.casefold() for name in names if isinstance(name, str)}) != len(names): codes.append("DUPLICATE_HEADER_NAME")
    if not isinstance(policy.maximum_header_count, int) or isinstance(policy.maximum_header_count, bool) or policy.maximum_header_count != len(names): codes.append("HEADER_COUNT_INVALID")
    for name in names:
        issue = _invalid_header(name, policy.allowed_header_names, policy.prohibited_header_names, policy.maximum_header_name_length)
        if issue: codes.append(issue)
    length = len(request.provider_request_payload_identity)
    if not isinstance(policy.maximum_body_bytes, int) or isinstance(policy.maximum_body_bytes, bool) or policy.maximum_body_bytes <= 0:
        codes.append("BODY_LENGTH_INVALID")
    elif length > policy.maximum_body_bytes:
        codes.append("BODY_LENGTH_EXCEEDED")
    if policy.maximum_attempts != 0 or policy.retry_allowed: codes.append("RETRY_NOT_AUTHORIZED")
    if policy.maximum_redirects != 0: codes.append("REDIRECT_NOT_AUTHORIZED")
    if policy.fallback_route_allowed: codes.append("FALLBACK_ROUTE_NOT_AUTHORIZED")
    return tuple(sorted(set(codes)))


def _result(policy: AuthenticatedProviderRequestPolicyV1, binding: AuthenticatedProviderRequestBindingV1, request: AuthenticatedProviderRequestAssemblyRequestV1, codes: tuple[str, ...], invoked: bool = False, bound: bool = False) -> AuthenticatedProviderRequestAssemblyResultV1:
    accepted = not codes and bound
    return AuthenticatedProviderRequestAssemblyResultV1(
        request.assembly_request_id, binding.binding_id, policy.policy_id, accepted, tuple(sorted(set(codes))),
        not any(code in codes for code in ("POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "REQUEST_METHOD_NOT_ALLOWED")),
        "BINDING_NOT_VERIFIED" not in codes, not any(code in codes for code in ("PROVIDER_REQUEST_NOT_CONSTRUCTED", "PRICING_NOT_REVALIDATED", "RESERVATION_NOT_PERSISTED", "PERSISTENCE_RECOVERY_UNRESOLVED", "CONNECTIVITY_METADATA_NOT_READY", "AUTHENTICATION_ENVELOPE_NOT_CONSTRUCTED")),
        not any(code in codes for code in ("HEADER_NAME_INVALID", "HEADER_NAME_NOT_ALLOWED", "HEADER_COUNT_INVALID", "DUPLICATE_HEADER_NAME")),
        not any(code in codes for code in ("PAYLOAD_IDENTITY_EMPTY", "PAYLOAD_IDENTITY_MISMATCH", "BODY_LENGTH_INVALID", "BODY_LENGTH_EXCEEDED")),
        "IDEMPOTENCY_IDENTITY_MISMATCH" not in codes and "IDEMPOTENCY_KEY_EMPTY" not in codes,
        invoked, bound, accepted, True, False, False, False, False, False, False,
    )


def assemble_authenticated_provider_request_v1(policy: AuthenticatedProviderRequestPolicyV1, binding: AuthenticatedProviderRequestBindingV1, request: AuthenticatedProviderRequestAssemblyRequestV1, binder: ProviderAuthenticationHeaderBinderV1 | None) -> AuthenticatedProviderRequestAssemblyResultV1:
    codes = _codes(policy, binding, request)
    if codes:
        return _result(policy, binding, request, codes)
    if binder is None or not callable(getattr(binder, "bind_header", None)):
        return _result(policy, binding, request, ("HEADER_BINDER_REQUIRED",))
    try:
        bound = bool(binder.bind_header(request.authentication_envelope_id, policy.authentication_field_name, lambda _opaque: True))
    except Exception:
        return _result(policy, binding, request, ("HEADER_BINDER_INVOCATION_FAILED",), True)
    if not bound:
        return _result(policy, binding, request, ("HEADER_BINDING_FAILED",), True)
    return _result(policy, binding, request, (), True, True)


def build_authenticated_provider_request_audit_evidence_v1(policy: AuthenticatedProviderRequestPolicyV1, binding: AuthenticatedProviderRequestBindingV1, request: AuthenticatedProviderRequestAssemblyRequestV1, result: AuthenticatedProviderRequestAssemblyResultV1) -> AuthenticatedProviderRequestAuditEvidenceV1:
    if not isinstance(policy, AuthenticatedProviderRequestPolicyV1) or not isinstance(binding, AuthenticatedProviderRequestBindingV1) or not isinstance(request, AuthenticatedProviderRequestAssemblyRequestV1) or not isinstance(result, AuthenticatedProviderRequestAssemblyResultV1) or result.assembly_request_id != request.assembly_request_id or result.binding_id != binding.binding_id or result.policy_id != policy.policy_id or binding.provider_id != request.provider_id:
        raise ValueError("authenticated request evidence identity mismatch")
    names = (policy.authentication_field_name, policy.request_id_header_name, policy.idempotency_header_name, policy.content_type_header_name, policy.accept_header_name)
    return AuthenticatedProviderRequestAuditEvidenceV1(
        request.assembly_request_id, binding.binding_id, policy.policy_id, binding.provider_id, binding.request_route_id,
        binding.endpoint_configuration_id, binding.connectivity_preflight_request_id, binding.authentication_request_id,
        binding.authentication_envelope_id, binding.credential_reference_id, binding.provider_request_id,
        binding.provider_request_payload_identity, binding.reservation_id, binding.persistence_command_id,
        binding.pricing_evidence_id, binding.request_construction_policy_id, policy.request_method,
        policy.transport_scheme, "application/json", "application/json", names,
        len(binding.provider_request_payload_identity), result.header_binder_invoked, result.header_value_bound,
        result.descriptor_constructed, result.failure_codes, False, False, False, False, False, False,
    )
