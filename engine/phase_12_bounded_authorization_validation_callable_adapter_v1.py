from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.phase_12_bounded_authorization_validation_composition_v1 import (
    run_phase_12_bounded_authorization_validation_composition_v1,
)


__all__ = (
    "build_phase_12_bounded_authorization_validation_callable_adapter_v1",
)


class _Phase12AuthorizationRecordParserCallableV1(Protocol):
    def __call__(self, *, document: str) -> object: ...


class _Phase12SemanticAuthorizationVerifierCallableV1(Protocol):
    def __call__(
        self,
        *,
        configuration: object,
        activation_mode: object,
        owner_authorization_id: object,
        approval_checkpoint_id: object,
        approved_locked_commit: object,
        approved_at: object,
        expires_at: object,
        accepted_locked_commit: object,
        now_utc: object,
    ) -> object: ...


class _Phase12PublicKeyLoaderCallableV1(Protocol):
    def __call__(
        self,
        *,
        path: str,
        expected_public_key_fingerprint: str,
        expected_signing_key_identifier: str,
    ) -> object: ...


class _Phase12RevocationStateSourceCallableV1(Protocol):
    def __call__(
        self,
        *,
        path: str,
        expected_artifact_fingerprint: str,
        expected_schema_identifier: str,
        expected_checkpoint_identifier: str,
        active_signing_key_identifier: str,
    ) -> object: ...


class _Phase12OwnerApprovalSignatureVerifierCallableV1(Protocol):
    def __call__(
        self,
        *,
        canonical_payload_bytes: bytes,
        signature_bytes: bytes,
        public_key_bytes: bytes | None,
        expected_signing_key_identifier: str,
        revocation_state_available: bool,
        active_signing_key_identifier: str | None,
        revoked_signing_key_identifiers: tuple[str, ...] | None,
        revocation_state_checkpoint_identifier: str | None,
        expected_environment_identifier: str,
        expected_deployment_identifier: str,
        expected_checkpoint_identifier: str,
        now_utc: object,
    ) -> object: ...


class _Phase12CanonicalReplayIdentityDerivationCallableV1(Protocol):
    def __call__(
        self,
        *,
        replay_control_value: str,
        deployment_identifier: str,
        owner_authorization_id: str,
        checkpoint_id: str,
        approved_locked_commit: str,
        environment_identifier: str,
    ) -> str: ...


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12BoundedAuthorizationValidationCallableAdapterV1:
    authorization_record_parser: _Phase12AuthorizationRecordParserCallableV1
    semantic_authorization_verifier: _Phase12SemanticAuthorizationVerifierCallableV1
    public_key_loader: _Phase12PublicKeyLoaderCallableV1
    revocation_state_source: _Phase12RevocationStateSourceCallableV1
    owner_approval_signature_verifier: _Phase12OwnerApprovalSignatureVerifierCallableV1
    canonical_replay_identity_derivation: _Phase12CanonicalReplayIdentityDerivationCallableV1

    def __call__(
        self,
        *,
        authorization_request: object,
        trust_expectations: object,
        validation_context: object,
    ) -> object:
        return run_phase_12_bounded_authorization_validation_composition_v1(
            authorization_request=authorization_request,
            trust_expectations=trust_expectations,
            validation_context=validation_context,
            authorization_record_parser=self.authorization_record_parser,
            semantic_authorization_verifier=self.semantic_authorization_verifier,
            public_key_loader=self.public_key_loader,
            revocation_state_source=self.revocation_state_source,
            owner_approval_signature_verifier=self.owner_approval_signature_verifier,
            canonical_replay_identity_derivation=self.canonical_replay_identity_derivation,
        )


def build_phase_12_bounded_authorization_validation_callable_adapter_v1(
    *,
    authorization_record_parser: _Phase12AuthorizationRecordParserCallableV1,
    semantic_authorization_verifier: _Phase12SemanticAuthorizationVerifierCallableV1,
    public_key_loader: _Phase12PublicKeyLoaderCallableV1,
    revocation_state_source: _Phase12RevocationStateSourceCallableV1,
    owner_approval_signature_verifier: _Phase12OwnerApprovalSignatureVerifierCallableV1,
    canonical_replay_identity_derivation: _Phase12CanonicalReplayIdentityDerivationCallableV1,
) -> _Phase12BoundedAuthorizationValidationCallableAdapterV1:
    if not callable(authorization_record_parser):
        raise TypeError()
    if not callable(semantic_authorization_verifier):
        raise TypeError()
    if not callable(public_key_loader):
        raise TypeError()
    if not callable(revocation_state_source):
        raise TypeError()
    if not callable(owner_approval_signature_verifier):
        raise TypeError()
    if not callable(canonical_replay_identity_derivation):
        raise TypeError()
    return _Phase12BoundedAuthorizationValidationCallableAdapterV1(
        authorization_record_parser=authorization_record_parser,
        semantic_authorization_verifier=semantic_authorization_verifier,
        public_key_loader=public_key_loader,
        revocation_state_source=revocation_state_source,
        owner_approval_signature_verifier=owner_approval_signature_verifier,
        canonical_replay_identity_derivation=canonical_replay_identity_derivation,
    )
