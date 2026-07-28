"""Durable, fail-closed active-signal capacity ledger.

This module is deliberately a narrow persistence seam.  It records lifecycle
metadata only; it does not publish signals, refill capacity, schedule work, or
invoke any transport/runtime component.
"""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping


SCHEMA_NAME = "active-signal-ledger"
SCHEMA_VERSION = 2

SWING = "SWING"
INTRADAY = "INTRADAY"
SCALP = "SCALP"
STYLES = (SWING, INTRADAY, SCALP)
CAPACITY_BY_MODE = {SWING: 3, INTRADAY: 3, SCALP: 3}
TOTAL_CAPACITY = 9
CAPACITY_SCOPE = "PER_TRADING_STYLE"

PUBLISHED_PENDING_ENTRY = "PUBLISHED_PENDING_ENTRY"
ENTRY_ACTIVE = "ENTRY_ACTIVE"
CLOSED_PROFIT = "CLOSED_PROFIT"
CLOSED_STOP_LOSS = "CLOSED_STOP_LOSS"
CLOSED_MANUAL = "CLOSED_MANUAL"
REJECTED_BY_OWNER = "REJECTED_BY_OWNER"
CANCELLED = "CANCELLED"
EXPIRED = "EXPIRED"
INVALIDATED = "INVALIDATED"
OCCUPYING_STATES = (ENTRY_ACTIVE,)
TERMINAL_STATES = (
    CLOSED_PROFIT,
    CLOSED_STOP_LOSS,
    CLOSED_MANUAL,
    REJECTED_BY_OWNER,
    CANCELLED,
    EXPIRED,
    INVALIDATED,
)
LIFECYCLE_STATES = (PUBLISHED_PENDING_ENTRY,) + OCCUPYING_STATES + TERMINAL_STATES

PREPARED = "PREPARED"
OCCUPANCY_COMMITTED = "OCCUPANCY_COMMITTED"
ABORTED = "ABORTED"
PUBLICATION_TRANSACTION_STATES = (PREPARED, OCCUPANCY_COMMITTED, ABORTED)

LEDGER_NOT_FOUND = "LEDGER_NOT_FOUND"
LEDGER_SCHEMA_UNSUPPORTED = "LEDGER_SCHEMA_UNSUPPORTED"
LEDGER_CORRUPT = "LEDGER_CORRUPT"
SIGNAL_ID_INVALID = "SIGNAL_ID_INVALID"
SIGNAL_ALREADY_EXISTS = "SIGNAL_ALREADY_EXISTS"
SIGNAL_ID_COLLISION = "SIGNAL_ID_COLLISION"
PUBLICATION_ID_COLLISION = "PUBLICATION_ID_COLLISION"
STYLE_INVALID = "STYLE_INVALID"
STYLE_IMMUTABLE = "STYLE_IMMUTABLE"
LIFECYCLE_TRANSITION_INVALID = "LIFECYCLE_TRANSITION_INVALID"
TERMINAL_SIGNAL_REOPEN_FORBIDDEN = "TERMINAL_SIGNAL_REOPEN_FORBIDDEN"
TRANSITION_ID_COLLISION = "TRANSITION_ID_COLLISION"
EXPECTED_REVISION_MISMATCH = "EXPECTED_REVISION_MISMATCH"
STYLE_CAPACITY_FULL = "STYLE_CAPACITY_FULL"
TOTAL_CAPACITY_FULL = "TOTAL_CAPACITY_FULL"
PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED = (
    "PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED"
)
LOCK_ACQUISITION_FAILED = "LOCK_ACQUISITION_FAILED"
ATOMIC_WRITE_FAILED = "ATOMIC_WRITE_FAILED"

IDENTITY_IMMUTABLE = "IDENTITY_IMMUTABLE"
TIMESTAMP_INVALID = "TIMESTAMP_INVALID"
TERMINAL_REASON_INVALID = "TERMINAL_REASON_INVALID"
TRANSACTION_ID_INVALID = "TRANSACTION_ID_INVALID"

_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LOCK_ATTEMPTS = 25
_LOCK_DELAY_SECONDS = 0.01


class ActiveSignalLedgerError(ValueError):
    """A stable, sanitized rejection suitable for caller-visible metadata."""

    def __init__(self, reason_code: str, public_message: str | None = None):
        self.reason_code = reason_code
        self.public_message = public_message or "Active signal ledger request rejected"
        super().__init__(self.public_message)


