"""Bounded Phase 12 authorization and repository validation composition."""
from __future__ import annotations

from dataclasses import dataclass
from inspect import getattr_static
from typing import Protocol
from engine.phase_12_authorization_trust_expectations_v1 import Phase12AuthorizationTrustExpectationsV1

__all__ = (
    "build_phase_12_authorization_request_v1",
    "build_phase_12_validation_context_v1",
    "build_phase_12_accepted_marker_request_v1",
    "build_phase_12_repository_verification_request_v1",
    "build_phase_12_replay_request_v1",
    "run_phase_12_authorization_repository_validation_composition_v1",
)

_AUTHORIZATION_VALIDATION_FAILED = "AUTHORIZATION_VALIDATION_FAILED"
_AUTHORIZATION_VALIDATION_RESULT_INVALID = "AUTHORIZATION_VALIDATION_RESULT_INVALID"
_ACCEPTED_MARKER_VALIDATION_FAILED = "ACCEPTED_MARKER_VALIDATION_FAILED"
_ACCEPTED_MARKER_VALIDATION_RESULT_INVALID = "ACCEPTED_MARKER_VALIDATION_RESULT_INVALID"
_REPOSITORY_VERIFICATION_FAILED = "REPOSITORY_VERIFICATION_FAILED"
_REPOSITORY_VERIFICATION_RESULT_INVALID = "REPOSITORY_VERIFICATION_RESULT_INVALID"
_REPLAY_CHECK_AND_RECORD_FAILED = "REPLAY_CHECK_AND_RECORD_FAILED"
_REPLAY_RESULT_INVALID = "REPLAY_RESULT_INVALID"
_REPLAY_ALREADY_CONSUMED = "REPLAY_ALREADY_CONSUMED"
_REPLAY_IDENTITY_ALREADY_CONSUMED = "REPLAY_IDENTITY_ALREADY_CONSUMED"


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12AuthorizationRequestV1:
    document: str
    canonical_payload_bytes: bytes
    signature_bytes: bytes
    activation_mode: str
    owner_authorization_id: str
    approval_checkpoint_id: str
    approved_locked_commit: str
    approved_at: str
    expires_at: str
    accepted_locked_commit_expectation: str

    def __repr__(self) -> str:
        return "_Phase12AuthorizationRequestV1(field_count=10)"



@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12AcceptedMarkerRequestV1:
    path: str
    expected_metadata_policy: object

    def __repr__(self) -> str:
        return "_Phase12AcceptedMarkerRequestV1(field_count=2)"


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12RepositoryVerificationRequestV1:
    source_path: str
    repository_path: str

    def __repr__(self) -> str:
        return "_Phase12RepositoryVerificationRequestV1(field_count=2)"


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12ReplayRequestV1:
    path: str
    expected_schema_identifier: str
    expected_deployment_identifier: str

    def __repr__(self) -> str:
        return "_Phase12ReplayRequestV1(field_count=3)"


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12ValidationContextV1:
    configuration: object
    now_utc: object

    def __repr__(self) -> str:
        return "_Phase12ValidationContextV1(field_count=2)"



def build_phase_12_authorization_request_v1(
    *,
    document: str,
    canonical_payload_bytes: bytes,
    signature_bytes: bytes,
    activation_mode: str,
    owner_authorization_id: str,
    approval_checkpoint_id: str,
    approved_locked_commit: str,
    approved_at: str,
    expires_at: str,
    accepted_locked_commit_expectation: str,
) -> object:
    return _Phase12AuthorizationRequestV1(
        document=document,
        canonical_payload_bytes=canonical_payload_bytes,
        signature_bytes=signature_bytes,
        activation_mode=activation_mode,
        owner_authorization_id=owner_authorization_id,
        approval_checkpoint_id=approval_checkpoint_id,
        approved_locked_commit=approved_locked_commit,
        approved_at=approved_at,
        expires_at=expires_at,
        accepted_locked_commit_expectation=accepted_locked_commit_expectation,
    )



def build_phase_12_validation_context_v1(
    *,
    configuration: object,
    now_utc: object,
) -> object:
    return _Phase12ValidationContextV1(
        configuration=configuration,
        now_utc=now_utc,
    )


