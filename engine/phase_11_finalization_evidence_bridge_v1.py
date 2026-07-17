"""Immutable additive evidence contracts for Phase 11 finalization.

This module validates evidence that has already been produced.  It does not
execute providers, perform adjudication, or transition budget state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.claude_escalated_review_provider_v1 import (
    ClaudeEscalatedReviewResultV1,
)
from engine.deepseek_primary_review_provider_v1 import (
    DeepSeekPrimaryReviewResultV1,
)
from engine.deterministic_escalation_router_v1 import (
    DeterministicEscalationDecisionV1,
)
from engine.phase_11_shadow_input_contracts_v1 import ShadowEvaluationInputV1
from engine.phase_11_shadow_run_orchestrator_v1 import (
    ShadowProviderRunPlanV1,
    ShadowProviderRunResultV1,
)


UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_UTC_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"

_TYPE_BINDINGS = {
    ("DEEPSEEK", "DEEPSEEK_PRIMARY"): DeepSeekPrimaryReviewResultV1,
    ("ANTHROPIC", "CLAUDE_SONNET_L1"): ClaudeEscalatedReviewResultV1,
    ("ANTHROPIC", "CLAUDE_OPUS_L2"): ClaudeEscalatedReviewResultV1,
}
_ROUTE_MAPPING = {
    "L0": ("L0", "L0"),
    "L1": ("L1", "L1"),
    "L2": ("L2", "L2"),
    "L1_TO_L2": ("L2", "L2"),
}
_ROUTE_EVIDENCE = {
    "L0": (("DEEPSEEK", "DEEPSEEK_PRIMARY"),),
    "L1": (
        ("DEEPSEEK", "DEEPSEEK_PRIMARY"),
        ("ANTHROPIC", "CLAUDE_SONNET_L1"),
    ),
    "L2": (
        ("DEEPSEEK", "DEEPSEEK_PRIMARY"),
        ("ANTHROPIC", "CLAUDE_OPUS_L2"),
    ),
    "L1_TO_L2": (
        ("DEEPSEEK", "DEEPSEEK_PRIMARY"),
        ("ANTHROPIC", "CLAUDE_SONNET_L1"),
        ("ANTHROPIC", "CLAUDE_OPUS_L2"),
    ),
}


class ShadowFinalizationEvidenceBridgeValidationError(ValueError):
    """Raised when additive finalization evidence is inconsistent."""


class ShadowTerminalRecordStatusV1(StrEnum):
    DENIED = "DENIED"
    FAILED_CLOSED = "FAILED_CLOSED"
    PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class ShadowTerminalAdjudicationStateV1(StrEnum):
    NOT_PERFORMED = "NOT_PERFORMED"


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                f"invalid {label}"
            )
        parsed = value.astimezone(UTC)
    elif type(value) is str and _UTC_TEXT.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                f"invalid {label}"
            ) from error
    else:
        raise ShadowFinalizationEvidenceBridgeValidationError(
            f"invalid {label}"
        )
    text = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return text.replace("+00:00", "Z").replace(".000000Z", "Z")


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "non-canonical decimal"
            )
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        return _timestamp(value, "timestamp")
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic canonical JSON encoded as UTF-8."""

    try:
        return json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowFinalizationEvidenceBridgeValidationError(
            "non-canonical bridge metadata"
        ) from error


def lowercase_sha256(value: Any) -> str:
    """Return lowercase SHA-256 over canonical structured JSON."""

    return sha256(canonical_json_bytes(value)).hexdigest()


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ShadowFinalizationEvidenceBridgeValidationError(
            f"invalid {label}"
        )
    return value


def _hash_value(
    value: Any, label: str, *, optional: bool = False
) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ShadowFinalizationEvidenceBridgeValidationError(
            f"invalid {label}"
        )
    return value


