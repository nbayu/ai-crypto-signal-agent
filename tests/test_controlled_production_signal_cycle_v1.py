"""Focused contracts for one controlled publication and registration cycle."""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from engine import controlled_production_signal_cycle_v1 as cycle
from engine import active_signal_ledger_v1 as active
from engine import passive_production_signal_flow_v1 as flow
from engine import e6_service_composition_root_v1 as e6_service
from test_e6_integrated_orchestrator_v1 import _scenario


NOW = "2026-07-21T00:00:00Z"
SOURCE_HASH = "a" * 64
PAYLOAD_HASH = "b" * 64


def _authorization(**changes):
    values = {name: True for name, _ in cycle._GATES}
    values.update(changes)
    return cycle.ControlledProductionSignalCycleAuthorizationV1(**values)


def _candidate(**changes):
    value = {
        "schema_version": 1,
        "schema_name": "production-signal-input",
        "source_commit": "1" * 40,
        "source_evaluation_id": "evaluation-one",
        "mode": "SWING",
        "evaluated_at": NOW,
        "production_evidence_ref": {
            "manifest_hash": "c" * 64,
            "manifest_path": "evidence/manifest.json",
        },
        "outcome_kind": "PUBLISHED_SIGNAL",
        "eligible_setups": [{
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_zone": {"min": 100.0, "max": 101.0},
            "stop_loss": 95.0,
            "take_profit": {"tp1": 110.0, "tp2": 120.0},
            "valid_until": "2026-07-22T00:00:00Z",
            "strategy_version": "candidate-v1",
            "source_payload_hash": SOURCE_HASH,
        }],
        "component_versions": {"candidate": "v1"},
    }
    value.update(changes)
    return value


def _publication(state="DELIVERY_SUCCEEDED"):
    return {
        "delivery_state": state,
        "signal_id": "PSG-" + "d" * 64,
        "delivery_id": "PDL-" + "e" * 64,
        "mode": "SWING",
        "published_at": NOW,
        "source_payload_hash": SOURCE_HASH,
        "publication_payload_hash": PAYLOAD_HASH,
        "content_hash": "f" * 64,
        "publication_payload": {
            "signal_id": "PSG-" + "d" * 64,
            "mode": "SWING",
            "symbol": "BTCUSDT",
        },
    }


def _registration(**changes):
    values = {
        "result": flow.PUBLISHED_SIGNAL_REGISTERED,
        "operation": flow.REGISTER_COMPLETED_PUBLICATION,
        "signal_id": "PSG-" + "d" * 64,
        "mode": "SWING",
        "symbol": "BTCUSDT",
        "delivery_id": "PDL-" + "e" * 64,
        "publication_identity_hash": "f" * 64,
        "signal_payload_hash": SOURCE_HASH,
        "reservation_transaction_id": "transaction-one",
        "reservation_transition_id": "reservation-one",
        "entry_transition_id": None,
        "terminal_transition_id": None,
        "active_ledger_revision": 4,
        "refill_request_id": None,
        "refill_ledger_revision": None,
        "previous_state": None,
        "current_state": "PUBLISHED_PENDING_ENTRY",
        "publication_confirmed": True,
        "registration_applied": True,
        "entry_applied": False,
        "terminal_applied": False,
        "refill_reconciled": False,
        "partial_success": False,
        "replay": False,
        "reason": flow.PUBLISHED_SIGNAL_REGISTERED,
        "timestamp": NOW,
    }
    values.update(changes)
    return flow.PassiveProductionSignalFlowResultV1(**values)


def _call(**changes):
    values = {
        "authorization": _authorization(),
        "candidate_source": lambda: _candidate(),
        "credential_loader": lambda: object(),
        "delivery_adapter_factory": lambda _: (lambda *_args, **_kwargs: object()),
        "publication_root": "publication-root",
        "channel": "telegram",
        "destination_id": "destination-hidden",
        "component_versions": {"candidate": "v1"},
        "active_ledger_path": "active-ledger-hidden",
        "expected_active_ledger_revision": 3,
        "reservation_transition_id": "reservation-one",
        "timestamp": NOW,
    }
    values.update(changes)
    return cycle.run_controlled_production_signal_cycle(**values)


