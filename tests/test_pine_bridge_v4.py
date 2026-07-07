from engine.pine_bridge_v4 import (
    build_pine_bridge_payload,
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
        "SUN/USDT:USDT|BULLISH|"
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
