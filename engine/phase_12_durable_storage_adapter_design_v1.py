"""Pure, immutable design evidence for a future durable-storage adapter.

The module contains no concrete adapter, storage operation, lifecycle action,
or provider capability.  It validates only metadata supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass


_ALLOWED_STORAGE_TECHNOLOGIES = ("SQLITE", "POSTGRESQL")
_REQUIRED_ENTITIES = (
    "RESERVATION_SNAPSHOT", "APPEND_ONLY_LEDGER_EVENT", "COMMAND_IDEMPOTENCY",
    "RECOVERY_EVIDENCE", "SCHEMA_METADATA",
)
_REQUIRED_UNIQUENESS = (
    "PERSISTENCE_COMMAND_ID", "RESERVATION_ID", "RESERVATION_REQUEST_ID", "REQUEST_ID",
    "IDEMPOTENCY_KEY", "LEDGER_EVENT_ID", "RESERVATION_REVISION",
)
_REQUIRED_ALIGNMENTS = (
    "SNAPSHOT_RESERVATION", "EVENT_RESERVATION", "EVENT_REQUEST", "EVENT_REVISION",
    "RECOVERY_COMMAND",
)


@dataclass(frozen=True, slots=True)
class DurableStorageAdapterDesignV1:
    adapter_id: str
    adapter_version: str
    storage_technology: str
    storage_mode: str
    storage_location_classification: str
    schema_id: str
    schema_version: int
    transaction_policy_id: str
    integrity_policy_id: str
    lifecycle_policy_id: str
    production_adapter_selected: bool = False
    storage_access_authorized: bool = False
    schema_creation_authorized: bool = False
    migration_authorized: bool = False
    persistence_authorized: bool = False
    reservation_creation_authorized: bool = False
    ledger_mutation_authorized: bool = False
    provider_transmission_authorized: bool = False
    provider_execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class DurableStorageSchemaDesignV1:
    schema_id: str
    schema_version: int
    logical_entities: tuple[str, ...]
    uniqueness_constraints: tuple[str, ...]
    identity_alignments: tuple[str, ...]
    append_only_events_required: bool
    event_update_forbidden: bool
    event_delete_forbidden: bool
    revision_monotonicity_required: bool
    exactly_one_current_snapshot_required: bool
    complete_snapshot_event_alignment_required: bool


@dataclass(frozen=True, slots=True)
class DurableStorageTransactionPolicyV1:
    transaction_policy_id: str
    atomic_compare_and_append_required: bool
    snapshot_event_single_transaction_required: bool
    revision_comparison_required: bool
    last_event_comparison_required: bool
    uniqueness_checks_required: bool
    rollback_on_failure_required: bool
    partial_append_forbidden: bool
    automatic_retry_forbidden: bool
    busy_conflicts_fail_closed: bool
    uncertain_commit_recovery_read_required: bool
    transaction_timeout_seconds: int
    transaction_authorized: bool = False
    maximum_persistence_attempts: int = 1


@dataclass(frozen=True, slots=True)
class DurableStorageIntegrityPolicyV1:
    integrity_policy_id: str
    append_only_event_history_required: bool
    immutable_event_identity_required: bool
    snapshot_event_revision_alignment_required: bool
    deterministic_serialization_identity_required: bool
    corruption_detection_required: bool
    unsupported_schema_rejected: bool
    downgrade_rejected: bool
    partial_record_rejected: bool
    identity_conflict_rejected: bool
    recovery_verification_required: bool
    database_repair_authorized: bool = False
    destructive_recovery_authorized: bool = False


@dataclass(frozen=True, slots=True)
class DurableStorageLifecyclePolicyV1:
    lifecycle_policy_id: str
    explicit_initialize_required: bool
    explicit_readiness_validation_required: bool
    explicit_shutdown_required: bool
    schema_compatibility_validation_required: bool
    migration_enabled: bool
    startup_recovery_required: bool
    clean_shutdown_evidence_required: bool
    background_migration_allowed: bool
    background_compaction_allowed: bool
    implicit_database_creation_allowed: bool
    implicit_directory_creation_allowed: bool
    destructive_reset_allowed: bool
    automatic_memory_fallback_allowed: bool
    automatic_adapter_fallback_allowed: bool
    initialize_authorized: bool = False
    create_authorized: bool = False
    migrate_authorized: bool = False
    repair_authorized: bool = False
    persist_authorized: bool = False
    mutate_authorized: bool = False


@dataclass(frozen=True, slots=True)
class DurableStorageDesignFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class DurableStorageDesignValidationResultV1:
    adapter_id: str
    design_valid: bool
    adapter_selected: bool
    storage_accessible: bool
    schema_compatible: bool
    migration_required: bool
    migration_authorized: bool
    corruption_detected: bool
    recovery_required: bool
    adapter_ready: bool
    production_persistence_authorized: bool
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DurableStorageDesignAuditEvidenceV1:
    adapter_id: str
    adapter_version: str
    storage_technology: str
    schema_id: str
    schema_version: int
    transaction_policy_id: str
    integrity_policy_id: str
    lifecycle_policy_id: str
    design_valid: bool
    adapter_selected: bool
    schema_compatible: bool
    adapter_ready: bool
    recovery_required: bool
    production_persistence_authorized: bool
    failure_codes: tuple[str, ...]
    persistence_authorized: bool
    reservation_creation_authorized: bool
    ledger_mutation_authorized: bool
    provider_transmission_authorized: bool
    provider_execution_authorized: bool


def _add(codes: tuple[str, ...], code: str) -> tuple[str, ...]:
    return codes if code in codes else codes + (code,)


def _ordered(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(codes))


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and "*" not in value


def _tuple_contains(values: object, required: tuple[str, ...]) -> bool:
    return isinstance(values, tuple) and all(isinstance(value, str) for value in values) and set(required).issubset(values)


def _component_types(
    adapter_design: object, schema_design: object, transaction_policy: object,
    integrity_policy: object, lifecycle_policy: object,
) -> bool:
    return (
        isinstance(adapter_design, DurableStorageAdapterDesignV1)
        and isinstance(schema_design, DurableStorageSchemaDesignV1)
        and isinstance(transaction_policy, DurableStorageTransactionPolicyV1)
        and isinstance(integrity_policy, DurableStorageIntegrityPolicyV1)
        and isinstance(lifecycle_policy, DurableStorageLifecyclePolicyV1)
    )


def _identity_failures(
    adapter_design: DurableStorageAdapterDesignV1, schema_design: DurableStorageSchemaDesignV1,
    transaction_policy: DurableStorageTransactionPolicyV1, integrity_policy: DurableStorageIntegrityPolicyV1,
    lifecycle_policy: DurableStorageLifecyclePolicyV1,
) -> tuple[str, ...]:
    codes: tuple[str, ...] = ()
    identities = (
        (adapter_design.adapter_id, "ADAPTER_ID_EMPTY"),
        (adapter_design.adapter_version, "ADAPTER_VERSION_EMPTY"),
        (adapter_design.storage_technology, "STORAGE_TECHNOLOGY_EMPTY"),
        (adapter_design.storage_mode, "STORAGE_MODE_EMPTY"),
        (adapter_design.storage_location_classification, "STORAGE_LOCATION_CLASSIFICATION_EMPTY"),
        (adapter_design.schema_id, "SCHEMA_ID_EMPTY"),
        (adapter_design.transaction_policy_id, "TRANSACTION_POLICY_ID_EMPTY"),
        (adapter_design.integrity_policy_id, "INTEGRITY_POLICY_ID_EMPTY"),
        (adapter_design.lifecycle_policy_id, "LIFECYCLE_POLICY_ID_EMPTY"),
        (schema_design.schema_id, "SCHEMA_ID_EMPTY"),
        (transaction_policy.transaction_policy_id, "TRANSACTION_POLICY_ID_EMPTY"),
        (integrity_policy.integrity_policy_id, "INTEGRITY_POLICY_ID_EMPTY"),
        (lifecycle_policy.lifecycle_policy_id, "LIFECYCLE_POLICY_ID_EMPTY"),
    )
    for value, empty_code in identities:
        if not isinstance(value, str) or not value:
            codes = _add(codes, empty_code)
        elif not _identifier(value):
            codes = _add(codes, "IDENTIFIER_NOT_NORMALIZED")
    versions = (adapter_design.schema_version, schema_design.schema_version)
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in versions):
        codes = _add(codes, "SCHEMA_VERSION_INVALID")
    elif adapter_design.schema_version != schema_design.schema_version or adapter_design.schema_id != schema_design.schema_id:
        codes = _add(codes, "SCHEMA_COMPATIBILITY_NOT_REQUIRED")
    if adapter_design.transaction_policy_id != transaction_policy.transaction_policy_id:
        codes = _add(codes, "DESIGN_INVALID")
    if adapter_design.integrity_policy_id != integrity_policy.integrity_policy_id:
        codes = _add(codes, "DESIGN_INVALID")
    if adapter_design.lifecycle_policy_id != lifecycle_policy.lifecycle_policy_id:
        codes = _add(codes, "DESIGN_INVALID")
    return codes


def _policy_failures(
    adapter_design: DurableStorageAdapterDesignV1, schema_design: DurableStorageSchemaDesignV1,
    transaction_policy: DurableStorageTransactionPolicyV1, integrity_policy: DurableStorageIntegrityPolicyV1,
    lifecycle_policy: DurableStorageLifecyclePolicyV1,
) -> tuple[str, ...]:
    codes: tuple[str, ...] = ()
    if adapter_design.storage_technology not in _ALLOWED_STORAGE_TECHNOLOGIES:
        codes = _add(codes, "STORAGE_TECHNOLOGY_NOT_ALLOWED")
    if transaction_policy.atomic_compare_and_append_required is not True:
        codes = _add(codes, "ATOMIC_COMPARE_AND_APPEND_NOT_REQUIRED")
    if transaction_policy.snapshot_event_single_transaction_required is not True or transaction_policy.rollback_on_failure_required is not True:
        codes = _add(codes, "SNAPSHOT_EVENT_TRANSACTION_NOT_ATOMIC")
    if transaction_policy.revision_comparison_required is not True:
        codes = _add(codes, "REVISION_CHECK_NOT_REQUIRED")
    if transaction_policy.last_event_comparison_required is not True:
        codes = _add(codes, "LAST_EVENT_CHECK_NOT_REQUIRED")
    if transaction_policy.uniqueness_checks_required is not True:
        codes = _add(codes, "UNIQUENESS_CHECK_NOT_REQUIRED")
    if transaction_policy.partial_append_forbidden is not True:
        codes = _add(codes, "PARTIAL_APPEND_ALLOWED")
    if (transaction_policy.automatic_retry_forbidden is not True or transaction_policy.busy_conflicts_fail_closed is not True
            or transaction_policy.maximum_persistence_attempts != 1):
        codes = _add(codes, "AUTOMATIC_RETRY_ALLOWED")
    if (not isinstance(transaction_policy.transaction_timeout_seconds, int)
            or isinstance(transaction_policy.transaction_timeout_seconds, bool)
            or transaction_policy.transaction_timeout_seconds <= 0):
        codes = _add(codes, "DESIGN_INVALID")
    if schema_design.append_only_events_required is not True or integrity_policy.append_only_event_history_required is not True:
        codes = _add(codes, "APPEND_ONLY_NOT_REQUIRED")
    if schema_design.event_update_forbidden is not True:
        codes = _add(codes, "EVENT_UPDATE_ALLOWED")
    if schema_design.event_delete_forbidden is not True:
        codes = _add(codes, "EVENT_DELETE_ALLOWED")
    if schema_design.revision_monotonicity_required is not True:
        codes = _add(codes, "REVISION_MONOTONICITY_NOT_REQUIRED")
    if integrity_policy.corruption_detection_required is not True:
        codes = _add(codes, "CORRUPTION_DETECTION_NOT_REQUIRED")
    if integrity_policy.database_repair_authorized is not False:
        codes = _add(codes, "AUTOMATIC_REPAIR_ALLOWED")
    if integrity_policy.destructive_recovery_authorized is not False:
        codes = _add(codes, "DESTRUCTIVE_RECOVERY_ALLOWED")
    if lifecycle_policy.schema_compatibility_validation_required is not True:
        codes = _add(codes, "SCHEMA_COMPATIBILITY_NOT_REQUIRED")
    if lifecycle_policy.startup_recovery_required is not True or transaction_policy.uncertain_commit_recovery_read_required is not True:
        codes = _add(codes, "STARTUP_RECOVERY_NOT_REQUIRED")
    if lifecycle_policy.background_migration_allowed is not False or lifecycle_policy.migration_enabled is not False:
        codes = _add(codes, "BACKGROUND_MIGRATION_ALLOWED")
    if lifecycle_policy.implicit_database_creation_allowed is not False:
        codes = _add(codes, "IMPLICIT_DATABASE_CREATION_ALLOWED")
    if lifecycle_policy.implicit_directory_creation_allowed is not False:
        codes = _add(codes, "IMPLICIT_DIRECTORY_CREATION_ALLOWED")
    if lifecycle_policy.automatic_memory_fallback_allowed is not False:
        codes = _add(codes, "AUTOMATIC_MEMORY_FALLBACK_ALLOWED")
    if lifecycle_policy.automatic_adapter_fallback_allowed is not False:
        codes = _add(codes, "AUTOMATIC_ADAPTER_FALLBACK_ALLOWED")
    if (not _tuple_contains(schema_design.logical_entities, _REQUIRED_ENTITIES)
            or not _tuple_contains(schema_design.uniqueness_constraints, _REQUIRED_UNIQUENESS)
            or not _tuple_contains(schema_design.identity_alignments, _REQUIRED_ALIGNMENTS)
            or schema_design.exactly_one_current_snapshot_required is not True
            or schema_design.complete_snapshot_event_alignment_required is not True
            or integrity_policy.immutable_event_identity_required is not True
            or integrity_policy.snapshot_event_revision_alignment_required is not True
            or integrity_policy.deterministic_serialization_identity_required is not True
            or integrity_policy.unsupported_schema_rejected is not True
            or integrity_policy.downgrade_rejected is not True
            or integrity_policy.partial_record_rejected is not True
            or integrity_policy.identity_conflict_rejected is not True
            or integrity_policy.recovery_verification_required is not True
            or lifecycle_policy.explicit_initialize_required is not True
            or lifecycle_policy.explicit_readiness_validation_required is not True
            or lifecycle_policy.explicit_shutdown_required is not True
            or lifecycle_policy.clean_shutdown_evidence_required is not True):
        codes = _add(codes, "DESIGN_INVALID")
    return codes


def _authority_failures(adapter_design: DurableStorageAdapterDesignV1) -> tuple[str, ...]:
    codes: tuple[str, ...] = ()
    if adapter_design.production_adapter_selected is not True:
        codes = _add(codes, "PRODUCTION_ADAPTER_NOT_SELECTED")
    if adapter_design.storage_access_authorized is not True:
        codes = _add(codes, "STORAGE_ACCESS_NOT_AUTHORIZED")
    if adapter_design.schema_creation_authorized is not True:
        codes = _add(codes, "SCHEMA_CREATION_NOT_AUTHORIZED")
    if adapter_design.migration_authorized is not True:
        codes = _add(codes, "MIGRATION_NOT_AUTHORIZED")
    if adapter_design.persistence_authorized is not True:
        codes = _add(codes, "PERSISTENCE_NOT_AUTHORIZED")
    if adapter_design.reservation_creation_authorized is not True:
        codes = _add(codes, "RESERVATION_CREATION_NOT_AUTHORIZED")
    if adapter_design.ledger_mutation_authorized is not True:
        codes = _add(codes, "LEDGER_MUTATION_NOT_AUTHORIZED")
    if adapter_design.provider_transmission_authorized is not True:
        codes = _add(codes, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED")
    if adapter_design.provider_execution_authorized is not True:
        codes = _add(codes, "PROVIDER_EXECUTION_NOT_AUTHORIZED")
    return codes


def validate_durable_storage_adapter_design_v1(
    adapter_design: DurableStorageAdapterDesignV1, schema_design: DurableStorageSchemaDesignV1,
    transaction_policy: DurableStorageTransactionPolicyV1, integrity_policy: DurableStorageIntegrityPolicyV1,
    lifecycle_policy: DurableStorageLifecyclePolicyV1,
) -> DurableStorageDesignValidationResultV1:
    """Validate future-adapter design metadata without selecting or operating an adapter."""
    if not _component_types(adapter_design, schema_design, transaction_policy, integrity_policy, lifecycle_policy):
        return DurableStorageDesignValidationResultV1("", False, False, False, False, False, False, False, True, False, False, ("DESIGN_INVALID", "ADAPTER_NOT_READY", "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED"))
    identity_codes = _identity_failures(adapter_design, schema_design, transaction_policy, integrity_policy, lifecycle_policy)
    policy_codes = _policy_failures(adapter_design, schema_design, transaction_policy, integrity_policy, lifecycle_policy)
    authority_codes = _authority_failures(adapter_design)
    core_codes = identity_codes + policy_codes
    design_valid = not core_codes
    schema_compatible = (
        adapter_design.schema_id == schema_design.schema_id
        and adapter_design.schema_version == schema_design.schema_version
        and lifecycle_policy.schema_compatibility_validation_required is True
    )
    codes = _ordered(core_codes + authority_codes + ("ADAPTER_NOT_READY", "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED"))
    return DurableStorageDesignValidationResultV1(
        adapter_design.adapter_id, design_valid, adapter_design.production_adapter_selected is True,
        False, schema_compatible, False, adapter_design.migration_authorized is True, False,
        True, False, False, codes,
    )


def build_durable_storage_design_audit_evidence_v1(
    adapter_design: DurableStorageAdapterDesignV1, schema_design: DurableStorageSchemaDesignV1,
    transaction_policy: DurableStorageTransactionPolicyV1, integrity_policy: DurableStorageIntegrityPolicyV1,
    lifecycle_policy: DurableStorageLifecyclePolicyV1, result: DurableStorageDesignValidationResultV1,
) -> DurableStorageDesignAuditEvidenceV1:
    """Project immutable validation evidence without adapter activation or I/O."""
    if (not _component_types(adapter_design, schema_design, transaction_policy, integrity_policy, lifecycle_policy)
            or not isinstance(result, DurableStorageDesignValidationResultV1)):
        raise ValueError("durable storage design evidence requires contract records")
    if result.adapter_id != adapter_design.adapter_id:
        raise ValueError("durable storage design evidence adapter mismatch")
    if (adapter_design.schema_id != schema_design.schema_id
            or adapter_design.transaction_policy_id != transaction_policy.transaction_policy_id
            or adapter_design.integrity_policy_id != integrity_policy.integrity_policy_id
            or adapter_design.lifecycle_policy_id != lifecycle_policy.lifecycle_policy_id):
        raise ValueError("durable storage design evidence component mismatch")
    expected = validate_durable_storage_adapter_design_v1(
        adapter_design, schema_design, transaction_policy, integrity_policy, lifecycle_policy,
    )
    if result != expected:
        raise ValueError("durable storage design evidence result mismatch")
    return DurableStorageDesignAuditEvidenceV1(
        adapter_design.adapter_id, adapter_design.adapter_version, adapter_design.storage_technology,
        adapter_design.schema_id, adapter_design.schema_version, adapter_design.transaction_policy_id,
        adapter_design.integrity_policy_id, adapter_design.lifecycle_policy_id, result.design_valid,
        result.adapter_selected, result.schema_compatible, result.adapter_ready, result.recovery_required,
        result.production_persistence_authorized, result.failure_codes, adapter_design.persistence_authorized,
        adapter_design.reservation_creation_authorized, adapter_design.ledger_mutation_authorized,
        adapter_design.provider_transmission_authorized, adapter_design.provider_execution_authorized,
    )
