"""Pure deterministic Python final-strategy authority for E6."""

from __future__ import annotations

from dataclasses import dataclass, fields
from hashlib import sha256
import json
import re
from typing import Final, Mapping

from engine.canonical_pair_v1 import normalize_pair
from engine.e3_actionable_admission_v1 import E3ActionableAdmissionResultV1
from engine.e4_duplicate_protection_composition_v1 import (
    E4DuplicateProtectionCompositionResultV1,
)
from engine.e4_thesis_fingerprint_v1 import build_e4_thesis_fingerprint
from engine.e5_bounded_final_review_composition_v1 import (
    CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE,
    CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE,
    E5_BOUNDED_FINAL_REVIEW_OUTCOME_CODES,
)
from engine.e5_claude_review_router_v1 import L0, L1
from engine.e5_deepseek_technical_review_v1 import CAUTION, CLEAR
from engine.e5_provider_invocation_boundary_v1 import (
    ACTIVE_PROVIDER_BINDING_SHA256,
)
from engine.e5_technical_review_payload_v1 import (
    E5TechnicalReviewPayloadV1,
    reconstruct_e5_technical_review_payload_v1,
)
from engine.e6_durable_review_execution_v1 import (
    DURABLE_RESERVATION_COMMITTED,
    NO_DURABLE_RESERVATION_REQUIRED,
    E6DurableReviewExecutionResultV1,
)
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)


FINAL_GATE_VERSION: Final = "e6-python-final-strategy-gate-v1"

PASS_CLEAR_L0_FINAL_STRATEGY: Final = "PASS_CLEAR_L0_FINAL_STRATEGY"
PASS_CAUTION_L1_FINAL_STRATEGY: Final = (
    "PASS_CAUTION_L1_FINAL_STRATEGY"
)
BLOCK_E5_FINAL_REVIEW_NOT_CONTINUABLE: Final = (
    "BLOCK_E5_FINAL_REVIEW_NOT_CONTINUABLE"
)
BLOCK_E3_ACTIONABLE_ADMISSION: Final = "BLOCK_E3_ACTIONABLE_ADMISSION"
BLOCK_E4_DUPLICATE_PROTECTION: Final = "BLOCK_E4_DUPLICATE_PROTECTION"
BLOCK_CANDIDATE_AUTHORITY: Final = "BLOCK_CANDIDATE_AUTHORITY"
BLOCK_CROSS_LINEAGE: Final = "BLOCK_CROSS_LINEAGE"
BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR: Final = (
    "BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR"
)

FINAL_GATE_DECISION_CODES: Final = (
    PASS_CLEAR_L0_FINAL_STRATEGY,
    PASS_CAUTION_L1_FINAL_STRATEGY,
    BLOCK_E5_FINAL_REVIEW_NOT_CONTINUABLE,
    BLOCK_E3_ACTIONABLE_ADMISSION,
    BLOCK_E4_DUPLICATE_PROTECTION,
    BLOCK_CANDIDATE_AUTHORITY,
    BLOCK_CROSS_LINEAGE,
    BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR,
)
FINAL_GATE_FIELD_COUNT: Final = 35

_PASS_CODES: Final = frozenset(
    (PASS_CLEAR_L0_FINAL_STRATEGY, PASS_CAUTION_L1_FINAL_STRATEGY)
)
_MODES: Final = frozenset(("SWING", "INTRADAY", "SCALP"))
_SIDES: Final = frozenset(("LONG", "SHORT"))
_ERROR: Final = "invalid E6 Python final strategy gate"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")


def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except Exception:
        _fail()


