"""Isolated contracts for the one-time PHAROS reconciliation utility."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import pharos_filled_position_reconciliation_v1 as pharos
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine.production_signal_artifact_v1 import (
    publish_completed_publication,
    publish_publication_intent,
)
from engine.production_signal_contract_v1 import (
    build_completed_publication,
    build_delivery_id,
    build_publication_intent,
    build_publication_payload,
    build_signal_geometry,
    build_signal_id,
    canonical_json_bytes,
)
from engine.telegram_owner_control_state_v1 import (
    bind_signal_message,
    initialize_state,
    mutate_state,
)


UID = 999
GID = 987
PAIR = "PHAROS/USDT"
ARTIFACT_SYMBOL = "PHAROS/USDT:USDT"
ENTRY_AT = "2026-07-29T18:30:00Z"


def _hash_payload(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _source_envelope():
    return {
        "schema_version": 1,
        "schema_name": "production-signal-input",
        "source_commit": "1" * 40,
        "source_evaluation_id": "eval-pharos-reconciliation-test",
        "mode": "SWING",
        "evaluated_at": "2026-07-29T17:17:40Z",
        "production_evidence_ref": {
            "manifest_hash": "b" * 64,
            "manifest_path": "production_run_v4_test/manifest.json",
        },
        "outcome_kind": "PUBLISHED_SIGNAL",
        "eligible_setups": [{
            "symbol": ARTIFACT_SYMBOL,
            "side": "LONG",
            "entry_zone": {"min": 0.01821438, "max": 0.01857894},
            "stop_loss": 0.01775,
            "take_profit": {"tp1": 0.0205059, "tp2": 0.0205059},
            "valid_until": "2026-12-31T23:59:59Z",
            "strategy_version": "v4",
            "source_payload_hash": "a" * 64,
        }],
        "component_versions": {
            "master_engine": "master-engine-v4",
            "pre_delivery": "pre-delivery-v4",
            "production_signal_contract": "production-signal-contract-v1",
        },
    }


def _publication(root: Path):
    envelope = _source_envelope()
    setup = envelope["eligible_setups"][0]
    geometry = build_signal_geometry(setup)
    geometry_hash = _hash_payload(geometry)
    signal_id = build_signal_id(
        source_envelope=envelope,
        signal_geometry_hash=geometry_hash,
        source_payload_hash=setup["source_payload_hash"],
    )
    payload = build_publication_payload(
        source_envelope=envelope, signal_id=signal_id, signal_geometry=geometry,
    )
    payload_hash = _hash_payload(payload)
    delivery_id = build_delivery_id(
        signal_id=signal_id, channel="TELEGRAM", destination_id="1276599223",
        publication_payload_hash=payload_hash,
    )
    intent = build_publication_intent(
        source_envelope=envelope, signal_id=signal_id, delivery_id=delivery_id,
        published_at="2026-07-29T17:17:42Z", channel="TELEGRAM",
        destination_id="1276599223", signal_geometry=geometry,
        signal_geometry_hash=geometry_hash, publication_payload=payload,
        publication_payload_hash=payload_hash,
        source_payload_hash=setup["source_payload_hash"],
    )
    completed = build_completed_publication(
        intent=intent,
        delivery_receipt={
            "channel": "TELEGRAM",
            "destination_id": "1276599223",
            "external_delivery_id": "932",
            "delivered_at": "2026-07-29T17:17:44Z",
        },
        failure=None,
    )
    publish_publication_intent(publication_root=root, payload=intent)
    path = publish_completed_publication(publication_root=root, payload=completed)
    return path, completed


def _control_state(path: Path, publication):
    initialize_state(path, timestamp=ENTRY_AT)
    bind_signal_message(
        path, signal_id=publication["signal_id"], canonical_pair=PAIR,
        style="SWING", telegram_chat_id="1276599223",
        telegram_message_id=932, timestamp=ENTRY_AT,
    )

    def add_incident(document):
        document["last_update_id"] = 469110663
        for command_id in pharos.INCIDENT_COMMAND_IDS:
            document["processed_commands"][command_id] = {
                "outcome": "COMMAND_REJECTED_AMBIGUOUS",
                "processed_at": ENTRY_AT,
            }
        return document, None

    mutate_state(path, timestamp=ENTRY_AT, mutation=add_incident)
    for sequence in range(30):
        def add_revision(document, sequence=sequence):
            document["processed_updates"][f"synthetic-{sequence}"] = {
                "outcome": "NO_EFFECT", "processed_at": ENTRY_AT,
            }
            return document, None
        mutate_state(path, timestamp=ENTRY_AT, mutation=add_revision)


def _reserve(ledger_path: Path, ledger, *, signal_id: str, delivery_id: str,
             transition_id: str, symbol: str):
    return active.reserve_published_signal(
        ledger_path,
        expected_revision=ledger["ledger_revision"],
        transaction_id=f"transaction-{transition_id}",
        transition_id=transition_id,
        signal_id=signal_id,
        delivery_id=delivery_id,
        mode="SWING", symbol=symbol,
        published_at="2026-07-29T11:17:37Z",
        source_payload_hash="c" * 64,
        publication_payload_hash="d" * 64,
        updated_at="2026-07-29T11:20:07Z",
    )


def _ledger(path: Path):
    ledger = active.initialize_ledger(path, created_at="2026-07-28T10:59:05Z")
    ledger = _reserve(
        path, ledger, signal_id="other-signal-ena", delivery_id="other-delivery-ena",
        transition_id="other-transition-ena", symbol="ENA/USDT:USDT",
    )
    ledger = _reserve(
        path, ledger, signal_id="other-signal-zro", delivery_id="other-delivery-zro",
        transition_id="other-transition-zro", symbol="ZRO/USDT:USDT",
    )
    ledger = _reserve(
        path, ledger, signal_id=pharos.EXISTING_SIGNAL_ID,
        delivery_id=pharos.EXISTING_DELIVERY_ID,
        transition_id="owner-publication-reconcile-kmno-test",
        symbol="KMNO/USDT:USDT",
    )
    return lifecycle.commit_owner_confirmed_entry(
        ledger_path=path, expected_revision=3,
        transition_id=pharos.EXISTING_LAST_TRANSITION_ID,
        signal_id=pharos.EXISTING_SIGNAL_ID,
        timestamp="2026-07-29T11:20:07Z",
    )


def _state_tree(root: Path):
    root.mkdir(mode=0o700)
    publication_root = root / "production-signals"
    publication_path, publication = _publication(publication_root)
    state_root = root / "owner-blueprint"
    state_root.mkdir()
    control_path = state_root / "telegram-owner-control-state-v1.json"
    ledger_path = state_root / "active-signal-ledger-v2.json"
    _control_state(control_path, publication)
    _ledger(ledger_path)
    result_path = root / "result.json"
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts)):
        if path.is_dir():
            os.chown(path, UID, GID)
            os.chmod(path, 0o700)
        elif path.is_file():
            os.chown(path, UID, GID)
            os.chmod(path, 0o600)
    os.chown(root, UID, GID)
    return {
        "root": root,
        "publication_path": publication_path,
        "publication": publication,
        "control_path": control_path,
        "ledger_path": ledger_path,
        "result_path": result_path,
    }


@pytest.fixture
def isolated_state():
    root = Path(tempfile.mkdtemp(prefix="pharos-reconciliation-test-", dir="/tmp"))
    root.rmdir()
    state = _state_tree(root)
    try:
        yield state
    finally:
        shutil.rmtree(state["root"], ignore_errors=True)


def _seal_synthetic_state(monkeypatch, state):
    publication = state["publication"]
    publication_hash = hashlib.sha256(state["publication_path"].read_bytes()).hexdigest()
    control_hash = hashlib.sha256(state["control_path"].read_bytes()).hexdigest()
    ledger_hash = hashlib.sha256(state["ledger_path"].read_bytes()).hexdigest()
    monkeypatch.setattr(pharos, "SIGNAL_ID", publication["signal_id"])
    monkeypatch.setattr(pharos, "DELIVERY_ID", publication["delivery_id"])
    monkeypatch.setattr(pharos, "PUBLICATION_SHA256", publication_hash)
    monkeypatch.setattr(pharos, "CONTROL_SHA256", control_hash)
    monkeypatch.setattr(pharos, "LEDGER_SHA256", ledger_hash)
    monkeypatch.setattr(pharos, "CONTENT_SHA256", publication["content_hash"])
    monkeypatch.setattr(pharos, "SOURCE_PAYLOAD_SHA256", publication["source_payload_hash"])
    monkeypatch.setattr(
        pharos, "PUBLICATION_PAYLOAD_SHA256", publication["publication_payload_hash"],
    )
    return publication_hash, control_hash, ledger_hash


def _arguments(state, hashes):
    publication_hash, control_hash, ledger_hash = hashes
    publication = state["publication"]
    return {
        "publication_artifact_path": state["publication_path"],
        "expected_publication_artifact_sha256": publication_hash,
        "expected_publication_timestamp": "2026-07-29T17:17:42Z",
        "expected_delivery_timestamp": "2026-07-29T17:17:44Z",
        "expected_valid_until": "2026-12-31T23:59:59Z",
        "expected_content_sha256": publication["content_hash"],
        "expected_source_payload_sha256": publication["source_payload_hash"],
        "expected_publication_payload_sha256": publication["publication_payload_hash"],
        "control_state_path": state["control_path"],
        "expected_control_state_sha256": control_hash,
        "expected_control_state_revision": 32,
        "expected_control_last_update_id": 469110663,
        "active_ledger_path": state["ledger_path"],
        "expected_active_ledger_sha256": ledger_hash,
        "expected_ledger_revision": 4,
        "signal_id": publication["signal_id"],
        "delivery_id": publication["delivery_id"],
        "telegram_message_id": 932,
        "canonical_pair": PAIR,
        "style": "SWING",
        "direction": "LONG",
        "expected_existing_active_signal_id": pharos.EXISTING_SIGNAL_ID,
        "expected_existing_active_delivery_id": pharos.EXISTING_DELIVERY_ID,
        "expected_existing_active_pair": pharos.EXISTING_PAIR,
        "expected_existing_active_style": "SWING",
        "expected_existing_active_state": active.ENTRY_ACTIVE,
        "expected_existing_active_last_transition_id": pharos.EXISTING_LAST_TRANSITION_ID,
        "expected_existing_active_signal_count": 1,
        "expected_existing_active_pair_owner_count": 1,
        "expected_target_active_count": 0,
        "expected_target_pair_owner_count": 0,
        "expected_swing_active_count": 1,
        "expected_swing_available_count": 2,
        "owner_authorization_id": pharos.OWNER_AUTHORIZATION_ID,
        "reservation_transition_id": pharos.RESERVATION_TRANSITION_ID,
        "entry_transition_id": pharos.ENTRY_TRANSITION_ID,
        "entry_at_authority": pharos.ENTRY_AT_AUTHORITY,
        "state_runtime_uid": UID,
        "state_runtime_gid": GID,
        "result_path": state["result_path"],
        "incident_verification": {
            "root_only_incident_seal_verification": "PASS",
            "incident_manifest_sha256": pharos.INCIDENT_MANIFEST_SHA256,
        },
        "release_verification": {"unit_release_parity": "PASS"},
        "privilege_verification": {
            "permanent_privilege_drop_before_state_access": "PASS",
        },
        "timestamp_provider": lambda: ENTRY_AT,
    }


def _run_unprivileged(arguments):
    read_descriptor, write_descriptor = os.pipe()
    process = os.fork()
    if process == 0:
        os.close(read_descriptor)
        try:
            os.setgroups([])
            os.setgid(GID)
            os.setuid(UID)
            result = pharos.reconcile_owner_reported_pharos_filled_position(**arguments)
            payload = {"result": result}
        except pharos.ReconciliationError as error:
            payload = {
                "error": error.reason,
                "exit_code": error.exit_code,
                "effect_count": error.effect_count,
            }
        except Exception as error:
            payload = {"unexpected": type(error).__name__, "message": str(error)}
        os.write(write_descriptor, json.dumps(payload, sort_keys=True).encode("utf-8"))
        os.close(write_descriptor)
        os._exit(0)
    os.close(write_descriptor)
    chunks = []
    while True:
        chunk = os.read(read_descriptor, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    os.close(read_descriptor)
    _, status = os.waitpid(process, 0)
    assert os.waitstatus_to_exitcode(status) == 0
    return json.loads(b"".join(chunks))


def test_exact_pharos_registration_and_entry_preserves_kmno(isolated_state, monkeypatch):
    hashes = _seal_synthetic_state(monkeypatch, isolated_state)
    arguments = _arguments(isolated_state, hashes)
    before = active.load_ledger(isolated_state["ledger_path"])
    kmno_before = before["signals"][pharos.EXISTING_SIGNAL_ID]
    result = _run_unprivileged(arguments)
    assert "unexpected" not in result and "error" not in result
    assert result["result"]["effect_count"] == 1
    assert result["result"]["existing_active_record_preserved"] == "YES"
    ledger = active.load_ledger(isolated_state["ledger_path"])
    assert ledger["signals"][pharos.EXISTING_SIGNAL_ID] == kmno_before
    assert ledger["signals"][isolated_state["publication"]["signal_id"]]["state"] == active.ENTRY_ACTIVE
    capacity = active.inspect_capacity(ledger)
    assert capacity["active_by_mode"]["SWING"] == 2
    assert capacity["remaining_by_mode"]["SWING"] == 1
    assert result["result"]["telegram_send_attempt_count"] == 0
    assert result["result"]["exchange_access_count"] == 0


def test_exact_replay_has_zero_effect(isolated_state, monkeypatch):
    hashes = _seal_synthetic_state(monkeypatch, isolated_state)
    arguments = _arguments(isolated_state, hashes)
    first = _run_unprivileged(arguments)
    assert "result" in first and first["result"]["effect_count"] == 1
    ledger_bytes = isolated_state["ledger_path"].read_bytes()
    result_bytes = isolated_state["result_path"].read_bytes()
    replay = _run_unprivileged(arguments)
    assert replay["result"]["effect_count"] == 0
    assert replay["result"]["transaction_state"] == "VERIFIED_EXACT_REPLAY"
    assert isolated_state["ledger_path"].read_bytes() == ledger_bytes
    assert isolated_state["result_path"].read_bytes() == result_bytes


def test_identity_owner_capacity_pair_and_hash_mismatches_fail_closed(isolated_state, monkeypatch):
    hashes = _seal_synthetic_state(monkeypatch, isolated_state)
    cases = (
        ("owner_authorization_id", "AUTHORIZE_WRONG"),
        ("canonical_pair", "BTC/USDT"),
        ("expected_swing_available_count", 1),
        ("expected_publication_artifact_sha256", "0" * 64),
    )
    initial = isolated_state["ledger_path"].read_bytes()
    for key, value in cases:
        arguments = _arguments(isolated_state, hashes)
        arguments[key] = value
        result = _run_unprivileged(arguments)
        assert "error" in result and result["effect_count"] == 0
        assert isolated_state["ledger_path"].read_bytes() == initial
        assert not isolated_state["result_path"].exists()


def test_registration_only_is_safe_and_resumable(isolated_state, monkeypatch):
    hashes = _seal_synthetic_state(monkeypatch, isolated_state)
    arguments = _arguments(isolated_state, hashes)

    def fail_entry(**_kwargs):
        raise RuntimeError("isolated entry failure")

    monkeypatch.setattr(pharos.lifecycle, "commit_owner_confirmed_entry", fail_entry)
    failed = _run_unprivileged(arguments)
    assert failed["exit_code"] == 16
    ledger = active.load_ledger(isolated_state["ledger_path"])
    target = ledger["signals"][isolated_state["publication"]["signal_id"]]
    capacity = active.inspect_capacity(ledger)
    assert target["state"] == active.PUBLISHED_PENDING_ENTRY
    assert ledger["signals"][pharos.EXISTING_SIGNAL_ID]["state"] == active.ENTRY_ACTIVE
    assert capacity["active_by_mode"]["SWING"] == 1
    assert capacity["remaining_by_mode"]["SWING"] == 2
    assert not isolated_state["result_path"].exists()


def test_no_transport_network_exchange_or_trading_imports_or_effects():
    source = Path(pharos.__file__).read_text(encoding="utf-8")
    banned = (
        "import httpx", "from httpx", "import requests", "from requests",
        "import telegram", "from telegram", "import ccxt", "from ccxt",
        "import binance", "from binance", "create_order", "place_order",
    )
    assert not any(token in source for token in banned)
    actions = {action.dest for action in pharos._parser()._actions}
    assert "dry_run" not in actions
    assert {
        "mode", "non_interactive", "result_path", "require_result_path_absent",
        "require_unit_release_parity",
    }.issubset(actions)


def test_runtime_quiescence_and_privilege_drop_contract(tmp_path, monkeypatch):
    def properties(unit, _names):
        if unit.endswith(".timer"):
            return {
                "UnitFileState": "disabled", "ActiveState": "inactive",
                "NextElapseUSecRealtime": "",
            }
        return {"ActiveState": "inactive", "Result": "success", "MainPID": "0"}

    monkeypatch.setattr(pharos, "_systemd_properties", properties)
    monkeypatch.setattr(pharos, "_process_count", lambda _markers: 0)
    assert pharos.verify_runtime_quiescence()["controller_process_count"] == 0

    release_root = "/opt/ai-crypto-signal-agent-releases/" + "f" * 40
    reference = tmp_path / "installed-release.path"
    scanner = tmp_path / "scanner.service"
    controller = tmp_path / "controller.service"
    reference.write_text(release_root + "\n", encoding="ascii")
    scanner.write_text(
        f"ConditionPathExists={release_root}/.f4-release-manifest\n"
        f"ExecStart={release_root}/deploy/operational_v1/bin/ai-crypto-signal-agent-run-once\n",
        encoding="utf-8",
    )
    controller.write_text(
        f"ConditionPathExists={release_root}/.f4-release-manifest\n"
        f"ExecStart={release_root}/deploy/operational_v1/bin/ai-crypto-signal-agent-telegram-control\n",
        encoding="utf-8",
    )
    reference.chmod(0o400)
    scanner.chmod(0o644)
    controller.chmod(0o644)
    assert pharos.verify_release_parity(reference, scanner, controller)["unit_release_parity"] == "PASS"
    controller.write_text(controller.read_text().replace("f" * 40, "e" * 40))
    controller.chmod(0o644)
    with pytest.raises(pharos.ReconciliationError, match="UNIT_RELEASE_PARITY_FAILED"):
        pharos.verify_release_parity(reference, scanner, controller)

    source = Path(pharos.__file__).read_text(encoding="utf-8")
    main = source[source.index("def main("):]
    assert main.index("verify_incident_evidence_as_root") < main.index("permanently_drop_privileges")
    assert main.index("verify_runtime_quiescence") < main.index("permanently_drop_privileges")
    assert main.index("verify_release_parity") < main.index("permanently_drop_privileges")
    assert main.index("permanently_drop_privileges") < main.index("reconcile_owner_reported_pharos_filled_position")
