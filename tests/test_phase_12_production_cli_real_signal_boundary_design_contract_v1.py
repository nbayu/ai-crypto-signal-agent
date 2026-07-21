"""RED contract for a metadata-only production CLI and real-signal boundary."""
from __future__ import annotations

from dataclasses import is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from engine.phase_12_production_cli_real_signal_boundary_design_contract_v1 import (
    ProductionCliActivationBoundaryV1,
    ProductionCliArgumentContractV1,
    ProductionCliCredentialBoundaryV1,
    ProductionCliEnvironmentBoundaryV1,
    ProductionCliExitClassificationV1,
    ProductionCliIdentityV1,
    ProductionCliInvocationModeV1,
    ProductionCliRealSignalAuditEvidenceV1,
    ProductionCliRealSignalBoundaryPolicyV1,
    ProductionCliRealSignalDecisionV1,
    ProductionCliRealSignalFailureV1,
    ProductionCliRealSignalIndependentReviewerApprovalV1,
    ProductionCliRealSignalOperatorAttestationV1,
    ProductionCliRealSignalReadinessChecklistV1,
    RealSignalBoundaryIdentityV1,
    RealSignalRegistrationPolicyV1,
    RealSignalShutdownPolicyV1,
    RealSignalTransitionPolicyV1,
    build_production_cli_real_signal_boundary_design_audit_evidence_v1,
    evaluate_production_cli_real_signal_boundary_design_v1,
)


_NOW = datetime(2030, 1, 10, 12, 0, tzinfo=UTC)
_MODULE = "engine.phase_12_passive_runtime_launcher_executable_contract_v1"
_PYTHON = "/opt/ai-crypto-signal-agent/.venv/bin/python"
_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PRODUCTION_CLI_DESIGN_NOT_AUTHORIZED",
    "REAL_SIGNAL_DESIGN_NOT_AUTHORIZED", "CLI_IDENTITY_MISMATCH", "PYTHON_INTERPRETER_MISMATCH",
    "LAUNCHER_MODULE_MISMATCH", "ARGV_CONTRACT_REQUIRED", "PASSIVE_ARGV_CONTRACT_MISMATCH",
    "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED", "SHELL_PARSING_NOT_AUTHORIZED",
    "ENVIRONMENT_ARGUMENT_NOT_ALLOWED", "CREDENTIAL_ARGUMENT_NOT_ALLOWED",
    "PROVIDER_ENDPOINT_ARGUMENT_NOT_ALLOWED", "AUTHORIZATION_ARGUMENT_NOT_ALLOWED",
    "PROXY_ARGUMENT_NOT_ALLOWED", "ACTIVATION_ARGUMENT_NOT_ALLOWED", "NETWORK_ARGUMENT_NOT_ALLOWED",
    "WORKLOAD_ARGUMENT_NOT_ALLOWED", "PUBLICATION_ARGUMENT_NOT_ALLOWED", "TRADING_ARGUMENT_NOT_ALLOWED",
    "PASSIVE_MODE_REQUIRED", "ACTIVE_MODE_NOT_AUTHORIZED", "ACTIVATION_GATE_MUST_REMAIN_CLOSED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "NETWORK_GATE_MUST_REMAIN_CLOSED",
    "WORKLOAD_GATE_MUST_REMAIN_CLOSED", "ENVIRONMENT_READ_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PRODUCTION_CLI_IMPLEMENTATION_NOT_AUTHORIZED", "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED",
    "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED", "REAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED",
    "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED", "PROCESS_CONTROL_NOT_AUTHORIZED", "SIGNAL_SET_MISMATCH",
    "SIGNAL_HANDLER_IO_NOT_AUTHORIZED", "SIGNAL_HANDLER_LIVE_ACTION_NOT_AUTHORIZED",
    "INVALID_SIGNAL_TRANSITION", "RELOAD_NOT_AUTHORIZED", "UNKNOWN_REAL_SIGNAL",
    "GRACEFUL_SHUTDOWN_REQUIRED", "SHUTDOWN_TIMEOUT_REQUIRED", "OPERATOR_ATTESTATION_REQUIRED",
    "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE",
    "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED",
    "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED", "DAEMON_RELOAD_NOT_AUTHORIZED",
    "SERVICE_ENABLEMENT_NOT_AUTHORIZED", "SERVICE_START_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_MATERIAL_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> ProductionCliRealSignalBoundaryPolicyV1:
    values = dict(
        policy_id="cli-signal-policy-v1", policy_version="V1",
        production_cli_boundary_design_authorized=True,
        real_signal_handling_boundary_design_authorized=True, argv_contract_design_authorized=True,
        passive_default_required=True, production_cli_implementation_authorized=False,
        real_signal_registration_implementation_authorized=False,
        production_cli_execution_authorized=False, production_runtime_execution_authorized=False,
        argv_access_authorized=False, environment_read_authorized=False,
        filesystem_read_authorized=False, filesystem_write_authorized=False,
        systemd_access_authorized=False, process_control_authorized=False,
        subprocess_authorized=False, thread_start_authorized=False, event_loop_start_authorized=False,
        credential_value_access_authorized=False, credential_loading_authorized=False,
        credential_validation_authorized=False, provider_transmission_authorized=False,
        scanner_execution_authorized=False, worker_start_authorized=False,
        scheduler_start_authorized=False, telegram_start_authorized=False,
        database_mutation_authorized=False, artifact_publication_authorized=False,
        trading_authorized=False, systemd_unit_file_generation_authorized=False,
        systemd_drop_in_generation_authorized=False, service_unit_installation_authorized=False,
        daemon_reload_authorized=False, service_enablement_authorized=False,
        service_start_restart_authorized=False, runtime_activation_authorized=False,
        publication_authorized=False, evidence_max_age_seconds=3600, fail_closed=True,
    )
    return ProductionCliRealSignalBoundaryPolicyV1(**(values | overrides))


