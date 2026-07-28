from engine.final_reporter_v4 import print_final_report_v4
from engine.master_engine_v4 import run_master_engine_v4
from engine.outcome_tracker_v4 import (
    generate_outcome_invocation_id,
    validate_outcome_invocation_id,
)


def main(
    *,
    outcome_invocation_id=None,
    outcome_invocation_id_provider=generate_outcome_invocation_id,
):
    selected_outcome_invocation_id = (
        outcome_invocation_id
        if outcome_invocation_id is not None
        else outcome_invocation_id_provider()
    )
    selected_outcome_invocation_id = validate_outcome_invocation_id(
        selected_outcome_invocation_id
    )
    run = run_master_engine_v4(
        outcome_invocation_id=selected_outcome_invocation_id
    )

    print_final_report_v4(
        run["out"],
        snapshot_path=run["snapshot_path"],
        evidence_path=run["evidence_path"],
    )


if __name__ == "__main__":
    main()
