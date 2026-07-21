"""RED contract for Phase 12 credential-onboarding security procedure only."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from engine.phase_12_credential_onboarding_security_procedure_contract_v1 import (
    CredentialIndependentReviewerApprovalV1,
    CredentialOnboardingAuditEvidenceV1,
    CredentialOnboardingChecklistV1,
    CredentialOnboardingDecisionV1,
    CredentialOnboardingFailureV1,
    CredentialOnboardingSecurityPolicyV1,
    CredentialOperatorAttestationV1,
    CredentialSecretTargetV1,
    build_credential_onboarding_audit_evidence_v1,
    evaluate_credential_onboarding_v1,
)


_NOW = datetime(2030, 1, 7, 12, 0, tzinfo=UTC)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "deployment_environment",
    "onboarding_authorization_confirmed", "require_provider_secret_separation",
    "require_no_shared_provider_credential", "require_least_privilege_scope",
    "require_dedicated_project_credential_when_supported", "require_revocation_capability",
    "require_rotation_procedure", "require_local_secret_store_target",
    "require_repository_path_exclusion", "require_git_ignore_coverage",
    "require_restrictive_permissions", "require_no_command_line_argument_exposure",
    "require_no_shell_history_exposure", "require_no_stdout_exposure",
    "require_no_stderr_exposure", "require_no_test_fixture_exposure",
    "require_no_log_exposure", "require_no_audit_evidence_exposure",
    "require_no_environment_dump", "require_no_process_list_exposure",
    "require_no_backup_archive_exposure", "require_no_screenshot_retention",
    "require_clipboard_cleanup", "require_rollback_procedure",
    "require_deletion_procedure", "require_independent_reviewer_confirmation",
    "evidence_max_age_seconds", "fail_closed",
)
_TARGET_FIELDS = (
    "secret_target_id", "policy_id", "provider_id", "credential_label", "routing_levels",
    "exact_provider_model_ids", "secret_store_classification", "target_outside_repository",
    "target_may_be_committed", "git_ignore_protection_confirmed", "permissions_restrictive",
)
_CHECKLIST_FIELDS = (
    "checklist_id", "policy_id", "secret_target_id", "provider_id", "credential_label",
    "routing_levels", "exact_provider_model_ids", "provider_secret_separation_confirmed",
    "credential_label_not_shared", "least_privilege_scope_confirmed",
    "dedicated_project_credential_confirmed", "revocation_capability_confirmed",
    "rotation_procedure_defined", "rollback_procedure_defined", "deletion_procedure_defined",
    "repository_path_excluded", "git_ignore_coverage_confirmed", "permissions_restrictive",
    "command_line_argument_exposure_prevented", "shell_history_exposure_prevented",
    "stdout_exposure_prevented", "stderr_exposure_prevented", "log_exposure_prevented",
    "test_fixture_exposure_prevented", "audit_evidence_exposure_prevented",
    "environment_dump_prevented", "process_list_exposure_prevented",
    "backup_archive_exposure_prevented", "screenshot_retention_prevented",
    "clipboard_cleanup_confirmed", "credential_material_supplied",
    "credential_fingerprint_supplied", "exception_detail_supplied",
    "credential_value_access_attempted", "credential_loading_attempted",
    "provider_validation_attempted", "network_attempted", "provider_transmission_attempted",
    "runtime_activation_attempted", "runtime_configuration_attempted", "publication_attempted",
)
_OPERATOR_FIELDS = (
    "operator_attestation_id", "policy_id", "secret_target_id", "operator_id", "operator_role",
    "attested_at", "owner_secret_entry_pending", "secret_placement_attested_redacted",
    "no_credential_material_in_attestation", "rollback_and_deletion_ready",
)
_REVIEWER_FIELDS = (
    "reviewer_approval_id", "policy_id", "secret_target_id", "reviewer_id", "reviewer_role",
    "approved_at", "independent_review_complete", "redacted_evidence_only",
    "onboarding_procedure_approved",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_DECISION_FIELDS = (
    "policy_id", "provider_id", "credential_label", "routing_levels", "exact_provider_model_ids",
    "ready", "onboarding_state", "state_codes", "supported_state_codes", "failure_codes", "failures",
    "credential_onboarding_authorized", "credential_value_access_authorized",
    "credential_loading_authorized", "credential_validation_authorized", "network_authorized",
    "provider_transmission_authorized", "runtime_activation_authorized",
    "runtime_configuration_authorized", "publication_authorized", "fail_closed",
)
_AUDIT_FIELDS = (
    "evidence_id", "policy_id", "policy_version", "provider_id", "credential_label",
    "routing_levels", "exact_provider_model_ids", "onboarding_authorization_confirmed",
    "secret_target_classification", "repository_path_excluded", "git_ignore_ready",
    "permissions_restrictive", "history_exposure_prevented", "argv_exposure_prevented",
    "stdout_exposure_prevented", "stderr_exposure_prevented", "log_exposure_prevented",
    "test_exposure_prevented", "audit_exposure_prevented", "clipboard_cleanup_ready",
    "rotation_ready", "revocation_ready", "rollback_ready", "deletion_ready", "operator_id",
    "operator_role", "reviewer_id", "reviewer_role", "evidence_freshness",
    "failure_codes", "credential_onboarding_authorized", "credential_value_access_authorized",
    "credential_loading_authorized", "credential_validation_authorized", "network_authorized",
    "provider_transmission_authorized", "runtime_activation_authorized",
    "runtime_configuration_authorized", "publication_authorized", "fail_closed",
)
_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "ONBOARDING_NOT_AUTHORIZED", "PROVIDER_NOT_ALLOWED", "ROUTING_LEVEL_MISMATCH",
    "EXACT_MODEL_ID_MISMATCH", "CREDENTIAL_LABEL_EMPTY", "CREDENTIAL_LABEL_SHARED",
    "RAW_CREDENTIAL_VALUE_PROVIDED", "RAW_CREDENTIAL_FINGERPRINT_PROVIDED",
    "SECRET_TARGET_REQUIRED", "SECRET_TARGET_INSIDE_REPOSITORY", "SECRET_TARGET_COMMITTABLE",
    "GIT_IGNORE_PROTECTION_REQUIRED", "RESTRICTIVE_PERMISSION_REQUIRED",
    "SHELL_HISTORY_EXPOSURE_RISK", "PROCESS_ARGUMENT_EXPOSURE_RISK", "STDOUT_EXPOSURE_RISK",
    "STDERR_EXPOSURE_RISK", "LOG_EXPOSURE_RISK", "TEST_FIXTURE_EXPOSURE_RISK",
    "AUDIT_EVIDENCE_EXPOSURE_RISK", "ENVIRONMENT_DUMP_NOT_AUTHORIZED",
    "CLIPBOARD_CLEANUP_REQUIRED", "ROTATION_PROCEDURE_REQUIRED",
    "REVOCATION_PROCEDURE_REQUIRED", "ROLLBACK_PROCEDURE_REQUIRED",
    "DELETION_PROCEDURE_REQUIRED", "OPERATOR_ATTESTATION_REQUIRED",
    "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE",
    "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "CREDENTIAL_VALIDATION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "RUNTIME_CONFIGURATION_NOT_AUTHORIZED",
    "PUBLICATION_NOT_AUTHORIZED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)
_STATES = (
    "ONBOARDING_PROCEDURE_DEFINED", "SECRET_TARGET_READY", "OWNER_SECRET_ENTRY_PENDING",
    "SECRET_PLACEMENT_ATTESTED_REDACTED", "INDEPENDENT_REVIEW_COMPLETE",
    "CREDENTIAL_PRESENT_BUT_NOT_LOADED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PROVIDER_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "REVOKED", "ROTATION_REQUIRED", "ONBOARDING_BLOCKED",
)
_PROHIBITED_FIELD_NAMES = (
    "value", "secret_value", "api_key", "token", "password", "authorization_header",
    "cookie", "account_identity", "organization_identity", "workspace_identity",
    "project_identity", "provider_response", "secret_file_contents", "environment_value",
    "exception_text", "stack_trace", "credential_hash",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> CredentialOnboardingSecurityPolicyV1:
    values = dict(
        policy_id="credential-onboarding-policy-v1", policy_version="V1",
        deployment_environment="CONTROLLED_PRODUCTION",
        onboarding_authorization_confirmed=True, require_provider_secret_separation=True,
        require_no_shared_provider_credential=True, require_least_privilege_scope=True,
        require_dedicated_project_credential_when_supported=True, require_revocation_capability=True,
        require_rotation_procedure=True, require_local_secret_store_target=True,
        require_repository_path_exclusion=True, require_git_ignore_coverage=True,
        require_restrictive_permissions=True, require_no_command_line_argument_exposure=True,
        require_no_shell_history_exposure=True, require_no_stdout_exposure=True,
        require_no_stderr_exposure=True, require_no_test_fixture_exposure=True,
        require_no_log_exposure=True, require_no_audit_evidence_exposure=True,
        require_no_environment_dump=True, require_no_process_list_exposure=True,
        require_no_backup_archive_exposure=True, require_no_screenshot_retention=True,
        require_clipboard_cleanup=True, require_rollback_procedure=True,
        require_deletion_procedure=True, require_independent_reviewer_confirmation=True,
        evidence_max_age_seconds=3600, fail_closed=True,
    )
    return CredentialOnboardingSecurityPolicyV1(**(values | overrides))


def _target(**overrides: object) -> CredentialSecretTargetV1:
    values = dict(
        secret_target_id="deepseek-secret-target-v1", policy_id="credential-onboarding-policy-v1",
        provider_id="DEEPSEEK", credential_label="DEEPSEEK_API_KEY", routing_levels=("L0",),
        exact_provider_model_ids=("deepseek-v4-pro",),
        secret_store_classification="LOCAL_SECRET_STORE_REFERENCE_ONLY",
        target_outside_repository=True, target_may_be_committed=False,
        git_ignore_protection_confirmed=True, permissions_restrictive=True,
    )
    return CredentialSecretTargetV1(**(values | overrides))


def _checklist(**overrides: object) -> CredentialOnboardingChecklistV1:
    values = dict(
        checklist_id="credential-onboarding-checklist-v1", policy_id="credential-onboarding-policy-v1",
        secret_target_id="deepseek-secret-target-v1", provider_id="DEEPSEEK",
        credential_label="DEEPSEEK_API_KEY", routing_levels=("L0",),
        exact_provider_model_ids=("deepseek-v4-pro",), provider_secret_separation_confirmed=True,
        credential_label_not_shared=True, least_privilege_scope_confirmed=True,
        dedicated_project_credential_confirmed=True, revocation_capability_confirmed=True,
        rotation_procedure_defined=True, rollback_procedure_defined=True,
        deletion_procedure_defined=True, repository_path_excluded=True,
        git_ignore_coverage_confirmed=True, permissions_restrictive=True,
        command_line_argument_exposure_prevented=True, shell_history_exposure_prevented=True,
        stdout_exposure_prevented=True, stderr_exposure_prevented=True, log_exposure_prevented=True,
        test_fixture_exposure_prevented=True, audit_evidence_exposure_prevented=True,
        environment_dump_prevented=True, process_list_exposure_prevented=True,
        backup_archive_exposure_prevented=True, screenshot_retention_prevented=True,
        clipboard_cleanup_confirmed=True, credential_material_supplied=False,
        credential_fingerprint_supplied=False, exception_detail_supplied=False,
        credential_value_access_attempted=False, credential_loading_attempted=False,
        provider_validation_attempted=False, network_attempted=False,
        provider_transmission_attempted=False, runtime_activation_attempted=False,
        runtime_configuration_attempted=False, publication_attempted=False,
    )
    return CredentialOnboardingChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> CredentialOperatorAttestationV1:
    values = dict(
        operator_attestation_id="operator-attestation-v1", policy_id="credential-onboarding-policy-v1",
        secret_target_id="deepseek-secret-target-v1", operator_id="operator-1",
        operator_role="SECRET_ENTRY_OPERATOR", attested_at=_NOW - timedelta(minutes=5),
        owner_secret_entry_pending=True, secret_placement_attested_redacted=False,
        no_credential_material_in_attestation=True, rollback_and_deletion_ready=True,
    )
    return CredentialOperatorAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> CredentialIndependentReviewerApprovalV1:
    values = dict(
        reviewer_approval_id="reviewer-approval-v1", policy_id="credential-onboarding-policy-v1",
        secret_target_id="deepseek-secret-target-v1", reviewer_id="reviewer-1",
        reviewer_role="INDEPENDENT_SECURITY_REVIEWER", approved_at=_NOW - timedelta(minutes=4),
        independent_review_complete=True, redacted_evidence_only=True,
        onboarding_procedure_approved=True,
    )
    return CredentialIndependentReviewerApprovalV1(**(values | overrides))


def _decision(**overrides: object) -> CredentialOnboardingDecisionV1:
    return evaluate_credential_onboarding_v1(
        policy=_policy(**overrides), secret_target=_target(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )


def test_public_api_is_immutable_metadata_only_and_has_no_secret_value_fields() -> None:
    assert tuple(field.name for field in fields(CredentialOnboardingSecurityPolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(CredentialSecretTargetV1)) == _TARGET_FIELDS
    assert tuple(field.name for field in fields(CredentialOnboardingChecklistV1)) == _CHECKLIST_FIELDS
    assert tuple(field.name for field in fields(CredentialOperatorAttestationV1)) == _OPERATOR_FIELDS
    assert tuple(field.name for field in fields(CredentialIndependentReviewerApprovalV1)) == _REVIEWER_FIELDS
    assert tuple(field.name for field in fields(CredentialOnboardingFailureV1)) == _FAILURE_FIELDS
    assert tuple(field.name for field in fields(CredentialOnboardingDecisionV1)) == _DECISION_FIELDS
    assert tuple(field.name for field in fields(CredentialOnboardingAuditEvidenceV1)) == _AUDIT_FIELDS
    records = (
        _policy(), _target(), _checklist(), _operator(), _reviewer(),
        CredentialOnboardingFailureV1("SAFE", "redacted metadata only", False), _decision(),
    )
    for record in records:
        _frozen(record)
    all_fields = tuple(field.name for record_type in (
        CredentialOnboardingSecurityPolicyV1, CredentialSecretTargetV1,
        CredentialOnboardingChecklistV1, CredentialOperatorAttestationV1,
        CredentialIndependentReviewerApprovalV1, CredentialOnboardingDecisionV1,
        CredentialOnboardingAuditEvidenceV1,
    ) for field in fields(record_type))
    assert set(all_fields).isdisjoint(_PROHIBITED_FIELD_NAMES)


def test_locked_targets_bind_only_the_two_authorized_providers_and_models() -> None:
    assert _target().provider_id == "DEEPSEEK"
    assert _target().credential_label == "DEEPSEEK_API_KEY"
    assert _target().routing_levels == ("L0",)
    assert _target().exact_provider_model_ids == ("deepseek-v4-pro",)
    anthropic = _target(
        secret_target_id="anthropic-secret-target-v1", provider_id="ANTHROPIC",
        credential_label="ANTHROPIC_API_KEY", routing_levels=("L1", "L2"),
        exact_provider_model_ids=("claude-sonnet-5", "claude-opus-4-8"),
    )
    assert anthropic.provider_id == "ANTHROPIC"
    assert anthropic.credential_label == "ANTHROPIC_API_KEY"
    assert anthropic.routing_levels == ("L1", "L2")
    assert anthropic.exact_provider_model_ids == ("claude-sonnet-5", "claude-opus-4-8")


def test_ready_means_procedure_only_and_all_non_onboarding_authorities_remain_false() -> None:
    decision = _decision()
    assert decision.ready is True
    assert decision.onboarding_state == "ONBOARDING_PROCEDURE_DEFINED"
    assert decision.state_codes == (
        "ONBOARDING_PROCEDURE_DEFINED", "SECRET_TARGET_READY", "OWNER_SECRET_ENTRY_PENDING",
        "CREDENTIAL_LOADING_NOT_AUTHORIZED", "PROVIDER_VALIDATION_NOT_AUTHORIZED",
        "NETWORK_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    )
    assert decision.supported_state_codes == _STATES
    assert decision.credential_onboarding_authorized is True
    assert decision.credential_value_access_authorized is False
    assert decision.credential_loading_authorized is False
    assert decision.credential_validation_authorized is False
    assert decision.network_authorized is False
    assert decision.provider_transmission_authorized is False
    assert decision.runtime_activation_authorized is False
    assert decision.runtime_configuration_authorized is False
    assert decision.publication_authorized is False
    assert decision.fail_closed is True
    assert decision.failure_codes == ()


@pytest.mark.parametrize(
    ("change", "failure_code"),
    (
        ({"policy_id": ""}, "POLICY_ID_EMPTY"),
        ({"policy_version": ""}, "POLICY_VERSION_EMPTY"),
        ({"deployment_environment": ""}, "DEPLOYMENT_ENVIRONMENT_EMPTY"),
        ({"onboarding_authorization_confirmed": False}, "ONBOARDING_NOT_AUTHORIZED"),
    ),
)
def test_policy_failures_are_closed_and_deterministic(change: dict[str, object], failure_code: str) -> None:
    decision = _decision(**change)
    assert decision.ready is False
    assert decision.onboarding_state == "ONBOARDING_BLOCKED"
    assert decision.failure_codes == (failure_code,)
    assert decision.fail_closed is True


@pytest.mark.parametrize(
    ("target_change", "checklist_change", "failure_code"),
    (
        ({"provider_id": "UNSUPPORTED"}, {"provider_id": "UNSUPPORTED"}, "PROVIDER_NOT_ALLOWED"),
        ({"routing_levels": ("L1",)}, {"routing_levels": ("L1",)}, "ROUTING_LEVEL_MISMATCH"),
        ({"exact_provider_model_ids": ("other-model",)}, {"exact_provider_model_ids": ("other-model",)}, "EXACT_MODEL_ID_MISMATCH"),
        ({"credential_label": ""}, {"credential_label": ""}, "CREDENTIAL_LABEL_EMPTY"),
        ({}, {"credential_label_not_shared": False}, "CREDENTIAL_LABEL_SHARED"),
        ({}, {"credential_material_supplied": True}, "RAW_CREDENTIAL_VALUE_PROVIDED"),
        ({}, {"credential_fingerprint_supplied": True}, "RAW_CREDENTIAL_FINGERPRINT_PROVIDED"),
        ({"target_outside_repository": False}, {}, "SECRET_TARGET_INSIDE_REPOSITORY"),
        ({"target_may_be_committed": True}, {}, "SECRET_TARGET_COMMITTABLE"),
        ({"git_ignore_protection_confirmed": False}, {}, "GIT_IGNORE_PROTECTION_REQUIRED"),
        ({"permissions_restrictive": False}, {}, "RESTRICTIVE_PERMISSION_REQUIRED"),
    ),
)
def test_target_and_binding_failures_are_closed(
    target_change: dict[str, object], checklist_change: dict[str, object], failure_code: str,
) -> None:
    decision = evaluate_credential_onboarding_v1(
        policy=_policy(), secret_target=_target(**target_change), checklist=_checklist(**checklist_change),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)
    assert decision.fail_closed is True


def test_missing_secret_target_is_a_normal_fail_closed_rejection() -> None:
    decision = evaluate_credential_onboarding_v1(
        policy=_policy(), secret_target=None, checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == ("SECRET_TARGET_REQUIRED",)
    assert decision.failures[0].safe_message == "secret target metadata is required"


@pytest.mark.parametrize(
    ("change", "failure_code"),
    (
        ({"shell_history_exposure_prevented": False}, "SHELL_HISTORY_EXPOSURE_RISK"),
        ({"command_line_argument_exposure_prevented": False}, "PROCESS_ARGUMENT_EXPOSURE_RISK"),
        ({"stdout_exposure_prevented": False}, "STDOUT_EXPOSURE_RISK"),
        ({"stderr_exposure_prevented": False}, "STDERR_EXPOSURE_RISK"),
        ({"log_exposure_prevented": False}, "LOG_EXPOSURE_RISK"),
        ({"test_fixture_exposure_prevented": False}, "TEST_FIXTURE_EXPOSURE_RISK"),
        ({"audit_evidence_exposure_prevented": False}, "AUDIT_EVIDENCE_EXPOSURE_RISK"),
        ({"environment_dump_prevented": False}, "ENVIRONMENT_DUMP_NOT_AUTHORIZED"),
        ({"clipboard_cleanup_confirmed": False}, "CLIPBOARD_CLEANUP_REQUIRED"),
        ({"rotation_procedure_defined": False}, "ROTATION_PROCEDURE_REQUIRED"),
        ({"revocation_capability_confirmed": False}, "REVOCATION_PROCEDURE_REQUIRED"),
        ({"rollback_procedure_defined": False}, "ROLLBACK_PROCEDURE_REQUIRED"),
        ({"deletion_procedure_defined": False}, "DELETION_PROCEDURE_REQUIRED"),
        ({"exception_detail_supplied": True}, "RAW_EXCEPTION_EXPOSURE_DETECTED"),
    ),
)
def test_exposure_and_lifecycle_failures_are_closed(change: dict[str, object], failure_code: str) -> None:
    decision = evaluate_credential_onboarding_v1(
        policy=_policy(), secret_target=_target(), checklist=_checklist(**change),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)
    assert decision.fail_closed is True


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
def test_operator_and_reviewer_evidence_is_required_independent_and_fresh(
    operator: CredentialOperatorAttestationV1 | None,
    reviewer: CredentialIndependentReviewerApprovalV1 | None,
    at: datetime,
    failure_code: str,
) -> None:
    decision = evaluate_credential_onboarding_v1(
        policy=_policy(), secret_target=_target(), checklist=_checklist(),
        operator_attestation=operator, reviewer_approval=reviewer, evaluation_at=at,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)


@pytest.mark.parametrize(
    ("change", "failure_code"),
    (
        ({"credential_value_access_attempted": True}, "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED"),
        ({"credential_loading_attempted": True}, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ({"provider_validation_attempted": True}, "CREDENTIAL_VALIDATION_NOT_AUTHORIZED"),
        ({"network_attempted": True}, "NETWORK_NOT_AUTHORIZED"),
        ({"provider_transmission_attempted": True}, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        ({"runtime_activation_attempted": True}, "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ({"runtime_configuration_attempted": True}, "RUNTIME_CONFIGURATION_NOT_AUTHORIZED"),
        ({"publication_attempted": True}, "PUBLICATION_NOT_AUTHORIZED"),
    ),
)
def test_every_prohibited_activity_fails_closed(change: dict[str, object], failure_code: str) -> None:
    decision = evaluate_credential_onboarding_v1(
        policy=_policy(), secret_target=_target(), checklist=_checklist(**change),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)
    assert decision.credential_onboarding_authorized is True
    assert not any((
        decision.credential_value_access_authorized, decision.credential_loading_authorized,
        decision.credential_validation_authorized, decision.network_authorized,
        decision.provider_transmission_authorized, decision.runtime_activation_authorized,
        decision.runtime_configuration_authorized, decision.publication_authorized,
    ))


def test_multiple_rejections_use_canonical_failure_order_and_immutable_safe_failures() -> None:
    decision = evaluate_credential_onboarding_v1(
        policy=_policy(onboarding_authorization_confirmed=False),
        secret_target=_target(target_outside_repository=False),
        checklist=_checklist(credential_material_supplied=True, network_attempted=True),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (
        "ONBOARDING_NOT_AUTHORIZED", "RAW_CREDENTIAL_VALUE_PROVIDED",
        "SECRET_TARGET_INSIDE_REPOSITORY", "NETWORK_NOT_AUTHORIZED",
    )
    assert tuple(failure.failure_code for failure in decision.failures) == decision.failure_codes
    assert all(is_dataclass(failure) and type(failure).__dataclass_params__.frozen for failure in decision.failures)
    assert all("credential" not in failure.safe_message.lower() or "value" not in failure.safe_message.lower()
               for failure in decision.failures)


def test_audit_evidence_is_redacted_immutable_and_preserves_only_metadata() -> None:
    decision = _decision()
    evidence = build_credential_onboarding_audit_evidence_v1(
        evidence_id="credential-onboarding-evidence-v1", decision=decision,
        policy=_policy(), secret_target=_target(), checklist=_checklist(),
        operator_attestation=_operator(), reviewer_approval=_reviewer(), evidence_at=_NOW,
    )
    _frozen(evidence)
    assert evidence.policy_id == "credential-onboarding-policy-v1"
    assert evidence.provider_id == "DEEPSEEK"
    assert evidence.credential_label == "DEEPSEEK_API_KEY"
    assert evidence.evidence_freshness == "FRESH"
    assert evidence.failure_codes == ()
    assert evidence.credential_onboarding_authorized is True
    assert not any((
        evidence.credential_value_access_authorized, evidence.credential_loading_authorized,
        evidence.credential_validation_authorized, evidence.network_authorized,
        evidence.provider_transmission_authorized, evidence.runtime_activation_authorized,
        evidence.runtime_configuration_authorized, evidence.publication_authorized,
    ))
    assert all(term not in repr(evidence).lower() for term in ("authorization_header", "cookie", "stack_trace"))


def test_complete_canonical_failure_vocabulary_is_frozen() -> None:
    assert _FAILURES == (
        "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
        "ONBOARDING_NOT_AUTHORIZED", "PROVIDER_NOT_ALLOWED", "ROUTING_LEVEL_MISMATCH",
        "EXACT_MODEL_ID_MISMATCH", "CREDENTIAL_LABEL_EMPTY", "CREDENTIAL_LABEL_SHARED",
        "RAW_CREDENTIAL_VALUE_PROVIDED", "RAW_CREDENTIAL_FINGERPRINT_PROVIDED",
        "SECRET_TARGET_REQUIRED", "SECRET_TARGET_INSIDE_REPOSITORY", "SECRET_TARGET_COMMITTABLE",
        "GIT_IGNORE_PROTECTION_REQUIRED", "RESTRICTIVE_PERMISSION_REQUIRED",
        "SHELL_HISTORY_EXPOSURE_RISK", "PROCESS_ARGUMENT_EXPOSURE_RISK", "STDOUT_EXPOSURE_RISK",
        "STDERR_EXPOSURE_RISK", "LOG_EXPOSURE_RISK", "TEST_FIXTURE_EXPOSURE_RISK",
        "AUDIT_EVIDENCE_EXPOSURE_RISK", "ENVIRONMENT_DUMP_NOT_AUTHORIZED",
        "CLIPBOARD_CLEANUP_REQUIRED", "ROTATION_PROCEDURE_REQUIRED",
        "REVOCATION_PROCEDURE_REQUIRED", "ROLLBACK_PROCEDURE_REQUIRED",
        "DELETION_PROCEDURE_REQUIRED", "OPERATOR_ATTESTATION_REQUIRED",
        "REVIEWER_APPROVAL_REQUIRED", "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE",
        "EVIDENCE_STALE", "EVIDENCE_EXPIRED", "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED",
        "CREDENTIAL_LOADING_NOT_AUTHORIZED", "CREDENTIAL_VALIDATION_NOT_AUTHORIZED",
        "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "RUNTIME_CONFIGURATION_NOT_AUTHORIZED",
        "PUBLICATION_NOT_AUTHORIZED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
    )


def test_complete_onboarding_state_vocabulary_is_frozen() -> None:
    assert _STATES == (
        "ONBOARDING_PROCEDURE_DEFINED", "SECRET_TARGET_READY", "OWNER_SECRET_ENTRY_PENDING",
        "SECRET_PLACEMENT_ATTESTED_REDACTED", "INDEPENDENT_REVIEW_COMPLETE",
        "CREDENTIAL_PRESENT_BUT_NOT_LOADED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
        "PROVIDER_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "REVOKED", "ROTATION_REQUIRED", "ONBOARDING_BLOCKED",
    )
