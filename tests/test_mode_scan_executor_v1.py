from __future__ import annotations

import ast
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.mode_scan_executor_v1 as executor_module
from engine.mode_router_v1 import build_mode_scan_request
from engine.mode_scan_execution_evidence_v1 import (
    MODE_OI_OBSERVATION_SCHEMA_VERSION,
    MODE_UTC_CANDLE_SCHEMA_VERSION,
    OUTCOME_CANDIDATE,
    OUTCOME_NO_CANDIDATE,
    OUTCOME_SKIPPED,
    REASON_CANDLE_BOUNDARY_EXCEPTION,
    REASON_CANDLE_EVIDENCE_INVALID,
    REASON_EVALUATOR_EXCEPTION,
    REASON_EVALUATOR_RESULT_INVALID,
    REASON_NO_CANDIDATE,
    REASON_OI_BOUNDARY_EXCEPTION,
    REASON_OI_EVIDENCE_INVALID,
    ModeOiObservationV1,
    ModeScanExecutionResultV1,
    ModeTechnicalEvaluatorPayloadV1,
    ModeUtcCandleV1,
    build_e2_candidate_id,
    build_mode_technical_evaluator_payload,
)
from engine.mode_scan_execution_plan_v1 import (
    MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
    ModeMarketSnapshotEntryV1,
    ModeScanExecutionPlanV1,
    build_mode_scan_execution_plan,
)
from engine.mode_scan_executor_v1 import (
    MODE_SCAN_EXECUTOR_POLICY_VERSION,
    ModeScanExecutorValidationError,
    execute_mode_scan_plan,
)


ENGINE_PATH = Path("engine/mode_scan_executor_v1.py")
TEST_PATH = Path("tests/test_mode_scan_executor_v1.py")
OBSERVED_AT = "2026-07-30T06:30:00Z"
TIMEFRAME_SECONDS = {
    "1w": 604800,
    "1d": 86400,
    "4h": 14400,
    "1h": 3600,
    "15m": 900,
    "5m": 300,
    "3m": 180,
}


class TextSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class TaggedResult:
    outcome_kind = "CANDIDATE"


class PayloadSubclass(ModeTechnicalEvaluatorPayloadV1):
    pass


class PlanSubclass(ModeScanExecutionPlanV1):
    pass


def snapshot_entry(symbol, volume):
    return ModeMarketSnapshotEntryV1(
        schema_version=MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
        canonical_symbol=symbol,
        quote_asset="USDT",
        settle_asset="USDT",
        market_kind="swap",
        active=True,
        linear=True,
        perpetual=True,
        quote_volume_24h=volume,
    )


def make_plan(mode="SWING", count=1, optional=False):
    snapshot = [
        snapshot_entry(
            f"S{index:03d}/USDT:USDT",
            1000.0 - index,
        )
        for index in range(count)
    ]
    request = build_mode_scan_request(
        mode=mode,
        due_window_id=f"window-{mode.lower()}",
    )
    return build_mode_scan_execution_plan(
        request=request,
        market_snapshot=snapshot,
        include_optional_context=optional,
    )


