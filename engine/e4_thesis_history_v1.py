"""Immutable append-only permanent E4 thesis history contract."""

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Final

from engine.e4_lifecycle_reset_adjudicator_v1 import (
    ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS,
    ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS,
    ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER,
    ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER,
    E4LifecycleResetDecisionV1,
    PREVIOUS_THESIS_STATES,
)
from engine.e4_thesis_fingerprint_v1 import (
    E4ThesisFingerprintV1,
    THESIS_IDENTITY_FIELDS,
)


__all__ = (
    "E4_THESIS_HISTORY_VERSION",
    "E4_THESIS_HISTORY_STATES",
    "E4_HISTORY_INITIAL_STATES",
    "E4_SAME_FINGERPRINT_TRANSITIONS",
    "E4ThesisHistoryEventV1",
    "E4ThesisHistoryV1",
    "create_e4_thesis_history_v1",
    "append_e4_thesis_history_event_v1",
    "reconstruct_e4_thesis_history_v1",
)


E4_THESIS_HISTORY_VERSION: Final = "e4-thesis-history-v1"
E4_THESIS_HISTORY_STATES: Final = PREVIOUS_THESIS_STATES
E4_HISTORY_INITIAL_STATES: Final = (
    "ARMED",
    "ACTIONABLE",
)
E4_SAME_FINGERPRINT_TRANSITIONS: Final = (
    ("ARMED", "ACTIONABLE"),
    ("ARMED", "INVALIDATED"),
    ("ACTIONABLE", "PUBLISHED_PENDING_ENTRY"),
    ("ACTIONABLE", "SKIPPED"),
    ("ACTIONABLE", "REJECTED_BY_OWNER"),
    ("ACTIONABLE", "INVALIDATED"),
    ("PUBLISHED_PENDING_ENTRY", "ENTRY_ACTIVE"),
    ("PUBLISHED_PENDING_ENTRY", "SKIPPED"),
    ("PUBLISHED_PENDING_ENTRY", "REJECTED_BY_OWNER"),
    ("PUBLISHED_PENDING_ENTRY", "INVALIDATED"),
    ("ENTRY_ACTIVE", "CLOSED"),
)


_ERROR: Final = "invalid E4 thesis history"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_SUCCESSOR_DECISIONS: Final = (
    ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER,
    ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER,
    ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS,
    ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS,
)
_FINGERPRINT_KEYS: Final = (
    "fingerprint_version",
    *THESIS_IDENTITY_FIELDS,
    "identity_sha256",
)
_RESET_DECISION_KEYS: Final = (
    "policy_version",
    "prior_history_exists",
    "prior_state",
    "prior_identity_sha256",
    "candidate_identity_sha256",
    "same_fingerprint",
    "changed_identity_fields",
    "price_exited_zone",
    "trigger_generation_changed",
    "trigger_candle_close_changed",
    "structure_generation_changed",
    "anchor_pair_changed",
    "publication_allowed",
    "decision_code",
    "decision_sha256",
)
_EVENT_KEYS: Final = (
    "history_version",
    "sequence",
    "fingerprint",
    "state",
    "publication_succeeded",
    "price_exited_zone",
    "reset_decision",
    "previous_event_sha256",
    "event_sha256",
)
_HISTORY_KEYS: Final = (
    "history_version",
    "revision",
    "events",
    "fingerprint_history",
    "current_identity_sha256",
    "current_state",
    "current_publication_succeeded",
    "current_price_exited_zone",
    "history_sha256",
)


def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _canonical_json(mapping: dict[str, object]) -> str:
    return json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash_mapping(mapping: dict[str, object]) -> str:
    return sha256(_canonical_json(mapping).encode("utf-8")).hexdigest()


def _fingerprint(value: object) -> E4ThesisFingerprintV1:
    _require(type(value) is E4ThesisFingerprintV1)
    value.__post_init__()
    return value


def _reset_decision(value: object) -> E4LifecycleResetDecisionV1:
    _require(type(value) is E4LifecycleResetDecisionV1)
    value.__post_init__()
    return value


def _exact_mapping(value: object, keys: tuple[str, ...]) -> dict[str, object]:
    _require(isinstance(value, Mapping))
    mapping = dict(value)
    _require(len(mapping) == len(keys))
    _require(set(mapping) == set(keys))
    return mapping


def _event_preimage(event: "E4ThesisHistoryEventV1") -> dict[str, object]:
    return {
        "history_version": event.history_version,
        "sequence": event.sequence,
        "fingerprint": event.fingerprint.to_mapping(),
        "state": event.state,
        "publication_succeeded": event.publication_succeeded,
        "price_exited_zone": event.price_exited_zone,
        "reset_decision": (
            event.reset_decision.to_mapping()
            if event.reset_decision is not None
            else None
        ),
        "previous_event_sha256": event.previous_event_sha256,
    }


