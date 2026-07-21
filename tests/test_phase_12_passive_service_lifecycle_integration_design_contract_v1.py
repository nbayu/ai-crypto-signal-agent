"""RED metadata contract for passive service lifecycle integration design."""
from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from engine.phase_12_passive_service_lifecycle_integration_design_contract_v1 import (
    GracefulShutdownOrchestrationV1,
    HandlerRestorationExitOrderingV1,
    HostSignalBoundaryCompositionV1,
    NonExecutingProcessExitIntegrationV1,
    PassiveCliLifecycleCompositionV1,
    PassiveServiceLifecycleAuditEvidenceV1,
    PassiveServiceLifecycleChecklistV1,
    PassiveServiceLifecycleDecisionV1,
    PassiveServiceLifecycleFailureV1,
    PassiveServiceLifecycleIdentityV1,
    PassiveServiceLifecycleIndependentReviewerApprovalV1,
    PassiveServiceLifecycleIntegrationPolicyV1,
    PassiveServiceLifecycleOperatorAttestationV1,
    PassiveServiceLifecycleStateV1,
    PassiveServiceLifecycleTransitionV1,
    SystemdCompatibleLifecycleResultV1,
    build_passive_service_lifecycle_audit_evidence_v1,
    compose_passive_service_lifecycle_without_execution_v1,
    evaluate_passive_service_lifecycle_integration_design_v1,
)

