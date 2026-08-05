"""RED contract for a TEST_EPHEMERAL SQLite reservation-persistence port."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from engine.phase_12_durable_reservation_persistence_contract_v1 import ReservationPersistenceCommandV1
from engine.phase_12_sqlite_connection_factory_schema_bootstrap_v1 import (
    SQLiteConnectionConfigurationV1,
    SQLiteConnectionFactoryImplementationV1,
    SQLiteSchemaBootstrapManifestV1,
    bootstrap_sqlite_schema_v1,
)
from engine.phase_12_sqlite_reservation_persistence_adapter_integration_v1 import (
    SQLitePersistenceAdapterAuditEvidenceV1,
    SQLitePersistenceAdapterReadinessResultV1,
    SQLiteReservationPersistenceAdapterConfigurationV1,
    SQLiteReservationPersistenceFailureV1,
    SQLiteReservationPersistencePortAdapterV1,
    SQLiteStoredPersistenceCommandV1,
    SQLiteStoredReservationEventV1,
    SQLiteStoredReservationSnapshotV1,
    build_sqlite_reservation_persistence_audit_evidence_v1,
    validate_sqlite_reservation_persistence_configuration_v1,
)


_NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
_CONFIG_FIELDS = (
    "adapter_configuration_id", "adapter_id", "database_identity", "location_classification",
    "schema_id", "schema_version", "schema_hash_identity", "connection_configuration_id",
    "persistence_policy_id", "require_bootstrapped_schema", "require_wal",
    "require_full_synchronous", "require_foreign_keys", "require_append_only_enforcement",
    "require_revision_monotonicity", "require_snapshot_event_alignment",
    "require_command_uniqueness", "require_idempotency_uniqueness", "require_event_uniqueness",
    "require_single_transaction", "require_explicit_recovery", "automatic_retry_allowed",
    "automatic_reconnect_allowed", "migration_authorized", "repair_authorized",
    "persistence_authorized", "reservation_creation_authorized", "ledger_mutation_authorized",
    "production_path_authorized", "provider_transmission_authorized", "provider_execution_authorized",
)
_SNAPSHOT_FIELDS = (
    "reservation_id", "reservation_request_id", "request_id", "idempotency_key", "payload_identity",
    "revision", "state", "last_event_id", "event_count", "currency", "reserved_amount",
    "consumed_amount", "released_amount", "created_at", "updated_at", "serialization_identity",
)
_EVENT_FIELDS = (
    "event_id", "reservation_id", "request_id", "revision", "event_sequence", "event_type",
    "prior_state", "next_state", "currency", "amount", "occurred_at", "immutable_event_identity",
    "serialization_identity",
)
_COMMAND_FIELDS = (
    "persistence_command_id", "reservation_id", "request_id", "idempotency_key", "payload_identity",
    "expected_revision", "resulting_revision", "command_identity", "accepted", "recorded_at",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_READINESS_FIELDS = (
    "adapter_configuration_id", "adapter_configuration_valid", "connection_configuration_valid",
    "connection_factory_available", "database_opened", "pragmas_verified", "schema_present",
    "schema_compatible", "schema_hash_aligned", "append_only_enforcement_present",
    "revision_enforcement_present", "snapshot_event_alignment_present", "command_uniqueness_present",
    "idempotency_uniqueness_present", "event_uniqueness_present", "adapter_ready_for_test_persistence",
    "production_persistence_authorized", "failure_codes",
)
_AUDIT_FIELDS = (
    "adapter_configuration_id", "adapter_id", "database_identity", "location_classification", "schema_id",
    "schema_version", "schema_hash_identity", "persistence_command_id", "reservation_id", "request_id",
    "idempotency_key", "payload_identity", "expected_revision", "resulting_revision",
    "expected_last_event_id", "resulting_last_event_id", "append_attempted", "append_confirmed",
    "replay_detected", "conflict_detected", "rollback_confirmed", "recovery_required", "adapter_closed",
    "failure_codes", "adapter_ready_for_test_persistence", "production_path_authorized",
    "provider_transmission_authorized", "provider_execution_authorized",
)
_FAILURES = {
    "ADAPTER_CONFIGURATION_ID_EMPTY", "ADAPTER_ID_EMPTY", "DATABASE_IDENTITY_EMPTY",
    "LOCATION_CLASSIFICATION_NOT_ALLOWED", "SCHEMA_ID_EMPTY", "SCHEMA_VERSION_INVALID",
    "SCHEMA_HASH_IDENTITY_EMPTY", "CONNECTION_CONFIGURATION_ID_EMPTY", "PERSISTENCE_POLICY_ID_EMPTY",
    "CONNECTION_FACTORY_REQUIRED", "TEST_EPHEMERAL_LOCATION_REQUIRED", "PRODUCTION_PATH_NOT_AUTHORIZED",
    "PERSISTENCE_NOT_AUTHORIZED", "RESERVATION_CREATION_NOT_AUTHORIZED", "LEDGER_MUTATION_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED", "ADAPTER_NOT_READY",
    "REQUIRED_PRAGMA_NOT_VERIFIED", "SCHEMA_NOT_BOOTSTRAPPED", "SCHEMA_IDENTITY_MISMATCH",
    "SCHEMA_VERSION_MISMATCH", "SCHEMA_HASH_MISMATCH", "APPEND_ONLY_ENFORCEMENT_MISSING",
    "REVISION_MONOTONICITY_NOT_ENFORCED", "SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED",
    "COMMAND_UNIQUENESS_NOT_ENFORCED", "IDEMPOTENCY_UNIQUENESS_NOT_ENFORCED",
    "EVENT_UNIQUENESS_NOT_ENFORCED", "COMMAND_IDENTITY_CONFLICT", "IDEMPOTENCY_REPLAY",
    "IDEMPOTENCY_CONFLICT", "REQUEST_IDENTITY_CONFLICT", "REVISION_CONFLICT",
    "LAST_EVENT_ID_CONFLICT", "EVENT_ID_DUPLICATE", "EVENT_IDENTITY_CONFLICT", "TRANSITION_INVALID",
    "SNAPSHOT_IDENTITY_MISMATCH", "EVENT_IDENTITY_MISMATCH", "COMMAND_SNAPSHOT_ALIGNMENT_FAILURE",
    "SNAPSHOT_EVENT_ALIGNMENT_FAILURE", "DECIMAL_SERIALIZATION_FAILURE", "UTC_SERIALIZATION_FAILURE",
    "PARTIAL_APPEND_DETECTED", "ATOMICITY_NOT_PROVEN", "SQLITE_BUSY", "SQLITE_LOCKED",
    "TRANSACTION_TIMEOUT", "COMMIT_OUTCOME_UNCERTAIN", "ROLLBACK_FAILURE", "RECOVERY_REQUIRED",
    "RECOVERY_READ_FAILED", "CORRUPTION_DETECTED", "ADAPTER_CLOSED",
    "RAW_DATABASE_PATH_EXPOSURE_DETECTED", "RAW_SQL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
}


def _adapter_configuration(**overrides: object) -> SQLiteReservationPersistenceAdapterConfigurationV1:
    values = {
        "adapter_configuration_id": "sqlite-reservation-adapter-config-v1", "adapter_id": "sqlite-reservation-port-v1",
        "database_identity": "reservation-integration-store-v1", "location_classification": "TEST_EPHEMERAL",
        "schema_id": "sqlite-bootstrap-schema-v1", "schema_version": 1,
        "schema_hash_identity": "bootstrap-schema-hash-v1", "connection_configuration_id": "sqlite-connection-config-v1",
        "persistence_policy_id": "sqlite-persistence-policy-v1", "require_bootstrapped_schema": True,
        "require_wal": True, "require_full_synchronous": True, "require_foreign_keys": True,
        "require_append_only_enforcement": True, "require_revision_monotonicity": True,
        "require_snapshot_event_alignment": True, "require_command_uniqueness": True,
        "require_idempotency_uniqueness": True, "require_event_uniqueness": True,
        "require_single_transaction": True, "require_explicit_recovery": True,
        "automatic_retry_allowed": False, "automatic_reconnect_allowed": False,
        "migration_authorized": False, "repair_authorized": False, "persistence_authorized": False,
        "reservation_creation_authorized": False, "ledger_mutation_authorized": False,
        "production_path_authorized": False, "provider_transmission_authorized": False,
        "provider_execution_authorized": False,
    }
    values.update(overrides)
    return SQLiteReservationPersistenceAdapterConfigurationV1(**values)


def _connection_configuration(database_location: str) -> SQLiteConnectionConfigurationV1:
    return SQLiteConnectionConfigurationV1(
        "sqlite-connection-config-v1", "reservation-integration-store-v1", database_location, "TEST_EPHEMERAL",
        "sqlite-bootstrap-schema-v1", 1, 5, 10, 1000, "WAL", "FULL", True, 1000, False, False,
        True, False, True, False, False, True, False, False,
    )


def _manifest() -> SQLiteSchemaBootstrapManifestV1:
    return SQLiteSchemaBootstrapManifestV1(
        "sqlite-bootstrap-schema-v1", 1, "schema_metadata", "reservation_snapshots", "reservation_events",
        "persistence_commands", "recovery_evidence", ("RESERVATION_REVISION_INDEX",),
        ("PERSISTENCE_COMMAND_ID", "RESERVATION_ID", "IDEMPOTENCY_KEY", "EVENT_ID"),
        ("EVENT_RESERVATION", "EVENT_REQUEST", "RECOVERY_COMMAND"), True, True, True,
        "bootstrap-schema-hash-v1", ("METADATA", "SNAPSHOTS", "EVENTS", "COMMANDS", "RECOVERY", "INDEXES"), False, False,
    )


def _command(**overrides: object) -> ReservationPersistenceCommandV1:
    values = {
        "persistence_command_id": "sqlite-persistence-command-v1", "reservation_id": "sqlite-reservation-v1",
        "reservation_request_id": "sqlite-reservation-request-v1", "request_id": "sqlite-provider-request-v1",
        "idempotency_key": "sqlite-idempotency-v1", "payload_identity": "sqlite-payload-v1",
        "expected_revision": 0, "prior_state": "PROPOSED", "requested_state": "RESERVED",
        "transition_event": (("event_id", "sqlite-event-v1"), ("event_type", "RESERVATION_CREATED")),
        "expected_last_event_id": "event-proposed-v1", "command_created_at": _NOW, "persistence_authorized": True,
    }
    values.update(overrides)
    return ReservationPersistenceCommandV1(**values)


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_narrow_and_redacted() -> None:
    assert tuple(field.name for field in fields(SQLiteReservationPersistenceAdapterConfigurationV1)) == _CONFIG_FIELDS
    assert tuple(field.name for field in fields(SQLiteStoredReservationSnapshotV1)) == _SNAPSHOT_FIELDS
    assert tuple(field.name for field in fields(SQLiteStoredReservationEventV1)) == _EVENT_FIELDS
    assert tuple(field.name for field in fields(SQLiteStoredPersistenceCommandV1)) == _COMMAND_FIELDS
    assert tuple(field.name for field in fields(SQLiteReservationPersistenceFailureV1)) == _FAILURE_FIELDS
    assert tuple(field.name for field in fields(SQLitePersistenceAdapterReadinessResultV1)) == _READINESS_FIELDS
    assert tuple(field.name for field in fields(SQLitePersistenceAdapterAuditEvidenceV1)) == _AUDIT_FIELDS
    assert {"compare_and_append", "read_reservation", "close"}.issubset(dir(SQLiteReservationPersistencePortAdapterV1))
    assert not {"execute", "query", "connection", "cursor", "delete", "truncate", "vacuum"}.intersection(dir(SQLiteReservationPersistencePortAdapterV1))
    result = validate_sqlite_reservation_persistence_configuration_v1(_adapter_configuration())
    evidence = build_sqlite_reservation_persistence_audit_evidence_v1(_adapter_configuration(), _command(), result, None)
    for value in (_adapter_configuration(), result, evidence):
        _frozen_slotted(value)
    with pytest.raises(FrozenInstanceError):
        _adapter_configuration().persistence_authorized = True  # type: ignore[misc]


def test_zero_authority_configuration_fails_closed_without_port_activation() -> None:
    result = validate_sqlite_reservation_persistence_configuration_v1(_adapter_configuration())
    assert {
        "PERSISTENCE_NOT_AUTHORIZED", "RESERVATION_CREATION_NOT_AUTHORIZED", "LEDGER_MUTATION_NOT_AUTHORIZED",
        "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED", "ADAPTER_NOT_READY",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert result.adapter_ready_for_test_persistence is False
    assert result.production_persistence_authorized is False


def test_future_tmp_path_first_append_replay_conflict_and_recovery() -> None:
    with TemporaryDirectory(
        prefix="phase12-reservation-integration-v1-",
        dir="/tmp",
    ) as temp_directory:
        database_location = str(
            Path(temp_directory)
            / "phase12-reservation-integration-v1.sqlite"
        )
        connection_configuration = _connection_configuration(
            database_location
        )
        manifest = _manifest()
        factory = SQLiteConnectionFactoryImplementationV1()
        bootstrap = bootstrap_sqlite_schema_v1(
            connection_configuration,
            manifest,
            factory,
        )
        assert bootstrap.bootstrap_confirmed is True
        configuration = _adapter_configuration(
            persistence_authorized=True,
            reservation_creation_authorized=True,
            ledger_mutation_authorized=True,
        )
        adapter = SQLiteReservationPersistencePortAdapterV1(
            configuration,
            connection_configuration,
            manifest,
            factory,
        )
        first = adapter.compare_and_append(_command())
        replay = adapter.compare_and_append(_command())
        conflict = adapter.compare_and_append(
            _command(
                expected_revision=1,
                payload_identity="other-payload-v1",
            )
        )
        recovered = adapter.read_reservation(
            "sqlite-reservation-v1"
        )
        adapter.close()
        assert first.revision == 1 and first.event_count == 1
        assert first.reserved_amount == Decimal("0") and first.created_at == _NOW
        assert replay == first
        assert conflict is None
        assert recovered is not None and recovered.revision == 1


def test_audit_evidence_is_deterministic_identity_bound_and_provider_free() -> None:
    configuration, command = _adapter_configuration(), _command()
    result = validate_sqlite_reservation_persistence_configuration_v1(configuration)
    evidence = build_sqlite_reservation_persistence_audit_evidence_v1(configuration, command, result, None)
    assert evidence == build_sqlite_reservation_persistence_audit_evidence_v1(configuration, command, result, None)
    assert evidence.production_path_authorized is False
    assert evidence.provider_transmission_authorized is evidence.provider_execution_authorized is False
    with pytest.raises(ValueError):
        build_sqlite_reservation_persistence_audit_evidence_v1(_adapter_configuration(adapter_id="other-adapter-v1"), command, result, None)
