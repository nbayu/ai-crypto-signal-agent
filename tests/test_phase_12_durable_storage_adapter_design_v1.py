"""RED contract for a future pure durable-storage adapter design boundary."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from engine.phase_12_durable_storage_adapter_design_v1 import (
    DurableStorageAdapterDesignV1,
    DurableStorageDesignAuditEvidenceV1,
    DurableStorageDesignFailureV1,
    DurableStorageDesignValidationResultV1,
    DurableStorageIntegrityPolicyV1,
    DurableStorageLifecyclePolicyV1,
    DurableStorageSchemaDesignV1,
    DurableStorageTransactionPolicyV1,
    build_durable_storage_design_audit_evidence_v1,
    validate_durable_storage_adapter_design_v1,
)


_ADAPTER_FIELDS = (
    "adapter_id", "adapter_version", "storage_technology", "storage_mode",
    "storage_location_classification", "schema_id", "schema_version", "transaction_policy_id",
    "integrity_policy_id", "lifecycle_policy_id", "production_adapter_selected",
    "storage_access_authorized", "schema_creation_authorized", "migration_authorized",
    "persistence_authorized", "reservation_creation_authorized", "ledger_mutation_authorized",
    "provider_transmission_authorized", "provider_execution_authorized",
)
_SCHEMA_FIELDS = (
    "schema_id", "schema_version", "logical_entities", "uniqueness_constraints",
    "identity_alignments", "append_only_events_required", "event_update_forbidden",
    "event_delete_forbidden", "revision_monotonicity_required",
    "exactly_one_current_snapshot_required", "complete_snapshot_event_alignment_required",
)
_TRANSACTION_FIELDS = (
    "transaction_policy_id", "atomic_compare_and_append_required",
    "snapshot_event_single_transaction_required", "revision_comparison_required",
    "last_event_comparison_required", "uniqueness_checks_required", "rollback_on_failure_required",
    "partial_append_forbidden", "automatic_retry_forbidden", "busy_conflicts_fail_closed",
    "uncertain_commit_recovery_read_required", "transaction_timeout_seconds",
    "transaction_authorized", "maximum_persistence_attempts",
)
_INTEGRITY_FIELDS = (
    "integrity_policy_id", "append_only_event_history_required", "immutable_event_identity_required",
    "snapshot_event_revision_alignment_required", "deterministic_serialization_identity_required",
    "corruption_detection_required", "unsupported_schema_rejected", "downgrade_rejected",
    "partial_record_rejected", "identity_conflict_rejected", "recovery_verification_required",
    "database_repair_authorized", "destructive_recovery_authorized",
)
_LIFECYCLE_FIELDS = (
    "lifecycle_policy_id", "explicit_initialize_required", "explicit_readiness_validation_required",
    "explicit_shutdown_required", "schema_compatibility_validation_required", "migration_enabled",
    "startup_recovery_required", "clean_shutdown_evidence_required", "background_migration_allowed",
    "background_compaction_allowed", "implicit_database_creation_allowed",
    "implicit_directory_creation_allowed", "destructive_reset_allowed",
    "automatic_memory_fallback_allowed", "automatic_adapter_fallback_allowed",
    "initialize_authorized", "create_authorized", "migrate_authorized", "repair_authorized",
    "persist_authorized", "mutate_authorized",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_RESULT_FIELDS = (
    "adapter_id", "design_valid", "adapter_selected", "storage_accessible", "schema_compatible",
    "migration_required", "migration_authorized", "corruption_detected", "recovery_required",
    "adapter_ready", "production_persistence_authorized", "failure_codes",
)
_AUDIT_FIELDS = (
    "adapter_id", "adapter_version", "storage_technology", "schema_id", "schema_version",
    "transaction_policy_id", "integrity_policy_id", "lifecycle_policy_id", "design_valid",
    "adapter_selected", "schema_compatible", "adapter_ready", "recovery_required",
    "production_persistence_authorized", "failure_codes", "persistence_authorized",
    "reservation_creation_authorized", "ledger_mutation_authorized", "provider_transmission_authorized",
    "provider_execution_authorized",
)
_FAILURES = {
    "ADAPTER_ID_EMPTY", "ADAPTER_VERSION_EMPTY", "STORAGE_TECHNOLOGY_EMPTY", "STORAGE_MODE_EMPTY",
    "STORAGE_LOCATION_CLASSIFICATION_EMPTY", "SCHEMA_ID_EMPTY", "SCHEMA_VERSION_INVALID",
    "TRANSACTION_POLICY_ID_EMPTY", "INTEGRITY_POLICY_ID_EMPTY", "LIFECYCLE_POLICY_ID_EMPTY",
    "IDENTIFIER_NOT_NORMALIZED", "STORAGE_TECHNOLOGY_NOT_ALLOWED", "PRODUCTION_ADAPTER_NOT_SELECTED",
    "STORAGE_ACCESS_NOT_AUTHORIZED", "SCHEMA_CREATION_NOT_AUTHORIZED", "MIGRATION_NOT_AUTHORIZED",
    "PERSISTENCE_NOT_AUTHORIZED", "RESERVATION_CREATION_NOT_AUTHORIZED",
    "LEDGER_MUTATION_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
    "PROVIDER_EXECUTION_NOT_AUTHORIZED", "ATOMIC_COMPARE_AND_APPEND_NOT_REQUIRED",
    "SNAPSHOT_EVENT_TRANSACTION_NOT_ATOMIC", "REVISION_CHECK_NOT_REQUIRED",
    "LAST_EVENT_CHECK_NOT_REQUIRED", "UNIQUENESS_CHECK_NOT_REQUIRED", "PARTIAL_APPEND_ALLOWED",
    "AUTOMATIC_RETRY_ALLOWED", "APPEND_ONLY_NOT_REQUIRED", "EVENT_UPDATE_ALLOWED",
    "EVENT_DELETE_ALLOWED", "REVISION_MONOTONICITY_NOT_REQUIRED",
    "CORRUPTION_DETECTION_NOT_REQUIRED", "AUTOMATIC_REPAIR_ALLOWED",
    "DESTRUCTIVE_RECOVERY_ALLOWED", "IMPLICIT_DATABASE_CREATION_ALLOWED",
    "IMPLICIT_DIRECTORY_CREATION_ALLOWED", "AUTOMATIC_MEMORY_FALLBACK_ALLOWED",
    "AUTOMATIC_ADAPTER_FALLBACK_ALLOWED", "BACKGROUND_MIGRATION_ALLOWED",
    "SCHEMA_COMPATIBILITY_NOT_REQUIRED", "STARTUP_RECOVERY_NOT_REQUIRED", "DESIGN_INVALID",
    "ADAPTER_NOT_READY", "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED",
}


def _design(**overrides: object) -> DurableStorageAdapterDesignV1:
    values = {
        "adapter_id": "durable-storage-adapter-v1", "adapter_version": "V1",
        "storage_technology": "UNSELECTED", "storage_mode": "DURABLE", "storage_location_classification": "UNCONFIGURED",
        "schema_id": "durable-reservation-schema-v1", "schema_version": 1,
        "transaction_policy_id": "durable-transaction-policy-v1", "integrity_policy_id": "durable-integrity-policy-v1",
        "lifecycle_policy_id": "durable-lifecycle-policy-v1", "production_adapter_selected": False,
        "storage_access_authorized": False, "schema_creation_authorized": False, "migration_authorized": False,
        "persistence_authorized": False, "reservation_creation_authorized": False,
        "ledger_mutation_authorized": False, "provider_transmission_authorized": False,
        "provider_execution_authorized": False,
    }
    values.update(overrides)
    return DurableStorageAdapterDesignV1(**values)


def _schema(**overrides: object) -> DurableStorageSchemaDesignV1:
    values = {
        "schema_id": "durable-reservation-schema-v1", "schema_version": 1,
        "logical_entities": ("RESERVATION_SNAPSHOT", "APPEND_ONLY_LEDGER_EVENT", "COMMAND_IDEMPOTENCY", "RECOVERY_EVIDENCE", "SCHEMA_METADATA"),
        "uniqueness_constraints": ("PERSISTENCE_COMMAND_ID", "RESERVATION_ID", "RESERVATION_REQUEST_ID", "REQUEST_ID", "IDEMPOTENCY_KEY", "LEDGER_EVENT_ID", "RESERVATION_REVISION"),
        "identity_alignments": ("SNAPSHOT_RESERVATION", "EVENT_RESERVATION", "EVENT_REQUEST", "EVENT_REVISION", "RECOVERY_COMMAND"),
        "append_only_events_required": True, "event_update_forbidden": True, "event_delete_forbidden": True,
        "revision_monotonicity_required": True, "exactly_one_current_snapshot_required": True,
        "complete_snapshot_event_alignment_required": True,
    }
    values.update(overrides)
    return DurableStorageSchemaDesignV1(**values)


def _transaction(**overrides: object) -> DurableStorageTransactionPolicyV1:
    values = {
        "transaction_policy_id": "durable-transaction-policy-v1", "atomic_compare_and_append_required": True,
        "snapshot_event_single_transaction_required": True, "revision_comparison_required": True,
        "last_event_comparison_required": True, "uniqueness_checks_required": True,
        "rollback_on_failure_required": True, "partial_append_forbidden": True,
        "automatic_retry_forbidden": True, "busy_conflicts_fail_closed": True,
        "uncertain_commit_recovery_read_required": True, "transaction_timeout_seconds": 30,
        "transaction_authorized": False, "maximum_persistence_attempts": 1,
    }
    values.update(overrides)
    return DurableStorageTransactionPolicyV1(**values)


def _integrity(**overrides: object) -> DurableStorageIntegrityPolicyV1:
    values = {
        "integrity_policy_id": "durable-integrity-policy-v1", "append_only_event_history_required": True,
        "immutable_event_identity_required": True, "snapshot_event_revision_alignment_required": True,
        "deterministic_serialization_identity_required": True, "corruption_detection_required": True,
        "unsupported_schema_rejected": True, "downgrade_rejected": True, "partial_record_rejected": True,
        "identity_conflict_rejected": True, "recovery_verification_required": True,
        "database_repair_authorized": False, "destructive_recovery_authorized": False,
    }
    values.update(overrides)
    return DurableStorageIntegrityPolicyV1(**values)


def _lifecycle(**overrides: object) -> DurableStorageLifecyclePolicyV1:
    values = {
        "lifecycle_policy_id": "durable-lifecycle-policy-v1", "explicit_initialize_required": True,
        "explicit_readiness_validation_required": True, "explicit_shutdown_required": True,
        "schema_compatibility_validation_required": True, "migration_enabled": False,
        "startup_recovery_required": True, "clean_shutdown_evidence_required": True,
        "background_migration_allowed": False, "background_compaction_allowed": False,
        "implicit_database_creation_allowed": False, "implicit_directory_creation_allowed": False,
        "destructive_reset_allowed": False, "automatic_memory_fallback_allowed": False,
        "automatic_adapter_fallback_allowed": False, "initialize_authorized": False,
        "create_authorized": False, "migrate_authorized": False, "repair_authorized": False,
        "persist_authorized": False, "mutate_authorized": False,
    }
    values.update(overrides)
    return DurableStorageLifecyclePolicyV1(**values)


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_pure_and_narrow() -> None:
    assert tuple(field.name for field in fields(DurableStorageAdapterDesignV1)) == _ADAPTER_FIELDS
    assert tuple(field.name for field in fields(DurableStorageSchemaDesignV1)) == _SCHEMA_FIELDS
    assert tuple(field.name for field in fields(DurableStorageTransactionPolicyV1)) == _TRANSACTION_FIELDS
    assert tuple(field.name for field in fields(DurableStorageIntegrityPolicyV1)) == _INTEGRITY_FIELDS
    assert tuple(field.name for field in fields(DurableStorageLifecyclePolicyV1)) == _LIFECYCLE_FIELDS
    assert tuple(field.name for field in fields(DurableStorageDesignFailureV1)) == _FAILURE_FIELDS
    assert tuple(field.name for field in fields(DurableStorageDesignValidationResultV1)) == _RESULT_FIELDS
    assert tuple(field.name for field in fields(DurableStorageDesignAuditEvidenceV1)) == _AUDIT_FIELDS
    design, schema, transaction, integrity, lifecycle = _design(), _schema(), _transaction(), _integrity(), _lifecycle()
    result = validate_durable_storage_adapter_design_v1(design, schema, transaction, integrity, lifecycle)
    evidence = build_durable_storage_design_audit_evidence_v1(design, schema, transaction, integrity, lifecycle, result)
    for value in (design, schema, transaction, integrity, lifecycle, result, evidence):
        _frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        design.persistence_authorized = True  # type: ignore[misc]
    assert list(inspect.signature(validate_durable_storage_adapter_design_v1).parameters) == [
        "adapter_design", "schema_design", "transaction_policy", "integrity_policy", "lifecycle_policy",
    ]
    assert list(inspect.signature(build_durable_storage_design_audit_evidence_v1).parameters) == [
        "adapter_design", "schema_design", "transaction_policy", "integrity_policy", "lifecycle_policy", "result",
    ]


def test_zero_authority_design_is_never_operational_or_production_ready() -> None:
    result = validate_durable_storage_adapter_design_v1(_design(), _schema(), _transaction(), _integrity(), _lifecycle())
    assert result.adapter_selected is False
    assert result.storage_accessible is False
    assert result.adapter_ready is False
    assert result.production_persistence_authorized is False
    assert {
        "STORAGE_TECHNOLOGY_NOT_ALLOWED", "PRODUCTION_ADAPTER_NOT_SELECTED", "STORAGE_ACCESS_NOT_AUTHORIZED",
        "SCHEMA_CREATION_NOT_AUTHORIZED", "MIGRATION_NOT_AUTHORIZED", "PERSISTENCE_NOT_AUTHORIZED",
        "RESERVATION_CREATION_NOT_AUTHORIZED", "LEDGER_MUTATION_NOT_AUTHORIZED",
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED",
        "ADAPTER_NOT_READY", "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)


def test_transaction_schema_integrity_and_lifecycle_rejections_are_fail_closed() -> None:
    result = validate_durable_storage_adapter_design_v1(
        _design(storage_technology="SQLITE", production_adapter_selected=True, storage_access_authorized=True),
        _schema(append_only_events_required=False, event_update_forbidden=False, event_delete_forbidden=False, revision_monotonicity_required=False),
        _transaction(atomic_compare_and_append_required=False, snapshot_event_single_transaction_required=False,
                     revision_comparison_required=False, last_event_comparison_required=False,
                     uniqueness_checks_required=False, partial_append_forbidden=False,
                     automatic_retry_forbidden=False, maximum_persistence_attempts=2),
        _integrity(corruption_detection_required=False, database_repair_authorized=True, destructive_recovery_authorized=True),
        _lifecycle(schema_compatibility_validation_required=False, startup_recovery_required=False,
                   background_migration_allowed=True, implicit_database_creation_allowed=True,
                   implicit_directory_creation_allowed=True, automatic_memory_fallback_allowed=True,
                   automatic_adapter_fallback_allowed=True),
    )
    assert {
        "ATOMIC_COMPARE_AND_APPEND_NOT_REQUIRED", "SNAPSHOT_EVENT_TRANSACTION_NOT_ATOMIC",
        "REVISION_CHECK_NOT_REQUIRED", "LAST_EVENT_CHECK_NOT_REQUIRED", "UNIQUENESS_CHECK_NOT_REQUIRED",
        "PARTIAL_APPEND_ALLOWED", "AUTOMATIC_RETRY_ALLOWED", "APPEND_ONLY_NOT_REQUIRED",
        "EVENT_UPDATE_ALLOWED", "EVENT_DELETE_ALLOWED", "REVISION_MONOTONICITY_NOT_REQUIRED",
        "CORRUPTION_DETECTION_NOT_REQUIRED", "AUTOMATIC_REPAIR_ALLOWED",
        "DESTRUCTIVE_RECOVERY_ALLOWED", "IMPLICIT_DATABASE_CREATION_ALLOWED",
        "IMPLICIT_DIRECTORY_CREATION_ALLOWED", "AUTOMATIC_MEMORY_FALLBACK_ALLOWED",
        "AUTOMATIC_ADAPTER_FALLBACK_ALLOWED", "BACKGROUND_MIGRATION_ALLOWED",
        "SCHEMA_COMPATIBILITY_NOT_REQUIRED", "STARTUP_RECOVERY_NOT_REQUIRED",
    }.issubset(result.failure_codes)
    assert result.adapter_ready is False and result.production_persistence_authorized is False


def test_audit_evidence_is_deterministic_identity_bound_and_non_operational() -> None:
    design, schema, transaction, integrity, lifecycle = _design(), _schema(), _transaction(), _integrity(), _lifecycle()
    result = validate_durable_storage_adapter_design_v1(design, schema, transaction, integrity, lifecycle)
    evidence = build_durable_storage_design_audit_evidence_v1(design, schema, transaction, integrity, lifecycle, result)
    assert evidence == build_durable_storage_design_audit_evidence_v1(design, schema, transaction, integrity, lifecycle, result)
    assert evidence.persistence_authorized is evidence.reservation_creation_authorized is False
    assert evidence.ledger_mutation_authorized is evidence.provider_transmission_authorized is False
    assert evidence.provider_execution_authorized is False
    with pytest.raises(ValueError):
        build_durable_storage_design_audit_evidence_v1(_design(adapter_id="other-adapter-v1"), schema, transaction, integrity, lifecycle, result)
    import engine.phase_12_durable_storage_adapter_design_v1 as module
    prohibited = {"os", "pathlib", "tempfile", "sqlite3", "sqlalchemy", "subprocess", "socket", "urllib", "requests", "httpx", "aiohttp", "openai", "telegram", "ccxt"}
    assert not prohibited.intersection(module.__dict__)
