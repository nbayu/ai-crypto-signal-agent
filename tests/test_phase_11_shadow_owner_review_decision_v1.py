"""RED contract for explicit synthetic Phase 11 Project Owner review evidence.

Fixtures construct a real immutable exit-gate report directly through its
public constructor.  Synthetic decisions exercise contracts only; they are
not a real Project Owner decision for this repository.
"""

from __future__ import annotations

import ast
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType

import pytest

from engine.phase_11_shadow_cost_projection_v1 import ShadowOwnerBudgetGateStatusV1
from engine.phase_11_shadow_exit_gate_evidence_v1 import (
    ShadowPhase11CriterionStatusV1,
    ShadowPhase11EvidenceDimensionResultV1,
    ShadowPhase11EvidenceDimensionV1,
    ShadowPhase11EvidenceReadinessV1,
    ShadowPhase11ExitGateReportV1,
    ShadowPhase11LimitationsAcceptanceStatusV1,
    ShadowPhase11MechanicalReadinessV1,
    ShadowPhase11OwnerAcceptanceStatusV1,
    ShadowPhase12RecommendationStatusV1,
)
from engine.phase_11_shadow_owner_review_decision_v1 import (
    ShadowPhase11OwnerDecisionInputV1,
    ShadowPhase11OwnerDecisionSourceV1,
    ShadowPhase11OwnerDimensionDecisionV1,
    ShadowPhase11OwnerEvidenceDecisionV1,
    ShadowPhase11OwnerLimitationsDecisionV1,
    ShadowPhase11OwnerOverallDecisionV1,
    ShadowPhase11OwnerReviewPlanV1,
    ShadowPhase11OwnerReviewRecordV1,
    ShadowPhase11OwnerReviewRecorderV1,
    ShadowPhase11OwnerReviewScopeV1,
    ShadowPhase11OwnerReviewValidationError,
    ShadowPhase12EnablementRecommendationV1,
    canonical_json_bytes,
    sha256_hex,
)


BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
EVALUATED_AT = datetime(2026, 7, 17, 0, 14, tzinfo=UTC)
REVIEWED_AT = datetime(2026, 7, 17, 0, 15, tzinfo=UTC)


def _id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dimension_result(
    dimension: ShadowPhase11EvidenceDimensionV1,
    readiness: ShadowPhase11EvidenceReadinessV1 = ShadowPhase11EvidenceReadinessV1.AVAILABLE,
) -> ShadowPhase11EvidenceDimensionResultV1:
    return ShadowPhase11EvidenceDimensionResultV1(
        schema_version="phase11-shadow-evidence-dimension-result-v1",
        evidence_dimension_result_id=_id("source-dimension-" + dimension.value + readiness.value),
        dimension=dimension,
        readiness=readiness,
        source_report_identities=(_id("source-report-" + dimension.value),),
        available_evidence=("SYNTHETIC_SOURCE_EVIDENCE",) if readiness is ShadowPhase11EvidenceReadinessV1.AVAILABLE else (),
        missing_evidence=() if readiness is ShadowPhase11EvidenceReadinessV1.AVAILABLE else ("SYNTHETIC_MISSING_EVIDENCE",),
        reason_codes=("SYNTHETIC_EXIT_GATE_DIMENSION",),
    )


