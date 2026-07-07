import json
from pathlib import Path

import engine.pre_delivery_flow_v4 as flow_module
from engine.pre_delivery_flow_v4 import (
    run_pre_delivery_flow,
)


def make_source_artifact():
    return {
        "generated_at": "2026-07-01T12:00:00",
        "setup_count": 1,
        "setups": [
            {
                "rank": 1,
                "symbol": "AAA/USDT:USDT",
            },
        ],
    }


def test_flow_builds_saves_and_exports_delivery_artifact(
    tmp_path,
    monkeypatch,
):
    source_path = tmp_path / "raw.json"
    source_path.write_text(
        json.dumps(make_source_artifact())
    )

    delivery_path = tmp_path / "delivery.json"
    tradingview_path = tmp_path / "watchlist.txt"

    calls = []

    expected_delivery = {
        "source_generated_at": "2026-07-01T12:00:00",
        "validated_at": "2026-07-02T00:00:00",
        "source_setup_count": 1,
        "eligible_setup_count": 1,
        "setups": [
            {
                "rank": 1,
                "symbol": "AAA/USDT:USDT",
            },
        ],
        "evaluations": [],
    }

    def fake_build(
        source_artifact,
        *,
        closed_candle_provider,
        validated_at,
    ):
        calls.append((
            "build",
            source_artifact,
            closed_candle_provider,
            validated_at,
        ))
        return expected_delivery

    def fake_save(artifact):
        calls.append(("save", artifact))
        delivery_path.write_text(
            json.dumps(artifact)
        )
        return delivery_path

    def fake_export(source, output):
        calls.append(("export", source, output))
        Path(output).write_text(
            "BINANCE:AAAUSDT.P"
        )
        return Path(output)

    monkeypatch.setattr(
        flow_module,
        "build_pre_delivery_artifact",
        fake_build,
    )
    monkeypatch.setattr(
        flow_module,
        "save_pre_delivery_artifact",
        fake_save,
    )
    monkeypatch.setattr(
        flow_module,
        "export_tradingview_watchlist",
        fake_export,
    )
    monkeypatch.setattr(
        flow_module,
        "build_pine_bridge_artifact",
        lambda artifact: {
            "snapshot_type": "v4_pine_bridge",
            "schema_version": 1,
            "setup_count": 1,
            "setups": artifact["setups"],
        },
    )
    monkeypatch.setattr(
        flow_module,
        "build_pine_bridge_delivery_payload",
        lambda artifact: "pine-payload",
    )
    monkeypatch.setattr(
        flow_module,
        "save_pine_delivery_artifact",
        lambda artifact, payload: (
            tmp_path / "pine_latest.json",
            tmp_path / "pine_payload.txt",
        ),
    )

    provider = object()

    result = run_pre_delivery_flow(
        source_path,
        tradingview_path,
        closed_candle_provider=provider,
        validated_at="2026-07-02T00:00:00",
    )

    assert calls[0] == (
        "build",
        make_source_artifact(),
        provider,
        "2026-07-02T00:00:00",
    )
    assert calls[1] == (
        "save",
        expected_delivery,
    )
    assert calls[2] == (
        "export",
        delivery_path,
        tradingview_path,
    )

    assert result == {
        "delivery_artifact_path": delivery_path,
        "tradingview_watchlist_path": tradingview_path,
        "pine_bridge_artifact_path": (
            tmp_path / "pine_latest.json"
        ),
        "pine_delivery_payload_path": (
            tmp_path / "pine_payload.txt"
        ),
    }


