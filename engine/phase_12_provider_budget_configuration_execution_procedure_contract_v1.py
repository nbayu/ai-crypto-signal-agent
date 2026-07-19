"""Pure redacted budget-configuration procedure validation."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True, slots=True)
class ProviderBudgetConfigurationPolicyV1:
    policy_id:str=""; policy_version:str=""; deployment_environment:str=""; currency:str=""; provider_console_access_authorized:bool=False; billing_configuration_authorized:bool=False; spend_control_activation_authorized:bool=False; credential_onboarding_authorized:bool=False; credential_loading_authorized:bool=False; network_authorized:bool=False; provider_transmission_authorized:bool=False; fail_closed:bool=True
@dataclass(frozen=True, slots=True)
class ProviderBudgetConfigurationTargetV1:
    target_id:str; policy_id:str; provider_id:str; routing_level:str; exact_provider_model_id:str; hard_spend_control_target:Decimal; soft_alert_threshold_target:Decimal; daily_spend_limit_target:Decimal; monthly_spend_limit_target:Decimal; per_request_cost_limit:Decimal; daily_route_cost_limit:Decimal; monthly_route_cost_limit:Decimal; maximum_input_tokens_per_request:int; maximum_output_tokens_per_request:int; maximum_calls_per_signal:int; maximum_calls_per_day:int
@dataclass(frozen=True, slots=True)
class ProviderBudgetConfigurationChecklistV1:
    checklist_id:str; policy_id:str; target_id:str; provider_id:str; routing_level:str; hard_cap_confirmed:bool; soft_alert_confirmed:bool; pricing_revalidated:bool; reservation_ready:bool; usage_ledger_ready:bool; alerting_ready:bool; kill_switch_ready:bool; rollback_ready:bool; checklist_ready:bool
@dataclass(frozen=True, slots=True)
class ProviderBudgetOperatorAttestationV1:
    attestation_id:str; checklist_id:str; target_id:str; operator_id:str; operator_role:str; target_confirmed:bool; verified_at:datetime|None; evidence_expires_at:datetime|None; attestation_ready:bool
@dataclass(frozen=True, slots=True)
class ProviderBudgetReviewerApprovalV1:
    approval_id:str; attestation_id:str; reviewer_id:str; reviewer_role:str; distinct:bool; approved:bool; reviewed_at:datetime|None; evidence_expires_at:datetime|None; approval_ready:bool
@dataclass(frozen=True, slots=True)
class ProviderBudgetConfigurationFailureV1: failure_code:str; safe_message:str; retryable:bool
@dataclass(frozen=True, slots=True)
class ProviderBudgetConfigurationDecisionV1:
    policy_id:str; deployment_environment:str; ready:bool; failure_codes:tuple[str,...]; provider_console_access_authorized:bool; billing_configuration_authorized:bool; spend_control_activation_authorized:bool; credential_onboarding_authorized:bool; credential_loading_authorized:bool; network_authorized:bool; provider_transmission_authorized:bool
@dataclass(frozen=True, slots=True)
class ProviderBudgetConfigurationAuditEvidenceV1:
    policy_id:str; target_ids:tuple[str,...]; failure_codes:tuple[str,...]; provider_console_access_authorized:bool; billing_configuration_authorized:bool; spend_control_activation_authorized:bool; credential_onboarding_authorized:bool; credential_loading_authorized:bool; network_authorized:bool; provider_transmission_authorized:bool

_EXPECTED=(("DEEPSEEK","L0","deepseek-v4-pro",Decimal("15.00"),Decimal("12.00"),Decimal("0.50"),Decimal("15.00"),Decimal("0.02"),Decimal("0.40"),Decimal("12.00"),12000,3000,1,3),("ANTHROPIC","L1","claude-sonnet-5",Decimal("25.00"),Decimal("20.00"),Decimal("0.85"),Decimal("25.00"),Decimal("0.12"),Decimal("0.50"),Decimal("15.00"),12000,3000,1,2),("ANTHROPIC","L2","claude-opus-4-8",Decimal("25.00"),Decimal("20.00"),Decimal("0.85"),Decimal("25.00"),Decimal("0.20"),Decimal("0.20"),Decimal("6.00"),12000,3000,1,1))
def evaluate_provider_budget_configuration_v1(policy,targets,checklists,attestations,approvals,evaluated_at):
    c=[]
    if len(targets)!=3:c.append("TARGET_REQUIRED")
    for target,expected in zip(targets,_EXPECTED):
        values=(target.provider_id,target.routing_level,target.exact_provider_model_id,target.hard_spend_control_target,target.soft_alert_threshold_target,target.daily_spend_limit_target,target.monthly_spend_limit_target,target.per_request_cost_limit,target.daily_route_cost_limit,target.monthly_route_cost_limit,target.maximum_input_tokens_per_request,target.maximum_output_tokens_per_request,target.maximum_calls_per_signal,target.maximum_calls_per_day)
        if values!=expected:c.append("TARGET_MISMATCH")
    if len(checklists)!=3 or not all(x.checklist_ready and x.hard_cap_confirmed and x.soft_alert_confirmed and x.pricing_revalidated and x.reservation_ready and x.usage_ledger_ready and x.alerting_ready and x.kill_switch_ready and x.rollback_ready for x in checklists):c.append("CHECKLIST_NOT_READY")
    if not attestations:c.append("OPERATOR_ATTESTATION_REQUIRED")
    if not approvals:c.append("REVIEWER_APPROVAL_REQUIRED")
    return ProviderBudgetConfigurationDecisionV1(policy.policy_id,policy.deployment_environment,not c,tuple(sorted(set(c))),False,False,False,False,False,False,False)
def build_provider_budget_configuration_audit_evidence_v1(policy,targets,checklists,attestations,approvals,decision):
    if len(targets)!=3 or tuple(x.target_id for x in targets)!=("deepseek-target","anthropic-l1-target","anthropic-l2-target"):raise ValueError("target identity alignment failed")
    return ProviderBudgetConfigurationAuditEvidenceV1(policy.policy_id,tuple(x.target_id for x in targets),decision.failure_codes,False,False,False,False,False,False,False)
