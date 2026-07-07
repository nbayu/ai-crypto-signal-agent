import json
from datetime import datetime, timezone

import engine.forward_outcome_resolver_v4 as resolver


def test_fresh_entry_without_eligible_horizon_persists_initial_resolution(
    tmp_path,
    monkeypatch,
):
    entry_path = (
        tmp_path / "outcome_entry_v4_test.json"
    )

    entry = {
        "snapshot_type": "v4_outcome_tracker_entry",
        "schema_version": 1,
        "captured_at": "2026-07-07T18:02:43.624709",
        "candidates": [
            {
                "symbol": "TEST/USDT:USDT",
                "reference_price": 100.0,
                "reference_candle_at": "2026-07-07T12:00:00",
                "python_score": 90.0,
                "validation_adjustment": 0,
                "final_rank_score": 90.0,
                "trend": "UPTREND",
                "bos": True,
                "choch": False,
                "volume_ratio": 2.0,
                "volume_class": "STRONG",
                "oi_change_pct": 1.0,
                "oi_class": "STRONG",
                "participation": "STRONG",
                "ai_validation": {
                    "status": "CLEAR",
                    "false_breakout_risk": "LOW",
                    "confluence": "STRONG",
                    "reason_code": "ALIGNED",
                },
            }
        ],
    }

    entry_path.write_text(
        json.dumps(entry, indent=2)
    )

    def fail_if_market_data_is_requested(*args, **kwargs):
        raise AssertionError(
            "Market data must not be requested "
            "before a horizon is eligible"
        )

    monkeypatch.setattr(
        resolver,
        "get_ohlcv",
        fail_if_market_data_is_requested,
    )

    result = resolver.resolve_entry_artifact(
        entry_path,
        now_utc=datetime(
            2026,
            7,
            7,
            15,
            0,
            tzinfo=timezone.utc,
        ),
    )

    resolution_path = tmp_path / (
        "outcome_resolved_v4_test.json"
    )

    assert result == {
        "entry_path": str(entry_path),
        "resolution_path": str(resolution_path),
        "changed": False,
        "resolved_horizons_added": 0,
    }

    assert resolution_path.exists()

    resolved = json.loads(
        resolution_path.read_text()
    )

    assert resolved == (
        resolver.build_initial_resolution_state(
            entry_path,
            entry,
        )
    )