def build_phase_12_accepted_marker_request_v1(
    *,
    path: str,
    expected_metadata_policy: object,
) -> object:
    return _Phase12AcceptedMarkerRequestV1(
        path=path,
        expected_metadata_policy=expected_metadata_policy,
    )


def build_phase_12_repository_verification_request_v1(
    *,
    source_path: str,
    repository_path: str,
) -> object:
    return _Phase12RepositoryVerificationRequestV1(
        source_path=source_path,
        repository_path=repository_path,
    )


def build_phase_12_replay_request_v1(
    *,
    path: str,
    expected_schema_identifier: str,
    expected_deployment_identifier: str,
) -> object:
    return _Phase12ReplayRequestV1(
        path=path,
        expected_schema_identifier=expected_schema_identifier,
        expected_deployment_identifier=expected_deployment_identifier,
    )

class _Phase12AuthorizationValidationCallableV1(Protocol):
    def __call__(self, *, authorization_request: _Phase12AuthorizationRequestV1, trust_expectations: Phase12AuthorizationTrustExpectationsV1, validation_context: _Phase12ValidationContextV1) -> object: ...


class _Phase12AcceptedMarkerCompositionCallableV1(Protocol):
    def __call__(self, *, accepted_marker_request: _Phase12AcceptedMarkerRequestV1) -> object: ...


class _Phase12RemoteExpectationSourceCallableV1(Protocol):
    def __call__(self, *, source_path: str) -> object: ...


class _Phase12RepositoryComparatorCallableV1(Protocol):
    def __call__(self, *, repository_path: str, repository_identity: str, accepted_locked_commit: str, expected_origin_fetch_url: str, expected_origin_push_url: str) -> object: ...


class _Phase12RepositoryVerificationCompositionCallableV1(Protocol):
    def __call__(self, *, source_path: str, repository_path: str, repository_identity: str, accepted_locked_commit: str, remote_expectation_source: _Phase12RemoteExpectationSourceCallableV1, repository_comparator: _Phase12RepositoryComparatorCallableV1) -> object: ...


class _Phase12ReplayGuardCallableV1(Protocol):
    def __call__(self, *, path: str, replay_identity: str, expected_schema_identifier: str, expected_deployment_identifier: str) -> object: ...


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12AuthorizationRepositoryValidationCompositionResultV1:
    is_validated: bool
    failure_codes: tuple[str, ...]

    def __repr__(self) -> str:
        return "_Phase12AuthorizationRepositoryValidationCompositionResultV1(" f"is_validated={self.is_validated!r}, failure_count={len(self.failure_codes)})"


def _failure(code: str) -> _Phase12AuthorizationRepositoryValidationCompositionResultV1:
    return _Phase12AuthorizationRepositoryValidationCompositionResultV1(is_validated=False, failure_codes=(code,))


def _has_required_attributes(value: object, names: tuple[str, ...]) -> bool:
    for name in names:
        try:
            getattr_static(value, name)
        except AttributeError:
            return False
    return True


def _nonempty_string_tuple(value: object) -> bool:
    return type(value) is tuple and len(value) >= 1 and all(type(item) is str for item in value)


def _authorization_result(value: object, expected_deployment_identifier: str) -> tuple[_Phase12AuthorizationRepositoryValidationCompositionResultV1 | None, str | None, str | None]:
    names = ("is_validated", "failure_codes", "repository_identity", "deployment_identifier", "replay_identity")
    if not _has_required_attributes(value, names):
        return _failure(_AUTHORIZATION_VALIDATION_RESULT_INVALID), None, None
    is_validated = value.is_validated
    failure_codes = value.failure_codes
    repository_identity = value.repository_identity
    deployment_identifier = value.deployment_identifier
    replay_identity = value.replay_identity
    if type(is_validated) is not bool or type(failure_codes) is not tuple:
        return _failure(_AUTHORIZATION_VALIDATION_RESULT_INVALID), None, None
    if is_validated is True:
        if failure_codes != () or type(repository_identity) is not str or type(deployment_identifier) is not str or type(replay_identity) is not str or deployment_identifier != expected_deployment_identifier:
            return _failure(_AUTHORIZATION_VALIDATION_RESULT_INVALID), None, None
        return None, repository_identity, replay_identity
    if not _nonempty_string_tuple(failure_codes) or repository_identity is not None or deployment_identifier is not None or replay_identity is not None:
        return _failure(_AUTHORIZATION_VALIDATION_RESULT_INVALID), None, None
    return _failure(_AUTHORIZATION_VALIDATION_FAILED), None, None


