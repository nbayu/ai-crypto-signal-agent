"""Deterministic Phase 11 event-level shadow comparison.

The contracts in this module consume detached Phase 09 evidence and an
already-finalized Phase 11 result.  They perform no production execution,
finalization, provider work, ledger transition, persistence, or aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.claude_escalated_review_provider_v1 import (
    ClaudeEscalatedReviewResultV1,
)
from engine.deepseek_primary_review_provider_v1 import (
    DeepSeekPrimaryReviewResultV1,
)
from engine.phase_11_shadow_adjudication_finalizer_v1 import (
    ShadowAdjudicationFinalizationPathV1,
    ShadowAdjudicationFinalizationResultV1,
)
from engine.phase_11_shadow_input_contracts_v1 import (
    Phase09ControlProjectionV1,
)


UTC = timezone.utc
LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_UTC_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"


class ShadowComparativeEvaluationValidationError(ValueError):
    """Raised when event-level comparison evidence is inconsistent."""


class ComparisonComparabilityV1(StrEnum):
    COMPARABLE = "COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class ControlTreatmentDecisionDeltaV1(StrEnum):
    NO_CHANGE = "NO_CHANGE"
    TREATMENT_MORE_RESTRICTIVE = "TREATMENT_MORE_RESTRICTIVE"
    TREATMENT_LESS_RESTRICTIVE = "TREATMENT_LESS_RESTRICTIVE"
    CONTROL_ONLY_DECISION = "CONTROL_ONLY_DECISION"
    TREATMENT_UNAVAILABLE = "TREATMENT_UNAVAILABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class StructuredProviderDisagreementV1(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNANIMOUS = "UNANIMOUS"
    PARTIAL_DISAGREEMENT = "PARTIAL_DISAGREEMENT"
    COMPLETE_DISAGREEMENT = "COMPLETE_DISAGREEMENT"
    UNRESOLVED = "UNRESOLVED"
    UNAVAILABLE = "UNAVAILABLE"


class TreatmentAvailabilityV1(StrEnum):
    AVAILABLE = "AVAILABLE"
    TERMINAL_UNAVAILABLE = "TERMINAL_UNAVAILABLE"


class MetricAvailabilityV1(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowComparativeEvaluationValidationError(
                f"invalid {label}"
            )
        parsed = value.astimezone(UTC)
    elif type(value) is str and _UTC_TEXT.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ShadowComparativeEvaluationValidationError(
                f"invalid {label}"
            ) from error
    else:
        raise ShadowComparativeEvaluationValidationError(f"invalid {label}")
    text = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return text.replace("+00:00", "Z").replace(".000000Z", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowComparativeEvaluationValidationError(
                "non-canonical decimal"
            )
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        return _timestamp(value, "timestamp")
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes."""

    try:
        return json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowComparativeEvaluationValidationError(
            "non-canonical comparison metadata"
        ) from error


def lowercase_sha256(value: Any) -> str:
    """Return lowercase SHA-256 over canonical structured material."""

    return sha256(canonical_json_bytes(value)).hexdigest()


def _identity(value: Any, material: Mapping[str, Any], label: str) -> str:
    expected = lowercase_sha256(material)
    if value is not None and (
        type(value) is not str
        or _HASH.fullmatch(value) is None
        or value != expected
    ):
        raise ShadowComparativeEvaluationValidationError(f"invalid {label}")
    return expected


