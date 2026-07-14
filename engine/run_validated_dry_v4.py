from engine.final_reporter_v4 import print_final_report_v4
from engine.master_engine_v4 import run_master_engine_v4


def main():
    run = run_master_engine_v4()

    print_final_report_v4(
        run["out"],
        snapshot_path=run["snapshot_path"],
        evidence_path=run["evidence_path"],
    )


if __name__ == "__main__":
    main()
