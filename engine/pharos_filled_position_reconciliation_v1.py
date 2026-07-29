"""One-time, evidence-gated PHAROS owner-filled-position reconciliation.

This module has no transport, provider, exchange, order, or trading imports.
It verifies sealed root-only evidence, permanently drops privilege, validates
three exact state authorities, and uses only the existing passive registration
and owner-confirmed entry APIs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from engine import active_signal_ledger_v1 as active
from engine import passive_production_signal_flow_v1 as flow
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine.canonical_pair_v1 import normalize_pair
from engine.production_signal_artifact_v1 import read_publication_artifact
from engine.telegram_owner_control_state_v1 import load_state


RECONCILIATION_ID = "PFR-f90cf3a14a9de4225fa3b087357e8cc3ac26d4cacea10cc0840db21fda2534ec"
SIGNAL_ID = "PSG-f90cf3a14a9de4225fa3b087357e8cc3ac26d4cacea10cc0840db21fda2534ec"
DELIVERY_ID = "PDL-6976a63488e4cb18c7ecf9d053817c2504d495baf6ca2fe2f404b705fab04b43"
INCIDENT_ROOT = Path("/opt/ai-crypto-signal-agent-forensics/post-kmno-pharos-p1-post-repair-command-failure-audit-20260729T174654Z")
INCIDENT_MANIFEST_SHA256 = "3a757bf82bcc742e2eb441a1014c355062c347f5282520612d6bc808f6108bcb"
INSTALLED_RELEASE_REFERENCE_PATH = Path("/var/lib/ai-crypto-signal-agent/installed-release.path")
SCANNER_UNIT_PATH = Path("/etc/systemd/system/ai-crypto-signal-agent.service")
CONTROLLER_UNIT_PATH = Path("/etc/systemd/system/ai-crypto-signal-agent-telegram-control.service")
PUBLICATION_SHA256 = "cf8c43da3debc6b92122cf91d13620a01534ffcbb31fe289aa94f843407f32ea"
CONTROL_SHA256 = "3e5b77a9b5c0dcf318114947dd9b7a71b945c9506c373fcc96dc45ec21cc3925"
LEDGER_SHA256 = "55e791f2eb54b4bb5ed4240dd26362a773e08b40b69526fa53477a50fd89118b"
PUBLICATION_PATH = Path("/var/lib/ai-crypto-signal-agent/phase09r1/production-signals/publications/PSG-f90cf3a14a9de4225fa3b087357e8cc3ac26d4cacea10cc0840db21fda2534ec/PDL-6976a63488e4cb18c7ecf9d053817c2504d495baf6ca2fe2f404b705fab04b43.json")
CONTROL_PATH = Path("/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/telegram-owner-control-state-v1.json")
LEDGER_PATH = Path("/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/active-signal-ledger-v2.json")
CONTENT_SHA256 = "c9cd1857d72d921c20d830eee892d3548e64ed7ac7219626f03fe4715fd8dd4e"
SOURCE_PAYLOAD_SHA256 = "7dfd08ba4cba3dae81b64219fc1014e0a006dff2c21e1ea5fd1b4e7c20ceba20"
PUBLICATION_PAYLOAD_SHA256 = "d244702c8568a82a1f0cca056e47492f1f463c065d6606da774877b0490972fc"
OWNER_AUTHORIZATION_ID = "AUTHORIZE_PHAROS_POST_REPAIR_COMMAND_PATH_REPAIR_AND_FILLED_POSITION_RECONCILIATION_EXECUTION"
RESERVATION_TRANSITION_ID = "owner-publication-reconcile-pharos-f90cf3a14a9de4225fa3b087357e8cc3ac26d4cacea10cc0840db21fda2534ec"
ENTRY_TRANSITION_ID = "owner-filled-entry-reconcile-pharos-f90cf3a14a9de4225fa3b087357e8cc3ac26d4cacea10cc0840db21fda2534ec"
ENTRY_AT_AUTHORITY = "CAPTURE_UTC_ONCE_AFTER_ALL_PRECONDITIONS_BEFORE_FIRST_LEDGER_MUTATION"
RESULT_PATH = Path("/var/tmp/ai-crypto-signal-agent-pharos-reconciliation-PFR-f90cf3a14a9de4225fa3b087357e8cc3ac26d4cacea10cc0840db21fda2534ec.json")
INCIDENT_COMMAND_IDS = {
    "14795cd91e3f23fc0c0cdf76a103563e869c57c288a75ee30e0d233f07968a67",
    "30b9d2583960da3466f70585db7922aee468e580be9ef46b3d55d994fd1e02ee",
}


class ReconciliationError(RuntimeError):
    """Sanitized failure carrying the sealed process exit contract."""

    def __init__(self, exit_code: int, reason: str, *, effect_count: int = 0):
        self.exit_code = exit_code
        self.reason = reason
        self.effect_count = effect_count
        super().__init__(reason)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8") + b"\n"


def _no_symlink_chain(path: Path, *, exit_code: int = 13) -> None:
    current = path
    while True:
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise ReconciliationError(exit_code, "SYMLINK_PATH_REJECTED")
        except FileNotFoundError:
            pass
        if current.parent == current:
            return
        current = current.parent


def _read_regular(path: Path, *, uid: int | None = None, gid: int | None = None,
                  mode: int | None = None, exit_code: int = 13) -> bytes:
    _no_symlink_chain(path, exit_code=exit_code)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = None
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ReconciliationError(exit_code, "STATE_PATH_NOT_REGULAR")
        if uid is not None and metadata.st_uid != uid:
            raise ReconciliationError(exit_code, "STATE_OWNER_MISMATCH")
        if gid is not None and metadata.st_gid != gid:
            raise ReconciliationError(exit_code, "STATE_GROUP_MISMATCH")
        if mode is not None and stat.S_IMODE(metadata.st_mode) != mode:
            raise ReconciliationError(exit_code, "STATE_MODE_MISMATCH")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    except ReconciliationError:
        raise
    except OSError as exc:
        raise ReconciliationError(exit_code, "STATE_READ_FAILED") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def verify_incident_evidence_as_root(root: Path, expected_manifest_sha256: str) -> dict[str, Any]:
    """Verify the complete root-only incident seal before any state access."""
    if os.geteuid() != 0 or os.getegid() != 0:
        raise ReconciliationError(11, "ROOT_EVIDENCE_VERIFICATION_REQUIRED")
    if not root.is_absolute() or root != INCIDENT_ROOT:
        raise ReconciliationError(11, "INCIDENT_ROOT_MISMATCH")
    _no_symlink_chain(root, exit_code=11)
    metadata = root.stat()
    if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != 0
            or metadata.st_gid != 0 or stat.S_IMODE(metadata.st_mode) != 0o700):
        raise ReconciliationError(11, "INCIDENT_ROOT_METADATA_INVALID")
    manifest_path = root / "evidence-sha256-manifest.txt"
    manifest = _read_regular(manifest_path, uid=0, gid=0, mode=0o400, exit_code=11)
    if expected_manifest_sha256 != INCIDENT_MANIFEST_SHA256 or _sha256(manifest) != expected_manifest_sha256:
        raise ReconciliationError(11, "INCIDENT_MANIFEST_HASH_MISMATCH")
    try:
        lines = manifest.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ReconciliationError(11, "INCIDENT_MANIFEST_INVALID") from exc
    if len(lines) != 18:
        raise ReconciliationError(11, "INCIDENT_MANIFEST_ENTRY_COUNT_MISMATCH")
    verified = []
    for line in lines:
        if len(line) < 67 or line[64:66] != "  ":
            raise ReconciliationError(11, "INCIDENT_MANIFEST_INVALID")
        expected_hash, relative = line[:64], line[66:]
        if (len(expected_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_hash)
                or not relative or Path(relative).name != relative
                or relative == manifest_path.name):
            raise ReconciliationError(11, "INCIDENT_MANIFEST_INVALID")
        payload = _read_regular(root / relative, uid=0, gid=0, exit_code=11)
        if _sha256(payload) != expected_hash:
            raise ReconciliationError(11, "INCIDENT_ENTRY_HASH_MISMATCH")
        verified.append(relative)
    return {
        "incident_manifest_sha256": expected_manifest_sha256,
        "incident_evidence_entry_count": len(verified) + 1,
        "root_only_incident_seal_verification": "PASS",
    }


def _systemd_properties(unit: str, properties: Sequence[str]) -> dict[str, str]:
    command = ["/usr/bin/systemctl", "show", unit]
    for name in properties:
        command.extend(["-p", name])
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReconciliationError(13, "RUNTIME_PRECONDITION_UNAVAILABLE") from exc
    if completed.returncode != 0:
        raise ReconciliationError(13, "RUNTIME_PRECONDITION_UNAVAILABLE")
    values = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    return values


def _process_count(markers: Sequence[bytes]) -> int:
    count = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        if any(marker in command for marker in markers):
            count += 1
    return count


def verify_runtime_quiescence() -> dict[str, Any]:
    timer = _systemd_properties(
        "ai-crypto-signal-agent.timer",
        ("UnitFileState", "ActiveState", "NextElapseUSecRealtime"),
    )
    scanner = _systemd_properties(
        "ai-crypto-signal-agent.service", ("ActiveState", "Result", "MainPID"),
    )
    controller = _systemd_properties(
        "ai-crypto-signal-agent-telegram-control.service",
        ("ActiveState", "Result", "MainPID"),
    )
    scanner_count = _process_count((b"engine.run_production_signal_v1",))
    controller_count = _process_count((b"engine.run_telegram_owner_control_v1",))
    if timer != {
        "UnitFileState": "disabled", "ActiveState": "inactive",
        "NextElapseUSecRealtime": "",
    }:
        raise ReconciliationError(13, "TIMER_PRECONDITION_FAILED")
    if (scanner.get("ActiveState") != "inactive" or scanner.get("Result") == "failed"
            or scanner.get("MainPID") != "0" or scanner_count != 0):
        raise ReconciliationError(13, "SCANNER_PRECONDITION_FAILED")
    if (controller.get("ActiveState") != "inactive" or controller.get("Result") == "failed"
            or controller.get("MainPID") != "0" or controller_count != 0):
        raise ReconciliationError(13, "CONTROLLER_PRECONDITION_FAILED")
    return {
        "timer_disabled_inactive_no_next_elapse": True,
        "scanner_process_count": scanner_count,
        "controller_process_count": controller_count,
    }


def permanently_drop_privileges(uid: int, gid: int) -> dict[str, Any]:
    """Clear supplementary groups and irreversibly become the state owner."""
    if os.geteuid() != 0 or os.getegid() != 0 or uid != 999 or gid != 987:
        raise ReconciliationError(12, "PRIVILEGE_DROP_PRECONDITION_FAILED")
    try:
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)
    except OSError as exc:
        raise ReconciliationError(12, "PRIVILEGE_DROP_FAILED") from exc
    uids = os.getresuid() if hasattr(os, "getresuid") else (os.getuid(), os.geteuid(), uid)
    gids = os.getresgid() if hasattr(os, "getresgid") else (os.getgid(), os.getegid(), gid)
    if uids != (uid, uid, uid) or gids != (gid, gid, gid) or os.getgroups():
        raise ReconciliationError(12, "PRIVILEGE_DROP_VERIFICATION_FAILED")
    os.umask(0o077)
    return {
        "permanent_privilege_drop_before_state_access": "PASS",
        "state_access_uid": os.geteuid(),
        "state_access_gid": os.getegid(),
        "supplementary_group_count": 0,
    }


def verify_release_parity(
    installed_release_reference_path: Path,
    scanner_unit_path: Path,
    controller_unit_path: Path,
) -> dict[str, Any]:
    """Prove both installed execution chains use the referenced release."""
    reference = _read_regular(
        installed_release_reference_path, uid=0, gid=0, mode=0o400,
    )
    try:
        release_lines = reference.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ReconciliationError(13, "RELEASE_REFERENCE_INVALID") from exc
    if len(release_lines) != 1 or re.fullmatch(
        r"/opt/ai-crypto-signal-agent-releases/[0-9a-f]{40}", release_lines[0],
    ) is None:
        raise ReconciliationError(13, "RELEASE_REFERENCE_INVALID")
    release_root = release_lines[0]
    scanner = _read_regular(scanner_unit_path, uid=0, gid=0, mode=0o644)
    controller = _read_regular(controller_unit_path, uid=0, gid=0, mode=0o644)
    try:
        scanner_text = scanner.decode("utf-8")
        controller_text = controller.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReconciliationError(13, "UNIT_RELEASE_PARITY_FAILED") from exc
    scanner_exec = (
        f"ExecStart={release_root}/deploy/operational_v1/bin/"
        "ai-crypto-signal-agent-run-once"
    )
    controller_exec = (
        f"ExecStart={release_root}/deploy/operational_v1/bin/"
        "ai-crypto-signal-agent-telegram-control"
    )
    condition = f"ConditionPathExists={release_root}/.f4-release-manifest"
    if (
        scanner_text.splitlines().count(scanner_exec) != 1
        or controller_text.splitlines().count(controller_exec) != 1
        or scanner_text.splitlines().count(condition) != 1
        or controller_text.splitlines().count(condition) != 1
    ):
        raise ReconciliationError(13, "UNIT_RELEASE_PARITY_FAILED")
    return {"release_root": release_root, "unit_release_parity": "PASS"}


EXISTING_SIGNAL_ID = "PSG-59f5492f4758cb93086bf57d997cf6f4239bd4a54ba817fb46bb1817f753acb3"
EXISTING_DELIVERY_ID = "PDL-c80055e0e435c83a23981324a444d653df1bed7d5cae6eee4367ec143631d6f8"
EXISTING_PAIR = "KMNO/USDT"
EXISTING_LAST_TRANSITION_ID = "owner-filled-entry-reconcile-062397b46c377ceb7e5b17d4962d4392643d5f57a4bc6516c0efa401a2c602a2"


def _capacity_and_pair(ledger: Mapping[str, Any], canonical_pair: str) -> dict[str, int]:
    capacity = active.inspect_capacity(ledger)
    owners = sum(
        1 for record in ledger["signals"].values()
        if record["state"] == active.ENTRY_ACTIVE
        and normalize_pair(record["symbol"]) == canonical_pair
    )
    return {
        "swing_active": capacity["active_by_mode"][active.SWING],
        "swing_available": capacity["remaining_by_mode"][active.SWING],
        "total_active": capacity["total_active"],
        "pair_owners": owners,
    }


def _validate_publication(
    publication: Mapping[str, Any], *, signal_id: str, delivery_id: str,
    telegram_message_id: int, canonical_pair: str, style: str, direction: str,
    expected_publication_timestamp: str, expected_delivery_timestamp: str,
    expected_valid_until: str, expected_content_sha256: str,
    expected_source_payload_sha256: str,
    expected_publication_payload_sha256: str,
) -> None:
    payload = publication.get("publication_payload")
    receipt = publication.get("delivery_receipt")
    if not isinstance(payload, Mapping) or not isinstance(receipt, Mapping):
        raise ReconciliationError(14, "PUBLICATION_IDENTITY_INVALID")
    expected = (
        publication.get("signal_id") == signal_id == SIGNAL_ID,
        publication.get("delivery_id") == delivery_id == DELIVERY_ID,
        publication.get("delivery_state") == "DELIVERY_SUCCEEDED",
        publication.get("mode") == style == "SWING",
        normalize_pair(payload.get("symbol")) == canonical_pair == "PHAROS/USDT",
        payload.get("side") == direction == "LONG",
        payload.get("signal_id") == signal_id,
        payload.get("mode") == style,
        publication.get("published_at") == expected_publication_timestamp,
        expected_publication_timestamp == "2026-07-29T17:17:42Z",
        receipt.get("delivered_at") == expected_delivery_timestamp,
        expected_delivery_timestamp == "2026-07-29T17:17:44Z",
        str(receipt.get("external_delivery_id")) == str(telegram_message_id) == "932",
        payload.get("valid_until") == expected_valid_until == "2026-12-31T23:59:59Z",
        publication.get("content_hash") == expected_content_sha256 == CONTENT_SHA256,
        publication.get("source_payload_hash") == expected_source_payload_sha256 == SOURCE_PAYLOAD_SHA256,
        publication.get("publication_payload_hash") == expected_publication_payload_sha256 == PUBLICATION_PAYLOAD_SHA256,
        publication.get("order_execution") == "PROHIBITED",
        publication.get("capital_exposure") == "NONE",
    )
    if not all(expected):
        raise ReconciliationError(14, "PUBLICATION_IDENTITY_INVALID")


def _validate_control(
    state: Mapping[str, Any], *, signal_id: str, telegram_message_id: int,
    canonical_pair: str, style: str, expected_revision: int,
    expected_last_update_id: int,
) -> None:
    if (
        state.get("revision") != expected_revision
        or expected_revision != 32
        or state.get("last_update_id") != expected_last_update_id
        or expected_last_update_id != 469110663
    ):
        raise ReconciliationError(14, "CONTROL_STATE_REVISION_INVALID")
    matches = [
        binding for key, binding in state["signal_message_bindings"].items()
        if key.endswith(f":{telegram_message_id}") and isinstance(binding, Mapping)
    ]
    if len(matches) != 1:
        raise ReconciliationError(14, "TELEGRAM_BINDING_INVALID")
    binding = matches[0]
    if not (
        binding.get("signal_id") == signal_id
        and binding.get("telegram_message_id") == telegram_message_id
        and binding.get("canonical_pair") == canonical_pair
        and binding.get("style") == style
    ):
        raise ReconciliationError(14, "TELEGRAM_BINDING_INVALID")
    commands = state["processed_commands"]
    if any(
        not isinstance(commands.get(command_id), Mapping)
        or commands[command_id].get("outcome") != "COMMAND_REJECTED_AMBIGUOUS"
        for command_id in INCIDENT_COMMAND_IDS
    ):
        raise ReconciliationError(14, "OWNER_AUTHORIZATION_PROOF_INVALID")


def _existing_active_record(
    ledger: Mapping[str, Any], *, expected_signal_id: str,
    expected_delivery_id: str, expected_pair: str, expected_style: str,
    expected_state: str, expected_last_transition_id: str,
) -> Mapping[str, Any]:
    record = ledger["signals"].get(expected_signal_id)
    if not isinstance(record, Mapping) or not (
        expected_signal_id == EXISTING_SIGNAL_ID
        and expected_delivery_id == EXISTING_DELIVERY_ID
        and expected_pair == EXISTING_PAIR
        and expected_style == "SWING"
        and expected_state == active.ENTRY_ACTIVE
        and expected_last_transition_id == EXISTING_LAST_TRANSITION_ID
        and record.get("signal_id") == expected_signal_id
        and record.get("delivery_id") == expected_delivery_id
        and normalize_pair(record.get("symbol")) == expected_pair
        and record.get("mode") == expected_style
        and record.get("state") == expected_state
        and record.get("last_transition_id") == expected_last_transition_id
    ):
        raise ReconciliationError(13, "EXISTING_ENTRY_PRESERVATION_PRECONDITION_FAILED")
    return record


def _validate_pre_state(
    ledger: Mapping[str, Any], *, expected_ledger_revision: int,
    signal_id: str, canonical_pair: str,
    expected_existing_active_signal_id: str,
    expected_existing_active_delivery_id: str,
    expected_existing_active_pair: str,
    expected_existing_active_style: str,
    expected_existing_active_state: str,
    expected_existing_active_last_transition_id: str,
    expected_existing_active_signal_count: int,
    expected_existing_active_pair_owner_count: int,
    expected_target_active_count: int,
    expected_target_pair_owner_count: int,
    expected_swing_active_count: int,
    expected_swing_available_count: int,
) -> dict[str, Any]:
    document = active.validate_ledger(ledger)
    existing = _existing_active_record(
        document,
        expected_signal_id=expected_existing_active_signal_id,
        expected_delivery_id=expected_existing_active_delivery_id,
        expected_pair=expected_existing_active_pair,
        expected_style=expected_existing_active_style,
        expected_state=expected_existing_active_state,
        expected_last_transition_id=expected_existing_active_last_transition_id,
    )
    active_records = [
        record for record in document["signals"].values()
        if record["state"] == active.ENTRY_ACTIVE
    ]
    relation = _capacity_and_pair(document, canonical_pair)
    existing_pair_owners = sum(
        record["state"] == active.ENTRY_ACTIVE
        and normalize_pair(record["symbol"]) == expected_existing_active_pair
        for record in document["signals"].values()
    )
    target_active = sum(
        record["state"] == active.ENTRY_ACTIVE and record["signal_id"] == signal_id
        for record in document["signals"].values()
    )
    if not (
        document["ledger_revision"] == expected_ledger_revision == 4
        and signal_id not in document["signals"]
        and len(active_records) == expected_existing_active_signal_count == 1
        and existing_pair_owners == expected_existing_active_pair_owner_count == 1
        and target_active == expected_target_active_count == 0
        and relation == {
            "swing_active": expected_swing_active_count,
            "swing_available": expected_swing_available_count,
            "total_active": 1,
            "pair_owners": expected_target_pair_owner_count,
        }
        and expected_swing_active_count == 1
        and expected_swing_available_count == 2
        and expected_target_pair_owner_count == 0
    ):
        raise ReconciliationError(13, "LEDGER_CAPACITY_PRECONDITION_FAILED")
    return dict(existing)


def _registration_only(
    ledger: Mapping[str, Any], *, signal_id: str, delivery_id: str,
    reservation_transition_id: str, canonical_pair: str,
    expected_ledger_revision: int, existing_record: Mapping[str, Any],
) -> bool:
    try:
        document = active.validate_ledger(ledger)
        record = document["signals"].get(signal_id)
        relation = _capacity_and_pair(document, canonical_pair)
        return bool(
            document["ledger_revision"] == expected_ledger_revision + 1
            and isinstance(record, Mapping)
            and record.get("delivery_id") == delivery_id
            and record.get("state") == active.PUBLISHED_PENDING_ENTRY
            and record.get("last_transition_id") == reservation_transition_id
            and document["signals"].get(EXISTING_SIGNAL_ID) == existing_record
            and relation == {
                "swing_active": 1, "swing_available": 2,
                "total_active": 1, "pair_owners": 0,
            }
        )
    except Exception:
        return False


def _validate_completed_state(
    ledger: Mapping[str, Any], *, signal_id: str, delivery_id: str,
    reservation_transition_id: str, entry_transition_id: str,
    entry_at: str, canonical_pair: str, expected_ledger_revision: int,
    existing_record: Mapping[str, Any] | None = None,
) -> bool:
    try:
        document = active.validate_ledger(ledger)
        existing = _existing_active_record(
            document,
            expected_signal_id=EXISTING_SIGNAL_ID,
            expected_delivery_id=EXISTING_DELIVERY_ID,
            expected_pair=EXISTING_PAIR,
            expected_style="SWING",
            expected_state=active.ENTRY_ACTIVE,
            expected_last_transition_id=EXISTING_LAST_TRANSITION_ID,
        )
        record = document["signals"].get(signal_id)
        reserve = document["transitions"].get(reservation_transition_id)
        entry = document["transitions"].get(entry_transition_id)
        transactions = [
            transaction for transaction in document["publication_transactions"].values()
            if transaction.get("signal_id") == signal_id
            and transaction.get("reservation_transition_id") == reservation_transition_id
            and transaction.get("state") == active.OCCUPANCY_COMMITTED
        ]
        relation = _capacity_and_pair(document, canonical_pair)
        existing_unchanged = existing_record is None or existing == existing_record
        return bool(
            document["ledger_revision"] == expected_ledger_revision + 2
            and isinstance(record, Mapping)
            and record.get("delivery_id") == delivery_id
            and record.get("mode") == "SWING"
            and normalize_pair(record.get("symbol")) == canonical_pair
            and record.get("state") == active.ENTRY_ACTIVE
            and record.get("entry_at") == entry_at
            and record.get("last_transition_id") == entry_transition_id
            and isinstance(reserve, Mapping) and reserve.get("operation") == "RESERVE"
            and isinstance(entry, Mapping) and entry.get("operation") == "ENTRY"
            and entry.get("occurred_at") == entry_at
            and len(transactions) == 1
            and existing_unchanged
            and relation == {
                "swing_active": 2, "swing_available": 1,
                "total_active": 2, "pair_owners": 1,
            }
        )
    except Exception:
        return False


def _load_result(path: Path) -> dict[str, Any]:
    raw = _read_regular(path, uid=999, gid=987, mode=0o600, exit_code=10)
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReconciliationError(10, "RESULT_COLLISION") from exc
    if _canonical_json(result) != raw:
        raise ReconciliationError(10, "RESULT_COLLISION")
    required = {
        "schema_name", "schema_version", "reconciliation_id", "signal_id",
        "delivery_id", "reservation_transition_id", "entry_transition_id",
        "entry_at", "entry_at_authority", "input_publication_sha256",
        "input_control_sha256", "input_ledger_sha256", "output_ledger_sha256",
        "input_ledger_revision", "output_ledger_revision", "effect_count",
        "publication_registration_created_count", "entry_active_creation_count",
        "swing_active_count", "swing_available_slot_count",
        "global_pair_lock_owner_count", "existing_active_signal_id",
        "existing_active_record_preserved", "state_access_uid", "state_access_gid",
        "incident_manifest_sha256", "unit_release_parity",
        "telegram_send_attempt_count", "network_access_count",
        "exchange_access_count", "exchange_order_execution_count",
        "trading_execution_count", "transaction_state",
    }
    if set(result) != required:
        raise ReconciliationError(10, "RESULT_COLLISION")
    return result


def _write_result(path: Path, result: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise ReconciliationError(10, "RESULT_COLLISION")
    _no_symlink_chain(path.parent)
    descriptor = None
    temporary = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent,
        )
        temporary = Path(name)
        os.fchmod(descriptor, 0o600)
        payload = _canonical_json(result)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except ReconciliationError:
        raise
    except OSError as exc:
        raise ReconciliationError(19, "RESULT_WRITE_FAILED", effect_count=1) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _identity() -> tuple[int, int]:
    return os.geteuid(), os.getegid()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ",
    )


def reconcile_owner_reported_pharos_filled_position(
    *, publication_artifact_path: Path,
    expected_publication_artifact_sha256: str,
    expected_publication_timestamp: str, expected_delivery_timestamp: str,
    expected_valid_until: str, expected_content_sha256: str,
    expected_source_payload_sha256: str,
    expected_publication_payload_sha256: str,
    control_state_path: Path, expected_control_state_sha256: str,
    expected_control_state_revision: int, expected_control_last_update_id: int,
    active_ledger_path: Path, expected_active_ledger_sha256: str,
    expected_ledger_revision: int, signal_id: str, delivery_id: str,
    telegram_message_id: int, canonical_pair: str, style: str, direction: str,
    expected_existing_active_signal_id: str,
    expected_existing_active_delivery_id: str,
    expected_existing_active_pair: str,
    expected_existing_active_style: str,
    expected_existing_active_state: str,
    expected_existing_active_last_transition_id: str,
    expected_existing_active_signal_count: int,
    expected_existing_active_pair_owner_count: int,
    expected_target_active_count: int, expected_target_pair_owner_count: int,
    expected_swing_active_count: int, expected_swing_available_count: int,
    owner_authorization_id: str, reservation_transition_id: str,
    entry_transition_id: str, entry_at_authority: str,
    state_runtime_uid: int, state_runtime_gid: int, result_path: Path,
    incident_verification: Mapping[str, Any],
    release_verification: Mapping[str, Any],
    privilege_verification: Mapping[str, Any],
    identity_provider: Callable[[], tuple[int, int]] = _identity,
    timestamp_provider: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    """Perform exactly one sealed PHAROS registration-and-entry transaction."""
    if (
        identity_provider() != (state_runtime_uid, state_runtime_gid)
        or (state_runtime_uid, state_runtime_gid) != (999, 987)
    ):
        raise ReconciliationError(12, "STATE_ACCESS_IDENTITY_INVALID")
    if incident_verification.get("root_only_incident_seal_verification") != "PASS":
        raise ReconciliationError(11, "INCIDENT_VERIFICATION_MISSING")
    if release_verification.get("unit_release_parity") != "PASS":
        raise ReconciliationError(13, "UNIT_RELEASE_PARITY_VERIFICATION_MISSING")
    if privilege_verification.get("permanent_privilege_drop_before_state_access") != "PASS":
        raise ReconciliationError(12, "PRIVILEGE_VERIFICATION_MISSING")
    if owner_authorization_id != OWNER_AUTHORIZATION_ID:
        raise ReconciliationError(14, "OWNER_AUTHORIZATION_ID_MISMATCH")
    if entry_at_authority != ENTRY_AT_AUTHORITY:
        raise ReconciliationError(10, "ENTRY_TIMESTAMP_AUTHORITY_MISMATCH")

    publication_raw = _read_regular(
        publication_artifact_path, uid=999, gid=987, mode=0o600,
    )
    control_raw = _read_regular(control_state_path, uid=999, gid=987, mode=0o600)
    ledger_raw = _read_regular(active_ledger_path, uid=999, gid=987, mode=0o600)
    if not (
        _sha256(publication_raw) == expected_publication_artifact_sha256 == PUBLICATION_SHA256
        and _sha256(control_raw) == expected_control_state_sha256 == CONTROL_SHA256
    ):
        raise ReconciliationError(13, "STATE_HASH_PRECONDITION_FAILED")
    try:
        publication = read_publication_artifact(
            publication_root=publication_artifact_path.parents[2],
            signal_id=signal_id, delivery_id=delivery_id,
        )
        control = load_state(control_state_path)
        ledger = active.load_ledger(active_ledger_path)
    except Exception as exc:
        raise ReconciliationError(13, "STATE_SCHEMA_PRECONDITION_FAILED") from exc
    _validate_publication(
        publication, signal_id=signal_id, delivery_id=delivery_id,
        telegram_message_id=telegram_message_id, canonical_pair=canonical_pair,
        style=style, direction=direction,
        expected_publication_timestamp=expected_publication_timestamp,
        expected_delivery_timestamp=expected_delivery_timestamp,
        expected_valid_until=expected_valid_until,
        expected_content_sha256=expected_content_sha256,
        expected_source_payload_sha256=expected_source_payload_sha256,
        expected_publication_payload_sha256=expected_publication_payload_sha256,
    )
    _validate_control(
        control, signal_id=signal_id, telegram_message_id=telegram_message_id,
        canonical_pair=canonical_pair, style=style,
        expected_revision=expected_control_state_revision,
        expected_last_update_id=expected_control_last_update_id,
    )

    initial_ledger_hash = _sha256(ledger_raw)
    if initial_ledger_hash != expected_active_ledger_sha256 or initial_ledger_hash != LEDGER_SHA256:
        existing_result = _load_result(result_path)
        entry_at = existing_result.get("entry_at")
        if (
            not isinstance(entry_at, str)
            or not _validate_completed_state(
                ledger, signal_id=signal_id, delivery_id=delivery_id,
                reservation_transition_id=reservation_transition_id,
                entry_transition_id=entry_transition_id, entry_at=entry_at,
                canonical_pair=canonical_pair,
                expected_ledger_revision=expected_ledger_revision,
            )
            or existing_result.get("reconciliation_id") != RECONCILIATION_ID
            or existing_result.get("signal_id") != signal_id
            or existing_result.get("delivery_id") != delivery_id
            or existing_result.get("input_ledger_sha256") != expected_active_ledger_sha256
            or existing_result.get("output_ledger_sha256") != initial_ledger_hash
            or existing_result.get("transaction_state") != "COMMITTED"
            or existing_result.get("effect_count") != 1
            or existing_result.get("existing_active_record_preserved") != "YES"
        ):
            raise ReconciliationError(10, "RESULT_COLLISION")
        replay = dict(existing_result)
        replay["effect_count"] = 0
        replay["publication_registration_created_count"] = 0
        replay["entry_active_creation_count"] = 0
        replay["transaction_state"] = "VERIFIED_EXACT_REPLAY"
        return replay

    existing_record = _validate_pre_state(
        ledger, expected_ledger_revision=expected_ledger_revision,
        signal_id=signal_id, canonical_pair=canonical_pair,
        expected_existing_active_signal_id=expected_existing_active_signal_id,
        expected_existing_active_delivery_id=expected_existing_active_delivery_id,
        expected_existing_active_pair=expected_existing_active_pair,
        expected_existing_active_style=expected_existing_active_style,
        expected_existing_active_state=expected_existing_active_state,
        expected_existing_active_last_transition_id=expected_existing_active_last_transition_id,
        expected_existing_active_signal_count=expected_existing_active_signal_count,
        expected_existing_active_pair_owner_count=expected_existing_active_pair_owner_count,
        expected_target_active_count=expected_target_active_count,
        expected_target_pair_owner_count=expected_target_pair_owner_count,
        expected_swing_active_count=expected_swing_active_count,
        expected_swing_available_count=expected_swing_available_count,
    )
    if result_path.exists() or result_path.is_symlink():
        raise ReconciliationError(10, "RESULT_COLLISION")

    entry_at = timestamp_provider()
    if re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", entry_at) is None:
        raise ReconciliationError(10, "ENTRY_TIMESTAMP_INVALID")
    registration = flow.repair_publication_registration(
        active_ledger_path=active_ledger_path,
        expected_active_ledger_revision=expected_ledger_revision,
        publication_evidence=publication,
        reservation_transition_id=reservation_transition_id,
        timestamp=entry_at,
    )
    try:
        registered_ledger = active.load_ledger(active_ledger_path)
    except Exception as exc:
        raise ReconciliationError(17, "AMBIGUOUS_LEDGER_AFTER_REGISTRATION") from exc
    if registration.result != flow.PUBLISHED_SIGNAL_REGISTERED or not _registration_only(
        registered_ledger, signal_id=signal_id, delivery_id=delivery_id,
        reservation_transition_id=reservation_transition_id,
        canonical_pair=canonical_pair, expected_ledger_revision=expected_ledger_revision,
        existing_record=existing_record,
    ):
        current_hash = _sha256(
            _read_regular(active_ledger_path, uid=999, gid=987, mode=0o600),
        )
        if current_hash == initial_ledger_hash:
            raise ReconciliationError(15, "PUBLICATION_REGISTRATION_FAILED")
        if _registration_only(
            registered_ledger, signal_id=signal_id, delivery_id=delivery_id,
            reservation_transition_id=reservation_transition_id,
            canonical_pair=canonical_pair,
            expected_ledger_revision=expected_ledger_revision,
            existing_record=existing_record,
        ):
            raise ReconciliationError(16, "REGISTRATION_ONLY_PRESERVED")
        raise ReconciliationError(17, "AMBIGUOUS_LEDGER_AFTER_REGISTRATION")

    try:
        lifecycle.commit_owner_confirmed_entry(
            ledger_path=active_ledger_path,
            expected_revision=expected_ledger_revision + 1,
            transition_id=entry_transition_id, signal_id=signal_id,
            timestamp=entry_at,
        )
    except Exception as exc:
        current = active.load_ledger(active_ledger_path)
        if _registration_only(
            current, signal_id=signal_id, delivery_id=delivery_id,
            reservation_transition_id=reservation_transition_id,
            canonical_pair=canonical_pair,
            expected_ledger_revision=expected_ledger_revision,
            existing_record=existing_record,
        ):
            raise ReconciliationError(16, "REGISTRATION_ONLY_PRESERVED") from exc
        raise ReconciliationError(17, "AMBIGUOUS_LEDGER_AFTER_ENTRY") from exc

    try:
        final_ledger = active.load_ledger(active_ledger_path)
        if not _validate_completed_state(
            final_ledger, signal_id=signal_id, delivery_id=delivery_id,
            reservation_transition_id=reservation_transition_id,
            entry_transition_id=entry_transition_id, entry_at=entry_at,
            canonical_pair=canonical_pair,
            expected_ledger_revision=expected_ledger_revision,
            existing_record=existing_record,
        ):
            raise ValueError
        publication_after = _read_regular(
            publication_artifact_path, uid=999, gid=987, mode=0o600,
        )
        control_after = _read_regular(control_state_path, uid=999, gid=987, mode=0o600)
        if publication_after != publication_raw or control_after != control_raw:
            raise ValueError
    except Exception as exc:
        raise ReconciliationError(
            18, "POST_ENTRY_VERIFICATION_FAILED", effect_count=1,
        ) from exc

    final_ledger_raw = _read_regular(
        active_ledger_path, uid=999, gid=987, mode=0o600,
    )
    result = {
        "schema_name": "pharos-filled-position-reconciliation-result",
        "schema_version": 1,
        "reconciliation_id": RECONCILIATION_ID,
        "signal_id": signal_id,
        "delivery_id": delivery_id,
        "reservation_transition_id": reservation_transition_id,
        "entry_transition_id": entry_transition_id,
        "entry_at": entry_at,
        "entry_at_authority": entry_at_authority,
        "input_publication_sha256": expected_publication_artifact_sha256,
        "input_control_sha256": expected_control_state_sha256,
        "input_ledger_sha256": expected_active_ledger_sha256,
        "output_ledger_sha256": _sha256(final_ledger_raw),
        "input_ledger_revision": expected_ledger_revision,
        "output_ledger_revision": final_ledger["ledger_revision"],
        "effect_count": 1,
        "publication_registration_created_count": 1,
        "entry_active_creation_count": 1,
        "swing_active_count": 2,
        "swing_available_slot_count": 1,
        "global_pair_lock_owner_count": 1,
        "existing_active_signal_id": expected_existing_active_signal_id,
        "existing_active_record_preserved": "YES",
        "state_access_uid": state_runtime_uid,
        "state_access_gid": state_runtime_gid,
        "incident_manifest_sha256": incident_verification["incident_manifest_sha256"],
        "unit_release_parity": release_verification["unit_release_parity"],
        "telegram_send_attempt_count": 0,
        "network_access_count": 0,
        "exchange_access_count": 0,
        "exchange_order_execution_count": 0,
        "trading_execution_count": 0,
        "transaction_state": "COMMITTED",
    }
    _write_result(result_path, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--incident-evidence-root", required=True, type=Path)
    parser.add_argument("--expected-incident-manifest-sha256", required=True)
    parser.add_argument("--installed-release-reference-path", required=True, type=Path)
    parser.add_argument("--scanner-unit-path", required=True, type=Path)
    parser.add_argument("--controller-unit-path", required=True, type=Path)
    parser.add_argument("--require-unit-release-parity", required=True, action="store_true")
    parser.add_argument("--publication-artifact-path", required=True, type=Path)
    parser.add_argument("--expected-publication-artifact-sha256", required=True)
    parser.add_argument("--expected-publication-timestamp", required=True)
    parser.add_argument("--expected-delivery-timestamp", required=True)
    parser.add_argument("--expected-valid-until", required=True)
    parser.add_argument("--expected-content-sha256", required=True)
    parser.add_argument("--expected-source-payload-sha256", required=True)
    parser.add_argument("--expected-publication-payload-sha256", required=True)
    parser.add_argument("--control-state-path", required=True, type=Path)
    parser.add_argument("--expected-control-state-sha256", required=True)
    parser.add_argument("--expected-control-state-revision", required=True, type=int)
    parser.add_argument("--expected-control-last-update-id", required=True, type=int)
    parser.add_argument("--active-ledger-path", required=True, type=Path)
    parser.add_argument("--expected-active-ledger-sha256", required=True)
    parser.add_argument("--expected-ledger-revision", required=True, type=int)
    parser.add_argument("--signal-id", required=True)
    parser.add_argument("--delivery-id", required=True)
    parser.add_argument("--telegram-message-id", required=True, type=int)
    parser.add_argument("--canonical-pair", required=True)
    parser.add_argument("--style", required=True)
    parser.add_argument("--direction", required=True)
    parser.add_argument("--expected-existing-active-signal-id", required=True)
    parser.add_argument("--expected-existing-active-delivery-id", required=True)
    parser.add_argument("--expected-existing-active-pair", required=True)
    parser.add_argument("--expected-existing-active-style", required=True)
    parser.add_argument("--expected-existing-active-state", required=True)
    parser.add_argument("--expected-existing-active-last-transition-id", required=True)
    parser.add_argument("--expected-existing-active-signal-count", required=True, type=int)
    parser.add_argument("--expected-existing-active-pair-owner-count", required=True, type=int)
    parser.add_argument("--expected-target-active-count", required=True, type=int)
    parser.add_argument("--expected-target-pair-owner-count", required=True, type=int)
    parser.add_argument("--expected-swing-active-count", required=True, type=int)
    parser.add_argument("--expected-swing-available-count", required=True, type=int)
    parser.add_argument("--owner-authorization-id", required=True)
    parser.add_argument("--reservation-transition-id", required=True)
    parser.add_argument("--entry-transition-id", required=True)
    parser.add_argument("--entry-at-authority", required=True)
    parser.add_argument("--state-runtime-uid", required=True, type=int)
    parser.add_argument("--state-runtime-gid", required=True, type=int)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--non-interactive", required=True, action="store_true")
    parser.add_argument("--result-path", required=True, type=Path)
    parser.add_argument("--expected-result-parent-path", required=True, type=Path)
    parser.add_argument("--expected-result-parent-owner", required=True)
    parser.add_argument("--expected-result-parent-group", required=True)
    parser.add_argument("--expected-result-parent-mode", required=True)
    parser.add_argument("--require-result-path-absent", required=True, action="store_true")
    return parser


def _validate_exact_arguments(arguments: argparse.Namespace) -> None:
    expected = {
        "incident_evidence_root": INCIDENT_ROOT,
        "expected_incident_manifest_sha256": INCIDENT_MANIFEST_SHA256,
        "installed_release_reference_path": INSTALLED_RELEASE_REFERENCE_PATH,
        "scanner_unit_path": SCANNER_UNIT_PATH,
        "controller_unit_path": CONTROLLER_UNIT_PATH,
        "require_unit_release_parity": True,
        "publication_artifact_path": PUBLICATION_PATH,
        "expected_publication_artifact_sha256": PUBLICATION_SHA256,
        "expected_publication_timestamp": "2026-07-29T17:17:42Z",
        "expected_delivery_timestamp": "2026-07-29T17:17:44Z",
        "expected_valid_until": "2026-12-31T23:59:59Z",
        "expected_content_sha256": CONTENT_SHA256,
        "expected_source_payload_sha256": SOURCE_PAYLOAD_SHA256,
        "expected_publication_payload_sha256": PUBLICATION_PAYLOAD_SHA256,
        "control_state_path": CONTROL_PATH,
        "expected_control_state_sha256": CONTROL_SHA256,
        "expected_control_state_revision": 32,
        "expected_control_last_update_id": 469110663,
        "active_ledger_path": LEDGER_PATH,
        "expected_active_ledger_sha256": LEDGER_SHA256,
        "expected_ledger_revision": 4,
        "signal_id": SIGNAL_ID,
        "delivery_id": DELIVERY_ID,
        "telegram_message_id": 932,
        "canonical_pair": "PHAROS/USDT",
        "style": "SWING",
        "direction": "LONG",
        "expected_existing_active_signal_id": EXISTING_SIGNAL_ID,
        "expected_existing_active_delivery_id": EXISTING_DELIVERY_ID,
        "expected_existing_active_pair": EXISTING_PAIR,
        "expected_existing_active_style": "SWING",
        "expected_existing_active_state": active.ENTRY_ACTIVE,
        "expected_existing_active_last_transition_id": EXISTING_LAST_TRANSITION_ID,
        "expected_existing_active_signal_count": 1,
        "expected_existing_active_pair_owner_count": 1,
        "expected_target_active_count": 0,
        "expected_target_pair_owner_count": 0,
        "expected_swing_active_count": 1,
        "expected_swing_available_count": 2,
        "owner_authorization_id": OWNER_AUTHORIZATION_ID,
        "reservation_transition_id": RESERVATION_TRANSITION_ID,
        "entry_transition_id": ENTRY_TRANSITION_ID,
        "entry_at_authority": ENTRY_AT_AUTHORITY,
        "state_runtime_uid": 999,
        "state_runtime_gid": 987,
        "mode": "production-reconcile-filled-position",
        "non_interactive": True,
        "result_path": RESULT_PATH,
        "expected_result_parent_path": Path("/var/tmp"),
        "expected_result_parent_owner": "root",
        "expected_result_parent_group": "root",
        "expected_result_parent_mode": "1777",
        "require_result_path_absent": True,
    }
    if any(getattr(arguments, key) != value for key, value in expected.items()):
        raise ReconciliationError(10, "EXACT_ARGUMENT_CONTRACT_MISMATCH")
    for path in (
        arguments.incident_evidence_root,
        arguments.installed_release_reference_path,
        arguments.scanner_unit_path,
        arguments.controller_unit_path,
        arguments.publication_artifact_path,
        arguments.control_state_path,
        arguments.active_ledger_path,
        arguments.result_path,
        arguments.expected_result_parent_path,
    ):
        if not path.is_absolute():
            raise ReconciliationError(10, "ABSOLUTE_PATH_REQUIRED")
    if (
        re.fullmatch(r"PSG-[0-9a-f]{64}", arguments.signal_id) is None
        or re.fullmatch(r"PDL-[0-9a-f]{64}", arguments.delivery_id) is None
    ):
        raise ReconciliationError(10, "EXACT_IDENTITY_FORMAT_INVALID")


def _verify_result_path_contract_as_root(arguments: argparse.Namespace) -> None:
    if os.geteuid() != 0 or os.getegid() != 0:
        raise ReconciliationError(13, "ROOT_RESULT_PATH_VERIFICATION_REQUIRED")
    parent = arguments.expected_result_parent_path
    _no_symlink_chain(parent)
    metadata = parent.stat()
    if (
        arguments.result_path.parent != parent
        or arguments.expected_result_parent_owner != "root"
        or arguments.expected_result_parent_group != "root"
        or arguments.expected_result_parent_mode != "1777"
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_gid != 0
        or stat.S_IMODE(metadata.st_mode) != 0o1777
        or arguments.result_path.exists()
        or arguments.result_path.is_symlink()
    ):
        raise ReconciliationError(13, "RESULT_PATH_PRECONDITION_FAILED")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        _validate_exact_arguments(arguments)
        incident = verify_incident_evidence_as_root(
            arguments.incident_evidence_root,
            arguments.expected_incident_manifest_sha256,
        )
        verify_runtime_quiescence()
        release = verify_release_parity(
            arguments.installed_release_reference_path,
            arguments.scanner_unit_path,
            arguments.controller_unit_path,
        )
        _verify_result_path_contract_as_root(arguments)
        privilege = permanently_drop_privileges(
            arguments.state_runtime_uid, arguments.state_runtime_gid,
        )
        result = reconcile_owner_reported_pharos_filled_position(
            publication_artifact_path=arguments.publication_artifact_path,
            expected_publication_artifact_sha256=arguments.expected_publication_artifact_sha256,
            expected_publication_timestamp=arguments.expected_publication_timestamp,
            expected_delivery_timestamp=arguments.expected_delivery_timestamp,
            expected_valid_until=arguments.expected_valid_until,
            expected_content_sha256=arguments.expected_content_sha256,
            expected_source_payload_sha256=arguments.expected_source_payload_sha256,
            expected_publication_payload_sha256=arguments.expected_publication_payload_sha256,
            control_state_path=arguments.control_state_path,
            expected_control_state_sha256=arguments.expected_control_state_sha256,
            expected_control_state_revision=arguments.expected_control_state_revision,
            expected_control_last_update_id=arguments.expected_control_last_update_id,
            active_ledger_path=arguments.active_ledger_path,
            expected_active_ledger_sha256=arguments.expected_active_ledger_sha256,
            expected_ledger_revision=arguments.expected_ledger_revision,
            signal_id=arguments.signal_id, delivery_id=arguments.delivery_id,
            telegram_message_id=arguments.telegram_message_id,
            canonical_pair=arguments.canonical_pair, style=arguments.style,
            direction=arguments.direction,
            expected_existing_active_signal_id=arguments.expected_existing_active_signal_id,
            expected_existing_active_delivery_id=arguments.expected_existing_active_delivery_id,
            expected_existing_active_pair=arguments.expected_existing_active_pair,
            expected_existing_active_style=arguments.expected_existing_active_style,
            expected_existing_active_state=arguments.expected_existing_active_state,
            expected_existing_active_last_transition_id=arguments.expected_existing_active_last_transition_id,
            expected_existing_active_signal_count=arguments.expected_existing_active_signal_count,
            expected_existing_active_pair_owner_count=arguments.expected_existing_active_pair_owner_count,
            expected_target_active_count=arguments.expected_target_active_count,
            expected_target_pair_owner_count=arguments.expected_target_pair_owner_count,
            expected_swing_active_count=arguments.expected_swing_active_count,
            expected_swing_available_count=arguments.expected_swing_available_count,
            owner_authorization_id=arguments.owner_authorization_id,
            reservation_transition_id=arguments.reservation_transition_id,
            entry_transition_id=arguments.entry_transition_id,
            entry_at_authority=arguments.entry_at_authority,
            state_runtime_uid=arguments.state_runtime_uid,
            state_runtime_gid=arguments.state_runtime_gid,
            result_path=arguments.result_path,
            incident_verification=incident,
            release_verification=release,
            privilege_verification=privilege,
        )
        sys.stdout.buffer.write(_canonical_json(result))
        return 0
    except ReconciliationError as error:
        sys.stderr.write(f"PHAROS_RECONCILIATION_FAILED:{error.reason}\n")
        return error.exit_code
    except SystemExit:
        return 10
    except Exception:
        sys.stderr.write("PHAROS_RECONCILIATION_FAILED:FAIL_CLOSED\n")
        return 17


if __name__ == "__main__":
    raise SystemExit(main())
