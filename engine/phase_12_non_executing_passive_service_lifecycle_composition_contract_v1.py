"""Non-executing caller-supplied passive lifecycle composition."""
from __future__ import annotations
from dataclasses import dataclass

_ORDER=("POLICY_ID_EMPTY","POLICY_VERSION_EMPTY","PASSIVE_LIFECYCLE_COMPOSITION_IMPLEMENTATION_NOT_AUTHORIZED","PASSIVE_CLI_METADATA_COMPOSITION_NOT_AUTHORIZED","HOST_SIGNAL_METADATA_COMPOSITION_NOT_AUTHORIZED","GRACEFUL_SHUTDOWN_ORCHESTRATION_NOT_AUTHORIZED","HANDLER_RESTORATION_EXIT_ORDERING_NOT_AUTHORIZED","PROCESS_EXIT_COMPOSITION_NOT_AUTHORIZED","SYSTEMD_LIFECYCLE_RESULT_NOT_AUTHORIZED","LIFECYCLE_AUDIT_NOT_AUTHORIZED","NON_EXECUTING_METADATA_COMPOSITION_MODE_REQUIRED","COMPONENT_ADAPTER_INVOCATION_NOT_AUTHORIZED","PASSIVE_CLI_EXECUTION_NOT_AUTHORIZED")
_CHAIN=("POLICY_VALIDATED","PASSIVE_CLI_METADATA_VALIDATED","HOST_SIGNAL_METADATA_VALIDATED","PASSIVE_READY","SHUTDOWN_REQUESTED","GRACEFUL_SHUTDOWN_COMPLETE","HANDLER_RESTORATION_REQUIRED","HANDLER_RESTORATION_COMPLETE","EXIT_CLASSIFICATION_SELECTED","SYSTEMD_RESULT_BUILT","AUDIT_EVIDENCE_BUILT","READY")
@dataclass(frozen=True,slots=True,init=False)
class _R:
 values:tuple[tuple[str,object],...]
 def __init__(self,**v:object)->None:object.__setattr__(self,"values",tuple(v.items()))
 def __getattr__(self,n:str)->object:
  for k,v in self.values:
   if k==n:return v
  raise AttributeError(n)
class NonExecutingPassiveLifecyclePolicyV1(_R):__slots__=()
class NonExecutingPassiveLifecycleIdentityV1(_R):__slots__=()
class NonExecutingPassiveCliMetadataV1(_R):__slots__=()
class NonExecutingHostSignalMetadataV1(_R):__slots__=()
class NonExecutingGracefulShutdownMetadataV1(_R):__slots__=()
class NonExecutingHandlerRestorationMetadataV1(_R):__slots__=()
class NonExecutingProcessExitCompositionV1(_R):__slots__=()
class NonExecutingSystemdLifecycleResultV1(_R):__slots__=()
class NonExecutingPassiveLifecycleStateV1(_R):__slots__=()
class NonExecutingPassiveLifecycleTransitionV1(_R):__slots__=()
class NonExecutingPassiveLifecycleCompositionRequestV1(_R):__slots__=()
class NonExecutingPassiveLifecycleCompositionResultV1(_R):__slots__=()
@dataclass(frozen=True,slots=True)
class NonExecutingPassiveLifecycleFailureV1: failure_code:str; safe_message:str; retryable:bool
class NonExecutingPassiveLifecycleAuditEvidenceV1(_R):__slots__=()
def _v(o:object,n:str,d:object=False)->object:return getattr(o,n,d)
def _codes(*c:str)->tuple[str,...]:
 s=set(c);return tuple(x for x in _ORDER if x in s)
def _base(c:tuple[str,...])->dict[str,object]:
 return {"failure_codes":c,"failures":tuple(NonExecutingPassiveLifecycleFailureV1(x,"fail-closed non-executing metadata rejection",False) for x in c),"activation_gate_open":False,"credential_gate_open":False,"network_gate_open":False,"workload_gate_open":False,"operating_system_exit_code_return_authorized":False,"production_process_exit_execution_authorized":False,"process_exit_execution_authorized":False,"process_termination_authorized":False,"process_signal_transmission_authorized":False,"production_service_execution_authorized":False,"production_runtime_execution_authorized":False,"credential_loading_authorized":False,"systemd_access_authorized":False,"runtime_activation_authorized":False,"publication_authorized":False,"fail_closed":True}
