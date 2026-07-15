"""Frozen RED tests for Phase 08 Shadow Release progress and readiness."""

from __future__ import annotations

import copy

import pytest

from engine.shadow_release_contract_v1 import build_shadow_run_contract
from engine.shadow_release_progress_v1 import (
    MINIMUM_OBSERVED_RUNTIME_SPAN_DAYS,
    MINIMUM_SUCCESSFUL_MATCHES_PER_ENABLED_MODE,
    MINIMUM_SUCCESSFUL_MATCH_TOTAL,
    MINIMUM_UNIQUE_EVALUATION_CYCLES_PER_ENABLED_MODE,
    SHADOW_RELEASE_PROGRESS_CAPITAL_EXPOSURE,
    SHADOW_RELEASE_PROGRESS_CLASSIFICATION,
    SHADOW_RELEASE_PROGRESS_EXECUTION_BOUNDARY,
    SHADOW_RELEASE_PROGRESS_ORDER_EXECUTION,
    SHADOW_RELEASE_PROGRESS_SCHEMA_NAME,
    SHADOW_RELEASE_PROGRESS_SCHEMA_VERSION,
    ShadowReleaseProgressError,
    build_shadow_release_progress,
    validate_shadow_release_progress,
)


MISMATCH_CODES = (
    "DECISION_MISMATCH",
    "PUBLICATION_MISMATCH",
    "LIFECYCLE_MISMATCH",
    "NO_TRADE_MISMATCH",
    "NONDETERMINISM_DETECTED",
    "EVIDENCE_HASH_MISMATCH",
)
FAILURE_CODES = (
    "INPUT_CONTRACT_REJECTED",
    "SOURCE_AUTHORITY_MISSING",
    "COMPONENT_VERSION_UNSUPPORTED",
    "SHADOW_EXECUTION_FAILED",
    "ARTIFACT_PUBLICATION_FAILED",
    "ROOT_ISOLATION_VIOLATION",
    "IDENTITY_COLLISION",
    "CONCURRENCY_CONFLICT",
)


def source_publication_ref(mode="SCALP", **overrides):
    value = {
        "signal_id": "SCP-20260716-001",
        "delivery_id": "delivery-001",
        "mode": mode,
        "published_at": "2026-07-16T12:00:00Z",
        "source_payload_hash": "a" * 64,
    }
    value.update(overrides)
    return value


def lifecycle(*, no_trade=False, **overrides):
    value = {
        "publication": "NO_TRADE" if no_trade else "PUBLISHED",
        "entry_eligibility": "NOT_APPLICABLE" if no_trade else "ELIGIBLE",
        "cancellation": None,
        "entry_touch": "NOT_APPLICABLE" if no_trade else "NOT_OBSERVED",
        "tp_sl_ordering": "NOT_APPLICABLE",
        "acknowledgment": None,
        "terminal_state": "NO_TRADE" if no_trade else "OBSERVING",
    }
    value.update(overrides)
    return value


def semantic_projection(*, mode="SCALP", no_trade=False, **overrides):
    value = {
        "validated_pipeline": {"final_top5": [{"symbol": "BTCUSDT"}]},
        "outcome_snapshot": {"candidates": ["BTCUSDT"]},
        "watchlist": {"setups": [{"rank": 1, "symbol": "BTCUSDT"}]},
        "pre_delivery": {"disposition": "NO_TRADE" if no_trade else "PUBLISHED"},
        "tradingview_watchlist": "" if no_trade else "BTCUSDT",
        "pine_bridge": {} if no_trade else {"symbol": "BTCUSDT"},
        "pine_delivery_payload": "" if no_trade else "BTCUSDT,LONG",
        "publication": None if no_trade else source_publication_ref(mode),
        "lifecycle": lifecycle(no_trade=no_trade),
    }
    value.update(overrides)
    return value


