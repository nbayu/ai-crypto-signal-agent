"""RED contract for deterministic Phase 11 event-level comparison.

The implementation is deliberately absent.  The evaluator consumes detached
Phase 09 control evidence and an already-finalized Phase 11 treatment result;
it does not run either system.
"""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_shadow_input_contracts_v1 import Phase09ControlProjectionV1
from engine.phase_11_shadow_adjudication_finalizer_v1 import (
    ShadowAdjudicationFinalizationPlanV1,
    ShadowAdjudicationFinalizationPathV1,
    ShadowAdjudicationFinalizationResultV1,
    ShadowAdjudicationFinalizationStatusV1,
    ShadowAdjudicationFinalizerV1,
)

from engine.phase_11_shadow_comparative_evaluator_v1 import (
    ComparisonComparabilityV1,
    ControlTreatmentDecisionDeltaV1,
    MetricAvailabilityV1,
    Phase09ControlSnapshotV1,
    ShadowComparativeEvaluationPlanV1,
    ShadowComparativeEvaluationValidationError,
    ShadowComparativeEvaluatorV1,
    ShadowComparativeObservationV1,
    StructuredProviderDisagreementV1,
    TreatmentAvailabilityV1,
    canonical_json_bytes,
    lowercase_sha256,
)


LOCKED_PHASE09_COMMIT = "a84375fa85c2f318944adfe57aaabac6e43c219c"
UTC_NOW = datetime(2026, 7, 17, 0, 7, tzinfo=UTC)


def _canonical(value):
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _sha(value):
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _control(disposition="NO_TRADE", candidate_id="candidate-001"):
    return Phase09ControlProjectionV1(
        schema_version="phase09-control-projection-v1",
        projection_id="projection-001",
        production_evaluation_id="evaluation-001",
        event_id="event-001",
        candidate_id=candidate_id,
        disposition=disposition,
        reason_codes=("NO_ELIGIBLE_SETUP",) if disposition == "NO_TRADE" else ("ELIGIBLE_SETUP",),
        evidence_refs=("control-evidence-001",),
        evaluated_at="2026-07-17T00:03:00Z",
        source_artifact_hash="a" * 64,
    )


def _snapshot(**overrides):
    control = overrides.pop("control_projection", _control())
    values = {
        "schema_version": "phase09-control-snapshot-v1",
        "control_snapshot_id": None,
        "locked_baseline_commit": LOCKED_PHASE09_COMMIT,
        "control_projection": control,
        "control_artifact_type": "PHASE09_CONTROL_PROJECTION",
        "control_artifact_identity": control.identity,
        "candidate_id": control.candidate_id,
        "event_id": control.event_id,
        "control_decision": "HOLD" if control.disposition == "NO_TRADE" else "ALLOW",
        "control_reason_codes": control.reason_codes,
        "captured_at": "2026-07-17T00:04:00Z",
        "control_evaluated_at": control.evaluated_at,
        "publication_state": "NO_TRADE" if control.disposition == "NO_TRADE" else "PUBLISHED_SIGNAL",
        "reason_codes": ("DETACHED_PHASE09_EVIDENCE",),
        "comparison_authority": "EVIDENCE_ONLY",
    }
    values.update(overrides)
    return Phase09ControlSnapshotV1(**values)


def _finalized(route="L0", terminal=None):
    """Construct pre-finalized child evidence; comparison never calls finalizer."""
    # The finalized-result fixtures are intentionally sourced from the already
    # committed finalizer contract, not from any provider/runtime dependency.
    from tests.test_phase_11_shadow_adjudication_finalizer_v1 import (  # noqa: PLC0415
        _finalization_values,
        _terminal_plan,
    )
    if terminal is None:
        return ShadowAdjudicationFinalizerV1().finalize(
            ShadowAdjudicationFinalizationPlanV1(**_finalization_values(route))
        )
    run_plan, run_result, terminal_record = _terminal_plan(terminal)
    plan = ShadowAdjudicationFinalizationPlanV1(
        schema_version="phase11-shadow-adjudication-finalization-plan-v1",
        finalization_plan_id=None, shadow_input=run_plan.shadow_input,
        run_plan=run_plan, run_result=run_result, clean_bundle=None,
        finalized_at="2026-07-17T00:06:00Z",
        reason_codes=("FINALIZATION_REQUESTED",), production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
    )
    return ShadowAdjudicationFinalizerV1().finalize(plan, terminal_record=terminal_record)


def _plan(**overrides):
    treatment = overrides.pop("treatment", _finalized())
    control = overrides.pop("control_snapshot", _snapshot())
    values = {
        "schema_version": "phase11-shadow-comparative-evaluation-plan-v1",
        "comparison_plan_id": None,
        "control_snapshot": control,
        "treatment_finalization": treatment,
        "candidate_id": control.candidate_id,
        "event_id": control.event_id,
        "compared_at": UTC_NOW,
        "reason_codes": ("EVENT_LEVEL_COMPARISON",),
        "comparison_scope": "EVENT_LEVEL",
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }
    values.update(overrides)
    return ShadowComparativeEvaluationPlanV1(**values)


