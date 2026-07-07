import json

from engine.deepseek_validator import validate_candidates
from engine.validation_control import apply_validation_control


TOP_N_FOR_VALIDATION = 10
FINAL_TOP_N = 5


def build_validation_payload(results):
    ranked = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )[:TOP_N_FOR_VALIDATION]

    payload = []

    for r in ranked:
        payload.append({
            "symbol": r["symbol"],
            "python_score": r["score"],
            "trend": r["trend"],
            "bos": r["bos"],
            "choch": r["choch"],
            "volume_spike": r["volume_spike"],
            "oi_growth": r["oi_growth"],
        })

    return payload


def run_validated_pipeline(results):
    candidates = build_validation_payload(results)

    if not candidates:
        return {
            "final_top5": [],
            "usage": {}
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
        validations
    )

    return {
        "controlled_top10": controlled,
        "final_top5": controlled[:FINAL_TOP_N],
        "usage": ai_result["usage"]
    }
