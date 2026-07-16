"""Pure deterministic News Risk Object contracts and mapping tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from engine.deterministic_adjudication_v1 import DeterministicAdjudicationResultV1
from engine.news_event_contract_v1 import canonical_json_bytes, sha256_hex


NEWS_RISK_POLICY_VERSION = "news-risk-policy-v1"

__all__ = (
    "NewsRiskObjectError",
    "NEWS_RISK_POLICY_VERSION",
    "NewsRiskPolicyV1",
    "NewsRiskObjectV1",
    "build_news_risk_object",
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_ROUTES = ("L0", "L1", "L2")
_OUTCOMES = frozenset(
    (
        "ACCEPT_DEEPSEEK",
        "ACCEPT_CLAUDE",
        "CONSENSUS_CONFIRMED",
        "CONSENSUS_WITH_QUALIFICATION",
        "MATERIAL_DISAGREEMENT",
        "INSUFFICIENT_EVIDENCE",
        "FAIL_CLOSED",
    )
)
_AGREEMENTS = frozenset(
    (
        "SINGLE_REVIEW",
        "AGREEMENT",
        "QUALIFIED_AGREEMENT",
        "DISAGREEMENT",
        "CRITICAL_DISAGREEMENT",
        "FAIL_CLOSED",
    )
)
_AMBIGUITY = frozenset(("NONE", "MODERATE", "CRITICAL"))
_CONTRADICTIONS = frozenset(("NONE", "PRESENT", "RESOLVED", "UNRESOLVED"))
_EVIDENCE = frozenset(("SUFFICIENT", "INSUFFICIENT"))
_ASSESSMENTS = frozenset(("ACCEPTABLE", "MODERATE", "CRITICAL"))
_RISKS = frozenset(("NONE", "MATERIAL_RISK"))
_CLASSIFICATIONS = frozenset(("CLEAR", "CAUTION", "ELEVATED", "BLOCKING", "FAIL_CLOSED"))
_RECOMMENDATIONS = frozenset(("NO_NEWS_RESTRICTION", "REQUIRE_CAUTION", "REQUIRE_BLOCK", "FAIL_CLOSED"))
_RECOMMENDATION_BY_CLASSIFICATION = {
    "CLEAR": "NO_NEWS_RESTRICTION",
    "CAUTION": "REQUIRE_CAUTION",
    "ELEVATED": "REQUIRE_CAUTION",
    "BLOCKING": "REQUIRE_BLOCK",
    "FAIL_CLOSED": "FAIL_CLOSED",
}
_ADJUDICATION_REASON_CODES = frozenset(
    (
        "PROVIDERS_AGREE",
        "MATERIAL_FACTS_ALIGNED",
        "RISK_ASSESSMENTS_ALIGNED",
        "MINOR_EVIDENCE_DIFFERENCE",
        "MODERATE_ENTITY_DIFFERENCE",
        "MODERATE_SOURCE_DIFFERENCE",
        "MATERIAL_RISK_DISAGREEMENT",
        "CONTRADICTION_DISAGREEMENT",
        "EVIDENCE_DISAGREEMENT",
        "ENTITY_DISAGREEMENT",
        "SOURCE_DISAGREEMENT",
        "INVALID_INPUT",
        "RESULT_NOT_COMPLETED",
        "ROUTE_RESULT_MISMATCH",
        "EVENT_BINDING_MISMATCH",
        "DECISION_BINDING_MISMATCH",
        "POLICY_MISMATCH",
        "CRITICAL_UNRESOLVED_DISAGREEMENT",
    )
)
_RISK_REASON_CODES = frozenset(
    (
        "ADJUDICATION_CONFIRMED",
        "NO_MATERIAL_NEWS_RISK",
        "EVIDENCE_SUFFICIENT",
        "QUALIFIED_ADJUDICATION",
        "EVIDENCE_LIMITED",
        "MODERATE_ENTITY_CONCERN",
        "MODERATE_SOURCE_CONCERN",
        "MATERIAL_DISAGREEMENT",
        "UNRESOLVED_CONTRADICTION",
        "MATERIAL_RISK_PRESENT",
        "INSUFFICIENT_EVIDENCE",
        "CRITICAL_MATERIAL_RISK",
        "CRITICAL_CONTRADICTION",
        "CRITICAL_ENTITY_CONCERN",
        "CRITICAL_SOURCE_CONCERN",
        "BLOCKING_ADJUDICATION_REASON",
        "INVALID_ADJUDICATION",
        "UNSUPPORTED_POLICY",
        "FORGED_IDENTITY",
        "FAIL_CLOSED_ADJUDICATION",
    )
)
_POLICY_FIELDS = frozenset(
    (
        "policy_version",
        "supported_adjudication_policy_versions",
        "supported_routes",
        "outcome_to_risk_classification",
        "ambiguity_precedence",
        "contradiction_precedence",
        "evidence_precedence",
        "entity_precedence",
        "source_precedence",
        "material_risk_precedence",
        "fail_closed_outcomes",
        "blocking_reason_codes",
        "caution_reason_codes",
        "deterministic_reason_order",
        "maximum_reason_code_count",
        "maximum_evidence_reference_count",
    )
)
_RESULT_FIELDS = frozenset(
    (
        "policy_version",
        "event_snapshot_id",
        "adjudication_policy_version",
        "adjudication_result_id",
        "route",
        "risk_classification",
        "news_gate_recommendation",
        "final_ambiguity_state",
        "final_contradiction_state",
        "final_evidence_state",
        "final_entity_state",
        "final_source_state",
        "final_material_risk_state",
        "reason_codes",
        "evidence_refs",
        "structured_explanation",
        "news_risk_object_id",
    )
)


class NewsRiskObjectError(ValueError):
    """Raised when News Risk semantic inputs or contracts are invalid."""


def _require_exact_fields(values: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(values) != expected:
        raise NewsRiskObjectError(f"invalid {label} fields")


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise NewsRiskObjectError(f"invalid {label}")
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise NewsRiskObjectError(f"invalid {label}")
    return value


def _require_text(value: Any, label: str) -> str:
    if type(value) is not str or not value or len(value) > 1000:
        raise NewsRiskObjectError(f"invalid {label}")
    return value


def _require_positive_integer(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise NewsRiskObjectError(f"invalid {label}")
    return value


def _require_choice(value: Any, label: str, allowed: frozenset[str]) -> str:
    if type(value) is not str or value not in allowed:
        raise NewsRiskObjectError(f"invalid {label}")
    return value


def _normalize_choices(value: Any, label: str, allowed: frozenset[str], *, sort: bool = True) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise NewsRiskObjectError(f"invalid {label}")
    result: list[str] = []
    for item in value:
        if type(item) is not str or item not in allowed:
            raise NewsRiskObjectError(f"invalid {label}")
        if item not in result:
            result.append(item)
    return tuple(sorted(result)) if sort else tuple(result)


def _normalize_identifiers(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise NewsRiskObjectError(f"invalid {label}")
    return tuple(sorted({_require_identifier(item, label) for item in value}))


def _normalize_mapping(value: Any) -> tuple[tuple[str, str], ...]:
    if type(value) is not dict:
        raise NewsRiskObjectError("invalid outcome_to_risk_classification")
    if set(value) != _OUTCOMES:
        raise NewsRiskObjectError("invalid outcome_to_risk_classification")
    items: list[tuple[str, str]] = []
    for outcome in sorted(_OUTCOMES):
        classification = value[outcome]
        if type(classification) is not str or classification not in _CLASSIFICATIONS:
            raise NewsRiskObjectError("invalid outcome_to_risk_classification")
        items.append((outcome, classification))
    if dict(items).get("FAIL_CLOSED") != "FAIL_CLOSED":
        raise NewsRiskObjectError("invalid fail_closed mapping")
    return tuple(items)


def _hash_mapping(value: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(value))


@dataclass(frozen=True, init=False)
class NewsRiskPolicyV1:
    policy_version: str
    supported_adjudication_policy_versions: tuple[str, ...]
    supported_routes: tuple[str, ...]
    outcome_to_risk_classification: tuple[tuple[str, str], ...]
    ambiguity_precedence: tuple[str, ...]
    contradiction_precedence: tuple[str, ...]
    evidence_precedence: tuple[str, ...]
    entity_precedence: tuple[str, ...]
    source_precedence: tuple[str, ...]
    material_risk_precedence: tuple[str, ...]
    fail_closed_outcomes: tuple[str, ...]
    blocking_reason_codes: tuple[str, ...]
    caution_reason_codes: tuple[str, ...]
    deterministic_reason_order: tuple[str, ...]
    maximum_reason_code_count: int
    maximum_evidence_reference_count: int

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _POLICY_FIELDS, "policy")
        if values["policy_version"] != NEWS_RISK_POLICY_VERSION:
            raise NewsRiskObjectError("invalid policy_version")
        versions = _normalize_choices(
            values["supported_adjudication_policy_versions"],
            "supported_adjudication_policy_versions",
            frozenset(("deterministic-adjudication-policy-v1",)),
        )
        if versions != ("deterministic-adjudication-policy-v1",):
            raise NewsRiskObjectError("invalid supported_adjudication_policy_versions")
        routes = _normalize_choices(values["supported_routes"], "supported_routes", frozenset(_ROUTES))
        if routes != _ROUTES:
            raise NewsRiskObjectError("invalid supported_routes")
        mapping = _normalize_mapping(values["outcome_to_risk_classification"])
        ambiguity = _normalize_choices(values["ambiguity_precedence"], "ambiguity_precedence", _AMBIGUITY, sort=False)
        contradiction = _normalize_choices(values["contradiction_precedence"], "contradiction_precedence", _CONTRADICTIONS, sort=False)
        evidence = _normalize_choices(values["evidence_precedence"], "evidence_precedence", _EVIDENCE, sort=False)
        entity = _normalize_choices(values["entity_precedence"], "entity_precedence", _ASSESSMENTS, sort=False)
        source = _normalize_choices(values["source_precedence"], "source_precedence", _ASSESSMENTS, sort=False)
        risk = _normalize_choices(values["material_risk_precedence"], "material_risk_precedence", _RISKS, sort=False)
        if set(ambiguity) != _AMBIGUITY or set(contradiction) != _CONTRADICTIONS or set(evidence) != _EVIDENCE:
            raise NewsRiskObjectError("invalid policy precedence")
        if set(entity) != _ASSESSMENTS or set(source) != _ASSESSMENTS or set(risk) != _RISKS:
            raise NewsRiskObjectError("invalid policy precedence")
        failed = _normalize_choices(values["fail_closed_outcomes"], "fail_closed_outcomes", _OUTCOMES)
        if failed != ("FAIL_CLOSED",):
            raise NewsRiskObjectError("invalid fail_closed_outcomes")
        blocking = _normalize_choices(
            values["blocking_reason_codes"],
            "blocking_reason_codes",
            _RISK_REASON_CODES | _ADJUDICATION_REASON_CODES,
            sort=False,
        )
        caution = _normalize_choices(values["caution_reason_codes"], "caution_reason_codes", _RISK_REASON_CODES, sort=False)
        order = _normalize_choices(values["deterministic_reason_order"], "deterministic_reason_order", _RISK_REASON_CODES, sort=False)
        if not order or any(code not in order for code in _RISK_REASON_CODES):
            raise NewsRiskObjectError("invalid deterministic_reason_order")
        maximum_reasons = _require_positive_integer(values["maximum_reason_code_count"], "maximum_reason_code_count")
        maximum_refs = _require_positive_integer(values["maximum_evidence_reference_count"], "maximum_evidence_reference_count")
        if maximum_reasons > len(_RISK_REASON_CODES) or maximum_refs > 128:
            raise NewsRiskObjectError("invalid policy limits")
        object.__setattr__(self, "policy_version", NEWS_RISK_POLICY_VERSION)
        object.__setattr__(self, "supported_adjudication_policy_versions", versions)
        object.__setattr__(self, "supported_routes", routes)
        object.__setattr__(self, "outcome_to_risk_classification", mapping)
        object.__setattr__(self, "ambiguity_precedence", ambiguity)
        object.__setattr__(self, "contradiction_precedence", contradiction)
        object.__setattr__(self, "evidence_precedence", evidence)
        object.__setattr__(self, "entity_precedence", entity)
        object.__setattr__(self, "source_precedence", source)
        object.__setattr__(self, "material_risk_precedence", risk)
        object.__setattr__(self, "fail_closed_outcomes", failed)
        object.__setattr__(self, "blocking_reason_codes", blocking)
        object.__setattr__(self, "caution_reason_codes", caution)
        object.__setattr__(self, "deterministic_reason_order", order)
        object.__setattr__(self, "maximum_reason_code_count", maximum_reasons)
        object.__setattr__(self, "maximum_evidence_reference_count", maximum_refs)


def _risk_identity(values: Mapping[str, Any]) -> str:
    return _hash_mapping(
        {
            "policy_version": values["policy_version"],
            "event_snapshot_id": values["event_snapshot_id"],
            "adjudication_policy_version": values["adjudication_policy_version"],
            "adjudication_result_id": values["adjudication_result_id"],
            "route": values["route"],
            "risk_classification": values["risk_classification"],
            "news_gate_recommendation": values["news_gate_recommendation"],
            "final_ambiguity_state": values["final_ambiguity_state"],
            "final_contradiction_state": values["final_contradiction_state"],
            "final_evidence_state": values["final_evidence_state"],
            "final_entity_state": values["final_entity_state"],
            "final_source_state": values["final_source_state"],
            "final_material_risk_state": values["final_material_risk_state"],
            "reason_codes": list(values["reason_codes"]),
            "evidence_refs": list(values["evidence_refs"]),
        }
    )


@dataclass(frozen=True, init=False)
class NewsRiskObjectV1:
    policy_version: str
    event_snapshot_id: str
    adjudication_policy_version: str
    adjudication_result_id: str
    route: str
    risk_classification: str
    news_gate_recommendation: str
    final_ambiguity_state: str
    final_contradiction_state: str
    final_evidence_state: str
    final_entity_state: str
    final_source_state: str
    final_material_risk_state: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    structured_explanation: str
    news_risk_object_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RESULT_FIELDS, "News Risk object")
        if values["policy_version"] != NEWS_RISK_POLICY_VERSION:
            raise NewsRiskObjectError("invalid policy_version")
        classification = _require_choice(values["risk_classification"], "risk_classification", _CLASSIFICATIONS)
        recommendation = _require_choice(values["news_gate_recommendation"], "news_gate_recommendation", _RECOMMENDATIONS)
        if recommendation != _RECOMMENDATION_BY_CLASSIFICATION[classification]:
            raise NewsRiskObjectError("invalid news_gate_recommendation")
        canonical = {
            "policy_version": NEWS_RISK_POLICY_VERSION,
            "event_snapshot_id": _require_hash(values["event_snapshot_id"], "event_snapshot_id"),
            "adjudication_policy_version": _require_text(values["adjudication_policy_version"], "adjudication_policy_version"),
            "adjudication_result_id": _require_hash(values["adjudication_result_id"], "adjudication_result_id"),
            "route": _require_choice(values["route"], "route", frozenset(_ROUTES)),
            "risk_classification": classification,
            "news_gate_recommendation": recommendation,
            "final_ambiguity_state": _require_choice(values["final_ambiguity_state"], "final_ambiguity_state", _AMBIGUITY),
            "final_contradiction_state": _require_choice(values["final_contradiction_state"], "final_contradiction_state", _CONTRADICTIONS),
            "final_evidence_state": _require_choice(values["final_evidence_state"], "final_evidence_state", _EVIDENCE),
            "final_entity_state": _require_choice(values["final_entity_state"], "final_entity_state", _ASSESSMENTS),
            "final_source_state": _require_choice(values["final_source_state"], "final_source_state", _ASSESSMENTS),
            "final_material_risk_state": _require_choice(values["final_material_risk_state"], "final_material_risk_state", _RISKS),
            "reason_codes": _normalize_choices(values["reason_codes"], "reason_codes", _RISK_REASON_CODES),
            "evidence_refs": _normalize_identifiers(values["evidence_refs"], "evidence_refs"),
            "structured_explanation": _require_text(values["structured_explanation"], "structured_explanation"),
        }
        if not canonical["reason_codes"] or not canonical["evidence_refs"]:
            raise NewsRiskObjectError("missing semantic fields")
        object_id = _risk_identity(canonical)
        supplied = values["news_risk_object_id"]
        if supplied is not None and supplied != object_id:
            raise NewsRiskObjectError("invalid news_risk_object_id")
        for name, value in canonical.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "news_risk_object_id", object_id)


def _adjudication_identity(values: Mapping[str, Any]) -> str:
    return _hash_mapping(
        {
            "policy_version": values["policy_version"],
            "event_snapshot_id": values["event_snapshot_id"],
            "route": values["route"],
            "router_decision_id": values["router_decision_id"],
            "deepseek_semantic_result_id": values["deepseek_semantic_result_id"],
            "claude_semantic_result_id": values["claude_semantic_result_id"],
            "adjudication_outcome": values["adjudication_outcome"],
            "agreement_state": values["agreement_state"],
            "final_ambiguity_state": values["final_ambiguity_state"],
            "final_contradiction_state": values["final_contradiction_state"],
            "final_evidence_state": values["final_evidence_state"],
            "final_entity_state": values["final_entity_state"],
            "final_source_state": values["final_source_state"],
            "final_material_risk_state": values["final_material_risk_state"],
            "reason_codes": list(values["reason_codes"]),
            "evidence_refs": list(values["evidence_refs"]),
        }
    )


def _validate_adjudication(result: DeterministicAdjudicationResultV1, policy: NewsRiskPolicyV1) -> dict[str, Any]:
    if result.policy_version not in policy.supported_adjudication_policy_versions:
        raise NewsRiskObjectError("unsupported adjudication policy")
    values = {name: getattr(result, name) for name in result.__dataclass_fields__}
    if _adjudication_identity(values) != result.adjudication_result_id:
        raise NewsRiskObjectError("invalid adjudication identity")
    route = _require_choice(result.route, "adjudication route", frozenset(policy.supported_routes))
    outcome = _require_choice(result.adjudication_outcome, "adjudication outcome", _OUTCOMES)
    agreement = _require_choice(result.agreement_state, "adjudication agreement", _AGREEMENTS)
    if route == "L0":
        if outcome != "ACCEPT_DEEPSEEK" or agreement != "SINGLE_REVIEW" or result.claude_semantic_result_id is not None:
            raise NewsRiskObjectError("invalid L0 adjudication")
    elif result.claude_semantic_result_id is None:
        raise NewsRiskObjectError("invalid escalated adjudication")
    return {
        "event": _require_hash(result.event_snapshot_id, "adjudication event_snapshot_id"),
        "policy_version": result.policy_version,
        "result_id": _require_hash(result.adjudication_result_id, "adjudication_result_id"),
        "route": route,
        "outcome": outcome,
        "agreement": agreement,
        "ambiguity": _require_choice(result.final_ambiguity_state, "final_ambiguity_state", _AMBIGUITY),
        "contradiction": _require_choice(result.final_contradiction_state, "final_contradiction_state", _CONTRADICTIONS),
        "evidence": _require_choice(result.final_evidence_state, "final_evidence_state", _EVIDENCE),
        "entity": _require_choice(result.final_entity_state, "final_entity_state", _ASSESSMENTS),
        "source": _require_choice(result.final_source_state, "final_source_state", _ASSESSMENTS),
        "risk": _require_choice(result.final_material_risk_state, "final_material_risk_state", _RISKS),
        "reasons": _normalize_choices(result.reason_codes, "adjudication reason_codes", _ADJUDICATION_REASON_CODES),
        "refs": _normalize_identifiers(result.evidence_refs, "adjudication evidence_refs"),
    }


def _canonical_reasons(codes: set[str], policy: NewsRiskPolicyV1) -> tuple[str, ...]:
    reasons = tuple(code for code in policy.deterministic_reason_order if code in codes)
    if not reasons or len(reasons) > policy.maximum_reason_code_count:
        raise NewsRiskObjectError("invalid News Risk reason_codes")
    return reasons


def _classification_from_outcome(outcome: str, policy: NewsRiskPolicyV1) -> str:
    return dict(policy.outcome_to_risk_classification)[outcome]


def _build_result(*, policy: NewsRiskPolicyV1, data: dict[str, Any], classification: str, reasons: set[str]) -> NewsRiskObjectV1:
    recommendation = _RECOMMENDATION_BY_CLASSIFICATION[classification]
    return NewsRiskObjectV1(
        policy_version=NEWS_RISK_POLICY_VERSION,
        event_snapshot_id=data["event"],
        adjudication_policy_version=data["policy_version"],
        adjudication_result_id=data["result_id"],
        route=data["route"],
        risk_classification=classification,
        news_gate_recommendation=recommendation,
        final_ambiguity_state=data["ambiguity"],
        final_contradiction_state=data["contradiction"],
        final_evidence_state=data["evidence"],
        final_entity_state=data["entity"],
        final_source_state=data["source"],
        final_material_risk_state=data["risk"],
        reason_codes=_canonical_reasons(reasons, policy),
        evidence_refs=data["refs"],
        structured_explanation="news-risk:" + classification,
        news_risk_object_id=None,
    )


def build_news_risk_object(adjudication_result: Any, policy: Any) -> NewsRiskObjectV1:
    """Build one immutable News Risk semantic object from adjudication only."""

    if type(adjudication_result) is not DeterministicAdjudicationResultV1:
        raise NewsRiskObjectError("invalid adjudication result type")
    if type(policy) is not NewsRiskPolicyV1:
        raise NewsRiskObjectError("invalid policy type")
    data = _validate_adjudication(adjudication_result, policy)
    if len(data["refs"]) > policy.maximum_evidence_reference_count:
        raise NewsRiskObjectError("too many evidence references")

    if data["outcome"] in policy.fail_closed_outcomes:
        return _build_result(policy=policy, data=data, classification="FAIL_CLOSED", reasons={"FAIL_CLOSED_ADJUDICATION"})

    blocking = set(data["reasons"]).intersection(policy.blocking_reason_codes)
    if data["risk"] == "MATERIAL_RISK" and "MATERIAL_RISK_DISAGREEMENT" in blocking:
        return _build_result(policy=policy, data=data, classification="BLOCKING", reasons={"CRITICAL_MATERIAL_RISK"})
    if data["contradiction"] == "UNRESOLVED" and "CONTRADICTION_DISAGREEMENT" in blocking:
        return _build_result(policy=policy, data=data, classification="BLOCKING", reasons={"CRITICAL_CONTRADICTION"})
    if data["entity"] == "CRITICAL":
        return _build_result(policy=policy, data=data, classification="BLOCKING", reasons={"CRITICAL_ENTITY_CONCERN"})
    if data["source"] == "CRITICAL":
        return _build_result(policy=policy, data=data, classification="BLOCKING", reasons={"CRITICAL_SOURCE_CONCERN"})
    if blocking:
        return _build_result(policy=policy, data=data, classification="BLOCKING", reasons={"BLOCKING_ADJUDICATION_REASON"})
    if data["risk"] == "MATERIAL_RISK":
        return _build_result(policy=policy, data=data, classification="ELEVATED", reasons={"MATERIAL_RISK_PRESENT"})
    if data["contradiction"] == "UNRESOLVED":
        return _build_result(policy=policy, data=data, classification="ELEVATED", reasons={"UNRESOLVED_CONTRADICTION"})
    if data["entity"] == "MODERATE":
        return _build_result(policy=policy, data=data, classification="CAUTION", reasons={"MODERATE_ENTITY_CONCERN"})
    if data["source"] == "MODERATE":
        return _build_result(policy=policy, data=data, classification="CAUTION", reasons={"MODERATE_SOURCE_CONCERN"})
    if data["evidence"] == "INSUFFICIENT":
        return _build_result(policy=policy, data=data, classification="CAUTION", reasons={"INSUFFICIENT_EVIDENCE"})

    classification = _classification_from_outcome(data["outcome"], policy)
    if classification == "FAIL_CLOSED":
        return _build_result(policy=policy, data=data, classification=classification, reasons={"FAIL_CLOSED_ADJUDICATION"})
    if classification == "ELEVATED":
        return _build_result(policy=policy, data=data, classification=classification, reasons={"MATERIAL_DISAGREEMENT"})
    if classification == "CAUTION":
        return _build_result(policy=policy, data=data, classification=classification, reasons={"QUALIFIED_ADJUDICATION"})
    return _build_result(
        policy=policy,
        data=data,
        classification="CLEAR",
        reasons={"ADJUDICATION_CONFIRMED", "NO_MATERIAL_NEWS_RISK", "EVIDENCE_SUFFICIENT"},
    )
