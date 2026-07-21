"""RED contract for a dependency-injected, non-executing production signal boundary."""
from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from engine.phase_12_non_executing_production_host_signal_boundary_contract_v1 import (
    ProductionGracefulShutdownStateV1,
    ProductionGracefulShutdownTransitionV1,
    ProductionHostSignalAdapterV1,
    ProductionHostSignalBoundaryAuditEvidenceV1,
    ProductionHostSignalBoundaryFailureV1,
    ProductionHostSignalBoundaryPolicyV1,
    ProductionHostSignalDispatchRequestV1,
    ProductionHostSignalDispatchResultV1,
    ProductionHostSignalHandlerRequestV1,
    ProductionHostSignalHandlerResultV1,
    ProductionHostSignalPreviousHandlerV1,
    ProductionHostSignalRegistrationRequestV1,
    ProductionHostSignalRegistrationResultV1,
    ProductionHostSignalRegistrationStateV1,
    ProductionHostSignalRestorationRequestV1,
    ProductionHostSignalRestorationResultV1,
    ProductionHostSignalRollbackResultV1,
    build_production_host_signal_boundary_audit_evidence_v1,
    dispatch_production_host_signal_v1,
    install_production_host_signal_handlers_v1,
    register_production_host_signal_handlers_v1,
    request_production_graceful_shutdown_v1,
    restore_production_host_signal_handlers_v1,
    rollback_partial_production_host_signal_registration_v1,
)


_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "HOST_SIGNAL_ADAPTER_IMPLEMENTATION_NOT_AUTHORIZED",
    "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED", "HANDLER_INSTALLATION_IMPLEMENTATION_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_IMPLEMENTATION_NOT_AUTHORIZED", "SIGNAL_DISPATCH_IMPLEMENTATION_NOT_AUTHORIZED",
    "GRACEFUL_SHUTDOWN_STATE_MACHINE_NOT_AUTHORIZED", "NON_EXECUTING_DEPENDENCY_INJECTED_MODE_REQUIRED",
    "PRODUCTION_HOST_SIGNAL_ADAPTER_REQUIRED", "STANDARD_LIBRARY_SIGNAL_MODULE_NOT_AUTHORIZED",
    "HOST_PROCESS_SIGNAL_MODULE_NOT_AUTHORIZED", "REAL_HOST_HANDLER_INSTALLATION_NOT_AUTHORIZED",
    "REAL_HOST_HANDLER_RESTORATION_NOT_AUTHORIZED", "ACTUAL_SIGNAL_TRANSMISSION_NOT_AUTHORIZED",
    "CALLER_SUPPLIED_THREAD_CLASSIFICATION_REQUIRED", "MAIN_THREAD_CLASSIFICATION_REQUIRED",
    "CONFIGURATION_VALIDATION_REQUIRED", "SIGNAL_SET_MISMATCH", "DUPLICATE_SIGNAL_REGISTRATION",
    "UNSUPPORTED_SIGNAL_REGISTRATION", "PREVIOUS_HANDLER_CAPTURE_REQUIRED", "PREVIOUS_HANDLER_REDACTION_REQUIRED",
    "RAW_HANDLER_REPRESENTATION_NOT_ALLOWED", "HANDLER_MEMORY_ADDRESS_EXPOSURE_NOT_ALLOWED",
    "HANDLER_INSTALLATION_ORDER_INVALID", "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED",
    "PARTIAL_REGISTRATION_ROLLBACK_FAILED", "HANDLER_RESTORATION_REQUIRED",
    "HANDLER_RESTORATION_ORDER_INVALID", "HANDLER_RESTORATION_NOT_IDEMPOTENT",
    "HANDLER_RESTORATION_FAILED", "INVALID_GRACEFUL_SHUTDOWN_TRANSITION",
    "RELOAD_NOT_AUTHORIZED", "UNKNOWN_HOST_GLOBAL_SIGNAL", "PRODUCTION_PROCESS_EXIT_IMPLEMENTATION_NOT_AUTHORIZED",
    "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED", "PROCESS_TERMINATION_NOT_AUTHORIZED",
    "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED",
    "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED",
    "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED", "ENVIRONMENT_READ_NOT_AUTHORIZED",
    "FILESYSTEM_READ_NOT_AUTHORIZED", "FILESYSTEM_WRITE_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "SYSTEMD_ACCESS_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "SCANNER_EXECUTION_NOT_AUTHORIZED", "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED",
    "TELEGRAM_START_NOT_AUTHORIZED", "DATABASE_MUTATION_NOT_AUTHORIZED",
    "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED", "SUBPROCESS_NOT_AUTHORIZED",
    "THREAD_CREATION_NOT_AUTHORIZED", "EVENT_LOOP_START_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "PUBLICATION_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED",
    "WORKLOAD_GATE_MUST_REMAIN_CLOSED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "PROVIDER_MATERIAL_EXPOSURE_DETECTED", "PROCESS_METADATA_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen
    assert "__dict__" not in type(value).__slots__


