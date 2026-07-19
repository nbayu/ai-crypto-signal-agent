"""Pure fake-only provider connectivity and transport preflight boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderEndpointConfigurationV1:
    endpoint_configuration_id: str
    provider_id: str
    transport_scheme: str
    host_identity: str
    port: int
    api_base_path: str
    region: str
    endpoint_environment: str
    tls_server_name: str
    proxy_mode: str
    proxy_identity: str
    credential_reference_id: str
    request_route_id: str
    endpoint_selected: bool = False
    connectivity_authorized: bool = False
    authentication_authorized: bool = False
    transmission_authorized: bool = False
    provider_execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ProviderTransportPolicyV1:
    policy_id: str
    policy_version: str
    allowed_transport_schemes: tuple[str, ...] = ()
    allowed_provider_ids: tuple[str, ...] = ()
    allowed_endpoint_environments: tuple[str, ...] = ()
    allowed_ports: tuple[int, ...] = ()
    require_https: bool = True
    require_tls: bool = True
    require_certificate_verification: bool = True
    require_hostname_verification: bool = True
    require_explicit_server_name: bool = True
    allow_system_proxy: bool = False
    allow_environment_proxy: bool = False
    allow_custom_proxy: bool = False
    require_proxy_allowlist: bool = True
    connect_timeout_seconds: int = 0
    tls_handshake_timeout_seconds: int = 0
    response_header_timeout_seconds: int = 0
    total_timeout_seconds: int = 0
    maximum_redirects: int = 0
    maximum_attempts: int = 0
    retry_allowed: bool = False
    fallback_endpoint_allowed: bool = False
    DNS_resolution_authorized: bool = False
    socket_connection_authorized: bool = False
    TLS_handshake_authorized: bool = False
    authentication_authorized: bool = False
    transmission_authorized: bool = False
    provider_execution_authorized: bool = False
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class ProviderConnectivityFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class ProviderConnectivityPreflightRequestV1:
    preflight_request_id: str
    endpoint_configuration_id: str
    provider_id: str
    request_route_id: str
    credential_reference_id: str
    provider_request_id: str
    reservation_id: str
    persistence_command_id: str
    requested_at: datetime
    credential_verified: bool
    pricing_revalidated: bool
    provider_request_constructed: bool
    reservation_persisted: bool
    persistence_recovery_clear: bool
    connectivity_preflight_authorized: bool


@dataclass(frozen=True, slots=True)
class ProviderConnectivityPreflightResultV1:
    preflight_request_id: str
    endpoint_configuration_id: str
    policy_id: str
    accepted: bool
    failure_codes: tuple[str, ...]
    factory_invoked: bool
    probe_invoked: bool
    endpoint_allowed: bool
    timeout_policy_valid: bool
    TLS_policy_valid: bool
    proxy_policy_valid: bool
    upstream_evidence_valid: bool
    connectivity_metadata_ready: bool
    DNS_resolved: bool
    socket_connected: bool
    TLS_established: bool
    authenticated: bool
    transmitted: bool
    provider_executed: bool
    retry_attempted: bool
    fallback_attempted: bool


@dataclass(frozen=True, slots=True)
class ProviderConnectivityAuditEvidenceV1:
    preflight_request_id: str
    endpoint_configuration_id: str
    policy_id: str
    provider_id: str
    request_route_id: str
    credential_reference_id: str
    provider_request_id: str
    reservation_id: str
    persistence_command_id: str
    endpoint_environment: str
    transport_scheme: str
    timeout_policy_valid: bool
    TLS_policy_valid: bool
    proxy_policy_valid: bool
    upstream_evidence_valid: bool
    factory_invoked: bool
    probe_invoked: bool
    connectivity_metadata_ready: bool
    failure_codes: tuple[str, ...]
    DNS_resolved: bool
    socket_connected: bool
    TLS_established: bool
    authenticated: bool
    transmitted: bool
    provider_executed: bool
    retry_attempted: bool
    fallback_attempted: bool


class ProviderTransportFactoryV1(Protocol):
    def create_preflight_probe(
        self, endpoint: ProviderEndpointConfigurationV1, policy: ProviderTransportPolicyV1,
    ) -> ProviderConnectivityProbeV1:
        """Create one supplied fake-only structural preflight probe."""


class ProviderConnectivityProbeV1(Protocol):
    def evaluate(self, preflight: ProviderConnectivityPreflightRequestV1) -> bool:
        """Return deterministic structural metadata readiness without networking."""


def _ordered(codes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(codes)))


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and value.isascii() and "*" not in value


def _positive(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _flag(value: object) -> bool:
    return type(value) is bool


def _utc(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo == UTC


def _raw_ip(value: str) -> bool:
    labels = value.split(".")
    return len(labels) == 4 and all(label.isdigit() and 0 <= int(label) <= 255 for label in labels)


def _endpoint_codes(endpoint: object, policy: object, preflight: object) -> tuple[str, ...]:
    codes: list[str] = []
    if not isinstance(endpoint, ProviderEndpointConfigurationV1):
        return ("ENDPOINT_CONFIGURATION_ID_EMPTY",)
    if not isinstance(policy, ProviderTransportPolicyV1):
        return ("POLICY_ID_EMPTY",)
    if not isinstance(preflight, ProviderConnectivityPreflightRequestV1):
        return ("PREFLIGHT_REQUEST_ID_EMPTY",)
    identities = (
        (endpoint.endpoint_configuration_id, "ENDPOINT_CONFIGURATION_ID_EMPTY"),
        (endpoint.provider_id, "PROVIDER_ID_EMPTY"),
        (endpoint.credential_reference_id, "CREDENTIAL_REFERENCE_ID_EMPTY"),
        (endpoint.request_route_id, "REQUEST_ROUTE_ID_EMPTY"),
        (policy.policy_id, "POLICY_ID_EMPTY"),
        (policy.policy_version, "POLICY_VERSION_EMPTY"),
        (preflight.preflight_request_id, "PREFLIGHT_REQUEST_ID_EMPTY"),
        (preflight.endpoint_configuration_id, "ENDPOINT_CONFIGURATION_ID_EMPTY"),
        (preflight.provider_id, "PROVIDER_ID_EMPTY"),
        (preflight.request_route_id, "REQUEST_ROUTE_ID_EMPTY"),
        (preflight.credential_reference_id, "CREDENTIAL_REFERENCE_ID_EMPTY"),
        (preflight.provider_request_id, "PROVIDER_REQUEST_ID_EMPTY"),
        (preflight.reservation_id, "RESERVATION_ID_EMPTY"),
        (preflight.persistence_command_id, "PERSISTENCE_COMMAND_ID_EMPTY"),
    )
    for value, empty_code in identities:
        if not isinstance(value, str) or not value:
            codes.append(empty_code)
        elif not _identifier(value):
            codes.append("IDENTIFIER_NOT_NORMALIZED")
    if endpoint.endpoint_selected is not True:
        codes.append("ENDPOINT_NOT_SELECTED")
    if endpoint.connectivity_authorized is not True:
        codes.append("CONNECTIVITY_NOT_AUTHORIZED")
    if endpoint.transport_scheme != "HTTPS":
        codes.extend(("TRANSPORT_SCHEME_NOT_ALLOWED", "HTTPS_REQUIRED"))
    if endpoint.transport_scheme not in policy.allowed_transport_schemes:
        codes.append("TRANSPORT_SCHEME_NOT_ALLOWED")
    host = endpoint.host_identity
    if not isinstance(host, str) or not host:
        codes.append("HOST_IDENTITY_EMPTY")
    elif (host != host.strip() or "://" in host or "/" in host or "?" in host or "#" in host
          or _raw_ip(host)):
        codes.append("HOST_IDENTITY_INVALID")
    if not isinstance(endpoint.port, int) or isinstance(endpoint.port, bool) or not 1 <= endpoint.port <= 65535:
        codes.append("PORT_INVALID")
    elif endpoint.port not in policy.allowed_ports:
        codes.append("PORT_NOT_ALLOWED")
    path = endpoint.api_base_path
    if not isinstance(path, str) or not path.startswith("/") or path == "/" or "?" in path or "#" in path or "//" in path:
        codes.append("API_BASE_PATH_INVALID")
    if not _identifier(endpoint.region):
        codes.append("REGION_EMPTY")
    if endpoint.endpoint_environment not in policy.allowed_endpoint_environments:
        codes.append("ENDPOINT_ENVIRONMENT_NOT_ALLOWED")
    if not _identifier(endpoint.tls_server_name):
        codes.append("TLS_SERVER_NAME_EMPTY")
    elif isinstance(host, str) and endpoint.tls_server_name != host:
        codes.append("TLS_SERVER_NAME_MISMATCH")
    if endpoint.provider_id not in policy.allowed_provider_ids:
        codes.append("PROVIDER_NOT_ALLOWED")
    if preflight.endpoint_configuration_id != endpoint.endpoint_configuration_id:
        codes.append("PERSISTENCE_COMMAND_IDENTITY_MISMATCH")
    if preflight.provider_id != endpoint.provider_id:
        codes.append("PROVIDER_NOT_ALLOWED")
    if preflight.request_route_id != endpoint.request_route_id:
        codes.append("ROUTE_IDENTITY_MISMATCH")
    if preflight.credential_reference_id != endpoint.credential_reference_id:
        codes.append("CREDENTIAL_REFERENCE_MISMATCH")
    return _ordered(codes)


def _timeout_codes(policy: ProviderTransportPolicyV1) -> tuple[str, ...]:
    codes: list[str] = []
    values = (
        (policy.connect_timeout_seconds, "CONNECT_TIMEOUT_INVALID"),
        (policy.tls_handshake_timeout_seconds, "TLS_TIMEOUT_INVALID"),
        (policy.response_header_timeout_seconds, "RESPONSE_TIMEOUT_INVALID"),
        (policy.total_timeout_seconds, "TOTAL_TIMEOUT_INVALID"),
    )
    for value, code in values:
        if not _positive(value):
            codes.append(code)
    if all(_positive(value) for value, _ in values):
        if policy.total_timeout_seconds < max(
            policy.connect_timeout_seconds, policy.tls_handshake_timeout_seconds,
            policy.response_header_timeout_seconds,
        ):
            codes.append("TIMEOUT_ORDER_INVALID")
    if policy.maximum_attempts != 0 or isinstance(policy.maximum_attempts, bool):
        codes.append("ATTEMPT_LIMIT_ZERO")
    if policy.retry_allowed is not False:
        codes.append("RETRY_NOT_AUTHORIZED")
    if policy.maximum_redirects != 0 or isinstance(policy.maximum_redirects, bool):
        codes.append("REDIRECT_NOT_AUTHORIZED")
    if policy.fallback_endpoint_allowed is not False:
        codes.append("FALLBACK_ENDPOINT_NOT_AUTHORIZED")
    return _ordered(codes)


def _tls_proxy_codes(endpoint: ProviderEndpointConfigurationV1, policy: ProviderTransportPolicyV1) -> tuple[str, ...]:
    codes: list[str] = []
    if policy.require_https is not True or policy.require_tls is not True:
        codes.append("HTTPS_REQUIRED")
    if policy.require_certificate_verification is not True:
        codes.append("CERTIFICATE_VERIFICATION_REQUIRED")
    if policy.require_hostname_verification is not True:
        codes.append("HOSTNAME_VERIFICATION_REQUIRED")
    if policy.require_explicit_server_name is not True:
        codes.append("TLS_SERVER_NAME_EMPTY")
    if endpoint.proxy_mode == "SYSTEM":
        codes.append("SYSTEM_PROXY_NOT_AUTHORIZED")
    elif endpoint.proxy_mode == "ENVIRONMENT":
        codes.append("ENVIRONMENT_PROXY_NOT_AUTHORIZED")
    elif endpoint.proxy_mode == "CUSTOM":
        if policy.allow_custom_proxy is not True:
            codes.append("CUSTOM_PROXY_NOT_AUTHORIZED")
        if policy.require_proxy_allowlist is not True or not _identifier(endpoint.proxy_identity):
            codes.append("PROXY_NOT_ALLOWLISTED")
    elif endpoint.proxy_mode != "NONE" or endpoint.proxy_identity not in ("",):
        codes.append("CUSTOM_PROXY_NOT_AUTHORIZED")
    if policy.allow_system_proxy is not False:
        codes.append("SYSTEM_PROXY_NOT_AUTHORIZED")
    if policy.allow_environment_proxy is not False:
        codes.append("ENVIRONMENT_PROXY_NOT_AUTHORIZED")
    return _ordered(codes)


def _upstream_codes(preflight: ProviderConnectivityPreflightRequestV1) -> tuple[str, ...]:
    codes: list[str] = []
    checks = (
        (preflight.credential_verified, "CREDENTIAL_NOT_VERIFIED"),
        (preflight.pricing_revalidated, "PRICING_NOT_REVALIDATED"),
        (preflight.provider_request_constructed, "PROVIDER_REQUEST_NOT_CONSTRUCTED"),
        (preflight.reservation_persisted, "RESERVATION_NOT_PERSISTED"),
        (preflight.persistence_recovery_clear, "PERSISTENCE_RECOVERY_UNRESOLVED"),
        (preflight.connectivity_preflight_authorized, "CONNECTIVITY_PREFLIGHT_NOT_AUTHORIZED"),
    )
    for value, code in checks:
        if value is not True:
            codes.append(code)
    if not _utc(preflight.requested_at):
        codes.append("IDENTIFIER_NOT_NORMALIZED")
    return _ordered(codes)


def _result(
    endpoint: object, policy: object, preflight: object, codes: tuple[str, ...], *, factory_invoked: bool = False,
    probe_invoked: bool = False, endpoint_allowed: bool = False, timeout_policy_valid: bool = False,
    tls_policy_valid: bool = False, proxy_policy_valid: bool = False, upstream_evidence_valid: bool = False,
    ready: bool = False,
) -> ProviderConnectivityPreflightResultV1:
    return ProviderConnectivityPreflightResultV1(
        getattr(preflight, "preflight_request_id", "") if isinstance(getattr(preflight, "preflight_request_id", ""), str) else "",
        getattr(endpoint, "endpoint_configuration_id", "") if isinstance(getattr(endpoint, "endpoint_configuration_id", ""), str) else "",
        getattr(policy, "policy_id", "") if isinstance(getattr(policy, "policy_id", ""), str) else "",
        ready and not codes, _ordered(codes), factory_invoked, probe_invoked, endpoint_allowed,
        timeout_policy_valid, tls_policy_valid, proxy_policy_valid, upstream_evidence_valid,
        ready and not codes, False, False, False, False, False, False, False, False,
    )


def evaluate_provider_connectivity_preflight_v1(
    endpoint: ProviderEndpointConfigurationV1, policy: ProviderTransportPolicyV1,
    preflight: ProviderConnectivityPreflightRequestV1, factory: ProviderTransportFactoryV1 | None,
) -> ProviderConnectivityPreflightResultV1:
    """Evaluate one injected fake probe without DNS, sockets, TLS, or HTTP."""
    endpoint_codes = _endpoint_codes(endpoint, policy, preflight)
    timeout_codes = _timeout_codes(policy) if isinstance(policy, ProviderTransportPolicyV1) else ("POLICY_ID_EMPTY",)
    tls_proxy_codes = _tls_proxy_codes(endpoint, policy) if isinstance(endpoint, ProviderEndpointConfigurationV1) and isinstance(policy, ProviderTransportPolicyV1) else ("CONNECTIVITY_METADATA_NOT_READY",)
    upstream_codes = _upstream_codes(preflight) if isinstance(preflight, ProviderConnectivityPreflightRequestV1) else ("PREFLIGHT_REQUEST_ID_EMPTY",)
    codes = _ordered(endpoint_codes + timeout_codes + tls_proxy_codes + upstream_codes)
    endpoint_allowed = not endpoint_codes
    timeout_valid = not timeout_codes
    tls_valid = not any(code in tls_proxy_codes for code in (
        "HTTPS_REQUIRED", "CERTIFICATE_VERIFICATION_REQUIRED", "HOSTNAME_VERIFICATION_REQUIRED",
        "TLS_SERVER_NAME_EMPTY", "TLS_SERVER_NAME_MISMATCH",
    ))
    proxy_valid = not any(code in tls_proxy_codes for code in (
        "SYSTEM_PROXY_NOT_AUTHORIZED", "ENVIRONMENT_PROXY_NOT_AUTHORIZED", "CUSTOM_PROXY_NOT_AUTHORIZED",
        "PROXY_NOT_ALLOWLISTED",
    ))
    upstream_valid = not upstream_codes
    if codes:
        return _result(
            endpoint, policy, preflight, _ordered(codes + ("CONNECTIVITY_METADATA_NOT_READY",)),
            endpoint_allowed=endpoint_allowed, timeout_policy_valid=timeout_valid, tls_policy_valid=tls_valid,
            proxy_policy_valid=proxy_valid, upstream_evidence_valid=upstream_valid,
        )
    if factory is None or not callable(getattr(factory, "create_preflight_probe", None)):
        return _result(
            endpoint, policy, preflight, ("CONNECTIVITY_METADATA_NOT_READY", "TRANSPORT_FACTORY_REQUIRED"),
            endpoint_allowed=True, timeout_policy_valid=True, tls_policy_valid=True, proxy_policy_valid=True,
            upstream_evidence_valid=True,
        )
    try:
        probe = factory.create_preflight_probe(endpoint, policy)
    except Exception:
        return _result(
            endpoint, policy, preflight, ("CONNECTIVITY_METADATA_NOT_READY", "CONNECTIVITY_PROBE_REQUIRED"),
            factory_invoked=True, endpoint_allowed=True, timeout_policy_valid=True, tls_policy_valid=True,
            proxy_policy_valid=True, upstream_evidence_valid=True,
        )
    if probe is None or not callable(getattr(probe, "evaluate", None)):
        return _result(
            endpoint, policy, preflight, ("CONNECTIVITY_METADATA_NOT_READY", "CONNECTIVITY_PROBE_REQUIRED"),
            factory_invoked=True, endpoint_allowed=True, timeout_policy_valid=True, tls_policy_valid=True,
            proxy_policy_valid=True, upstream_evidence_valid=True,
        )
    try:
        accepted = probe.evaluate(preflight) is True
    except Exception:
        return _result(
            endpoint, policy, preflight, ("CONNECTIVITY_METADATA_NOT_READY",), factory_invoked=True,
            probe_invoked=True, endpoint_allowed=True, timeout_policy_valid=True, tls_policy_valid=True,
            proxy_policy_valid=True, upstream_evidence_valid=True,
        )
    if not accepted:
        return _result(
            endpoint, policy, preflight, ("CONNECTIVITY_METADATA_NOT_READY",), factory_invoked=True,
            probe_invoked=True, endpoint_allowed=True, timeout_policy_valid=True, tls_policy_valid=True,
            proxy_policy_valid=True, upstream_evidence_valid=True,
        )
    return _result(
        endpoint, policy, preflight, (), factory_invoked=True, probe_invoked=True, endpoint_allowed=True,
        timeout_policy_valid=True, tls_policy_valid=True, proxy_policy_valid=True, upstream_evidence_valid=True,
        ready=True,
    )


def build_provider_connectivity_audit_evidence_v1(
    endpoint: ProviderEndpointConfigurationV1, policy: ProviderTransportPolicyV1,
    preflight: ProviderConnectivityPreflightRequestV1, result: ProviderConnectivityPreflightResultV1,
) -> ProviderConnectivityAuditEvidenceV1:
    """Build immutable redacted evidence without invoking a factory or probe."""
    if not isinstance(endpoint, ProviderEndpointConfigurationV1) or not isinstance(policy, ProviderTransportPolicyV1) or not isinstance(preflight, ProviderConnectivityPreflightRequestV1) or not isinstance(result, ProviderConnectivityPreflightResultV1):
        raise ValueError("provider connectivity evidence requires contract records")
    if (preflight.endpoint_configuration_id != endpoint.endpoint_configuration_id
            or preflight.provider_id != endpoint.provider_id
            or preflight.request_route_id != endpoint.request_route_id
            or preflight.credential_reference_id != endpoint.credential_reference_id
            or result.preflight_request_id != preflight.preflight_request_id
            or result.endpoint_configuration_id != endpoint.endpoint_configuration_id
            or result.policy_id != policy.policy_id):
        raise ValueError("provider connectivity evidence identity mismatch")
    if any((result.DNS_resolved, result.socket_connected, result.TLS_established, result.authenticated,
            result.transmitted, result.provider_executed, result.retry_attempted, result.fallback_attempted)):
        raise ValueError("provider connectivity evidence operational mismatch")
    return ProviderConnectivityAuditEvidenceV1(
        preflight.preflight_request_id, endpoint.endpoint_configuration_id, policy.policy_id, endpoint.provider_id,
        endpoint.request_route_id, endpoint.credential_reference_id, preflight.provider_request_id,
        preflight.reservation_id, preflight.persistence_command_id, endpoint.endpoint_environment,
        endpoint.transport_scheme, result.timeout_policy_valid, result.TLS_policy_valid,
        result.proxy_policy_valid, result.upstream_evidence_valid, result.factory_invoked, result.probe_invoked,
        result.connectivity_metadata_ready, _ordered(result.failure_codes), False, False, False, False, False,
        False, False, False,
    )
