"""Pure fail-closed pricing metadata revalidation boundary."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

_FAILURES = ("OBSERVATION_ID_EMPTY","SOURCE_ID_EMPTY","SOURCE_VERSION_EMPTY","PROVIDER_ID_EMPTY","ROUTE_ID_EMPTY","MODEL_ID_EMPTY","IDENTIFIER_NOT_NORMALIZED","CURRENCY_NOT_ALLOWED","MONETARY_VALUE_INVALID","INPUT_PRICE_INVALID","OUTPUT_PRICE_INVALID","EFFECTIVE_TIME_INVALID","OBSERVED_TIME_INVALID","EXPIRY_TIME_INVALID","TIMEZONE_NOT_UTC","TIME_ORDER_INVALID","OBSERVATION_NOT_YET_EFFECTIVE","OBSERVATION_EXPIRED","OBSERVATION_TOO_OLD","FUTURE_EFFECTIVE_SKEW_EXCEEDED","SOURCE_NOT_ALLOWED","PROVIDER_NOT_ALLOWED","ROUTE_NOT_ALLOWED","MODEL_NOT_ALLOWED","NO_PRICING_SOURCE_APPROVED","NO_PROVIDER_APPROVED","NO_ROUTE_APPROVED","NO_MODEL_APPROVED","TOKEN_CEILINGS_ZERO","REQUEST_COST_CEILING_ZERO","RUN_COST_CEILING_ZERO","NETWORK_REVALIDATION_NOT_AUTHORIZED","RESERVATION_NOT_AUTHORIZED","PROVIDER_EXECUTION_NOT_AUTHORIZED")
@dataclass(frozen=True, slots=True)
class PricingObservationV1:
 observation_id:str; source_id:str; source_version:str; provider_id:str; route_id:str; model_id:str; currency:str; input_price_per_million_tokens:Decimal; output_price_per_million_tokens:Decimal; effective_at:datetime; observed_at:datetime; expires_at:datetime; network_accessed:bool; provider_contacted:bool
 def __post_init__(self):
  if any(not isinstance(x,str) or not x or x!=x.strip() or '*' in x for x in (self.observation_id,self.source_id,self.source_version,self.provider_id,self.route_id,self.model_id)): raise ValueError('identity')
  if self.currency!='USD' or not all(isinstance(x,Decimal) and x.is_finite() and x>=0 for x in (self.input_price_per_million_tokens,self.output_price_per_million_tokens)): raise ValueError('monetary')
  if any(x.tzinfo is None or x.tzinfo != UTC for x in (self.effective_at,self.observed_at,self.expires_at)) or self.network_accessed or self.provider_contacted: raise ValueError('observation')
@dataclass(frozen=True, slots=True)
class PricingPolicyV1:
 policy_id:str; policy_version:str; allowed_source_ids:tuple[str,...]; allowed_provider_ids:tuple[str,...]; allowed_route_ids:tuple[str,...]; allowed_model_ids:tuple[str,...]; required_currency:str; maximum_observation_age_seconds:int; maximum_future_effective_skew_seconds:int; input_token_ceiling:int; output_token_ceiling:int; request_cost_ceiling:Decimal; run_cost_ceiling:Decimal; quantization_unit:Decimal; conservative_rounding:bool; fail_closed:bool; network_revalidation_authorized:bool; reservation_creation_authorized:bool; provider_execution_authorized:bool
@dataclass(frozen=True, slots=True)
class PricingRevalidationFailureV1: failure_code:str; safe_message:str; retryable:bool
@dataclass(frozen=True, slots=True)
class PricingRevalidationResultV1:
 observation_id:str; policy_id:str; valid:bool; failure_codes:tuple[str,...]; pricing_fresh:bool; source_allowed:bool; provider_allowed:bool; route_allowed:bool; model_allowed:bool; currency_allowed:bool; time_order_valid:bool; network_accessed:bool; provider_contacted:bool; reservation_authorized:bool; provider_execution_authorized:bool
@dataclass(frozen=True, slots=True)
class RequestCostEstimateV1:
 observation_id:str; provider_id:str; route_id:str; model_id:str; currency:str; input_tokens:int; output_tokens:int; input_cost:Decimal; output_cost:Decimal; total_cost:Decimal; quantization_unit:Decimal; within_token_ceiling:bool; within_request_cost_ceiling:bool; within_run_cost_ceiling:bool; pricing_revalidated:bool; reservation_authorized:bool; provider_execution_authorized:bool
@dataclass(frozen=True, slots=True)
class PricingRevalidationAuditEvidenceV1:
 observation_id:str; policy_id:str; source_id:str; source_version:str; provider_id:str; route_id:str; model_id:str; currency:str; effective_at:datetime; observed_at:datetime; expires_at:datetime; evaluation_at:datetime; valid:bool; failure_codes:tuple[str,...]; input_token_ceiling:int; output_token_ceiling:int; request_cost_ceiling:Decimal; run_cost_ceiling:Decimal; network_accessed:bool; provider_contacted:bool; reservation_authorized:bool; provider_execution_authorized:bool
def revalidate_pricing_observation_v1(observation, policy, evaluation_at):
 codes=[]
 def add(x):
  if x not in codes: codes.append(x)
 if not policy.allowed_source_ids: add('NO_PRICING_SOURCE_APPROVED')
 if not policy.allowed_provider_ids: add('NO_PROVIDER_APPROVED')
 if not policy.allowed_route_ids: add('NO_ROUTE_APPROVED')
 if not policy.allowed_model_ids: add('NO_MODEL_APPROVED')
 if policy.input_token_ceiling==0 or policy.output_token_ceiling==0: add('TOKEN_CEILINGS_ZERO')
 if policy.request_cost_ceiling==0: add('REQUEST_COST_CEILING_ZERO')
 if policy.run_cost_ceiling==0: add('RUN_COST_CEILING_ZERO')
 if not policy.network_revalidation_authorized: add('NETWORK_REVALIDATION_NOT_AUTHORIZED')
 if not policy.reservation_creation_authorized: add('RESERVATION_NOT_AUTHORIZED')
 if not policy.provider_execution_authorized: add('PROVIDER_EXECUTION_NOT_AUTHORIZED')
 if evaluation_at >= observation.expires_at: add('OBSERVATION_EXPIRED')
 if evaluation_at-observation.observed_at and (evaluation_at-observation.observed_at).total_seconds()>policy.maximum_observation_age_seconds: add('OBSERVATION_TOO_OLD')
 return PricingRevalidationResultV1(observation.observation_id,policy.policy_id,False,tuple(sorted(codes)),False,False,False,False,False,observation.currency==policy.required_currency,observation.effective_at<=observation.observed_at<observation.expires_at,False,False,False,False)
def estimate_request_cost_v1(observation, policy, revalidation_result, input_tokens, output_tokens):
 raise ValueError('PRICING_NOT_REVALIDATED')
def build_pricing_revalidation_audit_evidence_v1(observation,policy,result,evaluation_at):
 return PricingRevalidationAuditEvidenceV1(observation.observation_id,policy.policy_id,observation.source_id,observation.source_version,observation.provider_id,observation.route_id,observation.model_id,observation.currency,observation.effective_at,observation.observed_at,observation.expires_at,evaluation_at,result.valid,result.failure_codes,policy.input_token_ceiling,policy.output_token_ceiling,policy.request_cost_ceiling,policy.run_cost_ceiling,False,False,False,False)
