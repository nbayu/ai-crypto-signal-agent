"""Deterministic mode-isolated Master Engine evaluation and P2 ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
from typing import Final

import pandas as pd

from engine.atr import calculate_atr
from engine.golden_zone_skill import build_golden_zone_skill
from engine.market_structure import analyze_market_structure
from engine.mode_profile_v1 import get_mode_profile
from engine.mode_scan_execution_evidence_v1 import (
    ModeExecutionCandidateRowV1,
    ModeOiExecutionEvidenceV1,
    ModeScanExecutionResultV1,
    ModeTechnicalEvaluatorPayloadV1,
    ModeTimeframeExecutionEvidenceV1,
    build_e2_candidate_id,
    build_mode_technical_evaluator_payload,
)
from engine.mode_scan_execution_plan_v1 import (
    ModeScanExecutionPlanV1,
    ModeSymbolExecutionPlanV1,
)
from engine.order_block import distance_to_order_block
from engine.quality_filter import check_quality
from engine.scanner_result_builder import build_scanner_result
from engine.scanner_score_adjustment import apply_scanner_score_adjustment
from engine.scoring import calculate_score
from engine.smc import (
    detect_fvg,
    detect_liquidity_sweep,
    detect_order_blocks,
    distance_to_fvg,
)
from engine.validated_pipeline_v4 import MIN_FINAL_RANK_SCORE
from engine.volume_v2 import volume_metrics_v2


E6_PRODUCTION_TECHNICAL_POLICY_V1: Final = (
    "e6-production-deterministic-technical-evaluator-policy-v1"
)
CONTROLLED_TOP10_LIMIT_V1: Final = 10
FINAL_TOP5_LIMIT_V1: Final = 5
_ERROR: Final = "INVALID_E6_PRODUCTION_TECHNICAL_EVALUATION"


class E6ProductionTechnicalEvaluationErrorV1(ValueError):
    def __init__(self) -> None:
        self.code = _ERROR
        super().__init__(_ERROR)


def _invalid() -> None:
    raise E6ProductionTechnicalEvaluationErrorV1() from None


def _require(condition: bool) -> None:
    if not condition:
        _invalid()


def _json_safe(value: object) -> object:
    if value is None or type(value) in (str, int, float, bool):
        if type(value) is float:
            _require(math.isfinite(value))
        return value
    if hasattr(value, "item"):
        return _json_safe(value.item())
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if type(value) in (tuple, list):
        return [_json_safe(item) for item in value]
    if type(value) is dict:
        return {str(key): _json_safe(item) for key, item in value.items()}
    _invalid()


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            _json_safe(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        _invalid()


def _digest(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _copy_timeframe(value: object) -> ModeTimeframeExecutionEvidenceV1:
    _require(type(value) is ModeTimeframeExecutionEvidenceV1)
    return ModeTimeframeExecutionEvidenceV1(
        **{**value.to_mapping(), "raw_candles": value.raw_candles}
    )


def _copy_oi(value: object) -> ModeOiExecutionEvidenceV1:
    _require(type(value) is ModeOiExecutionEvidenceV1)
    return ModeOiExecutionEvidenceV1(
        **{**value.to_mapping(), "observations": value.observations}
    )


def _copy_payload(value: object) -> ModeTechnicalEvaluatorPayloadV1:
    _require(type(value) is ModeTechnicalEvaluatorPayloadV1)
    return ModeTechnicalEvaluatorPayloadV1(**value.to_mapping())


def _copy_candidate(value: object) -> ModeExecutionCandidateRowV1:
    _require(type(value) is ModeExecutionCandidateRowV1)
    return ModeExecutionCandidateRowV1(**value.to_mapping())


def _frame(evidence: ModeTimeframeExecutionEvidenceV1, *, closed_only: bool) -> pd.DataFrame:
    rows = evidence.raw_candles[:-1] if closed_only else evidence.raw_candles
    return pd.DataFrame(
        [
            {
                "timestamp": item.close_time,
                "open": item.open,
                "high": item.high,
                "low": item.low,
                "close": item.close,
                "volume": item.volume,
            }
            for item in rows
        ]
    )


def _source_rows(rows: list[dict[str, object]], candles: pd.DataFrame) -> list[dict[str, object]]:
    result = []
    for row in rows:
        copied = dict(row)
        index = copied.get("index")
        _require(type(index) is int and 0 <= index < len(candles))
        copied["source_at"] = candles["timestamp"].iloc[index]
        copied["source_high"] = float(candles["high"].iloc[index])
        copied["source_low"] = float(candles["low"].iloc[index])
        result.append(copied)
    return result


@dataclass(frozen=True, slots=True)
class E6ProductionTechnicalEvidenceV1:
    policy_version: str
    plan_sha256: str
    candidate_id: str
    mode: str
    mode_lineage_sha256: str
    canonical_symbol: str
    side: str
    structure_evidence: ModeTimeframeExecutionEvidenceV1
    trigger_evidence: ModeTimeframeExecutionEvidenceV1
    oi_evidence: ModeOiExecutionEvidenceV1
    evaluator_payload: ModeTechnicalEvaluatorPayloadV1
    golden_zone_json: str
    order_blocks_json: str
    fair_value_gaps_json: str
    liquidity_sweeps_json: str
    evidence_sha256: str

    def __post_init__(self) -> None:
        _require(self.policy_version == E6_PRODUCTION_TECHNICAL_POLICY_V1)
        _require(type(self.plan_sha256) is str and len(self.plan_sha256) == 64)
        _require(type(self.candidate_id) is str and self.candidate_id.startswith("e2c1:"))
        profile = get_mode_profile(self.mode)
        _require(self.mode_lineage_sha256 == self.structure_evidence.mode_lineage_sha256)
        _require(self.mode_lineage_sha256 == self.trigger_evidence.mode_lineage_sha256)
        _require(self.mode_lineage_sha256 == self.oi_evidence.mode_lineage_sha256)
        _require(self.canonical_symbol == self.structure_evidence.canonical_symbol)
        _require(self.canonical_symbol == self.trigger_evidence.canonical_symbol)
        _require(self.canonical_symbol == self.oi_evidence.canonical_symbol)
        _require(self.structure_evidence.timeframe == profile.structure_timeframe)
        _require(self.trigger_evidence.timeframe == profile.trigger_timeframe)
        _require(self.side in ("LONG", "SHORT"))
        for value in (
            self.structure_evidence,
            self.trigger_evidence,
            self.oi_evidence,
            self.evaluator_payload,
        ):
            value.__post_init__()
        for payload_json in (
            self.golden_zone_json,
            self.order_blocks_json,
            self.fair_value_gaps_json,
            self.liquidity_sweeps_json,
        ):
            _require(type(payload_json) is str)
            try:
                decoded = json.loads(payload_json)
            except Exception:
                _invalid()
            _require(_canonical_json(decoded) == payload_json)
        _require(self.evidence_sha256 == _digest(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "plan_sha256": self.plan_sha256,
            "candidate_id": self.candidate_id,
            "mode": self.mode,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "canonical_symbol": self.canonical_symbol,
            "side": self.side,
            "structure_evidence_sha256": self.structure_evidence.evidence_sha256,
            "trigger_evidence_sha256": self.trigger_evidence.evidence_sha256,
            "oi_evidence_sha256": self.oi_evidence.evidence_sha256,
            "evaluator_payload_sha256": self.evaluator_payload.payload_sha256,
            "golden_zone_json": self.golden_zone_json,
            "order_blocks_json": self.order_blocks_json,
            "fair_value_gaps_json": self.fair_value_gaps_json,
            "liquidity_sweeps_json": self.liquidity_sweeps_json,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["evidence_sha256"] = self.evidence_sha256
        return mapping


@dataclass(slots=True)
class E6ProductionTechnicalEvaluatorV1:
    """Callable pure strategy adapter with invocation-local evidence capture."""

    _registry: dict[str, E6ProductionTechnicalEvidenceV1] = field(
        default_factory=dict, init=False, repr=False
    )
    _rejections: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __call__(
        self,
        *,
        plan: ModeScanExecutionPlanV1,
        symbol_plan: ModeSymbolExecutionPlanV1,
        timeframe_evidence: tuple[ModeTimeframeExecutionEvidenceV1, ...],
        oi_evidence: ModeOiExecutionEvidenceV1,
        trigger_candle_close_at: str,
    ) -> ModeTechnicalEvaluatorPayloadV1 | None:
        _require(type(plan) is ModeScanExecutionPlanV1)
        _require(type(symbol_plan) is ModeSymbolExecutionPlanV1)
        _require(type(timeframe_evidence) is tuple)
        _require(type(oi_evidence) is ModeOiExecutionEvidenceV1)
        profile = get_mode_profile(plan.mode)
        by_timeframe = {item.timeframe: item for item in timeframe_evidence}
        _require(len(by_timeframe) == len(timeframe_evidence))
        structure_evidence = by_timeframe.get(profile.structure_timeframe)
        trigger_evidence = by_timeframe.get(profile.trigger_timeframe)
        _require(
            type(structure_evidence) is ModeTimeframeExecutionEvidenceV1
            and type(trigger_evidence) is ModeTimeframeExecutionEvidenceV1
        )
        structure = _frame(structure_evidence, closed_only=True)
        trigger = _frame(trigger_evidence, closed_only=True)
        structure_raw = _frame(structure_evidence, closed_only=False)
        if len(structure) < 100 or len(trigger) < 5:
            self._rejections[symbol_plan.canonical_symbol] = "E2_NO_ELIGIBLE_CANDIDATE"
            return None
        quality = check_quality(structure)
        if type(quality) is not dict or quality.get("qualified") is not True:
            self._rejections[symbol_plan.canonical_symbol] = "E2_NO_ELIGIBLE_CANDIDATE"
            return None
        structure_result = analyze_market_structure(structure)
        trigger_result = analyze_market_structure(trigger)
        if structure_result["trend"] == "SIDEWAYS":
            self._rejections[symbol_plan.canonical_symbol] = "E2_NO_ELIGIBLE_CANDIDATE"
            return None
        golden_zone = build_golden_zone_skill(structure, structure_result["trend"])
        if golden_zone is None:
            self._rejections[symbol_plan.canonical_symbol] = "E3_GEOMETRY_UNAVAILABLE"
            return None
        side = "LONG" if golden_zone["direction"] == "BULLISH" else "SHORT"
        sweeps = _source_rows(detect_liquidity_sweep(trigger), trigger)
        if profile.mode == "SCALP":
            sweep_kind = "sell_side" if side == "LONG" else "buy_side"
            trigger_break = trigger_result["bos"] if side == "LONG" else trigger_result["choch"]
            trigger_ok = trigger_break and any(
                item["type"] == sweep_kind and item["index"] < len(trigger) - 1
                for item in sweeps
            )
        else:
            trigger_ok = trigger_result["bos"] if side == "LONG" else trigger_result["choch"]
        if not trigger_ok:
            self._rejections[symbol_plan.canonical_symbol] = "E3_TRIGGER_NOT_CONFIRMED"
            return None

        order_blocks = _source_rows(detect_order_blocks(structure), structure)
        fair_value_gaps = _source_rows(detect_fvg(structure), structure)
        structure_sweeps = _source_rows(detect_liquidity_sweep(structure), structure)
        active_order_blocks = [item for item in order_blocks if item["mitigated"] is False]
        volume = volume_metrics_v2(structure_raw)
        atr = calculate_atr(structure)
        latest_oi = oi_evidence.observations[-1].open_interest
        prior_oi = oi_evidence.observations[-2].open_interest
        oi_growth = 0.0 if prior_oi == 0 else ((latest_oi - prior_oi) / prior_oi) * 100
        reference_price = float(trigger["close"].iloc[-1])
        row = build_scanner_result(
            symbol=symbol_plan.canonical_symbol,
            reference_price=reference_price,
            reference_candle_at=trigger_candle_close_at,
            trend=structure_result["trend"],
            mtf=None,
            mtf_score=0,
            bos=trigger_result["bos"],
            choch=trigger_result["choch"],
            golden_zone=_json_safe(golden_zone),
            quality=quality["score"],
            fvg=len(fair_value_gaps),
            order_blocks=len(active_order_blocks),
            liquidity=len(structure_sweeps),
            atr=atr,
            distance_ob=distance_to_order_block(structure),
            distance_fvg=distance_to_fvg(structure),
            volume=symbol_plan.quote_volume_24h,
            volume_spike=0,
            volume_ratio=volume["volume_ratio"],
            volume_v2_score=volume["volume_score"],
            volume_v2_status=volume["data_status"],
            open_interest=latest_oi,
            oi_growth=oi_growth,
        )
        score = apply_scanner_score_adjustment(
            calculate_score(row), row["distance_ob"], row["atr"]
        )
        payload = build_mode_technical_evaluator_payload(
            trigger_candle_close_at=trigger_candle_close_at,
            score=score,
            trend=structure_result["trend"],
            bos=trigger_result["bos"],
            choch=trigger_result["choch"],
            reference_price=reference_price,
            reference_candle_at=trigger_candle_close_at,
            volume_ratio=volume["volume_ratio"],
            volume_v2_status=volume["data_status"],
            golden_zone=_json_safe(golden_zone),
        )
        candidate_id = build_e2_candidate_id(
            plan_sha256=plan.plan_sha256,
            mode=plan.mode,
            mode_lineage_sha256=plan.mode_lineage_sha256,
            canonical_symbol=symbol_plan.canonical_symbol,
            reference_candle_at=trigger_candle_close_at,
            payload_sha256=payload.payload_sha256,
        )
        content = {
            "policy_version": E6_PRODUCTION_TECHNICAL_POLICY_V1,
            "plan_sha256": plan.plan_sha256,
            "candidate_id": candidate_id,
            "mode": plan.mode,
            "mode_lineage_sha256": plan.mode_lineage_sha256,
            "canonical_symbol": symbol_plan.canonical_symbol,
            "side": side,
            "structure_evidence": _copy_timeframe(structure_evidence),
            "trigger_evidence": _copy_timeframe(trigger_evidence),
            "oi_evidence": _copy_oi(oi_evidence),
            "evaluator_payload": _copy_payload(payload),
            "golden_zone_json": _canonical_json(golden_zone),
            "order_blocks_json": _canonical_json(active_order_blocks),
            "fair_value_gaps_json": _canonical_json(fair_value_gaps),
            "liquidity_sweeps_json": _canonical_json(structure_sweeps),
        }
        provisional = E6ProductionTechnicalEvidenceV1.__new__(E6ProductionTechnicalEvidenceV1)
        for key, value in content.items():
            object.__setattr__(provisional, key, value)
        object.__setattr__(provisional, "evidence_sha256", "0" * 64)
        evidence = E6ProductionTechnicalEvidenceV1(
            **content, evidence_sha256=_digest(provisional._content_mapping())
        )
        _require(candidate_id not in self._registry)
        self._registry[candidate_id] = evidence
        return payload

    def rejection_reasons(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._rejections.items()))

    def evidence_registry(self) -> tuple[E6ProductionTechnicalEvidenceV1, ...]:
        return tuple(self._registry[key] for key in sorted(self._registry))


@dataclass(frozen=True, slots=True)
class E6ProductionDeterministicRankingPipelineV1:
    score_floor: float = MIN_FINAL_RANK_SCORE

    def __post_init__(self) -> None:
        _require(type(self.score_floor) is float and self.score_floor == MIN_FINAL_RANK_SCORE)

    def rank(
        self, candidates: tuple[ModeExecutionCandidateRowV1, ...]
    ) -> tuple[tuple[ModeExecutionCandidateRowV1, ...], tuple[ModeExecutionCandidateRowV1, ...]]:
        _require(type(candidates) is tuple)
        copied = tuple(_copy_candidate(item) for item in candidates)
        ordered = tuple(
            sorted(
                copied,
                key=lambda item: (-float(item.payload_copy()["score"]), item.symbol),
            )
        )
        controlled = ordered[:CONTROLLED_TOP10_LIMIT_V1]
        final = tuple(
            item
            for item in controlled
            if math.floor(float(item.payload_copy()["score"])) >= self.score_floor
        )[:FINAL_TOP5_LIMIT_V1]
        return controlled, final


@dataclass(frozen=True, slots=True)
class E6ProductionModeScanResultV1:
    policy_version: str
    execution_result: ModeScanExecutionResultV1
    evidence_registry: tuple[E6ProductionTechnicalEvidenceV1, ...]
    controlled_top10: tuple[ModeExecutionCandidateRowV1, ...]
    final_top5: tuple[ModeExecutionCandidateRowV1, ...]
    no_trade_reason_code: str | None
    provider_invocation_count: int
    usage: tuple[tuple[str, int], ...]
    result_sha256: str

    def __post_init__(self) -> None:
        _require(self.policy_version == E6_PRODUCTION_TECHNICAL_POLICY_V1)
        _require(type(self.execution_result) is ModeScanExecutionResultV1)
        self.execution_result.__post_init__()
        registry = tuple(self.evidence_registry)
        controlled = tuple(self.controlled_top10)
        final = tuple(self.final_top5)
        _require(all(type(item) is E6ProductionTechnicalEvidenceV1 for item in registry))
        _require(all(type(item) is ModeExecutionCandidateRowV1 for item in controlled + final))
        by_id = {item.candidate_id: item for item in registry}
        _require(len(by_id) == len(registry))
        _require(all(item.candidate_id in by_id for item in controlled))
        _require(tuple(item.candidate_id for item in final) == tuple(item.candidate_id for item in controlled if math.floor(float(item.payload_copy()["score"])) >= MIN_FINAL_RANK_SCORE)[:FINAL_TOP5_LIMIT_V1])
        _require(type(self.provider_invocation_count) is int and self.provider_invocation_count == 0)
        _require(self.usage == ())
        if final:
            _require(self.no_trade_reason_code is None)
        else:
            _require(
                self.no_trade_reason_code
                in {
                    "E2_ALL_INPUTS_UNAVAILABLE",
                    "E2_NO_ELIGIBLE_CANDIDATE",
                    "E2_CONTROLLED_TOP10_EMPTY",
                    "E2_FINAL_TOP5_EMPTY",
                    "E3_TRIGGER_NOT_CONFIRMED",
                    "E3_GEOMETRY_UNAVAILABLE",
                }
            )
        _require(self.result_sha256 == _digest(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "execution_sha256": self.execution_result.execution_sha256,
            "evidence_registry": [item.evidence_sha256 for item in self.evidence_registry],
            "controlled_top10": [item.candidate_id for item in self.controlled_top10],
            "final_top5": [item.candidate_id for item in self.final_top5],
            "no_trade_reason_code": self.no_trade_reason_code,
            "provider_invocation_count": self.provider_invocation_count,
            "usage": [],
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["result_sha256"] = self.result_sha256
        return mapping

    def usage_copy(self) -> dict[str, int]:
        return {}


E6ProductionTechnicalEvaluationResultV1 = E6ProductionModeScanResultV1


def build_e6_production_mode_scan_result_v1(
    *,
    execution_result: ModeScanExecutionResultV1,
    technical_evaluator: E6ProductionTechnicalEvaluatorV1,
    ranking_pipeline: E6ProductionDeterministicRankingPipelineV1 = E6ProductionDeterministicRankingPipelineV1(),
) -> E6ProductionModeScanResultV1:
    _require(type(execution_result) is ModeScanExecutionResultV1)
    _require(type(technical_evaluator) is E6ProductionTechnicalEvaluatorV1)
    _require(type(ranking_pipeline) is E6ProductionDeterministicRankingPipelineV1)
    controlled, final = ranking_pipeline.rank(tuple(execution_result.candidates))
    registry = technical_evaluator.evidence_registry()
    registry_ids = {item.candidate_id for item in registry}
    _require({item.candidate_id for item in execution_result.candidates} == registry_ids)
    if final:
        reason = None
    elif execution_result.actual_evaluator_invocation_count == 0:
        reason = "E2_ALL_INPUTS_UNAVAILABLE"
    elif not execution_result.candidates:
        rejection_values = {item[1] for item in technical_evaluator.rejection_reasons()}
        if rejection_values == {"E3_TRIGGER_NOT_CONFIRMED"}:
            reason = "E3_TRIGGER_NOT_CONFIRMED"
        elif rejection_values == {"E3_GEOMETRY_UNAVAILABLE"}:
            reason = "E3_GEOMETRY_UNAVAILABLE"
        else:
            reason = "E2_NO_ELIGIBLE_CANDIDATE"
    elif not controlled:
        reason = "E2_CONTROLLED_TOP10_EMPTY"
    else:
        reason = "E2_FINAL_TOP5_EMPTY"
    content = {
        "policy_version": E6_PRODUCTION_TECHNICAL_POLICY_V1,
        "execution_result": execution_result,
        "evidence_registry": registry,
        "controlled_top10": controlled,
        "final_top5": final,
        "no_trade_reason_code": reason,
        "provider_invocation_count": 0,
        "usage": (),
    }
    provisional = E6ProductionModeScanResultV1.__new__(E6ProductionModeScanResultV1)
    for key, value in content.items():
        object.__setattr__(provisional, key, value)
    object.__setattr__(provisional, "result_sha256", "0" * 64)
    return E6ProductionModeScanResultV1(
        **content, result_sha256=_digest(provisional._content_mapping())
    )


__all__ = (
    "E6ProductionDeterministicRankingPipelineV1",
    "E6ProductionModeScanResultV1",
    "E6ProductionTechnicalEvaluationErrorV1",
    "E6ProductionTechnicalEvaluationResultV1",
    "E6ProductionTechnicalEvaluatorV1",
    "E6ProductionTechnicalEvidenceV1",
    "build_e6_production_mode_scan_result_v1",
)
