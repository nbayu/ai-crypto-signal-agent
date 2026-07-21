"""RED contract for an isolated host-global signal runtime adapter."""
from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from engine.phase_12_isolated_host_global_signal_runtime_adapter_contract_v1 import (
    IsolatedHostGlobalSignalDispatchRequestV1,
    IsolatedHostGlobalSignalDispatchResultV1,
    IsolatedHostGlobalSignalModuleAdapterV1,
    IsolatedHostGlobalSignalPreviousHandlerV1,
    IsolatedHostGlobalSignalRegistrationRequestV1,
    IsolatedHostGlobalSignalRegistrationResultV1,
    IsolatedHostGlobalSignalRegistrationStateV1,
    IsolatedHostGlobalSignalRestorationRequestV1,
    IsolatedHostGlobalSignalRestorationResultV1,
    IsolatedHostGlobalSignalRollbackResultV1,
    IsolatedHostGlobalSignalRuntimeAuditEvidenceV1,
    IsolatedHostGlobalSignalRuntimeFailureV1,
    IsolatedHostGlobalSignalRuntimePolicyV1,
    IsolatedSystemdRuntimeLifecycleEvaluationV1,
    IsolatedSystemdRuntimeLifecycleStateV1,
    IsolatedSystemdRuntimeLifecycleTransitionV1,
    build_isolated_host_global_signal_runtime_audit_evidence_v1,
    dispatch_isolated_host_global_signal_v1,
    evaluate_isolated_systemd_runtime_shutdown_v1,
    evaluate_isolated_systemd_runtime_startup_v1,
    register_isolated_host_global_signal_handlers_v1,
    restore_isolated_host_global_signal_handlers_v1,
    rollback_partial_isolated_signal_registration_v1,
)


_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY",
    "HOST_GLOBAL_ADAPTER_IMPLEMENTATION_NOT_AUTHORIZED",
    "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_IMPLEMENTATION_NOT_AUTHORIZED",
    "SYSTEMD_LIFECYCLE_EVALUATOR_NOT_AUTHORIZED", "ISOLATED_TEST_MODE_REQUIRED",
    "MONKEYPATCHED_SIGNAL_MODULE_REQUIRED", "ISOLATED_SIGNAL_ADAPTER_REQUIRED",
    "HOST_PROCESS_SIGNAL_MODULE_NOT_AUTHORIZED",
    "DIRECT_HOST_GLOBAL_REGISTRATION_NOT_AUTHORIZED",
    "CALLER_SUPPLIED_THREAD_CLASSIFICATION_REQUIRED", "MAIN_THREAD_CLASSIFICATION_REQUIRED",
    "SIGNAL_SET_MISMATCH", "DUPLICATE_SIGNAL_REGISTRATION",
    "UNSUPPORTED_SIGNAL_REGISTRATION", "SIGNAL_REGISTRATION_ORDER_INVALID",
    "CONFIGURATION_VALIDATION_REQUIRED", "REGISTRATION_AFTER_PASSIVE_READINESS_NOT_ALLOWED",
    "PREVIOUS_HANDLER_CAPTURE_REQUIRED", "RAW_HANDLER_REPRESENTATION_NOT_ALLOWED",
    "HANDLER_MEMORY_ADDRESS_EXPOSURE_NOT_ALLOWED", "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED",
    "PARTIAL_REGISTRATION_ROLLBACK_FAILED", "HANDLER_RESTORATION_REQUIRED",
    "HANDLER_RESTORATION_ORDER_INVALID", "HANDLER_RESTORATION_NOT_IDEMPOTENT",
    "HANDLER_RESTORATION_FAILED", "INVALID_LIFECYCLE_TRANSITION",
    "RELOAD_NOT_AUTHORIZED", "UNKNOWN_HOST_GLOBAL_SIGNAL",
    "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED", "PROCESS_TERMINATION_NOT_AUTHORIZED",
    "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED", "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED",
    "ENVIRONMENT_READ_NOT_AUTHORIZED", "FILESYSTEM_READ_NOT_AUTHORIZED",
    "FILESYSTEM_WRITE_NOT_AUTHORIZED", "CREDENTIAL_ACCESS_NOT_AUTHORIZED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "SYSTEMD_ACCESS_NOT_AUTHORIZED",
    "SERVICE_EXECUTION_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED",
    "TELEGRAM_START_NOT_AUTHORIZED", "DATABASE_MUTATION_NOT_AUTHORIZED",
    "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "SUBPROCESS_NOT_AUTHORIZED", "THREAD_CREATION_NOT_AUTHORIZED",
    "EVENT_LOOP_START_NOT_AUTHORIZED", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_MATERIAL_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


