from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from engine.mode_router_v1 import build_mode_scan_request
from engine.mode_scan_execution_evidence_v1 import (
    MODE_EXECUTION_CANDIDATE_ROW_SCHEMA_VERSION,
    MODE_OI_EXECUTION_EVIDENCE_SCHEMA_VERSION,
    MODE_OI_OBSERVATION_SCHEMA_VERSION,
    MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
    MODE_SCAN_EXECUTION_RESULT_SCHEMA_VERSION,
    MODE_SYMBOL_EXECUTION_OUTCOME_SCHEMA_VERSION,
    MODE_TECHNICAL_EVALUATOR_PAYLOAD_SCHEMA_VERSION,
    MODE_TIMEFRAME_EXECUTION_EVIDENCE_SCHEMA_VERSION,
    MODE_UTC_CANDLE_SCHEMA_VERSION,
    OUTCOME_CANDIDATE,
    OUTCOME_NO_CANDIDATE,
    OUTCOME_SKIPPED,
    REASON_CANDIDATE_ACCEPTED,
    REASON_CANDLE_BOUNDARY_EXCEPTION,
    REASON_CANDLE_EVIDENCE_INVALID,
    REASON_EVALUATOR_EXCEPTION,
    REASON_EVALUATOR_RESULT_INVALID,
    REASON_NO_CANDIDATE,
    REASON_OI_BOUNDARY_EXCEPTION,
    REASON_OI_EVIDENCE_INVALID,
    ModeExecutionCandidateRowV1,
    ModeOiExecutionEvidenceV1,
    ModeOiObservationV1,
    ModeScanExecutionEvidenceValidationError,
    ModeScanExecutionResultV1,
    ModeSymbolExecutionOutcomeV1,
    ModeTechnicalEvaluatorPayloadV1,
    ModeTimeframeExecutionEvidenceV1,
    ModeUtcCandleV1,
    build_e2_candidate_id,
    build_mode_execution_candidate_row,
    build_mode_oi_execution_evidence,
    build_mode_scan_execution_result,
    build_mode_technical_evaluator_payload,
    build_mode_timeframe_execution_evidence,
)
from engine.mode_scan_execution_plan_v1 import (
    MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
    ModeMarketSnapshotEntryV1,
    build_mode_scan_execution_plan,
)


OBSERVED_AT = "2026-07-30T06:30:00Z"
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64

TIMEFRAME_SECONDS = {
    "1w": 604800,
    "1d": 86400,
    "4h": 14400,
    "1h": 3600,
    "15m": 900,
    "5m": 300,
    "3m": 180,
}

PUBLIC_FIELDS = {
    ModeUtcCandleV1: (
        "schema_version",
        "timeframe",
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ),
    ModeTimeframeExecutionEvidenceV1: (
        "schema_version",
        "policy_version",
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "timeframe",
        "role",
        "optional_context",
        "observed_at",
        "raw_fetch_limit",
        "closed_candle_limit",
        "raw_candles",
        "developing_candle_dropped",
        "closed_candle_count",
        "closed_candles_sha256",
        "closed_candle_close_at",
        "cache_key_json",
        "cache_key_sha256",
        "evidence_sha256",
    ),
    ModeOiObservationV1: (
        "schema_version",
        "close_time",
        "open_interest",
    ),
    ModeOiExecutionEvidenceV1: (
        "schema_version",
        "policy_version",
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "observed_at",
        "period",
        "request_invocation_count",
        "observations",
        "observation_count",
        "newest_close_at",
        "newest_age_seconds",
        "observations_sha256",
        "evidence_sha256",
    ),
    ModeTechnicalEvaluatorPayloadV1: (
        "schema_version",
        "policy_version",
        "trigger_candle_close_at",
        "payload_json",
        "payload_sha256",
    ),
    ModeExecutionCandidateRowV1: (
        "schema_version",
        "policy_version",
        "plan_sha256",
        "candidate_id",
        "mode",
        "symbol",
        "mode_lineage_sha256",
        "reference_candle_at",
        "payload_json",
        "payload_sha256",
    ),
    ModeSymbolExecutionOutcomeV1: (
        "schema_version",
        "policy_version",
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "full_evaluation_rank",
        "outcome_kind",
        "reason_code",
        "timeframe_evidence_sha256s",
        "oi_evidence_sha256",
        "evaluator_payload_sha256",
        "candidate_row",
    ),
    ModeScanExecutionResultV1: (
        "schema_version",
        "policy_version",
        "plan_sha256",
        "mode",
        "mode_lineage_sha256",
        "observed_at",
        "planned_symbol_order",
        "planned_timeframe_counts",
        "planned_candle_call_count",
        "planned_oi_call_count",
        "planned_evaluator_invocation_count",
        "planned_executor_request_count",
        "planned_executor_ip_weight",
        "actual_candle_call_count",
        "actual_oi_call_count",
        "actual_evaluator_invocation_count",
        "actual_executor_request_count",
        "actual_executor_ip_weight",
        "candidate_count",
        "no_candidate_count",
        "skipped_count",
        "retry_count",
        "outcomes",
        "candidates",
        "execution_sha256",
    ),
}

BUILDERS = (
    build_mode_timeframe_execution_evidence,
    build_mode_oi_execution_evidence,
    build_mode_technical_evaluator_payload,
    build_e2_candidate_id,
    build_mode_execution_candidate_row,
    build_mode_scan_execution_result,
)


class StringSubclass(str):
    pass


class EqualitySpoof:
    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash("spoof")


