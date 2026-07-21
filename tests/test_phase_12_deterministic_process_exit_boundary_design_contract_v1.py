"""RED metadata contract for deterministic, non-executing process-exit design."""
from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from engine.phase_12_deterministic_process_exit_boundary_design_contract_v1 import (
    DeterministicExitCodeIdentityV1,
    DeterministicExitCodeSetV1,
    DeterministicProcessExitBoundaryPolicyV1,
    FailClosedExitMappingV1,
    GracefulShutdownExitMappingV1,
    ProcessExitBoundaryAuditEvidenceV1,
    ProcessExitBoundaryChecklistV1,
    ProcessExitBoundaryDecisionV1,
    ProcessExitBoundaryFailureV1,
    ProcessExitClassificationRequestV1,
    ProcessExitClassificationResultV1,
    ProcessExitIndependentReviewerApprovalV1,
    ProcessExitOperatorAttestationV1,
    SystemdExitStatusCompatibilityV1,
    build_deterministic_process_exit_boundary_audit_evidence_v1,
    classify_process_exit_without_execution_v1,
    evaluate_deterministic_process_exit_boundary_design_v1,
)


_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PROCESS_EXIT_BOUNDARY_DESIGN_NOT_AUTHORIZED",
    "EXIT_CODE_CLASSIFICATION_DESIGN_NOT_AUTHORIZED", "GRACEFUL_SHUTDOWN_EXIT_MAPPING_DESIGN_NOT_AUTHORIZED",
    "FAIL_CLOSED_EXIT_MAPPING_DESIGN_NOT_AUTHORIZED", "SYSTEMD_EXIT_STATUS_COMPATIBILITY_DESIGN_NOT_AUTHORIZED",
    "PROCESS_EXIT_AUDIT_EVIDENCE_DESIGN_NOT_AUTHORIZED", "PRODUCTION_PROCESS_EXIT_IMPLEMENTATION_NOT_AUTHORIZED",
    "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED", "PROCESS_TERMINATION_NOT_AUTHORIZED",
    "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED", "SYS_EXIT_NOT_AUTHORIZED", "SYSTEM_EXIT_NOT_AUTHORIZED",
    "OS_EXIT_NOT_AUTHORIZED", "KILL_OR_RAISE_SIGNAL_NOT_AUTHORIZED", "EXIT_CODE_SET_ID_EMPTY",
    "EXIT_CLASSIFICATION_MISSING", "EXIT_CODE_NOT_INTEGER", "EXIT_CODE_NEGATIVE", "EXIT_CODE_OVERLAP",
    "EXIT_CODE_OUTSIDE_SYSTEMD_COMPATIBLE_RANGE", "MAPPING_ID_EMPTY", "SOURCE_STATE_EMPTY",
    "UNKNOWN_SOURCE_STATE", "UNSUPPORTED_SIGNAL_CONTEXT", "GRACEFUL_SHUTDOWN_MAPPING_INCOMPLETE",
    "FAIL_CLOSED_MAPPING_INCOMPLETE", "INTERNAL_FAIL_CLOSED_MAPPING_REQUIRED",
    "SYSTEMD_COMPATIBILITY_EVIDENCE_REQUIRED", "SYSTEMD_ACCESS_NOT_AUTHORIZED",
    "SYSTEMD_RESTART_ACTION_NOT_AUTHORIZED", "SERVICE_EXECUTION_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "SUBPROCESS_NOT_AUTHORIZED", "THREAD_CREATION_NOT_AUTHORIZED", "EVENT_LOOP_START_NOT_AUTHORIZED",
    "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "PUBLICATION_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED",
    "WORKLOAD_GATE_MUST_REMAIN_CLOSED", "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED",
    "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE", "EVIDENCE_EXPIRED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_MATERIAL_EXPOSURE_DETECTED",
    "PROCESS_METADATA_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
    "AUTHORIZATION_MATERIAL_EXPOSURE_DETECTED",
)

