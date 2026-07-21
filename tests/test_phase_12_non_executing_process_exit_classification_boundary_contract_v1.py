"""RED contract for a dependency-injected, non-executing exit classifier."""
from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from engine.phase_12_non_executing_process_exit_classification_boundary_contract_v1 import (
    NonExecutingExitClassificationRequestV1,
    NonExecutingExitClassificationResultV1,
    NonExecutingExitClassificationSelectionV1,
    NonExecutingFailClosedExitMappingV1,
    NonExecutingGracefulShutdownExitMappingV1,
    NonExecutingProcessExitAdapterV1,
    NonExecutingProcessExitBoundaryAuditEvidenceV1,
    NonExecutingProcessExitBoundaryFailureV1,
    NonExecutingProcessExitBoundaryPolicyV1,
    NonExecutingProcessExitBoundaryStateV1,
    NonExecutingProcessExitBoundaryTransitionV1,
    NonExecutingSystemdExitResultV1,
    build_non_executing_process_exit_boundary_audit_evidence_v1,
    build_non_executing_systemd_exit_result_v1,
    evaluate_non_executing_process_exit_boundary_v1,
    map_non_executing_fail_closed_exit_v1,
    map_non_executing_graceful_shutdown_exit_v1,
    select_non_executing_process_exit_classification_v1,
)


_CODES = (
    "PASSIVE_SERVICE_READY_EXIT", "GRACEFUL_SIGTERM_SHUTDOWN_EXIT", "GRACEFUL_SIGINT_SHUTDOWN_EXIT",
    "CLI_CONFIGURATION_BLOCKED_EXIT", "HOST_SIGNAL_REGISTRATION_BLOCKED_EXIT",
    "HANDLER_INSTALLATION_BLOCKED_EXIT", "HANDLER_RESTORATION_BLOCKED_EXIT",
    "GRACEFUL_SHUTDOWN_BLOCKED_EXIT", "SERVICE_DEPLOYMENT_BLOCKED_EXIT",
    "SERVICE_EXECUTION_NOT_AUTHORIZED_EXIT", "CREDENTIAL_LOADING_NOT_AUTHORIZED_EXIT",
    "NETWORK_NOT_AUTHORIZED_EXIT", "WORKLOAD_NOT_AUTHORIZED_EXIT", "RUNTIME_NOT_AUTHORIZED_EXIT",
    "INTERNAL_FAIL_CLOSED_EXIT",
)

_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PROCESS_EXIT_ADAPTER_IMPLEMENTATION_NOT_AUTHORIZED",
    "EXIT_CODE_SELECTION_IMPLEMENTATION_NOT_AUTHORIZED", "GRACEFUL_SHUTDOWN_EXIT_MAPPING_IMPLEMENTATION_NOT_AUTHORIZED",
    "FAIL_CLOSED_EXIT_MAPPING_IMPLEMENTATION_NOT_AUTHORIZED", "SYSTEMD_COMPATIBLE_EXIT_RESULT_IMPLEMENTATION_NOT_AUTHORIZED",
    "PROCESS_EXIT_RESULT_AUDIT_IMPLEMENTATION_NOT_AUTHORIZED", "NON_EXECUTING_DEPENDENCY_INJECTED_MODE_REQUIRED",
    "PROCESS_EXIT_ADAPTER_REQUIRED", "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED",
    "PROCESS_TERMINATION_NOT_AUTHORIZED", "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED",
    "SYSTEMD_CONTACT_NOT_AUTHORIZED", "SERVICE_EXECUTION_NOT_AUTHORIZED", "EXIT_CLASSIFICATION_SET_INCOMPLETE",
    "EXIT_CLASSIFICATION_MISSING", "EXIT_CODE_MISSING", "EXIT_CODE_BOOLEAN_NOT_ALLOWED", "EXIT_CODE_NOT_INTEGER",
    "EXIT_CODE_NEGATIVE", "EXIT_CODE_OVERLAP", "EXIT_CODE_OUTSIDE_SYSTEMD_COMPATIBLE_RANGE",
    "REQUEST_ID_EMPTY", "REQUEST_TIMESTAMP_REQUIRED", "SOURCE_STATE_EMPTY", "UNKNOWN_SOURCE_STATE",
    "UNSUPPORTED_SIGNAL_CONTEXT", "HANDLER_RESTORATION_REQUIRED_FOR_GRACEFUL_EXIT", "MAPPING_ID_EMPTY",
    "SYS_EXIT_NOT_AUTHORIZED", "SYSTEM_EXIT_NOT_AUTHORIZED", "OS_EXIT_NOT_AUTHORIZED",
    "KILL_OR_RAISE_SIGNAL_NOT_AUTHORIZED", "STANDARD_LIBRARY_SIGNAL_ACCESS_NOT_AUTHORIZED",
    "ACTUAL_SIGNAL_TRANSMISSION_NOT_AUTHORIZED", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED",
    "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED",
    "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED", "ENVIRONMENT_READ_NOT_AUTHORIZED", "FILESYSTEM_READ_NOT_AUTHORIZED",
    "FILESYSTEM_WRITE_NOT_AUTHORIZED", "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "SUBPROCESS_NOT_AUTHORIZED", "THREAD_CREATION_NOT_AUTHORIZED", "EVENT_LOOP_START_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_MATERIAL_EXPOSURE_DETECTED",
    "PROCESS_METADATA_EXPOSURE_DETECTED", "EXIT_CALLBACK_EXPOSURE_DETECTED", "SYSTEMD_HANDLE_EXPOSURE_DETECTED",
    "AUTHORIZATION_MATERIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


