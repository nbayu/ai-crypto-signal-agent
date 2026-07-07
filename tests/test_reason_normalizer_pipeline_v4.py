import json

import pytest

import engine.validated_pipeline_v4 as pipeline_module
from engine.validation_semantic_guard_v4 import (
    SemanticValidationError,
)


SYMBOL = "TEST/USDT:USDT"


def _result():
    return {
        "symbol": SYMBOL,
        "score": 90.0,
        "reference_price": 100.0,
        "reference_candle_at": "2026-07-07T08:00:00",
        "golden_zone": {"direction": "BULLISH"},
    }


def _candidate(*, participation="NEUTRAL"):
    return {
        "symbol": SYMBOL,
        "python_score": 90.0,
        "trend": "UPTREND",
        "bos": True,
        "choch": False,
        "volume_ratio": 1.0,
        "volume_status": "OK",
        "volume_class": "NORMAL",
        "oi_change_pct": 0.0,
        "oi_status": "OK",
        "oi_class": "FLAT",
        "participation": participation,
    }


def _ai_result(
    *,
    status,
    risk,
    confluence,
    reason,
):
    return {
        "content": json.dumps(
            {
                "validations": [
                    {
                        "symbol": SYMBOL,
                        "status": status,
                        "false_breakout_risk": risk,
                        "confluence": confluence,
                        "reason_code": reason,
                    }
                ]
            }
        ),
        "usage": {"total_tokens": 1},
    }


def _patch_pipeline(
    monkeypatch,
    *,
    candidate,
    ai_result,
):
    monkeypatch.setattr(
        pipeline_module,
        "build_validation_payload_v4",
        lambda results: [candidate],
    )

    monkeypatch.setattr(
        pipeline_module,
        "validate_candidates",
        lambda candidates: ai_result,
    )


def test_pipeline_normalizes_impossible_reason_before_guard(
    monkeypatch,
):
    candidate = _candidate()

    _patch_pipeline(
        monkeypatch,
        candidate=candidate,
        ai_result=_ai_result(
            status="CONFLICT",
            risk="MEDIUM",
            confluence="MODERATE",
            reason="BREAKOUT_UNCONFIRMED",
        ),
    )

    out = pipeline_module.run_validated_pipeline_v4(
        [_result()]
    )

    row = out["controlled_top10"][0]

    assert row["ai_validation"]["reason_code"] == (
        "MULTIPLE_CONFLICTS"
    )
    assert row["validation_adjustment"] == -5
    assert row["final_rank_score"] == 85.0


def test_pipeline_keeps_non_reason_conflict_fail_closed(
    monkeypatch,
):
    candidate = _candidate(
        participation="UNKNOWN"
    )

    _patch_pipeline(
        monkeypatch,
        candidate=candidate,
        ai_result=_ai_result(
            status="CLEAR",
            risk="LOW",
            confluence="STRONG",
            reason="ALIGNED",
        ),
    )

    with pytest.raises(SemanticValidationError):
        pipeline_module.run_validated_pipeline_v4(
            [_result()]
        )