_CLASSIFICATIONS = (
    "PASSIVE_SERVICE_READY_EXIT", "GRACEFUL_SIGTERM_SHUTDOWN_EXIT", "GRACEFUL_SIGINT_SHUTDOWN_EXIT",
    "CLI_CONFIGURATION_BLOCKED_EXIT", "HOST_SIGNAL_REGISTRATION_BLOCKED_EXIT",
    "HANDLER_INSTALLATION_BLOCKED_EXIT", "HANDLER_RESTORATION_BLOCKED_EXIT",
    "GRACEFUL_SHUTDOWN_BLOCKED_EXIT", "SERVICE_DEPLOYMENT_BLOCKED_EXIT",
    "SERVICE_EXECUTION_NOT_AUTHORIZED_EXIT", "CREDENTIAL_LOADING_NOT_AUTHORIZED_EXIT",
    "NETWORK_NOT_AUTHORIZED_EXIT", "WORKLOAD_NOT_AUTHORIZED_EXIT", "RUNTIME_NOT_AUTHORIZED_EXIT",
    "INTERNAL_FAIL_CLOSED_EXIT",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> DeterministicProcessExitBoundaryPolicyV1:
    values = dict(
        policy_id="deterministic-process-exit-policy-v1", policy_version="V1",
        production_process_exit_boundary_design_authorized=True,
        deterministic_exit_code_classification_design_authorized=True,
        graceful_shutdown_to_exit_mapping_design_authorized=True,
        fail_closed_exit_mapping_design_authorized=True,
        systemd_exit_status_compatibility_design_authorized=True,
        process_exit_audit_evidence_design_authorized=True, unique_exit_codes_required=True,
        caller_supplied_exit_codes_required=True, non_executing_classification_only=True, fail_closed=True,
        production_process_exit_implementation_authorized=False, process_exit_execution_authorized=False,
        process_termination_authorized=False, process_signal_transmission_authorized=False,
        sys_exit_authorized=False, system_exit_authorized=False, os_exit_authorized=False,
        kill_or_raise_signal_authorized=False, standard_library_signal_access_authorized=False,
        real_host_handler_installation_authorized=False, real_host_handler_restoration_authorized=False,
        actual_signal_transmission_authorized=False, production_cli_execution_authorized=False,
        production_service_execution_authorized=False, production_runtime_execution_authorized=False,
        implicit_sys_argv_access_authorized=False, environment_read_authorized=False,
        filesystem_read_authorized=False, filesystem_write_authorized=False,
        credential_access_authorized=False, credential_loading_authorized=False,
        credential_validation_authorized=False, systemd_access_authorized=False, network_authorized=False,
        provider_transmission_authorized=False, scanner_execution_authorized=False,
        worker_start_authorized=False, scheduler_start_authorized=False, telegram_start_authorized=False,
        database_mutation_authorized=False, artifact_publication_authorized=False, trading_authorized=False,
        subprocess_authorized=False, thread_creation_authorized=False, event_loop_start_authorized=False,
        runtime_activation_authorized=False, publication_authorized=False, activation_gate_open=False,
        credential_gate_open=False, network_gate_open=False, workload_gate_open=False,
    )
    return DeterministicProcessExitBoundaryPolicyV1(**(values | overrides))


def _code_set(**overrides: object) -> DeterministicExitCodeSetV1:
    identities = tuple(
        DeterministicExitCodeIdentityV1(
            exit_code_id=f"exit-code-{index}-v1", classification=classification, code=index,
        )
        for index, classification in enumerate(_CLASSIFICATIONS)
    )
    values = dict(
        code_set_id="deterministic-exit-code-set-v1", exit_code_identities=identities,
        systemd_compatible_minimum=0, systemd_compatible_maximum=255,
    )
    return DeterministicExitCodeSetV1(**(values | overrides))


def _graceful_mapping(**overrides: object) -> GracefulShutdownExitMappingV1:
    values = dict(
        mapping_id="graceful-shutdown-exit-mapping-v1",
        mappings=(
            ("PASSIVE_READY", "", "PASSIVE_SERVICE_READY_EXIT"),
            ("GRACEFUL_SHUTDOWN_COMPLETE", "SIGTERM", "GRACEFUL_SIGTERM_SHUTDOWN_EXIT"),
            ("GRACEFUL_SHUTDOWN_COMPLETE", "SIGINT", "GRACEFUL_SIGINT_SHUTDOWN_EXIT"),
            ("CLI_CONFIGURATION_BLOCKED", "", "CLI_CONFIGURATION_BLOCKED_EXIT"),
            ("HOST_SIGNAL_REGISTRATION_BLOCKED", "", "HOST_SIGNAL_REGISTRATION_BLOCKED_EXIT"),
            ("HANDLER_INSTALLATION_BLOCKED", "", "HANDLER_INSTALLATION_BLOCKED_EXIT"),
            ("HANDLER_RESTORATION_BLOCKED", "", "HANDLER_RESTORATION_BLOCKED_EXIT"),
            ("GRACEFUL_SHUTDOWN_BLOCKED", "", "GRACEFUL_SHUTDOWN_BLOCKED_EXIT"),
            ("SERVICE_DEPLOYMENT_BLOCKED", "", "SERVICE_DEPLOYMENT_BLOCKED_EXIT"),
            ("SERVICE_EXECUTION_NOT_AUTHORIZED", "", "SERVICE_EXECUTION_NOT_AUTHORIZED_EXIT"),
            ("CREDENTIAL_LOADING_NOT_AUTHORIZED", "", "CREDENTIAL_LOADING_NOT_AUTHORIZED_EXIT"),
            ("NETWORK_NOT_AUTHORIZED", "", "NETWORK_NOT_AUTHORIZED_EXIT"),
            ("WORKLOAD_NOT_AUTHORIZED", "", "WORKLOAD_NOT_AUTHORIZED_EXIT"),
            ("RUNTIME_NOT_AUTHORIZED", "", "RUNTIME_NOT_AUTHORIZED_EXIT"),
        ),
    )
    return GracefulShutdownExitMappingV1(**(values | overrides))


def _fail_closed_mapping(**overrides: object) -> FailClosedExitMappingV1:
    values = dict(mapping_id="fail-closed-exit-mapping-v1", internal_fail_closed_classification="INTERNAL_FAIL_CLOSED_EXIT")
    return FailClosedExitMappingV1(**(values | overrides))


def _compatibility(**overrides: object) -> SystemdExitStatusCompatibilityV1:
    values = dict(
        compatibility_id="systemd-exit-status-compatibility-v1", systemd_compatibility_documented=True,
        successful_passive_ready_classified=True, graceful_sigterm_classified=True,
        graceful_sigint_classified=True, fail_closed_blocked_classified=True,
        unique_exit_codes_required=True, signal_derived_termination_allowed=False,
        core_dump_classification_allowed=False, watchdog_trigger_classification_allowed=False,
        restart_action_authorized=False, systemd_access_authorized=False,
        service_execution_authorized=False,
    )
    return SystemdExitStatusCompatibilityV1(**(values | overrides))


def _checklist(**overrides: object) -> ProcessExitBoundaryChecklistV1:
    values = dict(
        checklist_id="process-exit-checklist-v1", unique_codes_validated=True,
        graceful_mapping_complete=True, fail_closed_mapping_complete=True,
        systemd_compatibility_complete=True, process_exit_execution_unauthorized=True,
        all_gates_closed=True, checklist_complete=True,
    )
    return ProcessExitBoundaryChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> ProcessExitOperatorAttestationV1:
    values = dict(
        operator_id="exit-operator-v1", operator_identity="operator-a", role_classification="PROCESS_EXIT_OPERATOR",
        policy_id="deterministic-process-exit-policy-v1", code_set_id="deterministic-exit-code-set-v1",
        graceful_mapping_id="graceful-shutdown-exit-mapping-v1", fail_closed_mapping_id="fail-closed-exit-mapping-v1",
        compatibility_id="systemd-exit-status-compatibility-v1", checklist_id="process-exit-checklist-v1",
        evidence_id="process-exit-evidence-v1", timestamp="2026-01-01T00:00:00Z",
        expiry_timestamp="2026-12-31T00:00:00Z", complete=True,
    )
    return ProcessExitOperatorAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> ProcessExitIndependentReviewerApprovalV1:
    values = dict(
        reviewer_id="exit-reviewer-v1", reviewer_identity="reviewer-b", role_classification="INDEPENDENT_PROCESS_EXIT_REVIEWER",
        policy_id="deterministic-process-exit-policy-v1", code_set_id="deterministic-exit-code-set-v1",
        graceful_mapping_id="graceful-shutdown-exit-mapping-v1", fail_closed_mapping_id="fail-closed-exit-mapping-v1",
        compatibility_id="systemd-exit-status-compatibility-v1", checklist_id="process-exit-checklist-v1",
        evidence_id="process-exit-evidence-v1", timestamp="2026-01-01T00:00:00Z",
        expiry_timestamp="2026-12-31T00:00:00Z", complete=True,
    )
    return ProcessExitIndependentReviewerApprovalV1(**(values | overrides))


def _classification_request(state: str, signal_name: str = "") -> ProcessExitClassificationRequestV1:
    return ProcessExitClassificationRequestV1(
        classification_request_id="process-exit-classification-request-v1", timestamp="2026-01-01T00:00:00Z",
        source_lifecycle_state=state, source_signal_classification=signal_name,
        graceful_shutdown_complete=state == "GRACEFUL_SHUTDOWN_COMPLETE",
        handler_restoration_complete=True, deployment_state="NOT_YET_INSTALLED",
        service_execution_authorized=False, credential_gate_open=False, network_gate_open=False,
        workload_gate_open=False, activation_gate_open=False,
    )


def _closed(record: object) -> None:
    for field in (
        "activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open",
        "production_process_exit_implementation_authorized", "process_exit_execution_authorized",
        "process_termination_authorized", "process_signal_transmission_authorized", "sys_exit_authorized",
        "system_exit_authorized", "os_exit_authorized", "kill_or_raise_signal_authorized",
        "production_service_execution_authorized", "production_runtime_execution_authorized",
        "credential_loading_authorized", "systemd_access_authorized", "network_authorized",
        "runtime_activation_authorized", "publication_authorized",
    ):
        assert getattr(record, field) is False
    assert record.fail_closed is True


def _decision() -> ProcessExitBoundaryDecisionV1:
    return evaluate_deterministic_process_exit_boundary_design_v1(
        policy=_policy(), exit_code_set=_code_set(), graceful_shutdown_mapping=_graceful_mapping(),
        fail_closed_mapping=_fail_closed_mapping(), systemd_compatibility=_compatibility(),
        checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(),
        evidence_timestamp="2026-01-02T00:00:00Z", evidence_expiry_timestamp="2026-12-30T00:00:00Z",
    )


def test_public_records_are_frozen_slotted_and_static() -> None:
    for record in (_policy(), _code_set(), _graceful_mapping(), _fail_closed_mapping(), _compatibility(), _checklist(), _operator(), _reviewer(), _classification_request("PASSIVE_READY")):
        _frozen(record)
    for record_type in (ProcessExitClassificationResultV1, ProcessExitBoundaryFailureV1, ProcessExitBoundaryDecisionV1, ProcessExitBoundaryAuditEvidenceV1):
        assert hasattr(record_type, "__dataclass_fields__")


def test_complete_metadata_is_ready_only_for_a_separate_implementation_decision() -> None:
    decision = _decision()
    _frozen(decision)
    assert decision.ready is True
    assert decision.decision_classification == "DETERMINISTIC_PROCESS_EXIT_BOUNDARY_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION"
    assert decision.failure_codes == ()
    _closed(decision)


@pytest.mark.parametrize(
    ("policy_case", "failure_code"),
    (
        (_policy(production_process_exit_boundary_design_authorized=False), "PROCESS_EXIT_BOUNDARY_DESIGN_NOT_AUTHORIZED"),
        (_policy(process_exit_execution_authorized=True), "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
        (_policy(process_termination_authorized=True), "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        (_policy(systemd_access_authorized=True), "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        (_policy(credential_loading_authorized=True), "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        (_policy(network_gate_open=True), "NETWORK_GATE_MUST_REMAIN_CLOSED"),
    ),
)
def test_policy_escalations_fail_closed_deterministically(
    policy_case: DeterministicProcessExitBoundaryPolicyV1, failure_code: str,
) -> None:
    decision = evaluate_deterministic_process_exit_boundary_design_v1(
        policy=policy_case, exit_code_set=_code_set(), graceful_shutdown_mapping=_graceful_mapping(),
        fail_closed_mapping=_fail_closed_mapping(), systemd_compatibility=_compatibility(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evidence_timestamp="2026-01-02T00:00:00Z",
        evidence_expiry_timestamp="2026-12-30T00:00:00Z",
    )
    assert decision.ready is False
    assert failure_code in decision.failure_codes
    assert tuple(sorted(decision.failure_codes, key=_FAILURES.index)) == decision.failure_codes
    _closed(decision)


@pytest.mark.parametrize(
    ("code_set_case", "failure_code"),
    (
        (_code_set(code_set_id=""), "EXIT_CODE_SET_ID_EMPTY"),
        (_code_set(exit_code_identities=(_code_set().exit_code_identities[0],) * len(_CLASSIFICATIONS)), "EXIT_CODE_OVERLAP"),
        (_code_set(exit_code_identities=(DeterministicExitCodeIdentityV1(exit_code_id="negative", classification="PASSIVE_SERVICE_READY_EXIT", code=-1),) + _code_set().exit_code_identities[1:]), "EXIT_CODE_NEGATIVE"),
        (_code_set(exit_code_identities=(DeterministicExitCodeIdentityV1(exit_code_id="non-integer", classification="PASSIVE_SERVICE_READY_EXIT", code="0"),) + _code_set().exit_code_identities[1:]), "EXIT_CODE_NOT_INTEGER"),
        (_code_set(systemd_compatible_maximum=3), "EXIT_CODE_OUTSIDE_SYSTEMD_COMPATIBLE_RANGE"),
    ),
)
def test_code_set_validation_rejects_nonunique_invalid_or_out_of_range_metadata(
    code_set_case: DeterministicExitCodeSetV1, failure_code: str,
) -> None:
    decision = evaluate_deterministic_process_exit_boundary_design_v1(
        policy=_policy(), exit_code_set=code_set_case, graceful_shutdown_mapping=_graceful_mapping(),
        fail_closed_mapping=_fail_closed_mapping(), systemd_compatibility=_compatibility(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evidence_timestamp="2026-01-02T00:00:00Z",
        evidence_expiry_timestamp="2026-12-30T00:00:00Z",
    )
    assert decision.ready is False
    assert failure_code in decision.failure_codes
    _closed(decision)


@pytest.mark.parametrize(
    ("state", "signal_name", "classification"),
    (
        ("PASSIVE_READY", "", "PASSIVE_SERVICE_READY_EXIT"),
        ("GRACEFUL_SHUTDOWN_COMPLETE", "SIGTERM", "GRACEFUL_SIGTERM_SHUTDOWN_EXIT"),
        ("GRACEFUL_SHUTDOWN_COMPLETE", "SIGINT", "GRACEFUL_SIGINT_SHUTDOWN_EXIT"),
        ("CLI_CONFIGURATION_BLOCKED", "", "CLI_CONFIGURATION_BLOCKED_EXIT"),
        ("NETWORK_NOT_AUTHORIZED", "", "NETWORK_NOT_AUTHORIZED_EXIT"),
        ("UNKNOWN_STATE", "", "INTERNAL_FAIL_CLOSED_EXIT"),
    ),
)
def test_classification_is_deterministic_and_never_executes_a_process_action(
    state: str, signal_name: str, classification: str,
) -> None:
    result = classify_process_exit_without_execution_v1(
        decision=_decision(), classification_request=_classification_request(state, signal_name),
    )
    _frozen(result)
    assert result.selected_exit_classification == classification
    assert isinstance(result.selected_exit_code, int)
    assert result.process_exit_executed is False
    assert result.process_terminated is False
    assert result.signal_transmitted is False
    assert result.systemd_contacted is False
    assert result.service_executed is False
    assert result.production_runtime_executed is False
    _closed(result)


def test_mapping_evidence_review_and_audit_are_redacted_and_fail_closed() -> None:
    incomplete = evaluate_deterministic_process_exit_boundary_design_v1(
        policy=_policy(), exit_code_set=_code_set(), graceful_shutdown_mapping=_graceful_mapping(mapping_id=""),
        fail_closed_mapping=_fail_closed_mapping(), systemd_compatibility=_compatibility(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evidence_timestamp="2026-01-02T00:00:00Z",
        evidence_expiry_timestamp="2026-12-30T00:00:00Z",
    )
    assert incomplete.ready is False
    assert "MAPPING_ID_EMPTY" in incomplete.failure_codes
    collision = evaluate_deterministic_process_exit_boundary_design_v1(
        policy=_policy(), exit_code_set=_code_set(), graceful_shutdown_mapping=_graceful_mapping(),
        fail_closed_mapping=_fail_closed_mapping(), systemd_compatibility=_compatibility(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(reviewer_identity="operator-a"),
        evidence_timestamp="2026-01-02T00:00:00Z", evidence_expiry_timestamp="2026-12-30T00:00:00Z",
    )
    assert "OPERATOR_REVIEWER_COLLISION" in collision.failure_codes
    evidence = build_deterministic_process_exit_boundary_audit_evidence_v1(
        evidence_id="process-exit-evidence-v1", decision=_decision(),
        classification_result=classify_process_exit_without_execution_v1(
            decision=_decision(), classification_request=_classification_request("PASSIVE_READY"),
        ),
    )
    _frozen(evidence)
    assert evidence.failure_codes == ()
    assert "0x" not in repr(evidence)
    _closed(evidence)