def _install_success(monkeypatch, registration=None):
    calls = {"publication": [], "registration": []}

    def published(**kwargs):
        calls["publication"].append(kwargs)
        return {"publication": _publication(), "artifact_path": "/not/read"}

    def registered(**kwargs):
        calls["registration"].append(kwargs)
        return registration or _registration()

    monkeypatch.setattr(cycle.production, "run_production_signal_service_v1", published)
    monkeypatch.setattr(cycle.flow, "register_completed_publication", registered)
    return calls


def test_authorization_and_result_types_are_frozen_slotted_and_ordered():
    assert cycle.ControlledProductionSignalCycleAuthorizationV1.__dataclass_params__.frozen
    assert cycle.ControlledProductionSignalCycleResultV1.__dataclass_params__.frozen
    assert hasattr(cycle.ControlledProductionSignalCycleAuthorizationV1, "__slots__")
    assert hasattr(cycle.ControlledProductionSignalCycleResultV1, "__slots__")
    assert tuple(cycle.ControlledProductionSignalCycleAuthorizationV1().to_dict()) == (
        "activation_gate", "workload_gate", "credential_gate", "network_gate",
        "publication_gate", "telegram_publication_gate",
    )
    assert tuple(field.name for field in fields(cycle.ControlledProductionSignalCycleResultV1)) == (
        "result", "operation", "gate", "signal_id", "delivery_id", "mode", "symbol",
        "reservation_transaction_id", "reservation_transition_id", "active_ledger_revision",
        "publication_confirmed", "registration_applied", "partial_success", "replay",
        "candidate_generated", "publication_attempted", "delivery_attempted",
        "registration_attempted", "reason", "timestamp",
        "e6_service_result",
    )


def test_all_authorization_defaults_are_closed():
    assert not any(cycle.ControlledProductionSignalCycleAuthorizationV1().to_dict().values())


@pytest.mark.parametrize("field, expected", cycle._GATES)
def test_each_gate_closes_in_order_and_prevents_all_dependencies(field, expected):
    calls = []
    gates = _authorization(**{field: False})
    result = _call(
        authorization=gates,
        credential_loader=lambda: calls.append("credential"),
        candidate_source=lambda: calls.append("candidate"),
        delivery_adapter_factory=lambda _: calls.append("adapter"),
    )
    assert result.result == expected and result.gate == expected and result.reason == expected
    assert calls == []
    assert not any((result.candidate_generated, result.publication_attempted,
                    result.delivery_attempted, result.registration_attempted,
                    result.publication_confirmed, result.registration_applied,
                    result.partial_success, result.replay))


def test_invalid_authorization_fails_closed_without_dependency_invocation():
    calls = []
    result = _call(
        authorization={"activation_gate": True},
        credential_loader=lambda: calls.append("credential"),
    )
    assert result.result == cycle.FAIL_CLOSED and result.reason == cycle.INVALID_AUTHORIZATION
    assert calls == []


def test_credential_failure_is_sanitized_and_stops_before_candidate():
    calls = []
    result = _call(
        credential_loader=lambda: (_ for _ in ()).throw(RuntimeError("credential-canary")),
        candidate_source=lambda: calls.append("candidate"),
    )
    assert result.result == cycle.CREDENTIAL_LOAD_FAILED
    assert result.reason == cycle.CREDENTIAL_LOAD_FAILED
    assert "credential-canary" not in repr(result)
    assert calls == []


def test_credential_candidate_and_adapter_are_each_called_once(monkeypatch):
    calls = []
    delegated = _install_success(monkeypatch)
    result = _call(
        credential_loader=lambda: calls.append("credential") or object(),
        candidate_source=lambda: calls.append("candidate") or _candidate(),
        delivery_adapter_factory=lambda _: calls.append("adapter") or (lambda *_a, **_k: object()),
    )
    assert calls == ["credential", "candidate", "adapter"]
    assert len(delegated["publication"]) == len(delegated["registration"]) == 1
    assert result.result == flow.PUBLISHED_SIGNAL_REGISTERED


@pytest.mark.parametrize("candidate", (None, {"result": cycle.NO_ELIGIBLE_SIGNAL}))
def test_no_eligible_candidate_prevents_adapter_publication_and_registration(candidate, monkeypatch):
    calls = []
    _install_success(monkeypatch)
    result = _call(
        candidate_source=lambda: candidate,
        delivery_adapter_factory=lambda _: calls.append("adapter"),
    )
    assert result.result == cycle.NO_ELIGIBLE_SIGNAL
    assert not result.candidate_generated and calls == []


