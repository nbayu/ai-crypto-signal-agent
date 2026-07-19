"""Pure, secret-free Phase 12 credential configuration metadata domain."""

from __future__ import annotations

from dataclasses import dataclass


_CREDENTIAL_KINDS = ("API_KEY", "ACCESS_TOKEN")


def _require_normalized_text(value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("identifier must be a non-empty normalized string")


def _require_boolean(value: bool) -> None:
    if type(value) is not bool:
        raise ValueError("boolean value must be strict")


@dataclass(frozen=True, slots=True)
class CredentialReferenceV1:
    reference_id: str
    provider_id: str
    secret_namespace: str
    secret_name: str
    credential_kind: str
    version_label: str
    enabled: bool

    def __post_init__(self) -> None:
        for value in (
            self.reference_id,
            self.provider_id,
            self.secret_namespace,
            self.secret_name,
            self.version_label,
        ):
            _require_normalized_text(value)
        if self.credential_kind not in _CREDENTIAL_KINDS:
            raise ValueError("credential kind is not allowed")
        _require_boolean(self.enabled)


@dataclass(frozen=True, slots=True)
class ProviderCredentialBindingV1:
    binding_id: str
    provider_id: str
    route_id: str
    model_id: str
    credential_reference_id: str
    enabled: bool

    def __post_init__(self) -> None:
        for value in (
            self.binding_id,
            self.provider_id,
            self.route_id,
            self.model_id,
            self.credential_reference_id,
        ):
            _require_normalized_text(value)
            if "*" in value:
                raise ValueError("wildcard identities are not allowed")
        _require_boolean(self.enabled)


@dataclass(frozen=True, slots=True)
class CredentialSafeConfigurationPolicyV1:
    allowed_provider_ids: tuple[str, ...]
    allowed_credential_kinds: tuple[str, ...]
    require_explicit_version_label: bool
    require_unique_reference_ids: bool
    require_unique_binding_ids: bool
    require_provider_reference_match: bool
    require_enabled_reference_for_enabled_binding: bool
    allow_ambient_environment_discovery: bool
    allow_direct_environment_read: bool
    allow_secret_file_read: bool
    allow_secret_value_serialization: bool
    allow_secret_value_logging: bool
    fail_closed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_provider_ids, tuple):
            raise ValueError("provider allowlist must be immutable")
        if self.allowed_credential_kinds != _CREDENTIAL_KINDS:
            raise ValueError("credential-kind allowlist must remain frozen")
        for provider_id in self.allowed_provider_ids:
            _require_normalized_text(provider_id)
            if "*" in provider_id:
                raise ValueError("wildcard providers are not allowed")
        for value in (
            self.require_explicit_version_label,
            self.require_unique_reference_ids,
            self.require_unique_binding_ids,
            self.require_provider_reference_match,
            self.require_enabled_reference_for_enabled_binding,
            self.allow_ambient_environment_discovery,
            self.allow_direct_environment_read,
            self.allow_secret_file_read,
            self.allow_secret_value_serialization,
            self.allow_secret_value_logging,
            self.fail_closed,
        ):
            _require_boolean(value)
        if (
            self.allow_ambient_environment_discovery
            or self.allow_direct_environment_read
            or self.allow_secret_file_read
            or self.allow_secret_value_serialization
            or self.allow_secret_value_logging
            or not self.fail_closed
        ):
            raise ValueError("credential-safe policy is fail closed")


@dataclass(frozen=True, slots=True)
class CredentialSafeConfigurationV1:
    configuration_id: str
    policy_version: str
    design_phase: str
    implementation_authorized: bool
    credential_loading_authorized: bool
    credential_verification_authorized: bool
    provider_connectivity_authorized: bool
    provider_execution_authorized: bool
    credential_references: tuple[CredentialReferenceV1, ...]
    provider_bindings: tuple[ProviderCredentialBindingV1, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.credential_references, tuple) or not isinstance(
            self.provider_bindings, tuple
        ):
            raise ValueError("configuration collections must be immutable")
        if self.design_phase != "PHASE_12":
            raise ValueError("configuration is limited to Phase 12")
        for value in (
            self.implementation_authorized,
            self.credential_loading_authorized,
            self.credential_verification_authorized,
            self.provider_connectivity_authorized,
            self.provider_execution_authorized,
        ):
            _require_boolean(value)
            if value:
                raise ValueError("configuration grants no authority")


