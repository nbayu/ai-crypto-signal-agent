import os
from unittest.mock import patch

import pytest

from engine.run_production_signal_v1 import main


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
