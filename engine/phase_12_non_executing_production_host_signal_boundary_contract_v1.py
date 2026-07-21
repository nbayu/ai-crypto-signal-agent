"""Non-executing, dependency-injected production host-signal boundary."""
from __future__ import annotations

from dataclasses import dataclass


_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY",
    "HOST_SIGNAL_ADAPTER_IMPLEMENTATION_NOT_AUTHORIZED",
    "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED",
    "HANDLER_INSTALLATION_IMPLEMENTATION_NOT_AUTHORIZED",
    "HANDLER_RESTORATION_IMPLEMENTATION_NOT_AUTHORIZED",
    "SIGNAL_DISPATCH_IMPLEMENTATION_NOT_AUTHORIZED",
    "GRACEFUL_SHUTDOWN_STATE_MACHINE_NOT_AUTHORIZED",
    "NON_EXECUTING_DEPENDENCY_INJECTED_MODE_REQUIRED",
    "PRODUCTION_HOST_SIGNAL_ADAPTER_REQUIRED",
    "STANDARD_LIBRARY_SIGNAL_MODULE_NOT_AUTHORIZED",
    "HOST_PROCESS_SIGNAL_MODULE_NOT_AUTHORIZED",
    "REAL_HOST_HANDLER_INSTALLATION_NOT_AUTHORIZED",
    "REAL_HOST_HANDLER_RESTORATION_NOT_AUTHORIZED",
    "ACTUAL_SIGNAL_TRANSMISSION_NOT_AUTHORIZED",
    "CALLER_SUPPLIED_THREAD_CLASSIFICATION_REQUIRED",
    "MAIN_THREAD_CLASSIFICATION_REQUIRED", "CONFIGURATION_VALIDATION_REQUIRED",
    "SIGNAL_SET_MISMATCH", "DUPLICATE_SIGNAL_REGISTRATION",
    "UNSUPPORTED_SIGNAL_REGISTRATION", "PREVIOUS_HANDLER_CAPTURE_REQUIRED",
    "PREVIOUS_HANDLER_REDACTION_REQUIRED", "RAW_HANDLER_REPRESENTATION_NOT_ALLOWED",
    "HANDLER_MEMORY_ADDRESS_EXPOSURE_NOT_ALLOWED", "HANDLER_INSTALLATION_ORDER_INVALID",
    "PARTIAL_REGISTRATION_ROLLBACK_REQUIRED", "PARTIAL_REGISTRATION_ROLLBACK_FAILED",
    "HANDLER_RESTORATION_REQUIRED", "HANDLER_RESTORATION_ORDER_INVALID",
    "HANDLER_RESTORATION_NOT_IDEMPOTENT", "HANDLER_RESTORATION_FAILED",
    "INVALID_GRACEFUL_SHUTDOWN_TRANSITION", "RELOAD_NOT_AUTHORIZED",
    "UNKNOWN_HOST_GLOBAL_SIGNAL", "PRODUCTION_PROCESS_EXIT_IMPLEMENTATION_NOT_AUTHORIZED",
    "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED", "PROCESS_TERMINATION_NOT_AUTHORIZED",
    "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED",
    "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED",
    "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED", "ENVIRONMENT_READ_NOT_AUTHORIZED",
    "FILESYSTEM_READ_NOT_AUTHORIZED", "FILESYSTEM_WRITE_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "SYSTEMD_ACCESS_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED",
    "TELEGRAM_START_NOT_AUTHORIZED", "DATABASE_MUTATION_NOT_AUTHORIZED",
    "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "SUBPROCESS_NOT_AUTHORIZED", "THREAD_CREATION_NOT_AUTHORIZED",
    "EVENT_LOOP_START_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "PUBLICATION_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED",
    "WORKLOAD_GATE_MUST_REMAIN_CLOSED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "PROVIDER_MATERIAL_EXPOSURE_DETECTED", "PROCESS_METADATA_EXPOSURE_DETECTED",
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


class ProductionHostSignalBoundaryPolicyV1(_Record):
    __slots__ = ()


class ProductionHostSignalAdapterV1(_Record):
    __slots__ = ()


class ProductionHostSignalRegistrationRequestV1(_Record):
    __slots__ = ()


class ProductionHostSignalPreviousHandlerV1(_Record):
    __slots__ = ()


class ProductionHostSignalRegistrationStateV1(_Record):
    __slots__ = ()


class ProductionHostSignalRegistrationResultV1(_Record):
    __slots__ = ()