def _exit_gate_report(
    *,
    mechanical: ShadowPhase11MechanicalReadinessV1 = ShadowPhase11MechanicalReadinessV1.READY_FOR_OWNER_REVIEW,
    unavailable_dimension: ShadowPhase11EvidenceDimensionV1 | None = None,
    gaps: tuple[str, ...] = (),
) -> ShadowPhase11ExitGateReportV1:
    dimensions = tuple(
        _dimension_result(
            dimension,
            ShadowPhase11EvidenceReadinessV1.UNAVAILABLE if dimension is unavailable_dimension else ShadowPhase11EvidenceReadinessV1.AVAILABLE,
        )
        for dimension in ShadowPhase11EvidenceDimensionV1
    )
    return ShadowPhase11ExitGateReportV1(
        schema_version="phase11-shadow-exit-gate-report-v1",
        exit_gate_report_id=_id("exit-gate-" + mechanical.value + str(unavailable_dimension) + str(gaps)),
        exit_gate_plan_id=_id("exit-gate-plan"),
        comparative_aggregate_report_id=_id("comparative"),
        quality_aggregate_report_id=_id("quality"),
        alternative_arm_aggregate_report_id=_id("alternative"),
        route_cost_aggregate_report_id=_id("route-cost"),
        cost_projection_report_id=_id("projection"),
        criteria_id=_id("criteria"),
        control_assurance_evidence_id=_id("assurance"),
        locked_baseline_commit=BASELINE,
        source_window_start=datetime(2026, 7, 17, 0, 0, tzinfo=UTC),
        source_window_end=datetime(2026, 7, 17, 0, 10, tzinfo=UTC),
        evaluated_at=EVALUATED_AT,
        coverage_criterion_status=ShadowPhase11CriterionStatusV1.MET,
        critical_control_defect_criterion_status=ShadowPhase11CriterionStatusV1.MET,
        tiering_value_evidence=(),
        tiering_value_criterion_status=ShadowPhase11CriterionStatusV1.MET,
        evidence_dimension_results=dimensions,
        evidence_dimension_results_by_dimension=MappingProxyType({item.dimension: item for item in dimensions}),
        mechanical_readiness=mechanical,
        declared_limitations=("COVERAGE_WINDOW_LIMIT",),
        unresolved_evidence_gaps=gaps,
        uncertainty_classes=("COVERAGE_WINDOW_LIMIT",),
        owner_review_questions=("SYNTHETIC_OWNER_REVIEW_QUESTION",),
        owner_acceptance_status=ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED,
        limitations_acceptance_status=ShadowPhase11LimitationsAcceptanceStatusV1.NOT_RECORDED,
        phase_12_recommendation_status=ShadowPhase12RecommendationStatusV1.NOT_ISSUED,
        owner_budget_gate_status=ShadowOwnerBudgetGateStatusV1.NOT_APPROVED,
        reason_codes=("SYNTHETIC_EXIT_GATE_REPORT",),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )


def _dimension_decision(
    dimension: ShadowPhase11EvidenceDimensionV1,
    *,
    decision: ShadowPhase11OwnerEvidenceDecisionV1 = ShadowPhase11OwnerEvidenceDecisionV1.ACCEPTED,
    readiness: ShadowPhase11EvidenceReadinessV1 = ShadowPhase11EvidenceReadinessV1.AVAILABLE,
) -> ShadowPhase11OwnerDimensionDecisionV1:
    return ShadowPhase11OwnerDimensionDecisionV1(
        schema_version="phase11-shadow-owner-dimension-decision-v1",
        owner_dimension_decision_id=None,
        dimension=dimension,
        owner_decision=decision,
        source_readiness=readiness,
        owner_rationale="SYNTHETIC CONTRACT DECISION FOR " + dimension.value,
        evidence_references=(_id("dimension-reference-" + dimension.value),),
        reason_codes=("SYNTHETIC_OWNER_DIMENSION_DECISION",),
    )


