STATUS_PENALTY = {
    "CLEAR": 0,
    "CONFLICT": -3,
    "HIGH_RISK": -6,
}

FALSE_BREAKOUT_PENALTY = {
    "LOW": 0,
    "MEDIUM": -1,
    "HIGH": -3,
}

CONFLUENCE_PENALTY = {
    "STRONG": 0,
    "MODERATE": -1,
    "WEAK": -3,
}

MAX_PENALTY = -10


def calculate_validation_adjustment(validation):
    status = validation["status"]
    false_breakout_risk = validation["false_breakout_risk"]
    confluence = validation["confluence"]

    penalty = (
        STATUS_PENALTY[status]
        + FALSE_BREAKOUT_PENALTY[false_breakout_risk]
        + CONFLUENCE_PENALTY[confluence]
    )

    return max(MAX_PENALTY, penalty)


def apply_validation_control(candidates, validations):
    candidate_map = {
        candidate["symbol"]: candidate
        for candidate in candidates
    }

    validation_symbols = [
        validation["symbol"]
        for validation in validations
    ]

    if len(validation_symbols) != len(set(validation_symbols)):
        raise ValueError(
            "Duplicate symbols in AI validation"
        )

    validation_map = {
        validation["symbol"]: validation
        for validation in validations
    }

    controlled = []

    for symbol, candidate in candidate_map.items():
        if symbol not in validation_map:
            raise ValueError(
                f"Missing AI validation for {symbol}"
            )

        validation = validation_map[symbol]

        python_score = float(
            candidate.get("python_score", candidate.get("score", 0))
        )

        adjustment = calculate_validation_adjustment(validation)
        final_rank_score = max(0, python_score + adjustment)

        row = dict(candidate)
        row["python_score"] = python_score
        row["ai_validation"] = validation
        row["validation_adjustment"] = adjustment
        row["final_rank_score"] = final_rank_score

        controlled.append(row)

    extra_symbols = set(validation_map) - set(candidate_map)

    if extra_symbols:
        raise ValueError(
            f"Unknown symbols in AI validation: {sorted(extra_symbols)}"
        )

    controlled.sort(
        key=lambda x: (
            x["final_rank_score"],
            x["python_score"]
        ),
        reverse=True
    )

    return controlled
