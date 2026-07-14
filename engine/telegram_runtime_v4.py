"""SDK-free runtime composition for the Phase 05 Telegram interface."""

from dataclasses import dataclass, field

from engine.quota_slot_worker_v4 import run_quota_slot_worker_v4
from engine.telegram_application_v4 import TelegramApplicationV4
from engine.telegram_transport_v4 import TelegramTransportV4


TRUNCATION_MARKER_LENGTH = len("\n[truncated]")


class TelegramRuntimeConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramRuntimeConfig:
    bot_token: str = field(repr=False)
    bot_username: str | None
    quota_limit: int
    slot_capacity: int
    window_id: str
    quota_state_path: str
    worker_state_path: str
    max_response_chars: int


class TelegramRuntimeV4:
    def __init__(self, *, config, application, transport):
        self.config = config
        self.application = application
        self.transport = transport

    def handle_update(self, update):
        return self.transport.handle_update(update)

    def handle_update_with_sender(self, update, sender):
        if not callable(sender):
            raise TypeError("sender must be callable")
        transport = TelegramTransportV4(
            application=self.application,
            sender=sender,
            bot_username=self.config.bot_username,
        )
        return transport.handle_update(update)

    def start(self, sdk_runner):
        return sdk_runner(
            token=self.config.bot_token,
            handle_update=self.handle_update,
        )


def load_telegram_runtime_config(environment):
    config = TelegramRuntimeConfig(
        bot_token=_required_string(environment, "TELEGRAM_BOT_TOKEN"),
        bot_username=_optional_username(environment),
        quota_limit=_positive_integer(environment, "TELEGRAM_QUOTA_LIMIT"),
        slot_capacity=_positive_integer(environment, "TELEGRAM_SLOT_CAPACITY"),
        window_id=_required_string(environment, "TELEGRAM_WINDOW_ID"),
        quota_state_path=_required_string(
            environment,
            "TELEGRAM_QUOTA_STATE_PATH",
        ),
        worker_state_path=_required_string(
            environment,
            "TELEGRAM_WORKER_STATE_PATH",
        ),
        max_response_chars=_positive_integer(
            environment,
            "TELEGRAM_MAX_MESSAGE_LENGTH",
        ),
    )
    _validate_config(config)
    return config


def build_telegram_runtime(
    config,
    *,
    sender,
    worker,
    quota_now_provider,
    reservation_id_provider,
    quota_slot_worker=run_quota_slot_worker_v4,
):
    _validate_config(config)
    application = TelegramApplicationV4(
        window_id_provider=lambda request: config.window_id,
        quota_limit=config.quota_limit,
        slot_capacity=config.slot_capacity,
        quota_state_path=config.quota_state_path,
        worker_state_path=config.worker_state_path,
        quota_now_provider=quota_now_provider,
        reservation_id_provider=reservation_id_provider,
        quota_slot_worker=quota_slot_worker,
        worker=worker,
        max_response_chars=config.max_response_chars,
    )
    transport = TelegramTransportV4(
        application=application,
        sender=sender,
        bot_username=config.bot_username,
    )
    return TelegramRuntimeV4(
        config=config,
        application=application,
        transport=transport,
    )


def _required_string(environment, name):
    value = environment.get(name)
    if not isinstance(value, str) or not value.strip():
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    return value


def _optional_username(environment):
    value = environment.get("TELEGRAM_BOT_USERNAME")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    return value


def _positive_integer(environment, name):
    value = environment.get(name)
    if type(value) is int:
        parsed = value
    elif isinstance(value, str) and value.isdecimal():
        parsed = int(value)
    else:
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if parsed <= 0:
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    return parsed


def _validate_config(config):
    if not isinstance(config, TelegramRuntimeConfig):
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if not isinstance(config.bot_token, str) or not config.bot_token.strip():
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if config.bot_username is not None and (
        not isinstance(config.bot_username, str)
        or not config.bot_username.strip()
    ):
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if type(config.quota_limit) is not int or config.quota_limit <= 0:
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if type(config.slot_capacity) is not int or config.slot_capacity <= 0:
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if not isinstance(config.window_id, str) or not config.window_id.strip():
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if (
        not isinstance(config.quota_state_path, str)
        or not config.quota_state_path.strip()
    ):
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if (
        not isinstance(config.worker_state_path, str)
        or not config.worker_state_path.strip()
    ):
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
    if (
        type(config.max_response_chars) is not int
        or config.max_response_chars <= TRUNCATION_MARKER_LENGTH
    ):
        raise TelegramRuntimeConfigError("Invalid Telegram runtime configuration")
