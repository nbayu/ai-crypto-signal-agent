"""Deterministic aggregation of immutable Phase 11 comparative observations.

This module is deliberately evidence-only.  It consumes completed event-level
observations and never executes comparison, finalization, provider, ledger, or
control behavior.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from engine.phase_11_finalization_evidence_bridge_v1 import (
    ShadowTerminalRecordStatusV1,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    ComparisonComparabilityV1,
    ControlTreatmentDecisionDeltaV1,
    MetricAvailabilityV1,
    ShadowComparativeObservationV1,
    StructuredProviderDisagreementV1,
    TreatmentAvailabilityV1,
)


_UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_MEAN_SCALE = Decimal("0.0000000001")
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"


class ShadowComparativeAggregationValidationError(ValueError):
    """Raised when aggregate comparative evidence is inconsistent."""


class ShadowAggregationScopeV1(StrEnum):
    OBSERVATION_SET = "OBSERVATION_SET"


class ShadowAggregateCoverageStatusV1(StrEnum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AggregateMetricAvailabilityV1(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowComparativeAggregationValidationError(
                "canonical datetime must be timezone-aware"
            )
        return value.astimezone(_UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON for identity material."""

    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def lowercase_sha256(value: Any) -> str:
    """Return the lowercase SHA-256 digest of canonical identity material."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _identity(value: Any, supplied: Any, label: str) -> str:
    expected = lowercase_sha256(value)
    if supplied is None:
        return expected
    if type(supplied) is not str or not _HASH.fullmatch(supplied):
        raise ShadowComparativeAggregationValidationError(f"invalid {label}")
    if supplied != expected:
        raise ShadowComparativeAggregationValidationError(
            f"{label} does not match canonical evidence"
        )
    return supplied


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowComparativeAggregationValidationError(
                f"invalid {label}"
            )
        return value.astimezone(_UTC).isoformat().replace("+00:00", "Z")
    if type(value) is not str:
        raise ShadowComparativeAggregationValidationError(f"invalid {label}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ShadowComparativeAggregationValidationError(
            f"invalid {label}"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ShadowComparativeAggregationValidationError(f"invalid {label}")
    return parsed.astimezone(_UTC).isoformat().replace("+00:00", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ShadowComparativeAggregationValidationError(
            "invalid aggregate reason codes"
        )
    reasons = tuple(value)
    if (
        not reasons
        or any(type(item) is not str or not _REASON.fullmatch(item) for item in reasons)
        or tuple(sorted(set(reasons))) != reasons
    ):
        raise ShadowComparativeAggregationValidationError(
            "invalid aggregate reason codes"
        )
    return reasons


def _nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ShadowComparativeAggregationValidationError(f"invalid {label}")
    return value


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowComparativeAggregationValidationError(
            "aggregate evidence must have zero production effect"
        )


_COVERAGE_FIELDS = frozenset(
    {
        "schema_version",
        "coverage_plan_id",
        "minimum_total_observations",
        "minimum_comparable_observations",
        "minimum_clean_treatments",
        "minimum_l0",
        "minimum_l1",
        "minimum_direct_l2",
        "minimum_l1_to_l2",
        "minimum_terminal_treatments",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowAggregateCoveragePlanV1:
    schema_version: str
    coverage_plan_id: str
    minimum_total_observations: int
    minimum_comparable_observations: int
    minimum_clean_treatments: int
    minimum_l0: int
    minimum_l1: int
    minimum_direct_l2: int
    minimum_l1_to_l2: int
    minimum_terminal_treatments: int
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _COVERAGE_FIELDS:
            raise ShadowComparativeAggregationValidationError(
                "invalid aggregate coverage-plan fields"
            )
        if values["schema_version"] != "phase11-shadow-aggregate-coverage-plan-v1":
            raise ShadowComparativeAggregationValidationError(
                "unsupported aggregate coverage-plan schema"
            )
        names = (
            "minimum_total_observations",
            "minimum_comparable_observations",
            "minimum_clean_treatments",
            "minimum_l0",
            "minimum_l1",
            "minimum_direct_l2",
            "minimum_l1_to_l2",
            "minimum_terminal_treatments",
        )
        targets = {
            name: _nonnegative_integer(values[name], name) for name in names
        }
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            **targets,
            "reason_codes": reasons,
        }
        plan_id = _identity(
            material, values["coverage_plan_id"], "coverage_plan_id"
        )
        object.__setattr__(self, "schema_version", values["schema_version"])
        object.__setattr__(self, "coverage_plan_id", plan_id)
        for name, target in targets.items():
            object.__setattr__(self, name, target)
        object.__setattr__(self, "reason_codes", reasons)

    @property
    def identity(self) -> str:
        return self.coverage_plan_id


_SET_FIELDS = frozenset(
    {
        "schema_version",
        "observation_set_id",
        "observations",
        "window_start",
        "window_end",
        "locked_baseline_commit",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowComparativeObservationSetV1:
    schema_version: str
    observation_set_id: str
    observations: tuple[ShadowComparativeObservationV1, ...]
    window_start: str
    window_end: str
    locked_baseline_commit: str
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _SET_FIELDS:
            raise ShadowComparativeAggregationValidationError(
                "invalid comparative observation-set fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-comparative-observation-set-v1"
        ):
            raise ShadowComparativeAggregationValidationError(
                "unsupported comparative observation-set schema"
            )
        supplied = values["observations"]
        if type(supplied) not in (tuple, list) or not supplied:
            raise ShadowComparativeAggregationValidationError(
                "observation set must be non-empty and finite"
            )
        observations = tuple(supplied)
        if any(type(item) is not ShadowComparativeObservationV1 for item in observations):
            raise ShadowComparativeAggregationValidationError(
                "unsupported comparative observation"
            )
        baseline = values["locked_baseline_commit"]
        if type(baseline) is not str or baseline != LOCKED_PHASE09_BASELINE:
            raise ShadowComparativeAggregationValidationError(
                "invalid locked Phase 09 baseline"
            )
        window_start = _timestamp(values["window_start"], "window_start")
        window_end = _timestamp(values["window_end"], "window_end")
        if _parsed(window_start) > _parsed(window_end):
            raise ShadowComparativeAggregationValidationError(
                "invalid aggregate window"
            )
        observation_ids: set[str] = set()
        comparison_keys: set[tuple[str, str]] = set()
        for child in observations:
            if child.locked_baseline_commit != baseline:
                raise ShadowComparativeAggregationValidationError(
                    "mixed or foreign observation baseline"
                )
            _zero_effect(
                child.production_effect, child.zero_production_effect_proof
            )
            child_time = _parsed(_timestamp(child.compared_at, "compared_at"))
            if child_time < _parsed(window_start) or child_time > _parsed(window_end):
                raise ShadowComparativeAggregationValidationError(
                    "observation is outside aggregate window"
                )
            if child.observation_id in observation_ids:
                raise ShadowComparativeAggregationValidationError(
                    "duplicate observation identity"
                )
            observation_ids.add(child.observation_id)
            comparison_key = (child.event_id, child.candidate_id)
            if comparison_key in comparison_keys:
                raise ShadowComparativeAggregationValidationError(
                    "duplicate event/candidate comparison key"
                )
            comparison_keys.add(comparison_key)
        ordered = tuple(sorted(observations, key=lambda item: item.observation_id))
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "observation_ids": tuple(item.observation_id for item in ordered),
            "window_start": window_start,
            "window_end": window_end,
            "locked_baseline_commit": baseline,
            "reason_codes": reasons,
        }
        set_id = _identity(
            material, values["observation_set_id"], "observation_set_id"
        )
        object.__setattr__(self, "schema_version", values["schema_version"])
        object.__setattr__(self, "observation_set_id", set_id)
        object.__setattr__(self, "observations", ordered)
        object.__setattr__(self, "window_start", window_start)
        object.__setattr__(self, "window_end", window_end)
        object.__setattr__(self, "locked_baseline_commit", baseline)
        object.__setattr__(self, "reason_codes", reasons)

    @property
    def identity(self) -> str:
        return self.observation_set_id


_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "aggregate_plan_id",
        "observation_set",
        "coverage_plan",
        "generated_at",
        "aggregation_scope",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowAggregateComparativePlanV1:
    schema_version: str
    aggregate_plan_id: str
    observation_set: ShadowComparativeObservationSetV1
    coverage_plan: ShadowAggregateCoveragePlanV1
    generated_at: str
    aggregation_scope: ShadowAggregationScopeV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PLAN_FIELDS:
            raise ShadowComparativeAggregationValidationError(
                "invalid aggregate comparative-plan fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-aggregate-comparative-plan-v1"
        ):
            raise ShadowComparativeAggregationValidationError(
                "unsupported aggregate comparative-plan schema"
            )
        observation_set = values["observation_set"]
        coverage_plan = values["coverage_plan"]
        if (
            type(observation_set) is not ShadowComparativeObservationSetV1
            or type(coverage_plan) is not ShadowAggregateCoveragePlanV1
            or type(values["aggregation_scope"]) is not ShadowAggregationScopeV1
            or values["aggregation_scope"]
            is not ShadowAggregationScopeV1.OBSERVATION_SET
        ):
            raise ShadowComparativeAggregationValidationError(
                "invalid aggregate plan dependency or scope"
            )
        generated_at = _timestamp(values["generated_at"], "generated_at")
        if _parsed(generated_at) < _parsed(observation_set.window_end):
            raise ShadowComparativeAggregationValidationError(
                "generated_at precedes aggregate evidence"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "observation_set_id": observation_set.observation_set_id,
            "coverage_plan_id": coverage_plan.coverage_plan_id,
            "generated_at": generated_at,
            "aggregation_scope": values["aggregation_scope"].value,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        plan_id = _identity(
            material, values["aggregate_plan_id"], "aggregate_plan_id"
        )
        object.__setattr__(self, "schema_version", values["schema_version"])
        object.__setattr__(self, "aggregate_plan_id", plan_id)
        object.__setattr__(self, "observation_set", observation_set)
        object.__setattr__(self, "coverage_plan", coverage_plan)
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(
            self, "aggregation_scope", values["aggregation_scope"]
        )
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "production_effect", _ZERO_EFFECT)
        object.__setattr__(self, "zero_production_effect_proof", _ZERO_PROOF)

    @property
    def identity(self) -> str:
        return self.aggregate_plan_id


@dataclass(frozen=True, slots=True)
class ShadowAggregateRateEvidenceV1:
    numerator: int
    denominator: int
    availability: AggregateMetricAvailabilityV1
    value: Decimal | None


@dataclass(frozen=True, slots=True)
class ShadowAggregateTelemetrySummaryV1:
    availability: AggregateMetricAvailabilityV1
    available_observation_count: int
    unavailable_observation_count: int
    total: int | Decimal | None
    mean: Decimal | None


@dataclass(frozen=True, slots=True)
class ShadowAggregateCoverageResultV1:
    target: str
    required: int
    observed: int
    status: ShadowAggregateCoverageStatusV1
    coverage_result_id: str

    @property
    def identity(self) -> str:
        return self.coverage_result_id


@dataclass(frozen=True, slots=True)
class ShadowAggregateComparativeReportV1:
    schema_version: str
    aggregate_report_id: str
    aggregate_plan_id: str
    observation_set_id: str
    coverage_plan_id: str
    locked_baseline_commit: str
    window_start: str
    window_end: str
    generated_at: str
    total_observation_count: int
    comparable_observation_count: int
    non_comparable_observation_count: int
    clean_treatment_count: int
    terminal_treatment_count: int
    route_counts: Mapping[str, int]
    direct_l2_count: int
    l1_to_l2_count: int
    control_decision_counts: Mapping[str, int]
    treatment_decision_counts: Mapping[str, int]
    decision_delta_counts: Mapping[ControlTreatmentDecisionDeltaV1, int]
    disagreement_counts: Mapping[StructuredProviderDisagreementV1, int]
    unresolved_ambiguity_count: int
    treatment_availability_counts: Mapping[TreatmentAvailabilityV1, int]
    terminal_status_counts: Mapping[str, int]
    terminal_failure_counts: Mapping[str, int]
    terminal_reconciliation_counts: Mapping[str, int]
    comparability_rate: ShadowAggregateRateEvidenceV1
    clean_rate: ShadowAggregateRateEvidenceV1
    terminal_rate: ShadowAggregateRateEvidenceV1
    route_rates: Mapping[str, ShadowAggregateRateEvidenceV1]
    disagreement_rate: ShadowAggregateRateEvidenceV1
    unresolved_ambiguity_rate: ShadowAggregateRateEvidenceV1
    treatment_unavailable_rate: ShadowAggregateRateEvidenceV1
    decision_delta_rates: Mapping[
        ControlTreatmentDecisionDeltaV1, ShadowAggregateRateEvidenceV1
    ]
    latency_summary: ShadowAggregateTelemetrySummaryV1
    input_tokens_summary: ShadowAggregateTelemetrySummaryV1
    output_tokens_summary: ShadowAggregateTelemetrySummaryV1
    call_count_summary: ShadowAggregateTelemetrySummaryV1
    retry_count_summary: ShadowAggregateTelemetrySummaryV1
    tier_count_summary: ShadowAggregateTelemetrySummaryV1
    cost_summary: ShadowAggregateTelemetrySummaryV1
    coverage_results: tuple[ShadowAggregateCoverageResultV1, ...]
    coverage_results_by_target: Mapping[str, ShadowAggregateCoverageResultV1]
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.aggregate_report_id


def _rate(numerator: int, denominator: int) -> ShadowAggregateRateEvidenceV1:
    if denominator == 0:
        return ShadowAggregateRateEvidenceV1(
            numerator=0,
            denominator=0,
            availability=AggregateMetricAvailabilityV1.UNAVAILABLE,
            value=None,
        )
    return ShadowAggregateRateEvidenceV1(
        numerator=numerator,
        denominator=denominator,
        availability=AggregateMetricAvailabilityV1.COMPLETE,
        value=(Decimal(numerator) / Decimal(denominator)).quantize(
            _MEAN_SCALE, rounding=ROUND_HALF_EVEN
        ),
    )


def _summary(
    observations: tuple[ShadowComparativeObservationV1, ...],
    availability_name: str,
    value_name: str,
) -> ShadowAggregateTelemetrySummaryV1:
    values: list[int | Decimal] = []
    for child in observations:
        if getattr(child, availability_name) is MetricAvailabilityV1.AVAILABLE:
            value = getattr(child, value_name)
            if value is None:
                raise ShadowComparativeAggregationValidationError(
                    "available metric has no committed value"
                )
            values.append(value)
        elif getattr(child, value_name) is not None:
            raise ShadowComparativeAggregationValidationError(
                "unavailable metric contains a value"
            )
    available = len(values)
    unavailable = len(observations) - available
    if not values:
        metric_availability = AggregateMetricAvailabilityV1.UNAVAILABLE
        total: int | Decimal | None = None
        mean = None
    else:
        metric_availability = (
            AggregateMetricAvailabilityV1.COMPLETE
            if unavailable == 0
            else AggregateMetricAvailabilityV1.PARTIAL
        )
        total = sum(values)
        mean = (Decimal(total) / Decimal(available)).quantize(
            _MEAN_SCALE, rounding=ROUND_HALF_EVEN
        )
    return ShadowAggregateTelemetrySummaryV1(
        availability=metric_availability,
        available_observation_count=available,
        unavailable_observation_count=unavailable,
        total=total,
        mean=mean,
    )


def _count_summary(
    observations: tuple[ShadowComparativeObservationV1, ...],
    field_name: str,
) -> ShadowAggregateTelemetrySummaryV1:
    values = tuple(getattr(child, field_name) for child in observations)
    total = sum(values)
    return ShadowAggregateTelemetrySummaryV1(
        availability=AggregateMetricAvailabilityV1.COMPLETE,
        available_observation_count=len(values),
        unavailable_observation_count=0,
        total=total,
        mean=(Decimal(total) / Decimal(len(values))).quantize(
            _MEAN_SCALE, rounding=ROUND_HALF_EVEN
        ),
    )


def _coverage_result(
    target: str, required: int, observed: int
) -> ShadowAggregateCoverageResultV1:
    status = (
        ShadowAggregateCoverageStatusV1.MET
        if observed >= required
        else ShadowAggregateCoverageStatusV1.NOT_MET
    )
    material = {
        "target": target,
        "required": required,
        "observed": observed,
        "status": status.value,
    }
    return ShadowAggregateCoverageResultV1(
        target=target,
        required=required,
        observed=observed,
        status=status,
        coverage_result_id=lowercase_sha256(material),
    )


def _map_material(value: Mapping[Any, Any]) -> dict[str, Any]:
    return {
        key.value if isinstance(key, StrEnum) else str(key): (
            {
                "numerator": item.numerator,
                "denominator": item.denominator,
                "availability": item.availability.value,
                "value": item.value,
            }
            if isinstance(item, ShadowAggregateRateEvidenceV1)
            else item
        )
        for key, item in value.items()
    }


def _summary_material(value: ShadowAggregateTelemetrySummaryV1) -> dict[str, Any]:
    return {
        "availability": value.availability.value,
        "available_observation_count": value.available_observation_count,
        "unavailable_observation_count": value.unavailable_observation_count,
        "total": value.total,
        "mean": value.mean,
    }


class ShadowComparativeAggregatorV1:
    """Side-effect-free event-observation aggregator."""

    __slots__ = ()

    def aggregate(
        self, plan: ShadowAggregateComparativePlanV1
    ) -> ShadowAggregateComparativeReportV1:
        if type(plan) is not ShadowAggregateComparativePlanV1:
            raise ShadowComparativeAggregationValidationError(
                "invalid aggregate comparative plan"
            )
        observations = plan.observation_set.observations
        total = len(observations)
        comparable = sum(
            child.comparability is ComparisonComparabilityV1.COMPARABLE
            for child in observations
        )
        clean = sum(
            child.treatment_availability is TreatmentAvailabilityV1.AVAILABLE
            for child in observations
        )
        terminal = total - clean

        route_counts = {
            route: sum(child.original_treatment_route == route for child in observations)
            for route in ("L0", "L1", "L2", "L1_TO_L2")
        }
        control_counts = {
            decision: sum(child.control_decision == decision for child in observations)
            for decision in ("ALLOW", "HOLD", "REJECT")
        }
        treatment_counts = {
            decision: sum(child.treatment_decision == decision for child in observations)
            for decision in (
                "ALLOW_NEWS_ELIGIBILITY",
                "REQUIRE_NEWS_CAUTION",
                "DENY_NEWS_ELIGIBILITY",
                "FAIL_CLOSED",
            )
        }
        delta_counts = {
            item: sum(child.decision_delta is item for child in observations)
            for item in ControlTreatmentDecisionDeltaV1
        }
        disagreement_counts = {
            item: sum(child.structured_disagreement is item for child in observations)
            for item in StructuredProviderDisagreementV1
        }
        availability_counts = {
            item: sum(child.treatment_availability is item for child in observations)
            for item in TreatmentAvailabilityV1
        }
        terminal_status_counts = {
            item.value: sum(child.terminal_status is item for child in observations)
            for item in ShadowTerminalRecordStatusV1
        }
        terminal_failure_counts: dict[str, int] = {}
        terminal_reconciliation_counts: dict[str, int] = {}
        for child in observations:
            if child.terminal_status is not None:
                terminal_failure_counts[child.terminal_failure] = (
                    terminal_failure_counts.get(child.terminal_failure, 0) + 1
                )
                terminal_reconciliation_counts[child.terminal_reconciliation] = (
                    terminal_reconciliation_counts.get(
                        child.terminal_reconciliation, 0
                    )
                    + 1
                )

        unresolved = sum(child.unresolved_ambiguity for child in observations)
        disagreeing = sum(
            child.structured_disagreement
            in {
                StructuredProviderDisagreementV1.PARTIAL_DISAGREEMENT,
                StructuredProviderDisagreementV1.COMPLETE_DISAGREEMENT,
                StructuredProviderDisagreementV1.UNRESOLVED,
            }
            for child in observations
        )
        route_rates = {
            route: _rate(count, total) for route, count in route_counts.items()
        }
        delta_rates = {
            item: _rate(count, total) for item, count in delta_counts.items()
        }
        latency_summary = _summary(
            observations, "latency_availability", "total_latency_ms"
        )
        input_summary = _summary(
            observations, "input_tokens_availability", "total_input_tokens"
        )
        output_summary = _summary(
            observations, "output_tokens_availability", "total_output_tokens"
        )
        cost_summary = _summary(
            observations, "cost_availability", "total_actual_cost"
        )
        call_summary = _count_summary(observations, "call_count")
        retry_summary = _count_summary(observations, "retry_count")
        tier_summary = _count_summary(observations, "tier_count")

        coverage = plan.coverage_plan
        coverage_pairs = (
            (
                "TOTAL_OBSERVATIONS",
                coverage.minimum_total_observations,
                total,
            ),
            (
                "COMPARABLE_OBSERVATIONS",
                coverage.minimum_comparable_observations,
                comparable,
            ),
            (
                "CLEAN_TREATMENTS",
                coverage.minimum_clean_treatments,
                clean,
            ),
            ("L0", coverage.minimum_l0, route_counts["L0"]),
            ("L1", coverage.minimum_l1, route_counts["L1"]),
            (
                "DIRECT_L2",
                coverage.minimum_direct_l2,
                route_counts["L2"],
            ),
            (
                "L1_TO_L2",
                coverage.minimum_l1_to_l2,
                route_counts["L1_TO_L2"],
            ),
            (
                "TERMINAL_TREATMENTS",
                coverage.minimum_terminal_treatments,
                terminal,
            ),
        )
        coverage_results = tuple(
            _coverage_result(target, required, observed)
            for target, required, observed in coverage_pairs
        )
        coverage_by_target = {
            item.target: item for item in coverage_results
        }
        comparability_rate = _rate(comparable, total)
        clean_rate = _rate(clean, total)
        terminal_rate = _rate(terminal, total)
        disagreement_rate = _rate(disagreeing, total)
        unresolved_rate = _rate(unresolved, total)
        unavailable_rate = _rate(
            availability_counts[TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE],
            total,
        )
        reasons = ("AGGREGATE_EVIDENCE_COMPUTED",)

        material = {
            "schema_version": "phase11-shadow-aggregate-comparative-report-v1",
            "aggregate_plan_id": plan.aggregate_plan_id,
            "observation_set_id": plan.observation_set.observation_set_id,
            "coverage_plan_id": coverage.coverage_plan_id,
            "locked_baseline_commit": plan.observation_set.locked_baseline_commit,
            "window_start": plan.observation_set.window_start,
            "window_end": plan.observation_set.window_end,
            "generated_at": plan.generated_at,
            "counts": {
                "total": total,
                "comparable": comparable,
                "non_comparable": total - comparable,
                "clean": clean,
                "terminal": terminal,
                "routes": route_counts,
                "control_decisions": control_counts,
                "treatment_decisions": treatment_counts,
                "decision_deltas": _map_material(delta_counts),
                "disagreement": _map_material(disagreement_counts),
                "treatment_availability": _map_material(availability_counts),
                "terminal_status": terminal_status_counts,
                "terminal_failure": terminal_failure_counts,
                "terminal_reconciliation": terminal_reconciliation_counts,
                "unresolved_ambiguity": unresolved,
            },
            "rates": {
                "comparability": _map_material({"rate": comparability_rate}),
                "clean": _map_material({"rate": clean_rate}),
                "terminal": _map_material({"rate": terminal_rate}),
                "routes": _map_material(route_rates),
                "disagreement": _map_material({"rate": disagreement_rate}),
                "unresolved": _map_material({"rate": unresolved_rate}),
                "unavailable": _map_material({"rate": unavailable_rate}),
                "decision_deltas": _map_material(delta_rates),
            },
            "telemetry": {
                "latency": _summary_material(latency_summary),
                "input_tokens": _summary_material(input_summary),
                "output_tokens": _summary_material(output_summary),
                "calls": _summary_material(call_summary),
                "retries": _summary_material(retry_summary),
                "tiers": _summary_material(tier_summary),
                "cost": _summary_material(cost_summary),
            },
            "coverage_results": tuple(
                {
                    "target": item.target,
                    "required": item.required,
                    "observed": item.observed,
                    "status": item.status.value,
                    "coverage_result_id": item.coverage_result_id,
                }
                for item in coverage_results
            ),
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        report_id = lowercase_sha256(material)
        return ShadowAggregateComparativeReportV1(
            schema_version=material["schema_version"],
            aggregate_report_id=report_id,
            aggregate_plan_id=plan.aggregate_plan_id,
            observation_set_id=plan.observation_set.observation_set_id,
            coverage_plan_id=coverage.coverage_plan_id,
            locked_baseline_commit=plan.observation_set.locked_baseline_commit,
            window_start=plan.observation_set.window_start,
            window_end=plan.observation_set.window_end,
            generated_at=plan.generated_at,
            total_observation_count=total,
            comparable_observation_count=comparable,
            non_comparable_observation_count=total - comparable,
            clean_treatment_count=clean,
            terminal_treatment_count=terminal,
            route_counts=MappingProxyType(route_counts),
            direct_l2_count=route_counts["L2"],
            l1_to_l2_count=route_counts["L1_TO_L2"],
            control_decision_counts=MappingProxyType(control_counts),
            treatment_decision_counts=MappingProxyType(treatment_counts),
            decision_delta_counts=MappingProxyType(delta_counts),
            disagreement_counts=MappingProxyType(disagreement_counts),
            unresolved_ambiguity_count=unresolved,
            treatment_availability_counts=MappingProxyType(
                availability_counts
            ),
            terminal_status_counts=MappingProxyType(terminal_status_counts),
            terminal_failure_counts=MappingProxyType(terminal_failure_counts),
            terminal_reconciliation_counts=MappingProxyType(
                terminal_reconciliation_counts
            ),
            comparability_rate=comparability_rate,
            clean_rate=clean_rate,
            terminal_rate=terminal_rate,
            route_rates=MappingProxyType(route_rates),
            disagreement_rate=disagreement_rate,
            unresolved_ambiguity_rate=unresolved_rate,
            treatment_unavailable_rate=unavailable_rate,
            decision_delta_rates=MappingProxyType(delta_rates),
            latency_summary=latency_summary,
            input_tokens_summary=input_summary,
            output_tokens_summary=output_summary,
            call_count_summary=call_summary,
            retry_count_summary=retry_summary,
            tier_count_summary=tier_summary,
            cost_summary=cost_summary,
            coverage_results=coverage_results,
            coverage_results_by_target=MappingProxyType(coverage_by_target),
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )


__all__ = [
    "AggregateMetricAvailabilityV1",
    "ShadowAggregateComparativePlanV1",
    "ShadowAggregateComparativeReportV1",
    "ShadowAggregateCoveragePlanV1",
    "ShadowAggregateCoverageResultV1",
    "ShadowAggregateCoverageStatusV1",
    "ShadowAggregateRateEvidenceV1",
    "ShadowAggregateTelemetrySummaryV1",
    "ShadowAggregationScopeV1",
    "ShadowComparativeAggregationValidationError",
    "ShadowComparativeAggregatorV1",
    "ShadowComparativeObservationSetV1",
    "canonical_json_bytes",
    "lowercase_sha256",
]
