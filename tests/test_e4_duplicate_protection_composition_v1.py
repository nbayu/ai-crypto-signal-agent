import ast
from concurrent.futures import ThreadPoolExecutor
import dataclasses
import hashlib
import inspect
import json
import multiprocessing
from pathlib import Path

import pytest

import engine.e4_duplicate_protection_composition_v1 as subject
from engine.e3_actionable_admission_v1 import (
    E3ActionableAdmissionResultV1,
    build_e3_actionable_admission,
)
from engine.e3_executable_price_snapshot_v1 import (
    build_e3_executable_price_snapshot,
)
from engine.e3_golden_zone_geometry_v1 import (
    build_e3_golden_zone_geometry,
)
from engine.e3_mode_trigger_evidence_v1 import (
    build_e3_mode_trigger_evidence,
)
from engine.e3_price_zone_admission_v1 import (
    build_e3_price_zone_admission,
)
from engine.e3_setup_lifecycle_v1 import build_e3_setup_lifecycle
from engine.e3_structural_targets_v1 import build_e3_structural_targets
from engine.e4_publication_idempotency_guard_v1 import (
    CLAIM_SUPPRESSED_BY_RESET_POLICY,
    CLAIM_SUPPRESSED_EXISTING_THESIS,
    CLAIM_WON_INITIAL_THESIS,
    CLAIM_WON_RESET_THESIS,
    record_e4_publication_success_v1,
)
from engine.e4_thesis_fingerprint_v1 import (
    E4ThesisFingerprintV1,
    THESIS_EXCLUDED_FIELDS,
    build_e4_thesis_fingerprint,
)
from engine.e4_thesis_history_store_v1 import (
    compare_and_write_e4_thesis_history_store_v1,
    load_e4_thesis_history_store_v1,
)
from engine.e4_thesis_history_v1 import (
    append_e4_thesis_history_event_v1,
    create_e4_thesis_history_v1,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_profile_v1 import get_mode_profile
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)


MODES_AND_SIDES = (
    ("SWING", "LONG"),
    ("SWING", "SHORT"),
    ("INTRADAY", "LONG"),
    ("INTRADAY", "SHORT"),
    ("SCALP", "LONG"),
    ("SCALP", "SHORT"),
)

DECISION_CODES = (
    "ALLOW_INITIAL_THESIS_PUBLICATION_INTENT",
    "ALLOW_RESET_THESIS_PUBLICATION_INTENT",
    "SUPPRESS_EXISTING_THESIS",
    "SUPPRESS_BY_RESET_POLICY",
    "HOLD_ACTIONABLE_ADMISSION_REQUIRED",
)


def _authority(*, valid_until="2026-08-01T00:00:00Z"):
    return ProductionCandidateAuthorityV1(
        source_commit="a" * 40,
        source_evaluation_id="evaluation:e4-duplicate-protection",
        production_evidence_ref={
            "manifest_hash": "b" * 64,
            "manifest_path": "sealed/manifest.json",
        },
        component_versions={"adapter": "v1", "master": "v4"},
        tp2=12528,
        valid_until=valid_until,
        strategy_version="master-engine-v4",
        source_payload_hash="c" * 64,
    )