class DictSubclass(dict):
    pass


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha(value):
    if not isinstance(value, str):
        value = canonical_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def assert_invalid(call):
    with pytest.raises(
        ModeScanExecutionEvidenceValidationError,
        match="^invalid mode scan execution evidence$",
    ):
        call()


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
    symbols = tuple(
        f"{chr(65 + index) * 3}/USDT"
        for index in range(count)
    )
    snapshot = [
        snapshot_entry(symbol, 1000 - index)
        for index, symbol in enumerate(symbols)
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
    seconds = TIMEFRAME_SECONDS[timeframe]
    elapsed = int((observed - epoch).total_seconds())
    return epoch + timedelta(seconds=(elapsed // seconds) * seconds)


def make_candle(timeframe, opened, index=0):
    base = 100.0 + index
    return ModeUtcCandleV1(
        schema_version=MODE_UTC_CANDLE_SCHEMA_VERSION,
        timeframe=timeframe,
        open_time=utc_text(opened),
        close_time=utc_text(
            opened + timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
        ),
        open=base,
        high=base + 2,
        low=base - 2,
        close=base + 1,
        volume=1000.0 + index,
    )


def candles_for(fetch, observed_at=OBSERVED_AT):
    final_open = developing_open(observed_at, fetch.timeframe)
    seconds = TIMEFRAME_SECONDS[fetch.timeframe]
    first_open = final_open - timedelta(
        seconds=seconds * fetch.closed_candle_limit
    )
    return tuple(
        make_candle(
            fetch.timeframe,
            first_open + timedelta(seconds=seconds * index),
            index,
        )
        for index in range(fetch.raw_fetch_limit)
    )


def make_timeframe_evidence(
    mode="SWING",
    *,
    high_tier=False,
    observed_at=OBSERVED_AT,
):
    plan = make_plan(mode, optional=(mode == "SCALP"))
    fetches = plan.full_evaluation_symbols[0].candle_fetches
    if high_tier:
        fetch = next(
            item
            for item in fetches
            if "STRUCTURE" in item.role or "TRIGGER" in item.role
        )
    else:
        fetch = next(
            item
            for item in fetches
            if "STRUCTURE" not in item.role
            and "TRIGGER" not in item.role
        )
    return build_mode_timeframe_execution_evidence(
        timeframe_plan=fetch,
        observed_at=observed_at,
        raw_candles=candles_for(fetch, observed_at),
    )


def make_oi_observations(count=3, newest="2026-07-30T06:30:00Z"):
    newest_dt = datetime.strptime(
        newest,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    return tuple(
        ModeOiObservationV1(
            schema_version=MODE_OI_OBSERVATION_SCHEMA_VERSION,
            close_time=utc_text(
                newest_dt - timedelta(minutes=5 * (count - index - 1))
            ),
            open_interest=1000.0 + index,
        )
        for index in range(count)
    )


def make_oi_evidence(
    mode="SWING",
    *,
    observed_at=OBSERVED_AT,
    observations=None,
):
    plan = make_plan(mode)
    symbol = plan.full_evaluation_symbols[0]
    return build_mode_oi_execution_evidence(
        mode=plan.mode,
        mode_lineage_sha256=plan.mode_lineage_sha256,
        canonical_symbol=symbol.canonical_symbol,
        observed_at=observed_at,
        observations=(
            make_oi_observations()
            if observations is None
            else observations
        ),
        request_invocation_count=1,
    )


def make_payload(trigger=OBSERVED_AT, **changes):
    values = {
        "trigger_candle_close_at": trigger,
        "score": 91,
        "trend": "UPTREND",
        "bos": True,
        "choch": False,
        "reference_price": 100.0,
        "reference_candle_at": trigger,
        "volume_ratio": 2.0,
        "volume_v2_status": "OK",
        "golden_zone": {
            "direction": "BULLISH",
            "levels": {"0.618": 99.0},
        },
    }
    values.update(changes)
    return build_mode_technical_evaluator_payload(**values)


def make_candidate(plan=None, rank=1, trigger=OBSERVED_AT):
    plan = make_plan() if plan is None else plan
    payload = make_payload(trigger)
    return build_mode_execution_candidate_row(
        plan=plan,
        symbol_plan=plan.full_evaluation_symbols[rank - 1],
        evaluator_payload=payload,
        trigger_candle_close_at=trigger,
    )


def make_outcome(
    plan,
    rank,
    kind=OUTCOME_NO_CANDIDATE,
    reason=REASON_NO_CANDIDATE,
):
    candidate = (
        make_candidate(plan, rank)
        if kind == OUTCOME_CANDIDATE
        else None
    )
    evaluator_hash = (
        candidate.payload_sha256
        if candidate is not None
        else None
    )
    timeframe_hashes = (sha(f"timeframe-{rank}"),)
    oi_hash = sha(f"oi-{rank}")
    if kind == OUTCOME_SKIPPED:
        evaluator_hash = None
        if reason in (
            REASON_CANDLE_BOUNDARY_EXCEPTION,
            REASON_CANDLE_EVIDENCE_INVALID,
        ):
            oi_hash = None
        if reason == REASON_CANDLE_BOUNDARY_EXCEPTION:
            timeframe_hashes = ()
    return ModeSymbolExecutionOutcomeV1(
        schema_version=MODE_SYMBOL_EXECUTION_OUTCOME_SCHEMA_VERSION,
        policy_version=MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
        mode=plan.mode,
        mode_lineage_sha256=plan.mode_lineage_sha256,
        canonical_symbol=(
            plan.full_evaluation_symbols[rank - 1].canonical_symbol
        ),
        full_evaluation_rank=rank,
        outcome_kind=kind,
        reason_code=reason,
        timeframe_evidence_sha256s=timeframe_hashes,
        oi_evidence_sha256=oi_hash,
        evaluator_payload_sha256=evaluator_hash,
        candidate_row=candidate,
    )


def build_result(plan, outcomes):
    oi_calls = sum(
        item.reason_code
        not in (
            REASON_CANDLE_BOUNDARY_EXCEPTION,
            REASON_CANDLE_EVIDENCE_INVALID,
        )
        for item in outcomes
    )
    evaluator_calls = sum(
        item.outcome_kind in (OUTCOME_CANDIDATE, OUTCOME_NO_CANDIDATE)
        or item.reason_code
        in (REASON_EVALUATOR_EXCEPTION, REASON_EVALUATOR_RESULT_INVALID)
        for item in outcomes
    )
    return build_mode_scan_execution_result(
        plan=plan,
        observed_at=OBSERVED_AT,
        outcomes=outcomes,
        actual_candle_call_count=sum(
            len(item.candle_fetches)
            for item in plan.full_evaluation_symbols
        ),
        actual_oi_call_count=oi_calls,
        actual_evaluator_invocation_count=evaluator_calls,
        actual_executor_ip_weight=0,
    )


def test_exact_public_dataclass_field_inventories():
    for cls, expected in PUBLIC_FIELDS.items():
        assert tuple(item.name for item in fields(cls)) == expected


def test_all_public_dataclasses_are_frozen_and_slotted():
    for cls in PUBLIC_FIELDS:
        assert is_dataclass(cls)
        assert cls.__dataclass_params__.frozen is True
        assert "__dict__" not in cls.__dict__


def test_exact_builder_signatures_are_keyword_only_without_defaults():
    for builder in BUILDERS:
        signature = inspect.signature(builder)
        assert signature.parameters
        for parameter in signature.parameters.values():
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
            assert parameter.default is inspect.Parameter.empty


def test_validation_error_is_exactly_sanitized():
    with pytest.raises(
        ModeScanExecutionEvidenceValidationError,
    ) as captured:
        ModeUtcCandleV1(
            schema_version="wrong",
            timeframe="1h",
            open_time="internal-secret",
            close_time="path/internal",
            open=1,
            high=1,
            low=1,
            close=1,
            volume=1,
        )
    assert str(captured.value) == "invalid mode scan execution evidence"


def test_engine_import_inventory_is_pure_and_authorized():
    source = Path(
        "engine/mode_scan_execution_evidence_v1.py"
    ).read_text()
    tree = ast.parse(source)
    project_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("engine.")
    }
    assert project_imports == {
        "engine.mode_data_plan_v1",
        "engine.mode_fetch_budget_cadence_v1",
        "engine.mode_profile_v1",
        "engine.mode_scan_execution_plan_v1",
    }
    prohibited = {
        "requests",
        "ccxt",
        "pandas",
        "numpy",
        "socket",
        "subprocess",
        "urllib",
    }
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported.isdisjoint(prohibited)


def test_engine_contains_no_canonical_mode_literals():
    tree = ast.parse(
        Path("engine/mode_scan_execution_evidence_v1.py").read_text()
    )
    strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    }
    assert strings.isdisjoint({"SWING", "INTRADAY", "SCALP"})


def test_engine_has_no_callback_or_cache_storage_api():
    source = Path(
        "engine/mode_scan_execution_evidence_v1.py"
    ).read_text()
    for forbidden in (
        "route_mode_scan(",
        "run_mode_validation_pipeline(",
        "scan_market(",
        "requests.",
        "fetch_ohlcv",
        "cache_lookup",
        "cache_write",
        "cache_store",
    ):
        assert forbidden not in source


def test_mapping_and_tuple_ownership_is_detached():
    evidence = make_timeframe_evidence()
    mapping = evidence.to_mapping()
    mapping["raw_candles"][0]["close"] = 999
    assert evidence.raw_candles[0].close != 999
    assert isinstance(evidence.raw_candles, tuple)


@pytest.mark.parametrize("timeframe", tuple(TIMEFRAME_SECONDS))
def test_all_supported_timeframes_create_canonical_candles(timeframe):
    opened = developing_open(OBSERVED_AT, timeframe)
    candle = make_candle(timeframe, opened)
    assert candle.timeframe == timeframe
    assert datetime.strptime(
        candle.close_time,
        "%Y-%m-%dT%H:%M:%SZ",
    ) - datetime.strptime(
        candle.open_time,
        "%Y-%m-%dT%H:%M:%SZ",
    ) == timedelta(seconds=TIMEFRAME_SECONDS[timeframe])


@pytest.mark.parametrize(
    "field,value",
    (
        ("open_time", "2026-07-30T06:00:00+00:00"),
        ("open_time", "2026-07-30T06:00:00.000Z"),
        ("open_time", "2026-02-30T06:00:00Z"),
        ("open_time", " 2026-07-30T06:00:00Z"),
        ("open_time", StringSubclass("2026-07-30T06:00:00Z")),
        ("open_time", EqualitySpoof()),
    ),
)
def test_candle_rejects_noncanonical_utc_timestamps(field, value):
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert_invalid(lambda: replace(candle, **{field: value}))


@pytest.mark.parametrize(
    "timeframe,open_time",
    (
        ("1d", "2026-07-30T01:00:00Z"),
        ("4h", "2026-07-30T02:00:00Z"),
        ("1h", "2026-07-30T06:01:00Z"),
        ("15m", "2026-07-30T06:10:00Z"),
        ("5m", "2026-07-30T06:02:00Z"),
        ("3m", "2026-07-30T06:01:00Z"),
    ),
)
def test_candle_rejects_misaligned_opening_boundaries(
    timeframe,
    open_time,
):
    opened = datetime.strptime(
        open_time,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    values = make_candle(timeframe, developing_open(OBSERVED_AT, timeframe))
    assert_invalid(
        lambda: replace(
            values,
            open_time=open_time,
            close_time=utc_text(
                opened + timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
            ),
        )
    )


def test_weekly_candle_requires_monday_alignment():
    valid = make_candle(
        "1w",
        datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    assert valid.open_time.startswith("2026-07-27")
    assert_invalid(
        lambda: replace(
            valid,
            open_time="2026-07-28T00:00:00Z",
            close_time="2026-08-04T00:00:00Z",
        )
    )


def test_candle_requires_exact_close_time_derivation():
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert_invalid(
        lambda: replace(candle, close_time="2026-07-30T08:00:00Z")
    )


def test_candle_rejects_unsupported_timeframe():
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert_invalid(lambda: replace(candle, timeframe="2h"))


@pytest.mark.parametrize("field,value", (("open", 0), ("high", -1), ("low", 0), ("close", float("nan"))))
def test_candle_rejects_invalid_ohlc(field, value):
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert_invalid(lambda: replace(candle, **{field: value}))


def test_candle_rejects_negative_volume():
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert_invalid(lambda: replace(candle, volume=-1))


def test_candle_normalizes_negative_zero_volume():
    candle = replace(
        make_candle(
            "1h",
            datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
        ),
        volume=-0.0,
    )
    assert candle.volume == 0.0
    assert str(candle.volume) == "0.0"


@pytest.mark.parametrize("field", ("open", "high", "low", "close", "volume"))
def test_candle_rejects_bool_numeric_values(field):
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert_invalid(lambda: replace(candle, **{field: True}))


@pytest.mark.parametrize("value", (float("nan"), float("inf"), -float("inf")))
def test_candle_rejects_nonfinite_volume(value):
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert_invalid(lambda: replace(candle, volume=value))


def test_candle_rejects_incoherent_high_and_low():
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert_invalid(lambda: replace(candle, high=99))
    assert_invalid(lambda: replace(candle, low=102))


def test_candle_mapping_is_deterministic_json_compatible():
    candle = make_candle(
        "1h",
        datetime(2026, 7, 30, 6, tzinfo=timezone.utc),
    )
    assert canonical_json(candle.to_mapping()) == canonical_json(
        candle.to_mapping()
    )


@pytest.mark.parametrize(
    "mode,optional",
    (
        ("SWING", False),
        ("INTRADAY", False),
        ("SCALP", True),
    ),
)
def test_timeframe_evidence_binds_all_mode_plan_rows(mode, optional):
    plan = make_plan(mode, optional=optional)
    for fetch in plan.full_evaluation_symbols[0].candle_fetches:
        evidence = build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=candles_for(fetch),
        )
        assert evidence.mode == plan.mode
        assert evidence.mode_lineage_sha256 == plan.mode_lineage_sha256
        assert evidence.timeframe == fetch.timeframe


def test_timeframe_evidence_rejects_hostile_plan_row_mutation():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    candles = candles_for(fetch)
    object.__setattr__(fetch, "closed_candle_limit", 51)
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=candles,
        )
    )


def test_timeframe_evidence_requires_exact_raw_count():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=candles_for(fetch)[:-1],
        )
    )


