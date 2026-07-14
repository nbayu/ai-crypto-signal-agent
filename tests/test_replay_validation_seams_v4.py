import json
import socket

import pytest
import requests

import engine.deepseek_validator_v4 as deepseek_module
import engine.validated_pipeline_v4 as pipeline_module
import engine.validation_payload_v2 as payload_module
from engine.validation_semantic_guard_v4 import (
    SemanticValidationError,
)


SYMBOL_A = "AAA/USDT:USDT"
SYMBOL_B = "BBB/USDT:USDT"


def _golden_zone(*, direction="BULLISH"):
    return {
        "direction": direction,
        "swing_low_index": 10,
        "swing_high_index": 20,
        "swing_low_at": "2026-07-14T00:00:00+00:00",
        "swing_high_at": "2026-07-14T01:00:00+00:00",
        "swing_low": 95.0,
        "swing_high": 110.0,
        "levels": {
            "0.5": 102.5,
            "0.618": 100.73,
            "0.705": 99.425,
        },
        "entry_zone": {
            "low": 99.425,
            "high": 102.5,
        },
        "take_profit": {
            "price": 110.0,
        },
        "stop_loss": {
            "price": 95.0,
        },
    }


def _scanner_row(
    symbol=SYMBOL_A,
    *,
    score=90.0,
    volume_ratio=1.6,
    volume_status="OK",
):
    return {
        "symbol": symbol,
        "score": score,
        "direction": "BULLISH",
        "entry": 101.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "reference_price": 100.0,
        "reference_candle_at": "2026-07-14T02:00:00+00:00",
        "golden_zone": _golden_zone(),
        "trend": "UPTREND",
        "bos": True,
        "choch": False,
        "volume_ratio": volume_ratio,
        "volume_v2_status": volume_status,
    }


def _oi_metrics(
    *,
    change_pct=0.5,
    score=62.5,
    status="OK",
):
    return {
        "current_oi": 1005.0,
        "previous_oi": 1000.0,
        "oi_change_pct": change_pct,
        "oi_score": score,
        "data_status": status,
    }


def _validation(
    symbol,
    *,
    status="CLEAR",
    risk="LOW",
    confluence="STRONG",
    reason="ALIGNED",
):
    return {
        "symbol": symbol,
        "status": status,
        "false_breakout_risk": risk,
        "confluence": confluence,
        "reason_code": reason,
    }


def _validator_result(validations):
    return {
        "content": json.dumps(
            {"validations": validations},
            sort_keys=True,
            separators=(",", ":"),
        ),
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
            "cache_hit_tokens": 4,
            "cache_miss_tokens": 16,
        },
    }


def _provider_from(mapping, calls):
    def provider(symbol):
        calls.append(symbol)
        return mapping[symbol]

    return provider


def _fail_if_called(name):
    def fail(*args, **kwargs):
        raise AssertionError(f"unexpected live dependency: {name}")

    return fail


def test_candidate_accepts_injected_oi_and_uses_real_classification():
    calls = []
    provider = _provider_from(
        {SYMBOL_A: _oi_metrics()},
        calls,
    )

    candidate = payload_module.build_validation_candidate_v2(
        _scanner_row(),
        oi_provider=provider,
    )

    assert calls == [SYMBOL_A]
    assert candidate["symbol"] == SYMBOL_A
    assert candidate["volume_class"] == "STRONG"
    assert candidate["oi_class"] == "STRONG"
    assert candidate["participation"] == "STRONG"
    assert candidate["oi_change_pct"] == 0.5
    assert candidate["oi_status"] == "OK"


def test_candidate_provider_exception_propagates_unchanged():
    failure = RuntimeError("recorded OI unavailable")

    def provider(symbol):
        assert symbol == SYMBOL_A
        raise failure

    with pytest.raises(RuntimeError) as exc_info:
        payload_module.build_validation_candidate_v2(
            _scanner_row(),
            oi_provider=provider,
        )

    assert exc_info.value is failure


def test_candidate_malformed_provider_result_keeps_downstream_failure():
    def malformed_provider(symbol):
        assert symbol == SYMBOL_A
        return {"oi_change_pct": 0.5}

    with pytest.raises(KeyError) as exc_info:
        payload_module.build_validation_candidate_v2(
            _scanner_row(),
            oi_provider=malformed_provider,
        )

    assert exc_info.value.args == ("data_status",)


