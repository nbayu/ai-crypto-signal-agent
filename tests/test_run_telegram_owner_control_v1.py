"""Static and configuration contracts for the dedicated control runtime."""

from pathlib import Path

import pytest

from engine.run_telegram_owner_control_v1 import load_owner_control_config


def test_config_uses_credential_file_and_explicit_owner_authority(tmp_path):
    config = load_owner_control_config({
        "CREDENTIALS_DIRECTORY": str(tmp_path), "TELEGRAM_OWNER_USER_ID": "100",
        "TELEGRAM_OWNER_CHAT_ID": "200", "ACTIVE_SIGNAL_LEDGER_PATH": "/state/ledger.json",
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": "/state/control.json",
    })
    assert config.token_file == tmp_path / "telegram_bot_token"
    assert config.owner_user_id == "100" and config.owner_chat_id == "200"
    with pytest.raises(ValueError):
        load_owner_control_config({})


def test_runtime_is_continuous_and_contains_no_order_path():
    source = (Path(__file__).parents[1] / "engine" / "run_telegram_owner_control_v1.py").read_text()
    assert "while True" in source and "get_updates" in source
    assert not any(term in source for term in ("create_order", "place_order", "exchange.create"))
