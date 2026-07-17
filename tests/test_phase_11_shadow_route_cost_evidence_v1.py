"""RED contract for immutable Phase 11 route-attributed actual-cost evidence."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_shadow_alternative_arm_evaluator_v1 import (
    AlternativeArmDecisionQualityV1,
    AlternativeArmDecisionV1,
    AlternativeArmEvidenceAvailabilityV1,
    AlternativeArmExecutionStatusV1,
    AlternativeArmIdentityV1,
    AlternativeEscalationEfficiencyV1,
    AlternativeFalseBlockClassificationV1,
    AlternativeMissedMaterialEventClassificationV1,
    ShadowAlternativeArmEvaluationV1,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    MetricAvailabilityV1,
    TreatmentAvailabilityV1,
)
from engine.phase_11_shadow_quality_evaluator_v1 import (
    ControlQualityResultV1,
    EntityMappingCorrectnessV1,
    EscalationNecessityV1,
    EventMaterialityV1,
    ExpectedHandlingV1,
    FalseBlockClassificationV1,
    MappingQualityResultV1,
    MaterialityQualityResultV1,
    MissedMaterialEventClassificationV1,
    QualityComparabilityV1,
    ShadowQualityObservationV1,
    TreatmentQualityResultV1,
)
from engine.phase_11_shadow_route_cost_evidence_v1 import (
    RouteCostAggregationScopeV1,
    RouteCostCoverageStatusV1,
    RouteCostEvidenceScopeV1,
    RouteCostMetricAvailabilityV1,
    ShadowRouteCostAggregatePlanV1,
    ShadowRouteCostAggregateReportV1,
    ShadowRouteCostAggregatorV1,
    ShadowRouteCostCoveragePlanV1,
    ShadowRouteCostCoverageResultV1,
    ShadowRouteCostEvidenceBuilderV1,
    ShadowRouteCostEvidencePlanV1,
    ShadowRouteCostEvidenceSetV1,
    ShadowRouteCostEvidenceV1,
    ShadowRouteCostSummaryV1,
    ShadowRouteCostValidationError,
    canonical_json_bytes,
    lowercase_sha256,
)


QUALITY_EVALUATED_AT = "2026-07-17T00:12:00Z"
COMPLETED_AT = datetime(2026, 7, 17, 0, 13, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 7, 17, 0, 14, tzinfo=UTC)
BRIDGED_AT = datetime(2026, 7, 17, 0, 15, tzinfo=UTC)
WINDOW_START = datetime(2026, 7, 17, 0, 15, tzinfo=UTC)
WINDOW_END = datetime(2026, 7, 17, 0, 16, tzinfo=UTC)
GENERATED_AT = datetime(2026, 7, 17, 0, 17, tzinfo=UTC)

ROUTES = ("L0", "L1", "L2", "L1_TO_L2")


def _canonical(value):
    if isinstance(value, Decimal):
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _sha(value) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def _quality(
    index: int,
    *,
    route: str = "L0",
    candidate_id: str | None = None,
    event_id: str | None = None,
    evaluated_at: str = QUALITY_EVALUATED_AT,
    baseline: str = LOCKED_PHASE09_BASELINE,
    production_effect: str = "NONE",
    zero_production_effect_proof: str = "PROVEN_NONE",
) -> ShadowQualityObservationV1:
    """Direct immutable quality evidence; labels and comparatives are not reopened."""

    return ShadowQualityObservationV1(
        schema_version="phase11-shadow-quality-observation-v1",
        quality_observation_id=None,
        quality_plan_id=_sha(("quality-plan", index)),
        comparative_observation_id=_sha(("comparative", index)),
        label_id=_sha(("label", index)),
        candidate_id=candidate_id or f"candidate-{index}",
        event_id=event_id or f"event-{index}",
        entity_id="BTC",
        locked_baseline_commit=baseline,
        original_treatment_route=route,
        treatment_availability=TreatmentAvailabilityV1.AVAILABLE,
        control_decision="ALLOW",
        treatment_decision="ALLOW_NEWS_ELIGIBILITY",
        terminal_status=None,
        label_usable=True,
        event_materiality=EventMaterialityV1.MATERIAL,
        mapping_correctness=EntityMappingCorrectnessV1.CORRECT,
        expected_handling=ExpectedHandlingV1.ALLOW,
        quality_comparability=QualityComparabilityV1.COMPARABLE,
        materiality_quality=MaterialityQualityResultV1.CORRECT_MATERIAL_EVENT_HANDLING,
        mapping_quality=MappingQualityResultV1.CORRECT,
        control_quality=ControlQualityResultV1.CORRECT,
        treatment_quality=TreatmentQualityResultV1.CORRECT,
        false_block=FalseBlockClassificationV1.NOT_FALSE_BLOCK,
        missed_material_event=MissedMaterialEventClassificationV1.NOT_MISSED,
        escalation_necessity=EscalationNecessityV1.NOT_ESCALATED,
        evaluated_at=evaluated_at,
        reason_codes=("ROUTE_COST_QUALITY_FIXTURE",),
        production_effect=production_effect,
        zero_production_effect_proof=zero_production_effect_proof,
    )


def _evaluation(
    index: int,
    quality: ShadowQualityObservationV1,
    *,
    arm_identity: AlternativeArmIdentityV1 = AlternativeArmIdentityV1.DEEPSEEK_ONLY,
    cost_availability: MetricAvailabilityV1 = MetricAvailabilityV1.AVAILABLE,
    actual_cost: Decimal | None = Decimal("0.10"),
    candidate_id: str | None = None,
    event_id: str | None = None,
    quality_observation_id: str | None = None,
    baseline: str | None = None,
    completed_at: datetime = COMPLETED_AT,
    evaluated_at: datetime = EVALUATED_AT,
    production_effect: str = "NONE",
    zero_production_effect_proof: str = "PROVEN_NONE",
) -> ShadowAlternativeArmEvaluationV1:
    """Direct immutable detached evaluation; no arm evaluator is invoked."""

    return ShadowAlternativeArmEvaluationV1(
        schema_version="phase11-shadow-alternative-arm-evaluation-v1",
        alternative_arm_evaluation_id=_sha(("alternative-evaluation", index, actual_cost)),
        alternative_arm_plan_id=_sha(("alternative-plan", index)),
        quality_observation_id=quality_observation_id or quality.quality_observation_id,
        arm_evidence_id=_sha(("arm-evidence", index)),
        candidate_id=candidate_id or quality.candidate_id,
        event_id=event_id or quality.event_id,
        locked_baseline_commit=baseline or quality.locked_baseline_commit,
        arm_identity=arm_identity,
        provider_model_reference="detached-model-v1",
        execution_status=AlternativeArmExecutionStatusV1.COMPLETED,
        decision_availability=AlternativeArmEvidenceAvailabilityV1.AVAILABLE,
        arm_decision=AlternativeArmDecisionV1.ALLOW,
        arm_decision_quality=AlternativeArmDecisionQualityV1.CORRECT,
        mapping_quality=MappingQualityResultV1.CORRECT,
        false_block=AlternativeFalseBlockClassificationV1.NOT_FALSE_BLOCK,
        missed_material_event=AlternativeMissedMaterialEventClassificationV1.NOT_MISSED,
        escalation_efficiency=AlternativeEscalationEfficiencyV1.SUFFICIENT_WITHOUT_ESCALATION,
        latency_availability=MetricAvailabilityV1.AVAILABLE,
        actual_latency_ms=100,
        input_tokens_availability=MetricAvailabilityV1.AVAILABLE,
        actual_input_tokens=10,
        output_tokens_availability=MetricAvailabilityV1.AVAILABLE,
        actual_output_tokens=5,
        cost_availability=cost_availability,
        actual_cost=actual_cost,
        call_count=1,
        retry_count=0,
        terminal_status=None,
        completed_at=completed_at,
        evaluated_at=evaluated_at,
        reason_codes=("ROUTE_COST_ARM_FIXTURE",),
        production_effect=production_effect,
        zero_production_effect_proof=zero_production_effect_proof,
    )


def _event_plan(
    quality: ShadowQualityObservationV1,
    evaluation: ShadowAlternativeArmEvaluationV1,
    **overrides,
) -> ShadowRouteCostEvidencePlanV1:
    values = {
        "schema_version": "phase11-shadow-route-cost-evidence-plan-v1",
        "route_cost_evidence_plan_id": None,
        "quality_observation": quality,
        "alternative_arm_evaluation": evaluation,
        "bridged_at": BRIDGED_AT,
        "scope": RouteCostEvidenceScopeV1.EVENT_LEVEL_ROUTE_ATTRIBUTION,
        "reason_codes": ("DIRECT_ROUTE_COST_JOIN",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowRouteCostEvidencePlanV1(**values)


def _bridge(
    index: int,
    *,
    route: str,
    cost_availability: MetricAvailabilityV1 = MetricAvailabilityV1.AVAILABLE,
    actual_cost: Decimal | None = Decimal("0.10"),
    arm_identity: AlternativeArmIdentityV1 = AlternativeArmIdentityV1.DEEPSEEK_ONLY,
    candidate_id: str | None = None,
    event_id: str | None = None,
) -> ShadowRouteCostEvidenceV1:
    quality = _quality(index, route=route, candidate_id=candidate_id, event_id=event_id)
    evaluation = _evaluation(
        index,
        quality,
        arm_identity=arm_identity,
        cost_availability=cost_availability,
        actual_cost=actual_cost,
        candidate_id=candidate_id,
        event_id=event_id,
    )
    return ShadowRouteCostEvidenceBuilderV1().build(_event_plan(quality, evaluation))


def _coverage(**overrides) -> ShadowRouteCostCoveragePlanV1:
    values = {
        "schema_version": "phase11-shadow-route-cost-coverage-plan-v1",
        "route_cost_coverage_plan_id": None,
        "minimum_total_evidence": 9,
        "minimum_l0_evidence": 3,
        "minimum_l1_evidence": 2,
        "minimum_direct_l2_evidence": 2,
        "minimum_l1_to_l2_evidence": 2,
        "minimum_l0_available_cost": 2,
        "minimum_l1_available_cost": 1,
        "minimum_direct_l2_available_cost": 1,
        "minimum_l1_to_l2_available_cost": 1,
        "reason_codes": ("PREDECLARED_ROUTE_COST_COVERAGE",),
    }
    values.update(overrides)
    return ShadowRouteCostCoveragePlanV1(**values)


def _evidence_set(evidence, **overrides) -> ShadowRouteCostEvidenceSetV1:
    values = {
        "schema_version": "phase11-shadow-route-cost-evidence-set-v1",
        "route_cost_evidence_set_id": None,
        "route_cost_evidence": tuple(evidence),
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
        "reason_codes": ("ROUTE_COST_EVIDENCE_WINDOW",),
    }
    values.update(overrides)
    return ShadowRouteCostEvidenceSetV1(**values)


def _aggregate_plan(
    evidence_set: ShadowRouteCostEvidenceSetV1,
    coverage_plan: ShadowRouteCostCoveragePlanV1,
    **overrides,
) -> ShadowRouteCostAggregatePlanV1:
    values = {
        "schema_version": "phase11-shadow-route-cost-aggregate-plan-v1",
        "route_cost_aggregate_plan_id": None,
        "evidence_set": evidence_set,
        "coverage_plan": coverage_plan,
        "generated_at": GENERATED_AT,
        "scope": RouteCostAggregationScopeV1.ROUTE_KEYED_ACTUAL_COST,
        "reason_codes": ("ROUTE_COST_AGGREGATION",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowRouteCostAggregatePlanV1(**values)


def _principal_evidence() -> tuple[ShadowRouteCostEvidenceV1, ...]:
    return (
        _bridge(1, route="L0", actual_cost=Decimal("0.10")),
        _bridge(2, route="L0", actual_cost=Decimal("0")),
        _bridge(3, route="L0", cost_availability=MetricAvailabilityV1.UNAVAILABLE, actual_cost=None),
        _bridge(4, route="L1", actual_cost=Decimal("0.20")),
        _bridge(5, route="L1", cost_availability=MetricAvailabilityV1.UNAVAILABLE, actual_cost=None),
        _bridge(6, route="L2", actual_cost=Decimal("0.30")),
        _bridge(7, route="L2", cost_availability=MetricAvailabilityV1.UNAVAILABLE, actual_cost=None),
        _bridge(8, route="L1_TO_L2", actual_cost=Decimal("0.40")),
        _bridge(9, route="L1_TO_L2", cost_availability=MetricAvailabilityV1.UNAVAILABLE, actual_cost=None),
    )


def test_event_level_builder_joins_only_committed_route_and_actual_cost():
    evidence = _principal_evidence()

    assert {item.route for item in evidence} == set(ROUTES)
    assert evidence[0].route == "L0"
    assert evidence[0].actual_cost == Decimal("0.10")
    assert evidence[1].cost_availability is MetricAvailabilityV1.AVAILABLE
    assert evidence[1].actual_cost == Decimal("0")
    assert evidence[2].cost_availability is MetricAvailabilityV1.UNAVAILABLE
    assert evidence[2].actual_cost is None
    assert all(item.quality_observation_id for item in evidence)
    assert all(item.production_effect == "NONE" for item in evidence)
    assert all(item.zero_production_effect_proof == "PROVEN_NONE" for item in evidence)


@pytest.mark.parametrize(
    ("change", "value"),
    (
        ("candidate_id", "different-candidate"),
        ("event_id", "different-event"),
        ("quality_observation_id", _sha(("different-quality",))),
        ("baseline", "f" * 40),
        ("production_effect", "SOMETHING"),
        ("zero_production_effect_proof", "NOT_PROVEN"),
    ),
)
def test_event_level_plan_rejects_mismatched_or_nonzero_child_evidence(change, value):
    quality = _quality(20, route="L1")
    evaluation = _evaluation(20, quality, **{change: value})

    with pytest.raises(ShadowRouteCostValidationError):
        _event_plan(quality, evaluation)


def test_event_level_plan_rejects_timestamp_ordering_and_converges_identities():
    quality = _quality(21, route="L2")
    evaluation = _evaluation(21, quality)
    first = _event_plan(quality, evaluation)
    second = _event_plan(quality, evaluation)

    assert first.identity == second.identity
    assert ShadowRouteCostEvidenceBuilderV1().build(first).identity == (
        ShadowRouteCostEvidenceBuilderV1().build(second).identity
    )

    with pytest.raises(ShadowRouteCostValidationError):
        _event_plan(quality, evaluation, bridged_at=EVALUATED_AT - timedelta(seconds=1))


def test_material_route_cost_and_availability_changes_diverge_event_evidence():
    l0 = _bridge(30, route="L0", actual_cost=Decimal("0.10"))
    l1 = _bridge(30, route="L1", actual_cost=Decimal("0.10"))
    changed_cost = _bridge(30, route="L0", actual_cost=Decimal("0.11"))
    unavailable = _bridge(
        30,
        route="L0",
        cost_availability=MetricAvailabilityV1.UNAVAILABLE,
        actual_cost=None,
    )

    assert len({l0.identity, l1.identity, changed_cost.identity, unavailable.identity}) == 4


def test_route_keyed_aggregate_preserves_separate_actual_cost_summaries():
    evidence_set = _evidence_set(tuple(reversed(_principal_evidence())))
    report = ShadowRouteCostAggregatorV1().aggregate(
        _aggregate_plan(evidence_set, _coverage())
    )

    assert isinstance(report, ShadowRouteCostAggregateReportV1)
    assert report.total_evidence_count == 9
    assert report.route_counts == {"L0": 3, "L1": 2, "L2": 2, "L1_TO_L2": 2}
    assert set(report.route_cost_summaries) == set(ROUTES)

    l0 = report.route_cost_summaries["L0"]
    l1 = report.route_cost_summaries["L1"]
    direct_l2 = report.route_cost_summaries["L2"]
    l1_to_l2 = report.route_cost_summaries["L1_TO_L2"]
    assert all(isinstance(item, ShadowRouteCostSummaryV1) for item in (l0, l1, direct_l2, l1_to_l2))
    assert (l0.total_evidence_count, l0.available_cost_count, l0.unavailable_cost_count) == (3, 2, 1)
    assert l0.total_actual_cost == Decimal("0.10")
    assert l0.available_value_mean == Decimal("0.0500000000")
    assert (l1.total_actual_cost, direct_l2.total_actual_cost, l1_to_l2.total_actual_cost) == (
        Decimal("0.20"), Decimal("0.30"), Decimal("0.40")
    )
    assert report.combined_l2_cost_summary.total_actual_cost == Decimal("0.70")
    assert report.combined_l2_cost_summary.available_cost_count == 2
    assert report.combined_l2_cost_summary.available_value_mean == Decimal("0.3500000000")


def test_zero_available_route_cost_denominator_remains_unavailable():
    evidence = (
        _bridge(40, route="L0", cost_availability=MetricAvailabilityV1.UNAVAILABLE, actual_cost=None),
        _bridge(41, route="L1", actual_cost=Decimal("0.20")),
        _bridge(42, route="L2", actual_cost=Decimal("0.30")),
        _bridge(43, route="L1_TO_L2", actual_cost=Decimal("0.40")),
    )
    report = ShadowRouteCostAggregatorV1().aggregate(
        _aggregate_plan(
            _evidence_set(evidence),
            _coverage(
                minimum_total_evidence=0,
                minimum_l0_evidence=0,
                minimum_l1_evidence=0,
                minimum_direct_l2_evidence=0,
                minimum_l1_to_l2_evidence=0,
                minimum_l0_available_cost=0,
                minimum_l1_available_cost=0,
                minimum_direct_l2_available_cost=0,
                minimum_l1_to_l2_available_cost=0,
            ),
        )
    )

    l0 = report.route_cost_summaries["L0"]
    assert l0.availability is RouteCostMetricAvailabilityV1.UNAVAILABLE
    assert l0.available_cost_count == 0
    assert l0.unavailable_cost_count == 1
    assert l0.total_actual_cost is None
    assert l0.available_value_mean is None


def test_coverage_results_are_descriptive_and_support_met_and_not_met():
    evidence_set = _evidence_set(_principal_evidence())
    met_report = ShadowRouteCostAggregatorV1().aggregate(
        _aggregate_plan(evidence_set, _coverage())
    )
    not_met_report = ShadowRouteCostAggregatorV1().aggregate(
        _aggregate_plan(evidence_set, _coverage(minimum_l1_available_cost=2))
    )

    assert all(isinstance(item, ShadowRouteCostCoverageResultV1) for item in met_report.coverage_results)
    assert met_report.coverage_results_by_target["minimum_l1_available_cost"].status is RouteCostCoverageStatusV1.MET
    assert not_met_report.coverage_results_by_target["minimum_l1_available_cost"].status is RouteCostCoverageStatusV1.NOT_MET


def test_evidence_set_rejects_duplicate_identity_duplicate_key_mixed_baseline_and_window():
    first = _bridge(50, route="L0")
    duplicate_identity = first
    duplicate_key = _bridge(
        51,
        route="L0",
        candidate_id=first.candidate_id,
        event_id=first.event_id,
        arm_identity=first.alternative_arm_identity,
    )

    assert duplicate_key.identity != first.identity
    assert (
        duplicate_key.candidate_id,
        duplicate_key.event_id,
        duplicate_key.alternative_arm_identity,
    ) == (
        first.candidate_id,
        first.event_id,
        first.alternative_arm_identity,
    )

    with pytest.raises(ShadowRouteCostValidationError):
        _evidence_set((first, duplicate_identity))
    with pytest.raises(ShadowRouteCostValidationError):
        _evidence_set((first, duplicate_key))
    with pytest.raises(ShadowRouteCostValidationError):
        _evidence_set((first, _bridge(52, route="L1")), locked_baseline_commit="e" * 40)
    with pytest.raises(ShadowRouteCostValidationError):
        _evidence_set((first,), window_end=BRIDGED_AT - timedelta(seconds=1))


def test_set_and_report_identities_are_order_independent_and_materially_bound():
    evidence = _principal_evidence()
    first_set = _evidence_set(evidence)
    second_set = _evidence_set(tuple(reversed(evidence)))
    assert first_set.identity == second_set.identity

    coverage = _coverage()
    first_report = ShadowRouteCostAggregatorV1().aggregate(_aggregate_plan(first_set, coverage))
    second_report = ShadowRouteCostAggregatorV1().aggregate(_aggregate_plan(second_set, coverage))
    assert first_report.identity == second_report.identity
    changed_coverage = _coverage(minimum_total_evidence=10)
    changed_report = ShadowRouteCostAggregatorV1().aggregate(
        _aggregate_plan(first_set, changed_coverage)
    )
    assert changed_report.identity != first_report.identity


def test_validation_and_static_side_effect_boundaries():
    with pytest.raises(ShadowRouteCostValidationError):
        _coverage(minimum_total_evidence=True)
    with pytest.raises(ShadowRouteCostValidationError):
        _coverage(minimum_l1_evidence=-1)

    module = ast.parse(
        Path("engine/phase_11_shadow_route_cost_evidence_v1.py").read_text(
            encoding="utf-8"
        )
    )
    forbidden_modules = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket",
        "subprocess", "threading", "multiprocessing", "concurrent", "asyncio",
    }
    forbidden_names = {
        "ShadowQualityEvaluatorV1", "ShadowAlternativeArmEvaluatorV1",
        "ShadowComparativeEvaluatorV1", "ShadowComparativeAggregatorV1",
        "ShadowAlternativeArmAggregatorV1", "ShadowQualityAggregatorV1",
        "ShadowAdjudicationFinalizerV1", "open", "float",
    }
    imported = {
        node.module.split(".")[0]
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(module)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await)) for node in ast.walk(module))
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    assert lowercase_sha256(b"route-cost") == hashlib.sha256(b"route-cost").hexdigest()
