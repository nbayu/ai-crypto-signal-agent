import ast
from concurrent.futures import ThreadPoolExecutor
import dataclasses
import hashlib
import json
import multiprocessing
from pathlib import Path

import pytest

import engine.e4_publication_idempotency_guard_v1 as subject
from engine.e4_thesis_fingerprint_v1 import (
    E4ThesisFingerprintV1,
    THESIS_EXCLUDED_FIELDS,
)
from engine.e4_thesis_history_store_v1 import (
    compare_and_write_e4_thesis_history_store_v1,
    load_e4_thesis_history_store_v1,
)
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
    root = tmp_path / "isolated-guard"
    root.mkdir(parents=True)
    return root, root / "BTC-USDT.e4-thesis-history.json"


def _append(
    history,
    state,
    *,
    publication_succeeded=None,
    price_exited_zone=None,
):
    if publication_succeeded is None:
        publication_succeeded = history.current_publication_succeeded
    if price_exited_zone is None:
        price_exited_zone = history.current_price_exited_zone
    return append_e4_thesis_history_event_v1(
        history=history,
        fingerprint=history.events[-1].fingerprint,
        state=state,
        publication_succeeded=publication_succeeded,
        price_exited_zone=price_exited_zone,
        reset_decision=None,
    )


def _history_for_state(state, *, zone_exited=False):
    history = create_e4_thesis_history_v1(
        fingerprint=_fingerprint(),
        initial_state="ACTIONABLE",
    )
    if state in ("SKIPPED", "REJECTED_BY_OWNER", "INVALIDATED"):
        history = _append(history, state)
    elif state == "PUBLISHED_PENDING_ENTRY":
        history = _append(history, state, publication_succeeded=False)
    elif state in ("ENTRY_ACTIVE", "CLOSED"):
        history = _append(
            history,
            "PUBLISHED_PENDING_ENTRY",
            publication_succeeded=True,
        )
        history = _append(history, "ENTRY_ACTIVE")
        if state == "CLOSED":
            history = _append(history, "CLOSED")
    if zone_exited:
        history = _append(history, state, price_exited_zone=True)
    return history


def _persist_history(root, store, history):
    initial = create_e4_thesis_history_v1(
        fingerprint=history.events[0].fingerprint,
        initial_state=history.events[0].state,
    )
    document = compare_and_write_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
        expected_store_revision=None,
        expected_document_sha256=None,
        history=initial,
    )
    if history.revision > 1:
        document = compare_and_write_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
            expected_store_revision=document.store_revision,
            expected_document_sha256=document.document_sha256,
            history=history,
        )
    return document


def _claim(root, store, fingerprint, price_exited_zone=False):
    return subject.claim_e4_publication_intent_v1(
        authorized_store_root=root,
        store_path=store,
        candidate_fingerprint=fingerprint,
        price_exited_zone=price_exited_zone,
    )


def _process_claim(root_text, store_text, fingerprint, queue):
    try:
        result = _claim(
            Path(root_text),
            Path(store_text),
            fingerprint,
            False,
        )
        queue.put((result.claim_won, result.result_code, None))
    except Exception as error:
        queue.put((False, None, type(error).__name__))


def _dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def test_exact_guard_version_codes_and_frozen_slotted_result(tmp_path):
    root, store = _paths(tmp_path)
    result = _claim(root, store, _fingerprint())
    assert subject.E4_PUBLICATION_IDEMPOTENCY_GUARD_VERSION == (
        "e4-publication-idempotency-guard-v1"
    )
    assert subject.PUBLICATION_IDEMPOTENCY_RESULT_CODES == (
        "CLAIM_WON_INITIAL_THESIS",
        "CLAIM_WON_RESET_THESIS",
        "CLAIM_SUPPRESSED_EXISTING_THESIS",
        "CLAIM_SUPPRESSED_BY_RESET_POLICY",
        "PUBLICATION_SUCCESS_RECORDED",
        "PUBLICATION_SUCCESS_ALREADY_RECORDED",
    )
    assert subject.E4PublicationIdempotencyResultV1.__dataclass_params__.frozen
    assert not hasattr(result, "__dict__")
    assert tuple(field.name for field in dataclasses.fields(result)) == (
        "guard_version",
        "canonical_pair",
        "candidate_identity_sha256",
        "claim_won",
        "publication_success_recorded",
        "result_code",
        "reset_decision",
        "store_revision_before",
        "store_revision_after",
        "document_sha256_before",
        "document_sha256_after",
        "result_sha256",
    )


