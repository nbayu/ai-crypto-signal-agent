from engine.quota_slot_engine_v4 import (
    acquire_quota_slot_v4,
    release_quota_slot_v4,
)
from engine.stateful_worker_v4 import run_master_engine_worker_v4


def run_quota_slot_worker_v4(
    *,
    subject_id,
    window_id,
    quota_limit,
    slot_capacity,
    quota_state_path,
    worker_state_path,
    quota_now_provider,
    reservation_id_provider,
    worker=run_master_engine_worker_v4,
    acquire=acquire_quota_slot_v4,
    release=release_quota_slot_v4,
):
    admission = acquire(
        subject_id=subject_id,
        window_id=window_id,
        quota_limit=quota_limit,
        slot_capacity=slot_capacity,
        state_path=quota_state_path,
        now_provider=quota_now_provider,
        reservation_id_provider=reservation_id_provider,
    )

    worker_error = None
    try:
        worker_result = worker(state_path=worker_state_path)
    except BaseException as exc:
        worker_error = exc
        raise
    finally:
        try:
            release_result = release(
                reservation_id=admission["reservation_id"],
                state_path=quota_state_path,
                now_provider=quota_now_provider,
            )
        except BaseException as release_error:
            if worker_error is not None:
                raise worker_error from release_error
            raise

    return {
        "admission": admission,
        "worker_result": worker_result,
        "release": release_result,
    }
