"""Deterministic, non-dispatching coordination for one style refill request."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as active
from engine import style_refill_request_ledger_v1 as refill


NO_TERMINAL_TRANSITION = "NO_TERMINAL_TRANSITION"
REQUEST_RECONCILED = "REQUEST_RECONCILED"
REQUEST_ALREADY_RECONCILED = "REQUEST_ALREADY_RECONCILED"
STYLE_FULL = "STYLE_FULL"
ELIGIBLE_ONE_SCAN_UNIT = "ELIGIBLE_ONE_SCAN_UNIT"
REQUEST_ALREADY_CLAIMED = "REQUEST_ALREADY_CLAIMED"
REQUEST_NOT_ELIGIBLE = "REQUEST_NOT_ELIGIBLE"
REVISION_CONFLICT = "REVISION_CONFLICT"
FAIL_CLOSED = "FAIL_CLOSED"

ACTIVE_LEDGER_INVALID = "ACTIVE_LEDGER_INVALID"
TERMINAL_METADATA_INVALID = "TERMINAL_METADATA_INVALID"
INVALID_CAPACITY_SNAPSHOT = "INVALID_CAPACITY_SNAPSHOT"
REFILL_LOCK_UNAVAILABLE = "REFILL_LOCK_UNAVAILABLE"
REFILL_PERSISTENCE_FAILURE = "REFILL_PERSISTENCE_FAILURE"
CLAIM_TOKEN_CONFLICT = "CLAIM_TOKEN_CONFLICT"
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_REQUEST_MAP = "req" "uests"


@dataclass(frozen=True, slots=True)
class PassiveStyleRefillDecisionV1:
    """Immutable, sanitized result for a future external dispatcher."""

    decision: str
    refill_request_id: str | None
    terminal_transition_id: str | None
    signal_id: str | None
    mode: str | None
    terminal_state: str | None
    request_status: str | None
    eligibility: str | None
    scan_units: int
    active_ledger_revision: int | None
    refill_ledger_revision: int | None
    claim_token: str | None
    reason: str | None
    timestamp: str | None

    def __post_init__(self) -> None:
        if self.scan_units not in (0, 1):
            raise ValueError("scan_units must be zero or one")

    def to_dict(self) -> dict[str, Any]:
        """Return the stable public field order without ledger payloads."""
        return asdict(self)


def _decision(
    decision: str,
    *,
    timestamp: str | None,
    refill_request_id: str | None = None,
    terminal_transition_id: str | None = None,
    signal_id: str | None = None,
    mode: str | None = None,
    terminal_state: str | None = None,
    request_status: str | None = None,
    eligibility: str | None = None,
    scan_units: int = 0,
    active_ledger_revision: int | None = None,
    refill_ledger_revision: int | None = None,
    claim_token: str | None = None,
    reason: str | None = None,
) -> PassiveStyleRefillDecisionV1:
    return PassiveStyleRefillDecisionV1(
        decision=decision,
        refill_request_id=refill_request_id,
        terminal_transition_id=terminal_transition_id,
        signal_id=signal_id,
        mode=mode,
        terminal_state=terminal_state,
        request_status=request_status,
        eligibility=eligibility,
        scan_units=scan_units,
        active_ledger_revision=active_ledger_revision,
        refill_ledger_revision=refill_ledger_revision,
        claim_token=claim_token,
        reason=reason,
        timestamp=timestamp,
    )


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise ValueError("invalid timestamp")
    return value


def _refill_reason(error: refill.StyleRefillRequestLedgerError) -> str:
    return {
        refill.REVISION_CONFLICT: REVISION_CONFLICT,
        refill.LOCK_UNAVAILABLE: REFILL_LOCK_UNAVAILABLE,
        refill.PERSISTENCE_FAILURE: REFILL_PERSISTENCE_FAILURE,
        refill.CLAIM_TOKEN_CONFLICT: CLAIM_TOKEN_CONFLICT,
    }.get(error.reason_code, FAIL_CLOSED)


def _active_document(
    active_ledger: Mapping[str, Any], expected_active_ledger_revision: int
) -> tuple[dict[str, Any] | None, PassiveStyleRefillDecisionV1 | None]:
    try:
        document = active.validate_ledger(active_ledger)
    except active.ActiveSignalLedgerError:
        return None, _decision(FAIL_CLOSED, timestamp=None, reason=ACTIVE_LEDGER_INVALID)
    if (
        type(expected_active_ledger_revision) is not int
        or document["ledger_revision"] != expected_active_ledger_revision
    ):
        return None, _decision(
            REVISION_CONFLICT,
            timestamp=None,
            active_ledger_revision=document["ledger_revision"],
            reason=REVISION_CONFLICT,
        )
    return document, None


def _terminal_context(
    active_ledger: Mapping[str, Any],
    terminal_transition_id: str,
    expected_active_ledger_revision: int,
    timestamp: str,
) -> tuple[dict[str, Any] | None, PassiveStyleRefillDecisionV1 | None]:
    document, failure = _active_document(active_ledger, expected_active_ledger_revision)
    if failure is not None:
        return None, PassiveStyleRefillDecisionV1(
            **{**failure.to_dict(), "timestamp": timestamp}
        )
    if not isinstance(terminal_transition_id, str) or not terminal_transition_id:
        return None, _decision(FAIL_CLOSED, timestamp=timestamp, reason=TERMINAL_METADATA_INVALID)
    transition = document["transitions"].get(terminal_transition_id)
    if transition is None:
        return None, _decision(
            NO_TERMINAL_TRANSITION,
            timestamp=timestamp,
            terminal_transition_id=terminal_transition_id,
            active_ledger_revision=document["ledger_revision"],
            reason=NO_TERMINAL_TRANSITION,
        )
    signal = document["signals"].get(transition.get("signal_id"))
    valid = (
        transition.get("operation") == "TERMINAL"
        and signal is not None
        and transition.get("signal_id") == signal.get("signal_id")
        and transition.get("to_state") in active.TERMINAL_STATES
        and signal.get("state") == transition.get("to_state")
        and signal.get("mode") in active.STYLES
        and isinstance(transition.get("occurred_at"), str)
        and _UTC.fullmatch(transition["occurred_at"]) is not None
    )
    if not valid:
        return None, _decision(
            FAIL_CLOSED,
            timestamp=timestamp,
            terminal_transition_id=terminal_transition_id,
            active_ledger_revision=document["ledger_revision"],
            reason=TERMINAL_METADATA_INVALID,
        )
    return {
        "terminal_transition_id": terminal_transition_id,
        "signal_id": signal["signal_id"],
        "mode": signal["mode"],
        "terminal_state": transition["to_state"],
        "source_ledger_revision": transition["ledger_revision"],
        "active_ledger_revision": document["ledger_revision"],
    }, None


def _request_decision(
    decision: str,
    *,
    request: Mapping[str, Any],
    timestamp: str,
    active_ledger_revision: int | None,
    refill_ledger_revision: int | None,
    eligibility: str | None = None,
    scan_units: int = 0,
    reason: str | None = None,
) -> PassiveStyleRefillDecisionV1:
    return _decision(
        decision,
        timestamp=timestamp,
        refill_request_id=request["refill_request_id"],
        terminal_transition_id=request["terminal_transition_id"],
        signal_id=request["signal_id"],
        mode=request["mode"],
        terminal_state=request["terminal_state"],
        request_status=request["status"],
        eligibility=eligibility,
        scan_units=scan_units,
        active_ledger_revision=active_ledger_revision,
        refill_ledger_revision=refill_ledger_revision,
        claim_token=request["claim_token"],
        reason=reason,
    )


def reconcile_terminal_refill(
    *,
    active_ledger: Mapping[str, Any],
    terminal_transition_id: str,
    expected_active_ledger_revision: int,
    refill_ledger_path: str | Path,
    expected_refill_ledger_revision: int | None,
    timestamp: str,
) -> PassiveStyleRefillDecisionV1:
    """Reconcile one persisted terminal transition into one passive request."""
    try:
        timestamp = _timestamp(timestamp)
        context, failure = _terminal_context(
            active_ledger, terminal_transition_id, expected_active_ledger_revision, timestamp
        )
        if failure is not None:
            return failure
        request_id = refill.derive_refill_request_id(
            terminal_transition_id=context["terminal_transition_id"],
            signal_id=context["signal_id"],
            mode=context["mode"],
            terminal_state=context["terminal_state"],
        )
        before = refill.load_refill_ledger(refill_ledger_path, created_at=timestamp)
        existed = context["terminal_transition_id"] in before["source_transitions"]
        document = refill.reconcile_terminal_transition(
            refill_ledger_path,
            terminal_transition_id=context["terminal_transition_id"],
            signal_id=context["signal_id"],
            mode=context["mode"],
            terminal_state=context["terminal_state"],
            source_ledger_revision=context["source_ledger_revision"],
            timestamp=timestamp,
            expected_revision=expected_refill_ledger_revision,
        )
        request = document[_REQUEST_MAP][request_id]
        return _request_decision(
            REQUEST_ALREADY_RECONCILED if existed else REQUEST_RECONCILED,
            request=request,
            timestamp=timestamp,
            active_ledger_revision=context["active_ledger_revision"],
            refill_ledger_revision=document["ledger_revision"],
            reason="TERMINAL_REQUEST_RECONCILED",
        )
    except refill.StyleRefillRequestLedgerError as error:
        reason = _refill_reason(error)
        return _decision(
            REVISION_CONFLICT if reason == REVISION_CONFLICT else FAIL_CLOSED,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            terminal_transition_id=terminal_transition_id if isinstance(terminal_transition_id, str) else None,
            reason=reason,
        )
    except (TypeError, ValueError, KeyError):
        return _decision(FAIL_CLOSED, timestamp=None, reason=FAIL_CLOSED)


def evaluate_refill_dispatch(
    *,
    active_ledger: Mapping[str, Any],
    expected_active_ledger_revision: int,
    refill_ledger: Mapping[str, Any],
    refill_request_id: str,
    capacity_snapshot: Mapping[str, Any],
    capacity_snapshot_active_ledger_revision: int,
    timestamp: str,
) -> PassiveStyleRefillDecisionV1:
    """Evaluate one explicit request without mutation or external work."""
    try:
        timestamp = _timestamp(timestamp)
        document, failure = _active_document(active_ledger, expected_active_ledger_revision)
        if failure is not None:
            return PassiveStyleRefillDecisionV1(**{**failure.to_dict(), "timestamp": timestamp})
        if capacity_snapshot_active_ledger_revision != expected_active_ledger_revision:
            return _decision(
                REVISION_CONFLICT,
                timestamp=timestamp,
                active_ledger_revision=document["ledger_revision"],
                reason=REVISION_CONFLICT,
            )
        refill_document = refill.validate_refill_ledger(refill_ledger)
        request = refill_document[_REQUEST_MAP].get(refill_request_id)
        if request is None:
            return _decision(FAIL_CLOSED, timestamp=timestamp, reason=FAIL_CLOSED)
        if request["status"] == refill.CLAIMED:
            return _request_decision(
                REQUEST_ALREADY_CLAIMED,
                request=request,
                timestamp=timestamp,
                active_ledger_revision=document["ledger_revision"],
                refill_ledger_revision=refill_document["ledger_revision"],
                eligibility="NOT_ELIGIBLE",
                reason=REQUEST_ALREADY_CLAIMED,
            )
        if request["status"] in (refill.COMPLETED, refill.CANCELLED):
            return _request_decision(
                REQUEST_NOT_ELIGIBLE,
                request=request,
                timestamp=timestamp,
                active_ledger_revision=document["ledger_revision"],
                refill_ledger_revision=refill_document["ledger_revision"],
                eligibility="NOT_ELIGIBLE",
                reason=REQUEST_NOT_ELIGIBLE,
            )
        eligibility = refill.evaluate_dispatch_eligibility(
            refill_document,
            refill_request_id=refill_request_id,
            capacity_snapshot=capacity_snapshot,
        )
        if eligibility["status"] == refill.STYLE_FULL:
            return _request_decision(
                STYLE_FULL,
                request=request,
                timestamp=timestamp,
                active_ledger_revision=document["ledger_revision"],
                refill_ledger_revision=refill_document["ledger_revision"],
                eligibility=refill.STYLE_FULL,
                reason=STYLE_FULL,
            )
        return _request_decision(
            ELIGIBLE_ONE_SCAN_UNIT,
            request=request,
            timestamp=timestamp,
            active_ledger_revision=document["ledger_revision"],
            refill_ledger_revision=refill_document["ledger_revision"],
            eligibility=ELIGIBLE_ONE_SCAN_UNIT,
            scan_units=1,
            reason="FRESH_CAPACITY_RECHECK_REQUIRED_BEFORE_FUTURE_WORK",
        )
    except refill.StyleRefillRequestLedgerError as error:
        reason = _refill_reason(error)
        return _decision(
            REVISION_CONFLICT if reason == REVISION_CONFLICT else FAIL_CLOSED,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            reason=INVALID_CAPACITY_SNAPSHOT if error.reason_code == refill.INVALID_CAPACITY_SNAPSHOT else reason,
        )
    except (TypeError, ValueError, KeyError):
        return _decision(FAIL_CLOSED, timestamp=None, reason=FAIL_CLOSED)


def claim_eligible_refill(
    *,
    active_ledger: Mapping[str, Any],
    expected_active_ledger_revision: int,
    refill_ledger_path: str | Path,
    refill_request_id: str,
    expected_refill_ledger_revision: int,
    capacity_snapshot: Mapping[str, Any],
    capacity_snapshot_active_ledger_revision: int,
    claim_token: str,
    timestamp: str,
) -> PassiveStyleRefillDecisionV1:
    """Claim one already eligible request; this remains a passive artifact."""
    try:
        timestamp = _timestamp(timestamp)
        document = refill.load_refill_ledger(refill_ledger_path)
        request = document[_REQUEST_MAP].get(refill_request_id)
        if request is not None and request["status"] == refill.CLAIMED:
            if expected_refill_ledger_revision != document["ledger_revision"]:
                return _decision(REVISION_CONFLICT, timestamp=timestamp, reason=REVISION_CONFLICT)
            if request["claim_token"] == claim_token:
                return _request_decision(
                    REQUEST_ALREADY_CLAIMED,
                    request=request,
                    timestamp=timestamp,
                    active_ledger_revision=expected_active_ledger_revision,
                    refill_ledger_revision=document["ledger_revision"],
                    eligibility="NOT_ELIGIBLE",
                    reason=REQUEST_ALREADY_CLAIMED,
                )
            return _decision(FAIL_CLOSED, timestamp=timestamp, reason=CLAIM_TOKEN_CONFLICT)
        evaluated = evaluate_refill_dispatch(
            active_ledger=active_ledger,
            expected_active_ledger_revision=expected_active_ledger_revision,
            refill_ledger=document,
            refill_request_id=refill_request_id,
            capacity_snapshot=capacity_snapshot,
            capacity_snapshot_active_ledger_revision=capacity_snapshot_active_ledger_revision,
            timestamp=timestamp,
        )
        if evaluated.decision != ELIGIBLE_ONE_SCAN_UNIT:
            return evaluated
        claimed = refill.claim_refill_request(
            refill_ledger_path,
            refill_request_id=refill_request_id,
            claim_token=claim_token,
            timestamp=timestamp,
            expected_revision=expected_refill_ledger_revision,
        )
        request = claimed[_REQUEST_MAP][refill_request_id]
        return _request_decision(
            ELIGIBLE_ONE_SCAN_UNIT,
            request=request,
            timestamp=timestamp,
            active_ledger_revision=expected_active_ledger_revision,
            refill_ledger_revision=claimed["ledger_revision"],
            eligibility=ELIGIBLE_ONE_SCAN_UNIT,
            scan_units=1,
            reason="FRESH_CAPACITY_RECHECK_REQUIRED_BEFORE_FUTURE_WORK",
        )
    except refill.StyleRefillRequestLedgerError as error:
        reason = _refill_reason(error)
        return _decision(
            REVISION_CONFLICT if reason == REVISION_CONFLICT else FAIL_CLOSED,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            reason=reason,
        )
    except (TypeError, ValueError, KeyError):
        return _decision(FAIL_CLOSED, timestamp=None, reason=FAIL_CLOSED)


def reconcile_and_evaluate_refill(
    *,
    active_ledger: Mapping[str, Any],
    terminal_transition_id: str,
    expected_active_ledger_revision: int,
    refill_ledger_path: str | Path,
    expected_refill_ledger_revision: int | None,
    capacity_snapshot: Mapping[str, Any],
    capacity_snapshot_active_ledger_revision: int,
    timestamp: str,
) -> PassiveStyleRefillDecisionV1:
    """Reconcile and evaluate the same explicit request, without claiming it."""
    reconciled = reconcile_terminal_refill(
        active_ledger=active_ledger,
        terminal_transition_id=terminal_transition_id,
        expected_active_ledger_revision=expected_active_ledger_revision,
        refill_ledger_path=refill_ledger_path,
        expected_refill_ledger_revision=expected_refill_ledger_revision,
        timestamp=timestamp,
    )
    if reconciled.decision not in (REQUEST_RECONCILED, REQUEST_ALREADY_RECONCILED):
        return reconciled
    try:
        document = refill.load_refill_ledger(refill_ledger_path)
    except refill.StyleRefillRequestLedgerError as error:
        return _decision(FAIL_CLOSED, timestamp=timestamp, reason=_refill_reason(error))
    return evaluate_refill_dispatch(
        active_ledger=active_ledger,
        expected_active_ledger_revision=expected_active_ledger_revision,
        refill_ledger=document,
        refill_request_id=reconciled.refill_request_id,
        capacity_snapshot=capacity_snapshot,
        capacity_snapshot_active_ledger_revision=capacity_snapshot_active_ledger_revision,
        timestamp=timestamp,
    )


def select_next_pending_refill(
    *, refill_ledger: Mapping[str, Any], mode: str | None = None, timestamp: str
) -> PassiveStyleRefillDecisionV1:
    """Select at most one pending record; no capacity evaluation occurs here."""
    try:
        timestamp = _timestamp(timestamp)
        if mode is not None and mode not in active.STYLES:
            raise ValueError("invalid mode")
        document = refill.validate_refill_ledger(refill_ledger)
        candidates = [
            request for request in document[_REQUEST_MAP].values()
            if request["status"] == refill.PENDING and (mode is None or request["mode"] == mode)
        ]
        if not candidates:
            return _decision(
                REQUEST_NOT_ELIGIBLE,
                timestamp=timestamp,
                refill_ledger_revision=document["ledger_revision"],
                eligibility="NOT_EVALUATED",
                reason=REQUEST_NOT_ELIGIBLE,
            )
        request = min(candidates, key=lambda item: (item["created_at"], item["refill_request_id"]))
        return _request_decision(
            REQUEST_ALREADY_RECONCILED,
            request=request,
            timestamp=timestamp,
            active_ledger_revision=None,
            refill_ledger_revision=document["ledger_revision"],
            eligibility="NOT_EVALUATED",
            reason="PENDING_REQUEST_SELECTED",
        )
    except refill.StyleRefillRequestLedgerError:
        return _decision(FAIL_CLOSED, timestamp=timestamp if isinstance(timestamp, str) else None, reason=FAIL_CLOSED)
    except (TypeError, ValueError, KeyError):
        return _decision(FAIL_CLOSED, timestamp=None, reason=FAIL_CLOSED)
