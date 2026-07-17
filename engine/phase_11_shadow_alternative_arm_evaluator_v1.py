"""Detached, deterministic evaluation of precomputed alternative-arm evidence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Mapping

from engine.phase_11_shadow_comparative_evaluator_v1 import MetricAvailabilityV1
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
)
from engine.phase_11_shadow_quality_evaluator_v1 import (
    EscalationNecessityV1,
    EventMaterialityV1,
    ExpectedHandlingV1,
    MappingQualityResultV1,
    QualityComparabilityV1,
    ShadowQualityObservationV1,
)


class ShadowAlternativeArmValidationError(ValueError):
    """Raised when detached alternative-arm evidence is invalid."""


class AlternativeArmIdentityV1(StrEnum):
    DEEPSEEK_ONLY = "DEEPSEEK_ONLY"
    CLAUDE_SONNET_ONLY = "CLAUDE_SONNET_ONLY"
    CLAUDE_OPUS_ONLY = "CLAUDE_OPUS_ONLY"
    ROUTED_PRIMARY_PLUS_ESCALATION = "ROUTED_PRIMARY_PLUS_ESCALATION"


class AlternativeArmExecutionStatusV1(StrEnum):
    COMPLETED = "COMPLETED"
    DENIED = "DENIED"
    FAILED_CLOSED = "FAILED_CLOSED"
    PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"


class AlternativeArmEvidenceAvailabilityV1(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class AlternativeArmDecisionV1(StrEnum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


class AlternativeArmDecisionQualityV1(StrEnum):
    CORRECT = "CORRECT"
    TOO_RESTRICTIVE = "TOO_RESTRICTIVE"
    TOO_PERMISSIVE = "TOO_PERMISSIVE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    INSUFFICIENT_GROUND_TRUTH = "INSUFFICIENT_GROUND_TRUTH"


class AlternativeFalseBlockClassificationV1(StrEnum):
    FALSE_BLOCK = "FALSE_BLOCK"
    NOT_FALSE_BLOCK = "NOT_FALSE_BLOCK"
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_GROUND_TRUTH = "INSUFFICIENT_GROUND_TRUTH"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AlternativeMissedMaterialEventClassificationV1(StrEnum):
    MISSED_MATERIAL_EVENT = "MISSED_MATERIAL_EVENT"
    NOT_MISSED = "NOT_MISSED"
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_GROUND_TRUTH = "INSUFFICIENT_GROUND_TRUTH"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AlternativeEscalationEfficiencyV1(StrEnum):
    SUFFICIENT_WITHOUT_ESCALATION = "SUFFICIENT_WITHOUT_ESCALATION"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    UNNECESSARY_ESCALATION = "UNNECESSARY_ESCALATION"
    INDETERMINATE = "INDETERMINATE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_GROUND_TRUTH = "INSUFFICIENT_GROUND_TRUTH"


_SCHEMA_EVIDENCE = "phase11-shadow-alternative-arm-evidence-v1"
_SCHEMA_PLAN = "phase11-shadow-alternative-arm-evaluation-plan-v1"
_SCHEMA_EVALUATION = "phase11-shadow-alternative-arm-evaluation-v1"
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_REASON_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_MODEL_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SECRET_FRAGMENTS = (
    "api_key",
    "apikey",
    "bearer",
    "credential",
    "password",
    "secret",
    "sk-",
    "token",
)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowAlternativeArmValidationError("Decimal values must be finite")
        normalized = value.normalize()
        if normalized == normalized.to_integral():
            return str(normalized.quantize(Decimal("1")))
        return format(normalized, "f")
    if isinstance(value, datetime):
        _require_utc_datetime("canonical datetime", value)
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShadowAlternativeArmValidationError(
        f"unsupported canonical value type: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes for supported immutable evidence."""

    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def lowercase_sha256(value: Any) -> str:
    """Return a lowercase SHA-256 digest of canonical evidence."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _identity(payload: Mapping[str, Any]) -> str:
    return lowercase_sha256(payload)


def _require_exact_enum(name: str, value: Any, enum_type: type[StrEnum]) -> None:
    if type(value) is not enum_type:
        raise ShadowAlternativeArmValidationError(
            f"{name} must be an exact {enum_type.__name__}"
        )


def _require_identifier(name: str, value: Any) -> None:
    if type(value) is not str or not _IDENTIFIER_PATTERN.fullmatch(value):
        raise ShadowAlternativeArmValidationError(f"{name} is malformed")


def _require_utc_datetime(name: str, value: Any) -> None:
    if type(value) is not datetime:
        raise ShadowAlternativeArmValidationError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ShadowAlternativeArmValidationError(f"{name} must be explicit UTC")


def _parsed_timestamp(name: str, value: Any) -> datetime:
    if type(value) is not str:
        raise ShadowAlternativeArmValidationError(
            f"{name} must be a canonical timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ShadowAlternativeArmValidationError(
            f"{name} is malformed"
        ) from error
    _require_utc_datetime(name, parsed)
    return parsed


def _require_reasons(value: Any) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise ShadowAlternativeArmValidationError(
            "reason_codes must be a non-empty tuple"
        )
    if any(type(reason) is not str or not _REASON_PATTERN.fullmatch(reason) for reason in value):
        raise ShadowAlternativeArmValidationError("reason_codes are malformed")
    if tuple(sorted(set(value))) != value:
        raise ShadowAlternativeArmValidationError(
            "reason_codes must be sorted and unique"
        )
    return value


def _require_zero_effect(effect: Any, proof: Any) -> None:
    if effect != "NONE":
        raise ShadowAlternativeArmValidationError("production_effect must be NONE")
    if proof != "PROVEN_NONE":
        raise ShadowAlternativeArmValidationError(
            "zero_production_effect_proof must be PROVEN_NONE"
        )


def _require_nonnegative_int(name: str, value: Any) -> None:
    if type(value) is not int or value < 0:
        raise ShadowAlternativeArmValidationError(
            f"{name} must be an exact non-negative integer"
        )


def _validate_integer_metric(
    name: str, availability: Any, value: Any
) -> None:
    _require_exact_enum(
        f"{name}_availability", availability, MetricAvailabilityV1
    )
    if availability is MetricAvailabilityV1.AVAILABLE:
        _require_nonnegative_int(name, value)
    elif value is not None:
        raise ShadowAlternativeArmValidationError(
            f"unavailable {name} must remain None"
        )


def _validate_cost_metric(availability: Any, value: Any) -> None:
    _require_exact_enum(
        "cost_availability", availability, MetricAvailabilityV1
    )
    if availability is MetricAvailabilityV1.AVAILABLE:
        if type(value) is not Decimal or not value.is_finite() or value < 0:
            raise ShadowAlternativeArmValidationError(
                "available actual_cost must be a finite non-negative Decimal"
            )
    elif value is not None:
        raise ShadowAlternativeArmValidationError(
            "unavailable actual_cost must remain None"
        )


def _field_names(cls: type[Any]) -> frozenset[str]:
    return frozenset(field.name for field in fields(cls))


@dataclass(frozen=True, slots=True, init=False)
class ShadowAlternativeArmEvidenceV1:
    schema_version: str
    arm_evidence_id: str
    candidate_id: str
    event_id: str
    locked_baseline_commit: str
    arm_identity: AlternativeArmIdentityV1
    provider_model_reference: str
    execution_status: AlternativeArmExecutionStatusV1
    decision_availability: AlternativeArmEvidenceAvailabilityV1
    arm_decision: AlternativeArmDecisionV1 | None
    latency_availability: MetricAvailabilityV1
    actual_latency_ms: int | None
    input_tokens_availability: MetricAvailabilityV1
    actual_input_tokens: int | None
    output_tokens_availability: MetricAvailabilityV1
    actual_output_tokens: int | None
    cost_availability: MetricAvailabilityV1
    actual_cost: Decimal | None
    call_count: int
    retry_count: int
    completed_at: datetime
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        allowed = _field_names(type(self))
        unknown = set(values).difference(allowed)
        if unknown:
            raise ShadowAlternativeArmValidationError(
                f"unknown alternative-arm evidence fields: {sorted(unknown)}"
            )
        missing = allowed.difference(values).difference({"arm_evidence_id"})
        if missing:
            raise ShadowAlternativeArmValidationError(
                f"missing alternative-arm evidence fields: {sorted(missing)}"
            )

        supplied_identity = values.get("arm_evidence_id")
        if supplied_identity is not None:
            _require_identifier("arm_evidence_id", supplied_identity)
        if values["schema_version"] != _SCHEMA_EVIDENCE:
            raise ShadowAlternativeArmValidationError(
                "unsupported alternative-arm evidence schema"
            )
        _require_identifier("candidate_id", values["candidate_id"])
        _require_identifier("event_id", values["event_id"])
        _require_identifier(
            "locked_baseline_commit", values["locked_baseline_commit"]
        )
        if values["locked_baseline_commit"] != LOCKED_PHASE09_BASELINE:
            raise ShadowAlternativeArmValidationError(
                "invalid locked Phase 09 baseline"
            )
        _require_exact_enum(
            "arm_identity", values["arm_identity"], AlternativeArmIdentityV1
        )
        _require_exact_enum(
            "execution_status",
            values["execution_status"],
            AlternativeArmExecutionStatusV1,
        )
        _require_exact_enum(
            "decision_availability",
            values["decision_availability"],
            AlternativeArmEvidenceAvailabilityV1,
        )

        model_reference = values["provider_model_reference"]
        if (
            type(model_reference) is not str
            or not _MODEL_REFERENCE_PATTERN.fullmatch(model_reference)
            or any(fragment in model_reference.lower() for fragment in _SECRET_FRAGMENTS)
        ):
            raise ShadowAlternativeArmValidationError(
                "provider_model_reference is malformed or secret-shaped"
            )

        status = values["execution_status"]
        availability = values["decision_availability"]
        decision = values["arm_decision"]
        if status is AlternativeArmExecutionStatusV1.COMPLETED:
            if (
                availability is not AlternativeArmEvidenceAvailabilityV1.AVAILABLE
                or type(decision) is not AlternativeArmDecisionV1
            ):
                raise ShadowAlternativeArmValidationError(
                    "completed arm evidence requires an available exact decision"
                )
        elif (
            availability is not AlternativeArmEvidenceAvailabilityV1.UNAVAILABLE
            or decision is not None
        ):
            raise ShadowAlternativeArmValidationError(
                "non-completed arm evidence cannot carry a decision"
            )

        _validate_integer_metric(
            "actual_latency_ms",
            values["latency_availability"],
            values["actual_latency_ms"],
        )
        _validate_integer_metric(
            "actual_input_tokens",
            values["input_tokens_availability"],
            values["actual_input_tokens"],
        )
        _validate_integer_metric(
            "actual_output_tokens",
            values["output_tokens_availability"],
            values["actual_output_tokens"],
        )
        _validate_cost_metric(values["cost_availability"], values["actual_cost"])
        _require_nonnegative_int("call_count", values["call_count"])
        _require_nonnegative_int("retry_count", values["retry_count"])
        if values["retry_count"] > values["call_count"]:
            raise ShadowAlternativeArmValidationError(
                "retry_count cannot exceed call_count"
            )
        _require_utc_datetime("completed_at", values["completed_at"])
        reasons = _require_reasons(values["reason_codes"])
        _require_zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )

        payload = {
            name: values[name]
            for name in allowed
            if name != "arm_evidence_id"
        }
        payload["reason_codes"] = reasons
        derived_identity = _identity(payload)
        if supplied_identity is not None and supplied_identity != derived_identity:
            raise ShadowAlternativeArmValidationError(
                "arm_evidence_id does not match canonical evidence"
            )
        for name in allowed:
            if name == "arm_evidence_id":
                object.__setattr__(self, name, derived_identity)
            elif name == "reason_codes":
                object.__setattr__(self, name, reasons)
            else:
                object.__setattr__(self, name, values[name])

    @property
    def identity(self) -> str:
        return self.arm_evidence_id


@dataclass(frozen=True, slots=True, init=False)
class ShadowAlternativeArmEvaluationPlanV1:
    schema_version: str
    alternative_arm_plan_id: str
    quality_observation: ShadowQualityObservationV1
    arm_evidence: ShadowAlternativeArmEvidenceV1
    evaluated_at: datetime
    evaluation_scope: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        allowed = _field_names(type(self))
        unknown = set(values).difference(allowed)
        if unknown:
            raise ShadowAlternativeArmValidationError(
                f"unknown alternative-arm plan fields: {sorted(unknown)}"
            )
        missing = allowed.difference(values).difference(
            {"alternative_arm_plan_id"}
        )
        if missing:
            raise ShadowAlternativeArmValidationError(
                f"missing alternative-arm plan fields: {sorted(missing)}"
            )
        supplied_identity = values.get("alternative_arm_plan_id")
        if supplied_identity is not None:
            _require_identifier("alternative_arm_plan_id", supplied_identity)
        if values["schema_version"] != _SCHEMA_PLAN:
            raise ShadowAlternativeArmValidationError(
                "unsupported alternative-arm plan schema"
            )
        quality = values["quality_observation"]
        evidence = values["arm_evidence"]
        if type(quality) is not ShadowQualityObservationV1:
            raise ShadowAlternativeArmValidationError(
                "quality_observation must be an exact ShadowQualityObservationV1"
            )
        if type(evidence) is not ShadowAlternativeArmEvidenceV1:
            raise ShadowAlternativeArmValidationError(
                "arm_evidence must be an exact ShadowAlternativeArmEvidenceV1"
            )
        if quality.candidate_id != evidence.candidate_id:
            raise ShadowAlternativeArmValidationError("candidate lineage mismatch")
        if quality.event_id != evidence.event_id:
            raise ShadowAlternativeArmValidationError("event lineage mismatch")
        if quality.locked_baseline_commit != evidence.locked_baseline_commit:
            raise ShadowAlternativeArmValidationError("locked baseline mismatch")
        _require_utc_datetime("evaluated_at", values["evaluated_at"])
        quality_evaluated_at = _parsed_timestamp(
            "quality observation evaluated_at", quality.evaluated_at
        )
        if evidence.completed_at < quality_evaluated_at:
            raise ShadowAlternativeArmValidationError(
                "arm evidence cannot precede quality evidence"
            )
        if values["evaluated_at"] < evidence.completed_at:
            raise ShadowAlternativeArmValidationError(
                "evaluation cannot precede arm completion"
            )
        if values["evaluation_scope"] != "DETACHED_EVENT_LEVEL":
            raise ShadowAlternativeArmValidationError(
                "evaluation_scope must be DETACHED_EVENT_LEVEL"
            )
        reasons = _require_reasons(values["reason_codes"])
        _require_zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        payload = {
            "schema_version": values["schema_version"],
            "quality_observation_id": quality.quality_observation_id,
            "arm_evidence_id": evidence.arm_evidence_id,
            "evaluated_at": values["evaluated_at"],
            "evaluation_scope": values["evaluation_scope"],
            "reason_codes": reasons,
            "production_effect": values["production_effect"],
            "zero_production_effect_proof": values[
                "zero_production_effect_proof"
            ],
        }
        derived_identity = _identity(payload)
        if supplied_identity is not None and supplied_identity != derived_identity:
            raise ShadowAlternativeArmValidationError(
                "alternative_arm_plan_id does not match canonical evidence"
            )
        for name in allowed:
            if name == "alternative_arm_plan_id":
                object.__setattr__(self, name, derived_identity)
            elif name == "reason_codes":
                object.__setattr__(self, name, reasons)
            else:
                object.__setattr__(self, name, values[name])

    @property
    def identity(self) -> str:
        return self.alternative_arm_plan_id


@dataclass(frozen=True, slots=True)
class ShadowAlternativeArmEvaluationV1:
    schema_version: str
    alternative_arm_evaluation_id: str
    alternative_arm_plan_id: str
    quality_observation_id: str
    arm_evidence_id: str
    candidate_id: str
    event_id: str
    locked_baseline_commit: str
    arm_identity: AlternativeArmIdentityV1
    provider_model_reference: str
    execution_status: AlternativeArmExecutionStatusV1
    decision_availability: AlternativeArmEvidenceAvailabilityV1
    arm_decision: AlternativeArmDecisionV1 | None
    arm_decision_quality: AlternativeArmDecisionQualityV1
    mapping_quality: MappingQualityResultV1
    false_block: AlternativeFalseBlockClassificationV1
    missed_material_event: AlternativeMissedMaterialEventClassificationV1
    escalation_efficiency: AlternativeEscalationEfficiencyV1
    latency_availability: MetricAvailabilityV1
    actual_latency_ms: int | None
    input_tokens_availability: MetricAvailabilityV1
    actual_input_tokens: int | None
    output_tokens_availability: MetricAvailabilityV1
    actual_output_tokens: int | None
    cost_availability: MetricAvailabilityV1
    actual_cost: Decimal | None
    call_count: int
    retry_count: int
    terminal_status: Any
    completed_at: datetime
    evaluated_at: datetime
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.alternative_arm_evaluation_id


_EXPECTED_RANK = {
    ExpectedHandlingV1.ALLOW: 0,
    ExpectedHandlingV1.HOLD: 1,
    ExpectedHandlingV1.BLOCK: 2,
}
_DECISION_RANK = {
    AlternativeArmDecisionV1.ALLOW: 0,
    AlternativeArmDecisionV1.HOLD: 1,
    AlternativeArmDecisionV1.BLOCK: 2,
}


def _decision_quality(
    quality: ShadowQualityObservationV1,
    evidence: ShadowAlternativeArmEvidenceV1,
) -> AlternativeArmDecisionQualityV1:
    if evidence.decision_availability is AlternativeArmEvidenceAvailabilityV1.UNAVAILABLE:
        return AlternativeArmDecisionQualityV1.UNAVAILABLE
    if (
        not quality.label_usable
        or quality.expected_handling is ExpectedHandlingV1.INSUFFICIENT_EVIDENCE
        or quality.quality_comparability is QualityComparabilityV1.INSUFFICIENT_LABEL
    ):
        return AlternativeArmDecisionQualityV1.INSUFFICIENT_GROUND_TRUTH
    if quality.quality_comparability is QualityComparabilityV1.NOT_COMPARABLE:
        return AlternativeArmDecisionQualityV1.NOT_COMPARABLE
    expected_rank = _EXPECTED_RANK.get(quality.expected_handling)
    decision_rank = _DECISION_RANK.get(evidence.arm_decision)
    if expected_rank is None or decision_rank is None:
        raise ShadowAlternativeArmValidationError(
            "unsupported decision-quality combination"
        )
    if decision_rank == expected_rank:
        return AlternativeArmDecisionQualityV1.CORRECT
    if decision_rank > expected_rank:
        return AlternativeArmDecisionQualityV1.TOO_RESTRICTIVE
    return AlternativeArmDecisionQualityV1.TOO_PERMISSIVE


def _false_block(
    quality: ShadowQualityObservationV1,
    result: AlternativeArmDecisionQualityV1,
) -> AlternativeFalseBlockClassificationV1:
    if result is AlternativeArmDecisionQualityV1.UNAVAILABLE:
        return AlternativeFalseBlockClassificationV1.UNAVAILABLE
    if result in (
        AlternativeArmDecisionQualityV1.INSUFFICIENT_GROUND_TRUTH,
        AlternativeArmDecisionQualityV1.NOT_COMPARABLE,
    ):
        return AlternativeFalseBlockClassificationV1.INSUFFICIENT_GROUND_TRUTH
    if quality.event_materiality is EventMaterialityV1.NON_MATERIAL:
        return AlternativeFalseBlockClassificationV1.NOT_APPLICABLE
    if (
        quality.expected_handling is ExpectedHandlingV1.ALLOW
        and result is AlternativeArmDecisionQualityV1.TOO_RESTRICTIVE
    ):
        return AlternativeFalseBlockClassificationV1.FALSE_BLOCK
    return AlternativeFalseBlockClassificationV1.NOT_FALSE_BLOCK


def _missed_event(
    quality: ShadowQualityObservationV1,
    result: AlternativeArmDecisionQualityV1,
) -> AlternativeMissedMaterialEventClassificationV1:
    if result is AlternativeArmDecisionQualityV1.UNAVAILABLE:
        return AlternativeMissedMaterialEventClassificationV1.UNAVAILABLE
    if result in (
        AlternativeArmDecisionQualityV1.INSUFFICIENT_GROUND_TRUTH,
        AlternativeArmDecisionQualityV1.NOT_COMPARABLE,
    ):
        return (
            AlternativeMissedMaterialEventClassificationV1.INSUFFICIENT_GROUND_TRUTH
        )
    if quality.event_materiality is EventMaterialityV1.NON_MATERIAL:
        return AlternativeMissedMaterialEventClassificationV1.NOT_APPLICABLE
    if (
        quality.expected_handling is ExpectedHandlingV1.BLOCK
        and result is AlternativeArmDecisionQualityV1.TOO_PERMISSIVE
    ):
        return AlternativeMissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
    return AlternativeMissedMaterialEventClassificationV1.NOT_MISSED


def _efficiency(
    quality: ShadowQualityObservationV1,
    evidence: ShadowAlternativeArmEvidenceV1,
    result: AlternativeArmDecisionQualityV1,
) -> AlternativeEscalationEfficiencyV1:
    if result is AlternativeArmDecisionQualityV1.INSUFFICIENT_GROUND_TRUTH:
        return AlternativeEscalationEfficiencyV1.INSUFFICIENT_GROUND_TRUTH
    if result in (
        AlternativeArmDecisionQualityV1.UNAVAILABLE,
        AlternativeArmDecisionQualityV1.NOT_COMPARABLE,
    ):
        return AlternativeEscalationEfficiencyV1.INDETERMINATE
    necessity = quality.escalation_necessity
    if necessity is EscalationNecessityV1.INSUFFICIENT_LABEL:
        return AlternativeEscalationEfficiencyV1.INSUFFICIENT_GROUND_TRUTH
    if necessity is EscalationNecessityV1.INDETERMINATE:
        return AlternativeEscalationEfficiencyV1.INDETERMINATE
    if evidence.arm_identity is AlternativeArmIdentityV1.ROUTED_PRIMARY_PLUS_ESCALATION:
        if necessity is EscalationNecessityV1.NECESSARY:
            return AlternativeEscalationEfficiencyV1.ESCALATION_REQUIRED
        if necessity is EscalationNecessityV1.UNNECESSARY:
            return AlternativeEscalationEfficiencyV1.UNNECESSARY_ESCALATION
        return AlternativeEscalationEfficiencyV1.INDETERMINATE
    if (
        necessity is EscalationNecessityV1.NOT_ESCALATED
        and result is AlternativeArmDecisionQualityV1.CORRECT
    ):
        return AlternativeEscalationEfficiencyV1.SUFFICIENT_WITHOUT_ESCALATION
    return AlternativeEscalationEfficiencyV1.NOT_APPLICABLE


class ShadowAlternativeArmEvaluatorV1:
    """Stateless evaluator for detached, already-created arm evidence."""

    __slots__ = ()

    def evaluate(
        self, plan: ShadowAlternativeArmEvaluationPlanV1
    ) -> ShadowAlternativeArmEvaluationV1:
        if type(plan) is not ShadowAlternativeArmEvaluationPlanV1:
            raise ShadowAlternativeArmValidationError(
                "plan must be an exact ShadowAlternativeArmEvaluationPlanV1"
            )
        quality = plan.quality_observation
        evidence = plan.arm_evidence
        decision_quality = _decision_quality(quality, evidence)
        false_block = _false_block(quality, decision_quality)
        missed_event = _missed_event(quality, decision_quality)
        efficiency = _efficiency(quality, evidence, decision_quality)
        reasons = ("DETACHED_ARM_EVALUATED",)
        payload = {
            "schema_version": _SCHEMA_EVALUATION,
            "alternative_arm_plan_id": plan.alternative_arm_plan_id,
            "quality_observation_id": quality.quality_observation_id,
            "arm_evidence_id": evidence.arm_evidence_id,
            "candidate_id": evidence.candidate_id,
            "event_id": evidence.event_id,
            "locked_baseline_commit": evidence.locked_baseline_commit,
            "arm_identity": evidence.arm_identity,
            "provider_model_reference": evidence.provider_model_reference,
            "execution_status": evidence.execution_status,
            "decision_availability": evidence.decision_availability,
            "arm_decision": evidence.arm_decision,
            "arm_decision_quality": decision_quality,
            "mapping_quality": quality.mapping_quality,
            "false_block": false_block,
            "missed_material_event": missed_event,
            "escalation_efficiency": efficiency,
            "latency_availability": evidence.latency_availability,
            "actual_latency_ms": evidence.actual_latency_ms,
            "input_tokens_availability": evidence.input_tokens_availability,
            "actual_input_tokens": evidence.actual_input_tokens,
            "output_tokens_availability": evidence.output_tokens_availability,
            "actual_output_tokens": evidence.actual_output_tokens,
            "cost_availability": evidence.cost_availability,
            "actual_cost": evidence.actual_cost,
            "call_count": evidence.call_count,
            "retry_count": evidence.retry_count,
            "terminal_status": quality.terminal_status,
            "completed_at": evidence.completed_at,
            "evaluated_at": plan.evaluated_at,
            "reason_codes": reasons,
            "production_effect": "NONE",
            "zero_production_effect_proof": "PROVEN_NONE",
        }
        evaluation_identity = _identity(payload)
        return ShadowAlternativeArmEvaluationV1(
            alternative_arm_evaluation_id=evaluation_identity,
            **payload,
        )


__all__ = [
    "AlternativeArmDecisionQualityV1",
    "AlternativeArmDecisionV1",
    "AlternativeArmEvidenceAvailabilityV1",
    "AlternativeArmExecutionStatusV1",
    "AlternativeArmIdentityV1",
    "AlternativeEscalationEfficiencyV1",
    "AlternativeFalseBlockClassificationV1",
    "AlternativeMissedMaterialEventClassificationV1",
    "ShadowAlternativeArmEvaluationPlanV1",
    "ShadowAlternativeArmEvaluationV1",
    "ShadowAlternativeArmEvaluatorV1",
    "ShadowAlternativeArmEvidenceV1",
    "ShadowAlternativeArmValidationError",
    "canonical_json_bytes",
    "lowercase_sha256",
]
