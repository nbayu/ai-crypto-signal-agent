"""Detached fail-closed composition of the committed E3-E6 contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Mapping

from engine import active_signal_ledger_v1 as active
from engine.e3_actionable_admission_v1 import E3ActionableAdmissionResultV1
from engine.e4_duplicate_protection_composition_v1 import (
    E4DuplicateProtectionCompositionResultV1,
    compose_e4_duplicate_protection_v1,
)
from engine.e4_thesis_fingerprint_v1 import build_e4_thesis_fingerprint
from engine.e4_thesis_history_store_v1 import load_e4_thesis_history_store_v1
from engine.e5_technical_review_payload_v1 import (
    E5TechnicalReviewPayloadV1,
    build_e5_technical_review_payload_v1,
)
from engine.e6_claude_daily_usage_store_v1 import E6ClaudeDailyUsageStorePortV1
from engine.e6_durable_review_execution_v1 import (
    E6DurableReviewExecutionResultV1,
    execute_e6_durable_review_v1,
)
from engine.e6_owner_state_lifecycle_binding_v1 import (
    HOLD_CONFLICT,
    E6OwnerStateLifecycleBindingResultV1,
    bind_e6_publication_to_owner_state_v1,
)
from engine.e6_publication_eligibility_v1 import (
    E6PublicationEligibilityResultV1,
    evaluate_e6_publication_eligibility_v1,
)
from engine.e6_publication_envelope_v1 import (
    E6PublicationEnvelopeV1,
    build_e6_publication_envelope_v1,
)
from engine.e6_python_final_strategy_gate_v1 import (
    E6PythonFinalStrategyGateResultV1,
    candidate_authority_sha256_v1,
    evaluate_e6_python_final_strategy_gate_v1,
)
from engine.e6_telegram_human_formatter_v1 import format_e6_signal_message_v1
from engine.mode_profile_v1 import ModeProfileV1, get_mode_profile
from engine.mode_scan_execution_evidence_v1 import (
    ModeOiExecutionEvidenceV1,
    ModeScanExecutionResultV1,
    ModeTimeframeExecutionEvidenceV1,
)
from engine.news_event_contract_v1 import NormalizedNewsEventV1
from engine.news_risk_object_v1 import NewsRiskObjectV1
from engine.production_candidate_authority_v1 import ProductionCandidateAuthorityV1
from engine.outcome_tracker_v4 import validate_outcome_invocation_id
from engine.e6_production_news_evidence_v1 import (
    NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE,
    RELEVANT_NEWS_PRESENT,
    E6ProductionNewsEvidenceV1,
)


E6_INTEGRATED_ORCHESTRATOR_VERSION = "e6-integrated-orchestrator-v1"
E6_INTEGRATED_ORCHESTRATOR_SCHEMA = (
    "ai-crypto-signal-agent.e6-integrated-orchestrator.v1"
)

COMPLETE = "COMPLETE"
HOLD = "HOLD"
NO_TRADE = "NO_TRADE"

STAGE_1_VALIDATE_REQUEST_AND_LINEAGE = "STAGE_1_VALIDATE_REQUEST_AND_LINEAGE"
STAGE_2_E3_ACTIONABLE_ADMISSION = "STAGE_2_E3_ACTIONABLE_ADMISSION"
STAGE_3_E4_DUPLICATE_PROTECTION = "STAGE_3_E4_DUPLICATE_PROTECTION"
STAGE_4_DURABLE_E5_EXECUTION = "STAGE_4_DURABLE_E5_EXECUTION"
STAGE_5_PYTHON_FINAL_GATE = "STAGE_5_PYTHON_FINAL_GATE"
STAGE_6_PUBLICATION_ELIGIBILITY = "STAGE_6_PUBLICATION_ELIGIBILITY"
STAGE_7_PUBLICATION_ENVELOPE = "STAGE_7_PUBLICATION_ENVELOPE"
STAGE_8_HUMAN_PRESENTATION = "STAGE_8_HUMAN_PRESENTATION"
STAGE_9_OWNER_LIFECYCLE_BINDING = "STAGE_9_OWNER_LIFECYCLE_BINDING"
STAGE_10_COMPLETE = "STAGE_10_COMPLETE"

_STAGES = (
    STAGE_1_VALIDATE_REQUEST_AND_LINEAGE,
    STAGE_2_E3_ACTIONABLE_ADMISSION,
    STAGE_3_E4_DUPLICATE_PROTECTION,
    STAGE_4_DURABLE_E5_EXECUTION,
    STAGE_5_PYTHON_FINAL_GATE,
    STAGE_6_PUBLICATION_ELIGIBILITY,
    STAGE_7_PUBLICATION_ENVELOPE,
    STAGE_8_HUMAN_PRESENTATION,
    STAGE_9_OWNER_LIFECYCLE_BINDING,
    STAGE_10_COMPLETE,
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SIGNAL_ID = re.compile(r"^PSG-[0-9a-f]{64}$")
_DELIVERY_ID = re.compile(r"^PDL-[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ERROR = "invalid E6 integrated orchestrator"


def _fail() -> None:
    raise ValueError(_ERROR)


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _stable(value: object) -> object:
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float:
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _stable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_stable(item) for item in value]
    if is_dataclass(value):
        return {item.name: _stable(getattr(value, item.name)) for item in fields(value)}
    _fail()


def _canonical_json(value: Mapping[str, object]) -> str:
    return json.dumps(
        _stable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _hash(value: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _valid_sha256(value: object) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class E6IntegratedOrchestratorRequestV1:
    actionable_admission: E3ActionableAdmissionResultV1
    candidate_authority: ProductionCandidateAuthorityV1
    mode_profile: ModeProfileV1
    mode_execution_evidence: tuple[
        ModeScanExecutionResultV1,
        tuple[ModeTimeframeExecutionEvidenceV1, ...],
        ModeOiExecutionEvidenceV1,
    ]
    normalized_news_events: tuple[NormalizedNewsEventV1, ...]
    news_risk_object: NewsRiskObjectV1 | None
    price_exited_zone: bool
    deterministic_hard_gates_passed: bool
    pre_review_score: int
    mode_score_floor: int
    commit_timestamp: str
    deepseek_measured_input_tokens: int | None
    deepseek_requested_output_tokens: int | None
    claude_measured_input_tokens: int | None
    claude_requested_output_tokens: int | None
    publication_signal_id: str
    publication_delivery_id: str
    publication_published_at: str
    publication_source_payload_hash: str
    publication_payload_hash: str
    publication_content_hash: str | None
    publication_symbol: str
    publication_mode: str
    news_evidence: E6ProductionNewsEvidenceV1 | None = None
    production_outcome_invocation_id: str | None = None
    production_due_window_occurrence_id: str | None = None
    production_observed_at: str | None = None
    production_evidence_sha256: str | None = None
    request_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            _require(type(self.actionable_admission) is E3ActionableAdmissionResultV1)
            self.actionable_admission.__post_init__()
            _require(type(self.candidate_authority) is ProductionCandidateAuthorityV1)
            self.candidate_authority.__post_init__()
            _require(type(self.mode_profile) is ModeProfileV1)
            self.mode_profile.__post_init__()
            _require(type(self.mode_execution_evidence) is tuple)
            _require(len(self.mode_execution_evidence) == 3)
            _require(type(self.normalized_news_events) is tuple)
            _require(
                all(type(item) is NormalizedNewsEventV1 for item in self.normalized_news_events)
            )
            if self.news_evidence is None:
                _require(bool(self.normalized_news_events))
                _require(type(self.news_risk_object) is NewsRiskObjectV1)
            else:
                _require(type(self.news_evidence) is E6ProductionNewsEvidenceV1)
                self.news_evidence.__post_init__()
                _require(
                    self.normalized_news_events
                    == self.news_evidence.normalized_news_events
                    and self.news_risk_object == self.news_evidence.news_risk_object
                )
            for value in (
                self.price_exited_zone,
                self.deterministic_hard_gates_passed,
            ):
                _require(type(value) is bool)
            for value in (self.pre_review_score, self.mode_score_floor):
                _require(type(value) is int and value >= 0)
            deepseek_none = (
                self.deepseek_measured_input_tokens is None
                and self.deepseek_requested_output_tokens is None
            )
            deepseek_ints = (
                type(self.deepseek_measured_input_tokens) is int
                and self.deepseek_measured_input_tokens >= 0
                and type(self.deepseek_requested_output_tokens) is int
                and self.deepseek_requested_output_tokens >= 0
            )
            _require(deepseek_none or deepseek_ints)
            claude_none = (
                self.claude_measured_input_tokens is None
                and self.claude_requested_output_tokens is None
            )
            claude_ints = (
                type(self.claude_measured_input_tokens) is int
                and self.claude_measured_input_tokens >= 0
                and type(self.claude_requested_output_tokens) is int
                and self.claude_requested_output_tokens >= 0
            )
            _require(claude_none or claude_ints)
            _require(_UTC.fullmatch(self.commit_timestamp) is not None)
            _require(_SIGNAL_ID.fullmatch(self.publication_signal_id) is not None)
            _require(_DELIVERY_ID.fullmatch(self.publication_delivery_id) is not None)
            _require(_UTC.fullmatch(self.publication_published_at) is not None)
            for value in (
                self.publication_source_payload_hash,
                self.publication_payload_hash,
            ):
                _require(_valid_sha256(value))
            _require(
                self.publication_content_hash is None
                or _valid_sha256(self.publication_content_hash)
            )
            _require(type(self.publication_symbol) is str and bool(self.publication_symbol))
            _require(self.publication_mode in active.STYLES)
            production_context = (
                self.production_outcome_invocation_id,
                self.production_due_window_occurrence_id,
                self.production_observed_at,
                self.production_evidence_sha256,
            )
            _require(
                all(value is None for value in production_context)
                or all(type(value) is str and bool(value) for value in production_context)
            )
            if self.production_outcome_invocation_id is not None:
                validate_outcome_invocation_id(
                    self.production_outcome_invocation_id
                )
                _require(
                    re.fullmatch(
                        r"e6dw1:[0-9a-f]{64}",
                        self.production_due_window_occurrence_id,
                    )
                    is not None
                )
                _require(_UTC.fullmatch(self.production_observed_at) is not None)
                _require(_valid_sha256(self.production_evidence_sha256))
            object.__setattr__(self, "request_sha256", _hash(_request_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {**_request_preimage(self), "request_sha256": self.request_sha256}


def _request_preimage(request: E6IntegratedOrchestratorRequestV1) -> dict[str, object]:
    return {
        item.name: _stable(getattr(request, item.name))
        for item in fields(E6IntegratedOrchestratorRequestV1)
        if item.name != "request_sha256"
    }


@dataclass(frozen=True, slots=True)
class E6IntegratedOrchestratorPortsV1:
    e4_authorized_store_root: Path
    e4_store_path: Path
    usage_store: E6ClaudeDailyUsageStorePortV1
    active_ledger_path: Path
    deepseek_transport: Callable[[object], object]
    claude_transport: Callable[[object], object]

    def __post_init__(self) -> None:
        try:
            _require(isinstance(self.e4_authorized_store_root, Path))
            _require(isinstance(self.e4_store_path, Path))
            _require(isinstance(self.active_ledger_path, Path))
            _require(isinstance(self.usage_store, E6ClaudeDailyUsageStorePortV1))
            _require(callable(self.deepseek_transport))
            _require(callable(self.claude_transport))
        except Exception:
            _fail()


@dataclass(frozen=True, slots=True)
class E6IntegratedOrchestratorResultV1:
    result_version: str
    result_schema: str
    disposition: str
    terminal_stage: str
    reason_code: str
    request_sha256: str
    actionable_admission: E3ActionableAdmissionResultV1
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1 | None
    technical_review_payload: E5TechnicalReviewPayloadV1 | None
    durable_review_execution: E6DurableReviewExecutionResultV1 | None
    python_final_gate: E6PythonFinalStrategyGateResultV1 | None
    publication_eligibility: E6PublicationEligibilityResultV1 | None
    publication_envelope: E6PublicationEnvelopeV1 | None
    rendered_message: str | None
    owner_lifecycle_binding: E6OwnerStateLifecycleBindingResultV1 | None
    d6_outcome: str | None
    d7_route: str | None
    deepseek_provider_outcome: str | None
    claude_provider_outcome: str | None
    d8_fail_closed_cause: str | None
    deepseek_provider_attempt_count: int
    claude_provider_attempt_count: int
    retry_count: int
    telegram_send_count: int
    exchange_order_count: int
    slot_mutation_count: int
    pair_lock_mutation_count: int
    entry_active_mutation_count: int
    owner_decision_mutation_count: int
    correlation_sha256: str
    result_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(self.result_version == E6_INTEGRATED_ORCHESTRATOR_VERSION)
            _require(self.result_schema == E6_INTEGRATED_ORCHESTRATOR_SCHEMA)
            _require(self.disposition in {COMPLETE, HOLD, NO_TRADE})
            _require(self.terminal_stage in _STAGES)
            _require(type(self.reason_code) is str and bool(self.reason_code))
            _require(_valid_sha256(self.request_sha256))
            _require(type(self.actionable_admission) is E3ActionableAdmissionResultV1)
            self.actionable_admission.__post_init__()
            for count in (
                self.deepseek_provider_attempt_count,
                self.claude_provider_attempt_count,
            ):
                _require(type(count) is int and count in (0, 1))
            for count in (
                self.retry_count,
                self.telegram_send_count,
                self.exchange_order_count,
                self.slot_mutation_count,
                self.pair_lock_mutation_count,
                self.entry_active_mutation_count,
                self.owner_decision_mutation_count,
            ):
                _require(type(count) is int and count == 0)
            if self.disposition == COMPLETE:
                _require(self.terminal_stage == STAGE_10_COMPLETE)
                _require(self.reason_code == COMPLETE)
                for value in (
                    self.duplicate_protection_result,
                    self.technical_review_payload,
                    self.durable_review_execution,
                    self.python_final_gate,
                    self.publication_eligibility,
                    self.publication_envelope,
                    self.rendered_message,
                    self.owner_lifecycle_binding,
                ):
                    _require(value is not None)
                _require(self.owner_lifecycle_binding.classification != HOLD_CONFLICT)
            elif self.disposition == HOLD:
                _require(self.terminal_stage != STAGE_10_COMPLETE)
            else:
                _require(self.terminal_stage != STAGE_10_COMPLETE)
                _require(self.publication_envelope is None)
                _require(self.rendered_message is None)
                _require(self.owner_lifecycle_binding is None)
            _require(_valid_sha256(self.correlation_sha256))
            _require(self.correlation_sha256 == _hash(_correlation_preimage(self)))
            _require(_valid_sha256(self.result_sha256))
            _require(self.result_sha256 == _hash(_result_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {**_result_preimage(self), "result_sha256": self.result_sha256}


def _correlation_preimage(result: E6IntegratedOrchestratorResultV1) -> dict[str, object]:
    return {
        "request_sha256": result.request_sha256,
        "actionable_admission_sha256": result.actionable_admission.actionable_admission_sha256,
        "duplicate_protection_sha256": (
            None
            if result.duplicate_protection_result is None
            else result.duplicate_protection_result.composition_sha256
        ),
        "payload_sha256": (
            None if result.technical_review_payload is None else result.technical_review_payload.payload_sha256
        ),
        "durable_execution_sha256": (
            None if result.durable_review_execution is None else result.durable_review_execution.execution_sha256
        ),
        "final_gate_sha256": (
            None if result.python_final_gate is None else result.python_final_gate.final_gate_sha256
        ),
        "publication_eligibility_sha256": (
            None
            if result.publication_eligibility is None
            else result.publication_eligibility.publication_eligibility_sha256
        ),
        "publication_envelope_sha256": (
            None
            if result.publication_envelope is None
            else result.publication_envelope.publication_envelope_sha256
        ),
        "rendered_message_sha256": (
            None
            if result.rendered_message is None
            else hashlib.sha256(result.rendered_message.encode("utf-8")).hexdigest()
        ),
        "owner_binding_sha256": (
            None
            if result.owner_lifecycle_binding is None
            else result.owner_lifecycle_binding.binding.binding_sha256
        ),
    }


def _result_preimage(result: E6IntegratedOrchestratorResultV1) -> dict[str, object]:
    return {
        item.name: _stable(getattr(result, item.name))
        for item in fields(E6IntegratedOrchestratorResultV1)
        if item.name != "result_sha256"
    }


def _finish(
    *,
    request: E6IntegratedOrchestratorRequestV1,
    disposition: str,
    terminal_stage: str,
    reason_code: str,
    duplicate: E4DuplicateProtectionCompositionResultV1 | None = None,
    payload: E5TechnicalReviewPayloadV1 | None = None,
    durable: E6DurableReviewExecutionResultV1 | None = None,
    gate: E6PythonFinalStrategyGateResultV1 | None = None,
    eligibility: E6PublicationEligibilityResultV1 | None = None,
    envelope: E6PublicationEnvelopeV1 | None = None,
    message: str | None = None,
    binding: E6OwnerStateLifecycleBindingResultV1 | None = None,
    deepseek_attempts: int = 0,
    claude_attempts: int = 0,
) -> E6IntegratedOrchestratorResultV1:
    composition = None if durable is None else durable.final_composition
    data: dict[str, object] = {
        "result_version": E6_INTEGRATED_ORCHESTRATOR_VERSION,
        "result_schema": E6_INTEGRATED_ORCHESTRATOR_SCHEMA,
        "disposition": disposition,
        "terminal_stage": terminal_stage,
        "reason_code": reason_code,
        "request_sha256": request.request_sha256,
        "actionable_admission": request.actionable_admission,
        "duplicate_protection_result": duplicate,
        "technical_review_payload": payload,
        "durable_review_execution": durable,
        "python_final_gate": gate,
        "publication_eligibility": eligibility,
        "publication_envelope": envelope,
        "rendered_message": message,
        "owner_lifecycle_binding": binding,
        "d6_outcome": (
            None
            if composition is None or composition.deepseek_adjudication is None
            else composition.deepseek_adjudication.review_decision
        ),
        "d7_route": (
            None
            if composition is None or composition.claude_route_result is None
            else composition.claude_route_result.route
        ),
        "deepseek_provider_outcome": (
            None
            if composition is None
            else composition.deepseek_invocation_result.final_result_code
        ),
        "claude_provider_outcome": (
            None
            if composition is None or composition.claude_invocation_result is None
            else composition.claude_invocation_result.final_result_code
        ),
        "d8_fail_closed_cause": (
            None if composition is None else composition.underlying_d8_cause
        ),
        "deepseek_provider_attempt_count": deepseek_attempts,
        "claude_provider_attempt_count": claude_attempts,
        "retry_count": 0,
        "telegram_send_count": 0,
        "exchange_order_count": 0,
        "slot_mutation_count": 0,
        "pair_lock_mutation_count": 0,
        "entry_active_mutation_count": 0,
        "owner_decision_mutation_count": 0,
    }
    temporary = object.__new__(E6IntegratedOrchestratorResultV1)
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    correlation = _hash(_correlation_preimage(temporary))
    data["correlation_sha256"] = correlation
    object.__setattr__(temporary, "correlation_sha256", correlation)
    data["result_sha256"] = _hash(_result_preimage(temporary))
    return E6IntegratedOrchestratorResultV1(**data)  # type: ignore[arg-type]


def _validate_request_lineage(request: E6IntegratedOrchestratorRequestV1) -> None:
    admission = request.actionable_admission
    authority = request.candidate_authority
    geometry = admission.geometry
    trigger = admission.mode_trigger_evidence
    fingerprint = build_e4_thesis_fingerprint(
        geometry=geometry,
        structural_targets=admission.structural_targets,
        executable_price_snapshot=admission.executable_price_snapshot,
        mode_trigger_evidence=trigger,
        production_candidate_authority=authority,
    )
    _require(request.mode_profile == get_mode_profile(geometry.mode))
    execution, timeframes, oi = request.mode_execution_evidence
    _require(type(execution) is ModeScanExecutionResultV1)
    _require(type(timeframes) is tuple)
    _require(type(oi) is ModeOiExecutionEvidenceV1)
    execution.__post_init__()
    oi.__post_init__()
    _require(execution.mode == geometry.mode)
    _require(execution.mode_lineage_sha256 == geometry.mode_lineage_sha256)
    _require(execution.observed_at == trigger.evaluation_timestamp)
    _require(oi.mode == geometry.mode)
    _require(oi.mode_lineage_sha256 == geometry.mode_lineage_sha256)
    _require(active.normalize_pair(oi.canonical_symbol) == fingerprint.canonical_pair)
    for item in timeframes:
        _require(type(item) is ModeTimeframeExecutionEvidenceV1)
        item.__post_init__()
        _require(item.mode == geometry.mode)
        _require(item.mode_lineage_sha256 == geometry.mode_lineage_sha256)
        _require(active.normalize_pair(item.canonical_symbol) == fingerprint.canonical_pair)
    if request.news_evidence is None or request.news_evidence.status == RELEVANT_NEWS_PRESENT:
        _require(request.news_risk_object is not None)
        _require(request.news_risk_object.event_snapshot_id in {item.event_snapshot_id for item in request.normalized_news_events})
    else:
        _require(request.normalized_news_events == ())
        _require(request.news_risk_object is None)
    _require(request.publication_mode == geometry.mode)
    _require(active.normalize_pair(request.publication_symbol) == fingerprint.canonical_pair)
    _require(request.publication_source_payload_hash == authority.source_payload_hash)
    _require(candidate_authority_sha256_v1(authority))


def run_e6_integrated_orchestrator_v1(
    *,
    request: E6IntegratedOrchestratorRequestV1,
    ports: E6IntegratedOrchestratorPortsV1,
) -> E6IntegratedOrchestratorResultV1:
    """Run the detached state machine once without retry or transport authority."""

    _require(type(request) is E6IntegratedOrchestratorRequestV1)
    _require(type(ports) is E6IntegratedOrchestratorPortsV1)
    request.__post_init__()
    ports.__post_init__()
    try:
        _validate_request_lineage(request)
    except Exception:
        return _finish(
            request=request,
            disposition=HOLD,
            terminal_stage=STAGE_1_VALIDATE_REQUEST_AND_LINEAGE,
            reason_code="HOLD_REQUEST_OR_LINEAGE",
        )

    if not request.actionable_admission.actionable_admitted:
        return _finish(
            request=request,
            disposition=NO_TRADE,
            terminal_stage=STAGE_2_E3_ACTIONABLE_ADMISSION,
            reason_code=request.actionable_admission.reason_code,
        )

    if (
        request.news_evidence is not None
        and request.news_evidence.status == NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE
    ):
        return _finish(
            request=request,
            disposition=NO_TRADE,
            terminal_stage=STAGE_4_DURABLE_E5_EXECUTION,
            reason_code=NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE,
        )

    try:
        duplicate = compose_e4_duplicate_protection_v1(
            actionable_admission=request.actionable_admission,
            candidate_authority=request.candidate_authority,
            authorized_store_root=ports.e4_authorized_store_root,
            store_path=ports.e4_store_path,
            price_exited_zone=request.price_exited_zone,
        )
    except Exception:
        return _finish(
            request=request,
            disposition=HOLD,
            terminal_stage=STAGE_3_E4_DUPLICATE_PROTECTION,
            reason_code="HOLD_E4_DUPLICATE_PROTECTION_ERROR",
        )
    if not duplicate.publication_intent_allowed:
        return _finish(
            request=request,
            disposition=NO_TRADE,
            terminal_stage=STAGE_3_E4_DUPLICATE_PROTECTION,
            reason_code=duplicate.decision_code,
            duplicate=duplicate,
        )

    try:
        document = load_e4_thesis_history_store_v1(
            authorized_store_root=ports.e4_authorized_store_root,
            store_path=ports.e4_store_path,
        )
        _require(document is not None)
        payload = build_e5_technical_review_payload_v1(
            actionable_admission=request.actionable_admission,
            candidate_authority=request.candidate_authority,
            duplicate_protection_result=duplicate,
            thesis_history=document.history,
            mode_profile=request.mode_profile,
            mode_execution_evidence=request.mode_execution_evidence,
            normalized_news_events=request.normalized_news_events,
            news_risk_object=request.news_risk_object,
            news_evidence=request.news_evidence,
        )
    except Exception:
        return _finish(
            request=request,
            disposition=HOLD,
            terminal_stage=STAGE_4_DURABLE_E5_EXECUTION,
            reason_code="HOLD_E5_PAYLOAD_OR_HISTORY",
            duplicate=duplicate,
        )

    deepseek_attempts = 0
    claude_attempts = 0

    def deepseek_once(provider_request: object) -> object:
        nonlocal deepseek_attempts
        _require(deepseek_attempts == 0)
        deepseek_attempts += 1
        return ports.deepseek_transport(provider_request)

    def claude_once(provider_request: object) -> object:
        nonlocal claude_attempts
        _require(claude_attempts == 0)
        claude_attempts += 1
        return ports.claude_transport(provider_request)

    try:
        durable = execute_e6_durable_review_v1(
            payload=payload,
            deterministic_hard_gates_passed=request.deterministic_hard_gates_passed,
            pre_review_score=request.pre_review_score,
            mode_score_floor=request.mode_score_floor,
            usage_store=ports.usage_store,
            commit_timestamp=request.commit_timestamp,
            deepseek_measured_input_tokens=request.deepseek_measured_input_tokens,
            deepseek_requested_output_tokens=request.deepseek_requested_output_tokens,
            deepseek_transport=deepseek_once,
            claude_measured_input_tokens=request.claude_measured_input_tokens,
            claude_requested_output_tokens=request.claude_requested_output_tokens,
            claude_transport=claude_once,
        )
    except Exception:
        return _finish(
            request=request,
            disposition=HOLD,
            terminal_stage=STAGE_4_DURABLE_E5_EXECUTION,
            reason_code="HOLD_DURABLE_E5_EXECUTION",
            duplicate=duplicate,
            payload=payload,
            deepseek_attempts=deepseek_attempts,
            claude_attempts=claude_attempts,
        )
    _require(deepseek_attempts == durable.deepseek_provider_attempt_count)
    _require(claude_attempts == durable.claude_provider_attempt_count)
    if not durable.final_composition.may_continue_to_python_final_gate:
        return _finish(
            request=request,
            disposition=(
                NO_TRADE
                if durable.final_composition.underlying_d8_cause is None
                else HOLD
            ),
            terminal_stage=STAGE_4_DURABLE_E5_EXECUTION,
            reason_code=durable.final_composition.final_outcome_code,
            duplicate=duplicate,
            payload=payload,
            durable=durable,
            deepseek_attempts=deepseek_attempts,
            claude_attempts=claude_attempts,
        )

    gate = evaluate_e6_python_final_strategy_gate_v1(
        actionable_admission=request.actionable_admission,
        candidate_authority=request.candidate_authority,
        duplicate_protection_result=duplicate,
        payload=payload,
        durable_review_execution=durable,
    )
    if not gate.may_proceed_to_publication_eligibility:
        return _finish(
            request=request,
            disposition=NO_TRADE,
            terminal_stage=STAGE_5_PYTHON_FINAL_GATE,
            reason_code=gate.final_gate_decision_code,
            duplicate=duplicate,
            payload=payload,
            durable=durable,
            gate=gate,
            deepseek_attempts=deepseek_attempts,
            claude_attempts=claude_attempts,
        )

    eligibility = evaluate_e6_publication_eligibility_v1(
        final_strategy_gate_result=gate,
        actionable_admission=request.actionable_admission,
        candidate_authority=request.candidate_authority,
        duplicate_protection_result=duplicate,
    )
    if not eligibility.eligible_to_build_publication_envelope:
        return _finish(
            request=request,
            disposition=NO_TRADE,
            terminal_stage=STAGE_6_PUBLICATION_ELIGIBILITY,
            reason_code=eligibility.publication_eligibility_decision_code,
            duplicate=duplicate,
            payload=payload,
            durable=durable,
            gate=gate,
            eligibility=eligibility,
            deepseek_attempts=deepseek_attempts,
            claude_attempts=claude_attempts,
        )

    try:
        envelope = build_e6_publication_envelope_v1(
            publication_eligibility_result=eligibility,
            final_strategy_gate_result=gate,
            actionable_admission=request.actionable_admission,
            candidate_authority=request.candidate_authority,
            duplicate_protection_result=duplicate,
            payload=payload,
            durable_review_execution=durable,
        )
        _require(request.publication_signal_id == envelope.signal_id)
        _require(request.publication_source_payload_hash == envelope.source_payload_hash)
        _require(request.publication_mode == envelope.mode)
        _require(active.normalize_pair(request.publication_symbol) == envelope.canonical_pair)
    except Exception:
        return _finish(
            request=request,
            disposition=HOLD,
            terminal_stage=STAGE_7_PUBLICATION_ENVELOPE,
            reason_code="HOLD_PUBLICATION_ENVELOPE_OR_EVIDENCE_LINEAGE",
            duplicate=duplicate,
            payload=payload,
            durable=durable,
            gate=gate,
            eligibility=eligibility,
            deepseek_attempts=deepseek_attempts,
            claude_attempts=claude_attempts,
        )

    try:
        message = format_e6_signal_message_v1(envelope)
    except Exception:
        return _finish(
            request=request,
            disposition=HOLD,
            terminal_stage=STAGE_8_HUMAN_PRESENTATION,
            reason_code="HOLD_HUMAN_PRESENTATION",
            duplicate=duplicate,
            payload=payload,
            durable=durable,
            gate=gate,
            eligibility=eligibility,
            envelope=envelope,
            deepseek_attempts=deepseek_attempts,
            claude_attempts=claude_attempts,
        )

    publication_evidence = {
        "delivery_state": "DELIVERY_SUCCEEDED",
        "signal_id": request.publication_signal_id,
        "delivery_id": request.publication_delivery_id,
        "mode": request.publication_mode,
        "published_at": request.publication_published_at,
        "source_payload_hash": request.publication_source_payload_hash,
        "publication_payload_hash": request.publication_payload_hash,
        "content_hash": request.publication_content_hash,
        "publication_payload": {
            "signal_id": request.publication_signal_id,
            "mode": request.publication_mode,
            "symbol": request.publication_symbol,
        },
    }
    try:
        ledger = active.load_ledger(ports.active_ledger_path)
        binding = bind_e6_publication_to_owner_state_v1(
            envelope=envelope,
            active_ledger_path=ports.active_ledger_path,
            expected_active_ledger_revision=ledger["ledger_revision"],
            publication_evidence=publication_evidence,
            timestamp=request.commit_timestamp,
        )
    except Exception:
        return _finish(
            request=request,
            disposition=HOLD,
            terminal_stage=STAGE_9_OWNER_LIFECYCLE_BINDING,
            reason_code="HOLD_OWNER_LIFECYCLE_BINDING",
            duplicate=duplicate,
            payload=payload,
            durable=durable,
            gate=gate,
            eligibility=eligibility,
            envelope=envelope,
            message=message,
            deepseek_attempts=deepseek_attempts,
            claude_attempts=claude_attempts,
        )
    if binding.classification == HOLD_CONFLICT:
        return _finish(
            request=request,
            disposition=HOLD,
            terminal_stage=STAGE_9_OWNER_LIFECYCLE_BINDING,
            reason_code=binding.registration_reason or HOLD_CONFLICT,
            duplicate=duplicate,
            payload=payload,
            durable=durable,
            gate=gate,
            eligibility=eligibility,
            envelope=envelope,
            message=message,
            binding=binding,
            deepseek_attempts=deepseek_attempts,
            claude_attempts=claude_attempts,
        )
    return _finish(
        request=request,
        disposition=COMPLETE,
        terminal_stage=STAGE_10_COMPLETE,
        reason_code=COMPLETE,
        duplicate=duplicate,
        payload=payload,
        durable=durable,
        gate=gate,
        eligibility=eligibility,
        envelope=envelope,
        message=message,
        binding=binding,
        deepseek_attempts=deepseek_attempts,
        claude_attempts=claude_attempts,
    )


__all__ = (
    "E6IntegratedOrchestratorRequestV1",
    "E6IntegratedOrchestratorPortsV1",
    "E6IntegratedOrchestratorResultV1",
    "run_e6_integrated_orchestrator_v1",
)
