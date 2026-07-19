"""RED contract for pure Phase 12 provider-request construction evidence."""
from __future__ import annotations
import ast
import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import pytest
from engine.phase_12_provider_request_construction_contract_v1 import (
 ProviderRequestInputV1, ProviderRequestPolicyV1, ProviderRequestFailureV1,
 ConstructedProviderRequestV1, ProviderRequestConstructionResultV1,
 ProviderRequestAuditEvidenceV1, construct_provider_request_v1,
 build_provider_request_audit_evidence_v1,
)

_INPUT=("request_id","idempotency_key","payload_identity","provider_id","route_id","model_id","credential_reference_id","credential_verification_request_id","pricing_observation_id","pricing_policy_id","input_token_limit","output_token_limit","timeout_seconds","total_deadline_seconds","retry_count","payload_schema_version","sanitized_payload","credential_verified","pricing_revalidated","pricing_within_limits","construction_authorized")
_POLICY=("policy_id","policy_version","allowed_provider_ids","allowed_route_ids","allowed_model_ids","allowed_payload_schema_versions","maximum_input_tokens","maximum_output_tokens","maximum_timeout_seconds","maximum_total_deadline_seconds","default_retry_count","maximum_retry_count","require_idempotency_key","require_payload_identity","require_credential_verification","require_pricing_revalidation","require_pricing_within_limits","require_redacted_payload","fail_closed","reservation_required","reservation_creation_authorized","provider_connectivity_authorized","provider_transmission_authorized","provider_execution_authorized")
_FAILURES={"REQUEST_ID_EMPTY","IDEMPOTENCY_KEY_EMPTY","PAYLOAD_IDENTITY_EMPTY","PROVIDER_ID_EMPTY","ROUTE_ID_EMPTY","MODEL_ID_EMPTY","CREDENTIAL_REFERENCE_ID_EMPTY","CREDENTIAL_VERIFICATION_REQUEST_ID_EMPTY","PRICING_OBSERVATION_ID_EMPTY","PRICING_POLICY_ID_EMPTY","PAYLOAD_SCHEMA_VERSION_EMPTY","IDENTIFIER_NOT_NORMALIZED","PROVIDER_NOT_ALLOWED","ROUTE_NOT_ALLOWED","MODEL_NOT_ALLOWED","PAYLOAD_SCHEMA_NOT_ALLOWED","NO_PROVIDER_APPROVED","NO_ROUTE_APPROVED","NO_MODEL_APPROVED","NO_PAYLOAD_SCHEMA_APPROVED","INPUT_TOKEN_LIMIT_INVALID","OUTPUT_TOKEN_LIMIT_INVALID","INPUT_TOKEN_LIMIT_EXCEEDED","OUTPUT_TOKEN_LIMIT_EXCEEDED","TIMEOUT_INVALID","TOTAL_DEADLINE_INVALID","TIMEOUT_EXCEEDED","TOTAL_DEADLINE_EXCEEDED","TOTAL_DEADLINE_BELOW_TIMEOUT","RETRY_COUNT_INVALID","RETRY_NOT_AUTHORIZED","IDEMPOTENCY_KEY_REQUIRED","PAYLOAD_IDENTITY_REQUIRED","CREDENTIAL_NOT_VERIFIED","PRICING_NOT_REVALIDATED","PRICING_LIMIT_NOT_SATISFIED","PAYLOAD_NOT_REDACTED","FORBIDDEN_PAYLOAD_FIELD","PAYLOAD_VALUE_TYPE_NOT_ALLOWED","CONSTRUCTION_NOT_AUTHORIZED","RESERVATION_REQUIRED","RESERVATION_NOT_CREATED","PROVIDER_CONNECTIVITY_NOT_AUTHORIZED","PROVIDER_TRANSMISSION_NOT_AUTHORIZED","PROVIDER_EXECUTION_NOT_AUTHORIZED"}

def _input():
 return ProviderRequestInputV1("request-v1","idem-v1","payload-v1","provider-v1","route-v1","model-v1","cred-v1","verify-v1","price-v1","policy-v1",0,0,0,0,0,"schema-v1",(("messages",("sanitized",)),),False,False,False,False)
def _policy():
 return ProviderRequestPolicyV1("policy-v1","V1",(),(),(),(),0,0,0,0,0,0,True,True,True,True,True,True,True,True,False,False,False,False)
def _frozen(x):
 assert is_dataclass(x) and type(x).__dataclass_params__.frozen and "__dict__" not in type(x).__slots__

def test_public_records_are_closed_immutable_and_secret_free():
 assert tuple(f.name for f in fields(ProviderRequestInputV1)) == _INPUT
 assert tuple(f.name for f in fields(ProviderRequestPolicyV1)) == _POLICY
 value, policy = _input(), _policy()
 result=construct_provider_request_v1(value,policy)
 evidence=build_provider_request_audit_evidence_v1(value,policy,result)
 for x in (value,policy,result,evidence): _frozen(x)
 assert not {"api_key","token","authorization","secret","raw_prompt"}.intersection(f.name for f in fields(value))
 with pytest.raises(FrozenInstanceError): value.request_id="other" # type: ignore[misc]
 with pytest.raises(TypeError): ProviderRequestInputV1(**{f.name:getattr(value,f.name) for f in fields(value)},api_key="forbidden")

def test_empty_allowlists_zero_limits_and_zero_retry_fail_closed():
 result=construct_provider_request_v1(_input(),_policy())
 assert result.valid is False
 assert {"NO_PROVIDER_APPROVED","NO_ROUTE_APPROVED","NO_MODEL_APPROVED","NO_PAYLOAD_SCHEMA_APPROVED","RETRY_NOT_AUTHORIZED","RESERVATION_NOT_CREATED","PROVIDER_CONNECTIVITY_NOT_AUTHORIZED","PROVIDER_TRANSMISSION_NOT_AUTHORIZED","PROVIDER_EXECUTION_NOT_AUTHORIZED"}.issubset(result.failure_codes)
 assert tuple(result.failure_codes)==tuple(sorted(result.failure_codes))
 assert set(result.failure_codes).issubset(_FAILURES)
 assert (result.reservation_created,result.provider_connectivity_authorized,result.provider_transmission_authorized,result.provider_execution_authorized)==(False,False,False,False)

def test_identity_payload_timeout_and_audit_are_deterministic():
 value, policy=_input(),_policy(); result=construct_provider_request_v1(value,policy)
 assert list(inspect.signature(construct_provider_request_v1).parameters)==["request_input","policy"]
 first=build_provider_request_audit_evidence_v1(value,policy,result); second=build_provider_request_audit_evidence_v1(value,policy,result)
 assert first==second
 assert first.request_id==value.request_id and first.idempotency_key==value.idempotency_key and first.payload_identity==value.payload_identity
 with pytest.raises(TypeError): construct_provider_request_v1(value,policy,0)

def test_module_has_no_connectivity_or_operational_surface():
 import engine.phase_12_provider_request_construction_contract_v1 as module
 tree=ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
 banned={"os","pathlib","subprocess","socket","urllib","http","requests","httpx","aiohttp","openai","telegram","ccxt"}
 names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}; imports={a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names}
 assert not banned.intersection(names|imports)
 assert not {"open","print","getenv","environ","uuid4","random","time","now","utcnow"}.intersection(names)