_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PASSIVE_SERVICE_LIFECYCLE_INTEGRATION_DESIGN_NOT_AUTHORIZED",
    "PASSIVE_CLI_COMPOSITION_DESIGN_NOT_AUTHORIZED", "HOST_SIGNAL_COMPOSITION_DESIGN_NOT_AUTHORIZED",
    "GRACEFUL_SHUTDOWN_ORCHESTRATION_DESIGN_NOT_AUTHORIZED", "HANDLER_RESTORATION_EXIT_ORDERING_DESIGN_NOT_AUTHORIZED",
    "PROCESS_EXIT_INTEGRATION_DESIGN_NOT_AUTHORIZED", "SYSTEMD_LIFECYCLE_RESULT_DESIGN_NOT_AUTHORIZED",
    "LIFECYCLE_EVIDENCE_PACKAGE_DESIGN_NOT_AUTHORIZED", "PASSIVE_SERVICE_LIFECYCLE_IMPLEMENTATION_NOT_AUTHORIZED",
    "HOST_SIGNAL_IMPLEMENTATION_EXPANSION_NOT_AUTHORIZED", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED",
    "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED",
    "PASSIVE_CLI_ARGUMENT_MISMATCH", "PASSIVE_MODE_REQUIRED", "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED",
    "PASSIVE_LAUNCHER_EXECUTION_NOT_AUTHORIZED", "HOST_SIGNAL_BOUNDARY_GREEN_REQUIRED",
    "MAIN_THREAD_METADATA_REQUIRED", "SIGNAL_SET_MISMATCH", "PREVIOUS_HANDLER_REDACTION_REQUIRED",
    "PARTIAL_ROLLBACK_READINESS_REQUIRED", "HANDLER_RESTORATION_ORDER_INVALID", "GRACEFUL_SHUTDOWN_REQUIRED",
    "BOUNDED_SHUTDOWN_REQUIRED", "SHUTDOWN_ORDER_INVALID", "SHUTDOWN_NOT_IDEMPOTENT",
    "FORCED_KILL_NOT_AUTHORIZED", "HANDLER_RESTORATION_REQUIRED", "HANDLER_RESTORATION_INCOMPLETE",
    "EXIT_CLASSIFICATION_BEFORE_RESTORATION", "RAW_HANDLER_REPRESENTATION_EXPOSURE_DETECTED",
    "PROCESS_EXIT_BOUNDARY_GREEN_REQUIRED", "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED",
    "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED", "PROCESS_TERMINATION_NOT_AUTHORIZED",
    "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED", "BARE_INTEGER_LIFECYCLE_RESULT_NOT_ALLOWED",
    "SERVICE_UNIT_MISMATCH", "SERVICE_MANAGER_SCOPE_MISMATCH", "DEPLOYMENT_STATE_MISMATCH",
    "SYSTEMD_ACCESS_NOT_AUTHORIZED", "SERVICE_INSTALLATION_NOT_AUTHORIZED", "SERVICE_ENABLEMENT_NOT_AUTHORIZED",
    "SERVICE_START_NOT_AUTHORIZED", "SERVICE_EXECUTION_NOT_AUTHORIZED", "SYSTEMD_RESTART_ACTION_NOT_AUTHORIZED",
    "SYSTEMD_WATCHDOG_ACTION_NOT_AUTHORIZED", "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "SUBPROCESS_NOT_AUTHORIZED", "THREAD_CREATION_NOT_AUTHORIZED", "EVENT_LOOP_START_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION",
    "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "PROVIDER_MATERIAL_EXPOSURE_DETECTED", "PROCESS_METADATA_EXPOSURE_DETECTED", "SYSTEMD_HANDLE_EXPOSURE_DETECTED",
    "AUTHORIZATION_MATERIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> PassiveServiceLifecycleIntegrationPolicyV1:
    values = dict(
        policy_id="passive-lifecycle-policy-v1", policy_version="V1",
        passive_service_lifecycle_integration_design_authorized=True,
        passive_cli_lifecycle_composition_design_authorized=True, host_signal_boundary_composition_design_authorized=True,
        graceful_shutdown_orchestration_design_authorized=True, handler_restoration_to_exit_ordering_design_authorized=True,
        non_executing_process_exit_integration_design_authorized=True, systemd_compatible_lifecycle_result_design_authorized=True,
        lifecycle_integration_evidence_package_design_authorized=True, metadata_only_composition=True,
        caller_supplied_inputs_only=True, strict_ordering_required=True, handler_restoration_before_exit_required=True,
        non_executing_exit_classification_required=True, fail_closed=True,
        passive_service_lifecycle_implementation_authorized=False, production_host_signal_implementation_expansion_authorized=False,
        direct_standard_library_signal_registration_authorized=False, real_host_handler_installation_authorized=False,
        real_host_handler_restoration_authorized=False, actual_signal_transmission_authorized=False,
        operating_system_exit_code_return_authorized=False, production_process_exit_execution_authorized=False,
        process_termination_authorized=False, process_signal_transmission_authorized=False,
        production_cli_execution_authorized=False, production_service_execution_authorized=False,
        production_runtime_execution_authorized=False, implicit_sys_argv_access_authorized=False,
        environment_read_authorized=False, filesystem_read_authorized=False, filesystem_write_authorized=False,
        credential_access_authorized=False, credential_loading_authorized=False, credential_validation_authorized=False,
        systemd_access_authorized=False, service_installation_authorized=False, daemon_reload_authorized=False,
        service_enablement_authorized=False, service_start_restart_authorized=False, provider_transmission_authorized=False,
        scanner_execution_authorized=False, worker_start_authorized=False, scheduler_start_authorized=False,
        telegram_start_authorized=False, database_mutation_authorized=False, artifact_publication_authorized=False,
        trading_authorized=False, subprocess_authorized=False, thread_creation_authorized=False,
        event_loop_start_authorized=False, runtime_activation_authorized=False, publication_authorized=False,
        activation_gate_open=False, credential_gate_open=False, network_gate_open=False, workload_gate_open=False,
    )
    return PassiveServiceLifecycleIntegrationPolicyV1(**(values | overrides))


def _identity() -> PassiveServiceLifecycleIdentityV1:
    return PassiveServiceLifecycleIdentityV1(lifecycle_id="passive-lifecycle-v1", service_unit="ai-crypto-signal-agent.service", service_manager_scope="SYSTEM", deployment_state="NOT_YET_INSTALLED")


def _cli(**overrides: object) -> PassiveCliLifecycleCompositionV1:
    values = dict(composition_id="passive-cli-composition-v1", passive_cli_arguments=("--mode", "passive"), passive_mode_selected=True, implicit_sys_argv_used=False, cli_executed=False, launcher_executed=False, launcher_module="engine.phase_12_passive_runtime_launcher_executable_contract_v1", cli_adapter_module="engine.phase_12_passive_production_cli_real_signal_adapter_contract_v1")
    return PassiveCliLifecycleCompositionV1(**(values | overrides))


def _signal(**overrides: object) -> HostSignalBoundaryCompositionV1:
    values = dict(composition_id="host-signal-composition-v1", step_89_green=True, dependency_injected_adapter_green=True, main_thread_metadata_green=True, signal_names=("SIGTERM", "SIGINT"), sighup_classification="RELOAD_NOT_AUTHORIZED", unknown_classification="UNKNOWN_HOST_GLOBAL_SIGNAL", previous_handler_redaction_green=True, rollback_readiness_green=True, restoration_order=("SIGINT", "SIGTERM"), signal_imported=False, direct_registration=False, real_handler_mutation=False, signal_transmitted=False)
    return HostSignalBoundaryCompositionV1(**(values | overrides))