def _hash_value(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _valid_sha256(value: object) -> bool:
    return type(value) is str and _SHA256_PATTERN.fullmatch(value) is not None


def candidate_authority_sha256_v1(
    candidate_authority: ProductionCandidateAuthorityV1,
) -> str:
    try:
        _require(type(candidate_authority) is ProductionCandidateAuthorityV1)
        candidate_authority.__post_init__()
        reconstructed = ProductionCandidateAuthorityV1(
            **candidate_authority.to_dict()
        )
        _require(reconstructed.to_dict() == candidate_authority.to_dict())
        return _hash_value(candidate_authority.to_dict())
    except Exception:
        _fail()


def _final_gate_preimage(
    result: "E6PythonFinalStrategyGateResultV1",
) -> dict[str, object]:
    return {
        field.name: getattr(result, field.name)
        for field in fields(E6PythonFinalStrategyGateResultV1)
        if field.name != "final_gate_sha256"
    }


@dataclass(frozen=True, slots=True)
class E6PythonFinalStrategyGateResultV1:
    final_gate_version: str
    provider_binding_sha256: str
    actionable_admission_sha256: str
    candidate_authority_sha256: str
    duplicate_protection_sha256: str
    thesis_fingerprint_sha256: str
    payload_sha256: str
    durable_execution_sha256: str
    final_composition_sha256: str
    canonical_pair: str
    mode: str
    side: str
    structure_timeframe: str
    trigger_timeframe: str
    structure_generation_id: str
    trigger_generation_id: str
    deterministic_hard_gates_passed: bool | None
    actionable_admitted: bool
    duplicate_protection_allows_publication_intent: bool
    deepseek_review_decision: str | None
    claude_route: str | None
    final_score: int | None
    mode_score_floor: int | None
    source_e5_final_outcome_code: str
    final_gate_decision_code: str
    may_proceed_to_publication_eligibility: bool
    publication_side_effect_allowed: bool
    telegram_send_allowed: bool
    ledger_mutation_allowed: bool
    slot_mutation_allowed: bool
    pair_lock_mutation_allowed: bool
    exchange_order_allowed: bool
    entry_active_mutation_allowed: bool
    retry_count: int
    final_gate_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(self.final_gate_version == FINAL_GATE_VERSION)
            for value in (
                self.provider_binding_sha256,
                self.actionable_admission_sha256,
                self.candidate_authority_sha256,
                self.duplicate_protection_sha256,
                self.thesis_fingerprint_sha256,
                self.payload_sha256,
                self.durable_execution_sha256,
                self.final_composition_sha256,
                self.final_gate_sha256,
            ):
                _require(_valid_sha256(value))
            _require(
                self.provider_binding_sha256
                == ACTIVE_PROVIDER_BINDING_SHA256
            )
            _require(
                type(self.canonical_pair) is str
                and normalize_pair(self.canonical_pair) == self.canonical_pair
            )
            _require(type(self.mode) is str and self.mode in _MODES)
            _require(type(self.side) is str and self.side in _SIDES)
            for value in (
                self.structure_timeframe,
                self.trigger_timeframe,
                self.structure_generation_id,
                self.trigger_generation_id,
            ):
                _require(type(value) is str and bool(value))
            for value in (
                self.actionable_admitted,
                self.duplicate_protection_allows_publication_intent,
                self.may_proceed_to_publication_eligibility,
            ):
                _require(type(value) is bool)
            adjudication_values = (
                self.deterministic_hard_gates_passed,
                self.deepseek_review_decision,
                self.final_score,
                self.mode_score_floor,
            )
            _require(
                all(value is None for value in adjudication_values)
                or all(value is not None for value in adjudication_values)
            )
            if self.deterministic_hard_gates_passed is not None:
                _require(type(self.deterministic_hard_gates_passed) is bool)
                _require(type(self.deepseek_review_decision) is str)
                _require(type(self.final_score) is int)
                _require(type(self.mode_score_floor) is int)
            _require(self.claude_route is None or type(self.claude_route) is str)
            _require(
                self.source_e5_final_outcome_code
                in E5_BOUNDED_FINAL_REVIEW_OUTCOME_CODES
            )
            _require(self.final_gate_decision_code in FINAL_GATE_DECISION_CODES)
            _require(
                self.may_proceed_to_publication_eligibility
                == (self.final_gate_decision_code in _PASS_CODES)
            )
            for authority in (
                self.publication_side_effect_allowed,
                self.telegram_send_allowed,
                self.ledger_mutation_allowed,
                self.slot_mutation_allowed,
                self.pair_lock_mutation_allowed,
                self.exchange_order_allowed,
                self.entry_active_mutation_allowed,
            ):
                _require(type(authority) is bool and authority is False)
            _require(type(self.retry_count) is int and self.retry_count == 0)
            if self.final_gate_decision_code == PASS_CLEAR_L0_FINAL_STRATEGY:
                _require(self.actionable_admitted is True)
                _require(
                    self.duplicate_protection_allows_publication_intent is True
                )
                _require(self.deterministic_hard_gates_passed is True)
                _require(self.deepseek_review_decision == CLEAR)
                _require(self.claude_route == L0)
                _require(
                    self.source_e5_final_outcome_code
                    == CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE
                )
                _require(self.final_score > self.mode_score_floor)
            elif (
                self.final_gate_decision_code
                == PASS_CAUTION_L1_FINAL_STRATEGY
            ):
                _require(self.actionable_admitted is True)
                _require(
                    self.duplicate_protection_allows_publication_intent is True
                )
                _require(self.deterministic_hard_gates_passed is True)
                _require(self.deepseek_review_decision == CAUTION)
                _require(self.claude_route == L1)
                _require(
                    self.source_e5_final_outcome_code
                    == CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE
                )
                _require(self.final_score > self.mode_score_floor)
            _require(
                self.final_gate_sha256
                == _hash_value(_final_gate_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_final_gate_preimage(self),
            "final_gate_sha256": self.final_gate_sha256,
        }

    def canonical_final_gate_json(self) -> str:
        return _canonical_json(_final_gate_preimage(self))


def reconstruct_e6_python_final_strategy_gate_result_v1(
    mapping: Mapping[str, object],
) -> E6PythonFinalStrategyGateResultV1:
    try:
        expected = tuple(
            field.name for field in fields(E6PythonFinalStrategyGateResultV1)
        )
        _require(type(mapping) is dict)
        _require(tuple(mapping) == expected)
        return E6PythonFinalStrategyGateResultV1(
            **{name: mapping[name] for name in expected}
        )
    except Exception:
        _fail()


def _strict_inputs(
    *,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
    payload: E5TechnicalReviewPayloadV1,
    durable_review_execution: E6DurableReviewExecutionResultV1,
) -> tuple[dict[str, object], object, str]:
    _require(type(actionable_admission) is E3ActionableAdmissionResultV1)
    actionable_admission.__post_init__()
    _require(type(candidate_authority) is ProductionCandidateAuthorityV1)
    candidate_authority.__post_init__()
    _require(
        type(duplicate_protection_result)
        is E4DuplicateProtectionCompositionResultV1
    )
    duplicate_protection_result.__post_init__()
    _require(type(payload) is E5TechnicalReviewPayloadV1)
    payload.__post_init__()
    reconstructed_payload = reconstruct_e5_technical_review_payload_v1(
        payload.to_mapping()
    )
    _require(reconstructed_payload.to_mapping() == payload.to_mapping())
    _require(
        type(durable_review_execution)
        is E6DurableReviewExecutionResultV1
    )
    durable_review_execution.__post_init__()
    durable_review_execution.final_composition.__post_init__()
    _require(payload.provider_binding_sha256 == ACTIVE_PROVIDER_BINDING_SHA256)
    _require(
        durable_review_execution.provider_binding_sha256
        == ACTIVE_PROVIDER_BINDING_SHA256
    )
    _require(
        durable_review_execution.final_composition.provider_binding_sha256
        == ACTIVE_PROVIDER_BINDING_SHA256
    )
    _require(durable_review_execution.retry_count == 0)
    _require(durable_review_execution.final_composition.retry_count == 0)
    for authority in (
        durable_review_execution.publication_allowed,
        durable_review_execution.telegram_send_allowed,
        durable_review_execution.ledger_mutation_allowed,
        durable_review_execution.slot_mutation_allowed,
        durable_review_execution.pair_lock_mutation_allowed,
        durable_review_execution.final_composition.publication_allowed,
        durable_review_execution.final_composition.telegram_send_allowed,
        durable_review_execution.final_composition.slot_mutation_allowed,
        durable_review_execution.final_composition.pair_lock_mutation_allowed,
    ):
        _require(authority is False)
    rebuilt = build_e4_thesis_fingerprint(
        geometry=actionable_admission.geometry,
        structural_targets=actionable_admission.structural_targets,
        executable_price_snapshot=(
            actionable_admission.executable_price_snapshot
        ),
        mode_trigger_evidence=actionable_admission.mode_trigger_evidence,
        production_candidate_authority=candidate_authority,
    )
    return payload.to_mapping(), rebuilt, candidate_authority_sha256_v1(
        candidate_authority
    )


def _payload_lineage_matches(
    *,
    payload_mapping: dict[str, object],
    actionable_admission: E3ActionableAdmissionResultV1,
    rebuilt_fingerprint: object,
) -> bool:
    try:
        geometry = actionable_admission.geometry
        targets = actionable_admission.structural_targets
        admission = actionable_admission.price_zone_admission
        trigger = actionable_admission.mode_trigger_evidence
        lifecycle = actionable_admission.setup_lifecycle
        thesis = payload_mapping["thesis_fingerprint"]
        return all(
            (
                payload_mapping["mode"] == geometry.mode,
                geometry.structure_timeframe
                in payload_mapping["relevant_timeframes"],
                trigger.trigger_timeframe
                in payload_mapping["relevant_timeframes"],
                payload_mapping["trigger_type"] == trigger.trigger_rule,
                payload_mapping["executable_price"]["admission_sha256"]
                == admission.admission_sha256,
                payload_mapping["golden_zone"]["geometry_sha256"]
                == geometry.geometry_sha256,
                payload_mapping["target_geometry"]["targets_sha256"]
                == targets.targets_sha256,
                payload_mapping["trigger_age"]["trigger_evidence_sha256"]
                == trigger.trigger_evidence_sha256,
                payload_mapping["lifecycle_state"]["lifecycle_sha256"]
                == lifecycle.lifecycle_sha256,
                thesis["identity_sha256"]
                == rebuilt_fingerprint.identity_sha256,
                thesis["identity"]
                == rebuilt_fingerprint.to_identity_mapping(),
            )
        )
    except Exception:
        return False


def _build_result(
    *,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority_sha256: str,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
    payload: E5TechnicalReviewPayloadV1,
    durable_review_execution: E6DurableReviewExecutionResultV1,
    rebuilt_fingerprint: object,
    decision_code: str,
) -> E6PythonFinalStrategyGateResultV1:
    composition = durable_review_execution.final_composition
    adjudication = composition.deepseek_adjudication
    route = composition.claude_route_result
    data: dict[str, object] = {
        "final_gate_version": FINAL_GATE_VERSION,
        "provider_binding_sha256": ACTIVE_PROVIDER_BINDING_SHA256,
        "actionable_admission_sha256": (
            actionable_admission.actionable_admission_sha256
        ),
        "candidate_authority_sha256": candidate_authority_sha256,
        "duplicate_protection_sha256": (
            duplicate_protection_result.composition_sha256
        ),
        "thesis_fingerprint_sha256": rebuilt_fingerprint.identity_sha256,
        "payload_sha256": payload.payload_sha256,
        "durable_execution_sha256": (
            durable_review_execution.execution_sha256
        ),
        "final_composition_sha256": composition.composition_sha256,
        "canonical_pair": rebuilt_fingerprint.canonical_pair,
        "mode": rebuilt_fingerprint.mode,
        "side": rebuilt_fingerprint.side,
        "structure_timeframe": rebuilt_fingerprint.structure_timeframe,
        "trigger_timeframe": rebuilt_fingerprint.trigger_timeframe,
        "structure_generation_id": (
            rebuilt_fingerprint.structure_generation_id
        ),
        "trigger_generation_id": rebuilt_fingerprint.trigger_generation_id,
        "deterministic_hard_gates_passed": (
            None
            if adjudication is None
            else adjudication.deterministic_hard_gates_passed
        ),
        "actionable_admitted": actionable_admission.actionable_admitted,
        "duplicate_protection_allows_publication_intent": (
            duplicate_protection_result.publication_intent_allowed
        ),
        "deepseek_review_decision": (
            None if adjudication is None else adjudication.review_decision
        ),
        "claude_route": None if route is None else route.route,
        "final_score": None if adjudication is None else adjudication.final_score,
        "mode_score_floor": (
            None if adjudication is None else adjudication.mode_score_floor
        ),
        "source_e5_final_outcome_code": composition.final_outcome_code,
        "final_gate_decision_code": decision_code,
        "may_proceed_to_publication_eligibility": decision_code in _PASS_CODES,
        "publication_side_effect_allowed": False,
        "telegram_send_allowed": False,
        "ledger_mutation_allowed": False,
        "slot_mutation_allowed": False,
        "pair_lock_mutation_allowed": False,
        "exchange_order_allowed": False,
        "entry_active_mutation_allowed": False,
        "retry_count": 0,
    }
    temporary = object.__new__(E6PythonFinalStrategyGateResultV1)
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E6PythonFinalStrategyGateResultV1(
        **data,
        final_gate_sha256=_hash_value(_final_gate_preimage(temporary)),
    )


def evaluate_e6_python_final_strategy_gate_v1(
    *,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
    payload: E5TechnicalReviewPayloadV1,
    durable_review_execution: E6DurableReviewExecutionResultV1,
) -> E6PythonFinalStrategyGateResultV1:
    try:
        payload_mapping, rebuilt, authority_sha256 = _strict_inputs(
            actionable_admission=actionable_admission,
            candidate_authority=candidate_authority,
            duplicate_protection_result=duplicate_protection_result,
            payload=payload,
            durable_review_execution=durable_review_execution,
        )
        composition = durable_review_execution.final_composition
        stored_fingerprint = duplicate_protection_result.fingerprint
        candidate_mismatch = (
            stored_fingerprint is not None
            and stored_fingerprint.to_mapping() != rebuilt.to_mapping()
        )
        if candidate_mismatch:
            decision = BLOCK_CANDIDATE_AUTHORITY
        else:
            base_lineage = all(
                (
                    duplicate_protection_result.actionable_admission_sha256
                    == actionable_admission.actionable_admission_sha256,
                    durable_review_execution.payload_sha256
                    == payload.payload_sha256,
                    composition.payload_sha256 == payload.payload_sha256,
                    composition.composition_sha256
                    == durable_review_execution.final_composition.composition_sha256,
                    rebuilt.mode == actionable_admission.geometry.mode,
                    rebuilt.side == actionable_admission.geometry.side,
                    rebuilt.structure_timeframe
                    == actionable_admission.geometry.structure_timeframe,
                    rebuilt.trigger_timeframe
                    == actionable_admission.mode_trigger_evidence.trigger_timeframe,
                    rebuilt.structure_generation_id
                    == actionable_admission.geometry.structure_generation_id,
                    rebuilt.trigger_generation_id
                    == actionable_admission.mode_trigger_evidence.trigger_generation_id,
                )
            )
            detailed_payload_match = _payload_lineage_matches(
                payload_mapping=payload_mapping,
                actionable_admission=actionable_admission,
                rebuilt_fingerprint=rebuilt,
            )
            cross_lineage = not base_lineage or (
                actionable_admission.actionable_admitted
                and not detailed_payload_match
            )
            if cross_lineage:
                decision = BLOCK_CROSS_LINEAGE
            elif not actionable_admission.actionable_admitted:
                decision = BLOCK_E3_ACTIONABLE_ADMISSION
            elif (
                not duplicate_protection_result.actionable_admitted
                or not duplicate_protection_result.publication_intent_allowed
                or duplicate_protection_result.publication_guard_result is None
                or duplicate_protection_result.publication_guard_result.publication_success_recorded
            ):
                decision = BLOCK_E4_DUPLICATE_PROTECTION
            else:
                adjudication = composition.deepseek_adjudication
                route = composition.claude_route_result
                clear_exact = all(
                    (
                        composition.final_outcome_code
                        == CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE,
                        composition.may_continue_to_python_final_gate is True,
                        adjudication is not None,
                        route is not None,
                        adjudication is not None
                        and adjudication.review_decision == CLEAR,
                        route is not None and route.route == L0,
                        composition.claude_provider_attempt_count == 0,
                        durable_review_execution.persistence_outcome
                        == NO_DURABLE_RESERVATION_REQUIRED,
                        durable_review_execution.committed_usage_after is None,
                    )
                )
                caution_exact = all(
                    (
                        composition.final_outcome_code
                        == CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE,
                        composition.may_continue_to_python_final_gate is True,
                        adjudication is not None,
                        route is not None,
                        adjudication is not None
                        and adjudication.review_decision == CAUTION,
                        route is not None and route.route == L1,
                        composition.accepted_claude_review is not None,
                        composition.claude_provider_attempt_count == 1,
                        durable_review_execution.persistence_outcome
                        == DURABLE_RESERVATION_COMMITTED,
                        durable_review_execution.committed_usage_after
                        == durable_review_execution.proposed_usage_after,
                    )
                )
                if not (clear_exact or caution_exact):
                    decision = BLOCK_E5_FINAL_REVIEW_NOT_CONTINUABLE
                elif (
                    adjudication.deterministic_hard_gates_passed is not True
                    or type(adjudication.final_score) is not int
                    or type(adjudication.mode_score_floor) is not int
                    or adjudication.final_score <= adjudication.mode_score_floor
                ):
                    decision = BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR
                elif clear_exact:
                    decision = PASS_CLEAR_L0_FINAL_STRATEGY
                else:
                    decision = PASS_CAUTION_L1_FINAL_STRATEGY
        return _build_result(
            actionable_admission=actionable_admission,
            candidate_authority_sha256=authority_sha256,
            duplicate_protection_result=duplicate_protection_result,
            payload=payload,
            durable_review_execution=durable_review_execution,
            rebuilt_fingerprint=rebuilt,
            decision_code=decision,
        )
    except Exception:
        _fail()


__all__ = (
    "FINAL_GATE_VERSION",
    "FINAL_GATE_FIELD_COUNT",
    "PASS_CLEAR_L0_FINAL_STRATEGY",
    "PASS_CAUTION_L1_FINAL_STRATEGY",
    "BLOCK_E5_FINAL_REVIEW_NOT_CONTINUABLE",
    "BLOCK_E3_ACTIONABLE_ADMISSION",
    "BLOCK_E4_DUPLICATE_PROTECTION",
    "BLOCK_CANDIDATE_AUTHORITY",
    "BLOCK_CROSS_LINEAGE",
    "BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR",
    "FINAL_GATE_DECISION_CODES",
    "E6PythonFinalStrategyGateResultV1",
    "candidate_authority_sha256_v1",
    "reconstruct_e6_python_final_strategy_gate_result_v1",
    "evaluate_e6_python_final_strategy_gate_v1",
)
