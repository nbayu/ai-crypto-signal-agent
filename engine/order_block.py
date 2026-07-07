import math
from engine.smc import detect_order_blocks

def distance_to_order_block(df):
    current_price = float(df["close"].iloc[-1])

    obs = detect_order_blocks(df)

    if not obs:
        return 999999.0

    nearest = min(
        obs,
        key=lambda ob: min(
            abs(current_price - ob["high"]),
            abs(current_price - ob["low"])
        )
    )

    if current_price > nearest["high"]:
        return current_price - nearest["high"]

    elif current_price < nearest["low"]:
        return nearest["low"] - current_price

    else:
        return 0.0
