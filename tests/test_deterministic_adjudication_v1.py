"""RED contract tests for deterministic semantic adjudication."""

from __future__ import annotations

import hashlib
import inspect
from itertools import permutations

import pytest

import engine.deterministic_adjudication_v1 as adjudication
from engine.ai_review_payload_projector_v1 import (
    ClaudeReviewPayloadV1,
    DeepSeekReviewPayloadV1,
)
from engine.claude_escalated_review_provider_v1 import (
    ClaudeEscalatedReviewResultV1,
    ClaudeEscalatedReviewRunV1,
    ClaudeProviderExecutionRecordV1,
)
from engine.deepseek_primary_review_provider_v1 import (
    DeepSeekPrimaryReviewResultV1,
    DeepSeekPrimaryReviewRunV1,
    DeepSeekProviderExecutionRecordV1,
)
from engine.deterministic_escalation_router_v1 import (
    DeterministicEscalationDecisionV1,
)
from engine.news_event_contract_v1 import canonical_json_bytes


POLICY_VERSION = "deterministic-adjudication-policy-v1"
EVENT_SNAPSHOT_ID = "a" * 64
OTHER_SNAPSHOT_ID = "b" * 64
DEEPSEEK_RESULT_ID = "c" * 64
DEEPSEEK_PAYLOAD_SHA256 = "d" * 64
CLAUDE_RESULT_ID = "e" * 64
CLAUDE_PAYLOAD_SHA256 = "f" * 64
DECISION_ID = "1" * 64
LOGICAL_REVIEW_ID = "2" * 64
L1_POLICY_ID = "fictional-claude-sonnet-policy-v1"
L2_POLICY_ID = "fictional-claude-opus-policy-v1"


