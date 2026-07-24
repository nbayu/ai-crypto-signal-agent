from __future__ import annotations
from dataclasses import dataclass
from inspect import getattr_static
from typing import Protocol

from engine.phase_12_activation_mode_authorization_record_parser_v1 import (
    Phase12ActivationAuthorizationRecordDocumentErrorV1,
)


__all__ = (
    "run_phase_12_bounded_authorization_validation_composition_v1",
)


_AUTHORIZATION_RECORD_PARSE_FAILED = "AUTHORIZATION_RECORD_PARSE_FAILED"
_AUTHORIZATION_RECORD_PARSE_RESULT_INVALID = "AUTHORIZATION_RECORD_PARSE_RESULT_INVALID"
_SEMANTIC_AUTHORIZATION_FAILED = "SEMANTIC_AUTHORIZATION_FAILED"
_SEMANTIC_AUTHORIZATION_RESULT_INVALID = "SEMANTIC_AUTHORIZATION_RESULT_INVALID"
_PUBLIC_KEY_LOADING_FAILED = "PUBLIC_KEY_LOADING_FAILED"
_PUBLIC_KEY_LOADING_RESULT_INVALID = "PUBLIC_KEY_LOADING_RESULT_INVALID"
_REVOCATION_STATE_LOADING_FAILED = "REVOCATION_STATE_LOADING_FAILED"
_REVOCATION_STATE_LOADING_RESULT_INVALID = "REVOCATION_STATE_LOADING_RESULT_INVALID"
_OWNER_APPROVAL_SIGNATURE_VERIFICATION_FAILED = "OWNER_APPROVAL_SIGNATURE_VERIFICATION_FAILED"
_OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID = "OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID"
_AUTHORIZATION_FACT_MISMATCH = "AUTHORIZATION_FACT_MISMATCH"
_DEPLOYMENT_CONSISTENCY_MISMATCH = "DEPLOYMENT_CONSISTENCY_MISMATCH"
_REPLAY_IDENTITY_RESULT_INVALID = "REPLAY_IDENTITY_RESULT_INVALID"
_FAILURE_CODES = (
    _AUTHORIZATION_RECORD_PARSE_FAILED,
    _AUTHORIZATION_RECORD_PARSE_RESULT_INVALID,
    _SEMANTIC_AUTHORIZATION_FAILED,
    _SEMANTIC_AUTHORIZATION_RESULT_INVALID,
    _PUBLIC_KEY_LOADING_FAILED,
    _PUBLIC_KEY_LOADING_RESULT_INVALID,
    _REVOCATION_STATE_LOADING_FAILED,
    _REVOCATION_STATE_LOADING_RESULT_INVALID,
    _OWNER_APPROVAL_SIGNATURE_VERIFICATION_FAILED,
    _OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID,
    _AUTHORIZATION_FACT_MISMATCH,
    _DEPLOYMENT_CONSISTENCY_MISMATCH,
    _REPLAY_IDENTITY_RESULT_INVALID,
)


class _Phase12AuthorizationRecordParserCallableV1(Protocol):
    def __call__(self, *, document: str) -> object: ...


class _Phase12SemanticAuthorizationVerifierCallableV1(Protocol):
    def __call__(self, *, configuration: object, activation_mode: object,
                 owner_authorization_id: object, approval_checkpoint_id: object,
                 approved_locked_commit: object, approved_at: object,
                 expires_at: object, accepted_locked_commit: object,
                 now_utc: object) -> object: ...


class _Phase12PublicKeyLoaderCallableV1(Protocol):
    def __call__(self, *, path: str, expected_public_key_fingerprint: str,
                 expected_signing_key_identifier: str) -> object: ...


class _Phase12RevocationStateSourceCallableV1(Protocol):
    def __call__(self, *, path: str, expected_artifact_fingerprint: str,
                 expected_schema_identifier: str, expected_checkpoint_identifier: str,
                 active_signing_key_identifier: str) -> object: ...


class _Phase12OwnerApprovalSignatureVerifierCallableV1(Protocol):
    def __call__(self, *, canonical_payload_bytes: bytes, signature_bytes: bytes,
                 public_key_bytes: bytes | None, expected_signing_key_identifier: str,
                 revocation_state_available: bool, active_signing_key_identifier: str | None,
                 revoked_signing_key_identifiers: tuple[str, ...] | None,
                 revocation_state_checkpoint_identifier: str | None,
                 expected_environment_identifier: str,
                 expected_deployment_identifier: str,
                 expected_checkpoint_identifier: str, now_utc: object) -> object: ...


class _Phase12CanonicalReplayIdentityDerivationCallableV1(Protocol):
    def __call__(self, *, replay_control_value: str, deployment_identifier: str,
                 owner_authorization_id: str, checkpoint_id: str,
                 approved_locked_commit: str, environment_identifier: str) -> str: ...


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12BoundedAuthorizationValidationCompositionResultV1:
    is_validated: bool
    failure_codes: tuple[str, ...]
    repository_identity: str | None
    deployment_identifier: str | None
    replay_identity: str | None