@dataclass(frozen=True, slots=True)
class E4ThesisHistoryEventV1:
    history_version: str
    sequence: int
    fingerprint: E4ThesisFingerprintV1
    state: str
    publication_succeeded: bool
    price_exited_zone: bool
    reset_decision: E4LifecycleResetDecisionV1 | None
    previous_event_sha256: str | None
    event_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.history_version) is str)
            _require(self.history_version == E4_THESIS_HISTORY_VERSION)
            _require(type(self.sequence) is int)
            _require(self.sequence > 0)
            _fingerprint(self.fingerprint)
            _require(type(self.state) is str)
            _require(self.state in E4_THESIS_HISTORY_STATES)
            _require(type(self.publication_succeeded) is bool)
            _require(type(self.price_exited_zone) is bool)
            if self.reset_decision is not None:
                _reset_decision(self.reset_decision)
            if self.sequence == 1:
                _require(self.previous_event_sha256 is None)
            else:
                _require(type(self.previous_event_sha256) is str)
                _require(
                    _SHA256_PATTERN.fullmatch(self.previous_event_sha256)
                    is not None
                )
            _require(type(self.event_sha256) is str)
            _require(_SHA256_PATTERN.fullmatch(self.event_sha256) is not None)
            _require(self.event_sha256 == _hash_mapping(_event_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_event_preimage(self),
            "event_sha256": self.event_sha256,
        }

    def canonical_event_json(self) -> str:
        return _canonical_json(_event_preimage(self))


def _validate_same_fingerprint_transition(
    previous: E4ThesisHistoryEventV1,
    current: E4ThesisHistoryEventV1,
) -> None:
    _require(current.reset_decision is None)
    _require(
        not (
            previous.publication_succeeded
            and not current.publication_succeeded
        )
    )
    _require(
        not (
            previous.price_exited_zone
            and not current.price_exited_zone
        )
    )
    publication_changed = (
        previous.publication_succeeded != current.publication_succeeded
    )
    zone_changed = previous.price_exited_zone != current.price_exited_zone
    if publication_changed:
        _require(previous.publication_succeeded is False)
        _require(current.publication_succeeded is True)
        _require(current.state == "PUBLISHED_PENDING_ENTRY")
    if current.state in ("ENTRY_ACTIVE", "CLOSED"):
        _require(current.publication_succeeded is True)
    if zone_changed:
        _require(previous.price_exited_zone is False)
        _require(current.price_exited_zone is True)
        _require(previous.state == current.state)
        _require(current.state in ("SKIPPED", "REJECTED_BY_OWNER"))
    if current.state == previous.state:
        _require(publication_changed is not zone_changed)
    else:
        _require(
            (previous.state, current.state)
            in E4_SAME_FINGERPRINT_TRANSITIONS
        )


def _identity_delta(
    previous: E4ThesisFingerprintV1,
    current: E4ThesisFingerprintV1,
) -> tuple[str, ...]:
    previous_mapping = previous.to_identity_mapping()
    current_mapping = current.to_identity_mapping()
    return tuple(
        field
        for field in THESIS_IDENTITY_FIELDS
        if previous_mapping[field] != current_mapping[field]
    )


def _validate_successor_transition(
    previous: E4ThesisHistoryEventV1,
    current: E4ThesisHistoryEventV1,
    seen_fingerprints: tuple[str, ...],
) -> None:
    decision = _reset_decision(current.reset_decision)
    candidate_sha = current.fingerprint.identity_sha256
    _require(candidate_sha not in seen_fingerprints)
    _require(decision.publication_allowed is True)
    _require(decision.prior_history_exists is True)
    _require(decision.same_fingerprint is False)
    _require(decision.decision_code in _SUCCESSOR_DECISIONS)
    _require(
        decision.prior_identity_sha256
        == previous.fingerprint.identity_sha256
    )
    _require(decision.candidate_identity_sha256 == candidate_sha)
    _require(decision.prior_state == previous.state)
    _require(decision.price_exited_zone == previous.price_exited_zone)
    _require(
        decision.changed_identity_fields
        == _identity_delta(previous.fingerprint, current.fingerprint)
    )
    _require(current.state in E4_HISTORY_INITIAL_STATES)
    _require(current.publication_succeeded is False)
    _require(current.price_exited_zone is False)


def _history_preimage(history: "E4ThesisHistoryV1") -> dict[str, object]:
    return {
        "history_version": history.history_version,
        "revision": history.revision,
        "events": [event.to_mapping() for event in history.events],
        "fingerprint_history": list(history.fingerprint_history),
        "current_identity_sha256": history.current_identity_sha256,
        "current_state": history.current_state,
        "current_publication_succeeded": (
            history.current_publication_succeeded
        ),
        "current_price_exited_zone": history.current_price_exited_zone,
    }


@dataclass(frozen=True, slots=True)
class E4ThesisHistoryV1:
    history_version: str
    revision: int
    events: tuple[E4ThesisHistoryEventV1, ...]
    fingerprint_history: tuple[str, ...]
    current_identity_sha256: str
    current_state: str
    current_publication_succeeded: bool
    current_price_exited_zone: bool
    history_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.history_version) is str)
            _require(self.history_version == E4_THESIS_HISTORY_VERSION)
            _require(type(self.revision) is int)
            _require(self.revision > 0)
            _require(type(self.events) is tuple)
            _require(len(self.events) > 0)
            _require(self.revision == len(self.events))
            for event in self.events:
                _require(type(event) is E4ThesisHistoryEventV1)
                event.__post_init__()
            first = self.events[0]
            _require(first.sequence == 1)
            _require(first.previous_event_sha256 is None)
            _require(first.state in E4_HISTORY_INITIAL_STATES)
            _require(first.publication_succeeded is False)
            _require(first.price_exited_zone is False)
            _require(first.reset_decision is None)

            derived_history = [first.fingerprint.identity_sha256]
            for index, event in enumerate(self.events):
                _require(event.sequence == index + 1)
                if index == 0:
                    continue
                previous = self.events[index - 1]
                _require(
                    event.previous_event_sha256 == previous.event_sha256
                )
                if (
                    event.fingerprint.identity_sha256
                    == previous.fingerprint.identity_sha256
                ):
                    _validate_same_fingerprint_transition(previous, event)
                else:
                    _validate_successor_transition(
                        previous,
                        event,
                        tuple(derived_history),
                    )
                    derived_history.append(event.fingerprint.identity_sha256)

            _require(type(self.fingerprint_history) is tuple)
            _require(len(self.fingerprint_history) > 0)
            _require(
                all(type(value) is str for value in self.fingerprint_history)
            )
            _require(
                all(
                    _SHA256_PATTERN.fullmatch(value) is not None
                    for value in self.fingerprint_history
                )
            )
            _require(len(set(self.fingerprint_history)) == len(self.fingerprint_history))
            _require(self.fingerprint_history == tuple(derived_history))
            latest = self.events[-1]
            _require(type(self.current_identity_sha256) is str)
            _require(
                self.current_identity_sha256
                == latest.fingerprint.identity_sha256
            )
            _require(type(self.current_state) is str)
            _require(self.current_state == latest.state)
            _require(type(self.current_publication_succeeded) is bool)
            _require(
                self.current_publication_succeeded
                is latest.publication_succeeded
            )
            _require(type(self.current_price_exited_zone) is bool)
            _require(
                self.current_price_exited_zone is latest.price_exited_zone
            )
            _require(type(self.history_sha256) is str)
            _require(_SHA256_PATTERN.fullmatch(self.history_sha256) is not None)
            _require(self.history_sha256 == _hash_mapping(_history_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_history_preimage(self),
            "history_sha256": self.history_sha256,
        }

    def canonical_history_json(self) -> str:
        return _canonical_json(_history_preimage(self))


def _build_event(
    *,
    sequence: int,
    fingerprint: E4ThesisFingerprintV1,
    state: str,
    publication_succeeded: bool,
    price_exited_zone: bool,
    reset_decision: E4LifecycleResetDecisionV1 | None,
    previous_event_sha256: str | None,
) -> E4ThesisHistoryEventV1:
    mapping: dict[str, object] = {
        "history_version": E4_THESIS_HISTORY_VERSION,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "state": state,
        "publication_succeeded": publication_succeeded,
        "price_exited_zone": price_exited_zone,
        "reset_decision": reset_decision,
        "previous_event_sha256": previous_event_sha256,
    }
    preimage = {
        "history_version": E4_THESIS_HISTORY_VERSION,
        "sequence": sequence,
        "fingerprint": fingerprint.to_mapping(),
        "state": state,
        "publication_succeeded": publication_succeeded,
        "price_exited_zone": price_exited_zone,
        "reset_decision": (
            reset_decision.to_mapping()
            if reset_decision is not None
            else None
        ),
        "previous_event_sha256": previous_event_sha256,
    }
    return E4ThesisHistoryEventV1(
        **mapping,
        event_sha256=_hash_mapping(preimage),
    )


def _build_history(
    events: tuple[E4ThesisHistoryEventV1, ...],
    fingerprint_history: tuple[str, ...],
) -> E4ThesisHistoryV1:
    latest = events[-1]
    mapping: dict[str, object] = {
        "history_version": E4_THESIS_HISTORY_VERSION,
        "revision": len(events),
        "events": events,
        "fingerprint_history": fingerprint_history,
        "current_identity_sha256": latest.fingerprint.identity_sha256,
        "current_state": latest.state,
        "current_publication_succeeded": latest.publication_succeeded,
        "current_price_exited_zone": latest.price_exited_zone,
    }
    preimage = {
        "history_version": E4_THESIS_HISTORY_VERSION,
        "revision": len(events),
        "events": [event.to_mapping() for event in events],
        "fingerprint_history": list(fingerprint_history),
        "current_identity_sha256": latest.fingerprint.identity_sha256,
        "current_state": latest.state,
        "current_publication_succeeded": latest.publication_succeeded,
        "current_price_exited_zone": latest.price_exited_zone,
    }
    return E4ThesisHistoryV1(
        **mapping,
        history_sha256=_hash_mapping(preimage),
    )


def create_e4_thesis_history_v1(
    *,
    fingerprint: E4ThesisFingerprintV1,
    initial_state: str,
) -> E4ThesisHistoryV1:
    try:
        retained_fingerprint = _fingerprint(fingerprint)
        _require(type(initial_state) is str)
        _require(initial_state in E4_HISTORY_INITIAL_STATES)
        event = _build_event(
            sequence=1,
            fingerprint=retained_fingerprint,
            state=initial_state,
            publication_succeeded=False,
            price_exited_zone=False,
            reset_decision=None,
            previous_event_sha256=None,
        )
        return _build_history(
            (event,),
            (retained_fingerprint.identity_sha256,),
        )
    except Exception:
        _fail()


def append_e4_thesis_history_event_v1(
    *,
    history: E4ThesisHistoryV1,
    fingerprint: E4ThesisFingerprintV1,
    state: str,
    publication_succeeded: bool,
    price_exited_zone: bool,
    reset_decision: E4LifecycleResetDecisionV1 | None,
) -> E4ThesisHistoryV1:
    try:
        _require(type(history) is E4ThesisHistoryV1)
        history.__post_init__()
        retained_fingerprint = _fingerprint(fingerprint)
        _require(type(state) is str)
        _require(state in E4_THESIS_HISTORY_STATES)
        _require(type(publication_succeeded) is bool)
        _require(type(price_exited_zone) is bool)
        if reset_decision is not None:
            _reset_decision(reset_decision)
        event = _build_event(
            sequence=history.revision + 1,
            fingerprint=retained_fingerprint,
            state=state,
            publication_succeeded=publication_succeeded,
            price_exited_zone=price_exited_zone,
            reset_decision=reset_decision,
            previous_event_sha256=history.events[-1].event_sha256,
        )
        fingerprint_history = history.fingerprint_history
        if retained_fingerprint.identity_sha256 != history.current_identity_sha256:
            fingerprint_history = (
                *fingerprint_history,
                retained_fingerprint.identity_sha256,
            )
        return _build_history((*history.events, event), fingerprint_history)
    except Exception:
        _fail()


def _reconstruct_fingerprint(value: object) -> E4ThesisFingerprintV1:
    mapping = _exact_mapping(value, _FINGERPRINT_KEYS)
    return E4ThesisFingerprintV1(**mapping)


def _reconstruct_reset_decision(
    value: object,
) -> E4LifecycleResetDecisionV1 | None:
    if value is None:
        return None
    mapping = _exact_mapping(value, _RESET_DECISION_KEYS)
    changed_fields = mapping["changed_identity_fields"]
    _require(type(changed_fields) in (list, tuple))
    mapping["changed_identity_fields"] = tuple(changed_fields)
    return E4LifecycleResetDecisionV1(**mapping)


def _reconstruct_event(value: object) -> E4ThesisHistoryEventV1:
    mapping = _exact_mapping(value, _EVENT_KEYS)
    mapping["fingerprint"] = _reconstruct_fingerprint(mapping["fingerprint"])
    mapping["reset_decision"] = _reconstruct_reset_decision(
        mapping["reset_decision"]
    )
    return E4ThesisHistoryEventV1(**mapping)


def reconstruct_e4_thesis_history_v1(
    mapping: Mapping[str, object],
) -> E4ThesisHistoryV1:
    try:
        values = _exact_mapping(mapping, _HISTORY_KEYS)
        event_values = values["events"]
        _require(type(event_values) in (list, tuple))
        values["events"] = tuple(
            _reconstruct_event(value) for value in event_values
        )
        fingerprint_values = values["fingerprint_history"]
        _require(type(fingerprint_values) in (list, tuple))
        values["fingerprint_history"] = tuple(fingerprint_values)
        return E4ThesisHistoryV1(**values)
    except Exception:
        _fail()
