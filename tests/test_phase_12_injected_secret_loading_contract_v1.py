"""RED contract for Phase 12 injected, fail-closed secret resolution."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, asdict, fields, is_dataclass
from pathlib import Path

import pytest

from engine.phase_12_controlled_production_enablement_design_v1 import (
    build_phase_12_controlled_production_enablement_design_v1,
)
from engine.phase_12_credential_safe_configuration_v1 import (
    CredentialReferenceV1,
    CredentialSafeConfigurationPolicyV1,
    CredentialSafeConfigurationV1,
    ProviderCredentialBindingV1,
    validate_credential_safe_configuration_v1,
)
from engine.phase_12_injected_secret_loading_contract_v1 import (
    SecretResolutionAuditEvidenceV1,
    SecretResolutionFailureV1,
    SecretResolutionRequestV1,
    SecretResolutionResultV1,
    SecretResolverV1,
    build_secret_resolution_audit_evidence_v1,
    resolve_secret_reference_v1,
)


_SENTINEL_SECRET = "phase12-test-secret-do-not-expose"
_FORBIDDEN_FIELDS = {
    "value",
    "secret_value",
    "api_key",
    "token",
    "password",
    "authorization",
    "bearer",
    "private_key",
    "raw_secret",
    "credential_bytes",
}
_REQUEST_FIELDS = (
    "request_id",
    "configuration_id",
    "credential_reference_id",
    "provider_id",
    "secret_namespace",
    "secret_name",
    "credential_kind",
    "version_label",
    "resolver_id",
    "resolution_authorized",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_RESULT_FIELDS = (
    "request_id",
    "credential_reference_id",
    "resolver_id",
    "resolved",
    "secret_present",
    "failure",
    "resolver_invoked",
    "credential_values_exposed",
    "secret_persisted",
    "environment_accessed",
    "secret_files_accessed",
    "external_secret_store_contacted",
    "credential_verified",
    "provider_authenticated",
    "provider_contacted",
    "execution_authorized",
)
_AUDIT_FIELDS = (
    "request_id",
    "configuration_id",
    "credential_reference_id",
    "provider_id",
    "credential_kind",
    "resolver_id",
    "resolution_authorized",
    "resolver_invoked",
    "resolved",
    "failure_code",
    "credential_values_exposed",
    "secret_persisted",
    "environment_accessed",
    "secret_files_accessed",
    "external_secret_store_contacted",
    "provider_contacted",
    "execution_authorized",
)
_FAILURE_CODES = {
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
}


class _SuccessfulResolver:
    resolver_id = "resolver-test-v1"

    def __init__(self) -> None:
        self.invocations = 0

    def resolve(self, request: SecretResolutionRequestV1) -> str:
        self.invocations += 1
        assert request.request_id == "request-test-v1"
        return _SENTINEL_SECRET


class _NotFoundResolver(_SuccessfulResolver):
    def resolve(self, request: SecretResolutionRequestV1) -> None:
        self.invocations += 1
        return None


class _EmptyResolver(_SuccessfulResolver):
    def resolve(self, request: SecretResolutionRequestV1) -> str:
        self.invocations += 1
        return ""


class _InvalidTypeResolver(_SuccessfulResolver):
    def resolve(self, request: SecretResolutionRequestV1) -> object:
        self.invocations += 1
        return object()


class _RejectingResolver(_SuccessfulResolver):
    def resolve(self, request: SecretResolutionRequestV1) -> SecretResolutionFailureV1:
        self.invocations += 1
        return SecretResolutionFailureV1(
            "RESOLVER_REJECTED_REQUEST", "request rejected", False
        )


class _ExceptionalResolver(_SuccessfulResolver):
    def resolve(self, request: SecretResolutionRequestV1) -> str:
        self.invocations += 1
        raise RuntimeError(f"resolver failure: {_SENTINEL_SECRET}")


class _MismatchedResolver(_SuccessfulResolver):
    resolver_id = "resolver-other-v1"


def _request(*, authorized: bool = False) -> SecretResolutionRequestV1:
    return SecretResolutionRequestV1(
        request_id="request-test-v1",
        configuration_id="configuration-test-v1",
        credential_reference_id="reference-test-v1",
        provider_id="provider-test-v1",
        secret_namespace="phase12",
        secret_name="provider-test-credential",
        credential_kind="API_KEY",
        version_label="v1",
        resolver_id="resolver-test-v1",
        resolution_authorized=authorized,
    )


def _assert_frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def _assert_zero_access(result: SecretResolutionResultV1) -> None:
    assert (
        result.credential_values_exposed,
        result.secret_persisted,
        result.environment_accessed,
        result.secret_files_accessed,
        result.external_secret_store_contacted,
        result.credential_verified,
        result.provider_authenticated,
        result.provider_contacted,
        result.execution_authorized,
    ) == (False, False, False, False, False, False, False, False, False)


def test_public_schemas_are_closed_immutable_and_request_is_metadata_only() -> None:
    for schema, expected in (
        (SecretResolutionRequestV1, _REQUEST_FIELDS),
        (SecretResolutionFailureV1, _FAILURE_FIELDS),
        (SecretResolutionResultV1, _RESULT_FIELDS),
        (SecretResolutionAuditEvidenceV1, _AUDIT_FIELDS),
    ):
        assert tuple(field.name for field in fields(schema)) == expected
        assert not _FORBIDDEN_FIELDS.intersection(field.name for field in fields(schema))

    request = _request()
    failure = SecretResolutionFailureV1(
        "SECRET_RESOLUTION_NOT_AUTHORIZED", "resolution is not authorized", False
    )
    result = resolve_secret_reference_v1(request, _SuccessfulResolver())
    audit = build_secret_resolution_audit_evidence_v1(request, result)
    for value in (request, failure, result, audit):
        _assert_frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        request.resolution_authorized = True  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        failure.retryable = True  # type: ignore[misc]
    with pytest.raises(TypeError):
        SecretResolutionRequestV1(
            **{field.name: getattr(request, field.name) for field in fields(request)},
            value=_SENTINEL_SECRET,
        )

    assert hasattr(SecretResolverV1, "resolve")
    assert tuple(inspect.signature(SecretResolverV1.resolve).parameters) == (
        "self",
        "request",
    )


def test_unauthorized_resolution_fails_before_injected_resolver_invocation() -> None:
    resolver = _SuccessfulResolver()
    result = resolve_secret_reference_v1(_request(authorized=False), resolver)

    assert resolver.invocations == 0
    assert result.resolved is False
    assert result.secret_present is False
    assert result.resolver_invoked is False
    assert result.failure == SecretResolutionFailureV1(
        "SECRET_RESOLUTION_NOT_AUTHORIZED", "secret resolution is not authorized", False
    )
    _assert_zero_access(result)


@pytest.mark.parametrize(
    ("resolver_type", "expected_code"),
    (
        (_NotFoundResolver, "SECRET_NOT_FOUND"),
        (_EmptyResolver, "SECRET_EMPTY"),
        (_InvalidTypeResolver, "SECRET_TYPE_INVALID"),
        (_RejectingResolver, "RESOLVER_REJECTED_REQUEST"),
        (_ExceptionalResolver, "RESOLVER_FAILURE"),
    ),
)
def test_injected_fake_resolver_failures_are_single_attempt_and_redacted(
    resolver_type: type[_SuccessfulResolver], expected_code: str
) -> None:
    resolver = resolver_type()
    result = resolve_secret_reference_v1(_request(authorized=True), resolver)

    assert resolver.invocations == 1
    assert result.resolver_invoked is True
    assert result.resolved is False
    assert result.secret_present is False
    assert result.failure is not None
    assert result.failure.failure_code == expected_code
    assert result.failure.retryable is False
    assert _SENTINEL_SECRET not in repr(result) + str(result) + repr(result.failure)
    _assert_zero_access(result)


def test_success_is_transient_non_secret_evidence_only() -> None:
    resolver = _SuccessfulResolver()
    result = resolve_secret_reference_v1(_request(authorized=True), resolver)

    assert resolver.invocations == 1
    assert result.resolved is True
    assert result.secret_present is True
    assert result.failure is None
    assert result.resolver_invoked is True
    assert _SENTINEL_SECRET not in repr(result) + str(result) + repr(asdict(result))
    _assert_zero_access(result)


def test_request_validation_resolver_identity_and_audit_identity_are_fail_closed() -> None:
    with pytest.raises(ValueError):
        SecretResolutionRequestV1(
            " request-test-v1",
            "configuration-test-v1",
            "reference-test-v1",
            "provider-test-v1",
            "phase12",
            "provider-test-credential",
            "API_KEY",
            "v1",
            "resolver-test-v1",
            False,
        )
    with pytest.raises(ValueError):
        SecretResolutionRequestV1(
            "request-test-v1",
            "configuration-test-v1",
            "reference-test-v1",
            "*",
            "phase12",
            "provider-test-credential",
            "PASSWORD",
            "v1",
            "resolver-test-v1",
            1,
        )

    mismatch = _MismatchedResolver()
    result = resolve_secret_reference_v1(_request(authorized=True), mismatch)
    assert mismatch.invocations == 0
    assert result.failure is not None
    assert result.failure.failure_code == "RESOLVER_ID_MISMATCH"
    _assert_zero_access(result)

    valid_result = resolve_secret_reference_v1(_request(), _SuccessfulResolver())
    other_request = SecretResolutionRequestV1(
        "request-other-v1",
        "configuration-test-v1",
        "reference-test-v1",
        "provider-test-v1",
        "phase12",
        "provider-test-credential",
        "API_KEY",
        "v1",
        "resolver-test-v1",
        False,
    )
    with pytest.raises(ValueError):
        build_secret_resolution_audit_evidence_v1(other_request, valid_result)


def test_redacted_audit_evidence_contains_only_non_secret_result_metadata() -> None:
    request = _request(authorized=True)
    result = resolve_secret_reference_v1(request, _SuccessfulResolver())
    first = build_secret_resolution_audit_evidence_v1(request, result)
    second = build_secret_resolution_audit_evidence_v1(request, result)

    assert first == second
    assert (
        first.request_id,
        first.configuration_id,
        first.credential_reference_id,
        first.provider_id,
        first.credential_kind,
        first.resolver_id,
        first.resolution_authorized,
        first.resolver_invoked,
        first.resolved,
        first.failure_code,
    ) == (
        request.request_id,
        request.configuration_id,
        request.credential_reference_id,
        request.provider_id,
        request.credential_kind,
        request.resolver_id,
        True,
        True,
        True,
        None,
    )
    assert _SENTINEL_SECRET not in repr(first) + str(first) + repr(asdict(first))
    assert not _FORBIDDEN_FIELDS.intersection(field.name for field in fields(first))
    assert (
        first.credential_values_exposed,
        first.secret_persisted,
        first.environment_accessed,
        first.secret_files_accessed,
        first.external_secret_store_contacted,
        first.provider_contacted,
        first.execution_authorized,
    ) == (False, False, False, False, False, False, False)


def test_upstream_configuration_and_authority_alignment() -> None:
    reference = CredentialReferenceV1(
        "reference-test-v1",
        "provider-test-v1",
        "phase12",
        "provider-test-credential",
        "API_KEY",
        "v1",
        True,
    )
    binding = ProviderCredentialBindingV1(
        "binding-test-v1",
        "provider-test-v1",
        "route-test-v1",
        "model-test-v1",
        "reference-test-v1",
        True,
    )
    configuration = CredentialSafeConfigurationV1(
        "configuration-test-v1",
        "V1",
        "PHASE_12",
        False,
        False,
        False,
        False,
        False,
        (reference,),
        (binding,),
    )
    policy = CredentialSafeConfigurationPolicyV1(
        (),
        ("API_KEY", "ACCESS_TOKEN"),
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        True,
    )
    validation = validate_credential_safe_configuration_v1(configuration, policy)
    request = _request()
    assert (
        request.credential_reference_id,
        request.provider_id,
        request.secret_namespace,
        request.secret_name,
        request.credential_kind,
        request.version_label,
    ) == (
        reference.reference_id,
        reference.provider_id,
        reference.secret_namespace,
        reference.secret_name,
        reference.credential_kind,
        reference.version_label,
    )
    assert validation.valid is False
    assert "NO_PROVIDER_APPROVED" in validation.failure_codes
    assert resolve_secret_reference_v1(request, _SuccessfulResolver()).failure is not None

    matrix = build_phase_12_controlled_production_enablement_design_v1().authority_matrix
    assert all(
        getattr(matrix, name) is False
        for name in (
            "credential_source_access_authorized",
            "credential_loading_authorized",
            "credential_verification_execution_authorized",
            "environment_read_authorized",
            "secret_file_read_authorized",
            "provider_authentication_authorized",
            "provider_connectivity_authorized",
            "provider_transmission_authorized",
            "provider_retry_authorized",
            "trading_authorized",
        )
    )


def test_module_has_no_ambient_or_operational_dependency_surface() -> None:
    import engine.phase_12_injected_secret_loading_contract_v1 as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    prohibited_roots = {
        "aiohttp",
        "anthropic",
        "boto3",
        "ccxt",
        "dotenv",
        "http",
        "httpx",
        "keyring",
        "openai",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "sys",
        "telegram",
        "urllib",
    }
    prohibited_names = {
        "__import__",
        "environ",
        "getenv",
        "logging",
        "open",
        "print",
        "read_bytes",
        "read_text",
    }
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not prohibited_roots.intersection(imported_roots)
    assert not prohibited_roots.intersection(used_names)
    assert not prohibited_names.intersection(used_names)
