import ast
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e4_lifecycle_reset_adjudicator_v1 as subject
from engine.e4_thesis_fingerprint_v1 import (
    E4ThesisFingerprintV1,
    THESIS_EXCLUDED_FIELDS,
    THESIS_IDENTITY_FIELDS,
)


STATES = (
    "ARMED",
    "ACTIONABLE",
    "PUBLISHED_PENDING_ENTRY",
    "ENTRY_ACTIVE",
    "SKIPPED",
    "REJECTED_BY_OWNER",
    "INVALIDATED",
    "CLOSED",
)

DECISIONS = (
    "ALLOW_INITIAL_PUBLICATION",
    "ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER",
    "ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER",
    "ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS",
    "ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS",
    "SUPPRESS_SAME_FINGERPRINT",
    "SUPPRESS_ARMED_STATE",
    "SUPPRESS_ACTIONABLE_STATE",
    "SUPPRESS_PUBLISHED_PENDING_ENTRY_STATE",
    "SUPPRESS_ENTRY_ACTIVE_STATE",
    "SUPPRESS_ZONE_EXIT_REQUIRED",
    "SUPPRESS_NEW_TRIGGER_GENERATION_REQUIRED",
    "SUPPRESS_NEW_STRUCTURE_OR_ANCHORS_REQUIRED",
    "SUPPRESS_TIME_ONLY_RESET",
    "SUPPRESS_UNSUPPORTED_IDENTITY_DELTA",
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


def _adjudicate(
    state,
    candidate,
    *,
    prior=None,
    price_exited_zone=False,
):
    if prior is None:
        prior = _fingerprint()
    return subject.adjudicate_e4_lifecycle_reset_v1(
        candidate_fingerprint=candidate,
        prior_fingerprint=prior,
        prior_state=state,
        price_exited_zone=price_exited_zone,
    )


def _dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def test_exact_policy_states_and_decision_codes():
    assert subject.POLICY_VERSION == "e4-lifecycle-reset-policy-v1"
    assert subject.PREVIOUS_THESIS_STATES == STATES
    assert subject.DECISION_CODES == DECISIONS
    assert len(STATES) == 8
    assert len(DECISIONS) == 15
    assert tuple(getattr(subject, code) for code in DECISIONS) == DECISIONS


def test_result_is_frozen_slotted_and_builder_has_exact_signature():
    result = subject.adjudicate_e4_lifecycle_reset_v1(
        candidate_fingerprint=_fingerprint(),
        prior_fingerprint=None,
        prior_state=None,
        price_exited_zone=False,
    )
    assert subject.E4LifecycleResetDecisionV1.__dataclass_params__.frozen
    assert not hasattr(result, "__dict__")
    assert tuple(field.name for field in dataclasses.fields(result)) == (
        "policy_version",
        "prior_history_exists",
        "prior_state",
        "prior_identity_sha256",
        "candidate_identity_sha256",
        "same_fingerprint",
        "changed_identity_fields",
        "price_exited_zone",
        "trigger_generation_changed",
        "trigger_candle_close_changed",
        "structure_generation_changed",
        "anchor_pair_changed",
        "publication_allowed",
        "decision_code",
        "decision_sha256",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.decision_code = "SUPPRESS_SAME_FINGERPRINT"
    signature = inspect.signature(subject.adjudicate_e4_lifecycle_reset_v1)
    assert tuple(signature.parameters) == (
        "candidate_fingerprint",
        "prior_fingerprint",
        "prior_state",
        "price_exited_zone",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert not any(
        marker in signature.parameters
        for marker in ("time", "expiry", "signal_id", "delivery_id")
    )


def test_no_prior_history_allows_initial_publication():
    candidate = _fingerprint()
    result = subject.adjudicate_e4_lifecycle_reset_v1(
        candidate_fingerprint=candidate,
        prior_fingerprint=None,
        prior_state=None,
        price_exited_zone=False,
    )
    assert result.prior_history_exists is False
    assert result.prior_state is None
    assert result.prior_identity_sha256 is None
    assert result.changed_identity_fields == ()
    assert result.publication_allowed is True
    assert result.decision_code == subject.ALLOW_INITIAL_PUBLICATION


@pytest.mark.parametrize("state", STATES)
def test_same_fingerprint_is_suppressed_for_every_prior_state(state):
    fingerprint = _fingerprint()
    result = _adjudicate(state, fingerprint, prior=fingerprint, price_exited_zone=True)
    assert result.same_fingerprint is True
    assert result.changed_identity_fields == ()
    assert result.publication_allowed is False
    assert result.decision_code == subject.SUPPRESS_SAME_FINGERPRINT


@pytest.mark.parametrize(
    ("state", "candidate", "expected"),
    (
        (
            "ARMED",
            {"trigger_generation_id": "trg-" + "2" * 64},
            "SUPPRESS_ARMED_STATE",
        ),
        (
            "ACTIONABLE",
            {"trigger_generation_id": "trg-" + "2" * 64},
            "SUPPRESS_ACTIONABLE_STATE",
        ),
        (
            "PUBLISHED_PENDING_ENTRY",
            {"structure_generation_id": "structure:g2"},
            "SUPPRESS_PUBLISHED_PENDING_ENTRY_STATE",
        ),
        (
            "ENTRY_ACTIVE",
            {"structure_generation_id": "structure:g2"},
            "SUPPRESS_ENTRY_ACTIVE_STATE",
        ),
    ),
)
def test_nonterminal_states_remain_suppressed_after_identity_change(
    state,
    candidate,
    expected,
):
    result = _adjudicate(state, _fingerprint(**candidate), price_exited_zone=True)
    assert result.publication_allowed is False
    assert result.decision_code == expected


def test_skipped_reset_policy():
    new_trigger = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    no_zone = _adjudicate("SKIPPED", new_trigger, price_exited_zone=False)
    assert no_zone.decision_code == subject.SUPPRESS_ZONE_EXIT_REQUIRED
    same_generation = _adjudicate(
        "SKIPPED",
        _fingerprint(tp1_tick=12147),
        price_exited_zone=True,
    )
    assert same_generation.decision_code == (
        subject.SUPPRESS_NEW_TRIGGER_GENERATION_REQUIRED
    )
    time_only = _adjudicate(
        "SKIPPED",
        _fingerprint(trigger_candle_close_at="2026-07-30T00:30:00Z"),
        price_exited_zone=True,
    )
    assert time_only.changed_identity_fields == ("trigger_candle_close_at",)
    assert time_only.decision_code == subject.SUPPRESS_TIME_ONLY_RESET
    allowed = _adjudicate("SKIPPED", new_trigger, price_exited_zone=True)
    assert allowed.trigger_generation_changed is True
    assert allowed.publication_allowed is True
    assert allowed.decision_code == (
        subject.ALLOW_SKIPPED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER
    )


def test_rejected_by_owner_reset_policy():
    new_trigger = _fingerprint(trigger_generation_id="trg-" + "2" * 64)
    no_zone = _adjudicate(
        "REJECTED_BY_OWNER",
        new_trigger,
        price_exited_zone=False,
    )
    assert no_zone.decision_code == subject.SUPPRESS_ZONE_EXIT_REQUIRED
    same_generation = _adjudicate(
        "REJECTED_BY_OWNER",
        _fingerprint(tp2_tick=12529),
        price_exited_zone=True,
    )
    assert same_generation.decision_code == (
        subject.SUPPRESS_NEW_TRIGGER_GENERATION_REQUIRED
    )
    allowed = _adjudicate(
        "REJECTED_BY_OWNER",
        new_trigger,
        price_exited_zone=True,
    )
    assert allowed.publication_allowed is True
    assert allowed.decision_code == (
        subject.ALLOW_REJECTED_AFTER_ZONE_EXIT_AND_NEW_TRIGGER
    )


def test_invalidated_reset_policy():
    trigger_only = _adjudicate(
        "INVALIDATED",
        _fingerprint(trigger_generation_id="trg-" + "2" * 64),
    )
    assert trigger_only.decision_code == (
        subject.SUPPRESS_NEW_STRUCTURE_OR_ANCHORS_REQUIRED
    )
    time_only = _adjudicate(
        "INVALIDATED",
        _fingerprint(trigger_candle_close_at="2026-07-30T00:30:00Z"),
    )
    assert time_only.decision_code == subject.SUPPRESS_TIME_ONLY_RESET
    structure = _adjudicate(
        "INVALIDATED",
        _fingerprint(structure_generation_id="structure:g2"),
    )
    assert structure.structure_generation_changed is True
    assert structure.publication_allowed is True
    assert structure.decision_code == (
        subject.ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS
    )
    anchors = _adjudicate(
        "INVALIDATED",
        _fingerprint(anchor_low_tick=9001),
    )
    assert anchors.anchor_pair_changed is True
    assert anchors.publication_allowed is True
    assert anchors.decision_code == (
        subject.ALLOW_INVALIDATED_AFTER_NEW_STRUCTURE_OR_ANCHORS
    )


def test_closed_reset_policy():
    trigger_only = _adjudicate(
        "CLOSED",
        _fingerprint(trigger_generation_id="trg-" + "2" * 64),
    )
    assert trigger_only.decision_code == (
        subject.SUPPRESS_NEW_STRUCTURE_OR_ANCHORS_REQUIRED
    )
    structure = _adjudicate(
        "CLOSED",
        _fingerprint(structure_generation_id="structure:g2"),
    )
    assert structure.publication_allowed is True
    assert structure.decision_code == (
        subject.ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS
    )
    anchors = _adjudicate("CLOSED", _fingerprint(anchor_high_tick=12001))
    assert anchors.anchor_pair_changed is True
    assert anchors.publication_allowed is True
    assert anchors.decision_code == (
        subject.ALLOW_CLOSED_AFTER_NEW_STRUCTURE_OR_ANCHORS
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("canonical_pair", "ETH/USDT"),
        ("mode", "INTRADAY"),
        ("side", "SHORT"),
        ("strategy_version", "master-engine-v5"),
        ("mode_profile_version", "mode-profile-v2"),
        ("structure_timeframe", "15m"),
        ("target_policy_version", "target-policy-v2"),
        ("trigger_type", "another closed trigger"),
        ("trigger_timeframe", "5m"),
    ),
)
def test_unsupported_context_change_fails_closed(field, value):
    result = _adjudicate(
        "SKIPPED",
        _fingerprint(**{field: value}),
        price_exited_zone=True,
    )
    assert result.publication_allowed is False
    assert result.decision_code == subject.SUPPRESS_UNSUPPORTED_IDENTITY_DELTA


def test_changed_identity_fields_preserve_frozen_field_order():
    candidate = _fingerprint(
        anchor_low_tick=9001,
        structure_generation_id="structure:g2",
        trigger_generation_id="trg-" + "2" * 64,
        trigger_candle_close_at="2026-07-30T00:30:00Z",
    )
    result = _adjudicate("INVALIDATED", candidate)
    assert result.changed_identity_fields == tuple(
        field
        for field in THESIS_IDENTITY_FIELDS
        if field
        in {
            "structure_generation_id",
            "anchor_low_tick",
            "trigger_generation_id",
            "trigger_candle_close_at",
        }
    )


def test_canonical_decision_json_and_sha256_are_deterministic():
    first = _adjudicate(
        "SKIPPED",
        _fingerprint(trigger_generation_id="trg-" + "2" * 64),
        price_exited_zone=True,
    )
    second = _adjudicate(
        "SKIPPED",
        _fingerprint(trigger_generation_id="trg-" + "2" * 64),
        price_exited_zone=True,
    )
    mapping = first.to_mapping()
    supplied_hash = mapping.pop("decision_sha256")
    expected_json = json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert first == second
    assert first.canonical_decision_json() == expected_json
    assert supplied_hash == hashlib.sha256(
        expected_json.encode("utf-8")
    ).hexdigest()
    assert first.decision_sha256 == second.decision_sha256
    detached = first.to_mapping()
    detached["decision_code"] = "SUPPRESS_SAME_FINGERPRINT"
    assert first.publication_allowed is True


def test_incorrect_supplied_decision_hash_fails_closed():
    result = _adjudicate(
        "CLOSED",
        _fingerprint(structure_generation_id="structure:g2"),
    )
    with pytest.raises(
        ValueError,
        match="^invalid E4 lifecycle reset adjudication$",
    ):
        dataclasses.replace(result, decision_sha256="0" * 64)


@pytest.mark.parametrize(
    "case",
    (
        "prior_without_state",
        "state_without_prior",
        "unknown_state",
        "bool_as_int",
        "invalid_fingerprint",
    ),
)
def test_malformed_inputs_fail_closed(case):
    fingerprint = _fingerprint()
    arguments = {
        "candidate_fingerprint": fingerprint,
        "prior_fingerprint": fingerprint,
        "prior_state": "ARMED",
        "price_exited_zone": False,
    }
    if case == "prior_without_state":
        arguments["prior_state"] = None
    elif case == "state_without_prior":
        arguments["prior_fingerprint"] = None
    elif case == "unknown_state":
        arguments["prior_state"] = "PUBLISHED"
    elif case == "bool_as_int":
        arguments["price_exited_zone"] = 1
    else:
        arguments["candidate_fingerprint"] = object()
    with pytest.raises(
        ValueError,
        match="^invalid E4 lifecycle reset adjudication$",
    ):
        subject.adjudicate_e4_lifecycle_reset_v1(**arguments)


@pytest.mark.parametrize("excluded_field", THESIS_EXCLUDED_FIELDS)
def test_publication_envelope_changes_do_not_alter_adjudication(excluded_field):
    fingerprint = _fingerprint()
    first_envelope = {excluded_field: "one"}
    second_envelope = {excluded_field: "two"}
    first = _adjudicate("ACTIONABLE", fingerprint, prior=fingerprint)
    second = _adjudicate("ACTIONABLE", fingerprint, prior=fingerprint)
    assert first_envelope != second_envelope
    assert excluded_field not in inspect.signature(
        subject.adjudicate_e4_lifecycle_reset_v1
    ).parameters
    assert first == second
    assert first.decision_code == subject.SUPPRESS_SAME_FINGERPRINT


def test_source_has_exact_dependency_and_zero_external_effect_authority():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    project_imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and isinstance(node.module, str)
        and node.module.startswith("engine.")
    }
    assert project_imports == {"engine.e4_thesis_fingerprint_v1"}
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
