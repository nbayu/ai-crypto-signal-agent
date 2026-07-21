"""RED contract for explicit passive CLI parsing and isolated signal adapters."""
from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from engine.phase_12_passive_production_cli_real_signal_adapter_contract_v1 import (
    IsolatedSignalAdapterPolicyV1,
    IsolatedSignalAdapterV1,
    IsolatedSignalDispatchRequestV1,
    IsolatedSignalDispatchResultV1,
    IsolatedSignalRegistrationRequestV1,
    IsolatedSignalRegistrationResultV1,
    PassiveCliSignalAuditEvidenceV1,
    PassiveCliSignalRuntimeStateV1,
    PassiveCliSignalTransitionV1,
    PassiveProductionCliArgumentResultV1,
    PassiveProductionCliExitResultV1,
    PassiveProductionCliFailureV1,
    PassiveProductionCliInvocationV1,
    PassiveProductionCliPolicyV1,
    build_passive_cli_signal_audit_evidence_v1,
    dispatch_isolated_real_signal_v1,
    evaluate_passive_production_cli_v1,
    main,
    parse_explicit_passive_cli_arguments_v1,
    register_isolated_real_signal_handlers_v1,
    request_passive_cli_shutdown_v1,
)


_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "CLI_IMPLEMENTATION_NOT_AUTHORIZED",
    "PASSIVE_TEST_EXECUTION_NOT_AUTHORIZED", "EXPLICIT_ARGV_REQUIRED",
    "IMPLICIT_SYS_ARGV_ACCESS_NOT_AUTHORIZED", "PASSIVE_MODE_REQUIRED", "ACTIVE_MODE_NOT_AUTHORIZED",
    "UNKNOWN_CLI_ARGUMENT", "DUPLICATE_CLI_ARGUMENT", "CLI_ARGUMENT_VALUE_REQUIRED",
    "ACTIVATION_ARGUMENT_NOT_ALLOWED", "CREDENTIAL_ARGUMENT_NOT_ALLOWED",
    "ENVIRONMENT_ARGUMENT_NOT_ALLOWED", "PROVIDER_ARGUMENT_NOT_ALLOWED",
    "NETWORK_ARGUMENT_NOT_ALLOWED", "WORKLOAD_ARGUMENT_NOT_ALLOWED",
    "PUBLICATION_ARGUMENT_NOT_ALLOWED", "TRADING_ARGUMENT_NOT_ALLOWED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "ISOLATED_SIGNAL_ADAPTER_REQUIRED", "HOST_GLOBAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED",
    "SIGNAL_SET_MISMATCH", "UNSUPPORTED_SIGNAL_REGISTRATION", "DUPLICATE_SIGNAL_REGISTRATION",
    "SIGNAL_REGISTRATION_ORDER_INVALID", "PROCESS_TERMINATION_NOT_AUTHORIZED",
    "PROCESS_CONTROL_NOT_AUTHORIZED", "SUBPROCESS_NOT_AUTHORIZED", "THREAD_START_NOT_AUTHORIZED",
    "EVENT_LOOP_START_NOT_AUTHORIZED", "ENVIRONMENT_READ_NOT_AUTHORIZED",
    "FILESYSTEM_READ_NOT_AUTHORIZED", "FILESYSTEM_WRITE_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "SYSTEMD_ACCESS_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED",
    "TELEGRAM_START_NOT_AUTHORIZED", "DATABASE_MUTATION_NOT_AUTHORIZED",
    "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "PUBLICATION_NOT_AUTHORIZED", "INVALID_STATE_TRANSITION", "RELOAD_NOT_AUTHORIZED",
    "UNKNOWN_REAL_SIGNAL", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "PROVIDER_MATERIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _register_metadata(signal_name: str, handler_classification: str) -> tuple[str, str]:
    return (signal_name, handler_classification)


def _restore_metadata(signal_name: str) -> str:
    return signal_name


