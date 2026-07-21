"""RED contract for production host-signal and service-execution readiness design."""
from __future__ import annotations

from dataclasses import is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from engine.phase_12_production_host_signal_service_execution_readiness_contract_v1 import (
    ProductionGracefulShutdownReadinessV1,
    ProductionHandlerInstallationReadinessV1,
    ProductionHandlerRestorationReadinessV1,
    ProductionHostSignalRuntimeIdentityV1,
    ProductionHostSignalServiceReadinessAuditEvidenceV1,
    ProductionHostSignalServiceReadinessChecklistV1,
    ProductionHostSignalServiceReadinessDecisionV1,
    ProductionHostSignalServiceReadinessFailureV1,
    ProductionHostSignalServiceReadinessPolicyV1,
    ProductionLifecycleEvidencePackageV1,
    ProductionLifecycleIndependentReviewerApprovalV1,
    ProductionLifecycleOperatorAttestationV1,
    ProductionMainThreadRegistrationReadinessV1,
    ProductionProcessExitReadinessV1,
    ProductionSignalDispatchReadinessV1,
    SystemdServiceDeploymentPrerequisiteV1,
    SystemdServiceExecutionIdentityV1,
    SystemdServiceExecutionReadinessV1,
    build_production_host_signal_service_execution_readiness_audit_evidence_v1,
    evaluate_production_host_signal_service_execution_readiness_v1,
)


