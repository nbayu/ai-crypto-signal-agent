from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from engine import active_signal_ledger_v1 as active
from engine import controlled_production_signal_cycle_v1 as controlled
from engine.phase09r_telegram_delivery_adapter_v1 import (
    Phase09RTelegramDeliveryAdapterV1,
)
from engine.run_production_signal_v1 import main
from engine.telegram_owner_control_state_v1 import initialize_state, load_state
from test_e6_integrated_orchestrator_v1 import _new_ports, _scenario
from engine.e6_service_composition_root_v1 import E6ServiceCycleRequestV1


IDENTITY = "a" * 32
NOW = "2026-07-30T13:00:01Z"


def _authorization(**changes):
    values = {name: True for name, _ in controlled._GATES}
    values.update(changes)
    return controlled.ControlledProductionSignalCycleAuthorizationV1(**values)


def _bomb(calls, name):
    def fail(*_args, **_kwargs):
        calls.append(name)
        raise AssertionError(name)

    return fail


def test_default_invocation_is_e6_disabled_and_reads_no_runtime_or_environment():
    calls = []
    assert main(
        outcome_invocation_id_provider=_bomb(calls, "identity"),
        e6_runtime_factory=_bomb(calls, "runtime"),
        telegram_config_loader=_bomb(calls, "telegram-config"),
        telegram_delivery_adapter_factory=_bomb(calls, "telegram-adapter"),
    ) == 2
    assert calls == []


def test_authorized_missing_config_and_destination_return_exact_2():
    calls = []
    common = {
        "outcome_invocation_id": IDENTITY,
        "e6_enabled": True,
        "authorization": _authorization(),
        "e6_activation_authorized": True,
        "network_authorized": True,
        "publication_authorized": True,
        "e6_runtime_factory": _bomb(calls, "runtime"),
        "telegram_delivery_adapter_factory": _bomb(calls, "telegram-adapter"),
    }

    assert main(environment={}, **common) == 2
    assert main(
        environment={
            "TELEGRAM_BOT_TOKEN": "fixture-only-token",
            "TELEGRAM_MAX_MESSAGE_LENGTH": "4000",
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": "fixture-control-state",
        },
        **common,
    ) == 2
    assert calls == []


@pytest.mark.parametrize("field, _reason", controlled._GATES)
def test_every_controlled_gate_is_independently_required_before_construction(
    field, _reason,
):
    calls = []
    assert main(
        outcome_invocation_id=IDENTITY,
        e6_enabled=True,
        authorization=_authorization(**{field: False}),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=_bomb(calls, "runtime"),
        telegram_config_loader=_bomb(calls, "telegram-config"),
        telegram_delivery_adapter_factory=_bomb(calls, "telegram-adapter"),
    ) == 2
    assert calls == []


@pytest.mark.parametrize(
    "field",
    (
        "e6_enabled",
        "e6_activation_authorized",
        "network_authorized",
        "publication_authorized",
    ),
)
def test_each_cli_e6_decision_is_explicit_and_independently_required(field):
    calls = []
    decisions = {
        "e6_enabled": True,
        "e6_activation_authorized": True,
        "network_authorized": True,
        "publication_authorized": True,
    }
    decisions[field] = False
    assert main(
        outcome_invocation_id=IDENTITY,
        authorization=_authorization(),
        e6_runtime_factory=_bomb(calls, "runtime"),
        telegram_config_loader=_bomb(calls, "telegram-config"),
        telegram_delivery_adapter_factory=_bomb(calls, "telegram-adapter"),
        **decisions,
    ) == 2
    assert calls == []


@pytest.mark.parametrize(
    "authorization",
    (
        None,
        {name: True for name, _ in controlled._GATES},
        controlled.ControlledProductionSignalCycleAuthorizationV1(),
    ),
)
def test_invalid_or_partial_authorization_fails_closed(authorization):
    calls = []
    assert main(
        outcome_invocation_id=IDENTITY,
        e6_enabled=True,
        authorization=authorization,
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=_bomb(calls, "runtime"),
        telegram_config_loader=_bomb(calls, "telegram-config"),
    ) == 2
    assert calls == []


def test_invalid_outcome_identity_fails_before_runtime_or_telegram_construction():
    calls = []
    assert main(
        outcome_invocation_id="A" * 32,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=_bomb(calls, "runtime"),
        telegram_config_loader=_bomb(calls, "telegram-config"),
        telegram_delivery_adapter_factory=_bomb(calls, "telegram-adapter"),
    ) == 7
    assert calls == []


def test_missing_outcome_identity_returns_exact_7_before_runtime_or_telegram():
    calls = []
    assert main(
        outcome_invocation_id_provider=lambda: None,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=_bomb(calls, "runtime"),
        telegram_config_loader=_bomb(calls, "telegram-config"),
        telegram_delivery_adapter_factory=_bomb(calls, "telegram-adapter"),
    ) == 7
    assert calls == []