def source_envelope(
    *,
    evaluation_id="evaluation-000",
    mode="SCALP",
    day=1,
    expected_hash="e" * 64,
    no_trade=False,
):
    stamp = f"2026-07-{day:02d}T12:00:00Z"
    projection = semantic_projection(mode=mode, no_trade=no_trade)
    return {
        "schema_version": 1,
        "schema_name": "shadow-release-input",
        "classification": "SHADOW_RELEASE",
        "execution_boundary": (
            "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
        ),
        "source_commit": "b" * 40,
        "source_evaluation_id": evaluation_id,
        "mode": mode,
        "market_identity": {
            "venue": "BINANCE_FUTURES_PUBLIC",
            "symbol": "BTCUSDT",
            "interval": "5m",
            "market_data_source": "PUBLIC_CLOSED_CANDLE_CAPTURE",
            "market_input_hash": "c" * 64,
        },
        "captured_at": stamp,
        "evaluation_started_at": stamp,
        "evaluation_completed_at": stamp,
        "serialized_inputs": {
            "scanner_results": [{"symbol": "BTCUSDT"}],
            "open_interest": {"BTCUSDT": {"change_pct": 1.0}},
            "validator_response": {"content": "approved", "usage": {}},
            "closed_candles": {"BTCUSDT": []},
        },
        "serialized_input_hash": "d" * 64,
        "expected_decision": projection,
        "expected_decision_hash": expected_hash,
        "source_publication_ref": (
            None if no_trade else source_publication_ref(mode)
        ),
        "signal_geometry": (
            None
            if no_trade
            else {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "entry_zone": {"min": 100.0, "max": 102.0},
                "stop_loss": 95.0,
                "take_profit": {"tp1": 110.0, "tp2": 120.0},
                "valid_until": "2026-07-31T13:00:00Z",
            }
        ),
        "lifecycle_trace": lifecycle(no_trade=no_trade),
        "outcome_kind": "NO_TRADE" if no_trade else "PUBLISHED_SIGNAL",
    }


def completed_run(
    *,
    evaluation_id="evaluation-000",
    mode="SCALP",
    day=1,
    expected_hash="e" * 64,
    no_trade=False,
    observed=None,
    failure=None,
):
    envelope = source_envelope(
        evaluation_id=evaluation_id,
        mode=mode,
        day=day,
        expected_hash=expected_hash,
        no_trade=no_trade,
    )
    return build_shadow_run_contract(
        source_envelope=envelope,
        observed_decision=(
            copy.deepcopy(envelope["expected_decision"])
            if observed is None
            else observed
        ),
        component_versions={
            "master_engine": "master-engine-v4",
            "validated_pipeline": "validated-pipeline-v4",
            "pre_delivery": "pre-delivery-v4",
            "shadow_contract": "shadow-release-contract-v1",
            "shadow_runner": "shadow-release-runner-v1",
        },
        started_at=f"2026-07-{day:02d}T12:00:01Z",
        completed_at=f"2026-07-{day:02d}T12:00:03Z",
        failure=failure,
    )


def build_progress(*, enabled_modes=("SCALP",), runs=(), defects=0, **overrides):
    value = {
        "enabled_modes": list(enabled_modes),
        "completed_runs": list(runs),
        "critical_defect_count": defects,
    }
    value.update(overrides)
    return build_shadow_release_progress(**value)


def ready_runs(*, mode="SCALP", cycle_count=100, days=True):
    return [
        completed_run(
            evaluation_id=f"evaluation-{index:03d}",
            mode=mode,
            day=1 + (index % 15) if days else 1,
        )
        for index in range(cycle_count)
    ]


