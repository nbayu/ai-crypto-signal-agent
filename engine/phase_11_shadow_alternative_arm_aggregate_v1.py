"""Deterministic aggregation of detached alternative-arm evaluations."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

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
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    MetricAvailabilityV1,
)


class ShadowAlternativeArmAggregationValidationError(ValueError):
    """Raised when aggregate detached-arm evidence is inconsistent."""


class AlternativeArmAggregationScopeV1(StrEnum):
    ALTERNATIVE_ARM_EVALUATION_SET = "ALTERNATIVE_ARM_EVALUATION_SET"


class AlternativeArmCoverageStatusV1(StrEnum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AlternativeArmAggregateRateAvailabilityV1(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class AlternativeArmTelemetryAvailabilityV1(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


_UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_RATE_SCALE = Decimal("0.0000000001")
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"


def _canonical(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowAlternativeArmAggregationValidationError(
                "canonical Decimal must be finite"
            )
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        if (
            value.tzinfo is None
            or value.utcoffset() is None
            or value.utcoffset().total_seconds() != 0
        ):
            raise ShadowAlternativeArmAggregationValidationError(
                "canonical datetime must be explicit UTC"
            )
        return value.astimezone(_UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShadowAlternativeArmAggregationValidationError(
        f"unsupported canonical type: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON for aggregate arm evidence."""

    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def lowercase_sha256(value: Any) -> str:
    """Return lowercase SHA-256 over canonical evidence."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _identity(material: Any, supplied: Any, label: str) -> str:
    expected = lowercase_sha256(material)
    if supplied is None:
        return expected
    if type(supplied) is not str or not _HASH.fullmatch(supplied):
        raise ShadowAlternativeArmAggregationValidationError(f"invalid {label}")
    if supplied != expected:
        raise ShadowAlternativeArmAggregationValidationError(
            f"{label} does not match canonical evidence"
        )
    return supplied


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ShadowAlternativeArmAggregationValidationError(
                f"invalid {label}"
            ) from error
    else:
        raise ShadowAlternativeArmAggregationValidationError(f"invalid {label}")
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or parsed.utcoffset().total_seconds() != 0
    ):
        raise ShadowAlternativeArmAggregationValidationError(
            f"{label} must be explicit UTC"
        )
    return parsed.astimezone(_UTC).isoformat().replace("+00:00", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ShadowAlternativeArmAggregationValidationError(
            "invalid aggregate arm reasons"
        )
    reasons = tuple(value)
    if (
        not reasons
        or any(type(item) is not str or not _REASON.fullmatch(item) for item in reasons)
        or tuple(sorted(set(reasons))) != reasons
    ):
        raise ShadowAlternativeArmAggregationValidationError(
            "invalid aggregate arm reasons"
        )
    return reasons


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ShadowAlternativeArmAggregationValidationError(f"invalid {label}")
    return value


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowAlternativeArmAggregationValidationError(
            "aggregate arm evidence must have zero effect"
        )


def _field_names(contract: type[Any]) -> frozenset[str]:
    return frozenset(item.name for item in fields(contract))


_TARGETS = (
    "minimum_total_evaluations",
    "minimum_deepseek_only",
    "minimum_sonnet_only",
    "minimum_opus_only",
    "minimum_routed",
    "minimum_completed",
    "minimum_decision_available",
    "minimum_quality_comparable",
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowAlternativeArmCoveragePlanV1:
    schema_version: str
    coverage_plan_id: str
    minimum_total_evaluations: int
    minimum_deepseek_only: int
    minimum_sonnet_only: int
    minimum_opus_only: int
    minimum_routed: int
    minimum_completed: int
    minimum_decision_available: int
    minimum_quality_comparable: int
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        allowed = _field_names(type(self))
        if frozenset(values) != allowed:
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid coverage-plan fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-alternative-arm-coverage-plan-v1"
        ):
            raise ShadowAlternativeArmAggregationValidationError(
                "unsupported coverage-plan schema"
            )
        targets = {name: _nonnegative(values[name], name) for name in _TARGETS}
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            **targets,
            "reason_codes": reasons,
        }
        identity = _identity(material, values["coverage_plan_id"], "coverage_plan_id")
        normalized = {
            **values,
            **targets,
            "coverage_plan_id": identity,
            "reason_codes": reasons,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.coverage_plan_id


@dataclass(frozen=True, init=False, slots=True)
class ShadowAlternativeArmEvaluationSetV1:
    schema_version: str
    alternative_arm_evaluation_set_id: str
    evaluations: tuple[ShadowAlternativeArmEvaluationV1, ...]
    window_start: str
    window_end: str
    locked_baseline_commit: str
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        allowed = _field_names(type(self))
        if frozenset(values) != allowed:
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid evaluation-set fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-alternative-arm-evaluation-set-v1"
        ):
            raise ShadowAlternativeArmAggregationValidationError(
                "unsupported evaluation-set schema"
            )
        supplied = values["evaluations"]
        if (
            type(supplied) is not tuple
            or not supplied
            or any(type(child) is not ShadowAlternativeArmEvaluationV1 for child in supplied)
        ):
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid alternative-arm evaluations"
            )
        if values["locked_baseline_commit"] != LOCKED_PHASE09_BASELINE:
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid locked baseline"
            )
        window_start = _timestamp(values["window_start"], "window_start")
        window_end = _timestamp(values["window_end"], "window_end")
        if _parsed(window_start) > _parsed(window_end):
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid evaluation window"
            )
        evaluations = tuple(sorted(supplied, key=lambda child: child.identity))
        identities: set[str] = set()
        keys: set[tuple[str, str, AlternativeArmIdentityV1]] = set()
        for child in evaluations:
            if child.locked_baseline_commit != LOCKED_PHASE09_BASELINE:
                raise ShadowAlternativeArmAggregationValidationError(
                    "evaluation has foreign baseline"
                )
            _zero_effect(
                child.production_effect, child.zero_production_effect_proof
            )
            if not (
                _parsed(window_start)
                <= _parsed(_timestamp(child.evaluated_at, "evaluated_at"))
                <= _parsed(window_end)
            ):
                raise ShadowAlternativeArmAggregationValidationError(
                    "evaluation is outside the window"
                )
            if child.identity in identities:
                raise ShadowAlternativeArmAggregationValidationError(
                    "duplicate evaluation identity"
                )
            key = (child.candidate_id, child.event_id, child.arm_identity)
            if key in keys:
                raise ShadowAlternativeArmAggregationValidationError(
                    "duplicate candidate/event/arm comparison key"
                )
            identities.add(child.identity)
            keys.add(key)
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "evaluation_ids": tuple(child.identity for child in evaluations),
            "window_start": window_start,
            "window_end": window_end,
            "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["alternative_arm_evaluation_set_id"],
            "alternative_arm_evaluation_set_id",
        )
        normalized = {
            **values,
            "alternative_arm_evaluation_set_id": identity,
            "evaluations": evaluations,
            "window_start": window_start,
            "window_end": window_end,
            "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
            "reason_codes": reasons,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.alternative_arm_evaluation_set_id


@dataclass(frozen=True, init=False, slots=True)
class ShadowAggregateAlternativeArmPlanV1:
    schema_version: str
    aggregate_alternative_arm_plan_id: str
    evaluation_set: ShadowAlternativeArmEvaluationSetV1
    coverage_plan: ShadowAlternativeArmCoveragePlanV1
    generated_at: str
    aggregation_scope: AlternativeArmAggregationScopeV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        allowed = _field_names(type(self))
        if frozenset(values) != allowed:
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid aggregate-plan fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-aggregate-alternative-arm-plan-v1"
        ):
            raise ShadowAlternativeArmAggregationValidationError(
                "unsupported aggregate-plan schema"
            )
        evaluation_set = values["evaluation_set"]
        coverage_plan = values["coverage_plan"]
        if (
            type(evaluation_set) is not ShadowAlternativeArmEvaluationSetV1
            or type(coverage_plan) is not ShadowAlternativeArmCoveragePlanV1
            or values["aggregation_scope"]
            is not AlternativeArmAggregationScopeV1.ALTERNATIVE_ARM_EVALUATION_SET
        ):
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid aggregate-plan evidence"
            )
        generated_at = _timestamp(values["generated_at"], "generated_at")
        if _parsed(generated_at) < _parsed(evaluation_set.window_end):
            raise ShadowAlternativeArmAggregationValidationError(
                "generated_at precedes evaluation evidence"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        material = {
            "schema_version": values["schema_version"],
            "evaluation_set_id": evaluation_set.identity,
            "coverage_plan_id": coverage_plan.identity,
            "generated_at": generated_at,
            "aggregation_scope": values["aggregation_scope"],
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _identity(
            material,
            values["aggregate_alternative_arm_plan_id"],
            "aggregate_alternative_arm_plan_id",
        )
        normalized = {
            **values,
            "aggregate_alternative_arm_plan_id": identity,
            "generated_at": generated_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.aggregate_alternative_arm_plan_id


@dataclass(frozen=True, slots=True)
class ShadowAlternativeArmRateEvidenceV1:
    numerator: int
    denominator: int
    availability: AlternativeArmAggregateRateAvailabilityV1
    value: Decimal | None

    def __post_init__(self) -> None:
        numerator = _nonnegative(self.numerator, "rate numerator")
        denominator = _nonnegative(self.denominator, "rate denominator")
        if numerator > denominator:
            raise ShadowAlternativeArmAggregationValidationError(
                "rate numerator exceeds denominator"
            )
        if denominator == 0:
            if (
                numerator != 0
                or self.availability
                is not AlternativeArmAggregateRateAvailabilityV1.UNAVAILABLE
                or self.value is not None
            ):
                raise ShadowAlternativeArmAggregationValidationError(
                    "zero-denominator rate must be unavailable"
                )
        elif (
            self.availability
            is not AlternativeArmAggregateRateAvailabilityV1.AVAILABLE
            or type(self.value) is not Decimal
            or self.value
            != (Decimal(numerator) / Decimal(denominator)).quantize(
                _RATE_SCALE, rounding=ROUND_HALF_EVEN
            )
        ):
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid available rate"
            )


@dataclass(frozen=True, slots=True)
class ShadowAlternativeArmTelemetrySummaryV1:
    availability: AlternativeArmTelemetryAvailabilityV1
    available_count: int
    unavailable_count: int
    total: int | Decimal | None
    mean: Decimal | None

    def __post_init__(self) -> None:
        available = _nonnegative(self.available_count, "available count")
        unavailable = _nonnegative(self.unavailable_count, "unavailable count")
        if available == 0:
            if (
                self.availability is not AlternativeArmTelemetryAvailabilityV1.UNAVAILABLE
                or self.total is not None
                or self.mean is not None
            ):
                raise ShadowAlternativeArmAggregationValidationError(
                    "unavailable telemetry is inconsistent"
                )
        else:
            expected = (
                AlternativeArmTelemetryAvailabilityV1.COMPLETE
                if unavailable == 0
                else AlternativeArmTelemetryAvailabilityV1.PARTIAL
            )
            if self.availability is not expected or self.total is None or type(self.mean) is not Decimal:
                raise ShadowAlternativeArmAggregationValidationError(
                    "available telemetry is inconsistent"
                )


@dataclass(frozen=True, slots=True)
class ShadowAlternativeArmCoverageResultV1:
    target: str
    required: int
    observed: int
    status: AlternativeArmCoverageStatusV1
    coverage_result_id: str

    @property
    def identity(self) -> str:
        return self.coverage_result_id


@dataclass(frozen=True, slots=True)
class ShadowAggregateAlternativeArmReportV1:
    schema_version: str
    aggregate_alternative_arm_report_id: str
    aggregate_alternative_arm_plan_id: str
    evaluation_set_id: str
    coverage_plan_id: str
    locked_baseline_commit: str
    window_start: str
    window_end: str
    generated_at: str
    total_evaluation_count: int
    arm_identity_counts: Mapping[AlternativeArmIdentityV1, int]
    execution_status_counts: Mapping[AlternativeArmExecutionStatusV1, int]
    decision_availability_counts: Mapping[AlternativeArmEvidenceAvailabilityV1, int]
    arm_decision_counts: Mapping[AlternativeArmDecisionV1, int]
    decision_quality_counts: Mapping[AlternativeArmDecisionQualityV1, int]
    false_block_counts: Mapping[AlternativeFalseBlockClassificationV1, int]
    missed_event_counts: Mapping[AlternativeMissedMaterialEventClassificationV1, int]
    escalation_efficiency_counts: Mapping[AlternativeEscalationEfficiencyV1, int]
    terminal_status_counts: Mapping[str, int]
    decision_availability_rate: ShadowAlternativeArmRateEvidenceV1
    decision_correctness_rate: ShadowAlternativeArmRateEvidenceV1
    false_block_rate: ShadowAlternativeArmRateEvidenceV1
    missed_material_event_rate: ShadowAlternativeArmRateEvidenceV1
    unnecessary_escalation_rate: ShadowAlternativeArmRateEvidenceV1
    completed_execution_rate: ShadowAlternativeArmRateEvidenceV1
    latency_summary: ShadowAlternativeArmTelemetrySummaryV1
    input_tokens_summary: ShadowAlternativeArmTelemetrySummaryV1
    output_tokens_summary: ShadowAlternativeArmTelemetrySummaryV1
    call_count_summary: ShadowAlternativeArmTelemetrySummaryV1
    retry_count_summary: ShadowAlternativeArmTelemetrySummaryV1
    cost_summary: ShadowAlternativeArmTelemetrySummaryV1
    coverage_results: tuple[ShadowAlternativeArmCoverageResultV1, ...]
    coverage_results_by_target: Mapping[str, ShadowAlternativeArmCoverageResultV1]
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.aggregate_alternative_arm_report_id


def _rate(numerator: int, denominator: int) -> ShadowAlternativeArmRateEvidenceV1:
    if denominator == 0:
        return ShadowAlternativeArmRateEvidenceV1(
            0,
            0,
            AlternativeArmAggregateRateAvailabilityV1.UNAVAILABLE,
            None,
        )
    return ShadowAlternativeArmRateEvidenceV1(
        numerator,
        denominator,
        AlternativeArmAggregateRateAvailabilityV1.AVAILABLE,
        (Decimal(numerator) / Decimal(denominator)).quantize(
            _RATE_SCALE, rounding=ROUND_HALF_EVEN
        ),
    )


def _counts(
    evaluations: tuple[ShadowAlternativeArmEvaluationV1, ...],
    field: str,
    enum_type: type[StrEnum],
) -> dict[StrEnum, int]:
    return {
        member: sum(getattr(child, field) is member for child in evaluations)
        for member in enum_type
    }


def _summary(
    evaluations: tuple[ShadowAlternativeArmEvaluationV1, ...],
    field: str,
    availability_field: str | None,
) -> ShadowAlternativeArmTelemetrySummaryV1:
    if availability_field is None:
        values = [getattr(child, field) for child in evaluations]
    else:
        values = [
            getattr(child, field)
            for child in evaluations
            if getattr(child, availability_field) is MetricAvailabilityV1.AVAILABLE
        ]
    available = len(values)
    unavailable = len(evaluations) - available
    if available == 0:
        return ShadowAlternativeArmTelemetrySummaryV1(
            AlternativeArmTelemetryAvailabilityV1.UNAVAILABLE,
            0,
            unavailable,
            None,
            None,
        )
    total = sum(values)
    mean = (Decimal(total) / Decimal(available)).quantize(
        _RATE_SCALE, rounding=ROUND_HALF_EVEN
    )
    availability = (
        AlternativeArmTelemetryAvailabilityV1.COMPLETE
        if unavailable == 0
        else AlternativeArmTelemetryAvailabilityV1.PARTIAL
    )
    return ShadowAlternativeArmTelemetrySummaryV1(
        availability, available, unavailable, total, mean
    )


def _coverage_result(
    target: str, required: int, observed: int
) -> ShadowAlternativeArmCoverageResultV1:
    status = (
        AlternativeArmCoverageStatusV1.MET
        if observed >= required
        else AlternativeArmCoverageStatusV1.NOT_MET
    )
    material = {
        "target": target,
        "required": required,
        "observed": observed,
        "status": status,
    }
    return ShadowAlternativeArmCoverageResultV1(
        target,
        required,
        observed,
        status,
        lowercase_sha256(material),
    )


def _map_material(value: Mapping[Any, int]) -> dict[str, int]:
    return {
        item.value if isinstance(item, StrEnum) else str(item): count
        for item, count in value.items()
    }


def _rate_material(value: ShadowAlternativeArmRateEvidenceV1) -> dict[str, Any]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "availability": value.availability,
        "value": value.value,
    }


def _summary_material(value: ShadowAlternativeArmTelemetrySummaryV1) -> dict[str, Any]:
    return {
        "availability": value.availability,
        "available_count": value.available_count,
        "unavailable_count": value.unavailable_count,
        "total": value.total,
        "mean": value.mean,
    }


class ShadowAlternativeArmAggregatorV1:
    """Stateless aggregation over immutable detached evaluations."""

    __slots__ = ()

    def aggregate(
        self, plan: ShadowAggregateAlternativeArmPlanV1
    ) -> ShadowAggregateAlternativeArmReportV1:
        if type(plan) is not ShadowAggregateAlternativeArmPlanV1:
            raise ShadowAlternativeArmAggregationValidationError(
                "invalid aggregate arm plan"
            )
        evaluations = plan.evaluation_set.evaluations
        total = len(evaluations)
        arm_counts = _counts(evaluations, "arm_identity", AlternativeArmIdentityV1)
        status_counts = _counts(
            evaluations, "execution_status", AlternativeArmExecutionStatusV1
        )
        availability_counts = _counts(
            evaluations,
            "decision_availability",
            AlternativeArmEvidenceAvailabilityV1,
        )
        decision_counts = _counts(
            evaluations, "arm_decision", AlternativeArmDecisionV1
        )
        quality_counts = _counts(
            evaluations, "arm_decision_quality", AlternativeArmDecisionQualityV1
        )
        false_counts = _counts(
            evaluations,
            "false_block",
            AlternativeFalseBlockClassificationV1,
        )
        missed_counts = _counts(
            evaluations,
            "missed_material_event",
            AlternativeMissedMaterialEventClassificationV1,
        )
        efficiency_counts = _counts(
            evaluations,
            "escalation_efficiency",
            AlternativeEscalationEfficiencyV1,
        )
        terminal_counts = {
            status.value: sum(child.terminal_status is status for child in evaluations)
            for status in ShadowTerminalRecordStatusV1
        }
        comparable_quality = sum(
            quality_counts[item]
            for item in (
                AlternativeArmDecisionQualityV1.CORRECT,
                AlternativeArmDecisionQualityV1.TOO_RESTRICTIVE,
                AlternativeArmDecisionQualityV1.TOO_PERMISSIVE,
            )
        )
        false_denominator = sum(
            child.arm_decision_quality
            in {
                AlternativeArmDecisionQualityV1.CORRECT,
                AlternativeArmDecisionQualityV1.TOO_RESTRICTIVE,
            }
            for child in evaluations
        )
        missed_denominator = sum(
            child.arm_decision_quality
            in {
                AlternativeArmDecisionQualityV1.CORRECT,
                AlternativeArmDecisionQualityV1.TOO_PERMISSIVE,
            }
            for child in evaluations
        )
        efficiency_denominator = (
            efficiency_counts[
                AlternativeEscalationEfficiencyV1.ESCALATION_REQUIRED
            ]
            + efficiency_counts[
                AlternativeEscalationEfficiencyV1.UNNECESSARY_ESCALATION
            ]
        )
        rates = {
            "decision_availability_rate": _rate(
                availability_counts[AlternativeArmEvidenceAvailabilityV1.AVAILABLE],
                total,
            ),
            "decision_correctness_rate": _rate(
                quality_counts[AlternativeArmDecisionQualityV1.CORRECT],
                comparable_quality,
            ),
            "false_block_rate": _rate(
                false_counts[AlternativeFalseBlockClassificationV1.FALSE_BLOCK],
                false_denominator,
            ),
            "missed_material_event_rate": _rate(
                missed_counts[
                    AlternativeMissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
                ],
                missed_denominator,
            ),
            "unnecessary_escalation_rate": _rate(
                efficiency_counts[
                    AlternativeEscalationEfficiencyV1.UNNECESSARY_ESCALATION
                ],
                efficiency_denominator,
            ),
            "completed_execution_rate": _rate(
                status_counts[AlternativeArmExecutionStatusV1.COMPLETED], total
            ),
        }
        summaries = {
            "latency_summary": _summary(
                evaluations, "actual_latency_ms", "latency_availability"
            ),
            "input_tokens_summary": _summary(
                evaluations, "actual_input_tokens", "input_tokens_availability"
            ),
            "output_tokens_summary": _summary(
                evaluations, "actual_output_tokens", "output_tokens_availability"
            ),
            "call_count_summary": _summary(evaluations, "call_count", None),
            "retry_count_summary": _summary(evaluations, "retry_count", None),
            "cost_summary": _summary(
                evaluations, "actual_cost", "cost_availability"
            ),
        }
        observed = {
            "minimum_total_evaluations": total,
            "minimum_deepseek_only": arm_counts[
                AlternativeArmIdentityV1.DEEPSEEK_ONLY
            ],
            "minimum_sonnet_only": arm_counts[
                AlternativeArmIdentityV1.CLAUDE_SONNET_ONLY
            ],
            "minimum_opus_only": arm_counts[
                AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY
            ],
            "minimum_routed": arm_counts[
                AlternativeArmIdentityV1.ROUTED_PRIMARY_PLUS_ESCALATION
            ],
            "minimum_completed": status_counts[
                AlternativeArmExecutionStatusV1.COMPLETED
            ],
            "minimum_decision_available": availability_counts[
                AlternativeArmEvidenceAvailabilityV1.AVAILABLE
            ],
            "minimum_quality_comparable": comparable_quality,
        }
        coverage = tuple(
            _coverage_result(
                target, getattr(plan.coverage_plan, target), observed[target]
            )
            for target in _TARGETS
        )
        coverage_by_target = MappingProxyType(
            {result.target: result for result in coverage}
        )
        reasons = ("DETACHED_ARM_AGGREGATED",)
        material = {
            "schema_version": "phase11-shadow-aggregate-alternative-arm-report-v1",
            "aggregate_plan_id": plan.identity,
            "evaluation_set_id": plan.evaluation_set.identity,
            "coverage_plan_id": plan.coverage_plan.identity,
            "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
            "window_start": plan.evaluation_set.window_start,
            "window_end": plan.evaluation_set.window_end,
            "generated_at": plan.generated_at,
            "total_evaluation_count": total,
            "arm_identity_counts": _map_material(arm_counts),
            "execution_status_counts": _map_material(status_counts),
            "decision_availability_counts": _map_material(availability_counts),
            "arm_decision_counts": _map_material(decision_counts),
            "decision_quality_counts": _map_material(quality_counts),
            "false_block_counts": _map_material(false_counts),
            "missed_event_counts": _map_material(missed_counts),
            "escalation_efficiency_counts": _map_material(efficiency_counts),
            "terminal_status_counts": terminal_counts,
            "rates": {name: _rate_material(item) for name, item in rates.items()},
            "summaries": {
                name: _summary_material(item) for name, item in summaries.items()
            },
            "coverage_result_ids": tuple(result.identity for result in coverage),
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        report_id = lowercase_sha256(material)
        return ShadowAggregateAlternativeArmReportV1(
            schema_version=material["schema_version"],
            aggregate_alternative_arm_report_id=report_id,
            aggregate_alternative_arm_plan_id=plan.identity,
            evaluation_set_id=plan.evaluation_set.identity,
            coverage_plan_id=plan.coverage_plan.identity,
            locked_baseline_commit=LOCKED_PHASE09_BASELINE,
            window_start=plan.evaluation_set.window_start,
            window_end=plan.evaluation_set.window_end,
            generated_at=plan.generated_at,
            total_evaluation_count=total,
            arm_identity_counts=MappingProxyType(arm_counts),
            execution_status_counts=MappingProxyType(status_counts),
            decision_availability_counts=MappingProxyType(availability_counts),
            arm_decision_counts=MappingProxyType(decision_counts),
            decision_quality_counts=MappingProxyType(quality_counts),
            false_block_counts=MappingProxyType(false_counts),
            missed_event_counts=MappingProxyType(missed_counts),
            escalation_efficiency_counts=MappingProxyType(efficiency_counts),
            terminal_status_counts=MappingProxyType(terminal_counts),
            **rates,
            **summaries,
            coverage_results=coverage,
            coverage_results_by_target=coverage_by_target,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )


__all__ = [
    "AlternativeArmAggregateRateAvailabilityV1",
    "AlternativeArmAggregationScopeV1",
    "AlternativeArmCoverageStatusV1",
    "AlternativeArmTelemetryAvailabilityV1",
    "ShadowAggregateAlternativeArmPlanV1",
    "ShadowAggregateAlternativeArmReportV1",
    "ShadowAlternativeArmAggregationValidationError",
    "ShadowAlternativeArmAggregatorV1",
    "ShadowAlternativeArmCoveragePlanV1",
    "ShadowAlternativeArmCoverageResultV1",
    "ShadowAlternativeArmEvaluationSetV1",
    "ShadowAlternativeArmRateEvidenceV1",
    "ShadowAlternativeArmTelemetrySummaryV1",
    "canonical_json_bytes",
    "lowercase_sha256",
]