def _decision_input(**overrides) -> ShadowPhase11OwnerDecisionInputV1:
    values = {
        "schema_version": "phase11-shadow-owner-decision-input-v1",
        "owner_decision_input_id": None,
        "owner_reference": "SYNTHETIC_PROJECT_OWNER_CONTRACT_TEST",
        "owner_decision_reference": "SYNTHETIC_OWNER_DECISION_001",
        "decision_source": ShadowPhase11OwnerDecisionSourceV1.SYNTHETIC_CONTRACT_TEST,
        "dimension_decisions": tuple(_dimension_decision(item) for item in ShadowPhase11EvidenceDimensionV1),
        "limitation_references": ("COVERAGE_WINDOW_LIMIT",),
        "limitations_decision": ShadowPhase11OwnerLimitationsDecisionV1.ACCEPTED,
        "overall_decision": ShadowPhase11OwnerOverallDecisionV1.ACCEPTED,
        "phase_12_enablement_recommendation": ShadowPhase12EnablementRecommendationV1.RECOMMEND_ENABLEMENT_WITH_PRECONDITIONS,
        "recommendation_preconditions": ("NO_API_SPENDING_UNTIL_OWNER_BUDGET_APPROVAL", "OWNER_BUDGET_APPROVAL_REQUIRED"),
        "owner_comments": ("SYNTHETIC CONTRACT FIXTURE ONLY",),
        "reason_codes": ("EXPLICIT_SYNTHETIC_OWNER_DECISION",),
    }
    values.update(overrides)
    return ShadowPhase11OwnerDecisionInputV1(**values)