@pytest.mark.parametrize(
    "candidate",
    (
        {"mode": "invalid"},
        _candidate(channel="telegram"),
        _candidate(destination_id="unexpected"),
        _candidate(token="forbidden"),
    ),
)
def test_invalid_candidate_is_closed_before_adapter_and_publication(candidate, monkeypatch):
    calls = []
    _install_success(monkeypatch)
    result = _call(
        candidate_source=lambda: candidate,
        delivery_adapter_factory=lambda _: calls.append("adapter"),
    )
    assert result.result == cycle.INVALID_SIGNAL_CANDIDATE
    assert result.candidate_generated and calls == []
    assert not result.publication_attempted and not result.registration_attempted


def test_adapter_failure_is_sanitized_before_publication(monkeypatch):
    _install_success(monkeypatch)
    result = _call(
        delivery_adapter_factory=lambda _: (_ for _ in ()).throw(RuntimeError("adapter-canary")),
    )
    assert result.result == cycle.DELIVERY_ADAPTER_UNAVAILABLE
    assert "adapter-canary" not in repr(result)
    assert result.candidate_generated and not result.publication_attempted


def test_publication_failure_and_delivery_failure_never_register(monkeypatch):
    publication_calls = []
    registration_calls = []

    def failed(**kwargs):
        publication_calls.append(kwargs)
        raise RuntimeError("publication-canary")

    monkeypatch.setattr(cycle.production, "run_production_signal_service_v1", failed)
    monkeypatch.setattr(cycle.flow, "register_completed_publication", lambda **kwargs: registration_calls.append(kwargs))
    failed_result = _call()
    assert failed_result.result == cycle.PUBLICATION_FAILED
    assert len(publication_calls) == 1 and registration_calls == []

    monkeypatch.setattr(
        cycle.production,
        "run_production_signal_service_v1",
        lambda **_: {"publication": _publication("DELIVERY_FAILED")},
    )
    delivery_result = _call()
    assert delivery_result.result == cycle.DELIVERY_FAILED
    assert not delivery_result.publication_confirmed and registration_calls == []


def test_successful_publication_is_passed_in_memory_once_without_artifact_read(monkeypatch):
    delegated = _install_success(monkeypatch)
    result = _call()
    assert result.publication_confirmed and result.registration_applied
    assert delegated["registration"][0]["publication_evidence"] == _publication()
    assert "artifact_path" not in delegated["registration"][0]
    assert result.to_dict()["reservation_transition_id"] == "reservation-one"


@pytest.mark.parametrize(
    "registration",
    (
        _registration(result=flow.PUBLISHED_SIGNAL_REGISTRATION_REPLAYED, replay=True,
                      registration_applied=False, reason=flow.PUBLISHED_SIGNAL_REGISTRATION_REPLAYED),
        _registration(result=flow.REGISTRATION_ALREADY_PRESENT, replay=True,
                      registration_applied=False, reason=flow.REGISTRATION_ALREADY_PRESENT),
        _registration(result=flow.PUBLICATION_SUCCEEDED_REGISTRATION_PENDING,
                      registration_applied=False, partial_success=True,
                      reason=flow.PUBLICATION_SUCCEEDED_REGISTRATION_PENDING),
        _registration(result=flow.ACTIVE_REVISION_CONFLICT, registration_applied=False,
                      reason=flow.ACTIVE_REVISION_CONFLICT),
        _registration(result=flow.SIGNAL_IDENTITY_CONFLICT, registration_applied=False,
                      reason=flow.SIGNAL_IDENTITY_CONFLICT),
        _registration(result=flow.TRANSACTION_IDENTITY_CONFLICT, registration_applied=False,
                      reason=flow.TRANSACTION_IDENTITY_CONFLICT),
        _registration(result=flow.RESERVATION_IDENTITY_CONFLICT, registration_applied=False,
                      reason=flow.RESERVATION_IDENTITY_CONFLICT),
        _registration(result=flow.ACTIVE_LEDGER_FAILURE, registration_applied=False,
                      reason=flow.ACTIVE_LEDGER_FAILURE),
    ),
)
def test_registration_results_preserve_identity_revision_replay_and_partial_success(monkeypatch, registration):
    _install_success(monkeypatch, registration=registration)
    result = _call()
    assert result.result == registration.result and result.reason == registration.reason
    assert result.active_ledger_revision == registration.active_ledger_revision
    assert result.replay is registration.replay and result.partial_success is registration.partial_success
    assert result.publication_confirmed and result.registration_attempted