def test_timeframe_evidence_revalidates_closed_count():
    evidence = make_timeframe_evidence()
    assert_invalid(
        lambda: replace(
            evidence,
            closed_candle_count=evidence.closed_candle_count - 1,
        )
    )


def test_timeframe_evidence_requires_raw_equals_closed_plus_one():
    evidence = make_timeframe_evidence()
    assert (
        evidence.raw_fetch_limit
        == evidence.closed_candle_limit + 1
    )
    assert_invalid(
        lambda: replace(
            evidence,
            raw_fetch_limit=evidence.raw_fetch_limit + 1,
        )
    )


def test_timeframe_evidence_rejects_timestamp_reordering():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    candles = list(candles_for(fetch))
    candles[0], candles[1] = candles[1], candles[0]
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=candles,
        )
    )


def test_timeframe_evidence_rejects_duplicate_open_time():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    candles = list(candles_for(fetch))
    candles[1] = replace(
        candles[1],
        open_time=candles[0].open_time,
        close_time=candles[0].close_time,
    )
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=candles,
        )
    )


def test_timeframe_evidence_rejects_duplicate_close_time():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    candles = list(candles_for(fetch))
    object.__setattr__(candles[1], "close_time", candles[0].close_time)
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=candles,
        )
    )


def test_timeframe_evidence_rejects_interval_gap():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    candles = list(candles_for(fetch))
    shifted = datetime.strptime(
        candles[1].open_time,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc) + timedelta(
        seconds=TIMEFRAME_SECONDS[fetch.timeframe]
    )
    candles[1] = make_candle(fetch.timeframe, shifted, 1)
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=candles,
        )
    )


