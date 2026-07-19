"""RED contract for a pure injected Phase 12 reservation persistence port."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_12_durable_reservation_persistence_contract_v1 import (
    ReservationPersistenceAuditEvidenceV1,
    ReservationPersistenceCommandV1,
    ReservationPersistenceFailureV1,
    ReservationPersistencePolicyV1,
    ReservationPersistencePortV1,
    ReservationPersistenceResultV1,
    ReservationRecoveryResultV1,
    ReservationSnapshotV1,
    build_reservation_persistence_audit_evidence_v1,
    persist_reservation_transition_v1,
    recover_reservation_state_v1,
)


_NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
_COMMAND_FIELDS = (
    "persistence_command_id", "reservation_id", "reservation_request_id", "request_id",
    "idempotency_key", "payload_identity", "expected_revision", "prior_state",
    "requested_state", "transition_event", "expected_last_event_id", "command_created_at",
    "persistence_authorized",
)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "require_expected_revision", "require_expected_last_event_id",
    "require_unique_command_id", "require_unique_reservation_id", "require_unique_request_id",
    "require_unique_idempotency_key", "require_unique_event_id", "require_append_only_events",
    "require_atomic_compare_and_append", "require_read_after_uncertain_commit",
    "maximum_events_per_append", "persistence_authorized", "reservation_creation_authorized",
    "ledger_mutation_authorized", "provider_transmission_authorized",
    "provider_execution_authorized", "fail_closed",
)
_SNAPSHOT_FIELDS = (
    "reservation_id", "reservation_request_id", "request_id", "idempotency_key",
    "payload_identity", "revision", "state", "last_event_id", "event_count", "reserved_amount",
    "consumed_amount", "released_amount", "created_at", "updated_at", "append_only",
    "durable_state_claimed", "provider_contacted", "transmitted", "provider_execution_authorized",
)
_RESULT_FIELDS = (
    "persistence_command_id", "policy_id", "accepted", "failure_codes", "port_invoked",
    "append_attempted", "append_confirmed", "replay_detected", "conflict_detected",
    "recovery_required", "resulting_snapshot", "reservation_created", "ledger_mutated",
    "provider_contacted", "transmitted", "provider_execution_authorized",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_RECOVERY_FIELDS = (
    "recovery_request_id", "reservation_id", "request_id", "recovered", "found",
    "revision_current", "identity_aligned", "failure_codes", "port_invoked", "recovery_required",
    "snapshot", "reservation_created", "ledger_mutated", "provider_contacted", "transmitted",
    "provider_execution_authorized",
)
_AUDIT_FIELDS = (
    "persistence_command_id", "policy_id", "reservation_id", "request_id", "idempotency_key",
    "payload_identity", "expected_revision", "resulting_revision", "expected_last_event_id",
    "resulting_last_event_id", "event_count", "accepted", "failure_codes", "port_invoked",
    "replay_detected", "conflict_detected", "recovery_required", "reservation_created",
    "ledger_mutated", "provider_contacted", "transmitted", "provider_execution_authorized",
)
_FAILURES = {
    "PERSISTENCE_COMMAND_ID_EMPTY", "RESERVATION_ID_EMPTY", "RESERVATION_REQUEST_ID_EMPTY",
    "REQUEST_ID_EMPTY", "IDEMPOTENCY_KEY_EMPTY", "PAYLOAD_IDENTITY_EMPTY", "POLICY_ID_EMPTY",
    "POLICY_VERSION_EMPTY", "EXPECTED_REVISION_INVALID", "EXPECTED_LAST_EVENT_ID_EMPTY",
    "IDENTIFIER_NOT_NORMALIZED", "PERSISTENCE_PORT_REQUIRED", "PERSISTENCE_NOT_AUTHORIZED",
    "RESERVATION_CREATION_NOT_AUTHORIZED", "LEDGER_MUTATION_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED",
    "MAXIMUM_EVENTS_PER_APPEND_ZERO", "EVENT_BATCH_EMPTY", "EVENT_BATCH_TOO_LARGE",
    "EVENT_ID_EMPTY", "EVENT_ID_DUPLICATE", "EVENT_IDENTITY_CONFLICT", "COMMAND_ID_DUPLICATE",
    "COMMAND_IDENTITY_CONFLICT", "RESERVATION_ID_DUPLICATE", "RESERVATION_IDENTITY_CONFLICT",
    "REQUEST_ID_DUPLICATE", "REQUEST_IDENTITY_CONFLICT", "IDEMPOTENCY_REPLAY",
    "IDEMPOTENCY_CONFLICT", "REVISION_CONFLICT", "LAST_EVENT_ID_CONFLICT",
    "SNAPSHOT_IDENTITY_MISMATCH", "TRANSITION_IDENTITY_MISMATCH", "PARTIAL_APPEND_DETECTED",
    "ATOMICITY_NOT_PROVEN", "PERSISTENCE_REJECTED", "PERSISTENCE_FAILURE",
    "PERSISTENCE_OUTCOME_UNCERTAIN", "RECOVERY_REQUIRED", "RECOVERY_READ_FAILED",
    "RECOVERY_IDENTITY_MISMATCH",
}


def _command(**overrides: object) -> ReservationPersistenceCommandV1:
    values = {
        "persistence_command_id": "persistence-command-v1", "reservation_id": "reservation-v1",
        "reservation_request_id": "reservation-request-v1", "request_id": "provider-request-v1",
        "idempotency_key": "idempotency-v1", "payload_identity": "payload-v1",
        "expected_revision": 0, "prior_state": "PROPOSED", "requested_state": "RESERVED",
        "transition_event": (("event_id", "event-v1"), ("event_type", "RESERVATION_CREATED")),
        "expected_last_event_id": "event-proposed-v1", "command_created_at": _NOW,
        "persistence_authorized": False,
    }
    values.update(overrides)
    return ReservationPersistenceCommandV1(**values)


def _policy(**overrides: object) -> ReservationPersistencePolicyV1:
    values = {
        "policy_id": "persistence-policy-v1", "policy_version": "V1",
        "require_expected_revision": True, "require_expected_last_event_id": True,
        "require_unique_command_id": True, "require_unique_reservation_id": True,
        "require_unique_request_id": True, "require_unique_idempotency_key": True,
        "require_unique_event_id": True, "require_append_only_events": True,
        "require_atomic_compare_and_append": True, "require_read_after_uncertain_commit": True,
        "maximum_events_per_append": 0, "persistence_authorized": False,
        "reservation_creation_authorized": False, "ledger_mutation_authorized": False,
        "provider_transmission_authorized": False, "provider_execution_authorized": False,
        "fail_closed": True,
    }
    values.update(overrides)
    return ReservationPersistencePolicyV1(**values)


def _snapshot() -> ReservationSnapshotV1:
    return ReservationSnapshotV1(
        "reservation-v1", "reservation-request-v1", "provider-request-v1", "idempotency-v1",
        "payload-v1", 1, "RESERVED", "event-v1", 1, Decimal("1.25"), Decimal("0"),
        Decimal("0"), _NOW, _NOW, True, False, False, False, False,
    )


class _FakePort:
    def __init__(self, snapshot: ReservationSnapshotV1 | None = None, raises: bool = False) -> None:
        self.snapshot = snapshot
        self.raises = raises
        self.append_calls = 0
        self.read_calls = 0

    def compare_and_append(self, command: ReservationPersistenceCommandV1) -> ReservationSnapshotV1 | None:
        self.append_calls += 1
        if self.raises:
            raise RuntimeError("test-local-port-failure")
        return self.snapshot

    def read_reservation(self, reservation_id: str) -> ReservationSnapshotV1 | None:
        self.read_calls += 1
        if self.raises:
            raise RuntimeError("test-local-read-failure")
        return self.snapshot


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_immutable_closed_and_secret_free() -> None:
    assert tuple(field.name for field in fields(ReservationPersistenceCommandV1)) == _COMMAND_FIELDS
    assert tuple(field.name for field in fields(ReservationPersistencePolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(ReservationSnapshotV1)) == _SNAPSHOT_FIELDS
    assert tuple(field.name for field in fields(ReservationPersistenceResultV1)) == _RESULT_FIELDS
    assert tuple(field.name for field in fields(ReservationPersistenceFailureV1)) == _FAILURE_FIELDS
    assert tuple(field.name for field in fields(ReservationRecoveryResultV1)) == _RECOVERY_FIELDS
    assert tuple(field.name for field in fields(ReservationPersistenceAuditEvidenceV1)) == _AUDIT_FIELDS
    command, policy, port = _command(), _policy(), _FakePort()
    result = persist_reservation_transition_v1(command, policy, port)
    evidence = build_reservation_persistence_audit_evidence_v1(command, policy, result)
    for value in (command, policy, result, evidence):
        _frozen_slotted(value)
    assert not {"credential", "authorization", "sql", "database", "path"}.intersection(
        field.name for field in fields(command)
    )
    with pytest.raises(FrozenInstanceError):
        command.expected_revision = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        ReservationPersistenceCommandV1(**{field.name: getattr(command, field.name) for field in fields(command)}, sql="forbidden")


def test_default_policy_fails_closed_before_port_invocation() -> None:
    command, policy, port = _command(), _policy(), _FakePort()
    result = persist_reservation_transition_v1(command, policy, port)
    assert result.accepted is False
    assert {
        "PERSISTENCE_NOT_AUTHORIZED", "RESERVATION_CREATION_NOT_AUTHORIZED",
        "LEDGER_MUTATION_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
        "PROVIDER_EXECUTION_NOT_AUTHORIZED", "MAXIMUM_EVENTS_PER_APPEND_ZERO",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert port.append_calls == 0
    assert (result.port_invoked, result.append_attempted, result.append_confirmed, result.reservation_created,
            result.ledger_mutated, result.provider_contacted, result.transmitted,
            result.provider_execution_authorized) == (False, False, False, False, False, False, False, False)


def test_explicit_injected_port_is_narrow_single_attempt_and_identity_bound() -> None:
    assert list(inspect.signature(persist_reservation_transition_v1).parameters) == ["command", "policy", "port"]
    assert list(inspect.signature(recover_reservation_state_v1).parameters) == [
        "recovery_request_id", "reservation_id", "request_id", "expected_revision", "port", "recovery_authorized"
    ]
    assert hasattr(ReservationPersistencePortV1, "compare_and_append")
    assert hasattr(ReservationPersistencePortV1, "read_reservation")
    assert not {"execute", "delete", "truncate", "update", "query"}.intersection(dir(ReservationPersistencePortV1))
    port = _FakePort(_snapshot())
    result = persist_reservation_transition_v1(
        _command(persistence_authorized=True),
        _policy(maximum_events_per_append=1, persistence_authorized=True, reservation_creation_authorized=True,
                ledger_mutation_authorized=True),
        port,
    )
    assert port.append_calls == 1
    assert result.port_invoked is True and result.append_attempted is True
    assert result.provider_contacted is result.transmitted is result.provider_execution_authorized is False


def test_replay_conflict_uncertainty_and_recovery_are_explicit_and_non_operational() -> None:
    assert {
        "COMMAND_ID_DUPLICATE", "COMMAND_IDENTITY_CONFLICT", "IDEMPOTENCY_REPLAY",
        "IDEMPOTENCY_CONFLICT", "EVENT_ID_DUPLICATE", "EVENT_IDENTITY_CONFLICT",
        "PERSISTENCE_OUTCOME_UNCERTAIN", "RECOVERY_REQUIRED", "RECOVERY_READ_FAILED",
        "RECOVERY_IDENTITY_MISMATCH",
    }.issubset(_FAILURES)
    port = _FakePort(raises=True)
    result = persist_reservation_transition_v1(
        _command(persistence_authorized=True),
        _policy(maximum_events_per_append=1, persistence_authorized=True, reservation_creation_authorized=True,
                ledger_mutation_authorized=True),
        port,
    )
    assert port.append_calls == 1
    assert "PERSISTENCE_OUTCOME_UNCERTAIN" in result.failure_codes
    assert result.recovery_required is True
    recovery = recover_reservation_state_v1(
        "recovery-v1", "reservation-v1", "provider-request-v1", 0, _FakePort(), False
    )
    assert recovery.port_invoked is False and recovery.recovery_required is True
    assert recovery.provider_contacted is recovery.transmitted is recovery.provider_execution_authorized is False


def test_audit_evidence_is_deterministic_and_module_has_no_storage_or_operational_surface() -> None:
    command, policy, port = _command(), _policy(), _FakePort()
    result = persist_reservation_transition_v1(command, policy, port)
    assert build_reservation_persistence_audit_evidence_v1(command, policy, result) == build_reservation_persistence_audit_evidence_v1(command, policy, result)
    with pytest.raises(ValueError):
        build_reservation_persistence_audit_evidence_v1(_command(reservation_id="other"), policy, result)
    import engine.phase_12_durable_reservation_persistence_contract_v1 as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    prohibited = {"os", "pathlib", "tempfile", "sqlite3", "subprocess", "socket", "urllib", "http", "requests", "httpx", "aiohttp", "openai", "telegram", "ccxt", "sqlalchemy"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not prohibited.intersection(names | imports)
    assert not {"open", "print", "getenv", "environ", "now", "utcnow", "time", "monotonic", "uuid4", "random", "sleep", "__import__"}.intersection(names)
