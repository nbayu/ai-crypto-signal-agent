class SemanticValidationError(ValueError):
    def __init__(
        self,
        symbol,
        candidate,
        validation,
        errors,
    ):
        self.symbol = symbol
        self.candidate = dict(candidate)
        self.validation = dict(validation)
        self.errors = list(errors)

        super().__init__(
            f"Semantic AI validation conflict for {symbol}: "
            + "; ".join(self.errors)
        )


def validate_semantic_consistency(candidate, validation):
    symbol = candidate["symbol"]

    bos = candidate["bos"]
    choch = candidate["choch"]
    participation = candidate["participation"]

    status = validation["status"]
    risk = validation["false_breakout_risk"]
    confluence = validation["confluence"]
    reason = validation["reason_code"]

    errors = []

    # BREAKOUT_UNCONFIRMED is impossible when Python confirms BOS.
    if bos is True and reason == "BREAKOUT_UNCONFIRMED":
        errors.append(
            "bos=True cannot receive BREAKOUT_UNCONFIRMED"
        )

    # bos=False must never receive LOW false-breakout risk.
    if bos is False and risk == "LOW":
        errors.append(
            "bos=False cannot receive LOW false_breakout_risk"
        )

    # CHOCH is always a structural conflict.
    if choch is True:
        if status == "CLEAR":
            errors.append(
                "choch=True cannot receive CLEAR"
            )

        if reason == "ALIGNED":
            errors.append(
                "choch=True cannot receive ALIGNED"
            )

    # STRUCTURE_REVERSAL_CONFLICT requires Python-confirmed CHOCH.
    if (
        reason == "STRUCTURE_REVERSAL_CONFLICT"
        and choch is not True
    ):
        errors.append(
            "reason_code=STRUCTURE_REVERSAL_CONFLICT requires choch=True"
        )

    # MIXED participation requires caution.
    if (
        reason == "MIXED_PARTICIPATION"
        and participation != "MIXED"
    ):
        errors.append(
            "reason_code=MIXED_PARTICIPATION requires participation=MIXED"
        )

    if participation == "MIXED":
        if reason == "ALIGNED":
            errors.append(
                "participation=MIXED cannot receive ALIGNED"
            )

        if status == "CLEAR":
            errors.append(
                "participation=MIXED cannot receive CLEAR"
            )

        if risk == "LOW":
            errors.append(
                "participation=MIXED cannot receive LOW risk"
            )

    # UNKNOWN participation cannot be interpreted as aligned evidence.
    if (
        participation == "UNKNOWN"
        and reason == "ALIGNED"
    ):
        errors.append(
            "participation=UNKNOWN cannot receive ALIGNED"
        )

    # UNKNOWN data must never be reinterpreted as weak market evidence.
    if participation == "UNKNOWN":
        if reason in {
            "WEAK_VOLUME",
            "WEAK_OI",
            "WEAK_PARTICIPATION",
        }:
            errors.append(
                "participation=UNKNOWN cannot be treated as WEAK"
            )

    # WEAK_PARTICIPATION requires Python-confirmed WEAK participation.
    if (
        reason == "WEAK_PARTICIPATION"
        and participation != "WEAK"
    ):
        errors.append(
            "reason_code=WEAK_PARTICIPATION requires participation=WEAK"
        )

    # WEAK participation has an exact mandatory contract.
    if participation == "WEAK":
        if status != "HIGH_RISK":
            errors.append(
                "participation=WEAK requires HIGH_RISK"
            )

        if risk != "HIGH":
            errors.append(
                "participation=WEAK requires HIGH risk"
            )

        if confluence != "WEAK":
            errors.append(
                "participation=WEAK requires WEAK confluence"
            )

        if reason not in {
            "WEAK_PARTICIPATION",
            "MULTIPLE_CONFLICTS",
        }:
            errors.append(
                "participation=WEAK requires weak-participation reason"
            )

    if errors:
        raise SemanticValidationError(
            symbol=symbol,
            candidate=candidate,
            validation=validation,
            errors=errors,
        )

    return True
