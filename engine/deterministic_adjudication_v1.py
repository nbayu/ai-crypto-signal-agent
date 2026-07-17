"""Pure deterministic semantic adjudication contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from engine.claude_escalated_review_provider_v1 import ClaudeEscalatedReviewResultV1
from engine.deepseek_primary_review_provider_v1 import DeepSeekPrimaryReviewResultV1
from engine.deterministic_escalation_router_v1 import DeterministicEscalationDecisionV1
from engine.news_event_contract_v1 import canonical_json_bytes, sha256_hex


DETERMINISTIC_ADJUDICATION_POLICY_VERSION = "deterministic-adjudication-policy-v1"

__all__ = (
    "DeterministicAdjudicationError",
    "DETERMINISTIC_ADJUDICATION_POLICY_VERSION",
    "DeterministicAdjudicationPolicyV1",
    "DeterministicAdjudicationResultV1",
    "adjudicate_review_results",
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_ROUTES = ("L0", "L1", "L2")
_ESCALATED_ROUTES = frozenset(("L1", "L2"))
_ROUTE_NAMES = {"L0": "CLEAN_OR_ROUTINE", "L1": "MODERATE_AMBIGUITY", "L2": "CRITICAL_AMBIGUITY"}
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
_CONTRADICTIONS = frozenset(("NONE", "PRESENT", "RESOLVED", "UNRESOLVED"))
_EVIDENCE = frozenset(("SUFFICIENT", "INSUFFICIENT"))
_ASSESSMENTS = frozenset(("ACCEPTABLE", "MODERATE", "CRITICAL"))
_RISKS = frozenset(("NONE", "MATERIAL_RISK"))
_FAIL_CODES = frozenset(
    (
        "INVALID_INPUT",
        "RESULT_NOT_COMPLETED",
        "ROUTE_RESULT_MISMATCH",
        "EVENT_BINDING_MISMATCH",
        "DECISION_BINDING_MISMATCH",
        "POLICY_MISMATCH",
        "CRITICAL_UNRESOLVED_DISAGREEMENT",
    )
)
_REASON_CODES = frozenset(
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
_POLICY_FIELDS = frozenset(
    (
        "policy_version",
        "supported_routes",
        "agreement_values",
        "contradiction_values",
        "evidence_precedence",
        "entity_precedence",
        "source_precedence",
        "material_risk_precedence",
        "critical_disagreement_rules",
        "fail_closed_reason_codes",
        "deterministic_reason_order",
        "maximum_reason_code_count",
        "maximum_evidence_reference_count",
    )
)
_RESULT_FIELDS = frozenset(
    (
        "policy_version",
        "event_snapshot_id",
        "route",
        "router_decision_id",
        "deepseek_semantic_result_id",
        "claude_semantic_result_id",
        "adjudication_outcome",
        "agreement_state",
        "final_ambiguity_state",
        "final_contradiction_state",
        "final_evidence_state",
        "final_entity_state",
        "final_source_state",
        "final_material_risk_state",
        "reason_codes",
        "evidence_refs",
        "structured_explanation",
        "adjudication_result_id",
    )
)


class DeterministicAdjudicationError(ValueError):
    """Raised when deterministic adjudication inputs are invalid."""


def _require_exact_fields(values: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(values) != expected:
        raise DeterministicAdjudicationError(f"invalid {label} fields")


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise DeterministicAdjudicationError(f"invalid {label}")
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise DeterministicAdjudicationError(f"invalid {label}")
    return value


def _require_positive_integer(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise DeterministicAdjudicationError(f"invalid {label}")
    return value


def _require_bounded_text(value: Any, label: str) -> str:
    if type(value) is not str or not value or len(value) > 1000:
        raise DeterministicAdjudicationError(f"invalid {label}")
    return value


def _normalize_texts(value: Any, label: str, allowed: frozenset[str], *, canonical: bool = True) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise DeterministicAdjudicationError(f"invalid {label}")
    items: list[str] = []
    for item in value:
        if type(item) is not str or item not in allowed:
            raise DeterministicAdjudicationError(f"invalid {label}")
        if item not in items:
            items.append(item)
    return tuple(sorted(items)) if canonical else tuple(items)


def _normalize_identifiers(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise DeterministicAdjudicationError(f"invalid {label}")
    return tuple(sorted({_require_identifier(item, label) for item in value}))


def _hash_mapping(value: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(value))


@dataclass(frozen=True, init=False)
class DeterministicAdjudicationPolicyV1:
    policy_version: str
    supported_routes: tuple[str, ...]
    agreement_values: tuple[str, ...]
    contradiction_values: tuple[str, ...]
    evidence_precedence: tuple[str, ...]
    entity_precedence: tuple[str, ...]
    source_precedence: tuple[str, ...]
    material_risk_precedence: tuple[str, ...]
    critical_disagreement_rules: tuple[str, ...]
    fail_closed_reason_codes: tuple[str, ...]
    deterministic_reason_order: tuple[str, ...]
    maximum_reason_code_count: int
    maximum_evidence_reference_count: int

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _POLICY_FIELDS, "policy")
        if values["policy_version"] != DETERMINISTIC_ADJUDICATION_POLICY_VERSION:
            raise DeterministicAdjudicationError("invalid policy_version")
        routes = _normalize_texts(values["supported_routes"], "supported_routes", frozenset(_ROUTES))
        if routes != _ROUTES:
            raise DeterministicAdjudicationError("invalid supported_routes")
        agreements = _normalize_texts(values["agreement_values"], "agreement_values", _AGREEMENTS)
        contradictions = _normalize_texts(values["contradiction_values"], "contradiction_values", _CONTRADICTIONS)
        evidence = _normalize_texts(values["evidence_precedence"], "evidence_precedence", _EVIDENCE)
        entity = _normalize_texts(values["entity_precedence"], "entity_precedence", _ASSESSMENTS)
        source = _normalize_texts(values["source_precedence"], "source_precedence", _ASSESSMENTS)
        risk = _normalize_texts(values["material_risk_precedence"], "material_risk_precedence", _RISKS)
        critical = _normalize_texts(values["critical_disagreement_rules"], "critical_disagreement_rules", frozenset(("CRITICAL_UNRESOLVED_DISAGREEMENT",)))
        failed = _normalize_texts(values["fail_closed_reason_codes"], "fail_closed_reason_codes", _FAIL_CODES)
        sequence = _normalize_texts(values["deterministic_reason_order"], "deterministic_reason_order", _REASON_CODES, canonical=False)
        if not sequence:
            raise DeterministicAdjudicationError("invalid deterministic_reason_order")
        max_reasons = _require_positive_integer(values["maximum_reason_code_count"], "maximum_reason_code_count")
        max_refs = _require_positive_integer(values["maximum_evidence_reference_count"], "maximum_evidence_reference_count")
        if max_reasons > len(_REASON_CODES) or max_refs > 128:
            raise DeterministicAdjudicationError("invalid policy limits")
        object.__setattr__(self, "policy_version", DETERMINISTIC_ADJUDICATION_POLICY_VERSION)
        object.__setattr__(self, "supported_routes", routes)
        object.__setattr__(self, "agreement_values", agreements)
        object.__setattr__(self, "contradiction_values", contradictions)
        object.__setattr__(self, "evidence_precedence", evidence)
        object.__setattr__(self, "entity_precedence", entity)
        object.__setattr__(self, "source_precedence", source)
        object.__setattr__(self, "material_risk_precedence", risk)
        object.__setattr__(self, "critical_disagreement_rules", critical)
        object.__setattr__(self, "fail_closed_reason_codes", failed)
        object.__setattr__(self, "deterministic_reason_order", sequence)
        object.__setattr__(self, "maximum_reason_code_count", max_reasons)
        object.__setattr__(self, "maximum_evidence_reference_count", max_refs)


def _result_identity(values: Mapping[str, Any]) -> str:
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


@dataclass(frozen=True, init=False)
class DeterministicAdjudicationResultV1:
    policy_version: str
    event_snapshot_id: str
    route: str
    router_decision_id: str
    deepseek_semantic_result_id: str
    claude_semantic_result_id: str | None
    adjudication_outcome: str
    agreement_state: str
    final_ambiguity_state: str
    final_contradiction_state: str
    final_evidence_state: str
    final_entity_state: str
    final_source_state: str
    final_material_risk_state: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    structured_explanation: str
    adjudication_result_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RESULT_FIELDS, "adjudication result")
        if values["policy_version"] != DETERMINISTIC_ADJUDICATION_POLICY_VERSION:
            raise DeterministicAdjudicationError("invalid result policy_version")
        route = values["route"]
        if route not in _ROUTES:
            raise DeterministicAdjudicationError("invalid result route")
        outcome = values["adjudication_outcome"]
        agreement = values["agreement_state"]
        if outcome not in _OUTCOMES or agreement not in _AGREEMENTS:
            raise DeterministicAdjudicationError("invalid result outcome")
        if route == "L0" and (outcome != "ACCEPT_DEEPSEEK" or agreement != "SINGLE_REVIEW"):
            raise DeterministicAdjudicationError("invalid L0 result")
        claude_id = values["claude_semantic_result_id"]
        if route == "L0":
            if claude_id is not None:
                raise DeterministicAdjudicationError("invalid L0 Claude identity")
        elif claude_id is None:
            raise DeterministicAdjudicationError("missing Claude identity")
        if claude_id is not None:
            claude_id = _require_hash(claude_id, "claude_semantic_result_id")
        canonical = {
            "policy_version": DETERMINISTIC_ADJUDICATION_POLICY_VERSION,
            "event_snapshot_id": _require_hash(values["event_snapshot_id"], "event_snapshot_id"),
            "route": route,
            "router_decision_id": _require_hash(values["router_decision_id"], "router_decision_id"),
            "deepseek_semantic_result_id": _require_hash(values["deepseek_semantic_result_id"], "deepseek_semantic_result_id"),
            "claude_semantic_result_id": claude_id,
            "adjudication_outcome": outcome,
            "agreement_state": agreement,
            "final_ambiguity_state": _require_choice(values["final_ambiguity_state"], "final_ambiguity_state", frozenset(("NONE", "MODERATE", "CRITICAL"))),
            "final_contradiction_state": _require_choice(values["final_contradiction_state"], "final_contradiction_state", _CONTRADICTIONS),
            "final_evidence_state": _require_choice(values["final_evidence_state"], "final_evidence_state", _EVIDENCE),
            "final_entity_state": _require_choice(values["final_entity_state"], "final_entity_state", _ASSESSMENTS),
            "final_source_state": _require_choice(values["final_source_state"], "final_source_state", _ASSESSMENTS),
            "final_material_risk_state": _require_choice(values["final_material_risk_state"], "final_material_risk_state", _RISKS),
            "reason_codes": _normalize_texts(values["reason_codes"], "reason_codes", _REASON_CODES),
            "evidence_refs": _normalize_identifiers(values["evidence_refs"], "evidence_refs"),
            "structured_explanation": _require_bounded_text(values["structured_explanation"], "structured_explanation"),
        }
        result_id = _result_identity(canonical)
        supplied = values["adjudication_result_id"]
        if supplied is not None and supplied != result_id:
            raise DeterministicAdjudicationError("invalid adjudication_result_id")
        for name, value in canonical.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "adjudication_result_id", result_id)


def _require_choice(value: Any, label: str, allowed: frozenset[str]) -> str:
    if type(value) is not str or value not in allowed:
        raise DeterministicAdjudicationError(f"invalid {label}")
    return value


def _validate_deepseek(result: DeepSeekPrimaryReviewResultV1, decision: DeterministicEscalationDecisionV1, policy: DeterministicAdjudicationPolicyV1) -> dict[str, Any]:
    if result.review_status != "COMPLETED":
        raise DeterministicAdjudicationError("DeepSeek result not completed")
    event = _require_hash(result.event_snapshot_id, "DeepSeek event_snapshot_id")
    result_id = _require_hash(result.semantic_result_id, "DeepSeek semantic_result_id")
    payload = _require_hash(result.request_payload_sha256, "DeepSeek payload_sha256")
    if event != decision.event_snapshot_id:
        raise DeterministicAdjudicationError("event binding mismatch")
    if result_id != decision.deepseek_semantic_result_id:
        raise DeterministicAdjudicationError("DeepSeek result binding mismatch")
    if payload != decision.deepseek_payload_sha256:
        raise DeterministicAdjudicationError("DeepSeek payload binding mismatch")
    ambiguity = _require_choice(result.ambiguity_level, "ambiguity_level", frozenset(("NONE", "MODERATE", "CRITICAL")))
    if type(result.contradiction_present) is not bool:
        raise DeterministicAdjudicationError("invalid contradiction_present")
    evidence = _require_choice(result.evidence_sufficiency, "evidence_sufficiency", _EVIDENCE)
    entity = _deepseek_entity(result.entity_confidence_state)
    source = _deepseek_source(result.source_policy_concern_state)
    risks = _normalize_texts(result.material_risk_flags, "material_risk_flags", _RISKS)
    reasons = _input_reason_codes(result.reason_codes, policy)
    refs = _normalize_identifiers(result.escalation_evidence_refs, "escalation_evidence_refs")
    return {
        "event": event,
        "result_id": result_id,
        "ambiguity": ambiguity,
        "contradiction": "PRESENT" if result.contradiction_present else "NONE",
        "evidence": evidence,
        "entity": entity,
        "source": source,
        "risk": "MATERIAL_RISK" if "MATERIAL_RISK" in risks else "NONE",
        "reasons": reasons,
        "refs": refs,
    }


def _deepseek_entity(value: Any) -> str:
    mapping = {"EXPLICIT": "ACCEPTABLE", "MODERATE": "MODERATE", "CRITICAL": "CRITICAL"}
    if value not in mapping:
        raise DeterministicAdjudicationError("invalid entity_confidence_state")
    return mapping[value]


def _deepseek_source(value: Any) -> str:
    mapping = {"NONE": "ACCEPTABLE", "MODERATE": "MODERATE", "CRITICAL": "CRITICAL"}
    if value not in mapping:
        raise DeterministicAdjudicationError("invalid source_policy_concern_state")
    return mapping[value]


def _claude_entity(value: Any) -> str:
    if value == "CONFIRMED":
        return "ACCEPTABLE"
    return _require_choice(value, "entity_assessment", _ASSESSMENTS)


def _input_reason_codes(value: Any, policy: DeterministicAdjudicationPolicyV1) -> tuple[str, ...]:
    allowed = frozenset(("REVIEW_COMPLETED", "CLAUDE_REVIEW_COMPLETED")) | frozenset(policy.fail_closed_reason_codes)
    return _normalize_texts(value, "reason_codes", allowed)


def _validate_claude(result: ClaudeEscalatedReviewResultV1, decision: DeterministicEscalationDecisionV1, policy: DeterministicAdjudicationPolicyV1) -> dict[str, Any]:
    if result.review_status != "COMPLETED":
        raise DeterministicAdjudicationError("Claude result not completed")
    event = _require_hash(result.event_snapshot_id, "Claude event_snapshot_id")
    result_id = _require_hash(result.semantic_result_id, "Claude semantic_result_id")
    if event != decision.event_snapshot_id:
        raise DeterministicAdjudicationError("event binding mismatch")
    if result.router_decision_id != decision.decision_id:
        raise DeterministicAdjudicationError("decision binding mismatch")
    if result.route != decision.route:
        raise DeterministicAdjudicationError("route binding mismatch")
    if result.model_policy_id != decision.claude_model_policy_id:
        raise DeterministicAdjudicationError("model policy binding mismatch")
    ambiguity = _claude_ambiguity(result.ambiguity_resolution)
    contradiction = _require_choice(result.contradiction_resolution, "contradiction_resolution", _CONTRADICTIONS)
    evidence = _require_choice(result.evidence_assessment, "evidence_assessment", _EVIDENCE)
    entity = _claude_entity(result.entity_assessment)
    source = _require_choice(result.source_assessment, "source_assessment", _ASSESSMENTS)
    risk = _require_choice(result.material_risk_assessment, "material_risk_assessment", _RISKS)
    reasons = _input_reason_codes(result.reason_codes, policy)
    refs = _normalize_identifiers(result.adjudication_evidence_refs, "adjudication_evidence_refs")
    return {
        "event": event,
        "result_id": result_id,
        "ambiguity": ambiguity,
        "contradiction": contradiction,
        "evidence": evidence,
        "entity": entity,
        "source": source,
        "risk": risk,
        "reasons": reasons,
        "refs": refs,
    }


def _claude_ambiguity(value: Any) -> str:
    mapping = {"RESOLVED": "NONE", "MODERATE": "MODERATE", "CRITICAL": "CRITICAL"}
    if value not in mapping:
        raise DeterministicAdjudicationError("invalid ambiguity_resolution")
    return mapping[value]


def _validate_decision(decision: DeterministicEscalationDecisionV1) -> None:
    _require_hash(decision.event_snapshot_id, "decision event_snapshot_id")
    _require_hash(decision.decision_id, "decision_id")
    _require_hash(decision.deepseek_semantic_result_id, "decision DeepSeek result")
    _require_hash(decision.deepseek_payload_sha256, "decision DeepSeek payload")
    if decision.route not in _ROUTES or decision.route_name != _ROUTE_NAMES[decision.route]:
        raise DeterministicAdjudicationError("invalid router decision")
    if type(decision.claude_review_required) is not bool:
        raise DeterministicAdjudicationError("invalid router decision")
    if decision.route == "L0":
        if decision.claude_review_required or decision.claude_model_policy_id is not None:
            raise DeterministicAdjudicationError("invalid L0 decision")
    elif not decision.claude_review_required:
        raise DeterministicAdjudicationError("invalid escalated decision")
    elif type(decision.claude_model_policy_id) is not str:
        raise DeterministicAdjudicationError("invalid decision model policy")


def _canonical_refs(deepseek: tuple[str, ...], claude: tuple[str, ...], limit: int) -> tuple[str, ...]:
    refs = tuple(sorted(set(deepseek).union(claude)))
    if not refs or len(refs) > limit:
        raise DeterministicAdjudicationError("invalid evidence references")
    return refs


def _canonical_reasons(codes: set[str], policy: DeterministicAdjudicationPolicyV1) -> tuple[str, ...]:
    result = tuple(code for code in policy.deterministic_reason_order if code in codes)
    if len(result) > policy.maximum_reason_code_count:
        raise DeterministicAdjudicationError("too many reason codes")
    return result


def _new_result(*, policy: DeterministicAdjudicationPolicyV1, decision: DeterministicEscalationDecisionV1, deepseek: dict[str, Any], claude: dict[str, Any] | None, outcome: str, agreement: str, ambiguity: str, contradiction: str, evidence: str, entity: str, source: str, risk: str, reasons: set[str], refs: tuple[str, ...]) -> DeterministicAdjudicationResultV1:
    canonical_reasons = _canonical_reasons(reasons, policy)
    if not canonical_reasons:
        raise DeterministicAdjudicationError("missing reason codes")
    explanation = "adjudication:" + outcome
    return DeterministicAdjudicationResultV1(
        policy_version=DETERMINISTIC_ADJUDICATION_POLICY_VERSION,
        event_snapshot_id=deepseek["event"],
        route=decision.route,
        router_decision_id=decision.decision_id,
        deepseek_semantic_result_id=deepseek["result_id"],
        claude_semantic_result_id=None if claude is None else claude["result_id"],
        adjudication_outcome=outcome,
        agreement_state=agreement,
        final_ambiguity_state=ambiguity,
        final_contradiction_state=contradiction,
        final_evidence_state=evidence,
        final_entity_state=entity,
        final_source_state=source,
        final_material_risk_state=risk,
        reason_codes=canonical_reasons,
        evidence_refs=refs,
        structured_explanation=explanation,
        adjudication_result_id=None,
    )


def _critical_state(left: str, right: str, critical: str) -> bool:
    return left != right and (left == critical or right == critical)


def adjudicate_review_results(deepseek_result: Any, router_decision: Any, claude_result: Any, policy: Any) -> DeterministicAdjudicationResultV1:
    """Return one deterministic semantic adjudication result."""

    if type(deepseek_result) is not DeepSeekPrimaryReviewResultV1:
        raise DeterministicAdjudicationError("invalid DeepSeek result type")
    if type(router_decision) is not DeterministicEscalationDecisionV1:
        raise DeterministicAdjudicationError("invalid router decision type")
    if type(policy) is not DeterministicAdjudicationPolicyV1:
        raise DeterministicAdjudicationError("invalid policy type")
    if claude_result is not None and type(claude_result) is not ClaudeEscalatedReviewResultV1:
        raise DeterministicAdjudicationError("invalid Claude result type")
    _validate_decision(router_decision)
    deepseek = _validate_deepseek(deepseek_result, router_decision, policy)
    if router_decision.route == "L0":
        if claude_result is not None:
            raise DeterministicAdjudicationError("unexpected Claude result")
        refs = _canonical_refs(deepseek["refs"], (), policy.maximum_evidence_reference_count)
        return _new_result(
            policy=policy,
            decision=router_decision,
            deepseek=deepseek,
            claude=None,
            outcome="ACCEPT_DEEPSEEK",
            agreement="SINGLE_REVIEW",
            ambiguity=deepseek["ambiguity"],
            contradiction=deepseek["contradiction"],
            evidence=deepseek["evidence"],
            entity=deepseek["entity"],
            source=deepseek["source"],
            risk=deepseek["risk"],
            reasons={"MATERIAL_FACTS_ALIGNED"},
            refs=refs,
        )
    if claude_result is None:
        raise DeterministicAdjudicationError("missing Claude result")
    claude = _validate_claude(claude_result, router_decision, policy)
    refs = _canonical_refs(deepseek["refs"], claude["refs"], policy.maximum_evidence_reference_count)
    input_fail = set(deepseek["reasons"]).union(claude["reasons"]).intersection(policy.fail_closed_reason_codes)
    if input_fail:
        return _new_result(
            policy=policy,
            decision=router_decision,
            deepseek=deepseek,
            claude=claude,
            outcome="FAIL_CLOSED",
            agreement="FAIL_CLOSED",
            ambiguity="CRITICAL" if "CRITICAL_UNRESOLVED_DISAGREEMENT" in input_fail else deepseek["ambiguity"],
            contradiction="UNRESOLVED" if "CRITICAL_UNRESOLVED_DISAGREEMENT" in input_fail else deepseek["contradiction"],
            evidence=deepseek["evidence"],
            entity=deepseek["entity"],
            source=deepseek["source"],
            risk=deepseek["risk"],
            reasons=set(input_fail),
            refs=refs,
        )
    risk_disagreement = deepseek["risk"] != claude["risk"]
    contradiction_disagreement = deepseek["contradiction"] != claude["contradiction"]
    entity_critical = _critical_state(deepseek["entity"], claude["entity"], "CRITICAL")
    source_critical = _critical_state(deepseek["source"], claude["source"], "CRITICAL")
    risk = "MATERIAL_RISK" if "MATERIAL_RISK" in {deepseek["risk"], claude["risk"]} else "NONE"
    contradiction = "PRESENT" if "PRESENT" in {deepseek["contradiction"], claude["contradiction"]} else ("UNRESOLVED" if "UNRESOLVED" in {deepseek["contradiction"], claude["contradiction"]} else "NONE")
    ambiguity = "CRITICAL" if "CRITICAL" in {deepseek["ambiguity"], claude["ambiguity"]} else ("MODERATE" if "MODERATE" in {deepseek["ambiguity"], claude["ambiguity"]} else "NONE")
    entity = "CRITICAL" if "CRITICAL" in {deepseek["entity"], claude["entity"]} else ("MODERATE" if "MODERATE" in {deepseek["entity"], claude["entity"]} else "ACCEPTABLE")
    source = "CRITICAL" if "CRITICAL" in {deepseek["source"], claude["source"]} else ("MODERATE" if "MODERATE" in {deepseek["source"], claude["source"]} else "ACCEPTABLE")
    evidence = "INSUFFICIENT" if "INSUFFICIENT" in {deepseek["evidence"], claude["evidence"]} else "SUFFICIENT"
    if risk_disagreement:
        return _new_result(
            policy=policy, decision=router_decision, deepseek=deepseek, claude=claude,
            outcome="MATERIAL_DISAGREEMENT", agreement="CRITICAL_DISAGREEMENT",
            ambiguity=ambiguity, contradiction=contradiction, evidence=evidence,
            entity=entity, source=source, risk=risk,
            reasons={"MATERIAL_RISK_DISAGREEMENT"} | ({"CONTRADICTION_DISAGREEMENT"} if contradiction_disagreement else set()), refs=refs,
        )
    if contradiction_disagreement:
        return _new_result(
            policy=policy, decision=router_decision, deepseek=deepseek, claude=claude,
            outcome="MATERIAL_DISAGREEMENT", agreement="CRITICAL_DISAGREEMENT",
            ambiguity=ambiguity, contradiction=contradiction, evidence=evidence,
            entity=entity, source=source, risk=risk,
            reasons={"CONTRADICTION_DISAGREEMENT"}, refs=refs,
        )
    if entity_critical or source_critical:
        reasons = set()
        if entity_critical:
            reasons.add("ENTITY_DISAGREEMENT")
        if source_critical:
            reasons.add("SOURCE_DISAGREEMENT")
        return _new_result(
            policy=policy, decision=router_decision, deepseek=deepseek, claude=claude,
            outcome="MATERIAL_DISAGREEMENT", agreement="CRITICAL_DISAGREEMENT",
            ambiguity=ambiguity, contradiction=contradiction, evidence=evidence,
            entity=entity, source=source, risk=risk, reasons=reasons, refs=refs,
        )
    if deepseek["evidence"] == claude["evidence"] == "INSUFFICIENT":
        return _new_result(
            policy=policy, decision=router_decision, deepseek=deepseek, claude=claude,
            outcome="INSUFFICIENT_EVIDENCE", agreement="AGREEMENT",
            ambiguity=ambiguity, contradiction=contradiction, evidence=evidence,
            entity=entity, source=source, risk=risk,
            reasons={"PROVIDERS_AGREE"}, refs=refs,
        )
    reasons: set[str] = set()
    qualified = False
    if deepseek["evidence"] != claude["evidence"]:
        qualified = True
        reasons.add("MINOR_EVIDENCE_DIFFERENCE")
    if deepseek["entity"] != claude["entity"]:
        qualified = True
        reasons.add("MODERATE_ENTITY_DIFFERENCE")
    if deepseek["source"] != claude["source"]:
        qualified = True
        reasons.add("MODERATE_SOURCE_DIFFERENCE")
    if qualified:
        return _new_result(
            policy=policy, decision=router_decision, deepseek=deepseek, claude=claude,
            outcome="CONSENSUS_WITH_QUALIFICATION", agreement="QUALIFIED_AGREEMENT",
            ambiguity=ambiguity, contradiction=contradiction, evidence=evidence,
            entity=entity, source=source, risk=risk, reasons=reasons, refs=refs,
        )
    return _new_result(
        policy=policy, decision=router_decision, deepseek=deepseek, claude=claude,
        outcome="CONSENSUS_CONFIRMED", agreement="AGREEMENT",
        ambiguity=ambiguity, contradiction=contradiction, evidence=evidence,
        entity=entity, source=source, risk=risk,
        reasons={"PROVIDERS_AGREE", "MATERIAL_FACTS_ALIGNED", "RISK_ASSESSMENTS_ALIGNED"}, refs=refs,
    )
