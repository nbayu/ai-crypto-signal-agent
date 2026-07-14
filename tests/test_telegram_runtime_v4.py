import importlib
import inspect
from dataclasses import FrozenInstanceError

import pytest

from engine.quota_slot_worker_v4 import run_quota_slot_worker_v4
from engine.telegram_application_v4 import TelegramApplicationV4
from engine.telegram_runtime_v4 import (
    TelegramRuntimeConfig,
    TelegramRuntimeConfigError,
    TelegramRuntimeV4,
    build_telegram_runtime,
    load_telegram_runtime_config,
)
from engine.telegram_transport_v4 import TelegramTransportV4


TOKEN = "123456:token-like-secret-value"
ENVIRONMENT = {
    "TELEGRAM_BOT_TOKEN": TOKEN,
    "TELEGRAM_BOT_USERNAME": "configured_bot_name",
    "TELEGRAM_QUOTA_LIMIT": "3",
    "TELEGRAM_SLOT_CAPACITY": "2",
    "TELEGRAM_WINDOW_ID": "2026-W29",
    "TELEGRAM_QUOTA_STATE_PATH": "runtime/quota-state.json",
    "TELEGRAM_WORKER_STATE_PATH": "runtime/worker-state.json",
    "TELEGRAM_MAX_MESSAGE_LENGTH": "160",
}


def _config(**overrides):
    environment = dict(ENVIRONMENT)
    environment.update(overrides)
    return load_telegram_runtime_config(environment)


def _runtime(config, **overrides):
    dependencies = {
        "sender": lambda chat_id, message: None,
        "worker": lambda *, state_path: {"state_path": state_path},
        "quota_slot_worker": lambda **kwargs: {
            "admission": {"reservation_id": "reservation-001"},
            "worker_result": {"safe": True},
            "release": {"released": True},
        },
        "quota_now_provider": lambda: "2026-07-14T12:00:00",
        "reservation_id_provider": lambda: "reservation-001",
    }
    dependencies.update(overrides)
    return build_telegram_runtime(config, **dependencies)


def test_loads_immutable_redacted_runtime_configuration_from_mapping():
    config = _config()

    assert config == TelegramRuntimeConfig(
        bot_token=TOKEN,
        bot_username="configured_bot_name",
        quota_limit=3,
        slot_capacity=2,
        window_id="2026-W29",
        quota_state_path="runtime/quota-state.json",
        worker_state_path="runtime/worker-state.json",
        max_response_chars=160,
    )
    assert TOKEN not in repr(config)
    assert TOKEN not in str(config)
    with pytest.raises(FrozenInstanceError):
        config.quota_limit = 99


@pytest.mark.parametrize(
    "environment_overrides",
    [
        {"TELEGRAM_BOT_TOKEN": None},
        {"TELEGRAM_BOT_TOKEN": ""},
        {"TELEGRAM_BOT_TOKEN": "   "},
        {"TELEGRAM_QUOTA_LIMIT": "0"},
        {"TELEGRAM_QUOTA_LIMIT": "-1"},
        {"TELEGRAM_QUOTA_LIMIT": "1.5"},
        {"TELEGRAM_QUOTA_LIMIT": True},
        {"TELEGRAM_SLOT_CAPACITY": "0"},
        {"TELEGRAM_SLOT_CAPACITY": "not-a-number"},
        {"TELEGRAM_SLOT_CAPACITY": False},
        {"TELEGRAM_WINDOW_ID": None},
        {"TELEGRAM_WINDOW_ID": "   "},
        {"TELEGRAM_QUOTA_STATE_PATH": None},
        {"TELEGRAM_QUOTA_STATE_PATH": "   "},
        {"TELEGRAM_WORKER_STATE_PATH": None},
        {"TELEGRAM_WORKER_STATE_PATH": ""},
        {"TELEGRAM_MAX_MESSAGE_LENGTH": "12"},
        {"TELEGRAM_MAX_MESSAGE_LENGTH": "1.5"},
        {"TELEGRAM_MAX_MESSAGE_LENGTH": True},
        {"TELEGRAM_BOT_USERNAME": "   "},
    ],
)
def test_invalid_configuration_fails_closed_without_secret_exposure(
    environment_overrides,
):
    environment = dict(ENVIRONMENT)
    environment.update(environment_overrides)

    with pytest.raises(TelegramRuntimeConfigError) as exc_info:
        load_telegram_runtime_config(environment)

    assert TOKEN not in str(exc_info.value)
    assert TOKEN not in repr(exc_info.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("TELEGRAM_QUOTA_LIMIT", None),
        ("TELEGRAM_QUOTA_LIMIT", " "),
        ("TELEGRAM_SLOT_CAPACITY", None),
        ("TELEGRAM_MAX_MESSAGE_LENGTH", "-2"),
    ],
)
def test_numeric_configuration_does_not_silently_coerce_invalid_values(
    name, value
):
    with pytest.raises(TelegramRuntimeConfigError):
        _config(**{name: value})


