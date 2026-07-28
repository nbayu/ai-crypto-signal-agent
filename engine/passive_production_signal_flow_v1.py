"""Thin caller-driven façade for publication, owner entry, and terminal close.

Publication registration is non-occupying; entry activation is the occupancy seam.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from engine import passive_published_signal_registration_v1 as registration
from engine import passive_signal_lifecycle_service_v1 as lifecycle


REGISTER_COMPLETED_PUBLICATION = "REGISTER_COMPLETED_PUBLICATION"
ACTIVATE_REGISTERED_SIGNAL = "ACTIVATE_REGISTERED_SIGNAL"
TERMINATE_ACTIVE_SIGNAL = "TERMINATE_ACTIVE_SIGNAL"
REPAIR_PUBLICATION_REGISTRATION = "REPAIR_PUBLICATION_REGISTRATION"
REPAIR_TERMINAL_REFILL = "REPAIR_TERMINAL_REFILL"
INSPECT_PRODUCTION_SIGNAL_FLOW = "INSPECT_PRODUCTION_SIGNAL_FLOW"

PUBLISHED_SIGNAL_REGISTERED = "PUBLISHED_SIGNAL_REGISTERED"
PUBLISHED_SIGNAL_REGISTRATION_REPLAYED = "PUBLISHED_SIGNAL_REGISTRATION_REPLAYED"
PUBLICATION_SUCCEEDED_REGISTRATION_PENDING = "PUBLICATION_SUCCEEDED_REGISTRATION_PENDING"
REGISTRATION_ALREADY_PRESENT = "REGISTRATION_ALREADY_PRESENT"
ENTRY_ACTIVATED = "ENTRY_ACTIVATED"
ENTRY_REPLAYED = "ENTRY_REPLAYED"
ENTRY_ALREADY_ACTIVE = "ENTRY_ALREADY_ACTIVE"
PUBLISHED_ENTRY_INSPECTED = "PUBLISHED_ENTRY_INSPECTED"
TERMINAL_AND_REFILL_RECONCILED = "TERMINAL_AND_REFILL_RECONCILED"
TERMINAL_REPLAY_REFILL_RECONCILED = "TERMINAL_REPLAY_REFILL_RECONCILED"
TERMINAL_APPLIED_REFILL_PENDING = "TERMINAL_APPLIED_REFILL_PENDING"
REFILL_ALREADY_RECONCILED = "REFILL_ALREADY_RECONCILED"
NO_REGISTRATION = "NO_REGISTRATION"
NO_SIGNAL = "NO_SIGNAL"
INVALID_OPERATION = "INVALID_OPERATION"
INVALID_PUBLICATION_EVIDENCE = "INVALID_PUBLICATION_EVIDENCE"
INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
SIGNAL_IDENTITY_CONFLICT = "SIGNAL_IDENTITY_CONFLICT"
TRANSACTION_IDENTITY_CONFLICT = "TRANSACTION_IDENTITY_CONFLICT"
RESERVATION_IDENTITY_CONFLICT = "RESERVATION_IDENTITY_CONFLICT"
ACTIVE_REVISION_CONFLICT = "ACTIVE_REVISION_CONFLICT"
REFILL_REVISION_CONFLICT = "REFILL_REVISION_CONFLICT"
ACTIVE_LEDGER_FAILURE = "ACTIVE_LEDGER_FAILURE"
REFILL_LEDGER_FAILURE = "REFILL_LEDGER_FAILURE"
FAIL_CLOSED = "FAIL_CLOSED"

INVALID_INSPECTION_ARGUMENTS = "INVALID_INSPECTION_ARGUMENTS"
CROSS_COMPONENT_IDENTITY_MISMATCH = "CROSS_COMPONENT_IDENTITY_MISMATCH"


@dataclass(frozen=True, slots=True)
class PassiveProductionSignalFlowResultV1:
    """Sanitized, deterministic result for exactly one delegated flow operation."""

    result: str
    operation: str
    signal_id: str | None
    mode: str | None
    symbol: str | None
    delivery_id: str | None
    publication_identity_hash: str | None
    signal_payload_hash: str | None
    reservation_transaction_id: str | None
    reservation_transition_id: str | None
    entry_transition_id: str | None
    terminal_transition_id: str | None
    active_ledger_revision: int | None
    refill_request_id: str | None
    refill_ledger_revision: int | None
    previous_state: str | None
    current_state: str | None
    publication_confirmed: bool
    registration_applied: bool
    entry_applied: bool
    terminal_applied: bool
    refill_reconciled: bool
    partial_success: bool
    replay: bool
    reason: str | None
    timestamp: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return the public schema in declaration order."""
        return asdict(self)


