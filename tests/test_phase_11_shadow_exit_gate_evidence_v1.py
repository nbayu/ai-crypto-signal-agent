"""RED contract for evidence-only Phase 11 exit-gate reconciliation.

Fixtures construct real immutable aggregate reports through their public
constructors.  They do not open event-level children or invoke upstream work.
"""

from __future__ import annotations

import ast
import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

import pytest

from engine.phase_11_shadow_alternative_arm_aggregate_v1 import (
    AlternativeArmAggregateRateAvailabilityV1,
    AlternativeArmCoverageStatusV1,
    AlternativeArmTelemetryAvailabilityV1,
    ShadowAggregateAlternativeArmReportV1,
    ShadowAlternativeArmCoverageResultV1,
    ShadowAlternativeArmRateEvidenceV1,
    ShadowAlternativeArmTelemetrySummaryV1,
)
from engine.phase_11_shadow_alternative_arm_evaluator_v1 import (
    AlternativeArmDecisionQualityV1,
    AlternativeArmDecisionV1,
    AlternativeArmEvidenceAvailabilityV1,
    AlternativeArmExecutionStatusV1,
    AlternativeArmIdentityV1,
    AlternativeEscalationEfficiencyV1,
    AlternativeFalseBlockClassificationV1,
    AlternativeMissedMaterialEventClassificationV1,
)
from engine.phase_11_shadow_comparative_aggregate_v1 import (
    AggregateMetricAvailabilityV1,
    ShadowAggregateComparativeReportV1,
    ShadowAggregateCoverageResultV1,
    ShadowAggregateCoverageStatusV1,
    ShadowAggregateRateEvidenceV1,
    ShadowAggregateTelemetrySummaryV1,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    ControlTreatmentDecisionDeltaV1,
    StructuredProviderDisagreementV1,
    TreatmentAvailabilityV1,
)
from engine.phase_11_shadow_cost_projection_v1 import (
    ShadowCostProjectionAvailabilityV1,
    ShadowCostProjectionConfidenceV1,
    ShadowCostProjectionReportV1,
    ShadowOwnerBudgetGateStatusV1,
    ShadowProjectedCostMetricV1,
    ShadowProjectedRouteVolumeV1,
)
from engine.phase_11_shadow_exit_gate_evidence_v1 import (
    ShadowPhase11ControlAssuranceEvidenceV1,
    ShadowPhase11ControlDomainEvidenceV1,
    ShadowPhase11ControlDomainV1,
    ShadowPhase11CriterionStatusV1,
    ShadowPhase11EvidenceDimensionResultV1,
    ShadowPhase11EvidenceDimensionV1,
    ShadowPhase11EvidenceReadinessV1,
    ShadowPhase11ExitGateCriteriaV1,
    ShadowPhase11ExitGateEvaluatorV1,
    ShadowPhase11ExitGatePlanV1,
    ShadowPhase11ExitGateReportV1,
    ShadowPhase11ExitGateScopeV1,
    ShadowPhase11ExitGateValidationError,
    ShadowPhase11LimitationsAcceptanceStatusV1,
    ShadowPhase11MechanicalReadinessV1,
    ShadowPhase11OwnerAcceptanceStatusV1,
    ShadowPhase11TieringValueEvidenceV1,
    ShadowPhase12RecommendationStatusV1,
    canonical_json_bytes,
    sha256_hex,
)
from engine.phase_11_shadow_quality_aggregate_v1 import (
    QualityAggregateRateAvailabilityV1,
    QualityCoverageStatusV1,
    ShadowAggregateQualityReportV1,
    ShadowQualityCoverageResultV1,
    ShadowQualityRateEvidenceV1,
)
from engine.phase_11_shadow_quality_evaluator_v1 import (
    ControlQualityResultV1,
    EscalationNecessityV1,
    FalseBlockClassificationV1,
    MappingQualityResultV1,
    MaterialityQualityResultV1,
    MissedMaterialEventClassificationV1,
    TreatmentQualityResultV1,
)
from engine.phase_11_shadow_route_cost_evidence_v1 import (
    RouteCostCoverageStatusV1,
    RouteCostMetricAvailabilityV1,
    ShadowRouteCostAggregateReportV1,
    ShadowRouteCostCoverageResultV1,
    ShadowRouteCostSummaryV1,
)


BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
START = datetime(2026, 7, 17, 0, 0, tzinfo=UTC)
END = datetime(2026, 7, 17, 0, 10, tzinfo=UTC)
ROUTE_AT = datetime(2026, 7, 17, 0, 11, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 7, 17, 0, 14, tzinfo=UTC)
ROUTES = ("L0", "L1", "L2", "L1_TO_L2")


def _id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _enum_counts(enum, selected=None, count: int = 0):
    result = {item: 0 for item in enum}
    if selected is not None:
        result[selected] = count
    return MappingProxyType(result)


def _comparative_rate(numerator: int = 40, denominator: int = 40):
    return ShadowAggregateRateEvidenceV1(
        numerator=numerator,
        denominator=denominator,
        availability=AggregateMetricAvailabilityV1.COMPLETE,
        value=Decimal(numerator) / Decimal(denominator),
    )


def _comparative_telemetry(total, available: int = 40):
    return ShadowAggregateTelemetrySummaryV1(
        availability=(AggregateMetricAvailabilityV1.COMPLETE if available else AggregateMetricAvailabilityV1.UNAVAILABLE),
        available_observation_count=available,
        unavailable_observation_count=40 - available,
        total=total if available else None,
        mean=(Decimal(total) / Decimal(available) if available else None),
    )


