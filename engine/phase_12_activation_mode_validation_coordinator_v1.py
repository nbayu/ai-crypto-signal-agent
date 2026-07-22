"""Bounded, injected validation dispatch for Phase 12 activation modes."""
from __future__ import annotations

from dataclasses import dataclass


_CLOSED = "CLOSED"
_CREDENTIAL = "CREDENTIAL_VALIDATION"
_CONNECTIVITY = "TELEGRAM_CONNECTIVITY_VALIDATION"
_START = "TELEGRAM_START_VALIDATION"
_WORKLOAD = "CONTROLLED_WORKLOAD"
_NON_CLOSED = frozenset((_CREDENTIAL, _CONNECTIVITY, _START, _WORKLOAD))
_CLOSED_RESULT = (1, '{"launcher_result":"BLOCKED"}')
_AUTHORIZATION_FAILURE = (1, '{"executable_result":"ACTIVATION_MODE_AUTHORIZATION_FAILURE"}')
_UNEXPECTED_FAILURE = (70, '{"executable_result":"UNEXPECTED_FAILURE"}')
_CREDENTIAL_SUCCESS = (0, '{"activation_mode_validation_result":"CREDENTIAL_VALID"}')
_CREDENTIAL_FAILURE = (1, '{"activation_mode_validation_result":"CREDENTIAL_INVALID"}')
_CONNECTIVITY_SUCCESS = (0, '{"activation_mode_validation_result":"TELEGRAM_CONNECTIVITY_VALID"}')
_CONNECTIVITY_FAILURE = (1, '{"activation_mode_validation_result":"TELEGRAM_CONNECTIVITY_FAILURE"}')
_START_SUCCESS = (0, '{"activation_mode_validation_result":"TELEGRAM_START_VALID"}')
_START_FAILURE = (1, '{"activation_mode_validation_result":"TELEGRAM_START_FAILURE"}')


class ActivationModeValidationControlledFailureV1(Exception):
    """A fixed local marker for a controlled dependency failure."""


@dataclass(frozen=True, slots=True)
class ActivationModeApplicationInitializationV1:
    """A bounded application-initialization outcome supplied by an injected seam."""

    application: object
    ready: bool

    def __post_init__(self) -> None:
        if type(self.ready) is not bool:
            raise ValueError("INVALID_APPLICATION_INITIALIZATION")


def _mode(configuration: object) -> str | None:
    value = getattr(configuration, "activation_mode", None)
    if not isinstance(value, str):
        return None
    if value not in _NON_CLOSED and value != _CLOSED:
        return None
    return value


def _authorization_context(
    configuration: object,
    mode: str,
    accepted_locked_commit: object,
    now_utc: object,
) -> dict[str, object] | None:
    fields = (
        "owner_authorization_id",
        "approval_checkpoint_id",
        "approved_locked_commit",
        "approved_at",
        "expires_at",
    )
    values: dict[str, object] = {
        "configuration": configuration,
        "activation_mode": mode,
        "accepted_locked_commit": accepted_locked_commit,
        "now_utc": now_utc,
    }
    for field in fields:
        value = getattr(configuration, field, None)
        if not isinstance(value, str):
            return None
        values[field] = value
    return values


def _authorized(
    *,
    configuration: object,
    mode: str,
    accepted_locked_commit: object,
    now_utc: object,
    authorization_verifier: object,
) -> tuple[bool, tuple[int, str] | None]:
    context = _authorization_context(
        configuration, mode, accepted_locked_commit, now_utc
    )
    if context is None or not callable(authorization_verifier):
        return (False, _AUTHORIZATION_FAILURE)
    try:
        authorized = authorization_verifier(**context)
    except ActivationModeValidationControlledFailureV1:
        return (False, _AUTHORIZATION_FAILURE)
    except Exception:
        return (False, _UNEXPECTED_FAILURE)
    if authorized is not True:
        return (False, _AUTHORIZATION_FAILURE)
    return (True, None)


def _credential(
    *,
    credential_locator: object,
    credential_reader: object,
    credential_validator: object,
) -> tuple[bool, object | None, tuple[int, str] | None]:
    if not all(callable(value) for value in (credential_locator, credential_reader, credential_validator)):
        return (False, None, _CREDENTIAL_FAILURE)
    try:
        locator = credential_locator()
        if locator is None:
            return (False, None, _CREDENTIAL_FAILURE)
        value = credential_reader(locator=locator)
        if not isinstance(value, str) or not value:
            return (False, None, _CREDENTIAL_FAILURE)
        if credential_validator(credential=value) is not True:
            return (False, None, _CREDENTIAL_FAILURE)
    except ActivationModeValidationControlledFailureV1:
        return (False, None, _CREDENTIAL_FAILURE)
    except Exception:
        return (False, None, _UNEXPECTED_FAILURE)
    return (True, value, None)


