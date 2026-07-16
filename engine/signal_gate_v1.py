"""Pure deterministic Signal Gate contracts and mapping tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from engine.news_event_contract_v1 import canonical_json_bytes, sha256_hex
from engine.news_risk_object_v1 import NewsRiskObjectV1


SIGNAL_GATE_POLICY_VERSION = "signal-gate-policy-v1"

__all__ = (
    "SignalGateError",
    "SIGNAL_GATE_POLICY_VERSION",
    "SignalGatePolicyV1",
    "SignalGateDecisionV1",
    "evaluate_signal_gate",
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_ROUTES = ("L0", "L1", "L2")
_RISK_CLASSES = frozenset(("CLEAR", "CAUTION", "ELEVATED", "BLOCKING", "FAIL_CLOSED"))
_NEWS_RECOMMENDATIONS = frozenset(("NO_NEWS_RESTRICTION", "REQUIRE_CAUTION", "REQUIRE_BLOCK", "FAIL_CLOSED"))
_GATE_STATES = frozenset(("OPEN", "CAUTION", "BLOCKED", "FAIL_CLOSED"))
_ELIGIBILITY = frozenset(("ALLOW_NEWS_ELIGIBILITY", "REQUIRE_NEWS_CAUTION", "DENY_NEWS_ELIGIBILITY", "FAIL_CLOSED"))
_ELIGIBILITY_BY_STATE = {
    "OPEN": "ALLOW_NEWS_ELIGIBILITY",
    "CAUTION": "REQUIRE_NEWS_CAUTION",
    "BLOCKED": "DENY_NEWS_ELIGIBILITY",
    "FAIL_CLOSED": "FAIL_CLOSED",
}
_AMBIGUITY = frozenset(("NONE", "MODERATE", "CRITICAL"))
_CONTRADICTIONS = frozenset(("NONE", "PRESENT", "RESOLVED", "UNRESOLVED"))
_EVIDENCE = frozenset(("SUFFICIENT", "INSUFFICIENT"))
_ASSESSMENTS = frozenset(("ACCEPTABLE", "MODERATE", "CRITICAL"))
_RISKS = frozenset(("NONE", "MATERIAL_RISK"))
_NEWS_RISK_REASON_CODES = frozenset(
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
_GATE_REASON_CODES = frozenset(
    (
        "NEWS_RISK_CLEAR",
        "NO_NEWS_RESTRICTION",
        "NEWS_RISK_CAUTION",
        "CAUTION_RECOMMENDED",
        "LIMITED_EVIDENCE",
        "QUALIFIED_NEWS_ASSESSMENT",
        "NEWS_RISK_ELEVATED",
        "NEWS_RISK_BLOCKING",
        "BLOCK_RECOMMENDED",
        "CRITICAL_MATERIAL_RISK",
        "CRITICAL_CONTRADICTION",
        "CRITICAL_ENTITY_CONCERN",
        "CRITICAL_SOURCE_CONCERN",
        "BLOCKING_NEWS_REASON",
        "INVALID_NEWS_RISK_OBJECT",
        "UNSUPPORTED_POLICY",
        "FORGED_NEWS_RISK_IDENTITY",
        "FAIL_CLOSED_NEWS_RISK",
        "FAIL_CLOSED_GATE_POLICY",
    )
)
_POLICY_FIELDS = frozenset(
    (
        "policy_version",
        "supported_news_risk_policy_versions",
        "supported_routes",
        "supported_risk_classifications",
        "supported_news_gate_recommendations",
        "risk_to_gate_state",
        "recommendation_to_gate_state",
        "blocking_reason_codes",
        "caution_reason_codes",
        "fail_closed_reason_codes",
        "deterministic_reason_order",
        "maximum_reason_code_count",
        "maximum_evidence_reference_count",
    )
)
_DECISION_FIELDS = frozenset(
    (
        "policy_version",
        "event_snapshot_id",
        "news_risk_policy_version",
        "news_risk_object_id",
        "route",
        "gate_state",
        "eligibility_recommendation",
        "risk_classification",
        "news_gate_recommendation",
        "reason_codes",
        "evidence_refs",
        "structured_explanation",
        "signal_gate_decision_id",
    )
)
_RISK_MAPPING = {
    "CLEAR": "OPEN",
    "CAUTION": "CAUTION",
    "ELEVATED": "BLOCKED",
    "BLOCKING": "BLOCKED",
    "FAIL_CLOSED": "FAIL_CLOSED",
}
_RECOMMENDATION_MAPPING = {
    "NO_NEWS_RESTRICTION": "OPEN",
    "REQUIRE_CAUTION": "CAUTION",
    "REQUIRE_BLOCK": "BLOCKED",
    "FAIL_CLOSED": "FAIL_CLOSED",
}


class SignalGateError(ValueError):
    """Raised when deterministic Signal Gate contracts are invalid."""


def _require_exact_fields(values: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(values) != expected:
        raise SignalGateError(f"invalid {label} fields")


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise SignalGateError(f"invalid {label}")
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise SignalGateError(f"invalid {label}")
    return value


def _require_text(value: Any, label: str) -> str:
    if type(value) is not str or not value or len(value) > 1000:
        raise SignalGateError(f"invalid {label}")
    return value


def _require_positive_integer(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise SignalGateError(f"invalid {label}")
    return value


def _require_choice(value: Any, label: str, allowed: frozenset[str]) -> str:
    if type(value) is not str or value not in allowed:
        raise SignalGateError(f"invalid {label}")
    return value


def _normalize_choices(value: Any, label: str, allowed: frozenset[str], *, sort: bool = True) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise SignalGateError(f"invalid {label}")
    result: list[str] = []
    for item in value:
        if type(item) is not str or item not in allowed:
            raise SignalGateError(f"invalid {label}")
        if item not in result:
            result.append(item)
    return tuple(sorted(result)) if sort else tuple(result)


def _normalize_identifiers(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise SignalGateError(f"invalid {label}")
    return tuple(sorted({_require_identifier(item, label) for item in value}))


def _normalize_mapping(value: Any, expected: Mapping[str, str], label: str) -> tuple[tuple[str, str], ...]:
    if type(value) is not dict or set(value) != set(expected):
        raise SignalGateError(f"invalid {label}")
    for key, expected_value in expected.items():
        if value[key] != expected_value:
            raise SignalGateError(f"invalid {label}")
    return tuple(sorted(expected.items()))


def _hash_mapping(value: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(value))


@dataclass(frozen=True, init=False)
class SignalGatePolicyV1:
    policy_version: str
    supported_news_risk_policy_versions: tuple[str, ...]
    supported_routes: tuple[str, ...]
    supported_risk_classifications: tuple[str, ...]
    supported_news_gate_recommendations: tuple[str, ...]
    risk_to_gate_state: tuple[tuple[str, str], ...]
    recommendation_to_gate_state: tuple[tuple[str, str], ...]
    blocking_reason_codes: tuple[str, ...]
    caution_reason_codes: tuple[str, ...]
    fail_closed_reason_codes: tuple[str, ...]
    deterministic_reason_order: tuple[str, ...]
    maximum_reason_code_count: int
    maximum_evidence_reference_count: int

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _POLICY_FIELDS, "policy")
        if values["policy_version"] != SIGNAL_GATE_POLICY_VERSION:
            raise SignalGateError("invalid policy_version")
        versions = _normalize_choices(
            values["supported_news_risk_policy_versions"],
            "supported_news_risk_policy_versions",
            frozenset(("news-risk-policy-v1",)),
        )
        if versions != ("news-risk-policy-v1",):
            raise SignalGateError("invalid supported_news_risk_policy_versions")
        routes = _normalize_choices(values["supported_routes"], "supported_routes", frozenset(_ROUTES))
        if routes != _ROUTES:
            raise SignalGateError("invalid supported_routes")
        classifications = _normalize_choices(values["supported_risk_classifications"], "supported_risk_classifications", _RISK_CLASSES)
        if set(classifications) != _RISK_CLASSES:
            raise SignalGateError("invalid supported_risk_classifications")
        recommendations = _normalize_choices(
            values["supported_news_gate_recommendations"],
            "supported_news_gate_recommendations",
            _NEWS_RECOMMENDATIONS,
        )
        if set(recommendations) != _NEWS_RECOMMENDATIONS:
            raise SignalGateError("invalid supported_news_gate_recommendations")
        risk_mapping = _normalize_mapping(values["risk_to_gate_state"], _RISK_MAPPING, "risk_to_gate_state")
        recommendation_mapping = _normalize_mapping(values["recommendation_to_gate_state"], _RECOMMENDATION_MAPPING, "recommendation_to_gate_state")
        blocking = _normalize_choices(values["blocking_reason_codes"], "blocking_reason_codes", _NEWS_RISK_REASON_CODES, sort=False)
        caution = _normalize_choices(values["caution_reason_codes"], "caution_reason_codes", _NEWS_RISK_REASON_CODES, sort=False)
        failed = _normalize_choices(values["fail_closed_reason_codes"], "fail_closed_reason_codes", _NEWS_RISK_REASON_CODES, sort=False)
        order = _normalize_choices(values["deterministic_reason_order"], "deterministic_reason_order", _GATE_REASON_CODES, sort=False)
        if not order or any(code not in order for code in _GATE_REASON_CODES):
            raise SignalGateError("invalid deterministic_reason_order")
        maximum_reasons = _require_positive_integer(values["maximum_reason_code_count"], "maximum_reason_code_count")
        maximum_refs = _require_positive_integer(values["maximum_evidence_reference_count"], "maximum_evidence_reference_count")
        if maximum_reasons > len(_GATE_REASON_CODES) or maximum_refs > 128:
            raise SignalGateError("invalid policy limits")
        object.__setattr__(self, "policy_version", SIGNAL_GATE_POLICY_VERSION)
        object.__setattr__(self, "supported_news_risk_policy_versions", versions)
        object.__setattr__(self, "supported_routes", routes)
        object.__setattr__(self, "supported_risk_classifications", classifications)
        object.__setattr__(self, "supported_news_gate_recommendations", recommendations)
        object.__setattr__(self, "risk_to_gate_state", risk_mapping)
        object.__setattr__(self, "recommendation_to_gate_state", recommendation_mapping)
        object.__setattr__(self, "blocking_reason_codes", blocking)
        object.__setattr__(self, "caution_reason_codes", caution)
        object.__setattr__(self, "fail_closed_reason_codes", failed)
        object.__setattr__(self, "deterministic_reason_order", order)
        object.__setattr__(self, "maximum_reason_code_count", maximum_reasons)
        object.__setattr__(self, "maximum_evidence_reference_count", maximum_refs)


def _decision_identity(values: Mapping[str, Any]) -> str:
    return _hash_mapping(
        {
            "policy_version": values["policy_version"],
            "event_snapshot_id": values["event_snapshot_id"],
            "news_risk_policy_version": values["news_risk_policy_version"],
            "news_risk_object_id": values["news_risk_object_id"],
            "route": values["route"],
            "gate_state": values["gate_state"],
            "eligibility_recommendation": values["eligibility_recommendation"],
            "risk_classification": values["risk_classification"],
            "news_gate_recommendation": values["news_gate_recommendation"],
            "reason_codes": list(values["reason_codes"]),
            "evidence_refs": list(values["evidence_refs"]),
        }
    )


@dataclass(frozen=True, init=False)
class SignalGateDecisionV1:
    policy_version: str
    event_snapshot_id: str
    news_risk_policy_version: str
    news_risk_object_id: str
    route: str
    gate_state: str
    eligibility_recommendation: str
    risk_classification: str
    news_gate_recommendation: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    structured_explanation: str
    signal_gate_decision_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _DECISION_FIELDS, "Signal Gate decision")
        if values["policy_version"] != SIGNAL_GATE_POLICY_VERSION:
            raise SignalGateError("invalid policy_version")
        state = _require_choice(values["gate_state"], "gate_state", _GATE_STATES)
        eligibility = _require_choice(values["eligibility_recommendation"], "eligibility_recommendation", _ELIGIBILITY)
        if eligibility != _ELIGIBILITY_BY_STATE[state]:
            raise SignalGateError("invalid eligibility_recommendation")
        canonical = {
            "policy_version": SIGNAL_GATE_POLICY_VERSION,
            "event_snapshot_id": _require_hash(values["event_snapshot_id"], "event_snapshot_id"),
            "news_risk_policy_version": _require_text(values["news_risk_policy_version"], "news_risk_policy_version"),
            "news_risk_object_id": _require_hash(values["news_risk_object_id"], "news_risk_object_id"),
            "route": _require_choice(values["route"], "route", frozenset(_ROUTES)),
            "gate_state": state,
            "eligibility_recommendation": eligibility,
            "risk_classification": _require_choice(values["risk_classification"], "risk_classification", _RISK_CLASSES),
            "news_gate_recommendation": _require_choice(values["news_gate_recommendation"], "news_gate_recommendation", _NEWS_RECOMMENDATIONS),
            "reason_codes": _normalize_choices(values["reason_codes"], "reason_codes", _GATE_REASON_CODES, sort=False),
            "evidence_refs": _normalize_identifiers(values["evidence_refs"], "evidence_refs"),
            "structured_explanation": _require_text(values["structured_explanation"], "structured_explanation"),
        }
        if not canonical["reason_codes"] or not canonical["evidence_refs"]:
            raise SignalGateError("missing semantic fields")
        decision_id = _decision_identity(canonical)
        supplied = values["signal_gate_decision_id"]
        if supplied is not None and supplied != decision_id:
            raise SignalGateError("invalid signal_gate_decision_id")
        for name, value in canonical.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signal_gate_decision_id", decision_id)


def _news_risk_identity(values: Mapping[str, Any]) -> str:
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


def _validate_news_risk(result: NewsRiskObjectV1, policy: SignalGatePolicyV1) -> dict[str, Any]:
    if result.policy_version not in policy.supported_news_risk_policy_versions:
        raise SignalGateError("unsupported News Risk policy")
    values = {name: getattr(result, name) for name in result.__dataclass_fields__}
    if _news_risk_identity(values) != result.news_risk_object_id:
        raise SignalGateError("invalid News Risk identity")
    return {
        "event": _require_hash(result.event_snapshot_id, "News Risk event_snapshot_id"),
        "policy_version": result.policy_version,
        "object_id": _require_hash(result.news_risk_object_id, "news_risk_object_id"),
        "route": _require_choice(result.route, "News Risk route", frozenset(policy.supported_routes)),
        "classification": _require_choice(result.risk_classification, "risk_classification", frozenset(policy.supported_risk_classifications)),
        "recommendation": _require_choice(result.news_gate_recommendation, "news_gate_recommendation", frozenset(policy.supported_news_gate_recommendations)),
        "ambiguity": _require_choice(result.final_ambiguity_state, "final_ambiguity_state", _AMBIGUITY),
        "contradiction": _require_choice(result.final_contradiction_state, "final_contradiction_state", _CONTRADICTIONS),
        "evidence": _require_choice(result.final_evidence_state, "final_evidence_state", _EVIDENCE),
        "entity": _require_choice(result.final_entity_state, "final_entity_state", _ASSESSMENTS),
        "source": _require_choice(result.final_source_state, "final_source_state", _ASSESSMENTS),
        "risk": _require_choice(result.final_material_risk_state, "final_material_risk_state", _RISKS),
        "reasons": _normalize_choices(result.reason_codes, "News Risk reason_codes", _NEWS_RISK_REASON_CODES),
        "refs": _normalize_identifiers(result.evidence_refs, "News Risk evidence_refs"),
    }


def _canonical_reasons(codes: set[str], policy: SignalGatePolicyV1) -> tuple[str, ...]:
    reasons = tuple(code for code in policy.deterministic_reason_order if code in codes)
    if not reasons or len(reasons) > policy.maximum_reason_code_count:
        raise SignalGateError("invalid Signal Gate reason_codes")
    return reasons


def _new_decision(*, policy: SignalGatePolicyV1, data: dict[str, Any], state: str, reasons: set[str]) -> SignalGateDecisionV1:
    return SignalGateDecisionV1(
        policy_version=SIGNAL_GATE_POLICY_VERSION,
        event_snapshot_id=data["event"],
        news_risk_policy_version=data["policy_version"],
        news_risk_object_id=data["object_id"],
        route=data["route"],
        gate_state=state,
        eligibility_recommendation=_ELIGIBILITY_BY_STATE[state],
        risk_classification=data["classification"],
        news_gate_recommendation=data["recommendation"],
        reason_codes=_canonical_reasons(reasons, policy),
        evidence_refs=data["refs"],
        structured_explanation="signal-gate:" + state,
        signal_gate_decision_id=None,
    )


def evaluate_signal_gate(news_risk_object: Any, policy: Any) -> SignalGateDecisionV1:
    """Return one deterministic semantic eligibility decision."""

    if type(news_risk_object) is not NewsRiskObjectV1:
        raise SignalGateError("invalid News Risk object type")
    if type(policy) is not SignalGatePolicyV1:
        raise SignalGateError("invalid policy type")
    data = _validate_news_risk(news_risk_object, policy)
    if len(data["refs"]) > policy.maximum_evidence_reference_count:
        raise SignalGateError("too many evidence references")

    configured_failed = set(data["reasons"]).intersection(policy.fail_closed_reason_codes)
    if data["classification"] == "FAIL_CLOSED" or data["recommendation"] == "FAIL_CLOSED" or configured_failed:
        reasons = configured_failed | {"FAIL_CLOSED_NEWS_RISK"}
        return _new_decision(policy=policy, data=data, state="FAIL_CLOSED", reasons=reasons)

    configured_blocking = set(data["reasons"]).intersection(policy.blocking_reason_codes)
    if data["classification"] == "BLOCKING":
        return _new_decision(policy=policy, data=data, state="BLOCKED", reasons={"NEWS_RISK_BLOCKING"})
    if data["recommendation"] == "REQUIRE_BLOCK":
        return _new_decision(policy=policy, data=data, state="BLOCKED", reasons={"BLOCK_RECOMMENDED"})
    if configured_blocking:
        reasons = configured_blocking | {"BLOCKING_NEWS_REASON"}
        return _new_decision(policy=policy, data=data, state="BLOCKED", reasons=reasons)
    if data["classification"] == "ELEVATED":
        return _new_decision(policy=policy, data=data, state="BLOCKED", reasons={"NEWS_RISK_ELEVATED"})
    configured_caution = set(data["reasons"]).intersection(policy.caution_reason_codes)
    if configured_caution:
        reasons = configured_caution | {"NEWS_RISK_CAUTION"}
        return _new_decision(policy=policy, data=data, state="CAUTION", reasons=reasons)
    if data["classification"] == "CAUTION":
        return _new_decision(policy=policy, data=data, state="CAUTION", reasons={"NEWS_RISK_CAUTION"})
    if data["recommendation"] == "REQUIRE_CAUTION":
        return _new_decision(policy=policy, data=data, state="CAUTION", reasons={"CAUTION_RECOMMENDED"})
    return _new_decision(policy=policy, data=data, state="OPEN", reasons={"NEWS_RISK_CLEAR", "NO_NEWS_RESTRICTION"})