def _shutdown() -> GracefulShutdownOrchestrationV1:
    return GracefulShutdownOrchestrationV1(shutdown_id="graceful-shutdown-v1", bounded_shutdown_metadata_present=True, deterministic_order=True, repeated_shutdown_idempotent=True, passive_resource_set_empty=True, pending_database_mutation_allowed=False, pending_publication_allowed=False, forced_kill_authorized=False, process_exit_authorized=False)


def _restoration(**overrides: object) -> HandlerRestorationExitOrderingV1:
    values = dict(restoration_id="restoration-ordering-v1", ordering=("GRACEFUL_SHUTDOWN_COMPLETE", "HANDLER_RESTORATION_REQUIRED", "SIGINT_RESTORED", "SIGTERM_RESTORED", "RESTORATION_EVIDENCE_COMPLETE", "EXIT_CLASSIFICATION_ELIGIBLE"), restoration_complete=True, restoration_execution_claimed=False, raw_handler_material_present=False)
    return HandlerRestorationExitOrderingV1(**(values | overrides))


def _exit() -> NonExecutingProcessExitIntegrationV1:
    return NonExecutingProcessExitIntegrationV1(integration_id="process-exit-integration-v1", step_93_green=True, selected_exit_classification="GRACEFUL_SIGTERM_SHUTDOWN_EXIT", selected_exit_code=1, operating_system_exit_code_returned=False, process_exit_executed=False, process_terminated=False, signal_transmitted=False, systemd_contacted=False, service_executed=False, production_runtime_executed=False)


def _systemd(**overrides: object) -> SystemdCompatibleLifecycleResultV1:
    values = dict(systemd_result_id="lifecycle-systemd-result-v1", service_unit="ai-crypto-signal-agent.service", service_manager_scope="SYSTEM", deployment_state="NOT_YET_INSTALLED", passive_default=True, selected_exit_classification="GRACEFUL_SIGTERM_SHUTDOWN_EXIT", selected_exit_code=1, systemd_compatible=True, systemd_contacted=False, service_installed=False, service_enabled=False, service_started=False, service_executed=False, restart_action_authorized=False, watchdog_action_authorized=False, operating_system_exit_code_returned=False)
    return SystemdCompatibleLifecycleResultV1(**(values | overrides))


def _checklist() -> PassiveServiceLifecycleChecklistV1:
    return PassiveServiceLifecycleChecklistV1(checklist_id="passive-lifecycle-checklist-v1", lifecycle_chain_complete=True, checklist_complete=True, all_gates_closed=True)


def _operator() -> PassiveServiceLifecycleOperatorAttestationV1:
    return PassiveServiceLifecycleOperatorAttestationV1(operator_id="lifecycle-operator-v1", operator_identity="operator-a", role_classification="PASSIVE_SERVICE_LIFECYCLE_OPERATOR", complete=True, timestamp="2026-01-01T00:00:00Z", expiry_timestamp="2026-12-31T00:00:00Z")


def _reviewer(**overrides: object) -> PassiveServiceLifecycleIndependentReviewerApprovalV1:
    values = dict(reviewer_id="lifecycle-reviewer-v1", reviewer_identity="reviewer-b", role_classification="INDEPENDENT_PASSIVE_SERVICE_LIFECYCLE_REVIEWER", complete=True, timestamp="2026-01-01T00:00:00Z", expiry_timestamp="2026-12-31T00:00:00Z")
    return PassiveServiceLifecycleIndependentReviewerApprovalV1(**(values | overrides))


def _closed(record: object) -> None:
    for name in ("activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open", "passive_service_lifecycle_implementation_authorized", "production_cli_execution_authorized", "operating_system_exit_code_return_authorized", "process_exit_execution_authorized", "systemd_access_authorized", "production_service_execution_authorized", "production_runtime_execution_authorized", "credential_loading_authorized", "runtime_activation_authorized", "publication_authorized"):
        assert getattr(record, name) is False
    assert record.fail_closed is True