def _policy(**overrides: object) -> PassiveProductionCliPolicyV1:
    values = dict(
        policy_id="passive-cli-policy-v1", policy_version="V1",
        production_cli_implementation_authorized=True,
        real_signal_registration_implementation_authorized=True,
        production_cli_test_execution_authorized=True,
        isolated_signal_tests_authorized=True, explicit_caller_supplied_argv_required=True,
        implicit_sys_argv_access_authorized=False, passive_only=True, active_mode_supported=False,
        environment_read_authorized=False, filesystem_read_authorized=False,
        filesystem_write_authorized=False, credential_access_authorized=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        systemd_access_authorized=False, network_authorized=False,
        provider_transmission_authorized=False, production_runtime_execution_authorized=False,
        runtime_activation_authorized=False, publication_authorized=False,
        process_termination_authorized=False, process_control_authorized=False,
        subprocess_authorized=False, thread_start_authorized=False,
        event_loop_start_authorized=False, scanner_execution_authorized=False,
        worker_start_authorized=False, scheduler_start_authorized=False,
        telegram_start_authorized=False, database_mutation_authorized=False,
        artifact_publication_authorized=False, trading_authorized=False,
        systemd_unit_file_generation_authorized=False,
        systemd_drop_in_generation_authorized=False, service_unit_installation_authorized=False,
        daemon_reload_authorized=False, service_enablement_authorized=False,
        service_start_restart_authorized=False, fail_closed=True,
    )
    return PassiveProductionCliPolicyV1(**(values | overrides))


def _invocation(**overrides: object) -> PassiveProductionCliInvocationV1:
    values = dict(
        cli_id="passive-production-cli-v1", invocation_id="passive-cli-invocation-v1",
        explicit_argv=("--mode", "passive"), launcher_module="engine.phase_12_passive_runtime_launcher_executable_contract_v1",
        interpreter_path="/opt/ai-crypto-signal-agent/.venv/bin/python",
        service_unit="ai-crypto-signal-agent.service", execution_mode="PASSIVE_TEST_MODE",
        activation_gate_open=False, credential_gate_open=False, network_gate_open=False,
        workload_gate_open=False, invocation_complete=True,
    )
    return PassiveProductionCliInvocationV1(**(values | overrides))


def _adapter_policy(**overrides: object) -> IsolatedSignalAdapterPolicyV1:
    values = dict(
        adapter_policy_id="isolated-adapter-policy-v1", isolated_adapter_required=True,
        host_global_registration_authorized=False, only_sigterm_sigint_allowed=True,
        duplicate_registration_allowed=False, registration_after_configuration_validation_required=True,
        registration_before_passive_readiness_required=True, handler_restoration_required=True,
        process_termination_authorized=False, process_control_authorized=False,
        signal_wait_authorized=False, pause_loop_authorized=False,
        handler_blocking_io_authorized=False, handler_logging_authorized=False,
        handler_credential_access_authorized=False, handler_provider_access_authorized=False,
        handler_network_access_authorized=False, handler_workload_start_authorized=False,
        handler_publication_authorized=False, fail_closed=True,
    )
    return IsolatedSignalAdapterPolicyV1(**(values | overrides))


def _adapter(**overrides: object) -> IsolatedSignalAdapterV1:
    values = dict(
        adapter_id="isolated-adapter-v1", adapter_classification="ISOLATED_MONKEYPATCHED_ADAPTER",
        isolated=True, host_global=False, register_handler=_register_metadata,
        restore_handler=_restore_metadata, adapter_ready=True,
    )
    return IsolatedSignalAdapterV1(**(values | overrides))


def _state(**overrides: object) -> PassiveCliSignalRuntimeStateV1:
    values = dict(
        state_id="passive-cli-state-v1", state_code="CONFIGURATION_VALIDATED",
        configuration_validated=True, passive_ready=False, registration_complete=False,
        shutdown_requested=False, graceful_shutdown_complete=False,
        activation_gate_open=False, credential_gate_open=False, network_gate_open=False,
        workload_gate_open=False,
    )
    return PassiveCliSignalRuntimeStateV1(**(values | overrides))