def _cli(**overrides: object) -> ProductionCliIdentityV1:
    values = dict(
        cli_id="production-cli-v1", cli_version="V1", launcher_module=_MODULE,
        interpreter_path=_PYTHON, service_unit="ai-crypto-signal-agent.service",
        service_user="ai-crypto-signal-agent", service_group="ai-crypto-signal-agent",
        working_directory="/opt/ai-crypto-signal-agent", invocation_kind="PYTHON_MODULE_CLI",
        passive_default=True, production_cli_design_authorized=True,
        production_cli_implementation_authorized=False, production_cli_execution_authorized=False,
        production_runtime_execution_authorized=False,
    )
    return ProductionCliIdentityV1(**(values | overrides))


def _argv(**overrides: object) -> ProductionCliArgumentContractV1:
    values = dict(
        argument_contract_id="passive-argv-v1", canonical_arguments=("--mode", "passive"),
        permitted_argument_tuples=(("--mode", "passive"), ("--help",), ("--version",)),
        argv_contract_defined=True, argv_access_authorized=False, implicit_argv_read_allowed=False,
        shell_parsing_allowed=False, activation_argument_allowed=False,
        credential_argument_allowed=False, network_argument_allowed=False,
        workload_argument_allowed=False, publication_argument_allowed=False,
        trading_argument_allowed=False, environment_argument_allowed=False,
        provider_endpoint_argument_allowed=False, authorization_argument_allowed=False,
        proxy_argument_allowed=False,
    )
    return ProductionCliArgumentContractV1(**(values | overrides))


def _mode(**overrides: object) -> ProductionCliInvocationModeV1:
    values = dict(
        invocation_id="passive-invocation-v1", requested_mode="PASSIVE", default_mode="PASSIVE",
        passive_mode_supported=True, active_mode_supported=False, passive_mode_required=True,
        activation_gate_open=False, credential_gate_open=False, network_gate_open=False,
        workload_gate_open=False, mode_ready=True,
    )
    return ProductionCliInvocationModeV1(**(values | overrides))


def _exits(**overrides: object) -> ProductionCliExitClassificationV1:
    values = dict(
        exit_classification_id="cli-exits-v1", passive_ready_exit=20,
        passive_shutdown_complete_exit=21, cli_usage_error_exit=22,
        cli_configuration_blocked_exit=23, signal_shutdown_requested_exit=24,
        signal_shutdown_complete_exit=25,
        real_signal_registration_not_implemented_exit=26,
        production_execution_not_authorized_exit=27, exit_classifications_ready=True,
    )
    return ProductionCliExitClassificationV1(**(values | overrides))