@dataclass(frozen=True, slots=True)
class CredentialConfigurationValidationResultV1:
    configuration_id: str
    valid: bool
    failure_codes: tuple[str, ...]
    validated_reference_ids: tuple[str, ...]
    validated_binding_ids: tuple[str, ...]
    credential_values_accessed: bool
    environment_accessed: bool
    secret_files_accessed: bool
    provider_contacted: bool
    execution_authorized: bool


@dataclass(frozen=True, slots=True)
class _RedactedCredentialConfigurationEvidenceV1:
    configuration_id: str
    reference_ids: tuple[str, ...]
    binding_ids: tuple[str, ...]
    provider_ids: tuple[str, ...]
    credential_kinds: tuple[str, ...]
    enabled_reference_ids: tuple[str, ...]
    enabled_binding_ids: tuple[str, ...]
    validation_valid: bool
    failure_codes: tuple[str, ...]
    credential_values_accessed: bool
    environment_accessed: bool
    secret_files_accessed: bool
    provider_contacted: bool
    execution_authorized: bool


def _add_failure(failure_codes: tuple[str, ...], code: str) -> tuple[str, ...]:
    if code in failure_codes:
        return failure_codes
    return (*failure_codes, code)


def _is_normalized_text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def validate_credential_safe_configuration_v1(
    configuration: CredentialSafeConfigurationV1,
    policy: CredentialSafeConfigurationPolicyV1,
) -> CredentialConfigurationValidationResultV1:
    """Validate metadata only; credentials, files, environments, and providers stay untouched."""

    failure_codes: tuple[str, ...] = ()
    if not _is_normalized_text(configuration.configuration_id):
        failure_codes = _add_failure(failure_codes, "CONFIGURATION_ID_EMPTY")
    if not _is_normalized_text(configuration.policy_version):
        failure_codes = _add_failure(failure_codes, "POLICY_VERSION_EMPTY")

    reference_ids = tuple(reference.reference_id for reference in configuration.credential_references)
    binding_ids = tuple(binding.binding_id for binding in configuration.provider_bindings)
    if policy.require_unique_reference_ids and len(reference_ids) != len(set(reference_ids)):
        failure_codes = _add_failure(failure_codes, "DUPLICATE_REFERENCE_ID")
    if policy.require_unique_binding_ids and len(binding_ids) != len(set(binding_ids)):
        failure_codes = _add_failure(failure_codes, "DUPLICATE_BINDING_ID")

    for reference in configuration.credential_references:
        if not _is_normalized_text(reference.reference_id):
            failure_codes = _add_failure(failure_codes, "REFERENCE_ID_EMPTY")
        if not _is_normalized_text(reference.provider_id):
            failure_codes = _add_failure(failure_codes, "PROVIDER_ID_EMPTY")
        if not _is_normalized_text(reference.secret_namespace):
            failure_codes = _add_failure(failure_codes, "SECRET_NAMESPACE_EMPTY")
        if not _is_normalized_text(reference.secret_name):
            failure_codes = _add_failure(failure_codes, "SECRET_NAME_EMPTY")
        if not _is_normalized_text(reference.version_label):
            failure_codes = _add_failure(failure_codes, "VERSION_LABEL_EMPTY")
        if not all(
            _is_normalized_text(value)
            for value in (
                reference.reference_id,
                reference.provider_id,
                reference.secret_namespace,
                reference.secret_name,
                reference.version_label,
            )
        ):
            failure_codes = _add_failure(failure_codes, "IDENTIFIER_NOT_NORMALIZED")
        if reference.credential_kind not in policy.allowed_credential_kinds:
            failure_codes = _add_failure(failure_codes, "CREDENTIAL_KIND_NOT_ALLOWED")
        if reference.provider_id not in policy.allowed_provider_ids:
            failure_codes = _add_failure(failure_codes, "PROVIDER_NOT_ALLOWED")

    for binding in configuration.provider_bindings:
        reference = next(
            (
                candidate
                for candidate in configuration.credential_references
                if candidate.reference_id == binding.credential_reference_id
            ),
            None,
        )
        if reference is None:
            failure_codes = _add_failure(failure_codes, "BINDING_REFERENCE_NOT_FOUND")
            continue
        if (
            policy.require_provider_reference_match
            and binding.provider_id != reference.provider_id
        ):
            failure_codes = _add_failure(failure_codes, "BINDING_PROVIDER_MISMATCH")
        if (
            policy.require_enabled_reference_for_enabled_binding
            and binding.enabled
            and not reference.enabled
        ):
            failure_codes = _add_failure(
                failure_codes, "ENABLED_BINDING_REQUIRES_ENABLED_REFERENCE"
            )

    if not policy.allowed_provider_ids:
        failure_codes = _add_failure(failure_codes, "NO_PROVIDER_APPROVED")
    if not configuration.implementation_authorized:
        failure_codes = _add_failure(failure_codes, "IMPLEMENTATION_NOT_AUTHORIZED")
    if not configuration.credential_loading_authorized:
        failure_codes = _add_failure(failure_codes, "CREDENTIAL_LOADING_NOT_AUTHORIZED")
    if not configuration.credential_verification_authorized:
        failure_codes = _add_failure(
            failure_codes, "CREDENTIAL_VERIFICATION_NOT_AUTHORIZED"
        )
    if not configuration.provider_connectivity_authorized:
        failure_codes = _add_failure(
            failure_codes, "PROVIDER_CONNECTIVITY_NOT_AUTHORIZED"
        )
    if not configuration.provider_execution_authorized:
        failure_codes = _add_failure(failure_codes, "PROVIDER_EXECUTION_NOT_AUTHORIZED")

    return CredentialConfigurationValidationResultV1(
        configuration_id=configuration.configuration_id,
        valid=False,
        failure_codes=tuple(sorted(failure_codes)),
        validated_reference_ids=tuple(sorted(set(reference_ids))),
        validated_binding_ids=tuple(sorted(set(binding_ids))),
        credential_values_accessed=False,
        environment_accessed=False,
        secret_files_accessed=False,
        provider_contacted=False,
        execution_authorized=False,
    )


def build_redacted_credential_configuration_evidence_v1(
    configuration: CredentialSafeConfigurationV1,
    validation_result: CredentialConfigurationValidationResultV1,
) -> _RedactedCredentialConfigurationEvidenceV1:
    """Return immutable metadata evidence without resolving any credential reference."""

    references = configuration.credential_references
    bindings = configuration.provider_bindings
    return _RedactedCredentialConfigurationEvidenceV1(
        configuration_id=configuration.configuration_id,
        reference_ids=tuple(sorted({reference.reference_id for reference in references})),
        binding_ids=tuple(sorted({binding.binding_id for binding in bindings})),
        provider_ids=tuple(sorted({reference.provider_id for reference in references})),
        credential_kinds=tuple(
            sorted({reference.credential_kind for reference in references})
        ),
        enabled_reference_ids=tuple(
            sorted(reference.reference_id for reference in references if reference.enabled)
        ),
        enabled_binding_ids=tuple(
            sorted(binding.binding_id for binding in bindings if binding.enabled)
        ),
        validation_valid=validation_result.valid,
        failure_codes=validation_result.failure_codes,
        credential_values_accessed=False,
        environment_accessed=False,
        secret_files_accessed=False,
        provider_contacted=False,
        execution_authorized=False,
    )
