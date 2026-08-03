from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import e6_integrated_orchestrator_v1 as subject
from engine import e6_owner_state_lifecycle_binding_v1 as owner_binding
from engine import e6_publication_envelope_v1 as envelope_module
from engine.e5_provider_invocation_boundary_v1 import (
    MALFORMED_OR_SCHEMA_INVALID_RESPONSE,
    TIMEOUT,
)
from engine.e6_claude_daily_usage_store_v1 import (
    E6ClaudeDailyUsageFileStoreV1,
)
from engine.e6_production_news_evidence_v1 import (
    build_e6_production_unavailable_news_evidence_v1,
)
from test_e5_bounded_final_review_composition_v1 import _transports
from test_e5_technical_review_payload_v1 import (
    _bundle as _payload_bundle,
    _real_chain,
)
from test_e6_owner_state_lifecycle_binding_v1 import (
    _completed_publication_evidence,
)
from test_e6_publication_envelope_v1 import _envelope


NOW = "2026-07-30T13:00:00Z"


def _new_ports(
    tmp_path: Path,
    *,
    name: str,
    payload,
    decision: str,
    ledger_path: Path | None = None,
    deep_outcome: str = "SUCCESS",
    claude_outcome: str = "SUCCESS",
):
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    e4_root = root / "e4"
    e4_root.mkdir()
    usage_root = root / "usage"
    usage_root.mkdir()
    if ledger_path is None:
        ledger_path = root / "owner" / "active-ledger.json"
        ledger_path.parent.mkdir()
        active.initialize_ledger(
            ledger_path,
            created_at="2026-07-30T12:00:00Z",
        )
    deepseek, claude, deep_calls, claude_calls = _transports(
        payload,
        decision,
        deep_outcome=deep_outcome,
        claude_outcome=claude_outcome,
    )
    ports = subject.E6IntegratedOrchestratorPortsV1(
        e4_authorized_store_root=e4_root,
        e4_store_path=e4_root / "BTC-USDT.e4-thesis-history.json",
        usage_store=E6ClaudeDailyUsageFileStoreV1(
            authorized_store_root=usage_root
        ),
        active_ledger_path=ledger_path,
        deepseek_transport=deepseek,
        claude_transport=claude,
    )
    return ports, deep_calls, claude_calls


def _scenario(
    tmp_path: Path,
    *,
    name: str,
    decision: str = "CLEAR",
    mode: str = "SWING",
    side: str = "LONG",
    score: int = 80,
    floor: int = 70,
    hard_gates: bool = True,
    deep_outcome: str = "SUCCESS",
    claude_outcome: str = "SUCCESS",
    claude_measured: int | None = None,
    ledger_path: Path | None = None,
):
    chain, inputs, payload = _payload_bundle(
        tmp_path,
        mode,
        side,
        name=f"{name}-payload-preview",
    )
    reference_decision = (
        decision
        if decision in {"CLEAR", "CAUTION"}
        and hard_gates
        and score > floor
        and deep_outcome == "SUCCESS"
        and claude_outcome == "SUCCESS"
        and (claude_measured is None or claude_measured <= 4000)
        else "CLEAR"
    )
    reference, *_ = _envelope(
        tmp_path,
        reference_decision,
        mode=mode,
        side=side,
        name=f"{name}-publication-reference",
    )
    publication = _completed_publication_evidence(reference)
    claude_required = decision in {"CAUTION", "HOLD"}
    request = subject.E6IntegratedOrchestratorRequestV1(
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        mode_profile=inputs["mode_profile"],
        mode_execution_evidence=inputs["mode_execution_evidence"],
        normalized_news_events=inputs["normalized_news_events"],
        news_risk_object=inputs["news_risk_object"],
        price_exited_zone=False,
        deterministic_hard_gates_passed=hard_gates,
        pre_review_score=score,
        mode_score_floor=floor,
        commit_timestamp=NOW,
        deepseek_measured_input_tokens=100,
        deepseek_requested_output_tokens=100,
        claude_measured_input_tokens=(
            (100 if claude_measured is None else claude_measured)
            if claude_required
            else None
        ),
        claude_requested_output_tokens=100 if claude_required else None,
        publication_signal_id=publication["signal_id"],
        publication_delivery_id=publication["delivery_id"],
        publication_published_at=publication["published_at"],
        publication_source_payload_hash=publication["source_payload_hash"],
        publication_payload_hash=publication["publication_payload_hash"],
        publication_content_hash=publication["content_hash"],
        publication_symbol=publication["publication_payload"]["symbol"],
        publication_mode=publication["mode"],
    )
    ports, deep_calls, claude_calls = _new_ports(
        tmp_path,
        name=f"{name}-runtime",
        payload=payload,
        decision=decision,
        ledger_path=ledger_path,
        deep_outcome=deep_outcome,
        claude_outcome=claude_outcome,
    )
    return {
        "request": request,
        "ports": ports,
        "payload": payload,
        "reference": reference,
        "deep_calls": deep_calls,
        "claude_calls": claude_calls,
    }


