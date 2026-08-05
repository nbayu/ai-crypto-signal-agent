"""RED contract for a future isolated sqlite3 connection/bootstrap boundary."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from engine.phase_12_sqlite_connection_factory_schema_bootstrap_v1 import (
    SQLiteConnectionAuditEvidenceV1,
    SQLiteConnectionConfigurationV1,
    SQLiteConnectionFactoryImplementationV1,
    SQLiteConnectionFailureV1,
    SQLiteConnectionHandleV1,
    SQLiteConnectionReadinessResultV1,
    SQLiteSchemaBootstrapManifestV1,
    SQLiteSchemaBootstrapResultV1,
    bootstrap_sqlite_schema_v1,
    build_sqlite_connection_audit_evidence_v1,
    validate_sqlite_connection_configuration_v1,
    validate_sqlite_connection_readiness_v1,
)


_CONFIG_FIELDS = (
    "connection_configuration_id", "database_identity", "database_location", "location_classification",
    "expected_schema_id", "expected_schema_version", "connection_timeout_seconds",
    "transaction_timeout_seconds", "busy_timeout_milliseconds", "journal_mode", "synchronous_mode",
    "foreign_keys_required", "wal_autocheckpoint_pages", "query_only", "uri_mode",
    "create_database_if_missing", "create_directory_if_missing", "schema_bootstrap_authorized",
    "schema_migration_authorized", "repair_authorized", "storage_access_authorized",
    "production_path_authorized", "persistence_authorized",
)
_MANIFEST_FIELDS = (
    "schema_id", "schema_version", "schema_metadata_table", "snapshot_table", "event_table",
    "command_table", "recovery_table", "required_indexes", "required_unique_constraints",
    "required_foreign_keys", "append_only_enforcement_required", "revision_monotonicity_required",
    "snapshot_event_alignment_required", "schema_hash_identity", "ddl_order", "migrations_available",
    "destructive_migration_available",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_READINESS_FIELDS = (
    "connection_configuration_id", "configuration_valid", "location_authorized", "factory_supplied",
    "connection_attempted", "connection_opened", "pragmas_verified", "schema_present",
    "schema_compatible", "bootstrap_required", "migration_required", "corruption_detected",
    "recovery_required", "connection_closed_cleanly", "adapter_ready", "persistence_authorized",
    "production_path_authorized", "failure_codes",
)
_BOOTSTRAP_FIELDS = (
    "connection_configuration_id", "bootstrap_attempted", "bootstrap_confirmed", "rollback_attempted",
    "rollback_confirmed", "uncertain_outcome", "connection_attempted", "connection_opened",
    "pragmas_verified", "schema_compatible", "connection_closed_cleanly", "failure_codes",
)
_AUDIT_FIELDS = (
    "connection_configuration_id", "database_identity", "location_classification", "schema_id",
    "schema_version", "schema_hash_identity", "connection_attempted", "connection_opened",
    "bootstrap_attempted", "bootstrap_confirmed", "rollback_confirmed", "uncertain_outcome",
    "pragmas_verified", "schema_compatible", "connection_closed_cleanly", "adapter_ready",
    "persistence_authorized", "production_path_authorized", "failure_codes",
)
_FAILURES = {
    "CONNECTION_CONFIGURATION_ID_EMPTY", "DATABASE_IDENTITY_EMPTY", "DATABASE_LOCATION_EMPTY",
    "LOCATION_CLASSIFICATION_EMPTY", "LOCATION_CLASSIFICATION_NOT_ALLOWED", "DATABASE_LOCATION_NOT_NORMALIZED",
    "DATABASE_LOCATION_TRAVERSAL_DETECTED", "ENVIRONMENT_EXPANSION_NOT_ALLOWED",
    "HOME_EXPANSION_NOT_ALLOWED", "IN_MEMORY_DATABASE_NOT_ALLOWED", "TEMPORARY_UNNAMED_DATABASE_NOT_ALLOWED",
    "REPOSITORY_DATABASE_NOT_ALLOWED", "PRODUCTION_PATH_NOT_AUTHORIZED", "EXPECTED_SCHEMA_ID_EMPTY",
    "EXPECTED_SCHEMA_VERSION_INVALID", "CONNECTION_TIMEOUT_INVALID", "TRANSACTION_TIMEOUT_INVALID",
    "BUSY_TIMEOUT_INVALID", "WAL_AUTOCHECKPOINT_INVALID", "JOURNAL_MODE_NOT_ALLOWED",
    "SYNCHRONOUS_MODE_NOT_ALLOWED", "FOREIGN_KEYS_NOT_REQUIRED", "CONNECTION_FACTORY_REQUIRED",
    "STORAGE_ACCESS_NOT_AUTHORIZED", "DATABASE_CREATION_NOT_AUTHORIZED", "DIRECTORY_CREATION_NOT_AUTHORIZED",
    "SCHEMA_BOOTSTRAP_NOT_AUTHORIZED", "SCHEMA_MIGRATION_NOT_AUTHORIZED", "REPAIR_NOT_AUTHORIZED",
    "PERSISTENCE_NOT_AUTHORIZED", "TARGET_DATABASE_ALREADY_EXISTS", "TARGET_DATABASE_NOT_EMPTY",
    "SCHEMA_MANIFEST_INVALID", "SCHEMA_IDENTITY_MISMATCH", "SCHEMA_VERSION_MISMATCH",
    "SCHEMA_HASH_MISMATCH", "REQUIRED_TABLE_MISSING", "REQUIRED_INDEX_MISSING",
    "REQUIRED_UNIQUE_CONSTRAINT_MISSING", "REQUIRED_FOREIGN_KEY_MISSING",
    "APPEND_ONLY_ENFORCEMENT_MISSING", "REVISION_MONOTONICITY_NOT_ENFORCED",
    "SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED", "PRAGMA_JOURNAL_MODE_MISMATCH",
    "PRAGMA_SYNCHRONOUS_MODE_MISMATCH", "PRAGMA_FOREIGN_KEYS_DISABLED",
    "PRAGMA_BUSY_TIMEOUT_MISMATCH", "PRAGMA_WAL_AUTOCHECKPOINT_MISMATCH", "CONNECTION_FAILURE",
    "TRANSACTION_BEGIN_FAILURE", "SCHEMA_BOOTSTRAP_FAILURE", "SCHEMA_BOOTSTRAP_PARTIAL",
    "COMMIT_OUTCOME_UNCERTAIN", "ROLLBACK_FAILURE", "CONNECTION_CLOSE_FAILURE", "CONNECTION_CLOSED",
    "RAW_DATABASE_PATH_EXPOSURE_DETECTED", "RAW_SQL_EXPOSURE_DETECTED",
    "RAW_EXCEPTION_EXPOSURE_DETECTED", "ADAPTER_NOT_READY", "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED",
}


def _configuration(database_location: str, **overrides: object) -> SQLiteConnectionConfigurationV1:
    values = {
        "connection_configuration_id": "sqlite-connection-config-v1", "database_identity": "bootstrap-store-v1",
        "database_location": database_location, "location_classification": "TEST_EPHEMERAL",
        "expected_schema_id": "sqlite-bootstrap-schema-v1", "expected_schema_version": 1,
        "connection_timeout_seconds": 5, "transaction_timeout_seconds": 10,
        "busy_timeout_milliseconds": 1000, "journal_mode": "WAL", "synchronous_mode": "FULL",
        "foreign_keys_required": True, "wal_autocheckpoint_pages": 1000, "query_only": False,
        "uri_mode": False, "create_database_if_missing": False, "create_directory_if_missing": False,
        "schema_bootstrap_authorized": False, "schema_migration_authorized": False,
        "repair_authorized": False, "storage_access_authorized": False,
        "production_path_authorized": False, "persistence_authorized": False,
    }
    values.update(overrides)
    return SQLiteConnectionConfigurationV1(**values)


def _manifest(**overrides: object) -> SQLiteSchemaBootstrapManifestV1:
    values = {
        "schema_id": "sqlite-bootstrap-schema-v1", "schema_version": 1,
        "schema_metadata_table": "schema_metadata", "snapshot_table": "reservation_snapshots",
        "event_table": "reservation_events", "command_table": "persistence_commands",
        "recovery_table": "recovery_evidence", "required_indexes": ("RESERVATION_REVISION_INDEX",),
        "required_unique_constraints": ("PERSISTENCE_COMMAND_ID", "RESERVATION_ID", "IDEMPOTENCY_KEY", "EVENT_ID"),
        "required_foreign_keys": ("EVENT_RESERVATION", "EVENT_REQUEST", "RECOVERY_COMMAND"),
        "append_only_enforcement_required": True, "revision_monotonicity_required": True,
        "snapshot_event_alignment_required": True, "schema_hash_identity": "bootstrap-schema-hash-v1",
        "ddl_order": ("METADATA", "SNAPSHOTS", "EVENTS", "COMMANDS", "RECOVERY", "INDEXES"),
        "migrations_available": False, "destructive_migration_available": False,
    }
    values.update(overrides)
    return SQLiteSchemaBootstrapManifestV1(**values)


class _FailIfCalledFactory:
    def __init__(self) -> None:
        self.calls = 0

    def connect(self, configuration: SQLiteConnectionConfigurationV1) -> object:
        self.calls += 1
        raise AssertionError("factory must not run for failed preconditions")


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_narrow_and_redacted() -> None:
    assert tuple(field.name for field in fields(SQLiteConnectionConfigurationV1)) == _CONFIG_FIELDS
    assert tuple(field.name for field in fields(SQLiteSchemaBootstrapManifestV1)) == _MANIFEST_FIELDS
    assert tuple(field.name for field in fields(SQLiteConnectionFailureV1)) == _FAILURE_FIELDS
    assert tuple(field.name for field in fields(SQLiteConnectionReadinessResultV1)) == _READINESS_FIELDS
    assert tuple(field.name for field in fields(SQLiteSchemaBootstrapResultV1)) == _BOOTSTRAP_FIELDS
    assert tuple(field.name for field in fields(SQLiteConnectionAuditEvidenceV1)) == _AUDIT_FIELDS
    assert {"connect", "close"}.issubset(dir(SQLiteConnectionFactoryImplementationV1))
    assert {"close", "closed"}.issubset(dir(SQLiteConnectionHandleV1))
    assert not {"connection", "cursor", "execute", "query", "database_location"}.intersection(dir(SQLiteConnectionHandleV1))
    factory, location = _FailIfCalledFactory(), "isolated/bootstrap-v1.sqlite"
    readiness = validate_sqlite_connection_configuration_v1(_configuration(location), factory)
    bootstrap = bootstrap_sqlite_schema_v1(_configuration(location), _manifest(), factory)
    evidence = build_sqlite_connection_audit_evidence_v1(_configuration(location), readiness, bootstrap)
    for value in (_configuration(location), _manifest(), readiness, bootstrap, evidence):
        _frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        _configuration(location).persistence_authorized = True  # type: ignore[misc]
    assert factory.calls == 0
    assert list(inspect.signature(validate_sqlite_connection_configuration_v1).parameters) == ["configuration", "connection_factory"]
    assert list(inspect.signature(bootstrap_sqlite_schema_v1).parameters) == ["configuration", "schema_manifest", "connection_factory"]


def test_invalid_or_unauthorized_bootstrap_fails_before_factory() -> None:
    factory = _FailIfCalledFactory()
    configuration = _configuration(
        "../unsafe", location_classification="CONTROLLED_PRODUCTION", journal_mode="DELETE",
        synchronous_mode="NORMAL", foreign_keys_required=False, create_database_if_missing=True,
        create_directory_if_missing=True,
    )
    readiness = validate_sqlite_connection_configuration_v1(configuration, factory)
    bootstrap = bootstrap_sqlite_schema_v1(configuration, _manifest(), factory)
    assert {
        "DATABASE_LOCATION_TRAVERSAL_DETECTED", "LOCATION_CLASSIFICATION_NOT_ALLOWED",
        "PRODUCTION_PATH_NOT_AUTHORIZED", "JOURNAL_MODE_NOT_ALLOWED", "SYNCHRONOUS_MODE_NOT_ALLOWED",
        "FOREIGN_KEYS_NOT_REQUIRED", "DATABASE_CREATION_NOT_AUTHORIZED",
        "DIRECTORY_CREATION_NOT_AUTHORIZED", "STORAGE_ACCESS_NOT_AUTHORIZED",
        "SCHEMA_BOOTSTRAP_NOT_AUTHORIZED", "SCHEMA_MIGRATION_NOT_AUTHORIZED",
        "REPAIR_NOT_AUTHORIZED", "PERSISTENCE_NOT_AUTHORIZED", "ADAPTER_NOT_READY",
        "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED",
    }.issubset(readiness.failure_codes)
    assert tuple(readiness.failure_codes) == tuple(sorted(readiness.failure_codes))
    assert set(readiness.failure_codes).issubset(_FAILURES)
    assert bootstrap.bootstrap_attempted is bootstrap.connection_attempted is False
    assert factory.calls == 0


def test_manifest_and_readiness_are_fail_closed_without_bootstrap_or_migration() -> None:
    location = "isolated/bootstrap-v1.sqlite"
    manifest = _manifest(schema_id="other-schema-v1", schema_version=2, required_indexes=(),
                         required_unique_constraints=(), required_foreign_keys=(),
                         append_only_enforcement_required=False, revision_monotonicity_required=False,
                         snapshot_event_alignment_required=False, schema_hash_identity="")
    readiness = validate_sqlite_connection_readiness_v1(_configuration(location), manifest, _FailIfCalledFactory())
    assert {
        "SCHEMA_IDENTITY_MISMATCH", "SCHEMA_VERSION_MISMATCH", "SCHEMA_HASH_MISMATCH",
        "REQUIRED_INDEX_MISSING", "REQUIRED_UNIQUE_CONSTRAINT_MISSING",
        "REQUIRED_FOREIGN_KEY_MISSING", "APPEND_ONLY_ENFORCEMENT_MISSING",
        "REVISION_MONOTONICITY_NOT_ENFORCED", "SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED",
        "ADAPTER_NOT_READY",
    }.issubset(readiness.failure_codes)
    assert readiness.connection_attempted is readiness.connection_opened is readiness.adapter_ready is False


def test_future_bootstrap_uses_only_explicit_ephemeral_location_and_closes() -> None:
    with TemporaryDirectory(
        prefix="phase12-bootstrap-v1-",
        dir="/tmp",
    ) as temp_directory:
        location = str(
            Path(temp_directory)
            / "phase12-bootstrap-v1.sqlite"
        )
        configuration = _configuration(
            location,
            create_database_if_missing=True,
            schema_bootstrap_authorized=True,
            storage_access_authorized=True,
        )
        factory = SQLiteConnectionFactoryImplementationV1()
        bootstrap = bootstrap_sqlite_schema_v1(
            configuration,
            _manifest(),
            factory,
        )
        readiness = validate_sqlite_connection_readiness_v1(
            configuration,
            _manifest(),
            factory,
        )
        evidence = build_sqlite_connection_audit_evidence_v1(
            configuration,
            readiness,
            bootstrap,
        )
        assert bootstrap.bootstrap_confirmed is True
        assert bootstrap.connection_closed_cleanly is True
        assert readiness.production_path_authorized is False
        assert readiness.persistence_authorized is False
        assert "phase12-bootstrap-v1.sqlite" not in repr(evidence)
