"""Bounded repository verification composition."""
from __future__ import annotations

from dataclasses import dataclass
from inspect import getattr_static
from typing import Protocol

__all__ = (
    "run_phase_12_repository_verification_composition_v1",
)

_REMOTE_EXPECTATION_SOURCE_FAILED = "REMOTE_EXPECTATION_SOURCE_FAILED"
_REMOTE_EXPECTATION_SOURCE_RESULT_INVALID = "REMOTE_EXPECTATION_SOURCE_RESULT_INVALID"
_REPOSITORY_COMPARATOR_FAILED = "REPOSITORY_COMPARATOR_FAILED"
_REPOSITORY_COMPARATOR_RESULT_INVALID = "REPOSITORY_COMPARATOR_RESULT_INVALID"


class _Phase12RemoteExpectationSourceCallableV1(Protocol):
    def __call__(
        self,
        *,
        source_path: str,
    ) -> object:
        ...


class _Phase12RepositoryComparatorCallableV1(Protocol):
    def __call__(
        self,
        *,
        repository_path: str,
        repository_identity: str,
        accepted_locked_commit: str,
        expected_origin_fetch_url: str,
        expected_origin_push_url: str,
    ) -> object:
        ...


@dataclass(frozen=True, slots=True, kw_only=True)
class _Phase12RepositoryVerificationCompositionResultV1:
    is_verified: bool
    failure_codes: tuple[str, ...]

    def __repr__(self) -> str:
        return (
            "_Phase12RepositoryVerificationCompositionResultV1("
            f"is_verified={self.is_verified!r}, "
            f"failure_count={len(self.failure_codes)})"
        )


def _failure(code: str) -> _Phase12RepositoryVerificationCompositionResultV1:
    return _Phase12RepositoryVerificationCompositionResultV1(
        is_verified=False,
        failure_codes=(code,),
    )


def _has_required_attributes(value: object, names: tuple[str, ...]) -> bool:
    for name in names:
        try:
            getattr_static(value, name)
        except AttributeError:
            return False
    return True


def _source_result(
    value: object,
) -> tuple[
    _Phase12RepositoryVerificationCompositionResultV1 | None,
    str | None,
    str | None,
]:
    names = (
        "is_loaded",
        "failure_codes",
        "expected_origin_fetch_url",
        "expected_origin_push_url",
    )
    if value is None or not _has_required_attributes(value, names):
        return (_failure(_REMOTE_EXPECTATION_SOURCE_RESULT_INVALID), None, None)

    is_loaded = value.is_loaded
    failure_codes = value.failure_codes
    expected_origin_fetch_url = value.expected_origin_fetch_url
    expected_origin_push_url = value.expected_origin_push_url

    if type(is_loaded) is not bool or type(failure_codes) is not tuple:
        return (_failure(_REMOTE_EXPECTATION_SOURCE_RESULT_INVALID), None, None)

    if is_loaded is True:
        if (
            failure_codes != ()
            or type(expected_origin_fetch_url) is not str
            or type(expected_origin_push_url) is not str
        ):
            return (_failure(_REMOTE_EXPECTATION_SOURCE_RESULT_INVALID), None, None)
        return (None, expected_origin_fetch_url, expected_origin_push_url)

    if (
        len(failure_codes) < 1
        or not all(type(code) is str for code in failure_codes)
        or expected_origin_fetch_url is not None
        or expected_origin_push_url is not None
    ):
        return (_failure(_REMOTE_EXPECTATION_SOURCE_RESULT_INVALID), None, None)
    return (_failure(_REMOTE_EXPECTATION_SOURCE_FAILED), None, None)


def _comparator_result(
    value: object,
) -> _Phase12RepositoryVerificationCompositionResultV1 | None:
    names = ("is_match", "failure_codes")
    if value is None or not _has_required_attributes(value, names):
        return _failure(_REPOSITORY_COMPARATOR_RESULT_INVALID)

    is_match = value.is_match
    failure_codes = value.failure_codes

    if type(is_match) is not bool or type(failure_codes) is not tuple:
        return _failure(_REPOSITORY_COMPARATOR_RESULT_INVALID)

    if is_match is True:
        if failure_codes != ():
            return _failure(_REPOSITORY_COMPARATOR_RESULT_INVALID)
        return None

    if len(failure_codes) < 1 or not all(type(code) is str for code in failure_codes):
        return _failure(_REPOSITORY_COMPARATOR_RESULT_INVALID)
    return _failure(_REPOSITORY_COMPARATOR_FAILED)


def run_phase_12_repository_verification_composition_v1(
    *,
    source_path: str,
    repository_path: str,
    repository_identity: str,
    accepted_locked_commit: str,
    remote_expectation_source: _Phase12RemoteExpectationSourceCallableV1,
    repository_comparator: _Phase12RepositoryComparatorCallableV1,
) -> _Phase12RepositoryVerificationCompositionResultV1:
    if type(source_path) is not str:
        raise TypeError()
    if type(repository_path) is not str:
        raise TypeError()
    if type(repository_identity) is not str:
        raise TypeError()
    if type(accepted_locked_commit) is not str:
        raise TypeError()
    if not callable(remote_expectation_source):
        raise TypeError()
    if not callable(repository_comparator):
        raise TypeError()

    source_value = remote_expectation_source(source_path=source_path)
    source_failure, expected_origin_fetch_url, expected_origin_push_url = _source_result(
        source_value
    )
    if source_failure is not None:
        return source_failure

    comparator_value = repository_comparator(
        repository_path=repository_path,
        repository_identity=repository_identity,
        accepted_locked_commit=accepted_locked_commit,
        expected_origin_fetch_url=expected_origin_fetch_url,
        expected_origin_push_url=expected_origin_push_url,
    )
    comparator_failure = _comparator_result(comparator_value)
    if comparator_failure is not None:
        return comparator_failure

    return _Phase12RepositoryVerificationCompositionResultV1(
        is_verified=True,
        failure_codes=(),
    )