def test_post_authorization_runtime_failure_returns_exact_7_without_secret_output(
    capsys,
):
    def fail_runtime(**_kwargs):
        raise RuntimeError("fixture-runtime-secret")

    assert main(
        outcome_invocation_id=IDENTITY,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=fail_runtime,
        environment={
            "TELEGRAM_DESTINATION_ID": "isolated-owner-state-test",
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": "fixture-control-state",
        },
        telegram_config_loader=lambda _env: SimpleNamespace(
            bot_token="fixture-only-token",
            max_response_chars=4000,
        ),
    ) == 7
    captured = capsys.readouterr()
    assert "fixture-runtime-secret" not in captured.out
    assert "fixture-runtime-secret" not in captured.err


def test_authorized_fake_e6_cli_sends_once_and_binds_pending_owner_state(tmp_path):
    scenario = _scenario(tmp_path, name="entrypoint-success")
    control_path = tmp_path / "owner-control.json"
    initialize_state(control_path, timestamp=NOW)
    environment = {
        "TELEGRAM_DESTINATION_ID": "isolated-owner-state-test",
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
    }
    config = SimpleNamespace(
        bot_token="fixture-only-token",
        max_response_chars=4000,
    )
    identity_calls = []
    runtime_calls = []
    config_calls = []
    http_attempts = []

    def identity_provider():
        identity_calls.append(IDENTITY)
        return IDENTITY

    def runtime_factory(*, outcome_invocation_id):
        runtime_calls.append(outcome_invocation_id)
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=scenario["ports"],
            channel="TELEGRAM",
            destination_id="isolated-owner-state-test",
        )

    def config_loader(value):
        config_calls.append(value)
        return config

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "result": {"message_id": 913}}

    def fake_post(url, *, json, timeout):
        http_attempts.append((url, json, timeout))
        return Response()

    def adapter_factory(value, **kwargs):
        assert value is config
        return Phase09RTelegramDeliveryAdapterV1(
            value,
            http_post=fake_post,
            quota_now_provider=lambda: __import__("datetime").datetime(
                2026,
                7,
                30,
                13,
                0,
                1,
                tzinfo=__import__("datetime").timezone.utc,
            ),
            **kwargs,
        )

    exit_status = main(
        outcome_invocation_id_provider=identity_provider,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=runtime_factory,
        environment=environment,
        telegram_config_loader=config_loader,
        telegram_delivery_adapter_factory=adapter_factory,
    )

    assert exit_status == 0
    assert identity_calls == [IDENTITY]
    assert runtime_calls == [IDENTITY]
    assert config_calls == [environment]
    assert set(environment) == {
        "TELEGRAM_DESTINATION_ID",
        "TELEGRAM_OWNER_CONTROL_STATE_PATH",
    }
    assert len(http_attempts) == 1
    assert http_attempts[0][1]["chat_id"] == "isolated-owner-state-test"
    assert http_attempts[0][1]["text"].startswith(
        "AI CRYPTO SIGNAL — MANUAL OWNER REVIEW"
    )
    assert "Manual owner confirmation is required before ENTRY_ACTIVE." in (
        http_attempts[0][1]["text"]
    )
    state = load_state(control_path)
    binding = state["signal_message_bindings"]["isolated-owner-state-test:913"]
    assert binding["signal_id"] == scenario["request"].publication_signal_id
    assert binding["canonical_pair"] == active.normalize_pair(
        scenario["request"].publication_symbol
    )
    ledger = active.load_ledger(scenario["ports"].active_ledger_path)
    assert ledger["signals"][binding["signal_id"]]["state"] == (
        active.PUBLISHED_PENDING_ENTRY
    )
    assert ledger["signals"][binding["signal_id"]]["delivery_id"] == (
        scenario["request"].publication_delivery_id
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
        name="entrypoint-success-replay",
        payload=scenario["payload"],
        decision="CLEAR",
        ledger_path=scenario["ports"].active_ledger_path,
    )
    provider_calls = []
    replay_runtime_calls = []

    def replay_runtime_factory(*, outcome_invocation_id):
        replay_runtime_calls.append(outcome_invocation_id)
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=replay_ports,
            channel="TELEGRAM",
            destination_id="isolated-owner-state-test",
        )

    replay_status = main(
        outcome_invocation_id="b" * 32,
        outcome_invocation_id_provider=lambda: provider_calls.append(True),
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=replay_runtime_factory,
        environment=environment,
        telegram_config_loader=config_loader,
        telegram_delivery_adapter_factory=adapter_factory,
    )

    assert replay_status == 0
    assert provider_calls == []
    assert replay_runtime_calls == ["b" * 32]
    assert len(http_attempts) == 1
    assert scenario["ports"].active_ledger_path.read_bytes() == before_ledger
    assert control_path.read_bytes() == before_control