def test_result_canonical_mapping_and_sha256_are_deterministic(tmp_path):
    root, store = _paths(tmp_path)
    result = _claim(root, store, _fingerprint())
    mapping = result.to_mapping()
    supplied_hash = mapping.pop("result_sha256")
    canonical = json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert result.canonical_result_json() == canonical
    assert supplied_hash == hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_initial_claim_wins_and_writes_actionable_then_pending(tmp_path):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    result = _claim(root, store, candidate)
    document = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert result.claim_won is True
    assert result.result_code == subject.CLAIM_WON_INITIAL_THESIS
    assert result.store_revision_before is None
    assert result.store_revision_after == 2
    assert document is not None
    assert tuple(event.state for event in document.history.events) == (
        "ACTIONABLE",
        "PUBLISHED_PENDING_ENTRY",
    )
    assert document.history.current_publication_succeeded is False


def test_same_candidate_replay_is_suppressed_without_write(tmp_path):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    _claim(root, store, candidate)
    before = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    result = _claim(root, store, candidate)
    after = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert before is not None and after is not None
    assert result.claim_won is False
    assert result.result_code == subject.CLAIM_SUPPRESSED_EXISTING_THESIS
    assert result.store_revision_before == result.store_revision_after
    assert result.document_sha256_before == result.document_sha256_after
    assert after == before


@pytest.mark.parametrize("excluded_field", THESIS_EXCLUDED_FIELDS)
def test_publication_envelope_changes_do_not_change_claim_identity(
    tmp_path,
    excluded_field,
):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    first_envelope = {excluded_field: "one"}
    second_envelope = {excluded_field: "two"}
    first = _claim(root, store, candidate)
    second = _claim(root, store, candidate)
    assert first_envelope != second_envelope
    assert first.claim_won is True
    assert second.claim_won is False
    assert second.result_code == subject.CLAIM_SUPPRESSED_EXISTING_THESIS


def test_publication_success_records_once_and_replay_is_idempotent(tmp_path):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    _claim(root, store, candidate)
    first = subject.record_e4_publication_success_v1(
        authorized_store_root=root,
        store_path=store,
        candidate_identity_sha256=candidate.identity_sha256,
    )
    after_first = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    second = subject.record_e4_publication_success_v1(
        authorized_store_root=root,
        store_path=store,
        candidate_identity_sha256=candidate.identity_sha256,
    )
    after_second = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert first.result_code == subject.PUBLICATION_SUCCESS_RECORDED
    assert first.store_revision_after == first.store_revision_before + 1
    assert second.result_code == subject.PUBLICATION_SUCCESS_ALREADY_RECORDED
    assert second.store_revision_before == second.store_revision_after
    assert after_first == after_second
    assert after_second is not None
    assert after_second.history.current_publication_succeeded is True


def test_publication_success_wrong_identity_and_wrong_state_fail_closed(tmp_path):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    _claim(root, store, candidate)
    with pytest.raises(
        ValueError,
        match="^invalid E4 publication idempotency guard$",
    ):
        subject.record_e4_publication_success_v1(
            authorized_store_root=root,
            store_path=store,
            candidate_identity_sha256="0" * 64,
        )
    other_root, other_store = _paths(tmp_path / "other")
    _persist_history(
        other_root,
        other_store,
        _history_for_state("ACTIONABLE"),
    )
    with pytest.raises(
        ValueError,
        match="^invalid E4 publication idempotency guard$",
    ):
        subject.record_e4_publication_success_v1(
            authorized_store_root=other_root,
            store_path=other_store,
            candidate_identity_sha256=candidate.identity_sha256,
        )


