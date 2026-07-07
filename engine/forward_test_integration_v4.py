import json
from pathlib import Path

from engine.run_forward_test_v4 import (
    run_forward_test_v4,
)


def run_forward_test_from_production_evidence(
    manifest_path,
    now_utc=None,
):
    manifest_path = Path(manifest_path)

    try:
        manifest = json.loads(
            manifest_path.read_text()
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            "Invalid production evidence JSON"
        ) from e

    if not isinstance(manifest, dict):
        raise ValueError(
            "Production evidence must be an object"
        )

    if manifest.get("snapshot_type") != (
        "v4_production_evidence"
    ):
        raise ValueError(
            "Invalid production evidence snapshot_type"
        )

    if manifest.get("schema_version") != 1:
        raise ValueError(
            "Invalid production evidence schema_version"
        )

    artifacts = manifest.get("artifacts")

    if not isinstance(artifacts, dict):
        raise ValueError(
            "Invalid production evidence artifacts"
        )

    outcome_entry_path = artifacts.get(
        "outcome_entry"
    )

    if (
        not isinstance(outcome_entry_path, str)
        or not outcome_entry_path.strip()
    ):
        raise ValueError(
            "Invalid production evidence outcome_entry"
        )

    forward_test = run_forward_test_v4(
        outcome_entry_path,
        now_utc=now_utc,
    )

    return {
        "production_evidence_path": str(
            manifest_path
        ),
        "outcome_entry_path": outcome_entry_path,
        "forward_test": forward_test,
    }