def _run(scenario):
    return subject.run_e6_integrated_orchestrator_v1(
        request=scenario["request"],
        ports=scenario["ports"],
    )


def _assert_no_authority(result) -> None:
    assert result.retry_count == 0
    assert result.telegram_send_count == 0
    assert result.exchange_order_count == 0
    assert result.slot_mutation_count == 0
    assert result.pair_lock_mutation_count == 0
    assert result.entry_active_mutation_count == 0
    assert result.owner_decision_mutation_count == 0


def test_public_contracts_are_frozen_slotted_keyword_only_and_secret_free(
    tmp_path,
):
    scenario = _scenario(tmp_path, name="contract")
    result = _run(scenario)

    for contract in (
        subject.E6IntegratedOrchestratorRequestV1,
        subject.E6IntegratedOrchestratorPortsV1,
        subject.E6IntegratedOrchestratorResultV1,
    ):
        assert contract.__dataclass_params__.frozen
        assert "__dict__" not in contract.__slots__
    with pytest.raises(FrozenInstanceError):
        scenario["request"].publication_mode = "SCALP"
    with pytest.raises(FrozenInstanceError):
        scenario["ports"].active_ledger_path = Path("changed")
    with pytest.raises(FrozenInstanceError):
        result.disposition = subject.HOLD

    signature = inspect.signature(subject.run_e6_integrated_orchestrator_v1)
    assert tuple(signature.parameters) == ("request", "ports")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    request_fields = {field.name.lower() for field in fields(type(scenario["request"]))}
    prohibited = {
        "credential",
        "token",
        "secret",
        "password",
        "telegram_client",
        "exchange_client",
        "http_client",
        "runtime_configuration",
    }
    assert request_fields.isdisjoint(prohibited)
    _assert_no_authority(result)


def test_full_clear_l0_success_is_end_to_end_and_passive(tmp_path):
    scenario = _scenario(tmp_path, name="clear-success")
    result = _run(scenario)
    ledger = active.load_ledger(scenario["ports"].active_ledger_path)

    assert result.disposition == subject.COMPLETE
    assert result.terminal_stage == subject.STAGE_10_COMPLETE
    assert result.reason_code == subject.COMPLETE
    assert result.d6_outcome == "CLEAR"
    assert result.d7_route == "L0"
    assert result.deepseek_provider_attempt_count == 1
    assert result.claude_provider_attempt_count == 0
    assert len(scenario["deep_calls"]) == 1
    assert scenario["claude_calls"] == []
    assert result.publication_envelope is not None
    assert result.publication_envelope.signal_id == (
        scenario["request"].publication_signal_id
    )
    assert result.publication_envelope.thesis_fingerprint_sha256 == (
        result.duplicate_protection_result.fingerprint.identity_sha256
    )
    assert result.rendered_message is not None
    for text in (
        f"Pair: {result.publication_envelope.canonical_pair}",
        f"Direction: {result.publication_envelope.side}",
        f"Style: {result.publication_envelope.mode}",
        "Risk / Reason Codes:",
        "DeepSeek D6: CLEAR",
        "Manual owner confirmation is required before ENTRY_ACTIVE.",
        "This formatter cannot send Telegram or publish the signal.",
    ):
        assert text in result.rendered_message
    assert result.owner_lifecycle_binding.classification == owner_binding.CREATED
    record = ledger["signals"][result.publication_envelope.signal_id]
    assert record["state"] == active.PUBLISHED_PENDING_ENTRY
    assert all(
        item["state"] != active.ENTRY_ACTIVE for item in ledger["signals"].values()
    )
    _assert_no_authority(result)