def _hash(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _set_fields(cls, values):
    instance = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(instance, name, value)
    return instance


def _policy(**overrides):
    values = {
        "policy_version": POLICY_VERSION,
        "supported_routes": ("L0", "L1", "L2"),
        "agreement_values": (
            "SINGLE_REVIEW",
            "AGREEMENT",
            "QUALIFIED_AGREEMENT",
            "DISAGREEMENT",
            "CRITICAL_DISAGREEMENT",
            "FAIL_CLOSED",
        ),
        "contradiction_values": ("NONE", "PRESENT", "RESOLVED", "UNRESOLVED"),
        "evidence_precedence": ("SUFFICIENT", "INSUFFICIENT"),
        "entity_precedence": ("ACCEPTABLE", "MODERATE", "CRITICAL"),
        "source_precedence": ("ACCEPTABLE", "MODERATE", "CRITICAL"),
        "material_risk_precedence": ("NONE", "MATERIAL_RISK"),
        "critical_disagreement_rules": (
            "CRITICAL_UNRESOLVED_DISAGREEMENT",
        ),
        "fail_closed_reason_codes": (
            "INVALID_INPUT",
            "RESULT_NOT_COMPLETED",
            "ROUTE_RESULT_MISMATCH",
            "EVENT_BINDING_MISMATCH",
            "DECISION_BINDING_MISMATCH",
            "POLICY_MISMATCH",
            "CRITICAL_UNRESOLVED_DISAGREEMENT",
        ),
        "deterministic_reason_order": (
            "MATERIAL_RISK_DISAGREEMENT",
            "CONTRADICTION_DISAGREEMENT",
            "ENTITY_DISAGREEMENT",
            "SOURCE_DISAGREEMENT",
            "EVIDENCE_DISAGREEMENT",
            "PROVIDERS_AGREE",
            "MATERIAL_FACTS_ALIGNED",
            "RISK_ASSESSMENTS_ALIGNED",
            "MINOR_EVIDENCE_DIFFERENCE",
            "MODERATE_ENTITY_DIFFERENCE",
            "MODERATE_SOURCE_DIFFERENCE",
            "CRITICAL_UNRESOLVED_DISAGREEMENT",
        ),
        "maximum_reason_code_count": 12,
        "maximum_evidence_reference_count": 16,
    }
    values.update(overrides)
    return adjudication.DeterministicAdjudicationPolicyV1(**values)


def _deepseek(**overrides):
    values = {
        "policy_version": "deepseek-primary-review-policy-v1",
        "event_snapshot_id": EVENT_SNAPSHOT_ID,
        "request_payload_sha256": DEEPSEEK_PAYLOAD_SHA256,
        "logical_review_id": LOGICAL_REVIEW_ID,
        "review_status": "COMPLETED",
        "review_conclusion": "FACTUAL_REVIEW_COMPLETE",
        "ambiguity_level": "NONE",
        "contradiction_present": False,
        "evidence_sufficiency": "SUFFICIENT",
        "entity_confidence_state": "EXPLICIT",
        "source_policy_concern_state": "NONE",
        "material_risk_flags": ("NONE",),
        "reason_codes": ("REVIEW_COMPLETED",),
        "structured_explanation": "DeepSeek fixture explanation.",
        "escalation_evidence_refs": ("evidence-001",),
        "semantic_result_id": DEEPSEEK_RESULT_ID,
    }
    values.update(overrides)
    return _set_fields(DeepSeekPrimaryReviewResultV1, values)


def _decision(route="L1", **overrides):
    model = L1_POLICY_ID if route == "L1" else L2_POLICY_ID
    values = {
        "policy_version": "deterministic-escalation-router-policy-v1",
        "event_snapshot_id": EVENT_SNAPSHOT_ID,
        "deepseek_semantic_result_id": DEEPSEEK_RESULT_ID,
        "deepseek_payload_sha256": DEEPSEEK_PAYLOAD_SHA256,
        "route": route,
        "route_name": {
            "L0": "CLEAN_OR_ROUTINE",
            "L1": "MODERATE_AMBIGUITY",
            "L2": "CRITICAL_AMBIGUITY",
        }[route],
        "claude_review_required": route != "L0",
        "claude_model_policy_id": None if route == "L0" else model,
        "reason_codes": ("ROUTINE_COMPLETE",) if route == "L0" else ("MODERATE_AMBIGUITY",),
        "escalation_evidence_refs": ("evidence-001",),
        "decision_id": DECISION_ID,
    }
    values.update(overrides)
    return _set_fields(DeterministicEscalationDecisionV1, values)


def _claude(route="L1", **overrides):
    model = L1_POLICY_ID if route == "L1" else L2_POLICY_ID
    values = {
        "policy_version": "claude-escalated-review-policy-v1",
        "event_snapshot_id": EVENT_SNAPSHOT_ID,
        "request_payload_sha256": CLAUDE_PAYLOAD_SHA256,
        "router_decision_id": DECISION_ID,
        "logical_review_id": LOGICAL_REVIEW_ID,
        "route": route,
        "model_policy_id": model,
        "review_status": "COMPLETED",
        "review_conclusion": "ESCALATED_REVIEW_COMPLETE",
        "ambiguity_resolution": "RESOLVED",
        "contradiction_resolution": "NONE",
        "evidence_assessment": "SUFFICIENT",
        "entity_assessment": "ACCEPTABLE",
        "source_assessment": "ACCEPTABLE",
        "material_risk_assessment": "NONE",
        "agreement_state_with_deepseek": "AGREES",
        "reason_codes": ("CLAUDE_REVIEW_COMPLETED",),
        "structured_explanation": "Claude fixture explanation.",
        "adjudication_evidence_refs": ("evidence-001",),
        "semantic_result_id": CLAUDE_RESULT_ID,
    }
    values.update(overrides)
    return _set_fields(ClaudeEscalatedReviewResultV1, values)


_AUTO_CLAUDE = object()


def _adjudicate(deepseek=None, decision=None, claude=_AUTO_CLAUDE, policy=None):
    selected_decision = _decision("L1") if decision is None else decision
    selected_claude = (
        None
        if claude is _AUTO_CLAUDE and selected_decision.route == "L0"
        else _claude(selected_decision.route)
        if claude is _AUTO_CLAUDE
        else claude
    )
    return adjudication.adjudicate_review_results(
        _deepseek() if deepseek is None else deepseek,
        selected_decision,
        selected_claude,
        _policy() if policy is None else policy,
    )


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


def test_public_api_and_policy_version_are_frozen():
    assert adjudication.DETERMINISTIC_ADJUDICATION_POLICY_VERSION == POLICY_VERSION
    assert adjudication.__all__ == (
        "DeterministicAdjudicationError",
        "DETERMINISTIC_ADJUDICATION_POLICY_VERSION",
        "DeterministicAdjudicationPolicyV1",
        "DeterministicAdjudicationResultV1",
        "adjudicate_review_results",
    )
    assert type(adjudication.__all__) is tuple
    assert len(set(adjudication.__all__)) == 5


def test_policy_is_closed_immutable_and_deterministically_normalized():
    policy = _policy(
        supported_routes=("L2", "L0", "L1", "L1"),
        agreement_values=("FAIL_CLOSED", "AGREEMENT", "AGREEMENT"),
    )
    assert policy.supported_routes == ("L0", "L1", "L2")
    assert policy.agreement_values == ("AGREEMENT", "FAIL_CLOSED")
    with pytest.raises((AttributeError, TypeError)):
        policy.supported_routes = ("L0",)
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        adjudication.DeterministicAdjudicationPolicyV1(
            **{**policy.__dict__, "unknown": True}
        )


@pytest.mark.parametrize("field", ["maximum_reason_code_count", "maximum_evidence_reference_count"])
@pytest.mark.parametrize("value", [True, False, 1.0, 0, -1])
def test_policy_limits_require_positive_integers(field, value):
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        _policy(**{field: value})


@pytest.mark.parametrize(
    "overrides",
    [
        {"supported_routes": ("L0", "L1")},
        {"agreement_values": ("UNKNOWN",)},
        {"fail_closed_reason_codes": ("UNKNOWN",)},
        {"deterministic_reason_order": ("UNKNOWN",)},
    ],
)
def test_policy_rejects_unsupported_or_contradictory_configuration(overrides):
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        _policy(**overrides)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        "result",
        DeepSeekReviewPayloadV1,
        DeepSeekPrimaryReviewRunV1,
        DeepSeekProviderExecutionRecordV1,
        ClaudeReviewPayloadV1,
        ClaudeEscalatedReviewRunV1,
        ClaudeProviderExecutionRecordV1,
    ],
)
def test_exact_input_types_are_required(bad):
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        adjudication.adjudicate_review_results(bad, _decision(), _claude(), _policy())


