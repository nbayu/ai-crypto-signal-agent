"""Pure, redacted validation for provider budget metadata."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True, slots=True)
class ProviderBudgetPolicyV1:
    policy_id:str=""; policy_version:str=""; deployment_environment:str=""; currency:str=""; allowed_provider_ids:tuple[str,...]=(); allowed_routing_levels:tuple[str,...]=(); require_hard_provider_limit:bool=True; require_soft_provider_alert:bool=True; require_daily_provider_limit:bool=True; require_monthly_provider_limit:bool=True; require_per_request_route_limit:bool=True; require_daily_route_limit:bool=True; require_monthly_route_limit:bool=True; require_separate_provider_budgets:bool=True; require_separate_route_budgets:bool=True; require_escalation_budget:bool=True; require_pricing_revalidation:bool=True; require_reservation_before_call:bool=True; require_usage_ledger:bool=True; require_zero_automatic_retry:bool=True; require_fail_closed_budget_exhaustion:bool=True; require_operator_alert_on_soft_threshold:bool=True; require_kill_switch_on_hard_threshold:bool=True; require_budget_change_approval:bool=True; require_evidence_freshness:bool=True; maximum_evidence_age_days:int=0; budget_configuration_authorized:bool=False; spend_control_activation_authorized:bool=False; credential_onboarding_authorized:bool=False; credential_loading_authorized:bool=False; network_authorized:bool=False; provider_transmission_authorized:bool=False; fail_closed:bool=True

@dataclass(frozen=True, slots=True)
class ProviderSpendControlProfileV1:
    provider_budget_profile_id:str; policy_id:str; provider_id:str; billing_currency:str; hard_spend_control_available:bool; hard_spend_control_enabled:bool; hard_spend_limit:Decimal; soft_alert_available:bool; soft_alert_enabled:bool; soft_alert_threshold:Decimal; daily_spend_limit:Decimal; monthly_spend_limit:Decimal; provider_budget_reference_id:str; alerting_policy_id:str; kill_switch_policy_id:str; budget_change_approval_id:str; pricing_evidence_id:str; pricing_revalidated:bool; verified_at:datetime|None; evidence_expires_at:datetime|None; profile_ready:bool

@dataclass(frozen=True, slots=True)
class ProviderRouteBudgetProfileV1:
    route_budget_profile_id:str; policy_id:str; provider_budget_profile_id:str; provider_id:str; routing_level:str; exact_provider_model_id:str; per_request_cost_limit:Decimal; daily_route_cost_limit:Decimal; monthly_route_cost_limit:Decimal; maximum_input_tokens_per_request:int; maximum_output_tokens_per_request:int; maximum_calls_per_signal:int; maximum_calls_per_day:int; pricing_evidence_id:str; pricing_revalidated:bool; reservation_policy_id:str; usage_ledger_policy_id:str; fail_closed_on_unknown_cost:bool; fail_closed_on_budget_exhaustion:bool; automatic_retry_allowed:bool; route_budget_ready:bool

@dataclass(frozen=True, slots=True)
class ProviderEscalationBudgetProfileV1:
    escalation_budget_profile_id:str; policy_id:str; L0_route_budget_profile_id:str; L1_route_budget_profile_id:str; L2_route_budget_profile_id:str; L0_to_L1_budget_revalidation_required:bool; L1_to_L2_budget_revalidation_required:bool; L0_to_L2_direct_budget_allowed:bool; cumulative_signal_budget_limit:Decimal; maximum_escalation_cost:Decimal; separate_provider_reservation_required:bool; separate_route_reservation_required:bool; stop_on_soft_threshold:bool; stop_on_hard_threshold:bool; operator_override_allowed:bool; escalation_budget_ready:bool

@dataclass(frozen=True, slots=True)
class ProviderBudgetFailureV1: failure_code:str; safe_message:str; retryable:bool

@dataclass(frozen=True, slots=True)
class ProviderBudgetReadinessDecisionV1:
    policy_id:str; deployment_environment:str; ready:bool; failure_codes:tuple[str,...]; DeepSeek_spend_control_ready:bool; Anthropic_spend_control_ready:bool; L0_budget_ready:bool; L1_budget_ready:bool; L2_budget_ready:bool; escalation_budget_ready:bool; hard_limits_enabled:bool; soft_alerts_enabled:bool; daily_limits_ready:bool; monthly_limits_ready:bool; per_request_limits_ready:bool; pricing_revalidated:bool; reservations_ready:bool; usage_ledger_ready:bool; alerting_ready:bool; kill_switch_ready:bool; evidence_fresh:bool; budget_configuration_authorized:bool; spend_control_activation_authorized:bool; credential_onboarding_authorized:bool; credential_loading_authorized:bool; network_authorized:bool; provider_transmission_authorized:bool

@dataclass(frozen=True, slots=True)
class ProviderBudgetAuditEvidenceV1:
    policy_id:str; deployment_environment:str; provider_budget_profile_ids:tuple[str,...]; route_budget_profile_ids:tuple[str,...]; exact_model_ids:tuple[str,...]; hard_limits_enabled:bool; soft_alerts_enabled:bool; daily_limits_ready:bool; monthly_limits_ready:bool; per_request_limits_ready:bool; escalation_budget_ready:bool; pricing_revalidated:bool; reservations_ready:bool; usage_ledger_ready:bool; alerting_ready:bool; kill_switch_ready:bool; evidence_fresh:bool; failure_codes:tuple[str,...]; budget_configuration_authorized:bool; spend_control_activation_authorized:bool; credential_onboarding_authorized:bool; credential_loading_authorized:bool; network_authorized:bool; provider_transmission_authorized:bool

_ROUTES={"L0":("DEEPSEEK","deepseek-v4-pro"),"L1":("ANTHROPIC","claude-sonnet-5"),"L2":("ANTHROPIC","claude-opus-4-8")}
def _id(v:object)->bool:return isinstance(v,str) and bool(v) and v==v.strip()
def _add(c:list[str], ok:bool, code:str)->None:
    if not ok:c.append(code)
def _money(v:object)->bool:return isinstance(v,Decimal) and v.is_finite() and v>=0
def _fresh(a:datetime|None,b:datetime|None,at:datetime,age:int,c:list[str])->bool:
    if not isinstance(a,datetime) or not isinstance(b,datetime): c.append("VERIFICATION_TIMESTAMP_REQUIRED");return False
    if a>at:c.append("EVIDENCE_FROM_FUTURE");return False
    if b<a or b<at or (at-a).days>age:c.append("EVIDENCE_EXPIRED");return False
    return True

def evaluate_provider_budget_readiness_v1(policy:ProviderBudgetPolicyV1,spend_profiles:tuple[ProviderSpendControlProfileV1,...],route_profiles:tuple[ProviderRouteBudgetProfileV1,...],escalation_profile:ProviderEscalationBudgetProfileV1|None,evaluated_at:datetime)->ProviderBudgetReadinessDecisionV1:
    c:list[str]=[]; _add(c,_id(policy.policy_id),"POLICY_ID_EMPTY");_add(c,_id(policy.policy_version),"POLICY_VERSION_EMPTY");_add(c,policy.deployment_environment=="CONTROLLED_PRODUCTION","DEPLOYMENT_ENVIRONMENT_NOT_ALLOWED");_add(c,_id(policy.currency),"CURRENCY_EMPTY")
    _add(c,{"DEEPSEEK","ANTHROPIC"}.issubset(policy.allowed_provider_ids),"PROVIDER_NOT_ALLOWED");_add(c,{"L0","L1","L2"}.issubset(policy.allowed_routing_levels),"ROUTING_LEVEL_NOT_ALLOWED")
    maxok=isinstance(policy.maximum_evidence_age_days,int) and not isinstance(policy.maximum_evidence_age_days,bool) and policy.maximum_evidence_age_days>=0
    _add(c,maxok,"VERIFICATION_TIMESTAMP_REQUIRED"); sm={x.provider_id:x for x in spend_profiles}; rm={x.routing_level:x for x in route_profiles}; spendok=[]; routeok=[]; fresh=[]
    for provider in ("DEEPSEEK","ANTHROPIC"):
        p=sm.get(provider)
        if p is None:c.append("PROVIDER_BUDGET_PROFILE_MISSING");spendok.append(False);fresh.append(False);continue
        _add(c,_id(p.provider_budget_profile_id),"PROVIDER_BUDGET_PROFILE_ID_EMPTY");_add(c,p.policy_id==policy.policy_id,"PROVIDER_ID_MISMATCH");_add(c,p.billing_currency==policy.currency,"CURRENCY_MISMATCH");_add(c,p.hard_spend_control_available,"HARD_SPEND_CONTROL_NOT_AVAILABLE");_add(c,p.hard_spend_control_enabled,"HARD_SPEND_CONTROL_NOT_ENABLED");_add(c,p.soft_alert_available,"SOFT_ALERT_NOT_AVAILABLE");_add(c,p.soft_alert_enabled,"SOFT_ALERT_NOT_ENABLED")
        money=all(_money(v) for v in (p.hard_spend_limit,p.soft_alert_threshold,p.daily_spend_limit,p.monthly_spend_limit));_add(c,money,"MONETARY_VALUE_INVALID");_add(c,money and p.hard_spend_limit>0,"HARD_SPEND_LIMIT_REQUIRED");_add(c,money and p.soft_alert_threshold<p.hard_spend_limit,"SOFT_ALERT_THRESHOLD_INVALID");_add(c,money and p.daily_spend_limit<=p.monthly_spend_limit,"SPEND_LIMIT_ORDER_INVALID");_add(c,_id(p.alerting_policy_id),"ALERTING_POLICY_REQUIRED");_add(c,_id(p.kill_switch_policy_id),"KILL_SWITCH_POLICY_REQUIRED");_add(c,_id(p.budget_change_approval_id),"BUDGET_CHANGE_APPROVAL_REQUIRED");_add(c,_id(p.pricing_evidence_id),"PRICING_EVIDENCE_REQUIRED");_add(c,p.pricing_revalidated,"PRICING_NOT_REVALIDATED")
        spendok.append(p.hard_spend_control_available and p.hard_spend_control_enabled and p.soft_alert_available and p.soft_alert_enabled and money and p.profile_ready);fresh.append(_fresh(p.verified_at,p.evidence_expires_at,evaluated_at,policy.maximum_evidence_age_days,c))
    for level,(provider,model) in _ROUTES.items():
        r=rm.get(level);p=sm.get(provider)
        if r is None:c.append("ROUTE_BUDGET_PROFILE_MISSING");routeok.append(False);continue
        _add(c,_id(r.route_budget_profile_id),"ROUTE_BUDGET_PROFILE_ID_EMPTY");_add(c,r.provider_id==provider and p is not None and r.provider_budget_profile_id==p.provider_budget_profile_id,"PROVIDER_ID_MISMATCH");_add(c,r.exact_provider_model_id==model,"EXACT_MODEL_ID_MISMATCH")
        monetary=all(_money(v) and v>0 for v in (r.per_request_cost_limit,r.daily_route_cost_limit,r.monthly_route_cost_limit));_add(c,monetary,"MONETARY_VALUE_INVALID");_add(c,monetary and r.per_request_cost_limit<=r.daily_route_cost_limit<=r.monthly_route_cost_limit,"ROUTE_LIMIT_EXCEEDS_PROVIDER_LIMIT");ints=(r.maximum_input_tokens_per_request,r.maximum_output_tokens_per_request,r.maximum_calls_per_signal,r.maximum_calls_per_day);_add(c,all(isinstance(x,int) and not isinstance(x,bool) and x>0 for x in ints),"TOKEN_LIMIT_INVALID")
        _add(c,_id(r.pricing_evidence_id),"PRICING_EVIDENCE_REQUIRED");_add(c,r.pricing_revalidated,"PRICING_NOT_REVALIDATED");_add(c,_id(r.reservation_policy_id),"RESERVATION_POLICY_REQUIRED");_add(c,_id(r.usage_ledger_policy_id),"USAGE_LEDGER_POLICY_REQUIRED");_add(c,r.fail_closed_on_unknown_cost,"UNKNOWN_COST_MUST_FAIL_CLOSED");_add(c,r.fail_closed_on_budget_exhaustion,"BUDGET_EXHAUSTION_MUST_FAIL_CLOSED");_add(c,not r.automatic_retry_allowed,"AUTOMATIC_RETRY_NOT_AUTHORIZED");routeok.append(monetary and r.pricing_revalidated and r.route_budget_ready and not r.automatic_retry_allowed)
    e=escalation_profile
    if e is None:c.append("ESCALATION_BUDGET_PROFILE_REQUIRED");eok=False
    else:
        _add(c,_id(e.escalation_budget_profile_id),"ESCALATION_BUDGET_PROFILE_REQUIRED");_add(c,e.L0_to_L1_budget_revalidation_required and e.L1_to_L2_budget_revalidation_required,"ESCALATION_REVALIDATION_REQUIRED");_add(c,not e.L0_to_L2_direct_budget_allowed,"DIRECT_L0_TO_L2_NOT_AUTHORIZED");_add(c,e.separate_provider_reservation_required,"SEPARATE_PROVIDER_RESERVATION_REQUIRED");_add(c,e.separate_route_reservation_required,"SEPARATE_ROUTE_RESERVATION_REQUIRED");_add(c,e.stop_on_hard_threshold,"HARD_THRESHOLD_STOP_REQUIRED");_add(c,not e.operator_override_allowed,"OPERATOR_OVERRIDE_NOT_AUTHORIZED");_add(c,_money(e.cumulative_signal_budget_limit) and _money(e.maximum_escalation_cost),"MONETARY_VALUE_INVALID");eok=e.escalation_budget_ready
    codes=tuple(sorted(set(c))); hard=all(x.hard_spend_control_enabled for x in sm.values()) and len(sm)==2;soft=all(x.soft_alert_enabled for x in sm.values()) and len(sm)==2
    return ProviderBudgetReadinessDecisionV1(policy.policy_id,policy.deployment_environment,not codes,codes,spendok[0] if spendok else False,spendok[1] if len(spendok)>1 else False,*routeok,eok,hard,soft,hard,hard,all(routeok),all(x.pricing_revalidated for x in sm.values()) and len(sm)==2,all(_id(x.reservation_policy_id) for x in rm.values()) and len(rm)==3,all(_id(x.usage_ledger_policy_id) for x in rm.values()) and len(rm)==3,all(_id(x.alerting_policy_id) for x in sm.values()) and len(sm)==2,all(_id(x.kill_switch_policy_id) for x in sm.values()) and len(sm)==2,maxok and all(fresh),False,False,False,False,False,False)

def build_provider_budget_audit_evidence_v1(policy,spend_profiles,route_profiles,escalation_profile,decision):
    sm={x.provider_id:x for x in spend_profiles};rm={x.routing_level:x for x in route_profiles}
    if set(sm)!={"DEEPSEEK","ANTHROPIC"} or len(spend_profiles)!=2 or set(rm)!={"L0","L1","L2"} or len(route_profiles)!=3 or decision.policy_id!=policy.policy_id:raise ValueError("identity alignment failed")
    routes=tuple(rm[x] for x in ("L0","L1","L2"))
    return ProviderBudgetAuditEvidenceV1(policy.policy_id,policy.deployment_environment,tuple(sm[x].provider_budget_profile_id for x in ("DEEPSEEK","ANTHROPIC")),tuple(x.route_budget_profile_id for x in routes),tuple(x.exact_provider_model_id for x in routes),decision.hard_limits_enabled,decision.soft_alerts_enabled,decision.daily_limits_ready,decision.monthly_limits_ready,decision.per_request_limits_ready,decision.escalation_budget_ready,decision.pricing_revalidated,decision.reservations_ready,decision.usage_ledger_ready,decision.alerting_ready,decision.kill_switch_ready,decision.evidence_fresh,decision.failure_codes,False,False,False,False,False,False)