_NOW = datetime(2031, 2, 3, 4, 5, tzinfo=UTC)
_PYTHON = "/opt/ai-crypto-signal-agent/.venv/bin/python"
_LAUNCHER = "engine.phase_12_passive_runtime_launcher_executable_contract_v1"
_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY",
    "PRODUCTION_HOST_SIGNAL_READINESS_DESIGN_NOT_AUTHORIZED",
    "MAIN_THREAD_REGISTRATION_READINESS_DESIGN_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_READINESS_DESIGN_NOT_AUTHORIZED",
    "PROCESS_EXIT_READINESS_DESIGN_NOT_AUTHORIZED",
    "SYSTEMD_SERVICE_EXECUTION_READINESS_DESIGN_NOT_AUTHORIZED",
    "LIFECYCLE_EVIDENCE_PACKAGE_DESIGN_NOT_AUTHORIZED",
    "PRODUCTION_HOST_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
    "DIRECT_HOST_SIGNAL_REGISTRATION_NOT_AUTHORIZED",
    "PRODUCTION_HANDLER_INSTALLATION_NOT_AUTHORIZED",
    "PRODUCTION_HANDLER_RESTORATION_EXECUTION_NOT_AUTHORIZED",
    "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED", "PROCESS_TERMINATION_NOT_AUTHORIZED",
    "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED",
    "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED",
    "SERVICE_UNIT_MISMATCH", "SERVICE_MANAGER_SCOPE_MISMATCH", "DEPLOYMENT_STATE_MISMATCH",
    "SERVICE_USER_MISMATCH", "SERVICE_GROUP_MISMATCH", "WORKING_DIRECTORY_MISMATCH",
    "PYTHON_INTERPRETER_MISMATCH", "LAUNCHER_MODULE_MISMATCH",
    "PASSIVE_CLI_ARGUMENT_MISMATCH", "PASSIVE_DEFAULT_REQUIRED",
    "ISOLATED_SIGNAL_ADAPTER_GREEN_REQUIRED", "MAIN_THREAD_REGISTRATION_REQUIRED",
    "SIGNAL_SET_MISMATCH", "DUPLICATE_REGISTRATION_NOT_ALLOWED",
    "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED", "PREVIOUS_HANDLER_REDACTION_REQUIRED",
    "HANDLER_IO_NOT_AUTHORIZED", "HANDLER_LIVE_ACTION_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_REQUIRED", "HANDLER_RESTORATION_ORDER_INVALID",
    "HANDLER_RESTORATION_NOT_IDEMPOTENT", "GRACEFUL_SHUTDOWN_REQUIRED",
    "BOUNDED_SHUTDOWN_REQUIRED", "SHUTDOWN_TIMEOUT_REQUIRED", "SHUTDOWN_NOT_IDEMPOTENT",
    "PROCESS_EXIT_CLASSIFICATION_OVERLAP", "SYS_EXIT_NOT_AUTHORIZED",
    "SYSTEM_EXIT_NOT_AUTHORIZED", "OS_EXIT_NOT_AUTHORIZED", "PROCESS_SIGNAL_SEND_NOT_AUTHORIZED",
    "DEPLOYMENT_PREREQUISITES_INCOMPLETE", "SYSTEMD_ACCESS_NOT_AUTHORIZED",
    "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED", "SYSTEMD_DROP_IN_GENERATION_NOT_AUTHORIZED",
    "SERVICE_INSTALLATION_NOT_AUTHORIZED", "DAEMON_RELOAD_NOT_AUTHORIZED",
    "SERVICE_ENABLEMENT_NOT_AUTHORIZED", "SERVICE_START_NOT_AUTHORIZED",
    "CREDENTIAL_PRESENCE_NOT_CONFIRMED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "SCANNER_EXECUTION_NOT_AUTHORIZED", "WORKER_START_NOT_AUTHORIZED",
    "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED",
    "TRADING_NOT_AUTHORIZED", "SUBPROCESS_NOT_AUTHORIZED", "THREAD_CREATION_NOT_AUTHORIZED",
    "EVENT_LOOP_START_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "PUBLICATION_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED",
    "WORKLOAD_GATE_MUST_REMAIN_CLOSED", "OPERATOR_ATTESTATION_REQUIRED",
    "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE",
    "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "PROVIDER_MATERIAL_EXPOSURE_DETECTED", "RAW_HANDLER_REPRESENTATION_EXPOSURE_DETECTED",
    "PROCESS_METADATA_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> ProductionHostSignalServiceReadinessPolicyV1:
    values = dict(
        policy_id="production-readiness-policy-v1", policy_version="V1",
        production_host_global_signal_readiness_design_authorized=True,
        production_main_thread_registration_readiness_design_authorized=True,
        production_handler_restoration_readiness_design_authorized=True,
        production_process_exit_readiness_design_authorized=True,
        systemd_service_execution_readiness_design_authorized=True,
        production_lifecycle_evidence_package_design_authorized=True,
        production_host_global_signal_implementation_authorized=False,
        direct_host_signal_registration_authorized=False,
        production_handler_installation_authorized=False,
        production_handler_restoration_execution_authorized=False,
        process_exit_execution_authorized=False, process_termination_authorized=False,
        process_signal_transmission_authorized=False, production_cli_execution_authorized=False,
        production_service_execution_authorized=False, production_runtime_execution_authorized=False,
        implicit_sys_argv_access_authorized=False, environment_read_authorized=False,
        filesystem_read_authorized=False, filesystem_write_authorized=False,
        credential_access_authorized=False, credential_loading_authorized=False,
        credential_validation_authorized=False, systemd_unit_file_generation_authorized=False,
        systemd_drop_in_generation_authorized=False, systemd_access_authorized=False,
        service_unit_installation_authorized=False, daemon_reload_authorized=False,
        service_enablement_authorized=False, service_start_restart_authorized=False,
        provider_transmission_authorized=False, network_authorized=False,
        scanner_execution_authorized=False, worker_start_authorized=False,
        scheduler_start_authorized=False, telegram_start_authorized=False,
        database_mutation_authorized=False, artifact_publication_authorized=False,
        trading_authorized=False, subprocess_authorized=False, thread_creation_authorized=False,
        event_loop_start_authorized=False, runtime_activation_authorized=False,
        publication_authorized=False, activation_gate_open=False, credential_gate_open=False,
        network_gate_open=False, workload_gate_open=False, evidence_max_age_seconds=3600,
        fail_closed=True,
    )
    return ProductionHostSignalServiceReadinessPolicyV1(**(values | overrides))


