"""Synchronous, SDK-free transport adapter for the Phase 05 application."""

from engine.telegram_application_v4 import TelegramCommandRequest


SAFE_INTERNAL_ERROR_MESSAGE = "Request could not be completed."


class TelegramTransportV4:
    def __init__(self, *, application, sender, bot_username=None):
        self._application = application
        self._sender = sender
        self._bot_username = bot_username

    def handle_update(self, update):
        extracted = self._extract_request(update)
        if extracted is None:
            return False

        request, chat_id = extracted
        try:
            response = self._application.dispatch(request)
        except Exception:
            self._sender(chat_id, SAFE_INTERNAL_ERROR_MESSAGE)
            return True

        message = getattr(response, "message", None)
        if not isinstance(message, str):
            self._sender(chat_id, SAFE_INTERNAL_ERROR_MESSAGE)
            return True

        self._sender(chat_id, message)
        return True

    def _extract_request(self, update):
        message = self._field(update, "message")
        if message is None:
            return None

        user = self._field(message, "from_user")
        chat = self._field(message, "chat")
        text = self._field(message, "text")
        if user is None or chat is None or not isinstance(text, str):
            return None
        if not text or not text.startswith("/"):
            return None

        telegram_user_id = self._field(user, "id")
        chat_id = self._field(chat, "id")
        if not self._is_valid_user_id(telegram_user_id):
            return None
        if type(chat_id) is not int:
            return None

        parsed = self._parse_command(text)
        if parsed is None:
            return None
        command, arguments = parsed
        return (
            TelegramCommandRequest(
                command=command,
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                arguments=arguments,
            ),
            chat_id,
        )

    def _parse_command(self, text):
        parts = text.split()
        if not parts:
            return None

        command_token = parts[0]
        command, separator, suffix = command_token.partition("@")
        if separator:
            if suffix != self._bot_username:
                return None
        return command, tuple(parts[1:])

    @staticmethod
    def _field(value, name):
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @staticmethod
    def _is_valid_user_id(value):
        return type(value) is int and value > 0
