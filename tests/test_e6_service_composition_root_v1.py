from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
import subprocess
import sys

import pytest

from engine import active_signal_ledger_v1 as active
from engine import controlled_production_signal_cycle_v1 as controlled
from engine import e6_service_composition_root_v1 as subject
from engine.phase09r_telegram_delivery_adapter_v1 import E6TelegramDeliveryRequestV1
from engine.e6_telegram_human_formatter_v1 import format_e6_signal_message_v1
from test_e6_integrated_orchestrator_v1 import _new_ports, _run, _scenario


DELIVERED_AT = "2026-07-30T13:00:01Z"


def _authorization(**changes):
    values = {name: True for name, _ in controlled._GATES}
    values.update(changes)
    return controlled.ControlledProductionSignalCycleAuthorizationV1(**values)


def _request(scenario):
    return subject.E6ServiceCycleRequestV1(
        orchestrator_request=scenario["request"],
        orchestrator_ports=scenario["ports"],
        channel="TELEGRAM",
        destination_id="isolated-owner-state-test",
    )


def _root(delivery, **changes):
    values = {
        "telegram_delivery": delivery,
        "authorization": _authorization(),
        "e6_activation_authorized": True,
        "network_authorized": True,
        "publication_authorized": True,
    }
    values.update(changes)
    return subject.E6ServiceCompositionRootV1(**values)


def _receipt(*, channel="TELEGRAM", destination_id="isolated-owner-state-test"):
    return {
        "channel": channel,
        "destination_id": destination_id,
        "external_delivery_id": "fixture-message-1",
        "delivered_at": DELIVERED_AT,
    }


def _no_authority(result):
    assert result.owner_decision_count == 0
    assert result.entry_active_mutation_count == 0
    assert result.slot_mutation_count == 0
    assert result.pair_lock_mutation_count == 0
    assert result.exchange_order_count == 0
    assert result.publication_artifact_effect_count == 0


def _tampered(result, **changes):
    clone = object.__new__(type(result))
    for name in result.__slots__:
        object.__setattr__(clone, name, changes.get(name, getattr(result, name)))
    return clone


