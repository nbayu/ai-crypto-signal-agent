"""Frozen RED contract tests for Phase 08 Shadow Release."""

from __future__ import annotations

import copy

import pytest

from engine.shadow_release_contract_v1 import (
    SHADOW_RELEASE_CAPITAL_EXPOSURE,
    SHADOW_RELEASE_CLASSIFICATION,
    SHADOW_RELEASE_EXECUTION_BOUNDARY,
    SHADOW_RELEASE_ORDER_EXECUTION,
    SHADOW_RELEASE_SCHEMA_NAME,
    SHADOW_RELEASE_SCHEMA_VERSION,
    ShadowReleaseContractError,
    build_shadow_run_contract,
    build_shadow_run_id,
    canonical_json_bytes,
    compare_semantic_projections,
    validate_shadow_input_envelope,
)


SOURCE_COMMIT = "a" * 40
INPUT_HASH = "b" * 64
EXPECTED_HASH = "c" * 64


def source_publication_ref(**overrides):
    value = {
        "signal_id": "SCP-20260716-001",
        "delivery_id": "delivery-001",
        "mode": "SCALP",
        "published_at": "2026-07-16T12:00:00Z",
        "source_payload_hash": "d" * 64,
    }
    value.update(overrides)
    return value


def market_identity(**overrides):
    value = {
        "venue": "BINANCE_FUTURES_PUBLIC",
        "symbol": "BTCUSDT",
        "interval": "5m",
        "market_data_source": "PUBLIC_CLOSED_CANDLE_CAPTURE",
        "market_input_hash": "e" * 64,
    }
    value.update(overrides)
    return value


def semantic_projection(**overrides):
    value = {
        "validated_pipeline": {
            "final_top5": [
                {
                    "symbol": "BTCUSDT",
                    "final_rank_score": 91.25,
                    "reason_code": "APPROVED",
                }
            ]
        },
        "outcome_snapshot": {"candidates": ["BTCUSDT"]},
        "watchlist": {"setups": [{"rank": 1, "symbol": "BTCUSDT"}]},
        "pre_delivery": {"disposition": "PUBLISHED"},
        "tradingview_watchlist": "BTCUSDT",
        "pine_bridge": {"symbol": "BTCUSDT"},
        "pine_delivery_payload": "BTCUSDT,LONG",
        "publication": source_publication_ref(),
        "lifecycle": {
            "publication": "PUBLISHED",
            "entry_eligibility": "ELIGIBLE",
            "cancellation": None,
            "entry_touch": "NOT_OBSERVED",
            "tp_sl_ordering": "NOT_APPLICABLE",
            "acknowledgment": None,
            "terminal_state": "OBSERVING",
        },
    }
    value.update(overrides)
    return value


def serialized_inputs(**overrides):
    value = {
        "scanner_results": [{"symbol": "BTCUSDT"}],
        "open_interest": {"BTCUSDT": {"change_pct": 1.0}},
        "validator_response": {"content": "approved", "usage": {}},
        "closed_candles": {"BTCUSDT": []},
    }
    value.update(overrides)
    return value


def shadow_input_envelope(**overrides):
    value = {
        "schema_version": 1,
        "schema_name": "shadow-release-input",
        "classification": "SHADOW_RELEASE",
        "execution_boundary": (
            "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
        ),
        "source_commit": SOURCE_COMMIT,
        "source_evaluation_id": "evaluation-20260716-1200",
        "mode": "SCALP",
        "market_identity": market_identity(),
        "captured_at": "2026-07-16T12:00:02Z",
        "evaluation_started_at": "2026-07-16T12:00:00Z",
        "evaluation_completed_at": "2026-07-16T12:00:02Z",
        "serialized_inputs": serialized_inputs(),
        "serialized_input_hash": INPUT_HASH,
        "expected_decision": semantic_projection(),
        "expected_decision_hash": EXPECTED_HASH,
        "source_publication_ref": source_publication_ref(),
        "signal_geometry": {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_zone": {"min": 100.0, "max": 102.0},
            "stop_loss": 95.0,
            "take_profit": {"tp1": 110.0, "tp2": 120.0},
            "valid_until": "2026-07-16T13:00:00Z",
        },
        "lifecycle_trace": semantic_projection()["lifecycle"],
        "outcome_kind": "PUBLISHED_SIGNAL",
    }
    value.update(overrides)
    return value