def _hash_value(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ShadowComparativeEvaluationValidationError(f"invalid {label}")
    return value


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ShadowComparativeEvaluationValidationError(f"invalid {label}")
    return value


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ShadowComparativeEvaluationValidationError(
            "invalid reason_codes"
        )
    result: list[str] = []
    for item in value:
        if type(item) is not str or _REASON.fullmatch(item) is None:
            raise ShadowComparativeEvaluationValidationError(
                "invalid reason_codes"
            )
        if item in result:
            raise ShadowComparativeEvaluationValidationError(
                "duplicate reason_codes"
            )
        result.append(item)
    if not result:
        raise ShadowComparativeEvaluationValidationError(
            "missing reason_codes"
        )
    return tuple(sorted(result))


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowComparativeEvaluationValidationError(
            "non-zero production effect"
        )


_SNAPSHOT_FIELDS = frozenset(
    (
        "schema_version",
        "control_snapshot_id",
        "locked_baseline_commit",
        "control_projection",
        "control_artifact_type",
        "control_artifact_identity",
        "candidate_id",
        "event_id",
        "control_decision",
        "control_reason_codes",
        "captured_at",
        "control_evaluated_at",
        "publication_state",
        "reason_codes",
        "comparison_authority",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class Phase09ControlSnapshotV1:
    schema_version: str
    control_snapshot_id: str
    locked_baseline_commit: str
    control_projection: Phase09ControlProjectionV1
    control_artifact_type: str
    control_artifact_identity: str
    candidate_id: str
    event_id: str
    control_decision: str
    control_reason_codes: tuple[str, ...]
    captured_at: str
    control_evaluated_at: str
    publication_state: str
    reason_codes: tuple[str, ...]
    comparison_authority: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _SNAPSHOT_FIELDS:
            raise ShadowComparativeEvaluationValidationError(
                "invalid control-snapshot fields"
            )
        if values["schema_version"] != "phase09-control-snapshot-v1":
            raise ShadowComparativeEvaluationValidationError(
                "unsupported control-snapshot schema"
            )
        if values["locked_baseline_commit"] != LOCKED_PHASE09_BASELINE:
            raise ShadowComparativeEvaluationValidationError(
                "foreign Phase 09 baseline"
            )
        control = values["control_projection"]
        if type(control) is not Phase09ControlProjectionV1:
            raise ShadowComparativeEvaluationValidationError(
                "invalid control projection"
            )
        artifact_identity = _hash_value(
            values["control_artifact_identity"],
            "control_artifact_identity",
        )
        candidate_id = _identifier(values["candidate_id"], "candidate_id")
        event_id = _identifier(values["event_id"], "event_id")
        decision = values["control_decision"]
        state = values["publication_state"]
        expected_decision = (
            "ALLOW" if control.disposition == "PUBLISHED_SIGNAL" else "HOLD"
        )
        expected_state = control.disposition
        if (
            values["control_artifact_type"]
            != "PHASE09_CONTROL_PROJECTION"
            or artifact_identity != control.identity
            or candidate_id != control.candidate_id
            or event_id != control.event_id
            or decision != expected_decision
            or state != expected_state
            or values["comparison_authority"] != "EVIDENCE_ONLY"
        ):
            raise ShadowComparativeEvaluationValidationError(
                "control-snapshot evidence mismatch"
            )
        control_reasons = _reasons(values["control_reason_codes"])
        if control_reasons != tuple(sorted(control.reason_codes)):
            raise ShadowComparativeEvaluationValidationError(
                "control reason mismatch"
            )
        evaluated_at = _timestamp(
            values["control_evaluated_at"],
            "control_evaluated_at",
        )
        captured_at = _timestamp(values["captured_at"], "captured_at")
        if (
            evaluated_at != control.evaluated_at
            or _parsed(captured_at) < _parsed(evaluated_at)
        ):
            raise ShadowComparativeEvaluationValidationError(
                "control timestamp mismatch"
            )
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
            "control_artifact_type": "PHASE09_CONTROL_PROJECTION",
            "control_artifact_identity": artifact_identity,
            "candidate_id": candidate_id,
            "event_id": event_id,
            "control_decision": decision,
            "control_reason_codes": control_reasons,
            "captured_at": captured_at,
            "control_evaluated_at": evaluated_at,
            "publication_state": state,
            "reason_codes": reasons,
            "comparison_authority": "EVIDENCE_ONLY",
        }
        snapshot_id = _identity(
            values["control_snapshot_id"],
            material,
            "control_snapshot_id",
        )
        normalized = dict(values)
        normalized.update(
            control_snapshot_id=snapshot_id,
            locked_baseline_commit=LOCKED_PHASE09_BASELINE,
            control_artifact_identity=artifact_identity,
            candidate_id=candidate_id,
            event_id=event_id,
            control_decision=decision,
            control_reason_codes=control_reasons,
            captured_at=captured_at,
            control_evaluated_at=evaluated_at,
            publication_state=state,
            reason_codes=reasons,
            comparison_authority="EVIDENCE_ONLY",
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.control_snapshot_id


_PLAN_FIELDS = frozenset(
    (
        "schema_version",
        "comparison_plan_id",
        "control_snapshot",
        "treatment_finalization",
        "candidate_id",
        "event_id",
        "compared_at",
        "reason_codes",
        "comparison_scope",
        "production_effect",
        "zero_production_effect_proof",
    )
)


def _treatment_projection(
    treatment: ShadowAdjudicationFinalizationResultV1,
) -> Phase09ControlProjectionV1:
    if treatment.path is ShadowAdjudicationFinalizationPathV1.CLEAN:
        bundle = treatment.clean_bundle
        if bundle is None:
            raise ShadowComparativeEvaluationValidationError(
                "clean treatment lacks bundle"
            )
        return bundle.shadow_input.phase_09_control_projection
    terminal = treatment.terminal_record
    if terminal is None:
        raise ShadowComparativeEvaluationValidationError(
            "terminal treatment lacks record"
        )
    return terminal.shadow_input.phase_09_control_projection


@dataclass(frozen=True, init=False, slots=True)
class ShadowComparativeEvaluationPlanV1:
    schema_version: str
    comparison_plan_id: str
    control_snapshot: Phase09ControlSnapshotV1
    treatment_finalization: ShadowAdjudicationFinalizationResultV1
    candidate_id: str
    event_id: str
    compared_at: str
    reason_codes: tuple[str, ...]
    comparison_scope: str
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PLAN_FIELDS:
            raise ShadowComparativeEvaluationValidationError(
                "invalid comparison-plan fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-comparative-evaluation-plan-v1"
        ):
            raise ShadowComparativeEvaluationValidationError(
                "unsupported comparison-plan schema"
            )
        control = values["control_snapshot"]
        treatment = values["treatment_finalization"]
        if (
            type(control) is not Phase09ControlSnapshotV1
            or type(treatment)
            is not ShadowAdjudicationFinalizationResultV1
        ):
            raise ShadowComparativeEvaluationValidationError(
                "invalid comparison-plan child"
            )
        projection = _treatment_projection(treatment)
        candidate_id = _identifier(values["candidate_id"], "candidate_id")
        event_id = _identifier(values["event_id"], "event_id")
        if (
            control.locked_baseline_commit != LOCKED_PHASE09_BASELINE
            or control.control_projection.identity != projection.identity
            or candidate_id != control.candidate_id
            or candidate_id != projection.candidate_id
            or event_id != control.event_id
            or event_id != projection.event_id
        ):
            raise ShadowComparativeEvaluationValidationError(
                "comparison lineage mismatch"
            )
        if values["comparison_scope"] != "EVENT_LEVEL":
            raise ShadowComparativeEvaluationValidationError(
                "invalid comparison scope"
            )
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        if (
            treatment.production_effect != _ZERO_EFFECT
            or treatment.zero_production_effect_proof != _ZERO_PROOF
        ):
            raise ShadowComparativeEvaluationValidationError(
                "treatment has production effect"
            )
        compared_at = _timestamp(values["compared_at"], "compared_at")
        if (
            _parsed(compared_at) < _parsed(control.captured_at)
            or _parsed(compared_at) < _parsed(treatment.finalized_at)
        ):
            raise ShadowComparativeEvaluationValidationError(
                "comparison predates evidence"
            )
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "control_snapshot_identity": control.identity,
            "treatment_finalization_identity": treatment.identity,
            "candidate_id": candidate_id,
            "event_id": event_id,
            "compared_at": compared_at,
            "reason_codes": reasons,
            "comparison_scope": "EVENT_LEVEL",
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        plan_id = _identity(
            values["comparison_plan_id"],
            material,
            "comparison_plan_id",
        )
        normalized = dict(values)
        normalized.update(
            comparison_plan_id=plan_id,
            candidate_id=candidate_id,
            event_id=event_id,
            compared_at=compared_at,
            reason_codes=reasons,
            comparison_scope="EVENT_LEVEL",
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.comparison_plan_id


@dataclass(frozen=True, slots=True)
class ShadowComparativeObservationV1:
    schema_version: str
    observation_id: str
    comparison_plan_id: str
    control_snapshot_id: str
    treatment_finalization_id: str
    candidate_id: str
    event_id: str
    original_treatment_route: str
    canonical_treatment_route: str | None
    comparability: ComparisonComparabilityV1
    treatment_availability: TreatmentAvailabilityV1
    control_decision: str
    treatment_decision: str | None
    decision_delta: ControlTreatmentDecisionDeltaV1
    structured_disagreement: StructuredProviderDisagreementV1
    unresolved_ambiguity: bool
    terminal_failure: str | None
    terminal_reconciliation: str | None
    latency_availability: MetricAvailabilityV1
    total_latency_ms: int | None
    input_tokens_availability: MetricAvailabilityV1
    total_input_tokens: int | None
    output_tokens_availability: MetricAvailabilityV1
    total_output_tokens: int | None
    cost_availability: MetricAvailabilityV1
    total_actual_cost: Decimal | None
    call_count: int
    retry_count: int
    tier_count: int
    typed_review_ids: tuple[str, ...]
    compared_at: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.observation_id


def _decision_delta(
    control_decision: str,
    treatment_decision: str | None,
) -> ControlTreatmentDecisionDeltaV1:
    if treatment_decision is None:
        return ControlTreatmentDecisionDeltaV1.TREATMENT_UNAVAILABLE
    control_rank = {"ALLOW": 0, "HOLD": 1, "REJECT": 2}
    treatment_rank = {
        "ALLOW_NEWS_ELIGIBILITY": 0,
        "REQUIRE_NEWS_CAUTION": 1,
        "DENY_NEWS_ELIGIBILITY": 2,
        "FAIL_CLOSED": 2,
    }
    if control_decision not in control_rank or treatment_decision not in (
        treatment_rank
    ):
        raise ShadowComparativeEvaluationValidationError(
            "unsupported decision evidence"
        )
    before = control_rank[control_decision]
    after = treatment_rank[treatment_decision]
    if before == after:
        return ControlTreatmentDecisionDeltaV1.NO_CHANGE
    if after > before:
        return ControlTreatmentDecisionDeltaV1.TREATMENT_MORE_RESTRICTIVE
    return ControlTreatmentDecisionDeltaV1.TREATMENT_LESS_RESTRICTIVE


def _disagreement(
    treatment: ShadowAdjudicationFinalizationResultV1,
) -> tuple[StructuredProviderDisagreementV1, tuple[str, ...]]:
    bundle = treatment.clean_bundle
    if bundle is None:
        return StructuredProviderDisagreementV1.UNAVAILABLE, ()
    evidence = bundle.typed_review_evidence
    identities = tuple(item.typed_review_identity for item in evidence)
    if len(evidence) == 1:
        if type(evidence[0].typed_review_result) is not (
            DeepSeekPrimaryReviewResultV1
        ):
            raise ShadowComparativeEvaluationValidationError(
                "invalid primary review evidence"
            )
        return StructuredProviderDisagreementV1.NOT_APPLICABLE, identities
    states: list[str] = []
    for item in evidence[1:]:
        result = item.typed_review_result
        if type(result) is not ClaudeEscalatedReviewResultV1:
            raise ShadowComparativeEvaluationValidationError(
                "invalid escalated review evidence"
            )
        states.append(result.agreement_state_with_deepseek)
    if any(item == "UNRESOLVED" for item in states):
        classification = StructuredProviderDisagreementV1.UNRESOLVED
    elif all(item == "AGREES" for item in states):
        classification = StructuredProviderDisagreementV1.UNANIMOUS
    elif all(item == "DISAGREES" for item in states):
        classification = StructuredProviderDisagreementV1.COMPLETE_DISAGREEMENT
    else:
        classification = StructuredProviderDisagreementV1.PARTIAL_DISAGREEMENT
    return classification, identities


def _terminal_metrics(
    treatment: ShadowAdjudicationFinalizationResultV1,
) -> tuple[
    MetricAvailabilityV1,
    int | None,
    MetricAvailabilityV1,
    int | None,
    MetricAvailabilityV1,
    int | None,
    MetricAvailabilityV1,
    Decimal | None,
    int,
    int,
    int,
]:
    terminal = treatment.terminal_record
    if terminal is None:
        raise ShadowComparativeEvaluationValidationError(
            "terminal metrics require terminal record"
        )
    results = terminal.run_result.invocation_results
    if not results:
        unavailable = MetricAvailabilityV1.UNAVAILABLE
        return (
            unavailable,
            None,
            unavailable,
            None,
            unavailable,
            None,
            unavailable,
            None,
            0,
            0,
            0,
        )
    latency = sum(item.latency_ms for item in results)
    input_tokens = sum(item.input_tokens for item in results)
    output_tokens = sum(item.output_tokens for item in results)
    actual_values = tuple(item.actual_cost for item in results)
    cost_available = all(item is not None for item in actual_values)
    cost = (
        sum(
            (item for item in actual_values if item is not None),
            Decimal("0"),
        )
        if cost_available
        else None
    )
    retries = sum(max(item.attempt_count - 1, 0) for item in results)
    return (
        MetricAvailabilityV1.AVAILABLE,
        latency,
        MetricAvailabilityV1.AVAILABLE,
        input_tokens,
        MetricAvailabilityV1.AVAILABLE,
        output_tokens,
        (
            MetricAvailabilityV1.AVAILABLE
            if cost_available
            else MetricAvailabilityV1.UNAVAILABLE
        ),
        cost,
        len(results),
        retries,
        len({item.model for item in results}),
    )


class ShadowComparativeEvaluatorV1:
    """Side-effect-free evaluator for one immutable event-level plan."""

    __slots__ = ()

    def compare(
        self,
        plan: ShadowComparativeEvaluationPlanV1,
    ) -> ShadowComparativeObservationV1:
        if type(plan) is not ShadowComparativeEvaluationPlanV1:
            raise ShadowComparativeEvaluationValidationError(
                "invalid comparison plan"
            )
        control = plan.control_snapshot
        treatment = plan.treatment_finalization
        clean = treatment.path is ShadowAdjudicationFinalizationPathV1.CLEAN
        if clean:
            bundle = treatment.clean_bundle
            gate = treatment.signal_gate_decision
            risk = treatment.news_risk_object
            record = treatment.clean_execution_record
            if (
                bundle is None
                or gate is None
                or risk is None
                or record is None
                or treatment.terminal_record is not None
                or record.signal_gate_decision_id
                != gate.signal_gate_decision_id
                or record.news_risk_object_id != risk.news_risk_object_id
                or record.event_id != plan.event_id
                or record.route != treatment.canonical_record_route
            ):
                raise ShadowComparativeEvaluationValidationError(
                    "invalid clean treatment"
                )
            treatment_decision = gate.eligibility_recommendation
            availability = TreatmentAvailabilityV1.AVAILABLE
            disagreement, review_ids = _disagreement(treatment)
            unresolved = (
                treatment.adjudication_result.final_ambiguity_state != "NONE"
                or treatment.adjudication_result.final_contradiction_state
                == "UNRESOLVED"
            )
            latency_availability = MetricAvailabilityV1.AVAILABLE
            total_latency_ms = record.latency_ms
            input_availability = MetricAvailabilityV1.AVAILABLE
            total_input_tokens = record.input_tokens
            output_availability = MetricAvailabilityV1.AVAILABLE
            total_output_tokens = record.output_tokens
            cost_availability = (
                MetricAvailabilityV1.AVAILABLE
                if record.actual_cost is not None
                else MetricAvailabilityV1.UNAVAILABLE
            )
            total_actual_cost = record.actual_cost
            call_count = len(record.usage_record_ids)
            retry_count = max(record.attempt_count - call_count, 0)
            tier_count = len(record.model_identities)
            terminal_failure = None
            terminal_reconciliation = None
            reasons = ("CLEAN_TREATMENT_COMPARISON",)
        else:
            terminal = treatment.terminal_record
            if (
                terminal is None
                or treatment.clean_bundle is not None
                or treatment.adjudication_result is not None
                or treatment.news_risk_object is not None
                or treatment.signal_gate_decision is not None
                or treatment.clean_execution_record is not None
            ):
                raise ShadowComparativeEvaluationValidationError(
                    "invalid terminal treatment"
                )
            treatment_decision = None
            availability = TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE
            disagreement = StructuredProviderDisagreementV1.UNAVAILABLE
            review_ids = ()
            unresolved = (
                terminal.run_result.reconciliation_state
                == "RECONCILIATION_REQUIRED"
            )
            (
                latency_availability,
                total_latency_ms,
                input_availability,
                total_input_tokens,
                output_availability,
                total_output_tokens,
                cost_availability,
                total_actual_cost,
                call_count,
                retry_count,
                tier_count,
            ) = _terminal_metrics(treatment)
            terminal_failure = terminal.run_result.failure_class
            terminal_reconciliation = terminal.run_result.reconciliation_state
            reasons = ("TERMINAL_TREATMENT_UNAVAILABLE",)
        delta = _decision_delta(
            control.control_decision,
            treatment_decision,
        )
        comparability = ComparisonComparabilityV1.COMPARABLE
        material = {
            "schema_version": "phase11-shadow-comparative-observation-v1",
            "comparison_plan_id": plan.identity,
            "control_snapshot_id": control.identity,
            "treatment_finalization_id": treatment.identity,
            "candidate_id": plan.candidate_id,
            "event_id": plan.event_id,
            "original_treatment_route": treatment.original_run_route,
            "canonical_treatment_route": treatment.canonical_record_route,
            "comparability": comparability,
            "treatment_availability": availability,
            "control_decision": control.control_decision,
            "treatment_decision": treatment_decision,
            "decision_delta": delta,
            "structured_disagreement": disagreement,
            "unresolved_ambiguity": unresolved,
            "terminal_failure": terminal_failure,
            "terminal_reconciliation": terminal_reconciliation,
            "latency_availability": latency_availability,
            "total_latency_ms": total_latency_ms,
            "input_tokens_availability": input_availability,
            "total_input_tokens": total_input_tokens,
            "output_tokens_availability": output_availability,
            "total_output_tokens": total_output_tokens,
            "cost_availability": cost_availability,
            "total_actual_cost": total_actual_cost,
            "call_count": call_count,
            "retry_count": retry_count,
            "tier_count": tier_count,
            "typed_review_ids": review_ids,
            "compared_at": plan.compared_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        return ShadowComparativeObservationV1(
            schema_version=material["schema_version"],
            observation_id=lowercase_sha256(material),
            comparison_plan_id=plan.identity,
            control_snapshot_id=control.identity,
            treatment_finalization_id=treatment.identity,
            candidate_id=plan.candidate_id,
            event_id=plan.event_id,
            original_treatment_route=treatment.original_run_route,
            canonical_treatment_route=treatment.canonical_record_route,
            comparability=comparability,
            treatment_availability=availability,
            control_decision=control.control_decision,
            treatment_decision=treatment_decision,
            decision_delta=delta,
            structured_disagreement=disagreement,
            unresolved_ambiguity=unresolved,
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
            call_count=call_count,
            retry_count=retry_count,
            tier_count=tier_count,
            typed_review_ids=review_ids,
            compared_at=plan.compared_at,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )


__all__ = (
    "ComparisonComparabilityV1",
    "ControlTreatmentDecisionDeltaV1",
    "LOCKED_PHASE09_BASELINE",
    "MetricAvailabilityV1",
    "Phase09ControlSnapshotV1",
    "ShadowComparativeEvaluationPlanV1",
    "ShadowComparativeEvaluationValidationError",
    "ShadowComparativeEvaluatorV1",
    "ShadowComparativeObservationV1",
    "StructuredProviderDisagreementV1",
    "TreatmentAvailabilityV1",
    "canonical_json_bytes",
    "lowercase_sha256",
)
