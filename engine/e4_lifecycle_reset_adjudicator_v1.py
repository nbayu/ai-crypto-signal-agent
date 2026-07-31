"""Pure deterministic E4 lifecycle-reset adjudication evidence."""

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Final

from engine.e4_thesis_fingerprint_v1 import (
    E4ThesisFingerprintV1,
    THESIS_IDENTITY_FIELDS,
)


__all__ = (
    "POLICY_VERSION",
    "PREVIOUS_THESIS_STATES",
    "DECISION_CODES",
    "ALLOW_INITIAL_PUBLICATION",
    "ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER",
    "ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER",
    "ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS",
    "ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS",
    "SUPPRESS_SAME_FINGERPRINT",
    "SUPPRESS_ARMED_STATE",
    "SUPPRESS_ACTIONABLE_STATE",
    "SUPPRESS_PUBLISHED_PENDING_ENTRY_STATE",
    "SUPPRESS_ENTRY_ACTIVE_STATE",
    "SUPPRESS_ZONE_EXIT_REQUIRED",
    "SUPPRESS_NEW_TRIGGER_GENERATION_REQUIRED",
    "SUPPRESS_NEW_STRUCTURE_OR_ANCHORS_REQUIRED",
    "SUPPRESS_TIME_ONLY_RESET",
    "SUPPRESS_UNSUPPORTED_IDENTITY_DELTA",
    "E4LifecycleResetDecisionV1",
    "adjudicate_e4_lifecycle_reset_v1",
)


POLICY_VERSION: Final = "e4-lifecycle-reset-policy-v1"

PREVIOUS_THESIS_STATES: Final = (
    "ARMED",
    "ACTIONABLE",
    "PUBLISHED_PENDING_ENTRY",
    "ENTRY_ACTIVE",
    "SKIPPED",
    "REJECTED_BY_OWNER",
    "INVALIDATED",
    "CLOSED",
)

ALLOW_INITIAL_PUBLICATION: Final = "ALLOW_INITIAL_PUBLICATION"
ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER: Final = (
    "ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER"
)
ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER: Final = (
    "ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER"
)
ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS: Final = (
    "ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS"
)
ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS: Final = (
    "ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS"
)
SUPPRESS_SAME_FINGERPRINT: Final = "SUPPRESS_SAME_FINGERPRINT"
SUPPRESS_ARMED_STATE: Final = "SUPPRESS_ARMED_STATE"
SUPPRESS_ACTIONABLE_STATE: Final = "SUPPRESS_ACTIONABLE_STATE"
SUPPRESS_PUBLISHED_PENDING_ENTRY_STATE: Final = (
    "SUPPRESS_PUBLISHED_PENDING_ENTRY_STATE"
)
SUPPRESS_ENTRY_ACTIVE_STATE: Final = "SUPPRESS_ENTRY_ACTIVE_STATE"
SUPPRESS_ZONE_EXIT_REQUIRED: Final = "SUPPRESS_ZONE_EXIT_REQUIRED"
SUPPRESS_NEW_TRIGGER_GENERATION_REQUIRED: Final = (
    "SUPPRESS_NEW_TRIGGER_GENERATION_REQUIRED"
)
SUPPRESS_NEW_STRUCTURE_OR_ANCHORS_REQUIRED: Final = (
    "SUPPRESS_NEW_STRUCTURE_OR_ANCHORS_REQUIRED"
)
SUPPRESS_TIME_ONLY_RESET: Final = "SUPPRESS_TIME_ONLY_RESET"
SUPPRESS_UNSUPPORTED_IDENTITY_DELTA: Final = (
    "SUPPRESS_UNSUPPORTED_IDENTITY_DELTA"
)

DECISION_CODES: Final = (
    ALLOW_INITIAL_PUBLICATION,
    ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER,
    ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER,
    ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS,
    ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS,
    SUPPRESS_SAME_FINGERPRINT,
    SUPPRESS_ARMED_STATE,
    SUPPRESS_ACTIONABLE_STATE,
    SUPPRESS_PUBLISHED_PENDING_ENTRY_STATE,
    SUPPRESS_ENTRY_ACTIVE_STATE,
    SUPPRESS_ZONE_EXIT_REQUIRED,
    SUPPRESS_NEW_TRIGGER_GENERATION_REQUIRED,
    SUPPRESS_NEW_STRUCTURE_OR_ANCHORS_REQUIRED,
    SUPPRESS_TIME_ONLY_RESET,
    SUPPRESS_UNSUPPORTED_IDENTITY_DELTA,
)


_ERROR: Final = "invalid E4 lifecycle reset adjudication"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_ANCHOR_FIELDS: Final = (
    "anchor_low_at",
    "anchor_low_tick",
    "anchor_high_at",
    "anchor_high_tick",
)
_CONTEXT_FIELDS: Final = (
    "venue",
    "canonical_pair",
    "mode",
    "side",
    "strategy_version",
    "mode_profile_version",
    "structure_timeframe",
    "target_policy_version",
    "trigger_type",
    "trigger_timeframe",
)
def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _fingerprint(value: object) -> E4ThesisFingerprintV1:
    _require(type(value) is E4ThesisFingerprintV1)
    value.__post_init__()
    return value


