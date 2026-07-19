"""RED contract for a future injected SQLite durable-storage adapter."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from engine.phase_12_sqlite_durable_storage_adapter_contract_v1 import (
    SQLiteAdapterAuditEvidenceV1,
    SQLiteAdapterFailureV1,
    SQLiteAdapterReadinessResultV1,
    SQLiteCompareAndAppendResultV1,
    SQLiteConnectionFactoryV1,
    SQLiteRecoveryReadResultV1,
    SQLiteReservationPersistenceAdapterV1,
    SQLiteSchemaManifestV1,
    SQLiteStorageAdapterConfigurationV1,
    build_sqlite_adapter_audit_evidence_v1,
    validate_sqlite_schema_manifest_v1,
    validate_sqlite_storage_configuration_v1,
)


_CONFIG_FIELDS = (
    "adapter_id", "adapter_version", "database_identity", "storage_location",
    "storage_location_classification", "schema_id", "expected_schema_version",
    "connection_timeout_seconds", "transaction_timeout_seconds", "busy_timeout_milliseconds",
    "journal_mode", "synchronous_mode", "foreign_keys_required", "query_only_on_recovery",
    "immutable_reads_preferred", "uri_mode", "create_database_if_missing",
    "create_directory_if_missing", "migration_authorized", "repair_authorized",
    "storage_access_authorized", "schema_creation_authorized", "persistence_authorized",
    "reservation_creation_authorized", "ledger_mutation_authorized",
    "provider_transmission_authorized", "provider_execution_authorized",
)
_MANIFEST_FIELDS = (
    "schema_id", "schema_version", "minimum_supported_version", "maximum_supported_version",
    "snapshot_table", "event_table", "command_table", "recovery_table", "metadata_table",
    "required_indexes", "required_unique_constraints", "required_foreign_keys",
    "append_only_triggers_required", "event_update_forbidden", "event_delete_forbidden",
    "revision_monotonicity_required", "snapshot_event_alignment_required",
    "schema_hash_identity", "migrations_available", "destructive_migration_available",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_READINESS_FIELDS = (
    "adapter_id", "configuration_valid", "factory_supplied", "factory_invoked",
    "connection_opened", "schema_readable", "schema_compatible", "migration_required",
    "corruption_detected", "recovery_required", "adapter_ready",
    "production_persistence_authorized", "failure_codes",
)
_APPEND_FIELDS = (
    "adapter_id", "accepted", "failure_codes", "factory_invoked", "connection_opened",
    "append_attempted", "append_confirmed", "rollback_attempted", "rollback_confirmed",
    "recovery_required", "snapshot",
)
_RECOVERY_FIELDS = (
    "adapter_id", "reservation_id", "request_id", "recovered", "found", "revision_current",
    "identity_aligned", "failure_codes", "factory_invoked", "connection_opened",
    "read_attempted", "recovery_required", "snapshot", "provider_contacted",
    "transmitted", "provider_execution_authorized",
)
_AUDIT_FIELDS = (
    "adapter_id", "database_identity", "schema_id", "expected_schema_version", "journal_mode",
    "synchronous_mode", "connection_timeout_seconds", "transaction_timeout_seconds",
    "busy_timeout_milliseconds", "configuration_valid", "schema_compatible", "factory_invoked",
    "connection_opened", "append_attempted", "append_confirmed", "rollback_confirmed",
    "recovery_required", "failure_codes", "storage_access_authorized",
    "schema_creation_authorized", "migration_authorized", "persistence_authorized",
    "reservation_creation_authorized", "ledger_mutation_authorized",
    "provider_transmission_authorized", "provider_execution_authorized",
)
_FAILURES = {
    "ADAPTER_ID_EMPTY", "ADAPTER_VERSION_EMPTY", "DATABASE_IDENTITY_EMPTY", "STORAGE_LOCATION_EMPTY",
    "STORAGE_LOCATION_NOT_NORMALIZED", "STORAGE_LOCATION_NOT_ALLOWED", "STORAGE_LOCATION_TRAVERSAL_DETECTED",
    "IN_MEMORY_DATABASE_NOT_ALLOWED", "TEMPORARY_DATABASE_NOT_ALLOWED", "SCHEMA_ID_EMPTY",
    "EXPECTED_SCHEMA_VERSION_INVALID", "CONNECTION_TIMEOUT_INVALID", "TRANSACTION_TIMEOUT_INVALID",
    "BUSY_TIMEOUT_INVALID", "JOURNAL_MODE_NOT_ALLOWED", "SYNCHRONOUS_MODE_NOT_ALLOWED",
    "FOREIGN_KEYS_NOT_REQUIRED", "QUERY_ONLY_RECOVERY_NOT_REQUIRED", "CONNECTION_FACTORY_REQUIRED",
    "STORAGE_ACCESS_NOT_AUTHORIZED", "DATABASE_CREATION_NOT_AUTHORIZED", "DIRECTORY_CREATION_NOT_AUTHORIZED",
    "SCHEMA_CREATION_NOT_AUTHORIZED", "MIGRATION_NOT_AUTHORIZED", "REPAIR_NOT_AUTHORIZED",
    "PERSISTENCE_NOT_AUTHORIZED", "RESERVATION_CREATION_NOT_AUTHORIZED", "LEDGER_MUTATION_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED", "SCHEMA_IDENTITY_MISMATCH",
    "SCHEMA_VERSION_UNSUPPORTED", "SCHEMA_MIGRATION_REQUIRED", "SCHEMA_HASH_MISMATCH",
    "REQUIRED_TABLE_MISSING", "REQUIRED_INDEX_MISSING", "REQUIRED_UNIQUE_CONSTRAINT_MISSING",
    "REQUIRED_FOREIGN_KEY_MISSING", "APPEND_ONLY_ENFORCEMENT_MISSING", "EVENT_UPDATE_NOT_FORBIDDEN",
    "EVENT_DELETE_NOT_FORBIDDEN", "REVISION_MONOTONICITY_NOT_ENFORCED",
    "SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED", "ADAPTER_NOT_READY", "ADAPTER_CLOSED",
    "CONNECTION_FAILURE", "SQLITE_BUSY", "SQLITE_LOCKED", "TRANSACTION_TIMEOUT", "REVISION_CONFLICT",
    "LAST_EVENT_ID_CONFLICT", "IDEMPOTENCY_CONFLICT", "EVENT_IDENTITY_CONFLICT",
    "PARTIAL_APPEND_DETECTED", "COMMIT_OUTCOME_UNCERTAIN", "ROLLBACK_FAILURE",
    "CORRUPTION_DETECTED", "RECOVERY_REQUIRED", "RECOVERY_READ_FAILED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


def _configuration(**overrides: object) -> SQLiteStorageAdapterConfigurationV1:
    values = {
        "adapter_id": "sqlite-adapter-v1", "adapter_version": "V1", "database_identity": "reservation-store-v1",
        "storage_location": "controlled/reservations-v1.sqlite", "storage_location_classification": "EXPLICIT_CONTROLLED",
        "schema_id": "sqlite-reservation-schema-v1", "expected_schema_version": 1,
        "connection_timeout_seconds": 5, "transaction_timeout_seconds": 10, "busy_timeout_milliseconds": 1000,
        "journal_mode": "WAL", "synchronous_mode": "FULL", "foreign_keys_required": True,
        "query_only_on_recovery": True, "immutable_reads_preferred": True, "uri_mode": False,
        "create_database_if_missing": False, "create_directory_if_missing": False,
        "migration_authorized": False, "repair_authorized": False, "storage_access_authorized": False,
        "schema_creation_authorized": False, "persistence_authorized": False,
        "reservation_creation_authorized": False, "ledger_mutation_authorized": False,
        "provider_transmission_authorized": False, "provider_execution_authorized": False,
    }
    values.update(overrides)
    return SQLiteStorageAdapterConfigurationV1(**values)


def _manifest(**overrides: object) -> SQLiteSchemaManifestV1:
    values = {
        "schema_id": "sqlite-reservation-schema-v1", "schema_version": 1,
        "minimum_supported_version": 1, "maximum_supported_version": 1,
        "snapshot_table": "reservation_snapshots", "event_table": "reservation_events",
        "command_table": "persistence_commands", "recovery_table": "recovery_evidence",
        "metadata_table": "schema_metadata", "required_indexes": ("RESERVATION_REVISION_INDEX",),
        "required_unique_constraints": ("PERSISTENCE_COMMAND_ID", "RESERVATION_ID", "IDEMPOTENCY_KEY", "EVENT_ID"),
        "required_foreign_keys": ("EVENT_RESERVATION", "EVENT_REQUEST", "RECOVERY_COMMAND"),
        "append_only_triggers_required": True, "event_update_forbidden": True,
        "event_delete_forbidden": True, "revision_monotonicity_required": True,
        "snapshot_event_alignment_required": True, "schema_hash_identity": "schema-hash-v1",
        "migrations_available": False, "destructive_migration_available": False,
    }
    values.update(overrides)
    return SQLiteSchemaManifestV1(**values)


class _Factory:
    def __init__(self) -> None:
        self.calls = 0

    def connect(self, configuration: SQLiteStorageAdapterConfigurationV1) -> object:
        self.calls += 1
        return object()


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_narrow_and_connection_factory_injected() -> None:
    assert tuple(field.name for field in fields(SQLiteStorageAdapterConfigurationV1)) == _CONFIG_FIELDS
    assert tuple(field.name for field in fields(SQLiteSchemaManifestV1)) == _MANIFEST_FIELDS
    assert tuple(field.name for field in fields(SQLiteAdapterFailureV1)) == _FAILURE_FIELDS
    assert tuple(field.name for field in fields(SQLiteAdapterReadinessResultV1)) == _READINESS_FIELDS
    assert tuple(field.name for field in fields(SQLiteCompareAndAppendResultV1)) == _APPEND_FIELDS
    assert tuple(field.name for field in fields(SQLiteRecoveryReadResultV1)) == _RECOVERY_FIELDS
    assert tuple(field.name for field in fields(SQLiteAdapterAuditEvidenceV1)) == _AUDIT_FIELDS
    assert hasattr(SQLiteConnectionFactoryV1, "connect")
    assert {"validate_readiness", "compare_and_append", "read_reservation", "close"}.issubset(dir(SQLiteReservationPersistenceAdapterV1))
    assert not {"execute", "executemany", "executescript", "query", "delete", "truncate", "vacuum", "attach", "detach"}.intersection(dir(SQLiteReservationPersistenceAdapterV1))
    factory = _Factory()
    readiness = validate_sqlite_storage_configuration_v1(_configuration(), factory)
    manifest_result = validate_sqlite_schema_manifest_v1(_configuration(), _manifest())
    evidence = build_sqlite_adapter_audit_evidence_v1(_configuration(), readiness, manifest_result, None, None)
    for value in (_configuration(), _manifest(), readiness, manifest_result, evidence):
        _frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        _configuration().persistence_authorized = True  # type: ignore[misc]
    assert factory.calls == 0
    assert list(inspect.signature(validate_sqlite_storage_configuration_v1).parameters) == ["configuration", "connection_factory"]
    assert list(inspect.signature(validate_sqlite_schema_manifest_v1).parameters) == ["configuration", "schema_manifest"]


def test_fail_closed_configuration_rejects_location_modes_authorities_and_never_connects() -> None:
    factory = _Factory()
    result = validate_sqlite_storage_configuration_v1(
        _configuration(storage_location="../unsafe", journal_mode="DELETE", synchronous_mode="NORMAL",
                       foreign_keys_required=False, query_only_on_recovery=False,
                       create_database_if_missing=True, create_directory_if_missing=True),
        factory,
    )
    assert {
        "STORAGE_LOCATION_TRAVERSAL_DETECTED", "JOURNAL_MODE_NOT_ALLOWED", "SYNCHRONOUS_MODE_NOT_ALLOWED",
        "FOREIGN_KEYS_NOT_REQUIRED", "QUERY_ONLY_RECOVERY_NOT_REQUIRED", "DATABASE_CREATION_NOT_AUTHORIZED",
        "DIRECTORY_CREATION_NOT_AUTHORIZED", "STORAGE_ACCESS_NOT_AUTHORIZED",
        "SCHEMA_CREATION_NOT_AUTHORIZED", "MIGRATION_NOT_AUTHORIZED", "REPAIR_NOT_AUTHORIZED",
        "PERSISTENCE_NOT_AUTHORIZED", "RESERVATION_CREATION_NOT_AUTHORIZED",
        "LEDGER_MUTATION_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
        "PROVIDER_EXECUTION_NOT_AUTHORIZED", "ADAPTER_NOT_READY",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert factory.calls == 0
    assert result.factory_invoked is result.connection_opened is result.adapter_ready is False
    assert result.production_persistence_authorized is False


def test_schema_manifest_contract_is_logical_fail_closed_and_never_migrates() -> None:
    result = validate_sqlite_schema_manifest_v1(
        _configuration(),
        _manifest(schema_id="other-schema-v1", schema_version=2, required_indexes=(),
                  required_unique_constraints=(), required_foreign_keys=(),
                  append_only_triggers_required=False, event_update_forbidden=False,
                  event_delete_forbidden=False, revision_monotonicity_required=False,
                  snapshot_event_alignment_required=False, schema_hash_identity=""),
    )
    assert {
        "SCHEMA_IDENTITY_MISMATCH", "SCHEMA_VERSION_UNSUPPORTED", "REQUIRED_INDEX_MISSING",
        "REQUIRED_UNIQUE_CONSTRAINT_MISSING", "REQUIRED_FOREIGN_KEY_MISSING",
        "APPEND_ONLY_ENFORCEMENT_MISSING", "EVENT_UPDATE_NOT_FORBIDDEN",
        "EVENT_DELETE_NOT_FORBIDDEN", "REVISION_MONOTONICITY_NOT_ENFORCED",
        "SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED", "SCHEMA_HASH_MISMATCH", "ADAPTER_NOT_READY",
    }.issubset(result.failure_codes)
    assert result.migration_required is True
    assert result.adapter_ready is False and result.production_persistence_authorized is False


def test_audit_evidence_is_deterministic_redacted_and_identity_bound() -> None:
    configuration, manifest, factory = _configuration(), _manifest(), _Factory()
    readiness = validate_sqlite_storage_configuration_v1(configuration, factory)
    manifest_result = validate_sqlite_schema_manifest_v1(configuration, manifest)
    evidence = build_sqlite_adapter_audit_evidence_v1(configuration, readiness, manifest_result, None, None)
    assert evidence == build_sqlite_adapter_audit_evidence_v1(configuration, readiness, manifest_result, None, None)
    assert evidence.factory_invoked is evidence.connection_opened is evidence.append_attempted is False
    assert evidence.provider_transmission_authorized is evidence.provider_execution_authorized is False
    with pytest.raises(ValueError):
        build_sqlite_adapter_audit_evidence_v1(_configuration(adapter_id="other-adapter-v1"), readiness, manifest_result, None, None)