def _real_chain(
    mode="SWING",
    side="LONG",
    *,
    structure_generation_id="structure:g1",
    trigger_candle_close_at="2026-07-30T00:15:00Z",
    anchor_variant=0,
    price_case="PASS",
    trigger_satisfied=True,
    valid_until="2026-08-01T00:00:00Z",
):
    if side == "LONG":
        anchor_low_at = (
            "2026-07-29T23:00:00Z"
            if anchor_variant
            else "2026-07-30T00:00:00Z"
        )
        anchor_high_at = "2026-07-30T01:00:00Z"
    else:
        anchor_high_at = (
            "2026-07-29T23:00:00Z"
            if anchor_variant
            else "2026-07-30T00:00:00Z"
        )
        anchor_low_at = "2026-07-30T01:00:00Z"
    geometry = build_e3_golden_zone_geometry(
        mode=mode,
        mode_lineage_sha256=build_mode_audit_lineage(mode).lineage_sha256,
        canonical_symbol="BTC/USDT:USDT",
        side=side,
        structure_generation_id=structure_generation_id,
        anchor_low_at=anchor_low_at,
        anchor_low_tick=9000,
        anchor_high_at=anchor_high_at,
        anchor_high_tick=12000,
        tick_size="1",
    )
    targets = build_e3_structural_targets(
        geometry=geometry,
        ordered_destinations=(
            (
                "STRUCTURE",
                "destination:tp1",
                12146 if side == "LONG" else 8854,
                geometry.structure_timeframe,
                geometry.structure_generation_id,
            ),
            (
                "LIQUIDITY",
                "destination:tp2",
                12528 if side == "LONG" else 8472,
                geometry.structure_timeframe,
                geometry.structure_generation_id,
            ),
        ),
    )
    inside_tick = geometry.golden_zone_low_tick + (
        geometry.golden_zone_high_tick - geometry.golden_zone_low_tick
    ) // 2
    executable_tick = inside_tick
    if price_case == "OUTSIDE":
        executable_tick = (
            geometry.golden_zone_high_tick + 1
            if side == "LONG"
            else geometry.golden_zone_low_tick - 1
        )
    best_bid_tick = (
        executable_tick - 1 if side == "LONG" else executable_tick
    )
    best_ask_tick = (
        executable_tick if side == "LONG" else executable_tick + 1
    )
    exchange_timestamp = (
        "2026-07-30T00:14:44Z"
        if price_case == "STALE"
        else trigger_candle_close_at
    )
    snapshot = build_e3_executable_price_snapshot(
        geometry=geometry,
        venue="BINANCE_USDM",
        quote_generation_id=(
            f"quote:composition-{mode.lower()}-{side.lower()}-"
            f"{structure_generation_id}-{trigger_candle_close_at}"
        ),
        exchange_timestamp=exchange_timestamp,
        best_bid_tick=best_bid_tick,
        best_ask_tick=best_ask_tick,
        last_price_tick=executable_tick,
        mark_price_tick=executable_tick,
        modeled_adverse_slippage_bps=0,
        tick_size=geometry.tick_size,
    )
    admission = build_e3_price_zone_admission(
        geometry=geometry,
        snapshot=snapshot,
        evaluation_timestamp=trigger_candle_close_at,
    )
    profile = get_mode_profile(mode)
    trigger = build_e3_mode_trigger_evidence(
        geometry=geometry,
        mode=geometry.mode,
        mode_lineage_sha256=geometry.mode_lineage_sha256,
        canonical_symbol=geometry.canonical_symbol,
        side=geometry.side,
        structure_timeframe=geometry.structure_timeframe,
        structure_generation_id=geometry.structure_generation_id,
        trigger_timeframe=profile.trigger_timeframe,
        trigger_rule=profile.trigger_rule,
        trigger_candle_close_at=trigger_candle_close_at,
        trigger_candle_closed=True,
        trigger_rule_satisfied=trigger_satisfied,
        evaluation_timestamp=trigger_candle_close_at,
    )
    if price_case == "STALE":
        requested_state = "INVALIDATED"
    elif price_case == "OUTSIDE":
        requested_state = "DISCOVERED"
    elif not trigger_satisfied:
        requested_state = "ARMED"
    else:
        requested_state = "ACTIONABLE"
    lifecycle = build_e3_setup_lifecycle(
        previous_state="DISCOVERED",
        requested_state=requested_state,
        geometry=geometry,
        structural_targets=targets,
        price_zone_admission=admission,
        mode_trigger_evidence=trigger,
        structure_valid=True,
    )
    actionable = build_e3_actionable_admission(
        geometry=geometry,
        structural_targets=targets,
        executable_price_snapshot=snapshot,
        price_zone_admission=admission,
        mode_trigger_evidence=trigger,
        setup_lifecycle=lifecycle,
    )
    return {
        "geometry": geometry,
        "targets": targets,
        "snapshot": snapshot,
        "admission": admission,
        "trigger": trigger,
        "lifecycle": lifecycle,
        "actionable": actionable,
        "authority": _authority(valid_until=valid_until),
    }


def _fingerprint(chain):
    return build_e4_thesis_fingerprint(
        geometry=chain["geometry"],
        structural_targets=chain["targets"],
        executable_price_snapshot=chain["snapshot"],
        mode_trigger_evidence=chain["trigger"],
        production_candidate_authority=chain["authority"],
    )


