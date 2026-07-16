"""Pure deterministic mapping for explicitly supplied Phase 10 candidates."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from engine.news_event_contract_v1 import canonical_json_bytes, sha256_hex
from engine.news_source_policy_v1 import SourcePolicyDecisionV1


ENTITY_MAPPING_POLICY_VERSION = "news-entity-mapping-policy-v1"

__all__ = (
    "NewsEntityMappingError",
    "ENTITY_MAPPING_POLICY_VERSION",
    "EntityCandidateV1",
    "EntityMappingResultV1",
    "map_entity_candidates",
)


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_-]*$")
_CANDIDATE_IDENTIFIER = re.compile(r"^candidate-[A-Za-z0-9_-]+$")
_ENTITY_TYPES = frozenset(
    (
        "DIGITAL_ASSET",
        "PROTOCOL",
        "EXCHANGE",
        "ISSUER",
        "COMPANY",
        "REGULATOR",
        "JURISDICTION",
        "PERSON",
        "MARKET",
        "UNKNOWN",
    )
)
_CANDIDATE_STATUSES = frozenset(
    ("ACCEPTED", "REJECTED", "AMBIGUOUS", "UNRESOLVED")
)
_MAPPING_STATUSES = frozenset(
    ("RESOLVED", "PARTIALLY_RESOLVED", "AMBIGUOUS", "UNRESOLVED", "BLOCKED", "INVALID")
)
_REJECTION_SEQUENCE = (
    "ENTITY_TYPE_UNSUPPORTED",
    "CANONICAL_ID_MISSING",
    "CANONICAL_SYMBOL_MISSING",
    "AMBIGUOUS_IDENTITY",
    "EVIDENCE_INSUFFICIENT",
    "EVIDENCE_CONTRADICTORY",
    "DUPLICATE_CANDIDATE",
    "SOURCE_POLICY_NOT_ELIGIBLE",
    "EVENT_SNAPSHOT_MISMATCH",
    "INVALID_CANDIDATE_CONTRACT",
)
_REJECTION_REASONS = frozenset(_REJECTION_SEQUENCE)
_SOURCE_REASONS = frozenset(
    (
        "SOURCE_ELIGIBLE",
        "SOURCE_TYPE_BLOCKED",
        "SOURCE_NAMESPACE_BLOCKED",
        "PUBLISHER_BLOCKED",
        "SOURCE_TYPE_NOT_ALLOWED",
        "SOURCE_NAMESPACE_NOT_ALLOWED",
        "PUBLISHER_NOT_ALLOWED",
        "CREDIBILITY_TIER_BELOW_MINIMUM",
        "SOURCE_HEALTH_UNACCEPTABLE",
        "CONTENT_TYPE_NOT_ALLOWED",
        "URI_SCHEME_NOT_ALLOWED",
        "PUBLICATION_TIMESTAMP_IN_FUTURE",
        "POINT_IN_TIME_INVALID",
        "SOURCE_TOO_OLD",
        "CAPTURE_DELAY_EXCEEDED",
    )
)
_RESULT_REASONS = _REJECTION_REASONS | _SOURCE_REASONS
_CANDIDATE_FIELDS = frozenset(
    (
        "candidate_id",
        "entity_type",
        "canonical_entity_id",
        "canonical_name",
        "canonical_symbol",
        "source_text",
        "source_text_sha256",
        "evidence_refs",
        "confidence_basis",
        "supplied_confidence",
        "ambiguity_group_id",
        "candidate_status",
        "rejection_reason_codes",
        "mapping_policy_version",
    )
)
_RESULT_FIELDS = frozenset(
    (
        "mapping_policy_version",
        "event_snapshot_id",
        "source_policy_decision",
        "accepted_candidates",
        "rejected_candidates",
        "ambiguous_candidates",
        "unresolved_candidates",
        "mapping_status",
        "reason_codes",
        "mapping_result_id",
    )
)
_EVIDENCE_FIELDS = frozenset(
    ("evidence_ref_id", "event_snapshot_id", "reference_type", "field_name")
)


class NewsEntityMappingError(ValueError):
    """Raised when a closed entity-mapping contract is invalid."""


@dataclass(frozen=True, init=False)
class EntityCandidateV1:
    candidate_id: str
    entity_type: str
    canonical_entity_id: str
    canonical_name: str
    canonical_symbol: str | None
    source_text: str
    source_text_sha256: str
    evidence_refs: tuple[Mapping[str, str], ...]
    confidence_basis: str
    supplied_confidence: None
    ambiguity_group_id: str | None
    candidate_status: str
    rejection_reason_codes: tuple[str, ...]
    mapping_policy_version: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _CANDIDATE_FIELDS, "entity candidate")
        if values["mapping_policy_version"] != ENTITY_MAPPING_POLICY_VERSION:
            raise NewsEntityMappingError("invalid mapping_policy_version")

        candidate_id = _require_candidate_id(values["candidate_id"])
        entity_type = _require_closed(
            values["entity_type"], _ENTITY_TYPES, "entity_type"
        )
        canonical_id = _require_text(
            values["canonical_entity_id"], "canonical_entity_id"
        )
        canonical_name = _require_text(values["canonical_name"], "canonical_name")
        symbol = _require_symbol(values["canonical_symbol"], entity_type)
        source_text = _require_text(values["source_text"], "source_text")
        source_hash = _require_hash(
            values["source_text_sha256"], "source_text_sha256"
        )
        if source_hash != sha256_hex(source_text.encode("utf-8")):
            raise NewsEntityMappingError("source_text_sha256 does not match source_text")
        evidence_refs = _freeze_evidence_refs(values["evidence_refs"])
        confidence_basis = _require_closed(
            values["confidence_basis"],
            frozenset(("EXPLICIT_CALLER_ASSERTION",)),
            "confidence_basis",
        )
        if values["supplied_confidence"] is not None:
            raise NewsEntityMappingError("supplied_confidence must be null")
        status = _require_closed(
            values["candidate_status"], _CANDIDATE_STATUSES, "candidate_status"
        )
        ambiguity_group_id = _require_optional_identifier(
            values["ambiguity_group_id"], "ambiguity_group_id"
        )
        reasons = _normalize_rejection_reasons(values["rejection_reason_codes"])
        _validate_candidate_state(status, ambiguity_group_id, reasons)

        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "entity_type", entity_type)
        object.__setattr__(self, "canonical_entity_id", canonical_id)
        object.__setattr__(self, "canonical_name", canonical_name)
        object.__setattr__(self, "canonical_symbol", symbol)
        object.__setattr__(self, "source_text", source_text)
        object.__setattr__(self, "source_text_sha256", source_hash)
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "confidence_basis", confidence_basis)
        object.__setattr__(self, "supplied_confidence", None)
        object.__setattr__(self, "ambiguity_group_id", ambiguity_group_id)
        object.__setattr__(self, "candidate_status", status)
        object.__setattr__(self, "rejection_reason_codes", reasons)
        object.__setattr__(self, "mapping_policy_version", ENTITY_MAPPING_POLICY_VERSION)

    def __hash__(self) -> int:
        return hash(_candidate_semantic_bytes(self))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "entity_type": self.entity_type,
            "canonical_entity_id": self.canonical_entity_id,
            "canonical_name": self.canonical_name,
            "canonical_symbol": self.canonical_symbol,
            "source_text": self.source_text,
            "source_text_sha256": self.source_text_sha256,
            "evidence_refs": [dict(ref) for ref in self.evidence_refs],
            "confidence_basis": self.confidence_basis,
            "supplied_confidence": self.supplied_confidence,
            "ambiguity_group_id": self.ambiguity_group_id,
            "candidate_status": self.candidate_status,
            "rejection_reason_codes": self.rejection_reason_codes,
            "mapping_policy_version": self.mapping_policy_version,
        }


@dataclass(frozen=True, init=False)
class EntityMappingResultV1:
    mapping_policy_version: str
    event_snapshot_id: str
    source_policy_decision: SourcePolicyDecisionV1
    accepted_candidates: tuple[EntityCandidateV1, ...]
    rejected_candidates: tuple[EntityCandidateV1, ...]
    ambiguous_candidates: tuple[EntityCandidateV1, ...]
    unresolved_candidates: tuple[EntityCandidateV1, ...]
    mapping_status: str
    reason_codes: tuple[str, ...]
    mapping_result_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RESULT_FIELDS, "entity mapping result")
        if values["mapping_policy_version"] != ENTITY_MAPPING_POLICY_VERSION:
            raise NewsEntityMappingError("invalid mapping_policy_version")
        event_snapshot_id = _require_hash(
            values["event_snapshot_id"], "event_snapshot_id"
        )
        source_policy = values["source_policy_decision"]
        if type(source_policy) is not SourcePolicyDecisionV1:
            raise NewsEntityMappingError(
                "source_policy_decision must be SourcePolicyDecisionV1"
            )
        accepted = _freeze_partition(values["accepted_candidates"], "ACCEPTED")
        rejected = _freeze_partition(values["rejected_candidates"], "REJECTED")
        ambiguous = _freeze_partition(values["ambiguous_candidates"], "AMBIGUOUS")
        unresolved = _freeze_partition(values["unresolved_candidates"], "UNRESOLVED")
        _validate_partitions(accepted, rejected, ambiguous, unresolved)
        mapping_status = _require_closed(
            values["mapping_status"], _MAPPING_STATUSES, "mapping_status"
        )
        reasons = _normalize_result_reasons(values["reason_codes"])
        _validate_mapping_state(
            mapping_status, source_policy, accepted, rejected, ambiguous, unresolved
        )
        derived_id = _build_mapping_result_id(
            event_snapshot_id=event_snapshot_id,
            source_policy_decision=source_policy,
            accepted_candidates=accepted,
            rejected_candidates=rejected,
            ambiguous_candidates=ambiguous,
            unresolved_candidates=unresolved,
            mapping_status=mapping_status,
            reason_codes=reasons,
        )
        supplied_id = values["mapping_result_id"]
        if supplied_id is not None and supplied_id != derived_id:
            raise NewsEntityMappingError("mapping_result_id does not match result")

        object.__setattr__(self, "mapping_policy_version", ENTITY_MAPPING_POLICY_VERSION)
        object.__setattr__(self, "event_snapshot_id", event_snapshot_id)
        object.__setattr__(self, "source_policy_decision", source_policy)
        object.__setattr__(self, "accepted_candidates", accepted)
        object.__setattr__(self, "rejected_candidates", rejected)
        object.__setattr__(self, "ambiguous_candidates", ambiguous)
        object.__setattr__(self, "unresolved_candidates", unresolved)
        object.__setattr__(self, "mapping_status", mapping_status)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "mapping_result_id", derived_id)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "mapping_policy_version": self.mapping_policy_version,
            "event_snapshot_id": self.event_snapshot_id,
            "source_policy_decision": self.source_policy_decision,
            "accepted_candidates": self.accepted_candidates,
            "rejected_candidates": self.rejected_candidates,
            "ambiguous_candidates": self.ambiguous_candidates,
            "unresolved_candidates": self.unresolved_candidates,
            "mapping_status": self.mapping_status,
            "reason_codes": self.reason_codes,
            "mapping_result_id": self.mapping_result_id,
        }


def map_entity_candidates(
    *,
    event_snapshot_id: Any,
    source_policy_decision: Any,
    candidates: Any,
    resolver_selections: Any = None,
) -> EntityMappingResultV1:
    """Map caller-supplied candidates without deriving new facts."""

    event_id = _require_hash(event_snapshot_id, "event_snapshot_id")
    if type(source_policy_decision) is not SourcePolicyDecisionV1:
        raise NewsEntityMappingError(
            "source_policy_decision must be SourcePolicyDecisionV1"
        )
    supplied = _freeze_candidates(candidates)
    for candidate in supplied:
        _validate_candidate_snapshot(candidate, event_id)
    unique = _deduplicate_candidates(supplied)

    if source_policy_decision.decision != "ELIGIBLE":
        if resolver_selections is not None:
            raise NewsEntityMappingError("resolver_selections cannot override source policy")
        rejected = tuple(
            _as_rejected(candidate, "SOURCE_POLICY_NOT_ELIGIBLE")
            for candidate in unique
        )
        return _new_result(
            event_snapshot_id=event_id,
            source_policy_decision=source_policy_decision,
            accepted_candidates=(),
            rejected_candidates=rejected,
            ambiguous_candidates=(),
            unresolved_candidates=(),
            mapping_status=(
                "BLOCKED"
                if source_policy_decision.decision == "BLOCKED"
                else "INVALID"
                if source_policy_decision.decision == "INVALID"
                else "UNRESOLVED"
            ),
            reason_codes=source_policy_decision.reason_codes
            + ("SOURCE_POLICY_NOT_ELIGIBLE",),
        )

    selected = _validate_resolutions(resolver_selections, unique)
    resolved_candidates = tuple(
        _apply_selection(candidate, selected) for candidate in unique
    )
    _validate_ambiguity_groups(resolved_candidates)

    accepted = tuple(
        candidate
        for candidate in resolved_candidates
        if candidate.candidate_status == "ACCEPTED"
    )
    rejected = tuple(
        candidate
        for candidate in resolved_candidates
        if candidate.candidate_status == "REJECTED"
    )
    ambiguous = tuple(
        candidate
        for candidate in resolved_candidates
        if candidate.candidate_status == "AMBIGUOUS"
    )
    unresolved = tuple(
        candidate
        for candidate in resolved_candidates
        if candidate.candidate_status == "UNRESOLVED"
    )
    mapping_status = _mapping_status(accepted, rejected, ambiguous, unresolved)
    reasons = tuple(
        reason
        for candidate in resolved_candidates
        for reason in candidate.rejection_reason_codes
    )
    return _new_result(
        event_snapshot_id=event_id,
        source_policy_decision=source_policy_decision,
        accepted_candidates=accepted,
        rejected_candidates=rejected,
        ambiguous_candidates=ambiguous,
        unresolved_candidates=unresolved,
        mapping_status=mapping_status,
        reason_codes=reasons,
    )


def _new_result(**values: Any) -> EntityMappingResultV1:
    values["mapping_policy_version"] = ENTITY_MAPPING_POLICY_VERSION
    values["mapping_result_id"] = None
    return EntityMappingResultV1(**values)


def _require_exact_fields(
    values: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    if not isinstance(values, Mapping) or frozenset(values) != expected:
        raise NewsEntityMappingError("invalid " + label + " fields")


def _require_text(value: Any, field: str) -> str:
    if type(value) is not str:
        raise NewsEntityMappingError(field + " must be a string")
    normalized = unicodedata.normalize("NFC", value)
    if not normalized or normalized != normalized.strip():
        raise NewsEntityMappingError(field + " must be a non-empty string")
    return normalized


def _require_identifier(value: Any, field: str) -> str:
    value = _require_text(value, field)
    if not _IDENTIFIER.fullmatch(value):
        raise NewsEntityMappingError("invalid " + field)
    return value


def _require_candidate_id(value: Any) -> str:
    value = _require_text(value, "candidate_id")
    if not _CANDIDATE_IDENTIFIER.fullmatch(value):
        raise NewsEntityMappingError("invalid candidate_id")
    return value


def _require_optional_identifier(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _require_identifier(value, field)


def _require_hash(value: Any, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise NewsEntityMappingError("invalid " + field)
    return value


def _require_closed(value: Any, vocabulary: frozenset[str], field: str) -> str:
    if type(value) is not str or value not in vocabulary:
        raise NewsEntityMappingError("invalid " + field)
    return value


def _require_symbol(value: Any, entity_type: str) -> str | None:
    if value is None:
        if entity_type == "DIGITAL_ASSET":
            raise NewsEntityMappingError("canonical_symbol is required")
        return None
    return _require_text(value, "canonical_symbol")


def _freeze_evidence_refs(value: Any) -> tuple[Mapping[str, str], ...]:
    if isinstance(value, (str, bytes)):
        raise NewsEntityMappingError("evidence_refs must be a collection")
    try:
        supplied = tuple(value)
    except TypeError as exc:
        raise NewsEntityMappingError("evidence_refs must be a collection") from exc
    refs: dict[str, Mapping[str, str]] = {}
    for item in supplied:
        if not isinstance(item, Mapping) or frozenset(item) != _EVIDENCE_FIELDS:
            raise NewsEntityMappingError("invalid evidence_ref")
        evidence_id = _require_identifier(item["evidence_ref_id"], "evidence_ref_id")
        event_id = _require_hash(item["event_snapshot_id"], "evidence event_snapshot_id")
        reference_type = _require_closed(
            item["reference_type"], frozenset(("EVENT_FIELD",)), "reference_type"
        )
        field_name = _require_identifier(item["field_name"], "field_name")
        frozen = MappingProxyType(
            {
                "evidence_ref_id": evidence_id,
                "event_snapshot_id": event_id,
                "reference_type": reference_type,
                "field_name": field_name,
            }
        )
        prior = refs.get(evidence_id)
        if prior is not None and dict(prior) != dict(frozen):
            raise NewsEntityMappingError("conflicting evidence_ref_id")
        refs[evidence_id] = frozen
    if not refs:
        raise NewsEntityMappingError("evidence_refs must not be empty")
    return tuple(refs[key] for key in sorted(refs))


def _normalize_rejection_reasons(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise NewsEntityMappingError("rejection_reason_codes must be a collection")
    try:
        values = tuple(value)
    except TypeError as exc:
        raise NewsEntityMappingError("rejection_reason_codes must be a collection") from exc
    if any(type(reason) is not str or reason not in _REJECTION_REASONS for reason in values):
        raise NewsEntityMappingError("invalid rejection_reason_codes")
    supplied = set(values)
    return tuple(reason for reason in _REJECTION_SEQUENCE if reason in supplied)


def _validate_candidate_state(
    status: str, ambiguity_group_id: str | None, reasons: tuple[str, ...]
) -> None:
    if status == "ACCEPTED":
        if ambiguity_group_id is not None or reasons:
            raise NewsEntityMappingError("accepted candidate cannot have rejection facts")
        return
    if status == "REJECTED" and not reasons:
        raise NewsEntityMappingError("rejected candidate requires rejection_reason_codes")
    if status == "AMBIGUOUS":
        if ambiguity_group_id is None:
            raise NewsEntityMappingError("ambiguous candidate requires ambiguity_group_id")
        if "AMBIGUOUS_IDENTITY" not in reasons:
            raise NewsEntityMappingError("ambiguous candidate requires ambiguity reason")
    if status == "UNRESOLVED" and not reasons:
        raise NewsEntityMappingError("unresolved candidate requires rejection_reason_codes")


def _candidate_semantic_bytes(candidate: EntityCandidateV1) -> bytes:
    return canonical_json_bytes(_candidate_payload(candidate))


def _candidate_payload(candidate: EntityCandidateV1) -> dict[str, Any]:
    payload = candidate.to_mapping()
    payload["rejection_reason_codes"] = list(candidate.rejection_reason_codes)
    return payload


def _freeze_candidates(value: Any) -> tuple[EntityCandidateV1, ...]:
    if isinstance(value, (str, bytes)):
        raise NewsEntityMappingError("candidates must be a collection")
    try:
        candidates = tuple(value)
    except TypeError as exc:
        raise NewsEntityMappingError("candidates must be a collection") from exc
    if any(type(candidate) is not EntityCandidateV1 for candidate in candidates):
        raise NewsEntityMappingError("candidates must contain EntityCandidateV1")
    return candidates


def _validate_candidate_snapshot(candidate: EntityCandidateV1, event_snapshot_id: str) -> None:
    if any(ref["event_snapshot_id"] != event_snapshot_id for ref in candidate.evidence_refs):
        raise NewsEntityMappingError("candidate evidence does not match event_snapshot_id")


def _deduplicate_candidates(
    candidates: tuple[EntityCandidateV1, ...]
) -> tuple[EntityCandidateV1, ...]:
    unique: dict[bytes, EntityCandidateV1] = {}
    for candidate in candidates:
        unique.setdefault(_candidate_semantic_bytes(candidate), candidate)
    return tuple(sorted(unique.values(), key=_candidate_sort_key))


def _candidate_sort_key(candidate: EntityCandidateV1) -> tuple[str, str, str, str]:
    return (
        candidate.candidate_status,
        candidate.entity_type,
        candidate.canonical_entity_id,
        candidate.candidate_id,
    )


def _validate_resolutions(
    value: Any, candidates: tuple[EntityCandidateV1, ...]
) -> Mapping[str, str]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise NewsEntityMappingError("resolver_selections must be a mapping")
    groups: dict[str, set[str]] = {}
    for candidate in candidates:
        if candidate.candidate_status == "AMBIGUOUS":
            groups.setdefault(candidate.ambiguity_group_id or "", set()).add(
                candidate.candidate_id
            )
    selections: dict[str, str] = {}
    for group, candidate_id in value.items():
        group = _require_identifier(group, "resolver group")
        candidate_id = _require_candidate_id(candidate_id)
        if group not in groups:
            raise NewsEntityMappingError("resolver group is unknown")
        if candidate_id not in groups[group]:
            raise NewsEntityMappingError("resolver candidate is unknown")
        selections[group] = candidate_id
    return MappingProxyType(dict(sorted(selections.items())))


def _apply_selection(
    candidate: EntityCandidateV1, selections: Mapping[str, str]
) -> EntityCandidateV1:
    if (
        candidate.candidate_status != "AMBIGUOUS"
        or candidate.ambiguity_group_id not in selections
        or selections[candidate.ambiguity_group_id] != candidate.candidate_id
    ):
        return candidate
    values = candidate.to_mapping()
    values["candidate_status"] = "ACCEPTED"
    values["ambiguity_group_id"] = None
    values["rejection_reason_codes"] = ()
    return EntityCandidateV1(**values)


def _validate_ambiguity_groups(candidates: tuple[EntityCandidateV1, ...]) -> None:
    groups: dict[str, set[bytes]] = {}
    for candidate in candidates:
        if candidate.candidate_status == "AMBIGUOUS":
            group = candidate.ambiguity_group_id or ""
            groups.setdefault(group, set()).add(_candidate_semantic_bytes(candidate))
    if any(len(members) < 2 for members in groups.values()):
        raise NewsEntityMappingError("ambiguity_group_id requires distinct candidates")


def _as_rejected(candidate: EntityCandidateV1, reason: str) -> EntityCandidateV1:
    values = candidate.to_mapping()
    values["candidate_status"] = "REJECTED"
    values["ambiguity_group_id"] = None
    values["rejection_reason_codes"] = (reason,)
    return EntityCandidateV1(**values)


def _mapping_status(
    accepted: tuple[EntityCandidateV1, ...],
    rejected: tuple[EntityCandidateV1, ...],
    ambiguous: tuple[EntityCandidateV1, ...],
    unresolved: tuple[EntityCandidateV1, ...],
) -> str:
    if accepted and (ambiguous or unresolved):
        return "PARTIALLY_RESOLVED"
    if accepted:
        return "RESOLVED"
    if ambiguous:
        return "AMBIGUOUS"
    return "UNRESOLVED"


def _freeze_partition(value: Any, expected_status: str) -> tuple[EntityCandidateV1, ...]:
    candidates = _freeze_candidates(value)
    if any(candidate.candidate_status != expected_status for candidate in candidates):
        raise NewsEntityMappingError("candidate partition does not match candidate_status")
    return tuple(sorted(candidates, key=_candidate_sort_key))


def _validate_partitions(
    accepted: tuple[EntityCandidateV1, ...],
    rejected: tuple[EntityCandidateV1, ...],
    ambiguous: tuple[EntityCandidateV1, ...],
    unresolved: tuple[EntityCandidateV1, ...],
) -> None:
    fingerprints: set[bytes] = set()
    for partition in (accepted, rejected, ambiguous, unresolved):
        for candidate in partition:
            fingerprint = _candidate_semantic_bytes(candidate)
            if fingerprint in fingerprints:
                raise NewsEntityMappingError("candidate appears in multiple partitions")
            fingerprints.add(fingerprint)


def _normalize_result_reasons(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise NewsEntityMappingError("reason_codes must be a collection")
    try:
        reasons = tuple(value)
    except TypeError as exc:
        raise NewsEntityMappingError("reason_codes must be a collection") from exc
    if any(type(reason) is not str or reason not in _RESULT_REASONS for reason in reasons):
        raise NewsEntityMappingError("invalid reason_codes")
    priority = _REJECTION_SEQUENCE + tuple(sorted(_SOURCE_REASONS))
    supplied = set(reasons)
    return tuple(reason for reason in priority if reason in supplied)


def _validate_mapping_state(
    mapping_status: str,
    source_policy: SourcePolicyDecisionV1,
    accepted: tuple[EntityCandidateV1, ...],
    rejected: tuple[EntityCandidateV1, ...],
    ambiguous: tuple[EntityCandidateV1, ...],
    unresolved: tuple[EntityCandidateV1, ...],
) -> None:
    if source_policy.decision != "ELIGIBLE" and accepted:
        raise NewsEntityMappingError("source policy cannot permit accepted candidates")
    if mapping_status == "RESOLVED" and (not accepted or ambiguous or unresolved):
        raise NewsEntityMappingError("resolved mapping has inconsistent partitions")
    if mapping_status == "PARTIALLY_RESOLVED" and (not accepted or not (ambiguous or unresolved)):
        raise NewsEntityMappingError("partial mapping has inconsistent partitions")
    if mapping_status == "AMBIGUOUS" and not ambiguous:
        raise NewsEntityMappingError("ambiguous mapping requires ambiguous candidates")
    if mapping_status == "BLOCKED" and source_policy.decision != "BLOCKED":
        raise NewsEntityMappingError("blocked mapping requires blocked source policy")
    if mapping_status == "INVALID" and source_policy.decision != "INVALID":
        raise NewsEntityMappingError("invalid mapping requires invalid source policy")
    if mapping_status == "UNRESOLVED" and accepted:
        raise NewsEntityMappingError("unresolved mapping cannot have accepted candidates")


def _build_mapping_result_id(
    *,
    event_snapshot_id: str,
    source_policy_decision: SourcePolicyDecisionV1,
    accepted_candidates: tuple[EntityCandidateV1, ...],
    rejected_candidates: tuple[EntityCandidateV1, ...],
    ambiguous_candidates: tuple[EntityCandidateV1, ...],
    unresolved_candidates: tuple[EntityCandidateV1, ...],
    mapping_status: str,
    reason_codes: tuple[str, ...],
) -> str:
    payload = {
        "event_snapshot_id": event_snapshot_id,
        "mapping_policy_version": ENTITY_MAPPING_POLICY_VERSION,
        "source_policy_decision": _source_policy_payload(source_policy_decision),
        "accepted_candidates": [_candidate_payload(item) for item in accepted_candidates],
        "rejected_candidates": [_candidate_payload(item) for item in rejected_candidates],
        "ambiguous_candidates": [_candidate_payload(item) for item in ambiguous_candidates],
        "unresolved_candidates": [_candidate_payload(item) for item in unresolved_candidates],
        "mapping_status": mapping_status,
        "reason_codes": list(reason_codes),
    }
    return sha256_hex(canonical_json_bytes(payload))


def _source_policy_payload(decision: SourcePolicyDecisionV1) -> dict[str, Any]:
    payload = decision.to_mapping()
    payload["reason_codes"] = list(decision.reason_codes)
    return payload