def test_deterministic_semantic_runs_have_identical_correlation(tmp_path):
    first_scenario = _scenario(tmp_path, name="deterministic-a")
    second_scenario = _scenario(tmp_path, name="deterministic-b")
    first = _run(first_scenario)
    second = _run(second_scenario)

    assert first.request_sha256 == second.request_sha256
    assert first.correlation_sha256 == second.correlation_sha256
    assert first.result_sha256 == second.result_sha256
    assert first.publication_envelope == second.publication_envelope
    assert first.rendered_message == second.rendered_message
    assert first.owner_lifecycle_binding.binding == (
        second.owner_lifecycle_binding.binding
    )
    assert first.result_sha256 == hashlib.sha256(
        subject._canonical_json(
            {
                key: value
                for key, value in first.to_mapping().items()
                if key != "result_sha256"
            }
        ).encode("utf-8")
    ).hexdigest()


def test_exact_owner_registration_replay_is_idempotent(tmp_path):
    first_scenario = _scenario(tmp_path, name="owner-replay-first")
    first = _run(first_scenario)
    ledger_path = first_scenario["ports"].active_ledger_path
    bytes_after_first = ledger_path.read_bytes()

    second_ports, deep_calls, claude_calls = _new_ports(
        tmp_path,
        name="owner-replay-second-runtime",
        payload=first_scenario["payload"],
        decision="CLEAR",
        ledger_path=ledger_path,
    )
    second = subject.run_e6_integrated_orchestrator_v1(
        request=first_scenario["request"],
        ports=second_ports,
    )

    assert first.owner_lifecycle_binding.classification == owner_binding.CREATED
    assert second.disposition == subject.COMPLETE
    assert second.owner_lifecycle_binding.classification == (
        owner_binding.IDEMPOTENT_REPLAY
    )
    assert second.owner_lifecycle_binding.registration_applied is False
    assert ledger_path.read_bytes() == bytes_after_first
    assert len(active.load_ledger(ledger_path)["signals"]) == 1
    assert len(deep_calls) == 1 and claude_calls == []
    _assert_no_authority(second)


def test_e3_non_actionable_terminates_before_e4_and_providers(tmp_path):
    scenario = _scenario(tmp_path, name="e3-hold")
    non_actionable = _real_chain(
        mode="SWING",
        side="LONG",
        actionable=False,
    )["actionable"]
    request = replace(
        scenario["request"],
        actionable_admission=non_actionable,
    )
    result = subject.run_e6_integrated_orchestrator_v1(
        request=request,
        ports=scenario["ports"],
    )

    assert result.disposition == subject.NO_TRADE
    assert result.terminal_stage == subject.STAGE_2_E3_ACTIONABLE_ADMISSION
    assert result.duplicate_protection_result is None
    assert result.deepseek_provider_attempt_count == 0
    assert result.claude_provider_attempt_count == 0
    assert scenario["deep_calls"] == scenario["claude_calls"] == []
    assert result.publication_envelope is None
    assert result.rendered_message is None
    assert result.owner_lifecycle_binding is None
    assert not scenario["ports"].e4_store_path.exists()
    _assert_no_authority(result)


