"""Candidate-present P2-to-E6 production request construction."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Callable, Final, Mapping

from engine.e4_thesis_fingerprint_v1 import build_e4_thesis_fingerprint
from engine.e6_claude_daily_usage_store_v1 import E6ClaudeDailyUsageFileStoreV1
from engine.e6_claude_http_transport_v1 import get_e6_claude_http_transport_v1
from engine.e6_deepseek_http_transport_v1 import get_e6_deepseek_http_transport_v1
from engine.e6_integrated_orchestrator_v1 import (
    E6IntegratedOrchestratorPortsV1,
    E6IntegratedOrchestratorRequestV1,
    run_e6_integrated_orchestrator_v1,
)
from engine.e6_production_cycle_input_v1 import (
    E6_NO_TRADE_CYCLE_POLICY_V1,
    E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
    E6NoTradeCycleRequestV1,
)
from engine.e6_production_e3_bridge_v1 import E6ProductionE3CandidateV1
from engine.e6_production_news_evidence_v1 import (
    NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE,
    E6ProductionNewsEvidenceV1,
    build_e6_production_zero_source_news_evidence_v1,
)
from engine.e6_production_runtime_composition_v1 import (
    E6ProductionRuntimeCompositionV1,
)
from engine.e6_publication_eligibility_v1 import (
    _hash_value as _publication_hash_value,
    _signal_geometry_mapping,
)
from engine.e6_service_composition_root_v1 import (
    E6ServiceCompositionRootV1,
    E6ServiceCycleRequestV1,
)
from engine.mode_profile_v1 import get_mode_profile
from engine.production_candidate_authority_v1 import ProductionCandidateAuthorityV1
from engine.production_signal_contract_v1 import (
    OUTCOME_PUBLISHED_SIGNAL,
    PRODUCTION_SIGNAL_INPUT_SCHEMA,
    build_delivery_id,
    build_publication_payload,
    build_signal_geometry,
    build_signal_id,
)
from engine.validated_pipeline_v4 import MIN_FINAL_RANK_SCORE


E6_PRODUCTION_REQUEST_CONSTRUCTION_POLICY_V1: Final = (
    "e6-production-request-construction-policy-v1"
)
E6_PRODUCTION_RELATIVE_ROOT_V1: Final = Path("e6-production-v1")
E6_PRODUCTION_AUDIT_RELATIVE_ROOT_V1: Final = (
    E6_PRODUCTION_RELATIVE_ROOT_V1 / "audit"
)
E6_PRODUCTION_E4_RELATIVE_ROOT_V1: Final = E6_PRODUCTION_RELATIVE_ROOT_V1 / "e4"
E6_PRODUCTION_CLAUDE_USAGE_RELATIVE_ROOT_V1: Final = (
    E6_PRODUCTION_RELATIVE_ROOT_V1 / "claude-usage"
)
_ERROR: Final = "INVALID_E6_PRODUCTION_REQUEST_CONSTRUCTION"


class E6ProductionRequestConstructionErrorV1(ValueError):
    def __init__(self) -> None:
        self.code = _ERROR
        super().__init__(_ERROR)


def _invalid() -> None:
    raise E6ProductionRequestConstructionErrorV1() from None


def _require(condition: bool) -> None:
    if not condition:
        _invalid()


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        _invalid()


def _digest(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _secure_root(value: object) -> Path:
    _require(isinstance(value, Path) and value.is_absolute())
    root = value
    _require(Path(os.path.normpath(str(root))) == root)
    _require(root.exists() and root.is_dir() and not root.is_symlink())
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current = current / part
        _require(not current.is_symlink())
    return root


def _secure_directory(path: Path, *, root: Path) -> Path:
    _require(path == root or root in path.parents)
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.exists():
            _require(current.is_dir() and not current.is_symlink())
        else:
            current.mkdir(mode=0o700)
        os.chmod(current, 0o700)
    return path


def _atomic_manifest(path: Path, payload: Mapping[str, object]) -> str:
    _require(not path.exists() or (path.is_file() and not path.is_symlink()))
    body = (_canonical_json(payload) + "\n").encode("utf-8")
    digest = sha256(body).hexdigest()
    if path.exists():
        _require(path.read_bytes() == body)
        return digest
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".e6-audit-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()
    _require(stat.S_IMODE(path.stat().st_mode) == 0o600)
    return digest


def _price(tick: int, tick_size: str) -> int | float:
    try:
        value = Decimal(tick) * Decimal(tick_size)
        _require(value.is_finite() and value > 0)
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        _invalid()


def _valid_until(candidate: E6ProductionE3CandidateV1) -> str:
    try:
        trigger = datetime.strptime(
            candidate.mode_trigger_evidence.trigger_candle_close_at,
            "%Y-%m-%dT%H:%M:%SZ",
        ).replace(tzinfo=timezone.utc)
        result = trigger + timedelta(
            seconds=candidate.mode_trigger_evidence.maximum_trigger_age_seconds
        )
        return result.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OverflowError):
        _invalid()


def _validated_owner_paths(
    *,
    authorized_state_root: Path,
    active_ledger_path: Path,
    owner_control_state_path: Path,
) -> tuple[Path, Path, Path]:
    root = _secure_root(authorized_state_root)
    _require(
        isinstance(active_ledger_path, Path)
        and isinstance(owner_control_state_path, Path)
        and active_ledger_path.is_absolute()
        and owner_control_state_path.is_absolute()
        and active_ledger_path.parent == owner_control_state_path.parent
        and active_ledger_path.parent.name == "owner-blueprint"
        and active_ledger_path.parent.parent == root
    )
    _require(
        active_ledger_path.exists()
        and active_ledger_path.is_file()
        and not active_ledger_path.is_symlink()
        and owner_control_state_path.exists()
        and owner_control_state_path.is_file()
        and not owner_control_state_path.is_symlink()
    )
    return root, active_ledger_path, owner_control_state_path


def build_e6_production_candidate_authority_v1(
    *,
    candidate: E6ProductionE3CandidateV1,
    authorized_state_root: Path,
) -> ProductionCandidateAuthorityV1:
    _require(type(candidate) is E6ProductionE3CandidateV1)
    candidate.__post_init__()
    root = _secure_root(authorized_state_root)
    audit_root = _secure_directory(root / E6_PRODUCTION_AUDIT_RELATIVE_ROOT_V1, root=root)
    relative = E6_PRODUCTION_AUDIT_RELATIVE_ROOT_V1 / (
        candidate.audit_manifest_sha256 + ".json"
    )
    manifest_hash = _atomic_manifest(audit_root / relative.name, candidate.to_mapping())
    return ProductionCandidateAuthorityV1(
        source_commit=candidate.source_commit,
        source_evaluation_id=candidate.candidate.candidate_id,
        production_evidence_ref={
            "manifest_hash": manifest_hash,
            "manifest_path": relative.as_posix(),
        },
        component_versions={
            "e3_bridge": candidate.policy_version,
            "mode_profile": candidate.geometry.mode_profile_version,
            "production_request": E6_PRODUCTION_REQUEST_CONSTRUCTION_POLICY_V1,
        },
        tp2=_price(
            candidate.structural_targets.tp2_tick,
            candidate.geometry.tick_size,
        ),
        valid_until=_valid_until(candidate),
        strategy_version="MASTER_ENGINE_E2_E6_V1",
        source_payload_hash=candidate.audit_manifest_sha256,
    )


def _publication_identities(
    *,
    candidate: E6ProductionE3CandidateV1,
    authority: ProductionCandidateAuthorityV1,
    destination_id: str,
) -> dict[str, object]:
    admission = candidate.actionable_admission
    geometry = candidate.geometry
    targets = candidate.structural_targets
    fingerprint = build_e4_thesis_fingerprint(
        geometry=geometry,
        structural_targets=targets,
        executable_price_snapshot=candidate.executable_price_snapshot,
        mode_trigger_evidence=candidate.mode_trigger_evidence,
        production_candidate_authority=authority,
    )
    signal_geometry_sha256 = _publication_hash_value(
        _signal_geometry_mapping(
            actionable_admission=admission,
            candidate_authority=authority,
            rebuilt_fingerprint=fingerprint,
        )
    )
    setup = {
        "symbol": fingerprint.canonical_pair,
        "side": geometry.side,
        "entry_zone": {
            "min": _price(geometry.golden_zone_low_tick, geometry.tick_size),
            "max": _price(geometry.golden_zone_high_tick, geometry.tick_size),
        },
        "stop_loss": _price(geometry.stop_loss_tick, geometry.tick_size),
        "take_profit": {
            "tp1": _price(targets.tp1_tick, geometry.tick_size),
            "tp2": _price(targets.tp2_tick, geometry.tick_size),
        },
        "valid_until": authority.valid_until,
        "strategy_version": authority.strategy_version,
        "source_payload_hash": authority.source_payload_hash,
    }
    source_envelope = {
        "schema_version": 1,
        "schema_name": PRODUCTION_SIGNAL_INPUT_SCHEMA,
        "source_commit": authority.source_commit,
        "source_evaluation_id": authority.source_evaluation_id,
        "mode": geometry.mode,
        "evaluated_at": admission.price_zone_admission.evaluation_timestamp,
        "production_evidence_ref": dict(authority.production_evidence_ref),
        "outcome_kind": OUTCOME_PUBLISHED_SIGNAL,
        "eligible_setups": [setup],
        "component_versions": dict(authority.component_versions),
    }
    signal_id = build_signal_id(
        source_envelope=source_envelope,
        signal_geometry_hash=signal_geometry_sha256,
        source_payload_hash=authority.source_payload_hash,
    )
    signal_geometry = build_signal_geometry(setup)
    publication_payload = build_publication_payload(
        source_envelope=source_envelope,
        signal_id=signal_id,
        signal_geometry=signal_geometry,
    )
    publication_payload_hash = _digest(publication_payload)
    return {
        "signal_id": signal_id,
        "delivery_id": build_delivery_id(
            signal_id=signal_id,
            channel="TELEGRAM",
            destination_id=destination_id,
            publication_payload_hash=publication_payload_hash,
        ),
        "publication_payload_hash": publication_payload_hash,
        "canonical_pair": fingerprint.canonical_pair,
    }


def build_e6_production_orchestrator_request_v1(
    *,
    candidate: E6ProductionE3CandidateV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    news_evidence: E6ProductionNewsEvidenceV1,
    destination_id: str,
) -> E6IntegratedOrchestratorRequestV1:
    _require(type(candidate) is E6ProductionE3CandidateV1)
    candidate.__post_init__()
    _require(type(candidate_authority) is ProductionCandidateAuthorityV1)
    candidate_authority.__post_init__()
    _require(type(news_evidence) is E6ProductionNewsEvidenceV1)
    news_evidence.__post_init__()
    _require(type(destination_id) is str and bool(destination_id.strip()))
    fingerprint = build_e4_thesis_fingerprint(
        geometry=candidate.geometry,
        structural_targets=candidate.structural_targets,
        executable_price_snapshot=candidate.executable_price_snapshot,
        mode_trigger_evidence=candidate.mode_trigger_evidence,
        production_candidate_authority=candidate_authority,
    )
    _require(news_evidence.candidate_identity_sha256 == fingerprint.identity_sha256)
    identities = _publication_identities(
        candidate=candidate,
        authority=candidate_authority,
        destination_id=destination_id,
    )
    execution = candidate.mode_scan_result.execution_result
    technical = candidate.technical_evidence
    floor = int(MIN_FINAL_RANK_SCORE)
    _require(float(floor) == float(MIN_FINAL_RANK_SCORE))
    return E6IntegratedOrchestratorRequestV1(
        actionable_admission=candidate.actionable_admission,
        candidate_authority=candidate_authority,
        mode_profile=get_mode_profile(candidate.mode),
        mode_execution_evidence=(
            execution,
            (technical.structure_evidence, technical.trigger_evidence),
            technical.oi_evidence,
        ),
        normalized_news_events=news_evidence.normalized_news_events,
        news_risk_object=news_evidence.news_risk_object,
        price_exited_zone=False,
        deterministic_hard_gates_passed=True,
        pre_review_score=int(candidate.technical_score),
        mode_score_floor=floor,
        commit_timestamp=candidate.mode_trigger_evidence.evaluation_timestamp,
        deepseek_measured_input_tokens=None,
        deepseek_requested_output_tokens=None,
        claude_measured_input_tokens=None,
        claude_requested_output_tokens=None,
        publication_signal_id=identities["signal_id"],
        publication_delivery_id=identities["delivery_id"],
        publication_published_at=candidate.mode_trigger_evidence.evaluation_timestamp,
        publication_source_payload_hash=candidate_authority.source_payload_hash,
        publication_payload_hash=identities["publication_payload_hash"],
        publication_content_hash=None,
        publication_symbol=identities["canonical_pair"],
        publication_mode=candidate.mode,
        news_evidence=news_evidence,
        production_outcome_invocation_id=candidate.outcome_invocation_id,
        production_due_window_occurrence_id=(
            candidate.due_window_occurrence_id
        ),
        production_observed_at=(
            candidate.mode_trigger_evidence.evaluation_timestamp
        ),
        production_evidence_sha256=candidate.audit_manifest_sha256,
    )


def build_e6_production_orchestrator_ports_v1(
    *,
    candidate: E6ProductionE3CandidateV1,
    authorized_state_root: Path,
    active_ledger_path: Path,
    owner_control_state_path: Path,
    deepseek_transport_factory: Callable[[], object] = get_e6_deepseek_http_transport_v1,
    claude_transport_factory: Callable[[], object] = get_e6_claude_http_transport_v1,
    usage_store_factory: Callable[..., object] = E6ClaudeDailyUsageFileStoreV1,
) -> E6IntegratedOrchestratorPortsV1:
    _require(type(candidate) is E6ProductionE3CandidateV1)
    candidate.__post_init__()
    root, active_path, _owner = _validated_owner_paths(
        authorized_state_root=authorized_state_root,
        active_ledger_path=active_ledger_path,
        owner_control_state_path=owner_control_state_path,
    )
    _require(
        callable(deepseek_transport_factory)
        and callable(claude_transport_factory)
        and callable(usage_store_factory)
    )
    pair_hash = sha256(candidate.candidate.symbol.encode("utf-8")).hexdigest()
    e4_root = _secure_directory(
        root / E6_PRODUCTION_E4_RELATIVE_ROOT_V1 / pair_hash,
        root=root,
    )
    usage_root = _secure_directory(
        root / E6_PRODUCTION_CLAUDE_USAGE_RELATIVE_ROOT_V1,
        root=root,
    )
    usage_store = usage_store_factory(authorized_store_root=usage_root)
    deepseek_state: dict[str, object] = {}
    claude_state: dict[str, object] = {}

    def deepseek_once(request: object) -> object:
        if "transport" not in deepseek_state:
            transport = deepseek_transport_factory()
            _require(callable(transport))
            deepseek_state["transport"] = transport
        return deepseek_state["transport"](request)

    def claude_once(request: object) -> object:
        if "transport" not in claude_state:
            transport = claude_transport_factory()
            _require(callable(transport))
            claude_state["transport"] = transport
        return claude_state["transport"](request)

    return E6IntegratedOrchestratorPortsV1(
        e4_authorized_store_root=e4_root,
        e4_store_path=e4_root / ".e4-thesis-history.json",
        usage_store=usage_store,
        active_ledger_path=active_path,
        deepseek_transport=deepseek_once,
        claude_transport=claude_once,
    )


def _news_unavailable_no_trade(
    *,
    candidate: E6ProductionE3CandidateV1,
    news_evidence: E6ProductionNewsEvidenceV1,
) -> E6NoTradeCycleRequestV1:
    audit = _digest(
        {
            "domain": E6_PRODUCTION_REQUEST_CONSTRUCTION_POLICY_V1,
            "candidate_audit_manifest_sha256": candidate.audit_manifest_sha256,
            "news_evidence_sha256": news_evidence.evidence_sha256,
            "reason_code": NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE,
        }
    )
    return E6NoTradeCycleRequestV1(
        schema_version=E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
        policy_version=E6_NO_TRADE_CYCLE_POLICY_V1,
        source_commit=candidate.source_commit,
        outcome_invocation_id=candidate.outcome_invocation_id,
        mode=candidate.mode,
        due_job_id=candidate.due_job_id,
        due_window_occurrence_id=candidate.due_window_occurrence_id,
        mode_lineage_sha256=candidate.mode_lineage_sha256,
        observed_at=candidate.mode_trigger_evidence.evaluation_timestamp,
        reason_code=NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE,
        source_reason_code=news_evidence.reason_code,
        scan_composition_sha256=candidate.mode_scan_result.result_sha256,
        execution_sha256=candidate.mode_scan_result.execution_result.execution_sha256,
        e3_evidence_sha256=candidate.audit_manifest_sha256,
        audit_manifest_sha256=audit,
        provider_attempt_count=0,
        telegram_attempt_count=0,
        exchange_order_count=0,
        slot_mutation_count=0,
        pair_lock_mutation_count=0,
        entry_active_mutation_count=0,
        retry_count=0,
    )


def build_e6_production_service_cycle_request_v1(
    *,
    candidate: E6ProductionE3CandidateV1,
    composition: E6ProductionRuntimeCompositionV1,
    authorized_state_root: Path,
    active_ledger_path: Path,
    owner_control_state_path: Path,
    destination_id: str,
    news_evidence_builder: Callable[..., E6ProductionNewsEvidenceV1] = build_e6_production_zero_source_news_evidence_v1,
    deepseek_transport_factory: Callable[[], object] = get_e6_deepseek_http_transport_v1,
    claude_transport_factory: Callable[[], object] = get_e6_claude_http_transport_v1,
    usage_store_factory: Callable[..., object] = E6ClaudeDailyUsageFileStoreV1,
) -> E6NoTradeCycleRequestV1 | E6ServiceCycleRequestV1:
    _require(type(composition) is E6ProductionRuntimeCompositionV1)
    composition.__post_init__()
    _require(
        composition.e6_enabled is True
        and composition.e6_activation_authorized is True
        and composition.network_authorized is True
        and composition.publication_authorized is True
        and all(value is True for _name, value in composition.authorization.to_dict().items())
    )
    authority = build_e6_production_candidate_authority_v1(
        candidate=candidate,
        authorized_state_root=authorized_state_root,
    )
    fingerprint = build_e4_thesis_fingerprint(
        geometry=candidate.geometry,
        structural_targets=candidate.structural_targets,
        executable_price_snapshot=candidate.executable_price_snapshot,
        mode_trigger_evidence=candidate.mode_trigger_evidence,
        production_candidate_authority=authority,
    )
    news = news_evidence_builder(
        candidate_identity_sha256=fingerprint.identity_sha256,
        observed_at=candidate.mode_trigger_evidence.evaluation_timestamp,
    )
    _require(type(news) is E6ProductionNewsEvidenceV1)
    news.__post_init__()
    if news.status == NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE:
        return _news_unavailable_no_trade(candidate=candidate, news_evidence=news)
    request = build_e6_production_orchestrator_request_v1(
        candidate=candidate,
        candidate_authority=authority,
        news_evidence=news,
        destination_id=destination_id,
    )
    ports = build_e6_production_orchestrator_ports_v1(
        candidate=candidate,
        authorized_state_root=authorized_state_root,
        active_ledger_path=active_ledger_path,
        owner_control_state_path=owner_control_state_path,
        deepseek_transport_factory=deepseek_transport_factory,
        claude_transport_factory=claude_transport_factory,
        usage_store_factory=usage_store_factory,
    )
    return E6ServiceCycleRequestV1(
        orchestrator_request=request,
        orchestrator_ports=ports,
        channel="TELEGRAM",
        destination_id=destination_id,
    )


def build_e6_production_service_composition_root_v1(
    *,
    composition: E6ProductionRuntimeCompositionV1,
    telegram_delivery: Callable[..., object],
    orchestrator: Callable[..., object] = run_e6_integrated_orchestrator_v1,
) -> E6ServiceCompositionRootV1:
    _require(type(composition) is E6ProductionRuntimeCompositionV1)
    composition.__post_init__()
    return E6ServiceCompositionRootV1(
        orchestrator=orchestrator,
        telegram_delivery=telegram_delivery,
        authorization=composition.authorization,
        e6_activation_authorized=composition.e6_activation_authorized,
        network_authorized=composition.network_authorized,
        publication_authorized=composition.publication_authorized,
    )


def build_e6_production_runtime_factory_v1(
    *,
    candidate: E6ProductionE3CandidateV1,
    composition: E6ProductionRuntimeCompositionV1,
    authorized_state_root: Path,
    active_ledger_path: Path,
    owner_control_state_path: Path,
    destination_id: str,
    **dependencies: object,
) -> Callable[..., E6NoTradeCycleRequestV1 | E6ServiceCycleRequestV1]:
    _require(type(candidate) is E6ProductionE3CandidateV1)
    candidate.__post_init__()
    calls = 0

    def runtime_factory(*, outcome_invocation_id: str):
        nonlocal calls
        _require(calls == 0)
        calls += 1
        _require(outcome_invocation_id == candidate.outcome_invocation_id)
        return build_e6_production_service_cycle_request_v1(
            candidate=candidate,
            composition=composition,
            authorized_state_root=authorized_state_root,
            active_ledger_path=active_ledger_path,
            owner_control_state_path=owner_control_state_path,
            destination_id=destination_id,
            **dependencies,
        )

    return runtime_factory


__all__ = (
    "E6_PRODUCTION_REQUEST_CONSTRUCTION_POLICY_V1",
    "E6ProductionRequestConstructionErrorV1",
    "build_e6_production_candidate_authority_v1",
    "build_e6_production_orchestrator_request_v1",
    "build_e6_production_orchestrator_ports_v1",
    "build_e6_production_service_composition_root_v1",
    "build_e6_production_service_cycle_request_v1",
    "build_e6_production_runtime_factory_v1",
)
