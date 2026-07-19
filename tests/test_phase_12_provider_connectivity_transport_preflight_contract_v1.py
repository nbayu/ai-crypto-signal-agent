"""RED contract for a fake-only Phase 12 provider-connectivity preflight."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime

import pytest

from engine.phase_12_provider_connectivity_transport_preflight_contract_v1 import (
    ProviderConnectivityAuditEvidenceV1,
    ProviderConnectivityFailureV1,
    ProviderConnectivityPreflightRequestV1,
    ProviderConnectivityPreflightResultV1,
    ProviderConnectivityProbeV1,
    ProviderEndpointConfigurationV1,
    ProviderTransportFactoryV1,
    ProviderTransportPolicyV1,
    build_provider_connectivity_audit_evidence_v1,
    evaluate_provider_connectivity_preflight_v1,
)


_NOW = datetime(2030, 1, 2, 12, 0, tzinfo=UTC)
_ENDPOINT_FIELDS = (
    "endpoint_configuration_id", "provider_id", "transport_scheme", "host_identity", "port",
    "api_base_path", "region", "endpoint_environment", "tls_server_name", "proxy_mode",
    "proxy_identity", "credential_reference_id", "request_route_id", "endpoint_selected",
    "connectivity_authorized", "authentication_authorized", "transmission_authorized",
    "provider_execution_authorized",
)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "allowed_transport_schemes", "allowed_provider_ids",
    "allowed_endpoint_environments", "allowed_ports", "require_https", "require_tls",
    "require_certificate_verification", "require_hostname_verification", "require_explicit_server_name",
    "allow_system_proxy", "allow_environment_proxy", "allow_custom_proxy", "require_proxy_allowlist",
    "connect_timeout_seconds", "tls_handshake_timeout_seconds", "response_header_timeout_seconds",
    "total_timeout_seconds", "maximum_redirects", "maximum_attempts", "retry_allowed",
    "fallback_endpoint_allowed", "DNS_resolution_authorized", "socket_connection_authorized",
    "TLS_handshake_authorized", "authentication_authorized", "transmission_authorized",
    "provider_execution_authorized", "fail_closed",
)
_REQUEST_FIELDS = (
    "preflight_request_id", "endpoint_configuration_id", "provider_id", "request_route_id",
    "credential_reference_id", "provider_request_id", "reservation_id", "persistence_command_id",
    "requested_at", "credential_verified", "pricing_revalidated", "provider_request_constructed",
    "reservation_persisted", "persistence_recovery_clear", "connectivity_preflight_authorized",
)
_RESULT_FIELDS = (
    "preflight_request_id", "endpoint_configuration_id", "policy_id", "accepted", "failure_codes",
    "factory_invoked", "probe_invoked", "endpoint_allowed", "timeout_policy_valid", "TLS_policy_valid",
    "proxy_policy_valid", "upstream_evidence_valid", "connectivity_metadata_ready", "DNS_resolved",
    "socket_connected", "TLS_established", "authenticated", "transmitted", "provider_executed",
    "retry_attempted", "fallback_attempted",
)
_AUDIT_FIELDS = (
    "preflight_request_id", "endpoint_configuration_id", "policy_id", "provider_id", "request_route_id",
    "credential_reference_id", "provider_request_id", "reservation_id", "persistence_command_id",
    "endpoint_environment", "transport_scheme", "timeout_policy_valid", "TLS_policy_valid",
    "proxy_policy_valid", "upstream_evidence_valid", "factory_invoked", "probe_invoked",
    "connectivity_metadata_ready", "failure_codes", "DNS_resolved", "socket_connected",
    "TLS_established", "authenticated", "transmitted", "provider_executed", "retry_attempted",
    "fallback_attempted",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_FAILURES = {
    "PREFLIGHT_REQUEST_ID_EMPTY", "ENDPOINT_CONFIGURATION_ID_EMPTY", "PROVIDER_ID_EMPTY",
    "REQUEST_ROUTE_ID_EMPTY", "CREDENTIAL_REFERENCE_ID_EMPTY", "PROVIDER_REQUEST_ID_EMPTY",
    "RESERVATION_ID_EMPTY", "PERSISTENCE_COMMAND_ID_EMPTY", "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY",
    "IDENTIFIER_NOT_NORMALIZED", "ENDPOINT_NOT_SELECTED", "TRANSPORT_SCHEME_NOT_ALLOWED",
    "HTTPS_REQUIRED", "HOST_IDENTITY_EMPTY", "HOST_IDENTITY_INVALID", "PORT_INVALID", "PORT_NOT_ALLOWED",
    "API_BASE_PATH_INVALID", "REGION_EMPTY", "ENDPOINT_ENVIRONMENT_NOT_ALLOWED", "TLS_SERVER_NAME_EMPTY",
    "TLS_SERVER_NAME_MISMATCH", "PROVIDER_NOT_ALLOWED", "ROUTE_IDENTITY_MISMATCH",
    "CREDENTIAL_REFERENCE_MISMATCH", "PROVIDER_REQUEST_IDENTITY_MISMATCH", "RESERVATION_IDENTITY_MISMATCH",
    "PERSISTENCE_COMMAND_IDENTITY_MISMATCH", "CREDENTIAL_NOT_VERIFIED", "PRICING_NOT_REVALIDATED",
    "PROVIDER_REQUEST_NOT_CONSTRUCTED", "RESERVATION_NOT_PERSISTED", "PERSISTENCE_RECOVERY_UNRESOLVED",
    "CONNECTIVITY_PREFLIGHT_NOT_AUTHORIZED", "CONNECTIVITY_NOT_AUTHORIZED", "DNS_RESOLUTION_NOT_AUTHORIZED",
    "SOCKET_CONNECTION_NOT_AUTHORIZED", "TLS_HANDSHAKE_NOT_AUTHORIZED", "AUTHENTICATION_NOT_AUTHORIZED",
    "TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED", "TRANSPORT_FACTORY_REQUIRED",
    "CONNECTIVITY_PROBE_REQUIRED", "CONNECT_TIMEOUT_INVALID", "TLS_TIMEOUT_INVALID",
    "RESPONSE_TIMEOUT_INVALID", "TOTAL_TIMEOUT_INVALID", "TIMEOUT_ORDER_INVALID", "ATTEMPT_LIMIT_ZERO",
    "RETRY_NOT_AUTHORIZED", "REDIRECT_NOT_AUTHORIZED", "FALLBACK_ENDPOINT_NOT_AUTHORIZED",
    "SYSTEM_PROXY_NOT_AUTHORIZED", "ENVIRONMENT_PROXY_NOT_AUTHORIZED", "CUSTOM_PROXY_NOT_AUTHORIZED",
    "PROXY_NOT_ALLOWLISTED", "CERTIFICATE_VERIFICATION_REQUIRED", "HOSTNAME_VERIFICATION_REQUIRED",
    "CONNECTIVITY_METADATA_NOT_READY", "RAW_HOST_EXPOSURE_DETECTED", "RAW_ENDPOINT_EXPOSURE_DETECTED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


class _FakeProbe:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, preflight: ProviderConnectivityPreflightRequestV1) -> bool:
        self.calls += 1
        return preflight.preflight_request_id == "provider-connectivity-preflight-v1"


class _FakeFactory:
    def __init__(self, probe: _FakeProbe) -> None:
        self._probe = probe
        self.calls = 0

    def create_preflight_probe(
        self, endpoint: ProviderEndpointConfigurationV1, policy: ProviderTransportPolicyV1,
    ) -> _FakeProbe:
        self.calls += 1
        assert endpoint.endpoint_configuration_id == "provider-endpoint-config-v1"
        assert policy.policy_id == "provider-transport-policy-v1"
        return self._probe


def _endpoint(**overrides: object) -> ProviderEndpointConfigurationV1:
    values = {
        "endpoint_configuration_id": "provider-endpoint-config-v1", "provider_id": "provider-v1",
        "transport_scheme": "HTTPS", "host_identity": "api.provider.test", "port": 443,
        "api_base_path": "/v1", "region": "test-region-v1", "endpoint_environment": "TEST_EPHEMERAL",
        "tls_server_name": "api.provider.test", "proxy_mode": "NONE", "proxy_identity": "",
        "credential_reference_id": "credential-reference-v1", "request_route_id": "provider-route-v1",
        "endpoint_selected": True, "connectivity_authorized": True, "authentication_authorized": False,
        "transmission_authorized": False, "provider_execution_authorized": False,
    }
    values.update(overrides)
    return ProviderEndpointConfigurationV1(**values)


def _policy(**overrides: object) -> ProviderTransportPolicyV1:
    values = {
        "policy_id": "provider-transport-policy-v1", "policy_version": "V1",
        "allowed_transport_schemes": ("HTTPS",), "allowed_provider_ids": ("provider-v1",),
        "allowed_endpoint_environments": ("TEST_EPHEMERAL",), "allowed_ports": (443,),
        "require_https": True, "require_tls": True, "require_certificate_verification": True,
        "require_hostname_verification": True, "require_explicit_server_name": True,
        "allow_system_proxy": False, "allow_environment_proxy": False, "allow_custom_proxy": False,
        "require_proxy_allowlist": True, "connect_timeout_seconds": 5,
        "tls_handshake_timeout_seconds": 5, "response_header_timeout_seconds": 5,
        "total_timeout_seconds": 20, "maximum_redirects": 0, "maximum_attempts": 0,
        "retry_allowed": False, "fallback_endpoint_allowed": False, "DNS_resolution_authorized": False,
        "socket_connection_authorized": False, "TLS_handshake_authorized": False,
        "authentication_authorized": False, "transmission_authorized": False,
        "provider_execution_authorized": False, "fail_closed": True,
    }
    values.update(overrides)
    return ProviderTransportPolicyV1(**values)


def _preflight(**overrides: object) -> ProviderConnectivityPreflightRequestV1:
    values = {
        "preflight_request_id": "provider-connectivity-preflight-v1",
        "endpoint_configuration_id": "provider-endpoint-config-v1", "provider_id": "provider-v1",
        "request_route_id": "provider-route-v1", "credential_reference_id": "credential-reference-v1",
        "provider_request_id": "provider-request-v1", "reservation_id": "reservation-v1",
        "persistence_command_id": "persistence-command-v1", "requested_at": _NOW,
        "credential_verified": True, "pricing_revalidated": True, "provider_request_constructed": True,
        "reservation_persisted": True, "persistence_recovery_clear": True,
        "connectivity_preflight_authorized": True,
    }
    values.update(overrides)
    return ProviderConnectivityPreflightRequestV1(**values)


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_narrow_and_transport_free() -> None:
    assert tuple(field.name for field in fields(ProviderEndpointConfigurationV1)) == _ENDPOINT_FIELDS
    assert tuple(field.name for field in fields(ProviderTransportPolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(ProviderConnectivityPreflightRequestV1)) == _REQUEST_FIELDS
    assert tuple(field.name for field in fields(ProviderConnectivityPreflightResultV1)) == _RESULT_FIELDS
    assert tuple(field.name for field in fields(ProviderConnectivityAuditEvidenceV1)) == _AUDIT_FIELDS
    assert tuple(field.name for field in fields(ProviderConnectivityFailureV1)) == _FAILURE_FIELDS
    assert {"create_preflight_probe"}.issubset(dir(ProviderTransportFactoryV1))
    assert {"evaluate"}.issubset(dir(ProviderConnectivityProbeV1))
    forbidden = {"connect", "send", "post", "get", "execute", "socket", "request", "authorization"}
    assert not forbidden.intersection(dir(ProviderTransportFactoryV1))
    assert not forbidden.intersection(dir(ProviderConnectivityProbeV1))
    result = evaluate_provider_connectivity_preflight_v1(_endpoint(), _policy(), _preflight(), None)
    evidence = build_provider_connectivity_audit_evidence_v1(_endpoint(), _policy(), _preflight(), result)
    for value in (_endpoint(), _policy(), _preflight(), result, evidence):
        _frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        _endpoint().connectivity_authorized = False  # type: ignore[misc]


def test_fail_closed_preconditions_do_not_invoke_fake_factory_or_probe() -> None:
    probe, factory = _FakeProbe(), _FakeFactory(_FakeProbe())
    result = evaluate_provider_connectivity_preflight_v1(
        _endpoint(endpoint_selected=False, host_identity="https://unsafe.test"),
        _policy(),
        _preflight(credential_verified=False, reservation_persisted=False),
        factory,
    )
    assert {
        "ENDPOINT_NOT_SELECTED", "HOST_IDENTITY_INVALID", "CREDENTIAL_NOT_VERIFIED",
        "RESERVATION_NOT_PERSISTED", "CONNECTIVITY_METADATA_NOT_READY",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert factory.calls == probe.calls == 0
    assert (result.factory_invoked, result.probe_invoked, result.DNS_resolved, result.socket_connected,
            result.TLS_established, result.authenticated, result.transmitted, result.provider_executed,
            result.retry_attempted, result.fallback_attempted) == (False,) * 10


def test_fake_structural_preflight_remains_zero_network_and_zero_execution() -> None:
    probe = _FakeProbe()
    factory = _FakeFactory(probe)
    result = evaluate_provider_connectivity_preflight_v1(_endpoint(), _policy(), _preflight(), factory)
    assert result.accepted is True
    assert result.connectivity_metadata_ready is True
    assert factory.calls == probe.calls == 1
    assert (result.DNS_resolved, result.socket_connected, result.TLS_established, result.authenticated,
            result.transmitted, result.provider_executed, result.retry_attempted,
            result.fallback_attempted) == (False,) * 8


def test_audit_evidence_is_identity_bound_redacted_and_non_operational() -> None:
    probe = _FakeProbe()
    factory = _FakeFactory(probe)
    endpoint, policy, preflight = _endpoint(), _policy(), _preflight()
    result = evaluate_provider_connectivity_preflight_v1(endpoint, policy, preflight, factory)
    evidence = build_provider_connectivity_audit_evidence_v1(endpoint, policy, preflight, result)
    assert evidence == build_provider_connectivity_audit_evidence_v1(endpoint, policy, preflight, result)
    assert "api.provider.test" not in repr(evidence)
    assert evidence.transmitted is evidence.provider_executed is False
    with pytest.raises(ValueError):
        build_provider_connectivity_audit_evidence_v1(_endpoint(provider_id="other-provider-v1"), policy, preflight, result)
