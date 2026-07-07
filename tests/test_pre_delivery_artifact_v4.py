import json

import pandas as pd

import engine.pre_delivery_artifact_v4 as artifact_module
from engine.pre_delivery_artifact_v4 import (
    save_pre_delivery_artifact,
)


def make_artifact():
    return {
        "source_generated_at": "2026-07-01T12:00:00",
        "validated_at": "2026-07-02T00:00:00",
        "source_setup_count": 2,
        "eligible_setup_count": 1,
        "setups": [
            {
                "rank": 2,
                "symbol": "BBB/USDT:USDT",
            },
        ],
        "evaluations": [
            {
                "symbol": "AAA/USDT:USDT",
                "lifecycle": {
                    "state": "TP_HIT",
                    "resolved_at": pd.Timestamp(
                        "2026-07-01T20:00:00"
                    ),
                },
                "supersession": {
                    "state": "CURRENT",
                    "superseded": False,
                },
                "delivery_eligible": False,
                "rejection_reasons": [
                    "TP_HIT",
                ],
            },
            {
                "symbol": "BBB/USDT:USDT",
                "lifecycle": {
                    "state": "ACTIVE",
                    "resolved_at": None,
                },
                "supersession": {
                    "state": "CURRENT",
                    "superseded": False,
                },
                "delivery_eligible": True,
                "rejection_reasons": [],
            },
        ],
    }


def test_save_writes_latest_delivery_artifact(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        artifact_module,
        "PRE_DELIVERY_DIRECTORY",
        tmp_path,
    )

    artifact = make_artifact()

    path = save_pre_delivery_artifact(artifact)

    assert path == tmp_path / "latest.json"
    assert path.exists()

    saved = json.loads(path.read_text())

    assert saved["source_setup_count"] == 2
    assert saved["eligible_setup_count"] == 1
    assert saved["setups"][0]["rank"] == 2
    assert saved["setups"][0]["symbol"] == (
        "BBB/USDT:USDT"
    )


def test_save_serializes_nested_timestamps(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        artifact_module,
        "PRE_DELIVERY_DIRECTORY",
        tmp_path,
    )

    path = save_pre_delivery_artifact(
        make_artifact()
    )

    saved = json.loads(path.read_text())

    assert (
        saved["evaluations"][0]
        ["lifecycle"]["resolved_at"]
        == "2026-07-01T20:00:00"
    )


def test_save_does_not_mutate_artifact(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        artifact_module,
        "PRE_DELIVERY_DIRECTORY",
        tmp_path,
    )

    artifact = make_artifact()
    original_timestamp = (
        artifact["evaluations"][0]
        ["lifecycle"]["resolved_at"]
    )

    save_pre_delivery_artifact(artifact)

    assert (
        artifact["evaluations"][0]
        ["lifecycle"]["resolved_at"]
        is original_timestamp
    )
