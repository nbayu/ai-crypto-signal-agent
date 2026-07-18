"""Deterministic aggregate-evidence-only Phase 11 cost projection.

This module consumes immutable route-cost and comparative aggregate reports.
It performs no event-level evaluation, provider execution, pricing lookup,
budget decision, persistence, publication, or production action.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from engine.phase_11_shadow_comparative_aggregate_v1 import (
    AggregateMetricAvailabilityV1,
    ShadowAggregateComparativeReportV1,
)
from engine.phase_11_shadow_route_cost_evidence_v1 import (
    RouteCostMetricAvailabilityV1,
    ShadowRouteCostAggregateReportV1,
    ShadowRouteCostSummaryV1,
)


_UTC = timezone.utc
_LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"
_ROUTES = ("L0", "L1", "L2", "L1_TO_L2")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ShadowCostProjectionValidationError(ValueError):
    """Raised when cost-projection evidence or assumptions are inconsistent."""


class ShadowCostProjectionScopeV1(StrEnum):
    AGGREGATE_EVIDENCE_ONLY = "AGGREGATE_EVIDENCE_ONLY"


class ShadowCostProjectionAvailabilityV1(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"


class ShadowCostProjectionConfidenceV1(StrEnum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ShadowOwnerBudgetGateStatusV1(StrEnum):
    NOT_APPROVED = "NOT_APPROVED"


def _require_utc(name: str, value: Any) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() != _UTC.utcoffset(value)
    ):
        raise ShadowCostProjectionValidationError(
            f"{name} must be an explicit UTC datetime"
        )
    return value


def _parse_utc(name: str, value: Any) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ShadowCostProjectionValidationError(
            f"{name} must be a canonical UTC timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ShadowCostProjectionValidationError(f"invalid {name}") from error
    return _require_utc(name, parsed)


def _canonical(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowCostProjectionValidationError(
                "canonical Decimal values must be finite"
            )
        return "0" if value == 0 else format(value.normalize(), "f")
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
    raise ShadowCostProjectionValidationError(
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
        raise ShadowCostProjectionValidationError(
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
        raise ShadowCostProjectionValidationError(f"invalid {name}")
    return derived


def _codes(name: str, value: Any) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or not value
        or any(type(item) is not str or not _CODE.fullmatch(item) for item in value)
        or tuple(sorted(set(value))) != value
    ):
        raise ShadowCostProjectionValidationError(
            f"{name} must be a sorted unique tuple of deterministic codes"
        )
    return value


def _uncertainties(value: Any) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or any(type(item) is not str or not _CODE.fullmatch(item) for item in value)
        or tuple(sorted(set(value))) != value
    ):
        raise ShadowCostProjectionValidationError(
            "uncertainty_classes must be a sorted unique tuple of deterministic codes"
        )
    return value


def _nonnegative_integer(name: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ShadowCostProjectionValidationError(
            f"{name} must be an exact non-negative integer"
        )
    return value


def _share(name: str, value: Any) -> Decimal:
    if (
        type(value) is not Decimal
        or not value.is_finite()
        or value < Decimal("0")
        or value > Decimal("1")
    ):
        raise ShadowCostProjectionValidationError(
            f"{name} must be a finite Decimal within [0, 1]"
        )
    return value


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowCostProjectionValidationError(
            "projection evidence must prove zero production effect"
        )


_SCENARIO_FIELDS = frozenset(
    {
        "schema_version",
        "scenario_id",
        "daily_eligible_event_count",
        "projection_day_count",
        "sample_day_count",
        "l0_share",
        "l1_share",
        "direct_l2_share",
        "l1_to_l2_share",
        "unavailable_or_unprocessed_share",
        "uncertainty_classes",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowCostProjectionScenarioV1:
    schema_version: str
    scenario_id: str
    daily_eligible_event_count: int
    projection_day_count: int
    sample_day_count: int
    l0_share: Decimal
    l1_share: Decimal
    direct_l2_share: Decimal
    l1_to_l2_share: Decimal
    unavailable_or_unprocessed_share: Decimal
    uncertainty_classes: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _SCENARIO_FIELDS:
            raise ShadowCostProjectionValidationError(
                "invalid projection scenario fields"
            )
        if values["schema_version"] != "phase11-shadow-cost-projection-scenario-v1":
            raise ShadowCostProjectionValidationError(
                "unsupported projection scenario schema"
            )
        counts = {
            name: _nonnegative_integer(name, values[name])
            for name in (
                "daily_eligible_event_count",
                "projection_day_count",
                "sample_day_count",
            )
        }
        shares = {
            name: _share(name, values[name])
            for name in (
                "l0_share",
                "l1_share",
                "direct_l2_share",
                "l1_to_l2_share",
                "unavailable_or_unprocessed_share",
            )
        }
        if sum(shares.values(), Decimal("0")) != Decimal("1"):
            raise ShadowCostProjectionValidationError(
                "projection shares must reconcile exactly to one"
            )
        uncertainties = _uncertainties(values["uncertainty_classes"])
        reasons = _codes("reason_codes", values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            **counts,
            **shares,
            "uncertainty_classes": uncertainties,
            "reason_codes": reasons,
        }
        scenario_id = _identity(material, values["scenario_id"], "scenario_id")
        normalized = {
            **values,
            **counts,
            **shares,
            "scenario_id": scenario_id,
            "uncertainty_classes": uncertainties,
            "reason_codes": reasons,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.scenario_id


_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "projection_plan_id",
        "route_cost_aggregate_report",
        "comparative_aggregate_report",
        "scenario",
        "projected_at",
        "locked_baseline_commit",
        "scope",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowCostProjectionPlanV1:
    schema_version: str
    projection_plan_id: str
    route_cost_aggregate_report: ShadowRouteCostAggregateReportV1
    comparative_aggregate_report: ShadowAggregateComparativeReportV1
    scenario: ShadowCostProjectionScenarioV1
    projected_at: datetime
    locked_baseline_commit: str
    scope: ShadowCostProjectionScopeV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PLAN_FIELDS:
            raise ShadowCostProjectionValidationError(
                "invalid projection plan fields"
            )
        if values["schema_version"] != "phase11-shadow-cost-projection-plan-v1":
            raise ShadowCostProjectionValidationError(
                "unsupported projection plan schema"
            )
        route_report = values["route_cost_aggregate_report"]
        comparative_report = values["comparative_aggregate_report"]
        scenario = values["scenario"]
        if type(route_report) is not ShadowRouteCostAggregateReportV1:
            raise ShadowCostProjectionValidationError(
                "invalid route-cost aggregate report"
            )
        if type(comparative_report) is not ShadowAggregateComparativeReportV1:
            raise ShadowCostProjectionValidationError(
                "invalid comparative aggregate report"
            )
        if type(scenario) is not ShadowCostProjectionScenarioV1:
            raise ShadowCostProjectionValidationError(
                "invalid projection scenario"
            )
        baseline = values["locked_baseline_commit"]
        if (
            baseline != _LOCKED_PHASE09_BASELINE
            or route_report.locked_baseline_commit != baseline
            or comparative_report.locked_baseline_commit != baseline
        ):
            raise ShadowCostProjectionValidationError(
                "projection source baseline mismatch"
            )
        _zero_effect(
            route_report.production_effect,
            route_report.zero_production_effect_proof,
        )
        _zero_effect(
            comparative_report.production_effect,
            comparative_report.zero_production_effect_proof,
        )
        _zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        route_start = _require_utc("route window_start", route_report.window_start)
        route_end = _require_utc("route window_end", route_report.window_end)
        comparative_start = _parse_utc(
            "comparative window_start", comparative_report.window_start
        )
        comparative_end = _parse_utc(
            "comparative window_end", comparative_report.window_end
        )
        if route_start != comparative_start or route_end != comparative_end:
            raise ShadowCostProjectionValidationError(
                "projection source evidence windows are incompatible"
            )
        projected_at = _require_utc("projected_at", values["projected_at"])
        route_generated_at = _require_utc(
            "route generated_at", route_report.generated_at
        )
        comparative_generated_at = _parse_utc(
            "comparative generated_at", comparative_report.generated_at
        )
        if (
            projected_at < route_generated_at
            or projected_at < comparative_generated_at
        ):
            raise ShadowCostProjectionValidationError(
                "projected_at precedes aggregate source evidence"
            )
        if (
            values["scope"]
            is not ShadowCostProjectionScopeV1.AGGREGATE_EVIDENCE_ONLY
        ):
            raise ShadowCostProjectionValidationError(
                "unsupported projection scope"
            )
        reasons = _codes("reason_codes", values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "route_cost_aggregate_report_id": route_report.identity,
            "comparative_aggregate_report_id": comparative_report.identity,
            "scenario_id": scenario.identity,
            "projected_at": projected_at,
            "locked_baseline_commit": baseline,
            "scope": values["scope"],
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        plan_id = _identity(
            material, values["projection_plan_id"], "projection_plan_id"
        )
        normalized = {
            **values,
            "projection_plan_id": plan_id,
            "projected_at": projected_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.projection_plan_id


@dataclass(frozen=True, slots=True)
class ShadowProjectedRouteVolumeV1:
    schema_version: str
    projected_route_volume_id: str
    scenario_id: str
    route: str
    share: Decimal
    daily_volume: Decimal
    sample_volume: Decimal
    projected_volume: Decimal
    reason_codes: tuple[str, ...]

    @property
    def identity(self) -> str:
        return self.projected_route_volume_id


@dataclass(frozen=True, slots=True)
class ShadowProjectedCostMetricV1:
    schema_version: str
    projected_cost_metric_id: str
    metric_name: str
    source_summary_id: str
    source_total_actual_cost: Decimal | None
    source_available_denominator: int
    source_unavailable_denominator: int
    availability: ShadowCostProjectionAvailabilityV1
    value: Decimal | None
    reason_codes: tuple[str, ...]

    @property
    def identity(self) -> str:
        return self.projected_cost_metric_id


@dataclass(frozen=True, slots=True)
class ShadowCostProjectionReportV1:
    schema_version: str
    projection_report_id: str
    projection_plan_id: str
    route_cost_aggregate_report_id: str
    comparative_aggregate_report_id: str
    scenario_id: str
    locked_baseline_commit: str
    route_cost_window_start: datetime
    route_cost_window_end: datetime
    comparative_window_start: str
    comparative_window_end: str
    projected_at: datetime
    projected_route_volumes: tuple[ShadowProjectedRouteVolumeV1, ...]
    cost_metrics: tuple[ShadowProjectedCostMetricV1, ...]
    cost_metrics_by_name: Mapping[str, ShadowProjectedCostMetricV1]
    projected_daily_cost: ShadowProjectedCostMetricV1
    projected_sample_cost: ShadowProjectedCostMetricV1
    projected_monthly_cost: ShadowProjectedCostMetricV1
    observed_call_count: int | None
    observed_retry_count: int | None
    observed_retry_rate: Decimal | None
    terminal_failure_counts: Mapping[str, int]
    projection_availability: ShadowCostProjectionAvailabilityV1
    projection_confidence: ShadowCostProjectionConfidenceV1
    uncertainty_classes: tuple[str, ...]
    owner_budget_gate_status: ShadowOwnerBudgetGateStatusV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.projection_report_id


def _summary_value(
    summary: ShadowRouteCostSummaryV1,
) -> tuple[ShadowCostProjectionAvailabilityV1, Decimal | None]:
    denominator = summary.available_value_denominator
    if type(denominator) is not int or denominator < 0:
        raise ShadowCostProjectionValidationError(
            "route summary contains an invalid denominator"
        )
    if summary.available_cost_count != denominator:
        raise ShadowCostProjectionValidationError(
            "route summary available denominators do not reconcile"
        )
    unavailable = summary.unavailable_cost_count
    if type(unavailable) is not int or unavailable < 0:
        raise ShadowCostProjectionValidationError(
            "route summary contains an invalid unavailable denominator"
        )
    if denominator == 0:
        if (
            summary.availability is not RouteCostMetricAvailabilityV1.UNAVAILABLE
            or summary.total_actual_cost is not None
            or summary.available_value_mean is not None
        ):
            raise ShadowCostProjectionValidationError(
                "unavailable route cost must remain absent"
            )
        return ShadowCostProjectionAvailabilityV1.UNAVAILABLE, None
    total = summary.total_actual_cost
    if (
        summary.availability is not RouteCostMetricAvailabilityV1.AVAILABLE
        or type(total) is not Decimal
        or not total.is_finite()
        or total < Decimal("0")
    ):
        raise ShadowCostProjectionValidationError(
            "available route cost must be a finite non-negative Decimal"
        )
    value = summary.available_value_mean
    if (
        type(value) is not Decimal
        or not value.is_finite()
        or value < Decimal("0")
    ):
        raise ShadowCostProjectionValidationError(
            "available route mean must be a finite non-negative Decimal"
        )
    availability = (
        ShadowCostProjectionAvailabilityV1.PARTIAL
        if unavailable
        else ShadowCostProjectionAvailabilityV1.COMPLETE
    )
    return availability, value


def _actual_metric(
    metric_name: str,
    summary: ShadowRouteCostSummaryV1,
    reason: str,
) -> ShadowProjectedCostMetricV1:
    availability, value = _summary_value(summary)
    reasons = (reason,)
    material = {
        "schema_version": "phase11-shadow-projected-cost-metric-v1",
        "metric_name": metric_name,
        "source_summary_id": summary.identity,
        "source_total_actual_cost": summary.total_actual_cost,
        "source_available_denominator": summary.available_value_denominator,
        "source_unavailable_denominator": summary.unavailable_cost_count,
        "availability": availability,
        "value": value,
        "reason_codes": reasons,
    }
    return ShadowProjectedCostMetricV1(
        schema_version=material["schema_version"],
        projected_cost_metric_id=_derived_identity(material),
        metric_name=metric_name,
        source_summary_id=summary.identity,
        source_total_actual_cost=summary.total_actual_cost,
        source_available_denominator=summary.available_value_denominator,
        source_unavailable_denominator=summary.unavailable_cost_count,
        availability=availability,
        value=value,
        reason_codes=reasons,
    )


def _eligible_metric(
    summaries: Mapping[str, ShadowRouteCostSummaryV1],
) -> ShadowProjectedCostMetricV1:
    source_ids = tuple(summaries[route].identity for route in _ROUTES)
    available_summaries = tuple(
        summaries[route]
        for route in _ROUTES
        if summaries[route].available_value_denominator > 0
    )
    available = sum(
        (item.available_value_denominator for item in available_summaries), 0
    )
    unavailable = sum(
        (summaries[route].unavailable_cost_count for route in _ROUTES), 0
    )
    if not available_summaries:
        total = None
        value = None
        availability = ShadowCostProjectionAvailabilityV1.UNAVAILABLE
    else:
        totals: list[Decimal] = []
        for summary in available_summaries:
            _summary_value(summary)
            if summary.total_actual_cost is None:
                raise ShadowCostProjectionValidationError(
                    "represented eligible-event cost is absent"
                )
            totals.append(summary.total_actual_cost)
        total = sum(totals, Decimal("0"))
        value = total / Decimal(available)
        availability = (
            ShadowCostProjectionAvailabilityV1.COMPLETE
            if len(available_summaries) == len(_ROUTES) and unavailable == 0
            else ShadowCostProjectionAvailabilityV1.PARTIAL
        )
    source_id = _derived_identity(
        {"metric_name": "COST_PER_ELIGIBLE_EVENT", "source_summary_ids": source_ids}
    )
    reasons = ("ACTUAL_ROUTE_COSTS_PER_REPRESENTED_ELIGIBLE_EVENT",)
    material = {
        "schema_version": "phase11-shadow-projected-cost-metric-v1",
        "metric_name": "COST_PER_ELIGIBLE_EVENT",
        "source_summary_id": source_id,
        "source_total_actual_cost": total,
        "source_available_denominator": available,
        "source_unavailable_denominator": unavailable,
        "availability": availability,
        "value": value,
        "reason_codes": reasons,
    }
    return ShadowProjectedCostMetricV1(
        schema_version=material["schema_version"],
        projected_cost_metric_id=_derived_identity(material),
        metric_name=material["metric_name"],
        source_summary_id=source_id,
        source_total_actual_cost=total,
        source_available_denominator=available,
        source_unavailable_denominator=unavailable,
        availability=availability,
        value=value,
        reason_codes=reasons,
    )


def _route_volume(
    scenario: ShadowCostProjectionScenarioV1,
    route: str,
    share: Decimal,
) -> ShadowProjectedRouteVolumeV1:
    daily = Decimal(scenario.daily_eligible_event_count) * share
    sample = daily * Decimal(scenario.sample_day_count)
    projected = daily * Decimal(scenario.projection_day_count)
    reasons = ("EXPLICIT_SCENARIO_ROUTE_VOLUME",)
    material = {
        "schema_version": "phase11-shadow-projected-route-volume-v1",
        "scenario_id": scenario.identity,
        "route": route,
        "share": share,
        "daily_volume": daily,
        "sample_volume": sample,
        "projected_volume": projected,
        "reason_codes": reasons,
    }
    return ShadowProjectedRouteVolumeV1(
        schema_version=material["schema_version"],
        projected_route_volume_id=_derived_identity(material),
        scenario_id=scenario.identity,
        route=route,
        share=share,
        daily_volume=daily,
        sample_volume=sample,
        projected_volume=projected,
        reason_codes=reasons,
    )


def _projected_metric(
    metric_name: str,
    volumes: tuple[ShadowProjectedRouteVolumeV1, ...],
    route_metrics: Mapping[str, ShadowProjectedCostMetricV1],
    volume_field: str,
) -> tuple[ShadowProjectedCostMetricV1, tuple[str, ...]]:
    source_ids = tuple(route_metrics[route].identity for route in _ROUTES)
    required = tuple(
        (volume, route_metrics[volume.route])
        for volume in volumes
        if getattr(volume, volume_field) != Decimal("0")
    )
    unavailable_routes = tuple(
        volume.route for volume, metric in required if metric.value is None
    )
    reasons: tuple[str, ...]
    if unavailable_routes:
        route_reasons = tuple(
            f"UNAVAILABLE_{route}_ROUTE_COST" for route in unavailable_routes
        )
        reasons = tuple(sorted(route_reasons))
        available_required = sum(
            metric.value is not None for _, metric in required
        )
        availability = (
            ShadowCostProjectionAvailabilityV1.PARTIAL
            if available_required
            else ShadowCostProjectionAvailabilityV1.UNAVAILABLE
        )
        value = None
    else:
        value = sum(
            (
                getattr(volume, volume_field) * metric.value
                for volume, metric in required
                if metric.value is not None
            ),
            Decimal("0"),
        )
        availability = (
            ShadowCostProjectionAvailabilityV1.PARTIAL
            if any(
                metric.availability is ShadowCostProjectionAvailabilityV1.PARTIAL
                for _, metric in required
            )
            else ShadowCostProjectionAvailabilityV1.COMPLETE
        )
        reasons = ("ROUTE_WEIGHTED_ACTUAL_COST_PROJECTION",)
    available_denominator = sum(
        (metric.source_available_denominator for metric in route_metrics.values()), 0
    )
    unavailable_denominator = sum(
        (metric.source_unavailable_denominator for metric in route_metrics.values()), 0
    )
    totals = tuple(
        metric.source_total_actual_cost
        for metric in route_metrics.values()
        if metric.source_total_actual_cost is not None
    )
    source_total = sum(totals, Decimal("0")) if totals else None
    source_id = _derived_identity(
        {
            "metric_name": metric_name,
            "source_metric_ids": source_ids,
            "scenario_volume_ids": tuple(item.identity for item in volumes),
            "volume_field": volume_field,
        }
    )
    material = {
        "schema_version": "phase11-shadow-projected-cost-metric-v1",
        "metric_name": metric_name,
        "source_summary_id": source_id,
        "source_total_actual_cost": source_total,
        "source_available_denominator": available_denominator,
        "source_unavailable_denominator": unavailable_denominator,
        "availability": availability,
        "value": value,
        "reason_codes": reasons,
    }
    return (
        ShadowProjectedCostMetricV1(
            schema_version=material["schema_version"],
            projected_cost_metric_id=_derived_identity(material),
            metric_name=metric_name,
            source_summary_id=source_id,
            source_total_actual_cost=source_total,
            source_available_denominator=available_denominator,
            source_unavailable_denominator=unavailable_denominator,
            availability=availability,
            value=value,
            reason_codes=reasons,
        ),
        reasons,
    )


def _copied_count(summary: Any) -> int | None:
    if summary.availability is AggregateMetricAvailabilityV1.UNAVAILABLE:
        return None
    if type(summary.total) is not int or summary.total < 0:
        raise ShadowCostProjectionValidationError(
            "available comparative count must be a non-negative integer"
        )
    return summary.total


class ShadowCostProjectorV1:
    """Stateless projector over already-created immutable aggregate evidence."""

    __slots__ = ()

    def project(
        self, plan: ShadowCostProjectionPlanV1
    ) -> ShadowCostProjectionReportV1:
        if type(plan) is not ShadowCostProjectionPlanV1:
            raise ShadowCostProjectionValidationError(
                "invalid cost-projection plan"
            )
        route_report = plan.route_cost_aggregate_report
        comparative_report = plan.comparative_aggregate_report
        summaries = route_report.route_cost_summaries
        if set(summaries) != set(_ROUTES) or any(
            type(summaries[route]) is not ShadowRouteCostSummaryV1
            or summaries[route].route != route
            for route in _ROUTES
        ):
            raise ShadowCostProjectionValidationError(
                "route-cost report must expose four independent route summaries"
            )
        combined = route_report.combined_l2_cost_summary
        if (
            type(combined) is not ShadowRouteCostSummaryV1
            or combined.route != "COMBINED_L2"
        ):
            raise ShadowCostProjectionValidationError(
                "route-cost report lacks explicit combined-L2 reconciliation"
            )
        scenario = plan.scenario
        shares = {
            "L0": scenario.l0_share,
            "L1": scenario.l1_share,
            "L2": scenario.direct_l2_share,
            "L1_TO_L2": scenario.l1_to_l2_share,
        }
        volumes = tuple(
            _route_volume(scenario, route, shares[route]) for route in _ROUTES
        )
        actual_metrics = (
            _eligible_metric(summaries),
            _actual_metric("COST_PER_L1", summaries["L1"], "ACTUAL_L1_ROUTE_COST"),
            _actual_metric(
                "COST_PER_DIRECT_L2",
                summaries["L2"],
                "ACTUAL_DIRECT_L2_ROUTE_COST",
            ),
            _actual_metric(
                "COST_PER_L1_TO_L2",
                summaries["L1_TO_L2"],
                "ACTUAL_L1_TO_L2_ROUTE_COST",
            ),
            _actual_metric(
                "COMBINED_COST_PER_L2",
                combined,
                "EXPLICIT_COMBINED_L2_ACTUAL_COST",
            ),
        )
        route_metrics = {
            "L0": _actual_metric(
                "COST_PER_L0", summaries["L0"], "ACTUAL_L0_ROUTE_COST"
            ),
            "L1": actual_metrics[1],
            "L2": actual_metrics[2],
            "L1_TO_L2": actual_metrics[3],
        }
        projected_daily, daily_reasons = _projected_metric(
            "PROJECTED_DAILY_COST", volumes, route_metrics, "daily_volume"
        )
        projected_sample, sample_reasons = _projected_metric(
            "PROJECTED_SAMPLE_COST", volumes, route_metrics, "sample_volume"
        )
        projected_monthly, monthly_reasons = _projected_metric(
            "PROJECTED_MONTHLY_COST", volumes, route_metrics, "projected_volume"
        )
        metrics_by_name = {
            metric.metric_name: metric for metric in actual_metrics
        }
        call_count = _copied_count(comparative_report.call_count_summary)
        retry_count = _copied_count(comparative_report.retry_count_summary)
        retry_rate = (
            Decimal(retry_count) / Decimal(call_count)
            if retry_count is not None and call_count is not None and call_count > 0
            else None
        )
        terminal_failures = {
            str(name): count
            for name, count in sorted(
                comparative_report.terminal_failure_counts.items()
            )
        }
        if any(type(count) is not int or count < 0 for count in terminal_failures.values()):
            raise ShadowCostProjectionValidationError(
                "terminal failure counts must be non-negative integers"
            )
        projection_availability = projected_monthly.availability
        if projection_availability is ShadowCostProjectionAvailabilityV1.COMPLETE:
            confidence = (
                ShadowCostProjectionConfidenceV1.MODERATE
                if scenario.uncertainty_classes
                else ShadowCostProjectionConfidenceV1.HIGH
            )
        elif projection_availability is ShadowCostProjectionAvailabilityV1.PARTIAL:
            confidence = ShadowCostProjectionConfidenceV1.LOW
        else:
            confidence = ShadowCostProjectionConfidenceV1.INSUFFICIENT_EVIDENCE
        projection_reasons = set(plan.reason_codes)
        if daily_reasons != ("ROUTE_WEIGHTED_ACTUAL_COST_PROJECTION",):
            projection_reasons.update(daily_reasons)
        if sample_reasons != ("ROUTE_WEIGHTED_ACTUAL_COST_PROJECTION",):
            projection_reasons.update(sample_reasons)
        if monthly_reasons != ("ROUTE_WEIGHTED_ACTUAL_COST_PROJECTION",):
            projection_reasons.update(monthly_reasons)
        reasons = tuple(sorted(projection_reasons))
        immutable_metrics = MappingProxyType(metrics_by_name)
        immutable_failures = MappingProxyType(terminal_failures)
        material = {
            "schema_version": "phase11-shadow-cost-projection-report-v1",
            "projection_plan_id": plan.identity,
            "route_cost_aggregate_report_id": route_report.identity,
            "comparative_aggregate_report_id": comparative_report.identity,
            "scenario_id": scenario.identity,
            "locked_baseline_commit": plan.locked_baseline_commit,
            "route_cost_window_start": route_report.window_start,
            "route_cost_window_end": route_report.window_end,
            "comparative_window_start": comparative_report.window_start,
            "comparative_window_end": comparative_report.window_end,
            "projected_at": plan.projected_at,
            "projected_route_volume_ids": tuple(item.identity for item in volumes),
            "actual_cost_metric_ids": tuple(item.identity for item in actual_metrics),
            "projected_daily_cost_id": projected_daily.identity,
            "projected_sample_cost_id": projected_sample.identity,
            "projected_monthly_cost_id": projected_monthly.identity,
            "observed_call_count": call_count,
            "observed_retry_count": retry_count,
            "observed_retry_rate": retry_rate,
            "terminal_failure_counts": terminal_failures,
            "projection_availability": projection_availability,
            "projection_confidence": confidence,
            "uncertainty_classes": scenario.uncertainty_classes,
            "owner_budget_gate_status": ShadowOwnerBudgetGateStatusV1.NOT_APPROVED,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        return ShadowCostProjectionReportV1(
            schema_version=material["schema_version"],
            projection_report_id=_derived_identity(material),
            projection_plan_id=plan.identity,
            route_cost_aggregate_report_id=route_report.identity,
            comparative_aggregate_report_id=comparative_report.identity,
            scenario_id=scenario.identity,
            locked_baseline_commit=plan.locked_baseline_commit,
            route_cost_window_start=route_report.window_start,
            route_cost_window_end=route_report.window_end,
            comparative_window_start=comparative_report.window_start,
            comparative_window_end=comparative_report.window_end,
            projected_at=plan.projected_at,
            projected_route_volumes=volumes,
            cost_metrics=actual_metrics,
            cost_metrics_by_name=immutable_metrics,
            projected_daily_cost=projected_daily,
            projected_sample_cost=projected_sample,
            projected_monthly_cost=projected_monthly,
            observed_call_count=call_count,
            observed_retry_count=retry_count,
            observed_retry_rate=retry_rate,
            terminal_failure_counts=immutable_failures,
            projection_availability=projection_availability,
            projection_confidence=confidence,
            uncertainty_classes=scenario.uncertainty_classes,
            owner_budget_gate_status=ShadowOwnerBudgetGateStatusV1.NOT_APPROVED,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )


__all__ = [
    "ShadowCostProjectionAvailabilityV1",
    "ShadowCostProjectionConfidenceV1",
    "ShadowCostProjectionPlanV1",
    "ShadowCostProjectionReportV1",
    "ShadowCostProjectionScenarioV1",
    "ShadowCostProjectionScopeV1",
    "ShadowCostProjectionValidationError",
    "ShadowCostProjectorV1",
    "ShadowOwnerBudgetGateStatusV1",
    "ShadowProjectedCostMetricV1",
    "ShadowProjectedRouteVolumeV1",
    "canonical_json_bytes",
    "sha256_hex",
]
