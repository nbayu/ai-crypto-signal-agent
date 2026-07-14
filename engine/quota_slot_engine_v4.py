"""Single-process durable quota and active-slot accounting for Phase 04."""

import json
from pathlib import Path


SCHEMA_VERSION = 1
DEFAULT_STATE_PATH = Path("data/quota_slot_v4/quota_slot_state.json")

ACTIVE = "ACTIVE"
RELEASED = "RELEASED"


class QuotaSlotRejected(Exception):
    def __init__(self, reason_code, message=None):
        self.reason_code = reason_code
        super().__init__(message or f"Quota-slot request rejected: {reason_code}")


def _reject(reason_code, message=None):
    raise QuotaSlotRejected(reason_code, message)


def _is_positive_integer(value):
    return type(value) is int and value > 0


def _is_valid_identifier(value):
    return isinstance(value, str) and bool(value.strip())


def _isoformat(value):
    return value.isoformat()


def _empty_state():
    return {
        "schema_version": SCHEMA_VERSION,
        "quota_usage": {},
        "reservations": {},
    }


def _validate_reservation(reservation_id, reservation):
    if not _is_valid_identifier(reservation_id):
        _reject("STATE_CORRUPT", "Reservation identity is invalid")

    if not isinstance(reservation, dict):
        _reject("STATE_CORRUPT", "Reservation record is malformed")

    if reservation.get("reservation_id") != reservation_id:
        _reject("STATE_CORRUPT", "Reservation identity does not match")

    if not _is_valid_identifier(reservation.get("subject_id")):
        _reject("STATE_CORRUPT", "Reservation subject is invalid")

    if not _is_valid_identifier(reservation.get("window_id")):
        _reject("STATE_CORRUPT", "Reservation window is invalid")

    if reservation.get("state") not in (ACTIVE, RELEASED):
        _reject("STATE_CORRUPT", "Reservation state is invalid")

    if not _is_valid_identifier(reservation.get("acquired_at")):
        _reject("STATE_CORRUPT", "Reservation timestamp is invalid")

    if "released_at" not in reservation:
        _reject("STATE_CORRUPT", "Reservation release timestamp is missing")

    released_at = reservation["released_at"]
    if reservation["state"] == ACTIVE and released_at is not None:
        _reject("STATE_CORRUPT", "Active reservation has release time")

    if reservation["state"] == RELEASED and not _is_valid_identifier(
        released_at
    ):
        _reject("STATE_CORRUPT", "Released reservation timestamp is invalid")


def _validate_state(state):
    if not isinstance(state, dict):
        _reject("STATE_CORRUPT", "State must be an object")

    if type(state.get("schema_version")) is not int or state[
        "schema_version"
    ] != SCHEMA_VERSION:
        _reject("STATE_CORRUPT", "State schema version is incompatible")

    quota_usage = state.get("quota_usage")
    if not isinstance(quota_usage, dict):
        _reject("STATE_CORRUPT", "Quota usage is malformed")

    for subject_id, windows in quota_usage.items():
        if not _is_valid_identifier(subject_id) or not isinstance(windows, dict):
            _reject("STATE_CORRUPT", "Quota usage is malformed")

        for window_id, usage in windows.items():
            if not _is_valid_identifier(window_id):
                _reject("STATE_CORRUPT", "Quota window is invalid")
            if type(usage) is not int or usage < 0:
                _reject("STATE_CORRUPT", "Quota usage value is invalid")

    reservations = state.get("reservations")
    if not isinstance(reservations, dict):
        _reject("STATE_CORRUPT", "Reservations are malformed")

    for reservation_id, reservation in reservations.items():
        _validate_reservation(reservation_id, reservation)


def read_quota_slot_state(state_path):
    state_path = Path(state_path)
    if not state_path.exists():
        return _empty_state()

    try:
        state = json.loads(state_path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _reject("STATE_CORRUPT", f"Unable to read state: {exc}")

    _validate_state(state)
    return state


def write_quota_slot_state_atomic(state, state_path):
    _validate_state(state)

    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_name(f"{state_path.name}.tmp")
    temp_path.write_text(json.dumps(state, indent=2))
    temp_path.replace(state_path)

    return state_path


def _active_slot_count(state):
    return sum(
        reservation["state"] == ACTIVE
        for reservation in state["reservations"].values()
    )


def _validate_acquisition_request(
    subject_id,
    window_id,
    quota_limit,
    slot_capacity,
):
    if not _is_valid_identifier(subject_id) or not _is_valid_identifier(
        window_id
    ):
        _reject("INVALID_REQUEST", "Subject and window IDs must be non-blank")

    if not _is_positive_integer(quota_limit) or not _is_positive_integer(
        slot_capacity
    ):
        _reject("INVALID_POLICY", "Limits and capacity must be positive integers")


def acquire_quota_slot_v4(
    *,
    subject_id,
    window_id,
    quota_limit,
    slot_capacity,
    state_path,
    now_provider,
    reservation_id_provider,
):
    _validate_acquisition_request(
        subject_id,
        window_id,
        quota_limit,
        slot_capacity,
    )

    state = read_quota_slot_state(state_path)
    subject_usage = state["quota_usage"].get(subject_id, {})
    quota_used = subject_usage.get(window_id, 0)

    if quota_used >= quota_limit:
        _reject("QUOTA_EXHAUSTED", "Quota limit has been reached")

    active_slot_count = _active_slot_count(state)
    if active_slot_count >= slot_capacity:
        _reject("SLOTS_FULL", "No active slots are available")

    reservation_id = reservation_id_provider()
    if not _is_valid_identifier(reservation_id):
        _reject("INVALID_REQUEST", "Reservation ID is invalid")

    if reservation_id in state["reservations"]:
        _reject("INVALID_REQUEST", "Reservation ID already exists")

    state["quota_usage"].setdefault(subject_id, {})[window_id] = (
        quota_used + 1
    )
    state["reservations"][reservation_id] = {
        "reservation_id": reservation_id,
        "subject_id": subject_id,
        "window_id": window_id,
        "acquired_at": _isoformat(now_provider()),
        "released_at": None,
        "state": ACTIVE,
    }
    write_quota_slot_state_atomic(state, state_path)

    return {
        "admitted": True,
        "reservation_id": reservation_id,
        "subject_id": subject_id,
        "window_id": window_id,
        "quota_limit": quota_limit,
        "quota_used": quota_used + 1,
        "quota_remaining": quota_limit - (quota_used + 1),
        "slot_capacity": slot_capacity,
        "active_slot_count": active_slot_count + 1,
        "state_path": Path(state_path),
    }


def release_quota_slot_v4(
    *,
    reservation_id,
    state_path,
    now_provider,
):
    if not _is_valid_identifier(reservation_id):
        _reject("INVALID_REQUEST", "Reservation ID is invalid")

    state = read_quota_slot_state(state_path)
    reservation = state["reservations"].get(reservation_id)
    if reservation is None:
        _reject("INVALID_REQUEST", "Reservation ID is unknown")

    active_slot_count = _active_slot_count(state)
    if reservation["state"] == RELEASED:
        return {
            "reservation_id": reservation_id,
            "released": False,
            "already_released": True,
            "active_slot_count": active_slot_count,
            "state_path": Path(state_path),
        }

    reservation["state"] = RELEASED
    reservation["released_at"] = _isoformat(now_provider())
    write_quota_slot_state_atomic(state, state_path)

    return {
        "reservation_id": reservation_id,
        "released": True,
        "already_released": False,
        "active_slot_count": active_slot_count - 1,
        "state_path": Path(state_path),
    }
