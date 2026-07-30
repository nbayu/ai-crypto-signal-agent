"""Focused tests for pure E2 fetch-budget and cadence contracts."""

import ast
import dataclasses
import inspect
import json
from pathlib import Path

import pytest

from engine.mode_fetch_budget_cadence_v1 import (
    ADMITTED_REASON,
    ARMED_JOB_KIND,
    ARMED_MONITOR_MAX_SYMBOLS_PER_MODE,
    BASE_JOB_KIND,
    DISCOVERY_UNIVERSE_MAX_SYMBOLS,
    MAX_JOB_START_DELAY_SECONDS,
    MODE_FULL_EVALUATION_MAX_SYMBOLS,
    SKIPPED_START_DELAY_REASON,
    ModeFetchCadenceValidationError,
    admit_cadence_start,
    all_mode_cadence_jobs,
    build_armed_monitor_budget,
    build_daily_cadence_plan,
    build_discovery_universe_policy,
    build_mode_fetch_budget,
    build_mode_owned_cache_key,
)


def _budget(mode="SWING", *, symbols=100, optional=False):
    return build_mode_fetch_budget(
        mode=mode,
        symbol_count=symbols,
        include_optional_context=optional,
    )


def _window(plan, due_second):
    return next(
        item for item in plan.windows
        if item.due_second_utc == due_second
    )


def test_discovery_policy_exact_values():
    policy = build_discovery_universe_policy()
    assert policy.max_symbols == DISCOVERY_UNIVERSE_MAX_SYMBOLS == 500
    assert policy.market_type == "ACTIVE_USDT_LINEAR_PERPETUAL"
    assert policy.truncation_order == (
        "QUOTE_VOLUME_24H_DESC_THEN_CANONICAL_SYMBOL_ASC"
    )
    assert policy.truncation_must_be_audited is True
    assert policy.unbounded_universe_prohibited is True


def test_discovery_policy_is_frozen_and_mapping_is_fresh():
    policy = build_discovery_universe_policy()
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.max_symbols = 1
    first = policy.to_mapping()
    second = policy.to_mapping()
    first["max_symbols"] = 1
    assert second["max_symbols"] == 500
    assert policy.max_symbols == 500


def test_public_builder_arguments_are_keyword_only():
    functions = (
        build_mode_fetch_budget,
        build_armed_monitor_budget,
        build_mode_owned_cache_key,
        build_daily_cadence_plan,
        admit_cadence_start,
    )
    for function in functions:
        parameters = inspect.signature(function).parameters.values()
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in parameters
        )
        assert all(
            parameter.default is inspect.Parameter.empty
            for parameter in parameters
        )


def test_invalid_modes_fail_closed():
    for bad_mode in ("swing", "UNKNOWN", "", True, 1, None):
        with pytest.raises(
            ModeFetchCadenceValidationError,
            match=r"^invalid mode fetch cadence contract$",
        ):
            build_mode_fetch_budget(
                mode=bad_mode,
                symbol_count=1,
                include_optional_context=False,
            )


def test_swing_budget_matches_owner_freeze():
    budget = _budget("SWING")
    assert budget.per_symbol_ohlcv_request_count == 5
    assert budget.per_symbol_request_count == 6
    assert budget.per_symbol_ip_weight == 7
    assert budget.total_request_count == 602
    assert budget.total_ip_weight == 741
    assert budget.oi_history_request_count == 100


def test_intraday_budget_matches_owner_freeze():
    budget = _budget("INTRADAY")
    assert budget.per_symbol_ohlcv_request_count == 5
    assert budget.per_symbol_request_count == 6
    assert budget.per_symbol_ip_weight == 7
    assert budget.total_request_count == 602
    assert budget.total_ip_weight == 741


def test_scalp_required_budget_matches_owner_freeze():
    budget = _budget("SCALP", optional=False)
    assert [item.timeframe for item in budget.timeframe_fetches] == [
        "15m", "5m", "3m"
    ]
    assert budget.per_symbol_ohlcv_request_count == 3
    assert budget.per_symbol_request_count == 4
    assert budget.per_symbol_ip_weight == 5
    assert budget.total_request_count == 402
    assert budget.total_ip_weight == 541


def test_scalp_optional_budget_matches_owner_freeze():
    budget = _budget("SCALP", optional=True)
    assert [item.timeframe for item in budget.timeframe_fetches] == [
        "1h", "15m", "5m", "3m"
    ]
    assert budget.per_symbol_ohlcv_request_count == 4
    assert budget.per_symbol_request_count == 5
    assert budget.per_symbol_ip_weight == 6
    assert budget.total_request_count == 502
    assert budget.total_ip_weight == 641


