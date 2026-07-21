"""Dependency-injected, non-executing process-exit classification boundary."""
from __future__ import annotations

from dataclasses import dataclass


_NAMES = (
    "PASSIVE_SERVICE_READY_EXIT", "GRACEFUL_SIGTERM_SHUTDOWN_EXIT", "GRACEFUL_SIGINT_SHUTDOWN_EXIT",
    "CLI_CONFIGURATION_BLOCKED_EXIT", "HOST_SIGNAL_REGISTRATION_BLOCKED_EXIT",
    "HANDLER_INSTALLATION_BLOCKED_EXIT", "HANDLER_RESTORATION_BLOCKED_EXIT",
    "GRACEFUL_SHUTDOWN_BLOCKED_EXIT", "SERVICE_DEPLOYMENT_BLOCKED_EXIT",
    "SERVICE_EXECUTION_NOT_AUTHORIZED_EXIT", "CREDENTIAL_LOADING_NOT_AUTHORIZED_EXIT",
    "NETWORK_NOT_AUTHORIZED_EXIT", "WORKLOAD_NOT_AUTHORIZED_EXIT", "RUNTIME_NOT_AUTHORIZED_EXIT",
    "INTERNAL_FAIL_CLOSED_EXIT",
)
_ORDER = (
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


@dataclass(frozen=True, slots=True, init=False)
class _Record:
    values: tuple[tuple[str, object], ...]
    def __init__(self, **values: object) -> None:
        object.__setattr__(self, "values", tuple(values.items()))
    def __getattr__(self, name: str) -> object:
        for key, value in self.values:
            if key == name:
                return value
        raise AttributeError(name)


class NonExecutingProcessExitBoundaryPolicyV1(_Record): __slots__ = ()
class NonExecutingProcessExitAdapterV1(_Record): __slots__ = ()
class NonExecutingExitClassificationRequestV1(_Record): __slots__ = ()
class NonExecutingExitClassificationSelectionV1(_Record): __slots__ = ()
class NonExecutingExitClassificationResultV1(_Record): __slots__ = ()
class NonExecutingGracefulShutdownExitMappingV1(_Record): __slots__ = ()
class NonExecutingFailClosedExitMappingV1(_Record): __slots__ = ()
class NonExecutingSystemdExitResultV1(_Record): __slots__ = ()
class NonExecutingProcessExitBoundaryStateV1(_Record): __slots__ = ()
class NonExecutingProcessExitBoundaryTransitionV1(_Record): __slots__ = ()
@dataclass(frozen=True, slots=True)
class NonExecutingProcessExitBoundaryFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool
class NonExecutingProcessExitBoundaryAuditEvidenceV1(_Record): __slots__ = ()


def _v(record: object, name: str, default: object = False) -> object:
    return getattr(record, name, default)


def _codes(*codes: str) -> tuple[str, ...]:
    found = set(codes)
    return tuple(code for code in _ORDER if code in found)


def _closed() -> dict[str, bool]:
    return {
        "activation_gate_open": False, "credential_gate_open": False, "network_gate_open": False, "workload_gate_open": False,
        "operating_system_exit_code_return_authorized": False, "production_process_exit_execution_authorized": False,
        "process_exit_execution_authorized": False, "process_termination_authorized": False,
        "process_signal_transmission_authorized": False, "sys_exit_authorized": False, "system_exit_authorized": False,
        "os_exit_authorized": False, "kill_or_raise_signal_authorized": False,
        "production_service_execution_authorized": False, "production_runtime_execution_authorized": False,
        "credential_loading_authorized": False, "systemd_access_authorized": False, "network_authorized": False,
        "runtime_activation_authorized": False, "publication_authorized": False, "fail_closed": True,
    }


def _result(codes: tuple[str, ...]) -> dict[str, object]:
    values: dict[str, object] = {
        "failure_codes": codes,
        "failures": tuple(NonExecutingProcessExitBoundaryFailureV1(code, "fail-closed non-executing rejection", False) for code in codes),
    }
    values.update(_closed())
    return values


def _policy_codes(policy: NonExecutingProcessExitBoundaryPolicyV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not _v(policy, "policy_id", ""): codes.append("POLICY_ID_EMPTY")
    if not _v(policy, "policy_version", ""): codes.append("POLICY_VERSION_EMPTY")
    for name, code in (
        ("production_process_exit_adapter_implementation_authorized", "PROCESS_EXIT_ADAPTER_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("deterministic_exit_code_selection_implementation_authorized", "EXIT_CODE_SELECTION_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("graceful_shutdown_exit_mapping_implementation_authorized", "GRACEFUL_SHUTDOWN_EXIT_MAPPING_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("fail_closed_exit_mapping_implementation_authorized", "FAIL_CLOSED_EXIT_MAPPING_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("systemd_compatible_exit_result_implementation_authorized", "SYSTEMD_COMPATIBLE_EXIT_RESULT_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("process_exit_result_audit_implementation_authorized", "PROCESS_EXIT_RESULT_AUDIT_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("non_executing_dependency_injected_classification_only", "NON_EXECUTING_DEPENDENCY_INJECTED_MODE_REQUIRED"),
    ):
        if not _v(policy, name): codes.append(code)
    for name, code in (
        ("operating_system_exit_code_return_authorized", "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED"),
        ("production_process_exit_execution_authorized", "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED"),
        ("process_exit_execution_authorized", "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED"),
        ("process_termination_authorized", "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        ("process_signal_transmission_authorized", "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
        ("sys_exit_authorized", "SYS_EXIT_NOT_AUTHORIZED"), ("system_exit_authorized", "SYSTEM_EXIT_NOT_AUTHORIZED"),
        ("os_exit_authorized", "OS_EXIT_NOT_AUTHORIZED"), ("kill_or_raise_signal_authorized", "KILL_OR_RAISE_SIGNAL_NOT_AUTHORIZED"),
        ("standard_library_signal_access_authorized", "STANDARD_LIBRARY_SIGNAL_ACCESS_NOT_AUTHORIZED"),
        ("actual_signal_transmission_authorized", "ACTUAL_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
        ("production_cli_execution_authorized", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED"),
        ("production_service_execution_authorized", "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED"),
        ("production_runtime_execution_authorized", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED"),
        ("implicit_sys_argv_access_authorized", "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED"),
        ("environment_read_authorized", "ENVIRONMENT_READ_NOT_AUTHORIZED"),
        ("filesystem_read_authorized", "FILESYSTEM_READ_NOT_AUTHORIZED"), ("filesystem_write_authorized", "FILESYSTEM_WRITE_NOT_AUTHORIZED"),
        ("credential_access_authorized", "CREDENTIAL_ACCESS_NOT_AUTHORIZED"), ("credential_loading_authorized", "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ("provider_transmission_authorized", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"), ("scanner_execution_authorized", "SCANNER_EXECUTION_NOT_AUTHORIZED"),
        ("worker_start_authorized", "WORKER_START_NOT_AUTHORIZED"), ("scheduler_start_authorized", "SCHEDULER_START_NOT_AUTHORIZED"),
        ("telegram_start_authorized", "TELEGRAM_START_NOT_AUTHORIZED"), ("database_mutation_authorized", "DATABASE_MUTATION_NOT_AUTHORIZED"),
        ("artifact_publication_authorized", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED"), ("trading_authorized", "TRADING_NOT_AUTHORIZED"),
        ("subprocess_authorized", "SUBPROCESS_NOT_AUTHORIZED"), ("thread_creation_authorized", "THREAD_CREATION_NOT_AUTHORIZED"),
        ("event_loop_start_authorized", "EVENT_LOOP_START_NOT_AUTHORIZED"), ("runtime_activation_authorized", "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ("publication_authorized", "PUBLICATION_NOT_AUTHORIZED"), ("activation_gate_open", "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
        ("credential_gate_open", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"), ("network_gate_open", "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ("workload_gate_open", "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
    ):
        if _v(policy, name): codes.append(code)
    return _codes(*codes)


def _adapter_codes(adapter: NonExecutingProcessExitAdapterV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not _v(adapter, "dependency_injected") or not _v(adapter, "non_executing") or not _v(adapter, "classification_only"):
        codes.append("PROCESS_EXIT_ADAPTER_REQUIRED")
    for name, code in (("operating_system_exit_return_allowed", "OPERATING_SYSTEM_EXIT_RETURN_NOT_AUTHORIZED"),
                       ("process_termination_allowed", "PROCESS_TERMINATION_NOT_AUTHORIZED"),
                       ("process_signal_transmission_allowed", "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
                       ("systemd_contact_allowed", "SYSTEMD_CONTACT_NOT_AUTHORIZED"),
                       ("service_execution_allowed", "SERVICE_EXECUTION_NOT_AUTHORIZED")):
        if _v(adapter, name): codes.append(code)
    if not all(callable(_v(adapter, name, None)) for name in ("select_exit_code", "validate_exit_code", "format_systemd_result")):
        codes.append("PROCESS_EXIT_ADAPTER_REQUIRED")
    return _codes(*codes)


def _code_map(adapter: NonExecutingProcessExitAdapterV1) -> tuple[dict[str, int], tuple[str, ...]]:
    codes: list[str] = []
    identities = _v(adapter, "exit_code_identities", ())
    if not isinstance(identities, tuple) or len(identities) != len(_NAMES): codes.append("EXIT_CLASSIFICATION_SET_INCOMPLETE")
    entries: dict[str, int] = {}
    for item in identities if isinstance(identities, tuple) else ():
        if not isinstance(item, tuple) or len(item) != 2:
            codes.append("EXIT_CLASSIFICATION_SET_INCOMPLETE"); continue
        name, code = item
        if not isinstance(name, str) or not name: codes.append("EXIT_CLASSIFICATION_MISSING")
        if code is None: codes.append("EXIT_CODE_MISSING")
        elif isinstance(code, bool): codes.append("EXIT_CODE_BOOLEAN_NOT_ALLOWED")
        elif not isinstance(code, int): codes.append("EXIT_CODE_NOT_INTEGER")
        elif code < 0: codes.append("EXIT_CODE_NEGATIVE")
        else: entries[name] = code
    if set(entries) != set(_NAMES): codes.append("EXIT_CLASSIFICATION_SET_INCOMPLETE")
    if len(entries) != len(set(entries.values())): codes.append("EXIT_CODE_OVERLAP")
    minimum, maximum = _v(adapter, "systemd_compatible_minimum", 0), _v(adapter, "systemd_compatible_maximum", -1)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < minimum or any(code < minimum or code > maximum for code in entries.values()):
        codes.append("EXIT_CODE_OUTSIDE_SYSTEMD_COMPATIBLE_RANGE")
    return entries, _codes(*codes)


def _request_codes(request: NonExecutingExitClassificationRequestV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not _v(request, "request_id", ""): codes.append("REQUEST_ID_EMPTY")
    if not _v(request, "timestamp", ""): codes.append("REQUEST_TIMESTAMP_REQUIRED")
    if not _v(request, "source_lifecycle_state", ""): codes.append("SOURCE_STATE_EMPTY")
    if not _v(request, "requested_mapping_id", ""): codes.append("MAPPING_ID_EMPTY")
    for name, code in (("activation_gate_open", "ACTIVATION_GATE_MUST_REMAIN_CLOSED"), ("credential_gate_open", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"), ("network_gate_open", "NETWORK_GATE_MUST_REMAIN_CLOSED"), ("workload_gate_open", "WORKLOAD_GATE_MUST_REMAIN_CLOSED"), ("service_execution_authorized", "SERVICE_EXECUTION_NOT_AUTHORIZED")):
        if _v(request, name): codes.append(code)
    return _codes(*codes)


def _choice(request: NonExecutingExitClassificationRequestV1) -> tuple[str, tuple[str, ...]]:
    state, signal_name = _v(request, "source_lifecycle_state", ""), _v(request, "source_signal_classification", "")
    if state == "PASSIVE_READY": return "PASSIVE_SERVICE_READY_EXIT", ()
    if state == "GRACEFUL_SHUTDOWN_COMPLETE":
        if not _v(request, "handler_restoration_complete") or not _v(request, "graceful_shutdown_complete"):
            return "GRACEFUL_SHUTDOWN_BLOCKED_EXIT", ("HANDLER_RESTORATION_REQUIRED_FOR_GRACEFUL_EXIT",)
        if signal_name == "SIGTERM": return "GRACEFUL_SIGTERM_SHUTDOWN_EXIT", ()
        if signal_name == "SIGINT": return "GRACEFUL_SIGINT_SHUTDOWN_EXIT", ()
        return "INTERNAL_FAIL_CLOSED_EXIT", ("UNSUPPORTED_SIGNAL_CONTEXT",)
    blocked = {name.removesuffix("_EXIT"): name for name in _NAMES[3:-1]}
    if state in blocked: return blocked[state], ()
    return "INTERNAL_FAIL_CLOSED_EXIT", ("UNKNOWN_SOURCE_STATE",)


def _selection(policy: NonExecutingProcessExitBoundaryPolicyV1, adapter: NonExecutingProcessExitAdapterV1, request: NonExecutingExitClassificationRequestV1) -> NonExecutingExitClassificationResultV1:
    mapping, code_errors = _code_map(adapter)
    selected, choice_errors = _choice(request)
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter), *code_errors, *_request_codes(request), *choice_errors)
    code = mapping.get(selected, mapping.get("INTERNAL_FAIL_CLOSED_EXIT", -1))
    if not codes:
        try:
            selected_code = adapter.select_exit_code(selected)
            if not adapter.validate_exit_code(selected, selected_code) or selected_code != code:
                codes = _codes("EXIT_CODE_MISSING")
        except Exception:
            codes = _codes("RAW_EXCEPTION_EXPOSURE_DETECTED")
    values = _result(codes)
    values.update(request_id=_v(request, "request_id", ""), selected_classification=selected, selected_exit_code=code,
                  ready=not codes, blocked=bool(codes), operating_system_exit_code_returned=False, process_exit_executed=False,
                  process_terminated=False, signal_transmitted=False, systemd_contacted=False, service_executed=False,
                  production_runtime_executed=False, state=NonExecutingProcessExitBoundaryStateV1(state_id=_v(request, "request_id", ""), state_code=("READY" if not codes else "BLOCKED")))
    return NonExecutingExitClassificationResultV1(**values)


def select_non_executing_process_exit_classification_v1(*, policy: NonExecutingProcessExitBoundaryPolicyV1, adapter: NonExecutingProcessExitAdapterV1, request: NonExecutingExitClassificationRequestV1) -> NonExecutingExitClassificationResultV1:
    return _selection(policy, adapter, request)


def map_non_executing_graceful_shutdown_exit_v1(*, policy: NonExecutingProcessExitBoundaryPolicyV1, adapter: NonExecutingProcessExitAdapterV1, request: NonExecutingExitClassificationRequestV1) -> NonExecutingExitClassificationResultV1:
    return _selection(policy, adapter, request)


def map_non_executing_fail_closed_exit_v1(*, policy: NonExecutingProcessExitBoundaryPolicyV1, adapter: NonExecutingProcessExitAdapterV1, request: NonExecutingExitClassificationRequestV1) -> NonExecutingExitClassificationResultV1:
    return _selection(policy, adapter, request)


def build_non_executing_systemd_exit_result_v1(*, policy: NonExecutingProcessExitBoundaryPolicyV1, adapter: NonExecutingProcessExitAdapterV1, selection: NonExecutingExitClassificationResultV1, systemd_result_id: str) -> NonExecutingSystemdExitResultV1:
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter), *_v(selection, "failure_codes", ()))
    try:
        formatted = adapter.format_systemd_result(selection.selected_classification, selection.selected_exit_code) if not codes else "REDACTED"
    except Exception:
        formatted = "REDACTED"; codes = _codes(*codes, "RAW_EXCEPTION_EXPOSURE_DETECTED")
    values = _result(codes)
    values.update(systemd_result_id=systemd_result_id, selected_classification=selection.selected_classification,
                  selected_exit_code=selection.selected_exit_code, formatted_classification=formatted,
                  category=("SUCCESS" if selection.selected_classification == "PASSIVE_SERVICE_READY_EXIT" else "BLOCKED"),
                  restart_action_authorized=False, watchdog_action_authorized=False, core_dump_classification=False,
                  signal_derived_termination=False, operating_system_exit_code_returned=False, systemd_contacted=False,
                  service_executed=False)
    return NonExecutingSystemdExitResultV1(**values)


def evaluate_non_executing_process_exit_boundary_v1(*, policy: NonExecutingProcessExitBoundaryPolicyV1, adapter: NonExecutingProcessExitAdapterV1, request: NonExecutingExitClassificationRequestV1) -> NonExecutingProcessExitBoundaryTransitionV1:
    selection = _selection(policy, adapter, request)
    values = _result(selection.failure_codes)
    values.update(transition_id=_v(request, "request_id", ""), ready=selection.ready,
                  current_state=selection.state, selection=selection)
    return NonExecutingProcessExitBoundaryTransitionV1(**values)


def build_non_executing_process_exit_boundary_audit_evidence_v1(*, evidence_id: str, evaluation: NonExecutingProcessExitBoundaryTransitionV1, selection: NonExecutingExitClassificationResultV1, systemd_result: NonExecutingSystemdExitResultV1) -> NonExecutingProcessExitBoundaryAuditEvidenceV1:
    codes = _codes(*_v(evaluation, "failure_codes", ()), *_v(selection, "failure_codes", ()), *_v(systemd_result, "failure_codes", ()))
    values = _result(codes)
    values.update(evidence_id=evidence_id, selected_classification=selection.selected_classification,
                  selected_exit_code=selection.selected_exit_code, boundary_state=selection.state.state_code,
                  operating_system_exit_code_returned=False, process_exit_executed=False, process_terminated=False,
                  signal_transmitted=False, systemd_contacted=False, service_executed=False, production_runtime_executed=False)
    return NonExecutingProcessExitBoundaryAuditEvidenceV1(**values)