def test_l0_accepts_deepseek_without_claude():
    result = _adjudicate(
        deepseek=_deepseek(),
        decision=_decision("L0"),
        claude=None,
    )
    assert result.route == "L0"
    assert result.adjudication_outcome == "ACCEPT_DEEPSEEK"
    assert result.agreement_state == "SINGLE_REVIEW"
    assert result.claude_semantic_result_id is None
    assert result.event_snapshot_id == EVENT_SNAPSHOT_ID
    assert result.router_decision_id == DECISION_ID
    assert result.deepseek_semantic_result_id == DEEPSEEK_RESULT_ID


def test_l0_rejects_supplied_claude_result():
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        _adjudicate(decision=_decision("L0"), claude=_claude("L1"))


@pytest.mark.parametrize("route", ["L1", "L2"])
def test_escalated_routes_require_claude(route):
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        _adjudicate(decision=_decision(route), claude=None)


@pytest.mark.parametrize("route", ["L1", "L2"])
def test_aligned_escalated_results_produce_consensus(route):
    result = _adjudicate(
        decision=_decision(route),
        claude=_claude(route),
    )
    assert result.route == route
    assert result.adjudication_outcome == "CONSENSUS_CONFIRMED"
    assert result.agreement_state == "AGREEMENT"
    assert result.claude_semantic_result_id == CLAUDE_RESULT_ID


