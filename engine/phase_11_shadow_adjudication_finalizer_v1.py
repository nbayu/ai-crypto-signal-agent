"""Deterministic Phase 11 shadow adjudication and record finalization.

This module consumes already validated immutable evidence.  It performs no
provider execution, credential access, budget transition, persistence,
comparison, replay, publication, or production action.
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

from engine.deterministic_adjudication_v1 import (
    DeterministicAdjudicationPolicyV1,
    DeterministicAdjudicationResultV1,
    adjudicate_review_results,
)
from engine.news_risk_object_v1 import (
    NewsRiskObjectV1,
    NewsRiskPolicyV1,
    build_news_risk_object,
)
from engine.phase_11_finalization_evidence_bridge_v1 import (
    ShadowAdjudicationEvidenceBundleV1,
    ShadowAdjudicationRouteLineageV1,
    ShadowTerminalAdjudicationStateV1,
    ShadowTerminalExecutionRecordV1,
)
from engine.phase_11_shadow_execution_record_v1 import ShadowExecutionRecordV1
from engine.phase_11_shadow_input_contracts_v1 import ShadowEvaluationInputV1
from engine.phase_11_shadow_run_orchestrator_v1 import (
    ShadowProviderRunPlanV1,
    ShadowProviderRunResultV1,
)
from engine.signal_gate_v1 import (
    SignalGateDecisionV1,
    SignalGatePolicyV1,
    evaluate_signal_gate,
)


UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_UTC_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)
_ZERO_EFFECT = "NONE"
_ZERO_PROOF = "PROVEN_NONE"
_CLEAN_STATUS = "COMPLETED"
_TERMINAL_STATUSES = frozenset(
    (
        "DENIED",
        "FAILED_CLOSED",
        "PARTIAL_EVIDENCE",
        "RECONCILIATION_REQUIRED",
    )
)


class ShadowAdjudicationFinalizerValidationError(ValueError):
    """Raised when finalization evidence is incomplete or inconsistent."""


class ShadowAdjudicationFinalizationPathV1(StrEnum):
    CLEAN = "CLEAN"
    TERMINAL = "TERMINAL"


class ShadowAdjudicationFinalizationStatusV1(StrEnum):
    FINALIZED = "FINALIZED"


class ShadowAdjudicationFinalizationFailureV1(StrEnum):
    NONE = "NONE"


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowAdjudicationFinalizerValidationError(
                f"invalid {label}"
            )
        parsed = value.astimezone(UTC)
    elif type(value) is str and _UTC_TEXT.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ShadowAdjudicationFinalizerValidationError(
                f"invalid {label}"
            ) from error
    else:
        raise ShadowAdjudicationFinalizerValidationError(f"invalid {label}")
    text = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return text.replace("+00:00", "Z").replace(".000000Z", "Z")


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowAdjudicationFinalizerValidationError(
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
    """Return deterministic canonical JSON encoded as UTF-8."""

    try:
        return json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowAdjudicationFinalizerValidationError(
            "non-canonical finalization metadata"
        ) from error


def lowercase_sha256(value: Any) -> str:
    """Return lowercase SHA-256 over canonical structured JSON."""

    return sha256(canonical_json_bytes(value)).hexdigest()


def _identity(value: Any, material: Mapping[str, Any], label: str) -> str:
    expected = lowercase_sha256(material)
    if value is not None and (
        type(value) is not str
        or _HASH.fullmatch(value) is None
        or value != expected
    ):
        raise ShadowAdjudicationFinalizerValidationError(
            f"invalid {label}"
        )
    return expected


def _hash_value(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ShadowAdjudicationFinalizerValidationError(f"invalid {label}")
    return value


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ShadowAdjudicationFinalizerValidationError(f"invalid {label}")
    return value


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        raise ShadowAdjudicationFinalizerValidationError(
            "invalid reason_codes"
        )
    result: list[str] = []
    for item in value:
        if type(item) is not str or _REASON.fullmatch(item) is None:
            raise ShadowAdjudicationFinalizerValidationError(
                "invalid reason_codes"
            )
        if item in result:
            raise ShadowAdjudicationFinalizerValidationError(
                "duplicate reason_codes"
            )
        result.append(item)
    if not result:
        raise ShadowAdjudicationFinalizerValidationError(
            "missing reason_codes"
        )
    return tuple(sorted(result))


def _zero_effect(effect: Any, proof: Any) -> None:
    if effect != _ZERO_EFFECT or proof != _ZERO_PROOF:
        raise ShadowAdjudicationFinalizerValidationError(
            "non-zero production effect"
        )


_PLAN_FIELDS = frozenset(
    (
        "schema_version",
        "finalization_plan_id",
        "shadow_input",
        "run_plan",
        "run_result",
        "clean_bundle",
        "finalized_at",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowAdjudicationFinalizationPlanV1:
    schema_version: str
    finalization_plan_id: str
    shadow_input: ShadowEvaluationInputV1
    run_plan: ShadowProviderRunPlanV1
    run_result: ShadowProviderRunResultV1
    clean_bundle: ShadowAdjudicationEvidenceBundleV1 | None
    finalized_at: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _PLAN_FIELDS:
            raise ShadowAdjudicationFinalizerValidationError(
                "invalid finalization-plan fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-adjudication-finalization-plan-v1"
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "unsupported finalization-plan schema"
            )
        shadow_input = values["shadow_input"]
        run_plan = values["run_plan"]
        run_result = values["run_result"]
        bundle = values["clean_bundle"]
        if (
            type(shadow_input) is not ShadowEvaluationInputV1
            or type(run_plan) is not ShadowProviderRunPlanV1
            or type(run_result) is not ShadowProviderRunResultV1
            or (
                bundle is not None
                and type(bundle) is not ShadowAdjudicationEvidenceBundleV1
            )
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "invalid finalization-plan child"
            )
        if (
            run_plan.shadow_input_identity != shadow_input.identity
            or run_plan.identity != run_result.run_plan_id
            or run_plan.execution_id != run_result.execution_id
            or run_plan.run_id != run_result.run_id
            or run_plan.route != run_result.route
            or run_plan.budget_ledger_before_id
            != run_result.ledger_before_id
            or run_result.ledger_after.policy.identity
            != run_plan.budget_ledger_before.policy.identity
            or run_result.ledger_after.sequence
            < run_plan.budget_ledger_before.sequence
            or run_result.ledger_after.reservations
            != run_plan.budget_ledger_before.reservations
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "finalization-plan lineage mismatch"
            )
        clean = (
            run_result.status == _CLEAN_STATUS
            and run_result.failure_class == "NONE"
            and run_result.reconciliation_state in {"NOT_REQUIRED", "RESOLVED"}
        )
        if clean:
            if (
                type(bundle) is not ShadowAdjudicationEvidenceBundleV1
                or bundle.shadow_input.identity != shadow_input.identity
                or bundle.run_plan.identity != run_plan.identity
                or bundle.run_result.identity != run_result.identity
                or bundle.route_lineage.run_route != run_plan.route
            ):
                raise ShadowAdjudicationFinalizerValidationError(
                    "clean finalization requires its exact bundle"
                )
        elif (
            run_result.status not in _TERMINAL_STATUSES
            or run_result.failure_class == "NONE"
            or bundle is not None
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "invalid terminal finalization evidence"
            )
        finalized_at = _timestamp(values["finalized_at"], "finalized_at")
        if datetime.fromisoformat(finalized_at.replace("Z", "+00:00")) < (
            datetime.fromisoformat(
                run_result.completed_at.replace("Z", "+00:00")
            )
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "finalization predates run completion"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "execution_id": run_plan.execution_id,
            "run_id": run_plan.run_id,
            "shadow_input_identity": shadow_input.identity,
            "run_plan_identity": run_plan.identity,
            "run_result_identity": run_result.identity,
            "clean_bundle_identity": (
                None if bundle is None else bundle.identity
            ),
            "original_run_route": run_plan.route,
            "ledger_before_identity": run_plan.budget_ledger_before_id,
            "ledger_after_identity": run_result.ledger_after_id,
            "finalized_at": finalized_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        plan_id = _identity(
            values["finalization_plan_id"],
            material,
            "finalization_plan_id",
        )
        normalized = dict(values)
        normalized.update(
            finalization_plan_id=plan_id,
            finalized_at=finalized_at,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.finalization_plan_id

    @property
    def execution_id(self) -> str:
        return self.run_plan.execution_id

    @property
    def run_id(self) -> str:
        return self.run_plan.run_id

    @property
    def is_clean(self) -> bool:
        return self.clean_bundle is not None


_RESULT_FIELDS = frozenset(
    (
        "schema_version",
        "finalization_result_id",
        "finalization_plan_id",
        "execution_id",
        "run_id",
        "original_run_route",
        "canonical_record_route",
        "route_lineage",
        "clean_bundle",
        "path",
        "status",
        "failure",
        "adjudication_result",
        "news_risk_object",
        "signal_gate_decision",
        "clean_execution_record",
        "terminal_record",
        "finalized_at",
        "reason_codes",
        "production_effect",
        "zero_production_effect_proof",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowAdjudicationFinalizationResultV1:
    schema_version: str
    finalization_result_id: str
    finalization_plan_id: str
    execution_id: str
    run_id: str
    original_run_route: str
    canonical_record_route: str | None
    route_lineage: ShadowAdjudicationRouteLineageV1 | None
    clean_bundle: ShadowAdjudicationEvidenceBundleV1 | None
    path: ShadowAdjudicationFinalizationPathV1
    status: ShadowAdjudicationFinalizationStatusV1
    failure: ShadowAdjudicationFinalizationFailureV1
    adjudication_result: DeterministicAdjudicationResultV1 | None
    news_risk_object: NewsRiskObjectV1 | None
    signal_gate_decision: SignalGateDecisionV1 | None
    clean_execution_record: ShadowExecutionRecordV1 | None
    terminal_record: ShadowTerminalExecutionRecordV1 | None
    finalized_at: str
    reason_codes: tuple[str, ...]
    production_effect: str
    zero_production_effect_proof: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _RESULT_FIELDS:
            raise ShadowAdjudicationFinalizerValidationError(
                "invalid finalization-result fields"
            )
        if (
            values["schema_version"]
            != "phase11-shadow-adjudication-finalization-result-v1"
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "unsupported finalization-result schema"
            )
        path = values["path"]
        status = values["status"]
        failure = values["failure"]
        try:
            path = ShadowAdjudicationFinalizationPathV1(path)
            status = ShadowAdjudicationFinalizationStatusV1(status)
            failure = ShadowAdjudicationFinalizationFailureV1(failure)
        except (TypeError, ValueError) as error:
            raise ShadowAdjudicationFinalizerValidationError(
                "unsupported finalization state"
            ) from error
        lineage = values["route_lineage"]
        bundle = values["clean_bundle"]
        adjudication = values["adjudication_result"]
        risk = values["news_risk_object"]
        gate = values["signal_gate_decision"]
        clean_record = values["clean_execution_record"]
        terminal = values["terminal_record"]
        plan_id = _hash_value(
            values["finalization_plan_id"],
            "finalization_plan_id",
        )
        execution_id = _identifier(values["execution_id"], "execution_id")
        run_id = _identifier(values["run_id"], "run_id")
        if path is ShadowAdjudicationFinalizationPathV1.CLEAN:
            if (
                type(lineage) is not ShadowAdjudicationRouteLineageV1
                or type(bundle) is not ShadowAdjudicationEvidenceBundleV1
                or type(adjudication) is not DeterministicAdjudicationResultV1
                or type(risk) is not NewsRiskObjectV1
                or type(gate) is not SignalGateDecisionV1
                or type(clean_record) is not ShadowExecutionRecordV1
                or terminal is not None
                or values["canonical_record_route"]
                != lineage.clean_record_route
                or values["original_run_route"] != lineage.run_route
                or bundle.route_lineage.identity != lineage.identity
                or bundle.run_plan.execution_id != execution_id
                or bundle.run_plan.run_id != run_id
                or clean_record.route != lineage.clean_record_route
                or clean_record.adjudication_result_id
                != adjudication.adjudication_result_id
                or clean_record.news_risk_object_id
                != risk.news_risk_object_id
                or clean_record.signal_gate_decision_id
                != gate.signal_gate_decision_id
            ):
                raise ShadowAdjudicationFinalizerValidationError(
                    "invalid clean finalization result"
                )
        elif (
            lineage is not (
                None if terminal is None else terminal.route_lineage
            )
            or bundle is not None
            or adjudication is not None
            or risk is not None
            or gate is not None
            or clean_record is not None
            or type(terminal) is not ShadowTerminalExecutionRecordV1
            or values["canonical_record_route"] is not None
            or values["original_run_route"] != terminal.run_plan.route
            or terminal.run_plan.execution_id != execution_id
            or terminal.run_plan.run_id != run_id
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "invalid terminal finalization result"
            )
        finalized_at = _timestamp(values["finalized_at"], "finalized_at")
        child_completed_at = (
            clean_record.completed_at
            if clean_record is not None
            else terminal.finalized_at
        )
        if datetime.fromisoformat(finalized_at.replace("Z", "+00:00")) < (
            datetime.fromisoformat(child_completed_at.replace("Z", "+00:00"))
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "finalization result predates child evidence"
            )
        reasons = _reasons(values["reason_codes"])
        _zero_effect(
            values["production_effect"],
            values["zero_production_effect_proof"],
        )
        material = {
            "schema_version": values["schema_version"],
            "finalization_plan_id": plan_id,
            "execution_id": execution_id,
            "run_id": run_id,
            "original_run_route": values["original_run_route"],
            "canonical_record_route": values["canonical_record_route"],
            "route_lineage_identity": (
                None if lineage is None else lineage.identity
            ),
            "clean_bundle_identity": (
                None if bundle is None else bundle.identity
            ),
            "path": path,
            "status": status,
            "failure": failure,
            "adjudication_result_id": (
                None
                if adjudication is None
                else adjudication.adjudication_result_id
            ),
            "news_risk_object_id": (
                None if risk is None else risk.news_risk_object_id
            ),
            "signal_gate_decision_id": (
                None if gate is None else gate.signal_gate_decision_id
            ),
            "clean_execution_record_id": (
                None if clean_record is None else clean_record.identity
            ),
            "terminal_record_id": (
                None if terminal is None else terminal.identity
            ),
            "request_hashes": (
                None if clean_record is None else clean_record.request_hashes
            ),
            "finalized_at": finalized_at,
            "reason_codes": reasons,
            "production_effect": _ZERO_EFFECT,
            "zero_production_effect_proof": _ZERO_PROOF,
        }
        result_id = _identity(
            values["finalization_result_id"],
            material,
            "finalization_result_id",
        )
        normalized = dict(values)
        normalized.update(
            finalization_result_id=result_id,
            finalization_plan_id=plan_id,
            execution_id=execution_id,
            run_id=run_id,
            path=path,
            status=status,
            failure=failure,
            finalized_at=finalized_at,
            reason_codes=reasons,
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.finalization_result_id


def _adjudication_policy() -> DeterministicAdjudicationPolicyV1:
    return DeterministicAdjudicationPolicyV1(
        policy_version="deterministic-adjudication-policy-v1",
        supported_routes=("L0", "L1", "L2"),
        agreement_values=(
            "SINGLE_REVIEW",
            "AGREEMENT",
            "QUALIFIED_AGREEMENT",
            "DISAGREEMENT",
            "CRITICAL_DISAGREEMENT",
            "FAIL_CLOSED",
        ),
        contradiction_values=("NONE", "PRESENT", "RESOLVED", "UNRESOLVED"),
        evidence_precedence=("SUFFICIENT", "INSUFFICIENT"),
        entity_precedence=("ACCEPTABLE", "MODERATE", "CRITICAL"),
        source_precedence=("ACCEPTABLE", "MODERATE", "CRITICAL"),
        material_risk_precedence=("NONE", "MATERIAL_RISK"),
        critical_disagreement_rules=("CRITICAL_UNRESOLVED_DISAGREEMENT",),
        fail_closed_reason_codes=(
            "INVALID_INPUT",
            "RESULT_NOT_COMPLETED",
            "ROUTE_RESULT_MISMATCH",
            "EVENT_BINDING_MISMATCH",
            "DECISION_BINDING_MISMATCH",
            "POLICY_MISMATCH",
            "CRITICAL_UNRESOLVED_DISAGREEMENT",
        ),
        deterministic_reason_order=(
            "MATERIAL_RISK_DISAGREEMENT",
            "CONTRADICTION_DISAGREEMENT",
            "ENTITY_DISAGREEMENT",
            "SOURCE_DISAGREEMENT",
            "EVIDENCE_DISAGREEMENT",
            "PROVIDERS_AGREE",
            "MATERIAL_FACTS_ALIGNED",
            "RISK_ASSESSMENTS_ALIGNED",
            "MINOR_EVIDENCE_DIFFERENCE",
            "MODERATE_ENTITY_DIFFERENCE",
            "MODERATE_SOURCE_DIFFERENCE",
            "CRITICAL_UNRESOLVED_DISAGREEMENT",
        ),
        maximum_reason_code_count=12,
        maximum_evidence_reference_count=16,
    )


def _news_risk_policy() -> NewsRiskPolicyV1:
    return NewsRiskPolicyV1(
        policy_version="news-risk-policy-v1",
        supported_adjudication_policy_versions=(
            "deterministic-adjudication-policy-v1",
        ),
        supported_routes=("L0", "L1", "L2"),
        outcome_to_risk_classification={
            "ACCEPT_DEEPSEEK": "CLEAR",
            "ACCEPT_CLAUDE": "CLEAR",
            "CONSENSUS_CONFIRMED": "CLEAR",
            "CONSENSUS_WITH_QUALIFICATION": "CAUTION",
            "MATERIAL_DISAGREEMENT": "ELEVATED",
            "INSUFFICIENT_EVIDENCE": "CAUTION",
            "FAIL_CLOSED": "FAIL_CLOSED",
        },
        ambiguity_precedence=("NONE", "MODERATE", "CRITICAL"),
        contradiction_precedence=(
            "NONE",
            "RESOLVED",
            "PRESENT",
            "UNRESOLVED",
        ),
        evidence_precedence=("SUFFICIENT", "INSUFFICIENT"),
        entity_precedence=("ACCEPTABLE", "MODERATE", "CRITICAL"),
        source_precedence=("ACCEPTABLE", "MODERATE", "CRITICAL"),
        material_risk_precedence=("NONE", "MATERIAL_RISK"),
        fail_closed_outcomes=("FAIL_CLOSED",),
        blocking_reason_codes=(
            "CRITICAL_MATERIAL_RISK",
            "CRITICAL_CONTRADICTION",
            "CRITICAL_ENTITY_CONCERN",
            "CRITICAL_SOURCE_CONCERN",
            "BLOCKING_ADJUDICATION_REASON",
            "MATERIAL_RISK_DISAGREEMENT",
            "CONTRADICTION_DISAGREEMENT",
            "ENTITY_DISAGREEMENT",
            "SOURCE_DISAGREEMENT",
            "CRITICAL_UNRESOLVED_DISAGREEMENT",
        ),
        caution_reason_codes=(
            "QUALIFIED_ADJUDICATION",
            "EVIDENCE_LIMITED",
            "MODERATE_ENTITY_CONCERN",
            "MODERATE_SOURCE_CONCERN",
        ),
        deterministic_reason_order=(
            "INVALID_ADJUDICATION",
            "UNSUPPORTED_POLICY",
            "FORGED_IDENTITY",
            "FAIL_CLOSED_ADJUDICATION",
            "CRITICAL_MATERIAL_RISK",
            "CRITICAL_CONTRADICTION",
            "CRITICAL_ENTITY_CONCERN",
            "CRITICAL_SOURCE_CONCERN",
            "BLOCKING_ADJUDICATION_REASON",
            "MATERIAL_DISAGREEMENT",
            "UNRESOLVED_CONTRADICTION",
            "MATERIAL_RISK_PRESENT",
            "INSUFFICIENT_EVIDENCE",
            "QUALIFIED_ADJUDICATION",
            "EVIDENCE_LIMITED",
            "MODERATE_ENTITY_CONCERN",
            "MODERATE_SOURCE_CONCERN",
            "ADJUDICATION_CONFIRMED",
            "NO_MATERIAL_NEWS_RISK",
            "EVIDENCE_SUFFICIENT",
        ),
        maximum_reason_code_count=20,
        maximum_evidence_reference_count=16,
    )


def _signal_gate_policy() -> SignalGatePolicyV1:
    return SignalGatePolicyV1(
        policy_version="signal-gate-policy-v1",
        supported_news_risk_policy_versions=("news-risk-policy-v1",),
        supported_routes=("L0", "L1", "L2"),
        supported_risk_classifications=(
            "CLEAR",
            "CAUTION",
            "ELEVATED",
            "BLOCKING",
            "FAIL_CLOSED",
        ),
        supported_news_gate_recommendations=(
            "NO_NEWS_RESTRICTION",
            "REQUIRE_CAUTION",
            "REQUIRE_BLOCK",
            "FAIL_CLOSED",
        ),
        risk_to_gate_state={
            "CLEAR": "OPEN",
            "CAUTION": "CAUTION",
            "ELEVATED": "BLOCKED",
            "BLOCKING": "BLOCKED",
            "FAIL_CLOSED": "FAIL_CLOSED",
        },
        recommendation_to_gate_state={
            "NO_NEWS_RESTRICTION": "OPEN",
            "REQUIRE_CAUTION": "CAUTION",
            "REQUIRE_BLOCK": "BLOCKED",
            "FAIL_CLOSED": "FAIL_CLOSED",
        },
        blocking_reason_codes=(
            "CRITICAL_MATERIAL_RISK",
            "CRITICAL_CONTRADICTION",
            "CRITICAL_ENTITY_CONCERN",
            "CRITICAL_SOURCE_CONCERN",
        ),
        caution_reason_codes=(
            "INSUFFICIENT_EVIDENCE",
            "EVIDENCE_LIMITED",
            "MODERATE_ENTITY_CONCERN",
            "MODERATE_SOURCE_CONCERN",
            "QUALIFIED_ADJUDICATION",
        ),
        fail_closed_reason_codes=(
            "FAIL_CLOSED_ADJUDICATION",
            "UNSUPPORTED_POLICY",
            "FORGED_IDENTITY",
            "INVALID_ADJUDICATION",
        ),
        deterministic_reason_order=(
            "INVALID_NEWS_RISK_OBJECT",
            "UNSUPPORTED_POLICY",
            "FORGED_NEWS_RISK_IDENTITY",
            "FAIL_CLOSED_NEWS_RISK",
            "FAIL_CLOSED_GATE_POLICY",
            "NEWS_RISK_BLOCKING",
            "CRITICAL_MATERIAL_RISK",
            "CRITICAL_CONTRADICTION",
            "CRITICAL_ENTITY_CONCERN",
            "CRITICAL_SOURCE_CONCERN",
            "BLOCKING_NEWS_REASON",
            "BLOCK_RECOMMENDED",
            "NEWS_RISK_ELEVATED",
            "NEWS_RISK_CAUTION",
            "CAUTION_RECOMMENDED",
            "LIMITED_EVIDENCE",
            "QUALIFIED_NEWS_ASSESSMENT",
            "NEWS_RISK_CLEAR",
            "NO_NEWS_RESTRICTION",
        ),
        maximum_reason_code_count=19,
        maximum_evidence_reference_count=16,
    )


def _sum_money(values: tuple[Decimal, ...]) -> Decimal:
    total = sum(values, Decimal("0"))
    return Decimal("0") if total == 0 else total.normalize()


class ShadowAdjudicationFinalizerV1:
    """Finalize one already completed shadow run deterministically."""

    __slots__ = (
        "_adjudication_policy",
        "_news_risk_policy",
        "_signal_gate_policy",
    )

    def __init__(self) -> None:
        self._adjudication_policy = _adjudication_policy()
        self._news_risk_policy = _news_risk_policy()
        self._signal_gate_policy = _signal_gate_policy()

    def finalize(
        self,
        plan: ShadowAdjudicationFinalizationPlanV1,
        *,
        terminal_record: ShadowTerminalExecutionRecordV1 | None = None,
    ) -> ShadowAdjudicationFinalizationResultV1:
        if type(plan) is not ShadowAdjudicationFinalizationPlanV1:
            raise ShadowAdjudicationFinalizerValidationError(
                "invalid finalization plan"
            )
        if plan.is_clean:
            if terminal_record is not None:
                raise ShadowAdjudicationFinalizerValidationError(
                    "clean and terminal outputs cannot coexist"
                )
            return self._finalize_clean(plan)
        return self._finalize_terminal(plan, terminal_record)

    def _finalize_clean(
        self,
        plan: ShadowAdjudicationFinalizationPlanV1,
    ) -> ShadowAdjudicationFinalizationResultV1:
        bundle = plan.clean_bundle
        if type(bundle) is not ShadowAdjudicationEvidenceBundleV1:
            raise ShadowAdjudicationFinalizerValidationError(
                "missing clean adjudication bundle"
            )
        lineage = bundle.route_lineage
        deepseek = bundle.deepseek_result
        decision = lineage.router_decisions[-1]
        claude = None if lineage.adjudication_route == "L0" else (
            bundle.claude_results[-1]
        )
        adjudication = adjudicate_review_results(
            deepseek,
            decision,
            claude,
            self._adjudication_policy,
        )
        if (
            type(adjudication) is not DeterministicAdjudicationResultV1
            or adjudication.route != lineage.adjudication_route
            or adjudication.event_snapshot_id
            != plan.shadow_input.approved_news_capture.event_id
            or adjudication.router_decision_id != decision.decision_id
            or adjudication.deepseek_semantic_result_id
            != deepseek.semantic_result_id
            or (
                claude is None
                and adjudication.claude_semantic_result_id is not None
            )
            or (
                claude is not None
                and adjudication.claude_semantic_result_id
                != claude.semantic_result_id
            )
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "adjudication result binding mismatch"
            )
        risk = build_news_risk_object(
            adjudication,
            self._news_risk_policy,
        )
        gate = evaluate_signal_gate(risk, self._signal_gate_policy)
        clean_record = self._clean_record(
            plan,
            bundle,
            adjudication,
            risk,
            gate,
        )
        return ShadowAdjudicationFinalizationResultV1(
            schema_version=(
                "phase11-shadow-adjudication-finalization-result-v1"
            ),
            finalization_result_id=None,
            finalization_plan_id=plan.identity,
            execution_id=plan.execution_id,
            run_id=plan.run_id,
            original_run_route=plan.run_plan.route,
            canonical_record_route=lineage.clean_record_route,
            route_lineage=lineage,
            clean_bundle=bundle,
            path=ShadowAdjudicationFinalizationPathV1.CLEAN,
            status=ShadowAdjudicationFinalizationStatusV1.FINALIZED,
            failure=ShadowAdjudicationFinalizationFailureV1.NONE,
            adjudication_result=adjudication,
            news_risk_object=risk,
            signal_gate_decision=gate,
            clean_execution_record=clean_record,
            terminal_record=None,
            finalized_at=plan.finalized_at,
            reason_codes=("CLEAN_FINALIZATION_COMPLETED",),
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )

    def _clean_record(
        self,
        plan: ShadowAdjudicationFinalizationPlanV1,
        bundle: ShadowAdjudicationEvidenceBundleV1,
        adjudication: DeterministicAdjudicationResultV1,
        risk: NewsRiskObjectV1,
        gate: SignalGateDecisionV1,
    ) -> ShadowExecutionRecordV1:
        run_plan = plan.run_plan
        run_result = plan.run_result
        lineage = bundle.route_lineage
        before = run_plan.budget_ledger_before
        after = run_result.ledger_after
        reservations = before.reservations
        usages = after.usage_records
        runtime_results = run_result.invocation_results
        actual_values = tuple(item.actual_cost for item in usages)
        actual_cost = (
            None
            if any(item is None for item in actual_values)
            else _sum_money(actual_values)
        )
        if (
            run_result.status != _CLEAN_STATUS
            or run_result.failure_class != "NONE"
            or run_result.reconciliation_state != "RESOLVED"
            or any(item.timeout_state != "NONE" for item in runtime_results)
            or any(
                item.circuit_state != "CLOSED" for item in runtime_results
            )
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "run is not clean-record admissible"
            )
        retry_state = (
            "RETRIED"
            if any(item.retry_state == "RETRIED" for item in runtime_results)
            else "NO_RETRY"
        )
        capture = plan.shadow_input.approved_news_capture
        control = plan.shadow_input.phase_09_control_projection
        return ShadowExecutionRecordV1(
            schema_version="phase11-shadow-execution-record-v1",
            shadow_input=plan.shadow_input,
            shadow_input_id=plan.shadow_input.shadow_input_id,
            shadow_input_identity=plan.shadow_input.identity,
            approved_news_capture_id=capture.identity,
            phase09_control_projection_id=control.identity,
            sample_plan_id=plan.shadow_input.sample_plan_id,
            execution_record_id=None,
            run_id=run_plan.run_id,
            event_id=capture.event_id,
            event_version=capture.event_version,
            budget_policy_id=before.policy.policy_id,
            budget_ledger_before=before,
            budget_ledger_after=after,
            budget_ledger_before_id=before.identity,
            budget_ledger_after_id=after.identity,
            prompt_version=bundle.typed_review_evidence[0].prompt_version,
            provider_review_schema_version=(
                bundle.typed_review_evidence[
                    0
                ].provider_review_schema_version
            ),
            routing_policy_version=(
                lineage.router_decisions[0].policy_version
            ),
            adjudication_policy_version=adjudication.policy_version,
            news_risk_policy_version=risk.policy_version,
            signal_gate_policy_version=gate.policy_version,
            route=lineage.clean_record_route,
            escalation_reason_codes=lineage.reason_codes,
            provider_identities=tuple(
                item.provider for item in reservations
            ),
            model_identities=tuple(item.model for item in reservations),
            model_versions=tuple(item.model for item in reservations),
            reservation_ids=tuple(item.identity for item in reservations),
            usage_record_ids=tuple(item.identity for item in usages),
            request_hashes=tuple(item.request_hash for item in usages),
            response_hashes=tuple(item.response_hash for item in usages),
            provider_verdicts=tuple(
                "DEEPSEEK_NEUTRAL"
                if item.provider == "DEEPSEEK"
                else "CLAUDE_NEUTRAL"
                for item in reservations
            ),
            input_tokens=sum(item.input_tokens for item in usages),
            output_tokens=sum(item.output_tokens for item in usages),
            estimated_cost=_sum_money(
                tuple(item.estimated_cost for item in usages)
            ),
            actual_cost=actual_cost,
            latency_ms=sum(item.latency_ms for item in usages),
            attempt_count=sum(item.attempt_count for item in usages),
            timeout_state="NONE",
            retry_state=retry_state,
            circuit_state="CLOSED",
            reconciliation_state="RESOLVED",
            reservation_statuses=tuple(
                item.status for item in reservations
            ),
            usage_statuses=tuple(
                item.reconciliation_status for item in usages
            ),
            execution_status="COMPLETED",
            started_at=run_result.started_at,
            completed_at=run_result.completed_at,
            adjudication_result=adjudication,
            adjudication_result_id=adjudication.adjudication_result_id,
            adjudicated_news_risk_status=risk.risk_classification,
            news_risk_object=risk,
            news_risk_object_id=risk.news_risk_object_id,
            signal_gate_decision=gate,
            signal_gate_decision_id=gate.signal_gate_decision_id,
            failure_class="NONE",
            reason_codes=("EXECUTION_COMPLETED",),
            evidence_refs=adjudication.evidence_refs,
            production_effect=_ZERO_EFFECT,
            no_candidate_mutation_proof=_ZERO_PROOF,
            no_production_signal_mutation_proof=_ZERO_PROOF,
            no_publication_proof=_ZERO_PROOF,
            no_telegram_delivery_proof=_ZERO_PROOF,
            no_quota_capacity_consumption_proof=_ZERO_PROOF,
            no_account_exchange_order_trading_proof=_ZERO_PROOF,
            detached_phase09_evidence_proof="DETACHED_PHASE09_ONLY",
            proof_version="phase11-no-production-effect-proof-v1",
        )

    def _finalize_terminal(
        self,
        plan: ShadowAdjudicationFinalizationPlanV1,
        terminal_record: ShadowTerminalExecutionRecordV1 | None,
    ) -> ShadowAdjudicationFinalizationResultV1:
        if terminal_record is None:
            terminal_record = ShadowTerminalExecutionRecordV1(
                schema_version="phase11-shadow-terminal-execution-record-v1",
                terminal_record_id=None,
                shadow_input=plan.shadow_input,
                run_plan=plan.run_plan,
                run_result=plan.run_result,
                route_lineage=None,
                finalized_at=plan.finalized_at,
                adjudication_state=(
                    ShadowTerminalAdjudicationStateV1.NOT_PERFORMED
                ),
                reason_codes=plan.run_result.reason_codes,
                production_effect=_ZERO_EFFECT,
                zero_production_effect_proof=_ZERO_PROOF,
            )
        if (
            type(terminal_record) is not ShadowTerminalExecutionRecordV1
            or terminal_record.shadow_input.identity
            != plan.shadow_input.identity
            or terminal_record.run_plan.identity != plan.run_plan.identity
            or terminal_record.run_result.identity != plan.run_result.identity
            or terminal_record.adjudication_state
            != ShadowTerminalAdjudicationStateV1.NOT_PERFORMED
        ):
            raise ShadowAdjudicationFinalizerValidationError(
                "terminal record binding mismatch"
            )
        return ShadowAdjudicationFinalizationResultV1(
            schema_version=(
                "phase11-shadow-adjudication-finalization-result-v1"
            ),
            finalization_result_id=None,
            finalization_plan_id=plan.identity,
            execution_id=plan.execution_id,
            run_id=plan.run_id,
            original_run_route=plan.run_plan.route,
            canonical_record_route=None,
            route_lineage=terminal_record.route_lineage,
            clean_bundle=None,
            path=ShadowAdjudicationFinalizationPathV1.TERMINAL,
            status=ShadowAdjudicationFinalizationStatusV1.FINALIZED,
            failure=ShadowAdjudicationFinalizationFailureV1.NONE,
            adjudication_result=None,
            news_risk_object=None,
            signal_gate_decision=None,
            clean_execution_record=None,
            terminal_record=terminal_record,
            finalized_at=plan.finalized_at,
            reason_codes=("TERMINAL_FINALIZATION_COMPLETED",),
            production_effect=_ZERO_EFFECT,
            zero_production_effect_proof=_ZERO_PROOF,
        )


__all__ = (
    "ShadowAdjudicationFinalizationFailureV1",
    "ShadowAdjudicationFinalizationPathV1",
    "ShadowAdjudicationFinalizationPlanV1",
    "ShadowAdjudicationFinalizationResultV1",
    "ShadowAdjudicationFinalizationStatusV1",
    "ShadowAdjudicationFinalizerV1",
    "ShadowAdjudicationFinalizerValidationError",
    "canonical_json_bytes",
    "lowercase_sha256",
)
