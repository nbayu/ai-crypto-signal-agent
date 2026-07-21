"""RED contract for host-global signal and systemd lifecycle design metadata only."""
from __future__ import annotations

from dataclasses import is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from engine.phase_12_host_global_signal_systemd_runtime_boundary_design_contract_v1 import (
    DeterministicProcessExitDesignV1,
    HostGlobalSignalDispatchDesignV1,
    HostGlobalSignalHandlerDesignV1,
    HostGlobalSignalRegistrationDesignV1,
    HostGlobalSignalRestorationDesignV1,
    HostGlobalSignalRuntimeIdentityV1,
    HostGlobalSignalShutdownDesignV1,
    HostGlobalSignalSystemdRuntimeAuditEvidenceV1,
    HostGlobalSignalSystemdRuntimeBoundaryPolicyV1,
    HostGlobalSignalSystemdRuntimeDecisionV1,
    HostGlobalSignalSystemdRuntimeFailureV1,
    HostGlobalSignalSystemdRuntimeIndependentReviewerApprovalV1,
    HostGlobalSignalSystemdRuntimeOperatorAttestationV1,
    SystemdServiceFailureBoundaryV1,
    SystemdServiceRestartBoundaryV1,
    SystemdServiceRuntimeIdentityV1,
    SystemdServiceRuntimeReadinessChecklistV1,
    SystemdServiceShutdownLifecycleV1,
    SystemdServiceStartupLifecycleV1,
    build_host_global_signal_systemd_runtime_boundary_audit_evidence_v1,
    evaluate_host_global_signal_systemd_runtime_boundary_design_v1,
)


