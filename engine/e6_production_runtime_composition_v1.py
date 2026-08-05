"""Passive activation-to-runtime policy mapping for E6 production dispatch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Callable, Final

from engine.controlled_production_signal_cycle_v1 import (
    _GATES,
    ControlledProductionSignalCycleAuthorizationV1,
)
from engine.e6_activation_configuration_v1 import (
    E6ActivationConfigurationV1,
    load_e6_activation_configuration_v1,
)
from engine.e6_deployment_state_binding_v1 import E6DeploymentStateBindingV1
from engine.e6_production_cycle_input_v1 import (
    E6_NO_TRADE_CYCLE_POLICY_V1,
    E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
    E6NoTradeCycleRequestV1,
    E6ProductionDispatchDecisionV1,
    MODE_JOB_SELECTED,
)
from engine.e6_production_e3_bridge_v1 import (
    E6ProductionE3CandidateV1,
    build_e6_production_e3_candidate_v1,
)
from engine.e6_production_market_acquisition_v1 import (
    E6ProductionBinancePublicMarketPortV1,
    E6ProductionMarketAcquisitionErrorV1,
    E6ProductionMarketSnapshotV1,
)
from engine.e6_production_technical_evaluator_v1 import (
    E6ProductionTechnicalEvaluatorV1,
    build_e6_production_mode_scan_result_v1,
)
from engine.mode_router_v1 import build_mode_scan_request
from engine.mode_scan_execution_plan_v1 import build_mode_scan_execution_plan
from engine.mode_scan_executor_v1 import execute_mode_scan_plan


_ERROR_CODE: Final = "INVALID_E6_PRODUCTION_RUNTIME_COMPOSITION"


class E6ProductionRuntimeCompositionValidationErrorV1(ValueError):
    """Fixed-code fail-closed error for invalid composition output."""

    def __init__(self) -> None:
        self.code = _ERROR_CODE
        super().__init__(_ERROR_CODE)


def _invalid() -> None:
    raise E6ProductionRuntimeCompositionValidationErrorV1() from None


@dataclass(frozen=True, slots=True)
class E6ProductionRuntimeCompositionV1:
    """Validated non-secret decisions supplied explicitly to the public main."""

    activation_configuration: E6ActivationConfigurationV1 = field(repr=False)
    deployment_binding: E6DeploymentStateBindingV1 = field(repr=False)
    e6_enabled: bool
    authorization: ControlledProductionSignalCycleAuthorizationV1
    e6_activation_authorized: bool
    network_authorized: bool
    publication_authorized: bool

    def __post_init__(self) -> None:
        try:
            if type(self.activation_configuration) is not E6ActivationConfigurationV1:
                _invalid()
            self.activation_configuration.__post_init__()
            if (
                type(self.deployment_binding) is not E6DeploymentStateBindingV1
                or self.deployment_binding
                is not self.activation_configuration.deployment_binding
            ):
                _invalid()
            self.deployment_binding.__post_init__()
            if (
                type(self.authorization)
                is not ControlledProductionSignalCycleAuthorizationV1
            ):
                _invalid()
            for name, _reason in _GATES:
                if type(getattr(self.authorization, name)) is not bool:
                    _invalid()
            for decision in (
                self.e6_enabled,
                self.e6_activation_authorized,
                self.network_authorized,
                self.publication_authorized,
            ):
                if type(decision) is not bool:
                    _invalid()
            configuration = self.activation_configuration
            if self.e6_enabled is not (
                configuration.e6_runtime_enabled and configuration.provider_enabled
            ):
                _invalid()
            for name, _reason in _GATES:
                if getattr(self.authorization, name) is not getattr(
                    configuration, name
                ):
                    _invalid()
            if (
                self.e6_activation_authorized is not configuration.activation_gate
                or self.network_authorized is not configuration.network_gate
                or self.publication_authorized
                is not configuration.publication_gate
            ):
                _invalid()
        except E6ProductionRuntimeCompositionValidationErrorV1:
            raise
        except Exception:
            _invalid()


def build_e6_production_runtime_composition_v1(
    *,
    configuration: Mapping[str, str],
    activation_loader: Callable[
        [Mapping[str, str]], E6ActivationConfigurationV1
    ] = load_e6_activation_configuration_v1,
) -> E6ProductionRuntimeCompositionV1:
    """Load the exact activation schema once and map every decision explicitly."""

    if not isinstance(configuration, Mapping) or not callable(activation_loader):
        _invalid()
    loaded = activation_loader(configuration)
    if type(loaded) is not E6ActivationConfigurationV1:
        _invalid()
    loaded.__post_init__()
    authorization = ControlledProductionSignalCycleAuthorizationV1(
        activation_gate=loaded.activation_gate,
        workload_gate=loaded.workload_gate,
        credential_gate=loaded.credential_gate,
        network_gate=loaded.network_gate,
        publication_gate=loaded.publication_gate,
        telegram_publication_gate=loaded.telegram_publication_gate,
    )
    return E6ProductionRuntimeCompositionV1(
        activation_configuration=loaded,
        deployment_binding=loaded.deployment_binding,
        e6_enabled=loaded.e6_runtime_enabled and loaded.provider_enabled,
        authorization=authorization,
        e6_activation_authorized=loaded.activation_gate,
        network_authorized=loaded.network_gate,
        publication_authorized=loaded.publication_gate,
    )


def _canonical_sha256(value: object) -> str:
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        _invalid()
    return sha256(payload.encode("utf-8")).hexdigest()


# M11C_R3_PROFILE_AWARE_NORMAL_RUNTIME_AUTHORIZATION_V1
def _fully_authorized(composition: E6ProductionRuntimeCompositionV1) -> bool:
    common_authorized = (
        composition.e6_enabled is True
        and composition.e6_activation_authorized is True
        and composition.network_authorized is True
        and composition.authorization.activation_gate is True
        and composition.authorization.workload_gate is True
        and composition.authorization.credential_gate is True
        and composition.authorization.network_gate is True
    )
    if not common_authorized:
        return False

    publication_state = (
        composition.publication_authorized,
        composition.authorization.publication_gate,
        composition.authorization.telegram_publication_gate,
    )
    deployment_profile = composition.deployment_binding.deployment_profile

    if deployment_profile == "PRODUCTION":
        return publication_state == (True, True, True)
    if deployment_profile == "CANDIDATE_CANARY":
        return publication_state == (False, False, False)
    return False


def _selected_job_no_trade(
    *,
    decision: E6ProductionDispatchDecisionV1,
    observed_at: str,
    reason_code: str,
    source_reason_code: str,
    scan_composition_sha256: str,
    execution_sha256: str,
    e3_evidence_sha256: str,
) -> E6NoTradeCycleRequestV1:
    audit = _canonical_sha256(
        {
            "domain": "e6-production-selected-job-no-trade-v1",
            "dispatch_evidence_sha256": decision.dispatch_evidence_sha256,
            "reason_code": reason_code,
            "source_reason_code": source_reason_code,
            "scan_composition_sha256": scan_composition_sha256,
            "execution_sha256": execution_sha256,
            "e3_evidence_sha256": e3_evidence_sha256,
        }
    )
    if (
        decision.mode is None
        or decision.due_job_id is None
        or decision.due_window_occurrence_id is None
        or decision.mode_lineage_sha256 is None
    ):
        _invalid()
    return E6NoTradeCycleRequestV1(
        schema_version=E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
        policy_version=E6_NO_TRADE_CYCLE_POLICY_V1,
        source_commit=decision.source_commit,
        outcome_invocation_id=decision.outcome_invocation_id,
        mode=decision.mode,
        due_job_id=decision.due_job_id,
        due_window_occurrence_id=decision.due_window_occurrence_id,
        mode_lineage_sha256=decision.mode_lineage_sha256,
        observed_at=observed_at,
        reason_code=reason_code,
        source_reason_code=source_reason_code,
        scan_composition_sha256=scan_composition_sha256,
        execution_sha256=execution_sha256,
        e3_evidence_sha256=e3_evidence_sha256,
        audit_manifest_sha256=audit,
        provider_attempt_count=0,
        telegram_attempt_count=0,
        exchange_order_count=0,
        slot_mutation_count=0,
        pair_lock_mutation_count=0,
        entry_active_mutation_count=0,
        retry_count=0,
    )


def build_e6_production_selected_job_input_v1(
    *,
    composition: E6ProductionRuntimeCompositionV1,
    dispatch_decision: E6ProductionDispatchDecisionV1,
    observed_at: str,
    market_acquisition_port: E6ProductionBinancePublicMarketPortV1,
    scan_request_builder=build_mode_scan_request,
    scan_plan_builder=build_mode_scan_execution_plan,
    scan_executor=execute_mode_scan_plan,
    technical_evaluator_factory=E6ProductionTechnicalEvaluatorV1,
    technical_result_builder=build_e6_production_mode_scan_result_v1,
    e3_candidate_builder=build_e6_production_e3_candidate_v1,
) -> E6NoTradeCycleRequestV1 | E6ProductionE3CandidateV1:
    """Construct one truthful P2 selected-job input with injected external ports."""

    if type(composition) is not E6ProductionRuntimeCompositionV1:
        _invalid()
    composition.__post_init__()
    if not _fully_authorized(composition):
        _invalid()
    if type(dispatch_decision) is not E6ProductionDispatchDecisionV1:
        _invalid()
    dispatch_decision.__post_init__()
    if (
        dispatch_decision.disposition != MODE_JOB_SELECTED
        or dispatch_decision.observed_at != observed_at
        or dispatch_decision.mode is None
    ):
        _invalid()
    if type(market_acquisition_port) is not E6ProductionBinancePublicMarketPortV1:
        _invalid()
    for dependency in (
        scan_request_builder,
        scan_plan_builder,
        scan_executor,
        technical_evaluator_factory,
        technical_result_builder,
        e3_candidate_builder,
    ):
        if not callable(dependency):
            _invalid()

    snapshot = market_acquisition_port.acquire_market_snapshot(observed_at=observed_at)
    if type(snapshot) is not E6ProductionMarketSnapshotV1:
        _invalid()
    if not snapshot.entries:
        evidence = _canonical_sha256(snapshot.to_mapping())
        return _selected_job_no_trade(
            decision=dispatch_decision,
            observed_at=observed_at,
            reason_code="EMPTY_ELIGIBLE_MARKET",
            source_reason_code="ACTIVE_USDT_LINEAR_PERPETUAL_SET_EMPTY",
            scan_composition_sha256=snapshot.snapshot_sha256,
            execution_sha256=evidence,
            e3_evidence_sha256=evidence,
        )

    request = scan_request_builder(
        mode=dispatch_decision.mode,
        due_window_id=dispatch_decision.due_window_occurrence_id,
    )
    plan = scan_plan_builder(
        request=request,
        market_snapshot=snapshot.entries,
        include_optional_context=False,
    )
    technical_evaluator = technical_evaluator_factory()
    if type(technical_evaluator) is not E6ProductionTechnicalEvaluatorV1:
        _invalid()
    execution = scan_executor(
        plan=plan,
        observed_at=observed_at,
        candle_fetcher=market_acquisition_port.fetch_candles,
        oi_fetcher=market_acquisition_port.fetch_open_interest,
        technical_evaluator=technical_evaluator,
    )
    technical_result = technical_result_builder(
        execution_result=execution,
        technical_evaluator=technical_evaluator,
    )
    if not technical_result.final_top5:
        reason = technical_result.no_trade_reason_code
        if type(reason) is not str:
            _invalid()
        return _selected_job_no_trade(
            decision=dispatch_decision,
            observed_at=observed_at,
            reason_code=reason,
            source_reason_code="DETERMINISTIC_MODE_SCAN_INSUFFICIENT",
            scan_composition_sha256=plan.plan_sha256,
            execution_sha256=execution.execution_sha256,
            e3_evidence_sha256=technical_result.result_sha256,
        )

    candidate = technical_result.final_top5[0]
    evidence_by_id = {
        item.candidate_id: item for item in technical_result.evidence_registry
    }
    technical_evidence = evidence_by_id.get(candidate.candidate_id)
    if technical_evidence is None:
        _invalid()
    try:
        quote = market_acquisition_port.fetch_executable_quote(
            canonical_symbol=candidate.symbol,
            observed_at=observed_at,
        )
    except E6ProductionMarketAcquisitionErrorV1 as exc:
        if exc.reason_code != "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE":
            raise
        evidence_hash = _canonical_sha256(
            {
                "candidate_id": candidate.candidate_id,
                "technical_evidence_sha256": technical_evidence.evidence_sha256,
                "reason_code": exc.reason_code,
            }
        )
        return _selected_job_no_trade(
            decision=dispatch_decision,
            observed_at=observed_at,
            reason_code=exc.reason_code,
            source_reason_code="EXECUTABLE_QUOTE_BOUNDARY_INCOMPLETE",
            scan_composition_sha256=plan.plan_sha256,
            execution_sha256=execution.execution_sha256,
            e3_evidence_sha256=evidence_hash,
        )
    result = e3_candidate_builder(
        source_commit=dispatch_decision.source_commit,
        outcome_invocation_id=dispatch_decision.outcome_invocation_id,
        due_job_id=dispatch_decision.due_job_id,
        due_window_occurrence_id=dispatch_decision.due_window_occurrence_id,
        observed_at=observed_at,
        mode_scan_result=technical_result,
        candidate=candidate,
        technical_evidence=technical_evidence,
        quote_evidence=quote,
    )
    if type(result) not in (E6NoTradeCycleRequestV1, E6ProductionE3CandidateV1):
        _invalid()
    return result


__all__ = (
    "E6ProductionRuntimeCompositionV1",
    "E6ProductionRuntimeCompositionValidationErrorV1",
    "build_e6_production_runtime_composition_v1",
    "build_e6_production_selected_job_input_v1",
)
