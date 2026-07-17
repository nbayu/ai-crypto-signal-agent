"""RED contract for deterministic Phase 11 aggregate comparison.

The implementation is deliberately absent.  These tests use only completed,
immutable event-level observations; they never execute comparison, finalization,
provider, ledger, or production work.
"""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_finalization_evidence_bridge_v1 import (
    ShadowTerminalRecordStatusV1,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    ComparisonComparabilityV1,
    ControlTreatmentDecisionDeltaV1,
    MetricAvailabilityV1,
    ShadowComparativeEvaluationValidationError,
    ShadowComparativeObservationV1,
    StructuredProviderDisagreementV1,
    TreatmentAvailabilityV1,
)
from engine.phase_11_shadow_comparative_aggregate_v1 import (
    AggregateMetricAvailabilityV1,
    ShadowAggregateComparativePlanV1,
    ShadowAggregateComparativeReportV1,
    ShadowAggregateCoveragePlanV1,
    ShadowAggregateCoverageStatusV1,
    ShadowAggregationScopeV1,
    ShadowComparativeAggregationValidationError,
    ShadowComparativeAggregatorV1,
    ShadowComparativeObservationSetV1,
    canonical_json_bytes,
    lowercase_sha256,
)


UTC_NOW = datetime(2026, 7, 17, 0, 10, tzinfo=UTC)
WINDOW_START = datetime(2026, 7, 17, 0, 6, tzinfo=UTC)
WINDOW_END = datetime(2026, 7, 17, 0, 9, tzinfo=UTC)


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
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _observation(
    index: int,
    *,
    route: str = "L0",
    control_decision: str = "ALLOW",
    treatment_decision: str | None = "ALLOW_NEWS_ELIGIBILITY",
    decision_delta: ControlTreatmentDecisionDeltaV1 = (
        ControlTreatmentDecisionDeltaV1.NO_CHANGE
    ),
    disagreement: StructuredProviderDisagreementV1 = (
        StructuredProviderDisagreementV1.NOT_APPLICABLE
    ),
    unresolved_ambiguity: bool = False,
    terminal_status: ShadowTerminalRecordStatusV1 | None = None,
    telemetry: str = "COMPLETE",
    candidate_id: str | None = None,
    event_id: str | None = None,
    compared_at: datetime = UTC_NOW,
) -> ShadowComparativeObservationV1:
    """Directly construct immutable, already-created observation evidence."""

    terminal = terminal_status is not None
    if terminal:
        treatment_decision = None
        decision_delta = ControlTreatmentDecisionDeltaV1.TREATMENT_UNAVAILABLE
        disagreement = StructuredProviderDisagreementV1.UNAVAILABLE
        canonical_route = None
        terminal_failure = "FIXTURE_TERMINAL_FAILURE"
        terminal_reconciliation = (
            "RECONCILIATION_REQUIRED"
            if terminal_status
            is ShadowTerminalRecordStatusV1.RECONCILIATION_REQUIRED
            else "RESOLVED"
        )
    else:
        canonical_route = "L2" if route == "L1_TO_L2" else route
        terminal_failure = None
        terminal_reconciliation = None

    if telemetry == "COMPLETE":
        latency_availability = MetricAvailabilityV1.AVAILABLE
        total_latency_ms = 100 * index
        input_availability = MetricAvailabilityV1.AVAILABLE
        total_input_tokens = 10 * index
        output_availability = MetricAvailabilityV1.AVAILABLE
        total_output_tokens = 5 * index
        cost_availability = MetricAvailabilityV1.AVAILABLE
        total_actual_cost = Decimal("0.01") * index
    elif telemetry == "PARTIAL":
        latency_availability = MetricAvailabilityV1.AVAILABLE
        total_latency_ms = 100 * index
        input_availability = MetricAvailabilityV1.UNAVAILABLE
        total_input_tokens = None
        output_availability = MetricAvailabilityV1.AVAILABLE
        total_output_tokens = 5 * index
        cost_availability = MetricAvailabilityV1.UNAVAILABLE
        total_actual_cost = None
    elif telemetry == "UNAVAILABLE":
        latency_availability = MetricAvailabilityV1.UNAVAILABLE
        total_latency_ms = None
        input_availability = MetricAvailabilityV1.UNAVAILABLE
        total_input_tokens = None
        output_availability = MetricAvailabilityV1.UNAVAILABLE
        total_output_tokens = None
        cost_availability = MetricAvailabilityV1.UNAVAILABLE
        total_actual_cost = None
    else:
        raise AssertionError("unsupported fixture telemetry")

    review_count = {"L0": 1, "L1": 2, "L2": 2, "L1_TO_L2": 3}[route]
    review_ids = tuple(_sha(("review", index, item)) for item in range(review_count))
    return ShadowComparativeObservationV1(
        schema_version="phase11-shadow-comparative-observation-v1",
        observation_id=None,
        comparison_plan_id=_sha(("comparison-plan", index)),
        control_snapshot_id=_sha(("control-snapshot", index)),
        locked_baseline_commit=LOCKED_PHASE09_BASELINE,
        treatment_finalization_id=_sha(("treatment-finalization", index)),
        candidate_id=candidate_id or f"candidate-{index}",
        event_id=event_id or f"event-{index}",
        original_treatment_route=route,
        canonical_treatment_route=canonical_route,
        comparability=ComparisonComparabilityV1.COMPARABLE,
        treatment_availability=(
            TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE
            if terminal
            else TreatmentAvailabilityV1.AVAILABLE
        ),
        control_decision=control_decision,
        treatment_decision=treatment_decision,
        decision_delta=decision_delta,
        structured_disagreement=disagreement,
        unresolved_ambiguity=unresolved_ambiguity,
        terminal_status=terminal_status,
        terminal_failure=terminal_failure,
        terminal_reconciliation=terminal_reconciliation,
        latency_availability=latency_availability,
        total_latency_ms=total_latency_ms,
        input_tokens_availability=input_availability,
        total_input_tokens=total_input_tokens,
        output_tokens_availability=output_availability,
        total_output_tokens=total_output_tokens,
        cost_availability=cost_availability,
        total_actual_cost=total_actual_cost,
        call_count=0 if terminal and telemetry == "UNAVAILABLE" else review_count,
        retry_count=0,
        tier_count=0 if terminal and telemetry == "UNAVAILABLE" else review_count,
        typed_review_ids=review_ids,
        compared_at=compared_at,
        reason_codes=("AGGREGATE_FIXTURE",),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


def _coverage(**overrides) -> ShadowAggregateCoveragePlanV1:
    values = _coverage_values()
    values.update(overrides)
    return ShadowAggregateCoveragePlanV1(**values)


def _coverage_values() -> dict[str, object]:
    return {
        "schema_version": "phase11-shadow-aggregate-coverage-plan-v1",
        "coverage_plan_id": None,
        "minimum_total_observations": 8,
        "minimum_comparable_observations": 8,
        "minimum_clean_treatments": 4,
        "minimum_l0": 1,
        "minimum_l1": 1,
        "minimum_direct_l2": 1,
        "minimum_l1_to_l2": 1,
        "minimum_terminal_treatments": 4,
        "reason_codes": ("PREDECLARED_COVERAGE",),
    }


def _observation_set(
    observations: tuple[ShadowComparativeObservationV1, ...],
    **overrides,
) -> ShadowComparativeObservationSetV1:
    values = {
        "schema_version": "phase11-shadow-comparative-observation-set-v1",
        "observation_set_id": None,
        "observations": observations,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
        "reason_codes": ("IMMUTABLE_OBSERVATION_SET",),
    }
    values.update(overrides)
    return ShadowComparativeObservationSetV1(**values)


def _plan(
    observations: tuple[ShadowComparativeObservationV1, ...],
    **overrides,
) -> ShadowAggregateComparativePlanV1:
    values = {
        "schema_version": "phase11-shadow-aggregate-comparative-plan-v1",
        "aggregate_plan_id": None,
        "observation_set": _observation_set(observations),
        "coverage_plan": _coverage(),
        "generated_at": UTC_NOW,
        "aggregation_scope": ShadowAggregationScopeV1.OBSERVATION_SET,
        "reason_codes": ("EVENT_LEVEL_OBSERVATIONS_ONLY",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowAggregateComparativePlanV1(**values)


def _mixed_observations() -> tuple[ShadowComparativeObservationV1, ...]:
    return (
        _observation(1, route="L0"),
        _observation(
            2,
            route="L1",
            control_decision="ALLOW",
            treatment_decision="REQUIRE_NEWS_CAUTION",
            decision_delta=ControlTreatmentDecisionDeltaV1.TREATMENT_MORE_RESTRICTIVE,
            disagreement=StructuredProviderDisagreementV1.UNANIMOUS,
        ),
        _observation(
            3,
            route="L2",
            control_decision="HOLD",
            treatment_decision="ALLOW_NEWS_ELIGIBILITY",
            decision_delta=ControlTreatmentDecisionDeltaV1.TREATMENT_LESS_RESTRICTIVE,
            disagreement=StructuredProviderDisagreementV1.PARTIAL_DISAGREEMENT,
            telemetry="PARTIAL",
        ),
        _observation(
            4,
            route="L1_TO_L2",
            control_decision="HOLD",
            treatment_decision="REQUIRE_NEWS_CAUTION",
            decision_delta=ControlTreatmentDecisionDeltaV1.NO_CHANGE,
            disagreement=StructuredProviderDisagreementV1.UNRESOLVED,
            unresolved_ambiguity=True,
        ),
        _observation(
            5,
            route="L0",
            terminal_status=ShadowTerminalRecordStatusV1.DENIED,
            telemetry="UNAVAILABLE",
        ),
        _observation(
            6,
            route="L1",
            terminal_status=ShadowTerminalRecordStatusV1.FAILED_CLOSED,
        ),
        _observation(
            7,
            route="L2",
            terminal_status=ShadowTerminalRecordStatusV1.PARTIAL_EVIDENCE,
        ),
        _observation(
            8,
            route="L1_TO_L2",
            terminal_status=(
                ShadowTerminalRecordStatusV1.RECONCILIATION_REQUIRED
            ),
        ),
    )


def test_coverage_plan_is_closed_deterministic_and_evidence_only():
    first = _coverage()
    second = _coverage()
    assert first.identity == second.identity
    assert first.minimum_l1_to_l2 == 1
    assert first.minimum_terminal_treatments == 4
    with pytest.raises(ShadowComparativeAggregationValidationError):
        _coverage(minimum_l0=-1)
    unknown_fields = _coverage_values()
    unknown_fields["promotion_authority"] = "FORBIDDEN"
    with pytest.raises(ShadowComparativeAggregationValidationError):
        ShadowAggregateCoveragePlanV1(**unknown_fields)


def test_direct_observation_fixture_matrix_is_complete_and_immutable():
    observations = (
        _observation(
            9,
            treatment_decision="DENY_NEWS_ELIGIBILITY",
            decision_delta=ControlTreatmentDecisionDeltaV1.TREATMENT_MORE_RESTRICTIVE,
            disagreement=StructuredProviderDisagreementV1.COMPLETE_DISAGREEMENT,
        ),
        _observation(
            10,
            treatment_decision="FAIL_CLOSED",
            decision_delta=ControlTreatmentDecisionDeltaV1.CONTROL_ONLY_DECISION,
        ),
        _observation(
            11,
            control_decision="HOLD",
            treatment_decision="REQUIRE_NEWS_CAUTION",
            decision_delta=ControlTreatmentDecisionDeltaV1.NOT_COMPARABLE,
        ),
        _observation(
            12,
            control_decision="ALLOW",
            treatment_decision="ALLOW_NEWS_ELIGIBILITY",
            decision_delta=ControlTreatmentDecisionDeltaV1.NO_CHANGE,
        ),
    )
    assert {item.decision_delta for item in observations} == {
        ControlTreatmentDecisionDeltaV1.CONTROL_ONLY_DECISION,
        ControlTreatmentDecisionDeltaV1.NOT_COMPARABLE,
        ControlTreatmentDecisionDeltaV1.NO_CHANGE,
    }
    assert observations[0].structured_disagreement is (
        StructuredProviderDisagreementV1.COMPLETE_DISAGREEMENT
    )
    assert {
        item.treatment_decision for item in _mixed_observations() + observations
    } >= {
        "ALLOW_NEWS_ELIGIBILITY",
        "REQUIRE_NEWS_CAUTION",
        "DENY_NEWS_ELIGIBILITY",
        "FAIL_CLOSED",
    }
    assert all(item.locked_baseline_commit == LOCKED_PHASE09_BASELINE for item in observations)
    with pytest.raises(Exception):
        observations[0].candidate_id = "mutated"  # type: ignore[misc]


def test_observation_set_binds_direct_baseline_status_and_order_independence():
    observations = _mixed_observations()
    forward = _observation_set(observations)
    reverse = _observation_set(tuple(reversed(observations)))
    assert forward.identity == reverse.identity
    assert forward.locked_baseline_commit == LOCKED_PHASE09_BASELINE
    assert tuple(item.observation_id for item in forward.observations) == tuple(
        sorted(item.observation_id for item in observations)
    )
    assert {
        item.terminal_status
        for item in forward.observations
        if item.terminal_status is not None
    } == set(ShadowTerminalRecordStatusV1)
    assert all(
        item.locked_baseline_commit == LOCKED_PHASE09_BASELINE
        for item in forward.observations
    )


def test_observation_set_rejects_duplicate_and_window_incompatible_evidence():
    observation = _observation(1)
    with pytest.raises(ShadowComparativeAggregationValidationError):
        _observation_set((observation, observation))
    duplicate_key = _observation(
        2,
        candidate_id=observation.candidate_id,
        event_id=observation.event_id,
    )
    with pytest.raises(ShadowComparativeAggregationValidationError):
        _observation_set((observation, duplicate_key))
    outside_window = _observation(
        3,
        compared_at=datetime(2026, 7, 17, 0, 5, tzinfo=UTC),
    )
    with pytest.raises(ShadowComparativeAggregationValidationError):
        _observation_set((outside_window,))
    foreign_baseline_values = {
        name: getattr(observation, name) for name in observation.__slots__
    }
    foreign_baseline_values["locked_baseline_commit"] = "b" * 40
    with pytest.raises(ShadowComparativeEvaluationValidationError):
        ShadowComparativeObservationV1(**foreign_baseline_values)


def test_aggregate_report_counts_distributions_rates_and_coverage():
    report = ShadowComparativeAggregatorV1().aggregate(
        _plan(_mixed_observations())
    )
    assert type(report) is ShadowAggregateComparativeReportV1
    assert report.total_observation_count == 8
    assert report.comparable_observation_count == 8
    assert report.clean_treatment_count == 4
    assert report.terminal_treatment_count == 4
    assert report.route_counts == {
        "L0": 2,
        "L1": 2,
        "L2": 2,
        "L1_TO_L2": 2,
    }
    assert report.direct_l2_count == 2
    assert report.l1_to_l2_count == 2
    assert report.terminal_status_counts == {
        "DENIED": 1,
        "FAILED_CLOSED": 1,
        "PARTIAL_EVIDENCE": 1,
        "RECONCILIATION_REQUIRED": 1,
    }
    assert report.decision_delta_counts[
        ControlTreatmentDecisionDeltaV1.TREATMENT_UNAVAILABLE
    ] == 4
    assert report.unresolved_ambiguity_count == 1
    assert report.comparability_rate.numerator == 8
    assert report.comparability_rate.denominator == 8
    assert report.latency_summary.availability is AggregateMetricAvailabilityV1.PARTIAL
    assert report.latency_summary.available_observation_count == 7
    assert report.latency_summary.unavailable_observation_count == 1
    assert report.cost_summary.available_observation_count == 6
    assert report.cost_summary.unavailable_observation_count == 2
    assert report.cost_summary.total == Decimal("0.28")
    assert report.cost_summary.mean == Decimal("0.0466666667")
    assert all(
        item.status is ShadowAggregateCoverageStatusV1.MET
        for item in report.coverage_results
    )
    assert report.production_effect == "NONE"
    assert report.zero_production_effect_proof == "PROVEN_NONE"


def test_aggregate_report_preserves_unavailable_metrics_and_unmet_coverage():
    observations = _mixed_observations()[:1]
    report = ShadowComparativeAggregatorV1().aggregate(
        _plan(
            observations,
            coverage_plan=_coverage(
                minimum_total_observations=2,
                minimum_comparable_observations=2,
            ),
        )
    )
    assert report.coverage_results_by_target["TOTAL_OBSERVATIONS"].status is (
        ShadowAggregateCoverageStatusV1.NOT_MET
    )
    assert report.cost_summary.availability is AggregateMetricAvailabilityV1.COMPLETE
    unavailable = ShadowComparativeAggregatorV1().aggregate(
        _plan((_mixed_observations()[4],))
    )
    assert unavailable.latency_summary.availability is (
        AggregateMetricAvailabilityV1.UNAVAILABLE
    )
    assert unavailable.latency_summary.total is None
    assert unavailable.cost_summary.total is None


def test_aggregate_identities_converge_and_material_evidence_diverges():
    observations = _mixed_observations()
    first = ShadowComparativeAggregatorV1().aggregate(_plan(observations))
    second = ShadowComparativeAggregatorV1().aggregate(
        _plan(tuple(reversed(observations)))
    )
    changed = ShadowComparativeAggregatorV1().aggregate(
        _plan(observations, coverage_plan=_coverage(minimum_l0=2))
    )
    assert first.identity == second.identity
    assert first.observation_set_id == second.observation_set_id
    assert first.identity != changed.identity
    assert lowercase_sha256({"observation_ids": sorted(item.identity for item in observations)}) == _sha({"observation_ids": sorted(item.identity for item in observations)})
    assert canonical_json_bytes({"cost": Decimal("1.00")}) == b'{"cost":"1"}'


def test_aggregate_module_static_boundaries_are_side_effect_free():
    source = Path(__file__).parents[1] / "engine" / "phase_11_shadow_comparative_aggregate_v1.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket",
        "subprocess", "threading", "multiprocessing", "concurrent", "asyncio",
        "keyring", "boto3", "telegram", "ccxt", "ShadowComparativeEvaluatorV1",
        "ShadowAdjudicationFinalizerV1", "finalize", "compare", "requests",
        "sqlite", "replay", "production", "publish", "persist",
    }
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    assert not (forbidden & imported)
    assert not (forbidden & names)
    assert not ({"finalize", "compare"} & attributes)
