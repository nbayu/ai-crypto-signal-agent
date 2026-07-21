"""Passive durable request ledger for style-capacity refill coordination."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping


SCHEMA = "style-refill-request-ledger"
SCHEMA_VERSION = 1

SWING = "SWING"
INTRADAY = "INTRADAY"
SCALP = "SCALP"
MODES = (SWING, INTRADAY, SCALP)

PENDING = "PENDING"
CLAIMED = "CLAIMED"
COMPLETED = "COMPLETED"
CANCELLED = "CANCELLED"
REQUEST_STATUSES = (PENDING, CLAIMED, COMPLETED, CANCELLED)

DISPATCHED = "DISPATCHED"
STYLE_FULL = "STYLE_FULL"
CANCELLED_OUTCOME = "CANCELLED"
COMPLETION_OUTCOMES = (DISPATCHED, STYLE_FULL, CANCELLED_OUTCOME)

TERMINAL_STATES = (
    "CLOSED_PROFIT",
    "CLOSED_STOP_LOSS",
    "CANCELLED",
    "EXPIRED",
    "INVALIDATED",
)

INVALID_LEDGER = "INVALID_LEDGER"
INVALID_REQUEST = "INVALID_REQUEST"
INVALID_MODE = "INVALID_MODE"
INVALID_TERMINAL_STATE = "INVALID_TERMINAL_STATE"
REQUEST_ID_COLLISION = "REQUEST_ID_COLLISION"
REQUEST_ALREADY_EXISTS = "REQUEST_ALREADY_EXISTS"
REVISION_CONFLICT = "REVISION_CONFLICT"
REQUEST_NOT_PENDING = "REQUEST_NOT_PENDING"
REQUEST_NOT_CLAIMED = "REQUEST_NOT_CLAIMED"
CLAIM_TOKEN_CONFLICT = "CLAIM_TOKEN_CONFLICT"
INVALID_CAPACITY_SNAPSHOT = "INVALID_CAPACITY_SNAPSHOT"
LOCK_UNAVAILABLE = "LOCK_UNAVAILABLE"
PERSISTENCE_FAILURE = "PERSISTENCE_FAILURE"

_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_LOCK_ATTEMPTS = 25
_LOCK_DELAY_SECONDS = 0.01


class StyleRefillRequestLedgerError(ValueError):
    """Stable sanitized failure; no raw storage or caller material is exposed."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__("Style refill request rejected")


def _reject(reason_code: str) -> None:
    raise StyleRefillRequestLedgerError(reason_code)


def _nonempty(value: Any, code: str = INVALID_REQUEST) -> str:
    if not isinstance(value, str) or not value.strip():
        _reject(code)
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        _reject(INVALID_REQUEST)
    return value


def _revision(value: Any) -> int:
    if type(value) is not int or value < 0:
        _reject(INVALID_LEDGER)
    return value


def _mode(value: Any) -> str:
    if value not in MODES:
        _reject(INVALID_MODE)
    return value


def _terminal_state(value: Any) -> str:
    if value not in TERMINAL_STATES:
        _reject(INVALID_TERMINAL_STATE)
    return value


def _identity_payload(
    *, terminal_transition_id: str, signal_id: str, mode: str, terminal_state: str
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "terminal_transition_id": _nonempty(terminal_transition_id),
        "signal_id": _nonempty(signal_id),
        "mode": _mode(mode),
        "terminal_state": _terminal_state(terminal_state),
    }


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        _reject(INVALID_REQUEST)
    raise AssertionError("unreachable")


def derive_refill_request_id(
    *, terminal_transition_id: str, signal_id: str, mode: str, terminal_state: str
) -> str:
    """Derive the canonical, deterministic identity for one released slot."""
    return hashlib.sha256(
        _canonical_bytes(
            _identity_payload(
                terminal_transition_id=terminal_transition_id,
                signal_id=signal_id,
                mode=mode,
                terminal_state=terminal_state,
            )
        )
    ).hexdigest()


def create_empty_refill_ledger(*, created_at: str) -> dict[str, Any]:
    _timestamp(created_at)
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "ledger_revision": 0,
        "created_at": created_at,
        "updated_at": created_at,
        "requests": {},
        "source_transitions": {},
    }


def _request_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "terminal_transition_id": _nonempty(record["terminal_transition_id"]),
        "signal_id": _nonempty(record["signal_id"]),
        "mode": _mode(record["mode"]),
        "terminal_state": _terminal_state(record["terminal_state"]),
    }


