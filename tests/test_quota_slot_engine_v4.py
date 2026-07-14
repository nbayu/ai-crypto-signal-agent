import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

from engine.quota_slot_engine_v4 import (
    QuotaSlotRejected,
    acquire_quota_slot_v4,
    read_quota_slot_state,
    release_quota_slot_v4,
    write_quota_slot_state_atomic,
)


ACQUIRED_AT = datetime(2026, 7, 14, 16, 0, 0)
RELEASED_AT = datetime(2026, 7, 14, 16, 5, 0)


def _acquire(
    state_path,
    *,
    subject_id="subject-001",
    window_id="window-001",
    quota_limit=3,
    slot_capacity=2,
    acquired_at=ACQUIRED_AT,
    reservation_id="reservation-001",
):
    return acquire_quota_slot_v4(
        subject_id=subject_id,
        window_id=window_id,
        quota_limit=quota_limit,
        slot_capacity=slot_capacity,
        state_path=state_path,
        now_provider=lambda: acquired_at,
        reservation_id_provider=lambda: reservation_id,
    )


def _release(
    state_path,
    reservation_id="reservation-001",
    released_at=RELEASED_AT,
):
    return release_quota_slot_v4(
        reservation_id=reservation_id,
        state_path=state_path,
        now_provider=lambda: released_at,
    )


def _read_state(state_path):
    return json.loads(state_path.read_text())


def _valid_state_with_reservation(**overrides):
    reservation = {
        "reservation_id": "reservation-001",
        "subject_id": "subject-001",
        "window_id": "window-001",
        "acquired_at": "2026-07-14T16:00:00",
        "released_at": None,
        "state": "ACTIVE",
    }
    reservation.update(overrides)
    return {
        "schema_version": 1,
        "quota_usage": {"subject-001": {"window-001": 1}},
        "reservations": {"reservation-001": reservation},
    }


def _without_reservation_field(field):
    state = _valid_state_with_reservation()
    state["reservations"]["reservation-001"].pop(field)
    return state


def test_first_valid_acquisition_succeeds_and_writes_durable_state(
    tmp_path,
):
    state_path = tmp_path / "quota_slot_state.json"

    result = _acquire(state_path)

    assert result["admitted"] is True
    assert result["reservation_id"] == "reservation-001"
    assert result["subject_id"] == "subject-001"
    assert result["window_id"] == "window-001"
    assert result["quota_limit"] == 3
    assert result["quota_used"] == 1
    assert result["quota_remaining"] == 2
    assert result["slot_capacity"] == 2
    assert result["active_slot_count"] == 1
    assert result["state_path"] == state_path
    assert _read_state(state_path) == {
        "schema_version": 1,
        "quota_usage": {
            "subject-001": {
                "window-001": 1,
            },
        },
        "reservations": {
            "reservation-001": {
                "reservation_id": "reservation-001",
                "subject_id": "subject-001",
                "window_id": "window-001",
                "acquired_at": "2026-07-14T16:00:00",
                "released_at": None,
                "state": "ACTIVE",
            },
        },
    }


