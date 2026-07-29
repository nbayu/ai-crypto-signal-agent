"""One-time, evidence-gated KMNO owner-filled-position reconciliation.

This module has no transport, provider, exchange, order, or trading imports.
It verifies sealed root-only evidence, permanently drops privilege, validates
three exact state authorities, and uses only the existing passive registration
and owner-confirmed entry APIs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from engine import active_signal_ledger_v1 as active
from engine import passive_production_signal_flow_v1 as flow
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine.canonical_pair_v1 import normalize_pair
from engine.production_signal_artifact_v1 import read_publication_artifact
from engine.telegram_owner_control_state_v1 import load_state


RECONCILIATION_ID = "KFR-062397b46c377ceb7e5b17d4962d4392643d5f57a4bc6516c0efa401a2c602a2"
SIGNAL_ID = "PSG-59f5492f4758cb93086bf57d997cf6f4239bd4a54ba817fb46bb1817f753acb3"
DELIVERY_ID = "PDL-c80055e0e435c83a23981324a444d653df1bed7d5cae6eee4367ec143631d6f8"
INCIDENT_ROOT = Path("/opt/ai-crypto-signal-agent-forensics/post-closure-kmno-owner-entry-binding-reconciliation-scope-lock-20260729T114144Z")
INCIDENT_MANIFEST_SHA256 = "208ed4df521d88ed3f5fb799819e6886ee9cd0e1de76e42238f524e6a2a0717d"
PUBLICATION_SHA256 = "3a821c73c5da70e8696ffca1e96a4980f64147b65b31319218b6ee5e9a6d38c0"
CONTROL_SHA256 = "1299073cceb125758bf806e09e46c8f0bbdc557b475ba64443e440acd0500411"
LEDGER_SHA256 = "105a8c2bb2ed979bdc01662424221bfc510b4ca972cca72fa43cffffcfe2f6bd"
PUBLICATION_PATH = Path("/var/lib/ai-crypto-signal-agent/phase09r1/production-signals/publications/PSG-59f5492f4758cb93086bf57d997cf6f4239bd4a54ba817fb46bb1817f753acb3/PDL-c80055e0e435c83a23981324a444d653df1bed7d5cae6eee4367ec143631d6f8.json")
CONTROL_PATH = Path("/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/telegram-owner-control-state-v1.json")
LEDGER_PATH = Path("/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/active-signal-ledger-v2.json")
CONTENT_SHA256 = "693d699c10ebc348b4c6cd23ee00ffbf8b8851e93294e047fc3aa9cc22b30d7a"
SOURCE_PAYLOAD_SHA256 = "30a2c9cf0a88e37f4a9c52718d0b7392335c2a63144fa09cfe0879a3904f26f9"
PUBLICATION_PAYLOAD_SHA256 = "a71588a656c7277554db07af244fedb0a96b4f0401035024424628326328e2ef"
OWNER_AUTHORIZATION_ID = "AUTHORIZE_KMNO_REPAIR_REMOTE_LOCK_CONTROLLER_SWITCH_AND_ONE_TIME_FILLED_POSITION_RECONCILIATION"
RESERVATION_TRANSITION_ID = "owner-publication-reconcile-062397b46c377ceb7e5b17d4962d4392643d5f57a4bc6516c0efa401a2c602a2"
ENTRY_TRANSITION_ID = "owner-filled-entry-reconcile-062397b46c377ceb7e5b17d4962d4392643d5f57a4bc6516c0efa401a2c602a2"
ENTRY_AT = "2026-07-29T11:20:07Z"
RESULT_PATH = Path("/var/tmp/ai-crypto-signal-agent-kmno-reconciliation-KFR-062397b46c377ceb7e5b17d4962d4392643d5f57a4bc6516c0efa401a2c602a2.json")
INCIDENT_COMMAND_IDS = {
    "f613afb226ee79397f5b0da56bd44cef734ef11a911d26726988ac9e284874f4",
    "000ddc3aa4ac29a149714906c402cec41b0584c4bc19741cb4012b1bd57fa025",
    "7f3f1244cda5c2b346f85cc44cf79757402874929085d37baf8911b5c86524d0",
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
    if len(lines) != 19:
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


def _validate_publication(publication: Mapping[str, Any], *, signal_id: str,
                          delivery_id: str, telegram_message_id: int,
                          canonical_pair: str, style: str, direction: str) -> None:
    payload = publication.get("publication_payload")
    receipt = publication.get("delivery_receipt")
    if not isinstance(payload, Mapping) or not isinstance(receipt, Mapping):
        raise ReconciliationError(14, "PUBLICATION_IDENTITY_INVALID")
    expected = (
        publication.get("signal_id") == signal_id == SIGNAL_ID,
        publication.get("delivery_id") == delivery_id == DELIVERY_ID,
        publication.get("delivery_state") == "DELIVERY_SUCCEEDED",
        publication.get("mode") == style == "SWING",
        normalize_pair(payload.get("symbol")) == canonical_pair == "KMNO/USDT",
        payload.get("side") == direction == "LONG",
        payload.get("signal_id") == signal_id,
        payload.get("mode") == style,
        publication.get("published_at") == "2026-07-29T11:17:37Z",
        receipt.get("delivered_at") == "2026-07-29T11:17:41Z",
        str(receipt.get("external_delivery_id")) == str(telegram_message_id) == "913",
        payload.get("valid_until") == "2026-12-31T23:59:59Z",
        publication.get("content_hash") == CONTENT_SHA256,
        publication.get("source_payload_hash") == SOURCE_PAYLOAD_SHA256,
        publication.get("publication_payload_hash") == PUBLICATION_PAYLOAD_SHA256,
        publication.get("order_execution") == "PROHIBITED",
        publication.get("capital_exposure") == "NONE",
    )
    if not all(expected):
        raise ReconciliationError(14, "PUBLICATION_IDENTITY_INVALID")


def _validate_control(state: Mapping[str, Any], *, signal_id: str,
                      telegram_message_id: int, canonical_pair: str, style: str) -> None:
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


def _registration_only(ledger: Mapping[str, Any], *, signal_id: str,
                       reservation_transition_id: str, canonical_pair: str) -> bool:
    try:
        document = active.validate_ledger(ledger)
        record = document["signals"].get(signal_id)
        relation = _capacity_and_pair(document, canonical_pair)
        return bool(
            document["ledger_revision"] == 3
            and isinstance(record, Mapping)
            and record.get("state") == active.PUBLISHED_PENDING_ENTRY
            and record.get("last_transition_id") == reservation_transition_id
            and relation == {
                "swing_active": 0, "swing_available": 3,
                "total_active": 0, "pair_owners": 0,
            }
        )
    except Exception:
        return False


def _completed(ledger: Mapping[str, Any], *, signal_id: str,
               reservation_transition_id: str, entry_transition_id: str,
               entry_at: str, canonical_pair: str) -> bool:
    try:
        document = active.validate_ledger(ledger)
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
        return bool(
            document["ledger_revision"] == 4
            and isinstance(record, Mapping)
            and record.get("delivery_id") == DELIVERY_ID
            and record.get("mode") == "SWING"
            and normalize_pair(record.get("symbol")) == canonical_pair
            and record.get("state") == active.ENTRY_ACTIVE
            and record.get("entry_at") == entry_at
            and record.get("last_transition_id") == entry_transition_id
            and isinstance(reserve, Mapping) and reserve.get("operation") == "RESERVE"
            and isinstance(entry, Mapping) and entry.get("operation") == "ENTRY"
            and entry.get("occurred_at") == entry_at
            and len(transactions) == 1
            and relation == {
                "swing_active": 1, "swing_available": 2,
                "total_active": 1, "pair_owners": 1,
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
        "entry_at", "input_publication_sha256", "input_control_sha256",
        "input_ledger_sha256", "output_ledger_sha256", "input_ledger_revision",
        "output_ledger_revision", "effect_count", "publication_registration_created_count",
        "entry_active_creation_count", "swing_active_count", "swing_available_slot_count",
        "global_pair_lock_owner_count", "state_access_uid", "state_access_gid",
        "incident_manifest_sha256", "telegram_send_attempt_count", "network_access_count",
        "exchange_access_count", "exchange_order_execution_count", "trading_execution_count",
        "transaction_state",
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
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
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



def render_controller_unit(template: bytes, release_root: str) -> bytes:
    """Render only the two sealed immutable-release tokens."""
    if not isinstance(template, bytes) or not isinstance(release_root, str):
        raise ValueError("CONTROLLER_RENDER_INVALID")
    if re.fullmatch(
        r"/opt/ai-crypto-signal-agent-releases/[0-9a-f]{40}", release_root,
    ) is None:
        raise ValueError("CONTROLLER_RELEASE_ROOT_INVALID")
    token = b"@@RELEASE_ROOT@@"
    if template.count(token) != 2:
        raise ValueError("CONTROLLER_TEMPLATE_TOKEN_COUNT_INVALID")
    rendered = template.replace(token, release_root.encode("ascii"))
    if token in rendered:
        raise ValueError("CONTROLLER_TEMPLATE_TOKEN_REMAINS")
    return rendered


def _identity() -> tuple[int, int]:
    return os.geteuid(), os.getegid()


def reconcile_owner_reported_filled_position(
    *, publication_artifact_path: Path, expected_publication_artifact_sha256: str,
    control_state_path: Path, expected_control_state_sha256: str,
    active_ledger_path: Path, expected_active_ledger_sha256: str,
    expected_ledger_revision: int, signal_id: str, delivery_id: str,
    telegram_message_id: int, canonical_pair: str, style: str, direction: str,
    owner_authorization_id: str, reservation_transition_id: str,
    entry_transition_id: str, entry_at: str, state_runtime_uid: int,
    state_runtime_gid: int, result_path: Path,
    incident_verification: Mapping[str, Any], privilege_verification: Mapping[str, Any],
    identity_provider: Callable[[], tuple[int, int]] = _identity,
) -> dict[str, Any]:
    """Perform exactly one sealed registration-and-entry transaction."""
    if identity_provider() != (state_runtime_uid, state_runtime_gid) or (state_runtime_uid, state_runtime_gid) != (999, 987):
        raise ReconciliationError(12, "STATE_ACCESS_IDENTITY_INVALID")
    if incident_verification.get("root_only_incident_seal_verification") != "PASS":
        raise ReconciliationError(11, "INCIDENT_VERIFICATION_MISSING")
    if privilege_verification.get("permanent_privilege_drop_before_state_access") != "PASS":
        raise ReconciliationError(12, "PRIVILEGE_VERIFICATION_MISSING")
    if owner_authorization_id != OWNER_AUTHORIZATION_ID:
        raise ReconciliationError(14, "OWNER_AUTHORIZATION_ID_MISMATCH")

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
    )
    _validate_control(
        control, signal_id=signal_id, telegram_message_id=telegram_message_id,
        canonical_pair=canonical_pair, style=style,
    )

    initial_ledger_hash = _sha256(ledger_raw)
    if initial_ledger_hash != expected_active_ledger_sha256 or initial_ledger_hash != LEDGER_SHA256:
        if not _completed(
            ledger, signal_id=signal_id,
            reservation_transition_id=reservation_transition_id,
            entry_transition_id=entry_transition_id, entry_at=entry_at,
            canonical_pair=canonical_pair,
        ):
            raise ReconciliationError(13, "LEDGER_HASH_PRECONDITION_FAILED")
        existing = _load_result(result_path)
        if (existing.get("reconciliation_id") != RECONCILIATION_ID
                or existing.get("signal_id") != signal_id
                or existing.get("transaction_state") != "COMMITTED"
                or existing.get("effect_count") != 1):
            raise ReconciliationError(10, "RESULT_COLLISION")
        replay = dict(existing)
        replay["effect_count"] = 0
        replay["publication_registration_created_count"] = 0
        replay["entry_active_creation_count"] = 0
        replay["transaction_state"] = "VERIFIED_EXACT_REPLAY"
        return replay

    pre_relation = _capacity_and_pair(ledger, canonical_pair)
    if (ledger["ledger_revision"] != expected_ledger_revision or expected_ledger_revision != 2
            or signal_id in ledger["signals"]
            or pre_relation != {
                "swing_active": 0, "swing_available": 3,
                "total_active": 0, "pair_owners": 0,
            }):
        raise ReconciliationError(13, "LEDGER_CAPACITY_PRECONDITION_FAILED")
    if result_path.exists() or result_path.is_symlink():
        raise ReconciliationError(10, "RESULT_COLLISION")

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
        registered_ledger, signal_id=signal_id,
        reservation_transition_id=reservation_transition_id,
        canonical_pair=canonical_pair,
    ):
        current_hash = _sha256(_read_regular(active_ledger_path, uid=999, gid=987, mode=0o600))
        if current_hash == initial_ledger_hash:
            raise ReconciliationError(15, "PUBLICATION_REGISTRATION_FAILED")
        if _registration_only(
            registered_ledger, signal_id=signal_id,
            reservation_transition_id=reservation_transition_id,
            canonical_pair=canonical_pair,
        ):
            raise ReconciliationError(16, "REGISTRATION_ONLY_PRESERVED")
        raise ReconciliationError(17, "AMBIGUOUS_LEDGER_AFTER_REGISTRATION")

    try:
        lifecycle.commit_owner_confirmed_entry(
            ledger_path=active_ledger_path, expected_revision=3,
            transition_id=entry_transition_id, signal_id=signal_id,
            timestamp=entry_at,
        )
    except Exception as exc:
        current = active.load_ledger(active_ledger_path)
        if _registration_only(
            current, signal_id=signal_id,
            reservation_transition_id=reservation_transition_id,
            canonical_pair=canonical_pair,
        ):
            raise ReconciliationError(16, "REGISTRATION_ONLY_PRESERVED") from exc
        raise ReconciliationError(17, "AMBIGUOUS_LEDGER_AFTER_ENTRY") from exc

    try:
        final_ledger = active.load_ledger(active_ledger_path)
        if not _completed(
            final_ledger, signal_id=signal_id,
            reservation_transition_id=reservation_transition_id,
            entry_transition_id=entry_transition_id, entry_at=entry_at,
            canonical_pair=canonical_pair,
        ):
            raise ValueError
        publication_after = _read_regular(
            publication_artifact_path, uid=999, gid=987, mode=0o600,
        )
        control_after = _read_regular(control_state_path, uid=999, gid=987, mode=0o600)
        if publication_after != publication_raw or control_after != control_raw:
            raise ValueError
    except Exception as exc:
        raise ReconciliationError(18, "POST_ENTRY_VERIFICATION_FAILED", effect_count=1) from exc

    final_ledger_raw = _read_regular(active_ledger_path, uid=999, gid=987, mode=0o600)
    result = {
        "schema_name": "kmno-filled-position-reconciliation-result",
        "schema_version": 1,
        "reconciliation_id": RECONCILIATION_ID,
        "signal_id": signal_id,
        "delivery_id": delivery_id,
        "reservation_transition_id": reservation_transition_id,
        "entry_transition_id": entry_transition_id,
        "entry_at": entry_at,
        "input_publication_sha256": expected_publication_artifact_sha256,
        "input_control_sha256": expected_control_state_sha256,
        "input_ledger_sha256": expected_active_ledger_sha256,
        "output_ledger_sha256": _sha256(final_ledger_raw),
        "input_ledger_revision": expected_ledger_revision,
        "output_ledger_revision": final_ledger["ledger_revision"],
        "effect_count": 1,
        "publication_registration_created_count": 1,
        "entry_active_creation_count": 1,
        "swing_active_count": 1,
        "swing_available_slot_count": 2,
        "global_pair_lock_owner_count": 1,
        "state_access_uid": state_runtime_uid,
        "state_access_gid": state_runtime_gid,
        "incident_manifest_sha256": incident_verification["incident_manifest_sha256"],
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
    parser.add_argument("--publication-artifact-path", required=True, type=Path)
    parser.add_argument("--expected-publication-artifact-sha256", required=True)
    parser.add_argument("--control-state-path", required=True, type=Path)
    parser.add_argument("--expected-control-state-sha256", required=True)
    parser.add_argument("--active-ledger-path", required=True, type=Path)
    parser.add_argument("--expected-active-ledger-sha256", required=True)
    parser.add_argument("--expected-ledger-revision", required=True, type=int)
    parser.add_argument("--signal-id", required=True)
    parser.add_argument("--delivery-id", required=True)
    parser.add_argument("--telegram-message-id", required=True, type=int)
    parser.add_argument("--canonical-pair", required=True)
    parser.add_argument("--style", required=True)
    parser.add_argument("--direction", required=True)
    parser.add_argument("--owner-authorization-id", required=True)
    parser.add_argument("--reservation-transition-id", required=True)
    parser.add_argument("--entry-transition-id", required=True)
    parser.add_argument("--entry-at", required=True)
    parser.add_argument("--state-runtime-uid", required=True, type=int)
    parser.add_argument("--state-runtime-gid", required=True, type=int)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--non-interactive", required=True, action="store_true")
    parser.add_argument("--result-path", required=True, type=Path)
    return parser


def _validate_exact_arguments(arguments: argparse.Namespace) -> None:
    expected = {
        "incident_evidence_root": INCIDENT_ROOT,
        "expected_incident_manifest_sha256": INCIDENT_MANIFEST_SHA256,
        "publication_artifact_path": PUBLICATION_PATH,
        "control_state_path": CONTROL_PATH,
        "active_ledger_path": LEDGER_PATH,
        "expected_publication_artifact_sha256": PUBLICATION_SHA256,
        "expected_control_state_sha256": CONTROL_SHA256,
        "expected_active_ledger_sha256": LEDGER_SHA256,
        "expected_ledger_revision": 2,
        "signal_id": SIGNAL_ID,
        "delivery_id": DELIVERY_ID,
        "telegram_message_id": 913,
        "canonical_pair": "KMNO/USDT",
        "style": "SWING",
        "direction": "LONG",
        "owner_authorization_id": OWNER_AUTHORIZATION_ID,
        "reservation_transition_id": RESERVATION_TRANSITION_ID,
        "entry_transition_id": ENTRY_TRANSITION_ID,
        "entry_at": ENTRY_AT,
        "state_runtime_uid": 999,
        "state_runtime_gid": 987,
        "mode": "production-reconcile-filled-position",
        "non_interactive": True,
        "result_path": RESULT_PATH,
    }
    if any(getattr(arguments, key) != value for key, value in expected.items()):
        raise ReconciliationError(10, "EXACT_ARGUMENT_CONTRACT_MISMATCH")
    for path in (
        arguments.publication_artifact_path,
        arguments.control_state_path,
        arguments.active_ledger_path,
        arguments.result_path,
    ):
        if not path.is_absolute():
            raise ReconciliationError(10, "ABSOLUTE_PATH_REQUIRED")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        _validate_exact_arguments(arguments)
        incident = verify_incident_evidence_as_root(
            arguments.incident_evidence_root,
            arguments.expected_incident_manifest_sha256,
        )
        verify_runtime_quiescence()
        privilege = permanently_drop_privileges(
            arguments.state_runtime_uid, arguments.state_runtime_gid,
        )
        result = reconcile_owner_reported_filled_position(
            publication_artifact_path=arguments.publication_artifact_path,
            expected_publication_artifact_sha256=arguments.expected_publication_artifact_sha256,
            control_state_path=arguments.control_state_path,
            expected_control_state_sha256=arguments.expected_control_state_sha256,
            active_ledger_path=arguments.active_ledger_path,
            expected_active_ledger_sha256=arguments.expected_active_ledger_sha256,
            expected_ledger_revision=arguments.expected_ledger_revision,
            signal_id=arguments.signal_id, delivery_id=arguments.delivery_id,
            telegram_message_id=arguments.telegram_message_id,
            canonical_pair=arguments.canonical_pair, style=arguments.style,
            direction=arguments.direction,
            owner_authorization_id=arguments.owner_authorization_id,
            reservation_transition_id=arguments.reservation_transition_id,
            entry_transition_id=arguments.entry_transition_id,
            entry_at=arguments.entry_at,
            state_runtime_uid=arguments.state_runtime_uid,
            state_runtime_gid=arguments.state_runtime_gid,
            result_path=arguments.result_path,
            incident_verification=incident, privilege_verification=privilege,
        )
        sys.stdout.buffer.write(_canonical_json(result))
        return 0
    except ReconciliationError as error:
        sys.stderr.write(f"KMNO_RECONCILIATION_FAILED:{error.reason}\n")
        return error.exit_code
    except SystemExit:
        return 10
    except Exception:
        sys.stderr.write("KMNO_RECONCILIATION_FAILED:FAIL_CLOSED\n")
        return 17


if __name__ == "__main__":
    raise SystemExit(main())