def test_payload_passes_oi_provider_once_per_ranked_candidate():
    calls = []
    provider = _provider_from(
        {
            SYMBOL_A: _oi_metrics(change_pct=0.5),
            SYMBOL_B: _oi_metrics(change_pct=-0.5, score=37.5),
        },
        calls,
    )
    results = [
        _scanner_row(SYMBOL_B, score=82.0),
        _scanner_row(SYMBOL_A, score=91.0),
    ]

    payload = pipeline_module.build_validation_payload_v4(
        results,
        oi_provider=provider,
    )

    assert calls == [SYMBOL_A, SYMBOL_B]
    assert [row["symbol"] for row in payload] == [SYMBOL_A, SYMBOL_B]
    assert payload[0]["participation"] == "STRONG"
    assert payload[1]["participation"] == "MIXED"


def test_payload_preserves_current_duplicate_row_behavior():
    calls = []
    provider = _provider_from(
        {SYMBOL_A: _oi_metrics()},
        calls,
    )

    payload = pipeline_module.build_validation_payload_v4(
        [
            _scanner_row(SYMBOL_A, score=91.0),
            _scanner_row(SYMBOL_A, score=89.0),
        ],
        oi_provider=provider,
    )

    assert [row["symbol"] for row in payload] == [SYMBOL_A, SYMBOL_A]
    assert calls == [SYMBOL_A, SYMBOL_A]


def test_payload_provider_failure_stops_without_omitting_candidates():
    calls = []
    failure = LookupError("recorded OI fixture failure")

    def provider(symbol):
        calls.append(symbol)
        if symbol == SYMBOL_B:
            raise failure
        return _oi_metrics()

    with pytest.raises(LookupError) as exc_info:
        pipeline_module.build_validation_payload_v4(
            [
                _scanner_row(SYMBOL_A, score=92.0),
                _scanner_row(SYMBOL_B, score=91.0),
                _scanner_row("CCC/USDT:USDT", score=90.0),
            ],
            oi_provider=provider,
        )

    assert exc_info.value is failure
    assert calls == [SYMBOL_A, SYMBOL_B]


def test_payload_malformed_scanner_row_fails_before_provider_call():
    calls = []
    row = _scanner_row()
    del row["score"]

    with pytest.raises(KeyError) as exc_info:
        pipeline_module.build_validation_payload_v4(
            [row],
            oi_provider=lambda symbol: calls.append(symbol),
        )

    assert exc_info.value.args == ("score",)
    assert calls == []


def test_pipeline_injected_validator_receives_real_payload_once():
    oi_calls = []
    validator_calls = []
    oi_provider = _provider_from(
        {SYMBOL_A: _oi_metrics()},
        oi_calls,
    )
    recorded_result = _validator_result([_validation(SYMBOL_A)])

    def validator(candidates):
        validator_calls.append(candidates)
        return recorded_result

    result = pipeline_module.run_validated_pipeline_v4(
        [_scanner_row()],
        validator=validator,
        oi_provider=oi_provider,
    )

    assert oi_calls == [SYMBOL_A]
    assert len(validator_calls) == 1
    assert validator_calls[0][0]["symbol"] == SYMBOL_A
    assert validator_calls[0][0]["participation"] == "STRONG"
    assert result["usage"] == recorded_result["usage"]
    assert result["controlled_top10"][0]["final_rank_score"] == 90.0
    assert result["final_top5"][0]["symbol"] == SYMBOL_A


def test_pipeline_validator_exception_propagates_unchanged():
    failure = RuntimeError("recorded validator unavailable")
    calls = []

    def validator(candidates):
        calls.append(candidates)
        raise failure

    with pytest.raises(RuntimeError) as exc_info:
        pipeline_module.run_validated_pipeline_v4(
            [_scanner_row()],
            validator=validator,
            oi_provider=lambda symbol: _oi_metrics(),
        )

    assert exc_info.value is failure
    assert len(calls) == 1


def test_pipeline_malformed_recorded_validator_content_fails_closed():
    def validator(candidates):
        return {
            "content": "{",
            "usage": {"total_tokens": 0},
        }

    with pytest.raises(ValueError, match="Invalid DeepSeek JSON"):
        pipeline_module.run_validated_pipeline_v4(
            [_scanner_row()],
            validator=validator,
            oi_provider=lambda symbol: _oi_metrics(),
        )


