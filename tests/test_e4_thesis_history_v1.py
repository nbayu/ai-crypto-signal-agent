import ast
import copy
import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

import engine.e4_thesis_history_v1 as subject
from engine.e4_lifecycle_reset_adjudicator_v1 import (
    E4LifecycleResetDecisionV1,
    PREVIOUS_THESIS_STATES,
    adjudicate_e4_lifecycle_reset_v1,
)
from engine.e4_thesis_fingerprint_v1 import (
    E4ThesisFingerprintV1,
    THESIS_EXCLUDED_FIELDS,
)


TRANSITIONS = (
    ("ARMED", "ACTIONABLE"),
    ("ARMED", "INVALIDATED"),
    ("ACTIONABLE", "PUBLISHED_PENDING_ENTRY"),
    ("ACTIONABLE", "SKIPPED"),
    ("ACTIONABLE", "REJECTED_BY_OWNER"),
    ("ACTIONABLE", "INVALIDATED"),
    ("PUBLISHED_PENDING_ENTRY", "ENTRY_ACTIVE"),
    ("PUBLISHED_PENDING_ENTRY", "SKIPPED"),
    ("PUBLISHED_PENDING_ENTRY", "REJECTED_BY_OWNER"),
    ("PUBLISHED_PENDING_ENTRY", "INVALIDATED"),
    ("ENTRY_ACTIVE", "CLOSED"),
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
        identity_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _append(
    history,
    state,
    *,
    fingerprint=None,
    publication_succeeded=None,
    price_exited_zone=None,
    reset_decision=None,
):
    if fingerprint is None:
        fingerprint = history.events[-1].fingerprint
    if publication_succeeded is None:
        publication_succeeded = history.current_publication_succeeded
    if price_exited_zone is None:
        price_exited_zone = history.current_price_exited_zone
    return subject.append_e4_thesis_history_event_v1(
        history=history,
        fingerprint=fingerprint,
        state=state,
        publication_succeeded=publication_succeeded,
        price_exited_zone=price_exited_zone,
        reset_decision=reset_decision,
    )


def _history_for_state(state):
    fingerprint = _fingerprint()
    if state == "ARMED":
        return subject.create_e4_thesis_history_v1(
            fingerprint=fingerprint,
            initial_state="ARMED",
        )
    history = subject.create_e4_thesis_history_v1(
        fingerprint=fingerprint,
        initial_state="ACTIONABLE",
    )
    if state == "ACTIONABLE":
        return history
    if state in ("SKIPPED", "REJECTED_BY_OWNER", "INVALIDATED"):
        return _append(history, state)
    history = _append(
        history,
        "PUBLISHED_PENDING_ENTRY",
        publication_succeeded=True,
    )
    if state == "PUBLISHED_PENDING_ENTRY":
        return history
    history = _append(history, "ENTRY_ACTIVE")
    if state == "ENTRY_ACTIVE":
        return history
    return _append(history, "CLOSED")


def _zone_exited_history(state):
    history = _history_for_state(state)
    return _append(history, state, price_exited_zone=True)


def _reset(history, candidate, *, state=None, zone=None):
    return adjudicate_e4_lifecycle_reset_v1(
        candidate_fingerprint=candidate,
        prior_fingerprint=history.events[-1].fingerprint,
        prior_state=history.current_state if state is None else state,
        price_exited_zone=(
            history.current_price_exited_zone if zone is None else zone
        ),
    )


def _successor(history, candidate, *, initial_state="ARMED", decision=None):
    if decision is None:
        decision = _reset(history, candidate)
    return _append(
        history,
        initial_state,
        fingerprint=candidate,
        publication_succeeded=False,
        price_exited_zone=False,
        reset_decision=decision,
    )


def _dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def test_exact_version_state_reuse_initial_states_and_transition_matrix():
    assert subject.E4_THESIS_HISTORY_VERSION == "e4-thesis-history-v1"
    assert subject.E4_THESIS_HISTORY_STATES is PREVIOUS_THESIS_STATES
    assert subject.E4_THESIS_HISTORY_STATES == (
        "ARMED",
        "ACTIONABLE",
        "PUBLISHED_PENDING_ENTRY",
        "ENTRY_ACTIVE",
        "SKIPPED",
        "REJECTED_BY_OWNER",
        "INVALIDATED",
        "CLOSED",
    )
    assert subject.E4_HISTORY_INITIAL_STATES == ("ARMED", "ACTIONABLE")
    assert subject.E4_SAME_FINGERPRINT_TRANSITIONS == TRANSITIONS
    assert len(TRANSITIONS) == 11


def test_event_and_history_are_frozen_slotted_with_exact_fields():
    history = _history_for_state("ACTIONABLE")
    event = history.events[0]
    assert subject.E4ThesisHistoryEventV1.__dataclass_params__.frozen
    assert subject.E4ThesisHistoryV1.__dataclass_params__.frozen
    assert not hasattr(event, "__dict__")
    assert not hasattr(history, "__dict__")
    assert tuple(field.name for field in dataclasses.fields(event)) == (
        "history_version",
        "sequence",
        "fingerprint",
        "state",
        "publication_succeeded",
        "price_exited_zone",
        "reset_decision",
        "previous_event_sha256",
        "event_sha256",
    )
    assert tuple(field.name for field in dataclasses.fields(history)) == (
        "history_version",
        "revision",
        "events",
        "fingerprint_history",
        "current_identity_sha256",
        "current_state",
        "current_publication_succeeded",
        "current_price_exited_zone",
        "history_sha256",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.state = "CLOSED"
    with pytest.raises(dataclasses.FrozenInstanceError):
        history.revision = 2


@pytest.mark.parametrize("initial_state", ("ARMED", "ACTIONABLE"))
def test_initial_history_creation(initial_state):
    fingerprint = _fingerprint()
    history = subject.create_e4_thesis_history_v1(
        fingerprint=fingerprint,
        initial_state=initial_state,
    )
    event = history.events[0]
    assert history.revision == 1
    assert history.events == (event,)
    assert event.sequence == 1
    assert event.fingerprint is fingerprint
    assert event.state == initial_state
    assert event.publication_succeeded is False
    assert event.price_exited_zone is False
    assert event.reset_decision is None
    assert event.previous_event_sha256 is None
    assert history.fingerprint_history == (fingerprint.identity_sha256,)


@pytest.mark.parametrize(
    "initial_state",
    ("SKIPPED", "CLOSED", "UNKNOWN", "", None),
)
def test_invalid_initial_state_fails_closed(initial_state):
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        subject.create_e4_thesis_history_v1(
            fingerprint=_fingerprint(),
            initial_state=initial_state,
        )


@pytest.mark.parametrize(("source_state", "target_state"), TRANSITIONS)
def test_all_same_fingerprint_transitions(source_state, target_state):
    history = _history_for_state(source_state)
    publication = history.current_publication_succeeded
    if target_state == "PUBLISHED_PENDING_ENTRY":
        publication = True
    appended = _append(
        history,
        target_state,
        publication_succeeded=publication,
    )
    assert appended.revision == history.revision + 1
    assert appended.current_state == target_state
    assert appended.current_identity_sha256 == history.current_identity_sha256
    assert appended.events[-1].reset_decision is None


@pytest.mark.parametrize(
    ("source_state", "target_state"),
    (
        ("ARMED", "SKIPPED"),
        ("ACTIONABLE", "CLOSED"),
        ("PUBLISHED_PENDING_ENTRY", "CLOSED"),
        ("ENTRY_ACTIVE", "ACTIONABLE"),
    ),
)
def test_invalid_same_fingerprint_transition_fails_closed(
    source_state,
    target_state,
):
    history = _history_for_state(source_state)
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(history, target_state)


@pytest.mark.parametrize(
    "terminal_state",
    ("SKIPPED", "REJECTED_BY_OWNER", "INVALIDATED", "CLOSED"),
)
def test_terminal_same_fingerprint_reactivation_fails_closed(terminal_state):
    history = _history_for_state(terminal_state)
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(history, "ARMED")


def test_publication_success_sticky_policy():
    actionable = _history_for_state("ACTIONABLE")
    pending_without_success = _append(
        actionable,
        "PUBLISHED_PENDING_ENTRY",
        publication_succeeded=False,
    )
    pending_with_success = _append(
        pending_without_success,
        "PUBLISHED_PENDING_ENTRY",
        publication_succeeded=True,
    )
    assert pending_with_success.current_publication_succeeded is True
    active = _append(pending_with_success, "ENTRY_ACTIVE")
    closed = _append(active, "CLOSED")
    assert active.current_publication_succeeded is True
    assert closed.current_publication_succeeded is True


def test_publication_success_first_state_reversion_and_duplicate_fail_closed():
    actionable = _history_for_state("ACTIONABLE")
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(actionable, "SKIPPED", publication_succeeded=True)
    pending = _append(
        actionable,
        "PUBLISHED_PENDING_ENTRY",
        publication_succeeded=True,
    )
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(pending, "ENTRY_ACTIVE", publication_succeeded=False)
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(pending, "PUBLISHED_PENDING_ENTRY")


@pytest.mark.parametrize("state", ("SKIPPED", "REJECTED_BY_OWNER"))
def test_zone_exit_sticky_evidence_for_owner_terminal_states(state):
    history = _history_for_state(state)
    exited = _append(history, state, price_exited_zone=True)
    assert exited.current_state == state
    assert exited.current_price_exited_zone is True
    assert exited.events[-1].price_exited_zone is True


def test_zone_exit_other_state_reversion_and_duplicate_fail_closed():
    actionable = _history_for_state("ACTIONABLE")
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(actionable, "ACTIONABLE", price_exited_zone=True)
    skipped = _zone_exited_history("SKIPPED")
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(skipped, "SKIPPED", price_exited_zone=False)
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(skipped, "SKIPPED", price_exited_zone=True)


def test_exact_no_op_event_fails_closed():
    history = _history_for_state("ARMED")
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(history, "ARMED")


@pytest.mark.parametrize(
    ("prior_state", "candidate_changes"),
    (
        (
            "SKIPPED",
            {
                "trigger_generation_id": "trg-" + "2" * 64,
                "trigger_candle_close_at": "2026-07-30T00:30:00Z",
            },
        ),
        (
            "REJECTED_BY_OWNER",
            {
                "trigger_generation_id": "trg-" + "2" * 64,
                "trigger_candle_close_at": "2026-07-30T00:30:00Z",
            },
        ),
        ("INVALIDATED", {"structure_generation_id": "structure:g2"}),
        ("CLOSED", {"anchor_low_tick": 9001}),
    ),
)
def test_allowed_successor_resets_append_new_fingerprint(
    prior_state,
    candidate_changes,
):
    history = (
        _zone_exited_history(prior_state)
        if prior_state in ("SKIPPED", "REJECTED_BY_OWNER")
        else _history_for_state(prior_state)
    )
    candidate = _fingerprint(**candidate_changes)
    decision = _reset(history, candidate)
    assert type(decision) is E4LifecycleResetDecisionV1
    assert decision.publication_allowed is True
    appended = _successor(history, candidate, decision=decision)
    assert appended.current_identity_sha256 == candidate.identity_sha256
    assert appended.current_state == "ARMED"
    assert appended.current_publication_succeeded is False
    assert appended.current_price_exited_zone is False
    assert appended.fingerprint_history == (
        history.fingerprint_history[0],
        candidate.identity_sha256,
    )


def test_suppressed_reset_decision_cannot_append_successor():
    history = _history_for_state("SKIPPED")
    candidate = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    decision = _reset(history, candidate)
    assert decision.publication_allowed is False
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _successor(history, candidate, decision=decision)


def test_reset_prior_fingerprint_mismatch_fails_closed():
    history = _zone_exited_history("SKIPPED")
    candidate = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    other_prior = _fingerprint(tp1_tick=12147)
    decision = adjudicate_e4_lifecycle_reset_v1(
        candidate_fingerprint=candidate,
        prior_fingerprint=other_prior,
        prior_state="SKIPPED",
        price_exited_zone=True,
    )
    assert decision.publication_allowed is True
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _successor(history, candidate, decision=decision)


def test_reset_candidate_fingerprint_mismatch_fails_closed():
    history = _zone_exited_history("SKIPPED")
    candidate = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    other_candidate = _fingerprint(trigger_generation_id="trg-" + "3" * 64)
    decision = _reset(history, other_candidate)
    assert decision.publication_allowed is True
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _successor(history, candidate, decision=decision)


def test_reset_prior_state_mismatch_fails_closed():
    history = _zone_exited_history("SKIPPED")
    candidate = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    decision = _reset(history, candidate, state="REJECTED_BY_OWNER")
    assert decision.publication_allowed is True
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _successor(history, candidate, decision=decision)


def test_reset_zone_exit_mismatch_fails_closed():
    history = _history_for_state("INVALIDATED")
    candidate = _fingerprint(structure_generation_id="structure:g2")
    decision = _reset(history, candidate, zone=True)
    assert decision.publication_allowed is True
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _successor(history, candidate, decision=decision)


@pytest.mark.parametrize(
    ("state", "publication_succeeded", "price_exited_zone"),
    (
        ("SKIPPED", False, False),
        ("ARMED", True, False),
        ("ARMED", False, True),
    ),
)
def test_successor_initial_state_and_flags_fail_closed(
    state,
    publication_succeeded,
    price_exited_zone,
):
    history = _history_for_state("INVALIDATED")
    candidate = _fingerprint(structure_generation_id="structure:g2")
    decision = _reset(history, candidate)
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _append(
            history,
            state,
            fingerprint=candidate,
            publication_succeeded=publication_succeeded,
            price_exited_zone=price_exited_zone,
            reset_decision=decision,
        )


def test_previously_seen_old_fingerprint_reuse_fails_closed():
    original = _fingerprint()
    history = subject.create_e4_thesis_history_v1(
        fingerprint=original,
        initial_state="ACTIONABLE",
    )
    history = _append(history, "INVALIDATED")
    successor = _fingerprint(structure_generation_id="structure:g2")
    history = _successor(history, successor)
    history = _append(history, "INVALIDATED")
    decision = _reset(history, original)
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        _successor(history, original, decision=decision)


def test_revision_sequences_hash_links_and_permanent_fingerprint_order():
    history = _zone_exited_history("SKIPPED")
    second = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    history = _successor(history, second, initial_state="ACTIONABLE")
    history = _append(history, "INVALIDATED")
    third = _fingerprint(
        trigger_generation_id="trg-" + "2" * 64,
        structure_generation_id="structure:g2",
    )
    history = _successor(history, third)
    assert history.revision == len(history.events) == 6
    assert tuple(event.sequence for event in history.events) == tuple(
        range(1, history.revision + 1)
    )
    assert history.events[0].previous_event_sha256 is None
    assert all(
        history.events[index].previous_event_sha256
        == history.events[index - 1].event_sha256
        for index in range(1, history.revision)
    )
    assert history.fingerprint_history == (
        history.events[0].fingerprint.identity_sha256,
        second.identity_sha256,
        third.identity_sha256,
    )


def test_event_and_history_canonical_hashes_are_deterministic():
    first = _history_for_state("PUBLISHED_PENDING_ENTRY")
    second = _history_for_state("PUBLISHED_PENDING_ENTRY")
    assert first == second
    event = first.events[-1]
    event_mapping = event.to_mapping()
    event_hash = event_mapping.pop("event_sha256")
    event_json = json.dumps(
        event_mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert event.canonical_event_json() == event_json
    assert event_hash == hashlib.sha256(event_json.encode("utf-8")).hexdigest()
    history_mapping = first.to_mapping()
    history_hash = history_mapping.pop("history_sha256")
    history_json = json.dumps(
        history_mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert first.canonical_history_json() == history_json
    assert history_hash == hashlib.sha256(
        history_json.encode("utf-8")
    ).hexdigest()


def test_reconstruction_round_trip_and_mapping_order_invariance():
    history = _zone_exited_history("REJECTED_BY_OWNER")
    candidate = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    history = _successor(history, candidate)
    mapping = history.to_mapping()
    reconstructed = subject.reconstruct_e4_thesis_history_v1(mapping)
    reordered = dict(reversed(tuple(mapping.items())))
    reordered_reconstruction = subject.reconstruct_e4_thesis_history_v1(
        reordered
    )
    assert reconstructed == history
    assert reconstructed.to_mapping() == mapping
    assert reconstructed.canonical_history_json() == history.canonical_history_json()
    assert reordered_reconstruction == history


@pytest.mark.parametrize("kind", ("missing", "extra"))
def test_missing_or_extra_history_mapping_key_fails_closed(kind):
    mapping = _history_for_state("ACTIONABLE").to_mapping()
    if kind == "missing":
        mapping.pop("revision")
    else:
        mapping["unexpected"] = "forbidden"
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        subject.reconstruct_e4_thesis_history_v1(mapping)


@pytest.mark.parametrize(
    "tamper",
    (
        "event_hash",
        "previous_hash",
        "fingerprint_history_duplicate",
        "fingerprint_history_missing",
        "current_identity",
        "current_state",
        "current_publication",
        "current_zone",
        "history_hash",
        "sequence_bool",
        "revision_bool",
    ),
)
def test_reconstruction_rejects_tampered_history(tamper):
    history = _history_for_state("PUBLISHED_PENDING_ENTRY")
    mapping = copy.deepcopy(history.to_mapping())
    if tamper == "event_hash":
        mapping["events"][-1]["event_sha256"] = "0" * 64
    elif tamper == "previous_hash":
        mapping["events"][-1]["previous_event_sha256"] = "0" * 64
    elif tamper == "fingerprint_history_duplicate":
        mapping["fingerprint_history"].append(mapping["fingerprint_history"][0])
    elif tamper == "fingerprint_history_missing":
        mapping["fingerprint_history"] = []
    elif tamper == "current_identity":
        mapping["current_identity_sha256"] = "0" * 64
    elif tamper == "current_state":
        mapping["current_state"] = "ARMED"
    elif tamper == "current_publication":
        mapping["current_publication_succeeded"] = False
    elif tamper == "current_zone":
        mapping["current_price_exited_zone"] = True
    elif tamper == "history_hash":
        mapping["history_sha256"] = "0" * 64
    elif tamper == "sequence_bool":
        mapping["events"][0]["sequence"] = True
    else:
        mapping["revision"] = True
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        subject.reconstruct_e4_thesis_history_v1(mapping)


def test_nested_mapping_keys_are_exact_and_publication_envelope_absent():
    history = _history_for_state("PUBLISHED_PENDING_ENTRY")
    event_keys = tuple(history.events[-1].to_mapping())
    history_keys = tuple(history.to_mapping())
    assert event_keys == (
        "history_version",
        "sequence",
        "fingerprint",
        "state",
        "publication_succeeded",
        "price_exited_zone",
        "reset_decision",
        "previous_event_sha256",
        "event_sha256",
    )
    assert history_keys == (
        "history_version",
        "revision",
        "events",
        "fingerprint_history",
        "current_identity_sha256",
        "current_state",
        "current_publication_succeeded",
        "current_price_exited_zone",
        "history_sha256",
    )
    def collect_mapping_keys(value):
        if isinstance(value, dict):
            keys = set(value)
            for nested_value in value.values():
                keys.update(collect_mapping_keys(nested_value))
            return keys
        if isinstance(value, (list, tuple)):
            keys = set()
            for nested_value in value:
                keys.update(collect_mapping_keys(nested_value))
            return keys
        return set()

    nested_mapping_keys = collect_mapping_keys(history.to_mapping())
    assert set(THESIS_EXCLUDED_FIELDS).isdisjoint(nested_mapping_keys)
    assert "current_price" not in nested_mapping_keys
    assert "current_price_exited_zone" in nested_mapping_keys
    assert not any(
        field in event_keys or field in history_keys
        for field in (
            "timestamp",
            "uuid",
            "current_price",
            "provider_result",
            "slot",
            "pair_lock",
        )
    )


def test_malformed_nested_mapping_and_invalid_dependency_fail_closed():
    mapping = _history_for_state("ACTIONABLE").to_mapping()
    mapping["events"][0]["fingerprint"]["extra"] = "forbidden"
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        subject.reconstruct_e4_thesis_history_v1(mapping)
    with pytest.raises(ValueError, match="^invalid E4 thesis history$"):
        subject.create_e4_thesis_history_v1(
            fingerprint=object(),
            initial_state="ACTIONABLE",
        )


def test_source_has_exact_dependencies_and_zero_external_effect_authority():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    project_imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and isinstance(node.module, str)
        and node.module.startswith("engine.")
    }
    assert project_imports == {
        "engine.e4_lifecycle_reset_adjudicator_v1",
        "engine.e4_thesis_fingerprint_v1",
    }
    forbidden_roots = {
        "aiohttp",
        "asyncio",
        "ccxt",
        "datetime",
        "httpx",
        "multiprocessing",
        "os",
        "pathlib",
        "random",
        "redis",
        "requests",
        "secrets",
        "socket",
        "sqlite3",
        "subprocess",
        "threading",
        "time",
        "urllib",
        "uuid",
    }
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots.isdisjoint(forbidden_roots)
    calls = {
        name
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        if (name := _dotted_name(node.func)) is not None
    }
    assert calls.isdisjoint(
        {
            "open",
            "eval",
            "exec",
            "compile",
            "__import__",
            "datetime.now",
            "datetime.utcnow",
            "date.today",
            "time.time",
            "random.random",
            "uuid.uuid4",
            "os.getenv",
        }
    )
    assert not any(
        call.endswith(
            (
                ".send",
                ".publish",
                ".create_order",
                ".place_order",
                ".write_text",
                ".write_bytes",
                ".commit",
                ".acquire",
                ".lock",
            )
        )
        for call in calls
    )
    assert all(
        not isinstance(
            node,
            (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom),
        )
        for node in ast.walk(tree)
    )
