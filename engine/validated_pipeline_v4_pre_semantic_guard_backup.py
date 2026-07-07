import json

from engine.deepseek_validator_v4 import validate_candidates
from engine.validation_control import apply_validation_control
from engine.validation_semantic_guard_v4 import (
    validate_semantic_consistency,
)
from engine.validation_payload_v2 import build_validation_candidate_v2


TOP_N_FOR_VALIDATION = 10
FINAL_TOP_N = 5


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


def run_validated_pipeline_v4(results):
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

    return {
        "controlled_top10": controlled,
        "final_top5": controlled[:FINAL_TOP_N],
        "usage": ai_result["usage"],
    }