class TestControlSnapshot:
    def test_snapshot_binds_locked_phase09_projection_as_evidence_only(self):
        snapshot = _snapshot()
        assert snapshot.locked_baseline_commit == LOCKED_PHASE09_COMMIT
        assert snapshot.control_projection.identity == snapshot.control_artifact_identity
        assert snapshot.comparison_authority == "EVIDENCE_ONLY"
        assert snapshot.identity == _snapshot().identity

    @pytest.mark.parametrize("field,value", [
        ("locked_baseline_commit", "b" * 40), ("candidate_id", "candidate-foreign"),
        ("comparison_authority", "PUBLISH"),
    ])
    def test_snapshot_rejects_foreign_or_authoritative_control(self, field, value):
        values = _snapshot().__dict__ if hasattr(_snapshot(), "__dict__") else None
        assert values is None  # frozen slots: malformed inputs must be supplied fresh.
        with pytest.raises((TypeError, ValueError, ShadowComparativeEvaluationValidationError)):
            _snapshot(**{field: value})


class TestComparisonPlanAndObservation:
    @pytest.mark.parametrize("route,canonical", [("L0", "L0"), ("L1", "L1"), ("L2", "L2"), ("L1_TO_L2", "L2")])
    def test_clean_routes_compare_real_finalized_gate_evidence(self, route, canonical):
        treatment = _finalized(route)
        control = _snapshot(control_projection=treatment.clean_bundle.shadow_input.phase_09_control_projection)
        plan = _plan(treatment=treatment, control_snapshot=control, event_id=control.event_id)
        observation = ShadowComparativeEvaluatorV1().compare(plan)
        assert type(observation) is ShadowComparativeObservationV1
        assert observation.comparability is ComparisonComparabilityV1.COMPARABLE
        assert observation.treatment_availability is TreatmentAvailabilityV1.AVAILABLE
        assert observation.treatment_decision is treatment.signal_gate_decision.eligibility_recommendation
        assert observation.original_treatment_route == route
        assert observation.canonical_treatment_route == canonical

    @pytest.mark.parametrize("status", ["DENIED", "FAILED_CLOSED", "PARTIAL_EVIDENCE", "RECONCILIATION_REQUIRED"])
    def test_terminal_treatment_has_no_fabricated_gate_or_decision(self, status):
        treatment = _finalized(terminal=status)
        control = _snapshot(control_projection=treatment.terminal_record.shadow_input.phase_09_control_projection)
        observation = ShadowComparativeEvaluatorV1().compare(_plan(treatment=treatment, control_snapshot=control, event_id=control.event_id))
        assert treatment.path is ShadowAdjudicationFinalizationPathV1.TERMINAL
        assert treatment.signal_gate_decision is None
        assert observation.treatment_decision is None
        assert observation.treatment_availability is TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE
        assert observation.decision_delta is ControlTreatmentDecisionDeltaV1.TREATMENT_UNAVAILABLE

    def test_plan_rejects_candidate_event_timestamp_and_effect_mismatch(self):
        treatment = _finalized("L1")
        control = _snapshot(control_projection=treatment.clean_bundle.shadow_input.phase_09_control_projection)
        for changed in (
            {"candidate_id": "candidate-foreign"}, {"event_id": "event-foreign"},
            {"compared_at": "2026-07-17T00:00:00Z"}, {"production_effect": "PUBLISHED"},
        ):
            with pytest.raises((TypeError, ValueError, ShadowComparativeEvaluationValidationError)):
                _plan(treatment=treatment, control_snapshot=control, **changed)

    def test_structured_disagreement_metrics_identity_and_static_boundaries(self):
        treatment = _finalized("L1_TO_L2")
        control = _snapshot(control_projection=treatment.clean_bundle.shadow_input.phase_09_control_projection)
        observation = ShadowComparativeEvaluatorV1().compare(_plan(treatment=treatment, control_snapshot=control, event_id=control.event_id))
        assert observation.structured_disagreement in {
            StructuredProviderDisagreementV1.UNANIMOUS,
            StructuredProviderDisagreementV1.PARTIAL_DISAGREEMENT,
            StructuredProviderDisagreementV1.COMPLETE_DISAGREEMENT,
            StructuredProviderDisagreementV1.UNRESOLVED,
        }
        assert observation.cost_availability is MetricAvailabilityV1.AVAILABLE
        assert isinstance(observation.total_actual_cost, Decimal)
        assert observation.identity == ShadowComparativeEvaluatorV1().compare(_plan(treatment=treatment, control_snapshot=control, event_id=control.event_id)).identity
        assert lowercase_sha256({"route": "L2"}) == _sha({"route": "L2"})
        assert canonical_json_bytes({"safe": "evidence"}) == b'{"safe":"evidence"}'
        source = Path(__file__).parents[1] / "engine" / "phase_11_shadow_comparative_evaluator_v1.py"
        if not source.exists():
            pytest.skip("RED suite: comparative evaluator implementation is intentionally absent")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert not imports & {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "asyncio", "keyring", "boto3", "google", "azure", "telegram", "ccxt"}
        assert not names & {"run_production_signal_service_v1", "finalize", "invoke", "material_for_adapter", "commit_usage", "reconcile_uncertain_usage", "open", "environ", "getenv", "publication", "replay", "aggregate"}
