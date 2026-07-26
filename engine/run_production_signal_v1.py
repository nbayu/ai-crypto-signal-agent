import os
import sys
from collections.abc import Mapping

from engine.telegram_runtime_v4 import load_telegram_runtime_config
from engine.master_engine_v4 import run_master_engine_v4
from engine.phase09r_telegram_delivery_adapter_v1 import Phase09RTelegramDeliveryAdapterV1
from engine.phase09r_observability_v1 import (
    BOUNDARY_UNKNOWN,
    MASTER_ENGINE_UNCLASSIFIED,
    PRODUCTION_SIGNAL_OUT_MALFORMED,
    PRODUCTION_SIGNAL_OUT_MISSING,
    UNKNOWN_PRODUCTION_SIGNAL_OUTCOME,
    Phase09RExit7Failure,
    classified_failure,
    emit_exit7_event,
)

def _exit7(failure_stage, failure_code, exc, boundary=BOUNDARY_UNKNOWN):
    emit_exit7_event(classified_failure(
        failure_stage=failure_stage,
        failure_code=failure_code,
        exc=exc,
        telegram_boundary_reached=boundary,
    ))
    return 7

def main():
    try:
        config = load_telegram_runtime_config(os.environ)
        destination_id = os.environ.get("TELEGRAM_DESTINATION_ID")
        if not destination_id:
            return 2
    except Exception:
        return 2

    adapter = Phase09RTelegramDeliveryAdapterV1(config)

    try:
        pub_dir = os.environ.get("PRODUCTION_SIGNAL_DIR")
        run_out = run_master_engine_v4(
            enable_publication=True,
            delivery_adapter=adapter,
            destination_id=destination_id,
            publication_root=pub_dir,
        )
    except Phase09RExit7Failure as failure:
        emit_exit7_event(failure)
        return 7
    except Exception as exc:
        return _exit7(
            "MASTER_ENGINE_UNCLASSIFIED",
            MASTER_ENGINE_UNCLASSIFIED,
            exc,
        )

    if adapter.rejection_reason == "QUOTA_EXHAUSTED":
        return 3
    if adapter.rejection_reason == "SLOTS_FULL":
        return 4
    if adapter.malformed_receipt:
        return 6

    if not isinstance(run_out, Mapping):
        return _exit7(
            "PRODUCTION_SIGNAL_OUT_MALFORMED",
            PRODUCTION_SIGNAL_OUT_MALFORMED,
            TypeError(),
        )
    if "production_signal_out" not in run_out or run_out["production_signal_out"] is None:
        return _exit7(
            "PRODUCTION_SIGNAL_OUT_MISSING",
            PRODUCTION_SIGNAL_OUT_MISSING,
            KeyError(),
        )
    prod_out = run_out["production_signal_out"]
    if not isinstance(prod_out, Mapping) or not prod_out:
        return _exit7(
            "PRODUCTION_SIGNAL_OUT_MALFORMED",
            PRODUCTION_SIGNAL_OUT_MALFORMED,
            TypeError(),
        )

    status = prod_out.get("status")
    if status is not None and not isinstance(status, str):
        return _exit7(
            "PRODUCTION_SIGNAL_OUT_MALFORMED",
            PRODUCTION_SIGNAL_OUT_MALFORMED,
            TypeError(),
        )
    if status == "DELIVERY_NOT_CONFIGURED":
        return 2

    publication = prod_out.get("publication")
    if publication is not None:
        if not isinstance(publication, Mapping) or not publication:
            return _exit7(
                "PRODUCTION_SIGNAL_OUT_MALFORMED",
                PRODUCTION_SIGNAL_OUT_MALFORMED,
                TypeError(),
            )
        delivery_state = publication.get("delivery_state")
        if not isinstance(delivery_state, str):
            return _exit7(
                "PRODUCTION_SIGNAL_OUT_MALFORMED",
                PRODUCTION_SIGNAL_OUT_MALFORMED,
                TypeError(),
            )
        if delivery_state == "DELIVERY_FAILED":
            return 5
        if delivery_state == "DELIVERY_SUCCEEDED":
            return 0

    # Maybe it was a NO_TRADE outcome?
    evaluation = prod_out.get("evaluation")
    if evaluation is not None:
        if not isinstance(evaluation, Mapping):
            return _exit7(
                "PRODUCTION_SIGNAL_OUT_MALFORMED",
                PRODUCTION_SIGNAL_OUT_MALFORMED,
                TypeError(),
            )
        return 0

    return _exit7(
        "UNKNOWN_PRODUCTION_SIGNAL_OUTCOME",
        UNKNOWN_PRODUCTION_SIGNAL_OUTCOME,
        ValueError(),
    )

if __name__ == "__main__":
    sys.exit(main())
