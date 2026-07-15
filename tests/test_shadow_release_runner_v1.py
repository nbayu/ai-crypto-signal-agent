"""Frozen RED tests for the Phase 08 Shadow Release runner."""

from __future__ import annotations

import copy

import pytest

from engine.shadow_release_contract_v1 import build_shadow_run_id
from engine.shadow_release_runner_v1 import (
    ShadowReleaseRunnerError,
    run_shadow_release_v1,
)


SOURCE_COMMIT = "a" * 40
_DEFAULT_ADAPTER = object()


def source_publication_ref(**overrides):
    value = {
        "signal_id": "SCP-20260716-001",
        "delivery_id": "delivery-001",
        "mode": "SCALP",
        "published_at": "2026-07-16T12:00:00Z",
        "source_payload_hash": "b" * 64,
    }
    value.update(overrides)
    return value


def lifecycle(**overrides):
    value = {
        "publication": "PUBLISHED",
        "entry_eligibility": "ELIGIBLE",
        "cancellation": None,
        "entry_touch": "NOT_OBSERVED",
        "tp_sl_ordering": "NOT_APPLICABLE",
        "acknowledgment": None,
        "terminal_state": "OBSERVING",
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
        "lifecycle": lifecycle(),
    }
    value.update(overrides)
    return value


def source_envelope(**overrides):
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
        "market_identity": {
            "venue": "BINANCE_FUTURES_PUBLIC",
            "symbol": "BTCUSDT",
            "interval": "5m",
            "market_data_source": "PUBLIC_CLOSED_CANDLE_CAPTURE",
            "market_input_hash": "c" * 64,
        },
        "captured_at": "2026-07-16T12:00:02Z",
        "evaluation_started_at": "2026-07-16T12:00:00Z",
        "evaluation_completed_at": "2026-07-16T12:00:02Z",
        "serialized_inputs": {
            "scanner_results": [{"symbol": "BTCUSDT"}],
            "open_interest": {"BTCUSDT": {"change_pct": 1.0}},
            "validator_response": {"content": "approved", "usage": {}},
            "closed_candles": {"BTCUSDT": []},
        },
        "serialized_input_hash": "d" * 64,
        "expected_decision": semantic_projection(),
        "expected_decision_hash": "e" * 64,
        "source_publication_ref": source_publication_ref(),
        "signal_geometry": {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_zone": {"min": 100.0, "max": 102.0},
            "stop_loss": 95.0,
            "take_profit": {"tp1": 110.0, "tp2": 120.0},
            "valid_until": "2026-07-16T13:00:00Z",
        },
        "lifecycle_trace": lifecycle(),
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


def identity(envelope=None):
    return build_shadow_run_id(
        source_envelope() if envelope is None else envelope
    )


def run_shadow(
    *,
    envelope=None,
    shadow_run_id=None,
    expected_adapter=_DEFAULT_ADAPTER,
    observed_adapter=_DEFAULT_ADAPTER,
    versions=None,
    **overrides,
):
    envelope = source_envelope() if envelope is None else envelope
    value = {
        "source_envelope": envelope,
        "shadow_run_id": (
            identity(envelope) if shadow_run_id is None else shadow_run_id
        ),
        "expected_adapter": (
            (lambda forwarded: copy.deepcopy(forwarded["expected_decision"]))
            if expected_adapter is _DEFAULT_ADAPTER
            else expected_adapter
        ),
        "observed_adapter": (
            (lambda forwarded: copy.deepcopy(forwarded["expected_decision"]))
            if observed_adapter is _DEFAULT_ADAPTER
            else observed_adapter
        ),
        "component_versions": (
            component_versions() if versions is None else versions
        ),
        "started_at": "2026-07-16T12:00:03Z",
        "completed_at": "2026-07-16T12:00:05Z",
    }
    value.update(overrides)
    return run_shadow_release_v1(**value)