def _failure(code: str) -> _Phase12BoundedAuthorizationValidationCompositionResultV1:
    return _Phase12BoundedAuthorizationValidationCompositionResultV1(
        is_validated=False, failure_codes=(code,), repository_identity=None,
        deployment_identifier=None, replay_identity=None,
    )


def _has(value: object, names: tuple[str, ...]) -> bool:
    for name in names:
        try:
            getattr_static(value, name)
        except AttributeError:
            return False
    return True


def _text(value: object) -> bool:
    return type(value) is str and value != ""


def _utc_datetime(value: object) -> bool:
    return (
        type(value).__name__ == "datetime"
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def _nonempty_codes(value: object) -> bool:
    return type(value) is tuple and len(value) >= 1 and all(type(x) is str for x in value)


def run_phase_12_bounded_authorization_validation_composition_v1(
    *,
    authorization_request: object,
    trust_expectations: object,
    validation_context: object,
    authorization_record_parser: _Phase12AuthorizationRecordParserCallableV1,
    semantic_authorization_verifier: _Phase12SemanticAuthorizationVerifierCallableV1,
    public_key_loader: _Phase12PublicKeyLoaderCallableV1,
    revocation_state_source: _Phase12RevocationStateSourceCallableV1,
    owner_approval_signature_verifier: _Phase12OwnerApprovalSignatureVerifierCallableV1,
    canonical_replay_identity_derivation: _Phase12CanonicalReplayIdentityDerivationCallableV1,
) -> _Phase12BoundedAuthorizationValidationCompositionResultV1:
    request_names = ("document", "canonical_payload_bytes", "signature_bytes", "activation_mode", "owner_authorization_id", "approval_checkpoint_id", "approved_locked_commit", "approved_at", "expires_at", "accepted_locked_commit_expectation")
    trust_names = ("public_key_path", "expected_public_key_fingerprint", "expected_signing_key_identifier", "revocation_state_path", "expected_revocation_artifact_fingerprint", "expected_revocation_schema_identifier", "expected_revocation_checkpoint_identifier", "expected_environment_identifier", "expected_deployment_identifier")
    if not _has(authorization_request, request_names): raise TypeError()
    if not _has(trust_expectations, trust_names): raise TypeError()
    if not _has(validation_context, ("configuration", "now_utc")): raise TypeError()
    request = tuple(getattr(authorization_request, name) for name in request_names)
    trust = tuple(getattr(trust_expectations, name) for name in trust_names)
    if not _text(request[0]) or type(request[1]) is not bytes or type(request[2]) is not bytes or any(not _text(value) for value in request[3:]): raise TypeError()
    if any(not _text(value) for value in trust): raise TypeError()
    if validation_context.configuration is None: raise TypeError()
    for dependency in (authorization_record_parser, semantic_authorization_verifier, public_key_loader, revocation_state_source, owner_approval_signature_verifier, canonical_replay_identity_derivation):
        if not callable(dependency): raise TypeError()
    try:
        parser_result = authorization_record_parser(document=request[0])
    except Phase12ActivationAuthorizationRecordDocumentErrorV1:
        return _failure(_AUTHORIZATION_RECORD_PARSE_FAILED)
    parser_names = ("mode", "owner_authorization_id", "checkpoint_id", "approved_locked_commit", "accepted_locked_commit", "approval_timestamp_utc", "expires_at_utc")
    if not _has(parser_result, parser_names): return _failure(_AUTHORIZATION_RECORD_PARSE_RESULT_INVALID)
    parsed = tuple(getattr(parser_result, name) for name in parser_names)
    if any(not _text(value) for value in parsed[:5]) or not _utc_datetime(parsed[5]) or not _utc_datetime(parsed[6]): return _failure(_AUTHORIZATION_RECORD_PARSE_RESULT_INVALID)
    approved_at = parsed[5].strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_at = parsed[6].strftime("%Y-%m-%dT%H:%M:%SZ")
    semantic = semantic_authorization_verifier(configuration=validation_context.configuration, activation_mode=parsed[0], owner_authorization_id=parsed[1], approval_checkpoint_id=parsed[2], approved_locked_commit=parsed[3], approved_at=approved_at, expires_at=expires_at, accepted_locked_commit=request[9], now_utc=validation_context.now_utc)
    if type(semantic) is not bool: return _failure(_SEMANTIC_AUTHORIZATION_RESULT_INVALID)
    if semantic is False: return _failure(_SEMANTIC_AUTHORIZATION_FAILED)
    key_result = public_key_loader(path=trust[0], expected_public_key_fingerprint=trust[1], expected_signing_key_identifier=trust[2])
    key_names = ("is_loaded", "failure_codes", "raw_public_key_bytes", "derived_signing_key_identifier")
    if not _has(key_result, key_names): return _failure(_PUBLIC_KEY_LOADING_RESULT_INVALID)
    key = tuple(getattr(key_result, name) for name in key_names)
    if type(key[0]) is not bool or type(key[1]) is not tuple: return _failure(_PUBLIC_KEY_LOADING_RESULT_INVALID)
    if key[0] is False:
        return _failure(_PUBLIC_KEY_LOADING_FAILED) if _nonempty_codes(key[1]) and key[2] is None and key[3] is None else _failure(_PUBLIC_KEY_LOADING_RESULT_INVALID)
    if key[1] != () or type(key[2]) is not bytes or not _text(key[3]): return _failure(_PUBLIC_KEY_LOADING_RESULT_INVALID)
    revocation_result = revocation_state_source(path=trust[3], expected_artifact_fingerprint=trust[4], expected_schema_identifier=trust[5], expected_checkpoint_identifier=trust[6], active_signing_key_identifier=key[3])
    revocation_names = ("is_loaded", "failure_codes", "schema_identifier", "checkpoint_identifier", "revoked_signing_key_identifiers", "artifact_fingerprint")
    if not _has(revocation_result, revocation_names): return _failure(_REVOCATION_STATE_LOADING_RESULT_INVALID)
    revocation = tuple(getattr(revocation_result, name) for name in revocation_names)
    if type(revocation[0]) is not bool or type(revocation[1]) is not tuple: return _failure(_REVOCATION_STATE_LOADING_RESULT_INVALID)
    if revocation[0] is False:
        return _failure(_REVOCATION_STATE_LOADING_FAILED) if _nonempty_codes(revocation[1]) else _failure(_REVOCATION_STATE_LOADING_RESULT_INVALID)
    if revocation[1] != () or not _text(revocation[2]) or not _text(revocation[3]) or type(revocation[4]) is not tuple or not _text(revocation[5]): return _failure(_REVOCATION_STATE_LOADING_RESULT_INVALID)
    signature_result = owner_approval_signature_verifier(canonical_payload_bytes=request[1], signature_bytes=request[2], public_key_bytes=key[2], expected_signing_key_identifier=trust[2], revocation_state_available=True, active_signing_key_identifier=key[3], revoked_signing_key_identifiers=revocation[4], revocation_state_checkpoint_identifier=revocation[3], expected_environment_identifier=trust[7], expected_deployment_identifier=trust[8], expected_checkpoint_identifier=request[5], now_utc=validation_context.now_utc)
    if not _has(signature_result, ("is_valid", "failure_codes", "verified_approval")): return _failure(_OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID)
    if type(signature_result.is_valid) is not bool or type(signature_result.failure_codes) is not tuple: return _failure(_OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID)
    if signature_result.is_valid is False:
        return _failure(_OWNER_APPROVAL_SIGNATURE_VERIFICATION_FAILED) if _nonempty_codes(signature_result.failure_codes) and signature_result.verified_approval is None else _failure(_OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID)
    approval = signature_result.verified_approval
    approval_names = ("repository_identity", "deployment_identifier", "replay_control_value", "owner_authorization_id", "checkpoint_id", "approved_locked_commit", "accepted_locked_commit", "approval_timestamp_utc", "expiry_utc", "activation_mode", "environment_identifier", "signing_key_identifier")
    if signature_result.failure_codes != () or not _has(approval, approval_names): return _failure(_OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID)
    facts = tuple(getattr(approval, name) for name in approval_names)
    if any(not _text(value) for value in facts[:7]) or not _utc_datetime(facts[7]) or not _utc_datetime(facts[8]) or any(not _text(value) for value in facts[9:]): return _failure(_OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID)
    comparisons = ((request[3], parsed[0]), (request[4], parsed[1]), (request[5], parsed[2]), (request[6], parsed[3]), (request[7], approved_at), (request[8], expires_at), (request[9], parsed[4]), (parsed[0], facts[9]), (parsed[1], facts[3]), (parsed[2], facts[4]), (parsed[3], facts[5]), (parsed[4], facts[6]), (parsed[5], facts[7]), (parsed[6], facts[8]), (key[3], facts[11]), (trust[7], facts[10]))
    if any(left != right for left, right in comparisons): return _failure(_AUTHORIZATION_FACT_MISMATCH)
    if trust[8] != facts[1]: return _failure(_DEPLOYMENT_CONSISTENCY_MISMATCH)
    replay_identity = canonical_replay_identity_derivation(replay_control_value=facts[2], deployment_identifier=facts[1], owner_authorization_id=facts[3], checkpoint_id=facts[4], approved_locked_commit=facts[5], environment_identifier=facts[10])
    if type(replay_identity) is not str or len(replay_identity) != 64 or any(character not in "0123456789abcdef" for character in replay_identity): return _failure(_REPLAY_IDENTITY_RESULT_INVALID)
    return _Phase12BoundedAuthorizationValidationCompositionResultV1(is_validated=True, failure_codes=(), repository_identity=facts[0], deployment_identifier=facts[1], replay_identity=replay_identity)
