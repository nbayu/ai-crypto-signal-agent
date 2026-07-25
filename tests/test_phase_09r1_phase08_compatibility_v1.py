import json
import pytest
from pathlib import Path
from engine.master_engine_v4 import run_master_engine_v4
from datetime import datetime

def test_canonical_entrypoint_resolves():
    import engine.run_validated_dry_v4
    assert hasattr(engine.run_validated_dry_v4, "main")

def test_characterize_phase08_master_engine_path(tmp_path):
    def fake_scanner():
        return [
            {
                "symbol": "BTC/USDT:USDT",
                "score": 95.0,
                "reference_price": 50000.0,
                "reference_candle_at": "2026-07-16T12:00:00Z",
                "golden_zone": {
                        "min": 49000.0, 
                        "max": 49500.0, 
                        "direction": "BULLISH",
                        "swing_low_at": "2026-07-15T12:00:00Z",
                        "swing_high_at": "2026-07-15T13:00:00Z",
                        "swing_low": 48000.0,
                        "swing_high": 50000.0,
                        "levels": {
                            "0.0": 50000.0,
                            "0.5": 49000.0,
                            "0.618": 48764.0,
                            "0.786": 48428.0,
                            "1.0": 48000.0,
                            "-0.27": 50540.0
                        },
                        "entry_zone": {"price_low": 49000.0, "price_high": 49500.0},
                        "take_profit": {"price": 52000.0},
                        "stop_loss": {"price": 48000.0}
                    },
                "side": "LONG",
                "entry_zone": {"min": 49000.0, "max": 49500.0},
                "stop_loss": 48000.0,
                "take_profit": {"tp1": 52000.0},
                "valid_until": "2026-07-17T12:00:00Z",
                "setup_id": "test-123",
                "generated_at": "2026-07-16T12:00:00Z",
                "trend": "UPTREND",
                "bos": True,
                "choch": False,
                "volume_ratio": 1.5,
                "volume_v2_status": "OK"
            }
        ]
        
    def fake_validator(candidates):
        return {
            "content": json.dumps({
                "validations": [
                    {
                        "symbol": "BTC/USDT:USDT",
                        "action": "APPROVE",
                        "status": "CLEAR",
                        "false_breakout_risk": "LOW",
                        "confluence": "STRONG",
                        "reason_code": "ALIGNED"
                    }
                ]
            }),
            "usage": {"total_tokens": 100}
        }
        
    def fake_closed_candle_provider(symbol):
        import pandas as pd
        df = pd.DataFrame([
            {"close": 50000.0, "high": 51000.0, "low": 49000.0, "timestamp": "2026-07-16T12:00:00Z"}
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def fake_snapshot_saver(out, *, directory=None, now=None):
        path = tmp_path / "snapshot.json"
        path.write_text(json.dumps(out))
        return path

    def fake_outcome_saver(top5):
        path = tmp_path / "outcome.json"
        path.write_text(json.dumps(top5))
        return path

    def fake_watchlist_saver(top5):
        path = tmp_path / "watchlist.json"
        path.write_text(json.dumps({
            "setups": top5,
            "setup_count": len(top5),
            "generated_at": "2026-07-16T12:00:00Z"
        }))
        return path

    from engine.pre_delivery_flow_v4 import run_pre_delivery_flow

    def fake_pre_delivery_runner(source_path, tv_path, *, closed_candle_provider, validated_at):
        return run_pre_delivery_flow(
            source_path, tv_path,
            closed_candle_provider=closed_candle_provider,
            validated_at=validated_at,
            delivery_artifact_saver=lambda art: (tmp_path / "delivery.json").write_text(json.dumps(art)) or (tmp_path / "delivery.json"),
            tradingview_exporter=lambda src, dst: tmp_path / "tv.txt",
            pine_delivery_saver=lambda art, pld: (tmp_path / "pine_art.json", tmp_path / "pine_pld.json")
        )

    def fake_production_evidence_saver(**kwargs):
        path = tmp_path / "manifest.json"
        # kwargs contain Paths, convert to str
        serializable = {k: str(v) for k, v in kwargs.items()}
        path.write_text(json.dumps(serializable))
        return path

    from engine.validated_pipeline_v4 import run_validated_pipeline_v4
    def fake_pipeline(results):
        return run_validated_pipeline_v4(
            results, 
            validator=fake_validator, 
            oi_provider=lambda s: {"oi_change_pct": 5.0, "data_status": "OK"}
        )

    run_out = run_master_engine_v4(
        scanner=fake_scanner,
        pipeline=fake_pipeline,
        snapshot_saver=fake_snapshot_saver,
        outcome_saver=fake_outcome_saver,
        watchlist_saver=fake_watchlist_saver,
        pre_delivery_runner=fake_pre_delivery_runner,
        closed_candle_provider=fake_closed_candle_provider,
        production_evidence_saver=fake_production_evidence_saver,
        now_provider=lambda: datetime(2026, 7, 16, 12, 0, 0)
    )

    assert "out" in run_out
    assert len(run_out["out"]["final_top5"]) == 1
    
    # 5. deterministic score is preserved
    assert run_out["out"]["final_top5"][0]["python_score"] == 95.0

    # 8. lifecycle behavior is captured
    delivery_artifact = json.loads((tmp_path / "delivery.json").read_text())
    assert len(delivery_artifact["evaluations"]) == 1
    assert "lifecycle" in delivery_artifact["evaluations"][0]

    # 9. current publication path is absent or manual-only
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "tradingview_watchlist_path" in manifest

    # 10. Phase 09 service is now reachable
    import sys
    assert "engine.production_signal_service_v1" in sys.modules

    # 11. no Phase 10-12 module is imported
    assert "engine.news_intelligence" not in sys.modules
    assert "engine.controlled_production_signal_cycle_v1" not in sys.modules

    # 6 & 7. Quota and Slot behavior is captured (Absent in production path)
    with pytest.raises(KeyError):
        _ = run_out["quota"]
