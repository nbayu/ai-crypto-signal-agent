"""Explicit passive CLI metadata and isolated, caller-injected signal adapter."""
from __future__ import annotations

from dataclasses import dataclass


_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "CLI_IMPLEMENTATION_NOT_AUTHORIZED",
    "PASSIVE_TEST_EXECUTION_NOT_AUTHORIZED", "EXPLICIT_ARGV_REQUIRED",
    "IMPLICIT_SYS_ARGV_ACCESS_NOT_AUTHORIZED", "PASSIVE_MODE_REQUIRED", "ACTIVE_MODE_NOT_AUTHORIZED",
    "UNKNOWN_CLI_ARGUMENT", "DUPLICATE_CLI_ARGUMENT", "CLI_ARGUMENT_VALUE_REQUIRED",
    "ACTIVATION_ARGUMENT_NOT_ALLOWED", "CREDENTIAL_ARGUMENT_NOT_ALLOWED",
    "ENVIRONMENT_ARGUMENT_NOT_ALLOWED", "PROVIDER_ARGUMENT_NOT_ALLOWED",
    "NETWORK_ARGUMENT_NOT_ALLOWED", "WORKLOAD_ARGUMENT_NOT_ALLOWED",
    "PUBLICATION_ARGUMENT_NOT_ALLOWED", "TRADING_ARGUMENT_NOT_ALLOWED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "ISOLATED_SIGNAL_ADAPTER_REQUIRED", "HOST_GLOBAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED",
    "SIGNAL_SET_MISMATCH", "UNSUPPORTED_SIGNAL_REGISTRATION", "DUPLICATE_SIGNAL_REGISTRATION",
    "SIGNAL_REGISTRATION_ORDER_INVALID", "PROCESS_TERMINATION_NOT_AUTHORIZED",
    "PROCESS_CONTROL_NOT_AUTHORIZED", "SUBPROCESS_NOT_AUTHORIZED", "THREAD_START_NOT_AUTHORIZED",
    "EVENT_LOOP_START_NOT_AUTHORIZED", "ENVIRONMENT_READ_NOT_AUTHORIZED",
    "FILESYSTEM_READ_NOT_AUTHORIZED", "FILESYSTEM_WRITE_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "SYSTEMD_ACCESS_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED",
    "TELEGRAM_START_NOT_AUTHORIZED", "DATABASE_MUTATION_NOT_AUTHORIZED",
    "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "PUBLICATION_NOT_AUTHORIZED", "INVALID_STATE_TRANSITION", "RELOAD_NOT_AUTHORIZED",
    "UNKNOWN_REAL_SIGNAL", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "PROVIDER_MATERIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
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


class PassiveProductionCliPolicyV1(_Record):
    __slots__ = ()


class PassiveProductionCliInvocationV1(_Record):
    __slots__ = ()


class PassiveProductionCliArgumentResultV1(_Record):
    __slots__ = ()


class PassiveProductionCliExitResultV1(_Record):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class PassiveProductionCliFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


class IsolatedSignalAdapterPolicyV1(_Record):
    __slots__ = ()


class IsolatedSignalAdapterV1(_Record):
    __slots__ = ()


class IsolatedSignalRegistrationRequestV1(_Record):
    __slots__ = ()


class IsolatedSignalRegistrationResultV1(_Record):
    __slots__ = ()


class IsolatedSignalDispatchRequestV1(_Record):
    __slots__ = ()


class IsolatedSignalDispatchResultV1(_Record):
    __slots__ = ()


class PassiveCliSignalRuntimeStateV1(_Record):
    __slots__ = ()


class PassiveCliSignalTransitionV1(_Record):
    __slots__ = ()


class PassiveCliSignalAuditEvidenceV1(_Record):
    __slots__ = ()


def _codes(*codes: str) -> tuple[str, ...]:
    selected = set(codes)
    return tuple(code for code in _ORDER if code in selected)


def _add(codes: list[str], condition: bool, code: str) -> None:
    if condition:
        codes.append(code)


def _flag(record: object, name: str) -> bool:
    return bool(getattr(record, name))