def utc_text(value):
    return value.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def developing_open(observed_at, timeframe):
    observed = datetime.strptime(
        observed_at,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    epoch = datetime(
        1970,
        1,
        5 if timeframe == "1w" else 1,
        tzinfo=timezone.utc,
    )
    duration = TIMEFRAME_SECONDS[timeframe]
    elapsed = int((observed - epoch).total_seconds())
    return epoch + timedelta(
        seconds=(elapsed // duration) * duration
    )


def make_candle(timeframe, opened, index=0):
    base = 100.0 + index
    return ModeUtcCandleV1(
        schema_version=MODE_UTC_CANDLE_SCHEMA_VERSION,
        timeframe=timeframe,
        open_time=utc_text(opened),
        close_time=utc_text(
            opened
            + timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
        ),
        open=base,
        high=base + 2.0,
        low=base - 2.0,
        close=base + 1.0,
        volume=1000.0 + index,
    )


def candles_for(timeframe_plan, observed_at=OBSERVED_AT):
    final_open = developing_open(
        observed_at,
        timeframe_plan.timeframe,
    )
    duration = TIMEFRAME_SECONDS[timeframe_plan.timeframe]
    first_open = final_open - timedelta(
        seconds=duration * timeframe_plan.closed_candle_limit
    )
    return tuple(
        make_candle(
            timeframe_plan.timeframe,
            first_open + timedelta(seconds=duration * index),
            index,
        )
        for index in range(timeframe_plan.raw_fetch_limit)
    )


def oi_observations(
    observed_at=OBSERVED_AT,
    *,
    newest_offset_minutes=0,
):
    observed = datetime.strptime(
        observed_at,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    newest = observed + timedelta(minutes=newest_offset_minutes)
    return tuple(
        ModeOiObservationV1(
            schema_version=MODE_OI_OBSERVATION_SCHEMA_VERSION,
            close_time=utc_text(
                newest - timedelta(minutes=5 * (2 - index))
            ),
            open_interest=1000.0 + index,
        )
        for index in range(3)
    )


def payload_for(trigger_candle_close_at):
    return build_mode_technical_evaluator_payload(
        trigger_candle_close_at=trigger_candle_close_at,
        score=91,
        trend="UPTREND",
        bos=True,
        choch=False,
        reference_price=100.0,
        reference_candle_at=trigger_candle_close_at,
        volume_ratio=2.0,
        volume_v2_status="OK",
        golden_zone={"direction": "BULLISH"},
    )


def default_candle_fetcher(*, timeframe_plan, observed_at):
    return candles_for(timeframe_plan, observed_at)


def default_oi_fetcher(*, symbol_plan, observed_at, period):
    assert symbol_plan.canonical_symbol
    assert period == "5m"
    return oi_observations(observed_at)


def default_evaluator(
    *,
    plan,
    symbol_plan,
    timeframe_evidence,
    oi_evidence,
    trigger_candle_close_at,
):
    assert plan.mode == symbol_plan.mode
    assert timeframe_evidence
    assert oi_evidence.canonical_symbol == symbol_plan.canonical_symbol
    return payload_for(trigger_candle_close_at)


def execute(
    plan=None,
    *,
    observed_at=OBSERVED_AT,
    candle_fetcher=default_candle_fetcher,
    oi_fetcher=default_oi_fetcher,
    technical_evaluator=default_evaluator,
):
    selected = make_plan() if plan is None else plan
    return execute_mode_scan_plan(
        plan=selected,
        observed_at=observed_at,
        candle_fetcher=candle_fetcher,
        oi_fetcher=oi_fetcher,
        technical_evaluator=technical_evaluator,
    )


def assert_executor_invalid(call):
    with pytest.raises(
        ModeScanExecutorValidationError,
        match="^invalid mode scan executor$",
    ):
        call()


def hostile_copy(value, field_name, replacement):
    object.__setattr__(value, field_name, replacement)
    return value


def test_exact_public_constant_inventory():
    tree = ast.parse(ENGINE_PATH.read_text())
    public_constants = {
        node.target.id
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id.isupper()
        and not node.target.id.startswith("_")
    }
    assert public_constants == {"MODE_SCAN_EXECUTOR_POLICY_VERSION"}
    assert (
        MODE_SCAN_EXECUTOR_POLICY_VERSION
        == "mode-scan-executor-policy-v1"
    )


def test_exact_exception_type_and_sanitized_message():
    with pytest.raises(ModeScanExecutorValidationError) as captured:
        execute(plan=object())
    assert str(captured.value) == "invalid mode scan executor"
    assert isinstance(captured.value, ValueError)


def test_exact_public_function_signature():
    signature = inspect.signature(execute_mode_scan_plan)
    assert tuple(signature.parameters) == (
        "plan",
        "observed_at",
        "candle_fetcher",
        "oi_fetcher",
        "technical_evaluator",
    )
    assert str(signature.return_annotation) == (
        "ModeScanExecutionResultV1"
    )


def test_public_function_parameters_are_keyword_only():
    signature = inspect.signature(execute_mode_scan_plan)
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


def test_public_function_parameters_have_no_defaults():
    signature = inspect.signature(execute_mode_scan_plan)
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_success_returns_exact_result_type():
    assert type(execute()) is ModeScanExecutionResultV1


def test_authorized_engine_import_inventory():
    tree = ast.parse(ENGINE_PATH.read_text())
    project_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("engine.")
    }
    assert project_imports == {
        "engine.mode_fetch_budget_cadence_v1",
        "engine.mode_profile_v1",
        "engine.mode_scan_execution_evidence_v1",
        "engine.mode_scan_execution_plan_v1",
    }


def test_prohibited_engine_imports_are_absent():
    tree = ast.parse(ENGINE_PATH.read_text())
    roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert roots.isdisjoint(
        {
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
            "socket",
            "websocket",
            "ccxt",
            "subprocess",
            "pandas",
            "numpy",
        }
    )


def test_engine_has_no_filesystem_network_cache_runtime_effect():
    tree = ast.parse(ENGINE_PATH.read_text())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imports.isdisjoint(
        {"os", "pathlib", "shutil", "tempfile", "socket"}
    )
    source = ENGINE_PATH.read_text()
    assert "build_mode_owned_cache_key" not in source
    assert "route_mode_scan" not in source
    assert "run_mode_validation_pipeline" not in source


def test_no_additional_public_executor_or_projector():
    assert executor_module.__all__ == (
        "MODE_SCAN_EXECUTOR_POLICY_VERSION",
        "ModeScanExecutorValidationError",
        "execute_mode_scan_plan",
    )
    tree = ast.parse(ENGINE_PATH.read_text())
    public_functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert public_functions == {"execute_mode_scan_plan"}


def test_valid_plan_is_accepted():
    result = execute(make_plan())
    assert result.candidate_count == 1


def test_wrong_plan_type_is_rejected_before_callbacks():
    calls = []
    assert_executor_invalid(
        lambda: execute(
            object(),
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_plan_subclass_is_rejected_before_callbacks():
    original = make_plan()
    values = {
        item.name: getattr(original, item.name)
        for item in fields(ModeScanExecutionPlanV1)
    }
    subclass = PlanSubclass(**values)
    calls = []
    assert_executor_invalid(
        lambda: execute(
            subclass,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_hostile_outer_plan_mutation_is_rejected_before_callbacks():
    plan = hostile_copy(make_plan(), "plan_sha256", "0" * 64)
    calls = []
    assert_executor_invalid(
        lambda: execute(
            plan,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_hostile_nested_symbol_mutation_is_rejected_before_callbacks():
    plan = make_plan()
    hostile_copy(
        plan.full_evaluation_symbols[0],
        "full_evaluation_rank",
        2,
    )
    calls = []
    assert_executor_invalid(
        lambda: execute(
            plan,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_hostile_timeframe_mutation_is_rejected_before_callbacks():
    plan = make_plan()
    hostile_copy(
        plan.full_evaluation_symbols[0].candle_fetches[0],
        "raw_fetch_limit",
        2,
    )
    calls = []
    assert_executor_invalid(
        lambda: execute(
            plan,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_hostile_fetch_budget_mutation_is_rejected_before_callbacks():
    plan = hostile_copy(make_plan(), "fetch_budget_sha256", "0" * 64)
    calls = []
    assert_executor_invalid(
        lambda: execute(
            plan,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_invalid_plan_hash_is_rejected_before_callbacks():
    plan = hostile_copy(make_plan(), "plan_sha256", "f" * 64)
    calls = []
    assert_executor_invalid(
        lambda: execute(
            plan,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_noncanonical_observed_at_is_rejected_before_callbacks():
    calls = []
    assert_executor_invalid(
        lambda: execute(
            observed_at="2026-07-30T06:30:00+00:00",
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_timestamp_subclass_is_rejected_before_callbacks():
    calls = []
    assert_executor_invalid(
        lambda: execute(
            observed_at=TextSubclass(OBSERVED_AT),
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_noncallable_candle_dependency_is_rejected():
    assert_executor_invalid(lambda: execute(candle_fetcher=None))


def test_noncallable_oi_dependency_is_rejected():
    assert_executor_invalid(lambda: execute(oi_fetcher=None))


def test_noncallable_evaluator_is_rejected():
    assert_executor_invalid(lambda: execute(technical_evaluator=None))


def test_missing_trigger_is_rejected_before_callbacks():
    plan = make_plan()
    trigger = next(
        item
        for item in plan.full_evaluation_symbols[0].candle_fetches
        if item.role == "TRIGGER"
    )
    hostile_copy(trigger, "role", "STRUCTURE")
    calls = []
    assert_executor_invalid(
        lambda: execute(
            plan,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_duplicate_trigger_is_rejected_before_callbacks():
    plan = make_plan()
    rows = plan.full_evaluation_symbols[0].candle_fetches
    nontrigger = next(item for item in rows if item.role != "TRIGGER")
    hostile_copy(nontrigger, "role", "TRIGGER")
    calls = []
    assert_executor_invalid(
        lambda: execute(
            plan,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_trigger_profile_mismatch_is_rejected_before_callbacks():
    plan = make_plan()
    trigger = next(
        item
        for item in plan.full_evaluation_symbols[0].candle_fetches
        if item.role == "TRIGGER"
    )
    hostile_copy(trigger, "timeframe", "1d")
    calls = []
    assert_executor_invalid(
        lambda: execute(
            plan,
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_missing_budget_row_is_rejected_before_callbacks(monkeypatch):
    original = ModeScanExecutionPlanV1.fetch_budget_copy

    def missing(self):
        mapping = original(self)
        mapping["timeframe_fetches"].pop()
        return mapping

    monkeypatch.setattr(
        ModeScanExecutionPlanV1,
        "fetch_budget_copy",
        missing,
    )
    calls = []
    assert_executor_invalid(
        lambda: execute(
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_ambiguous_budget_row_is_rejected_before_callbacks(monkeypatch):
    original = ModeScanExecutionPlanV1.fetch_budget_copy

    def duplicated(self):
        mapping = original(self)
        mapping["timeframe_fetches"].append(
            dict(mapping["timeframe_fetches"][0])
        )
        return mapping

    monkeypatch.setattr(
        ModeScanExecutionPlanV1,
        "fetch_budget_copy",
        duplicated,
    )
    calls = []
    assert_executor_invalid(
        lambda: execute(
            candle_fetcher=lambda **kwargs: calls.append(kwargs),
        )
    )
    assert calls == []


def test_swing_success():
    result = execute(make_plan("SWING"))
    assert result.mode == "SWING"
    assert result.candidate_count == 1


def test_intraday_success():
    result = execute(make_plan("INTRADAY"))
    assert result.mode == "INTRADAY"
    assert result.candidate_count == 1


def test_scalp_without_optional_context_success():
    result = execute(make_plan("SCALP", optional=False))
    assert result.mode == "SCALP"
    assert result.candidate_count == 1


def test_scalp_with_optional_context_success():
    result = execute(make_plan("SCALP", optional=True))
    assert result.mode == "SCALP"
    assert result.candidate_count == 1


def test_exact_symbol_order_is_preserved():
    plan = make_plan(count=3)
    result = execute(plan)
    assert result.planned_symbol_order == tuple(
        item.canonical_symbol
        for item in plan.full_evaluation_symbols
    )


def test_exact_timeframe_order_is_preserved():
    plan = make_plan()
    seen = []

    def candle_fetcher(*, timeframe_plan, observed_at):
        seen.append(timeframe_plan.timeframe)
        return candles_for(timeframe_plan, observed_at)

    execute(plan, candle_fetcher=candle_fetcher)
    assert seen == [
        item.timeframe
        for item in plan.full_evaluation_symbols[0].candle_fetches
    ]


def test_candle_callback_keyword_arguments_are_exact():
    captured = []

    def candle_fetcher(**kwargs):
        captured.append(kwargs)
        return candles_for(
            kwargs["timeframe_plan"],
            kwargs["observed_at"],
        )

    execute(candle_fetcher=candle_fetcher)
    assert captured
    assert all(
        set(item) == {"timeframe_plan", "observed_at"}
        for item in captured
    )


def test_oi_callback_keyword_arguments_are_exact():
    captured = []

    def oi_fetcher(**kwargs):
        captured.append(kwargs)
        return oi_observations(kwargs["observed_at"])

    execute(oi_fetcher=oi_fetcher)
    assert len(captured) == 1
    assert set(captured[0]) == {
        "symbol_plan",
        "observed_at",
        "period",
    }
    assert captured[0]["period"] == "5m"


def test_evaluator_keyword_arguments_are_exact():
    captured = []

    def evaluator(**kwargs):
        captured.append(kwargs)
        return payload_for(kwargs["trigger_candle_close_at"])

    execute(technical_evaluator=evaluator)
    assert len(captured) == 1
    assert set(captured[0]) == {
        "plan",
        "symbol_plan",
        "timeframe_evidence",
        "oi_evidence",
        "trigger_candle_close_at",
    }


@pytest.mark.parametrize("mode", ("SWING", "INTRADAY", "SCALP"))
def test_exact_trigger_close_for_every_mode(mode):
    captured = []

    def evaluator(**kwargs):
        captured.append(kwargs)
        return payload_for(kwargs["trigger_candle_close_at"])

    execute(
        make_plan(mode, optional=(mode == "SCALP")),
        technical_evaluator=evaluator,
    )
    evidence = captured[0]["timeframe_evidence"]
    symbol_plan = captured[0]["symbol_plan"]
    expected = next(
        item.closed_candle_close_at
        for row, item in zip(
            symbol_plan.candle_fetches,
            evidence,
            strict=True,
        )
        if row.role == "TRIGGER"
    )
    assert captured[0]["trigger_candle_close_at"] == expected


def test_evaluator_evidence_tuple_order_matches_plan():
    captured = []

    def evaluator(**kwargs):
        captured.append(kwargs)
        return payload_for(kwargs["trigger_candle_close_at"])

    execute(technical_evaluator=evaluator)
    kwargs = captured[0]
    assert type(kwargs["timeframe_evidence"]) is tuple
    assert tuple(
        item.timeframe for item in kwargs["timeframe_evidence"]
    ) == tuple(
        item.timeframe
        for item in kwargs["symbol_plan"].candle_fetches
    )


def test_candidate_id_is_exact():
    result = execute()
    candidate = result.candidates[0]
    expected = build_e2_candidate_id(
        plan_sha256=result.plan_sha256,
        mode=result.mode,
        mode_lineage_sha256=result.mode_lineage_sha256,
        canonical_symbol=candidate.symbol,
        reference_candle_at=candidate.reference_candle_at,
        payload_sha256=candidate.payload_sha256,
    )
    assert candidate.candidate_id == expected


def test_exact_five_key_scanner_row_is_derivable():
    row = execute().candidates[0].to_scanner_row()
    assert tuple(row) == (
        "candidate_id",
        "mode",
        "symbol",
        "mode_lineage_sha256",
        "payload",
    )


def test_executor_returns_result_only():
    result = execute()
    assert type(result) is ModeScanExecutionResultV1
    assert not isinstance(result, tuple)


def test_deterministic_replay_and_execution_hash():
    first = execute()
    second = execute()
    assert first.to_mapping() == second.to_mapping()
    assert first.execution_sha256 == second.execution_sha256


def test_multiple_candidates_retain_plan_order():
    plan = make_plan(count=3)
    result = execute(plan)
    assert tuple(item.symbol for item in result.candidates) == tuple(
        item.canonical_symbol
        for item in plan.full_evaluation_symbols
    )


def test_candle_callback_exception_maps_to_skipped():
    def candle_fetcher(**kwargs):
        raise RuntimeError("provider secret")

    result = execute(candle_fetcher=candle_fetcher)
    outcome = result.outcomes[0]
    assert outcome.outcome_kind == OUTCOME_SKIPPED
    assert outcome.reason_code == REASON_CANDLE_BOUNDARY_EXCEPTION


def test_candle_exception_text_is_not_retained():
    def candle_fetcher(**kwargs):
        raise RuntimeError("provider-secret-value")

    result = execute(candle_fetcher=candle_fetcher)
    assert "provider-secret-value" not in repr(result.to_mapping())


def test_candle_list_output_is_rejected():
    def candle_fetcher(*, timeframe_plan, observed_at):
        return list(candles_for(timeframe_plan, observed_at))

    result = execute(candle_fetcher=candle_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_candle_tuple_subclass_output_is_rejected():
    def candle_fetcher(*, timeframe_plan, observed_at):
        return TupleSubclass(
            candles_for(timeframe_plan, observed_at)
        )

    result = execute(candle_fetcher=candle_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_candle_mapping_output_is_rejected():
    result = execute(candle_fetcher=lambda **kwargs: {})
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_candle_generator_output_is_rejected():
    def candle_fetcher(*, timeframe_plan, observed_at):
        return (
            item
            for item in candles_for(timeframe_plan, observed_at)
        )

    result = execute(candle_fetcher=candle_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_wrong_candle_item_is_rejected():
    result = execute(candle_fetcher=lambda **kwargs: (object(),))
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_hostile_candle_object_is_rejected():
    def candle_fetcher(*, timeframe_plan, observed_at):
        rows = candles_for(timeframe_plan, observed_at)
        hostile_copy(rows[0], "close_time", rows[0].open_time)
        return rows

    result = execute(candle_fetcher=candle_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_insufficient_candle_rows_are_rejected():
    def candle_fetcher(*, timeframe_plan, observed_at):
        return candles_for(timeframe_plan, observed_at)[:-1]

    result = execute(candle_fetcher=candle_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_candle_discontinuity_is_rejected():
    def candle_fetcher(*, timeframe_plan, observed_at):
        rows = list(candles_for(timeframe_plan, observed_at))
        rows[1] = replace(
            rows[1],
            open_time=rows[2].open_time,
            close_time=rows[2].close_time,
        )
        return tuple(rows)

    result = execute(candle_fetcher=candle_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_duplicate_candle_timestamp_is_rejected():
    def candle_fetcher(*, timeframe_plan, observed_at):
        rows = list(candles_for(timeframe_plan, observed_at))
        rows[1] = rows[0]
        return tuple(rows)

    result = execute(candle_fetcher=candle_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_developing_window_failure_is_rejected():
    future = "2026-08-06T06:30:00Z"

    def candle_fetcher(*, timeframe_plan, observed_at):
        return candles_for(timeframe_plan, future)

    result = execute(candle_fetcher=candle_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_partial_timeframe_hashes_are_preserved():
    count = 0

    def candle_fetcher(*, timeframe_plan, observed_at):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError
        return candles_for(timeframe_plan, observed_at)

    result = execute(candle_fetcher=candle_fetcher)
    assert len(
        result.outcomes[0].timeframe_evidence_sha256s
    ) == 1


def test_later_candles_are_not_invoked_after_failure():
    calls = 0

    def candle_fetcher(**kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError

    result = execute(candle_fetcher=candle_fetcher)
    assert calls == 1
    assert result.actual_candle_call_count == 1


def test_oi_and_evaluator_not_invoked_after_candle_failure():
    oi_calls = []
    evaluator_calls = []
    result = execute(
        candle_fetcher=lambda **kwargs: (),
        oi_fetcher=lambda **kwargs: oi_calls.append(kwargs),
        technical_evaluator=lambda **kwargs: evaluator_calls.append(
            kwargs
        ),
    )
    assert result.actual_oi_call_count == 0
    assert oi_calls == []
    assert evaluator_calls == []


def test_next_symbol_continues_after_candle_failure():
    plan = make_plan(count=2)
    failed_symbol = plan.full_evaluation_symbols[0].canonical_symbol

    def candle_fetcher(*, timeframe_plan, observed_at):
        if timeframe_plan.canonical_symbol == failed_symbol:
            raise RuntimeError
        return candles_for(timeframe_plan, observed_at)

    result = execute(plan, candle_fetcher=candle_fetcher)
    assert tuple(item.outcome_kind for item in result.outcomes) == (
        OUTCOME_SKIPPED,
        OUTCOME_CANDIDATE,
    )


def test_oi_callback_exception_maps_to_skipped():
    def oi_fetcher(**kwargs):
        raise RuntimeError

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_BOUNDARY_EXCEPTION
    )


def test_oi_list_output_is_rejected():
    def oi_fetcher(**kwargs):
        return list(oi_observations(kwargs["observed_at"]))

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_oi_tuple_subclass_output_is_rejected():
    def oi_fetcher(**kwargs):
        return TupleSubclass(
            oi_observations(kwargs["observed_at"])
        )

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_oi_mapping_output_is_rejected():
    result = execute(oi_fetcher=lambda **kwargs: {})
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_wrong_oi_observation_item_is_rejected():
    result = execute(oi_fetcher=lambda **kwargs: (object(),))
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_hostile_oi_observation_is_rejected():
    def oi_fetcher(**kwargs):
        rows = oi_observations(kwargs["observed_at"])
        hostile_copy(rows[0], "open_interest", -1)
        return rows

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_too_few_oi_observations_are_rejected():
    def oi_fetcher(**kwargs):
        return oi_observations(kwargs["observed_at"])[:1]

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_oi_gap_is_rejected():
    def oi_fetcher(**kwargs):
        rows = oi_observations(kwargs["observed_at"])
        return (rows[0], rows[2])

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_duplicate_oi_timestamp_is_rejected():
    def oi_fetcher(**kwargs):
        rows = oi_observations(kwargs["observed_at"])
        return (rows[0], rows[0], rows[2])

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_future_oi_evidence_is_rejected():
    def oi_fetcher(**kwargs):
        return oi_observations(
            kwargs["observed_at"],
            newest_offset_minutes=5,
        )

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_stale_oi_evidence_is_rejected():
    def oi_fetcher(**kwargs):
        return oi_observations(
            kwargs["observed_at"],
            newest_offset_minutes=-10,
        )

    result = execute(oi_fetcher=oi_fetcher)
    assert (
        result.outcomes[0].reason_code
        == REASON_OI_EVIDENCE_INVALID
    )


def test_evaluator_not_invoked_after_oi_failure():
    calls = []
    result = execute(
        oi_fetcher=lambda **kwargs: (),
        technical_evaluator=lambda **kwargs: calls.append(kwargs),
    )
    assert result.actual_evaluator_invocation_count == 0
    assert calls == []


def test_all_timeframe_hashes_preserved_on_oi_failure():
    plan = make_plan()
    result = execute(plan, oi_fetcher=lambda **kwargs: ())
    assert len(
        result.outcomes[0].timeframe_evidence_sha256s
    ) == len(plan.full_evaluation_symbols[0].candle_fetches)


def test_next_symbol_continues_after_oi_failure():
    plan = make_plan(count=2)
    failed_symbol = plan.full_evaluation_symbols[0].canonical_symbol

    def oi_fetcher(*, symbol_plan, observed_at, period):
        if symbol_plan.canonical_symbol == failed_symbol:
            raise RuntimeError
        return oi_observations(observed_at)

    result = execute(plan, oi_fetcher=oi_fetcher)
    assert tuple(item.outcome_kind for item in result.outcomes) == (
        OUTCOME_SKIPPED,
        OUTCOME_CANDIDATE,
    )


def test_evaluator_exception_maps_to_skipped():
    def evaluator(**kwargs):
        raise RuntimeError

    result = execute(technical_evaluator=evaluator)
    assert (
        result.outcomes[0].reason_code
        == REASON_EVALUATOR_EXCEPTION
    )


def test_evaluator_exception_text_is_not_retained():
    def evaluator(**kwargs):
        raise RuntimeError("evaluator-secret-value")

    result = execute(technical_evaluator=evaluator)
    assert "evaluator-secret-value" not in repr(result.to_mapping())


def test_none_gives_exact_no_candidate():
    result = execute(technical_evaluator=lambda **kwargs: None)
    outcome = result.outcomes[0]
    assert outcome.outcome_kind == OUTCOME_NO_CANDIDATE
    assert outcome.reason_code == REASON_NO_CANDIDATE


def test_evaluator_mapping_output_is_rejected():
    result = execute(technical_evaluator=lambda **kwargs: {})
    assert (
        result.outcomes[0].reason_code
        == REASON_EVALUATOR_RESULT_INVALID
    )


def test_evaluator_tagged_object_is_rejected():
    result = execute(
        technical_evaluator=lambda **kwargs: TaggedResult()
    )
    assert (
        result.outcomes[0].reason_code
        == REASON_EVALUATOR_RESULT_INVALID
    )


def test_payload_subclass_is_rejected():
    def evaluator(**kwargs):
        payload = payload_for(kwargs["trigger_candle_close_at"])
        return PayloadSubclass(**payload.to_mapping())

    result = execute(technical_evaluator=evaluator)
    assert (
        result.outcomes[0].reason_code
        == REASON_EVALUATOR_RESULT_INVALID
    )


def test_hostile_payload_is_rejected():
    def evaluator(**kwargs):
        payload = payload_for(kwargs["trigger_candle_close_at"])
        return hostile_copy(payload, "payload_sha256", "0" * 64)

    result = execute(technical_evaluator=evaluator)
    assert (
        result.outcomes[0].reason_code
        == REASON_EVALUATOR_RESULT_INVALID
    )


def test_payload_trigger_close_mismatch_is_rejected():
    def evaluator(**kwargs):
        payload = payload_for(kwargs["trigger_candle_close_at"])
        return hostile_copy(
            payload,
            "trigger_candle_close_at",
            "2026-07-30T06:35:00Z",
        )

    result = execute(technical_evaluator=evaluator)
    assert (
        result.outcomes[0].reason_code
        == REASON_EVALUATOR_RESULT_INVALID
    )


def test_reference_candle_mismatch_is_rejected():
    def evaluator(**kwargs):
        payload = payload_for(kwargs["trigger_candle_close_at"])
        decoded = payload.payload_copy()
        decoded["reference_candle_at"] = "2026-07-30T06:35:00Z"
        encoded = json.dumps(
            decoded,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        hostile_copy(payload, "payload_json", encoded)
        hostile_copy(
            payload,
            "payload_sha256",
            hashlib.sha256(encoded.encode()).hexdigest(),
        )
        return payload

    result = execute(technical_evaluator=evaluator)
    assert (
        result.outcomes[0].reason_code
        == REASON_EVALUATOR_RESULT_INVALID
    )


def test_evaluator_identity_injection_is_rejected():
    def evaluator(**kwargs):
        payload = payload_for(kwargs["trigger_candle_close_at"])
        decoded = payload.payload_copy()
        decoded["mode"] = kwargs["plan"].mode
        encoded = json.dumps(
            decoded,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        hostile_copy(payload, "payload_json", encoded)
        hostile_copy(
            payload,
            "payload_sha256",
            hashlib.sha256(encoded.encode()).hexdigest(),
        )
        return payload

    result = execute(technical_evaluator=evaluator)
    assert (
        result.outcomes[0].reason_code
        == REASON_EVALUATOR_RESULT_INVALID
    )


def test_evaluator_failure_preserves_candle_and_oi_evidence():
    result = execute(technical_evaluator=lambda **kwargs: object())
    outcome = result.outcomes[0]
    assert outcome.timeframe_evidence_sha256s
    assert outcome.oi_evidence_sha256 is not None
    assert outcome.evaluator_payload_sha256 is None


def test_next_symbol_continues_after_evaluator_failure():
    plan = make_plan(count=2)
    failed_symbol = plan.full_evaluation_symbols[0].canonical_symbol

    def evaluator(**kwargs):
        if kwargs["symbol_plan"].canonical_symbol == failed_symbol:
            raise RuntimeError
        return payload_for(kwargs["trigger_candle_close_at"])

    result = execute(plan, technical_evaluator=evaluator)
    assert tuple(item.outcome_kind for item in result.outcomes) == (
        OUTCOME_SKIPPED,
        OUTCOME_CANDIDATE,
    )


def test_candidate_row_construction_failure_aborts(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("candidate internal")

    monkeypatch.setattr(
        executor_module,
        "build_mode_execution_candidate_row",
        fail,
    )
    assert_executor_invalid(execute)


def test_duplicate_candidate_id_aborts(monkeypatch):
    plan = make_plan(count=2)
    original = executor_module.build_mode_execution_candidate_row
    first = None

    def duplicate(**kwargs):
        nonlocal first
        candidate = original(**kwargs)
        if first is None:
            first = candidate
            return candidate
        return first

    monkeypatch.setattr(
        executor_module,
        "build_mode_execution_candidate_row",
        duplicate,
    )
    assert_executor_invalid(lambda: execute(plan))


def test_duplicate_candidate_symbol_aborts(monkeypatch):
    plan = make_plan(count=2)
    original = executor_module.build_mode_execution_candidate_row
    first_symbol = None

    def duplicate_symbol(**kwargs):
        nonlocal first_symbol
        candidate = original(**kwargs)
        if first_symbol is None:
            first_symbol = candidate.symbol
        else:
            hostile_copy(candidate, "symbol", first_symbol)
        return candidate

    monkeypatch.setattr(
        executor_module,
        "build_mode_execution_candidate_row",
        duplicate_symbol,
    )
    assert_executor_invalid(lambda: execute(plan))


def test_final_result_invariant_failure_is_sanitized(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("result internal")

    monkeypatch.setattr(
        executor_module,
        "build_mode_scan_execution_result",
        fail,
    )
    assert_executor_invalid(execute)


def test_unexpected_internal_invariant_is_sanitized(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("unexpected internal")

    monkeypatch.setattr(executor_module, "_outcome", fail)
    assert_executor_invalid(
        lambda: execute(candle_fetcher=lambda **kwargs: ())
    )


def test_callback_keyboard_interrupt_is_not_swallowed():
    def candle_fetcher(**kwargs):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        execute(candle_fetcher=candle_fetcher)


def test_callback_system_exit_is_not_swallowed():
    def oi_fetcher(**kwargs):
        raise SystemExit

    with pytest.raises(SystemExit):
        execute(oi_fetcher=oi_fetcher)


def test_candle_count_increments_before_successful_callback():
    result = execute()
    assert result.actual_candle_call_count == (
        result.planned_candle_call_count
    )


def test_candle_exception_still_counts():
    result = execute(
        candle_fetcher=lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError()
        )
    )
    assert result.actual_candle_call_count == 1


def test_candle_malformed_output_still_counts():
    result = execute(candle_fetcher=lambda **kwargs: [])
    assert result.actual_candle_call_count == 1


def test_only_attempted_candle_rows_count_after_fail_fast():
    plan = make_plan()
    result = execute(plan, candle_fetcher=lambda **kwargs: ())
    assert result.actual_candle_call_count == 1
    assert result.actual_candle_call_count < (
        sum(
            len(item.candle_fetches)
            for item in plan.full_evaluation_symbols
        )
    )


def test_oi_count_increments_before_callback():
    result = execute(oi_fetcher=lambda **kwargs: ())
    assert result.actual_oi_call_count == 1


def test_oi_exception_still_counts():
    def oi_fetcher(**kwargs):
        raise RuntimeError

    result = execute(oi_fetcher=oi_fetcher)
    assert result.actual_oi_call_count == 1


def test_evaluator_count_increments_before_callback():
    result = execute(technical_evaluator=lambda **kwargs: None)
    assert result.actual_evaluator_invocation_count == 1


def test_evaluator_exception_still_counts():
    def evaluator(**kwargs):
        raise RuntimeError

    result = execute(technical_evaluator=evaluator)
    assert result.actual_evaluator_invocation_count == 1


def test_actual_request_count_reconciles():
    result = execute()
    assert result.actual_executor_request_count == (
        result.actual_candle_call_count
        + result.actual_oi_call_count
    )


def test_success_consumes_planned_executor_ip_weight():
    result = execute()
    assert (
        result.actual_executor_ip_weight
        == result.planned_executor_ip_weight
    )


def test_failed_candle_attempt_consumes_weight():
    result = execute(candle_fetcher=lambda **kwargs: ())
    assert result.actual_executor_ip_weight > 0


def test_unattempted_rows_consume_zero_weight():
    failed = execute(candle_fetcher=lambda **kwargs: ())
    success = execute()
    assert (
        failed.actual_executor_ip_weight
        < success.actual_executor_ip_weight
    )


def test_oi_attempt_consumes_zero_additional_weight():
    candle_failure = execute(candle_fetcher=lambda **kwargs: ())

    def fail_second_timeframe(*, timeframe_plan, observed_at):
        if timeframe_plan.role == "TRIGGER":
            return ()
        return candles_for(timeframe_plan, observed_at)

    later_failure = execute(candle_fetcher=fail_second_timeframe)
    assert later_failure.actual_executor_ip_weight >= (
        candle_failure.actual_executor_ip_weight
    )


def test_market_level_reservation_is_excluded():
    result = execute()
    plan = make_plan()
    budget = plan.fetch_budget_copy()
    assert result.planned_executor_ip_weight == (
        budget["total_ip_weight"]
        - budget["market_level_ip_weight"]
    )
    assert result.planned_executor_request_count == (
        budget["total_request_count"]
        - budget["market_level_request_count"]
    )


def test_actual_weight_never_exceeds_planned_weight():
    result = execute()
    assert (
        result.actual_executor_ip_weight
        <= result.planned_executor_ip_weight
    )


def test_zero_retry_is_preserved():
    result = execute(
        candle_fetcher=lambda **kwargs: (),
    )
    assert result.retry_count == 0
    assert result.actual_candle_call_count == 1


def test_no_concurrency_construct_exists():
    tree = ast.parse(ENGINE_PATH.read_text())
    forbidden = {
        "AsyncFunctionDef",
        "Await",
        "Yield",
        "YieldFrom",
    }
    assert not {
        type(node).__name__ for node in ast.walk(tree)
    }.intersection(forbidden)
    source = ENGINE_PATH.read_text()
    assert "ThreadPoolExecutor" not in source
    assert "ProcessPoolExecutor" not in source


def test_no_callback_invoked_more_than_once_per_stage():
    plan = make_plan()
    counts = {"candle": 0, "oi": 0, "evaluator": 0}

    def candle_fetcher(*, timeframe_plan, observed_at):
        counts["candle"] += 1
        return candles_for(timeframe_plan, observed_at)

    def oi_fetcher(**kwargs):
        counts["oi"] += 1
        return oi_observations(kwargs["observed_at"])

    def evaluator(**kwargs):
        counts["evaluator"] += 1
        return payload_for(kwargs["trigger_candle_close_at"])

    execute(
        plan,
        candle_fetcher=candle_fetcher,
        oi_fetcher=oi_fetcher,
        technical_evaluator=evaluator,
    )
    assert counts == {
        "candle": len(
            plan.full_evaluation_symbols[0].candle_fetches
        ),
        "oi": 1,
        "evaluator": 1,
    }


def test_no_cache_lookup_write_or_store_surface():
    source = ENGINE_PATH.read_text()
    for forbidden in (
        "cache_lookup",
        "cache_write",
        "cache_store",
        "cache_hit",
        "cache_miss",
        "cache_evict",
    ):
        assert forbidden not in source


def test_no_route_mode_scan_invocation():
    assert "route_mode_scan" not in ENGINE_PATH.read_text()


def test_no_validation_pipeline_invocation():
    assert (
        "run_mode_validation_pipeline"
        not in ENGINE_PATH.read_text()
    )


def test_no_live_price_admission():
    source = ENGINE_PATH.read_text()
    assert "live_price" not in source
    assert "executable_price" not in source


def test_no_production_conversion():
    assert "production" not in ENGINE_PATH.read_text().lower()


def test_no_publication():
    assert "publish" not in ENGINE_PATH.read_text().lower()


def test_no_telegram_surface():
    assert "telegram" not in ENGINE_PATH.read_text().lower()


def test_no_exchange_order_surface():
    source = ENGINE_PATH.read_text().lower()
    assert "exchange" not in source
    assert "create_order" not in source


def test_no_legacy_file_mutation_surface():
    tree = ast.parse(ENGINE_PATH.read_text())
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
        for node in ast.walk(tree)
    )


@pytest.mark.parametrize(
    ("candle_fetcher", "expected_reason"),
    (
        (
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError()),
            REASON_CANDLE_BOUNDARY_EXCEPTION,
        ),
        (lambda **kwargs: (), REASON_CANDLE_EVIDENCE_INVALID),
    ),
)
def test_exact_candle_failure_reason_vocabulary(
    candle_fetcher,
    expected_reason,
):
    result = execute(candle_fetcher=candle_fetcher)
    assert result.outcomes[0].reason_code == expected_reason


@pytest.mark.parametrize(
    ("oi_fetcher", "expected_reason"),
    (
        (
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError()),
            REASON_OI_BOUNDARY_EXCEPTION,
        ),
        (lambda **kwargs: (), REASON_OI_EVIDENCE_INVALID),
    ),
)
def test_exact_oi_failure_reason_vocabulary(
    oi_fetcher,
    expected_reason,
):
    result = execute(oi_fetcher=oi_fetcher)
    assert result.outcomes[0].reason_code == expected_reason


@pytest.mark.parametrize(
    ("evaluator", "expected_reason"),
    (
        (
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError()),
            REASON_EVALUATOR_EXCEPTION,
        ),
        (lambda **kwargs: object(), REASON_EVALUATOR_RESULT_INVALID),
    ),
)
def test_exact_evaluator_failure_reason_vocabulary(
    evaluator,
    expected_reason,
):
    result = execute(technical_evaluator=evaluator)
    assert result.outcomes[0].reason_code == expected_reason


def test_outcome_order_is_exactly_plan_order_after_mixed_results():
    plan = make_plan(count=3)

    def evaluator(**kwargs):
        rank = kwargs["symbol_plan"].full_evaluation_rank
        if rank == 1:
            return None
        if rank == 2:
            raise RuntimeError
        return payload_for(kwargs["trigger_candle_close_at"])

    result = execute(plan, technical_evaluator=evaluator)
    assert tuple(item.canonical_symbol for item in result.outcomes) == (
        result.planned_symbol_order
    )
    assert tuple(item.outcome_kind for item in result.outcomes) == (
        OUTCOME_NO_CANDIDATE,
        OUTCOME_SKIPPED,
        OUTCOME_CANDIDATE,
    )


def test_candidate_order_omits_no_candidate_and_skipped_in_plan_order():
    plan = make_plan(count=3)

    def evaluator(**kwargs):
        rank = kwargs["symbol_plan"].full_evaluation_rank
        if rank == 1:
            return None
        return payload_for(kwargs["trigger_candle_close_at"])

    result = execute(plan, technical_evaluator=evaluator)
    assert tuple(item.symbol for item in result.candidates) == tuple(
        item.canonical_symbol
        for item in plan.full_evaluation_symbols[1:]
    )


def test_exact_one_outcome_per_planned_symbol():
    plan = make_plan(count=3)
    result = execute(plan)
    assert len(result.outcomes) == len(
        plan.full_evaluation_symbols
    )


def test_result_candidate_counts_reconcile():
    plan = make_plan(count=3)

    def evaluator(**kwargs):
        rank = kwargs["symbol_plan"].full_evaluation_rank
        if rank == 1:
            return None
        if rank == 2:
            raise RuntimeError
        return payload_for(kwargs["trigger_candle_close_at"])

    result = execute(plan, technical_evaluator=evaluator)
    assert (
        result.candidate_count
        + result.no_candidate_count
        + result.skipped_count
        == len(result.outcomes)
    )


def test_plan_passed_to_evaluator_is_reconstructed():
    original = make_plan()
    captured = []

    def evaluator(**kwargs):
        captured.append(kwargs["plan"])
        return payload_for(kwargs["trigger_candle_close_at"])

    execute(original, technical_evaluator=evaluator)
    assert captured[0] is not original
    assert captured[0].to_mapping() == original.to_mapping()


def test_symbol_plan_passed_to_oi_is_reconstructed():
    original = make_plan()
    captured = []

    def oi_fetcher(**kwargs):
        captured.append(kwargs["symbol_plan"])
        return oi_observations(kwargs["observed_at"])

    execute(original, oi_fetcher=oi_fetcher)
    assert (
        captured[0]
        is not original.full_evaluation_symbols[0]
    )
    assert (
        captured[0].to_mapping()
        == original.full_evaluation_symbols[0].to_mapping()
    )


def test_timeframe_plan_passed_to_candle_is_reconstructed():
    original = make_plan()
    captured = []

    def candle_fetcher(**kwargs):
        captured.append(kwargs["timeframe_plan"])
        return candles_for(
            kwargs["timeframe_plan"],
            kwargs["observed_at"],
        )

    execute(original, candle_fetcher=candle_fetcher)
    assert (
        captured[0]
        is not original.full_evaluation_symbols[0].candle_fetches[0]
    )


def test_callback_outputs_must_be_exact_immutable_objects():
    result = execute(
        candle_fetcher=lambda **kwargs: (
            {"timeframe": kwargs["timeframe_plan"].timeframe},
        )
    )
    assert (
        result.outcomes[0].reason_code
        == REASON_CANDLE_EVIDENCE_INVALID
    )


def test_result_mapping_is_detached():
    result = execute()
    mapping = result.to_mapping()
    mapping["candidates"][0]["candidate_id"] = "changed"
    assert result.candidates[0].candidate_id != "changed"


def test_executor_has_no_module_global_mutable_execution_state():
    tree = ast.parse(ENGINE_PATH.read_text())
    mutable_assignments = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if isinstance(value, (ast.List, ast.Dict, ast.Set)):
                mutable_assignments.append(node)
    assert mutable_assignments == []


def test_top_level_test_inventory_meets_minimum():
    tree = ast.parse(TEST_PATH.read_text())
    tests = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    assert len(tests) >= 75


def test_no_skip_or_xfail_markers():
    tree = ast.parse(TEST_PATH.read_text())
    attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    assert "skip" not in attributes
    assert "skipif" not in attributes
    assert "xfail" not in attributes
