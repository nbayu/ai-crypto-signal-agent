import asyncio
import importlib
import inspect

import pytest

from engine.telegram_sdk_runner_v4 import (
    build_runtime_sdk_runner_v4,
    run_telegram_polling_v4,
)


TOKEN = "123456:telegram-token-must-remain-secret"


class FakeBot:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def send_message(self, *, chat_id, text):
        self.calls.append((chat_id, text))
        if self.error is not None:
            raise self.error


class FakeApplication:
    def __init__(self):
        self.handlers = []
        self.polling_calls = 0

    def add_handler(self, handler):
        self.handlers.append(handler)

    def run_polling(self):
        self.polling_calls += 1
        return "polling-started"


class FakeApplicationBuilder:
    def __init__(self, application):
        self.application = application
        self.tokens = []
        self.build_calls = 0

    def token(self, token):
        self.tokens.append(token)
        return self

    def build(self):
        self.build_calls += 1
        return self.application


class FakeMessageHandler:
    def __init__(self, filters, callback):
        self.filters = filters
        self.callback = callback


class FakeFilters:
    COMMAND = object()


class FakeContext:
    def __init__(self, bot):
        self.bot = bot


class FakeRuntime:
    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = []

    def handle_update_with_sender(self, update, sender):
        self.calls.append((update, sender))
        return self.behavior(update, sender)


def _runner_dependencies(application):
    builder = FakeApplicationBuilder(application)
    builder_factory_calls = []

    def builder_factory():
        builder_factory_calls.append(True)
        return builder

    return builder, builder_factory, builder_factory_calls


def _run_runner(*, runtime, application):
    builder, builder_factory, builder_factory_calls = _runner_dependencies(
        application
    )
    result = run_telegram_polling_v4(
        token=TOKEN,
        runtime=runtime,
        application_builder_factory=builder_factory,
        message_handler_factory=FakeMessageHandler,
        filters_module=FakeFilters,
    )
    return result, builder, builder_factory_calls


def _handler(application):
    assert len(application.handlers) == 1
    return application.handlers[0]


def test_runner_builds_once_registers_one_generic_handler_and_polls_once():
    runtime = FakeRuntime(lambda update, sender: False)
    application = FakeApplication()

    result, builder, builder_factory_calls = _run_runner(
        runtime=runtime,
        application=application,
    )

    assert result == "polling-started"
    assert builder_factory_calls == [True]
    assert builder.tokens == [TOKEN]
    assert builder.build_calls == 1
    assert application.polling_calls == 1
    assert runtime.calls == []
    handler = _handler(application)
    assert handler.filters is FakeFilters.COMMAND


@pytest.mark.parametrize("token", [None, 7, "", "   "])
def test_invalid_token_fails_before_sdk_builder_creation_without_leaking_it(token):
    application = FakeApplication()
    builder, builder_factory, builder_factory_calls = _runner_dependencies(
        application
    )
    runtime = FakeRuntime(lambda update, sender: False)

    with pytest.raises(ValueError) as error:
        run_telegram_polling_v4(
            token=token,
            runtime=runtime,
            application_builder_factory=builder_factory,
            message_handler_factory=FakeMessageHandler,
            filters_module=FakeFilters,
        )

    assert TOKEN not in str(error.value)
    if isinstance(token, str) and token:
        assert token not in str(error.value)
    assert builder_factory_calls == []
    assert builder.tokens == []
    assert application.polling_calls == 0


def test_handler_forwards_one_update_to_runtime_and_delivers_one_buffered_message():
    update = {"update": "one"}

    def behavior(received_update, sender):
        assert received_update is update
        sender(-1001, "Safe normalized response")
        return True

    runtime = FakeRuntime(behavior)
    application = FakeApplication()
    _run_runner(runtime=runtime, application=application)
    bot = FakeBot()

    asyncio.run(_handler(application).callback(update, FakeContext(bot)))

    assert len(runtime.calls) == 1
    assert runtime.calls[0][0] is update
    assert bot.calls == [(-1001, "Safe normalized response")]


def test_handler_does_not_send_when_runtime_ignores_update_without_buffering():
    runtime = FakeRuntime(lambda update, sender: False)
    application = FakeApplication()
    _run_runner(runtime=runtime, application=application)
    bot = FakeBot()

    asyncio.run(_handler(application).callback({"update": "ignored"}, FakeContext(bot)))

    assert len(runtime.calls) == 1
    assert bot.calls == []


