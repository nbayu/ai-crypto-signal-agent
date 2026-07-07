FIB_LEVELS = (
    -0.27,
    0.0,
    0.5,
    0.618,
    0.786,
    1.0,
)

ENTRY_LEVELS = (
    0.618,
    0.786,
)

TAKE_PROFIT_LEVEL = -0.27
STOP_LOSS_LEVEL = 1.0


def _validate_anchors(swing_low, swing_high):
    swing_low = float(swing_low)
    swing_high = float(swing_high)

    if swing_high <= swing_low:
        raise ValueError(
            "swing_high must be greater than swing_low"
        )

    return swing_low, swing_high


def _level_price(
    swing_low,
    swing_high,
    level,
    direction,
):
    price_range = swing_high - swing_low

    if direction == "BULLISH":
        return swing_high - (price_range * level)

    if direction == "BEARISH":
        return swing_low + (price_range * level)

    raise ValueError(
        f"Unsupported Fibonacci direction: {direction}"
    )


def build_golden_zone_fibonacci(
    swing_low,
    swing_high,
    direction,
):
    swing_low, swing_high = _validate_anchors(
        swing_low,
        swing_high,
    )

    direction = direction.upper()

    levels = {
        str(level): _level_price(
            swing_low,
            swing_high,
            level,
            direction,
        )
        for level in FIB_LEVELS
    }

    entry_prices = [
        levels[str(level)]
        for level in ENTRY_LEVELS
    ]

    return {
        "direction": direction,
        "swing_low": swing_low,
        "swing_high": swing_high,
        "levels": levels,
        "entry_zone": {
            "level_from": ENTRY_LEVELS[0],
            "level_to": ENTRY_LEVELS[1],
            "price_low": min(entry_prices),
            "price_high": max(entry_prices),
        },
        "take_profit": {
            "level": TAKE_PROFIT_LEVEL,
            "price": levels[str(TAKE_PROFIT_LEVEL)],
        },
        "stop_loss": {
            "level": STOP_LOSS_LEVEL,
            "price": levels[str(STOP_LOSS_LEVEL)],
        },
    }