class _FakeSignalAdapter:
    """In-memory fake; it never touches a host signal module."""

    def __init__(self, fail_on: str | None = None) -> None:
        self.handlers = {"SIGTERM": "DEFAULT", "SIGINT": "IGNORE"}
        self.calls: list[tuple[str, str]] = []
        self.fail_on = fail_on

    def get_handler(self, signal_name: str) -> str:
        self.calls.append(("get", signal_name))
        return self.handlers[signal_name]

    def set_handler(self, signal_name: str, handler: object) -> None:
        self.calls.append(("set", signal_name))
        if signal_name == self.fail_on:
            raise ValueError("isolated registration failure")
        self.handlers[signal_name] = "INSTALLED"

    def restore_handler(self, signal_name: str, previous_handler: object) -> None:
        self.calls.append(("restore", signal_name))
        self.handlers[signal_name] = previous_handler


def _policy(**overrides: object) -> IsolatedHostGlobalSignalRuntimePolicyV1:
    values = dict(
        policy_id="isolated-host-global-policy-v1", policy_version="V1",
        host_global_signal_adapter_implementation_authorized=True,
        main_thread_signal_registration_implementation_authorized=True,
        handler_restoration_implementation_authorized=True,
        systemd_runtime_lifecycle_evaluator_implementation_authorized=True,
        isolated_test_mode_required=True, monkeypatched_signal_module_required=True,
        caller_supplied_thread_classification_required=True, handler_restoration_required=True,
        partial_registration_rollback_required=True, direct_host_global_registration_authorized=False,
        production_service_execution_authorized=False, production_cli_execution_authorized=False,
        production_runtime_execution_authorized=False, process_exit_execution_authorized=False,
        process_termination_authorized=False, process_signal_transmission_authorized=False,
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
        publication_authorized=False, fail_closed=True,
    )
    return IsolatedHostGlobalSignalRuntimePolicyV1(**(values | overrides))


def _adapter(fake: _FakeSignalAdapter | None = None, **overrides: object) -> IsolatedHostGlobalSignalModuleAdapterV1:
    fake = fake or _FakeSignalAdapter()
    values = dict(
        adapter_id="isolated-host-adapter-v1", isolated_test_adapter=True,
        monkeypatched_signal_module=True, host_process_signal_module=False,
        direct_host_registration_allowed=False, get_handler=fake.get_handler,
        set_handler=fake.set_handler, restore_handler=fake.restore_handler,
    )
    return IsolatedHostGlobalSignalModuleAdapterV1(**(values | overrides))


def _request(**overrides: object) -> IsolatedHostGlobalSignalRegistrationRequestV1:
    values = dict(
        registration_id="isolated-host-registration-v1", thread_classification="MAIN_THREAD",
        requested_signals=("SIGTERM", "SIGINT"), configuration_validated=True,
        passive_readiness_entered=False, duplicate_registration_requested=False,
        registration_order=("CAPTURE_SIGTERM", "INSTALL_SIGTERM", "CAPTURE_SIGINT", "INSTALL_SIGINT"),
        handler_identity="isolated-handler-v1", restoration_required=True,
    )
    return IsolatedHostGlobalSignalRegistrationRequestV1(**(values | overrides))


def _registration_state(**overrides: object) -> IsolatedHostGlobalSignalRegistrationStateV1:
    values = dict(
        lifecycle_id="isolated-runtime-v1", state_code="CONFIGURATION_VALIDATED",
        configuration_validated=True, passive_ready=False, registration_started=False,
        registration_complete=False, sigterm_registered=False, sigint_registered=False,
        shutdown_requested=False, graceful_shutdown_complete=False,
        handlers_restored=False, activation_gate_open=False, credential_gate_open=False,
        network_gate_open=False, workload_gate_open=False,
    )
    return IsolatedHostGlobalSignalRegistrationStateV1(**(values | overrides))


def _dispatch(signal_classification: str = "SIGTERM", **overrides: object) -> IsolatedHostGlobalSignalDispatchRequestV1:
    values = dict(dispatch_id="isolated-host-dispatch-v1", signal_classification=signal_classification)
    values.update(overrides)
    return IsolatedHostGlobalSignalDispatchRequestV1(**values)