def _registration(**overrides: object) -> IsolatedSignalRegistrationRequestV1:
    values = dict(
        registration_id="isolated-registration-v1", requested_signals=("SIGTERM", "SIGINT"),
        configuration_validated=True, passive_readiness_pending=True,
        duplicate_registration_requested=False, restoration_policy_defined=True,
    )
    return IsolatedSignalRegistrationRequestV1(**(values | overrides))


def _dispatch(signal_classification: str = "SIGTERM", **overrides: object) -> IsolatedSignalDispatchRequestV1:
    values = {"dispatch_id": "isolated-dispatch-v1", "signal_classification": signal_classification}
    values.update(overrides)
    return IsolatedSignalDispatchRequestV1(**values)


def _assert_closed(record: object) -> None:
    assert record.activation_gate_open is False
    assert record.credential_gate_open is False
    assert record.network_gate_open is False
    assert record.workload_gate_open is False
    for name in (
        "credential_access_authorized", "credential_loading_authorized",
        "credential_validation_authorized", "systemd_access_authorized", "network_authorized",
        "provider_transmission_authorized", "scanner_execution_authorized",
        "worker_start_authorized", "scheduler_start_authorized", "telegram_start_authorized",
        "database_mutation_authorized", "artifact_publication_authorized", "trading_authorized",
        "production_runtime_execution_authorized", "runtime_activation_authorized",
        "publication_authorized", "process_termination_authorized", "subprocess_authorized",
        "thread_start_authorized", "event_loop_start_authorized",
    ):
        assert getattr(record, name) is False
    assert record.fail_closed is True


def test_public_records_are_immutable_slotted_and_side_effect_free() -> None:
    for record in (_policy(), _invocation(), _adapter_policy(), _adapter(), _state(), _registration(), _dispatch()):
        _frozen(record)
    for record_type in (
        PassiveProductionCliArgumentResultV1, PassiveProductionCliExitResultV1,
        PassiveProductionCliFailureV1, IsolatedSignalRegistrationResultV1,
        IsolatedSignalDispatchResultV1, PassiveCliSignalTransitionV1,
        PassiveCliSignalAuditEvidenceV1,
    ):
        assert hasattr(record_type, "__dataclass_fields__")


def test_explicit_passive_argv_parsing_and_cli_evaluation_stay_passive() -> None:
    parsed = parse_explicit_passive_cli_arguments_v1(policy=_policy(), explicit_argv=("--mode", "passive"))
    _frozen(parsed)
    assert parsed.accepted is True
    assert parsed.mode == "PASSIVE"
    assert parsed.failure_codes == ()
    result = evaluate_passive_production_cli_v1(policy=_policy(), invocation=_invocation(), argument_result=parsed)
    _frozen(result)
    assert result.ready is True
    assert result.result_classification == "PASSIVE_PRODUCTION_CLI_READY_IN_ISOLATED_TEST_MODE"
    assert result.current_state.state_code == "PASSIVE_READY"
    _assert_closed(result)


@pytest.mark.parametrize(
    ("argv", "failure_code"),
    (
        ((), "EXPLICIT_ARGV_REQUIRED"),
        (("--mode",), "CLI_ARGUMENT_VALUE_REQUIRED"),
        (("--mode", "active"), "ACTIVE_MODE_NOT_AUTHORIZED"),
        (("--other",), "UNKNOWN_CLI_ARGUMENT"),
        (("--mode", "passive", "--mode", "passive"), "DUPLICATE_CLI_ARGUMENT"),
        (("--activate",), "ACTIVATION_ARGUMENT_NOT_ALLOWED"),
        (("--credential",), "CREDENTIAL_ARGUMENT_NOT_ALLOWED"),
        (("--env-file",), "ENVIRONMENT_ARGUMENT_NOT_ALLOWED"),
        (("--endpoint",), "PROVIDER_ARGUMENT_NOT_ALLOWED"),
        (("--network",), "NETWORK_ARGUMENT_NOT_ALLOWED"),
        (("--scanner",), "WORKLOAD_ARGUMENT_NOT_ALLOWED"),
        (("--publish",), "PUBLICATION_ARGUMENT_NOT_ALLOWED"),
        (("--trade",), "TRADING_ARGUMENT_NOT_ALLOWED"),
    ),
)
def test_explicit_argv_rejections_are_fail_closed_and_deterministic(
    argv: tuple[str, ...], failure_code: str,
) -> None:
    result = parse_explicit_passive_cli_arguments_v1(policy=_policy(), explicit_argv=argv)
    assert result.accepted is False
    assert failure_code in result.failure_codes
    assert tuple(item.failure_code for item in result.failures) == result.failure_codes
    assert tuple(sorted(result.failure_codes, key=_FAILURES.index)) == result.failure_codes
    _assert_closed(result)


