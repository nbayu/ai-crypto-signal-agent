"""Pure publication-envelope eligibility after the E6 Python final gate."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal, InvalidOperation
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
from engine.e6_python_final_strategy_gate_v1 import (
    PASS_CAUTION_L1_FINAL_STRATEGY,
    PASS_CLEAR_L0_FINAL_STRATEGY,
    E6PythonFinalStrategyGateResultV1,
    candidate_authority_sha256_v1,
    reconstruct_e6_python_final_strategy_gate_result_v1,
)
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)


PUBLICATION_ELIGIBILITY_VERSION: Final = "e6-publication-eligibility-v1"

ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE: Final = (
    "ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE"
)
INELIGIBLE_PYTHON_FINAL_STRATEGY: Final = (
    "INELIGIBLE_PYTHON_FINAL_STRATEGY"
)
INELIGIBLE_LINEAGE_OR_IDENTITY: Final = (
    "INELIGIBLE_LINEAGE_OR_IDENTITY"
)
INELIGIBLE_DUPLICATE_PROTECTION: Final = (
    "INELIGIBLE_DUPLICATE_PROTECTION"
)
INELIGIBLE_MISSING_PUBLICATION_PREREQUISITES: Final = (
    "INELIGIBLE_MISSING_PUBLICATION_PREREQUISITES"
)
INELIGIBLE_POLICY_OR_AMBIGUITY: Final = (
    "INELIGIBLE_POLICY_OR_AMBIGUITY"
)

PUBLICATION_ELIGIBILITY_DECISION_CODES: Final = (
    ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE,
    INELIGIBLE_PYTHON_FINAL_STRATEGY,
    INELIGIBLE_LINEAGE_OR_IDENTITY,
    INELIGIBLE_DUPLICATE_PROTECTION,
    INELIGIBLE_MISSING_PUBLICATION_PREREQUISITES,
    INELIGIBLE_POLICY_OR_AMBIGUITY,
)
PUBLICATION_ELIGIBILITY_FIELD_COUNT: Final = 27
OWNER_BLUEPRINT_CAPACITY_GATE_PLACEMENT: Final = (
    "SEPARATE_PREPUBLICATION_RUNTIME_GATE"
)

_FINAL_PASS_CODES: Final = frozenset(
    (PASS_CLEAR_L0_FINAL_STRATEGY, PASS_CAUTION_L1_FINAL_STRATEGY)
)
_MODES: Final = frozenset(("SWING", "INTRADAY", "SCALP"))
_SIDES: Final = frozenset(("LONG", "SHORT"))
_ERROR: Final = "invalid E6 publication eligibility"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_UTC_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?Z"
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


def _valid_utc(value: object) -> bool:
    if type(value) is not str or _UTC_PATTERN.fullmatch(value) is None:
        return False
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return False
    return True


def _eligibility_preimage(
    result: "E6PublicationEligibilityResultV1",
) -> dict[str, object]:
    return {
        field.name: getattr(result, field.name)
        for field in fields(E6PublicationEligibilityResultV1)
        if field.name != "publication_eligibility_sha256"
    }


@dataclass(frozen=True, slots=True)
class E6PublicationEligibilityResultV1:
    publication_eligibility_version: str
    final_gate_sha256: str
    actionable_admission_sha256: str
    candidate_authority_sha256: str
    duplicate_protection_sha256: str
    thesis_fingerprint_sha256: str
    publication_identity_sha256: str
    signal_geometry_sha256: str
    canonical_pair: str
    mode: str
    side: str
    structure_timeframe: str
    trigger_timeframe: str
    source_payload_hash: str
    strategy_version: str
    valid_until: str
    eligible_to_build_publication_envelope: bool
    publication_eligibility_decision_code: str
    manual_owner_entry_required: bool
    publication_side_effect_allowed: bool
    telegram_send_allowed: bool
    ledger_mutation_allowed: bool
    entry_active_mutation_allowed: bool
    slot_mutation_allowed: bool
    pair_lock_mutation_allowed: bool
    exchange_order_allowed: bool
    publication_eligibility_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                self.publication_eligibility_version
                == PUBLICATION_ELIGIBILITY_VERSION
            )
            for value in (
                self.final_gate_sha256,
                self.actionable_admission_sha256,
                self.candidate_authority_sha256,
                self.duplicate_protection_sha256,
                self.thesis_fingerprint_sha256,
                self.publication_identity_sha256,
                self.signal_geometry_sha256,
                self.source_payload_hash,
                self.publication_eligibility_sha256,
            ):
                _require(_valid_sha256(value))
            _require(
                type(self.canonical_pair) is str
                and normalize_pair(self.canonical_pair) == self.canonical_pair
            )
            _require(type(self.mode) is str and self.mode in _MODES)
            _require(type(self.side) is str and self.side in _SIDES)
            for value in (
                self.structure_timeframe,
                self.trigger_timeframe,
                self.strategy_version,
            ):
                _require(type(value) is str and bool(value))
            _require(
                _valid_utc(self.valid_until)
            )
            _require(type(self.eligible_to_build_publication_envelope) is bool)
            _require(
                self.publication_eligibility_decision_code
                in PUBLICATION_ELIGIBILITY_DECISION_CODES
            )
            _require(
                self.eligible_to_build_publication_envelope
                == (
                    self.publication_eligibility_decision_code
                    == ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE
                )
            )
            _require(
                type(self.manual_owner_entry_required) is bool
                and self.manual_owner_entry_required is True
            )
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
                self.publication_eligibility_sha256
                == _hash_value(_eligibility_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_eligibility_preimage(self),
            "publication_eligibility_sha256": (
                self.publication_eligibility_sha256
            ),
        }

    def canonical_publication_eligibility_json(self) -> str:
        return _canonical_json(_eligibility_preimage(self))


def reconstruct_e6_publication_eligibility_result_v1(
    mapping: Mapping[str, object],
) -> E6PublicationEligibilityResultV1:
    try:
        expected = tuple(
            field.name for field in fields(E6PublicationEligibilityResultV1)
        )
        _require(type(mapping) is dict)
        _require(tuple(mapping) == expected)
        return E6PublicationEligibilityResultV1(
            **{name: mapping[name] for name in expected}
        )
    except Exception:
        _fail()


def _strict_inputs(
    *,
    final_strategy_gate_result: E6PythonFinalStrategyGateResultV1,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
) -> tuple[E6PythonFinalStrategyGateResultV1, object, str]:
    _require(
        type(final_strategy_gate_result)
        is E6PythonFinalStrategyGateResultV1
    )
    final_strategy_gate_result.__post_init__()
    reconstructed_gate = reconstruct_e6_python_final_strategy_gate_result_v1(
        final_strategy_gate_result.to_mapping()
    )
    _require(reconstructed_gate.to_mapping() == final_strategy_gate_result.to_mapping())
    _require(type(actionable_admission) is E3ActionableAdmissionResultV1)
    actionable_admission.__post_init__()
    _require(type(candidate_authority) is ProductionCandidateAuthorityV1)
    candidate_authority.__post_init__()
    reconstructed_authority = ProductionCandidateAuthorityV1(
        **candidate_authority.to_dict()
    )
    _require(reconstructed_authority.to_dict() == candidate_authority.to_dict())
    _require(
        type(duplicate_protection_result)
        is E4DuplicateProtectionCompositionResultV1
    )
    duplicate_protection_result.__post_init__()
    rebuilt = build_e4_thesis_fingerprint(
        geometry=actionable_admission.geometry,
        structural_targets=actionable_admission.structural_targets,
        executable_price_snapshot=(
            actionable_admission.executable_price_snapshot
        ),
        mode_trigger_evidence=actionable_admission.mode_trigger_evidence,
        production_candidate_authority=candidate_authority,
    )
    return reconstructed_gate, rebuilt, candidate_authority_sha256_v1(
        candidate_authority
    )


def _signal_geometry_mapping(
    *,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    rebuilt_fingerprint: object,
) -> dict[str, object]:
    geometry = actionable_admission.geometry
    targets = actionable_admission.structural_targets
    return {
        "canonical_pair": rebuilt_fingerprint.canonical_pair,
        "mode": rebuilt_fingerprint.mode,
        "side": rebuilt_fingerprint.side,
        "structure_timeframe": rebuilt_fingerprint.structure_timeframe,
        "trigger_timeframe": rebuilt_fingerprint.trigger_timeframe,
        "structure_generation_id": rebuilt_fingerprint.structure_generation_id,
        "trigger_generation_id": rebuilt_fingerprint.trigger_generation_id,
        "tick_size": geometry.tick_size,
        "entry_zone_low_tick": geometry.golden_zone_low_tick,
        "entry_zone_high_tick": geometry.golden_zone_high_tick,
        "stop_loss_tick": geometry.stop_loss_tick,
        "tp1_tick": targets.tp1_tick,
        "tp2_tick": targets.tp2_tick,
        "valid_until": candidate_authority.valid_until,
        "strategy_version": candidate_authority.strategy_version,
        "source_payload_hash": candidate_authority.source_payload_hash,
    }


def _publication_prerequisites_complete(
    *,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    rebuilt_fingerprint: object,
) -> bool:
    try:
        geometry = actionable_admission.geometry
        targets = actionable_admission.structural_targets
        tick_size = Decimal(geometry.tick_size)
        expected_tp2 = tick_size * Decimal(targets.tp2_tick)
        authority_tp2 = Decimal(str(candidate_authority.tp2))
        return all(
            (
                actionable_admission.actionable_admitted is True,
                rebuilt_fingerprint.mode in _MODES,
                rebuilt_fingerprint.side in _SIDES,
                normalize_pair(rebuilt_fingerprint.canonical_pair)
                == rebuilt_fingerprint.canonical_pair,
                geometry.golden_zone_low_tick
                <= geometry.golden_zone_high_tick,
                targets.tp1_tick != targets.tp2_tick,
                geometry.stop_loss_tick
                not in (
                    geometry.golden_zone_low_tick,
                    geometry.golden_zone_high_tick,
                ),
                tick_size > 0,
                expected_tp2 == authority_tp2,
                bool(candidate_authority.strategy_version),
                _valid_sha256(candidate_authority.source_payload_hash),
                _valid_utc(candidate_authority.valid_until),
                bool(candidate_authority.production_evidence_ref),
                bool(candidate_authority.component_versions),
            )
        )
    except (InvalidOperation, TypeError, ValueError):
        return False


def _build_result(
    *,
    final_gate: E6PythonFinalStrategyGateResultV1,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
    rebuilt_fingerprint: object,
    authority_sha256: str,
    decision_code: str,
) -> E6PublicationEligibilityResultV1:
    geometry_mapping = _signal_geometry_mapping(
        actionable_admission=actionable_admission,
        candidate_authority=candidate_authority,
        rebuilt_fingerprint=rebuilt_fingerprint,
    )
    signal_geometry_sha256 = _hash_value(geometry_mapping)
    publication_identity_sha256 = _hash_value(
        {
            "final_gate_sha256": final_gate.final_gate_sha256,
            "actionable_admission_sha256": (
                actionable_admission.actionable_admission_sha256
            ),
            "candidate_authority_sha256": authority_sha256,
            "duplicate_protection_sha256": (
                duplicate_protection_result.composition_sha256
            ),
            "thesis_fingerprint_sha256": (
                rebuilt_fingerprint.identity_sha256
            ),
            "signal_geometry_sha256": signal_geometry_sha256,
            "source_payload_hash": candidate_authority.source_payload_hash,
        }
    )
    data: dict[str, object] = {
        "publication_eligibility_version": PUBLICATION_ELIGIBILITY_VERSION,
        "final_gate_sha256": final_gate.final_gate_sha256,
        "actionable_admission_sha256": (
            actionable_admission.actionable_admission_sha256
        ),
        "candidate_authority_sha256": authority_sha256,
        "duplicate_protection_sha256": (
            duplicate_protection_result.composition_sha256
        ),
        "thesis_fingerprint_sha256": rebuilt_fingerprint.identity_sha256,
        "publication_identity_sha256": publication_identity_sha256,
        "signal_geometry_sha256": signal_geometry_sha256,
        "canonical_pair": rebuilt_fingerprint.canonical_pair,
        "mode": rebuilt_fingerprint.mode,
        "side": rebuilt_fingerprint.side,
        "structure_timeframe": rebuilt_fingerprint.structure_timeframe,
        "trigger_timeframe": rebuilt_fingerprint.trigger_timeframe,
        "source_payload_hash": candidate_authority.source_payload_hash,
        "strategy_version": candidate_authority.strategy_version,
        "valid_until": candidate_authority.valid_until,
        "eligible_to_build_publication_envelope": (
            decision_code == ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE
        ),
        "publication_eligibility_decision_code": decision_code,
        "manual_owner_entry_required": True,
        "publication_side_effect_allowed": False,
        "telegram_send_allowed": False,
        "ledger_mutation_allowed": False,
        "entry_active_mutation_allowed": False,
        "slot_mutation_allowed": False,
        "pair_lock_mutation_allowed": False,
        "exchange_order_allowed": False,
    }
    temporary = object.__new__(E6PublicationEligibilityResultV1)
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E6PublicationEligibilityResultV1(
        **data,
        publication_eligibility_sha256=_hash_value(
            _eligibility_preimage(temporary)
        ),
    )


def evaluate_e6_publication_eligibility_v1(
    *,
    final_strategy_gate_result: E6PythonFinalStrategyGateResultV1,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
) -> E6PublicationEligibilityResultV1:
    try:
        final_gate, rebuilt, authority_sha256 = _strict_inputs(
            final_strategy_gate_result=final_strategy_gate_result,
            actionable_admission=actionable_admission,
            candidate_authority=candidate_authority,
            duplicate_protection_result=duplicate_protection_result,
        )
        if (
            final_gate.final_gate_decision_code not in _FINAL_PASS_CODES
            or not final_gate.may_proceed_to_publication_eligibility
        ):
            decision = INELIGIBLE_PYTHON_FINAL_STRATEGY
        else:
            lineage_matches = all(
                (
                    final_gate.actionable_admission_sha256
                    == actionable_admission.actionable_admission_sha256,
                    final_gate.candidate_authority_sha256 == authority_sha256,
                    final_gate.duplicate_protection_sha256
                    == duplicate_protection_result.composition_sha256,
                    final_gate.thesis_fingerprint_sha256
                    == rebuilt.identity_sha256,
                    final_gate.canonical_pair == rebuilt.canonical_pair,
                    final_gate.mode == rebuilt.mode,
                    final_gate.side == rebuilt.side,
                    final_gate.structure_timeframe
                    == rebuilt.structure_timeframe,
                    final_gate.trigger_timeframe == rebuilt.trigger_timeframe,
                )
            )
            stored_fingerprint = duplicate_protection_result.fingerprint
            if stored_fingerprint is not None:
                lineage_matches = (
                    lineage_matches
                    and stored_fingerprint.to_mapping() == rebuilt.to_mapping()
                )
            if not lineage_matches:
                decision = INELIGIBLE_LINEAGE_OR_IDENTITY
            elif (
                not duplicate_protection_result.actionable_admitted
                or not duplicate_protection_result.publication_intent_allowed
                or duplicate_protection_result.publication_guard_result is None
                or duplicate_protection_result.publication_guard_result.publication_success_recorded
            ):
                decision = INELIGIBLE_DUPLICATE_PROTECTION
            elif not _publication_prerequisites_complete(
                actionable_admission=actionable_admission,
                candidate_authority=candidate_authority,
                rebuilt_fingerprint=rebuilt,
            ):
                decision = INELIGIBLE_MISSING_PUBLICATION_PREREQUISITES
            elif final_gate.final_gate_decision_code not in (
                PASS_CLEAR_L0_FINAL_STRATEGY,
                PASS_CAUTION_L1_FINAL_STRATEGY,
            ):
                decision = INELIGIBLE_POLICY_OR_AMBIGUITY
            else:
                decision = ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE
        return _build_result(
            final_gate=final_gate,
            actionable_admission=actionable_admission,
            candidate_authority=candidate_authority,
            duplicate_protection_result=duplicate_protection_result,
            rebuilt_fingerprint=rebuilt,
            authority_sha256=authority_sha256,
            decision_code=decision,
        )
    except Exception:
        _fail()


__all__ = (
    "PUBLICATION_ELIGIBILITY_VERSION",
    "PUBLICATION_ELIGIBILITY_FIELD_COUNT",
    "OWNER_BLUEPRINT_CAPACITY_GATE_PLACEMENT",
    "ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE",
    "INELIGIBLE_PYTHON_FINAL_STRATEGY",
    "INELIGIBLE_LINEAGE_OR_IDENTITY",
    "INELIGIBLE_DUPLICATE_PROTECTION",
    "INELIGIBLE_MISSING_PUBLICATION_PREREQUISITES",
    "INELIGIBLE_POLICY_OR_AMBIGUITY",
    "PUBLICATION_ELIGIBILITY_DECISION_CODES",
    "E6PublicationEligibilityResultV1",
    "reconstruct_e6_publication_eligibility_result_v1",
    "evaluate_e6_publication_eligibility_v1",
)
