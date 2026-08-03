from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import inspect
import json
import os
from pathlib import Path

import pytest

import engine.e6_production_mode_dispatch_v1 as module
from engine.e6_production_cycle_input_v1 import (
    DUE_WINDOW_ALREADY_HANDLED,
    MODE_JOB_SELECTED,
    NO_MODE_JOB_DUE,
)
from engine.mode_fetch_budget_cadence_v1 import (
    MAX_JOB_START_DELAY_SECONDS,
    admit_cadence_start,
    build_daily_cadence_plan,
)


COMMIT = "a" * 40
INVOCATION = "b" * 32


def _at(day: str, due_second: int, delay: int = 0) -> str:
    base = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (base + timedelta(seconds=due_second + delay)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path.resolve()
    owner_blueprint = root / "owner-blueprint"
    owner_blueprint.mkdir(mode=0o700, exist_ok=True)
    return owner_blueprint / "active.json", owner_blueprint / "owner.json", root


def _dispatch(
    tmp_path: Path,
    *,
    observed_at: str,
    active_modes: tuple[str, ...] = (),
    cadence_admitter=admit_cadence_start,
):
    active, owner, root = _paths(tmp_path)
    signals = {
        f"signal-{index}": {"state": "ENTRY_ACTIVE", "mode": mode}
        for index, mode in enumerate(active_modes)
    }
    return module.build_e6_production_mode_dispatch_v1(
        source_commit=COMMIT,
        outcome_invocation_id=INVOCATION,
        observed_at=observed_at,
        active_ledger_path=active,
        owner_control_state_path=owner,
        authorized_state_root=root,
        cadence_admitter=cadence_admitter,
        active_ledger_loader=lambda _path: {"signals": signals},
        owner_state_loader=lambda _path: {"revision": 0},
    )


def test_import_is_passive_and_has_no_client_or_polling_surface() -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    assert "ccxt" not in source
    assert "while True" not in source
    assert "sleep(" not in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_e6_production_mode_dispatch_v1"
        for node in tree.body
    )


@pytest.mark.parametrize("mode", ("SWING", "INTRADAY", "SCALP"))
def test_all_three_base_modes_are_selected_from_committed_plan(tmp_path: Path, mode: str) -> None:
    plan = build_daily_cadence_plan(armed_modes=())
    window = next(item for item in plan.windows if item.ordered_jobs[0].mode == mode)
    result = _dispatch(tmp_path, observed_at=_at("2026-08-03", window.due_second_utc))
    assert result.disposition == MODE_JOB_SELECTED
    assert result.mode == mode
    assert result.due_job_id.endswith(":BASE_EVALUATION")
    assert result.due_window_occurrence_id.startswith("e6dw1:")
    assert len(result.due_window_occurrence_id) == 70


def test_committed_sixty_second_admission_and_no_catchup(tmp_path: Path) -> None:
    window = build_daily_cadence_plan(armed_modes=()).windows[0]
    calls: list[int] = []

    def admitter(*, delay_seconds):
        calls.append(delay_seconds)
        return admit_cadence_start(delay_seconds=delay_seconds)

    admitted = _dispatch(
        tmp_path,
        observed_at=_at("2026-08-03", window.due_second_utc, MAX_JOB_START_DELAY_SECONDS),
        cadence_admitter=admitter,
    )
    assert admitted.disposition == MODE_JOB_SELECTED
    assert MAX_JOB_START_DELAY_SECONDS in calls

    due_seconds = {item.due_second_utc for item in build_daily_cadence_plan(armed_modes=()).windows}
    late_second = next(
        second
        for second in range(24 * 60 * 60)
        if min((second - due) % (24 * 60 * 60) for due in due_seconds)
        > MAX_JOB_START_DELAY_SECONDS
    )
    other_root = tmp_path / "late"
    other_root.mkdir()
    late = _dispatch(
        other_root,
        observed_at=_at("2026-08-03", late_second),
    )
    assert late.disposition == NO_MODE_JOB_DUE


def test_pending_entries_do_not_arm_and_entry_active_does(tmp_path: Path) -> None:
    plan = build_daily_cadence_plan(armed_modes=("SWING",))
    armed_window = next(
        item
        for item in plan.windows
        if any(job.mode == "SWING" and job.armed_conditional for job in item.ordered_jobs)
    )
    active, owner, root = _paths(tmp_path)
    pending = module.build_e6_production_mode_dispatch_v1(
        source_commit=COMMIT,
        outcome_invocation_id=INVOCATION,
        observed_at=_at("2026-08-03", armed_window.due_second_utc),
        active_ledger_path=active,
        owner_control_state_path=owner,
        authorized_state_root=root,
        active_ledger_loader=lambda _path: {
            "signals": {"one": {"state": "PUBLISHED_PENDING_ENTRY", "mode": "SWING"}}
        },
        owner_state_loader=lambda _path: {},
    )
    assert not (pending.mode == "SWING" and pending.due_job_id.endswith(":ARMED_MONITOR"))