def test_frozen_progress_constants_and_readiness_thresholds():
    assert SHADOW_RELEASE_PROGRESS_SCHEMA_VERSION == 1
    assert SHADOW_RELEASE_PROGRESS_SCHEMA_NAME == "shadow-release-progress"
    assert SHADOW_RELEASE_PROGRESS_CLASSIFICATION == "SHADOW_RELEASE"
    assert SHADOW_RELEASE_PROGRESS_EXECUTION_BOUNDARY == (
        "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
    )
    assert SHADOW_RELEASE_PROGRESS_CAPITAL_EXPOSURE == "NONE"
    assert SHADOW_RELEASE_PROGRESS_ORDER_EXECUTION == "PROHIBITED"
    assert MINIMUM_SUCCESSFUL_MATCH_TOTAL == 100
    assert MINIMUM_SUCCESSFUL_MATCHES_PER_ENABLED_MODE == 30
    assert MINIMUM_UNIQUE_EVALUATION_CYCLES_PER_ENABLED_MODE == 30
    assert MINIMUM_OBSERVED_RUNTIME_SPAN_DAYS == 14


def test_progress_has_closed_derived_schema_and_validates_its_own_output():
    result = build_progress(runs=[completed_run()])

    assert set(result) == {
        "schema_version",
        "schema_name",
        "classification",
        "execution_boundary",
        "capital_exposure",
        "order_execution",
        "position_authority",
        "enabled_modes",
        "completed_run_total",
        "official_serialized_run_total",
        "successful_match_total",
        "match_count",
        "mismatch_count",
        "failed_count",
        "outcome_count_by_kind",
        "outcome_count_by_state",
        "successful_match_count_by_enabled_mode",
        "unique_evaluation_cycle_count_by_enabled_mode",
        "evaluation_coverage_by_mode",
        "official_shadow_run_identities",
        "mismatch_count_by_primary_code",
        "failure_count_by_primary_code",
        "observed_runtime_span_days",
        "critical_defect_count",
        "evidence_incomplete_count",
        "shadow_release_readiness",
        "content_hash",
    }
    assert result["classification"] == "SHADOW_RELEASE"
    assert result["execution_boundary"] == (
        "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
    )
    assert result["capital_exposure"] == "NONE"
    assert result["order_execution"] == "PROHIBITED"
    assert result["position_authority"] == "NONE"
    assert validate_shadow_release_progress(result) == result


def test_preserves_unique_official_serialized_identity_and_market_authority():
    run = completed_run()
    result = build_progress(runs=[run])

    assert result["official_shadow_run_identities"] == [
        {
            "shadow_run_id": run["shadow_run_id"],
            "signal_id": "SCP-20260716-001",
            "delivery_id": "delivery-001",
            "source_evaluation_id": "evaluation-000",
            "mode": "SCALP",
            "market_identity": run["market_identity"],
            "content_hash": run["content_hash"],
        }
    ]


def test_exact_duplicate_completed_evidence_is_deduplicated_but_conflict_fails():
    run = completed_run()
    result = build_progress(runs=[run, copy.deepcopy(run)])
    assert result["completed_run_total"] == 1

    conflicting = completed_run(
        evaluation_id="evaluation-000",
        day=2,
    )
    assert conflicting["shadow_run_id"] == run["shadow_run_id"]
    with pytest.raises(ShadowReleaseProgressError):
        build_progress(runs=[run, conflicting])


def test_aggregates_match_mismatch_and_failed_evidence_by_frozen_codes():
    matched = completed_run(evaluation_id="match")
    mismatched = completed_run(
        evaluation_id="mismatch",
        observed=semantic_projection(
            mode="SCALP", validated_pipeline={"final_top5": []}
        ),
    )
    failed = completed_run(
        evaluation_id="failed",
        failure={
            "primary_code": "SHADOW_EXECUTION_FAILED",
            "component": "observed_adapter",
            "message": "adapter execution failed",
        },
    )
    result = build_progress(runs=[failed, mismatched, matched])

    assert result["completed_run_total"] == 3
    assert result["match_count"] == 1
    assert result["mismatch_count"] == 1
    assert result["failed_count"] == 1
    assert result["successful_match_total"] == 1
    assert result["mismatch_count_by_primary_code"] == {
        code: int(code == "DECISION_MISMATCH") for code in MISMATCH_CODES
    }
    assert result["failure_count_by_primary_code"] == {
        code: int(code == "SHADOW_EXECUTION_FAILED") for code in FAILURE_CODES
    }
    assert result["critical_defect_count"] == 1
    assert result["shadow_release_readiness"] is False