def test_timeframe_evidence_rejects_overlapping_intervals():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    candles = list(candles_for(fetch))
    candles[1] = replace(
        candles[1],
        open_time=candles[0].open_time,
        close_time=candles[0].close_time,
    )
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=candles,
        )
    )


def test_timeframe_evidence_rejects_observed_before_developing_open():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    candles = candles_for(fetch)
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=candles[-2].open_time,
            raw_candles=candles,
        )
    )


def test_timeframe_evidence_rejects_observed_at_developing_close():
    plan = make_plan()
    fetch = plan.full_evaluation_symbols[0].candle_fetches[0]
    candles = candles_for(fetch)
    assert_invalid(
        lambda: build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=candles[-1].close_time,
            raw_candles=candles,
        )
    )


def test_timeframe_evidence_marks_final_developing_row_dropped():
    evidence = make_timeframe_evidence()
    assert evidence.developing_candle_dropped is True
    assert_invalid(
        lambda: replace(evidence, developing_candle_dropped=False)
    )


def test_timeframe_evidence_last_closed_matches_developing_open():
    evidence = make_timeframe_evidence()
    assert (
        evidence.raw_candles[-2].close_time
        == evidence.raw_candles[-1].open_time
        == evidence.closed_candle_close_at
    )


def test_timeframe_evidence_closed_hash_is_exact():
    evidence = make_timeframe_evidence()
    expected = sha(
        [item.to_mapping() for item in evidence.raw_candles[:-1]]
    )
    assert evidence.closed_candles_sha256 == expected
    assert_invalid(
        lambda: replace(evidence, closed_candles_sha256=HASH_A)
    )


def test_timeframe_evidence_materializes_exact_cache_key():
    evidence = make_timeframe_evidence()
    cache = json.loads(evidence.cache_key_json)
    assert cache["mode"] == evidence.mode
    assert cache["canonical_symbol"] == evidence.canonical_symbol
    assert cache["timeframe"] == evidence.timeframe
    assert (
        cache["closed_candle_close_at"]
        == evidence.closed_candle_close_at
    )
    assert cache["cache_key_sha256"] == evidence.cache_key_sha256