def test_pipeline_runs_real_reason_normalization_and_control():
    def validator(candidates):
        return _validator_result(
            [
                _validation(
                    SYMBOL_A,
                    status="CONFLICT",
                    risk="MEDIUM",
                    confluence="MODERATE",
                    reason="BREAKOUT_UNCONFIRMED",
                )
            ]
        )

    result = pipeline_module.run_validated_pipeline_v4(
        [_scanner_row()],
        validator=validator,
        oi_provider=lambda symbol: _oi_metrics(),
    )

    row = result["controlled_top10"][0]
    assert row["ai_validation"]["reason_code"] == "MULTIPLE_CONFLICTS"
    assert row["validation_adjustment"] == -5
    assert row["final_rank_score"] == 85.0


def test_pipeline_injected_validator_cannot_bypass_semantic_guard():
    def unknown_oi(symbol):
        return _oi_metrics(
            change_pct=None,
            score=None,
            status="API_ERROR",
        )

    def validator(candidates):
        assert candidates[0]["participation"] == "UNKNOWN"
        return _validator_result([_validation(SYMBOL_A)])

    with pytest.raises(SemanticValidationError):
        pipeline_module.run_validated_pipeline_v4(
            [_scanner_row()],
            validator=validator,
            oi_provider=unknown_oi,
        )


def test_pipeline_injected_flow_uses_real_final_ranking():
    validator_calls = []

    def validator(candidates):
        validator_calls.append(candidates)
        return _validator_result(
            [_validation(row["symbol"]) for row in candidates]
        )

    result = pipeline_module.run_validated_pipeline_v4(
        [
            _scanner_row(SYMBOL_B, score=84.0),
            _scanner_row(SYMBOL_A, score=95.0),
        ],
        validator=validator,
        oi_provider=lambda symbol: _oi_metrics(),
    )

    assert len(validator_calls) == 1
    assert [
        row["symbol"] for row in validator_calls[0]
    ] == [SYMBOL_A, SYMBOL_B]
    assert [
        row["symbol"] for row in result["controlled_top10"]
    ] == [SYMBOL_A, SYMBOL_B]
    assert [
        row["symbol"] for row in result["final_top5"]
    ] == [SYMBOL_A, SYMBOL_B]


def test_combined_injection_performs_complete_flow_without_live_access(
    monkeypatch,
):
    monkeypatch.setattr(
        payload_module,
        "open_interest_metrics_v2",
        _fail_if_called("default OI provider"),
    )
    monkeypatch.setattr(
        pipeline_module,
        "validate_candidates",
        _fail_if_called("default validator"),
    )
    monkeypatch.setattr(
        requests,
        "get",
        _fail_if_called("requests.get"),
    )
    monkeypatch.setattr(
        socket,
        "create_connection",
        _fail_if_called("socket.create_connection"),
    )
    monkeypatch.setattr(
        deepseek_module,
        "OpenAI",
        _fail_if_called("OpenAI client"),
    )

    oi_calls = []
    validator_calls = []
    oi_provider = _provider_from(
        {
            SYMBOL_A: _oi_metrics(change_pct=0.5),
            SYMBOL_B: _oi_metrics(change_pct=0.4),
        },
        oi_calls,
    )

    def validator(candidates):
        validator_calls.append(candidates)
        return _validator_result(
            [_validation(row["symbol"]) for row in candidates]
        )

    result = pipeline_module.run_validated_pipeline_v4(
        [
            _scanner_row(SYMBOL_A, score=94.0),
            _scanner_row(SYMBOL_B, score=92.0),
        ],
        validator=validator,
        oi_provider=oi_provider,
    )

    assert oi_calls == [SYMBOL_A, SYMBOL_B]
    assert len(validator_calls) == 1
    assert all(
        row["participation"] == "STRONG"
        for row in validator_calls[0]
    )
    assert len(result["controlled_top10"]) == 2
    assert len(result["final_top5"]) == 2


def test_candidate_default_provider_is_resolved_from_module_at_call_time(
    monkeypatch,
):
    calls = []
    default_provider = _provider_from(
        {SYMBOL_A: _oi_metrics()},
        calls,
    )
    monkeypatch.setattr(
        payload_module,
        "open_interest_metrics_v2",
        default_provider,
    )

    candidate = payload_module.build_validation_candidate_v2(
        _scanner_row()
    )

    assert calls == [SYMBOL_A]
    assert candidate["participation"] == "STRONG"


