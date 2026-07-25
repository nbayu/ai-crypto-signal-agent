import os
import sys

from engine.telegram_runtime_v4 import load_telegram_runtime_config
from engine.master_engine_v4 import run_master_engine_v4
from engine.phase09r_telegram_delivery_adapter_v1 import Phase09RTelegramDeliveryAdapterV1

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
    except Exception as exc:
        return 7

    if adapter.rejection_reason == "QUOTA_EXHAUSTED":
        return 3
    if adapter.rejection_reason == "SLOTS_FULL":
        return 4
    if adapter.malformed_receipt:
        return 6

    prod_out = run_out.get("production_signal_out")
    if not prod_out:
        return 7

    status = prod_out.get("status")
    if status == "DELIVERY_NOT_CONFIGURED":
        return 2

    publication = prod_out.get("publication")
    if publication:
        delivery_state = publication.get("delivery_state")
        if delivery_state == "DELIVERY_FAILED":
            return 5
        if delivery_state == "DELIVERY_SUCCEEDED":
            return 0

    # Maybe it was a NO_TRADE outcome?
    if prod_out.get("evaluation") is not None:
        return 0

    return 7

if __name__ == "__main__":
    sys.exit(main())
