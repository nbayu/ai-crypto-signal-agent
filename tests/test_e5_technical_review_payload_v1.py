from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e5_technical_review_payload_v1 as subject
import engine.e5_deepseek_technical_review_v1 as deepseek_review
from engine.e3_actionable_admission_v1 import build_e3_actionable_admission
from engine.e3_executable_price_snapshot_v1 import (
    build_e3_executable_price_snapshot,
)
from engine.e3_golden_zone_geometry_v1 import build_e3_golden_zone_geometry
from engine.e3_mode_trigger_evidence_v1 import build_e3_mode_trigger_evidence
from engine.e3_price_zone_admission_v1 import build_e3_price_zone_admission
from engine.e3_setup_lifecycle_v1 import build_e3_setup_lifecycle
from engine.e3_structural_targets_v1 import build_e3_structural_targets
from engine.e4_duplicate_protection_composition_v1 import (
    compose_e4_duplicate_protection_v1,
)
from engine.e4_thesis_history_store_v1 import (
    load_e4_thesis_history_store_v1,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_profile_v1 import get_mode_profile
from engine.mode_router_v1 import build_mode_scan_request
from engine.mode_scan_execution_evidence_v1 import (
    MODE_OI_OBSERVATION_SCHEMA_VERSION,
    MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
    MODE_SYMBOL_EXECUTION_OUTCOME_SCHEMA_VERSION,
    MODE_UTC_CANDLE_SCHEMA_VERSION,
    OUTCOME_CANDIDATE,
    REASON_CANDIDATE_ACCEPTED,
    ModeOiObservationV1,
    ModeSymbolExecutionOutcomeV1,
    ModeUtcCandleV1,
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
from engine.news_event_contract_v1 import (
    EVENT_SCHEMA_VERSION,
    NormalizedNewsEventV1,
)
from engine.news_risk_object_v1 import NEWS_RISK_POLICY_VERSION, NewsRiskObjectV1
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)


OBSERVED_AT = "2026-07-30T06:30:00Z"
MODES_AND_SIDES = (
    ("SWING", "LONG"),
    ("SWING", "SHORT"),
    ("INTRADAY", "LONG"),
    ("INTRADAY", "SHORT"),
    ("SCALP", "LONG"),
    ("SCALP", "SHORT"),
)
TIMEFRAME_SECONDS = {
    "1w": 604800,
    "1d": 86400,
    "4h": 14400,
    "1h": 3600,
    "15m": 900,
    "5m": 300,
    "3m": 180,
}
EXPECTED_EVIDENCE_FIELDS = (
    "mode",
    "relevant_timeframes",
    "executable_price",
    "exchange_timestamp",
    "golden_zone",
    "anchors",
    "stop_geometry",
    "target_geometry",
    "net_rr",
    "trigger_type",
    "trigger_age",
    "lifecycle_state",
    "thesis_fingerprint",
    "prior_publication_identity",
    "prior_history_identity",
    "liquidity_evidence",
    "volume_evidence",
    "open_interest_evidence",
    "news_and_contradiction_quality",
)
EXCLUDED_PUBLICATION_FIELDS = {
    "signal_id",
    "delivery_id",
    "publication_timestamp",
    "telegram_message_id",
    "current_price",
    "score",
    "llm_result",
    "valid_until",
    "ledger_revision",
}


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _developing_open(observed_at: str, timeframe: str) -> datetime:
    observed = datetime.strptime(observed_at, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    epoch = datetime(
        1970,
        1,
        5 if timeframe == "1w" else 1,
        tzinfo=timezone.utc,
    )
    seconds = TIMEFRAME_SECONDS[timeframe]
    elapsed = int((observed - epoch).total_seconds())
    return epoch + timedelta(seconds=(elapsed // seconds) * seconds)


def _candles_for(fetch, observed_at: str = OBSERVED_AT):
    final_open = _developing_open(observed_at, fetch.timeframe)
    seconds = TIMEFRAME_SECONDS[fetch.timeframe]
    first_open = final_open - timedelta(
        seconds=seconds * fetch.closed_candle_limit
    )
    return tuple(
        ModeUtcCandleV1(
            schema_version=MODE_UTC_CANDLE_SCHEMA_VERSION,
            timeframe=fetch.timeframe,
            open_time=_utc_text(first_open + timedelta(seconds=seconds * index)),
            close_time=_utc_text(
                first_open + timedelta(seconds=seconds * (index + 1))
            ),
            open=100 + index,
            high=102 + index,
            low=98 + index,
            close=101 + index,
            volume=1000 + index,
        )
        for index in range(fetch.raw_fetch_limit)
    )


def _authority(tp2: int) -> ProductionCandidateAuthorityV1:
    return ProductionCandidateAuthorityV1(
        source_commit="a" * 40,
        source_evaluation_id="evaluation:e5-technical-review-payload",
        production_evidence_ref={
            "manifest_hash": "b" * 64,
            "manifest_path": "sealed/manifest.json",
        },
        component_versions={"adapter": "v1", "master": "v4"},
        tp2=tp2,
        valid_until="2026-08-01T00:00:00Z",
        strategy_version="master-engine-v4",
        source_payload_hash="c" * 64,
    )


def _real_chain(mode: str = "SWING", side: str = "LONG", *, actionable=True):
    if side == "LONG":
        anchor_low_at = "2026-07-30T00:00:00Z"
        anchor_high_at = "2026-07-30T01:00:00Z"
    else:
        anchor_high_at = "2026-07-30T00:00:00Z"
        anchor_low_at = "2026-07-30T01:00:00Z"
    geometry = build_e3_golden_zone_geometry(
        mode=mode,
        mode_lineage_sha256=build_mode_audit_lineage(mode).lineage_sha256,
        canonical_symbol="BTC/USDT:USDT",
        side=side,
        structure_generation_id=f"structure:e5-{mode.lower()}-{side.lower()}",
        anchor_low_at=anchor_low_at,
        anchor_low_tick=9000,
        anchor_high_at=anchor_high_at,
        anchor_high_tick=12000,
        tick_size="1",
    )
    targets = build_e3_structural_targets(
        geometry=geometry,
        ordered_destinations=(
            (
                "STRUCTURE",
                "destination:tp1",
                12146 if side == "LONG" else 8854,
                geometry.structure_timeframe,
                geometry.structure_generation_id,
            ),
            (
                "LIQUIDITY",
                "destination:tp2",
                12528 if side == "LONG" else 8472,
                geometry.structure_timeframe,
                geometry.structure_generation_id,
            ),
        ),
    )
    inside_tick = geometry.golden_zone_low_tick + (
        geometry.golden_zone_high_tick - geometry.golden_zone_low_tick
    ) // 2
    executable_tick = (
        inside_tick
        if actionable
        else geometry.golden_zone_high_tick + 1
    )
    snapshot = build_e3_executable_price_snapshot(
        geometry=geometry,
        venue="BINANCE_USDM",
        quote_generation_id=f"quote:e5-{mode.lower()}-{side.lower()}",
        exchange_timestamp=OBSERVED_AT,
        best_bid_tick=(
            executable_tick - 1 if side == "LONG" else executable_tick
        ),
        best_ask_tick=(
            executable_tick if side == "LONG" else executable_tick + 1
        ),
        last_price_tick=executable_tick,
        mark_price_tick=executable_tick,
        modeled_adverse_slippage_bps=0,
        tick_size=geometry.tick_size,
    )
    admission = build_e3_price_zone_admission(
        geometry=geometry,
        snapshot=snapshot,
        evaluation_timestamp=OBSERVED_AT,
    )
    profile = get_mode_profile(mode)
    trigger = build_e3_mode_trigger_evidence(
        geometry=geometry,
        mode=geometry.mode,
        mode_lineage_sha256=geometry.mode_lineage_sha256,
        canonical_symbol=geometry.canonical_symbol,
        side=geometry.side,
        structure_timeframe=geometry.structure_timeframe,
        structure_generation_id=geometry.structure_generation_id,
        trigger_timeframe=profile.trigger_timeframe,
        trigger_rule=profile.trigger_rule,
        trigger_candle_close_at=OBSERVED_AT,
        trigger_candle_closed=True,
        trigger_rule_satisfied=actionable,
        evaluation_timestamp=OBSERVED_AT,
    )
    lifecycle = build_e3_setup_lifecycle(
        previous_state="DISCOVERED",
        requested_state="ACTIONABLE" if actionable else "DISCOVERED",
        geometry=geometry,
        structural_targets=targets,
        price_zone_admission=admission,
        mode_trigger_evidence=trigger,
        structure_valid=True,
    )
    admission_result = build_e3_actionable_admission(
        geometry=geometry,
        structural_targets=targets,
        executable_price_snapshot=snapshot,
        price_zone_admission=admission,
        mode_trigger_evidence=trigger,
        setup_lifecycle=lifecycle,
    )
    return {
        "geometry": geometry,
        "targets": targets,
        "snapshot": snapshot,
        "admission": admission,
        "trigger": trigger,
        "lifecycle": lifecycle,
        "actionable": admission_result,
        "authority": _authority(targets.tp2_tick),
    }


def _mode_execution_bundle(chain):
    mode = chain["geometry"].mode
    request = build_mode_scan_request(
        mode=mode,
        due_window_id=f"window:e5-{mode.lower()}",
    )
    snapshot = (
        ModeMarketSnapshotEntryV1(
            schema_version=MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
            canonical_symbol="BTC/USDT",
            quote_asset="USDT",
            settle_asset="USDT",
            market_kind="swap",
            active=True,
            linear=True,
            perpetual=True,
            quote_volume_24h=1000,
        ),
    )
    plan = build_mode_scan_execution_plan(
        request=request,
        market_snapshot=snapshot,
        include_optional_context=(mode == "SCALP"),
    )
    symbol_plan = plan.full_evaluation_symbols[0]
    timeframe_evidence = tuple(
        build_mode_timeframe_execution_evidence(
            timeframe_plan=fetch,
            observed_at=OBSERVED_AT,
            raw_candles=_candles_for(fetch),
        )
        for fetch in symbol_plan.candle_fetches
    )
    observations = tuple(
        ModeOiObservationV1(
            schema_version=MODE_OI_OBSERVATION_SCHEMA_VERSION,
            close_time=_utc_text(
                datetime(2026, 7, 30, 6, 20, tzinfo=timezone.utc)
                + timedelta(minutes=5 * index)
            ),
            open_interest=1000 + index,
        )
        for index in range(3)
    )
    oi_evidence = build_mode_oi_execution_evidence(
        mode=plan.mode,
        mode_lineage_sha256=plan.mode_lineage_sha256,
        canonical_symbol=symbol_plan.canonical_symbol,
        observed_at=OBSERVED_AT,
        observations=observations,
        request_invocation_count=1,
    )
    evaluator_payload = build_mode_technical_evaluator_payload(
        trigger_candle_close_at=OBSERVED_AT,
        score=91,
        trend="UPTREND" if chain["geometry"].side == "LONG" else "DOWNTREND",
        bos=True,
        choch=False,
        reference_price=chain["admission"].executable_price_tick,
        reference_candle_at=OBSERVED_AT,
        volume_ratio=2,
        volume_v2_status="OK",
        golden_zone={
            "direction": chain["geometry"].side,
            "low_tick": chain["geometry"].golden_zone_low_tick,
            "high_tick": chain["geometry"].golden_zone_high_tick,
        },
    )
    candidate = build_mode_execution_candidate_row(
        plan=plan,
        symbol_plan=symbol_plan,
        evaluator_payload=evaluator_payload,
        trigger_candle_close_at=OBSERVED_AT,
    )
    outcome = ModeSymbolExecutionOutcomeV1(
        schema_version=MODE_SYMBOL_EXECUTION_OUTCOME_SCHEMA_VERSION,
        policy_version=MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
        mode=plan.mode,
        mode_lineage_sha256=plan.mode_lineage_sha256,
        canonical_symbol=symbol_plan.canonical_symbol,
        full_evaluation_rank=1,
        outcome_kind=OUTCOME_CANDIDATE,
        reason_code=REASON_CANDIDATE_ACCEPTED,
        timeframe_evidence_sha256s=tuple(
            item.evidence_sha256 for item in timeframe_evidence
        ),
        oi_evidence_sha256=oi_evidence.evidence_sha256,
        evaluator_payload_sha256=candidate.payload_sha256,
        candidate_row=candidate,
    )
    result = build_mode_scan_execution_result(
        plan=plan,
        observed_at=OBSERVED_AT,
        outcomes=(outcome,),
        actual_candle_call_count=len(symbol_plan.candle_fetches),
        actual_oi_call_count=1,
        actual_evaluator_invocation_count=1,
        actual_executor_ip_weight=0,
    )
    return result, timeframe_evidence, oi_evidence


def _event(index: int = 1, *, minute: int = 25) -> NormalizedNewsEventV1:
    point_in_time = datetime(2026, 7, 30, 6, minute, tzinfo=timezone.utc)
    return NormalizedNewsEventV1(
        event_namespace="news",
        authoritative_source_namespace="fixture-wire",
        authoritative_source_event_id=f"fixture-event-{index}",
        deterministic_source_key=None,
        normalized_primary_subject="BTC",
        canonical_event_class="REGULATORY",
        normalized_title=f"Fixture event {index}",
        normalized_body=f"Deterministic fixture body {index}.",
        normalized_language="en",
        publication_timestamp_utc=point_in_time - timedelta(minutes=1),
        point_in_time_timestamp_utc=point_in_time,
        material_source_metadata={"edition": "e5-fixture-v1"},
        previous_event_version_id=None,
        event_version_number=1,
        source_snapshot_ref={
            "source_namespace": "fixture-wire",
            "source_id": f"fixture-event-{index}",
        },
        schema_version=EVENT_SCHEMA_VERSION,
    )


def _risk(event: NormalizedNewsEventV1) -> NewsRiskObjectV1:
    return NewsRiskObjectV1(
        policy_version=NEWS_RISK_POLICY_VERSION,
        event_snapshot_id=event.event_snapshot_id,
        adjudication_policy_version="deterministic-adjudication-policy-v1",
        adjudication_result_id="d" * 64,
        route="L0",
        risk_classification="CLEAR",
        news_gate_recommendation="NO_NEWS_RESTRICTION",
        final_ambiguity_state="NONE",
        final_contradiction_state="NONE",
        final_evidence_state="SUFFICIENT",
        final_entity_state="ACCEPTABLE",
        final_source_state="ACCEPTABLE",
        final_material_risk_state="NONE",
        reason_codes=(
            "ADJUDICATION_CONFIRMED",
            "NO_MATERIAL_NEWS_RISK",
            "EVIDENCE_SUFFICIENT",
        ),
        evidence_refs=(event.event_snapshot_id,),
        structured_explanation="news-risk:CLEAR",
        news_risk_object_id=None,
    )


def _bundle(tmp_path: Path, mode="SWING", side="LONG", *, name="payload"):
    chain = _real_chain(mode, side)
    root = tmp_path / name
    root.mkdir()
    store = root / "BTC-USDT.e4-thesis-history.json"
    duplicate = compose_e4_duplicate_protection_v1(
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        authorized_store_root=root,
        store_path=store,
        price_exited_zone=False,
    )
    document = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert document is not None
    event = _event()
    inputs = {
        "actionable_admission": chain["actionable"],
        "candidate_authority": chain["authority"],
        "duplicate_protection_result": duplicate,
        "thesis_history": document.history,
        "mode_profile": get_mode_profile(mode),
        "mode_execution_evidence": _mode_execution_bundle(chain),
        "normalized_news_events": (event,),
        "news_risk_object": _risk(event),
    }
    payload = subject.build_e5_technical_review_payload_v1(**inputs)
    return chain, inputs, payload


def _unsafe_clone(value, **changes):
    clone = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return clone


def _payload_with_registered_binding(payload, binding_sha256):
    temporary = _unsafe_clone(
        payload,
        provider_binding_sha256=binding_sha256,
        payload_sha256="0" * 64,
    )
    payload_sha256 = hashlib.sha256(
        temporary.canonical_payload_json().encode()
    ).hexdigest()
    return replace(
        payload,
        provider_binding_sha256=binding_sha256,
        payload_sha256=payload_sha256,
    )


def _nested_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(
            *(_nested_keys(item) for item in value.values()),
            set(),
        )
    if isinstance(value, (list, tuple)):
        return set().union(*(_nested_keys(item) for item in value), set())
    return set()


def test_exact_versions_field_tuple_and_decision_codes():
    assert subject.E5_PROVIDER_MODEL_PRICE_BINDING_VERSION == (
        "e5-provider-model-price-binding-v1"
    )
    assert subject.E5_PROVIDER_MODEL_PRICE_BINDING_V2_VERSION == (
        "e5-provider-model-price-binding-v2"
    )
    assert subject.E5_PROVIDER_MODEL_PRICE_BINDING_V3_VERSION == (
        "e5-provider-model-price-binding-v3"
    )
    assert subject.E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION == (
        "e5-provider-model-price-binding-v4"
    )
    assert subject.E5_TECHNICAL_REVIEW_PAYLOAD_VERSION == (
        "e5-technical-review-payload-v1"
    )
    assert subject.E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_VERSION == (
        "e5-technical-review-token-preflight-v1"
    )
    assert subject.E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS == EXPECTED_EVIDENCE_FIELDS
    assert subject.E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_DECISION_CODES == (
        "PASS_TOKEN_BUDGET",
        "HOLD_INPUT_TOKEN_LIMIT",
        "HOLD_OUTPUT_TOKEN_LIMIT",
    )


@pytest.mark.parametrize(
    "contract",
    (
        subject.E5ProviderModelPriceBindingV1,
        subject.E5ProviderModelPriceBindingV2,
        subject.E5ProviderModelPriceBindingV3,
        subject.E5ProviderModelPriceBindingV4,
        subject.E5TechnicalReviewPayloadV1,
        subject.E5TechnicalReviewTokenPreflightResultV1,
    ),
)
def test_public_results_are_frozen_and_slotted(contract):
    assert is_dataclass(contract)
    assert contract.__dataclass_params__.frozen is True
    assert "__dict__" not in contract.__dict__


def test_exact_owner_frozen_binding_values():
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    assert binding.deepseek_model_id == "deepseek-v4-pro"
    assert (
        binding.deepseek_input_hard_limit_tokens,
        binding.deepseek_output_hard_limit_tokens,
        binding.deepseek_provider_attempts,
        binding.deepseek_retry_count,
    ) == (4000, 500, 1, 0)
    assert (
        binding.deepseek_cache_hit_input_usd_per_mtok,
        binding.deepseek_cache_miss_input_usd_per_mtok,
        binding.deepseek_output_usd_per_mtok,
    ) == ("0.003625", "0.435", "0.87")
    assert binding.deepseek_pre_ga_unpinned_risk_accepted is True
    assert binding.claude_l1_model_id == "claude-sonnet-5"
    assert (
        binding.claude_l1_input_hard_limit_tokens,
        binding.claude_l1_output_hard_limit_tokens,
        binding.claude_l1_timeout_seconds,
        binding.claude_l1_provider_attempts,
        binding.claude_l1_retry_count,
        binding.claude_l1_base_input_usd_per_mtok,
        binding.claude_l1_output_usd_per_mtok,
        binding.claude_l1_max_cost_micro_usd,
    ) == (4000, 500, 10, 1, 0, "3", "15", 19500)
    assert binding.claude_l2_model_id == "claude-fable-5"
    assert (
        binding.claude_l2_input_hard_limit_tokens,
        binding.claude_l2_output_hard_limit_tokens,
        binding.claude_l2_timeout_seconds,
        binding.claude_l2_provider_attempts,
        binding.claude_l2_retry_count,
        binding.claude_l2_base_input_usd_per_mtok,
        binding.claude_l2_output_usd_per_mtok,
        binding.claude_l2_max_cost_micro_usd,
    ) == (6000, 800, 20, 1, 0, "10", "50", 100000)


def test_exact_owner_policy_ceiling_and_prohibition_values():
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    assert binding.shared_l1_l2_daily_logical_review_ceiling == 9
    assert binding.l2_daily_logical_review_ceiling == 3
    assert binding.maximum_daily_cost_micro_usd == 417000
    assert binding.price_artifact_maximum_age_days == 30
    assert binding.claude_mythos_limited_availability_accepted is False
    assert binding.latest_alias_allowed is False
    assert binding.cross_provider_substitution_allowed is False
    assert binding.malformed_response_prompt_repair_allowed is False
    assert binding.stale_result_reuse_allowed is False
    assert binding.same_invocation_retry_allowed is False


def test_exact_six_artifact_hashes():
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    assert (
        binding.deepseek_models_artifact_sha256,
        binding.deepseek_pricing_artifact_sha256,
        binding.deepseek_updates_artifact_sha256,
        binding.claude_models_artifact_sha256,
        binding.claude_pricing_artifact_sha256,
        binding.claude_deprecations_artifact_sha256,
    ) == (
        "cc58ecae320965aa248bfe54ecf2fb0c7cbb64b44692f96f55089599a81278f5",
        "4c0ad750134543b515a8c7435f2bdda0f7b0f04582bf7546c0045cab47ef245e",
        "144a324a536da41b142d134112905669282a893eb6af081920373d672d5fbfc7",
        "4145151ccbda647f67e4a8ae307559bf6040e3dd5cb6111569076e738c0dbfa8",
        "79d551dd56ebd7caec99833c3740f2c93cb58a64f35dbf87947bf80de11ae78a",
        "7c7ce500f1d2a3af8963b40181bf34b54f3e28ed1f73c0650f39bcae4ff9367b",
    )


def test_binding_canonical_json_and_sha256_are_deterministic():
    first = subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    second = subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    assert first == second
    assert first.canonical_binding_json() == second.canonical_binding_json()
    assert hashlib.sha256(first.canonical_binding_json().encode()).hexdigest() == (
        first.binding_sha256
    )
    assert json.loads(first.canonical_binding_json())["deepseek_model_id"] == (
        "deepseek-v4-pro"
    )


def test_exact_owner_frozen_v2_binding_values():
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v2()
    assert binding.binding_version == "e5-provider-model-price-binding-v2"
    assert binding.deepseek_model_id == "deepseek-v4-pro"
    assert (
        binding.deepseek_input_hard_limit_tokens,
        binding.deepseek_output_hard_limit_tokens,
        binding.deepseek_provider_attempts,
        binding.deepseek_retry_count,
    ) == (4000, 500, 1, 0)
    assert (
        binding.deepseek_cache_hit_input_usd_per_mtok,
        binding.deepseek_cache_miss_input_usd_per_mtok,
        binding.deepseek_output_usd_per_mtok,
    ) == ("0.003625", "0.435", "0.87")
    assert binding.deepseek_pre_ga_unpinned_risk_accepted is True
    assert binding.claude_l1_model_id == "claude-opus-5"
    assert (
        binding.claude_l1_input_hard_limit_tokens,
        binding.claude_l1_output_hard_limit_tokens,
        binding.claude_l1_timeout_seconds,
        binding.claude_l1_provider_attempts,
        binding.claude_l1_retry_count,
        binding.claude_l1_base_input_usd_per_mtok,
        binding.claude_l1_output_usd_per_mtok,
        binding.claude_l1_max_cost_micro_usd,
    ) == (4000, 500, 10, 1, 0, "5", "25", 32500)
    assert (
        binding.claude_l2_model_id,
        binding.claude_l2_input_hard_limit_tokens,
        binding.claude_l2_output_hard_limit_tokens,
        binding.claude_l2_timeout_seconds,
        binding.claude_l2_provider_attempts,
        binding.claude_l2_retry_count,
        binding.claude_l2_base_input_usd_per_mtok,
        binding.claude_l2_output_usd_per_mtok,
        binding.claude_l2_max_cost_micro_usd,
    ) == ("claude-fable-5", 6000, 800, 20, 1, 0, "10", "50", 100000)
    assert binding.shared_l1_l2_daily_logical_review_ceiling == 9
    assert binding.l2_daily_logical_review_ceiling == 3
    assert binding.maximum_daily_cost_micro_usd == 495000
    assert binding.claude_mythos_limited_availability_accepted is False
    assert binding.latest_alias_allowed is False
    assert binding.cross_provider_substitution_allowed is False
    assert binding.malformed_response_prompt_repair_allowed is False
    assert binding.stale_result_reuse_allowed is False
    assert binding.same_invocation_retry_allowed is False
    assert binding.price_artifact_maximum_age_days == 30


def test_v2_preserves_exact_six_artifact_hashes():
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v2()
    assert (
        binding.deepseek_models_artifact_sha256,
        binding.deepseek_pricing_artifact_sha256,
        binding.deepseek_updates_artifact_sha256,
        binding.claude_models_artifact_sha256,
        binding.claude_pricing_artifact_sha256,
        binding.claude_deprecations_artifact_sha256,
    ) == (
        "cc58ecae320965aa248bfe54ecf2fb0c7cbb64b44692f96f55089599a81278f5",
        "4c0ad750134543b515a8c7435f2bdda0f7b0f04582bf7546c0045cab47ef245e",
        "144a324a536da41b142d134112905669282a893eb6af081920373d672d5fbfc7",
        "4145151ccbda647f67e4a8ae307559bf6040e3dd5cb6111569076e738c0dbfa8",
        "79d551dd56ebd7caec99833c3740f2c93cb58a64f35dbf87947bf80de11ae78a",
        "7c7ce500f1d2a3af8963b40181bf34b54f3e28ed1f73c0650f39bcae4ff9367b",
    )


def test_historical_and_active_binding_mappings_are_deterministic_and_distinct():
    v1 = subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    v2 = subject.get_owner_frozen_e5_provider_model_price_binding_v2()
    v3 = subject.get_owner_frozen_e5_provider_model_price_binding_v3()
    v4 = subject.get_owner_frozen_e5_provider_model_price_binding_v4()
    assert v1 == subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    assert v2 == subject.get_owner_frozen_e5_provider_model_price_binding_v2()
    assert v3 == subject.get_owner_frozen_e5_provider_model_price_binding_v3()
    assert v4 == subject.get_owner_frozen_e5_provider_model_price_binding_v4()
    assert v1.binding_sha256 == (
        "0acb1a37dc4b7b308aae7e4f2f5faf7223d735ab0cd070e5a27393b845768eb0"
    )
    assert v2.binding_sha256 == (
        "b6dec84a88151e465cff5ea0a4166b43e93653bcc7fb1668fb72ae65878650a8"
    )
    assert v1.binding_sha256 != v2.binding_sha256
    assert v1.to_mapping()["claude_l1_model_id"] == "claude-sonnet-5"
    assert v2.to_mapping()["claude_l1_model_id"] == "claude-opus-5"
    assert tuple(field.name for field in fields(type(v1))) == tuple(
        field.name for field in fields(type(v2))
    )
    assert subject.E5_REGISTERED_PROVIDER_MODEL_PRICE_BINDING_SHA256S == (
        v1.binding_sha256,
        v2.binding_sha256,
        v3.binding_sha256,
        v4.binding_sha256,
    )
    for binding in (v1, v2):
        assert hashlib.sha256(
            binding.canonical_binding_json().encode()
        ).hexdigest() == binding.binding_sha256


def test_exact_owner_frozen_v3_binding_preimage_timeout_and_sha():
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v3()
    v2 = subject.get_owner_frozen_e5_provider_model_price_binding_v2()
    field_names = tuple(field.name for field in fields(type(binding)))
    canonical = binding.canonical_binding_json()
    preimage = json.loads(canonical)
    v2_preimage = json.loads(v2.canonical_binding_json())
    assert binding.binding_version == "e5-provider-model-price-binding-v3"
    assert len(field_names) == 46
    assert field_names == (
        *(field.name for field in fields(subject.E5ProviderModelPriceBindingV2)),
        "deepseek_timeout_seconds",
    )
    assert len(preimage) == 45
    assert "binding_sha256" not in preimage
    assert preimage["deepseek_timeout_seconds"] == 60
    comparable_v3 = dict(preimage)
    comparable_v3.pop("deepseek_timeout_seconds")
    comparable_v3["binding_version"] = v2_preimage["binding_version"]
    assert comparable_v3 == v2_preimage
    assert type(binding.deepseek_timeout_seconds) is int
    assert len(canonical.encode("utf-8")) == 2104
    assert binding.binding_sha256 == subject.E5_PROVIDER_MODEL_PRICE_BINDING_V3_SHA256
    assert binding.binding_sha256 == (
        "dc2454ffdc7f05978a168f88beaf892e7e04387053a0b91c89da79adccf3778e"
    )
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == (
        binding.binding_sha256
    )
    assert not inspect.signature(
        subject.get_owner_frozen_e5_provider_model_price_binding_v3
    ).parameters


def test_exact_owner_frozen_v4_binding_preimage_policy_and_sha():
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v4()
    v3 = subject.get_owner_frozen_e5_provider_model_price_binding_v3()
    field_names = tuple(field.name for field in fields(type(binding)))
    canonical = binding.canonical_binding_json()
    preimage = json.loads(canonical)
    v3_preimage = json.loads(v3.canonical_binding_json())
    new_values = {
        "deepseek_thinking_mode": "disabled",
        "deepseek_reasoning_effort": "none",
        "claude_l1_thinking_mode": "disabled",
        "claude_l1_effort": "high",
        "claude_l2_thinking_mode": "always_on_adaptive",
        "claude_l2_effort": "high",
        "billed_cost_semantics": (
            "LOCALLY_DERIVED_DETERMINISTIC_COST_USING_VALIDATED_PROVIDER_"
            "USAGE_AND_OWNER_FROZEN_BINDING_PRICES"
        ),
        "claude_cache_input_cost_policy": (
            "CACHE_NOT_REQUESTED_REQUIRE_CACHE_CREATION_AND_CACHE_READ_"
            "COUNTS_BOTH_ZERO_UNTIL_DISTINCT_CACHE_PRICES_ARE_OWNER_FROZEN"
        ),
        "provider_output_limit_activation_status": (
            "NON_PRODUCTION_CANARY_CANDIDATES_NOT_PRODUCTION_PROVEN"
        ),
    }
    assert binding.binding_version == "e5-provider-model-price-binding-v4"
    assert len(field_names) == 55
    assert field_names == (
        *(field.name for field in fields(subject.E5ProviderModelPriceBindingV3)),
        *new_values,
    )
    assert len(preimage) == 54
    assert "binding_sha256" not in preimage
    assert {name: preimage[name] for name in new_values} == new_values
    comparable_v4 = dict(preimage)
    for name in new_values:
        comparable_v4.pop(name)
    comparable_v4["binding_version"] = v3_preimage["binding_version"]
    assert comparable_v4 == v3_preimage
    assert (
        binding.deepseek_output_hard_limit_tokens,
        binding.claude_l1_output_hard_limit_tokens,
        binding.claude_l2_output_hard_limit_tokens,
    ) == (500, 500, 800)
    assert len(canonical.encode("utf-8")) == 2689
    assert binding.binding_sha256 == subject.E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256
    assert binding.binding_sha256 == (
        "4a31dbcb7a0c4daed3215dbe8817002c24b2ead30e7092096c992b322e0fe1d9"
    )
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == (
        binding.binding_sha256
    )
    assert not inspect.signature(
        subject.get_owner_frozen_e5_provider_model_price_binding_v4
    ).parameters


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("deepseek_thinking_mode", "enabled"),
        ("deepseek_reasoning_effort", "high"),
        ("claude_l1_thinking_mode", "adaptive"),
        ("claude_l1_effort", "low"),
        ("claude_l2_thinking_mode", "disabled"),
        ("claude_l2_effort", "medium"),
        ("billed_cost_semantics", "provider_invoice"),
        ("claude_cache_input_cost_policy", "base_input_price"),
        ("provider_output_limit_activation_status", "production_proven"),
        ("deepseek_thinking_mode", True),
        ("deepseek_thinking_mode", None),
        ("deepseek_thinking_mode", " disabled"),
    ),
)
def test_v4_binding_rejects_nonexact_policy_values(field, value):
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v4()
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        replace(binding, **{field: value})


@pytest.mark.parametrize(
    "field",
    (
        "deepseek_thinking_mode",
        "deepseek_reasoning_effort",
        "claude_l1_thinking_mode",
        "claude_l1_effort",
        "claude_l2_thinking_mode",
        "claude_l2_effort",
        "billed_cost_semantics",
        "claude_cache_input_cost_policy",
        "provider_output_limit_activation_status",
    ),
)
def test_v4_binding_rejects_missing_policy_field(field):
    mapping = subject.get_owner_frozen_e5_provider_model_price_binding_v4().to_mapping()
    mapping.pop(field)
    with pytest.raises(TypeError):
        subject.E5ProviderModelPriceBindingV4(**mapping)


@pytest.mark.parametrize("timeout", (True, 0, -1, 1.5, "60", None, 59, 61))
def test_v3_binding_rejects_nonexact_timeout_values(timeout):
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v3()
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        replace(binding, deepseek_timeout_seconds=timeout)


def test_v3_binding_rejects_missing_timeout_field():
    mapping = subject.get_owner_frozen_e5_provider_model_price_binding_v3().to_mapping()
    mapping.pop("deepseek_timeout_seconds")
    with pytest.raises(TypeError):
        subject.E5ProviderModelPriceBindingV3(**mapping)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("claude_l1_model_id", "claude-sonnet-5"),
        ("claude_l1_input_hard_limit_tokens", True),
        ("claude_l1_base_input_usd_per_mtok", "5.0"),
        ("claude_l1_output_usd_per_mtok", "24"),
        ("claude_l1_max_cost_micro_usd", 19500),
        ("maximum_daily_cost_micro_usd", 417000),
    ),
)
def test_v2_binding_rejects_unknown_altered_and_bool_as_int_values(field, value):
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v2()
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        replace(binding, **{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("deepseek_input_hard_limit_tokens", True),
        ("claude_l1_timeout_seconds", False),
        ("maximum_daily_cost_micro_usd", True),
        ("deepseek_model_id", "deepseek-v4-flash"),
        ("claude_l1_model_id", "claude-haiku-4-5-20251001"),
        ("deepseek_cache_miss_input_usd_per_mtok", "0.4350"),
    ),
)
def test_binding_rejects_bool_as_int_alternate_models_and_noncanonical_prices(
    field, value
):
    binding = subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        replace(binding, **{field: value})