def _authority() -> dict[str, bool]:
    return {
        "production_cli_implementation_authorized": True,
        "real_signal_registration_implementation_authorized": True,
        "production_cli_test_execution_authorized": True,
        "isolated_signal_tests_authorized": True,
        "implicit_sys_argv_access_authorized": False,
        "environment_read_authorized": False,
        "filesystem_read_authorized": False,
        "filesystem_write_authorized": False,
        "credential_access_authorized": False,
        "credential_loading_authorized": False,
        "credential_validation_authorized": False,
        "systemd_access_authorized": False,
        "network_authorized": False,
        "provider_transmission_authorized": False,
        "scanner_execution_authorized": False,
        "worker_start_authorized": False,
        "scheduler_start_authorized": False,
        "telegram_start_authorized": False,
        "database_mutation_authorized": False,
        "artifact_publication_authorized": False,
        "trading_authorized": False,
        "production_runtime_execution_authorized": False,
        "runtime_activation_authorized": False,
        "publication_authorized": False,
        "process_termination_authorized": False,
        "process_control_authorized": False,
        "subprocess_authorized": False,
        "thread_start_authorized": False,
        "event_loop_start_authorized": False,
        "fail_closed": True,
    }


def _closed() -> dict[str, bool]:
    return {
        "activation_gate_open": False,
        "credential_gate_open": False,
        "network_gate_open": False,
        "workload_gate_open": False,
    }


def _failures(codes: tuple[str, ...]) -> tuple[PassiveProductionCliFailureV1, ...]:
    return tuple(PassiveProductionCliFailureV1(code, "fail-closed passive metadata rejection", False) for code in codes)


def _state(
    source: PassiveCliSignalRuntimeStateV1, state_code: str, *, passive_ready: bool,
    registration_complete: bool, shutdown_requested: bool, graceful_shutdown_complete: bool,
) -> PassiveCliSignalRuntimeStateV1:
    return PassiveCliSignalRuntimeStateV1(
        state_id=source.state_id, state_code=state_code,
        configuration_validated=True, passive_ready=passive_ready,
        registration_complete=registration_complete, shutdown_requested=shutdown_requested,
        graceful_shutdown_complete=graceful_shutdown_complete, **_closed(),
    )


