from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
import inspect
import json

import pytest

import engine.e6_production_e3_bridge_v1 as module
from engine.e6_production_cycle_input_v1 import E6NoTradeCycleRequestV1
from engine.e6_production_market_acquisition_v1 import (
    E6ProductionExecutableQuoteEvidenceV1,
)
from engine.e6_production_technical_evaluator_v1 import (
    E6ProductionModeScanResultV1,
    E6ProductionTechnicalEvidenceV1,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_scan_execution_evidence_v1 import (
    MODE_UTC_CANDLE_SCHEMA_VERSION,
    ModeExecutionCandidateRowV1,
    ModeScanExecutionResultV1,
    ModeTimeframeExecutionEvidenceV1,
    ModeUtcCandleV1,
)


COMMIT = "a" * 40
INVOCATION = "b" * 32
OCCURRENCE = "e6dw1:" + "c" * 64
OBSERVED = "2026-07-30T00:15:00Z"


def _typed_new(cls, **values):
    instance = cls.__new__(cls)
    for name, value in values.items():
        object.__setattr__(instance, name, value)
    return instance


def _candle(timeframe, open_at, close_at, close):
    return ModeUtcCandleV1(
        schema_version=MODE_UTC_CANDLE_SCHEMA_VERSION,
        timeframe=timeframe,
        open_time=open_at,
        close_time=close_at,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=2000,
    )


def _scenario(*, side="LONG", sparse=False, quote_price=None):
    mode = "SWING"
    lineage = build_mode_audit_lineage(mode).lineage_sha256
    candidate_id = "e2c1:" + "d" * 64
    candidate = _typed_new(
        ModeExecutionCandidateRowV1,
        schema_version="mode-execution-candidate-row-v1",
        policy_version="mode-scan-execution-evidence-policy-v1",
        plan_sha256="1" * 64,
        candidate_id=candidate_id,
        mode=mode,
        symbol="BTC/USDT:USDT",
        mode_lineage_sha256=lineage,
        reference_candle_at=OBSERVED,
        payload_json=json.dumps({"score": 90.0}, sort_keys=True, separators=(",", ":")),
        payload_sha256="2" * 64,
    )
    execution = _typed_new(
        ModeScanExecutionResultV1,
        plan_sha256="1" * 64,
        execution_sha256="3" * 64,
    )
    scan_result = _typed_new(
        E6ProductionModeScanResultV1,
        execution_result=execution,
        controlled_top10=(candidate,),
        final_top5=(candidate,),
    )
    structure_candles = (
        _candle("1h", "2026-07-29T00:00:00Z", "2026-07-29T01:00:00Z", 100.0),
        _candle("1h", "2026-07-29T01:00:00Z", "2026-07-29T02:00:00Z", 102.0),
        _candle("1h", "2026-07-29T02:00:00Z", "2026-07-29T03:00:00Z", 126.0),
        _candle("1h", "2026-07-29T03:00:00Z", "2026-07-29T04:00:00Z", 127.0),
    )
    structure = _typed_new(
        ModeTimeframeExecutionEvidenceV1,
        raw_candles=structure_candles,
        evidence_sha256="4" * 64,
    )
    trigger = _typed_new(
        ModeTimeframeExecutionEvidenceV1,
        timeframe="15m",
        closed_candle_close_at=OBSERVED,
        evidence_sha256="5" * 64,
    )
    if side == "LONG":
        low_at, high_at = "2026-07-29T00:00:00Z", "2026-07-29T01:00:00Z"
        direction = "BULLISH"
        fib_price = 125.4
        order_block = {"type": "bearish", "mitigated": False, "low": 126.0, "high": 127.0, "source_at": "2026-07-29T02:00:00Z"}
        gap = {"type": "bearish", "bottom": 127.0, "top": 128.0, "source_at": "2026-07-29T03:00:00Z"}
        sweep = {"type": "sell_side", "source_low": 129.0, "source_high": 130.0, "source_at": "2026-07-29T03:00:00Z"}
        default_price = 105.0
        bid, ask, mark = default_price - 0.1, default_price, default_price
    else:
        low_at, high_at = "2026-07-29T01:00:00Z", "2026-07-29T00:00:00Z"
        direction = "BEARISH"
        fib_price = 94.6
        order_block = {"type": "bullish", "mitigated": False, "low": 93.0, "high": 94.0, "source_at": "2026-07-29T02:00:00Z"}
        gap = {"type": "bullish", "bottom": 92.0, "top": 93.0, "source_at": "2026-07-29T03:00:00Z"}
        sweep = {"type": "buy_side", "source_low": 90.0, "source_high": 91.0, "source_at": "2026-07-29T03:00:00Z"}
        default_price = 115.0
        bid, ask, mark = default_price, default_price + 0.1, default_price
    golden = {
        "direction": direction,
        "swing_low_at": low_at,
        "swing_high_at": high_at,
        "swing_low": 100.0,
        "swing_high": 120.0,
        "take_profit": {"level": -0.27, "price": fib_price},
    }
    technical = _typed_new(
        E6ProductionTechnicalEvidenceV1,
        mode=mode,
        mode_lineage_sha256=lineage,
        canonical_symbol=candidate.symbol,
        candidate_id=candidate_id,
        side=side,
        structure_evidence=structure,
        trigger_evidence=trigger,
        golden_zone_json=json.dumps(golden, sort_keys=True, separators=(",", ":")),
        order_blocks_json=json.dumps([] if sparse else [order_block], sort_keys=True, separators=(",", ":")),
        fair_value_gaps_json=json.dumps([] if sparse else [gap], sort_keys=True, separators=(",", ":")),
        liquidity_sweeps_json=json.dumps([] if sparse else [sweep], sort_keys=True, separators=(",", ":")),
        evidence_sha256="6" * 64,
    )
    selected_price = default_price if quote_price is None else quote_price
    if side == "LONG":
        bid, ask, mark = selected_price - 0.1, selected_price, selected_price
    else:
        bid, ask, mark = selected_price, selected_price + 0.1, selected_price
    quote = _typed_new(
        E6ProductionExecutableQuoteEvidenceV1,
        canonical_symbol=candidate.symbol,
        tick_size="0.1",
        exchange_timestamp=OBSERVED,
        best_bid=bid,
        best_ask=ask,
        last_price=selected_price,
        mark_price=mark,
        quote_sha256="7" * 64,
    )
    return scan_result, candidate, technical, quote


def _build(*, side="LONG", sparse=False, quote_price=None):
    scan, candidate, evidence, quote = _scenario(
        side=side, sparse=sparse, quote_price=quote_price
    )
    return module.build_e6_production_e3_candidate_v1(
        source_commit=COMMIT,
        outcome_invocation_id=INVOCATION,
        due_job_id="SWING:BASE_EVALUATION",
        due_window_occurrence_id=OCCURRENCE,
        observed_at=OBSERVED,
        mode_scan_result=scan,
        candidate=candidate,
        technical_evidence=evidence,
        quote_evidence=quote,
    )


def test_import_is_passive_and_candidate_bundle_is_frozen_slotted() -> None:
    source = inspect.getsource(module)
    ast.parse(source)
    assert "ccxt" not in source and "requests" not in source
    result = _build()
    assert type(result) is module.E6ProductionE3CandidateV1
    assert "__dict__" not in result.__slots__
    with pytest.raises(FrozenInstanceError):
        result.mode = "SCALP"


@pytest.mark.parametrize("side", ("LONG", "SHORT"))
def test_complete_real_e3_constructor_lineage_and_zero_effects(side: str) -> None:
    result = _build(side=side)
    assert type(result) is module.E6ProductionE3CandidateV1
    assert result.geometry.side == side
    assert len(result.destination_evidence) == 2
    assert result.structural_targets.geometry is result.geometry
    assert result.executable_price_snapshot.geometry is result.geometry
    assert result.price_zone_admission.decision == "PASS_PRICE_ADMISSION"
    assert result.mode_trigger_evidence.decision == "PASS_TRIGGER_EVIDENCE"
    assert result.setup_lifecycle.resulting_state == "ACTIONABLE"
    assert result.actionable_admission.actionable_admitted is True
    assert result.provider_attempt_count == result.telegram_attempt_count == 0
    assert result.exchange_order_count == result.slot_mutation_count == 0
    assert result.pair_lock_mutation_count == result.entry_active_mutation_count == 0
    assert result.retry_count == 0


def test_destination_sources_are_bounded_profitable_deduplicated_and_ordered() -> None:
    result = _build()
    assert type(result) is module.E6ProductionE3CandidateV1
    allowed = {
        module.FIB_EXTENSION,
        module.LIQUIDITY_SWEEP,
        module.ORDER_BLOCK,
        module.FVG,
    }
    assert {item.source_kind for item in result.destination_evidence} <= allowed
    assert len({item.destination_tick for item in result.destination_evidence}) == 2
    assert [item.destination_tick for item in result.destination_evidence] == sorted(
        item.destination_tick for item in result.destination_evidence
    )
    assert all(
        item.destination_tick > result.geometry.golden_zone_high_tick
        for item in result.destination_evidence
    )


def test_equal_tick_uses_fibonacci_before_other_sources() -> None:
    scan, candidate, evidence, quote = _scenario()
    golden = json.loads(evidence.golden_zone_json)
    order_blocks = [{"type": "bearish", "mitigated": False, "low": golden["take_profit"]["price"], "high": 126.0, "source_at": "2026-07-29T02:00:00Z"}]
    object.__setattr__(evidence, "order_blocks_json", json.dumps(order_blocks, sort_keys=True, separators=(",", ":")))
    result = module.build_e6_production_e3_candidate_v1(
        source_commit=COMMIT,
        outcome_invocation_id=INVOCATION,
        due_job_id="SWING:BASE_EVALUATION",
        due_window_occurrence_id=OCCURRENCE,
        observed_at=OBSERVED,
        mode_scan_result=scan,
        candidate=candidate,
        technical_evidence=evidence,
        quote_evidence=quote,
    )
    assert type(result) is module.E6ProductionE3CandidateV1
    assert result.destination_evidence[0].source_kind == module.FIB_EXTENSION


def test_fewer_than_two_destinations_is_exact_no_trade() -> None:
    result = _build(sparse=True)
    assert type(result) is E6NoTradeCycleRequestV1
    assert result.reason_code == "E3_STRUCTURAL_DESTINATIONS_INCOMPLETE"
    assert result.provider_attempt_count == result.telegram_attempt_count == 0


def test_outside_zone_is_valid_actionable_hold_mapped_to_no_trade() -> None:
    result = _build(quote_price=119.0)
    assert type(result) is E6NoTradeCycleRequestV1
    assert result.reason_code == "E3_ACTIONABLE_REJECTED"


@pytest.mark.parametrize(
    ("side", "best_bid", "best_ask", "mark", "expected"),
    (
        ("LONG", 104.9, 105.2, 105.0, 20),
        ("SHORT", 104.8, 105.1, 105.0, 20),
    ),
)
def test_adverse_slippage_formulas_are_exact(monkeypatch, side, best_bid, best_ask, mark, expected) -> None:
    scan, candidate, evidence, quote = _scenario(side=side)
    object.__setattr__(quote, "best_bid", best_bid)
    object.__setattr__(quote, "best_ask", best_ask)
    object.__setattr__(quote, "mark_price", mark)
    captured = {}
    real = module.build_e3_executable_price_snapshot

    def spy(**values):
        captured.update(values)
        return real(**values)

    monkeypatch.setattr(module, "build_e3_executable_price_snapshot", spy)
    module.build_e6_production_e3_candidate_v1(
        source_commit=COMMIT,
        outcome_invocation_id=INVOCATION,
        due_job_id="SWING:BASE_EVALUATION",
        due_window_occurrence_id=OCCURRENCE,
        observed_at=OBSERVED,
        mode_scan_result=scan,
        candidate=candidate,
        technical_evidence=evidence,
        quote_evidence=quote,
    )
    assert captured["modeled_adverse_slippage_bps"] == expected



@pytest.mark.parametrize(
    ("side", "raw_fib_price", "expected_tick"),
    (
        ("LONG", 125.49, 1254),
        ("SHORT", 94.51, 946),
    ),
)
def test_non_aligned_analytical_destination_is_normalized_conservatively(
    side: str,
    raw_fib_price: float,
    expected_tick: int,
) -> None:
    scan, candidate, evidence, quote = _scenario(side=side)
    golden = json.loads(evidence.golden_zone_json)
    golden["take_profit"]["price"] = raw_fib_price
    object.__setattr__(
        evidence,
        "golden_zone_json",
        json.dumps(golden, sort_keys=True, separators=(",", ":")),
    )

    result = module.build_e6_production_e3_candidate_v1(
        source_commit=COMMIT,
        outcome_invocation_id=INVOCATION,
        due_job_id="SWING:BASE_EVALUATION",
        due_window_occurrence_id=OCCURRENCE,
        observed_at=OBSERVED,
        mode_scan_result=scan,
        candidate=candidate,
        technical_evidence=evidence,
        quote_evidence=quote,
    )

    assert type(result) is module.E6ProductionE3CandidateV1
    fibonacci = tuple(
        item
        for item in result.destination_evidence
        if item.source_kind == module.FIB_EXTENSION
    )
    assert len(fibonacci) == 1
    assert fibonacci[0].destination_tick == expected_tick


def test_non_aligned_last_and_mark_prices_are_nearest_tick_reference_evidence() -> None:
    scan, candidate, evidence, quote = _scenario()
    object.__setattr__(quote, "last_price", 105.04)
    object.__setattr__(quote, "mark_price", 105.04)

    result = module.build_e6_production_e3_candidate_v1(
        source_commit=COMMIT,
        outcome_invocation_id=INVOCATION,
        due_job_id="SWING:BASE_EVALUATION",
        due_window_occurrence_id=OCCURRENCE,
        observed_at=OBSERVED,
        mode_scan_result=scan,
        candidate=candidate,
        technical_evidence=evidence,
        quote_evidence=quote,
    )

    assert type(result) is module.E6ProductionE3CandidateV1
    assert result.executable_price_snapshot.last_price_tick == 1050
    assert result.executable_price_snapshot.mark_price_tick == 1050
    assert result.price_zone_admission.executable_price_tick == 1050


@pytest.mark.parametrize(("field", "value"), (("best_bid", 104.94), ("best_ask", 105.04)))
def test_non_aligned_executable_book_price_remains_fail_closed(
    field: str,
    value: float,
) -> None:
    scan, candidate, evidence, quote = _scenario()
    object.__setattr__(quote, field, value)

    result = module.build_e6_production_e3_candidate_v1(
        source_commit=COMMIT,
        outcome_invocation_id=INVOCATION,
        due_job_id="SWING:BASE_EVALUATION",
        due_window_occurrence_id=OCCURRENCE,
        observed_at=OBSERVED,
        mode_scan_result=scan,
        candidate=candidate,
        technical_evidence=evidence,
        quote_evidence=quote,
    )

    assert type(result) is E6NoTradeCycleRequestV1
    assert result.reason_code == "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE"
    assert result.source_reason_code == "PRICE_NOT_ALIGNED_TO_MARKET_TICK"
    assert result.provider_attempt_count == result.telegram_attempt_count == 0


def test_constructor_corruption_is_not_disguised_as_no_trade(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "build_e3_golden_zone_geometry",
        lambda **_values: (_ for _ in ()).throw(RuntimeError("corrupt")),
    )
    with pytest.raises(RuntimeError, match="corrupt"):
        _build()


def test_source_has_no_projection_retry_external_client_or_exchange_authority() -> None:
    source = inspect.getsource(module).casefold()
    for prohibited in (
        "import tests", "from tests", "create_order", "send_message",
        "provider_client", "telegram_client", "retry(", "projection", "extrapolat",
    ):
        assert prohibited not in source
