import json
from pathlib import Path

from engine.pre_delivery_artifact_v4 import (
    save_pre_delivery_artifact,
)
from engine.pre_delivery_validator_v4 import (
    build_pre_delivery_artifact,
)
from engine.pine_bridge_v4 import (
    build_pine_bridge_artifact,
    build_pine_bridge_delivery_payload,
)
from engine.pine_delivery_artifact_v4 import (
    save_pine_delivery_artifact,
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
    delivery_artifact_saver=None,
    tradingview_exporter=None,
    pine_delivery_saver=None,
):
    source_path = Path(source_path)

    resolved_delivery_artifact_saver = (
        save_pre_delivery_artifact
        if delivery_artifact_saver is None
        else delivery_artifact_saver
    )
    resolved_tradingview_exporter = (
        export_tradingview_watchlist
        if tradingview_exporter is None
        else tradingview_exporter
    )
    resolved_pine_delivery_saver = (
        save_pine_delivery_artifact
        if pine_delivery_saver is None
        else pine_delivery_saver
    )

    source_artifact = json.loads(
        source_path.read_text()
    )

    delivery_artifact = build_pre_delivery_artifact(
        source_artifact,
        closed_candle_provider=closed_candle_provider,
        validated_at=validated_at,
    )

    delivery_artifact_path = (
        resolved_delivery_artifact_saver(
            delivery_artifact
        )
    )

    tradingview_watchlist_path = (
        resolved_tradingview_exporter(
            delivery_artifact_path,
            tradingview_output_path,
        )
    )

    pine_bridge_artifact = (
        build_pine_bridge_artifact(
            delivery_artifact
        )
    )
    pine_delivery_payload = (
        build_pine_bridge_delivery_payload(
            pine_bridge_artifact
        )
    )
    (
        pine_bridge_artifact_path,
        pine_delivery_payload_path,
    ) = resolved_pine_delivery_saver(
        pine_bridge_artifact,
        pine_delivery_payload,
    )

    return {
        "delivery_artifact_path": (
            delivery_artifact_path
        ),
        "tradingview_watchlist_path": (
            tradingview_watchlist_path
        ),
        "pine_bridge_artifact_path": (
            pine_bridge_artifact_path
        ),
        "pine_delivery_payload_path": (
            pine_delivery_payload_path
        ),
    }