class _FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def select_exit_code(self, classification: str) -> int:
        self.calls.append(("select", classification))
        return _CODES.index(classification)

    def validate_exit_code(self, classification: str, code: int) -> bool:
        self.calls.append(("validate", classification))
        return isinstance(code, int) and code == _CODES.index(classification)

    def format_systemd_result(self, classification: str, code: int) -> str:
        self.calls.append(("format", classification))
        return f"{classification}:{code}"


def _policy(**overrides: object) -> NonExecutingProcessExitBoundaryPolicyV1:
    values = dict(
        policy_id="non-executing-exit-policy-v1", policy_version="V1",
        production_process_exit_adapter_implementation_authorized=True,
        deterministic_exit_code_selection_implementation_authorized=True,
        graceful_shutdown_exit_mapping_implementation_authorized=True,
        fail_closed_exit_mapping_implementation_authorized=True,
        systemd_compatible_exit_result_implementation_authorized=True,
        process_exit_result_audit_implementation_authorized=True,
        non_executing_dependency_injected_classification_only=True, caller_supplied_exit_codes_required=True,
        unique_exit_codes_required=True, operating_system_exit_return_prohibited=True, fail_closed=True,
        operating_system_exit_code_return_authorized=False, production_process_exit_execution_authorized=False,
        process_exit_execution_authorized=False, process_termination_authorized=False,
        process_signal_transmission_authorized=False, sys_exit_authorized=False, system_exit_authorized=False,
        os_exit_authorized=False, kill_or_raise_signal_authorized=False,
        standard_library_signal_access_authorized=False, real_host_handler_installation_authorized=False,
        real_host_handler_restoration_authorized=False, actual_signal_transmission_authorized=False,
        production_cli_execution_authorized=False, production_service_execution_authorized=False,
        production_runtime_execution_authorized=False, implicit_sys_argv_access_authorized=False,
        environment_read_authorized=False, filesystem_read_authorized=False, filesystem_write_authorized=False,
        credential_access_authorized=False, credential_loading_authorized=False,
        credential_validation_authorized=False, systemd_access_authorized=False,
        systemd_unit_generation_authorized=False, systemd_drop_in_generation_authorized=False,
        service_installation_authorized=False, daemon_reload_authorized=False, service_enablement_authorized=False,
        service_start_restart_authorized=False, provider_transmission_authorized=False,
        scanner_execution_authorized=False, worker_start_authorized=False, scheduler_start_authorized=False,
        telegram_start_authorized=False, database_mutation_authorized=False,
        artifact_publication_authorized=False, trading_authorized=False, subprocess_authorized=False,
        thread_creation_authorized=False, event_loop_start_authorized=False,
        runtime_activation_authorized=False, publication_authorized=False, activation_gate_open=False,
        credential_gate_open=False, network_gate_open=False, workload_gate_open=False,
    )
    return NonExecutingProcessExitBoundaryPolicyV1(**(values | overrides))