def _restoration_request(**overrides: object) -> IsolatedHostGlobalSignalRestorationRequestV1:
    values = dict(restoration_id="isolated-host-restoration-v1", restoration_order=("SIGINT", "SIGTERM"),
                  restoration_required=True)
    values.update(overrides)
    return IsolatedHostGlobalSignalRestorationRequestV1(**values)


def _assert_closed(record: object) -> None:
    for name in (
        "activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open",
        "direct_host_global_registration_authorized", "production_service_execution_authorized",
        "production_cli_execution_authorized", "production_runtime_execution_authorized",
        "process_exit_execution_authorized", "process_termination_authorized",
        "process_signal_transmission_authorized", "credential_access_authorized",
        "credential_loading_authorized", "credential_validation_authorized", "systemd_access_authorized",
        "network_authorized", "provider_transmission_authorized", "scanner_execution_authorized",
        "worker_start_authorized", "scheduler_start_authorized", "telegram_start_authorized",
        "database_mutation_authorized", "artifact_publication_authorized", "trading_authorized",
        "subprocess_authorized", "thread_creation_authorized", "event_loop_start_authorized",
        "runtime_activation_authorized", "publication_authorized",
    ):
        assert getattr(record, name) is False
    assert record.fail_closed is True


def _assert_ordered(failure_codes: tuple[str, ...]) -> None:
    assert tuple(sorted(failure_codes, key=_FAILURES.index)) == failure_codes


def test_public_records_are_immutable_slotted_and_import_is_passive() -> None:
    records = (_policy(), _adapter(), _request(), _registration_state(), _dispatch(), _restoration_request())
    for record in records:
        _frozen(record)
    for record_type in (
        IsolatedHostGlobalSignalPreviousHandlerV1, IsolatedHostGlobalSignalRegistrationResultV1,
        IsolatedHostGlobalSignalDispatchResultV1, IsolatedHostGlobalSignalRestorationResultV1,
        IsolatedHostGlobalSignalRollbackResultV1, IsolatedSystemdRuntimeLifecycleStateV1,
        IsolatedSystemdRuntimeLifecycleTransitionV1, IsolatedSystemdRuntimeLifecycleEvaluationV1,
        IsolatedHostGlobalSignalRuntimeFailureV1, IsolatedHostGlobalSignalRuntimeAuditEvidenceV1,
    ):
        assert hasattr(record_type, "__dataclass_fields__")


def test_main_thread_registration_captures_redacted_previous_handlers_in_order() -> None:
    fake = _FakeSignalAdapter()
    result = register_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=_adapter(fake), request=_request(), state=_registration_state(),
    )
    _frozen(result)
    assert result.registered is True
    assert result.failure_codes == ()
    assert result.current_state.state_code == "SIGNAL_REGISTRATION_COMPLETE"
    assert tuple(item.signal_name for item in result.previous_handlers) == ("SIGTERM", "SIGINT")
    assert tuple(item.classification for item in result.previous_handlers) == ("DEFAULT_HANDLER", "IGNORE_HANDLER")
    assert tuple(item.restoration_order for item in result.previous_handlers) == (2, 1)
    assert fake.calls == [("get", "SIGTERM"), ("set", "SIGTERM"), ("get", "SIGINT"), ("set", "SIGINT")]
    assert all("0x" not in repr(item) for item in result.previous_handlers)
    _assert_closed(result)


@pytest.mark.parametrize(
    ("request", "adapter", "failure_code"),
    (
        (_request(thread_classification="WORKER_THREAD"), _adapter(), "MAIN_THREAD_CLASSIFICATION_REQUIRED"),
        (_request(thread_classification=""), _adapter(), "CALLER_SUPPLIED_THREAD_CLASSIFICATION_REQUIRED"),
        (_request(requested_signals=("SIGTERM",)), _adapter(), "SIGNAL_SET_MISMATCH"),
        (_request(requested_signals=("SIGTERM", "SIGHUP")), _adapter(), "UNSUPPORTED_SIGNAL_REGISTRATION"),
        (_request(duplicate_registration_requested=True), _adapter(), "DUPLICATE_SIGNAL_REGISTRATION"),
        (_request(configuration_validated=False), _adapter(), "CONFIGURATION_VALIDATION_REQUIRED"),
        (_request(passive_readiness_entered=True), _adapter(), "REGISTRATION_AFTER_PASSIVE_READINESS_NOT_ALLOWED"),
        (_request(registration_order=("INSTALL_SIGTERM",)), _adapter(), "SIGNAL_REGISTRATION_ORDER_INVALID"),
        (_request(), _adapter(host_process_signal_module=True), "HOST_PROCESS_SIGNAL_MODULE_NOT_AUTHORIZED"),
        (_request(), _adapter(monkeypatched_signal_module=False), "MONKEYPATCHED_SIGNAL_MODULE_REQUIRED"),
        (_request(), _adapter(direct_host_registration_allowed=True), "DIRECT_HOST_GLOBAL_REGISTRATION_NOT_AUTHORIZED"),
    ),
)
def test_registration_rejections_are_fail_closed(
    request: IsolatedHostGlobalSignalRegistrationRequestV1,
    adapter: IsolatedHostGlobalSignalModuleAdapterV1,
    failure_code: str,
) -> None:
    result = register_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=adapter, request=request, state=_registration_state(),
    )
    assert result.registered is False
    assert failure_code in result.failure_codes
    _assert_ordered(result.failure_codes)
    _assert_closed(result)


