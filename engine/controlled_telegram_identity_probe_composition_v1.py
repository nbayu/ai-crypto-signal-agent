"""Bounded composition for one controlled Telegram identity probe."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from engine.bounded_telegram_sdk_identity_adapter_v1 import (
    BoundedTelegramSdkIdentityProbeV1,
)
from engine.controlled_telegram_identity_probe_v1 import (
    ControlledTelegramIdentityProbeResultV1,
    run_controlled_telegram_identity_probe,
)


@dataclass(frozen=True, slots=True)
class ControlledTelegramIdentityProbeCompositionV1:
    """Forward caller authority to the bounded executor exactly once."""

    _adapter: Callable[..., bool] = field(
        default_factory=BoundedTelegramSdkIdentityProbeV1,
        repr=False,
        compare=False,
    )

    def __call__(
        self,
        *,
        authorization,
        credential_metadata,
        credential_resolver,
        probed_at,
    ) -> ControlledTelegramIdentityProbeResultV1:
        return run_controlled_telegram_identity_probe(
            authorization=authorization,
            credential_metadata=credential_metadata,
            credential_resolver=credential_resolver,
            telegram_identity_probe=self._adapter,
            probed_at=probed_at,
        )