def test_l1_qualified_evidence_difference_is_explicit():
    result = _adjudicate(
        deepseek=_deepseek(evidence_sufficiency="INSUFFICIENT"),
        claude=_claude(evidence_assessment="SUFFICIENT"),
    )
    assert result.adjudication_outcome == "CONSENSUS_WITH_QUALIFICATION"
    assert result.agreement_state == "QUALIFIED_AGREEMENT"
    assert "MINOR_EVIDENCE_DIFFERENCE" in result.reason_codes


def test_l1_qualified_entity_and_source_differences_are_order_invariant():
    first = _adjudicate(
        deepseek=_deepseek(entity_confidence_state="EXPLICIT"),
        claude=_claude(entity_assessment="MODERATE", source_assessment="MODERATE"),
    )
    second = _adjudicate(
        deepseek=_deepseek(entity_confidence_state="EXPLICIT"),
        claude=_claude(source_assessment="MODERATE", entity_assessment="MODERATE"),
    )
    assert first.adjudication_outcome == "CONSENSUS_WITH_QUALIFICATION"
    assert first.reason_codes == second.reason_codes
    assert first.adjudication_result_id == second.adjudication_result_id


@pytest.mark.parametrize(
    ("deepseek_overrides", "claude_overrides", "reason"),
    [
        ({"material_risk_flags": ("MATERIAL_RISK",)}, {"material_risk_assessment": "NONE"}, "MATERIAL_RISK_DISAGREEMENT"),
        ({"contradiction_present": True}, {"contradiction_resolution": "RESOLVED"}, "CONTRADICTION_DISAGREEMENT"),
        ({"entity_confidence_state": "CRITICAL"}, {"entity_assessment": "ACCEPTABLE"}, "ENTITY_DISAGREEMENT"),
        ({"source_policy_concern_state": "CRITICAL"}, {"source_assessment": "ACCEPTABLE"}, "SOURCE_DISAGREEMENT"),
    ],
)
def test_critical_disagreement_is_not_silently_consensus(deepseek_overrides, claude_overrides, reason):
    result = _adjudicate(
        deepseek=_deepseek(**deepseek_overrides),
        claude=_claude(**claude_overrides),
    )
    assert result.adjudication_outcome in {"MATERIAL_DISAGREEMENT", "FAIL_CLOSED"}
    assert result.agreement_state in {"CRITICAL_DISAGREEMENT", "FAIL_CLOSED"}
    assert reason in result.reason_codes


def test_insufficient_evidence_has_precedence_over_otherwise_aligned_facts():
    result = _adjudicate(
        deepseek=_deepseek(evidence_sufficiency="INSUFFICIENT"),
        claude=_claude(evidence_assessment="INSUFFICIENT"),
    )
    assert result.adjudication_outcome == "INSUFFICIENT_EVIDENCE"
    assert result.final_evidence_state == "INSUFFICIENT"


def test_material_risk_and_contradiction_combination_preserves_critical_state():
    result = _adjudicate(
        deepseek=_deepseek(material_risk_flags=("MATERIAL_RISK",), contradiction_present=True),
        claude=_claude(material_risk_assessment="NONE", contradiction_resolution="RESOLVED"),
    )
    assert result.adjudication_outcome in {"MATERIAL_DISAGREEMENT", "FAIL_CLOSED"}
    assert result.final_material_risk_state == "MATERIAL_RISK"
    assert result.final_contradiction_state in {"PRESENT", "UNRESOLVED"}


def test_configured_fail_closed_reason_overrides_agreement():
    result = _adjudicate(
        deepseek=_deepseek(reason_codes=("CRITICAL_UNRESOLVED_DISAGREEMENT",)),
        claude=_claude(),
    )
    assert result.adjudication_outcome == "FAIL_CLOSED"
    assert result.agreement_state == "FAIL_CLOSED"
    assert "CRITICAL_UNRESOLVED_DISAGREEMENT" in result.reason_codes