def _environment(**overrides: object) -> ProductionCliEnvironmentBoundaryV1:
    values = dict(
        environment_boundary_id="cli-environment-v1", environment_read_authorized=False,
        environment_file_allowed=False, dotenv_allowed=False, secret_environment_allowed=False,
        environment_dump_allowed=False, implicit_locale_read_allowed=False,
        implicit_terminal_read_allowed=False, environment_boundary_ready=True,
    )
    return ProductionCliEnvironmentBoundaryV1(**(values | overrides))


def _credential(**overrides: object) -> ProductionCliCredentialBoundaryV1:
    values = dict(
        credential_boundary_id="cli-credential-v1", secret_store_selection="SYSTEMD_CREDENTIALS",
        placement_method="SYSTEMD_ENCRYPTED_CREDENTIAL",
        credential_names=("deepseek_api_key", "anthropic_api_key"),
        owner_secret_entry_authorized=True, owner_secret_entry_executed=False,
        credential_presence_claimed=False, credential_access_authorized=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        credential_argument_allowed=False, credential_gate_open=False,
        credential_exposure_detected=False,
    )
    return ProductionCliCredentialBoundaryV1(**(values | overrides))


def _activation(**overrides: object) -> ProductionCliActivationBoundaryV1:
    values = dict(
        activation_boundary_id="cli-activation-v1", activation_requested=False,
        activation_authorized=False, activation_argument_allowed=False, activation_token_present=False,
        network_authorized=False, provider_transmission_authorized=False,
        scanner_execution_authorized=False, worker_start_authorized=False,
        scheduler_start_authorized=False, telegram_start_authorized=False,
        database_mutation_authorized=False, artifact_publication_authorized=False,
        trading_authorized=False, runtime_activation_authorized=False, publication_authorized=False,
        activation_gate_open=False, network_gate_open=False, workload_gate_open=False,
    )
    return ProductionCliActivationBoundaryV1(**(values | overrides))


def _signal_identity(**overrides: object) -> RealSignalBoundaryIdentityV1:
    values = dict(
        signal_boundary_id="real-signal-v1", supported_signal_names=("SIGTERM", "SIGINT"),
        unsupported_signal_names=("SIGHUP", "SIGQUIT", "SIGUSR1", "SIGUSR2", "UNKNOWN"),
        process_role="FUTURE_PRODUCTION_CLI", registration_scope="MAIN_THREAD_ONLY",
        registration_implementation_authorized=False, real_signal_registration_authorized=False,
        process_control_authorized=False, signal_boundary_design_ready=True,
    )
    return RealSignalBoundaryIdentityV1(**(values | overrides))


def _registration(**overrides: object) -> RealSignalRegistrationPolicyV1:
    values = dict(
        registration_policy_id="signal-registration-v1",
        registration_after_configuration_validation=True, registration_before_passive_readiness=True,
        handlers_minimal=True, handlers_only_request_shutdown=True,
        handlers_blocking_io_allowed=False, handlers_credential_loading_allowed=False,
        handlers_provider_access_allowed=False, handlers_network_activation_allowed=False,
        handlers_workload_start_allowed=False, handlers_publication_allowed=False,
        handlers_database_mutation_allowed=False, duplicate_registration_prohibited=True,
        handler_restoration_policy_defined=True, main_thread_only_required=True,
        registration_implementation_authorized=False, real_signal_registration_authorized=False,
        registration_policy_ready=True,
    )
    return RealSignalRegistrationPolicyV1(**(values | overrides))


def _transitions(**overrides: object) -> RealSignalTransitionPolicyV1:
    values = dict(
        transition_policy_id="signal-transitions-v1", sigterm_transition=("PASSIVE_READY", "SHUTDOWN_REQUESTED"),
        sigint_transition=("PASSIVE_READY", "SHUTDOWN_REQUESTED"),
        repeated_shutdown_transition=("SHUTDOWN_REQUESTED", "SHUTDOWN_REQUESTED"),
        completed_shutdown_transition=("GRACEFUL_SHUTDOWN_COMPLETE", "GRACEFUL_SHUTDOWN_COMPLETE"),
        sighup_classification="RELOAD_NOT_AUTHORIZED", unknown_signal_classification="UNKNOWN_REAL_SIGNAL",
        transitions_idempotent=True, transitions_keep_gates_closed=True,
        transitions_keep_live_authorities_false=True, transition_policy_ready=True,
    )
    return RealSignalTransitionPolicyV1(**(values | overrides))