@pytest.mark.parametrize(
    ("state", "zone", "candidate_changes", "allowed"),
    (
        (
            "SKIPPED",
            False,
            {"trigger_generation_id": "trg-" + "2" * 64},
            False,
        ),
        ("SKIPPED", True, {"tp1_tick": 12147}, False),
        (
            "SKIPPED",
            True,
            {
                "trigger_generation_id": "trg-" + "2" * 64,
                "trigger_candle_close_at": "2026-07-30T00:30:00Z",
            },
            True,
        ),
        (
            "REJECTED_BY_OWNER",
            True,
            {"trigger_generation_id": "trg-" + "2" * 64},
            True,
        ),
        (
            "INVALIDATED",
            False,
            {"trigger_generation_id": "trg-" + "2" * 64},
            False,
        ),
        (
            "INVALIDATED",
            False,
            {"structure_generation_id": "structure:g2"},
            True,
        ),
        ("CLOSED", False, {"anchor_low_tick": 9001}, True),
    ),
)
def test_reset_policy_claims(tmp_path, state, zone, candidate_changes, allowed):
    root, store = _paths(tmp_path)
    history = _history_for_state(state, zone_exited=zone)
    before = _persist_history(root, store, history)
    candidate = _fingerprint(**candidate_changes)
    result = _claim(root, store, candidate, zone)
    after = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert after is not None
    if allowed:
        assert result.claim_won is True
        assert result.result_code == subject.CLAIM_WON_RESET_THESIS
        assert result.reset_decision is not None
        assert result.reset_decision.publication_allowed is True
        assert tuple(event.state for event in after.history.events[-2:]) == (
            "ACTIONABLE",
            "PUBLISHED_PENDING_ENTRY",
        )
        assert after.history.events[-2].reset_decision == result.reset_decision
        assert after.store_revision == before.store_revision + 2
    else:
        assert result.claim_won is False
        assert result.result_code == subject.CLAIM_SUPPRESSED_BY_RESET_POLICY
        assert result.reset_decision is not None
        assert result.reset_decision.publication_allowed is False
        assert after == before


def test_previously_seen_fingerprint_reuse_fails_closed(tmp_path):
    root, store = _paths(tmp_path)
    original = _fingerprint()
    history = create_e4_thesis_history_v1(
        fingerprint=original,
        initial_state="ACTIONABLE",
    )
    history = _append(history, "INVALIDATED")
    _persist_history(root, store, history)
    successor = _fingerprint(structure_generation_id="structure:g2")
    _claim(root, store, successor, False)
    document = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert document is not None
    invalidated = _append(document.history, "INVALIDATED")
    document = compare_and_write_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
        expected_store_revision=document.store_revision,
        expected_document_sha256=document.document_sha256,
        history=invalidated,
    )
    with pytest.raises(
        ValueError,
        match="^invalid E4 publication idempotency guard$",
    ):
        _claim(root, store, original, False)
    assert load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    ) == document


def test_caller_and_history_zone_exit_disagreement_fails_closed(tmp_path):
    root, store = _paths(tmp_path)
    history = _history_for_state("SKIPPED", zone_exited=True)
    before = _persist_history(root, store, history)
    candidate = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    with pytest.raises(
        ValueError,
        match="^invalid E4 publication idempotency guard$",
    ):
        _claim(root, store, candidate, False)
    assert load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    ) == before


def test_concurrent_identical_initial_claims_have_one_winner(tmp_path):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(
            executor.map(
                lambda _: _claim(root, store, candidate, False),
                range(8),
            )
        )
    assert sum(result.claim_won for result in results) == 1
    assert sum(
        result.result_code == subject.CLAIM_SUPPRESSED_EXISTING_THESIS
        for result in results
    ) == 7
    document = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert document is not None
    assert document.store_revision == 2


def test_concurrent_identical_reset_claims_have_one_winner(tmp_path):
    root, store = _paths(tmp_path)
    history = _history_for_state("SKIPPED", zone_exited=True)
    before = _persist_history(root, store, history)
    candidate = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(
            executor.map(
                lambda _: _claim(root, store, candidate, True),
                range(8),
            )
        )
    assert sum(result.claim_won for result in results) == 1
    assert sum(
        result.result_code == subject.CLAIM_SUPPRESSED_EXISTING_THESIS
        for result in results
    ) == 7
    document = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert document is not None
    assert document.store_revision == before.store_revision + 2


def test_separate_process_initial_claim_has_exactly_one_winner(tmp_path):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    processes = [
        context.Process(
            target=_process_claim,
            args=(str(root), str(store), candidate, queue),
        )
        for _ in range(4)
    ]
    for process in processes:
        process.start()
    results = [queue.get() for _ in processes]
    for process in processes:
        process.join()
    assert all(process.exitcode == 0 for process in processes)
    assert all(error is None for _, _, error in results)
    assert sum(won for won, _, _ in results) == 1
    document = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert document is not None
    assert document.store_revision == 2


