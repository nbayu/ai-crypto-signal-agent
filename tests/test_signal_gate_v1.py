"""RED contract tests for the pure deterministic Signal Gate boundary."""

from __future__ import annotations

import hashlib
import inspect
import ast

import pytest

import engine.news_risk_object_v1 as news_risk
import engine.signal_gate_v1 as signal_gate
from engine.deterministic_adjudication_v1 import (
    DeterministicAdjudicationResultV1,
    DeterministicAdjudicationPolicyV1,
)
from engine.news_event_contract_v1 import canonical_json_bytes


NEWS_RISK_POLICY_VERSION = "news-risk-policy-v1"
SIGNAL_GATE_POLICY_VERSION = "signal-gate-policy-v1"
EVENT = "a" * 64
OTHER_EVENT = "b" * 64
NEWS_RISK_ID = "c" * 64
OTHER_NEWS_RISK_ID = "d" * 64
ROUTE_DECISION_ID = "e" * 64


def _hash(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _policy(**overrides):
    values = {
        "policy_version": SIGNAL_GATE_POLICY_VERSION,
        "supported_news_risk_policy_versions": (NEWS_RISK_POLICY_VERSION,),
        "supported_routes": ("L0", "L1", "L2"),
        "supported_risk_classifications": ("CLEAR", "CAUTION", "ELEVATED", "BLOCKING", "FAIL_CLOSED"),
        "supported_news_gate_recommendations": (
            "NO_NEWS_RESTRICTION",
            "REQUIRE_CAUTION",
            "REQUIRE_BLOCK",
            "FAIL_CLOSED",
        ),
        "risk_to_gate_state": {
            "CLEAR": "OPEN",
            "CAUTION": "CAUTION",
            "ELEVATED": "BLOCKED",
            "BLOCKING": "BLOCKED",
            "FAIL_CLOSED": "FAIL_CLOSED",
        },
        "recommendation_to_gate_state": {
            "NO_NEWS_RESTRICTION": "OPEN",
            "REQUIRE_CAUTION": "CAUTION",
            "REQUIRE_BLOCK": "BLOCKED",
            "FAIL_CLOSED": "FAIL_CLOSED",
        },
        "blocking_reason_codes": (
            "CRITICAL_MATERIAL_RISK",
            "CRITICAL_CONTRADICTION",
            "CRITICAL_ENTITY_CONCERN",
            "CRITICAL_SOURCE_CONCERN",
        ),
        "caution_reason_codes": (
            "INSUFFICIENT_EVIDENCE",
            "EVIDENCE_LIMITED",
            "MODERATE_ENTITY_CONCERN",
            "MODERATE_SOURCE_CONCERN",
            "QUALIFIED_ADJUDICATION",
        ),
        "fail_closed_reason_codes": (
            "FAIL_CLOSED_ADJUDICATION",
            "UNSUPPORTED_POLICY",
            "FORGED_IDENTITY",
            "INVALID_ADJUDICATION",
        ),
        "deterministic_reason_order": (
            "INVALID_NEWS_RISK_OBJECT",
            "UNSUPPORTED_POLICY",
            "FORGED_NEWS_RISK_IDENTITY",
            "FAIL_CLOSED_NEWS_RISK",
            "FAIL_CLOSED_GATE_POLICY",
            "NEWS_RISK_BLOCKING",
            "CRITICAL_MATERIAL_RISK",
            "CRITICAL_CONTRADICTION",
            "CRITICAL_ENTITY_CONCERN",
            "CRITICAL_SOURCE_CONCERN",
            "BLOCKING_NEWS_REASON",
            "BLOCK_RECOMMENDED",
            "NEWS_RISK_ELEVATED",
            "NEWS_RISK_CAUTION",
            "CAUTION_RECOMMENDED",
            "LIMITED_EVIDENCE",
            "QUALIFIED_NEWS_ASSESSMENT",
            "NEWS_RISK_CLEAR",
            "NO_NEWS_RESTRICTION",
        ),
        "maximum_reason_code_count": 19,
        "maximum_evidence_reference_count": 16,
    }
    values.update(overrides)
    return signal_gate.SignalGatePolicyV1(**values)


def _risk_identity(values):
    return _hash(
        {
            "policy_version": values["policy_version"],
            "event_snapshot_id": values["event_snapshot_id"],
            "adjudication_policy_version": values["adjudication_policy_version"],
            "adjudication_result_id": values["adjudication_result_id"],
            "route": values["route"],
            "risk_classification": values["risk_classification"],
            "news_gate_recommendation": values["news_gate_recommendation"],
            "final_ambiguity_state": values["final_ambiguity_state"],
            "final_contradiction_state": values["final_contradiction_state"],
            "final_evidence_state": values["final_evidence_state"],
            "final_entity_state": values["final_entity_state"],
            "final_source_state": values["final_source_state"],
            "final_material_risk_state": values["final_material_risk_state"],
            "reason_codes": list(values["reason_codes"]),
            "evidence_refs": list(values["evidence_refs"]),
        }
    )


def _risk(**overrides):
    values = {
        "policy_version": NEWS_RISK_POLICY_VERSION,
        "event_snapshot_id": EVENT,
        "adjudication_policy_version": "deterministic-adjudication-policy-v1",
        "adjudication_result_id": NEWS_RISK_ID,
        "route": "L1",
        "risk_classification": "CLEAR",
        "news_gate_recommendation": "NO_NEWS_RESTRICTION",
        "final_ambiguity_state": "NONE",
        "final_contradiction_state": "NONE",
        "final_evidence_state": "SUFFICIENT",
        "final_entity_state": "ACCEPTABLE",
        "final_source_state": "ACCEPTABLE",
        "final_material_risk_state": "NONE",
        "reason_codes": ("ADJUDICATION_CONFIRMED", "NO_MATERIAL_NEWS_RISK", "EVIDENCE_SUFFICIENT"),
        "evidence_refs": ("evidence-001",),
        "structured_explanation": "News Risk fixture.",
        "news_risk_object_id": None,
    }
    values.update(overrides)
    values["reason_codes"] = tuple(sorted(set(values["reason_codes"])))
    values["evidence_refs"] = tuple(sorted(set(values["evidence_refs"])))
    values["news_risk_object_id"] = _risk_identity(values)
    return news_risk.NewsRiskObjectV1(**values)


def _evaluate(risk=None, policy=None):
    return signal_gate.evaluate_signal_gate(
        _risk() if risk is None else risk,
        _policy() if policy is None else policy,
    )


def test_public_api_and_policy_version_are_frozen():
    assert signal_gate.SIGNAL_GATE_POLICY_VERSION == SIGNAL_GATE_POLICY_VERSION
    assert signal_gate.__all__ == (
        "SignalGateError",
        "SIGNAL_GATE_POLICY_VERSION",
        "SignalGatePolicyV1",
        "SignalGateDecisionV1",
        "evaluate_signal_gate",
    )
    assert type(signal_gate.__all__) is tuple
    assert len(set(signal_gate.__all__)) == 5


def test_policy_is_closed_immutable_and_normalized():
    policy = _policy(
        supported_routes=("L2", "L0", "L1", "L1"),
        blocking_reason_codes=("CRITICAL_MATERIAL_RISK", "CRITICAL_MATERIAL_RISK"),
    )
    assert policy.supported_routes == ("L0", "L1", "L2")
    assert policy.blocking_reason_codes == ("CRITICAL_MATERIAL_RISK",)
    with pytest.raises((AttributeError, TypeError)):
        policy.supported_routes = ("L0",)
    with pytest.raises(signal_gate.SignalGateError):
        signal_gate.SignalGatePolicyV1(**{**policy.__dict__, "unknown": True})


@pytest.mark.parametrize("field", ["maximum_reason_code_count", "maximum_evidence_reference_count"])
@pytest.mark.parametrize("value", [True, False, 1.0, 0, -1])
def test_policy_limits_require_positive_integers(field, value):
    with pytest.raises(signal_gate.SignalGateError):
        _policy(**{field: value})


@pytest.mark.parametrize(
    "overrides",
    [
        {"policy_version": "wrong-policy-v1"},
        {"supported_news_risk_policy_versions": ("other-policy-v1",)},
        {"supported_routes": ("L0", "L1")},
        {"supported_risk_classifications": ("BUY",)},
        {"risk_to_gate_state": {"CLEAR": "TRADE"}},
        {"fail_closed_reason_codes": ("UNKNOWN",)},
    ],
)
def test_policy_rejects_unsupported_or_unsafe_configuration(overrides):
    with pytest.raises(signal_gate.SignalGateError):
        _policy(**overrides)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        "risk",
        object(),
        DeterministicAdjudicationResultV1,
        DeterministicAdjudicationPolicyV1,
    ],
)
def test_exact_news_risk_input_type_is_required(bad):
    with pytest.raises(signal_gate.SignalGateError):
        signal_gate.evaluate_signal_gate(bad, _policy())


