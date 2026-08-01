"""Isolated contracts for the one-time KMNO reconciliation utility."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import kmno_filled_position_reconciliation_v1 as kmno
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
PAIR = "KMNO/USDT"
ARTIFACT_SYMBOL = "KMNO/USDT:USDT"


def _hash_payload(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _source_envelope():
    return {
        "schema_version": 1,
        "schema_name": "production-signal-input",
        "source_commit": "1" * 40,
        "source_evaluation_id": "eval-kmno-reconciliation-test",
        "mode": "SWING",
        "evaluated_at": "2026-07-29T11:17:30Z",
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
        published_at="2026-07-29T11:17:37Z", channel="TELEGRAM",
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
            "external_delivery_id": "913",
            "delivered_at": "2026-07-29T11:17:41Z",
        },
        failure=None,
    )
    publish_publication_intent(publication_root=root, payload=intent)
    path = publish_completed_publication(publication_root=root, payload=completed)
    return path, completed


def _add_incident_commands(state):
    def apply(document):
        for command_id in kmno.INCIDENT_COMMAND_IDS:
            document["processed_commands"][command_id] = {
                "outcome": "COMMAND_REJECTED_AMBIGUOUS",
                "processed_at": kmno.ENTRY_AT,
            }
        return document, None

    mutate_state(state, timestamp=kmno.ENTRY_AT, mutation=apply)


def _pending_other(ledger_path, ledger, suffix, symbol):
    return active.reserve_published_signal(
        ledger_path,
        expected_revision=ledger["ledger_revision"],
        transaction_id=f"other-transaction-{suffix}",
        transition_id=f"other-transition-{suffix}",
        signal_id=f"other-signal-{suffix}",
        delivery_id=f"other-delivery-{suffix}",
        mode="SWING", symbol=symbol,
        published_at="2026-07-29T11:00:00Z",
        source_payload_hash="c" * 64,
        publication_payload_hash="d" * 64,
        updated_at="2026-07-29T11:00:00Z",
    )


def _state_tree():
    root = Path(tempfile.mkdtemp(prefix="kmno-reconciliation-test-", dir="/tmp"))
    os.chmod(root, 0o700)
    publication_root = root / "production-signals"
    publication_path, publication = _publication(publication_root)
    state_root = root / "owner-blueprint"
    state_root.mkdir()
    control_path = state_root / "telegram-owner-control-state-v1.json"
    ledger_path = state_root / "active-signal-ledger-v2.json"
    initialize_state(control_path, timestamp=kmno.ENTRY_AT)
    bind_signal_message(
        control_path, signal_id=publication["signal_id"],
        canonical_pair=PAIR, style="SWING", telegram_chat_id="1276599223",
        telegram_message_id=913, timestamp=kmno.ENTRY_AT,
    )
    _add_incident_commands(control_path)
    ledger = active.initialize_ledger(ledger_path, created_at=kmno.ENTRY_AT)
    ledger = _pending_other(ledger_path, ledger, "one", "ENA/USDT:USDT")
    _pending_other(ledger_path, ledger, "two", "ZRO/USDT:USDT")
    result_path = root / "result.json"
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts)):
        if path.is_dir():
            os.chmod(path, 0o700)
        elif path.is_file():
            os.chmod(path, 0o600)
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
    state = _state_tree()
    try:
        yield state
    finally:
        shutil.rmtree(state["root"], ignore_errors=True)


def _seal_synthetic_state(monkeypatch, state):
    publication = state["publication"]
    publication_hash = hashlib.sha256(state["publication_path"].read_bytes()).hexdigest()
    control_hash = hashlib.sha256(state["control_path"].read_bytes()).hexdigest()
    ledger_hash = hashlib.sha256(state["ledger_path"].read_bytes()).hexdigest()
    monkeypatch.setattr(kmno, "SIGNAL_ID", publication["signal_id"])
    monkeypatch.setattr(kmno, "DELIVERY_ID", publication["delivery_id"])
    monkeypatch.setattr(kmno, "PUBLICATION_SHA256", publication_hash)
    monkeypatch.setattr(kmno, "CONTROL_SHA256", control_hash)
    monkeypatch.setattr(kmno, "LEDGER_SHA256", ledger_hash)
    monkeypatch.setattr(kmno, "CONTENT_SHA256", publication["content_hash"])
    monkeypatch.setattr(kmno, "SOURCE_PAYLOAD_SHA256", publication["source_payload_hash"])
    monkeypatch.setattr(
        kmno, "PUBLICATION_PAYLOAD_SHA256", publication["publication_payload_hash"],
    )
    fixture_root = state["root"].resolve()
    fixture_uid = os.geteuid()
    fixture_gid = os.getegid()
    original_read_regular = kmno._read_regular

    def fixture_read_regular(
        path,
        *,
        uid=None,
        gid=None,
        mode=None,
        exit_code=13,
    ):
        resolved = Path(path).resolve()
        inside_fixture = (
            resolved == fixture_root
            or fixture_root in resolved.parents
        )
        if inside_fixture:
            return original_read_regular(
                path,
                uid=fixture_uid if uid is not None else None,
                gid=fixture_gid if gid is not None else None,
                mode=mode,
                exit_code=exit_code,
            )
        return original_read_regular(
            path,
            uid=uid,
            gid=gid,
            mode=mode,
            exit_code=exit_code,
        )

    monkeypatch.setattr(
        kmno,
        "_read_regular",
        fixture_read_regular,
    )
    return publication_hash, control_hash, ledger_hash


def _arguments(state, hashes):
    publication_hash, control_hash, ledger_hash = hashes
    publication = state["publication"]
    return {
        "publication_artifact_path": state["publication_path"],
        "expected_publication_artifact_sha256": publication_hash,
        "control_state_path": state["control_path"],
        "expected_control_state_sha256": control_hash,
        "active_ledger_path": state["ledger_path"],
        "expected_active_ledger_sha256": ledger_hash,
        "expected_ledger_revision": 2,
        "signal_id": publication["signal_id"],
        "delivery_id": publication["delivery_id"],
        "telegram_message_id": 913,
        "canonical_pair": PAIR,
        "style": "SWING",
        "direction": "LONG",
        "owner_authorization_id": kmno.OWNER_AUTHORIZATION_ID,
        "reservation_transition_id": kmno.RESERVATION_TRANSITION_ID,
        "entry_transition_id": kmno.ENTRY_TRANSITION_ID,
        "entry_at": kmno.ENTRY_AT,
        "state_runtime_uid": UID,
        "state_runtime_gid": GID,
        "identity_provider": lambda: (UID, GID),
        "result_path": state["result_path"],
        "incident_verification": {
            "root_only_incident_seal_verification": "PASS",
            "incident_manifest_sha256": kmno.INCIDENT_MANIFEST_SHA256,
        },
        "privilege_verification": {
            "permanent_privilege_drop_before_state_access": "PASS",
        },
    }


def _run_unprivileged(arguments):
    read_descriptor, write_descriptor = os.pipe()
    process = os.fork()
    if process == 0:
        os.close(read_descriptor)
        try:
            result = kmno.reconcile_owner_reported_filled_position(**arguments)
            payload = {"result": result}
        except kmno.ReconciliationError as error:
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


def test_exact_transaction_creates_one_entry_slot_pair_and_replays_effect_zero(
    isolated_state, monkeypatch,
):
    hashes = _seal_synthetic_state(monkeypatch, isolated_state)
    arguments = _arguments(isolated_state, hashes)
    first = _run_unprivileged(arguments)
    assert "unexpected" not in first and "error" not in first
    result = first["result"]
    assert result["effect_count"] == 1
    assert result["publication_registration_created_count"] == 1
    assert result["entry_active_creation_count"] == 1
    assert result["telegram_send_attempt_count"] == 0
    assert result["exchange_access_count"] == 0
    ledger = active.load_ledger(isolated_state["ledger_path"])
    target = ledger["signals"][isolated_state["publication"]["signal_id"]]
    capacity = active.inspect_capacity(ledger)
    assert target["state"] == active.ENTRY_ACTIVE
    assert target["entry_at"] == kmno.ENTRY_AT
    assert capacity["active_by_mode"]["SWING"] == 1
    assert capacity["remaining_by_mode"]["SWING"] == 2
    assert sum(
        record["state"] == active.ENTRY_ACTIVE
        and record["symbol"] == ARTIFACT_SYMBOL
        for record in ledger["signals"].values()
    ) == 1
    result_bytes = isolated_state["result_path"].read_bytes()

    replay = _run_unprivileged(arguments)
    assert replay["result"]["effect_count"] == 0
    assert replay["result"]["transaction_state"] == "VERIFIED_EXACT_REPLAY"
    assert isolated_state["result_path"].read_bytes() == result_bytes


def test_entry_failure_preserves_registration_without_slot_or_pair(
    isolated_state, monkeypatch,
):
    hashes = _seal_synthetic_state(monkeypatch, isolated_state)
    arguments = _arguments(isolated_state, hashes)

    def fail_entry(**_kwargs):
        raise RuntimeError("isolated entry failure")

    monkeypatch.setattr(kmno.lifecycle, "commit_owner_confirmed_entry", fail_entry)
    failed = _run_unprivileged(arguments)
    assert failed["exit_code"] == 16
    ledger = active.load_ledger(isolated_state["ledger_path"])
    target = ledger["signals"][isolated_state["publication"]["signal_id"]]
    capacity = active.inspect_capacity(ledger)
    assert target["state"] == active.PUBLISHED_PENDING_ENTRY
    assert capacity["active_by_mode"]["SWING"] == 0
    assert capacity["remaining_by_mode"]["SWING"] == 3
    assert not isolated_state["result_path"].exists()


def test_source_is_non_network_non_order_and_cli_has_no_dry_run():
    source = Path(kmno.__file__).read_text(encoding="utf-8")
    banned_imports = (
        "import httpx", "from httpx", "import requests", "from requests",
        "import telegram", "from telegram", "import ccxt", "from ccxt",
        "import binance", "from binance",
    )
    assert not any(token in source for token in banned_imports)
    actions = {action.dest for action in kmno._parser()._actions}
    assert "dry_run" not in actions
    assert {"mode", "non_interactive", "result_path"}.issubset(actions)


def test_controller_template_render_changes_only_two_release_tokens():
    template_path = Path(
        "deploy/operational_v1/systemd/ai-crypto-signal-agent-telegram-control.service.in",
    )
    template = template_path.read_bytes()
    release_root = "/opt/ai-crypto-signal-agent-releases/" + "f" * 40
    rendered = kmno.render_controller_unit(template, release_root)
    assert template.count(b"@@RELEASE_ROOT@@") == 2
    assert rendered.count(release_root.encode("ascii")) == 2
    assert b"@@RELEASE_ROOT@@" not in rendered
    assert b"LoadCredentialEncrypted=telegram_bot_token:" in rendered
    assert b"User=ai-crypto-signal-agent" in rendered
    assert b"Restart=on-failure" in rendered
    assert b"NoNewPrivileges=true" in rendered
    assert b"engine.run_production_signal_v1" not in rendered
    with pytest.raises(ValueError):
        kmno.render_controller_unit(template.replace(b"@@RELEASE_ROOT@@", b"x", 1), release_root)