def test_payload_public_signature_is_exact_and_excludes_envelope_fields():
    parameters = inspect.signature(
        subject.build_e5_technical_review_payload_v1
    ).parameters
    assert tuple(parameters) == (
        "actionable_admission",
        "candidate_authority",
        "duplicate_protection_result",
        "thesis_history",
        "mode_profile",
        "mode_execution_evidence",
        "normalized_news_events",
        "news_risk_object",
    )
    assert EXCLUDED_PUBLICATION_FIELDS.isdisjoint(parameters)
    assert "current_price" not in parameters
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        and item.default is inspect.Parameter.empty
        for item in parameters.values()
    )


@pytest.mark.parametrize(("mode", "side"), MODES_AND_SIDES)
def test_six_real_mode_side_chains_build_and_retain_exact_identities(
    tmp_path, mode, side
):
    chain, inputs, payload = _bundle(
        tmp_path, mode, side, name=f"{mode.lower()}-{side.lower()}"
    )
    mapping = payload.to_mapping()
    assert payload.mode == mode
    assert mapping["thesis_fingerprint"]["identity"]["side"] == side
    assert mapping["thesis_fingerprint"]["identity"]["mode"] == mode
    assert mapping["thesis_fingerprint"]["identity_sha256"] == (
        inputs["duplicate_protection_result"].fingerprint.identity_sha256
    )
    assert mapping["golden_zone"] == {
        "geometry_sha256": chain["geometry"].geometry_sha256,
        "high_tick": chain["geometry"].golden_zone_high_tick,
        "low_tick": chain["geometry"].golden_zone_low_tick,
    }
    assert payload.provider_binding_sha256 == (
        subject.get_owner_frozen_e5_provider_model_price_binding_v4().binding_sha256
    )