def test_exact_policy_input_type_is_required():
    with pytest.raises(signal_gate.SignalGateError):
        signal_gate.evaluate_signal_gate(_risk(), {})


@pytest.mark.parametrize(
    ("classification", "recommendation", "state", "eligibility"),
    [
        ("CLEAR", "NO_NEWS_RESTRICTION", "OPEN", "ALLOW_NEWS_ELIGIBILITY"),
        ("CAUTION", "REQUIRE_CAUTION", "CAUTION", "REQUIRE_NEWS_CAUTION"),
        ("ELEVATED", "REQUIRE_CAUTION", "BLOCKED", "DENY_NEWS_ELIGIBILITY"),
        ("BLOCKING", "REQUIRE_BLOCK", "BLOCKED", "DENY_NEWS_ELIGIBILITY"),
        ("FAIL_CLOSED", "FAIL_CLOSED", "FAIL_CLOSED", "FAIL_CLOSED"),
    ],
)
def test_risk_classification_mapping_is_deterministic(classification, recommendation, state, eligibility):
    result = _evaluate(_risk(risk_classification=classification, news_gate_recommendation=recommendation))
    assert result.gate_state == state
    assert result.eligibility_recommendation == eligibility


@pytest.mark.parametrize(
    ("classification", "recommendation", "state", "eligibility"),
    [
        ("CLEAR", "NO_NEWS_RESTRICTION", "OPEN", "ALLOW_NEWS_ELIGIBILITY"),
        ("CAUTION", "REQUIRE_CAUTION", "CAUTION", "REQUIRE_NEWS_CAUTION"),
        ("BLOCKING", "REQUIRE_BLOCK", "BLOCKED", "DENY_NEWS_ELIGIBILITY"),
        ("FAIL_CLOSED", "FAIL_CLOSED", "FAIL_CLOSED", "FAIL_CLOSED"),
    ],
)
def test_recommendation_mapping_is_deterministic(classification, recommendation, state, eligibility):
    result = _evaluate(_risk(risk_classification=classification, news_gate_recommendation=recommendation))
    assert result.gate_state == state
    assert result.eligibility_recommendation == eligibility