def test_full_evaluation_symbol_lower_bound_is_enforced():
    with pytest.raises(ModeFetchCadenceValidationError):
        _budget(symbols=0)


def test_full_evaluation_symbol_upper_bound_is_enforced():
    assert _budget(symbols=MODE_FULL_EVALUATION_MAX_SYMBOLS).symbol_count == 100
    with pytest.raises(ModeFetchCadenceValidationError):
        _budget(symbols=MODE_FULL_EVALUATION_MAX_SYMBOLS + 1)


def test_include_optional_context_requires_exact_boolean():
    for bad_value in (0, 1, "false", None):
        with pytest.raises(ModeFetchCadenceValidationError):
            build_mode_fetch_budget(
                mode="SCALP",
                symbol_count=1,
                include_optional_context=bad_value,
            )


def test_fetch_counts_and_raw_limits_match_purpose_policy():
    budget = _budget("SWING", symbols=1)
    expected = {
        "CONTEXT": (50, 51, 1),
        "BIAS": (50, 51, 1),
        "STRUCTURE": (300, 301, 2),
        "TRIGGER": (300, 301, 2),
    }
    for fetch in budget.timeframe_fetches:
        policy = expected[fetch.purposes[0]]
        assert (
            fetch.closed_candle_count,
            fetch.raw_fetch_limit,
            fetch.ip_weight,
        ) == policy
        assert fetch.raw_fetch_limit == fetch.closed_candle_count + 1
        assert fetch.closed_candle_only is True
        assert fetch.request_count == 1


def test_same_mode_timeframe_fetches_are_unique():
    for mode, optional in (
        ("SWING", False),
        ("INTRADAY", False),
        ("SCALP", True),
    ):
        timeframes = [
            item.timeframe
            for item in _budget(mode, optional=optional).timeframe_fetches
        ]
        assert len(timeframes) == len(set(timeframes))


def test_budget_output_is_deterministic():
    first = _budget("INTRADAY", symbols=73)
    second = _budget("INTRADAY", symbols=73)
    assert first == second
    assert first.to_mapping() == second.to_mapping()
    assert json.dumps(
        first.to_mapping(),
        sort_keys=True,
        separators=(",", ":"),
    ) == json.dumps(
        second.to_mapping(),
        sort_keys=True,
        separators=(",", ":"),
    )


def test_budget_and_owned_fetches_are_immutable():
    budget = _budget()
    with pytest.raises(dataclasses.FrozenInstanceError):
        budget.symbol_count = 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        budget.timeframe_fetches[0].raw_fetch_limit = 1
    first = budget.to_mapping()
    first["timeframe_fetches"].clear()
    assert len(budget.timeframe_fetches) == 5


def test_swing_armed_budget_is_trigger_only():
    budget = build_armed_monitor_budget(mode="SWING", symbol_count=5)
    assert budget.trigger_timeframe == "15m"
    assert budget.closed_candle_count == 300
    assert budget.raw_fetch_limit == 301
    assert budget.request_count == 5
    assert budget.ip_weight == 10


def test_intraday_armed_budget_is_trigger_only():
    budget = build_armed_monitor_budget(mode="INTRADAY", symbol_count=5)
    assert budget.trigger_timeframe == "5m"
    assert budget.request_count == 5
    assert budget.ip_weight == 10


def test_scalp_armed_budget_is_trigger_only():
    budget = build_armed_monitor_budget(mode="SCALP", symbol_count=5)
    assert budget.trigger_timeframe == "3m"
    assert budget.request_count == 5
    assert budget.ip_weight == 10
    assert budget.full_universe_fallback_allowed is False
    assert budget.full_mode_rescan_fallback_allowed is False
    assert budget.retry_count == 0


def test_armed_monitor_symbol_bound_is_enforced():
    assert build_armed_monitor_budget(
        mode="SCALP",
        symbol_count=ARMED_MONITOR_MAX_SYMBOLS_PER_MODE,
    ).max_symbols == 5
    for bad_value in (0, 6, True):
        with pytest.raises(ModeFetchCadenceValidationError):
            build_armed_monitor_budget(
                mode="SCALP",
                symbol_count=bad_value,
            )


def test_armed_monitor_uses_mode_owned_cache_and_fail_closed_action():
    budget = build_armed_monitor_budget(mode="INTRADAY", symbol_count=1)
    assert budget.higher_context_source == (
        "CURRENT_MODE_OWNED_CLOSED_CANDLE_CACHE"
    )
    assert budget.cache_missing_or_stale_action == (
        "FAIL_CLOSED_SKIP_DUE_WINDOW"
    )