def test_runner_returns_the_canonical_completed_contract_for_a_match():
    result = run_shadow()

    assert result["shadow_run_id"] == identity()
    assert result["classification"] == "SHADOW_RELEASE"
    assert result["execution_boundary"] == (
        "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
    )
    assert result["capital_exposure"] == "NONE"
    assert result["order_execution"] == "PROHIBITED"
    assert result["comparison"] == {
        "outcome": "MATCH",
        "primary_code": None,
        "secondary_codes": [],
    }
    assert result["failure"] is None
    assert result["operational_duration_ms"] == 2_000


def test_runner_requires_the_caller_supplied_canonical_shadow_identity():
    envelope = source_envelope()

    with pytest.raises(ShadowReleaseRunnerError):
        run_shadow(envelope=envelope, shadow_run_id="SHR-" + "0" * 64)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_publication_ref", None),
        ("source_evaluation_id", ""),
        ("source_commit", "short"),
        ("mode", "scalp"),
    ],
)
def test_runner_fails_closed_for_missing_or_invalid_serialized_authority(
    field, value
):
    envelope = source_envelope(**{field: value})

    with pytest.raises(ShadowReleaseRunnerError):
        run_shadow(envelope=envelope, shadow_run_id="SHR-" + "0" * 64)


def test_expected_and_observed_adapters_receive_exact_detached_input_once():
    envelope = source_envelope()
    original = copy.deepcopy(envelope)
    calls = []

    def expected_adapter(forwarded):
        calls.append(("expected", copy.deepcopy(forwarded)))
        forwarded["serialized_inputs"]["scanner_results"].append(
            {"symbol": "MUTATION"}
        )
        return semantic_projection()

    def observed_adapter(forwarded):
        calls.append(("observed", copy.deepcopy(forwarded)))
        return semantic_projection()

    result = run_shadow(
        envelope=envelope,
        expected_adapter=expected_adapter,
        observed_adapter=observed_adapter,
    )

    assert result["comparison"]["outcome"] == "MATCH"
    assert [name for name, _ in calls] == ["expected", "observed"]
    assert calls[0][1]["source_publication_ref"] == source_publication_ref()
    assert envelope == original


def test_expected_adapter_has_no_hidden_fallback_to_envelope_output():
    def unexpected_expected_adapter(_):
        return semantic_projection(
            validated_pipeline={"final_top5": []},
        )

    result = run_shadow(expected_adapter=unexpected_expected_adapter)

    assert result["comparison"] == {
        "outcome": "MISMATCH",
        "primary_code": "DECISION_MISMATCH",
        "secondary_codes": [],
    }
    assert result["failure"] is None


def test_decision_mismatch_is_completed_evidence_without_failure():
    def observed_adapter(_):
        return semantic_projection(
            validated_pipeline={"final_top5": []},
        )

    result = run_shadow(observed_adapter=observed_adapter)

    assert result["comparison"] == {
        "outcome": "MISMATCH",
        "primary_code": "DECISION_MISMATCH",
        "secondary_codes": [],
    }
    assert result["failure"] is None
    assert len(result["content_hash"]) == 64


@pytest.mark.parametrize(
    ("field", "changed_value"),
    [
        ("entry_eligibility", "NOT_ELIGIBLE"),
        ("cancellation", {"event_id": "cancel-001"}),
        ("entry_touch", "ENTRY_ZONE_TOUCHED"),
        ("tp_sl_ordering", "AMBIGUOUS"),
        ("acknowledgment", {"event_id": "ack-001"}),
        ("terminal_state", "CANCELLED"),
    ],
)
def test_lifecycle_and_terminal_differences_use_frozen_lifecycle_code(
    field, changed_value
):
    def observed_adapter(_):
        changed = semantic_projection()
        changed["lifecycle"] = copy.deepcopy(changed["lifecycle"])
        changed["lifecycle"][field] = changed_value
        return changed

    result = run_shadow(observed_adapter=observed_adapter)

    assert result["comparison"]["outcome"] == "MISMATCH"
    assert result["comparison"]["primary_code"] == "LIFECYCLE_MISMATCH"
    assert result["failure"] is None