@pytest.mark.parametrize(
    ("classification", "recommendation", "state"),
    [
        ("FAIL_CLOSED", "FAIL_CLOSED", "FAIL_CLOSED"),
        ("BLOCKING", "REQUIRE_BLOCK", "BLOCKED"),
        ("ELEVATED", "REQUIRE_CAUTION", "BLOCKED"),
        ("CAUTION", "REQUIRE_CAUTION", "CAUTION"),
        ("CLEAR", "NO_NEWS_RESTRICTION", "OPEN"),
    ],
)
def test_highest_severity_precedence_wins(classification, recommendation, state):
    result = _evaluate(_risk(risk_classification=classification, news_gate_recommendation=recommendation))
    assert result.gate_state == state


@pytest.mark.parametrize(
    ("reason", "state", "eligibility"),
    [
        ("CRITICAL_MATERIAL_RISK", "BLOCKED", "DENY_NEWS_ELIGIBILITY"),
    ],
)
def test_configured_reason_precedence_wins(reason, state, eligibility):
    result = _evaluate(_risk(reason_codes=(reason,)))
    assert result.gate_state == state
    assert result.eligibility_recommendation == eligibility
    assert reason in result.reason_codes


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("fail_closed_reason_codes", "FAIL_CLOSED_ADJUDICATION"),
        ("blocking_reason_codes", "CRITICAL_MATERIAL_RISK"),
        ("caution_reason_codes", "INSUFFICIENT_EVIDENCE"),
    ],
)
def test_policy_reason_matchers_accept_reachable_upstream_values(field, reason):
    policy = _policy(**{field: (reason,)})
    assert getattr(policy, field) == (reason,)


@pytest.mark.parametrize(
    "field",
    ["fail_closed_reason_codes", "blocking_reason_codes", "caution_reason_codes"],
)
def test_policy_reason_matchers_reject_downstream_only_values(field):
    with pytest.raises(signal_gate.SignalGateError):
        _policy(**{field: ("NEWS_RISK_CLEAR",)})


