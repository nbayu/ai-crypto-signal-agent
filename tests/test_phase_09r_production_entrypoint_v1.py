from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine import active_signal_ledger_v1 as active
from engine import controlled_production_signal_cycle_v1 as controlled
from engine.phase09r_telegram_delivery_adapter_v1 import (
    Phase09RTelegramDeliveryAdapterV1,
)
from engine.e6_production_cycle_input_v1 import (
    DUE_WINDOW_ALREADY_HANDLED,
    E6_NO_TRADE_CYCLE_POLICY_V1,
    E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
    E6NoTradeCycleRequestV1,
    MODE_JOB_SELECTED,
    NO_MODE_JOB_DUE,
    build_e6_production_dispatch_decision_v1,
)
from engine.e6_production_runtime_composition_v1 import (
    build_e6_production_runtime_composition_v1,
)
from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
)
from engine.e6_activation_configuration_v1 import (
    E6_ACTIVATION_CONFIGURATION_SCHEMA_V1,
)
from engine.e6_deployment_state_binding_v1 import (
    E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
    build_e6_deployment_state_binding_v1,
)
from engine.phase09r_observability_v1 import (
    E6_PRODUCTION_IDEMPOTENT_REPLAY_V1,
    E6_PRODUCTION_NO_TRADE_V1,
    E6_PRODUCTION_NO_WORK_DUE_V1,
    E6ProductionObservabilityEventV1,
)
from engine.run_production_signal_v1 import (
    _production_state_paths_v1,
    _run_production_module_v1,
    main,
)
from engine.telegram_owner_control_state_v1 import initialize_state, load_state
from test_e6_integrated_orchestrator_v1 import _new_ports, _run, _scenario
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