def _validate(p:NonExecutingPassiveLifecyclePolicyV1,r:NonExecutingPassiveLifecycleCompositionRequestV1)->tuple[str,...]:
 c=[]
 if not _v(p,"policy_id",""):c.append("POLICY_ID_EMPTY")
 if not _v(p,"policy_version",""):c.append("POLICY_VERSION_EMPTY")
 for n,x in (("passive_service_lifecycle_composition_implementation_authorized","PASSIVE_LIFECYCLE_COMPOSITION_IMPLEMENTATION_NOT_AUTHORIZED"),("passive_cli_metadata_composition_implementation_authorized","PASSIVE_CLI_METADATA_COMPOSITION_NOT_AUTHORIZED"),("host_signal_metadata_composition_implementation_authorized","HOST_SIGNAL_METADATA_COMPOSITION_NOT_AUTHORIZED"),("graceful_shutdown_orchestration_implementation_authorized","GRACEFUL_SHUTDOWN_ORCHESTRATION_NOT_AUTHORIZED"),("handler_restoration_to_exit_ordering_implementation_authorized","HANDLER_RESTORATION_EXIT_ORDERING_NOT_AUTHORIZED"),("non_executing_process_exit_composition_implementation_authorized","PROCESS_EXIT_COMPOSITION_NOT_AUTHORIZED"),("systemd_compatible_lifecycle_result_implementation_authorized","SYSTEMD_LIFECYCLE_RESULT_NOT_AUTHORIZED"),("lifecycle_integration_audit_implementation_authorized","LIFECYCLE_AUDIT_NOT_AUTHORIZED"),("non_executing_caller_supplied_metadata_composition_only","NON_EXECUTING_METADATA_COMPOSITION_MODE_REQUIRED")):
  if not _v(p,n):c.append(x)
 if _v(p,"passive_cli_execution_authorized"):c.append("PASSIVE_CLI_EXECUTION_NOT_AUTHORIZED")
 if _v(p,"component_adapter_invocation_authorized"):c.append("COMPONENT_ADAPTER_INVOCATION_NOT_AUTHORIZED")
 if _v(r,"lifecycle_order",())!=_CHAIN:c.append("NON_EXECUTING_METADATA_COMPOSITION_MODE_REQUIRED")
 return _codes(*c)
def compose_non_executing_passive_service_lifecycle_v1(*,policy,request):
 c=_validate(policy,request);d=_base(c);d.update(ready=not c,composition_classification=("NON_EXECUTING_PASSIVE_SERVICE_LIFECYCLE_COMPOSITION_COMPLETE" if not c else "BLOCKED"),operating_system_exit_code_returned=False,process_exit_executed=False,systemd_contacted=False,current_state=NonExecutingPassiveLifecycleStateV1(state_id=_v(request,"request_id",""),state_code=("READY" if not c else "BLOCKED")));return NonExecutingPassiveLifecycleCompositionResultV1(**d)
def evaluate_non_executing_passive_service_lifecycle_v1(*,policy,request):return compose_non_executing_passive_service_lifecycle_v1(policy=policy,request=request)
def transition_non_executing_passive_service_lifecycle_v1(*,result,transition_id,target_state):
 c=_codes(*_v(result,"failure_codes",*()),*( () if target_state=="READY" and _v(result,"ready") else ("NON_EXECUTING_METADATA_COMPOSITION_MODE_REQUIRED",)));d=_base(c);d.update(transition_id=transition_id,current_state=NonExecutingPassiveLifecycleStateV1(state_id=transition_id,state_code=(target_state if not c else "BLOCKED")));return NonExecutingPassiveLifecycleTransitionV1(**d)
def build_non_executing_passive_service_lifecycle_audit_evidence_v1(*,evidence_id,result,transition):
 c=_codes(*_v(result,"failure_codes",()),*_v(transition,"failure_codes",()));d=_base(c);d.update(evidence_id=evidence_id,composition_classification=_v(result,"composition_classification",""),operating_system_exit_code_returned=False,process_exit_executed=False,systemd_contacted=False);return NonExecutingPassiveLifecycleAuditEvidenceV1(**d)
