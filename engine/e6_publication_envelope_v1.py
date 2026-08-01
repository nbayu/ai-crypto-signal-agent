"""Immutable, side-effect-free E6 publication proposal envelope."""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Final

from engine.e3_actionable_admission_v1 import E3ActionableAdmissionResultV1
from engine.e4_duplicate_protection_composition_v1 import (
    E4DuplicateProtectionCompositionResultV1,
)
from engine.e4_thesis_fingerprint_v1 import build_e4_thesis_fingerprint
from engine.e5_bounded_final_review_composition_v1 import (
    E5_BOUNDED_FINAL_REVIEW_OUTCOME_CODES,
)
from engine.e5_claude_review_router_v1 import (
    CLAUDE_ROUTES,
    E5_CLAUDE_ROUTER_DECISION_CODES,
)
from engine.e5_deepseek_technical_review_v1 import (
    DEEPSEEK_ADJUDICATION_OUTCOME_CODES,
    DEEPSEEK_REASON_CODES,
    DEEPSEEK_REVIEW_DECISIONS,
)
from engine.e5_provider_invocation_boundary_v1 import (
    E5_D8_FAILURE_CODES,
    E5_PROVIDER_INVOCATION_SUCCESS_CODES,
)
from engine.e5_technical_review_payload_v1 import E5TechnicalReviewPayloadV1
from engine.e6_durable_review_execution_v1 import (
    E6DurableReviewExecutionResultV1,
)
from engine.e6_publication_eligibility_v1 import (
    ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE,
    PUBLICATION_ELIGIBILITY_DECISION_CODES,
    E6PublicationEligibilityResultV1,
)
from engine.e6_python_final_strategy_gate_v1 import (
    FINAL_GATE_DECISION_CODES,
    PASS_CAUTION_L1_FINAL_STRATEGY,
    PASS_CLEAR_L0_FINAL_STRATEGY,
    E6PythonFinalStrategyGateResultV1,
    candidate_authority_sha256_v1,
)
from engine.mode_profile_v1 import get_mode_profile
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)
from engine.production_signal_contract_v1 import (
    OUTCOME_PUBLISHED_SIGNAL,
    PRODUCTION_SIGNAL_INPUT_SCHEMA,
    build_signal_id,
)


E6_PUBLICATION_ENVELOPE_VERSION: Final = "e6-publication-envelope-v1"
E6_PUBLICATION_ENVELOPE_SCHEMA: Final = "E6PublicationEnvelopeV1"
OWNER_ACTION_AWAITING_MANUAL_DECISION: Final = (
    "AWAITING_MANUAL_OWNER_DECISION"
)
MANUAL_OWNER_AUTHORITY_STATEMENT: Final = (
    "Manual owner confirmation is required; no entry, publication effect, "
    "slot, pair lock, ledger mutation, or exchange order has occurred."
)
NO_CLAUDE_REVIEW_REQUIRED: Final = "NO_CLAUDE_REVIEW_REQUIRED"

_ERROR: Final = "invalid E6 publication envelope"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_SIGNAL_ID_PATTERN: Final = re.compile(r"PSG-[0-9a-f]{64}")
_MODES: Final = frozenset(("SWING", "INTRADAY", "SCALP"))
_SIDES: Final = frozenset(("LONG", "SHORT"))
_FINAL_PASS_CODES: Final = frozenset(
    (PASS_CLEAR_L0_FINAL_STRATEGY, PASS_CAUTION_L1_FINAL_STRATEGY)
)
_D8_OUTCOMES: Final = frozenset(
    (*E5_D8_FAILURE_CODES, *E5_PROVIDER_INVOCATION_SUCCESS_CODES)
)


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


def _nonblank(value: object, *, maximum: int = 512) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= maximum
        and not any(ord(character) < 32 for character in value)
    )