def _connectivity(
    *,
    credential: object,
    identity_probe_client_factory: object,
    authenticated_identity_probe: object,
) -> tuple[bool, object | None, tuple[int, str] | None]:
    if not callable(identity_probe_client_factory) or not callable(authenticated_identity_probe):
        return (False, None, _CONNECTIVITY_FAILURE)
    try:
        client = identity_probe_client_factory(credential=credential)
        if client is None:
            return (False, None, _CONNECTIVITY_FAILURE)
        if authenticated_identity_probe(client=client) is not True:
            return (False, None, _CONNECTIVITY_FAILURE)
    except ActivationModeValidationControlledFailureV1:
        return (False, None, _CONNECTIVITY_FAILURE)
    except Exception:
        return (False, None, _UNEXPECTED_FAILURE)
    return (True, client, None)


def _start(
    *,
    credential: object,
    client: object,
    application_initializer: object,
    application_shutdown: object,
) -> tuple[int, str]:
    if not callable(application_initializer) or not callable(application_shutdown):
        return _START_FAILURE
    try:
        initialized = application_initializer(credential=credential, client=client)
    except ActivationModeValidationControlledFailureV1:
        return _START_FAILURE
    except Exception:
        return _UNEXPECTED_FAILURE
    if not isinstance(initialized, ActivationModeApplicationInitializationV1):
        return _START_FAILURE
    try:
        application_shutdown(application=initialized.application)
    except ActivationModeValidationControlledFailureV1:
        return _START_FAILURE
    except Exception:
        return _UNEXPECTED_FAILURE
    if initialized.ready is not True:
        return _START_FAILURE
    return _START_SUCCESS


def run_phase_12_activation_mode_validation_coordinator(
    *,
    configuration,
    accepted_locked_commit,
    now_utc,
    authorization_verifier,
    credential_locator,
    credential_reader,
    credential_validator,
    identity_probe_client_factory,
    authenticated_identity_probe,
    application_initializer,
    application_shutdown,
    production_launcher,
) -> tuple[int, str]:
    """Dispatch one validated activation mode through bounded injected seams."""

    mode = _mode(configuration)
    if mode is None:
        return _AUTHORIZATION_FAILURE
    if mode == _CLOSED:
        return _CLOSED_RESULT

    authorized, outcome = _authorized(
        configuration=configuration,
        mode=mode,
        accepted_locked_commit=accepted_locked_commit,
        now_utc=now_utc,
        authorization_verifier=authorization_verifier,
    )
    if not authorized:
        return outcome  # type: ignore[return-value]

    if mode == _WORKLOAD:
        if not callable(production_launcher):
            return _UNEXPECTED_FAILURE
        try:
            result = production_launcher()
        except Exception:
            return _UNEXPECTED_FAILURE
        if (
            not isinstance(result, tuple)
            or len(result) != 2
            or type(result[0]) is not int
            or type(result[1]) is not str
        ):
            return _UNEXPECTED_FAILURE
        return result

    credential_valid, credential, outcome = _credential(
        credential_locator=credential_locator,
        credential_reader=credential_reader,
        credential_validator=credential_validator,
    )
    if not credential_valid:
        if outcome == _UNEXPECTED_FAILURE:
            return _UNEXPECTED_FAILURE
        return _CREDENTIAL_FAILURE if mode == _CREDENTIAL else (
            _CONNECTIVITY_FAILURE if mode == _CONNECTIVITY else _START_FAILURE
        )
    if mode == _CREDENTIAL:
        return _CREDENTIAL_SUCCESS

    connectivity_valid, client, outcome = _connectivity(
        credential=credential,
        identity_probe_client_factory=identity_probe_client_factory,
        authenticated_identity_probe=authenticated_identity_probe,
    )
    if not connectivity_valid:
        if outcome == _UNEXPECTED_FAILURE:
            return _UNEXPECTED_FAILURE
        return _CONNECTIVITY_FAILURE if mode == _CONNECTIVITY else _START_FAILURE
    if mode == _CONNECTIVITY:
        return _CONNECTIVITY_SUCCESS

    return _start(
        credential=credential,
        client=client,
        application_initializer=application_initializer,
        application_shutdown=application_shutdown,
    )