def _shutdown(**overrides: object) -> RealSignalShutdownPolicyV1:
    values = dict(
        shutdown_policy_id="real-signal-shutdown-v1", graceful_shutdown_required=True,
        shutdown_timeout_seconds=30, deterministic_shutdown_order=True,
        repeated_shutdown_idempotent=True, passive_resource_set_empty=True,
        future_worker_stop_classification="FUTURE", future_scheduler_stop_classification="FUTURE",
        future_provider_session_close_classification="FUTURE",
        future_telegram_stop_classification="FUTURE", pending_database_mutation_prohibited=True,
        pending_publication_prohibited=True, exit_classification_defined=True,
        forced_kill_fallback_classification="FUTURE", shutdown_policy_ready=True,
    )
    return RealSignalShutdownPolicyV1(**(values | overrides))


def _checklist(**overrides: object) -> ProductionCliRealSignalReadinessChecklistV1:
    values = dict(
        checklist_id="cli-signal-checklist-v1", canonical_cli_identity_confirmed=True,
        interpreter_and_module_confirmed=True, canonical_passive_argv_contract_defined=True,
        implicit_argv_access_prohibited=True, shell_parsing_prohibited=True,
        environment_reads_prohibited=True, credential_arguments_prohibited=True,
        activation_arguments_prohibited=True, passive_mode_required=True,
        active_mode_unsupported=True, all_gates_closed=True,
        deterministic_exit_classifications_defined=True, sigterm_design_defined=True,
        sigint_design_defined=True, sighup_rejection_defined=True, unknown_signal_behavior_defined=True,
        idempotent_shutdown_defined=True, handler_minimality_defined=True,
        no_io_in_handler_defined=True, implementation_unauthorized=True,
        cli_execution_unauthorized=True, signal_registration_unauthorized=True,
        systemd_generation_install_start_unauthorized=True,
        credential_loading_unauthorized=True, network_runtime_publication_unauthorized=True,
        operator_attestation_complete=True, reviewer_approval_complete=True,
        evidence_fresh=True, checklist_complete=True,
    )
    return ProductionCliRealSignalReadinessChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> ProductionCliRealSignalOperatorAttestationV1:
    values = dict(
        attestation_id="cli-signal-operator-v1", operator_identity="operator-v1", operator_role="OPERATOR",
        policy_id="cli-signal-policy-v1", cli_id="production-cli-v1", signal_boundary_id="real-signal-v1",
        checklist_id="cli-signal-checklist-v1", passive_only_confirmed=True,
        argv_access_unauthorized_confirmed=True, signal_registration_unauthorized_confirmed=True,
        all_gates_closed_confirmed=True, live_authorities_false_confirmed=True,
        sensitive_evidence_retained=False, attested_at=_NOW - timedelta(minutes=5),
        expires_at=_NOW + timedelta(minutes=5), attestation_complete=True,
    )
    return ProductionCliRealSignalOperatorAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> ProductionCliRealSignalIndependentReviewerApprovalV1:
    values = dict(
        approval_id="cli-signal-reviewer-v1", reviewer_identity="reviewer-v1",
        reviewer_role="INDEPENDENT_REVIEWER", policy_id="cli-signal-policy-v1",
        cli_id="production-cli-v1", signal_boundary_id="real-signal-v1",
        checklist_id="cli-signal-checklist-v1", attestation_id="cli-signal-operator-v1",
        passive_only_confirmed=True, argv_access_unauthorized_confirmed=True,
        signal_registration_unauthorized_confirmed=True, all_gates_closed_confirmed=True,
        live_authorities_false_confirmed=True, sensitive_evidence_retained=False,
        approved=True, reviewed_at=_NOW - timedelta(minutes=4), expires_at=_NOW + timedelta(minutes=5),
        review_complete=True,
    )
    return ProductionCliRealSignalIndependentReviewerApprovalV1(**(values | overrides))


def _evaluate(**overrides: object) -> ProductionCliRealSignalDecisionV1:
    values = dict(
        policy=_policy(), cli_identity=_cli(), argument_contract=_argv(), invocation_mode=_mode(),
        exit_classification=_exits(), environment_boundary=_environment(), credential_boundary=_credential(),
        activation_boundary=_activation(), signal_identity=_signal_identity(),
        registration_policy=_registration(), transition_policy=_transitions(), shutdown_policy=_shutdown(),
        checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(),
        evaluation_time=_NOW,
    )
    return evaluate_production_cli_real_signal_boundary_design_v1(**(values | overrides))


