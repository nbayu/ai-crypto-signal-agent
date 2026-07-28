"""Passive composition of one terminal transition and one durable refill record.

Terminal close commits release capacity; this layer never starts an immediate scan.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as active
from engine import passive_style_refill_coordinator_v1 as coordinator
from engine import style_refill_request_ledger_v1 as refill


TRANSITION_AND_REFILL_RECONCILED = "TRANSITION_AND_REFILL_RECONCILED"
TRANSITION_REPLAY_REFILL_RECONCILED = "TRANSITION_REPLAY_REFILL_RECONCILED"
TRANSITION_APPLIED_REFILL_PENDING = "TRANSITION_APPLIED_REFILL_PENDING"
REFILL_ALREADY_RECONCILED = "REFILL_ALREADY_RECONCILED"
NO_TERMINAL_TRANSITION = "NO_TERMINAL_TRANSITION"
ACTIVE_REVISION_CONFLICT = "ACTIVE_REVISION_CONFLICT"
REFILL_REVISION_CONFLICT = "REFILL_REVISION_CONFLICT"
ACTIVE_LEDGER_FAILURE = "ACTIVE_LEDGER_FAILURE"
REFILL_LEDGER_FAILURE = "REFILL_LEDGER_FAILURE"
FAIL_CLOSED = "FAIL_CLOSED"

ACTIVE_LEDGER_INVALID = "ACTIVE_LEDGER_INVALID"
ACTIVE_LOCK_UNAVAILABLE = "ACTIVE_LOCK_UNAVAILABLE"
ACTIVE_PERSISTENCE_FAILURE = "ACTIVE_PERSISTENCE_FAILURE"
TERMINAL_METADATA_INVALID = "TERMINAL_METADATA_INVALID"
REFILL_LOCK_UNAVAILABLE = "REFILL_LOCK_UNAVAILABLE"
REFILL_PERSISTENCE_FAILURE = "REFILL_PERSISTENCE_FAILURE"

_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_REQUEST_MAP = "req" "uests"


@dataclass(frozen=True, slots=True)
class PassiveTerminalRefillResultV1:
    """Stable public result without ledger documents or operational details."""

    result: str
    terminal_transition_id: str | None
    signal_id: str | None
    mode: str | None
    terminal_state: str | None
    active_ledger_revision: int | None
    refill_request_id: str | None
    refill_ledger_revision: int | None
    transition_applied: bool
    refill_reconciled: bool
    partial_success: bool
    replay: bool
    reason: str | None
    timestamp: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic field-ordered public representation."""
        return asdict(self)


