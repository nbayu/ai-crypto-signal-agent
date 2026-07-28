from datetime import datetime
from pathlib import Path

from engine.master_engine_v4 import (
    run_master_engine_v4,
    save_validated_snapshot_v4,
)


def test_save_validated_snapshot_v4_preserves_existing_contract(tmp_path):
    out = {
        "controlled_top10": [],
        "final_top5": [],
        "usage": {},
    }

    path = save_validated_snapshot_v4(
        out,
        directory=tmp_path,
        now=datetime(2026, 7, 14, 12, 34, 56),
    )

    assert path == tmp_path / "validated_v4_20260714_123456.json"
    assert path.read_text() == (
        '{\n'
        '  "controlled_top10": [],\n'
        '  "final_top5": [],\n'
        '  "usage": {}\n'
        '}'
    )


def test_outcome_invocation_identity_and_captured_at_propagate_to_outcome_saver():
    calls = []

    scanner_results = [
        {
            "symbol": "AAA",
            "score": 90,
            "reference_price": 1.23,
            "reference_candle_at": "2026-07-14T00:00:00",
            "golden_zone": None,
        }
    ]

    pipeline_out = {
        "controlled_top10": [],
        "final_top5": [{"symbol": "AAA"}],
        "usage": {"total_tokens": 1},
    }

    def scanner():
        calls.append(("scanner",))
        return scanner_results

    def pipeline(results):
        calls.append(("pipeline", results))
        return pipeline_out

    def snapshot_saver(out, *, now):
        calls.append(("snapshot_saver", out, now))
        return Path("validated.json")

    def outcome_saver(
        final_top5,
        *,
        outcome_invocation_id,
        captured_at,
    ):
        calls.append((
            "outcome_saver",
            final_top5,
            outcome_invocation_id,
            captured_at,
        ))
        return Path("outcome.json")

    def watchlist_saver(final_top5):
        calls.append(("watchlist_saver", final_top5))
        return Path("raw_top5.json")

    def closed_candle_provider(symbol):
        calls.append(("closed_candle_provider", symbol))
        return []

    def pre_delivery_runner(
        source_path,
        tradingview_output_path,
        *,
        closed_candle_provider,
        validated_at,
    ):
        calls.append(
            (
                "pre_delivery_runner",
                source_path,
                tradingview_output_path,
                closed_candle_provider,
                validated_at,
            )
        )
        return {
            "delivery_artifact_path": Path("pre_delivery.json"),
            "tradingview_watchlist_path": Path(
                "tradingview_watchlist.txt"
            ),
            "pine_bridge_artifact_path": Path("pine_bridge.json"),
            "pine_delivery_payload_path": Path("payload.txt"),
        }

    def production_evidence_saver(**kwargs):
        calls.append(("production_evidence_saver", kwargs))
        return Path("manifest.json")

    def now_provider():
        return datetime(2026, 7, 14, 12, 0, 0)

    result = run_master_engine_v4(
        outcome_invocation_id="a" * 32,
        scanner=scanner,
        pipeline=pipeline,
        snapshot_saver=snapshot_saver,
        outcome_saver=outcome_saver,
        watchlist_saver=watchlist_saver,
        pre_delivery_runner=pre_delivery_runner,
        closed_candle_provider=closed_candle_provider,
        production_evidence_saver=production_evidence_saver,
        now_provider=now_provider,
    )

    assert result == {
        "results": scanner_results,
        "out": pipeline_out,
        "snapshot_path": Path("validated.json"),
        "outcome_path": Path("outcome.json"),
        "watchlist_path": Path("raw_top5.json"),
        "delivery_out": {
            "delivery_artifact_path": Path("pre_delivery.json"),
            "tradingview_watchlist_path": Path(
                "tradingview_watchlist.txt"
            ),
            "pine_bridge_artifact_path": Path("pine_bridge.json"),
            "pine_delivery_payload_path": Path("payload.txt"),
        },
        "evidence_path": Path("manifest.json"),
    }

    assert calls == [
        ("scanner",),
        ("pipeline", scanner_results),
        (
            "snapshot_saver",
            pipeline_out,
            datetime(2026, 7, 14, 12, 0, 0),
        ),
        (
            "outcome_saver",
            pipeline_out["final_top5"],
            "a" * 32,
            "2026-07-14T12:00:00",
        ),
        ("watchlist_saver", pipeline_out["final_top5"]),
        (
            "pre_delivery_runner",
            Path("raw_top5.json"),
            "data/top5_watchlist_v4/tradingview_watchlist.txt",
            closed_candle_provider,
            "2026-07-14T12:00:00",
        ),
        (
            "production_evidence_saver",
            {
                "created_at": "2026-07-14T12:00:00",
                "validated_snapshot_path": Path("validated.json"),
                "outcome_entry_path": Path("outcome.json"),
                "raw_top5_path": Path("raw_top5.json"),
                "pre_delivery_path": Path("pre_delivery.json"),
                "tradingview_watchlist_path": Path(
                    "tradingview_watchlist.txt"
                ),
            },
        ),
    ]


def test_owner_gate_is_wired_before_production_service():
    source = (Path(__file__).parents[1] / "engine" / "master_engine_v4.py").read_text()
    assert source.index("evaluate_candidate(") < source.index("run_production_signal_service_v1(")