def _assert_authority(record: object) -> None:
    assert record.production_cli_boundary_design_authorized is True
    assert record.real_signal_handling_boundary_design_authorized is True
    assert record.argv_contract_design_authorized is True
    for name in (
        "production_cli_implementation_authorized", "real_signal_registration_implementation_authorized",
        "production_cli_execution_authorized", "production_runtime_execution_authorized",
        "argv_access_authorized", "environment_read_authorized", "filesystem_read_authorized",
        "filesystem_write_authorized", "systemd_access_authorized", "process_control_authorized",
        "subprocess_authorized", "thread_start_authorized", "event_loop_start_authorized",
        "credential_value_access_authorized", "credential_loading_authorized",
        "credential_validation_authorized", "provider_transmission_authorized",
        "scanner_execution_authorized", "worker_start_authorized", "scheduler_start_authorized",
        "telegram_start_authorized", "database_mutation_authorized",
        "artifact_publication_authorized", "trading_authorized",
        "systemd_unit_file_generation_authorized", "systemd_drop_in_generation_authorized",
        "service_unit_installation_authorized", "daemon_reload_authorized",
        "service_enablement_authorized", "service_start_restart_authorized",
        "runtime_activation_authorized", "publication_authorized",
    ):
        assert getattr(record, name) is False
    assert record.fail_closed is True


def test_public_records_are_frozen_slotted_and_metadata_only() -> None:
    records = (
        _policy(), _cli(), _argv(), _mode(), _exits(), _environment(), _credential(), _activation(),
        _signal_identity(), _registration(), _transitions(), _shutdown(), _checklist(), _operator(), _reviewer(),
    )
    for record in records:
        _frozen(record)
    for record_type in (
        ProductionCliRealSignalFailureV1, ProductionCliRealSignalDecisionV1,
        ProductionCliRealSignalAuditEvidenceV1,
    ):
        assert hasattr(record_type, "__dataclass_fields__")


def test_aligned_design_is_ready_only_for_a_separate_implementation_decision() -> None:
    decision = _evaluate()
    _frozen(decision)
    assert decision.ready is True
    assert decision.decision_classification == (
        "PRODUCTION_CLI_AND_REAL_SIGNAL_BOUNDARY_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION"
    )
    assert decision.production_cli_execution_ready is False
    assert decision.real_signal_registration_ready is False
    assert decision.failure_codes == ()
    assert decision.states == (
        "PRODUCTION_CLI_DESIGN_AUTHORIZED", "PRODUCTION_CLI_IMPLEMENTATION_NOT_AUTHORIZED",
        "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED", "ARGV_CONTRACT_DEFINED",
        "ARGV_ACCESS_NOT_AUTHORIZED", "PASSIVE_MODE_REQUIRED", "REAL_SIGNAL_DESIGN_AUTHORIZED",
        "REAL_SIGNAL_REGISTRATION_NOT_IMPLEMENTED", "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED",
        "PRODUCTION_RUNTIME_NOT_AUTHORIZED", "ACTIVATION_GATE_CLOSED", "CREDENTIAL_GATE_CLOSED",
        "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED", "DEPLOYMENT_BLOCKED",
    )
    _assert_authority(decision)


