"""Focused contract tests for the non-executing Telegram launcher."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from engine.phase_12_telegram_production_launcher_v1 import (
    TelegramCredentialSourceMetadataV1,
    TelegramLauncherDependenciesV1,
    TelegramProductionGateStateV1,
    TelegramProductionLauncherPolicyV1,
    TelegramProductionRuntimeConfigurationV1,
    TelegramShutdownStateV1,
    prepare_telegram_production_launcher_v1,
    transition_telegram_shutdown_v1,
)


_TOKEN = "test-token-not-for-production"


def _policy(**changes):
    return TelegramProductionLauncherPolicyV1(
        launcher_implementation_authorized=True,
        **changes,
    )


def _configuration(**changes):
    values = {
        "bot_username": None,
        "quota_limit": 1,
        "slot_capacity": 1,
        "window_id": "window",
        "quota_state_path": "/var/lib/ai-crypto-signal-agent/quota.json",
        "worker_state_path": "/var/lib/ai-crypto-signal-agent/worker.json",
        "max_response_chars": 64,
        "expected_credential_filename": "telegram_bot_token",
        "expected_credential_directory_classification": "SYSTEMD_CREDENTIALS",
    }
    values.update(changes)
    return TelegramProductionRuntimeConfigurationV1(**values)


def _gates(**changes):
    values = {
        "activation_gate_open": True,
        "credential_gate_open": True,
        "network_gate_open": True,
        "workload_gate_open": True,
        "telegram_start_authorized": True,
    }
    values.update(changes)
    return TelegramProductionGateStateV1(**values)


def _source(**changes):
    values = {
        "credential_directory": "/run/credentials/ai-crypto-signal-agent.service",
        "directory_classification": "SYSTEMD_CREDENTIALS",
        "credential_filename": "telegram_bot_token",
    }
    values.update(changes)
    return TelegramCredentialSourceMetadataV1(**values)


def _dependencies(reader=lambda *_: _TOKEN, **changes):
    values = {
        "credential_reader": reader,
        "sender": lambda *_: None,
        "worker": lambda *_: None,
        "quota_now_provider": lambda: 0,
        "reservation_id_provider": lambda: "reservation",
        "runtime_builder": lambda config, **_: object(),
        "sdk_runner_builder": lambda **_: object(),
    }
    values.update(changes)
    return TelegramLauncherDependenciesV1(**values)


@pytest.mark.parametrize(
    ("field", "failure"),
    (
        ("activation_gate_open", "ACTIVATION_GATE_CLOSED"),
        ("credential_gate_open", "CREDENTIAL_GATE_CLOSED"),
        ("network_gate_open", "NETWORK_GATE_CLOSED"),
        ("workload_gate_open", "WORKLOAD_GATE_CLOSED"),
        ("telegram_start_authorized", "TELEGRAM_START_NOT_AUTHORIZED"),
    ),
)
def test_each_gate_fails_closed_before_reader(field, failure):
    calls = []
    result = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(),
        gates=_gates(**{field: False}), credential_source=_source(),
        dependencies=_dependencies(reader=lambda *_: calls.append(True)),
    )
    assert failure in result.failure_codes
    assert calls == []


def test_exact_five_gates_and_credential_filename_are_required():
    result = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(), gates=_gates(),
        credential_source=_source(credential_filename="wrong"),
        dependencies=_dependencies(),
    )
    assert result.prepared is False
    assert result.failure_codes == ("CREDENTIAL_FILENAME_MISMATCH",)


@pytest.mark.parametrize(
    "changes, code",
    (
        ({"quota_limit": 0}, "QUOTA_LIMIT_INVALID"),
        ({"slot_capacity": True}, "SLOT_CAPACITY_INVALID"),
        ({"window_id": " "}, "WINDOW_ID_INVALID"),
        ({"quota_state_path": "relative"}, "QUOTA_STATE_PATH_INVALID"),
        ({"worker_state_path": "/tmp/worker"}, "WORKER_STATE_PATH_INVALID"),
        ({"quota_state_path": "/var/lib/ai-crypto-signal-agent/../x"}, "QUOTA_STATE_PATH_INVALID"),
        ({"max_response_chars": 1}, "MAX_RESPONSE_CHARS_INVALID"),
    ),
)
def test_non_secret_configuration_is_fail_closed(changes, code):
    result = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(**changes), gates=_gates(),
        credential_source=_source(), dependencies=_dependencies(),
    )
    assert code in result.failure_codes


def test_invalid_reader_and_credential_value_are_sanitized():
    invalid_reader = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(), gates=_gates(),
        credential_source=_source(), dependencies=_dependencies(reader=None),
    )
    invalid_value = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(), gates=_gates(),
        credential_source=_source(), dependencies=_dependencies(reader=lambda *_: " "),
    )
    assert invalid_reader.failure_codes == ("CREDENTIAL_READER_INVALID",)
    assert invalid_value.failure_codes == ("CREDENTIAL_VALUE_INVALID",)
    assert _TOKEN not in repr(invalid_value)


def test_environment_token_is_not_a_fallback(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", _TOKEN)
    result = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(), gates=_gates(),
        credential_source=_source(), dependencies=_dependencies(reader=lambda *_: ""),
    )
    assert result.failure_codes == ("CREDENTIAL_VALUE_INVALID",)


def test_invalid_credential_directory_and_reader_exception_never_disclose_token():
    bad_directory = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(), gates=_gates(),
        credential_source=_source(credential_directory="relative"),
        dependencies=_dependencies(),
    )
    raised_reader = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(), gates=_gates(),
        credential_source=_source(),
        dependencies=_dependencies(reader=lambda *_: (_ for _ in ()).throw(RuntimeError(_TOKEN))),
    )
    assert "CREDENTIAL_DIRECTORY_INVALID" in bad_directory.failure_codes
    assert raised_reader.failure_codes == ("COMPOSITION_FAILED",)
    assert _TOKEN not in repr(raised_reader)


def test_injected_builders_prepare_without_execution_or_token_disclosure():
    calls = []
    worker_calls = []

    class Runtime:
        def start(self, *_):
            raise AssertionError("runtime.start must not be called")

    def runtime_builder(config, **kwargs):
        calls.append(("runtime", config.bot_token, kwargs))
        return Runtime()

    def runner_builder(**kwargs):
        calls.append(("runner", kwargs))
        return object()

    result = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(), gates=_gates(),
        credential_source=_source(),
        dependencies=_dependencies(
            worker=lambda *_: worker_calls.append(True),
            runtime_builder=runtime_builder,
            sdk_runner_builder=runner_builder,
        ),
    )
    assert [entry[0] for entry in calls] == ["runtime", "runner"]
    assert result.prepared and result.runtime_prepared and result.sdk_runner_prepared
    assert not result.execution_performed and not result.polling_started
    assert not result.worker_invoked and not result.network_accessed
    assert worker_calls == []
    assert _TOKEN not in repr(result)
    assert _TOKEN not in repr(result.audit_evidence)


def test_failure_order_and_shutdown_transitions_are_pure():
    result = prepare_telegram_production_launcher_v1(
        policy=_policy(), configuration=_configuration(),
        gates=_gates(activation_gate_open=False, network_gate_open=False),
        credential_source=_source(), dependencies=_dependencies(),
    )
    assert result.failure_codes == ("ACTIVATION_GATE_CLOSED", "NETWORK_GATE_CLOSED")
    ready = transition_telegram_shutdown_v1(
        current=TelegramShutdownStateV1.NOT_STARTED,
        target=TelegramShutdownStateV1.PREPARED,
    )
    blocked = transition_telegram_shutdown_v1(
        current=TelegramShutdownStateV1.PREPARED,
        target=TelegramShutdownStateV1.GRACEFUL_SHUTDOWN_COMPLETE,
    )
    assert ready.transition_valid
    assert blocked.state is TelegramShutdownStateV1.BLOCKED


def test_passive_launcher_file_remains_unchanged():
    protected = Path("engine/phase_12_passive_runtime_launcher_executable_contract_v1.py")
    assert hashlib.sha256(protected.read_bytes()).hexdigest() == (
        "5173b7e376cd8590dd2bdc95a50d4a8dfeb2e0e8f7227ffdf56803698dddc49d"
    )
