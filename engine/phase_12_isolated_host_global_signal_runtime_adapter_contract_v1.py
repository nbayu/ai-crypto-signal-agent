"""Isolated, caller-injected host-global signal runtime test boundary."""
from __future__ import annotations

from dataclasses import dataclass


_ORDER = (
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


class IsolatedHostGlobalSignalRuntimePolicyV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalModuleAdapterV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalRegistrationRequestV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalPreviousHandlerV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalRegistrationStateV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalRegistrationResultV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalDispatchRequestV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalDispatchResultV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalRestorationRequestV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalRestorationResultV1(_Record):
    __slots__ = ()


class IsolatedHostGlobalSignalRollbackResultV1(_Record):
    __slots__ = ()


class IsolatedSystemdRuntimeLifecycleStateV1(_Record):
    __slots__ = ()


class IsolatedSystemdRuntimeLifecycleTransitionV1(_Record):
    __slots__ = ()


class IsolatedSystemdRuntimeLifecycleEvaluationV1(_Record):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class IsolatedHostGlobalSignalRuntimeFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


class IsolatedHostGlobalSignalRuntimeAuditEvidenceV1(_Record):
    __slots__ = ()


def _value(record: object, name: str, default: object = False) -> object:
    return getattr(record, name, default)


def _codes(*codes: str) -> tuple[str, ...]:
    selected = set(codes)
    return tuple(code for code in _ORDER if code in selected)


def _failures(codes: tuple[str, ...]) -> tuple[IsolatedHostGlobalSignalRuntimeFailureV1, ...]:
    return tuple(IsolatedHostGlobalSignalRuntimeFailureV1(code, "fail-closed isolated metadata rejection", False) for code in codes)


def _closed() -> dict[str, bool]:
    return {
        "activation_gate_open": False, "credential_gate_open": False,
        "network_gate_open": False, "workload_gate_open": False,
        "direct_host_global_registration_authorized": False,
        "production_service_execution_authorized": False,
        "production_cli_execution_authorized": False,
        "production_runtime_execution_authorized": False,
        "process_exit_execution_authorized": False,
        "process_termination_authorized": False,
        "process_signal_transmission_authorized": False,
        "credential_access_authorized": False,
        "credential_loading_authorized": False,
        "credential_validation_authorized": False,
        "systemd_access_authorized": False, "network_authorized": False,
        "provider_transmission_authorized": False,
        "scanner_execution_authorized": False, "worker_start_authorized": False,
        "scheduler_start_authorized": False, "telegram_start_authorized": False,
        "database_mutation_authorized": False,
        "artifact_publication_authorized": False, "trading_authorized": False,
        "subprocess_authorized": False, "thread_creation_authorized": False,
        "event_loop_start_authorized": False,
        "runtime_activation_authorized": False, "publication_authorized": False,
        "fail_closed": True,
    }


def _state(state: IsolatedHostGlobalSignalRegistrationStateV1, state_code: str, **changes: object) -> IsolatedHostGlobalSignalRegistrationStateV1:
    values = dict(state.values)
    values.update(changes)
    values["state_code"] = state_code
    values.update({key: False for key in ("activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open")})
    return IsolatedHostGlobalSignalRegistrationStateV1(**values)


def _policy_codes(policy: IsolatedHostGlobalSignalRuntimePolicyV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not isinstance(_value(policy, "policy_id", ""), str) or not _value(policy, "policy_id", ""):
        codes.append("POLICY_ID_EMPTY")
    if not isinstance(_value(policy, "policy_version", ""), str) or not _value(policy, "policy_version", ""):
        codes.append("POLICY_VERSION_EMPTY")
    for name, code in (
        ("host_global_signal_adapter_implementation_authorized", "HOST_GLOBAL_ADAPTER_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("main_thread_signal_registration_implementation_authorized", "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("handler_restoration_implementation_authorized", "HANDLER_RESTORATION_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("systemd_runtime_lifecycle_evaluator_implementation_authorized", "SYSTEMD_LIFECYCLE_EVALUATOR_NOT_AUTHORIZED"),
        ("isolated_test_mode_required", "ISOLATED_TEST_MODE_REQUIRED"),
    ):
        if not _value(policy, name):
            codes.append(code)
    for name, code in (
        ("process_exit_execution_authorized", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
        ("process_termination_authorized", "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        ("process_signal_transmission_authorized", "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
        ("implicit_sys_argv_access_authorized", "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED"),
        ("environment_read_authorized", "ENVIRONMENT_READ_NOT_AUTHORIZED"),
        ("filesystem_read_authorized", "FILESYSTEM_READ_NOT_AUTHORIZED"),
        ("filesystem_write_authorized", "FILESYSTEM_WRITE_NOT_AUTHORIZED"),
        ("credential_access_authorized", "CREDENTIAL_ACCESS_NOT_AUTHORIZED"),
        ("credential_loading_authorized", "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ("systemd_access_authorized", "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        ("production_service_execution_authorized", "SERVICE_EXECUTION_NOT_AUTHORIZED"),
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


def _adapter_codes(adapter: IsolatedHostGlobalSignalModuleAdapterV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not _value(adapter, "isolated_test_adapter"):
        codes.append("ISOLATED_SIGNAL_ADAPTER_REQUIRED")
    if not _value(adapter, "monkeypatched_signal_module"):
        codes.append("MONKEYPATCHED_SIGNAL_MODULE_REQUIRED")
    if _value(adapter, "host_process_signal_module"):
        codes.append("HOST_PROCESS_SIGNAL_MODULE_NOT_AUTHORIZED")
    if _value(adapter, "direct_host_registration_allowed"):
        codes.append("DIRECT_HOST_GLOBAL_REGISTRATION_NOT_AUTHORIZED")
    for name in ("get_handler", "set_handler", "restore_handler"):
        if not callable(_value(adapter, name, None)):
            codes.append("ISOLATED_SIGNAL_ADAPTER_REQUIRED")
    return _codes(*codes)


def _registration_codes(request: IsolatedHostGlobalSignalRegistrationRequestV1, state: IsolatedHostGlobalSignalRegistrationStateV1) -> tuple[str, ...]:
    codes: list[str] = []
    thread = _value(request, "thread_classification", "")
    if not thread:
        codes.append("CALLER_SUPPLIED_THREAD_CLASSIFICATION_REQUIRED")
    elif thread != "MAIN_THREAD":
        codes.append("MAIN_THREAD_CLASSIFICATION_REQUIRED")
    signals = _value(request, "requested_signals", ())
    if signals != ("SIGTERM", "SIGINT"):
        codes.append("UNSUPPORTED_SIGNAL_REGISTRATION" if "SIGHUP" in signals else "SIGNAL_SET_MISMATCH")
    if _value(request, "duplicate_registration_requested") or _value(state, "registration_complete"):
        codes.append("DUPLICATE_SIGNAL_REGISTRATION")
    if not _value(request, "configuration_validated") or not _value(state, "configuration_validated"):
        codes.append("CONFIGURATION_VALIDATION_REQUIRED")
    if _value(request, "passive_readiness_entered") or _value(state, "passive_ready"):
        codes.append("REGISTRATION_AFTER_PASSIVE_READINESS_NOT_ALLOWED")
    if _value(request, "registration_order", ()) != ("CAPTURE_SIGTERM", "INSTALL_SIGTERM", "CAPTURE_SIGINT", "INSTALL_SIGINT"):
        codes.append("SIGNAL_REGISTRATION_ORDER_INVALID")
    if not _value(request, "restoration_required"):
        codes.append("HANDLER_RESTORATION_REQUIRED")
    return _codes(*codes)


def _result_values(policy: IsolatedHostGlobalSignalRuntimePolicyV1, codes: tuple[str, ...]) -> dict[str, object]:
    values: dict[str, object] = {"failure_codes": codes, "failures": _failures(codes)}
    values.update(_closed())
    return values


def _classification(previous: object) -> str:
    if previous == "DEFAULT":
        return "DEFAULT_HANDLER"
    if previous == "IGNORE":
        return "IGNORE_HANDLER"
    if callable(previous):
        return "CALLABLE_HANDLER"
    return "UNKNOWN_HANDLER"


def register_isolated_host_global_signal_handlers_v1(
    *, policy: IsolatedHostGlobalSignalRuntimePolicyV1, adapter: IsolatedHostGlobalSignalModuleAdapterV1,
    request: IsolatedHostGlobalSignalRegistrationRequestV1, state: IsolatedHostGlobalSignalRegistrationStateV1,
) -> IsolatedHostGlobalSignalRegistrationResultV1:
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter), *_registration_codes(request, state))
    if codes:
        values = _result_values(policy, codes)
        values.update(registered=False, previous_handlers=(), current_state=_state(state, "BLOCKED"))
        return IsolatedHostGlobalSignalRegistrationResultV1(**values)
    previous_handlers: list[IsolatedHostGlobalSignalPreviousHandlerV1] = []
    partial_state = _state(state, "SIGNAL_REGISTRATION_STARTED", registration_started=True)
    try:
        previous_term = adapter.get_handler("SIGTERM")
        previous_handlers.append(IsolatedHostGlobalSignalPreviousHandlerV1(
            previous_handler_id="sigterm-previous-handler-v1", signal_name="SIGTERM",
            classification=_classification(previous_term), handler_identity=request.handler_identity,
            restoration_order=2, captured=True,
        ))
        adapter.set_handler("SIGTERM", request.handler_identity)
        partial_state = _state(partial_state, "SIGNAL_REGISTRATION_PARTIAL", sigterm_registered=True)
        previous_int = adapter.get_handler("SIGINT")
        previous_handlers.append(IsolatedHostGlobalSignalPreviousHandlerV1(
            previous_handler_id="sigint-previous-handler-v1", signal_name="SIGINT",
            classification=_classification(previous_int), handler_identity=request.handler_identity,
            restoration_order=1, captured=True,
        ))
        adapter.set_handler("SIGINT", request.handler_identity)
    except Exception:
        values = _result_values(policy, _codes("PARTIAL_REGISTRATION_ROLLBACK_REQUIRED"))
        values.update(registered=False, previous_handlers=tuple(previous_handlers), current_state=partial_state)
        return IsolatedHostGlobalSignalRegistrationResultV1(**values)
    complete = _state(
        partial_state, "SIGNAL_REGISTRATION_COMPLETE", registration_complete=True,
        sigterm_registered=True, sigint_registered=True,
    )
    values = _result_values(policy, ())
    values.update(registered=True, previous_handlers=tuple(previous_handlers), current_state=complete)
    return IsolatedHostGlobalSignalRegistrationResultV1(**values)


def rollback_partial_isolated_signal_registration_v1(
    *, policy: IsolatedHostGlobalSignalRuntimePolicyV1, adapter: IsolatedHostGlobalSignalModuleAdapterV1,
    rollback_id: str, previous_handlers: tuple[IsolatedHostGlobalSignalPreviousHandlerV1, ...],
    state: IsolatedHostGlobalSignalRegistrationStateV1,
) -> IsolatedHostGlobalSignalRollbackResultV1:
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter))
    term = next((item for item in previous_handlers if item.signal_name == "SIGTERM"), None)
    if term is None:
        codes = _codes(*codes, "PREVIOUS_HANDLER_CAPTURE_REQUIRED")
    if codes:
        values = _result_values(policy, codes)
        values.update(rollback_id=rollback_id, rolled_back=False, current_state=_state(state, "BLOCKED"))
        return IsolatedHostGlobalSignalRollbackResultV1(**values)
    if _value(state, "handlers_restored"):
        values = _result_values(policy, ())
        values.update(rollback_id=rollback_id, rolled_back=True, idempotent=True, current_state=state)
        return IsolatedHostGlobalSignalRollbackResultV1(**values)
    try:
        adapter.restore_handler("SIGTERM", "DEFAULT" if term.classification == "DEFAULT_HANDLER" else "IGNORE")
    except Exception:
        values = _result_values(policy, _codes("PARTIAL_REGISTRATION_ROLLBACK_FAILED"))
        values.update(rollback_id=rollback_id, rolled_back=False, current_state=_state(state, "BLOCKED"))
        return IsolatedHostGlobalSignalRollbackResultV1(**values)
    rolled = _state(state, "ROLLBACK_COMPLETE", registration_complete=False, sigterm_registered=False,
                    sigint_registered=False, handlers_restored=True)
    values = _result_values(policy, ())
    values.update(rollback_id=rollback_id, rolled_back=True, idempotent=False, current_state=rolled)
    return IsolatedHostGlobalSignalRollbackResultV1(**values)


def restore_isolated_host_global_signal_handlers_v1(
    *, policy: IsolatedHostGlobalSignalRuntimePolicyV1, adapter: IsolatedHostGlobalSignalModuleAdapterV1,
    request: IsolatedHostGlobalSignalRestorationRequestV1,
    previous_handlers: tuple[IsolatedHostGlobalSignalPreviousHandlerV1, ...],
    state: IsolatedHostGlobalSignalRegistrationStateV1,
) -> IsolatedHostGlobalSignalRestorationResultV1:
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter))
    if not _value(request, "restoration_required"):
        codes = _codes(*codes, "HANDLER_RESTORATION_REQUIRED")
    if _value(request, "restoration_order", ()) != ("SIGINT", "SIGTERM"):
        codes = _codes(*codes, "HANDLER_RESTORATION_ORDER_INVALID")
    if len(previous_handlers) != 2:
        codes = _codes(*codes, "PREVIOUS_HANDLER_CAPTURE_REQUIRED")
    if codes:
        values = _result_values(policy, codes)
        values.update(restored=False, idempotent=False, current_state=_state(state, "BLOCKED"))
        return IsolatedHostGlobalSignalRestorationResultV1(**values)
    if _value(state, "handlers_restored"):
        values = _result_values(policy, ())
        values.update(restored=True, idempotent=True, current_state=state)
        return IsolatedHostGlobalSignalRestorationResultV1(**values)
    by_signal = {item.signal_name: item for item in previous_handlers}
    try:
        for signal_name in ("SIGINT", "SIGTERM"):
            item = by_signal[signal_name]
            previous = "DEFAULT" if item.classification == "DEFAULT_HANDLER" else "IGNORE"
            adapter.restore_handler(signal_name, previous)
    except Exception:
        values = _result_values(policy, _codes("HANDLER_RESTORATION_FAILED"))
        values.update(restored=False, idempotent=False, current_state=_state(state, "BLOCKED"))
        return IsolatedHostGlobalSignalRestorationResultV1(**values)
    restored = _state(state, "HANDLER_RESTORATION_COMPLETE", handlers_restored=True)
    values = _result_values(policy, ())
    values.update(restored=True, idempotent=False, current_state=restored)
    return IsolatedHostGlobalSignalRestorationResultV1(**values)


def dispatch_isolated_host_global_signal_v1(
    *, policy: IsolatedHostGlobalSignalRuntimePolicyV1,
    request: IsolatedHostGlobalSignalDispatchRequestV1,
    state: IsolatedHostGlobalSignalRegistrationStateV1,
) -> IsolatedHostGlobalSignalDispatchResultV1:
    codes = _policy_codes(policy)
    signal_name = _value(request, "signal_classification", "UNKNOWN")
    state_code = state.state_code
    classification = "INVALID_LIFECYCLE_TRANSITION"
    next_state = state
    if signal_name in ("SIGTERM", "SIGINT") and state_code == "PASSIVE_READY":
        classification = "SHUTDOWN_REQUESTED"
        next_state = _state(state, "SHUTDOWN_REQUESTED", shutdown_requested=True)
    elif signal_name in ("SIGTERM", "SIGINT") and state_code in ("SHUTDOWN_REQUESTED", "GRACEFUL_SHUTDOWN_COMPLETE"):
        classification = state_code
    elif signal_name == "SIGHUP":
        classification = "RELOAD_NOT_AUTHORIZED"
        codes = _codes(*codes, "RELOAD_NOT_AUTHORIZED")
    elif signal_name == "UNKNOWN":
        classification = "UNKNOWN_HOST_GLOBAL_SIGNAL"
        codes = _codes(*codes, "UNKNOWN_HOST_GLOBAL_SIGNAL")
    else:
        codes = _codes(*codes, "INVALID_LIFECYCLE_TRANSITION")
    values = _result_values(policy, _codes(*codes))
    values.update(dispatch_id=_value(request, "dispatch_id", ""), dispatch_classification=classification,
                  current_state=next_state)
    return IsolatedHostGlobalSignalDispatchResultV1(**values)


def evaluate_isolated_systemd_runtime_startup_v1(
    *, policy: IsolatedHostGlobalSignalRuntimePolicyV1, adapter: IsolatedHostGlobalSignalModuleAdapterV1,
    thread_classification: str, registration_state: IsolatedHostGlobalSignalRegistrationStateV1,
    explicit_cli_validated: bool, configuration_validated: bool, passive_readiness_requested: bool,
) -> IsolatedSystemdRuntimeLifecycleEvaluationV1:
    codes = list(_policy_codes(policy)) + list(_adapter_codes(adapter))
    if not thread_classification:
        codes.append("CALLER_SUPPLIED_THREAD_CLASSIFICATION_REQUIRED")
    elif thread_classification != "MAIN_THREAD":
        codes.append("MAIN_THREAD_CLASSIFICATION_REQUIRED")
    if not explicit_cli_validated or not configuration_validated:
        codes.append("CONFIGURATION_VALIDATION_REQUIRED")
    if not _value(registration_state, "registration_complete"):
        codes.append("INVALID_LIFECYCLE_TRANSITION")
    if not passive_readiness_requested:
        codes.append("INVALID_LIFECYCLE_TRANSITION")
    ordered = _codes(*codes)
    current = _state(registration_state, "PASSIVE_READY", passive_ready=True) if not ordered else _state(registration_state, "BLOCKED")
    values = _result_values(policy, ordered)
    values.update(ready=not ordered,
                  evaluation_classification=("ISOLATED_SYSTEMD_RUNTIME_PASSIVE_READY_FOR_TEST_ONLY" if not ordered else "BLOCKED"),
                  current_state=current)
    return IsolatedSystemdRuntimeLifecycleEvaluationV1(**values)


def evaluate_isolated_systemd_runtime_shutdown_v1(
    *, policy: IsolatedHostGlobalSignalRuntimePolicyV1,
    dispatch_result: IsolatedHostGlobalSignalDispatchResultV1,
    restoration_result: IsolatedHostGlobalSignalRestorationResultV1,
    deterministic_exit_classification: str,
) -> IsolatedSystemdRuntimeLifecycleEvaluationV1:
    codes = list(_policy_codes(policy))
    if dispatch_result.current_state.state_code != "SHUTDOWN_REQUESTED":
        codes.append("INVALID_LIFECYCLE_TRANSITION")
    if not restoration_result.restored:
        codes.append("HANDLER_RESTORATION_REQUIRED")
    if not deterministic_exit_classification:
        codes.append("INVALID_LIFECYCLE_TRANSITION")
    ordered = _codes(*codes)
    basis = restoration_result.current_state
    current = _state(basis, "GRACEFUL_SHUTDOWN_COMPLETE", graceful_shutdown_complete=True,
                     shutdown_requested=True) if not ordered else _state(basis, "BLOCKED")
    values = _result_values(policy, ordered)
    values.update(ready=not ordered,
                  evaluation_classification=("ISOLATED_SYSTEMD_RUNTIME_GRACEFUL_SHUTDOWN_COMPLETE_FOR_TEST_ONLY" if not ordered else "BLOCKED"),
                  exit_classification=deterministic_exit_classification, current_state=current)
    return IsolatedSystemdRuntimeLifecycleEvaluationV1(**values)


def build_isolated_host_global_signal_runtime_audit_evidence_v1(
    *, evidence_id: str, policy: IsolatedHostGlobalSignalRuntimePolicyV1,
    adapter: IsolatedHostGlobalSignalModuleAdapterV1,
    registration_result: IsolatedHostGlobalSignalRegistrationResultV1,
    dispatch_result: IsolatedHostGlobalSignalDispatchResultV1 | None,
    restoration_result: IsolatedHostGlobalSignalRestorationResultV1 | None,
    rollback_result: IsolatedHostGlobalSignalRollbackResultV1 | None,
    lifecycle_evaluation: IsolatedSystemdRuntimeLifecycleEvaluationV1 | None,
) -> IsolatedHostGlobalSignalRuntimeAuditEvidenceV1:
    del dispatch_result, restoration_result, rollback_result, lifecycle_evaluation
    values = _result_values(policy, registration_result.failure_codes)
    values.update(
        evidence_id=evidence_id, policy_id=policy.policy_id, adapter_id=adapter.adapter_id,
        registration_id=_value(registration_result, "registration_id", "isolated-host-registration-v1"),
        failure_codes=registration_result.failure_codes,
        previous_handler_classifications=tuple(item.classification for item in registration_result.previous_handlers),
    )
    return IsolatedHostGlobalSignalRuntimeAuditEvidenceV1(**values)