def test_mixed_pair_lineage_fails_at_validation_without_effect(tmp_path):
    scenario = _scenario(tmp_path, name="mixed-lineage")
    request = replace(scenario["request"], publication_symbol="ETH/USDT")
    result = subject.run_e6_integrated_orchestrator_v1(
        request=request,
        ports=scenario["ports"],
    )

    assert result.disposition == subject.HOLD
    assert result.terminal_stage == subject.STAGE_1_VALIDATE_REQUEST_AND_LINEAGE
    assert result.reason_code == "HOLD_REQUEST_OR_LINEAGE"
    assert scenario["deep_calls"] == scenario["claude_calls"] == []
    assert not scenario["ports"].e4_store_path.exists()
    assert active.load_ledger(scenario["ports"].active_ledger_path)["signals"] == {}
    assert result.publication_envelope is None
    assert result.rendered_message is None
    assert result.owner_lifecycle_binding is None
    _assert_no_authority(result)


def test_e4_same_thesis_different_signal_is_suppressed_before_providers(tmp_path):
    scenario = _scenario(tmp_path, name="duplicate")
    first = _run(scenario)
    provider_counts = (
        len(scenario["deep_calls"]),
        len(scenario["claude_calls"]),
    )
    second_request = replace(
        scenario["request"],
        publication_signal_id="PSG-" + "a" * 64,
    )
    second = subject.run_e6_integrated_orchestrator_v1(
        request=second_request,
        ports=scenario["ports"],
    )

    assert first.disposition == subject.COMPLETE
    assert second.disposition == subject.NO_TRADE
    assert second.terminal_stage == subject.STAGE_3_E4_DUPLICATE_PROTECTION
    assert second.duplicate_protection_result is not None
    assert second.duplicate_protection_result.publication_intent_allowed is False
    assert second.deepseek_provider_attempt_count == 0
    assert second.claude_provider_attempt_count == 0
    assert (
        len(scenario["deep_calls"]),
        len(scenario["claude_calls"]),
    ) == provider_counts
    assert second.publication_envelope is None
    assert second.rendered_message is None
    assert second.owner_lifecycle_binding is None
    _assert_no_authority(second)


@pytest.mark.parametrize(
    ("decision", "mode", "side", "expected_route", "claude_count"),
    (
        ("CLEAR", "SWING", "LONG", "L0", 0),
        ("CAUTION", "SWING", "SHORT", "L1", 1),
        ("HOLD", "INTRADAY", "LONG", "L2", 1),
    ),
)
def test_d6_d7_route_matrix_is_bounded(
    tmp_path,
    decision,
    mode,
    side,
    expected_route,
    claude_count,
):
    scenario = _scenario(
        tmp_path,
        name=f"route-{decision.lower()}",
        decision=decision,
        mode=mode,
        side=side,
    )
    result = _run(scenario)

    assert result.d6_outcome == decision
    assert result.d7_route == expected_route
    assert result.deepseek_provider_attempt_count == 1
    assert result.claude_provider_attempt_count == claude_count
    assert len(scenario["deep_calls"]) == 1
    assert len(scenario["claude_calls"]) == claude_count
    assert result.retry_count == 0
    if decision == "HOLD":
        assert result.disposition == subject.NO_TRADE
        assert result.terminal_stage == subject.STAGE_4_DURABLE_E5_EXECUTION
        assert result.publication_envelope is None
        assert result.rendered_message is None
        assert result.owner_lifecycle_binding is None
    else:
        assert result.disposition == subject.COMPLETE
    _assert_no_authority(result)