def _result(
    result: str,
    *,
    operation: str,
    timestamp: str | None,
    signal_id: str | None = None,
    mode: str | None = None,
    symbol: str | None = None,
    delivery_id: str | None = None,
    publication_identity_hash: str | None = None,
    signal_payload_hash: str | None = None,
    reservation_transaction_id: str | None = None,
    reservation_transition_id: str | None = None,
    entry_transition_id: str | None = None,
    terminal_transition_id: str | None = None,
    active_ledger_revision: int | None = None,
    refill_request_id: str | None = None,
    refill_ledger_revision: int | None = None,
    previous_state: str | None = None,
    current_state: str | None = None,
    publication_confirmed: bool = False,
    registration_applied: bool = False,
    entry_applied: bool = False,
    terminal_applied: bool = False,
    refill_reconciled: bool = False,
    partial_success: bool = False,
    replay: bool = False,
    reason: str | None = None,
) -> PassiveProductionSignalFlowResultV1:
    return PassiveProductionSignalFlowResultV1(
        result=result,
        operation=operation,
        signal_id=signal_id,
        mode=mode,
        symbol=symbol,
        delivery_id=delivery_id,
        publication_identity_hash=publication_identity_hash,
        signal_payload_hash=signal_payload_hash,
        reservation_transaction_id=reservation_transaction_id,
        reservation_transition_id=reservation_transition_id,
        entry_transition_id=entry_transition_id,
        terminal_transition_id=terminal_transition_id,
        active_ledger_revision=active_ledger_revision,
        refill_request_id=refill_request_id,
        refill_ledger_revision=refill_ledger_revision,
        previous_state=previous_state,
        current_state=current_state,
        publication_confirmed=bool(publication_confirmed),
        registration_applied=bool(registration_applied),
        entry_applied=bool(entry_applied),
        terminal_applied=bool(terminal_applied),
        refill_reconciled=bool(refill_reconciled),
        partial_success=bool(partial_success),
        replay=bool(replay),
        reason=reason,
        timestamp=timestamp,
    )


