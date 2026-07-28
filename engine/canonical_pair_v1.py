"""Single fail-closed canonical pair identity authority."""

from __future__ import annotations

import re
from typing import Any


PAIR_INVALID = "PAIR_INVALID"
_ASSET = re.compile(r"^[A-Z0-9]{2,20}$")
_CONCATENATED_QUOTES = ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH")


class CanonicalPairError(ValueError):
    """Stable rejection for malformed or unsupported pair input."""


def normalize_pair(value: Any) -> str:
    """Normalize case, whitespace, and a matching settlement suffix."""
    if not isinstance(value, str):
        raise CanonicalPairError(PAIR_INVALID)
    compact = re.sub(r"\s+", "", value).upper()
    if not compact:
        raise CanonicalPairError(PAIR_INVALID)
    market, separator, settlement = compact.partition(":")
    if separator and (not settlement or ":" in settlement):
        raise CanonicalPairError(PAIR_INVALID)
    if "/" not in market:
        for quote in _CONCATENATED_QUOTES:
            if market.endswith(quote) and len(market) > len(quote):
                market = f"{market[:-len(quote)]}/{quote}"
                break
    parts = market.split("/")
    if len(parts) != 2 or not all(_ASSET.fullmatch(part) for part in parts):
        raise CanonicalPairError(PAIR_INVALID)
    base, quote = parts
    if base == quote or (separator and settlement != quote):
        raise CanonicalPairError(PAIR_INVALID)
    return f"{base}/{quote}"
