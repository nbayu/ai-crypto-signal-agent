"""Replay-safe binding of an E6 publication to passive owner lifecycle state.

This adapter registers completed publication evidence in the existing active
signal ledger.  Registration creates only ``PUBLISHED_PENDING_ENTRY`` state;
the existing owner-confirmed lifecycle service remains the sole authority for
entry activation, slot use, and canonical-pair ownership.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as active
from engine import passive_published_signal_registration_v1 as registration
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine.e6_publication_envelope_v1 import (
    E6PublicationEnvelopeV1,
    MANUAL_OWNER_AUTHORITY_STATEMENT,
    OWNER_ACTION_AWAITING_MANUAL_DECISION,
)


E6_OWNER_STATE_LIFECYCLE_BINDING_VERSION = "e6-owner-state-lifecycle-binding-v1"
E6_OWNER_STATE_LIFECYCLE_BINDING_SCHEMA = (
    "ai-crypto-signal-agent.e6-owner-state-lifecycle-binding.v1"
)
E6_OWNER_STATE_LIFECYCLE_RESULT_VERSION = (
    "e6-owner-state-lifecycle-binding-result-v1"
)

CREATED = "CREATED"
IDEMPOTENT_REPLAY = "IDEMPOTENT_REPLAY"
HOLD_CONFLICT = "HOLD_CONFLICT"
OWNER_CONTROL_RESOLUTION = "EXISTING_OWNER_SERVICE_PENDING_PAIR_OR_REPLY_BINDING"

_CLASSIFICATIONS = frozenset({CREATED, IDEMPOTENT_REPLAY, HOLD_CONFLICT})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DELIVERY_ID = re.compile(r"^PDL-[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_FAILURE = "invalid E6 owner state lifecycle binding"


def _fail() -> None:
    raise ValueError(_FAILURE)


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _nonblank(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _valid_sha256(value: object) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _canonical_json(value: Mapping[str, object]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    _require(parsed.tzinfo == timezone.utc)
    return parsed


def _hash_mapping(value: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _active_pair_count(ledger: Mapping[str, Any]) -> int:
    return len(
        {
            active.normalize_pair(record["symbol"])
            for record in ledger["signals"].values()
            if record["state"] == active.ENTRY_ACTIVE
        }
    )


@dataclass(frozen=True, slots=True)
class E6OwnerStateLifecycleBindingV1:
    """Immutable registration and owner-lifecycle correlation proposal."""

    binding_version: str
    binding_schema: str
    publication_envelope_sha256: str
    publication_identity_sha256: str
    signal_id: str
    delivery_id: str
    thesis_fingerprint_sha256: str
    source_payload_hash: str
    publication_payload_hash: str
    completed_publication_content_sha256: str | None
    canonical_pair: str
    registration_symbol: str
    mode: str
    side: str
    published_at: str
    owner_action_state: str
    manual_owner_authority_statement: str
    registration_state: str
    owner_control_resolution: str
    reservation_transition_id: str
    publication_transport_allowed: bool
    telegram_send_allowed: bool
    owner_decision_synthesized: bool
    entry_active_mutation_allowed: bool
    slot_mutation_allowed: bool
    pair_lock_mutation_allowed: bool
    exchange_order_allowed: bool
    binding_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                self.binding_version == E6_OWNER_STATE_LIFECYCLE_BINDING_VERSION
            )
            _require(
                self.binding_schema == E6_OWNER_STATE_LIFECYCLE_BINDING_SCHEMA
            )
            for value in (
                self.publication_envelope_sha256,
                self.publication_identity_sha256,
                self.thesis_fingerprint_sha256,
                self.source_payload_hash,
                self.publication_payload_hash,
                self.binding_sha256,
            ):
                _require(_valid_sha256(value))
            _require(
                self.completed_publication_content_sha256 is None
                or _valid_sha256(self.completed_publication_content_sha256)
            )
            _require(_nonblank(self.signal_id))
            _require(_DELIVERY_ID.fullmatch(self.delivery_id) is not None)
            for value in (
                self.canonical_pair,
                self.registration_symbol,
                self.mode,
                self.side,
            ):
                _require(_nonblank(value))
            _require(
                active.normalize_pair(self.registration_symbol)
                == self.canonical_pair
            )
            _require(self.mode in active.STYLES)
            _require(self.side in {"LONG", "SHORT"})
            _require(_UTC.fullmatch(self.published_at) is not None)
            _require(
                self.owner_action_state == OWNER_ACTION_AWAITING_MANUAL_DECISION
            )
            _require(
                self.manual_owner_authority_statement
                == MANUAL_OWNER_AUTHORITY_STATEMENT
            )
            _require(self.registration_state == active.PUBLISHED_PENDING_ENTRY)
            _require(self.owner_control_resolution == OWNER_CONTROL_RESOLUTION)
            _require(
                self.reservation_transition_id
                == "e6-owner-bind-" + _hash_mapping(_binding_core(self))
            )
            for authority in (
                self.publication_transport_allowed,
                self.telegram_send_allowed,
                self.owner_decision_synthesized,
                self.entry_active_mutation_allowed,
                self.slot_mutation_allowed,
                self.pair_lock_mutation_allowed,
                self.exchange_order_allowed,
            ):
                _require(type(authority) is bool and authority is False)
            _require(self.binding_sha256 == _hash_mapping(_binding_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_binding_preimage(self),
            "binding_sha256": self.binding_sha256,
        }

    def canonical_binding_json(self) -> str:
        """Return deterministic UTF-8 JSON identity input, excluding its hash."""

        return _canonical_json(_binding_preimage(self))


def _binding_core(binding: E6OwnerStateLifecycleBindingV1) -> dict[str, object]:
    return {
        "binding_version": binding.binding_version,
        "binding_schema": binding.binding_schema,
        "publication_envelope_sha256": binding.publication_envelope_sha256,
        "publication_identity_sha256": binding.publication_identity_sha256,
        "signal_id": binding.signal_id,
        "delivery_id": binding.delivery_id,
        "thesis_fingerprint_sha256": binding.thesis_fingerprint_sha256,
        "source_payload_hash": binding.source_payload_hash,
        "publication_payload_hash": binding.publication_payload_hash,
        "completed_publication_content_sha256": (
            binding.completed_publication_content_sha256
        ),
        "canonical_pair": binding.canonical_pair,
        "registration_symbol": binding.registration_symbol,
        "mode": binding.mode,
        "side": binding.side,
        "published_at": binding.published_at,
        "owner_action_state": binding.owner_action_state,
        "manual_owner_authority_statement": (
            binding.manual_owner_authority_statement
        ),
        "registration_state": binding.registration_state,
        "owner_control_resolution": binding.owner_control_resolution,
        "publication_transport_allowed": binding.publication_transport_allowed,
        "telegram_send_allowed": binding.telegram_send_allowed,
        "owner_decision_synthesized": binding.owner_decision_synthesized,
        "entry_active_mutation_allowed": binding.entry_active_mutation_allowed,
        "slot_mutation_allowed": binding.slot_mutation_allowed,
        "pair_lock_mutation_allowed": binding.pair_lock_mutation_allowed,
        "exchange_order_allowed": binding.exchange_order_allowed,
    }


def _binding_preimage(
    binding: E6OwnerStateLifecycleBindingV1,
) -> dict[str, object]:
    return {
        **_binding_core(binding),
        "reservation_transition_id": binding.reservation_transition_id,
    }


@dataclass(frozen=True, slots=True)
class E6OwnerStateLifecycleBindingResultV1:
    """Immutable result of one registration attempt; never an owner decision."""

    result_version: str
    classification: str
    binding: E6OwnerStateLifecycleBindingV1
    registration_result: str
    registration_reason: str | None
    reservation_transaction_id: str | None
    active_ledger_revision: int
    current_state: str | None
    lifecycle_inspection_result: str | None
    registration_applied: bool
    replay: bool
    conflict: bool
    owner_decision_required: bool
    publication_transport_performed: bool
    telegram_send_performed: bool
    owner_decision_synthesized: bool
    entry_active_mutated: bool
    slot_mutated: bool
    pair_lock_mutated: bool
    exchange_order_performed: bool
    result_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(self.result_version == E6_OWNER_STATE_LIFECYCLE_RESULT_VERSION)
            _require(self.classification in _CLASSIFICATIONS)
            _require(type(self.binding) is E6OwnerStateLifecycleBindingV1)
            self.binding.__post_init__()
            _require(_nonblank(self.registration_result))
            _require(
                self.registration_reason is None
                or _nonblank(self.registration_reason)
            )
            _require(
                self.reservation_transaction_id is None
                or _nonblank(self.reservation_transaction_id)
            )
            _require(
                type(self.active_ledger_revision) is int
                and self.active_ledger_revision >= 0
            )
            _require(
                self.current_state is None
                or self.current_state == active.PUBLISHED_PENDING_ENTRY
            )
            _require(
                self.lifecycle_inspection_result is None
                or self.lifecycle_inspection_result
                == lifecycle.PUBLISHED_ENTRY_INSPECTED
            )
            _require(type(self.owner_decision_required) is bool)
            _require(self.owner_decision_required is True)
            for effect in (
                self.publication_transport_performed,
                self.telegram_send_performed,
                self.owner_decision_synthesized,
                self.entry_active_mutated,
                self.slot_mutated,
                self.pair_lock_mutated,
                self.exchange_order_performed,
            ):
                _require(type(effect) is bool and effect is False)
            if self.classification == CREATED:
                _require(self.registration_applied is True)
                _require(self.replay is False and self.conflict is False)
                _require(self.current_state == active.PUBLISHED_PENDING_ENTRY)
                _require(
                    self.lifecycle_inspection_result
                    == lifecycle.PUBLISHED_ENTRY_INSPECTED
                )
            elif self.classification == IDEMPOTENT_REPLAY:
                _require(self.registration_applied is False)
                _require(self.replay is True and self.conflict is False)
                _require(self.current_state == active.PUBLISHED_PENDING_ENTRY)
                _require(
                    self.lifecycle_inspection_result
                    == lifecycle.PUBLISHED_ENTRY_INSPECTED
                )
            else:
                _require(self.registration_applied is False)
                _require(self.replay is False and self.conflict is True)
                _require(self.lifecycle_inspection_result is None)
            _require(_valid_sha256(self.result_sha256))
            _require(self.result_sha256 == _hash_mapping(_result_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_result_preimage(self),
            "result_sha256": self.result_sha256,
        }


def _result_preimage(
    result: E6OwnerStateLifecycleBindingResultV1,
) -> dict[str, object]:
    return {
        "result_version": result.result_version,
        "classification": result.classification,
        "binding": result.binding.to_mapping(),
        "registration_result": result.registration_result,
        "registration_reason": result.registration_reason,
        "reservation_transaction_id": result.reservation_transaction_id,
        "active_ledger_revision": result.active_ledger_revision,
        "current_state": result.current_state,
        "lifecycle_inspection_result": result.lifecycle_inspection_result,
        "registration_applied": result.registration_applied,
        "replay": result.replay,
        "conflict": result.conflict,
        "owner_decision_required": result.owner_decision_required,
        "publication_transport_performed": result.publication_transport_performed,
        "telegram_send_performed": result.telegram_send_performed,
        "owner_decision_synthesized": result.owner_decision_synthesized,
        "entry_active_mutated": result.entry_active_mutated,
        "slot_mutated": result.slot_mutated,
        "pair_lock_mutated": result.pair_lock_mutated,
        "exchange_order_performed": result.exchange_order_performed,
    }


def _validated_evidence(
    envelope: E6PublicationEnvelopeV1,
    publication_evidence: Mapping[str, Any],
) -> dict[str, object]:
    _require(type(envelope) is E6PublicationEnvelopeV1)
    envelope.__post_init__()
    _require(isinstance(publication_evidence, Mapping))
    _require(publication_evidence.get("delivery_state") == "DELIVERY_SUCCEEDED")
    signal_id = publication_evidence.get("signal_id")
    delivery_id = publication_evidence.get("delivery_id")
    mode = publication_evidence.get("mode")
    published_at = publication_evidence.get("published_at")
    source_payload_hash = publication_evidence.get("source_payload_hash")
    publication_payload_hash = publication_evidence.get(
        "publication_payload_hash"
    )
    content_hash = publication_evidence.get("content_hash")
    payload = publication_evidence.get("publication_payload")
    _require(signal_id == envelope.signal_id)
    _require(type(delivery_id) is str and _DELIVERY_ID.fullmatch(delivery_id))
    _require(mode == envelope.mode)
    _require(type(published_at) is str and _UTC.fullmatch(published_at))
    _require(source_payload_hash == envelope.source_payload_hash)
    _require(_valid_sha256(publication_payload_hash))
    _require(content_hash is None or _valid_sha256(content_hash))
    _require(isinstance(payload, Mapping))
    symbol = payload.get("symbol")
    _require(_nonblank(symbol))
    _require(active.normalize_pair(symbol) == envelope.canonical_pair)
    _require(payload.get("signal_id", signal_id) == signal_id)
    _require(payload.get("mode", mode) == mode)
    return {
        "signal_id": signal_id,
        "delivery_id": delivery_id,
        "mode": mode,
        "symbol": symbol,
        "published_at": published_at,
        "source_payload_hash": source_payload_hash,
        "publication_payload_hash": publication_payload_hash,
        "content_hash": content_hash,
    }


def _build_binding(
    *,
    envelope: E6PublicationEnvelopeV1,
    evidence: Mapping[str, object],
) -> E6OwnerStateLifecycleBindingV1:
    values: dict[str, object] = {
        "binding_version": E6_OWNER_STATE_LIFECYCLE_BINDING_VERSION,
        "binding_schema": E6_OWNER_STATE_LIFECYCLE_BINDING_SCHEMA,
        "publication_envelope_sha256": envelope.publication_envelope_sha256,
        "publication_identity_sha256": envelope.publication_identity_sha256,
        "signal_id": envelope.signal_id,
        "delivery_id": evidence["delivery_id"],
        "thesis_fingerprint_sha256": envelope.thesis_fingerprint_sha256,
        "source_payload_hash": envelope.source_payload_hash,
        "publication_payload_hash": evidence["publication_payload_hash"],
        "completed_publication_content_sha256": evidence["content_hash"],
        "canonical_pair": envelope.canonical_pair,
        "registration_symbol": evidence["symbol"],
        "mode": envelope.mode,
        "side": envelope.side,
        "published_at": evidence["published_at"],
        "owner_action_state": envelope.owner_action_state,
        "manual_owner_authority_statement": (
            envelope.manual_owner_authority_statement
        ),
        "registration_state": active.PUBLISHED_PENDING_ENTRY,
        "owner_control_resolution": OWNER_CONTROL_RESOLUTION,
        "publication_transport_allowed": False,
        "telegram_send_allowed": False,
        "owner_decision_synthesized": False,
        "entry_active_mutation_allowed": False,
        "slot_mutation_allowed": False,
        "pair_lock_mutation_allowed": False,
        "exchange_order_allowed": False,
    }
    core_hash = _hash_mapping(values)
    values["reservation_transition_id"] = "e6-owner-bind-" + core_hash
    values["binding_sha256"] = _hash_mapping(values)
    return E6OwnerStateLifecycleBindingV1(**values)  # type: ignore[arg-type]


def _build_result(
    *,
    classification: str,
    binding: E6OwnerStateLifecycleBindingV1,
    registration_result: registration.PassivePublishedSignalRegistrationResultV1,
    active_ledger_revision: int,
    lifecycle_inspection_result: str | None,
) -> E6OwnerStateLifecycleBindingResultV1:
    values: dict[str, object] = {
        "result_version": E6_OWNER_STATE_LIFECYCLE_RESULT_VERSION,
        "classification": classification,
        "binding": binding,
        "registration_result": registration_result.result,
        "registration_reason": registration_result.reason,
        "reservation_transaction_id": (
            registration_result.reservation_transaction_id
        ),
        "active_ledger_revision": active_ledger_revision,
        "current_state": registration_result.current_state,
        "lifecycle_inspection_result": lifecycle_inspection_result,
        "registration_applied": registration_result.registration_applied,
        "replay": registration_result.replay,
        "conflict": classification == HOLD_CONFLICT,
        "owner_decision_required": True,
        "publication_transport_performed": False,
        "telegram_send_performed": False,
        "owner_decision_synthesized": False,
        "entry_active_mutated": False,
        "slot_mutated": False,
        "pair_lock_mutated": False,
        "exchange_order_performed": False,
    }
    values["result_sha256"] = _hash_mapping(
        {
            **values,
            "binding": binding.to_mapping(),
        }
    )
    return E6OwnerStateLifecycleBindingResultV1(**values)  # type: ignore[arg-type]


def bind_e6_publication_to_owner_state_v1(
    *,
    envelope: E6PublicationEnvelopeV1,
    active_ledger_path: str | Path,
    expected_active_ledger_revision: int,
    publication_evidence: Mapping[str, Any],
    timestamp: str,
) -> E6OwnerStateLifecycleBindingResultV1:
    """Register an eligible publication as pending explicit owner action.

    The only mutation delegated by this function is the existing passive
    publication registration.  No owner decision or active-entry transition is
    attempted, and conflicts are returned without retry or overwrite.
    """

    evidence = _validated_evidence(envelope, publication_evidence)
    _require(type(expected_active_ledger_revision) is int)
    _require(expected_active_ledger_revision >= 0)
    _require(type(timestamp) is str and _UTC.fullmatch(timestamp) is not None)
    _require(_utc_datetime(evidence["published_at"]) <= _utc_datetime(timestamp))
    _require(_utc_datetime(timestamp) <= _utc_datetime(envelope.valid_until))
    binding = _build_binding(envelope=envelope, evidence=evidence)
    before = active.load_ledger(active_ledger_path)
    before_capacity = active.inspect_capacity(before)
    before_active_pairs = _active_pair_count(before)

    registered = registration.register_published_signal(
        active_ledger_path=active_ledger_path,
        expected_active_ledger_revision=expected_active_ledger_revision,
        publication_evidence=publication_evidence,
        reservation_transition_id=binding.reservation_transition_id,
        timestamp=timestamp,
    )
    after = active.load_ledger(active_ledger_path)

    if registered.result == registration.PUBLISHED_SIGNAL_REGISTERED:
        classification = CREATED
    elif registered.result == registration.PUBLISHED_SIGNAL_REGISTRATION_REPLAYED:
        classification = IDEMPOTENT_REPLAY
    else:
        _require(before == after)
        return _build_result(
            classification=HOLD_CONFLICT,
            binding=binding,
            registration_result=registered,
            active_ledger_revision=after["ledger_revision"],
            lifecycle_inspection_result=None,
        )

    _require(registered.signal_id == binding.signal_id)
    _require(registered.delivery_id == binding.delivery_id)
    _require(registered.mode == binding.mode)
    _require(active.normalize_pair(registered.symbol) == binding.canonical_pair)
    _require(registered.source_payload_hash == binding.source_payload_hash)
    _require(
        registered.publication_payload_hash == binding.publication_payload_hash
    )
    _require(
        registered.reservation_transition_id == binding.reservation_transition_id
    )
    _require(
        registered.publication_identity_hash
        == binding.completed_publication_content_sha256
    )
    _require(registered.current_state == active.PUBLISHED_PENDING_ENTRY)
    _require(active.inspect_capacity(after) == before_capacity)
    _require(_active_pair_count(after) == before_active_pairs)
    inspected = lifecycle.inspect_signal_lifecycle(
        active_ledger=after,
        signal_id=binding.signal_id,
        timestamp=timestamp,
    )
    _require(inspected.result == lifecycle.PUBLISHED_ENTRY_INSPECTED)
    _require(inspected.current_state == active.PUBLISHED_PENDING_ENTRY)
    return _build_result(
        classification=classification,
        binding=binding,
        registration_result=registered,
        active_ledger_revision=after["ledger_revision"],
        lifecycle_inspection_result=inspected.result,
    )


__all__ = [
    "CREATED",
    "E6OwnerStateLifecycleBindingResultV1",
    "E6OwnerStateLifecycleBindingV1",
    "HOLD_CONFLICT",
    "IDEMPOTENT_REPLAY",
    "bind_e6_publication_to_owner_state_v1",
]