def _marker_result(value: object) -> tuple[_Phase12AuthorizationRepositoryValidationCompositionResultV1 | None, str | None]:
    names = ("is_validated", "failure_codes", "accepted_locked_commit")
    if not _has_required_attributes(value, names):
        return _failure(_ACCEPTED_MARKER_VALIDATION_RESULT_INVALID), None
    is_validated = value.is_validated
    failure_codes = value.failure_codes
    accepted_locked_commit = value.accepted_locked_commit
    if type(is_validated) is not bool or type(failure_codes) is not tuple:
        return _failure(_ACCEPTED_MARKER_VALIDATION_RESULT_INVALID), None
    if is_validated is True:
        if failure_codes != () or type(accepted_locked_commit) is not str:
            return _failure(_ACCEPTED_MARKER_VALIDATION_RESULT_INVALID), None
        return None, accepted_locked_commit
    if not _nonempty_string_tuple(failure_codes) or accepted_locked_commit is not None:
        return _failure(_ACCEPTED_MARKER_VALIDATION_RESULT_INVALID), None
    return _failure(_ACCEPTED_MARKER_VALIDATION_FAILED), None


def _repository_result(value: object) -> _Phase12AuthorizationRepositoryValidationCompositionResultV1 | None:
    names = ("is_verified", "failure_codes")
    if not _has_required_attributes(value, names):
        return _failure(_REPOSITORY_VERIFICATION_RESULT_INVALID)
    is_verified = value.is_verified
    failure_codes = value.failure_codes
    if type(is_verified) is not bool or type(failure_codes) is not tuple:
        return _failure(_REPOSITORY_VERIFICATION_RESULT_INVALID)
    if is_verified is True:
        return None if failure_codes == () else _failure(_REPOSITORY_VERIFICATION_RESULT_INVALID)
    return _failure(_REPOSITORY_VERIFICATION_FAILED) if _nonempty_string_tuple(failure_codes) else _failure(_REPOSITORY_VERIFICATION_RESULT_INVALID)


def _replay_result(value: object, replay_identity: str, schema_identifier: str, deployment_identifier: str) -> _Phase12AuthorizationRepositoryValidationCompositionResultV1 | None:
    names = ("is_recorded", "was_already_consumed", "failure_codes", "replay_identity", "schema_identifier", "deployment_identifier")
    if not _has_required_attributes(value, names):
        return _failure(_REPLAY_RESULT_INVALID)
    is_recorded = value.is_recorded
    was_already_consumed = value.was_already_consumed
    failure_codes = value.failure_codes
    result_identity = value.replay_identity
    result_schema = value.schema_identifier
    result_deployment = value.deployment_identifier
    if type(is_recorded) is not bool or type(was_already_consumed) is not bool or type(failure_codes) is not tuple:
        return _failure(_REPLAY_RESULT_INVALID)
    if is_recorded is True:
        if was_already_consumed is False and failure_codes == () and type(result_identity) is str and result_identity == replay_identity and type(result_schema) is str and result_schema == schema_identifier and type(result_deployment) is str and result_deployment == deployment_identifier:
            return None
        return _failure(_REPLAY_RESULT_INVALID)
    if was_already_consumed is True:
        if failure_codes == (_REPLAY_IDENTITY_ALREADY_CONSUMED,) and type(result_identity) is str and result_identity == replay_identity and type(result_schema) is str and result_schema == schema_identifier and type(result_deployment) is str and result_deployment == deployment_identifier:
            return _failure(_REPLAY_ALREADY_CONSUMED)
        return _failure(_REPLAY_RESULT_INVALID)
    if len(failure_codes) == 1 and type(failure_codes[0]) is str and failure_codes[0] != _REPLAY_IDENTITY_ALREADY_CONSUMED and result_identity is None and result_schema is None and result_deployment is None:
        return _failure(_REPLAY_CHECK_AND_RECORD_FAILED)
    return _failure(_REPLAY_RESULT_INVALID)