@pytest.mark.parametrize(
    "field,value",
    (
        ("mode", "INTRADAY"),
        ("canonical_symbol", "FOREIGN/USDT"),
        ("timeframe", "1d"),
        ("closed_candle_close_at", "2026-07-29T00:00:00Z"),
        ("cache_key_sha256", HASH_A),
    ),
)
def test_timeframe_evidence_rejects_cache_key_parity_changes(
    field,
    value,
):
    evidence = make_timeframe_evidence()
    cache = json.loads(evidence.cache_key_json)
    cache[field] = value
    assert_invalid(
        lambda: replace(
            evidence,
            cache_key_json=canonical_json(cache),
        )
    )


def test_timeframe_evidence_hash_is_exact():
    evidence = make_timeframe_evidence()
    assert_invalid(lambda: replace(evidence, evidence_sha256=HASH_A))


def test_timeframe_evidence_contains_no_cache_storage_state():
    keys = set(make_timeframe_evidence().to_mapping())
    assert not keys.intersection(
        {"cache_hit", "cache_miss", "cache_value", "cache_storage"}
    )


def test_oi_evidence_accepts_canonical_observations():
    evidence = make_oi_evidence()
    assert evidence.period == "5m"
    assert evidence.observation_count == 3
    assert isinstance(evidence.observations, tuple)


def test_oi_evidence_requires_exact_period():
    evidence = make_oi_evidence()
    assert_invalid(lambda: replace(evidence, period="15m"))


@pytest.mark.parametrize("value", (0, 2, True))
def test_oi_evidence_requires_exact_one_invocation(value):
    plan = make_plan()
    symbol = plan.full_evaluation_symbols[0]
    assert_invalid(
        lambda: build_mode_oi_execution_evidence(
            mode=plan.mode,
            mode_lineage_sha256=plan.mode_lineage_sha256,
            canonical_symbol=symbol.canonical_symbol,
            observed_at=OBSERVED_AT,
            observations=make_oi_observations(),
            request_invocation_count=value,
        )
    )


def test_oi_evidence_requires_at_least_two_observations():
    assert_invalid(
        lambda: make_oi_evidence(
            observations=make_oi_observations(count=1)
        )
    )


def test_oi_evidence_rejects_more_than_one_thousand_observations():
    observations = make_oi_observations(
        count=1001,
        newest=OBSERVED_AT,
    )
    assert_invalid(
        lambda: make_oi_evidence(observations=observations)
    )


def test_oi_evidence_rejects_reordered_observations():
    observations = list(make_oi_observations())
    observations[0], observations[1] = (
        observations[1],
        observations[0],
    )
    assert_invalid(
        lambda: make_oi_evidence(observations=observations)
    )


def test_oi_evidence_rejects_duplicate_observation_times():
    observations = list(make_oi_observations())
    observations[1] = replace(
        observations[1],
        close_time=observations[0].close_time,
    )
    assert_invalid(
        lambda: make_oi_evidence(observations=observations)
    )


def test_oi_evidence_rejects_five_minute_gap():
    observations = list(make_oi_observations())
    observations[1] = replace(
        observations[1],
        close_time="2026-07-30T06:20:00Z",
    )
    assert_invalid(
        lambda: make_oi_evidence(observations=observations)
    )


def test_oi_evidence_rejects_future_observation():
    assert_invalid(
        lambda: make_oi_evidence(
            observed_at="2026-07-30T06:29:59Z"
        )
    )


@pytest.mark.parametrize(
    "observed_at,expected_age",
    (
        ("2026-07-30T06:30:00Z", 0),
        ("2026-07-30T06:35:00Z", 300),
    ),
)
def test_oi_evidence_accepts_age_boundaries(observed_at, expected_age):
    evidence = make_oi_evidence(observed_at=observed_at)
    assert evidence.newest_age_seconds == expected_age


def test_oi_evidence_rejects_age_above_300_seconds():
    assert_invalid(
        lambda: make_oi_evidence(
            observed_at="2026-07-30T06:35:01Z"
        )
    )


@pytest.mark.parametrize(
    "value",
    (-1, True, float("nan"), float("inf"), EqualitySpoof()),
)
def test_oi_observation_rejects_invalid_values(value):
    assert_invalid(
        lambda: ModeOiObservationV1(
            schema_version=MODE_OI_OBSERVATION_SCHEMA_VERSION,
            close_time="2026-07-30T06:30:00Z",
            open_interest=value,
        )
    )


def test_oi_observation_normalizes_negative_zero():
    observation = ModeOiObservationV1(
        schema_version=MODE_OI_OBSERVATION_SCHEMA_VERSION,
        close_time="2026-07-30T06:30:00Z",
        open_interest=-0.0,
    )
    assert str(observation.open_interest) == "0.0"


def test_oi_evidence_hashes_and_mapping_are_detached():
    evidence = make_oi_evidence()
    mapping = evidence.to_mapping()
    mapping["observations"][0]["open_interest"] = 0
    assert evidence.observations[0].open_interest != 0
    assert_invalid(lambda: replace(evidence, evidence_sha256=HASH_A))


def test_evaluator_payload_has_exact_nine_keys():
    payload = make_payload()
    assert set(payload.payload_copy()) == {
        "score",
        "trend",
        "bos",
        "choch",
        "reference_price",
        "reference_candle_at",
        "volume_ratio",
        "volume_v2_status",
        "golden_zone",
    }


@pytest.mark.parametrize("mutation", ("missing", "unknown"))
def test_evaluator_payload_rejects_nonexact_direct_json_keys(mutation):
    payload = make_payload()
    mapping = payload.payload_copy()
    if mutation == "missing":
        mapping.pop("trend")
    else:
        mapping["unknown"] = 1
    encoded = canonical_json(mapping)
    assert_invalid(
        lambda: replace(
            payload,
            payload_json=encoded,
            payload_sha256=sha(encoded),
        )
    )


@pytest.mark.parametrize("score", (0, 100, 50.5))
def test_evaluator_payload_accepts_score_boundaries(score):
    assert make_payload(score=score).payload_copy()["score"] == score


@pytest.mark.parametrize("score", (-1, 101, True, float("nan")))
def test_evaluator_payload_rejects_invalid_scores(score):
    assert_invalid(lambda: make_payload(score=score))


