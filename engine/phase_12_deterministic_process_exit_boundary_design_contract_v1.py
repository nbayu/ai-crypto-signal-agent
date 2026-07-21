"""Metadata-only deterministic process-exit boundary design."""
from __future__ import annotations

from dataclasses import dataclass


_ORDER = (
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

_MAPPING_KEYS = (
    ("PASSIVE_READY", ""), ("GRACEFUL_SHUTDOWN_COMPLETE", "SIGTERM"),
    ("GRACEFUL_SHUTDOWN_COMPLETE", "SIGINT"), ("CLI_CONFIGURATION_BLOCKED", ""),
    ("HOST_SIGNAL_REGISTRATION_BLOCKED", ""), ("HANDLER_INSTALLATION_BLOCKED", ""),
    ("HANDLER_RESTORATION_BLOCKED", ""), ("GRACEFUL_SHUTDOWN_BLOCKED", ""),
    ("SERVICE_DEPLOYMENT_BLOCKED", ""), ("SERVICE_EXECUTION_NOT_AUTHORIZED", ""),
    ("CREDENTIAL_LOADING_NOT_AUTHORIZED", ""), ("NETWORK_NOT_AUTHORIZED", ""),
    ("WORKLOAD_NOT_AUTHORIZED", ""), ("RUNTIME_NOT_AUTHORIZED", ""),
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


class DeterministicProcessExitBoundaryPolicyV1(_Record):
    __slots__ = ()


class DeterministicExitCodeIdentityV1(_Record):
    __slots__ = ()


class DeterministicExitCodeSetV1(_Record):
    __slots__ = ()


class GracefulShutdownExitMappingV1(_Record):
    __slots__ = ()


class FailClosedExitMappingV1(_Record):
    __slots__ = ()


class ProcessExitClassificationRequestV1(_Record):
    __slots__ = ()


class ProcessExitClassificationResultV1(_Record):
    __slots__ = ()


class SystemdExitStatusCompatibilityV1(_Record):
    __slots__ = ()


class ProcessExitBoundaryChecklistV1(_Record):
    __slots__ = ()


class ProcessExitOperatorAttestationV1(_Record):
    __slots__ = ()


class ProcessExitIndependentReviewerApprovalV1(_Record):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ProcessExitBoundaryFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


class ProcessExitBoundaryDecisionV1(_Record):
    __slots__ = ()


class ProcessExitBoundaryAuditEvidenceV1(_Record):
    __slots__ = ()


def _value(record: object, name: str, default: object = False) -> object:
    return getattr(record, name, default)


def _codes(*codes: str) -> tuple[str, ...]:
    selected = set(codes)
    return tuple(code for code in _ORDER if code in selected)


def _failures(codes: tuple[str, ...]) -> tuple[ProcessExitBoundaryFailureV1, ...]:
    return tuple(ProcessExitBoundaryFailureV1(code, "fail-closed process-exit design rejection", False) for code in codes)


def _closed() -> dict[str, bool]:
    return {
        "activation_gate_open": False, "credential_gate_open": False,
        "network_gate_open": False, "workload_gate_open": False,
        "production_process_exit_implementation_authorized": False,
        "process_exit_execution_authorized": False, "process_termination_authorized": False,
        "process_signal_transmission_authorized": False, "sys_exit_authorized": False,
        "system_exit_authorized": False, "os_exit_authorized": False,
        "kill_or_raise_signal_authorized": False, "production_service_execution_authorized": False,
        "production_runtime_execution_authorized": False, "credential_access_authorized": False,
        "credential_loading_authorized": False, "credential_validation_authorized": False,
        "systemd_access_authorized": False, "network_authorized": False,
        "provider_transmission_authorized": False, "scanner_execution_authorized": False,
        "worker_start_authorized": False, "scheduler_start_authorized": False,
        "telegram_start_authorized": False, "database_mutation_authorized": False,
        "artifact_publication_authorized": False, "trading_authorized": False,
        "subprocess_authorized": False, "thread_creation_authorized": False,
        "event_loop_start_authorized": False, "runtime_activation_authorized": False,
        "publication_authorized": False, "fail_closed": True,
    }


def _result_values(codes: tuple[str, ...]) -> dict[str, object]:
    values: dict[str, object] = {"failure_codes": codes, "failures": _failures(codes)}
    values.update(_closed())
    return values


def _policy_codes(policy: DeterministicProcessExitBoundaryPolicyV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not isinstance(_value(policy, "policy_id", ""), str) or not _value(policy, "policy_id", ""):
        codes.append("POLICY_ID_EMPTY")
    if not isinstance(_value(policy, "policy_version", ""), str) or not _value(policy, "policy_version", ""):
        codes.append("POLICY_VERSION_EMPTY")
    for name, code in (
        ("production_process_exit_boundary_design_authorized", "PROCESS_EXIT_BOUNDARY_DESIGN_NOT_AUTHORIZED"),
        ("deterministic_exit_code_classification_design_authorized", "EXIT_CODE_CLASSIFICATION_DESIGN_NOT_AUTHORIZED"),
        ("graceful_shutdown_to_exit_mapping_design_authorized", "GRACEFUL_SHUTDOWN_EXIT_MAPPING_DESIGN_NOT_AUTHORIZED"),
        ("fail_closed_exit_mapping_design_authorized", "FAIL_CLOSED_EXIT_MAPPING_DESIGN_NOT_AUTHORIZED"),
        ("systemd_exit_status_compatibility_design_authorized", "SYSTEMD_EXIT_STATUS_COMPATIBILITY_DESIGN_NOT_AUTHORIZED"),
        ("process_exit_audit_evidence_design_authorized", "PROCESS_EXIT_AUDIT_EVIDENCE_DESIGN_NOT_AUTHORIZED"),
    ):
        if not _value(policy, name):
            codes.append(code)
    for name, code in (
        ("production_process_exit_implementation_authorized", "PRODUCTION_PROCESS_EXIT_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("process_exit_execution_authorized", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
        ("process_termination_authorized", "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        ("process_signal_transmission_authorized", "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
        ("sys_exit_authorized", "SYS_EXIT_NOT_AUTHORIZED"),
        ("system_exit_authorized", "SYSTEM_EXIT_NOT_AUTHORIZED"),
        ("os_exit_authorized", "OS_EXIT_NOT_AUTHORIZED"),
        ("kill_or_raise_signal_authorized", "KILL_OR_RAISE_SIGNAL_NOT_AUTHORIZED"),
        ("systemd_access_authorized", "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        ("production_service_execution_authorized", "SERVICE_EXECUTION_NOT_AUTHORIZED"),
        ("credential_access_authorized", "CREDENTIAL_ACCESS_NOT_AUTHORIZED"),
        ("credential_loading_authorized", "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ("provider_transmission_authorized", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        ("network_authorized", "NETWORK_NOT_AUTHORIZED"),
        ("scanner_execution_authorized", "SCANNER_EXECUTION_NOT_AUTHORIZED"),
        ("worker_start_authorized", "WORKER_START_NOT_AUTHORIZED"),
        ("scheduler_start_authorized", "SCHEDULER_START_NOT_AUTHORIZED"),
        ("telegram_start_authorized", "TELEGRAM_START_NOT_AUTHORIZED"),
        ("database_mutation_authorized", "DATABASE_MUTATION_NOT_AUTHORIZED"),
        ("artifact_publication_authorized", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED"),
        ("trading_authorized", "TRADING_NOT_AUTHORIZED"),
        ("subprocess_authorized", "SUBPROCESS_NOT_AUTHORIZED"),
        ("thread_creation_authorized", "THREAD_CREATION_NOT_AUTHORIZED"),
        ("event_loop_start_authorized", "EVENT_LOOP_START_NOT_AUTHORIZED"),
        ("production_runtime_execution_authorized", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED"),
        ("runtime_activation_authorized", "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ("publication_authorized", "PUBLICATION_NOT_AUTHORIZED"),
        ("activation_gate_open", "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
        ("credential_gate_open", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
        ("network_gate_open", "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ("workload_gate_open", "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
    ):
        if _value(policy, name):
            codes.append(code)
    return _codes(*codes)


def _code_set_codes(code_set: DeterministicExitCodeSetV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not _value(code_set, "code_set_id", ""):
        codes.append("EXIT_CODE_SET_ID_EMPTY")
    identities = _value(code_set, "exit_code_identities", ())
    classifications = tuple(_value(item, "classification", "") for item in identities)
    if set(classifications) != set(_CLASSIFICATIONS) or len(identities) != len(_CLASSIFICATIONS):
        codes.append("EXIT_CLASSIFICATION_MISSING")
    minimum = _value(code_set, "systemd_compatible_minimum", 0)
    maximum = _value(code_set, "systemd_compatible_maximum", -1)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or not isinstance(maximum, int) or isinstance(maximum, bool):
        codes.append("EXIT_CODE_OUTSIDE_SYSTEMD_COMPATIBLE_RANGE")
    exit_codes = tuple(_value(item, "code", None) for item in identities)
    if any(not isinstance(code, int) or isinstance(code, bool) for code in exit_codes):
        codes.append("EXIT_CODE_NOT_INTEGER")
    if any(isinstance(code, int) and not isinstance(code, bool) and code < 0 for code in exit_codes):
        codes.append("EXIT_CODE_NEGATIVE")
    valid_ints = tuple(code for code in exit_codes if isinstance(code, int) and not isinstance(code, bool))
    if len(valid_ints) != len(set(valid_ints)):
        codes.append("EXIT_CODE_OVERLAP")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and isinstance(maximum, int) and not isinstance(maximum, bool):
        if minimum < 0 or maximum < minimum or any(code < minimum or code > maximum for code in valid_ints):
            codes.append("EXIT_CODE_OUTSIDE_SYSTEMD_COMPATIBLE_RANGE")
    return _codes(*codes)


def _mapping_codes(
    graceful: GracefulShutdownExitMappingV1, fail_closed: FailClosedExitMappingV1,
) -> tuple[str, ...]:
    codes: list[str] = []
    if not _value(graceful, "mapping_id", "") or not _value(fail_closed, "mapping_id", ""):
        codes.append("MAPPING_ID_EMPTY")
    mappings = _value(graceful, "mappings", ())
    by_key = {(item[0], item[1]): item[2] for item in mappings if isinstance(item, tuple) and len(item) == 3}
    if any(key not in by_key for key in _MAPPING_KEYS):
        codes.append("GRACEFUL_SHUTDOWN_MAPPING_INCOMPLETE")
    if _value(fail_closed, "internal_fail_closed_classification", "") != "INTERNAL_FAIL_CLOSED_EXIT":
        codes.extend(("FAIL_CLOSED_MAPPING_INCOMPLETE", "INTERNAL_FAIL_CLOSED_MAPPING_REQUIRED"))
    return _codes(*codes)


def _compatibility_codes(compatibility: SystemdExitStatusCompatibilityV1) -> tuple[str, ...]:
    codes: list[str] = []
    required = (
        "systemd_compatibility_documented", "successful_passive_ready_classified",
        "graceful_sigterm_classified", "graceful_sigint_classified", "fail_closed_blocked_classified",
        "unique_exit_codes_required",
    )
    if not _value(compatibility, "compatibility_id", "") or not all(_value(compatibility, name) for name in required):
        codes.append("SYSTEMD_COMPATIBILITY_EVIDENCE_REQUIRED")
    if _value(compatibility, "systemd_access_authorized"):
        codes.append("SYSTEMD_ACCESS_NOT_AUTHORIZED")
    if _value(compatibility, "restart_action_authorized"):
        codes.append("SYSTEMD_RESTART_ACTION_NOT_AUTHORIZED")
    if _value(compatibility, "service_execution_authorized"):
        codes.append("SERVICE_EXECUTION_NOT_AUTHORIZED")
    if any(_value(compatibility, name) for name in (
        "signal_derived_termination_allowed", "core_dump_classification_allowed", "watchdog_trigger_classification_allowed",
    )):
        codes.append("SYSTEMD_COMPATIBILITY_EVIDENCE_REQUIRED")
    return _codes(*codes)


def _evidence_codes(
    checklist: ProcessExitBoundaryChecklistV1, operator: ProcessExitOperatorAttestationV1,
    reviewer: ProcessExitIndependentReviewerApprovalV1, evidence_timestamp: str, evidence_expiry_timestamp: str,
) -> tuple[str, ...]:
    codes: list[str] = []
    if not _value(checklist, "checklist_complete") or not _value(checklist, "all_gates_closed"):
        codes.append("SYSTEMD_COMPATIBILITY_EVIDENCE_REQUIRED")
    if not _value(operator, "operator_identity", "") or not _value(operator, "complete"):
        codes.append("OPERATOR_ATTESTATION_REQUIRED")
    if not _value(reviewer, "reviewer_identity", "") or not _value(reviewer, "complete"):
        codes.append("REVIEWER_APPROVAL_REQUIRED")
    if _value(operator, "operator_identity", "") and _value(operator, "operator_identity", "") == _value(reviewer, "reviewer_identity", ""):
        codes.append("OPERATOR_REVIEWER_COLLISION")
    if not evidence_timestamp or not evidence_expiry_timestamp or evidence_timestamp > evidence_expiry_timestamp:
        codes.append("EVIDENCE_EXPIRED")
    if _value(operator, "timestamp", "") > evidence_timestamp or _value(reviewer, "timestamp", "") > evidence_timestamp:
        codes.append("EVIDENCE_FROM_FUTURE")
    if _value(operator, "expiry_timestamp", "") < evidence_timestamp or _value(reviewer, "expiry_timestamp", "") < evidence_timestamp:
        codes.append("EVIDENCE_STALE")
    return _codes(*codes)


def _code_map(code_set: DeterministicExitCodeSetV1) -> dict[str, int]:
    return {
        item.classification: item.code for item in _value(code_set, "exit_code_identities", ())
        if isinstance(_value(item, "code", None), int) and not isinstance(_value(item, "code", None), bool)
    }


def evaluate_deterministic_process_exit_boundary_design_v1(
    *, policy: DeterministicProcessExitBoundaryPolicyV1, exit_code_set: DeterministicExitCodeSetV1,
    graceful_shutdown_mapping: GracefulShutdownExitMappingV1, fail_closed_mapping: FailClosedExitMappingV1,
    systemd_compatibility: SystemdExitStatusCompatibilityV1, checklist: ProcessExitBoundaryChecklistV1,
    operator_attestation: ProcessExitOperatorAttestationV1,
    reviewer_approval: ProcessExitIndependentReviewerApprovalV1,
    evidence_timestamp: str, evidence_expiry_timestamp: str,
) -> ProcessExitBoundaryDecisionV1:
    codes = _codes(
        *_policy_codes(policy), *_code_set_codes(exit_code_set),
        *_mapping_codes(graceful_shutdown_mapping, fail_closed_mapping),
        *_compatibility_codes(systemd_compatibility),
        *_evidence_codes(checklist, operator_attestation, reviewer_approval, evidence_timestamp, evidence_expiry_timestamp),
    )
    values = _result_values(codes)
    values.update(
        ready=not codes,
        decision_classification=(
            "DETERMINISTIC_PROCESS_EXIT_BOUNDARY_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION"
            if not codes else "NOT_READY"
        ),
        policy_id=_value(policy, "policy_id", ""), code_set_id=_value(exit_code_set, "code_set_id", ""),
        graceful_mapping_id=_value(graceful_shutdown_mapping, "mapping_id", ""),
        fail_closed_mapping_id=_value(fail_closed_mapping, "mapping_id", ""),
        compatibility_id=_value(systemd_compatibility, "compatibility_id", ""),
        exit_code_map=tuple(sorted(_code_map(exit_code_set).items())),
        graceful_mappings=tuple(_value(graceful_shutdown_mapping, "mappings", ())),
        internal_fail_closed_classification=_value(fail_closed_mapping, "internal_fail_closed_classification", ""),
        deployment_blocked=True,
    )
    return ProcessExitBoundaryDecisionV1(**values)


def classify_process_exit_without_execution_v1(
    *, decision: ProcessExitBoundaryDecisionV1,
    classification_request: ProcessExitClassificationRequestV1,
) -> ProcessExitClassificationResultV1:
    codes = list(_value(decision, "failure_codes", ()))
    source_state = _value(classification_request, "source_lifecycle_state", "")
    signal_name = _value(classification_request, "source_signal_classification", "")
    selected = _value(decision, "internal_fail_closed_classification", "INTERNAL_FAIL_CLOSED_EXIT")
    mapping = {(state, signal): classification for state, signal, classification in _value(decision, "graceful_mappings", ())}
    if not source_state:
        codes.append("SOURCE_STATE_EMPTY")
    elif source_state == "GRACEFUL_SHUTDOWN_COMPLETE" and signal_name not in ("SIGTERM", "SIGINT"):
        codes.append("UNSUPPORTED_SIGNAL_CONTEXT")
    elif (source_state, signal_name) in mapping:
        selected = mapping[(source_state, signal_name)]
    elif (source_state, "") in mapping:
        selected = mapping[(source_state, "")]
    else:
        codes.append("UNKNOWN_SOURCE_STATE")
    if any(_value(classification_request, gate) for gate in (
        "activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open",
    )):
        codes.append("ACTIVATION_GATE_MUST_REMAIN_CLOSED")
    if _value(classification_request, "service_execution_authorized"):
        codes.append("SERVICE_EXECUTION_NOT_AUTHORIZED")
    exit_map = dict(_value(decision, "exit_code_map", ()))
    selected_code = exit_map.get(selected, exit_map.get("INTERNAL_FAIL_CLOSED_EXIT", -1))
    ordered = _codes(*codes)
    values = _result_values(ordered)
    values.update(
        classification_result_id=_value(classification_request, "classification_request_id", ""),
        selected_exit_classification=selected, selected_exit_code=selected_code,
        mapping_identity=_value(decision, "graceful_mapping_id", ""), source_lifecycle_state=source_state,
        source_signal_classification=signal_name, ready=not ordered,
        blocked=bool(ordered), process_exit_executed=False, process_terminated=False,
        signal_transmitted=False, systemd_contacted=False, service_executed=False,
        production_runtime_executed=False,
    )
    return ProcessExitClassificationResultV1(**values)


def build_deterministic_process_exit_boundary_audit_evidence_v1(
    *, evidence_id: str, decision: ProcessExitBoundaryDecisionV1,
    classification_result: ProcessExitClassificationResultV1,
) -> ProcessExitBoundaryAuditEvidenceV1:
    codes = _codes(*_value(decision, "failure_codes", ()), *_value(classification_result, "failure_codes", ()))
    values = _result_values(codes)
    values.update(
        evidence_id=evidence_id, policy_id=_value(decision, "policy_id", ""),
        code_set_id=_value(decision, "code_set_id", ""),
        graceful_mapping_id=_value(decision, "graceful_mapping_id", ""),
        fail_closed_mapping_id=_value(decision, "fail_closed_mapping_id", ""),
        compatibility_id=_value(decision, "compatibility_id", ""),
        selected_exit_classification=_value(classification_result, "selected_exit_classification", ""),
        selected_exit_code=_value(classification_result, "selected_exit_code", -1),
    )
    return ProcessExitBoundaryAuditEvidenceV1(**values)