def _runtime(**overrides: object) -> ProductionHostSignalRuntimeIdentityV1:
    values = dict(
        runtime_id="production-host-runtime-v1", process_role="SYSTEMD_SERVICE_MAIN_PROCESS",
        signal_scope="PRODUCTION_HOST_GLOBAL_MAIN_THREAD", supported_signal_names=("SIGTERM", "SIGINT"),
        reload_signal_name="SIGHUP", unsupported_signal_names=("SIGQUIT", "SIGUSR1", "SIGUSR2", "UNKNOWN"),
        main_thread_registration_required=True, isolated_adapter_validation_completed=True,
        isolated_adapter_green=True, production_host_signal_readiness_design_authorized=True,
        production_host_signal_implementation_authorized=False,
        direct_host_signal_registration_authorized=False,
    )
    return ProductionHostSignalRuntimeIdentityV1(**(values | overrides))


def _registration(**overrides: object) -> ProductionMainThreadRegistrationReadinessV1:
    values = dict(
        registration_id="production-main-thread-readiness-v1", caller_supplied_main_thread_contract_green=True,
        isolated_adapter_registration_green=True, signal_names=("SIGTERM", "SIGINT"),
        configuration_before_registration=True, registration_before_passive_readiness=True,
        duplicate_registration_prohibited=True, unsupported_registration_prohibited=True,
        partial_registration_rollback_green=True, previous_handler_redaction_green=True,
        raw_handler_representation_prohibited=True, memory_address_exposure_prohibited=True,
        no_host_registration_performed=True, no_signal_import_performed=True,
        no_process_action_performed=True, registration_readiness_complete=True,
        registration_implementation_authorized=False, direct_registration_authorized=False,
    )
    return ProductionMainThreadRegistrationReadinessV1(**(values | overrides))


def _installation(**overrides: object) -> ProductionHandlerInstallationReadinessV1:
    values = dict(
        handler_id="production-handler-readiness-v1", minimal_non_blocking=True,
        shutdown_request_only=True, sigterm_transition="SHUTDOWN_REQUESTED",
        sigint_transition="SHUTDOWN_REQUESTED", idempotent=True,
        filesystem_access_allowed=False, environment_access_allowed=False,
        credential_access_allowed=False, provider_network_action_allowed=False,
        workload_direct_action_allowed=False, database_mutation_allowed=False,
        publication_allowed=False, handler_logging_allowed=False,
        process_exit_allowed=False, raw_exception_allowed=False,
        handler_installation_readiness_complete=True, handler_installation_authorized=False,
    )
    return ProductionHandlerInstallationReadinessV1(**(values | overrides))


def _restoration(**overrides: object) -> ProductionHandlerRestorationReadinessV1:
    values = dict(
        restoration_id="production-restoration-readiness-v1", reverse_order_defined=True,
        restoration_order=("SIGINT", "SIGTERM"), normal_shutdown_restoration_required=True,
        startup_abort_restoration_required=True, partial_registration_restoration_required=True,
        restoration_idempotent=True, partial_restoration_failure_classified=True,
        previous_handlers_redacted=True, raw_callable_representation_prohibited=True,
        restoration_opens_gate=False, restoration_process_exit_allowed=False,
        handler_restoration_readiness_complete=True, handler_restoration_execution_authorized=False,
    )
    return ProductionHandlerRestorationReadinessV1(**(values | overrides))