def test_contracts_are_frozen_slotted_default_deny_and_construction_is_passive(
    tmp_path,
):
    scenario = _scenario(tmp_path, name="contract")
    request = _request(scenario)
    before = set(tmp_path.rglob("*"))
    root = subject.E6ServiceCompositionRootV1()
    result = subject.run_e6_service_cycle_v1(root=root, request=request)
    after = set(tmp_path.rglob("*"))

    for contract in (
        subject.E6ServiceCompositionRootV1,
        subject.E6ServiceCycleRequestV1,
        subject.E6ServiceCycleResultV1,
    ):
        assert contract.__dataclass_params__.frozen
        assert "__dict__" not in contract.__slots__
    with pytest.raises(FrozenInstanceError):
        root.network_authorized = True
    with pytest.raises(FrozenInstanceError):
        request.channel = "OTHER"
    with pytest.raises(FrozenInstanceError):
        result.disposition = subject.DELIVERED
    assert root.authorization.to_dict() == {
        "activation_gate": False,
        "workload_gate": False,
        "credential_gate": False,
        "network_gate": False,
        "publication_gate": False,
        "telegram_publication_gate": False,
    }
    assert root.e6_activation_authorized is False
    assert root.network_authorized is False
    assert root.publication_authorized is False
    assert result.disposition == subject.DRY
    assert result.reason_code == controlled.ACTIVATION_GATE_CLOSED
    assert before == after

    prohibited_fields = {
        "credential", "token", "secret", "password", "http_client",
        "telegram_client", "exchange", "exchange_client", "chat_id",
    }
    for contract in (subject.E6ServiceCompositionRootV1, subject.E6ServiceCycleRequestV1):
        assert {item.name.casefold() for item in fields(contract)}.isdisjoint(
            prohibited_fields
        )

    parent_subject = subject
    parent_root_type = subject.E6ServiceCompositionRootV1
    parent_request_type = subject.E6ServiceCycleRequestV1
    parent_result_type = subject.E6ServiceCycleResultV1
    parent_runner = subject.run_e6_service_cycle_v1
    repository_root = Path(__file__).resolve().parents[1]
    child_workdir = tmp_path / "isolated-child-cwd"
    child_workdir.mkdir()
    child_program = (
        "import pathlib, sys\n"
        "repository_root = pathlib.Path(sys.argv[1]).resolve()\n"
        "expected_working_directory = pathlib.Path(sys.argv[2]).resolve()\n"
        "if pathlib.Path.cwd().resolve() != expected_working_directory:\n"
        "    raise SystemExit(3)\n"
        "sys.path.insert(0, str(repository_root))\n"
        "import engine.e6_service_composition_root_v1\n"
    )

    child = subprocess.run(
        [
            sys.executable,
            "-c",
            child_program,
            str(repository_root),
            str(child_workdir),
        ],
        cwd=child_workdir,
        env={"PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert child.returncode == 0
    assert child.stdout == ""
    assert child.stderr == ""
    assert tuple(child_workdir.iterdir()) == ()
    assert subject is parent_subject
    assert subject.E6ServiceCompositionRootV1 is parent_root_type
    assert subject.E6ServiceCycleRequestV1 is parent_request_type
    assert subject.E6ServiceCycleResultV1 is parent_result_type
    assert subject.run_e6_service_cycle_v1 is parent_runner


@pytest.mark.parametrize("field, reason", controlled._GATES)
def test_each_of_six_controlled_gates_blocks_before_orchestrator_and_delivery(
    tmp_path, field, reason,
):
    scenario = _scenario(tmp_path, name=f"gate-{field}")
    calls = []
    root = _root(
        lambda *_args, **_kwargs: calls.append("delivery"),
        orchestrator=lambda **_kwargs: calls.append("orchestrator"),
        authorization=_authorization(**{field: False}),
    )

    result = subject.run_e6_service_cycle_v1(root=root, request=_request(scenario))

    assert result.disposition == subject.DRY
    assert result.reason_code == reason
    assert calls == []
    assert result.deepseek_provider_attempt_count == 0
    assert result.claude_provider_attempt_count == 0
    assert result.telegram_attempt_count == 0
    assert result.owner_lifecycle_binding_disposition is None
    _no_authority(result)


@pytest.mark.parametrize(
    "field, reason",
    (
        ("e6_activation_authorized", subject.E6_ACTIVATION_NOT_AUTHORIZED),
        ("network_authorized", subject.E6_NETWORK_NOT_AUTHORIZED),
        ("publication_authorized", subject.E6_PUBLICATION_NOT_AUTHORIZED),
    ),
)
def test_each_explicit_e6_authorization_blocks_independently(
    tmp_path, field, reason,
):
    scenario = _scenario(tmp_path, name=f"explicit-{field}")
    calls = []
    root = _root(
        lambda *_args, **_kwargs: calls.append("delivery"),
        orchestrator=lambda **_kwargs: calls.append("orchestrator"),
        **{field: False},
    )

    result = subject.run_e6_service_cycle_v1(root=root, request=_request(scenario))

    assert result.disposition == subject.DRY
    assert result.reason_code == reason
    assert calls == []
    assert result.telegram_attempt_count == 0
    _no_authority(result)


def test_expected_review_and_final_gate_suppression_are_healthy_no_trade(tmp_path):
    hold_scenario = _scenario(tmp_path, name="orchestrator-hold", decision="HOLD")
    hold_deliveries = []
    hold = subject.run_e6_service_cycle_v1(
        root=_root(lambda *_args, **_kwargs: hold_deliveries.append(1)),
        request=_request(hold_scenario),
    )
    assert hold.disposition == subject.NO_TRADE
    assert hold.reason_code == "BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE"
    assert hold_deliveries == []
    assert hold.telegram_attempt_count == 0

    gate_scenario = _scenario(
        tmp_path,
        name="python-final-gate",
        hard_gates=False,
    )
    gate_deliveries = []
    rejected = subject.run_e6_service_cycle_v1(
        root=_root(lambda *_args, **_kwargs: gate_deliveries.append(1)),
        request=_request(gate_scenario),
    )
    assert rejected.disposition == subject.NO_TRADE
    assert rejected.reason_code == "BLOCK_D6_DETERMINISTIC_POLICY"
    assert gate_deliveries == []
    assert rejected.telegram_attempt_count == 0
    _no_authority(hold)
    _no_authority(rejected)


@pytest.mark.parametrize(
    "changes",
    (
        {"publication_envelope": None},
        {"rendered_message": None},
        {"correlation_sha256": "f" * 64},
    ),
)
def test_missing_or_mismatched_e6_evidence_fails_closed_without_legacy_bypass(
    tmp_path, changes,
):
    scenario = _scenario(tmp_path, name="strict-evidence")
    complete = _run(scenario)
    invalid = _tampered(complete, **changes)
    deliveries = []
    result = subject.run_e6_service_cycle_v1(
        root=_root(
            lambda *_args, **_kwargs: deliveries.append(1),
            orchestrator=lambda **_kwargs: invalid,
        ),
        request=_request(scenario),
    )

    assert result.disposition == subject.HOLD
    assert result.reason_code == subject.E6_ORCHESTRATOR_FAILED
    assert result.telegram_attempt_count == 0
    assert deliveries == []
    assert "master_engine" not in Path(subject.__file__).read_text(encoding="utf-8")
    _no_authority(result)


def test_authorized_fake_success_sends_exact_e6_message_once_and_remains_passive(
    tmp_path,
):
    scenario = _scenario(tmp_path, name="delivery-success")
    attempts = []

    def deliver(payload, *, channel, destination_id):
        attempts.append((payload, channel, destination_id))
        return _receipt(channel=channel, destination_id=destination_id)

    result = subject.run_e6_service_cycle_v1(
        root=_root(deliver),
        request=_request(scenario),
    )
    ledger = active.load_ledger(scenario["ports"].active_ledger_path)

    assert result.disposition == subject.DELIVERED
    assert result.terminal_stage == subject.STAGE_6_COMPLETE_DELIVERY_EVIDENCE
    assert result.delivery_completion_disposition == subject.DELIVERY_COMPLETED
    assert result.telegram_attempt_count == 1
    assert result.telegram_send_attempt_effect_count == 1
    assert len(attempts) == 1
    delivery_request = attempts[0][0]
    assert type(delivery_request) is E6TelegramDeliveryRequestV1
    assert delivery_request.rendered_message == format_e6_signal_message_v1(
        delivery_request.publication_envelope
    )
    assert delivery_request.rendered_message.startswith(
        "AI CRYPTO SIGNAL — MANUAL OWNER REVIEW"
    )
    assert delivery_request.publication_envelope.publication_envelope_sha256 == (
        result.envelope_sha256
    )
    assert delivery_request.delivery_id == result.delivery_id
    record = ledger["signals"][result.signal_id]
    assert record["state"] == active.PUBLISHED_PENDING_ENTRY
    assert active.inspect_capacity(ledger)["total_active"] == 0
    assert result.owner_registration_applied is True
    assert result.owner_registration_replay is False
    assert result.deepseek_provider_attempt_count == 1
    assert result.claude_provider_attempt_count == 0
    _no_authority(result)


def test_exact_completed_replay_sends_zero_additional_attempts(tmp_path):
    scenario = _scenario(tmp_path, name="delivery-replay-first")
    attempts = []
    first = subject.run_e6_service_cycle_v1(
        root=_root(
            lambda _payload, *, channel, destination_id: (
                attempts.append("first")
                or _receipt(channel=channel, destination_id=destination_id)
            )
        ),
        request=_request(scenario),
    )
    ledger_path = scenario["ports"].active_ledger_path
    ledger_bytes = ledger_path.read_bytes()
    second_ports, _deep_calls, _claude_calls = _new_ports(
        tmp_path,
        name="delivery-replay-second",
        payload=scenario["payload"],
        decision="CLEAR",
        ledger_path=ledger_path,
    )
    second_request = subject.E6ServiceCycleRequestV1(
        orchestrator_request=scenario["request"],
        orchestrator_ports=second_ports,
        channel="TELEGRAM",
        destination_id="isolated-owner-state-test",
    )
    replay = subject.run_e6_service_cycle_v1(
        root=_root(lambda *_args, **_kwargs: pytest.fail("replay delivery")),
        request=second_request,
    )

    assert first.disposition == subject.DELIVERED
    assert replay.disposition == subject.IDEMPOTENT_REPLAY
    assert replay.reason_code == subject.IDEMPOTENT_COMPLETED_REPLAY
    assert replay.delivery_completion_disposition == subject.IDEMPOTENT_COMPLETED_REPLAY
    assert replay.telegram_attempt_count == 0
    assert attempts == ["first"]
    assert replay.owner_registration_replay is True
    assert replay.owner_registration_applied is False
    assert ledger_path.read_bytes() == ledger_bytes
    _no_authority(replay)


def test_conflicting_delivery_identity_holds_without_send_overwrite_or_retry(tmp_path):
    scenario = _scenario(tmp_path, name="delivery-conflict-first")
    first = subject.run_e6_service_cycle_v1(
        root=_root(
            lambda _payload, *, channel, destination_id: _receipt(
                channel=channel,
                destination_id=destination_id,
            )
        ),
        request=_request(scenario),
    )
    ledger_path = scenario["ports"].active_ledger_path
    ledger_bytes = ledger_path.read_bytes()
    conflict_ports, _deep_calls, _claude_calls = _new_ports(
        tmp_path,
        name="delivery-conflict-second",
        payload=scenario["payload"],
        decision="CLEAR",
        ledger_path=ledger_path,
    )
    conflicting = replace(
        scenario["request"],
        publication_delivery_id="PDL-" + "f" * 64,
    )
    deliveries = []
    conflict = subject.run_e6_service_cycle_v1(
        root=_root(lambda *_args, **_kwargs: deliveries.append(1)),
        request=subject.E6ServiceCycleRequestV1(
            orchestrator_request=conflicting,
            orchestrator_ports=conflict_ports,
            channel="TELEGRAM",
            destination_id="isolated-owner-state-test",
        ),
    )

    assert first.disposition == subject.DELIVERED
    assert conflict.disposition == subject.HOLD
    assert conflict.reason_code == subject.E6_ORCHESTRATOR_TERMINAL
    assert conflict.telegram_attempt_count == 0
    assert deliveries == []
    assert ledger_path.read_bytes() == ledger_bytes
    _no_authority(conflict)


def test_one_transport_failure_is_sanitized_and_never_retried(tmp_path):
    scenario = _scenario(tmp_path, name="delivery-failure")
    attempts = []

    def fail(*_args, **_kwargs):
        attempts.append(1)
        raise RuntimeError("bot_token=fixture-secret /private/path")

    result = subject.run_e6_service_cycle_v1(
        root=_root(fail),
        request=_request(scenario),
    )

    assert result.disposition == subject.HOLD
    assert result.terminal_stage == subject.STAGE_5_ONE_TELEGRAM_ATTEMPT
    assert result.reason_code == subject.TELEGRAM_DELIVERY_FAILED
    assert result.delivery_completion_disposition == subject.TELEGRAM_DELIVERY_FAILED
    assert result.telegram_attempt_count == 1
    assert attempts == [1]
    assert "fixture-secret" not in repr(result)
    assert "private/path" not in repr(result)
    _no_authority(result)


def test_source_has_no_network_client_secret_environment_retry_or_exchange_authority():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported.isdisjoint({"httpx", "requests", "socket", "ccxt"})
    assert "os.environ" not in source
    assert "getenv(" not in source
    assert "while True" not in source
    assert "run_master_engine_v4" not in source
    assert "mark_entry_active" not in source
    assert "commit_owner_confirmed_entry" not in source
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))
    assert tuple(name for name, _ in controlled._GATES) == (
        "activation_gate",
        "workload_gate",
        "credential_gate",
        "network_gate",
        "publication_gate",
        "telegram_publication_gate",
    )
