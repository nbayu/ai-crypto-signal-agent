"""Immutable Phase 11 shadow-execution evidence contract.

This module validates deterministic evidence objects only.  It performs no
provider invocation, persistence, environment access, or production action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.deterministic_adjudication_v1 import DeterministicAdjudicationResultV1
from engine.news_risk_object_v1 import NewsRiskObjectV1
from engine.phase_11_budget_control_v1 import BudgetLedgerV1
from engine.phase_11_shadow_input_contracts_v1 import ShadowEvaluationInputV1
from engine.signal_gate_v1 import SignalGateDecisionV1


UTC = timezone.utc

EXECUTION_STATUSES = (
    "COMPLETED",
    "FAILED",
    "NO_CALL",
    "RECONCILIATION_REQUIRED",
)
TIMEOUT_STATES = ("NONE", "CONNECTION_TIMEOUT", "RESPONSE_TIMEOUT")
RETRY_STATES = ("NOT_ATTEMPTED", "NO_RETRY", "RETRIED")
CIRCUIT_STATES = ("CLOSED", "OPEN", "HALF_OPEN")
RECONCILIATION_STATES = ("NOT_REQUIRED", "RESOLVED", "RECONCILIATION_REQUIRED")
FAILURE_CLASSES = (
    "NONE",
    "VALIDATION_FAILURE",
    "UNAUTHORIZED_INVOCATION",
    "BUDGET_DENIED",
    "TIMEOUT",
    "TRANSPORT_FAILURE",
    "PROVIDER_UNAVAILABLE",
    "CIRCUIT_OPEN",
    "MALFORMED_RESPONSE",
    "SCHEMA_MISMATCH",
    "IDENTITY_MISMATCH",
    "ADJUDICATION_FAILURE",
    "PERSISTENCE_FAILURE",
    "REPLAY_MISMATCH",
    "COMPARISON_FAILURE",
    "RECONCILIATION_REQUIRED",
)
PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
MODELS = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
ROUTES = ("L0", "L1", "L2")

_MODEL_PROVIDERS = {
    "DEEPSEEK_PRIMARY": "DEEPSEEK",
    "CLAUDE_SONNET_L1": "ANTHROPIC",
    "CLAUDE_OPUS_L2": "ANTHROPIC",
}
_EXPECTED_VERDICTS = {
    "DEEPSEEK": "DEEPSEEK_NEUTRAL",
    "ANTHROPIC": "CLAUDE_NEUTRAL",
}
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")

_FIELDS = frozenset(
    (
        "schema_version",
        "shadow_input",
        "shadow_input_id",
        "shadow_input_identity",
        "approved_news_capture_id",
        "phase09_control_projection_id",
        "sample_plan_id",
        "execution_record_id",
        "run_id",
        "event_id",
        "event_version",
        "budget_policy_id",
        "budget_ledger_before",
        "budget_ledger_after",
        "budget_ledger_before_id",
        "budget_ledger_after_id",
        "prompt_version",
        "provider_review_schema_version",
        "routing_policy_version",
        "adjudication_policy_version",
        "news_risk_policy_version",
        "signal_gate_policy_version",
        "route",
        "escalation_reason_codes",
        "provider_identities",
        "model_identities",
        "model_versions",
        "reservation_ids",
        "usage_record_ids",
        "request_hashes",
        "response_hashes",
        "provider_verdicts",
        "input_tokens",
        "output_tokens",
        "estimated_cost",
        "actual_cost",
        "latency_ms",
        "attempt_count",
        "timeout_state",
        "retry_state",
        "circuit_state",
        "reconciliation_state",
        "reservation_statuses",
        "usage_statuses",
        "execution_status",
        "started_at",
        "completed_at",
        "adjudication_result",
        "adjudication_result_id",
        "adjudicated_news_risk_status",
        "news_risk_object",
        "news_risk_object_id",
        "signal_gate_decision",
        "signal_gate_decision_id",
        "failure_class",
        "reason_codes",
        "evidence_refs",
        "production_effect",
        "no_candidate_mutation_proof",
        "no_production_signal_mutation_proof",
        "no_publication_proof",
        "no_telegram_delivery_proof",
        "no_quota_capacity_consumption_proof",
        "no_account_exchange_order_trading_proof",
        "detached_phase09_evidence_proof",
        "proof_version",
    )
)

_CHILD_FIELDS = frozenset(
    (
        "shadow_input",
        "budget_ledger_before",
        "budget_ledger_after",
        "adjudication_result",
        "news_risk_object",
        "signal_gate_decision",
    )
)


class ShadowExecutionRecordValidationError(ValueError):
    """Raised when shadow execution evidence fails closed."""


def _semantic_identifier_probe(disposition: str) -> str:
    """Exercise complete-identifier static checks for the safe term."""

    return disposition


def _money_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _money_text(value)
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowExecutionRecordValidationError("value is not canonical JSON") from error


def _digest(value: Any) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER_RE.fullmatch(value) is None:
        raise ShadowExecutionRecordValidationError(f"{field_name} is invalid")
    return value


def _hash(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or _HASH_RE.fullmatch(value) is None:
        raise ShadowExecutionRecordValidationError(f"{field_name} must be lowercase SHA-256")
    return value


def _nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ShadowExecutionRecordValidationError(f"{field_name} must be non-negative")
    return value


def _positive_int(value: Any, field_name: str) -> int:
    result = _nonnegative_int(value, field_name)
    if result == 0:
        raise ShadowExecutionRecordValidationError(f"{field_name} must be positive")
    return result


def _money(value: Any, field_name: str, *, optional: bool = False) -> Decimal | None:
    if optional and value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ShadowExecutionRecordValidationError(f"{field_name} must be a finite Decimal")
    if value < 0:
        raise ShadowExecutionRecordValidationError(f"{field_name} must not be negative")
    return Decimal("0") if value == 0 else value.normalize()


def _timestamp(value: Any, field_name: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowExecutionRecordValidationError(f"{field_name} must be timezone-aware")
        parsed = value.astimezone(UTC)
    elif isinstance(value, str) and _UTC_RE.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ShadowExecutionRecordValidationError(f"{field_name} is invalid") from error
    else:
        raise ShadowExecutionRecordValidationError(f"{field_name} must be canonical UTC")
    canonical = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return canonical.replace("+00:00", "Z").replace(".000000Z", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sequence(value: Any, field_name: str, *, allow_empty: bool = False) -> tuple[Any, ...]:
    if not isinstance(value, (tuple, list)):
        raise ShadowExecutionRecordValidationError(f"{field_name} is invalid")
    result = tuple(value)
    if not allow_empty and not result:
        raise ShadowExecutionRecordValidationError(f"{field_name} must not be empty")
    return result


def _identifiers(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool = False,
    unique: bool = True,
) -> tuple[str, ...]:
    result = tuple(_identifier(item, field_name) for item in _sequence(value, field_name, allow_empty=allow_empty))
    if unique and len(set(result)) != len(result):
        raise ShadowExecutionRecordValidationError(f"{field_name} contains duplicates")
    return result


def _hashes(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool = False,
    unique: bool = True,
) -> tuple[str, ...]:
    result = tuple(_hash(item, field_name) for item in _sequence(value, field_name, allow_empty=allow_empty))
    if unique and len(set(result)) != len(result):
        raise ShadowExecutionRecordValidationError(f"{field_name} contains duplicates")
    return result


def _reason_codes(value: Any, field_name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    items = _sequence(value, field_name, allow_empty=allow_empty)
    result = []
    for item in items:
        if not isinstance(item, str) or _REASON_RE.fullmatch(item) is None:
            raise ShadowExecutionRecordValidationError(f"{field_name} contains an invalid code")
        if item in result:
            raise ShadowExecutionRecordValidationError(f"{field_name} contains duplicates")
        result.append(item)
    return tuple(sorted(result))


def _sum_money(values: Any) -> Decimal:
    result = Decimal("0")
    for value in values:
        result += value
    return Decimal("0") if result == 0 else result.normalize()


def _prefix(before: tuple[str, ...], after: tuple[str, ...], field_name: str) -> None:
    if len(before) > len(after) or after[: len(before)] != before:
        raise ShadowExecutionRecordValidationError(f"{field_name} is not an append-only transition")


@dataclass(frozen=True, init=False)
class ShadowExecutionRecordV1:
    schema_version: str
    shadow_input: ShadowEvaluationInputV1
    shadow_input_id: str
    shadow_input_identity: str
    approved_news_capture_id: str
    phase09_control_projection_id: str
    sample_plan_id: str
    execution_record_id: str
    run_id: str
    event_id: str
    event_version: int
    budget_policy_id: str
    budget_ledger_before: BudgetLedgerV1
    budget_ledger_after: BudgetLedgerV1
    budget_ledger_before_id: str
    budget_ledger_after_id: str
    prompt_version: str
    provider_review_schema_version: str
    routing_policy_version: str
    adjudication_policy_version: str
    news_risk_policy_version: str
    signal_gate_policy_version: str
    route: str
    escalation_reason_codes: tuple[str, ...]
    provider_identities: tuple[str, ...]
    model_identities: tuple[str, ...]
    model_versions: tuple[str, ...]
    reservation_ids: tuple[str, ...]
    usage_record_ids: tuple[str, ...]
    request_hashes: tuple[str, ...]
    response_hashes: tuple[str, ...]
    provider_verdicts: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    estimated_cost: Decimal
    actual_cost: Decimal | None
    latency_ms: int
    attempt_count: int
    timeout_state: str
    retry_state: str
    circuit_state: str
    reconciliation_state: str
    reservation_statuses: tuple[str, ...]
    usage_statuses: tuple[str, ...]
    execution_status: str
    started_at: str
    completed_at: str
    adjudication_result: DeterministicAdjudicationResultV1
    adjudication_result_id: str
    adjudicated_news_risk_status: str
    news_risk_object: NewsRiskObjectV1
    news_risk_object_id: str
    signal_gate_decision: SignalGateDecisionV1
    signal_gate_decision_id: str
    failure_class: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    production_effect: str
    no_candidate_mutation_proof: str
    no_production_signal_mutation_proof: str
    no_publication_proof: str
    no_telegram_delivery_proof: str
    no_quota_capacity_consumption_proof: str
    no_account_exchange_order_trading_proof: str
    detached_phase09_evidence_proof: str
    proof_version: str

    def __init__(self, **values: Any) -> None:
        if set(values) != _FIELDS:
            raise ShadowExecutionRecordValidationError("invalid shadow execution record fields")
        if values["schema_version"] != "phase11-shadow-execution-record-v1":
            raise ShadowExecutionRecordValidationError("schema_version is unsupported")

        shadow_input = values["shadow_input"]
        before = values["budget_ledger_before"]
        after = values["budget_ledger_after"]
        adjudication = values["adjudication_result"]
        risk = values["news_risk_object"]
        gate = values["signal_gate_decision"]
        if type(shadow_input) is not ShadowEvaluationInputV1:
            raise ShadowExecutionRecordValidationError("shadow_input is invalid")
        if type(before) is not BudgetLedgerV1 or type(after) is not BudgetLedgerV1:
            raise ShadowExecutionRecordValidationError("budget ledger evidence is invalid")
        if type(adjudication) is not DeterministicAdjudicationResultV1:
            raise ShadowExecutionRecordValidationError("adjudication_result is invalid")
        if type(risk) is not NewsRiskObjectV1:
            raise ShadowExecutionRecordValidationError("news_risk_object is invalid")
        if type(gate) is not SignalGateDecisionV1:
            raise ShadowExecutionRecordValidationError("signal_gate_decision is invalid")

        capture = shadow_input.approved_news_capture
        control = shadow_input.phase_09_control_projection
        normalized: dict[str, Any] = {
            "schema_version": values["schema_version"],
            "shadow_input": shadow_input,
            "shadow_input_id": _identifier(values["shadow_input_id"], "shadow_input_id"),
            "shadow_input_identity": _hash(values["shadow_input_identity"], "shadow_input_identity"),
            "approved_news_capture_id": _hash(values["approved_news_capture_id"], "approved_news_capture_id"),
            "phase09_control_projection_id": _hash(values["phase09_control_projection_id"], "phase09_control_projection_id"),
            "sample_plan_id": _identifier(values["sample_plan_id"], "sample_plan_id"),
            "run_id": _identifier(values["run_id"], "run_id"),
            "event_id": _hash(values["event_id"], "event_id"),
            "event_version": _positive_int(values["event_version"], "event_version"),
            "budget_policy_id": _identifier(values["budget_policy_id"], "budget_policy_id"),
            "budget_ledger_before": before,
            "budget_ledger_after": after,
            "budget_ledger_before_id": _hash(values["budget_ledger_before_id"], "budget_ledger_before_id"),
            "budget_ledger_after_id": _hash(values["budget_ledger_after_id"], "budget_ledger_after_id"),
            "prompt_version": _identifier(values["prompt_version"], "prompt_version"),
            "provider_review_schema_version": _identifier(values["provider_review_schema_version"], "provider_review_schema_version"),
            "routing_policy_version": _identifier(values["routing_policy_version"], "routing_policy_version"),
            "adjudication_policy_version": _identifier(values["adjudication_policy_version"], "adjudication_policy_version"),
            "news_risk_policy_version": _identifier(values["news_risk_policy_version"], "news_risk_policy_version"),
            "signal_gate_policy_version": _identifier(values["signal_gate_policy_version"], "signal_gate_policy_version"),
            "route": values["route"],
            "escalation_reason_codes": _reason_codes(values["escalation_reason_codes"], "escalation_reason_codes", allow_empty=True),
            "provider_identities": _identifiers(values["provider_identities"], "provider_identities", unique=False),
            "model_identities": _identifiers(values["model_identities"], "model_identities"),
            "model_versions": _identifiers(values["model_versions"], "model_versions"),
            "reservation_ids": _hashes(values["reservation_ids"], "reservation_ids"),
            "usage_record_ids": _hashes(values["usage_record_ids"], "usage_record_ids", allow_empty=True),
            "request_hashes": _hashes(
                values["request_hashes"],
                "request_hashes",
                allow_empty=True,
                unique=False,
            ),
            "response_hashes": _hashes(values["response_hashes"], "response_hashes", allow_empty=True),
            "provider_verdicts": _identifiers(values["provider_verdicts"], "provider_verdicts", allow_empty=True, unique=False),
            "input_tokens": _nonnegative_int(values["input_tokens"], "input_tokens"),
            "output_tokens": _nonnegative_int(values["output_tokens"], "output_tokens"),
            "estimated_cost": _money(values["estimated_cost"], "estimated_cost"),
            "actual_cost": _money(values["actual_cost"], "actual_cost", optional=True),
            "latency_ms": _nonnegative_int(values["latency_ms"], "latency_ms"),
            "attempt_count": _nonnegative_int(values["attempt_count"], "attempt_count"),
            "timeout_state": values["timeout_state"],
            "retry_state": values["retry_state"],
            "circuit_state": values["circuit_state"],
            "reconciliation_state": values["reconciliation_state"],
            "reservation_statuses": _identifiers(values["reservation_statuses"], "reservation_statuses", unique=False),
            "usage_statuses": _identifiers(values["usage_statuses"], "usage_statuses", allow_empty=True, unique=False),
            "execution_status": values["execution_status"],
            "started_at": _timestamp(values["started_at"], "started_at"),
            "completed_at": _timestamp(values["completed_at"], "completed_at"),
            "adjudication_result": adjudication,
            "adjudication_result_id": _hash(values["adjudication_result_id"], "adjudication_result_id"),
            "adjudicated_news_risk_status": _identifier(values["adjudicated_news_risk_status"], "adjudicated_news_risk_status"),
            "news_risk_object": risk,
            "news_risk_object_id": _hash(values["news_risk_object_id"], "news_risk_object_id"),
            "signal_gate_decision": gate,
            "signal_gate_decision_id": _hash(values["signal_gate_decision_id"], "signal_gate_decision_id"),
            "failure_class": values["failure_class"],
            "reason_codes": _reason_codes(values["reason_codes"], "reason_codes"),
            "evidence_refs": _identifiers(values["evidence_refs"], "evidence_refs"),
            "production_effect": values["production_effect"],
            "no_candidate_mutation_proof": values["no_candidate_mutation_proof"],
            "no_production_signal_mutation_proof": values["no_production_signal_mutation_proof"],
            "no_publication_proof": values["no_publication_proof"],
            "no_telegram_delivery_proof": values["no_telegram_delivery_proof"],
            "no_quota_capacity_consumption_proof": values["no_quota_capacity_consumption_proof"],
            "no_account_exchange_order_trading_proof": values["no_account_exchange_order_trading_proof"],
            "detached_phase09_evidence_proof": values["detached_phase09_evidence_proof"],
            "proof_version": _identifier(values["proof_version"], "proof_version"),
        }

        self._validate_input(normalized, shadow_input, capture, control)
        self._validate_ledger(normalized, before, after)
        self._validate_route(normalized, after)
        self._validate_output_chain(normalized, capture, adjudication, risk, gate)
        self._validate_operations(normalized, after)
        self._validate_request_hashes(normalized)
        self._validate_terminal_state(normalized)
        self._validate_zero_effect(normalized)

        material = {
            key: item
            for key, item in normalized.items()
            if key not in _CHILD_FIELDS
        }
        expected_identity = _digest(material)
        supplied_identity = values["execution_record_id"]
        if supplied_identity is not None and _hash(supplied_identity, "execution_record_id") != expected_identity:
            raise ShadowExecutionRecordValidationError("execution_record_id does not match canonical evidence")
        normalized["execution_record_id"] = expected_identity
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @staticmethod
    def _validate_input(values: dict[str, Any], shadow_input: ShadowEvaluationInputV1, capture: Any, control: Any) -> None:
        expected = {
            "shadow_input_id": shadow_input.shadow_input_id,
            "shadow_input_identity": shadow_input.identity,
            "approved_news_capture_id": capture.identity,
            "phase09_control_projection_id": control.identity,
            "sample_plan_id": shadow_input.sample_plan_id,
            "event_id": capture.event_id,
            "event_version": capture.event_version,
        }
        if any(values[name] != item for name, item in expected.items()):
            raise ShadowExecutionRecordValidationError("shadow input binding mismatch")

    @staticmethod
    def _validate_ledger(values: dict[str, Any], before: BudgetLedgerV1, after: BudgetLedgerV1) -> None:
        if before.policy.identity != after.policy.identity or before.ledger_id != after.ledger_id:
            raise ShadowExecutionRecordValidationError("budget policy or ledger lineage mismatch")
        if values["budget_policy_id"] != before.policy.policy_id:
            raise ShadowExecutionRecordValidationError("budget_policy_id binding mismatch")
        if values["budget_ledger_before_id"] != before.identity or values["budget_ledger_after_id"] != after.identity:
            raise ShadowExecutionRecordValidationError("budget ledger identity mismatch")
        if after.sequence < before.sequence:
            raise ShadowExecutionRecordValidationError("budget ledger sequence regressed")
        before_reservations = tuple(item.identity for item in before.reservations)
        after_reservations = tuple(item.identity for item in after.reservations)
        before_usage = tuple(item.identity for item in before.usage_records)
        after_usage = tuple(item.identity for item in after.usage_records)
        _prefix(before_reservations, after_reservations, "reservation evidence")
        _prefix(before_usage, after_usage, "usage evidence")
        if values["reservation_ids"] != after_reservations:
            raise ShadowExecutionRecordValidationError("reservation identity evidence mismatch")
        if values["usage_record_ids"] != after_usage:
            raise ShadowExecutionRecordValidationError("usage identity evidence mismatch")
        known = {item.reservation_id: item for item in after.reservations}
        for usage in after.usage_records:
            reservation = known.get(usage.reservation_id)
            if reservation is None:
                raise ShadowExecutionRecordValidationError("usage has no reservation")
            if (
                usage.policy_id != reservation.policy_id
                or usage.run_id != reservation.run_id
                or usage.call_id != reservation.call_id
                or usage.provider != reservation.provider
                or usage.model != reservation.model
            ):
                raise ShadowExecutionRecordValidationError("usage and reservation binding mismatch")

    @staticmethod
    def _validate_route(values: dict[str, Any], after: BudgetLedgerV1) -> None:
        route = values["route"]
        if route not in ROUTES:
            raise ShadowExecutionRecordValidationError("route is unsupported")
        reservations = after.reservations
        providers = tuple(item.provider for item in reservations)
        models = tuple(item.model for item in reservations)
        if values["provider_identities"] != providers or values["model_identities"] != models:
            raise ShadowExecutionRecordValidationError("provider/model evidence mismatch")
        if len(values["model_versions"]) != len(models):
            raise ShadowExecutionRecordValidationError("model version evidence mismatch")
        if any(_MODEL_PROVIDERS.get(model) != provider for provider, model in zip(providers, models)):
            raise ShadowExecutionRecordValidationError("provider/model binding mismatch")
        if route == "L0":
            expected = ("DEEPSEEK_PRIMARY",)
        elif route == "L1":
            expected = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1")
        elif "CLAUDE_SONNET_L1" in models:
            expected = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
            if values["escalation_reason_codes"] != ("L1_TO_L2",):
                raise ShadowExecutionRecordValidationError("L1-to-L2 evidence is incomplete")
        else:
            expected = ("DEEPSEEK_PRIMARY", "CLAUDE_OPUS_L2")
        if models != expected:
            raise ShadowExecutionRecordValidationError("route reviewer tiers are invalid")
        expected_verdicts = tuple(_EXPECTED_VERDICTS[item] for item in providers)
        if values["provider_verdicts"] != expected_verdicts:
            raise ShadowExecutionRecordValidationError("provider verdict evidence is invalid")

    @staticmethod
    def _validate_output_chain(values: dict[str, Any], capture: Any, adjudication: DeterministicAdjudicationResultV1, risk: NewsRiskObjectV1, gate: SignalGateDecisionV1) -> None:
        if values["adjudication_result_id"] != adjudication.adjudication_result_id:
            raise ShadowExecutionRecordValidationError("adjudication identity mismatch")
        if values["adjudication_policy_version"] != adjudication.policy_version:
            raise ShadowExecutionRecordValidationError("adjudication policy mismatch")
        if adjudication.event_snapshot_id != capture.event_id or adjudication.route != values["route"]:
            raise ShadowExecutionRecordValidationError("adjudication upstream binding mismatch")
        if (
            values["news_risk_object_id"] != risk.news_risk_object_id
            or values["news_risk_policy_version"] != risk.policy_version
            or risk.event_snapshot_id != capture.event_id
            or risk.adjudication_policy_version != adjudication.policy_version
            or risk.adjudication_result_id != adjudication.adjudication_result_id
            or risk.route != adjudication.route
            or risk.final_ambiguity_state != adjudication.final_ambiguity_state
            or risk.final_contradiction_state != adjudication.final_contradiction_state
            or risk.final_evidence_state != adjudication.final_evidence_state
            or risk.final_entity_state != adjudication.final_entity_state
            or risk.final_source_state != adjudication.final_source_state
            or risk.final_material_risk_state != adjudication.final_material_risk_state
            or values["adjudicated_news_risk_status"] != risk.risk_classification
        ):
            raise ShadowExecutionRecordValidationError("News Risk binding mismatch")
        if (
            values["signal_gate_decision_id"] != gate.signal_gate_decision_id
            or values["signal_gate_policy_version"] != gate.policy_version
            or gate.event_snapshot_id != capture.event_id
            or gate.news_risk_policy_version != risk.policy_version
            or gate.news_risk_object_id != risk.news_risk_object_id
            or gate.route != risk.route
            or gate.risk_classification != risk.risk_classification
            or gate.news_gate_recommendation != risk.news_gate_recommendation
        ):
            raise ShadowExecutionRecordValidationError("Signal Gate binding mismatch")

    @staticmethod
    def _validate_operations(values: dict[str, Any], after: BudgetLedgerV1) -> None:
        usages = after.usage_records
        if any(item.run_id != values["run_id"] for item in after.reservations):
            raise ShadowExecutionRecordValidationError("reservation run binding mismatch")
        if any(item.run_id != values["run_id"] for item in usages):
            raise ShadowExecutionRecordValidationError("usage run binding mismatch")
        expected_requests = tuple(item.request_hash for item in usages)
        expected_responses = tuple(item.response_hash for item in usages)
        expected_reservation_statuses = tuple(item.status for item in after.reservations)
        expected_usage_statuses = tuple(item.reconciliation_status for item in usages)
        if values["request_hashes"] != expected_requests or values["response_hashes"] != expected_responses:
            raise ShadowExecutionRecordValidationError("request/response hash evidence mismatch")
        if values["reservation_statuses"] != expected_reservation_statuses or values["usage_statuses"] != expected_usage_statuses:
            raise ShadowExecutionRecordValidationError("reservation/usage status evidence mismatch")
        if values["input_tokens"] != sum(item.input_tokens for item in usages):
            raise ShadowExecutionRecordValidationError("input token aggregate mismatch")
        if values["output_tokens"] != sum(item.output_tokens for item in usages):
            raise ShadowExecutionRecordValidationError("output token aggregate mismatch")
        if values["estimated_cost"] != _sum_money(item.estimated_cost for item in usages):
            raise ShadowExecutionRecordValidationError("estimated cost aggregate mismatch")
        actual_values = tuple(item.actual_cost for item in usages)
        expected_actual = None if any(item is None for item in actual_values) else _sum_money(actual_values)
        if values["actual_cost"] != expected_actual:
            raise ShadowExecutionRecordValidationError("actual cost aggregate mismatch")
        if values["latency_ms"] != sum(item.latency_ms for item in usages):
            raise ShadowExecutionRecordValidationError("latency aggregate mismatch")
        if values["attempt_count"] != sum(item.attempt_count for item in usages):
            raise ShadowExecutionRecordValidationError("attempt aggregate mismatch")
        if after.committed_input_tokens != sum(
            item.input_tokens for item in usages if item.actual_cost is not None and item.reconciliation_status in {"RESOLVED", "RELEASED"}
        ):
            raise ShadowExecutionRecordValidationError("ledger input aggregate mismatch")
        if after.committed_output_tokens != sum(
            item.output_tokens for item in usages if item.actual_cost is not None and item.reconciliation_status in {"RESOLVED", "RELEASED"}
        ):
            raise ShadowExecutionRecordValidationError("ledger output aggregate mismatch")
        for usage in usages:
            if _parsed(usage.started_at) < _parsed(values["started_at"]) or _parsed(usage.completed_at) > _parsed(values["completed_at"]):
                raise ShadowExecutionRecordValidationError("provider timing is outside execution timing")

    @staticmethod
    def _validate_request_hashes(values: dict[str, Any]) -> None:
        requests = values["request_hashes"]
        if len(set(requests)) == len(requests):
            return
        authorized_claude_reuse = (
            values["route"] == "L2"
            and values["escalation_reason_codes"] == ("L1_TO_L2",)
            and values["provider_identities"]
            == ("DEEPSEEK", "ANTHROPIC", "ANTHROPIC")
            and values["model_identities"]
            == (
                "DEEPSEEK_PRIMARY",
                "CLAUDE_SONNET_L1",
                "CLAUDE_OPUS_L2",
            )
            and len(requests) == 3
            and requests[0] != requests[1]
            and requests[1] == requests[2]
            and len(set(requests)) == 2
            and len(set(values["reservation_ids"])) == 3
            and len(set(values["usage_record_ids"])) == 3
            and len(set(values["response_hashes"])) == 3
        )
        if not authorized_claude_reuse:
            raise ShadowExecutionRecordValidationError(
                "request_hashes contains unauthorized duplicates"
            )

    @staticmethod
    def _validate_terminal_state(values: dict[str, Any]) -> None:
        if values["execution_status"] not in EXECUTION_STATUSES:
            raise ShadowExecutionRecordValidationError("execution_status is unsupported")
        if values["timeout_state"] not in TIMEOUT_STATES:
            raise ShadowExecutionRecordValidationError("timeout_state is unsupported")
        if values["retry_state"] not in RETRY_STATES:
            raise ShadowExecutionRecordValidationError("retry_state is unsupported")
        if values["circuit_state"] not in CIRCUIT_STATES:
            raise ShadowExecutionRecordValidationError("circuit_state is unsupported")
        if values["reconciliation_state"] not in RECONCILIATION_STATES:
            raise ShadowExecutionRecordValidationError("reconciliation_state is unsupported")
        if values["failure_class"] not in FAILURE_CLASSES:
            raise ShadowExecutionRecordValidationError("failure_class is unsupported")
        if _parsed(values["completed_at"]) < _parsed(values["started_at"]):
            raise ShadowExecutionRecordValidationError("completed_at is earlier than started_at")
        if values["execution_status"] == "COMPLETED":
            if values["failure_class"] != "NONE" or values["timeout_state"] != "NONE":
                raise ShadowExecutionRecordValidationError("completed execution has failure evidence")
            if values["reconciliation_state"] != "RESOLVED":
                raise ShadowExecutionRecordValidationError("completed execution is not reconciled")
        if values["retry_state"] == "RETRIED" and values["attempt_count"] < 2:
            raise ShadowExecutionRecordValidationError("retry evidence is inconsistent")
        if values["retry_state"] == "NOT_ATTEMPTED" and values["attempt_count"] != 0:
            raise ShadowExecutionRecordValidationError("no-attempt evidence is inconsistent")
        if values["reconciliation_state"] == "RECONCILIATION_REQUIRED" and values["actual_cost"] is not None:
            raise ShadowExecutionRecordValidationError("unresolved evidence claims final cost")

    @staticmethod
    def _validate_zero_effect(values: dict[str, Any]) -> None:
        if values["production_effect"] != "NONE":
            raise ShadowExecutionRecordValidationError("production_effect must be NONE")
        for field_name in (
            "no_candidate_mutation_proof",
            "no_production_signal_mutation_proof",
            "no_publication_proof",
            "no_telegram_delivery_proof",
            "no_quota_capacity_consumption_proof",
            "no_account_exchange_order_trading_proof",
        ):
            if values[field_name] != "PROVEN_NONE":
                raise ShadowExecutionRecordValidationError(f"{field_name} is invalid")
        if values["detached_phase09_evidence_proof"] != "DETACHED_PHASE09_ONLY":
            raise ShadowExecutionRecordValidationError("detached Phase 09 proof is invalid")

    @property
    def identity(self) -> str:
        return self.execution_record_id


__all__ = (
    "CIRCUIT_STATES",
    "EXECUTION_STATUSES",
    "FAILURE_CLASSES",
    "RECONCILIATION_STATES",
    "RETRY_STATES",
    "ShadowExecutionRecordV1",
    "ShadowExecutionRecordValidationError",
    "TIMEOUT_STATES",
)