@pytest.mark.parametrize(
    ("decision", "deep_outcome", "claude_outcome", "deep_count", "claude_count"),
    (
        ("CLEAR", TIMEOUT, "SUCCESS", 1, 0),
        ("CAUTION", "SUCCESS", TIMEOUT, 1, 1),
        ("CLEAR", MALFORMED_OR_SCHEMA_INVALID_RESPONSE, "SUCCESS", 1, 0),
    ),
)
def test_provider_failure_is_one_attempt_no_retry_and_no_stale_reuse(
    tmp_path,
    decision,
    deep_outcome,
    claude_outcome,
    deep_count,
    claude_count,
):
    scenario = _scenario(
        tmp_path,
        name=f"provider-failure-{decision}-{deep_outcome}-{claude_outcome}",
        decision=decision,
        deep_outcome=deep_outcome,
        claude_outcome=claude_outcome,
    )
    result = _run(scenario)

    assert result.disposition == subject.HOLD
    assert result.terminal_stage == subject.STAGE_4_DURABLE_E5_EXECUTION
    assert result.deepseek_provider_attempt_count == deep_count
    assert result.claude_provider_attempt_count == claude_count
    assert len(scenario["deep_calls"]) == deep_count
    assert len(scenario["claude_calls"]) == claude_count
    assert result.retry_count == 0
    assert result.publication_envelope is None
    assert result.rendered_message is None
    assert result.owner_lifecycle_binding is None
    _assert_no_authority(result)


def test_claude_token_preflight_blocks_before_claude_call(tmp_path):
    scenario = _scenario(
        tmp_path,
        name="claude-preflight",
        decision="CAUTION",
        claude_measured=4001,
    )
    result = _run(scenario)

    assert result.disposition == subject.HOLD
    assert result.terminal_stage == subject.STAGE_4_DURABLE_E5_EXECUTION
    assert result.reason_code == "BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT"
    assert result.deepseek_provider_attempt_count == 1
    assert result.claude_provider_attempt_count == 0
    assert len(scenario["deep_calls"]) == 1
    assert scenario["claude_calls"] == []
    assert result.d8_fail_closed_cause == "HOLD_TOKEN_LIMIT"
    assert result.publication_envelope is None
    assert result.rendered_message is None
    assert result.owner_lifecycle_binding is None
    _assert_no_authority(result)


def test_python_final_gate_hold_prevents_all_publication_stages(tmp_path):
    scenario = _scenario(
        tmp_path,
        name="final-gate-hold",
        decision="CLEAR",
        score=70,
        floor=70,
    )
    result = _run(scenario)

    assert result.disposition == subject.NO_TRADE
    assert result.terminal_stage == subject.STAGE_5_PYTHON_FINAL_GATE
    assert result.python_final_gate.final_gate_decision_code == (
        "BLOCK_FINAL_SCORE_AT_OR_BELOW_MODE_FLOOR"
    )
    assert result.publication_eligibility is None
    assert result.publication_envelope is None
    assert result.rendered_message is None
    assert result.owner_lifecycle_binding is None
    assert active.load_ledger(scenario["ports"].active_ledger_path)["signals"] == {}
    _assert_no_authority(result)


def test_ineligible_result_prevents_envelope_message_and_registration(
    tmp_path,
    monkeypatch,
):
    scenario = _scenario(tmp_path, name="eligibility-hold")
    real_evaluator = subject.evaluate_e6_publication_eligibility_v1

    def reject_eligibility(**arguments):
        conflicting = replace(
            arguments["candidate_authority"],
            source_payload_hash="f" * 64,
        )
        return real_evaluator(
            final_strategy_gate_result=arguments["final_strategy_gate_result"],
            actionable_admission=arguments["actionable_admission"],
            candidate_authority=conflicting,
            duplicate_protection_result=arguments["duplicate_protection_result"],
        )

    monkeypatch.setattr(
        subject,
        "evaluate_e6_publication_eligibility_v1",
        reject_eligibility,
    )
    result = _run(scenario)

    assert result.disposition == subject.NO_TRADE
    assert result.terminal_stage == subject.STAGE_6_PUBLICATION_ELIGIBILITY
    assert result.publication_eligibility is not None
    assert result.publication_eligibility.eligible_to_build_publication_envelope is False
    assert result.publication_envelope is None
    assert result.rendered_message is None
    assert result.owner_lifecycle_binding is None
    assert active.load_ledger(scenario["ports"].active_ledger_path)["signals"] == {}
    _assert_no_authority(result)


