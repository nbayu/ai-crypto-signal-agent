"""RED contract for manual, redacted provider-budget configuration procedure."""

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from engine.phase_12_provider_budget_configuration_execution_procedure_contract_v1 import (
    ProviderBudgetConfigurationAuditEvidenceV1,
    ProviderBudgetConfigurationChecklistV1,
    ProviderBudgetConfigurationDecisionV1,
    ProviderBudgetConfigurationFailureV1,
    ProviderBudgetConfigurationPolicyV1,
    ProviderBudgetConfigurationTargetV1,
    ProviderBudgetOperatorAttestationV1,
    ProviderBudgetReviewerApprovalV1,
    build_provider_budget_configuration_audit_evidence_v1,
    evaluate_provider_budget_configuration_v1,
)


_AT = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


def _names(record: type) -> tuple[str, ...]:
    return tuple(field.name for field in fields(record))


def _targets() -> tuple[ProviderBudgetConfigurationTargetV1, ...]:
    return (
        ProviderBudgetConfigurationTargetV1("deepseek-target", "budget-config-policy-v1", "DEEPSEEK", "L0", "deepseek-v4-pro", Decimal("15.00"), Decimal("12.00"), Decimal("0.50"), Decimal("15.00"), Decimal("0.02"), Decimal("0.40"), Decimal("12.00"), 12000, 3000, 1, 3),
        ProviderBudgetConfigurationTargetV1("anthropic-l1-target", "budget-config-policy-v1", "ANTHROPIC", "L1", "claude-sonnet-5", Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00"), Decimal("0.12"), Decimal("0.50"), Decimal("15.00"), 12000, 3000, 1, 2),
        ProviderBudgetConfigurationTargetV1("anthropic-l2-target", "budget-config-policy-v1", "ANTHROPIC", "L2", "claude-opus-4-8", Decimal("25.00"), Decimal("20.00"), Decimal("0.85"), Decimal("25.00"), Decimal("0.20"), Decimal("0.20"), Decimal("6.00"), 12000, 3000, 1, 1),
    )


def test_public_api_is_immutable_and_target_values_are_locked() -> None:
    records = (ProviderBudgetConfigurationPolicyV1, ProviderBudgetConfigurationTargetV1, ProviderBudgetConfigurationChecklistV1, ProviderBudgetOperatorAttestationV1, ProviderBudgetReviewerApprovalV1, ProviderBudgetConfigurationDecisionV1, ProviderBudgetConfigurationAuditEvidenceV1)
    for record in records:
        assert is_dataclass(record) and getattr(record, "__dataclass_params__").frozen and hasattr(record, "__slots__")
    assert _names(ProviderBudgetConfigurationFailureV1) == ("failure_code", "safe_message", "retryable")
    assert tuple((item.provider_id, item.routing_level, item.exact_provider_model_id, item.per_request_cost_limit) for item in _targets()) == (("DEEPSEEK", "L0", "deepseek-v4-pro", Decimal("0.02")), ("ANTHROPIC", "L1", "claude-sonnet-5", Decimal("0.12")), ("ANTHROPIC", "L2", "claude-opus-4-8", Decimal("0.20")))
    defaults = ProviderBudgetConfigurationPolicyV1()
    assert defaults.fail_closed is True
    assert not any((defaults.provider_console_access_authorized, defaults.billing_configuration_authorized, defaults.spend_control_activation_authorized, defaults.credential_onboarding_authorized, defaults.credential_loading_authorized, defaults.network_authorized, defaults.provider_transmission_authorized))


def test_available_but_unactivated_targets_fail_closed_without_console_authority() -> None:
    policy = ProviderBudgetConfigurationPolicyV1(policy_id="budget-config-policy-v1", policy_version="v1", deployment_environment="CONTROLLED_PRODUCTION", currency="USD")
    checklists = tuple(ProviderBudgetConfigurationChecklistV1(f"check-{target.routing_level}", policy.policy_id, target.target_id, target.provider_id, target.routing_level, False, False, False, False, False, False, False, False, False) for target in _targets())
    decision = evaluate_provider_budget_configuration_v1(policy, _targets(), checklists, (), (), _AT)
    assert decision.ready is False
    assert not any((decision.provider_console_access_authorized, decision.billing_configuration_authorized, decision.spend_control_activation_authorized, decision.credential_onboarding_authorized, decision.credential_loading_authorized, decision.network_authorized, decision.provider_transmission_authorized))


def test_audit_rejects_target_mismatch_without_sensitive_evidence() -> None:
    policy = ProviderBudgetConfigurationPolicyV1(policy_id="budget-config-policy-v1", policy_version="v1", deployment_environment="CONTROLLED_PRODUCTION", currency="USD")
    checklists = tuple(ProviderBudgetConfigurationChecklistV1(f"check-{target.routing_level}", policy.policy_id, target.target_id, target.provider_id, target.routing_level, False, False, False, False, False, False, False, False, False) for target in _targets())
    decision = evaluate_provider_budget_configuration_v1(policy, _targets(), checklists, (), (), _AT)
    with pytest.raises(ValueError):
        build_provider_budget_configuration_audit_evidence_v1(policy, _targets()[1:], checklists, (), (), decision)
