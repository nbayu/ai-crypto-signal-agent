import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

import engine.e4_thesis_history_store_v1 as subject
from engine.e4_thesis_fingerprint_v1 import E4ThesisFingerprintV1
from engine.e4_thesis_history_v1 import (
    append_e4_thesis_history_event_v1,
    create_e4_thesis_history_v1,
)


def _identity(**changes):
    values = {
        "venue": "BINANCE_USDM",
        "canonical_pair": "BTC/USDT",
        "mode": "SWING",
        "side": "LONG",
        "strategy_version": "master-engine-v4",
        "mode_profile_version": "mode-profile-v1",
        "structure_timeframe": "1h",
        "structure_generation_id": "structure:g1",
        "anchor_low_at": "2026-07-30T00:00:00Z",
        "anchor_low_tick": 9000,
        "anchor_high_at": "2026-07-30T01:00:00Z",
        "anchor_high_tick": 12000,
        "golden_zone_low_tick": 10854,
        "golden_zone_high_tick": 11358,
        "stop_loss_tick": 8950,
        "target_policy_version": "e3-structural-targets-policy-v1",
        "tp1_destination_id": "destination:tp1",
        "tp1_tick": 12146,
        "tp2_destination_id": "destination:tp2",
        "tp2_tick": 12528,
        "trigger_type": "closed 15m BOS/CHOCH aligned with structure",
        "trigger_timeframe": "15m",
        "trigger_generation_id": "trg-" + "1" * 64,
        "trigger_candle_close_at": "2026-07-30T00:15:00Z",
    }
    values.update(changes)
    return values


def _fingerprint(**changes):
    identity = _identity(**changes)
    preimage = json.dumps(
        {
            "fingerprint_version": "thesis-fingerprint-v1",
            "identity": identity,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return E4ThesisFingerprintV1(
        fingerprint_version="thesis-fingerprint-v1",
        **identity,
        identity_sha256=hashlib.sha256(preimage.encode("utf-8")).hexdigest(),
    )


def _paths(tmp_path):
    root = tmp_path / "isolated-store"
    root.mkdir()
    return root, root / "BTC-USDT.e4-thesis-history.json"


def _initial_history(fingerprint=None):
    if fingerprint is None:
        fingerprint = _fingerprint()
    return create_e4_thesis_history_v1(
        fingerprint=fingerprint,
        initial_state="ARMED",
    )


def _write_initial(root, store, history=None):
    if history is None:
        history = _initial_history()
    return subject.compare_and_write_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
        expected_store_revision=None,
        expected_document_sha256=None,
        history=history,
    )


def _extend_actionable(history):
    fingerprint = history.events[-1].fingerprint
    return append_e4_thesis_history_event_v1(
        history=history,
        fingerprint=fingerprint,
        state="ACTIONABLE",
        publication_succeeded=False,
        price_exited_zone=False,
        reset_decision=None,
    )


def _write_json(path, mapping):
    path.write_text(
        json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_exact_store_version_and_frozen_slotted_document(tmp_path):
    root, store = _paths(tmp_path)
    document = _write_initial(root, store)
    assert subject.E4_THESIS_HISTORY_STORE_VERSION == (
        "e4-thesis-history-store-v1"
    )
    assert subject.E4ThesisHistoryStoreDocumentV1.__dataclass_params__.frozen
    assert not hasattr(document, "__dict__")
    assert tuple(field.name for field in dataclasses.fields(document)) == (
        "store_version",
        "canonical_pair",
        "store_revision",
        "history",
        "document_sha256",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        document.store_revision = 2


def test_document_mapping_canonical_pair_and_sha256_are_deterministic(tmp_path):
    root, store = _paths(tmp_path)
    document = _write_initial(root, store)
    mapping = document.to_mapping()
    supplied_hash = mapping.pop("document_sha256")
    canonical = json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert document.canonical_pair == "BTC/USDT"
    assert document.store_revision == document.history.revision == 1
    assert document.canonical_document_json() == canonical
    assert supplied_hash == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert subject.load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    ) == document


def test_bool_as_int_store_revision_fails_closed(tmp_path):
    root, store = _paths(tmp_path)
    document = _write_initial(root, store)
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        dataclasses.replace(document, store_revision=True)


@pytest.mark.parametrize("which", ("root", "store"))
def test_absolute_root_and_store_path_are_required(tmp_path, which):
    root, store = _paths(tmp_path)
    if which == "root":
        root = Path("relative-root")
    else:
        store = Path("relative.e4-thesis-history.json")
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.load_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
        )


def test_path_traversal_and_wrong_suffix_fail_closed(tmp_path):
    root, store = _paths(tmp_path)
    nested = root / "nested"
    nested.mkdir()
    traversal = nested / ".." / store.name
    for invalid_store in (traversal, root / "history.json"):
        with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
            subject.load_e4_thesis_history_store_v1(
                authorized_store_root=root,
                store_path=invalid_store,
            )


def test_root_symlink_fails_closed(tmp_path):
    real_root, store = _paths(tmp_path)
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(real_root, target_is_directory=True)
    linked_store = linked_root / store.name
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.load_e4_thesis_history_store_v1(
            authorized_store_root=linked_root,
            store_path=linked_store,
        )


@pytest.mark.parametrize("companion", ("store", "lock", "temporary"))
def test_store_lock_and_temporary_symlinks_fail_closed(tmp_path, companion):
    root, store = _paths(tmp_path)
    target = root / "target"
    target.write_bytes(b"target")
    path = {
        "store": store,
        "lock": Path(str(store) + ".lock"),
        "temporary": Path(str(store) + ".tmp"),
    }[companion]
    path.symlink_to(target)
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.load_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
        )