@pytest.mark.parametrize(
    ("overrides", "failure_code"),
    (
        ({"policy": _policy(policy_id="")}, "POLICY_ID_EMPTY"),
        ({"policy": _policy(policy_version="")}, "POLICY_VERSION_EMPTY"),
        ({"policy": _policy(production_cli_boundary_design_authorized=False)}, "PRODUCTION_CLI_DESIGN_NOT_AUTHORIZED"),
        ({"policy": _policy(real_signal_handling_boundary_design_authorized=False)}, "REAL_SIGNAL_DESIGN_NOT_AUTHORIZED"),
        ({"cli_identity": _cli(service_unit="other.service")}, "CLI_IDENTITY_MISMATCH"),
        ({"cli_identity": _cli(interpreter_path="python")}, "PYTHON_INTERPRETER_MISMATCH"),
        ({"cli_identity": _cli(launcher_module="other.module")}, "LAUNCHER_MODULE_MISMATCH"),
        ({"argument_contract": _argv(argv_contract_defined=False)}, "ARGV_CONTRACT_REQUIRED"),
        ({"argument_contract": _argv(canonical_arguments=("--help",))}, "PASSIVE_ARGV_CONTRACT_MISMATCH"),
        ({"argument_contract": _argv(implicit_argv_read_allowed=True)}, "IMPLICIT_ARGV_ACCESS_NOT_AUTHORIZED"),
        ({"argument_contract": _argv(shell_parsing_allowed=True)}, "SHELL_PARSING_NOT_AUTHORIZED"),
        ({"argument_contract": _argv(credential_argument_allowed=True)}, "CREDENTIAL_ARGUMENT_NOT_ALLOWED"),
        ({"argument_contract": _argv(provider_endpoint_argument_allowed=True)}, "PROVIDER_ENDPOINT_ARGUMENT_NOT_ALLOWED"),
        ({"argument_contract": _argv(activation_argument_allowed=True)}, "ACTIVATION_ARGUMENT_NOT_ALLOWED"),
        ({"argument_contract": _argv(network_argument_allowed=True)}, "NETWORK_ARGUMENT_NOT_ALLOWED"),
        ({"argument_contract": _argv(workload_argument_allowed=True)}, "WORKLOAD_ARGUMENT_NOT_ALLOWED"),
        ({"argument_contract": _argv(publication_argument_allowed=True)}, "PUBLICATION_ARGUMENT_NOT_ALLOWED"),
        ({"argument_contract": _argv(trading_argument_allowed=True)}, "TRADING_ARGUMENT_NOT_ALLOWED"),
        ({"invocation_mode": _mode(passive_mode_required=False)}, "PASSIVE_MODE_REQUIRED"),
        ({"invocation_mode": _mode(active_mode_supported=True)}, "ACTIVE_MODE_NOT_AUTHORIZED"),
        ({"invocation_mode": _mode(activation_gate_open=True)}, "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
        ({"invocation_mode": _mode(credential_gate_open=True)}, "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
        ({"invocation_mode": _mode(network_gate_open=True)}, "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ({"invocation_mode": _mode(workload_gate_open=True)}, "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
        ({"environment_boundary": _environment(environment_read_authorized=True)}, "ENVIRONMENT_READ_NOT_AUTHORIZED"),
        ({"credential_boundary": _credential(credential_access_authorized=True)}, "CREDENTIAL_ACCESS_NOT_AUTHORIZED"),
        ({"credential_boundary": _credential(credential_loading_authorized=True)}, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ({"cli_identity": _cli(production_cli_implementation_authorized=True)}, "PRODUCTION_CLI_IMPLEMENTATION_NOT_AUTHORIZED"),
        ({"cli_identity": _cli(production_cli_execution_authorized=True)}, "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED"),
        ({"cli_identity": _cli(production_runtime_execution_authorized=True)}, "PRODUCTION_RUNTIME_EXECUTION_NOT_AUTHORIZED"),
        ({"signal_identity": _signal_identity(registration_implementation_authorized=True)}, "REAL_SIGNAL_IMPLEMENTATION_NOT_AUTHORIZED"),
        ({"signal_identity": _signal_identity(real_signal_registration_authorized=True)}, "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED"),
        ({"signal_identity": _signal_identity(process_control_authorized=True)}, "PROCESS_CONTROL_NOT_AUTHORIZED"),
        ({"signal_identity": _signal_identity(supported_signal_names=("SIGTERM",))}, "SIGNAL_SET_MISMATCH"),
        ({"registration_policy": _registration(handlers_blocking_io_allowed=True)}, "SIGNAL_HANDLER_IO_NOT_AUTHORIZED"),
        ({"registration_policy": _registration(handlers_network_activation_allowed=True)}, "SIGNAL_HANDLER_LIVE_ACTION_NOT_AUTHORIZED"),
        ({"transition_policy": _transitions(transitions_idempotent=False)}, "INVALID_SIGNAL_TRANSITION"),
        ({"transition_policy": _transitions(sighup_classification="RELOAD")}, "RELOAD_NOT_AUTHORIZED"),
        ({"transition_policy": _transitions(unknown_signal_classification="IGNORE")}, "UNKNOWN_REAL_SIGNAL"),
        ({"shutdown_policy": _shutdown(graceful_shutdown_required=False)}, "GRACEFUL_SHUTDOWN_REQUIRED"),
        ({"shutdown_policy": _shutdown(shutdown_timeout_seconds=0)}, "SHUTDOWN_TIMEOUT_REQUIRED"),
        ({"operator_attestation": None}, "OPERATOR_ATTESTATION_REQUIRED"),
        ({"reviewer_approval": None}, "REVIEWER_APPROVAL_REQUIRED"),
        ({"reviewer_approval": _reviewer(reviewer_identity="operator-v1")}, "OPERATOR_REVIEWER_COLLISION"),
        ({"operator_attestation": _operator(attested_at=_NOW + timedelta(seconds=1))}, "EVIDENCE_FROM_FUTURE"),
        ({"operator_attestation": _operator(attested_at=_NOW - timedelta(hours=2))}, "EVIDENCE_STALE"),
        ({"reviewer_approval": _reviewer(expires_at=_NOW - timedelta(seconds=1))}, "EVIDENCE_EXPIRED"),
        ({"policy": _policy(systemd_unit_file_generation_authorized=True)}, "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED"),
        ({"policy": _policy(service_unit_installation_authorized=True)}, "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED"),
        ({"policy": _policy(daemon_reload_authorized=True)}, "DAEMON_RELOAD_NOT_AUTHORIZED"),
        ({"policy": _policy(service_enablement_authorized=True)}, "SERVICE_ENABLEMENT_NOT_AUTHORIZED"),
        ({"policy": _policy(service_start_restart_authorized=True)}, "SERVICE_START_NOT_AUTHORIZED"),
        ({"activation_boundary": _activation(network_authorized=True)}, "NETWORK_NOT_AUTHORIZED"),
        ({"activation_boundary": _activation(runtime_activation_authorized=True)}, "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ({"activation_boundary": _activation(publication_authorized=True)}, "PUBLICATION_NOT_AUTHORIZED"),
        ({"credential_boundary": _credential(credential_exposure_detected=True)}, "RAW_CREDENTIAL_EXPOSURE_DETECTED"),
        ({"argument_contract": _argv(provider_endpoint_argument_allowed=True)}, "PROVIDER_MATERIAL_EXPOSURE_DETECTED"),
        ({"checklist": _checklist(checklist_complete=False)}, "RAW_EXCEPTION_EXPOSURE_DETECTED"),
    ),
)
def test_invalid_design_metadata_fails_closed_in_canonical_order(
    overrides: dict[str, object], failure_code: str,
) -> None:
    decision = _evaluate(**overrides)
    _frozen(decision)
    assert decision.ready is False
    assert decision.decision_classification == "NOT_READY"
    assert failure_code in decision.failure_codes
    assert tuple(item.failure_code for item in decision.failures) == decision.failure_codes
    assert tuple(sorted(decision.failure_codes, key=_FAILURES.index)) == decision.failure_codes
    _assert_authority(decision)


def test_passive_argv_and_real_signal_design_remain_non_executable() -> None:
    argv = _argv()
    transitions = _transitions()
    assert argv.canonical_arguments == ("--mode", "passive")
    assert argv.argv_access_authorized is False
    assert argv.implicit_argv_read_allowed is False
    assert argv.shell_parsing_allowed is False
    assert transitions.sigterm_transition == ("PASSIVE_READY", "SHUTDOWN_REQUESTED")
    assert transitions.sigint_transition == ("PASSIVE_READY", "SHUTDOWN_REQUESTED")
    assert transitions.sighup_classification == "RELOAD_NOT_AUTHORIZED"
    assert transitions.unknown_signal_classification == "UNKNOWN_REAL_SIGNAL"
    assert transitions.transitions_idempotent is True
    assert transitions.transitions_keep_gates_closed is True


def test_audit_is_immutable_redacted_and_preserves_design_only_status() -> None:
    decision = _evaluate()
    evidence = build_production_cli_real_signal_boundary_design_audit_evidence_v1(
        audit_id="cli-signal-audit-v1", policy=_policy(), cli_identity=_cli(),
        argument_contract=_argv(), invocation_mode=_mode(), exit_classification=_exits(),
        environment_boundary=_environment(), credential_boundary=_credential(),
        activation_boundary=_activation(), signal_identity=_signal_identity(),
        registration_policy=_registration(), transition_policy=_transitions(), shutdown_policy=_shutdown(),
        checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(),
        decision=decision, evaluation_time=_NOW,
    )
    _frozen(evidence)
    assert evidence.ready_for_separate_implementation_decision is True
    assert evidence.production_cli_execution_ready is False
    assert evidence.real_signal_registration_ready is False
    assert evidence.failure_codes == ()
    _assert_authority(evidence)
