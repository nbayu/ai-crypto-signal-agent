"""RED contract for additive Phase 11 finalization-evidence bridges.

The bridge binds explicitly supplied Phase 10 semantic evidence to immutable
Phase 11 provider-run evidence.  It never reconstructs semantic evidence from
generic hashes or invokes a provider boundary.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from engine.claude_escalated_review_provider_v1 import ClaudeEscalatedReviewResultV1
from engine.deepseek_primary_review_provider_v1 import DeepSeekPrimaryReviewResultV1
from engine.deterministic_escalation_router_v1 import (
    DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION,
    DeterministicEscalationDecisionV1,
)
from engine.phase_11_finalization_evidence_bridge_v1 import (
    ShadowAdjudicationEvidenceBundleV1,
    ShadowAdjudicationRouteLineageV1,
    ShadowFinalizationEvidenceBridgeValidationError,
    ShadowTerminalExecutionRecordV1,
    ShadowTypedProviderReviewEvidenceV1,
    ShadowTerminalRecordStatusV1,
    canonical_json_bytes,
    lowercase_sha256,
)


EVENT_ID = "a" * 64
PAYLOAD_HASH = "b" * 64
LOGICAL_REVIEW_ID = "c" * 64


def _sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _deepseek() -> DeepSeekPrimaryReviewResultV1:
    return DeepSeekPrimaryReviewResultV1(
        policy_version="deepseek-primary-review-policy-v1",
        event_snapshot_id=EVENT_ID,
        request_payload_sha256=PAYLOAD_HASH,
        logical_review_id=LOGICAL_REVIEW_ID,
        review_status="COMPLETED",
        review_conclusion="FACTUAL_REVIEW_COMPLETE",
        ambiguity_level="NONE",
        contradiction_present=False,
        evidence_sufficiency="SUFFICIENT",
        entity_confidence_state="EXPLICIT",
        source_policy_concern_state="NONE",
        material_risk_flags=("NONE",),
        reason_codes=("REVIEW_COMPLETED",),
        structured_explanation="synthetic bounded DeepSeek semantic review",
        escalation_evidence_refs=("evidence-001",),
        semantic_result_id=None,
    )


def _decision(deepseek: DeepSeekPrimaryReviewResultV1, route: str) -> DeterministicEscalationDecisionV1:
    model = "claude-sonnet-policy" if route == "L1" else "claude-opus-policy"
    reason = "MODERATE_AMBIGUITY" if route == "L1" else "CRITICAL_AMBIGUITY"
    name = "MODERATE_AMBIGUITY" if route == "L1" else "CRITICAL_AMBIGUITY"
    return DeterministicEscalationDecisionV1(
        policy_version=DETERMINISTIC_ESCALATION_ROUTER_POLICY_VERSION,
        event_snapshot_id=EVENT_ID,
        deepseek_semantic_result_id=deepseek.semantic_result_id,
        deepseek_payload_sha256=PAYLOAD_HASH,
        route=route,
        route_name=name,
        claude_review_required=True,
        claude_model_policy_id=model,
        reason_codes=(reason,),
        escalation_evidence_refs=("evidence-001",),
        decision_id=None,
    )


def _claude(decision: DeterministicEscalationDecisionV1) -> ClaudeEscalatedReviewResultV1:
    return ClaudeEscalatedReviewResultV1(
        policy_version="claude-escalated-review-policy-v1",
        event_snapshot_id=EVENT_ID,
        request_payload_sha256=PAYLOAD_HASH,
        router_decision_id=decision.decision_id,
        logical_review_id="d" * 64 if decision.route == "L1" else "e" * 64,
        route=decision.route,
        model_policy_id=decision.claude_model_policy_id,
        review_status="COMPLETED",
        review_conclusion="ESCALATED_REVIEW_COMPLETE",
        ambiguity_resolution="RESOLVED",
        contradiction_resolution="NONE",
        evidence_assessment="SUFFICIENT",
        entity_assessment="CONFIRMED",
        source_assessment="ACCEPTABLE",
        material_risk_assessment="NONE",
        agreement_state_with_deepseek="AGREES",
        reason_codes=("CLAUDE_REVIEW_COMPLETED",),
        structured_explanation="synthetic bounded Claude semantic review",
        adjudication_evidence_refs=("evidence-001",),
        semantic_result_id=None,
    )


def _typed_values(*, provider, model, result, call_id, invocation_result_id):
    return {
        "schema_version": "phase11-shadow-typed-provider-review-evidence-v1",
        "typed_evidence_id": None,
        "execution_id": "execution-001",
        "run_id": "run-001",
        "call_plan_id": _sha({"call_id": call_id}),
        "invocation_result_id": invocation_result_id,
        "call_id": call_id,
        "provider": provider,
        "model": model,
        "request_hash": PAYLOAD_HASH,
        "provider_review_identity": result.semantic_result_id,
        "typed_review_result": result,
        "typed_review_identity": result.semantic_result_id,
        "event_id": EVENT_ID,
        "event_version": 1,
        "prompt_version": "phase11-prompt-v1",
        "provider_review_schema_version": "phase10-review-schema-v1",
        "structured_verdict": {"verdict": "ADVISORY_REVIEW"},
        "reason_codes": ("TYPED_REVIEW_BOUND",),
        "production_effect": "NONE",
        "zero_production_effect_proof": "PROVEN_NONE",
    }


class TestCommittedBlockersAndTypedFixtures:
    def test_real_typed_provider_results_and_router_decisions_construct(self):
        deepseek = _deepseek()
        l1, l2 = _decision(deepseek, "L1"), _decision(deepseek, "L2")
        sonnet, opus = _claude(l1), _claude(l2)
        assert type(deepseek) is DeepSeekPrimaryReviewResultV1
        assert type(sonnet) is ClaudeEscalatedReviewResultV1
        assert type(opus) is ClaudeEscalatedReviewResultV1
        assert sonnet.route == "L1" and opus.route == "L2"
        assert l1.deepseek_semantic_result_id == l2.deepseek_semantic_result_id == deepseek.semantic_result_id

    def test_generic_hash_and_verdict_are_not_typed_review_objects(self):
        deepseek = _deepseek()
        assert not isinstance(deepseek.semantic_result_id, DeepSeekPrimaryReviewResultV1)
        assert {"provider_review_identity", "structured_verdict", "reason_codes"} != set(deepseek.to_mapping())

    def test_existing_routes_confirm_the_additive_l1_to_l2_bridge_need(self):
        source = Path(__file__).parents[1] / "engine"
        run_tree = ast.parse((source / "phase_11_shadow_run_orchestrator_v1.py").read_text(encoding="utf-8"))
        record_tree = ast.parse((source / "phase_11_shadow_execution_record_v1.py").read_text(encoding="utf-8"))
        run_text, record_text = ast.unparse(run_tree), ast.unparse(record_tree)
        assert "L1_TO_L2" in run_text
        assert 'ROUTES = (\'L0\', \'L1\', \'L2\')' in record_text


class TestFutureBridgeContracts:
    def test_typed_evidence_is_closed_immutable_and_requires_exact_supplied_result(self):
        deepseek = _deepseek()
        evidence = ShadowTypedProviderReviewEvidenceV1(**_typed_values(provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", result=deepseek, call_id="call-001", invocation_result_id="f" * 64))
        assert evidence.provider_review_identity == deepseek.semantic_result_id
        assert evidence.typed_review_identity == deepseek.semantic_result_id
        assert evidence.identity == ShadowTypedProviderReviewEvidenceV1(**_typed_values(provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", result=deepseek, call_id="call-001", invocation_result_id="f" * 64)).identity
        with pytest.raises((TypeError, ValueError, ShadowFinalizationEvidenceBridgeValidationError)):
            ShadowTypedProviderReviewEvidenceV1(**_typed_values(provider="ANTHROPIC", model="CLAUDE_SONNET_L1", result=deepseek, call_id="call-001", invocation_result_id="f" * 64))
        with pytest.raises((TypeError, ValueError, ShadowFinalizationEvidenceBridgeValidationError)):
            ShadowTypedProviderReviewEvidenceV1(**_typed_values(provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", result=DeepSeekPrimaryReviewResultV1, call_id="call-001", invocation_result_id="f" * 64))

    def test_l1_to_l2_lineage_preserves_l1_then_l2_while_mapping_clean_path_to_l2(self):
        deepseek = _deepseek()
        l1, l2 = _decision(deepseek, "L1"), _decision(deepseek, "L2")
        sonnet, opus = _claude(l1), _claude(l2)
        typed = (
            ShadowTypedProviderReviewEvidenceV1(**_typed_values(provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", result=deepseek, call_id="call-001", invocation_result_id="1" * 64)),
            ShadowTypedProviderReviewEvidenceV1(**_typed_values(provider="ANTHROPIC", model="CLAUDE_SONNET_L1", result=sonnet, call_id="call-002", invocation_result_id="2" * 64)),
            ShadowTypedProviderReviewEvidenceV1(**_typed_values(provider="ANTHROPIC", model="CLAUDE_OPUS_L2", result=opus, call_id="call-003", invocation_result_id="3" * 64)),
        )
        lineage = ShadowAdjudicationRouteLineageV1(
            schema_version="phase11-shadow-adjudication-route-lineage-v1", route_lineage_id=None,
            execution_id="execution-001", run_id="run-001", run_route="L1_TO_L2",
            adjudication_route="L2", clean_record_route="L2", router_decisions=(l1, l2),
            call_plan_ids=tuple(item.call_plan_id for item in typed), typed_review_ids=tuple(item.identity for item in typed),
            escalation_required=True, escalation_proven=True, reason_codes=("L1_TO_L2",),
            production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
        )
        assert lineage.run_route == "L1_TO_L2"
        assert lineage.adjudication_route == lineage.clean_record_route == "L2"
        with pytest.raises((TypeError, ValueError, ShadowFinalizationEvidenceBridgeValidationError)):
            ShadowAdjudicationRouteLineageV1(
                schema_version="phase11-shadow-adjudication-route-lineage-v1", route_lineage_id=None,
                execution_id="execution-001", run_id="run-001", run_route="L1_TO_L2",
                adjudication_route="L1", clean_record_route="L2", router_decisions=(l1, l2),
                call_plan_ids=tuple(item.call_plan_id for item in typed), typed_review_ids=tuple(item.identity for item in typed),
                escalation_required=True, escalation_proven=True, reason_codes=("L1_TO_L2",),
                production_effect="NONE", zero_production_effect_proof="PROVEN_NONE",
            )

    def test_bundle_and_terminal_record_are_disjoint_contracts(self):
        assert {item.value for item in ShadowTerminalRecordStatusV1} >= {"DENIED", "FAILED_CLOSED", "PARTIAL_EVIDENCE", "RECONCILIATION_REQUIRED"}
        assert ShadowAdjudicationEvidenceBundleV1 is not ShadowTerminalExecutionRecordV1
        assert lowercase_sha256({"route": "L2"}) == _sha({"route": "L2"})
        assert canonical_json_bytes({"safe": "metadata"}) == b'{"safe":"metadata"}'


def test_future_bridge_excludes_runtime_adapters_credentials_and_persistence():
    path = Path(__file__).parents[1] / "engine" / "phase_11_finalization_evidence_bridge_v1.py"
    if not path.exists():
        pytest.skip("RED suite: finalization evidence bridge implementation is intentionally absent")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not imports & {"os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "asyncio", "keyring", "boto3", "google", "azure", "telegram", "ccxt"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not names & {"invoke", "material_for_adapter", "credential_material", "commit_usage", "reconcile_uncertain_usage", "open", "mkdir", "makedirs", "environ", "getenv", "account", "exchange", "order", "trading", "publication"}
