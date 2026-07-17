"""RED contract for explicit, ephemeral Phase 11 provider credentials."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.phase_11_provider_credential_boundary_v1 import (
    CredentialFailureV1,
    CredentialResolutionStatusV1,
    CredentialSourceKindV1,
    EphemeralProviderCredentialV1,
    ProviderCredentialReferenceV1,
    ProviderCredentialResolutionV1,
    ProviderCredentialResolverProtocol,
    ProviderCredentialValidationError,
    canonical_json_bytes,
    lowercase_sha256,
    resolve_provider_credential,
)
from engine.phase_11_shadow_provider_runtime_v1 import (
    ShadowProviderInvocationResultV1,
    ShadowProviderInvocationV1,
    ShadowProviderRuntimeV1,
)


UTC = timezone.utc
SYNTHETIC_BYTES = b"synthetic-test-credential"
SYNTHETIC_TEXT = "synthetic-test-credential-text"
PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
FAILURES = (
    "NONE", "VALIDATION_FAILURE", "REFERENCE_NOT_FOUND", "PROVIDER_MISMATCH",
    "VERSION_MISMATCH", "NOT_YET_VALID", "EXPIRED", "ROTATION_REQUIRED",
    "RESOLVER_FAILURE", "MALFORMED_RESOLUTION", "UNAUTHORIZED_SOURCE",
    "IDENTITY_MISMATCH",
)


def _canonical(value):
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _sha(value):
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _reject(factory, **values):
    with pytest.raises((TypeError, ValueError, ProviderCredentialValidationError)):
        factory(**values)


def _reference_values(provider="DEEPSEEK", **overrides):
    values = {
        "schema_version": "phase11-provider-credential-reference-v1",
        "credential_reference_id": "credential-reference-001",
        "provider": provider,
        "credential_version": 1,
        "source_kind": "TEST_FIXTURE",
        "owner_approval_reference": "owner-approval-001",
        "created_at": "2026-07-17T00:00:00Z",
        "valid_from": "2026-07-17T00:00:00Z",
        "valid_until": "2026-07-18T00:00:00Z",
        "rotation_required": False,
        "reference_identity": None,
    }
    values.update(overrides)
    return values


def _reference(provider="DEEPSEEK", **overrides):
    return ProviderCredentialReferenceV1(**_reference_values(provider, **overrides))


def _ephemeral_values(reference=None, material=SYNTHETIC_BYTES, **overrides):
    reference = _reference() if reference is None else reference
    values = {
        "schema_version": "phase11-ephemeral-provider-credential-v1",
        "provider": reference.provider,
        "credential_reference": reference,
        "credential_reference_identity": reference.identity,
        "credential_version": reference.credential_version,
        "material": material,
    }
    values.update(overrides)
    return values


def _ephemeral(reference=None, material=SYNTHETIC_BYTES, **overrides):
    return EphemeralProviderCredentialV1(**_ephemeral_values(reference, material, **overrides))


def _resolution_values(reference=None, credential=None, **overrides):
    reference = _reference() if reference is None else reference
    credential = _ephemeral(reference) if credential is None else credential
    values = {
        "schema_version": "phase11-provider-credential-resolution-v1",
        "resolution_identity": None,
        "credential_reference": reference,
        "credential_reference_identity": reference.identity,
        "provider": reference.provider,
        "credential_version": reference.credential_version,
        "status": "RESOLVED",
        "failure_class": "NONE",
        "resolved_at": "2026-07-17T00:05:00Z",
        "valid_until": reference.valid_until,
        "rotation_required": reference.rotation_required,
        "reason_codes": ("CREDENTIAL_RESOLVED",),
        "ephemeral_credential": credential,
    }
    values.update(overrides)
    return values


def _resolution(reference=None, credential=None, **overrides):
    return ProviderCredentialResolutionV1(**_resolution_values(reference, credential, **overrides))


class _FakeResolver:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def resolve(self, reference, resolved_at):
        self.calls.append((reference, resolved_at))
        if self.error is not None:
            raise self.error
        return self.result


class TestSafeCredentialReference:
    def test_reference_is_closed_immutable_safe_and_canonical(self):
        deepseek = _reference()
        anthropic = _reference("ANTHROPIC", credential_reference_id="credential-reference-002")
        assert deepseek.provider == "DEEPSEEK"
        assert anthropic.provider == "ANTHROPIC"
        assert deepseek.identity == _reference().identity
        assert deepseek.identity != anthropic.identity
        assert deepseek.reference_identity == deepseek.identity
        with pytest.raises((AttributeError, TypeError)):
            deepseek.provider = "ANTHROPIC"
        _reject(ProviderCredentialReferenceV1, **_reference_values(unexpected="reject"))

    @pytest.mark.parametrize("field", [
        "api_key", "secret", "secret_value", "raw_secret", "token_value",
        "bearer_token", "authorization_header", "password", "private_key", "client_secret",
    ])
    def test_reference_rejects_secret_bearing_aliases(self, field):
        _reject(ProviderCredentialReferenceV1, **_reference_values(**{field: SYNTHETIC_TEXT}))

    @pytest.mark.parametrize("field,value", [
        ("provider", "UNKNOWN"), ("credential_version", 0),
        ("source_kind", "ENVIRONMENT"), ("created_at", "2026-07-17T00:00:00"),
        ("valid_from", "2026-07-17T00:00:00"), ("valid_until", "2026-07-16T23:59:59Z"),
    ])
    def test_reference_rejects_invalid_metadata(self, field, value):
        _reject(ProviderCredentialReferenceV1, **_reference_values(**{field: value}))

    def test_validity_rotation_and_owner_metadata_bind_safe_identity(self):
        baseline = _reference()
        assert _reference(valid_until="2026-07-17T00:00:00Z").valid_until == "2026-07-17T00:00:00Z"
        assert _reference(valid_until="2026-07-18T00:00:01Z").identity != baseline.identity
        assert _reference(rotation_required=True).identity != baseline.identity
        assert _reference(owner_approval_reference="owner-approval-002").identity != baseline.identity
        _reject(ProviderCredentialReferenceV1, **_reference_values(valid_from="2026-07-18T00:00:00Z", valid_until="2026-07-17T00:00:00Z"))
        _reject(ProviderCredentialReferenceV1, **_reference_values(reference_identity="0" * 64))
        _reject(ProviderCredentialReferenceV1, **_reference_values(owner_approval_reference=""))


class TestEphemeralCredential:
    def test_ephemeral_material_is_provider_reference_version_bound_and_redacted(self):
        reference = _reference()
        value = _ephemeral(reference)
        assert value.provider == reference.provider
        assert value.credential_reference_identity == reference.identity
        assert value.credential_version == reference.credential_version
        assert value.material_for_adapter() == SYNTHETIC_BYTES
        for rendered in (repr(value), str(value), repr(reference), str(reference)):
            assert SYNTHETIC_BYTES.decode() not in rendered
            assert SYNTHETIC_TEXT not in rendered
        assert not hasattr(value, "to_mapping")
        assert not hasattr(value, "to_json")

    def test_bytes_and_text_material_are_supported_but_blank_or_wrong_material_fails(self):
        reference = _reference()
        assert _ephemeral(reference, SYNTHETIC_TEXT).material_for_adapter() == SYNTHETIC_TEXT
        for material in (b"", "", 7, object()):
            _reject(EphemeralProviderCredentialV1, **_ephemeral_values(reference, material))

    def test_ephemeral_rejects_provider_reference_version_and_unknown_field_mismatch(self):
        deepseek = _reference()
        anthropic = _reference("ANTHROPIC", credential_reference_id="credential-reference-002")
        _reject(EphemeralProviderCredentialV1, **_ephemeral_values(deepseek, provider="ANTHROPIC"))
        _reject(EphemeralProviderCredentialV1, **_ephemeral_values(deepseek, credential_reference=anthropic, credential_reference_identity=anthropic.identity))
        _reject(EphemeralProviderCredentialV1, **_ephemeral_values(deepseek, credential_version=2))
        _reject(EphemeralProviderCredentialV1, **_ephemeral_values(deepseek, unknown="reject"))


class TestResolutionEvidence:
    def test_successful_deepseek_and_anthropic_resolution_is_explicit_and_safe(self):
        for provider, reference_id in (("DEEPSEEK", "credential-reference-001"), ("ANTHROPIC", "credential-reference-002")):
            reference = _reference(provider, credential_reference_id=reference_id)
            credential = _ephemeral(reference)
            resolver = _FakeResolver(credential)
            result = resolve_provider_credential(reference=reference, resolver=resolver, resolved_at="2026-07-17T00:05:00Z")
            assert result.status == "RESOLVED" and result.failure_class == "NONE"
            assert result.ephemeral_credential is credential
            assert resolver.calls == [(reference, "2026-07-17T00:05:00Z")]
            assert SYNTHETIC_BYTES.decode() not in repr(result)
            assert SYNTHETIC_BYTES.decode() not in str(result)

    @pytest.mark.parametrize("failure", FAILURES[1:])
    def test_closed_failure_resolution_has_no_usable_credential(self, failure):
        reference = _reference()
        result = _resolution(
            reference, None, status="DENIED", failure_class=failure,
            reason_codes=(failure,), ephemeral_credential=None,
        )
        assert result.status == "DENIED"
        assert result.failure_class == failure
        assert result.ephemeral_credential is None
        assert SYNTHETIC_BYTES.decode() not in repr(result)
        _reject(ProviderCredentialResolutionV1, **_resolution_values(reference, None, status="DENIED", failure_class="UNKNOWN", reason_codes=("UNKNOWN",), ephemeral_credential=None))

    def test_resolution_rejects_success_failure_validity_and_child_binding_mismatch(self):
        reference = _reference()
        credential = _ephemeral(reference)
        _reject(ProviderCredentialResolutionV1, **_resolution_values(reference, credential, failure_class="EXPIRED"))
        _reject(ProviderCredentialResolutionV1, **_resolution_values(reference, None, status="DENIED", failure_class="EXPIRED", reason_codes=("EXPIRED",), ephemeral_credential=credential))
        _reject(ProviderCredentialResolutionV1, **_resolution_values(reference, credential, resolved_at="2026-07-18T00:00:01Z"))
        other = _reference("ANTHROPIC", credential_reference_id="credential-reference-002")
        _reject(ProviderCredentialResolutionV1, **_resolution_values(reference, _ephemeral(other)))
        _reject(ProviderCredentialResolutionV1, **_resolution_values(reference, credential, extra="reject"))

    def test_resolver_handles_missing_mismatch_validity_rotation_exception_and_malformed_values(self):
        reference = _reference()
        cases = [
            (_FakeResolver(None), "REFERENCE_NOT_FOUND"),
            (_FakeResolver(_ephemeral(_reference("ANTHROPIC", credential_reference_id="credential-reference-002"))), "PROVIDER_MISMATCH"),
            (_FakeResolver(_ephemeral(_reference(credential_version=2))), "VERSION_MISMATCH"),
            (_FakeResolver({"malformed": "value"}), "MALFORMED_RESOLUTION"),
            (_FakeResolver(error=RuntimeError(SYNTHETIC_TEXT)), "RESOLVER_FAILURE"),
        ]
        for resolver, failure in cases:
            result = resolve_provider_credential(reference=reference, resolver=resolver, resolved_at="2026-07-17T00:05:00Z")
            assert result.status == "DENIED" and result.failure_class == failure
            assert result.ephemeral_credential is None
            assert SYNTHETIC_TEXT not in repr(result)
        assert resolve_provider_credential(reference=_reference(valid_from="2026-07-17T01:00:00Z"), resolver=_FakeResolver(_ephemeral()), resolved_at="2026-07-17T00:05:00Z").failure_class == "NOT_YET_VALID"
        assert resolve_provider_credential(reference=_reference(valid_until="2026-07-17T00:04:59Z"), resolver=_FakeResolver(_ephemeral()), resolved_at="2026-07-17T00:05:00Z").failure_class == "EXPIRED"
        assert resolve_provider_credential(reference=_reference(rotation_required=True), resolver=_FakeResolver(_ephemeral()), resolved_at="2026-07-17T00:05:00Z").failure_class == "ROTATION_REQUIRED"
        with pytest.raises((TypeError, ValueError, ProviderCredentialValidationError)):
            resolve_provider_credential(reference=reference, resolver=_FakeResolver(_ephemeral(reference)))

    def test_resolution_identity_is_safe_and_binds_metadata_not_material(self):
        reference = _reference()
        first = _resolution(reference, _ephemeral(reference, SYNTHETIC_BYTES))
        second = _resolution(reference, _ephemeral(reference, SYNTHETIC_TEXT))
        assert first.identity == second.identity
        assert first.identity != _resolution(_reference(credential_version=2), _ephemeral(_reference(credential_version=2))).identity
        assert SYNTHETIC_BYTES.decode() not in first.identity
        assert SYNTHETIC_TEXT not in second.identity
        assert SYNTHETIC_BYTES.decode() not in canonical_json_bytes({"identity": first.identity}).decode()
        assert lowercase_sha256({"provider": "DEEPSEEK"}) == _sha({"provider": "DEEPSEEK"})
        with pytest.raises((AttributeError, TypeError)):
            first.status = "DENIED"


def test_protocol_is_explicit_and_generic_runtime_remains_credential_neutral():
    assert "resolver" not in inspect.signature(ShadowProviderRuntimeV1).parameters
    assert hasattr(ProviderCredentialResolverProtocol, "resolve")
    runtime_path = Path(__file__).parents[1] / "engine" / "phase_11_shadow_provider_runtime_v1.py"
    tree = ast.parse(runtime_path.read_text(encoding="utf-8"))
    forbidden = {"api_key", "credential", "raw_secret", "bearer_token", "authorization_header", "private_key", "password"}
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    for class_name in ("ShadowProviderInvocationV1", "ShadowProviderInvocationResultV1"):
        fields = {node.target.id for node in classes[class_name].body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}
        assert not fields & forbidden
    allowed = {node.arg for node in ast.walk(ast.parse("def fixture(disposition, input_tokens, output_tokens, token_limit): pass")) if isinstance(node, ast.arg)}
    assert not allowed & forbidden


def test_future_credential_module_static_boundary_is_semantic_and_side_effect_free():
    path = Path(__file__).parents[1] / "engine" / "phase_11_provider_credential_boundary_v1.py"
    if not path.exists():
        pytest.skip("RED suite: credential boundary implementation is intentionally absent")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_imports = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "keyring", "boto3", "google", "azure", "telegram", "ccxt"}
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not imports & forbidden_imports
    forbidden_names = {"environ", "getenv", "load_dotenv", "dotenv_values", "open", "mkdir", "makedirs", "requests", "httpx", "socket", "subprocess", "keyring", "boto3"}
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    identifiers |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not identifiers & forbidden_names
