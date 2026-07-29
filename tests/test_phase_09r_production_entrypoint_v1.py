import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from engine import active_signal_ledger_v1 as active
from engine.telegram_owner_control_state_v1 import initialize_state, load_state
from engine.run_production_signal_v1 import main

NOW = "2026-07-29T11:17:41Z"


@pytest.fixture
def valid_env():
    return {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_DESTINATION_ID": "test_dest_id",
        "TELEGRAM_MAX_MESSAGE_LENGTH": "4000",
    }


def test_missing_config_and_destination_return_2(valid_env):
    with patch.dict(os.environ, {}, clear=True):
        assert main(outcome_invocation_id="a" * 32) == 2

    env = dict(valid_env)
    del env["TELEGRAM_DESTINATION_ID"]
    with patch.dict(os.environ, env, clear=True):
        assert main(outcome_invocation_id="a" * 32) == 2


@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_outcome_invocation_identity_generated_once_and_passed_to_master(
    mock_run,
    valid_env,
):
    generated = []
    identity = "a" * 32

    def provider():
        generated.append(identity)
        return identity

    mock_run.return_value = {
        "production_signal_out": {
            "status": "OK",
            "publication": {"delivery_state": "DELIVERY_SUCCEEDED"},
        }
    }
    with patch.dict(os.environ, valid_env, clear=True):
        assert main(outcome_invocation_id_provider=provider) == 0

    mock_run.assert_called_once()
    assert generated == [identity]
    assert mock_run.call_args.kwargs["outcome_invocation_id"] == identity
    assert mock_run.call_args.kwargs["enable_publication"] is True
    assert mock_run.call_args.kwargs["owner_blueprint_ledger"] is None

    provider_calls = []
    mock_run.reset_mock()
    with patch.dict(os.environ, valid_env, clear=True):
        assert main(
            outcome_invocation_id="b" * 32,
            outcome_invocation_id_provider=lambda: provider_calls.append(True),
        ) == 0

    assert provider_calls == []
    assert mock_run.call_args.kwargs["outcome_invocation_id"] == "b" * 32


@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_missing_outcome_invocation_identity_fails_before_master(
    mock_run,
    valid_env,
):
    with patch.dict(os.environ, valid_env, clear=True):
        assert main(outcome_invocation_id_provider=lambda: None) == 7

    mock_run.assert_not_called()


@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_malformed_outcome_invocation_identity_fails_before_master(
    mock_run,
    valid_env,
):
    with patch.dict(os.environ, valid_env, clear=True):
        assert main(outcome_invocation_id="A" * 32) == 7

    mock_run.assert_not_called()


def test_static_f4_quota_values_are_not_required(valid_env):
    with patch.dict(os.environ, valid_env, clear=True):
        with patch(
            "engine.run_production_signal_v1.run_master_engine_v4"
        ) as mock_run:
            mock_run.return_value = {
                "production_signal_out": {
                    "evaluation": {"outcome_kind": "NO_TRADE"}
                }
            }
            assert main(outcome_invocation_id="a" * 32) == 0


@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_master_failure_and_delivery_failure_exit_contracts(
    mock_run,
    valid_env,
    capsys,
):
    mock_run.side_effect = Exception("General error")
    with patch.dict(os.environ, valid_env, clear=True):
        assert main(outcome_invocation_id="a" * 32) == 7
    captured = capsys.readouterr()
    assert "test_token" not in captured.out
    assert "test_token" not in captured.err

    mock_run.reset_mock()
    mock_run.side_effect = lambda *args, **kwargs: {
        "production_signal_out": {
            "status": "OK",
            "publication": {"delivery_state": "DELIVERY_FAILED"},
        }
    }
    with patch.dict(os.environ, valid_env, clear=True):
        assert main(outcome_invocation_id="b" * 32) == 5