def test_quota_exhaustion_fails_closed_without_mutating_state(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"
    _acquire(state_path, quota_limit=1, slot_capacity=1)
    _release(state_path)
    state_before_rejection = state_path.read_text()

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _acquire(
            state_path,
            quota_limit=1,
            slot_capacity=1,
            reservation_id="reservation-002",
        )

    assert exc_info.value.reason_code == "QUOTA_EXHAUSTED"
    assert state_path.read_text() == state_before_rejection
    state = _read_state(state_path)
    assert state["quota_usage"]["subject-001"]["window-001"] == 1
    assert list(state["reservations"]) == ["reservation-001"]


def test_slot_capacity_exhaustion_fails_closed_without_consuming_quota(
    tmp_path,
):
    state_path = tmp_path / "quota_slot_state.json"
    _acquire(state_path, quota_limit=1, slot_capacity=1)
    state_before_rejection = state_path.read_text()

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _acquire(
            state_path,
            subject_id="subject-002",
            quota_limit=1,
            slot_capacity=1,
            reservation_id="reservation-002",
        )

    assert exc_info.value.reason_code == "SLOTS_FULL"
    assert state_path.read_text() == state_before_rejection
    state = _read_state(state_path)
    assert "subject-002" not in state["quota_usage"]
    assert "reservation-002" not in state["reservations"]


def test_quota_is_checked_before_slots_and_reservation_id_generation(
    tmp_path,
):
    state_path = tmp_path / "quota_slot_state.json"
    _acquire(state_path, quota_limit=1, slot_capacity=1)
    state_before_rejection = state_path.read_text()
    reservation_id_calls = []

    with pytest.raises(QuotaSlotRejected) as exc_info:
        acquire_quota_slot_v4(
            subject_id="subject-001",
            window_id="window-001",
            quota_limit=1,
            slot_capacity=1,
            state_path=state_path,
            now_provider=lambda: ACQUIRED_AT,
            reservation_id_provider=lambda: reservation_id_calls.append(
                "called"
            ),
        )

    assert exc_info.value.reason_code == "QUOTA_EXHAUSTED"
    assert reservation_id_calls == []
    assert state_path.read_text() == state_before_rejection


def test_slots_are_checked_before_reservation_id_generation(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"
    _acquire(state_path, quota_limit=2, slot_capacity=1)
    state_before_rejection = state_path.read_text()
    reservation_id_calls = []

    with pytest.raises(QuotaSlotRejected) as exc_info:
        acquire_quota_slot_v4(
            subject_id="subject-002",
            window_id="window-001",
            quota_limit=2,
            slot_capacity=1,
            state_path=state_path,
            now_provider=lambda: ACQUIRED_AT,
            reservation_id_provider=lambda: reservation_id_calls.append(
                "called"
            ),
        )

    assert exc_info.value.reason_code == "SLOTS_FULL"
    assert reservation_id_calls == []
    assert state_path.read_text() == state_before_rejection


def test_duplicate_reservation_id_fails_without_mutation(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"
    _acquire(state_path, quota_limit=2, slot_capacity=2)
    state_before_rejection = state_path.read_text()

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _acquire(
            state_path,
            subject_id="subject-002",
            quota_limit=2,
            slot_capacity=2,
            reservation_id="reservation-001",
        )

    assert exc_info.value.reason_code == "INVALID_REQUEST"
    assert state_path.read_text() == state_before_rejection


def test_release_frees_exactly_one_active_slot(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"
    _acquire(state_path)

    result = _release(state_path)

    assert result["released"] is True
    assert result["already_released"] is False
    assert result["reservation_id"] == "reservation-001"
    assert result["active_slot_count"] == 0
    assert result["state_path"] == state_path
    reservation = _read_state(state_path)["reservations"][
        "reservation-001"
    ]
    assert reservation["state"] == "RELEASED"
    assert reservation["released_at"] == "2026-07-14T16:05:00"


def test_release_is_idempotent_and_preserves_original_release_time(
    tmp_path,
):
    state_path = tmp_path / "quota_slot_state.json"
    _acquire(state_path)
    first_result = _release(state_path)

    second_result = _release(
        state_path,
        released_at=datetime(2026, 7, 14, 16, 10, 0),
    )

    assert first_result["released"] is True
    assert first_result["already_released"] is False
    assert second_result["released"] is False
    assert second_result["already_released"] is True
    assert second_result["reservation_id"] == "reservation-001"
    assert second_result["active_slot_count"] == 0
    reservation = _read_state(state_path)["reservations"][
        "reservation-001"
    ]
    assert reservation["state"] == "RELEASED"
    assert reservation["released_at"] == "2026-07-14T16:05:00"


def test_unknown_reservation_release_fails_closed_without_mutation(
    tmp_path,
):
    state_path = tmp_path / "quota_slot_state.json"
    _acquire(state_path)
    state_before_rejection = state_path.read_text()

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _release(state_path, reservation_id="unknown-reservation")

    assert exc_info.value.reason_code == "INVALID_REQUEST"
    assert state_path.read_text() == state_before_rejection


def test_independent_subjects_have_independent_quota_usage(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"

    first = _acquire(
        state_path,
        subject_id="subject-001",
        quota_limit=1,
        slot_capacity=2,
        reservation_id="reservation-001",
    )
    second = _acquire(
        state_path,
        subject_id="subject-002",
        quota_limit=1,
        slot_capacity=2,
        reservation_id="reservation-002",
    )

    assert first["quota_used"] == 1
    assert first["quota_remaining"] == 0
    assert second["quota_used"] == 1
    assert second["quota_remaining"] == 0
    assert _read_state(state_path)["quota_usage"] == {
        "subject-001": {"window-001": 1},
        "subject-002": {"window-001": 1},
    }


def test_independent_windows_have_independent_quota_usage(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"

    first = _acquire(
        state_path,
        window_id="window-001",
        quota_limit=1,
        slot_capacity=2,
        reservation_id="reservation-001",
    )
    second = _acquire(
        state_path,
        window_id="window-002",
        quota_limit=1,
        slot_capacity=2,
        reservation_id="reservation-002",
    )

    assert first["quota_used"] == 1
    assert first["quota_remaining"] == 0
    assert second["quota_used"] == 1
    assert second["quota_remaining"] == 0
    assert _read_state(state_path)["quota_usage"] == {
        "subject-001": {
            "window-001": 1,
            "window-002": 1,
        },
    }


@pytest.mark.parametrize(
    ("quota_limit", "slot_capacity"),
    [
        (0, 1),
        (-1, 1),
        (1, 0),
        (1, -1),
        (True, 1),
        (1, False),
    ],
)
def test_invalid_policy_fails_before_state_mutation(
    tmp_path,
    quota_limit,
    slot_capacity,
):
    state_path = tmp_path / "quota_slot_state.json"

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _acquire(
            state_path,
            quota_limit=quota_limit,
            slot_capacity=slot_capacity,
        )

    assert exc_info.value.reason_code == "INVALID_POLICY"
    assert not state_path.exists()


@pytest.mark.parametrize(
    ("subject_id", "window_id"),
    [
        ("", "window-001"),
        ("   ", "window-001"),
        ("subject-001", ""),
        ("subject-001", "   "),
    ],
)
def test_invalid_request_fails_before_state_mutation(
    tmp_path,
    subject_id,
    window_id,
):
    state_path = tmp_path / "quota_slot_state.json"

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _acquire(
            state_path,
            subject_id=subject_id,
            window_id=window_id,
        )

    assert exc_info.value.reason_code == "INVALID_REQUEST"
    assert not state_path.exists()


@pytest.mark.parametrize("reservation_id", [None, "", "   ", 123])
def test_invalid_generated_reservation_id_fails_before_state_mutation(
    tmp_path,
    reservation_id,
):
    state_path = tmp_path / "quota_slot_state.json"

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _acquire(state_path, reservation_id=reservation_id)

    assert exc_info.value.reason_code == "INVALID_REQUEST"
    assert not state_path.exists()


@pytest.mark.parametrize("reservation_id", [None, "", "   ", 123])
def test_invalid_release_reservation_id_fails_before_state_mutation(
    tmp_path,
    reservation_id,
):
    state_path = tmp_path / "quota_slot_state.json"

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _release(state_path, reservation_id=reservation_id)

    assert exc_info.value.reason_code == "INVALID_REQUEST"
    assert not state_path.exists()


def test_malformed_json_state_fails_closed_without_overwrite(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"
    malformed_state = "{not valid json"
    state_path.write_text(malformed_state)

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _acquire(state_path)

    assert exc_info.value.reason_code == "STATE_CORRUPT"
    assert state_path.read_text() == malformed_state


def test_incompatible_schema_fails_closed_without_reset(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"
    incompatible_state = {
        "schema_version": 2,
        "quota_usage": {},
        "reservations": {},
    }
    original_text = json.dumps(incompatible_state, indent=2)
    state_path.write_text(original_text)

    with pytest.raises(QuotaSlotRejected) as exc_info:
        _acquire(state_path)

    assert exc_info.value.reason_code == "STATE_CORRUPT"
    assert state_path.read_text() == original_text


@pytest.mark.parametrize(
    ("case", "state"),
    [
        ("top-level-list", []),
        (
            "schema-boolean",
            {
                "schema_version": True,
                "quota_usage": {},
                "reservations": {},
            },
        ),
        (
            "quota-usage-not-object",
            {
                "schema_version": 1,
                "quota_usage": [],
                "reservations": {},
            },
        ),
        (
            "subject-windows-not-object",
            {
                "schema_version": 1,
                "quota_usage": {"subject-001": []},
                "reservations": {},
            },
        ),
        (
            "quota-usage-boolean",
            {
                "schema_version": 1,
                "quota_usage": {"subject-001": {"window-001": True}},
                "reservations": {},
            },
        ),
        (
            "quota-usage-negative",
            {
                "schema_version": 1,
                "quota_usage": {"subject-001": {"window-001": -1}},
                "reservations": {},
            },
        ),
        (
            "reservations-not-object",
            {
                "schema_version": 1,
                "quota_usage": {},
                "reservations": [],
            },
        ),
        (
            "reservation-record-not-object",
            {
                "schema_version": 1,
                "quota_usage": {},
                "reservations": {"reservation-001": []},
            },
        ),
        (
            "reservation-id-mismatch",
            _valid_state_with_reservation(reservation_id="reservation-002"),
        ),
        (
            "reservation-state-invalid",
            _valid_state_with_reservation(state="PENDING"),
        ),
        (
            "acquired-at-invalid",
            _valid_state_with_reservation(acquired_at=None),
        ),
        (
            "released-at-missing",
            _without_reservation_field("released_at"),
        ),
        (
            "active-has-release-time",
            _valid_state_with_reservation(
                released_at="2026-07-14T16:05:00"
            ),
        ),
        (
            "released-missing-release-time",
            _valid_state_with_reservation(state="RELEASED"),
        ),
    ],
)
def test_malformed_state_shapes_fail_closed_without_overwrite(
    tmp_path,
    case,
    state,
):
    state_path = tmp_path / f"{case}.json"
    original_text = json.dumps(state, indent=2)
    state_path.write_text(original_text)

    with pytest.raises(QuotaSlotRejected) as exc_info:
        read_quota_slot_state(state_path)

    assert exc_info.value.reason_code == "STATE_CORRUPT"
    assert state_path.read_text() == original_text


def test_importing_quota_slot_engine_has_no_side_effects(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delitem(
        sys.modules,
        "engine.quota_slot_engine_v4",
        raising=False,
    )

    module = importlib.import_module("engine.quota_slot_engine_v4")

    assert hasattr(module, "acquire_quota_slot_v4")
    assert hasattr(module, "release_quota_slot_v4")
    assert not Path("data").exists()


def test_write_quota_slot_state_atomic_replaces_target(tmp_path):
    state_path = tmp_path / "quota_slot_state.json"
    state_path.write_text("old state")
    state = {
        "schema_version": 1,
        "quota_usage": {},
        "reservations": {},
    }

    result = write_quota_slot_state_atomic(state, state_path)

    assert result == state_path
    assert _read_state(state_path) == state
    assert not (tmp_path / "quota_slot_state.json.tmp").exists()


def test_atomic_write_rejects_invalid_state_before_creating_parent(
    tmp_path,
):
    state_path = tmp_path / "new-parent" / "quota_slot_state.json"
    invalid_state = {
        "schema_version": 1,
        "quota_usage": [],
        "reservations": {},
    }

    with pytest.raises(QuotaSlotRejected) as exc_info:
        write_quota_slot_state_atomic(invalid_state, state_path)

    assert exc_info.value.reason_code == "STATE_CORRUPT"
    assert not state_path.parent.exists()
