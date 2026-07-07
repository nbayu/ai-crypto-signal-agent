from engine.open_interest_v2 import open_interest_metrics_v2
from engine.evidence_classifier_v2 import classify_participation


def build_validation_candidate_v2(candidate):
    """
    Build one bounded V4 validation candidate.

    Volume V2 is reused from scanner output.
    OI V2 is fetched only for candidates entering V4 validation.

    Python owns:
    - raw evidence calculation
    - evidence classification

    DeepSeek receives the result but must not recalculate it.
    """

    volume_ratio = candidate.get("volume_ratio")
    volume_status = candidate.get("volume_v2_status")

    oi = open_interest_metrics_v2(
        candidate["symbol"]
    )

    evidence = classify_participation(
        volume_ratio,
        volume_status,
        oi["oi_change_pct"],
        oi["data_status"],
    )

    return {
        "symbol": candidate["symbol"],
        "python_score": candidate["score"],
        "trend": candidate["trend"],
        "bos": candidate["bos"],
        "choch": candidate["choch"],

        "volume_ratio": volume_ratio,
        "volume_status": volume_status,
        "volume_class": evidence["volume_class"],

        "oi_change_pct": oi["oi_change_pct"],
        "oi_status": oi["data_status"],
        "oi_class": evidence["oi_class"],

        "participation": evidence["participation"],
    }