def component_versions(**overrides):
    value = {
        "master_engine": "master-engine-v4",
        "validated_pipeline": "validated-pipeline-v4",
        "pre_delivery": "pre-delivery-v4",
        "shadow_contract": "shadow-release-contract-v1",
        "shadow_runner": "shadow-release-runner-v1",
    }
    value.update(overrides)
    return value


def build_run(*, envelope=None, observed=None, **overrides):
    value = {
        "source_envelope": (
            shadow_input_envelope() if envelope is None else envelope
        ),
        "observed_decision": (
            semantic_projection() if observed is None else observed
        ),
        "component_versions": component_versions(),
        "started_at": "2026-07-16T12:00:03Z",
        "completed_at": "2026-07-16T12:00:05Z",
        "failure": None,
    }
    value.update(overrides)
    return build_shadow_run_contract(**value)


def test_canonical_constants_are_frozen():
    assert SHADOW_RELEASE_SCHEMA_VERSION == 1
    assert SHADOW_RELEASE_SCHEMA_NAME == "shadow-release-run"
    assert SHADOW_RELEASE_CLASSIFICATION == "SHADOW_RELEASE"
    assert SHADOW_RELEASE_EXECUTION_BOUNDARY == (
        "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
    )
    assert SHADOW_RELEASE_CAPITAL_EXPOSURE == "NONE"
    assert SHADOW_RELEASE_ORDER_EXECUTION == "PROHIBITED"


def test_validated_envelope_is_copied_and_has_exact_authority_fields():
    original = shadow_input_envelope()
    result = validate_shadow_input_envelope(original)

    assert result == original
    assert result is not original
    assert result["market_identity"] is not original["market_identity"]
    assert set(result) == {
        "schema_version",
        "schema_name",
        "classification",
        "execution_boundary",
        "source_commit",
        "source_evaluation_id",
        "mode",
        "market_identity",
        "captured_at",
        "evaluation_started_at",
        "evaluation_completed_at",
        "serialized_inputs",
        "serialized_input_hash",
        "expected_decision",
        "expected_decision_hash",
        "source_publication_ref",
        "signal_geometry",
        "lifecycle_trace",
        "outcome_kind",
    }


def test_builded_run_has_closed_top_level_contract_and_match_evidence():
    result = build_run()

    assert set(result) == {
        "schema_version",
        "schema_name",
        "classification",
        "execution_boundary",
        "capital_exposure",
        "order_execution",
        "position_authority",
        "shadow_run_id",
        "source_commit",
        "source_evaluation_id",
        "mode",
        "market_identity",
        "outcome_kind",
        "source_publication_ref",
        "serialized_input_hash",
        "expected_decision",
        "expected_decision_hash",
        "observed_decision",
        "observed_decision_hash",
        "comparison",
        "component_versions",
        "evaluation_started_at",
        "evaluation_completed_at",
        "started_at",
        "completed_at",
        "operational_duration_ms",
        "failure",
        "content_hash",
    }
    assert result["schema_version"] == 1
    assert result["schema_name"] == "shadow-release-run"
    assert result["classification"] == "SHADOW_RELEASE"
    assert result["execution_boundary"] == (
        "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
    )
    assert result["capital_exposure"] == "NONE"
    assert result["order_execution"] == "PROHIBITED"
    assert result["position_authority"] == "NONE"
    assert result["comparison"] == {
        "outcome": "MATCH",
        "primary_code": None,
        "secondary_codes": [],
    }
    assert result["failure"] is None
    assert result["operational_duration_ms"] == 2_000
    assert result["shadow_run_id"].startswith("SHR-")
    assert len(result["shadow_run_id"]) == 68
    assert len(result["content_hash"]) == 64