def test_missing_store_returns_none(tmp_path):
    root, store = _paths(tmp_path)
    assert subject.load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    ) is None


def test_initial_atomic_create_and_existing_compare_write(tmp_path):
    root, store = _paths(tmp_path)
    history = _initial_history()
    initial = _write_initial(root, store, history)
    extended = _extend_actionable(history)
    updated = subject.compare_and_write_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
        expected_store_revision=initial.store_revision,
        expected_document_sha256=initial.document_sha256,
        history=extended,
    )
    assert initial.store_revision == 1
    assert updated.store_revision == 2
    assert updated.history == extended
    assert not Path(str(store) + ".tmp").exists()


@pytest.mark.parametrize("stale", ("revision", "hash"))
def test_stale_revision_or_hash_fails_closed(tmp_path, stale):
    root, store = _paths(tmp_path)
    history = _initial_history()
    current = _write_initial(root, store, history)
    extended = _extend_actionable(history)
    revision = current.store_revision
    document_hash = current.document_sha256
    if stale == "revision":
        revision += 1
    else:
        document_hash = "0" * 64
    before = store.read_bytes()
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.compare_and_write_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
            expected_store_revision=revision,
            expected_document_sha256=document_hash,
            history=extended,
        )
    assert store.read_bytes() == before


def test_absent_and_existing_expectation_mismatch_fail_closed(tmp_path):
    root, store = _paths(tmp_path)
    history = _initial_history()
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.compare_and_write_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
            expected_store_revision=1,
            expected_document_sha256="0" * 64,
            history=history,
        )
    current = _write_initial(root, store, history)
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.compare_and_write_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
            expected_store_revision=None,
            expected_document_sha256=None,
            history=_extend_actionable(history),
        )
    assert subject.load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    ) == current


@pytest.mark.parametrize("corruption", ("utf8", "json", "empty"))
def test_malformed_utf8_json_and_empty_store_fail_closed(tmp_path, corruption):
    root, store = _paths(tmp_path)
    content = {
        "utf8": b"\xff\xfe",
        "json": b"{not-json}\n",
        "empty": b"",
    }[corruption]
    store.write_bytes(content)
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.load_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
        )
    assert store.read_bytes() == content


@pytest.mark.parametrize(
    "tamper",
    (
        "missing_key",
        "extra_key",
        "document_hash",
        "history_hash",
        "canonical_pair",
        "revision",
        "fingerprint_history",
    ),
)
def test_document_and_nested_history_corruption_fail_closed(tmp_path, tamper):
    root, store = _paths(tmp_path)
    current = _write_initial(root, store)
    mapping = current.to_mapping()
    if tamper == "missing_key":
        mapping.pop("store_revision")
    elif tamper == "extra_key":
        mapping["extra"] = "forbidden"
    elif tamper == "document_hash":
        mapping["document_sha256"] = "0" * 64
    elif tamper == "history_hash":
        mapping["history"]["history_sha256"] = "0" * 64
    elif tamper == "canonical_pair":
        mapping["canonical_pair"] = "ETH/USDT"
    elif tamper == "revision":
        mapping["store_revision"] = 2
    else:
        mapping["history"]["fingerprint_history"] = []
    _write_json(store, mapping)
    before = store.read_bytes()
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.load_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
        )
    assert store.read_bytes() == before


def test_prior_event_prefix_mutation_fails_closed(tmp_path):
    root, store = _paths(tmp_path)
    current_history = _initial_history()
    current = _write_initial(root, store, current_history)
    other = _initial_history(_fingerprint(tp1_tick=12147))
    candidate = _extend_actionable(other)
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.compare_and_write_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
            expected_store_revision=current.store_revision,
            expected_document_sha256=current.document_sha256,
            history=candidate,
        )


def test_preexisting_temporary_file_fails_without_overwrite(tmp_path):
    root, store = _paths(tmp_path)
    history = _initial_history()
    current = _write_initial(root, store, history)
    before = store.read_bytes()
    temporary = Path(str(store) + ".tmp")
    temporary.write_bytes(b"unexplained")
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        subject.compare_and_write_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
            expected_store_revision=current.store_revision,
            expected_document_sha256=current.document_sha256,
            history=_extend_actionable(history),
        )
    assert store.read_bytes() == before
    assert temporary.read_bytes() == b"unexplained"


def test_restart_loader_and_canonical_utf8_final_lf_output(tmp_path):
    root, store = _paths(tmp_path)
    written = _write_initial(root, store)
    loaded = subject.load_e4_thesis_history_store_v1(
        authorized_store_root=Path(str(root)),
        store_path=Path(str(store)),
    )
    assert loaded == written
    encoded = store.read_bytes()
    assert encoded.endswith(b"\n")
    assert b"\r" not in encoded
    assert encoded.decode("utf-8") == (
        json.dumps(
            written.to_mapping(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    assert not Path(str(store) + ".tmp").exists()