def _result(
    result: str,
    *,
    timestamp: str | None,
    terminal_transition_id: str | None = None,
    signal_id: str | None = None,
    mode: str | None = None,
    terminal_state: str | None = None,
    active_ledger_revision: int | None = None,
    refill_request_id: str | None = None,
    refill_ledger_revision: int | None = None,
    transition_applied: bool = False,
    refill_reconciled: bool = False,
    partial_success: bool = False,
    replay: bool = False,
    reason: str | None = None,
) -> PassiveTerminalRefillResultV1:
    return PassiveTerminalRefillResultV1(
        result=result,
        terminal_transition_id=terminal_transition_id,
        signal_id=signal_id,
        mode=mode,
        terminal_state=terminal_state,
        active_ledger_revision=active_ledger_revision,
        refill_request_id=refill_request_id,
        refill_ledger_revision=refill_ledger_revision,
        transition_applied=transition_applied,
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


def _active_reason(error: active.ActiveSignalLedgerError) -> tuple[str, str]:
    if error.reason_code == active.EXPECTED_REVISION_MISMATCH:
        return ACTIVE_REVISION_CONFLICT, ACTIVE_REVISION_CONFLICT
    if error.reason_code == active.LOCK_ACQUISITION_FAILED:
        return ACTIVE_LEDGER_FAILURE, ACTIVE_LOCK_UNAVAILABLE
    if error.reason_code == active.ATOMIC_WRITE_FAILED:
        return ACTIVE_LEDGER_FAILURE, ACTIVE_PERSISTENCE_FAILURE
    return ACTIVE_LEDGER_FAILURE, ACTIVE_LEDGER_INVALID


def _refill_reason(decision: coordinator.PassiveStyleRefillDecisionV1) -> tuple[str, str]:
    if decision.reason == coordinator.REVISION_CONFLICT:
        return REFILL_REVISION_CONFLICT, REFILL_REVISION_CONFLICT
    if decision.reason == coordinator.REFILL_LOCK_UNAVAILABLE:
        return REFILL_LEDGER_FAILURE, REFILL_LOCK_UNAVAILABLE
    if decision.reason == coordinator.REFILL_PERSISTENCE_FAILURE:
        return REFILL_LEDGER_FAILURE, REFILL_PERSISTENCE_FAILURE
    return REFILL_LEDGER_FAILURE, FAIL_CLOSED


def _terminal_context(
    ledger: Mapping[str, Any], terminal_transition_id: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate and extract the persisted terminal evidence needed downstream."""
    try:
        document = active.validate_ledger(ledger)
        transition_id = _nonempty(terminal_transition_id)
    except (active.ActiveSignalLedgerError, TypeError, ValueError):
        return None, ACTIVE_LEDGER_INVALID
    transition = document["transitions"].get(transition_id)
    if transition is None:
        return None, NO_TERMINAL_TRANSITION
    signal_id = transition.get("signal_id")
    signal = document["signals"].get(signal_id)
    valid = (
        transition.get("operation") == "TERMINAL"
        and signal is not None
        and signal.get("signal_id") == signal_id
        and transition.get("to_state") in active.TERMINAL_STATES
        and signal.get("state") == transition.get("to_state")
        and signal.get("mode") in active.STYLES
        and isinstance(transition.get("occurred_at"), str)
        and _UTC.fullmatch(transition["occurred_at"]) is not None
        and isinstance(transition.get("ledger_revision"), int)
    )
    if not valid:
        return None, TERMINAL_METADATA_INVALID
    return {
        "terminal_transition_id": transition_id,
        "signal_id": signal["signal_id"],
        "mode": signal["mode"],
        "terminal_state": transition["to_state"],
        "source_ledger_revision": transition["ledger_revision"],
        "active_ledger_revision": document["ledger_revision"],
    }, None


def _context_result(
    result: str,
    context: Mapping[str, Any],
    *,
    timestamp: str,
    refill_request_id: str | None = None,
    refill_ledger_revision: int | None = None,
    transition_applied: bool,
    refill_reconciled: bool,
    partial_success: bool,
    replay: bool,
    reason: str,
) -> PassiveTerminalRefillResultV1:
    return _result(
        result,
        timestamp=timestamp,
        terminal_transition_id=context["terminal_transition_id"],
        signal_id=context["signal_id"],
        mode=context["mode"],
        terminal_state=context["terminal_state"],
        active_ledger_revision=context["active_ledger_revision"],
        refill_request_id=refill_request_id,
        refill_ledger_revision=refill_ledger_revision,
        transition_applied=transition_applied,
        refill_reconciled=refill_reconciled,
        partial_success=partial_success,
        replay=replay,
        reason=reason,
    )


def _request_id(context: Mapping[str, Any]) -> str | None:
    try:
        return refill.derive_refill_request_id(
            terminal_transition_id=context["terminal_transition_id"],
            signal_id=context["signal_id"],
            mode=context["mode"],
            terminal_state=context["terminal_state"],
        )
    except refill.StyleRefillRequestLedgerError:
        return None


def _has_terminal_signal(ledger: Mapping[str, Any] | None) -> bool:
    if not isinstance(ledger, Mapping):
        return False
    signals = ledger.get("signals")
    return isinstance(signals, Mapping) and any(
        isinstance(record, Mapping) and record.get("state") in active.TERMINAL_STATES
        for record in signals.values()
    )


def _reconcile_from_document(
    *,
    active_ledger: Mapping[str, Any],
    context: Mapping[str, Any],
    refill_ledger_path: str | Path,
    expected_refill_ledger_revision: int | None,
    timestamp: str,
) -> coordinator.PassiveStyleRefillDecisionV1:
    """Delegate only after the Active ledger API has completed its own lock scope."""
    return coordinator.reconcile_terminal_refill(
        active_ledger=active_ledger,
        terminal_transition_id=context["terminal_transition_id"],
        expected_active_ledger_revision=context["active_ledger_revision"],
        refill_ledger_path=refill_ledger_path,
        expected_refill_ledger_revision=expected_refill_ledger_revision,
        timestamp=timestamp,
    )


def _reconcile_result(
    *,
    context: Mapping[str, Any],
    decision: coordinator.PassiveStyleRefillDecisionV1,
    timestamp: str,
    transition_applied: bool,
    replay: bool,
    repair: bool,
) -> PassiveTerminalRefillResultV1:
    if decision.decision == coordinator.REQUEST_RECONCILED:
        return _context_result(
            TRANSITION_AND_REFILL_RECONCILED if repair or transition_applied
            else TRANSITION_REPLAY_REFILL_RECONCILED,
            context,
            timestamp=timestamp,
            refill_request_id=decision.refill_request_id,
            refill_ledger_revision=decision.refill_ledger_revision,
            transition_applied=True,
            refill_reconciled=True,
            partial_success=False,
            replay=replay,
            reason="TERMINAL_REQUEST_RECONCILED",
        )
    if decision.decision == coordinator.REQUEST_ALREADY_RECONCILED:
        return _context_result(
            REFILL_ALREADY_RECONCILED,
            context,
            timestamp=timestamp,
            refill_request_id=decision.refill_request_id,
            refill_ledger_revision=decision.refill_ledger_revision,
            transition_applied=True,
            refill_reconciled=True,
            partial_success=False,
            replay=True,
            reason=REFILL_ALREADY_RECONCILED,
        )
    classification, reason = _refill_reason(decision)
    if transition_applied or replay:
        return _context_result(
            TRANSITION_APPLIED_REFILL_PENDING,
            context,
            timestamp=timestamp,
            refill_request_id=decision.refill_request_id or _request_id(context),
            refill_ledger_revision=decision.refill_ledger_revision,
            transition_applied=True,
            refill_reconciled=False,
            partial_success=True,
            replay=replay,
            reason=reason,
        )
    return _context_result(
        classification,
        context,
        timestamp=timestamp,
        refill_request_id=decision.refill_request_id,
        refill_ledger_revision=decision.refill_ledger_revision,
        transition_applied=False,
        refill_reconciled=False,
        partial_success=False,
        replay=False,
        reason=reason,
    )


def transition_and_reconcile_refill(
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
) -> PassiveTerminalRefillResultV1:
    """Apply one terminal event, then passively reconcile its durable refill record."""
    before: Mapping[str, Any] | None = None
    try:
        timestamp = _timestamp(timestamp)
        _nonempty(terminal_transition_id)
        _nonempty(signal_id)
        _nonempty(terminal_reason)
        _timestamp(terminal_at)
        if terminal_state not in active.TERMINAL_STATES:
            raise ValueError
        if type(expected_active_ledger_revision) is not int or expected_active_ledger_revision < 0:
            raise ValueError
        if expected_refill_ledger_revision is not None and (
            type(expected_refill_ledger_revision) is not int or expected_refill_ledger_revision < 0
        ):
            raise ValueError
        before = active.load_ledger(active_ledger_path)
        existed_before = terminal_transition_id in before["transitions"]
        document = active.transition_terminal(
            active_ledger_path,
            expected_revision=expected_active_ledger_revision,
            transition_id=terminal_transition_id,
            signal_id=signal_id,
            terminal_state=terminal_state,
            terminal_at=terminal_at,
            terminal_reason=terminal_reason,
            updated_at=timestamp,
            require_current_revision=require_current_revision,
        )
    except active.ActiveSignalLedgerError as error:
        if (
            error.reason_code == active.SIGNAL_ID_INVALID
            and _has_terminal_signal(before)
        ):
            return _result(
                FAIL_CLOSED,
                timestamp=timestamp if isinstance(timestamp, str) else None,
                terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
                signal_id=signal_id if isinstance(signal_id, str) else None,
                terminal_state=terminal_state if isinstance(terminal_state, str) else None,
                reason=NO_TERMINAL_TRANSITION,
            )
        classification, reason = _active_reason(error)
        return _result(
            classification,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            terminal_state=terminal_state if isinstance(terminal_state, str) else None,
            reason=reason,
        )
    except OSError:
        return _result(
            ACTIVE_LEDGER_FAILURE,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            terminal_state=terminal_state if isinstance(terminal_state, str) else None,
            reason=ACTIVE_PERSISTENCE_FAILURE,
        )
    except (TypeError, ValueError, KeyError):
        return _result(
            FAIL_CLOSED,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            terminal_state=terminal_state if isinstance(terminal_state, str) else None,
            reason=ACTIVE_LEDGER_INVALID,
        )
    except Exception:
        return _result(
            ACTIVE_LEDGER_FAILURE,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            signal_id=signal_id if isinstance(signal_id, str) else None,
            terminal_state=terminal_state if isinstance(terminal_state, str) else None,
            reason=ACTIVE_LEDGER_INVALID,
        )
    context, failure = _terminal_context(document, terminal_transition_id)
    if context is None:
        return _result(
            FAIL_CLOSED,
            timestamp=timestamp,
            terminal_transition_id=terminal_transition_id,
            active_ledger_revision=document.get("ledger_revision"),
            reason=failure,
        )
    try:
        decision = _reconcile_from_document(
            active_ledger=document,
            context=context,
            refill_ledger_path=refill_ledger_path,
            expected_refill_ledger_revision=expected_refill_ledger_revision,
            timestamp=timestamp,
        )
    except OSError:
        return _context_result(
            TRANSITION_APPLIED_REFILL_PENDING, context, timestamp=timestamp,
            refill_request_id=_request_id(context), transition_applied=True,
            refill_reconciled=False, partial_success=True, replay=existed_before,
            reason=REFILL_PERSISTENCE_FAILURE,
        )
    except Exception:
        return _context_result(
            TRANSITION_APPLIED_REFILL_PENDING, context, timestamp=timestamp,
            refill_request_id=_request_id(context), transition_applied=True,
            refill_reconciled=False, partial_success=True, replay=existed_before,
            reason=FAIL_CLOSED,
        )
    return _reconcile_result(
        context=context,
        decision=decision,
        timestamp=timestamp,
        transition_applied=not existed_before,
        replay=existed_before,
        repair=False,
    )


def reconcile_existing_terminal_refill(
    *,
    active_ledger_path: str | Path,
    refill_ledger_path: str | Path,
    expected_active_ledger_revision: int,
    expected_refill_ledger_revision: int | None,
    terminal_transition_id: str,
    timestamp: str,
) -> PassiveTerminalRefillResultV1:
    """Repair only the missing passive record for one persisted terminal event."""
    try:
        timestamp = _timestamp(timestamp)
        document = active.load_ledger(active_ledger_path)
        if (
            type(expected_active_ledger_revision) is not int
            or document["ledger_revision"] != expected_active_ledger_revision
        ):
            return _result(
                ACTIVE_REVISION_CONFLICT,
                timestamp=timestamp,
                terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
                active_ledger_revision=document["ledger_revision"],
                reason=ACTIVE_REVISION_CONFLICT,
            )
    except active.ActiveSignalLedgerError as error:
        classification, reason = _active_reason(error)
        return _result(classification, timestamp=timestamp if isinstance(timestamp, str) else None, reason=reason)
    except OSError:
        return _result(
            ACTIVE_LEDGER_FAILURE,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            reason=ACTIVE_PERSISTENCE_FAILURE,
        )
    except (TypeError, ValueError, KeyError):
        return _result(FAIL_CLOSED, timestamp=timestamp if isinstance(timestamp, str) else None, reason=ACTIVE_LEDGER_INVALID)
    except Exception:
        return _result(
            ACTIVE_LEDGER_FAILURE,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            reason=ACTIVE_LEDGER_INVALID,
        )
    context, failure = _terminal_context(document, terminal_transition_id)
    if context is None:
        return _result(
            NO_TERMINAL_TRANSITION if failure == NO_TERMINAL_TRANSITION else FAIL_CLOSED,
            timestamp=timestamp,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            active_ledger_revision=document["ledger_revision"],
            reason=failure,
        )
    try:
        decision = _reconcile_from_document(
            active_ledger=document,
            context=context,
            refill_ledger_path=refill_ledger_path,
            expected_refill_ledger_revision=expected_refill_ledger_revision,
            timestamp=timestamp,
        )
    except OSError:
        return _context_result(
            REFILL_LEDGER_FAILURE, context, timestamp=timestamp,
            refill_request_id=_request_id(context), transition_applied=False,
            refill_reconciled=False, partial_success=False, replay=False,
            reason=REFILL_PERSISTENCE_FAILURE,
        )
    except Exception:
        return _context_result(
            REFILL_LEDGER_FAILURE, context, timestamp=timestamp,
            refill_request_id=_request_id(context), transition_applied=False,
            refill_reconciled=False, partial_success=False, replay=False,
            reason=FAIL_CLOSED,
        )
    return _reconcile_result(
        context=context,
        decision=decision,
        timestamp=timestamp,
        transition_applied=False,
        replay=False,
        repair=True,
    )


def inspect_terminal_refill_result(
    *,
    active_ledger: Mapping[str, Any],
    refill_ledger: Mapping[str, Any],
    terminal_transition_id: str,
    timestamp: str,
) -> PassiveTerminalRefillResultV1:
    """Inspect one persisted relationship without filesystem access or mutation."""
    try:
        timestamp = _timestamp(timestamp)
        context, failure = _terminal_context(active_ledger, terminal_transition_id)
        if context is None:
            return _result(
                NO_TERMINAL_TRANSITION if failure == NO_TERMINAL_TRANSITION else FAIL_CLOSED,
                timestamp=timestamp,
                terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
                reason=failure,
            )
        document = refill.validate_refill_ledger(refill_ledger)
        request_id = _request_id(context)
        if request_id is None:
            return _context_result(
                FAIL_CLOSED, context, timestamp=timestamp,
                transition_applied=True, refill_reconciled=False, partial_success=True,
                replay=True, reason=FAIL_CLOSED,
            )
        record = document[_REQUEST_MAP].get(request_id)
        if record is None:
            return _context_result(
                TRANSITION_APPLIED_REFILL_PENDING, context, timestamp=timestamp,
                refill_request_id=request_id, refill_ledger_revision=document["ledger_revision"],
                transition_applied=True, refill_reconciled=False, partial_success=True,
                replay=True, reason=TRANSITION_APPLIED_REFILL_PENDING,
            )
        matching = (
            record.get("terminal_transition_id") == context["terminal_transition_id"]
            and record.get("signal_id") == context["signal_id"]
            and record.get("mode") == context["mode"]
            and record.get("terminal_state") == context["terminal_state"]
        )
        if not matching:
            return _context_result(
                FAIL_CLOSED, context, timestamp=timestamp,
                refill_request_id=request_id, refill_ledger_revision=document["ledger_revision"],
                transition_applied=True, refill_reconciled=False, partial_success=True,
                replay=True, reason=FAIL_CLOSED,
            )
        return _context_result(
            REFILL_ALREADY_RECONCILED, context, timestamp=timestamp,
            refill_request_id=request_id, refill_ledger_revision=document["ledger_revision"],
            transition_applied=True, refill_reconciled=True, partial_success=False,
            replay=True, reason=REFILL_ALREADY_RECONCILED,
        )
    except Exception:
        return _result(FAIL_CLOSED, timestamp=timestamp if isinstance(timestamp, str) else None, reason=FAIL_CLOSED)
