"""Static and configuration contracts for the dedicated control runtime."""

import ast
import asyncio
import importlib
from pathlib import Path
import runpy
import sys
import types

import pytest

from engine import active_signal_ledger_v1 as active
from engine.run_telegram_owner_control_v1 import (
    TelegramOwnerControlConfigV1,
    load_owner_control_config,
    run_forever,
)
from engine.telegram_owner_control_state_v1 import initialize_state, load_state


MODULE_NAME = "engine.run_telegram_owner_control_v1"


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


def _configure_main_environment(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "telegram_bot_token").write_text("fixture-token", encoding="utf-8")
    values = {
        "CREDENTIALS_DIRECTORY": str(tmp_path),
        "TELEGRAM_OWNER_USER_ID": "100",
        "TELEGRAM_OWNER_CHAT_ID": "200",
        "ACTIVE_SIGNAL_LEDGER_PATH": str(tmp_path / "ledger.json"),
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(tmp_path / "control.json"),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_module_import_does_not_start_controller(monkeypatch, tmp_path: Path):
    _configure_main_environment(monkeypatch, tmp_path)
    start_count = 0

    def fail_if_started(coroutine):
        nonlocal start_count
        start_count += 1
        coroutine.close()
        raise AssertionError("normal import started controller")

    monkeypatch.setattr(asyncio, "run", fail_if_started)
    monkeypatch.delitem(sys.modules, MODULE_NAME, raising=False)

    module = importlib.import_module(MODULE_NAME)

    assert callable(module.main)
    assert start_count == 0


def test_module_main_execution_invokes_main_once_and_propagates_exit_code(
    monkeypatch, tmp_path: Path
):
    _configure_main_environment(monkeypatch, tmp_path)
    start_count = 0

    def isolated_run(coroutine):
        nonlocal start_count
        start_count += 1
        coroutine.close()

    monkeypatch.setattr(asyncio, "run", isolated_run)
    monkeypatch.delitem(sys.modules, MODULE_NAME, raising=False)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module(MODULE_NAME, run_name="__main__")

    assert exc_info.value.code == 0
    assert start_count == 1


def test_run_forever_enters_polling_once_with_fake_bot_and_no_network(
    monkeypatch, tmp_path: Path
):
    class PollingReached(RuntimeError):
        pass

    class FakeBot:
        get_updates_count = 0

        def __init__(self, *, token: str):
            assert token == "fixture-token"

        async def get_updates(self, *, offset: int, timeout: int):
            assert offset == 1
            assert timeout == 25
            type(self).get_updates_count += 1
            raise PollingReached

    fake_telegram = types.ModuleType("telegram")
    fake_telegram.Bot = FakeBot
    monkeypatch.setitem(sys.modules, "telegram", fake_telegram)

    from engine import telegram_owner_control_state_v1

    monkeypatch.setattr(
        telegram_owner_control_state_v1,
        "load_state",
        lambda _path: {"last_update_id": 0},
    )
    config = TelegramOwnerControlConfigV1(
        owner_user_id="100",
        owner_chat_id="200",
        ledger_path=tmp_path / "ledger.json",
        state_path=tmp_path / "control.json",
        token_file=tmp_path / "telegram_bot_token",
    )

    with pytest.raises(PollingReached):
        asyncio.run(run_forever(config, "fixture-token"))

    assert FakeBot.get_updates_count == 1


def test_release_wrapper_module_target_rejects_silent_success_without_controller_start():
    root = Path(__file__).parents[1]
    wrapper = (
        root / "deploy/operational_v1/bin/ai-crypto-signal-agent-telegram-control"
    ).read_text(encoding="utf-8")
    assert 'exec "$PYTHON_BIN" -m engine.run_telegram_owner_control_v1' in wrapper

    tree = ast.parse(
        (root / "engine/run_telegram_owner_control_v1.py").read_text(encoding="utf-8")
    )
    guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and ast.unparse(node.test) == "__name__ == '__main__'"
    ]
    assert len(guards) == 1
    assert len(guards[0].body) == 1
    statement = guards[0].body[0]
    assert isinstance(statement, ast.Raise)
    assert ast.unparse(statement.exc) == "SystemExit(main())"


