"""RED contract for a passive, systemd-safe runtime launcher design only."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from engine.phase_12_dedicated_systemd_safe_runtime_launcher_design_contract_v1 import (
    SystemdSafeRuntimeLauncherActivationGateV1,
    SystemdSafeRuntimeLauncherAuditEvidenceV1,
    SystemdSafeRuntimeLauncherChecklistV1,
    SystemdSafeRuntimeLauncherCredentialGateV1,
    SystemdSafeRuntimeLauncherDecisionV1,
    SystemdSafeRuntimeLauncherDirectoryPolicyV1,
    SystemdSafeRuntimeLauncherFailureV1,
    SystemdSafeRuntimeLauncherIdentityV1,
    SystemdSafeRuntimeLauncherIndependentReviewerApprovalV1,
    SystemdSafeRuntimeLauncherLoggingPolicyV1,
    SystemdSafeRuntimeLauncherNetworkGateV1,
    SystemdSafeRuntimeLauncherOperatorAttestationV1,
    SystemdSafeRuntimeLauncherPathBindingV1,
    SystemdSafeRuntimeLauncherPolicyV1,
    SystemdSafeRuntimeLauncherShutdownPolicyV1,
    SystemdSafeRuntimeLauncherSignalPolicyV1,
    SystemdSafeRuntimeLauncherWorkloadGateV1,
    build_systemd_safe_runtime_launcher_design_audit_evidence_v1,
    evaluate_systemd_safe_runtime_launcher_design_v1,
)


_NOW = datetime(2030, 1, 10, 12, 0, tzinfo=UTC)
_LOCKED_PATH = "/opt/ai-crypto-signal-agent"
_LOCKED_PYTHON = "/opt/ai-crypto-signal-agent/.venv/bin/python"
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
_STATES = (
    "PASSIVE_STARTUP", "CONFIGURATION_SHAPE_VALIDATED", "ACTIVATION_GATE_CLOSED",
    "CREDENTIAL_GATE_CLOSED", "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED",
    "READY_FOR_SEPARATE_ACTIVATION_DECISION", "SHUTDOWN_REQUESTED",
    "GRACEFUL_SHUTDOWN_COMPLETE", "LAUNCHER_BLOCKED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> SystemdSafeRuntimeLauncherPolicyV1:
    values = dict(
        policy_id="launcher-policy-v1", policy_version="V1", launcher_design_authorized=True,
        require_passive_default=True, require_closed_activation_gate=True,
        require_closed_credential_gate=True, require_closed_network_gate=True,
        require_closed_workload_gate=True, require_signal_policy=True,
        require_graceful_shutdown=True, require_directory_policy=True,
        require_journald_only_logging=True, require_independent_review=True,
        evidence_max_age_seconds=3600, fail_closed=True,
    )
    return SystemdSafeRuntimeLauncherPolicyV1(**(values | overrides))


def _identity(**overrides: object) -> SystemdSafeRuntimeLauncherIdentityV1:
    values = dict(
        launcher_id="launcher-identity-v1", launcher_version="V1", launcher_kind="SYSTEMD_SAFE_PASSIVE",
        expected_module_name="FUTURE_MODULE", expected_callable_name="FUTURE_CALLABLE",
        expected_execution_mode="PASSIVE_DEFAULT", expected_service_unit="ai-crypto-signal-agent.service",
        expected_service_user="ai-crypto-signal-agent", expected_service_group="ai-crypto-signal-agent",
        expected_installation_path=_LOCKED_PATH, expected_working_directory=_LOCKED_PATH,
        expected_python_interpreter=_LOCKED_PYTHON, current_manual_entrypoint="./run_scanner.sh",
        manual_entrypoint_allowed_for_systemd=False, launcher_design_authorized=True,
        launcher_implementation_authorized=False, runtime_activation_authorized=False,
    )
    return SystemdSafeRuntimeLauncherIdentityV1(**(values | overrides))


def _paths(**overrides: object) -> SystemdSafeRuntimeLauncherPathBindingV1:
    values = dict(
        path_binding_id="launcher-paths-v1", installation_path=_LOCKED_PATH,
        working_directory=_LOCKED_PATH, python_interpreter_path=_LOCKED_PYTHON,
        state_directory="/var/lib/ai-crypto-signal-agent",
        cache_directory="/var/cache/ai-crypto-signal-agent",
        runtime_directory="/run/ai-crypto-signal-agent", log_destination="JOURNALD_ONLY",
        log_directory="NONE", source_tree_read_only=True, state_writes_restricted=True,
        cache_writes_restricted=True, runtime_writes_restricted=True,
        no_writable_source_tree=True, no_secret_path_metadata=True, path_binding_ready=True,
    )
    return SystemdSafeRuntimeLauncherPathBindingV1(**(values | overrides))


def _activation(**overrides: object) -> SystemdSafeRuntimeLauncherActivationGateV1:
    values = dict(
        activation_gate_id="activation-gate-v1", activation_requested=False, activation_authorized=False,
        activation_token_present=False, owner_decision_identity="owner-decision-v1",
        readiness_evidence_identity="readiness-evidence-v1", service_installation_state="NOT_YET_INSTALLED",
        credential_presence_state="NOT_ESTABLISHED", credential_loading_state="NOT_AUTHORIZED",
        network_authority_state="NOT_AUTHORIZED", runtime_authority_state="NOT_AUTHORIZED",
        publication_authority_state="NOT_AUTHORIZED", activation_gate_open=False,
        activation_gate_failure_codes=(),
    )
    return SystemdSafeRuntimeLauncherActivationGateV1(**(values | overrides))


def _credential(**overrides: object) -> SystemdSafeRuntimeLauncherCredentialGateV1:
    values = dict(
        credential_gate_id="credential-gate-v1", secret_store_selection="SYSTEMD_CREDENTIALS",
        placement_method="SYSTEMD_ENCRYPTED_CREDENTIAL",
        expected_credentials_directory_classification="CREDENTIALS_DIRECTORY",
        provider_ids=("DEEPSEEK", "ANTHROPIC"),
        logical_credential_labels=("DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"),
        credential_names=("deepseek_api_key", "anthropic_api_key"),
        routing_levels=(("L0",), ("L1", "L2")),
        exact_provider_model_ids=(("deepseek-v4-pro",), ("claude-sonnet-5", "claude-opus-4-8")),
        owner_secret_entry_authorized=True, owner_secret_entry_executed=False,
        credential_presence_claimed=False, environment_file_sourcing_allowed=False,
        dotenv_sourcing_allowed=False, shell_export_allowed=False,
        credential_argument_reference_detected=False, credential_value_access_authorized=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        credential_gate_open=False, sensitive_material_declared=False,
    )
    return SystemdSafeRuntimeLauncherCredentialGateV1(**(values | overrides))


def _network(**overrides: object) -> SystemdSafeRuntimeLauncherNetworkGateV1:
    values = dict(
        network_gate_id="network-gate-v1", network_requested=False, network_authorized=False,
        provider_transmission_authorized=False, endpoint_resolution_authorized=False,
        dns_authorized=False, socket_authorized=False, tls_authorized=False, proxy_authorized=False,
        network_gate_open=False, network_failure_codes=(),
    )
    return SystemdSafeRuntimeLauncherNetworkGateV1(**(values | overrides))


def _workload(**overrides: object) -> SystemdSafeRuntimeLauncherWorkloadGateV1:
    values = dict(
        workload_gate_id="workload-gate-v1", scanner_execution_authorized=False,
        worker_start_authorized=False, scheduler_start_authorized=False, quota_mutation_authorized=False,
        reservation_mutation_authorized=False, usage_ledger_mutation_authorized=False,
        provider_call_authorized=False, telegram_start_authorized=False,
        signal_publication_authorized=False, database_mutation_authorized=False,
        artifact_publication_authorized=False, trading_authorized=False, workload_gate_open=False,
        automatic_provider_retry_authorized=False,
    )
    return SystemdSafeRuntimeLauncherWorkloadGateV1(**(values | overrides))


def _signal(**overrides: object) -> SystemdSafeRuntimeLauncherSignalPolicyV1:
    values = dict(
        signal_policy_id="signal-policy-v1", sigterm_handling_defined=True,
        sigint_handling_defined=True, sighup_classification="IGNORED_WHILE_PASSIVE",
        duplicate_signal_behavior="IDEMPOTENT", handler_reentrancy_policy="NO_REENTRY",
        shutdown_request_state_transition="SHUTDOWN_REQUESTED",
        no_signal_triggered_provider_activity=True, no_signal_triggered_credential_loading=True,
        no_signal_triggered_publication=True, signal_policy_ready=True,
    )
    return SystemdSafeRuntimeLauncherSignalPolicyV1(**(values | overrides))


def _shutdown(**overrides: object) -> SystemdSafeRuntimeLauncherShutdownPolicyV1:
    values = dict(
        shutdown_policy_id="shutdown-policy-v1", graceful_shutdown_required=True,
        shutdown_timeout_seconds=30, deterministic_shutdown_ordering=True,
        worker_stop_coordination_defined=True, scheduler_stop_coordination_defined=True,
        provider_session_close_classification="NOT_OPENED_WHILE_PASSIVE",
        telegram_stop_classification="NOT_STARTED_WHILE_PASSIVE",
        pending_artifact_policy="NO_ARTIFACTS_WHILE_PASSIVE",
        pending_reservation_policy="NO_RESERVATIONS_WHILE_PASSIVE",
        usage_ledger_mutation_prohibited_while_inactive=True, repeated_shutdown_idempotent=True,
        final_exit_classification="CLEAN_PASSIVE_EXIT", forced_kill_fallback_classification="SYSTEMD_ONLY",
        shutdown_policy_ready=True,
    )
    return SystemdSafeRuntimeLauncherShutdownPolicyV1(**(values | overrides))


def _logging(**overrides: object) -> SystemdSafeRuntimeLauncherLoggingPolicyV1:
    values = dict(
        logging_policy_id="logging-policy-v1", log_destination="JOURNALD_ONLY",
        structured_metadata_classification="REDACTED_METADATA_ONLY", api_key_values_forbidden=True,
        secret_derived_identifiers_forbidden=True, credential_paths_forbidden=True,
        authorization_headers_forbidden=True, provider_response_bodies_forbidden=True,
        billing_details_forbidden=True, environment_dumps_forbidden=True,
        exception_sanitization_required=True, stack_trace_classification="SANITIZED_ONLY",
        rate_limiting_classification="REQUIRED", startup_event_classification="REDACTED",
        shutdown_event_classification="REDACTED", activation_gate_decision_classification="REDACTED",
        logging_policy_ready=True,
    )
    return SystemdSafeRuntimeLauncherLoggingPolicyV1(**(values | overrides))


def _directories(**overrides: object) -> SystemdSafeRuntimeLauncherDirectoryPolicyV1:
    values = dict(
        directory_policy_id="directory-policy-v1", source_tree_read_only=True,
        state_directory_durable_only=True, cache_directory_disposable_only=True,
        runtime_directory_transient_only=True, explicit_log_directory_forbidden=True,
        journald_only=True, credential_copying_forbidden=True, api_key_persistence_forbidden=True,
        provider_response_persistence_forbidden=True, unrestricted_temporary_paths_forbidden=True,
        directory_policy_ready=True,
    )
    return SystemdSafeRuntimeLauncherDirectoryPolicyV1(**(values | overrides))


def _checklist(**overrides: object) -> SystemdSafeRuntimeLauncherChecklistV1:
    values = dict(
        checklist_id="launcher-checklist-v1", policy_id="launcher-policy-v1", launcher_id="launcher-identity-v1",
        path_binding_id="launcher-paths-v1", activation_gate_id="activation-gate-v1",
        credential_gate_id="credential-gate-v1", network_gate_id="network-gate-v1",
        workload_gate_id="workload-gate-v1", signal_policy_id="signal-policy-v1",
        shutdown_policy_id="shutdown-policy-v1", logging_policy_id="logging-policy-v1",
        directory_policy_id="directory-policy-v1", canonical_service_identity_confirmed=True,
        service_user_group_confirmed=True, installation_working_paths_confirmed=True,
        interpreter_path_confirmed=True, passive_default_confirmed=True,
        manual_entrypoint_rejected_for_systemd=True, credential_gate_closed=True,
        network_gate_closed=True, workload_gate_closed=True, activation_gate_closed=True,
        no_environment_file_sourcing=True, no_implicit_credentials=True, no_implicit_network=True,
        no_automatic_provider_retry=True, writable_path_policy_complete=True,
        signal_handling_complete=True, graceful_shutdown_complete=True,
        journald_logging_complete=True, redaction_complete=True,
        implementation_unauthorized=True, installation_unauthorized=True,
        runtime_activation_unauthorized=True, operator_attestation_complete=True,
        reviewer_approval_complete=True, evidence_fresh=True, checklist_complete=True,
    )
    return SystemdSafeRuntimeLauncherChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> SystemdSafeRuntimeLauncherOperatorAttestationV1:
    values = dict(
        attestation_id="launcher-attestation-v1", policy_id="launcher-policy-v1",
        launcher_id="launcher-identity-v1", checklist_id="launcher-checklist-v1",
        operator_id="operator-a", operator_role="SYSTEMD_RUNTIME_DESIGN_OPERATOR",
        attested_at=_NOW - timedelta(minutes=2), expires_at=_NOW + timedelta(minutes=30),
        redacted_metadata_only=True, passive_design_confirmed=True, no_implementation_performed=True,
        no_credential_accessed=True, no_runtime_executed=True, no_sensitive_material_retained=True,
        raw_exception_exposure_detected=False, attestation_complete=True,
    )
    return SystemdSafeRuntimeLauncherOperatorAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> SystemdSafeRuntimeLauncherIndependentReviewerApprovalV1:
    values = dict(
        approval_id="launcher-review-v1", policy_id="launcher-policy-v1",
        launcher_id="launcher-identity-v1", checklist_id="launcher-checklist-v1",
        attestation_id="launcher-attestation-v1", reviewer_id="reviewer-b",
        reviewer_role="INDEPENDENT_SYSTEMD_RUNTIME_REVIEWER",
        approved_at=_NOW - timedelta(minutes=1), expires_at=_NOW + timedelta(minutes=30),
        redacted_evidence_only=True, passive_design_confirmed=True, design_approved=True,
        no_sensitive_material_retained=True, review_complete=True,
    )
    return SystemdSafeRuntimeLauncherIndependentReviewerApprovalV1(**(values | overrides))


def _evaluate(**overrides: object) -> SystemdSafeRuntimeLauncherDecisionV1:
    values = dict(
        policy=_policy(), identity=_identity(), paths=_paths(), activation_gate=_activation(),
        credential_gate=_credential(), network_gate=_network(), workload_gate=_workload(),
        signal_policy=_signal(), shutdown_policy=_shutdown(), logging_policy=_logging(),
        directory_policy=_directories(), checklist=_checklist(), operator_attestation=_operator(),
        reviewer_approval=_reviewer(), evaluated_at=_NOW,
    )
    return evaluate_systemd_safe_runtime_launcher_design_v1(**(values | overrides))


def _assert_authorities(record: object) -> None:
    assert record.launcher_design_authorized is True
    assert record.owner_secret_entry_authorized is True
    assert record.launcher_implementation_authorized is False
    assert record.service_unit_installation_authorized is False
    assert record.daemon_reload_authorized is False
    assert record.service_enablement_authorized is False
    assert record.service_start_restart_authorized is False
    assert record.credential_value_access_authorized is False
    assert record.credential_loading_authorized is False
    assert record.credential_validation_authorized is False
    assert record.network_authorized is False
    assert record.provider_transmission_authorized is False
    assert record.runtime_activation_authorized is False
    assert record.runtime_configuration_authorized is False
    assert record.publication_authorized is False
    assert record.fail_closed is True


def test_public_contract_is_immutable_metadata_only_and_has_no_secret_fields() -> None:
    records = (
        _policy(), _identity(), _paths(), _activation(), _credential(), _network(), _workload(),
        _signal(), _shutdown(), _logging(), _directories(), _checklist(), _operator(), _reviewer(),
    )
    for record in records:
        _frozen(record)
    for record_type in (SystemdSafeRuntimeLauncherFailureV1, SystemdSafeRuntimeLauncherDecisionV1,
                        SystemdSafeRuntimeLauncherAuditEvidenceV1):
        assert hasattr(record_type, "__dataclass_fields__")
    forbidden = ("raw_credential", "fingerprint", "secret_hash", "key_prefix", "key_suffix",
                 "authorization_header", "cookie", "account_identity", "provider_response")
    field_names = tuple(
        name.lower()
        for record in records
        for name in tuple(item.name for item in fields(record))
    )
    assert not any(token in name for name in field_names for token in forbidden)
    assert _credential().credential_names == ("deepseek_api_key", "anthropic_api_key")
    assert _credential().logical_credential_labels == ("DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY")
    assert _credential().routing_levels == (("L0",), ("L1", "L2"))
    assert _credential().exact_provider_model_ids == (
        ("deepseek-v4-pro",), ("claude-sonnet-5", "claude-opus-4-8"),
    )


def test_complete_passive_design_is_ready_only_for_separate_implementation_decision() -> None:
    decision = _evaluate()
    _frozen(decision)
    assert decision.ready is True
    assert decision.design_state == (
        "SYSTEMD_SAFE_RUNTIME_LAUNCHER_DESIGN_READY_FOR_SEPARATE_IMPLEMENTATION_DECISION"
    )
    assert decision.state_codes == (
        "PASSIVE_STARTUP", "CONFIGURATION_SHAPE_VALIDATED", "ACTIVATION_GATE_CLOSED",
        "CREDENTIAL_GATE_CLOSED", "NETWORK_GATE_CLOSED", "WORKLOAD_GATE_CLOSED",
        "READY_FOR_SEPARATE_ACTIVATION_DECISION",
    )
    assert decision.supported_state_codes == _STATES
    assert decision.failure_codes == ()
    _assert_authorities(decision)


@pytest.mark.parametrize(
    ("target", "override", "failure_code"),
    (
        ("policy", {"policy_id": ""}, "POLICY_ID_EMPTY"),
        ("policy", {"policy_version": ""}, "POLICY_VERSION_EMPTY"),
        ("policy", {"launcher_design_authorized": False}, "LAUNCHER_DESIGN_NOT_AUTHORIZED"),
        ("identity", {"expected_service_unit": "other.service"}, "SERVICE_UNIT_MISMATCH"),
        ("identity", {"expected_service_user": "other-user"}, "SERVICE_USER_MISMATCH"),
        ("identity", {"expected_service_group": "other-group"}, "SERVICE_GROUP_MISMATCH"),
        ("paths", {"installation_path": "/opt/other"}, "INSTALLATION_PATH_MISMATCH"),
        ("paths", {"working_directory": "/opt/other"}, "WORKING_DIRECTORY_MISMATCH"),
        ("paths", {"python_interpreter_path": "/opt/other/bin/python"}, "PYTHON_INTERPRETER_PATH_MISMATCH"),
        ("paths", {"state_directory": "/var/lib/other"}, "STATE_DIRECTORY_MISMATCH"),
        ("paths", {"cache_directory": "/var/cache/other"}, "CACHE_DIRECTORY_MISMATCH"),
        ("paths", {"runtime_directory": "/run/other"}, "RUNTIME_DIRECTORY_MISMATCH"),
        ("paths", {"log_destination": "FILE"}, "LOG_DESTINATION_MISMATCH"),
        ("paths", {"log_directory": "/var/log/other"}, "LOG_DIRECTORY_NOT_ALLOWED"),
        ("paths", {"working_directory": "relative"}, "RELATIVE_PATH_NOT_ALLOWED"),
        ("paths", {"installation_path": "/home/development"}, "DEVELOPMENT_HOME_PATH_NOT_ALLOWED"),
        ("identity", {"manual_entrypoint_allowed_for_systemd": True}, "MANUAL_ENTRYPOINT_NOT_ALLOWED_FOR_SYSTEMD"),
        ("identity", {"expected_execution_mode": "ACTIVE"}, "PASSIVE_DEFAULT_REQUIRED"),
        ("credential_gate", {"environment_file_sourcing_allowed": True}, "ENVIRONMENT_FILE_SOURCING_NOT_ALLOWED"),
        ("credential_gate", {"dotenv_sourcing_allowed": True}, "DOTENV_SOURCING_NOT_ALLOWED"),
        ("credential_gate", {"credential_gate_open": True}, "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
        ("credential_gate", {"credential_presence_claimed": True}, "CREDENTIAL_PRESENCE_NOT_ESTABLISHED"),
        ("credential_gate", {"shell_export_allowed": True}, "RAW_CREDENTIAL_EXPOSURE_DETECTED"),
        ("credential_gate", {"credential_argument_reference_detected": True}, "RAW_CREDENTIAL_EXPOSURE_DETECTED"),
        ("credential_gate", {"credential_value_access_authorized": True}, "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED"),
        ("credential_gate", {"credential_loading_authorized": True}, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ("credential_gate", {"credential_validation_authorized": True}, "CREDENTIAL_VALIDATION_NOT_AUTHORIZED"),
        ("network_gate", {"network_gate_open": True}, "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ("network_gate", {"dns_authorized": True}, "DNS_NOT_AUTHORIZED"),
        ("network_gate", {"socket_authorized": True}, "SOCKET_NOT_AUTHORIZED"),
        ("network_gate", {"tls_authorized": True}, "TLS_NOT_AUTHORIZED"),
        ("network_gate", {"proxy_authorized": True}, "PROXY_NOT_AUTHORIZED"),
        ("network_gate", {"provider_transmission_authorized": True}, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        ("workload_gate", {"workload_gate_open": True}, "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
        ("workload_gate", {"scanner_execution_authorized": True}, "SCANNER_EXECUTION_NOT_AUTHORIZED"),
        ("workload_gate", {"worker_start_authorized": True}, "WORKER_START_NOT_AUTHORIZED"),
        ("workload_gate", {"scheduler_start_authorized": True}, "SCHEDULER_START_NOT_AUTHORIZED"),
        ("workload_gate", {"telegram_start_authorized": True}, "TELEGRAM_START_NOT_AUTHORIZED"),
        ("workload_gate", {"database_mutation_authorized": True}, "DATABASE_MUTATION_NOT_AUTHORIZED"),
        ("workload_gate", {"artifact_publication_authorized": True}, "ARTIFACT_PUBLICATION_NOT_AUTHORIZED"),
        ("workload_gate", {"trading_authorized": True}, "TRADING_NOT_AUTHORIZED"),
        ("workload_gate", {"automatic_provider_retry_authorized": True}, "AUTOMATIC_PROVIDER_RETRY_NOT_AUTHORIZED"),
        ("signal_policy", {"signal_policy_ready": False}, "SIGNAL_POLICY_REQUIRED"),
        ("shutdown_policy", {"graceful_shutdown_required": False}, "GRACEFUL_SHUTDOWN_REQUIRED"),
        ("shutdown_policy", {"shutdown_timeout_seconds": 0}, "SHUTDOWN_TIMEOUT_REQUIRED"),
        ("directories", {"source_tree_read_only": False}, "SOURCE_TREE_MUST_BE_READ_ONLY"),
        ("paths", {"state_writes_restricted": False}, "WRITABLE_PATH_POLICY_REQUIRED"),
        ("directories", {"credential_copying_forbidden": False}, "CREDENTIAL_COPY_NOT_AUTHORIZED"),
        ("logging_policy", {"log_destination": "FILE"}, "JOURNALD_ONLY_LOGGING_REQUIRED"),
        ("logging_policy", {"api_key_values_forbidden": False}, "LOG_REDACTION_REQUIRED"),
        ("operator_attestation", {"operator_id": ""}, "OPERATOR_ATTESTATION_REQUIRED"),
        ("reviewer_approval", {"reviewer_id": ""}, "REVIEWER_APPROVAL_REQUIRED"),
        ("reviewer_approval", {"reviewer_id": "operator-a"}, "OPERATOR_REVIEWER_COLLISION"),
        ("operator_attestation", {"attested_at": _NOW + timedelta(seconds=1)}, "EVIDENCE_FROM_FUTURE"),
        ("operator_attestation", {"attested_at": _NOW - timedelta(hours=2)}, "EVIDENCE_STALE"),
        ("operator_attestation", {"expires_at": _NOW - timedelta(seconds=1)}, "EVIDENCE_EXPIRED"),
        ("identity", {"launcher_implementation_authorized": True}, "LAUNCHER_IMPLEMENTATION_NOT_AUTHORIZED"),
        ("activation_gate", {"service_installation_state": "AUTHORIZED"}, "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED"),
        ("activation_gate", {"readiness_evidence_identity": "DAEMON_RELOAD_AUTHORIZED"}, "DAEMON_RELOAD_NOT_AUTHORIZED"),
        ("activation_gate", {"credential_loading_state": "SERVICE_ENABLEMENT_AUTHORIZED"}, "SERVICE_ENABLEMENT_NOT_AUTHORIZED"),
        ("activation_gate", {"network_authority_state": "SERVICE_START_RESTART_AUTHORIZED"}, "SERVICE_START_RESTART_NOT_AUTHORIZED"),
        ("identity", {"runtime_activation_authorized": True}, "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ("activation_gate", {"runtime_authority_state": "RUNTIME_CONFIGURATION_AUTHORIZED"}, "RUNTIME_CONFIGURATION_NOT_AUTHORIZED"),
        ("activation_gate", {"publication_authority_state": "AUTHORIZED"}, "PUBLICATION_NOT_AUTHORIZED"),
        ("credential_gate", {"sensitive_material_declared": True}, "RAW_CREDENTIAL_EXPOSURE_DETECTED"),
        ("operator_attestation", {"raw_exception_exposure_detected": True}, "RAW_EXCEPTION_EXPOSURE_DETECTED"),
    ),
)
def test_every_fail_closed_rejection_returns_immutable_redacted_evidence(
    target: str, override: dict[str, object], failure_code: str,
) -> None:
    factory = {
        "policy": _policy, "identity": _identity, "paths": _paths, "activation_gate": _activation,
        "credential_gate": _credential, "network_gate": _network, "workload_gate": _workload,
        "signal_policy": _signal, "shutdown_policy": _shutdown, "logging_policy": _logging,
        "directories": _directories, "operator_attestation": _operator, "reviewer_approval": _reviewer,
    }[target]
    decision = _evaluate(**{target: factory(**override)})
    _frozen(decision)
    assert decision.ready is False
    assert decision.design_state == "LAUNCHER_BLOCKED"
    assert failure_code in decision.failure_codes
    assert tuple(item.failure_code for item in decision.failures) == decision.failure_codes
    assert tuple(sorted(decision.failure_codes, key=_FAILURES.index)) == decision.failure_codes
    _assert_authorities(decision)


def test_complete_canonical_failure_surface_has_stable_ordering_and_safe_messages() -> None:
    decision = _evaluate(
        policy=_policy(policy_id="", policy_version="", launcher_design_authorized=False),
        identity=_identity(expected_service_unit="other.service", expected_service_user="other-user",
                           expected_service_group="other-group", expected_execution_mode="ACTIVE",
                           manual_entrypoint_allowed_for_systemd=True, launcher_implementation_authorized=True,
                           runtime_activation_authorized=True),
        paths=_paths(installation_path="/home/development", working_directory="relative",
                     python_interpreter_path="relative", state_directory="/var/lib/other",
                     cache_directory="/var/cache/other", runtime_directory="/run/other", log_destination="FILE",
                     log_directory="/var/log/other", state_writes_restricted=False),
        activation_gate=_activation(activation_gate_open=True, service_installation_state="AUTHORIZED",
                                    readiness_evidence_identity="DAEMON_RELOAD_AUTHORIZED",
                                    credential_loading_state="SERVICE_ENABLEMENT_AUTHORIZED",
                                    network_authority_state="SERVICE_START_RESTART_AUTHORIZED",
                                    runtime_authority_state="RUNTIME_CONFIGURATION_AUTHORIZED",
                                    publication_authority_state="AUTHORIZED"),
        credential_gate=_credential(environment_file_sourcing_allowed=True, dotenv_sourcing_allowed=True,
                                    credential_gate_open=True, credential_presence_claimed=True,
                                    shell_export_allowed=True, credential_argument_reference_detected=True,
                                    credential_value_access_authorized=True, credential_loading_authorized=True,
                                    credential_validation_authorized=True, sensitive_material_declared=True),
        network_gate=_network(network_gate_open=True, dns_authorized=True, socket_authorized=True,
                              tls_authorized=True, proxy_authorized=True, provider_transmission_authorized=True),
        workload_gate=_workload(workload_gate_open=True, scanner_execution_authorized=True,
                                worker_start_authorized=True, scheduler_start_authorized=True,
                                telegram_start_authorized=True, database_mutation_authorized=True,
                                artifact_publication_authorized=True, trading_authorized=True,
                                automatic_provider_retry_authorized=True),
        signal_policy=_signal(signal_policy_ready=False),
        shutdown_policy=_shutdown(graceful_shutdown_required=False, shutdown_timeout_seconds=0),
        logging_policy=_logging(log_destination="FILE", api_key_values_forbidden=False),
        directories=_directories(source_tree_read_only=False, credential_copying_forbidden=False),
        operator_attestation=_operator(operator_id="", attested_at=_NOW + timedelta(seconds=1),
                                       expires_at=_NOW - timedelta(seconds=1), raw_exception_exposure_detected=True),
        reviewer_approval=_reviewer(reviewer_id="operator-a"),
    )
    assert decision.ready is False
    assert decision.failure_codes == _FAILURES
    assert all(item.safe_message and "\n" not in item.safe_message for item in decision.failures)
    assert all(item.retryable is False for item in decision.failures)
    _assert_authorities(decision)


def test_audit_evidence_is_pure_redacted_immutable_and_authority_preserving() -> None:
    decision = _evaluate()
    evidence = build_systemd_safe_runtime_launcher_design_audit_evidence_v1(
        evidence_id="launcher-audit-v1", policy=_policy(), identity=_identity(), paths=_paths(),
        activation_gate=_activation(), credential_gate=_credential(), network_gate=_network(),
        workload_gate=_workload(), signal_policy=_signal(), shutdown_policy=_shutdown(),
        logging_policy=_logging(), directory_policy=_directories(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), decision=decision,
        built_at=_NOW,
    )
    _frozen(evidence)
    assert evidence.evidence_id == "launcher-audit-v1"
    assert evidence.credential_names == ("deepseek_api_key", "anthropic_api_key")
    assert evidence.failure_codes == ()
    assert evidence.state_codes == decision.state_codes
    _assert_authorities(evidence)


def test_red_contract_declares_every_required_public_symbol_and_caller_supplied_time() -> None:
    assert tuple(item.name for item in fields(SystemdSafeRuntimeLauncherFailureV1)) == (
        "failure_code", "safe_message", "retryable",
    )
    assert "evaluated_at" not in tuple(item.name for item in fields(SystemdSafeRuntimeLauncherDecisionV1))
    assert "built_at" not in tuple(item.name for item in fields(SystemdSafeRuntimeLauncherAuditEvidenceV1))
    assert _NOW.tzinfo is UTC