def _changed_fields(value: object) -> tuple[str, ...]:
    _require(type(value) is tuple)
    fields = tuple(value)
    _require(all(type(field) is str for field in fields))
    _require(len(fields) == len(set(fields)))
    _require(all(field in THESIS_IDENTITY_FIELDS for field in fields))
    ordered = tuple(
        field for field in THESIS_IDENTITY_FIELDS if field in fields
    )
    _require(fields == ordered)
    return fields


def _expected_decision(
    *,
    prior_history_exists: bool,
    prior_state: str | None,
    same_fingerprint: bool,
    changed_identity_fields: tuple[str, ...],
    price_exited_zone: bool,
    trigger_generation_changed: bool,
    structure_generation_changed: bool,
    anchor_pair_changed: bool,
) -> str:
    if not prior_history_exists:
        return ALLOW_INITIAL_PUBLICATION
    if same_fingerprint:
        return SUPPRESS_SAME_FINGERPRINT
    _require(type(prior_state) is str)
    if prior_state == "ARMED":
        return SUPPRESS_ARMED_STATE
    if prior_state == "ACTIONABLE":
        return SUPPRESS_ACTIONABLE_STATE
    if prior_state == "PUBLISHED_PENDING_ENTRY":
        return SUPPRESS_PUBLISHED_PENDING_ENTRY_STATE
    if prior_state == "ENTRY_ACTIVE":
        return SUPPRESS_ENTRY_ACTIVE_STATE
    if any(field in _CONTEXT_FIELDS for field in changed_identity_fields):
        return SUPPRESS_UNSUPPORTED_IDENTITY_DELTA
    time_only_reset = changed_identity_fields == (
        "trigger_candle_close_at",
    )
    if prior_state in ("SKIPPED", "REJECTED_BY_OWNER"):
        if time_only_reset:
            return SUPPRESS_TIME_ONLY_RESET
        if not price_exited_zone:
            return SUPPRESS_ZONE_EXIT_REQUIRED
        if not trigger_generation_changed:
            return SUPPRESS_NEW_TRIGGER_GENERATION_REQUIRED
        if prior_state == "SKIPPED":
            return ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER
        return ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER
    if time_only_reset:
        return SUPPRESS_TIME_ONLY_RESET
    if not structure_generation_changed and not anchor_pair_changed:
        return SUPPRESS_NEW_STRUCTURE_OR_ANCHORS_REQUIRED
    if prior_state == "INVALIDATED":
        return ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS
    _require(prior_state == "CLOSED")
    return ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS


def _canonical_json(mapping: dict[str, object]) -> str:
    return json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _decision_hash(mapping: dict[str, object]) -> str:
    return sha256(_canonical_json(mapping).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class E4LifecycleResetDecisionV1:
    policy_version: str
    prior_history_exists: bool
    prior_state: str | None
    prior_identity_sha256: str | None
    candidate_identity_sha256: str
    same_fingerprint: bool
    changed_identity_fields: tuple[str, ...]
    price_exited_zone: bool
    trigger_generation_changed: bool
    trigger_candle_close_changed: bool
    structure_generation_changed: bool
    anchor_pair_changed: bool
    publication_allowed: bool
    decision_code: str
    decision_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.policy_version) is str)
            _require(self.policy_version == POLICY_VERSION)
            _require(type(self.prior_history_exists) is bool)
            _require(type(self.price_exited_zone) is bool)
            _require(type(self.same_fingerprint) is bool)
            _require(type(self.trigger_generation_changed) is bool)
            _require(type(self.trigger_candle_close_changed) is bool)
            _require(type(self.structure_generation_changed) is bool)
            _require(type(self.anchor_pair_changed) is bool)
            _require(type(self.publication_allowed) is bool)
            _require(type(self.candidate_identity_sha256) is str)
            _require(
                _SHA256_PATTERN.fullmatch(self.candidate_identity_sha256)
                is not None
            )
            fields = _changed_fields(self.changed_identity_fields)
            if self.prior_history_exists:
                _require(type(self.prior_state) is str)
                _require(self.prior_state in PREVIOUS_THESIS_STATES)
                _require(type(self.prior_identity_sha256) is str)
                _require(
                    _SHA256_PATTERN.fullmatch(self.prior_identity_sha256)
                    is not None
                )
                _require(
                    self.same_fingerprint
                    is (
                        self.prior_identity_sha256
                        == self.candidate_identity_sha256
                    )
                )
                _require(self.same_fingerprint is (len(fields) == 0))
            else:
                _require(self.prior_state is None)
                _require(self.prior_identity_sha256 is None)
                _require(self.same_fingerprint is False)
                _require(fields == ())
            _require(
                self.trigger_generation_changed
                is ("trigger_generation_id" in fields)
            )
            _require(
                self.trigger_candle_close_changed
                is ("trigger_candle_close_at" in fields)
            )
            _require(
                self.structure_generation_changed
                is ("structure_generation_id" in fields)
            )
            _require(
                self.anchor_pair_changed
                is any(field in _ANCHOR_FIELDS for field in fields)
            )
            _require(type(self.decision_code) is str)
            _require(self.decision_code in DECISION_CODES)
            expected_decision = _expected_decision(
                prior_history_exists=self.prior_history_exists,
                prior_state=self.prior_state,
                same_fingerprint=self.same_fingerprint,
                changed_identity_fields=fields,
                price_exited_zone=self.price_exited_zone,
                trigger_generation_changed=self.trigger_generation_changed,
                structure_generation_changed=(
                    self.structure_generation_changed
                ),
                anchor_pair_changed=self.anchor_pair_changed,
            )
            _require(self.decision_code == expected_decision)
            _require(
                self.publication_allowed
                is expected_decision.startswith("ALLOW_")
            )
            _require(type(self.decision_sha256) is str)
            _require(_SHA256_PATTERN.fullmatch(self.decision_sha256) is not None)
            mapping = self.to_mapping()
            supplied_hash = mapping.pop("decision_sha256")
            _require(supplied_hash == _decision_hash(mapping))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "prior_history_exists": self.prior_history_exists,
            "prior_state": self.prior_state,
            "prior_identity_sha256": self.prior_identity_sha256,
            "candidate_identity_sha256": self.candidate_identity_sha256,
            "same_fingerprint": self.same_fingerprint,
            "changed_identity_fields": self.changed_identity_fields,
            "price_exited_zone": self.price_exited_zone,
            "trigger_generation_changed": self.trigger_generation_changed,
            "trigger_candle_close_changed": self.trigger_candle_close_changed,
            "structure_generation_changed": self.structure_generation_changed,
            "anchor_pair_changed": self.anchor_pair_changed,
            "publication_allowed": self.publication_allowed,
            "decision_code": self.decision_code,
            "decision_sha256": self.decision_sha256,
        }

    def canonical_decision_json(self) -> str:
        mapping = self.to_mapping()
        mapping.pop("decision_sha256")
        return _canonical_json(mapping)


