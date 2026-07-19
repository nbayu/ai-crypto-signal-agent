"""Isolated TEST_EPHEMERAL sqlite3 factory and static schema bootstrap boundary."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3


_TABLES = ("schema_metadata", "reservation_snapshots", "reservation_events", "persistence_commands", "recovery_evidence")
_INDEXES = ("RESERVATION_REVISION_INDEX",)
_UNIQUENESS = ("PERSISTENCE_COMMAND_ID", "RESERVATION_ID", "IDEMPOTENCY_KEY", "EVENT_ID")
_FOREIGN_KEYS = ("EVENT_RESERVATION", "EVENT_REQUEST", "RECOVERY_COMMAND")
_DDL_ORDER = ("METADATA", "SNAPSHOTS", "EVENTS", "COMMANDS", "RECOVERY", "INDEXES")
_STATIC_SCHEMA = (
    "CREATE TABLE schema_metadata (schema_id TEXT NOT NULL, schema_version INTEGER NOT NULL, schema_hash TEXT NOT NULL)",
    "CREATE TABLE reservation_snapshots (reservation_id TEXT PRIMARY KEY, revision INTEGER NOT NULL UNIQUE, last_event_id TEXT NOT NULL)",
    "CREATE TABLE reservation_events (event_id TEXT PRIMARY KEY, reservation_id TEXT NOT NULL, request_id TEXT NOT NULL, revision INTEGER NOT NULL, FOREIGN KEY(reservation_id) REFERENCES reservation_snapshots(reservation_id))",
    "CREATE TABLE persistence_commands (command_id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE, reservation_id TEXT NOT NULL, FOREIGN KEY(reservation_id) REFERENCES reservation_snapshots(reservation_id))",
    "CREATE TABLE recovery_evidence (recovery_id TEXT PRIMARY KEY, command_id TEXT NOT NULL, FOREIGN KEY(command_id) REFERENCES persistence_commands(command_id))",
    "CREATE INDEX RESERVATION_REVISION_INDEX ON reservation_events(reservation_id, revision)",
    "CREATE TRIGGER reservation_events_no_update BEFORE UPDATE ON reservation_events BEGIN SELECT RAISE(ABORT, 'append-only'); END",
    "CREATE TRIGGER reservation_events_no_delete BEFORE DELETE ON reservation_events BEGIN SELECT RAISE(ABORT, 'append-only'); END",
)


@dataclass(frozen=True, slots=True)
class SQLiteConnectionConfigurationV1:
    connection_configuration_id: str
    database_identity: str
    database_location: str
    location_classification: str
    expected_schema_id: str
    expected_schema_version: int
    connection_timeout_seconds: int
    transaction_timeout_seconds: int
    busy_timeout_milliseconds: int
    journal_mode: str
    synchronous_mode: str
    foreign_keys_required: bool
    wal_autocheckpoint_pages: int
    query_only: bool
    uri_mode: bool
    create_database_if_missing: bool = False
    create_directory_if_missing: bool = False
    schema_bootstrap_authorized: bool = False
    schema_migration_authorized: bool = False
    repair_authorized: bool = False
    storage_access_authorized: bool = False
    production_path_authorized: bool = False
    persistence_authorized: bool = False

    def __repr__(self) -> str:
        return f"SQLiteConnectionConfigurationV1(connection_configuration_id={self.connection_configuration_id!r}, database_identity={self.database_identity!r}, location_classification={self.location_classification!r})"


@dataclass(frozen=True, slots=True)
class SQLiteSchemaBootstrapManifestV1:
    schema_id: str
    schema_version: int
    schema_metadata_table: str
    snapshot_table: str
    event_table: str
    command_table: str
    recovery_table: str
    required_indexes: tuple[str, ...]
    required_unique_constraints: tuple[str, ...]
    required_foreign_keys: tuple[str, ...]
    append_only_enforcement_required: bool
    revision_monotonicity_required: bool
    snapshot_event_alignment_required: bool
    schema_hash_identity: str
    ddl_order: tuple[str, ...]
    migrations_available: bool
    destructive_migration_available: bool


@dataclass(frozen=True, slots=True)
class SQLiteConnectionFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class SQLiteConnectionReadinessResultV1:
    connection_configuration_id: str
    configuration_valid: bool
    location_authorized: bool
    factory_supplied: bool
    connection_attempted: bool
    connection_opened: bool
    pragmas_verified: bool
    schema_present: bool
    schema_compatible: bool
    bootstrap_required: bool
    migration_required: bool
    corruption_detected: bool
    recovery_required: bool
    connection_closed_cleanly: bool
    adapter_ready: bool
    persistence_authorized: bool
    production_path_authorized: bool
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SQLiteSchemaBootstrapResultV1:
    connection_configuration_id: str
    bootstrap_attempted: bool
    bootstrap_confirmed: bool
    rollback_attempted: bool
    rollback_confirmed: bool
    uncertain_outcome: bool
    connection_attempted: bool
    connection_opened: bool
    pragmas_verified: bool
    schema_compatible: bool
    connection_closed_cleanly: bool
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SQLiteConnectionAuditEvidenceV1:
    connection_configuration_id: str
    database_identity: str
    location_classification: str
    schema_id: str
    schema_version: int
    schema_hash_identity: str
    connection_attempted: bool
    connection_opened: bool
    bootstrap_attempted: bool
    bootstrap_confirmed: bool
    rollback_confirmed: bool
    uncertain_outcome: bool
    pragmas_verified: bool
    schema_compatible: bool
    connection_closed_cleanly: bool
    adapter_ready: bool
    persistence_authorized: bool
    production_path_authorized: bool
    failure_codes: tuple[str, ...]


class SQLiteConnectionHandleV1:
    __slots__ = ("_connection", "_database_identity", "_location_classification", "_closed")

    def __init__(self, connection: sqlite3.Connection, database_identity: str, location_classification: str) -> None:
        self._connection = connection
        self._database_identity = database_identity
        self._location_classification = location_classification
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> bool:
        if self._closed:
            return True
        try:
            self._connection.close()
        except sqlite3.Error:
            return False
        self._closed = True
        return True

    def __repr__(self) -> str:
        return f"SQLiteConnectionHandleV1(database_identity={self._database_identity!r}, location_classification={self._location_classification!r}, closed={self._closed!r})"


def _add(codes: tuple[str, ...], code: str) -> tuple[str, ...]:
    return codes if code in codes else codes + (code,)


def _ordered(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(codes))


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and "*" not in value


def _positive(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _contains(values: object, required: tuple[str, ...]) -> bool:
    return isinstance(values, tuple) and all(isinstance(value, str) for value in values) and set(required).issubset(values)


def _configuration_codes(configuration: SQLiteConnectionConfigurationV1, factory: object) -> tuple[str, ...]:
    codes: tuple[str, ...] = ()
    identities = (
        (configuration.connection_configuration_id, "CONNECTION_CONFIGURATION_ID_EMPTY"),
        (configuration.database_identity, "DATABASE_IDENTITY_EMPTY"),
        (configuration.database_location, "DATABASE_LOCATION_EMPTY"),
        (configuration.location_classification, "LOCATION_CLASSIFICATION_EMPTY"),
        (configuration.expected_schema_id, "EXPECTED_SCHEMA_ID_EMPTY"),
    )
    for value, empty_code in identities:
        if not isinstance(value, str) or not value:
            codes = _add(codes, empty_code)
        elif not _identifier(value):
            codes = _add(codes, "DATABASE_LOCATION_NOT_NORMALIZED" if empty_code == "DATABASE_LOCATION_EMPTY" else "LOCATION_CLASSIFICATION_NOT_ALLOWED")
    location = configuration.database_location
    if isinstance(location, str) and location:
        if ".." in location:
            codes = _add(codes, "DATABASE_LOCATION_TRAVERSAL_DETECTED")
        if location.startswith("~"):
            codes = _add(codes, "HOME_EXPANSION_NOT_ALLOWED")
        if "$" in location or "%" in location:
            codes = _add(codes, "ENVIRONMENT_EXPANSION_NOT_ALLOWED")
        if location == ":memory:" or location.startswith("file::memory:"):
            codes = _add(codes, "IN_MEMORY_DATABASE_NOT_ALLOWED")
        if location in ("", "file:") or location.startswith("temp:"):
            codes = _add(codes, "TEMPORARY_UNNAMED_DATABASE_NOT_ALLOWED")
        if location.endswith("/") or location in (".", "./") or "?" in location or "#" in location:
            codes = _add(codes, "DATABASE_LOCATION_NOT_NORMALIZED")
        if not location.startswith("/tmp/"):
            codes = _add(codes, "REPOSITORY_DATABASE_NOT_ALLOWED")
    if configuration.location_classification != "TEST_EPHEMERAL":
        codes = _add(codes, "LOCATION_CLASSIFICATION_NOT_ALLOWED")
        if configuration.location_classification == "CONTROLLED_PRODUCTION" and configuration.production_path_authorized is not True:
            codes = _add(codes, "PRODUCTION_PATH_NOT_AUTHORIZED")
    if not _positive(configuration.expected_schema_version):
        codes = _add(codes, "EXPECTED_SCHEMA_VERSION_INVALID")
    for value, code in ((configuration.connection_timeout_seconds, "CONNECTION_TIMEOUT_INVALID"), (configuration.transaction_timeout_seconds, "TRANSACTION_TIMEOUT_INVALID"), (configuration.busy_timeout_milliseconds, "BUSY_TIMEOUT_INVALID"), (configuration.wal_autocheckpoint_pages, "WAL_AUTOCHECKPOINT_INVALID")):
        if not _positive(value):
            codes = _add(codes, code)
    if configuration.journal_mode != "WAL":
        codes = _add(codes, "JOURNAL_MODE_NOT_ALLOWED")
    if configuration.synchronous_mode != "FULL":
        codes = _add(codes, "SYNCHRONOUS_MODE_NOT_ALLOWED")
    if configuration.foreign_keys_required is not True:
        codes = _add(codes, "FOREIGN_KEYS_NOT_REQUIRED")
    if configuration.query_only is not False or configuration.uri_mode is not False:
        codes = _add(codes, "DATABASE_LOCATION_NOT_NORMALIZED")
    if factory is None or not callable(getattr(factory, "connect", None)):
        codes = _add(codes, "CONNECTION_FACTORY_REQUIRED")
    codes = _add(codes, "DATABASE_CREATION_NOT_AUTHORIZED")
    if configuration.create_directory_if_missing is not False:
        codes = _add(codes, "DIRECTORY_CREATION_NOT_AUTHORIZED")
    if configuration.schema_bootstrap_authorized is not True:
        codes = _add(codes, "SCHEMA_BOOTSTRAP_NOT_AUTHORIZED")
    if configuration.schema_migration_authorized is not True:
        codes = _add(codes, "SCHEMA_MIGRATION_NOT_AUTHORIZED")
    if configuration.repair_authorized is not True:
        codes = _add(codes, "REPAIR_NOT_AUTHORIZED")
    if configuration.storage_access_authorized is not True:
        codes = _add(codes, "STORAGE_ACCESS_NOT_AUTHORIZED")
    if configuration.persistence_authorized is not True:
        codes = _add(codes, "PERSISTENCE_NOT_AUTHORIZED")
    return _ordered(codes)


def _manifest_codes(configuration: SQLiteConnectionConfigurationV1, manifest: object) -> tuple[str, ...]:
    if not isinstance(manifest, SQLiteSchemaBootstrapManifestV1):
        return ("SCHEMA_MANIFEST_INVALID",)
    codes: tuple[str, ...] = ()
    if manifest.schema_id != configuration.expected_schema_id:
        codes = _add(codes, "SCHEMA_IDENTITY_MISMATCH")
    if manifest.schema_version != configuration.expected_schema_version:
        codes = _add(codes, "SCHEMA_VERSION_MISMATCH")
    if not _identifier(manifest.schema_hash_identity):
        codes = _add(codes, "SCHEMA_HASH_MISMATCH")
    tables = (manifest.schema_metadata_table, manifest.snapshot_table, manifest.event_table, manifest.command_table, manifest.recovery_table)
    if tuple(tables) != _TABLES:
        codes = _add(codes, "REQUIRED_TABLE_MISSING")
    if not _contains(manifest.required_indexes, _INDEXES):
        codes = _add(codes, "REQUIRED_INDEX_MISSING")
    if not _contains(manifest.required_unique_constraints, _UNIQUENESS):
        codes = _add(codes, "REQUIRED_UNIQUE_CONSTRAINT_MISSING")
    if not _contains(manifest.required_foreign_keys, _FOREIGN_KEYS):
        codes = _add(codes, "REQUIRED_FOREIGN_KEY_MISSING")
    if manifest.append_only_enforcement_required is not True:
        codes = _add(codes, "APPEND_ONLY_ENFORCEMENT_MISSING")
    if manifest.revision_monotonicity_required is not True:
        codes = _add(codes, "REVISION_MONOTONICITY_NOT_ENFORCED")
    if manifest.snapshot_event_alignment_required is not True:
        codes = _add(codes, "SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED")
    if manifest.ddl_order != _DDL_ORDER or manifest.migrations_available is not False or manifest.destructive_migration_available is not False:
        codes = _add(codes, "SCHEMA_MANIFEST_INVALID")
    return _ordered(codes)


def _readiness(configuration: SQLiteConnectionConfigurationV1, codes: tuple[str, ...], *, factory_supplied: bool, schema_compatible: bool = False, connection_attempted: bool = False, connection_opened: bool = False, pragmas_verified: bool = False, schema_present: bool = False, closed: bool = False) -> SQLiteConnectionReadinessResultV1:
    return SQLiteConnectionReadinessResultV1(
        configuration.connection_configuration_id, not codes, configuration.location_classification == "TEST_EPHEMERAL",
        factory_supplied, connection_attempted, connection_opened, pragmas_verified, schema_present,
        schema_compatible, not schema_present, False, False, False, closed,
        schema_compatible and pragmas_verified and closed, False, False,
        _ordered(codes + ("ADAPTER_NOT_READY", "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED")),
    )


def validate_sqlite_connection_configuration_v1(
    configuration: SQLiteConnectionConfigurationV1, connection_factory: object,
) -> SQLiteConnectionReadinessResultV1:
    """Purely validate an explicit TEST_EPHEMERAL configuration before connection."""
    if not isinstance(configuration, SQLiteConnectionConfigurationV1):
        return SQLiteConnectionReadinessResultV1("", False, False, connection_factory is not None, False, False, False, False, False, False, False, False, True, False, False, False, False, ("ADAPTER_NOT_READY", "CONNECTION_FACTORY_REQUIRED", "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED"))
    return _readiness(configuration, _configuration_codes(configuration, connection_factory), factory_supplied=connection_factory is not None)


class SQLiteConnectionFactoryImplementationV1:
    """Concrete sqlite3 factory restricted to validated TEST_EPHEMERAL paths."""

    def connect(self, configuration: SQLiteConnectionConfigurationV1) -> SQLiteConnectionHandleV1:
        connection = sqlite3.connect(configuration.database_location, timeout=configuration.connection_timeout_seconds, uri=False)
        return SQLiteConnectionHandleV1(connection, configuration.database_identity, configuration.location_classification)

    def close(self) -> None:
        return None


def _configure(connection: sqlite3.Connection, configuration: SQLiteConnectionConfigurationV1) -> tuple[str, ...]:
    try:
        journal = connection.execute("PRAGMA journal_mode = WAL").fetchone()
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {configuration.busy_timeout_milliseconds}")
        connection.execute(f"PRAGMA wal_autocheckpoint = {configuration.wal_autocheckpoint_pages}")
        synchronous = connection.execute("PRAGMA synchronous").fetchone()
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()
        checkpoint = connection.execute("PRAGMA wal_autocheckpoint").fetchone()
    except sqlite3.Error:
        return ("CONNECTION_FAILURE",)
    codes: tuple[str, ...] = ()
    if not journal or str(journal[0]).upper() != "WAL":
        codes = _add(codes, "PRAGMA_JOURNAL_MODE_MISMATCH")
    if not synchronous or synchronous[0] != 2:
        codes = _add(codes, "PRAGMA_SYNCHRONOUS_MODE_MISMATCH")
    if not foreign_keys or foreign_keys[0] != 1:
        codes = _add(codes, "PRAGMA_FOREIGN_KEYS_DISABLED")
    if not busy_timeout or busy_timeout[0] != configuration.busy_timeout_milliseconds:
        codes = _add(codes, "PRAGMA_BUSY_TIMEOUT_MISMATCH")
    if not checkpoint or checkpoint[0] != configuration.wal_autocheckpoint_pages:
        codes = _add(codes, "PRAGMA_WAL_AUTOCHECKPOINT_MISMATCH")
    return _ordered(codes)


def _bootstrap_blockers(codes: tuple[str, ...]) -> tuple[str, ...]:
    ignored = ("DATABASE_CREATION_NOT_AUTHORIZED", "SCHEMA_MIGRATION_NOT_AUTHORIZED", "REPAIR_NOT_AUTHORIZED", "PERSISTENCE_NOT_AUTHORIZED", "ADAPTER_NOT_READY", "PRODUCTION_PERSISTENCE_NOT_AUTHORIZED")
    return tuple(code for code in codes if code not in ignored)


def bootstrap_sqlite_schema_v1(
    configuration: SQLiteConnectionConfigurationV1, schema_manifest: SQLiteSchemaBootstrapManifestV1,
    connection_factory: object,
) -> SQLiteSchemaBootstrapResultV1:
    """Bootstrap one empty TEST_EPHEMERAL database through a single transaction."""
    if not isinstance(configuration, SQLiteConnectionConfigurationV1):
        return SQLiteSchemaBootstrapResultV1("", False, False, False, False, False, False, False, False, False, False, ("CONNECTION_FACTORY_REQUIRED",))
    codes = _bootstrap_blockers(_configuration_codes(configuration, connection_factory) + _manifest_codes(configuration, schema_manifest))
    if codes:
        return SQLiteSchemaBootstrapResultV1(configuration.connection_configuration_id, False, False, False, False, False, False, False, False, False, False, _ordered(codes))
    try:
        handle = connection_factory.connect(configuration)
    except Exception:
        return SQLiteSchemaBootstrapResultV1(configuration.connection_configuration_id, False, False, False, False, False, True, False, False, False, False, ("CONNECTION_FAILURE",))
    if not isinstance(handle, SQLiteConnectionHandleV1):
        return SQLiteSchemaBootstrapResultV1(configuration.connection_configuration_id, False, False, False, False, False, True, False, False, False, False, ("CONNECTION_FAILURE",))
    connection = handle._connection
    pragma_codes = _configure(connection, configuration)
    if pragma_codes:
        closed = handle.close()
        return SQLiteSchemaBootstrapResultV1(configuration.connection_configuration_id, False, False, False, False, False, True, True, False, False, closed, pragma_codes)
    rollback_attempted = False
    rollback_confirmed = False
    try:
        existing = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        if existing:
            closed = handle.close()
            return SQLiteSchemaBootstrapResultV1(configuration.connection_configuration_id, False, False, False, False, False, True, True, True, False, closed, ("TARGET_DATABASE_ALREADY_EXISTS",))
        connection.execute("BEGIN IMMEDIATE")
        for statement in _STATIC_SCHEMA:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_metadata(schema_id, schema_version, schema_hash) VALUES (?, ?, ?)", (schema_manifest.schema_id, schema_manifest.schema_version, schema_manifest.schema_hash_identity))
        connection.commit()
    except sqlite3.Error:
        rollback_attempted = True
        try:
            connection.rollback()
            rollback_confirmed = True
        except sqlite3.Error:
            closed = handle.close()
            return SQLiteSchemaBootstrapResultV1(configuration.connection_configuration_id, True, False, True, False, False, True, True, True, False, closed, ("ROLLBACK_FAILURE", "SCHEMA_BOOTSTRAP_FAILURE"))
        closed = handle.close()
        return SQLiteSchemaBootstrapResultV1(configuration.connection_configuration_id, True, False, rollback_attempted, rollback_confirmed, False, True, True, True, False, closed, ("SCHEMA_BOOTSTRAP_FAILURE",))
    closed = handle.close()
    return SQLiteSchemaBootstrapResultV1(configuration.connection_configuration_id, True, True, False, False, False, True, True, True, True, closed, ())


def validate_sqlite_connection_readiness_v1(
    configuration: SQLiteConnectionConfigurationV1, schema_manifest: SQLiteSchemaBootstrapManifestV1,
    connection_factory: object,
) -> SQLiteConnectionReadinessResultV1:
    """Open once, verify static safety/schema metadata, then close without mutation."""
    if not isinstance(configuration, SQLiteConnectionConfigurationV1):
        return validate_sqlite_connection_configuration_v1(configuration, connection_factory)
    codes = _bootstrap_blockers(_configuration_codes(configuration, connection_factory) + _manifest_codes(configuration, schema_manifest))
    if codes:
        return _readiness(configuration, _ordered(codes), factory_supplied=connection_factory is not None)
    try:
        handle = connection_factory.connect(configuration)
    except Exception:
        return _readiness(configuration, ("CONNECTION_FAILURE",), factory_supplied=True, connection_attempted=True)
    if not isinstance(handle, SQLiteConnectionHandleV1):
        return _readiness(configuration, ("CONNECTION_FAILURE",), factory_supplied=True, connection_attempted=True)
    pragma_codes = _configure(handle._connection, configuration)
    if pragma_codes:
        closed = handle.close()
        return _readiness(configuration, pragma_codes, factory_supplied=True, connection_attempted=True, connection_opened=True, closed=closed)
    try:
        metadata = handle._connection.execute("SELECT schema_id, schema_version, schema_hash FROM schema_metadata").fetchone()
    except sqlite3.Error:
        closed = handle.close()
        return _readiness(configuration, ("SCHEMA_MANIFEST_INVALID",), factory_supplied=True, connection_attempted=True, connection_opened=True, pragmas_verified=True, closed=closed)
    compatible = metadata == (schema_manifest.schema_id, schema_manifest.schema_version, schema_manifest.schema_hash_identity)
    closed = handle.close()
    codes = () if compatible else ("SCHEMA_HASH_MISMATCH",)
    return _readiness(configuration, codes, factory_supplied=True, schema_compatible=compatible, connection_attempted=True, connection_opened=True, pragmas_verified=True, schema_present=True, closed=closed)


def build_sqlite_connection_audit_evidence_v1(
    configuration: SQLiteConnectionConfigurationV1, readiness: SQLiteConnectionReadinessResultV1,
    bootstrap: SQLiteSchemaBootstrapResultV1,
) -> SQLiteConnectionAuditEvidenceV1:
    """Project redacted evidence only; this function never opens a connection."""
    if not isinstance(configuration, SQLiteConnectionConfigurationV1) or not isinstance(readiness, SQLiteConnectionReadinessResultV1) or not isinstance(bootstrap, SQLiteSchemaBootstrapResultV1):
        raise ValueError("SQLite audit evidence requires contract records")
    if readiness.connection_configuration_id != configuration.connection_configuration_id or bootstrap.connection_configuration_id != configuration.connection_configuration_id:
        raise ValueError("SQLite audit evidence identity mismatch")
    return SQLiteConnectionAuditEvidenceV1(
        configuration.connection_configuration_id, configuration.database_identity, configuration.location_classification,
        configuration.expected_schema_id, configuration.expected_schema_version, "REDACTED_SCHEMA_HASH",
        readiness.connection_attempted or bootstrap.connection_attempted,
        readiness.connection_opened or bootstrap.connection_opened, bootstrap.bootstrap_attempted,
        bootstrap.bootstrap_confirmed, bootstrap.rollback_confirmed, bootstrap.uncertain_outcome,
        readiness.pragmas_verified or bootstrap.pragmas_verified,
        readiness.schema_compatible or bootstrap.schema_compatible,
        readiness.connection_closed_cleanly and bootstrap.connection_closed_cleanly,
        readiness.adapter_ready, False, False, _ordered(readiness.failure_codes + bootstrap.failure_codes),
    )