def _decision() -> PassiveServiceLifecycleDecisionV1:
    return evaluate_passive_service_lifecycle_integration_design_v1(policy=_policy(), identity=_identity(), cli_composition=_cli(), signal_composition=_signal(), shutdown_orchestration=_shutdown(), restoration_ordering=_restoration(), process_exit_integration=_exit(), systemd_result=_systemd(), checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(), evidence_timestamp="2026-01-02T00:00:00Z", evidence_expiry_timestamp="2026-12-30T00:00:00Z")


def test_public_records_are_frozen_slotted_and_metadata_only() -> None:
    for record in (_policy(), _identity(), _cli(), _signal(), _shutdown(), _restoration(), _exit(), _systemd(), _checklist(), _operator(), _reviewer()): _frozen(record)
    for record_type in (PassiveServiceLifecycleStateV1, PassiveServiceLifecycleTransitionV1, PassiveServiceLifecycleFailureV1, PassiveServiceLifecycleDecisionV1, PassiveServiceLifecycleAuditEvidenceV1): assert hasattr(record_type, "__dataclass_fields__")


def test_complete_chain_is_ready_only_for_a_separate_implementation_decision() -> None:
    decision = _decision()
    assert decision.ready is True
    assert decision.decision_classification == "PASSIVE_SERVICE_LIFECYCLE_INTEGRATION_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION"
    assert decision.lifecycle_chain == ("PASSIVE_CLI_ARGUMENTS_VALIDATED", "PASSIVE_LAUNCHER_METADATA_VALIDATED", "HOST_SIGNAL_BOUNDARY_READY", "MAIN_THREAD_REGISTRATION_METADATA_READY", "HANDLER_INSTALLATION_METADATA_READY", "PASSIVE_SERVICE_READY", "SHUTDOWN_REQUESTED", "GRACEFUL_SHUTDOWN_COMPLETE", "HANDLER_RESTORATION_REQUIRED", "HANDLER_RESTORATION_COMPLETE", "NON_EXECUTING_EXIT_CLASSIFICATION_SELECTED", "SYSTEMD_COMPATIBLE_RESULT_BUILT", "LIFECYCLE_AUDIT_EVIDENCE_BUILT", "DESIGN_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION")
    _closed(decision)


@pytest.mark.parametrize(("cli_case", "signal_case", "restoration_case", "failure"), ((_cli(passive_cli_arguments=("--mode", "live")), _signal(), _restoration(), "PASSIVE_CLI_ARGUMENT_MISMATCH"), (_cli(implicit_sys_argv_used=True), _signal(), _restoration(), "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED"), (_cli(), _signal(step_89_green=False), _restoration(), "HOST_SIGNAL_BOUNDARY_GREEN_REQUIRED"), (_cli(), _signal(signal_names=("SIGTERM",)), _restoration(), "SIGNAL_SET_MISMATCH"), (_cli(), _signal(), _restoration(restoration_complete=False), "HANDLER_RESTORATION_INCOMPLETE")))
def test_invalid_composition_metadata_fails_closed_deterministically(cli_case: PassiveCliLifecycleCompositionV1, signal_case: HostSignalBoundaryCompositionV1, restoration_case: HandlerRestorationExitOrderingV1, failure: str) -> None:
    decision = evaluate_passive_service_lifecycle_integration_design_v1(policy=_policy(), identity=_identity(), cli_composition=cli_case, signal_composition=signal_case, shutdown_orchestration=_shutdown(), restoration_ordering=restoration_case, process_exit_integration=_exit(), systemd_result=_systemd(), checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(), evidence_timestamp="2026-01-02T00:00:00Z", evidence_expiry_timestamp="2026-12-30T00:00:00Z")
    assert decision.ready is False
    assert failure in decision.failure_codes
    assert tuple(sorted(decision.failure_codes, key=_ORDER.index)) == decision.failure_codes
    _closed(decision)


def test_composition_and_audit_never_execute_any_component() -> None:
    decision = _decision()
    composition = compose_passive_service_lifecycle_without_execution_v1(decision=decision, composition_id="passive-lifecycle-composition-v1")
    assert not isinstance(composition, int)
    assert composition.operating_system_exit_code_returned is False
    assert composition.process_exit_executed is False
    assert composition.systemd_contacted is False
    evidence = build_passive_service_lifecycle_audit_evidence_v1(evidence_id="passive-lifecycle-evidence-v1", decision=decision, composition=composition)
    _frozen(evidence)
    assert "0x" not in repr(evidence)
    _closed(evidence)