class ProductionHostSignalHandlerRequestV1(_Record):
    __slots__ = ()


class ProductionHostSignalHandlerResultV1(_Record):
    __slots__ = ()


class ProductionHostSignalDispatchRequestV1(_Record):
    __slots__ = ()


class ProductionHostSignalDispatchResultV1(_Record):
    __slots__ = ()


class ProductionHostSignalRestorationRequestV1(_Record):
    __slots__ = ()


class ProductionHostSignalRestorationResultV1(_Record):
    __slots__ = ()


class ProductionHostSignalRollbackResultV1(_Record):
    __slots__ = ()


class ProductionGracefulShutdownStateV1(_Record):
    __slots__ = ()


class ProductionGracefulShutdownTransitionV1(_Record):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ProductionHostSignalBoundaryFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


class ProductionHostSignalBoundaryAuditEvidenceV1(_Record):
    __slots__ = ()


def _value(record: object, name: str, default: object = False) -> object:
    return getattr(record, name, default)


def _codes(*codes: str) -> tuple[str, ...]:
    selected = set(codes)
    return tuple(code for code in _ORDER if code in selected)


def _failures(codes: tuple[str, ...]) -> tuple[ProductionHostSignalBoundaryFailureV1, ...]:
    return tuple(
        ProductionHostSignalBoundaryFailureV1(code, "fail-closed non-executing boundary rejection", False)
        for code in codes
    )


def _closed() -> dict[str, bool]:
    return {
        "activation_gate_open": False, "credential_gate_open": False,
        "network_gate_open": False, "workload_gate_open": False,
        "direct_standard_library_signal_registration_authorized": False,
        "real_host_handler_installation_authorized": False,
        "real_host_handler_restoration_authorized": False,
        "actual_signal_transmission_authorized": False,
        "production_process_exit_implementation_authorized": False,
        "process_exit_execution_authorized": False, "process_termination_authorized": False,
        "process_signal_transmission_authorized": False,
        "production_cli_execution_authorized": False,
        "production_service_execution_authorized": False,
        "production_runtime_execution_authorized": False,
        "credential_access_authorized": False, "credential_loading_authorized": False,
        "credential_validation_authorized": False, "systemd_access_authorized": False,
        "network_authorized": False, "provider_transmission_authorized": False,
        "scanner_execution_authorized": False, "worker_start_authorized": False,
        "scheduler_start_authorized": False, "telegram_start_authorized": False,
        "database_mutation_authorized": False, "artifact_publication_authorized": False,
        "trading_authorized": False, "subprocess_authorized": False,
        "thread_creation_authorized": False, "event_loop_start_authorized": False,
        "runtime_activation_authorized": False, "publication_authorized": False,
        "fail_closed": True,
    }


def _state(
    state: ProductionHostSignalRegistrationStateV1, state_code: str, **changes: object,
) -> ProductionHostSignalRegistrationStateV1:
    values = dict(state.values)
    values.update(changes)
    values["state_code"] = state_code
    values.update({name: False for name in (
        "activation_gate_open", "credential_gate_open", "network_gate_open", "workload_gate_open",
    )})
    return ProductionHostSignalRegistrationStateV1(**values)


def _result_values(codes: tuple[str, ...]) -> dict[str, object]:
    values: dict[str, object] = {"failure_codes": codes, "failures": _failures(codes)}
    values.update(_closed())
    return values