def _comparative_report(*, window_end: str = "2026-07-17T00:10:00Z"):
    routes = MappingProxyType({"L0": 20, "L1": 10, "L2": 5, "L1_TO_L2": 5})
    coverage = tuple(
        ShadowAggregateCoverageResultV1(route, 1, count, ShadowAggregateCoverageStatusV1.MET, _id("comparative-" + route))
        for route, count in routes.items()
    )
    return ShadowAggregateComparativeReportV1(
        schema_version="phase11-shadow-aggregate-comparative-report-v1", aggregate_report_id=_id("comparative-report"), aggregate_plan_id=_id("comparative-plan"), observation_set_id=_id("comparative-set"), coverage_plan_id=_id("comparative-coverage"), locked_baseline_commit=BASELINE, window_start="2026-07-17T00:00:00Z", window_end=window_end, generated_at="2026-07-17T00:12:00Z", total_observation_count=40, comparable_observation_count=40, non_comparable_observation_count=0, clean_treatment_count=38, terminal_treatment_count=2, route_counts=routes, direct_l2_count=5, l1_to_l2_count=5,
        control_decision_counts=MappingProxyType({"ALLOW": 40}), treatment_decision_counts=MappingProxyType({"ALLOW_NEWS_ELIGIBILITY": 38, "FAIL_CLOSED": 2}), decision_delta_counts=_enum_counts(ControlTreatmentDecisionDeltaV1), disagreement_counts=_enum_counts(StructuredProviderDisagreementV1), unresolved_ambiguity_count=0, treatment_availability_counts=_enum_counts(TreatmentAvailabilityV1, TreatmentAvailabilityV1.AVAILABLE, 38), terminal_status_counts=MappingProxyType({"FAILED_CLOSED": 2}), terminal_failure_counts=MappingProxyType({"FIXTURE_FAILURE": 2}), terminal_reconciliation_counts=MappingProxyType({"RESOLVED": 2}), comparability_rate=_comparative_rate(), clean_rate=_comparative_rate(38), terminal_rate=_comparative_rate(2), route_rates=MappingProxyType({route: _comparative_rate(count) for route, count in routes.items()}), disagreement_rate=_comparative_rate(0), unresolved_ambiguity_rate=_comparative_rate(0), treatment_unavailable_rate=_comparative_rate(2), decision_delta_rates=MappingProxyType({item: _comparative_rate(0) for item in ControlTreatmentDecisionDeltaV1}), latency_summary=_comparative_telemetry(4000), input_tokens_summary=_comparative_telemetry(400), output_tokens_summary=_comparative_telemetry(200), call_count_summary=_comparative_telemetry(43), retry_count_summary=_comparative_telemetry(3), tier_count_summary=_comparative_telemetry(50), cost_summary=_comparative_telemetry(Decimal("30")), coverage_results=coverage, coverage_results_by_target=MappingProxyType({item.target: item for item in coverage}), reason_codes=("COMPARATIVE_FIXTURE",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
    )


def _quality_rate(numerator: int = 10, denominator: int = 10):
    return ShadowQualityRateEvidenceV1(numerator, denominator, QualityAggregateRateAvailabilityV1.AVAILABLE, (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0000000001")))


def _quality_report(*, coverage_status=QualityCoverageStatusV1.MET):
    coverage = tuple(ShadowQualityCoverageResultV1(target, 1, 10 if coverage_status is QualityCoverageStatusV1.MET else 0, coverage_status, _id("quality-" + target)) for target in ("SAMPLE", "MATERIAL", "NON_MATERIAL", *ROUTES))
    return ShadowAggregateQualityReportV1(
        schema_version="phase11-shadow-aggregate-quality-report-v1", aggregate_quality_report_id=_id("quality-report"), aggregate_quality_plan_id=_id("quality-plan"), quality_observation_set_id=_id("quality-set"), coverage_plan_id=_id("quality-coverage"), locked_baseline_commit=BASELINE, window_start="2026-07-17T00:00:00Z", window_end="2026-07-17T00:10:00Z", generated_at="2026-07-17T00:12:00Z", total_quality_observation_count=40, usable_label_count=40, insufficient_label_count=0, clean_treatment_count=38, terminal_treatment_count=2, route_counts=MappingProxyType({"L0": 20, "L1": 10, "L2": 5, "L1_TO_L2": 5}), materiality_quality_counts=_enum_counts(MaterialityQualityResultV1), mapping_quality_counts=_enum_counts(MappingQualityResultV1), control_quality_counts=_enum_counts(ControlQualityResultV1), treatment_quality_counts=_enum_counts(TreatmentQualityResultV1), false_block_counts=_enum_counts(FalseBlockClassificationV1), missed_event_counts=_enum_counts(MissedMaterialEventClassificationV1), escalation_counts=_enum_counts(EscalationNecessityV1), terminal_status_counts=MappingProxyType({"FAILED_CLOSED": 2}), usable_label_coverage_rate=_quality_rate(), materiality_handling_correctness_rate=_quality_rate(), mapping_correctness_rate=_quality_rate(), control_correctness_rate=_quality_rate(), treatment_correctness_rate=_quality_rate(), false_block_rate=_quality_rate(0), missed_material_event_rate=_quality_rate(0), unnecessary_escalation_rate=_quality_rate(0), terminal_treatment_unavailable_rate=_quality_rate(2), coverage_results=coverage, coverage_results_by_target=MappingProxyType({item.target: item for item in coverage}), reason_codes=("QUALITY_FIXTURE",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
    )


def _arm_rate(numerator: int = 10, denominator: int = 10):
    return ShadowAlternativeArmRateEvidenceV1(numerator, denominator, AlternativeArmAggregateRateAvailabilityV1.AVAILABLE, (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0000000001")))


def _arm_telemetry(total):
    return ShadowAlternativeArmTelemetrySummaryV1(AlternativeArmTelemetryAvailabilityV1.COMPLETE, 10, 0, total, Decimal(total) / Decimal("10"))


def _alternative_report(*, include_opus: bool = True):
    arms = _enum_counts(AlternativeArmIdentityV1, AlternativeArmIdentityV1.DEEPSEEK_ONLY, 10)
    if include_opus:
        arm_map = dict(arms)
        arm_map[AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY] = 10
        arms = MappingProxyType(arm_map)
    coverage = tuple(ShadowAlternativeArmCoverageResultV1(target, 1, 10, AlternativeArmCoverageStatusV1.MET, _id("arm-" + target)) for target in ("DEEPSEEK_ONLY", "CLAUDE_OPUS_ONLY", "ROUTED"))
    return ShadowAggregateAlternativeArmReportV1(
        schema_version="phase11-shadow-aggregate-alternative-arm-report-v1", aggregate_alternative_arm_report_id=_id("arm-report-" + str(include_opus)), aggregate_alternative_arm_plan_id=_id("arm-plan"), evaluation_set_id=_id("arm-set"), coverage_plan_id=_id("arm-coverage"), locked_baseline_commit=BASELINE, window_start="2026-07-17T00:00:00Z", window_end="2026-07-17T00:10:00Z", generated_at="2026-07-17T00:12:00Z", total_evaluation_count=20 if include_opus else 10, arm_identity_counts=arms, execution_status_counts=_enum_counts(AlternativeArmExecutionStatusV1, AlternativeArmExecutionStatusV1.COMPLETED, 20), decision_availability_counts=_enum_counts(AlternativeArmEvidenceAvailabilityV1, AlternativeArmEvidenceAvailabilityV1.AVAILABLE, 20), arm_decision_counts=_enum_counts(AlternativeArmDecisionV1, AlternativeArmDecisionV1.ALLOW, 20), decision_quality_counts=_enum_counts(AlternativeArmDecisionQualityV1, AlternativeArmDecisionQualityV1.CORRECT, 20), false_block_counts=_enum_counts(AlternativeFalseBlockClassificationV1), missed_event_counts=_enum_counts(AlternativeMissedMaterialEventClassificationV1), escalation_efficiency_counts=_enum_counts(AlternativeEscalationEfficiencyV1), terminal_status_counts=MappingProxyType({}), decision_availability_rate=_arm_rate(), decision_correctness_rate=_arm_rate(), false_block_rate=_arm_rate(0), missed_material_event_rate=_arm_rate(0), unnecessary_escalation_rate=_arm_rate(0), completed_execution_rate=_arm_rate(), latency_summary=_arm_telemetry(1000), input_tokens_summary=_arm_telemetry(100), output_tokens_summary=_arm_telemetry(50), call_count_summary=_arm_telemetry(10), retry_count_summary=_arm_telemetry(0), cost_summary=_arm_telemetry(Decimal("10")), coverage_results=coverage, coverage_results_by_target=MappingProxyType({item.target: item for item in coverage}), reason_codes=("ALTERNATIVE_ARM_FIXTURE",), production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
    )


def _route_summary(route: str, total: Decimal | None, available: int = 10):
    return ShadowRouteCostSummaryV1("phase11-shadow-route-cost-summary-v1", _id("summary-" + route + str(total) + str(available)), route, available, available, 0, RouteCostMetricAvailabilityV1.AVAILABLE if available else RouteCostMetricAvailabilityV1.UNAVAILABLE, total, total / Decimal(available) if available else None, available)


def _route_report():
    summaries = {"L0": _route_summary("L0", Decimal("1")), "L1": _route_summary("L1", Decimal("4")), "L2": _route_summary("L2", Decimal("9")), "L1_TO_L2": _route_summary("L1_TO_L2", Decimal("16"))}
    combined = _route_summary("COMBINED_L2", Decimal("25"), 20)
    coverage = tuple(ShadowRouteCostCoverageResultV1("phase11-shadow-route-cost-coverage-result-v1", _id("route-" + route), route, 1, 10, RouteCostCoverageStatusV1.MET) for route in ROUTES)
    return ShadowRouteCostAggregateReportV1("phase11-shadow-route-cost-aggregate-report-v1", _id("route-report"), _id("route-plan"), _id("route-set"), _id("route-coverage"), BASELINE, START, END, ROUTE_AT, 40, MappingProxyType({route: 10 for route in ROUTES}), MappingProxyType(summaries), combined, coverage, MappingProxyType({item.target_name: item for item in coverage}), ("ROUTE_COST_FIXTURE",), "NONE", "PROVEN_NONE")


def _projection_report(route=None, comparative=None):
    route = route or _route_report()
    comparative = comparative or _comparative_report()
    volumes = tuple(ShadowProjectedRouteVolumeV1("phase11-shadow-projected-route-volume-v1", _id("volume-" + item), _id("scenario"), item, Decimal("0.25"), Decimal("25"), Decimal("175"), Decimal("750"), ("SCENARIO_VOLUME",)) for item in ROUTES)
    metric = ShadowProjectedCostMetricV1("phase11-shadow-projected-cost-metric-v1", _id("metric"), "COST_PER_ELIGIBLE_EVENT", _id("summary"), Decimal("30"), 40, 0, ShadowCostProjectionAvailabilityV1.COMPLETE, Decimal("0.75"), ("ACTUAL_COST",))
    projected = ShadowProjectedCostMetricV1("phase11-shadow-projected-cost-metric-v1", _id("monthly"), "PROJECTED_MONTHLY_COST", _id("projection-source"), Decimal("30"), 40, 0, ShadowCostProjectionAvailabilityV1.COMPLETE, Decimal("1387.50"), ("ROUTE_WEIGHTED",))
    return ShadowCostProjectionReportV1("phase11-shadow-cost-projection-report-v1", _id("projection-report"), _id("projection-plan"), route.identity, comparative.identity, _id("scenario"), BASELINE, START, END, "2026-07-17T00:00:00Z", "2026-07-17T00:10:00Z", EVALUATED_AT, volumes, (metric,), MappingProxyType({metric.metric_name: metric}), projected, projected, projected, 43, 3, Decimal("3") / Decimal("43"), MappingProxyType({"FIXTURE_FAILURE": 2}), ShadowCostProjectionAvailabilityV1.COMPLETE, ShadowCostProjectionConfidenceV1.MODERATE, ("COVERAGE_WINDOW_LIMIT",), ShadowOwnerBudgetGateStatusV1.NOT_APPROVED, ("PROJECTION_FIXTURE",), "NONE", "PROVEN_NONE")


def _criteria(**overrides):
    values = {
        "schema_version": "phase11-shadow-exit-gate-criteria-v1", "exit_gate_criteria_id": None,
        "required_coverage_targets": ("SAMPLE", "MATERIAL", "NON_MATERIAL", "L0", "L1", "L2", "L1_TO_L2"),
        "required_event_classes": ("MATERIAL", "NON_MATERIAL"), "required_route_classes": ROUTES,
        "required_alternative_arms": (AlternativeArmIdentityV1.DEEPSEEK_ONLY, AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY),
        "required_comparison_dimensions": tuple(ShadowPhase11EvidenceDimensionV1), "permitted_guardrail_regressions": Decimal("0"),
        "critical_control_defect_maximum": 0, "required_evidence_dimensions": tuple(ShadowPhase11EvidenceDimensionV1),
        "reason_codes": ("PREDECLARED_EXIT_GATE_CRITERIA",),
    }
    values.update(overrides)
    return ShadowPhase11ExitGateCriteriaV1(**values)


def _control_domain(domain, *, readiness=ShadowPhase11EvidenceReadinessV1.AVAILABLE, critical: int = 0):
    return ShadowPhase11ControlDomainEvidenceV1(schema_version="phase11-shadow-control-domain-evidence-v1", control_domain_evidence_id=None, domain=domain, evidence_readiness=readiness, critical_open_defect_count=critical, unresolved_noncritical_count=0, evidence_references=(_id("control-" + domain.value),), reason_codes=("SUPPLIED_CONTROL_ASSURANCE",))


def _assurance(domains=None, **overrides):
    values = {"schema_version": "phase11-shadow-control-assurance-evidence-v1", "control_assurance_evidence_id": None, "locked_baseline_commit": BASELINE, "window_start": START, "window_end": END, "generated_at": EVALUATED_AT, "domain_evidence": tuple(domains or (_control_domain(domain) for domain in ShadowPhase11ControlDomainV1)), "reason_codes": ("EXTERNAL_CONTROL_ASSURANCE",), "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE"}
    values.update(overrides)
    return ShadowPhase11ControlAssuranceEvidenceV1(**values)


def _tiering(arm, *, measurable=True, guardrails=True, readiness=ShadowPhase11EvidenceReadinessV1.AVAILABLE):
    return ShadowPhase11TieringValueEvidenceV1(schema_version="phase11-shadow-tiering-value-evidence-v1", tiering_value_evidence_id=None, alternative_arm=arm, comparison_dimensions=tuple(ShadowPhase11EvidenceDimensionV1), evidence_readiness=readiness, mandatory_guardrails_met=guardrails, measurable_value_met=measurable if readiness is ShadowPhase11EvidenceReadinessV1.AVAILABLE else None, source_report_identities=(_id("comparative-report"), _id("quality-report"), _id("arm-report-True"), _id("projection-report")), reason_codes=("PREDECLARED_TIERING_COMPARISON",))


def _plan(**overrides):
    route = _route_report(); comparative = _comparative_report()
    values = {"schema_version": "phase11-shadow-exit-gate-plan-v1", "exit_gate_plan_id": None, "comparative_aggregate_report": comparative, "quality_aggregate_report": _quality_report(), "alternative_arm_aggregate_report": _alternative_report(), "route_cost_aggregate_report": route, "cost_projection_report": _projection_report(route, comparative), "control_assurance_evidence": _assurance(), "criteria": _criteria(), "tiering_value_evidence": (_tiering(AlternativeArmIdentityV1.DEEPSEEK_ONLY), _tiering(AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY)), "evaluated_at": EVALUATED_AT, "locked_baseline_commit": BASELINE, "scope": ShadowPhase11ExitGateScopeV1.AGGREGATE_EVIDENCE_RECONCILIATION, "reason_codes": ("EXIT_GATE_RECONCILIATION",), "production_effect": "NONE", "zero_production_effect_proof": "PROVEN_NONE"}
    values.update(overrides)
    return ShadowPhase11ExitGatePlanV1(**values)


def _report(**overrides):
    return ShadowPhase11ExitGateEvaluatorV1().evaluate(_plan(**overrides))


def test_contracts_are_closed_immutable_and_exclude_completion_and_authority():
    for contract in (ShadowPhase11ExitGateCriteriaV1, ShadowPhase11ControlAssuranceEvidenceV1, ShadowPhase11ExitGatePlanV1, ShadowPhase11ExitGateReportV1, ShadowPhase11ControlDomainEvidenceV1, ShadowPhase11TieringValueEvidenceV1, ShadowPhase11EvidenceDimensionResultV1):
        assert getattr(contract, "__slots__") and "__dict__" not in contract.__slots__
    names = set(ShadowPhase11ExitGateReportV1.__dataclass_fields__)
    assert not names & {"phase11_completion", "provider_ranking", "preferred_provider", "budget_recommendation", "approved_budget", "promotion_verdict", "rollout_recommendation", "phase12_enablement", "persistence", "publication"}


def test_predeclared_criteria_are_deterministic_and_reject_invalid_counts_dimensions_and_duplicates():
    assert _criteria().identity == _criteria().identity
    with pytest.raises(ShadowPhase11ExitGateValidationError): _criteria(critical_control_defect_maximum=True)
    with pytest.raises(ShadowPhase11ExitGateValidationError): _criteria(critical_control_defect_maximum=-1)
    with pytest.raises(ShadowPhase11ExitGateValidationError): _criteria(required_route_classes=("L0", "L0"))
    with pytest.raises(ShadowPhase11ExitGateValidationError): _criteria(required_comparison_dimensions=("UNKNOWN",))


def test_control_assurance_requires_each_domain_once_and_does_not_treat_unavailable_as_zero():
    assurance = _assurance()
    assert tuple(item.domain for item in assurance.domain_evidence) == tuple(ShadowPhase11ControlDomainV1)
    assert assurance.identity == _assurance().identity
    with pytest.raises(ShadowPhase11ExitGateValidationError): _assurance(tuple(_control_domain(domain) for domain in tuple(ShadowPhase11ControlDomainV1)[:-1]))
    with pytest.raises(ShadowPhase11ExitGateValidationError): _assurance((_control_domain(ShadowPhase11ControlDomainV1.INTEGRITY),) * 6)
    with pytest.raises(ShadowPhase11ExitGateValidationError): _control_domain(ShadowPhase11ControlDomainV1.REPLAY, critical=True)


def test_plan_binds_exact_real_aggregate_reports_and_rejects_lineage_windows_and_time():
    plan = _plan()
    assert type(plan.comparative_aggregate_report) is ShadowAggregateComparativeReportV1
    assert type(plan.quality_aggregate_report) is ShadowAggregateQualityReportV1
    assert type(plan.alternative_arm_aggregate_report) is ShadowAggregateAlternativeArmReportV1
    assert type(plan.route_cost_aggregate_report) is ShadowRouteCostAggregateReportV1
    assert type(plan.cost_projection_report) is ShadowCostProjectionReportV1
    with pytest.raises(ShadowPhase11ExitGateValidationError): _plan(locked_baseline_commit="f" * 40)
    with pytest.raises(ShadowPhase11ExitGateValidationError): _plan(comparative_aggregate_report=_comparative_report(window_end="2026-07-17T00:09:00Z"))
    with pytest.raises(ShadowPhase11ExitGateValidationError): _plan(evaluated_at=END)


def test_coverage_criterion_uses_predeclared_results_and_event_route_classes():
    report = _report()
    assert report.coverage_criterion_status is ShadowPhase11CriterionStatusV1.MET
    not_met = _report(quality_aggregate_report=_quality_report(coverage_status=QualityCoverageStatusV1.NOT_MET))
    assert not_met.coverage_criterion_status is ShadowPhase11CriterionStatusV1.NOT_MET
    assert "UNDERREPRESENTED_MATERIAL" in not_met.unresolved_evidence_gaps


def test_control_criterion_is_met_only_for_supplied_available_zero_critical_evidence():
    assert _report().critical_control_defect_criterion_status is ShadowPhase11CriterionStatusV1.MET
    critical = list(_assurance().domain_evidence); critical[0] = _control_domain(ShadowPhase11ControlDomainV1.INTEGRITY, critical=1)
    assert _report(control_assurance_evidence=_assurance(tuple(critical))).critical_control_defect_criterion_status is ShadowPhase11CriterionStatusV1.NOT_MET
    unavailable = list(_assurance().domain_evidence); unavailable[0] = _control_domain(ShadowPhase11ControlDomainV1.INTEGRITY, readiness=ShadowPhase11EvidenceReadinessV1.UNAVAILABLE)
    assert _report(control_assurance_evidence=_assurance(tuple(unavailable))).critical_control_defect_criterion_status is ShadowPhase11CriterionStatusV1.INSUFFICIENT_EVIDENCE


def test_tiering_value_requires_both_predeclared_alternatives_and_guardrails_without_ranking():
    report = _report()
    assert report.tiering_value_criterion_status is ShadowPhase11CriterionStatusV1.MET
    assert {item.alternative_arm for item in report.tiering_value_evidence} == {AlternativeArmIdentityV1.DEEPSEEK_ONLY, AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY}
    missing = _report(tiering_value_evidence=(_tiering(AlternativeArmIdentityV1.DEEPSEEK_ONLY),))
    assert missing.tiering_value_criterion_status is ShadowPhase11CriterionStatusV1.INSUFFICIENT_EVIDENCE
    guarded = _report(tiering_value_evidence=(_tiering(AlternativeArmIdentityV1.DEEPSEEK_ONLY, guardrails=False), _tiering(AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY)))
    assert guarded.tiering_value_criterion_status is ShadowPhase11CriterionStatusV1.NOT_MET


def test_owner_review_dimensions_are_independent_evidence_readiness_only():
    report = _report()
    dimensions = {item.dimension: item for item in report.evidence_dimension_results}
    assert set(dimensions) == set(ShadowPhase11EvidenceDimensionV1)
    assert all(item.readiness is ShadowPhase11EvidenceReadinessV1.AVAILABLE for item in dimensions.values())
    assert report.mechanical_readiness is ShadowPhase11MechanicalReadinessV1.READY_FOR_OWNER_REVIEW
    assert report.owner_acceptance_status is ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED
    assert report.limitations_acceptance_status is ShadowPhase11LimitationsAcceptanceStatusV1.NOT_RECORDED
    assert report.phase_12_recommendation_status is ShadowPhase12RecommendationStatusV1.NOT_ISSUED
    assert report.owner_budget_gate_status is ShadowOwnerBudgetGateStatusV1.NOT_APPROVED


def test_mechanical_readiness_remains_evidence_only_for_not_ready_and_insufficient_cases():
    critical = list(_assurance().domain_evidence); critical[0] = _control_domain(ShadowPhase11ControlDomainV1.AUTHORITY, critical=1)
    assert _report(control_assurance_evidence=_assurance(tuple(critical))).mechanical_readiness is ShadowPhase11MechanicalReadinessV1.NOT_READY
    unavailable = list(_assurance().domain_evidence); unavailable[0] = _control_domain(ShadowPhase11ControlDomainV1.AUTHORITY, readiness=ShadowPhase11EvidenceReadinessV1.UNAVAILABLE)
    assert _report(control_assurance_evidence=_assurance(tuple(unavailable))).mechanical_readiness is ShadowPhase11MechanicalReadinessV1.INSUFFICIENT_EVIDENCE


def test_report_binds_limitations_uncertainty_source_identities_and_canonical_identity_order_independently():
    first = _report(); second = _report()
    assert first.identity == second.identity
    assert first.declared_limitations == ("COVERAGE_WINDOW_LIMIT",)
    assert first.uncertainty_classes == ("COVERAGE_WINDOW_LIMIT",)
    assert first.route_cost_aggregate_report_id == _route_report().identity
    assert first.cost_projection_report_id == _projection_report().identity
    reversed_assurance = _assurance(tuple(reversed(_assurance().domain_evidence)))
    assert _report(control_assurance_evidence=reversed_assurance).identity == first.identity
    assert _report(evaluated_at=EVALUATED_AT + timedelta(minutes=1)).identity != first.identity
    assert canonical_json_bytes({"b": Decimal("1.0"), "a": "é"}) == b'{"a":"\xc3\xa9","b":"1"}'
    assert sha256_hex(b"exit-gate") == hashlib.sha256(b"exit-gate").hexdigest()


def test_zero_production_effect_and_only_evaluate_creates_report():
    report = _report()
    assert report.production_effect == "NONE" and report.zero_production_effect_proof == "PROVEN_NONE"
    with pytest.raises((AttributeError, TypeError)): report.owner_acceptance_status = ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED
    assert not hasattr(ShadowPhase11ExitGatePlanV1, "evaluate")
    assert callable(ShadowPhase11ExitGateEvaluatorV1().evaluate)


def test_static_dependency_and_side_effect_boundaries():
    module = ast.parse(Path("engine/phase_11_shadow_exit_gate_evidence_v1.py").read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest"}
    forbidden_names = {"open", "float", "ShadowComparativeAggregatorV1", "ShadowQualityAggregatorV1", "ShadowAlternativeArmAggregatorV1", "ShadowRouteCostAggregatorV1", "ShadowCostProjectorV1", "ShadowAdjudicationFinalizerV1", "Provider", "Budget", "Ranking", "Replay", "Persistence", "Publication"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module} | {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.With)) for node in ast.walk(module))