def test_flow_exports_from_delivery_path_not_raw_source(
    tmp_path,
    monkeypatch,
):
    source_path = tmp_path / "raw.json"
    source_path.write_text(
        json.dumps(make_source_artifact())
    )

    delivery_path = tmp_path / "delivery.json"
    exported_sources = []

    monkeypatch.setattr(
        flow_module,
        "build_pre_delivery_artifact",
        lambda source_artifact, **kwargs: {
            "source_generated_at": source_artifact[
                "generated_at"
            ],
            "validated_at": "2026-07-02T00:00:00",
            "source_setup_count": 1,
            "eligible_setup_count": 0,
            "setups": [],
            "evaluations": [],
        },
    )
    monkeypatch.setattr(
        flow_module,
        "save_pre_delivery_artifact",
        lambda artifact: delivery_path,
    )
    monkeypatch.setattr(
        flow_module,
        "export_tradingview_watchlist",
        lambda source, output: (
            exported_sources.append(source)
            or Path(output)
        ),
    )
    monkeypatch.setattr(
        flow_module,
        "build_pine_bridge_artifact",
        lambda artifact: {
            "snapshot_type": "v4_pine_bridge",
            "schema_version": 1,
            "setup_count": 0,
            "setups": [],
        },
    )
    monkeypatch.setattr(
        flow_module,
        "build_pine_bridge_delivery_payload",
        lambda artifact: "",
    )
    monkeypatch.setattr(
        flow_module,
        "save_pine_delivery_artifact",
        lambda artifact, payload: (
            tmp_path / "pine_latest.json",
            tmp_path / "pine_payload.txt",
        ),
    )

    run_pre_delivery_flow(
        source_path,
        tmp_path / "watchlist.txt",
        closed_candle_provider=object(),
        validated_at="2026-07-02T00:00:00",
    )

    assert exported_sources == [
        delivery_path,
    ]
    assert source_path not in exported_sources


def test_flow_builds_and_saves_pine_delivery_artifacts(
    tmp_path,
    monkeypatch,
):
    source_path = tmp_path / "raw.json"
    source_path.write_text(
        json.dumps(make_source_artifact())
    )

    delivery_path = tmp_path / "delivery.json"
    tradingview_path = tmp_path / "watchlist.txt"
    pine_bridge_path = tmp_path / "pine_latest.json"
    pine_payload_path = tmp_path / "pine_payload.txt"

    expected_delivery = {
        "source_generated_at": "2026-07-01T12:00:00",
        "validated_at": "2026-07-02T00:00:00",
        "setup_count": 1,
        "setups": [
            {
                "rank": 1,
                "symbol": "AAA/USDT:USDT",
            },
        ],
    }
    expected_bridge = {
        "snapshot_type": "v4_pine_bridge",
        "schema_version": 1,
        "source_generated_at": "2026-07-01T12:00:00",
        "validated_at": "2026-07-02T00:00:00",
        "setup_count": 1,
        "setups": expected_delivery["setups"],
    }
    expected_payload = "pine-delivery-payload"

    calls = []

    monkeypatch.setattr(
        flow_module,
        "build_pre_delivery_artifact",
        lambda source_artifact, **kwargs: expected_delivery,
    )
    monkeypatch.setattr(
        flow_module,
        "save_pre_delivery_artifact",
        lambda artifact: delivery_path,
    )
    monkeypatch.setattr(
        flow_module,
        "export_tradingview_watchlist",
        lambda source, output: Path(output),
    )

    def fake_build_bridge(artifact):
        calls.append(("build_bridge", artifact))
        return expected_bridge

    def fake_build_payload(artifact):
        calls.append(("build_payload", artifact))
        return expected_payload

    def fake_save_pine(artifact, payload):
        calls.append(("save_pine", artifact, payload))
        return pine_bridge_path, pine_payload_path

    monkeypatch.setattr(
        flow_module,
        "build_pine_bridge_artifact",
        fake_build_bridge,
    )
    monkeypatch.setattr(
        flow_module,
        "build_pine_bridge_delivery_payload",
        fake_build_payload,
    )
    monkeypatch.setattr(
        flow_module,
        "save_pine_delivery_artifact",
        fake_save_pine,
    )

    result = run_pre_delivery_flow(
        source_path,
        tradingview_path,
        closed_candle_provider=object(),
        validated_at="2026-07-02T00:00:00",
    )

    assert calls == [
        ("build_bridge", expected_delivery),
        ("build_payload", expected_bridge),
        (
            "save_pine",
            expected_bridge,
            expected_payload,
        ),
    ]

    assert result["pine_bridge_artifact_path"] == (
        pine_bridge_path
    )
    assert result["pine_delivery_payload_path"] == (
        pine_payload_path
    )