@pytest.mark.parametrize(
    ("field", "reason", "state", "eligibility"),
    [
        ("fail_closed_reason_codes", "FAIL_CLOSED_ADJUDICATION", "FAIL_CLOSED", "FAIL_CLOSED"),
        ("blocking_reason_codes", "CRITICAL_MATERIAL_RISK", "BLOCKED", "DENY_NEWS_ELIGIBILITY"),
        ("caution_reason_codes", "INSUFFICIENT_EVIDENCE", "CAUTION", "REQUIRE_NEWS_CAUTION"),
    ],
)
def test_reachable_upstream_reason_precedence_is_separate_from_output(field, reason, state, eligibility):
    policy = _policy(**{field: (reason,)})
    result = _evaluate(_risk(reason_codes=(reason,)), policy)
    assert result.gate_state == state
    assert result.eligibility_recommendation == eligibility
    assert result.reason_codes == tuple(
        code for code in policy.deterministic_reason_order if code in result.reason_codes
    )
    if reason != "CRITICAL_MATERIAL_RISK":
        assert reason not in result.reason_codes


def test_l0_route_is_preserved_as_semantic_data():
    result = _evaluate(_risk(route="L0"))
    assert result.route == "L0"
    assert result.gate_state == "OPEN"


@pytest.mark.parametrize(
    "override",
    [
        {"policy_version": "other-news-risk-policy-v1"},
        {"news_risk_object_id": "9" * 64},
        {"event_snapshot_id": "not-a-hash"},
        {"route": "L3"},
        {"risk_classification": "BUY"},
        {"news_gate_recommendation": "TRADE"},
        {"final_evidence_state": "UNKNOWN"},
        {"reason_codes": ("UNKNOWN",)},
        {"evidence_refs": ("bad ref",)},
    ],
)
def test_malformed_or_forged_news_risk_is_rejected(override):
    values = {
        "policy_version": NEWS_RISK_POLICY_VERSION,
        "event_snapshot_id": EVENT,
        "adjudication_policy_version": "deterministic-adjudication-policy-v1",
        "adjudication_result_id": NEWS_RISK_ID,
        "route": "L1",
        "risk_classification": "CLEAR",
        "news_gate_recommendation": "NO_NEWS_RESTRICTION",
        "final_ambiguity_state": "NONE",
        "final_contradiction_state": "NONE",
        "final_evidence_state": "SUFFICIENT",
        "final_entity_state": "ACCEPTABLE",
        "final_source_state": "ACCEPTABLE",
        "final_material_risk_state": "NONE",
        "reason_codes": ("ADJUDICATION_CONFIRMED",),
        "evidence_refs": ("evidence-001",),
        "structured_explanation": "fixture",
        "news_risk_object_id": None,
    }
    values.update(override)
    with pytest.raises((news_risk.NewsRiskObjectError, signal_gate.SignalGateError)):
        evaluate_input = news_risk.NewsRiskObjectV1(**values)
        _evaluate(evaluate_input)


def test_news_risk_identity_is_revalidated_before_mapping():
    risk = _risk()
    forged = object.__new__(news_risk.NewsRiskObjectV1)
    for name in risk.__dataclass_fields__:
        object.__setattr__(forged, name, getattr(risk, name))
    object.__setattr__(forged, "news_risk_object_id", "9" * 64)
    with pytest.raises(signal_gate.SignalGateError):
        _evaluate(forged)


def test_event_and_news_risk_bindings_are_preserved():
    first = _evaluate(_risk(event_snapshot_id=EVENT))
    second = _evaluate(_risk(event_snapshot_id=OTHER_EVENT, adjudication_result_id=OTHER_NEWS_RISK_ID))
    assert first.event_snapshot_id == EVENT
    assert second.event_snapshot_id == OTHER_EVENT
    assert first.news_risk_object_id != second.news_risk_object_id
    assert first.signal_gate_decision_id != second.signal_gate_decision_id