def test_authorized_missing_config_and_destination_return_exact_2(tmp_path):
    calls = []
    scenario = _scenario(tmp_path, name="entrypoint-missing-config")

    def runtime_factory(*, outcome_invocation_id):
        calls.append(("runtime", outcome_invocation_id))
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=scenario["ports"],
            channel="TELEGRAM",
            destination_id="isolated-owner-state-test",
        )

    common = {
        "outcome_invocation_id": IDENTITY,
        "e6_enabled": True,
        "authorization": _authorization(),
        "e6_activation_authorized": True,
        "network_authorized": True,
        "publication_authorized": True,
        "e6_runtime_factory": runtime_factory,
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
    assert calls == [("runtime", IDENTITY), ("runtime", IDENTITY)]


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
    assert "build_e6_production_binance_public_market_port_v1" in source
    assert "create_order" not in source
    assert "mark_entry_active" not in source
    assert "systemctl" not in source


def _no_trade_request(*, identity=IDENTITY, **changes):
    values = {
        "schema_version": E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
        "policy_version": E6_NO_TRADE_CYCLE_POLICY_V1,
        "source_commit": "a" * 40,
        "outcome_invocation_id": identity,
        "mode": "SCALP",
        "due_job_id": "SCALP:2026-08-03T08:00:00Z",
        "due_window_occurrence_id": "e6dw1:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "mode_lineage_sha256": "1" * 64,
        "observed_at": "2026-08-03T08:00:00Z",
        "reason_code": "E3_TRIGGER_NOT_CONFIRMED",
        "source_reason_code": "CLOSED_TRIGGER_NOT_CONFIRMED",
        "scan_composition_sha256": "2" * 64,
        "execution_sha256": "3" * 64,
        "e3_evidence_sha256": "4" * 64,
        "audit_manifest_sha256": "5" * 64,
        "provider_attempt_count": 0,
        "telegram_attempt_count": 0,
        "exchange_order_count": 0,
        "slot_mutation_count": 0,
        "pair_lock_mutation_count": 0,
        "entry_active_mutation_count": 0,
        "retry_count": 0,
    }
    values.update(changes)
    return E6NoTradeCycleRequestV1(**values)


def _activation_mapping(**changes):
    commit = "a" * 40
    binding = build_e6_deployment_state_binding_v1(
        deployment_profile="CANDIDATE_CANARY", release_commit=commit
    )
    values = {
        "E6_ACTIVATION_SCHEMA_VERSION": E6_ACTIVATION_CONFIGURATION_SCHEMA_V1,
        "E6_DEPLOYMENT_BINDING_VERSION": E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
        "E6_DEPLOYMENT_PROFILE": binding.deployment_profile.value,
        "E6_RELEASE_COMMIT": commit,
        "E6_RELEASE_TREE": "b" * 40,
        "E6_TRUSTED_CHECKPOINT_COMMIT": "c" * 40,
        "E6_RELEASE_ROOT": binding.release_root,
        "E6_SERVICE_UNIT": binding.service_unit,
        "E6_TIMER_UNIT": binding.timer_unit,
        "E6_STATE_ROOT": binding.state_root,
        "E6_OWNER_STATE_ROOT": binding.owner_state_root,
        "E6_LEDGER_ROOT": binding.ledger_root,
        "E6_ACTIVE_SIGNAL_LEDGER_PATH": binding.active_ledger_path,
        "E6_OWNER_CONTROL_STATE_PATH": binding.owner_state_path,
        "E6_PUBLICATION_ROOT": binding.publication_root,
        "E6_OPERATIONAL_ARTIFACT_ROOT": binding.operational_artifact_root,
        "E6_RUNTIME_ROOT": binding.runtime_root,
        "E6_RUNTIME_LOCK_PATH": binding.runtime_lock,
        "E6_CACHE_ROOT": binding.cache_root,
        "E6_LOG_POLICY": binding.log_policy,
        "E6_CONTROL_ROOT": binding.control_root,
        "E6_RELEASE_REFERENCE_PATH": binding.install_pointer,
        "E6_ROLLBACK_REFERENCE_PATH": binding.rollback_pointer,
        "E6_ACCEPTED_RELEASE_MARKER_PATH": binding.accepted_marker,
        "E6_KILL_SWITCH_PATH": binding.kill_switch,
        "E6_CONFIGURATION_ROOT": binding.configuration_root,
        "E6_CREDENTIAL_METADATA_PATH": binding.credential_metadata_path,
        "E6_ACTIVATION_CONFIGURATION_PATH": binding.activation_configuration_path,
        "E6_SERVICE_USER": binding.service_user,
        "E6_SERVICE_GROUP": binding.service_group,
        "E6_PROVIDER_BINDING_VERSION": E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
        "E6_PROVIDER_BINDING_SHA256": E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
        "E6_RUNTIME_ENABLED": "true",
        "E6_PROVIDER_ENABLED": "true",
        "E6_ACTIVATION_GATE": "true",
        "E6_WORKLOAD_GATE": "true",
        "E6_CREDENTIAL_GATE": "true",
        "E6_NETWORK_GATE": "true",
        "E6_PUBLICATION_GATE": "true",
        "E6_TELEGRAM_PUBLICATION_GATE": "true",
        "E6_AUTOMATIC_RETRY_COUNT": "0",
        "E6_PROVIDER_SUBSTITUTION_ENABLED": "false",
        "E6_PROMPT_REPAIR_ENABLED": "false",
        "E6_STALE_REVIEW_REUSE_ENABLED": "false",
        "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED": "false",
        "ACTIVE_SIGNAL_LEDGER_PATH": binding.active_ledger_path,
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": binding.owner_state_path,
    }
    values.update(changes)
    return values


def _dispatch(disposition):
    options = {}
    if disposition != NO_MODE_JOB_DUE:
        options = {
            "mode": "SWING",
            "due_job_id": "SWING:2026-08-03T08:00:00Z",
            "due_window_occurrence_id": "e6dw1:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "mode_lineage_sha256": "9" * 64,
        }
    return build_e6_production_dispatch_decision_v1(
        source_commit="a" * 40,
        outcome_invocation_id=IDENTITY,
        observed_at="2026-08-03T08:00:00Z",
        disposition=disposition,
        reason_code=disposition,
        **options,
    )


def _authorized_main_options(calls, events, *, request):
    def runtime_factory(*, outcome_invocation_id):
        calls.append(("runtime", outcome_invocation_id))
        return request

    return {
        "outcome_invocation_id": IDENTITY,
        "e6_enabled": True,
        "authorization": _authorization(),
        "e6_activation_authorized": True,
        "network_authorized": True,
        "publication_authorized": True,
        "e6_runtime_factory": runtime_factory,
        "environment": {},
        "telegram_config_loader": _bomb(calls, "telegram-config"),
        "telegram_delivery_adapter_factory": _bomb(calls, "telegram-adapter"),
        "e6_orchestrator": _bomb(calls, "orchestrator"),
        "e6_service_cycle_runner": _bomb(calls, "service-runner"),
        "production_observability_emitter": events.append,
    }


def test_exact_no_trade_union_returns_zero_and_skips_every_external_boundary():
    calls = []
    events = []
    request = _no_trade_request()
    assert main(**_authorized_main_options(calls, events, request=request)) == 0
    assert calls == [("runtime", IDENTITY)]
    assert len(events) == 1
    event = events[0]
    assert type(event) is E6ProductionObservabilityEventV1
    assert event.event_name == E6_PRODUCTION_NO_TRADE_V1
    assert event.outcome_invocation_id == IDENTITY
    assert event.reason_code == request.reason_code
    assert event.provider_attempt_count == event.telegram_attempt_count == 0


def test_service_level_duplicate_suppression_returns_zero_and_stays_lazy(
    tmp_path,
):
    scenario = _scenario(tmp_path, name="entrypoint-duplicate-suppression")
    assert _run(scenario).disposition == "COMPLETE"
    suppressed_request = replace(
        scenario["request"],
        publication_signal_id="PSG-" + "f" * 64,
        production_outcome_invocation_id=IDENTITY,
        production_due_window_occurrence_id="e6dw1:" + "d" * 64,
        production_observed_at="2026-07-30T13:00:00Z",
        production_evidence_sha256="e" * 64,
    )
    cycle = E6ServiceCycleRequestV1(
        orchestrator_request=suppressed_request,
        orchestrator_ports=scenario["ports"],
        channel="TELEGRAM",
        destination_id="isolated-owner-state-test",
    )
    calls = []
    events = []

    assert main(
        outcome_invocation_id=IDENTITY,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=lambda **_kwargs: cycle,
        environment={
            "TELEGRAM_DESTINATION_ID": "isolated-owner-state-test",
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(tmp_path / "owner.json"),
        },
        telegram_config_loader=_bomb(calls, "telegram-config"),
        telegram_delivery_adapter_factory=_bomb(calls, "telegram-adapter"),
        production_observability_emitter=events.append,
    ) == 0
    assert calls == []
    assert len(events) == 1
    assert events[0].reason_code == "E4_DUPLICATE_SUPPRESSED"
    assert events[0].source_reason_code == "SUPPRESS_EXISTING_THESIS"


def test_no_trade_invocation_mismatch_and_invalid_object_are_sanitized_exit7(capsys):
    mismatch_calls = []
    mismatch_events = []
    mismatch = _no_trade_request(identity="b" * 32)
    assert main(
        **_authorized_main_options(
            mismatch_calls, mismatch_events, request=mismatch
        )
    ) == 7
    assert mismatch_calls == [("runtime", IDENTITY)]
    assert mismatch_events == []
    assert "b" * 32 not in capsys.readouterr().err

    invalid_calls = []
    invalid_events = []
    invalid = _no_trade_request()
    object.__setattr__(invalid, "reason_code", NO_MODE_JOB_DUE)
    assert main(
        **_authorized_main_options(invalid_calls, invalid_events, request=invalid)
    ) == 7
    assert invalid_calls == [("runtime", IDENTITY)]
    assert invalid_events == []
    assert "Traceback" not in capsys.readouterr().err


def test_unsupported_runtime_factory_output_remains_sanitized_exit7(capsys):
    calls = []
    events = []
    assert main(
        **_authorized_main_options(calls, events, request=SimpleNamespace())
    ) == 7
    assert calls == [("runtime", IDENTITY)]
    assert events == []
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PHASE09R_EXIT7" in captured.err


@pytest.mark.parametrize(
    ("disposition", "event_name"),
    (
        (NO_MODE_JOB_DUE, E6_PRODUCTION_NO_WORK_DUE_V1),
        (DUE_WINDOW_ALREADY_HANDLED, E6_PRODUCTION_IDEMPOTENT_REPLAY_V1),
    ),
)
def test_private_seam_healthy_dispatch_returns_zero_without_public_main(
    disposition, event_name
):
    configuration = _activation_mapping()
    calls = []
    events = []

    def composition_builder(*, configuration):
        calls.append(("composition", configuration))
        return build_e6_production_runtime_composition_v1(
            configuration=configuration
        )

    def dispatch_provider(*, configuration, composition):
        calls.append(("dispatch", configuration, composition))
        return _dispatch(disposition)

    assert _run_production_module_v1(
        environment=configuration,
        runtime_composition_builder=composition_builder,
        dispatch_decision_provider=dispatch_provider,
        selected_job_runtime_factory_provider=_bomb(calls, "runtime-provider"),
        production_observability_emitter=events.append,
        public_main_runner=_bomb(calls, "main"),
    ) == 0
    assert [call[0] for call in calls] == ["composition", "dispatch"]
    assert len(events) == 1
    assert events[0].event_name == event_name


def test_private_seam_selected_job_gets_one_factory_and_calls_main_once():
    configuration = _activation_mapping()
    calls = []
    runtime_factory = lambda *, outcome_invocation_id: _no_trade_request(
        identity=outcome_invocation_id
    )

    def dispatch_provider(**_kwargs):
        calls.append("dispatch")
        return _dispatch(MODE_JOB_SELECTED)

    def runtime_provider(*, decision, configuration, composition):
        calls.append(("runtime-provider", decision, configuration, composition))
        return runtime_factory

    def main_runner(**kwargs):
        calls.append(("main", kwargs))
        return 0

    assert _run_production_module_v1(
        environment=configuration,
        dispatch_decision_provider=dispatch_provider,
        selected_job_runtime_factory_provider=runtime_provider,
        production_observability_emitter=lambda _event: None,
        public_main_runner=main_runner,
    ) == 0
    assert calls[0] == "dispatch"
    assert calls[1][0] == "runtime-provider"
    assert calls[2][0] == "main"
    supplied = calls[2][1]
    assert supplied["outcome_invocation_id"] == IDENTITY
    assert supplied["e6_enabled"] is True
    assert supplied["authorization"] == _authorization()
    assert supplied["e6_activation_authorized"] is True
    assert supplied["network_authorized"] is True
    assert supplied["publication_authorized"] is True
    assert supplied["e6_runtime_factory"] is runtime_factory
    assert supplied["environment"] is configuration
    assert callable(supplied["telegram_config_loader"])
    assert callable(supplied["telegram_delivery_adapter_factory"])
    assert callable(supplied["e6_orchestrator"])
    assert callable(supplied["e6_service_cycle_runner"])


@pytest.mark.parametrize(
    "change",
    (
        {"E6_RUNTIME_ENABLED": "false"},
        {"E6_PROVIDER_ENABLED": "false"},
        {"E6_WORKLOAD_GATE": "false"},
        {"E6_CREDENTIAL_GATE": "false"},
        {"E6_TELEGRAM_PUBLICATION_GATE": "false"},
    ),
)
def test_private_seam_disabled_or_partial_composition_stops_before_dispatch(change):
    calls = []
    assert _run_production_module_v1(
        environment=_activation_mapping(**change),
        dispatch_decision_provider=_bomb(calls, "dispatch"),
        selected_job_runtime_factory_provider=_bomb(calls, "runtime-provider"),
        public_main_runner=_bomb(calls, "main"),
    ) == 2
    assert calls == []


def test_private_seam_invalid_activation_stops_before_dispatch():
    calls = []
    assert _run_production_module_v1(
        environment={},
        dispatch_decision_provider=_bomb(calls, "dispatch"),
        selected_job_runtime_factory_provider=_bomb(calls, "runtime-provider"),
        public_main_runner=_bomb(calls, "main"),
    ) == 2
    assert calls == []


def test_entrypoint_state_paths_come_only_from_the_validated_binding() -> None:
    environment = _activation_mapping()
    activation_only = {
        key: environment[key]
        for key in __import__(
            "engine.e6_activation_configuration_v1", fromlist=["_EXPECTED_KEYS"]
        )._EXPECTED_KEYS
    }
    composition = build_e6_production_runtime_composition_v1(
        configuration=activation_only
    )
    state_root, active_path, owner_path = _production_state_paths_v1(
        configuration=environment, composition=composition
    )
    binding = composition.deployment_binding
    assert state_root == Path(binding.state_root)
    assert active_path == Path(binding.active_ledger_path)
    assert owner_path == Path(binding.owner_state_path)
    for key in (
        "E6_DEPLOYMENT_PROFILE",
        "E6_RELEASE_COMMIT",
        "E6_STATE_ROOT",
        "E6_RUNTIME_LOCK_PATH",
        "ACTIVE_SIGNAL_LEDGER_PATH",
        "TELEGRAM_OWNER_CONTROL_STATE_PATH",
    ):
        detached = dict(environment)
        detached[key] = "/tmp/detached"
        with pytest.raises(ValueError, match="E6_PRODUCTION_STATE_PATH_INVALID"):
            _production_state_paths_v1(
                configuration=detached, composition=composition
            )


def test_module_execution_uses_real_private_dispatcher_without_cli_authority():
    source = Path(
        __import__("engine.run_production_signal_v1", fromlist=["x"]).__file__
    ).read_text(encoding="utf-8")
    assert source.endswith(
        '\nif __name__ == "__main__":\n    sys.exit(_run_production_module_v1())\n'
    )
    assert "sys.exit(main())" not in source
    assert "argparse" not in source
