from __future__ import annotations

import ast
import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from engine import active_signal_ledger_v1 as active
from engine import e6_owner_state_lifecycle_binding_v1 as subject
from engine import e6_publication_envelope_v1 as envelope_module
from engine import passive_signal_lifecycle_service_v1 as lifecycle
from engine.production_signal_contract_v1 import build_delivery_id
from test_e6_publication_envelope_v1 import _envelope, _unsafe_clone


NOW = "2026-07-30T13:00:00Z"
PUBLISHED_AT = "2026-07-30T12:59:59Z"


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _completed_publication_evidence(envelope, **changes):
    payload = {
        "signal_id": envelope.signal_id,
        "mode": envelope.mode,
        "symbol": envelope.canonical_pair,
        "presentation": "validated Slice 05 envelope",
    }
    publication_payload_hash = _sha256(payload)
    evidence = {
        "delivery_state": "DELIVERY_SUCCEEDED",
        "signal_id": envelope.signal_id,
        "delivery_id": build_delivery_id(
            signal_id=envelope.signal_id,
            channel="TELEGRAM",
            destination_id="isolated-owner-state-test",
            publication_payload_hash=publication_payload_hash,
        ),
        "mode": envelope.mode,
        "published_at": PUBLISHED_AT,
        "source_payload_hash": envelope.source_payload_hash,
        "publication_payload_hash": publication_payload_hash,
        "content_hash": envelope.publication_envelope_sha256,
        "publication_payload": payload,
    }
    evidence.update(changes)
    return evidence


def _initialized_ledger(tmp_path: Path) -> Path:
    path = tmp_path / "isolated-active-ledger.json"
    active.initialize_ledger(path, created_at="2026-07-30T12:00:00Z")
    return path


def _bind(envelope, ledger_path: Path, evidence=None):
    ledger = active.load_ledger(ledger_path)
    return subject.bind_e6_publication_to_owner_state_v1(
        envelope=envelope,
        active_ledger_path=ledger_path,
        expected_active_ledger_revision=ledger["ledger_revision"],
        publication_evidence=(
            _completed_publication_evidence(envelope)
            if evidence is None
            else evidence
        ),
        timestamp=NOW,
    )


def _rehash_envelope(envelope, **changes):
    changed = _unsafe_clone(envelope, **changes)
    digest = hashlib.sha256(
        changed.canonical_publication_envelope_json().encode("utf-8")
    ).hexdigest()
    return _unsafe_clone(changed, publication_envelope_sha256=digest)


def test_binding_contract_is_frozen_slotted_and_has_no_secret_or_client_fields(
    tmp_path,
):
    envelope, *_ = _envelope(tmp_path)
    result = _bind(envelope, _initialized_ledger(tmp_path))
    binding = result.binding

    assert subject.E6OwnerStateLifecycleBindingV1.__slots__
    assert subject.E6OwnerStateLifecycleBindingResultV1.__slots__
    assert "__dict__" not in subject.E6OwnerStateLifecycleBindingV1.__slots__
    assert "__dict__" not in subject.E6OwnerStateLifecycleBindingResultV1.__slots__
    with pytest.raises(FrozenInstanceError):
        binding.signal_id = "changed"
    with pytest.raises(FrozenInstanceError):
        result.classification = subject.HOLD_CONFLICT

    field_names = {field.name.lower() for field in fields(type(binding))}
    prohibited_exact = {
        "token",
        "credential",
        "secret",
        "password",
        "client",
        "transport",
        "exchange_handle",
        "exchange_client",
        "provider_client",
        "telegram_client",
        "chat_id",
        "message_id",
    }
    assert field_names.isdisjoint(prohibited_exact)
    assert not any(name.endswith(("_client", "_handle", "_object")) for name in field_names)


