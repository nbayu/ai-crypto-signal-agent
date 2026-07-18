"""RED contract for deterministic, evidence-only Phase 11 cost projection.

The implementation is deliberately absent.  Fixtures below construct only
real immutable aggregate reports with their public constructors: no event
evidence, upstream builder, evaluator, aggregator, provider, or runtime is
opened or invoked.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

import pytest

from engine.phase_11_shadow_comparative_aggregate_v1 import (
    AggregateMetricAvailabilityV1,
    ShadowAggregateComparativeReportV1,
    ShadowAggregateCoverageResultV1,
    ShadowAggregateCoverageStatusV1,
    ShadowAggregateRateEvidenceV1,
    ShadowAggregateTelemetrySummaryV1,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    ControlTreatmentDecisionDeltaV1,
    StructuredProviderDisagreementV1,
    TreatmentAvailabilityV1,
)
from engine.phase_11_shadow_cost_projection_v1 import (
    ShadowCostProjectionAvailabilityV1,
    ShadowCostProjectionConfidenceV1,
    ShadowCostProjectionPlanV1,
    ShadowCostProjectionReportV1,
    ShadowCostProjectionScenarioV1,
    ShadowCostProjectionScopeV1,
    ShadowCostProjectionValidationError,
    ShadowCostProjectorV1,
    ShadowOwnerBudgetGateStatusV1,
    ShadowProjectedCostMetricV1,
    ShadowProjectedRouteVolumeV1,
    canonical_json_bytes,
    sha256_hex,
)
from engine.phase_11_shadow_route_cost_evidence_v1 import (
    RouteCostCoverageStatusV1,
    RouteCostMetricAvailabilityV1,
    ShadowRouteCostAggregateReportV1,
    ShadowRouteCostCoverageResultV1,
    ShadowRouteCostSummaryV1,
)


WINDOW_START = datetime(2026, 7, 17, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 7, 17, 0, 10, tzinfo=UTC)
ROUTE_GENERATED_AT = datetime(2026, 7, 17, 0, 11, tzinfo=UTC)
COMPARATIVE_GENERATED_AT = datetime(2026, 7, 17, 0, 12, tzinfo=UTC)
PROJECTED_AT = datetime(2026, 7, 17, 0, 13, tzinfo=UTC)
ROUTES = ("L0", "L1", "L2", "L1_TO_L2")


def _digest(value: object) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def _summary(
    route: str,
    *,
    total: Decimal | None,
    available: int,
    unavailable: int = 0,
) -> ShadowRouteCostSummaryV1:
    availability = (
        RouteCostMetricAvailabilityV1.AVAILABLE
        if available
        else RouteCostMetricAvailabilityV1.UNAVAILABLE
    )
    return ShadowRouteCostSummaryV1(
        schema_version="phase11-shadow-route-cost-summary-v1",
        route_cost_summary_id=_digest((route, total, available, unavailable)),
        route=route,
        total_evidence_count=available + unavailable,
        available_cost_count=available,
        unavailable_cost_count=unavailable,
        availability=availability,
        total_actual_cost=total,
        available_value_mean=(total / Decimal(available) if available else None),
        available_value_denominator=available,
    )


def _route_cost_report(
    *,
    l0: Decimal | None = Decimal("1.00"),
    l1: Decimal | None = Decimal("4.00"),
    direct_l2: Decimal | None = Decimal("9.00"),
    l1_to_l2: Decimal | None = Decimal("16.00"),
    l0_available: int = 10,
    l1_available: int = 10,
    direct_l2_available: int = 10,
    l1_to_l2_available: int = 10,
    unavailable: int = 0,
    baseline: str = LOCKED_PHASE09_BASELINE,
    window_start: datetime = WINDOW_START,
    window_end: datetime = WINDOW_END,
    generated_at: datetime = ROUTE_GENERATED_AT,
    proof: str = "PROVEN_NONE",
) -> ShadowRouteCostAggregateReportV1:
    summaries = {
        "L0": _summary("L0", total=l0, available=l0_available, unavailable=unavailable),
        "L1": _summary("L1", total=l1, available=l1_available, unavailable=unavailable),
        "L2": _summary("L2", total=direct_l2, available=direct_l2_available, unavailable=unavailable),
        "L1_TO_L2": _summary("L1_TO_L2", total=l1_to_l2, available=l1_to_l2_available, unavailable=unavailable),
    }
    combined_available = direct_l2_available + l1_to_l2_available
    combined_total = (
        None if not combined_available else (direct_l2 or Decimal("0")) + (l1_to_l2 or Decimal("0"))
    )
    combined = _summary(
        "COMBINED_L2",
        total=combined_total,
        available=combined_available,
        unavailable=unavailable * 2,
    )
    coverage = tuple(
        ShadowRouteCostCoverageResultV1(
            schema_version="phase11-shadow-route-cost-coverage-result-v1",
            route_cost_coverage_result_id=_digest(("coverage", route)),
            target_name=route,
            required_count=1,
            observed_count=summaries[route].available_cost_count,
            status=(RouteCostCoverageStatusV1.MET if summaries[route].available_cost_count else RouteCostCoverageStatusV1.NOT_MET),
        )
        for route in ROUTES
    )
    return ShadowRouteCostAggregateReportV1(
        schema_version="phase11-shadow-route-cost-aggregate-report-v1",
        route_cost_aggregate_report_id=_digest(("route-report", summaries, generated_at)),
        route_cost_aggregate_plan_id=_digest("route-plan"),
        route_cost_evidence_set_id=_digest("route-set"),
        route_cost_coverage_plan_id=_digest("route-coverage"),
        locked_baseline_commit=baseline,
        window_start=window_start,
        window_end=window_end,
        generated_at=generated_at,
        total_evidence_count=sum(item.total_evidence_count for item in summaries.values()),
        route_counts=MappingProxyType({route: summaries[route].total_evidence_count for route in ROUTES}),
        route_cost_summaries=MappingProxyType(summaries),
        combined_l2_cost_summary=combined,
        coverage_results=coverage,
        coverage_results_by_target=MappingProxyType({item.target_name: item for item in coverage}),
        reason_codes=("ROUTE_COST_AGGREGATE_FIXTURE",),
        production_effect="NONE",
        zero_production_effect_proof=proof,
    )


def _rate(numerator: int, denominator: int) -> ShadowAggregateRateEvidenceV1:
    return ShadowAggregateRateEvidenceV1(
        numerator=numerator,
        denominator=denominator,
        availability=AggregateMetricAvailabilityV1.COMPLETE,
        value=Decimal(numerator) / Decimal(denominator),
    )


def _telemetry(
    *, total: int | Decimal | None, available: int = 40, unavailable: int = 0
) -> ShadowAggregateTelemetrySummaryV1:
    return ShadowAggregateTelemetrySummaryV1(
        availability=(AggregateMetricAvailabilityV1.COMPLETE if available else AggregateMetricAvailabilityV1.UNAVAILABLE),
        available_observation_count=available,
        unavailable_observation_count=unavailable,
        total=total,
        mean=(Decimal(total) / Decimal(available) if available and total is not None else None),
    )


def _comparative_report(
    *,
    baseline: str = LOCKED_PHASE09_BASELINE,
    window_start: str = "2026-07-17T00:00:00Z",
    window_end: str = "2026-07-17T00:10:00Z",
    generated_at: str = "2026-07-17T00:12:00Z",
    retry_total: int = 3,
    retry_available: int = 40,
    terminal_failure_count: int = 2,
    proof: str = "PROVEN_NONE",
) -> ShadowAggregateComparativeReportV1:
    route_counts = {"L0": 20, "L1": 10, "L2": 5, "L1_TO_L2": 5}
    coverage = tuple(
        ShadowAggregateCoverageResultV1(
            target=route,
            required=1,
            observed=count,
            status=ShadowAggregateCoverageStatusV1.MET,
            coverage_result_id=_digest(("comparative-coverage", route)),
        )
        for route, count in route_counts.items()
    )
    return ShadowAggregateComparativeReportV1(
        schema_version="phase11-shadow-aggregate-comparative-report-v1",
        aggregate_report_id=_digest(("comparative-report", retry_total, terminal_failure_count, generated_at)),
        aggregate_plan_id=_digest("comparative-plan"),
        observation_set_id=_digest("comparative-set"),
        coverage_plan_id=_digest("comparative-coverage-plan"),
        locked_baseline_commit=baseline,
        window_start=window_start,
        window_end=window_end,
        generated_at=generated_at,
        total_observation_count=40,
        comparable_observation_count=40,
        non_comparable_observation_count=0,
        clean_treatment_count=38,
        terminal_treatment_count=2,
        route_counts=MappingProxyType(route_counts),
        direct_l2_count=5,
        l1_to_l2_count=5,
        control_decision_counts=MappingProxyType({"ALLOW": 40, "HOLD": 0, "REJECT": 0}),
        treatment_decision_counts=MappingProxyType({"ALLOW_NEWS_ELIGIBILITY": 38, "REQUIRE_NEWS_CAUTION": 0, "DENY_NEWS_ELIGIBILITY": 0, "FAIL_CLOSED": 0}),
        decision_delta_counts=MappingProxyType({item: 0 for item in ControlTreatmentDecisionDeltaV1}),
        disagreement_counts=MappingProxyType({item: 0 for item in StructuredProviderDisagreementV1}),
        unresolved_ambiguity_count=0,
        treatment_availability_counts=MappingProxyType({TreatmentAvailabilityV1.AVAILABLE: 38, TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE: 2}),
        terminal_status_counts=MappingProxyType({"RECONCILIATION_REQUIRED": 2}),
        terminal_failure_counts=MappingProxyType({"FIXTURE_FAILURE": terminal_failure_count}),
        terminal_reconciliation_counts=MappingProxyType({"RECONCILIATION_REQUIRED": terminal_failure_count}),
        comparability_rate=_rate(40, 40),
        clean_rate=_rate(38, 40),
        terminal_rate=_rate(2, 40),
        route_rates=MappingProxyType({route: _rate(count, 40) for route, count in route_counts.items()}),
        disagreement_rate=_rate(0, 40),
        unresolved_ambiguity_rate=_rate(0, 40),
        treatment_unavailable_rate=_rate(2, 40),
        decision_delta_rates=MappingProxyType({item: _rate(0, 40) for item in ControlTreatmentDecisionDeltaV1}),
        latency_summary=_telemetry(total=4000),
        input_tokens_summary=_telemetry(total=400),
        output_tokens_summary=_telemetry(total=200),
        call_count_summary=_telemetry(total=43),
        retry_count_summary=_telemetry(total=retry_total, available=retry_available),
        tier_count_summary=_telemetry(total=50),
        cost_summary=_telemetry(total=Decimal("30")),
        coverage_results=coverage,
        coverage_results_by_target=MappingProxyType({item.target: item for item in coverage}),
        reason_codes=("COMPARATIVE_AGGREGATE_FIXTURE",),
        production_effect="NONE",
        zero_production_effect_proof=proof,
    )


def _scenario(**overrides: object) -> ShadowCostProjectionScenarioV1:
    values: dict[str, object] = {
        "schema_version": "phase11-shadow-cost-projection-scenario-v1",
        "scenario_id": None,
        "daily_eligible_event_count": 100,
        "projection_day_count": 30,
        "sample_day_count": 7,
        "l0_share": Decimal("0.50"),
        "l1_share": Decimal("0.25"),
        "direct_l2_share": Decimal("0.125"),
        "l1_to_l2_share": Decimal("0.125"),
        "unavailable_or_unprocessed_share": Decimal("0"),
        "uncertainty_classes": ("COVERAGE_WINDOW_LIMIT",),
        "reason_codes": ("EXPLICIT_SCENARIO_ASSUMPTIONS",),
    }
    values.update(overrides)
    return ShadowCostProjectionScenarioV1(**values)


def _plan(
    route_report: ShadowRouteCostAggregateReportV1 | None = None,
    comparative_report: ShadowAggregateComparativeReportV1 | None = None,
    scenario: ShadowCostProjectionScenarioV1 | None = None,
    **overrides: object,
) -> ShadowCostProjectionPlanV1:
    values: dict[str, object] = {
        "schema_version": "phase11-shadow-cost-projection-plan-v1",
        "projection_plan_id": None,
        "route_cost_aggregate_report": route_report or _route_cost_report(),
        "comparative_aggregate_report": comparative_report or _comparative_report(),
        "scenario": scenario or _scenario(),
        "projected_at": PROJECTED_AT,
        "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
        "scope": ShadowCostProjectionScopeV1.AGGREGATE_EVIDENCE_ONLY,
        "reason_codes": ("ROUTE_COST_PROJECTION",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowCostProjectionPlanV1(**values)


def _report(**overrides: object) -> ShadowCostProjectionReportV1:
    return ShadowCostProjectorV1().project(_plan(**overrides))


def test_public_contract_is_closed_immutable_and_contains_no_authority_fields():
    for contract in (
        ShadowCostProjectionScenarioV1,
        ShadowCostProjectionPlanV1,
        ShadowCostProjectionReportV1,
        ShadowProjectedRouteVolumeV1,
        ShadowProjectedCostMetricV1,
    ):
        assert getattr(contract, "__slots__")
        assert "__dict__" not in contract.__slots__
    report_names = {item.name for item in fields(ShadowCostProjectionReportV1)}
    forbidden = {"provider_ranking", "preferred_arm", "approved_budget", "budget_recommendation", "promotion_verdict", "phase11_completion", "rollout", "phase12_enablement", "persistence", "publication"}
    assert not report_names & forbidden


def test_scenario_requires_exact_decimal_shares_that_reconcile_and_converge():
    first = _scenario()
    second = _scenario()
    assert first.identity == second.identity
    assert first.daily_eligible_event_count == 100
    assert sum((first.l0_share, first.l1_share, first.direct_l2_share, first.l1_to_l2_share, first.unavailable_or_unprocessed_share), Decimal("0")) == Decimal("1")
    with pytest.raises(ShadowCostProjectionValidationError):
        _scenario(l0_share=Decimal("0.51"))
    with pytest.raises(ShadowCostProjectionValidationError):
        _scenario(l0_share=0.5)
    with pytest.raises(ShadowCostProjectionValidationError):
        _scenario(l0_share=Decimal("NaN"))


@pytest.mark.parametrize("field,value", (("daily_eligible_event_count", -1), ("projection_day_count", -1), ("sample_day_count", -1), ("daily_eligible_event_count", True), ("projection_day_count", True), ("sample_day_count", True)))
def test_scenario_rejects_invalid_or_boolean_exact_counts(field, value):
    with pytest.raises(ShadowCostProjectionValidationError):
        _scenario(**{field: value})


def test_plan_binds_real_aggregate_reports_and_rejects_lineage_time_and_effect_breaks():
    route = _route_cost_report()
    comparative = _comparative_report()
    plan = _plan(route, comparative)
    assert plan.route_cost_aggregate_report is route
    assert plan.comparative_aggregate_report is comparative
    assert plan.locked_baseline_commit == LOCKED_PHASE09_BASELINE
    with pytest.raises(ShadowCostProjectionValidationError):
        _plan(route, _comparative_report(baseline="f" * 40))
    with pytest.raises(ShadowCostProjectionValidationError):
        _plan(route, _comparative_report(window_end="2026-07-17T00:09:00Z"))
    with pytest.raises(ShadowCostProjectionValidationError):
        _plan(route, comparative, projected_at=WINDOW_END)
    with pytest.raises(ShadowCostProjectionValidationError):
        _plan(_route_cost_report(proof="NOT_PROVEN"), comparative)


def test_projected_route_volumes_are_exact_decimal_and_direct_l2_remains_separate():
    report = _report()
    by_route = {item.route: item for item in report.projected_route_volumes}
    assert set(by_route) == set(ROUTES)
    assert by_route["L0"].daily_volume == Decimal("50")
    assert by_route["L1"].daily_volume == Decimal("25")
    assert by_route["L2"].daily_volume == Decimal("12.5")
    assert by_route["L1_TO_L2"].daily_volume == Decimal("12.5")
    assert by_route["L0"].sample_volume == Decimal("350")
    assert by_route["L1_TO_L2"].projected_volume == Decimal("375")
    assert sum(item.projected_volume for item in by_route.values()) == Decimal("3000")


def test_actual_cost_metrics_use_their_exact_route_summaries_and_denominators():
    report = _report()
    metrics = report.cost_metrics_by_name
    assert metrics["COST_PER_ELIGIBLE_EVENT"].value == Decimal("0.75")
    assert metrics["COST_PER_L1"].value == Decimal("0.4")
    assert metrics["COST_PER_DIRECT_L2"].value == Decimal("0.9")
    assert metrics["COST_PER_L1_TO_L2"].value == Decimal("1.6")
    assert metrics["COMBINED_COST_PER_L2"].value == Decimal("1.25")
    assert metrics["COST_PER_L1"].source_summary_id == _route_cost_report().route_cost_summaries["L1"].identity
    assert metrics["COMBINED_COST_PER_L2"].source_summary_id == _route_cost_report().combined_l2_cost_summary.identity
    assert metrics["COST_PER_ELIGIBLE_EVENT"].source_available_denominator == 40


def test_explicit_actual_zero_is_available_evidence_not_missing_cost():
    report = _report(route_report=_route_cost_report(l1=Decimal("0")))
    metric = report.cost_metrics_by_name["COST_PER_L1"]
    assert metric.availability is ShadowCostProjectionAvailabilityV1.COMPLETE
    assert metric.value == Decimal("0")


def test_zero_route_denominator_is_unavailable_and_is_not_coerced_to_zero():
    report = _report(route_report=_route_cost_report(l1=None, l1_available=0))
    metric = report.cost_metrics_by_name["COST_PER_L1"]
    assert metric.availability is ShadowCostProjectionAvailabilityV1.UNAVAILABLE
    assert metric.value is None
    assert metric.source_available_denominator == 0


def test_nonzero_volume_with_unavailable_route_cost_makes_cost_projections_partial():
    report = _report(route_report=_route_cost_report(direct_l2=None, direct_l2_available=0))
    assert report.projected_daily_cost.availability is ShadowCostProjectionAvailabilityV1.PARTIAL
    assert report.projected_daily_cost.value is None
    assert report.projected_monthly_cost.value is None
    assert "UNAVAILABLE_L2_ROUTE_COST" in report.reason_codes


def test_projected_cost_horizons_apply_only_route_specific_actual_means():
    report = _report()
    assert report.projected_daily_cost.value == Decimal("75")
    assert report.projected_sample_cost.value == Decimal("525")
    assert report.projected_monthly_cost.value == Decimal("2250")
    assert report.projected_daily_cost.source_available_denominator == 40
    assert report.projected_monthly_cost.source_available_denominator == 40


def test_retry_failure_evidence_is_copied_without_multiplier_and_can_remain_unavailable():
    report = _report()
    assert report.observed_call_count == 43
    assert report.observed_retry_count == 3
    assert report.observed_retry_rate == Decimal("3") / Decimal("43")
    assert report.terminal_failure_counts == {"FIXTURE_FAILURE": 2}
    unavailable = _report(comparative_report=_comparative_report(retry_available=0, retry_total=0))
    assert unavailable.observed_retry_count is None
    assert unavailable.observed_retry_rate is None


def test_report_binds_source_identities_windows_scenario_and_not_approved_owner_gate():
    plan = _plan()
    report = ShadowCostProjectorV1().project(plan)
    assert report.projection_plan_id == plan.identity
    assert report.route_cost_aggregate_report_id == plan.route_cost_aggregate_report.identity
    assert report.comparative_aggregate_report_id == plan.comparative_aggregate_report.identity
    assert report.scenario_id == plan.scenario.identity
    assert report.owner_budget_gate_status is ShadowOwnerBudgetGateStatusV1.NOT_APPROVED
    assert report.production_effect == "NONE"
    assert report.zero_production_effect_proof == "PROVEN_NONE"
    assert report.projection_availability is ShadowCostProjectionAvailabilityV1.COMPLETE
    assert report.projection_confidence in set(ShadowCostProjectionConfidenceV1)


@pytest.mark.parametrize(
    "change",
    (
        {"daily_eligible_event_count": 101},
        {"projection_day_count": 31},
        {"l1_share": Decimal("0.24"), "unavailable_or_unprocessed_share": Decimal("0.01")},
        {"uncertainty_classes": ("COVERAGE_WINDOW_LIMIT", "ROUTE_MIX_STABILITY")},
    ),
)
def test_identities_converge_for_equivalent_evidence_and_diverge_for_material_assumptions(change):
    first = _report()
    assert first.identity == _report().identity
    assert first.identity != _report(scenario=_scenario(**change)).identity


def test_canonical_hash_is_utf8_lowercase_sha256_and_does_not_use_runtime_identity():
    assert canonical_json_bytes({"b": Decimal("1.0"), "a": "é"}) == b'{"a":"\xc3\xa9","b":"1"}'
    assert sha256_hex(b"projection") == hashlib.sha256(b"projection").hexdigest()
    assert sha256_hex(b"projection") == sha256_hex(b"projection").lower()


def test_report_rejects_mutation_and_only_project_creates_report():
    report = _report()
    with pytest.raises((AttributeError, TypeError)):
        report.owner_budget_gate_status = ShadowOwnerBudgetGateStatusV1.NOT_APPROVED
    assert not hasattr(ShadowCostProjectionPlanV1, "project")
    assert callable(ShadowCostProjectorV1().project)


def test_static_dependency_and_side_effect_boundaries():
    module = ast.parse(Path("engine/phase_11_shadow_cost_projection_v1.py").read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio"}
    forbidden_names = {
        "open", "float", "ShadowRouteCostEvidenceBuilderV1", "ShadowRouteCostAggregatorV1",
        "ShadowComparativeEvaluatorV1", "ShadowComparativeAggregatorV1", "ShadowQualityEvaluatorV1",
        "ShadowQualityAggregatorV1", "ShadowAlternativeArmEvaluatorV1", "ShadowAlternativeArmAggregatorV1",
        "ShadowAdjudicationFinalizerV1", "Provider", "Budget", "Ranking", "Replay", "Persistence", "Publication",
    }
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module} | {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not (names | attributes) & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.With)) for node in ast.walk(module))