def test_payload_mapping_projection_binds_all_nineteen_evidence_categories(tmp_path):
    chain, inputs, payload = _bundle(tmp_path)
    mapping = payload.to_mapping()
    assert tuple(key for key in mapping if key in EXPECTED_EVIDENCE_FIELDS) == (
        EXPECTED_EVIDENCE_FIELDS
    )
    assert mapping["executable_price"] == {
        "admission_sha256": chain["admission"].admission_sha256,
        "executable_price_source": chain["admission"].executable_price_source,
        "executable_price_tick": chain["admission"].executable_price_tick,
        "snapshot_sha256": chain["snapshot"].snapshot_sha256,
    }
    assert mapping["exchange_timestamp"]["exchange_timestamp"] == OBSERVED_AT
    assert mapping["anchors"]["anchor_low_at"] == chain["geometry"].anchor_low_at
    assert mapping["stop_geometry"]["stop_loss_tick"] == (
        chain["targets"].stop_loss_tick
    )
    assert mapping["target_geometry"]["tp2"]["destination_kind"] == "LIQUIDITY"
    assert mapping["net_rr"]["tp2_rr_denominator"] > 0
    assert mapping["trigger_type"] == chain["trigger"].trigger_rule
    assert mapping["trigger_age"]["trigger_fresh"] is True
    assert mapping["lifecycle_state"]["resulting_state"] == "ACTIONABLE"
    assert mapping["prior_publication_identity"]["current_state"] == (
        "PUBLISHED_PENDING_ENTRY"
    )
    assert mapping["prior_history_identity"]["revision"] == 2
    assert mapping["liquidity_evidence"]["tp2_destination_kind"] == "LIQUIDITY"
    assert mapping["volume_evidence"]["volume_ratio"] == "2"
    assert mapping["open_interest_evidence"]["observation_count"] == 3
    assert mapping["news_and_contradiction_quality"][
        "final_contradiction_state"
    ] == "NONE"
    assert mapping["news_and_contradiction_quality"]["final_evidence_state"] == (
        "SUFFICIENT"
    )
    assert mapping["news_and_contradiction_quality"]["final_source_state"] == (
        "ACCEPTABLE"
    )
    assert mapping["news_and_contradiction_quality"][
        "final_material_risk_state"
    ] == "NONE"
    assert payload.provider_binding_sha256 == (
        subject.get_owner_frozen_e5_provider_model_price_binding_v4().binding_sha256
    )


