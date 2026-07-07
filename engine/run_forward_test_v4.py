import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from engine.forward_outcome_resolver_v4 import (
    resolve_entry_artifact,
)
from engine.forward_test_validator_v4 import (
    validate_resolved_artifact,
)


def run_forward_test_v4(entry_path, now_utc=None):
    entry_path = Path(entry_path)

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    resolution = resolve_entry_artifact(
        entry_path,
        now_utc=now_utc,
    )

    report = validate_resolved_artifact(
        resolution["resolution_path"]
    )

    return {
        "resolution": resolution,
        "validation": report,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Resolve and validate one explicit "
            "V4 outcome entry artifact."
        )
    )
    parser.add_argument(
        "entry_path",
        help=(
            "Explicit path to an "
            "outcome_entry_v4_*.json artifact"
        ),
    )

    args = parser.parse_args()

    result = run_forward_test_v4(
        args.entry_path
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
