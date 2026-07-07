from engine.volume_v2 import volume_metrics_v2
from engine.open_interest_v2 import open_interest_metrics_v2
from engine.evidence_classifier_v2 import classify_participation


def build_validation_candidate_v2(candidate, df):
    """
    Build one bounded V4 validation candidate.

    Python owns:
    - raw evidence calculation
    - evidence classification

    DeepSeek receives the result but must not recalculate it.
    """

    vol = volume_metrics_v2(df)

    oi = open_interest_metrics_v2(
        candidate["symbol"]
    )

    evidence = classify_participation(
        vol["volume_ratio"],
        vol["data_status"],
        oi["oi_change_pct"],
        oi["data_status"],
    )

    return {
        "symbol": candidate["symbol"],
        "python_score": candidate["score"],
        "trend": candidate["trend"],
        "bos": candidate["bos"],
        "choch": candidate["choch"],

        "volume_ratio": vol["volume_ratio"],
        "volume_status": vol["data_status"],
        "volume_class": evidence["volume_class"],

        "oi_change_pct": oi["oi_change_pct"],
        "oi_status": oi["data_status"],
        "oi_class": evidence["oi_class"],

        "participation": evidence["participation"],
    }