def _hashes(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ShadowFinalizationEvidenceBridgeValidationError(
            f"invalid {label}"
        )
    result = tuple(_hash_value(item, label) for item in value)
    if len(set(result)) != len(result):
        raise ShadowFinalizationEvidenceBridgeValidationError(
            f"duplicate {label}"
        )
    return result


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowFinalizationEvidenceBridgeValidationError(
            "invalid reason_codes"
        )
    result = tuple(sorted(value))
    if len(set(result)) != len(result) or any(
        type(item) is not str or _REASON.fullmatch(item) is None
        for item in result
    ):
        raise ShadowFinalizationEvidenceBridgeValidationError(
            "invalid reason_codes"
        )
    return result


def _zero_effect(production_effect: Any, proof: Any) -> None:
    if production_effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowFinalizationEvidenceBridgeValidationError(
            "invalid zero-production-effect evidence"
        )


def _identity(
    supplied: Any, material: Mapping[str, Any], label: str
) -> str:
    calculated = lowercase_sha256(material)
    provided = _hash_value(supplied, label, optional=True)
    if provided is not None and provided != calculated:
        raise ShadowFinalizationEvidenceBridgeValidationError(
            f"{label} mismatch"
        )
    return calculated


_TYPED_FIELDS = frozenset(
    (
        "schema_version",
        "typed_evidence_id",
        "execution_id",
        "run_id",
        "call_plan_id",
        "invocation_result_id",
        "call_id",
        "provider",
        "model",
        "request_hash",
        "provider_review_identity",
        "typed_review_result",
        "typed_review_identity",
        "event_id",
        "event_version",
        "prompt_version",
        "provider_review_schema_version",
        "structured_verdict",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowTypedProviderReviewEvidenceV1:
    schema_version: str
    typed_evidence_id: str
    execution_id: str
    run_id: str
    call_plan_id: str
    invocation_result_id: str
    call_id: str
    provider: str
    model: str
    request_hash: str
    provider_review_identity: str
    typed_review_result: (
        DeepSeekPrimaryReviewResultV1 | ClaudeEscalatedReviewResultV1
    )
    typed_review_identity: str
    event_id: str
    event_version: int
    prompt_version: str
    provider_review_schema_version: str
    structured_verdict: Mapping[str, str]
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _TYPED_FIELDS:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid typed-evidence fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-typed-provider-review-evidence-v1"
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "unsupported typed-evidence schema"
            )
        execution_id = _identifier(values["execution_id"], "execution_id")
        run_id = _identifier(values["run_id"], "run_id")
        call_plan_id = _hash_value(values["call_plan_id"], "call_plan_id")
        result_id = _hash_value(
            values["invocation_result_id"], "invocation_result_id"
        )
        call_id = _identifier(values["call_id"], "call_id")
        provider = values["provider"]
        model = values["model"]
        expected_type = _TYPE_BINDINGS.get((provider, model))
        typed_result = values["typed_review_result"]
        if expected_type is None or type(typed_result) is not expected_type:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "typed result does not match provider and model"
            )
        if provider == "ANTHROPIC":
            required_route = (
                "L1" if model == "CLAUDE_SONNET_L1" else "L2"
            )
            if typed_result.route != required_route:
                raise ShadowFinalizationEvidenceBridgeValidationError(
                    "typed Claude tier mismatch"
                )
        request_hash = _hash_value(values["request_hash"], "request_hash")
        event_id = _hash_value(values["event_id"], "event_id")
        semantic_id = _hash_value(
            typed_result.semantic_result_id, "semantic_result_id"
        )
        generic_identity = _hash_value(
            values["provider_review_identity"],
            "provider_review_identity",
        )
        typed_identity = _hash_value(
            values["typed_review_identity"], "typed_review_identity"
        )
        if (
            request_hash != typed_result.request_payload_sha256
            or event_id != typed_result.event_snapshot_id
            or generic_identity != semantic_id
            or typed_identity != semantic_id
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "typed semantic binding mismatch"
            )
        event_version = values["event_version"]
        if type(event_version) is not int or event_version <= 0:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid event_version"
            )
        prompt_version = _identifier(
            values["prompt_version"], "prompt_version"
        )
        review_schema = _identifier(
            values["provider_review_schema_version"],
            "provider_review_schema_version",
        )
        verdict = values["structured_verdict"]
        if (
            not isinstance(verdict, Mapping)
            or frozenset(verdict) != {"verdict"}
            or verdict["verdict"] != "ADVISORY_REVIEW"
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid structured verdict"
            )
        verdict_value = {"verdict": "ADVISORY_REVIEW"}
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "execution_id": execution_id,
            "run_id": run_id,
            "call_plan_id": call_plan_id,
            "invocation_result_id": result_id,
            "call_id": call_id,
            "provider": provider,
            "model": model,
            "request_hash": request_hash,
            "provider_review_identity": generic_identity,
            "typed_review_identity": typed_identity,
            "event_id": event_id,
            "event_version": event_version,
            "prompt_version": prompt_version,
            "provider_review_schema_version": review_schema,
            "structured_verdict": verdict_value,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _identity(
            values["typed_evidence_id"],
            material,
            "typed_evidence_id",
        )
        normalized = dict(values)
        normalized.update(
            typed_evidence_id=identity,
            execution_id=execution_id,
            run_id=run_id,
            call_plan_id=call_plan_id,
            invocation_result_id=result_id,
            call_id=call_id,
            request_hash=request_hash,
            provider_review_identity=generic_identity,
            typed_review_identity=typed_identity,
            event_id=event_id,
            event_version=event_version,
            prompt_version=prompt_version,
            provider_review_schema_version=review_schema,
            structured_verdict=verdict_value,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.typed_evidence_id


_LINEAGE_FIELDS = frozenset(
    (
        "schema_version",
        "route_lineage_id",
        "execution_id",
        "run_id",
        "run_route",
        "adjudication_route",
        "clean_record_route",
        "router_decisions",
        "call_plan_ids",
        "typed_review_ids",
        "escalation_required",
        "escalation_proven",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowAdjudicationRouteLineageV1:
    schema_version: str
    route_lineage_id: str
    execution_id: str
    run_id: str
    run_route: str
    adjudication_route: str
    clean_record_route: str
    router_decisions: tuple[DeterministicEscalationDecisionV1, ...]
    call_plan_ids: tuple[str, ...]
    typed_review_ids: tuple[str, ...]
    escalation_required: bool
    escalation_proven: bool
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _LINEAGE_FIELDS:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid route-lineage fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-adjudication-route-lineage-v1"
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "unsupported route-lineage schema"
            )
        execution_id = _identifier(values["execution_id"], "execution_id")
        run_id = _identifier(values["run_id"], "run_id")
        run_route = values["run_route"]
        if run_route not in _ROUTE_MAPPING:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "unsupported run route"
            )
        adjudication_route = values["adjudication_route"]
        record_route = values["clean_record_route"]
        if (adjudication_route, record_route) != _ROUTE_MAPPING[run_route]:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid canonical route mapping"
            )
        supplied_decisions = values["router_decisions"]
        if type(supplied_decisions) not in (tuple, list):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid router decisions"
            )
        decisions = tuple(supplied_decisions)
        if any(
            type(item) is not DeterministicEscalationDecisionV1
            for item in decisions
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid router decision"
            )
        call_ids = _hashes(values["call_plan_ids"], "call_plan_ids")
        typed_ids = _hashes(values["typed_review_ids"], "typed_review_ids")
        expected_count = len(_ROUTE_EVIDENCE[run_route])
        if len(call_ids) != expected_count or len(typed_ids) != expected_count:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "route evidence count mismatch"
            )
        required = values["escalation_required"]
        proven = values["escalation_proven"]
        if type(required) is not bool or type(proven) is not bool:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid escalation state"
            )
        if run_route == "L0":
            if (
                len(decisions) != 1
                or decisions[0].route != "L0"
                or required
                or proven
            ):
                raise ShadowFinalizationEvidenceBridgeValidationError(
                    "invalid L0 route lineage"
                )
        elif run_route in {"L1", "L2"}:
            if (
                len(decisions) != 1
                or decisions[0].route != run_route
                or not required
                or not proven
            ):
                raise ShadowFinalizationEvidenceBridgeValidationError(
                    "invalid escalation evidence"
                )
        elif (
            tuple(item.route for item in decisions) != ("L1", "L2")
            or not required
            or not proven
            or decisions[0].event_snapshot_id
            != decisions[1].event_snapshot_id
            or decisions[0].deepseek_semantic_result_id
            != decisions[1].deepseek_semantic_result_id
            or decisions[0].deepseek_payload_sha256
            != decisions[1].deepseek_payload_sha256
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid L1-to-L2 escalation lineage"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "execution_id": execution_id,
            "run_id": run_id,
            "run_route": run_route,
            "adjudication_route": adjudication_route,
            "clean_record_route": record_route,
            "router_decision_ids": tuple(
                item.decision_id for item in decisions
            ),
            "call_plan_ids": call_ids,
            "typed_review_ids": typed_ids,
            "escalation_required": required,
            "escalation_proven": proven,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _identity(
            values["route_lineage_id"],
            material,
            "route_lineage_id",
        )
        normalized = dict(values)
        normalized.update(
            route_lineage_id=identity,
            execution_id=execution_id,
            run_id=run_id,
            router_decisions=decisions,
            call_plan_ids=call_ids,
            typed_review_ids=typed_ids,
            escalation_required=required,
            escalation_proven=proven,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.route_lineage_id


_BUNDLE_FIELDS = frozenset(
    (
        "schema_version",
        "bundle_id",
        "shadow_input",
        "run_plan",
        "run_result",
        "route_lineage",
        "typed_review_evidence",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowAdjudicationEvidenceBundleV1:
    schema_version: str
    bundle_id: str
    shadow_input: ShadowEvaluationInputV1
    run_plan: ShadowProviderRunPlanV1
    run_result: ShadowProviderRunResultV1
    route_lineage: ShadowAdjudicationRouteLineageV1
    typed_review_evidence: tuple[ShadowTypedProviderReviewEvidenceV1, ...]
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _BUNDLE_FIELDS:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid adjudication-bundle fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-adjudication-evidence-bundle-v1"
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "unsupported adjudication-bundle schema"
            )
        shadow_input = values["shadow_input"]
        run_plan = values["run_plan"]
        run_result = values["run_result"]
        lineage = values["route_lineage"]
        if (
            type(shadow_input) is not ShadowEvaluationInputV1
            or type(run_plan) is not ShadowProviderRunPlanV1
            or type(run_result) is not ShadowProviderRunResultV1
            or type(lineage) is not ShadowAdjudicationRouteLineageV1
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid adjudication-bundle child"
            )
        supplied_typed = values["typed_review_evidence"]
        if type(supplied_typed) not in (tuple, list):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid typed review evidence"
            )
        typed_evidence = tuple(supplied_typed)
        if any(
            type(item) is not ShadowTypedProviderReviewEvidenceV1
            for item in typed_evidence
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid typed review evidence"
            )
        if (
            run_result.status != "COMPLETED"
            or run_result.failure_class != "NONE"
            or run_result.reconciliation_state
            not in {"NOT_REQUIRED", "RESOLVED"}
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "run evidence is not admissible"
            )
        if (
            run_plan.identity != run_result.run_plan_id
            or run_plan.shadow_input_identity != shadow_input.identity
            or run_plan.execution_id != run_result.execution_id
            or run_plan.run_id != run_result.run_id
            or run_plan.route != run_result.route
            or lineage.execution_id != run_plan.execution_id
            or lineage.run_id != run_plan.run_id
            or lineage.run_route != run_plan.route
            or run_result.ledger_before_id
            != run_plan.budget_ledger_before_id
            or run_result.ledger_after.policy.identity
            != run_plan.budget_ledger_before.policy.identity
            or run_result.ledger_after.sequence
            < run_plan.budget_ledger_before.sequence
            or run_result.ledger_after.reservations
            != run_plan.budget_ledger_before.reservations
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "adjudication-bundle lineage mismatch"
            )
        expected_pairs = _ROUTE_EVIDENCE[run_plan.route]
        actual_pairs = tuple(
            (item.provider, item.model) for item in typed_evidence
        )
        if actual_pairs != expected_pairs:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "typed review route mismatch"
            )
        typed_call_ids = tuple(
            item.call_plan_id for item in typed_evidence
        )
        invocation_results = run_result.invocation_results
        if (
            typed_call_ids != run_result.completed_call_plan_ids
            or typed_call_ids != lineage.call_plan_ids
            or typed_call_ids
            != tuple(item.identity for item in run_plan.call_plans)
            or tuple(item.identity for item in typed_evidence)
            != lineage.typed_review_ids
            or len(invocation_results) != len(typed_evidence)
            or any(
                item.execution_id != run_plan.execution_id
                or item.run_id != run_plan.run_id
                for item in typed_evidence
            )
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "typed review lineage mismatch"
            )
        for call_plan, generic_result, typed_item in zip(
            run_plan.call_plans,
            invocation_results,
            typed_evidence,
            strict=True,
        ):
            if (
                generic_result.status != "SUCCEEDED"
                or generic_result.failure_class != "NONE"
                or generic_result.reconciliation_state != "RESOLVED"
                or typed_item.call_id != call_plan.call_id
                or typed_item.invocation_result_id != generic_result.identity
                or typed_item.provider != generic_result.provider
                or typed_item.model != generic_result.model
                or typed_item.request_hash != generic_result.request_hash
                or typed_item.provider_review_identity
                != generic_result.provider_review_identity
            ):
                raise ShadowFinalizationEvidenceBridgeValidationError(
                    "generic and typed review evidence mismatch"
                )
        decisions = lineage.router_decisions
        deepseek_identity = typed_evidence[0].typed_review_identity
        if any(
            item.deepseek_semantic_result_id != deepseek_identity
            or item.deepseek_payload_sha256
            != typed_evidence[0].request_hash
            for item in decisions
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "router decision semantic lineage mismatch"
            )
        claude_items = tuple(
            item for item in typed_evidence if item.provider == "ANTHROPIC"
        )
        linked_decisions = () if run_plan.route == "L0" else decisions
        if len(claude_items) != len(linked_decisions) or any(
            item.typed_review_result.router_decision_id
            != decision.decision_id
            for item, decision in zip(
                claude_items, linked_decisions, strict=True
            )
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "Claude router-decision lineage mismatch"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "shadow_input_identity": shadow_input.identity,
            "run_plan_identity": run_plan.identity,
            "run_result_identity": run_result.identity,
            "route_lineage_identity": lineage.identity,
            "typed_review_identities": tuple(
                item.identity for item in typed_evidence
            ),
            "ledger_before_identity": run_plan.budget_ledger_before_id,
            "ledger_after_identity": run_result.ledger_after_id,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _identity(values["bundle_id"], material, "bundle_id")
        normalized = dict(values)
        normalized.update(
            bundle_id=identity,
            typed_review_evidence=typed_evidence,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.bundle_id

    @property
    def deepseek_result(self) -> DeepSeekPrimaryReviewResultV1:
        return self.typed_review_evidence[0].typed_review_result

    @property
    def claude_results(self) -> tuple[ClaudeEscalatedReviewResultV1, ...]:
        return tuple(
            item.typed_review_result
            for item in self.typed_review_evidence
            if type(item.typed_review_result)
            is ClaudeEscalatedReviewResultV1
        )


_TERMINAL_FIELDS = frozenset(
    (
        "schema_version",
        "terminal_record_id",
        "shadow_input",
        "run_plan",
        "run_result",
        "route_lineage",
        "finalized_at",
        "adjudication_state",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowTerminalExecutionRecordV1:
    schema_version: str
    terminal_record_id: str
    shadow_input: ShadowEvaluationInputV1
    run_plan: ShadowProviderRunPlanV1
    run_result: ShadowProviderRunResultV1
    route_lineage: ShadowAdjudicationRouteLineageV1 | None
    finalized_at: str
    adjudication_state: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _TERMINAL_FIELDS:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid terminal-record fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-terminal-execution-record-v1"
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "unsupported terminal-record schema"
            )
        shadow_input = values["shadow_input"]
        run_plan = values["run_plan"]
        run_result = values["run_result"]
        lineage = values["route_lineage"]
        if (
            type(shadow_input) is not ShadowEvaluationInputV1
            or type(run_plan) is not ShadowProviderRunPlanV1
            or type(run_result) is not ShadowProviderRunResultV1
            or (
                lineage is not None
                and type(lineage) is not ShadowAdjudicationRouteLineageV1
            )
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "invalid terminal-record child"
            )
        if run_result.status not in {
            item.value for item in ShadowTerminalRecordStatusV1
        }:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "clean completed evidence cannot be terminal"
            )
        if (
            run_result.failure_class == "NONE"
            or run_plan.identity != run_result.run_plan_id
            or run_plan.shadow_input_identity != shadow_input.identity
            or run_plan.execution_id != run_result.execution_id
            or run_plan.run_id != run_result.run_id
            or run_plan.route != run_result.route
            or run_result.ledger_before_id
            != run_plan.budget_ledger_before_id
            or run_result.ledger_after.policy.identity
            != run_plan.budget_ledger_before.policy.identity
            or run_result.ledger_after.sequence
            < run_plan.budget_ledger_before.sequence
            or run_result.ledger_after.reservations
            != run_plan.budget_ledger_before.reservations
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "terminal-record lineage mismatch"
            )
        if lineage is not None and (
            lineage.execution_id != run_plan.execution_id
            or lineage.run_id != run_plan.run_id
            or lineage.run_route != run_plan.route
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "terminal route-lineage mismatch"
            )
        if (
            run_result.status == "DENIED"
            and (
                run_result.completed_call_plan_ids
                or run_result.invocation_results
                or run_result.ledger_after_id
                != run_plan.budget_ledger_before_id
            )
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "denied record contains fabricated evidence"
            )
        if (
            run_result.status == "RECONCILIATION_REQUIRED"
            and run_result.reconciliation_state != "RECONCILIATION_REQUIRED"
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "uncertain evidence is falsely resolved"
            )
        finalized_at = _timestamp(values["finalized_at"], "finalized_at")
        if datetime.fromisoformat(finalized_at.replace("Z", "+00:00")) < (
            datetime.fromisoformat(
                run_result.completed_at.replace("Z", "+00:00")
            )
        ):
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "terminal record predates run completion"
            )
        adjudication_state = values["adjudication_state"]
        if adjudication_state != ShadowTerminalAdjudicationStateV1.NOT_PERFORMED:
            raise ShadowFinalizationEvidenceBridgeValidationError(
                "terminal evidence cannot be adjudicated"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "execution_id": run_plan.execution_id,
            "run_id": run_plan.run_id,
            "run_route": run_plan.route,
            "route_lineage_identity": (
                None if lineage is None else lineage.identity
            ),
            "shadow_input_identity": shadow_input.identity,
            "run_plan_identity": run_plan.identity,
            "run_result_identity": run_result.identity,
            "completed_call_plan_ids": run_result.completed_call_plan_ids,
            "completed_result_ids": tuple(
                item.identity for item in run_result.invocation_results
            ),
            "ledger_before_identity": run_plan.budget_ledger_before_id,
            "ledger_after_identity": run_result.ledger_after_id,
            "run_status": run_result.status,
            "run_failure": run_result.failure_class,
            "reconciliation_state": run_result.reconciliation_state,
            "first_failed_call_plan_id": (
                run_result.first_failed_call_plan_id
            ),
            "started_at": run_result.started_at,
            "finalized_at": finalized_at,
            "adjudication_state": (
                ShadowTerminalAdjudicationStateV1.NOT_PERFORMED
            ),
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _identity(
            values["terminal_record_id"],
            material,
            "terminal_record_id",
        )
        normalized = dict(values)
        normalized.update(
            terminal_record_id=identity,
            finalized_at=finalized_at,
            adjudication_state=(
                ShadowTerminalAdjudicationStateV1.NOT_PERFORMED
            ),
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.terminal_record_id

    @property
    def status(self) -> ShadowTerminalRecordStatusV1:
        return ShadowTerminalRecordStatusV1(self.run_result.status)


__all__ = (
    "ShadowAdjudicationEvidenceBundleV1",
    "ShadowAdjudicationRouteLineageV1",
    "ShadowFinalizationEvidenceBridgeValidationError",
    "ShadowTerminalAdjudicationStateV1",
    "ShadowTerminalExecutionRecordV1",
    "ShadowTerminalRecordStatusV1",
    "ShadowTypedProviderReviewEvidenceV1",
    "canonical_json_bytes",
    "lowercase_sha256",
)
