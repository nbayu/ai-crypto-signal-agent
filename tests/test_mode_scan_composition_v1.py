"""Focused tests for detached mode-scan composition."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from pathlib import Path
import typing

import pytest

import engine.mode_scan_composition_v1 as composition_module
from engine.mode_profile_v1 import all_mode_profiles
from engine.mode_router_v1 import (
    ModeRouteResultV1,
    ModeRoutedCandidateV1,
    ModeScanRequestV1,
    build_mode_scan_request,
    route_mode_scan as committed_route_mode_scan,
)
from engine.mode_scan_execution_evidence_v1 import (
    MODE_OI_OBSERVATION_SCHEMA_VERSION,
    MODE_UTC_CANDLE_SCHEMA_VERSION,
    OUTCOME_CANDIDATE,
    OUTCOME_NO_CANDIDATE,
    OUTCOME_SKIPPED,
    ModeOiObservationV1,
    ModeScanExecutionResultV1,
    ModeUtcCandleV1,
    build_mode_technical_evaluator_payload,
)
from engine.mode_scan_execution_plan_v1 import (
    MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
    ModeMarketSnapshotEntryV1,
    ModeScanExecutionPlanV1,
    build_mode_scan_execution_plan as committed_plan_builder,
)
from engine.mode_scan_executor_v1 import (
    execute_mode_scan_plan as committed_executor,
)
from engine.mode_validation_pipeline_adapter_v1 import (
    ModeValidatedCandidateV1,
    ModeValidationPipelineResultV1,
    run_mode_validation_pipeline as committed_validation_adapter,
)
from engine.mode_scan_composition_v1 import (
    MODE_SCAN_COMPOSITION_POLICY_VERSION,
    MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION,
    ModeScanCompositionResultV1,
    ModeScanCompositionValidationError,
    compose_mode_scan_pipeline,
)


ENGINE_PATH = Path("engine/mode_scan_composition_v1.py")
TEST_PATH = Path("tests/test_mode_scan_composition_v1.py")
OBSERVED_AT = "2026-07-30T06:30:00Z"
MODES = tuple(profile.mode for profile in all_mode_profiles())
TIMEFRAME_SECONDS = {
    "1w": 604800,
    "1d": 86400,
    "4h": 14400,
    "1h": 3600,
    "15m": 900,
    "5m": 300,
    "3m": 180,
}
RESULT_FIELDS = (
    "schema_version",
    "policy_version",
    "mode",
    "due_window_id",
    "mode_lineage_sha256",
    "observed_at",
    "include_optional_context",
    "execution_plan",
    "execution_result",
    "route_result",
    "validation_result",
    "composition_sha256",
)
SCANNER_ROW_KEYS = (
    "candidate_id",
    "mode",
    "symbol",
    "mode_lineage_sha256",
    "payload",
)


class TextSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class CustomSequence:
    def __iter__(self):
        return iter(())


class SnapshotSubclass(ModeMarketSnapshotEntryV1):
    pass


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def digest_mapping(value):
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def market(
    symbol="BTC/USDT:USDT",
    volume=1000.0,
    **changes,
):
    values = {
        "schema_version":
            MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
        "canonical_symbol": symbol,
        "quote_asset": "USDT",
        "settle_asset": "USDT",
        "market_kind": "swap",
        "active": True,
        "linear": True,
        "perpetual": True,
        "quote_volume_24h": volume,
    }
    values.update(changes)
    return ModeMarketSnapshotEntryV1(**values)


def markets(count=1):
    return tuple(
        market(
            symbol=f"S{index:03d}/USDT:USDT",
            volume=1000.0 - index,
        )
        for index in range(count)
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


def make_candle(timeframe, opened, index):
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


def candles_for(timeframe_plan, observed_at):
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


def oi_observations(observed_at):
    observed = datetime.strptime(
        observed_at,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    return tuple(
        ModeOiObservationV1(
            schema_version=MODE_OI_OBSERVATION_SCHEMA_VERSION,
            close_time=utc_text(
                observed - timedelta(minutes=5 * (2 - index))
            ),
            open_interest=1000.0 + index,
        )
        for index in range(3)
    )


def evaluator_payload(trigger_candle_close_at, *, score=91):
    return build_mode_technical_evaluator_payload(
        trigger_candle_close_at=trigger_candle_close_at,
        score=score,
        trend="UPTREND",
        bos=True,
        choch=False,
        reference_price=100.0,
        reference_candle_at=trigger_candle_close_at,
        volume_ratio=2.0,
        volume_v2_status="OK",
        golden_zone={"direction": "BULLISH"},
    )


def dependency_set(
    *,
    evaluator_kind="candidate",
    candle_kind="valid",
    score=91,
    counts=None,
):
    state = (
        {
            "candle": 0,
            "oi": 0,
            "evaluator": 0,
            "pipeline": 0,
        }
        if counts is None
        else counts
    )

    def candle_fetcher(*, timeframe_plan, observed_at):
        state["candle"] += 1
        if candle_kind == "exception":
            raise ValueError("private candle detail")
        return candles_for(timeframe_plan, observed_at)

    def oi_fetcher(*, symbol_plan, observed_at, period):
        state["oi"] += 1
        if period != "5m" or not symbol_plan.canonical_symbol:
            raise ValueError("fixture invariant")
        return oi_observations(observed_at)

    def technical_evaluator(
        *,
        plan,
        symbol_plan,
        timeframe_evidence,
        oi_evidence,
        trigger_candle_close_at,
    ):
        state["evaluator"] += 1
        if (
            plan.mode != symbol_plan.mode
            or not timeframe_evidence
            or oi_evidence.canonical_symbol
            != symbol_plan.canonical_symbol
        ):
            raise ValueError("fixture invariant")
        if evaluator_kind == "none":
            return None
        if evaluator_kind == "exception":
            raise ValueError("private evaluator detail")
        return evaluator_payload(
            trigger_candle_close_at,
            score=score,
        )

    def pipeline(rows):
        state["pipeline"] += 1
        controlled = [dict(row) for row in rows[:10]]
        final = [dict(row) for row in controlled[:5]]
        return {
            "controlled_top10": controlled,
            "final_top5": final,
            "usage": {"fixture": True, "row_count": len(rows)},
        }

    return (
        candle_fetcher,
        oi_fetcher,
        technical_evaluator,
        pipeline,
        state,
    )


def call_composition(
    *,
    mode="SWING",
    due_window_id=None,
    market_snapshot=None,
    include_optional_context=False,
    observed_at=OBSERVED_AT,
    candle_fetcher=None,
    oi_fetcher=None,
    technical_evaluator=None,
    pipeline=None,
    evaluator_kind="candidate",
    candle_kind="valid",
    score=91,
    counts=None,
):
    (
        default_candle,
        default_oi,
        default_evaluator,
        default_pipeline,
        state,
    ) = dependency_set(
        evaluator_kind=evaluator_kind,
        candle_kind=candle_kind,
        score=score,
        counts=counts,
    )
    result = compose_mode_scan_pipeline(
        mode=mode,
        due_window_id=(
            f"window-{mode.lower()}"
            if due_window_id is None
            else due_window_id
        ),
        market_snapshot=(
            markets()
            if market_snapshot is None
            else market_snapshot
        ),
        include_optional_context=include_optional_context,
        observed_at=observed_at,
        candle_fetcher=(
            default_candle
            if candle_fetcher is None
            else candle_fetcher
        ),
        oi_fetcher=(
            default_oi
            if oi_fetcher is None
            else oi_fetcher
        ),
        technical_evaluator=(
            default_evaluator
            if technical_evaluator is None
            else technical_evaluator
        ),
        pipeline=(
            default_pipeline if pipeline is None else pipeline
        ),
    )
    return result, state


def valid_arguments():
    candle, oi, evaluator, pipeline, state = dependency_set()
    return {
        "mode": "SWING",
        "due_window_id": "window-swing",
        "market_snapshot": markets(),
        "include_optional_context": False,
        "observed_at": OBSERVED_AT,
        "candle_fetcher": candle,
        "oi_fetcher": oi,
        "technical_evaluator": evaluator,
        "pipeline": pipeline,
    }, state


def assert_invalid(call):
    with pytest.raises(
        ModeScanCompositionValidationError,
        match=r"^invalid mode scan composition$",
    ):
        call()


def assert_upfront_invalid(monkeypatch, **changes):
    arguments, state = valid_arguments()
    arguments.update(changes)
    route_calls = {"count": 0}

    def forbidden_route(**_kwargs):
        route_calls["count"] += 1
        raise AssertionError("route must not run")

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        forbidden_route,
    )
    assert_invalid(
        lambda: compose_mode_scan_pipeline(**arguments)
    )
    assert route_calls["count"] == 0
    assert state == {
        "candle": 0,
        "oi": 0,
        "evaluator": 0,
        "pipeline": 0,
    }


def hostile_copy(value, field_name, replacement):
    object.__setattr__(value, field_name, replacement)
    return value


def result_values(value, **changes):
    values = {
        field.name: getattr(value, field.name)
        for field in fields(ModeScanCompositionResultV1)
    }
    values.update(changes)
    return values


def route_capture_wrapper(captured):
    def wrapper(*, mode, due_window_id, scanner):
        captured["mode"] = mode
        captured["due_window_id"] = due_window_id
        captured["scanner"] = scanner

        def intercept(*, request):
            captured["request"] = request
            rows = scanner(request=request)
            captured["rows"] = rows
            return rows

        return committed_route_mode_scan(
            mode=mode,
            due_window_id=due_window_id,
            scanner=intercept,
        )

    return wrapper


def validation_mutator(monkeypatch, mutation, *, count=1):
    def wrapper(*, route_result, pipeline):
        value = committed_validation_adapter(
            route_result=route_result,
            pipeline=pipeline,
        )
        mutation(value)
        return value

    monkeypatch.setattr(
        composition_module,
        "run_mode_validation_pipeline",
        wrapper,
    )
    return lambda: call_composition(
        market_snapshot=markets(count)
    )


def route_mutator(monkeypatch, mutation, *, count=1):
    def wrapper(*, mode, due_window_id, scanner):
        value = committed_route_mode_scan(
            mode=mode,
            due_window_id=due_window_id,
            scanner=scanner,
        )
        mutation(value)
        return value

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        wrapper,
    )
    return lambda: call_composition(
        market_snapshot=markets(count)
    )


def test_public_constant_names_are_exact():
    constants = {
        node.target.id
        for node in ast.parse(ENGINE_PATH.read_text()).body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id.isupper()
        and not node.target.id.startswith("_")
    }
    assert constants == {
        "MODE_SCAN_COMPOSITION_POLICY_VERSION",
        "MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION",
    }


def test_policy_constant_value_is_exact():
    assert (
        MODE_SCAN_COMPOSITION_POLICY_VERSION
        == "mode-scan-composition-policy-v1"
    )


def test_result_schema_constant_value_is_exact():
    assert (
        MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION
        == "mode-scan-composition-result-v1"
    )


def test_public_exception_is_exact_value_error_subclass():
    assert ModeScanCompositionValidationError.__bases__ == (
        ValueError,
    )


def test_exception_message_is_exact_and_sanitized():
    assert_invalid(
        lambda: compose_mode_scan_pipeline(
            **{**valid_arguments()[0], "mode": "BAD"}
        )
    )


def test_result_field_order_is_exact():
    assert tuple(
        field.name
        for field in fields(ModeScanCompositionResultV1)
    ) == RESULT_FIELDS


def test_result_field_types_are_exact():
    hints = typing.get_type_hints(
        ModeScanCompositionResultV1
    )
    assert tuple(hints) == RESULT_FIELDS
    assert hints["execution_plan"] is ModeScanExecutionPlanV1
    assert (
        hints["execution_result"]
        is ModeScanExecutionResultV1
    )
    assert hints["route_result"] is ModeRouteResultV1
    assert (
        hints["validation_result"]
        is ModeValidationPipelineResultV1
    )


def test_result_dataclass_is_frozen():
    result, _state = call_composition()
    with pytest.raises(FrozenInstanceError):
        result.mode = "SCALP"


def test_result_dataclass_is_slotted():
    result, _state = call_composition()
    assert not hasattr(result, "__dict__")
    assert ModeScanCompositionResultV1.__slots__ == RESULT_FIELDS


def test_result_has_exact_one_public_method():
    methods = {
        name
        for name, value in vars(
            ModeScanCompositionResultV1
        ).items()
        if callable(value) and not name.startswith("_")
    }
    assert methods == {"to_mapping"}


def test_to_mapping_key_order_is_exact():
    result, _state = call_composition()
    assert tuple(result.to_mapping()) == RESULT_FIELDS


def test_composition_function_parameter_names_are_exact():
    signature = inspect.signature(
        compose_mode_scan_pipeline
    )
    assert tuple(signature.parameters) == (
        "mode",
        "due_window_id",
        "market_snapshot",
        "include_optional_context",
        "observed_at",
        "candle_fetcher",
        "oi_fetcher",
        "technical_evaluator",
        "pipeline",
    )


def test_composition_function_parameters_are_keyword_only():
    signature = inspect.signature(
        compose_mode_scan_pipeline
    )
    assert all(
        parameter.kind
        is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


def test_composition_function_parameters_have_no_defaults():
    signature = inspect.signature(
        compose_mode_scan_pipeline
    )
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_composition_function_return_annotation_is_exact():
    hints = typing.get_type_hints(
        compose_mode_scan_pipeline
    )
    assert (
        hints["return"] is ModeScanCompositionResultV1
    )


def test_public_export_inventory_is_exact():
    assert composition_module.__all__ == (
        "MODE_SCAN_COMPOSITION_POLICY_VERSION",
        "MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION",
        "ModeScanCompositionValidationError",
        "ModeScanCompositionResultV1",
        "compose_mode_scan_pipeline",
    )


def test_no_additional_public_definition_exists():
    tree = ast.parse(ENGINE_PATH.read_text())
    definitions = {
        node.name
        for node in tree.body
        if isinstance(
            node,
            (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and not node.name.startswith("_")
    }
    assert definitions == {
        "ModeScanCompositionValidationError",
        "ModeScanCompositionResultV1",
        "compose_mode_scan_pipeline",
    }


def test_authorized_project_import_inventory_is_exact():
    tree = ast.parse(ENGINE_PATH.read_text())
    imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("engine.")
    }
    assert imports == {
        "engine.mode_profile_v1",
        "engine.mode_router_v1",
        "engine.mode_scan_execution_plan_v1",
        "engine.mode_scan_execution_evidence_v1",
        "engine.mode_scan_executor_v1",
        "engine.mode_validation_pipeline_adapter_v1",
    }


def test_prohibited_import_inventory_is_absent():
    source = ENGINE_PATH.read_text()
    prohibited = (
        "requests",
        "httpx",
        "aiohttp",
        "urllib",
        "socket",
        "websocket",
        "ccxt",
        "subprocess",
        "validated_pipeline_v4",
        "master_engine_v4",
    )
    assert not any(
        token in source for token in prohibited
    )


def test_module_has_no_public_builder_projector_or_factory():
    assert not any(
        name.startswith(("build_", "project_", "make_"))
        for name in composition_module.__all__
    )


def test_wrong_mode_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(monkeypatch, mode="BAD")


def test_mode_text_subclass_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        mode=TextSubclass("SWING"),
    )


def test_empty_due_window_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(monkeypatch, due_window_id="")


def test_whitespace_due_window_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        due_window_id="window bad",
    )


def test_slash_due_window_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        due_window_id="window/bad",
    )


def test_long_due_window_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        due_window_id="x" * 129,
    )


def test_due_window_subclass_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        due_window_id=TextSubclass("window-swing"),
    )


def test_snapshot_list_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=list(markets()),
    )


def test_snapshot_tuple_subclass_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=TupleSubclass(markets()),
    )


def test_empty_snapshot_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(),
    )


def test_snapshot_row_subclass_is_upfront_zero_effect(
    monkeypatch,
):
    row = SnapshotSubclass(**market().to_mapping())
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(row,),
    )


def test_snapshot_mapping_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot={"row": market()},
    )


def test_snapshot_generator_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(item for item in markets()),
    )


def test_snapshot_custom_sequence_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=CustomSequence(),
    )


def test_wrong_snapshot_row_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(object(),),
    )


def test_hostile_snapshot_row_is_upfront_zero_effect(monkeypatch):
    row = hostile_copy(market(), "active", "yes")
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(row,),
    )


def test_inactive_only_snapshot_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(market(active=False),),
    )


def test_wrong_quote_only_snapshot_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(market(quote_asset="USD"),),
    )


def test_wrong_settle_only_snapshot_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(market(settle_asset="USD"),),
    )


def test_wrong_market_kind_snapshot_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(market(market_kind="future"),),
    )


def test_nonlinear_snapshot_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(market(linear=False),),
    )


def test_nonperpetual_snapshot_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(market(perpetual=False),),
    )


def test_optional_context_int_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        include_optional_context=1,
    )


def test_swing_optional_true_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        include_optional_context=True,
    )


def test_intraday_optional_true_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        mode="INTRADAY",
        due_window_id="window-intraday",
        include_optional_context=True,
    )


def test_observed_at_offset_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        observed_at="2026-07-30T06:30:00+00:00",
    )


def test_observed_at_fraction_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        observed_at="2026-07-30T06:30:00.0Z",
    )


def test_observed_at_whitespace_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        observed_at=" 2026-07-30T06:30:00Z",
    )


def test_observed_at_invalid_calendar_is_upfront_zero_effect(
    monkeypatch,
):
    assert_upfront_invalid(
        monkeypatch,
        observed_at="2026-02-30T06:30:00Z",
    )


def test_observed_at_subclass_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        observed_at=TextSubclass(OBSERVED_AT),
    )


def test_noncallable_candle_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        candle_fetcher=None,
    )


def test_noncallable_oi_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(monkeypatch, oi_fetcher=None)


def test_noncallable_evaluator_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        technical_evaluator=None,
    )


def test_noncallable_pipeline_is_upfront_zero_effect(monkeypatch):
    assert_upfront_invalid(monkeypatch, pipeline=None)


def test_every_upfront_dependency_remains_uninvoked(monkeypatch):
    assert_upfront_invalid(
        monkeypatch,
        market_snapshot=(),
    )


def test_build_mode_scan_request_has_zero_direct_calls():
    tree = ast.parse(ENGINE_PATH.read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_mode_scan_request"
    ]
    assert calls == []


def test_route_mode_scan_is_called_exactly_once(monkeypatch):
    calls = {"count": 0}

    def wrapper(*, mode, due_window_id, scanner):
        calls["count"] += 1
        return committed_route_mode_scan(
            mode=mode,
            due_window_id=due_window_id,
            scanner=scanner,
        )

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        wrapper,
    )
    call_composition()
    assert calls["count"] == 1


def test_route_mode_scan_keyword_arguments_are_exact(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    call_composition()
    assert captured["mode"] == "SWING"
    assert captured["due_window_id"] == "window-swing"
    assert callable(captured["scanner"])


def test_private_scanner_signature_is_exact(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    call_composition()
    signature = inspect.signature(captured["scanner"])
    assert tuple(signature.parameters) == ("request",)
    parameter = signature.parameters["request"]
    assert (
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
    )


def test_private_scanner_receives_router_created_request(
    monkeypatch,
):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    call_composition()
    assert type(captured["request"]) is ModeScanRequestV1
    assert captured["request"].mode == "SWING"


def test_private_scanner_rejects_request_mode_mismatch(
    monkeypatch,
):
    def wrapper(*, mode, due_window_id, scanner):
        request = build_mode_scan_request(
            mode="SCALP",
            due_window_id=due_window_id,
        )
        return scanner(request=request)

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        wrapper,
    )
    assert_invalid(lambda: call_composition())


def test_private_scanner_rejects_request_due_window_mismatch(
    monkeypatch,
):
    def wrapper(*, mode, due_window_id, scanner):
        request = build_mode_scan_request(
            mode=mode,
            due_window_id="other-window",
        )
        return scanner(request=request)

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        wrapper,
    )
    assert_invalid(lambda: call_composition())


def test_private_scanner_second_invocation_fails_closed(
    monkeypatch,
):
    def wrapper(*, mode, due_window_id, scanner):
        request = build_mode_scan_request(
            mode=mode,
            due_window_id=due_window_id,
        )
        scanner(request=request)
        return scanner(request=request)

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        wrapper,
    )
    assert_invalid(lambda: call_composition())


def test_private_scanner_state_is_not_retained_across_calls():
    first, _first_state = call_composition()
    second, _second_state = call_composition()
    assert first.to_mapping() == second.to_mapping()


def test_no_module_global_execution_holder_exists():
    forbidden = {
        "scanner_invocation_count",
        "captured_execution_plan",
        "captured_execution_result",
    }
    assert forbidden.isdisjoint(vars(composition_module))


def test_route_exception_is_sanitized(monkeypatch):
    def wrapper(**_kwargs):
        raise ValueError("private route detail")

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        wrapper,
    )
    assert_invalid(lambda: call_composition())


def test_route_keyboard_interrupt_is_not_swallowed(monkeypatch):
    def wrapper(**_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        wrapper,
    )
    with pytest.raises(KeyboardInterrupt):
        call_composition()


def test_route_system_exit_is_not_swallowed(monkeypatch):
    def wrapper(**_kwargs):
        raise SystemExit

    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        wrapper,
    )
    with pytest.raises(SystemExit):
        call_composition()


def test_candle_keyboard_interrupt_is_not_swallowed():
    def callback(**_kwargs):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        call_composition(candle_fetcher=callback)


def test_candle_system_exit_is_not_swallowed():
    def callback(**_kwargs):
        raise SystemExit

    with pytest.raises(SystemExit):
        call_composition(candle_fetcher=callback)


def test_plan_builder_is_called_exactly_once(monkeypatch):
    calls = {"count": 0}

    def wrapper(**kwargs):
        calls["count"] += 1
        return committed_plan_builder(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "build_mode_scan_execution_plan",
        wrapper,
    )
    call_composition()
    assert calls["count"] == 1


def test_plan_builder_keyword_arguments_are_exact(monkeypatch):
    captured = {}

    def wrapper(**kwargs):
        captured.update(kwargs)
        return committed_plan_builder(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "build_mode_scan_execution_plan",
        wrapper,
    )
    call_composition()
    assert tuple(captured) == (
        "request",
        "market_snapshot",
        "include_optional_context",
    )


def test_plan_builder_receives_exact_typed_snapshot(monkeypatch):
    captured = {}

    def wrapper(**kwargs):
        captured["snapshot"] = kwargs["market_snapshot"]
        return committed_plan_builder(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "build_mode_scan_execution_plan",
        wrapper,
    )
    call_composition(market_snapshot=markets(2))
    assert type(captured["snapshot"]) is tuple
    assert all(
        type(item) is ModeMarketSnapshotEntryV1
        for item in captured["snapshot"]
    )


def test_plan_builder_receives_explicit_optional_false(
    monkeypatch,
):
    captured = {}

    def wrapper(**kwargs):
        captured["optional"] = kwargs[
            "include_optional_context"
        ]
        return committed_plan_builder(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "build_mode_scan_execution_plan",
        wrapper,
    )
    call_composition()
    assert captured["optional"] is False


def test_plan_builder_receives_explicit_optional_true(
    monkeypatch,
):
    captured = {}

    def wrapper(**kwargs):
        captured["optional"] = kwargs[
            "include_optional_context"
        ]
        return committed_plan_builder(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "build_mode_scan_execution_plan",
        wrapper,
    )
    call_composition(
        mode="SCALP",
        include_optional_context=True,
    )
    assert captured["optional"] is True


def test_all_three_modes_succeed():
    for mode in MODES:
        result, _state = call_composition(mode=mode)
        assert result.mode == mode


def test_scalp_optional_false_succeeds():
    result, _state = call_composition(
        mode="SCALP",
        include_optional_context=False,
    )
    assert result.include_optional_context is False


def test_scalp_optional_true_succeeds():
    result, _state = call_composition(
        mode="SCALP",
        include_optional_context=True,
    )
    assert result.include_optional_context is True


def test_wrong_plan_result_type_is_rejected(monkeypatch):
    monkeypatch.setattr(
        composition_module,
        "build_mode_scan_execution_plan",
        lambda **_kwargs: object(),
    )
    assert_invalid(lambda: call_composition())


def test_hostile_plan_result_is_rejected(monkeypatch):
    def wrapper(**kwargs):
        value = committed_plan_builder(**kwargs)
        return hostile_copy(
            value,
            "execution_performed",
            True,
        )

    monkeypatch.setattr(
        composition_module,
        "build_mode_scan_execution_plan",
        wrapper,
    )
    assert_invalid(lambda: call_composition())


def test_request_plan_due_window_mismatch_is_rejected(
    monkeypatch,
):
    def wrapper(**kwargs):
        value = committed_plan_builder(**kwargs)
        return hostile_copy(
            value,
            "due_window_id",
            "other-window",
        )

    monkeypatch.setattr(
        composition_module,
        "build_mode_scan_execution_plan",
        wrapper,
    )
    assert_invalid(lambda: call_composition())


def test_executor_is_called_exactly_once(monkeypatch):
    calls = {"count": 0}

    def wrapper(**kwargs):
        calls["count"] += 1
        return committed_executor(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "execute_mode_scan_plan",
        wrapper,
    )
    call_composition()
    assert calls["count"] == 1


def test_executor_keyword_arguments_are_exact(monkeypatch):
    captured = {}

    def wrapper(**kwargs):
        captured.update(kwargs)
        return committed_executor(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "execute_mode_scan_plan",
        wrapper,
    )
    call_composition()
    assert tuple(captured) == (
        "plan",
        "observed_at",
        "candle_fetcher",
        "oi_fetcher",
        "technical_evaluator",
    )


def test_executor_receives_exact_shared_observed_at(monkeypatch):
    captured = {}

    def wrapper(**kwargs):
        captured["observed_at"] = kwargs["observed_at"]
        return committed_executor(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "execute_mode_scan_plan",
        wrapper,
    )
    call_composition()
    assert captured["observed_at"] == OBSERVED_AT


def test_wrong_execution_result_type_is_rejected(monkeypatch):
    monkeypatch.setattr(
        composition_module,
        "execute_mode_scan_plan",
        lambda **_kwargs: object(),
    )
    assert_invalid(lambda: call_composition())


def test_hostile_execution_result_is_rejected(monkeypatch):
    def wrapper(**kwargs):
        value = committed_executor(**kwargs)
        return hostile_copy(
            value,
            "observed_at",
            "2026-07-30T06:35:00Z",
        )

    monkeypatch.setattr(
        composition_module,
        "execute_mode_scan_plan",
        wrapper,
    )
    assert_invalid(lambda: call_composition())


def test_executor_whole_failure_is_sanitized(monkeypatch):
    def wrapper(**_kwargs):
        raise ValueError("private executor detail")

    monkeypatch.setattr(
        composition_module,
        "execute_mode_scan_plan",
        wrapper,
    )
    assert_invalid(lambda: call_composition())


def test_executor_skipped_outcome_is_preserved():
    result, state = call_composition(
        candle_kind="exception",
    )
    assert result.execution_result.skipped_count == 1
    assert (
        result.execution_result.outcomes[0].outcome_kind
        == OUTCOME_SKIPPED
    )
    assert result.route_result.candidates == ()
    assert state["pipeline"] == 1


def test_executor_no_candidate_outcome_is_preserved():
    result, state = call_composition(
        evaluator_kind="none",
    )
    assert result.execution_result.no_candidate_count == 1
    assert (
        result.execution_result.outcomes[0].outcome_kind
        == OUTCOME_NO_CANDIDATE
    )
    assert result.route_result.candidates == ()
    assert state["pipeline"] == 1


def test_executor_candidate_outcome_is_preserved():
    result, _state = call_composition()
    assert result.execution_result.candidate_count == 1
    assert (
        result.execution_result.outcomes[0].outcome_kind
        == OUTCOME_CANDIDATE
    )


def test_scanner_projection_is_exact_builtin_tuple(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    call_composition()
    assert type(captured["rows"]) is tuple


def test_scanner_projection_key_order_is_exact(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    call_composition()
    assert tuple(captured["rows"][0]) == SCANNER_ROW_KEYS


def test_scanner_projection_preserves_candidate_order(
    monkeypatch,
):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    result, _state = call_composition(
        market_snapshot=markets(2)
    )
    assert tuple(
        row["candidate_id"] for row in captured["rows"]
    ) == tuple(
        candidate.candidate_id
        for candidate in result.execution_result.candidates
    )


def test_empty_candidate_projection_is_exact_empty_tuple(
    monkeypatch,
):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    call_composition(evaluator_kind="none")
    assert captured["rows"] == ()
    assert type(captured["rows"]) is tuple


def test_skipped_outcome_is_not_projected(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    call_composition(candle_kind="exception")
    assert captured["rows"] == ()


def test_no_candidate_outcome_is_not_projected(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        composition_module,
        "route_mode_scan",
        route_capture_wrapper(captured),
    )
    call_composition(evaluator_kind="none")
    assert captured["rows"] == ()


def test_projection_creates_no_synthetic_candidate():
    result, _state = call_composition(
        evaluator_kind="none"
    )
    assert result.execution_result.candidates == ()
    assert result.route_result.candidates == ()


def test_projection_does_not_sort_candidate_order():
    result, _state = call_composition(
        market_snapshot=(
            market("ZZZ/USDT:USDT", 2000.0),
            market("AAA/USDT:USDT", 1000.0),
        )
    )
    assert tuple(
        item.symbol for item in result.route_result.candidates
    ) == ("ZZZ/USDT:USDT", "AAA/USDT:USDT")


def test_duplicate_routed_candidate_is_rejected(monkeypatch):
    call = route_mutator(
        monkeypatch,
        lambda route: hostile_copy(
            route,
            "candidates",
            (route.candidates[0], route.candidates[0]),
        ),
    )
    assert_invalid(call)


def test_reordered_routed_candidates_are_rejected(monkeypatch):
    call = route_mutator(
        monkeypatch,
        lambda route: hostile_copy(
            route,
            "candidates",
            tuple(reversed(route.candidates)),
        ),
        count=2,
    )
    assert_invalid(call)


def test_missing_routed_candidate_is_rejected(monkeypatch):
    call = route_mutator(
        monkeypatch,
        lambda route: hostile_copy(
            route,
            "candidates",
            (),
        ),
    )
    assert_invalid(call)


def test_mutated_routed_candidate_is_rejected(monkeypatch):
    def mutation(route):
        hostile_copy(
            route.candidates[0],
            "payload_json",
            "{}",
        )

    assert_invalid(route_mutator(monkeypatch, mutation))


def test_route_mode_parity_is_required(monkeypatch):
    assert_invalid(
        route_mutator(
            monkeypatch,
            lambda route: hostile_copy(
                route,
                "mode",
                "SCALP",
            ),
        )
    )


def test_route_due_window_parity_is_required(monkeypatch):
    assert_invalid(
        route_mutator(
            monkeypatch,
            lambda route: hostile_copy(
                route,
                "due_window_id",
                "other-window",
            ),
        )
    )


def test_route_lineage_parity_is_required(monkeypatch):
    assert_invalid(
        route_mutator(
            monkeypatch,
            lambda route: hostile_copy(
                route,
                "mode_lineage_sha256",
                "0" * 64,
            ),
        )
    )


def test_route_scanner_invocation_count_is_one():
    result, _state = call_composition()
    assert result.route_result.scanner_invocation_count == 1


def test_route_retry_count_is_zero():
    result, _state = call_composition()
    assert result.route_result.retry_count == 0


def test_validation_adapter_is_called_exactly_once(monkeypatch):
    calls = {"count": 0}

    def wrapper(**kwargs):
        calls["count"] += 1
        return committed_validation_adapter(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "run_mode_validation_pipeline",
        wrapper,
    )
    call_composition()
    assert calls["count"] == 1


def test_validation_adapter_keyword_arguments_are_exact(
    monkeypatch,
):
    captured = {}

    def wrapper(**kwargs):
        captured.update(kwargs)
        return committed_validation_adapter(**kwargs)

    monkeypatch.setattr(
        composition_module,
        "run_mode_validation_pipeline",
        wrapper,
    )
    call_composition()
    assert tuple(captured) == ("route_result", "pipeline")
    assert type(captured["route_result"]) is ModeRouteResultV1


def test_pipeline_callback_is_called_exactly_once():
    _result, state = call_composition()
    assert state["pipeline"] == 1


def test_empty_route_still_calls_pipeline_once():
    result, state = call_composition(
        evaluator_kind="none"
    )
    assert result.route_result.candidates == ()
    assert state["pipeline"] == 1


def test_empty_route_has_valid_empty_validation_result():
    result, _state = call_composition(
        evaluator_kind="none"
    )
    assert result.validation_result.input_candidate_count == 0
    assert result.validation_result.controlled_top10 == ()
    assert result.validation_result.final_top5 == ()


def test_wrong_validation_result_type_is_rejected(monkeypatch):
    monkeypatch.setattr(
        composition_module,
        "run_mode_validation_pipeline",
        lambda **_kwargs: object(),
    )
    assert_invalid(lambda: call_composition())


def test_validation_input_route_hash_mismatch_is_rejected(
    monkeypatch,
):
    assert_invalid(
        validation_mutator(
            monkeypatch,
            lambda value: hostile_copy(
                value,
                "input_route_sha256",
                "0" * 64,
            ),
        )
    )


def test_validation_candidate_count_mismatch_is_rejected(
    monkeypatch,
):
    assert_invalid(
        validation_mutator(
            monkeypatch,
            lambda value: hostile_copy(
                value,
                "input_candidate_count",
                2,
            ),
        )
    )


def test_controlled_candidate_identity_mismatch_is_rejected(
    monkeypatch,
):
    def mutation(value):
        hostile_copy(
            value.controlled_top10[0],
            "candidate_id",
            "other-candidate",
        )

    assert_invalid(validation_mutator(monkeypatch, mutation))


def test_final_candidate_identity_mismatch_is_rejected(
    monkeypatch,
):
    def mutation(value):
        hostile_copy(
            value.final_top5[0],
            "candidate_id",
            "other-candidate",
        )

    assert_invalid(validation_mutator(monkeypatch, mutation))


def test_controlled_candidate_order_mismatch_is_rejected(
    monkeypatch,
):
    def mutation(value):
        hostile_copy(
            value,
            "controlled_top10",
            tuple(reversed(value.controlled_top10)),
        )

    assert_invalid(
        validation_mutator(
            monkeypatch,
            mutation,
            count=2,
        )
    )


def test_final_candidate_subsequence_mismatch_is_rejected(
    monkeypatch,
):
    def mutation(value):
        hostile_copy(
            value,
            "final_top5",
            tuple(reversed(value.final_top5)),
        )

    assert_invalid(
        validation_mutator(
            monkeypatch,
            mutation,
            count=2,
        )
    )


def test_validation_retry_count_is_zero():
    result, _state = call_composition()
    assert result.validation_result.retry_count == 0


def test_pipeline_exception_is_sanitized():
    def pipeline(_rows):
        raise ValueError("private pipeline detail")

    assert_invalid(
        lambda: call_composition(pipeline=pipeline)
    )


def test_pipeline_malformed_output_is_sanitized():
    assert_invalid(
        lambda: call_composition(
            pipeline=lambda _rows: {"bad": True}
        )
    )


def test_combined_result_nested_types_are_exact():
    result, _state = call_composition()
    assert type(result.execution_plan) is ModeScanExecutionPlanV1
    assert (
        type(result.execution_result)
        is ModeScanExecutionResultV1
    )
    assert type(result.route_result) is ModeRouteResultV1
    assert (
        type(result.validation_result)
        is ModeValidationPipelineResultV1
    )


def test_combined_result_reconstructs_all_nested_objects():
    result, _state = call_composition()
    reconstructed = ModeScanCompositionResultV1(
        **result_values(result)
    )
    assert reconstructed.execution_plan is not result.execution_plan
    assert (
        reconstructed.execution_result
        is not result.execution_result
    )
    assert reconstructed.route_result is not result.route_result
    assert (
        reconstructed.validation_result
        is not result.validation_result
    )
    assert reconstructed.to_mapping() == result.to_mapping()


def test_combined_result_rejects_hostile_nested_plan():
    result, _state = call_composition()
    plan = hostile_copy(
        result.execution_plan,
        "due_window_id",
        "other-window",
    )
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(result, execution_plan=plan)
        )
    )


def test_combined_result_requires_mode_parity():
    result, _state = call_composition()
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(result, mode="SCALP")
        )
    )


def test_combined_result_requires_due_window_parity():
    result, _state = call_composition()
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(
                result,
                due_window_id="other-window",
            )
        )
    )


def test_combined_result_requires_lineage_parity():
    result, _state = call_composition()
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(
                result,
                mode_lineage_sha256="0" * 64,
            )
        )
    )


def test_combined_result_requires_plan_sha_parity():
    result, _state = call_composition()
    execution = hostile_copy(
        result.execution_result,
        "plan_sha256",
        "0" * 64,
    )
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(
                result,
                execution_result=execution,
            )
        )
    )


def test_combined_result_requires_observed_at_parity():
    result, _state = call_composition()
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(
                result,
                observed_at="2026-07-30T06:35:00Z",
            )
        )
    )


def test_combined_result_requires_optional_context_parity():
    result, _state = call_composition(
        mode="SCALP",
        include_optional_context=True,
    )
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(
                result,
                include_optional_context=False,
            )
        )
    )


def test_combined_result_requires_candidate_identity_parity():
    result, _state = call_composition()
    route = result.route_result
    hostile_copy(
        route.candidates[0],
        "candidate_id",
        "other-candidate",
    )
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(result, route_result=route)
        )
    )


def test_combined_result_requires_route_hash_parity():
    result, _state = call_composition()
    validation = hostile_copy(
        result.validation_result,
        "input_route_sha256",
        "0" * 64,
    )
    assert_invalid(
        lambda: ModeScanCompositionResultV1(
            **result_values(
                result,
                validation_result=validation,
            )
        )
    )


def test_combined_result_to_mapping_is_exact_and_detached():
    result, _state = call_composition()
    mapping = result.to_mapping()
    mapping["execution_plan"]["discovery_symbols"].append(
        "MUTATED/USDT:USDT"
    )
    assert (
        "MUTATED/USDT:USDT"
        not in result.execution_plan.discovery_symbols
    )


def test_composition_hash_is_exact_canonical_digest():
    result, _state = call_composition()
    mapping = result.to_mapping()
    supplied = mapping.pop("composition_sha256")
    assert supplied == digest_mapping(mapping)


def test_deterministic_replay_is_exact():
    first, _first_state = call_composition()
    second, _second_state = call_composition()
    assert first.to_mapping() == second.to_mapping()
    assert first.composition_sha256 == second.composition_sha256


def test_hash_changes_with_due_window():
    first, _state = call_composition(
        due_window_id="window-a"
    )
    second, _state = call_composition(
        due_window_id="window-b"
    )
    assert first.composition_sha256 != second.composition_sha256


def test_hash_changes_with_snapshot_volume():
    first, _state = call_composition(
        market_snapshot=(market(volume=1000.0),)
    )
    second, _state = call_composition(
        market_snapshot=(market(volume=2000.0),)
    )
    assert first.composition_sha256 != second.composition_sha256


def test_hash_changes_with_mode():
    first, _state = call_composition(mode="SWING")
    second, _state = call_composition(mode="INTRADAY")
    assert first.composition_sha256 != second.composition_sha256


def test_hash_changes_with_optional_context():
    first, _state = call_composition(
        mode="SCALP",
        include_optional_context=False,
    )
    second, _state = call_composition(
        mode="SCALP",
        include_optional_context=True,
    )
    assert first.composition_sha256 != second.composition_sha256


def test_hash_changes_with_observed_at():
    first, _state = call_composition(
        observed_at="2026-07-30T06:30:00Z"
    )
    second, _state = call_composition(
        observed_at="2026-07-30T06:35:00Z"
    )
    assert first.composition_sha256 != second.composition_sha256


def test_hash_changes_with_evaluator_payload():
    first, _state = call_composition(score=91)
    second, _state = call_composition(score=92)
    assert first.composition_sha256 != second.composition_sha256


def test_hash_changes_with_pipeline_usage():
    def pipeline(rows):
        controlled = [dict(row) for row in rows]
        return {
            "controlled_top10": controlled,
            "final_top5": controlled[:1],
            "usage": {"variant": 2},
        }

    first, _state = call_composition()
    second, _state = call_composition(pipeline=pipeline)
    assert first.composition_sha256 != second.composition_sha256


def test_public_function_returns_result_only():
    result, _state = call_composition()
    assert type(result) is ModeScanCompositionResultV1
    assert not isinstance(result, tuple)


def test_nested_input_mutation_cannot_change_reconstructed_result():
    result, _state = call_composition()
    reconstructed = ModeScanCompositionResultV1(
        **result_values(result)
    )
    expected = reconstructed.to_mapping()
    hostile_copy(
        result.execution_plan,
        "due_window_id",
        "mutated-window",
    )
    assert reconstructed.to_mapping() == expected


def test_execution_route_candidates_match_exactly():
    result, _state = call_composition(
        market_snapshot=markets(2)
    )
    executed = result.execution_result.candidates
    routed = result.route_result.candidates
    assert len(executed) == len(routed)
    for left, right in zip(executed, routed, strict=True):
        assert (
            left.candidate_id,
            left.mode,
            left.symbol,
            left.mode_lineage_sha256,
            left.payload_json,
            left.payload_sha256,
        ) == (
            right.candidate_id,
            right.mode,
            right.symbol,
            right.mode_lineage_sha256,
            right.payload_json,
            right.payload_sha256,
        )


def test_controlled_candidates_are_ordered_route_subsequence():
    result, _state = call_composition(
        market_snapshot=markets(2)
    )
    route_ids = [
        item.candidate_id
        for item in result.route_result.candidates
    ]
    controlled_ids = [
        item.candidate_id
        for item in result.validation_result.controlled_top10
    ]
    assert controlled_ids == route_ids[:10]


def test_final_candidates_are_ordered_controlled_subsequence():
    result, _state = call_composition(
        market_snapshot=markets(2)
    )
    controlled_ids = [
        item.candidate_id
        for item in result.validation_result.controlled_top10
    ]
    final_ids = [
        item.candidate_id
        for item in result.validation_result.final_top5
    ]
    assert final_ids == controlled_ids[:5]


def test_end_to_end_mode_lineage_is_exact():
    result, _state = call_composition()
    lineage = result.mode_lineage_sha256
    assert result.execution_plan.mode_lineage_sha256 == lineage
    assert result.execution_result.mode_lineage_sha256 == lineage
    assert result.route_result.mode_lineage_sha256 == lineage
    assert result.validation_result.mode_lineage_sha256 == lineage


def test_plan_execution_route_validation_modes_are_exact():
    result, _state = call_composition(mode="INTRADAY")
    assert (
        result.mode,
        result.execution_plan.mode,
        result.execution_result.mode,
        result.route_result.mode,
        result.validation_result.mode,
    ) == ("INTRADAY",) * 5


def test_due_window_is_exact_across_owned_layers():
    result, _state = call_composition(
        due_window_id="window.parity+1"
    )
    assert (
        result.due_window_id,
        result.execution_plan.due_window_id,
        result.route_result.due_window_id,
        result.validation_result.due_window_id,
    ) == ("window.parity+1",) * 4


def test_observed_at_is_exact_across_execution_layers():
    result, _state = call_composition()
    assert result.observed_at == OBSERVED_AT
    assert result.execution_result.observed_at == OBSERVED_AT


def test_all_retry_counts_are_zero():
    result, _state = call_composition()
    assert result.execution_result.retry_count == 0
    assert result.route_result.retry_count == 0
    assert result.validation_result.retry_count == 0


def test_fixture_callbacks_obey_committed_stage_counts():
    result, state = call_composition()
    assert (
        state["candle"]
        == result.execution_result.actual_candle_call_count
    )
    assert (
        state["oi"]
        == result.execution_result.actual_oi_call_count
    )
    assert (
        state["evaluator"]
        == result.execution_result.actual_evaluator_invocation_count
    )
    assert state["pipeline"] == 1


def test_no_automatic_retry_call_site_exists():
    source = ENGINE_PATH.read_text()
    assert "retry(" not in source
    assert ".retry(" not in source


def test_no_async_definition_exists():
    tree = ast.parse(ENGINE_PATH.read_text())
    assert not any(
        isinstance(node, (ast.AsyncFunctionDef, ast.Await))
        for node in ast.walk(tree)
    )


def test_no_concurrency_import_or_call_exists():
    source = ENGINE_PATH.read_text()
    prohibited = (
        "thread",
        "process",
        "pool",
        "gather",
        "asyncio",
        "concurrent",
    )
    assert not any(token in source.lower() for token in prohibited)


def test_no_cache_surface_exists():
    source = ENGINE_PATH.read_text().lower()
    assert "cache_lookup" not in source
    assert "cache_write" not in source
    assert "redis" not in source


def test_no_network_or_provider_surface_exists():
    tree = ast.parse(ENGINE_PATH.read_text())
    imported_roots = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
    )
    prohibited_roots = {
        "aiohttp",
        "ccxt",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "websocket",
    }
    assert imported_roots.isdisjoint(prohibited_roots)


def test_no_current_clock_call_exists():
    tree = ast.parse(ENGINE_PATH.read_text())
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"now", "utcnow", "today"}
        for node in ast.walk(tree)
    )


def test_no_live_price_surface_exists():
    assert "live_price" not in ENGINE_PATH.read_text().lower()


def test_no_legacy_scanner_or_master_surface_exists():
    source = ENGINE_PATH.read_text().lower()
    assert "scanner.py" not in source
    assert "master_engine" not in source


def test_no_production_conversion_surface_exists():
    assert "production" not in ENGINE_PATH.read_text().lower()


def test_no_publication_or_delivery_surface_exists():
    source = ENGINE_PATH.read_text().lower()
    assert "publication" not in source
    assert "publish(" not in source


def test_no_telegram_surface_exists():
    assert "telegram" not in ENGINE_PATH.read_text().lower()


def test_no_exchange_order_surface_exists():
    source = ENGINE_PATH.read_text().lower()
    assert "exchange" not in source
    assert "order(" not in source


def test_no_filesystem_write_surface_exists():
    tree = ast.parse(ENGINE_PATH.read_text())
    prohibited = {"open", "write_text", "write_bytes", "unlink"}
    assert not any(
        isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id in prohibited
            or isinstance(node.func, ast.Attribute)
            and node.func.attr in prohibited
        )
        for node in ast.walk(tree)
    )


def test_no_module_global_mutable_execution_state():
    tree = ast.parse(ENGINE_PATH.read_text())
    mutable_assignments = []
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign):
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            value = node.value
        if isinstance(value, (ast.List, ast.Dict, ast.Set)):
            mutable_assignments.append(node)
    assert mutable_assignments == []


def test_exact_composition_call_site_inventory():
    tree = ast.parse(ENGINE_PATH.read_text())
    names = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    ]
    assert names.count("route_mode_scan") == 1
    assert names.count("build_mode_scan_execution_plan") == 1
    assert names.count("execute_mode_scan_plan") == 1
    assert names.count("run_mode_validation_pipeline") == 1


def test_exact_candidate_projection_call_site_inventory():
    tree = ast.parse(ENGINE_PATH.read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "to_scanner_row"
    ]
    assert len(calls) == 1


def test_result_constructor_occurs_after_validation_call():
    tree = ast.parse(ENGINE_PATH.read_text())
    calls = {
        (
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
            if isinstance(node.func, ast.Attribute)
            else ""
        ): node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id
            in {
                "run_mode_validation_pipeline",
                "ModeScanCompositionResultV1",
            }
        )
    }
    assert (
        calls["run_mode_validation_pipeline"]
        < calls["ModeScanCompositionResultV1"]
    )


def test_route_call_occurs_before_validation_call():
    tree = ast.parse(ENGINE_PATH.read_text())
    positions = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id
            in {
                "route_mode_scan",
                "run_mode_validation_pipeline",
            }
        ):
            positions[node.func.id] = node.lineno
    assert (
        positions["route_mode_scan"]
        < positions["run_mode_validation_pipeline"]
    )


def test_test_module_has_at_least_100_top_level_tests():
    tree = ast.parse(TEST_PATH.read_text())
    count = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in tree.body
    )
    assert count >= 100


def test_test_module_has_no_nonrunning_markers():
    tree = ast.parse(TEST_PATH.read_text())
    prohibited = {"skip", "skipif", "xfail"}
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    decorators = {
        node.attr
        for item in tree.body
        if isinstance(
            item,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        for node in ast.walk(
            ast.Tuple(elts=item.decorator_list)
        )
        if isinstance(node, ast.Attribute)
    }
    assert prohibited.isdisjoint(calls | decorators)