def test_shadow_identity_is_deterministic_across_mapping_order():
    first = shadow_input_envelope()
    second = {
        key: copy.deepcopy(first[key])
        for key in reversed(tuple(first.keys()))
    }

    assert build_shadow_run_id(first) == build_shadow_run_id(second)
    assert build_run(envelope=first)["shadow_run_id"] == (
        build_run(envelope=second)["shadow_run_id"]
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source_commit", "f" * 40),
        ("source_evaluation_id", "evaluation-20260716-1201"),
        ("mode", "INTRADAY"),
        ("outcome_kind", "NO_TRADE"),
    ],
)
def test_semantic_identity_mutation_changes_shadow_run_id(
    field, replacement
):
    first = shadow_input_envelope()
    second = shadow_input_envelope(**{field: replacement})
    if field == "outcome_kind":
        second["source_publication_ref"] = None
        second["signal_geometry"] = None
        second["lifecycle_trace"] = {
            "publication": "NO_TRADE",
            "entry_eligibility": "NOT_APPLICABLE",
            "cancellation": None,
            "entry_touch": "NOT_APPLICABLE",
            "tp_sl_ordering": "NOT_APPLICABLE",
            "acknowledgment": None,
            "terminal_state": "NO_TRADE",
        }
        second["expected_decision"] = semantic_projection(
            publication=None,
            lifecycle=second["lifecycle_trace"],
        )

    assert build_shadow_run_id(first) != build_shadow_run_id(second)


def test_content_hash_is_deterministic_and_changes_for_semantic_mutation():
    first = build_run()
    second = build_run()
    changed = build_run(
        observed=semantic_projection(
            validated_pipeline={"final_top5": []},
        )
    )

    assert first["content_hash"] == second["content_hash"]
    assert first["content_hash"] != changed["content_hash"]


def test_caller_cannot_supply_or_override_content_hash():
    with pytest.raises(ShadowReleaseContractError):
        build_shadow_run_contract(
            source_envelope=shadow_input_envelope(),
            observed_decision=semantic_projection(),
            component_versions=component_versions(),
            started_at="2026-07-16T12:00:03Z",
            completed_at="2026-07-16T12:00:05Z",
            failure=None,
            content_hash="0" * 64,
        )


@pytest.mark.parametrize(
    "field",
    ["source_publication_ref", "signal_geometry"],
)
def test_published_signal_requires_authoritative_serialized_identity(field):
    envelope = shadow_input_envelope(**{field: None})

    with pytest.raises(ShadowReleaseContractError):
        validate_shadow_input_envelope(envelope)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("signal_id", ""),
        ("delivery_id", ""),
        ("signal_id", "guessed-from-process-state"),
    ],
)
def test_source_identity_cannot_be_missing_or_recovered_from_hidden_state(
    field, value
):
    source = source_publication_ref(**{field: value})
    envelope = shadow_input_envelope(source_publication_ref=source)

    with pytest.raises(ShadowReleaseContractError):
        validate_shadow_input_envelope(envelope)


def test_no_trade_has_no_signal_or_delivery_identity():
    lifecycle = {
        "publication": "NO_TRADE",
        "entry_eligibility": "NOT_APPLICABLE",
        "cancellation": None,
        "entry_touch": "NOT_APPLICABLE",
        "tp_sl_ordering": "NOT_APPLICABLE",
        "acknowledgment": None,
        "terminal_state": "NO_TRADE",
    }
    expected = semantic_projection(publication=None, lifecycle=lifecycle)
    envelope = shadow_input_envelope(
        outcome_kind="NO_TRADE",
        source_publication_ref=None,
        signal_geometry=None,
        lifecycle_trace=lifecycle,
        expected_decision=expected,
    )

    result = validate_shadow_input_envelope(envelope)

    assert result["source_publication_ref"] is None
    assert result["outcome_kind"] == "NO_TRADE"


