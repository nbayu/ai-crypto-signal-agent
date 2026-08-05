"""Typed P2 bridge from ranked E2 evidence through complete E3 admission."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_UP,
)
from hashlib import sha256
import json
import math
import re
from typing import Final

from engine.e3_actionable_admission_v1 import (
    E3ActionableAdmissionResultV1,
    build_e3_actionable_admission,
)
from engine.e3_executable_price_snapshot_v1 import (
    E3ExecutablePriceSnapshotV1,
    build_e3_executable_price_snapshot,
)
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
    build_e3_golden_zone_geometry,
)
from engine.e3_mode_trigger_evidence_v1 import (
    E3ModeTriggerEvidenceV1,
    build_e3_mode_trigger_evidence,
)
from engine.e3_price_zone_admission_v1 import (
    E3PriceZoneAdmissionV1,
    build_e3_price_zone_admission,
)
from engine.e3_setup_lifecycle_v1 import (
    E3LifecycleResultV1,
    build_e3_setup_lifecycle,
)
from engine.e3_structural_targets_v1 import (
    DESTINATION_KIND_LIQUIDITY,
    DESTINATION_KIND_STRUCTURE,
    E3StructuralTargetsV1,
    build_e3_structural_targets,
)
from engine.e6_production_cycle_input_v1 import (
    E6_NO_TRADE_CYCLE_POLICY_V1,
    E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
    E6NoTradeCycleRequestV1,
)
from engine.e6_production_market_acquisition_v1 import (
    BINANCE_USDM_VENUE_V1,
    E6ProductionExecutableQuoteEvidenceV1,
)
from engine.e6_production_technical_evaluator_v1 import (
    E6ProductionModeScanResultV1,
    E6ProductionTechnicalEvidenceV1,
)
from engine.mode_scan_execution_evidence_v1 import ModeExecutionCandidateRowV1
from engine.mode_profile_v1 import get_mode_profile
from engine.outcome_tracker_v4 import validate_outcome_invocation_id


E6_PRODUCTION_E3_BRIDGE_POLICY_V1: Final = "e6-production-e3-bridge-policy-v1"
FIB_EXTENSION: Final = "FIB_EXTENSION"
LIQUIDITY_SWEEP: Final = "LIQUIDITY_SWEEP"
ORDER_BLOCK: Final = "ORDER_BLOCK"
FVG: Final = "FVG"
_SOURCE_PRECEDENCE: Final = {
    FIB_EXTENSION: 0,
    LIQUIDITY_SWEEP: 1,
    ORDER_BLOCK: 2,
    FVG: 3,
}
_SHA1: Final = re.compile(r"[0-9a-f]{40}\Z")
_SHA256: Final = re.compile(r"[0-9a-f]{64}\Z")
_ERROR: Final = "INVALID_E6_PRODUCTION_E3_BRIDGE"


class E6ProductionE3BridgeErrorV1(ValueError):
    def __init__(self) -> None:
        self.code = _ERROR
        super().__init__(_ERROR)


class _InsufficientEvidence(Exception):
    def __init__(self, reason_code: str, source_reason_code: str) -> None:
        self.reason_code = reason_code
        self.source_reason_code = source_reason_code


def _invalid() -> None:
    raise E6ProductionE3BridgeErrorV1() from None


def _require(condition: bool) -> None:
    if not condition:
        _invalid()


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        _invalid()


def _digest(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _decoded(value: str, expected_type: type) -> object:
    _require(type(value) is str)
    try:
        decoded = json.loads(value)
    except Exception:
        _invalid()
    _require(type(decoded) is expected_type and _canonical_json(decoded) == value)
    return decoded


def _price_tick(value: object, tick_size: str) -> int:
    try:
        price = Decimal(str(value))
        size = Decimal(tick_size)
        ratio = price / size
    except (InvalidOperation, ValueError, ZeroDivisionError):
        raise _InsufficientEvidence(
            "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE",
            "PRICE_NOT_ALIGNED_TO_MARKET_TICK",
        ) from None
    if not price.is_finite() or not size.is_finite() or price <= 0 or size <= 0:
        raise _InsufficientEvidence(
            "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE",
            "PRICE_NOT_ALIGNED_TO_MARKET_TICK",
        )
    integral = ratio.to_integral_value()
    if ratio != integral or integral <= 0:
        raise _InsufficientEvidence(
            "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE",
            "PRICE_NOT_ALIGNED_TO_MARKET_TICK",
        )
    return int(integral)


def _normalized_price_tick(
    value: object,
    tick_size: str,
    *,
    rounding: str,
) -> int:
    try:
        price = Decimal(str(value))
        size = Decimal(tick_size)
        ratio = price / size
    except (InvalidOperation, ValueError, ZeroDivisionError):
        raise _InsufficientEvidence(
            "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE",
            "PRICE_NOT_ALIGNED_TO_MARKET_TICK",
        ) from None
    if not price.is_finite() or not size.is_finite() or price <= 0 or size <= 0:
        raise _InsufficientEvidence(
            "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE",
            "PRICE_NOT_ALIGNED_TO_MARKET_TICK",
        )
    integral = ratio.to_integral_value(rounding=rounding)
    if integral <= 0:
        raise _InsufficientEvidence(
            "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE",
            "PRICE_NOT_ALIGNED_TO_MARKET_TICK",
        )
    return int(integral)


@dataclass(frozen=True, slots=True)
class E6ProductionDestinationEvidenceV1:
    source_kind: str
    destination_kind: str
    destination_id: str
    destination_tick: int
    source_at: str
    structure_timeframe: str
    structure_generation_id: str

    def __post_init__(self) -> None:
        _require(self.source_kind in _SOURCE_PRECEDENCE)
        expected_kind = (
            DESTINATION_KIND_LIQUIDITY
            if self.source_kind == LIQUIDITY_SWEEP
            else DESTINATION_KIND_STRUCTURE
        )
        _require(self.destination_kind == expected_kind)
        _require(type(self.destination_id) is str and re.fullmatch(r"e3d1:[0-9a-f]{64}", self.destination_id))
        _require(type(self.destination_tick) is int and self.destination_tick > 0)
        _require(type(self.source_at) is str and self.source_at.endswith("Z"))
        _require(type(self.structure_timeframe) is str and self.structure_timeframe)
        _require(type(self.structure_generation_id) is str and self.structure_generation_id)

    def to_target_record(self) -> tuple[object, ...]:
        return (
            self.destination_kind,
            self.destination_id,
            self.destination_tick,
            self.structure_timeframe,
            self.structure_generation_id,
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind,
            "destination_kind": self.destination_kind,
            "destination_id": self.destination_id,
            "destination_tick": self.destination_tick,
            "source_at": self.source_at,
            "structure_timeframe": self.structure_timeframe,
            "structure_generation_id": self.structure_generation_id,
        }


@dataclass(frozen=True, slots=True)
class E6ProductionE3CandidateV1:
    policy_version: str
    source_commit: str
    outcome_invocation_id: str
    mode: str
    due_job_id: str
    due_window_occurrence_id: str
    mode_lineage_sha256: str
    candidate: ModeExecutionCandidateRowV1
    mode_scan_result: E6ProductionModeScanResultV1
    technical_evidence: E6ProductionTechnicalEvidenceV1
    geometry: E3GoldenZoneGeometryV1
    destination_evidence: tuple[E6ProductionDestinationEvidenceV1, ...]
    structural_targets: E3StructuralTargetsV1
    executable_price_snapshot: E3ExecutablePriceSnapshotV1
    price_zone_admission: E3PriceZoneAdmissionV1
    mode_trigger_evidence: E3ModeTriggerEvidenceV1
    setup_lifecycle: E3LifecycleResultV1
    actionable_admission: E3ActionableAdmissionResultV1
    controlled_rank: int
    final_rank: int
    technical_score: float
    audit_manifest_sha256: str
    provider_attempt_count: int
    telegram_attempt_count: int
    exchange_order_count: int
    slot_mutation_count: int
    pair_lock_mutation_count: int
    entry_active_mutation_count: int
    retry_count: int

    def __post_init__(self) -> None:
        _require(self.policy_version == E6_PRODUCTION_E3_BRIDGE_POLICY_V1)
        _require(type(self.source_commit) is str and _SHA1.fullmatch(self.source_commit))
        validate_outcome_invocation_id(self.outcome_invocation_id)
        _require(type(self.candidate) is ModeExecutionCandidateRowV1)
        _require(type(self.mode_scan_result) is E6ProductionModeScanResultV1)
        _require(type(self.technical_evidence) is E6ProductionTechnicalEvidenceV1)
        _require(self.mode == self.candidate.mode == self.technical_evidence.mode)
        _require(self.mode_lineage_sha256 == self.candidate.mode_lineage_sha256 == self.technical_evidence.mode_lineage_sha256)
        _require(self.candidate.candidate_id == self.technical_evidence.candidate_id)
        _require(type(self.geometry) is E3GoldenZoneGeometryV1)
        _require(type(self.destination_evidence) in (tuple, list) and len(self.destination_evidence) == 2)
        destinations = tuple(self.destination_evidence)
        _require(all(type(item) is E6ProductionDestinationEvidenceV1 for item in destinations))
        object.__setattr__(self, "destination_evidence", destinations)
        for value, expected_type in (
            (self.structural_targets, E3StructuralTargetsV1),
            (self.executable_price_snapshot, E3ExecutablePriceSnapshotV1),
            (self.price_zone_admission, E3PriceZoneAdmissionV1),
            (self.mode_trigger_evidence, E3ModeTriggerEvidenceV1),
            (self.setup_lifecycle, E3LifecycleResultV1),
            (self.actionable_admission, E3ActionableAdmissionResultV1),
        ):
            _require(type(value) is expected_type)
            value.__post_init__()
        _require(self.actionable_admission.actionable_admitted is True)
        _require(type(self.controlled_rank) is int and self.controlled_rank >= 1)
        _require(type(self.final_rank) is int and self.final_rank >= 1)
        _require(type(self.technical_score) is float and math.isfinite(self.technical_score))
        for count in (
            self.provider_attempt_count,
            self.telegram_attempt_count,
            self.exchange_order_count,
            self.slot_mutation_count,
            self.pair_lock_mutation_count,
            self.entry_active_mutation_count,
            self.retry_count,
        ):
            _require(type(count) is int and count == 0)
        _require(type(self.audit_manifest_sha256) is str and _SHA256.fullmatch(self.audit_manifest_sha256))
        _require(self.audit_manifest_sha256 == _digest(self._audit_mapping()))

    def _audit_mapping(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "source_commit": self.source_commit,
            "outcome_invocation_id": self.outcome_invocation_id,
            "mode": self.mode,
            "due_job_id": self.due_job_id,
            "due_window_occurrence_id": self.due_window_occurrence_id,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "candidate_id": self.candidate.candidate_id,
            "execution_sha256": self.mode_scan_result.execution_result.execution_sha256,
            "technical_evidence_sha256": self.technical_evidence.evidence_sha256,
            "geometry_sha256": self.geometry.geometry_sha256,
            "destination_evidence": [item.to_mapping() for item in self.destination_evidence],
            "targets_sha256": self.structural_targets.targets_sha256,
            "snapshot_sha256": self.executable_price_snapshot.snapshot_sha256,
            "admission_sha256": self.price_zone_admission.admission_sha256,
            "trigger_evidence_sha256": self.mode_trigger_evidence.trigger_evidence_sha256,
            "lifecycle_sha256": self.setup_lifecycle.lifecycle_sha256,
            "actionable_admission_sha256": self.actionable_admission.actionable_admission_sha256,
            "controlled_rank": self.controlled_rank,
            "final_rank": self.final_rank,
            "technical_score": self.technical_score,
            "effect_counts": {
                "provider": 0,
                "telegram": 0,
                "exchange": 0,
                "slot": 0,
                "pair_lock": 0,
                "entry_active": 0,
                "retry": 0,
            },
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._audit_mapping()
        mapping["audit_manifest_sha256"] = self.audit_manifest_sha256
        return mapping


def _no_trade(
    *,
    source_commit: str,
    outcome_invocation_id: str,
    mode: str,
    due_job_id: str,
    due_window_occurrence_id: str,
    mode_lineage_sha256: str,
    observed_at: str,
    reason_code: str,
    source_reason_code: str,
    scan_composition_sha256: str,
    execution_sha256: str,
    e3_evidence_sha256: str,
) -> E6NoTradeCycleRequestV1:
    audit = _digest(
        {
            "domain": E6_PRODUCTION_E3_BRIDGE_POLICY_V1,
            "mode": mode,
            "due_window_occurrence_id": due_window_occurrence_id,
            "reason_code": reason_code,
            "source_reason_code": source_reason_code,
            "scan_composition_sha256": scan_composition_sha256,
            "execution_sha256": execution_sha256,
            "e3_evidence_sha256": e3_evidence_sha256,
        }
    )
    return E6NoTradeCycleRequestV1(
        schema_version=E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
        policy_version=E6_NO_TRADE_CYCLE_POLICY_V1,
        source_commit=source_commit,
        outcome_invocation_id=outcome_invocation_id,
        mode=mode,
        due_job_id=due_job_id,
        due_window_occurrence_id=due_window_occurrence_id,
        mode_lineage_sha256=mode_lineage_sha256,
        observed_at=observed_at,
        reason_code=reason_code,
        source_reason_code=source_reason_code,
        scan_composition_sha256=scan_composition_sha256,
        execution_sha256=execution_sha256,
        e3_evidence_sha256=e3_evidence_sha256,
        audit_manifest_sha256=audit,
        provider_attempt_count=0,
        telegram_attempt_count=0,
        exchange_order_count=0,
        slot_mutation_count=0,
        pair_lock_mutation_count=0,
        entry_active_mutation_count=0,
        retry_count=0,
    )


def _destination_id(
    *,
    source_kind: str,
    symbol: str,
    mode: str,
    timeframe: str,
    generation: str,
    source_at: str,
    source_close: float,
    tick: int,
) -> str:
    return "e3d1:" + _digest(
        {
            "domain": E6_PRODUCTION_E3_BRIDGE_POLICY_V1,
            "source_kind": source_kind,
            "symbol": symbol,
            "mode": mode,
            "timeframe": timeframe,
            "structure_generation_id": generation,
            "source_at": source_at,
            "source_close": source_close,
            "destination_tick": tick,
        }
    )


def _candidate_destinations(
    *, geometry: E3GoldenZoneGeometryV1, evidence: E6ProductionTechnicalEvidenceV1
) -> tuple[E6ProductionDestinationEvidenceV1, ...]:
    golden_zone = _decoded(evidence.golden_zone_json, dict)
    order_blocks = _decoded(evidence.order_blocks_json, list)
    gaps = _decoded(evidence.fair_value_gaps_json, list)
    sweeps = _decoded(evidence.liquidity_sweeps_json, list)
    closed = evidence.structure_evidence.raw_candles[:-1]
    close_by_at = {item.close_time: float(item.close) for item in closed}
    candidates: list[tuple[str, float, str]] = []
    fib = golden_zone.get("take_profit")
    if type(fib) is dict and "price" in fib:
        source_at = golden_zone["swing_high_at"] if geometry.side == "LONG" else golden_zone["swing_low_at"]
        candidates.append((FIB_EXTENSION, float(fib["price"]), source_at))
    opposing_ob = "bearish" if geometry.side == "LONG" else "bullish"
    for item in order_blocks:
        if item.get("type") == opposing_ob and item.get("mitigated") is False:
            price = item["low"] if geometry.side == "LONG" else item["high"]
            candidates.append((ORDER_BLOCK, float(price), item["source_at"]))
    opposing_gap = "bearish" if geometry.side == "LONG" else "bullish"
    for item in gaps:
        if item.get("type") == opposing_gap:
            price = item["bottom"] if geometry.side == "LONG" else item["top"]
            candidates.append((FVG, float(price), item["source_at"]))
    matching_sweep = "sell_side" if geometry.side == "LONG" else "buy_side"
    for item in sweeps:
        if item.get("type") == matching_sweep:
            price = item["source_low"] if geometry.side == "LONG" else item["source_high"]
            candidates.append((LIQUIDITY_SWEEP, float(price), item["source_at"]))

    by_tick: dict[int, tuple[str, float, str]] = {}
    for source_kind, price, source_at in candidates:
        tick = _normalized_price_tick(
            price,
            geometry.tick_size,
            rounding=ROUND_FLOOR if geometry.side == "LONG" else ROUND_CEILING,
        )
        profitable = (
            tick > geometry.golden_zone_high_tick
            if geometry.side == "LONG"
            else tick < geometry.golden_zone_low_tick
        )
        if not profitable:
            continue
        current = by_tick.get(tick)
        if current is None or _SOURCE_PRECEDENCE[source_kind] < _SOURCE_PRECEDENCE[current[0]]:
            by_tick[tick] = (source_kind, price, source_at)
    built = []
    for tick, (source_kind, _price, source_at) in by_tick.items():
        source_close = close_by_at.get(source_at)
        if source_close is None:
            source_close = float(golden_zone["swing_high"] if geometry.side == "LONG" else golden_zone["swing_low"])
        built.append(
            E6ProductionDestinationEvidenceV1(
                source_kind=source_kind,
                destination_kind=(
                    DESTINATION_KIND_LIQUIDITY
                    if source_kind == LIQUIDITY_SWEEP
                    else DESTINATION_KIND_STRUCTURE
                ),
                destination_id=_destination_id(
                    source_kind=source_kind,
                    symbol=geometry.canonical_symbol,
                    mode=geometry.mode,
                    timeframe=geometry.structure_timeframe,
                    generation=geometry.structure_generation_id,
                    source_at=source_at,
                    source_close=source_close,
                    tick=tick,
                ),
                destination_tick=tick,
                source_at=source_at,
                structure_timeframe=geometry.structure_timeframe,
                structure_generation_id=geometry.structure_generation_id,
            )
        )
    built.sort(
        key=lambda item: (
            item.destination_tick - geometry.golden_zone_high_tick
            if geometry.side == "LONG"
            else geometry.golden_zone_low_tick - item.destination_tick,
            item.source_at,
            item.destination_id,
        )
    )
    if len(built) < 2:
        raise _InsufficientEvidence(
            "E3_STRUCTURAL_DESTINATIONS_INCOMPLETE",
            "FEWER_THAN_TWO_DISTINCT_PROFITABLE_DESTINATIONS",
        )
    return tuple(built[:2])


def build_e6_production_e3_candidate_v1(
    *,
    source_commit: str,
    outcome_invocation_id: str,
    due_job_id: str,
    due_window_occurrence_id: str,
    observed_at: str,
    mode_scan_result: E6ProductionModeScanResultV1,
    candidate: ModeExecutionCandidateRowV1,
    technical_evidence: E6ProductionTechnicalEvidenceV1,
    quote_evidence: E6ProductionExecutableQuoteEvidenceV1,
) -> E6NoTradeCycleRequestV1 | E6ProductionE3CandidateV1:
    _require(type(mode_scan_result) is E6ProductionModeScanResultV1)
    _require(type(candidate) is ModeExecutionCandidateRowV1)
    _require(type(technical_evidence) is E6ProductionTechnicalEvidenceV1)
    _require(type(quote_evidence) is E6ProductionExecutableQuoteEvidenceV1)
    _require(candidate.candidate_id == technical_evidence.candidate_id)
    _require(candidate.mode == technical_evidence.mode)
    scan_hash = mode_scan_result.execution_result.plan_sha256
    execution_hash = mode_scan_result.execution_result.execution_sha256
    e3_seed = _digest(
        {
            "technical_evidence_sha256": technical_evidence.evidence_sha256,
            "quote_sha256": quote_evidence.quote_sha256,
        }
    )
    try:
        golden_zone = _decoded(technical_evidence.golden_zone_json, dict)
        side = technical_evidence.side
        generation = "e3sg1:" + _digest(
            {
                "mode": candidate.mode,
                "symbol": candidate.symbol,
                "structure_evidence_sha256": technical_evidence.structure_evidence.evidence_sha256,
                "golden_zone": golden_zone,
            }
        )
        geometry = build_e3_golden_zone_geometry(
            mode=candidate.mode,
            mode_lineage_sha256=candidate.mode_lineage_sha256,
            canonical_symbol=candidate.symbol,
            side=side,
            structure_generation_id=generation,
            anchor_low_at=golden_zone["swing_low_at"],
            anchor_low_tick=_price_tick(golden_zone["swing_low"], quote_evidence.tick_size),
            anchor_high_at=golden_zone["swing_high_at"],
            anchor_high_tick=_price_tick(golden_zone["swing_high"], quote_evidence.tick_size),
            tick_size=quote_evidence.tick_size,
        )
        destinations = _candidate_destinations(geometry=geometry, evidence=technical_evidence)
        targets = build_e3_structural_targets(
            geometry=geometry,
            ordered_destinations=tuple(item.to_target_record() for item in destinations),
        )
        mark = quote_evidence.mark_price
        slippage = math.ceil(
            max(
                0.0,
                quote_evidence.best_ask - mark
                if side == "LONG"
                else mark - quote_evidence.best_bid,
            )
            / mark
            * 10000
        )
        snapshot = build_e3_executable_price_snapshot(
            geometry=geometry,
            venue=BINANCE_USDM_VENUE_V1,
            quote_generation_id="e3q1:" + quote_evidence.quote_sha256,
            exchange_timestamp=quote_evidence.exchange_timestamp,
            best_bid_tick=_price_tick(quote_evidence.best_bid, quote_evidence.tick_size),
            best_ask_tick=_price_tick(quote_evidence.best_ask, quote_evidence.tick_size),
            last_price_tick=_normalized_price_tick(
                quote_evidence.last_price,
                quote_evidence.tick_size,
                rounding=ROUND_HALF_UP,
            ),
            mark_price_tick=_normalized_price_tick(
                quote_evidence.mark_price,
                quote_evidence.tick_size,
                rounding=ROUND_HALF_UP,
            ),
            modeled_adverse_slippage_bps=slippage,
            tick_size=quote_evidence.tick_size,
        )
        admission = build_e3_price_zone_admission(
            geometry=geometry,
            snapshot=snapshot,
            evaluation_timestamp=observed_at,
        )
        trigger = build_e3_mode_trigger_evidence(
            geometry=geometry,
            mode=geometry.mode,
            mode_lineage_sha256=geometry.mode_lineage_sha256,
            canonical_symbol=geometry.canonical_symbol,
            side=geometry.side,
            structure_timeframe=geometry.structure_timeframe,
            structure_generation_id=geometry.structure_generation_id,
            trigger_timeframe=technical_evidence.trigger_evidence.timeframe,
            trigger_rule=get_mode_profile(geometry.mode).trigger_rule,
            trigger_candle_close_at=technical_evidence.trigger_evidence.closed_candle_close_at,
            trigger_candle_closed=True,
            trigger_rule_satisfied=True,
            evaluation_timestamp=observed_at,
        )
        lifecycle = build_e3_setup_lifecycle(
            previous_state="DISCOVERED",
            requested_state="ACTIONABLE",
            geometry=geometry,
            structural_targets=targets,
            price_zone_admission=admission,
            mode_trigger_evidence=trigger,
            structure_valid=True,
        )
        actionable = build_e3_actionable_admission(
            geometry=geometry,
            structural_targets=targets,
            executable_price_snapshot=snapshot,
            price_zone_admission=admission,
            mode_trigger_evidence=trigger,
            setup_lifecycle=lifecycle,
        )
        if actionable.actionable_admitted is not True:
            raise _InsufficientEvidence(
                "E3_ACTIONABLE_REJECTED",
                actionable.reason_code,
            )
        controlled_rank = next(index for index, item in enumerate(mode_scan_result.controlled_top10, 1) if item.candidate_id == candidate.candidate_id)
        final_rank = next(index for index, item in enumerate(mode_scan_result.final_top5, 1) if item.candidate_id == candidate.candidate_id)
        content = {
            "policy_version": E6_PRODUCTION_E3_BRIDGE_POLICY_V1,
            "source_commit": source_commit,
            "outcome_invocation_id": outcome_invocation_id,
            "mode": candidate.mode,
            "due_job_id": due_job_id,
            "due_window_occurrence_id": due_window_occurrence_id,
            "mode_lineage_sha256": candidate.mode_lineage_sha256,
            "candidate": candidate,
            "mode_scan_result": mode_scan_result,
            "technical_evidence": technical_evidence,
            "geometry": geometry,
            "destination_evidence": destinations,
            "structural_targets": targets,
            "executable_price_snapshot": snapshot,
            "price_zone_admission": admission,
            "mode_trigger_evidence": trigger,
            "setup_lifecycle": lifecycle,
            "actionable_admission": actionable,
            "controlled_rank": controlled_rank,
            "final_rank": final_rank,
            "technical_score": float(candidate.payload_copy()["score"]),
            "provider_attempt_count": 0,
            "telegram_attempt_count": 0,
            "exchange_order_count": 0,
            "slot_mutation_count": 0,
            "pair_lock_mutation_count": 0,
            "entry_active_mutation_count": 0,
            "retry_count": 0,
        }
        provisional = E6ProductionE3CandidateV1.__new__(E6ProductionE3CandidateV1)
        for key, value in content.items():
            object.__setattr__(provisional, key, value)
        object.__setattr__(provisional, "audit_manifest_sha256", "0" * 64)
        return E6ProductionE3CandidateV1(
            **content,
            audit_manifest_sha256=_digest(provisional._audit_mapping()),
        )
    except _InsufficientEvidence as exc:
        return _no_trade(
            source_commit=source_commit,
            outcome_invocation_id=outcome_invocation_id,
            mode=candidate.mode,
            due_job_id=due_job_id,
            due_window_occurrence_id=due_window_occurrence_id,
            mode_lineage_sha256=candidate.mode_lineage_sha256,
            observed_at=observed_at,
            reason_code=exc.reason_code,
            source_reason_code=exc.source_reason_code,
            scan_composition_sha256=scan_hash,
            execution_sha256=execution_hash,
            e3_evidence_sha256=e3_seed,
        )


__all__ = (
    "E6ProductionDestinationEvidenceV1",
    "E6ProductionE3BridgeErrorV1",
    "E6ProductionE3CandidateV1",
    "FIB_EXTENSION",
    "FVG",
    "LIQUIDITY_SWEEP",
    "ORDER_BLOCK",
    "build_e6_production_e3_candidate_v1",
)
