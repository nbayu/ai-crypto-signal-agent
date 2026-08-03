from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import inspect

import pytest

import engine.e6_production_technical_evaluator_v1 as module
from engine.mode_router_v1 import build_mode_scan_request
from engine.mode_scan_execution_evidence_v1 import (
    MODE_OI_OBSERVATION_SCHEMA_VERSION,
    MODE_UTC_CANDLE_SCHEMA_VERSION,
    ModeOiObservationV1,
    ModeUtcCandleV1,
)
from engine.mode_scan_execution_plan_v1 import (
    MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
    ModeMarketSnapshotEntryV1,
    build_mode_scan_execution_plan,
)
from engine.mode_scan_executor_v1 import execute_mode_scan_plan
from engine.validated_pipeline_v4 import MIN_FINAL_RANK_SCORE


OBSERVED = "2026-07-30T06:30:00Z"
SECONDS = {
    "1w": 604800, "1d": 86400, "4h": 14400, "1h": 3600,
    "15m": 900, "5m": 300, "3m": 180,
}


def _utc(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _developing_open(timeframe: str) -> datetime:
    observed = datetime.strptime(OBSERVED, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    epoch = datetime(1970, 1, 5 if timeframe == "1w" else 1, tzinfo=timezone.utc)
    elapsed = int((observed - epoch).total_seconds())
    return epoch + timedelta(seconds=(elapsed // SECONDS[timeframe]) * SECONDS[timeframe])


def _candles(timeframe_plan):
    final_open = _developing_open(timeframe_plan.timeframe)
    first = final_open - timedelta(
        seconds=SECONDS[timeframe_plan.timeframe] * timeframe_plan.closed_candle_limit
    )
    result = []
    for index in range(timeframe_plan.raw_fetch_limit):
        opened = first + timedelta(seconds=SECONDS[timeframe_plan.timeframe] * index)
        base = 100.0 + index * 0.1
        result.append(
            ModeUtcCandleV1(
                schema_version=MODE_UTC_CANDLE_SCHEMA_VERSION,
                timeframe=timeframe_plan.timeframe,
                open_time=_utc(opened),
                close_time=_utc(opened + timedelta(seconds=SECONDS[timeframe_plan.timeframe])),
                open=base,
                high=base + 2,
                low=base - 2,
                close=base + 1,
                volume=2000 + index,
            )
        )
    return tuple(result)


def _oi(*, symbol_plan, observed_at, period):
    assert period == "5m"
    observed = datetime.strptime(observed_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return tuple(
        ModeOiObservationV1(
            schema_version=MODE_OI_OBSERVATION_SCHEMA_VERSION,
            close_time=_utc(observed - timedelta(minutes=5 * (2 - index))),
            open_interest=1000 + index,
        )
        for index in range(3)
    )


def _plan(mode="SWING", count=1):
    snapshot = tuple(
        ModeMarketSnapshotEntryV1(
            schema_version=MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
            canonical_symbol=f"S{index:03d}/USDT:USDT",
            quote_asset="USDT",
            settle_asset="USDT",
            market_kind="swap",
            active=True,
            linear=True,
            perpetual=True,
            quote_volume_24h=10000 - index,
        )
        for index in range(count)
    )
    request = build_mode_scan_request(mode=mode, due_window_id="e6dw1:" + "a" * 64)
    return build_mode_scan_execution_plan(
        request=request, market_snapshot=snapshot, include_optional_context=False
    )


def _patch_strategy(monkeypatch, *, side="LONG", trigger=True, scores=None):
    calls: list[str] = []
    structures = iter(
        (
            {"trend": "UPTREND" if side == "LONG" else "DOWNTREND", "bos": side == "LONG", "choch": side == "SHORT"},
            {"trend": "UPTREND" if side == "LONG" else "DOWNTREND", "bos": trigger and side == "LONG", "choch": trigger and side == "SHORT"},
        )
    )

    def analyze(_df):
        calls.append("analyze_market_structure")
        try:
            return next(structures)
        except StopIteration:
            return {"trend": "UPTREND", "bos": True, "choch": False}

    monkeypatch.setattr(module, "check_quality", lambda _df: calls.append("check_quality") or {"qualified": True, "score": 100, "reasons": []})
    monkeypatch.setattr(module, "analyze_market_structure", analyze)
    monkeypatch.setattr(
        module,
        "build_golden_zone_skill",
        lambda df, trend: calls.append("build_golden_zone_skill") or {
            "direction": "BULLISH" if side == "LONG" else "BEARISH",
            "swing_low_index": 1,
            "swing_high_index": 2,
            "swing_low_at": df["timestamp"].iloc[1],
            "swing_high_at": df["timestamp"].iloc[2],
            "swing_low": 100.0,
            "swing_high": 120.0,
            "levels": {"-0.27": 125.4 if side == "LONG" else 94.6},
            "entry_zone": {"price_low": 104.0, "price_high": 108.0},
            "take_profit": {"level": -0.27, "price": 125.4 if side == "LONG" else 94.6},
            "stop_loss": {"level": 1.0, "price": 100.0 if side == "LONG" else 120.0},
        },
    )
    monkeypatch.setattr(module, "detect_order_blocks", lambda _df: calls.append("detect_order_blocks") or [{"type": "bearish" if side == "LONG" else "bullish", "index": 3, "high": 126.0, "low": 125.0, "mitigated": False}])
    monkeypatch.setattr(module, "detect_fvg", lambda _df: calls.append("detect_fvg") or [{"type": "bearish" if side == "LONG" else "bullish", "index": 4, "top": 128.0, "bottom": 127.0}])
    monkeypatch.setattr(module, "detect_liquidity_sweep", lambda _df: calls.append("detect_liquidity_sweep") or [{"type": "sell_side" if side == "LONG" else "buy_side", "index": 1}])
    monkeypatch.setattr(module, "calculate_atr", lambda _df: calls.append("calculate_atr") or 2.0)
    monkeypatch.setattr(module, "distance_to_order_block", lambda _df: calls.append("distance_to_order_block") or 0.0)
    monkeypatch.setattr(module, "distance_to_fvg", lambda _df: calls.append("distance_to_fvg") or 0.0)
    monkeypatch.setattr(module, "volume_metrics_v2", lambda _df: {"volume_ratio": 2.0, "volume_score": 66.67, "data_status": "OK"})
    monkeypatch.setattr(module, "calculate_score", lambda row: (scores or {}).get(row["symbol"], 90.0))
    monkeypatch.setattr(module, "apply_scanner_score_adjustment", lambda score, _distance, _atr: score)
    return calls


def _execute(monkeypatch, *, mode="SWING", count=1, side="LONG", trigger=True, scores=None):
    calls = _patch_strategy(monkeypatch, side=side, trigger=trigger, scores=scores)
    plan = _plan(mode, count)
    evaluator = module.E6ProductionTechnicalEvaluatorV1()
    execution = execute_mode_scan_plan(
        plan=plan,
        observed_at=OBSERVED,
        candle_fetcher=lambda *, timeframe_plan, observed_at: _candles(timeframe_plan),
        oi_fetcher=_oi,
        technical_evaluator=evaluator,
    )
    result = module.build_e6_production_mode_scan_result_v1(
        execution_result=execution,
        technical_evaluator=evaluator,
    )
    return plan, evaluator, execution, result, calls


def test_import_is_passive_and_has_no_external_or_legacy_validator_surface() -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    assert "deepseek" not in source.casefold()
    assert "run_validated_pipeline_v4" not in source
    assert "mtf_confirm" not in source
    assert "ccxt" not in source
    assert not any(
        isinstance(node, ast.Call) and getattr(node.func, "id", "") == "E6ProductionTechnicalEvaluatorV1"
        for node in tree.body
    )


@pytest.mark.parametrize("mode", ("SWING", "INTRADAY", "SCALP"))
def test_mode_isolation_and_exact_profile_timeframes(monkeypatch, mode: str) -> None:
    plan, _evaluator, execution, result, calls = _execute(monkeypatch, mode=mode)
    evidence = result.evidence_registry[0]
    profile = __import__("engine.mode_profile_v1", fromlist=["get_mode_profile"]).get_mode_profile(mode)
    assert execution.mode == evidence.mode == mode
    assert evidence.structure_evidence.timeframe == profile.structure_timeframe
    assert evidence.trigger_evidence.timeframe == profile.trigger_timeframe
    assert evidence.mode_lineage_sha256 == plan.mode_lineage_sha256
    assert result.provider_invocation_count == 0
    for expected in (
        "check_quality", "analyze_market_structure", "build_golden_zone_skill",
        "detect_fvg", "detect_order_blocks", "detect_liquidity_sweep",
        "calculate_atr", "distance_to_order_block", "distance_to_fvg",
    ):
        assert expected in calls


@pytest.mark.parametrize(("mode", "side"), (("SWING", "LONG"), ("SWING", "SHORT"), ("INTRADAY", "LONG"), ("INTRADAY", "SHORT"), ("SCALP", "LONG"), ("SCALP", "SHORT")))
def test_committed_directional_trigger_rules(monkeypatch, mode: str, side: str) -> None:
    _plan_value, _evaluator, execution, result, _calls = _execute(
        monkeypatch, mode=mode, side=side, trigger=True
    )
    assert execution.candidate_count == 1
    assert result.final_top5
    assert result.evidence_registry[0].side == side


@pytest.mark.parametrize("mode", ("SWING", "INTRADAY", "SCALP"))
def test_unconfirmed_or_unsupported_trigger_is_truthful_no_trade(monkeypatch, mode: str) -> None:
    _plan_value, _evaluator, execution, result, _calls = _execute(
        monkeypatch, mode=mode, trigger=False
    )
    assert execution.candidate_count == 0
    assert result.final_top5 == ()
    assert result.no_trade_reason_code == "E3_TRIGGER_NOT_CONFIRMED"


def test_controlled_top10_and_final_top5_are_deterministic_and_identity_preserving(monkeypatch) -> None:
    scores = {f"S{index:03d}/USDT:USDT": 99.0 - index for index in range(12)}
    _plan_value, _evaluator, execution, result, _calls = _execute(
        monkeypatch, count=12, scores=scores
    )
    assert len(execution.candidates) == 12
    assert len(result.controlled_top10) == 10
    assert len(result.final_top5) == 5
    assert [item.symbol for item in result.controlled_top10] == [
        f"S{index:03d}/USDT:USDT" for index in range(10)
    ]
    assert tuple(item.candidate_id for item in result.final_top5) == tuple(
        item.candidate_id for item in result.controlled_top10[:5]
    )
    assert MIN_FINAL_RANK_SCORE == 80.0


def test_final_floor_uses_authoritative_constant(monkeypatch) -> None:
    scores = {"S000/USDT:USDT": 79.99}
    _plan_value, _evaluator, _execution, result, _calls = _execute(
        monkeypatch, scores=scores
    )
    assert result.controlled_top10
    assert result.final_top5 == ()
    assert result.no_trade_reason_code == "E2_FINAL_TOP5_EMPTY"


def test_registry_is_immutable_output_and_hash_matches_candidate(monkeypatch) -> None:
    _plan_value, evaluator, execution, result, _calls = _execute(monkeypatch)
    registry = evaluator.evidence_registry()
    assert type(registry) is tuple
    assert registry[0].candidate_id == execution.candidates[0].candidate_id
    assert registry[0].evaluator_payload.payload_sha256 == execution.candidates[0].payload_sha256
    assert result.evidence_registry == registry
    assert result.usage_copy() == {}


def test_source_contains_no_retry_provider_exchange_or_test_fixture_import() -> None:
    source = inspect.getsource(module).casefold()
    for prohibited in (
        "import tests", "from tests", "create_order", "send_message",
        "provider_client", "while true", "retry(",
    ):
        assert prohibited not in source