def test_unavailable_optional_news_is_healthy_no_trade_before_providers(tmp_path):
    scenario = _scenario(tmp_path, name="news-unavailable")
    fingerprint = scenario["payload"].to_mapping()["thesis_fingerprint"]
    evidence = build_e6_production_unavailable_news_evidence_v1(
        candidate_identity_sha256=fingerprint["identity_sha256"],
        scan_started_at=NOW,
        scan_completed_at=NOW,
        declared_source_count=1,
        completed_source_count=0,
    )
    request = replace(
        scenario["request"],
        normalized_news_events=(),
        news_risk_object=None,
        news_evidence=evidence,
    )

    result = subject.run_e6_integrated_orchestrator_v1(
        request=request,
        ports=scenario["ports"],
    )

    assert result.disposition == subject.NO_TRADE
    assert result.reason_code == "NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE"
    assert result.terminal_stage == subject.STAGE_4_DURABLE_E5_EXECUTION
    assert scenario["deep_calls"] == scenario["claude_calls"] == []
    assert result.deepseek_provider_attempt_count == 0
    assert result.claude_provider_attempt_count == 0
    assert result.publication_envelope is None
    assert result.owner_lifecycle_binding is None
    _assert_no_authority(result)


def test_conflicting_owner_binding_replay_holds_without_overwrite(tmp_path):
    first_scenario = _scenario(tmp_path, name="binding-conflict-first")
    first = _run(first_scenario)
    ledger_path = first_scenario["ports"].active_ledger_path
    bytes_before_conflict = ledger_path.read_bytes()
    conflicting_request = replace(
        first_scenario["request"],
        publication_delivery_id="PDL-" + "f" * 64,
    )
    conflict_ports, deep_calls, claude_calls = _new_ports(
        tmp_path,
        name="binding-conflict-second-runtime",
        payload=first_scenario["payload"],
        decision="CLEAR",
        ledger_path=ledger_path,
    )
    conflict = subject.run_e6_integrated_orchestrator_v1(
        request=conflicting_request,
        ports=conflict_ports,
    )

    assert first.owner_lifecycle_binding.classification == owner_binding.CREATED
    assert conflict.disposition == subject.HOLD
    assert conflict.terminal_stage == subject.STAGE_9_OWNER_LIFECYCLE_BINDING
    assert conflict.owner_lifecycle_binding.classification == owner_binding.HOLD_CONFLICT
    assert conflict.owner_lifecycle_binding.registration_applied is False
    assert ledger_path.read_bytes() == bytes_before_conflict
    assert len(active.load_ledger(ledger_path)["signals"]) == 1
    assert len(deep_calls) == 1 and claude_calls == []
    _assert_no_authority(conflict)


def test_source_has_detached_injected_effect_boundary():
    source_path = Path(subject.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    prohibited_modules = {
        "http" + "x",
        "re" + "quests",
        "sock" + "et",
        "telegram",
        "engine.e6_deepseek_http_transport_v1",
        "engine.e6_claude_http_transport_v1",
        "engine.e6_provider_runtime_configuration_v1",
        "engine.production_signal_service_v1",
        "engine.controlled_production_cycle_v1",
        "engine.master_engine_v4",
    }
    assert imported_modules.isdisjoint(prohibited_modules)
    assert "/" + "opt/" not in source
    assert "os.environ" not in source
    assert "getenv(" not in source
    assert "system" + "ctl" not in source
    assert "sub" + "process" not in source
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))
    assert source.count("format_e6_signal_message_v1(envelope)") == 1
    assert source.count("bind_e6_publication_to_owner_state_v1(") == 1
    assert envelope_module.MANUAL_OWNER_AUTHORITY_STATEMENT
