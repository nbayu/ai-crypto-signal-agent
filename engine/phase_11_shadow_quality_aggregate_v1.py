"""Deterministic aggregation of immutable Phase 11 quality observations.

This module consumes only evidence already committed to
``ShadowQualityObservationV1`` children.  It has no operational dependencies
and grants no execution or publication authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from engine.phase_11_finalization_evidence_bridge_v1 import (
    ShadowTerminalRecordStatusV1,
)
from engine.phase_11_shadow_comparative_evaluator_v1 import (
    LOCKED_PHASE09_BASELINE,
    TreatmentAvailabilityV1,
)
from engine.phase_11_shadow_quality_evaluator_v1 import (
    ControlQualityResultV1,
    EscalationNecessityV1,
    EventMaterialityV1,
    FalseBlockClassificationV1,
    MappingQualityResultV1,
    MaterialityQualityResultV1,
    MissedMaterialEventClassificationV1,
    ShadowQualityObservationV1,
    TreatmentQualityResultV1,
)


_UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_RATE_SCALE = Decimal("0.0000000001")
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"
_ROUTES = ("L0", "L1", "L2", "L1_TO_L2")


class ShadowQualityAggregationValidationError(ValueError):
    """Raised when aggregate quality evidence is inconsistent."""


class QualityAggregationScopeV1(StrEnum):
    QUALITY_OBSERVATION_SET = "QUALITY_OBSERVATION_SET"


class QualityCoverageStatusV1(StrEnum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class QualityAggregateRateAvailabilityV1(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowQualityAggregationValidationError(
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
    """Return canonical UTF-8 JSON bytes for aggregate quality evidence."""

    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def lowercase_sha256(value: Any) -> str:
    """Return a lowercase SHA-256 over canonical aggregate evidence."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _identity(material: Any, supplied: Any, label: str) -> str:
    expected = lowercase_sha256(material)
    if supplied is None:
        return expected
    if type(supplied) is not str or not _HASH.fullmatch(supplied):
        raise ShadowQualityAggregationValidationError(f"invalid {label}")
    if supplied != expected:
        raise ShadowQualityAggregationValidationError(
            f"{label} does not match canonical evidence"
        )
    return supplied


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ShadowQualityAggregationValidationError(
                f"invalid {label}"
            ) from exc
    else:
        raise ShadowQualityAggregationValidationError(f"invalid {label}")
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or parsed.utcoffset().total_seconds() != 0
    ):
        raise ShadowQualityAggregationValidationError(
            f"{label} must be explicit UTC"
        )
    return parsed.astimezone(_UTC).isoformat().replace("+00:00", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ShadowQualityAggregationValidationError(
            "invalid aggregate quality reason codes"
        )
    reasons = tuple(value)
    if (
        not reasons
        or any(type(item) is not str or not _REASON.fullmatch(item) for item in reasons)
        or tuple(sorted(set(reasons))) != reasons
    ):
        raise ShadowQualityAggregationValidationError(
            "invalid aggregate quality reason codes"
        )
    return reasons


def _non_negative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ShadowQualityAggregationValidationError(f"invalid {label}")
    return value


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowQualityAggregationValidationError(
            "aggregate quality evidence must have zero effect"
        )


_COVERAGE_FIELDS = frozenset(
    {
        "schema_version",
        "coverage_plan_id",
        "minimum_total_quality_observations",
        "minimum_usable_labels",
        "minimum_material_events",
        "minimum_non_material_events",
        "minimum_clean_treatments",
        "minimum_terminal_treatments",
        "minimum_l0",
        "minimum_l1",
        "minimum_direct_l2",
        "minimum_l1_to_l2",
        "reason_codes",
    }
)

_COVERAGE_TARGET_FIELDS = (
    "minimum_total_quality_observations",
    "minimum_usable_labels",
    "minimum_material_events",
    "minimum_non_material_events",
    "minimum_clean_treatments",
    "minimum_terminal_treatments",
    "minimum_l0",
    "minimum_l1",
    "minimum_direct_l2",
    "minimum_l1_to_l2",
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowQualityCoveragePlanV1:
    schema_version: str
    coverage_plan_id: str
    minimum_total_quality_observations: int
    minimum_usable_labels: int
    minimum_material_events: int
    minimum_non_material_events: int
    minimum_clean_treatments: int
    minimum_terminal_treatments: int
    minimum_l0: int
    minimum_l1: int
    minimum_direct_l2: int
    minimum_l1_to_l2: int
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _COVERAGE_FIELDS:
            raise ShadowQualityAggregationValidationError(
                "invalid quality coverage-plan fields"
            )
        if values["schema_version"] != "phase11-shadow-quality-coverage-plan-v1":
            raise ShadowQualityAggregationValidationError(
                "unsupported quality coverage-plan schema"
            )
        targets = {
            name: _non_negative_integer(values[name], name)
            for name in _COVERAGE_TARGET_FIELDS
        }
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            **targets,
            "reason_codes": reasons,
        }
        coverage_plan_id = _identity(
            material, values["coverage_plan_id"], "coverage_plan_id"
        )
        normalized = {
            **values,
            **targets,
            "coverage_plan_id": coverage_plan_id,
            "reason_codes": reasons,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.coverage_plan_id


_SET_FIELDS = frozenset(
    {
        "schema_version",
        "quality_observation_set_id",
        "observations",
        "window_start",
        "window_end",
        "locked_baseline_commit",
        "reason_codes",
    }
)


def _validate_child(child: ShadowQualityObservationV1) -> None:
    if child.locked_baseline_commit != LOCKED_PHASE09_BASELINE:
        raise ShadowQualityAggregationValidationError(
            "quality observation has a foreign baseline"
        )
    _zero_effect(child.production_effect, child.zero_production_effect_proof)
    if type(child.label_usable) is not bool:
        raise ShadowQualityAggregationValidationError(
            "invalid label usability evidence"
        )
    exact_enums = (
        (child.event_materiality, EventMaterialityV1),
        (child.materiality_quality, MaterialityQualityResultV1),
        (child.mapping_quality, MappingQualityResultV1),
        (child.control_quality, ControlQualityResultV1),
        (child.treatment_quality, TreatmentQualityResultV1),
        (child.false_block, FalseBlockClassificationV1),
        (child.missed_material_event, MissedMaterialEventClassificationV1),
        (child.escalation_necessity, EscalationNecessityV1),
        (child.treatment_availability, TreatmentAvailabilityV1),
    )
    if any(type(value) is not expected for value, expected in exact_enums):
        raise ShadowQualityAggregationValidationError(
            "invalid categorical quality evidence"
        )
    if child.original_treatment_route not in _ROUTES:
        raise ShadowQualityAggregationValidationError(
            "invalid quality-observation route"
        )
    if child.treatment_availability is TreatmentAvailabilityV1.AVAILABLE:
        if child.terminal_status is not None or child.treatment_decision is None:
            raise ShadowQualityAggregationValidationError(
                "invalid clean quality-observation treatment evidence"
            )
    elif (
        type(child.terminal_status) is not ShadowTerminalRecordStatusV1
        or child.treatment_decision is not None
        or child.treatment_quality is not TreatmentQualityResultV1.UNAVAILABLE
    ):
        raise ShadowQualityAggregationValidationError(
            "invalid terminal quality-observation treatment evidence"
        )


@dataclass(frozen=True, init=False, slots=True)
class ShadowQualityObservationSetV1:
    schema_version: str
    quality_observation_set_id: str
    observations: tuple[ShadowQualityObservationV1, ...]
    window_start: str
    window_end: str
    locked_baseline_commit: str
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _SET_FIELDS:
            raise ShadowQualityAggregationValidationError(
                "invalid quality observation-set fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-quality-observation-set-v1"
        ):
            raise ShadowQualityAggregationValidationError(
                "unsupported quality observation-set schema"
            )
        supplied = values["observations"]
        if (
            type(supplied) is not tuple
            or not supplied
            or any(type(child) is not ShadowQualityObservationV1 for child in supplied)
        ):
            raise ShadowQualityAggregationValidationError(
                "invalid quality observations"
            )
        if values["locked_baseline_commit"] != LOCKED_PHASE09_BASELINE:
            raise ShadowQualityAggregationValidationError(
                "invalid locked Phase 09 baseline"
            )
        window_start = _timestamp(values["window_start"], "window_start")
        window_end = _timestamp(values["window_end"], "window_end")
        if _parsed(window_start) > _parsed(window_end):
            raise ShadowQualityAggregationValidationError(
                "invalid quality evaluation window"
            )
        observations = tuple(sorted(supplied, key=lambda child: child.identity))
        identities: set[str] = set()
        comparison_keys: set[tuple[str, str, str]] = set()
        for child in observations:
            _validate_child(child)
            if not (
                _parsed(window_start)
                <= _parsed(child.evaluated_at)
                <= _parsed(window_end)
            ):
                raise ShadowQualityAggregationValidationError(
                    "quality observation is outside the evaluation window"
                )
            if child.identity in identities:
                raise ShadowQualityAggregationValidationError(
                    "duplicate quality-observation identity"
                )
            comparison_key = (
                child.candidate_id,
                child.event_id,
                child.label_id,
            )
            if comparison_key in comparison_keys:
                raise ShadowQualityAggregationValidationError(
                    "duplicate candidate/event/label comparison key"
                )
            identities.add(child.identity)
            comparison_keys.add(comparison_key)
        reasons = _reasons(values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "quality_observation_ids": tuple(
                child.identity for child in observations
            ),
            "window_start": window_start,
            "window_end": window_end,
            "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
            "reason_codes": reasons,
        }
        observation_set_id = _identity(
            material,
            values["quality_observation_set_id"],
            "quality_observation_set_id",
        )
        normalized = {
            **values,
            "quality_observation_set_id": observation_set_id,
            "observations": observations,
            "window_start": window_start,
            "window_end": window_end,
            "locked_baseline_commit": LOCKED_PHASE09_BASELINE,
            "reason_codes": reasons,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.quality_observation_set_id


_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "aggregate_quality_plan_id",
        "quality_observation_set",
        "coverage_plan",
        "generated_at",
        "aggregation_scope",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowAggregateQualityPlanV1:
    schema_version: str
    aggregate_quality_plan_id: str
    quality_observation_set: ShadowQualityObservationSetV1
    coverage_plan: ShadowQualityCoveragePlanV1
    generated_at: str
    aggregation_scope: QualityAggregationScopeV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PLAN_FIELDS:
            raise ShadowQualityAggregationValidationError(
                "invalid aggregate quality-plan fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-aggregate-quality-plan-v1"
        ):
            raise ShadowQualityAggregationValidationError(
                "unsupported aggregate quality-plan schema"
            )
        observation_set = values["quality_observation_set"]
        coverage_plan = values["coverage_plan"]
        if (
            type(observation_set) is not ShadowQualityObservationSetV1
            or type(coverage_plan) is not ShadowQualityCoveragePlanV1
            or type(values["aggregation_scope"]) is not QualityAggregationScopeV1
            or values["aggregation_scope"]
            is not QualityAggregationScopeV1.QUALITY_OBSERVATION_SET
        ):
            raise ShadowQualityAggregationValidationError(
                "invalid aggregate quality-plan evidence"
            )
        generated_at = _timestamp(values["generated_at"], "generated_at")
        if _parsed(generated_at) < _parsed(observation_set.window_end):
            raise ShadowQualityAggregationValidationError(
                "generated_at precedes quality evidence"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "quality_observation_set_id": observation_set.identity,
            "coverage_plan_id": coverage_plan.identity,
            "generated_at": generated_at,
            "aggregation_scope": values["aggregation_scope"].value,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        plan_id = _identity(
            material,
            values["aggregate_quality_plan_id"],
            "aggregate_quality_plan_id",
        )
        normalized = {
            **values,
            "aggregate_quality_plan_id": plan_id,
            "generated_at": generated_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.aggregate_quality_plan_id


@dataclass(frozen=True, slots=True)
class ShadowQualityRateEvidenceV1:
    numerator: int
    denominator: int
    availability: QualityAggregateRateAvailabilityV1
    value: Decimal | None

    def __post_init__(self) -> None:
        numerator = _non_negative_integer(self.numerator, "rate numerator")
        denominator = _non_negative_integer(self.denominator, "rate denominator")
        if numerator > denominator:
            raise ShadowQualityAggregationValidationError(
                "rate numerator exceeds denominator"
            )
        if denominator == 0:
            if (
                numerator != 0
                or self.availability
                is not QualityAggregateRateAvailabilityV1.UNAVAILABLE
                or self.value is not None
            ):
                raise ShadowQualityAggregationValidationError(
                    "zero-denominator rate must be unavailable"
                )
        elif (
            self.availability
            is not QualityAggregateRateAvailabilityV1.AVAILABLE
            or type(self.value) is not Decimal
            or self.value
            != (Decimal(numerator) / Decimal(denominator)).quantize(
                _RATE_SCALE, rounding=ROUND_HALF_EVEN
            )
        ):
            raise ShadowQualityAggregationValidationError(
                "invalid available rate evidence"
            )


@dataclass(frozen=True, slots=True)
class ShadowQualityCoverageResultV1:
    target: str
    required: int
    observed: int
    status: QualityCoverageStatusV1
    coverage_result_id: str

    @property
    def identity(self) -> str:
        return self.coverage_result_id


@dataclass(frozen=True, slots=True)
class ShadowAggregateQualityReportV1:
    schema_version: str
    aggregate_quality_report_id: str
    aggregate_quality_plan_id: str
    quality_observation_set_id: str
    coverage_plan_id: str
    locked_baseline_commit: str
    window_start: str
    window_end: str
    generated_at: str
    total_quality_observation_count: int
    usable_label_count: int
    insufficient_label_count: int
    clean_treatment_count: int
    terminal_treatment_count: int
    route_counts: Mapping[str, int]
    materiality_quality_counts: Mapping[MaterialityQualityResultV1, int]
    mapping_quality_counts: Mapping[MappingQualityResultV1, int]
    control_quality_counts: Mapping[ControlQualityResultV1, int]
    treatment_quality_counts: Mapping[TreatmentQualityResultV1, int]
    false_block_counts: Mapping[FalseBlockClassificationV1, int]
    missed_event_counts: Mapping[MissedMaterialEventClassificationV1, int]
    escalation_counts: Mapping[EscalationNecessityV1, int]
    terminal_status_counts: Mapping[str, int]
    usable_label_coverage_rate: ShadowQualityRateEvidenceV1
    materiality_handling_correctness_rate: ShadowQualityRateEvidenceV1
    mapping_correctness_rate: ShadowQualityRateEvidenceV1
    control_correctness_rate: ShadowQualityRateEvidenceV1
    treatment_correctness_rate: ShadowQualityRateEvidenceV1
    false_block_rate: ShadowQualityRateEvidenceV1
    missed_material_event_rate: ShadowQualityRateEvidenceV1
    unnecessary_escalation_rate: ShadowQualityRateEvidenceV1
    terminal_treatment_unavailable_rate: ShadowQualityRateEvidenceV1
    coverage_results: tuple[ShadowQualityCoverageResultV1, ...]
    coverage_results_by_target: Mapping[str, ShadowQualityCoverageResultV1]
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.aggregate_quality_report_id


def _rate(numerator: int, denominator: int) -> ShadowQualityRateEvidenceV1:
    if denominator == 0:
        return ShadowQualityRateEvidenceV1(
            numerator=0,
            denominator=0,
            availability=QualityAggregateRateAvailabilityV1.UNAVAILABLE,
            value=None,
        )
    return ShadowQualityRateEvidenceV1(
        numerator=numerator,
        denominator=denominator,
        availability=QualityAggregateRateAvailabilityV1.AVAILABLE,
        value=(Decimal(numerator) / Decimal(denominator)).quantize(
            _RATE_SCALE, rounding=ROUND_HALF_EVEN
        ),
    )


def _enum_counts(
    observations: tuple[ShadowQualityObservationV1, ...],
    field_name: str,
    enum_type: type[StrEnum],
) -> dict[StrEnum, int]:
    return {
        member: sum(getattr(child, field_name) is member for child in observations)
        for member in enum_type
    }


def _coverage_result(
    target: str,
    required: int,
    observed: int,
) -> ShadowQualityCoverageResultV1:
    status = (
        QualityCoverageStatusV1.MET
        if observed >= required
        else QualityCoverageStatusV1.NOT_MET
    )
    material = {
        "target": target,
        "required": required,
        "observed": observed,
        "status": status.value,
    }
    return ShadowQualityCoverageResultV1(
        target=target,
        required=required,
        observed=observed,
        status=status,
        coverage_result_id=lowercase_sha256(material),
    )


def _count_material(value: Mapping[Any, int]) -> dict[str, int]:
    return {
        item.value if isinstance(item, StrEnum) else str(item): count
        for item, count in value.items()
    }


def _rate_material(value: ShadowQualityRateEvidenceV1) -> dict[str, Any]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "availability": value.availability.value,
        "value": value.value,
    }


class ShadowQualityAggregatorV1:
    """Stateless aggregator over immutable event-level quality evidence."""

    __slots__ = ()

    def aggregate(
        self,
        plan: ShadowAggregateQualityPlanV1,
    ) -> ShadowAggregateQualityReportV1:
        if type(plan) is not ShadowAggregateQualityPlanV1:
            raise ShadowQualityAggregationValidationError(
                "invalid aggregate quality plan"
            )
        observations = plan.quality_observation_set.observations
        total = len(observations)
        usable = sum(child.label_usable for child in observations)
        clean = sum(
            child.treatment_availability is TreatmentAvailabilityV1.AVAILABLE
            for child in observations
        )
        terminal = total - clean
        route_counts = {
            route: sum(
                child.original_treatment_route == route for child in observations
            )
            for route in _ROUTES
        }
        materiality_counts = _enum_counts(
            observations,
            "materiality_quality",
            MaterialityQualityResultV1,
        )
        mapping_counts = _enum_counts(
            observations,
            "mapping_quality",
            MappingQualityResultV1,
        )
        control_counts = _enum_counts(
            observations,
            "control_quality",
            ControlQualityResultV1,
        )
        treatment_counts = _enum_counts(
            observations,
            "treatment_quality",
            TreatmentQualityResultV1,
        )
        false_block_counts = _enum_counts(
            observations,
            "false_block",
            FalseBlockClassificationV1,
        )
        missed_counts = _enum_counts(
            observations,
            "missed_material_event",
            MissedMaterialEventClassificationV1,
        )
        escalation_counts = _enum_counts(
            observations,
            "escalation_necessity",
            EscalationNecessityV1,
        )
        terminal_status_counts = {
            status.value: sum(child.terminal_status is status for child in observations)
            for status in ShadowTerminalRecordStatusV1
        }

        materiality_correct = (
            materiality_counts[
                MaterialityQualityResultV1.CORRECT_MATERIAL_EVENT_HANDLING
            ]
            + materiality_counts[
                MaterialityQualityResultV1.CORRECT_NON_MATERIAL_SUPPRESSION
            ]
        )
        materiality_denominator = sum(
            count
            for result, count in materiality_counts.items()
            if result
            not in {
                MaterialityQualityResultV1.INSUFFICIENT_LABEL,
                MaterialityQualityResultV1.NOT_APPLICABLE,
            }
        )
        mapping_denominator = (
            mapping_counts[MappingQualityResultV1.CORRECT]
            + mapping_counts[MappingQualityResultV1.INCORRECT]
        )
        control_denominator = sum(
            control_counts[result]
            for result in (
                ControlQualityResultV1.CORRECT,
                ControlQualityResultV1.TOO_RESTRICTIVE,
                ControlQualityResultV1.TOO_PERMISSIVE,
            )
        )
        treatment_denominator = sum(
            treatment_counts[result]
            for result in (
                TreatmentQualityResultV1.CORRECT,
                TreatmentQualityResultV1.TOO_RESTRICTIVE,
                TreatmentQualityResultV1.TOO_PERMISSIVE,
            )
        )
        false_block_denominator = (
            false_block_counts[FalseBlockClassificationV1.FALSE_BLOCK]
            + false_block_counts[FalseBlockClassificationV1.NOT_FALSE_BLOCK]
        )
        missed_denominator = (
            missed_counts[
                MissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
            ]
            + missed_counts[
                MissedMaterialEventClassificationV1.NOT_MISSED
            ]
        )
        determinate_escalations = tuple(
            child
            for child in observations
            if child.original_treatment_route == "L1_TO_L2"
            and child.escalation_necessity
            in {
                EscalationNecessityV1.NECESSARY,
                EscalationNecessityV1.UNNECESSARY,
            }
        )
        escalation_denominator = len(determinate_escalations)
        unnecessary_escalations = sum(
            child.escalation_necessity is EscalationNecessityV1.UNNECESSARY
            for child in determinate_escalations
        )

        rates = {
            "usable_label_coverage": _rate(usable, total),
            "materiality_handling_correctness": _rate(
                materiality_correct, materiality_denominator
            ),
            "mapping_correctness": _rate(
                mapping_counts[MappingQualityResultV1.CORRECT],
                mapping_denominator,
            ),
            "control_correctness": _rate(
                control_counts[ControlQualityResultV1.CORRECT],
                control_denominator,
            ),
            "treatment_correctness": _rate(
                treatment_counts[TreatmentQualityResultV1.CORRECT],
                treatment_denominator,
            ),
            "false_block": _rate(
                false_block_counts[FalseBlockClassificationV1.FALSE_BLOCK],
                false_block_denominator,
            ),
            "missed_material_event": _rate(
                missed_counts[
                    MissedMaterialEventClassificationV1.MISSED_MATERIAL_EVENT
                ],
                missed_denominator,
            ),
            "unnecessary_escalation": _rate(
                unnecessary_escalations,
                escalation_denominator,
            ),
            "terminal_treatment_unavailable": _rate(terminal, total),
        }

        material_event_count = sum(
            child.event_materiality is EventMaterialityV1.MATERIAL
            for child in observations
        )
        non_material_event_count = sum(
            child.event_materiality is EventMaterialityV1.NON_MATERIAL
            for child in observations
        )
        coverage = plan.coverage_plan
        coverage_pairs = (
            (
                "TOTAL_QUALITY_OBSERVATIONS",
                coverage.minimum_total_quality_observations,
                total,
            ),
            (
                "USABLE_LABELS",
                coverage.minimum_usable_labels,
                usable,
            ),
            (
                "MATERIAL_EVENTS",
                coverage.minimum_material_events,
                material_event_count,
            ),
            (
                "NON_MATERIAL_EVENTS",
                coverage.minimum_non_material_events,
                non_material_event_count,
            ),
            (
                "CLEAN_TREATMENTS",
                coverage.minimum_clean_treatments,
                clean,
            ),
            (
                "TERMINAL_TREATMENTS",
                coverage.minimum_terminal_treatments,
                terminal,
            ),
            ("L0", coverage.minimum_l0, route_counts["L0"]),
            ("L1", coverage.minimum_l1, route_counts["L1"]),
            ("DIRECT_L2", coverage.minimum_direct_l2, route_counts["L2"]),
            (
                "L1_TO_L2",
                coverage.minimum_l1_to_l2,
                route_counts["L1_TO_L2"],
            ),
        )
        coverage_results = tuple(
            _coverage_result(target, required, observed)
            for target, required, observed in coverage_pairs
        )
        coverage_by_target = {
            result.target: result for result in coverage_results
        }
        reasons = ("AGGREGATE_QUALITY_EVIDENCE_COMPUTED",)
        observation_set = plan.quality_observation_set
        material = {
            "schema_version": "phase11-shadow-aggregate-quality-report-v1",
            "aggregate_quality_plan_id": plan.identity,
            "quality_observation_set_id": observation_set.identity,
            "coverage_plan_id": coverage.identity,
            "locked_baseline_commit": observation_set.locked_baseline_commit,
            "window_start": observation_set.window_start,
            "window_end": observation_set.window_end,
            "generated_at": plan.generated_at,
            "counts": {
                "total_quality_observations": total,
                "usable_labels": usable,
                "insufficient_labels": total - usable,
                "clean_treatments": clean,
                "terminal_treatments": terminal,
                "routes": route_counts,
                "materiality_quality": _count_material(materiality_counts),
                "mapping_quality": _count_material(mapping_counts),
                "control_quality": _count_material(control_counts),
                "treatment_quality": _count_material(treatment_counts),
                "false_block": _count_material(false_block_counts),
                "missed_material_event": _count_material(missed_counts),
                "escalation_necessity": _count_material(escalation_counts),
                "terminal_status": terminal_status_counts,
            },
            "rates": {
                name: _rate_material(rate) for name, rate in rates.items()
            },
            "coverage_results": tuple(
                {
                    "target": result.target,
                    "required": result.required,
                    "observed": result.observed,
                    "status": result.status.value,
                    "coverage_result_id": result.identity,
                }
                for result in coverage_results
            ),
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        report_id = lowercase_sha256(material)
        return ShadowAggregateQualityReportV1(
            schema_version=material["schema_version"],
            aggregate_quality_report_id=report_id,
            aggregate_quality_plan_id=plan.identity,
            quality_observation_set_id=observation_set.identity,
            coverage_plan_id=coverage.identity,
            locked_baseline_commit=observation_set.locked_baseline_commit,
            window_start=observation_set.window_start,
            window_end=observation_set.window_end,
            generated_at=plan.generated_at,
            total_quality_observation_count=total,
            usable_label_count=usable,
            insufficient_label_count=total - usable,
            clean_treatment_count=clean,
            terminal_treatment_count=terminal,
            route_counts=MappingProxyType(route_counts),
            materiality_quality_counts=MappingProxyType(materiality_counts),
            mapping_quality_counts=MappingProxyType(mapping_counts),
            control_quality_counts=MappingProxyType(control_counts),
            treatment_quality_counts=MappingProxyType(treatment_counts),
            false_block_counts=MappingProxyType(false_block_counts),
            missed_event_counts=MappingProxyType(missed_counts),
            escalation_counts=MappingProxyType(escalation_counts),
            terminal_status_counts=MappingProxyType(terminal_status_counts),
            usable_label_coverage_rate=rates["usable_label_coverage"],
            materiality_handling_correctness_rate=rates[
                "materiality_handling_correctness"
            ],
            mapping_correctness_rate=rates["mapping_correctness"],
            control_correctness_rate=rates["control_correctness"],
            treatment_correctness_rate=rates["treatment_correctness"],
            false_block_rate=rates["false_block"],
            missed_material_event_rate=rates["missed_material_event"],
            unnecessary_escalation_rate=rates["unnecessary_escalation"],
            terminal_treatment_unavailable_rate=rates[
                "terminal_treatment_unavailable"
            ],
            coverage_results=coverage_results,
            coverage_results_by_target=MappingProxyType(coverage_by_target),
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )


__all__ = [
    "QualityAggregateRateAvailabilityV1",
    "QualityAggregationScopeV1",
    "QualityCoverageStatusV1",
    "ShadowAggregateQualityPlanV1",
    "ShadowAggregateQualityReportV1",
    "ShadowQualityAggregationValidationError",
    "ShadowQualityAggregatorV1",
    "ShadowQualityCoveragePlanV1",
    "ShadowQualityCoverageResultV1",
    "ShadowQualityObservationSetV1",
    "ShadowQualityRateEvidenceV1",
    "canonical_json_bytes",
    "lowercase_sha256",
]
