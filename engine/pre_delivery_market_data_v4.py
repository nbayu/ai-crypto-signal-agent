from datetime import datetime, timezone

import pandas as pd

from engine.binance_client import get_ohlcv


TIMEFRAME_DURATION = pd.Timedelta(hours=4)


def get_closed_ohlcv_for_pre_delivery(
    symbol,
    *,
    now=None,
):
    raw = get_ohlcv(symbol)

    if now is None:
        now = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    now = pd.Timestamp(now)

    timestamps = pd.to_datetime(
        raw["timestamp"]
    )

    closed_mask = (
        timestamps + TIMEFRAME_DURATION
        <= now
    )

    return raw.loc[
        closed_mask
    ].copy()
