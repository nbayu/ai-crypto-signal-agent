"""Deterministic one-job E6 production cadence selection and durable claim."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable, Final, Mapping

from engine.active_signal_ledger_v1 import ENTRY_ACTIVE, load_ledger
from engine.e6_production_cycle_input_v1 import (
    DUE_WINDOW_ALREADY_HANDLED,
    MODE_JOB_SELECTED,
    NO_MODE_JOB_DUE,
    E6ProductionDispatchDecisionV1,
    build_e6_production_dispatch_decision_v1,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_fetch_budget_cadence_v1 import (
    MODE_FETCH_CADENCE_POLICY_VERSION,
    CadenceDueJobV1,
    CadenceDueWindowV1,
    DailyCadencePlanV1,
    admit_cadence_start,
    build_daily_cadence_plan,
)
from engine.telegram_owner_control_state_v1 import load_state


E6_PRODUCTION_DISPATCH_LEDGER_SCHEMA_V1: Final = (
    "ai-crypto-signal-agent.e6-production-dispatch-ledger.v1"
)
E6_PRODUCTION_DISPATCH_LEDGER_POLICY_V1: Final = (
    "e6-production-mode-dispatch-ledger-policy-v1"
)
E6_PRODUCTION_DISPATCH_RELATIVE_PATH_V1: Final = Path(
    "e6-production-v1/dispatch/e6-mode-dispatch-ledger-v1.json"
)
_OCCURRENCE_DOMAIN: Final = "e6-production-due-window-occurrence-v1"
_COLLISION_DOMAIN: Final = "e6-production-due-window-collision-v1"
_UTC: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z"
)
_UTC_DAY: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_SHA1: Final = re.compile(r"[0-9a-f]{40}\Z")
_SHA256: Final = re.compile(r"[0-9a-f]{64}\Z")
_OCCURRENCE: Final = re.compile(r"e6dw1:[0-9a-f]{64}\Z")
_SAFE_JOB: Final = re.compile(r"[A-Z0-9][A-Z0-9._:+-]{0,159}\Z")
_ERROR: Final = "INVALID_E6_PRODUCTION_MODE_DISPATCH"


class E6ProductionModeDispatchErrorV1(ValueError):
    """Sanitized fail-closed dispatch or persistence rejection."""

    def __init__(self) -> None:
        self.code = _ERROR
        super().__init__(_ERROR)


def _invalid() -> None:
    raise E6ProductionModeDispatchErrorV1() from None


def _require(condition: bool) -> None:
    if not condition:
        _invalid()


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        _invalid()


def _digest(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _observed(value: object) -> tuple[str, datetime]:
    _require(type(value) is str and _UTC.fullmatch(value) is not None)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        _invalid()
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return value, parsed


def _validated_root_and_inputs(
    *,
    active_ledger_path: object,
    owner_control_state_path: object,
    authorized_state_root: object,
) -> tuple[Path, Path, Path]:
    _require(
        isinstance(active_ledger_path, Path)
        and isinstance(owner_control_state_path, Path)
        and isinstance(authorized_state_root, Path)
    )
    active = active_ledger_path
    owner = owner_control_state_path
    root = authorized_state_root
    _require(root.is_absolute() and active.is_absolute() and owner.is_absolute())
    _require(Path(os.path.normpath(str(root))) == root)
    _require(Path(os.path.normpath(str(active))) == active)
    _require(Path(os.path.normpath(str(owner))) == owner)
    owner_blueprint = active.parent
    _require(
        owner.parent == owner_blueprint
        and owner_blueprint.name == "owner-blueprint"
        and owner_blueprint.parent == root
    )
    _require(root.exists() and root.is_dir() and not root.is_symlink())
    _require(
        owner_blueprint.exists()
        and owner_blueprint.is_dir()
        and not owner_blueprint.is_symlink()
    )
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current = current / part
        _require(not current.is_symlink())
    _require(not owner_blueprint.is_symlink())
    return active, owner, root


def derive_e6_production_dispatch_ledger_path_v1(
    *, authorized_state_root: Path
) -> Path:
    """Derive the single versioned ledger path beneath an admitted root."""

    _require(
        isinstance(authorized_state_root, Path)
        and authorized_state_root.is_absolute()
    )
    return authorized_state_root / E6_PRODUCTION_DISPATCH_RELATIVE_PATH_V1


@dataclass(frozen=True, slots=True)
class E6ProductionDispatchDayV1:
    utc_date: str
    occurrence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require(type(self.utc_date) is str and _UTC_DAY.fullmatch(self.utc_date) is not None)
        _require(type(self.occurrence_ids) in (tuple, list))
        copied = tuple(self.occurrence_ids)
        _require(
            len(copied) == len(set(copied))
            and all(type(item) is str and _OCCURRENCE.fullmatch(item) for item in copied)
        )
        object.__setattr__(self, "occurrence_ids", tuple(sorted(copied)))

    def to_mapping(self) -> dict[str, object]:
        return {"utc_date": self.utc_date, "occurrence_ids": list(self.occurrence_ids)}


@dataclass(frozen=True, slots=True)
class E6ProductionDispatchLedgerV1:
    schema_version: str
    policy_version: str
    revision: int
    utc_days: tuple[E6ProductionDispatchDayV1, ...]
    claimed_occurrence_ids: tuple[str, ...]
    last_selected_job_by_collision_sha256: tuple[tuple[str, str], ...]
    updated_at: str
    state_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(self.schema_version == E6_PRODUCTION_DISPATCH_LEDGER_SCHEMA_V1)
            _require(self.policy_version == E6_PRODUCTION_DISPATCH_LEDGER_POLICY_V1)
            _require(type(self.revision) is int and self.revision >= 0)
            _observed(self.updated_at)
            _require(type(self.utc_days) in (tuple, list))
            days = tuple(self.utc_days)
            _require(all(type(day) is E6ProductionDispatchDayV1 for day in days))
            _require(tuple(day.utc_date for day in days) == tuple(sorted(day.utc_date for day in days)))
            _require(len(days) <= 2 and len({day.utc_date for day in days}) == len(days))
            object.__setattr__(self, "utc_days", days)
            flattened = tuple(sorted(item for day in days for item in day.occurrence_ids))
            _require(type(self.claimed_occurrence_ids) in (tuple, list))
            _require(tuple(self.claimed_occurrence_ids) == flattened)
            object.__setattr__(self, "claimed_occurrence_ids", flattened)
            _require(type(self.last_selected_job_by_collision_sha256) in (tuple, list))
            rotations = tuple(tuple(item) for item in self.last_selected_job_by_collision_sha256)
            _require(
                all(
                    len(item) == 2
                    and type(item[0]) is str
                    and _SHA256.fullmatch(item[0])
                    and type(item[1]) is str
                    and _SAFE_JOB.fullmatch(item[1])
                    for item in rotations
                )
            )
            _require(tuple(sorted(rotations)) == rotations)
            _require(len({item[0] for item in rotations}) == len(rotations))
            object.__setattr__(self, "last_selected_job_by_collision_sha256", rotations)
            _require(type(self.state_sha256) is str and _SHA256.fullmatch(self.state_sha256) is not None)
            _require(self.state_sha256 == _digest(self._content_mapping()))
        except E6ProductionModeDispatchErrorV1:
            raise
        except Exception:
            _invalid()

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "revision": self.revision,
            "utc_days": [day.to_mapping() for day in self.utc_days],
            "claimed_occurrence_ids": list(self.claimed_occurrence_ids),
            "last_selected_job_by_collision_sha256": [
                {"collision_sha256": key, "job_id": job}
                for key, job in self.last_selected_job_by_collision_sha256
            ],
            "updated_at": self.updated_at,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["state_sha256"] = self.state_sha256
        return mapping


def _new_ledger(*, observed_at: str) -> E6ProductionDispatchLedgerV1:
    content = {
        "schema_version": E6_PRODUCTION_DISPATCH_LEDGER_SCHEMA_V1,
        "policy_version": E6_PRODUCTION_DISPATCH_LEDGER_POLICY_V1,
        "revision": 0,
        "utc_days": (),
        "claimed_occurrence_ids": (),
        "last_selected_job_by_collision_sha256": (),
        "updated_at": observed_at,
    }
    provisional = E6ProductionDispatchLedgerV1.__new__(E6ProductionDispatchLedgerV1)
    for key, value in content.items():
        object.__setattr__(provisional, key, value)
    object.__setattr__(provisional, "state_sha256", "0" * 64)
    return E6ProductionDispatchLedgerV1(**content, state_sha256=_digest(provisional._content_mapping()))


def _ledger_from_mapping(value: object) -> E6ProductionDispatchLedgerV1:
    _require(type(value) is dict)
    try:
        days = tuple(E6ProductionDispatchDayV1(**item) for item in value["utc_days"])
        rotations = tuple(
            (item["collision_sha256"], item["job_id"])
            for item in value["last_selected_job_by_collision_sha256"]
        )
        return E6ProductionDispatchLedgerV1(
            **{
                **value,
                "utc_days": days,
                "claimed_occurrence_ids": tuple(value["claimed_occurrence_ids"]),
                "last_selected_job_by_collision_sha256": rotations,
            }
        )
    except E6ProductionModeDispatchErrorV1:
        raise
    except Exception:
        _invalid()


def _load_dispatch_ledger(path: Path, *, observed_at: str) -> E6ProductionDispatchLedgerV1:
    if not path.exists():
        return _new_ledger(observed_at=observed_at)
    _require(path.is_file() and not path.is_symlink())
    try:
        return _ledger_from_mapping(json.loads(path.read_text(encoding="utf-8")))
    except E6ProductionModeDispatchErrorV1:
        raise
    except Exception:
        _invalid()


def _secure_directories(root: Path, target: Path) -> None:
    current = root
    for part in target.parent.relative_to(root).parts:
        current = current / part
        if current.exists():
            _require(current.is_dir() and not current.is_symlink())
        else:
            current.mkdir(mode=0o700)
        os.chmod(current, 0o700)


def _write_dispatch_ledger(path: Path, ledger: E6ProductionDispatchLedgerV1) -> None:
    payload = (_canonical_json(ledger.to_mapping()) + "\n").encode("utf-8")
    descriptor: int | None = None
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        os.chmod(path, 0o600)
    except Exception:
        _invalid()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _occurrence_id(*, utc_date: str, window: CadenceDueWindowV1, job: CadenceDueJobV1) -> str:
    payload = {
        "domain": _OCCURRENCE_DOMAIN,
        "cadence_policy_version": MODE_FETCH_CADENCE_POLICY_VERSION,
        "utc_date": utc_date,
        "due_second_utc": window.due_second_utc,
        "job_id": job.job_id,
        "due_timeframes": list(job.due_timeframes),
    }
    return f"e6dw1:{_digest(payload)}"


def _collision_sha256(window: CadenceDueWindowV1) -> str:
    return _digest(
        {
            "domain": _COLLISION_DOMAIN,
            "cadence_policy_version": MODE_FETCH_CADENCE_POLICY_VERSION,
            "due_second_utc": window.due_second_utc,
            "ordered_job_ids": [job.job_id for job in window.ordered_jobs],
        }
    )


def _due_window(
    plan: DailyCadencePlanV1,
    observed: datetime,
    cadence_admitter: Callable[..., object],
) -> tuple[str, CadenceDueWindowV1] | None:
    observed_second = observed.hour * 3600 + observed.minute * 60 + observed.second
    candidates: list[tuple[int, str, CadenceDueWindowV1]] = []
    for window in plan.windows:
        delay = observed_second - window.due_second_utc
        day = observed.date()
        if delay < 0:
            delay += 24 * 60 * 60
            day -= timedelta(days=1)
        admission = cadence_admitter(delay_seconds=delay)
        if getattr(admission, "admitted", None) is True:
            candidates.append((delay, day.isoformat(), window))
    if not candidates:
        return None
    _delay, utc_date, window = min(candidates, key=lambda item: (item[0], item[2].due_second_utc))
    return utc_date, window


def _claim(
    *,
    ledger: E6ProductionDispatchLedgerV1,
    utc_date: str,
    occurrence_id: str,
    collision_sha256: str,
    selected_job_id: str,
    observed_at: str,
) -> E6ProductionDispatchLedgerV1:
    previous = (datetime.strptime(utc_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
    retained = {day.utc_date: list(day.occurrence_ids) for day in ledger.utc_days if day.utc_date in {utc_date, previous}}
    retained.setdefault(utc_date, [])
    _require(occurrence_id not in retained[utc_date])
    retained[utc_date].append(occurrence_id)
    days = tuple(
        E6ProductionDispatchDayV1(utc_date=day, occurrence_ids=tuple(values))
        for day, values in sorted(retained.items())
    )
    claims = tuple(sorted(item for day in days for item in day.occurrence_ids))
    rotations = dict(ledger.last_selected_job_by_collision_sha256)
    rotations[collision_sha256] = selected_job_id
    content = {
        "schema_version": E6_PRODUCTION_DISPATCH_LEDGER_SCHEMA_V1,
        "policy_version": E6_PRODUCTION_DISPATCH_LEDGER_POLICY_V1,
        "revision": ledger.revision + 1,
        "utc_days": days,
        "claimed_occurrence_ids": claims,
        "last_selected_job_by_collision_sha256": tuple(sorted(rotations.items())),
        "updated_at": observed_at,
    }
    provisional = E6ProductionDispatchLedgerV1.__new__(E6ProductionDispatchLedgerV1)
    for key, value in content.items():
        object.__setattr__(provisional, key, value)
    object.__setattr__(provisional, "state_sha256", "0" * 64)
    return E6ProductionDispatchLedgerV1(**content, state_sha256=_digest(provisional._content_mapping()))


def build_e6_production_mode_dispatch_v1(
    *,
    source_commit: str,
    outcome_invocation_id: str,
    observed_at: str,
    active_ledger_path: Path,
    owner_control_state_path: Path,
    authorized_state_root: Path,
    cadence_plan_builder: Callable[..., DailyCadencePlanV1] = build_daily_cadence_plan,
    cadence_admitter: Callable[..., object] = admit_cadence_start,
    active_ledger_loader: Callable[[Path], Mapping[str, object]] = load_ledger,
    owner_state_loader: Callable[[Path], Mapping[str, object]] = load_state,
) -> E6ProductionDispatchDecisionV1:
    """Select and durably claim at most one due job with no retry."""

    _require(type(source_commit) is str and _SHA1.fullmatch(source_commit) is not None)
    canonical_observed, observed = _observed(observed_at)
    active_path, owner_path, root = _validated_root_and_inputs(
        active_ledger_path=active_ledger_path,
        owner_control_state_path=owner_control_state_path,
        authorized_state_root=authorized_state_root,
    )
    _require(
        callable(cadence_plan_builder)
        and callable(cadence_admitter)
        and callable(active_ledger_loader)
        and callable(owner_state_loader)
    )
    try:
        active = active_ledger_loader(active_path)
        owner = owner_state_loader(owner_path)
    except Exception:
        _invalid()
    _require(isinstance(active, Mapping) and isinstance(owner, Mapping))
    signals = active.get("signals")
    _require(isinstance(signals, Mapping))
    armed_modes = tuple(
        sorted(
            {
                record["mode"]
                for record in signals.values()
                if isinstance(record, Mapping) and record.get("state") == ENTRY_ACTIVE
            }
        )
    )
    try:
        plan = cadence_plan_builder(armed_modes=armed_modes)
    except Exception:
        _invalid()
    _require(type(plan) is DailyCadencePlanV1)
    due = _due_window(plan, observed, cadence_admitter)
    if due is None:
        return build_e6_production_dispatch_decision_v1(
            source_commit=source_commit,
            outcome_invocation_id=outcome_invocation_id,
            observed_at=canonical_observed,
            disposition=NO_MODE_JOB_DUE,
            reason_code=NO_MODE_JOB_DUE,
        )

    utc_date, window = due
    path = derive_e6_production_dispatch_ledger_path_v1(authorized_state_root=root)
    _secure_directories(root, path)
    lock_path = path.with_name(path.name + ".lock")
    descriptor: int | None = None
    try:
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = _load_dispatch_ledger(path, observed_at=canonical_observed)
        occurrence_by_job = {
            job.job_id: _occurrence_id(utc_date=utc_date, window=window, job=job)
            for job in window.ordered_jobs
        }
        claimed = set(ledger.claimed_occurrence_ids)
        for job in window.ordered_jobs:
            occurrence = occurrence_by_job[job.job_id]
            if occurrence in claimed:
                return build_e6_production_dispatch_decision_v1(
                    source_commit=source_commit,
                    outcome_invocation_id=outcome_invocation_id,
                    observed_at=canonical_observed,
                    disposition=DUE_WINDOW_ALREADY_HANDLED,
                    reason_code=DUE_WINDOW_ALREADY_HANDLED,
                    mode=job.mode,
                    due_job_id=job.job_id,
                    due_window_occurrence_id=occurrence,
                    mode_lineage_sha256=build_mode_audit_lineage(job.mode).lineage_sha256,
                )
        collision = _collision_sha256(window)
        jobs = tuple(window.ordered_jobs)
        previous_job = dict(ledger.last_selected_job_by_collision_sha256).get(collision)
        start = 0
        if previous_job is not None:
            prior_index = next((index for index, job in enumerate(jobs) if job.job_id == previous_job), -1)
            start = 0 if prior_index < 0 else (prior_index + 1) % len(jobs)
        selected = jobs[start]
        occurrence = occurrence_by_job[selected.job_id]
        updated = _claim(
            ledger=ledger,
            utc_date=utc_date,
            occurrence_id=occurrence,
            collision_sha256=collision,
            selected_job_id=selected.job_id,
            observed_at=canonical_observed,
        )
        _write_dispatch_ledger(path, updated)
        return build_e6_production_dispatch_decision_v1(
            source_commit=source_commit,
            outcome_invocation_id=outcome_invocation_id,
            observed_at=canonical_observed,
            disposition=MODE_JOB_SELECTED,
            reason_code=MODE_JOB_SELECTED,
            mode=selected.mode,
            due_job_id=selected.job_id,
            due_window_occurrence_id=occurrence,
            mode_lineage_sha256=build_mode_audit_lineage(selected.mode).lineage_sha256,
        )
    except BlockingIOError:
        _invalid()
    finally:
        if descriptor is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


__all__ = (
    "E6ProductionDispatchDayV1",
    "E6ProductionDispatchLedgerV1",
    "E6ProductionModeDispatchErrorV1",
    "build_e6_production_mode_dispatch_v1",
    "derive_e6_production_dispatch_ledger_path_v1",
)