_NOW = datetime(2030, 1, 10, 12, 0, tzinfo=UTC)
_PYTHON = "/opt/ai-crypto-signal-agent/.venv/bin/python"
_MODULE = "engine.phase_12_passive_runtime_launcher_executable_contract_v1"
_ADAPTER = "engine.phase_12_passive_production_cli_real_signal_adapter_contract_v1"
_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "HOST_GLOBAL_SIGNAL_DESIGN_NOT_AUTHORIZED",
    "SYSTEMD_RUNTIME_DESIGN_NOT_AUTHORIZED", "MAIN_THREAD_REGISTRATION_DESIGN_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_DESIGN_NOT_AUTHORIZED", "PROCESS_EXIT_DESIGN_NOT_AUTHORIZED",
    "HOST_GLOBAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
    "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED",
    "SYSTEMD_RUNTIME_IMPLEMENTATION_NOT_AUTHORIZED", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED",
    "PROCESS_TERMINATION_NOT_AUTHORIZED", "SERVICE_UNIT_MISMATCH",
    "SERVICE_MANAGER_SCOPE_MISMATCH", "DEPLOYMENT_STATE_MISMATCH", "SERVICE_USER_MISMATCH",
    "SERVICE_GROUP_MISMATCH", "WORKING_DIRECTORY_MISMATCH", "PYTHON_INTERPRETER_MISMATCH",
    "LAUNCHER_MODULE_MISMATCH", "CLI_ADAPTER_MODULE_MISMATCH", "PASSIVE_CLI_ARGUMENT_MISMATCH",
    "PASSIVE_DEFAULT_REQUIRED", "MAIN_THREAD_REGISTRATION_REQUIRED", "SIGNAL_SET_MISMATCH",
    "DUPLICATE_REGISTRATION_NOT_ALLOWED", "UNSUPPORTED_SIGNAL_REGISTRATION",
    "SIGHUP_RELOAD_NOT_AUTHORIZED", "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED",
    "HANDLER_IO_NOT_AUTHORIZED", "HANDLER_LIVE_ACTION_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_REQUIRED", "HANDLER_RESTORATION_ORDER_INVALID",
    "HANDLER_RESTORATION_NOT_IDEMPOTENT", "GRACEFUL_SHUTDOWN_REQUIRED",
    "BOUNDED_SHUTDOWN_REQUIRED", "SHUTDOWN_TIMEOUT_REQUIRED", "SHUTDOWN_NOT_IDEMPOTENT",
    "PROCESS_EXIT_CLASSIFICATION_OVERLAP", "SYS_EXIT_NOT_AUTHORIZED", "SYSTEM_EXIT_NOT_AUTHORIZED",
    "OS_EXIT_NOT_AUTHORIZED", "PROCESS_SIGNAL_SEND_NOT_AUTHORIZED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED", "ENVIRONMENT_READ_NOT_AUTHORIZED",
    "FILESYSTEM_READ_NOT_AUTHORIZED", "FILESYSTEM_WRITE_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "SYSTEMD_ACCESS_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED", "WORKER_START_NOT_AUTHORIZED",
    "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED",
    "TRADING_NOT_AUTHORIZED", "SUBPROCESS_NOT_AUTHORIZED", "THREAD_START_NOT_AUTHORIZED",
    "EVENT_LOOP_START_NOT_AUTHORIZED", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED",
    "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE", "EVIDENCE_EXPIRED",
    "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED", "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED",
    "DAEMON_RELOAD_NOT_AUTHORIZED", "SERVICE_ENABLEMENT_NOT_AUTHORIZED", "SERVICE_START_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_MATERIAL_EXPOSURE_DETECTED",
    "RAW_HANDLER_REPRESENTATION_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> HostGlobalSignalSystemdRuntimeBoundaryPolicyV1:
    values = dict(
        policy_id="host-global-policy-v1", policy_version="V1",
        host_global_signal_boundary_design_authorized=True,
        systemd_service_runtime_lifecycle_design_authorized=True,
        main_thread_signal_registration_design_authorized=True,
        handler_restoration_design_authorized=True,
        deterministic_process_exit_design_authorized=True,
        host_global_signal_implementation_authorized=False,
        systemd_service_runtime_implementation_authorized=False,
        main_thread_signal_registration_implementation_authorized=False,
        process_termination_implementation_authorized=False, process_exit_execution_authorized=False,
        implicit_sys_argv_access_authorized=False, environment_read_authorized=False,
        filesystem_read_authorized=False, filesystem_write_authorized=False,
        credential_access_authorized=False, credential_loading_authorized=False,
        credential_validation_authorized=False, systemd_unit_file_generation_authorized=False,
        systemd_drop_in_generation_authorized=False, systemd_access_authorized=False,
        service_unit_installation_authorized=False, daemon_reload_authorized=False,
        service_enablement_authorized=False, service_start_restart_authorized=False,
        provider_transmission_authorized=False, scanner_execution_authorized=False,
        worker_start_authorized=False, scheduler_start_authorized=False,
        telegram_start_authorized=False, database_mutation_authorized=False,
        artifact_publication_authorized=False, trading_authorized=False,
        subprocess_authorized=False, thread_start_authorized=False,
        event_loop_start_authorized=False, runtime_activation_authorized=False,
        publication_authorized=False, evidence_max_age_seconds=3600, fail_closed=True,
    )
    return HostGlobalSignalSystemdRuntimeBoundaryPolicyV1(**(values | overrides))


def _signal_identity(**overrides: object) -> HostGlobalSignalRuntimeIdentityV1:
    values = dict(
        signal_runtime_id="host-global-runtime-v1", process_role="SYSTEMD_SERVICE_MAIN_PROCESS",
        registration_scope="HOST_GLOBAL_MAIN_THREAD", supported_signal_names=("SIGTERM", "SIGINT"),
        reload_signal_name="SIGHUP", unsupported_signal_names=("SIGQUIT", "SIGUSR1", "SIGUSR2", "UNKNOWN"),
        main_thread_registration_required=True, host_global_signal_design_authorized=True,
        host_global_signal_implementation_authorized=False,
        main_thread_signal_registration_design_authorized=True,
        main_thread_signal_registration_implementation_authorized=False,
        process_termination_implementation_authorized=False, process_exit_execution_authorized=False,
    )
    return HostGlobalSignalRuntimeIdentityV1(**(values | overrides))