def test_no_trade_match_counts_evaluation_coverage_not_successful_published_runs():
    result = build_progress(
        runs=[completed_run(evaluation_id="no-trade", no_trade=True)]
    )

    coverage = result["evaluation_coverage_by_mode"]["SCALP"]
    assert result["completed_run_total"] == 1
    assert result["official_serialized_run_total"] == 0
    assert result["successful_match_total"] == 0
    assert coverage["unique_evaluation_cycle_count"] == 1
    assert coverage["no_trade_cycle_count"] == 1
    assert coverage["lifecycle_surface_count"]["no_trade"] == 1


def test_lifecycle_coverage_is_recorded_without_mutating_lifecycle_evidence():
    run = completed_run()
    original = copy.deepcopy(run)
    result = build_progress(runs=[run])

    assert result["evaluation_coverage_by_mode"]["SCALP"][
        "lifecycle_surface_count"
    ] == {
        "publication": 1,
        "entry_eligibility": 1,
        "cancellation": 1,
        "entry_touch": 1,
        "tp_sl_ordering": 1,
        "acknowledgment": 1,
        "no_trade": 0,
        "terminal_state": 1,
    }
    assert run == original


@pytest.mark.parametrize(
    "enabled_modes",
    [[], ["SCALP", "SCALP"], ["scalp"], ["UNKNOWN"]],
)
def test_enabled_modes_are_explicit_unique_and_canonical(enabled_modes):
    with pytest.raises(ShadowReleaseProgressError):
        build_progress(enabled_modes=enabled_modes)


def test_disabled_mode_evidence_does_not_satisfy_an_enabled_mode_gate():
    result = build_progress(
        enabled_modes=["SCALP"], runs=ready_runs(mode="INTRADAY")
    )

    assert result["successful_match_total"] == 100
    assert result["successful_match_count_by_enabled_mode"] == {"SCALP": 0}
    assert result["shadow_release_readiness"] is False


def test_all_readiness_gates_pass_at_the_exact_frozen_boundary():
    result = build_progress(runs=ready_runs())

    assert result["successful_match_total"] == 100
    assert result["successful_match_count_by_enabled_mode"] == {"SCALP": 100}
    assert result["unique_evaluation_cycle_count_by_enabled_mode"] == {
        "SCALP": 100
    }
    assert result["observed_runtime_span_days"] == 14
    assert result["mismatch_count"] == 0
    assert result["critical_defect_count"] == 0
    assert result["evidence_incomplete_count"] == 0
    assert result["shadow_release_readiness"] is True
    assert result["capital_exposure"] == "NONE"
    assert result["order_execution"] == "PROHIBITED"


@pytest.mark.parametrize(
    "runs,defects",
    [
        (ready_runs()[:-1], 0),
        (ready_runs(days=False), 0),
        (ready_runs(), 1),
    ],
)
def test_each_total_span_or_critical_defect_gate_blocks_readiness(runs, defects):
    assert build_progress(runs=runs, defects=defects)[
        "shadow_release_readiness"
    ] is False


def test_unique_evaluation_cycle_gate_blocks_even_with_100_matches():
    runs = [
        completed_run(
            evaluation_id=f"evaluation-{index % 29:03d}",
            expected_hash=f"{index:064x}",
            day=1 + (index % 15),
        )
        for index in range(100)
    ]
    result = build_progress(runs=runs)

    assert result["successful_match_total"] == 100
    assert result["unique_evaluation_cycle_count_by_enabled_mode"] == {
        "SCALP": 29
    }
    assert result["shadow_release_readiness"] is False