def test_restart_replay_before_and_after_success_adds_no_events(tmp_path):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    _claim(root, store, candidate)
    reloaded_before = load_e4_thesis_history_store_v1(
        authorized_store_root=Path(str(root)),
        store_path=Path(str(store)),
    )
    replay = _claim(Path(str(root)), Path(str(store)), candidate)
    assert replay.claim_won is False
    assert load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    ) == reloaded_before
    subject.record_e4_publication_success_v1(
        authorized_store_root=root,
        store_path=store,
        candidate_identity_sha256=candidate.identity_sha256,
    )
    after_success = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    replay_after = _claim(root, store, candidate)
    success_after = subject.record_e4_publication_success_v1(
        authorized_store_root=root,
        store_path=store,
        candidate_identity_sha256=candidate.identity_sha256,
    )
    assert replay_after.claim_won is False
    assert success_after.result_code == (
        subject.PUBLICATION_SUCCESS_ALREADY_RECORDED
    )
    assert load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    ) == after_success


def test_corrupt_store_blocks_claim_without_replacement(tmp_path):
    root, store = _paths(tmp_path)
    corrupt = b"{corrupt}\n"
    store.write_bytes(corrupt)
    with pytest.raises(
        ValueError,
        match="^invalid E4 publication idempotency guard$",
    ):
        _claim(root, store, _fingerprint())
    assert store.read_bytes() == corrupt


def test_stale_compare_write_cannot_overwrite_publication_success(tmp_path):
    root, store = _paths(tmp_path)
    candidate = _fingerprint()
    _claim(root, store, candidate)
    stale = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert stale is not None
    stale_candidate = _append(
        stale.history,
        "PUBLISHED_PENDING_ENTRY",
        publication_succeeded=True,
    )
    subject.record_e4_publication_success_v1(
        authorized_store_root=root,
        store_path=store,
        candidate_identity_sha256=candidate.identity_sha256,
    )
    winner = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    with pytest.raises(ValueError, match="^invalid E4 thesis history store$"):
        compare_and_write_e4_thesis_history_store_v1(
            authorized_store_root=root,
            store_path=store,
            expected_store_revision=stale.store_revision,
            expected_document_sha256=stale.document_sha256,
            history=stale_candidate,
        )
    assert load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    ) == winner


def test_production_sources_have_no_retry_clock_environment_or_external_authority():
    source_paths = (
        Path(__file__).parents[1] / "engine/e4_thesis_history_store_v1.py",
        Path(__file__).parents[1]
        / "engine/e4_publication_idempotency_guard_v1.py",
    )
    forbidden_import_roots = {
        "aiohttp",
        "ccxt",
        "datetime",
        "httpx",
        "random",
        "requests",
        "secrets",
        "socket",
        "subprocess",
        "telegram",
        "time",
        "uuid",
    }
    forbidden_project_modules = {
        "engine.active_signal_ledger_v1",
        "engine.telegram",
        "engine.provider",
        "engine.exchange",
        "engine.order",
        "engine.slot",
        "engine.pair_lock",
        "engine.service",
        "engine.production",
    }
    for source_path in source_paths:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported = set()
        project_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
                if node.module.startswith("engine."):
                    project_modules.add(node.module)
        assert imported.isdisjoint(forbidden_import_roots)
        assert project_modules.isdisjoint(forbidden_project_modules)
        calls = {
            name
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            if (name := _dotted_name(node.func)) is not None
        }
        assert calls.isdisjoint(
            {
                "time.sleep",
                "time.time",
                "datetime.now",
                "datetime.utcnow",
                "date.today",
                "os.getenv",
                "os.environ.get",
                "random.random",
                "uuid.uuid4",
            }
        )
        assert not any(
            call.endswith(
                (
                    ".send",
                    ".publish",
                    ".create_order",
                    ".place_order",
                    ".consume_slot",
                    ".acquire_pair_lock",
                    ".restart",
                )
            )
            for call in calls
        )
        assert all(
            not isinstance(node, (ast.While, ast.AsyncFunctionDef, ast.Await))
            for node in ast.walk(tree)
        )
