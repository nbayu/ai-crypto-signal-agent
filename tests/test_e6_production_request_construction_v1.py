from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
import stat

import pytest

import engine.e6_production_request_construction_v1 as subject
from engine.e6_production_cycle_input_v1 import E6NoTradeCycleRequestV1
from engine.e6_production_news_evidence_v1 import (
    NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE,
    RELEVANT_NEWS_PRESENT,
    build_e6_production_present_news_evidence_v1,
    build_e6_production_unavailable_news_evidence_v1,
)
from engine.e6_service_composition_root_v1 import E6ServiceCycleRequestV1
from test_e5_technical_review_payload_v1 import (
    _event,
    _mode_execution_bundle,
    _real_chain,
    _risk,
)
from test_e6_production_e3_bridge_v1 import _build as _candidate
from test_e6_production_runtime_composition_v1 import _mapping
from engine.e6_production_runtime_composition_v1 import (
    build_e6_production_runtime_composition_v1,
)


def _composition():
    enabled = {
        "E6_RUNTIME_ENABLED": "true",
        "E6_PROVIDER_ENABLED": "true",
        "E6_ACTIVATION_GATE": "true",
        "E6_WORKLOAD_GATE": "true",
        "E6_CREDENTIAL_GATE": "true",
        "E6_NETWORK_GATE": "true",
        "E6_PUBLICATION_GATE": "true",
        "E6_TELEGRAM_PUBLICATION_GATE": "true",
    }
    return build_e6_production_runtime_composition_v1(
        configuration=_mapping(**enabled)
    )


