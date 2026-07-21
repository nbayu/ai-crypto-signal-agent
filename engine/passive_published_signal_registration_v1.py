"""Caller-driven durable registration of already completed publications."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as active


PUBLISHED_SIGNAL_REGISTERED = "PUBLISHED_SIGNAL_REGISTERED"
PUBLISHED_SIGNAL_REGISTRATION_REPLAYED = "PUBLISHED_SIGNAL_REGISTRATION_REPLAYED"
PUBLICATION_SUCCEEDED_REGISTRATION_PENDING = (
    "PUBLICATION_SUCCEEDED_REGISTRATION_PENDING"
)
REGISTRATION_ALREADY_PRESENT = "REGISTRATION_ALREADY_PRESENT"
INVALID_PUBLICATION_EVIDENCE = "INVALID_PUBLICATION_EVIDENCE"
SIGNAL_IDENTITY_CONFLICT = "SIGNAL_IDENTITY_CONFLICT"
TRANSACTION_IDENTITY_CONFLICT = "TRANSACTION_IDENTITY_CONFLICT"
RESERVATION_IDENTITY_CONFLICT = "RESERVATION_IDENTITY_CONFLICT"
ACTIVE_REVISION_CONFLICT = "ACTIVE_REVISION_CONFLICT"
ACTIVE_LEDGER_FAILURE = "ACTIVE_LEDGER_FAILURE"
NO_REGISTRATION = "NO_REGISTRATION"
FAIL_CLOSED = "FAIL_CLOSED"

ACTIVE_LOCK_UNAVAILABLE = "ACTIVE_LOCK_UNAVAILABLE"
ACTIVE_PERSISTENCE_FAILURE = "ACTIVE_PERSISTENCE_FAILURE"
ACTIVE_LEDGER_INVALID = "ACTIVE_LEDGER_INVALID"

_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DOMAIN = "passive-published-signal-registration-v1"
_EVIDENCE_FIELDS = (
    "signal_id",
    "delivery_id",
    "mode",
    "symbol",
    "published_at",
    "source_payload_hash",
    "publication_payload_hash",
)


@dataclass(frozen=True, slots=True)
class PassivePublishedSignalRegistrationResultV1:
    """Sanitized registration result with deterministic field order."""

    result: str
    signal_id: str | None
    reservation_transaction_id: str | None
    reservation_transition_id: str | None
    delivery_id: str | None
    mode: str | None
    symbol: str | None
    published_at: str | None
    publication_identity_hash: str | None
    signal_payload_hash: str | None
    source_payload_hash: str | None
    publication_payload_hash: str | None
    active_ledger_revision: int | None
    current_state: str | None
    publication_confirmed: bool
    registration_applied: bool
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
    timestamp: str | None,
    signal_id: str | None = None,
    reservation_transaction_id: str | None = None,
    reservation_transition_id: str | None = None,
    delivery_id: str | None = None,
    mode: str | None = None,
    symbol: str | None = None,
    published_at: str | None = None,
    publication_identity_hash: str | None = None,
    source_payload_hash: str | None = None,
    publication_payload_hash: str | None = None,
    active_ledger_revision: int | None = None,
    current_state: str | None = None,
    publication_confirmed: bool = False,
    registration_applied: bool = False,
    partial_success: bool = False,
    replay: bool = False,
    reason: str | None = None,
) -> PassivePublishedSignalRegistrationResultV1:
    return PassivePublishedSignalRegistrationResultV1(
        result=result,
        signal_id=signal_id,
        reservation_transaction_id=reservation_transaction_id,
        reservation_transition_id=reservation_transition_id,
        delivery_id=delivery_id,
        mode=mode,
        symbol=symbol,
        published_at=published_at,
        publication_identity_hash=publication_identity_hash,
        signal_payload_hash=source_payload_hash,
        source_payload_hash=source_payload_hash,
        publication_payload_hash=publication_payload_hash,
        active_ledger_revision=active_ledger_revision,
        current_state=current_state,
        publication_confirmed=publication_confirmed,
        registration_applied=registration_applied,
        partial_success=partial_success,
        replay=replay,
        reason=reason,
        timestamp=timestamp,
    )


def _nonempty(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise ValueError
    return value


def _hash(value: Any) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError
    return value


def _canonical_transaction_payload(context: Mapping[str, str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "domain": _DOMAIN,
        "signal_id": context["signal_id"],
        "delivery_id": context["delivery_id"],
        "mode": context["mode"],
        "symbol": context["symbol"],
        "published_at": context["published_at"],
        "source_payload_hash": context["source_payload_hash"],
        "publication_payload_hash": context["publication_payload_hash"],
    }


def _derive_reservation_transaction_id(
    *,
    signal_id: str,
    delivery_id: str,
    mode: str,
    symbol: str,
    published_at: str,
    source_payload_hash: str,
    publication_payload_hash: str,
) -> str:
    """Derive the deterministic Active Ledger transaction identity."""
    context = _validated_context(
        {
            "delivery_state": "DELIVERY_SUCCEEDED",
            "signal_id": signal_id,
            "delivery_id": delivery_id,
            "mode": mode,
            "published_at": published_at,
            "source_payload_hash": source_payload_hash,
            "publication_payload_hash": publication_payload_hash,
            "publication_payload": {
                "signal_id": signal_id,
                "mode": mode,
                "symbol": symbol,
            },
        }
    )
    return hashlib.sha256(
        json.dumps(
            _canonical_transaction_payload(context),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _validated_context(publication_evidence: Any) -> dict[str, str | None]:
    if not isinstance(publication_evidence, Mapping):
        raise ValueError
    evidence = dict(publication_evidence)
    if evidence.get("delivery_state") != "DELIVERY_SUCCEEDED":
        raise ValueError
    signal_id = _nonempty(evidence.get("signal_id"))
    delivery_id = _nonempty(evidence.get("delivery_id"))
    mode = evidence.get("mode")
    if mode not in active.STYLES:
        raise ValueError
    payload = evidence.get("publication_payload")
    if not isinstance(payload, Mapping):
        raise ValueError
    symbol = _nonempty(payload.get("symbol"))
    if "signal_id" in payload and payload["signal_id"] != signal_id:
        raise ValueError
    if "mode" in payload and payload["mode"] != mode:
        raise ValueError
    published_at = _timestamp(evidence.get("published_at"))
    source_payload_hash = _hash(evidence.get("source_payload_hash"))
    publication_payload_hash = _hash(evidence.get("publication_payload_hash"))
    content_hash = evidence.get("content_hash")
    if content_hash is not None:
        content_hash = _hash(content_hash)
    return {
        "signal_id": signal_id,
        "delivery_id": delivery_id,
        "mode": mode,
        "symbol": symbol,
        "published_at": published_at,
        "source_payload_hash": source_payload_hash,
        "publication_payload_hash": publication_payload_hash,
        "publication_identity_hash": content_hash,
    }


def _transaction_id(context: Mapping[str, str | None]) -> str:
    payload = _canonical_transaction_payload(context)  # type: ignore[arg-type]
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _common(
    context: Mapping[str, str | None], *, transaction_id: str, transition_id: str
) -> dict[str, Any]:
    return {
        "signal_id": context["signal_id"],
        "reservation_transaction_id": transaction_id,
        "reservation_transition_id": transition_id,
        "delivery_id": context["delivery_id"],
        "mode": context["mode"],
        "symbol": context["symbol"],
        "published_at": context["published_at"],
        "publication_identity_hash": context["publication_identity_hash"],
        "source_payload_hash": context["source_payload_hash"],
        "publication_payload_hash": context["publication_payload_hash"],
        "publication_confirmed": True,
    }


def _pending(
    context: Mapping[str, str | None],
    *,
    transaction_id: str,
    transition_id: str,
    timestamp: str,
    reason: str,
) -> PassivePublishedSignalRegistrationResultV1:
    return _result(
        PUBLICATION_SUCCEEDED_REGISTRATION_PENDING,
        timestamp=timestamp,
        partial_success=True,
        reason=reason,
        **_common(context, transaction_id=transaction_id, transition_id=transition_id),
    )


def _active_error(error: active.ActiveSignalLedgerError) -> tuple[str, str, bool]:
    if error.reason_code == active.EXPECTED_REVISION_MISMATCH:
        return ACTIVE_REVISION_CONFLICT, ACTIVE_REVISION_CONFLICT, False
    if error.reason_code in {
        active.IDENTITY_IMMUTABLE,
        active.STYLE_IMMUTABLE,
        active.SIGNAL_ALREADY_EXISTS,
        active.PUBLICATION_ID_COLLISION,
    }:
        return SIGNAL_IDENTITY_CONFLICT, SIGNAL_IDENTITY_CONFLICT, False
    if error.reason_code in {
        active.SIGNAL_ID_COLLISION,
        active.PUBLICATION_OCCUPANCY_RECONCILIATION_REQUIRED,
    }:
        return TRANSACTION_IDENTITY_CONFLICT, TRANSACTION_IDENTITY_CONFLICT, False
    if error.reason_code == active.TRANSITION_ID_COLLISION:
        return RESERVATION_IDENTITY_CONFLICT, RESERVATION_IDENTITY_CONFLICT, False
    if error.reason_code == active.LOCK_ACQUISITION_FAILED:
        return PUBLICATION_SUCCEEDED_REGISTRATION_PENDING, ACTIVE_LOCK_UNAVAILABLE, True
    if error.reason_code == active.ATOMIC_WRITE_FAILED:
        return PUBLICATION_SUCCEEDED_REGISTRATION_PENDING, ACTIVE_PERSISTENCE_FAILURE, True
    return PUBLICATION_SUCCEEDED_REGISTRATION_PENDING, ACTIVE_LEDGER_INVALID, True


def _matches_persisted(
    document: Mapping[str, Any],
    *,
    context: Mapping[str, str | None],
    transaction_id: str,
    transition_id: str,
) -> bool:
    try:
        ledger = active.validate_ledger(document)
    except (active.ActiveSignalLedgerError, TypeError, ValueError):
        return False
    signal = ledger["signals"].get(context["signal_id"])
    transaction = ledger["publication_transactions"].get(transaction_id)
    transition = ledger["transitions"].get(transition_id)
    expected = {
        "signal_id": context["signal_id"],
        "delivery_id": context["delivery_id"],
        "mode": context["mode"],
        "symbol": context["symbol"],
        "published_at": context["published_at"],
        "source_payload_hash": context["source_payload_hash"],
        "publication_payload_hash": context["publication_payload_hash"],
    }
    return bool(
        signal is not None
        and transaction is not None
        and transition is not None
        and all(signal.get(key) == value for key, value in expected.items())
        and all(transaction.get(key) == value for key, value in expected.items())
        and transaction.get("transaction_id") == transaction_id
        and transaction.get("reservation_transition_id") == transition_id
        and transaction.get("state") == active.OCCUPANCY_COMMITTED
        and signal.get("state") == active.PUBLISHED_PENDING_ENTRY
        and signal.get("last_transition_id") == transition_id
        and transition.get("operation") == "RESERVE"
        and transition.get("signal_id") == context["signal_id"]
        and transition.get("to_state") == active.PUBLISHED_PENDING_ENTRY
    )


def _inspect_relation(
    ledger: Mapping[str, Any],
    *,
    context: Mapping[str, str | None],
    transaction_id: str,
    transition_id: str,
) -> str:
    signal_conflict, signal = _signal_identity_conflict(ledger, context=context)
    if signal_conflict:
        return SIGNAL_IDENTITY_CONFLICT

    transaction = ledger["publication_transactions"].get(transaction_id)
    if transaction is None:
        if transition_id in ledger["transitions"]:
            return RESERVATION_IDENTITY_CONFLICT
        if signal is not None or any(
            item.get("signal_id") == context["signal_id"]
            or item.get("delivery_id") == context["delivery_id"]
            for item in ledger["publication_transactions"].values()
        ):
            return TRANSACTION_IDENTITY_CONFLICT
        return NO_REGISTRATION

    candidate = {
        "transaction_id": transaction_id,
        "signal_id": context["signal_id"],
        "delivery_id": context["delivery_id"],
        "mode": context["mode"],
        "symbol": context["symbol"],
        "published_at": context["published_at"],
        "source_payload_hash": context["source_payload_hash"],
        "publication_payload_hash": context["publication_payload_hash"],
    }
    if any(transaction.get(key) != value for key, value in candidate.items()):
        return TRANSACTION_IDENTITY_CONFLICT
    if transaction.get("reservation_transition_id") != transition_id:
        return RESERVATION_IDENTITY_CONFLICT
    if _matches_persisted(
        ledger,
        context=context,
        transaction_id=transaction_id,
        transition_id=transition_id,
    ):
        return REGISTRATION_ALREADY_PRESENT
    return NO_REGISTRATION


def _signal_identity_conflict(
    ledger: Mapping[str, Any], *, context: Mapping[str, str | None]
) -> tuple[bool, Mapping[str, Any] | None]:
    """Compare signal evidence before any transaction or transition evidence."""
    signal = ledger["signals"].get(context["signal_id"])
    if signal is not None:
        immutable = {
            "delivery_id": context["delivery_id"],
            "mode": context["mode"],
            "symbol": context["symbol"],
            "published_at": context["published_at"],
            "source_payload_hash": context["source_payload_hash"],
            "publication_payload_hash": context["publication_payload_hash"],
        }
        return (
            any(signal.get(key) != value for key, value in immutable.items()),
            signal,
        )
    delivery_collision = any(
        record.get("delivery_id") == context["delivery_id"]
        for record in ledger["signals"].values()
    )
    return delivery_collision, None


def _known_reservation_conflict(
    ledger: Mapping[str, Any],
    *,
    context: Mapping[str, str | None],
    transaction_id: str,
    transition_id: str,
) -> str | None:
    """Classify a known collision before asking the ledger to persist anything."""
    signal_conflict, _ = _signal_identity_conflict(ledger, context=context)
    if signal_conflict:
        return SIGNAL_IDENTITY_CONFLICT
    transaction = ledger["publication_transactions"].get(transaction_id)
    if transaction is not None:
        immutable = {
            "signal_id": context["signal_id"],
            "delivery_id": context["delivery_id"],
            "mode": context["mode"],
            "symbol": context["symbol"],
            "published_at": context["published_at"],
            "source_payload_hash": context["source_payload_hash"],
            "publication_payload_hash": context["publication_payload_hash"],
        }
        if any(transaction.get(key) != value for key, value in immutable.items()):
            return TRANSACTION_IDENTITY_CONFLICT
        if transaction.get("reservation_transition_id") != transition_id:
            return RESERVATION_IDENTITY_CONFLICT
    transition = ledger["transitions"].get(transition_id)
    if transition is not None and transaction is None:
        return RESERVATION_IDENTITY_CONFLICT
    return None


def _reserve(
    *,
    active_ledger_path: str | Path,
    expected_active_ledger_revision: int,
    context: Mapping[str, str | None],
    transaction_id: str,
    transition_id: str,
    timestamp: str,
    repair: bool,
) -> PassivePublishedSignalRegistrationResultV1:
    common = _common(context, transaction_id=transaction_id, transition_id=transition_id)
    try:
        if type(expected_active_ledger_revision) is not int or expected_active_ledger_revision < 0:
            return _result(
                ACTIVE_REVISION_CONFLICT,
                timestamp=timestamp,
                reason=ACTIVE_REVISION_CONFLICT,
                **common,
            )
        before = active.load_ledger(active_ledger_path)
        if before["ledger_revision"] != expected_active_ledger_revision:
            return _result(
                ACTIVE_REVISION_CONFLICT,
                timestamp=timestamp,
                active_ledger_revision=before["ledger_revision"],
                reason=ACTIVE_REVISION_CONFLICT,
                **common,
            )
        conflict = _known_reservation_conflict(
            before,
            context=context,
            transaction_id=transaction_id,
            transition_id=transition_id,
        )
        if conflict is not None:
            return _result(conflict, timestamp=timestamp, reason=conflict, **common)
        document = active.reserve_published_signal(
            active_ledger_path,
            expected_revision=expected_active_ledger_revision,
            transaction_id=transaction_id,
            transition_id=transition_id,
            signal_id=context["signal_id"],
            delivery_id=context["delivery_id"],
            mode=context["mode"],
            symbol=context["symbol"],
            published_at=context["published_at"],
            source_payload_hash=context["source_payload_hash"],
            publication_payload_hash=context["publication_payload_hash"],
            updated_at=timestamp,
            publication_intent_durable=True,
        )
    except active.ActiveSignalLedgerError as error:
        result, reason, pending = _active_error(error)
        if pending:
            return _pending(
                context,
                transaction_id=transaction_id,
                transition_id=transition_id,
                timestamp=timestamp,
                reason=reason,
            )
        return _result(result, timestamp=timestamp, reason=reason, **common)
    except Exception:
        return _pending(
            context,
            transaction_id=transaction_id,
            transition_id=transition_id,
            timestamp=timestamp,
            reason=ACTIVE_PERSISTENCE_FAILURE,
        )

    if not _matches_persisted(
        document,
        context=context,
        transaction_id=transaction_id,
        transition_id=transition_id,
    ):
        return _result(FAIL_CLOSED, timestamp=timestamp, reason=FAIL_CLOSED, **common)
    revision = document["ledger_revision"]
    mutated = revision == before["ledger_revision"] + 1
    if repair and not mutated:
        classification = REGISTRATION_ALREADY_PRESENT
    elif mutated:
        classification = PUBLISHED_SIGNAL_REGISTERED
    else:
        classification = PUBLISHED_SIGNAL_REGISTRATION_REPLAYED
    return _result(
        classification,
        timestamp=timestamp,
        active_ledger_revision=revision,
        current_state=active.PUBLISHED_PENDING_ENTRY,
        registration_applied=mutated,
        replay=not mutated,
        reason=classification,
        **common,
    )


def register_published_signal(
    *,
    active_ledger_path: str | Path,
    expected_active_ledger_revision: int,
    publication_evidence: Mapping[str, Any],
    reservation_transition_id: str,
    timestamp: str,
) -> PassivePublishedSignalRegistrationResultV1:
    """Register one caller-confirmed completed publication, without publishing it."""
    try:
        timestamp = _timestamp(timestamp)
        transition_id = _nonempty(reservation_transition_id)
        context = _validated_context(publication_evidence)
        transaction_id = _transaction_id(context)
    except Exception:
        return _result(
            INVALID_PUBLICATION_EVIDENCE,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            reason=INVALID_PUBLICATION_EVIDENCE,
        )
    return _reserve(
        active_ledger_path=active_ledger_path,
        expected_active_ledger_revision=expected_active_ledger_revision,
        context=context,
        transaction_id=transaction_id,
        transition_id=transition_id,
        timestamp=timestamp,
        repair=False,
    )


def reconcile_published_signal_registration(
    *,
    active_ledger_path: str | Path,
    expected_active_ledger_revision: int,
    publication_evidence: Mapping[str, Any],
    reservation_transition_id: str,
    timestamp: str,
) -> PassivePublishedSignalRegistrationResultV1:
    """Explicitly repair a missing registration without any publication action."""
    try:
        timestamp = _timestamp(timestamp)
        transition_id = _nonempty(reservation_transition_id)
        context = _validated_context(publication_evidence)
        transaction_id = _transaction_id(context)
    except Exception:
        return _result(
            INVALID_PUBLICATION_EVIDENCE,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            reason=INVALID_PUBLICATION_EVIDENCE,
        )
    return _reserve(
        active_ledger_path=active_ledger_path,
        expected_active_ledger_revision=expected_active_ledger_revision,
        context=context,
        transaction_id=transaction_id,
        transition_id=transition_id,
        timestamp=timestamp,
        repair=True,
    )


def inspect_published_signal_registration(
    *,
    active_ledger: Mapping[str, Any],
    publication_evidence: Mapping[str, Any],
    reservation_transition_id: str,
    timestamp: str,
) -> PassivePublishedSignalRegistrationResultV1:
    """Inspect snapshots only; never read files, acquire locks, or mutate state."""
    try:
        timestamp = _timestamp(timestamp)
        transition_id = _nonempty(reservation_transition_id)
        context = _validated_context(publication_evidence)
        transaction_id = _transaction_id(context)
    except Exception:
        return _result(
            INVALID_PUBLICATION_EVIDENCE,
            timestamp=timestamp if isinstance(timestamp, str) else None,
            reason=INVALID_PUBLICATION_EVIDENCE,
        )
    try:
        ledger = active.validate_ledger(active_ledger)
    except Exception:
        return _result(
            FAIL_CLOSED,
            timestamp=timestamp,
            reason=FAIL_CLOSED,
            **_common(
                context,
                transaction_id=transaction_id,
                transition_id=transition_id,
            ),
        )
    common = _common(context, transaction_id=transaction_id, transition_id=transition_id)
    relation = _inspect_relation(
        ledger,
        context=context,
        transaction_id=transaction_id,
        transition_id=transition_id,
    )
    if relation == REGISTRATION_ALREADY_PRESENT:
        return _result(
            relation,
            timestamp=timestamp,
            active_ledger_revision=ledger["ledger_revision"],
            current_state=active.PUBLISHED_PENDING_ENTRY,
            reason=relation,
            **common,
        )
    return _result(
        relation,
        timestamp=timestamp,
        active_ledger_revision=ledger["ledger_revision"],
        reason=relation,
        **common,
    )