def test_handler_rejects_multiple_buffered_messages_without_delivery_or_retry():
    def behavior(update, sender):
        sender(1, "first")
        sender(1, "second")

    runtime = FakeRuntime(behavior)
    application = FakeApplication()
    _run_runner(runtime=runtime, application=application)
    bot = FakeBot()

    with pytest.raises(RuntimeError):
        asyncio.run(_handler(application).callback({"update": "many"}, FakeContext(bot)))

    assert len(runtime.calls) == 1
    assert bot.calls == []


def test_runtime_failure_propagates_without_send_or_retry():
    failure = RuntimeError("runtime internal detail")

    def behavior(update, sender):
        raise failure

    runtime = FakeRuntime(behavior)
    application = FakeApplication()
    _run_runner(runtime=runtime, application=application)
    bot = FakeBot()

    with pytest.raises(RuntimeError) as error:
        asyncio.run(_handler(application).callback({"update": "fail"}, FakeContext(bot)))

    assert error.value is failure
    assert len(runtime.calls) == 1
    assert bot.calls == []


def test_sdk_send_failure_propagates_without_rerunning_runtime():
    failure = RuntimeError("SDK send failed")

    def behavior(update, sender):
        sender(42, "Safe response")

    runtime = FakeRuntime(behavior)
    application = FakeApplication()
    _run_runner(runtime=runtime, application=application)
    bot = FakeBot(error=failure)

    with pytest.raises(RuntimeError) as error:
        asyncio.run(_handler(application).callback({"update": "send"}, FakeContext(bot)))

    assert error.value is failure
    assert len(runtime.calls) == 1
    assert bot.calls == [(42, "Safe response")]


def test_each_update_uses_an_isolated_buffer():
    def behavior(update, sender):
        sender(update["chat_id"], update["message"])

    runtime = FakeRuntime(behavior)
    application = FakeApplication()
    _run_runner(runtime=runtime, application=application)
    bot = FakeBot()
    handler = _handler(application)

    asyncio.run(handler.callback({"chat_id": 1, "message": "one"}, FakeContext(bot)))
    asyncio.run(handler.callback({"chat_id": 2, "message": "two"}, FakeContext(bot)))

    assert len(runtime.calls) == 2
    assert runtime.calls[0][1] is not runtime.calls[1][1]
    assert bot.calls == [(1, "one"), (2, "two")]


def test_runtime_start_compatibility_uses_an_explicit_runtime_bound_wrapper():
    runtime = FakeRuntime(lambda update, sender: False)
    application = FakeApplication()
    builder, builder_factory, builder_factory_calls = _runner_dependencies(
        application
    )
    sdk_runner = build_runtime_sdk_runner_v4(
        runtime=runtime,
        application_builder_factory=builder_factory,
        message_handler_factory=FakeMessageHandler,
        filters_module=FakeFilters,
    )

    result = sdk_runner(token=TOKEN, handle_update=lambda update: False)

    assert result == "polling-started"
    assert builder_factory_calls == [True]
    assert builder.tokens == [TOKEN]
    assert application.polling_calls == 1
    assert runtime.calls == []
    assert set(inspect.signature(sdk_runner).parameters) == {
        "token",
        "handle_update",
    }


def test_import_has_no_side_effects_or_sdk_requirement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    module = importlib.import_module("engine.telegram_sdk_runner_v4")
    importlib.reload(module)

    assert list(tmp_path.iterdir()) == []


def test_runner_source_has_no_forbidden_phase_boundaries_or_sdk_alternatives():
    module = importlib.import_module("engine.telegram_sdk_runner_v4")
    source = inspect.getsource(module)

    for forbidden in (
        "run_quota_slot_worker_v4",
        "acquire_quota_slot_v4",
        "release_quota_slot_v4",
        "run_master_engine_worker_v4",
        "scan_symbol",
        "scan_market",
        "quota_limit",
        "slot_capacity",
        "quota_state_path",
        "worker_state_path",
        "run_webhook",
        "job_queue",
        "aiogram",
    ):
        assert forbidden not in source