def adjudicate_e4_lifecycle_reset_v1(
    *,
    candidate_fingerprint: E4ThesisFingerprintV1,
    prior_fingerprint: E4ThesisFingerprintV1 | None,
    prior_state: str | None,
    price_exited_zone: bool,
) -> E4LifecycleResetDecisionV1:
    try:
        candidate = _fingerprint(candidate_fingerprint)
        _require(type(price_exited_zone) is bool)
        prior_history_exists = prior_fingerprint is not None
        _require(prior_history_exists is (prior_state is not None))

        if not prior_history_exists:
            changed_identity_fields: tuple[str, ...] = ()
            prior_identity_sha256 = None
            same_fingerprint = False
        else:
            prior = _fingerprint(prior_fingerprint)
            _require(type(prior_state) is str)
            _require(prior_state in PREVIOUS_THESIS_STATES)
            prior_mapping = prior.to_identity_mapping()
            candidate_mapping = candidate.to_identity_mapping()
            changed_identity_fields = tuple(
                field
                for field in THESIS_IDENTITY_FIELDS
                if prior_mapping[field] != candidate_mapping[field]
            )
            prior_identity_sha256 = prior.identity_sha256
            same_fingerprint = (
                prior.identity_sha256 == candidate.identity_sha256
            )

        trigger_generation_changed = (
            "trigger_generation_id" in changed_identity_fields
        )
        trigger_candle_close_changed = (
            "trigger_candle_close_at" in changed_identity_fields
        )
        structure_generation_changed = (
            "structure_generation_id" in changed_identity_fields
        )
        anchor_pair_changed = any(
            field in _ANCHOR_FIELDS for field in changed_identity_fields
        )
        decision_code = _expected_decision(
            prior_history_exists=prior_history_exists,
            prior_state=prior_state,
            same_fingerprint=same_fingerprint,
            changed_identity_fields=changed_identity_fields,
            price_exited_zone=price_exited_zone,
            trigger_generation_changed=trigger_generation_changed,
            structure_generation_changed=structure_generation_changed,
            anchor_pair_changed=anchor_pair_changed,
        )
        mapping: dict[str, object] = {
            "policy_version": POLICY_VERSION,
            "prior_history_exists": prior_history_exists,
            "prior_state": prior_state,
            "prior_identity_sha256": prior_identity_sha256,
            "candidate_identity_sha256": candidate.identity_sha256,
            "same_fingerprint": same_fingerprint,
            "changed_identity_fields": changed_identity_fields,
            "price_exited_zone": price_exited_zone,
            "trigger_generation_changed": trigger_generation_changed,
            "trigger_candle_close_changed": trigger_candle_close_changed,
            "structure_generation_changed": structure_generation_changed,
            "anchor_pair_changed": anchor_pair_changed,
            "publication_allowed": decision_code.startswith("ALLOW_"),
            "decision_code": decision_code,
        }
        return E4LifecycleResetDecisionV1(
            **mapping,
            decision_sha256=_decision_hash(mapping),
        )
    except Exception:
        _fail()