def _registration(**overrides: object) -> HostGlobalSignalRegistrationDesignV1:
    values = dict(
        registration_design_id="host-registration-v1", main_thread_only=True,
        registration_after_configuration_validation=True, registration_before_passive_readiness=True,
        signal_names=("SIGTERM", "SIGINT"), duplicate_registration_prohibited=True,
        unsupported_registration_prohibited=True, previous_handler_classifications_only=True,
        previous_handler_repr_prohibited=True, handler_restoration_mandatory=True,
        restoration_order="SIGTERM_THEN_SIGINT", registration_failure_fail_closed=True,
        partial_registration_rollback_defined=True, signal_wait_loop_allowed=False,
        pause_loop_allowed=False, process_termination_allowed=False, sys_exit_allowed=False,
        system_exit_allowed=False, blocking_io_allowed=False, handler_logging_allowed=False,
        handler_live_action_allowed=False, registration_design_ready=True,
        registration_implementation_authorized=False, host_global_registration_authorized=False,
    )
    return HostGlobalSignalRegistrationDesignV1(**(values | overrides))


def _handler(**overrides: object) -> HostGlobalSignalHandlerDesignV1:
    values = dict(
        handler_id="host-handler-v1", sigterm_transition="SHUTDOWN_REQUESTED",
        sigint_transition="SHUTDOWN_REQUESTED", minimal_frame_metadata_only=True,
        blocking_operation_allowed=False, filesystem_access_allowed=False,
        environment_access_allowed=False, credential_access_allowed=False,
        provider_network_access_allowed=False, workload_direct_action_allowed=False,
        publication_allowed=False, database_mutation_allowed=False, raw_exception_allowed=False,
        process_exit_allowed=False, in_memory_metadata_only=True, repeated_signal_idempotent=True,
        handler_design_ready=True, handler_implementation_authorized=False,
    )
    return HostGlobalSignalHandlerDesignV1(**(values | overrides))


def _restoration(**overrides: object) -> HostGlobalSignalRestorationDesignV1:
    values = dict(
        restoration_id="host-restoration-v1", original_handler_classifications_captured=True,
        restoration_on_normal_shutdown=True, restoration_on_partial_registration_failure=True,
        restoration_on_startup_abort=True, restoration_order="SIGTERM_THEN_SIGINT",
        restoration_idempotent=True, restoration_failure_classified=True,
        raw_callable_repr_prohibited=True, memory_address_exposure_prohibited=True,
        restoration_process_exit_allowed=False, restoration_opens_gate=False,
        handler_restoration_design_authorized=True,
        handler_restoration_implementation_authorized=False, handler_restoration_design_ready=True,
    )
    return HostGlobalSignalRestorationDesignV1(**(values | overrides))


