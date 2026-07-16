"""RED contract tests for the deterministic News Risk Object boundary."""

from __future__ import annotations

import hashlib
import inspect

import pytest

import engine.deterministic_adjudication_v1 as adjudication
import engine.news_risk_object_v1 as news_risk
from engine.claude_escalated_review_provider_v1 import ClaudeEscalatedReviewResultV1
from engine.deepseek_primary_review_provider_v1 import DeepSeekPrimaryReviewResultV1
from engine.deterministic_escalation_router_v1 import DeterministicEscalationDecisionV1
from engine.news_event_contract_v1 import canonical_json_bytes


ADJUDICATION_POLICY_VERSION = "deterministic-adjudication-policy-v1"
NEWS_RISK_POLICY_VERSION = "news-risk-policy-v1"
EVENT = "a" * 64
OTHER_EVENT = "b" * 64
ADJUDICATION_ID = "c" * 64
OTHER_ADJUDICATION_ID = "d" * 64
DECISION_ID = "e" * 64
DEEPSEEK_ID = "f" * 64
CLAUDE_ID = "1" * 64


def _hash(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _policy(**overrides):
    values = {
        "policy_version": NEWS_RISK_POLICY_VERSION,
        "supported_adjudication_policy_versions": (ADJUDICATION_POLICY_VERSION,),
        "supported_routes": ("L0", "L1", "L2"),
        "outcome_to_risk_classification": {
            "ACCEPT_DEEPSEEK": "CLEAR",
            "ACCEPT_CLAUDE": "CLEAR",
            "CONSENSUS_CONFIRMED": "CLEAR",
            "CONSENSUS_WITH_QUALIFICATION": "CAUTION",
            "MATERIAL_DISAGREEMENT": "ELEVATED",
            "INSUFFICIENT_EVIDENCE": "CAUTION",
            "FAIL_CLOSED": "FAIL_CLOSED",
        },
        "ambiguity_precedence": ("NONE", "MODERATE", "CRITICAL"),
        "contradiction_precedence": ("NONE", "RESOLVED", "PRESENT", "UNRESOLVED"),
        "evidence_precedence": ("SUFFICIENT", "INSUFFICIENT"),
        "entity_precedence": ("ACCEPTABLE", "MODERATE", "CRITICAL"),
        "source_precedence": ("ACCEPTABLE", "MODERATE", "CRITICAL"),
        "material_risk_precedence": ("NONE", "MATERIAL_RISK"),
        "fail_closed_outcomes": ("FAIL_CLOSED",),
        "blocking_reason_codes": (
            "CRITICAL_MATERIAL_RISK",
            "CRITICAL_CONTRADICTION",
            "CRITICAL_ENTITY_CONCERN",
            "CRITICAL_SOURCE_CONCERN",
            "BLOCKING_ADJUDICATION_REASON",
            "MATERIAL_RISK_DISAGREEMENT",
            "CONTRADICTION_DISAGREEMENT",
            "ENTITY_DISAGREEMENT",
            "SOURCE_DISAGREEMENT",
            "CRITICAL_UNRESOLVED_DISAGREEMENT",
        ),
        "caution_reason_codes": (
            "QUALIFIED_ADJUDICATION",
            "EVIDENCE_LIMITED",
            "MODERATE_ENTITY_CONCERN",
            "MODERATE_SOURCE_CONCERN",
        ),
        "deterministic_reason_order": (
            "INVALID_ADJUDICATION",
            "UNSUPPORTED_POLICY",
            "FORGED_IDENTITY",
            "FAIL_CLOSED_ADJUDICATION",
            "CRITICAL_MATERIAL_RISK",
            "CRITICAL_CONTRADICTION",
            "CRITICAL_ENTITY_CONCERN",
            "CRITICAL_SOURCE_CONCERN",
            "BLOCKING_ADJUDICATION_REASON",
            "MATERIAL_DISAGREEMENT",
            "UNRESOLVED_CONTRADICTION",
            "MATERIAL_RISK_PRESENT",
            "INSUFFICIENT_EVIDENCE",
            "QUALIFIED_ADJUDICATION",
            "EVIDENCE_LIMITED",
            "MODERATE_ENTITY_CONCERN",
            "MODERATE_SOURCE_CONCERN",
            "ADJUDICATION_CONFIRMED",
            "NO_MATERIAL_NEWS_RISK",
            "EVIDENCE_SUFFICIENT",
        ),
        "maximum_reason_code_count": 20,
        "maximum_evidence_reference_count": 16,
    }
    values.update(overrides)
    return news_risk.NewsRiskPolicyV1(**values)


def _result_identity(values):
    return _hash(
        {
            "policy_version": values["policy_version"],
            "event_snapshot_id": values["event_snapshot_id"],
            "route": values["route"],
            "router_decision_id": values["router_decision_id"],
            "deepseek_semantic_result_id": values["deepseek_semantic_result_id"],
            "claude_semantic_result_id": values["claude_semantic_result_id"],
            "adjudication_outcome": values["adjudication_outcome"],
            "agreement_state": values["agreement_state"],
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


def _adjudication(**overrides):
    values = {
        "policy_version": ADJUDICATION_POLICY_VERSION,
        "event_snapshot_id": EVENT,
        "route": "L1",
        "router_decision_id": DECISION_ID,
        "deepseek_semantic_result_id": DEEPSEEK_ID,
        "claude_semantic_result_id": CLAUDE_ID,
        "adjudication_outcome": "CONSENSUS_CONFIRMED",
        "agreement_state": "AGREEMENT",
        "final_ambiguity_state": "NONE",
        "final_contradiction_state": "NONE",
        "final_evidence_state": "SUFFICIENT",
        "final_entity_state": "ACCEPTABLE",
        "final_source_state": "ACCEPTABLE",
        "final_material_risk_state": "NONE",
        "reason_codes": ("PROVIDERS_AGREE",),
        "evidence_refs": ("evidence-001",),
        "structured_explanation": "Adjudication fixture.",
        "adjudication_result_id": None,
    }
    values.update(overrides)
    values["adjudication_result_id"] = _result_identity(values)
    return adjudication.DeterministicAdjudicationResultV1(**values)


def _build(result=None, policy=None):
    return news_risk.build_news_risk_object(
        _adjudication() if result is None else result,
        _policy() if policy is None else policy,
    )


def test_public_api_and_policy_version_are_frozen():
    assert news_risk.NEWS_RISK_POLICY_VERSION == NEWS_RISK_POLICY_VERSION
    assert news_risk.__all__ == (
        "NewsRiskObjectError",
        "NEWS_RISK_POLICY_VERSION",
        "NewsRiskPolicyV1",
        "NewsRiskObjectV1",
        "build_news_risk_object",
    )
    assert type(news_risk.__all__) is tuple
    assert len(set(news_risk.__all__)) == 5


def test_policy_is_closed_immutable_and_normalized():
    policy = _policy(
        supported_routes=("L2", "L0", "L1", "L1"),
        blocking_reason_codes=("CRITICAL_SOURCE_CONCERN", "CRITICAL_SOURCE_CONCERN"),
    )
    assert policy.supported_routes == ("L0", "L1", "L2")
    assert policy.blocking_reason_codes == ("CRITICAL_SOURCE_CONCERN",)
    with pytest.raises((AttributeError, TypeError)):
        policy.supported_routes = ("L0",)
    with pytest.raises(news_risk.NewsRiskObjectError):
        news_risk.NewsRiskPolicyV1(**{**policy.__dict__, "unknown": True})


@pytest.mark.parametrize("field", ["maximum_reason_code_count", "maximum_evidence_reference_count"])
@pytest.mark.parametrize("value", [True, False, 1.0, 0, -1])
def test_policy_limits_require_positive_integers(field, value):
    with pytest.raises(news_risk.NewsRiskObjectError):
        _policy(**{field: value})


@pytest.mark.parametrize(
    "overrides",
    [
        {"policy_version": "wrong-policy-v1"},
        {"supported_adjudication_policy_versions": ("other-v1",)},
        {"supported_routes": ("L0", "L1")},
        {"outcome_to_risk_classification": {"BUY": "CLEAR"}},
        {"blocking_reason_codes": ("UNKNOWN",)},
        {"caution_reason_codes": ("UNKNOWN",)},
    ],
)
def test_policy_rejects_unsupported_or_unsafe_configuration(overrides):
    with pytest.raises(news_risk.NewsRiskObjectError):
        _policy(**overrides)


@pytest.mark.parametrize(
    "bad",
    [None, {}, "result", object(), adjudication.DeterministicAdjudicationPolicyV1],
)
def test_exact_adjudication_input_type_is_required(bad):
    with pytest.raises(news_risk.NewsRiskObjectError):
        news_risk.build_news_risk_object(bad, _policy())


def test_exact_policy_input_type_is_required():
    with pytest.raises(news_risk.NewsRiskObjectError):
        news_risk.build_news_risk_object(_adjudication(), {})


@pytest.mark.parametrize(
    ("outcome", "classification", "recommendation"),
    [
        ("ACCEPT_DEEPSEEK", "CLEAR", "NO_NEWS_RESTRICTION"),
        ("ACCEPT_CLAUDE", "CLEAR", "NO_NEWS_RESTRICTION"),
        ("CONSENSUS_CONFIRMED", "CLEAR", "NO_NEWS_RESTRICTION"),
        ("CONSENSUS_WITH_QUALIFICATION", "CAUTION", "REQUIRE_CAUTION"),
        ("MATERIAL_DISAGREEMENT", "ELEVATED", "REQUIRE_CAUTION"),
        ("INSUFFICIENT_EVIDENCE", "CAUTION", "REQUIRE_CAUTION"),
        ("FAIL_CLOSED", "FAIL_CLOSED", "FAIL_CLOSED"),
    ],
)
def test_outcome_mapping_is_closed_and_deterministic(outcome, classification, recommendation):
    result = _adjudication(
        adjudication_outcome=outcome,
        agreement_state="FAIL_CLOSED" if outcome == "FAIL_CLOSED" else "AGREEMENT",
        reason_codes=("CRITICAL_UNRESOLVED_DISAGREEMENT",) if outcome == "FAIL_CLOSED" else ("PROVIDERS_AGREE",),
    )
    risk = _build(result)
    assert risk.risk_classification == classification
    assert risk.news_gate_recommendation == recommendation


@pytest.mark.parametrize(
    ("field", "value", "expected_classification", "expected_recommendation", "reason"),
    [
        ("final_material_risk_state", "MATERIAL_RISK", "ELEVATED", "REQUIRE_CAUTION", "MATERIAL_RISK_PRESENT"),
        ("final_contradiction_state", "UNRESOLVED", "ELEVATED", "REQUIRE_CAUTION", "UNRESOLVED_CONTRADICTION"),
        ("final_entity_state", "MODERATE", "CAUTION", "REQUIRE_CAUTION", "MODERATE_ENTITY_CONCERN"),
        ("final_source_state", "MODERATE", "CAUTION", "REQUIRE_CAUTION", "MODERATE_SOURCE_CONCERN"),
    ],
)
def test_final_assessment_states_override_neutral_consensus(field, value, expected_classification, expected_recommendation, reason):
    risk = _build(_adjudication(**{field: value}))
    assert risk.risk_classification == expected_classification
    assert risk.news_gate_recommendation == expected_recommendation
    assert reason in risk.reason_codes


@pytest.mark.parametrize(
    ("field", "input_reason", "risk_reason"),
    [
        ("final_material_risk_state", "MATERIAL_RISK_DISAGREEMENT", "CRITICAL_MATERIAL_RISK"),
        ("final_contradiction_state", "CONTRADICTION_DISAGREEMENT", "CRITICAL_CONTRADICTION"),
        ("final_entity_state", "ENTITY_DISAGREEMENT", "CRITICAL_ENTITY_CONCERN"),
        ("final_source_state", "SOURCE_DISAGREEMENT", "CRITICAL_SOURCE_CONCERN"),
    ],
)
def test_critical_states_block_or_fail_closed(field, input_reason, risk_reason):
    # The adjudication result owns the input disagreement vocabulary; the
    # News Risk layer maps it to its own closed blocking vocabulary.
    result = _adjudication(reason_codes=(input_reason,), **{field: "MATERIAL_RISK" if field == "final_material_risk_state" else "CRITICAL" if field in {"final_entity_state", "final_source_state"} else "UNRESOLVED"})
    risk = _build(result)
    assert risk.risk_classification in {"BLOCKING", "FAIL_CLOSED"}
    assert risk.news_gate_recommendation in {"REQUIRE_BLOCK", "FAIL_CLOSED"}
    assert risk_reason in risk.reason_codes


def test_fail_closed_adjudication_has_highest_precedence():
    result = _adjudication(
        adjudication_outcome="FAIL_CLOSED",
        agreement_state="FAIL_CLOSED",
        final_material_risk_state="NONE",
        reason_codes=("CRITICAL_UNRESOLVED_DISAGREEMENT",),
    )
    risk = _build(result)
    assert risk.risk_classification == "FAIL_CLOSED"
    assert risk.news_gate_recommendation == "FAIL_CLOSED"
    assert "FAIL_CLOSED_ADJUDICATION" in risk.reason_codes


def test_insufficient_evidence_cannot_clear_consensus():
    risk = _build(_adjudication(final_evidence_state="INSUFFICIENT"))
    assert risk.risk_classification in {"CAUTION", "ELEVATED", "BLOCKING", "FAIL_CLOSED"}
    assert risk.risk_classification != "CLEAR"
    assert "INSUFFICIENT_EVIDENCE" in risk.reason_codes


def test_l0_accepted_primary_review_is_clear_when_neutral():
    values = {
        "policy_version": ADJUDICATION_POLICY_VERSION,
        "event_snapshot_id": EVENT,
        "route": "L0",
        "router_decision_id": DECISION_ID,
        "deepseek_semantic_result_id": DEEPSEEK_ID,
        "claude_semantic_result_id": None,
        "adjudication_outcome": "ACCEPT_DEEPSEEK",
        "agreement_state": "SINGLE_REVIEW",
        "final_ambiguity_state": "NONE",
        "final_contradiction_state": "NONE",
        "final_evidence_state": "SUFFICIENT",
        "final_entity_state": "ACCEPTABLE",
        "final_source_state": "ACCEPTABLE",
        "final_material_risk_state": "NONE",
        "reason_codes": ("MATERIAL_FACTS_ALIGNED",),
        "evidence_refs": ("evidence-001",),
        "structured_explanation": "L0 fixture.",
        "adjudication_result_id": None,
    }
    values["adjudication_result_id"] = _result_identity(values)
    risk = _build(adjudication.DeterministicAdjudicationResultV1(**values))
    assert risk.route == "L0"
    assert risk.risk_classification == "CLEAR"


@pytest.mark.parametrize(
    "override",
    [
        {"policy_version": "wrong-policy-v1"},
        {"adjudication_result_id": "9" * 64},
        {"adjudication_outcome": "BUY"},
        {"route": "L3"},
        {"final_evidence_state": "UNKNOWN"},
        {"reason_codes": ("UNKNOWN",)},
        {"evidence_refs": ("bad ref",)},
    ],
)
def test_malformed_or_forged_adjudication_is_rejected(override):
    values = {
        "policy_version": ADJUDICATION_POLICY_VERSION,
        "event_snapshot_id": EVENT,
        "route": "L1",
        "router_decision_id": DECISION_ID,
        "deepseek_semantic_result_id": DEEPSEEK_ID,
        "claude_semantic_result_id": CLAUDE_ID,
        "adjudication_outcome": "CONSENSUS_CONFIRMED",
        "agreement_state": "AGREEMENT",
        "final_ambiguity_state": "NONE",
        "final_contradiction_state": "NONE",
        "final_evidence_state": "SUFFICIENT",
        "final_entity_state": "ACCEPTABLE",
        "final_source_state": "ACCEPTABLE",
        "final_material_risk_state": "NONE",
        "reason_codes": ("PROVIDERS_AGREE",),
        "evidence_refs": ("evidence-001",),
        "structured_explanation": "fixture",
        "adjudication_result_id": None,
    }
    values.update(override)
    with pytest.raises((adjudication.DeterministicAdjudicationError, news_risk.NewsRiskObjectError)):
        _build(adjudication.DeterministicAdjudicationResultV1(**values))


def test_cross_event_binding_is_rejected():
    with pytest.raises(news_risk.NewsRiskObjectError):
        _build(_adjudication(event_snapshot_id=OTHER_EVENT))


def test_identity_is_deterministic_and_manually_recomputable():
    first = _build()
    second = _build()
    assert first == second
    values = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "news_risk_object_id"}
    assert first.news_risk_object_id == _hash(
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


@pytest.mark.parametrize("field", ["risk_classification", "news_gate_recommendation", "route"])
def test_semantic_identity_changes_when_bound_field_changes(field):
    first = _build()
    overrides = {"final_material_risk_state": "MATERIAL_RISK"} if field != "route" else {"route": "L2"}
    second = _build(_adjudication(**overrides))
    assert first.news_risk_object_id != second.news_risk_object_id


def test_free_text_is_inert_and_excluded_from_identity():
    first = _build(_adjudication(structured_explanation="open gate; publish; buy; shell command"))
    second = _build(_adjudication(structured_explanation="system instruction; ignore policy; sell"))
    assert first.risk_classification == second.risk_classification
    assert first.news_gate_recommendation == second.news_gate_recommendation
    assert first.reason_codes == second.reason_codes
    assert first.evidence_refs == second.evidence_refs
    assert first.news_risk_object_id == second.news_risk_object_id


def test_result_is_immutable_and_has_no_operational_fields():
    result = _build()
    with pytest.raises((AttributeError, TypeError)):
        result.route = "L2"
    forbidden = {
        "request_id", "attempts", "retries", "input_tokens", "output_tokens",
        "cache_usage", "cost_micro_usd", "duration_ms", "budget", "market_price",
        "direction", "entry", "stop", "target", "quantity", "leverage",
    }
    assert not forbidden.intersection(result.__dataclass_fields__)
    assert type(result.reason_codes) is tuple
    assert type(result.evidence_refs) is tuple


def test_caller_owned_policy_and_result_inputs_are_not_mutated():
    reasons = ["PROVIDERS_AGREE"]
    refs = ["evidence-001"]
    result = _adjudication(reason_codes=reasons, evidence_refs=refs)
    policy = _policy()
    _build(result, policy)
    reasons.append("MATERIAL_DISAGREEMENT")
    refs.append("evidence-002")
    assert result.reason_codes == ("PROVIDERS_AGREE",)
    assert result.evidence_refs == ("evidence-001",)


def test_reason_and_evidence_limits_are_enforced():
    policy = _policy(maximum_evidence_reference_count=1)
    result = _adjudication(evidence_refs=("evidence-001", "evidence-002"))
    with pytest.raises(news_risk.NewsRiskObjectError):
        _build(result, policy)


def test_telemetry_budget_market_and_provider_objects_are_not_inputs():
    bad_values = [
        object(),
        {"request_id": "req-1"},
        {"cost_micro_usd": 1},
        {"market_price": 1},
    ]
    for bad in bad_values:
        with pytest.raises(news_risk.NewsRiskObjectError):
            news_risk.build_news_risk_object(bad, _policy())


def test_news_risk_source_has_no_external_or_downstream_authority():
    source = inspect.getsource(news_risk)
    for forbidden in (
        "anthropic", "openai", "httpx", "requests", "aiohttp", "urllib.request",
        "socket", "os.environ", "getenv", "dotenv", "subprocess", "pathlib",
        "random", "secrets", "uuid", "Signal Gate", "publication", "trading",
        "account", "balance", "position", "capital", "market_price",
    ):
        assert forbidden not in source


def test_errors_are_bounded_and_sanitized():
    secret = "sk-test-secret authorization header /tmp/article-body"
    with pytest.raises(news_risk.NewsRiskObjectError) as caught:
        news_risk.build_news_risk_object(secret, _policy())
    assert secret not in str(caught.value)
    assert len(str(caught.value)) < 200