def test_configuration_failure_and_registration_exception_are_sanitized(monkeypatch):
    invalid = _call(component_versions={})
    assert invalid.result == cycle.FAIL_CLOSED and invalid.reason == cycle.INVALID_CYCLE_CONFIGURATION

    _install_success(monkeypatch)
    monkeypatch.setattr(
        cycle.flow,
        "register_completed_publication",
        lambda **_: (_ for _ in ()).throw(RuntimeError("/hidden/path")),
    )
    failed = _call()
    assert failed.result == cycle.FAIL_CLOSED and failed.publication_confirmed
    assert "/hidden/path" not in repr(failed)


def test_source_contains_no_operational_surface_or_leakage():
    source = Path(cycle.__file__).read_text()
    forbidden = (
        "active_signal_ledger", "scan_market", "master_engine", "telegram_runtime",
        "telegram_sdk", "subprocess", "os.environ", "getenv", "while True",
        "activate_registered_signal", "terminate_active_signal", "claim_refill_request",
        "str(exc)", "repr(exc)", "BaseException",
    )
    assert not any(value in source for value in forbidden)


def test_active_pair_gate_stops_before_adapter_and_publication(monkeypatch, tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = active.initialize_ledger(ledger_path, created_at=NOW)
    ledger = active.reserve_published_signal(
        ledger_path, expected_revision=0, transaction_id="tx", transition_id="reserve",
        signal_id="signal", delivery_id="delivery", mode=active.SWING,
        symbol="BTC/USDT", published_at=NOW, source_payload_hash=SOURCE_HASH,
        publication_payload_hash=PAYLOAD_HASH, updated_at=NOW,
    )
    ledger = active.mark_entry_active(
        ledger_path, expected_revision=ledger["ledger_revision"], transition_id="entry",
        signal_id="signal", entry_at=NOW, updated_at=NOW,
    )
    calls = []
    monkeypatch.setattr(cycle.production, "run_production_signal_service_v1", lambda **_: calls.append("publish"))
    result = _call(
        owner_blueprint_ledger=ledger,
        delivery_adapter_factory=lambda _: calls.append("adapter"),
    )
    assert result.result == cycle.NO_ELIGIBLE_SIGNAL
    assert result.reason == "GLOBAL_PAIR_ACTIVE"
    assert calls == [] and not result.delivery_attempted


def test_e6_selected_cycle_delegates_without_legacy_publication_bypass(tmp_path):
    scenario = _scenario(tmp_path, name="controlled-e6")
    deliveries = []

    def deliver(payload, *, channel, destination_id):
        deliveries.append(payload)
        return {
            "channel": channel,
            "destination_id": destination_id,
            "external_delivery_id": "fixture-message-1",
            "delivered_at": "2026-07-30T13:00:01Z",
        }

    request = e6_service.E6ServiceCycleRequestV1(
        orchestrator_request=scenario["request"],
        orchestrator_ports=scenario["ports"],
        channel="TELEGRAM",
        destination_id="isolated-owner-state-test",
    )
    root = e6_service.E6ServiceCompositionRootV1(
        telegram_delivery=deliver,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
    )
    legacy_calls = []

    result = _call(
        credential_loader=lambda: legacy_calls.append("credential"),
        candidate_source=lambda: legacy_calls.append("candidate"),
        delivery_adapter_factory=lambda _: legacy_calls.append("legacy-adapter"),
        e6_composition_root=root,
        e6_cycle_request=request,
        e6_required=True,
    )

    assert result.result == e6_service.DELIVERED
    assert result.e6_service_result is not None
    assert result.e6_service_result.telegram_attempt_count == 1
    assert len(deliveries) == 1
    assert legacy_calls == []
    assert result.e6_service_result.owner_decision_count == 0
    assert result.e6_service_result.entry_active_mutation_count == 0
    assert result.e6_service_result.slot_mutation_count == 0
    assert result.e6_service_result.pair_lock_mutation_count == 0
    assert result.e6_service_result.exchange_order_count == 0


def test_e6_required_without_typed_composition_fails_before_legacy_dependencies():
    calls = []
    result = _call(
        credential_loader=lambda: calls.append("credential"),
        candidate_source=lambda: calls.append("candidate"),
        delivery_adapter_factory=lambda _: calls.append("adapter"),
        e6_required=True,
    )
    assert result.result == cycle.FAIL_CLOSED
    assert result.reason == cycle.INVALID_CYCLE_CONFIGURATION
    assert calls == []
