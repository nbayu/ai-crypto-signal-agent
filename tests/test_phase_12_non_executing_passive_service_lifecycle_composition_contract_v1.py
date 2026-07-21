"""RED contract for non-executing passive lifecycle composition."""
from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from engine.phase_12_non_executing_passive_service_lifecycle_composition_contract_v1 import (
    NonExecutingGracefulShutdownMetadataV1, NonExecutingHandlerRestorationMetadataV1,
    NonExecutingHostSignalMetadataV1, NonExecutingPassiveCliMetadataV1,
    NonExecutingPassiveLifecycleAuditEvidenceV1, NonExecutingPassiveLifecycleCompositionRequestV1,
    NonExecutingPassiveLifecycleCompositionResultV1, NonExecutingPassiveLifecycleFailureV1,
    NonExecutingPassiveLifecycleIdentityV1, NonExecutingPassiveLifecyclePolicyV1,
    NonExecutingPassiveLifecycleStateV1, NonExecutingPassiveLifecycleTransitionV1,
    NonExecutingProcessExitCompositionV1, NonExecutingSystemdLifecycleResultV1,
    build_non_executing_passive_service_lifecycle_audit_evidence_v1,
    compose_non_executing_passive_service_lifecycle_v1,
    evaluate_non_executing_passive_service_lifecycle_v1,
    transition_non_executing_passive_service_lifecycle_v1,
)


_ORDER = ("POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PASSIVE_LIFECYCLE_COMPOSITION_IMPLEMENTATION_NOT_AUTHORIZED", "PASSIVE_CLI_METADATA_COMPOSITION_NOT_AUTHORIZED", "HOST_SIGNAL_METADATA_COMPOSITION_NOT_AUTHORIZED", "GRACEFUL_SHUTDOWN_ORCHESTRATION_NOT_AUTHORIZED", "HANDLER_RESTORATION_EXIT_ORDERING_NOT_AUTHORIZED", "PROCESS_EXIT_COMPOSITION_NOT_AUTHORIZED", "SYSTEMD_LIFECYCLE_RESULT_NOT_AUTHORIZED", "LIFECYCLE_AUDIT_NOT_AUTHORIZED", "NON_EXECUTING_METADATA_COMPOSITION_MODE_REQUIRED", "COMPONENT_ADAPTER_INVOCATION_NOT_AUTHORIZED", "PASSIVE_CLI_ARGUMENT_MISMATCH", "PASSIVE_MODE_REQUIRED", "LAUNCHER_MODULE_MISMATCH", "PASSIVE_CLI_ADAPTER_MODULE_MISMATCH", "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED", "PASSIVE_CLI_EXECUTION_NOT_AUTHORIZED", "PASSIVE_LAUNCHER_EXECUTION_NOT_AUTHORIZED", "HOST_SIGNAL_BOUNDARY_GREEN_REQUIRED", "MAIN_THREAD_METADATA_REQUIRED", "SIGNAL_SET_MISMATCH", "PREVIOUS_HANDLER_REDACTION_REQUIRED", "PARTIAL_ROLLBACK_READINESS_REQUIRED", "HANDLER_RESTORATION_ORDER_INVALID", "STANDARD_LIBRARY_SIGNAL_ACCESS_NOT_AUTHORIZED", "DIRECT_SIGNAL_REGISTRATION_NOT_AUTHORIZED", "REAL_HOST_HANDLER_MUTATION_NOT_AUTHORIZED", "ACTUAL_SIGNAL_TRANSMISSION_NOT_AUTHORIZED", "GRACEFUL_SHUTDOWN_REQUIRED", "BOUNDED_SHUTDOWN_REQUIRED", "SHUTDOWN_ORDER_INVALID", "SHUTDOWN_NOT_IDEMPOTENT", "FORCED_KILL_NOT_AUTHORIZED", "HANDLER_RESTORATION_REQUIRED", "HANDLER_RESTORATION_INCOMPLETE", "EXIT_CLASSIFICATION_BEFORE_RESTORATION", "RAW_HANDLER_REPRESENTATION_EXPOSURE_DETECTED", "PROCESS_EXIT_BOUNDARY_GREEN_REQUIRED", "BARE_INTEGER_RESULT_NOT_ALLOWED")

