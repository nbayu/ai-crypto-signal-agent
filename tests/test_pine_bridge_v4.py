from engine.pine_bridge_v4 import (
    build_pine_bridge_payload,
)
from engine.tradingview_watchlist_export_v4 import (
    build_tradingview_symbol,
)


def _artifact():
    return {
        "generated_at": "2026-07-07T13:44:02",
        "setup_count": 1,
        "setups": [
            {
                "rank": 1,
                "symbol": "SUN/USDT:USDT",
                "final_rank_score": 89.7,
                "reference_price": 0.018,
                "reference_candle_at": "2026-07-07T04:00:00",
                "golden_zone": {
                    "direction": "BULLISH",
                    "swing_low_at": "2026-07-05T04:00:00",
                    "swing_high_at": "2026-07-05T20:00:00",
                    "swing_low": 0.016879,
                    "swing_high": 0.018093,
                    "levels": {
                        "-0.27": 0.01842078,
                        "0.0": 0.018093,
                        "0.5": 0.017486,
                        "0.618": 0.017342748,
                        "0.786": 0.017138796,
                        "1.0": 0.016879,
                    },
                    "entry_zone": {
                        "price_low": 0.017138796,
                        "price_high": 0.017342748,
                    },
                    "take_profit": {
                        "price": 0.01842078,
                    },
                    "stop_loss": {
                        "price": 0.016879,
                    },
                },
            }
        ],
    }


def test_build_pine_bridge_payload_preserves_scanner_values():
    payload = build_pine_bridge_payload(_artifact())

    assert payload == (
        "SUN/USDT:USDT|BINANCE:SUNUSDT.P|BULLISH|"
        "2026-07-05T04:00:00|"
        "2026-07-05T20:00:00|"
        "0.016879|0.018093|"
        "0.018093|0.017486|"
        "0.017342748|0.017138796|"
        "0.016879|0.01842078"
    )


def test_build_pine_bridge_payload_joins_setups_by_newline():
    artifact = _artifact()
    artifact["setups"].append(
        {
            **artifact["setups"][0],
            "rank": 2,
            "symbol": "HUMA/USDT:USDT",
        }
    )
    artifact["setup_count"] = 2

    payload = build_pine_bridge_payload(artifact)

    assert len(payload.splitlines()) == 2
    assert payload.splitlines()[0].startswith(
        "SUN/USDT:USDT|"
    )
    assert payload.splitlines()[1].startswith(
        "HUMA/USDT:USDT|"
    )


def test_build_pine_bridge_payload_formats_float_noise_compactly():
    artifact = _artifact()
    golden_zone = artifact["setups"][0]["golden_zone"]

    golden_zone["levels"]["-0.27"] = 0.023711509999999998
    golden_zone["levels"]["0.786"] = 0.056532059999999995
    golden_zone["levels"]["1.0"] = 0.26620639999999995

    payload = build_pine_bridge_payload(artifact)

    assert "0.02371151" in payload
    assert "0.05653206" in payload
    assert "0.2662064" in payload

    assert "0.023711509999999998" not in payload
    assert "0.056532059999999995" not in payload
    assert "0.26620639999999995" not in payload


def test_build_pine_bridge_delivery_payload_is_single_line():
    from engine.pine_bridge_v4 import (
        build_pine_bridge_delivery_payload,
    )

    artifact = _artifact()
    artifact["setups"].append(
        {
            **artifact["setups"][0],
            "rank": 2,
            "symbol": "HUMA/USDT:USDT",
        }
    )
    artifact["setup_count"] = 2

    payload = build_pine_bridge_delivery_payload(
        artifact
    )

    assert "\n" not in payload
    assert payload.count("~") == 1

    records = payload.split("~")

    assert len(records) == 2
    assert records[0].startswith(
        "SUN/USDT:USDT|"
    )
    assert records[1].startswith(
        "HUMA/USDT:USDT|"
    )



def test_bridge_uses_existing_tradingview_symbol_contract():
    artifact = _artifact()

    payload = build_pine_bridge_payload(artifact)
    fields = payload.split("|")

    assert fields[0] == "SUN/USDT:USDT"
    assert fields[1] == build_tradingview_symbol(
        "SUN/USDT:USDT"
    )
    assert fields[1] == "BINANCE:SUNUSDT.P"
    assert len(fields) == 13


def test_bridge_artifact_has_explicit_contract_metadata():
    from engine.pine_bridge_v4 import (
        build_pine_bridge_artifact,
    )

    artifact = _artifact()
    artifact["source_generated_at"] = artifact.pop(
        "generated_at"
    )
    artifact["validated_at"] = "2026-07-07T16:55:47"

    bridge = build_pine_bridge_artifact(artifact)

    assert bridge["snapshot_type"] == "v4_pine_bridge"
    assert bridge["schema_version"] == 1
    assert bridge["source_generated_at"] == (
        "2026-07-07T13:44:02"
    )
    assert bridge["validated_at"] == (
        "2026-07-07T16:55:47"
    )
    assert bridge["setup_count"] == 1


def test_bridge_artifact_preserves_original_rank():
    from engine.pine_bridge_v4 import (
        build_pine_bridge_artifact,
    )

    artifact = _artifact()
    artifact["setups"][0]["rank"] = 5

    bridge = build_pine_bridge_artifact(artifact)

    assert bridge["setups"][0]["rank"] == 5
    assert bridge["setups"][0]["symbol"] == (
        "SUN/USDT:USDT"
    )


def test_bridge_artifact_rejects_setup_count_mismatch():
    import pytest

    from engine.pine_bridge_v4 import (
        build_pine_bridge_artifact,
    )

    artifact = _artifact()
    artifact["setup_count"] = 2

    with pytest.raises(
        ValueError,
        match="setup_count does not match setups length",
    ):
        build_pine_bridge_artifact(artifact)


def test_bridge_payload_accepts_bridge_artifact_contract():
    from engine.pine_bridge_v4 import (
        build_pine_bridge_artifact,
        build_pine_bridge_payload,
    )

    artifact = _artifact()
    bridge = build_pine_bridge_artifact(artifact)

    payload = build_pine_bridge_payload(bridge)

    assert payload.startswith(
        "SUN/USDT:USDT|BINANCE:SUNUSDT.P|"
    )
