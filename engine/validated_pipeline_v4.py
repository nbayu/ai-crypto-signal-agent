import json

from engine.deepseek_validator_v4 import validate_candidates
from engine.validation_control import apply_validation_control
from engine.validation_semantic_guard_v4 import (
    validate_semantic_consistency,
)
from engine.validation_payload_v2 import build_validation_candidate_v2


TOP_N_FOR_VALIDATION = 10
FINAL_TOP_N = 5
MIN_FINAL_RANK_SCORE = 80.0


def build_validation_payload_v4(results):
    ranked = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True,
    )[:TOP_N_FOR_VALIDATION]

    return [
        build_validation_candidate_v2(candidate)
        for candidate in ranked
    ]


def build_final_top5(controlled):
    qualified = [
        row
        for row in controlled
        if row["final_rank_score"] >= MIN_FINAL_RANK_SCORE
    ]

    return qualified[:FINAL_TOP_N]


def run_validated_pipeline_v4(results):
    reference_price_map = {
        row["symbol"]: row["reference_price"]
        for row in results
    }

    reference_candle_at_map = {
        row["symbol"]: row["reference_candle_at"]
        for row in results
    }

    golden_zone_map = {
        row["symbol"]: row.get("golden_zone")
        for row in results
    }

    candidates = build_validation_payload_v4(results)

    if not candidates:
        return {
            "controlled_top10": [],
            "final_top5": [],
            "usage": {},
        }

    ai_result = validate_candidates(candidates)

    try:
        parsed = json.loads(ai_result["content"])
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(
            f"Invalid DeepSeek JSON: {e}"
        )

    validations = parsed.get("validations")

    if not isinstance(validations, list):
        raise ValueError(
            "DeepSeek output missing validations list"
        )

    controlled = apply_validation_control(
        candidates,
        validations,
        semantic_guard=validate_semantic_consistency,
    )

    enriched_controlled = []

    for controlled_row in controlled:
        symbol = controlled_row["symbol"]

        if symbol not in reference_price_map:
            raise ValueError(
                f"Missing reference price for {symbol}"
            )

        row = dict(controlled_row)
        row["reference_price"] = reference_price_map[symbol]
        row["reference_candle_at"] = reference_candle_at_map[symbol]
        row["golden_zone"] = golden_zone_map[symbol]
        enriched_controlled.append(row)

    controlled = enriched_controlled

    return {
        "controlled_top10": controlled,
        "final_top5": build_final_top5(controlled),
        "usage": ai_result["usage"],
    }
