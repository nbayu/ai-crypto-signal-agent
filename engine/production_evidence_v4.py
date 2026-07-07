import json
from datetime import datetime
from pathlib import Path
from shutil import copy2


EVIDENCE_DIRECTORY = Path("data/production_evidence_v4")
SCHEMA_VERSION = 1
SNAPSHOT_TYPE = "v4_production_evidence"


def save_production_evidence(
    *,
    created_at,
    validated_snapshot_path,
    outcome_entry_path,
    raw_top5_path,
    pre_delivery_path,
    tradingview_watchlist_path,
    directory=None,
):
    if directory is None:
        directory = EVIDENCE_DIRECTORY

    directory = Path(directory)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    run_directory = (
        directory
        / f"production_run_v4_{timestamp}"
    )
    run_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    raw_top5_copy = (
        run_directory / "raw_top5.json"
    )
    pre_delivery_copy = (
        run_directory / "pre_delivery.json"
    )
    tradingview_copy = (
        run_directory / "tradingview_watchlist.txt"
    )

    copy2(
        raw_top5_path,
        raw_top5_copy,
    )
    copy2(
        pre_delivery_path,
        pre_delivery_copy,
    )
    copy2(
        tradingview_watchlist_path,
        tradingview_copy,
    )

    evidence = {
        "snapshot_type": SNAPSHOT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "artifacts": {
            "validated_snapshot": str(
                validated_snapshot_path
            ),
            "outcome_entry": str(
                outcome_entry_path
            ),
            "raw_top5": str(
                raw_top5_copy
            ),
            "pre_delivery": str(
                pre_delivery_copy
            ),
            "tradingview_watchlist": str(
                tradingview_copy
            ),
        },
    }

    manifest_path = (
        run_directory / "manifest.json"
    )
    manifest_path.write_text(
        json.dumps(
            evidence,
            indent=2,
        )
    )

    return manifest_path