def test_no_trade_rejects_a_publication_identity():
    envelope = shadow_input_envelope(outcome_kind="NO_TRADE")

    with pytest.raises(ShadowReleaseContractError):
        validate_shadow_input_envelope(envelope)


def test_exact_equal_semantic_projections_match():
    result = compare_semantic_projections(
        semantic_projection(), semantic_projection()
    )

    assert result == {
        "outcome": "MATCH",
        "primary_code": None,
        "secondary_codes": [],
    }


def test_only_explicit_nonsemantic_metadata_is_ignored():
    expected = semantic_projection()
    observed = semantic_projection()
    expected["operational_metadata"] = {
        "artifact_path": "/production/a.json",
        "temporary_path": "/production/.a.tmp",
        "worker_run_id": "worker-a",
        "telegram_update_id": "update-a",
    }
    observed["operational_metadata"] = {
        "artifact_path": "/shadow/b.json",
        "temporary_path": "/shadow/.b.tmp",
        "worker_run_id": "worker-b",
        "telegram_update_id": "update-b",
    }

    assert compare_semantic_projections(expected, observed)["outcome"] == (
        "MATCH"
    )


@pytest.mark.parametrize(
    ("expected", "observed", "code"),
    [
        (
            semantic_projection(
                validated_pipeline={"final_top5": ["BTCUSDT"]}
            ),
            semantic_projection(
                validated_pipeline={"final_top5": ["ETHUSDT"]}
            ),
            "DECISION_MISMATCH",
        ),
        (
            semantic_projection(publication=source_publication_ref()),
            semantic_projection(
                publication=source_publication_ref(
                    delivery_id="delivery-002"
                )
            ),
            "PUBLICATION_MISMATCH",
        ),
        (
            semantic_projection(),
            semantic_projection(
                lifecycle={
                    **semantic_projection()["lifecycle"],
                    "terminal_state": "CANCELLED",
                }
            ),
            "LIFECYCLE_MISMATCH",
        ),
    ],
)
def test_semantic_mismatches_have_frozen_primary_classification(
    expected, observed, code
):
    result = compare_semantic_projections(expected, observed)

    assert result["outcome"] == "MISMATCH"
    assert result["primary_code"] == code


def test_no_trade_disposition_difference_is_not_a_match():
    no_trade = semantic_projection(
        publication=None,
        lifecycle={
            "publication": "NO_TRADE",
            "entry_eligibility": "NOT_APPLICABLE",
            "cancellation": None,
            "entry_touch": "NOT_APPLICABLE",
            "tp_sl_ordering": "NOT_APPLICABLE",
            "acknowledgment": None,
            "terminal_state": "NO_TRADE",
        },
    )

    result = compare_semantic_projections(semantic_projection(), no_trade)

    assert result["outcome"] == "MISMATCH"
    assert result["primary_code"] == "NO_TRADE_MISMATCH"


@pytest.mark.parametrize(
    "lifecycle_field",
    [
        "publication",
        "entry_eligibility",
        "cancellation",
        "entry_touch",
        "tp_sl_ordering",
        "acknowledgment",
        "terminal_state",
    ],
)
def test_lifecycle_surface_is_compared_exactly(lifecycle_field):
    expected = semantic_projection()
    observed = semantic_projection()
    observed["lifecycle"] = copy.deepcopy(observed["lifecycle"])
    observed["lifecycle"][lifecycle_field] = "DIFFERENT"

    result = compare_semantic_projections(expected, observed)

    assert result["outcome"] == "MISMATCH"
    assert result["primary_code"] == "LIFECYCLE_MISMATCH"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("schema_name", ""),
        ("classification", "PAPER_SIGNAL"),
        ("execution_boundary", "LIVE_MARKET_OBSERVATION_NO_CAPITAL"),
        ("source_commit", "short"),
        ("source_evaluation_id", ""),
        ("mode", "scalp"),
        ("captured_at", "2026-07-16 12:00:00"),
        ("serialized_input_hash", "not-a-hash"),
        ("expected_decision_hash", "not-a-hash"),
        ("outcome_kind", "EXECUTED_ORDER"),
    ],
)
def test_envelope_rejects_invalid_scalar_contract_values(field, value):
    with pytest.raises(ShadowReleaseContractError):
        validate_shadow_input_envelope(shadow_input_envelope(**{field: value}))


