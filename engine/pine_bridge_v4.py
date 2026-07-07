from engine.tradingview_watchlist_export_v4 import (
    build_tradingview_symbol,
)


def format_pine_bridge_value(value):
    if isinstance(value, float):
        return format(value, ".15g")

    return str(value)


def build_pine_bridge_artifact(artifact):
    setups = artifact["setups"]

    if artifact["setup_count"] != len(setups):
        raise ValueError(
            "setup_count does not match setups length"
        )

    return {
        "snapshot_type": "v4_pine_bridge",
        "schema_version": 1,
        "source_generated_at": artifact.get(
            "source_generated_at",
            artifact.get("generated_at"),
        ),
        "validated_at": artifact.get("validated_at"),
        "setup_count": len(setups),
        "setups": setups,
    }


def build_pine_bridge_payload(artifact):
    lines = []

    for setup in artifact["setups"]:
        golden_zone = setup["golden_zone"]
        levels = golden_zone["levels"]

        fields = [
            setup["symbol"],
            build_tradingview_symbol(setup["symbol"]),
            golden_zone["direction"],
            golden_zone["swing_low_at"],
            golden_zone["swing_high_at"],
            golden_zone["swing_low"],
            golden_zone["swing_high"],
            levels["0.0"],
            levels["0.5"],
            levels["0.618"],
            levels["0.786"],
            levels["1.0"],
            levels["-0.27"],
        ]

        lines.append(
            "|".join(
                format_pine_bridge_value(value)
                for value in fields
            )
        )

    return "\n".join(lines)


def build_pine_bridge_delivery_payload(artifact):
    payload = build_pine_bridge_payload(artifact)

    return "~".join(payload.splitlines())
