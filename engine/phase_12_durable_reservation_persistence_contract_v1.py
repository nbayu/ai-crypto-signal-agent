"""Pure, injected durable-reservation compare-and-append boundary.

This module deliberately owns no persistence.  A caller supplies a narrow port;
the returned records are only immutable evidence of that port interaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol


class _BoundCommandIdentifier(str):
    """A string identifier carrying immutable local result lineage.

    The public value remains exactly the command identifier.  The tuple is used
    only to prevent audit evidence from being projected against a different
    command after a pre-port rejection, where no snapshot exists to bind it.
    """

    def __new__(
        cls, value: str, reservation_id: str, reservation_request_id: str, request_id: str,
        idempotency_key: str, payload_identity: str,
    ) -> _BoundCommandIdentifier:
        instance = str.__new__(cls, value)
        object.__setattr__(
            instance, "_lineage", (reservation_id, reservation_request_id, request_id, idempotency_key, payload_identity),
        )
        return instance

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("immutable command identifier")


@dataclass(frozen=True, slots=True)
class ReservationPersistenceCommandV1:
    persistence_command_id: str
    reservation_id: str
    reservation_request_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    expected_revision: int
    prior_state: str
    requested_state: str
    transition_event: tuple[tuple[str, str], ...]
    expected_last_event_id: str
    command_created_at: datetime
    persistence_authorized: bool


@dataclass(frozen=True, slots=True)
class ReservationPersistencePolicyV1:
    policy_id: str
    policy_version: str
    require_expected_revision: bool
    require_expected_last_event_id: bool
    require_unique_command_id: bool
    require_unique_reservation_id: bool
    require_unique_request_id: bool
    require_unique_idempotency_key: bool
    require_unique_event_id: bool
    require_append_only_events: bool
    require_atomic_compare_and_append: bool
    require_read_after_uncertain_commit: bool
    maximum_events_per_append: int
    persistence_authorized: bool
    reservation_creation_authorized: bool
    ledger_mutation_authorized: bool
    provider_transmission_authorized: bool
    provider_execution_authorized: bool
    fail_closed: bool


class ReservationPersistencePortV1(Protocol):
    def compare_and_append(self, command: ReservationPersistenceCommandV1) -> ReservationSnapshotV1 | None:
        """Atomically compare the command's revision/event and append at most once."""

    def read_reservation(self, reservation_id: str) -> ReservationSnapshotV1 | None:
        """Read a reservation only when an explicitly authorized recovery asks for it."""


@dataclass(frozen=True, slots=True)
class ReservationPersistenceFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class ReservationSnapshotV1:
    reservation_id: str
    reservation_request_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    revision: int
    state: str
    last_event_id: str
    event_count: int
    reserved_amount: Decimal
    consumed_amount: Decimal
    released_amount: Decimal
    created_at: datetime
    updated_at: datetime
    append_only: bool
    durable_state_claimed: bool
    provider_contacted: bool
    transmitted: bool
    provider_execution_authorized: bool


@dataclass(frozen=True, slots=True)
class ReservationPersistenceResultV1:
    persistence_command_id: str
    policy_id: str
    accepted: bool
    failure_codes: tuple[str, ...]
    port_invoked: bool
    append_attempted: bool
    append_confirmed: bool
    replay_detected: bool
    conflict_detected: bool
    recovery_required: bool
    resulting_snapshot: ReservationSnapshotV1 | None
    reservation_created: bool
    ledger_mutated: bool
    provider_contacted: bool
    transmitted: bool
    provider_execution_authorized: bool


@dataclass(frozen=True, slots=True)
class ReservationRecoveryResultV1:
    recovery_request_id: str
    reservation_id: str
    request_id: str
    recovered: bool
    found: bool
    revision_current: bool
    identity_aligned: bool
    failure_codes: tuple[str, ...]
    port_invoked: bool
    recovery_required: bool
    snapshot: ReservationSnapshotV1 | None
    reservation_created: bool
    ledger_mutated: bool
    provider_contacted: bool
    transmitted: bool
    provider_execution_authorized: bool


@dataclass(frozen=True, slots=True)
class ReservationPersistenceAuditEvidenceV1:
    persistence_command_id: str
    policy_id: str
    reservation_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    expected_revision: int
    resulting_revision: int
    expected_last_event_id: str
    resulting_last_event_id: str
    event_count: int
    accepted: bool
    failure_codes: tuple[str, ...]
    port_invoked: bool
    replay_detected: bool
    conflict_detected: bool
    recovery_required: bool
    reservation_created: bool
    ledger_mutated: bool
    provider_contacted: bool
    transmitted: bool
    provider_execution_authorized: bool


