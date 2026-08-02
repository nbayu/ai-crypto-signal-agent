"""Default-deny local entry point for one explicitly authorized E6 cycle."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping

from engine.controlled_production_signal_cycle_v1 import (
    _GATES,
    ControlledProductionSignalCycleAuthorizationV1,
)
from engine.e6_integrated_orchestrator_v1 import run_e6_integrated_orchestrator_v1
from engine.e6_service_composition_root_v1 import (
    DELIVERED,
    DRY,
    IDEMPOTENT_REPLAY,
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
from engine.telegram_owner_control_state_v1 import bind_signal_message
from engine.telegram_runtime_v4 import load_telegram_delivery_config


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
    e6_runtime_factory=None,
    environment: Mapping[str, str] | None = None,
    telegram_config_loader=load_telegram_delivery_config,
    telegram_delivery_adapter_factory=Phase09RTelegramDeliveryAdapterV1,
    e6_orchestrator=run_e6_integrated_orchestrator_v1,
    e6_service_cycle_runner=run_e6_service_cycle_v1,
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

    try:
        selected_outcome_invocation_id = (
            outcome_invocation_id
            if outcome_invocation_id is not None
            else outcome_invocation_id_provider()
        )
        selected_outcome_invocation_id = validate_outcome_invocation_id(
            selected_outcome_invocation_id
        )
    except Exception:
        return 7

    try:
        selected_environment = os.environ if environment is None else environment
        if not isinstance(selected_environment, Mapping):
            return 2
        config = telegram_config_loader(selected_environment)
        destination_id = selected_environment.get("TELEGRAM_DESTINATION_ID")
        control_state_path = selected_environment.get(
            "TELEGRAM_OWNER_CONTROL_STATE_PATH"
        )
        if not isinstance(destination_id, str) or not destination_id.strip():
            return 2
        if not isinstance(control_state_path, str) or not control_state_path.strip():
            return 2
    except Exception:
        return 2

    try:
        cycle_request = e6_runtime_factory(
            outcome_invocation_id=selected_outcome_invocation_id
        )
        if type(cycle_request) is not E6ServiceCycleRequestV1:
            return 7
    except Exception:
        return 7

    delivered_bindings: list[dict[str, object]] = []

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

    try:
        adapter = telegram_delivery_adapter_factory(
            config,
            message_binding_recorder=record_binding,
        )
        root = E6ServiceCompositionRootV1(
            orchestrator=e6_orchestrator,
            telegram_delivery=adapter,
            authorization=authorization,
            e6_activation_authorized=e6_activation_authorized,
            network_authorized=network_authorized,
            publication_authorized=publication_authorized,
        )
        result = e6_service_cycle_runner(root=root, request=cycle_request)
        if type(result) is not E6ServiceCycleResultV1:
            return 7
        result.__post_init__()
    except Exception:
        return 7

    if result.disposition == DRY:
        return 2
    if result.disposition == IDEMPOTENT_REPLAY:
        return 0
    if result.disposition != DELIVERED:
        if (
            result.terminal_stage == STAGE_5_ONE_TELEGRAM_ATTEMPT
            and getattr(adapter, "malformed_receipt", False) is True
        ):
            return 6
        return 5 if result.terminal_stage == STAGE_5_ONE_TELEGRAM_ATTEMPT else 7
    if len(delivered_bindings) != 1:
        return 7
    binding = delivered_bindings[0]
    if (
        binding["signal_id"] != result.signal_id
        or str(binding["telegram_chat_id"]) != destination_id
    ):
        return 7
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
    except Exception:
        return 7
    return 0


if __name__ == "__main__":
    sys.exit(main())