def _reject(code: str, message: str | None = None) -> None:
    raise ActiveSignalLedgerError(code, message)


def _identifier(value: Any, code: str = SIGNAL_ID_INVALID) -> str:
    if not isinstance(value, str) or not value.strip():
        _reject(code)
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        _reject(TIMESTAMP_INVALID)
    return value


def _hash(value: Any) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        _reject(LEDGER_CORRUPT)
    return value


def _revision(value: Any) -> int:
    if type(value) is not int or value < 0:
        _reject(LEDGER_CORRUPT)
    return value


def _capacity_policy() -> dict[str, Any]:
    return {
        "scope": CAPACITY_SCOPE,
        "by_mode": dict(CAPACITY_BY_MODE),
        "total_capacity": TOTAL_CAPACITY,
        "occupying_states": list(OCCUPYING_STATES),
        "terminal_states": list(TERMINAL_STATES),
    }


def create_empty_ledger(created_at: str) -> dict[str, Any]:
    """Return a caller-timestamped, canonical initial ledger document."""
    _timestamp(created_at)
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "ledger_revision": 0,
        "created_at": created_at,
        "updated_at": created_at,
        "capacity_policy": _capacity_policy(),
        "signals": {},
        "transitions": {},
        "publication_transactions": {},
    }


def _canonical_json(document: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                document,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError, OverflowError):
        _reject(LEDGER_CORRUPT)
    raise AssertionError("unreachable")


def _record_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(record))


def _validate_signal(signal_id: str, record: Any) -> None:
    _identifier(signal_id)
    required = {
        "signal_id", "delivery_id", "mode", "symbol", "state", "published_at",
        "entry_at", "terminal_at", "terminal_reason", "last_transition_id",
        "source_payload_hash", "publication_payload_hash", "created_at", "updated_at",
    }
    if not isinstance(record, dict) or set(record) != required:
        _reject(LEDGER_CORRUPT)
    if record["signal_id"] != signal_id:
        _reject(LEDGER_CORRUPT)
    _identifier(record["delivery_id"], PUBLICATION_ID_COLLISION)
    if record["mode"] not in STYLES:
        _reject(STYLE_INVALID)
    _identifier(record["symbol"])
    if record["state"] not in LIFECYCLE_STATES:
        _reject(LEDGER_CORRUPT)
    _timestamp(record["published_at"])
    _hash(record["source_payload_hash"])
    _hash(record["publication_payload_hash"])
    _timestamp(record["created_at"])
    _timestamp(record["updated_at"])
    _identifier(record["last_transition_id"], TRANSITION_ID_COLLISION)
    terminal = record["state"] in TERMINAL_STATES
    if record["state"] == PUBLISHED_PENDING_ENTRY:
        if any(record[key] is not None for key in ("entry_at", "terminal_at", "terminal_reason")):
            _reject(LEDGER_CORRUPT)
    elif record["state"] == ENTRY_ACTIVE:
        _timestamp(record["entry_at"])
        if record["terminal_at"] is not None or record["terminal_reason"] is not None:
            _reject(LEDGER_CORRUPT)
    elif terminal:
        if record["entry_at"] is not None:
            _timestamp(record["entry_at"])
        _timestamp(record["terminal_at"])
        _identifier(record["terminal_reason"], TERMINAL_REASON_INVALID)


def _validate_transition(transition_id: str, transition: Any, signals: Mapping[str, Any]) -> None:
    _identifier(transition_id, TRANSITION_ID_COLLISION)
    required = {
        "transition_id", "operation", "signal_id", "from_state", "to_state",
        "occurred_at", "terminal_reason", "ledger_revision",
    }
    if not isinstance(transition, dict) or set(transition) != required:
        _reject(LEDGER_CORRUPT)
    if transition["transition_id"] != transition_id:
        _reject(LEDGER_CORRUPT)
    if transition["operation"] not in {"RESERVE", "ENTRY", "TERMINAL"}:
        _reject(LEDGER_CORRUPT)
    _identifier(transition["signal_id"])
    if transition["signal_id"] not in signals:
        _reject(LEDGER_CORRUPT)
    if transition["from_state"] is not None and transition["from_state"] not in LIFECYCLE_STATES:
        _reject(LEDGER_CORRUPT)
    if transition["to_state"] not in LIFECYCLE_STATES:
        _reject(LEDGER_CORRUPT)
    _timestamp(transition["occurred_at"])
    if transition["terminal_reason"] is not None:
        _identifier(transition["terminal_reason"], TERMINAL_REASON_INVALID)
    _revision(transition["ledger_revision"])