def _validate_request(request_id: str, record: Any) -> None:
    fields = {
        "refill_request_id", "terminal_transition_id", "signal_id", "mode",
        "terminal_state", "status", "completion_outcome", "created_at",
        "updated_at", "claimed_at", "completed_at", "claim_token",
        "attempt_count", "source_ledger_revision",
    }
    if not isinstance(record, dict) or set(record) != fields:
        _reject(INVALID_LEDGER)
    if record["refill_request_id"] != request_id or not _DIGEST.fullmatch(request_id):
        _reject(INVALID_LEDGER)
    expected_id = derive_refill_request_id(**_request_identity(record))
    if expected_id != request_id:
        _reject(INVALID_LEDGER)
    if record["status"] not in REQUEST_STATUSES:
        _reject(INVALID_LEDGER)
    _timestamp(record["created_at"])
    _timestamp(record["updated_at"])
    if type(record["attempt_count"]) is not int or record["attempt_count"] < 0:
        _reject(INVALID_LEDGER)
    if type(record["source_ledger_revision"]) is not int or record["source_ledger_revision"] < 0:
        _reject(INVALID_LEDGER)
    status = record["status"]
    if status == PENDING:
        if any(record[key] is not None for key in ("completion_outcome", "claimed_at", "completed_at", "claim_token")):
            _reject(INVALID_LEDGER)
    elif status == CLAIMED:
        if record["completion_outcome"] is not None or record["completed_at"] is not None:
            _reject(INVALID_LEDGER)
        _timestamp(record["claimed_at"])
        _nonempty(record["claim_token"])
    else:
        expected_outcome = CANCELLED_OUTCOME if status == CANCELLED else record["completion_outcome"]
        if expected_outcome not in COMPLETION_OUTCOMES:
            _reject(INVALID_LEDGER)
        if status == COMPLETED and record["completion_outcome"] not in (DISPATCHED, STYLE_FULL):
            _reject(INVALID_LEDGER)
        _timestamp(record["claimed_at"])
        _timestamp(record["completed_at"])
        _nonempty(record["claim_token"])


def _validate_transition_source(transition_id: str, source: Any, requests: Mapping[str, Any]) -> None:
    fields = {
        "terminal_transition_id", "signal_id", "mode", "terminal_state",
        "refill_request_id", "source_ledger_revision", "timestamp",
    }
    if not isinstance(source, dict) or set(source) != fields:
        _reject(INVALID_LEDGER)
    if source["terminal_transition_id"] != transition_id:
        _reject(INVALID_LEDGER)
    identity = {
        "terminal_transition_id": _nonempty(transition_id),
        "signal_id": _nonempty(source["signal_id"]),
        "mode": _mode(source["mode"]),
        "terminal_state": _terminal_state(source["terminal_state"]),
    }
    request_id = derive_refill_request_id(**identity)
    if source["refill_request_id"] != request_id or request_id not in requests:
        _reject(INVALID_LEDGER)
    if type(source["source_ledger_revision"]) is not int or source["source_ledger_revision"] < 0:
        _reject(INVALID_LEDGER)
    _timestamp(source["timestamp"])


def validate_refill_ledger(ledger: Any) -> dict[str, Any]:
    fields = {
        "schema", "schema_version", "ledger_revision", "created_at", "updated_at",
        "requests", "source_transitions",
    }
    if not isinstance(ledger, dict) or set(ledger) != fields:
        _reject(INVALID_LEDGER)
    if ledger["schema"] != SCHEMA or ledger["schema_version"] != SCHEMA_VERSION:
        _reject(INVALID_LEDGER)
    _revision(ledger["ledger_revision"])
    _timestamp(ledger["created_at"])
    _timestamp(ledger["updated_at"])
    if not isinstance(ledger["requests"], dict) or not isinstance(ledger["source_transitions"], dict):
        _reject(INVALID_LEDGER)
    for request_id, record in ledger["requests"].items():
        _validate_request(request_id, record)
    for transition_id, source in ledger["source_transitions"].items():
        _validate_transition_source(transition_id, source, ledger["requests"])
    return copy.deepcopy(ledger)


def _path(value: str | Path) -> Path:
    try:
        result = Path(value)
    except TypeError:
        _reject(INVALID_REQUEST)
    if not str(result):
        _reject(INVALID_REQUEST)
    return result


def _read_or_empty(path: Path, *, created_at: str | None) -> dict[str, Any]:
    if not path.exists():
        if created_at is None:
            _reject(INVALID_REQUEST)
        return create_empty_refill_ledger(created_at=created_at)
    try:
        return validate_refill_ledger(json.loads(path.read_text(encoding="utf-8")))
    except StyleRefillRequestLedgerError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _reject(INVALID_LEDGER)
    raise AssertionError("unreachable")


