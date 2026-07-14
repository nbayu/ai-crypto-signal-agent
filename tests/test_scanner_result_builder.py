from copy import deepcopy

from engine.scanner_result_builder import build_scanner_result


def _builder_inputs():
    mtf = {"confirmed": True, "score": 6}
    golden_zone = {"zone": "GZ"}
    return {
        "symbol": "BTCUSDT",
        "reference_price": 110.0,
        "reference_candle_at": "2024-01-02T00:00:00",
        "trend": "UP",
        "mtf": mtf,
        "mtf_score": 6,
        "bos": True,
        "choch": False,
        "golden_zone": golden_zone,
        "quality": 9,
        "fvg": 3,
        "order_blocks": 2,
        "liquidity": 2,
        "atr": 10,
        "distance_ob": 15,
        "distance_fvg": 2,
        "volume": 60,
        "volume_spike": True,
        "volume_ratio": 1.5,
        "volume_v2_score": 7,
        "volume_v2_status": "OK",
        "open_interest": 70,
        "oi_growth": 8,
    }


def test_build_scanner_result_contract_and_identity():
    inputs = _builder_inputs()
    original_inputs = deepcopy(inputs)

    result = build_scanner_result(**inputs)
    second_result = build_scanner_result(**inputs)

    assert result == original_inputs
    assert list(result) == list(original_inputs)
    assert result["mtf"] is inputs["mtf"]
    assert result["golden_zone"] is inputs["golden_zone"]
    assert result is not second_result
    assert inputs == original_inputs
    assert "score" not in result
    assert "entry_score" not in result