def _adapter(fake: _FakeAdapter | None = None, **overrides: object) -> NonExecutingProcessExitAdapterV1:
    fake = fake or _FakeAdapter()
    values = dict(
        adapter_id="non-executing-exit-adapter-v1", dependency_injected=True, non_executing=True,
        classification_only=True, operating_system_exit_return_allowed=False, process_termination_allowed=False,
        process_signal_transmission_allowed=False, systemd_contact_allowed=False, service_execution_allowed=False,
        exit_code_identities=tuple((name, index) for index, name in enumerate(_CODES)),
        systemd_compatible_minimum=0, systemd_compatible_maximum=255, select_exit_code=fake.select_exit_code,
        validate_exit_code=fake.validate_exit_code, format_systemd_result=fake.format_systemd_result,
    )
    return NonExecutingProcessExitAdapterV1(**(values | overrides))


def _request(state: str = "PASSIVE_READY", signal_name: str = "", **overrides: object) -> NonExecutingExitClassificationRequestV1:
    values = dict(
        request_id="non-executing-exit-request-v1", timestamp="2026-01-01T00:00:00Z",
        source_lifecycle_state=state, source_signal_classification=signal_name,
        graceful_shutdown_complete=state == "GRACEFUL_SHUTDOWN_COMPLETE", handler_restoration_complete=True,
        deployment_state="NOT_YET_INSTALLED", service_execution_authorized=False,
        activation_gate_open=False, credential_gate_open=False, network_gate_open=False, workload_gate_open=False,
        expected_classification="", requested_mapping_id="non-executing-exit-mapping-v1",
    )
    return NonExecutingExitClassificationRequestV1(**(values | overrides))


def _closed(record: object) -> None:
    for name in (
        "activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open",
        "operating_system_exit_code_return_authorized", "production_process_exit_execution_authorized",
        "process_exit_execution_authorized", "process_termination_authorized", "process_signal_transmission_authorized",
        "production_service_execution_authorized", "production_runtime_execution_authorized",
        "credential_loading_authorized", "systemd_access_authorized", "runtime_activation_authorized",
        "publication_authorized",
    ):
        assert getattr(record, name) is False
    assert record.fail_closed is True


def test_public_records_are_frozen_slotted_and_non_executing() -> None:
    for record in (_policy(), _adapter(), _request()):
        _frozen(record)
    for record_type in (
        NonExecutingExitClassificationSelectionV1, NonExecutingExitClassificationResultV1,
        NonExecutingGracefulShutdownExitMappingV1, NonExecutingFailClosedExitMappingV1,
        NonExecutingSystemdExitResultV1, NonExecutingProcessExitBoundaryStateV1,
        NonExecutingProcessExitBoundaryTransitionV1, NonExecutingProcessExitBoundaryFailureV1,
        NonExecutingProcessExitBoundaryAuditEvidenceV1,
    ):
        assert hasattr(record_type, "__dataclass_fields__")


def test_injected_selection_returns_metadata_not_a_bare_operating_system_exit_code() -> None:
    fake = _FakeAdapter()
    result = select_non_executing_process_exit_classification_v1(policy=_policy(), adapter=_adapter(fake), request=_request())
    _frozen(result)
    assert not isinstance(result, int)
    assert result.selected_classification == "PASSIVE_SERVICE_READY_EXIT"
    assert result.selected_exit_code == 0
    assert fake.calls[:2] == [("select", "PASSIVE_SERVICE_READY_EXIT"), ("validate", "PASSIVE_SERVICE_READY_EXIT")]
    assert result.operating_system_exit_code_returned is False
    assert result.process_exit_executed is False
    assert result.process_terminated is False
    assert result.signal_transmitted is False
    _closed(result)