def test_cache_key_is_deterministic():
    kwargs = {
        "mode": "SWING",
        "canonical_symbol": "BTC/USDT",
        "timeframe": "4h",
        "closed_candle_close_at": "2026-07-30T00:00:00Z",
    }
    first = build_mode_owned_cache_key(**kwargs)
    second = build_mode_owned_cache_key(**kwargs)
    assert first == second
    assert len(first.cache_key_sha256) == 64


def test_cache_key_is_mode_owned():
    swing = build_mode_owned_cache_key(
        mode="SWING",
        canonical_symbol="BTC/USDT",
        timeframe="1h",
        closed_candle_close_at="2026-07-30T00:00:00Z",
    )
    scalp = build_mode_owned_cache_key(
        mode="SCALP",
        canonical_symbol="BTC/USDT",
        timeframe="1h",
        closed_candle_close_at="2026-07-30T00:00:00Z",
    )
    assert swing.cache_key_sha256 != scalp.cache_key_sha256


def test_cache_key_changes_with_closed_candle_identity():
    first = build_mode_owned_cache_key(
        mode="INTRADAY",
        canonical_symbol="ETH/USDT:USDT",
        timeframe="5m",
        closed_candle_close_at="2026-07-30T00:00:00Z",
    )
    second = build_mode_owned_cache_key(
        mode="INTRADAY",
        canonical_symbol="ETH/USDT:USDT",
        timeframe="5m",
        closed_candle_close_at="2026-07-30T00:05:00Z",
    )
    assert first.cache_key_sha256 != second.cache_key_sha256


def test_cache_key_rejects_cross_mode_timeframe():
    with pytest.raises(ModeFetchCadenceValidationError):
        build_mode_owned_cache_key(
            mode="SCALP",
            canonical_symbol="BTC/USDT",
            timeframe="1d",
            closed_candle_close_at="2026-07-30T00:00:00Z",
        )


def test_optional_context_is_rejected_when_mode_has_no_optional_layer():
    for mode in ("SWING", "INTRADAY"):
        with pytest.raises(ModeFetchCadenceValidationError):
            build_mode_fetch_budget(
                mode=mode,
                symbol_count=1,
                include_optional_context=True,
            )


def test_budget_rejects_noncanonical_optional_flag_replacement():
    budget = _budget("SWING", symbols=1, optional=False)
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(
            budget,
            include_optional_context=True,
        )


@pytest.mark.parametrize(
    ("mode", "timeframe", "close_at"),
    (
        ("SWING", "1w", "2026-08-03T00:00:00Z"),
        ("SWING", "1d", "2026-07-30T00:00:00Z"),
        ("SWING", "4h", "2026-07-30T04:00:00Z"),
        ("INTRADAY", "1h", "2026-07-30T01:00:00Z"),
        ("SWING", "15m", "2026-07-30T00:15:00Z"),
        ("INTRADAY", "5m", "2026-07-30T00:05:00Z"),
        ("SCALP", "3m", "2026-07-30T00:03:00Z"),
    ),
)
def test_cache_key_accepts_exact_utc_aligned_candle_close(
    mode,
    timeframe,
    close_at,
):
    key = build_mode_owned_cache_key(
        mode=mode,
        canonical_symbol="BTC/USDT",
        timeframe=timeframe,
        closed_candle_close_at=close_at,
    )
    assert key.closed_candle_close_at == close_at


@pytest.mark.parametrize(
    "close_at",
    (
        "x",
        "2026-07-30T00:00:00+00:00",
        "2026-07-30T00:00:00.000Z",
        "2026-07-30 00:00:00Z",
        "2026-7-30T00:00:00Z",
        "2026-02-30T00:00:00Z",
        "2026-07-30T00:01:00Z",
    ),
)
def test_cache_key_rejects_noncanonical_or_misaligned_close_at(
    close_at,
):
    with pytest.raises(ModeFetchCadenceValidationError):
        build_mode_owned_cache_key(
            mode="SWING",
            canonical_symbol="BTC/USDT",
            timeframe="4h",
            closed_candle_close_at=close_at,
        )


def test_cache_key_replacement_revalidates_candle_close_alignment():
    key = build_mode_owned_cache_key(
        mode="SWING",
        canonical_symbol="BTC/USDT",
        timeframe="4h",
        closed_candle_close_at="2026-07-30T00:00:00Z",
    )
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(
            key,
            closed_candle_close_at="2026-07-30T00:01:00Z",
        )


