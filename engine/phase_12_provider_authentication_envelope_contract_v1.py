"""Pure, fake-only, redacted provider authentication-envelope boundary."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

@dataclass(frozen=True, slots=True)
class ProviderAuthenticationPolicyV1:
 policy_id:str; policy_version:str; provider_id:str; authentication_scheme:str; authentication_location:str; authentication_field_name:str; allowed_authentication_schemes:tuple=(); allowed_authentication_locations:tuple=(); allowed_field_names:tuple=(); require_https:bool=True; require_verified_credential:bool=True; require_verified_secret_source:bool=True; require_single_secret_load:bool=True; require_single_secret_consumption:bool=True; require_secret_redaction:bool=True; require_nonempty_secret:bool=True; minimum_secret_length:int=0; maximum_secret_length:int=0; fingerprint_algorithm:str=""; fingerprint_prefix_length:int=0; secret_provider_invocation_limit:int=0; secret_consumption_limit:int=0; retry_allowed:bool=False; fallback_credential_allowed:bool=False; authentication_authorized:bool=False; transmission_authorized:bool=False; provider_execution_authorized:bool=False; fail_closed:bool=True
@dataclass(frozen=True, slots=True)
class ProviderCredentialBindingV1:
 credential_binding_id:str; provider_id:str; credential_reference_id:str; credential_verification_id:str; secret_source_id:str; secret_version_id:str; authentication_policy_id:str; endpoint_configuration_id:str; request_route_id:str; provider_request_id:str; reservation_id:str; persistence_command_id:str; connectivity_preflight_request_id:str; verified_at:datetime; expires_at:datetime; credential_verified:bool; secret_source_verified:bool; credential_active:bool; credential_expired:bool; credential_revoked:bool; authentication_authorized:bool; transmission_authorized:bool; provider_execution_authorized:bool
@dataclass(frozen=True, slots=True)
class ProviderAuthenticationRequestV1:
 authentication_request_id:str; authentication_policy_id:str; credential_binding_id:str; provider_id:str; credential_reference_id:str; endpoint_configuration_id:str; request_route_id:str; provider_request_id:str; reservation_id:str; persistence_command_id:str; connectivity_preflight_request_id:str; requested_at:datetime; credential_verified:bool; credential_binding_valid:bool; connectivity_metadata_ready:bool; persistence_confirmed:bool; persistence_recovery_clear:bool; authentication_envelope_authorized:bool
@dataclass(frozen=True, slots=True)
class ProviderAuthenticationFailureV1: failure_code:str; safe_message:str; retryable:bool
@dataclass(frozen=True, slots=True)
class ProviderAuthenticationEnvelopeV1:
 authentication_envelope_id:str; authentication_request_id:str; authentication_policy_id:str; credential_binding_id:str; provider_id:str; credential_reference_id:str; secret_source_id:str; secret_version_id:str; authentication_scheme:str; authentication_location:str; authentication_field_name:str; secret_fingerprint:str; secret_length:int; envelope_constructed:bool; secret_provider_invoked:bool; secret_handle_received:bool; secret_consumed:bool; authenticated:bool; transmitted:bool; provider_executed:bool; retry_attempted:bool; fallback_attempted:bool
@dataclass(frozen=True, slots=True)
class ProviderAuthenticationResultV1:
 authentication_request_id:str; authentication_policy_id:str; credential_binding_id:str; accepted:bool; failure_codes:tuple[str,...]; secret_provider_invoked:bool; secret_handle_received:bool; secret_consumed:bool; envelope_constructed:bool; credential_binding_valid:bool; authentication_policy_valid:bool; connectivity_evidence_valid:bool; persistence_evidence_valid:bool; fingerprint_valid:bool; redaction_valid:bool; authenticated:bool; transmitted:bool; provider_executed:bool; retry_attempted:bool; fallback_attempted:bool
 @property
 def envelope(self)->ProviderAuthenticationEnvelopeV1|None:
  if not self.envelope_constructed:return None
  return ProviderAuthenticationEnvelopeV1("redacted-envelope-v1",self.authentication_request_id,self.authentication_policy_id,self.credential_binding_id,"","","","","","","","REDACTED",0,True,self.secret_provider_invoked,self.secret_handle_received,self.secret_consumed,False,False,False,False,False)
@dataclass(frozen=True, slots=True)
class ProviderAuthenticationAuditEvidenceV1:
 authentication_request_id:str; authentication_policy_id:str; credential_binding_id:str; provider_id:str; credential_reference_id:str; secret_source_id:str; secret_version_id:str; endpoint_configuration_id:str; request_route_id:str; provider_request_id:str; reservation_id:str; persistence_command_id:str; connectivity_preflight_request_id:str; authentication_scheme:str; authentication_location:str; authentication_field_name:str; secret_fingerprint:str; secret_length:int; secret_provider_invoked:bool; secret_consumed:bool; envelope_constructed:bool; failure_codes:tuple[str,...]; authenticated:bool; transmitted:bool; provider_executed:bool; retry_attempted:bool; fallback_attempted:bool
class ProviderSecretHandleV1(Protocol):
 def secret_identity(self)->str:...
 def secret_length(self)->int:...
 def use_once_for_authentication(self,consumer:object)->object:...
class ProviderSecretProviderV1(Protocol):
 def load_verified_secret(self,credential_reference_id:str)->ProviderSecretHandleV1:...
def _id(v:object)->bool:return isinstance(v,str) and bool(v) and v==v.strip() and "*" not in v
def _codes(p:ProviderAuthenticationPolicyV1,b:ProviderCredentialBindingV1,r:ProviderAuthenticationRequestV1)->tuple[str,...]:
 c=[]
 for v,code in ((p.policy_id,"AUTHENTICATION_POLICY_ID_EMPTY"),(p.policy_version,"POLICY_VERSION_EMPTY"),(b.credential_binding_id,"CREDENTIAL_BINDING_ID_EMPTY"),(b.provider_id,"PROVIDER_ID_EMPTY"),(b.credential_reference_id,"CREDENTIAL_REFERENCE_ID_EMPTY"),(b.credential_verification_id,"CREDENTIAL_VERIFICATION_ID_EMPTY"),(b.secret_source_id,"SECRET_SOURCE_ID_EMPTY"),(b.secret_version_id,"SECRET_VERSION_ID_EMPTY"),(r.authentication_request_id,"AUTHENTICATION_REQUEST_ID_EMPTY")):
  if not _id(v):c.append(code)
 if p.provider_id!=b.provider_id or r.provider_id!=b.provider_id:c.append("PROVIDER_IDENTITY_MISMATCH")
 if r.credential_reference_id!=b.credential_reference_id:c.append("CREDENTIAL_REFERENCE_MISMATCH")
 if r.authentication_policy_id!=p.policy_id or b.authentication_policy_id!=p.policy_id:c.append("POLICY_IDENTITY_MISMATCH")
 if not r.credential_verified or not b.credential_verified:c.append("CREDENTIAL_NOT_VERIFIED")
 if not r.credential_binding_valid:c.append("CREDENTIAL_BINDING_INVALID")
 if not b.secret_source_verified:c.append("SECRET_SOURCE_NOT_VERIFIED")
 if not b.credential_active:c.append("CREDENTIAL_INACTIVE")
 if b.credential_expired:c.append("CREDENTIAL_EXPIRED")
 if b.credential_revoked:c.append("CREDENTIAL_REVOKED")
 if not r.connectivity_metadata_ready:c.append("CONNECTIVITY_METADATA_NOT_READY")
 if not r.persistence_confirmed:c.append("PERSISTENCE_NOT_CONFIRMED")
 if not r.persistence_recovery_clear:c.append("PERSISTENCE_RECOVERY_UNRESOLVED")
 if not r.authentication_envelope_authorized:c.append("AUTHENTICATION_ENVELOPE_NOT_AUTHORIZED")
 if not p.authentication_authorized or not b.authentication_authorized:c.append("AUTHENTICATION_NOT_AUTHORIZED")
 if p.authentication_scheme not in p.allowed_authentication_schemes:c.append("AUTHENTICATION_SCHEME_NOT_ALLOWED")
 if p.authentication_location not in p.allowed_authentication_locations:c.append("AUTHENTICATION_LOCATION_NOT_ALLOWED")
 if not _id(p.authentication_field_name):c.append("AUTHENTICATION_FIELD_NAME_EMPTY")
 elif p.authentication_field_name not in p.allowed_field_names or ":" in p.authentication_field_name or any(x.isspace() for x in p.authentication_field_name):c.append("AUTHENTICATION_FIELD_NAME_NOT_ALLOWED")
 if p.secret_provider_invocation_limit!=1:c.append("SECRET_PROVIDER_INVOCATION_LIMIT_INVALID")
 if p.secret_consumption_limit!=1:c.append("SECRET_CONSUMPTION_LIMIT_INVALID")
 if p.retry_allowed:c.append("RETRY_NOT_AUTHORIZED")
 if p.fallback_credential_allowed:c.append("FALLBACK_CREDENTIAL_NOT_AUTHORIZED")
 if not (isinstance(b.verified_at,datetime) and isinstance(b.expires_at,datetime) and isinstance(r.requested_at,datetime) and b.verified_at.tzinfo==UTC and b.expires_at.tzinfo==UTC and r.requested_at.tzinfo==UTC and b.verified_at<=r.requested_at<b.expires_at):c.append("CREDENTIAL_EXPIRED")
 return tuple(sorted(set(c)))
def _result(p,b,r,c,pi=False,hi=False,si=False,ok=False)->ProviderAuthenticationResultV1:
 return ProviderAuthenticationResultV1(r.authentication_request_id,p.policy_id,b.credential_binding_id,ok and not c,tuple(sorted(set(c))),pi,hi,si,ok and not c,not any(x in c for x in ("CREDENTIAL_BINDING_INVALID","CREDENTIAL_INACTIVE")),not any(x in c for x in ("AUTHENTICATION_POLICY_ID_EMPTY","POLICY_VERSION_EMPTY")),"CONNECTIVITY_METADATA_NOT_READY" not in c,"PERSISTENCE_NOT_CONFIRMED" not in c and "PERSISTENCE_RECOVERY_UNRESOLVED" not in c,ok and not c,True,False,False,False,False,False)
def build_provider_authentication_envelope_v1(p:ProviderAuthenticationPolicyV1,b:ProviderCredentialBindingV1,r:ProviderAuthenticationRequestV1,provider:ProviderSecretProviderV1|None)->ProviderAuthenticationResultV1:
 c=_codes(p,b,r)
 if c:return _result(p,b,r,c)
 if provider is None or not callable(getattr(provider,"load_verified_secret",None)):return _result(p,b,r,("SECRET_PROVIDER_REQUIRED",))
 try:h=provider.load_verified_secret(r.credential_reference_id)
 except Exception:return _result(p,b,r,("SECRET_PROVIDER_INVOCATION_FAILED",),True)
 if h is None or not callable(getattr(h,"use_once_for_authentication",None)) or not callable(getattr(h,"secret_length",None)):return _result(p,b,r,("SECRET_HANDLE_INVALID",),True)
 try:length=h.secret_length()
 except Exception:return _result(p,b,r,("SECRET_HANDLE_INVALID",),True,True)
 if not isinstance(length,int) or isinstance(length,bool) or length<=0:return _result(p,b,r,("SECRET_EMPTY",),True,True)
 if length<p.minimum_secret_length or length>p.maximum_secret_length:return _result(p,b,r,("SECRET_LENGTH_INVALID",),True,True)
 try:
  fingerprint=h.use_once_for_authentication(lambda value:sha256(value.encode("utf-8")).hexdigest()[:p.fingerprint_prefix_length])
 except Exception:return _result(p,b,r,("SECRET_CONSUMPTION_FAILED",),True,True)
 if not isinstance(fingerprint,str) or not fingerprint:return _result(p,b,r,("SECRET_FINGERPRINT_FAILURE",),True,True,True)
 return _result(p,b,r,(),True,True,True,True)
def build_provider_authentication_audit_evidence_v1(p:ProviderAuthenticationPolicyV1,b:ProviderCredentialBindingV1,r:ProviderAuthenticationRequestV1,result:ProviderAuthenticationResultV1)->ProviderAuthenticationAuditEvidenceV1:
 if not isinstance(p,ProviderAuthenticationPolicyV1) or not isinstance(b,ProviderCredentialBindingV1) or not isinstance(r,ProviderAuthenticationRequestV1) or not isinstance(result,ProviderAuthenticationResultV1) or result.authentication_request_id!=r.authentication_request_id or result.authentication_policy_id!=p.policy_id or result.credential_binding_id!=b.credential_binding_id or r.provider_id!=b.provider_id:raise ValueError("authentication evidence identity mismatch")
 return ProviderAuthenticationAuditEvidenceV1(r.authentication_request_id,p.policy_id,b.credential_binding_id,b.provider_id,b.credential_reference_id,b.secret_source_id,b.secret_version_id,b.endpoint_configuration_id,b.request_route_id,b.provider_request_id,b.reservation_id,b.persistence_command_id,b.connectivity_preflight_request_id,p.authentication_scheme,p.authentication_location,p.authentication_field_name,"REDACTED",0,result.secret_provider_invoked,result.secret_consumed,result.envelope_constructed,result.failure_codes,False,False,False,False,False)
