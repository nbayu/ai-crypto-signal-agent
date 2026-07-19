"""RED contract for Phase 12 credential governance metadata and procedures."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime

import pytest

from engine.phase_12_credential_governance_incident_procedure_contract_v1 import (
    CredentialGovernanceAuditEvidenceV1,
    CredentialGovernanceFailureV1,
    CredentialGovernancePolicyV1,
    CredentialGovernanceReadinessDecisionV1,
    CredentialLeakResponseProcedureV1,
    CredentialOnboardingProcedureV1,
    CredentialRevocationProcedureV1,
    CredentialRotationProcedureV1,
    CredentialSourceGovernanceV1,
    build_credential_governance_audit_evidence_v1,
    evaluate_credential_governance_readiness_v1,
)


_NOW = datetime(2030, 1, 7, 12, 0, tzinfo=UTC)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "provider_id", "deployment_environment",
    "allowed_deployment_environments", "allowed_source_types", "allowed_credential_names",
    "require_explicit_owner_authorization", "require_operator_identity",
    "require_separation_of_duties", "require_credential_source_selected",
    "require_source_redaction", "require_non_repository_storage",
    "require_no_plaintext_configuration", "require_no_shell_history_exposure",
    "require_no_log_exposure", "require_no_test_fixture_exposure",
    "require_no_error_exposure", "require_rotation_procedure", "require_revocation_procedure",
    "require_expiry_policy", "require_leak_response", "require_provider_console_revocation",
    "require_application_restart_or_reload_plan", "require_post_rotation_verification",
    "require_post_revocation_verification", "require_incident_audit_evidence",
    "require_credential_fingerprint_only", "onboarding_authorized",
    "credential_loading_authorized", "credential_validation_authorized", "network_authorized",
    "provider_transmission_authorized", "fail_closed",
)
_SOURCE_FIELDS = (
    "credential_source_id", "policy_id", "provider_id", "deployment_environment", "source_type",
    "credential_name", "source_location_classification", "source_selected", "source_redacted",
    "non_repository_storage", "plaintext_configuration_forbidden", "shell_history_exposure_forbidden",
    "log_exposure_forbidden", "test_fixture_exposure_forbidden", "error_exposure_forbidden",
    "source_access_operator_role", "source_management_operator_role", "separation_of_duties_ready",
    "file_permissions_policy_id", "access_control_policy_id", "source_backup_policy_id",
    "source_recovery_policy_id", "source_ready",
)
_ONBOARDING_FIELDS = (
    "onboarding_procedure_id", "policy_id", "credential_source_id", "owner_authorization_id",
    "requesting_operator_id", "approving_operator_id", "execution_operator_id", "authorization_present",
    "separation_of_duties_satisfied", "provider_account_verified", "credential_created_outside_repository",
    "credential_scoped_to_required_permissions", "credential_expiry_configured",
    "credential_stored_in_selected_source", "plaintext_copy_destroyed", "shell_history_protected",
    "logs_protected", "tests_protected", "repository_scan_required",
    "post_onboarding_verification_required", "rollback_defined", "onboarding_ready",
)
_ROTATION_FIELDS = (
    "rotation_procedure_id", "policy_id", "credential_source_id", "rotation_interval_days",
    "maximum_credential_age_days", "rotation_trigger_types", "owner_authorization_required",
    "new_credential_created_before_cutover", "overlap_window_allowed", "overlap_window_minutes",
    "old_credential_revoked_after_cutover", "application_reload_defined",
    "post_rotation_verification_defined", "rollback_defined", "audit_evidence_required", "rotation_ready",
)
_REVOCATION_FIELDS = (
    "revocation_procedure_id", "policy_id", "credential_source_id", "revocation_trigger_types",
    "immediate_revocation_supported", "provider_console_revocation_defined", "local_source_removal_defined",
    "application_stop_or_reload_defined", "active_session_invalidation_defined",
    "post_revocation_verification_defined", "audit_evidence_required", "escalation_owner_id",
    "revocation_ready",
)
_LEAK_FIELDS = (
    "leak_response_procedure_id", "policy_id", "credential_source_id",
    "incident_severity_classifications", "immediate_kill_switch_required",
    "immediate_provider_revocation_required", "application_shutdown_required",
    "local_source_quarantine_required", "repository_history_assessment_required",
    "log_and_artifact_assessment_required", "shell_history_assessment_required",
    "CI_artifact_assessment_required", "rotation_required", "forensic_evidence_preservation_required",
    "affected_window_identification_required", "notification_owner_id", "escalation_owner_id",
    "incident_audit_required", "post_incident_review_required", "leak_response_ready",
)
_DECISION_FIELDS = (
    "policy_id", "provider_id", "deployment_environment", "ready", "failure_codes", "policy_valid",
    "source_governance_ready", "naming_ready", "onboarding_procedure_ready", "rotation_procedure_ready",
    "revocation_procedure_ready", "leak_response_ready", "separation_of_duties_ready",
    "repository_exposure_controls_ready", "operational_verification_ready", "onboarding_authorized",
    "credential_loading_authorized", "credential_validation_authorized", "network_authorized",
    "provider_transmission_authorized",
)
_AUDIT_FIELDS = (
    "policy_id", "provider_id", "deployment_environment", "credential_source_id", "source_type",
    "credential_name", "source_redacted", "non_repository_storage", "separation_of_duties_ready",
    "onboarding_ready", "rotation_ready", "revocation_ready", "leak_response_ready",
    "repository_exposure_controls_ready", "rollback_ready", "verification_ready", "failure_codes",
    "onboarding_authorized", "credential_loading_authorized", "credential_validation_authorized",
    "network_authorized", "provider_transmission_authorized",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_FAILURES = {
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "PROVIDER_ID_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED", "CREDENTIAL_SOURCE_ID_EMPTY", "SOURCE_TYPE_EMPTY",
    "SOURCE_TYPE_NOT_ALLOWED", "CREDENTIAL_NAME_EMPTY", "CREDENTIAL_NAME_NOT_NORMALIZED",
    "CREDENTIAL_NAME_NOT_ALLOWED", "SOURCE_NOT_SELECTED", "SOURCE_NOT_REDACTED",
    "REPOSITORY_STORAGE_FORBIDDEN", "PLAINTEXT_CONFIGURATION_FORBIDDEN",
    "SHELL_HISTORY_PROTECTION_REQUIRED", "LOG_REDACTION_REQUIRED", "TEST_FIXTURE_REDACTION_REQUIRED",
    "ERROR_REDACTION_REQUIRED", "SOURCE_LOCATION_EXPOSURE_DETECTED",
    "OWNER_AUTHORIZATION_PROCEDURE_REQUIRED", "OPERATOR_IDENTITY_REQUIRED",
    "SEPARATION_OF_DUTIES_REQUIRED", "PROVIDER_ACCOUNT_VERIFICATION_REQUIRED",
    "CREDENTIAL_PERMISSION_SCOPE_REQUIRED", "CREDENTIAL_EXPIRY_POLICY_REQUIRED",
    "ONBOARDING_PROCEDURE_NOT_READY", "ROTATION_PROCEDURE_NOT_READY", "ROTATION_INTERVAL_INVALID",
    "MAXIMUM_CREDENTIAL_AGE_INVALID", "ROTATION_OVERLAP_INVALID",
    "OLD_CREDENTIAL_REVOCATION_REQUIRED", "REVOCATION_PROCEDURE_NOT_READY",
    "IMMEDIATE_REVOCATION_REQUIRED", "PROVIDER_CONSOLE_REVOCATION_REQUIRED",
    "LOCAL_SOURCE_REMOVAL_REQUIRED", "APPLICATION_STOP_OR_RELOAD_REQUIRED",
    "POST_REVOCATION_VERIFICATION_REQUIRED", "LEAK_RESPONSE_NOT_READY", "KILL_SWITCH_REQUIRED_FOR_LEAK",
    "REPOSITORY_HISTORY_ASSESSMENT_REQUIRED", "LOG_ARTIFACT_ASSESSMENT_REQUIRED",
    "SHELL_HISTORY_ASSESSMENT_REQUIRED", "CI_ARTIFACT_ASSESSMENT_REQUIRED",
    "FORENSIC_EVIDENCE_PRESERVATION_REQUIRED", "INCIDENT_NOTIFICATION_OWNER_REQUIRED",
    "INCIDENT_ESCALATION_OWNER_REQUIRED", "INCIDENT_AUDIT_REQUIRED", "POST_INCIDENT_REVIEW_REQUIRED",
    "ROLLBACK_PROCEDURE_REQUIRED", "POST_ONBOARDING_VERIFICATION_REQUIRED",
    "POST_ROTATION_VERIFICATION_REQUIRED", "RAW_CREDENTIAL_EXPOSURE_DETECTED",
    "RAW_SOURCE_LOCATION_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
    "ONBOARDING_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "CREDENTIAL_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
}
_FORBIDDEN_FIELDS = {
    "value", "secret", "secret_value", "api_key", "token", "password", "authorization",
    "header", "path", "uri", "location", "raw_exception",
}


def _frozen(value: object) -> None:
    assert is_dataclass(value) and type(value).__dataclass_params__.frozen
    assert "__dict__" not in type(value).__slots__


def _policy(**overrides: object) -> CredentialGovernancePolicyV1:
    values = dict(
        policy_id="credential-governance-policy-v1", policy_version="V1", provider_id="provider-v1",
        deployment_environment="CONTROLLED_PRODUCTION", allowed_deployment_environments=("CONTROLLED_PRODUCTION",),
        allowed_source_types=("PROCESS_ENVIRONMENT_REFERENCE",),
        allowed_credential_names=("PROVIDER_API_KEY_PRODUCTION",),
        require_explicit_owner_authorization=True, require_operator_identity=True,
        require_separation_of_duties=True, require_credential_source_selected=True,
        require_source_redaction=True, require_non_repository_storage=True,
        require_no_plaintext_configuration=True, require_no_shell_history_exposure=True,
        require_no_log_exposure=True, require_no_test_fixture_exposure=True,
        require_no_error_exposure=True, require_rotation_procedure=True,
        require_revocation_procedure=True, require_expiry_policy=True, require_leak_response=True,
        require_provider_console_revocation=True, require_application_restart_or_reload_plan=True,
        require_post_rotation_verification=True, require_post_revocation_verification=True,
        require_incident_audit_evidence=True, require_credential_fingerprint_only=True,
        onboarding_authorized=False, credential_loading_authorized=False,
        credential_validation_authorized=False, network_authorized=False,
        provider_transmission_authorized=False, fail_closed=True,
    )
    values.update(overrides)
    return CredentialGovernancePolicyV1(**values)


def _source(**overrides: object) -> CredentialSourceGovernanceV1:
    values = dict(
        credential_source_id="credential-source-v1", policy_id="credential-governance-policy-v1",
        provider_id="provider-v1", deployment_environment="CONTROLLED_PRODUCTION",
        source_type="PROCESS_ENVIRONMENT_REFERENCE", credential_name="PROVIDER_API_KEY_PRODUCTION",
        source_location_classification="REDACTED_REFERENCE", source_selected=True, source_redacted=True,
        non_repository_storage=True, plaintext_configuration_forbidden=True,
        shell_history_exposure_forbidden=True, log_exposure_forbidden=True,
        test_fixture_exposure_forbidden=True, error_exposure_forbidden=True,
        source_access_operator_role="credential-reader", source_management_operator_role="credential-manager",
        separation_of_duties_ready=True, file_permissions_policy_id="permissions-policy-v1",
        access_control_policy_id="access-policy-v1", source_backup_policy_id="backup-policy-v1",
        source_recovery_policy_id="recovery-policy-v1", source_ready=True,
    )
    values.update(overrides)
    return CredentialSourceGovernanceV1(**values)


def _onboarding(**overrides: object) -> CredentialOnboardingProcedureV1:
    values = dict(
        onboarding_procedure_id="onboarding-procedure-v1", policy_id="credential-governance-policy-v1",
        credential_source_id="credential-source-v1", owner_authorization_id="owner-authorization-v1",
        requesting_operator_id="requester-v1", approving_operator_id="approver-v1",
        execution_operator_id="executor-v1", authorization_present=True,
        separation_of_duties_satisfied=True, provider_account_verified=True,
        credential_created_outside_repository=True, credential_scoped_to_required_permissions=True,
        credential_expiry_configured=True, credential_stored_in_selected_source=True,
        plaintext_copy_destroyed=True, shell_history_protected=True, logs_protected=True,
        tests_protected=True, repository_scan_required=True,
        post_onboarding_verification_required=True, rollback_defined=True, onboarding_ready=True,
    )
    values.update(overrides)
    return CredentialOnboardingProcedureV1(**values)


def _rotation(**overrides: object) -> CredentialRotationProcedureV1:
    values = dict(
        rotation_procedure_id="rotation-procedure-v1", policy_id="credential-governance-policy-v1",
        credential_source_id="credential-source-v1", rotation_interval_days=30,
        maximum_credential_age_days=60, rotation_trigger_types=("SCHEDULED_ROTATION", "SUSPECTED_EXPOSURE"),
        owner_authorization_required=True, new_credential_created_before_cutover=True,
        overlap_window_allowed=True, overlap_window_minutes=15, old_credential_revoked_after_cutover=True,
        application_reload_defined=True, post_rotation_verification_defined=True,
        rollback_defined=True, audit_evidence_required=True, rotation_ready=True,
    )
    values.update(overrides)
    return CredentialRotationProcedureV1(**values)


def _revocation(**overrides: object) -> CredentialRevocationProcedureV1:
    values = dict(
        revocation_procedure_id="revocation-procedure-v1", policy_id="credential-governance-policy-v1",
        credential_source_id="credential-source-v1",
        revocation_trigger_types=("OWNER_REQUEST", "SUSPECTED_EXPOSURE", "CONFIRMED_EXPOSURE", "OPERATOR_DEPARTURE", "PROVIDER_ACCOUNT_CHANGE", "PERMISSION_CHANGE", "SCHEDULED_ROTATION", "SYSTEM_DECOMMISSION"),
        immediate_revocation_supported=True, provider_console_revocation_defined=True,
        local_source_removal_defined=True, application_stop_or_reload_defined=True,
        active_session_invalidation_defined=True, post_revocation_verification_defined=True,
        audit_evidence_required=True, escalation_owner_id="revocation-owner-v1", revocation_ready=True,
    )
    values.update(overrides)
    return CredentialRevocationProcedureV1(**values)


def _leak(**overrides: object) -> CredentialLeakResponseProcedureV1:
    values = dict(
        leak_response_procedure_id="leak-response-procedure-v1", policy_id="credential-governance-policy-v1",
        credential_source_id="credential-source-v1",
        incident_severity_classifications=("SUSPECTED_EXPOSURE", "CONFIRMED_EXPOSURE", "REPOSITORY_EXPOSURE", "LOG_EXPOSURE", "SHELL_HISTORY_EXPOSURE", "CI_ARTIFACT_EXPOSURE", "OPERATOR_DEVICE_EXPOSURE"),
        immediate_kill_switch_required=True, immediate_provider_revocation_required=True,
        application_shutdown_required=True, local_source_quarantine_required=True,
        repository_history_assessment_required=True, log_and_artifact_assessment_required=True,
        shell_history_assessment_required=True, CI_artifact_assessment_required=True,
        rotation_required=True, forensic_evidence_preservation_required=True,
        affected_window_identification_required=True, notification_owner_id="notification-owner-v1",
        escalation_owner_id="incident-owner-v1", incident_audit_required=True,
        post_incident_review_required=True, leak_response_ready=True,
    )
    values.update(overrides)
    return CredentialLeakResponseProcedureV1(**values)


def _decision(**overrides: object) -> CredentialGovernanceReadinessDecisionV1:
    return evaluate_credential_governance_readiness_v1(
        _policy(**overrides), _source(), _onboarding(), _rotation(), _revocation(), _leak()
    )


def test_public_contract_is_immutable_redacted_and_zero_authority() -> None:
    schemas = (
        (CredentialGovernancePolicyV1, _POLICY_FIELDS), (CredentialSourceGovernanceV1, _SOURCE_FIELDS),
        (CredentialOnboardingProcedureV1, _ONBOARDING_FIELDS), (CredentialRotationProcedureV1, _ROTATION_FIELDS),
        (CredentialRevocationProcedureV1, _REVOCATION_FIELDS), (CredentialLeakResponseProcedureV1, _LEAK_FIELDS),
        (CredentialGovernanceReadinessDecisionV1, _DECISION_FIELDS),
        (CredentialGovernanceAuditEvidenceV1, _AUDIT_FIELDS), (CredentialGovernanceFailureV1, _FAILURE_FIELDS),
    )
    decision = _decision()
    audit = build_credential_governance_audit_evidence_v1(
        _policy(), _source(), _onboarding(), _rotation(), _revocation(), _leak(), decision
    )
    for schema, expected in schemas:
        assert tuple(field.name for field in fields(schema)) == expected
        assert not _FORBIDDEN_FIELDS.intersection(field.name for field in fields(schema))
    for value in (_policy(), _source(), _onboarding(), _rotation(), _revocation(), _leak(), decision, audit):
        _frozen(value)
    with pytest.raises(FrozenInstanceError):
        decision.network_authorized = True  # type: ignore[misc]
    assert (decision.onboarding_authorized, decision.credential_loading_authorized,
            decision.credential_validation_authorized, decision.network_authorized,
            decision.provider_transmission_authorized) == (False,) * 5


def test_fail_closed_source_and_operator_controls_are_deterministic() -> None:
    decision = evaluate_credential_governance_readiness_v1(
        _policy(), _source(source_type="UNAPPROVED_REFERENCE", source_redacted=False,
                           non_repository_storage=False, log_exposure_forbidden=False),
        _onboarding(authorization_present=False, separation_of_duties_satisfied=False,
                    provider_account_verified=False, credential_expiry_configured=False),
        _rotation(), _revocation(), _leak(),
    )
    required = {"SOURCE_TYPE_NOT_ALLOWED", "SOURCE_NOT_REDACTED", "REPOSITORY_STORAGE_FORBIDDEN",
                "LOG_REDACTION_REQUIRED", "OWNER_AUTHORIZATION_PROCEDURE_REQUIRED",
                "SEPARATION_OF_DUTIES_REQUIRED", "PROVIDER_ACCOUNT_VERIFICATION_REQUIRED",
                "CREDENTIAL_EXPIRY_POLICY_REQUIRED"}
    assert required.issubset(decision.failure_codes)
    assert decision.failure_codes == tuple(sorted(decision.failure_codes))
    assert set(decision.failure_codes).issubset(_FAILURES)
    assert not decision.ready


def test_rotation_revocation_and_incident_controls_fail_closed() -> None:
    decision = evaluate_credential_governance_readiness_v1(
        _policy(), _source(), _onboarding(),
        _rotation(rotation_interval_days=True, maximum_credential_age_days=15,
                  overlap_window_minutes=0, old_credential_revoked_after_cutover=False,
                  post_rotation_verification_defined=False),
        _revocation(immediate_revocation_supported=False, provider_console_revocation_defined=False,
                    local_source_removal_defined=False, application_stop_or_reload_defined=False,
                    post_revocation_verification_defined=False),
        _leak(immediate_kill_switch_required=False, repository_history_assessment_required=False,
              log_and_artifact_assessment_required=False, shell_history_assessment_required=False,
              CI_artifact_assessment_required=False, forensic_evidence_preservation_required=False,
              notification_owner_id="", escalation_owner_id="", incident_audit_required=False,
              post_incident_review_required=False),
    )
    required = {"ROTATION_INTERVAL_INVALID", "MAXIMUM_CREDENTIAL_AGE_INVALID", "ROTATION_OVERLAP_INVALID",
                "OLD_CREDENTIAL_REVOCATION_REQUIRED", "POST_ROTATION_VERIFICATION_REQUIRED",
                "IMMEDIATE_REVOCATION_REQUIRED", "PROVIDER_CONSOLE_REVOCATION_REQUIRED",
                "LOCAL_SOURCE_REMOVAL_REQUIRED", "APPLICATION_STOP_OR_RELOAD_REQUIRED",
                "POST_REVOCATION_VERIFICATION_REQUIRED", "KILL_SWITCH_REQUIRED_FOR_LEAK",
                "REPOSITORY_HISTORY_ASSESSMENT_REQUIRED", "LOG_ARTIFACT_ASSESSMENT_REQUIRED",
                "SHELL_HISTORY_ASSESSMENT_REQUIRED", "CI_ARTIFACT_ASSESSMENT_REQUIRED",
                "FORENSIC_EVIDENCE_PRESERVATION_REQUIRED", "INCIDENT_NOTIFICATION_OWNER_REQUIRED",
                "INCIDENT_ESCALATION_OWNER_REQUIRED", "INCIDENT_AUDIT_REQUIRED", "POST_INCIDENT_REVIEW_REQUIRED"}
    assert required.issubset(decision.failure_codes)
    assert not decision.ready


def test_complete_synthetic_governance_is_only_ready_for_separate_authorization() -> None:
    decision = _decision()
    assert decision.ready
    assert decision.naming_ready and decision.source_governance_ready
    assert decision.onboarding_procedure_ready and decision.rotation_procedure_ready
    assert decision.revocation_procedure_ready and decision.leak_response_ready
    assert decision.repository_exposure_controls_ready and decision.operational_verification_ready
    assert not any((decision.onboarding_authorized, decision.credential_loading_authorized,
                    decision.credential_validation_authorized, decision.network_authorized,
                    decision.provider_transmission_authorized))


def test_audit_is_identity_bound_deterministic_and_never_grants_authority() -> None:
    policy, source, onboarding, rotation, revocation, leak = _policy(), _source(), _onboarding(), _rotation(), _revocation(), _leak()
    decision = evaluate_credential_governance_readiness_v1(policy, source, onboarding, rotation, revocation, leak)
    first = build_credential_governance_audit_evidence_v1(policy, source, onboarding, rotation, revocation, leak, decision)
    second = build_credential_governance_audit_evidence_v1(policy, source, onboarding, rotation, revocation, leak, decision)
    assert first == second
    assert first.policy_id == policy.policy_id and first.credential_source_id == source.credential_source_id
    assert (first.onboarding_authorized, first.credential_loading_authorized,
            first.credential_validation_authorized, first.network_authorized,
            first.provider_transmission_authorized) == (False,) * 5
    with pytest.raises(ValueError):
        build_credential_governance_audit_evidence_v1(policy, _source(provider_id="other-provider-v1"), onboarding, rotation, revocation, leak, decision)