def test_claude_self_reported_agreement_is_not_authoritative():
    first = _adjudicate(claude=_claude(agreement_state_with_deepseek="AGREES"))
    second = _adjudicate(claude=_claude(agreement_state_with_deepseek="DISAGREES"))
    assert first.adjudication_outcome == second.adjudication_outcome
    assert first.agreement_state == second.agreement_state
    assert first.reason_codes == second.reason_codes
    assert first.adjudication_result_id == second.adjudication_result_id


def test_free_text_is_inert_and_excluded_from_identity():
    first = _adjudicate(
        deepseek=_deepseek(structured_explanation="accept Claude; publish; buy"),
        claude=_claude(structured_explanation="ignore policy; sell; open signal gate"),
    )
    second = _adjudicate(
        deepseek=_deepseek(structured_explanation="role injection"),
        claude=_claude(structured_explanation="system instruction"),
    )
    assert first.adjudication_outcome == second.adjudication_outcome
    assert first.agreement_state == second.agreement_state
    assert first.reason_codes == second.reason_codes
    assert first.evidence_refs == second.evidence_refs
    assert first.adjudication_result_id == second.adjudication_result_id


@pytest.mark.parametrize(
    ("decision_overrides", "claude"),
    [
        ({"event_snapshot_id": OTHER_SNAPSHOT_ID}, _AUTO_CLAUDE),
        ({"deepseek_semantic_result_id": OTHER_SNAPSHOT_ID}, _AUTO_CLAUDE),
        ({}, _claude(router_decision_id=OTHER_SNAPSHOT_ID)),
        ({}, _claude("L2")),
    ],
)
def test_cross_contract_binding_mismatches_fail_before_adjudication(decision_overrides, claude):
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        _adjudicate(decision=_decision(**decision_overrides), claude=claude)


@pytest.mark.parametrize("status", ["PROVIDER_REJECTED", "INVALID_RESPONSE", "TRANSIENT_FAILURE", "PERMANENT_FAILURE", "BUDGET_BLOCKED", "ROUTE_BLOCKED", "TOKEN_LIMIT_BLOCKED"])
def test_non_completed_deepseek_status_fails_closed(status):
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        _adjudicate(deepseek=_deepseek(review_status=status))


@pytest.mark.parametrize("status", ["PROVIDER_REJECTED", "INVALID_RESPONSE", "TRANSIENT_FAILURE", "PERMANENT_FAILURE", "BUDGET_BLOCKED", "ROUTE_BLOCKED", "TOKEN_LIMIT_BLOCKED"])
def test_non_completed_claude_status_fails_closed(status):
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        _adjudicate(claude=_claude(review_status=status))


def test_payload_hashes_are_distinct_provider_identities():
    result = _adjudicate()
    assert DEEPSEEK_PAYLOAD_SHA256 != CLAUDE_PAYLOAD_SHA256
    assert result.deepseek_semantic_result_id == DEEPSEEK_RESULT_ID
    assert result.claude_semantic_result_id == CLAUDE_RESULT_ID


def test_reason_and_evidence_ordering_is_canonical():
    results = []
    for refs in permutations(("evidence-001", "evidence-002", "evidence-001")):
        results.append(
            _adjudicate(
                deepseek=_deepseek(escalation_evidence_refs=refs),
                claude=_claude(adjudication_evidence_refs=refs),
            )
        )
    assert {item.adjudication_result_id for item in results} == {results[0].adjudication_result_id}
    assert results[0].evidence_refs == tuple(sorted(set(results[0].evidence_refs)))


def test_result_is_immutable_and_telemetry_free():
    result = _adjudicate()
    with pytest.raises((AttributeError, TypeError)):
        result.route = "L2"
    assert not {"request_id", "attempt_number", "retry_count", "input_tokens", "output_tokens", "cost_micro_usd", "duration_ms"}.intersection(result.__dataclass_fields__)


