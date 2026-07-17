"""RED contract for immutable human-label evidence and event quality.

The implementation is deliberately absent. Fixtures construct completed
comparative observations and independent label evidence only.
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
from engine.phase_11_shadow_quality_evaluator_v1 import (
    ControlQualityResultV1,
    EntityMappingCorrectnessV1,
    EscalationNecessityV1,
    EventMaterialityV1,
    ExpectedHandlingV1,
    FalseBlockClassificationV1,
    LabelReviewStatusV1,
    MappingQualityResultV1,
    MaterialityQualityResultV1,
    MissedMaterialEventClassificationV1,
    QualityComparabilityV1,
    ShadowHumanLabelEvidenceV1,
    ShadowQualityEvaluationPlanV1,
    ShadowQualityEvaluationValidationError,
    ShadowQualityEvaluatorV1,
    ShadowQualityObservationV1,
    TreatmentQualityResultV1,
    canonical_json_bytes,
    lowercase_sha256,
)


OBSERVED_AT = datetime(2026, 7, 17, 0, 10, tzinfo=UTC)
LABELED_AT = datetime(2026, 7, 17, 0, 11, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 7, 17, 0, 12, tzinfo=UTC)


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
    terminal_status: ShadowTerminalRecordStatusV1 | None = None,
    disagreement: StructuredProviderDisagreementV1 = (
        StructuredProviderDisagreementV1.NOT_APPLICABLE
    ),
    unresolved_ambiguity: bool = False,
    candidate_id: str | None = None,
    event_id: str | None = None,
) -> ShadowComparativeObservationV1:
    """Direct, already-created immutable event-level evidence."""

    terminal = terminal_status is not None
    review_count = {"L0": 1, "L1": 2, "L2": 2, "L1_TO_L2": 3}[route]
    if terminal:
        treatment_decision = None
        canonical_route = None
        delta = ControlTreatmentDecisionDeltaV1.TREATMENT_UNAVAILABLE
        disagreement = StructuredProviderDisagreementV1.UNAVAILABLE
        terminal_failure = "FIXTURE_TERMINAL_FAILURE"
        terminal_reconciliation = (
            "RECONCILIATION_REQUIRED"
            if terminal_status is ShadowTerminalRecordStatusV1.RECONCILIATION_REQUIRED
            else "RESOLVED"
        )
    else:
        canonical_route = "L2" if route == "L1_TO_L2" else route
        delta = ControlTreatmentDecisionDeltaV1.NO_CHANGE
        terminal_failure = None
        terminal_reconciliation = None
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
        decision_delta=delta,
        structured_disagreement=disagreement,
        unresolved_ambiguity=unresolved_ambiguity,
        terminal_status=terminal_status,
        terminal_failure=terminal_failure,
        terminal_reconciliation=terminal_reconciliation,
        latency_availability=MetricAvailabilityV1.AVAILABLE,
        total_latency_ms=100 * index,
        input_tokens_availability=MetricAvailabilityV1.AVAILABLE,
        total_input_tokens=10 * index,
        output_tokens_availability=MetricAvailabilityV1.AVAILABLE,
        total_output_tokens=5 * index,
        cost_availability=MetricAvailabilityV1.AVAILABLE,
        total_actual_cost=Decimal("0.01") * index,
        call_count=review_count,
        retry_count=0,
        tier_count=review_count,
        typed_review_ids=tuple(
            _sha(("typed-review", index, item)) for item in range(review_count)
        ),
        compared_at=OBSERVED_AT,
        reason_codes=("QUALITY_FIXTURE",),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


def _label(
    index: int,
    *,
    candidate_id: str | None = None,
    event_id: str | None = None,
    entity_id: str = "BTC",
    materiality: EventMaterialityV1 = EventMaterialityV1.MATERIAL,
    mapping: EntityMappingCorrectnessV1 = EntityMappingCorrectnessV1.CORRECT,
    expected_handling: ExpectedHandlingV1 = ExpectedHandlingV1.ALLOW,
    review_status: LabelReviewStatusV1 = LabelReviewStatusV1.REVIEWED,
    labeled_at: datetime = LABELED_AT,
    reason_codes: tuple[str, ...] = ("INDEPENDENT_EVENT_REVIEW",),
) -> ShadowHumanLabelEvidenceV1:
    """Independent label truth; it does not read comparative evidence."""

    return ShadowHumanLabelEvidenceV1(
        schema_version="phase11-shadow-human-label-evidence-v1",
        label_id=None,
        candidate_id=candidate_id or f"candidate-{index}",
        event_id=event_id or f"event-{index}",
        entity_id=entity_id,
        event_materiality=materiality,
        mapping_correctness=mapping,
        expected_handling=expected_handling,
        review_status=review_status,
        provenance_category="INDEPENDENT_HUMAN_REVIEW",
        reviewer_reference=f"review-batch-20260717-{index}",
        labeled_at=labeled_at,
        reason_codes=reason_codes,
    )


def _plan(
    observation: ShadowComparativeObservationV1,
    label: ShadowHumanLabelEvidenceV1,
    **overrides,
) -> ShadowQualityEvaluationPlanV1:
    values = {
        "schema_version": "phase11-shadow-quality-evaluation-plan-v1",
        "quality_plan_id": None,
        "comparative_observation": observation,
        "human_label": label,
        "evaluated_at": EVALUATED_AT,
        "quality_scope": "EVENT_LEVEL",
        "reason_codes": ("INDEPENDENT_LABEL_ONLY",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowQualityEvaluationPlanV1(**values)


def test_human_label_is_closed_independent_and_canonically_identified():
    first = _label(1)
    assert first.identity == _label(1).identity
    assert first.candidate_id == "candidate-1"
    assert first.event_id == "event-1"
    assert first.entity_id == "BTC"
    assert first.review_status is LabelReviewStatusV1.REVIEWED
    assert first.identity != _label(
        1, materiality=EventMaterialityV1.NON_MATERIAL
    ).identity
    assert first.identity != _label(
        1, expected_handling=ExpectedHandlingV1.HOLD
    ).identity
    assert first.identity != _label(
        1, mapping=EntityMappingCorrectnessV1.INCORRECT
    ).identity
    assert first.identity != _label(
        1, review_status=LabelReviewStatusV1.INSUFFICIENT_EVIDENCE
    ).identity
    assert first.identity != _label(
        1, labeled_at=EVALUATED_AT
    ).identity
    assert first.identity != _label(
        1, reason_codes=("INDEPENDENT_EVENT_REVIEW", "SECOND_REVIEW")
    ).identity
    with pytest.raises(Exception):
        first.entity_id = "ETH"  # type: ignore[misc]
    with pytest.raises(ShadowQualityEvaluationValidationError):
        _label(1, entity_id="reviewer@example.com")
    with pytest.raises(ShadowQualityEvaluationValidationError):
        _label(1, labeled_at=datetime(2026, 7, 17, 0, 11))


def test_label_matrix_reaches_materiality_mapping_handling_and_review_states():
    labels = (
        _label(1),
        _label(
            2,
            materiality=EventMaterialityV1.NON_MATERIAL,
            expected_handling=ExpectedHandlingV1.BLOCK,
        ),
        _label(3, mapping=EntityMappingCorrectnessV1.INCORRECT),
        _label(4, expected_handling=ExpectedHandlingV1.HOLD),
        _label(
            5,
            materiality=EventMaterialityV1.INSUFFICIENT_EVIDENCE,
            mapping=EntityMappingCorrectnessV1.UNAVAILABLE,
            expected_handling=ExpectedHandlingV1.INSUFFICIENT_EVIDENCE,
            review_status=LabelReviewStatusV1.INSUFFICIENT_EVIDENCE,
        ),
        _label(6, review_status=LabelReviewStatusV1.PENDING),
    )
    assert {item.event_materiality for item in labels} == {
        EventMaterialityV1.MATERIAL,
        EventMaterialityV1.NON_MATERIAL,
        EventMaterialityV1.INSUFFICIENT_EVIDENCE,
    }
    assert {item.mapping_correctness for item in labels} >= {
        EntityMappingCorrectnessV1.CORRECT,
        EntityMappingCorrectnessV1.INCORRECT,
        EntityMappingCorrectnessV1.UNAVAILABLE,
    }
    assert {item.expected_handling for item in labels} == {
        ExpectedHandlingV1.ALLOW,
        ExpectedHandlingV1.HOLD,
        ExpectedHandlingV1.BLOCK,
        ExpectedHandlingV1.INSUFFICIENT_EVIDENCE,
    }


def test_quality_plan_requires_lineage_usable_label_and_time_ordering():
    observation = _observation(1)
    label = _label(1)
    plan = _plan(observation, label)
    assert plan.comparative_observation.identity == observation.identity
    assert plan.human_label.identity == label.identity
    with pytest.raises(ShadowQualityEvaluationValidationError):
        _plan(observation, _label(2))
    with pytest.raises(ShadowQualityEvaluationValidationError):
        _plan(observation, _label(1, event_id="other-event"))
    with pytest.raises(ShadowQualityEvaluationValidationError):
        _plan(observation, _label(1, review_status=LabelReviewStatusV1.PENDING))
    with pytest.raises(ShadowQualityEvaluationValidationError):
        _plan(
            observation,
            _label(1, labeled_at=datetime(2026, 7, 17, 0, 13, tzinfo=UTC)),
        )
    with pytest.raises(ShadowQualityEvaluationValidationError):
        _plan(
            observation,
            _label(1, labeled_at=datetime(2026, 7, 17, 0, 5, tzinfo=UTC)),
        )


def test_quality_evaluation_handles_material_correct_false_block_and_missed_event():
    correct = ShadowQualityEvaluatorV1().evaluate(_plan(_observation(1), _label(1)))
    false_block = ShadowQualityEvaluatorV1().evaluate(
        _plan(
            _observation(
                2,
                control_decision="REJECT",
                treatment_decision="DENY_NEWS_ELIGIBILITY",
            ),
            _label(2),
        )
    )
    missed = ShadowQualityEvaluatorV1().evaluate(
        _plan(
            _observation(3),
            _label(3, expected_handling=ExpectedHandlingV1.BLOCK),
        )
    )
    assert type(correct) is ShadowQualityObservationV1
    assert correct.materiality_quality is (
        MaterialityQualityResultV1.CORRECT_MATERIAL_EVENT_HANDLING
    )
    assert correct.mapping_quality is MappingQualityResultV1.CORRECT
    assert correct.control_quality is ControlQualityResultV1.CORRECT
    assert correct.treatment_quality is TreatmentQualityResultV1.CORRECT
    assert false_block.false_block is FalseBlockClassificationV1.FALSE_BLOCK
    assert false_block.control_quality is ControlQualityResultV1.TOO_RESTRICTIVE
    assert false_block.treatment_quality is TreatmentQualityResultV1.TOO_RESTRICTIVE
    assert missed.missed_material_event is (
        MissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
    )
    assert missed.control_quality is ControlQualityResultV1.TOO_PERMISSIVE
    assert missed.treatment_quality is TreatmentQualityResultV1.TOO_PERMISSIVE


def test_quality_evaluation_handles_non_material_mapping_and_insufficient_labels():
    suppressed = ShadowQualityEvaluatorV1().evaluate(
        _plan(
            _observation(
                4,
                control_decision="REJECT",
                treatment_decision="DENY_NEWS_ELIGIBILITY",
            ),
            _label(
                4,
                materiality=EventMaterialityV1.NON_MATERIAL,
                expected_handling=ExpectedHandlingV1.BLOCK,
            ),
        )
    )
    incorrect_mapping = ShadowQualityEvaluatorV1().evaluate(
        _plan(
            _observation(5),
            _label(5, mapping=EntityMappingCorrectnessV1.INCORRECT),
        )
    )
    insufficient = ShadowQualityEvaluatorV1().evaluate(
        _plan(
            _observation(6),
            _label(
                6,
                materiality=EventMaterialityV1.INSUFFICIENT_EVIDENCE,
                mapping=EntityMappingCorrectnessV1.UNAVAILABLE,
                expected_handling=ExpectedHandlingV1.INSUFFICIENT_EVIDENCE,
                review_status=LabelReviewStatusV1.INSUFFICIENT_EVIDENCE,
            ),
        )
    )
    assert suppressed.materiality_quality is (
        MaterialityQualityResultV1.CORRECT_NON_MATERIAL_SUPPRESSION
    )
    assert incorrect_mapping.mapping_quality is MappingQualityResultV1.INCORRECT
    assert insufficient.quality_comparability is (
        QualityComparabilityV1.INSUFFICIENT_LABEL
    )
    assert insufficient.false_block is FalseBlockClassificationV1.INSUFFICIENT_LABEL
    assert insufficient.missed_material_event is (
        MissedMaterialEventClassificationV1.INSUFFICIENT_LABEL
    )


def test_quality_evaluation_preserves_terminal_treatment_unavailability():
    for index, status in enumerate(ShadowTerminalRecordStatusV1, start=10):
        result = ShadowQualityEvaluatorV1().evaluate(
            _plan(_observation(index, terminal_status=status), _label(index))
        )
        assert result.treatment_quality is TreatmentQualityResultV1.UNAVAILABLE
        assert result.treatment_decision is None
        assert result.terminal_status is status
        assert result.quality_comparability is (
            QualityComparabilityV1.TERMINAL_TREATMENT_UNAVAILABLE
        )


def test_escalation_necessity_is_event_level_and_never_counterfactual():
    l0 = ShadowQualityEvaluatorV1().evaluate(
        _plan(_observation(20, route="L0"), _label(20))
    )
    necessary = ShadowQualityEvaluatorV1().evaluate(
        _plan(
            _observation(
                21,
                route="L1_TO_L2",
                disagreement=StructuredProviderDisagreementV1.UNRESOLVED,
                unresolved_ambiguity=True,
            ),
            _label(21, expected_handling=ExpectedHandlingV1.HOLD),
        )
    )
    indeterminate = ShadowQualityEvaluatorV1().evaluate(
        _plan(_observation(22, route="L2"), _label(22))
    )
    unnecessary = ShadowQualityEvaluatorV1().evaluate(
        _plan(_observation(23, route="L1_TO_L2"), _label(23))
    )
    assert l0.escalation_necessity is EscalationNecessityV1.NOT_ESCALATED
    assert necessary.escalation_necessity is EscalationNecessityV1.NECESSARY
    assert indeterminate.escalation_necessity is EscalationNecessityV1.INDETERMINATE
    assert unnecessary.escalation_necessity is EscalationNecessityV1.UNNECESSARY


def test_quality_identity_converges_diverges_and_preserves_zero_effect():
    observation = _observation(30, route="L1")
    first = ShadowQualityEvaluatorV1().evaluate(_plan(observation, _label(30)))
    second = ShadowQualityEvaluatorV1().evaluate(_plan(observation, _label(30)))
    changed = ShadowQualityEvaluatorV1().evaluate(
        _plan(observation, _label(30, expected_handling=ExpectedHandlingV1.HOLD))
    )
    assert first.identity == second.identity
    assert first.identity != changed.identity
    assert first.locked_baseline_commit == LOCKED_PHASE09_BASELINE
    assert first.production_effect == "NONE"
    assert first.zero_production_effect_proof == "PROVEN_NONE"
    assert canonical_json_bytes({"cost": Decimal("1.00")}) == b'{"cost":"1"}'
    assert lowercase_sha256({"observation": observation.identity}) == _sha(
        {"observation": observation.identity}
    )


def test_observation_fixture_routes_and_terminal_shapes_are_reachable():
    clean = tuple(
        _observation(index, route=route)
        for index, route in enumerate(("L0", "L1", "L2", "L1_TO_L2"), start=40)
    )
    terminal = tuple(
        _observation(index, terminal_status=status)
        for index, status in enumerate(ShadowTerminalRecordStatusV1, start=50)
    )
    assert {item.original_treatment_route for item in clean} == {
        "L0",
        "L1",
        "L2",
        "L1_TO_L2",
    }
    assert all(item.treatment_decision is not None for item in clean)
    assert {item.terminal_status for item in terminal} == set(
        ShadowTerminalRecordStatusV1
    )
    assert all(item.treatment_decision is None for item in terminal)
    with pytest.raises(ShadowComparativeEvaluationValidationError):
        values = {name: getattr(clean[0], name) for name in clean[0].__slots__}
        values["production_effect"] = "PUBLISHED"
        ShadowComparativeObservationV1(**values)


def test_quality_module_static_boundaries_are_side_effect_free():
    source = (
        Path(__file__).parents[1]
        / "engine"
        / "phase_11_shadow_quality_evaluator_v1.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket",
        "subprocess", "threading", "multiprocessing", "concurrent", "asyncio",
        "keyring", "boto3", "telegram", "ccxt", "ShadowComparativeEvaluatorV1",
        "ShadowComparativeAggregatorV1", "ShadowAdjudicationFinalizerV1",
        "compare", "aggregate", "finalize", "sqlite", "replay", "production",
        "publish", "persist", "annotation",
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
    float_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]
    assert not (forbidden & imported)
    assert not (forbidden & names)
    assert not ({"compare", "aggregate", "finalize"} & attributes)
    assert not float_literals
