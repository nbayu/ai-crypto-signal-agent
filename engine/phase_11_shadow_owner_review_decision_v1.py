"""Immutable Phase 11 Project Owner review decision evidence contracts.

This module records only explicitly supplied decision evidence over one
already-created exit-gate report.  It does not authenticate an owner, infer a
decision, approve spending, enable Phase 12, or perform production work.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from engine.phase_11_shadow_cost_projection_v1 import (
    ShadowOwnerBudgetGateStatusV1,
)
from engine.phase_11_shadow_exit_gate_evidence_v1 import (
    ShadowPhase11EvidenceDimensionResultV1,
    ShadowPhase11EvidenceDimensionV1,
    ShadowPhase11EvidenceReadinessV1,
    ShadowPhase11ExitGateReportV1,
    ShadowPhase11LimitationsAcceptanceStatusV1,
    ShadowPhase11MechanicalReadinessV1,
    ShadowPhase11OwnerAcceptanceStatusV1,
    ShadowPhase12RecommendationStatusV1,
)


_UTC = timezone.utc
_LOCKED_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_REFERENCE = re.compile(r"^[A-Z][A-Z0-9_]{0,255}$")
_REQUIRED_PRECONDITIONS = frozenset(
    {
        "OWNER_BUDGET_APPROVAL_REQUIRED",
        "NO_API_SPENDING_UNTIL_OWNER_BUDGET_APPROVAL",
    }
)


class ShadowPhase11OwnerReviewValidationError(ValueError):
    """Raised when supplied owner-review decision evidence is inconsistent."""


class ShadowPhase11OwnerReviewScopeV1(StrEnum):
    EXPLICIT_OWNER_REVIEW_RECORD = "EXPLICIT_OWNER_REVIEW_RECORD"


class ShadowPhase11OwnerDecisionSourceV1(StrEnum):
    SYNTHETIC_CONTRACT_TEST = "SYNTHETIC_CONTRACT_TEST"
    PROJECT_OWNER_SUPPLIED = "PROJECT_OWNER_SUPPLIED"


class ShadowPhase11OwnerEvidenceDecisionV1(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class ShadowPhase11OwnerOverallDecisionV1(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class ShadowPhase11OwnerLimitationsDecisionV1(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class ShadowPhase12EnablementRecommendationV1(StrEnum):
    RECOMMEND_ENABLEMENT_WITH_PRECONDITIONS = (
        "RECOMMEND_ENABLEMENT_WITH_PRECONDITIONS"
    )
    DO_NOT_RECOMMEND = "DO_NOT_RECOMMEND"
    DEFERRED = "DEFERRED"


def _require_utc(name: str, value: Any) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() != _UTC.utcoffset(value)
    ):
        raise ShadowPhase11OwnerReviewValidationError(
            f"{name} must be an explicit UTC datetime"
        )
    return value


def _canonical(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _require_utc("canonical datetime", value).isoformat().replace(
            "+00:00", "Z"
        )
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShadowPhase11OwnerReviewValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic canonical UTF-8 JSON bytes."""

    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    """Return a lowercase SHA-256 digest for exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11OwnerReviewValidationError(
            "sha256 input must be exact bytes"
        )
    return hashlib.sha256(value).hexdigest()


def _derived_identity(material: Any) -> str:
    return sha256_hex(canonical_json_bytes(material))


def _identity(material: Any, supplied: Any, name: str) -> str:
    derived = _derived_identity(material)
    if supplied is not None and (
        type(supplied) is not str
        or not _HASH.fullmatch(supplied)
        or supplied != derived
    ):
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    return derived


def _exact_enum(name: str, value: Any, expected: type[StrEnum]) -> Any:
    if type(value) is not expected:
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    return value


def _codes(name: str, value: Any, *, empty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple or (not empty and not value):
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    if any(type(item) is not str or not _CODE.fullmatch(item) for item in value):
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    if len(set(value)) != len(value):
        raise ShadowPhase11OwnerReviewValidationError(f"duplicate {name}")
    return tuple(sorted(value))


def _hashes(name: str, value: Any, *, empty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple or (not empty and not value):
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    if any(type(item) is not str or not _HASH.fullmatch(item) for item in value):
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    if len(set(value)) != len(value):
        raise ShadowPhase11OwnerReviewValidationError(f"duplicate {name}")
    return tuple(sorted(value))


def _comments(name: str, value: Any, *, empty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple or (not empty and not value):
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    if any(
        type(item) is not str or not item.strip() or item != item.strip()
        for item in value
    ):
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    if len(set(value)) != len(value):
        raise ShadowPhase11OwnerReviewValidationError(f"duplicate {name}")
    return tuple(sorted(value))


def _reference(name: str, value: Any) -> str:
    if type(value) is not str or not _REFERENCE.fullmatch(value):
        raise ShadowPhase11OwnerReviewValidationError(f"invalid {name}")
    return value


def _baseline(value: Any) -> str:
    if (
        type(value) is not str
        or not _COMMIT.fullmatch(value)
        or value != _LOCKED_PHASE09_BASELINE
    ):
        raise ShadowPhase11OwnerReviewValidationError("invalid locked baseline")
    return value


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowPhase11OwnerReviewValidationError(
            "owner-review evidence must prove zero production effect"
        )


_DIMENSION_DECISION_FIELDS = frozenset(
    {
        "schema_version",
        "owner_dimension_decision_id",
        "dimension",
        "owner_decision",
        "source_readiness",
        "owner_rationale",
        "evidence_references",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11OwnerDimensionDecisionV1:
    schema_version: str
    owner_dimension_decision_id: str
    dimension: ShadowPhase11EvidenceDimensionV1
    owner_decision: ShadowPhase11OwnerEvidenceDecisionV1
    source_readiness: ShadowPhase11EvidenceReadinessV1
    owner_rationale: str
    evidence_references: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _DIMENSION_DECISION_FIELDS:
            raise ShadowPhase11OwnerReviewValidationError(
                "invalid owner dimension decision fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-owner-dimension-decision-v1"
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "unsupported owner dimension decision schema"
            )
        dimension = _exact_enum(
            "dimension", values["dimension"], ShadowPhase11EvidenceDimensionV1
        )
        decision = _exact_enum(
            "owner_decision",
            values["owner_decision"],
            ShadowPhase11OwnerEvidenceDecisionV1,
        )
        readiness = _exact_enum(
            "source_readiness",
            values["source_readiness"],
            ShadowPhase11EvidenceReadinessV1,
        )
        rationale = values["owner_rationale"]
        if (
            type(rationale) is not str
            or not rationale.strip()
            or rationale != rationale.strip()
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "invalid owner_rationale"
            )
        references = _hashes(
            "evidence_references", values["evidence_references"]
        )
        reasons = _codes("reason_codes", values["reason_codes"])
        if (
            decision is ShadowPhase11OwnerEvidenceDecisionV1.ACCEPTED
            and readiness
            in {
                ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE,
                ShadowPhase11EvidenceReadinessV1.UNAVAILABLE,
            }
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "unavailable or insufficient evidence cannot be accepted"
            )
        material = {
            "schema_version": values["schema_version"],
            "dimension": dimension,
            "owner_decision": decision,
            "source_readiness": readiness,
            "owner_rationale": rationale,
            "evidence_references": references,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["owner_dimension_decision_id"],
            "owner_dimension_decision_id",
        )
        normalized = {
            **material,
            "owner_dimension_decision_id": identity,
        }
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.owner_dimension_decision_id


_OWNER_INPUT_FIELDS = frozenset(
    {
        "schema_version",
        "owner_decision_input_id",
        "owner_reference",
        "owner_decision_reference",
        "decision_source",
        "dimension_decisions",
        "limitation_references",
        "limitations_decision",
        "overall_decision",
        "phase_12_enablement_recommendation",
        "recommendation_preconditions",
        "owner_comments",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11OwnerDecisionInputV1:
    schema_version: str
    owner_decision_input_id: str
    owner_reference: str
    owner_decision_reference: str
    decision_source: ShadowPhase11OwnerDecisionSourceV1
    dimension_decisions: tuple[ShadowPhase11OwnerDimensionDecisionV1, ...]
    limitation_references: tuple[str, ...]
    limitations_decision: ShadowPhase11OwnerLimitationsDecisionV1
    overall_decision: ShadowPhase11OwnerOverallDecisionV1
    phase_12_enablement_recommendation: ShadowPhase12EnablementRecommendationV1
    recommendation_preconditions: tuple[str, ...]
    owner_comments: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _OWNER_INPUT_FIELDS:
            raise ShadowPhase11OwnerReviewValidationError(
                "invalid owner decision input fields"
            )
        if values["schema_version"] != "phase11-shadow-owner-decision-input-v1":
            raise ShadowPhase11OwnerReviewValidationError(
                "unsupported owner decision input schema"
            )
        owner_reference = _reference(
            "owner_reference", values["owner_reference"]
        )
        decision_reference = _reference(
            "owner_decision_reference", values["owner_decision_reference"]
        )
        source = _exact_enum(
            "decision_source",
            values["decision_source"],
            ShadowPhase11OwnerDecisionSourceV1,
        )
        supplied_decisions = values["dimension_decisions"]
        if (
            type(supplied_decisions) is not tuple
            or len(supplied_decisions) != len(ShadowPhase11EvidenceDimensionV1)
            or any(
                type(item) is not ShadowPhase11OwnerDimensionDecisionV1
                for item in supplied_decisions
            )
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "exactly five owner dimension decisions are required"
            )
        by_dimension: dict[
            ShadowPhase11EvidenceDimensionV1,
            ShadowPhase11OwnerDimensionDecisionV1,
        ] = {}
        for item in supplied_decisions:
            if item.dimension in by_dimension:
                raise ShadowPhase11OwnerReviewValidationError(
                    "duplicate owner dimension decision"
                )
            by_dimension[item.dimension] = item
        required_dimensions = tuple(ShadowPhase11EvidenceDimensionV1)
        if set(by_dimension) != set(required_dimensions):
            raise ShadowPhase11OwnerReviewValidationError(
                "missing owner dimension decision"
            )
        decisions = tuple(by_dimension[item] for item in required_dimensions)
        limitations = _codes(
            "limitation_references",
            values["limitation_references"],
            empty=True,
        )
        limitations_decision = _exact_enum(
            "limitations_decision",
            values["limitations_decision"],
            ShadowPhase11OwnerLimitationsDecisionV1,
        )
        overall = _exact_enum(
            "overall_decision",
            values["overall_decision"],
            ShadowPhase11OwnerOverallDecisionV1,
        )
        recommendation = _exact_enum(
            "phase_12_enablement_recommendation",
            values["phase_12_enablement_recommendation"],
            ShadowPhase12EnablementRecommendationV1,
        )
        preconditions = _codes(
            "recommendation_preconditions",
            values["recommendation_preconditions"],
            empty=True,
        )
        comments = _comments("owner_comments", values["owner_comments"])
        reasons = _codes("reason_codes", values["reason_codes"])
        if (
            recommendation
            is ShadowPhase12EnablementRecommendationV1.RECOMMEND_ENABLEMENT_WITH_PRECONDITIONS
        ):
            if overall is not ShadowPhase11OwnerOverallDecisionV1.ACCEPTED:
                raise ShadowPhase11OwnerReviewValidationError(
                    "enablement recommendation requires accepted disposition"
                )
            if (
                limitations_decision
                is not ShadowPhase11OwnerLimitationsDecisionV1.ACCEPTED
            ):
                raise ShadowPhase11OwnerReviewValidationError(
                    "enablement recommendation requires accepted limitations"
                )
            if any(
                item.owner_decision
                is not ShadowPhase11OwnerEvidenceDecisionV1.ACCEPTED
                for item in decisions
            ):
                raise ShadowPhase11OwnerReviewValidationError(
                    "enablement recommendation requires accepted dimensions"
                )
            if not _REQUIRED_PRECONDITIONS.issubset(preconditions):
                raise ShadowPhase11OwnerReviewValidationError(
                    "enablement recommendation lacks budget preconditions"
                )
        material = {
            "schema_version": values["schema_version"],
            "owner_reference": owner_reference,
            "owner_decision_reference": decision_reference,
            "decision_source": source,
            "dimension_decision_ids": tuple(item.identity for item in decisions),
            "limitation_references": limitations,
            "limitations_decision": limitations_decision,
            "overall_decision": overall,
            "phase_12_enablement_recommendation": recommendation,
            "recommendation_preconditions": preconditions,
            "owner_comments": comments,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["owner_decision_input_id"],
            "owner_decision_input_id",
        )
        normalized = {
            **values,
            "owner_decision_input_id": identity,
            "owner_reference": owner_reference,
            "owner_decision_reference": decision_reference,
            "decision_source": source,
            "dimension_decisions": decisions,
            "limitation_references": limitations,
            "limitations_decision": limitations_decision,
            "overall_decision": overall,
            "phase_12_enablement_recommendation": recommendation,
            "recommendation_preconditions": preconditions,
            "owner_comments": comments,
            "reason_codes": reasons,
        }
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.owner_decision_input_id


_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "owner_review_plan_id",
        "exit_gate_report",
        "owner_decision_input",
        "reviewed_at",
        "locked_baseline_commit",
        "scope",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11OwnerReviewPlanV1:
    schema_version: str
    owner_review_plan_id: str
    exit_gate_report: ShadowPhase11ExitGateReportV1
    owner_decision_input: ShadowPhase11OwnerDecisionInputV1
    reviewed_at: datetime
    locked_baseline_commit: str
    scope: ShadowPhase11OwnerReviewScopeV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PLAN_FIELDS:
            raise ShadowPhase11OwnerReviewValidationError(
                "invalid owner review plan fields"
            )
        if values["schema_version"] != "phase11-shadow-owner-review-plan-v1":
            raise ShadowPhase11OwnerReviewValidationError(
                "unsupported owner review plan schema"
            )
        report = values["exit_gate_report"]
        decision_input = values["owner_decision_input"]
        if type(report) is not ShadowPhase11ExitGateReportV1:
            raise ShadowPhase11OwnerReviewValidationError(
                "exit_gate_report must be exact immutable exit-gate evidence"
            )
        if type(decision_input) is not ShadowPhase11OwnerDecisionInputV1:
            raise ShadowPhase11OwnerReviewValidationError(
                "owner_decision_input must be exact immutable decision evidence"
            )
        baseline = _baseline(values["locked_baseline_commit"])
        if report.locked_baseline_commit != baseline:
            raise ShadowPhase11OwnerReviewValidationError(
                "exit-gate baseline mismatch"
            )
        reviewed_at = _require_utc("reviewed_at", values["reviewed_at"])
        evaluated_at = _require_utc("exit-gate evaluated_at", report.evaluated_at)
        if reviewed_at < evaluated_at:
            raise ShadowPhase11OwnerReviewValidationError(
                "reviewed_at precedes exit-gate evaluation"
            )
        scope = _exact_enum(
            "scope", values["scope"], ShadowPhase11OwnerReviewScopeV1
        )
        if (
            report.owner_acceptance_status
            is not ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED
            or report.limitations_acceptance_status
            is not ShadowPhase11LimitationsAcceptanceStatusV1.NOT_RECORDED
            or report.phase_12_recommendation_status
            is not ShadowPhase12RecommendationStatusV1.NOT_ISSUED
            or report.owner_budget_gate_status
            is not ShadowOwnerBudgetGateStatusV1.NOT_APPROVED
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "exit-gate authority states are not frozen"
            )
        _zero_effect(
            report.production_effect, report.zero_production_effect_proof
        )
        _zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        reasons = _codes("reason_codes", values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "exit_gate_report_id": report.identity,
            "owner_decision_input_id": decision_input.identity,
            "reviewed_at": reviewed_at,
            "locked_baseline_commit": baseline,
            "scope": scope,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _identity(
            material, values["owner_review_plan_id"], "owner_review_plan_id"
        )
        normalized = {
            **values,
            "owner_review_plan_id": identity,
            "exit_gate_report": report,
            "owner_decision_input": decision_input,
            "reviewed_at": reviewed_at,
            "locked_baseline_commit": baseline,
            "scope": scope,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.owner_review_plan_id


@dataclass(frozen=True, slots=True)
class ShadowPhase11OwnerReviewRecordV1:
    schema_version: str
    owner_review_record_id: str
    owner_review_plan_id: str
    exit_gate_report_id: str
    owner_decision_input_id: str
    owner_reference: str
    owner_decision_reference: str
    decision_source: ShadowPhase11OwnerDecisionSourceV1
    locked_baseline_commit: str
    exit_gate_evaluated_at: datetime
    reviewed_at: datetime
    source_mechanical_readiness: ShadowPhase11MechanicalReadinessV1
    dimension_decisions: tuple[ShadowPhase11OwnerDimensionDecisionV1, ...]
    source_dimension_readiness_by_dimension: Mapping[
        ShadowPhase11EvidenceDimensionV1, ShadowPhase11EvidenceReadinessV1
    ]
    declared_limitations: tuple[str, ...]
    limitations_decision: ShadowPhase11OwnerLimitationsDecisionV1
    overall_decision: ShadowPhase11OwnerOverallDecisionV1
    phase_12_enablement_recommendation: ShadowPhase12EnablementRecommendationV1
    recommendation_preconditions: tuple[str, ...]
    unresolved_evidence_gaps: tuple[str, ...]
    owner_comments: tuple[str, ...]
    source_owner_acceptance_status: ShadowPhase11OwnerAcceptanceStatusV1
    source_limitations_acceptance_status: (
        ShadowPhase11LimitationsAcceptanceStatusV1
    )
    source_phase_12_recommendation_status: ShadowPhase12RecommendationStatusV1
    owner_budget_gate_status: ShadowOwnerBudgetGateStatusV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.owner_review_record_id


def _source_readiness(
    report: ShadowPhase11ExitGateReportV1,
) -> Mapping[ShadowPhase11EvidenceDimensionV1, ShadowPhase11EvidenceReadinessV1]:
    results = report.evidence_dimension_results
    if (
        type(results) is not tuple
        or len(results) != len(ShadowPhase11EvidenceDimensionV1)
        or any(type(item) is not ShadowPhase11EvidenceDimensionResultV1 for item in results)
    ):
        raise ShadowPhase11OwnerReviewValidationError(
            "invalid source evidence dimension results"
        )
    by_dimension: dict[
        ShadowPhase11EvidenceDimensionV1, ShadowPhase11EvidenceReadinessV1
    ] = {}
    for result in results:
        if type(result.dimension) is not ShadowPhase11EvidenceDimensionV1:
            raise ShadowPhase11OwnerReviewValidationError(
                "invalid source evidence dimension"
            )
        if result.dimension in by_dimension:
            raise ShadowPhase11OwnerReviewValidationError(
                "duplicate source evidence dimension"
            )
        if type(result.readiness) is not ShadowPhase11EvidenceReadinessV1:
            raise ShadowPhase11OwnerReviewValidationError(
                "invalid source evidence readiness"
            )
        by_dimension[result.dimension] = result.readiness
    required = tuple(ShadowPhase11EvidenceDimensionV1)
    if set(by_dimension) != set(required):
        raise ShadowPhase11OwnerReviewValidationError(
            "missing source evidence dimension"
        )
    return MappingProxyType({item: by_dimension[item] for item in required})


def _validate_decision_consistency(
    plan: ShadowPhase11OwnerReviewPlanV1,
) -> Mapping[ShadowPhase11EvidenceDimensionV1, ShadowPhase11EvidenceReadinessV1]:
    report = plan.exit_gate_report
    supplied = plan.owner_decision_input
    readiness = _source_readiness(report)
    for decision in supplied.dimension_decisions:
        if decision.source_readiness is not readiness[decision.dimension]:
            raise ShadowPhase11OwnerReviewValidationError(
                "observed source readiness does not match exit-gate evidence"
            )
        if (
            decision.owner_decision
            is ShadowPhase11OwnerEvidenceDecisionV1.ACCEPTED
            and readiness[decision.dimension]
            in {
                ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE,
                ShadowPhase11EvidenceReadinessV1.UNAVAILABLE,
            }
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "source readiness does not permit acceptance"
            )
    if set(supplied.limitation_references) != set(report.declared_limitations):
        raise ShadowPhase11OwnerReviewValidationError(
            "owner decision must bind every declared limitation"
        )
    if supplied.overall_decision is ShadowPhase11OwnerOverallDecisionV1.ACCEPTED:
        if (
            report.mechanical_readiness
            is not ShadowPhase11MechanicalReadinessV1.READY_FOR_OWNER_REVIEW
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "overall acceptance requires ready source evidence"
            )
        if any(
            item.owner_decision
            is not ShadowPhase11OwnerEvidenceDecisionV1.ACCEPTED
            for item in supplied.dimension_decisions
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "overall acceptance requires all dimensions accepted"
            )
        if (
            supplied.limitations_decision
            is not ShadowPhase11OwnerLimitationsDecisionV1.ACCEPTED
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "overall acceptance requires limitations accepted"
            )
        if report.unresolved_evidence_gaps:
            raise ShadowPhase11OwnerReviewValidationError(
                "overall acceptance is blocked by unresolved evidence gaps"
            )
    if (
        supplied.phase_12_enablement_recommendation
        is ShadowPhase12EnablementRecommendationV1.RECOMMEND_ENABLEMENT_WITH_PRECONDITIONS
    ):
        if (
            supplied.overall_decision
            is not ShadowPhase11OwnerOverallDecisionV1.ACCEPTED
            or report.mechanical_readiness
            is not ShadowPhase11MechanicalReadinessV1.READY_FOR_OWNER_REVIEW
            or supplied.limitations_decision
            is not ShadowPhase11OwnerLimitationsDecisionV1.ACCEPTED
            or any(
                item.owner_decision
                is not ShadowPhase11OwnerEvidenceDecisionV1.ACCEPTED
                for item in supplied.dimension_decisions
            )
            or not _REQUIRED_PRECONDITIONS.issubset(
                supplied.recommendation_preconditions
            )
            or report.owner_budget_gate_status
            is not ShadowOwnerBudgetGateStatusV1.NOT_APPROVED
        ):
            raise ShadowPhase11OwnerReviewValidationError(
                "inconsistent Phase 12 recommendation evidence"
            )
    return readiness


class ShadowPhase11OwnerReviewRecorderV1:
    """Stateless recorder for explicit owner-review decision evidence."""

    __slots__ = ()

    def record(
        self, plan: ShadowPhase11OwnerReviewPlanV1
    ) -> ShadowPhase11OwnerReviewRecordV1:
        if type(plan) is not ShadowPhase11OwnerReviewPlanV1:
            raise ShadowPhase11OwnerReviewValidationError(
                "record requires an exact owner-review plan"
            )
        readiness = _validate_decision_consistency(plan)
        report = plan.exit_gate_report
        supplied = plan.owner_decision_input
        reasons = tuple(
            sorted(
                set(plan.reason_codes)
                | set(supplied.reason_codes)
                | {"EXPLICIT_OWNER_DECISION_RECORDED"}
            )
        )
        material = {
            "schema_version": "phase11-shadow-owner-review-record-v1",
            "owner_review_plan_id": plan.identity,
            "exit_gate_report_id": report.identity,
            "owner_decision_input_id": supplied.identity,
            "owner_reference": supplied.owner_reference,
            "owner_decision_reference": supplied.owner_decision_reference,
            "decision_source": supplied.decision_source,
            "locked_baseline_commit": plan.locked_baseline_commit,
            "exit_gate_evaluated_at": report.evaluated_at,
            "reviewed_at": plan.reviewed_at,
            "source_mechanical_readiness": report.mechanical_readiness,
            "dimension_decision_ids": tuple(
                item.identity for item in supplied.dimension_decisions
            ),
            "source_dimension_readiness_by_dimension": {
                item.value: readiness[item]
                for item in ShadowPhase11EvidenceDimensionV1
            },
            "declared_limitations": tuple(sorted(report.declared_limitations)),
            "limitations_decision": supplied.limitations_decision,
            "overall_decision": supplied.overall_decision,
            "phase_12_enablement_recommendation": (
                supplied.phase_12_enablement_recommendation
            ),
            "recommendation_preconditions": supplied.recommendation_preconditions,
            "unresolved_evidence_gaps": tuple(
                sorted(report.unresolved_evidence_gaps)
            ),
            "owner_comments": supplied.owner_comments,
            "source_owner_acceptance_status": report.owner_acceptance_status,
            "source_limitations_acceptance_status": (
                report.limitations_acceptance_status
            ),
            "source_phase_12_recommendation_status": (
                report.phase_12_recommendation_status
            ),
            "owner_budget_gate_status": report.owner_budget_gate_status,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _derived_identity(material)
        return ShadowPhase11OwnerReviewRecordV1(
            schema_version=material["schema_version"],
            owner_review_record_id=identity,
            owner_review_plan_id=plan.identity,
            exit_gate_report_id=report.identity,
            owner_decision_input_id=supplied.identity,
            owner_reference=supplied.owner_reference,
            owner_decision_reference=supplied.owner_decision_reference,
            decision_source=supplied.decision_source,
            locked_baseline_commit=plan.locked_baseline_commit,
            exit_gate_evaluated_at=report.evaluated_at,
            reviewed_at=plan.reviewed_at,
            source_mechanical_readiness=report.mechanical_readiness,
            dimension_decisions=supplied.dimension_decisions,
            source_dimension_readiness_by_dimension=readiness,
            declared_limitations=tuple(sorted(report.declared_limitations)),
            limitations_decision=supplied.limitations_decision,
            overall_decision=supplied.overall_decision,
            phase_12_enablement_recommendation=(
                supplied.phase_12_enablement_recommendation
            ),
            recommendation_preconditions=supplied.recommendation_preconditions,
            unresolved_evidence_gaps=tuple(
                sorted(report.unresolved_evidence_gaps)
            ),
            owner_comments=supplied.owner_comments,
            source_owner_acceptance_status=report.owner_acceptance_status,
            source_limitations_acceptance_status=(
                report.limitations_acceptance_status
            ),
            source_phase_12_recommendation_status=(
                report.phase_12_recommendation_status
            ),
            owner_budget_gate_status=report.owner_budget_gate_status,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