def _p3_candidate():
    candidate = _candidate()
    execution_result, timeframe_evidence, oi_evidence = (
        _mode_execution_bundle(_real_chain())
    )
    evidence_by_timeframe = {
        item.timeframe: item for item in timeframe_evidence
    }
    object.__setattr__(
        candidate.mode_scan_result,
        "execution_result",
        execution_result,
    )
    object.__setattr__(
        candidate.technical_evidence,
        "structure_evidence",
        evidence_by_timeframe[candidate.geometry.structure_timeframe],
    )
    object.__setattr__(
        candidate.technical_evidence,
        "trigger_evidence",
        evidence_by_timeframe[candidate.mode_trigger_evidence.trigger_timeframe],
    )
    object.__setattr__(candidate.technical_evidence, "oi_evidence", oi_evidence)
    object.__setattr__(candidate.mode_scan_result, "result_sha256", "8" * 64)
    object.__setattr__(
        candidate,
        "audit_manifest_sha256",
        hashlib.sha256(
            json.dumps(
                candidate._audit_mapping(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest(),
    )
    return candidate


def _state(tmp_path: Path):
    root = tmp_path / "phase09r1"
    owner_root = root / "owner-blueprint"
    owner_root.mkdir(parents=True)
    root.chmod(0o700)
    owner_root.chmod(0o700)
    active = owner_root / "active-signal-ledger-v1.json"
    owner = owner_root / "telegram-owner-control-state-v1.json"
    active.write_text("{}\n", encoding="utf-8")
    owner.write_text("{}\n", encoding="utf-8")
    active.chmod(0o600)
    owner.chmod(0o600)
    return root, active, owner


def test_module_is_passive_and_has_no_fixture_or_shadow_authority() -> None:
    source = inspect.getsource(subject)
    ast.parse(source)
    for forbidden in (
        "from tests",
        "test_",
        "phase_11",
        "shadow",
        "create_order",
        "os.environ",
    ):
        assert forbidden not in source.casefold()


def test_candidate_authority_uses_exact_e3_lineage_and_atomic_audit(tmp_path) -> None:
    candidate = _p3_candidate()
    authority = subject.build_e6_production_candidate_authority_v1(
        candidate=candidate,
        authorized_state_root=tmp_path,
    )

    relative = Path(authority.production_evidence_ref["manifest_path"])
    manifest = tmp_path / relative
    assert relative.parts[:2] == ("e6-production-v1", "audit")
    assert manifest.is_file() and not manifest.is_symlink()
    assert stat.S_IMODE(manifest.stat().st_mode) == 0o600
    assert authority.source_commit == candidate.source_commit
    assert authority.source_evaluation_id == candidate.candidate.candidate_id
    assert authority.source_payload_hash == candidate.audit_manifest_sha256
    assert authority.tp2 > 0
    assert authority.valid_until > candidate.mode_trigger_evidence.trigger_candle_close_at
    assert "owner" not in authority.to_dict()


def test_zero_source_policy_constructs_one_service_request_with_lazy_ports(
    tmp_path,
) -> None:
    candidate = _p3_candidate()
    root, active, owner = _state(tmp_path)
    calls: list[str] = []

    result = subject.build_e6_production_service_cycle_request_v1(
        candidate=candidate,
        composition=_composition(),
        authorized_state_root=root,
        active_ledger_path=active,
        owner_control_state_path=owner,
        destination_id="owner-destination",
        deepseek_transport_factory=lambda: calls.append("deepseek"),
        claude_transport_factory=lambda: calls.append("claude"),
    )

    assert type(result) is E6ServiceCycleRequestV1
    assert calls == []
    request = result.orchestrator_request
    assert request.news_evidence is not None
    assert request.normalized_news_events == ()
    assert request.news_risk_object is None
    assert request.deepseek_measured_input_tokens is None
    assert request.deepseek_requested_output_tokens is None
    assert request.claude_measured_input_tokens is None
    assert request.claude_requested_output_tokens is None
    assert request.production_outcome_invocation_id == candidate.outcome_invocation_id
    assert request.production_due_window_occurrence_id == candidate.due_window_occurrence_id
    assert request.production_evidence_sha256 == candidate.audit_manifest_sha256
    assert result.destination_id == "owner-destination"
    assert stat.S_IMODE((root / "e6-production-v1").stat().st_mode) == 0o700
    assert stat.S_IMODE(result.orchestrator_ports.e4_authorized_store_root.stat().st_mode) == 0o700


def test_unavailable_news_returns_no_trade_before_external_port_construction(
    tmp_path,
) -> None:
    candidate = _p3_candidate()
    root, active, owner = _state(tmp_path)
    calls: list[str] = []

    def unavailable(*, candidate_identity_sha256, observed_at):
        return build_e6_production_unavailable_news_evidence_v1(
            candidate_identity_sha256=candidate_identity_sha256,
            scan_started_at=observed_at,
            scan_completed_at=observed_at,
            declared_source_count=1,
            completed_source_count=0,
        )

    result = subject.build_e6_production_service_cycle_request_v1(
        candidate=candidate,
        composition=_composition(),
        authorized_state_root=root,
        active_ledger_path=active,
        owner_control_state_path=owner,
        destination_id="owner-destination",
        news_evidence_builder=unavailable,
        deepseek_transport_factory=lambda: calls.append("deepseek"),
        claude_transport_factory=lambda: calls.append("claude"),
        usage_store_factory=lambda **_kwargs: calls.append("usage"),
    )

    assert type(result) is E6NoTradeCycleRequestV1
    assert result.reason_code == NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE
    assert result.outcome_invocation_id == candidate.outcome_invocation_id
    assert calls == []
    assert result.provider_attempt_count == result.telegram_attempt_count == 0
    assert result.exchange_order_count == result.slot_mutation_count == 0
    assert result.pair_lock_mutation_count == result.entry_active_mutation_count == 0
    assert result.retry_count == 0


def test_injected_present_news_preserves_strict_cp10_contract(tmp_path) -> None:
    candidate = _p3_candidate()
    root, active, owner = _state(tmp_path)
    event = _event()

    def present(*, candidate_identity_sha256, observed_at):
        evidence = build_e6_production_present_news_evidence_v1(
            candidate_identity_sha256=candidate_identity_sha256,
            scan_started_at=observed_at,
            scan_completed_at=observed_at,
            declared_source_count=1,
            normalized_news_events=(event,),
            news_risk_object=_risk(event),
        )
        assert evidence.status == RELEVANT_NEWS_PRESENT
        return evidence

    result = subject.build_e6_production_service_cycle_request_v1(
        candidate=candidate,
        composition=_composition(),
        authorized_state_root=root,
        active_ledger_path=active,
        owner_control_state_path=owner,
        destination_id="owner-destination",
        news_evidence_builder=present,
    )

    assert type(result) is E6ServiceCycleRequestV1
    assert result.orchestrator_request.normalized_news_events == (event,)
    assert result.orchestrator_request.news_risk_object == _risk(event)


def test_runtime_factory_is_single_use_and_binds_outcome_identity(tmp_path) -> None:
    candidate = _p3_candidate()
    root, active, owner = _state(tmp_path)
    factory = subject.build_e6_production_runtime_factory_v1(
        candidate=candidate,
        composition=_composition(),
        authorized_state_root=root,
        active_ledger_path=active,
        owner_control_state_path=owner,
        destination_id="owner-destination",
    )

    request = factory(outcome_invocation_id=candidate.outcome_invocation_id)
    assert type(request) is E6ServiceCycleRequestV1
    with pytest.raises(subject.E6ProductionRequestConstructionErrorV1):
        factory(outcome_invocation_id=candidate.outcome_invocation_id)


def test_paths_reject_escape_and_symlink(tmp_path) -> None:
    candidate = _p3_candidate()
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(subject.E6ProductionRequestConstructionErrorV1):
        subject.build_e6_production_candidate_authority_v1(
            candidate=candidate,
            authorized_state_root=link,
        )
