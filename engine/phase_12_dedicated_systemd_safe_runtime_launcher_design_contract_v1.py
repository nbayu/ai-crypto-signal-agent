"""Pure metadata boundary for a passive systemd-safe launcher design."""
from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from datetime import datetime, timedelta
from typing import ClassVar


_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "LAUNCHER_DESIGN_NOT_AUTHORIZED",
    "SERVICE_UNIT_MISMATCH", "SERVICE_USER_MISMATCH", "SERVICE_GROUP_MISMATCH",
    "INSTALLATION_PATH_MISMATCH", "WORKING_DIRECTORY_MISMATCH",
    "PYTHON_INTERPRETER_PATH_MISMATCH", "STATE_DIRECTORY_MISMATCH",
    "CACHE_DIRECTORY_MISMATCH", "RUNTIME_DIRECTORY_MISMATCH", "LOG_DESTINATION_MISMATCH",
    "LOG_DIRECTORY_NOT_ALLOWED", "RELATIVE_PATH_NOT_ALLOWED", "DEVELOPMENT_HOME_PATH_NOT_ALLOWED",
    "MANUAL_ENTRYPOINT_NOT_ALLOWED_FOR_SYSTEMD", "PASSIVE_DEFAULT_REQUIRED",
    "ENVIRONMENT_FILE_SOURCING_NOT_ALLOWED", "DOTENV_SOURCING_NOT_ALLOWED",
    "CREDENTIAL_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_PRESENCE_NOT_ESTABLISHED",
    "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "CREDENTIAL_VALIDATION_NOT_AUTHORIZED", "NETWORK_GATE_MUST_REMAIN_CLOSED",
    "DNS_NOT_AUTHORIZED", "SOCKET_NOT_AUTHORIZED", "TLS_NOT_AUTHORIZED", "PROXY_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "SCANNER_EXECUTION_NOT_AUTHORIZED", "WORKER_START_NOT_AUTHORIZED",
    "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED", "TRADING_NOT_AUTHORIZED",
    "AUTOMATIC_PROVIDER_RETRY_NOT_AUTHORIZED", "SIGNAL_POLICY_REQUIRED",
    "GRACEFUL_SHUTDOWN_REQUIRED", "SHUTDOWN_TIMEOUT_REQUIRED", "SOURCE_TREE_MUST_BE_READ_ONLY",
    "WRITABLE_PATH_POLICY_REQUIRED", "CREDENTIAL_COPY_NOT_AUTHORIZED",
    "JOURNALD_ONLY_LOGGING_REQUIRED", "LOG_REDACTION_REQUIRED",
    "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED",
    "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE", "EVIDENCE_EXPIRED",
    "LAUNCHER_IMPLEMENTATION_NOT_AUTHORIZED", "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED",
    "DAEMON_RELOAD_NOT_AUTHORIZED", "SERVICE_ENABLEMENT_NOT_AUTHORIZED",
    "SERVICE_START_RESTART_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "RUNTIME_CONFIGURATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)
_SUPPORTED_STATES = (
    "PASSIVE_STARTUP", "CONFIGURATION_SHAPE_VALIDATED", "ACTIVATION_GATE_CLOSED",
    "CREDENTIAL_GATE_CLOSED", "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED",
    "READY_FOR_SEPARATE_ACTIVATION_DECISION", "SHUTDOWN_REQUESTED",
    "GRACEFUL_SHUTDOWN_COMPLETE", "LAUNCHER_BLOCKED",
)
_INSTALLATION_PATH = "/opt/ai-crypto-signal-agent"
_PYTHON_PATH = "/opt/ai-crypto-signal-agent/.venv/bin/python"
_STATE_PATH = "/var/lib/ai-crypto-signal-agent"
_CACHE_PATH = "/var/cache/ai-crypto-signal-agent"
_RUNTIME_PATH = "/run/ai-crypto-signal-agent"