def _add(codes: tuple[str, ...], code: str) -> tuple[str, ...]:
    return codes if code in codes else codes + (code,)


def _ordered(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(codes))


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _utc(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo == UTC


def _event(command: ReservationPersistenceCommandV1) -> tuple[str, str] | None:
    event = command.transition_event
    if not isinstance(event, tuple) or not event:
        return None
    pairs: dict[str, str] = {}
    for item in event:
        if not isinstance(item, tuple) or len(item) != 2:
            return None
        key, value = item
        if not isinstance(key, str) or not isinstance(value, str) or key in pairs:
            return None
        pairs[key] = value
    event_id, event_type = pairs.get("event_id"), pairs.get("event_type")
    if not _identifier(event_id) or not _identifier(event_type):
        return None
    return event_id, event_type


def _command_value(command: object, name: str) -> str:
    value = getattr(command, name, "")
    return value if isinstance(value, str) else ""


def _policy_value(policy: object, name: str) -> str:
    value = getattr(policy, name, "")
    return value if isinstance(value, str) else ""


def _result(
    command: object, policy: object, codes: tuple[str, ...], *, port_invoked: bool = False,
    append_attempted: bool = False, append_confirmed: bool = False, replay_detected: bool = False,
    conflict_detected: bool = False, recovery_required: bool = False,
    snapshot: ReservationSnapshotV1 | None = None, accepted: bool = False,
) -> ReservationPersistenceResultV1:
    command_id = _command_value(command, "persistence_command_id")
    if isinstance(command, ReservationPersistenceCommandV1):
        command_id = _BoundCommandIdentifier(
            command_id, command.reservation_id, command.reservation_request_id, command.request_id,
            command.idempotency_key, command.payload_identity,
        )
    return ReservationPersistenceResultV1(
        command_id, _policy_value(policy, "policy_id"), accepted,
        _ordered(codes), port_invoked, append_attempted, append_confirmed, replay_detected,
        conflict_detected, recovery_required, snapshot, False, False, False, False, False,
    )


def _preconditions(
    command: ReservationPersistenceCommandV1, policy: ReservationPersistencePolicyV1, port: object,
) -> tuple[str, ...]:
    codes: tuple[str, ...] = ()
    identities = (
        (command.persistence_command_id, "PERSISTENCE_COMMAND_ID_EMPTY"),
        (command.reservation_id, "RESERVATION_ID_EMPTY"),
        (command.reservation_request_id, "RESERVATION_REQUEST_ID_EMPTY"),
        (command.request_id, "REQUEST_ID_EMPTY"),
        (command.idempotency_key, "IDEMPOTENCY_KEY_EMPTY"),
        (command.payload_identity, "PAYLOAD_IDENTITY_EMPTY"),
        (policy.policy_id, "POLICY_ID_EMPTY"),
        (policy.policy_version, "POLICY_VERSION_EMPTY"),
        (command.expected_last_event_id, "EXPECTED_LAST_EVENT_ID_EMPTY"),
    )
    for value, empty_code in identities:
        if not isinstance(value, str) or not value:
            codes = _add(codes, empty_code)
        elif not _identifier(value):
            codes = _add(codes, "IDENTIFIER_NOT_NORMALIZED")
    if not isinstance(command.expected_revision, int) or isinstance(command.expected_revision, bool) or command.expected_revision < 0:
        codes = _add(codes, "EXPECTED_REVISION_INVALID")
    if not _identifier(command.prior_state) or not _identifier(command.requested_state) or not _utc(command.command_created_at):
        codes = _add(codes, "TRANSITION_IDENTITY_MISMATCH")
    if _event(command) is None:
        codes = _add(codes, "EVENT_BATCH_EMPTY")
    if port is None or not callable(getattr(port, "compare_and_append", None)):
        codes = _add(codes, "PERSISTENCE_PORT_REQUIRED")
    if command.persistence_authorized is not True or policy.persistence_authorized is not True:
        codes = _add(codes, "PERSISTENCE_NOT_AUTHORIZED")
    if policy.reservation_creation_authorized is not True:
        codes = _add(codes, "RESERVATION_CREATION_NOT_AUTHORIZED")
    if policy.ledger_mutation_authorized is not True:
        codes = _add(codes, "LEDGER_MUTATION_NOT_AUTHORIZED")
    maximum = policy.maximum_events_per_append
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
        codes = _add(codes, "MAXIMUM_EVENTS_PER_APPEND_ZERO")
    if policy.require_atomic_compare_and_append is not True:
        codes = _add(codes, "ATOMICITY_NOT_PROVEN")
    # Persistence is intentionally not provider transmission.  Provider authority stays false
    # on every result and cannot be inferred from a successful append.
    if codes and policy.provider_transmission_authorized is not True:
        codes = _add(codes, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED")
    if codes and policy.provider_execution_authorized is not True:
        codes = _add(codes, "PROVIDER_EXECUTION_NOT_AUTHORIZED")
    return _ordered(codes)


def _snapshot_failures(
    command: ReservationPersistenceCommandV1, snapshot: object,
) -> tuple[str, ...]:
    if not isinstance(snapshot, ReservationSnapshotV1):
        return ("PERSISTENCE_FAILURE",)
    codes: tuple[str, ...] = ()
    expected = (
        (snapshot.reservation_id, command.reservation_id),
        (snapshot.reservation_request_id, command.reservation_request_id),
        (snapshot.request_id, command.request_id),
        (snapshot.idempotency_key, command.idempotency_key),
        (snapshot.payload_identity, command.payload_identity),
    )
    if any(actual != wanted for actual, wanted in expected):
        codes = _add(codes, "SNAPSHOT_IDENTITY_MISMATCH")
    event = _event(command)
    if event is None or snapshot.last_event_id != event[0]:
        codes = _add(codes, "LAST_EVENT_ID_CONFLICT")
    if (not isinstance(snapshot.revision, int) or isinstance(snapshot.revision, bool)
            or snapshot.revision != command.expected_revision + 1):
        codes = _add(codes, "REVISION_CONFLICT")
    if (not isinstance(snapshot.event_count, int) or isinstance(snapshot.event_count, bool)
            or snapshot.event_count <= 0 or snapshot.event_count != snapshot.revision):
        codes = _add(codes, "PARTIAL_APPEND_DETECTED")
    if snapshot.append_only is not True:
        codes = _add(codes, "ATOMICITY_NOT_PROVEN")
    if snapshot.provider_contacted or snapshot.transmitted or snapshot.provider_execution_authorized:
        codes = _add(codes, "PERSISTENCE_FAILURE")
    return _ordered(codes)


def persist_reservation_transition_v1(
    command: ReservationPersistenceCommandV1, policy: ReservationPersistencePolicyV1,
    port: ReservationPersistencePortV1 | None,
) -> ReservationPersistenceResultV1:
    """Make one authorized compare-and-append attempt, never retrying or reading."""
    if not isinstance(command, ReservationPersistenceCommandV1) or not isinstance(policy, ReservationPersistencePolicyV1):
        return _result(command, policy, ("PERSISTENCE_FAILURE",))
    failures = _preconditions(command, policy, port)
    if failures:
        return _result(command, policy, failures)
    try:
        snapshot = port.compare_and_append(command)  # type: ignore[union-attr]
    except Exception:
        return _result(
            command, policy, ("PERSISTENCE_OUTCOME_UNCERTAIN", "RECOVERY_REQUIRED"),
            port_invoked=True, append_attempted=True, recovery_required=True,
        )
    if snapshot is None:
        return _result(command, policy, ("PERSISTENCE_REJECTED",), port_invoked=True, append_attempted=True)
    failures = _snapshot_failures(command, snapshot)
    if failures:
        return _result(
            command, policy, failures, port_invoked=True, append_attempted=True,
            conflict_detected=True, snapshot=snapshot if isinstance(snapshot, ReservationSnapshotV1) else None,
        )
    return _result(
        command, policy, (), port_invoked=True, append_attempted=True, append_confirmed=True,
        snapshot=snapshot, accepted=True,
    )


def _recovery_result(
    recovery_request_id: object, reservation_id: object, request_id: object, *, recovered: bool = False,
    found: bool = False, revision_current: bool = False, identity_aligned: bool = False,
    codes: tuple[str, ...] = (), port_invoked: bool = False, recovery_required: bool = False,
    snapshot: ReservationSnapshotV1 | None = None,
) -> ReservationRecoveryResultV1:
    return ReservationRecoveryResultV1(
        recovery_request_id if isinstance(recovery_request_id, str) else "",
        reservation_id if isinstance(reservation_id, str) else "", request_id if isinstance(request_id, str) else "",
        recovered, found, revision_current, identity_aligned, _ordered(codes), port_invoked,
        recovery_required, snapshot, False, False, False, False, False,
    )


def recover_reservation_state_v1(
    recovery_request_id: str, reservation_id: str, request_id: str, expected_revision: int,
    port: ReservationPersistencePortV1 | None, recovery_authorized: bool,
) -> ReservationRecoveryResultV1:
    """Perform one explicitly authorized read-only recovery lookup."""
    invalid = not all(_identifier(value) for value in (recovery_request_id, reservation_id, request_id))
    invalid_revision = (not isinstance(expected_revision, int) or isinstance(expected_revision, bool)
                        or expected_revision < 0)
    if invalid or invalid_revision:
        return _recovery_result(recovery_request_id, reservation_id, request_id, codes=("RECOVERY_IDENTITY_MISMATCH",), recovery_required=True)
    if recovery_authorized is not True:
        return _recovery_result(recovery_request_id, reservation_id, request_id, codes=("RECOVERY_REQUIRED",), recovery_required=True)
    if port is None or not callable(getattr(port, "read_reservation", None)):
        return _recovery_result(recovery_request_id, reservation_id, request_id, codes=("PERSISTENCE_PORT_REQUIRED",), recovery_required=True)
    try:
        snapshot = port.read_reservation(reservation_id)
    except Exception:
        return _recovery_result(
            recovery_request_id, reservation_id, request_id,
            codes=("PERSISTENCE_OUTCOME_UNCERTAIN", "RECOVERY_READ_FAILED"), port_invoked=True,
            recovery_required=True,
        )
    if snapshot is None:
        return _recovery_result(recovery_request_id, reservation_id, request_id, found=False, identity_aligned=True)
    if not isinstance(snapshot, ReservationSnapshotV1):
        return _recovery_result(recovery_request_id, reservation_id, request_id, found=True, codes=("RECOVERY_READ_FAILED",), port_invoked=True, recovery_required=True)
    aligned = snapshot.reservation_id == reservation_id and snapshot.request_id == request_id
    if not aligned:
        return _recovery_result(
            recovery_request_id, reservation_id, request_id, found=True, codes=("RECOVERY_IDENTITY_MISMATCH",),
            port_invoked=True, recovery_required=True, snapshot=snapshot,
        )
    current = isinstance(snapshot.revision, int) and not isinstance(snapshot.revision, bool) and snapshot.revision >= expected_revision
    if not current:
        return _recovery_result(
            recovery_request_id, reservation_id, request_id, found=True, identity_aligned=True,
            codes=("REVISION_CONFLICT",), port_invoked=True, recovery_required=True, snapshot=snapshot,
        )
    return _recovery_result(
        recovery_request_id, reservation_id, request_id, recovered=True, found=True, revision_current=True,
        identity_aligned=True, port_invoked=True, snapshot=snapshot,
    )


def build_reservation_persistence_audit_evidence_v1(
    command: ReservationPersistenceCommandV1, policy: ReservationPersistencePolicyV1,
    result: ReservationPersistenceResultV1,
) -> ReservationPersistenceAuditEvidenceV1:
    """Project validated immutable result evidence without touching the injected port."""
    if not isinstance(command, ReservationPersistenceCommandV1) or not isinstance(policy, ReservationPersistencePolicyV1) or not isinstance(result, ReservationPersistenceResultV1):
        raise ValueError("persistence evidence inputs must be contract records")
    if result.persistence_command_id != command.persistence_command_id or result.policy_id != policy.policy_id:
        raise ValueError("persistence evidence identity mismatch")
    if isinstance(result.persistence_command_id, _BoundCommandIdentifier):
        expected_lineage = (
            command.reservation_id, command.reservation_request_id, command.request_id,
            command.idempotency_key, command.payload_identity,
        )
        if result.persistence_command_id._lineage != expected_lineage:
            raise ValueError("persistence evidence command mismatch")
    snapshot = result.resulting_snapshot
    if snapshot is not None:
        if _snapshot_failures(command, snapshot):
            raise ValueError("persistence evidence snapshot mismatch")
        revision, last_event_id, event_count = snapshot.revision, snapshot.last_event_id, snapshot.event_count
    else:
        revision, last_event_id, event_count = command.expected_revision, command.expected_last_event_id, 0
    if result.provider_contacted or result.transmitted or result.provider_execution_authorized:
        raise ValueError("persistence evidence operational mismatch")
    return ReservationPersistenceAuditEvidenceV1(
        command.persistence_command_id, policy.policy_id, command.reservation_id, command.request_id,
        command.idempotency_key, command.payload_identity, command.expected_revision, revision,
        command.expected_last_event_id, last_event_id, event_count, result.accepted, _ordered(result.failure_codes),
        result.port_invoked, result.replay_detected, result.conflict_detected, result.recovery_required,
        result.reservation_created, result.ledger_mutated, False, False, False,
    )
