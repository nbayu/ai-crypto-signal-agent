"""One-shot synchronous bridge for a bounded Telegram SDK identity check."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import math
from typing import Callable


_DEFAULT_TIMEOUT_SECONDS = 5.0
_DEFAULT_POOL_TIMEOUT_SECONDS = 1.0


def _production_factory(
    *,
    token: str,
    timeout_seconds: float | int,
    pool_timeout_seconds: float | int,
) -> object:
    """Build the one SDK context manager only when the production path is invoked."""
    from telegram import Bot
    from telegram.request import HTTPXRequest

    request = HTTPXRequest(
        connection_pool_size=1,
        read_timeout=timeout_seconds,
        write_timeout=timeout_seconds,
        connect_timeout=timeout_seconds,
        pool_timeout=pool_timeout_seconds,
    )
    return Bot(token=token, request=request)


def _valid_timeout(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and value > 0
    except OverflowError:
        return False


@dataclass(frozen=True, slots=True)
class BoundedTelegramSdkIdentityProbeV1:
    """A token-only, bounded callable compatible with the controlled executor."""

    timeout_seconds: float | int = _DEFAULT_TIMEOUT_SECONDS
    pool_timeout_seconds: float | int = _DEFAULT_POOL_TIMEOUT_SECONDS
    _factory: Callable[..., object] = field(
        default=_production_factory,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not _valid_timeout(self.timeout_seconds):
            raise ValueError("INVALID_TIMEOUT")
        if not _valid_timeout(self.pool_timeout_seconds):
            raise ValueError("INVALID_TIMEOUT")
        if not callable(self._factory):
            raise ValueError("INVALID_FACTORY")

    def __call__(self, *, token: object) -> bool:
        if type(token) is not str or not token.strip():
            return False
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        except Exception:
            return False
        else:
            return False
        try:
            return asyncio.run(self._lifecycle(token=token)) is True
        except Exception:
            return False

    async def _lifecycle(self, *, token: str) -> bool:
        try:
            session = self._factory(
                token=token,
                timeout_seconds=self.timeout_seconds,
                pool_timeout_seconds=self.pool_timeout_seconds,
            )
            async with session:
                return True
        except Exception:
            return False
