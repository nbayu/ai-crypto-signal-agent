from engine.market_structure import (
    swing_high,
    swing_low,
)


def resolve_golden_zone_swing_pair(
    df,
    trend,
):
    trend = trend.upper()

    if trend == "SIDEWAYS":
        return None

    high_indices = swing_high(df)
    low_indices = swing_low(df)

    if trend == "UPTREND":
        direction = "BULLISH"

        for high_index in reversed(high_indices):
            prior_lows = [
                low_index
                for low_index in low_indices
                if low_index < high_index
            ]

            if not prior_lows:
                continue

            low_index = prior_lows[-1]

            swing_low_price = float(
                df["low"].iloc[low_index]
            )
            swing_high_price = float(
                df["high"].iloc[high_index]
            )

            if swing_high_price <= swing_low_price:
                continue

            return {
                "direction": direction,
                "swing_low_index": low_index,
                "swing_high_index": high_index,
                "swing_low": swing_low_price,
                "swing_high": swing_high_price,
            }

        return None

    if trend == "DOWNTREND":
        direction = "BEARISH"

        for low_index in reversed(low_indices):
            prior_highs = [
                high_index
                for high_index in high_indices
                if high_index < low_index
            ]

            if not prior_highs:
                continue

            high_index = prior_highs[-1]

            swing_low_price = float(
                df["low"].iloc[low_index]
            )
            swing_high_price = float(
                df["high"].iloc[high_index]
            )

            if swing_high_price <= swing_low_price:
                continue

            return {
                "direction": direction,
                "swing_low_index": low_index,
                "swing_high_index": high_index,
                "swing_low": swing_low_price,
                "swing_high": swing_high_price,
            }

        return None

    raise ValueError(
        f"Unsupported market trend: {trend}"
    )
