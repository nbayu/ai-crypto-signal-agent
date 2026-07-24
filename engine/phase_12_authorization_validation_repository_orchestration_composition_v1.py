from __future__ import annotations

from typing import Protocol

from engine.phase_12_bounded_authorization_validation_callable_adapter_v1 import (
    build_phase_12_bounded_authorization_validation_callable_adapter_v1,
)
from engine.phase_12_authorization_repository_validation_composition_v1 import (
    run_phase_12_authorization_repository_validation_composition_v1,
)


__all__ = (
    "run_phase_12_authorization_validation_repository_orchestration_composition_v1",
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


class _Phase12AcceptedMarkerCompositionCallableV1(Protocol):
    def __call__(self, *, accepted_marker_request: object) -> object: ...


class _Phase12RepositoryVerificationCompositionCallableV1(Protocol):
    def __call__(
        self,
        *,
        source_path: str,
        repository_path: str,
        repository_identity: str,
        accepted_locked_commit: str,
        remote_expectation_source: _Phase12RemoteExpectationSourceCallableV1,
        repository_comparator: _Phase12RepositoryComparatorCallableV1,
    ) -> object: ...


class _Phase12RemoteExpectationSourceCallableV1(Protocol):
    def __call__(self, *, source_path: str) -> object: ...


class _Phase12RepositoryComparatorCallableV1(Protocol):
    def __call__(
        self,
        *,
        repository_path: str,
        repository_identity: str,
        accepted_locked_commit: str,
        expected_origin_fetch_url: str,
        expected_origin_push_url: str,
    ) -> object: ...


class _Phase12ReplayGuardCallableV1(Protocol):
    def __call__(
        self,
        *,
        path: str,
        replay_identity: str,
        expected_schema_identifier: str,
        expected_deployment_identifier: str,
    ) -> object: ...


def run_phase_12_authorization_validation_repository_orchestration_composition_v1(
    *,
    authorization_request: object,
    trust_expectations: object,
    validation_context: object,
    accepted_marker_request: object,
    repository_verification_request: object,
    replay_request: object,
    authorization_record_parser: _Phase12AuthorizationRecordParserCallableV1,
    semantic_authorization_verifier: _Phase12SemanticAuthorizationVerifierCallableV1,
    public_key_loader: _Phase12PublicKeyLoaderCallableV1,
    revocation_state_source: _Phase12RevocationStateSourceCallableV1,
    owner_approval_signature_verifier: _Phase12OwnerApprovalSignatureVerifierCallableV1,
    canonical_replay_identity_derivation: _Phase12CanonicalReplayIdentityDerivationCallableV1,
    accepted_marker_composition: _Phase12AcceptedMarkerCompositionCallableV1,
    repository_verification_composition: _Phase12RepositoryVerificationCompositionCallableV1,
    remote_expectation_source: _Phase12RemoteExpectationSourceCallableV1,
    repository_comparator: _Phase12RepositoryComparatorCallableV1,
    replay_guard: _Phase12ReplayGuardCallableV1,
) -> object:
    if not callable(accepted_marker_composition):
        raise TypeError()
    if not callable(repository_verification_composition):
        raise TypeError()
    if not callable(remote_expectation_source):
        raise TypeError()
    if not callable(repository_comparator):
        raise TypeError()
    if not callable(replay_guard):
        raise TypeError()

    authorization_validation_callable = (
        build_phase_12_bounded_authorization_validation_callable_adapter_v1(
            authorization_record_parser=authorization_record_parser,
            semantic_authorization_verifier=semantic_authorization_verifier,
            public_key_loader=public_key_loader,
            revocation_state_source=revocation_state_source,
            owner_approval_signature_verifier=owner_approval_signature_verifier,
            canonical_replay_identity_derivation=canonical_replay_identity_derivation,
        )
    )

    return run_phase_12_authorization_repository_validation_composition_v1(
        authorization_request=authorization_request,
        trust_expectations=trust_expectations,
        accepted_marker_request=accepted_marker_request,
        repository_verification_request=repository_verification_request,
        replay_request=replay_request,
        validation_context=validation_context,
        authorization_validation=authorization_validation_callable,
        accepted_marker_composition=accepted_marker_composition,
        repository_verification_composition=repository_verification_composition,
        remote_expectation_source=remote_expectation_source,
        repository_comparator=repository_comparator,
        replay_guard=replay_guard,
    )