@pytest.mark.parametrize(
    ("policy_overrides", "invocation_overrides", "failure_code"),
    (
        ({"policy_id": ""}, {}, "POLICY_ID_EMPTY"),
        ({"policy_version": ""}, {}, "POLICY_VERSION_EMPTY"),
        ({"production_cli_implementation_authorized": False}, {}, "CLI_IMPLEMENTATION_NOT_AUTHORIZED"),
        ({"production_cli_test_execution_authorized": False}, {}, "PASSIVE_TEST_EXECUTION_NOT_AUTHORIZED"),
        ({"implicit_sys_argv_access_authorized": True}, {}, "IMPLICIT_SYS_ARGV_ACCESS_NOT_AUTHORIZED"),
        ({"environment_read_authorized": True}, {}, "ENVIRONMENT_READ_NOT_AUTHORIZED"),
        ({"filesystem_read_authorized": True}, {}, "FILESYSTEM_READ_NOT_AUTHORIZED"),
        ({"filesystem_write_authorized": True}, {}, "FILESYSTEM_WRITE_NOT_AUTHORIZED"),
        ({"credential_access_authorized": True}, {}, "CREDENTIAL_ACCESS_NOT_AUTHORIZED"),
        ({"credential_loading_authorized": True}, {}, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ({"systemd_access_authorized": True}, {}, "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        ({"network_authorized": True}, {}, "NETWORK_NOT_AUTHORIZED"),
        ({"provider_transmission_authorized": True}, {}, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        ({"process_termination_authorized": True}, {}, "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        ({"subprocess_authorized": True}, {}, "SUBPROCESS_NOT_AUTHORIZED"),
        ({"thread_start_authorized": True}, {}, "THREAD_START_NOT_AUTHORIZED"),
        ({"event_loop_start_authorized": True}, {}, "EVENT_LOOP_START_NOT_AUTHORIZED"),
        ({}, {"activation_gate_open": True}, "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
        ({}, {"credential_gate_open": True}, "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
        ({}, {"network_gate_open": True}, "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ({}, {"workload_gate_open": True}, "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
    ),
)
def test_cli_policy_and_gate_rejections_are_fail_closed(
    policy_overrides: dict[str, object], invocation_overrides: dict[str, object], failure_code: str,
) -> None:
    parsed = parse_explicit_passive_cli_arguments_v1(policy=_policy(**policy_overrides), explicit_argv=("--mode", "passive"))
    result = evaluate_passive_production_cli_v1(
        policy=_policy(**policy_overrides), invocation=_invocation(**invocation_overrides), argument_result=parsed,
    )
    assert result.ready is False
    assert failure_code in result.failure_codes
    _assert_closed(result)


def test_isolated_adapter_registers_only_sigterm_and_sigint_after_configuration_validation() -> None:
    result = register_isolated_real_signal_handlers_v1(
        policy=_policy(), adapter_policy=_adapter_policy(), adapter=_adapter(),
        registration_request=_registration(), runtime_state=_state(),
    )
    _frozen(result)
    assert result.registered is True
    assert result.registered_signals == ("SIGTERM", "SIGINT")
    assert result.current_state.state_code == "SIGNAL_HANDLERS_REGISTERED"
    _assert_closed(result)


@pytest.mark.parametrize(
    ("adapter_overrides", "request_overrides", "state_overrides", "failure_code"),
    (
        ({"isolated": False}, {}, {}, "ISOLATED_SIGNAL_ADAPTER_REQUIRED"),
        ({"host_global": True}, {}, {}, "HOST_GLOBAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED"),
        ({}, {"requested_signals": ("SIGTERM",)}, {}, "SIGNAL_SET_MISMATCH"),
        ({}, {"requested_signals": ("SIGTERM", "SIGHUP")}, {}, "UNSUPPORTED_SIGNAL_REGISTRATION"),
        ({}, {"duplicate_registration_requested": True}, {}, "DUPLICATE_SIGNAL_REGISTRATION"),
        ({}, {"configuration_validated": False}, {}, "SIGNAL_REGISTRATION_ORDER_INVALID"),
        ({}, {}, {"shutdown_requested": True}, "SIGNAL_REGISTRATION_ORDER_INVALID"),
    ),
)
def test_isolated_adapter_rejects_global_duplicate_unsupported_and_bad_order(
    adapter_overrides: dict[str, object], request_overrides: dict[str, object], state_overrides: dict[str, object], failure_code: str,
) -> None:
    result = register_isolated_real_signal_handlers_v1(
        policy=_policy(), adapter_policy=_adapter_policy(), adapter=_adapter(**adapter_overrides),
        registration_request=_registration(**request_overrides), runtime_state=_state(**state_overrides),
    )
    assert result.registered is False
    assert failure_code in result.failure_codes
    _assert_closed(result)


def test_isolated_dispatch_and_shutdown_are_deterministic_and_idempotent() -> None:
    ready = PassiveCliSignalRuntimeStateV1(
        state_id="ready-state-v1", state_code="PASSIVE_READY", configuration_validated=True,
        passive_ready=True, registration_complete=True, shutdown_requested=False,
        graceful_shutdown_complete=False, activation_gate_open=False, credential_gate_open=False,
        network_gate_open=False, workload_gate_open=False,
    )
    term = dispatch_isolated_real_signal_v1(policy=_policy(), runtime_state=ready, dispatch_request=_dispatch())
    interrupt = dispatch_isolated_real_signal_v1(policy=_policy(), runtime_state=ready, dispatch_request=_dispatch("SIGINT"))
    assert term.current_state.state_code == "SHUTDOWN_REQUESTED"
    assert interrupt.current_state.state_code == "SHUTDOWN_REQUESTED"
    hup = dispatch_isolated_real_signal_v1(policy=_policy(), runtime_state=ready, dispatch_request=_dispatch("SIGHUP"))
    unknown = dispatch_isolated_real_signal_v1(policy=_policy(), runtime_state=ready, dispatch_request=_dispatch("UNKNOWN"))
    assert "RELOAD_NOT_AUTHORIZED" in hup.failure_codes
    assert "UNKNOWN_REAL_SIGNAL" in unknown.failure_codes
    completed = request_passive_cli_shutdown_v1(policy=_policy(), runtime_state=term.current_state, shutdown_id="shutdown-v1")
    assert completed.current_state.state_code == "GRACEFUL_SHUTDOWN_COMPLETE"
    repeated = request_passive_cli_shutdown_v1(policy=_policy(), runtime_state=completed.current_state, shutdown_id="shutdown-repeat-v1")
    assert repeated.current_state.state_code == "GRACEFUL_SHUTDOWN_COMPLETE"
    _assert_closed(completed)


def test_audit_and_main_require_explicit_metadata_without_operational_side_effects() -> None:
    parsed = parse_explicit_passive_cli_arguments_v1(policy=_policy(), explicit_argv=("--mode", "passive"))
    cli = evaluate_passive_production_cli_v1(policy=_policy(), invocation=_invocation(), argument_result=parsed)
    evidence = build_passive_cli_signal_audit_evidence_v1(
        evidence_id="cli-signal-audit-v1", policy=_policy(), invocation=_invocation(),
        argument_result=parsed, cli_result=cli, runtime_state=cli.current_state,
    )
    _frozen(evidence)
    _assert_closed(evidence)
    result = main(policy=_policy(), explicit_argv=("--mode", "passive"), invocation=_invocation(),
                  adapter_policy=_adapter_policy(), adapter=_adapter(), registration_request=_registration())
    assert result.ready is True
    _assert_closed(result)