def test_caller_owned_semantic_inputs_are_not_mutated():
    deepseek = _deepseek(material_risk_flags=["NONE"], reason_codes=["REVIEW_COMPLETED"], escalation_evidence_refs=["evidence-001"])
    claude = _claude(reason_codes=["CLAUDE_REVIEW_COMPLETED"], adjudication_evidence_refs=["evidence-001"])
    decision = _decision()
    _adjudicate(deepseek=deepseek, claude=claude, decision=decision)
    assert deepseek.material_risk_flags == ["NONE"]
    assert deepseek.reason_codes == ["REVIEW_COMPLETED"]
    assert claude.reason_codes == ["CLAUDE_REVIEW_COMPLETED"]
    assert decision.route == "L1"


def test_manual_result_identity_recomputation_uses_semantic_fields_only():
    result = _adjudicate()
    values = {name: getattr(result, name) for name in result.__dataclass_fields__ if name != "adjudication_result_id"}
    assert _result_identity(values) == result.adjudication_result_id


@pytest.mark.parametrize("field", ["request_id", "attempt_number", "retry_count", "input_tokens", "output_tokens", "cost_micro_usd", "duration_ms"])
def test_operational_fields_are_not_adjudication_inputs(field):
    result = _adjudicate()
    assert field not in result.__dataclass_fields__


def test_direct_result_construction_rejects_unknown_fields():
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        adjudication.DeterministicAdjudicationResultV1(unknown=True)


def test_direct_result_construction_rejects_forged_identity():
    with pytest.raises(adjudication.DeterministicAdjudicationError):
        adjudication.DeterministicAdjudicationResultV1(
            policy_version=POLICY_VERSION,
            event_snapshot_id=EVENT_SNAPSHOT_ID,
            route="L1",
            router_decision_id=DECISION_ID,
            deepseek_semantic_result_id=DEEPSEEK_RESULT_ID,
            claude_semantic_result_id=CLAUDE_RESULT_ID,
            adjudication_outcome="CONSENSUS_CONFIRMED",
            agreement_state="AGREEMENT",
            final_ambiguity_state="NONE",
            final_contradiction_state="NONE",
            final_evidence_state="SUFFICIENT",
            final_entity_state="ACCEPTABLE",
            final_source_state="ACCEPTABLE",
            final_material_risk_state="NONE",
            reason_codes=("PROVIDERS_AGREE",),
            evidence_refs=("evidence-001",),
            structured_explanation="bounded",
            adjudication_result_id="9" * 64,
        )


def test_provider_runs_and_records_are_not_semantic_inputs():
    for bad in (DeepSeekPrimaryReviewRunV1, DeepSeekProviderExecutionRecordV1, ClaudeEscalatedReviewRunV1, ClaudeProviderExecutionRecordV1):
        with pytest.raises(adjudication.DeterministicAdjudicationError):
            adjudication.adjudicate_review_results(bad, _decision(), _claude(), _policy())


def test_adjudicator_source_has_no_external_execution_authority():
    source = inspect.getsource(adjudication)
    for forbidden in (
        "anthropic",
        "openai",
        "httpx",
        "requests",
        "aiohttp",
        "urllib.request",
        "socket",
        "os.environ",
        "getenv",
        "dotenv",
        "subprocess",
        "pathlib",
        "random",
        "secrets",
        "uuid",
        "MasterEngine",
        "publication",
        "trading",
        "account",
        "capital",
    ):
        assert forbidden not in source


def test_errors_are_bounded_and_sanitized():
    secret = "sk-test-secret-value"
    with pytest.raises(adjudication.DeterministicAdjudicationError) as caught:
        adjudication.adjudicate_review_results(
            _deepseek(reason_codes=(secret,)),
            _decision(),
            _claude(structured_explanation=secret),
            _policy(),
        )
    assert secret not in str(caught.value)
    assert len(str(caught.value)) < 200