def test_binding_identity_is_canonical_deterministic_and_lineage_sensitive(
    tmp_path,
):
    envelope_root = tmp_path / "first-envelope"
    envelope_root.mkdir(parents=True, exist_ok=True)
    envelope, *_ = _envelope(envelope_root)
    evidence = _completed_publication_evidence(envelope)
    first = _bind(envelope, _initialized_ledger(tmp_path / "first"), evidence)
    second = _bind(envelope, _initialized_ledger(tmp_path / "second"), evidence)

    assert first.binding == second.binding
    assert first.binding.binding_sha256 == second.binding.binding_sha256
    assert first.binding.canonical_binding_json() == json.dumps(
        {
            key: value
            for key, value in first.binding.to_mapping().items()
            if key != "binding_sha256"
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    assert first.binding.binding_sha256 == hashlib.sha256(
        first.binding.canonical_binding_json().encode("utf-8")
    ).hexdigest()

    changed_evidence = _completed_publication_evidence(
        envelope,
        delivery_id="PDL-" + "a" * 64,
    )
    changed = _bind(
        envelope,
        _initialized_ledger(tmp_path / "changed"),
        changed_evidence,
    )
    assert changed.binding.binding_sha256 != first.binding.binding_sha256
    assert changed.binding.delivery_id != first.binding.delivery_id


def test_eligible_envelope_creates_one_inspectable_pending_registration(tmp_path):
    envelope, *_ = _envelope(tmp_path)
    ledger_path = _initialized_ledger(tmp_path)
    before = active.load_ledger(ledger_path)
    before_capacity = active.inspect_capacity(before)

    result = _bind(envelope, ledger_path)
    after = active.load_ledger(ledger_path)
    record = after["signals"][envelope.signal_id]

    assert result.classification == subject.CREATED
    assert result.registration_applied is True
    assert result.replay is False
    assert result.binding.publication_envelope_sha256 == (
        envelope.publication_envelope_sha256
    )
    assert result.binding.signal_id == envelope.signal_id
    assert result.binding.thesis_fingerprint_sha256 == (
        envelope.thesis_fingerprint_sha256
    )
    assert result.binding.owner_action_state == (
        envelope_module.OWNER_ACTION_AWAITING_MANUAL_DECISION
    )
    assert result.binding.manual_owner_authority_statement == (
        envelope_module.MANUAL_OWNER_AUTHORITY_STATEMENT
    )
    assert record["delivery_id"] == result.binding.delivery_id
    assert record["state"] == active.PUBLISHED_PENDING_ENTRY
    assert result.current_state == active.PUBLISHED_PENDING_ENTRY
    assert result.lifecycle_inspection_result == lifecycle.PUBLISHED_ENTRY_INSPECTED
    assert active.inspect_capacity(after) == before_capacity
    assert sum(
        record["state"] == active.ENTRY_ACTIVE
        for record in after["signals"].values()
    ) == 0


def test_exact_replay_is_idempotent_and_preserves_state_bytes(tmp_path):
    envelope, *_ = _envelope(tmp_path)
    ledger_path = _initialized_ledger(tmp_path)
    created = _bind(envelope, ledger_path)
    bytes_after_create = ledger_path.read_bytes()
    document_after_create = active.load_ledger(ledger_path)

    replay = _bind(envelope, ledger_path)

    assert created.classification == subject.CREATED
    assert replay.classification == subject.IDEMPOTENT_REPLAY
    assert replay.registration_applied is False
    assert replay.replay is True
    assert replay.binding == created.binding
    assert replay.active_ledger_revision == document_after_create["ledger_revision"]
    assert ledger_path.read_bytes() == bytes_after_create
    assert len(active.load_ledger(ledger_path)["signals"]) == 1


def test_conflicting_envelope_lineage_holds_without_overwrite(tmp_path):
    envelope, *_ = _envelope(tmp_path)
    ledger_path = _initialized_ledger(tmp_path)
    created = _bind(envelope, ledger_path)
    bytes_before_conflict = ledger_path.read_bytes()
    conflicting = _rehash_envelope(
        envelope,
        thesis_fingerprint_sha256="f" * 64,
    )

    held = _bind(
        conflicting,
        ledger_path,
        _completed_publication_evidence(envelope),
    )

    assert held.classification == subject.HOLD_CONFLICT
    assert held.conflict is True
    assert held.registration_applied is False
    assert held.replay is False
    assert held.binding.binding_sha256 != created.binding.binding_sha256
    assert ledger_path.read_bytes() == bytes_before_conflict
    assert len(active.load_ledger(ledger_path)["signals"]) == 1


@pytest.mark.parametrize(
    "envelope_change,evidence_change,expected_error",
    (
        (
            {"owner_action_state": "ENTRY_ACTIVE"},
            {},
            "invalid E6 publication envelope",
        ),
        (
            {"publication_eligibility_decision": "HOLD"},
            {},
            "invalid E6 publication envelope",
        ),
        (
            {"canonical_pair": "ETH/USDT"},
            {},
            "invalid E6 owner state lifecycle binding",
        ),
        (
            {"mode": "SCALP"},
            {},
            "invalid E6 owner state lifecycle binding",
        ),
        (
            {"side": "UNKNOWN"},
            {},
            "invalid E6 publication envelope",
        ),
        (
            {"valid_until": "2026-07-30T12:30:00Z"},
            {},
            "invalid E6 owner state lifecycle binding",
        ),
        (
            {},
            {"delivery_state": "DELIVERY_FAILED"},
            "invalid E6 owner state lifecycle binding",
        ),
        (
            {},
            {"signal_id": "PSG-" + "a" * 64},
            "invalid E6 owner state lifecycle binding",
        ),
        (
            {},
            {"source_payload_hash": "b" * 64},
            "invalid E6 owner state lifecycle binding",
        ),
    ),
)
def test_ineligible_malformed_or_mixed_lineage_fails_before_registration(
    tmp_path,
    envelope_change,
    evidence_change,
    expected_error,
):
    envelope, *_ = _envelope(tmp_path)
    changed_envelope = (
        _rehash_envelope(envelope, **envelope_change)
        if envelope_change
        else envelope
    )
    evidence = _completed_publication_evidence(envelope)
    evidence.update(evidence_change)
    ledger_path = _initialized_ledger(tmp_path)
    before = ledger_path.read_bytes()

    with pytest.raises(
        ValueError,
        match=f"^{expected_error}$",
    ):
        _bind(changed_envelope, ledger_path, evidence)

    assert ledger_path.read_bytes() == before
    assert active.load_ledger(ledger_path)["signals"] == {}


def test_registration_has_zero_owner_decision_slot_pair_lock_or_entry_effect(
    tmp_path,
):
    envelope, *_ = _envelope(tmp_path)
    ledger_path = _initialized_ledger(tmp_path)
    result = _bind(envelope, ledger_path)
    document = active.load_ledger(ledger_path)

    assert result.owner_decision_required is True
    assert result.publication_transport_performed is False
    assert result.telegram_send_performed is False
    assert result.owner_decision_synthesized is False
    assert result.entry_active_mutated is False
    assert result.slot_mutated is False
    assert result.pair_lock_mutated is False
    assert result.exchange_order_performed is False
    assert active.inspect_capacity(document)["total_active"] == 0
    assert document["signals"][envelope.signal_id]["state"] == (
        active.PUBLISHED_PENDING_ENTRY
    )
    assert {
        transition["operation"]
        for transition in document["transitions"].values()
    } == {"RESERVE"}

    entry_source = inspect.getsource(lifecycle.commit_owner_confirmed_entry)
    module_source = inspect.getsource(subject)
    assert "active.mark_entry_active(" in entry_source
    assert "commit_owner_confirmed_entry" not in module_source
    assert "mark_entry_active" not in module_source


def test_module_has_no_external_transport_runtime_or_production_path_surface():
    source = inspect.getsource(subject)
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert not imported_roots & {
        "anthropic",
        "ccxt",
        "httpx",
        "requests",
        "socket",
        "telegram",
        "urllib",
    }
    for prohibited in (
        "/opt/",
        "TELEGRAM_BOT_TOKEN",
        "API_KEY",
        "send_message",
        "create_order",
        "subprocess",
        "systemctl",
    ):
        assert prohibited not in source