def load_refill_ledger(ledger_path: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Load validated state, or return a caller-timestamped empty document."""
    return _read_or_empty(_path(ledger_path), created_at=created_at)


def _write_atomic(path: Path, ledger: Mapping[str, Any]) -> None:
    payload = _canonical_bytes(validate_refill_ledger(dict(ledger))) + b"\n"
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    except (OSError, ValueError):
        _reject(PERSISTENCE_FAILURE)
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
def _lock(path: Path) -> Iterator[None]:
    lock_path = path.with_name(path.name + ".lock")
    descriptor: int | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(_LOCK_ATTEMPTS):
            try:
                descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.write(descriptor, b"style-refill-request-ledger-v1\n")
                os.fsync(descriptor)
                break
            except FileExistsError:
                time.sleep(_LOCK_DELAY_SECONDS)
            except OSError:
                _reject(LOCK_UNAVAILABLE)
        if descriptor is None:
            _reject(LOCK_UNAVAILABLE)
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


def _persist(path: Path, ledger: dict[str, Any], *, timestamp: str) -> dict[str, Any]:
    _timestamp(timestamp)
    ledger["ledger_revision"] += 1
    ledger["updated_at"] = timestamp
    document = validate_refill_ledger(ledger)
    _write_atomic(path, document)
    return document


def _request_record(
    *, request_id: str, terminal_transition_id: str, signal_id: str, mode: str,
    terminal_state: str, source_ledger_revision: int, timestamp: str,
) -> dict[str, Any]:
    if type(source_ledger_revision) is not int or source_ledger_revision < 0:
        _reject(INVALID_REQUEST)
    _timestamp(timestamp)
    return {
        "refill_request_id": request_id,
        "terminal_transition_id": terminal_transition_id,
        "signal_id": signal_id,
        "mode": mode,
        "terminal_state": terminal_state,
        "status": PENDING,
        "completion_outcome": None,
        "created_at": timestamp,
        "updated_at": timestamp,
        "claimed_at": None,
        "completed_at": None,
        "claim_token": None,
        "attempt_count": 0,
        "source_ledger_revision": source_ledger_revision,
    }


def reconcile_terminal_transition(
    ledger_path: str | Path,
    *,
    terminal_transition_id: str,
    signal_id: str,
    mode: str,
    terminal_state: str,
    source_ledger_revision: int,
    timestamp: str,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    """Record one passive PENDING request from a terminal transition."""
    identity = {
        "terminal_transition_id": _nonempty(terminal_transition_id),
        "signal_id": _nonempty(signal_id),
        "mode": _mode(mode),
        "terminal_state": _terminal_state(terminal_state),
    }
    request_id = derive_refill_request_id(**identity)
    _timestamp(timestamp)
    path = _path(ledger_path)
    with _lock(path):
        ledger = _read_or_empty(path, created_at=timestamp)
        if expected_revision is not None and expected_revision != ledger["ledger_revision"]:
            _reject(REVISION_CONFLICT)
        existing_source = ledger["source_transitions"].get(terminal_transition_id)
        if existing_source is not None:
            expected_source = {
                **identity,
                "refill_request_id": request_id,
                "source_ledger_revision": source_ledger_revision,
            }
            if any(existing_source[key] != value for key, value in expected_source.items()):
                _reject(REQUEST_ID_COLLISION)
            return ledger
        existing_request = ledger["requests"].get(request_id)
        if existing_request is not None:
            if _request_identity(existing_request) != identity:
                _reject(REQUEST_ID_COLLISION)
            _reject(REQUEST_ALREADY_EXISTS)
        record = _request_record(
            request_id=request_id,
            terminal_transition_id=terminal_transition_id,
            signal_id=signal_id,
            mode=mode,
            terminal_state=terminal_state,
            source_ledger_revision=source_ledger_revision,
            timestamp=timestamp,
        )
        ledger["requests"][request_id] = record
        ledger["source_transitions"][terminal_transition_id] = {
            **identity,
            "refill_request_id": request_id,
            "source_ledger_revision": source_ledger_revision,
            "timestamp": timestamp,
        }
        return _persist(path, ledger, timestamp=timestamp)


def inspect_refill_requests(ledger: Mapping[str, Any]) -> dict[str, Any]:
    document = validate_refill_ledger(ledger)
    counts = {status: {mode: 0 for mode in MODES} for status in REQUEST_STATUSES}
    ordered = []
    for request_id in sorted(document["requests"]):
        request = copy.deepcopy(document["requests"][request_id])
        counts[request["status"]][request["mode"]] += 1
        ordered.append(request)
    return {
        "total_requests": len(ordered),
        "pending_by_mode": counts[PENDING],
        "claimed_by_mode": counts[CLAIMED],
        "completed_by_mode": counts[COMPLETED],
        "cancelled_by_mode": counts[CANCELLED],
        "requests": tuple(ordered),
    }


def _remaining_capacity(snapshot: Any, mode: str) -> int:
    if not isinstance(snapshot, Mapping) or "remaining_by_mode" not in snapshot:
        _reject(INVALID_CAPACITY_SNAPSHOT)
    values = snapshot["remaining_by_mode"]
    if not isinstance(values, Mapping) or set(values) != set(MODES):
        _reject(INVALID_CAPACITY_SNAPSHOT)
    value = values.get(mode)
    if type(value) is not int or value < 0:
        _reject(INVALID_CAPACITY_SNAPSHOT)
    return value


def evaluate_dispatch_eligibility(
    ledger: Mapping[str, Any], *, refill_request_id: str, capacity_snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    document = validate_refill_ledger(ledger)
    request = document["requests"].get(refill_request_id)
    if request is None:
        _reject(INVALID_REQUEST)
    if request["status"] != PENDING:
        return {"status": "NOT_ELIGIBLE", "scan_units": 0, "mode": request["mode"]}
    remaining = _remaining_capacity(capacity_snapshot, request["mode"])
    if remaining == 0:
        return {"status": STYLE_FULL, "scan_units": 0, "mode": request["mode"]}
    return {"status": "ELIGIBLE_ONE_SCAN_UNIT", "scan_units": 1, "mode": request["mode"]}


def _expected(ledger: Mapping[str, Any], expected_revision: int) -> None:
    if type(expected_revision) is not int or expected_revision != ledger["ledger_revision"]:
        _reject(REVISION_CONFLICT)


def claim_refill_request(
    ledger_path: str | Path, *, refill_request_id: str, claim_token: str,
    timestamp: str, expected_revision: int,
) -> dict[str, Any]:
    _nonempty(refill_request_id)
    _nonempty(claim_token)
    _timestamp(timestamp)
    path = _path(ledger_path)
    with _lock(path):
        ledger = _read_or_empty(path, created_at=None)
        _expected(ledger, expected_revision)
        request = ledger["requests"].get(refill_request_id)
        if request is None:
            _reject(INVALID_REQUEST)
        if request["status"] == CLAIMED:
            if request["claim_token"] == claim_token:
                return ledger
            _reject(CLAIM_TOKEN_CONFLICT)
        if request["status"] != PENDING:
            _reject(REQUEST_NOT_PENDING)
        request["status"] = CLAIMED
        request["claim_token"] = claim_token
        request["claimed_at"] = timestamp
        request["updated_at"] = timestamp
        request["attempt_count"] += 1
        return _persist(path, ledger, timestamp=timestamp)


def complete_refill_request(
    ledger_path: str | Path, *, refill_request_id: str, claim_token: str,
    completion_outcome: str, timestamp: str, expected_revision: int,
) -> dict[str, Any]:
    _nonempty(refill_request_id)
    _nonempty(claim_token)
    _timestamp(timestamp)
    if completion_outcome not in COMPLETION_OUTCOMES:
        _reject(INVALID_REQUEST)
    path = _path(ledger_path)
    with _lock(path):
        ledger = _read_or_empty(path, created_at=None)
        _expected(ledger, expected_revision)
        request = ledger["requests"].get(refill_request_id)
        if request is None:
            _reject(INVALID_REQUEST)
        if request["status"] in (COMPLETED, CANCELLED):
            if request["claim_token"] == claim_token and request["completion_outcome"] == completion_outcome:
                return ledger
            _reject(CLAIM_TOKEN_CONFLICT)
        if request["status"] != CLAIMED:
            _reject(REQUEST_NOT_CLAIMED)
        if request["claim_token"] != claim_token:
            _reject(CLAIM_TOKEN_CONFLICT)
        request["status"] = CANCELLED if completion_outcome == CANCELLED_OUTCOME else COMPLETED
        request["completion_outcome"] = completion_outcome
        request["completed_at"] = timestamp
        request["updated_at"] = timestamp
        return _persist(path, ledger, timestamp=timestamp)


def recover_interrupted_claims(
    ledger_path: str | Path, *, recovery_before_timestamp: str, timestamp: str,
    expected_revision: int,
) -> dict[str, Any]:
    _timestamp(recovery_before_timestamp)
    _timestamp(timestamp)
    path = _path(ledger_path)
    with _lock(path):
        ledger = _read_or_empty(path, created_at=None)
        _expected(ledger, expected_revision)
        recovered = []
        for request_id in sorted(ledger["requests"]):
            request = ledger["requests"][request_id]
            if request["status"] == CLAIMED and request["claimed_at"] < recovery_before_timestamp:
                request["status"] = PENDING
                request["claim_token"] = None
                request["claimed_at"] = None
                request["updated_at"] = timestamp
                recovered.append(request_id)
        if not recovered:
            return {"ledger": ledger, "recovered_request_ids": ()}
        document = _persist(path, ledger, timestamp=timestamp)
        return {"ledger": document, "recovered_request_ids": tuple(recovered)}
