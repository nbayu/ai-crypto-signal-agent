from engine.market_structure import detect_trend
from engine.setup_lifecycle_validator_v4 import (
    evaluate_setup_lifecycle,
)
from engine.swing_supersession_validator_v4 import (
    evaluate_swing_supersession,
)


def build_pre_delivery_artifact(
    source_artifact,
    *,
    closed_candle_provider,
    validated_at,
):
    setups = source_artifact["setups"]

    if source_artifact["setup_count"] != len(setups):
        raise ValueError(
            "setup_count does not match setups length"
        )

    symbols = [
        setup["symbol"]
        for setup in setups
    ]

    if len(symbols) != len(set(symbols)):
        raise ValueError(
            "Duplicate source setup symbols found"
        )

    eligible_setups = []
    evaluations = []

    for setup in setups:
        closed_candles = closed_candle_provider(
            setup["symbol"]
        )
        current_trend = detect_trend(
            closed_candles
        )

        lifecycle = evaluate_setup_lifecycle(
            setup,
            closed_candles,
        )
        supersession = evaluate_swing_supersession(
            setup,
            closed_candles,
            current_trend,
        )

        rejection_reasons = []

        if not lifecycle["actionable"]:
            rejection_reasons.append(
                lifecycle["state"]
            )

        if supersession["superseded"]:
            rejection_reasons.append(
                "SUPERSEDED"
            )

        delivery_eligible = (
            lifecycle["actionable"]
            and not supersession["superseded"]
        )

        evaluations.append({
            "symbol": setup["symbol"],
            "lifecycle": lifecycle,
            "supersession": supersession,
            "delivery_eligible": delivery_eligible,
            "rejection_reasons": rejection_reasons,
        })

        if delivery_eligible:
            eligible_setups.append(setup)

    return {
        "source_generated_at": source_artifact[
            "generated_at"
        ],
        "validated_at": validated_at,
        "source_setup_count": len(setups),
        "eligible_setup_count": len(
            eligible_setups
        ),
        "setup_count": len(
            eligible_setups
        ),
        "setups": eligible_setups,
        "evaluations": evaluations,
    }