def test_fake_telegram_failure_returns_5_once_without_secret_output(
    tmp_path, capsys,
):
    scenario = _scenario(tmp_path, name="entrypoint-failure")
    control_path = tmp_path / "owner-control-failure.json"
    initialize_state(control_path, timestamp=NOW)
    attempts = []

    def runtime_factory(**_kwargs):
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=scenario["ports"],
            channel="TELEGRAM",
            destination_id="isolated-owner-state-test",
        )

    def adapter_factory(config, **kwargs):
        def fail(*_args, **_options):
            attempts.append(1)
            raise RuntimeError("fixture-secret-token")

        return Phase09RTelegramDeliveryAdapterV1(
            config,
            http_post=fail,
            **kwargs,
        )

    status = main(
        outcome_invocation_id=IDENTITY,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=runtime_factory,
        environment={
            "TELEGRAM_DESTINATION_ID": "isolated-owner-state-test",
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
        },
        telegram_config_loader=lambda _env: SimpleNamespace(
            bot_token="fixture-only-token",
            max_response_chars=4000,
        ),
        telegram_delivery_adapter_factory=adapter_factory,
    )
    captured = capsys.readouterr()

    assert status == 5
    assert attempts == [1]
    assert "fixture-secret-token" not in captured.out
    assert "fixture-secret-token" not in captured.err
    assert "fixture-only-token" not in captured.out
    assert "fixture-only-token" not in captured.err
    assert load_state(control_path)["signal_message_bindings"] == {}


def test_malformed_telegram_receipt_returns_exact_6_once(tmp_path):
    scenario = _scenario(tmp_path, name="entrypoint-malformed-receipt")
    control_path = tmp_path / "owner-control-malformed.json"
    initialize_state(control_path, timestamp=NOW)
    attempts = []

    def runtime_factory(**_kwargs):
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=scenario["ports"],
            channel="TELEGRAM",
            destination_id="isolated-owner-state-test",
        )

    class MalformedResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "result": {}}

    def adapter_factory(config, **kwargs):
        def malformed_post(*_args, **_options):
            attempts.append(1)
            return MalformedResponse()

        return Phase09RTelegramDeliveryAdapterV1(
            config,
            http_post=malformed_post,
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
        environment={
            "TELEGRAM_DESTINATION_ID": "isolated-owner-state-test",
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
        },
        telegram_config_loader=lambda _env: SimpleNamespace(
            bot_token="fixture-only-token",
            max_response_chars=4000,
        ),
        telegram_delivery_adapter_factory=adapter_factory,
    ) == 6
    assert attempts == [1]
    assert load_state(control_path)["signal_message_bindings"] == {}


def test_owner_registration_failure_returns_7_without_binding_or_occupancy(
    tmp_path, monkeypatch,
):
    scenario = _scenario(tmp_path, name="entrypoint-registration-failure")
    control_path = tmp_path / "owner-control-registration-failure.json"
    initialize_state(control_path, timestamp=NOW)
    telegram_attempts = []

    def fail_registration(**_kwargs):
        raise RuntimeError("fixture-registration-failure")

    monkeypatch.setattr(
        "engine.e6_integrated_orchestrator_v1.bind_e6_publication_to_owner_state_v1",
        fail_registration,
    )

    def runtime_factory(**_kwargs):
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=scenario["ports"],
            channel="TELEGRAM",
            destination_id="isolated-owner-state-test",
        )

    def adapter_factory(config, **kwargs):
        def forbidden_post(*_args, **_options):
            telegram_attempts.append(1)
            pytest.fail("registration failure reached Telegram")

        return Phase09RTelegramDeliveryAdapterV1(
            config,
            http_post=forbidden_post,
            **kwargs,
        )

    assert main(
        outcome_invocation_id="e" * 32,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=runtime_factory,
        environment={
            "TELEGRAM_DESTINATION_ID": "isolated-owner-state-test",
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
        },
        telegram_config_loader=lambda _env: SimpleNamespace(
            bot_token="fixture-only-token",
            max_response_chars=4000,
        ),
        telegram_delivery_adapter_factory=adapter_factory,
    ) == 7
    assert active.load_ledger(scenario["ports"].active_ledger_path)[
        "ledger_revision"
    ] == 0
    assert load_state(control_path)["signal_message_bindings"] == {}
    assert telegram_attempts == []


def test_entrypoint_has_no_legacy_publication_or_exchange_bypass():
    source = Path(__import__("engine.run_production_signal_v1", fromlist=["x"]).__file__).read_text(
        encoding="utf-8"
    )
    assert "run_master_engine_v4" not in source
    assert "enable_publication=True" not in source
    assert "owner_blueprint_ledger" not in source
    assert "production_signal_service_v1" not in source
    assert "ccxt" not in source
    assert "binance" not in source
    assert "mark_entry_active" not in source
    assert "systemctl" not in source
