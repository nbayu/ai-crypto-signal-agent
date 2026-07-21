"""Pure metadata-only canonical production systemd service-unit design boundary."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


_UNIT_NAME = "ai-crypto-signal-agent.service"
_LOCKED_COMMIT = "1f79783c5fe40dc01c6fa6162dbc961ece23c098"
_BINDINGS = (
    ("DEEPSEEK", "DEEPSEEK_API_KEY", "deepseek_api_key", ("L0",), ("deepseek-v4-pro",)),
    ("ANTHROPIC", "ANTHROPIC_API_KEY", "anthropic_api_key", ("L1", "L2"),
     ("claude-sonnet-5", "claude-opus-4-8")),
)
_STATES = (
    "CANONICAL_SERVICE_IDENTITY_DEFINED", "EXECUTION_IDENTITY_UNRESOLVED",
    "EXECUTION_IDENTITY_RESOLVED", "RUNTIME_BINDING_UNRESOLVED", "RUNTIME_BINDING_RESOLVED",
    "SYSTEMD_CREDENTIAL_BINDING_DEFINED", "SERVICE_UNIT_DESIGN_READY",
    "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED", "CREDENTIAL_PRESENT_BUT_NOT_LOADED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "DEPLOYMENT_BLOCKED",
)
_ORDER = (
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
_MESSAGES = {code: "redacted metadata requirement not satisfied" for code in _ORDER}


@dataclass(frozen=True, slots=True)
class ProductionSystemdServiceUnitPolicyV1:
    policy_id: str; policy_version: str; canonical_unit_name: str; manager_scope: str; deployment_state: str
    expected_branch: str; expected_locked_commit: str; require_encrypted_credentials: bool
    require_dedicated_non_root_identity: bool; require_hardening_profile: bool; require_logging_policy: bool
    require_lifecycle_policy: bool; require_independent_review: bool; evidence_max_age_seconds: int; fail_closed: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdServiceIdentityV1:
    unit_identity: str; unit_name: str; manager_scope: str; deployment_state: str; unit_type: str
    description_classification: str; documentation_classification: str; after_targets: tuple[str, ...]; wants_targets: tuple[str, ...]
    restart_policy: str; restart_delay_seconds: int; start_limit_interval_seconds: int; start_limit_burst: int
    timeout_start_seconds: int; timeout_stop_seconds: int; kill_signal: str; final_kill_signal: str
    send_sigkill: bool; success_exit_statuses: tuple[str, ...]; service_installation_authorized: bool
    daemon_reload_authorized: bool; service_enablement_authorized: bool; service_start_restart_authorized: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdExecutionIdentityV1:
    execution_identity_id: str; service_user: str; service_group: str; dynamic_user: bool; supplementary_groups: tuple[str, ...]
    umask: str; working_directory: str; executable_path: str; runtime_entrypoint: str; runtime_arguments: tuple[str, ...]
    environment_classification: str; state_directory_classification: str; cache_directory_classification: str
    logs_directory_classification: str; runtime_directory_classification: str; read_write_paths: tuple[str, ...]
    read_only_paths: tuple[str, ...]; inaccessible_paths: tuple[str, ...]; interactive_terminal_required: bool
    login_shell_required: bool; privilege_escalation_required: bool; execution_identity_ready: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdRuntimeBindingV1:
    runtime_binding_id: str; repository_root: str; working_directory: str; python_interpreter_path: str
    module_or_entrypoint: str; runtime_arguments: tuple[str, ...]; phase_12_runtime_boundary_identity: str
    production_signal_service_boundary_identity: str; controlled_production_design_identity: str
    expected_branch: str; expected_locked_commit: str; startup_mode: str; shutdown_mode: str
    deterministic_startup_required: bool; graceful_shutdown_required: bool; no_automatic_provider_retry: bool
    no_implicit_network_activation: bool; no_implicit_credential_loading: bool; runtime_binding_ready: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdCredentialBindingV1:
    credential_binding_id: str; provider_id: str; logical_credential_label: str; systemd_credential_name: str
    credential_file_runtime_name: str; expected_runtime_directory: str; routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]; load_directive: str; environment_secret_loading: bool
    environment_file_secret_loading: bool; shell_expansion_of_secret: bool; argument_secret_material: bool
    credential_loading_authorized: bool; binding_ready: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdHardeningProfileV1:
    hardening_profile_id: str; no_new_privileges: str; private_tmp: str; private_devices: str; protect_system: str
    protect_home: str; protect_kernel_tunables: str; protect_kernel_modules: str; protect_kernel_logs: str
    protect_control_groups: str; restrict_suid_sgid: str; restrict_realtime: str; lock_personality: str
    memory_deny_write_execute: str; remove_ipc: str; system_call_architectures: str; restrict_namespaces: str
    capability_bounding_set: str; ambient_capabilities: str; umask: str; proc_subset: str; protect_proc: str
    device_policy: str; ip_address_deny: str; restrict_address_families: str; read_write_paths: str
    read_only_paths: str; inaccessible_paths: str; relaxed_directives: tuple[str, ...]; relaxation_justifications: tuple[str, ...]
    hardening_profile_ready: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdLifecyclePolicyV1:
    lifecycle_policy_id: str; installation_procedure_defined: bool; rollback_procedure_defined: bool
    uninstall_procedure_defined: bool; daemon_reload_procedure_defined: bool; enablement_procedure_defined: bool
    start_procedure_defined: bool; stop_procedure_defined: bool; restart_procedure_defined: bool
    failure_recovery_procedure_defined: bool; credential_rotation_coordination_defined: bool
    credential_revocation_coordination_defined: bool; pre_start_verification_required: bool
    post_start_verification_required: bool; deployment_lock_required: bool
    operator_reviewer_separation_required: bool; installation_authorized: bool; daemon_reload_authorized: bool
    enablement_authorized: bool; start_restart_authorized: bool; lifecycle_policy_ready: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdLoggingPolicyV1:
    logging_policy_id: str; journald_classification: str; stdout_policy: str; stderr_policy: str; log_level_policy: str
    redaction_required: bool; api_key_redaction_required: bool; authorization_header_redaction_required: bool
    provider_response_redaction_required: bool; billing_data_redaction_required: bool
    exception_sanitization_required: bool; stack_trace_policy: str; retention_classification: str
    rate_limit_classification: str; secret_derived_identifiers_forbidden: bool
    credential_paths_forbidden: bool; environment_dumps_forbidden: bool; logging_policy_ready: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdDeploymentChecklistV1:
    checklist_id: str; policy_id: str; unit_identity: str; execution_identity_id: str; runtime_binding_id: str
    credential_binding_ids: tuple[str, ...]; hardening_profile_id: str; lifecycle_policy_id: str; logging_policy_id: str
    canonical_unit_identity_confirmed: bool; manager_scope_confirmed: bool; deployment_state_confirmed: bool
    execution_user_resolved: bool; execution_group_resolved: bool; executable_path_resolved: bool
    working_directory_resolved: bool; runtime_entrypoint_resolved: bool; locked_commit_confirmed: bool
    encrypted_credential_binding_defined: bool; credential_loading_unauthorized: bool
    service_installation_unauthorized: bool; daemon_reload_unauthorized: bool; enablement_unauthorized: bool
    start_restart_unauthorized: bool; provider_validation_unauthorized: bool; network_activation_unauthorized: bool
    provider_transmission_unauthorized: bool; runtime_activation_unauthorized: bool; publication_unauthorized: bool
    hardening_profile_complete: bool; lifecycle_procedures_complete: bool; logging_policy_complete: bool
    rollback_complete: bool; operator_attestation_complete: bool; independent_review_complete: bool
    evidence_fresh: bool; checklist_complete: bool; prohibited_authority_claimed: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdOperatorAttestationV1:
    attestation_id: str; policy_id: str; unit_identity: str; checklist_id: str; operator_id: str; operator_role: str
    attested_at: datetime; redacted_metadata_only: bool; installation_not_performed: bool; credentials_not_accessed: bool
    attestation_complete: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdIndependentReviewerApprovalV1:
    approval_id: str; policy_id: str; unit_identity: str; checklist_id: str; attestation_id: str; reviewer_id: str
    reviewer_role: str; approved_at: datetime; independent_review_complete: bool; redacted_evidence_only: bool
    design_approved: bool; review_complete: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdDesignFailureV1:
    failure_code: str; safe_message: str; retryable: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdDesignDecisionV1:
    policy_id: str; unit_name: str; manager_scope: str; deployment_state: str; ready: bool; design_state: str
    state_codes: tuple[str, ...]; supported_state_codes: tuple[str, ...]; failure_codes: tuple[str, ...]
    failures: tuple[ProductionSystemdDesignFailureV1, ...]; service_unit_design_authorized: bool
    service_unit_installation_authorized: bool; daemon_reload_authorized: bool; service_enablement_authorized: bool
    service_start_restart_authorized: bool; owner_secret_entry_authorized: bool
    credential_value_access_authorized: bool; credential_loading_authorized: bool
    credential_validation_authorized: bool; network_authorized: bool; provider_transmission_authorized: bool
    runtime_activation_authorized: bool; runtime_configuration_authorized: bool; publication_authorized: bool; fail_closed: bool


@dataclass(frozen=True, slots=True)
class ProductionSystemdDesignAuditEvidenceV1:
    evidence_id: str; policy_id: str; unit_name: str; manager_scope: str; deployment_state: str
    execution_identity_id: str; runtime_binding_id: str; credential_binding_ids: tuple[str, ...]; hardening_profile_id: str
    lifecycle_policy_id: str; logging_policy_id: str; identity_resolution_state: str; locked_commit_confirmed: bool
    encrypted_credentials_defined: bool; hardening_ready: bool; lifecycle_ready: bool; logging_ready: bool
    operator_id: str; operator_role: str; reviewer_id: str; reviewer_role: str; evidence_freshness: str
    failure_codes: tuple[str, ...]; service_unit_design_authorized: bool; service_unit_installation_authorized: bool
    daemon_reload_authorized: bool; service_enablement_authorized: bool; service_start_restart_authorized: bool
    owner_secret_entry_authorized: bool; credential_value_access_authorized: bool
    credential_loading_authorized: bool; credential_validation_authorized: bool; network_authorized: bool
    provider_transmission_authorized: bool; runtime_activation_authorized: bool
    runtime_configuration_authorized: bool; publication_authorized: bool; fail_closed: bool


def _yes(value: bool) -> bool:
    return value is True


def _binding(binding: ProductionSystemdCredentialBindingV1) -> tuple[str, str, str, tuple[str, ...], tuple[str, ...]] | None:
    return next((item for item in _BINDINGS if item[0] == binding.provider_id), None)


def _failure_codes(
    policy: ProductionSystemdServiceUnitPolicyV1, service: ProductionSystemdServiceIdentityV1,
    execution: ProductionSystemdExecutionIdentityV1, runtime: ProductionSystemdRuntimeBindingV1,
    credentials: tuple[ProductionSystemdCredentialBindingV1, ...], hardening: ProductionSystemdHardeningProfileV1,
    lifecycle: ProductionSystemdLifecyclePolicyV1, logging_policy: ProductionSystemdLoggingPolicyV1,
    checklist: ProductionSystemdDeploymentChecklistV1, operator: ProductionSystemdOperatorAttestationV1 | None,
    reviewer: ProductionSystemdIndependentReviewerApprovalV1 | None, at: datetime,
) -> tuple[str, ...]:
    bindings = tuple(_binding(item) for item in credentials)
    classifications = (
        hardening.no_new_privileges, hardening.private_tmp, hardening.private_devices, hardening.protect_system,
        hardening.protect_home, hardening.protect_kernel_tunables, hardening.protect_kernel_modules,
        hardening.protect_kernel_logs, hardening.protect_control_groups, hardening.restrict_suid_sgid,
        hardening.restrict_realtime, hardening.lock_personality, hardening.memory_deny_write_execute,
        hardening.remove_ipc, hardening.system_call_architectures, hardening.restrict_namespaces,
        hardening.capability_bounding_set, hardening.ambient_capabilities, hardening.umask,
        hardening.proc_subset, hardening.protect_proc, hardening.device_policy, hardening.ip_address_deny,
        hardening.restrict_address_families, hardening.read_write_paths, hardening.read_only_paths,
        hardening.inaccessible_paths,
    )
    future = operator is not None and operator.attested_at > at or reviewer is not None and reviewer.approved_at > at
    stale = operator is not None and not operator.attested_at > at and (at - operator.attested_at).total_seconds() > policy.evidence_max_age_seconds
    expired = reviewer is not None and not reviewer.approved_at > at and (at - reviewer.approved_at).total_seconds() > policy.evidence_max_age_seconds
    credential_names = tuple(item.systemd_credential_name for item in credentials)
    credential_bad = any(binding is None or (
        item.logical_credential_label != binding[1] or item.systemd_credential_name != binding[2]
        or item.credential_file_runtime_name != binding[2] or item.expected_runtime_directory != "CREDENTIALS_DIRECTORY"
        or item.routing_levels != binding[3] or item.exact_provider_model_ids != binding[4]
    ) for item, binding in zip(credentials, bindings))
    conditions = {
        "POLICY_ID_EMPTY": not policy.policy_id,
        "POLICY_VERSION_EMPTY": not policy.policy_version,
        "UNIT_NAME_MISMATCH": policy.canonical_unit_name != _UNIT_NAME or service.unit_name != _UNIT_NAME,
        "MANAGER_SCOPE_MISMATCH": policy.manager_scope != "SYSTEM" or service.manager_scope != "SYSTEM",
        "DEPLOYMENT_STATE_MISMATCH": policy.deployment_state != "NOT_YET_INSTALLED" or service.deployment_state != "NOT_YET_INSTALLED",
        "SERVICE_USER_REQUIRED": not execution.service_user or not _yes(execution.execution_identity_ready),
        "ROOT_SERVICE_USER_NOT_ALLOWED": execution.service_user == "root",
        "SERVICE_GROUP_REQUIRED": not execution.service_group,
        "ROOT_SERVICE_GROUP_NOT_ALLOWED": execution.service_group == "root",
        "EXECUTABLE_PATH_REQUIRED": not execution.executable_path or not execution.executable_path.startswith("REPOSITORY_BOUND_ABSOLUTE_PATH"),
        "WORKING_DIRECTORY_REQUIRED": not execution.working_directory,
        "RUNTIME_ENTRYPOINT_REQUIRED": not execution.runtime_entrypoint or not runtime.module_or_entrypoint,
        "REPOSITORY_ROOT_MISMATCH": runtime.repository_root != "REPOSITORY_ROOT" or runtime.expected_branch != policy.expected_branch,
        "LOCKED_COMMIT_MISMATCH": runtime.expected_locked_commit != policy.expected_locked_commit,
        "RUNTIME_ARGUMENT_SECRET_EXPOSURE": any("SECRET" in argument for argument in execution.runtime_arguments + runtime.runtime_arguments) or any(_yes(item.argument_secret_material) or _yes(item.shell_expansion_of_secret) for item in credentials),
        "ENVIRONMENT_SECRET_LOADING_NOT_ALLOWED": any(_yes(item.environment_secret_loading) for item in credentials),
        "ENVIRONMENT_FILE_SECRET_LOADING_NOT_ALLOWED": any(_yes(item.environment_file_secret_loading) for item in credentials),
        "SYSTEMD_CREDENTIAL_BINDING_REQUIRED": not credentials or any(not _yes(item.binding_ready) for item in credentials),
        "SYSTEMD_CREDENTIAL_NAME_MISMATCH": credential_bad,
        "SYSTEMD_CREDENTIAL_NAME_SHARED": len(set(credential_names)) != len(credential_names),
        "LOAD_CREDENTIAL_ENCRYPTED_REQUIRED": any(item.load_directive != "LoadCredentialEncrypted" for item in credentials) or not _yes(policy.require_encrypted_credentials),
        "CREDENTIAL_LOADING_NOT_AUTHORIZED": any(_yes(item.credential_loading_authorized) for item in credentials) or not _yes(checklist.credential_loading_unauthorized) or not _yes(runtime.no_implicit_credential_loading),
        "AUTOMATIC_PROVIDER_RETRY_NOT_AUTHORIZED": not _yes(runtime.no_automatic_provider_retry),
        "IMPLICIT_NETWORK_ACTIVATION_NOT_AUTHORIZED": not _yes(runtime.no_implicit_network_activation),
        "HARDENING_PROFILE_REQUIRED": not _yes(hardening.hardening_profile_ready) or not _yes(policy.require_hardening_profile) or any(not value for value in classifications),
        "HARDENING_JUSTIFICATION_REQUIRED": any(value not in ("REQUIRED", "REQUIRED_WITH_JUSTIFICATION", "NOT_APPLICABLE_WITH_JUSTIFICATION") for value in classifications) or any(not text for text in hardening.relaxation_justifications),
        "LOGGING_POLICY_REQUIRED": not _yes(logging_policy.logging_policy_ready) or not _yes(policy.require_logging_policy),
        "LOG_REDACTION_REQUIRED": not all((logging_policy.redaction_required, logging_policy.api_key_redaction_required, logging_policy.authorization_header_redaction_required, logging_policy.provider_response_redaction_required, logging_policy.billing_data_redaction_required, logging_policy.exception_sanitization_required, logging_policy.secret_derived_identifiers_forbidden, logging_policy.credential_paths_forbidden, logging_policy.environment_dumps_forbidden)),
        "LIFECYCLE_POLICY_REQUIRED": not _yes(lifecycle.lifecycle_policy_ready) or not _yes(policy.require_lifecycle_policy),
        "ROLLBACK_PROCEDURE_REQUIRED": not _yes(lifecycle.rollback_procedure_defined),
        "OPERATOR_ATTESTATION_REQUIRED": operator is None or (operator is not None and (not operator.attestation_id or not operator.operator_id or operator.operator_role != "DESIGN_OPERATOR" or operator.policy_id != policy.policy_id or operator.unit_identity != service.unit_identity or operator.checklist_id != checklist.checklist_id or not _yes(operator.redacted_metadata_only) or not _yes(operator.installation_not_performed) or not _yes(operator.credentials_not_accessed) or not _yes(operator.attestation_complete))),
        "REVIEWER_APPROVAL_REQUIRED": reviewer is None or (reviewer is not None and (not reviewer.approval_id or not reviewer.reviewer_id or reviewer.reviewer_role != "INDEPENDENT_SECURITY_REVIEWER" or reviewer.policy_id != policy.policy_id or reviewer.unit_identity != service.unit_identity or reviewer.checklist_id != checklist.checklist_id or (operator is not None and reviewer.attestation_id != operator.attestation_id) or not _yes(reviewer.independent_review_complete) or not _yes(reviewer.redacted_evidence_only) or not _yes(reviewer.design_approved) or not _yes(reviewer.review_complete) or not _yes(policy.require_independent_review))),
        "OPERATOR_REVIEWER_COLLISION": operator is not None and reviewer is not None and operator.operator_id == reviewer.reviewer_id,
        "EVIDENCE_FROM_FUTURE": future,
        "EVIDENCE_STALE": stale,
        "EVIDENCE_EXPIRED": expired,
        "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED": _yes(service.service_installation_authorized) or _yes(lifecycle.installation_authorized) or not _yes(checklist.service_installation_unauthorized),
        "DAEMON_RELOAD_NOT_AUTHORIZED": _yes(service.daemon_reload_authorized) or _yes(lifecycle.daemon_reload_authorized) or not _yes(checklist.daemon_reload_unauthorized),
        "SERVICE_ENABLEMENT_NOT_AUTHORIZED": _yes(service.service_enablement_authorized) or _yes(lifecycle.enablement_authorized) or not _yes(checklist.enablement_unauthorized),
        "SERVICE_START_RESTART_NOT_AUTHORIZED": _yes(service.service_start_restart_authorized) or _yes(lifecycle.start_restart_authorized) or not _yes(checklist.start_restart_unauthorized),
        "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED": _yes(checklist.prohibited_authority_claimed),
        "CREDENTIAL_VALIDATION_NOT_AUTHORIZED": not _yes(checklist.provider_validation_unauthorized),
        "NETWORK_NOT_AUTHORIZED": not _yes(checklist.network_activation_unauthorized),
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED": not _yes(checklist.provider_transmission_unauthorized),
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED": not _yes(checklist.runtime_activation_unauthorized),
        "RUNTIME_CONFIGURATION_NOT_AUTHORIZED": False,
        "PUBLICATION_NOT_AUTHORIZED": not _yes(checklist.publication_unauthorized),
        "RAW_CREDENTIAL_EXPOSURE_DETECTED": False,
        "RAW_EXCEPTION_EXPOSURE_DETECTED": False,
    }
    return tuple(code for code in _ORDER if conditions[code])


def evaluate_production_systemd_service_unit_design_v1(
    *, policy: ProductionSystemdServiceUnitPolicyV1, service_identity: ProductionSystemdServiceIdentityV1,
    execution_identity: ProductionSystemdExecutionIdentityV1, runtime_binding: ProductionSystemdRuntimeBindingV1,
    credential_bindings: tuple[ProductionSystemdCredentialBindingV1, ...], hardening_profile: ProductionSystemdHardeningProfileV1,
    lifecycle_policy: ProductionSystemdLifecyclePolicyV1, logging_policy: ProductionSystemdLoggingPolicyV1,
    checklist: ProductionSystemdDeploymentChecklistV1, operator_attestation: ProductionSystemdOperatorAttestationV1 | None,
    reviewer_approval: ProductionSystemdIndependentReviewerApprovalV1 | None, evaluation_at: datetime,
) -> ProductionSystemdDesignDecisionV1:
    """Evaluate caller metadata only; no service, credential, filesystem, or network operation occurs."""
    codes = _failure_codes(policy, service_identity, execution_identity, runtime_binding, credential_bindings, hardening_profile, lifecycle_policy, logging_policy, checklist, operator_attestation, reviewer_approval, evaluation_at)
    ready = not codes
    return ProductionSystemdDesignDecisionV1(
        policy_id=policy.policy_id, unit_name=service_identity.unit_name, manager_scope=service_identity.manager_scope,
        deployment_state=service_identity.deployment_state, ready=ready,
        design_state="SERVICE_UNIT_DESIGN_READY" if ready else "DEPLOYMENT_BLOCKED",
        state_codes=("CANONICAL_SERVICE_IDENTITY_DEFINED", "EXECUTION_IDENTITY_RESOLVED", "RUNTIME_BINDING_RESOLVED", "SYSTEMD_CREDENTIAL_BINDING_DEFINED", "SERVICE_UNIT_DESIGN_READY", "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED") if ready else ("DEPLOYMENT_BLOCKED", "SERVICE_UNIT_INSTALLATION_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        supported_state_codes=_STATES, failure_codes=codes,
        failures=tuple(ProductionSystemdDesignFailureV1(code, _MESSAGES[code], False) for code in codes),
        service_unit_design_authorized=True, service_unit_installation_authorized=False,
        daemon_reload_authorized=False, service_enablement_authorized=False,
        service_start_restart_authorized=False, owner_secret_entry_authorized=True,
        credential_value_access_authorized=False, credential_loading_authorized=False,
        credential_validation_authorized=False, network_authorized=False,
        provider_transmission_authorized=False, runtime_activation_authorized=False,
        runtime_configuration_authorized=False, publication_authorized=False, fail_closed=True,
    )


def build_production_systemd_service_unit_design_audit_evidence_v1(
    *, evidence_id: str, decision: ProductionSystemdDesignDecisionV1, policy: ProductionSystemdServiceUnitPolicyV1,
    service_identity: ProductionSystemdServiceIdentityV1, execution_identity: ProductionSystemdExecutionIdentityV1,
    runtime_binding: ProductionSystemdRuntimeBindingV1, credential_bindings: tuple[ProductionSystemdCredentialBindingV1, ...],
    hardening_profile: ProductionSystemdHardeningProfileV1, lifecycle_policy: ProductionSystemdLifecyclePolicyV1,
    logging_policy: ProductionSystemdLoggingPolicyV1, checklist: ProductionSystemdDeploymentChecklistV1,
    operator_attestation: ProductionSystemdOperatorAttestationV1, reviewer_approval: ProductionSystemdIndependentReviewerApprovalV1,
    evidence_at: datetime,
) -> ProductionSystemdDesignAuditEvidenceV1:
    """Build redacted immutable metadata evidence without I/O, mutation, or system interaction."""
    fresh = operator_attestation.attested_at <= evidence_at and reviewer_approval.approved_at <= evidence_at and (evidence_at - operator_attestation.attested_at).total_seconds() <= policy.evidence_max_age_seconds and (evidence_at - reviewer_approval.approved_at).total_seconds() <= policy.evidence_max_age_seconds
    alignment = ("POLICY_ID_EMPTY",) if not policy.policy_id else ()
    failures = tuple(code for code in _ORDER if code in decision.failure_codes or code in alignment)
    return ProductionSystemdDesignAuditEvidenceV1(
        evidence_id=evidence_id, policy_id=policy.policy_id, unit_name=service_identity.unit_name,
        manager_scope=service_identity.manager_scope, deployment_state=service_identity.deployment_state,
        execution_identity_id=execution_identity.execution_identity_id, runtime_binding_id=runtime_binding.runtime_binding_id,
        credential_binding_ids=tuple(binding.credential_binding_id for binding in credential_bindings),
        hardening_profile_id=hardening_profile.hardening_profile_id, lifecycle_policy_id=lifecycle_policy.lifecycle_policy_id,
        logging_policy_id=logging_policy.logging_policy_id,
        identity_resolution_state="RESOLVED" if execution_identity.execution_identity_ready and runtime_binding.runtime_binding_ready else "UNRESOLVED",
        locked_commit_confirmed=runtime_binding.expected_locked_commit == policy.expected_locked_commit,
        encrypted_credentials_defined=all(binding.load_directive == "LoadCredentialEncrypted" for binding in credential_bindings),
        hardening_ready=hardening_profile.hardening_profile_ready, lifecycle_ready=lifecycle_policy.lifecycle_policy_ready,
        logging_ready=logging_policy.logging_policy_ready, operator_id=operator_attestation.operator_id,
        operator_role=operator_attestation.operator_role, reviewer_id=reviewer_approval.reviewer_id,
        reviewer_role=reviewer_approval.reviewer_role, evidence_freshness="FRESH" if fresh else "NOT_FRESH",
        failure_codes=failures, service_unit_design_authorized=True,
        service_unit_installation_authorized=False, daemon_reload_authorized=False,
        service_enablement_authorized=False, service_start_restart_authorized=False,
        owner_secret_entry_authorized=True, credential_value_access_authorized=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        network_authorized=False, provider_transmission_authorized=False,
        runtime_activation_authorized=False, runtime_configuration_authorized=False,
        publication_authorized=False, fail_closed=True,
    )
