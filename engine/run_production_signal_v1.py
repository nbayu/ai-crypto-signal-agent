"""Default-deny local entry point for one explicitly authorized E6 cycle."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path

from engine.controlled_production_signal_cycle_v1 import (
    _GATES,
    ControlledProductionSignalCycleAuthorizationV1,
)
from engine.e6_activation_configuration_v1 import (
    _EXPECTED_KEYS as E6_ACTIVATION_CONFIGURATION_KEYS_V1,
    E6ActivationConfigurationErrorV1,
)
from engine.e6_integrated_orchestrator_v1 import run_e6_integrated_orchestrator_v1
from engine.e6_production_cycle_input_v1 import (
    DUE_WINDOW_ALREADY_HANDLED,
    MODE_JOB_SELECTED,
    NO_MODE_JOB_DUE,
    E6NoTradeCycleRequestV1,
    E6ProductionDispatchDecisionV1,
)
from engine.e6_production_runtime_composition_v1 import (
    E6ProductionRuntimeCompositionV1,
    E6ProductionRuntimeCompositionValidationErrorV1,
    build_e6_production_runtime_composition_v1,
    build_e6_production_selected_job_input_v1,
)
from engine.e6_production_market_acquisition_v1 import (
    build_e6_production_binance_public_market_port_v1,
)
from engine.e6_production_mode_dispatch_v1 import (
    build_e6_production_mode_dispatch_v1,
)
from engine.e6_production_e3_bridge_v1 import E6ProductionE3CandidateV1
from engine.e6_production_request_construction_v1 import (
    build_e6_production_runtime_factory_v1,
)
from engine.e6_service_composition_root_v1 import (
    DELIVERED,
    DRY,
    IDEMPOTENT_REPLAY,
    NO_TRADE as SERVICE_NO_TRADE,
    TELEGRAM_DELIVERY_FAILED,
    STAGE_5_ONE_TELEGRAM_ATTEMPT,
    E6ServiceCompositionRootV1,
    E6ServiceCycleRequestV1,
    E6ServiceCycleResultV1,
    run_e6_service_cycle_v1,
)
from engine.outcome_tracker_v4 import (
    generate_outcome_invocation_id,
    validate_outcome_invocation_id,
)
from engine.phase09r_telegram_delivery_adapter_v1 import (
    Phase09RTelegramDeliveryAdapterV1,
)
from engine.phase09r_observability_v1 import (
    BOUNDARY_NO,
    BOUNDARY_UNKNOWN,
    BOUNDARY_YES,
    PRODUCTION_SIGNAL_SERVICE_FAILED,
    SERVICE_INVOCATION_INVALID,
    E6_PRODUCTION_IDEMPOTENT_REPLAY_V1,
    E6_PRODUCTION_NO_TRADE_V1,
    E6_PRODUCTION_NO_WORK_DUE_V1,
    E6_PRODUCTION_OBSERVABILITY_SCHEMA_V1,
    E6_PRODUCTION_STAGE_DISPATCH_V1,
    E6_PRODUCTION_STAGE_PRODUCTION_INPUT_V1,
    E6ProductionObservabilityEventV1,
    classified_failure,
    emit_e6_production_observability_event_v1,
    emit_exit7_event,
)
from engine.telegram_owner_control_state_v1 import bind_signal_message
from engine.telegram_runtime_v4 import load_telegram_delivery_config


_SAFE_E6_REASON_CODES = frozenset(
    {
        "DELIVERY_COMPLETED",
        "E6_ACTIVATION_NOT_AUTHORIZED",
        "E6_DELIVERY_REPLAY_CONFLICT",
        "E6_ELIGIBILITY_OR_LINEAGE_INVALID",
        "E6_NETWORK_NOT_AUTHORIZED",
        "E6_ORCHESTRATOR_FAILED",
        "E6_ORCHESTRATOR_TERMINAL",
        "E6_PUBLICATION_NOT_AUTHORIZED",
        "IDEMPOTENT_COMPLETED_REPLAY",
        "INVALID_ROOT_OR_REQUEST",
        "NOT_ATTEMPTED",
        "PUBLICATION_COMPLETION_PERSIST_FAILED",
        "PUBLICATION_READBACK_FAILED",
        "QUOTA_EXHAUSTED",
        "SLOTS_FULL",
        "TELEGRAM_DELIVERY_FAILED",
    }
)


class E6ServiceCycleTerminalResult(RuntimeError):
    """Safe category used only for sanitized exit-7 evidence."""


def _safe_e6_reason(reason_code: str) -> str:
    if reason_code in _SAFE_E6_REASON_CODES:
        return reason_code
    return "E6_SERVICE_CYCLE_TERMINAL"


def _return_exit7(
    *,
    stage: str,
    code: str,
    exc: BaseException,
    telegram_boundary_reached: str,
) -> int:
    emit_exit7_event(
        classified_failure(
            failure_stage=stage,
            failure_code=code,
            exc=exc,
            telegram_boundary_reached=telegram_boundary_reached,
        )
    )
    return 7


def _all_six_authorized(value: object) -> bool:
    return bool(
        type(value) is ControlledProductionSignalCycleAuthorizationV1
        and all(getattr(value, name) is True for name, _ in _GATES)
    )


def main(
    *,
    outcome_invocation_id=None,
    outcome_invocation_id_provider=generate_outcome_invocation_id,
    e6_enabled: bool = False,
    authorization: ControlledProductionSignalCycleAuthorizationV1 | None = None,
    e6_activation_authorized: bool = False,
    network_authorized: bool = False,
    publication_authorized: bool = False,
    e6_runtime_factory: Callable[
        ..., E6NoTradeCycleRequestV1 | E6ServiceCycleRequestV1
    ]
    | None = None,
    environment: Mapping[str, str] | None = None,
    telegram_config_loader=load_telegram_delivery_config,
    telegram_delivery_adapter_factory=Phase09RTelegramDeliveryAdapterV1,
    e6_orchestrator=run_e6_integrated_orchestrator_v1,
    e6_service_cycle_runner=run_e6_service_cycle_v1,
    production_observability_emitter=emit_e6_production_observability_event_v1,
):
    """Run E6 only after six cycle gates and four CLI decisions authorize it."""

    if type(e6_enabled) is not bool or e6_enabled is not True:
        return 2
    if not _all_six_authorized(authorization):
        return 2
    for decision in (
        e6_activation_authorized,
        network_authorized,
        publication_authorized,
    ):
        if type(decision) is not bool or decision is not True:
            return 2
    if not callable(e6_runtime_factory):
        return 2
    if not callable(telegram_config_loader):
        return 2
    if not callable(telegram_delivery_adapter_factory):
        return 2
    if not callable(e6_orchestrator) or not callable(e6_service_cycle_runner):
        return 2
    if not callable(production_observability_emitter):
        return 2

    try:
        selected_outcome_invocation_id = (
            outcome_invocation_id
            if outcome_invocation_id is not None
            else outcome_invocation_id_provider()
        )
        selected_outcome_invocation_id = validate_outcome_invocation_id(
            selected_outcome_invocation_id
        )
    except Exception as exc:
        return _return_exit7(
            stage="E6_OUTCOME_INVOCATION_ID",
            code=SERVICE_INVOCATION_INVALID,
            exc=exc,
            telegram_boundary_reached=BOUNDARY_NO,
        )

    selected_environment = os.environ if environment is None else environment
    if not isinstance(selected_environment, Mapping):
        return 2

    try:
        cycle_request = e6_runtime_factory(
            outcome_invocation_id=selected_outcome_invocation_id
        )
    except Exception as exc:
        return _return_exit7(
            stage="E6_RUNTIME_REQUEST_CONSTRUCTION",
            code=SERVICE_INVOCATION_INVALID,
            exc=exc,
            telegram_boundary_reached=BOUNDARY_NO,
        )
    if type(cycle_request) is E6NoTradeCycleRequestV1:
        try:
            cycle_request.__post_init__()
            if cycle_request.outcome_invocation_id != selected_outcome_invocation_id:
                raise ValueError("E6_NO_TRADE_INVOCATION_ID_MISMATCH")
            production_observability_emitter(
                E6ProductionObservabilityEventV1(
                    schema_version=E6_PRODUCTION_OBSERVABILITY_SCHEMA_V1,
                    event_name=E6_PRODUCTION_NO_TRADE_V1,
                    outcome_invocation_id=cycle_request.outcome_invocation_id,
                    observed_at=cycle_request.observed_at,
                    mode=cycle_request.mode,
                    due_window_occurrence_id=(
                        cycle_request.due_window_occurrence_id
                    ),
                    stage=E6_PRODUCTION_STAGE_PRODUCTION_INPUT_V1,
                    reason_code=cycle_request.reason_code,
                    source_reason_code=cycle_request.source_reason_code,
                    evidence_sha256=cycle_request.canonical_payload_sha256(),
                    provider_attempt_count=cycle_request.provider_attempt_count,
                    telegram_attempt_count=cycle_request.telegram_attempt_count,
                    retry_count=cycle_request.retry_count,
                )
            )
        except Exception as exc:
            return _return_exit7(
                stage="E6_RUNTIME_REQUEST_CONSTRUCTION",
                code=SERVICE_INVOCATION_INVALID,
                exc=exc,
                telegram_boundary_reached=BOUNDARY_NO,
            )
        return 0
    if type(cycle_request) is not E6ServiceCycleRequestV1:
        return _return_exit7(
            stage="E6_RUNTIME_REQUEST_CONSTRUCTION",
            code=SERVICE_INVOCATION_INVALID,
            exc=TypeError(),
            telegram_boundary_reached=BOUNDARY_NO,
        )

    destination_id = selected_environment.get("TELEGRAM_DESTINATION_ID")
    control_state_path = selected_environment.get(
        "TELEGRAM_OWNER_CONTROL_STATE_PATH"
    )
    if not isinstance(destination_id, str) or not destination_id.strip():
        return 2
    if not isinstance(control_state_path, str) or not control_state_path.strip():
        return 2
    if cycle_request.destination_id != destination_id:
        return 2

    delivered_bindings: list[dict[str, object]] = []
    adapter_state: dict[str, object] = {}

    def record_binding(*, payload, destination_id, message_id, timestamp):
        delivered_bindings.append(
            {
                "signal_id": payload["signal_id"],
                "canonical_pair": payload["symbol"],
                "style": payload["mode"],
                "telegram_chat_id": destination_id,
                "telegram_message_id": message_id,
                "timestamp": timestamp,
            }
        )

    def lazy_telegram_delivery(payload, *, channel, destination_id):
        try:
            if "adapter" not in adapter_state:
                config = telegram_config_loader(selected_environment)
                adapter_state["adapter"] = telegram_delivery_adapter_factory(
                    config,
                    message_binding_recorder=record_binding,
                )
            return adapter_state["adapter"](
                payload,
                channel=channel,
                destination_id=destination_id,
            )
        except Exception:
            adapter_state["configuration_failed"] = "adapter" not in adapter_state
            raise

    # Preserve the established dependency-injection contract for callers that
    # supply their own complete service runner.  The production runner retains
    # the lazy delivery boundary below, so suppressed production outcomes never
    # construct Telegram configuration or an adapter.
    if e6_service_cycle_runner is not run_e6_service_cycle_v1:
        try:
            config = telegram_config_loader(selected_environment)
            adapter_state["adapter"] = telegram_delivery_adapter_factory(
                config,
                message_binding_recorder=record_binding,
            )
        except Exception:
            return 2

    try:
        root = E6ServiceCompositionRootV1(
            orchestrator=e6_orchestrator,
            telegram_delivery=lazy_telegram_delivery,
            authorization=authorization,
            e6_activation_authorized=e6_activation_authorized,
            network_authorized=network_authorized,
            publication_authorized=publication_authorized,
        )
        result = e6_service_cycle_runner(root=root, request=cycle_request)
    except Exception as exc:
        return _return_exit7(
            stage="E6_SERVICE_CYCLE_INVOCATION",
            code=PRODUCTION_SIGNAL_SERVICE_FAILED,
            exc=exc,
            telegram_boundary_reached=BOUNDARY_UNKNOWN,
        )
    if type(result) is not E6ServiceCycleResultV1:
        return _return_exit7(
            stage="E6_SERVICE_CYCLE_RESULT",
            code=SERVICE_INVOCATION_INVALID,
            exc=TypeError(),
            telegram_boundary_reached=BOUNDARY_UNKNOWN,
        )
    try:
        result.__post_init__()
    except Exception as exc:
        return _return_exit7(
            stage="E6_SERVICE_CYCLE_RESULT",
            code=SERVICE_INVOCATION_INVALID,
            exc=exc,
            telegram_boundary_reached=BOUNDARY_UNKNOWN,
        )

    if result.disposition == DRY:
        return 2
    if result.disposition == SERVICE_NO_TRADE:
        request = cycle_request.orchestrator_request
        if (
            request.production_outcome_invocation_id is not None
            and result.deepseek_provider_attempt_count == 0
            and result.claude_provider_attempt_count == 0
        ):
            try:
                reason_code = _service_no_trade_reason_v1(result)
                production_observability_emitter(
                    E6ProductionObservabilityEventV1(
                        schema_version=E6_PRODUCTION_OBSERVABILITY_SCHEMA_V1,
                        event_name=E6_PRODUCTION_NO_TRADE_V1,
                        outcome_invocation_id=(
                            request.production_outcome_invocation_id
                        ),
                        observed_at=request.production_observed_at,
                        mode=request.publication_mode,
                        due_window_occurrence_id=(
                            request.production_due_window_occurrence_id
                        ),
                        stage=E6_PRODUCTION_STAGE_PRODUCTION_INPUT_V1,
                        reason_code=reason_code,
                        source_reason_code=result.reason_code,
                        evidence_sha256=request.production_evidence_sha256,
                        provider_attempt_count=0,
                        telegram_attempt_count=0,
                        retry_count=0,
                    )
                )
            except Exception as exc:
                return _return_exit7(
                    stage="E6_PRODUCTION_OBSERVABILITY",
                    code=SERVICE_INVOCATION_INVALID,
                    exc=exc,
                    telegram_boundary_reached=BOUNDARY_NO,
                )
        return 0
    if result.disposition == IDEMPOTENT_REPLAY:
        return 0
    if result.disposition != DELIVERED:
        if adapter_state.get("configuration_failed") is True:
            return 2
        if result.reason_code in {"QUOTA_EXHAUSTED", "SLOTS_FULL"}:
            return 5
        if (
            result.terminal_stage == STAGE_5_ONE_TELEGRAM_ATTEMPT
            and getattr(adapter_state.get("adapter"), "malformed_receipt", False) is True
        ):
            return 6
        if (
            result.terminal_stage == STAGE_5_ONE_TELEGRAM_ATTEMPT
            and result.reason_code == TELEGRAM_DELIVERY_FAILED
        ):
            return 5
        return _return_exit7(
            stage=result.terminal_stage,
            code=_safe_e6_reason(result.reason_code),
            exc=E6ServiceCycleTerminalResult(),
            telegram_boundary_reached=(
                BOUNDARY_YES if result.telegram_attempt_count == 1 else BOUNDARY_NO
            ),
        )
    if len(delivered_bindings) != 1:
        return _return_exit7(
            stage="E6_OWNER_STATE_BINDING",
            code="E6_DELIVERY_EVIDENCE_INVALID",
            exc=E6ServiceCycleTerminalResult(),
            telegram_boundary_reached=BOUNDARY_YES,
        )
    binding = delivered_bindings[0]
    if (
        binding["signal_id"] != result.signal_id
        or str(binding["telegram_chat_id"]) != destination_id
    ):
        return _return_exit7(
            stage="E6_OWNER_STATE_BINDING",
            code="E6_DELIVERY_EVIDENCE_INVALID",
            exc=E6ServiceCycleTerminalResult(),
            telegram_boundary_reached=BOUNDARY_YES,
        )
    try:
        bind_signal_message(
            control_state_path,
            signal_id=str(binding["signal_id"]),
            canonical_pair=str(binding["canonical_pair"]),
            style=str(binding["style"]),
            telegram_chat_id=str(binding["telegram_chat_id"]),
            telegram_message_id=int(binding["telegram_message_id"]),
            timestamp=str(binding["timestamp"]),
        )
    except Exception as exc:
        return _return_exit7(
            stage="E6_OWNER_STATE_BINDING",
            code="E6_OWNER_STATE_BINDING_FAILED",
            exc=exc,
            telegram_boundary_reached=BOUNDARY_YES,
        )
    return 0


def _composition_fully_authorizes_dispatch_v1(
    composition: E6ProductionRuntimeCompositionV1,
) -> bool:
    if type(composition) is not E6ProductionRuntimeCompositionV1:
        return False
    try:
        composition.__post_init__()
        from engine.e6_production_runtime_composition_v1 import _fully_authorized
        return _fully_authorized(composition)
    except Exception:
        return False


def _service_no_trade_reason_v1(result: E6ServiceCycleResultV1) -> str:
    if result.reason_code == "SUPPRESS_EXISTING_THESIS":
        return "E4_DUPLICATE_SUPPRESSED"
    if result.reason_code == "NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE":
        return "NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE"
    if result.reason_code.startswith(("INELIGIBLE_", "BLOCK_E")):
        return "PUBLICATION_INELIGIBLE"
    return "E5_TECHNICAL_REVIEW_REJECTED"


def _dispatch_observability_event_v1(
    decision: E6ProductionDispatchDecisionV1,
) -> E6ProductionObservabilityEventV1:
    if decision.disposition == NO_MODE_JOB_DUE:
        event_name = E6_PRODUCTION_NO_WORK_DUE_V1
    elif decision.disposition == DUE_WINDOW_ALREADY_HANDLED:
        event_name = E6_PRODUCTION_IDEMPOTENT_REPLAY_V1
    else:
        raise ValueError("E6_PRODUCTION_DISPATCH_DISPOSITION_INVALID")
    return E6ProductionObservabilityEventV1(
        schema_version=E6_PRODUCTION_OBSERVABILITY_SCHEMA_V1,
        event_name=event_name,
        outcome_invocation_id=decision.outcome_invocation_id,
        observed_at=decision.observed_at,
        mode=decision.mode,
        due_window_occurrence_id=decision.due_window_occurrence_id,
        stage=E6_PRODUCTION_STAGE_DISPATCH_V1,
        reason_code=decision.reason_code,
        source_reason_code=None,
        evidence_sha256=decision.dispatch_evidence_sha256,
        provider_attempt_count=0,
        telegram_attempt_count=0,
        retry_count=0,
    )


def _production_observed_at_v1() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _production_state_paths_v1(
    *,
    configuration: Mapping[str, str],
    composition: E6ProductionRuntimeCompositionV1,
) -> tuple[Path, Path, Path]:
    binding = composition.deployment_binding
    active_value = configuration.get("ACTIVE_SIGNAL_LEDGER_PATH")
    owner_value = configuration.get("TELEGRAM_OWNER_CONTROL_STATE_PATH")
    supplied_authority = {
        "E6_DEPLOYMENT_PROFILE": binding.deployment_profile.value,
        "E6_RELEASE_COMMIT": binding.release_commit,
        "E6_STATE_ROOT": binding.state_root,
        "E6_RUNTIME_LOCK_PATH": binding.runtime_lock,
        "ACTIVE_SIGNAL_LEDGER_PATH": binding.active_ledger_path,
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": binding.owner_state_path,
    }
    if any(configuration.get(key) != value for key, value in supplied_authority.items()):
        raise ValueError("E6_PRODUCTION_STATE_PATH_INVALID")
    if (
        active_value != composition.activation_configuration.deployment_binding.active_ledger_path
        or owner_value
        != composition.activation_configuration.deployment_binding.owner_state_path
    ):
        raise ValueError("E6_PRODUCTION_STATE_PATH_INVALID")
    return (
        Path(binding.state_root),
        Path(binding.active_ledger_path),
        Path(binding.owner_state_path),
    )


def _build_production_dispatch_decision_v1(
    *,
    configuration: Mapping[str, str],
    composition: E6ProductionRuntimeCompositionV1,
) -> E6ProductionDispatchDecisionV1:
    state_root, active_path, owner_path = _production_state_paths_v1(
        configuration=configuration,
        composition=composition,
    )
    return build_e6_production_mode_dispatch_v1(
        source_commit=composition.activation_configuration.release_commit,
        outcome_invocation_id=generate_outcome_invocation_id(),
        observed_at=_production_observed_at_v1(),
        active_ledger_path=active_path,
        owner_control_state_path=owner_path,
        authorized_state_root=state_root,
    )


def _build_production_selected_job_runtime_factory_v1(
    *,
    decision: E6ProductionDispatchDecisionV1,
    configuration: Mapping[str, str],
    composition: E6ProductionRuntimeCompositionV1,
):
    state_root, active_path, owner_path = _production_state_paths_v1(
        configuration=configuration,
        composition=composition,
    )
    destination_id = configuration.get("TELEGRAM_DESTINATION_ID")
    if type(destination_id) is not str or not destination_id.strip():
        raise ValueError("E6_PRODUCTION_DESTINATION_INVALID")
    calls = 0

    def runtime_factory(*, outcome_invocation_id: str):
        nonlocal calls
        if calls != 0 or outcome_invocation_id != decision.outcome_invocation_id:
            raise ValueError("E6_PRODUCTION_RUNTIME_INVOCATION_INVALID")
        calls += 1
        selected = build_e6_production_selected_job_input_v1(
            composition=composition,
            dispatch_decision=decision,
            observed_at=decision.observed_at,
            market_acquisition_port=(
                build_e6_production_binance_public_market_port_v1()
            ),
        )
        if type(selected) is E6NoTradeCycleRequestV1:
            return selected
        if type(selected) is not E6ProductionE3CandidateV1:
            raise TypeError("E6_PRODUCTION_SELECTED_JOB_INPUT_INVALID")
        production_factory = build_e6_production_runtime_factory_v1(
            candidate=selected,
            composition=composition,
            authorized_state_root=state_root,
            active_ledger_path=active_path,
            owner_control_state_path=owner_path,
            destination_id=destination_id,
        )
        return production_factory(outcome_invocation_id=outcome_invocation_id)

    return runtime_factory


def _run_production_module_v1(
    *,
    environment: Mapping[str, str] | None = None,
    runtime_composition_builder=build_e6_production_runtime_composition_v1,
    dispatch_decision_provider=_build_production_dispatch_decision_v1,
    selected_job_runtime_factory_provider=_build_production_selected_job_runtime_factory_v1,
    production_observability_emitter=emit_e6_production_observability_event_v1,
    public_main_runner=main,
    outcome_invocation_id_provider=generate_outcome_invocation_id,
    telegram_config_loader=load_telegram_delivery_config,
    telegram_delivery_adapter_factory=Phase09RTelegramDeliveryAdapterV1,
    e6_orchestrator=run_e6_integrated_orchestrator_v1,
    e6_service_cycle_runner=run_e6_service_cycle_v1,
) -> int:
    """Run one explicit production composition without weakening public main."""

    selected_environment = os.environ if environment is None else environment
    try:
        activation_configuration = {
            key: selected_environment[key]
            for key in E6_ACTIVATION_CONFIGURATION_KEYS_V1
        }
        composition = runtime_composition_builder(
            configuration=activation_configuration
        )
    except (
        KeyError,
        E6ActivationConfigurationErrorV1,
        E6ProductionRuntimeCompositionValidationErrorV1,
    ):
        return 2
    except Exception as exc:
        return _return_exit7(
            stage="E6_PRODUCTION_RUNTIME_COMPOSITION",
            code=SERVICE_INVOCATION_INVALID,
            exc=exc,
            telegram_boundary_reached=BOUNDARY_NO,
        )
    if type(composition) is not E6ProductionRuntimeCompositionV1:
        return _return_exit7(
            stage="E6_PRODUCTION_RUNTIME_COMPOSITION",
            code=SERVICE_INVOCATION_INVALID,
            exc=TypeError(),
            telegram_boundary_reached=BOUNDARY_NO,
        )
    try:
        composition.__post_init__()
    except Exception:
        return 2
    if not _composition_fully_authorizes_dispatch_v1(composition):
        return 2

    if not callable(dispatch_decision_provider):
        return _return_exit7(
            stage="E6_PRODUCTION_DISPATCH",
            code=SERVICE_INVOCATION_INVALID,
            exc=TypeError(),
            telegram_boundary_reached=BOUNDARY_NO,
        )
    try:
        decision = dispatch_decision_provider(
            configuration=selected_environment,
            composition=composition,
        )
        if type(decision) is not E6ProductionDispatchDecisionV1:
            raise TypeError()
        decision.__post_init__()
    except Exception as exc:
        return _return_exit7(
            stage="E6_PRODUCTION_DISPATCH",
            code=SERVICE_INVOCATION_INVALID,
            exc=exc,
            telegram_boundary_reached=BOUNDARY_NO,
        )

    if decision.disposition in {NO_MODE_JOB_DUE, DUE_WINDOW_ALREADY_HANDLED}:
        try:
            production_observability_emitter(
                _dispatch_observability_event_v1(decision)
            )
        except Exception as exc:
            return _return_exit7(
                stage="E6_PRODUCTION_OBSERVABILITY",
                code=SERVICE_INVOCATION_INVALID,
                exc=exc,
                telegram_boundary_reached=BOUNDARY_NO,
            )
        return 0
    if decision.disposition != MODE_JOB_SELECTED:
        return _return_exit7(
            stage="E6_PRODUCTION_DISPATCH",
            code=SERVICE_INVOCATION_INVALID,
            exc=TypeError(),
            telegram_boundary_reached=BOUNDARY_NO,
        )
    if not callable(selected_job_runtime_factory_provider):
        return _return_exit7(
            stage="E6_PRODUCTION_RUNTIME_REQUEST_FACTORY",
            code=SERVICE_INVOCATION_INVALID,
            exc=TypeError(),
            telegram_boundary_reached=BOUNDARY_NO,
        )
    try:
        runtime_factory = selected_job_runtime_factory_provider(
            decision=decision,
            configuration=selected_environment,
            composition=composition,
        )
        if not callable(runtime_factory) or not callable(public_main_runner):
            raise TypeError()
        exit_status = public_main_runner(
            outcome_invocation_id=decision.outcome_invocation_id,
            outcome_invocation_id_provider=outcome_invocation_id_provider,
            e6_enabled=composition.e6_enabled,
            authorization=composition.authorization,
            e6_activation_authorized=composition.e6_activation_authorized,
            network_authorized=composition.network_authorized,
            publication_authorized=composition.publication_authorized,
            e6_runtime_factory=runtime_factory,
            environment=selected_environment,
            telegram_config_loader=telegram_config_loader,
            telegram_delivery_adapter_factory=telegram_delivery_adapter_factory,
            e6_orchestrator=e6_orchestrator,
            e6_service_cycle_runner=e6_service_cycle_runner,
            production_observability_emitter=production_observability_emitter,
        )
        if type(exit_status) is not int:
            raise TypeError()
        return exit_status
    except Exception as exc:
        return _return_exit7(
            stage="E6_PRODUCTION_MAIN_INVOCATION",
            code=PRODUCTION_SIGNAL_SERVICE_FAILED,
            exc=exc,
            telegram_boundary_reached=BOUNDARY_UNKNOWN,
        )


if __name__ == "__main__":
    sys.exit(_run_production_module_v1())