def _plan(**overrides) -> ShadowPhase11OwnerReviewPlanV1:
    values = {
        "schema_version": "phase11-shadow-owner-review-plan-v1",
        "owner_review_plan_id": None,
        "exit_gate_report": _exit_gate_report(),
        "owner_decision_input": _decision_input(),
        "reviewed_at": REVIEWED_AT,
        "locked_baseline_commit": BASELINE,
        "scope": ShadowPhase11OwnerReviewScopeV1.EXPLICIT_OWNER_REVIEW_RECORD,
        "reason_codes": ("EXPLICIT_OWNER_REVIEW_RECORDING",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowPhase11OwnerReviewPlanV1(**values)


def _record(**overrides) -> ShadowPhase11OwnerReviewRecordV1:
    return ShadowPhase11OwnerReviewRecorderV1().record(_plan(**overrides))


def test_contracts_are_closed_immutable_and_exclude_completion_activation_and_spending_authority():
    for contract in (ShadowPhase11OwnerDecisionInputV1, ShadowPhase11OwnerReviewPlanV1, ShadowPhase11OwnerReviewRecordV1, ShadowPhase11OwnerDimensionDecisionV1):
        assert getattr(contract, "__slots__") and "__dict__" not in contract.__slots__
    names = set(ShadowPhase11OwnerReviewRecordV1.__dataclass_fields__)
    assert not names & {"phase11_completion", "phase11_pass", "phase12_enabled", "approved_budget", "spending_authorization", "provider_activation", "deployment", "promotion_verdict", "persistence", "publication"}


def test_explicit_synthetic_owner_input_is_deterministic_and_rejects_invalid_references_and_dimension_sets():
    assert _decision_input().identity == _decision_input().identity
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _decision_input(owner_reference="")
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _decision_input(owner_decision_reference="")
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _decision_input(dimension_decisions=tuple(_dimension_decision(item) for item in tuple(ShadowPhase11EvidenceDimensionV1)[:-1]))
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _decision_input(dimension_decisions=(_dimension_decision(ShadowPhase11EvidenceDimensionV1.QUALITY),) * 5)
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _dimension_decision("UNKNOWN")


def test_all_five_explicit_dimension_acceptances_bind_source_readiness_without_inference():
    record = _record()
    assert tuple(item.dimension for item in record.dimension_decisions) == tuple(ShadowPhase11EvidenceDimensionV1)
    assert all(item.owner_decision is ShadowPhase11OwnerEvidenceDecisionV1.ACCEPTED for item in record.dimension_decisions)
    assert all(item.source_readiness is ShadowPhase11EvidenceReadinessV1.AVAILABLE for item in record.dimension_decisions)


def test_rejected_and_deferred_dimension_decisions_are_explicit_and_unavailable_evidence_cannot_be_accepted():
    decisions = list(_decision_input().dimension_decisions)
    decisions[0] = _dimension_decision(ShadowPhase11EvidenceDimensionV1.QUALITY, decision=ShadowPhase11OwnerEvidenceDecisionV1.REJECTED)
    assert _record(owner_decision_input=_decision_input(dimension_decisions=tuple(decisions), overall_decision=ShadowPhase11OwnerOverallDecisionV1.REJECTED, phase_12_enablement_recommendation=ShadowPhase12EnablementRecommendationV1.DO_NOT_RECOMMEND)).dimension_decisions[0].owner_decision is ShadowPhase11OwnerEvidenceDecisionV1.REJECTED
    decisions[1] = _dimension_decision(ShadowPhase11EvidenceDimensionV1.LATENCY, decision=ShadowPhase11OwnerEvidenceDecisionV1.DEFERRED)
    assert _record(owner_decision_input=_decision_input(dimension_decisions=tuple(decisions), overall_decision=ShadowPhase11OwnerOverallDecisionV1.DEFERRED, phase_12_enablement_recommendation=ShadowPhase12EnablementRecommendationV1.DEFERRED)).dimension_decisions[1].owner_decision is ShadowPhase11OwnerEvidenceDecisionV1.DEFERRED
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _dimension_decision(ShadowPhase11EvidenceDimensionV1.COST, readiness=ShadowPhase11EvidenceReadinessV1.UNAVAILABLE)


def test_limitations_decision_is_explicit_binds_every_declared_limitation_and_rejected_or_deferred_blocks_overall_acceptance():
    report = _exit_gate_report()
    accepted = _record(exit_gate_report=report)
    assert accepted.declared_limitations == report.declared_limitations
    assert accepted.limitations_decision is ShadowPhase11OwnerLimitationsDecisionV1.ACCEPTED
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _record(owner_decision_input=_decision_input(limitation_references=()))
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _record(owner_decision_input=_decision_input(limitations_decision=ShadowPhase11OwnerLimitationsDecisionV1.REJECTED))
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _record(owner_decision_input=_decision_input(limitations_decision=ShadowPhase11OwnerLimitationsDecisionV1.DEFERRED))


def test_overall_acceptance_requires_ready_source_explicit_dimension_and_limitation_acceptance_and_no_gaps():
    assert _record().overall_decision is ShadowPhase11OwnerOverallDecisionV1.ACCEPTED
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _record(exit_gate_report=_exit_gate_report(mechanical=ShadowPhase11MechanicalReadinessV1.NOT_READY))
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _record(exit_gate_report=_exit_gate_report(mechanical=ShadowPhase11MechanicalReadinessV1.INSUFFICIENT_EVIDENCE))
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _record(exit_gate_report=_exit_gate_report(gaps=("BLOCKING_GAP",)))


def test_overall_rejected_and_deferred_are_explicit_without_claiming_the_exit_gate_passed():
    rejected = _record(owner_decision_input=_decision_input(overall_decision=ShadowPhase11OwnerOverallDecisionV1.REJECTED, phase_12_enablement_recommendation=ShadowPhase12EnablementRecommendationV1.DO_NOT_RECOMMEND))
    deferred = _record(owner_decision_input=_decision_input(overall_decision=ShadowPhase11OwnerOverallDecisionV1.DEFERRED, phase_12_enablement_recommendation=ShadowPhase12EnablementRecommendationV1.DEFERRED))
    assert rejected.overall_decision is ShadowPhase11OwnerOverallDecisionV1.REJECTED
    assert deferred.overall_decision is ShadowPhase11OwnerOverallDecisionV1.DEFERRED


def test_phase12_recommendation_is_explicit_and_retains_required_not_approved_budget_preconditions():
    record = _record()
    assert record.phase_12_enablement_recommendation is ShadowPhase12EnablementRecommendationV1.RECOMMEND_ENABLEMENT_WITH_PRECONDITIONS
    assert set(record.recommendation_preconditions) == {"OWNER_BUDGET_APPROVAL_REQUIRED", "NO_API_SPENDING_UNTIL_OWNER_BUDGET_APPROVAL"}
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _record(owner_decision_input=_decision_input(recommendation_preconditions=("NO_API_SPENDING_UNTIL_OWNER_BUDGET_APPROVAL",)))


def test_plan_binds_exact_exit_gate_lineage_timestamp_and_frozen_source_statuses():
    plan = _plan()
    assert type(plan.exit_gate_report) is ShadowPhase11ExitGateReportV1
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _plan(locked_baseline_commit="f" * 40)
    with pytest.raises(ShadowPhase11OwnerReviewValidationError): _plan(reviewed_at=EVALUATED_AT - timedelta(seconds=1))
    assert plan.exit_gate_report.owner_acceptance_status is ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED
    assert plan.exit_gate_report.limitations_acceptance_status is ShadowPhase11LimitationsAcceptanceStatusV1.NOT_RECORDED
    assert plan.exit_gate_report.phase_12_recommendation_status is ShadowPhase12RecommendationStatusV1.NOT_ISSUED
    assert plan.exit_gate_report.owner_budget_gate_status is ShadowOwnerBudgetGateStatusV1.NOT_APPROVED


def test_record_preserves_source_statuses_references_comments_and_not_approved_budget_gate_without_mutation():
    source = _exit_gate_report()
    record = _record(exit_gate_report=source)
    assert record.exit_gate_report_id == source.identity
    assert record.owner_reference == "SYNTHETIC_PROJECT_OWNER_CONTRACT_TEST"
    assert record.owner_decision_reference == "SYNTHETIC_OWNER_DECISION_001"
    assert record.owner_budget_gate_status is ShadowOwnerBudgetGateStatusV1.NOT_APPROVED
    assert record.source_owner_acceptance_status is ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED
    assert record.source_limitations_acceptance_status is ShadowPhase11LimitationsAcceptanceStatusV1.NOT_RECORDED
    assert record.source_phase_12_recommendation_status is ShadowPhase12RecommendationStatusV1.NOT_ISSUED
    with pytest.raises((AttributeError, TypeError)): source.owner_acceptance_status = ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED


def test_identity_converges_diverges_for_material_decisions_and_is_order_independent():
    first = _record(); second = _record()
    assert first.identity == second.identity
    reversed_decisions = tuple(reversed(_decision_input().dimension_decisions))
    reversed_input = _decision_input(dimension_decisions=reversed_decisions, owner_comments=("SYNTHETIC CONTRACT FIXTURE ONLY",))
    assert _record(owner_decision_input=reversed_input).identity == first.identity
    assert _record(owner_decision_input=_decision_input(owner_decision_reference="SYNTHETIC_OWNER_DECISION_002")).identity != first.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\xc3\xa9"}'
    assert sha256_hex(b"owner-review") == hashlib.sha256(b"owner-review").hexdigest()


def test_zero_production_effect_and_only_record_creates_the_owner_review_record():
    record = _record()
    assert record.production_effect == "NONE" and record.zero_production_effect_proof == "PROVEN_NONE"
    assert not hasattr(ShadowPhase11OwnerReviewPlanV1, "record")
    assert callable(ShadowPhase11OwnerReviewRecorderV1().record)


def test_static_dependency_and_side_effect_boundaries():
    module = ast.parse(Path("engine/phase_11_shadow_owner_review_decision_v1.py").read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest"}
    forbidden_names = {"open", "float", "ShadowPhase11ExitGateEvaluatorV1", "ShadowComparativeAggregatorV1", "ShadowQualityAggregatorV1", "ShadowAlternativeArmAggregatorV1", "ShadowRouteCostAggregatorV1", "ShadowCostProjectorV1", "ShadowAdjudicationFinalizerV1", "Provider", "Budget", "Ranking", "Replay", "Persistence", "Publication"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module} | {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.With)) for node in ast.walk(module))
