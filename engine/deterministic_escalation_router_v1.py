"""Pure deterministic escalation decisions for validated semantic reviews."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from engine.deepseek_primary_review_provider_v1 import DeepSeekPrimaryReviewResultV1
from engine.news_event_contract_v1 import canonical_json_bytes, sha256_hex


DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION = (
    "deterministic-escalation-router-policy-v1"
)

__all__ = (
    "DeterministicEscalationRouterError",
    "DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION",
    "DeterministicEscalationRouterPolicyV1",
    "DeterministicEscalationDecisionV1",
    "route_deepseek_primary_review",
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_POLICY_FIELDS = frozenset(
    {
        "policy_version",
        "l1_claude_model_policy_id",
        "l2_claude_model_policy_id",
        "forced_l2_reason_codes",
        "fail_closed_reason_codes",
        "moderate_ambiguity_values",
        "critical_ambiguity_values",
        "moderate_entity_concern_values",
        "critical_entity_concern_values",
        "moderate_source_concern_values",
        "critical_source_concern_values",
        "insufficient_evidence_values",
        "critical_risk_flags",
    }
)
_DECISION_FIELDS = frozenset(
    {
        "policy_version",
        "event_snapshot_id",
        "deepseek_semantic_result_id",
        "deepseek_payload_sha256",
        "route",
        "route_name",
        "claude_review_required",
        "claude_model_policy_id",
        "reason_codes",
        "escalation_evidence_refs",
        "decision_id",
    }
)
_INPUT_REASON_CODES = frozenset(
    {
        "REVIEW_COMPLETED",
        "ROUTINE_COMPLETE",
        "EVIDENCE_SUFFICIENT",
        "NO_MATERIAL_CONTRADICTION",
        "MODERATE_AMBIGUITY",
        "LIMITED_EVIDENCE_CONCERN",
        "MODERATE_ENTITY_CONCERN",
        "MODERATE_SOURCE_CONCERN",
        "NONCRITICAL_CONTRADICTION",
        "CRITICAL_AMBIGUITY",
        "MATERIAL_CONTRADICTION",
        "CRITICAL_EVIDENCE_DEFICIT",
        "CRITICAL_ENTITY_CONCERN",
        "CRITICAL_SOURCE_CONCERN",
        "FORCED_CRITICAL_REVIEW",
        "INVALID_RESULT_STATUS",
        "INVALID_ROUTER_INPUT",
        "POLICY_MISMATCH",
        "INCONSISTENT_RESULT_BINDING",
    }
)
_OUTPUT_REASON_CODES = _INPUT_REASON_CODES - {"REVIEW_COMPLETED"} - {
    "INVALID_RESULT_STATUS",
    "INVALID_ROUTER_INPUT",
    "POLICY_MISMATCH",
    "INCONSISTENT_RESULT_BINDING",
}
_L0_REASONS = (
    "ROUTINE_COMPLETE",
    "EVIDENCE_SUFFICIENT",
    "NO_MATERIAL_CONTRADICTION",
)
_L1_REASON_ORDER = (
    "MODERATE_AMBIGUITY",
    "LIMITED_EVIDENCE_CONCERN",
    "MODERATE_ENTITY_CONCERN",
    "MODERATE_SOURCE_CONCERN",
    "NONCRITICAL_CONTRADICTION",
)
_L2_REASON_ORDER = (
    "CRITICAL_AMBIGUITY",
    "MATERIAL_CONTRADICTION",
    "CRITICAL_EVIDENCE_DEFICIT",
    "CRITICAL_ENTITY_CONCERN",
    "CRITICAL_SOURCE_CONCERN",
    "FORCED_CRITICAL_REVIEW",
)
_ROUTE_NAMES = {
    "L0": "CLEAN_OR_ROUTINE",
    "L1": "MODERATE_AMBIGUITY",
    "L2": "CRITICAL_AMBIGUITY",
}


class DeterministicEscalationRouterError(ValueError):
    """Raised when deterministic escalation routing contracts are invalid."""


def _require_exact_fields(values: dict[str, Any], expected: frozenset[str], label: str) -> None:
    if set(values) != expected:
        raise DeterministicEscalationRouterError(f"invalid {label} fields")


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise DeterministicEscalationRouterError(f"invalid {label}")
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise DeterministicEscalationRouterError(f"invalid {label}")
    return value


def _require_texts(value: Any, label: str, allowed: frozenset[str]) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise DeterministicEscalationRouterError(f"invalid {label}")
    texts: list[str] = []
    for item in value:
        if type(item) is not str or item not in allowed:
            raise DeterministicEscalationRouterError(f"invalid {label}")
        texts.append(item)
    return tuple(sorted(set(texts)))


def _require_identifiers(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise DeterministicEscalationRouterError(f"invalid {label}")
    return tuple(sorted({_require_identifier(item, label) for item in value}))


def _semantic_decision_id(values: dict[str, Any]) -> str:
    semantic = {
        "policy_version": values["policy_version"],
        "event_snapshot_id": values["event_snapshot_id"],
        "deepseek_semantic_result_id": values["deepseek_semantic_result_id"],
        "deepseek_payload_sha256": values["deepseek_payload_sha256"],
        "route": values["route"],
        "route_name": values["route_name"],
        "claude_review_required": values["claude_review_required"],
        "claude_model_policy_id": values["claude_model_policy_id"],
        "reason_codes": list(values["reason_codes"]),
        "escalation_evidence_refs": list(values["escalation_evidence_refs"]),
    }
    return sha256_hex(canonical_json_bytes(semantic))


@dataclass(frozen=True, init=False)
class DeterministicEscalationRouterPolicyV1:
    policy_version: str
    l1_claude_model_policy_id: str
    l2_claude_model_policy_id: str
    forced_l2_reason_codes: tuple[str, ...]
    fail_closed_reason_codes: tuple[str, ...]
    moderate_ambiguity_values: tuple[str, ...]
    critical_ambiguity_values: tuple[str, ...]
    moderate_entity_concern_values: tuple[str, ...]
    critical_entity_concern_values: tuple[str, ...]
    moderate_source_concern_values: tuple[str, ...]
    critical_source_concern_values: tuple[str, ...]
    insufficient_evidence_values: tuple[str, ...]
    critical_risk_flags: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _POLICY_FIELDS, "router policy")
        if values["policy_version"] != DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION:
            raise DeterministicEscalationRouterError("invalid policy_version")
        l1 = _require_identifier(values["l1_claude_model_policy_id"], "l1 model policy")
        l2 = _require_identifier(values["l2_claude_model_policy_id"], "l2 model policy")
        if l1 == l2:
            raise DeterministicEscalationRouterError("model policies must differ")
        forced = _require_texts(
            values["forced_l2_reason_codes"],
            "forced_l2_reason_codes",
            frozenset({"FORCED_CRITICAL_REVIEW"}),
        )
        failed = _require_texts(
            values["fail_closed_reason_codes"],
            "fail_closed_reason_codes",
            frozenset(
                {
                    "INVALID_RESULT_STATUS",
                    "INVALID_ROUTER_INPUT",
                    "POLICY_MISMATCH",
                    "INCONSISTENT_RESULT_BINDING",
                }
            ),
        )
        moderate_ambiguity = _require_texts(
            values["moderate_ambiguity_values"],
            "moderate_ambiguity_values",
            frozenset({"MODERATE"}),
        )
        critical_ambiguity = _require_texts(
            values["critical_ambiguity_values"],
            "critical_ambiguity_values",
            frozenset({"CRITICAL"}),
        )
        moderate_entity = _require_texts(
            values["moderate_entity_concern_values"],
            "moderate_entity_concern_values",
            frozenset({"MODERATE"}),
        )
        critical_entity = _require_texts(
            values["critical_entity_concern_values"],
            "critical_entity_concern_values",
            frozenset({"CRITICAL"}),
        )
        moderate_source = _require_texts(
            values["moderate_source_concern_values"],
            "moderate_source_concern_values",
            frozenset({"MODERATE"}),
        )
        critical_source = _require_texts(
            values["critical_source_concern_values"],
            "critical_source_concern_values",
            frozenset({"CRITICAL"}),
        )
        insufficient = _require_texts(
            values["insufficient_evidence_values"],
            "insufficient_evidence_values",
            frozenset({"INSUFFICIENT"}),
        )
        risks = _require_texts(
            values["critical_risk_flags"],
            "critical_risk_flags",
            frozenset({"MATERIAL_RISK"}),
        )
        object.__setattr__(self, "policy_version", DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION)
        object.__setattr__(self, "l1_claude_model_policy_id", l1)
        object.__setattr__(self, "l2_claude_model_policy_id", l2)
        object.__setattr__(self, "forced_l2_reason_codes", forced)
        object.__setattr__(self, "fail_closed_reason_codes", failed)
        object.__setattr__(self, "moderate_ambiguity_values", moderate_ambiguity)
        object.__setattr__(self, "critical_ambiguity_values", critical_ambiguity)
        object.__setattr__(self, "moderate_entity_concern_values", moderate_entity)
        object.__setattr__(self, "critical_entity_concern_values", critical_entity)
        object.__setattr__(self, "moderate_source_concern_values", moderate_source)
        object.__setattr__(self, "critical_source_concern_values", critical_source)
        object.__setattr__(self, "insufficient_evidence_values", insufficient)
        object.__setattr__(self, "critical_risk_flags", risks)


@dataclass(frozen=True, init=False)
class DeterministicEscalationDecisionV1:
    policy_version: str
    event_snapshot_id: str
    deepseek_semantic_result_id: str
    deepseek_payload_sha256: str
    route: str
    route_name: str
    claude_review_required: bool
    claude_model_policy_id: str | None
    reason_codes: tuple[str, ...]
    escalation_evidence_refs: tuple[str, ...]
    decision_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _DECISION_FIELDS, "decision")
        if values["policy_version"] != DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION:
            raise DeterministicEscalationRouterError("invalid policy_version")
        event_snapshot_id = _require_hash(values["event_snapshot_id"], "event_snapshot_id")
        result_id = _require_hash(values["deepseek_semantic_result_id"], "deepseek_semantic_result_id")
        payload_hash = _require_hash(values["deepseek_payload_sha256"], "deepseek_payload_sha256")
        route = values["route"]
        if type(route) is not str or route not in _ROUTE_NAMES:
            raise DeterministicEscalationRouterError("invalid route")
        if values["route_name"] != _ROUTE_NAMES[route]:
            raise DeterministicEscalationRouterError("invalid route_name")
        required = values["claude_review_required"]
        if type(required) is not bool:
            raise DeterministicEscalationRouterError("invalid claude_review_required")
        model = values["claude_model_policy_id"]
        if route == "L0":
            if required or model is not None:
                raise DeterministicEscalationRouterError("invalid L0 decision")
        else:
            if not required or type(model) is not str or _IDENTIFIER.fullmatch(model) is None:
                raise DeterministicEscalationRouterError("invalid escalated decision")
        reasons = _require_texts(values["reason_codes"], "reason_codes", _OUTPUT_REASON_CODES)
        evidence = _require_identifiers(values["escalation_evidence_refs"], "escalation_evidence_refs")
        canonical = {
            "policy_version": DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION,
            "event_snapshot_id": event_snapshot_id,
            "deepseek_semantic_result_id": result_id,
            "deepseek_payload_sha256": payload_hash,
            "route": route,
            "route_name": _ROUTE_NAMES[route],
            "claude_review_required": required,
            "claude_model_policy_id": model,
            "reason_codes": reasons,
            "escalation_evidence_refs": evidence,
        }
        decision_id = _semantic_decision_id(canonical)
        supplied = values["decision_id"]
        if supplied is not None and supplied != decision_id:
            raise DeterministicEscalationRouterError("invalid decision_id")
        object.__setattr__(self, "policy_version", DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION)
        object.__setattr__(self, "event_snapshot_id", event_snapshot_id)
        object.__setattr__(self, "deepseek_semantic_result_id", result_id)
        object.__setattr__(self, "deepseek_payload_sha256", payload_hash)
        object.__setattr__(self, "route", route)
        object.__setattr__(self, "route_name", _ROUTE_NAMES[route])
        object.__setattr__(self, "claude_review_required", required)
        object.__setattr__(self, "claude_model_policy_id", model)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "escalation_evidence_refs", evidence)
        object.__setattr__(self, "decision_id", decision_id)


def _result_facts(result: DeepSeekPrimaryReviewResultV1) -> dict[str, Any]:
    if result.review_status != "COMPLETED":
        raise DeterministicEscalationRouterError("review_status must be COMPLETED")
    if result.review_conclusion != "FACTUAL_REVIEW_COMPLETE":
        raise DeterministicEscalationRouterError("invalid review_conclusion")
    event_snapshot_id = _require_hash(result.event_snapshot_id, "event_snapshot_id")
    payload_hash = _require_hash(result.request_payload_sha256, "request_payload_sha256")
    supplied_result_id = _require_hash(result.semantic_result_id, "semantic_result_id")
    if result.ambiguity_level not in {"NONE", "MODERATE", "CRITICAL"}:
        raise DeterministicEscalationRouterError("invalid ambiguity_level")
    if type(result.contradiction_present) is not bool:
        raise DeterministicEscalationRouterError("invalid contradiction_present")
    if result.evidence_sufficiency not in {"SUFFICIENT", "INSUFFICIENT"}:
        raise DeterministicEscalationRouterError("invalid evidence_sufficiency")
    if result.entity_confidence_state not in {"EXPLICIT", "MODERATE", "CRITICAL"}:
        raise DeterministicEscalationRouterError("invalid entity_confidence_state")
    if result.source_policy_concern_state not in {"NONE", "MODERATE", "CRITICAL"}:
        raise DeterministicEscalationRouterError("invalid source_policy_concern_state")
    risks = _require_texts(
        result.material_risk_flags,
        "material_risk_flags",
        frozenset({"NONE", "MATERIAL_RISK"}),
    )
    reasons = _require_texts(result.reason_codes, "reason_codes", _INPUT_REASON_CODES)
    evidence = _require_identifiers(result.escalation_evidence_refs, "escalation_evidence_refs")
    raw_semantic = {
        "policy_version": result.policy_version,
        "event_snapshot_id": event_snapshot_id,
        "request_payload_sha256": payload_hash,
        "logical_review_id": result.logical_review_id,
        "review_status": result.review_status,
        "review_conclusion": result.review_conclusion,
        "ambiguity_level": result.ambiguity_level,
        "contradiction_present": result.contradiction_present,
        "evidence_sufficiency": result.evidence_sufficiency,
        "entity_confidence_state": result.entity_confidence_state,
        "source_policy_concern_state": result.source_policy_concern_state,
        "material_risk_flags": list(result.material_risk_flags),
        "reason_codes": list(result.reason_codes),
        "structured_explanation": result.structured_explanation,
        "escalation_evidence_refs": list(result.escalation_evidence_refs),
    }
    normalized_semantic = {
        **raw_semantic,
        "material_risk_flags": list(risks),
        "reason_codes": list(reasons),
        "escalation_evidence_refs": list(evidence),
    }
    raw_result_id = sha256_hex(canonical_json_bytes(raw_semantic))
    result_id = supplied_result_id
    if supplied_result_id == raw_result_id:
        result_id = sha256_hex(canonical_json_bytes(normalized_semantic))
    return {
        "event_snapshot_id": event_snapshot_id,
        "payload_hash": payload_hash,
        "result_id": result_id,
        "ambiguity": result.ambiguity_level,
        "contradiction": result.contradiction_present,
        "evidence": result.evidence_sufficiency,
        "entity": result.entity_confidence_state,
        "source": result.source_policy_concern_state,
        "risks": risks,
        "reasons": reasons,
        "evidence_refs": evidence,
    }


def _ordered_reasons(route: str, reasons: set[str]) -> tuple[str, ...]:
    if route == "L0":
        return _L0_REASONS
    order = _L1_REASON_ORDER if route == "L1" else _L2_REASON_ORDER
    return tuple(code for code in order if code in reasons)


def route_deepseek_primary_review(
    result: DeepSeekPrimaryReviewResultV1,
    policy: DeterministicEscalationRouterPolicyV1,
) -> DeterministicEscalationDecisionV1:
    """Return a deterministic escalation decision for one semantic result."""

    if type(result) is not DeepSeekPrimaryReviewResultV1:
        raise DeterministicEscalationRouterError("invalid semantic result type")
    if type(policy) is not DeterministicEscalationRouterPolicyV1:
        raise DeterministicEscalationRouterError("invalid router policy type")
    facts = _result_facts(result)
    input_reasons = set(facts["reasons"])
    if input_reasons.intersection(policy.fail_closed_reason_codes):
        raise DeterministicEscalationRouterError("fail-closed reason code")

    output_reasons: set[str] = set()
    forced = bool(input_reasons.intersection(policy.forced_l2_reason_codes))
    critical_ambiguity = facts["ambiguity"] in policy.critical_ambiguity_values
    critical_entity = facts["entity"] in policy.critical_entity_concern_values
    critical_source = facts["source"] in policy.critical_source_concern_values
    has_risk = bool(set(facts["risks"]).intersection(policy.critical_risk_flags))
    limited_evidence = facts["evidence"] in policy.insufficient_evidence_values

    if forced:
        route = "L2"
        output_reasons.add("FORCED_CRITICAL_REVIEW")
    elif critical_ambiguity or critical_entity or critical_source or has_risk:
        route = "L2"
        if critical_ambiguity:
            output_reasons.add("CRITICAL_AMBIGUITY")
        if critical_entity:
            output_reasons.add("CRITICAL_ENTITY_CONCERN")
        if critical_source:
            output_reasons.add("CRITICAL_SOURCE_CONCERN")
        if facts["contradiction"] and critical_ambiguity:
            output_reasons.add("MATERIAL_CONTRADICTION")
        if limited_evidence and has_risk:
            output_reasons.add("CRITICAL_EVIDENCE_DEFICIT")
    else:
        moderate_ambiguity = facts["ambiguity"] in policy.moderate_ambiguity_values
        moderate_entity = facts["entity"] in policy.moderate_entity_concern_values
        moderate_source = facts["source"] in policy.moderate_source_concern_values
        if moderate_ambiguity or moderate_entity or moderate_source or limited_evidence or facts["contradiction"]:
            route = "L1"
            if moderate_ambiguity:
                output_reasons.add("MODERATE_AMBIGUITY")
            if moderate_entity:
                output_reasons.add("MODERATE_ENTITY_CONCERN")
            if moderate_source:
                output_reasons.add("MODERATE_SOURCE_CONCERN")
            if limited_evidence:
                output_reasons.add("LIMITED_EVIDENCE_CONCERN")
            if facts["contradiction"]:
                output_reasons.add("NONCRITICAL_CONTRADICTION")
        else:
            route = "L0"

    required = route != "L0"
    model = None
    if route == "L1":
        model = policy.l1_claude_model_policy_id
    elif route == "L2":
        model = policy.l2_claude_model_policy_id
    return DeterministicEscalationDecisionV1(
        policy_version=DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION,
        event_snapshot_id=facts["event_snapshot_id"],
        deepseek_semantic_result_id=facts["result_id"],
        deepseek_payload_sha256=facts["payload_hash"],
        route=route,
        route_name=_ROUTE_NAMES[route],
        claude_review_required=required,
        claude_model_policy_id=model,
        reason_codes=_ordered_reasons(route, output_reasons),
        escalation_evidence_refs=facts["evidence_refs"],
        decision_id=None,
    )
