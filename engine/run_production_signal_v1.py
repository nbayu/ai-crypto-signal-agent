import hashlib
import os
import sys
from collections.abc import Mapping

from engine import passive_production_signal_flow_v1 as signal_flow
from engine.telegram_runtime_v4 import load_telegram_delivery_config
from engine.master_engine_v4 import run_master_engine_v4
from engine.outcome_tracker_v4 import (
    generate_outcome_invocation_id,
    validate_outcome_invocation_id,
)
from engine.phase09r_telegram_delivery_adapter_v1 import Phase09RTelegramDeliveryAdapterV1
from engine.active_signal_ledger_v1 import inspect_capacity, load_ledger
from engine.canonical_pair_v1 import normalize_pair
from engine.telegram_owner_control_state_v1 import bind_signal_message
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

def main(
    *,
    outcome_invocation_id=None,
    outcome_invocation_id_provider=generate_outcome_invocation_id,
):
    try:
        selected_outcome_invocation_id = (
            outcome_invocation_id
            if outcome_invocation_id is not None
            else outcome_invocation_id_provider()
        )
        selected_outcome_invocation_id = validate_outcome_invocation_id(
            selected_outcome_invocation_id
        )
    except Exception:
        return 7

    try:
        config = load_telegram_delivery_config(os.environ)
        destination_id = os.environ.get("TELEGRAM_DESTINATION_ID")
        if not destination_id:
            return 2
    except Exception:
        return 2

    ledger_path = os.environ.get("ACTIVE_SIGNAL_LEDGER_PATH")
    try:
        owner_blueprint_ledger = load_ledger(ledger_path) if ledger_path else None
    except Exception:
        return 2

    control_state_path = os.environ.get("TELEGRAM_OWNER_CONTROL_STATE_PATH")
    delivered_bindings = []

    def record_binding(*, payload, destination_id, message_id, timestamp):
        delivered_bindings.append({
            "signal_id": payload["signal_id"],
            "canonical_pair": normalize_pair(payload["symbol"]),
            "style": payload["mode"],
            "telegram_chat_id": destination_id,
            "telegram_message_id": message_id,
            "timestamp": timestamp,
        })

    adapter = Phase09RTelegramDeliveryAdapterV1(
        config,
        available_slots_provider=(
            (lambda style: inspect_capacity(owner_blueprint_ledger)["remaining_by_mode"][style])
            if owner_blueprint_ledger is not None else None
        ),
        message_binding_recorder=record_binding if control_state_path else None,
    )

    try:
        pub_dir = os.environ.get("PRODUCTION_SIGNAL_DIR")
        run_out = run_master_engine_v4(
            outcome_invocation_id=selected_outcome_invocation_id,
            enable_publication=True,
            delivery_adapter=adapter,
            destination_id=destination_id,
            publication_root=pub_dir,
            owner_blueprint_ledger=owner_blueprint_ledger,
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
            if ledger_path:
                try:
                    current_ledger = load_ledger(ledger_path)
                    signal_id = publication["signal_id"]
                    delivery_id = publication["delivery_id"]
                    transition_digest = hashlib.sha256(
                        (
                            "published-signal-registration-v1\0"
                            + signal_id
                            + "\0"
                            + delivery_id
                        ).encode("utf-8")
                    ).hexdigest()
                    receipt = publication["delivery_receipt"]
                    if not isinstance(receipt, Mapping):
                        raise ValueError
                    binding = {
                        "signal_id": signal_id,
                        "canonical_pair": normalize_pair(
                            publication["publication_payload"]["symbol"]
                        ),
                        "style": publication["mode"],
                        "telegram_chat_id": str(receipt["destination_id"]),
                        "telegram_message_id": int(receipt["external_delivery_id"]),
                        "timestamp": receipt["delivered_at"],
                    }
                    if delivered_bindings and (
                        len(delivered_bindings) != 1
                        or delivered_bindings[0] != binding
                    ):
                        raise ValueError
                    registered = signal_flow.register_completed_publication(
                        active_ledger_path=ledger_path,
                        expected_active_ledger_revision=current_ledger["ledger_revision"],
                        publication_evidence=publication,
                        reservation_transition_id=(
                            f"published-signal-registration-{transition_digest}"
                        ),
                        timestamp=receipt["delivered_at"],
                    )
                    if registered.result not in {
                        signal_flow.PUBLISHED_SIGNAL_REGISTERED,
                        signal_flow.PUBLISHED_SIGNAL_REGISTRATION_REPLAYED,
                    }:
                        raise RuntimeError
                    if not control_state_path:
                        raise RuntimeError
                    bind_signal_message(
                        control_state_path,
                        signal_id=binding["signal_id"],
                        canonical_pair=binding["canonical_pair"],
                        style=binding["style"],
                        telegram_chat_id=binding["telegram_chat_id"],
                        telegram_message_id=binding["telegram_message_id"],
                        timestamp=binding["timestamp"],
                    )
                except Exception as exc:
                    return _exit7(
                        "PUBLISHED_SIGNAL_REGISTRATION",
                        "PUBLISHED_SIGNAL_REGISTRATION_FAILED",
                        exc,
                    )
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