@pytest.mark.parametrize(
    "trend",
    ("", " UPTREND", "x" * 65, StringSubclass("UPTREND")),
)
def test_evaluator_payload_rejects_invalid_trend(trend):
    assert_invalid(lambda: make_payload(trend=trend))


@pytest.mark.parametrize("field", ("bos", "choch"))
def test_evaluator_payload_requires_exact_boolean_structure(field):
    assert_invalid(lambda: make_payload(**{field: 1}))


@pytest.mark.parametrize("value", (0, -1, True, float("inf")))
def test_evaluator_payload_requires_positive_reference_price(value):
    assert_invalid(lambda: make_payload(reference_price=value))


def test_evaluator_payload_requires_reference_trigger_time_parity():
    assert_invalid(
        lambda: make_payload(
            reference_candle_at="2026-07-30T06:29:59Z"
        )
    )


@pytest.mark.parametrize(
    "ratio,status",
    ((None, None), (0, "OK"), (2.5, "INSUFFICIENT_DATA")),
)
def test_evaluator_payload_accepts_optional_volume_fields(
    ratio,
    status,
):
    payload = make_payload(
        volume_ratio=ratio,
        volume_v2_status=status,
    ).payload_copy()
    assert payload["volume_ratio"] == ratio
    assert payload["volume_v2_status"] == status


@pytest.mark.parametrize(
    "field,value",
    (
        ("volume_ratio", -1),
        ("volume_ratio", True),
        ("volume_v2_status", ""),
        ("volume_v2_status", StringSubclass("OK")),
    ),
)
def test_evaluator_payload_rejects_invalid_optional_volume_fields(
    field,
    value,
):
    assert_invalid(lambda: make_payload(**{field: value}))


def test_evaluator_payload_accepts_canonical_golden_zone_dict():
    payload = make_payload()
    assert payload.payload_copy()["golden_zone"]["direction"] == "BULLISH"


@pytest.mark.parametrize(
    "golden_zone",
    (
        ("not", "a", "dict"),
        DictSubclass({"direction": "BULLISH"}),
        {"values": (1, 2)},
        {"value": float("nan")},
    ),
)
def test_evaluator_payload_rejects_noncanonical_golden_zone(
    golden_zone,
):
    assert_invalid(lambda: make_payload(golden_zone=golden_zone))


@pytest.mark.parametrize(
    "identity_key",
    (
        "candidate_id",
        "symbol",
        "mode",
        "mode_lineage_sha256",
        "payload_sha256",
    ),
)
def test_evaluator_payload_rejects_nested_identity_fields(identity_key):
    assert_invalid(
        lambda: make_payload(
            golden_zone={"nested": {identity_key: "spoof"}}
        )
    )


def test_evaluator_payload_json_hash_and_copy_are_detached():
    payload = make_payload()
    assert payload.payload_sha256 == sha(payload.payload_json)
    first = payload.payload_copy()
    first["golden_zone"]["direction"] = "CHANGED"
    assert (
        payload.payload_copy()["golden_zone"]["direction"]
        == "BULLISH"
    )


def test_e2_candidate_id_format_and_determinism():
    plan = make_plan()
    payload = make_payload()
    values = {
        "plan_sha256": plan.plan_sha256,
        "mode": plan.mode,
        "mode_lineage_sha256": plan.mode_lineage_sha256,
        "canonical_symbol":
            plan.full_evaluation_symbols[0].canonical_symbol,
        "reference_candle_at": payload.trigger_candle_close_at,
        "payload_sha256": payload.payload_sha256,
    }
    first = build_e2_candidate_id(**values)
    second = build_e2_candidate_id(**values)
    assert first == second
    assert first.startswith("e2c1:")
    assert len(first) == 69


@pytest.mark.parametrize(
    "field,value",
    (
        ("plan_sha256", HASH_A),
        ("canonical_symbol", "FOREIGN/USDT"),
        ("reference_candle_at", "2026-07-30T06:31:00Z"),
        ("payload_sha256", HASH_B),
    ),
)
def test_every_non_lineage_candidate_id_digest_input_changes_id(
    field,
    value,
):
    plan = make_plan()
    payload = make_payload()
    values = {
        "plan_sha256": plan.plan_sha256,
        "mode": plan.mode,
        "mode_lineage_sha256": plan.mode_lineage_sha256,
        "canonical_symbol":
            plan.full_evaluation_symbols[0].canonical_symbol,
        "reference_candle_at": payload.trigger_candle_close_at,
        "payload_sha256": payload.payload_sha256,
    }
    original = build_e2_candidate_id(**values)
    values[field] = value
    assert build_e2_candidate_id(**values) != original


def test_candidate_id_contains_no_random_or_clock_dependency():
    source = inspect.getsource(build_e2_candidate_id)
    assert "random" not in source
    assert "uuid" not in source
    assert "datetime" not in source


def test_candidate_row_exact_plan_and_symbol_binding():
    plan = make_plan()
    row = make_candidate(plan)
    assert row.plan_sha256 == plan.plan_sha256
    assert row.symbol == plan.full_evaluation_symbols[0].canonical_symbol
    assert row.mode_lineage_sha256 == plan.mode_lineage_sha256


def test_candidate_row_rejects_hostile_outer_plan_mutation():
    plan = make_plan()
    symbol = plan.full_evaluation_symbols[0]
    payload = make_payload()
    object.__setattr__(plan, "retry_count", 1)
    assert_invalid(
        lambda: build_mode_execution_candidate_row(
            plan=plan,
            symbol_plan=symbol,
            evaluator_payload=payload,
            trigger_candle_close_at=OBSERVED_AT,
        )
    )


def test_candidate_row_rejects_symbol_plan_from_another_plan():
    first = make_plan("SWING")
    second = make_plan("INTRADAY")
    assert_invalid(
        lambda: build_mode_execution_candidate_row(
            plan=first,
            symbol_plan=second.full_evaluation_symbols[0],
            evaluator_payload=make_payload(),
            trigger_candle_close_at=OBSERVED_AT,
        )
    )