def test_partial_sigint_registration_failure_rolls_back_sigterm_deterministically() -> None:
    fake = _FakeSignalAdapter(fail_on="SIGINT")
    result = register_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=_adapter(fake), request=_request(), state=_registration_state(),
    )
    assert result.registered is False
    assert result.current_state.state_code == "SIGNAL_REGISTRATION_PARTIAL"
    assert "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED" in result.failure_codes
    rollback = rollback_partial_isolated_signal_registration_v1(
        policy=_policy(), adapter=_adapter(fake), rollback_id="isolated-host-rollback-v1",
        previous_handlers=result.previous_handlers, state=result.current_state,
    )
    _frozen(rollback)
    assert rollback.rolled_back is True
    assert rollback.current_state.state_code == "ROLLBACK_COMPLETE"
    assert rollback.failure_codes == ()
    assert fake.calls[-1] == ("restore", "SIGTERM")
    _assert_closed(rollback)


def test_restoration_is_reverse_order_and_idempotent() -> None:
    fake = _FakeSignalAdapter()
    registered = register_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=_adapter(fake), request=_request(), state=_registration_state(),
    )
    restored = restore_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=_adapter(fake), request=_restoration_request(),
        previous_handlers=registered.previous_handlers, state=registered.current_state,
    )
    _frozen(restored)
    assert restored.restored is True
    assert restored.current_state.state_code == "HANDLER_RESTORATION_COMPLETE"
    assert fake.calls[-2:] == [("restore", "SIGINT"), ("restore", "SIGTERM")]
    repeated = restore_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=_adapter(fake), request=_restoration_request(),
        previous_handlers=registered.previous_handlers, state=restored.current_state,
    )
    assert repeated.restored is True
    assert repeated.idempotent is True
    assert repeated.failure_codes == ()
    _assert_closed(restored)
    _assert_closed(repeated)


