"""Immutable route-attributed actual-cost evidence for Phase 11.

This module joins already-created quality and detached alternative-arm
evidence.  It performs no upstream evaluation, provider execution, pricing,
projection, persistence, or production action.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from engine.phase_11_shadow_alternative_arm_evaluator_v1 import (
    AlternativeArmExecutionStatusV1,
    AlternativeArmIdentityV1,
    ShadowAlternativeArmEvaluationV1,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    MetricAvailabilityV1,
)
from engine.phase_11_shadow_quality_evaluator_v1 import (
    ShadowQualityObservationV1,
)


_UTC = timezone.utc
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"
_ROUTES = ("L0", "L1", "L2", "L1_TO_L2")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_MEAN_QUANTUM = Decimal("0.0000000001")


class ShadowRouteCostValidationError(ValueError):
    """Raised when route-attributed cost evidence is inconsistent."""


class RouteCostEvidenceScopeV1(StrEnum):
    EVENT_LEVEL_ROUTE_ATTRIBUTION = "EVENT_LEVEL_ROUTE_ATTRIBUTION"


class RouteCostAggregationScopeV1(StrEnum):
    ROUTE_KEYED_ACTUAL_COST = "ROUTE_KEYED_ACTUAL_COST"


class RouteCostCoverageStatusV1(StrEnum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RouteCostMetricAvailabilityV1(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


def _require_utc(name: str, value: Any) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() != _UTC.utcoffset(value)
    ):
        raise ShadowRouteCostValidationError(f"{name} must be a UTC datetime")
    return value


def _parse_timestamp(name: str, value: Any) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ShadowRouteCostValidationError(f"{name} must be a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ShadowRouteCostValidationError(f"invalid {name}") from exc
    return _require_utc(name, parsed)


def _reasons(value: Any) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or not value
        or any(type(item) is not str or not _REASON.fullmatch(item) for item in value)
        or tuple(sorted(set(value))) != value
    ):
        raise ShadowRouteCostValidationError(
            "reason_codes must be a sorted unique tuple of deterministic codes"
        )
    return value


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT:
        raise ShadowRouteCostValidationError("production_effect must be NONE")
    if proof != _ZERO_PROOF:
        raise ShadowRouteCostValidationError(
            "zero_production_effect_proof must be PROVEN_NONE"
        )


def _canonical(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowRouteCostValidationError("Decimal values must be finite")
        if value == 0:
            return "0"
        return format(value.normalize(), "f")
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
    raise ShadowRouteCostValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic canonical UTF-8 JSON."""

    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def lowercase_sha256(value: bytes) -> str:
    """Return a lowercase SHA-256 digest for exact bytes."""

    if type(value) is not bytes:
        raise ShadowRouteCostValidationError("sha256 input must be exact bytes")
    return hashlib.sha256(value).hexdigest()


def _derived_identity(material: Any) -> str:
    return lowercase_sha256(canonical_json_bytes(material))


def _identity(material: Any, supplied: Any, name: str) -> str:
    derived = _derived_identity(material)
    if supplied is not None and (
        type(supplied) is not str
        or not _HASH.fullmatch(supplied)
        or supplied != derived
    ):
        raise ShadowRouteCostValidationError(f"invalid {name}")
    return derived