def _dispatch(**overrides: object) -> HostGlobalSignalDispatchDesignV1:
    values = dict(
        dispatch_id="host-dispatch-v1", sigterm_transition=("PASSIVE_READY", "SHUTDOWN_REQUESTED"),
        sigint_transition=("PASSIVE_READY", "SHUTDOWN_REQUESTED"),
        repeated_transition=("SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        completed_transition=("GRACEFUL_SHUTDOWN_COMPLETE", "GRACEFUL_SHUTDOWN_COMPLETE"),
        sighup_classification="RELOAD_NOT_AUTHORIZED", unknown_classification="UNKNOWN_HOST_GLOBAL_SIGNAL",
        gates_remain_closed=True, live_authorities_remain_false=True, dispatch_design_ready=True,
    )
    return HostGlobalSignalDispatchDesignV1(**(values | overrides))


def _shutdown(**overrides: object) -> HostGlobalSignalShutdownDesignV1:
    values = dict(
        shutdown_id="host-shutdown-v1", graceful_shutdown_required=True,
        bounded_shutdown_required=True, shutdown_timeout_seconds=30,
        deterministic_shutdown_order=True, repeated_shutdown_idempotent=True,
        passive_resource_set_empty=True, future_worker_stop_coordination_classified=True,
        future_scheduler_stop_coordination_classified=True,
        future_provider_session_close_classified=True, future_telegram_stop_classified=True,
        pending_database_mutation_allowed=False, pending_publication_allowed=False,
        handler_restoration_before_exit_classification=True,
        process_exit_after_shutdown_classification_only=True,
        forced_kill_fallback_design_classified=True, forced_kill_execution_authorized=False,
        shutdown_design_ready=True,
    )
    return HostGlobalSignalShutdownDesignV1(**(values | overrides))


def _exit(**overrides: object) -> DeterministicProcessExitDesignV1:
    values = dict(
        exit_design_id="host-exit-v1", exit_codes=(20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31),
        process_exit_design_authorized=True, process_exit_execution_authorized=False,
        sys_exit_allowed=False, system_exit_raise_allowed=False, os_exit_allowed=False,
        process_signal_send_allowed=False, exit_design_ready=True,
    )
    return DeterministicProcessExitDesignV1(**(values | overrides))


def _service(**overrides: object) -> SystemdServiceRuntimeIdentityV1:
    values = dict(
        service_id="systemd-runtime-v1", service_unit="ai-crypto-signal-agent.service",
        service_manager_scope="SYSTEM", deployment_state="NOT_YET_INSTALLED",
        service_user="ai-crypto-signal-agent", service_group="ai-crypto-signal-agent",
        working_directory="/opt/ai-crypto-signal-agent", python_interpreter=_PYTHON,
        launcher_module=_MODULE, cli_adapter_module=_ADAPTER,
        passive_cli_arguments=("--mode", "passive"), passive_default=True,
        production_runtime_execution_authorized=False, service_execution_authorized=False,
    )
    return SystemdServiceRuntimeIdentityV1(**(values | overrides))


def _startup(**overrides: object) -> SystemdServiceStartupLifecycleV1:
    values = dict(
        startup_lifecycle_id="systemd-startup-v1", explicit_cli_metadata_validated=True,
        passive_configuration_validated=True, all_gates_confirmed_closed=True,
        main_thread_registration_attempted_after_validation=True,
        registration_before_passive_readiness=True, redacted_previous_handler_metadata_only=True,
        registration_success_confirmed=True, passive_readiness_entered=True,
        network_workload_activation_performed=False, implicit_sys_argv_access_allowed=False,
        environment_read_allowed=False, credential_loading_allowed=False,
        network_activation_allowed=False, workload_start_allowed=False,
        service_startup_design_ready=True, service_runtime_implementation_authorized=False,
        service_execution_authorized=False,
    )
    return SystemdServiceStartupLifecycleV1(**(values | overrides))


def _service_shutdown(**overrides: object) -> SystemdServiceShutdownLifecycleV1:
    values = dict(
        shutdown_lifecycle_id="systemd-shutdown-v1", shutdown_on_sigterm_defined=True,
        shutdown_on_sigint_defined=True, sighup_reload_allowed=False,
        repeated_signal_idempotent=True, handler_restoration_required=True,
        process_exit_execution_authorized=False, service_shutdown_design_ready=True,
    )
    return SystemdServiceShutdownLifecycleV1(**(values | overrides))


def _restart(**overrides: object) -> SystemdServiceRestartBoundaryV1:
    values = dict(
        restart_boundary_id="systemd-restart-v1", restart_policy_classification="METADATA_ONLY",
        restart_on_clean_exit=False, restart_on_fail_closed_exit=False, restart_on_signal_exit=False,
        restart_delay_classification="METADATA_ONLY", start_limit_classification="METADATA_ONLY",
        automatic_restart_execution_authorized=False, restart_policy_implementation_authorized=False,
        systemd_access_authorized=False,
    )
    return SystemdServiceRestartBoundaryV1(**(values | overrides))


def _failure_boundary(**overrides: object) -> SystemdServiceFailureBoundaryV1:
    values = dict(
        failure_boundary_id="systemd-failure-v1", cli_validation_failure_classified=True,
        passive_configuration_failure_classified=True, signal_registration_failure_classified=True,
        partial_registration_rollback_failure_classified=True,
        handler_restoration_failure_classified=True, invalid_lifecycle_transition_classified=True,
        attempted_credential_loading_classified=True, attempted_network_activation_classified=True,
        attempted_workload_activation_classified=True, attempted_runtime_activation_classified=True,
        attempted_process_exit_classified=True, raw_exception_exposure_prohibited=True,
        failure_boundary_ready=True,
    )
    return SystemdServiceFailureBoundaryV1(**(values | overrides))


def _checklist(**overrides: object) -> SystemdServiceRuntimeReadinessChecklistV1:
    values = dict(
        checklist_id="systemd-checklist-v1", canonical_service_identity_confirmed=True,
        canonical_interpreter_and_module_confirmed=True, explicit_passive_cli_argv_confirmed=True,
        passive_default_confirmed=True, implicit_argv_access_prohibited=True,
        environment_reads_prohibited=True, all_gates_closed=True, sigterm_design_complete=True,
        sigint_design_complete=True, sighup_rejection_complete=True,
        unknown_signal_behavior_complete=True, main_thread_only_registration_defined=True,
        duplicate_registration_rejected=True, partial_registration_rollback_defined=True,
        handler_minimality_defined=True, handler_io_prohibited=True, restoration_mandatory=True,
        restoration_idempotent=True, deterministic_exit_classifications_defined=True,
        process_exit_execution_unauthorized=True, systemd_runtime_implementation_unauthorized=True,
        service_execution_unauthorized=True, credential_loading_unauthorized=True,
        network_workload_runtime_publication_unauthorized=True,
        unit_generation_install_reload_enable_start_unauthorized=True,
        operator_attestation_complete=True, reviewer_approval_complete=True,
        evidence_fresh=True, checklist_complete=True,
    )
    return SystemdServiceRuntimeReadinessChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> HostGlobalSignalSystemdRuntimeOperatorAttestationV1:
    values = dict(
        attestation_id="host-operator-v1", operator_identity="operator-v1", operator_role="OPERATOR",
        policy_id="host-global-policy-v1", signal_runtime_id="host-global-runtime-v1",
        handler_id="host-handler-v1", restoration_id="host-restoration-v1",
        service_id="systemd-runtime-v1", checklist_id="systemd-checklist-v1",
        design_only_authority_confirmed=True, implementation_execution_unauthorized_confirmed=True,
        all_gates_closed_confirmed=True, sensitive_evidence_retained=False,
        attested_at=_NOW - timedelta(minutes=5), expires_at=_NOW + timedelta(minutes=5),
        attestation_complete=True,
    )
    return HostGlobalSignalSystemdRuntimeOperatorAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> HostGlobalSignalSystemdRuntimeIndependentReviewerApprovalV1:
    values = dict(
        approval_id="host-reviewer-v1", reviewer_identity="reviewer-v1",
        reviewer_role="INDEPENDENT_REVIEWER", policy_id="host-global-policy-v1",
        signal_runtime_id="host-global-runtime-v1", handler_id="host-handler-v1",
        restoration_id="host-restoration-v1", service_id="systemd-runtime-v1",
        checklist_id="systemd-checklist-v1", attestation_id="host-operator-v1",
        design_only_authority_confirmed=True, implementation_execution_unauthorized_confirmed=True,
        all_gates_closed_confirmed=True, sensitive_evidence_retained=False, approved=True,
        reviewed_at=_NOW - timedelta(minutes=4), expires_at=_NOW + timedelta(minutes=5), review_complete=True,
    )
    return HostGlobalSignalSystemdRuntimeIndependentReviewerApprovalV1(**(values | overrides))


def _evaluate(**overrides: object) -> HostGlobalSignalSystemdRuntimeDecisionV1:
    values = dict(
        policy=_policy(), signal_identity=_signal_identity(), registration_design=_registration(),
        handler_design=_handler(), restoration_design=_restoration(), dispatch_design=_dispatch(),
        shutdown_design=_shutdown(), exit_design=_exit(), service_identity=_service(),
        startup_lifecycle=_startup(), shutdown_lifecycle=_service_shutdown(), restart_boundary=_restart(),
        failure_boundary=_failure_boundary(), checklist=_checklist(), operator_attestation=_operator(),
        reviewer_approval=_reviewer(), evaluation_time=_NOW,
    )
    return evaluate_host_global_signal_systemd_runtime_boundary_design_v1(**(values | overrides))


def _assert_authority(record: object) -> None:
    for name in (
        "host_global_signal_implementation_authorized", "systemd_service_runtime_implementation_authorized",
        "main_thread_signal_registration_implementation_authorized", "process_exit_execution_authorized",
        "process_termination_implementation_authorized", "credential_loading_authorized",
        "systemd_access_authorized", "network_authorized", "production_runtime_execution_authorized",
        "runtime_activation_authorized", "publication_authorized",
    ):
        assert getattr(record, name) is False
    assert record.activation_gate_open is False
    assert record.credential_gate_open is False
    assert record.network_gate_open is False
    assert record.workload_gate_open is False
    assert record.fail_closed is True


def test_public_records_are_frozen_slotted_and_metadata_only() -> None:
    records = (_policy(), _signal_identity(), _registration(), _handler(), _restoration(), _dispatch(),
               _shutdown(), _exit(), _service(), _startup(), _service_shutdown(), _restart(),
               _failure_boundary(), _checklist(), _operator(), _reviewer())
    for record in records:
        _frozen(record)
    for record_type in (HostGlobalSignalSystemdRuntimeFailureV1,
                        HostGlobalSignalSystemdRuntimeDecisionV1,
                        HostGlobalSignalSystemdRuntimeAuditEvidenceV1):
        assert hasattr(record_type, "__dataclass_fields__")


def test_aligned_metadata_is_ready_only_for_separate_implementation() -> None:
    decision = _evaluate()
    _frozen(decision)
    assert decision.ready is True
    assert decision.decision_classification == (
        "HOST_GLOBAL_SIGNAL_AND_SYSTEMD_SERVICE_RUNTIME_BOUNDARY_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION"
    )
    assert decision.failure_codes == ()
    assert decision.states == (
        "HOST_GLOBAL_SIGNAL_DESIGN_AUTHORIZED", "HOST_GLOBAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
        "MAIN_THREAD_REGISTRATION_DESIGN_READY", "MAIN_THREAD_REGISTRATION_NOT_IMPLEMENTED",
        "HANDLER_RESTORATION_DESIGN_READY", "HANDLER_RESTORATION_NOT_IMPLEMENTED",
        "PROCESS_EXIT_DESIGN_READY", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED",
        "SYSTEMD_SERVICE_RUNTIME_DESIGN_READY", "SYSTEMD_SERVICE_RUNTIME_NOT_IMPLEMENTED",
        "SERVICE_UNIT_NOT_INSTALLED", "SERVICE_EXECUTION_NOT_AUTHORIZED",
        "PRODUCTION_RUNTIME_NOT_AUTHORIZED", "ACTIVATION_GATE_CLOSED", "CREDENTIAL_GATE_CLOSED",
        "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED", "DEPLOYMENT_BLOCKED",
    )
    _assert_authority(decision)


@pytest.mark.parametrize(
    ("overrides", "failure_code"),
    (
        ({"policy": _policy(policy_id="")}, "POLICY_ID_EMPTY"),
        ({"policy": _policy(policy_version="")}, "POLICY_VERSION_EMPTY"),
        ({"policy": _policy(host_global_signal_boundary_design_authorized=False)}, "HOST_GLOBAL_SIGNAL_DESIGN_NOT_AUTHORIZED"),
        ({"policy": _policy(systemd_service_runtime_lifecycle_design_authorized=False)}, "SYSTEMD_RUNTIME_DESIGN_NOT_AUTHORIZED"),
        ({"policy": _policy(main_thread_signal_registration_design_authorized=False)}, "MAIN_THREAD_REGISTRATION_DESIGN_NOT_AUTHORIZED"),
        ({"policy": _policy(handler_restoration_design_authorized=False)}, "HANDLER_RESTORATION_DESIGN_NOT_AUTHORIZED"),
        ({"policy": _policy(deterministic_process_exit_design_authorized=False)}, "PROCESS_EXIT_DESIGN_NOT_AUTHORIZED"),
        ({"policy": _policy(host_global_signal_implementation_authorized=True)}, "HOST_GLOBAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED"),
        ({"policy": _policy(systemd_service_runtime_implementation_authorized=True)}, "SYSTEMD_RUNTIME_IMPLEMENTATION_NOT_AUTHORIZED"),
        ({"signal_identity": _signal_identity(main_thread_registration_required=False)}, "MAIN_THREAD_REGISTRATION_REQUIRED"),
        ({"signal_identity": _signal_identity(supported_signal_names=("SIGTERM",))}, "SIGNAL_SET_MISMATCH"),
        ({"registration_design": _registration(duplicate_registration_prohibited=False)}, "DUPLICATE_REGISTRATION_NOT_ALLOWED"),
        ({"registration_design": _registration(partial_registration_rollback_defined=False)}, "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED"),
        ({"handler_design": _handler(blocking_operation_allowed=True)}, "HANDLER_IO_NOT_AUTHORIZED"),
        ({"handler_design": _handler(provider_network_access_allowed=True)}, "HANDLER_LIVE_ACTION_NOT_AUTHORIZED"),
        ({"restoration_design": _restoration(restoration_on_normal_shutdown=False)}, "HANDLER_RESTORATION_REQUIRED"),
        ({"restoration_design": _restoration(restoration_idempotent=False)}, "HANDLER_RESTORATION_NOT_IDEMPOTENT"),
        ({"shutdown_design": _shutdown(graceful_shutdown_required=False)}, "GRACEFUL_SHUTDOWN_REQUIRED"),
        ({"shutdown_design": _shutdown(shutdown_timeout_seconds=0)}, "SHUTDOWN_TIMEOUT_REQUIRED"),
        ({"exit_design": _exit(exit_codes=(20, 20))}, "PROCESS_EXIT_CLASSIFICATION_OVERLAP"),
        ({"exit_design": _exit(sys_exit_allowed=True)}, "SYS_EXIT_NOT_AUTHORIZED"),
        ({"exit_design": _exit(system_exit_raise_allowed=True)}, "SYSTEM_EXIT_NOT_AUTHORIZED"),
        ({"exit_design": _exit(os_exit_allowed=True)}, "OS_EXIT_NOT_AUTHORIZED"),
        ({"exit_design": _exit(process_signal_send_allowed=True)}, "PROCESS_SIGNAL_SEND_NOT_AUTHORIZED"),
        ({"service_identity": _service(service_unit="other.service")}, "SERVICE_UNIT_MISMATCH"),
        ({"service_identity": _service(cli_adapter_module="other.module")}, "CLI_ADAPTER_MODULE_MISMATCH"),
        ({"startup_lifecycle": _startup(network_activation_allowed=True)}, "NETWORK_NOT_AUTHORIZED"),
        ({"operator_attestation": None}, "OPERATOR_ATTESTATION_REQUIRED"),
        ({"reviewer_approval": None}, "REVIEWER_APPROVAL_REQUIRED"),
        ({"reviewer_approval": _reviewer(reviewer_identity="operator-v1")}, "OPERATOR_REVIEWER_COLLISION"),
        ({"operator_attestation": _operator(attested_at=_NOW + timedelta(seconds=1))}, "EVIDENCE_FROM_FUTURE"),
        ({"operator_attestation": _operator(attested_at=_NOW - timedelta(hours=2))}, "EVIDENCE_STALE"),
        ({"reviewer_approval": _reviewer(expires_at=_NOW - timedelta(seconds=1))}, "EVIDENCE_EXPIRED"),
        ({"checklist": _checklist(checklist_complete=False)}, "RAW_EXCEPTION_EXPOSURE_DETECTED"),
    ),
)
def test_design_failures_are_fail_closed_and_deterministically_ordered(
    overrides: dict[str, object], failure_code: str,
) -> None:
    decision = _evaluate(**overrides)
    assert decision.ready is False
    assert decision.decision_classification == "NOT_READY"
    assert failure_code in decision.failure_codes
    assert tuple(item.failure_code for item in decision.failures) == decision.failure_codes
    assert tuple(sorted(decision.failure_codes, key=_FAILURES.index)) == decision.failure_codes
    _assert_authority(decision)


def test_audit_evidence_is_redacted_and_preserves_design_only_blocking() -> None:
    decision = _evaluate()
    evidence = build_host_global_signal_systemd_runtime_boundary_audit_evidence_v1(
        evidence_id="host-audit-v1", policy=_policy(), signal_identity=_signal_identity(),
        registration_design=_registration(), handler_design=_handler(), restoration_design=_restoration(),
        dispatch_design=_dispatch(), shutdown_design=_shutdown(), exit_design=_exit(),
        service_identity=_service(), startup_lifecycle=_startup(), shutdown_lifecycle=_service_shutdown(),
        restart_boundary=_restart(), failure_boundary=_failure_boundary(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), decision=decision,
        evaluation_time=_NOW,
    )
    _frozen(evidence)
    assert evidence.ready_for_separate_implementation_decision is True
    assert evidence.process_exit_execution_authorized is False
    assert evidence.service_execution_authorized is False
    assert evidence.failure_codes == ()
    _assert_authority(evidence)
