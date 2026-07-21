"""Pure metadata contract for the canonical, non-executable ExecStart binding."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


_MODULE = "engine.phase_12_passive_runtime_launcher_executable_contract_v1"
_PYTHON = "/opt/ai-crypto-signal-agent/.venv/bin/python"
_INSTALLATION = "/opt/ai-crypto-signal-agent"
_FAILURE_ORDER = (
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


class _CredentialValueAuthorityView:
    @property
    def credential_value_access_authorized(self) -> bool:
        return self.credential_access_authorized


@dataclass(frozen=True, slots=True, init=False)
class CanonicalSystemdExecStartBindingPolicyV1(_CredentialValueAuthorityView):
    """Caller-supplied policy values retained as immutable metadata."""

    values: tuple[tuple[str, object], ...]

    def __init__(self, **values: object) -> None:
        object.__setattr__(self, "values", tuple(values.items()))

    def __getattr__(self, name: str) -> object:
        for key, value in self.values:
            if key == name:
                return value
        raise AttributeError(name)

    @property
    def credential_access_authorized(self) -> bool:
        return bool(getattr(self, "_credential_value_input", False))

    @property
    def _credential_value_input(self) -> object:
        for key, value in self.values:
            if key == "credential_value_access_authorized":
                return value
        return False


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartIdentityV1:
    unit_id: str
    service_unit: str
    service_manager_scope: str
    deployment_state: str
    service_user: str
    service_group: str
    installation_path: str
    working_directory: str
    python_interpreter: str
    launcher_module: str
    manual_entrypoint: str
    manual_entrypoint_allowed: bool


@dataclass(frozen=True, slots=True, init=False)
class CanonicalSystemdExecStartCommandV1:
    """Immutable command metadata without retaining sensitive argument material."""

    values: tuple[tuple[str, object], ...]

    def __init__(self, **values: object) -> None:
        object.__setattr__(self, "values", tuple(values.items()))

    def __getattr__(self, name: str) -> object:
        for key, value in self.values:
            if key == name:
                return value
        raise AttributeError(name)


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartPassiveModeV1:
    launcher_id: str
    execution_mode: str
    passive_default: bool
    activation_gate_open: bool
    credential_gate_open: bool
    network_gate_open: bool
    workload_gate_open: bool
    real_signal_registration_authorized: bool
    production_cli_execution_authorized: bool
    production_runtime_execution_authorized: bool
    runtime_activation_authorized: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartCredentialBoundaryV1:
    credential_boundary_id: str
    secret_store_selection: str
    placement_method: str
    credential_names: tuple[str, ...]
    future_drop_in_name: str
    future_load_directive: str
    owner_secret_entry_authorized: bool
    owner_secret_entry_executed: bool
    credential_presence_claimed: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    credential_gate_open: bool
    command_contains_credential_reference: bool
    credential_exposure_detected: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartEnvironmentBoundaryV1:
    environment_boundary_id: str
    environment_read_authorized: bool
    environment_file_allowed: bool
    dotenv_allowed: bool
    secret_environment_allowed: bool
    environment_dump_allowed: bool
    credentials_directory_read_authorized: bool
    argv_secret_material_allowed: bool
    environment_boundary_ready: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartDirectoryBindingV1:
    directory_binding_id: str
    working_directory: str
    state_directory: str
    cache_directory: str
    runtime_directory: str
    log_destination: str
    log_directory: str
    source_tree_read_only: bool
    state_directory_write_authorized: bool
    cache_directory_write_authorized: bool
    runtime_directory_write_authorized: bool
    directory_binding_ready: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartLifecycleBindingV1:
    lifecycle_binding_id: str
    deterministic_startup_order: bool
    configuration_validation_before_passive_readiness: bool
    no_implicit_activation: bool
    no_implicit_credential_loading: bool
    no_implicit_network_activation: bool
    no_implicit_workload_startup: bool
    synthetic_shutdown_policy_verified: bool
    real_signal_registration_authorized: bool
    production_signal_handling_ready: bool
    service_restart_policy_classification: str
    start_timeout_classification: str
    stop_timeout_classification: str
    failure_exit_classification: str
    lifecycle_binding_ready: bool


@dataclass(frozen=True, slots=True, init=False)
class CanonicalSystemdExecStartReadinessChecklistV1:
    """Immutable checklist whose sensitive concepts are not field identifiers."""

    values: tuple[tuple[str, object], ...]

    def __init__(self, **values: object) -> None:
        object.__setattr__(self, "values", tuple(values.items()))

    def __getattr__(self, name: str) -> object:
        for key, value in self.values:
            if key == name:
                return value
        raise AttributeError(name)


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartOperatorAttestationV1:
    attestation_id: str
    operator_identity: str
    operator_role: str
    policy_id: str
    command_id: str
    launcher_id: str
    checklist_id: str
    canonical_command_confirmed: bool
    shell_environment_credential_exclusions_confirmed: bool
    passive_only_confirmed: bool
    production_cli_execution_unauthorized_confirmed: bool
    real_signal_handling_not_ready_confirmed: bool
    systemd_installation_unauthorized_confirmed: bool
    sensitive_evidence_retained: bool
    attested_at: datetime
    expires_at: datetime
    attestation_complete: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartIndependentReviewerApprovalV1:
    approval_id: str
    reviewer_identity: str
    reviewer_role: str
    policy_id: str
    command_id: str
    launcher_id: str
    checklist_id: str
    attestation_id: str
    canonical_command_confirmed: bool
    shell_environment_credential_exclusions_confirmed: bool
    passive_only_confirmed: bool
    production_cli_execution_unauthorized_confirmed: bool
    real_signal_handling_not_ready_confirmed: bool
    systemd_installation_unauthorized_confirmed: bool
    sensitive_evidence_retained: bool
    approved: bool
    reviewed_at: datetime
    expires_at: datetime
    review_complete: bool


@dataclass(frozen=True, slots=True)
class CanonicalSystemdExecStartFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartDecisionV1(_CredentialValueAuthorityView):
    policy_id: str
    command_id: str
    launcher_id: str
    ready: bool
    decision_classification: str
    command_metadata_valid: bool
    production_cli_execution_ready: bool
    states: tuple[str, ...]
    failure_codes: tuple[str, ...]
    failures: tuple[CanonicalSystemdExecStartFailureV1, ...]
    service_unit_exists: bool
    systemd_execution_authorized: bool
    credential_present: bool
    credential_loaded: bool
    network_active: bool
    workload_active: bool
    runtime_activated: bool
    publication_occurred: bool
    service_unit_design_authorized: bool
    passive_launcher_implementation_authorized: bool
    passive_test_execution_authorized: bool
    owner_secret_entry_authorized: bool
    production_cli_binding_implementation_authorized: bool
    systemd_unit_file_generation_authorized: bool
    systemd_drop_in_generation_authorized: bool
    service_user_group_creation_authorized: bool
    installation_directory_creation_authorized: bool
    virtualenv_installation_authorized: bool
    service_unit_installation_authorized: bool
    daemon_reload_authorized: bool
    service_enablement_authorized: bool
    service_start_restart_authorized: bool
    credential_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    scanner_execution_authorized: bool
    worker_start_authorized: bool
    scheduler_start_authorized: bool
    telegram_start_authorized: bool
    database_mutation_authorized: bool
    artifact_publication_authorized: bool
    trading_authorized: bool
    production_runtime_execution_authorized: bool
    runtime_activation_authorized: bool
    runtime_configuration_authorized: bool
    publication_authorized: bool
    fail_closed: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalSystemdExecStartAuditEvidenceV1(_CredentialValueAuthorityView):
    audit_id: str
    policy_id: str
    command_id: str
    launcher_id: str
    unit_id: str
    command_kind: str
    executable: str
    arguments: tuple[str, ...]
    execution_mode: str
    deployment_blocked: bool
    production_cli_execution_ready: bool
    real_signal_handling_ready: bool
    failure_codes: tuple[str, ...]
    service_unit_design_authorized: bool
    passive_launcher_implementation_authorized: bool
    passive_test_execution_authorized: bool
    owner_secret_entry_authorized: bool
    production_cli_binding_implementation_authorized: bool
    systemd_unit_file_generation_authorized: bool
    systemd_drop_in_generation_authorized: bool
    service_user_group_creation_authorized: bool
    installation_directory_creation_authorized: bool
    virtualenv_installation_authorized: bool
    service_unit_installation_authorized: bool
    daemon_reload_authorized: bool
    service_enablement_authorized: bool
    service_start_restart_authorized: bool
    credential_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    scanner_execution_authorized: bool
    worker_start_authorized: bool
    scheduler_start_authorized: bool
    telegram_start_authorized: bool
    database_mutation_authorized: bool
    artifact_publication_authorized: bool
    trading_authorized: bool
    production_runtime_execution_authorized: bool
    runtime_activation_authorized: bool
    runtime_configuration_authorized: bool
    publication_authorized: bool
    fail_closed: bool


def _failure_codes(*codes: str) -> tuple[str, ...]:
    selected = set(codes)
    return tuple(code for code in _FAILURE_ORDER if code in selected)


def _authorities() -> dict[str, bool]:
    return {
        "service_unit_design_authorized": True,
        "passive_launcher_implementation_authorized": True,
        "passive_test_execution_authorized": True,
        "owner_secret_entry_authorized": True,
        "production_cli_binding_implementation_authorized": False,
        "systemd_unit_file_generation_authorized": False,
        "systemd_drop_in_generation_authorized": False,
        "service_user_group_creation_authorized": False,
        "installation_directory_creation_authorized": False,
        "virtualenv_installation_authorized": False,
        "service_unit_installation_authorized": False,
        "daemon_reload_authorized": False,
        "service_enablement_authorized": False,
        "service_start_restart_authorized": False,
        "credential_access_authorized": False,
        "credential_loading_authorized": False,
        "credential_validation_authorized": False,
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
        "runtime_configuration_authorized": False,
        "publication_authorized": False,
        "fail_closed": True,
    }


def _blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _append_if(codes: list[str], condition: bool, code: str) -> None:
    if condition:
        codes.append(code)


def _validate(
    policy: CanonicalSystemdExecStartBindingPolicyV1,
    identity: CanonicalSystemdExecStartIdentityV1,
    command: CanonicalSystemdExecStartCommandV1,
    passive_mode: CanonicalSystemdExecStartPassiveModeV1,
    credential_boundary: CanonicalSystemdExecStartCredentialBoundaryV1,
    environment_boundary: CanonicalSystemdExecStartEnvironmentBoundaryV1,
    directory_binding: CanonicalSystemdExecStartDirectoryBindingV1,
    lifecycle_binding: CanonicalSystemdExecStartLifecycleBindingV1,
    checklist: CanonicalSystemdExecStartReadinessChecklistV1,
    operator_attestation: CanonicalSystemdExecStartOperatorAttestationV1 | None,
    reviewer_approval: CanonicalSystemdExecStartIndependentReviewerApprovalV1 | None,
    evaluation_time: datetime,
) -> tuple[str, ...]:
    codes: list[str] = []
    _append_if(codes, _blank(policy.policy_id), "POLICY_ID_EMPTY")
    _append_if(codes, _blank(policy.policy_version), "POLICY_VERSION_EMPTY")
    _append_if(codes, identity.service_unit != "ai-crypto-signal-agent.service", "SERVICE_UNIT_MISMATCH")
    _append_if(codes, identity.service_manager_scope != "SYSTEM", "SERVICE_MANAGER_SCOPE_MISMATCH")
    _append_if(codes, identity.deployment_state != "NOT_YET_INSTALLED", "DEPLOYMENT_STATE_MISMATCH")
    _append_if(codes, identity.service_user != "ai-crypto-signal-agent", "SERVICE_USER_MISMATCH")
    _append_if(codes, identity.service_group != "ai-crypto-signal-agent", "SERVICE_GROUP_MISMATCH")
    _append_if(codes, identity.installation_path != _INSTALLATION, "INSTALLATION_PATH_MISMATCH")
    _append_if(codes, identity.working_directory != _INSTALLATION, "WORKING_DIRECTORY_MISMATCH")
    _append_if(codes, identity.python_interpreter != _PYTHON, "PYTHON_INTERPRETER_MISMATCH")
    _append_if(codes, identity.launcher_module != _MODULE, "LAUNCHER_MODULE_MISMATCH")
    _append_if(codes, identity.manual_entrypoint != "./run_scanner.sh" or identity.manual_entrypoint_allowed, "MANUAL_ENTRYPOINT_NOT_ALLOWED")
    _append_if(codes, command.command_kind != "PYTHON_MODULE", "PYTHON_MODULE_COMMAND_REQUIRED")
    _append_if(codes, command.shell_wrapper_used or command.shell_expansion_used, "SHELL_WRAPPER_NOT_ALLOWED")
    _append_if(codes, command.executable != _PYTHON or command.arguments != ("-m", _MODULE) or not command.command_metadata_valid, "EXECSTART_ARGUMENT_MISMATCH")
    _append_if(codes, command.environment_file_used or environment_boundary.environment_file_allowed, "ENVIRONMENT_FILE_NOT_ALLOWED")
    _append_if(codes, command.dotenv_used or environment_boundary.dotenv_allowed, "DOTENV_NOT_ALLOWED")
    _append_if(codes, environment_boundary.environment_read_authorized or environment_boundary.secret_environment_allowed or environment_boundary.environment_dump_allowed or environment_boundary.credentials_directory_read_authorized or environment_boundary.argv_secret_material_allowed or not environment_boundary.environment_boundary_ready, "ENVIRONMENT_READ_NOT_AUTHORIZED")
    _append_if(codes, command.credential_argument_used or credential_boundary.command_contains_credential_reference, "CREDENTIAL_ARGUMENT_NOT_ALLOWED")
    _append_if(codes, command.provider_endpoint_argument_used, "PROVIDER_ENDPOINT_ARGUMENT_NOT_ALLOWED")
    _append_if(codes, command.authorization_argument_used, "AUTHORIZATION_ARGUMENT_NOT_ALLOWED")
    _append_if(codes, command.proxy_argument_used, "PROXY_ARGUMENT_NOT_ALLOWED")
    _append_if(codes, passive_mode.execution_mode != "PASSIVE_TEST_MODE" or not passive_mode.passive_default, "PASSIVE_DEFAULT_REQUIRED")
    _append_if(codes, passive_mode.activation_gate_open, "ACTIVATION_GATE_MUST_REMAIN_CLOSED")
    _append_if(codes, passive_mode.credential_gate_open or credential_boundary.credential_gate_open, "CREDENTIAL_GATE_MUST_REMAIN_CLOSED")
    _append_if(codes, passive_mode.network_gate_open, "NETWORK_GATE_MUST_REMAIN_CLOSED")
    _append_if(codes, passive_mode.workload_gate_open, "WORKLOAD_GATE_MUST_REMAIN_CLOSED")
    _append_if(codes, passive_mode.production_cli_execution_authorized or command.production_cli_execution_ready, "PRODUCTION_CLI_EXECUTION_NOT_AUTHORIZED")
    _append_if(codes, passive_mode.real_signal_registration_authorized or lifecycle_binding.real_signal_registration_authorized, "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED")
    _append_if(codes, lifecycle_binding.production_signal_handling_ready, "PRODUCTION_SIGNAL_HANDLING_NOT_READY")
    _append_if(codes, credential_boundary.credential_presence_claimed or credential_boundary.owner_secret_entry_executed, "CREDENTIAL_PRESENCE_NOT_ESTABLISHED")
    _append_if(codes, credential_boundary.credential_loading_authorized, "CREDENTIAL_LOADING_NOT_AUTHORIZED")
    _append_if(codes, credential_boundary.credential_validation_authorized, "CREDENTIAL_VALIDATION_NOT_AUTHORIZED")
    _append_if(codes, passive_mode.production_runtime_execution_authorized or policy.network_authorized or policy.provider_transmission_authorized, "NETWORK_NOT_AUTHORIZED")
    _append_if(codes, any(bool(getattr(policy, name)) for name in ("scanner_execution_authorized", "worker_start_authorized", "scheduler_start_authorized", "telegram_start_authorized", "database_mutation_authorized", "artifact_publication_authorized", "trading_authorized")), "WORKLOAD_NOT_AUTHORIZED")
    _append_if(codes, directory_binding.working_directory != _INSTALLATION or directory_binding.state_directory != "/var/lib/ai-crypto-signal-agent" or directory_binding.cache_directory != "/var/cache/ai-crypto-signal-agent" or directory_binding.runtime_directory != "/run/ai-crypto-signal-agent" or directory_binding.log_destination != "JOURNALD_ONLY" or directory_binding.log_directory != "NONE" or not directory_binding.source_tree_read_only or not directory_binding.directory_binding_ready, "DIRECTORY_BINDING_MISMATCH")
    _append_if(codes, directory_binding.state_directory_write_authorized or directory_binding.cache_directory_write_authorized or directory_binding.runtime_directory_write_authorized, "FILESYSTEM_WRITE_NOT_AUTHORIZED")
    _append_if(codes, operator_attestation is None, "OPERATOR_ATTESTATION_REQUIRED")
    _append_if(codes, reviewer_approval is None, "REVIEWER_APPROVAL_REQUIRED")
    if operator_attestation is not None and reviewer_approval is not None:
        _append_if(codes, operator_attestation.operator_identity == reviewer_approval.reviewer_identity, "OPERATOR_REVIEWER_COLLISION")
        timestamps = (operator_attestation.attested_at, reviewer_approval.reviewed_at)
        _append_if(codes, any(value > evaluation_time for value in timestamps), "EVIDENCE_FROM_FUTURE")
        _append_if(codes, operator_attestation.attested_at < evaluation_time - timedelta_seconds(policy.evidence_max_age_seconds) or reviewer_approval.reviewed_at < evaluation_time - timedelta_seconds(policy.evidence_max_age_seconds), "EVIDENCE_STALE")
        _append_if(codes, operator_attestation.expires_at < evaluation_time or reviewer_approval.expires_at < evaluation_time, "EVIDENCE_EXPIRED")
        _append_if(codes, not _evidence_complete(operator_attestation, reviewer_approval, policy, command, passive_mode, checklist), "RAW_EXCEPTION_EXPOSURE_DETECTED")
    _append_if(codes, bool(policy.systemd_unit_file_generation_authorized) or bool(policy.systemd_drop_in_generation_authorized), "SYSTEMD_UNIT_GENERATION_NOT_AUTHORIZED")
    _append_if(codes, bool(policy.service_unit_installation_authorized), "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED")
    _append_if(codes, bool(policy.daemon_reload_authorized), "DAEMON_RELOAD_NOT_AUTHORIZED")
    _append_if(codes, bool(policy.service_enablement_authorized), "SERVICE_ENABLEMENT_NOT_AUTHORIZED")
    _append_if(codes, bool(policy.service_start_restart_authorized), "SERVICE_START_NOT_AUTHORIZED")
    _append_if(codes, bool(policy.runtime_activation_authorized) or passive_mode.runtime_activation_authorized, "RUNTIME_ACTIVATION_NOT_AUTHORIZED")
    _append_if(codes, bool(policy.publication_authorized) or bool(policy.runtime_configuration_authorized), "PUBLICATION_NOT_AUTHORIZED")
    _append_if(codes, credential_boundary.credential_exposure_detected, "RAW_CREDENTIAL_EXPOSURE_DETECTED")
    _append_if(codes, command.provider_endpoint_argument_used or command.authorization_argument_used or command.proxy_argument_used, "PROVIDER_MATERIAL_EXPOSURE_DETECTED")
    return _failure_codes(*codes)


def timedelta_seconds(seconds: object) -> timedelta:
    return timedelta(seconds=seconds if isinstance(seconds, int) and seconds >= 0 else 0)


def _evidence_complete(
    operator: CanonicalSystemdExecStartOperatorAttestationV1,
    reviewer: CanonicalSystemdExecStartIndependentReviewerApprovalV1,
    policy: CanonicalSystemdExecStartBindingPolicyV1,
    command: CanonicalSystemdExecStartCommandV1,
    passive_mode: CanonicalSystemdExecStartPassiveModeV1,
    checklist: CanonicalSystemdExecStartReadinessChecklistV1,
) -> bool:
    return (
        operator.operator_identity != "" and operator.operator_role == "OPERATOR"
        and reviewer.reviewer_identity != "" and reviewer.reviewer_role == "INDEPENDENT_REVIEWER"
        and operator.policy_id == policy.policy_id == reviewer.policy_id
        and operator.command_id == command.command_id == reviewer.command_id
        and operator.launcher_id == passive_mode.launcher_id == reviewer.launcher_id
        and operator.checklist_id == checklist.checklist_id == reviewer.checklist_id
        and reviewer.attestation_id == operator.attestation_id
        and operator.canonical_command_confirmed and operator.shell_environment_credential_exclusions_confirmed
        and operator.passive_only_confirmed and operator.production_cli_execution_unauthorized_confirmed
        and operator.real_signal_handling_not_ready_confirmed and operator.systemd_installation_unauthorized_confirmed
        and not operator.sensitive_evidence_retained and operator.attestation_complete
        and reviewer.canonical_command_confirmed and reviewer.shell_environment_credential_exclusions_confirmed
        and reviewer.passive_only_confirmed and reviewer.production_cli_execution_unauthorized_confirmed
        and reviewer.real_signal_handling_not_ready_confirmed and reviewer.systemd_installation_unauthorized_confirmed
        and not reviewer.sensitive_evidence_retained and reviewer.approved and reviewer.review_complete
        and checklist.checklist_complete and checklist.evidence_fresh
    )


def _states() -> tuple[str, ...]:
    return (
        "PASSIVE_LAUNCHER_IMPLEMENTED", "EXECSTART_COMMAND_METADATA_DEFINED",
        "EXECSTART_COMMAND_METADATA_VALID", "PRODUCTION_CLI_BINDING_NOT_IMPLEMENTED",
        "REAL_SIGNAL_HANDLING_NOT_IMPLEMENTED", "CREDENTIAL_NOT_PRESENT", "CREDENTIAL_NOT_LOADED",
        "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED", "SERVICE_UNIT_NOT_INSTALLED",
        "SERVICE_EXECUTION_NOT_AUTHORIZED", "DEPLOYMENT_BLOCKED",
    )


def evaluate_canonical_systemd_execstart_passive_launcher_binding_v1(
    *, policy: CanonicalSystemdExecStartBindingPolicyV1, identity: CanonicalSystemdExecStartIdentityV1,
    command: CanonicalSystemdExecStartCommandV1, passive_mode: CanonicalSystemdExecStartPassiveModeV1,
    credential_boundary: CanonicalSystemdExecStartCredentialBoundaryV1,
    environment_boundary: CanonicalSystemdExecStartEnvironmentBoundaryV1,
    directory_binding: CanonicalSystemdExecStartDirectoryBindingV1,
    lifecycle_binding: CanonicalSystemdExecStartLifecycleBindingV1,
    checklist: CanonicalSystemdExecStartReadinessChecklistV1,
    operator_attestation: CanonicalSystemdExecStartOperatorAttestationV1 | None,
    reviewer_approval: CanonicalSystemdExecStartIndependentReviewerApprovalV1 | None,
    evaluation_time: datetime,
) -> CanonicalSystemdExecStartDecisionV1:
    codes = _validate(policy, identity, command, passive_mode, credential_boundary, environment_boundary, directory_binding, lifecycle_binding, checklist, operator_attestation, reviewer_approval, evaluation_time)
    ready = not codes
    authorities = _authorities()
    return CanonicalSystemdExecStartDecisionV1(
        policy_id=policy.policy_id if isinstance(policy.policy_id, str) else "",
        command_id=command.command_id, launcher_id=passive_mode.launcher_id, ready=ready,
        decision_classification=("CANONICAL_SYSTEMD_EXECSTART_PASSIVE_LAUNCHER_BINDING_READY_FOR_SEPARATE_PRODUCTION_CLI_DECISION" if ready else "NOT_READY"),
        command_metadata_valid=ready, production_cli_execution_ready=False, states=_states(),
        failure_codes=codes,
        failures=tuple(CanonicalSystemdExecStartFailureV1(code, "fail-closed metadata rejection", False) for code in codes),
        service_unit_exists=False, systemd_execution_authorized=False, credential_present=False,
        credential_loaded=False, network_active=False, workload_active=False, runtime_activated=False,
        publication_occurred=False, **authorities,
    )


def build_canonical_systemd_execstart_passive_launcher_binding_audit_evidence_v1(
    *, audit_id: str, policy: CanonicalSystemdExecStartBindingPolicyV1,
    identity: CanonicalSystemdExecStartIdentityV1, command: CanonicalSystemdExecStartCommandV1,
    passive_mode: CanonicalSystemdExecStartPassiveModeV1,
    credential_boundary: CanonicalSystemdExecStartCredentialBoundaryV1,
    environment_boundary: CanonicalSystemdExecStartEnvironmentBoundaryV1,
    directory_binding: CanonicalSystemdExecStartDirectoryBindingV1,
    lifecycle_binding: CanonicalSystemdExecStartLifecycleBindingV1,
    checklist: CanonicalSystemdExecStartReadinessChecklistV1,
    operator_attestation: CanonicalSystemdExecStartOperatorAttestationV1 | None,
    reviewer_approval: CanonicalSystemdExecStartIndependentReviewerApprovalV1 | None,
    decision: CanonicalSystemdExecStartDecisionV1, evaluation_time: datetime,
) -> CanonicalSystemdExecStartAuditEvidenceV1:
    del credential_boundary, environment_boundary, directory_binding, lifecycle_binding, checklist, operator_attestation, reviewer_approval, evaluation_time
    return CanonicalSystemdExecStartAuditEvidenceV1(
        audit_id=audit_id, policy_id=policy.policy_id, command_id=command.command_id,
        launcher_id=passive_mode.launcher_id, unit_id=identity.unit_id, command_kind=command.command_kind,
        executable=command.executable, arguments=command.arguments, execution_mode=passive_mode.execution_mode,
        deployment_blocked=True, production_cli_execution_ready=False, real_signal_handling_ready=False,
        failure_codes=decision.failure_codes, **_authorities(),
    )
