"""RED contract for detached Phase 11 alternative-provider-arm evidence."""

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
from engine.phase_11_shadow_alternative_arm_evaluator_v1 import (
    AlternativeArmDecisionQualityV1,
    AlternativeArmDecisionV1,
    AlternativeArmEvidenceAvailabilityV1,
    AlternativeArmExecutionStatusV1,
    AlternativeArmIdentityV1,
    AlternativeEscalationEfficiencyV1,
    AlternativeFalseBlockClassificationV1,
    AlternativeMissedMaterialEventClassificationV1,
    ShadowAlternativeArmEvaluationPlanV1,
    ShadowAlternativeArmEvaluationV1,
    ShadowAlternativeArmEvaluatorV1,
    ShadowAlternativeArmEvidenceV1,
    ShadowAlternativeArmValidationError,
    canonical_json_bytes,
    lowercase_sha256,
)


QUALITY_EVALUATED_AT = datetime(2026, 7, 17, 0, 12, tzinfo=UTC)
ARM_COMPLETED_AT = datetime(2026, 7, 17, 0, 13, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 7, 17, 0, 14, tzinfo=UTC)


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
    expected_handling: ExpectedHandlingV1 = ExpectedHandlingV1.ALLOW,
    event_materiality: EventMaterialityV1 = EventMaterialityV1.MATERIAL,
    label_usable: bool = True,
    mapping_quality: MappingQualityResultV1 = MappingQualityResultV1.CORRECT,
    escalation: EscalationNecessityV1 = EscalationNecessityV1.NOT_ESCALATED,
    route: str = "L0",
    terminal_status: ShadowTerminalRecordStatusV1 | None = None,
    candidate_id: str | None = None,
    event_id: str | None = None,
) -> ShadowQualityObservationV1:
    """Direct immutable quality evidence; no label or evaluator is reopened."""

    terminal = terminal_status is not None
    if escalation in {
        EscalationNecessityV1.NECESSARY,
        EscalationNecessityV1.UNNECESSARY,
    }:
        route = "L1_TO_L2"
    return ShadowQualityObservationV1(
        schema_version="phase11-shadow-quality-observation-v1",
        quality_observation_id=None,
        quality_plan_id=_sha(("quality-plan", index)),
        comparative_observation_id=_sha(("comparative-observation", index)),
        label_id=_sha(("human-label", index)),
        candidate_id=candidate_id or f"candidate-{index}",
        event_id=event_id or f"event-{index}",
        entity_id="BTC",
        locked_baseline_commit=LOCKED_PHASE09_BASELINE,
        original_treatment_route=route,
        treatment_availability=(
            TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE
            if terminal
            else TreatmentAvailabilityV1.AVAILABLE
        ),
        control_decision="ALLOW",
        treatment_decision=None if terminal else "ALLOW_NEWS_ELIGIBILITY",
        terminal_status=terminal_status,
        label_usable=label_usable,
        event_materiality=(
            event_materiality
            if label_usable
            else EventMaterialityV1.INSUFFICIENT_EVIDENCE
        ),
        mapping_correctness=(
            EntityMappingCorrectnessV1.CORRECT
            if mapping_quality is MappingQualityResultV1.CORRECT
            else EntityMappingCorrectnessV1.INCORRECT
            if mapping_quality is MappingQualityResultV1.INCORRECT
            else EntityMappingCorrectnessV1.UNAVAILABLE
        ),
        expected_handling=(
            expected_handling
            if label_usable
            else ExpectedHandlingV1.INSUFFICIENT_EVIDENCE
        ),
        quality_comparability=(
            QualityComparabilityV1.TERMINAL_TREATMENT_UNAVAILABLE
            if terminal
            else QualityComparabilityV1.INSUFFICIENT_LABEL
            if not label_usable
            else QualityComparabilityV1.COMPARABLE
        ),
        materiality_quality=(
            MaterialityQualityResultV1.INSUFFICIENT_LABEL
            if not label_usable
            else MaterialityQualityResultV1.CORRECT_NON_MATERIAL_SUPPRESSION
            if event_materiality is EventMaterialityV1.NON_MATERIAL
            else MaterialityQualityResultV1.CORRECT_MATERIAL_EVENT_HANDLING
        ),
        mapping_quality=mapping_quality,
        control_quality=(
            ControlQualityResultV1.INSUFFICIENT_LABEL
            if not label_usable
            else ControlQualityResultV1.CORRECT
        ),
        treatment_quality=(
            TreatmentQualityResultV1.UNAVAILABLE
            if terminal
            else TreatmentQualityResultV1.INSUFFICIENT_LABEL
            if not label_usable
            else TreatmentQualityResultV1.CORRECT
        ),
        false_block=(
            FalseBlockClassificationV1.INSUFFICIENT_LABEL
            if not label_usable
            else FalseBlockClassificationV1.NOT_APPLICABLE
            if event_materiality is EventMaterialityV1.NON_MATERIAL
            else FalseBlockClassificationV1.NOT_FALSE_BLOCK
        ),
        missed_material_event=(
            MissedMaterialEventClassificationV1.INSUFFICIENT_LABEL
            if not label_usable
            else MissedMaterialEventClassificationV1.NOT_APPLICABLE
            if event_materiality is EventMaterialityV1.NON_MATERIAL
            else MissedMaterialEventClassificationV1.NOT_MISSED
        ),
        escalation_necessity=(
            escalation if label_usable else EscalationNecessityV1.INSUFFICIENT_LABEL
        ),
        evaluated_at=QUALITY_EVALUATED_AT,
        reason_codes=("DETACHED_ARM_QUALITY_FIXTURE",),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


def _provider_model(arm: AlternativeArmIdentityV1) -> str:
    return {
        AlternativeArmIdentityV1.DEEPSEEK_ONLY: "deepseek-v3.1",
        AlternativeArmIdentityV1.CLAUDE_SONNET_ONLY: "claude-sonnet-4",
        AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY: "claude-opus-4",
        AlternativeArmIdentityV1.ROUTED_PRIMARY_PLUS_ESCALATION: "phase11-routed-v1",
    }[arm]


def _arm_evidence(
    index: int,
    *,
    arm_identity: AlternativeArmIdentityV1 = AlternativeArmIdentityV1.DEEPSEEK_ONLY,
    execution_status: AlternativeArmExecutionStatusV1 = (
        AlternativeArmExecutionStatusV1.COMPLETED
    ),
    decision_availability: AlternativeArmEvidenceAvailabilityV1 = (
        AlternativeArmEvidenceAvailabilityV1.AVAILABLE
    ),
    decision: AlternativeArmDecisionV1 | None = AlternativeArmDecisionV1.ALLOW,
    latency_availability: MetricAvailabilityV1 = MetricAvailabilityV1.AVAILABLE,
    actual_latency_ms: int | None = 125,
    input_tokens_availability: MetricAvailabilityV1 = MetricAvailabilityV1.AVAILABLE,
    actual_input_tokens: int | None = 40,
    output_tokens_availability: MetricAvailabilityV1 = MetricAvailabilityV1.AVAILABLE,
    actual_output_tokens: int | None = 12,
    cost_availability: MetricAvailabilityV1 = MetricAvailabilityV1.AVAILABLE,
    actual_cost: Decimal | None = Decimal("0.03"),
    candidate_id: str | None = None,
    event_id: str | None = None,
    completed_at: datetime = ARM_COMPLETED_AT,
    provider_model_reference: str | None = None,
    locked_baseline_commit: str = LOCKED_PHASE09_BASELINE,
) -> ShadowAlternativeArmEvidenceV1:
    """Detached precomputed arm evidence; it never invokes a provider."""

    if execution_status is not AlternativeArmExecutionStatusV1.COMPLETED:
        decision_availability = AlternativeArmEvidenceAvailabilityV1.UNAVAILABLE
        decision = None
    return ShadowAlternativeArmEvidenceV1(
        schema_version="phase11-shadow-alternative-arm-evidence-v1",
        arm_evidence_id=None,
        candidate_id=candidate_id or f"candidate-{index}",
        event_id=event_id or f"event-{index}",
        locked_baseline_commit=locked_baseline_commit,
        arm_identity=arm_identity,
        provider_model_reference=provider_model_reference or _provider_model(arm_identity),
        execution_status=execution_status,
        decision_availability=decision_availability,
        arm_decision=decision,
        latency_availability=latency_availability,
        actual_latency_ms=actual_latency_ms,
        input_tokens_availability=input_tokens_availability,
        actual_input_tokens=actual_input_tokens,
        output_tokens_availability=output_tokens_availability,
        actual_output_tokens=actual_output_tokens,
        cost_availability=cost_availability,
        actual_cost=actual_cost,
        call_count=1,
        retry_count=0,
        completed_at=completed_at,
        reason_codes=("PRECOMPUTED_DETACHED_ARM",),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


def _plan(
    quality_observation: ShadowQualityObservationV1,
    arm_evidence: ShadowAlternativeArmEvidenceV1,
    **overrides,
) -> ShadowAlternativeArmEvaluationPlanV1:
    values = {
        "schema_version": "phase11-shadow-alternative-arm-evaluation-plan-v1",
        "alternative_arm_plan_id": None,
        "quality_observation": quality_observation,
        "arm_evidence": arm_evidence,
        "evaluated_at": EVALUATED_AT,
        "evaluation_scope": "DETACHED_EVENT_LEVEL",
        "reason_codes": ("PRECOMPUTED_ARM_ONLY",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowAlternativeArmEvaluationPlanV1(**values)


def test_detached_arm_evidence_is_closed_immutable_and_canonical():
    evidence = _arm_evidence(1)
    assert evidence.identity == _arm_evidence(1).identity
    assert evidence.identity != _arm_evidence(
        1, arm_identity=AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY
    ).identity
    assert evidence.identity != _arm_evidence(1, actual_cost=Decimal("0.04")).identity
    assert evidence.actual_cost == Decimal("0.03")
    assert evidence.production_effect == "NONE"
    assert evidence.zero_production_effect_proof == "PROVEN_NONE"
    with pytest.raises(Exception):
        evidence.actual_cost = Decimal("1.00")  # type: ignore[misc]
    with pytest.raises(ShadowAlternativeArmValidationError):
        _arm_evidence(1, actual_cost=float("0.03"))  # type: ignore[arg-type]
    with pytest.raises(ShadowAlternativeArmValidationError):
        _arm_evidence(1, provider_model_reference="sk-detached-secret")
    values = {name: getattr(evidence, name) for name in evidence.__slots__}
    values["provider_client"] = "FORBIDDEN"
    with pytest.raises(ShadowAlternativeArmValidationError):
        ShadowAlternativeArmEvidenceV1(**values)


def test_arm_fixture_matrix_covers_all_identities_statuses_and_telemetry():
    evidence = tuple(
        _arm_evidence(index, arm_identity=arm)
        for index, arm in enumerate(AlternativeArmIdentityV1, start=1)
    )
    denied = _arm_evidence(
        10, execution_status=AlternativeArmExecutionStatusV1.DENIED
    )
    failed = _arm_evidence(
        11, execution_status=AlternativeArmExecutionStatusV1.FAILED_CLOSED
    )
    partial = _arm_evidence(
        12,
        cost_availability=MetricAvailabilityV1.UNAVAILABLE,
        actual_cost=None,
    )
    unavailable = _arm_evidence(
        13,
        execution_status=AlternativeArmExecutionStatusV1.PARTIAL_EVIDENCE,
    )
    zero_cost = _arm_evidence(14, actual_cost=Decimal("0"))
    terminal_quality = tuple(
        _quality_observation(index, terminal_status=status)
        for index, status in enumerate(ShadowTerminalRecordStatusV1, start=20)
    )
    assert {item.arm_identity for item in evidence} == set(AlternativeArmIdentityV1)
    assert denied.arm_decision is None
    assert failed.decision_availability is AlternativeArmEvidenceAvailabilityV1.UNAVAILABLE
    assert partial.actual_cost is None
    assert unavailable.arm_decision is None
    assert zero_cost.actual_cost == Decimal("0")
    assert {item.terminal_status for item in terminal_quality} == set(
        ShadowTerminalRecordStatusV1
    )
    with pytest.raises(ShadowAlternativeArmValidationError):
        _arm_evidence(
            15,
            cost_availability=MetricAvailabilityV1.UNAVAILABLE,
            actual_cost=Decimal("0"),
        )
    with pytest.raises(ShadowAlternativeArmValidationError):
        _arm_evidence(16, locked_baseline_commit="b" * 40)
    contradictory = {
        name: getattr(denied, name) for name in denied.__slots__
    }
    contradictory["arm_decision"] = AlternativeArmDecisionV1.ALLOW
    with pytest.raises(ShadowAlternativeArmValidationError):
        ShadowAlternativeArmEvidenceV1(**contradictory)


def test_evaluation_plan_binds_detached_lineage_baseline_and_timestamps():
    quality = _quality_observation(1)
    arm = _arm_evidence(1)
    plan = _plan(quality, arm)
    assert plan.quality_observation.identity == quality.identity
    assert plan.arm_evidence.identity == arm.identity
    with pytest.raises(ShadowAlternativeArmValidationError):
        _plan(quality, _arm_evidence(2))
    with pytest.raises(ShadowAlternativeArmValidationError):
        _plan(quality, _arm_evidence(1, event_id="other-event"))
    with pytest.raises(ShadowAlternativeArmValidationError):
        _plan(
            quality,
            _arm_evidence(
                1,
                completed_at=datetime(2026, 7, 17, 0, 15, tzinfo=UTC),
            ),
        )
    with pytest.raises(ShadowAlternativeArmValidationError):
        _plan(
            quality,
            _arm_evidence(
                1,
                completed_at=datetime(2026, 7, 17, 0, 11, tzinfo=UTC),
            ),
        )
    with pytest.raises(ShadowAlternativeArmValidationError):
        _plan(quality, arm, evaluated_at=datetime(2026, 7, 17, 0, 11, tzinfo=UTC))


def test_detached_arm_decision_quality_false_block_and_missed_event():
    evaluator = ShadowAlternativeArmEvaluatorV1()
    correct = evaluator.evaluate(
        _plan(_quality_observation(1), _arm_evidence(1))
    )
    false_block = evaluator.evaluate(
        _plan(
            _quality_observation(2),
            _arm_evidence(2, decision=AlternativeArmDecisionV1.BLOCK),
        )
    )
    missed = evaluator.evaluate(
        _plan(
            _quality_observation(3, expected_handling=ExpectedHandlingV1.BLOCK),
            _arm_evidence(3, decision=AlternativeArmDecisionV1.ALLOW),
        )
    )
    caution = evaluator.evaluate(
        _plan(
            _quality_observation(5, expected_handling=ExpectedHandlingV1.HOLD),
            _arm_evidence(5, decision=AlternativeArmDecisionV1.HOLD),
        )
    )
    suppressed = evaluator.evaluate(
        _plan(
            _quality_observation(
                4,
                event_materiality=EventMaterialityV1.NON_MATERIAL,
                expected_handling=ExpectedHandlingV1.BLOCK,
            ),
            _arm_evidence(4, decision=AlternativeArmDecisionV1.BLOCK),
        )
    )
    assert type(correct) is ShadowAlternativeArmEvaluationV1
    assert correct.arm_decision_quality is AlternativeArmDecisionQualityV1.CORRECT
    assert correct.mapping_quality is MappingQualityResultV1.CORRECT
    assert correct.false_block is AlternativeFalseBlockClassificationV1.NOT_FALSE_BLOCK
    assert correct.missed_material_event is (
        AlternativeMissedMaterialEventClassificationV1.NOT_MISSED
    )
    assert false_block.arm_decision_quality is (
        AlternativeArmDecisionQualityV1.TOO_RESTRICTIVE
    )
    assert false_block.false_block is AlternativeFalseBlockClassificationV1.FALSE_BLOCK
    assert missed.arm_decision_quality is AlternativeArmDecisionQualityV1.TOO_PERMISSIVE
    assert missed.missed_material_event is (
        AlternativeMissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
    )
    assert caution.arm_decision_quality is AlternativeArmDecisionQualityV1.CORRECT
    assert suppressed.arm_decision_quality is AlternativeArmDecisionQualityV1.CORRECT
    assert suppressed.false_block is AlternativeFalseBlockClassificationV1.NOT_APPLICABLE


def test_unavailable_terminal_and_insufficient_ground_truth_do_not_fabricate_arm_decisions():
    evaluator = ShadowAlternativeArmEvaluatorV1()
    unavailable = evaluator.evaluate(
        _plan(
            _quality_observation(10),
            _arm_evidence(
                10,
                execution_status=AlternativeArmExecutionStatusV1.FAILED_CLOSED,
            ),
        )
    )
    insufficient = evaluator.evaluate(
        _plan(
            _quality_observation(11, label_usable=False),
            _arm_evidence(11),
        )
    )
    terminal_quality = _quality_observation(
        12, terminal_status=ShadowTerminalRecordStatusV1.PARTIAL_EVIDENCE
    )
    terminal_arm = evaluator.evaluate(_plan(terminal_quality, _arm_evidence(12)))
    assert unavailable.arm_decision is None
    assert unavailable.arm_decision_quality is AlternativeArmDecisionQualityV1.UNAVAILABLE
    assert insufficient.arm_decision_quality is (
        AlternativeArmDecisionQualityV1.INSUFFICIENT_GROUND_TRUTH
    )
    assert insufficient.false_block is (
        AlternativeFalseBlockClassificationV1.INSUFFICIENT_GROUND_TRUTH
    )
    assert terminal_arm.quality_observation_id == terminal_quality.identity
    assert terminal_arm.terminal_status is ShadowTerminalRecordStatusV1.PARTIAL_EVIDENCE


def test_arm_efficiency_uses_only_committed_route_quality_and_arm_evidence():
    evaluator = ShadowAlternativeArmEvaluatorV1()
    sufficient = evaluator.evaluate(
        _plan(_quality_observation(20), _arm_evidence(20))
    )
    necessary = evaluator.evaluate(
        _plan(
            _quality_observation(21, escalation=EscalationNecessityV1.NECESSARY),
            _arm_evidence(
                21,
                arm_identity=AlternativeArmIdentityV1.ROUTED_PRIMARY_PLUS_ESCALATION,
            ),
        )
    )
    unnecessary = evaluator.evaluate(
        _plan(
            _quality_observation(22, escalation=EscalationNecessityV1.UNNECESSARY),
            _arm_evidence(
                22,
                arm_identity=AlternativeArmIdentityV1.ROUTED_PRIMARY_PLUS_ESCALATION,
            ),
        )
    )
    indeterminate = evaluator.evaluate(
        _plan(
            _quality_observation(23, route="L1", escalation=EscalationNecessityV1.INDETERMINATE),
            _arm_evidence(23),
        )
    )
    assert sufficient.escalation_efficiency is (
        AlternativeEscalationEfficiencyV1.SUFFICIENT_WITHOUT_ESCALATION
    )
    assert necessary.escalation_efficiency is (
        AlternativeEscalationEfficiencyV1.ESCALATION_REQUIRED
    )
    assert unnecessary.escalation_efficiency is (
        AlternativeEscalationEfficiencyV1.UNNECESSARY_ESCALATION
    )
    assert indeterminate.escalation_efficiency is (
        AlternativeEscalationEfficiencyV1.INDETERMINATE
    )


def test_evaluation_preserves_committed_telemetry_decimal_cost_and_unavailability():
    evaluator = ShadowAlternativeArmEvaluatorV1()
    complete = evaluator.evaluate(_plan(_quality_observation(30), _arm_evidence(30)))
    partial = evaluator.evaluate(
        _plan(
            _quality_observation(31),
            _arm_evidence(
                31,
                cost_availability=MetricAvailabilityV1.UNAVAILABLE,
                actual_cost=None,
            ),
        )
    )
    unavailable = evaluator.evaluate(
        _plan(
            _quality_observation(32),
            _arm_evidence(
                32,
                latency_availability=MetricAvailabilityV1.UNAVAILABLE,
                actual_latency_ms=None,
                input_tokens_availability=MetricAvailabilityV1.UNAVAILABLE,
                actual_input_tokens=None,
                output_tokens_availability=MetricAvailabilityV1.UNAVAILABLE,
                actual_output_tokens=None,
                cost_availability=MetricAvailabilityV1.UNAVAILABLE,
                actual_cost=None,
            ),
        )
    )
    assert complete.actual_cost == Decimal("0.03")
    assert complete.actual_latency_ms == 125
    assert partial.cost_availability is MetricAvailabilityV1.UNAVAILABLE
    assert partial.actual_cost is None
    assert unavailable.actual_latency_ms is None
    assert unavailable.actual_input_tokens is None
    assert unavailable.actual_output_tokens is None
    assert unavailable.actual_cost is None


def test_arm_plan_and_evaluation_identities_converge_diverge_and_bind_zero_effect():
    quality = _quality_observation(40)
    first = ShadowAlternativeArmEvaluatorV1().evaluate(_plan(quality, _arm_evidence(40)))
    second = ShadowAlternativeArmEvaluatorV1().evaluate(_plan(quality, _arm_evidence(40)))
    changed = ShadowAlternativeArmEvaluatorV1().evaluate(
        _plan(quality, _arm_evidence(40, decision=AlternativeArmDecisionV1.HOLD))
    )
    assert first.identity == second.identity
    assert first.identity != changed.identity
    assert first.locked_baseline_commit == LOCKED_PHASE09_BASELINE
    assert first.production_effect == "NONE"
    assert first.zero_production_effect_proof == "PROVEN_NONE"
    assert canonical_json_bytes({"cost": Decimal("1.00")}) == b'{"cost":"1"}'
    assert lowercase_sha256({"arm": first.arm_evidence_id}) == _sha(
        {"arm": first.arm_evidence_id}
    )


def test_alternative_arm_module_static_boundaries_are_side_effect_free():
    source = (
        Path(__file__).parents[1]
        / "engine"
        / "phase_11_shadow_alternative_arm_evaluator_v1.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket",
        "subprocess", "threading", "multiprocessing", "concurrent", "asyncio",
        "keyring", "boto3", "telegram", "ccxt", "ShadowQualityEvaluatorV1",
        "ShadowQualityAggregatorV1", "ShadowComparativeEvaluatorV1",
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
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    float_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]
    assert not (forbidden & imported)
    assert not (forbidden & names)
    assert not ({"evaluate", "compare", "aggregate", "finalize"} & attributes)
    assert not float_literals
