import json
from pathlib import Path

from engine.pre_delivery_artifact_v4 import (
    save_pre_delivery_artifact,
)
from engine.pre_delivery_validator_v4 import (
    build_pre_delivery_artifact,
)
from engine.tradingview_watchlist_export_v4 import (
    export_tradingview_watchlist,
)


def run_pre_delivery_flow(
    source_path,
    tradingview_output_path,
    *,
    closed_candle_provider,
    validated_at,
):
    source_path = Path(source_path)

    source_artifact = json.loads(
        source_path.read_text()
    )

    delivery_artifact = build_pre_delivery_artifact(
        source_artifact,
        closed_candle_provider=closed_candle_provider,
        validated_at=validated_at,
    )

    delivery_artifact_path = (
        save_pre_delivery_artifact(
            delivery_artifact
        )
    )

    tradingview_watchlist_path = (
        export_tradingview_watchlist(
            delivery_artifact_path,
            tradingview_output_path,
        )
    )

    return {
        "delivery_artifact_path": (
            delivery_artifact_path
        ),
        "tradingview_watchlist_path": (
            tradingview_watchlist_path
        ),
    }
