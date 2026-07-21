"""RED contract for canonical systemd ExecStart passive-launcher metadata only."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from engine.phase_12_canonical_systemd_execstart_passive_launcher_binding_contract_v1 import (
    CanonicalSystemdExecStartAuditEvidenceV1,
    CanonicalSystemdExecStartCommandV1,
    CanonicalSystemdExecStartCredentialBoundaryV1,
    CanonicalSystemdExecStartDecisionV1,
    CanonicalSystemdExecStartDirectoryBindingV1,
    CanonicalSystemdExecStartEnvironmentBoundaryV1,
    CanonicalSystemdExecStartFailureV1,
    CanonicalSystemdExecStartIdentityV1,
    CanonicalSystemdExecStartIndependentReviewerApprovalV1,
    CanonicalSystemdExecStartLifecycleBindingV1,
    CanonicalSystemdExecStartOperatorAttestationV1,
    CanonicalSystemdExecStartPassiveModeV1,
    CanonicalSystemdExecStartReadinessChecklistV1,
    CanonicalSystemdExecStartBindingPolicyV1,
    build_canonical_systemd_execstart_passive_launcher_binding_audit_evidence_v1,
    evaluate_canonical_systemd_execstart_passive_launcher_binding_v1,
)


_NOW = datetime(2030, 1, 10, 12, 0, tzinfo=UTC)
_MODULE = "engine.phase_12_passive_runtime_launcher_executable_contract_v1"
_PYTHON = "/opt/ai-crypto-signal-agent/.venv/bin/python"
_INSTALLATION = "/opt/ai-crypto-signal-agent"
_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "SERVICE_UNIT_MISMATCH",
    "SERVICE_MANAGER_SCOPE_MISMATCH", "DEPLOYMENT_STATE_MISMATCH",
    "SERVICE_USER_MISMATCH", "SERVICE_GROUP_MISMATCH", "INSTALLATION_PATH_MISMATCH",
    "WORKING_DIRECTORY_MISMATCH", "PYTHON_INTERPRETER_MISMATCH", "LAUNCHER_MODULE_MISMATCH",
    "MANUAL_ENTRYPOINT_NOT_ALLOWED", "PYTHON_MODULE_COMMAND_REQUIRED", "SHELL_WRAPPER_NOT_ALLOWED",
    "EXECSTART_ARGUMENT_MISMATCH", "ENVIRONMENT_FILE_NOT_ALLOWED", "DOTENV_NOT_ALLOWED",
    "ENVIRONMENT_READ_NOT_AUTHORIZED", "CREDENTIAL_ARGUMENT_NOT_ALLOWED",
    "PROVIDER_ENDPOINT_ARGUMENT_NOT_ALLOWED", "AUTHORIZATION_ARGUMENT_NOT_ALLOWED",
    "PROXY_ARGUMENT_NOT_ALLOWED", "PASSIVE_DEFAULT_REQUIRED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED", "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED",
    "PRODUCTION_SIGNAL_HANDLING_NOT_READY", "CREDENTIAL_PRESENCE_NOT_ESTABLISHED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "CREDENTIAL_VALIDATION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "WORKLOAD_NOT_AUTHORIZED", "DIRECTORY_BINDING_MISMATCH",
    "FILESYSTEM_WRITE_NOT_AUTHORIZED", "OPERATOR_ATTESTATION_REQUIRED",
    "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE",
    "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED",
    "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED", "DAEMON_RELOAD_NOT_AUTHORIZED",
    "SERVICE_ENABLEMENT_NOT_AUTHORIZED", "SERVICE_START_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_MATERIAL_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> CanonicalSystemdExecStartBindingPolicyV1:
    values = dict(
        policy_id="execstart-binding-policy-v1", policy_version="V1",
        service_unit_design_authorized=True, passive_launcher_implementation_authorized=True,
        passive_test_execution_authorized=True, owner_secret_entry_authorized=True,
        production_cli_binding_implementation_authorized=False,
        systemd_unit_file_generation_authorized=False, systemd_drop_in_generation_authorized=False,
        service_user_group_creation_authorized=False, installation_directory_creation_authorized=False,
        virtualenv_installation_authorized=False, service_unit_installation_authorized=False,
        daemon_reload_authorized=False, service_enablement_authorized=False,
        service_start_restart_authorized=False, credential_value_access_authorized=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        network_authorized=False, provider_transmission_authorized=False,
        scanner_execution_authorized=False, worker_start_authorized=False,
        scheduler_start_authorized=False, telegram_start_authorized=False,
        database_mutation_authorized=False, artifact_publication_authorized=False,
        trading_authorized=False, production_runtime_execution_authorized=False,
        runtime_activation_authorized=False, runtime_configuration_authorized=False,
        publication_authorized=False, evidence_max_age_seconds=3600, fail_closed=True,
    )
    return CanonicalSystemdExecStartBindingPolicyV1(**(values | overrides))


def _identity(**overrides: object) -> CanonicalSystemdExecStartIdentityV1:
    values = dict(
        unit_id="execstart-unit-v1", service_unit="ai-crypto-signal-agent.service",
        service_manager_scope="SYSTEM", deployment_state="NOT_YET_INSTALLED",
        service_user="ai-crypto-signal-agent", service_group="ai-crypto-signal-agent",
        installation_path=_INSTALLATION, working_directory=_INSTALLATION,
        python_interpreter=_PYTHON, launcher_module=_MODULE, manual_entrypoint="./run_scanner.sh",
        manual_entrypoint_allowed=False,
    )
    return CanonicalSystemdExecStartIdentityV1(**(values | overrides))


def _command(**overrides: object) -> CanonicalSystemdExecStartCommandV1:
    values = dict(
        command_id="execstart-command-v1", command_kind="PYTHON_MODULE", executable=_PYTHON,
        arguments=("-m", _MODULE), shell_wrapper_used=False, environment_file_used=False,
        dotenv_used=False, shell_expansion_used=False, credential_argument_used=False,
        provider_endpoint_argument_used=False, authorization_argument_used=False,
        proxy_argument_used=False, command_metadata_valid=True,
        production_cli_execution_ready=False,
    )
    return CanonicalSystemdExecStartCommandV1(**(values | overrides))


def _passive_mode(**overrides: object) -> CanonicalSystemdExecStartPassiveModeV1:
    values = dict(
        launcher_id="passive-launcher-v1", execution_mode="PASSIVE_TEST_MODE", passive_default=True,
        activation_gate_open=False, credential_gate_open=False, network_gate_open=False,
        workload_gate_open=False, real_signal_registration_authorized=False,
        production_cli_execution_authorized=False, production_runtime_execution_authorized=False,
        runtime_activation_authorized=False,
    )
    return CanonicalSystemdExecStartPassiveModeV1(**(values | overrides))


def _credential_boundary(**overrides: object) -> CanonicalSystemdExecStartCredentialBoundaryV1:
    values = dict(
        credential_boundary_id="execstart-credential-boundary-v1",
        secret_store_selection="SYSTEMD_CREDENTIALS", placement_method="SYSTEMD_ENCRYPTED_CREDENTIAL",
        credential_names=("deepseek_api_key", "anthropic_api_key"),
        future_drop_in_name="50-provider-credentials.conf",
        future_load_directive="LoadCredentialEncrypted=", owner_secret_entry_authorized=True,
        owner_secret_entry_executed=False, credential_presence_claimed=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        credential_gate_open=False, command_contains_credential_reference=False,
        credential_exposure_detected=False,
    )
    return CanonicalSystemdExecStartCredentialBoundaryV1(**(values | overrides))


def _environment_boundary(**overrides: object) -> CanonicalSystemdExecStartEnvironmentBoundaryV1:
    values = dict(
        environment_boundary_id="execstart-environment-boundary-v1",
        environment_read_authorized=False, environment_file_allowed=False, dotenv_allowed=False,
        secret_environment_allowed=False, environment_dump_allowed=False,
        credentials_directory_read_authorized=False, argv_secret_material_allowed=False,
        environment_boundary_ready=True,
    )
    return CanonicalSystemdExecStartEnvironmentBoundaryV1(**(values | overrides))


def _directory_binding(**overrides: object) -> CanonicalSystemdExecStartDirectoryBindingV1:
    values = dict(
        directory_binding_id="execstart-directories-v1", working_directory=_INSTALLATION,
        state_directory="/var/lib/ai-crypto-signal-agent",
        cache_directory="/var/cache/ai-crypto-signal-agent",
        runtime_directory="/run/ai-crypto-signal-agent", log_destination="JOURNALD_ONLY",
        log_directory="NONE", source_tree_read_only=True, state_directory_write_authorized=False,
        cache_directory_write_authorized=False, runtime_directory_write_authorized=False,
        directory_binding_ready=True,
    )
    return CanonicalSystemdExecStartDirectoryBindingV1(**(values | overrides))


def _lifecycle_binding(**overrides: object) -> CanonicalSystemdExecStartLifecycleBindingV1:
    values = dict(
        lifecycle_binding_id="execstart-lifecycle-v1", deterministic_startup_order=True,
        configuration_validation_before_passive_readiness=True, no_implicit_activation=True,
        no_implicit_credential_loading=True, no_implicit_network_activation=True,
        no_implicit_workload_startup=True, synthetic_shutdown_policy_verified=True,
        real_signal_registration_authorized=False, production_signal_handling_ready=False,
        service_restart_policy_classification="METADATA_ONLY", start_timeout_classification="METADATA_ONLY",
        stop_timeout_classification="METADATA_ONLY", failure_exit_classification="METADATA_ONLY",
        lifecycle_binding_ready=True,
    )
    return CanonicalSystemdExecStartLifecycleBindingV1(**(values | overrides))


def _checklist(**overrides: object) -> CanonicalSystemdExecStartReadinessChecklistV1:
    values = dict(
        checklist_id="execstart-checklist-v1", canonical_service_identity_confirmed=True,
        canonical_service_user_group_confirmed=True, installation_path_confirmed=True,
        working_directory_confirmed=True, python_interpreter_confirmed=True,
        launcher_module_confirmed=True, manual_entrypoint_rejected=True,
        shell_wrapper_absent=True, environment_file_sourcing_absent=True, dotenv_sourcing_absent=True,
        credential_arguments_absent=True, provider_endpoint_arguments_absent=True,
        proxy_arguments_absent=True, passive_mode_confirmed=True, all_gates_closed=True,
        synthetic_signal_behavior_confirmed=True, real_signal_handling_unresolved=True,
        production_cli_execution_unauthorized=True, unit_generation_unauthorized=True,
        installation_unauthorized=True, credential_loading_unauthorized=True,
        network_unauthorized=True, production_runtime_unauthorized=True,
        operator_attestation_complete=True, reviewer_approval_complete=True, evidence_fresh=True,
        checklist_complete=True,
    )
    return CanonicalSystemdExecStartReadinessChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> CanonicalSystemdExecStartOperatorAttestationV1:
    values = dict(
        attestation_id="execstart-operator-attestation-v1", operator_identity="operator-v1",
        operator_role="OPERATOR", policy_id="execstart-binding-policy-v1",
        command_id="execstart-command-v1", launcher_id="passive-launcher-v1",
        checklist_id="execstart-checklist-v1", canonical_command_confirmed=True,
        shell_environment_credential_exclusions_confirmed=True, passive_only_confirmed=True,
        production_cli_execution_unauthorized_confirmed=True,
        real_signal_handling_not_ready_confirmed=True,
        systemd_installation_unauthorized_confirmed=True, sensitive_evidence_retained=False,
        attested_at=_NOW - timedelta(minutes=5), expires_at=_NOW + timedelta(minutes=5),
        attestation_complete=True,
    )
    return CanonicalSystemdExecStartOperatorAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> CanonicalSystemdExecStartIndependentReviewerApprovalV1:
    values = dict(
        approval_id="execstart-reviewer-approval-v1", reviewer_identity="reviewer-v1",
        reviewer_role="INDEPENDENT_REVIEWER", policy_id="execstart-binding-policy-v1",
        command_id="execstart-command-v1", launcher_id="passive-launcher-v1",
        checklist_id="execstart-checklist-v1", attestation_id="execstart-operator-attestation-v1",
        canonical_command_confirmed=True, shell_environment_credential_exclusions_confirmed=True,
        passive_only_confirmed=True, production_cli_execution_unauthorized_confirmed=True,
        real_signal_handling_not_ready_confirmed=True,
        systemd_installation_unauthorized_confirmed=True, sensitive_evidence_retained=False,
        approved=True, reviewed_at=_NOW - timedelta(minutes=4), expires_at=_NOW + timedelta(minutes=5),
        review_complete=True,
    )
    return CanonicalSystemdExecStartIndependentReviewerApprovalV1(**(values | overrides))


def _evaluate(**overrides: object) -> CanonicalSystemdExecStartDecisionV1:
    values = dict(
        policy=_policy(), identity=_identity(), command=_command(), passive_mode=_passive_mode(),
        credential_boundary=_credential_boundary(), environment_boundary=_environment_boundary(),
        directory_binding=_directory_binding(), lifecycle_binding=_lifecycle_binding(),
        checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(),
        evaluation_time=_NOW,
    )
    return evaluate_canonical_systemd_execstart_passive_launcher_binding_v1(**(values | overrides))


def _assert_authority(record: object) -> None:
    assert record.service_unit_design_authorized is True
    assert record.passive_launcher_implementation_authorized is True
    assert record.passive_test_execution_authorized is True
    assert record.owner_secret_entry_authorized is True
    for name in (
        "production_cli_binding_implementation_authorized", "systemd_unit_file_generation_authorized",
        "systemd_drop_in_generation_authorized", "service_user_group_creation_authorized",
        "installation_directory_creation_authorized", "virtualenv_installation_authorized",
        "service_unit_installation_authorized", "daemon_reload_authorized",
        "service_enablement_authorized", "service_start_restart_authorized",
        "credential_value_access_authorized", "credential_loading_authorized",
        "credential_validation_authorized", "network_authorized", "provider_transmission_authorized",
        "scanner_execution_authorized", "worker_start_authorized", "scheduler_start_authorized",
        "telegram_start_authorized", "database_mutation_authorized",
        "artifact_publication_authorized", "trading_authorized",
        "production_runtime_execution_authorized", "runtime_activation_authorized",
        "runtime_configuration_authorized", "publication_authorized",
    ):
        assert getattr(record, name) is False
    assert record.fail_closed is True


def test_public_contract_records_are_frozen_slotted_and_redacted() -> None:
    records = (
        _policy(), _identity(), _command(), _passive_mode(), _credential_boundary(),
        _environment_boundary(), _directory_binding(), _lifecycle_binding(), _checklist(),
        _operator(), _reviewer(),
    )
    for record in records:
        _frozen(record)
    for record_type in (
        CanonicalSystemdExecStartFailureV1, CanonicalSystemdExecStartDecisionV1,
        CanonicalSystemdExecStartAuditEvidenceV1,
    ):
        assert hasattr(record_type, "__dataclass_fields__")
    forbidden = (
        "credential_value", "credential_path", "environment_value", "provider_endpoint",
        "authorization_header", "token_value", "process_id", "hostname", "account_identity",
    )
    names = tuple(name.lower() for record in records for name in (field.name for field in fields(record)))
    assert not any(token in name for name in names for token in forbidden)


def test_exact_python_module_command_is_metadata_valid_but_execution_remains_blocked() -> None:
    decision = _evaluate()
    _frozen(decision)
    assert decision.ready is True
    assert decision.decision_classification == (
        "CANONICAL_SYSTEMD_EXECSTART_PASSIVE_LAUNCHER_BINDING_READY_FOR_SEPARATE_PRODUCTION_CLI_DECISION"
    )
    assert decision.command_metadata_valid is True
    assert decision.production_cli_execution_ready is False
    assert decision.failure_codes == ()
    assert decision.states == (
        "PASSIVE_LAUNCHER_IMPLEMENTED", "EXECSTART_COMMAND_METADATA_DEFINED",
        "EXECSTART_COMMAND_METADATA_VALID", "PRODUCTION_CLI_BINDING_NOT_IMPLEMENTED",
        "REAL_SIGNAL_HANDLING_NOT_IMPLEMENTED", "CREDENTIAL_NOT_PRESENT", "CREDENTIAL_NOT_LOADED",
        "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED", "SERVICE_UNIT_NOT_INSTALLED",
        "SERVICE_EXECUTION_NOT_AUTHORIZED", "DEPLOYMENT_BLOCKED",
    )
    _assert_authority(decision)


@pytest.mark.parametrize(
    ("overrides", "failure_code"),
    (
        ({"policy": _policy(policy_id="")}, "POLICY_ID_EMPTY"),
        ({"policy": _policy(policy_version="")}, "POLICY_VERSION_EMPTY"),
        ({"identity": _identity(service_unit="other.service")}, "SERVICE_UNIT_MISMATCH"),
        ({"identity": _identity(service_manager_scope="USER")}, "SERVICE_MANAGER_SCOPE_MISMATCH"),
        ({"identity": _identity(deployment_state="INSTALLED")}, "DEPLOYMENT_STATE_MISMATCH"),
        ({"identity": _identity(service_user="other-user")}, "SERVICE_USER_MISMATCH"),
        ({"identity": _identity(service_group="other-group")}, "SERVICE_GROUP_MISMATCH"),
        ({"identity": _identity(installation_path="/opt/other")}, "INSTALLATION_PATH_MISMATCH"),
        ({"identity": _identity(working_directory="/opt/other")}, "WORKING_DIRECTORY_MISMATCH"),
        ({"identity": _identity(python_interpreter="python")}, "PYTHON_INTERPRETER_MISMATCH"),
        ({"identity": _identity(launcher_module="other.module")}, "LAUNCHER_MODULE_MISMATCH"),
        ({"identity": _identity(manual_entrypoint_allowed=True)}, "MANUAL_ENTRYPOINT_NOT_ALLOWED"),
        ({"command": _command(command_kind="SHELL")}, "PYTHON_MODULE_COMMAND_REQUIRED"),
        ({"command": _command(shell_wrapper_used=True)}, "SHELL_WRAPPER_NOT_ALLOWED"),
        ({"command": _command(arguments=("-m", "other.module"))}, "EXECSTART_ARGUMENT_MISMATCH"),
        ({"command": _command(environment_file_used=True)}, "ENVIRONMENT_FILE_NOT_ALLOWED"),
        ({"command": _command(dotenv_used=True)}, "DOTENV_NOT_ALLOWED"),
        ({"environment_boundary": _environment_boundary(environment_read_authorized=True)}, "ENVIRONMENT_READ_NOT_AUTHORIZED"),
        ({"command": _command(credential_argument_used=True)}, "CREDENTIAL_ARGUMENT_NOT_ALLOWED"),
        ({"command": _command(provider_endpoint_argument_used=True)}, "PROVIDER_ENDPOINT_ARGUMENT_NOT_ALLOWED"),
        ({"command": _command(authorization_argument_used=True)}, "AUTHORIZATION_ARGUMENT_NOT_ALLOWED"),
        ({"command": _command(proxy_argument_used=True)}, "PROXY_ARGUMENT_NOT_ALLOWED"),
        ({"passive_mode": _passive_mode(passive_default=False)}, "PASSIVE_DEFAULT_REQUIRED"),
        ({"passive_mode": _passive_mode(activation_gate_open=True)}, "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
        ({"passive_mode": _passive_mode(credential_gate_open=True)}, "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
        ({"passive_mode": _passive_mode(network_gate_open=True)}, "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ({"passive_mode": _passive_mode(workload_gate_open=True)}, "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
        ({"passive_mode": _passive_mode(production_cli_execution_authorized=True)}, "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED"),
        ({"passive_mode": _passive_mode(real_signal_registration_authorized=True)}, "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED"),
        ({"lifecycle_binding": _lifecycle_binding(production_signal_handling_ready=True)}, "PRODUCTION_SIGNAL_HANDLING_NOT_READY"),
        ({"credential_boundary": _credential_boundary(credential_presence_claimed=True)}, "CREDENTIAL_PRESENCE_NOT_ESTABLISHED"),
        ({"credential_boundary": _credential_boundary(credential_loading_authorized=True)}, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ({"credential_boundary": _credential_boundary(credential_validation_authorized=True)}, "CREDENTIAL_VALIDATION_NOT_AUTHORIZED"),
        ({"policy": _policy(network_authorized=True)}, "NETWORK_NOT_AUTHORIZED"),
        ({"policy": _policy(scanner_execution_authorized=True)}, "WORKLOAD_NOT_AUTHORIZED"),
        ({"directory_binding": _directory_binding(working_directory="/opt/other")}, "DIRECTORY_BINDING_MISMATCH"),
        ({"directory_binding": _directory_binding(state_directory_write_authorized=True)}, "FILESYSTEM_WRITE_NOT_AUTHORIZED"),
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
        ({"policy": _policy(runtime_activation_authorized=True)}, "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ({"policy": _policy(publication_authorized=True)}, "PUBLICATION_NOT_AUTHORIZED"),
        ({"credential_boundary": _credential_boundary(credential_exposure_detected=True)}, "RAW_CREDENTIAL_EXPOSURE_DETECTED"),
        ({"command": _command(provider_endpoint_argument_used=True)}, "PROVIDER_MATERIAL_EXPOSURE_DETECTED"),
        ({"checklist": _checklist(checklist_complete=False)}, "RAW_EXCEPTION_EXPOSURE_DETECTED"),
    ),
)
def test_mismatches_and_live_authority_attempts_fail_closed_deterministically(
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


def test_credential_environment_and_command_boundaries_exclude_sensitive_material() -> None:
    command = _command()
    credential = _credential_boundary()
    environment = _environment_boundary()
    assert command.arguments == ("-m", _MODULE)
    assert command.shell_wrapper_used is False
    assert command.environment_file_used is False
    assert command.dotenv_used is False
    assert command.credential_argument_used is False
    assert command.provider_endpoint_argument_used is False
    assert command.authorization_argument_used is False
    assert command.proxy_argument_used is False
    assert credential.credential_presence_claimed is False
    assert credential.credential_loading_authorized is False
    assert credential.credential_validation_authorized is False
    assert credential.credential_gate_open is False
    assert environment.environment_read_authorized is False
    assert environment.credentials_directory_read_authorized is False
    assert environment.argv_secret_material_allowed is False


def test_audit_evidence_is_immutable_redacted_and_preserves_the_deployment_block() -> None:
    decision = _evaluate()
    evidence = build_canonical_systemd_execstart_passive_launcher_binding_audit_evidence_v1(
        audit_id="execstart-audit-v1", policy=_policy(), identity=_identity(), command=_command(),
        passive_mode=_passive_mode(), credential_boundary=_credential_boundary(),
        environment_boundary=_environment_boundary(), directory_binding=_directory_binding(),
        lifecycle_binding=_lifecycle_binding(), checklist=_checklist(), operator_attestation=_operator(),
        reviewer_approval=_reviewer(), decision=decision, evaluation_time=_NOW,
    )
    _frozen(evidence)
    assert evidence.deployment_blocked is True
    assert evidence.production_cli_execution_ready is False
    assert evidence.real_signal_handling_ready is False
    assert evidence.failure_codes == ()
    _assert_authority(evidence)
    forbidden = ("credential_value", "credential_path", "provider_endpoint", "authorization", "environment_value")
    assert not any(token in field.name.lower() for field in fields(evidence) for token in forbidden)


def test_checklist_and_evidence_cannot_turn_metadata_readiness_into_systemd_execution() -> None:
    decision = _evaluate()
    assert decision.ready is True
    assert decision.service_unit_exists is False
    assert decision.systemd_execution_authorized is False
    assert decision.credential_present is False
    assert decision.credential_loaded is False
    assert decision.network_active is False
    assert decision.workload_active is False
    assert decision.runtime_activated is False
    assert decision.publication_occurred is False
