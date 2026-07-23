"""RED contract for the unwired Phase 12 owner approval signature verifier."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import hashlib
import inspect

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

import engine.phase_12_activation_owner_approval_signature_verifier_v1 as verifier_module


_SCHEMA = "phase12-owner-approval-signature-v1"
_ALGORITHM = "PHASE12-ED25519-SHA512-RAW-V1"
_ENVIRONMENT = "ai-crypto-signal-agent-production-v1"
_NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)
_FIELDS = (
    "payload_schema_version", "signature_algorithm_identifier", "signing_key_identifier",
    "activation_mode", "owner_authorization_id", "checkpoint_id",
    "approved_locked_commit", "accepted_locked_commit", "approval_timestamp", "expiry",
    "environment_identifier", "deployment_identifier", "replay_control_value",
    "repository_identity", "repository_commit", "approval_scope",
)


def _payload(values: dict[str, str]) -> bytes:
    return "".join(f"{name}={values[name]}\n" for name in _FIELDS).encode("ascii")


def _vector(**changes: str):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    key_id = "ed25519-sha256:" + hashlib.sha256(public).hexdigest()
    values = {
        "payload_schema_version": _SCHEMA,
        "signature_algorithm_identifier": _ALGORITHM,
        "signing_key_identifier": key_id,
        "activation_mode": "CREDENTIAL_VALIDATION",
        "owner_authorization_id": "owner-approval-v1",
        "checkpoint_id": "checkpoint-v1",
        "approved_locked_commit": "a" * 40,
        "accepted_locked_commit": "a" * 40,
        "approval_timestamp": "2026-07-23T12:00:00Z",
        "expiry": "2026-07-23T12:15:00Z",
        "environment_identifier": _ENVIRONMENT,
        "deployment_identifier": "deployment-v1",
        "replay_control_value": "replay-v1",
        "repository_identity": "ai-crypto-signal-agent",
        "repository_commit": "a" * 40,
        "approval_scope": "EXACT_ACTIVATION_ATTEMPT",
    }
    values.update(changes)
    payload = _payload(values)
    return payload, private.sign(payload), public, key_id, values


def _verify(payload: bytes, signature: bytes, public: bytes | None, key_id: str, **changes):
    values = {
        "canonical_payload_bytes": payload,
        "signature_bytes": signature,
        "public_key_bytes": public,
        "expected_signing_key_identifier": key_id,
        "revocation_state_available": True,
        "active_signing_key_identifier": key_id,
        "revoked_signing_key_identifiers": (),
        "revocation_state_checkpoint_identifier": "trust-checkpoint-v1",
        "expected_environment_identifier": _ENVIRONMENT,
        "expected_deployment_identifier": "deployment-v1",
        "expected_checkpoint_identifier": "checkpoint-v1",
        "now_utc": _NOW,
    }
    values.update(changes)
    return verifier_module.verify_phase_12_activation_owner_approval_signature_v1(**values)


def _failure(result, code: str) -> None:
    assert result.is_valid is False
    assert result.failure_codes == (code,)
    assert result.verified_approval is None


# 4 public-surface/signature tests.
def test_public_all_is_exact():
    assert verifier_module.__all__ == ("verify_phase_12_activation_owner_approval_signature_v1",)


def test_public_function_name_is_exact():
    assert verifier_module.verify_phase_12_activation_owner_approval_signature_v1.__name__ == "verify_phase_12_activation_owner_approval_signature_v1"


def test_public_function_signature_is_exact_and_keyword_only():
    signature = inspect.signature(verifier_module.verify_phase_12_activation_owner_approval_signature_v1)
    assert tuple(signature.parameters) == ("canonical_payload_bytes", "signature_bytes", "public_key_bytes", "expected_signing_key_identifier", "revocation_state_available", "active_signing_key_identifier", "revoked_signing_key_identifiers", "revocation_state_checkpoint_identifier", "expected_environment_identifier", "expected_deployment_identifier", "expected_checkpoint_identifier", "now_utc")
    assert all(item.kind is inspect.Parameter.KEYWORD_ONLY for item in signature.parameters.values())


def test_no_result_facts_or_failure_type_is_exported():
    assert not {name for name in verifier_module.__all__ if "Result" in name or "Facts" in name or "Failure" in name}


# 4 immutability/result-shape tests.
def test_valid_result_has_exact_field_shape():
    payload, signature, public, key_id, _ = _vector()
    result = _verify(payload, signature, public, key_id)
    assert tuple(type(result).__dataclass_fields__) == ("is_valid", "failure_codes", "verified_approval")


def test_result_is_immutable_and_slotted():
    payload, signature, public, key_id, _ = _vector()
    result = _verify(payload, signature, public, key_id)
    assert not hasattr(result, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        result.is_valid = False


def test_success_facts_are_immutable_and_slotted():
    payload, signature, public, key_id, _ = _vector()
    facts = _verify(payload, signature, public, key_id).verified_approval
    assert facts is not None and not hasattr(facts, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        facts.checkpoint_id = "changed"


def test_failure_codes_are_tuple():
    payload, signature, public, key_id, _ = _vector()
    assert isinstance(_verify(payload, signature[:-1], public, key_id).failure_codes, tuple)


# 12 canonical-framing tests.
def test_valid_canonical_payload_verifies():
    payload, signature, public, key_id, _ = _vector(); assert _verify(payload, signature, public, key_id).is_valid is True


def test_canonical_rejects_bom():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(b"\xef\xbb\xbf" + payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_crlf():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload.replace(b"\n", b"\r\n"), signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_missing_terminal_lf():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload[:-1], signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_blank_line():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload + b"\n", signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_comment():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload + b"comment=x\n", signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_duplicate_field():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload + b"checkpoint_id=checkpoint-v1\n", signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_extra_field():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload.replace(b"approval_scope=", b"extra="), signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_missing_field():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload.replace(b"approval_scope=EXACT_ACTIVATION_ATTEMPT\n", b""), signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_multiple_equals():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload.replace(b"owner-approval-v1", b"owner=approval"), signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_whitespace():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload.replace(b"checkpoint-v1", b" checkpoint-v1"), signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_canonical_rejects_over_limit_bytes():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload + b"x" * 2049, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


# 16 field-grammar tests.
def test_schema_literal_is_known():
    payload, signature, public, key_id, _ = _vector(payload_schema_version="unknown-v1"); _failure(_verify(payload, signature, public, key_id), "UNKNOWN_PAYLOAD_SCHEMA")


def test_algorithm_literal_is_known():
    payload, signature, public, key_id, _ = _vector(signature_algorithm_identifier="UNKNOWN-V1"); _failure(_verify(payload, signature, public, key_id), "UNKNOWN_SIGNATURE_ALGORITHM")


def test_key_id_grammar_is_exact():
    payload, signature, public, key_id, _ = _vector(signing_key_identifier="ed25519-sha256:ABC"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_activation_mode_is_bounded():
    payload, signature, public, key_id, _ = _vector(activation_mode="PRODUCTION"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_owner_authorization_id_grammar_is_exact():
    payload, signature, public, key_id, _ = _vector(owner_authorization_id="owner/a"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_checkpoint_id_grammar_is_exact():
    payload, signature, public, key_id, _ = _vector(checkpoint_id="checkpoint/a"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_approved_commit_is_lowercase_sha1():
    payload, signature, public, key_id, _ = _vector(approved_locked_commit="A" * 40); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_accepted_commit_is_lowercase_sha1():
    payload, signature, public, key_id, _ = _vector(accepted_locked_commit="b" * 39); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_approval_timestamp_has_canonical_spelling():
    payload, signature, public, key_id, _ = _vector(approval_timestamp="2026-07-23T12:00:00+00:00"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_expiry_has_canonical_spelling():
    payload, signature, public, key_id, _ = _vector(expiry="2026-07-23T12:15:00.0Z"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_environment_literal_is_exact():
    payload, signature, public, key_id, _ = _vector(environment_identifier="staging"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_deployment_id_grammar_is_exact():
    payload, signature, public, key_id, _ = _vector(deployment_identifier="deployment/v1"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_replay_control_grammar_is_exact():
    payload, signature, public, key_id, _ = _vector(replay_control_value="replay value"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_repository_identity_grammar_is_exact():
    payload, signature, public, key_id, _ = _vector(repository_identity="repo/id"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_repository_commit_is_lowercase_sha1():
    payload, signature, public, key_id, _ = _vector(repository_commit="g" * 40); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


def test_approval_scope_literal_is_exact():
    payload, signature, public, key_id, _ = _vector(approval_scope="ONE_DEPLOYMENT"); _failure(_verify(payload, signature, public, key_id), "MALFORMED_CANONICAL_PAYLOAD")


# 8 exact-type/API-shape tests.
def test_payload_requires_exact_bytes():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(bytearray(payload), signature, public, key_id)


def test_signature_requires_exact_bytes():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(payload, bytearray(signature), public, key_id)


def test_public_key_requires_exact_bytes_or_none():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(payload, signature, bytearray(public), key_id)


def test_expected_key_id_requires_exact_string():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(payload, signature, public, 1)


def test_revocation_availability_requires_exact_bool():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(payload, signature, public, key_id, revocation_state_available=1)


def test_revoked_ids_require_exact_tuple():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(payload, signature, public, key_id, revoked_signing_key_identifiers=[])


def test_expected_context_requires_exact_strings():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(payload, signature, public, key_id, expected_checkpoint_identifier=1)


def test_now_requires_exact_utc_datetime_or_none():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(payload, signature, public, key_id, now_utc=datetime(2026, 7, 23, 12, 0, 0))


# 8 key/fingerprint/revocation tests.
def test_missing_public_key_is_unavailable():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, None, key_id), "TRUST_MATERIAL_UNAVAILABLE")


def test_public_key_is_32_bytes():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, public[:-1], key_id), "MALFORMED_PUBLIC_KEY")


def test_fingerprint_must_match_expected_key_id():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, public, "ed25519-sha256:" + "0" * 64), "PUBLIC_KEY_FINGERPRINT_MISMATCH")


def test_signed_key_id_must_match_expected_key_id():
    payload, signature, public, key_id, _ = _vector(signing_key_identifier="ed25519-sha256:" + "1" * 64); _failure(_verify(payload, signature, public, key_id), "UNKNOWN_SIGNING_KEY_ID")


def test_active_key_id_must_match_expected_key_id():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, public, key_id, active_signing_key_identifier="ed25519-sha256:" + "2" * 64), "UNKNOWN_SIGNING_KEY_ID")


def test_unavailable_revocation_state_fails_closed():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, public, key_id, revocation_state_available=False, active_signing_key_identifier=None, revoked_signing_key_identifiers=None, revocation_state_checkpoint_identifier=None), "REVOCATION_STATE_UNAVAILABLE")


def test_active_key_in_revoked_ids_is_type_error():
    payload, signature, public, key_id, _ = _vector()
    with pytest.raises(TypeError) as caught:
        _verify(payload, signature, public, key_id, revoked_signing_key_identifiers=(key_id,))
    assert caught.value.args == ()


def test_duplicate_revoked_ids_are_type_error():
    payload, signature, public, key_id, _ = _vector();
    with pytest.raises(TypeError): _verify(payload, signature, public, key_id, revoked_signing_key_identifiers=("ed25519-sha256:" + "3" * 64,) * 2)


# 5 signature/cryptography tests.
def test_signature_is_64_bytes():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature[:-1], public, key_id), "MALFORMED_SIGNATURE")


def test_invalid_signature_maps_exactly():
    payload, signature, public, key_id, _ = _vector()
    nonmatching_signature = b"\x00" * 64
    assert len(nonmatching_signature) == 64
    _failure(_verify(payload, nonmatching_signature, public, key_id), "SIGNATURE_MISMATCH")


def test_signature_covers_exact_bytes_only():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload.replace(b"checkpoint-v1", b"checkpoint-v2"), signature, public, key_id), "SIGNATURE_MISMATCH")


def test_malformed_key_precedes_signature_failure():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature[:-1], public[:-1], key_id), "MALFORMED_PUBLIC_KEY")


def test_signature_has_no_envelope_metadata():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, b"v1:" + signature, public, key_id), "MALFORMED_SIGNATURE")


# 8 context/time/commit tests.
def test_wrong_environment_fails_closed():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, public, key_id, expected_environment_identifier="other-environment"), "WRONG_ENVIRONMENT")


def test_wrong_deployment_fails_closed():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, public, key_id, expected_deployment_identifier="deployment-v2"), "WRONG_DEPLOYMENT")


def test_wrong_checkpoint_fails_closed():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, public, key_id, expected_checkpoint_identifier="checkpoint-v2"), "WRONG_CHECKPOINT")


def test_clock_unavailable_fails_closed():
    payload, signature, public, key_id, _ = _vector(); _failure(_verify(payload, signature, public, key_id, now_utc=None), "CLOCK_EVIDENCE_UNAVAILABLE")


def test_future_skew_boundary_is_60_seconds():
    payload, signature, public, key_id, _ = _vector(approval_timestamp="2026-07-23T12:01:01Z", expiry="2026-07-23T12:15:00Z"); _failure(_verify(payload, signature, public, key_id), "APPROVAL_TIMESTAMP_IN_FUTURE")


def test_expiry_equality_is_expired():
    payload, signature, public, key_id, _ = _vector(expiry="2026-07-23T12:00:00Z"); _failure(_verify(payload, signature, public, key_id), "APPROVAL_EXPIRED")


def test_lifetime_cannot_exceed_15_minutes():
    payload, signature, public, key_id, _ = _vector(expiry="2026-07-23T12:15:01Z"); _failure(_verify(payload, signature, public, key_id), "EXCESSIVE_APPROVAL_LIFETIME")


def test_signed_commits_must_agree_without_git_access():
    payload, signature, public, key_id, _ = _vector(accepted_locked_commit="b" * 40); _failure(_verify(payload, signature, public, key_id), "APPROVED_ACCEPTED_COMMIT_MISMATCH")


# 2 authenticated-fact tests.
def test_success_returns_authenticated_repository_and_replay_facts():
    payload, signature, public, key_id, values = _vector(); facts = _verify(payload, signature, public, key_id).verified_approval
    assert facts is not None and facts.repository_identity == values["repository_identity"] and facts.replay_control_value == values["replay_control_value"]


def test_failure_returns_no_authenticated_facts():
    payload, signature, public, key_id, _ = _vector(); assert _verify(payload, signature[:-1], public, key_id).verified_approval is None


# 2 source-guard and non-overclaim tests.
def test_module_source_has_no_effectful_import_surface():
    source = inspect.getsource(verifier_module); assert not any(name in source for name in ("pathlib", "subprocess", "socket", "logging", "requests", "uuid"))


def test_success_does_not_claim_authorization_or_replay_prevention():
    payload, signature, public, key_id, _ = _vector(); result = _verify(payload, signature, public, key_id)
    assert not hasattr(result, "authorized") and not hasattr(result, "replay_prevented")