def _policy_codes(policy: ProductionHostSignalBoundaryPolicyV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not isinstance(_value(policy, "policy_id", ""), str) or not _value(policy, "policy_id", ""):
        codes.append("POLICY_ID_EMPTY")
    if not isinstance(_value(policy, "policy_version", ""), str) or not _value(policy, "policy_version", ""):
        codes.append("POLICY_VERSION_EMPTY")
    for name, code in (
        ("production_host_global_signal_adapter_implementation_authorized", "HOST_SIGNAL_ADAPTER_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("production_main_thread_registration_implementation_authorized", "MAIN_THREAD_REGISTRATION_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("production_handler_installation_implementation_authorized", "HANDLER_INSTALLATION_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("production_handler_restoration_implementation_authorized", "HANDLER_RESTORATION_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("production_signal_dispatch_implementation_authorized", "SIGNAL_DISPATCH_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("production_graceful_shutdown_state_machine_implementation_authorized", "GRACEFUL_SHUTDOWN_STATE_MACHINE_NOT_AUTHORIZED"),
        ("non_executing_dependency_injected_boundary_only", "NON_EXECUTING_DEPENDENCY_INJECTED_MODE_REQUIRED"),
    ):
        if not _value(policy, name):
            codes.append(code)
    for name, code in (
        ("direct_standard_library_signal_registration_authorized", "STANDARD_LIBRARY_SIGNAL_MODULE_NOT_AUTHORIZED"),
        ("real_host_handler_installation_authorized", "REAL_HOST_HANDLER_INSTALLATION_NOT_AUTHORIZED"),
        ("real_host_handler_restoration_authorized", "REAL_HOST_HANDLER_RESTORATION_NOT_AUTHORIZED"),
        ("actual_signal_transmission_authorized", "ACTUAL_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
        ("production_process_exit_implementation_authorized", "PRODUCTION_PROCESS_EXIT_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("process_exit_execution_authorized", "PROCESS_EXIT_EXECUTION_NOT_AUTHORIZED"),
        ("process_termination_authorized", "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        ("process_signal_transmission_authorized", "PROCESS_SIGNAL_TRANSMISSION_NOT_AUTHORIZED"),
        ("production_cli_execution_authorized", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED"),
        ("production_service_execution_authorized", "PRODUCTION_SERVICE_EXECUTION_NOT_AUTHORIZED"),
        ("production_runtime_execution_authorized", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED"),
        ("implicit_sys_argv_access_authorized", "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED"),
        ("environment_read_authorized", "ENVIRONMENT_READ_NOT_AUTHORIZED"),
        ("filesystem_read_authorized", "FILESYSTEM_READ_NOT_AUTHORIZED"),
        ("filesystem_write_authorized", "FILESYSTEM_WRITE_NOT_AUTHORIZED"),
        ("credential_access_authorized", "CREDENTIAL_ACCESS_NOT_AUTHORIZED"),
        ("credential_loading_authorized", "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ("systemd_access_authorized", "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
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


def _adapter_codes(adapter: ProductionHostSignalAdapterV1) -> tuple[str, ...]:
    codes: list[str] = []
    if not _value(adapter, "dependency_injected") or not _value(adapter, "non_executing_boundary"):
        codes.append("PRODUCTION_HOST_SIGNAL_ADAPTER_REQUIRED")
    if _value(adapter, "standard_library_signal_module"):
        codes.append("STANDARD_LIBRARY_SIGNAL_MODULE_NOT_AUTHORIZED")
    if _value(adapter, "host_process_signal_module"):
        codes.append("HOST_PROCESS_SIGNAL_MODULE_NOT_AUTHORIZED")
    if _value(adapter, "real_host_handler_mutation_allowed"):
        codes.append("REAL_HOST_HANDLER_INSTALLATION_NOT_AUTHORIZED")
    if _value(adapter, "actual_signal_transmission_allowed"):
        codes.append("ACTUAL_SIGNAL_TRANSMISSION_NOT_AUTHORIZED")
    for name in ("capture_handler", "install_handler", "restore_handler"):
        if not callable(_value(adapter, name, None)):
            codes.append("PRODUCTION_HOST_SIGNAL_ADAPTER_REQUIRED")
    return _codes(*codes)


def _registration_codes(
    request: ProductionHostSignalRegistrationRequestV1,
    state: ProductionHostSignalRegistrationStateV1,
) -> tuple[str, ...]:
    codes: list[str] = []
    thread = _value(request, "thread_classification", "")
    if not thread:
        codes.append("CALLER_SUPPLIED_THREAD_CLASSIFICATION_REQUIRED")
    elif thread != "MAIN_THREAD":
        codes.append("MAIN_THREAD_CLASSIFICATION_REQUIRED")
    signals = _value(request, "signal_names", ())
    if len(signals) != len(set(signals)) or _value(request, "duplicate_registration_requested") or _value(state, "registration_complete"):
        codes.append("DUPLICATE_SIGNAL_REGISTRATION")
    if signals != ("SIGTERM", "SIGINT"):
        codes.append("UNSUPPORTED_SIGNAL_REGISTRATION" if any(name not in ("SIGTERM", "SIGINT") for name in signals) else "SIGNAL_SET_MISMATCH")
    if not _value(request, "configuration_validated") or not _value(state, "configuration_validated"):
        codes.append("CONFIGURATION_VALIDATION_REQUIRED")
    if _value(request, "passive_readiness_entered") or _value(state, "passive_ready"):
        codes.append("HANDLER_INSTALLATION_ORDER_INVALID")
    if _value(request, "registration_order", ()) != (
        "CAPTURE_SIGTERM", "PREPARE_SIGTERM", "CAPTURE_SIGINT", "PREPARE_SIGINT",
    ):
        codes.append("HANDLER_INSTALLATION_ORDER_INVALID")
    if not _value(request, "sigterm_handler_token", "") or not _value(request, "sigint_handler_token", ""):
        codes.append("PREVIOUS_HANDLER_REDACTION_REQUIRED")
    return _codes(*codes)


def _classification(token: object) -> str:
    if token == "DEFAULT":
        return "DEFAULT_HANDLER"
    if token == "IGNORE":
        return "IGNORE_HANDLER"
    return "CALLABLE_HANDLER" if callable(token) else "UNKNOWN_HANDLER"


def register_production_host_signal_handlers_v1(
    *, policy: ProductionHostSignalBoundaryPolicyV1, adapter: ProductionHostSignalAdapterV1,
    registration_request: ProductionHostSignalRegistrationRequestV1,
    state: ProductionHostSignalRegistrationStateV1,
) -> ProductionHostSignalRegistrationResultV1:
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter), *_registration_codes(registration_request, state))
    if codes:
        values = _result_values(codes)
        values.update(registration_id=_value(registration_request, "registration_id", ""), ready=False,
                      previous_handlers=(), current_state=_state(state, "BLOCKED"))
        return ProductionHostSignalRegistrationResultV1(**values)
    previous: list[ProductionHostSignalPreviousHandlerV1] = []
    try:
        for signal_name, token, order in (
            ("SIGTERM", registration_request.sigterm_handler_token, 2),
            ("SIGINT", registration_request.sigint_handler_token, 1),
        ):
            captured = adapter.capture_handler(signal_name)
            previous.append(ProductionHostSignalPreviousHandlerV1(
                signal_name=signal_name, classification=_classification(captured),
                handler_token=captured if isinstance(captured, str) else "REDACTED_HANDLER_TOKEN",
                captured=True, restoration_order=order,
            ))
            del token
    except Exception:
        values = _result_values(_codes("PREVIOUS_HANDLER_CAPTURE_REQUIRED"))
        values.update(registration_id=registration_request.registration_id, ready=False,
                      previous_handlers=tuple(previous), current_state=_state(state, "BLOCKED"))
        return ProductionHostSignalRegistrationResultV1(**values)
    prepared = _state(state, "REGISTRATION_PREPARED", registration_complete=True, handlers_prepared=False)
    values = _result_values(())
    values.update(registration_id=registration_request.registration_id, ready=True,
                  previous_handlers=tuple(previous), current_state=prepared,
                  signal_names=("SIGTERM", "SIGINT"))
    return ProductionHostSignalRegistrationResultV1(**values)


def install_production_host_signal_handlers_v1(
    *, policy: ProductionHostSignalBoundaryPolicyV1, adapter: ProductionHostSignalAdapterV1,
    handler_request: ProductionHostSignalHandlerRequestV1,
    registration_result: ProductionHostSignalRegistrationResultV1,
) -> ProductionHostSignalHandlerResultV1:
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter))
    if not _value(registration_result, "ready"):
        codes = _codes(*codes, "HANDLER_INSTALLATION_ORDER_INVALID")
    tokens = _value(handler_request, "handler_tokens", ())
    # Handler tokens are caller supplied; only shape and nonblankness are relevant here.
    if not isinstance(tokens, tuple) or len(tokens) != 2 or not all(isinstance(item, str) and item for item in tokens):
        codes = _codes(*codes, "HANDLER_INSTALLATION_ORDER_INVALID")
    if codes:
        basis = _value(registration_result, "current_state", ProductionHostSignalRegistrationStateV1())
        values = _result_values(codes)
        values.update(handler_id=_value(handler_request, "handler_id", ""), installed=False,
                      current_state=_state(basis, "BLOCKED"))
        return ProductionHostSignalHandlerResultV1(**values)
    state = registration_result.current_state
    try:
        adapter.install_handler("SIGTERM", tokens[0])
        adapter.install_handler("SIGINT", tokens[1])
    except Exception:
        values = _result_values(_codes("PARTIAL_REGISTRATION_ROLLBACK_REQUIRED"))
        values.update(handler_id=handler_request.handler_id, installed=False,
                      current_state=_state(state, "ROLLBACK_REQUIRED", handlers_prepared=False))
        return ProductionHostSignalHandlerResultV1(**values)
    installed = _state(state, "HANDLERS_PREPARED", handlers_prepared=True, registration_complete=True)
    values = _result_values(())
    values.update(handler_id=handler_request.handler_id, installed=True, current_state=installed)
    return ProductionHostSignalHandlerResultV1(**values)


def rollback_partial_production_host_signal_registration_v1(
    *, policy: ProductionHostSignalBoundaryPolicyV1, adapter: ProductionHostSignalAdapterV1,
    rollback_id: str, previous_handlers: tuple[ProductionHostSignalPreviousHandlerV1, ...],
    state: ProductionHostSignalRegistrationStateV1,
) -> ProductionHostSignalRollbackResultV1:
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter))
    term = next((item for item in previous_handlers if item.signal_name == "SIGTERM"), None)
    if term is None:
        codes = _codes(*codes, "PREVIOUS_HANDLER_CAPTURE_REQUIRED")
    if codes:
        values = _result_values(codes)
        values.update(rollback_id=rollback_id, rolled_back=False, idempotent=False,
                      current_state=_state(state, "BLOCKED"))
        return ProductionHostSignalRollbackResultV1(**values)
    if _value(state, "handlers_restored"):
        values = _result_values(())
        values.update(rollback_id=rollback_id, rolled_back=True, idempotent=True, current_state=state)
        return ProductionHostSignalRollbackResultV1(**values)
    try:
        adapter.restore_handler("SIGTERM", term.handler_token)
    except Exception:
        values = _result_values(_codes("PARTIAL_REGISTRATION_ROLLBACK_FAILED"))
        values.update(rollback_id=rollback_id, rolled_back=False, idempotent=False,
                      current_state=_state(state, "BLOCKED"))
        return ProductionHostSignalRollbackResultV1(**values)
    rolled = _state(state, "ROLLBACK_COMPLETE", handlers_prepared=False, registration_complete=False,
                    handlers_restored=True)
    values = _result_values(())
    values.update(rollback_id=rollback_id, rolled_back=True, idempotent=False, current_state=rolled)
    return ProductionHostSignalRollbackResultV1(**values)


def restore_production_host_signal_handlers_v1(
    *, policy: ProductionHostSignalBoundaryPolicyV1, adapter: ProductionHostSignalAdapterV1,
    restoration_request: ProductionHostSignalRestorationRequestV1,
    previous_handlers: tuple[ProductionHostSignalPreviousHandlerV1, ...],
    state: ProductionHostSignalRegistrationStateV1,
) -> ProductionHostSignalRestorationResultV1:
    codes = _codes(*_policy_codes(policy), *_adapter_codes(adapter))
    if not _value(restoration_request, "restoration_required"):
        codes = _codes(*codes, "HANDLER_RESTORATION_REQUIRED")
    if _value(restoration_request, "restoration_order", ()) != ("SIGINT", "SIGTERM"):
        codes = _codes(*codes, "HANDLER_RESTORATION_ORDER_INVALID")
    if {item.signal_name for item in previous_handlers} != {"SIGTERM", "SIGINT"}:
        codes = _codes(*codes, "PREVIOUS_HANDLER_CAPTURE_REQUIRED")
    if codes:
        values = _result_values(codes)
        values.update(restoration_id=_value(restoration_request, "restoration_id", ""), restored=False,
                      idempotent=False, current_state=_state(state, "BLOCKED"))
        return ProductionHostSignalRestorationResultV1(**values)
    if _value(state, "handlers_restored"):
        values = _result_values(())
        values.update(restoration_id=restoration_request.restoration_id, restored=True,
                      idempotent=True, current_state=state)
        return ProductionHostSignalRestorationResultV1(**values)
    by_signal = {item.signal_name: item for item in previous_handlers}
    try:
        for signal_name in ("SIGINT", "SIGTERM"):
            adapter.restore_handler(signal_name, by_signal[signal_name].handler_token)
    except Exception:
        values = _result_values(_codes("HANDLER_RESTORATION_FAILED"))
        values.update(restoration_id=restoration_request.restoration_id, restored=False,
                      idempotent=False, current_state=_state(state, "BLOCKED"))
        return ProductionHostSignalRestorationResultV1(**values)
    restored = _state(state, "HANDLER_RESTORATION_COMPLETE", handlers_restored=True)
    values = _result_values(())
    values.update(restoration_id=restoration_request.restoration_id, restored=True,
                  idempotent=False, current_state=restored)
    return ProductionHostSignalRestorationResultV1(**values)


def dispatch_production_host_signal_v1(
    *, policy: ProductionHostSignalBoundaryPolicyV1,
    dispatch_request: ProductionHostSignalDispatchRequestV1,
    state: ProductionHostSignalRegistrationStateV1,
) -> ProductionHostSignalDispatchResultV1:
    codes = list(_policy_codes(policy))
    signal_name = _value(dispatch_request, "signal_classification", "UNKNOWN")
    current = state
    classification = "INVALID_GRACEFUL_SHUTDOWN_TRANSITION"
    if signal_name in ("SIGTERM", "SIGINT") and state.state_code == "PASSIVE_READY":
        current = _state(state, "SHUTDOWN_REQUESTED", shutdown_requested=True)
        classification = "SHUTDOWN_REQUESTED"
    elif signal_name in ("SIGTERM", "SIGINT") and state.state_code in (
        "SHUTDOWN_REQUESTED", "GRACEFUL_SHUTDOWN_COMPLETE",
    ):
        classification = state.state_code
    elif signal_name == "SIGHUP":
        classification = "RELOAD_NOT_AUTHORIZED"
        codes.append("RELOAD_NOT_AUTHORIZED")
    elif signal_name == "UNKNOWN":
        classification = "UNKNOWN_HOST_GLOBAL_SIGNAL"
        codes.append("UNKNOWN_HOST_GLOBAL_SIGNAL")
    else:
        codes.append("INVALID_GRACEFUL_SHUTDOWN_TRANSITION")
    values = _result_values(_codes(*codes))
    values.update(dispatch_id=_value(dispatch_request, "dispatch_id", ""),
                  dispatch_classification=classification, current_state=current)
    return ProductionHostSignalDispatchResultV1(**values)


def request_production_graceful_shutdown_v1(
    *, policy: ProductionHostSignalBoundaryPolicyV1, shutdown_id: str,
    state: ProductionHostSignalRegistrationStateV1, complete_shutdown: bool,
) -> ProductionGracefulShutdownTransitionV1:
    codes = list(_policy_codes(policy))
    current = state
    if state.state_code == "PASSIVE_READY":
        current = _state(state, "SHUTDOWN_REQUESTED", shutdown_requested=True)
    if current.state_code == "SHUTDOWN_REQUESTED" and complete_shutdown:
        current = _state(current, "GRACEFUL_SHUTDOWN_COMPLETE", shutdown_requested=True,
                         graceful_shutdown_complete=True)
    elif current.state_code not in ("SHUTDOWN_REQUESTED", "GRACEFUL_SHUTDOWN_COMPLETE"):
        codes.append("INVALID_GRACEFUL_SHUTDOWN_TRANSITION")
    values = _result_values(_codes(*codes))
    values.update(shutdown_id=shutdown_id, current_state=current,
                  completed=current.state_code == "GRACEFUL_SHUTDOWN_COMPLETE")
    return ProductionGracefulShutdownTransitionV1(**values)


def build_production_host_signal_boundary_audit_evidence_v1(
    *, evidence_id: str, policy: ProductionHostSignalBoundaryPolicyV1,
    adapter: ProductionHostSignalAdapterV1,
    registration_result: ProductionHostSignalRegistrationResultV1,
    installation_result: ProductionHostSignalHandlerResultV1 | None,
    rollback_result: ProductionHostSignalRollbackResultV1 | None,
    dispatch_result: ProductionHostSignalDispatchResultV1 | None,
    shutdown_transition: ProductionGracefulShutdownTransitionV1 | None,
    restoration_result: ProductionHostSignalRestorationResultV1 | None,
) -> ProductionHostSignalBoundaryAuditEvidenceV1:
    del installation_result, rollback_result, dispatch_result, shutdown_transition, restoration_result
    codes = _codes(*_policy_codes(policy), *registration_result.failure_codes)
    values = _result_values(codes)
    values.update(
        evidence_id=evidence_id, policy_id=_value(policy, "policy_id", ""),
        adapter_id=_value(adapter, "adapter_id", ""),
        registration_id=_value(registration_result, "registration_id", ""),
        signal_names=_value(registration_result, "signal_names", ("SIGTERM", "SIGINT")),
        previous_handler_classifications=tuple(
            item.classification for item in _value(registration_result, "previous_handlers", ())
        ),
    )
    return ProductionHostSignalBoundaryAuditEvidenceV1(**values)
