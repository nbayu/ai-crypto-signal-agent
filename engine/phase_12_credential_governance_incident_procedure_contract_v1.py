"""Pure metadata-only credential governance readiness boundary."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CredentialGovernancePolicyV1:
    policy_id: str = ""; policy_version: str = ""; provider_id: str = ""; deployment_environment: str = ""
    allowed_deployment_environments: tuple = (); allowed_source_types: tuple = (); allowed_credential_names: tuple = ()
    require_explicit_owner_authorization: bool = True; require_operator_identity: bool = True; require_separation_of_duties: bool = True
    require_credential_source_selected: bool = True; require_source_redaction: bool = True; require_non_repository_storage: bool = True
    require_no_plaintext_configuration: bool = True; require_no_shell_history_exposure: bool = True; require_no_log_exposure: bool = True
    require_no_test_fixture_exposure: bool = True; require_no_error_exposure: bool = True; require_rotation_procedure: bool = True
    require_revocation_procedure: bool = True; require_expiry_policy: bool = True; require_leak_response: bool = True
    require_provider_console_revocation: bool = True; require_application_restart_or_reload_plan: bool = True
    require_post_rotation_verification: bool = True; require_post_revocation_verification: bool = True
    require_incident_audit_evidence: bool = True; require_credential_fingerprint_only: bool = True
    onboarding_authorized: bool = False; credential_loading_authorized: bool = False; credential_validation_authorized: bool = False
    network_authorized: bool = False; provider_transmission_authorized: bool = False; fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class CredentialSourceGovernanceV1:
    credential_source_id: str; policy_id: str; provider_id: str; deployment_environment: str; source_type: str; credential_name: str
    source_location_classification: str; source_selected: bool; source_redacted: bool; non_repository_storage: bool
    plaintext_configuration_forbidden: bool; shell_history_exposure_forbidden: bool; log_exposure_forbidden: bool
    test_fixture_exposure_forbidden: bool; error_exposure_forbidden: bool; source_access_operator_role: str
    source_management_operator_role: str; separation_of_duties_ready: bool; file_permissions_policy_id: str
    access_control_policy_id: str; source_backup_policy_id: str; source_recovery_policy_id: str; source_ready: bool


@dataclass(frozen=True, slots=True)
class CredentialOnboardingProcedureV1:
    onboarding_procedure_id: str; policy_id: str; credential_source_id: str; owner_authorization_id: str
    requesting_operator_id: str; approving_operator_id: str; execution_operator_id: str; authorization_present: bool
    separation_of_duties_satisfied: bool; provider_account_verified: bool; credential_created_outside_repository: bool
    credential_scoped_to_required_permissions: bool; credential_expiry_configured: bool; credential_stored_in_selected_source: bool
    plaintext_copy_destroyed: bool; shell_history_protected: bool; logs_protected: bool; tests_protected: bool
    repository_scan_required: bool; post_onboarding_verification_required: bool; rollback_defined: bool; onboarding_ready: bool


@dataclass(frozen=True, slots=True)
class CredentialRotationProcedureV1:
    rotation_procedure_id: str; policy_id: str; credential_source_id: str; rotation_interval_days: int
    maximum_credential_age_days: int; rotation_trigger_types: tuple; owner_authorization_required: bool
    new_credential_created_before_cutover: bool; overlap_window_allowed: bool; overlap_window_minutes: int
    old_credential_revoked_after_cutover: bool; application_reload_defined: bool
    post_rotation_verification_defined: bool; rollback_defined: bool; audit_evidence_required: bool; rotation_ready: bool


@dataclass(frozen=True, slots=True)
class CredentialRevocationProcedureV1:
    revocation_procedure_id: str; policy_id: str; credential_source_id: str; revocation_trigger_types: tuple
    immediate_revocation_supported: bool; provider_console_revocation_defined: bool; local_source_removal_defined: bool
    application_stop_or_reload_defined: bool; active_session_invalidation_defined: bool
    post_revocation_verification_defined: bool; audit_evidence_required: bool; escalation_owner_id: str; revocation_ready: bool


@dataclass(frozen=True, slots=True)
class CredentialLeakResponseProcedureV1:
    leak_response_procedure_id: str; policy_id: str; credential_source_id: str; incident_severity_classifications: tuple
    immediate_kill_switch_required: bool; immediate_provider_revocation_required: bool; application_shutdown_required: bool
    local_source_quarantine_required: bool; repository_history_assessment_required: bool; log_and_artifact_assessment_required: bool
    shell_history_assessment_required: bool; CI_artifact_assessment_required: bool; rotation_required: bool
    forensic_evidence_preservation_required: bool; affected_window_identification_required: bool; notification_owner_id: str
    escalation_owner_id: str; incident_audit_required: bool; post_incident_review_required: bool; leak_response_ready: bool


@dataclass(frozen=True, slots=True)
class CredentialGovernanceFailureV1:
    failure_code: str; safe_message: str; retryable: bool


@dataclass(frozen=True, slots=True)
class CredentialGovernanceReadinessDecisionV1:
    policy_id: str; provider_id: str; deployment_environment: str; ready: bool; failure_codes: tuple[str, ...]; policy_valid: bool
    source_governance_ready: bool; naming_ready: bool; onboarding_procedure_ready: bool; rotation_procedure_ready: bool
    revocation_procedure_ready: bool; leak_response_ready: bool; separation_of_duties_ready: bool
    repository_exposure_controls_ready: bool; operational_verification_ready: bool; onboarding_authorized: bool
    credential_loading_authorized: bool; credential_validation_authorized: bool; network_authorized: bool; provider_transmission_authorized: bool


@dataclass(frozen=True, slots=True)
class CredentialGovernanceAuditEvidenceV1:
    policy_id: str; provider_id: str; deployment_environment: str; credential_source_id: str; source_type: str
    credential_name: str; source_redacted: bool; non_repository_storage: bool; separation_of_duties_ready: bool
    onboarding_ready: bool; rotation_ready: bool; revocation_ready: bool; leak_response_ready: bool
    repository_exposure_controls_ready: bool; rollback_ready: bool; verification_ready: bool; failure_codes: tuple[str, ...]
    onboarding_authorized: bool; credential_loading_authorized: bool; credential_validation_authorized: bool
    network_authorized: bool; provider_transmission_authorized: bool


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _positive(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _append(codes: list[str], valid: bool, code: str) -> None:
    if not valid:
        codes.append(code)


def evaluate_credential_governance_readiness_v1(
    policy: CredentialGovernancePolicyV1,
    source: CredentialSourceGovernanceV1,
    onboarding: CredentialOnboardingProcedureV1,
    rotation: CredentialRotationProcedureV1,
    revocation: CredentialRevocationProcedureV1,
    leak_response: CredentialLeakResponseProcedureV1,
) -> CredentialGovernanceReadinessDecisionV1:
    codes: list[str] = []
    _append(codes, _identifier(policy.policy_id), "POLICY_ID_EMPTY")
    _append(codes, _identifier(policy.policy_version), "POLICY_VERSION_EMPTY")
    _append(codes, _identifier(policy.provider_id), "PROVIDER_ID_EMPTY")
    _append(codes, _identifier(policy.deployment_environment), "DEPLOYMENT_ENVIRONMENT_EMPTY")
    _append(codes, policy.deployment_environment in policy.allowed_deployment_environments, "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED")
    _append(codes, _identifier(source.credential_source_id), "CREDENTIAL_SOURCE_ID_EMPTY")
    _append(codes, _identifier(source.source_type), "SOURCE_TYPE_EMPTY")
    _append(codes, source.source_type in policy.allowed_source_types, "SOURCE_TYPE_NOT_ALLOWED")
    _append(codes, _identifier(source.credential_name), "CREDENTIAL_NAME_EMPTY")
    _append(codes, _identifier(source.credential_name), "CREDENTIAL_NAME_NOT_NORMALIZED")
    _append(codes, source.credential_name in policy.allowed_credential_names, "CREDENTIAL_NAME_NOT_ALLOWED")
    _append(codes, source.source_selected, "SOURCE_NOT_SELECTED")
    _append(codes, source.source_redacted, "SOURCE_NOT_REDACTED")
    _append(codes, source.non_repository_storage, "REPOSITORY_STORAGE_FORBIDDEN")
    _append(codes, source.plaintext_configuration_forbidden, "PLAINTEXT_CONFIGURATION_FORBIDDEN")
    _append(codes, source.shell_history_exposure_forbidden, "SHELL_HISTORY_PROTECTION_REQUIRED")
    _append(codes, source.log_exposure_forbidden, "LOG_REDACTION_REQUIRED")
    _append(codes, source.test_fixture_exposure_forbidden, "TEST_FIXTURE_REDACTION_REQUIRED")
    _append(codes, source.error_exposure_forbidden, "ERROR_REDACTION_REQUIRED")
    _append(codes, _identifier(source.source_location_classification), "SOURCE_LOCATION_EXPOSURE_DETECTED")
    source_alignment = source.policy_id == policy.policy_id and source.provider_id == policy.provider_id and source.deployment_environment == policy.deployment_environment
    _append(codes, source_alignment and source.source_ready, "SOURCE_NOT_SELECTED")
    operators = (onboarding.requesting_operator_id, onboarding.approving_operator_id, onboarding.execution_operator_id)
    _append(codes, _identifier(onboarding.owner_authorization_id) and onboarding.authorization_present, "OWNER_AUTHORIZATION_PROCEDURE_REQUIRED")
    _append(codes, all(_identifier(item) for item in operators), "OPERATOR_IDENTITY_REQUIRED")
    separated = len(set(operators)) == 3 and source.source_access_operator_role != source.source_management_operator_role
    _append(codes, onboarding.separation_of_duties_satisfied and source.separation_of_duties_ready and separated, "SEPARATION_OF_DUTIES_REQUIRED")
    _append(codes, onboarding.provider_account_verified, "PROVIDER_ACCOUNT_VERIFICATION_REQUIRED")
    _append(codes, onboarding.credential_scoped_to_required_permissions, "CREDENTIAL_PERMISSION_SCOPE_REQUIRED")
    _append(codes, onboarding.credential_expiry_configured, "CREDENTIAL_EXPIRY_POLICY_REQUIRED")
    onboarding_controls = (onboarding.credential_created_outside_repository and onboarding.credential_stored_in_selected_source and onboarding.plaintext_copy_destroyed and onboarding.shell_history_protected and onboarding.logs_protected and onboarding.tests_protected and onboarding.repository_scan_required and onboarding.rollback_defined)
    _append(codes, onboarding_controls and onboarding.onboarding_ready and onboarding.policy_id == policy.policy_id and onboarding.credential_source_id == source.credential_source_id, "ONBOARDING_PROCEDURE_NOT_READY")
    _append(codes, onboarding.post_onboarding_verification_required, "POST_ONBOARDING_VERIFICATION_REQUIRED")
    rotation_values = _positive(rotation.rotation_interval_days) and _positive(rotation.maximum_credential_age_days)
    _append(codes, _positive(rotation.rotation_interval_days), "ROTATION_INTERVAL_INVALID")
    _append(codes, _positive(rotation.rotation_interval_days) and _positive(rotation.maximum_credential_age_days) and rotation.maximum_credential_age_days >= rotation.rotation_interval_days, "MAXIMUM_CREDENTIAL_AGE_INVALID")
    overlap_valid = isinstance(rotation.overlap_window_minutes, int) and not isinstance(rotation.overlap_window_minutes, bool) and ((not rotation.overlap_window_allowed and rotation.overlap_window_minutes == 0) or (rotation.overlap_window_allowed and rotation.overlap_window_minutes > 0 and rotation.overlap_window_minutes <= 1440))
    _append(codes, overlap_valid, "ROTATION_OVERLAP_INVALID")
    _append(codes, rotation.old_credential_revoked_after_cutover, "OLD_CREDENTIAL_REVOCATION_REQUIRED")
    _append(codes, rotation.application_reload_defined, "APPLICATION_STOP_OR_RELOAD_REQUIRED")
    _append(codes, rotation.post_rotation_verification_defined, "POST_ROTATION_VERIFICATION_REQUIRED")
    rotation_controls = rotation_values and bool(rotation.rotation_trigger_types) and rotation.owner_authorization_required and rotation.new_credential_created_before_cutover and rotation.rollback_defined and rotation.audit_evidence_required
    _append(codes, rotation_controls and rotation.rotation_ready and rotation.policy_id == policy.policy_id and rotation.credential_source_id == source.credential_source_id, "ROTATION_PROCEDURE_NOT_READY")
    _append(codes, revocation.immediate_revocation_supported, "IMMEDIATE_REVOCATION_REQUIRED")
    _append(codes, revocation.provider_console_revocation_defined, "PROVIDER_CONSOLE_REVOCATION_REQUIRED")
    _append(codes, revocation.local_source_removal_defined, "LOCAL_SOURCE_REMOVAL_REQUIRED")
    _append(codes, revocation.application_stop_or_reload_defined, "APPLICATION_STOP_OR_RELOAD_REQUIRED")
    _append(codes, revocation.post_revocation_verification_defined, "POST_REVOCATION_VERIFICATION_REQUIRED")
    revocation_controls = bool(revocation.revocation_trigger_types) and revocation.active_session_invalidation_defined and revocation.audit_evidence_required and _identifier(revocation.escalation_owner_id)
    _append(codes, revocation_controls and revocation.revocation_ready and revocation.policy_id == policy.policy_id and revocation.credential_source_id == source.credential_source_id, "REVOCATION_PROCEDURE_NOT_READY")
    _append(codes, leak_response.immediate_kill_switch_required, "KILL_SWITCH_REQUIRED_FOR_LEAK")
    _append(codes, leak_response.repository_history_assessment_required, "REPOSITORY_HISTORY_ASSESSMENT_REQUIRED")
    _append(codes, leak_response.log_and_artifact_assessment_required, "LOG_ARTIFACT_ASSESSMENT_REQUIRED")
    _append(codes, leak_response.shell_history_assessment_required, "SHELL_HISTORY_ASSESSMENT_REQUIRED")
    _append(codes, leak_response.CI_artifact_assessment_required, "CI_ARTIFACT_ASSESSMENT_REQUIRED")
    _append(codes, leak_response.forensic_evidence_preservation_required, "FORENSIC_EVIDENCE_PRESERVATION_REQUIRED")
    _append(codes, _identifier(leak_response.notification_owner_id), "INCIDENT_NOTIFICATION_OWNER_REQUIRED")
    _append(codes, _identifier(leak_response.escalation_owner_id), "INCIDENT_ESCALATION_OWNER_REQUIRED")
    _append(codes, leak_response.incident_audit_required, "INCIDENT_AUDIT_REQUIRED")
    _append(codes, leak_response.post_incident_review_required, "POST_INCIDENT_REVIEW_REQUIRED")
    leak_controls = (bool(leak_response.incident_severity_classifications) and leak_response.immediate_provider_revocation_required and leak_response.application_shutdown_required and leak_response.local_source_quarantine_required and leak_response.rotation_required and leak_response.affected_window_identification_required)
    _append(codes, leak_controls and leak_response.leak_response_ready and leak_response.policy_id == policy.policy_id and leak_response.credential_source_id == source.credential_source_id, "LEAK_RESPONSE_NOT_READY")
    policy_valid = not any(code in codes for code in ("POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PROVIDER_ID_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY", "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED"))
    source_ready = source_alignment and source.source_ready and not any(code in codes for code in ("CREDENTIAL_SOURCE_ID_EMPTY", "SOURCE_TYPE_EMPTY", "SOURCE_TYPE_NOT_ALLOWED", "SOURCE_NOT_SELECTED", "SOURCE_NOT_REDACTED", "REPOSITORY_STORAGE_FORBIDDEN", "PLAINTEXT_CONFIGURATION_FORBIDDEN", "SHELL_HISTORY_PROTECTION_REQUIRED", "LOG_REDACTION_REQUIRED", "TEST_FIXTURE_REDACTION_REQUIRED", "ERROR_REDACTION_REQUIRED"))
    naming_ready = not any(code in codes for code in ("CREDENTIAL_NAME_EMPTY", "CREDENTIAL_NAME_NOT_NORMALIZED", "CREDENTIAL_NAME_NOT_ALLOWED"))
    onboarding_ready = onboarding.onboarding_ready and not any(code in codes for code in ("OWNER_AUTHORIZATION_PROCEDURE_REQUIRED", "OPERATOR_IDENTITY_REQUIRED", "SEPARATION_OF_DUTIES_REQUIRED", "PROVIDER_ACCOUNT_VERIFICATION_REQUIRED", "CREDENTIAL_PERMISSION_SCOPE_REQUIRED", "CREDENTIAL_EXPIRY_POLICY_REQUIRED", "ONBOARDING_PROCEDURE_NOT_READY", "POST_ONBOARDING_VERIFICATION_REQUIRED"))
    rotation_ready = rotation.rotation_ready and not any(code in codes for code in ("ROTATION_PROCEDURE_NOT_READY", "ROTATION_INTERVAL_INVALID", "MAXIMUM_CREDENTIAL_AGE_INVALID", "ROTATION_OVERLAP_INVALID", "OLD_CREDENTIAL_REVOCATION_REQUIRED", "POST_ROTATION_VERIFICATION_REQUIRED"))
    revocation_ready = revocation.revocation_ready and not any(code in codes for code in ("REVOCATION_PROCEDURE_NOT_READY", "IMMEDIATE_REVOCATION_REQUIRED", "PROVIDER_CONSOLE_REVOCATION_REQUIRED", "LOCAL_SOURCE_REMOVAL_REQUIRED", "APPLICATION_STOP_OR_RELOAD_REQUIRED", "POST_REVOCATION_VERIFICATION_REQUIRED"))
    leak_ready = leak_response.leak_response_ready and not any(code in codes for code in ("LEAK_RESPONSE_NOT_READY", "KILL_SWITCH_REQUIRED_FOR_LEAK", "REPOSITORY_HISTORY_ASSESSMENT_REQUIRED", "LOG_ARTIFACT_ASSESSMENT_REQUIRED", "SHELL_HISTORY_ASSESSMENT_REQUIRED", "CI_ARTIFACT_ASSESSMENT_REQUIRED", "FORENSIC_EVIDENCE_PRESERVATION_REQUIRED", "INCIDENT_NOTIFICATION_OWNER_REQUIRED", "INCIDENT_ESCALATION_OWNER_REQUIRED", "INCIDENT_AUDIT_REQUIRED", "POST_INCIDENT_REVIEW_REQUIRED"))
    separation_ready = "SEPARATION_OF_DUTIES_REQUIRED" not in codes
    repository_controls = not any(code in codes for code in ("REPOSITORY_STORAGE_FORBIDDEN", "PLAINTEXT_CONFIGURATION_FORBIDDEN", "SHELL_HISTORY_PROTECTION_REQUIRED", "LOG_REDACTION_REQUIRED", "TEST_FIXTURE_REDACTION_REQUIRED", "ERROR_REDACTION_REQUIRED"))
    verification_ready = onboarding.post_onboarding_verification_required and rotation.post_rotation_verification_defined and revocation.post_revocation_verification_defined
    ordered = tuple(sorted(set(codes)))
    return CredentialGovernanceReadinessDecisionV1(policy.policy_id, policy.provider_id, policy.deployment_environment, not ordered, ordered, policy_valid, source_ready, naming_ready, onboarding_ready, rotation_ready, revocation_ready, leak_ready, separation_ready, repository_controls, verification_ready, False, False, False, False, False)


def build_credential_governance_audit_evidence_v1(
    policy: CredentialGovernancePolicyV1,
    source: CredentialSourceGovernanceV1,
    onboarding: CredentialOnboardingProcedureV1,
    rotation: CredentialRotationProcedureV1,
    revocation: CredentialRevocationProcedureV1,
    leak_response: CredentialLeakResponseProcedureV1,
    decision: CredentialGovernanceReadinessDecisionV1,
) -> CredentialGovernanceAuditEvidenceV1:
    aligned = (source.policy_id == policy.policy_id and source.provider_id == policy.provider_id and source.deployment_environment == policy.deployment_environment and onboarding.policy_id == policy.policy_id and onboarding.credential_source_id == source.credential_source_id and rotation.policy_id == policy.policy_id and rotation.credential_source_id == source.credential_source_id and revocation.policy_id == policy.policy_id and revocation.credential_source_id == source.credential_source_id and leak_response.policy_id == policy.policy_id and leak_response.credential_source_id == source.credential_source_id and decision.policy_id == policy.policy_id and decision.provider_id == policy.provider_id and decision.deployment_environment == policy.deployment_environment)
    if not aligned:
        raise ValueError("credential governance identity mismatch")
    return CredentialGovernanceAuditEvidenceV1(policy.policy_id, policy.provider_id, policy.deployment_environment, source.credential_source_id, source.source_type, source.credential_name, source.source_redacted, source.non_repository_storage, decision.separation_of_duties_ready, decision.onboarding_procedure_ready, decision.rotation_procedure_ready, decision.revocation_procedure_ready, decision.leak_response_ready, decision.repository_exposure_controls_ready, onboarding.rollback_defined and rotation.rollback_defined, decision.operational_verification_ready, decision.failure_codes, False, False, False, False, False)
