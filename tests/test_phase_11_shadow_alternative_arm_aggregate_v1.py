"""RED contract for aggregate detached alternative-arm evidence only."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_finalization_evidence_bridge_v1 import (
    ShadowTerminalRecordStatusV1,
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
    ShadowAlternativeArmEvaluationV1,
)
from engine.phase_11_shadow_alternative_arm_aggregate_v1 import (
    AlternativeArmAggregateRateAvailabilityV1,
    AlternativeArmAggregationScopeV1,
    AlternativeArmCoverageStatusV1,
    AlternativeArmTelemetryAvailabilityV1,
    ShadowAggregateAlternativeArmPlanV1,
    ShadowAggregateAlternativeArmReportV1,
    ShadowAlternativeArmAggregationValidationError,
    ShadowAlternativeArmAggregatorV1,
    ShadowAlternativeArmCoveragePlanV1,
    ShadowAlternativeArmCoverageResultV1,
    ShadowAlternativeArmEvaluationSetV1,
    ShadowAlternativeArmRateEvidenceV1,
    ShadowAlternativeArmTelemetrySummaryV1,
    canonical_json_bytes,
    lowercase_sha256,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    MetricAvailabilityV1,
)
from engine.phase_11_shadow_quality_evaluator_v1 import MappingQualityResultV1


WINDOW_START = datetime(2026, 7, 17, 0, 10, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 7, 17, 0, 14, tzinfo=UTC)
WINDOW_END = EVALUATED_AT
GENERATED_AT = datetime(2026, 7, 17, 0, 15, tzinfo=UTC)


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


def _sha(value):
    return hashlib.sha256(
        json.dumps(
            _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def _evaluation(index: int, **overrides) -> ShadowAlternativeArmEvaluationV1:
    """Direct immutable detached evaluation; no evaluator or provider is used."""

    arm = (
        AlternativeArmIdentityV1.DEEPSEEK_ONLY,
        AlternativeArmIdentityV1.CLAUDE_SONNET_ONLY,
        AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY,
        AlternativeArmIdentityV1.ROUTED_PRIMARY_PLUS_ESCALATION,
    )[(index - 1) % 4]
    values = {
        "schema_version": "phase11-shadow-alternative-arm-evaluation-v1",
        "alternative_arm_evaluation_id": _sha(("evaluation", index)),
        "alternative_arm_plan_id": _sha(("plan", index)),
        "quality_observation_id": _sha(("quality", index)),
        "arm_evidence_id": _sha(("arm-evidence", index)),
        "candidate_id": f"candidate-{index}",
        "event_id": f"event-{index}",
        "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
        "arm_identity": arm,
        "provider_model_reference": f"model-{arm.value.lower()}",
        "execution_status": AlternativeArmExecutionStatusV1.COMPLETED,
        "decision_availability": AlternativeArmEvidenceAvailabilityV1.AVAILABLE,
        "arm_decision": AlternativeArmDecisionV1.ALLOW,
        "arm_decision_quality": AlternativeArmDecisionQualityV1.CORRECT,
        "mapping_quality": MappingQualityResultV1.CORRECT,
        "false_block": AlternativeFalseBlockClassificationV1.NOT_FALSE_BLOCK,
        "missed_material_event": (
            AlternativeMissedMaterialEventClassificationV1.NOT_MISSED
        ),
        "escalation_efficiency": (
            AlternativeEscalationEfficiencyV1.SUFFICIENT_WITHOUT_ESCALATION
        ),
        "latency_availability": MetricAvailabilityV1.AVAILABLE,
        "actual_latency_ms": 100 + index,
        "input_tokens_availability": MetricAvailabilityV1.AVAILABLE,
        "actual_input_tokens": 10 + index,
        "output_tokens_availability": MetricAvailabilityV1.AVAILABLE,
        "actual_output_tokens": 5 + index,
        "cost_availability": MetricAvailabilityV1.AVAILABLE,
        "actual_cost": Decimal("0.01") * Decimal(index),
        "call_count": 1,
        "retry_count": 0,
        "terminal_status": None,
        "completed_at": EVALUATED_AT - timedelta(minutes=1),
        "evaluated_at": EVALUATED_AT,
        "reason_codes": ("DETACHED_AGGREGATE_FIXTURE",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowAlternativeArmEvaluationV1(**values)


def _principal_evaluations() -> tuple[ShadowAlternativeArmEvaluationV1, ...]:
    unavailable = {
        "decision_availability": AlternativeArmEvidenceAvailabilityV1.UNAVAILABLE,
        "arm_decision": None,
        "arm_decision_quality": AlternativeArmDecisionQualityV1.UNAVAILABLE,
        "false_block": AlternativeFalseBlockClassificationV1.UNAVAILABLE,
        "missed_material_event": AlternativeMissedMaterialEventClassificationV1.UNAVAILABLE,
    }
    absent_metrics = {
        "latency_availability": MetricAvailabilityV1.UNAVAILABLE,
        "actual_latency_ms": None,
        "input_tokens_availability": MetricAvailabilityV1.UNAVAILABLE,
        "actual_input_tokens": None,
        "output_tokens_availability": MetricAvailabilityV1.UNAVAILABLE,
        "actual_output_tokens": None,
        "cost_availability": MetricAvailabilityV1.UNAVAILABLE,
        "actual_cost": None,
    }
    return (
        _evaluation(1, actual_cost=Decimal("0")),
        _evaluation(2, arm_decision=AlternativeArmDecisionV1.HOLD),
        _evaluation(
            3,
            arm_decision=AlternativeArmDecisionV1.BLOCK,
            arm_decision_quality=AlternativeArmDecisionQualityV1.TOO_RESTRICTIVE,
            false_block=AlternativeFalseBlockClassificationV1.FALSE_BLOCK,
        ),
        _evaluation(
            4,
            arm_decision=AlternativeArmDecisionV1.ALLOW,
            arm_decision_quality=AlternativeArmDecisionQualityV1.TOO_PERMISSIVE,
            missed_material_event=(
                AlternativeMissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
            ),
            escalation_efficiency=AlternativeEscalationEfficiencyV1.ESCALATION_REQUIRED,
        ),
        _evaluation(
            5,
            execution_status=AlternativeArmExecutionStatusV1.DENIED,
            escalation_efficiency=AlternativeEscalationEfficiencyV1.INDETERMINATE,
            **unavailable,
        ),
        _evaluation(
            6,
            execution_status=AlternativeArmExecutionStatusV1.FAILED_CLOSED,
            escalation_efficiency=AlternativeEscalationEfficiencyV1.NOT_APPLICABLE,
            **unavailable,
        ),
        _evaluation(
            7,
            execution_status=AlternativeArmExecutionStatusV1.PARTIAL_EVIDENCE,
            arm_decision_quality=(
                AlternativeArmDecisionQualityV1.INSUFFICIENT_GROUND_TRUTH
            ),
            false_block=(
                AlternativeFalseBlockClassificationV1.INSUFFICIENT_GROUND_TRUTH
            ),
            missed_material_event=(
                AlternativeMissedMaterialEventClassificationV1.INSUFFICIENT_GROUND_TRUTH
            ),
            escalation_efficiency=(
                AlternativeEscalationEfficiencyV1.INSUFFICIENT_GROUND_TRUTH
            ),
            **{key: value for key, value in unavailable.items() if key not in {"arm_decision_quality", "false_block", "missed_material_event"}},
        ),
        _evaluation(
            8,
            execution_status=AlternativeArmExecutionStatusV1.PARTIAL_EVIDENCE,
            escalation_efficiency=AlternativeEscalationEfficiencyV1.UNNECESSARY_ESCALATION,
            terminal_status=ShadowTerminalRecordStatusV1.PARTIAL_EVIDENCE,
            cost_availability=MetricAvailabilityV1.UNAVAILABLE,
            actual_cost=None,
            **unavailable,
        ),
        _evaluation(
            9,
            mapping_quality=MappingQualityResultV1.INCORRECT,
            latency_availability=MetricAvailabilityV1.UNAVAILABLE,
            actual_latency_ms=None,
            cost_availability=MetricAvailabilityV1.UNAVAILABLE,
            actual_cost=None,
        ),
        _evaluation(
            10,
            mapping_quality=MappingQualityResultV1.UNAVAILABLE,
            input_tokens_availability=MetricAvailabilityV1.UNAVAILABLE,
            actual_input_tokens=None,
            output_tokens_availability=MetricAvailabilityV1.UNAVAILABLE,
            actual_output_tokens=None,
            cost_availability=MetricAvailabilityV1.UNAVAILABLE,
            actual_cost=None,
        ),
    )


def _coverage(**overrides) -> ShadowAlternativeArmCoveragePlanV1:
    values = {
        "schema_version": "phase11-shadow-alternative-arm-coverage-plan-v1",
        "coverage_plan_id": None,
        "minimum_total_evaluations": 10,
        "minimum_deepseek_only": 2,
        "minimum_sonnet_only": 2,
        "minimum_opus_only": 2,
        "minimum_routed": 2,
        "minimum_completed": 4,
        "minimum_decision_available": 4,
        "minimum_quality_comparable": 4,
        "reason_codes": ("PREDECLARED_ARM_COVERAGE",),
    }
    values.update(overrides)
    return ShadowAlternativeArmCoveragePlanV1(**values)


def _set(observations, **overrides) -> ShadowAlternativeArmEvaluationSetV1:
    values = {
        "schema_version": "phase11-shadow-alternative-arm-evaluation-set-v1",
        "alternative_arm_evaluation_set_id": None,
        "evaluations": tuple(observations),
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
        "reason_codes": ("DETACHED_ARM_EVALUATIONS",),
    }
    values.update(overrides)
    return ShadowAlternativeArmEvaluationSetV1(**values)


def _plan(evaluation_set, coverage_plan, **overrides) -> ShadowAggregateAlternativeArmPlanV1:
    values = {
        "schema_version": "phase11-shadow-aggregate-alternative-arm-plan-v1",
        "aggregate_alternative_arm_plan_id": None,
        "evaluation_set": evaluation_set,
        "coverage_plan": coverage_plan,
        "generated_at": GENERATED_AT,
        "aggregation_scope": AlternativeArmAggregationScopeV1.ALTERNATIVE_ARM_EVALUATION_SET,
        "reason_codes": ("DESCRIPTIVE_ARM_AGGREGATION",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowAggregateAlternativeArmPlanV1(**values)


def test_direct_evaluation_fixture_matrix_is_immutable_and_complete():
    evaluations = _principal_evaluations()
    assert len(evaluations) == 10
    assert {item.arm_identity for item in evaluations} == set(AlternativeArmIdentityV1)
    assert {item.execution_status for item in evaluations} == set(AlternativeArmExecutionStatusV1)
    assert {item.arm_decision for item in evaluations if item.arm_decision is not None} == set(AlternativeArmDecisionV1)
    assert Decimal("0") in {item.actual_cost for item in evaluations if item.actual_cost is not None}
    with pytest.raises(Exception):
        evaluations[0].actual_cost = Decimal("1")  # type: ignore[misc]


def test_coverage_plan_freezes_predeclared_evidence_targets():
    plan = _coverage()
    assert plan.identity == _coverage().identity
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        _coverage(minimum_total_evaluations=True)
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        _coverage(minimum_routed=-1)
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        ShadowAlternativeArmCoveragePlanV1(**{**{name: getattr(plan, name) for name in plan.__slots__}, "callback": "FORBIDDEN"})


def test_evaluation_set_is_canonical_and_rejects_duplicate_foreign_or_outside_evidence():
    evaluations = _principal_evaluations()
    first = _set(evaluations)
    second = _set(tuple(reversed(evaluations)))
    assert first.identity == second.identity
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        _set((evaluations[0], evaluations[0]))
    duplicate_key = _evaluation(
        99,
        candidate_id="candidate-1",
        event_id="event-1",
        arm_identity=AlternativeArmIdentityV1.DEEPSEEK_ONLY,
    )
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        _set((evaluations[0], duplicate_key))
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        _set((_evaluation(98, locked_baseline_commit="b" * 40),))
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        _set((_evaluation(97, evaluated_at=WINDOW_START - timedelta(seconds=1)),))


def test_aggregate_plan_binds_set_coverage_window_and_zero_effect():
    plan = _plan(_set(_principal_evaluations()), _coverage())
    assert plan.identity == _plan(_set(_principal_evaluations()), _coverage()).identity
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        _plan(_set(_principal_evaluations()), _coverage(), generated_at=WINDOW_START)
    with pytest.raises(ShadowAlternativeArmAggregationValidationError):
        _plan(_set(_principal_evaluations()), _coverage(), production_effect="APPLIED")


def test_aggregate_counts_distributions_rates_and_decimal_telemetry_are_exact():
    report = ShadowAlternativeArmAggregatorV1().aggregate(
        _plan(_set(_principal_evaluations()), _coverage())
    )
    assert type(report) is ShadowAggregateAlternativeArmReportV1
    assert report.total_evaluation_count == 10
    assert report.arm_identity_counts == {
        AlternativeArmIdentityV1.DEEPSEEK_ONLY: 3,
        AlternativeArmIdentityV1.CLAUDE_SONNET_ONLY: 3,
        AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY: 2,
        AlternativeArmIdentityV1.ROUTED_PRIMARY_PLUS_ESCALATION: 2,
    }
    assert sum(report.execution_status_counts.values()) == 10
    assert sum(report.decision_availability_counts.values()) == 10
    assert sum(report.decision_quality_counts.values()) == 10
    assert sum(report.false_block_counts.values()) == 10
    assert sum(report.missed_event_counts.values()) == 10
    assert sum(report.escalation_efficiency_counts.values()) == 10
    assert report.decision_availability_rate == ShadowAlternativeArmRateEvidenceV1(6, 10, AlternativeArmAggregateRateAvailabilityV1.AVAILABLE, Decimal("0.6000000000"))
    assert report.decision_correctness_rate == ShadowAlternativeArmRateEvidenceV1(4, 6, AlternativeArmAggregateRateAvailabilityV1.AVAILABLE, Decimal("0.6666666667"))
    assert report.false_block_rate == ShadowAlternativeArmRateEvidenceV1(1, 5, AlternativeArmAggregateRateAvailabilityV1.AVAILABLE, Decimal("0.2000000000"))
    assert report.missed_material_event_rate == ShadowAlternativeArmRateEvidenceV1(1, 5, AlternativeArmAggregateRateAvailabilityV1.AVAILABLE, Decimal("0.2000000000"))
    assert report.unnecessary_escalation_rate == ShadowAlternativeArmRateEvidenceV1(1, 2, AlternativeArmAggregateRateAvailabilityV1.AVAILABLE, Decimal("0.5000000000"))
    assert report.cost_summary == ShadowAlternativeArmTelemetrySummaryV1(AlternativeArmTelemetryAvailabilityV1.PARTIAL, 7, 3, Decimal("0.27"), Decimal("0.0385714286"))
    assert report.cost_summary.total == Decimal("0.27")
    assert report.cost_summary.mean == Decimal("0.0385714286")


def test_zero_denominator_rates_remain_unavailable_not_zero():
    unavailable = _evaluation(
        200,
        execution_status=AlternativeArmExecutionStatusV1.DENIED,
        decision_availability=AlternativeArmEvidenceAvailabilityV1.UNAVAILABLE,
        arm_decision=None,
        arm_decision_quality=AlternativeArmDecisionQualityV1.UNAVAILABLE,
        false_block=AlternativeFalseBlockClassificationV1.UNAVAILABLE,
        missed_material_event=AlternativeMissedMaterialEventClassificationV1.UNAVAILABLE,
        escalation_efficiency=AlternativeEscalationEfficiencyV1.INDETERMINATE,
        cost_availability=MetricAvailabilityV1.UNAVAILABLE,
        actual_cost=None,
    )
    report = ShadowAlternativeArmAggregatorV1().aggregate(_plan(_set((unavailable,)), _coverage(minimum_total_evaluations=0)))
    assert report.false_block_rate == ShadowAlternativeArmRateEvidenceV1(0, 0, AlternativeArmAggregateRateAvailabilityV1.UNAVAILABLE, None)
    assert report.cost_summary.availability is AlternativeArmTelemetryAvailabilityV1.UNAVAILABLE
    assert report.cost_summary.total is None
    assert report.cost_summary.mean is None


def test_coverage_met_and_not_met_are_descriptive_only():
    report = ShadowAlternativeArmAggregatorV1().aggregate(_plan(_set(_principal_evaluations()), _coverage()))
    assert all(result.status is AlternativeArmCoverageStatusV1.MET for result in report.coverage_results)
    not_met = ShadowAlternativeArmAggregatorV1().aggregate(_plan(_set(_principal_evaluations()), _coverage(minimum_routed=3)))
    assert not_met.coverage_results_by_target["minimum_routed"].status is AlternativeArmCoverageStatusV1.NOT_MET
    assert type(not_met.coverage_results_by_target["minimum_routed"]) is ShadowAlternativeArmCoverageResultV1


def test_report_identity_converges_diverges_and_binds_direct_evidence_only():
    first = ShadowAlternativeArmAggregatorV1().aggregate(_plan(_set(_principal_evaluations()), _coverage()))
    second = ShadowAlternativeArmAggregatorV1().aggregate(_plan(_set(tuple(reversed(_principal_evaluations()))), _coverage()))
    changed = ShadowAlternativeArmAggregatorV1().aggregate(_plan(_set(_principal_evaluations()), _coverage(minimum_completed=5)))
    assert first.identity == second.identity
    assert first.identity != changed.identity
    assert first.production_effect == "NONE"
    assert first.zero_production_effect_proof == "PROVEN_NONE"
    assert canonical_json_bytes({"cost": Decimal("1.00")}) == b'{"cost":"1"}'
    assert lowercase_sha256({"report": first.identity}) == _sha({"report": first.identity})


def test_aggregate_module_static_boundaries_are_side_effect_free():
    source = Path(__file__).parents[1] / "engine" / "phase_11_shadow_alternative_arm_aggregate_v1.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "keyring", "boto3", "telegram", "ccxt", "ShadowAlternativeArmEvaluatorV1", "ShadowQualityEvaluatorV1", "ShadowQualityAggregatorV1", "ShadowComparativeEvaluatorV1", "ShadowComparativeAggregatorV1", "ShadowAdjudicationFinalizerV1", "evaluate", "compare", "finalize", "sqlite", "replay", "production", "publish", "persist", "ranking", "recommendation", "projection",
    }
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not (forbidden & imported)
    assert not (forbidden & names)
    assert not ({"evaluate", "compare", "finalize"} & attributes)
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, float)]