def test_envelope_rejects_unknown_fields_and_does_not_mutate_input():
    envelope = shadow_input_envelope()
    original = copy.deepcopy(envelope)
    envelope["process_local_identity"] = "forbidden"

    with pytest.raises(ShadowReleaseContractError):
        validate_shadow_input_envelope(envelope)

    assert envelope["source_publication_ref"] == original[
        "source_publication_ref"
    ]


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "exchange_credentials",
        "private_endpoint",
        "order_payload",
        "position_size",
        "account_state",
        "balance_state",
        "portfolio_state",
        "exchange_execution",
        "api_secret",
        "private_key",
    ],
)
def test_security_and_execution_authority_fields_are_rejected(
    forbidden_field,
):
    envelope = shadow_input_envelope()
    envelope[forbidden_field] = {"forbidden": True}

    with pytest.raises(ShadowReleaseContractError):
        validate_shadow_input_envelope(envelope)


@pytest.mark.parametrize(
    ("started_at", "completed_at"),
    [
        ("2026-07-16T12:00:05Z", "2026-07-16T12:00:03Z"),
        ("not-a-timestamp", "2026-07-16T12:00:05Z"),
        ("2026-07-16T12:00:03.000001Z", "2026-07-16T12:00:05Z"),
    ],
)
def test_operational_duration_requires_ordered_exact_milliseconds(
    started_at, completed_at
):
    with pytest.raises(ShadowReleaseContractError):
        build_run(started_at=started_at, completed_at=completed_at)


def test_failed_run_requires_classified_safe_failure_evidence():
    failure = {
        "primary_code": "SOURCE_AUTHORITY_MISSING",
        "component": "publication_adapter",
        "message": "authoritative publication capture unavailable",
    }
    result = build_run(
        observed=semantic_projection(),
        failure=failure,
    )

    assert result["comparison"]["outcome"] == "FAILED"
    assert result["failure"] == failure


@pytest.mark.parametrize(
    "failure",
    [
        None,
        {"primary_code": "UNKNOWN", "component": "x", "message": "x"},
        {
            "primary_code": "SOURCE_AUTHORITY_MISSING",
            "component": "",
            "message": "x",
        },
        {
            "primary_code": "SOURCE_AUTHORITY_MISSING",
            "component": "x",
            "message": "token=secret",
        },
    ],
)
def test_failure_evidence_is_closed_and_safe(failure):
    if failure is None:
        kwargs = {"observed": semantic_projection(
            validated_pipeline={"final_top5": []}
        )}
    else:
        kwargs = {"failure": failure}

    with pytest.raises(ShadowReleaseContractError):
        build_run(**kwargs)


def test_builder_and_comparator_do_not_mutate_caller_owned_nested_values():
    envelope = shadow_input_envelope()
    observed = semantic_projection()
    versions = component_versions()
    original = copy.deepcopy((envelope, observed, versions))

    build_shadow_run_contract(
        source_envelope=envelope,
        observed_decision=observed,
        component_versions=versions,
        started_at="2026-07-16T12:00:03Z",
        completed_at="2026-07-16T12:00:05Z",
        failure=None,
    )
    compare_semantic_projections(
        semantic_projection(),
        semantic_projection(),
    )

    assert (envelope, observed, versions) == original


def test_canonical_json_rejects_non_finite_and_is_order_independent():
    assert canonical_json_bytes({"b": 2, "a": 1}) == (
        canonical_json_bytes({"a": 1, "b": 2})
    )

    with pytest.raises(ShadowReleaseContractError):
        canonical_json_bytes({"value": float("nan")})
