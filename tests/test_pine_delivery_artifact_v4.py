import json

from engine.pine_delivery_artifact_v4 import (
    save_pine_delivery_artifact,
)


def _bridge():
    return {
        "snapshot_type": "v4_pine_bridge",
        "schema_version": 1,
        "source_generated_at": "2026-07-07T16:55:47",
        "validated_at": "2026-07-07T16:55:48",
        "setup_count": 1,
        "setups": [
            {
                "rank": 1,
                "symbol": "AAA/USDT:USDT",
            },
        ],
    }


def test_save_writes_bridge_artifact_and_delivery_payload(
    tmp_path,
):
    bridge_path, payload_path = (
        save_pine_delivery_artifact(
            _bridge(),
            "AAA|BINANCE:AAAUSDT.P|BULLISH",
            directory=tmp_path,
        )
    )

    assert bridge_path == tmp_path / "latest.json"
    assert payload_path == tmp_path / "payload.txt"

    assert json.loads(
        bridge_path.read_text()
    ) == _bridge()

    assert payload_path.read_text() == (
        "AAA|BINANCE:AAAUSDT.P|BULLISH"
    )


def test_save_replaces_previous_operational_delivery(
    tmp_path,
):
    bridge_path, payload_path = (
        save_pine_delivery_artifact(
            _bridge(),
            "first",
            directory=tmp_path,
        )
    )

    updated = _bridge()
    updated["setup_count"] = 0
    updated["setups"] = []

    second_bridge_path, second_payload_path = (
        save_pine_delivery_artifact(
            updated,
            "",
            directory=tmp_path,
        )
    )

    assert second_bridge_path == bridge_path
    assert second_payload_path == payload_path

    assert json.loads(
        bridge_path.read_text()
    ) == updated
    assert payload_path.read_text() == ""


def test_save_does_not_mutate_bridge_artifact(
    tmp_path,
):
    bridge = _bridge()
    before = json.loads(json.dumps(bridge))

    save_pine_delivery_artifact(
        bridge,
        "payload",
        directory=tmp_path,
    )

    assert bridge == before