def _policy_codes(policy: PassiveProductionCliPolicyV1) -> tuple[str, ...]:
    codes: list[str] = []
    _add(codes, not isinstance(policy.policy_id, str) or not policy.policy_id, "POLICY_ID_EMPTY")
    _add(codes, not isinstance(policy.policy_version, str) or not policy.policy_version, "POLICY_VERSION_EMPTY")
    _add(codes, not _flag(policy, "production_cli_implementation_authorized"), "CLI_IMPLEMENTATION_NOT_AUTHORIZED")
    _add(codes, not _flag(policy, "production_cli_test_execution_authorized"), "PASSIVE_TEST_EXECUTION_NOT_AUTHORIZED")
    _add(codes, _flag(policy, "implicit_sys_argv_access_authorized"), "IMPLICIT_SYS_ARGV_ACCESS_NOT_AUTHORIZED")
    mapping = (
        ("environment_read_authorized", "ENVIRONMENT_READ_NOT_AUTHORIZED"),
        ("filesystem_read_authorized", "FILESYSTEM_READ_NOT_AUTHORIZED"),
        ("filesystem_write_authorized", "FILESYSTEM_WRITE_NOT_AUTHORIZED"),
        ("credential_access_authorized", "CREDENTIAL_ACCESS_NOT_AUTHORIZED"),
        ("credential_loading_authorized", "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ("systemd_access_authorized", "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        ("network_authorized", "NETWORK_NOT_AUTHORIZED"),
        ("provider_transmission_authorized", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        ("process_termination_authorized", "PROCESS_TERMINATION_NOT_AUTHORIZED"),
        ("process_control_authorized", "PROCESS_CONTROL_NOT_AUTHORIZED"),
        ("subprocess_authorized", "SUBPROCESS_NOT_AUTHORIZED"),
        ("thread_start_authorized", "THREAD_START_NOT_AUTHORIZED"),
        ("event_loop_start_authorized", "EVENT_LOOP_START_NOT_AUTHORIZED"),
        ("scanner_execution_authorized", "SCANNER_EXECUTION_NOT_AUTHORIZED"),
        ("worker_start_authorized", "WORKER_START_NOT_AUTHORIZED"),
        ("scheduler_start_authorized", "SCHEDULER_START_NOT_AUTHORIZED"),
        ("telegram_start_authorized", "TELEGRAM_START_NOT_AUTHORIZED"),
        ("database_mutation_authorized", "DATABASE_MUTATION_NOT_AUTHORIZED"),
        ("artifact_publication_authorized", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED"),
        ("trading_authorized", "TRADING_NOT_AUTHORIZED"),
        ("production_runtime_execution_authorized", "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED"),
        ("runtime_activation_authorized", "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ("publication_authorized", "PUBLICATION_NOT_AUTHORIZED"),
    )
    for name, code in mapping:
        _add(codes, _flag(policy, name), code)
    return _codes(*codes)


def _argument_codes(explicit_argv: object) -> tuple[str, ...]:
    codes: list[str] = []
    if not isinstance(explicit_argv, tuple) or not explicit_argv:
        return ("EXPLICIT_ARGV_REQUIRED",)
    if explicit_argv in (("--help",), ("--version",)):
        return ()
    if explicit_argv.count("--mode") > 1:
        codes.append("DUPLICATE_CLI_ARGUMENT")
    if "--mode" in explicit_argv:
        position = explicit_argv.index("--mode")
        if position + 1 >= len(explicit_argv):
            codes.append("CLI_ARGUMENT_VALUE_REQUIRED")
        elif explicit_argv[position + 1] != "passive":
            codes.append("ACTIVE_MODE_NOT_AUTHORIZED")
        elif explicit_argv != ("--mode", "passive"):
            codes.append("UNKNOWN_CLI_ARGUMENT")
    else:
        option_codes = (
            ("--activate", "ACTIVATION_ARGUMENT_NOT_ALLOWED"),
            ("--credential", "CREDENTIAL_ARGUMENT_NOT_ALLOWED"),
            ("--env-file", "ENVIRONMENT_ARGUMENT_NOT_ALLOWED"),
            ("--dotenv", "ENVIRONMENT_ARGUMENT_NOT_ALLOWED"),
            ("--endpoint", "PROVIDER_ARGUMENT_NOT_ALLOWED"),
            ("--proxy", "PROVIDER_ARGUMENT_NOT_ALLOWED"),
            ("--network", "NETWORK_ARGUMENT_NOT_ALLOWED"),
            ("--scanner", "WORKLOAD_ARGUMENT_NOT_ALLOWED"),
            ("--worker", "WORKLOAD_ARGUMENT_NOT_ALLOWED"),
            ("--scheduler", "WORKLOAD_ARGUMENT_NOT_ALLOWED"),
            ("--telegram", "WORKLOAD_ARGUMENT_NOT_ALLOWED"),
            ("--database", "WORKLOAD_ARGUMENT_NOT_ALLOWED"),
            ("--publish", "PUBLICATION_ARGUMENT_NOT_ALLOWED"),
            ("--trade", "TRADING_ARGUMENT_NOT_ALLOWED"),
        )
        for option, code in option_codes:
            if option in explicit_argv:
                codes.append(code)
        if not codes:
            codes.append("UNKNOWN_CLI_ARGUMENT")
    return _codes(*codes)


def parse_explicit_passive_cli_arguments_v1(
    *, policy: PassiveProductionCliPolicyV1, explicit_argv: tuple[str, ...],
) -> PassiveProductionCliArgumentResultV1:
    codes = _codes(*_policy_codes(policy), *_argument_codes(explicit_argv))
    accepted = not codes
    values: dict[str, object] = {
        "policy_id": policy.policy_id, "explicit_argv_classification": "EXPLICIT_CALLER_SUPPLIED",
        "accepted": accepted, "mode": "PASSIVE" if accepted else "BLOCKED",
        "failure_codes": codes, "failures": _failures(codes),
    }
    values.update(_closed())
    values.update(_authority())
    return PassiveProductionCliArgumentResultV1(**values)


def evaluate_passive_production_cli_v1(
    *, policy: PassiveProductionCliPolicyV1, invocation: PassiveProductionCliInvocationV1,
    argument_result: PassiveProductionCliArgumentResultV1,
) -> PassiveProductionCliExitResultV1:
    codes = list(_policy_codes(policy)) + list(argument_result.failure_codes)
    for name, code in (
        ("activation_gate_open", "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
        ("credential_gate_open", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
        ("network_gate_open", "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ("workload_gate_open", "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
    ):
        _add(codes, _flag(invocation, name), code)
    _add(codes, invocation.execution_mode != "PASSIVE_TEST_MODE", "PASSIVE_MODE_REQUIRED")
    ordered = _codes(*codes)
    ready = not ordered
    initial = PassiveCliSignalRuntimeStateV1(
        state_id=invocation.invocation_id, state_code="CONFIGURATION_VALIDATED",
        configuration_validated=True, passive_ready=False, registration_complete=False,
        shutdown_requested=False, graceful_shutdown_complete=False, **_closed(),
    )
    current = _state(initial, "PASSIVE_READY", passive_ready=True, registration_complete=False,
                     shutdown_requested=False, graceful_shutdown_complete=False) if ready else _state(
        initial, "BLOCKED", passive_ready=False, registration_complete=False,
        shutdown_requested=False, graceful_shutdown_complete=False,
    )
    values: dict[str, object] = {
        "policy_id": policy.policy_id, "cli_id": invocation.cli_id, "invocation_id": invocation.invocation_id,
        "ready": ready,
        "result_classification": "PASSIVE_PRODUCTION_CLI_READY_IN_ISOLATED_TEST_MODE" if ready else "NOT_READY",
        "current_state": current, "failure_codes": ordered, "failures": _failures(ordered),
    }
    values.update(_closed())
    values.update(_authority())
    return PassiveProductionCliExitResultV1(**values)


def register_isolated_real_signal_handlers_v1(
    *, policy: PassiveProductionCliPolicyV1, adapter_policy: IsolatedSignalAdapterPolicyV1,
    adapter: IsolatedSignalAdapterV1, registration_request: IsolatedSignalRegistrationRequestV1,
    runtime_state: PassiveCliSignalRuntimeStateV1,
) -> IsolatedSignalRegistrationResultV1:
    codes = list(_policy_codes(policy))
    _add(codes, not _flag(adapter, "isolated") or not _flag(adapter, "adapter_ready"), "ISOLATED_SIGNAL_ADAPTER_REQUIRED")
    _add(codes, _flag(adapter, "host_global") or _flag(adapter_policy, "host_global_registration_authorized"), "HOST_GLOBAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED")
    requested = registration_request.requested_signals
    _add(codes, requested != ("SIGTERM", "SIGINT"), "SIGNAL_SET_MISMATCH")
    _add(codes, "SIGHUP" in requested or any(item not in ("SIGTERM", "SIGINT") for item in requested), "UNSUPPORTED_SIGNAL_REGISTRATION")
    _add(codes, _flag(registration_request, "duplicate_registration_requested") or _flag(runtime_state, "registration_complete"), "DUPLICATE_SIGNAL_REGISTRATION")
    _add(codes, not _flag(registration_request, "configuration_validated") or not _flag(runtime_state, "configuration_validated") or not _flag(registration_request, "passive_readiness_pending") or _flag(runtime_state, "shutdown_requested") or _flag(runtime_state, "graceful_shutdown_complete"), "SIGNAL_REGISTRATION_ORDER_INVALID")
    ordered = _codes(*codes)
    registered = not ordered
    if registered:
        adapter.register_handler("SIGTERM", "REQUEST_SHUTDOWN")
        adapter.register_handler("SIGINT", "REQUEST_SHUTDOWN")
        current = _state(runtime_state, "SIGNAL_HANDLERS_REGISTERED", passive_ready=False,
                         registration_complete=True, shutdown_requested=False, graceful_shutdown_complete=False)
    else:
        current = _state(runtime_state, "BLOCKED", passive_ready=False,
                         registration_complete=False, shutdown_requested=False, graceful_shutdown_complete=False)
    values: dict[str, object] = {
        "registration_id": registration_request.registration_id, "adapter_id": adapter.adapter_id,
        "registered": registered, "registered_signals": ("SIGTERM", "SIGINT") if registered else (),
        "current_state": current, "failure_codes": ordered, "failures": _failures(ordered),
    }
    values.update(_closed())
    values.update(_authority())
    return IsolatedSignalRegistrationResultV1(**values)


def _dispatch_result(
    state: PassiveCliSignalRuntimeStateV1, codes: tuple[str, ...],
) -> IsolatedSignalDispatchResultV1:
    values: dict[str, object] = {
        "current_state": state, "failure_codes": codes, "failures": _failures(codes),
    }
    values.update(_closed())
    values.update(_authority())
    return IsolatedSignalDispatchResultV1(**values)


def dispatch_isolated_real_signal_v1(
    *, policy: PassiveProductionCliPolicyV1, runtime_state: PassiveCliSignalRuntimeStateV1,
    dispatch_request: IsolatedSignalDispatchRequestV1,
) -> IsolatedSignalDispatchResultV1:
    codes = _policy_codes(policy)
    if codes:
        return _dispatch_result(_state(runtime_state, "BLOCKED", passive_ready=False,
                                       registration_complete=False, shutdown_requested=False,
                                       graceful_shutdown_complete=False), codes)
    signal_name = dispatch_request.signal_classification
    if signal_name in ("SIGTERM", "SIGINT"):
        if runtime_state.state_code == "PASSIVE_READY":
            state = _state(runtime_state, "SHUTDOWN_REQUESTED", passive_ready=False,
                           registration_complete=_flag(runtime_state, "registration_complete"),
                           shutdown_requested=True, graceful_shutdown_complete=False)
        elif runtime_state.state_code == "SHUTDOWN_REQUESTED":
            state = runtime_state
        elif runtime_state.state_code == "GRACEFUL_SHUTDOWN_COMPLETE":
            state = runtime_state
        else:
            return _dispatch_result(_state(runtime_state, "BLOCKED", passive_ready=False,
                                           registration_complete=False, shutdown_requested=False,
                                           graceful_shutdown_complete=False), ("INVALID_STATE_TRANSITION",))
        return _dispatch_result(state, ())
    if signal_name == "SIGHUP":
        return _dispatch_result(runtime_state, ("RELOAD_NOT_AUTHORIZED",))
    return _dispatch_result(runtime_state, ("UNKNOWN_REAL_SIGNAL",))


def request_passive_cli_shutdown_v1(
    *, policy: PassiveProductionCliPolicyV1, runtime_state: PassiveCliSignalRuntimeStateV1,
    shutdown_id: str,
) -> IsolatedSignalDispatchResultV1:
    del shutdown_id
    codes = _policy_codes(policy)
    if codes:
        return _dispatch_result(_state(runtime_state, "BLOCKED", passive_ready=False,
                                       registration_complete=False, shutdown_requested=False,
                                       graceful_shutdown_complete=False), codes)
    if runtime_state.state_code == "PASSIVE_READY":
        state = _state(runtime_state, "SHUTDOWN_REQUESTED", passive_ready=False,
                       registration_complete=_flag(runtime_state, "registration_complete"),
                       shutdown_requested=True, graceful_shutdown_complete=False)
    elif runtime_state.state_code == "SHUTDOWN_REQUESTED":
        state = _state(runtime_state, "GRACEFUL_SHUTDOWN_COMPLETE", passive_ready=False,
                       registration_complete=_flag(runtime_state, "registration_complete"),
                       shutdown_requested=True, graceful_shutdown_complete=True)
    elif runtime_state.state_code == "GRACEFUL_SHUTDOWN_COMPLETE":
        state = runtime_state
    else:
        return _dispatch_result(_state(runtime_state, "BLOCKED", passive_ready=False,
                                       registration_complete=False, shutdown_requested=False,
                                       graceful_shutdown_complete=False), ("INVALID_STATE_TRANSITION",))
    return _dispatch_result(state, ())


def build_passive_cli_signal_audit_evidence_v1(
    *, evidence_id: str, policy: PassiveProductionCliPolicyV1,
    invocation: PassiveProductionCliInvocationV1, argument_result: PassiveProductionCliArgumentResultV1,
    cli_result: PassiveProductionCliExitResultV1, runtime_state: PassiveCliSignalRuntimeStateV1,
) -> PassiveCliSignalAuditEvidenceV1:
    values: dict[str, object] = {
        "evidence_id": evidence_id, "policy_id": policy.policy_id, "cli_id": invocation.cli_id,
        "invocation_id": invocation.invocation_id,
        "explicit_argv_classification": argument_result.explicit_argv_classification,
        "runtime_state": runtime_state.state_code, "failure_codes": cli_result.failure_codes,
    }
    values.update(_closed())
    values.update(_authority())
    return PassiveCliSignalAuditEvidenceV1(**values)


def main(
    *, policy: PassiveProductionCliPolicyV1, explicit_argv: tuple[str, ...],
    invocation: PassiveProductionCliInvocationV1, adapter_policy: IsolatedSignalAdapterPolicyV1,
    adapter: IsolatedSignalAdapterV1, registration_request: IsolatedSignalRegistrationRequestV1,
) -> PassiveProductionCliExitResultV1:
    del adapter_policy, adapter, registration_request
    parsed = parse_explicit_passive_cli_arguments_v1(policy=policy, explicit_argv=explicit_argv)
    return evaluate_passive_production_cli_v1(policy=policy, invocation=invocation, argument_result=parsed)
