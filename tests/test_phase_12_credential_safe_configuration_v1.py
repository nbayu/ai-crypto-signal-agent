"""RED contract for Phase 12 credential-safe configuration metadata only."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from engine.phase_12_controlled_production_enablement_design_v1 import (
    build_phase_12_controlled_production_enablement_design_v1,
)
from engine.phase_12_credential_safe_configuration_v1 import (
    CredentialConfigurationValidationResultV1,
    CredentialReferenceV1,
    CredentialSafeConfigurationPolicyV1,
    CredentialSafeConfigurationV1,
    ProviderCredentialBindingV1,
    build_redacted_credential_configuration_evidence_v1,
    validate_credential_safe_configuration_v1,
)


_SENTINEL_SECRET = "sk-phase12-forbidden-secret-value"
_CREDENTIAL_KINDS = ("API_KEY", "ACCESS_TOKEN")
_REFERENCE_FIELDS = (
    "reference_id",
    "provider_id",
    "secret_namespace",
    "secret_name",
    "credential_kind",
    "version_label",
    "enabled",
)
_BINDING_FIELDS = (
    "binding_id",
    "provider_id",
    "route_id",
    "model_id",
    "credential_reference_id",
    "enabled",
)
_POLICY_FIELDS = (
    "allowed_provider_ids",
    "allowed_credential_kinds",
    "require_explicit_version_label",
    "require_unique_reference_ids",
    "require_unique_binding_ids",
    "require_provider_reference_match",
    "require_enabled_reference_for_enabled_binding",
    "allow_ambient_environment_discovery",
    "allow_direct_environment_read",
    "allow_secret_file_read",
    "allow_secret_value_serialization",
    "allow_secret_value_logging",
    "fail_closed",
)
_CONFIGURATION_FIELDS = (
    "configuration_id",
    "policy_version",
    "design_phase",
    "implementation_authorized",
    "credential_loading_authorized",
    "credential_verification_authorized",
    "provider_connectivity_authorized",
    "provider_execution_authorized",
    "credential_references",
    "provider_bindings",
)
_VALIDATION_FIELDS = (
    "configuration_id",
    "valid",
    "failure_codes",
    "validated_reference_ids",
    "validated_binding_ids",
    "credential_values_accessed",
    "environment_accessed",
    "secret_files_accessed",
    "provider_contacted",
    "execution_authorized",
)
_CANONICAL_FAILURE_CODES = {
    "CONFIGURATION_ID_EMPTY",
    "POLICY_VERSION_EMPTY",
    "DUPLICATE_REFERENCE_ID",
    "DUPLICATE_BINDING_ID",
    "REFERENCE_ID_EMPTY",
    "PROVIDER_ID_EMPTY",
    "SECRET_NAMESPACE_EMPTY",
    "SECRET_NAME_EMPTY",
    "VERSION_LABEL_EMPTY",
    "CREDENTIAL_KIND_NOT_ALLOWED",
    "PROVIDER_NOT_ALLOWED",
    "BINDING_REFERENCE_NOT_FOUND",
    "BINDING_PROVIDER_MISMATCH",
    "ENABLED_BINDING_REQUIRES_ENABLED_REFERENCE",
    "IDENTIFIER_NOT_NORMALIZED",
    "NO_PROVIDER_APPROVED",
    "IMPLEMENTATION_NOT_AUTHORIZED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "CREDENTIAL_VERIFICATION_NOT_AUTHORIZED",
    "PROVIDER_CONNECTIVITY_NOT_AUTHORIZED",
    "PROVIDER_EXECUTION_NOT_AUTHORIZED",
}
_FORBIDDEN_SECRET_FIELDS = {
    "value",
    "secret_value",
    "api_key",
    "token",
    "password",
    "authorization",
    "bearer",
    "private_key",
    "raw_secret",
}


def _assert_frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def _policy() -> CredentialSafeConfigurationPolicyV1:
    return CredentialSafeConfigurationPolicyV1(
        allowed_provider_ids=(),
        allowed_credential_kinds=_CREDENTIAL_KINDS,
        require_explicit_version_label=True,
        require_unique_reference_ids=True,
        require_unique_binding_ids=True,
        require_provider_reference_match=True,
        require_enabled_reference_for_enabled_binding=True,
        allow_ambient_environment_discovery=False,
        allow_direct_environment_read=False,
        allow_secret_file_read=False,
        allow_secret_value_serialization=False,
        allow_secret_value_logging=False,
        fail_closed=True,
    )


def _reference(*, enabled: bool = False) -> CredentialReferenceV1:
    return CredentialReferenceV1(
        reference_id="ref-primary-v1",
        provider_id="provider-primary",
        secret_namespace="phase12",
        secret_name="provider-primary-api-key",
        credential_kind="API_KEY",
        version_label="v1",
        enabled=enabled,
    )


def _binding(*, enabled: bool = False) -> ProviderCredentialBindingV1:
    return ProviderCredentialBindingV1(
        binding_id="binding-primary-v1",
        provider_id="provider-primary",
        route_id="route-primary",
        model_id="model-primary",
        credential_reference_id="ref-primary-v1",
        enabled=enabled,
    )


def _configuration(
    references: tuple[CredentialReferenceV1, ...] | None = None,
    bindings: tuple[ProviderCredentialBindingV1, ...] | None = None,
) -> CredentialSafeConfigurationV1:
    return CredentialSafeConfigurationV1(
        configuration_id="phase12-credential-safe-configuration-v1",
        policy_version="V1",
        design_phase="PHASE_12",
        implementation_authorized=False,
        credential_loading_authorized=False,
        credential_verification_authorized=False,
        provider_connectivity_authorized=False,
        provider_execution_authorized=False,
        credential_references=references if references is not None else (_reference(),),
        provider_bindings=bindings if bindings is not None else (_binding(),),
    )


def test_public_schemas_are_closed_immutable_and_secret_free() -> None:
    for schema, expected_fields in (
        (CredentialReferenceV1, _REFERENCE_FIELDS),
        (ProviderCredentialBindingV1, _BINDING_FIELDS),
        (CredentialSafeConfigurationPolicyV1, _POLICY_FIELDS),
        (CredentialSafeConfigurationV1, _CONFIGURATION_FIELDS),
        (CredentialConfigurationValidationResultV1, _VALIDATION_FIELDS),
    ):
        assert tuple(field.name for field in fields(schema)) == expected_fields
        assert type(schema).__class__ is type

    reference = _reference()
    binding = _binding()
    policy = _policy()
    configuration = _configuration()
    result = validate_credential_safe_configuration_v1(configuration, policy)
    for value in (reference, binding, policy, configuration, result):
        _assert_frozen_slotted(value)
        assert not _FORBIDDEN_SECRET_FIELDS.intersection(
            field.name for field in fields(value)
        )

    for value, field_name, replacement in (
        (reference, "enabled", True),
        (binding, "enabled", True),
        (policy, "fail_closed", False),
        (configuration, "provider_execution_authorized", True),
        (result, "execution_authorized", True),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(value, field_name, replacement)


def test_reference_binding_and_policy_validation_are_strict_and_fail_closed() -> None:
    assert _policy() == _policy()
    assert _policy().allowed_provider_ids == ()
    assert _policy().allowed_credential_kinds == _CREDENTIAL_KINDS
    assert (
        _policy().require_explicit_version_label,
        _policy().require_unique_reference_ids,
        _policy().require_unique_binding_ids,
        _policy().require_provider_reference_match,
        _policy().require_enabled_reference_for_enabled_binding,
        _policy().allow_ambient_environment_discovery,
        _policy().allow_direct_environment_read,
        _policy().allow_secret_file_read,
        _policy().allow_secret_value_serialization,
        _policy().allow_secret_value_logging,
        _policy().fail_closed,
    ) == (True, True, True, True, True, False, False, False, False, False, True)

    with pytest.raises(ValueError):
        CredentialReferenceV1(
            " ref-primary-v1",
            "provider-primary",
            "phase12",
            "provider-primary-api-key",
            "API_KEY",
            "v1",
            False,
        )
    with pytest.raises(ValueError):
        CredentialReferenceV1(
            "ref-primary-v1",
            "provider-primary",
            "phase12",
            "provider-primary-api-key",
            "PASSWORD",
            "v1",
            False,
        )
    with pytest.raises(ValueError):
        CredentialReferenceV1(
            "ref-primary-v1",
            "provider-primary",
            "phase12",
            "provider-primary-api-key",
            "API_KEY",
            "v1",
            1,
        )
    with pytest.raises(ValueError):
        ProviderCredentialBindingV1(
            "binding-primary-v1",
            "*",
            "route-primary",
            "model-primary",
            "ref-primary-v1",
            False,
        )
    with pytest.raises(TypeError):
        CredentialReferenceV1(
            **{
                field.name: getattr(_reference(), field.name)
                for field in fields(CredentialReferenceV1)
            },
            value=_SENTINEL_SECRET,
        )
    with pytest.raises(TypeError):
        ProviderCredentialBindingV1(
            **{
                field.name: getattr(_binding(), field.name)
                for field in fields(ProviderCredentialBindingV1)
            },
            api_key=_SENTINEL_SECRET,
        )


def test_empty_allowlist_is_structural_but_not_operationally_valid() -> None:
    configuration = _configuration()
    result = validate_credential_safe_configuration_v1(configuration, _policy())

    assert result.configuration_id == configuration.configuration_id
    assert result.valid is False
    assert "NO_PROVIDER_APPROVED" in result.failure_codes
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert len(result.failure_codes) == len(set(result.failure_codes))
    assert set(result.failure_codes).issubset(_CANONICAL_FAILURE_CODES)
    assert result.validated_reference_ids == ("ref-primary-v1",)
    assert result.validated_binding_ids == ("binding-primary-v1",)
    assert (
        result.credential_values_accessed,
        result.environment_accessed,
        result.secret_files_accessed,
        result.provider_contacted,
        result.execution_authorized,
    ) == (False, False, False, False, False)


def test_validator_returns_canonical_multiple_metadata_failures_without_access() -> None:
    duplicate_reference = CredentialReferenceV1(
        "ref-primary-v1",
        "provider-other",
        "phase12",
        "provider-other-api-key",
        "ACCESS_TOKEN",
        "v2",
        False,
    )
    missing_reference_binding = ProviderCredentialBindingV1(
        "binding-secondary-v1",
        "provider-other",
        "route-secondary",
        "model-secondary",
        "missing-reference",
        False,
    )
    configuration = _configuration(
        references=(_reference(), duplicate_reference),
        bindings=(_binding(), missing_reference_binding),
    )
    result = validate_credential_safe_configuration_v1(configuration, _policy())

    assert {
        "DUPLICATE_REFERENCE_ID",
        "BINDING_REFERENCE_NOT_FOUND",
        "NO_PROVIDER_APPROVED",
        "IMPLEMENTATION_NOT_AUTHORIZED",
        "CREDENTIAL_LOADING_NOT_AUTHORIZED",
        "CREDENTIAL_VERIFICATION_NOT_AUTHORIZED",
        "PROVIDER_CONNECTIVITY_NOT_AUTHORIZED",
        "PROVIDER_EXECUTION_NOT_AUTHORIZED",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert len(result.failure_codes) == len(set(result.failure_codes))
    assert not any(
        (
            result.credential_values_accessed,
            result.environment_accessed,
            result.secret_files_accessed,
            result.provider_contacted,
            result.execution_authorized,
        )
    )


def test_redacted_evidence_is_deterministic_and_has_no_secret_value_surface() -> None:
    configuration = _configuration()
    result = validate_credential_safe_configuration_v1(configuration, _policy())
    assert list(inspect.signature(build_redacted_credential_configuration_evidence_v1).parameters) == [
        "configuration",
        "validation_result",
    ]

    first = build_redacted_credential_configuration_evidence_v1(configuration, result)
    second = build_redacted_credential_configuration_evidence_v1(configuration, result)
    _assert_frozen_slotted(first)
    assert first == second
    assert first.configuration_id == configuration.configuration_id
    assert first.reference_ids == ("ref-primary-v1",)
    assert first.binding_ids == ("binding-primary-v1",)
    assert first.provider_ids == ("provider-primary",)
    assert first.credential_kinds == ("API_KEY",)
    assert first.validation_valid is False
    assert first.failure_codes == result.failure_codes
    assert (
        first.credential_values_accessed,
        first.environment_accessed,
        first.secret_files_accessed,
        first.provider_contacted,
        first.execution_authorized,
    ) == (False, False, False, False, False)
    rendered = repr(first) + str(first) + repr(configuration) + repr(result)
    assert _SENTINEL_SECRET not in rendered
    assert not _FORBIDDEN_SECRET_FIELDS.intersection(field.name for field in fields(first))
    with pytest.raises(TypeError):
        build_redacted_credential_configuration_evidence_v1(
            configuration, result, _SENTINEL_SECRET
        )


def test_upstream_design_alignment_and_no_operational_dependency_surface() -> None:
    design = build_phase_12_controlled_production_enablement_design_v1()
    matrix = design.authority_matrix
    assert design.implementation_authorized is False
    assert design.production_effect == "NONE"
    assert all(
        getattr(matrix, field_name) is False
        for field_name in (
            "credential_source_access_authorized",
            "credential_loading_authorized",
            "credential_verification_execution_authorized",
            "environment_read_authorized",
            "secret_file_read_authorized",
            "provider_authentication_authorized",
            "provider_connectivity_authorized",
            "provider_request_creation_authorized",
            "provider_transmission_authorized",
            "implementation_authorized",
            "trading_authorized",
        )
    )

    import engine.phase_12_credential_safe_configuration_v1 as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    prohibited_roots = {
        "aiohttp",
        "anthropic",
        "binance",
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
