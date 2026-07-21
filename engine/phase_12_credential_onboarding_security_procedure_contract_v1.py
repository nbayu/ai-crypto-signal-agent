"""Pure, metadata-only credential-onboarding security boundary for Phase 12."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


_DEEPSEEK_BINDING = ("DEEPSEEK", "DEEPSEEK_API_KEY", ("L0",), ("deepseek-v4-pro",))
_ANTHROPIC_BINDING = (
    "ANTHROPIC", "ANTHROPIC_API_KEY", ("L1", "L2"),
    ("claude-sonnet-5", "claude-opus-4-8"),
)
_BINDINGS = (_DEEPSEEK_BINDING, _ANTHROPIC_BINDING)
_SUPPORTED_STATES = (
    "ONBOARDING_PROCEDURE_DEFINED", "SECRET_TARGET_READY", "OWNER_SECRET_ENTRY_PENDING",
    "SECRET_PLACEMENT_ATTESTED_REDACTED", "INDEPENDENT_REVIEW_COMPLETE",
    "CREDENTIAL_PRESENT_BUT_NOT_LOADED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PROVIDER_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "REVOKED", "ROTATION_REQUIRED", "ONBOARDING_BLOCKED",
)
_READY_STATES = (
    "ONBOARDING_PROCEDURE_DEFINED", "SECRET_TARGET_READY", "OWNER_SECRET_ENTRY_PENDING",
    "CREDENTIAL_LOADING_NOT_AUTHORIZED", "PROVIDER_VALIDATION_NOT_AUTHORIZED",
    "NETWORK_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
)
_BLOCKED_STATES = (
    "ONBOARDING_BLOCKED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "PROVIDER_VALIDATION_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "RUNTIME_ACTIVATION_NOT_AUTHORIZED",
)
_FAILURE_ORDER = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "DEPLOYMENT_ENVIRONMENT_EMPTY",
    "ONBOARDING_NOT_AUTHORIZED", "PROVIDER_NOT_ALLOWED", "ROUTING_LEVEL_MISMATCH",
    "EXACT_MODEL_ID_MISMATCH", "CREDENTIAL_LABEL_EMPTY", "CREDENTIAL_LABEL_SHARED",
    "RAW_CREDENTIAL_VALUE_PROVIDED", "RAW_CREDENTIAL_FINGERPRINT_PROVIDED",
    "SECRET_TARGET_REQUIRED", "SECRET_TARGET_INSIDE_REPOSITORY", "SECRET_TARGET_COMMITTABLE",
    "GIT_IGNORE_PROTECTION_REQUIRED", "RESTRICTIVE_PERMISSION_REQUIRED",
    "SHELL_HISTORY_EXPOSURE_RISK", "PROCESS_ARGUMENT_EXPOSURE_RISK", "STDOUT_EXPOSURE_RISK",
    "STDERR_EXPOSURE_RISK", "LOG_EXPOSURE_RISK", "TEST_FIXTURE_EXPOSURE_RISK",
    "AUDIT_EVIDENCE_EXPOSURE_RISK", "ENVIRONMENT_DUMP_NOT_AUTHORIZED",
    "BACKUP_ARCHIVE_EXPOSURE_RISK", "SCREENSHOT_RETENTION_RISK",
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
_SAFE_MESSAGES = {
    "POLICY_ID_EMPTY": "policy identity is required",
    "POLICY_VERSION_EMPTY": "policy version is required",
    "DEPLOYMENT_ENVIRONMENT_EMPTY": "deployment environment is required",
    "ONBOARDING_NOT_AUTHORIZED": "onboarding procedure is not authorized",
    "PROVIDER_NOT_ALLOWED": "provider metadata is not allowed",
    "ROUTING_LEVEL_MISMATCH": "routing metadata does not match the provider binding",
    "EXACT_MODEL_ID_MISMATCH": "model metadata does not match the provider binding",
    "CREDENTIAL_LABEL_EMPTY": "credential label is required",
    "CREDENTIAL_LABEL_SHARED": "provider credential label must be separate",
    "RAW_CREDENTIAL_VALUE_PROVIDED": "credential material is not accepted",
    "RAW_CREDENTIAL_FINGERPRINT_PROVIDED": "credential-derived material is not accepted",
    "SECRET_TARGET_REQUIRED": "secret target metadata is required",
    "SECRET_TARGET_INSIDE_REPOSITORY": "secret target must be outside the repository",
    "SECRET_TARGET_COMMITTABLE": "secret target must not be committable",
    "GIT_IGNORE_PROTECTION_REQUIRED": "repository exclusion protection is required",
    "RESTRICTIVE_PERMISSION_REQUIRED": "restrictive permissions are required",
    "SHELL_HISTORY_EXPOSURE_RISK": "shell history exposure prevention is required",
    "PROCESS_ARGUMENT_EXPOSURE_RISK": "process argument exposure prevention is required",
    "STDOUT_EXPOSURE_RISK": "standard output exposure prevention is required",
    "STDERR_EXPOSURE_RISK": "standard error exposure prevention is required",
    "LOG_EXPOSURE_RISK": "log exposure prevention is required",
    "TEST_FIXTURE_EXPOSURE_RISK": "test exposure prevention is required",
    "AUDIT_EVIDENCE_EXPOSURE_RISK": "audit exposure prevention is required",
    "ENVIRONMENT_DUMP_NOT_AUTHORIZED": "environment dumping is not authorized",
    "BACKUP_ARCHIVE_EXPOSURE_RISK": "backup archive exclusion is required",
    "SCREENSHOT_RETENTION_RISK": "screenshot retention prevention is required",
    "CLIPBOARD_CLEANUP_REQUIRED": "clipboard cleanup is required",
    "ROTATION_PROCEDURE_REQUIRED": "rotation procedure is required",
    "REVOCATION_PROCEDURE_REQUIRED": "revocation procedure is required",
    "ROLLBACK_PROCEDURE_REQUIRED": "rollback procedure is required",
    "DELETION_PROCEDURE_REQUIRED": "deletion procedure is required",
    "OPERATOR_ATTESTATION_REQUIRED": "operator attestation is required",
    "REVIEWER_APPROVAL_REQUIRED": "independent reviewer approval is required",
    "OPERATOR_REVIEWER_COLLISION": "operator and reviewer must be distinct",
    "EVIDENCE_FROM_FUTURE": "evidence timestamp must not be in the future",
    "EVIDENCE_STALE": "operator evidence is stale",
    "EVIDENCE_EXPIRED": "reviewer evidence is expired",
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
class CredentialOnboardingSecurityPolicyV1:
    policy_id: str
    policy_version: str
    deployment_environment: str
    onboarding_authorization_confirmed: bool
    require_provider_secret_separation: bool
    require_no_shared_provider_credential: bool
    require_least_privilege_scope: bool
    require_dedicated_project_credential_when_supported: bool
    require_revocation_capability: bool
    require_rotation_procedure: bool
    require_local_secret_store_target: bool
    require_repository_path_exclusion: bool
    require_git_ignore_coverage: bool
    require_restrictive_permissions: bool
    require_no_command_line_argument_exposure: bool
    require_no_shell_history_exposure: bool
    require_no_stdout_exposure: bool
    require_no_stderr_exposure: bool
    require_no_test_fixture_exposure: bool
    require_no_log_exposure: bool
    require_no_audit_evidence_exposure: bool
    require_no_environment_dump: bool
    require_no_process_list_exposure: bool
    require_no_backup_archive_exposure: bool
    require_no_screenshot_retention: bool
    require_clipboard_cleanup: bool
    require_rollback_procedure: bool
    require_deletion_procedure: bool
    require_independent_reviewer_confirmation: bool
    evidence_max_age_seconds: int
    fail_closed: bool


@dataclass(frozen=True, slots=True)
class CredentialSecretTargetV1:
    secret_target_id: str
    policy_id: str
    provider_id: str
    credential_label: str
    routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]
    secret_store_classification: str
    target_outside_repository: bool
    target_may_be_committed: bool
    git_ignore_protection_confirmed: bool
    permissions_restrictive: bool


@dataclass(frozen=True, slots=True)
class CredentialOnboardingChecklistV1:
    checklist_id: str
    policy_id: str
    secret_target_id: str
    provider_id: str
    credential_label: str
    routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]
    provider_secret_separation_confirmed: bool
    credential_label_not_shared: bool
    least_privilege_scope_confirmed: bool
    dedicated_project_credential_confirmed: bool
    revocation_capability_confirmed: bool
    rotation_procedure_defined: bool
    rollback_procedure_defined: bool
    deletion_procedure_defined: bool
    repository_path_excluded: bool
    git_ignore_coverage_confirmed: bool
    permissions_restrictive: bool
    command_line_argument_exposure_prevented: bool
    shell_history_exposure_prevented: bool
    stdout_exposure_prevented: bool
    stderr_exposure_prevented: bool
    log_exposure_prevented: bool
    test_fixture_exposure_prevented: bool
    audit_evidence_exposure_prevented: bool
    environment_dump_prevented: bool
    process_list_exposure_prevented: bool
    backup_archive_exposure_prevented: bool
    screenshot_retention_prevented: bool
    clipboard_cleanup_confirmed: bool
    credential_material_supplied: bool
    credential_fingerprint_supplied: bool
    exception_detail_supplied: bool
    credential_value_access_attempted: bool
    credential_loading_attempted: bool
    provider_validation_attempted: bool
    network_attempted: bool
    provider_transmission_attempted: bool
    runtime_activation_attempted: bool
    runtime_configuration_attempted: bool
    publication_attempted: bool


@dataclass(frozen=True, slots=True)
class CredentialOperatorAttestationV1:
    operator_attestation_id: str
    policy_id: str
    secret_target_id: str
    operator_id: str
    operator_role: str
    attested_at: datetime
    owner_secret_entry_pending: bool
    secret_placement_attested_redacted: bool
    no_credential_material_in_attestation: bool
    rollback_and_deletion_ready: bool


@dataclass(frozen=True, slots=True)
class CredentialIndependentReviewerApprovalV1:
    reviewer_approval_id: str
    policy_id: str
    secret_target_id: str
    reviewer_id: str
    reviewer_role: str
    approved_at: datetime
    independent_review_complete: bool
    redacted_evidence_only: bool
    onboarding_procedure_approved: bool


@dataclass(frozen=True, slots=True)
class CredentialOnboardingFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class CredentialOnboardingDecisionV1:
    policy_id: str
    provider_id: str
    credential_label: str
    routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]
    ready: bool
    onboarding_state: str
    state_codes: tuple[str, ...]
    supported_state_codes: tuple[str, ...]
    failure_codes: tuple[str, ...]
    failures: tuple[CredentialOnboardingFailureV1, ...]
    credential_onboarding_authorized: bool
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
class CredentialOnboardingAuditEvidenceV1:
    evidence_id: str
    policy_id: str
    policy_version: str
    provider_id: str
    credential_label: str
    routing_levels: tuple[str, ...]
    exact_provider_model_ids: tuple[str, ...]
    onboarding_authorization_confirmed: bool
    secret_target_classification: str
    repository_path_excluded: bool
    git_ignore_ready: bool
    permissions_restrictive: bool
    history_exposure_prevented: bool
    argv_exposure_prevented: bool
    stdout_exposure_prevented: bool
    stderr_exposure_prevented: bool
    log_exposure_prevented: bool
    test_exposure_prevented: bool
    audit_exposure_prevented: bool
    clipboard_cleanup_ready: bool
    rotation_ready: bool
    revocation_ready: bool
    rollback_ready: bool
    deletion_ready: bool
    operator_id: str
    operator_role: str
    reviewer_id: str
    reviewer_role: str
    evidence_freshness: str
    failure_codes: tuple[str, ...]
    credential_onboarding_authorized: bool
    credential_value_access_authorized: bool
    credential_loading_authorized: bool
    credential_validation_authorized: bool
    network_authorized: bool
    provider_transmission_authorized: bool
    runtime_activation_authorized: bool
    runtime_configuration_authorized: bool
    publication_authorized: bool
    fail_closed: bool


def _binding_for(provider_id: str) -> tuple[str, str, tuple[str, ...], tuple[str, ...]] | None:
    return next((binding for binding in _BINDINGS if binding[0] == provider_id), None)


def _enabled(value: bool) -> bool:
    return value is True


def _failure_codes(
    policy: CredentialOnboardingSecurityPolicyV1,
    secret_target: CredentialSecretTargetV1 | None,
    checklist: CredentialOnboardingChecklistV1,
    operator_attestation: CredentialOperatorAttestationV1 | None,
    reviewer_approval: CredentialIndependentReviewerApprovalV1 | None,
    evaluation_at: datetime,
) -> tuple[str, ...]:
    target = secret_target
    binding = _binding_for(target.provider_id) if target is not None else None
    target_or_checklist_label_empty = (
        target is not None and (not target.credential_label or not checklist.credential_label)
    )
    provider_mismatch = target is not None and (
        binding is None or checklist.provider_id != target.provider_id
    )
    route_mismatch = target is not None and binding is not None and (
        target.routing_levels != binding[2] or checklist.routing_levels != binding[2]
    )
    model_mismatch = target is not None and binding is not None and (
        target.exact_provider_model_ids != binding[3] or checklist.exact_provider_model_ids != binding[3]
    )
    label_mismatch = target is not None and binding is not None and bool(target.credential_label) and (
        bool(checklist.credential_label)
        and (target.credential_label != binding[1] or checklist.credential_label != binding[1])
    )
    identity_mismatch = target is not None and bool(policy.policy_id) and (
        target.policy_id != policy.policy_id or checklist.policy_id != policy.policy_id
        or checklist.secret_target_id != target.secret_target_id
        or checklist.provider_id != target.provider_id
    )
    operator_future = operator_attestation is not None and operator_attestation.attested_at > evaluation_at
    reviewer_future = reviewer_approval is not None and reviewer_approval.approved_at > evaluation_at
    operator_stale = operator_attestation is not None and (
        evaluation_at - operator_attestation.attested_at
    ).total_seconds() > policy.evidence_max_age_seconds
    reviewer_expired = reviewer_approval is not None and (
        evaluation_at - reviewer_approval.approved_at
    ).total_seconds() > policy.evidence_max_age_seconds
    conditions = {
        "POLICY_ID_EMPTY": not policy.policy_id,
        "POLICY_VERSION_EMPTY": not policy.policy_version,
        "DEPLOYMENT_ENVIRONMENT_EMPTY": not policy.deployment_environment,
        "ONBOARDING_NOT_AUTHORIZED": not _enabled(policy.onboarding_authorization_confirmed)
            or not _enabled(policy.require_provider_secret_separation)
            or not _enabled(policy.require_least_privilege_scope)
            or not _enabled(policy.require_dedicated_project_credential_when_supported)
            or not _enabled(policy.require_local_secret_store_target)
            or not _enabled(policy.require_independent_reviewer_confirmation)
            or not _enabled(policy.fail_closed)
            or policy.evidence_max_age_seconds <= 0
            or identity_mismatch,
        "PROVIDER_NOT_ALLOWED": provider_mismatch,
        "ROUTING_LEVEL_MISMATCH": route_mismatch,
        "EXACT_MODEL_ID_MISMATCH": model_mismatch,
        "CREDENTIAL_LABEL_EMPTY": target is not None and target_or_checklist_label_empty,
        "CREDENTIAL_LABEL_SHARED": not _enabled(policy.require_no_shared_provider_credential)
            or not _enabled(checklist.provider_secret_separation_confirmed)
            or not _enabled(checklist.credential_label_not_shared)
            or label_mismatch,
        "RAW_CREDENTIAL_VALUE_PROVIDED": _enabled(checklist.credential_material_supplied),
        "RAW_CREDENTIAL_FINGERPRINT_PROVIDED": _enabled(checklist.credential_fingerprint_supplied),
        "SECRET_TARGET_REQUIRED": target is None,
        "SECRET_TARGET_INSIDE_REPOSITORY": target is not None and (
            not _enabled(policy.require_repository_path_exclusion)
            or not _enabled(target.target_outside_repository)
            or not _enabled(checklist.repository_path_excluded)
        ),
        "SECRET_TARGET_COMMITTABLE": target is not None and _enabled(target.target_may_be_committed),
        "GIT_IGNORE_PROTECTION_REQUIRED": target is not None and (
            not _enabled(policy.require_git_ignore_coverage)
            or not _enabled(target.git_ignore_protection_confirmed)
            or not _enabled(checklist.git_ignore_coverage_confirmed)
        ),
        "RESTRICTIVE_PERMISSION_REQUIRED": target is not None and (
            not _enabled(policy.require_restrictive_permissions)
            or not _enabled(target.permissions_restrictive) or not _enabled(checklist.permissions_restrictive)
        ),
        "SHELL_HISTORY_EXPOSURE_RISK": not _enabled(policy.require_no_shell_history_exposure)
            or not _enabled(checklist.shell_history_exposure_prevented),
        "PROCESS_ARGUMENT_EXPOSURE_RISK": not _enabled(policy.require_no_command_line_argument_exposure)
            or not _enabled(checklist.command_line_argument_exposure_prevented),
        "STDOUT_EXPOSURE_RISK": not _enabled(policy.require_no_stdout_exposure)
            or not _enabled(checklist.stdout_exposure_prevented),
        "STDERR_EXPOSURE_RISK": not _enabled(policy.require_no_stderr_exposure)
            or not _enabled(checklist.stderr_exposure_prevented),
        "LOG_EXPOSURE_RISK": not _enabled(policy.require_no_log_exposure)
            or not _enabled(checklist.log_exposure_prevented),
        "TEST_FIXTURE_EXPOSURE_RISK": not _enabled(policy.require_no_test_fixture_exposure)
            or not _enabled(checklist.test_fixture_exposure_prevented),
        "AUDIT_EVIDENCE_EXPOSURE_RISK": not _enabled(policy.require_no_audit_evidence_exposure)
            or not _enabled(checklist.audit_evidence_exposure_prevented),
        "ENVIRONMENT_DUMP_NOT_AUTHORIZED": not _enabled(policy.require_no_environment_dump)
            or not _enabled(policy.require_no_process_list_exposure)
            or not _enabled(checklist.environment_dump_prevented)
            or not _enabled(checklist.process_list_exposure_prevented),
        "BACKUP_ARCHIVE_EXPOSURE_RISK": not _enabled(policy.require_no_backup_archive_exposure)
            or not _enabled(checklist.backup_archive_exposure_prevented),
        "SCREENSHOT_RETENTION_RISK": not _enabled(policy.require_no_screenshot_retention)
            or not _enabled(checklist.screenshot_retention_prevented),
        "CLIPBOARD_CLEANUP_REQUIRED": not _enabled(policy.require_clipboard_cleanup)
            or not _enabled(checklist.clipboard_cleanup_confirmed),
        "ROTATION_PROCEDURE_REQUIRED": not _enabled(policy.require_rotation_procedure)
            or not _enabled(checklist.rotation_procedure_defined),
        "REVOCATION_PROCEDURE_REQUIRED": not _enabled(policy.require_revocation_capability)
            or not _enabled(checklist.revocation_capability_confirmed),
        "ROLLBACK_PROCEDURE_REQUIRED": not _enabled(policy.require_rollback_procedure)
            or not _enabled(checklist.rollback_procedure_defined),
        "DELETION_PROCEDURE_REQUIRED": not _enabled(policy.require_deletion_procedure)
            or not _enabled(checklist.deletion_procedure_defined),
        "OPERATOR_ATTESTATION_REQUIRED": operator_attestation is None or (
            operator_attestation is not None and (
                not operator_attestation.operator_attestation_id or not operator_attestation.operator_id
                or operator_attestation.operator_role != "SECRET_ENTRY_OPERATOR"
                or (bool(policy.policy_id) and operator_attestation.policy_id != policy.policy_id)
                or (target is not None and operator_attestation.secret_target_id != target.secret_target_id)
                or not _enabled(operator_attestation.owner_secret_entry_pending)
                or not _enabled(operator_attestation.no_credential_material_in_attestation)
                or not _enabled(operator_attestation.rollback_and_deletion_ready)
            )
        ),
        "REVIEWER_APPROVAL_REQUIRED": reviewer_approval is None or (
            reviewer_approval is not None and (
                not reviewer_approval.reviewer_approval_id or not reviewer_approval.reviewer_id
                or reviewer_approval.reviewer_role != "INDEPENDENT_SECURITY_REVIEWER"
                or (bool(policy.policy_id) and reviewer_approval.policy_id != policy.policy_id)
                or (target is not None and reviewer_approval.secret_target_id != target.secret_target_id)
                or not _enabled(reviewer_approval.independent_review_complete)
                or not _enabled(reviewer_approval.redacted_evidence_only)
                or not _enabled(reviewer_approval.onboarding_procedure_approved)
            )
        ),
        "OPERATOR_REVIEWER_COLLISION": operator_attestation is not None and reviewer_approval is not None
            and operator_attestation.operator_id == reviewer_approval.reviewer_id,
        "EVIDENCE_FROM_FUTURE": operator_future or reviewer_future,
        "EVIDENCE_STALE": operator_stale and not operator_future,
        "EVIDENCE_EXPIRED": reviewer_expired and not reviewer_future,
        "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED": _enabled(checklist.credential_value_access_attempted),
        "CREDENTIAL_LOADING_NOT_AUTHORIZED": _enabled(checklist.credential_loading_attempted),
        "CREDENTIAL_VALIDATION_NOT_AUTHORIZED": _enabled(checklist.provider_validation_attempted),
        "NETWORK_NOT_AUTHORIZED": _enabled(checklist.network_attempted),
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED": _enabled(checklist.provider_transmission_attempted),
        "RUNTIME_ACTIVATION_NOT_AUTHORIZED": _enabled(checklist.runtime_activation_attempted),
        "RUNTIME_CONFIGURATION_NOT_AUTHORIZED": _enabled(checklist.runtime_configuration_attempted),
        "PUBLICATION_NOT_AUTHORIZED": _enabled(checklist.publication_attempted),
        "RAW_EXCEPTION_EXPOSURE_DETECTED": _enabled(checklist.exception_detail_supplied),
    }
    return tuple(code for code in _FAILURE_ORDER if conditions[code])


def evaluate_credential_onboarding_v1(
    *,
    policy: CredentialOnboardingSecurityPolicyV1,
    secret_target: CredentialSecretTargetV1 | None,
    checklist: CredentialOnboardingChecklistV1,
    operator_attestation: CredentialOperatorAttestationV1 | None,
    reviewer_approval: CredentialIndependentReviewerApprovalV1 | None,
    evaluation_at: datetime,
) -> CredentialOnboardingDecisionV1:
    """Evaluate caller-supplied redacted metadata without accessing any credential."""
    failure_codes = _failure_codes(
        policy, secret_target, checklist, operator_attestation, reviewer_approval, evaluation_at,
    )
    failures = tuple(
        CredentialOnboardingFailureV1(code, _SAFE_MESSAGES[code], False) for code in failure_codes
    )
    ready = not failure_codes
    return CredentialOnboardingDecisionV1(
        policy_id=policy.policy_id,
        provider_id=secret_target.provider_id if secret_target is not None else checklist.provider_id,
        credential_label=(secret_target.credential_label if secret_target is not None else checklist.credential_label),
        routing_levels=secret_target.routing_levels if secret_target is not None else checklist.routing_levels,
        exact_provider_model_ids=(
            secret_target.exact_provider_model_ids if secret_target is not None else checklist.exact_provider_model_ids
        ),
        ready=ready,
        onboarding_state="ONBOARDING_PROCEDURE_DEFINED" if ready else "ONBOARDING_BLOCKED",
        state_codes=_READY_STATES if ready else _BLOCKED_STATES,
        supported_state_codes=_SUPPORTED_STATES,
        failure_codes=failure_codes,
        failures=failures,
        credential_onboarding_authorized=True,
        credential_value_access_authorized=False,
        credential_loading_authorized=False,
        credential_validation_authorized=False,
        network_authorized=False,
        provider_transmission_authorized=False,
        runtime_activation_authorized=False,
        runtime_configuration_authorized=False,
        publication_authorized=False,
        fail_closed=True,
    )


def build_credential_onboarding_audit_evidence_v1(
    *,
    evidence_id: str,
    decision: CredentialOnboardingDecisionV1,
    policy: CredentialOnboardingSecurityPolicyV1,
    secret_target: CredentialSecretTargetV1,
    checklist: CredentialOnboardingChecklistV1,
    operator_attestation: CredentialOperatorAttestationV1,
    reviewer_approval: CredentialIndependentReviewerApprovalV1,
    evidence_at: datetime,
) -> CredentialOnboardingAuditEvidenceV1:
    """Build immutable redacted evidence from caller-supplied metadata only."""
    freshness = "FRESH" if (
        operator_attestation.attested_at <= evidence_at
        and reviewer_approval.approved_at <= evidence_at
        and (evidence_at - operator_attestation.attested_at).total_seconds() <= policy.evidence_max_age_seconds
        and (evidence_at - reviewer_approval.approved_at).total_seconds() <= policy.evidence_max_age_seconds
    ) else "NOT_FRESH"
    alignment_failures = (
        ("POLICY_ID_EMPTY",) if not policy.policy_id else ()
    ) + (
        ("ONBOARDING_NOT_AUTHORIZED",) if (
            secret_target.policy_id != policy.policy_id or checklist.policy_id != policy.policy_id
            or operator_attestation.policy_id != policy.policy_id
            or reviewer_approval.policy_id != policy.policy_id
            or checklist.secret_target_id != secret_target.secret_target_id
            or operator_attestation.secret_target_id != secret_target.secret_target_id
            or reviewer_approval.secret_target_id != secret_target.secret_target_id
            or decision.policy_id != policy.policy_id
        ) else ()
    ) + (
        ("PROVIDER_NOT_ALLOWED",) if decision.provider_id != secret_target.provider_id else ()
    ) + (
        ("ROUTING_LEVEL_MISMATCH",) if decision.routing_levels != secret_target.routing_levels else ()
    ) + (
        ("EXACT_MODEL_ID_MISMATCH",)
        if decision.exact_provider_model_ids != secret_target.exact_provider_model_ids else ()
    ) + (
        ("CREDENTIAL_LABEL_SHARED",) if decision.credential_label != secret_target.credential_label else ()
    )
    failure_codes = tuple(
        code for code in _FAILURE_ORDER if code in decision.failure_codes or code in alignment_failures
    )
    return CredentialOnboardingAuditEvidenceV1(
        evidence_id=evidence_id,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        provider_id=secret_target.provider_id,
        credential_label=secret_target.credential_label,
        routing_levels=secret_target.routing_levels,
        exact_provider_model_ids=secret_target.exact_provider_model_ids,
        onboarding_authorization_confirmed=_enabled(policy.onboarding_authorization_confirmed),
        secret_target_classification=secret_target.secret_store_classification,
        repository_path_excluded=_enabled(secret_target.target_outside_repository)
            and _enabled(checklist.repository_path_excluded),
        git_ignore_ready=_enabled(secret_target.git_ignore_protection_confirmed)
            and _enabled(checklist.git_ignore_coverage_confirmed),
        permissions_restrictive=_enabled(secret_target.permissions_restrictive)
            and _enabled(checklist.permissions_restrictive),
        history_exposure_prevented=_enabled(checklist.shell_history_exposure_prevented),
        argv_exposure_prevented=_enabled(checklist.command_line_argument_exposure_prevented),
        stdout_exposure_prevented=_enabled(checklist.stdout_exposure_prevented),
        stderr_exposure_prevented=_enabled(checklist.stderr_exposure_prevented),
        log_exposure_prevented=_enabled(checklist.log_exposure_prevented),
        test_exposure_prevented=_enabled(checklist.test_fixture_exposure_prevented),
        audit_exposure_prevented=_enabled(checklist.audit_evidence_exposure_prevented),
        clipboard_cleanup_ready=_enabled(checklist.clipboard_cleanup_confirmed),
        rotation_ready=_enabled(checklist.rotation_procedure_defined),
        revocation_ready=_enabled(checklist.revocation_capability_confirmed),
        rollback_ready=_enabled(checklist.rollback_procedure_defined),
        deletion_ready=_enabled(checklist.deletion_procedure_defined),
        operator_id=operator_attestation.operator_id,
        operator_role=operator_attestation.operator_role,
        reviewer_id=reviewer_approval.reviewer_id,
        reviewer_role=reviewer_approval.reviewer_role,
        evidence_freshness=freshness,
        failure_codes=failure_codes,
        credential_onboarding_authorized=True,
        credential_value_access_authorized=False,
        credential_loading_authorized=False,
        credential_validation_authorized=False,
        network_authorized=False,
        provider_transmission_authorized=False,
        runtime_activation_authorized=False,
        runtime_configuration_authorized=False,
        publication_authorized=False,
        fail_closed=True,
    )
