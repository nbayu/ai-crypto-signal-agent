from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from engine import active_signal_ledger_v1 as active
from engine import controlled_production_signal_cycle_v1 as controlled
from engine.e6_service_composition_root_v1 import E6ServiceCycleRequestV1
from engine.phase09r_telegram_delivery_adapter_v1 import (
    Phase09RTelegramDeliveryAdapterV1,
)
from engine.production_signal_contract_v1 import build_delivery_id
from engine.run_production_signal_v1 import main
from engine.telegram_owner_control_state_v1 import initialize_state, load_state
from test_e6_integrated_orchestrator_v1 import _new_ports, _scenario


IDENTITY = "a" * 32
NOW = "2026-07-30T13:00:01Z"
SCENARIO_DESTINATION_ID = "isolated-owner-state-test"


def _authorization(**changes):
    values = {name: True for name, _ in controlled._GATES}
    values.update(changes)
    return controlled.ControlledProductionSignalCycleAuthorizationV1(**values)


def _bomb(calls, name):
    def fail(*_args, **_kwargs):
        calls.append(name)
        raise AssertionError(name)

    return fail


def test_real_path_reachability(tmp_path):
    """The real entrypoint reaches E6 once, remains passive, and replays dry."""

    denied_calls = []
    assert main(
        outcome_invocation_id_provider=_bomb(denied_calls, "identity"),
        e6_runtime_factory=_bomb(denied_calls, "runtime"),
        telegram_config_loader=_bomb(denied_calls, "config"),
        telegram_delivery_adapter_factory=_bomb(denied_calls, "adapter"),
    ) == 2
    assert denied_calls == []

    scenario = _scenario(tmp_path, name="phase09r1-reachability")
    request = scenario["request"]
    assert request.publication_delivery_id == build_delivery_id(
        signal_id=request.publication_signal_id,
        channel="TELEGRAM",
        destination_id=SCENARIO_DESTINATION_ID,
        publication_payload_hash=request.publication_payload_hash,
    )
    control_path = tmp_path / "owner-control.json"
    initialize_state(control_path, timestamp=NOW)
    environment = {
        "TELEGRAM_DESTINATION_ID": SCENARIO_DESTINATION_ID,
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
    }
    config = SimpleNamespace(
        bot_token="fixture-only-token",
        max_response_chars=4000,
    )
    runtime_calls = []
    telegram_attempts = []

    def runtime_factory(*, outcome_invocation_id):
        runtime_calls.append(outcome_invocation_id)
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=scenario["ports"],
            channel="TELEGRAM",
            destination_id=SCENARIO_DESTINATION_ID,
        )

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "result": {"message_id": 919}}

    def fake_post(url, *, json, timeout):
        telegram_attempts.append((url, json, timeout))
        return Response()

    def adapter_factory(value, **kwargs):
        assert value is config
        return Phase09RTelegramDeliveryAdapterV1(
            value,
            http_post=fake_post,
            quota_now_provider=lambda: datetime(
                2026, 7, 30, 13, 0, 1, tzinfo=timezone.utc
            ),
            **kwargs,
        )

    assert main(
        outcome_invocation_id=IDENTITY,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=runtime_factory,
        environment=environment,
        telegram_config_loader=lambda value: config,
        telegram_delivery_adapter_factory=adapter_factory,
    ) == 0

    assert runtime_calls == [IDENTITY]
    assert len(telegram_attempts) == 1
    assert telegram_attempts[0][1]["chat_id"] == SCENARIO_DESTINATION_ID
    assert telegram_attempts[0][1]["text"].startswith(
        "AI CRYPTO SIGNAL — MANUAL OWNER REVIEW"
    )
    state = load_state(control_path)
    binding_key = f"{SCENARIO_DESTINATION_ID}:919"
    binding = state["signal_message_bindings"][binding_key]
    assert binding["signal_id"] == scenario["request"].publication_signal_id
    ledger = active.load_ledger(scenario["ports"].active_ledger_path)
    assert ledger["signals"][binding["signal_id"]]["state"] == (
        active.PUBLISHED_PENDING_ENTRY
    )
    assert active.inspect_capacity(ledger)["active_by_mode"]["SWING"] == 0
    assert active.inspect_capacity(ledger)["total_active"] == 0
    assert not any(
        record["state"] == active.ENTRY_ACTIVE
        for record in ledger["signals"].values()
    )

    before_ledger = scenario["ports"].active_ledger_path.read_bytes()
    before_control = control_path.read_bytes()
    replay_ports, _deep_calls, _claude_calls = _new_ports(
        tmp_path,
        name="phase09r1-reachability-replay",
        payload=scenario["payload"],
        decision="CLEAR",
        ledger_path=scenario["ports"].active_ledger_path,
    )

    def replay_runtime_factory(*, outcome_invocation_id):
        runtime_calls.append(outcome_invocation_id)
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=replay_ports,
            channel="TELEGRAM",
            destination_id=SCENARIO_DESTINATION_ID,
        )

    assert main(
        outcome_invocation_id="b" * 32,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=replay_runtime_factory,
        environment=environment,
        telegram_config_loader=lambda value: config,
        telegram_delivery_adapter_factory=adapter_factory,
    ) == 0
    assert runtime_calls == [IDENTITY, "b" * 32]
    assert len(telegram_attempts) == 1
    assert scenario["ports"].active_ledger_path.read_bytes() == before_ledger
    assert control_path.read_bytes() == before_control

    source = Path(__import__("engine.run_production_signal_v1", fromlist=["x"]).__file__).read_text(
        encoding="utf-8"
    )
    assert "E6ServiceCompositionRootV1" in source
    assert "run_e6_service_cycle_v1" in source
    assert "run_master_engine_v4" not in source
    assert "enable_publication=True" not in source
    assert "mark_entry_active" not in source
    assert "systemctl" not in source