def _dispatch(**overrides: object) -> ProductionSignalDispatchReadinessV1:
    values = dict(
        dispatch_id="production-dispatch-readiness-v1", sigterm_transition=("PASSIVE_READY", "SHUTDOWN_REQUESTED"),
        sigint_transition=("PASSIVE_READY", "SHUTDOWN_REQUESTED"),
        repeated_transition=("SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        completed_transition=("GRACEFUL_SHUTDOWN_COMPLETE", "GRACEFUL_SHUTDOWN_COMPLETE"),
        sighup_classification="RELOAD_NOT_AUTHORIZED", unknown_classification="UNKNOWN_HOST_GLOBAL_SIGNAL",
        no_live_authority_granted=True, dispatch_readiness_complete=True,
    )
    return ProductionSignalDispatchReadinessV1(**(values | overrides))


def _shutdown(**overrides: object) -> ProductionGracefulShutdownReadinessV1:
    values = dict(
        shutdown_id="production-shutdown-readiness-v1", graceful_shutdown_required=True,
        bounded_shutdown_required=True, shutdown_timeout_seconds=30,
        deterministic_shutdown_order=True, repeated_shutdown_idempotent=True,
        passive_resource_set_empty=True, worker_stop_coordination_classified=True,
        scheduler_stop_coordination_classified=True, provider_session_close_classified=True,
        telegram_shutdown_classified=True, pending_database_mutation_allowed=False,
        pending_publication_allowed=False, restoration_before_exit_classification=True,
        process_exit_after_shutdown_classification_only=True,
        forced_kill_execution_authorized=False, shutdown_readiness_complete=True,
    )
    return ProductionGracefulShutdownReadinessV1(**(values | overrides))


def _exit(**overrides: object) -> ProductionProcessExitReadinessV1:
    values = dict(
        exit_id="production-exit-readiness-v1", exit_codes=tuple(range(40, 54)),
        process_exit_readiness_complete=True, process_exit_execution_authorized=False,
        sys_exit_allowed=False, system_exit_raise_allowed=False, os_exit_allowed=False,
        process_signal_send_allowed=False,
    )
    return ProductionProcessExitReadinessV1(**(values | overrides))


def _service(**overrides: object) -> SystemdServiceExecutionIdentityV1:
    values = dict(
        service_id="production-service-identity-v1", service_unit="ai-crypto-signal-agent.service",
        service_manager_scope="SYSTEM", deployment_state="NOT_YET_INSTALLED",
        service_user="ai-crypto-signal-agent", service_group="ai-crypto-signal-agent",
        working_directory="/opt/ai-crypto-signal-agent", python_interpreter=_PYTHON,
        launcher_module=_LAUNCHER, passive_cli_arguments=("--mode", "passive"),
        passive_default=True, service_execution_authorized=False,
        production_runtime_execution_authorized=False,
    )
    return SystemdServiceExecutionIdentityV1(**(values | overrides))


def _deployment(**overrides: object) -> SystemdServiceDeploymentPrerequisiteV1:
    values = dict(
        deployment_id="production-deployment-prerequisite-v1", canonical_unit_identity_frozen=True,
        canonical_execstart_metadata_frozen=True, service_user_group_approved=True,
        install_working_directory_approved=True, python_interpreter_approved=True,
        passive_cli_contract_green=True, isolated_signal_adapter_contract_green=True,
        host_signal_readiness_design_complete=True, credential_placement_procedure_defined=True,
        owner_secret_entry_executed=False, credential_presence_claimed=False,
        provider_accounts_metadata_verified=True, provider_hard_caps_metadata_confirmed=True,
        internal_budget_guards_green=True, activation_gate_open=False, credential_gate_open=False,
        network_gate_open=False, workload_gate_open=False, deployment_state="NOT_YET_INSTALLED",
        systemd_actions_authorized=False, service_execution_authorized=False,
        deployment_prerequisites_documented=True, deployment_execution_authorized=False,
    )
    return SystemdServiceDeploymentPrerequisiteV1(**(values | overrides))


def _execution(**overrides: object) -> SystemdServiceExecutionReadinessV1:
    values = dict(
        execution_readiness_id="production-service-execution-readiness-v1",
        installation_identity_verified=True, service_user_group_verified=True,
        interpreter_module_verified=True, passive_cli_metadata_validated=True,
        all_gates_confirmed_closed=True, credential_status_checked_not_loaded=True,
        main_thread_signal_readiness_confirmed=True, restoration_readiness_confirmed=True,
        process_exit_readiness_confirmed=True, service_execution_readiness_complete=True,
        service_execution_authorized=False, systemd_access_authorized=False,
        service_installation_authorized=False, daemon_reload_authorized=False,
        service_enablement_authorized=False, service_start_restart_authorized=False,
    )
    return SystemdServiceExecutionReadinessV1(**(values | overrides))


def _checklist(**overrides: object) -> ProductionHostSignalServiceReadinessChecklistV1:
    values = dict(
        checklist_id="production-readiness-checklist-v1", canonical_service_identity_confirmed=True,
        passive_cli_readiness_confirmed=True, isolated_adapter_green_confirmed=True,
        production_signal_readiness_confirmed=True, main_thread_registration_readiness_confirmed=True,
        handler_installation_readiness_confirmed=True, restoration_readiness_confirmed=True,
        shutdown_readiness_confirmed=True, process_exit_readiness_confirmed=True,
        deployment_prerequisites_confirmed=True, service_execution_readiness_confirmed=True,
        systemd_authorities_false_confirmed=True, credential_not_entered_confirmed=True,
        provider_budget_metadata_confirmed=True, all_gates_closed=True,
        operator_attestation_complete=True, reviewer_approval_complete=True,
        evidence_fresh=True, checklist_complete=True,
    )
    return ProductionHostSignalServiceReadinessChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> ProductionLifecycleOperatorAttestationV1:
    values = dict(
        attestation_id="production-readiness-operator-v1", operator_identity="operator-v1",
        operator_role="OPERATOR", policy_id="production-readiness-policy-v1",
        runtime_id="production-host-runtime-v1", service_id="production-service-identity-v1",
        deployment_id="production-deployment-prerequisite-v1", evidence_id="production-evidence-v1",
        design_only_authority_confirmed=True, implementation_execution_unauthorized_confirmed=True,
        all_gates_closed_confirmed=True, attested_at=_NOW - timedelta(minutes=5),
        expires_at=_NOW + timedelta(minutes=5), attestation_complete=True,
    )
    return ProductionLifecycleOperatorAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> ProductionLifecycleIndependentReviewerApprovalV1:
    values = dict(
        approval_id="production-readiness-review-v1", reviewer_identity="reviewer-v1",
        reviewer_role="INDEPENDENT_REVIEWER", policy_id="production-readiness-policy-v1",
        runtime_id="production-host-runtime-v1", service_id="production-service-identity-v1",
        deployment_id="production-deployment-prerequisite-v1", evidence_id="production-evidence-v1",
        attestation_id="production-readiness-operator-v1", design_only_authority_confirmed=True,
        implementation_execution_unauthorized_confirmed=True, all_gates_closed_confirmed=True,
        approved=True, reviewed_at=_NOW - timedelta(minutes=4), expires_at=_NOW + timedelta(minutes=5),
        review_complete=True,
    )
    return ProductionLifecycleIndependentReviewerApprovalV1(**(values | overrides))


def _evidence(**overrides: object) -> ProductionLifecycleEvidencePackageV1:
    values = dict(
        evidence_id="production-evidence-v1", canonical_service_identity_covered=True,
        passive_cli_readiness_covered=True, isolated_signal_adapter_green_covered=True,
        production_signal_readiness_covered=True, main_thread_readiness_covered=True,
        handler_installation_readiness_covered=True, restoration_readiness_covered=True,
        shutdown_readiness_covered=True, process_exit_readiness_covered=True,
        deployment_prerequisites_covered=True, service_execution_readiness_covered=True,
        systemd_authorities_false=True, credential_not_entered=True,
        provider_budget_metadata_covered=True, all_gates_closed=True,
        evidence_state="DESIGN_READY", implementation_state="IMPLEMENTATION_NOT_AUTHORIZED",
        execution_state="EXECUTION_NOT_AUTHORIZED", deployment_state="DEPLOYMENT_NOT_PERFORMED",
        runtime_state="RUNTIME_NOT_ACTIVE", evidence_complete=True,
    )
    return ProductionLifecycleEvidencePackageV1(**(values | overrides))


def _evaluate(**overrides: object) -> ProductionHostSignalServiceReadinessDecisionV1:
    values = dict(
        policy=_policy(), runtime_identity=_runtime(), registration_readiness=_registration(),
        handler_installation_readiness=_installation(), handler_restoration_readiness=_restoration(),
        dispatch_readiness=_dispatch(), shutdown_readiness=_shutdown(), exit_readiness=_exit(),
        service_identity=_service(), deployment_prerequisites=_deployment(),
        service_execution_readiness=_execution(), lifecycle_evidence=_evidence(),
        checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(),
        evaluation_time=_NOW,
    )
    return evaluate_production_host_signal_service_execution_readiness_v1(**(values | overrides))


def _assert_closed(record: object) -> None:
    for name in (
        "activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open",
        "production_host_signal_implementation_authorized", "direct_host_signal_registration_authorized",
        "production_handler_installation_authorized", "production_handler_restoration_execution_authorized",
        "process_exit_execution_authorized", "process_termination_authorized",
        "process_signal_transmission_authorized", "production_service_execution_authorized",
        "production_runtime_execution_authorized", "credential_loading_authorized",
        "systemd_access_authorized", "network_authorized", "runtime_activation_authorized",
        "publication_authorized",
    ):
        assert getattr(record, name) is False
    assert record.fail_closed is True


def test_public_records_are_immutable_slotted_and_readiness_only() -> None:
    records = (_policy(), _runtime(), _registration(), _installation(), _restoration(), _dispatch(),
               _shutdown(), _exit(), _service(), _deployment(), _execution(), _evidence(),
               _operator(), _reviewer(), _checklist())
    for record in records:
        _frozen(record)
    for record_type in (
        ProductionHostSignalServiceReadinessFailureV1, ProductionHostSignalServiceReadinessDecisionV1,
        ProductionHostSignalServiceReadinessAuditEvidenceV1,
    ):
        assert hasattr(record_type, "__dataclass_fields__")


def test_aligned_readiness_is_design_ready_only_for_separate_decisions() -> None:
    decision = _evaluate()
    _frozen(decision)
    assert decision.ready is True
    assert decision.decision_classification == (
        "PRODUCTION_HOST_SIGNAL_AND_SERVICE_EXECUTION_READY_FOR_SEPARATE_IMPLEMENTATION_AND_EXECUTION_DECISIONS"
    )
    assert decision.failure_codes == ()
    assert decision.states == (
        "PRODUCTION_HOST_SIGNAL_READINESS_DESIGN_AUTHORIZED",
        "PRODUCTION_HOST_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
        "MAIN_THREAD_REGISTRATION_READINESS_COMPLETE", "DIRECT_HOST_REGISTRATION_NOT_AUTHORIZED",
        "HANDLER_INSTALLATION_READINESS_COMPLETE", "HANDLER_INSTALLATION_NOT_AUTHORIZED",
        "HANDLER_RESTORATION_READINESS_COMPLETE", "HANDLER_RESTORATION_EXECUTION_NOT_AUTHORIZED",
        "PROCESS_EXIT_READINESS_COMPLETE", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED",
        "SYSTEMD_SERVICE_EXECUTION_READINESS_COMPLETE", "SERVICE_EXECUTION_NOT_AUTHORIZED",
        "SERVICE_UNIT_NOT_INSTALLED", "CREDENTIAL_NOT_ENTERED", "PRODUCTION_RUNTIME_NOT_AUTHORIZED",
        "DEPLOYMENT_BLOCKED", "ACTIVATION_GATE_CLOSED", "CREDENTIAL_GATE_CLOSED",
        "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED",
    )
    _assert_closed(decision)


@pytest.mark.parametrize(
    ("overrides", "failure_code"),
    (
        ({"policy": _policy(policy_id="")}, "POLICY_ID_EMPTY"),
        ({"policy": _policy(production_host_global_signal_readiness_design_authorized=False)}, "PRODUCTION_HOST_SIGNAL_READINESS_DESIGN_NOT_AUTHORIZED"),
        ({"policy": _policy(production_host_global_signal_implementation_authorized=True)}, "PRODUCTION_HOST_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED"),
        ({"runtime_identity": _runtime(isolated_adapter_green=False)}, "ISOLATED_SIGNAL_ADAPTER_GREEN_REQUIRED"),
        ({"runtime_identity": _runtime(supported_signal_names=("SIGTERM",))}, "SIGNAL_SET_MISMATCH"),
        ({"registration_readiness": _registration(caller_supplied_main_thread_contract_green=False)}, "MAIN_THREAD_REGISTRATION_REQUIRED"),
        ({"registration_readiness": _registration(duplicate_registration_prohibited=False)}, "DUPLICATE_REGISTRATION_NOT_ALLOWED"),
        ({"registration_readiness": _registration(partial_registration_rollback_green=False)}, "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED"),
        ({"installation_readiness": _installation(filesystem_access_allowed=True)}, "HANDLER_IO_NOT_AUTHORIZED"),
        ({"restoration_readiness": _restoration(restoration_order=("SIGTERM", "SIGINT"))}, "HANDLER_RESTORATION_ORDER_INVALID"),
        ({"shutdown_readiness": _shutdown(shutdown_timeout_seconds=0)}, "SHUTDOWN_TIMEOUT_REQUIRED"),
        ({"exit_readiness": _exit(exit_codes=(40, 40))}, "PROCESS_EXIT_CLASSIFICATION_OVERLAP"),
        ({"service_identity": _service(service_unit="other.service")}, "SERVICE_UNIT_MISMATCH"),
        ({"deployment_prerequisites": _deployment(deployment_prerequisites_documented=False)}, "DEPLOYMENT_PREREQUISITES_INCOMPLETE"),
        ({"service_execution_readiness": _execution(systemd_access_authorized=True)}, "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        ({"operator_attestation": None}, "OPERATOR_ATTESTATION_REQUIRED"),
        ({"reviewer_approval": None}, "REVIEWER_APPROVAL_REQUIRED"),
        ({"reviewer_approval": _reviewer(reviewer_identity="operator-v1")}, "OPERATOR_REVIEWER_COLLISION"),
        ({"operator_attestation": _operator(attested_at=_NOW + timedelta(seconds=1))}, "EVIDENCE_FROM_FUTURE"),
        ({"reviewer_approval": _reviewer(expires_at=_NOW - timedelta(seconds=1))}, "EVIDENCE_EXPIRED"),
    ),
)
def test_readiness_rejections_are_fail_closed_and_deterministically_ordered(
    overrides: dict[str, object], failure_code: str,
) -> None:
    decision = _evaluate(**overrides)
    assert decision.ready is False
    assert decision.decision_classification == "NOT_READY"
    assert failure_code in decision.failure_codes
    assert tuple(item.failure_code for item in decision.failures) == decision.failure_codes
    assert tuple(sorted(decision.failure_codes, key=_FAILURES.index)) == decision.failure_codes
    _assert_closed(decision)


def test_audit_evidence_is_redacted_and_preserves_execution_blocking() -> None:
    decision = _evaluate()
    evidence = build_production_host_signal_service_execution_readiness_audit_evidence_v1(
        audit_evidence_id="production-readiness-audit-v1", policy=_policy(), runtime_identity=_runtime(),
        registration_readiness=_registration(), handler_installation_readiness=_installation(),
        handler_restoration_readiness=_restoration(), dispatch_readiness=_dispatch(),
        shutdown_readiness=_shutdown(), exit_readiness=_exit(), service_identity=_service(),
        deployment_prerequisites=_deployment(), service_execution_readiness=_execution(),
        lifecycle_evidence=_evidence(), checklist=_checklist(), operator_attestation=_operator(),
        reviewer_approval=_reviewer(), decision=decision, evaluation_time=_NOW,
    )
    _frozen(evidence)
    assert evidence.ready_for_separate_implementation_and_execution_decisions is True
    assert evidence.process_exit_execution_authorized is False
    assert evidence.service_execution_authorized is False
    assert evidence.failure_codes == ()
    assert "0x" not in repr(evidence)
    _assert_closed(evidence)
