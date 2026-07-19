"""Pure fake-factory boundary for a future SQLite durable-storage adapter.

No SQLite driver, storage operation, schema action, or filesystem capability is
implemented here.  The adapter can only coordinate an explicitly supplied
test-local fake connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


_REQUIRED_TABLES = (
    "reservation_snapshots", "reservation_events", "persistence_commands",
    "recovery_evidence", "schema_metadata",
)
_REQUIRED_INDEXES = ("RESERVATION_REVISION_INDEX",)
_REQUIRED_UNIQUENESS = ("PERSISTENCE_COMMAND_ID", "RESERVATION_ID", "IDEMPOTENCY_KEY", "EVENT_ID")
_REQUIRED_FOREIGN_KEYS = ("EVENT_RESERVATION", "EVENT_REQUEST", "RECOVERY_COMMAND")


@dataclass(frozen=True, slots=True)
class SQLiteStorageAdapterConfigurationV1:
    adapter_id: str
    adapter_version: str
    database_identity: str
    storage_location: str
    storage_location_classification: str
    schema_id: str
    expected_schema_version: int
    connection_timeout_seconds: int
    transaction_timeout_seconds: int
    busy_timeout_milliseconds: int
    journal_mode: str
    synchronous_mode: str
    foreign_keys_required: bool
    query_only_on_recovery: bool
    immutable_reads_preferred: bool
    uri_mode: bool
    create_database_if_missing: bool = False
    create_directory_if_missing: bool = False
    migration_authorized: bool = False
    repair_authorized: bool = False
    storage_access_authorized: bool = False
    schema_creation_authorized: bool = False
    persistence_authorized: bool = False
    reservation_creation_authorized: bool = False
    ledger_mutation_authorized: bool = False
    provider_transmission_authorized: bool = False
    provider_execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class SQLiteSchemaManifestV1:
    schema_id: str
    schema_version: int
    minimum_supported_version: int
    maximum_supported_version: int
    snapshot_table: str
    event_table: str
    command_table: str
    recovery_table: str
    metadata_table: str
    required_indexes: tuple[str, ...]
    required_unique_constraints: tuple[str, ...]
    required_foreign_keys: tuple[str, ...]
    append_only_triggers_required: bool
    event_update_forbidden: bool
    event_delete_forbidden: bool
    revision_monotonicity_required: bool
    snapshot_event_alignment_required: bool
    schema_hash_identity: str
    migrations_available: bool
    destructive_migration_available: bool


@dataclass(frozen=True, slots=True)
class SQLiteAdapterFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class SQLiteAdapterReadinessResultV1:
    adapter_id: str
    configuration_valid: bool
    factory_supplied: bool
    factory_invoked: bool
    connection_opened: bool
    schema_readable: bool
    schema_compatible: bool
    migration_required: bool
    corruption_detected: bool
    recovery_required: bool
    adapter_ready: bool
    production_persistence_authorized: bool
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SQLiteCompareAndAppendResultV1:
    adapter_id: str
    accepted: bool
    failure_codes: tuple[str, ...]
    factory_invoked: bool
    connection_opened: bool
    append_attempted: bool
    append_confirmed: bool
    rollback_attempted: bool
    rollback_confirmed: bool
    recovery_required: bool
    snapshot: object | None


@dataclass(frozen=True, slots=True)
class SQLiteRecoveryReadResultV1:
    adapter_id: str
    reservation_id: str
    request_id: str
    recovered: bool
    found: bool
    revision_current: bool
    identity_aligned: bool
    failure_codes: tuple[str, ...]
    factory_invoked: bool
    connection_opened: bool
    read_attempted: bool
    recovery_required: bool
    snapshot: object | None
    provider_contacted: bool
    transmitted: bool
    provider_execution_authorized: bool


@dataclass(frozen=True, slots=True)
class SQLiteAdapterAuditEvidenceV1:
    adapter_id: str
    database_identity: str
    schema_id: str
    expected_schema_version: int
    journal_mode: str
    synchronous_mode: str
    connection_timeout_seconds: int
    transaction_timeout_seconds: int
    busy_timeout_milliseconds: int
    configuration_valid: bool
    schema_compatible: bool
    factory_invoked: bool
    connection_opened: bool
    append_attempted: bool
    append_confirmed: bool
    rollback_confirmed: bool
    recovery_required: bool
    failure_codes: tuple[str, ...]
    storage_access_authorized: bool
    schema_creation_authorized: bool
    migration_authorized: bool
    persistence_authorized: bool
    reservation_creation_authorized: bool
    ledger_mutation_authorized: bool
    provider_transmission_authorized: bool
    provider_execution_authorized: bool


class SQLiteConnectionFactoryV1(Protocol):
    def connect(self, configuration: SQLiteStorageAdapterConfigurationV1) -> object:
        """Return a caller-owned fake connection for this explicit configuration."""


def _add(codes: tuple[str, ...], code: str) -> tuple[str, ...]:
    return codes if code in codes else codes + (code,)


def _ordered(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(codes))


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and "*" not in value


def _positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _contains(values: object, required: tuple[str, ...]) -> bool:
    return isinstance(values, tuple) and all(isinstance(value, str) for value in values) and set(required).issubset(values)


def _readiness(
    configuration: SQLiteStorageAdapterConfigurationV1, codes: tuple[str, ...], *, schema_compatible: bool = False,
    migration_required: bool = False, corruption_detected: bool = False, factory_supplied: bool = False,
) -> SQLiteAdapterReadinessResultV1:
    ordered_codes = _ordered(codes + ("ADAPTER_NOT_READY",))
    return SQLiteAdapterReadinessResultV1(
        configuration.adapter_id, not codes or all(code in _authority_codes(configuration) for code in codes),
        factory_supplied, False, False, False, schema_compatible, migration_required,
        corruption_detected, migration_required or corruption_detected, False, False, ordered_codes,
    )


def _authority_codes(configuration: SQLiteStorageAdapterConfigurationV1) -> tuple[str, ...]:
    codes: tuple[str, ...] = ()
    if configuration.create_database_if_missing is not False:
        codes = _add(codes, "DATABASE_CREATION_NOT_AUTHORIZED")
    if configuration.create_directory_if_missing is not False:
        codes = _add(codes, "DIRECTORY_CREATION_NOT_AUTHORIZED")
    if configuration.storage_access_authorized is not True:
        codes = _add(codes, "STORAGE_ACCESS_NOT_AUTHORIZED")
    if configuration.schema_creation_authorized is not True:
        codes = _add(codes, "SCHEMA_CREATION_NOT_AUTHORIZED")
    if configuration.migration_authorized is not True:
        codes = _add(codes, "MIGRATION_NOT_AUTHORIZED")
    if configuration.repair_authorized is not True:
        codes = _add(codes, "REPAIR_NOT_AUTHORIZED")
    if configuration.persistence_authorized is not True:
        codes = _add(codes, "PERSISTENCE_NOT_AUTHORIZED")
    if configuration.reservation_creation_authorized is not True:
        codes = _add(codes, "RESERVATION_CREATION_NOT_AUTHORIZED")
    if configuration.ledger_mutation_authorized is not True:
        codes = _add(codes, "LEDGER_MUTATION_NOT_AUTHORIZED")
    if configuration.provider_transmission_authorized is not True:
        codes = _add(codes, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED")
    if configuration.provider_execution_authorized is not True:
        codes = _add(codes, "PROVIDER_EXECUTION_NOT_AUTHORIZED")
    return codes


def validate_sqlite_storage_configuration_v1(
    configuration: SQLiteStorageAdapterConfigurationV1, connection_factory: SQLiteConnectionFactoryV1 | None,
) -> SQLiteAdapterReadinessResultV1:
    """Validate metadata before any possible fake-factory invocation."""
    if not isinstance(configuration, SQLiteStorageAdapterConfigurationV1):
        return SQLiteAdapterReadinessResultV1("", False, connection_factory is not None, False, False, False, False, False, False, True, False, False, ("ADAPTER_NOT_READY", "CONNECTION_FACTORY_REQUIRED"))
    codes: tuple[str, ...] = ()
    identities = (
        (configuration.adapter_id, "ADAPTER_ID_EMPTY"), (configuration.adapter_version, "ADAPTER_VERSION_EMPTY"),
        (configuration.database_identity, "DATABASE_IDENTITY_EMPTY"), (configuration.storage_location, "STORAGE_LOCATION_EMPTY"),
        (configuration.schema_id, "SCHEMA_ID_EMPTY"),
    )
    for value, empty_code in identities:
        if not isinstance(value, str) or not value:
            codes = _add(codes, empty_code)
        elif not _identifier(value):
            codes = _add(codes, "STORAGE_LOCATION_NOT_NORMALIZED" if empty_code == "STORAGE_LOCATION_EMPTY" else "STORAGE_LOCATION_NOT_ALLOWED")
    location = configuration.storage_location
    if isinstance(location, str) and location:
        if location in (".", "./") or location.endswith("/"):
            codes = _add(codes, "STORAGE_LOCATION_NOT_ALLOWED")
        if ".." in location:
            codes = _add(codes, "STORAGE_LOCATION_TRAVERSAL_DETECTED")
        if "*" in location or "?" in location or location.startswith("~") or "$" in location or "\\" in location:
            codes = _add(codes, "STORAGE_LOCATION_NOT_ALLOWED")
        if location == ":memory:" or location.startswith("file::memory:"):
            codes = _add(codes, "IN_MEMORY_DATABASE_NOT_ALLOWED")
        if location in ("", "file:") or location.startswith("temp:"):
            codes = _add(codes, "TEMPORARY_DATABASE_NOT_ALLOWED")
        if location.startswith("file:") and ("?" in location or "#" in location):
            codes = _add(codes, "STORAGE_LOCATION_NOT_ALLOWED")
    if not _positive_integer(configuration.expected_schema_version):
        codes = _add(codes, "EXPECTED_SCHEMA_VERSION_INVALID")
    if not _positive_integer(configuration.connection_timeout_seconds):
        codes = _add(codes, "CONNECTION_TIMEOUT_INVALID")
    if not _positive_integer(configuration.transaction_timeout_seconds):
        codes = _add(codes, "TRANSACTION_TIMEOUT_INVALID")
    if not _positive_integer(configuration.busy_timeout_milliseconds):
        codes = _add(codes, "BUSY_TIMEOUT_INVALID")
    if configuration.journal_mode != "WAL":
        codes = _add(codes, "JOURNAL_MODE_NOT_ALLOWED")
    if configuration.synchronous_mode != "FULL":
        codes = _add(codes, "SYNCHRONOUS_MODE_NOT_ALLOWED")
    if configuration.foreign_keys_required is not True:
        codes = _add(codes, "FOREIGN_KEYS_NOT_REQUIRED")
    if configuration.query_only_on_recovery is not True:
        codes = _add(codes, "QUERY_ONLY_RECOVERY_NOT_REQUIRED")
    if configuration.immutable_reads_preferred is not True:
        codes = _add(codes, "STORAGE_LOCATION_NOT_ALLOWED")
    if connection_factory is None or not callable(getattr(connection_factory, "connect", None)):
        codes = _add(codes, "CONNECTION_FACTORY_REQUIRED")
    codes = codes + _authority_codes(configuration)
    return _readiness(configuration, codes, factory_supplied=connection_factory is not None)


def validate_sqlite_schema_manifest_v1(
    configuration: SQLiteStorageAdapterConfigurationV1, schema_manifest: SQLiteSchemaManifestV1,
) -> SQLiteAdapterReadinessResultV1:
    """Validate logical schema metadata without reading, creating, or migrating storage."""
    if not isinstance(configuration, SQLiteStorageAdapterConfigurationV1) or not isinstance(schema_manifest, SQLiteSchemaManifestV1):
        return SQLiteAdapterReadinessResultV1("", False, False, False, False, False, False, False, True, True, False, False, ("ADAPTER_NOT_READY", "SCHEMA_IDENTITY_MISMATCH"))
    codes: tuple[str, ...] = ()
    if schema_manifest.schema_id != configuration.schema_id:
        codes = _add(codes, "SCHEMA_IDENTITY_MISMATCH")
    versions_valid = all(_positive_integer(value) for value in (
        schema_manifest.schema_version, schema_manifest.minimum_supported_version, schema_manifest.maximum_supported_version,
    ))
    if not versions_valid or schema_manifest.minimum_supported_version > schema_manifest.maximum_supported_version:
        codes = _add(codes, "SCHEMA_VERSION_UNSUPPORTED")
    migration_required = schema_manifest.schema_version != configuration.expected_schema_version
    if migration_required:
        codes = _add(codes, "SCHEMA_MIGRATION_REQUIRED")
    if schema_manifest.schema_version > schema_manifest.maximum_supported_version:
        codes = _add(codes, "SCHEMA_VERSION_UNSUPPORTED")
    if not _identifier(schema_manifest.schema_hash_identity):
        codes = _add(codes, "SCHEMA_HASH_MISMATCH")
    tables = (schema_manifest.snapshot_table, schema_manifest.event_table, schema_manifest.command_table, schema_manifest.recovery_table, schema_manifest.metadata_table)
    if tuple(tables) != _REQUIRED_TABLES or not all(_identifier(value) for value in tables):
        codes = _add(codes, "REQUIRED_TABLE_MISSING")
    if not _contains(schema_manifest.required_indexes, _REQUIRED_INDEXES):
        codes = _add(codes, "REQUIRED_INDEX_MISSING")
    if not _contains(schema_manifest.required_unique_constraints, _REQUIRED_UNIQUENESS):
        codes = _add(codes, "REQUIRED_UNIQUE_CONSTRAINT_MISSING")
    if not _contains(schema_manifest.required_foreign_keys, _REQUIRED_FOREIGN_KEYS):
        codes = _add(codes, "REQUIRED_FOREIGN_KEY_MISSING")
    if schema_manifest.append_only_triggers_required is not True:
        codes = _add(codes, "APPEND_ONLY_ENFORCEMENT_MISSING")
    if schema_manifest.event_update_forbidden is not True:
        codes = _add(codes, "EVENT_UPDATE_NOT_FORBIDDEN")
    if schema_manifest.event_delete_forbidden is not True:
        codes = _add(codes, "EVENT_DELETE_NOT_FORBIDDEN")
    if schema_manifest.revision_monotonicity_required is not True:
        codes = _add(codes, "REVISION_MONOTONICITY_NOT_ENFORCED")
    if schema_manifest.snapshot_event_alignment_required is not True:
        codes = _add(codes, "SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED")
    if schema_manifest.destructive_migration_available is not False:
        codes = _add(codes, "CORRUPTION_DETECTED")
    compatible = not codes
    return SQLiteAdapterReadinessResultV1(
        configuration.adapter_id, compatible, False, False, False, False, compatible,
        migration_required, "CORRUPTION_DETECTED" in codes, migration_required or "CORRUPTION_DETECTED" in codes,
        False, False, _ordered(codes + ("ADAPTER_NOT_READY",)),
    )


def build_sqlite_adapter_audit_evidence_v1(
    configuration: SQLiteStorageAdapterConfigurationV1, readiness: SQLiteAdapterReadinessResultV1,
    manifest_result: SQLiteAdapterReadinessResultV1, append_result: SQLiteCompareAndAppendResultV1 | None,
    recovery_result: SQLiteRecoveryReadResultV1 | None,
) -> SQLiteAdapterAuditEvidenceV1:
    """Build redacted immutable evidence only; no fake connection is touched."""
    if not isinstance(configuration, SQLiteStorageAdapterConfigurationV1) or not isinstance(readiness, SQLiteAdapterReadinessResultV1) or not isinstance(manifest_result, SQLiteAdapterReadinessResultV1):
        raise ValueError("SQLite audit evidence requires contract records")
    if readiness.adapter_id != configuration.adapter_id or manifest_result.adapter_id != configuration.adapter_id:
        raise ValueError("SQLite audit evidence identity mismatch")
    if append_result is not None and (not isinstance(append_result, SQLiteCompareAndAppendResultV1) or append_result.adapter_id != configuration.adapter_id):
        raise ValueError("SQLite audit evidence append mismatch")
    if recovery_result is not None and (not isinstance(recovery_result, SQLiteRecoveryReadResultV1) or recovery_result.adapter_id != configuration.adapter_id):
        raise ValueError("SQLite audit evidence recovery mismatch")
    append_attempted = append_result.append_attempted if append_result is not None else False
    append_confirmed = append_result.append_confirmed if append_result is not None else False
    rollback_confirmed = append_result.rollback_confirmed if append_result is not None else False
    recovery_required = readiness.recovery_required or manifest_result.recovery_required or (recovery_result.recovery_required if recovery_result is not None else False)
    codes = readiness.failure_codes + manifest_result.failure_codes
    if append_result is not None:
        codes += append_result.failure_codes
    if recovery_result is not None:
        codes += recovery_result.failure_codes
    return SQLiteAdapterAuditEvidenceV1(
        configuration.adapter_id, configuration.database_identity, configuration.schema_id,
        configuration.expected_schema_version, configuration.journal_mode, configuration.synchronous_mode,
        configuration.connection_timeout_seconds, configuration.transaction_timeout_seconds,
        configuration.busy_timeout_milliseconds, readiness.configuration_valid, manifest_result.schema_compatible,
        readiness.factory_invoked or (append_result.factory_invoked if append_result is not None else False),
        readiness.connection_opened or (append_result.connection_opened if append_result is not None else False),
        append_attempted, append_confirmed, rollback_confirmed, recovery_required, _ordered(codes),
        configuration.storage_access_authorized, configuration.schema_creation_authorized,
        configuration.migration_authorized, configuration.persistence_authorized,
        configuration.reservation_creation_authorized, configuration.ledger_mutation_authorized,
        configuration.provider_transmission_authorized, configuration.provider_execution_authorized,
    )


class SQLiteReservationPersistenceAdapterV1:
    """Narrow fake-only adapter with explicit lifecycle and no reconnect path."""

    def __init__(
        self, configuration: SQLiteStorageAdapterConfigurationV1, schema_manifest: SQLiteSchemaManifestV1,
        connection_factory: SQLiteConnectionFactoryV1,
    ) -> None:
        self._configuration = configuration
        self._schema_manifest = schema_manifest
        self._connection_factory = connection_factory
        self._connection: object | None = None
        self._closed = False

    def validate_readiness(self) -> SQLiteAdapterReadinessResultV1:
        if self._closed:
            return SQLiteAdapterReadinessResultV1(self._configuration.adapter_id, False, True, False, False, False, False, False, False, False, False, False, ("ADAPTER_CLOSED", "ADAPTER_NOT_READY"))
        configuration_result = validate_sqlite_storage_configuration_v1(self._configuration, self._connection_factory)
        manifest_result = validate_sqlite_schema_manifest_v1(self._configuration, self._schema_manifest)
        codes = _ordered(configuration_result.failure_codes + manifest_result.failure_codes)
        return SQLiteAdapterReadinessResultV1(
            self._configuration.adapter_id, configuration_result.configuration_valid, True, False, False,
            False, manifest_result.schema_compatible, manifest_result.migration_required,
            manifest_result.corruption_detected, manifest_result.recovery_required, False, False, codes,
        )

    def _precondition_codes(self) -> tuple[str, ...]:
        configuration_result = validate_sqlite_storage_configuration_v1(self._configuration, self._connection_factory)
        manifest_result = validate_sqlite_schema_manifest_v1(self._configuration, self._schema_manifest)
        return _ordered(tuple(
            code for code in configuration_result.failure_codes + manifest_result.failure_codes
            if code != "ADAPTER_NOT_READY"
        ))

    def _open_fake_once(self) -> tuple[object | None, bool, tuple[str, ...]]:
        if self._connection is not None:
            return self._connection, False, ()
        try:
            connection = self._connection_factory.connect(self._configuration)
        except Exception:
            return None, True, ("CONNECTION_FAILURE",)
        if connection is None:
            return None, True, ("CONNECTION_FAILURE",)
        self._connection = connection
        return connection, True, ()

    def compare_and_append(self, command: object) -> SQLiteCompareAndAppendResultV1:
        if self._closed:
            return SQLiteCompareAndAppendResultV1(self._configuration.adapter_id, False, ("ADAPTER_CLOSED",), False, False, False, False, False, False, False, None)
        failures = self._precondition_codes()
        if failures:
            return SQLiteCompareAndAppendResultV1(self._configuration.adapter_id, False, failures, False, False, False, False, False, False, "RECOVERY_REQUIRED" in failures, None)
        connection, factory_invoked, open_failures = self._open_fake_once()
        if open_failures:
            return SQLiteCompareAndAppendResultV1(self._configuration.adapter_id, False, open_failures, factory_invoked, False, False, False, False, False, False, None)
        operation = getattr(connection, "compare_and_append", None)
        if not callable(operation):
            return SQLiteCompareAndAppendResultV1(self._configuration.adapter_id, False, ("CONNECTION_FAILURE",), factory_invoked, True, False, False, False, False, False, None)
        try:
            snapshot = operation(command)
        except Exception:
            return SQLiteCompareAndAppendResultV1(self._configuration.adapter_id, False, ("COMMIT_OUTCOME_UNCERTAIN", "RECOVERY_REQUIRED"), factory_invoked, True, True, False, False, False, True, None)
        if snapshot is None:
            return SQLiteCompareAndAppendResultV1(self._configuration.adapter_id, False, ("PARTIAL_APPEND_DETECTED",), factory_invoked, True, True, False, True, True, False, None)
        return SQLiteCompareAndAppendResultV1(self._configuration.adapter_id, True, (), factory_invoked, True, True, True, False, False, False, snapshot)

    def read_reservation(
        self, reservation_id: str, request_id: str = "", expected_revision: int = 0,
        recovery_authorized: bool = False,
    ) -> SQLiteRecoveryReadResultV1:
        if self._closed:
            return SQLiteRecoveryReadResultV1(self._configuration.adapter_id, reservation_id, request_id, False, False, False, False, ("ADAPTER_CLOSED",), False, False, False, False, None, False, False, False)
        if recovery_authorized is not True or self._configuration.query_only_on_recovery is not True:
            return SQLiteRecoveryReadResultV1(self._configuration.adapter_id, reservation_id, request_id, False, False, False, False, ("RECOVERY_REQUIRED",), False, False, False, True, None, False, False, False)
        failures = self._precondition_codes()
        if failures:
            return SQLiteRecoveryReadResultV1(self._configuration.adapter_id, reservation_id, request_id, False, False, False, False, failures, False, False, False, True, None, False, False, False)
        connection, factory_invoked, open_failures = self._open_fake_once()
        if open_failures:
            return SQLiteRecoveryReadResultV1(self._configuration.adapter_id, reservation_id, request_id, False, False, False, False, open_failures, factory_invoked, False, False, True, None, False, False, False)
        operation = getattr(connection, "read_reservation", None)
        if not callable(operation):
            return SQLiteRecoveryReadResultV1(self._configuration.adapter_id, reservation_id, request_id, False, False, False, False, ("RECOVERY_READ_FAILED",), factory_invoked, True, False, True, None, False, False, False)
        try:
            snapshot = operation(reservation_id)
        except Exception:
            return SQLiteRecoveryReadResultV1(self._configuration.adapter_id, reservation_id, request_id, False, False, False, False, ("RECOVERY_READ_FAILED", "RECOVERY_REQUIRED"), factory_invoked, True, True, True, None, False, False, False)
        if snapshot is None:
            return SQLiteRecoveryReadResultV1(self._configuration.adapter_id, reservation_id, request_id, False, False, True, True, (), factory_invoked, True, True, False, None, False, False, False)
        return SQLiteRecoveryReadResultV1(self._configuration.adapter_id, reservation_id, request_id, True, True, True, True, (), factory_invoked, True, True, False, snapshot, False, False, False)

    def close(self) -> None:
        if self._closed:
            return
        closer = getattr(self._connection, "close", None)
        if callable(closer):
            try:
                closer()
            except Exception:
                pass
        self._closed = True
