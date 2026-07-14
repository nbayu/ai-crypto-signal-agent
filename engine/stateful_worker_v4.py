import json
import uuid
from datetime import datetime
from pathlib import Path

from engine.master_engine_v4 import run_master_engine_v4


WORKER_NAME = "master_engine_v4"
SCHEMA_VERSION = 1
DEFAULT_STATE_PATH = Path(
    "data/worker_state_v4/master_engine_v4_latest.json"
)


def _isoformat(value):
    if value is None:
        return None
    return value.isoformat()


def _default_run_id_provider():
    return str(uuid.uuid4())


def _build_started_event(*, run_id, started_at):
    return {
        "schema_version": SCHEMA_VERSION,
        "worker_name": WORKER_NAME,
        "run_id": run_id,
        "state": "STARTED",
        "started_at": _isoformat(started_at),
        "completed_at": None,
        "failed_at": None,
        "error": None,
        "artifacts": {},
    }


def _capture_artifacts(run):
    delivery_out = run.get("delivery_out") or {}

    artifact_map = {
        "snapshot_path": run.get("snapshot_path"),
        "outcome_path": run.get("outcome_path"),
        "watchlist_path": run.get("watchlist_path"),
        "evidence_path": run.get("evidence_path"),
        "delivery_artifact_path": delivery_out.get(
            "delivery_artifact_path"
        ),
        "tradingview_watchlist_path": delivery_out.get(
            "tradingview_watchlist_path"
        ),
        "pine_bridge_artifact_path": delivery_out.get(
            "pine_bridge_artifact_path"
        ),
        "pine_delivery_payload_path": delivery_out.get(
            "pine_delivery_payload_path"
        ),
    }

    return {
        key: str(value)
        for key, value in artifact_map.items()
        if value is not None
    }


def write_worker_state_atomic(event, state_path):
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = state_path.with_name(f"{state_path.name}.tmp")
    temp_path.write_text(
        json.dumps(
            event,
            indent=2,
            default=str,
        )
    )
    temp_path.replace(state_path)

    return state_path


def run_master_engine_worker_v4(
    *,
    master_engine=run_master_engine_v4,
    state_path=DEFAULT_STATE_PATH,
    now_provider=datetime.now,
    run_id_provider=_default_run_id_provider,
):
    run_id = run_id_provider()
    started_at = now_provider()

    event = _build_started_event(
        run_id=run_id,
        started_at=started_at,
    )
    write_worker_state_atomic(event, state_path)

    try:
        run = master_engine()
    except Exception as exc:
        failed = dict(event)
        failed.update(
            {
                "state": "FAILED",
                "failed_at": _isoformat(now_provider()),
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
                "artifacts": {},
            }
        )
        write_worker_state_atomic(failed, state_path)
        raise

    completed = dict(event)
    completed.update(
        {
            "state": "COMPLETED",
            "completed_at": _isoformat(now_provider()),
            "artifacts": _capture_artifacts(run),
        }
    )
    write_worker_state_atomic(completed, state_path)

    return {
        "state_path": Path(state_path),
        "run": run,
    }
