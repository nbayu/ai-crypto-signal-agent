"""Independent-label, event-level quality evaluation for Phase 11.

The contracts in this module consume immutable comparative observations and
independently supplied label evidence.  They provide evidence only and perform
no upstream execution or operational side effect.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Mapping

from engine.phase_11_finalization_evidence_bridge_v1 import (
    ShadowTerminalRecordStatusV1,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    ComparisonComparabilityV1,
    ShadowComparativeObservationV1,
    StructuredProviderDisagreementV1,
    TreatmentAvailabilityV1,
)


_UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_REVIEW_REFERENCE = re.compile(r"^review-batch-[a-zA-Z0-9-]{1,96}$")
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"


class ShadowQualityEvaluationValidationError(ValueError):
    """Raised when independent label or quality evidence is inconsistent."""


class LabelReviewStatusV1(StrEnum):
    REVIEWED = "REVIEWED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PENDING = "PENDING"


class EventMaterialityV1(StrEnum):
    MATERIAL = "MATERIAL"
    NON_MATERIAL = "NON_MATERIAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EntityMappingCorrectnessV1(StrEnum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    UNAVAILABLE = "UNAVAILABLE"


class ExpectedHandlingV1(StrEnum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class QualityComparabilityV1(StrEnum):
    COMPARABLE = "COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    INSUFFICIENT_LABEL = "INSUFFICIENT_LABEL"
    TERMINAL_TREATMENT_UNAVAILABLE = "TERMINAL_TREATMENT_UNAVAILABLE"


class ControlQualityResultV1(StrEnum):
    CORRECT = "CORRECT"
    TOO_RESTRICTIVE = "TOO_RESTRICTIVE"
    TOO_PERMISSIVE = "TOO_PERMISSIVE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    INSUFFICIENT_LABEL = "INSUFFICIENT_LABEL"


class TreatmentQualityResultV1(StrEnum):
    CORRECT = "CORRECT"
    TOO_RESTRICTIVE = "TOO_RESTRICTIVE"
    TOO_PERMISSIVE = "TOO_PERMISSIVE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    INSUFFICIENT_LABEL = "INSUFFICIENT_LABEL"


class EscalationNecessityV1(StrEnum):
    NECESSARY = "NECESSARY"
    UNNECESSARY = "UNNECESSARY"
    NOT_ESCALATED = "NOT_ESCALATED"
    INDETERMINATE = "INDETERMINATE"
    INSUFFICIENT_LABEL = "INSUFFICIENT_LABEL"


class FalseBlockClassificationV1(StrEnum):
    FALSE_BLOCK = "FALSE_BLOCK"
    NOT_FALSE_BLOCK = "NOT_FALSE_BLOCK"
    INSUFFICIENT_LABEL = "INSUFFICIENT_LABEL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MissedMaterialEventClassificationV1(StrEnum):
    MISSED_MATERIAL_EVENT = "MISSED_MATERIAL_EVENT"
    NOT_MISSED = "NOT_MISSED"
    INSUFFICIENT_LABEL = "INSUFFICIENT_LABEL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MappingQualityResultV1(StrEnum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MaterialityQualityResultV1(StrEnum):
    CORRECT_MATERIAL_EVENT_HANDLING = "CORRECT_MATERIAL_EVENT_HANDLING"
    FALSE_BLOCK = "FALSE_BLOCK"
    MISSED_MATERIAL_EVENT = "MISSED_MATERIAL_EVENT"
    CORRECT_NON_MATERIAL_SUPPRESSION = "CORRECT_NON_MATERIAL_SUPPRESSION"
    INSUFFICIENT_LABEL = "INSUFFICIENT_LABEL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowQualityEvaluationValidationError(
                "canonical datetime must be timezone-aware"
            )
        return value.astimezone(_UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes."""

    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def lowercase_sha256(value: Any) -> str:
    """Return the lowercase SHA-256 of canonical evidence."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _identity(material: Any, supplied: Any, label: str) -> str:
    expected = lowercase_sha256(material)
    if supplied is None:
        return expected
    if type(supplied) is not str or not _HASH.fullmatch(supplied):
        raise ShadowQualityEvaluationValidationError(f"invalid {label}")
    if supplied != expected:
        raise ShadowQualityEvaluationValidationError(
            f"{label} does not match canonical evidence"
        )
    return supplied


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ShadowQualityEvaluationValidationError(f"invalid {label}")
    return value


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ShadowQualityEvaluationValidationError(
                f"invalid {label}"
            ) from exc
    else:
        raise ShadowQualityEvaluationValidationError(f"invalid {label}")
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or parsed.utcoffset().total_seconds() != 0
    ):
        raise ShadowQualityEvaluationValidationError(
            f"{label} must be explicit UTC"
        )
    return parsed.astimezone(_UTC).isoformat().replace("+00:00", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ShadowQualityEvaluationValidationError(
            "invalid quality reason codes"
        )
    reasons = tuple(value)
    if (
        not reasons
        or any(type(item) is not str or not _REASON.fullmatch(item) for item in reasons)
        or tuple(sorted(set(reasons))) != reasons
    ):
        raise ShadowQualityEvaluationValidationError(
            "invalid quality reason codes"
        )
    return reasons


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowQualityEvaluationValidationError(
            "quality evidence must have zero production effect"
        )


_LABEL_FIELDS = frozenset(
    {
        "schema_version",
        "label_id",
        "candidate_id",
        "event_id",
        "entity_id",
        "event_materiality",
        "mapping_correctness",
        "expected_handling",
        "review_status",
        "provenance_category",
        "reviewer_reference",
        "labeled_at",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowHumanLabelEvidenceV1:
    schema_version: str
    label_id: str
    candidate_id: str
    event_id: str
    entity_id: str
    event_materiality: EventMaterialityV1
    mapping_correctness: EntityMappingCorrectnessV1
    expected_handling: ExpectedHandlingV1
    review_status: LabelReviewStatusV1
    provenance_category: str
    reviewer_reference: str
    labeled_at: str
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _LABEL_FIELDS:
            raise ShadowQualityEvaluationValidationError(
                "invalid human-label fields"
            )
        if values["schema_version"] != "phase11-shadow-human-label-evidence-v1":
            raise ShadowQualityEvaluationValidationError(
                "unsupported human-label schema"
            )
        candidate_id = _identifier(values["candidate_id"], "candidate_id")
        event_id = _identifier(values["event_id"], "event_id")
        entity_id = _identifier(values["entity_id"], "entity_id")
        materiality = values["event_materiality"]
        mapping = values["mapping_correctness"]
        expected = values["expected_handling"]
        status = values["review_status"]
        if (
            type(materiality) is not EventMaterialityV1
            or type(mapping) is not EntityMappingCorrectnessV1
            or type(expected) is not ExpectedHandlingV1
            or type(status) is not LabelReviewStatusV1
        ):
            raise ShadowQualityEvaluationValidationError(
                "invalid human-label classification"
            )
        if values["provenance_category"] != "INDEPENDENT_HUMAN_REVIEW":
            raise ShadowQualityEvaluationValidationError(
                "invalid label provenance"
            )
        reviewer_reference = values["reviewer_reference"]
        if (
            type(reviewer_reference) is not str
            or not _REVIEW_REFERENCE.fullmatch(reviewer_reference)
        ):
            raise ShadowQualityEvaluationValidationError(
                "reviewer reference must be pseudonymous"
            )
        labeled_at = _timestamp(values["labeled_at"], "labeled_at")
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "candidate_id": candidate_id,
            "event_id": event_id,
            "entity_id": entity_id,
            "event_materiality": materiality.value,
            "mapping_correctness": mapping.value,
            "expected_handling": expected.value,
            "review_status": status.value,
            "provenance_category": "INDEPENDENT_HUMAN_REVIEW",
            "reviewer_reference": reviewer_reference,
            "labeled_at": labeled_at,
            "reason_codes": reasons,
        }
        label_id = _identity(material, values["label_id"], "label_id")
        normalized = {
            **values,
            "label_id": label_id,
            "candidate_id": candidate_id,
            "event_id": event_id,
            "entity_id": entity_id,
            "labeled_at": labeled_at,
            "reason_codes": reasons,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.label_id


_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "quality_plan_id",
        "comparative_observation",
        "human_label",
        "evaluated_at",
        "quality_scope",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowQualityEvaluationPlanV1:
    schema_version: str
    quality_plan_id: str
    comparative_observation: ShadowComparativeObservationV1
    human_label: ShadowHumanLabelEvidenceV1
    evaluated_at: str
    quality_scope: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PLAN_FIELDS:
            raise ShadowQualityEvaluationValidationError(
                "invalid quality-plan fields"
            )
        if values["schema_version"] != "phase11-shadow-quality-evaluation-plan-v1":
            raise ShadowQualityEvaluationValidationError(
                "unsupported quality-plan schema"
            )
        observation = values["comparative_observation"]
        human_label = values["human_label"]
        if (
            type(observation) is not ShadowComparativeObservationV1
            or type(human_label) is not ShadowHumanLabelEvidenceV1
        ):
            raise ShadowQualityEvaluationValidationError(
                "invalid quality-plan evidence"
            )
        if (
            observation.candidate_id != human_label.candidate_id
            or observation.event_id != human_label.event_id
        ):
            raise ShadowQualityEvaluationValidationError(
                "quality-plan lineage mismatch"
            )
        if observation.locked_baseline_commit != LOCKED_PHASE09_BASELINE:
            raise ShadowQualityEvaluationValidationError(
                "invalid locked Phase 09 baseline"
            )
        if human_label.review_status is LabelReviewStatusV1.PENDING:
            raise ShadowQualityEvaluationValidationError(
                "pending label is unusable"
            )
        if values["quality_scope"] != "EVENT_LEVEL":
            raise ShadowQualityEvaluationValidationError(
                "unsupported quality scope"
            )
        evaluated_at = _timestamp(values["evaluated_at"], "evaluated_at")
        if not (
            _parsed(observation.compared_at)
            <= _parsed(human_label.labeled_at)
            <= _parsed(evaluated_at)
        ):
            raise ShadowQualityEvaluationValidationError(
                "invalid quality evidence timestamp order"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "comparative_observation_id": observation.identity,
            "human_label_id": human_label.identity,
            "candidate_id": observation.candidate_id,
            "event_id": observation.event_id,
            "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
            "evaluated_at": evaluated_at,
            "quality_scope": "EVENT_LEVEL",
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        plan_id = _identity(
            material, values["quality_plan_id"], "quality_plan_id"
        )
        normalized = {
            **values,
            "quality_plan_id": plan_id,
            "evaluated_at": evaluated_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.quality_plan_id


_QUALITY_OBSERVATION_FIELDS = frozenset(
    {
        "schema_version",
        "quality_observation_id",
        "quality_plan_id",
        "comparative_observation_id",
        "label_id",
        "candidate_id",
        "event_id",
        "entity_id",
        "locked_baseline_commit",
        "original_treatment_route",
        "treatment_availability",
        "control_decision",
        "treatment_decision",
        "terminal_status",
        "label_usable",
        "event_materiality",
        "mapping_correctness",
        "expected_handling",
        "quality_comparability",
        "materiality_quality",
        "mapping_quality",
        "control_quality",
        "treatment_quality",
        "false_block",
        "missed_material_event",
        "escalation_necessity",
        "evaluated_at",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowQualityObservationV1:
    schema_version: str
    quality_observation_id: str
    quality_plan_id: str
    comparative_observation_id: str
    label_id: str
    candidate_id: str
    event_id: str
    entity_id: str
    locked_baseline_commit: str
    original_treatment_route: str
    treatment_availability: TreatmentAvailabilityV1
    control_decision: str
    treatment_decision: str | None
    terminal_status: ShadowTerminalRecordStatusV1 | None
    label_usable: bool
    event_materiality: EventMaterialityV1
    mapping_correctness: EntityMappingCorrectnessV1
    expected_handling: ExpectedHandlingV1
    quality_comparability: QualityComparabilityV1
    materiality_quality: MaterialityQualityResultV1
    mapping_quality: MappingQualityResultV1
    control_quality: ControlQualityResultV1
    treatment_quality: TreatmentQualityResultV1
    false_block: FalseBlockClassificationV1
    missed_material_event: MissedMaterialEventClassificationV1
    escalation_necessity: EscalationNecessityV1
    evaluated_at: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _QUALITY_OBSERVATION_FIELDS:
            raise ShadowQualityEvaluationValidationError(
                "invalid quality-observation fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-quality-observation-v1"
        ):
            raise ShadowQualityEvaluationValidationError(
                "unsupported quality-observation schema"
            )
        hash_fields = ("quality_plan_id", "comparative_observation_id", "label_id")
        for name in hash_fields:
            if type(values[name]) is not str or not _HASH.fullmatch(values[name]):
                raise ShadowQualityEvaluationValidationError(f"invalid {name}")
        if (
            values["locked_baseline_commit"] != LOCKED_PHASE09_BASELINE
            or type(values["label_usable"]) is not bool
        ):
            raise ShadowQualityEvaluationValidationError(
                "invalid quality-observation lineage"
            )
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        evaluated_at = _timestamp(values["evaluated_at"], "evaluated_at")
        reasons = _reasons(values["reason_codes"])
        material = {
            name: (
                item.value
                if isinstance(item, StrEnum)
                else item
            )
            for name, item in values.items()
            if name != "quality_observation_id"
        }
        material["evaluated_at"] = evaluated_at
        material["reason_codes"] = reasons
        observation_id = _identity(
            material,
            values["quality_observation_id"],
            "quality_observation_id",
        )
        normalized = {
            **values,
            "quality_observation_id": observation_id,
            "evaluated_at": evaluated_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.quality_observation_id


_CONTROL_RANK = {"ALLOW": 0, "HOLD": 1, "REJECT": 2}
_TREATMENT_RANK = {
    "ALLOW_NEWS_ELIGIBILITY": 0,
    "REQUIRE_NEWS_CAUTION": 1,
    "DENY_NEWS_ELIGIBILITY": 2,
    "FAIL_CLOSED": 2,
}
_EXPECTED_RANK = {
    ExpectedHandlingV1.ALLOW: 0,
    ExpectedHandlingV1.HOLD: 1,
    ExpectedHandlingV1.BLOCK: 2,
}


def _control_quality(
    observation: ShadowComparativeObservationV1,
    human_label: ShadowHumanLabelEvidenceV1,
) -> ControlQualityResultV1:
    if human_label.review_status is LabelReviewStatusV1.INSUFFICIENT_EVIDENCE:
        return ControlQualityResultV1.INSUFFICIENT_LABEL
    if observation.comparability is ComparisonComparabilityV1.NOT_COMPARABLE:
        return ControlQualityResultV1.NOT_COMPARABLE
    expected = _EXPECTED_RANK.get(human_label.expected_handling)
    actual = _CONTROL_RANK.get(observation.control_decision)
    if expected is None:
        return ControlQualityResultV1.INSUFFICIENT_LABEL
    if actual is None:
        return ControlQualityResultV1.UNAVAILABLE
    if actual == expected:
        return ControlQualityResultV1.CORRECT
    if actual > expected:
        return ControlQualityResultV1.TOO_RESTRICTIVE
    return ControlQualityResultV1.TOO_PERMISSIVE


def _treatment_quality(
    observation: ShadowComparativeObservationV1,
    human_label: ShadowHumanLabelEvidenceV1,
) -> TreatmentQualityResultV1:
    if human_label.review_status is LabelReviewStatusV1.INSUFFICIENT_EVIDENCE:
        return TreatmentQualityResultV1.INSUFFICIENT_LABEL
    if observation.comparability is ComparisonComparabilityV1.NOT_COMPARABLE:
        return TreatmentQualityResultV1.NOT_COMPARABLE
    if observation.treatment_availability is TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE:
        return TreatmentQualityResultV1.UNAVAILABLE
    expected = _EXPECTED_RANK.get(human_label.expected_handling)
    actual = _TREATMENT_RANK.get(observation.treatment_decision)
    if expected is None:
        return TreatmentQualityResultV1.INSUFFICIENT_LABEL
    if actual is None:
        return TreatmentQualityResultV1.UNAVAILABLE
    if actual == expected:
        return TreatmentQualityResultV1.CORRECT
    if actual > expected:
        return TreatmentQualityResultV1.TOO_RESTRICTIVE
    return TreatmentQualityResultV1.TOO_PERMISSIVE


def _false_block(
    human_label: ShadowHumanLabelEvidenceV1,
    control: ControlQualityResultV1,
    treatment: TreatmentQualityResultV1,
) -> FalseBlockClassificationV1:
    if human_label.review_status is LabelReviewStatusV1.INSUFFICIENT_EVIDENCE:
        return FalseBlockClassificationV1.INSUFFICIENT_LABEL
    if human_label.event_materiality is not EventMaterialityV1.MATERIAL:
        return FalseBlockClassificationV1.NOT_APPLICABLE
    if (
        human_label.expected_handling is ExpectedHandlingV1.ALLOW
        and (
            control is ControlQualityResultV1.TOO_RESTRICTIVE
            or treatment is TreatmentQualityResultV1.TOO_RESTRICTIVE
        )
    ):
        return FalseBlockClassificationV1.FALSE_BLOCK
    return FalseBlockClassificationV1.NOT_FALSE_BLOCK


def _missed_event(
    human_label: ShadowHumanLabelEvidenceV1,
    control: ControlQualityResultV1,
    treatment: TreatmentQualityResultV1,
) -> MissedMaterialEventClassificationV1:
    if human_label.review_status is LabelReviewStatusV1.INSUFFICIENT_EVIDENCE:
        return MissedMaterialEventClassificationV1.INSUFFICIENT_LABEL
    if human_label.event_materiality is not EventMaterialityV1.MATERIAL:
        return MissedMaterialEventClassificationV1.NOT_APPLICABLE
    if (
        human_label.expected_handling is ExpectedHandlingV1.BLOCK
        and (
            control is ControlQualityResultV1.TOO_PERMISSIVE
            or treatment is TreatmentQualityResultV1.TOO_PERMISSIVE
        )
    ):
        return MissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
    return MissedMaterialEventClassificationV1.NOT_MISSED


def _materiality_quality(
    human_label: ShadowHumanLabelEvidenceV1,
    false_block: FalseBlockClassificationV1,
    missed_event: MissedMaterialEventClassificationV1,
    control: ControlQualityResultV1,
    treatment: TreatmentQualityResultV1,
) -> MaterialityQualityResultV1:
    if human_label.review_status is LabelReviewStatusV1.INSUFFICIENT_EVIDENCE:
        return MaterialityQualityResultV1.INSUFFICIENT_LABEL
    if human_label.event_materiality is EventMaterialityV1.MATERIAL:
        if false_block is FalseBlockClassificationV1.FALSE_BLOCK:
            return MaterialityQualityResultV1.FALSE_BLOCK
        if (
            missed_event
            is MissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
        ):
            return MaterialityQualityResultV1.MISSED_MATERIAL_EVENT
        return MaterialityQualityResultV1.CORRECT_MATERIAL_EVENT_HANDLING
    if (
        human_label.event_materiality is EventMaterialityV1.NON_MATERIAL
        and human_label.expected_handling is ExpectedHandlingV1.BLOCK
        and (
            control is ControlQualityResultV1.CORRECT
            or treatment is TreatmentQualityResultV1.CORRECT
        )
    ):
        return MaterialityQualityResultV1.CORRECT_NON_MATERIAL_SUPPRESSION
    return MaterialityQualityResultV1.NOT_APPLICABLE


def _mapping_quality(
    human_label: ShadowHumanLabelEvidenceV1,
) -> MappingQualityResultV1:
    return {
        EntityMappingCorrectnessV1.CORRECT: MappingQualityResultV1.CORRECT,
        EntityMappingCorrectnessV1.INCORRECT: MappingQualityResultV1.INCORRECT,
        EntityMappingCorrectnessV1.UNAVAILABLE: MappingQualityResultV1.UNAVAILABLE,
    }[human_label.mapping_correctness]


def _escalation_necessity(
    observation: ShadowComparativeObservationV1,
    human_label: ShadowHumanLabelEvidenceV1,
) -> EscalationNecessityV1:
    if human_label.review_status is LabelReviewStatusV1.INSUFFICIENT_EVIDENCE:
        return EscalationNecessityV1.INSUFFICIENT_LABEL
    if observation.original_treatment_route == "L0":
        return EscalationNecessityV1.NOT_ESCALATED
    if observation.original_treatment_route == "L1_TO_L2":
        if (
            observation.unresolved_ambiguity
            or observation.structured_disagreement
            in {
                StructuredProviderDisagreementV1.PARTIAL_DISAGREEMENT,
                StructuredProviderDisagreementV1.COMPLETE_DISAGREEMENT,
                StructuredProviderDisagreementV1.UNRESOLVED,
            }
        ):
            return EscalationNecessityV1.NECESSARY
        return EscalationNecessityV1.UNNECESSARY
    return EscalationNecessityV1.INDETERMINATE


class ShadowQualityEvaluatorV1:
    """Stateless evaluator over immutable observation and label evidence."""

    __slots__ = ()

    def evaluate(
        self, plan: ShadowQualityEvaluationPlanV1
    ) -> ShadowQualityObservationV1:
        if type(plan) is not ShadowQualityEvaluationPlanV1:
            raise ShadowQualityEvaluationValidationError(
                "invalid quality evaluation plan"
            )
        observation = plan.comparative_observation
        human_label = plan.human_label
        label_usable = human_label.review_status is LabelReviewStatusV1.REVIEWED
        control = _control_quality(observation, human_label)
        treatment = _treatment_quality(observation, human_label)
        false_block = _false_block(human_label, control, treatment)
        missed_event = _missed_event(human_label, control, treatment)
        materiality = _materiality_quality(
            human_label,
            false_block,
            missed_event,
            control,
            treatment,
        )
        mapping = _mapping_quality(human_label)
        escalation = _escalation_necessity(observation, human_label)
        if human_label.review_status is LabelReviewStatusV1.INSUFFICIENT_EVIDENCE:
            comparability = QualityComparabilityV1.INSUFFICIENT_LABEL
        elif (
            observation.treatment_availability
            is TreatmentAvailabilityV1.TERMINAL_UNAVAILABLE
        ):
            comparability = (
                QualityComparabilityV1.TERMINAL_TREATMENT_UNAVAILABLE
            )
        elif observation.comparability is ComparisonComparabilityV1.NOT_COMPARABLE:
            comparability = QualityComparabilityV1.NOT_COMPARABLE
        else:
            comparability = QualityComparabilityV1.COMPARABLE
        reasons = ("EVENT_QUALITY_EVALUATED",)
        return ShadowQualityObservationV1(
            schema_version="phase11-shadow-quality-observation-v1",
            quality_observation_id=None,
            quality_plan_id=plan.identity,
            comparative_observation_id=observation.identity,
            label_id=human_label.identity,
            candidate_id=observation.candidate_id,
            event_id=observation.event_id,
            entity_id=human_label.entity_id,
            locked_baseline_commit=observation.locked_baseline_commit,
            original_treatment_route=observation.original_treatment_route,
            treatment_availability=observation.treatment_availability,
            control_decision=observation.control_decision,
            treatment_decision=observation.treatment_decision,
            terminal_status=observation.terminal_status,
            label_usable=label_usable,
            event_materiality=human_label.event_materiality,
            mapping_correctness=human_label.mapping_correctness,
            expected_handling=human_label.expected_handling,
            quality_comparability=comparability,
            materiality_quality=materiality,
            mapping_quality=mapping,
            control_quality=control,
            treatment_quality=treatment,
            false_block=false_block,
            missed_material_event=missed_event,
            escalation_necessity=escalation,
            evaluated_at=plan.evaluated_at,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )


__all__ = [
    "ControlQualityResultV1",
    "EntityMappingCorrectnessV1",
    "EscalationNecessityV1",
    "EventMaterialityV1",
    "ExpectedHandlingV1",
    "FalseBlockClassificationV1",
    "LabelReviewStatusV1",
    "MappingQualityResultV1",
    "MaterialityQualityResultV1",
    "MissedMaterialEventClassificationV1",
    "QualityComparabilityV1",
    "ShadowHumanLabelEvidenceV1",
    "ShadowQualityEvaluationPlanV1",
    "ShadowQualityEvaluationValidationError",
    "ShadowQualityEvaluatorV1",
    "ShadowQualityObservationV1",
    "TreatmentQualityResultV1",
    "canonical_json_bytes",
    "lowercase_sha256",
]