def test_candidate_row_rejects_trigger_payload_mismatch():
    plan = make_plan()
    assert_invalid(
        lambda: build_mode_execution_candidate_row(
            plan=plan,
            symbol_plan=plan.full_evaluation_symbols[0],
            evaluator_payload=make_payload(),
            trigger_candle_close_at="2026-07-30T06:31:00Z",
        )
    )


def test_candidate_scanner_row_has_exact_five_keys():
    row = make_candidate()
    scanner_row = row.to_scanner_row()
    assert list(scanner_row) == [
        "candidate_id",
        "mode",
        "symbol",
        "mode_lineage_sha256",
        "payload",
    ]
    assert len(scanner_row) == 5


def test_candidate_scanner_row_payload_is_detached():
    row = make_candidate()
    scanner_row = row.to_scanner_row()
    scanner_row["payload"]["score"] = 0
    assert row.payload_copy()["score"] == 91


def test_candidate_id_is_router_safe_identifier_compatible():
    candidate_id = make_candidate().candidate_id
    assert len(candidate_id) <= 128
    assert all(
        character.isalnum() or character in "._:+-"
        for character in candidate_id
    )


@pytest.mark.parametrize(
    "kind,reason",
    (
        (OUTCOME_CANDIDATE, REASON_CANDIDATE_ACCEPTED),
        (OUTCOME_NO_CANDIDATE, REASON_NO_CANDIDATE),
        (
            OUTCOME_SKIPPED,
            REASON_CANDLE_BOUNDARY_EXCEPTION,
        ),
    ),
)
def test_all_three_outcome_kinds_construct(kind, reason):
    plan = make_plan()
    outcome = make_outcome(plan, 1, kind, reason)
    assert outcome.outcome_kind == kind
    assert outcome.reason_code == reason


@pytest.mark.parametrize(
    "reason",
    (
        REASON_CANDLE_BOUNDARY_EXCEPTION,
        REASON_CANDLE_EVIDENCE_INVALID,
        REASON_OI_BOUNDARY_EXCEPTION,
        REASON_OI_EVIDENCE_INVALID,
        REASON_EVALUATOR_EXCEPTION,
        REASON_EVALUATOR_RESULT_INVALID,
    ),
)
def test_every_skip_reason_constructs(reason):
    plan = make_plan()
    assert make_outcome(
        plan,
        1,
        OUTCOME_SKIPPED,
        reason,
    ).reason_code == reason


@pytest.mark.parametrize(
    "kind,reason",
    (
        (OUTCOME_CANDIDATE, REASON_NO_CANDIDATE),
        (OUTCOME_NO_CANDIDATE, REASON_CANDIDATE_ACCEPTED),
        (OUTCOME_SKIPPED, REASON_NO_CANDIDATE),
        ("UNKNOWN", REASON_CANDIDATE_ACCEPTED),
    ),
)
def test_outcome_rejects_invalid_kind_reason_pairs(kind, reason):
    plan = make_plan()
    assert_invalid(lambda: make_outcome(plan, 1, kind, reason))


def test_outcome_rejects_duplicate_timeframe_hashes():
    plan = make_plan()
    outcome = make_outcome(plan, 1)
    assert_invalid(
        lambda: replace(
            outcome,
            timeframe_evidence_sha256s=(HASH_A, HASH_A),
        )
    )


def test_outcome_rejects_bool_or_nonpositive_rank():
    plan = make_plan()
    outcome = make_outcome(plan, 1)
    assert_invalid(
        lambda: replace(outcome, full_evaluation_rank=True)
    )
    assert_invalid(lambda: replace(outcome, full_evaluation_rank=0))


def test_candidate_outcome_requires_candidate_and_hash_parity():
    plan = make_plan()
    outcome = make_outcome(
        plan,
        1,
        OUTCOME_CANDIDATE,
        REASON_CANDIDATE_ACCEPTED,
    )
    assert_invalid(lambda: replace(outcome, candidate_row=None))
    assert_invalid(
        lambda: replace(outcome, evaluator_payload_sha256=HASH_A)
    )


def test_no_candidate_outcome_rejects_candidate_presence():
    plan = make_plan()
    outcome = make_outcome(plan, 1)
    assert_invalid(
        lambda: replace(outcome, candidate_row=make_candidate(plan))
    )


def test_evaluator_failure_requires_completed_oi_evidence():
    plan = make_plan()
    outcome = make_outcome(
        plan,
        1,
        OUTCOME_SKIPPED,
        REASON_EVALUATOR_EXCEPTION,
    )
    assert_invalid(
        lambda: replace(outcome, oi_evidence_sha256=None)
    )


def test_result_derives_exact_plan_counts_and_symbol_order():
    plan = make_plan(count=3)
    outcomes = tuple(
        make_outcome(plan, rank)
        for rank in range(1, 4)
    )
    result = build_result(plan, outcomes)
    assert result.planned_symbol_order == tuple(
        item.canonical_symbol
        for item in plan.full_evaluation_symbols
    )
    assert result.planned_timeframe_counts == tuple(
        len(item.candle_fetches)
        for item in plan.full_evaluation_symbols
    )
    assert result.planned_candle_call_count == sum(
        result.planned_timeframe_counts
    )
    assert result.planned_oi_call_count == 3
    assert result.planned_evaluator_invocation_count == 3


def test_result_subtracts_market_level_budget_exactly():
    plan = make_plan(count=2)
    outcomes = (make_outcome(plan, 1), make_outcome(plan, 2))
    result = build_result(plan, outcomes)
    budget = plan.fetch_budget_copy()
    assert result.planned_executor_request_count == (
        budget["total_request_count"]
        - budget["market_level_request_count"]
    )
    assert result.planned_executor_ip_weight == (
        budget["total_ip_weight"]
        - budget["market_level_ip_weight"]
    )
    assert result.planned_executor_request_count == (
        result.planned_candle_call_count
        + result.planned_oi_call_count
    )