def _paths(tmp_path, name="composition"):
    root = tmp_path / name
    root.mkdir()
    return root, root / "BTC-USDT.e4-thesis-history.json"


def _compose(root, store, chain, *, price_exited_zone=False):
    return subject.compose_e4_duplicate_protection_v1(
        actionable_admission=chain["actionable"],
        candidate_authority=chain["authority"],
        authorized_store_root=root,
        store_path=store,
        price_exited_zone=price_exited_zone,
    )


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


def _history_for_state(fingerprint, state, *, zone_exited=False):
    initial_state = "ARMED" if state == "ARMED" else "ACTIONABLE"
    history = create_e4_thesis_history_v1(
        fingerprint=fingerprint,
        initial_state=initial_state,
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


def _persist_state(root, store, chain, state, *, zone_exited=False):
    history = _history_for_state(
        _fingerprint(chain),
        state,
        zone_exited=zone_exited,
    )
    return _persist_history(root, store, history)


def _replace_fingerprint(fingerprint, **changes):
    identity = fingerprint.to_identity_mapping()
    identity.update(changes)
    canonical = json.dumps(
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
        identity_sha256=hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest(),
    )


def _process_compose(root_text, store_text, queue):
    try:
        result = _compose(
            Path(root_text),
            Path(store_text),
            _real_chain(),
        )
        queue.put((result.publication_intent_allowed, result.decision_code))
    except Exception as error:
        queue.put((False, type(error).__name__))


def _dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def test_exact_version_decision_codes_and_public_exports():
    assert subject.E4_DUPLICATE_PROTECTION_COMPOSITION_VERSION == (
        "e4-duplicate-protection-composition-v1"
    )
    assert subject.DUPLICATE_PROTECTION_DECISION_CODES == DECISION_CODES
    assert tuple(getattr(subject, code) for code in DECISION_CODES) == (
        *DECISION_CODES,
    )
    assert len(DECISION_CODES) == 5


def test_result_is_frozen_slotted_and_has_exact_fields(tmp_path):
    root, store = _paths(tmp_path)
    result = _compose(root, store, _real_chain())
    assert subject.E4DuplicateProtectionCompositionResultV1.__dataclass_params__.frozen
    assert not hasattr(result, "__dict__")
    assert tuple(field.name for field in dataclasses.fields(result)) == (
        "composition_version",
        "actionable_admission_sha256",
        "actionable_admitted",
        "fingerprint",
        "publication_guard_result",
        "publication_intent_allowed",
        "decision_code",
        "composition_sha256",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.decision_code = subject.SUPPRESS_EXISTING_THESIS


def test_public_function_signature_is_exact_and_excludes_envelope_authority():
    signature = inspect.signature(subject.compose_e4_duplicate_protection_v1)
    assert tuple(signature.parameters) == (
        "actionable_admission",
        "candidate_authority",
        "authorized_store_root",
        "store_path",
        "price_exited_zone",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert set(signature.parameters).isdisjoint(THESIS_EXCLUDED_FIELDS)
    assert set(signature.parameters).isdisjoint(
        {"owner_decision", "telegram", "ledger", "slot", "pair_lock"}
    )


def test_composition_mapping_canonical_json_and_sha256_are_deterministic(
    tmp_path,
):
    chain = _real_chain()
    root_one, store_one = _paths(tmp_path, "first")
    root_two, store_two = _paths(tmp_path, "second")
    first = _compose(root_one, store_one, chain)
    second = _compose(root_two, store_two, chain)
    mapping = first.to_mapping()
    supplied_hash = mapping.pop("composition_sha256")
    canonical = json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    assert first.canonical_composition_json() == canonical
    assert supplied_hash == hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    assert first.to_mapping() == second.to_mapping()
    assert json.dumps(
        dict(reversed(tuple(mapping.items()))),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) == canonical


def test_incorrect_composition_sha256_fails_closed(tmp_path):
    root, store = _paths(tmp_path)
    result = _compose(root, store, _real_chain())
    with pytest.raises(
        ValueError,
        match="^invalid E4 duplicate protection composition$",
    ):
        dataclasses.replace(result, composition_sha256="0" * 64)


@pytest.mark.parametrize(
    "changes",
    (
        {"publication_intent_allowed": False},
        {"decision_code": "SUPPRESS_EXISTING_THESIS"},
        {"actionable_admitted": False},
        {"fingerprint": None},
    ),
)
def test_result_guard_decision_and_boolean_contradictions_fail_closed(
    tmp_path,
    changes,
):
    root, store = _paths(tmp_path)
    result = _compose(root, store, _real_chain())
    with pytest.raises(ValueError):
        dataclasses.replace(result, **changes)


@pytest.mark.parametrize("mode,side", MODES_AND_SIDES)
def test_six_real_mode_side_chains_win_and_retain_exact_identities(
    tmp_path,
    mode,
    side,
):
    chain = _real_chain(mode, side)
    root, store = _paths(tmp_path)
    result = _compose(root, store, chain)
    assert result.publication_intent_allowed is True
    assert result.decision_code == subject.ALLOW_INITIAL_THESIS_PUBLICATION_INTENT
    assert result.actionable_admitted is True
    assert result.fingerprint is not None
    assert result.publication_guard_result is not None
    assert result.publication_guard_result.result_code == CLAIM_WON_INITIAL_THESIS
    assert result.actionable_admission_sha256 == (
        chain["actionable"].actionable_admission_sha256
    )
    assert result.fingerprint.mode == mode
    assert result.fingerprint.side == side
    assert result.fingerprint.trigger_type == chain["trigger"].trigger_rule
    assert result.fingerprint.trigger_timeframe == (
        chain["trigger"].trigger_timeframe
    )
    assert result.fingerprint.canonical_pair == "BTC/USDT"
    assert result.fingerprint.identity_sha256 == (
        result.publication_guard_result.candidate_identity_sha256
    )


def test_fingerprint_builder_receives_exact_retained_e3_objects(
    tmp_path,
    monkeypatch,
):
    chain = _real_chain()
    captured = []
    committed_builder = subject.build_e4_thesis_fingerprint

    def recording_builder(**values):
        captured.append(values)
        return committed_builder(**values)

    monkeypatch.setattr(subject, "build_e4_thesis_fingerprint", recording_builder)
    root, store = _paths(tmp_path)
    result = _compose(root, store, chain)
    assert len(captured) == 1
    assert captured[0]["geometry"] is chain["actionable"].geometry
    assert captured[0]["structural_targets"] is (
        chain["actionable"].structural_targets
    )
    assert captured[0]["executable_price_snapshot"] is (
        chain["actionable"].executable_price_snapshot
    )
    assert captured[0]["mode_trigger_evidence"] is (
        chain["actionable"].mode_trigger_evidence
    )
    assert captured[0]["production_candidate_authority"] is chain["authority"]
    assert result.fingerprint.trigger_type == chain["trigger"].trigger_rule


def test_fingerprint_failure_prevents_guard_access(tmp_path, monkeypatch):
    chain = _real_chain()
    calls = []

    def fail_fingerprint(**_values):
        raise ValueError("sealed dependency mismatch")

    def forbidden_claim(**values):
        calls.append(values)
        raise AssertionError("guard must not be reached")

    monkeypatch.setattr(subject, "build_e4_thesis_fingerprint", fail_fingerprint)
    monkeypatch.setattr(subject, "claim_e4_publication_intent_v1", forbidden_claim)
    root = tmp_path / "must-not-exist"
    store = root / "BTC-USDT.e4-thesis-history.json"
    with pytest.raises(ValueError):
        _compose(root, store, chain)
    assert calls == []
    assert not root.exists()


def test_malformed_guard_result_fails_closed(tmp_path, monkeypatch):
    chain = _real_chain()
    root, store = _paths(tmp_path)
    monkeypatch.setattr(
        subject,
        "claim_e4_publication_intent_v1",
        lambda **_values: object(),
    )
    with pytest.raises(
        ValueError,
        match="^invalid E4 duplicate protection composition$",
    ):
        _compose(root, store, chain)
    assert not store.exists()


@pytest.mark.parametrize(
    "chain_changes",
    (
        {"price_case": "OUTSIDE"},
        {"price_case": "STALE"},
        {"trigger_satisfied": False},
    ),
)
def test_non_actionable_evidence_has_zero_store_access(tmp_path, chain_changes):
    chain = _real_chain(**chain_changes)
    assert chain["actionable"].actionable_admitted is False
    root = tmp_path / "must-not-exist"
    store = root / "BTC-USDT.e4-thesis-history.json"
    result = _compose(root, store, chain)
    assert result.decision_code == subject.HOLD_ACTIONABLE_ADMISSION_REQUIRED
    assert result.publication_intent_allowed is False
    assert result.fingerprint is None
    assert result.publication_guard_result is None
    assert not root.exists()
    assert not store.exists()
    assert not Path(str(store) + ".lock").exists()
    assert not Path(str(store) + ".tmp").exists()


def test_forged_actionable_subclass_fails_before_store_access(tmp_path):
    chain = _real_chain()

    class ForgedActionable(E3ActionableAdmissionResultV1):
        pass

    forged = ForgedActionable(
        **{
            field.name: getattr(chain["actionable"], field.name)
            for field in dataclasses.fields(E3ActionableAdmissionResultV1)
        }
    )
    root = tmp_path / "must-not-exist"
    store = root / "BTC-USDT.e4-thesis-history.json"
    with pytest.raises(ValueError):
        subject.compose_e4_duplicate_protection_v1(
            actionable_admission=forged,
            candidate_authority=chain["authority"],
            authorized_store_root=root,
            store_path=store,
            price_exited_zone=False,
        )
    assert not root.exists()


def test_same_thesis_replay_is_suppressed_without_write(tmp_path):
    root, store = _paths(tmp_path)
    chain = _real_chain()
    first = _compose(root, store, chain)
    document = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    second = _compose(root, store, chain)
    after = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert first.publication_intent_allowed is True
    assert second.decision_code == subject.SUPPRESS_EXISTING_THESIS
    assert second.publication_guard_result.result_code == (
        CLAIM_SUPPRESSED_EXISTING_THESIS
    )
    assert after == document


def test_same_thesis_rebuilt_as_new_python_objects_is_suppressed(tmp_path):
    root, store = _paths(tmp_path)
    first_chain = _real_chain()
    second_chain = _real_chain()
    assert first_chain["geometry"] is not second_chain["geometry"]
    first = _compose(root, store, first_chain)
    second = _compose(root, store, second_chain)
    assert first.fingerprint == second.fingerprint
    assert second.decision_code == subject.SUPPRESS_EXISTING_THESIS


@pytest.mark.parametrize("excluded_field", THESIS_EXCLUDED_FIELDS)
def test_publication_envelope_changes_cannot_bypass_suppression(
    tmp_path,
    excluded_field,
):
    root, store = _paths(tmp_path)
    first_chain = _real_chain()
    second_chain = _real_chain(
        valid_until=(
            "2026-08-02T00:00:00Z"
            if excluded_field == "valid_until"
            else "2026-08-01T00:00:00Z"
        )
    )
    envelope = {
        "signal_id": "signal:changed",
        "delivery_id": "delivery:changed",
        "publication_timestamp": "2026-07-31T01:00:00Z",
        "telegram_message_id": "telegram:changed",
        "current_price": 11300,
        "score": 99,
        "llm_result": "changed",
        "valid_until": "2026-08-02T00:00:00Z",
        "ledger_revision": 42,
    }
    assert envelope[excluded_field] is not None
    first = _compose(root, store, first_chain)
    second = _compose(root, store, second_chain)
    assert first.fingerprint.identity_sha256 == second.fingerprint.identity_sha256
    assert second.decision_code == subject.SUPPRESS_EXISTING_THESIS


def test_time_only_reset_is_suppressed_by_committed_reset_policy(
    tmp_path,
    monkeypatch,
):
    root, store = _paths(tmp_path)
    chain = _real_chain()
    prior = _fingerprint(chain)
    _persist_history(
        root,
        store,
        _history_for_state(prior, "SKIPPED", zone_exited=True),
    )
    candidate = _replace_fingerprint(
        prior,
        trigger_candle_close_at="2026-07-30T00:30:00Z",
    )
    monkeypatch.setattr(
        subject,
        "build_e4_thesis_fingerprint",
        lambda **_values: candidate,
    )
    result = _compose(root, store, chain, price_exited_zone=True)
    assert result.decision_code == subject.SUPPRESS_BY_RESET_POLICY
    assert result.publication_guard_result.result_code == (
        CLAIM_SUPPRESSED_BY_RESET_POLICY
    )
    assert result.publication_guard_result.reset_decision.decision_code == (
        "SUPPRESS_TIME_ONLY_RESET"
    )


@pytest.mark.parametrize(
    "state",
    ("ARMED", "ACTIONABLE", "PUBLISHED_PENDING_ENTRY", "ENTRY_ACTIVE"),
)
def test_nonterminal_state_repeats_are_suppressed(tmp_path, state):
    root, store = _paths(tmp_path)
    chain = _real_chain()
    _persist_state(root, store, chain, state)
    result = _compose(root, store, chain)
    assert result.decision_code == subject.SUPPRESS_EXISTING_THESIS
    assert result.publication_guard_result.claim_won is False


@pytest.mark.parametrize(
    "scenario,zone,candidate_changes,expected_decision,expected_reset",
    (
        (
            "without-zone-exit",
            False,
            {"trigger_candle_close_at": "2026-07-30T00:30:00Z"},
            "SUPPRESS_BY_RESET_POLICY",
            "SUPPRESS_ZONE_EXIT_REQUIRED",
        ),
        (
            "same-trigger",
            True,
            {},
            "SUPPRESS_EXISTING_THESIS",
            None,
        ),
        (
            "new-trigger",
            True,
            {"trigger_candle_close_at": "2026-07-30T00:30:00Z"},
            "ALLOW_RESET_THESIS_PUBLICATION_INTENT",
            "ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER",
        ),
    ),
)
def test_skipped_reset_matrix(
    tmp_path,
    scenario,
    zone,
    candidate_changes,
    expected_decision,
    expected_reset,
):
    root, store = _paths(tmp_path)
    prior = _real_chain()
    _persist_state(root, store, prior, "SKIPPED", zone_exited=zone)
    candidate = _real_chain(**candidate_changes)
    result = _compose(root, store, candidate, price_exited_zone=zone)
    assert scenario
    assert result.decision_code == expected_decision
    reset = result.publication_guard_result.reset_decision
    assert (reset.decision_code if reset is not None else None) == expected_reset
    if result.publication_intent_allowed:
        replay = _compose(root, store, candidate, price_exited_zone=False)
        assert replay.decision_code == subject.SUPPRESS_EXISTING_THESIS


def test_rejected_owner_new_trigger_reset_wins_exactly_once(tmp_path):
    root, store = _paths(tmp_path)
    _persist_state(
        root,
        store,
        _real_chain(),
        "REJECTED_BY_OWNER",
        zone_exited=True,
    )
    candidate = _real_chain(
        trigger_candle_close_at="2026-07-30T00:30:00Z"
    )
    winner = _compose(root, store, candidate, price_exited_zone=True)
    replay = _compose(root, store, candidate, price_exited_zone=False)
    assert winner.decision_code == subject.ALLOW_RESET_THESIS_PUBLICATION_INTENT
    assert winner.publication_guard_result.result_code == CLAIM_WON_RESET_THESIS
    assert winner.publication_guard_result.reset_decision.decision_code == (
        "ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER"
    )
    assert replay.decision_code == subject.SUPPRESS_EXISTING_THESIS


@pytest.mark.parametrize(
    "candidate_changes,allowed",
    (
        ({"trigger_candle_close_at": "2026-07-30T00:30:00Z"}, False),
        ({"structure_generation_id": "structure:g2"}, True),
    ),
)
def test_invalidated_structure_reset_matrix(
    tmp_path,
    candidate_changes,
    allowed,
):
    root, store = _paths(tmp_path)
    _persist_state(root, store, _real_chain(), "INVALIDATED")
    candidate = _real_chain(**candidate_changes)
    result = _compose(root, store, candidate)
    assert result.publication_intent_allowed is allowed
    assert result.decision_code == (
        subject.ALLOW_RESET_THESIS_PUBLICATION_INTENT
        if allowed
        else subject.SUPPRESS_BY_RESET_POLICY
    )
    if allowed:
        assert result.publication_guard_result.reset_decision.decision_code == (
            "ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS"
        )
        assert _compose(root, store, candidate).publication_intent_allowed is False


@pytest.mark.parametrize(
    "candidate_changes,allowed",
    (
        ({"trigger_candle_close_at": "2026-07-30T00:30:00Z"}, False),
        ({"anchor_variant": 1}, True),
    ),
)
def test_closed_anchor_reset_matrix(tmp_path, candidate_changes, allowed):
    root, store = _paths(tmp_path)
    _persist_state(root, store, _real_chain(), "CLOSED")
    candidate = _real_chain(**candidate_changes)
    result = _compose(root, store, candidate)
    assert result.publication_intent_allowed is allowed
    assert result.decision_code == (
        subject.ALLOW_RESET_THESIS_PUBLICATION_INTENT
        if allowed
        else subject.SUPPRESS_BY_RESET_POLICY
    )
    if allowed:
        assert result.publication_guard_result.reset_decision.decision_code == (
            "ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS"
        )
        assert _compose(root, store, candidate).publication_intent_allowed is False


def test_previously_seen_old_fingerprint_reuse_fails_closed(tmp_path):
    root, store = _paths(tmp_path)
    original = _real_chain()
    _persist_state(root, store, original, "INVALIDATED")
    successor = _real_chain(structure_generation_id="structure:g2")
    assert _compose(root, store, successor).publication_intent_allowed is True
    current = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    invalidated = _append(current.history, "INVALIDATED")
    compare_and_write_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
        expected_store_revision=current.store_revision,
        expected_document_sha256=current.document_sha256,
        history=invalidated,
    )
    with pytest.raises(ValueError):
        _compose(root, store, original)


def test_restart_loader_replay_preserves_history_and_adds_no_intent(tmp_path):
    root, store = _paths(tmp_path)
    winner = _compose(root, store, _real_chain())
    loaded = load_e4_thesis_history_store_v1(
        authorized_store_root=Path(str(root)),
        store_path=Path(str(store)),
    )
    replay = _compose(Path(str(root)), Path(str(store)), _real_chain())
    after = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert winner.publication_intent_allowed is True
    assert replay.publication_intent_allowed is False
    assert after == loaded
    assert after.history.fingerprint_history == (
        winner.fingerprint.identity_sha256,
    )


def test_restart_after_publication_success_adds_no_intent_or_success_event(
    tmp_path,
):
    root, store = _paths(tmp_path)
    winner = _compose(root, store, _real_chain())
    recorded = record_e4_publication_success_v1(
        authorized_store_root=root,
        store_path=store,
        candidate_identity_sha256=winner.fingerprint.identity_sha256,
    )
    before = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    replay = _compose(Path(str(root)), Path(str(store)), _real_chain())
    after = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert recorded.publication_success_recorded is True
    assert replay.decision_code == subject.SUPPRESS_EXISTING_THESIS
    assert after == before


def test_concurrent_identical_initial_compositions_have_one_winner(tmp_path):
    root, store = _paths(tmp_path)

    def invoke():
        return _compose(root, store, _real_chain())

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(executor.map(lambda _index: invoke(), range(8)))
    assert sum(result.publication_intent_allowed for result in results) == 1
    assert sum(
        result.decision_code == subject.SUPPRESS_EXISTING_THESIS
        for result in results
    ) == 7
    document = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert document.store_revision == 2


def test_concurrent_identical_reset_compositions_have_one_winner(tmp_path):
    root, store = _paths(tmp_path)
    _persist_state(
        root,
        store,
        _real_chain(),
        "SKIPPED",
        zone_exited=True,
    )

    def invoke():
        return _compose(
            root,
            store,
            _real_chain(
                trigger_candle_close_at="2026-07-30T00:30:00Z"
            ),
            price_exited_zone=True,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(executor.map(lambda _index: invoke(), range(8)))
    assert sum(result.publication_intent_allowed for result in results) == 1
    assert sum(
        result.publication_guard_result.result_code == (
            CLAIM_SUPPRESSED_EXISTING_THESIS
        )
        for result in results
    ) == 7


def test_suppressed_concurrent_callers_preserve_revision_and_hash(tmp_path):
    root, store = _paths(tmp_path)
    _compose(root, store, _real_chain())
    before = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(
            executor.map(
                lambda _index: _compose(root, store, _real_chain()),
                range(8),
            )
        )
    after = load_e4_thesis_history_store_v1(
        authorized_store_root=root,
        store_path=store,
    )
    assert all(not result.publication_intent_allowed for result in results)
    assert after.store_revision == before.store_revision
    assert after.document_sha256 == before.document_sha256


def test_separate_process_identical_compositions_have_one_winner(tmp_path):
    root, store = _paths(tmp_path)
    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    processes = tuple(
        context.Process(
            target=_process_compose,
            args=(str(root), str(store), queue),
        )
        for _index in range(4)
    )
    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
        assert process.exitcode == 0
    results = tuple(queue.get(timeout=5) for _process in processes)
    assert sum(allowed for allowed, _decision in results) == 1
    assert sum(
        decision == subject.SUPPRESS_EXISTING_THESIS
        for _allowed, decision in results
    ) == 3


def test_one_composition_invocation_calls_claim_guard_exactly_once(
    tmp_path,
    monkeypatch,
):
    committed_claim = subject.claim_e4_publication_intent_v1
    calls = []

    def recording_claim(**values):
        calls.append(values)
        return committed_claim(**values)

    monkeypatch.setattr(subject, "claim_e4_publication_intent_v1", recording_claim)
    root, store = _paths(tmp_path)
    result = _compose(root, store, _real_chain())
    assert result.publication_intent_allowed is True
    assert len(calls) == 1
    assert calls[0]["candidate_fingerprint"] is result.fingerprint


@pytest.mark.parametrize("bad_value", (1, 0, "false"))
def test_price_exited_zone_requires_exact_bool_before_store_access(
    tmp_path,
    bad_value,
):
    chain = _real_chain()
    root = tmp_path / "must-not-exist"
    store = root / "BTC-USDT.e4-thesis-history.json"
    with pytest.raises(ValueError):
        subject.compose_e4_duplicate_protection_v1(
            actionable_admission=chain["actionable"],
            candidate_authority=chain["authority"],
            authorized_store_root=root,
            store_path=store,
            price_exited_zone=bad_value,
        )
    assert not root.exists()


@pytest.mark.parametrize("which", ("root", "store"))
def test_store_authority_inputs_require_path_objects(tmp_path, which):
    chain = _real_chain()
    root = tmp_path / "must-not-exist"
    store = root / "BTC-USDT.e4-thesis-history.json"
    values = {"authorized_store_root": root, "store_path": store}
    values["authorized_store_root" if which == "root" else "store_path"] = (
        str(root) if which == "root" else str(store)
    )
    with pytest.raises(ValueError):
        subject.compose_e4_duplicate_protection_v1(
            actionable_admission=chain["actionable"],
            candidate_authority=chain["authority"],
            price_exited_zone=False,
            **values,
        )
    assert not root.exists()


def test_source_delegates_exactly_one_claim_and_never_records_success():
    source_path = Path(subject.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    compose = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "compose_e4_duplicate_protection_v1"
    )
    calls = tuple(
        _dotted_name(node.func)
        for node in ast.walk(compose)
        if isinstance(node, ast.Call)
    )
    assert calls.count("build_e4_thesis_fingerprint") == 1
    assert calls.count("claim_e4_publication_intent_v1") == 1
    assert "record_e4_publication_success_v1" not in calls
    assert not any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(compose))


@pytest.mark.parametrize(
    "forbidden_root",
    (
        "active_signal_ledger_v1",
        "telegram",
        "provider",
        "exchange",
        "order",
        "slot",
        "pair_lock",
        "subprocess",
        "socket",
        "requests",
        "os",
        "time",
    ),
)
def test_production_source_has_zero_external_effect_reachability(
    forbidden_root,
):
    source_path = Path(subject.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
            imported_roots.add(node.module)
        elif isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            if name is not None:
                calls.add(name)
    assert forbidden_root not in imported_roots
    assert all(name.split(".")[0] != forbidden_root for name in calls)
    assert not any(
        name in {
            "datetime.now",
            "datetime.utcnow",
            "date.today",
            "time.time",
            "random.random",
            "sleep",
        }
        for name in calls
    )
