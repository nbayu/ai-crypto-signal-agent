"""Caller-driven composition of passive signal lifecycle persistence seams.

Only explicit entry activation delegates to an occupying ledger transition.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as active
from engine import passive_terminal_refill_integration_v1 as terminal_integration


ENTRY_ACTIVATED = "ENTRY_ACTIVATED"
ENTRY_REPLAYED = "ENTRY_REPLAYED"
ENTRY_ALREADY_ACTIVE = "ENTRY_ALREADY_ACTIVE"
PUBLISHED_ENTRY_INSPECTED = "PUBLISHED_ENTRY_INSPECTED"
TERMINAL_AND_REFILL_RECONCILED = "TERMINAL_AND_REFILL_RECONCILED"
TERMINAL_REPLAY_REFILL_RECONCILED = "TERMINAL_REPLAY_REFILL_RECONCILED"
TERMINAL_APPLIED_REFILL_PENDING = "TERMINAL_APPLIED_REFILL_PENDING"
REFILL_ALREADY_RECONCILED = "REFILL_ALREADY_RECONCILED"
NO_SIGNAL = "NO_SIGNAL"
INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
ACTIVE_REVISION_CONFLICT = "ACTIVE_REVISION_CONFLICT"
REFILL_REVISION_CONFLICT = "REFILL_REVISION_CONFLICT"
ACTIVE_LEDGER_FAILURE = "ACTIVE_LEDGER_FAILURE"
REFILL_LEDGER_FAILURE = "REFILL_LEDGER_FAILURE"
FAIL_CLOSED = "FAIL_CLOSED"

ACTIVE_LOCK_UNAVAILABLE = "ACTIVE_LOCK_UNAVAILABLE"
ACTIVE_PERSISTENCE_FAILURE = "ACTIVE_PERSISTENCE_FAILURE"
ACTIVE_LEDGER_INVALID = "ACTIVE_LEDGER_INVALID"
TERMINAL_METADATA_INVALID = "TERMINAL_METADATA_INVALID"

_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


@dataclass(frozen=True, slots=True)
class PassiveSignalLifecycleResultV1:
    """Stable lifecycle result without storage documents or external identifiers."""

    result: str
    operation: str
    signal_id: str | None
    mode: str | None
    previous_state: str | None
    current_state: str | None
    entry_transition_id: str | None
    terminal_transition_id: str | None
    active_ledger_revision: int | None
    refill_request_id: str | None
    refill_ledger_revision: int | None
    entry_applied: bool
    terminal_applied: bool
    refill_reconciled: bool
    partial_success: bool
    replay: bool
    reason: str | None
    timestamp: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return the deterministic public field order."""
        return asdict(self)


def _result(
    result: str,
    *,
    operation: str,
    timestamp: str | None,
    signal_id: str | None = None,
    mode: str | None = None,
    previous_state: str | None = None,
    current_state: str | None = None,
    entry_transition_id: str | None = None,
    terminal_transition_id: str | None = None,
    active_ledger_revision: int | None = None,
    refill_request_id: str | None = None,
    refill_ledger_revision: int | None = None,
    entry_applied: bool = False,
    terminal_applied: bool = False,
    refill_reconciled: bool = False,
    partial_success: bool = False,
    replay: bool = False,
    reason: str | None = None,
) -> PassiveSignalLifecycleResultV1:
    return PassiveSignalLifecycleResultV1(
        result=result,
        operation=operation,
        signal_id=signal_id,
        mode=mode,
        previous_state=previous_state,
        current_state=current_state,
        entry_transition_id=entry_transition_id,
        terminal_transition_id=terminal_transition_id,
        active_ledger_revision=active_ledger_revision,
        refill_request_id=refill_request_id,
        refill_ledger_revision=refill_ledger_revision,
        entry_applied=entry_applied,
        terminal_applied=terminal_applied,
        refill_reconciled=refill_reconciled,
        partial_success=partial_success,
        replay=replay,
        reason=reason,
        timestamp=timestamp,
    )


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise ValueError
    return value