class _FakeAdapter:
    def __init__(self, fail_on: str | None = None) -> None:
        self.tokens = {"SIGTERM": "DEFAULT", "SIGINT": "IGNORE"}
        self.calls: list[tuple[str, str]] = []
        self.fail_on = fail_on

    def capture_handler(self, signal_name: str) -> str:
        self.calls.append(("capture", signal_name))
        return self.tokens[signal_name]

    def install_handler(self, signal_name: str, handler_token: str) -> None:
        self.calls.append(("install", signal_name))
        if signal_name == self.fail_on:
            raise ValueError("synthetic adapter failure")
        self.tokens[signal_name] = handler_token

    def restore_handler(self, signal_name: str, previous_token: str) -> None:
        self.calls.append(("restore", signal_name))
        self.tokens[signal_name] = previous_token


def _policy(**overrides: object) -> ProductionHostSignalBoundaryPolicyV1:
    values = dict(
        policy_id="production-boundary-policy-v1", policy_version="V1",
        production_host_global_signal_adapter_implementation_authorized=True,
        production_main_thread_registration_implementation_authorized=True,
        production_handler_installation_implementation_authorized=True,
        production_handler_restoration_implementation_authorized=True,
        production_signal_dispatch_implementation_authorized=True,
        production_graceful_shutdown_state_machine_implementation_authorized=True,
        non_executing_dependency_injected_boundary_only=True,
        caller_supplied_main_thread_classification_required=True, handler_restoration_required=True,
        partial_registration_rollback_required=True, direct_standard_library_signal_registration_authorized=False,
        real_host_handler_installation_authorized=False, real_host_handler_restoration_authorized=False,
        actual_signal_transmission_authorized=False, production_process_exit_implementation_authorized=False,
        process_exit_execution_authorized=False, process_termination_authorized=False,
        process_signal_transmission_authorized=False, production_cli_execution_authorized=False,
        production_service_execution_authorized=False, production_runtime_execution_authorized=False,
        implicit_sys_argv_access_authorized=False, environment_read_authorized=False,
        filesystem_read_authorized=False, filesystem_write_authorized=False,
        credential_access_authorized=False, credential_loading_authorized=False,
        credential_validation_authorized=False, systemd_access_authorized=False,
        network_authorized=False, provider_transmission_authorized=False,
        scanner_execution_authorized=False, worker_start_authorized=False,
        scheduler_start_authorized=False, telegram_start_authorized=False,
        database_mutation_authorized=False, artifact_publication_authorized=False,
        trading_authorized=False, subprocess_authorized=False, thread_creation_authorized=False,
        event_loop_start_authorized=False, runtime_activation_authorized=False,
        publication_authorized=False, activation_gate_open=False, credential_gate_open=False,
        network_gate_open=False, workload_gate_open=False, fail_closed=True,
    )
    return ProductionHostSignalBoundaryPolicyV1(**(values | overrides))


def _adapter(fake: _FakeAdapter | None = None, **overrides: object) -> ProductionHostSignalAdapterV1:
    fake = fake or _FakeAdapter()
    values = dict(
        adapter_id="production-boundary-adapter-v1", dependency_injected=True,
        non_executing_boundary=True, standard_library_signal_module=False,
        host_process_signal_module=False, real_host_handler_mutation_allowed=False,
        actual_signal_transmission_allowed=False, capture_handler=fake.capture_handler,
        install_handler=fake.install_handler, restore_handler=fake.restore_handler,
    )
    return ProductionHostSignalAdapterV1(**(values | overrides))


def _registration(**overrides: object) -> ProductionHostSignalRegistrationRequestV1:
    values = dict(
        registration_id="production-boundary-registration-v1", thread_classification="MAIN_THREAD",
        signal_names=("SIGTERM", "SIGINT"), configuration_validated=True,
        passive_readiness_entered=False, duplicate_registration_requested=False,
        registration_order=("CAPTURE_SIGTERM", "PREPARE_SIGTERM", "CAPTURE_SIGINT", "PREPARE_SIGINT"),
        sigterm_handler_token="handler-term-v1", sigint_handler_token="handler-int-v1",
    )
    return ProductionHostSignalRegistrationRequestV1(**(values | overrides))


