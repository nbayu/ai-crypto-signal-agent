"""RED contract for an injected, non-provider credential verification boundary."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, asdict, fields, is_dataclass
from pathlib import Path

import pytest

from engine.phase_12_controlled_production_enablement_design_v1 import (
    build_phase_12_controlled_production_enablement_design_v1,
)
from engine.phase_12_credential_verification_boundary_v1 import (
    CredentialVerificationAuditEvidenceV1,
    CredentialVerificationFailureV1,
    CredentialVerificationRequestV1,
    CredentialVerificationResultV1,
    CredentialVerifierV1,
    build_credential_verification_audit_evidence_v1,
    verify_credential_reference_v1,
)


_SENTINEL = "phase12-verifier-sentinel-not-for-output"
_REQUEST_FIELDS = (
    "verification_request_id", "secret_resolution_request_id", "configuration_id",
    "credential_reference_id", "provider_id", "credential_kind", "version_label",
    "verifier_id", "secret_resolution_succeeded", "secret_present",
    "verification_authorized",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_RESULT_FIELDS = (
    "verification_request_id", "credential_reference_id", "verifier_id",
    "verification_attempted", "verifier_invoked", "credential_verified", "failure",
    "credential_values_exposed", "secret_persisted", "environment_accessed",
    "secret_files_accessed", "external_secret_store_contacted", "provider_authenticated",
    "provider_contacted", "provider_connectivity_proven", "request_creation_authorized",
    "provider_execution_authorized", "execution_authorized",
)
_AUDIT_FIELDS = (
    "verification_request_id", "secret_resolution_request_id", "configuration_id",
    "credential_reference_id", "provider_id", "credential_kind", "verifier_id",
    "secret_resolution_succeeded", "secret_present", "verification_authorized",
    "verification_attempted", "verifier_invoked", "credential_verified", "failure_code",
    "credential_values_exposed", "secret_persisted", "environment_accessed",
    "secret_files_accessed", "external_secret_store_contacted", "provider_contacted",
    "provider_connectivity_proven", "request_creation_authorized",
    "provider_execution_authorized", "execution_authorized",
)
_FORBIDDEN_FIELDS = {
    "value", "secret_value", "api_key", "token", "password", "authorization",
    "bearer", "private_key", "raw_secret", "credential_bytes",
}


class _Verifier:
    verifier_id = "verifier-test-v1"

    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.invocations = 0

    def verify(self, request: CredentialVerificationRequestV1) -> object:
        self.invocations += 1
        return self.outcome


class _ExceptionalVerifier(_Verifier):
    def __init__(self) -> None:
        super().__init__(False)

    def verify(self, request: CredentialVerificationRequestV1) -> object:
        self.invocations += 1
        raise RuntimeError(f"untrusted verifier text {_SENTINEL}")


class _MismatchedVerifier(_Verifier):
    verifier_id = "verifier-other-v1"


def _request(
    *, succeeded: bool = True, present: bool = True, authorized: bool = False
) -> CredentialVerificationRequestV1:
    return CredentialVerificationRequestV1(
        "verification-request-v1", "secret-resolution-request-v1", "configuration-v1",
        "credential-reference-v1", "provider-v1", "API_KEY", "v1", "verifier-test-v1",
        succeeded, present, authorized,
    )


def _assert_frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def _assert_downstream_denied(result: CredentialVerificationResultV1) -> None:
    assert (
        result.credential_values_exposed, result.secret_persisted, result.environment_accessed,
        result.secret_files_accessed, result.external_secret_store_contacted,
        result.provider_authenticated, result.provider_contacted,
        result.provider_connectivity_proven, result.request_creation_authorized,
        result.provider_execution_authorized, result.execution_authorized,
    ) == (False,) * 11


def test_public_contract_is_closed_immutable_and_secret_free() -> None:
    for schema, expected in (
        (CredentialVerificationRequestV1, _REQUEST_FIELDS),
        (CredentialVerificationFailureV1, _FAILURE_FIELDS),
        (CredentialVerificationResultV1, _RESULT_FIELDS),
        (CredentialVerificationAuditEvidenceV1, _AUDIT_FIELDS),
    ):
        assert tuple(field.name for field in fields(schema)) == expected
        assert not _FORBIDDEN_FIELDS.intersection(field.name for field in fields(schema))
    request = _request()
    result = verify_credential_reference_v1(request, _Verifier(True))
    evidence = build_credential_verification_audit_evidence_v1(request, result)
    for value in (request, result, evidence):
        _assert_frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        request.verification_authorized = True  # type: ignore[misc]
    with pytest.raises(TypeError):
        CredentialVerificationRequestV1(
            **{field.name: getattr(request, field.name) for field in fields(request)},
            value=_SENTINEL,
        )
    assert tuple(inspect.signature(CredentialVerifierV1.verify).parameters) == ("self", "request")


@pytest.mark.parametrize(
    ("request", "verifier", "code"),
    (
        (_request(succeeded=False), _Verifier(True), "SECRET_RESOLUTION_NOT_SUCCESSFUL"),
        (_request(present=False), _Verifier(True), "SECRET_NOT_PRESENT"),
        (_request(authorized=False), _Verifier(True), "CREDENTIAL_VERIFICATION_NOT_AUTHORIZED"),
        (_request(authorized=True), None, "VERIFIER_REQUIRED"),
        (_request(authorized=True), _MismatchedVerifier(True), "VERIFIER_ID_MISMATCH"),
    ),
)
def test_preconditions_fail_before_verifier_invocation(
    request: CredentialVerificationRequestV1, verifier: object, code: str
) -> None:
    result = verify_credential_reference_v1(request, verifier)
    if verifier is not None:
        assert verifier.invocations == 0
    assert result.verification_attempted is False
    assert result.verifier_invoked is False
    assert result.credential_verified is False
    assert result.failure is not None and result.failure.failure_code == code
    _assert_downstream_denied(result)


@pytest.mark.parametrize(
    ("outcome", "code"),
    (
        (CredentialVerificationFailureV1("CREDENTIAL_INVALID", "credential invalid", False), "CREDENTIAL_INVALID"),
        (CredentialVerificationFailureV1("CREDENTIAL_DISABLED", "credential disabled", False), "CREDENTIAL_DISABLED"),
        (CredentialVerificationFailureV1("CREDENTIAL_EXPIRED", "credential expired", False), "CREDENTIAL_EXPIRED"),
        (CredentialVerificationFailureV1("CREDENTIAL_SCOPE_INSUFFICIENT", "scope insufficient", False), "CREDENTIAL_SCOPE_INSUFFICIENT"),
        (CredentialVerificationFailureV1("VERIFIER_REJECTED_REQUEST", "request rejected", False), "VERIFIER_REJECTED_REQUEST"),
    ),
)
def test_fake_verifier_failures_are_single_attempt_non_retryable_and_redacted(
    outcome: CredentialVerificationFailureV1, code: str
) -> None:
    verifier = _Verifier(outcome)
    result = verify_credential_reference_v1(_request(authorized=True), verifier)
    assert verifier.invocations == 1
    assert result.verification_attempted is True and result.verifier_invoked is True
    assert result.credential_verified is False
    assert result.failure is not None and result.failure.failure_code == code
    assert result.failure.retryable is False
    assert _SENTINEL not in repr(result) + str(result) + repr(result.failure)
    _assert_downstream_denied(result)


def test_success_and_exception_remain_separate_from_provider_authority() -> None:
    success = _Verifier(True)
    result = verify_credential_reference_v1(_request(authorized=True), success)
    assert success.invocations == 1
    assert (result.verification_attempted, result.verifier_invoked, result.credential_verified) == (True, True, True)
    assert result.failure is None
    _assert_downstream_denied(result)

    exceptional = _ExceptionalVerifier()
    failed = verify_credential_reference_v1(_request(authorized=True), exceptional)
    assert exceptional.invocations == 1
    assert failed.failure is not None and failed.failure.failure_code == "VERIFIER_FAILURE"
    assert _SENTINEL not in repr(failed) + str(failed) + repr(failed.failure)
    _assert_downstream_denied(failed)


def test_request_validation_audit_identity_and_metadata_only_evidence() -> None:
    with pytest.raises(ValueError):
        CredentialVerificationRequestV1(
            " verification-request-v1", "secret-resolution-request-v1", "configuration-v1",
            "credential-reference-v1", "provider-v1", "PASSWORD", "v1", "verifier-test-v1",
            True, True, 1,
        )
    request = _request(authorized=True)
    result = verify_credential_reference_v1(request, _Verifier(True))
    first = build_credential_verification_audit_evidence_v1(request, result)
    second = build_credential_verification_audit_evidence_v1(request, result)
    assert first == second
    assert first.verification_request_id == request.verification_request_id
    assert first.credential_verified is True and first.failure_code is None
    assert _SENTINEL not in repr(first) + str(first) + repr(asdict(first))
    other = CredentialVerificationRequestV1(
        "other-request-v1", "secret-resolution-request-v1", "configuration-v1",
        "credential-reference-v1", "provider-v1", "API_KEY", "v1", "verifier-test-v1",
        True, True, True,
    )
    with pytest.raises(ValueError):
        build_credential_verification_audit_evidence_v1(other, result)


def test_upstream_authorities_remain_denied_and_module_is_pure() -> None:
    matrix = build_phase_12_controlled_production_enablement_design_v1().authority_matrix
    assert build_phase_12_controlled_production_enablement_design_v1().production_effect == "NONE"
    assert all(getattr(matrix, name) is False for name in (
        "credential_verification_execution_authorized", "provider_authentication_authorized",
        "provider_connectivity_authorized", "provider_request_creation_authorized",
        "provider_transmission_authorized", "provider_retry_authorized",
        "reservation_creation_authorized", "runtime_invocation_authorized",
        "production_publication_authorized", "telegram_publication_authorized",
        "launch_authorized", "trading_authorized",
    ))
    import engine.phase_12_credential_verification_boundary_v1 as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    prohibited = {"aiohttp", "anthropic", "boto3", "ccxt", "dotenv", "http", "httpx", "keyring", "openai", "os", "pathlib", "requests", "socket", "subprocess", "telegram", "urllib"}
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not prohibited.intersection(imports | names)
    assert not {"__import__", "environ", "getenv", "open", "print", "logging", "read_text", "read_bytes"}.intersection(names)
