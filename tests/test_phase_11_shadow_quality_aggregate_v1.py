"""RED contract for deterministic aggregation of quality observations only."""

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
from engine.phase_11_shadow_quality_aggregate_v1 import (
    QualityAggregateRateAvailabilityV1,
    QualityAggregationScopeV1,
    QualityCoverageStatusV1,
    ShadowAggregateQualityPlanV1,
    ShadowAggregateQualityReportV1,
    ShadowQualityAggregationValidationError,
    ShadowQualityAggregatorV1,
    ShadowQualityCoveragePlanV1,
    ShadowQualityCoverageResultV1,
    ShadowQualityObservationSetV1,
    ShadowQualityRateEvidenceV1,
    canonical_json_bytes,
    lowercase_sha256,
)


EVALUATED_AT = datetime(2026, 7, 17, 0, 12, tzinfo=UTC)
WINDOW_START = datetime(2026, 7, 17, 0, 10, tzinfo=UTC)
WINDOW_END = EVALUATED_AT


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


def _quality_observation(
    index: int,
    *,
    route: str = "L0",
    label_usable: bool = True,
    materiality: MaterialityQualityResultV1 = (
        MaterialityQualityResultV1.CORRECT_MATERIAL_EVENT_HANDLING
    ),
    mapping: MappingQualityResultV1 = MappingQualityResultV1.CORRECT,
    control: ControlQualityResultV1 = ControlQualityResultV1.CORRECT,
    treatment: TreatmentQualityResultV1 = TreatmentQualityResultV1.CORRECT,
    false_block: FalseBlockClassificationV1 = (
        FalseBlockClassificationV1.NOT_FALSE_BLOCK
    ),
    missed_event: MissedMaterialEventClassificationV1 = (
        MissedMaterialEventClassificationV1.NOT_MISSED
    ),
    escalation: EscalationNecessityV1 | None = None,
    terminal_status: ShadowTerminalRecordStatusV1 | None = None,
    candidate_id: str | None = None,
    event_id: str | None = None,
    label_id: str | None = None,
    evaluated_at: datetime = EVALUATED_AT,
) -> ShadowQualityObservationV1:
    """Directly construct already-created immutable quality evidence."""

    if escalation is None:
        escalation = {
            "L0": EscalationNecessityV1.NOT_ESCALATED,
            "L1": EscalationNecessityV1.INDETERMINATE,
            "L2": EscalationNecessityV1.INDETERMINATE,
            "L1_TO_L2": EscalationNecessityV1.UNNECESSARY,
        }[route]
    terminal = terminal_status is not None
    if terminal:
        treatment = TreatmentQualityResultV1.UNAVAILABLE
        treatment_decision = None
        availability = TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE
        comparability = QualityComparabilityV1.TERMINAL_TREATMENT_UNAVAILABLE
    else:
        treatment_decision = {
            TreatmentQualityResultV1.CORRECT: "ALLOW_NEWS_ELIGIBILITY",
            TreatmentQualityResultV1.TOO_RESTRICTIVE: "DENY_NEWS_ELIGIBILITY",
            TreatmentQualityResultV1.TOO_PERMISSIVE: "ALLOW_NEWS_ELIGIBILITY",
            TreatmentQualityResultV1.INSUFFICIENT_LABEL: "ALLOW_NEWS_ELIGIBILITY",
            TreatmentQualityResultV1.NOT_COMPARABLE: "ALLOW_NEWS_ELIGIBILITY",
            TreatmentQualityResultV1.UNAVAILABLE: "ALLOW_NEWS_ELIGIBILITY",
        }[treatment]
        availability = TreatmentAvailabilityV1.AVAILABLE
        comparability = (
            QualityComparabilityV1.INSUFFICIENT_LABEL
            if not label_usable
            else QualityComparabilityV1.COMPARABLE
        )
    return ShadowQualityObservationV1(
        schema_version="phase11-shadow-quality-observation-v1",
        quality_observation_id=None,
        quality_plan_id=_sha(("quality-plan", index)),
        comparative_observation_id=_sha(("comparative-observation", index)),
        label_id=label_id or _sha(("human-label", index)),
        candidate_id=candidate_id or f"candidate-{index}",
        event_id=event_id or f"event-{index}",
        entity_id="BTC",
        locked_baseline_commit=LOCKED_PHASE09_BASELINE,
        original_treatment_route=route,
        treatment_availability=availability,
        control_decision="ALLOW",
        treatment_decision=treatment_decision,
        terminal_status=terminal_status,
        label_usable=label_usable,
        event_materiality=(
            EventMaterialityV1.INSUFFICIENT_EVIDENCE
            if not label_usable
            else (
                EventMaterialityV1.NON_MATERIAL
                if materiality
                is MaterialityQualityResultV1.CORRECT_NON_MATERIAL_SUPPRESSION
                else EventMaterialityV1.MATERIAL
            )
        ),
        mapping_correctness={
            MappingQualityResultV1.CORRECT: EntityMappingCorrectnessV1.CORRECT,
            MappingQualityResultV1.INCORRECT: EntityMappingCorrectnessV1.INCORRECT,
            MappingQualityResultV1.UNAVAILABLE: EntityMappingCorrectnessV1.UNAVAILABLE,
            MappingQualityResultV1.NOT_APPLICABLE: EntityMappingCorrectnessV1.UNAVAILABLE,
        }[mapping],
        expected_handling=(
            ExpectedHandlingV1.INSUFFICIENT_EVIDENCE
            if not label_usable
            else ExpectedHandlingV1.ALLOW
        ),
        quality_comparability=comparability,
        materiality_quality=materiality,
        mapping_quality=mapping,
        control_quality=control,
        treatment_quality=treatment,
        false_block=false_block,
        missed_material_event=missed_event,
        escalation_necessity=escalation,
        evaluated_at=evaluated_at,
        reason_codes=("QUALITY_AGGREGATE_FIXTURE",),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


def _coverage(**overrides) -> ShadowQualityCoveragePlanV1:
    values = {
        "schema_version": "phase11-shadow-quality-coverage-plan-v1",
        "coverage_plan_id": None,
        "minimum_total_quality_observations": 10,
        "minimum_usable_labels": 9,
        "minimum_material_events": 8,
        "minimum_non_material_events": 1,
        "minimum_clean_treatments": 6,
        "minimum_terminal_treatments": 4,
        "minimum_l0": 1,
        "minimum_l1": 1,
        "minimum_direct_l2": 1,
        "minimum_l1_to_l2": 1,
        "reason_codes": ("PREDECLARED_QUALITY_COVERAGE",),
    }
    values.update(overrides)
    return ShadowQualityCoveragePlanV1(**values)


def _observation_set(
    observations: tuple[ShadowQualityObservationV1, ...],
    **overrides,
) -> ShadowQualityObservationSetV1:
    values = {
        "schema_version": "phase11-shadow-quality-observation-set-v1",
        "quality_observation_set_id": None,
        "observations": observations,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
        "reason_codes": ("IMMUTABLE_QUALITY_OBSERVATION_SET",),
    }
    values.update(overrides)
    return ShadowQualityObservationSetV1(**values)


def _plan(
    observations: tuple[ShadowQualityObservationV1, ...],
    **overrides,
) -> ShadowAggregateQualityPlanV1:
    values = {
        "schema_version": "phase11-shadow-aggregate-quality-plan-v1",
        "aggregate_quality_plan_id": None,
        "quality_observation_set": _observation_set(observations),
        "coverage_plan": _coverage(),
        "generated_at": EVALUATED_AT,
        "aggregation_scope": QualityAggregationScopeV1.QUALITY_OBSERVATION_SET,
        "reason_codes": ("QUALITY_OBSERVATIONS_ONLY",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowAggregateQualityPlanV1(**values)


def _mixed_quality_observations() -> tuple[ShadowQualityObservationV1, ...]:
    return (
        _quality_observation(1, route="L0"),
        _quality_observation(
            2,
            route="L1",
            materiality=MaterialityQualityResultV1.FALSE_BLOCK,
            mapping=MappingQualityResultV1.INCORRECT,
            control=ControlQualityResultV1.TOO_RESTRICTIVE,
            treatment=TreatmentQualityResultV1.TOO_RESTRICTIVE,
            false_block=FalseBlockClassificationV1.FALSE_BLOCK,
        ),
        _quality_observation(
            3,
            route="L2",
            materiality=MaterialityQualityResultV1.MISSED_MATERIAL_EVENT,
            mapping=MappingQualityResultV1.UNAVAILABLE,
            control=ControlQualityResultV1.TOO_PERMISSIVE,
            treatment=TreatmentQualityResultV1.TOO_PERMISSIVE,
            missed_event=MissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT,
        ),
        _quality_observation(
            4,
            route="L1_TO_L2",
            materiality=MaterialityQualityResultV1.CORRECT_NON_MATERIAL_SUPPRESSION,
            false_block=FalseBlockClassificationV1.NOT_APPLICABLE,
            missed_event=MissedMaterialEventClassificationV1.NOT_APPLICABLE,
            escalation=EscalationNecessityV1.NECESSARY,
        ),
        _quality_observation(5, route="L1_TO_L2"),
        _quality_observation(
            6,
            label_usable=False,
            materiality=MaterialityQualityResultV1.INSUFFICIENT_LABEL,
            mapping=MappingQualityResultV1.UNAVAILABLE,
            control=ControlQualityResultV1.INSUFFICIENT_LABEL,
            treatment=TreatmentQualityResultV1.INSUFFICIENT_LABEL,
            false_block=FalseBlockClassificationV1.INSUFFICIENT_LABEL,
            missed_event=MissedMaterialEventClassificationV1.INSUFFICIENT_LABEL,
            escalation=EscalationNecessityV1.INSUFFICIENT_LABEL,
        ),
        _quality_observation(7, terminal_status=ShadowTerminalRecordStatusV1.DENIED),
        _quality_observation(8, route="L1", terminal_status=ShadowTerminalRecordStatusV1.FAILED_CLOSED),
        _quality_observation(9, route="L2", terminal_status=ShadowTerminalRecordStatusV1.PARTIAL_EVIDENCE),
        _quality_observation(10, route="L1_TO_L2", terminal_status=ShadowTerminalRecordStatusV1.RECONCILIATION_REQUIRED),
    )


def test_quality_coverage_plan_is_closed_and_deterministic():
    first = _coverage()
    assert first.identity == _coverage().identity
    assert first.minimum_terminal_treatments == 4
    with pytest.raises(ShadowQualityAggregationValidationError):
        _coverage(minimum_l0=-1)
    with pytest.raises(ShadowQualityAggregationValidationError):
        _coverage(minimum_l0=True)
    values = dict(first.__dict__) if hasattr(first, "__dict__") else {
        name: getattr(first, name) for name in first.__slots__
    }
    values["promotion_authority"] = "FORBIDDEN"
    with pytest.raises(ShadowQualityAggregationValidationError):
        ShadowQualityCoveragePlanV1(**values)


def test_direct_quality_fixture_matrix_is_complete_and_immutable():
    observations = _mixed_quality_observations()
    assert len(observations) == 10
    assert {item.original_treatment_route for item in observations} == {
        "L0", "L1", "L2", "L1_TO_L2"
    }
    assert {item.terminal_status for item in observations if item.terminal_status} == set(
        ShadowTerminalRecordStatusV1
    )
    assert {item.false_block for item in observations} == set(
        FalseBlockClassificationV1
    )
    assert {item.missed_material_event for item in observations} == set(
        MissedMaterialEventClassificationV1
    )
    assert {item.escalation_necessity for item in observations} == set(
        EscalationNecessityV1
    )
    with pytest.raises(Exception):
        observations[0].candidate_id = "mutated"  # type: ignore[misc]


def test_quality_observation_set_binds_baseline_window_order_and_duplicates():
    observations = _mixed_quality_observations()
    forward = _observation_set(observations)
    reverse = _observation_set(tuple(reversed(observations)))
    assert forward.identity == reverse.identity
    assert tuple(item.identity for item in forward.observations) == tuple(
        sorted(item.identity for item in observations)
    )
    assert forward.locked_baseline_commit == LOCKED_PHASE09_BASELINE
    with pytest.raises(ShadowQualityAggregationValidationError):
        _observation_set((observations[0], observations[0]))
    duplicate_key = _quality_observation(
        11,
        candidate_id=observations[0].candidate_id,
        event_id=observations[0].event_id,
        label_id=observations[0].label_id,
    )
    with pytest.raises(ShadowQualityAggregationValidationError):
        _observation_set((observations[0], duplicate_key))
    with pytest.raises(ShadowQualityAggregationValidationError):
        _observation_set((
            _quality_observation(
                12,
                evaluated_at=datetime(2026, 7, 17, 0, 9, tzinfo=UTC),
            ),
        ))


def test_quality_observation_set_rejects_foreign_baseline_without_reopening_children():
    observation = _quality_observation(1)
    values = {name: getattr(observation, name) for name in observation.__slots__}
    values["locked_baseline_commit"] = "b" * 40
    with pytest.raises(Exception):
        ShadowQualityObservationV1(**values)


def test_aggregate_quality_report_counts_distributions_rates_and_coverage():
    report = ShadowQualityAggregatorV1().aggregate(_plan(_mixed_quality_observations()))
    assert type(report) is ShadowAggregateQualityReportV1
    assert report.total_quality_observation_count == 10
    assert report.usable_label_count == 9
    assert report.insufficient_label_count == 1
    assert report.clean_treatment_count == 6
    assert report.terminal_treatment_count == 4
    assert report.route_counts == {"L0": 3, "L1": 2, "L2": 2, "L1_TO_L2": 3}
    assert report.materiality_quality_counts == {
        MaterialityQualityResultV1.CORRECT_MATERIAL_EVENT_HANDLING: 6,
        MaterialityQualityResultV1.FALSE_BLOCK: 1,
        MaterialityQualityResultV1.MISSED_MATERIAL_EVENT: 1,
        MaterialityQualityResultV1.CORRECT_NON_MATERIAL_SUPPRESSION: 1,
        MaterialityQualityResultV1.INSUFFICIENT_LABEL: 1,
        MaterialityQualityResultV1.NOT_APPLICABLE: 0,
    }
    assert report.mapping_quality_counts == {
        MappingQualityResultV1.CORRECT: 7,
        MappingQualityResultV1.INCORRECT: 1,
        MappingQualityResultV1.UNAVAILABLE: 2,
        MappingQualityResultV1.NOT_APPLICABLE: 0,
    }
    assert report.control_quality_counts[ControlQualityResultV1.CORRECT] == 7
    assert report.control_quality_counts[
        ControlQualityResultV1.TOO_RESTRICTIVE
    ] == 1
    assert report.control_quality_counts[
        ControlQualityResultV1.TOO_PERMISSIVE
    ] == 1
    assert report.control_quality_counts[
        ControlQualityResultV1.INSUFFICIENT_LABEL
    ] == 1
    assert report.treatment_quality_counts[TreatmentQualityResultV1.CORRECT] == 3
    assert report.treatment_quality_counts[
        TreatmentQualityResultV1.TOO_RESTRICTIVE
    ] == 1
    assert report.treatment_quality_counts[
        TreatmentQualityResultV1.TOO_PERMISSIVE
    ] == 1
    assert report.treatment_quality_counts[TreatmentQualityResultV1.UNAVAILABLE] == 4
    assert report.treatment_quality_counts[
        TreatmentQualityResultV1.INSUFFICIENT_LABEL
    ] == 1
    assert report.false_block_counts[FalseBlockClassificationV1.FALSE_BLOCK] == 1
    assert report.missed_event_counts[
        MissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
    ] == 1
    assert report.escalation_counts[EscalationNecessityV1.UNNECESSARY] == 2
    assert report.terminal_status_counts == {
        "DENIED": 1,
        "FAILED_CLOSED": 1,
        "PARTIAL_EVIDENCE": 1,
        "RECONCILIATION_REQUIRED": 1,
    }
    assert report.false_block_rate == ShadowQualityRateEvidenceV1(
        numerator=1,
        denominator=8,
        availability=QualityAggregateRateAvailabilityV1.AVAILABLE,
        value=Decimal("0.1250000000"),
    )
    assert report.missed_material_event_rate.numerator == 1
    assert report.missed_material_event_rate.denominator == 8
    assert report.usable_label_coverage_rate == ShadowQualityRateEvidenceV1(
        numerator=9,
        denominator=10,
        availability=QualityAggregateRateAvailabilityV1.AVAILABLE,
        value=Decimal("0.9000000000"),
    )
    assert report.materiality_handling_correctness_rate.numerator == 7
    assert report.materiality_handling_correctness_rate.denominator == 9
    assert report.mapping_correctness_rate.denominator == 8
    assert report.mapping_correctness_rate.numerator == 7
    assert report.control_correctness_rate.denominator == 9
    assert report.control_correctness_rate.numerator == 7
    assert report.treatment_correctness_rate.denominator == 5
    assert report.treatment_correctness_rate.numerator == 3
    assert report.terminal_treatment_unavailable_rate == ShadowQualityRateEvidenceV1(
        numerator=4,
        denominator=10,
        availability=QualityAggregateRateAvailabilityV1.AVAILABLE,
        value=Decimal("0.4000000000"),
    )
    assert report.unnecessary_escalation_rate == ShadowQualityRateEvidenceV1(
        numerator=2,
        denominator=3,
        availability=QualityAggregateRateAvailabilityV1.AVAILABLE,
        value=Decimal("0.6666666667"),
    )
    assert all(item.status is QualityCoverageStatusV1.MET for item in report.coverage_results)
    assert report.production_effect == "NONE"
    assert report.zero_production_effect_proof == "PROVEN_NONE"


def test_quality_rate_denominators_exclude_insufficient_unavailable_and_not_applicable():
    insufficient = _quality_observation(
        20,
        label_usable=False,
        materiality=MaterialityQualityResultV1.INSUFFICIENT_LABEL,
        mapping=MappingQualityResultV1.UNAVAILABLE,
        control=ControlQualityResultV1.INSUFFICIENT_LABEL,
        treatment=TreatmentQualityResultV1.INSUFFICIENT_LABEL,
        false_block=FalseBlockClassificationV1.INSUFFICIENT_LABEL,
        missed_event=MissedMaterialEventClassificationV1.INSUFFICIENT_LABEL,
        escalation=EscalationNecessityV1.INSUFFICIENT_LABEL,
    )
    report = ShadowQualityAggregatorV1().aggregate(
        _plan((insufficient,), coverage_plan=_coverage(minimum_total_quality_observations=2))
    )
    assert report.false_block_rate.availability is QualityAggregateRateAvailabilityV1.UNAVAILABLE
    assert report.false_block_rate.value is None
    assert report.mapping_correctness_rate.denominator == 0
    assert report.treatment_correctness_rate.denominator == 0
    assert report.coverage_results_by_target["TOTAL_QUALITY_OBSERVATIONS"].status is (
        QualityCoverageStatusV1.NOT_MET
    )


def test_quality_aggregate_identities_converge_diverge_and_canonical_helpers():
    observations = _mixed_quality_observations()
    first = ShadowQualityAggregatorV1().aggregate(_plan(observations))
    second = ShadowQualityAggregatorV1().aggregate(_plan(tuple(reversed(observations))))
    changed = ShadowQualityAggregatorV1().aggregate(
        _plan(observations, coverage_plan=_coverage(minimum_l0=4))
    )
    assert first.identity == second.identity
    assert first.quality_observation_set_id == second.quality_observation_set_id
    assert first.identity != changed.identity
    assert canonical_json_bytes({"rate": Decimal("1.00")}) == b'{"rate":"1"}'
    assert lowercase_sha256({"quality_ids": sorted(item.identity for item in observations)}) == _sha(
        {"quality_ids": sorted(item.identity for item in observations)}
    )


def test_quality_aggregate_module_static_boundaries_are_side_effect_free():
    source = Path(__file__).parents[1] / "engine" / "phase_11_shadow_quality_aggregate_v1.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket",
        "subprocess", "threading", "multiprocessing", "concurrent", "asyncio",
        "keyring", "boto3", "telegram", "ccxt", "ShadowQualityEvaluatorV1",
        "ShadowComparativeEvaluatorV1", "ShadowComparativeAggregatorV1",
        "ShadowAdjudicationFinalizerV1", "evaluate", "compare", "finalize",
        "sqlite", "replay", "production", "publish", "persist", "annotation",
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
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    float_literals = [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]
    assert not (forbidden & imported)
    assert not (forbidden & names)
    assert not ({"evaluate", "compare", "finalize"} & attributes)
    assert not float_literals