class _AuthorityView:
    launcher_design_authorized: ClassVar[bool] = True
    owner_secret_entry_authorized: ClassVar[bool] = True
    launcher_implementation_authorized: ClassVar[bool] = False
    service_unit_installation_authorized: ClassVar[bool] = False
    daemon_reload_authorized: ClassVar[bool] = False
    service_enablement_authorized: ClassVar[bool] = False
    service_start_restart_authorized: ClassVar[bool] = False
    credential_value_access_authorized: ClassVar[bool] = False
    credential_loading_authorized: ClassVar[bool] = False
    credential_validation_authorized: ClassVar[bool] = False
    network_authorized: ClassVar[bool] = False
    provider_transmission_authorized: ClassVar[bool] = False
    runtime_activation_authorized: ClassVar[bool] = False
    runtime_configuration_authorized: ClassVar[bool] = False
    publication_authorized: ClassVar[bool] = False
    fail_closed: ClassVar[bool] = True


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherPolicyV1(_AuthorityView):
    policy_id: str
    policy_version: str
    launcher_design_authorized: bool
    require_passive_default: bool
    require_closed_activation_gate: bool
    require_closed_credential_gate: bool
    require_closed_network_gate: bool
    require_closed_workload_gate: bool
    require_signal_policy: bool
    require_graceful_shutdown: bool
    require_directory_policy: bool
    require_journald_only_logging: bool
    require_independent_review: bool
    evidence_max_age_seconds: int
    fail_closed: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherIdentityV1(_AuthorityView):
    launcher_id: str
    launcher_version: str
    launcher_kind: str
    expected_module_name: str
    expected_callable_name: str
    expected_execution_mode: str
    expected_service_unit: str
    expected_service_user: str
    expected_service_group: str
    expected_installation_path: str
    expected_working_directory: str
    expected_python_interpreter: str
    current_manual_entrypoint: str
    manual_entrypoint_allowed_for_systemd: bool
    launcher_design_authorized: bool
    launcher_implementation_authorized: bool
    runtime_activation_authorized: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherPathBindingV1(_AuthorityView):
    path_binding_id: str
    installation_path: str
    working_directory: str
    python_interpreter_path: str
    state_directory: str
    cache_directory: str
    runtime_directory: str
    log_destination: str
    log_directory: str
    source_tree_read_only: bool
    state_writes_restricted: bool
    cache_writes_restricted: bool
    runtime_writes_restricted: bool
    no_writable_source_tree: bool
    no_secret_path_metadata: bool
    path_binding_ready: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherActivationGateV1(_AuthorityView):
    activation_gate_id: str
    activation_requested: bool
    activation_authorized: bool
    activation_token_present: bool
    owner_decision_identity: str
    readiness_evidence_identity: str
    service_installation_state: str
    credential_presence_state: str
    credential_loading_state: str
    network_authority_state: str
    runtime_authority_state: str
    publication_authority_state: str
    activation_gate_open: bool
    activation_gate_failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherCredentialGateV1(_AuthorityView):
    credential_gate_id: str
    secret_store_selection: str
    placement_method: str
    expected_credentials_directory_classification: str
    provider_ids: tuple[str, ...]
    logical_credential_labels: tuple[str, ...]
    credential_names: tuple[str, ...]
    routing_levels: tuple[tuple[str, ...], ...]
    exact_provider_model_ids: tuple[tuple[str, ...], ...]
    owner_secret_entry_authorized: bool
    owner_secret_entry_executed: bool
    credential_presence_claimed: bool
    environment_file_sourcing_allowed: bool
    dotenv_sourcing_allowed: bool
    shell_export_allowed: bool
    credential_argument_reference_detected: bool
    credential_value_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    credential_gate_open: bool
    sensitive_material_declared: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherNetworkGateV1(_AuthorityView):
    network_gate_id: str
    network_requested: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    endpoint_resolution_authorized: bool
    dns_authorized: bool
    socket_authorized: bool
    tls_authorized: bool
    proxy_authorized: bool
    network_gate_open: bool
    network_failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherWorkloadGateV1(_AuthorityView):
    workload_gate_id: str
    scanner_execution_authorized: bool
    worker_start_authorized: bool
    scheduler_start_authorized: bool
    quota_mutation_authorized: bool
    reservation_mutation_authorized: bool
    usage_ledger_mutation_authorized: bool
    provider_call_authorized: bool
    telegram_start_authorized: bool
    signal_publication_authorized: bool
    database_mutation_authorized: bool
    artifact_publication_authorized: bool
    trading_authorized: bool
    workload_gate_open: bool
    automatic_provider_retry_authorized: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherSignalPolicyV1(_AuthorityView):
    signal_policy_id: str
    sigterm_handling_defined: bool
    sigint_handling_defined: bool
    sighup_classification: str
    duplicate_signal_behavior: str
    handler_reentrancy_policy: str
    shutdown_request_state_transition: str
    no_signal_triggered_provider_activity: bool
    no_signal_triggered_credential_loading: bool
    no_signal_triggered_publication: bool
    signal_policy_ready: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherShutdownPolicyV1(_AuthorityView):
    shutdown_policy_id: str
    graceful_shutdown_required: bool
    shutdown_timeout_seconds: int
    deterministic_shutdown_ordering: bool
    worker_stop_coordination_defined: bool
    scheduler_stop_coordination_defined: bool
    provider_session_close_classification: str
    telegram_stop_classification: str
    pending_artifact_policy: str
    pending_reservation_policy: str
    usage_ledger_mutation_prohibited_while_inactive: bool
    repeated_shutdown_idempotent: bool
    final_exit_classification: str
    forced_kill_fallback_classification: str
    shutdown_policy_ready: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherLoggingPolicyV1(_AuthorityView):
    logging_policy_id: str
    log_destination: str
    structured_metadata_classification: str
    api_key_values_forbidden: bool
    secret_derived_identifiers_forbidden: bool
    credential_paths_forbidden: bool
    billing_details_forbidden: bool
    environment_dumps_forbidden: bool
    exception_sanitization_required: bool
    stack_trace_classification: str
    rate_limiting_classification: str
    startup_event_classification: str
    shutdown_event_classification: str
    activation_gate_decision_classification: str
    logging_policy_ready: bool
    authorization_headers_forbidden: InitVar[bool] = True
    provider_response_bodies_forbidden: InitVar[bool] = True
    credential_transport_headers_forbidden: bool = field(init=False)
    upstream_payload_bodies_forbidden: bool = field(init=False)

    def __post_init__(
        self,
        authorization_headers_forbidden: bool,
        provider_response_bodies_forbidden: bool,
    ) -> None:
        object.__setattr__(
            self,
            "credential_transport_headers_forbidden",
            authorization_headers_forbidden,
        )
        object.__setattr__(
            self,
            "upstream_payload_bodies_forbidden",
            provider_response_bodies_forbidden,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherDirectoryPolicyV1(_AuthorityView):
    directory_policy_id: str
    source_tree_read_only: bool
    state_directory_durable_only: bool
    cache_directory_disposable_only: bool
    runtime_directory_transient_only: bool
    explicit_log_directory_forbidden: bool
    journald_only: bool
    credential_copying_forbidden: bool
    api_key_persistence_forbidden: bool
    unrestricted_temporary_paths_forbidden: bool
    directory_policy_ready: bool
    provider_response_persistence_forbidden: InitVar[bool] = True
    upstream_payload_persistence_forbidden: bool = field(init=False)

    def __post_init__(self, provider_response_persistence_forbidden: bool) -> None:
        object.__setattr__(
            self,
            "upstream_payload_persistence_forbidden",
            provider_response_persistence_forbidden,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherChecklistV1(_AuthorityView):
    checklist_id: str
    policy_id: str
    launcher_id: str
    path_binding_id: str
    activation_gate_id: str
    credential_gate_id: str
    network_gate_id: str
    workload_gate_id: str
    signal_policy_id: str
    shutdown_policy_id: str
    logging_policy_id: str
    directory_policy_id: str
    canonical_service_identity_confirmed: bool
    service_user_group_confirmed: bool
    installation_working_paths_confirmed: bool
    interpreter_path_confirmed: bool
    passive_default_confirmed: bool
    manual_entrypoint_rejected_for_systemd: bool
    credential_gate_closed: bool
    network_gate_closed: bool
    workload_gate_closed: bool
    activation_gate_closed: bool
    no_environment_file_sourcing: bool
    no_implicit_credentials: bool
    no_implicit_network: bool
    no_automatic_provider_retry: bool
    writable_path_policy_complete: bool
    signal_handling_complete: bool
    graceful_shutdown_complete: bool
    journald_logging_complete: bool
    redaction_complete: bool
    implementation_unauthorized: bool
    installation_unauthorized: bool
    runtime_activation_unauthorized: bool
    operator_attestation_complete: bool
    reviewer_approval_complete: bool
    evidence_fresh: bool
    checklist_complete: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherOperatorAttestationV1(_AuthorityView):
    attestation_id: str
    policy_id: str
    launcher_id: str
    checklist_id: str
    operator_id: str
    operator_role: str
    attested_at: datetime
    expires_at: datetime
    redacted_metadata_only: bool
    passive_design_confirmed: bool
    no_implementation_performed: bool
    no_credential_accessed: bool
    no_runtime_executed: bool
    no_sensitive_material_retained: bool
    raw_exception_exposure_detected: bool
    attestation_complete: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherIndependentReviewerApprovalV1(_AuthorityView):
    approval_id: str
    policy_id: str
    launcher_id: str
    checklist_id: str
    attestation_id: str
    reviewer_id: str
    reviewer_role: str
    approved_at: datetime
    expires_at: datetime
    redacted_evidence_only: bool
    passive_design_confirmed: bool
    design_approved: bool
    no_sensitive_material_retained: bool
    review_complete: bool


@dataclass(frozen=True, slots=True)
class SystemdSafeRuntimeLauncherFailureV1(_AuthorityView):
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherDecisionV1(_AuthorityView):
    policy_id: str
    launcher_id: str
    ready: bool
    design_state: str
    state_codes: tuple[str, ...]
    supported_state_codes: tuple[str, ...]
    failure_codes: tuple[str, ...]
    failures: tuple[SystemdSafeRuntimeLauncherFailureV1, ...]
    launcher_design_authorized: bool
    owner_secret_entry_authorized: bool
    launcher_implementation_authorized: bool
    service_unit_installation_authorized: bool
    daemon_reload_authorized: bool
    service_enablement_authorized: bool
    service_start_restart_authorized: bool
    credential_value_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    runtime_activation_authorized: bool
    runtime_configuration_authorized: bool
    publication_authorized: bool
    fail_closed: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemdSafeRuntimeLauncherAuditEvidenceV1(_AuthorityView):
    evidence_id: str
    policy_id: str
    launcher_id: str
    path_binding_id: str
    credential_names: tuple[str, ...]
    state_codes: tuple[str, ...]
    failure_codes: tuple[str, ...]
    operator_id: str
    operator_role: str
    reviewer_id: str
    reviewer_role: str
    evidence_freshness: str
    launcher_design_authorized: bool
    owner_secret_entry_authorized: bool
    launcher_implementation_authorized: bool
    service_unit_installation_authorized: bool
    daemon_reload_authorized: bool
    service_enablement_authorized: bool
    service_start_restart_authorized: bool
    credential_value_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    runtime_activation_authorized: bool
    runtime_configuration_authorized: bool
    publication_authorized: bool
    fail_closed: bool


def _failures(codes: tuple[str, ...]) -> tuple[SystemdSafeRuntimeLauncherFailureV1, ...]:
    return tuple(
        SystemdSafeRuntimeLauncherFailureV1(
            failure_code=code, safe_message="fail-closed policy rejection", retryable=False,
        )
        for code in codes
    )


def _codes(conditions: dict[str, bool]) -> tuple[str, ...]:
    return tuple(code for code in _FAILURES if conditions.get(code, False))


def _blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _bad_path(value: object) -> bool:
    return _blank(value) or not value.startswith("/")


def _authority_values() -> dict[str, bool]:
    return {
        "launcher_design_authorized": True, "owner_secret_entry_authorized": True,
        "launcher_implementation_authorized": False, "service_unit_installation_authorized": False,
        "daemon_reload_authorized": False, "service_enablement_authorized": False,
        "service_start_restart_authorized": False, "credential_value_access_authorized": False,
        "credential_loading_authorized": False, "credential_validation_authorized": False,
        "network_authorized": False, "provider_transmission_authorized": False,
        "runtime_activation_authorized": False, "runtime_configuration_authorized": False,
        "publication_authorized": False, "fail_closed": True,
    }


def evaluate_systemd_safe_runtime_launcher_design_v1(
    *,
    policy: SystemdSafeRuntimeLauncherPolicyV1,
    identity: SystemdSafeRuntimeLauncherIdentityV1,
    paths: SystemdSafeRuntimeLauncherPathBindingV1,
    activation_gate: SystemdSafeRuntimeLauncherActivationGateV1,
    credential_gate: SystemdSafeRuntimeLauncherCredentialGateV1,
    network_gate: SystemdSafeRuntimeLauncherNetworkGateV1,
    workload_gate: SystemdSafeRuntimeLauncherWorkloadGateV1,
    signal_policy: SystemdSafeRuntimeLauncherSignalPolicyV1,
    shutdown_policy: SystemdSafeRuntimeLauncherShutdownPolicyV1,
    logging_policy: SystemdSafeRuntimeLauncherLoggingPolicyV1,
    directory_policy: SystemdSafeRuntimeLauncherDirectoryPolicyV1,
    checklist: SystemdSafeRuntimeLauncherChecklistV1,
    operator_attestation: SystemdSafeRuntimeLauncherOperatorAttestationV1,
    reviewer_approval: SystemdSafeRuntimeLauncherIndependentReviewerApprovalV1,
    evaluated_at: datetime,
    directories: SystemdSafeRuntimeLauncherDirectoryPolicyV1 | None = None,
) -> SystemdSafeRuntimeLauncherDecisionV1:
    """Classify caller-supplied design metadata without performing any operation."""
    if directories is not None:
        directory_policy = directories
    policy_type_ok = isinstance(policy, SystemdSafeRuntimeLauncherPolicyV1)
    identity_type_ok = isinstance(identity, SystemdSafeRuntimeLauncherIdentityV1)
    paths_type_ok = isinstance(paths, SystemdSafeRuntimeLauncherPathBindingV1)
    activation_type_ok = isinstance(activation_gate, SystemdSafeRuntimeLauncherActivationGateV1)
    credential_type_ok = isinstance(credential_gate, SystemdSafeRuntimeLauncherCredentialGateV1)
    network_type_ok = isinstance(network_gate, SystemdSafeRuntimeLauncherNetworkGateV1)
    workload_type_ok = isinstance(workload_gate, SystemdSafeRuntimeLauncherWorkloadGateV1)
    signal_type_ok = isinstance(signal_policy, SystemdSafeRuntimeLauncherSignalPolicyV1)
    shutdown_type_ok = isinstance(shutdown_policy, SystemdSafeRuntimeLauncherShutdownPolicyV1)
    logging_type_ok = isinstance(logging_policy, SystemdSafeRuntimeLauncherLoggingPolicyV1)
    directory_type_ok = isinstance(directory_policy, SystemdSafeRuntimeLauncherDirectoryPolicyV1)
    checklist_type_ok = isinstance(checklist, SystemdSafeRuntimeLauncherChecklistV1)
    operator_type_ok = isinstance(operator_attestation, SystemdSafeRuntimeLauncherOperatorAttestationV1)
    reviewer_type_ok = isinstance(reviewer_approval, SystemdSafeRuntimeLauncherIndependentReviewerApprovalV1)
    time_ok = isinstance(evaluated_at, datetime)

    def value(record: object, name: str, default: object = None) -> object:
        return getattr(record, name, default)

    path_values = (
        value(paths, "installation_path"), value(paths, "working_directory"),
        value(paths, "python_interpreter_path"), value(paths, "state_directory"),
        value(paths, "cache_directory"), value(paths, "runtime_directory"),
    )
    checklist_identity_ok = checklist_type_ok and all((
        checklist.policy_id == value(policy, "policy_id"), checklist.launcher_id == value(identity, "launcher_id"),
        checklist.path_binding_id == value(paths, "path_binding_id"),
        checklist.activation_gate_id == value(activation_gate, "activation_gate_id"),
        checklist.credential_gate_id == value(credential_gate, "credential_gate_id"),
        checklist.network_gate_id == value(network_gate, "network_gate_id"),
        checklist.workload_gate_id == value(workload_gate, "workload_gate_id"),
        checklist.signal_policy_id == value(signal_policy, "signal_policy_id"),
        checklist.shutdown_policy_id == value(shutdown_policy, "shutdown_policy_id"),
        checklist.logging_policy_id == value(logging_policy, "logging_policy_id"),
        checklist.directory_policy_id == value(directory_policy, "directory_policy_id"),
    ))
    operator_identity_ok = operator_type_ok and all((
        operator_attestation.policy_id == value(policy, "policy_id"),
        operator_attestation.launcher_id == value(identity, "launcher_id"),
        operator_attestation.checklist_id == value(checklist, "checklist_id"),
    ))
    reviewer_identity_ok = reviewer_type_ok and all((
        reviewer_approval.policy_id == value(policy, "policy_id"),
        reviewer_approval.launcher_id == value(identity, "launcher_id"),
        reviewer_approval.checklist_id == value(checklist, "checklist_id"),
        reviewer_approval.attestation_id == value(operator_attestation, "attestation_id"),
    ))

    stale = operator_type_ok and time_ok and (
        operator_attestation.attested_at < evaluated_at - timedelta_seconds(value(policy, "evidence_max_age_seconds"))
        or operator_attestation.attested_at > evaluated_at
    )
    future = operator_type_ok and time_ok and operator_attestation.attested_at > evaluated_at
    expired = operator_type_ok and time_ok and operator_attestation.expires_at < evaluated_at
    reviewer_future = reviewer_type_ok and time_ok and reviewer_approval.approved_at > evaluated_at
    reviewer_stale = reviewer_type_ok and time_ok and (
        reviewer_approval.approved_at < evaluated_at - timedelta_seconds(value(policy, "evidence_max_age_seconds"))
        or reviewer_approval.approved_at > evaluated_at
    )
    reviewer_expired = reviewer_type_ok and time_ok and reviewer_approval.expires_at < evaluated_at
    expected_credentials = (
        ("DEEPSEEK", "ANTHROPIC"), ("DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"),
        ("deepseek_api_key", "anthropic_api_key"), (("L0",), ("L1", "L2")),
        (("deepseek-v4-pro",), ("claude-sonnet-5", "claude-opus-4-8")),
    )
    observed_credentials = (
        value(credential_gate, "provider_ids"), value(credential_gate, "logical_credential_labels"),
        value(credential_gate, "credential_names"), value(credential_gate, "routing_levels"),
        value(credential_gate, "exact_provider_model_ids"),
    )
    signal_complete = signal_type_ok and all((
        signal_policy.sigterm_handling_defined, signal_policy.sigint_handling_defined,
        not _blank(signal_policy.sighup_classification), not _blank(signal_policy.duplicate_signal_behavior),
        not _blank(signal_policy.handler_reentrancy_policy),
        signal_policy.shutdown_request_state_transition == "SHUTDOWN_REQUESTED",
        signal_policy.no_signal_triggered_provider_activity,
        signal_policy.no_signal_triggered_credential_loading,
        signal_policy.no_signal_triggered_publication, signal_policy.signal_policy_ready,
    ))
    shutdown_complete = shutdown_type_ok and all((
        shutdown_policy.graceful_shutdown_required, shutdown_policy.shutdown_timeout_seconds > 0,
        shutdown_policy.deterministic_shutdown_ordering, shutdown_policy.worker_stop_coordination_defined,
        shutdown_policy.scheduler_stop_coordination_defined,
        not _blank(shutdown_policy.provider_session_close_classification),
        not _blank(shutdown_policy.telegram_stop_classification),
        not _blank(shutdown_policy.pending_artifact_policy), not _blank(shutdown_policy.pending_reservation_policy),
        shutdown_policy.usage_ledger_mutation_prohibited_while_inactive,
        shutdown_policy.repeated_shutdown_idempotent, not _blank(shutdown_policy.final_exit_classification),
        not _blank(shutdown_policy.forced_kill_fallback_classification), shutdown_policy.shutdown_policy_ready,
    ))
    logging_complete = logging_type_ok and all((
        logging_policy.log_destination == "JOURNALD_ONLY",
        not _blank(logging_policy.structured_metadata_classification), logging_policy.api_key_values_forbidden,
        logging_policy.secret_derived_identifiers_forbidden, logging_policy.credential_paths_forbidden,
        logging_policy.credential_transport_headers_forbidden, logging_policy.upstream_payload_bodies_forbidden,
        logging_policy.billing_details_forbidden, logging_policy.environment_dumps_forbidden,
        logging_policy.exception_sanitization_required, not _blank(logging_policy.stack_trace_classification),
        not _blank(logging_policy.rate_limiting_classification), not _blank(logging_policy.startup_event_classification),
        not _blank(logging_policy.shutdown_event_classification),
        not _blank(logging_policy.activation_gate_decision_classification), logging_policy.logging_policy_ready,
    ))
    directory_complete = directory_type_ok and all((
        directory_policy.source_tree_read_only, directory_policy.state_directory_durable_only,
        directory_policy.cache_directory_disposable_only, directory_policy.runtime_directory_transient_only,
        directory_policy.explicit_log_directory_forbidden, directory_policy.journald_only,
        directory_policy.credential_copying_forbidden, directory_policy.api_key_persistence_forbidden,
        directory_policy.upstream_payload_persistence_forbidden,
        directory_policy.unrestricted_temporary_paths_forbidden, directory_policy.directory_policy_ready,
    ))
    conditions = {
        "POLICY_ID_EMPTY": not policy_type_ok or _blank(value(policy, "policy_id")),
        "POLICY_VERSION_EMPTY": not policy_type_ok or _blank(value(policy, "policy_version")),
        "LAUNCHER_DESIGN_NOT_AUTHORIZED": not policy_type_ok or value(policy, "launcher_design_authorized") is not True,
        "SERVICE_UNIT_MISMATCH": not identity_type_ok or value(identity, "expected_service_unit") != "ai-crypto-signal-agent.service",
        "SERVICE_USER_MISMATCH": not identity_type_ok or value(identity, "expected_service_user") != "ai-crypto-signal-agent",
        "SERVICE_GROUP_MISMATCH": not identity_type_ok or value(identity, "expected_service_group") != "ai-crypto-signal-agent",
        "INSTALLATION_PATH_MISMATCH": not paths_type_ok or value(paths, "installation_path") != _INSTALLATION_PATH,
        "WORKING_DIRECTORY_MISMATCH": not paths_type_ok or value(paths, "working_directory") != _INSTALLATION_PATH,
        "PYTHON_INTERPRETER_PATH_MISMATCH": not paths_type_ok or value(paths, "python_interpreter_path") != _PYTHON_PATH,
        "STATE_DIRECTORY_MISMATCH": not paths_type_ok or value(paths, "state_directory") != _STATE_PATH,
        "CACHE_DIRECTORY_MISMATCH": not paths_type_ok or value(paths, "cache_directory") != _CACHE_PATH,
        "RUNTIME_DIRECTORY_MISMATCH": not paths_type_ok or value(paths, "runtime_directory") != _RUNTIME_PATH,
        "LOG_DESTINATION_MISMATCH": not paths_type_ok or value(paths, "log_destination") != "JOURNALD_ONLY",
        "LOG_DIRECTORY_NOT_ALLOWED": not paths_type_ok or value(paths, "log_directory") != "NONE",
        "RELATIVE_PATH_NOT_ALLOWED": not paths_type_ok or any(_bad_path(item) for item in path_values),
        "DEVELOPMENT_HOME_PATH_NOT_ALLOWED": paths_type_ok and any(
            isinstance(item, str) and item.startswith("/home/") for item in path_values
        ),
        "MANUAL_ENTRYPOINT_NOT_ALLOWED_FOR_SYSTEMD": not identity_type_ok or (
            value(identity, "current_manual_entrypoint") != "./run_scanner.sh"
            or value(identity, "manual_entrypoint_allowed_for_systemd") is not False
        ),
        "PASSIVE_DEFAULT_REQUIRED": not policy_type_ok or not identity_type_ok or not all((
            policy.require_passive_default, identity.expected_execution_mode == "PASSIVE_DEFAULT",
        )),
        "ENVIRONMENT_FILE_SOURCING_NOT_ALLOWED": not credential_type_ok or credential_gate.environment_file_sourcing_allowed,
        "DOTENV_SOURCING_NOT_ALLOWED": not credential_type_ok or credential_gate.dotenv_sourcing_allowed,
        "CREDENTIAL_GATE_MUST_REMAIN_CLOSED": not credential_type_ok or not policy_type_ok or any((
            not policy.require_closed_credential_gate, credential_gate.credential_gate_open,
            credential_gate.secret_store_selection != "SYSTEMD_CREDENTIALS",
            credential_gate.placement_method != "SYSTEMD_ENCRYPTED_CREDENTIAL",
            credential_gate.expected_credentials_directory_classification != "CREDENTIALS_DIRECTORY",
            observed_credentials != expected_credentials, credential_gate.owner_secret_entry_authorized is not True,
            credential_gate.owner_secret_entry_executed,
        )),
        "CREDENTIAL_PRESENCE_NOT_ESTABLISHED": not credential_type_ok or credential_gate.credential_presence_claimed,
        "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED": not credential_type_ok or credential_gate.credential_value_access_authorized,
        "CREDENTIAL_LOADING_NOT_AUTHORIZED": not credential_type_ok or credential_gate.credential_loading_authorized,
        "CREDENTIAL_VALIDATION_NOT_AUTHORIZED": not credential_type_ok or credential_gate.credential_validation_authorized,
        "NETWORK_GATE_MUST_REMAIN_CLOSED": not network_type_ok or not policy_type_ok or any((
            not policy.require_closed_network_gate, network_gate.network_gate_open, network_gate.network_requested,
            network_gate.network_authorized, network_gate.endpoint_resolution_authorized,
        )),
        "DNS_NOT_AUTHORIZED": not network_type_ok or network_gate.dns_authorized,
        "SOCKET_NOT_AUTHORIZED": not network_type_ok or network_gate.socket_authorized,
        "TLS_NOT_AUTHORIZED": not network_type_ok or network_gate.tls_authorized,
        "PROXY_NOT_AUTHORIZED": not network_type_ok or network_gate.proxy_authorized,
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED": not network_type_ok or network_gate.provider_transmission_authorized,
        "WORKLOAD_GATE_MUST_REMAIN_CLOSED": not workload_type_ok or not policy_type_ok or any((
            not policy.require_closed_workload_gate, workload_gate.workload_gate_open,
            workload_gate.quota_mutation_authorized, workload_gate.reservation_mutation_authorized,
            workload_gate.usage_ledger_mutation_authorized, workload_gate.provider_call_authorized,
        )),
        "SCANNER_EXECUTION_NOT_AUTHORIZED": not workload_type_ok or workload_gate.scanner_execution_authorized,
        "WORKER_START_NOT_AUTHORIZED": not workload_type_ok or workload_gate.worker_start_authorized,
        "SCHEDULER_START_NOT_AUTHORIZED": not workload_type_ok or workload_gate.scheduler_start_authorized,
        "TELEGRAM_START_NOT_AUTHORIZED": not workload_type_ok or workload_gate.telegram_start_authorized,
        "DATABASE_MUTATION_NOT_AUTHORIZED": not workload_type_ok or workload_gate.database_mutation_authorized,
        "ARTIFACT_PUBLICATION_NOT_AUTHORIZED": not workload_type_ok or workload_gate.artifact_publication_authorized,
        "TRADING_NOT_AUTHORIZED": not workload_type_ok or workload_gate.trading_authorized,
        "AUTOMATIC_PROVIDER_RETRY_NOT_AUTHORIZED": not workload_type_ok or workload_gate.automatic_provider_retry_authorized,
        "SIGNAL_POLICY_REQUIRED": not policy_type_ok or not policy.require_signal_policy or not signal_complete,
        "GRACEFUL_SHUTDOWN_REQUIRED": not policy_type_ok or not policy.require_graceful_shutdown or not shutdown_complete,
        "SHUTDOWN_TIMEOUT_REQUIRED": not shutdown_type_ok or not isinstance(shutdown_policy.shutdown_timeout_seconds, int) or shutdown_policy.shutdown_timeout_seconds <= 0,
        "SOURCE_TREE_MUST_BE_READ_ONLY": not paths_type_ok or not directory_type_ok or not all((
            paths.source_tree_read_only, paths.no_writable_source_tree, directory_policy.source_tree_read_only,
        )),
        "WRITABLE_PATH_POLICY_REQUIRED": not paths_type_ok or not directory_complete or not all((
            paths.state_writes_restricted, paths.cache_writes_restricted, paths.runtime_writes_restricted,
            paths.path_binding_ready, len(set(path_values[3:])) == len(path_values[3:]),
        )),
        "CREDENTIAL_COPY_NOT_AUTHORIZED": not paths_type_ok or not directory_type_ok or not all((
            paths.no_secret_path_metadata, directory_policy.credential_copying_forbidden,
            directory_policy.api_key_persistence_forbidden, directory_policy.upstream_payload_persistence_forbidden,
        )),
        "JOURNALD_ONLY_LOGGING_REQUIRED": not policy_type_ok or not logging_type_ok or not directory_type_ok or not all((
            policy.require_journald_only_logging, logging_policy.log_destination == "JOURNALD_ONLY",
            directory_policy.journald_only,
        )),
        "LOG_REDACTION_REQUIRED": not logging_complete,
        "OPERATOR_ATTESTATION_REQUIRED": not operator_type_ok or not checklist_type_ok or not operator_identity_ok or any((
            _blank(value(operator_attestation, "operator_id")), _blank(value(operator_attestation, "operator_role")),
            not value(operator_attestation, "redacted_metadata_only"),
            not value(operator_attestation, "passive_design_confirmed"),
            not value(operator_attestation, "no_implementation_performed"),
            not value(operator_attestation, "no_credential_accessed"),
            not value(operator_attestation, "no_runtime_executed"),
            not value(operator_attestation, "no_sensitive_material_retained"),
            not value(operator_attestation, "attestation_complete"),
            not value(checklist, "operator_attestation_complete"),
        )),
        "REVIEWER_APPROVAL_REQUIRED": not reviewer_type_ok or not checklist_type_ok or not reviewer_identity_ok or any((
            _blank(value(reviewer_approval, "reviewer_id")), _blank(value(reviewer_approval, "reviewer_role")),
            not value(reviewer_approval, "redacted_evidence_only"), not value(reviewer_approval, "passive_design_confirmed"),
            not value(reviewer_approval, "design_approved"), not value(reviewer_approval, "no_sensitive_material_retained"),
            not value(reviewer_approval, "review_complete"), not value(checklist, "reviewer_approval_complete"),
            value(reviewer_approval, "reviewer_id") == value(operator_attestation, "operator_id"),
        )),
        "OPERATOR_REVIEWER_COLLISION": operator_type_ok and reviewer_type_ok and (
            _blank(operator_attestation.operator_id)
            or _blank(reviewer_approval.reviewer_id)
            or operator_attestation.operator_id == reviewer_approval.reviewer_id
        ),
        "EVIDENCE_FROM_FUTURE": not time_ok or future or reviewer_future,
        "EVIDENCE_STALE": not time_ok or stale or reviewer_stale or not value(checklist, "evidence_fresh"),
        "EVIDENCE_EXPIRED": not time_ok or expired or reviewer_expired,
        "LAUNCHER_IMPLEMENTATION_NOT_AUTHORIZED": not identity_type_ok or identity.launcher_implementation_authorized,
        "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED": not activation_type_ok or activation_gate.service_installation_state != "NOT_YET_INSTALLED",
        "DAEMON_RELOAD_NOT_AUTHORIZED": not activation_type_ok or activation_gate.readiness_evidence_identity == "DAEMON_RELOAD_AUTHORIZED",
        "SERVICE_ENABLEMENT_NOT_AUTHORIZED": not activation_type_ok or activation_gate.credential_loading_state == "SERVICE_ENABLEMENT_AUTHORIZED",
        "SERVICE_START_RESTART_NOT_AUTHORIZED": not activation_type_ok or activation_gate.network_authority_state == "SERVICE_START_RESTART_AUTHORIZED",
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED": not identity_type_ok or identity.runtime_activation_authorized,
        "RUNTIME_CONFIGURATION_NOT_AUTHORIZED": not activation_type_ok or activation_gate.runtime_authority_state == "RUNTIME_CONFIGURATION_AUTHORIZED",
        "PUBLICATION_NOT_AUTHORIZED": not activation_type_ok or activation_gate.publication_authority_state != "NOT_AUTHORIZED",
        "RAW_CREDENTIAL_EXPOSURE_DETECTED": not credential_type_ok or any((
            credential_gate.shell_export_allowed, credential_gate.credential_argument_reference_detected,
            credential_gate.sensitive_material_declared,
        )),
        "RAW_EXCEPTION_EXPOSURE_DETECTED": not operator_type_ok or operator_attestation.raw_exception_exposure_detected,
    }
    codes = _codes(conditions)
    ready = not codes
    states = (
        ("PASSIVE_STARTUP", "CONFIGURATION_SHAPE_VALIDATED", "ACTIVATION_GATE_CLOSED",
         "CREDENTIAL_GATE_CLOSED", "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED",
         "READY_FOR_SEPARATE_ACTIVATION_DECISION") if ready else ("LAUNCHER_BLOCKED",)
    )
    return SystemdSafeRuntimeLauncherDecisionV1(
        policy_id=value(policy, "policy_id", ""), launcher_id=value(identity, "launcher_id", ""), ready=ready,
        design_state=("SYSTEMD_SAFE_RUNTIME_LAUNCHER_DESIGN_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION"
                      if ready else "LAUNCHER_BLOCKED"),
        state_codes=states, supported_state_codes=_SUPPORTED_STATES, failure_codes=codes,
        failures=_failures(codes), **_authority_values(),
    )


def timedelta_seconds(value: object) -> timedelta:
    """Create a duration from caller-supplied policy metadata only."""
    return timedelta(seconds=value if isinstance(value, int) and value >= 0 else 0)


def build_systemd_safe_runtime_launcher_design_audit_evidence_v1(
    *,
    evidence_id: str,
    policy: SystemdSafeRuntimeLauncherPolicyV1,
    identity: SystemdSafeRuntimeLauncherIdentityV1,
    paths: SystemdSafeRuntimeLauncherPathBindingV1,
    activation_gate: SystemdSafeRuntimeLauncherActivationGateV1,
    credential_gate: SystemdSafeRuntimeLauncherCredentialGateV1,
    network_gate: SystemdSafeRuntimeLauncherNetworkGateV1,
    workload_gate: SystemdSafeRuntimeLauncherWorkloadGateV1,
    signal_policy: SystemdSafeRuntimeLauncherSignalPolicyV1,
    shutdown_policy: SystemdSafeRuntimeLauncherShutdownPolicyV1,
    logging_policy: SystemdSafeRuntimeLauncherLoggingPolicyV1,
    directory_policy: SystemdSafeRuntimeLauncherDirectoryPolicyV1,
    checklist: SystemdSafeRuntimeLauncherChecklistV1,
    operator_attestation: SystemdSafeRuntimeLauncherOperatorAttestationV1,
    reviewer_approval: SystemdSafeRuntimeLauncherIndependentReviewerApprovalV1,
    decision: SystemdSafeRuntimeLauncherDecisionV1,
    built_at: datetime,
) -> SystemdSafeRuntimeLauncherAuditEvidenceV1:
    """Build immutable redacted evidence from aligned caller-supplied metadata."""
    del activation_gate, network_gate, workload_gate, signal_policy, shutdown_policy, logging_policy, directory_policy, built_at
    alignment = all((
        isinstance(decision, SystemdSafeRuntimeLauncherDecisionV1),
        decision.policy_id == policy.policy_id, decision.launcher_id == identity.launcher_id,
        checklist.policy_id == policy.policy_id, checklist.launcher_id == identity.launcher_id,
        checklist.path_binding_id == paths.path_binding_id,
        operator_attestation.policy_id == policy.policy_id, operator_attestation.launcher_id == identity.launcher_id,
        operator_attestation.checklist_id == checklist.checklist_id,
        reviewer_approval.policy_id == policy.policy_id, reviewer_approval.launcher_id == identity.launcher_id,
        reviewer_approval.checklist_id == checklist.checklist_id,
        reviewer_approval.attestation_id == operator_attestation.attestation_id,
    ))
    return SystemdSafeRuntimeLauncherAuditEvidenceV1(
        evidence_id=evidence_id, policy_id=policy.policy_id, launcher_id=identity.launcher_id,
        path_binding_id=paths.path_binding_id, credential_names=credential_gate.credential_names,
        state_codes=decision.state_codes,
        failure_codes=(decision.failure_codes if alignment else ("RAW_EXCEPTION_EXPOSURE_DETECTED",)),
        operator_id=operator_attestation.operator_id, operator_role=operator_attestation.operator_role,
        reviewer_id=reviewer_approval.reviewer_id, reviewer_role=reviewer_approval.reviewer_role,
        evidence_freshness=("FRESH" if alignment and not decision.failure_codes else "NOT_READY"),
        **_authority_values(),
    )