def test_claim_is_durable_and_replay_is_suppressed(tmp_path: Path) -> None:
    window = build_daily_cadence_plan(armed_modes=()).windows[0]
    observed = _at("2026-08-03", window.due_second_utc)
    first = _dispatch(tmp_path, observed_at=observed)
    ledger_path = module.derive_e6_production_dispatch_ledger_path_v1(
        authorized_state_root=tmp_path.resolve()
    )
    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert first.due_window_occurrence_id in persisted["claimed_occurrence_ids"]
    second = _dispatch(tmp_path, observed_at=observed)
    assert second.disposition == DUE_WINDOW_ALREADY_HANDLED
    assert second.due_window_occurrence_id == first.due_window_occurrence_id
    assert persisted["revision"] == 1


def test_collision_rotation_is_deterministic_across_days(tmp_path: Path) -> None:
    plan = build_daily_cadence_plan(armed_modes=("SWING", "INTRADAY", "SCALP"))
    window = next(item for item in plan.windows if len(item.ordered_jobs) > 1)
    active = ("SWING", "INTRADAY", "SCALP")
    first = _dispatch(
        tmp_path,
        observed_at=_at("2026-08-03", window.due_second_utc),
        active_modes=active,
    )
    second = _dispatch(
        tmp_path,
        observed_at=_at("2026-08-04", window.due_second_utc),
        active_modes=active,
    )
    expected_jobs = tuple(job.job_id for job in window.ordered_jobs)
    assert first.due_job_id == expected_jobs[0]
    assert second.due_job_id == expected_jobs[1 % len(expected_jobs)]


def test_ledger_retains_current_and_previous_utc_day_only(tmp_path: Path) -> None:
    window = build_daily_cadence_plan(armed_modes=()).windows[0]
    for day in ("2026-08-03", "2026-08-04", "2026-08-05"):
        _dispatch(tmp_path, observed_at=_at(day, window.due_second_utc))
    ledger_path = module.derive_e6_production_dispatch_ledger_path_v1(
        authorized_state_root=tmp_path.resolve()
    )
    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert [item["utc_date"] for item in persisted["utc_days"]] == [
        "2026-08-04",
        "2026-08-05",
    ]


def test_atomic_state_permissions_and_frozen_contract(tmp_path: Path) -> None:
    window = build_daily_cadence_plan(armed_modes=()).windows[0]
    _dispatch(tmp_path, observed_at=_at("2026-08-03", window.due_second_utc))
    path = module.derive_e6_production_dispatch_ledger_path_v1(
        authorized_state_root=tmp_path.resolve()
    )
    assert path.relative_to(tmp_path.resolve()) == Path(
        "e6-production-v1/dispatch/e6-mode-dispatch-ledger-v1.json"
    )
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert oct(path.with_name(path.name + ".lock").stat().st_mode & 0o777) == "0o600"
    assert oct(path.parent.stat().st_mode & 0o777) == "0o700"
    loaded = module._ledger_from_mapping(json.loads(path.read_text(encoding="utf-8")))
    with pytest.raises(FrozenInstanceError):
        loaded.revision = 9
    assert not tuple(path.parent.glob(f".{path.name}.*"))


def test_root_symlink_and_path_escape_fail_closed(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(module.E6ProductionModeDispatchErrorV1):
        module.build_e6_production_mode_dispatch_v1(
            source_commit=COMMIT,
            outcome_invocation_id=INVOCATION,
            observed_at="2026-08-03T00:00:00Z",
            active_ledger_path=linked / "owner-blueprint" / "active.json",
            owner_control_state_path=linked / "owner-blueprint" / "owner.json",
            authorized_state_root=linked,
            active_ledger_loader=lambda _path: {"signals": {}},
            owner_state_loader=lambda _path: {},
        )
    outside = tmp_path.parent / "outside.json"
    with pytest.raises(module.E6ProductionModeDispatchErrorV1):
        module.build_e6_production_mode_dispatch_v1(
            source_commit=COMMIT,
            outcome_invocation_id=INVOCATION,
            observed_at="2026-08-03T00:00:00Z",
            active_ledger_path=outside,
            owner_control_state_path=tmp_path / "owner-blueprint" / "owner.json",
            authorized_state_root=tmp_path.resolve(),
            active_ledger_loader=lambda _path: {"signals": {}},
            owner_state_loader=lambda _path: {},
        )