class _FakeUpdate:
    def __init__(self, value):
        self._value = value

    def to_dict(self):
        return self._value


def _runtime_config(tmp_path: Path) -> TelegramOwnerControlConfigV1:
    ledger_path = tmp_path / "ledger.json"
    state_path = tmp_path / "control.json"
    active.initialize_ledger(ledger_path, created_at="2026-07-28T00:00:00Z")
    initialize_state(state_path, timestamp="2026-07-28T00:00:00Z")
    return TelegramOwnerControlConfigV1(
        owner_user_id="100", owner_chat_id="200", ledger_path=ledger_path,
        state_path=state_path, token_file=tmp_path / "telegram_bot_token",
    )


def test_run_forever_sends_first_decision_once_and_suppresses_replay(
    monkeypatch, tmp_path, caplog,
):
    caplog.set_level("INFO")

    class PollingComplete(RuntimeError):
        pass

    update = {"update_id": 50, "message": {
        "message_id": 1050, "from": {"id": 100}, "chat": {"id": 200},
        "text": "unsupported",
    }}

    class FakeBot:
        offsets = []
        sends = []

        def __init__(self, *, token):
            assert token == "fixture-token"

        async def get_updates(self, *, offset, timeout):
            assert timeout == 25
            type(self).offsets.append(offset)
            if len(type(self).offsets) > 2:
                raise PollingComplete
            return [_FakeUpdate(update)]

        async def send_message(self, **kwargs):
            type(self).sends.append(kwargs)
            return types.SimpleNamespace(message_id=9050)

    fake_telegram = types.ModuleType("telegram")
    fake_telegram.Bot = FakeBot
    monkeypatch.setitem(sys.modules, "telegram", fake_telegram)
    config = _runtime_config(tmp_path)

    with pytest.raises(PollingComplete):
        asyncio.run(run_forever(config, "fixture-token"))

    assert FakeBot.offsets == [0, 51, 51]
    assert len(FakeBot.sends) == 1
    decision = load_state(config.state_path)["processed_updates"]["50"]
    assert decision["response_message_id"] == 9050
    send_records = [
        record for record in caplog.records
        if record.msg == "telegram_owner_response_sent"
    ]
    assert len(send_records) == 1
    assert send_records[0].update_id == 50
    assert send_records[0].response_message_id == 9050


def test_send_failure_then_restart_replay_produces_no_second_attempt(
    monkeypatch, tmp_path,
):
    class FloodControlFailure(RuntimeError):
        pass

    class PollingComplete(RuntimeError):
        pass

    update = {"update_id": 60, "message": {
        "message_id": 1060, "from": {"id": 999}, "chat": {"id": 200},
        "text": "/status",
    }}

    class FirstBot:
        send_attempts = 0

        def __init__(self, *, token):
            assert token == "fixture-token"

        async def get_updates(self, *, offset, timeout):
            assert offset == 0 and timeout == 25
            return [_FakeUpdate(update)]

        async def send_message(self, **_kwargs):
            type(self).send_attempts += 1
            raise FloodControlFailure

    fake_telegram = types.ModuleType("telegram")
    fake_telegram.Bot = FirstBot
    monkeypatch.setitem(sys.modules, "telegram", fake_telegram)
    config = _runtime_config(tmp_path)

    with pytest.raises(FloodControlFailure):
        asyncio.run(run_forever(config, "fixture-token"))
    assert FirstBot.send_attempts == 1
    assert load_state(config.state_path)["last_update_id"] == 60

    class RestartBot:
        send_attempts = 0
        polls = 0

        def __init__(self, *, token):
            assert token == "fixture-token"

        async def get_updates(self, *, offset, timeout):
            assert offset == 61 and timeout == 25
            type(self).polls += 1
            if type(self).polls > 1:
                raise PollingComplete
            return [_FakeUpdate(update)]

        async def send_message(self, **_kwargs):
            type(self).send_attempts += 1
            raise AssertionError("duplicate response attempted")

    fake_telegram.Bot = RestartBot
    with pytest.raises(PollingComplete):
        asyncio.run(run_forever(config, "fixture-token"))

    assert RestartBot.send_attempts == 0
    assert load_state(config.state_path)["last_update_id"] == 60