def test_historical_payload_reconstruction_and_identity_separation(tmp_path):
    _, _, active_v4 = _bundle(tmp_path)
    v1_binding = subject.get_owner_frozen_e5_provider_model_price_binding_v1()
    v2_binding = subject.get_owner_frozen_e5_provider_model_price_binding_v2()
    v3_binding = subject.get_owner_frozen_e5_provider_model_price_binding_v3()
    v4_binding = subject.get_owner_frozen_e5_provider_model_price_binding_v4()
    historical_v1 = _payload_with_registered_binding(
        active_v4,
        v1_binding.binding_sha256,
    )
    historical_v2 = _payload_with_registered_binding(
        active_v4,
        v2_binding.binding_sha256,
    )
    historical_v3 = _payload_with_registered_binding(
        active_v4,
        v3_binding.binding_sha256,
    )
    assert active_v4.provider_binding_sha256 == v4_binding.binding_sha256
    assert historical_v1.provider_binding_sha256 == v1_binding.binding_sha256
    assert historical_v2.provider_binding_sha256 == v2_binding.binding_sha256
    assert historical_v3.provider_binding_sha256 == v3_binding.binding_sha256
    assert len(
        {
            historical_v1.payload_sha256,
            historical_v2.payload_sha256,
            historical_v3.payload_sha256,
            active_v4.payload_sha256,
        }
    ) == 4
    assert subject.reconstruct_e5_technical_review_payload_v1(
        historical_v1.to_mapping()
    ).to_mapping() == historical_v1.to_mapping()
    assert subject.reconstruct_e5_technical_review_payload_v1(
        historical_v2.to_mapping()
    ).to_mapping() == historical_v2.to_mapping()
    assert subject.reconstruct_e5_technical_review_payload_v1(
        historical_v3.to_mapping()
    ).to_mapping() == historical_v3.to_mapping()
    assert subject.reconstruct_e5_technical_review_payload_v1(
        active_v4.to_mapping()
    ).to_mapping() == active_v4.to_mapping()