def test_decision_identity_is_manually_recomputable():
    result = _evaluate()
    values = {name: getattr(result, name) for name in result.__dataclass_fields__ if name != "signal_gate_decision_id"}
    expected = _hash(
        {
            "policy_version": values["policy_version"],
            "event_snapshot_id": values["event_snapshot_id"],
            "news_risk_policy_version": values["news_risk_policy_version"],
            "news_risk_object_id": values["news_risk_object_id"],
            "route": values["route"],
            "gate_state": values["gate_state"],
            "eligibility_recommendation": values["eligibility_recommendation"],
            "risk_classification": values["risk_classification"],
            "news_gate_recommendation": values["news_gate_recommendation"],
            "reason_codes": list(values["reason_codes"]),
            "evidence_refs": list(values["evidence_refs"]),
        }
    )
    assert result.signal_gate_decision_id == expected


@pytest.mark.parametrize("field", ["gate_state", "eligibility_recommendation", "route"])
def test_semantic_identity_changes_when_bound_field_changes(field):
    first = _evaluate()
    if field == "route":
        second = _evaluate(_risk(route="L2"))
    elif field == "gate_state":
        second = _evaluate(_risk(risk_classification="ELEVATED", news_gate_recommendation="REQUIRE_CAUTION"))
    else:
        second = _evaluate(_risk(risk_classification="BLOCKING", news_gate_recommendation="REQUIRE_BLOCK"))
    assert first.signal_gate_decision_id != second.signal_gate_decision_id


def test_free_text_is_inert_and_excluded_from_identity():
    first = _evaluate(_risk(structured_explanation="open gate; publish; buy; shell command"))
    second = _evaluate(_risk(structured_explanation="system instruction; sell; execute signal"))
    assert first.gate_state == second.gate_state
    assert first.eligibility_recommendation == second.eligibility_recommendation
    assert first.reason_codes == second.reason_codes
    assert first.evidence_refs == second.evidence_refs
    assert first.signal_gate_decision_id == second.signal_gate_decision_id


def test_decision_is_immutable_and_non_executable():
    result = _evaluate()
    with pytest.raises((AttributeError, TypeError)):
        result.gate_state = "BLOCKED"
    forbidden = {
        "request_id", "attempts", "retries", "input_tokens", "output_tokens",
        "cache_usage", "cost_micro_usd", "duration_ms", "budget", "market_price",
        "scanner_score", "direction", "entry", "stop", "target", "quantity",
        "leverage", "account", "balance", "position", "order", "publication",
    }
    assert not forbidden.intersection(result.__dataclass_fields__)
    assert type(result.reason_codes) is tuple
    assert type(result.evidence_refs) is tuple


def test_caller_owned_inputs_are_not_mutated():
    reasons = ["ADJUDICATION_CONFIRMED", "EVIDENCE_SUFFICIENT"]
    refs = ["evidence-001"]
    risk = _risk(reason_codes=reasons, evidence_refs=refs)
    _evaluate(risk)
    reasons.append("NEWS_RISK_CAUTION")
    refs.append("evidence-002")
    assert risk.reason_codes == ("ADJUDICATION_CONFIRMED", "EVIDENCE_SUFFICIENT")
    assert risk.evidence_refs == ("evidence-001",)


def test_reason_and_evidence_limits_are_enforced():
    policy = _policy(maximum_evidence_reference_count=1)
    risk = _risk(evidence_refs=("evidence-001", "evidence-002"))
    with pytest.raises(signal_gate.SignalGateError):
        _evaluate(risk, policy)


def test_operational_and_downstream_objects_are_not_inputs():
    for bad in (object(), {"request_id": "req-1"}, {"market_price": 1}, {"signal": "BUY"}):
        with pytest.raises(signal_gate.SignalGateError):
            signal_gate.evaluate_signal_gate(bad, _policy())


def test_signal_gate_source_has_no_external_or_downstream_authority():
    source = inspect.getsource(signal_gate)
    tree = ast.parse(source)
    forbidden_modules = {
        "anthropic", "openai", "httpx", "requests", "aiohttp", "socket",
        "subprocess", "pathlib", "random", "secrets", "uuid",
    }
    forbidden_calls = {
        "ProductionSignal", "publish", "send", "place_order", "cancel_order",
        "open_position", "close_position",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] not in forbidden_modules for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden_modules
        elif isinstance(node, ast.Call):
            target = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            assert target not in forbidden_calls


def test_errors_are_bounded_and_sanitized():
    secret = "sk-test-secret authorization header /tmp/article-body market price"
    with pytest.raises(signal_gate.SignalGateError) as caught:
        signal_gate.evaluate_signal_gate(secret, _policy())
    assert secret not in str(caught.value)
    assert len(str(caught.value)) < 200