def run_phase_12_authorization_repository_validation_composition_v1(
    *,
    authorization_request: _Phase12AuthorizationRequestV1,
    trust_expectations: Phase12AuthorizationTrustExpectationsV1,
    accepted_marker_request: _Phase12AcceptedMarkerRequestV1,
    repository_verification_request: _Phase12RepositoryVerificationRequestV1,
    replay_request: _Phase12ReplayRequestV1,
    validation_context: _Phase12ValidationContextV1,
    authorization_validation: _Phase12AuthorizationValidationCallableV1,
    accepted_marker_composition: _Phase12AcceptedMarkerCompositionCallableV1,
    repository_verification_composition: _Phase12RepositoryVerificationCompositionCallableV1,
    remote_expectation_source: _Phase12RemoteExpectationSourceCallableV1,
    repository_comparator: _Phase12RepositoryComparatorCallableV1,
    replay_guard: _Phase12ReplayGuardCallableV1,
) -> _Phase12AuthorizationRepositoryValidationCompositionResultV1:
    if type(authorization_request) is not _Phase12AuthorizationRequestV1: raise TypeError()
    if type(trust_expectations) is not Phase12AuthorizationTrustExpectationsV1: raise TypeError()
    if type(accepted_marker_request) is not _Phase12AcceptedMarkerRequestV1: raise TypeError()
    if type(repository_verification_request) is not _Phase12RepositoryVerificationRequestV1: raise TypeError()
    if type(replay_request) is not _Phase12ReplayRequestV1: raise TypeError()
    if type(validation_context) is not _Phase12ValidationContextV1: raise TypeError()
    if not callable(authorization_validation): raise TypeError()
    if not callable(accepted_marker_composition): raise TypeError()
    if not callable(repository_verification_composition): raise TypeError()
    if not callable(remote_expectation_source): raise TypeError()
    if not callable(repository_comparator): raise TypeError()
    if not callable(replay_guard): raise TypeError()
    if type(repository_verification_request.source_path) is not str: raise TypeError()
    if type(repository_verification_request.repository_path) is not str: raise TypeError()
    if type(replay_request.path) is not str: raise TypeError()
    if type(replay_request.expected_schema_identifier) is not str: raise TypeError()
    if type(replay_request.expected_deployment_identifier) is not str: raise TypeError()

    authorization_value = authorization_validation(authorization_request=authorization_request, trust_expectations=trust_expectations, validation_context=validation_context)
    authorization_failure, repository_identity, replay_identity = _authorization_result(authorization_value, replay_request.expected_deployment_identifier)
    if authorization_failure is not None: return authorization_failure
    marker_value = accepted_marker_composition(accepted_marker_request=accepted_marker_request)
    marker_failure, accepted_locked_commit = _marker_result(marker_value)
    if marker_failure is not None: return marker_failure
    repository_value = repository_verification_composition(source_path=repository_verification_request.source_path, repository_path=repository_verification_request.repository_path, repository_identity=repository_identity, accepted_locked_commit=accepted_locked_commit, remote_expectation_source=remote_expectation_source, repository_comparator=repository_comparator)
    repository_failure = _repository_result(repository_value)
    if repository_failure is not None: return repository_failure
    replay_value = replay_guard(path=replay_request.path, replay_identity=replay_identity, expected_schema_identifier=replay_request.expected_schema_identifier, expected_deployment_identifier=replay_request.expected_deployment_identifier)
    replay_failure = _replay_result(replay_value, replay_identity, replay_request.expected_schema_identifier, replay_request.expected_deployment_identifier)
    if replay_failure is not None: return replay_failure
    return _Phase12AuthorizationRepositoryValidationCompositionResultV1(is_validated=True, failure_codes=())