def test_unknown_provider_binding_sha_fails_historical_reconstruction(tmp_path):
    _, _, payload = _bundle(tmp_path)
    mapping = payload.to_mapping()
    mapping["provider_binding_sha256"] = "0" * 64
    preimage = dict(mapping)
    preimage.pop("payload_sha256")
    mapping["payload_sha256"] = hashlib.sha256(
        json.dumps(
            preimage,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.reconstruct_e5_technical_review_payload_v1(mapping)


def test_active_builder_has_no_binding_selector_and_always_emits_v4(tmp_path):
    parameters = inspect.signature(
        subject.build_e5_technical_review_payload_v1
    ).parameters
    assert "binding" not in parameters
    assert "binding_version" not in parameters
    assert "provider_binding_sha256" not in parameters
    _, _, payload = _bundle(tmp_path)
    assert payload.provider_binding_sha256 == (
        subject.get_owner_frozen_e5_provider_model_price_binding_v4().binding_sha256
    )


def test_payload_is_deeply_immutable_and_has_no_publication_envelope_keys(tmp_path):
    _, _, payload = _bundle(tmp_path)
    assert not hasattr(payload, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        payload.mode = "SCALP"
    mapping = payload.to_mapping()
    assert EXCLUDED_PUBLICATION_FIELDS.isdisjoint(_nested_keys(mapping))
    assert "current_price" not in _nested_keys(mapping)
    assert "executable_price_tick" in _nested_keys(mapping)
    for field in fields(payload):
        retained = getattr(payload, field.name)
        assert not isinstance(retained, (dict, list))


def test_payload_canonical_json_sha_and_key_order_are_deterministic(tmp_path):
    _, _, payload = _bundle(tmp_path)
    preimage = payload.to_mapping()
    preimage.pop("payload_sha256")
    reversed_mapping = dict(reversed(tuple(preimage.items())))
    expected = json.dumps(
        reversed_mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert expected == payload.canonical_payload_json()
    assert hashlib.sha256(expected.encode()).hexdigest() == payload.payload_sha256


def test_same_evidence_reconstructed_as_new_objects_has_same_payload_identity(tmp_path):
    _, _, first = _bundle(tmp_path, name="first")
    _, _, second = _bundle(tmp_path, name="second")
    assert first.to_mapping() == second.to_mapping()
    assert first.payload_sha256 == second.payload_sha256


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("payload_sha256", "0" * 64),
        ("provider_binding_sha256", "0" * 64),
        ("golden_zone", {}),
        ("relevant_timeframes", ["1h"]),
        ("volume_evidence", (("volume_ratio", float("nan")),)),
        ("open_interest_evidence", (("newest_age_seconds", float("inf")),)),
    ),
)
def test_payload_rejects_wrong_hash_mutable_values_nan_and_infinity(
    tmp_path, field, value
):
    _, _, payload = _bundle(tmp_path)
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        replace(payload, **{field: value})


def test_news_events_are_sorted_deterministically(tmp_path):
    _, inputs, _ = _bundle(tmp_path)
    early = _event(1, minute=20)
    late = _event(2, minute=25)
    inputs["normalized_news_events"] = (late, early)
    inputs["news_risk_object"] = _risk(late)
    first = subject.build_e5_technical_review_payload_v1(**inputs)
    inputs["normalized_news_events"] = (early, late)
    second = subject.build_e5_technical_review_payload_v1(**inputs)
    assert first.payload_sha256 == second.payload_sha256
    assert first.to_mapping()["news_and_contradiction_quality"][
        "event_snapshot_ids"
    ] == [early.event_snapshot_id, late.event_snapshot_id]


def test_nonactionable_admission_fails_before_payload_creation(tmp_path):
    _, inputs, _ = _bundle(tmp_path)
    inputs["actionable_admission"] = _real_chain(
        "SWING", "LONG", actionable=False
    )["actionable"]
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.build_e5_technical_review_payload_v1(**inputs)


def test_suppressed_duplicate_result_fails_closed(tmp_path):
    chain, inputs, _ = _bundle(tmp_path)
    duplicate = compose_e4_duplicate_protection_v1(
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        authorized_store_root=tmp_path / "payload",
        store_path=tmp_path / "payload" / "BTC-USDT.e4-thesis-history.json",
        price_exited_zone=False,
    )
    assert duplicate.publication_intent_allowed is False
    inputs["duplicate_protection_result"] = duplicate
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.build_e5_technical_review_payload_v1(**inputs)


@pytest.mark.parametrize(
    "changes",
    (
        {"fingerprint": None},
        {"publication_guard_result": None},
        {"actionable_admission_sha256": "0" * 64},
    ),
)
def test_missing_or_mismatched_duplicate_lineage_fails_closed(
    tmp_path, changes
):
    _, inputs, _ = _bundle(tmp_path)
    inputs["duplicate_protection_result"] = _unsafe_clone(
        inputs["duplicate_protection_result"], **changes
    )
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.build_e5_technical_review_payload_v1(**inputs)


def test_guard_fingerprint_identity_mismatch_fails_closed(tmp_path):
    _, inputs, _ = _bundle(tmp_path)
    duplicate = inputs["duplicate_protection_result"]
    forged_guard = _unsafe_clone(
        duplicate.publication_guard_result,
        candidate_identity_sha256="0" * 64,
    )
    inputs["duplicate_protection_result"] = _unsafe_clone(
        duplicate,
        publication_guard_result=forged_guard,
    )
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.build_e5_technical_review_payload_v1(**inputs)


def test_history_current_fingerprint_mismatch_fails_closed(tmp_path):
    _, inputs, _ = _bundle(tmp_path, name="swing")
    _, other, _ = _bundle(tmp_path, "INTRADAY", "LONG", name="intraday")
    inputs["thesis_history"] = other["thesis_history"]
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.build_e5_technical_review_payload_v1(**inputs)


def test_mode_profile_mismatch_fails_closed(tmp_path):
    _, inputs, _ = _bundle(tmp_path)
    inputs["mode_profile"] = get_mode_profile("SCALP")
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.build_e5_technical_review_payload_v1(**inputs)


def test_cross_thesis_mode_execution_evidence_fails_closed(tmp_path):
    _, inputs, _ = _bundle(tmp_path, name="swing")
    other_chain = _real_chain("SCALP", "LONG")
    inputs["mode_execution_evidence"] = _mode_execution_bundle(other_chain)
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.build_e5_technical_review_payload_v1(**inputs)


def test_stale_or_forged_news_risk_binding_fails_closed(tmp_path):
    _, inputs, _ = _bundle(tmp_path)
    early = _event(1, minute=20)
    late = _event(2, minute=25)
    inputs["normalized_news_events"] = (early, late)
    inputs["news_risk_object"] = _risk(early)
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.build_e5_technical_review_payload_v1(**inputs)


@pytest.mark.parametrize(
    ("measured", "requested", "within", "code"),
    (
        (3999, 499, True, "PASS_TOKEN_BUDGET"),
        (4000, 500, True, "PASS_TOKEN_BUDGET"),
        (4001, 500, False, "HOLD_INPUT_TOKEN_LIMIT"),
        (4000, 501, False, "HOLD_OUTPUT_TOKEN_LIMIT"),
        (4001, 501, False, "HOLD_INPUT_TOKEN_LIMIT"),
    ),
)
def test_deepseek_token_preflight_exact_boundaries_and_priority(
    tmp_path, measured, requested, within, code
):
    _, _, payload = _bundle(tmp_path)
    result = subject.preflight_e5_technical_review_payload_v1(
        payload=payload,
        measured_input_tokens=measured,
        requested_output_tokens=requested,
    )
    assert result.preflight_version == "e5-technical-review-token-preflight-v1"
    assert result.model_id == "deepseek-v4-pro"
    assert result.input_hard_limit_tokens == 4000
    assert result.output_hard_limit_tokens == 500
    assert result.payload_sha256 == payload.payload_sha256
    assert payload.provider_binding_sha256 == (
        subject.get_owner_frozen_e5_provider_model_price_binding_v4().binding_sha256
    )
    assert result.within_limits is within
    assert result.decision_code == code


@pytest.mark.parametrize(
    "binding_getter",
    (
        subject.get_owner_frozen_e5_provider_model_price_binding_v1,
        subject.get_owner_frozen_e5_provider_model_price_binding_v2,
        subject.get_owner_frozen_e5_provider_model_price_binding_v3,
    ),
)
def test_active_token_preflight_rejects_historical_payload(
    tmp_path,
    binding_getter,
):
    _, _, active_v4 = _bundle(tmp_path)
    historical = _payload_with_registered_binding(
        active_v4,
        binding_getter().binding_sha256,
    )
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.preflight_e5_technical_review_payload_v1(
            payload=historical,
            measured_input_tokens=1,
            requested_output_tokens=1,
        )


@pytest.mark.parametrize(
    "binding_getter",
    (
        subject.get_owner_frozen_e5_provider_model_price_binding_v1,
        subject.get_owner_frozen_e5_provider_model_price_binding_v2,
        subject.get_owner_frozen_e5_provider_model_price_binding_v3,
    ),
)
def test_active_slice_03_review_rejects_historical_payload(
    tmp_path,
    binding_getter,
):
    _, _, active_v4 = _bundle(tmp_path)
    historical = _payload_with_registered_binding(
        active_v4,
        binding_getter().binding_sha256,
    )
    with pytest.raises(ValueError, match="^invalid E5 DeepSeek technical review$"):
        deepseek_review.build_e5_deepseek_structured_review_v1(
            payload=historical,
            model_id="deepseek-v4-pro",
            decision=deepseek_review.CLEAR,
            reason_codes=(deepseek_review.CLEAR_NO_MATERIAL_CONFLICT,),
            concise_reason="No material technical conflict.",
            reviewed_evidence_fields=("mode",),
        )


@pytest.mark.parametrize(
    ("measured", "requested"),
    ((-1, 1), (1, -1), (True, 1), (1, False)),
)
def test_token_preflight_rejects_negative_and_bool_counts(
    tmp_path, measured, requested
):
    _, _, payload = _bundle(tmp_path)
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.preflight_e5_technical_review_payload_v1(
            payload=payload,
            measured_input_tokens=measured,
            requested_output_tokens=requested,
        )


def test_token_preflight_hash_is_deterministic_and_tamper_evident(tmp_path):
    _, _, payload = _bundle(tmp_path)
    first = subject.preflight_e5_technical_review_payload_v1(
        payload=payload,
        measured_input_tokens=4000,
        requested_output_tokens=500,
    )
    second = subject.preflight_e5_technical_review_payload_v1(
        payload=payload,
        measured_input_tokens=4000,
        requested_output_tokens=500,
    )
    assert first == second
    assert first.canonical_preflight_json() == second.canonical_preflight_json()
    assert hashlib.sha256(first.canonical_preflight_json().encode()).hexdigest() == (
        first.preflight_sha256
    )
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        replace(first, preflight_sha256="0" * 64)


def test_wrong_payload_hash_is_rejected_by_preflight(tmp_path):
    _, _, payload = _bundle(tmp_path)
    forged = _unsafe_clone(payload, payload_sha256="0" * 64)
    with pytest.raises(ValueError, match="^invalid E5 technical review payload$"):
        subject.preflight_e5_technical_review_payload_v1(
            payload=forged,
            measured_input_tokens=1,
            requested_output_tokens=1,
        )


def test_builder_has_no_claim_or_publication_success_recording_call():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "claim_e4_publication_intent_v1" not in called
    assert "record_e4_publication_success_v1" not in called


def test_zero_provider_publication_and_production_reachability_surface():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                raise AssertionError(
                    "unclassifiable relative import in production module"
                )
            imported_modules.add(node.module)
    forbidden_external_roots = {
        "requests",
        "httpx",
        "anthropic",
        "subprocess",
        "socket",
        "os",
        "uuid",
        "random",
        "secrets",
    }
    assert "os" not in imported_modules
    assert all(
        module.casefold().split(".", 1)[0] != "os"
        for module in imported_modules
    )
    assert all(
        module.casefold().split(".", 1)[0] not in forbidden_external_roots
        for module in imported_modules
    )
    forbidden_project_components = (
        "deepseek",
        "telegram",
        "exchange",
        "active_signal_ledger",
        "provider_transport",
        "service",
        "deployment",
        "slot",
        "pair_lock",
    )
    assert not any(
        component == forbidden
        or component.startswith(f"{forbidden}_")
        for module in imported_modules
        for component in module.casefold().split(".")
        for forbidden in forbidden_project_components
    )
    prohibited_calls = (
        "claim_e4_publication_intent_v1",
        "record_e4_publication_success_v1",
        "sleep",
        "getenv",
        "environ",
        "now",
        "utcnow",
        "time",
        "urlopen",
        "request",
        "post",
        "send",
        "publish",
        "order",
    )
    call_names = {
        node.func.id
        if isinstance(node.func, ast.Name)
        else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert set(prohibited_calls).isdisjoint(call_names)
    assert "tokenizer" not in source.casefold()
    assert "retry" not in {
        node.func.id.casefold()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