@pytest.mark.parametrize(
    "field",
    (
        "actual_candle_call_count",
        "actual_oi_call_count",
        "actual_evaluator_invocation_count",
        "actual_executor_request_count",
        "actual_executor_ip_weight",
    ),
)
def test_result_rejects_actual_count_or_weight_overflow(field):
    plan = make_plan()
    result = build_result(plan, (make_outcome(plan, 1),))
    maximum = {
        "actual_candle_call_count":
            result.planned_candle_call_count,
        "actual_oi_call_count": result.planned_oi_call_count,
        "actual_evaluator_invocation_count":
            result.planned_evaluator_invocation_count,
        "actual_executor_request_count":
            result.planned_executor_request_count,
        "actual_executor_ip_weight":
            result.planned_executor_ip_weight,
    }[field]
    assert_invalid(lambda: replace(result, **{field: maximum + 1}))


def test_result_rejects_nonzero_or_bool_retry():
    plan = make_plan()
    result = build_result(plan, (make_outcome(plan, 1),))
    assert_invalid(lambda: replace(result, retry_count=1))
    assert_invalid(lambda: replace(result, retry_count=False))


def test_result_requires_one_ordered_outcome_per_symbol():
    plan = make_plan(count=2)
    first = make_outcome(plan, 1)
    second = make_outcome(plan, 2)
    assert_invalid(
        lambda: build_result(plan, (first,))
    )
    assert_invalid(
        lambda: build_result(plan, (second, first))
    )


def test_result_reconciles_outcome_counts():
    plan = make_plan(count=3)
    outcomes = (
        make_outcome(
            plan,
            1,
            OUTCOME_CANDIDATE,
            REASON_CANDIDATE_ACCEPTED,
        ),
        make_outcome(plan, 2),
        make_outcome(
            plan,
            3,
            OUTCOME_SKIPPED,
            REASON_CANDLE_EVIDENCE_INVALID,
        ),
    )
    result = build_result(plan, outcomes)
    assert (
        result.candidate_count,
        result.no_candidate_count,
        result.skipped_count,
    ) == (1, 1, 1)
    assert_invalid(lambda: replace(result, skipped_count=0))


def test_result_reconciles_evaluator_stage_invocations():
    plan = make_plan(count=2)
    outcomes = (
        make_outcome(plan, 1),
        make_outcome(
            plan,
            2,
            OUTCOME_SKIPPED,
            REASON_EVALUATOR_RESULT_INVALID,
        ),
    )
    result = build_result(plan, outcomes)
    assert result.actual_evaluator_invocation_count == 2
    assert_invalid(
        lambda: replace(
            result,
            actual_evaluator_invocation_count=1,
        )
    )


def test_result_reconciles_oi_stage_invocations():
    plan = make_plan(count=2)
    outcomes = (
        make_outcome(
            plan,
            1,
            OUTCOME_SKIPPED,
            REASON_CANDLE_BOUNDARY_EXCEPTION,
        ),
        make_outcome(
            plan,
            2,
            OUTCOME_SKIPPED,
            REASON_OI_BOUNDARY_EXCEPTION,
        ),
    )
    result = build_result(plan, outcomes)
    assert result.actual_oi_call_count == 1
    assert_invalid(
        lambda: replace(result, actual_oi_call_count=2)
    )


def test_result_candidate_order_survives_skips_and_no_candidate():
    plan = make_plan(count=3)
    outcomes = (
        make_outcome(
            plan,
            1,
            OUTCOME_SKIPPED,
            REASON_CANDLE_EVIDENCE_INVALID,
        ),
        make_outcome(plan, 2),
        make_outcome(
            plan,
            3,
            OUTCOME_CANDIDATE,
            REASON_CANDIDATE_ACCEPTED,
        ),
    )
    result = build_result(plan, outcomes)
    assert tuple(item.symbol for item in result.candidates) == (
        plan.full_evaluation_symbols[2].canonical_symbol,
    )


def test_result_rejects_duplicate_candidate_identity():
    plan = make_plan(count=2)
    first = make_outcome(
        plan,
        1,
        OUTCOME_CANDIDATE,
        REASON_CANDIDATE_ACCEPTED,
    )
    second = make_outcome(
        plan,
        2,
        OUTCOME_CANDIDATE,
        REASON_CANDIDATE_ACCEPTED,
    )
    object.__setattr__(
        second.candidate_row,
        "candidate_id",
        first.candidate_row.candidate_id,
    )
    assert_invalid(lambda: build_result(plan, (first, second)))


def test_result_rejects_duplicate_candidate_symbol():
    plan = make_plan(count=2)
    first = make_outcome(
        plan,
        1,
        OUTCOME_CANDIDATE,
        REASON_CANDIDATE_ACCEPTED,
    )
    second = make_outcome(
        plan,
        2,
        OUTCOME_CANDIDATE,
        REASON_CANDIDATE_ACCEPTED,
    )
    object.__setattr__(
        second.candidate_row,
        "symbol",
        first.candidate_row.symbol,
    )
    assert_invalid(lambda: build_result(plan, (first, second)))


def test_result_replay_and_hash_are_deterministic():
    plan = make_plan(count=2)
    outcomes = (make_outcome(plan, 1), make_outcome(plan, 2))
    first = build_result(plan, outcomes)
    second = build_result(plan, outcomes)
    assert first.to_mapping() == second.to_mapping()
    assert first.execution_sha256 == second.execution_sha256
    assert_invalid(lambda: replace(first, execution_sha256=HASH_A))


def test_result_mapping_is_deeply_detached():
    plan = make_plan()
    result = build_result(plan, (make_outcome(plan, 1),))
    mapping = result.to_mapping()
    mapping["outcomes"][0]["canonical_symbol"] = "CHANGED/USDT"
    assert (
        result.outcomes[0].canonical_symbol
        != "CHANGED/USDT"
    )


def test_result_has_zero_validation_live_price_and_production_fields():
    result = build_result(
        make_plan(),
        (make_outcome(make_plan(), 1),),
    )
    serialized = canonical_json(result.to_mapping()).casefold()
    for forbidden in (
        "validation_pipeline",
        "live_price",
        "production",
        "publication",
        "telegram",
    ):
        assert forbidden not in serialized