@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_malformed_receipt_returns_6(mock_run, valid_env):
    def fake_run(*args, **kwargs):
        adapter = kwargs["delivery_adapter"]
        adapter.malformed_receipt = True
        return {
            "production_signal_out": {
                "status": "OK",
                "publication": {"delivery_state": "DELIVERY_FAILED"},
            }
        }

    mock_run.side_effect = fake_run
    with patch.dict(os.environ, valid_env, clear=True):
        assert main(outcome_invocation_id="a" * 32) == 6


def _completed_publication():
    signal_id = "PSG-" + "1" * 64
    delivery_id = "PDL-" + "2" * 64
    return {
        "delivery_state": "DELIVERY_SUCCEEDED",
        "signal_id": signal_id,
        "delivery_id": delivery_id,
        "mode": "SWING",
        "published_at": "2026-07-29T11:17:37Z",
        "source_payload_hash": "3" * 64,
        "publication_payload_hash": "4" * 64,
        "publication_payload": {
            "signal_id": signal_id,
            "mode": "SWING",
            "symbol": "KMNO/USDT:USDT",
        },
        "delivery_receipt": {
            "destination_id": "test_dest_id",
            "external_delivery_id": "913",
            "delivered_at": NOW,
        },
    }


@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_delivery_success_registers_pending_before_binding_and_replays_idempotently(
    mock_run, valid_env, tmp_path,
):
    ledger_path = tmp_path / "ledger.json"
    control_path = tmp_path / "control.json"
    active.initialize_ledger(ledger_path, created_at=NOW)
    initialize_state(control_path, timestamp=NOW)
    publication = _completed_publication()
    mock_run.return_value = {
        "production_signal_out": {"status": "OK", "publication": publication},
    }
    env = {
        **valid_env,
        "ACTIVE_SIGNAL_LEDGER_PATH": str(ledger_path),
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
    }

    with patch.dict(os.environ, env, clear=True):
        assert main(outcome_invocation_id="c" * 32) == 0

    ledger = active.load_ledger(ledger_path)
    signal = ledger["signals"][publication["signal_id"]]
    assert signal["state"] == active.PUBLISHED_PENDING_ENTRY
    assert signal["delivery_id"] == publication["delivery_id"]
    assert active.inspect_capacity(ledger)["active_by_mode"]["SWING"] == 0
    assert not any(
        record["state"] == active.ENTRY_ACTIVE
        for record in ledger["signals"].values()
    )
    binding = load_state(control_path)["signal_message_bindings"]["test_dest_id:913"]
    assert binding["signal_id"] == publication["signal_id"]
    assert binding["canonical_pair"] == "KMNO/USDT"
    before_ledger = ledger_path.read_bytes()
    before_control = control_path.read_bytes()

    with patch.dict(os.environ, env, clear=True):
        assert main(outcome_invocation_id="d" * 32) == 0

    assert ledger_path.read_bytes() == before_ledger
    assert control_path.read_bytes() == before_control


@patch("engine.run_production_signal_v1.run_master_engine_v4")
def test_registration_failure_fails_closed_without_binding_or_occupancy(
    mock_run, valid_env, tmp_path,
):
    ledger_path = tmp_path / "ledger.json"
    control_path = tmp_path / "control.json"
    active.initialize_ledger(ledger_path, created_at=NOW)
    initialize_state(control_path, timestamp=NOW)
    mock_run.return_value = {
        "production_signal_out": {
            "status": "OK", "publication": _completed_publication(),
        },
    }
    env = {
        **valid_env,
        "ACTIVE_SIGNAL_LEDGER_PATH": str(ledger_path),
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
    }

    with patch.dict(os.environ, env, clear=True), patch(
        "engine.run_production_signal_v1.signal_flow.register_completed_publication",
        return_value=SimpleNamespace(result="FAIL_CLOSED"),
    ):
        assert main(outcome_invocation_id="e" * 32) == 7
    assert active.load_ledger(ledger_path)["ledger_revision"] == 0
    assert load_state(control_path)["signal_message_bindings"] == {}
