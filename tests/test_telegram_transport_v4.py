import importlib
import inspect
from dataclasses import dataclass

import pytest

from engine.telegram_application_v4 import (
    TelegramApplicationResponse,
    TelegramCommandRequest,
)
from engine.telegram_transport_v4 import TelegramTransportV4


@dataclass
class FakeUser:
    id: object
    username: str = "mutable_username"
    full_name: str = "Mutable Display Name"


@dataclass
class FakeChat:
    id: object
    title: str = "Mutable Chat Title"


@dataclass
class FakeMessage:
    text: object
    from_user: object
    chat: object


@dataclass
class FakeUpdate:
    message: object


class FakeApplication:
    def __init__(self, response=None, error=None):
        self.calls = []
        self.response = response or TelegramApplicationResponse(
            category="INFO",
            command="/start",
            message="Safe application response.",
        )
        self.error = error

    def dispatch(self, request):
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.response


def _update(text="/start", *, user_id=123456, chat_id=-100987654321):
    return FakeUpdate(
        message=FakeMessage(
            text=text,
            from_user=FakeUser(user_id),
            chat=FakeChat(chat_id),
        )
    )


def _transport(application, sender, *, bot_username=None):
    return TelegramTransportV4(
        application=application,
        sender=sender,
        bot_username=bot_username,
    )


@pytest.mark.parametrize(
    ("text", "command", "arguments"),
    [
        ("/start", "/start", ()),
        ("/help", "/help", ()),
        ("/status", "/status", ()),
        ("/scan", "/scan", ()),
        ("/scan BTCUSDT", "/scan", ("BTCUSDT",)),
        ("/help extra", "/help", ("extra",)),
    ],
)
def test_forwards_supported_commands_as_pure_requests_once(
    text, command, arguments
):
    application = FakeApplication()
    sent = []
    transport = _transport(application, lambda chat_id, message: sent.append(
        (chat_id, message)
    ))

    transport.handle_update(_update(text))

    assert application.calls == [
        TelegramCommandRequest(
            command=command,
            telegram_user_id=123456,
            chat_id=-100987654321,
            arguments=arguments,
        )
    ]
    assert sent == [(-100987654321, "Safe application response.")]


def test_identity_uses_only_ids_not_mutable_user_or_chat_fields():
    application = FakeApplication()
    sent = []
    transport = _transport(application, lambda chat_id, message: sent.append(
        (chat_id, message)
    ))
    update = _update("/status")
    update.message.from_user.username = "different_username"
    update.message.from_user.full_name = "Different Display Name"
    update.message.chat.title = "Different Chat Title"

    transport.handle_update(update)

    request = application.calls[0]
    assert request.telegram_user_id == 123456
    assert request.chat_id == -100987654321
    assert sent == [(-100987654321, "Safe application response.")]


def test_matching_bot_username_suffix_is_stripped_before_dispatch():
    application = FakeApplication()
    sent = []
    transport = _transport(
        application,
        lambda chat_id, message: sent.append((chat_id, message)),
        bot_username="configured_bot_name",
    )

    transport.handle_update(_update("/scan@configured_bot_name BTCUSDT"))

    assert application.calls == [
        TelegramCommandRequest(
            command="/scan",
            telegram_user_id=123456,
            chat_id=-100987654321,
            arguments=("BTCUSDT",),
        )
    ]
    assert sent == [(-100987654321, "Safe application response.")]


def test_mismatched_bot_username_suffix_is_ignored_without_dispatch():
    application = FakeApplication()
    sent = []
    transport = _transport(
        application,
        lambda chat_id, message: sent.append((chat_id, message)),
        bot_username="configured_bot_name",
    )

    transport.handle_update(_update("/scan@another_bot"))

    assert application.calls == []
    assert sent == []


@pytest.mark.parametrize(
    "update",
    [
        FakeUpdate(message=None),
        FakeUpdate(message=FakeMessage("/scan", None, FakeChat(1))),
        FakeUpdate(message=FakeMessage("/scan", FakeUser(None), FakeChat(1))),
        FakeUpdate(message=FakeMessage("/scan", FakeUser(1), None)),
        FakeUpdate(message=FakeMessage(None, FakeUser(1), FakeChat(1))),
        FakeUpdate(message=FakeMessage(123, FakeUser(1), FakeChat(1))),
        FakeUpdate(message=FakeMessage("", FakeUser(1), FakeChat(1))),
        FakeUpdate(message=FakeMessage("scan", FakeUser(1), FakeChat(1))),
    ],
)
def test_malformed_updates_are_ignored_without_dispatch_or_send(update):
    application = FakeApplication()
    sent = []
    transport = _transport(application, lambda chat_id, message: sent.append(
        (chat_id, message)
    ))

    transport.handle_update(update)

    assert application.calls == []
    assert sent == []


def test_sender_receives_only_the_safe_application_message_once():
    application = FakeApplication(
        TelegramApplicationResponse(
            category="SCAN_SUCCESS",
            command="/scan",
            message="Scan completed safely.",
            scan={"unsafe": "must not be dumped"},
        )
    )
    sent = []
    transport = _transport(application, lambda chat_id, message: sent.append(
        (chat_id, message)
    ))

    transport.handle_update(_update("/scan"))

    assert len(application.calls) == 1
    assert sent == [(-100987654321, "Scan completed safely.")]


def test_send_failure_propagates_without_reinvoking_application():
    application = FakeApplication()
    send_error = RuntimeError("transport failure: sk-live-secret")
    sender_calls = []

    def sender(chat_id, message):
        sender_calls.append((chat_id, message))
        raise send_error

    transport = _transport(application, sender)

    with pytest.raises(RuntimeError) as exc_info:
        transport.handle_update(_update("/scan"))

    assert exc_info.value is send_error
    assert len(application.calls) == 1
    assert sender_calls == [(-100987654321, "Safe application response.")]


def test_unexpected_application_failure_sends_safe_internal_response_once():
    application = FakeApplication(
        error=RuntimeError("Traceback sk-live-secret /private/secret")
    )
    sent = []
    transport = _transport(application, lambda chat_id, message: sent.append(
        (chat_id, message)
    ))

    transport.handle_update(_update("/scan"))

    assert len(application.calls) == 1
    assert sent == [(-100987654321, "Request could not be completed.")]


def test_module_has_no_forbidden_phase_04_or_scanner_references():
    module = importlib.import_module("engine.telegram_transport_v4")
    source = inspect.getsource(module)

    for name in (
        "run_quota_slot_worker_v4",
        "acquire_quota_slot_v4",
        "release_quota_slot_v4",
        "run_master_engine_worker_v4",
        "scan_symbol",
        "scan_market",
    ):
        assert name not in source


def test_import_is_side_effect_free_in_an_empty_working_directory(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)

    module = importlib.import_module("engine.telegram_transport_v4")
    importlib.reload(module)

    assert list(tmp_path.iterdir()) == []
