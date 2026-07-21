"""RED contract for the metadata-only Phase 12 systemd credential-placement procedure."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from engine.phase_12_systemd_credential_store_target_placement_procedure_contract_v1 import (
    SystemdCredentialIndependentReviewerApprovalV1,
    SystemdCredentialOwnerEntryAttestationV1,
    SystemdCredentialPlacementAuditEvidenceV1,
    SystemdCredentialPlacementChecklistV1,
    SystemdCredentialPlacementDecisionV1,
    SystemdCredentialPlacementFailureV1,
    SystemdCredentialStorePolicyV1,
    SystemdCredentialTargetV1,
    build_systemd_credential_placement_audit_evidence_v1,
    evaluate_systemd_credential_placement_v1,
)


_NOW = datetime(2030, 1, 8, 12, 0, tzinfo=UTC)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "deployment_environment", "secret_store_selection",
    "systemd_credentials_selected", "require_provider_separation", "require_distinct_credential_names",
    "require_repository_exclusion", "require_git_history_exclusion",
    "require_shell_history_exclusion", "require_process_argument_exclusion",
    "require_environment_dump_exclusion", "require_stdout_exclusion", "require_stderr_exclusion",
    "require_log_exclusion", "require_test_fixture_exclusion", "require_audit_evidence_exclusion",
    "require_backup_exclusion", "require_screenshot_exclusion", "require_clipboard_cleanup",
    "require_restrictive_ownership", "require_restrictive_permission",
    "require_encryption_at_rest", "require_rollback", "require_deletion", "require_rotation",
    "require_revocation", "require_independent_reviewer", "evidence_max_age_seconds", "fail_closed",
)
_TARGET_FIELDS = (
    "target_id", "policy_id", "provider_id", "logical_credential_label", "systemd_credential_name",
    "service_unit_identity", "deployment_environment", "routing_levels", "exact_provider_model_ids",
    "secret_source_classification", "secret_destination_classification", "encrypted_at_rest_required",
    "provider_separation_confirmed", "repository_exclusion_confirmed",
    "git_history_exclusion_confirmed", "shell_history_exclusion_confirmed",
    "process_argument_exclusion_confirmed", "environment_dump_exclusion_confirmed",
    "stdout_exclusion_confirmed", "stderr_exclusion_confirmed", "log_exclusion_confirmed",
    "test_fixture_exclusion_confirmed", "audit_evidence_exclusion_confirmed",
    "backup_exclusion_confirmed", "screenshot_exclusion_confirmed", "clipboard_cleanup_required",
    "restrictive_ownership_required", "restrictive_permission_required", "rollback_ready",
    "deletion_ready", "rotation_ready", "revocation_ready", "target_ready",
)
_CHECKLIST_FIELDS = (
    "checklist_id", "policy_id", "target_id", "provider_id", "logical_credential_label",
    "systemd_credential_name", "service_unit_identity", "routing_levels", "exact_provider_model_ids",
    "systemd_selection_confirmed", "provider_separation_confirmed", "credential_name_distinct",
    "repository_exclusion_confirmed", "git_history_exclusion_confirmed",
    "shell_history_exclusion_confirmed", "process_argument_exclusion_confirmed",
    "environment_dump_exclusion_confirmed", "stdout_exclusion_confirmed",
    "stderr_exclusion_confirmed", "log_exclusion_confirmed", "test_fixture_exclusion_confirmed",
    "audit_evidence_exclusion_confirmed", "backup_exclusion_confirmed",
    "screenshot_exclusion_confirmed", "clipboard_cleanup_confirmed",
    "restrictive_ownership_confirmed", "restrictive_permission_confirmed",
    "encryption_at_rest_confirmed", "rollback_ready", "deletion_ready", "rotation_ready",
    "revocation_ready", "raw_credential_material_supplied", "credential_derived_material_supplied",
    "raw_exception_detail_supplied", "owner_secret_entry_claimed_completed",
    "credential_value_access_attempted", "credential_loading_attempted",
    "provider_validation_attempted", "network_attempted", "provider_transmission_attempted",
    "runtime_activation_attempted", "runtime_configuration_attempted", "publication_attempted",
    "owner_secret_entry_authorized", "prohibited_authority_claimed",
)
_OPERATOR_FIELDS = (
    "attestation_id", "policy_id", "target_id", "checklist_id", "operator_id", "operator_role",
    "attested_at", "owner_secret_entry_pending", "owner_secret_entry_completed",
    "secret_placement_attested_redacted", "sensitive_material_retained", "attestation_complete",
)
_REVIEWER_FIELDS = (
    "approval_id", "policy_id", "target_id", "checklist_id", "attestation_id", "reviewer_id",
    "reviewer_role", "approved_at", "independent_review_complete", "redacted_evidence_only",
    "placement_procedure_approved", "sensitive_material_retained", "review_complete",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_DECISION_FIELDS = (
    "policy_id", "provider_id", "logical_credential_label", "systemd_credential_name",
    "service_unit_identity", "routing_levels", "exact_provider_model_ids", "ready", "placement_state",
    "state_codes", "supported_state_codes", "failure_codes", "failures",
    "credential_onboarding_authorized", "systemd_target_definition_authorized",
    "owner_secret_entry_authorized", "credential_value_access_authorized",
    "credential_loading_authorized", "credential_validation_authorized", "network_authorized",
    "provider_transmission_authorized", "runtime_activation_authorized",
    "runtime_configuration_authorized", "publication_authorized", "fail_closed",
)
_AUDIT_FIELDS = (
    "evidence_id", "policy_id", "policy_version", "provider_id", "logical_credential_label",
    "systemd_credential_name", "service_unit_identity", "routing_levels", "exact_provider_model_ids",
    "systemd_selection_confirmed", "repository_exclusion_confirmed",
    "git_history_exclusion_confirmed", "exposure_controls_ready", "restrictive_ownership_ready",
    "restrictive_permission_ready", "encryption_at_rest_ready", "clipboard_cleanup_ready",
    "rollback_ready", "deletion_ready", "rotation_ready", "revocation_ready", "operator_id",
    "operator_role", "reviewer_id", "reviewer_role", "evidence_freshness", "failure_codes",
    "credential_onboarding_authorized", "systemd_target_definition_authorized",
    "owner_secret_entry_authorized", "credential_value_access_authorized",
    "credential_loading_authorized", "credential_validation_authorized", "network_authorized",
    "provider_transmission_authorized", "runtime_activation_authorized",
    "runtime_configuration_authorized", "publication_authorized", "fail_closed",
)
_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "SECRET_STORE_SELECTION_MISMATCH", "PROVIDER_NOT_ALLOWED", "ROUTING_LEVEL_MISMATCH",
    "EXACT_MODEL_ID_MISMATCH", "LOGICAL_CREDENTIAL_LABEL_EMPTY",
    "LOGICAL_CREDENTIAL_LABEL_SHARED", "SYSTEMD_CREDENTIAL_NAME_EMPTY",
    "SYSTEMD_CREDENTIAL_NAME_SHARED", "SERVICE_UNIT_IDENTITY_REQUIRED",
    "RAW_CREDENTIAL_VALUE_PROVIDED", "RAW_CREDENTIAL_DERIVED_MATERIAL_PROVIDED",
    "REPOSITORY_EXCLUSION_REQUIRED", "GIT_HISTORY_EXCLUSION_REQUIRED",
    "SHELL_HISTORY_EXCLUSION_REQUIRED", "PROCESS_ARGUMENT_EXCLUSION_REQUIRED",
    "ENVIRONMENT_DUMP_EXCLUSION_REQUIRED", "STDOUT_EXCLUSION_REQUIRED",
    "STDERR_EXCLUSION_REQUIRED", "LOG_EXCLUSION_REQUIRED", "TEST_FIXTURE_EXCLUSION_REQUIRED",
    "AUDIT_EVIDENCE_EXCLUSION_REQUIRED", "BACKUP_EXCLUSION_REQUIRED",
    "SCREENSHOT_EXCLUSION_REQUIRED", "CLIPBOARD_CLEANUP_REQUIRED",
    "RESTRICTIVE_OWNERSHIP_REQUIRED", "RESTRICTIVE_PERMISSION_REQUIRED",
    "ENCRYPTION_AT_REST_REQUIRED", "ROLLBACK_PROCEDURE_REQUIRED", "DELETION_PROCEDURE_REQUIRED",
    "ROTATION_PROCEDURE_REQUIRED", "REVOCATION_PROCEDURE_REQUIRED",
    "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED",
    "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE",
    "EVIDENCE_EXPIRED", "OWNER_SECRET_ENTRY_NOT_AUTHORIZED",
    "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "CREDENTIAL_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    "RUNTIME_CONFIGURATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED",
)
_STATES = (
    "SYSTEMD_CREDENTIAL_TARGET_DEFINED", "OWNER_SECRET_ENTRY_PENDING",
    "OWNER_SECRET_ENTRY_AUTHORIZED_SEPARATELY", "SECRET_PLACEMENT_ATTESTED_REDACTED",
    "INDEPENDENT_REVIEW_COMPLETE", "CREDENTIAL_PRESENT_BUT_NOT_LOADED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "PROVIDER_VALIDATION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "ROTATION_REQUIRED", "REVOKED", "PLACEMENT_BLOCKED",
)
_PROHIBITED_FIELD_NAMES = (
    "value", "secret_value", "api_key", "token", "password", "credential_length",
    "credential_prefix", "credential_suffix", "credential_hash", "fingerprint",
    "authorization_header", "cookie", "account_identity", "organization_identity",
    "workspace_identity", "project_identity", "provider_response", "secret_contents",
    "environment_value", "exception_text", "stack_trace",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> SystemdCredentialStorePolicyV1:
    values = dict(
        policy_id="systemd-placement-policy-v1", policy_version="V1",
        deployment_environment="CONTROLLED_PRODUCTION", secret_store_selection="SYSTEMD_CREDENTIALS",
        systemd_credentials_selected=True, require_provider_separation=True,
        require_distinct_credential_names=True, require_repository_exclusion=True,
        require_git_history_exclusion=True, require_shell_history_exclusion=True,
        require_process_argument_exclusion=True, require_environment_dump_exclusion=True,
        require_stdout_exclusion=True, require_stderr_exclusion=True, require_log_exclusion=True,
        require_test_fixture_exclusion=True, require_audit_evidence_exclusion=True,
        require_backup_exclusion=True, require_screenshot_exclusion=True,
        require_clipboard_cleanup=True, require_restrictive_ownership=True,
        require_restrictive_permission=True, require_encryption_at_rest=True,
        require_rollback=True, require_deletion=True, require_rotation=True, require_revocation=True,
        require_independent_reviewer=True, evidence_max_age_seconds=3600, fail_closed=True,
    )
    return SystemdCredentialStorePolicyV1(**(values | overrides))


def _target(**overrides: object) -> SystemdCredentialTargetV1:
    values = dict(
        target_id="deepseek-systemd-target-v1", policy_id="systemd-placement-policy-v1",
        provider_id="DEEPSEEK", logical_credential_label="DEEPSEEK_API_KEY",
        systemd_credential_name="deepseek_api_key", service_unit_identity="signal-agent.service",
        deployment_environment="CONTROLLED_PRODUCTION", routing_levels=("L0",),
        exact_provider_model_ids=("deepseek-v4-pro",),
        secret_source_classification="OWNER_ENTRY_OUTSIDE_AGENT",
        secret_destination_classification="SYSTEMD_CREDENTIAL_STORE_REFERENCE_ONLY",
        encrypted_at_rest_required=True, provider_separation_confirmed=True,
        repository_exclusion_confirmed=True, git_history_exclusion_confirmed=True,
        shell_history_exclusion_confirmed=True, process_argument_exclusion_confirmed=True,
        environment_dump_exclusion_confirmed=True, stdout_exclusion_confirmed=True,
        stderr_exclusion_confirmed=True, log_exclusion_confirmed=True,
        test_fixture_exclusion_confirmed=True, audit_evidence_exclusion_confirmed=True,
        backup_exclusion_confirmed=True, screenshot_exclusion_confirmed=True,
        clipboard_cleanup_required=True, restrictive_ownership_required=True,
        restrictive_permission_required=True, rollback_ready=True, deletion_ready=True,
        rotation_ready=True, revocation_ready=True, target_ready=True,
    )
    return SystemdCredentialTargetV1(**(values | overrides))


def _checklist(**overrides: object) -> SystemdCredentialPlacementChecklistV1:
    values = dict(
        checklist_id="systemd-placement-checklist-v1", policy_id="systemd-placement-policy-v1",
        target_id="deepseek-systemd-target-v1", provider_id="DEEPSEEK",
        logical_credential_label="DEEPSEEK_API_KEY", systemd_credential_name="deepseek_api_key",
        service_unit_identity="signal-agent.service", routing_levels=("L0",),
        exact_provider_model_ids=("deepseek-v4-pro",), systemd_selection_confirmed=True,
        provider_separation_confirmed=True, credential_name_distinct=True,
        repository_exclusion_confirmed=True, git_history_exclusion_confirmed=True,
        shell_history_exclusion_confirmed=True, process_argument_exclusion_confirmed=True,
        environment_dump_exclusion_confirmed=True, stdout_exclusion_confirmed=True,
        stderr_exclusion_confirmed=True, log_exclusion_confirmed=True,
        test_fixture_exclusion_confirmed=True, audit_evidence_exclusion_confirmed=True,
        backup_exclusion_confirmed=True, screenshot_exclusion_confirmed=True,
        clipboard_cleanup_confirmed=True, restrictive_ownership_confirmed=True,
        restrictive_permission_confirmed=True, encryption_at_rest_confirmed=True,
        rollback_ready=True, deletion_ready=True, rotation_ready=True, revocation_ready=True,
        raw_credential_material_supplied=False, credential_derived_material_supplied=False,
        raw_exception_detail_supplied=False, owner_secret_entry_claimed_completed=False,
        credential_value_access_attempted=False, credential_loading_attempted=False,
        provider_validation_attempted=False, network_attempted=False,
        provider_transmission_attempted=False, runtime_activation_attempted=False,
        runtime_configuration_attempted=False, publication_attempted=False,
        owner_secret_entry_authorized=False, prohibited_authority_claimed=False,
    )
    return SystemdCredentialPlacementChecklistV1(**(values | overrides))


def _operator(**overrides: object) -> SystemdCredentialOwnerEntryAttestationV1:
    values = dict(
        attestation_id="owner-entry-attestation-v1", policy_id="systemd-placement-policy-v1",
        target_id="deepseek-systemd-target-v1", checklist_id="systemd-placement-checklist-v1",
        operator_id="operator-1", operator_role="REDACTED_PLACEMENT_OPERATOR",
        attested_at=_NOW - timedelta(minutes=5), owner_secret_entry_pending=True,
        owner_secret_entry_completed=False, secret_placement_attested_redacted=False,
        sensitive_material_retained=False, attestation_complete=True,
    )
    return SystemdCredentialOwnerEntryAttestationV1(**(values | overrides))


def _reviewer(**overrides: object) -> SystemdCredentialIndependentReviewerApprovalV1:
    values = dict(
        approval_id="independent-review-v1", policy_id="systemd-placement-policy-v1",
        target_id="deepseek-systemd-target-v1", checklist_id="systemd-placement-checklist-v1",
        attestation_id="owner-entry-attestation-v1", reviewer_id="reviewer-1",
        reviewer_role="INDEPENDENT_SECURITY_REVIEWER", approved_at=_NOW - timedelta(minutes=4),
        independent_review_complete=True, redacted_evidence_only=True,
        placement_procedure_approved=True, sensitive_material_retained=False, review_complete=True,
    )
    return SystemdCredentialIndependentReviewerApprovalV1(**(values | overrides))


def _decision(**overrides: object) -> SystemdCredentialPlacementDecisionV1:
    return evaluate_systemd_credential_placement_v1(
        policy=_policy(**overrides), target=_target(), checklist=_checklist(),
        owner_entry_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )


def test_public_contract_is_immutable_metadata_only_and_has_no_secret_value_field() -> None:
    assert tuple(field.name for field in fields(SystemdCredentialStorePolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(SystemdCredentialTargetV1)) == _TARGET_FIELDS
    assert tuple(field.name for field in fields(SystemdCredentialPlacementChecklistV1)) == _CHECKLIST_FIELDS
    assert tuple(field.name for field in fields(SystemdCredentialOwnerEntryAttestationV1)) == _OPERATOR_FIELDS
    assert tuple(field.name for field in fields(SystemdCredentialIndependentReviewerApprovalV1)) == _REVIEWER_FIELDS
    assert tuple(field.name for field in fields(SystemdCredentialPlacementFailureV1)) == _FAILURE_FIELDS
    assert tuple(field.name for field in fields(SystemdCredentialPlacementDecisionV1)) == _DECISION_FIELDS
    assert tuple(field.name for field in fields(SystemdCredentialPlacementAuditEvidenceV1)) == _AUDIT_FIELDS
    for record in (_policy(), _target(), _checklist(), _operator(), _reviewer(), _decision()):
        _frozen(record)
    all_fields = tuple(field.name for record_type in (
        SystemdCredentialStorePolicyV1, SystemdCredentialTargetV1,
        SystemdCredentialPlacementChecklistV1, SystemdCredentialOwnerEntryAttestationV1,
        SystemdCredentialIndependentReviewerApprovalV1, SystemdCredentialPlacementDecisionV1,
        SystemdCredentialPlacementAuditEvidenceV1,
    ) for field in fields(record_type))
    assert set(all_fields).isdisjoint(_PROHIBITED_FIELD_NAMES)


def test_locked_systemd_bindings_are_provider_specific_and_distinct() -> None:
    assert (_target().provider_id, _target().logical_credential_label, _target().systemd_credential_name) == (
        "DEEPSEEK", "DEEPSEEK_API_KEY", "deepseek_api_key",
    )
    assert _target().routing_levels == ("L0",)
    assert _target().exact_provider_model_ids == ("deepseek-v4-pro",)
    anthropic = _target(
        target_id="anthropic-systemd-target-v1", provider_id="ANTHROPIC",
        logical_credential_label="ANTHROPIC_API_KEY", systemd_credential_name="anthropic_api_key",
        routing_levels=("L1", "L2"), exact_provider_model_ids=("claude-sonnet-5", "claude-opus-4-8"),
    )
    assert (anthropic.provider_id, anthropic.logical_credential_label, anthropic.systemd_credential_name) == (
        "ANTHROPIC", "ANTHROPIC_API_KEY", "anthropic_api_key",
    )
    assert anthropic.systemd_credential_name != _target().systemd_credential_name


def test_ready_means_only_procedure_definition_and_preserves_authority_boundary() -> None:
    decision = _decision()
    assert decision.ready is True
    assert decision.placement_state == "SYSTEMD_CREDENTIAL_TARGET_DEFINED"
    assert decision.state_codes == (
        "SYSTEMD_CREDENTIAL_TARGET_DEFINED", "OWNER_SECRET_ENTRY_PENDING",
        "CREDENTIAL_LOADING_NOT_AUTHORIZED", "PROVIDER_VALIDATION_NOT_AUTHORIZED",
        "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
    )
    assert decision.supported_state_codes == _STATES
    assert decision.credential_onboarding_authorized is True
    assert decision.systemd_target_definition_authorized is True
    assert not any((
        decision.owner_secret_entry_authorized, decision.credential_value_access_authorized,
        decision.credential_loading_authorized, decision.credential_validation_authorized,
        decision.network_authorized, decision.provider_transmission_authorized,
        decision.runtime_activation_authorized, decision.runtime_configuration_authorized,
        decision.publication_authorized,
    ))
    assert decision.fail_closed is True
    assert decision.failure_codes == ()


@pytest.mark.parametrize(
    ("change", "failure_code"),
    (
        ({"policy_id": ""}, "POLICY_ID_EMPTY"),
        ({"policy_version": ""}, "POLICY_VERSION_EMPTY"),
        ({"deployment_environment": ""}, "DEPLOYMENT_ENVIRONMENT_EMPTY"),
        ({"secret_store_selection": "OTHER_STORE"}, "SECRET_STORE_SELECTION_MISMATCH"),
    ),
)
def test_policy_rejections_are_normal_and_deterministic(change: dict[str, object], failure_code: str) -> None:
    decision = _decision(**change)
    assert decision.ready is False
    assert decision.placement_state == "PLACEMENT_BLOCKED"
    assert decision.failure_codes == (failure_code,)
    assert decision.fail_closed is True


@pytest.mark.parametrize(
    ("target_change", "checklist_change", "failure_code"),
    (
        ({"provider_id": "UNSUPPORTED"}, {"provider_id": "UNSUPPORTED"}, "PROVIDER_NOT_ALLOWED"),
        ({"routing_levels": ("L1",)}, {"routing_levels": ("L1",)}, "ROUTING_LEVEL_MISMATCH"),
        ({"exact_provider_model_ids": ("other-model",)}, {"exact_provider_model_ids": ("other-model",)}, "EXACT_MODEL_ID_MISMATCH"),
        ({"logical_credential_label": ""}, {"logical_credential_label": ""}, "LOGICAL_CREDENTIAL_LABEL_EMPTY"),
        ({}, {"credential_name_distinct": False}, "LOGICAL_CREDENTIAL_LABEL_SHARED"),
        ({"systemd_credential_name": ""}, {"systemd_credential_name": ""}, "SYSTEMD_CREDENTIAL_NAME_EMPTY"),
        ({"service_unit_identity": ""}, {"service_unit_identity": ""}, "SERVICE_UNIT_IDENTITY_REQUIRED"),
        ({}, {"raw_credential_material_supplied": True}, "RAW_CREDENTIAL_VALUE_PROVIDED"),
        ({}, {"credential_derived_material_supplied": True}, "RAW_CREDENTIAL_DERIVED_MATERIAL_PROVIDED"),
    ),
)
def test_binding_and_material_rejections_fail_closed(
    target_change: dict[str, object], checklist_change: dict[str, object], failure_code: str,
) -> None:
    decision = evaluate_systemd_credential_placement_v1(
        policy=_policy(), target=_target(**target_change), checklist=_checklist(**checklist_change),
        owner_entry_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)


@pytest.mark.parametrize(
    ("change", "failure_code"),
    (
        ({"repository_exclusion_confirmed": False}, "REPOSITORY_EXCLUSION_REQUIRED"),
        ({"git_history_exclusion_confirmed": False}, "GIT_HISTORY_EXCLUSION_REQUIRED"),
        ({"shell_history_exclusion_confirmed": False}, "SHELL_HISTORY_EXCLUSION_REQUIRED"),
        ({"process_argument_exclusion_confirmed": False}, "PROCESS_ARGUMENT_EXCLUSION_REQUIRED"),
        ({"environment_dump_exclusion_confirmed": False}, "ENVIRONMENT_DUMP_EXCLUSION_REQUIRED"),
        ({"stdout_exclusion_confirmed": False}, "STDOUT_EXCLUSION_REQUIRED"),
        ({"stderr_exclusion_confirmed": False}, "STDERR_EXCLUSION_REQUIRED"),
        ({"log_exclusion_confirmed": False}, "LOG_EXCLUSION_REQUIRED"),
        ({"test_fixture_exclusion_confirmed": False}, "TEST_FIXTURE_EXCLUSION_REQUIRED"),
        ({"audit_evidence_exclusion_confirmed": False}, "AUDIT_EVIDENCE_EXCLUSION_REQUIRED"),
        ({"backup_exclusion_confirmed": False}, "BACKUP_EXCLUSION_REQUIRED"),
        ({"screenshot_exclusion_confirmed": False}, "SCREENSHOT_EXCLUSION_REQUIRED"),
        ({"clipboard_cleanup_confirmed": False}, "CLIPBOARD_CLEANUP_REQUIRED"),
        ({"restrictive_ownership_confirmed": False}, "RESTRICTIVE_OWNERSHIP_REQUIRED"),
        ({"restrictive_permission_confirmed": False}, "RESTRICTIVE_PERMISSION_REQUIRED"),
        ({"encryption_at_rest_confirmed": False}, "ENCRYPTION_AT_REST_REQUIRED"),
        ({"rollback_ready": False}, "ROLLBACK_PROCEDURE_REQUIRED"),
        ({"deletion_ready": False}, "DELETION_PROCEDURE_REQUIRED"),
        ({"rotation_ready": False}, "ROTATION_PROCEDURE_REQUIRED"),
        ({"revocation_ready": False}, "REVOCATION_PROCEDURE_REQUIRED"),
        ({"raw_exception_detail_supplied": True}, "RAW_EXCEPTION_EXPOSURE_DETECTED"),
    ),
)
def test_target_safety_and_lifecycle_rejections_fail_closed(change: dict[str, object], failure_code: str) -> None:
    decision = evaluate_systemd_credential_placement_v1(
        policy=_policy(), target=_target(), checklist=_checklist(**change),
        owner_entry_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
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
def test_owner_and_reviewer_evidence_is_required_independent_and_fresh(
    operator: SystemdCredentialOwnerEntryAttestationV1 | None,
    reviewer: SystemdCredentialIndependentReviewerApprovalV1 | None,
    at: datetime,
    failure_code: str,
) -> None:
    decision = evaluate_systemd_credential_placement_v1(
        policy=_policy(), target=_target(), checklist=_checklist(), owner_entry_attestation=operator,
        reviewer_approval=reviewer, evaluation_at=at,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)


@pytest.mark.parametrize(
    ("change", "failure_code"),
    (
        ({"owner_secret_entry_claimed_completed": True}, "OWNER_SECRET_ENTRY_NOT_AUTHORIZED"),
        ({"owner_secret_entry_authorized": True}, "OWNER_SECRET_ENTRY_NOT_AUTHORIZED"),
        ({"credential_value_access_attempted": True}, "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED"),
        ({"credential_loading_attempted": True}, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ({"provider_validation_attempted": True}, "CREDENTIAL_VALIDATION_NOT_AUTHORIZED"),
        ({"network_attempted": True}, "NETWORK_NOT_AUTHORIZED"),
        ({"provider_transmission_attempted": True}, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        ({"runtime_activation_attempted": True}, "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ({"runtime_configuration_attempted": True}, "RUNTIME_CONFIGURATION_NOT_AUTHORIZED"),
        ({"publication_attempted": True}, "PUBLICATION_NOT_AUTHORIZED"),
        ({"prohibited_authority_claimed": True}, "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED"),
    ),
)
def test_owner_entry_and_all_prohibited_actions_fail_closed(change: dict[str, object], failure_code: str) -> None:
    decision = evaluate_systemd_credential_placement_v1(
        policy=_policy(), target=_target(), checklist=_checklist(**change),
        owner_entry_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.ready is False
    assert decision.failure_codes == (failure_code,)
    assert decision.credential_onboarding_authorized is True
    assert decision.systemd_target_definition_authorized is True
    assert not any((
        decision.owner_secret_entry_authorized, decision.credential_value_access_authorized,
        decision.credential_loading_authorized, decision.credential_validation_authorized,
        decision.network_authorized, decision.provider_transmission_authorized,
        decision.runtime_activation_authorized, decision.runtime_configuration_authorized,
        decision.publication_authorized,
    ))


def test_multiple_rejections_use_canonical_order_and_return_immutable_failures() -> None:
    decision = evaluate_systemd_credential_placement_v1(
        policy=_policy(secret_store_selection="OTHER_STORE"), target=_target(repository_exclusion_confirmed=False),
        checklist=_checklist(raw_credential_material_supplied=True, network_attempted=True),
        owner_entry_attestation=_operator(), reviewer_approval=_reviewer(), evaluation_at=_NOW,
    )
    assert decision.failure_codes == (
        "SECRET_STORE_SELECTION_MISMATCH", "RAW_CREDENTIAL_VALUE_PROVIDED",
        "REPOSITORY_EXCLUSION_REQUIRED", "NETWORK_NOT_AUTHORIZED",
    )
    assert tuple(failure.failure_code for failure in decision.failures) == decision.failure_codes
    assert all(is_dataclass(failure) and type(failure).__dataclass_params__.frozen for failure in decision.failures)


def test_redacted_audit_evidence_is_immutable_and_preserves_authority_boundary() -> None:
    evidence = build_systemd_credential_placement_audit_evidence_v1(
        evidence_id="systemd-placement-evidence-v1", decision=_decision(), policy=_policy(),
        target=_target(), checklist=_checklist(), owner_entry_attestation=_operator(),
        reviewer_approval=_reviewer(), evidence_at=_NOW,
    )
    _frozen(evidence)
    assert evidence.systemd_selection_confirmed is True
    assert evidence.provider_id == "DEEPSEEK"
    assert evidence.systemd_credential_name == "deepseek_api_key"
    assert evidence.evidence_freshness == "FRESH"
    assert evidence.failure_codes == ()
    assert evidence.credential_onboarding_authorized is True
    assert evidence.systemd_target_definition_authorized is True
    assert not any((
        evidence.owner_secret_entry_authorized, evidence.credential_value_access_authorized,
        evidence.credential_loading_authorized, evidence.credential_validation_authorized,
        evidence.network_authorized, evidence.provider_transmission_authorized,
        evidence.runtime_activation_authorized, evidence.runtime_configuration_authorized,
        evidence.publication_authorized,
    ))


def test_canonical_failure_and_state_vocabularies_are_frozen() -> None:
    assert _FAILURES == (
        "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
        "SECRET_STORE_SELECTION_MISMATCH", "PROVIDER_NOT_ALLOWED", "ROUTING_LEVEL_MISMATCH",
        "EXACT_MODEL_ID_MISMATCH", "LOGICAL_CREDENTIAL_LABEL_EMPTY",
        "LOGICAL_CREDENTIAL_LABEL_SHARED", "SYSTEMD_CREDENTIAL_NAME_EMPTY",
        "SYSTEMD_CREDENTIAL_NAME_SHARED", "SERVICE_UNIT_IDENTITY_REQUIRED",
        "RAW_CREDENTIAL_VALUE_PROVIDED", "RAW_CREDENTIAL_DERIVED_MATERIAL_PROVIDED",
        "REPOSITORY_EXCLUSION_REQUIRED", "GIT_HISTORY_EXCLUSION_REQUIRED",
        "SHELL_HISTORY_EXCLUSION_REQUIRED", "PROCESS_ARGUMENT_EXCLUSION_REQUIRED",
        "ENVIRONMENT_DUMP_EXCLUSION_REQUIRED", "STDOUT_EXCLUSION_REQUIRED",
        "STDERR_EXCLUSION_REQUIRED", "LOG_EXCLUSION_REQUIRED", "TEST_FIXTURE_EXCLUSION_REQUIRED",
        "AUDIT_EVIDENCE_EXCLUSION_REQUIRED", "BACKUP_EXCLUSION_REQUIRED",
        "SCREENSHOT_EXCLUSION_REQUIRED", "CLIPBOARD_CLEANUP_REQUIRED",
        "RESTRICTIVE_OWNERSHIP_REQUIRED", "RESTRICTIVE_PERMISSION_REQUIRED",
        "ENCRYPTION_AT_REST_REQUIRED", "ROLLBACK_PROCEDURE_REQUIRED",
        "DELETION_PROCEDURE_REQUIRED", "ROTATION_PROCEDURE_REQUIRED", "REVOCATION_PROCEDURE_REQUIRED",
        "OPERATOR_ATTESTATION_REQUIRED", "REVIEWER_APPROVAL_REQUIRED",
        "OPERATOR_REVIEWER_COLLISION", "EVIDENCE_FROM_FUTURE", "EVIDENCE_STALE",
        "EVIDENCE_EXPIRED", "OWNER_SECRET_ENTRY_NOT_AUTHORIZED",
        "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
        "CREDENTIAL_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
        "RUNTIME_CONFIGURATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
        "RAW_EXCEPTION_EXPOSURE_DETECTED",
    )
    assert _STATES == (
        "SYSTEMD_CREDENTIAL_TARGET_DEFINED", "OWNER_SECRET_ENTRY_PENDING",
        "OWNER_SECRET_ENTRY_AUTHORIZED_SEPARATELY", "SECRET_PLACEMENT_ATTESTED_REDACTED",
        "INDEPENDENT_REVIEW_COMPLETE", "CREDENTIAL_PRESENT_BUT_NOT_LOADED",
        "CREDENTIAL_LOADING_NOT_AUTHORIZED", "PROVIDER_VALIDATION_NOT_AUTHORIZED",
        "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "ROTATION_REQUIRED", "REVOKED", "PLACEMENT_BLOCKED",
    )