@pytest.mark.parametrize(
    ("adapter_case", "request_case", "failure_code"),
    (
        (_adapter(operating_system_exit_return_allowed=True), _request(), "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED"),
        (_adapter(process_termination_allowed=True), _request(), "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        (_adapter(process_signal_transmission_allowed=True), _request(), "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
        (_adapter(exit_code_identities=(("PASSIVE_SERVICE_READY_EXIT", True),) + _adapter().exit_code_identities[1:]), _request(), "EXIT_CODE_BOOLEAN_NOT_ALLOWED"),
        (_adapter(exit_code_identities=(("PASSIVE_SERVICE_READY_EXIT", -1),) + _adapter().exit_code_identities[1:]), _request(), "EXIT_CODE_NEGATIVE"),
        (_adapter(exit_code_identities=("bad",) * len(_CODES)), _request(), "EXIT_CLASSIFICATION_SET_INCOMPLETE"),
        (_adapter(), _request(request_id=""), "REQUEST_ID_EMPTY"),
        (_adapter(), _request(source_lifecycle_state=""), "SOURCE_STATE_EMPTY"),
    ),
)
def test_invalid_adapter_or_request_metadata_fails_closed_deterministically(
    adapter_case: NonExecutingProcessExitAdapterV1, request_case: NonExecutingExitClassificationRequestV1,
    failure_code: str,
) -> None:
    result = select_non_executing_process_exit_classification_v1(policy=_policy(), adapter=adapter_case, request=request_case)
    assert result.ready is False
    assert failure_code in result.failure_codes
    assert tuple(sorted(result.failure_codes, key=_FAILURES.index)) == result.failure_codes
    _closed(result)


@pytest.mark.parametrize(
    ("state", "signal_name", "expected"),
    (
        ("GRACEFUL_SHUTDOWN_COMPLETE", "SIGTERM", "GRACEFUL_SIGTERM_SHUTDOWN_EXIT"),
        ("GRACEFUL_SHUTDOWN_COMPLETE", "SIGINT", "GRACEFUL_SIGINT_SHUTDOWN_EXIT"),
        ("CLI_CONFIGURATION_BLOCKED", "", "CLI_CONFIGURATION_BLOCKED_EXIT"),
        ("NETWORK_NOT_AUTHORIZED", "", "NETWORK_NOT_AUTHORIZED_EXIT"),
        ("UNKNOWN", "", "INTERNAL_FAIL_CLOSED_EXIT"),
    ),
)
def test_graceful_and_fail_closed_mappings_are_deterministic(state: str, signal_name: str, expected: str) -> None:
    graceful = map_non_executing_graceful_shutdown_exit_v1(policy=_policy(), adapter=_adapter(), request=_request(state, signal_name))
    fail_closed = map_non_executing_fail_closed_exit_v1(policy=_policy(), adapter=_adapter(), request=_request(state, signal_name))
    result = graceful if state in ("GRACEFUL_SHUTDOWN_COMPLETE", "PASSIVE_READY") else fail_closed
    assert result.selected_classification == expected
    _closed(result)


def test_graceful_restoration_systemd_result_state_and_audit_remain_metadata_only() -> None:
    blocked = map_non_executing_graceful_shutdown_exit_v1(
        policy=_policy(), adapter=_adapter(), request=_request("GRACEFUL_SHUTDOWN_COMPLETE", "SIGTERM", handler_restoration_complete=False),
    )
    assert blocked.selected_classification == "GRACEFUL_SHUTDOWN_BLOCKED_EXIT"
    selected = select_non_executing_process_exit_classification_v1(policy=_policy(), adapter=_adapter(), request=_request("GRACEFUL_SHUTDOWN_COMPLETE", "SIGINT"))
    systemd_result = build_non_executing_systemd_exit_result_v1(policy=_policy(), adapter=_adapter(), selection=selected, systemd_result_id="non-executing-systemd-result-v1")
    assert systemd_result.systemd_contacted is False
    assert systemd_result.service_executed is False
    assert systemd_result.operating_system_exit_code_returned is False
    evaluation = evaluate_non_executing_process_exit_boundary_v1(policy=_policy(), adapter=_adapter(), request=_request())
    assert evaluation.ready is True
    evidence = build_non_executing_process_exit_boundary_audit_evidence_v1(evidence_id="non-executing-exit-evidence-v1", evaluation=evaluation, selection=selected, systemd_result=systemd_result)
    _frozen(evidence)
    assert "0x" not in repr(evidence)
    _closed(evidence)
