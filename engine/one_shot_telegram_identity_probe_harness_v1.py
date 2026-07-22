"""Pure one-shot harness for a controlled Telegram identity probe."""
from __future__ import annotations

from engine.controlled_telegram_identity_probe_composition_v1 import (
    ControlledTelegramIdentityProbeCompositionV1,
)
from engine.controlled_telegram_identity_probe_v1 import (
    ControlledTelegramIdentityProbeResultV1,
)


class _OneShotResolverRejected(Exception):
    pass


def run_one_shot_telegram_identity_probe(
    *,
    authorization,
    credential_metadata,
    secret_reader,
    probed_at,
    composition=None,
) -> ControlledTelegramIdentityProbeResultV1:
    """Run one caller-authorized identity probe through one local resolver."""

    reader_called = False

    def resolver(*, credential_name, source_kind):
        nonlocal reader_called
        if (
            credential_name != "telegram_bot_token"
            or source_kind != "INJECTED_SECRET_RESOLVER"
            or reader_called
        ):
            raise _OneShotResolverRejected
        reader_called = True
        return secret_reader()

    composition_instance = (
        ControlledTelegramIdentityProbeCompositionV1()
        if composition is None
        else composition
    )
    return composition_instance(
        authorization=authorization,
        credential_metadata=credential_metadata,
        credential_resolver=resolver,
        probed_at=probed_at,
    )