def _state(**overrides: object) -> ProductionHostSignalRegistrationStateV1:
    values = dict(
        state_id="production-boundary-state-v1", state_code="CONFIGURATION_VALIDATED",
        configuration_validated=True, registration_complete=False, handlers_prepared=False,
        passive_ready=False, shutdown_requested=False, graceful_shutdown_complete=False,
        handlers_restored=False, activation_gate_open=False, credential_gate_open=False,
        network_gate_open=False, workload_gate_open=False,
    )
    return ProductionHostSignalRegistrationStateV1(**(values | overrides))


def _handler_request(**overrides: object) -> ProductionHostSignalHandlerRequestV1:
    values = dict(handler_id="production-boundary-handler-v1", handler_tokens=("handler-term-v1", "handler-int-v1"))
    values.update(overrides)
    return ProductionHostSignalHandlerRequestV1(**values)


def _dispatch(signal_name: str = "SIGTERM") -> ProductionHostSignalDispatchRequestV1:
    return ProductionHostSignalDispatchRequestV1(dispatch_id="production-boundary-dispatch-v1", signal_classification=signal_name)


def _restore_request(**overrides: object) -> ProductionHostSignalRestorationRequestV1:
    values = dict(restoration_id="production-boundary-restoration-v1", restoration_order=("SIGINT", "SIGTERM"), restoration_required=True)
    values.update(overrides)
    return ProductionHostSignalRestorationRequestV1(**values)


def _closed(record: object) -> None:
    for name in (
        "activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open",
        "direct_standard_library_signal_registration_authorized", "real_host_handler_installation_authorized",
        "real_host_handler_restoration_authorized", "actual_signal_transmission_authorized",
        "process_exit_execution_authorized", "process_termination_authorized",
        "process_signal_transmission_authorized", "production_service_execution_authorized",
        "production_runtime_execution_authorized", "credential_loading_authorized",
        "systemd_access_authorized", "network_authorized", "runtime_activation_authorized",
        "publication_authorized",
    ):
        assert getattr(record, name) is False
    assert record.fail_closed is True


def test_public_records_are_frozen_slotted_and_non_executing() -> None:
    for record in (_policy(), _adapter(), _registration(), _state(), _handler_request(), _dispatch(), _restore_request()):
        _frozen(record)
    for record_type in (
        ProductionHostSignalPreviousHandlerV1, ProductionHostSignalRegistrationResultV1,
        ProductionHostSignalHandlerResultV1, ProductionHostSignalDispatchResultV1,
        ProductionHostSignalRestorationResultV1, ProductionHostSignalRollbackResultV1,
        ProductionGracefulShutdownStateV1, ProductionGracefulShutdownTransitionV1,
        ProductionHostSignalBoundaryFailureV1, ProductionHostSignalBoundaryAuditEvidenceV1,
    ):
        assert hasattr(record_type, "__dataclass_fields__")


def test_injected_adapter_registration_and_installation_preserve_redaction() -> None:
    fake = _FakeAdapter()
    registration = register_production_host_signal_handlers_v1(policy=_policy(), adapter=_adapter(fake), registration_request=_registration(), state=_state())
    _frozen(registration)
    assert registration.ready is True
    assert tuple(item.signal_name for item in registration.previous_handlers) == ("SIGTERM", "SIGINT")
    assert tuple(item.classification for item in registration.previous_handlers) == ("DEFAULT_HANDLER", "IGNORE_HANDLER")
    assert all("0x" not in repr(item) for item in registration.previous_handlers)
    installed = install_production_host_signal_handlers_v1(policy=_policy(), adapter=_adapter(fake), handler_request=_handler_request(), registration_result=registration)
    _frozen(installed)
    assert installed.installed is True
    assert fake.calls == [("capture", "SIGTERM"), ("capture", "SIGINT"), ("install", "SIGTERM"), ("install", "SIGINT")]
    _closed(installed)


@pytest.mark.parametrize(
    ("registration_case", "adapter_case", "failure_code"),
    (
        (_registration(thread_classification="WORKER_THREAD"), _adapter(), "MAIN_THREAD_CLASSIFICATION_REQUIRED"),
        (_registration(thread_classification=""), _adapter(), "CALLER_SUPPLIED_THREAD_CLASSIFICATION_REQUIRED"),
        (_registration(signal_names=("SIGTERM",)), _adapter(), "SIGNAL_SET_MISMATCH"),
        (_registration(signal_names=("SIGTERM", "SIGHUP")), _adapter(), "UNSUPPORTED_SIGNAL_REGISTRATION"),
        (_registration(duplicate_registration_requested=True), _adapter(), "DUPLICATE_SIGNAL_REGISTRATION"),
        (_registration(configuration_validated=False), _adapter(), "CONFIGURATION_VALIDATION_REQUIRED"),
        (_registration(), _adapter(standard_library_signal_module=True), "STANDARD_LIBRARY_SIGNAL_MODULE_NOT_AUTHORIZED"),
        (_registration(), _adapter(host_process_signal_module=True), "HOST_PROCESS_SIGNAL_MODULE_NOT_AUTHORIZED"),
        (_registration(), _adapter(real_host_handler_mutation_allowed=True), "REAL_HOST_HANDLER_INSTALLATION_NOT_AUTHORIZED"),
    ),
)
def test_registration_failures_are_deterministic_and_fail_closed(
    registration_case: ProductionHostSignalRegistrationRequestV1,
    adapter_case: ProductionHostSignalAdapterV1, failure_code: str,
) -> None:
    result = register_production_host_signal_handlers_v1(policy=_policy(), adapter=adapter_case, registration_request=registration_case, state=_state())
    assert result.ready is False
    assert failure_code in result.failure_codes
    assert tuple(sorted(result.failure_codes, key=_FAILURES.index)) == result.failure_codes
    _closed(result)