def test_loading_config_does_not_touch_configured_paths(tmp_path):
    quota_state_path = tmp_path / "quota" / "state.json"
    worker_state_path = tmp_path / "worker" / "state.json"

    config = _config(
        TELEGRAM_QUOTA_STATE_PATH=str(quota_state_path),
        TELEGRAM_WORKER_STATE_PATH=str(worker_state_path),
    )

    assert config.quota_state_path == str(quota_state_path)
    assert config.worker_state_path == str(worker_state_path)
    assert list(tmp_path.iterdir()) == []


def test_composition_wires_config_and_injected_dependencies_without_execution():
    config = _config()
    sender_calls = []
    worker_calls = []
    runner_calls = []

    def sender(chat_id, message):
        sender_calls.append((chat_id, message))

    def worker(*, state_path):
        worker_calls.append(state_path)
        return {"state_path": state_path}

    def quota_slot_worker(**kwargs):
        runner_calls.append(kwargs)
        worker_result = kwargs["worker"](state_path=kwargs["worker_state_path"])
        return {
            "admission": {"reservation_id": "reservation-001"},
            "worker_result": worker_result,
            "release": {"released": True},
        }

    runtime = _runtime(
        config,
        sender=sender,
        worker=worker,
        quota_slot_worker=quota_slot_worker,
    )

    assert isinstance(runtime, TelegramRuntimeV4)
    assert runtime.config is config
    assert isinstance(runtime.application, TelegramApplicationV4)
    assert isinstance(runtime.transport, TelegramTransportV4)
    assert sender_calls == []
    assert worker_calls == []
    assert runner_calls == []

    runtime.handle_update(
        {
            "message": {
                "text": "/status",
                "from_user": {"id": 123456},
                "chat": {"id": -100987654321},
            }
        }
    )

    request_type = importlib.import_module(
        "engine.telegram_application_v4"
    ).TelegramCommandRequest
    runtime.application.dispatch(
        request_type(
            command="/scan",
            telegram_user_id=123456,
            chat_id=-100987654321,
        )
    )

    assert len(runner_calls) == 1
    forwarded = runner_calls[0]
    assert forwarded | {"worker": None} == {
        "subject_id": "telegram:user:123456",
        "window_id": "2026-W29",
        "quota_limit": 3,
        "slot_capacity": 2,
        "quota_state_path": "runtime/quota-state.json",
        "worker_state_path": "runtime/worker-state.json",
        "quota_now_provider": forwarded["quota_now_provider"],
        "reservation_id_provider": forwarded["reservation_id_provider"],
        "worker": None,
    }
    assert worker_calls == ["runtime/worker-state.json"]
    assert sender_calls == [(-100987654321, "Interface ready.")]


def test_runtime_factory_defaults_to_the_canonical_quota_slot_boundary():
    parameters = inspect.signature(build_telegram_runtime).parameters

    assert parameters["quota_slot_worker"].default is run_quota_slot_worker_v4


def test_start_is_explicit_and_passes_only_token_and_update_handler():
    config = _config()
    runtime = _runtime(config)
    runner_calls = []

    def sdk_runner(*, token, handle_update):
        runner_calls.append({"token": token, "handle_update": handle_update})
        return "runner-result"

    assert runner_calls == []
    assert runtime.start(sdk_runner) == "runner-result"
    assert runner_calls == [
        {"token": TOKEN, "handle_update": runtime.handle_update}
    ]


def test_invalid_configuration_prevents_startup_runner_invocation():
    runner_calls = []

    with pytest.raises(TelegramRuntimeConfigError):
        _config(TELEGRAM_WINDOW_ID=" ")

    assert runner_calls == []


def test_runner_failure_propagates_once_without_token_wrapping():
    runtime = _runtime(_config())
    runner_error = RuntimeError("runner failed with sk-live-secret")
    runner_calls = []

    def sdk_runner(*, token, handle_update):
        runner_calls.append((token, handle_update))
        raise runner_error

    with pytest.raises(RuntimeError) as exc_info:
        runtime.start(sdk_runner)

    assert exc_info.value is runner_error
    assert runner_calls == [(TOKEN, runtime.handle_update)]


def test_module_has_no_forbidden_sdk_or_engine_references():
    module = importlib.import_module("engine.telegram_runtime_v4")
    source = inspect.getsource(module)

    for name in (
        "acquire_quota_slot_v4",
        "release_quota_slot_v4",
        "run_master_engine_worker_v4",
        "scan_symbol",
        "scan_market",
        "python-telegram-bot",
        "telegram.ext",
        "aiogram",
    ):
        assert name not in source


def test_import_is_side_effect_free_without_environment_configuration(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)

    module = importlib.import_module("engine.telegram_runtime_v4")
    importlib.reload(module)

    assert list(tmp_path.iterdir()) == []