def test_payload_default_candidate_builder_is_resolved_at_call_time(
    monkeypatch,
):
    calls = []

    def candidate_builder(row):
        calls.append(row["symbol"])
        return {"symbol": row["symbol"], "python_score": row["score"]}

    monkeypatch.setattr(
        pipeline_module,
        "build_validation_candidate_v2",
        candidate_builder,
    )

    payload = pipeline_module.build_validation_payload_v4(
        [
            _scanner_row(SYMBOL_B, score=80.0),
            _scanner_row(SYMBOL_A, score=90.0),
        ]
    )

    assert calls == [SYMBOL_A, SYMBOL_B]
    assert [row["symbol"] for row in payload] == [SYMBOL_A, SYMBOL_B]


def test_pipeline_default_validator_is_resolved_at_call_time(monkeypatch):
    candidate = {
        "symbol": SYMBOL_A,
        "python_score": 90.0,
        "trend": "UPTREND",
        "bos": True,
        "choch": False,
        "volume_ratio": 1.6,
        "volume_status": "OK",
        "volume_class": "STRONG",
        "oi_change_pct": 0.5,
        "oi_status": "OK",
        "oi_class": "STRONG",
        "participation": "STRONG",
    }
    calls = []

    monkeypatch.setattr(
        pipeline_module,
        "build_validation_payload_v4",
        lambda results: [candidate],
    )

    def default_validator(candidates):
        calls.append(candidates)
        return _validator_result([_validation(SYMBOL_A)])

    monkeypatch.setattr(
        pipeline_module,
        "validate_candidates",
        default_validator,
    )

    result = pipeline_module.run_validated_pipeline_v4([_scanner_row()])

    assert len(calls) == 1
    assert result["final_top5"][0]["symbol"] == SYMBOL_A


def test_explicit_none_oi_dependencies_use_call_time_defaults(monkeypatch):
    oi_calls = []
    monkeypatch.setattr(
        payload_module,
        "open_interest_metrics_v2",
        _provider_from({SYMBOL_A: _oi_metrics()}, oi_calls),
    )

    candidate = payload_module.build_validation_candidate_v2(
        _scanner_row(),
        oi_provider=None,
    )

    builder_calls = []

    def default_candidate_builder(row):
        builder_calls.append(row["symbol"])
        return candidate

    monkeypatch.setattr(
        pipeline_module,
        "build_validation_candidate_v2",
        default_candidate_builder,
    )

    payload = pipeline_module.build_validation_payload_v4(
        [_scanner_row()],
        oi_provider=None,
    )

    assert oi_calls == [SYMBOL_A]
    assert builder_calls == [SYMBOL_A]
    assert payload == [candidate]


def test_explicit_none_dependencies_use_call_time_production_defaults(
    monkeypatch,
):
    oi_calls = []
    validator_calls = []
    monkeypatch.setattr(
        payload_module,
        "open_interest_metrics_v2",
        _provider_from({SYMBOL_A: _oi_metrics()}, oi_calls),
    )

    def default_validator(candidates):
        validator_calls.append(candidates)
        return _validator_result([_validation(SYMBOL_A)])

    monkeypatch.setattr(
        pipeline_module,
        "validate_candidates",
        default_validator,
    )

    result = pipeline_module.run_validated_pipeline_v4(
        [_scanner_row()],
        validator=None,
        oi_provider=None,
    )

    assert oi_calls == [SYMBOL_A]
    assert len(validator_calls) == 1
    assert result["final_top5"][0]["symbol"] == SYMBOL_A


def test_non_callable_dependencies_fail_without_default_fallback(monkeypatch):
    monkeypatch.setattr(
        payload_module,
        "open_interest_metrics_v2",
        _fail_if_called("default OI provider"),
    )
    monkeypatch.setattr(
        pipeline_module,
        "validate_candidates",
        _fail_if_called("default validator"),
    )

    with pytest.raises(TypeError):
        payload_module.build_validation_candidate_v2(
            _scanner_row(),
            oi_provider=object(),
        )

    with pytest.raises(TypeError):
        pipeline_module.run_validated_pipeline_v4(
            [_scanner_row()],
            validator=object(),
            oi_provider=lambda symbol: _oi_metrics(),
        )


def test_provider_dependencies_are_keyword_only():
    provider = lambda symbol: _oi_metrics()
    validator = lambda candidates: _validator_result(
        [_validation(row["symbol"]) for row in candidates]
    )

    with pytest.raises(TypeError):
        payload_module.build_validation_candidate_v2(
            _scanner_row(),
            provider,
        )

    with pytest.raises(TypeError):
        pipeline_module.build_validation_payload_v4(
            [_scanner_row()],
            provider,
        )

    with pytest.raises(TypeError):
        pipeline_module.run_validated_pipeline_v4(
            [_scanner_row()],
            validator,
            provider,
        )