def test_partial_installation_rolls_back_and_restoration_is_reverse_order_idempotent() -> None:
    fake = _FakeAdapter(fail_on="SIGINT")
    registration = register_production_host_signal_handlers_v1(policy=_policy(), adapter=_adapter(fake), registration_request=_registration(), state=_state())
    installation = install_production_host_signal_handlers_v1(policy=_policy(), adapter=_adapter(fake), handler_request=_handler_request(), registration_result=registration)
    assert installation.installed is False
    assert "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED" in installation.failure_codes
    rollback = rollback_partial_production_host_signal_registration_v1(policy=_policy(), adapter=_adapter(fake), rollback_id="production-boundary-rollback-v1", previous_handlers=registration.previous_handlers, state=installation.current_state)
    assert rollback.rolled_back is True
    restored = restore_production_host_signal_handlers_v1(policy=_policy(), adapter=_adapter(fake), restoration_request=_restore_request(), previous_handlers=registration.previous_handlers, state=_state(handlers_prepared=True))
    assert restored.restored is True
    assert fake.calls[-2:] == [("restore", "SIGINT"), ("restore", "SIGTERM")]
    repeated = restore_production_host_signal_handlers_v1(policy=_policy(), adapter=_adapter(fake), restoration_request=_restore_request(), previous_handlers=registration.previous_handlers, state=restored.current_state)
    assert repeated.idempotent is True
    _closed(rollback)
    _closed(restored)


@pytest.mark.parametrize(
    ("state", "signal_name", "expected", "classification"),
    (
        (_state(state_code="PASSIVE_READY", passive_ready=True), "SIGTERM", "SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        (_state(state_code="PASSIVE_READY", passive_ready=True), "SIGINT", "SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        (_state(state_code="SHUTDOWN_REQUESTED", shutdown_requested=True), "SIGTERM", "SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        (_state(state_code="GRACEFUL_SHUTDOWN_COMPLETE", graceful_shutdown_complete=True), "SIGINT", "GRACEFUL_SHUTDOWN_COMPLETE", "GRACEFUL_SHUTDOWN_COMPLETE"),
        (_state(state_code="PASSIVE_READY", passive_ready=True), "SIGHUP", "PASSIVE_READY", "RELOAD_NOT_AUTHORIZED"),
        (_state(state_code="PASSIVE_READY", passive_ready=True), "UNKNOWN", "PASSIVE_READY", "UNKNOWN_HOST_GLOBAL_SIGNAL"),
    ),
)
def test_dispatch_and_graceful_shutdown_state_machine_are_non_executing(
    state: ProductionHostSignalRegistrationStateV1, signal_name: str, expected: str, classification: str,
) -> None:
    result = dispatch_production_host_signal_v1(policy=_policy(), dispatch_request=_dispatch(signal_name), state=state)
    assert result.current_state.state_code == expected
    assert result.dispatch_classification == classification
    if signal_name == "SIGTERM" and state.state_code == "PASSIVE_READY":
        transition = request_production_graceful_shutdown_v1(policy=_policy(), shutdown_id="production-boundary-shutdown-v1", state=result.current_state, complete_shutdown=True)
        assert transition.current_state.state_code == "GRACEFUL_SHUTDOWN_COMPLETE"
    _closed(result)


def test_audit_evidence_is_redacted_and_never_grants_live_authority() -> None:
    registration = register_production_host_signal_handlers_v1(policy=_policy(), adapter=_adapter(), registration_request=_registration(), state=_state())
    evidence = build_production_host_signal_boundary_audit_evidence_v1(evidence_id="production-boundary-audit-v1", policy=_policy(), adapter=_adapter(), registration_result=registration, installation_result=None, rollback_result=None, dispatch_result=None, shutdown_transition=None, restoration_result=None)
    _frozen(evidence)
    assert evidence.failure_codes == ()
    assert "0x" not in repr(evidence)
    _closed(evidence)
