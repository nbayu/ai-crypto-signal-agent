"""RED contract for a canonical production systemd service-unit design only."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from engine.phase_12_canonical_production_systemd_service_unit_design_contract_v1 import (
    ProductionSystemdCredentialBindingV1,
    ProductionSystemdDeploymentChecklistV1,
    ProductionSystemdDesignAuditEvidenceV1,
    ProductionSystemdDesignDecisionV1,
    ProductionSystemdDesignFailureV1,
    ProductionSystemdExecutionIdentityV1,
    ProductionSystemdHardeningProfileV1,
    ProductionSystemdIndependentReviewerApprovalV1,
    ProductionSystemdLifecyclePolicyV1,
    ProductionSystemdLoggingPolicyV1,
    ProductionSystemdOperatorAttestationV1,
    ProductionSystemdRuntimeBindingV1,
    ProductionSystemdServiceIdentityV1,
    ProductionSystemdServiceUnitPolicyV1,
    build_production_systemd_service_unit_design_audit_evidence_v1,
    evaluate_production_systemd_service_unit_design_v1,
)


_NOW = datetime(2030, 1, 9, 12, 0, tzinfo=UTC)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "canonical_unit_name", "manager_scope", "deployment_state",
    "expected_branch", "expected_locked_commit", "require_encrypted_credentials",
    "require_dedicated_non_root_identity", "require_hardening_profile", "require_logging_policy",
    "require_lifecycle_policy", "require_independent_review", "evidence_max_age_seconds", "fail_closed",
)
_SERVICE_FIELDS = (
    "unit_identity", "unit_name", "manager_scope", "deployment_state", "unit_type",
    "description_classification", "documentation_classification", "after_targets", "wants_targets",
    "restart_policy", "restart_delay_seconds", "start_limit_interval_seconds", "start_limit_burst",
    "timeout_start_seconds", "timeout_stop_seconds", "kill_signal", "final_kill_signal",
    "send_sigkill", "success_exit_statuses", "service_installation_authorized",
    "daemon_reload_authorized", "service_enablement_authorized", "service_start_restart_authorized",
)
_EXECUTION_FIELDS = (
    "execution_identity_id", "service_user", "service_group", "dynamic_user", "supplementary_groups",
    "umask", "working_directory", "executable_path", "runtime_entrypoint", "runtime_arguments",
    "environment_classification", "state_directory_classification", "cache_directory_classification",
    "logs_directory_classification", "runtime_directory_classification", "read_write_paths",
    "read_only_paths", "inaccessible_paths", "interactive_terminal_required",
    "login_shell_required", "privilege_escalation_required", "execution_identity_ready",
)
_RUNTIME_FIELDS = (
    "runtime_binding_id", "repository_root", "working_directory", "python_interpreter_path",
    "module_or_entrypoint", "runtime_arguments", "phase_12_runtime_boundary_identity",
    "production_signal_service_boundary_identity", "controlled_production_design_identity",
    "expected_branch", "expected_locked_commit", "startup_mode", "shutdown_mode",
    "deterministic_startup_required", "graceful_shutdown_required", "no_automatic_provider_retry",
    "no_implicit_network_activation", "no_implicit_credential_loading", "runtime_binding_ready",
)
_CREDENTIAL_FIELDS = (
    "credential_binding_id", "provider_id", "logical_credential_label", "systemd_credential_name",
    "credential_file_runtime_name", "expected_runtime_directory", "routing_levels",
    "exact_provider_model_ids", "load_directive", "environment_secret_loading",
    "environment_file_secret_loading", "shell_expansion_of_secret", "argument_secret_material",
    "credential_loading_authorized", "binding_ready",
)
_HARDENING_FIELDS = (
    "hardening_profile_id", "no_new_privileges", "private_tmp", "private_devices", "protect_system",
    "protect_home", "protect_kernel_tunables", "protect_kernel_modules", "protect_kernel_logs",
    "protect_control_groups", "restrict_suid_sgid", "restrict_realtime", "lock_personality",
    "memory_deny_write_execute", "remove_ipc", "system_call_architectures", "restrict_namespaces",
    "capability_bounding_set", "ambient_capabilities", "umask", "proc_subset", "protect_proc",
    "device_policy", "ip_address_deny", "restrict_address_families", "read_write_paths",
    "read_only_paths", "inaccessible_paths", "relaxed_directives", "relaxation_justifications",
    "hardening_profile_ready",
)
_LIFECYCLE_FIELDS = (
    "lifecycle_policy_id", "installation_procedure_defined", "rollback_procedure_defined",
    "uninstall_procedure_defined", "daemon_reload_procedure_defined", "enablement_procedure_defined",
    "start_procedure_defined", "stop_procedure_defined", "restart_procedure_defined",
    "failure_recovery_procedure_defined", "credential_rotation_coordination_defined",
    "credential_revocation_coordination_defined", "pre_start_verification_required",
    "post_start_verification_required", "deployment_lock_required",
    "operator_reviewer_separation_required", "installation_authorized", "daemon_reload_authorized",
    "enablement_authorized", "start_restart_authorized", "lifecycle_policy_ready",
)
_LOGGING_FIELDS = (
    "logging_policy_id", "journald_classification", "stdout_policy", "stderr_policy", "log_level_policy",
    "redaction_required", "api_key_redaction_required", "authorization_header_redaction_required",
    "provider_response_redaction_required", "billing_data_redaction_required",
    "exception_sanitization_required", "stack_trace_policy", "retention_classification",
    "rate_limit_classification", "secret_derived_identifiers_forbidden",
    "credential_paths_forbidden", "environment_dumps_forbidden", "logging_policy_ready",
)
_CHECKLIST_FIELDS = (
    "checklist_id", "policy_id", "unit_identity", "execution_identity_id", "runtime_binding_id",
    "credential_binding_ids", "hardening_profile_id", "lifecycle_policy_id", "logging_policy_id",
    "canonical_unit_identity_confirmed", "manager_scope_confirmed", "deployment_state_confirmed",
    "execution_user_resolved", "execution_group_resolved", "executable_path_resolved",
    "working_directory_resolved", "runtime_entrypoint_resolved", "locked_commit_confirmed",
    "encrypted_credential_binding_defined", "credential_loading_unauthorized",
    "service_installation_unauthorized", "daemon_reload_unauthorized", "enablement_unauthorized",
    "start_restart_unauthorized", "provider_validation_unauthorized", "network_activation_unauthorized",
    "provider_transmission_unauthorized", "runtime_activation_unauthorized", "publication_unauthorized",
    "hardening_profile_complete", "lifecycle_procedures_complete", "logging_policy_complete",
    "rollback_complete", "operator_attestation_complete", "independent_review_complete",
    "evidence_fresh", "checklist_complete", "prohibited_authority_claimed",
)
_OPERATOR_FIELDS = (
    "attestation_id", "policy_id", "unit_identity", "checklist_id", "operator_id", "operator_role",
    "attested_at", "redacted_metadata_only", "installation_not_performed", "credentials_not_accessed",
    "attestation_complete",
)
_REVIEWER_FIELDS = (
    "approval_id", "policy_id", "unit_identity", "checklist_id", "attestation_id", "reviewer_id",
    "reviewer_role", "approved_at", "independent_review_complete", "redacted_evidence_only",
    "design_approved", "review_complete",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_DECISION_FIELDS = (
    "policy_id", "unit_name", "manager_scope", "deployment_state", "ready", "design_state",
    "state_codes", "supported_state_codes", "failure_codes", "failures", "service_unit_design_authorized",
    "service_unit_installation_authorized", "daemon_reload_authorized", "service_enablement_authorized",
    "service_start_restart_authorized", "owner_secret_entry_authorized",
    "credential_value_access_authorized", "credential_loading_authorized",
    "credential_validation_authorized", "network_authorized", "provider_transmission_authorized",
    "runtime_activation_authorized", "runtime_configuration_authorized", "publication_authorized", "fail_closed",
)
_AUDIT_FIELDS = (
    "evidence_id", "policy_id", "unit_name", "manager_scope", "deployment_state",
    "execution_identity_id", "runtime_binding_id", "credential_binding_ids", "hardening_profile_id",
    "lifecycle_policy_id", "logging_policy_id", "identity_resolution_state", "locked_commit_confirmed",
    "encrypted_credentials_defined", "hardening_ready", "lifecycle_ready", "logging_ready",
    "operator_id", "operator_role", "reviewer_id", "reviewer_role", "evidence_freshness",
    "failure_codes", "service_unit_design_authorized", "service_unit_installation_authorized",
    "daemon_reload_authorized", "service_enablement_authorized", "service_start_restart_authorized",
    "owner_secret_entry_authorized", "credential_value_access_authorized",
    "credential_loading_authorized", "credential_validation_authorized", "network_authorized",
    "provider_transmission_authorized", "runtime_activation_authorized",
    "runtime_configuration_authorized", "publication_authorized", "fail_closed",
)
_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "UNIT_NAME_MISMATCH", "MANAGER_SCOPE_MISMATCH",
    "DEPLOYMENT_STATE_MISMATCH", "SERVICE_USER_REQUIRED", "ROOT_SERVICE_USER_NOT_ALLOWED",
    "SERVICE_GROUP_REQUIRED", "ROOT_SERVICE_GROUP_NOT_ALLOWED", "EXECUTABLE_PATH_REQUIRED",
    "WORKING_DIRECTORY_REQUIRED", "RUNTIME_ENTRYPOINT_REQUIRED", "REPOSITORY_ROOT_MISMATCH",
    "LOCKED_COMMIT_MISMATCH", "RUNTIME_ARGUMENT_SECRET_EXPOSURE",
    "ENVIRONMENT_SECRET_LOADING_NOT_ALLOWED", "ENVIRONMENT_FILE_SECRET_LOADING_NOT_ALLOWED",
    "SYSTEMD_CREDENTIAL_BINDING_REQUIRED", "SYSTEMD_CREDENTIAL_NAME_MISMATCH",
    "SYSTEMD_CREDENTIAL_NAME_SHARED", "LOAD_CREDENTIAL_ENCRYPTED_REQUIRED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "AUTOMATIC_PROVIDER_RETRY_NOT_AUTHORIZED",
    "IMPLICIT_NETWORK_ACTIVATION_NOT_AUTHORIZED", "HARDENING_PROFILE_REQUIRED",
    "HARDENING_JUSTIFICATION_REQUIRED", "LOGGING_POLICY_REQUIRED", "LOG_REDACTION_REQUIRED",
    "LIFECYCLE_POLICY_REQUIRED", "ROLLBACK_PROCEDURE_REQUIRED", "OPERATOR_ATTESTATION_REQUIRED",
    "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE",
    "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED",
    "DAEMON_RELOAD_NOT_AUTHORIZED", "SERVICE_ENABLEMENT_NOT_AUTHORIZED",
    "SERVICE_START_RESTART_NOT_AUTHORIZED", "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED",
    "CREDENTIAL_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "RUNTIME_CONFIGURATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)
_STATES = (
    "CANONICAL_SERVICE_IDENTITY_DEFINED", "EXECUTION_IDENTITY_UNRESOLVED",
    "EXECUTION_IDENTITY_RESOLVED", "RUNTIME_BINDING_UNRESOLVED", "RUNTIME_BINDING_RESOLVED",
    "SYSTEMD_CREDENTIAL_BINDING_DEFINED", "SERVICE_UNIT_DESIGN_READY",
    "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED", "CREDENTIAL_PRESENT_BUT_NOT_LOADED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "DEPLOYMENT_BLOCKED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> ProductionSystemdServiceUnitPolicyV1:
    values = dict(
        policy_id="production-unit-policy-v1", policy_version="V1",
        canonical_unit_name="ai-crypto-signal-agent.service", manager_scope="SYSTEM",
        deployment_state="NOT_YET_INSTALLED", expected_branch="master",
        expected_locked_commit="a4071561b6acd5ab231cbcb4ea0e749195810ccb",
        require_encrypted_credentials=True, require_dedicated_non_root_identity=True,
        require_hardening_profile=True, require_logging_policy=True, require_lifecycle_policy=True,
        require_independent_review=True, evidence_max_age_seconds=3600, fail_closed=True,
    )
    return ProductionSystemdServiceUnitPolicyV1(**(values | overrides))


def _service(**overrides: object) -> ProductionSystemdServiceIdentityV1:
    values = dict(
        unit_identity="production-unit-v1", unit_name="ai-crypto-signal-agent.service", manager_scope="SYSTEM",
        deployment_state="NOT_YET_INSTALLED", unit_type="simple", description_classification="REDACTED",
        documentation_classification="REPOSITORY_DOCUMENTATION", after_targets=("network.target",),
        wants_targets=(), restart_policy="no", restart_delay_seconds=5, start_limit_interval_seconds=60,
        start_limit_burst=3, timeout_start_seconds=60, timeout_stop_seconds=30, kill_signal="SIGTERM",
        final_kill_signal="SIGKILL", send_sigkill=True, success_exit_statuses=("0",),
        service_installation_authorized=False, daemon_reload_authorized=False,
        service_enablement_authorized=False, service_start_restart_authorized=False,
    )
    return ProductionSystemdServiceIdentityV1(**(values | overrides))


def _execution(**overrides: object) -> ProductionSystemdExecutionIdentityV1:
    values = dict(
        execution_identity_id="execution-identity-v1", service_user="service-user", service_group="service-group",
        dynamic_user=False, supplementary_groups=(), umask="0077", working_directory="REPOSITORY_BOUND_PATH",
        executable_path="REPOSITORY_BOUND_ABSOLUTE_PATH", runtime_entrypoint="MODULE_ENTRYPOINT",
        runtime_arguments=("REDACTED_ARGUMENTS_ONLY",), environment_classification="NO_SECRET_ENVIRONMENT",
        state_directory_classification="SYSTEMD_MANAGED_STATE", cache_directory_classification="SYSTEMD_MANAGED_CACHE",
        logs_directory_classification="JOURNALD_ONLY", runtime_directory_classification="SYSTEMD_MANAGED_RUNTIME",
        read_write_paths=("SYSTEMD_MANAGED_STATE",), read_only_paths=("REPOSITORY_BOUND_PATH",),
        inaccessible_paths=("HOME",), interactive_terminal_required=False, login_shell_required=False,
        privilege_escalation_required=False, execution_identity_ready=True,
    )
    return ProductionSystemdExecutionIdentityV1(**(values | overrides))


def _runtime(**overrides: object) -> ProductionSystemdRuntimeBindingV1:
    values = dict(
        runtime_binding_id="runtime-binding-v1", repository_root="REPOSITORY_ROOT",
        working_directory="REPOSITORY_BOUND_PATH", python_interpreter_path="REPOSITORY_BOUND_ABSOLUTE_PATH",
        module_or_entrypoint="MODULE_ENTRYPOINT", runtime_arguments=("REDACTED_ARGUMENTS_ONLY",),
        phase_12_runtime_boundary_identity="phase-12-boundary-v1",
        production_signal_service_boundary_identity="production-signal-boundary-v1",
        controlled_production_design_identity="controlled-production-design-v1", expected_branch="master",
        expected_locked_commit="a4071561b6acd5ab231cbcb4ea0e749195810ccb", startup_mode="DETERMINISTIC",
        shutdown_mode="GRACEFUL", deterministic_startup_required=True, graceful_shutdown_required=True,
        no_automatic_provider_retry=True, no_implicit_network_activation=True,
        no_implicit_credential_loading=True, runtime_binding_ready=True,
    )
    return ProductionSystemdRuntimeBindingV1(**(values | overrides))


def _credential(**overrides: object) -> ProductionSystemdCredentialBindingV1:
    values = dict(
        credential_binding_id="deepseek-credential-binding-v1", provider_id="DEEPSEEK",
        logical_credential_label="DEEPSEEK_API_KEY", systemd_credential_name="deepseek_api_key",
        credential_file_runtime_name="deepseek_api_key", expected_runtime_directory="CREDENTIALS_DIRECTORY",
        routing_levels=("L0",), exact_provider_model_ids=("deepseek-v4-pro",),
        load_directive="LoadCredentialEncrypted", environment_secret_loading=False,
        environment_file_secret_loading=False, shell_expansion_of_secret=False,
        argument_secret_material=False, credential_loading_authorized=False, binding_ready=True,
    )
    return ProductionSystemdCredentialBindingV1(**(values | overrides))


def _hardening(**overrides: object) -> ProductionSystemdHardeningProfileV1:
    values = dict(
        hardening_profile_id="hardening-v1", no_new_privileges="REQUIRED", private_tmp="REQUIRED",
        private_devices="REQUIRED", protect_system="REQUIRED_WITH_JUSTIFICATION", protect_home="REQUIRED",
        protect_kernel_tunables="REQUIRED", protect_kernel_modules="REQUIRED", protect_kernel_logs="REQUIRED",
        protect_control_groups="REQUIRED", restrict_suid_sgid="REQUIRED", restrict_realtime="REQUIRED",
        lock_personality="REQUIRED", memory_deny_write_execute="REQUIRED_WITH_JUSTIFICATION", remove_ipc="REQUIRED",
        system_call_architectures="REQUIRED", restrict_namespaces="REQUIRED", capability_bounding_set="REQUIRED",
        ambient_capabilities="REQUIRED", umask="REQUIRED", proc_subset="REQUIRED", protect_proc="REQUIRED",
        device_policy="REQUIRED", ip_address_deny="REQUIRED", restrict_address_families="REQUIRED",
        read_write_paths="REQUIRED", read_only_paths="REQUIRED", inaccessible_paths="REQUIRED",
        relaxed_directives=("protect_system", "memory_deny_write_execute"),
        relaxation_justifications=("repository runtime access classified", "interpreter compatibility classified"),
        hardening_profile_ready=True,
    )
    return ProductionSystemdHardeningProfileV1(**(values | overrides))


def _lifecycle(**overrides: object) -> ProductionSystemdLifecyclePolicyV1:
    values = dict(
        lifecycle_policy_id="lifecycle-v1", installation_procedure_defined=True, rollback_procedure_defined=True,
        uninstall_procedure_defined=True, daemon_reload_procedure_defined=True, enablement_procedure_defined=True,
        start_procedure_defined=True, stop_procedure_defined=True, restart_procedure_defined=True,
        failure_recovery_procedure_defined=True, credential_rotation_coordination_defined=True,
        credential_revocation_coordination_defined=True, pre_start_verification_required=True,
        post_start_verification_required=True, deployment_lock_required=True,
        operator_reviewer_separation_required=True, installation_authorized=False,
        daemon_reload_authorized=False, enablement_authorized=False, start_restart_authorized=False,
        lifecycle_policy_ready=True,
    )
    return ProductionSystemdLifecyclePolicyV1(**(values | overrides))


def _logging(**overrides: object) -> ProductionSystemdLoggingPolicyV1:
    values = dict(
        logging_policy_id="logging-v1", journald_classification="REDACTED_METADATA", stdout_policy="REDACTED",
        stderr_policy="REDACTED", log_level_policy="CONTROLLED", redaction_required=True,
        api_key_redaction_required=True, authorization_header_redaction_required=True,
        provider_response_redaction_required=True, billing_data_redaction_required=True,
        exception_sanitization_required=True, stack_trace_policy="SANITIZED", retention_classification="CONTROLLED",
        rate_limit_classification="CONTROLLED", secret_derived_identifiers_forbidden=True,
        credential_paths_forbidden=True, environment_dumps_forbidden=True, logging_policy_ready=True,
    )
    return ProductionSystemdLoggingPolicyV1(**(values | overrides))


def _checklist(**overrides: object) -> ProductionSystemdDeploymentChecklistV1:
    values = dict(
        checklist_id="deployment-checklist-v1", policy_id="production-unit-policy-v1", unit_identity="production-unit-v1",
        execution_identity_id="execution-identity-v1", runtime_binding_id="runtime-binding-v1",
        credential_binding_ids=("deepseek-credential-binding-v1", "anthropic-credential-binding-v1"),
        hardening_profile_id="hardening-v1", lifecycle_policy_id="lifecycle-v1", logging_policy_id="logging-v1",
        canonical_unit_identity_confirmed=True, manager_scope_confirmed=True, deployment_state_confirmed=True,
        execution_user_resolved=True, execution_group_resolved=True, executable_path_resolved=True,
        working_directory_resolved=True, runtime_entrypoint_resolved=True, locked_commit_confirmed=True,
        encrypted_credential_binding_defined=True, credential_loading_unauthorized=True,
        service_installation_unauthorized=True, daemon_reload_unauthorized=True, enablement_unauthorized=True,
        start_restart_unauthorized=True, provider_validation_unauthorized=True, network_activation_unauthorized=True,
        provider_transmission_unauthorized=True, runtime_activation_unauthorized=True, publication_unauthorized=True,
        hardening_profile_complete=True, lifecycle_procedures_complete=True, logging_policy_complete=True,
        rollback_complete=True, operator_attestation_complete=True, independent_review_complete=True,
        evidence_fresh=True, checklist_complete=True, prohibited_authority_claimed=False,
    )
    return ProductionSystemdDeploymentChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> ProductionSystemdOperatorAttestationV1:
    values = dict(
        attestation_id="operator-attestation-v1", policy_id="production-unit-policy-v1", unit_identity="production-unit-v1",
        checklist_id="deployment-checklist-v1", operator_id="operator-1", operator_role="DESIGN_OPERATOR",
        attested_at=_NOW - timedelta(minutes=5), redacted_metadata_only=True, installation_not_performed=True,
        credentials_not_accessed=True, attestation_complete=True,
    )
    return ProductionSystemdOperatorAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> ProductionSystemdIndependentReviewerApprovalV1:
    values = dict(
        approval_id="reviewer-approval-v1", policy_id="production-unit-policy-v1", unit_identity="production-unit-v1",
        checklist_id="deployment-checklist-v1", attestation_id="operator-attestation-v1", reviewer_id="reviewer-1",
        reviewer_role="INDEPENDENT_SECURITY_REVIEWER", approved_at=_NOW - timedelta(minutes=4),
        independent_review_complete=True, redacted_evidence_only=True, design_approved=True, review_complete=True,
    )
    return ProductionSystemdIndependentReviewerApprovalV1(**(values | overrides))


def _decision(**overrides: object) -> ProductionSystemdDesignDecisionV1:
    return evaluate_production_systemd_service_unit_design_v1(
        policy=_policy(**overrides), service_identity=_service(), execution_identity=_execution(),
        runtime_binding=_runtime(), credential_bindings=(_credential(), _credential(
            credential_binding_id="anthropic-credential-binding-v1", provider_id="ANTHROPIC",
            logical_credential_label="ANTHROPIC_API_KEY", systemd_credential_name="anthropic_api_key",
            credential_file_runtime_name="anthropic_api_key", routing_levels=("L1", "L2"),
            exact_provider_model_ids=("claude-sonnet-5", "claude-opus-4-8"),
        )), hardening_profile=_hardening(), lifecycle_policy=_lifecycle(), logging_policy=_logging(),
        checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )


def test_public_contract_records_are_immutable_and_exact() -> None:
    expected = (
        (ProductionSystemdServiceUnitPolicyV1, _POLICY_FIELDS),
        (ProductionSystemdServiceIdentityV1, _SERVICE_FIELDS),
        (ProductionSystemdExecutionIdentityV1, _EXECUTION_FIELDS),
        (ProductionSystemdRuntimeBindingV1, _RUNTIME_FIELDS),
        (ProductionSystemdCredentialBindingV1, _CREDENTIAL_FIELDS),
        (ProductionSystemdHardeningProfileV1, _HARDENING_FIELDS),
        (ProductionSystemdLifecyclePolicyV1, _LIFECYCLE_FIELDS),
        (ProductionSystemdLoggingPolicyV1, _LOGGING_FIELDS),
        (ProductionSystemdDeploymentChecklistV1, _CHECKLIST_FIELDS),
        (ProductionSystemdOperatorAttestationV1, _OPERATOR_FIELDS),
        (ProductionSystemdIndependentReviewerApprovalV1, _REVIEWER_FIELDS),
        (ProductionSystemdDesignFailureV1, _FAILURE_FIELDS),
        (ProductionSystemdDesignDecisionV1, _DECISION_FIELDS),
        (ProductionSystemdDesignAuditEvidenceV1, _AUDIT_FIELDS),
    )
    assert all(tuple(field.name for field in fields(record_type)) == names for record_type, names in expected)
    for record in (_policy(), _service(), _execution(), _runtime(), _credential(), _hardening(), _lifecycle(), _logging(), _checklist(), _operator(), _reviewer(), _decision()):
        _frozen(record)


def test_canonical_identity_and_exact_encrypted_bindings_are_frozen() -> None:
    assert (_service().unit_name, _service().manager_scope, _service().deployment_state) == (
        "ai-crypto-signal-agent.service", "SYSTEM", "NOT_YET_INSTALLED",
    )
    bindings = _decision().credential_binding_ids if hasattr(_decision(), "credential_binding_ids") else _checklist().credential_binding_ids
    assert bindings == ("deepseek-credential-binding-v1", "anthropic-credential-binding-v1")
    assert _credential().systemd_credential_name == "deepseek_api_key"
    assert _credential().load_directive == "LoadCredentialEncrypted"


def test_ready_design_preserves_all_execution_authority_boundaries() -> None:
    decision = _decision()
    assert decision.ready is True
    assert decision.design_state == "SERVICE_UNIT_DESIGN_READY"
    assert decision.supported_state_codes == _STATES
    assert decision.service_unit_design_authorized is True
    assert decision.owner_secret_entry_authorized is True
    assert not any((
        decision.service_unit_installation_authorized, decision.daemon_reload_authorized,
        decision.service_enablement_authorized, decision.service_start_restart_authorized,
        decision.credential_value_access_authorized, decision.credential_loading_authorized,
        decision.credential_validation_authorized, decision.network_authorized,
        decision.provider_transmission_authorized, decision.runtime_activation_authorized,
        decision.runtime_configuration_authorized, decision.publication_authorized,
    ))
    assert decision.fail_closed is True


@pytest.mark.parametrize(
    ("service_change", "execution_change", "runtime_change", "failure_code"),
    (
        ({"unit_name": "other.service"}, {}, {}, "UNIT_NAME_MISMATCH"),
        ({"manager_scope": "USER"}, {}, {}, "MANAGER_SCOPE_MISMATCH"),
        ({"deployment_state": "INSTALLED"}, {}, {}, "DEPLOYMENT_STATE_MISMATCH"),
        ({}, {"service_user": ""}, {}, "SERVICE_USER_REQUIRED"),
        ({}, {"service_user": "root"}, {}, "ROOT_SERVICE_USER_NOT_ALLOWED"),
        ({}, {"service_group": ""}, {}, "SERVICE_GROUP_REQUIRED"),
        ({}, {"service_group": "root"}, {}, "ROOT_SERVICE_GROUP_NOT_ALLOWED"),
        ({}, {"executable_path": ""}, {}, "EXECUTABLE_PATH_REQUIRED"),
        ({}, {"working_directory": ""}, {}, "WORKING_DIRECTORY_REQUIRED"),
        ({}, {"runtime_entrypoint": ""}, {}, "RUNTIME_ENTRYPOINT_REQUIRED"),
        ({}, {}, {"repository_root": "OTHER_ROOT"}, "REPOSITORY_ROOT_MISMATCH"),
        ({}, {}, {"expected_locked_commit": "OTHER_COMMIT"}, "LOCKED_COMMIT_MISMATCH"),
    ),
)
def test_identity_and_runtime_resolution_failures_are_closed(
    service_change: dict[str, object], execution_change: dict[str, object], runtime_change: dict[str, object], failure_code: str,
) -> None:
    decision = evaluate_production_systemd_service_unit_design_v1(
        policy=_policy(), service_identity=_service(**service_change), execution_identity=_execution(**execution_change),
        runtime_binding=_runtime(**runtime_change), credential_bindings=(_credential(),), hardening_profile=_hardening(),
        lifecycle_policy=_lifecycle(), logging_policy=_logging(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)


@pytest.mark.parametrize(
    ("credential_change", "runtime_change", "failure_code"),
    (
        ({"argument_secret_material": True}, {}, "RUNTIME_ARGUMENT_SECRET_EXPOSURE"),
        ({"environment_secret_loading": True}, {}, "ENVIRONMENT_SECRET_LOADING_NOT_ALLOWED"),
        ({"environment_file_secret_loading": True}, {}, "ENVIRONMENT_FILE_SECRET_LOADING_NOT_ALLOWED"),
        ({"systemd_credential_name": "other_name"}, {}, "SYSTEMD_CREDENTIAL_NAME_MISMATCH"),
        ({"load_directive": "LoadCredential"}, {}, "LOAD_CREDENTIAL_ENCRYPTED_REQUIRED"),
        ({"credential_loading_authorized": True}, {}, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ({}, {"no_automatic_provider_retry": False}, "AUTOMATIC_PROVIDER_RETRY_NOT_AUTHORIZED"),
        ({}, {"no_implicit_network_activation": False}, "IMPLICIT_NETWORK_ACTIVATION_NOT_AUTHORIZED"),
    ),
)
def test_credential_and_runtime_activation_boundaries_fail_closed(
    credential_change: dict[str, object], runtime_change: dict[str, object], failure_code: str,
) -> None:
    decision = evaluate_production_systemd_service_unit_design_v1(
        policy=_policy(), service_identity=_service(), execution_identity=_execution(), runtime_binding=_runtime(**runtime_change),
        credential_bindings=(_credential(**credential_change),), hardening_profile=_hardening(), lifecycle_policy=_lifecycle(),
        logging_policy=_logging(), checklist=_checklist(), operator_attestation=_operator(),
        reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)


@pytest.mark.parametrize(
    ("hardening_change", "logging_change", "lifecycle_change", "failure_code"),
    (
        ({"hardening_profile_ready": False}, {}, {}, "HARDENING_PROFILE_REQUIRED"),
        ({"relaxation_justifications": ("",)}, {}, {}, "HARDENING_JUSTIFICATION_REQUIRED"),
        ({}, {"logging_policy_ready": False}, {}, "LOGGING_POLICY_REQUIRED"),
        ({}, {"redaction_required": False}, {}, "LOG_REDACTION_REQUIRED"),
        ({}, {}, {"lifecycle_policy_ready": False}, "LIFECYCLE_POLICY_REQUIRED"),
        ({}, {}, {"rollback_procedure_defined": False}, "ROLLBACK_PROCEDURE_REQUIRED"),
    ),
)
def test_hardening_logging_and_lifecycle_failures_are_closed(
    hardening_change: dict[str, object], logging_change: dict[str, object], lifecycle_change: dict[str, object], failure_code: str,
) -> None:
    decision = evaluate_production_systemd_service_unit_design_v1(
        policy=_policy(), service_identity=_service(), execution_identity=_execution(), runtime_binding=_runtime(),
        credential_bindings=(_credential(),), hardening_profile=_hardening(**hardening_change),
        lifecycle_policy=_lifecycle(**lifecycle_change), logging_policy=_logging(**logging_change),
        checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)


@pytest.mark.parametrize(
    ("operator", "reviewer", "at", "failure_code"),
    (
        (None, _reviewer(), _NOW, "OPERATOR_ATTESTATION_REQUIRED"),
        (_operator(), None, _NOW, "REVIEWER_APPROVAL_REQUIRED"),
        (_operator(operator_id="reviewer-1"), _reviewer(), _NOW, "OPERATOR_REVIEWER_COLLISION"),
        (_operator(attested_at=_NOW + timedelta(seconds=1)), _reviewer(), _NOW, "EVIDENCE_FROM_FUTURE"),
        (_operator(attested_at=_NOW - timedelta(seconds=3601)), _reviewer(), _NOW, "EVIDENCE_STALE"),
        (_operator(), _reviewer(approved_at=_NOW - timedelta(seconds=3601)), _NOW, "EVIDENCE_EXPIRED"),
    ),
)
def test_evidence_is_required_independent_and_fresh(
    operator: ProductionSystemdOperatorAttestationV1 | None,
    reviewer: ProductionSystemdIndependentReviewerApprovalV1 | None,
    at: datetime,
    failure_code: str,
) -> None:
    decision = evaluate_production_systemd_service_unit_design_v1(
        policy=_policy(), service_identity=_service(), execution_identity=_execution(), runtime_binding=_runtime(),
        credential_bindings=(_credential(),), hardening_profile=_hardening(), lifecycle_policy=_lifecycle(),
        logging_policy=_logging(), checklist=_checklist(), operator_attestation=operator,
        reviewer_approval=reviewer, evaluation_at=at,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)


@pytest.mark.parametrize(
    ("service_change", "lifecycle_change", "checklist_change", "failure_code"),
    (
        ({"service_installation_authorized": True}, {}, {}, "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED"),
        ({"daemon_reload_authorized": True}, {}, {}, "DAEMON_RELOAD_NOT_AUTHORIZED"),
        ({"service_enablement_authorized": True}, {}, {}, "SERVICE_ENABLEMENT_NOT_AUTHORIZED"),
        ({"service_start_restart_authorized": True}, {}, {}, "SERVICE_START_RESTART_NOT_AUTHORIZED"),
        ({}, {"installation_authorized": True}, {}, "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED"),
        ({}, {}, {"prohibited_authority_claimed": True}, "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED"),
    ),
)
def test_all_execution_authority_claims_fail_closed(
    service_change: dict[str, object], lifecycle_change: dict[str, object], checklist_change: dict[str, object], failure_code: str,
) -> None:
    decision = evaluate_production_systemd_service_unit_design_v1(
        policy=_policy(), service_identity=_service(**service_change), execution_identity=_execution(), runtime_binding=_runtime(),
        credential_bindings=(_credential(),), hardening_profile=_hardening(), lifecycle_policy=_lifecycle(**lifecycle_change),
        logging_policy=_logging(), checklist=_checklist(**checklist_change), operator_attestation=_operator(),
        reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)


def test_audit_evidence_is_redacted_immutable_and_pure() -> None:
    evidence = build_production_systemd_service_unit_design_audit_evidence_v1(
        evidence_id="design-evidence-v1", decision=_decision(), policy=_policy(), service_identity=_service(),
        execution_identity=_execution(), runtime_binding=_runtime(), credential_bindings=(_credential(),),
        hardening_profile=_hardening(), lifecycle_policy=_lifecycle(), logging_policy=_logging(),
        checklist=_checklist(), operator_attestation=_operator(), reviewer_approval=_reviewer(), evidence_at=_NOW,
    )
    _frozen(evidence)
    assert evidence.unit_name == "ai-crypto-signal-agent.service"
    assert evidence.encrypted_credentials_defined is True
    assert evidence.evidence_freshness == "FRESH"
    assert evidence.failure_codes == ()
    assert evidence.service_unit_design_authorized is True
    assert evidence.owner_secret_entry_authorized is True
    assert not any((
        evidence.service_unit_installation_authorized, evidence.daemon_reload_authorized,
        evidence.service_enablement_authorized, evidence.service_start_restart_authorized,
        evidence.credential_value_access_authorized, evidence.credential_loading_authorized,
        evidence.credential_validation_authorized, evidence.network_authorized,
        evidence.provider_transmission_authorized, evidence.runtime_activation_authorized,
        evidence.runtime_configuration_authorized, evidence.publication_authorized,
    ))


def test_canonical_failure_and_state_vocabulary_is_frozen() -> None:
    assert _FAILURES[0] == "POLICY_ID_EMPTY"
    assert _FAILURES[-1] == "RAW_EXCEPTION_EXPOSURE_DETECTED"
    assert len(_FAILURES) == 49
    assert _STATES == (
        "CANONICAL_SERVICE_IDENTITY_DEFINED", "EXECUTION_IDENTITY_UNRESOLVED",
        "EXECUTION_IDENTITY_RESOLVED", "RUNTIME_BINDING_UNRESOLVED", "RUNTIME_BINDING_RESOLVED",
        "SYSTEMD_CREDENTIAL_BINDING_DEFINED", "SERVICE_UNIT_DESIGN_READY",
        "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED", "CREDENTIAL_PRESENT_BUT_NOT_LOADED",
        "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "DEPLOYMENT_BLOCKED",
    )
