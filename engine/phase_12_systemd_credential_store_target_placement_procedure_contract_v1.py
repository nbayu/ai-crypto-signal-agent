"""Pure metadata boundary for the Phase 12 systemd credential-placement procedure."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


_BINDINGS = (
    ("DEEPSEEK", "DEEPSEEK_API_KEY", "deepseek_api_key", ("L0",), ("deepseek-v4-pro",)),
    ("ANTHROPIC", "ANTHROPIC_API_KEY", "anthropic_api_key", ("L1", "L2"),
     ("claude-sonnet-5", "claude-opus-4-8")),
)
_STATES = (
    "SYSTEMD_CREDENTIAL_TARGET_DEFINED", "OWNER_SECRET_ENTRY_PENDING",
    "OWNER_SECRET_ENTRY_AUTHORIZED_SEPARATELY", "SECRET_PLACEMENT_ATTESTED_REDACTED",
    "INDEPENDENT_REVIEW_COMPLETE", "CREDENTIAL_PRESENT_BUT_NOT_LOADED",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "PROVIDER_VALIDATION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "ROTATION_REQUIRED", "REVOKED", "PLACEMENT_BLOCKED",
)
_FAILURE_ORDER = (
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
_MESSAGES = {
    "POLICY_ID_EMPTY": "policy identity is required",
    "POLICY_VERSION_EMPTY": "policy version is required",
    "DEPLOYMENT_ENVIRONMENT_EMPTY": "deployment environment is required",
    "SECRET_STORE_SELECTION_MISMATCH": "systemd credentials must be selected",
    "PROVIDER_NOT_ALLOWED": "provider metadata is not allowed",
    "ROUTING_LEVEL_MISMATCH": "routing metadata does not match the locked binding",
    "EXACT_MODEL_ID_MISMATCH": "model metadata does not match the locked binding",
    "LOGICAL_CREDENTIAL_LABEL_EMPTY": "logical credential label is required",
    "LOGICAL_CREDENTIAL_LABEL_SHARED": "logical credential label must be provider-specific",
    "SYSTEMD_CREDENTIAL_NAME_EMPTY": "systemd credential name is required",
    "SYSTEMD_CREDENTIAL_NAME_SHARED": "systemd credential name must be provider-specific",
    "SERVICE_UNIT_IDENTITY_REQUIRED": "service unit identity is required",
    "RAW_CREDENTIAL_VALUE_PROVIDED": "credential material is not accepted",
    "RAW_CREDENTIAL_DERIVED_MATERIAL_PROVIDED": "credential-derived material is not accepted",
    "REPOSITORY_EXCLUSION_REQUIRED": "repository exclusion is required",
    "GIT_HISTORY_EXCLUSION_REQUIRED": "git history exclusion is required",
    "SHELL_HISTORY_EXCLUSION_REQUIRED": "shell history exclusion is required",
    "PROCESS_ARGUMENT_EXCLUSION_REQUIRED": "process argument exclusion is required",
    "ENVIRONMENT_DUMP_EXCLUSION_REQUIRED": "environment dump exclusion is required",
    "STDOUT_EXCLUSION_REQUIRED": "standard output exclusion is required",
    "STDERR_EXCLUSION_REQUIRED": "standard error exclusion is required",
    "LOG_EXCLUSION_REQUIRED": "log exclusion is required",
    "TEST_FIXTURE_EXCLUSION_REQUIRED": "test fixture exclusion is required",
    "AUDIT_EVIDENCE_EXCLUSION_REQUIRED": "audit evidence exclusion is required",
    "BACKUP_EXCLUSION_REQUIRED": "backup exclusion is required",
    "SCREENSHOT_EXCLUSION_REQUIRED": "screenshot exclusion is required",
    "CLIPBOARD_CLEANUP_REQUIRED": "clipboard cleanup is required",
    "RESTRICTIVE_OWNERSHIP_REQUIRED": "restrictive ownership is required",
    "RESTRICTIVE_PERMISSION_REQUIRED": "restrictive permission is required",
    "ENCRYPTION_AT_REST_REQUIRED": "encryption at rest is required",
    "ROLLBACK_PROCEDURE_REQUIRED": "rollback procedure is required",
    "DELETION_PROCEDURE_REQUIRED": "deletion procedure is required",
    "ROTATION_PROCEDURE_REQUIRED": "rotation procedure is required",
    "REVOCATION_PROCEDURE_REQUIRED": "revocation procedure is required",
    "OPERATOR_ATTESTATION_REQUIRED": "redacted operator attestation is required",
    "REVIEWER_APPROVAL_REQUIRED": "independent reviewer approval is required",
    "OPERATOR_REVIEWER_COLLISION": "operator and reviewer must be distinct",
    "EVIDENCE_FROM_FUTURE": "evidence must not be future-dated",
    "EVIDENCE_STALE": "operator evidence is stale",
    "EVIDENCE_EXPIRED": "reviewer evidence is expired",
    "OWNER_SECRET_ENTRY_NOT_AUTHORIZED": "owner secret entry is not authorized",
    "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED": "credential value access is not authorized",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED": "credential loading is not authorized",
    "CREDENTIAL_VALIDATION_NOT_AUTHORIZED": "credential validation is not authorized",
    "NETWORK_NOT_AUTHORIZED": "network access is not authorized",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED": "provider transmission is not authorized",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED": "runtime activation is not authorized",
    "RUNTIME_CONFIGURATION_NOT_AUTHORIZED": "runtime configuration is not authorized",
    "PUBLICATION_NOT_AUTHORIZED": "publication is not authorized",
    "RAW_EXCEPTION_EXPOSURE_DETECTED": "exception detail is not accepted",
}


@dataclass(frozen=True, slots=True)
class SystemdCredentialStorePolicyV1:
    policy_id: str
    policy_version: str
    deployment_environment: str
    secret_store_selection: str
    systemd_credentials_selected: bool
    require_provider_separation: bool
    require_distinct_credential_names: bool
    require_repository_exclusion: bool
    require_git_history_exclusion: bool
    require_shell_history_exclusion: bool
    require_process_argument_exclusion: bool
    require_environment_dump_exclusion: bool
    require_stdout_exclusion: bool
    require_stderr_exclusion: bool
    require_log_exclusion: bool
    require_test_fixture_exclusion: bool
    require_audit_evidence_exclusion: bool
    require_backup_exclusion: bool
    require_screenshot_exclusion: bool
    require_clipboard_cleanup: bool
    require_restrictive_ownership: bool
    require_restrictive_permission: bool
    require_encryption_at_rest: bool
    require_rollback: bool
    require_deletion: bool
    require_rotation: bool
    require_revocation: bool
    require_independent_reviewer: bool
    evidence_max_age_seconds: int
    fail_closed: bool


@dataclass(frozen=True, slots=True)
class SystemdCredentialTargetV1:
    target_id: str
    policy_id: str
    provider_id: str
    logical_credential_label: str
    systemd_credential_name: str
    service_unit_identity: str
    deployment_environment: str
    routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]
    secret_source_classification: str
    secret_destination_classification: str
    encrypted_at_rest_required: bool
    provider_separation_confirmed: bool
    repository_exclusion_confirmed: bool
    git_history_exclusion_confirmed: bool
    shell_history_exclusion_confirmed: bool
    process_argument_exclusion_confirmed: bool
    environment_dump_exclusion_confirmed: bool
    stdout_exclusion_confirmed: bool
    stderr_exclusion_confirmed: bool
    log_exclusion_confirmed: bool
    test_fixture_exclusion_confirmed: bool
    audit_evidence_exclusion_confirmed: bool
    backup_exclusion_confirmed: bool
    screenshot_exclusion_confirmed: bool
    clipboard_cleanup_required: bool
    restrictive_ownership_required: bool
    restrictive_permission_required: bool
    rollback_ready: bool
    deletion_ready: bool
    rotation_ready: bool
    revocation_ready: bool
    target_ready: bool


@dataclass(frozen=True, slots=True)
class SystemdCredentialPlacementChecklistV1:
    checklist_id: str
    policy_id: str
    target_id: str
    provider_id: str
    logical_credential_label: str
    systemd_credential_name: str
    service_unit_identity: str
    routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]
    systemd_selection_confirmed: bool
    provider_separation_confirmed: bool
    credential_name_distinct: bool
    repository_exclusion_confirmed: bool
    git_history_exclusion_confirmed: bool
    shell_history_exclusion_confirmed: bool
    process_argument_exclusion_confirmed: bool
    environment_dump_exclusion_confirmed: bool
    stdout_exclusion_confirmed: bool
    stderr_exclusion_confirmed: bool
    log_exclusion_confirmed: bool
    test_fixture_exclusion_confirmed: bool
    audit_evidence_exclusion_confirmed: bool
    backup_exclusion_confirmed: bool
    screenshot_exclusion_confirmed: bool
    clipboard_cleanup_confirmed: bool
    restrictive_ownership_confirmed: bool
    restrictive_permission_confirmed: bool
    encryption_at_rest_confirmed: bool
    rollback_ready: bool
    deletion_ready: bool
    rotation_ready: bool
    revocation_ready: bool
    raw_credential_material_supplied: bool
    credential_derived_material_supplied: bool
    raw_exception_detail_supplied: bool
    owner_secret_entry_claimed_completed: bool
    credential_value_access_attempted: bool
    credential_loading_attempted: bool
    provider_validation_attempted: bool
    network_attempted: bool
    provider_transmission_attempted: bool
    runtime_activation_attempted: bool
    runtime_configuration_attempted: bool
    publication_attempted: bool
    owner_secret_entry_authorized: bool
    prohibited_authority_claimed: bool


@dataclass(frozen=True, slots=True)
class SystemdCredentialOwnerEntryAttestationV1:
    attestation_id: str
    policy_id: str
    target_id: str
    checklist_id: str
    operator_id: str
    operator_role: str
    attested_at: datetime
    owner_secret_entry_pending: bool
    owner_secret_entry_completed: bool
    secret_placement_attested_redacted: bool
    sensitive_material_retained: bool
    attestation_complete: bool


@dataclass(frozen=True, slots=True)
class SystemdCredentialIndependentReviewerApprovalV1:
    approval_id: str
    policy_id: str
    target_id: str
    checklist_id: str
    attestation_id: str
    reviewer_id: str
    reviewer_role: str
    approved_at: datetime
    independent_review_complete: bool
    redacted_evidence_only: bool
    placement_procedure_approved: bool
    sensitive_material_retained: bool
    review_complete: bool


@dataclass(frozen=True, slots=True)
class SystemdCredentialPlacementFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class SystemdCredentialPlacementDecisionV1:
    policy_id: str
    provider_id: str
    logical_credential_label: str
    systemd_credential_name: str
    service_unit_identity: str
    routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]
    ready: bool
    placement_state: str
    state_codes: tuple[str, ...]
    supported_state_codes: tuple[str, ...]
    failure_codes: tuple[str, ...]
    failures: tuple[SystemdCredentialPlacementFailureV1, ...]
    credential_onboarding_authorized: bool
    systemd_target_definition_authorized: bool
    owner_secret_entry_authorized: bool
    credential_value_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    runtime_activation_authorized: bool
    runtime_configuration_authorized: bool
    publication_authorized: bool
    fail_closed: bool


@dataclass(frozen=True, slots=True)
class SystemdCredentialPlacementAuditEvidenceV1:
    evidence_id: str
    policy_id: str
    policy_version: str
    provider_id: str
    logical_credential_label: str
    systemd_credential_name: str
    service_unit_identity: str
    routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]
    systemd_selection_confirmed: bool
    repository_exclusion_confirmed: bool
    git_history_exclusion_confirmed: bool
    exposure_controls_ready: bool
    restrictive_ownership_ready: bool
    restrictive_permission_ready: bool
    encryption_at_rest_ready: bool
    clipboard_cleanup_ready: bool
    rollback_ready: bool
    deletion_ready: bool
    rotation_ready: bool
    revocation_ready: bool
    operator_id: str
    operator_role: str
    reviewer_id: str
    reviewer_role: str
    evidence_freshness: str
    failure_codes: tuple[str, ...]
    credential_onboarding_authorized: bool
    systemd_target_definition_authorized: bool
    owner_secret_entry_authorized: bool
    credential_value_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    runtime_activation_authorized: bool
    runtime_configuration_authorized: bool
    publication_authorized: bool
    fail_closed: bool


def _true(value: bool) -> bool:
    return value is True


def _binding(provider_id: str) -> tuple[str, str, str, tuple[str, ...], tuple[str, ...]] | None:
    return next((item for item in _BINDINGS if item[0] == provider_id), None)


def _codes(
    policy: SystemdCredentialStorePolicyV1,
    target: SystemdCredentialTargetV1,
    checklist: SystemdCredentialPlacementChecklistV1,
    attestation: SystemdCredentialOwnerEntryAttestationV1 | None,
    reviewer: SystemdCredentialIndependentReviewerApprovalV1 | None,
    at: datetime,
) -> tuple[str, ...]:
    binding = _binding(target.provider_id)
    label_empty = not target.logical_credential_label or not checklist.logical_credential_label
    name_empty = not target.systemd_credential_name or not checklist.systemd_credential_name
    policy_alignment = bool(policy.policy_id) and (
        target.policy_id != policy.policy_id or checklist.policy_id != policy.policy_id
        or checklist.target_id != target.target_id
    )
    attestation_future = attestation is not None and attestation.attested_at > at
    reviewer_future = reviewer is not None and reviewer.approved_at > at
    attestation_stale = attestation is not None and (at - attestation.attested_at).total_seconds() > policy.evidence_max_age_seconds
    reviewer_expired = reviewer is not None and (at - reviewer.approved_at).total_seconds() > policy.evidence_max_age_seconds
    provider_bad = binding is None or checklist.provider_id != target.provider_id
    route_bad = binding is not None and (target.routing_levels != binding[3] or checklist.routing_levels != binding[3])
    model_bad = binding is not None and (target.exact_provider_model_ids != binding[4] or checklist.exact_provider_model_ids != binding[4])
    label_bad = binding is not None and not label_empty and (
        target.logical_credential_label != binding[1] or checklist.logical_credential_label != binding[1]
    )
    name_bad = binding is not None and not name_empty and (
        target.systemd_credential_name != binding[2] or checklist.systemd_credential_name != binding[2]
    )
    required_target = (
        ("REPOSITORY_EXCLUSION_REQUIRED", policy.require_repository_exclusion, target.repository_exclusion_confirmed, checklist.repository_exclusion_confirmed),
        ("GIT_HISTORY_EXCLUSION_REQUIRED", policy.require_git_history_exclusion, target.git_history_exclusion_confirmed, checklist.git_history_exclusion_confirmed),
        ("SHELL_HISTORY_EXCLUSION_REQUIRED", policy.require_shell_history_exclusion, target.shell_history_exclusion_confirmed, checklist.shell_history_exclusion_confirmed),
        ("PROCESS_ARGUMENT_EXCLUSION_REQUIRED", policy.require_process_argument_exclusion, target.process_argument_exclusion_confirmed, checklist.process_argument_exclusion_confirmed),
        ("ENVIRONMENT_DUMP_EXCLUSION_REQUIRED", policy.require_environment_dump_exclusion, target.environment_dump_exclusion_confirmed, checklist.environment_dump_exclusion_confirmed),
        ("STDOUT_EXCLUSION_REQUIRED", policy.require_stdout_exclusion, target.stdout_exclusion_confirmed, checklist.stdout_exclusion_confirmed),
        ("STDERR_EXCLUSION_REQUIRED", policy.require_stderr_exclusion, target.stderr_exclusion_confirmed, checklist.stderr_exclusion_confirmed),
        ("LOG_EXCLUSION_REQUIRED", policy.require_log_exclusion, target.log_exclusion_confirmed, checklist.log_exclusion_confirmed),
        ("TEST_FIXTURE_EXCLUSION_REQUIRED", policy.require_test_fixture_exclusion, target.test_fixture_exclusion_confirmed, checklist.test_fixture_exclusion_confirmed),
        ("AUDIT_EVIDENCE_EXCLUSION_REQUIRED", policy.require_audit_evidence_exclusion, target.audit_evidence_exclusion_confirmed, checklist.audit_evidence_exclusion_confirmed),
        ("BACKUP_EXCLUSION_REQUIRED", policy.require_backup_exclusion, target.backup_exclusion_confirmed, checklist.backup_exclusion_confirmed),
        ("SCREENSHOT_EXCLUSION_REQUIRED", policy.require_screenshot_exclusion, target.screenshot_exclusion_confirmed, checklist.screenshot_exclusion_confirmed),
    )
    target_conditions = {code: not (_true(required) and _true(first) and _true(second)) for code, required, first, second in required_target}
    conditions = {
        "POLICY_ID_EMPTY": not policy.policy_id,
        "POLICY_VERSION_EMPTY": not policy.policy_version,
        "DEPLOYMENT_ENVIRONMENT_EMPTY": not policy.deployment_environment,
        "SECRET_STORE_SELECTION_MISMATCH": policy.secret_store_selection != "SYSTEMD_CREDENTIALS" or not _true(policy.systemd_credentials_selected) or not _true(checklist.systemd_selection_confirmed),
        "PROVIDER_NOT_ALLOWED": provider_bad,
        "ROUTING_LEVEL_MISMATCH": route_bad,
        "EXACT_MODEL_ID_MISMATCH": model_bad,
        "LOGICAL_CREDENTIAL_LABEL_EMPTY": label_empty,
        "LOGICAL_CREDENTIAL_LABEL_SHARED": not _true(policy.require_provider_separation) or not _true(checklist.provider_separation_confirmed) or not _true(checklist.credential_name_distinct) or label_bad,
        "SYSTEMD_CREDENTIAL_NAME_EMPTY": name_empty,
        "SYSTEMD_CREDENTIAL_NAME_SHARED": not _true(policy.require_distinct_credential_names) or name_bad,
        "SERVICE_UNIT_IDENTITY_REQUIRED": not target.service_unit_identity or not checklist.service_unit_identity,
        "RAW_CREDENTIAL_VALUE_PROVIDED": _true(checklist.raw_credential_material_supplied),
        "RAW_CREDENTIAL_DERIVED_MATERIAL_PROVIDED": _true(checklist.credential_derived_material_supplied),
        **target_conditions,
        "CLIPBOARD_CLEANUP_REQUIRED": not (_true(policy.require_clipboard_cleanup) and _true(target.clipboard_cleanup_required) and _true(checklist.clipboard_cleanup_confirmed)),
        "RESTRICTIVE_OWNERSHIP_REQUIRED": not (_true(policy.require_restrictive_ownership) and _true(target.restrictive_ownership_required) and _true(checklist.restrictive_ownership_confirmed)),
        "RESTRICTIVE_PERMISSION_REQUIRED": not (_true(policy.require_restrictive_permission) and _true(target.restrictive_permission_required) and _true(checklist.restrictive_permission_confirmed)),
        "ENCRYPTION_AT_REST_REQUIRED": not (_true(policy.require_encryption_at_rest) and _true(target.encrypted_at_rest_required) and _true(checklist.encryption_at_rest_confirmed)),
        "ROLLBACK_PROCEDURE_REQUIRED": not (_true(policy.require_rollback) and _true(target.rollback_ready) and _true(checklist.rollback_ready)),
        "DELETION_PROCEDURE_REQUIRED": not (_true(policy.require_deletion) and _true(target.deletion_ready) and _true(checklist.deletion_ready)),
        "ROTATION_PROCEDURE_REQUIRED": not (_true(policy.require_rotation) and _true(target.rotation_ready) and _true(checklist.rotation_ready)),
        "REVOCATION_PROCEDURE_REQUIRED": not (_true(policy.require_revocation) and _true(target.revocation_ready) and _true(checklist.revocation_ready)),
        "OPERATOR_ATTESTATION_REQUIRED": attestation is None or (attestation is not None and (
            not attestation.attestation_id or not attestation.operator_id
            or attestation.operator_role != "REDACTED_PLACEMENT_OPERATOR"
            or (bool(policy.policy_id) and attestation.policy_id != policy.policy_id)
            or attestation.target_id != target.target_id or attestation.checklist_id != checklist.checklist_id
            or not _true(attestation.owner_secret_entry_pending) or _true(attestation.owner_secret_entry_completed)
            or _true(attestation.sensitive_material_retained) or not _true(attestation.attestation_complete)
        )),
        "REVIEWER_APPROVAL_REQUIRED": reviewer is None or (reviewer is not None and (
            not reviewer.approval_id or not reviewer.reviewer_id
            or reviewer.reviewer_role != "INDEPENDENT_SECURITY_REVIEWER"
            or (bool(policy.policy_id) and reviewer.policy_id != policy.policy_id)
            or reviewer.target_id != target.target_id or reviewer.checklist_id != checklist.checklist_id
            or (attestation is not None and reviewer.attestation_id != attestation.attestation_id)
            or not _true(reviewer.independent_review_complete) or not _true(reviewer.redacted_evidence_only)
            or not _true(reviewer.placement_procedure_approved) or _true(reviewer.sensitive_material_retained)
            or not _true(reviewer.review_complete) or not _true(policy.require_independent_reviewer)
        )),
        "OPERATOR_REVIEWER_COLLISION": attestation is not None and reviewer is not None and attestation.operator_id == reviewer.reviewer_id,
        "EVIDENCE_FROM_FUTURE": attestation_future or reviewer_future,
        "EVIDENCE_STALE": attestation_stale and not attestation_future,
        "EVIDENCE_EXPIRED": reviewer_expired and not reviewer_future,
        "OWNER_SECRET_ENTRY_NOT_AUTHORIZED": _true(checklist.owner_secret_entry_claimed_completed) or _true(checklist.owner_secret_entry_authorized) or policy_alignment or not _true(target.target_ready),
        "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED": _true(checklist.credential_value_access_attempted) or _true(checklist.prohibited_authority_claimed),
        "CREDENTIAL_LOADING_NOT_AUTHORIZED": _true(checklist.credential_loading_attempted),
        "CREDENTIAL_VALIDATION_NOT_AUTHORIZED": _true(checklist.provider_validation_attempted),
        "NETWORK_NOT_AUTHORIZED": _true(checklist.network_attempted),
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED": _true(checklist.provider_transmission_attempted),
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED": _true(checklist.runtime_activation_attempted),
        "RUNTIME_CONFIGURATION_NOT_AUTHORIZED": _true(checklist.runtime_configuration_attempted),
        "PUBLICATION_NOT_AUTHORIZED": _true(checklist.publication_attempted),
        "RAW_EXCEPTION_EXPOSURE_DETECTED": _true(checklist.raw_exception_detail_supplied),
    }
    return tuple(code for code in _FAILURE_ORDER if conditions[code])


def evaluate_systemd_credential_placement_v1(
    *, policy: SystemdCredentialStorePolicyV1, target: SystemdCredentialTargetV1,
    checklist: SystemdCredentialPlacementChecklistV1,
    owner_entry_attestation: SystemdCredentialOwnerEntryAttestationV1 | None,
    reviewer_approval: SystemdCredentialIndependentReviewerApprovalV1 | None,
    evaluation_at: datetime,
) -> SystemdCredentialPlacementDecisionV1:
    """Evaluate redacted caller metadata without systemd, secret, filesystem, or network access."""
    codes = _codes(policy, target, checklist, owner_entry_attestation, reviewer_approval, evaluation_at)
    ready = not codes
    return SystemdCredentialPlacementDecisionV1(
        policy_id=policy.policy_id, provider_id=target.provider_id,
        logical_credential_label=target.logical_credential_label,
        systemd_credential_name=target.systemd_credential_name,
        service_unit_identity=target.service_unit_identity, routing_levels=target.routing_levels,
        exact_provider_model_ids=target.exact_provider_model_ids, ready=ready,
        placement_state="SYSTEMD_CREDENTIAL_TARGET_DEFINED" if ready else "PLACEMENT_BLOCKED",
        state_codes=(
            "SYSTEMD_CREDENTIAL_TARGET_DEFINED", "OWNER_SECRET_ENTRY_PENDING",
            "CREDENTIAL_LOADING_NOT_AUTHORIZED", "PROVIDER_VALIDATION_NOT_AUTHORIZED",
            "NETWORK_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
            "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
        ) if ready else (
            "PLACEMENT_BLOCKED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
            "PROVIDER_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
            "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
        ),
        supported_state_codes=_STATES, failure_codes=codes,
        failures=tuple(SystemdCredentialPlacementFailureV1(code, _MESSAGES[code], False) for code in codes),
        credential_onboarding_authorized=True, systemd_target_definition_authorized=True,
        owner_secret_entry_authorized=False, credential_value_access_authorized=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        network_authorized=False, provider_transmission_authorized=False,
        runtime_activation_authorized=False, runtime_configuration_authorized=False,
        publication_authorized=False, fail_closed=True,
    )


def build_systemd_credential_placement_audit_evidence_v1(
    *, evidence_id: str, decision: SystemdCredentialPlacementDecisionV1,
    policy: SystemdCredentialStorePolicyV1, target: SystemdCredentialTargetV1,
    checklist: SystemdCredentialPlacementChecklistV1,
    owner_entry_attestation: SystemdCredentialOwnerEntryAttestationV1,
    reviewer_approval: SystemdCredentialIndependentReviewerApprovalV1, evidence_at: datetime,
) -> SystemdCredentialPlacementAuditEvidenceV1:
    """Build immutable redacted evidence from supplied metadata without I/O or mutation."""
    fresh = (
        owner_entry_attestation.attested_at <= evidence_at
        and reviewer_approval.approved_at <= evidence_at
        and (evidence_at - owner_entry_attestation.attested_at).total_seconds() <= policy.evidence_max_age_seconds
        and (evidence_at - reviewer_approval.approved_at).total_seconds() <= policy.evidence_max_age_seconds
    )
    alignment = (
        ("POLICY_ID_EMPTY",) if not policy.policy_id else ()
    ) + (
        ("OWNER_SECRET_ENTRY_NOT_AUTHORIZED",) if (
            decision.policy_id != policy.policy_id or decision.provider_id != target.provider_id
            or decision.logical_credential_label != target.logical_credential_label
            or decision.systemd_credential_name != target.systemd_credential_name
            or decision.routing_levels != target.routing_levels
            or decision.exact_provider_model_ids != target.exact_provider_model_ids
            or target.policy_id != policy.policy_id or checklist.policy_id != policy.policy_id
            or owner_entry_attestation.policy_id != policy.policy_id or reviewer_approval.policy_id != policy.policy_id
            or checklist.target_id != target.target_id or owner_entry_attestation.target_id != target.target_id
            or reviewer_approval.target_id != target.target_id
        ) else ()
    )
    failures = tuple(code for code in _FAILURE_ORDER if code in decision.failure_codes or code in alignment)
    exposure_ready = all((
        _true(checklist.shell_history_exclusion_confirmed), _true(checklist.process_argument_exclusion_confirmed),
        _true(checklist.environment_dump_exclusion_confirmed), _true(checklist.stdout_exclusion_confirmed),
        _true(checklist.stderr_exclusion_confirmed), _true(checklist.log_exclusion_confirmed),
        _true(checklist.test_fixture_exclusion_confirmed), _true(checklist.audit_evidence_exclusion_confirmed),
        _true(checklist.backup_exclusion_confirmed), _true(checklist.screenshot_exclusion_confirmed),
    ))
    return SystemdCredentialPlacementAuditEvidenceV1(
        evidence_id=evidence_id, policy_id=policy.policy_id, policy_version=policy.policy_version,
        provider_id=target.provider_id, logical_credential_label=target.logical_credential_label,
        systemd_credential_name=target.systemd_credential_name, service_unit_identity=target.service_unit_identity,
        routing_levels=target.routing_levels, exact_provider_model_ids=target.exact_provider_model_ids,
        systemd_selection_confirmed=_true(policy.systemd_credentials_selected) and _true(checklist.systemd_selection_confirmed),
        repository_exclusion_confirmed=_true(target.repository_exclusion_confirmed) and _true(checklist.repository_exclusion_confirmed),
        git_history_exclusion_confirmed=_true(target.git_history_exclusion_confirmed) and _true(checklist.git_history_exclusion_confirmed),
        exposure_controls_ready=exposure_ready,
        restrictive_ownership_ready=_true(target.restrictive_ownership_required) and _true(checklist.restrictive_ownership_confirmed),
        restrictive_permission_ready=_true(target.restrictive_permission_required) and _true(checklist.restrictive_permission_confirmed),
        encryption_at_rest_ready=_true(target.encrypted_at_rest_required) and _true(checklist.encryption_at_rest_confirmed),
        clipboard_cleanup_ready=_true(target.clipboard_cleanup_required) and _true(checklist.clipboard_cleanup_confirmed),
        rollback_ready=_true(target.rollback_ready) and _true(checklist.rollback_ready),
        deletion_ready=_true(target.deletion_ready) and _true(checklist.deletion_ready),
        rotation_ready=_true(target.rotation_ready) and _true(checklist.rotation_ready),
        revocation_ready=_true(target.revocation_ready) and _true(checklist.revocation_ready),
        operator_id=owner_entry_attestation.operator_id, operator_role=owner_entry_attestation.operator_role,
        reviewer_id=reviewer_approval.reviewer_id, reviewer_role=reviewer_approval.reviewer_role,
        evidence_freshness="FRESH" if fresh else "NOT_FRESH", failure_codes=failures,
        credential_onboarding_authorized=True, systemd_target_definition_authorized=True,
        owner_secret_entry_authorized=False, credential_value_access_authorized=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        network_authorized=False, provider_transmission_authorized=False,
        runtime_activation_authorized=False, runtime_configuration_authorized=False,
        publication_authorized=False, fail_closed=True,
    )