def _validate_transaction(transaction_id: str, transaction: Any, signals: Mapping[str, Any]) -> None:
    _identifier(transaction_id, TRANSACTION_ID_INVALID)
    required = {
        "transaction_id", "signal_id", "delivery_id", "mode", "symbol",
        "published_at", "source_payload_hash", "publication_payload_hash",
        "reservation_transition_id", "state", "created_at", "updated_at",
        "aborted_at", "abort_reason",
    }
    if not isinstance(transaction, dict) or set(transaction) != required:
        _reject(LEDGER_CORRUPT)
    if transaction["transaction_id"] != transaction_id:
        _reject(LEDGER_CORRUPT)
    _identifier(transaction["signal_id"])
    _identifier(transaction["delivery_id"], PUBLICATION_ID_COLLISION)
    if transaction["mode"] not in STYLES:
        _reject(STYLE_INVALID)
    _identifier(transaction["symbol"])
    _timestamp(transaction["published_at"])
    _hash(transaction["source_payload_hash"])
    _hash(transaction["publication_payload_hash"])
    _identifier(transaction["reservation_transition_id"], TRANSITION_ID_COLLISION)
    if transaction["state"] not in PUBLICATION_TRANSACTION_STATES:
        _reject(LEDGER_CORRUPT)
    _timestamp(transaction["created_at"])
    _timestamp(transaction["updated_at"])
    if transaction["state"] == ABORTED:
        _timestamp(transaction["aborted_at"])
        _identifier(transaction["abort_reason"], TERMINAL_REASON_INVALID)
    elif transaction["aborted_at"] is not None or transaction["abort_reason"] is not None:
        _reject(LEDGER_CORRUPT)
    if transaction["state"] == OCCUPANCY_COMMITTED:
        record = signals.get(transaction["signal_id"])
        if record is None or any(
            record[key] != transaction[key]
            for key in ("delivery_id", "mode", "symbol", "published_at", "source_payload_hash", "publication_payload_hash")
        ):
            _reject(LEDGER_CORRUPT)


def validate_ledger(ledger: Any) -> dict[str, Any]:
    """Validate and return a defensive copy of a persisted ledger document."""
    required = {
        "schema_name", "schema_version", "ledger_revision", "created_at", "updated_at",
        "capacity_policy", "signals", "transitions", "publication_transactions",
    }
    if not isinstance(ledger, dict) or set(ledger) != required:
        _reject(LEDGER_CORRUPT)
    if ledger["schema_name"] != SCHEMA_NAME or ledger["schema_version"] != SCHEMA_VERSION:
        _reject(LEDGER_SCHEMA_UNSUPPORTED)
    _revision(ledger["ledger_revision"])
    _timestamp(ledger["created_at"])
    _timestamp(ledger["updated_at"])
    if ledger["capacity_policy"] != _capacity_policy():
        _reject(LEDGER_CORRUPT)
    signals = ledger["signals"]
    transitions = ledger["transitions"]
    transactions = ledger["publication_transactions"]
    if not all(isinstance(value, dict) for value in (signals, transitions, transactions)):
        _reject(LEDGER_CORRUPT)
    delivery_ids: set[str] = set()
    for signal_id, record in signals.items():
        _validate_signal(signal_id, record)
        if record["delivery_id"] in delivery_ids:
            _reject(PUBLICATION_ID_COLLISION)
        delivery_ids.add(record["delivery_id"])
    for transition_id, transition in transitions.items():
        _validate_transition(transition_id, transition, signals)
    transaction_ids: set[str] = set()
    for transaction_id, transaction in transactions.items():
        _validate_transaction(transaction_id, transaction, signals)
        if transaction_id in transaction_ids:
            _reject(LEDGER_CORRUPT)
        transaction_ids.add(transaction_id)
    _ensure_capacity(ledger)
    return _record_payload(ledger)