def test_publication_difference_uses_frozen_publication_code():
    def observed_adapter(_):
        return semantic_projection(
            publication=source_publication_ref(delivery_id="delivery-002"),
        )

    result = run_shadow(observed_adapter=observed_adapter)

    assert result["comparison"]["primary_code"] == "PUBLICATION_MISMATCH"


def test_no_trade_difference_uses_frozen_no_trade_code():
    no_trade_lifecycle = lifecycle(
        publication="NO_TRADE",
        entry_eligibility="NOT_APPLICABLE",
        entry_touch="NOT_APPLICABLE",
        terminal_state="NO_TRADE",
    )

    def observed_adapter(_):
        return semantic_projection(
            publication=None,
            lifecycle=no_trade_lifecycle,
        )

    result = run_shadow(observed_adapter=observed_adapter)

    assert result["comparison"]["primary_code"] == "NO_TRADE_MISMATCH"


@pytest.mark.parametrize(
    "adapter_name",
    ["expected_adapter", "observed_adapter"],
)
def test_adapter_exceptions_are_safe_classified_failed_evidence(adapter_name):
    calls = []

    def exploding_adapter(_):
        calls.append("called")
        raise RuntimeError("token=secret should never be serialized")

    kwargs = {adapter_name: exploding_adapter}
    result = run_shadow(**kwargs)

    assert calls == ["called"]
    assert result["comparison"]["outcome"] == "FAILED"
    assert result["failure"]["primary_code"] == "SHADOW_EXECUTION_FAILED"
    assert result["failure"]["component"] == adapter_name
    assert "secret" not in result["failure"]["message"].casefold()


@pytest.mark.parametrize(
    ("adapter_name", "adapter"),
    [
        ("expected_adapter", None),
        ("observed_adapter", None),
        ("expected_adapter", "not-callable"),
        ("observed_adapter", "not-callable"),
    ],
)
def test_runner_rejects_missing_or_non_callable_adapter(adapter_name, adapter):
    with pytest.raises(ShadowReleaseRunnerError):
        run_shadow(**{adapter_name: adapter})


@pytest.mark.parametrize(
    "adapter_name",
    ["expected_adapter", "observed_adapter"],
)
def test_runner_rejects_invalid_adapter_output(adapter_name):
    kwargs = {adapter_name: lambda _: ["not", "a", "projection"]}

    with pytest.raises(ShadowReleaseRunnerError):
        run_shadow(**kwargs)


def test_identical_inputs_are_deterministic_across_mapping_insertion_order():
    first = source_envelope()
    second = {
        key: copy.deepcopy(first[key])
        for key in reversed(tuple(first.keys()))
    }

    assert run_shadow(envelope=first) == run_shadow(envelope=second)


def test_semantic_mutation_changes_completed_contract_content_hash():
    matched = run_shadow()

    def observed_adapter(_):
        return semantic_projection(
            validated_pipeline={"final_top5": []},
        )

    mismatched = run_shadow(observed_adapter=observed_adapter)

    assert matched["content_hash"] != mismatched["content_hash"]


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
        "telegram_ledger",
        "replay_output_root",
        "paper_signal_output_root",
        "artifact_path",
    ],
)
def test_runner_rejects_forbidden_authority_and_publication_fields(
    forbidden_field,
):
    envelope = source_envelope()
    envelope[forbidden_field] = {"forbidden": True}

    with pytest.raises(ShadowReleaseRunnerError):
        run_shadow(envelope=envelope, shadow_run_id="SHR-" + "0" * 64)


def test_runner_requires_caller_supplied_explicit_operational_timestamps():
    with pytest.raises(ShadowReleaseRunnerError):
        run_shadow(started_at=None)

    with pytest.raises(ShadowReleaseRunnerError):
        run_shadow(completed_at="2026-07-16T12:00:03.000001Z")


def test_runner_does_not_retry_an_adapter_after_failure():
    calls = []

    def exploding_adapter(_):
        calls.append("called")
        raise ValueError("safe failure")

    result = run_shadow(observed_adapter=exploding_adapter)

    assert calls == ["called"]
    assert result["comparison"]["outcome"] == "FAILED"