def test_fetch_purposes_are_detached_into_immutable_tuple():
    fetch = _budget("SWING", symbols=1).timeframe_fetches[0]
    caller_purposes = list(fetch.purposes)
    detached = dataclasses.replace(fetch, purposes=caller_purposes)
    caller_purposes.append("TRIGGER")
    assert type(detached.purposes) is tuple
    assert detached.purposes == fetch.purposes


def test_cadence_source_timeframes_are_detached_into_tuple():
    job = all_mode_cadence_jobs()[0]
    caller_timeframes = list(job.source_timeframes)
    detached = dataclasses.replace(
        job,
        source_timeframes=caller_timeframes,
    )
    caller_timeframes.append(job.source_timeframes[0])
    assert type(detached.source_timeframes) is tuple
    assert detached.source_timeframes == job.source_timeframes


def test_due_timeframes_are_detached_into_tuple():
    due_job = build_daily_cadence_plan(
        armed_modes=()
    ).windows[0].ordered_jobs[0]
    caller_timeframes = list(due_job.due_timeframes)
    detached = dataclasses.replace(
        due_job,
        due_timeframes=caller_timeframes,
    )
    caller_timeframes.append(due_job.due_timeframes[0])
    assert type(detached.due_timeframes) is tuple
    assert detached.due_timeframes == due_job.due_timeframes


def test_cache_key_rejects_nonexact_timeframe_string():
    class TimeframeString(str):
        pass

    key = build_mode_owned_cache_key(
        mode="SWING",
        canonical_symbol="BTC/USDT",
        timeframe="4h",
        closed_candle_close_at="2026-07-30T00:00:00Z",
    )
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(key, timeframe=TimeframeString("4h"))


def test_due_job_rejects_duplicate_timeframes():
    job = _window(
        build_daily_cadence_plan(armed_modes=()),
        20,
    ).ordered_jobs[0]
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(
            job,
            due_timeframes=("15m", "15m"),
        )


def test_due_window_rejects_job_at_impossible_due_second():
    window = build_daily_cadence_plan(armed_modes=()).windows[0]
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(
            window,
            due_second_utc=window.due_second_utc + 1,
        )


def test_due_window_rejects_incomplete_due_timeframe_set():
    window = _window(
        build_daily_cadence_plan(armed_modes=()),
        20,
    )
    due_job = dataclasses.replace(
        window.ordered_jobs[0],
        due_timeframes=("15m",),
    )
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(window, ordered_jobs=(due_job,))


def test_daily_plan_rejects_armed_mode_window_mismatch():
    plan = build_daily_cadence_plan(
        armed_modes=("SWING", "INTRADAY", "SCALP")
    )
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(plan, armed_modes=())


def test_daily_plan_rejects_duplicate_due_timestamps():
    plan = build_daily_cadence_plan(armed_modes=())
    duplicate_windows = (plan.windows[0], plan.windows[0])
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(
            plan,
            windows=duplicate_windows,
            logical_mode_job_count=2,
            unique_due_timestamp_count=2,
            collision_timestamp_count=0,
        )


def test_daily_plan_rejects_missing_canonical_window():
    plan = build_daily_cadence_plan(armed_modes=())
    windows = plan.windows[:-1]
    with pytest.raises(ModeFetchCadenceValidationError):
        dataclasses.replace(
            plan,
            windows=windows,
            logical_mode_job_count=sum(
                len(window.ordered_jobs) for window in windows
            ),
            unique_due_timestamp_count=len(windows),
            collision_timestamp_count=sum(
                len(window.ordered_jobs) > 1 for window in windows
            ),
        )


def test_cadence_job_inventory_has_two_jobs_per_mode():
    jobs = all_mode_cadence_jobs()
    assert len(jobs) == 6
    assert {
        (job.mode, job.job_kind)
        for job in jobs
    } == {
        ("SWING", BASE_JOB_KIND),
        ("SWING", ARMED_JOB_KIND),
        ("INTRADAY", BASE_JOB_KIND),
        ("INTRADAY", ARMED_JOB_KIND),
        ("SCALP", BASE_JOB_KIND),
        ("SCALP", ARMED_JOB_KIND),
    }


def test_cadence_job_due_counts_match_d5():
    counts = {
        (job.mode, job.job_kind): job.due_windows_per_utc_day
        for job in all_mode_cadence_jobs()
    }
    assert counts == {
        ("SWING", BASE_JOB_KIND): 6,
        ("SWING", ARMED_JOB_KIND): 96,
        ("INTRADAY", BASE_JOB_KIND): 96,
        ("INTRADAY", ARMED_JOB_KIND): 288,
        ("SCALP", BASE_JOB_KIND): 288,
        ("SCALP", ARMED_JOB_KIND): 480,
    }