def _frozen(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen
    assert "__dict__" not in type(value).__slots__

def _policy(**overrides: object) -> NonExecutingPassiveLifecyclePolicyV1:
    values = dict(policy_id="non-executing-lifecycle-policy-v1", policy_version="V1", passive_service_lifecycle_composition_implementation_authorized=True, passive_cli_metadata_composition_implementation_authorized=True, host_signal_metadata_composition_implementation_authorized=True, graceful_shutdown_orchestration_implementation_authorized=True, handler_restoration_to_exit_ordering_implementation_authorized=True, non_executing_process_exit_composition_implementation_authorized=True, systemd_compatible_lifecycle_result_implementation_authorized=True, lifecycle_integration_audit_implementation_authorized=True, non_executing_caller_supplied_metadata_composition_only=True, strict_lifecycle_ordering_required=True, handler_restoration_before_exit_required=True, component_adapter_invocation_prohibited=True, operating_system_exit_return_prohibited=True, fail_closed=True, passive_cli_execution_authorized=False, passive_launcher_execution_authorized=False, implicit_sys_argv_access_authorized=False, environment_read_authorized=False, filesystem_read_authorized=False, filesystem_write_authorized=False, component_adapter_invocation_authorized=False, production_host_signal_implementation_expansion_authorized=False, direct_standard_library_signal_registration_authorized=False, real_host_handler_installation_authorized=False, real_host_handler_restoration_authorized=False, actual_signal_transmission_authorized=False, operating_system_exit_code_return_authorized=False, production_process_exit_execution_authorized=False, process_termination_authorized=False, process_signal_transmission_authorized=False, sys_exit_authorized=False, system_exit_authorized=False, os_exit_authorized=False, kill_or_raise_signal_authorized=False, production_service_execution_authorized=False, production_runtime_execution_authorized=False, credential_access_authorized=False, credential_loading_authorized=False, credential_validation_authorized=False, systemd_access_authorized=False, systemd_unit_generation_authorized=False, systemd_drop_in_generation_authorized=False, service_installation_authorized=False, daemon_reload_authorized=False, service_enablement_authorized=False, service_start_restart_authorized=False, provider_transmission_authorized=False, scanner_execution_authorized=False, worker_start_authorized=False, scheduler_start_authorized=False, telegram_start_authorized=False, database_mutation_authorized=False, artifact_publication_authorized=False, trading_authorized=False, subprocess_authorized=False, thread_creation_authorized=False, event_loop_start_authorized=False, runtime_activation_authorized=False, publication_authorized=False, activation_gate_open=False, credential_gate_open=False, network_gate_open=False, workload_gate_open=False)
    return NonExecutingPassiveLifecyclePolicyV1(**(values | overrides))

def _request(**overrides: object) -> NonExecutingPassiveLifecycleCompositionRequestV1:
    values = dict(request_id="non-executing-lifecycle-request-v1", timestamp="2026-01-01T00:00:00Z", lifecycle_order=("POLICY_VALIDATED", "PASSIVE_CLI_METADATA_VALIDATED", "HOST_SIGNAL_METADATA_VALIDATED", "PASSIVE_READY", "SHUTDOWN_REQUESTED", "GRACEFUL_SHUTDOWN_COMPLETE", "HANDLER_RESTORATION_REQUIRED", "HANDLER_RESTORATION_COMPLETE", "EXIT_CLASSIFICATION_SELECTED", "SYSTEMD_RESULT_BUILT", "AUDIT_EVIDENCE_BUILT", "READY"))
    return NonExecutingPassiveLifecycleCompositionRequestV1(**(values | overrides))

def test_public_contract_is_immutable_and_slotted() -> None:
    for record in (_policy(), _request()): _frozen(record)
    for typ in (NonExecutingPassiveLifecycleIdentityV1, NonExecutingPassiveCliMetadataV1, NonExecutingHostSignalMetadataV1, NonExecutingGracefulShutdownMetadataV1, NonExecutingHandlerRestorationMetadataV1, NonExecutingProcessExitCompositionV1, NonExecutingSystemdLifecycleResultV1, NonExecutingPassiveLifecycleStateV1, NonExecutingPassiveLifecycleTransitionV1, NonExecutingPassiveLifecycleCompositionResultV1, NonExecutingPassiveLifecycleFailureV1, NonExecutingPassiveLifecycleAuditEvidenceV1): assert hasattr(typ, "__dataclass_fields__")

@pytest.mark.parametrize(("policy_case", "failure"), ((_policy(passive_cli_execution_authorized=True), "PASSIVE_CLI_EXECUTION_NOT_AUTHORIZED"), (_policy(component_adapter_invocation_authorized=True), "COMPONENT_ADAPTER_INVOCATION_NOT_AUTHORIZED"), (_policy(passive_service_lifecycle_composition_implementation_authorized=False), "PASSIVE_LIFECYCLE_COMPOSITION_IMPLEMENTATION_NOT_AUTHORIZED")))
def test_policy_escalations_fail_closed(policy_case: NonExecutingPassiveLifecyclePolicyV1, failure: str) -> None:
    result = evaluate_non_executing_passive_service_lifecycle_v1(policy=policy_case, request=_request())
    assert result.ready is False
    assert failure in result.failure_codes
    assert tuple(sorted(result.failure_codes, key=_ORDER.index)) == result.failure_codes

def test_composition_requires_metadata_only_chain_and_never_returns_a_bare_integer() -> None:
    result = compose_non_executing_passive_service_lifecycle_v1(policy=_policy(), request=_request())
    _frozen(result)
    assert not isinstance(result, int)
    assert result.ready is True
    assert result.composition_classification == "NON_EXECUTING_PASSIVE_SERVICE_LIFECYCLE_COMPOSITION_COMPLETE"
    assert result.operating_system_exit_code_returned is False
    assert result.process_exit_executed is False
    assert result.systemd_contacted is False
    transition = transition_non_executing_passive_service_lifecycle_v1(result=result, transition_id="lifecycle-transition-v1", target_state="READY")
    assert transition.current_state.state_code == "READY"
    evidence = build_non_executing_passive_service_lifecycle_audit_evidence_v1(evidence_id="lifecycle-evidence-v1", result=result, transition=transition)
    _frozen(evidence)
    assert "0x" not in repr(evidence)