def _decimal_price(tick: int, tick_size: str) -> str:
    try:
        value = Decimal(tick) * Decimal(tick_size)
        _require(value.is_finite() and value > 0)
        normalized = format(value, "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        return normalized
    except (InvalidOperation, ValueError, TypeError):
        _fail()


def _production_price(price: str) -> int | float:
    try:
        value = Decimal(price)
        _require(value.is_finite())
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        _fail()


def _envelope_preimage(
    envelope: "E6PublicationEnvelopeV1",
) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in fields(E6PublicationEnvelopeV1):
        if field.name == "publication_envelope_sha256":
            continue
        value = getattr(envelope, field.name)
        result[field.name] = list(value) if type(value) is tuple else value
    return result


@dataclass(frozen=True, slots=True)
class E6PublicationEnvelopeV1:
    publication_envelope_version: str
    publication_envelope_schema: str
    signal_id: str
    publication_identity_sha256: str
    signal_geometry_sha256: str
    final_gate_sha256: str
    publication_eligibility_sha256: str
    actionable_admission_sha256: str
    duplicate_protection_sha256: str
    payload_sha256: str
    durable_execution_sha256: str
    thesis_fingerprint_sha256: str
    source_commit: str
    source_evaluation_id: str
    source_payload_hash: str
    canonical_venue: str
    canonical_pair: str
    mode: str
    side: str
    strategy_version: str
    mode_profile_version: str
    context_timeframes: tuple[str, ...]
    optional_context_timeframes: tuple[str, ...]
    bias_timeframe: str
    structure_timeframe: str
    trigger_timeframe: str
    structure_generation_id: str
    trigger_generation_id: str
    trigger_type: str
    trigger_candle_close_at: str
    tick_size: str
    golden_zone_low: str
    golden_zone_high: str
    admission_price_source: str
    admission_price: str
    admission_exchange_timestamp: str
    entry_zone_interpretation: str
    stop_loss: str
    tp1_destination_kind: str
    tp1_destination_id: str
    tp1: str
    tp2_destination_kind: str
    tp2_destination_id: str
    tp2: str
    pre_review_score: int
    final_score: int
    mode_score_floor: int
    risk_reason_codes: tuple[str, ...]
    deepseek_d6_outcome: str
    deepseek_d6_summary: str
    deepseek_d6_adjudication_outcome: str
    claude_d7_route: str
    claude_d7_outcome: str
    claude_d7_summary: str
    d8_deepseek_provider_outcome: str
    d8_claude_provider_outcome: str
    d8_underlying_fail_closed_cause: str | None
    bounded_final_review_outcome: str
    python_final_gate_decision: str
    publication_eligibility_decision: str
    owner_action_state: str
    manual_owner_authority_statement: str
    valid_until: str
    evaluation_timestamp: str
    quote_age_seconds: int
    maximum_quote_age_seconds: int
    executable_price_fresh: bool
    trigger_age_seconds: int
    maximum_trigger_age_seconds: int
    trigger_fresh: bool
    lifecycle_state: str
    publication_side_effect_allowed: bool
    telegram_send_allowed: bool
    ledger_mutation_allowed: bool
    entry_active_mutation_allowed: bool
    slot_mutation_allowed: bool
    pair_lock_mutation_allowed: bool
    exchange_order_allowed: bool
    publication_envelope_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                self.publication_envelope_version
                == E6_PUBLICATION_ENVELOPE_VERSION
            )
            _require(
                self.publication_envelope_schema
                == E6_PUBLICATION_ENVELOPE_SCHEMA
            )
            _require(_SIGNAL_ID_PATTERN.fullmatch(self.signal_id) is not None)
            for value in (
                self.publication_identity_sha256,
                self.signal_geometry_sha256,
                self.final_gate_sha256,
                self.publication_eligibility_sha256,
                self.actionable_admission_sha256,
                self.duplicate_protection_sha256,
                self.payload_sha256,
                self.durable_execution_sha256,
                self.thesis_fingerprint_sha256,
                self.source_payload_hash,
                self.publication_envelope_sha256,
            ):
                _require(_valid_sha256(value))
            _require(
                type(self.source_commit) is str
                and re.fullmatch(r"[0-9a-f]{40}", self.source_commit) is not None
            )
            for value in (
                self.source_evaluation_id,
                self.canonical_venue,
                self.canonical_pair,
                self.strategy_version,
                self.mode_profile_version,
                self.bias_timeframe,
                self.structure_timeframe,
                self.trigger_timeframe,
                self.structure_generation_id,
                self.trigger_generation_id,
                self.trigger_type,
                self.trigger_candle_close_at,
                self.tick_size,
                self.golden_zone_low,
                self.golden_zone_high,
                self.admission_price_source,
                self.admission_price,
                self.admission_exchange_timestamp,
                self.entry_zone_interpretation,
                self.stop_loss,
                self.tp1_destination_kind,
                self.tp1_destination_id,
                self.tp1,
                self.tp2_destination_kind,
                self.tp2_destination_id,
                self.tp2,
                self.deepseek_d6_summary,
                self.claude_d7_summary,
                self.owner_action_state,
                self.manual_owner_authority_statement,
                self.valid_until,
                self.evaluation_timestamp,
                self.lifecycle_state,
            ):
                _require(_nonblank(value))
            _require(self.mode in _MODES and self.side in _SIDES)
            for timeframes in (
                self.context_timeframes,
                self.optional_context_timeframes,
            ):
                _require(type(timeframes) is tuple)
                _require(len(timeframes) == len(set(timeframes)))
                _require(all(_nonblank(value, maximum=16) for value in timeframes))
            prices = tuple(
                Decimal(value)
                for value in (
                    self.golden_zone_low,
                    self.golden_zone_high,
                    self.admission_price,
                    self.stop_loss,
                    self.tp1,
                    self.tp2,
                )
            )
            _require(all(value.is_finite() and value > 0 for value in prices))
            _require(prices[0] <= prices[2] <= prices[1])
            _require(prices[4] != prices[5])
            for value in (
                self.pre_review_score,
                self.final_score,
                self.mode_score_floor,
                self.quote_age_seconds,
                self.maximum_quote_age_seconds,
                self.trigger_age_seconds,
                self.maximum_trigger_age_seconds,
            ):
                _require(type(value) is int and value >= 0)
            _require(self.final_score > self.mode_score_floor)
            _require(type(self.risk_reason_codes) is tuple)
            _require(bool(self.risk_reason_codes))
            _require(len(self.risk_reason_codes) == len(set(self.risk_reason_codes)))
            _require(
                all(code in DEEPSEEK_REASON_CODES for code in self.risk_reason_codes)
            )
            _require(self.deepseek_d6_outcome in DEEPSEEK_REVIEW_DECISIONS)
            _require(
                self.deepseek_d6_adjudication_outcome
                in DEEPSEEK_ADJUDICATION_OUTCOME_CODES
            )
            _require(self.claude_d7_route in CLAUDE_ROUTES)
            _require(self.claude_d7_outcome in E5_CLAUDE_ROUTER_DECISION_CODES)
            _require(self.d8_deepseek_provider_outcome in _D8_OUTCOMES)
            _require(
                self.d8_claude_provider_outcome
                in _D8_OUTCOMES
            )
            _require(
                self.d8_underlying_fail_closed_cause is None
                or self.d8_underlying_fail_closed_cause in E5_D8_FAILURE_CODES
            )
            _require(
                self.bounded_final_review_outcome
                in E5_BOUNDED_FINAL_REVIEW_OUTCOME_CODES
            )
            _require(self.python_final_gate_decision in FINAL_GATE_DECISION_CODES)
            _require(self.python_final_gate_decision in _FINAL_PASS_CODES)
            _require(
                self.publication_eligibility_decision
                in PUBLICATION_ELIGIBILITY_DECISION_CODES
            )
            _require(
                self.publication_eligibility_decision
                == ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE
            )
            _require(
                self.owner_action_state
                == OWNER_ACTION_AWAITING_MANUAL_DECISION
            )
            _require(
                self.manual_owner_authority_statement
                == MANUAL_OWNER_AUTHORITY_STATEMENT
            )
            _require(self.executable_price_fresh is True)
            _require(self.trigger_fresh is True)
            _require(self.quote_age_seconds <= self.maximum_quote_age_seconds)
            _require(self.trigger_age_seconds <= self.maximum_trigger_age_seconds)
            for authority in (
                self.publication_side_effect_allowed,
                self.telegram_send_allowed,
                self.ledger_mutation_allowed,
                self.entry_active_mutation_allowed,
                self.slot_mutation_allowed,
                self.pair_lock_mutation_allowed,
                self.exchange_order_allowed,
            ):
                _require(type(authority) is bool and authority is False)
            _require(
                self.publication_envelope_sha256
                == _hash_value(_envelope_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_envelope_preimage(self),
            "publication_envelope_sha256": self.publication_envelope_sha256,
        }

    def canonical_publication_envelope_json(self) -> str:
        """Return the canonical identity preimage, excluding its hash."""

        return _canonical_json(_envelope_preimage(self))


def _strict_inputs(
    *,
    publication_eligibility_result: E6PublicationEligibilityResultV1,
    final_strategy_gate_result: E6PythonFinalStrategyGateResultV1,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
    payload: E5TechnicalReviewPayloadV1,
    durable_review_execution: E6DurableReviewExecutionResultV1,
) -> None:
    exact_values = (
        (publication_eligibility_result, E6PublicationEligibilityResultV1),
        (final_strategy_gate_result, E6PythonFinalStrategyGateResultV1),
        (actionable_admission, E3ActionableAdmissionResultV1),
        (candidate_authority, ProductionCandidateAuthorityV1),
        (duplicate_protection_result, E4DuplicateProtectionCompositionResultV1),
        (payload, E5TechnicalReviewPayloadV1),
        (durable_review_execution, E6DurableReviewExecutionResultV1),
    )
    for value, expected_type in exact_values:
        _require(type(value) is expected_type)
        value.__post_init__()


def build_e6_publication_envelope_v1(
    *,
    publication_eligibility_result: E6PublicationEligibilityResultV1,
    final_strategy_gate_result: E6PythonFinalStrategyGateResultV1,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
    payload: E5TechnicalReviewPayloadV1,
    durable_review_execution: E6DurableReviewExecutionResultV1,
) -> E6PublicationEnvelopeV1:
    """Build one audit-ready proposal without publication authority."""

    try:
        _strict_inputs(
            publication_eligibility_result=publication_eligibility_result,
            final_strategy_gate_result=final_strategy_gate_result,
            actionable_admission=actionable_admission,
            candidate_authority=candidate_authority,
            duplicate_protection_result=duplicate_protection_result,
            payload=payload,
            durable_review_execution=durable_review_execution,
        )
        eligibility = publication_eligibility_result
        gate = final_strategy_gate_result
        admission = actionable_admission
        duplicate = duplicate_protection_result
        composition = durable_review_execution.final_composition
        geometry = admission.geometry
        targets = admission.structural_targets
        price_admission = admission.price_zone_admission
        snapshot = admission.executable_price_snapshot
        trigger = admission.mode_trigger_evidence
        lifecycle = admission.setup_lifecycle

        _require(eligibility.eligible_to_build_publication_envelope is True)
        _require(
            eligibility.publication_eligibility_decision_code
            == ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE
        )
        _require(eligibility.manual_owner_entry_required is True)
        _require(gate.may_proceed_to_publication_eligibility is True)
        _require(gate.final_gate_decision_code in _FINAL_PASS_CODES)
        _require(admission.actionable_admitted is True)
        _require(duplicate.publication_intent_allowed is True)
        _require(duplicate.fingerprint is not None)
        rebuilt_fingerprint = build_e4_thesis_fingerprint(
            geometry=geometry,
            structural_targets=targets,
            executable_price_snapshot=snapshot,
            mode_trigger_evidence=trigger,
            production_candidate_authority=candidate_authority,
        )
        authority_sha256 = candidate_authority_sha256_v1(candidate_authority)
        lineage = (
            eligibility.actionable_admission_sha256
            == gate.actionable_admission_sha256
            == admission.actionable_admission_sha256
            == duplicate.actionable_admission_sha256
            and eligibility.candidate_authority_sha256
            == gate.candidate_authority_sha256
            == authority_sha256
            and eligibility.duplicate_protection_sha256
            == gate.duplicate_protection_sha256
            == duplicate.composition_sha256
            and eligibility.thesis_fingerprint_sha256
            == gate.thesis_fingerprint_sha256
            == duplicate.fingerprint.identity_sha256
            == rebuilt_fingerprint.identity_sha256
            and gate.payload_sha256
            == payload.payload_sha256
            == durable_review_execution.payload_sha256
            == composition.payload_sha256
            and gate.durable_execution_sha256
            == durable_review_execution.execution_sha256
            and gate.final_composition_sha256 == composition.composition_sha256
            and eligibility.final_gate_sha256 == gate.final_gate_sha256
        )
        _require(lineage)
        _require(
            eligibility.publication_identity_sha256
            == _hash_value(
                {
                    "final_gate_sha256": gate.final_gate_sha256,
                    "actionable_admission_sha256": (
                        admission.actionable_admission_sha256
                    ),
                    "candidate_authority_sha256": authority_sha256,
                    "duplicate_protection_sha256": duplicate.composition_sha256,
                    "thesis_fingerprint_sha256": (
                        rebuilt_fingerprint.identity_sha256
                    ),
                    "signal_geometry_sha256": eligibility.signal_geometry_sha256,
                    "source_payload_hash": candidate_authority.source_payload_hash,
                }
            )
        )
        _require(
            eligibility.canonical_pair
            == gate.canonical_pair
            == rebuilt_fingerprint.canonical_pair
        )
        _require(
            eligibility.mode == gate.mode == geometry.mode == payload.mode
        )
        _require(eligibility.side == gate.side == geometry.side)
        _require(
            gate.structure_generation_id == geometry.structure_generation_id
        )
        _require(
            gate.trigger_generation_id == trigger.trigger_generation_id
        )
        _require(
            eligibility.source_payload_hash
            == candidate_authority.source_payload_hash
        )
        _require(
            eligibility.strategy_version == candidate_authority.strategy_version
        )
        _require(eligibility.valid_until == candidate_authority.valid_until)
        _require(price_admission.age_within_limit is True)
        _require(price_admission.spread_within_limit is True)
        _require(price_admission.slippage_within_limit is True)
        _require(price_admission.inside_zone is True)
        _require(trigger.trigger_fresh is True)
        _require(lifecycle.actionable_ready is True)

        review = composition.accepted_deepseek_review
        adjudication = composition.deepseek_adjudication
        route = composition.claude_route_result
        _require(review is not None and adjudication is not None and route is not None)
        _require(review.payload_sha256 == payload.payload_sha256)
        _require(adjudication.review_sha256 == review.review_sha256)
        _require(route.deepseek_adjudication_sha256 == adjudication.adjudication_sha256)
        _require(gate.final_score == adjudication.final_score)
        _require(gate.mode_score_floor == adjudication.mode_score_floor)
        _require(gate.deepseek_review_decision == review.decision)
        _require(gate.claude_route == route.route)
        _require(composition.may_continue_to_python_final_gate is True)
        _require(composition.publication_blocked is False)
        _require(composition.underlying_d8_cause is None)

        claude_review = composition.accepted_claude_review
        if route.claude_required:
            _require(claude_review is not None)
            _require(composition.claude_invocation_result is not None)
            claude_summary = claude_review.review_summary
            claude_provider_outcome = (
                composition.claude_invocation_result.final_result_code
            )
        else:
            _require(claude_review is None)
            _require(composition.claude_invocation_result is not None)
            _require(
                composition.claude_invocation_result.transport_invoked is False
            )
            claude_summary = NO_CLAUDE_REVIEW_REQUIRED
            claude_provider_outcome = (
                composition.claude_invocation_result.final_result_code
            )

        profile = get_mode_profile(geometry.mode)
        _require(profile.policy_version == geometry.mode_profile_version)
        zone_low = _decimal_price(geometry.golden_zone_low_tick, geometry.tick_size)
        zone_high = _decimal_price(
            geometry.golden_zone_high_tick,
            geometry.tick_size,
        )
        admission_price = _decimal_price(
            price_admission.executable_price_tick,
            geometry.tick_size,
        )
        stop_loss = _decimal_price(targets.stop_loss_tick, geometry.tick_size)
        tp1 = _decimal_price(targets.tp1_tick, geometry.tick_size)
        tp2 = _decimal_price(targets.tp2_tick, geometry.tick_size)
        source_envelope = {
            "schema_version": 1,
            "schema_name": PRODUCTION_SIGNAL_INPUT_SCHEMA,
            "source_commit": candidate_authority.source_commit,
            "source_evaluation_id": candidate_authority.source_evaluation_id,
            "mode": geometry.mode,
            "evaluated_at": price_admission.evaluation_timestamp,
            "production_evidence_ref": dict(
                candidate_authority.production_evidence_ref
            ),
            "outcome_kind": OUTCOME_PUBLISHED_SIGNAL,
            "eligible_setups": [
                {
                    "symbol": eligibility.canonical_pair,
                    "side": geometry.side,
                    "entry_zone": {
                        "min": _production_price(zone_low),
                        "max": _production_price(zone_high),
                    },
                    "stop_loss": _production_price(stop_loss),
                    "take_profit": {
                        "tp1": _production_price(tp1),
                        "tp2": _production_price(tp2),
                    },
                    "valid_until": candidate_authority.valid_until,
                    "strategy_version": candidate_authority.strategy_version,
                    "source_payload_hash": candidate_authority.source_payload_hash,
                }
            ],
            "component_versions": dict(candidate_authority.component_versions),
        }
        signal_id = build_signal_id(
            source_envelope=source_envelope,
            signal_geometry_hash=eligibility.signal_geometry_sha256,
            source_payload_hash=candidate_authority.source_payload_hash,
        )
        data: dict[str, object] = {
            "publication_envelope_version": E6_PUBLICATION_ENVELOPE_VERSION,
            "publication_envelope_schema": E6_PUBLICATION_ENVELOPE_SCHEMA,
            "signal_id": signal_id,
            "publication_identity_sha256": eligibility.publication_identity_sha256,
            "signal_geometry_sha256": eligibility.signal_geometry_sha256,
            "final_gate_sha256": gate.final_gate_sha256,
            "publication_eligibility_sha256": (
                eligibility.publication_eligibility_sha256
            ),
            "actionable_admission_sha256": admission.actionable_admission_sha256,
            "duplicate_protection_sha256": duplicate.composition_sha256,
            "payload_sha256": payload.payload_sha256,
            "durable_execution_sha256": durable_review_execution.execution_sha256,
            "thesis_fingerprint_sha256": rebuilt_fingerprint.identity_sha256,
            "source_commit": candidate_authority.source_commit,
            "source_evaluation_id": candidate_authority.source_evaluation_id,
            "source_payload_hash": candidate_authority.source_payload_hash,
            "canonical_venue": snapshot.venue,
            "canonical_pair": eligibility.canonical_pair,
            "mode": geometry.mode,
            "side": geometry.side,
            "strategy_version": candidate_authority.strategy_version,
            "mode_profile_version": geometry.mode_profile_version,
            "context_timeframes": profile.context_timeframes,
            "optional_context_timeframes": profile.optional_context_timeframes,
            "bias_timeframe": profile.bias_timeframe,
            "structure_timeframe": geometry.structure_timeframe,
            "trigger_timeframe": trigger.trigger_timeframe,
            "structure_generation_id": geometry.structure_generation_id,
            "trigger_generation_id": trigger.trigger_generation_id,
            "trigger_type": trigger.trigger_rule,
            "trigger_candle_close_at": trigger.trigger_candle_close_at,
            "tick_size": geometry.tick_size,
            "golden_zone_low": zone_low,
            "golden_zone_high": zone_high,
            "admission_price_source": price_admission.executable_price_source,
            "admission_price": admission_price,
            "admission_exchange_timestamp": snapshot.exchange_timestamp,
            "entry_zone_interpretation": (
                "LONG entry is owner-confirmed only within the Golden Zone."
                if geometry.side == "LONG"
                else "SHORT entry is owner-confirmed only within the Golden Zone."
            ),
            "stop_loss": stop_loss,
            "tp1_destination_kind": targets.tp1_destination_kind,
            "tp1_destination_id": targets.tp1_destination_id,
            "tp1": tp1,
            "tp2_destination_kind": targets.tp2_destination_kind,
            "tp2_destination_id": targets.tp2_destination_id,
            "tp2": tp2,
            "pre_review_score": adjudication.pre_review_score,
            "final_score": adjudication.final_score,
            "mode_score_floor": adjudication.mode_score_floor,
            "risk_reason_codes": review.reason_codes,
            "deepseek_d6_outcome": review.decision,
            "deepseek_d6_summary": review.concise_reason,
            "deepseek_d6_adjudication_outcome": adjudication.outcome_code,
            "claude_d7_route": route.route,
            "claude_d7_outcome": route.decision_code,
            "claude_d7_summary": claude_summary,
            "d8_deepseek_provider_outcome": (
                composition.deepseek_invocation_result.final_result_code
            ),
            "d8_claude_provider_outcome": claude_provider_outcome,
            "d8_underlying_fail_closed_cause": composition.underlying_d8_cause,
            "bounded_final_review_outcome": composition.final_outcome_code,
            "python_final_gate_decision": gate.final_gate_decision_code,
            "publication_eligibility_decision": (
                eligibility.publication_eligibility_decision_code
            ),
            "owner_action_state": OWNER_ACTION_AWAITING_MANUAL_DECISION,
            "manual_owner_authority_statement": MANUAL_OWNER_AUTHORITY_STATEMENT,
            "valid_until": candidate_authority.valid_until,
            "evaluation_timestamp": price_admission.evaluation_timestamp,
            "quote_age_seconds": price_admission.quote_age_seconds,
            "maximum_quote_age_seconds": price_admission.max_quote_age_seconds,
            "executable_price_fresh": price_admission.age_within_limit,
            "trigger_age_seconds": trigger.trigger_age_seconds,
            "maximum_trigger_age_seconds": trigger.maximum_trigger_age_seconds,
            "trigger_fresh": trigger.trigger_fresh,
            "lifecycle_state": lifecycle.resulting_state,
            "publication_side_effect_allowed": False,
            "telegram_send_allowed": False,
            "ledger_mutation_allowed": False,
            "entry_active_mutation_allowed": False,
            "slot_mutation_allowed": False,
            "pair_lock_mutation_allowed": False,
            "exchange_order_allowed": False,
        }
        temporary = object.__new__(E6PublicationEnvelopeV1)
        for name, value in data.items():
            object.__setattr__(temporary, name, value)
        return E6PublicationEnvelopeV1(
            **data,
            publication_envelope_sha256=_hash_value(
                _envelope_preimage(temporary)
            ),
        )
    except Exception:
        _fail()


__all__ = (
    "E6_PUBLICATION_ENVELOPE_VERSION",
    "E6_PUBLICATION_ENVELOPE_SCHEMA",
    "OWNER_ACTION_AWAITING_MANUAL_DECISION",
    "MANUAL_OWNER_AUTHORITY_STATEMENT",
    "E6PublicationEnvelopeV1",
    "build_e6_publication_envelope_v1",
)