def test_mismatch_is_completed_evidence_and_blocks_readiness_at_zero_threshold():
    runs = ready_runs()
    runs[-1] = completed_run(
        evaluation_id="evaluation-099",
        day=10,
        observed=semantic_projection(
            mode="SCALP", validated_pipeline={"final_top5": []}
        ),
    )
    result = build_progress(runs=runs)

    assert result["mismatch_count"] == 1
    assert result["failed_count"] == 0
    assert result["critical_defect_count"] == 1
    assert result["shadow_release_readiness"] is False


def test_generic_failed_evidence_is_visible_but_has_no_separate_zero_failure_gate():
    failed = completed_run(
        evaluation_id="failed-extra",
        day=15,
        failure={
            "primary_code": "SHADOW_EXECUTION_FAILED",
            "component": "observed_adapter",
            "message": "adapter execution failed",
        },
    )
    result = build_progress(runs=ready_runs() + [failed])

    assert result["failed_count"] == 1
    assert result["failure_count_by_primary_code"]["SHADOW_EXECUTION_FAILED"] == 1
    assert result["critical_defect_count"] == 0
    assert result["shadow_release_readiness"] is True


def test_root_isolation_failure_is_critical_and_blocks_readiness():
    failed = completed_run(
        evaluation_id="root-failure",
        failure={
            "primary_code": "ROOT_ISOLATION_VIOLATION",
            "component": "shadow_artifact",
            "message": "root isolation violation",
        },
    )
    result = build_progress(runs=ready_runs() + [failed])

    assert result["critical_defect_count"] == 1
    assert result["shadow_release_readiness"] is False


@pytest.mark.parametrize("defects", [-1, True, 1.0, "1"])
def test_explicit_critical_defects_are_nonnegative_integers(defects):
    with pytest.raises(ShadowReleaseProgressError):
        build_progress(defects=defects)


def test_readiness_is_derived_and_caller_cannot_supply_content_or_readiness():
    with pytest.raises(ShadowReleaseProgressError):
        build_progress(shadow_release_readiness=True)
    with pytest.raises(ShadowReleaseProgressError):
        build_progress(content_hash="0" * 64)


def test_progress_is_deterministic_across_input_order_and_content_changes():
    runs = [
        completed_run(evaluation_id="first", day=1),
        completed_run(evaluation_id="second", day=15),
    ]
    first = build_progress(runs=runs)
    second = build_progress(runs=list(reversed(runs)))
    changed = build_progress(
        runs=[
            runs[0],
            completed_run(evaluation_id="second", day=15, mode="INTRADAY"),
        ]
    )

    assert first == second
    assert first["content_hash"] == second["content_hash"]
    assert first["content_hash"] != changed["content_hash"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda run: run.__setitem__("content_hash", "0" * 64),
        lambda run: run.__setitem__("classification", "PAPER_SIGNAL"),
        lambda run: run.__setitem__("incomplete", True),
        lambda run: run.__setitem__(
            "exchange_credentials", {"token": "forbidden"}
        ),
    ],
)
def test_rejects_incomplete_nonshadow_and_forbidden_completed_evidence(mutation):
    run = completed_run()
    mutation(run)
    with pytest.raises(ShadowReleaseProgressError):
        build_progress(runs=[run])


def test_validator_rejects_unknown_or_mutated_derived_progress():
    progress = build_progress(runs=[completed_run()])
    unknown = copy.deepcopy(progress)
    unknown["unexpected"] = "forbidden"
    mutated = copy.deepcopy(progress)
    mutated["shadow_release_readiness"] = True

    with pytest.raises(ShadowReleaseProgressError):
        validate_shadow_release_progress(unknown)
    with pytest.raises(ShadowReleaseProgressError):
        validate_shadow_release_progress(mutated)


def test_builder_does_not_mutate_caller_owned_runs_or_enabled_modes():
    runs = [completed_run()]
    enabled_modes = ["SCALP"]
    original = copy.deepcopy((runs, enabled_modes))

    build_progress(runs=runs, enabled_modes=enabled_modes)

    assert (runs, enabled_modes) == original