def _supplied_timestamp(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _registration_result(
    outcome: registration.PassivePublishedSignalRegistrationResultV1,
    *,
    operation: str,
) -> PassiveProductionSignalFlowResultV1:
    return _result(
        outcome.result,
        operation=operation,
        timestamp=outcome.timestamp,
        signal_id=outcome.signal_id,
        mode=outcome.mode,
        symbol=outcome.symbol,
        delivery_id=outcome.delivery_id,
        publication_identity_hash=outcome.publication_identity_hash,
        signal_payload_hash=outcome.signal_payload_hash,
        reservation_transaction_id=outcome.reservation_transaction_id,
        reservation_transition_id=outcome.reservation_transition_id,
        active_ledger_revision=outcome.active_ledger_revision,
        current_state=outcome.current_state,
        publication_confirmed=outcome.publication_confirmed,
        registration_applied=outcome.registration_applied,
        partial_success=outcome.partial_success,
        replay=outcome.replay,
        reason=outcome.reason,
    )


def _lifecycle_result(
    outcome: lifecycle.PassiveSignalLifecycleResultV1,
    *,
    operation: str,
) -> PassiveProductionSignalFlowResultV1:
    return _result(
        outcome.result,
        operation=operation,
        timestamp=outcome.timestamp,
        signal_id=outcome.signal_id,
        mode=outcome.mode,
        entry_transition_id=outcome.entry_transition_id,
        terminal_transition_id=outcome.terminal_transition_id,
        active_ledger_revision=outcome.active_ledger_revision,
        refill_request_id=outcome.refill_request_id,
        refill_ledger_revision=outcome.refill_ledger_revision,
        previous_state=outcome.previous_state,
        current_state=outcome.current_state,
        entry_applied=outcome.entry_applied,
        terminal_applied=outcome.terminal_applied,
        refill_reconciled=outcome.refill_reconciled,
        partial_success=outcome.partial_success,
        replay=outcome.replay,
        reason=outcome.reason,
    )


def _failure(
    *,
    operation: str,
    timestamp: object,
    signal_id: object = None,
    reservation_transition_id: object = None,
    entry_transition_id: object = None,
    terminal_transition_id: object = None,
    reason: str = FAIL_CLOSED,
) -> PassiveProductionSignalFlowResultV1:
    return _result(
        FAIL_CLOSED,
        operation=operation,
        timestamp=_supplied_timestamp(timestamp),
        signal_id=signal_id if isinstance(signal_id, str) else None,
        reservation_transition_id=(
            reservation_transition_id if isinstance(reservation_transition_id, str) else None
        ),
        entry_transition_id=entry_transition_id if isinstance(entry_transition_id, str) else None,
        terminal_transition_id=(
            terminal_transition_id if isinstance(terminal_transition_id, str) else None
        ),
        reason=reason,
    )


def register_completed_publication(
    *,
    active_ledger_path: object,
    expected_active_ledger_revision: object,
    publication_evidence: object,
    reservation_transition_id: object,
    timestamp: object,
) -> PassiveProductionSignalFlowResultV1:
    """Delegate one completed-publication registration and normalize its result."""
    try:
        outcome = registration.register_published_signal(
            active_ledger_path=active_ledger_path,
            expected_active_ledger_revision=expected_active_ledger_revision,
            publication_evidence=publication_evidence,
            reservation_transition_id=reservation_transition_id,
            timestamp=timestamp,
        )
        return _registration_result(outcome, operation=REGISTER_COMPLETED_PUBLICATION)
    except Exception:
        return _failure(
            operation=REGISTER_COMPLETED_PUBLICATION,
            timestamp=timestamp,
            reservation_transition_id=reservation_transition_id,
        )


def activate_registered_signal(
    *,
    active_ledger_path: object,
    expected_active_ledger_revision: object,
    entry_transition_id: object,
    signal_id: object,
    entry_at: object,
    timestamp: object,
) -> PassiveProductionSignalFlowResultV1:
    """Delegate one caller-authorized entry activation and normalize its result."""
    try:
        outcome = lifecycle.activate_signal_entry(
            active_ledger_path=active_ledger_path,
            expected_active_ledger_revision=expected_active_ledger_revision,
            entry_transition_id=entry_transition_id,
            signal_id=signal_id,
            entry_at=entry_at,
            timestamp=timestamp,
            require_current_revision=True,
        )
        return _lifecycle_result(outcome, operation=ACTIVATE_REGISTERED_SIGNAL)
    except Exception:
        return _failure(
            operation=ACTIVATE_REGISTERED_SIGNAL,
            timestamp=timestamp,
            signal_id=signal_id,
            entry_transition_id=entry_transition_id,
        )


def terminate_active_signal(
    *,
    active_ledger_path: object,
    refill_ledger_path: object,
    expected_active_ledger_revision: object,
    expected_refill_ledger_revision: object,
    terminal_transition_id: object,
    signal_id: object,
    terminal_state: object,
    terminal_at: object,
    terminal_reason: object,
    timestamp: object,
) -> PassiveProductionSignalFlowResultV1:
    """Delegate one terminal/refill operation and normalize its result."""
    try:
        outcome = lifecycle.terminate_signal_and_reconcile_refill(
            active_ledger_path=active_ledger_path,
            refill_ledger_path=refill_ledger_path,
            expected_active_ledger_revision=expected_active_ledger_revision,
            expected_refill_ledger_revision=expected_refill_ledger_revision,
            terminal_transition_id=terminal_transition_id,
            signal_id=signal_id,
            terminal_state=terminal_state,
            terminal_at=terminal_at,
            terminal_reason=terminal_reason,
            timestamp=timestamp,
            require_current_revision=True,
        )
        return _lifecycle_result(outcome, operation=TERMINATE_ACTIVE_SIGNAL)
    except Exception:
        return _failure(
            operation=TERMINATE_ACTIVE_SIGNAL,
            timestamp=timestamp,
            signal_id=signal_id,
            terminal_transition_id=terminal_transition_id,
        )


def repair_publication_registration(
    *,
    active_ledger_path: object,
    expected_active_ledger_revision: object,
    publication_evidence: object,
    reservation_transition_id: object,
    timestamp: object,
) -> PassiveProductionSignalFlowResultV1:
    """Delegate one explicit registration repair and normalize its result."""
    try:
        outcome = registration.reconcile_published_signal_registration(
            active_ledger_path=active_ledger_path,
            expected_active_ledger_revision=expected_active_ledger_revision,
            publication_evidence=publication_evidence,
            reservation_transition_id=reservation_transition_id,
            timestamp=timestamp,
        )
        return _registration_result(outcome, operation=REPAIR_PUBLICATION_REGISTRATION)
    except Exception:
        return _failure(
            operation=REPAIR_PUBLICATION_REGISTRATION,
            timestamp=timestamp,
            reservation_transition_id=reservation_transition_id,
        )


def repair_terminal_refill(
    *,
    active_ledger_path: object,
    refill_ledger_path: object,
    expected_active_ledger_revision: object,
    expected_refill_ledger_revision: object,
    terminal_transition_id: object,
    timestamp: object,
) -> PassiveProductionSignalFlowResultV1:
    """Delegate one explicit terminal-refill repair and normalize its result."""
    try:
        outcome = lifecycle.reconcile_terminal_refill_after_restart(
            active_ledger_path=active_ledger_path,
            refill_ledger_path=refill_ledger_path,
            expected_active_ledger_revision=expected_active_ledger_revision,
            expected_refill_ledger_revision=expected_refill_ledger_revision,
            terminal_transition_id=terminal_transition_id,
            timestamp=timestamp,
        )
        return _lifecycle_result(outcome, operation=REPAIR_TERMINAL_REFILL)
    except Exception:
        return _failure(
            operation=REPAIR_TERMINAL_REFILL,
            timestamp=timestamp,
            terminal_transition_id=terminal_transition_id,
        )


def _invalid_inspection(
    *, timestamp: object, signal_id: object
) -> PassiveProductionSignalFlowResultV1:
    return _result(
        INVALID_OPERATION,
        operation=INSPECT_PRODUCTION_SIGNAL_FLOW,
        timestamp=_supplied_timestamp(timestamp),
        signal_id=signal_id if isinstance(signal_id, str) else None,
        reason=INVALID_INSPECTION_ARGUMENTS,
    )


def _combined_inspection(
    registration_outcome: registration.PassivePublishedSignalRegistrationResultV1,
    lifecycle_outcome: lifecycle.PassiveSignalLifecycleResultV1,
) -> PassiveProductionSignalFlowResultV1:
    if (
        registration_outcome.signal_id != lifecycle_outcome.signal_id
        or (
            registration_outcome.mode is not None
            and lifecycle_outcome.mode is not None
            and registration_outcome.mode != lifecycle_outcome.mode
        )
    ):
        return _result(
            FAIL_CLOSED,
            operation=INSPECT_PRODUCTION_SIGNAL_FLOW,
            timestamp=lifecycle_outcome.timestamp,
            signal_id=lifecycle_outcome.signal_id or registration_outcome.signal_id,
            mode=lifecycle_outcome.mode or registration_outcome.mode,
            symbol=registration_outcome.symbol,
            delivery_id=registration_outcome.delivery_id,
            publication_identity_hash=registration_outcome.publication_identity_hash,
            signal_payload_hash=registration_outcome.signal_payload_hash,
            reservation_transaction_id=registration_outcome.reservation_transaction_id,
            reservation_transition_id=registration_outcome.reservation_transition_id,
            active_ledger_revision=lifecycle_outcome.active_ledger_revision,
            publication_confirmed=registration_outcome.publication_confirmed,
            reason=CROSS_COMPONENT_IDENTITY_MISMATCH,
        )
    return _result(
        lifecycle_outcome.result,
        operation=INSPECT_PRODUCTION_SIGNAL_FLOW,
        timestamp=lifecycle_outcome.timestamp,
        signal_id=lifecycle_outcome.signal_id,
        mode=lifecycle_outcome.mode,
        symbol=registration_outcome.symbol,
        delivery_id=registration_outcome.delivery_id,
        publication_identity_hash=registration_outcome.publication_identity_hash,
        signal_payload_hash=registration_outcome.signal_payload_hash,
        reservation_transaction_id=registration_outcome.reservation_transaction_id,
        reservation_transition_id=registration_outcome.reservation_transition_id,
        entry_transition_id=lifecycle_outcome.entry_transition_id,
        terminal_transition_id=lifecycle_outcome.terminal_transition_id,
        active_ledger_revision=lifecycle_outcome.active_ledger_revision,
        refill_request_id=lifecycle_outcome.refill_request_id,
        refill_ledger_revision=lifecycle_outcome.refill_ledger_revision,
        previous_state=lifecycle_outcome.previous_state,
        current_state=lifecycle_outcome.current_state,
        publication_confirmed=registration_outcome.publication_confirmed,
        registration_applied=registration_outcome.registration_applied,
        entry_applied=lifecycle_outcome.entry_applied,
        terminal_applied=lifecycle_outcome.terminal_applied,
        refill_reconciled=lifecycle_outcome.refill_reconciled,
        partial_success=lifecycle_outcome.partial_success,
        replay=lifecycle_outcome.replay,
        reason=lifecycle_outcome.reason,
    )


def _lifecycle_inspection_failure(result: str) -> bool:
    return result in {
        lifecycle.INVALID_STATE_TRANSITION,
        lifecycle.ACTIVE_REVISION_CONFLICT,
        lifecycle.REFILL_REVISION_CONFLICT,
        lifecycle.ACTIVE_LEDGER_FAILURE,
        lifecycle.REFILL_LEDGER_FAILURE,
        lifecycle.FAIL_CLOSED,
    }


def inspect_production_signal_flow(
    *,
    active_ledger: object,
    signal_id: object,
    timestamp: object,
    publication_evidence: object = None,
    reservation_transition_id: object = None,
    entry_transition_id: object = None,
    terminal_transition_id: object = None,
    refill_ledger: object = None,
) -> PassiveProductionSignalFlowResultV1:
    """Inspect supplied snapshots only; no persistence action is performed."""
    evidence_present = publication_evidence is not None
    reservation_present = reservation_transition_id is not None
    terminal_present = terminal_transition_id is not None
    refill_present = refill_ledger is not None
    if evidence_present != reservation_present or terminal_present != refill_present:
        return _invalid_inspection(timestamp=timestamp, signal_id=signal_id)
    try:
        if not evidence_present:
            outcome = lifecycle.inspect_signal_lifecycle(
                active_ledger=active_ledger,
                signal_id=signal_id,
                entry_transition_id=entry_transition_id,
                terminal_transition_id=terminal_transition_id,
                refill_ledger=refill_ledger,
                timestamp=timestamp,
            )
            return _lifecycle_result(outcome, operation=INSPECT_PRODUCTION_SIGNAL_FLOW)
        registration_outcome = registration.inspect_published_signal_registration(
            active_ledger=active_ledger,
            publication_evidence=publication_evidence,
            reservation_transition_id=reservation_transition_id,
            timestamp=timestamp,
        )
        if registration_outcome.result not in {
            registration.REGISTRATION_ALREADY_PRESENT,
            registration.NO_REGISTRATION,
        }:
            return _registration_result(
                registration_outcome,
                operation=INSPECT_PRODUCTION_SIGNAL_FLOW,
            )
        lifecycle_outcome = lifecycle.inspect_signal_lifecycle(
            active_ledger=active_ledger,
            signal_id=signal_id,
            entry_transition_id=entry_transition_id,
            terminal_transition_id=terminal_transition_id,
            refill_ledger=refill_ledger,
            timestamp=timestamp,
        )
        if _lifecycle_inspection_failure(lifecycle_outcome.result):
            return _lifecycle_result(
                lifecycle_outcome,
                operation=INSPECT_PRODUCTION_SIGNAL_FLOW,
            )
        if lifecycle_outcome.result == lifecycle.NO_SIGNAL:
            return _registration_result(
                registration_outcome,
                operation=INSPECT_PRODUCTION_SIGNAL_FLOW,
            )
        if registration_outcome.result == registration.NO_REGISTRATION:
            return _lifecycle_result(
                lifecycle_outcome,
                operation=INSPECT_PRODUCTION_SIGNAL_FLOW,
            )
        return _combined_inspection(registration_outcome, lifecycle_outcome)
    except Exception:
        return _failure(
            operation=INSPECT_PRODUCTION_SIGNAL_FLOW,
            timestamp=timestamp,
            signal_id=signal_id,
        )
