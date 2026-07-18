"""Deterministic aggregate-only Phase 11 exit-gate evidence reconciliation.

The contracts in this module reconcile already-created immutable aggregate
reports.  They grant no owner, budget, provider, promotion, persistence,
publication, later-phase, or production authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from engine.phase_11_shadow_alternative_arm_aggregate_v1 import (
    ShadowAggregateAlternativeArmReportV1,
)
from engine.phase_11_shadow_alternative_arm_evaluator_v1 import (
    AlternativeArmIdentityV1,
)
from engine.phase_11_shadow_comparative_aggregate_v1 import (
    ShadowAggregateComparativeReportV1,
)
from engine.phase_11_shadow_cost_projection_v1 import (
    ShadowCostProjectionReportV1,
    ShadowOwnerBudgetGateStatusV1,
)
from engine.phase_11_shadow_quality_aggregate_v1 import (
    ShadowAggregateQualityReportV1,
)
from engine.phase_11_shadow_route_cost_evidence_v1 import (
    ShadowRouteCostAggregateReportV1,
)


_UTC = timezone.utc
_LOCKED_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_ROUTES = ("L0", "L1", "L2", "L1_TO_L2")


class ShadowPhase11ExitGateValidationError(ValueError):
    """Raised when exit-gate evidence is inconsistent."""


class ShadowPhase11ExitGateScopeV1(StrEnum):
    AGGREGATE_EVIDENCE_RECONCILIATION = "AGGREGATE_EVIDENCE_RECONCILIATION"


class ShadowPhase11CriterionStatusV1(StrEnum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ShadowPhase11EvidenceReadinessV1(StrEnum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"


class ShadowPhase11MechanicalReadinessV1(StrEnum):
    READY_FOR_OWNER_REVIEW = "READY_FOR_OWNER_REVIEW"
    NOT_READY = "NOT_READY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ShadowPhase11OwnerAcceptanceStatusV1(StrEnum):
    NOT_RECORDED = "NOT_RECORDED"


class ShadowPhase11LimitationsAcceptanceStatusV1(StrEnum):
    NOT_RECORDED = "NOT_RECORDED"


class ShadowPhase12RecommendationStatusV1(StrEnum):
    NOT_ISSUED = "NOT_ISSUED"


class ShadowPhase11ControlDomainV1(StrEnum):
    INTEGRITY = "INTEGRITY"
    AUTHORITY = "AUTHORITY"
    STATE = "STATE"
    SECURITY = "SECURITY"
    REPLAY = "REPLAY"
    BUDGET_CONTROL = "BUDGET_CONTROL"


class ShadowPhase11EvidenceDimensionV1(StrEnum):
    QUALITY = "QUALITY"
    LATENCY = "LATENCY"
    COST = "COST"
    FAIL_POLICY = "FAIL_POLICY"
    OPERATIONAL = "OPERATIONAL"


def _require_utc(name: str, value: Any) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() != _UTC.utcoffset(value)
    ):
        raise ShadowPhase11ExitGateValidationError(
            f"{name} must be an explicit UTC datetime"
        )
    return value


def _parse_utc(name: str, value: Any) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ShadowPhase11ExitGateValidationError(
            f"{name} must be a canonical UTC timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}") from error
    return _require_utc(name, parsed)


def _canonical(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowPhase11ExitGateValidationError(
                "canonical Decimal values must be finite"
            )
        return "0" if value == 0 else format(value.normalize(), "f")
    if isinstance(value, datetime):
        return _require_utc("canonical datetime", value).isoformat().replace(
            "+00:00", "Z"
        )
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShadowPhase11ExitGateValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes."""

    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    """Return a lowercase SHA-256 digest for exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11ExitGateValidationError(
            "sha256 input must be exact bytes"
        )
    return hashlib.sha256(value).hexdigest()


def _derived_identity(material: Any) -> str:
    return sha256_hex(canonical_json_bytes(material))


def _identity(material: Any, supplied: Any, name: str) -> str:
    derived = _derived_identity(material)
    if supplied is not None and (
        type(supplied) is not str
        or not _HASH.fullmatch(supplied)
        or supplied != derived
    ):
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
    return derived


def _nonnegative_integer(name: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ShadowPhase11ExitGateValidationError(
            f"{name} must be an exact non-negative integer"
        )
    return value


def _codes(name: str, value: Any, *, empty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ShadowPhase11ExitGateValidationError(
            f"{name} must be a tuple of deterministic codes"
        )
    if (not empty and not value) or any(
        type(item) is not str or not _CODE.fullmatch(item) for item in value
    ):
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
    if tuple(sorted(set(value))) != value:
        raise ShadowPhase11ExitGateValidationError(
            f"{name} must be sorted and unique"
        )
    return value


def _hashes(name: str, value: Any, *, empty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple or (not empty and not value):
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
    if any(type(item) is not str or not _HASH.fullmatch(item) for item in value):
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
    if len(set(value)) != len(value):
        raise ShadowPhase11ExitGateValidationError(f"duplicate {name}")
    return tuple(sorted(value))


def _strings(
    name: str,
    value: Any,
    *,
    allowed: frozenset[str] | None = None,
    empty: bool = False,
) -> tuple[str, ...]:
    if type(value) is not tuple or (not empty and not value):
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
    if any(type(item) is not str or not item for item in value):
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
    if len(set(value)) != len(value):
        raise ShadowPhase11ExitGateValidationError(f"duplicate {name}")
    if allowed is not None and any(item not in allowed for item in value):
        raise ShadowPhase11ExitGateValidationError(f"unknown {name}")
    return tuple(sorted(value))


def _enum_tuple(
    name: str,
    value: Any,
    enum_type: type[StrEnum],
    *,
    empty: bool = False,
) -> tuple[Any, ...]:
    if type(value) is not tuple or (not empty and not value):
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
    if any(type(item) is not enum_type for item in value):
        raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
    if len(set(value)) != len(value):
        raise ShadowPhase11ExitGateValidationError(f"duplicate {name}")
    order = {item: index for index, item in enumerate(enum_type)}
    return tuple(sorted(value, key=order.__getitem__))


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowPhase11ExitGateValidationError(
            "exit-gate evidence must prove zero production effect"
        )


def _baseline(value: Any) -> str:
    if (
        type(value) is not str
        or not _COMMIT.fullmatch(value)
        or value != _LOCKED_PHASE09_BASELINE
    ):
        raise ShadowPhase11ExitGateValidationError("invalid locked baseline")
    return value


_CRITERIA_FIELDS = frozenset(
    {
        "schema_version",
        "exit_gate_criteria_id",
        "required_coverage_targets",
        "required_event_classes",
        "required_route_classes",
        "required_alternative_arms",
        "required_comparison_dimensions",
        "permitted_guardrail_regressions",
        "critical_control_defect_maximum",
        "required_evidence_dimensions",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11ExitGateCriteriaV1:
    schema_version: str
    exit_gate_criteria_id: str
    required_coverage_targets: tuple[str, ...]
    required_event_classes: tuple[str, ...]
    required_route_classes: tuple[str, ...]
    required_alternative_arms: tuple[AlternativeArmIdentityV1, ...]
    required_comparison_dimensions: tuple[ShadowPhase11EvidenceDimensionV1, ...]
    permitted_guardrail_regressions: Decimal
    critical_control_defect_maximum: int
    required_evidence_dimensions: tuple[ShadowPhase11EvidenceDimensionV1, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _CRITERIA_FIELDS:
            raise ShadowPhase11ExitGateValidationError(
                "invalid exit-gate criteria fields"
            )
        if values["schema_version"] != "phase11-shadow-exit-gate-criteria-v1":
            raise ShadowPhase11ExitGateValidationError(
                "unsupported exit-gate criteria schema"
            )
        coverage = _strings("required_coverage_targets", values["required_coverage_targets"])
        events = _strings(
            "required_event_classes",
            values["required_event_classes"],
            allowed=frozenset({"MATERIAL", "NON_MATERIAL"}),
        )
        routes = _strings(
            "required_route_classes",
            values["required_route_classes"],
            allowed=frozenset(_ROUTES),
        )
        arms = _enum_tuple(
            "required_alternative_arms",
            values["required_alternative_arms"],
            AlternativeArmIdentityV1,
        )
        dimensions = _enum_tuple(
            "required_comparison_dimensions",
            values["required_comparison_dimensions"],
            ShadowPhase11EvidenceDimensionV1,
        )
        required_dimensions = _enum_tuple(
            "required_evidence_dimensions",
            values["required_evidence_dimensions"],
            ShadowPhase11EvidenceDimensionV1,
        )
        regression = values["permitted_guardrail_regressions"]
        if (
            type(regression) is not Decimal
            or not regression.is_finite()
            or regression < Decimal("0")
        ):
            raise ShadowPhase11ExitGateValidationError(
                "invalid permitted_guardrail_regressions"
            )
        maximum = _nonnegative_integer(
            "critical_control_defect_maximum",
            values["critical_control_defect_maximum"],
        )
        reasons = _codes("reason_codes", values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "required_coverage_targets": coverage,
            "required_event_classes": events,
            "required_route_classes": routes,
            "required_alternative_arms": arms,
            "required_comparison_dimensions": dimensions,
            "permitted_guardrail_regressions": regression,
            "critical_control_defect_maximum": maximum,
            "required_evidence_dimensions": required_dimensions,
            "reason_codes": reasons,
        }
        identity = _identity(
            material, values["exit_gate_criteria_id"], "exit_gate_criteria_id"
        )
        normalized = {**material, "exit_gate_criteria_id": identity}
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.exit_gate_criteria_id


_CONTROL_DOMAIN_FIELDS = frozenset(
    {
        "schema_version",
        "control_domain_evidence_id",
        "domain",
        "evidence_readiness",
        "critical_open_defect_count",
        "unresolved_noncritical_count",
        "evidence_references",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11ControlDomainEvidenceV1:
    schema_version: str
    control_domain_evidence_id: str
    domain: ShadowPhase11ControlDomainV1
    evidence_readiness: ShadowPhase11EvidenceReadinessV1
    critical_open_defect_count: int
    unresolved_noncritical_count: int
    evidence_references: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _CONTROL_DOMAIN_FIELDS:
            raise ShadowPhase11ExitGateValidationError(
                "invalid control-domain evidence fields"
            )
        if values["schema_version"] != "phase11-shadow-control-domain-evidence-v1":
            raise ShadowPhase11ExitGateValidationError(
                "unsupported control-domain evidence schema"
            )
        domain = values["domain"]
        readiness = values["evidence_readiness"]
        if type(domain) is not ShadowPhase11ControlDomainV1:
            raise ShadowPhase11ExitGateValidationError("invalid control domain")
        if type(readiness) is not ShadowPhase11EvidenceReadinessV1:
            raise ShadowPhase11ExitGateValidationError(
                "invalid control evidence readiness"
            )
        critical = _nonnegative_integer(
            "critical_open_defect_count", values["critical_open_defect_count"]
        )
        noncritical = _nonnegative_integer(
            "unresolved_noncritical_count", values["unresolved_noncritical_count"]
        )
        references = _hashes(
            "evidence_references",
            values["evidence_references"],
            empty=readiness
            in {
                ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE,
                ShadowPhase11EvidenceReadinessV1.UNAVAILABLE,
            },
        )
        reasons = _codes("reason_codes", values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "domain": domain,
            "evidence_readiness": readiness,
            "critical_open_defect_count": critical,
            "unresolved_noncritical_count": noncritical,
            "evidence_references": references,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["control_domain_evidence_id"],
            "control_domain_evidence_id",
        )
        normalized = {**material, "control_domain_evidence_id": identity}
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.control_domain_evidence_id


_ASSURANCE_FIELDS = frozenset(
    {
        "schema_version",
        "control_assurance_evidence_id",
        "locked_baseline_commit",
        "window_start",
        "window_end",
        "generated_at",
        "domain_evidence",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11ControlAssuranceEvidenceV1:
    schema_version: str
    control_assurance_evidence_id: str
    locked_baseline_commit: str
    window_start: datetime
    window_end: datetime
    generated_at: datetime
    domain_evidence: tuple[ShadowPhase11ControlDomainEvidenceV1, ...]
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _ASSURANCE_FIELDS:
            raise ShadowPhase11ExitGateValidationError(
                "invalid control-assurance fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-control-assurance-evidence-v1"
        ):
            raise ShadowPhase11ExitGateValidationError(
                "unsupported control-assurance schema"
            )
        baseline = _baseline(values["locked_baseline_commit"])
        start = _require_utc("control window_start", values["window_start"])
        end = _require_utc("control window_end", values["window_end"])
        generated = _require_utc("control generated_at", values["generated_at"])
        if start > end or generated < end:
            raise ShadowPhase11ExitGateValidationError(
                "invalid control-assurance timestamp ordering"
            )
        supplied = values["domain_evidence"]
        if type(supplied) is not tuple or any(
            type(item) is not ShadowPhase11ControlDomainEvidenceV1
            for item in supplied
        ):
            raise ShadowPhase11ExitGateValidationError(
                "invalid control-domain evidence collection"
            )
        domains = tuple(item.domain for item in supplied)
        expected = tuple(ShadowPhase11ControlDomainV1)
        if len(supplied) != len(expected) or set(domains) != set(expected):
            raise ShadowPhase11ExitGateValidationError(
                "control assurance requires every domain exactly once"
            )
        by_domain = {item.domain: item for item in supplied}
        domain_evidence = tuple(by_domain[domain] for domain in expected)
        reasons = _codes("reason_codes", values["reason_codes"])
        _zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        material = {
            "schema_version": values["schema_version"],
            "locked_baseline_commit": baseline,
            "window_start": start,
            "window_end": end,
            "generated_at": generated,
            "domain_evidence_ids": tuple(item.identity for item in domain_evidence),
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _identity(
            material,
            values["control_assurance_evidence_id"],
            "control_assurance_evidence_id",
        )
        normalized = {
            "schema_version": values["schema_version"],
            "control_assurance_evidence_id": identity,
            "locked_baseline_commit": baseline,
            "window_start": start,
            "window_end": end,
            "generated_at": generated,
            "domain_evidence": domain_evidence,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.control_assurance_evidence_id


_TIERING_FIELDS = frozenset(
    {
        "schema_version",
        "tiering_value_evidence_id",
        "alternative_arm",
        "comparison_dimensions",
        "evidence_readiness",
        "mandatory_guardrails_met",
        "measurable_value_met",
        "source_report_identities",
        "reason_codes",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11TieringValueEvidenceV1:
    schema_version: str
    tiering_value_evidence_id: str
    alternative_arm: AlternativeArmIdentityV1
    comparison_dimensions: tuple[ShadowPhase11EvidenceDimensionV1, ...]
    evidence_readiness: ShadowPhase11EvidenceReadinessV1
    mandatory_guardrails_met: bool
    measurable_value_met: bool | None
    source_report_identities: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _TIERING_FIELDS:
            raise ShadowPhase11ExitGateValidationError(
                "invalid tiering-value evidence fields"
            )
        if values["schema_version"] != "phase11-shadow-tiering-value-evidence-v1":
            raise ShadowPhase11ExitGateValidationError(
                "unsupported tiering-value evidence schema"
            )
        arm = values["alternative_arm"]
        if type(arm) is not AlternativeArmIdentityV1 or arm not in {
            AlternativeArmIdentityV1.DEEPSEEK_ONLY,
            AlternativeArmIdentityV1.CLAUDE_OPUS_ONLY,
        }:
            raise ShadowPhase11ExitGateValidationError(
                "unsupported tiering alternative"
            )
        dimensions = _enum_tuple(
            "comparison_dimensions",
            values["comparison_dimensions"],
            ShadowPhase11EvidenceDimensionV1,
        )
        readiness = values["evidence_readiness"]
        if type(readiness) is not ShadowPhase11EvidenceReadinessV1:
            raise ShadowPhase11ExitGateValidationError(
                "invalid tiering evidence readiness"
            )
        guardrails = values["mandatory_guardrails_met"]
        measurable = values["measurable_value_met"]
        if type(guardrails) is not bool:
            raise ShadowPhase11ExitGateValidationError(
                "mandatory_guardrails_met must be an exact bool"
            )
        if readiness is ShadowPhase11EvidenceReadinessV1.AVAILABLE:
            if type(measurable) is not bool:
                raise ShadowPhase11ExitGateValidationError(
                    "available tiering evidence requires a measurable-value status"
                )
        elif measurable is not None:
            raise ShadowPhase11ExitGateValidationError(
                "unavailable tiering evidence cannot claim measurable value"
            )
        sources = _hashes(
            "source_report_identities", values["source_report_identities"]
        )
        reasons = _codes("reason_codes", values["reason_codes"])
        material = {
            "schema_version": values["schema_version"],
            "alternative_arm": arm,
            "comparison_dimensions": dimensions,
            "evidence_readiness": readiness,
            "mandatory_guardrails_met": guardrails,
            "measurable_value_met": measurable,
            "source_report_identities": sources,
            "reason_codes": reasons,
        }
        identity = _identity(
            material,
            values["tiering_value_evidence_id"],
            "tiering_value_evidence_id",
        )
        normalized = {**material, "tiering_value_evidence_id": identity}
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, normalized[name])

    @property
    def identity(self) -> str:
        return self.tiering_value_evidence_id


_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "exit_gate_plan_id",
        "comparative_aggregate_report",
        "quality_aggregate_report",
        "alternative_arm_aggregate_report",
        "route_cost_aggregate_report",
        "cost_projection_report",
        "control_assurance_evidence",
        "criteria",
        "tiering_value_evidence",
        "evaluated_at",
        "locked_baseline_commit",
        "scope",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ShadowPhase11ExitGatePlanV1:
    schema_version: str
    exit_gate_plan_id: str
    comparative_aggregate_report: ShadowAggregateComparativeReportV1
    quality_aggregate_report: ShadowAggregateQualityReportV1
    alternative_arm_aggregate_report: ShadowAggregateAlternativeArmReportV1
    route_cost_aggregate_report: ShadowRouteCostAggregateReportV1
    cost_projection_report: ShadowCostProjectionReportV1
    control_assurance_evidence: ShadowPhase11ControlAssuranceEvidenceV1
    criteria: ShadowPhase11ExitGateCriteriaV1
    tiering_value_evidence: tuple[ShadowPhase11TieringValueEvidenceV1, ...]
    evaluated_at: datetime
    locked_baseline_commit: str
    scope: ShadowPhase11ExitGateScopeV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PLAN_FIELDS:
            raise ShadowPhase11ExitGateValidationError(
                "invalid exit-gate plan fields"
            )
        if values["schema_version"] != "phase11-shadow-exit-gate-plan-v1":
            raise ShadowPhase11ExitGateValidationError(
                "unsupported exit-gate plan schema"
            )
        expected_types = (
            ("comparative_aggregate_report", ShadowAggregateComparativeReportV1),
            ("quality_aggregate_report", ShadowAggregateQualityReportV1),
            (
                "alternative_arm_aggregate_report",
                ShadowAggregateAlternativeArmReportV1,
            ),
            ("route_cost_aggregate_report", ShadowRouteCostAggregateReportV1),
            ("cost_projection_report", ShadowCostProjectionReportV1),
            (
                "control_assurance_evidence",
                ShadowPhase11ControlAssuranceEvidenceV1,
            ),
            ("criteria", ShadowPhase11ExitGateCriteriaV1),
        )
        for name, expected_type in expected_types:
            if type(values[name]) is not expected_type:
                raise ShadowPhase11ExitGateValidationError(f"invalid {name}")
        comparative = values["comparative_aggregate_report"]
        quality = values["quality_aggregate_report"]
        alternative = values["alternative_arm_aggregate_report"]
        route_cost = values["route_cost_aggregate_report"]
        projection = values["cost_projection_report"]
        assurance = values["control_assurance_evidence"]
        criteria = values["criteria"]
        baseline = _baseline(values["locked_baseline_commit"])
        sources = (comparative, quality, alternative, route_cost, projection)
        if any(item.locked_baseline_commit != baseline for item in sources):
            raise ShadowPhase11ExitGateValidationError(
                "aggregate source baseline mismatch"
            )
        if assurance.locked_baseline_commit != baseline:
            raise ShadowPhase11ExitGateValidationError(
                "control-assurance baseline mismatch"
            )
        for item in (*sources, assurance):
            _zero_effect(
                item.production_effect, item.zero_production_effect_proof
            )
        starts = (
            _parse_utc("comparative window_start", comparative.window_start),
            _parse_utc("quality window_start", quality.window_start),
            _parse_utc("alternative window_start", alternative.window_start),
            _require_utc("route-cost window_start", route_cost.window_start),
            _require_utc(
                "projection route-cost window_start",
                projection.route_cost_window_start,
            ),
            _parse_utc(
                "projection comparative window_start",
                projection.comparative_window_start,
            ),
            assurance.window_start,
        )
        ends = (
            _parse_utc("comparative window_end", comparative.window_end),
            _parse_utc("quality window_end", quality.window_end),
            _parse_utc("alternative window_end", alternative.window_end),
            _require_utc("route-cost window_end", route_cost.window_end),
            _require_utc(
                "projection route-cost window_end", projection.route_cost_window_end
            ),
            _parse_utc(
                "projection comparative window_end",
                projection.comparative_window_end,
            ),
            assurance.window_end,
        )
        if len(set(starts)) != 1 or len(set(ends)) != 1:
            raise ShadowPhase11ExitGateValidationError(
                "aggregate source evidence windows are incompatible"
            )
        evaluated = _require_utc("evaluated_at", values["evaluated_at"])
        generated = (
            _parse_utc("comparative generated_at", comparative.generated_at),
            _parse_utc("quality generated_at", quality.generated_at),
            _parse_utc("alternative generated_at", alternative.generated_at),
            _require_utc("route-cost generated_at", route_cost.generated_at),
            _require_utc("projection projected_at", projection.projected_at),
            assurance.generated_at,
        )
        if any(evaluated < item for item in generated):
            raise ShadowPhase11ExitGateValidationError(
                "evaluated_at precedes supplied evidence"
            )
        if (
            projection.route_cost_aggregate_report_id != route_cost.identity
            or projection.comparative_aggregate_report_id != comparative.identity
        ):
            raise ShadowPhase11ExitGateValidationError(
                "cost-projection source lineage mismatch"
            )
        if (
            projection.owner_budget_gate_status
            is not ShadowOwnerBudgetGateStatusV1.NOT_APPROVED
        ):
            raise ShadowPhase11ExitGateValidationError(
                "owner budget gate must remain not approved"
            )
        source_ids = tuple(item.identity for item in sources)
        if len(set(source_ids)) != len(source_ids):
            raise ShadowPhase11ExitGateValidationError(
                "aggregate source identities must be unique"
            )
        tiering = values["tiering_value_evidence"]
        if type(tiering) is not tuple or any(
            type(item) is not ShadowPhase11TieringValueEvidenceV1
            for item in tiering
        ):
            raise ShadowPhase11ExitGateValidationError(
                "invalid tiering-value evidence collection"
            )
        if len({item.alternative_arm for item in tiering}) != len(tiering):
            raise ShadowPhase11ExitGateValidationError(
                "duplicate tiering alternative evidence"
            )
        tiering = tuple(sorted(tiering, key=lambda item: item.alternative_arm.value))
        if (
            values["scope"]
            is not ShadowPhase11ExitGateScopeV1.AGGREGATE_EVIDENCE_RECONCILIATION
        ):
            raise ShadowPhase11ExitGateValidationError(
                "unsupported exit-gate scope"
            )
        reasons = _codes("reason_codes", values["reason_codes"])
        _zero_effect(
            values["production_effect"], values["zero_production_effect_proof"]
        )
        material = {
            "schema_version": values["schema_version"],
            "source_report_ids": source_ids,
            "control_assurance_evidence_id": assurance.identity,
            "criteria_id": criteria.identity,
            "tiering_value_evidence_ids": tuple(item.identity for item in tiering),
            "evaluated_at": evaluated,
            "locked_baseline_commit": baseline,
            "scope": values["scope"],
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        identity = _identity(
            material, values["exit_gate_plan_id"], "exit_gate_plan_id"
        )
        normalized = {
            **values,
            "exit_gate_plan_id": identity,
            "tiering_value_evidence": tiering,
            "evaluated_at": evaluated,
            "locked_baseline_commit": baseline,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.exit_gate_plan_id


@dataclass(frozen=True, slots=True)
class ShadowPhase11EvidenceDimensionResultV1:
    schema_version: str
    evidence_dimension_result_id: str
    dimension: ShadowPhase11EvidenceDimensionV1
    readiness: ShadowPhase11EvidenceReadinessV1
    source_report_identities: tuple[str, ...]
    available_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    reason_codes: tuple[str, ...]

    @property
    def identity(self) -> str:
        return self.evidence_dimension_result_id


@dataclass(frozen=True, slots=True)
class ShadowPhase11ExitGateReportV1:
    schema_version: str
    exit_gate_report_id: str
    exit_gate_plan_id: str
    comparative_aggregate_report_id: str
    quality_aggregate_report_id: str
    alternative_arm_aggregate_report_id: str
    route_cost_aggregate_report_id: str
    cost_projection_report_id: str
    criteria_id: str
    control_assurance_evidence_id: str
    locked_baseline_commit: str
    source_window_start: datetime
    source_window_end: datetime
    evaluated_at: datetime
    coverage_criterion_status: ShadowPhase11CriterionStatusV1
    critical_control_defect_criterion_status: ShadowPhase11CriterionStatusV1
    tiering_value_evidence: tuple[ShadowPhase11TieringValueEvidenceV1, ...]
    tiering_value_criterion_status: ShadowPhase11CriterionStatusV1
    evidence_dimension_results: tuple[ShadowPhase11EvidenceDimensionResultV1, ...]
    evidence_dimension_results_by_dimension: Mapping[
        ShadowPhase11EvidenceDimensionV1, ShadowPhase11EvidenceDimensionResultV1
    ]
    mechanical_readiness: ShadowPhase11MechanicalReadinessV1
    declared_limitations: tuple[str, ...]
    unresolved_evidence_gaps: tuple[str, ...]
    uncertainty_classes: tuple[str, ...]
    owner_review_questions: tuple[str, ...]
    owner_acceptance_status: ShadowPhase11OwnerAcceptanceStatusV1
    limitations_acceptance_status: ShadowPhase11LimitationsAcceptanceStatusV1
    phase_12_recommendation_status: ShadowPhase12RecommendationStatusV1
    owner_budget_gate_status: ShadowOwnerBudgetGateStatusV1
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    @property
    def identity(self) -> str:
        return self.exit_gate_report_id


def _coverage_status(
    plan: ShadowPhase11ExitGatePlanV1,
) -> tuple[ShadowPhase11CriterionStatusV1, tuple[str, ...]]:
    criteria = plan.criteria
    comparative = plan.comparative_aggregate_report
    quality = plan.quality_aggregate_report
    alternative = plan.alternative_arm_aggregate_report
    route_cost = plan.route_cost_aggregate_report
    status_by_target: dict[str, list[str]] = {}
    for result in quality.coverage_results:
        status_by_target.setdefault(result.target, []).append(result.status.value)
    for result in comparative.coverage_results:
        status_by_target.setdefault(result.target, []).append(result.status.value)
    for result in route_cost.coverage_results:
        status_by_target.setdefault(result.target_name, []).append(
            result.status.value
        )
    for result in alternative.coverage_results:
        status_by_target.setdefault(result.target, []).append(result.status.value)
    gaps: set[str] = set()
    direct_not_met = False
    insufficient = False
    required_targets = set(criteria.required_coverage_targets)
    required_targets.update(criteria.required_event_classes)
    required_targets.update(criteria.required_route_classes)
    for target in required_targets:
        statuses = status_by_target.get(target, [])
        if not statuses or any(item == "NOT_APPLICABLE" for item in statuses):
            insufficient = True
            gaps.add(f"MISSING_COVERAGE_{target}")
        elif any(item == "NOT_MET" for item in statuses):
            direct_not_met = True
            gaps.add(f"UNDERREPRESENTED_{target}")
    for route in criteria.required_route_classes:
        observed = (
            quality.route_counts.get(route, 0)
            + comparative.route_counts.get(route, 0)
            + route_cost.route_counts.get(route, 0)
        )
        if observed == 0:
            direct_not_met = True
            gaps.add(f"UNDERREPRESENTED_{route}")
    for arm in criteria.required_alternative_arms:
        if alternative.arm_identity_counts.get(arm, 0) == 0:
            direct_not_met = True
            gaps.add(f"UNDERREPRESENTED_{arm.value}")
    if direct_not_met:
        status = ShadowPhase11CriterionStatusV1.NOT_MET
    elif insufficient:
        status = ShadowPhase11CriterionStatusV1.INSUFFICIENT_EVIDENCE
    else:
        status = ShadowPhase11CriterionStatusV1.MET
    return status, tuple(sorted(gaps))


def _control_status(
    plan: ShadowPhase11ExitGatePlanV1,
) -> tuple[ShadowPhase11CriterionStatusV1, tuple[str, ...]]:
    insufficient: set[str] = set()
    not_met: set[str] = set()
    maximum = plan.criteria.critical_control_defect_maximum
    for evidence in plan.control_assurance_evidence.domain_evidence:
        if (
            evidence.evidence_readiness
            is not ShadowPhase11EvidenceReadinessV1.AVAILABLE
            or not evidence.evidence_references
        ):
            insufficient.add(f"UNAVAILABLE_CONTROL_{evidence.domain.value}")
        elif evidence.critical_open_defect_count > maximum:
            not_met.add(f"CRITICAL_CONTROL_DEFECT_{evidence.domain.value}")
    if not_met:
        return ShadowPhase11CriterionStatusV1.NOT_MET, tuple(sorted(not_met))
    if insufficient:
        return (
            ShadowPhase11CriterionStatusV1.INSUFFICIENT_EVIDENCE,
            tuple(sorted(insufficient)),
        )
    return ShadowPhase11CriterionStatusV1.MET, ()


def _tiering_status(
    plan: ShadowPhase11ExitGatePlanV1,
) -> tuple[ShadowPhase11CriterionStatusV1, tuple[str, ...]]:
    by_arm = {item.alternative_arm: item for item in plan.tiering_value_evidence}
    missing: set[str] = set()
    failed: set[str] = set()
    for arm in plan.criteria.required_alternative_arms:
        evidence = by_arm.get(arm)
        if evidence is None:
            missing.add(f"MISSING_TIERING_{arm.value}")
            continue
        required_dimensions = set(plan.criteria.required_comparison_dimensions)
        if (
            evidence.evidence_readiness
            is not ShadowPhase11EvidenceReadinessV1.AVAILABLE
            or not required_dimensions.issubset(evidence.comparison_dimensions)
            or not evidence.source_report_identities
            or evidence.measurable_value_met is None
        ):
            missing.add(f"INSUFFICIENT_TIERING_{arm.value}")
        elif (
            not evidence.mandatory_guardrails_met
            or evidence.measurable_value_met is False
        ):
            failed.add(f"TIERING_GUARDRAIL_NOT_MET_{arm.value}")
    if failed:
        return ShadowPhase11CriterionStatusV1.NOT_MET, tuple(sorted(failed))
    if missing:
        return (
            ShadowPhase11CriterionStatusV1.INSUFFICIENT_EVIDENCE,
            tuple(sorted(missing)),
        )
    return ShadowPhase11CriterionStatusV1.MET, ()


def _dimension_result(
    dimension: ShadowPhase11EvidenceDimensionV1,
    readiness: ShadowPhase11EvidenceReadinessV1,
    sources: tuple[str, ...],
    available: tuple[str, ...],
    missing: tuple[str, ...] = (),
) -> ShadowPhase11EvidenceDimensionResultV1:
    sources = tuple(sorted(sources))
    available = tuple(sorted(available))
    missing = tuple(sorted(missing))
    reasons = (f"{dimension.value}_AGGREGATE_EVIDENCE_RECONCILED",)
    material = {
        "schema_version": "phase11-shadow-evidence-dimension-result-v1",
        "dimension": dimension,
        "readiness": readiness,
        "source_report_identities": sources,
        "available_evidence": available,
        "missing_evidence": missing,
        "reason_codes": reasons,
    }
    return ShadowPhase11EvidenceDimensionResultV1(
        schema_version=material["schema_version"],
        evidence_dimension_result_id=_derived_identity(material),
        dimension=dimension,
        readiness=readiness,
        source_report_identities=sources,
        available_evidence=available,
        missing_evidence=missing,
        reason_codes=reasons,
    )


def _dimension_results(
    plan: ShadowPhase11ExitGatePlanV1,
) -> tuple[ShadowPhase11EvidenceDimensionResultV1, ...]:
    comparative = plan.comparative_aggregate_report
    quality = plan.quality_aggregate_report
    alternative = plan.alternative_arm_aggregate_report
    route_cost = plan.route_cost_aggregate_report
    projection = plan.cost_projection_report
    quality_rates = (
        quality.usable_label_coverage_rate,
        quality.materiality_handling_correctness_rate,
        quality.mapping_correctness_rate,
        quality.control_correctness_rate,
        quality.treatment_correctness_rate,
        quality.false_block_rate,
        quality.missed_material_event_rate,
        quality.unnecessary_escalation_rate,
    )
    quality_available = all(item.value is not None for item in quality_rates)
    quality_result = _dimension_result(
        ShadowPhase11EvidenceDimensionV1.QUALITY,
        (
            ShadowPhase11EvidenceReadinessV1.AVAILABLE
            if quality_available
            else ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE
        ),
        (quality.identity,),
        (
            "DECISION_AND_MAPPING_QUALITY",
            "FALSE_BLOCK_AND_MISSED_EVENT_RATES",
            "LABEL_COVERAGE",
        )
        if quality_available
        else (),
        () if quality_available else ("QUALITY_RATE_EVIDENCE",),
    )
    latency_available = (
        comparative.latency_summary.mean is not None
        and alternative.latency_summary.mean is not None
    )
    latency_result = _dimension_result(
        ShadowPhase11EvidenceDimensionV1.LATENCY,
        (
            ShadowPhase11EvidenceReadinessV1.AVAILABLE
            if latency_available
            else ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE
        ),
        (comparative.identity, alternative.identity),
        ("AGGREGATE_LATENCY_TELEMETRY",) if latency_available else (),
        () if latency_available else ("LATENCY_TELEMETRY",),
    )
    route_cost_available = all(
        summary.available_value_mean is not None
        for summary in route_cost.route_cost_summaries.values()
    )
    projection_available = projection.projection_availability.value in {
        "COMPLETE",
        "PARTIAL",
    } and projection.projected_monthly_cost.value is not None
    if route_cost_available and projection_available:
        cost_readiness = ShadowPhase11EvidenceReadinessV1.AVAILABLE
        cost_missing: tuple[str, ...] = ()
    elif route_cost_available or projection_available:
        cost_readiness = ShadowPhase11EvidenceReadinessV1.PARTIAL
        cost_missing = ("COMPLETE_COST_EVIDENCE",)
    else:
        cost_readiness = ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE
        cost_missing = ("ROUTE_COST_AND_PROJECTION_EVIDENCE",)
    cost_result = _dimension_result(
        ShadowPhase11EvidenceDimensionV1.COST,
        cost_readiness,
        (route_cost.identity, projection.identity),
        (
            "ACTUAL_ROUTE_KEYED_COSTS",
            "COST_PER_ELIGIBLE_EVENT",
            "PROJECTED_MONTHLY_COST",
            "OWNER_GATE_NOT_APPROVED",
        )
        if route_cost_available or projection_available
        else (),
        cost_missing,
    )
    fail_available = (
        comparative.retry_count_summary.total is not None
        and quality.false_block_rate.value is not None
        and quality.missed_material_event_rate.value is not None
    )
    fail_result = _dimension_result(
        ShadowPhase11EvidenceDimensionV1.FAIL_POLICY,
        (
            ShadowPhase11EvidenceReadinessV1.AVAILABLE
            if fail_available
            else ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE
        ),
        (comparative.identity, quality.identity, projection.identity),
        (
            "FAILED_CLOSED_AND_TERMINAL_EVIDENCE",
            "FALSE_BLOCK_AND_MISSED_EVENT_RATES",
            "RETRY_AND_FAILURE_EVIDENCE",
        )
        if fail_available
        else (),
        () if fail_available else ("FAIL_POLICY_EVIDENCE",),
    )
    operational_available = (
        comparative.call_count_summary.total is not None
        and comparative.retry_count_summary.total is not None
        and all(
            item.production_effect == _ZERO_EFFECT
            and item.zero_production_effect_proof == _ZERO_PROOF
            for item in (comparative, quality, alternative, route_cost, projection)
        )
    )
    operational_result = _dimension_result(
        ShadowPhase11EvidenceDimensionV1.OPERATIONAL,
        (
            ShadowPhase11EvidenceReadinessV1.AVAILABLE
            if operational_available
            else ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE
        ),
        tuple(
            item.identity
            for item in (comparative, quality, alternative, route_cost, projection)
        ),
        (
            "COVERAGE_AND_IDENTITY",
            "RETRY_TERMINAL_AND_FAILURE_EVIDENCE",
            "ZERO_PRODUCTION_PROOF",
        )
        if operational_available
        else (),
        () if operational_available else ("OPERATIONAL_EVIDENCE",),
    )
    by_dimension = {
        item.dimension: item
        for item in (
            quality_result,
            latency_result,
            cost_result,
            fail_result,
            operational_result,
        )
    }
    return tuple(by_dimension[item] for item in ShadowPhase11EvidenceDimensionV1)


def _mechanical_readiness(
    plan: ShadowPhase11ExitGatePlanV1,
    criteria_statuses: tuple[ShadowPhase11CriterionStatusV1, ...],
    dimensions: tuple[ShadowPhase11EvidenceDimensionResultV1, ...],
) -> ShadowPhase11MechanicalReadinessV1:
    if any(
        status is ShadowPhase11CriterionStatusV1.NOT_MET
        for status in criteria_statuses
    ):
        return ShadowPhase11MechanicalReadinessV1.NOT_READY
    if any(
        status is ShadowPhase11CriterionStatusV1.INSUFFICIENT_EVIDENCE
        for status in criteria_statuses
    ):
        return ShadowPhase11MechanicalReadinessV1.INSUFFICIENT_EVIDENCE
    by_dimension = {item.dimension: item for item in dimensions}
    for required in plan.criteria.required_evidence_dimensions:
        result = by_dimension.get(required)
        if result is None or result.readiness in {
            ShadowPhase11EvidenceReadinessV1.INSUFFICIENT_EVIDENCE,
            ShadowPhase11EvidenceReadinessV1.UNAVAILABLE,
        }:
            return ShadowPhase11MechanicalReadinessV1.INSUFFICIENT_EVIDENCE
    return ShadowPhase11MechanicalReadinessV1.READY_FOR_OWNER_REVIEW


class ShadowPhase11ExitGateEvaluatorV1:
    """Stateless reconciler over already-created immutable aggregate evidence."""

    __slots__ = ()

    def evaluate(
        self, plan: ShadowPhase11ExitGatePlanV1
    ) -> ShadowPhase11ExitGateReportV1:
        if type(plan) is not ShadowPhase11ExitGatePlanV1:
            raise ShadowPhase11ExitGateValidationError(
                "invalid exit-gate evaluation plan"
            )
        coverage, coverage_gaps = _coverage_status(plan)
        controls, control_gaps = _control_status(plan)
        tiering, tiering_gaps = _tiering_status(plan)
        dimensions = _dimension_results(plan)
        mechanical = _mechanical_readiness(
            plan, (coverage, controls, tiering), dimensions
        )
        uncertainty = tuple(
            sorted(set(plan.cost_projection_report.uncertainty_classes))
        )
        declared_limitations = uncertainty
        dimension_gaps = tuple(
            gap for item in dimensions for gap in item.missing_evidence
        )
        unresolved = tuple(
            sorted(
                set(
                    coverage_gaps
                    + control_gaps
                    + tiering_gaps
                    + dimension_gaps
                )
            )
        )
        questions = tuple(
            sorted(
                {
                    "REVIEW_LIMITATIONS_AND_UNRESOLVED_EVIDENCE",
                    "REVIEW_QUALITY_LATENCY_COST_FAIL_POLICY_OPERATIONAL_EVIDENCE",
                }
            )
        )
        reasons = ("AGGREGATE_EXIT_GATE_EVIDENCE_RECONCILED",)
        dimension_map = MappingProxyType(
            {item.dimension: item for item in dimensions}
        )
        source_ids = {
            "comparative_aggregate_report_id": plan.comparative_aggregate_report.identity,
            "quality_aggregate_report_id": plan.quality_aggregate_report.identity,
            "alternative_arm_aggregate_report_id": plan.alternative_arm_aggregate_report.identity,
            "route_cost_aggregate_report_id": plan.route_cost_aggregate_report.identity,
            "cost_projection_report_id": plan.cost_projection_report.identity,
        }
        material = {
            "schema_version": "phase11-shadow-exit-gate-report-v1",
            "exit_gate_plan_id": plan.identity,
            **source_ids,
            "criteria_id": plan.criteria.identity,
            "control_assurance_evidence_id": plan.control_assurance_evidence.identity,
            "locked_baseline_commit": plan.locked_baseline_commit,
            "source_window_start": plan.control_assurance_evidence.window_start,
            "source_window_end": plan.control_assurance_evidence.window_end,
            "evaluated_at": plan.evaluated_at,
            "coverage_criterion_status": coverage,
            "critical_control_defect_criterion_status": controls,
            "tiering_value_evidence_ids": tuple(
                item.identity for item in plan.tiering_value_evidence
            ),
            "tiering_value_criterion_status": tiering,
            "evidence_dimension_result_ids": tuple(
                item.identity for item in dimensions
            ),
            "mechanical_readiness": mechanical,
            "declared_limitations": declared_limitations,
            "unresolved_evidence_gaps": unresolved,
            "uncertainty_classes": uncertainty,
            "owner_review_questions": questions,
            "owner_acceptance_status": ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED,
            "limitations_acceptance_status": ShadowPhase11LimitationsAcceptanceStatusV1.NOT_RECORDED,
            "phase_12_recommendation_status": ShadowPhase12RecommendationStatusV1.NOT_ISSUED,
            "owner_budget_gate_status": ShadowOwnerBudgetGateStatusV1.NOT_APPROVED,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        report_id = _derived_identity(material)
        return ShadowPhase11ExitGateReportV1(
            schema_version=material["schema_version"],
            exit_gate_report_id=report_id,
            exit_gate_plan_id=plan.identity,
            **source_ids,
            criteria_id=plan.criteria.identity,
            control_assurance_evidence_id=plan.control_assurance_evidence.identity,
            locked_baseline_commit=plan.locked_baseline_commit,
            source_window_start=plan.control_assurance_evidence.window_start,
            source_window_end=plan.control_assurance_evidence.window_end,
            evaluated_at=plan.evaluated_at,
            coverage_criterion_status=coverage,
            critical_control_defect_criterion_status=controls,
            tiering_value_evidence=plan.tiering_value_evidence,
            tiering_value_criterion_status=tiering,
            evidence_dimension_results=dimensions,
            evidence_dimension_results_by_dimension=dimension_map,
            mechanical_readiness=mechanical,
            declared_limitations=declared_limitations,
            unresolved_evidence_gaps=unresolved,
            uncertainty_classes=uncertainty,
            owner_review_questions=questions,
            owner_acceptance_status=ShadowPhase11OwnerAcceptanceStatusV1.NOT_RECORDED,
            limitations_acceptance_status=ShadowPhase11LimitationsAcceptanceStatusV1.NOT_RECORDED,
            phase_12_recommendation_status=ShadowPhase12RecommendationStatusV1.NOT_ISSUED,
            owner_budget_gate_status=ShadowOwnerBudgetGateStatusV1.NOT_APPROVED,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
