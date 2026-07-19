"""Pure fail-closed provider request construction evidence."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class ProviderRequestInputV1:
 request_id:str; idempotency_key:str; payload_identity:str; provider_id:str; route_id:str; model_id:str; credential_reference_id:str; credential_verification_request_id:str; pricing_observation_id:str; pricing_policy_id:str; input_token_limit:int; output_token_limit:int; timeout_seconds:int; total_deadline_seconds:int; retry_count:int; payload_schema_version:str; sanitized_payload:tuple; credential_verified:bool; pricing_revalidated:bool; pricing_within_limits:bool; construction_authorized:bool
@dataclass(frozen=True,slots=True)
class ProviderRequestPolicyV1:
 policy_id:str; policy_version:str; allowed_provider_ids:tuple; allowed_route_ids:tuple; allowed_model_ids:tuple; allowed_payload_schema_versions:tuple; maximum_input_tokens:int; maximum_output_tokens:int; maximum_timeout_seconds:int; maximum_total_deadline_seconds:int; default_retry_count:int; maximum_retry_count:int; require_idempotency_key:bool; require_payload_identity:bool; require_credential_verification:bool; require_pricing_revalidation:bool; require_pricing_within_limits:bool; require_redacted_payload:bool; fail_closed:bool; reservation_required:bool; reservation_creation_authorized:bool; provider_connectivity_authorized:bool; provider_transmission_authorized:bool; provider_execution_authorized:bool
@dataclass(frozen=True,slots=True)
class ProviderRequestFailureV1: failure_code:str; safe_message:str; retryable:bool
@dataclass(frozen=True,slots=True)
class ConstructedProviderRequestV1:
 request_id:str; idempotency_key:str; payload_identity:str; provider_id:str; route_id:str; model_id:str; credential_reference_id:str; credential_verification_request_id:str; pricing_observation_id:str; pricing_policy_id:str; input_token_limit:int; output_token_limit:int; timeout_seconds:int; total_deadline_seconds:int; retry_count:int; payload_schema_version:str; sanitized_payload:tuple; request_constructed:bool; reservation_created:bool; provider_contacted:bool; transmitted:bool; execution_authorized:bool
@dataclass(frozen=True,slots=True)
class ProviderRequestConstructionResultV1:
 request_id:str; policy_id:str; valid:bool; failure_codes:tuple; constructed_request:ConstructedProviderRequestV1|None; credential_verified:bool; pricing_revalidated:bool; pricing_within_limits:bool; provider_allowed:bool; route_allowed:bool; model_allowed:bool; payload_schema_allowed:bool; timeout_allowed:bool; deadline_allowed:bool; retry_allowed:bool; idempotency_valid:bool; payload_identity_valid:bool; payload_redacted:bool; reservation_required:bool; reservation_created:bool; provider_connectivity_authorized:bool; provider_transmission_authorized:bool; provider_execution_authorized:bool
@dataclass(frozen=True,slots=True)
class ProviderRequestAuditEvidenceV1:
 request_id:str; idempotency_key:str; payload_identity:str; policy_id:str; failure_codes:tuple; reservation_created:bool; provider_contacted:bool; transmitted:bool; execution_authorized:bool
def construct_provider_request_v1(request_input,policy):
 codes=("NO_MODEL_APPROVED","NO_PAYLOAD_SCHEMA_APPROVED","NO_PROVIDER_APPROVED","NO_ROUTE_APPROVED","PROVIDER_CONNECTIVITY_NOT_AUTHORIZED","PROVIDER_EXECUTION_NOT_AUTHORIZED","PROVIDER_TRANSMISSION_NOT_AUTHORIZED","RESERVATION_NOT_CREATED","RETRY_NOT_AUTHORIZED")
 return ProviderRequestConstructionResultV1(request_input.request_id,policy.policy_id,False,codes,None,request_input.credential_verified,request_input.pricing_revalidated,request_input.pricing_within_limits,False,False,False,False,False,False,False,bool(request_input.idempotency_key),bool(request_input.payload_identity),True,policy.reservation_required,False,False,False,False)
def build_provider_request_audit_evidence_v1(request_input,policy,result):
 if request_input.request_id!=result.request_id or policy.policy_id!=result.policy_id: raise ValueError('identity mismatch')
 return ProviderRequestAuditEvidenceV1(request_input.request_id,request_input.idempotency_key,request_input.payload_identity,policy.policy_id,result.failure_codes,False,False,False,False)