def _exact_non_negative(name: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ShadowRouteCostValidationError(
            f"{name} must be an exact non-negative integer"
        )
    return value


def _available_cost(availability: Any, value: Any) -> Decimal | None:
    if availability is MetricAvailabilityV1.AVAILABLE:
        if (
            type(value) is not Decimal
            or not value.is_finite()
            or value < Decimal("0")
        ):
            raise ShadowRouteCostValidationError(
                "available actual_cost must be a finite non-negative Decimal"
            )
        return value
    if availability is MetricAvailabilityV1.UNAVAILABLE:
        if value is not None:
            raise ShadowRouteCostValidationError(
                "unavailable actual_cost must remain None"
            )
        return None
    raise ShadowRouteCostValidationError("unsupported cost availability")


_EVENT_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "route_cost_evidence_plan_id",
        "quality_observation",
        "alternative_arm_evaluation",
        "bridged_at",
        "scope",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowRouteCostEvidencePlanV1:
    schema_version: str
    route_cost_evidence_plan_id: str
    quality_observation: ShadowQualityObservationV1
    alternative_arm_evaluation: ShadowAlternativeArmEvaluationV1
    bridged_at: datetime
    scope: RouteCostEvidenceScopeV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _EVENT_PLAN_FIELDS:
            raise ShadowRouteCostValidationError("invalid route-cost plan fields")
        if values["schema_version"] != "phase11-shadow-route-cost-evidence-plan-v1":
            raise ShadowRouteCostValidationError("unsupported route-cost plan schema")
        quality = values["quality_observation"]
        evaluation = values["alternative_arm_evaluation"]
        if type(quality) is not ShadowQualityObservationV1:
            raise ShadowRouteCostValidationError("invalid quality observation child")
        if type(evaluation) is not ShadowAlternativeArmEvaluationV1:
            raise ShadowRouteCostValidationError(
                "invalid alternative-arm evaluation child"
            )
        if quality.candidate_id != evaluation.candidate_id:
            raise ShadowRouteCostValidationError("candidate lineage mismatch")
        if quality.event_id != evaluation.event_id:
            raise ShadowRouteCostValidationError("event lineage mismatch")
        if quality.locked_baseline_commit != evaluation.locked_baseline_commit:
            raise ShadowRouteCostValidationError("locked baseline mismatch")
        if quality.locked_baseline_commit != LOCKED_PHASE09_BASELINE:
            raise ShadowRouteCostValidationError("unsupported locked baseline")
        if quality.quality_observation_id != evaluation.quality_observation_id:
            raise ShadowRouteCostValidationError("quality observation identity mismatch")
        if quality.original_treatment_route not in _ROUTES:
            raise ShadowRouteCostValidationError("unsupported committed route")
        _zero_effect(
            quality.production_effect, quality.zero_production_effect_proof
        )
        _zero_effect(
            evaluation.production_effect, evaluation.zero_production_effect_proof
        )
        _zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        _available_cost(evaluation.cost_availability, evaluation.actual_cost)
        quality_at = _parse_timestamp(
            "quality observation evaluated_at", quality.evaluated_at
        )
        completed_at = _require_utc(
            "alternative evaluation completed_at", evaluation.completed_at
        )
        evaluated_at = _require_utc(
            "alternative evaluation evaluated_at", evaluation.evaluated_at
        )
        bridged_at = _require_utc("bridged_at", values["bridged_at"])
        if completed_at < quality_at or evaluated_at < completed_at:
            raise ShadowRouteCostValidationError("invalid child timestamp ordering")
        if bridged_at < evaluated_at or bridged_at < quality_at:
            raise ShadowRouteCostValidationError("bridged_at precedes child evidence")
        if values["scope"] is not RouteCostEvidenceScopeV1.EVENT_LEVEL_ROUTE_ATTRIBUTION:
            raise ShadowRouteCostValidationError("unsupported route-cost evidence scope")
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "quality_observation_id": quality.quality_observation_id,
            "alternative_arm_evaluation_id": evaluation.alternative_arm_evaluation_id,
            "bridged_at": bridged_at,
            "scope": values["scope"],
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        plan_id = _identity(
            material,
            values["route_cost_evidence_plan_id"],
            "route_cost_evidence_plan_id",
        )
        normalized = {
            **values,
            "route_cost_evidence_plan_id": plan_id,
            "bridged_at": bridged_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.route_cost_evidence_plan_id


_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "route_cost_evidence_id",
        "route_cost_evidence_plan_id",
        "quality_observation_id",
        "alternative_arm_evaluation_id",
        "candidate_id",
        "event_id",
        "locked_baseline_commit",
        "route",
        "alternative_arm_identity",
        "execution_status",
        "cost_availability",
        "actual_cost",
        "quality_evaluated_at",
        "alternative_completed_at",
        "alternative_evaluated_at",
        "bridged_at",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowRouteCostEvidenceV1:
    schema_version: str
    route_cost_evidence_id: str
    route_cost_evidence_plan_id: str
    quality_observation_id: str
    alternative_arm_evaluation_id: str
    candidate_id: str
    event_id: str
    locked_baseline_commit: str
    route: str
    alternative_arm_identity: AlternativeArmIdentityV1
    execution_status: AlternativeArmExecutionStatusV1
    cost_availability: MetricAvailabilityV1
    actual_cost: Decimal | None
    quality_evaluated_at: str
    alternative_completed_at: datetime
    alternative_evaluated_at: datetime
    bridged_at: datetime
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _EVIDENCE_FIELDS:
            raise ShadowRouteCostValidationError("invalid route-cost evidence fields")
        if values["schema_version"] != "phase11-shadow-route-cost-evidence-v1":
            raise ShadowRouteCostValidationError(
                "unsupported route-cost evidence schema"
            )
        for name in (
            "route_cost_evidence_plan_id",
            "quality_observation_id",
            "alternative_arm_evaluation_id",
        ):
            if type(values[name]) is not str or not _HASH.fullmatch(values[name]):
                raise ShadowRouteCostValidationError(f"invalid {name}")
        if values["locked_baseline_commit"] != LOCKED_PHASE09_BASELINE:
            raise ShadowRouteCostValidationError("unsupported locked baseline")
        if values["route"] not in _ROUTES:
            raise ShadowRouteCostValidationError("unsupported route")
        if type(values["alternative_arm_identity"]) is not AlternativeArmIdentityV1:
            raise ShadowRouteCostValidationError("invalid alternative arm identity")
        if type(values["execution_status"]) is not AlternativeArmExecutionStatusV1:
            raise ShadowRouteCostValidationError("invalid execution status")
        cost = _available_cost(values["cost_availability"], values["actual_cost"])
        _parse_timestamp("quality_evaluated_at", values["quality_evaluated_at"])
        completed_at = _require_utc(
            "alternative_completed_at", values["alternative_completed_at"]
        )
        evaluated_at = _require_utc(
            "alternative_evaluated_at", values["alternative_evaluated_at"]
        )
        bridged_at = _require_utc("bridged_at", values["bridged_at"])
        if evaluated_at < completed_at or bridged_at < evaluated_at:
            raise ShadowRouteCostValidationError("invalid evidence timestamp ordering")
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        material = {
            name: item
            for name, item in values.items()
            if name != "route_cost_evidence_id"
        }
        material["actual_cost"] = cost
        material["reason_codes"] = reasons
        evidence_id = _identity(
            material,
            values["route_cost_evidence_id"],
            "route_cost_evidence_id",
        )
        normalized = {
            **values,
            "route_cost_evidence_id": evidence_id,
            "actual_cost": cost,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.route_cost_evidence_id


class ShadowRouteCostEvidenceBuilderV1:
    """Stateless builder of one route-attributed cost evidence value."""

    __slots__ = ()

    def build(self, plan: ShadowRouteCostEvidencePlanV1) -> ShadowRouteCostEvidenceV1:
        if type(plan) is not ShadowRouteCostEvidencePlanV1:
            raise ShadowRouteCostValidationError("invalid route-cost evidence plan")
        quality = plan.quality_observation
        evaluation = plan.alternative_arm_evaluation
        return ShadowRouteCostEvidenceV1(
            schema_version="phase11-shadow-route-cost-evidence-v1",
            route_cost_evidence_id=None,
            route_cost_evidence_plan_id=plan.route_cost_evidence_plan_id,
            quality_observation_id=quality.quality_observation_id,
            alternative_arm_evaluation_id=evaluation.alternative_arm_evaluation_id,
            candidate_id=quality.candidate_id,
            event_id=quality.event_id,
            locked_baseline_commit=quality.locked_baseline_commit,
            route=quality.original_treatment_route,
            alternative_arm_identity=evaluation.arm_identity,
            execution_status=evaluation.execution_status,
            cost_availability=evaluation.cost_availability,
            actual_cost=evaluation.actual_cost,
            quality_evaluated_at=quality.evaluated_at,
            alternative_completed_at=evaluation.completed_at,
            alternative_evaluated_at=evaluation.evaluated_at,
            bridged_at=plan.bridged_at,
            reason_codes=plan.reason_codes,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )


_COVERAGE_FIELDS = frozenset(
    {
        "schema_version",
        "route_cost_coverage_plan_id",
        "minimum_total_evidence",
        "minimum_l0_evidence",
        "minimum_l1_evidence",
        "minimum_direct_l2_evidence",
        "minimum_l1_to_l2_evidence",
        "minimum_l0_available_cost",
        "minimum_l1_available_cost",
        "minimum_direct_l2_available_cost",
        "minimum_l1_to_l2_available_cost",
        "reason_codes",
    }
)
_COVERAGE_TARGETS = (
    "minimum_total_evidence",
    "minimum_l0_evidence",
    "minimum_l1_evidence",
    "minimum_direct_l2_evidence",
    "minimum_l1_to_l2_evidence",
    "minimum_l0_available_cost",
    "minimum_l1_available_cost",
    "minimum_direct_l2_available_cost",
    "minimum_l1_to_l2_available_cost",
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowRouteCostCoveragePlanV1:
    schema_version: str
    route_cost_coverage_plan_id: str
    minimum_total_evidence: int
    minimum_l0_evidence: int
    minimum_l1_evidence: int
    minimum_direct_l2_evidence: int
    minimum_l1_to_l2_evidence: int
    minimum_l0_available_cost: int
    minimum_l1_available_cost: int
    minimum_direct_l2_available_cost: int
    minimum_l1_to_l2_available_cost: int
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _COVERAGE_FIELDS:
            raise ShadowRouteCostValidationError("invalid coverage-plan fields")
        if values["schema_version"] != "phase11-shadow-route-cost-coverage-plan-v1":
            raise ShadowRouteCostValidationError("unsupported coverage-plan schema")
        normalized_targets = {
            name: _exact_non_negative(name, values[name])
            for name in _COVERAGE_TARGETS
        }
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            **normalized_targets,
            "reason_codes": reasons,
        }
        coverage_id = _identity(
            material,
            values["route_cost_coverage_plan_id"],
            "route_cost_coverage_plan_id",
        )
        normalized = {
            **values,
            **normalized_targets,
            "route_cost_coverage_plan_id": coverage_id,
            "reason_codes": reasons,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.route_cost_coverage_plan_id


_SET_FIELDS = frozenset(
    {
        "schema_version",
        "route_cost_evidence_set_id",
        "route_cost_evidence",
        "window_start",
        "window_end",
        "locked_baseline_commit",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowRouteCostEvidenceSetV1:
    schema_version: str
    route_cost_evidence_set_id: str
    route_cost_evidence: tuple[ShadowRouteCostEvidenceV1, ...]
    window_start: datetime
    window_end: datetime
    locked_baseline_commit: str
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _SET_FIELDS:
            raise ShadowRouteCostValidationError("invalid evidence-set fields")
        if values["schema_version"] != "phase11-shadow-route-cost-evidence-set-v1":
            raise ShadowRouteCostValidationError("unsupported evidence-set schema")
        children = values["route_cost_evidence"]
        if (
            type(children) is not tuple
            or not children
            or any(type(item) is not ShadowRouteCostEvidenceV1 for item in children)
        ):
            raise ShadowRouteCostValidationError(
                "route_cost_evidence must be a non-empty exact tuple"
            )
        if values["locked_baseline_commit"] != LOCKED_PHASE09_BASELINE:
            raise ShadowRouteCostValidationError("unsupported set baseline")
        window_start = _require_utc("window_start", values["window_start"])
        window_end = _require_utc("window_end", values["window_end"])
        if window_end < window_start:
            raise ShadowRouteCostValidationError("window_end precedes window_start")
        identities: set[str] = set()
        comparison_keys: set[tuple[str, str, AlternativeArmIdentityV1]] = set()
        for child in children:
            if child.locked_baseline_commit != values["locked_baseline_commit"]:
                raise ShadowRouteCostValidationError("mixed or foreign child baseline")
            _zero_effect(
                child.production_effect, child.zero_production_effect_proof
            )
            if not window_start <= child.bridged_at <= window_end:
                raise ShadowRouteCostValidationError(
                    "route-cost evidence outside inclusive window"
                )
            if child.route_cost_evidence_id in identities:
                raise ShadowRouteCostValidationError("duplicate evidence identity")
            identities.add(child.route_cost_evidence_id)
            key = (
                child.candidate_id,
                child.event_id,
                child.alternative_arm_identity,
            )
            if key in comparison_keys:
                raise ShadowRouteCostValidationError("duplicate comparison key")
            comparison_keys.add(key)
        canonical_children = tuple(
            sorted(children, key=lambda item: item.route_cost_evidence_id)
        )
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "route_cost_evidence_ids": tuple(
                item.route_cost_evidence_id for item in canonical_children
            ),
            "window_start": window_start,
            "window_end": window_end,
            "locked_baseline_commit": values["locked_baseline_commit"],
            "reason_codes": reasons,
        }
        set_id = _identity(
            material,
            values["route_cost_evidence_set_id"],
            "route_cost_evidence_set_id",
        )
        normalized = {
            **values,
            "route_cost_evidence_set_id": set_id,
            "route_cost_evidence": canonical_children,
            "window_start": window_start,
            "window_end": window_end,
            "reason_codes": reasons,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.route_cost_evidence_set_id


_AGGREGATE_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "route_cost_aggregate_plan_id",
        "evidence_set",
        "coverage_plan",
        "generated_at",
        "scope",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowRouteCostAggregatePlanV1:
    schema_version: str
    route_cost_aggregate_plan_id: str
    evidence_set: ShadowRouteCostEvidenceSetV1
    coverage_plan: ShadowRouteCostCoveragePlanV1
    generated_at: datetime
    scope: RouteCostAggregationScopeV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _AGGREGATE_PLAN_FIELDS:
            raise ShadowRouteCostValidationError("invalid aggregate-plan fields")
        if values["schema_version"] != "phase11-shadow-route-cost-aggregate-plan-v1":
            raise ShadowRouteCostValidationError("unsupported aggregate-plan schema")
        evidence_set = values["evidence_set"]
        coverage_plan = values["coverage_plan"]
        if type(evidence_set) is not ShadowRouteCostEvidenceSetV1:
            raise ShadowRouteCostValidationError("invalid route-cost evidence set")
        if type(coverage_plan) is not ShadowRouteCostCoveragePlanV1:
            raise ShadowRouteCostValidationError("invalid route-cost coverage plan")
        generated_at = _require_utc("generated_at", values["generated_at"])
        if generated_at < evidence_set.window_end or any(
            generated_at < child.bridged_at
            for child in evidence_set.route_cost_evidence
        ):
            raise ShadowRouteCostValidationError(
                "generated_at precedes route-cost evidence"
            )
        if values["scope"] is not RouteCostAggregationScopeV1.ROUTE_KEYED_ACTUAL_COST:
            raise ShadowRouteCostValidationError("unsupported aggregation scope")
        _zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "route_cost_evidence_set_id": evidence_set.route_cost_evidence_set_id,
            "route_cost_coverage_plan_id": coverage_plan.route_cost_coverage_plan_id,
            "generated_at": generated_at,
            "scope": values["scope"],
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        plan_id = _identity(
            material,
            values["route_cost_aggregate_plan_id"],
            "route_cost_aggregate_plan_id",
        )
        normalized = {
            **values,
            "route_cost_aggregate_plan_id": plan_id,
            "generated_at": generated_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.route_cost_aggregate_plan_id


@dataclass(frozen=True, slots=True)
class ShadowRouteCostSummaryV1:
    schema_version: str
    route_cost_summary_id: str
    route: str
    total_evidence_count: int
    available_cost_count: int
    unavailable_cost_count: int
    availability: RouteCostMetricAvailabilityV1
    total_actual_cost: Decimal | None
    available_value_mean: Decimal | None
    available_value_denominator: int

    @property
    def identity(self) -> str:
        return self.route_cost_summary_id


@dataclass(frozen=True, slots=True)
class ShadowRouteCostCoverageResultV1:
    schema_version: str
    route_cost_coverage_result_id: str
    target_name: str
    required_count: int
    observed_count: int
    status: RouteCostCoverageStatusV1

    @property
    def identity(self) -> str:
        return self.route_cost_coverage_result_id


@dataclass(frozen=True, slots=True)
class ShadowRouteCostAggregateReportV1:
    schema_version: str
    route_cost_aggregate_report_id: str
    route_cost_aggregate_plan_id: str
    route_cost_evidence_set_id: str
    route_cost_coverage_plan_id: str
    locked_baseline_commit: str
    window_start: datetime
    window_end: datetime
    generated_at: datetime
    total_evidence_count: int
    route_counts: Mapping[str, int]
    route_cost_summaries: Mapping[str, ShadowRouteCostSummaryV1]
    combined_l2_cost_summary: ShadowRouteCostSummaryV1
    coverage_results: tuple[ShadowRouteCostCoverageResultV1, ...]
    coverage_results_by_target: Mapping[str, ShadowRouteCostCoverageResultV1]
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.route_cost_aggregate_report_id


def _summary(
    route: str,
    children: tuple[ShadowRouteCostEvidenceV1, ...],
) -> ShadowRouteCostSummaryV1:
    available_values = tuple(
        child.actual_cost
        for child in children
        if child.cost_availability is MetricAvailabilityV1.AVAILABLE
    )
    available_count = len(available_values)
    unavailable_count = len(children) - available_count
    if available_count == 0:
        availability = RouteCostMetricAvailabilityV1.UNAVAILABLE
        total = None
        mean = None
    else:
        availability = RouteCostMetricAvailabilityV1.AVAILABLE
        total = sum(available_values, Decimal("0"))
        mean = (total / Decimal(available_count)).quantize(
            _MEAN_QUANTUM, rounding=ROUND_HALF_UP
        )
    material = {
        "schema_version": "phase11-shadow-route-cost-summary-v1",
        "route": route,
        "route_cost_evidence_ids": tuple(
            sorted(child.route_cost_evidence_id for child in children)
        ),
        "total_evidence_count": len(children),
        "available_cost_count": available_count,
        "unavailable_cost_count": unavailable_count,
        "availability": availability,
        "total_actual_cost": total,
        "available_value_mean": mean,
        "available_value_denominator": available_count,
    }
    return ShadowRouteCostSummaryV1(
        schema_version=material["schema_version"],
        route_cost_summary_id=_derived_identity(material),
        route=route,
        total_evidence_count=len(children),
        available_cost_count=available_count,
        unavailable_cost_count=unavailable_count,
        availability=availability,
        total_actual_cost=total,
        available_value_mean=mean,
        available_value_denominator=available_count,
    )


def _coverage_result(
    target_name: str, required_count: int, observed_count: int
) -> ShadowRouteCostCoverageResultV1:
    status = (
        RouteCostCoverageStatusV1.MET
        if observed_count >= required_count
        else RouteCostCoverageStatusV1.NOT_MET
    )
    material = {
        "schema_version": "phase11-shadow-route-cost-coverage-result-v1",
        "target_name": target_name,
        "required_count": required_count,
        "observed_count": observed_count,
        "status": status,
    }
    return ShadowRouteCostCoverageResultV1(
        schema_version=material["schema_version"],
        route_cost_coverage_result_id=_derived_identity(material),
        target_name=target_name,
        required_count=required_count,
        observed_count=observed_count,
        status=status,
    )


class ShadowRouteCostAggregatorV1:
    """Stateless aggregator over already-created route-cost evidence."""

    __slots__ = ()

    def aggregate(
        self, plan: ShadowRouteCostAggregatePlanV1
    ) -> ShadowRouteCostAggregateReportV1:
        if type(plan) is not ShadowRouteCostAggregatePlanV1:
            raise ShadowRouteCostValidationError("invalid route-cost aggregate plan")
        children = plan.evidence_set.route_cost_evidence
        grouped = {
            route: tuple(child for child in children if child.route == route)
            for route in _ROUTES
        }
        summaries = {route: _summary(route, grouped[route]) for route in _ROUTES}
        combined_l2_children = grouped["L2"] + grouped["L1_TO_L2"]
        combined_l2 = _summary("COMBINED_L2", combined_l2_children)
        route_counts = {route: len(grouped[route]) for route in _ROUTES}
        observed = {
            "minimum_total_evidence": len(children),
            "minimum_l0_evidence": route_counts["L0"],
            "minimum_l1_evidence": route_counts["L1"],
            "minimum_direct_l2_evidence": route_counts["L2"],
            "minimum_l1_to_l2_evidence": route_counts["L1_TO_L2"],
            "minimum_l0_available_cost": summaries["L0"].available_cost_count,
            "minimum_l1_available_cost": summaries["L1"].available_cost_count,
            "minimum_direct_l2_available_cost": summaries[
                "L2"
            ].available_cost_count,
            "minimum_l1_to_l2_available_cost": summaries[
                "L1_TO_L2"
            ].available_cost_count,
        }
        coverage = plan.coverage_plan
        coverage_results = tuple(
            _coverage_result(name, getattr(coverage, name), observed[name])
            for name in _COVERAGE_TARGETS
        )
        coverage_by_target = {
            result.target_name: result for result in coverage_results
        }
        immutable_route_counts = MappingProxyType(route_counts)
        immutable_summaries = MappingProxyType(summaries)
        immutable_coverage = MappingProxyType(coverage_by_target)
        material = {
            "schema_version": "phase11-shadow-route-cost-aggregate-report-v1",
            "route_cost_aggregate_plan_id": plan.route_cost_aggregate_plan_id,
            "route_cost_evidence_set_id": plan.evidence_set.route_cost_evidence_set_id,
            "route_cost_coverage_plan_id": coverage.route_cost_coverage_plan_id,
            "locked_baseline_commit": plan.evidence_set.locked_baseline_commit,
            "window_start": plan.evidence_set.window_start,
            "window_end": plan.evidence_set.window_end,
            "generated_at": plan.generated_at,
            "total_evidence_count": len(children),
            "route_counts": route_counts,
            "route_cost_summary_ids": {
                route: summary.route_cost_summary_id
                for route, summary in summaries.items()
            },
            "combined_l2_cost_summary_id": combined_l2.route_cost_summary_id,
            "coverage_result_ids": tuple(
                result.route_cost_coverage_result_id
                for result in coverage_results
            ),
            "reason_codes": plan.reason_codes,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        return ShadowRouteCostAggregateReportV1(
            schema_version=material["schema_version"],
            route_cost_aggregate_report_id=_derived_identity(material),
            route_cost_aggregate_plan_id=plan.route_cost_aggregate_plan_id,
            route_cost_evidence_set_id=plan.evidence_set.route_cost_evidence_set_id,
            route_cost_coverage_plan_id=coverage.route_cost_coverage_plan_id,
            locked_baseline_commit=plan.evidence_set.locked_baseline_commit,
            window_start=plan.evidence_set.window_start,
            window_end=plan.evidence_set.window_end,
            generated_at=plan.generated_at,
            total_evidence_count=len(children),
            route_counts=immutable_route_counts,
            route_cost_summaries=immutable_summaries,
            combined_l2_cost_summary=combined_l2,
            coverage_results=coverage_results,
            coverage_results_by_target=immutable_coverage,
            reason_codes=plan.reason_codes,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
