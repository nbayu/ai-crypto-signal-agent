"""Contract tests for the bounded Phase 12 activation-mode coordinator."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import inspect

import pytest

from engine.phase_12_activation_configuration_v1 import (
    Phase12ActivationConfigurationV1,
)
from engine.phase_12_activation_mode_validation_coordinator_v1 import (
    ActivationModeApplicationInitializationV1,
    ActivationModeValidationControlledFailureV1,
    run_phase_12_activation_mode_validation_coordinator,
)


_NOW = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)
_COMMIT = "415c77c4b9a021bbc211797d7b41e74c55c18538"
_CLOSED_JSON = '{"launcher_result":"BLOCKED"}'
_AUTH_FAILURE_JSON = '{"executable_result":"ACTIVATION_MODE_AUTHORIZATION_FAILURE"}'
_UNEXPECTED_JSON = '{"executable_result":"UNEXPECTED_FAILURE"}'
_MODE_GATES = {
    "CLOSED": (False, False, False, False, False),
    "CREDENTIAL_VALIDATION": (True, True, False, False, False),
    "TELEGRAM_CONNECTIVITY_VALIDATION": (True, True, True, False, False),
    "TELEGRAM_START_VALIDATION": (True, True, True, False, True),
    "CONTROLLED_WORKLOAD": (True, True, True, True, True),
}
_SUCCESS = {
    "CREDENTIAL_VALIDATION": '{"activation_mode_validation_result":"CREDENTIAL_VALID"}',
    "TELEGRAM_CONNECTIVITY_VALIDATION": '{"activation_mode_validation_result":"TELEGRAM_CONNECTIVITY_VALID"}',
    "TELEGRAM_START_VALIDATION": '{"activation_mode_validation_result":"TELEGRAM_START_VALID"}',
}
_FAILURE = {
    "CREDENTIAL_VALIDATION": '{"activation_mode_validation_result":"CREDENTIAL_INVALID"}',
    "TELEGRAM_CONNECTIVITY_VALIDATION": '{"activation_mode_validation_result":"TELEGRAM_CONNECTIVITY_FAILURE"}',
    "TELEGRAM_START_VALIDATION": '{"activation_mode_validation_result":"TELEGRAM_START_FAILURE"}',
}


def _configuration(mode: str) -> Phase12ActivationConfigurationV1:
    gates = _MODE_GATES[mode]
    evidence = ("NONE",) * 5 if mode == "CLOSED" else (
        "owner-authorization-v1",
        "checkpoint-v1",
        _COMMIT,
        "2026-07-22T12:00:00Z",
        "2026-07-22T12:05:00Z",
    )
    return Phase12ActivationConfigurationV1(
        schema_version="phase12-activation-v1",
        activation_mode=mode,
        owner_authorization_id=evidence[0],
        approval_checkpoint_id=evidence[1],
        approved_locked_commit=evidence[2],
        approved_at=evidence[3],
        expires_at=evidence[4],
        activation_gate_open=gates[0],
        credential_gate_open=gates[1],
        network_gate_open=gates[2],
        workload_gate_open=gates[3],
        telegram_start_authorized=gates[4],
    )


class _Events:
    def __init__(self) -> None:
        self.values: list[str] = []

    def add(self, value: str) -> None:
        self.values.append(value)


class _BaseInterrupt(BaseException):
    pass


def _dependencies(events: _Events, **overrides: object) -> dict[str, object]:
    def authorization_verifier(**kwargs: object) -> bool:
        events.add("authorization")
        assert kwargs["accepted_locked_commit"] == _COMMIT
        assert kwargs["now_utc"] == _NOW
        return True

    def credential_locator() -> object:
        events.add("locator")
        return object()

    def credential_reader(*, locator: object) -> str:
        assert locator is not None
        events.add("credential")
        return "opaque-test-credential"

    def credential_validator(*, credential: object) -> bool:
        assert isinstance(credential, str)
        events.add("lexical")
        return True

    def identity_probe_client_factory(*, credential: object) -> object:
        assert isinstance(credential, str)
        events.add("client")
        return object()

    def authenticated_identity_probe(*, client: object) -> bool:
        assert client is not None
        events.add("probe")
        return True

    def application_initializer(*, credential: object, client: object) -> object:
        assert isinstance(credential, str)
        assert client is not None
        events.add("initialize")
        return ActivationModeApplicationInitializationV1(application=object(), ready=True)

    def application_shutdown(*, application: object) -> None:
        assert application is not None
        events.add("shutdown")

    def production_launcher(**kwargs: object) -> tuple[int, str]:
        events.add("launcher")
        return (0, '{"launcher_result":"PREPARED"}')

    values: dict[str, object] = {
        "accepted_locked_commit": _COMMIT,
        "now_utc": _NOW,
        "authorization_verifier": authorization_verifier,
        "credential_locator": credential_locator,
        "credential_reader": credential_reader,
        "credential_validator": credential_validator,
        "identity_probe_client_factory": identity_probe_client_factory,
        "authenticated_identity_probe": authenticated_identity_probe,
        "application_initializer": application_initializer,
        "application_shutdown": application_shutdown,
        "production_launcher": production_launcher,
    }
    values.update(overrides)
    return values


def _run(
    configuration: Phase12ActivationConfigurationV1,
    events: _Events,
    **overrides: object,
) -> tuple[int, str]:
    return run_phase_12_activation_mode_validation_coordinator(
        configuration=configuration,
        **_dependencies(events, **overrides),
    )


def test_public_api_is_keyword_only_and_has_no_import_time_effect() -> None:
    signature = inspect.signature(run_phase_12_activation_mode_validation_coordinator)
    assert tuple(signature.parameters) == (
        "configuration",
        "accepted_locked_commit",
        "now_utc",
        "authorization_verifier",
        "credential_locator",
        "credential_reader",
        "credential_validator",
        "identity_probe_client_factory",
        "authenticated_identity_probe",
        "application_initializer",
        "application_shutdown",
        "production_launcher",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


def test_closed_is_fixed_blocked_and_reaches_no_dependency() -> None:
    events = _Events()
    assert _run(_configuration("CLOSED"), events) == (1, _CLOSED_JSON)
    assert events.values == []


@pytest.mark.parametrize(
    "mode",
    (
        "CREDENTIAL_VALIDATION",
        "TELEGRAM_CONNECTIVITY_VALIDATION",
        "TELEGRAM_START_VALIDATION",
        "CONTROLLED_WORKLOAD",
    ),
)
def test_non_closed_authorization_receives_immutable_configuration_context(mode: str) -> None:
    events = _Events()
    received: list[dict[str, object]] = []

    def verifier(**kwargs: object) -> bool:
        events.add("authorization")
        received.append(kwargs)
        return False

    assert _run(_configuration(mode), events, authorization_verifier=verifier) == (1, _AUTH_FAILURE_JSON)
    assert events.values == ["authorization"]
    context = received[0]
    configuration = _configuration(mode)
    assert context["configuration"] == configuration
    assert context["activation_mode"] == mode
    assert context["owner_authorization_id"] == configuration.owner_authorization_id
    assert context["approval_checkpoint_id"] == configuration.approval_checkpoint_id
    assert context["approved_locked_commit"] == _COMMIT
    assert context["approved_at"] == configuration.approved_at
    assert context["expires_at"] == configuration.expires_at
    assert context["accepted_locked_commit"] == _COMMIT
    assert context["now_utc"] == _NOW


@pytest.mark.parametrize(
    "mode",
    (
        "CREDENTIAL_VALIDATION",
        "TELEGRAM_CONNECTIVITY_VALIDATION",
        "TELEGRAM_START_VALIDATION",
        "CONTROLLED_WORKLOAD",
    ),
)
def test_authorization_rejection_is_fail_closed_before_all_effects(mode: str) -> None:
    events = _Events()
    assert _run(
        _configuration(mode), events, authorization_verifier=lambda **_: False
    ) == (1, _AUTH_FAILURE_JSON)
    assert events.values == []


def test_unexpected_authorization_failure_is_sanitized_and_baseexception_propagates() -> None:
    events = _Events()
    assert _run(
        _configuration("CREDENTIAL_VALIDATION"),
        events,
        authorization_verifier=lambda **_: (_ for _ in ()).throw(RuntimeError("detail")),
    ) == (70, _UNEXPECTED_JSON)
    assert events.values == []
    interrupt = _BaseInterrupt()
    with pytest.raises(_BaseInterrupt) as caught:
        _run(
            _configuration("CREDENTIAL_VALIDATION"),
            _Events(),
            authorization_verifier=lambda **_: (_ for _ in ()).throw(interrupt),
        )
    assert caught.value is interrupt


def test_credential_validation_is_exactly_once_and_isolated() -> None:
    events = _Events()
    assert _run(_configuration("CREDENTIAL_VALIDATION"), events) == (
        0,
        _SUCCESS["CREDENTIAL_VALIDATION"],
    )
    assert events.values == ["authorization", "locator", "credential", "lexical"]


@pytest.mark.parametrize(
    "failure_name",
    ("locator", "credential", "lexical"),
)
def test_credential_controlled_failures_are_sanitized_and_do_not_escalate(failure_name: str) -> None:
    events = _Events()
    values: dict[str, object] = {}
    if failure_name == "locator":
        values["credential_locator"] = lambda: None
    elif failure_name == "credential":
        values["credential_reader"] = lambda **_: None
    else:
        values["credential_validator"] = lambda **_: False
    assert _run(_configuration("CREDENTIAL_VALIDATION"), events, **values) == (
        1,
        _FAILURE["CREDENTIAL_VALIDATION"],
    )
    assert "client" not in events.values
    assert "probe" not in events.values
    assert "initialize" not in events.values
    assert "shutdown" not in events.values
    assert "launcher" not in events.values


def test_connectivity_validation_is_exactly_once_and_has_one_identity_probe() -> None:
    events = _Events()
    assert _run(_configuration("TELEGRAM_CONNECTIVITY_VALIDATION"), events) == (
        0,
        _SUCCESS["TELEGRAM_CONNECTIVITY_VALIDATION"],
    )
    assert events.values == ["authorization", "locator", "credential", "lexical", "client", "probe"]


@pytest.mark.parametrize(
    "failure_name",
    ("locator", "credential", "lexical", "client", "probe"),
)
def test_connectivity_controlled_failures_are_isolated(failure_name: str) -> None:
    events = _Events()
    values: dict[str, object] = {}
    if failure_name == "locator":
        values["credential_locator"] = lambda: None
    elif failure_name == "credential":
        values["credential_reader"] = lambda **_: None
    elif failure_name == "lexical":
        values["credential_validator"] = lambda **_: False
    elif failure_name == "client":
        values["identity_probe_client_factory"] = lambda **_: None
    else:
        values["authenticated_identity_probe"] = lambda **_: False
    assert _run(_configuration("TELEGRAM_CONNECTIVITY_VALIDATION"), events, **values) == (
        1,
        _FAILURE["TELEGRAM_CONNECTIVITY_VALIDATION"],
    )
    assert "initialize" not in events.values
    assert "shutdown" not in events.values
    assert "launcher" not in events.values


def test_start_validation_initializes_then_shuts_down_once_without_launcher() -> None:
    events = _Events()
    assert _run(_configuration("TELEGRAM_START_VALIDATION"), events) == (
        0,
        _SUCCESS["TELEGRAM_START_VALIDATION"],
    )
    assert events.values == [
        "authorization", "locator", "credential", "lexical", "client", "probe", "initialize", "shutdown"
    ]


@pytest.mark.parametrize(
    "failure_name",
    ("locator", "credential", "lexical", "client", "probe", "initialize"),
)
def test_start_failure_before_a_resource_exists_does_not_shutdown(failure_name: str) -> None:
    events = _Events()
    values: dict[str, object] = {}
    if failure_name == "locator":
        values["credential_locator"] = lambda: None
    elif failure_name == "credential":
        values["credential_reader"] = lambda **_: None
    elif failure_name == "lexical":
        values["credential_validator"] = lambda **_: False
    elif failure_name == "client":
        values["identity_probe_client_factory"] = lambda **_: None
    elif failure_name == "probe":
        values["authenticated_identity_probe"] = lambda **_: False
    else:
        values["application_initializer"] = lambda **_: None
    assert _run(_configuration("TELEGRAM_START_VALIDATION"), events, **values) == (
        1,
        _FAILURE["TELEGRAM_START_VALIDATION"],
    )
    assert "shutdown" not in events.values
    assert "launcher" not in events.values


def test_start_not_ready_after_initialization_shuts_down_once() -> None:
    events = _Events()

    def initializer(**_: object) -> object:
        events.add("initialize")
        return ActivationModeApplicationInitializationV1(application=object(), ready=False)

    assert _run(
        _configuration("TELEGRAM_START_VALIDATION"), events, application_initializer=initializer
    ) == (1, _FAILURE["TELEGRAM_START_VALIDATION"])
    assert events.values == [
        "authorization", "locator", "credential", "lexical", "client", "probe", "initialize", "shutdown"
    ]


def test_start_shutdown_failure_is_unexpected_and_baseexception_propagates() -> None:
    events = _Events()
    assert _run(
        _configuration("TELEGRAM_START_VALIDATION"),
        events,
        application_shutdown=lambda **_: (_ for _ in ()).throw(RuntimeError("detail")),
    ) == (70, _UNEXPECTED_JSON)
    assert events.values == ["authorization", "locator", "credential", "lexical", "client", "probe", "initialize"]
    interrupt = _BaseInterrupt()
    with pytest.raises(_BaseInterrupt) as caught:
        _run(
            _configuration("TELEGRAM_START_VALIDATION"),
            _Events(),
            application_shutdown=lambda **_: (_ for _ in ()).throw(interrupt),
        )
    assert caught.value is interrupt


def test_controlled_workload_authorizes_then_passes_the_launcher_tuple_unchanged() -> None:
    events = _Events()
    launcher_result = (7, '{"launcher_result":"CONTROLLED_NON_SUCCESS"}')
    assert _run(
        _configuration("CONTROLLED_WORKLOAD"),
        events,
        production_launcher=lambda **_: launcher_result,
    ) == launcher_result
    assert events.values == ["authorization"]


def test_controlled_workload_never_runs_partial_mode_dependencies() -> None:
    events = _Events()
    assert _run(_configuration("CONTROLLED_WORKLOAD"), events) == (
        0,
        '{"launcher_result":"PREPARED"}',
    )
    assert events.values == ["authorization", "launcher"]


@pytest.mark.parametrize(
    "mode, forbidden",
    (
        ("CLOSED", {"authorization", "locator", "credential", "lexical", "client", "probe", "initialize", "shutdown", "launcher"}),
        ("CREDENTIAL_VALIDATION", {"client", "probe", "initialize", "shutdown", "launcher"}),
        ("TELEGRAM_CONNECTIVITY_VALIDATION", {"initialize", "shutdown", "launcher"}),
        ("TELEGRAM_START_VALIDATION", {"launcher"}),
        ("CONTROLLED_WORKLOAD", {"locator", "credential", "lexical", "client", "probe", "initialize", "shutdown"}),
    ),
)
def test_every_mode_isolated_from_more_powerful_dependencies(mode: str, forbidden: set[str]) -> None:
    events = _Events()
    _run(_configuration(mode), events)
    assert forbidden.isdisjoint(events.values)


@pytest.mark.parametrize("mode", tuple(_MODE_GATES))
def test_each_mode_has_no_retry_or_duplicate_dependency_invocation(mode: str) -> None:
    events = _Events()
    _run(_configuration(mode), events)
    assert len(events.values) == len(set(events.values))


@pytest.mark.parametrize("mode", tuple(_MODE_GATES))
def test_unexpected_ordinary_dependency_failure_is_sanitized(mode: str) -> None:
    if mode == "CLOSED":
        return
    events = _Events()
    assert _run(
        _configuration(mode),
        events,
        authorization_verifier=lambda **_: (_ for _ in ()).throw(RuntimeError("sensitive-detail")),
    ) == (70, _UNEXPECTED_JSON)
    assert events.values == []


@pytest.mark.parametrize("mode", tuple(_MODE_GATES))
def test_result_never_contains_context_or_exception_detail(mode: str) -> None:
    events = _Events()
    result = _run(
        _configuration(mode),
        events,
        authorization_verifier=(lambda **_: False) if mode != "CLOSED" else _dependencies(events)["authorization_verifier"],
    )
    rendered = result[1]
    for forbidden in (
        "opaque-test-credential", "owner-authorization-v1", "checkpoint-v1", _COMMIT,
        "2026-07-22", "/etc/ai-crypto-signal-agent", "detail", "RuntimeError",
    ):
        assert forbidden not in rendered


def test_invalid_mode_fails_closed_without_any_dependency() -> None:
    events = _Events()
    invalid = replace(_configuration("CLOSED"), activation_mode="PRODUCTION")
    assert _run(invalid, events) == (1, _AUTH_FAILURE_JSON)
    assert events.values == []


def test_controlled_failure_marker_is_a_domain_contract_not_dynamic_output() -> None:
    assert issubclass(ActivationModeValidationControlledFailureV1, Exception)
    events = _Events()
    assert _run(
        _configuration("CREDENTIAL_VALIDATION"),
        events,
        credential_locator=lambda: (_ for _ in ()).throw(ActivationModeValidationControlledFailureV1()),
    ) == (1, _FAILURE["CREDENTIAL_VALIDATION"])


def test_source_contract_forbids_real_effect_surfaces() -> None:
    import engine.phase_12_activation_mode_validation_coordinator_v1 as module

    source = inspect.getsource(module)
    for forbidden in (
        "import socket", "import requests", "import httpx", "import subprocess",
        "import logging", "systemctl", "os.environ", "telegram.ext", "run_polling",
    ):
        assert forbidden not in source
    assert "read_systemd_telegram_credential" not in source
    assert "open(" not in source