@pytest.mark.parametrize(
    ("state", "signal_name", "expected_state", "classification"),
    (
        (_registration_state(state_code="PASSIVE_READY", passive_ready=True), "SIGTERM", "SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        (_registration_state(state_code="PASSIVE_READY", passive_ready=True), "SIGINT", "SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        (_registration_state(state_code="SHUTDOWN_REQUESTED", shutdown_requested=True), "SIGTERM", "SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        (_registration_state(state_code="GRACEFUL_SHUTDOWN_COMPLETE", graceful_shutdown_complete=True), "SIGINT", "GRACEFUL_SHUTDOWN_COMPLETE", "GRACEFUL_SHUTDOWN_COMPLETE"),
        (_registration_state(state_code="PASSIVE_READY", passive_ready=True), "SIGHUP", "PASSIVE_READY", "RELOAD_NOT_AUTHORIZED"),
        (_registration_state(state_code="PASSIVE_READY", passive_ready=True), "UNKNOWN", "PASSIVE_READY", "UNKNOWN_HOST_GLOBAL_SIGNAL"),
    ),
)
def test_isolated_dispatch_is_deterministic_and_never_exits(
    state: IsolatedHostGlobalSignalRegistrationStateV1, signal_name: str,
    expected_state: str, classification: str,
) -> None:
    result = dispatch_isolated_host_global_signal_v1(
        policy=_policy(), request=_dispatch(signal_name), state=state,
    )
    _frozen(result)
    assert result.current_state.state_code == expected_state
    assert result.dispatch_classification == classification
    _assert_closed(result)


def test_startup_and_shutdown_lifecycle_evaluators_are_pure_test_metadata() -> None:
    fake = _FakeSignalAdapter()
    registered = register_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=_adapter(fake), request=_request(), state=_registration_state(),
    )
    startup = evaluate_isolated_systemd_runtime_startup_v1(
        policy=_policy(), adapter=_adapter(fake), thread_classification="MAIN_THREAD",
        registration_state=registered.current_state, explicit_cli_validated=True,
        configuration_validated=True, passive_readiness_requested=True,
    )
    _frozen(startup)
    assert startup.ready is True
    assert startup.evaluation_classification == "ISOLATED_SYSTEMD_RUNTIME_PASSIVE_READY_FOR_TEST_ONLY"
    assert startup.current_state.state_code == "PASSIVE_READY"
    dispatch = dispatch_isolated_host_global_signal_v1(
        policy=_policy(), request=_dispatch("SIGTERM"), state=startup.current_state,
    )
    restored = restore_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=_adapter(fake), request=_restoration_request(),
        previous_handlers=registered.previous_handlers, state=dispatch.current_state,
    )
    shutdown = evaluate_isolated_systemd_runtime_shutdown_v1(
        policy=_policy(), dispatch_result=dispatch, restoration_result=restored,
        deterministic_exit_classification="GRACEFUL_SIGTERM_SHUTDOWN_EXIT",
    )
    _frozen(shutdown)
    assert shutdown.ready is True
    assert shutdown.evaluation_classification == "ISOLATED_SYSTEMD_RUNTIME_GRACEFUL_SHUTDOWN_COMPLETE_FOR_TEST_ONLY"
    assert shutdown.current_state.state_code == "GRACEFUL_SHUTDOWN_COMPLETE"
    _assert_closed(startup)
    _assert_closed(shutdown)


@pytest.mark.parametrize(
    ("policy", "failure_code"),
    (
        (_policy(policy_id=""), "POLICY_ID_EMPTY"),
        (_policy(policy_version=""), "POLICY_VERSION_EMPTY"),
        (_policy(host_global_signal_adapter_implementation_authorized=False), "HOST_GLOBAL_ADAPTER_IMPLEMENTATION_NOT_AUTHORIZED"),
        (_policy(main_thread_signal_registration_implementation_authorized=False), "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED"),
        (_policy(handler_restoration_implementation_authorized=False), "HANDLER_RESTORATION_IMPLEMENTATION_NOT_AUTHORIZED"),
        (_policy(systemd_runtime_lifecycle_evaluator_implementation_authorized=False), "SYSTEMD_LIFECYCLE_EVALUATOR_NOT_AUTHORIZED"),
        (_policy(isolated_test_mode_required=False), "ISOLATED_TEST_MODE_REQUIRED"),
        (_policy(process_exit_execution_authorized=True), "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
        (_policy(process_termination_authorized=True), "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        (_policy(systemd_access_authorized=True), "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        (_policy(network_authorized=True), "NETWORK_NOT_AUTHORIZED"),
        (_policy(activation_gate_open=True), "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
    ),
)
def test_policy_failures_remain_blocked_and_deterministically_ordered(
    policy: IsolatedHostGlobalSignalRuntimePolicyV1, failure_code: str,
) -> None:
    result = register_isolated_host_global_signal_handlers_v1(
        policy=policy, adapter=_adapter(), request=_request(), state=_registration_state(),
    )
    assert result.registered is False
    assert failure_code in result.failure_codes
    _assert_ordered(result.failure_codes)
    _assert_closed(result)


def test_audit_evidence_is_redacted_immutable_and_never_grants_authority() -> None:
    fake = _FakeSignalAdapter()
    registration = register_isolated_host_global_signal_handlers_v1(
        policy=_policy(), adapter=_adapter(fake), request=_request(), state=_registration_state(),
    )
    evidence = build_isolated_host_global_signal_runtime_audit_evidence_v1(
        evidence_id="isolated-host-audit-v1", policy=_policy(), adapter=_adapter(fake),
        registration_result=registration, dispatch_result=None, restoration_result=None,
        rollback_result=None, lifecycle_evaluation=None,
    )
    _frozen(evidence)
    assert evidence.registration_id == "isolated-host-registration-v1"
    assert evidence.adapter_id == "isolated-host-adapter-v1"
    assert evidence.failure_codes == ()
    assert "0x" not in repr(evidence)
    _assert_closed(evidence)