def test_base_daily_plan_has_no_collisions():
    plan = build_daily_cadence_plan(armed_modes=())
    assert plan.logical_mode_job_count == 390
    assert plan.unique_due_timestamp_count == 390
    assert plan.collision_timestamp_count == 0


def test_all_armed_daily_plan_matches_d5_collision_counts():
    plan = build_daily_cadence_plan(
        armed_modes=("SWING", "INTRADAY", "SCALP")
    )
    assert plan.logical_mode_job_count == 1254
    assert plan.unique_due_timestamp_count == 870
    assert plan.collision_timestamp_count == 384


def test_intraday_armed_precedes_scalp_base_at_collision():
    plan = build_daily_cadence_plan(
        armed_modes=("SWING", "INTRADAY", "SCALP")
    )
    jobs = _window(plan, 10).ordered_jobs
    assert [item.job_id for item in jobs] == [
        "INTRADAY:ARMED_MONITOR",
        "SCALP:BASE_EVALUATION",
    ]


def test_swing_armed_precedes_intraday_base_at_collision():
    plan = build_daily_cadence_plan(
        armed_modes=("SWING", "INTRADAY", "SCALP")
    )
    jobs = _window(plan, 20).ordered_jobs
    assert [item.job_id for item in jobs] == [
        "SWING:ARMED_MONITOR",
        "INTRADAY:BASE_EVALUATION",
    ]


def test_within_mode_same_timestamp_updates_are_merged():
    plan = build_daily_cadence_plan(armed_modes=())
    jobs = _window(plan, 20).ordered_jobs
    assert len(jobs) == 1
    assert jobs[0].job_id == "INTRADAY:BASE_EVALUATION"
    assert jobs[0].due_timeframes == ("1h", "15m")


def test_armed_mode_input_is_canonical_and_duplicate_safe():
    first = build_daily_cadence_plan(
        armed_modes=("SCALP", "SWING")
    )
    second = build_daily_cadence_plan(
        armed_modes=("SWING", "SCALP")
    )
    assert first.armed_modes == second.armed_modes == ("SWING", "SCALP")
    with pytest.raises(ModeFetchCadenceValidationError):
        build_daily_cadence_plan(armed_modes=("SWING", "SWING"))
    with pytest.raises(ModeFetchCadenceValidationError):
        build_daily_cadence_plan(armed_modes=("UNKNOWN",))


def test_start_delay_boundary_is_inclusive_at_sixty_seconds():
    before = admit_cadence_start(delay_seconds=59)
    boundary = admit_cadence_start(
        delay_seconds=MAX_JOB_START_DELAY_SECONDS
    )
    after = admit_cadence_start(delay_seconds=61)
    assert before.admitted is True
    assert boundary.admitted is True
    assert after.admitted is False


def test_start_decision_is_fail_closed_without_retry_or_parallelism():
    admitted = admit_cadence_start(delay_seconds=0)
    skipped = admit_cadence_start(delay_seconds=61)
    assert admitted.reason_code == ADMITTED_REASON
    assert skipped.reason_code == SKIPPED_START_DELAY_REASON
    assert skipped.retry_count == 0
    assert skipped.catchup_allowed is False
    assert skipped.parallel_mode_job_allowed is False
    for bad_value in (True, -1, "60"):
        with pytest.raises(ModeFetchCadenceValidationError):
            admit_cadence_start(delay_seconds=bad_value)


def test_engine_source_is_pure_and_contains_no_canonical_mode_literals():
    source_path = (
        Path(__file__).parents[1]
        / "engine"
        / "mode_fetch_budget_cadence_v1.py"
    )
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    allowed_imports = {
        "__future__",
        "collections",
        "collections.abc",
        "dataclasses",
        "datetime",
        "hashlib",
        "json",
        "re",
        "typing",
        "engine.mode_data_plan_v1",
        "engine.mode_profile_v1",
    }
    imports = set()
    calls = set()
    strings = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        elif isinstance(node, ast.Constant) and type(node.value) is str:
            strings.add(node.value)
    assert imports <= allowed_imports
    assert not calls & {
        "open",
        "sleep",
        "system",
        "run",
        "Popen",
        "connect",
        "send_message",
        "create_order",
        "place_order",
        "fetch_ohlcv",
        "fetch_ticker",
        "get",
    }
    assert not strings & {"SWING", "INTRADAY", "SCALP"}
    assert "engine.scanner" not in source
    assert "master_engine" not in source
