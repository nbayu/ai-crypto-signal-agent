"""Thin python-telegram-bot polling bridge for the Phase 05 runtime."""


class _TelegramSdkBridgeError(RuntimeError):
    pass


class _SingleMessageBuffer:
    def __init__(self):
        self._has_message = False
        self.chat_id = None
        self.message = None

    def __call__(self, chat_id, message):
        if self._has_message:
            raise _TelegramSdkBridgeError(
                "Only one outgoing message is permitted per update"
            )
        self._has_message = True
        self.chat_id = chat_id
        self.message = message


def run_telegram_polling_v4(
    *,
    token,
    runtime,
    application_builder_factory=None,
    message_handler_factory=None,
    filters_module=None,
):
    """Build and run the SDK polling loop through the supplied runtime."""
    _validate_token(token)
    (
        application_builder_factory,
        message_handler_factory,
        filters_module,
    ) = _resolve_sdk_dependencies(
        application_builder_factory,
        message_handler_factory,
        filters_module,
    )

    async def handle_sdk_update(update, context):
        sender = _SingleMessageBuffer()
        runtime.handle_update_with_sender(update, sender)
        if sender._has_message:
            await context.bot.send_message(
                chat_id=sender.chat_id,
                text=sender.message,
            )

    builder = application_builder_factory()
    application = builder.token(token).build()
    application.add_handler(
        message_handler_factory(filters_module.COMMAND, handle_sdk_update)
    )
    return application.run_polling()


def build_runtime_sdk_runner_v4(
    *,
    runtime,
    application_builder_factory=None,
    message_handler_factory=None,
    filters_module=None,
):
    """Return a runner compatible with ``TelegramRuntimeV4.start``."""

    def sdk_runner(*, token, handle_update):
        return run_telegram_polling_v4(
            token=token,
            runtime=runtime,
            application_builder_factory=application_builder_factory,
            message_handler_factory=message_handler_factory,
            filters_module=filters_module,
        )

    return sdk_runner


def _validate_token(token):
    if not isinstance(token, str) or not token.strip():
        raise ValueError("A valid Telegram bot token is required")


def _resolve_sdk_dependencies(
    application_builder_factory,
    message_handler_factory,
    filters_module,
):
    if (
        application_builder_factory is not None
        and message_handler_factory is not None
        and filters_module is not None
    ):
        return (
            application_builder_factory,
            message_handler_factory,
            filters_module,
        )

    from telegram.ext import ApplicationBuilder, MessageHandler, filters

    return (
        application_builder_factory or ApplicationBuilder,
        message_handler_factory or MessageHandler,
        filters_module or filters,
    )
