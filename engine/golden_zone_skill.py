from engine.golden_zone_fibonacci import (
    build_golden_zone_fibonacci,
)
from engine.golden_zone_swing_resolver import (
    resolve_golden_zone_swing_pair,
)


def build_golden_zone_skill(
    closed_df,
    trend,
):
    swing_pair = resolve_golden_zone_swing_pair(
        closed_df,
        trend,
    )

    if swing_pair is None:
        return None

    fibonacci = build_golden_zone_fibonacci(
        swing_low=swing_pair["swing_low"],
        swing_high=swing_pair["swing_high"],
        direction=swing_pair["direction"],
    )

    return {
        "direction": fibonacci["direction"],
        "swing_low_index": swing_pair["swing_low_index"],
        "swing_high_index": swing_pair["swing_high_index"],
        "swing_low": fibonacci["swing_low"],
        "swing_high": fibonacci["swing_high"],
        "levels": fibonacci["levels"],
        "entry_zone": fibonacci["entry_zone"],
        "take_profit": fibonacci["take_profit"],
        "stop_loss": fibonacci["stop_loss"],
    }
