"""TEST_EPHEMERAL SQLite implementation of the narrow reservation port.

This boundary owns no production configuration.  It accepts only the committed
test-local connection/bootstrap records and returns immutable, redacted domain
evidence.  All SQL is static and is used solely against a caller-supplied
``TEST_EPHEMERAL`` database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import sqlite3

from engine.phase_12_durable_reservation_persistence_contract_v1 import ReservationPersistenceCommandV1
from engine.phase_12_sqlite_connection_factory_schema_bootstrap_v1 import (
    SQLiteConnectionConfigurationV1,
    SQLiteConnectionFactoryImplementationV1,
    SQLiteConnectionHandleV1,
    SQLiteSchemaBootstrapManifestV1,
)


_FAILURES = frozenset((
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
))

_ALLOWED_TRANSITIONS = frozenset((
    ("PROPOSED", "RESERVED"), ("RESERVED", "TRANSMISSION_PENDING"),
    ("RESERVED", "RELEASED"), ("RESERVED", "EXPIRED"),
    ("TRANSMISSION_PENDING", "CONSUMED"), ("TRANSMISSION_PENDING", "UNCERTAIN"),
    ("UNCERTAIN", "RECONCILED"),
))


class _BoundAdapterConfigurationIdentifier(str):
    """A string identifier carrying immutable, local validation lineage."""

    def __new__(cls, value: str, adapter_id: str, database_identity: str, schema_id: str, schema_version: int, schema_hash_identity: str) -> _BoundAdapterConfigurationIdentifier:
        instance = str.__new__(cls, value)
        object.__setattr__(instance, "_lineage", (adapter_id, database_identity, schema_id, schema_version, schema_hash_identity))
        return instance

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("immutable adapter configuration identifier")


@dataclass(frozen=True, slots=True)
class SQLiteReservationPersistenceAdapterConfigurationV1:
    adapter_configuration_id: str
    adapter_id: str
    database_identity: str
    location_classification: str
    schema_id: str
    schema_version: int
    schema_hash_identity: str
    connection_configuration_id: str
    persistence_policy_id: str
    require_bootstrapped_schema: bool = True
    require_wal: bool = True
    require_full_synchronous: bool = True
    require_foreign_keys: bool = True
    require_append_only_enforcement: bool = True
    require_revision_monotonicity: bool = True
    require_snapshot_event_alignment: bool = True
    require_command_uniqueness: bool = True
    require_idempotency_uniqueness: bool = True
    require_event_uniqueness: bool = True
    require_single_transaction: bool = True
    require_explicit_recovery: bool = True
    automatic_retry_allowed: bool = False
    automatic_reconnect_allowed: bool = False
    migration_authorized: bool = False
    repair_authorized: bool = False
    persistence_authorized: bool = False
    reservation_creation_authorized: bool = False
    ledger_mutation_authorized: bool = False
    production_path_authorized: bool = False
    provider_transmission_authorized: bool = False
    provider_execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class SQLiteReservationPersistenceFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class SQLiteStoredReservationSnapshotV1:
    reservation_id: str
    reservation_request_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    revision: int
    state: str
    last_event_id: str
    event_count: int
    currency: str
    reserved_amount: Decimal
    consumed_amount: Decimal
    released_amount: Decimal
    created_at: datetime
    updated_at: datetime
    serialization_identity: str


@dataclass(frozen=True, slots=True)
class SQLiteStoredReservationEventV1:
    event_id: str
    reservation_id: str
    request_id: str
    revision: int
    event_sequence: int
    event_type: str
    prior_state: str
    next_state: str
    currency: str
    amount: Decimal
    occurred_at: datetime
    immutable_event_identity: str
    serialization_identity: str


@dataclass(frozen=True, slots=True)
class SQLiteStoredPersistenceCommandV1:
    persistence_command_id: str
    reservation_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    expected_revision: int
    resulting_revision: int
    command_identity: str
    accepted: bool
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class SQLitePersistenceAdapterReadinessResultV1:
    adapter_configuration_id: str
    adapter_configuration_valid: bool
    connection_configuration_valid: bool
    connection_factory_available: bool
    database_opened: bool
    pragmas_verified: bool
    schema_present: bool
    schema_compatible: bool
    schema_hash_aligned: bool
    append_only_enforcement_present: bool
    revision_enforcement_present: bool
    snapshot_event_alignment_present: bool
    command_uniqueness_present: bool
    idempotency_uniqueness_present: bool
    event_uniqueness_present: bool
    adapter_ready_for_test_persistence: bool
    production_persistence_authorized: bool
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SQLitePersistenceAdapterAuditEvidenceV1:
    adapter_configuration_id: str
    adapter_id: str
    database_identity: str
    location_classification: str
    schema_id: str
    schema_version: int
    schema_hash_identity: str
    persistence_command_id: str
    reservation_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    expected_revision: int
    resulting_revision: int
    expected_last_event_id: str
    resulting_last_event_id: str
    append_attempted: bool
    append_confirmed: bool
    replay_detected: bool
    conflict_detected: bool
    rollback_confirmed: bool
    recovery_required: bool
    adapter_closed: bool
    failure_codes: tuple[str, ...]
    adapter_ready_for_test_persistence: bool
    production_path_authorized: bool
    provider_transmission_authorized: bool
    provider_execution_authorized: bool


def _ordered(codes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(codes)))


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and "*" not in value


def _positive(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _utc(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo == UTC


def _event(command: ReservationPersistenceCommandV1) -> tuple[str, str] | None:
    values: dict[str, str] = {}
    if not isinstance(command.transition_event, tuple) or not command.transition_event:
        return None
    for pair in command.transition_event:
        if not isinstance(pair, tuple) or len(pair) != 2:
            return None
        key, value = pair
        if not isinstance(key, str) or not isinstance(value, str) or key in values:
            return None
        values[key] = value
    event_id, event_type = values.get("event_id"), values.get("event_type")
    return (event_id, event_type) if _identifier(event_id) and _identifier(event_type) else None


def _command_codes(command: object) -> tuple[str, ...]:
    if not isinstance(command, ReservationPersistenceCommandV1):
        return ("CORRUPTION_DETECTED",)
    codes: list[str] = []
    for value in (
        command.persistence_command_id, command.reservation_id, command.reservation_request_id,
        command.request_id, command.idempotency_key, command.payload_identity,
        command.prior_state, command.requested_state, command.expected_last_event_id,
    ):
        if not _identifier(value):
            codes.append("TRANSITION_INVALID")
    if not isinstance(command.expected_revision, int) or isinstance(command.expected_revision, bool) or command.expected_revision < 0:
        codes.append("REVISION_CONFLICT")
    if not _utc(command.command_created_at):
        codes.append("UTC_SERIALIZATION_FAILURE")
    if command.persistence_authorized is not True or _event(command) is None:
        codes.append("TRANSITION_INVALID")
    if (command.prior_state, command.requested_state) not in _ALLOWED_TRANSITIONS:
        codes.append("TRANSITION_INVALID")
    return _ordered(codes)


def _configuration_codes(configuration: object) -> tuple[str, ...]:
    if not isinstance(configuration, SQLiteReservationPersistenceAdapterConfigurationV1):
        return ("ADAPTER_NOT_READY",)
    codes: list[str] = []
    required = (
        (configuration.adapter_configuration_id, "ADAPTER_CONFIGURATION_ID_EMPTY"),
        (configuration.adapter_id, "ADAPTER_ID_EMPTY"),
        (configuration.database_identity, "DATABASE_IDENTITY_EMPTY"),
        (configuration.schema_id, "SCHEMA_ID_EMPTY"),
        (configuration.schema_hash_identity, "SCHEMA_HASH_IDENTITY_EMPTY"),
        (configuration.connection_configuration_id, "CONNECTION_CONFIGURATION_ID_EMPTY"),
        (configuration.persistence_policy_id, "PERSISTENCE_POLICY_ID_EMPTY"),
    )
    for value, code in required:
        if not _identifier(value):
            codes.append(code)
    if not _positive(configuration.schema_version):
        codes.append("SCHEMA_VERSION_INVALID")
    if configuration.location_classification != "TEST_EPHEMERAL":
        codes.extend(("LOCATION_CLASSIFICATION_NOT_ALLOWED", "TEST_EPHEMERAL_LOCATION_REQUIRED"))
        if configuration.location_classification == "CONTROLLED_PRODUCTION" and configuration.production_path_authorized is not True:
            codes.append("PRODUCTION_PATH_NOT_AUTHORIZED")
    requirements = (
        (configuration.require_bootstrapped_schema, "SCHEMA_NOT_BOOTSTRAPPED"),
        (configuration.require_wal, "REQUIRED_PRAGMA_NOT_VERIFIED"),
        (configuration.require_full_synchronous, "REQUIRED_PRAGMA_NOT_VERIFIED"),
        (configuration.require_foreign_keys, "REQUIRED_PRAGMA_NOT_VERIFIED"),
        (configuration.require_append_only_enforcement, "APPEND_ONLY_ENFORCEMENT_MISSING"),
        (configuration.require_revision_monotonicity, "REVISION_MONOTONICITY_NOT_ENFORCED"),
        (configuration.require_snapshot_event_alignment, "SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED"),
        (configuration.require_command_uniqueness, "COMMAND_UNIQUENESS_NOT_ENFORCED"),
        (configuration.require_idempotency_uniqueness, "IDEMPOTENCY_UNIQUENESS_NOT_ENFORCED"),
        (configuration.require_event_uniqueness, "EVENT_UNIQUENESS_NOT_ENFORCED"),
        (configuration.require_single_transaction, "ATOMICITY_NOT_PROVEN"),
        (configuration.require_explicit_recovery, "RECOVERY_REQUIRED"),
    )
    for valid, code in requirements:
        if valid is not True:
            codes.append(code)
    if configuration.automatic_retry_allowed is not False or configuration.automatic_reconnect_allowed is not False:
        codes.append("ATOMICITY_NOT_PROVEN")
    if configuration.migration_authorized is not False or configuration.repair_authorized is not False:
        codes.append("CORRUPTION_DETECTED")
    if configuration.persistence_authorized is not True:
        codes.append("PERSISTENCE_NOT_AUTHORIZED")
    if configuration.reservation_creation_authorized is not True:
        codes.append("RESERVATION_CREATION_NOT_AUTHORIZED")
    if configuration.ledger_mutation_authorized is not True:
        codes.append("LEDGER_MUTATION_NOT_AUTHORIZED")
    if codes and configuration.provider_transmission_authorized is not True:
        codes.append("PROVIDER_TRANSMISSION_NOT_AUTHORIZED")
    if codes and configuration.provider_execution_authorized is not True:
        codes.append("PROVIDER_EXECUTION_NOT_AUTHORIZED")
    return _ordered(codes)


def _readiness(configuration: SQLiteReservationPersistenceAdapterConfigurationV1, codes: tuple[str, ...], *, factory_available: bool = False, database_opened: bool = False, pragmas_verified: bool = False, schema_present: bool = False, schema_compatible: bool = False, schema_hash_aligned: bool = False) -> SQLitePersistenceAdapterReadinessResultV1:
    configuration_valid = not any(code in codes for code in (
        "ADAPTER_CONFIGURATION_ID_EMPTY", "ADAPTER_ID_EMPTY", "DATABASE_IDENTITY_EMPTY",
        "LOCATION_CLASSIFICATION_NOT_ALLOWED", "SCHEMA_ID_EMPTY", "SCHEMA_VERSION_INVALID",
        "SCHEMA_HASH_IDENTITY_EMPTY", "CONNECTION_CONFIGURATION_ID_EMPTY", "PERSISTENCE_POLICY_ID_EMPTY",
    ))
    enforcement = schema_compatible and schema_hash_aligned
    ready = not codes and database_opened and pragmas_verified and enforcement
    failures = _ordered(codes + (() if ready else ("ADAPTER_NOT_READY",)))
    return SQLitePersistenceAdapterReadinessResultV1(
        _BoundAdapterConfigurationIdentifier(
            configuration.adapter_configuration_id, configuration.adapter_id, configuration.database_identity,
            configuration.schema_id, configuration.schema_version, configuration.schema_hash_identity,
        ), configuration_valid, configuration_valid, factory_available,
        database_opened, pragmas_verified, schema_present, schema_compatible, schema_hash_aligned,
        enforcement, enforcement, enforcement, enforcement, enforcement, enforcement, ready, False, failures,
    )


def validate_sqlite_reservation_persistence_configuration_v1(
    configuration: SQLiteReservationPersistenceAdapterConfigurationV1,
) -> SQLitePersistenceAdapterReadinessResultV1:
    """Purely validate fail-closed adapter metadata; no connection is opened."""
    if not isinstance(configuration, SQLiteReservationPersistenceAdapterConfigurationV1):
        return SQLitePersistenceAdapterReadinessResultV1("", False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, ("ADAPTER_NOT_READY",))
    return _readiness(configuration, _configuration_codes(configuration))


def _timestamp(value: datetime) -> str:
    if not _utc(value):
        raise ValueError
    return value.isoformat().replace("+00:00", "Z")


def _decode_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not _utc(parsed) or _timestamp(parsed) != value:
        raise ValueError
    return parsed


def _pack(values: tuple[str, ...]) -> str:
    return "".join(f"{len(value)}:{value}" for value in values)


def _unpack(value: object, expected: int) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise ValueError
    values: list[str] = []
    position = 0
    while position < len(value):
        colon = value.find(":", position)
        if colon <= position:
            raise ValueError
        length_text = value[position:colon]
        if not length_text.isdigit():
            raise ValueError
        length = int(length_text)
        start, end = colon + 1, colon + 1 + length
        if end > len(value):
            raise ValueError
        values.append(value[start:end])
        position = end
    if len(values) != expected:
        raise ValueError
    return tuple(values)


def _command_identity(command: ReservationPersistenceCommandV1) -> tuple[str, ...]:
    event = _event(command)
    if event is None:
        raise ValueError
    return (
        command.persistence_command_id, command.reservation_id, command.reservation_request_id, command.request_id,
        command.idempotency_key, command.payload_identity, str(command.expected_revision), command.prior_state,
        command.requested_state, event[0], event[1], command.expected_last_event_id, _timestamp(command.command_created_at),
    )


def _stored_payload(command: ReservationPersistenceCommandV1, snapshot: SQLiteStoredReservationSnapshotV1) -> str:
    return _pack(_command_identity(command) + (
        str(snapshot.revision), snapshot.state, snapshot.last_event_id, str(snapshot.event_count), snapshot.currency,
        format(snapshot.reserved_amount, "f"), format(snapshot.consumed_amount, "f"), format(snapshot.released_amount, "f"),
        _timestamp(snapshot.created_at), _timestamp(snapshot.updated_at), snapshot.serialization_identity,
    ))


def _decode_payload(value: object) -> tuple[tuple[str, ...], SQLiteStoredReservationSnapshotV1]:
    data = _unpack(value, 24)
    revision, event_count = int(data[13]), int(data[16])
    if revision < 0 or event_count < 0:
        raise ValueError
    amounts = tuple(Decimal(item) for item in data[18:21])
    if not all(item.is_finite() and item >= Decimal("0") for item in amounts):
        raise ValueError
    snapshot = SQLiteStoredReservationSnapshotV1(
        data[1], data[2], data[3], data[4], data[5], revision, data[14], data[15], event_count, data[17],
        amounts[0], amounts[1], amounts[2], _decode_timestamp(data[21]), _decode_timestamp(data[22]), data[23],
    )
    if not all(_identifier(item) for item in (snapshot.reservation_id, snapshot.reservation_request_id, snapshot.request_id, snapshot.idempotency_key, snapshot.payload_identity, snapshot.state, snapshot.last_event_id, snapshot.currency, snapshot.serialization_identity)):
        raise ValueError
    return data[:13], snapshot


def _snapshot(command: ReservationPersistenceCommandV1, revision: int, event_count: int) -> SQLiteStoredReservationSnapshotV1:
    event = _event(command)
    if event is None:
        raise ValueError
    identity = "sqlite-reservation-snapshot-v1"
    return SQLiteStoredReservationSnapshotV1(
        command.reservation_id, command.reservation_request_id, command.request_id, command.idempotency_key,
        command.payload_identity, revision, command.requested_state, event[0], event_count, "USD",
        Decimal("0"), Decimal("0"), Decimal("0"), command.command_created_at, command.command_created_at, identity,
    )


def _factory_available(factory: object) -> bool:
    return isinstance(factory, SQLiteConnectionFactoryImplementationV1) and callable(getattr(factory, "connect", None))


class SQLiteReservationPersistencePortAdapterV1:
    """Narrow, explicit test adapter; no connection survives an operation."""

    __slots__ = ("_configuration", "_connection_configuration", "_manifest", "_factory", "_closed")

    def __init__(self, configuration: SQLiteReservationPersistenceAdapterConfigurationV1, connection_configuration: SQLiteConnectionConfigurationV1, schema_manifest: SQLiteSchemaBootstrapManifestV1, connection_factory: SQLiteConnectionFactoryImplementationV1) -> None:
        self._configuration = configuration
        self._connection_configuration = connection_configuration
        self._manifest = schema_manifest
        self._factory = connection_factory
        self._closed = False

    def _base_codes(self) -> tuple[str, ...]:
        codes = list(_configuration_codes(self._configuration))
        connection = self._connection_configuration
        manifest = self._manifest
        if not _factory_available(self._factory):
            codes.append("CONNECTION_FACTORY_REQUIRED")
        if not isinstance(connection, SQLiteConnectionConfigurationV1):
            codes.append("CONNECTION_FACTORY_REQUIRED")
        else:
            if connection.location_classification != "TEST_EPHEMERAL" or connection.database_location.startswith("/tmp/") is not True:
                codes.append("TEST_EPHEMERAL_LOCATION_REQUIRED")
            if connection.connection_configuration_id != self._configuration.connection_configuration_id:
                codes.append("CONNECTION_FACTORY_REQUIRED")
            if connection.database_identity != self._configuration.database_identity:
                codes.append("SCHEMA_IDENTITY_MISMATCH")
            if connection.expected_schema_id != self._configuration.schema_id:
                codes.append("SCHEMA_IDENTITY_MISMATCH")
            if connection.expected_schema_version != self._configuration.schema_version:
                codes.append("SCHEMA_VERSION_MISMATCH")
            if connection.journal_mode != "WAL" or connection.synchronous_mode != "FULL" or connection.foreign_keys_required is not True:
                codes.append("REQUIRED_PRAGMA_NOT_VERIFIED")
        if not isinstance(manifest, SQLiteSchemaBootstrapManifestV1):
            codes.append("SCHEMA_NOT_BOOTSTRAPPED")
        else:
            if manifest.schema_id != self._configuration.schema_id:
                codes.append("SCHEMA_IDENTITY_MISMATCH")
            if manifest.schema_version != self._configuration.schema_version:
                codes.append("SCHEMA_VERSION_MISMATCH")
            if manifest.schema_hash_identity != self._configuration.schema_hash_identity:
                codes.append("SCHEMA_HASH_MISMATCH")
            if manifest.append_only_enforcement_required is not True:
                codes.append("APPEND_ONLY_ENFORCEMENT_MISSING")
            if manifest.revision_monotonicity_required is not True:
                codes.append("REVISION_MONOTONICITY_NOT_ENFORCED")
            if manifest.snapshot_event_alignment_required is not True:
                codes.append("SNAPSHOT_EVENT_ALIGNMENT_NOT_ENFORCED")
        return _ordered(codes)

    def _open_verified(self) -> tuple[SQLiteConnectionHandleV1 | None, tuple[str, ...]]:
        codes = self._base_codes()
        if codes or self._closed:
            return None, _ordered(codes + (("ADAPTER_CLOSED",) if self._closed else ()))
        try:
            handle = self._factory.connect(self._connection_configuration)
        except sqlite3.OperationalError:
            return None, ("CONNECTION_FAILURE",)
        except Exception:
            return None, ("CONNECTION_FAILURE",)
        if not isinstance(handle, SQLiteConnectionHandleV1):
            return None, ("CONNECTION_FAILURE",)
        connection = handle._connection
        try:
            journal = connection.execute("PRAGMA journal_mode = WAL").fetchone()
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {self._connection_configuration.busy_timeout_milliseconds}")
            synchronous = connection.execute("PRAGMA synchronous").fetchone()
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
            busy = connection.execute("PRAGMA busy_timeout").fetchone()
            metadata = connection.execute("SELECT schema_id, schema_version, schema_hash FROM schema_metadata").fetchone()
            objects = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'trigger')").fetchall()}
        except sqlite3.Error:
            handle.close()
            return None, ("SCHEMA_NOT_BOOTSTRAPPED",)
        pragma_ok = bool(journal and str(journal[0]).upper() == "WAL" and synchronous and synchronous[0] == 2 and foreign_keys and foreign_keys[0] == 1 and busy and busy[0] == self._connection_configuration.busy_timeout_milliseconds)
        schema_ok = metadata == (self._manifest.schema_id, self._manifest.schema_version, self._manifest.schema_hash_identity)
        needed = {"schema_metadata", "reservation_snapshots", "reservation_events", "persistence_commands", "recovery_evidence", "reservation_events_no_update", "reservation_events_no_delete"}
        if not pragma_ok or not schema_ok or not needed.issubset(objects):
            handle.close()
            failures: list[str] = []
            if not pragma_ok:
                failures.append("REQUIRED_PRAGMA_NOT_VERIFIED")
            if not schema_ok:
                failures.append("SCHEMA_HASH_MISMATCH")
            if not needed.issubset(objects):
                failures.append("APPEND_ONLY_ENFORCEMENT_MISSING")
            return None, _ordered(failures)
        return handle, ()

    def _record_for_command(self, connection: sqlite3.Connection, command_id: str) -> tuple[tuple[str, ...], SQLiteStoredReservationSnapshotV1] | None:
        row = connection.execute(
            "SELECT recovery_id FROM recovery_evidence WHERE command_id = ?", (command_id,)
        ).fetchone()
        return None if row is None else _decode_payload(row[0])

    def _record_for_idempotency(self, connection: sqlite3.Connection, idempotency_key: str) -> tuple[tuple[str, ...], SQLiteStoredReservationSnapshotV1] | None:
        row = connection.execute(
            "SELECT c.command_id, r.recovery_id FROM persistence_commands c JOIN recovery_evidence r ON r.command_id = c.command_id WHERE c.idempotency_key = ?", (idempotency_key,)
        ).fetchone()
        return None if row is None else _decode_payload(row[1])

    def _current_snapshot(self, connection: sqlite3.Connection, reservation_id: str) -> tuple[tuple[str, ...], SQLiteStoredReservationSnapshotV1] | None:
        row = connection.execute(
            "SELECT r.recovery_id FROM persistence_commands c JOIN recovery_evidence r ON r.command_id = c.command_id WHERE c.reservation_id = ? ORDER BY c.rowid DESC LIMIT 1", (reservation_id,)
        ).fetchone()
        return None if row is None else _decode_payload(row[0])

    def _request_conflict(self, connection: sqlite3.Connection, command: ReservationPersistenceCommandV1) -> bool:
        rows = connection.execute("SELECT recovery_id FROM recovery_evidence").fetchall()
        for row in rows:
            _, snapshot = _decode_payload(row[0])
            if snapshot.request_id == command.request_id and snapshot.reservation_id != command.reservation_id:
                return True
        return False

    def compare_and_append(self, command: ReservationPersistenceCommandV1) -> SQLiteStoredReservationSnapshotV1 | None:
        """Perform one explicit transaction and return a decoded immutable snapshot."""
        if self._closed or _command_codes(command):
            return None
        handle, codes = self._open_verified()
        if handle is None or codes:
            return None
        connection = handle._connection
        began = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            began = True
            existing = self._record_for_command(connection, command.persistence_command_id)
            identity = _command_identity(command)
            if existing is not None:
                connection.rollback()
                began = False
                return existing[1] if existing[0] == identity else None
            idem = self._record_for_idempotency(connection, command.idempotency_key)
            if idem is not None:
                connection.rollback()
                began = False
                return idem[1] if idem[0][1:] == identity[1:] else None
            if self._request_conflict(connection, command):
                connection.rollback()
                began = False
                return None
            current = self._current_snapshot(connection, command.reservation_id)
            event = _event(command)
            if event is None:
                connection.rollback()
                began = False
                return None
            duplicate_event = connection.execute("SELECT event_id, reservation_id, request_id, revision FROM reservation_events WHERE event_id = ?", (event[0],)).fetchone()
            if duplicate_event is not None:
                connection.rollback()
                began = False
                return None
            if current is None:
                if command.expected_revision != 0:
                    connection.rollback()
                    began = False
                    return None
                revision, sequence = 1, 1
            else:
                _, prior = current
                if prior.revision != command.expected_revision or prior.last_event_id != command.expected_last_event_id or prior.state != command.prior_state:
                    connection.rollback()
                    began = False
                    return None
                revision, sequence = prior.revision + 1, prior.event_count + 1
            snapshot = _snapshot(command, revision, sequence)
            if current is None:
                connection.execute(
                    "INSERT INTO reservation_snapshots(reservation_id, revision, last_event_id) VALUES (?, ?, ?)",
                    (snapshot.reservation_id, snapshot.revision, snapshot.last_event_id),
                )
            else:
                connection.execute(
                    "UPDATE reservation_snapshots SET revision = ?, last_event_id = ? WHERE reservation_id = ?",
                    (snapshot.revision, snapshot.last_event_id, snapshot.reservation_id),
                )
            connection.execute(
                "INSERT INTO reservation_events(event_id, reservation_id, request_id, revision) VALUES (?, ?, ?, ?)",
                (event[0], snapshot.reservation_id, snapshot.request_id, snapshot.revision),
            )
            connection.execute(
                "INSERT INTO persistence_commands(command_id, idempotency_key, reservation_id) VALUES (?, ?, ?)",
                (command.persistence_command_id, command.idempotency_key, snapshot.reservation_id),
            )
            connection.execute(
                "INSERT INTO recovery_evidence(recovery_id, command_id) VALUES (?, ?)",
                (_stored_payload(command, snapshot), command.persistence_command_id),
            )
            connection.commit()
            began = False
            return snapshot
        except sqlite3.OperationalError:
            if began:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    return None
            return None
        except (sqlite3.Error, ValueError, InvalidOperation):
            if began:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    return None
            return None
        finally:
            handle.close()

    def read_reservation(self, reservation_id: str) -> SQLiteStoredReservationSnapshotV1 | None:
        """Perform one explicit read-only recovery lookup with no mutation."""
        if self._closed or not _identifier(reservation_id) or self._configuration.require_explicit_recovery is not True:
            return None
        handle, codes = self._open_verified()
        if handle is None or codes:
            return None
        try:
            record = self._current_snapshot(handle._connection, reservation_id)
            if record is None:
                return None
            _, snapshot = record
            row = handle._connection.execute(
                "SELECT revision, last_event_id FROM reservation_snapshots WHERE reservation_id = ?", (reservation_id,)
            ).fetchone()
            count = handle._connection.execute(
                "SELECT COUNT(*) FROM reservation_events WHERE reservation_id = ?", (reservation_id,)
            ).fetchone()
            if row != (snapshot.revision, snapshot.last_event_id) or not count or count[0] != snapshot.event_count:
                return None
            return snapshot
        except (sqlite3.Error, ValueError, InvalidOperation):
            return None
        finally:
            handle.close()

    def close(self) -> bool:
        """Close the adapter lifecycle; no database connection is retained."""
        self._closed = True
        return True


def build_sqlite_reservation_persistence_audit_evidence_v1(
    configuration: SQLiteReservationPersistenceAdapterConfigurationV1,
    command: ReservationPersistenceCommandV1,
    readiness: SQLitePersistenceAdapterReadinessResultV1,
    result: SQLiteStoredReservationSnapshotV1 | None,
) -> SQLitePersistenceAdapterAuditEvidenceV1:
    """Create deterministic redacted evidence without opening SQLite."""
    if not isinstance(configuration, SQLiteReservationPersistenceAdapterConfigurationV1) or not isinstance(command, ReservationPersistenceCommandV1) or not isinstance(readiness, SQLitePersistenceAdapterReadinessResultV1):
        raise ValueError("SQLite persistence audit inputs must be contract records")
    if readiness.adapter_configuration_id != configuration.adapter_configuration_id:
        raise ValueError("SQLite persistence audit identity mismatch")
    if isinstance(readiness.adapter_configuration_id, _BoundAdapterConfigurationIdentifier):
        if readiness.adapter_configuration_id._lineage != (
            configuration.adapter_id, configuration.database_identity, configuration.schema_id,
            configuration.schema_version, configuration.schema_hash_identity,
        ):
            raise ValueError("SQLite persistence audit configuration mismatch")
    if result is not None and (not isinstance(result, SQLiteStoredReservationSnapshotV1) or result.reservation_id != command.reservation_id or result.request_id != command.request_id):
        raise ValueError("SQLite persistence audit result mismatch")
    snapshot = result
    return SQLitePersistenceAdapterAuditEvidenceV1(
        configuration.adapter_configuration_id, configuration.adapter_id, configuration.database_identity,
        configuration.location_classification, configuration.schema_id, configuration.schema_version,
        configuration.schema_hash_identity, command.persistence_command_id, command.reservation_id,
        command.request_id, command.idempotency_key, command.payload_identity, command.expected_revision,
        command.expected_revision if snapshot is None else snapshot.revision, command.expected_last_event_id,
        command.expected_last_event_id if snapshot is None else snapshot.last_event_id,
        snapshot is not None, snapshot is not None, False, False, False, False, False,
        _ordered(readiness.failure_codes), readiness.adapter_ready_for_test_persistence,
        configuration.production_path_authorized, False, False,
    )