def _nonempty(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError
    return value


def _active_failure(error: active.ActiveSignalLedgerError) -> tuple[str, str]:
    if error.reason_code == active.EXPECTED_REVISION_MISMATCH:
        return ACTIVE_REVISION_CONFLICT, ACTIVE_REVISION_CONFLICT
    if error.reason_code == active.SIGNAL_ID_INVALID:
        return NO_SIGNAL, NO_SIGNAL
    if error.reason_code in {
        active.LIFECYCLE_TRANSITION_INVALID,
        active.TERMINAL_SIGNAL_REOPEN_FORBIDDEN,
        active.TRANSITION_ID_COLLISION,
    }:
        return INVALID_STATE_TRANSITION, INVALID_STATE_TRANSITION
    if error.reason_code == active.LOCK_ACQUISITION_FAILED:
        return ACTIVE_LEDGER_FAILURE, ACTIVE_LOCK_UNAVAILABLE
    if error.reason_code == active.ATOMIC_WRITE_FAILED:
        return ACTIVE_LEDGER_FAILURE, ACTIVE_PERSISTENCE_FAILURE
    return ACTIVE_LEDGER_FAILURE, ACTIVE_LEDGER_INVALID


def _entry_context(
    document: Mapping[str, Any], *, signal_id: str, transition_id: str
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        ledger = active.validate_ledger(document)
    except (active.ActiveSignalLedgerError, TypeError, ValueError):
        return None, ACTIVE_LEDGER_INVALID
    transition = ledger["transitions"].get(transition_id)
    signal = ledger["signals"].get(signal_id)
    valid = (
        transition is not None
        and signal is not None
        and transition.get("operation") == "ENTRY"
        and transition.get("signal_id") == signal_id
        and transition.get("from_state") == active.PUBLISHED_PENDING_ENTRY
        and transition.get("to_state") == active.ENTRY_ACTIVE
        and signal.get("state") == active.ENTRY_ACTIVE
        and signal.get("last_transition_id") == transition_id
        and signal.get("mode") in active.STYLES
        and signal.get("entry_at") == transition.get("occurred_at")
        and isinstance(transition.get("occurred_at"), str)
        and _UTC.fullmatch(transition["occurred_at"]) is not None
    )
    if not valid:
        return None, TERMINAL_METADATA_INVALID
    return {
        "signal_id": signal_id,
        "mode": signal["mode"],
        "previous_state": transition["from_state"],
        "current_state": signal["state"],
        "entry_transition_id": transition_id,
        "active_ledger_revision": ledger["ledger_revision"],
    }, None


def _entry_result(
    result: str,
    *,
    context: Mapping[str, Any],
    timestamp: str,
    applied: bool,
    replay: bool,
    reason: str,
) -> PassiveSignalLifecycleResultV1:
    return _result(
        result,
        operation="ENTRY_ACTIVATION",
        timestamp=timestamp,
        signal_id=context["signal_id"],
        mode=context["mode"],
        previous_state=context["previous_state"],
        current_state=context["current_state"],
        entry_transition_id=context["entry_transition_id"],
        active_ledger_revision=context["active_ledger_revision"],
        entry_applied=applied,
        replay=replay,
        reason=reason,
    )


def activate_signal_entry(
    *,
    active_ledger_path: str | Path,
    expected_active_ledger_revision: int,
    entry_transition_id: str,
    signal_id: str,
    entry_at: str,
    timestamp: str,
    require_current_revision: bool = False,
) -> PassiveSignalLifecycleResultV1:
    """Persist one caller-authorized entry event without external inference."""
    before: Mapping[str, Any] | None = None
    try:
        timestamp = _timestamp(timestamp)
        _timestamp(entry_at)
        _nonempty(entry_transition_id)
        _nonempty(signal_id)
        if type(expected_active_ledger_revision) is not int or expected_active_ledger_revision < 0:
            raise ValueError
        before = active.load_ledger(active_ledger_path)
        previous = before["signals"].get(signal_id)
        document = active.mark_entry_active(
            active_ledger_path,
            expected_revision=expected_active_ledger_revision,
            transition_id=entry_transition_id,
            signal_id=signal_id,
            entry_at=entry_at,
            updated_at=timestamp,
            require_current_revision=require_current_revision,
        )
    except active.ActiveSignalLedgerError as error:
        classification, reason = _active_failure(error)
        return _result(
            classification,
            operation="ENTRY_ACTIVATION",
            timestamp=timestamp if isinstance(timestamp, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            entry_transition_id=entry_transition_id if isinstance(entry_transition_id, str) else None,
            previous_state=previous.get("state") if isinstance(previous, Mapping) else None,
            reason=reason,
        )
    except OSError:
        return _result(
            ACTIVE_LEDGER_FAILURE,
            operation="ENTRY_ACTIVATION",
            timestamp=timestamp if isinstance(timestamp, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            entry_transition_id=entry_transition_id if isinstance(entry_transition_id, str) else None,
            reason=ACTIVE_PERSISTENCE_FAILURE,
        )
    except (TypeError, ValueError, KeyError):
        return _result(
            FAIL_CLOSED,
            operation="ENTRY_ACTIVATION",
            timestamp=timestamp if isinstance(timestamp, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            entry_transition_id=entry_transition_id if isinstance(entry_transition_id, str) else None,
            reason=ACTIVE_LEDGER_INVALID,
        )
    except Exception:
        return _result(
            ACTIVE_LEDGER_FAILURE,
            operation="ENTRY_ACTIVATION",
            timestamp=timestamp if isinstance(timestamp, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            entry_transition_id=entry_transition_id if isinstance(entry_transition_id, str) else None,
            reason=ACTIVE_LEDGER_INVALID,
        )
    context, failure = _entry_context(document, signal_id=signal_id, transition_id=entry_transition_id)
    if context is None:
        return _result(
            FAIL_CLOSED,
            operation="ENTRY_ACTIVATION",
            timestamp=timestamp,
            signal_id=signal_id,
            entry_transition_id=entry_transition_id,
            active_ledger_revision=document.get("ledger_revision"),
            reason=failure,
        )
    replay = before is not None and document["ledger_revision"] == before["ledger_revision"]
    return _entry_result(
        ENTRY_REPLAYED if replay else ENTRY_ACTIVATED,
        context=context,
        timestamp=timestamp,
        applied=not replay,
        replay=replay,
        reason=ENTRY_REPLAYED if replay else ENTRY_ACTIVATED,
    )


def _terminal_result(
    *,
    outcome: terminal_integration.PassiveTerminalRefillResultV1,
    operation: str,
    timestamp: str,
) -> PassiveSignalLifecycleResultV1:
    mapping = {
        terminal_integration.TRANSITION_AND_REFILL_RECONCILED: TERMINAL_AND_REFILL_RECONCILED,
        terminal_integration.TRANSITION_REPLAY_REFILL_RECONCILED: TERMINAL_REPLAY_REFILL_RECONCILED,
        terminal_integration.TRANSITION_APPLIED_REFILL_PENDING: TERMINAL_APPLIED_REFILL_PENDING,
        terminal_integration.REFILL_ALREADY_RECONCILED: REFILL_ALREADY_RECONCILED,
        terminal_integration.ACTIVE_REVISION_CONFLICT: ACTIVE_REVISION_CONFLICT,
        terminal_integration.REFILL_REVISION_CONFLICT: REFILL_REVISION_CONFLICT,
        terminal_integration.ACTIVE_LEDGER_FAILURE: ACTIVE_LEDGER_FAILURE,
        terminal_integration.REFILL_LEDGER_FAILURE: REFILL_LEDGER_FAILURE,
        terminal_integration.NO_TERMINAL_TRANSITION: INVALID_STATE_TRANSITION,
        terminal_integration.FAIL_CLOSED: FAIL_CLOSED,
    }
    result = mapping.get(outcome.result, FAIL_CLOSED)
    return _result(
        result,
        operation=operation,
        timestamp=timestamp,
        signal_id=outcome.signal_id,
        mode=outcome.mode,
        current_state=outcome.terminal_state,
        terminal_transition_id=outcome.terminal_transition_id,
        active_ledger_revision=outcome.active_ledger_revision,
        refill_request_id=outcome.refill_request_id,
        refill_ledger_revision=outcome.refill_ledger_revision,
        terminal_applied=outcome.transition_applied,
        refill_reconciled=outcome.refill_reconciled,
        partial_success=outcome.partial_success,
        replay=outcome.replay,
        reason=outcome.reason if outcome.reason in {
            ACTIVE_REVISION_CONFLICT, REFILL_REVISION_CONFLICT,
            ACTIVE_LOCK_UNAVAILABLE, ACTIVE_PERSISTENCE_FAILURE,
            terminal_integration.REFILL_LOCK_UNAVAILABLE,
            terminal_integration.REFILL_PERSISTENCE_FAILURE,
            terminal_integration.NO_TERMINAL_TRANSITION,
            terminal_integration.TERMINAL_METADATA_INVALID,
            terminal_integration.FAIL_CLOSED,
            terminal_integration.REFILL_ALREADY_RECONCILED,
        } else FAIL_CLOSED,
    )


def terminate_signal_and_reconcile_refill(
    *,
    active_ledger_path: str | Path,
    refill_ledger_path: str | Path,
    expected_active_ledger_revision: int,
    expected_refill_ledger_revision: int | None,
    terminal_transition_id: str,
    signal_id: str,
    terminal_state: str,
    terminal_at: str,
    terminal_reason: str,
    timestamp: str,
    require_current_revision: bool = False,
) -> PassiveSignalLifecycleResultV1:
    """Delegate one terminal event and its durable passive refill reconciliation."""
    try:
        timestamp = _timestamp(timestamp)
        _timestamp(terminal_at)
        _nonempty(terminal_transition_id)
        _nonempty(signal_id)
        _nonempty(terminal_reason)
        if terminal_state not in active.TERMINAL_STATES:
            raise ValueError
        if type(expected_active_ledger_revision) is not int or expected_active_ledger_revision < 0:
            raise ValueError
        if expected_refill_ledger_revision is not None and (
            type(expected_refill_ledger_revision) is not int or expected_refill_ledger_revision < 0
        ):
            raise ValueError
        outcome = terminal_integration.transition_and_reconcile_refill(
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
            require_current_revision=require_current_revision,
        )
        return _terminal_result(outcome=outcome, operation="TERMINAL_TRANSITION", timestamp=timestamp)
    except OSError:
        return _result(
            ACTIVE_LEDGER_FAILURE, operation="TERMINAL_TRANSITION", timestamp=timestamp if isinstance(timestamp, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            reason=ACTIVE_PERSISTENCE_FAILURE,
        )
    except (TypeError, ValueError, KeyError):
        return _result(
            FAIL_CLOSED, operation="TERMINAL_TRANSITION", timestamp=timestamp if isinstance(timestamp, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            reason=FAIL_CLOSED,
        )
    except Exception:
        return _result(
            FAIL_CLOSED, operation="TERMINAL_TRANSITION", timestamp=timestamp if isinstance(timestamp, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            reason=FAIL_CLOSED,
        )


def reconcile_terminal_refill_after_restart(
    *,
    active_ledger_path: str | Path,
    refill_ledger_path: str | Path,
    expected_active_ledger_revision: int,
    expected_refill_ledger_revision: int | None,
    terminal_transition_id: str,
    timestamp: str,
) -> PassiveSignalLifecycleResultV1:
    """Delegate only the explicit passive repair of one persisted terminal event."""
    try:
        timestamp = _timestamp(timestamp)
        _nonempty(terminal_transition_id)
        if type(expected_active_ledger_revision) is not int or expected_active_ledger_revision < 0:
            raise ValueError
        if expected_refill_ledger_revision is not None and (
            type(expected_refill_ledger_revision) is not int or expected_refill_ledger_revision < 0
        ):
            raise ValueError
        outcome = terminal_integration.reconcile_existing_terminal_refill(
            active_ledger_path=active_ledger_path,
            refill_ledger_path=refill_ledger_path,
            expected_active_ledger_revision=expected_active_ledger_revision,
            expected_refill_ledger_revision=expected_refill_ledger_revision,
            terminal_transition_id=terminal_transition_id,
            timestamp=timestamp,
        )
        return _terminal_result(outcome=outcome, operation="TERMINAL_REFILL_REPAIR", timestamp=timestamp)
    except Exception:
        return _result(
            FAIL_CLOSED, operation="TERMINAL_REFILL_REPAIR", timestamp=timestamp if isinstance(timestamp, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            reason=FAIL_CLOSED,
        )


def inspect_signal_lifecycle(
    *,
    active_ledger: Mapping[str, Any],
    signal_id: str,
    entry_transition_id: str | None = None,
    terminal_transition_id: str | None = None,
    refill_ledger: Mapping[str, Any] | None = None,
    timestamp: str,
) -> PassiveSignalLifecycleResultV1:
    """Inspect supplied lifecycle snapshots without filesystem access or mutation."""
    try:
        timestamp = _timestamp(timestamp)
        _nonempty(signal_id)
        ledger = active.validate_ledger(active_ledger)
        signal = ledger["signals"].get(signal_id)
        if signal is None:
            return _result(NO_SIGNAL, operation="INSPECTION", timestamp=timestamp, signal_id=signal_id, reason=NO_SIGNAL)
        common = {
            "operation": "INSPECTION", "timestamp": timestamp, "signal_id": signal_id,
            "mode": signal["mode"], "current_state": signal["state"],
            "active_ledger_revision": ledger["ledger_revision"],
        }
        if signal["state"] == active.PUBLISHED_PENDING_ENTRY:
            return _result(PUBLISHED_ENTRY_INSPECTED, previous_state=None, reason=PUBLISHED_ENTRY_INSPECTED, **common)
        if signal["state"] == active.ENTRY_ACTIVE:
            if entry_transition_id is not None:
                context, failure = _entry_context(ledger, signal_id=signal_id, transition_id=entry_transition_id)
                if context is None:
                    return _result(INVALID_STATE_TRANSITION, entry_transition_id=entry_transition_id, reason=failure, **common)
                return _entry_result(ENTRY_ALREADY_ACTIVE, context=context, timestamp=timestamp, applied=False, replay=False, reason=ENTRY_ALREADY_ACTIVE)
            return _result(ENTRY_ALREADY_ACTIVE, entry_transition_id=signal["last_transition_id"], previous_state=active.PUBLISHED_PENDING_ENTRY, reason=ENTRY_ALREADY_ACTIVE, **common)
        if signal["state"] not in active.TERMINAL_STATES or terminal_transition_id is None or refill_ledger is None:
            return _result(INVALID_STATE_TRANSITION, terminal_transition_id=terminal_transition_id, reason=INVALID_STATE_TRANSITION, **common)
        outcome = terminal_integration.inspect_terminal_refill_result(
            active_ledger=ledger,
            refill_ledger=refill_ledger,
            terminal_transition_id=terminal_transition_id,
            timestamp=timestamp,
        )
        return _terminal_result(outcome=outcome, operation="INSPECTION", timestamp=timestamp)
    except Exception:
        return _result(FAIL_CLOSED, operation="INSPECTION", timestamp=timestamp if isinstance(timestamp, str) else None, reason=FAIL_CLOSED)