def _capacity(ledger: Mapping[str, Any]) -> dict[str, int]:
    counts = {mode: 0 for mode in STYLES}
    for record in ledger["signals"].values():
        if record["state"] in OCCUPYING_STATES:
            counts[record["mode"]] += 1
    counts["TOTAL"] = sum(counts.values())
    return counts


def _ensure_capacity(ledger: Mapping[str, Any]) -> None:
    counts = _capacity(ledger)
    if counts["TOTAL"] > TOTAL_CAPACITY:
        _reject(TOTAL_CAPACITY_FULL)
    if any(counts[mode] > CAPACITY_BY_MODE[mode] for mode in STYLES):
        _reject(STYLE_CAPACITY_FULL)


def inspect_capacity(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Return derived capacity only; this operation never writes a ledger."""
    document = validate_ledger(ledger)
    active = _capacity(document)
    return {
        "scope": CAPACITY_SCOPE,
        "active_by_mode": {mode: active[mode] for mode in STYLES},
        "remaining_by_mode": {mode: CAPACITY_BY_MODE[mode] - active[mode] for mode in STYLES},
        "total_active": active["TOTAL"],
        "total_remaining": TOTAL_CAPACITY - active["TOTAL"],
    }


def _path(value: str | Path) -> Path:
    try:
        path = Path(value)
    except TypeError:
        _reject(LEDGER_CORRUPT)
    if not str(path):
        _reject(LEDGER_CORRUPT)
    return path


def _read_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        _reject(LEDGER_NOT_FOUND)
    try:
        raw = path.read_text(encoding="utf-8")
        return validate_ledger(json.loads(raw))
    except ActiveSignalLedgerError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _reject(LEDGER_CORRUPT)
    raise AssertionError("unreachable")


def load_ledger(ledger_path: str | Path) -> dict[str, Any]:
    """Load and fully validate a ledger; missing/corrupt state fails closed."""
    return _read_ledger(_path(ledger_path))


def _atomic_write(path: Path, ledger: Mapping[str, Any]) -> None:
    payload = _canonical_json(validate_ledger(dict(ledger)))
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    except (OSError, ValueError):
        _reject(ATOMIC_WRITE_FAILED)
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


@contextmanager
def _ledger_lock(path: Path) -> Iterator[None]:
    """Use a sibling lock with bounded acquisition and no age-based deletion."""
    lock_path = path.with_name(path.name + ".lock")
    descriptor: int | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(_LOCK_ATTEMPTS):
            try:
                descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.write(descriptor, b"active-signal-ledger-v1\n")
                os.fsync(descriptor)
                break
            except FileExistsError:
                time.sleep(_LOCK_DELAY_SECONDS)
            except OSError:
                _reject(LOCK_ACQUISITION_FAILED)
        if descriptor is None:
            _reject(LOCK_ACQUISITION_FAILED)
        yield
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass


def initialize_ledger(ledger_path: str | Path, *, created_at: str) -> dict[str, Any]:
    """Explicitly create a ledger. Existing files are never overwritten."""
    path = _path(ledger_path)
    with _ledger_lock(path):
        if path.exists():
            _reject(SIGNAL_ALREADY_EXISTS)
        ledger = create_empty_ledger(created_at)
        _atomic_write(path, ledger)
        return ledger


def _expected_revision(ledger: Mapping[str, Any], expected_revision: int) -> None:
    if type(expected_revision) is not int or expected_revision != ledger["ledger_revision"]:
        _reject(EXPECTED_REVISION_MISMATCH)


def _pending_conflict(ledger: Mapping[str, Any], signal_id: str, delivery_id: str) -> None:
    for transaction in ledger["publication_transactions"].values():
        if transaction["state"] == PREPARED and (
            transaction["signal_id"] != signal_id or transaction["delivery_id"] != delivery_id
        ):
            _reject(PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED)


def _transaction_payload(
    *, transaction_id: str, transition_id: str, signal_id: str, delivery_id: str,
    mode: str, symbol: str, published_at: str, source_payload_hash: str,
    publication_payload_hash: str, updated_at: str,
) -> dict[str, Any]:
    _identifier(transaction_id, TRANSACTION_ID_INVALID)
    _identifier(transition_id, TRANSITION_ID_COLLISION)
    _identifier(signal_id)
    _identifier(delivery_id, PUBLICATION_ID_COLLISION)
    if mode not in STYLES:
        _reject(STYLE_INVALID)
    _identifier(symbol)
    _timestamp(published_at)
    _timestamp(updated_at)
    _hash(source_payload_hash)
    _hash(publication_payload_hash)
    return {
        "transaction_id": transaction_id,
        "signal_id": signal_id,
        "delivery_id": delivery_id,
        "mode": mode,
        "symbol": symbol,
        "published_at": published_at,
        "source_payload_hash": source_payload_hash,
        "publication_payload_hash": publication_payload_hash,
        "reservation_transition_id": transition_id,
        "state": PREPARED,
        "created_at": updated_at,
        "updated_at": updated_at,
        "aborted_at": None,
        "abort_reason": None,
    }


def _reservation_equivalent(transaction: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    return all(transaction[key] == candidate[key] for key in candidate if key not in {"state", "created_at", "updated_at", "aborted_at", "abort_reason"})


def _commit_occupancy(ledger: dict[str, Any], transaction: dict[str, Any], *, updated_at: str) -> None:
    # Publication creates lifecycle evidence, not owner entry occupancy.
    record = {
        "signal_id": transaction["signal_id"],
        "delivery_id": transaction["delivery_id"],
        "mode": transaction["mode"],
        "symbol": transaction["symbol"],
        "state": PUBLISHED_PENDING_ENTRY,
        "published_at": transaction["published_at"],
        "entry_at": None,
        "terminal_at": None,
        "terminal_reason": None,
        "last_transition_id": transaction["reservation_transition_id"],
        "source_payload_hash": transaction["source_payload_hash"],
        "publication_payload_hash": transaction["publication_payload_hash"],
        "created_at": updated_at,
        "updated_at": updated_at,
    }
    ledger["signals"][record["signal_id"]] = record
    ledger["transitions"][transaction["reservation_transition_id"]] = {
        "transition_id": transaction["reservation_transition_id"],
        "operation": "RESERVE",
        "signal_id": record["signal_id"],
        "from_state": None,
        "to_state": PUBLISHED_PENDING_ENTRY,
        "occurred_at": updated_at,
        "terminal_reason": None,
        "ledger_revision": ledger["ledger_revision"] + 1,
    }
    transaction["state"] = OCCUPANCY_COMMITTED
    transaction["updated_at"] = updated_at


def _persist_mutation(path: Path, ledger: dict[str, Any], updated_at: str) -> dict[str, Any]:
    _timestamp(updated_at)
    ledger["ledger_revision"] += 1
    ledger["updated_at"] = updated_at
    document = validate_ledger(ledger)
    _atomic_write(path, document)
    return document


def reserve_published_signal(
    ledger_path: str | Path,
    *,
    expected_revision: int,
    transaction_id: str,
    transition_id: str,
    signal_id: str,
    delivery_id: str,
    mode: str,
    symbol: str,
    published_at: str,
    source_payload_hash: str,
    publication_payload_hash: str,
    updated_at: str,
    publication_intent_durable: bool = True,
) -> dict[str, Any]:
    """Durably register publication without consuming an active-entry slot."""
    if type(publication_intent_durable) is not bool:
        _reject(PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED)
    path = _path(ledger_path)
    candidate = _transaction_payload(
        transaction_id=transaction_id, transition_id=transition_id, signal_id=signal_id,
        delivery_id=delivery_id, mode=mode, symbol=symbol, published_at=published_at,
        source_payload_hash=source_payload_hash, publication_payload_hash=publication_payload_hash,
        updated_at=updated_at,
    )
    with _ledger_lock(path):
        ledger = _read_ledger(path)
        existing = ledger["publication_transactions"].get(transaction_id)
        if existing is not None:
            if not _reservation_equivalent(existing, candidate):
                _reject(TRANSITION_ID_COLLISION)
            if existing["state"] == PREPARED and publication_intent_durable:
                _commit_occupancy(ledger, existing, updated_at=updated_at)
                return _persist_mutation(path, ledger, updated_at)
            return ledger
        _expected_revision(ledger, expected_revision)
        _pending_conflict(ledger, signal_id, delivery_id)
        existing_signal = ledger["signals"].get(signal_id)
        if existing_signal is not None:
            if existing_signal["mode"] != mode:
                _reject(STYLE_IMMUTABLE)
            if any(
                existing_signal[field] != value
                for field, value in {
                    "symbol": symbol,
                    "source_payload_hash": source_payload_hash,
                    "publication_payload_hash": publication_payload_hash,
                }.items()
            ):
                _reject(IDENTITY_IMMUTABLE)
            _reject(SIGNAL_ALREADY_EXISTS)
        if any(record["delivery_id"] == delivery_id for record in ledger["signals"].values()):
            _reject(PUBLICATION_ID_COLLISION)
        if any(
            transaction["signal_id"] == signal_id or transaction["delivery_id"] == delivery_id
            for transaction in ledger["publication_transactions"].values()
        ):
            _reject(SIGNAL_ID_COLLISION)
        ledger["publication_transactions"][transaction_id] = candidate
        if publication_intent_durable:
            _commit_occupancy(ledger, candidate, updated_at=updated_at)
        return _persist_mutation(path, ledger, updated_at)


def _transition_payload(
    *, operation: str, transition_id: str, signal_id: str, from_state: str,
    to_state: str, occurred_at: str, terminal_reason: str | None,
    ledger_revision: int,
) -> dict[str, Any]:
    _identifier(transition_id, TRANSITION_ID_COLLISION)
    _identifier(signal_id)
    _timestamp(occurred_at)
    if terminal_reason is not None:
        _identifier(terminal_reason, TERMINAL_REASON_INVALID)
    return {
        "transition_id": transition_id,
        "operation": operation,
        "signal_id": signal_id,
        "from_state": from_state,
        "to_state": to_state,
        "occurred_at": occurred_at,
        "terminal_reason": terminal_reason,
        "ledger_revision": ledger_revision,
    }


def _existing_transition(ledger: Mapping[str, Any], transition_id: str, candidate: Mapping[str, Any]) -> bool:
    existing = ledger["transitions"].get(transition_id)
    if existing is None:
        return False
    # The stored revision is historical.  It must not make a byte-for-byte
    # replay look different merely because later ledger mutations occurred.
    semantic_existing = {key: value for key, value in existing.items() if key != "ledger_revision"}
    semantic_candidate = {key: value for key, value in candidate.items() if key != "ledger_revision"}
    if semantic_existing != semantic_candidate:
        _reject(TRANSITION_ID_COLLISION)
    return True


def mark_entry_active(
    ledger_path: str | Path, *, expected_revision: int, transition_id: str,
    signal_id: str, entry_at: str, updated_at: str,
    require_current_revision: bool = False,
) -> dict[str, Any]:
    path = _path(ledger_path)
    _timestamp(entry_at)
    _timestamp(updated_at)
    if type(require_current_revision) is not bool:
        _reject(EXPECTED_REVISION_MISMATCH)
    with _ledger_lock(path):
        ledger = _read_ledger(path)
        _expected_revision(ledger, expected_revision)
        record = ledger["signals"].get(signal_id)
        if record is None:
            _reject(SIGNAL_ID_INVALID)
        candidate = _transition_payload(
            operation="ENTRY", transition_id=transition_id, signal_id=signal_id,
            from_state=PUBLISHED_PENDING_ENTRY, to_state=ENTRY_ACTIVE,
            occurred_at=entry_at, terminal_reason=None,
            ledger_revision=ledger["ledger_revision"] + 1,
        )
        if _existing_transition(ledger, transition_id, candidate):
            return ledger
        if record["state"] in TERMINAL_STATES:
            _reject(TERMINAL_SIGNAL_REOPEN_FORBIDDEN)
        if record["state"] != PUBLISHED_PENDING_ENTRY:
            _reject(LIFECYCLE_TRANSITION_INVALID)
        capacity = _capacity(ledger)
        if capacity[record["mode"]] >= CAPACITY_BY_MODE[record["mode"]]:
            _reject(STYLE_CAPACITY_FULL)
        if capacity["TOTAL"] >= TOTAL_CAPACITY:
            _reject(TOTAL_CAPACITY_FULL)
        record["state"] = ENTRY_ACTIVE
        record["entry_at"] = entry_at
        record["last_transition_id"] = transition_id
        record["updated_at"] = updated_at
        ledger["transitions"][transition_id] = candidate
        return _persist_mutation(path, ledger, updated_at)


def transition_terminal(
    ledger_path: str | Path, *, expected_revision: int, transition_id: str,
    signal_id: str, terminal_state: str, terminal_at: str, terminal_reason: str,
    updated_at: str, require_current_revision: bool = False,
) -> dict[str, Any]:
    if terminal_state not in TERMINAL_STATES:
        _reject(LIFECYCLE_TRANSITION_INVALID)
    _timestamp(terminal_at)
    _timestamp(updated_at)
    _identifier(terminal_reason, TERMINAL_REASON_INVALID)
    if type(require_current_revision) is not bool:
        _reject(EXPECTED_REVISION_MISMATCH)
    path = _path(ledger_path)
    with _ledger_lock(path):
        ledger = _read_ledger(path)
        _expected_revision(ledger, expected_revision)
        record = ledger["signals"].get(signal_id)
        if record is None:
            _reject(SIGNAL_ID_INVALID)
        if record["state"] in TERMINAL_STATES:
            existing = ledger["transitions"].get(transition_id)
            if existing is not None:
                equivalent_transition = (
                    existing["operation"] == "TERMINAL"
                    and existing["signal_id"] == signal_id
                    and existing["to_state"] == terminal_state
                    and existing["occurred_at"] == terminal_at
                    and existing["terminal_reason"] == terminal_reason
                )
                if equivalent_transition:
                    return ledger
                _reject(TRANSITION_ID_COLLISION)
            equivalent = (
                record["state"] == terminal_state
                and record["terminal_at"] == terminal_at
                and record["terminal_reason"] == terminal_reason
            )
            if equivalent:
                return ledger
            _reject(TERMINAL_SIGNAL_REOPEN_FORBIDDEN)
        allowed = record["state"] == PUBLISHED_PENDING_ENTRY or (
            record["state"] == ENTRY_ACTIVE and terminal_state != EXPIRED
        )
        if not allowed:
            _reject(LIFECYCLE_TRANSITION_INVALID)
        candidate = _transition_payload(
            operation="TERMINAL", transition_id=transition_id, signal_id=signal_id,
            from_state=record["state"], to_state=terminal_state, occurred_at=terminal_at,
            terminal_reason=terminal_reason, ledger_revision=ledger["ledger_revision"] + 1,
        )
        if _existing_transition(ledger, transition_id, candidate):
            return ledger
        record["state"] = terminal_state
        record["terminal_at"] = terminal_at
        record["terminal_reason"] = terminal_reason
        record["last_transition_id"] = transition_id
        record["updated_at"] = updated_at
        ledger["transitions"][transition_id] = candidate
        return _persist_mutation(path, ledger, updated_at)


def reconcile_publication_state(
    ledger_path: str | Path, *, expected_revision: int, transaction_id: str,
    publication_artifact_exists: bool, artifact_signal_id: str | None,
    artifact_delivery_id: str | None, artifact_publication_payload_hash: str | None,
    reconciled_at: str, abort_reason: str = "PUBLICATION_NOT_CONFIRMED",
) -> dict[str, Any]:
    """Commit or abort a PREPARED transaction from caller-supplied artifact evidence."""
    if type(publication_artifact_exists) is not bool:
        _reject(PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED)
    _timestamp(reconciled_at)
    _identifier(transaction_id, TRANSACTION_ID_INVALID)
    path = _path(ledger_path)
    with _ledger_lock(path):
        ledger = _read_ledger(path)
        _expected_revision(ledger, expected_revision)
        transaction = ledger["publication_transactions"].get(transaction_id)
        if transaction is None:
            _reject(PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED)
        if transaction["state"] == OCCUPANCY_COMMITTED or transaction["state"] == ABORTED:
            return ledger
        if publication_artifact_exists:
            if (
                artifact_signal_id != transaction["signal_id"]
                or artifact_delivery_id != transaction["delivery_id"]
                or artifact_publication_payload_hash != transaction["publication_payload_hash"]
            ):
                _reject(PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED)
            _commit_occupancy(ledger, transaction, updated_at=reconciled_at)
        elif any(item is not None for item in (artifact_signal_id, artifact_delivery_id, artifact_publication_payload_hash)):
            _reject(PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED)
        else:
            _identifier(abort_reason, TERMINAL_REASON_INVALID)
            transaction["state"] = ABORTED
            transaction["updated_at"] = reconciled_at
            transaction["aborted_at"] = reconciled_at
            transaction["abort_reason"] = abort_reason
        return _persist_mutation(path, ledger, reconciled_at)
