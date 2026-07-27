"""RED contract for immutable Phase 11 credential-verification boundary."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_blocked_readiness_reconciliation_v1 import (
    get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1,
)
from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import (
    get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotProviderRoleV1,
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_revalidation_boundary_v1 import (
    get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1,
)
from engine.phase_11_shadow_pilot_credential_configuration_verification_boundary_v1 import (
    ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1,
    ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1,
    ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError,
    ShadowPhase11CredentialConfigurationVerificationCheckKindV1,
    ShadowPhase11CredentialConfigurationVerificationRequestV1,
    ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1,
    ShadowPhase11CredentialConfigurationVerificationResultStateV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1,
    sha256_hex,
)


BASELINE = "7b0edf90cf5abbb7776a0e56058839543e8dc2ab"
PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
REQUEST_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_REQUEST_001"
RESULT_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_RESULT_BOUNDARY_001"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_VERIFICATION_BOUNDARY_001"
ROLES = (
    ShadowPhase11PilotProviderRoleV1.PRIMARY,
    ShadowPhase11PilotProviderRoleV1.L1,
    ShadowPhase11PilotProviderRoleV1.L2,
)
CHECKS = (
    ShadowPhase11CredentialConfigurationVerificationCheckKindV1.PRIMARY_PROVIDER_CREDENTIAL_CONFIGURATION,
    ShadowPhase11CredentialConfigurationVerificationCheckKindV1.L1_PROVIDER_CREDENTIAL_CONFIGURATION,
    ShadowPhase11CredentialConfigurationVerificationCheckKindV1.L2_PROVIDER_CREDENTIAL_CONFIGURATION,
    ShadowPhase11CredentialConfigurationVerificationCheckKindV1.SECRET_MATERIAL_REPOSITORY_ABSENCE,
    ShadowPhase11CredentialConfigurationVerificationCheckKindV1.RUNTIME_CREDENTIAL_INJECTION_BOUNDARY,
)
REQUEST_REASONS = tuple(sorted((
    "REQUIRED_CREDENTIAL_SLOTS_DEFINED",
    "CREDENTIAL_VERIFICATION_CHECKS_DEFINED",
    "VERIFICATION_EXECUTION_NOT_AUTHORIZED",
    "ENVIRONMENT_ACCESS_NOT_AUTHORIZED",
    "CREDENTIAL_ACCESS_NOT_AUTHORIZED",
    "SECRET_MATERIAL_ACCESS_NOT_AUTHORIZED",
    "NO_PROVIDER_AUTHENTICATION_REQUEST_AUTHORITY",
)))
RESULT_REASONS = tuple(sorted((
    "RESULT_ABSENT",
    "VERIFICATION_NOT_STARTED",
    "VERIFICATION_NOT_COMPLETED",
    "CREDENTIAL_REFERENCES_NOT_RESOLVED",
    "NO_PROVIDER_AUTHENTICATION_OBSERVATION",
    "NO_CHECK_PASSED",
)))
EVIDENCE_REASONS = tuple(sorted((
    "CREDENTIAL_VERIFICATION_REQUEST_DEFINED",
    "CREDENTIAL_VERIFICATION_EXECUTION_NOT_AUTHORIZED",
    "CREDENTIAL_VERIFICATION_RESULT_ABSENT",
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "NO_ENVIRONMENT_OR_CREDENTIAL_ACCESS",
    "NO_PROVIDER_AUTHENTICATION_REQUEST",
    "NO_OPERATIONAL_AUTHORITY",
)))
FUTURE_PATH = "engine/phase_11_shadow_pilot_credential_configuration_verification_boundary_v1.py"


def _request(**overrides: object) -> ShadowPhase11CredentialConfigurationVerificationRequestV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    reconciliation = get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-credential-configuration-verification-request-v1",
        "request_id": None,
        "request_reference": REQUEST_REFERENCE,
        "credential_safe_gate_reference": gate.evidence_reference,
        "credential_safe_gate_identity": gate.identity,
        "blocked_readiness_reconciliation_reference": reconciliation.evidence_reference,
        "blocked_readiness_reconciliation_identity": reconciliation.identity,
        "current_runtime_integrity_reference": runtime.evidence_reference,
        "current_runtime_integrity_identity": runtime.identity,
        "pricing_revalidation_boundary_reference": pricing.evidence_reference,
        "pricing_revalidation_boundary_identity": pricing.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "provider_roles": ROLES,
        "primary_model_identifier": "deepseek-v4-pro",
        "l1_model_identifier": "claude-sonnet-5",
        "l2_model_identifier": "claude-opus-4-8",
        "check_kinds": CHECKS,
        "verification_descriptor_defined": True,
        "verification_execution_authorized": False,
        "credential_reference_access_authorized": False,
        "secret_material_access_authorized": False,
        "environment_access_authorized": False,
        "filesystem_access_authorized": False,
        "network_access_authorized": False,
        "provider_authentication_probe_authorized": False,
        "provider_authentication_request_created": False,
        "credential_configuration_write_authorized": False,
        "actual_credential_reference_names_present": False,
        "secret_material_present": False,
        "reason_codes": REQUEST_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11CredentialConfigurationVerificationRequestV1(**fields)


def _result(**overrides: object) -> ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1:
    request = _request()
    fields = {
        "schema_version": "phase11-shadow-pilot-credential-configuration-verification-result-boundary-v1",
        "result_boundary_id": None,
        "result_boundary_reference": RESULT_REFERENCE,
        "request_reference": request.request_reference,
        "request_identity": request.identity,
        "result_state": ShadowPhase11CredentialConfigurationVerificationResultStateV1.RESULT_ABSENT_NOT_EXECUTED,
        "result_present": False,
        "result_reference": None,
        "result_identity": None,
        "verification_started": False,
        "verification_completed": False,
        "credential_references_resolved": False,
        "secret_material_loaded": False,
        "environment_configuration_observed": False,
        "filesystem_configuration_observed": False,
        "primary_provider_configuration_verified": False,
        "l1_provider_configuration_verified": False,
        "l2_provider_configuration_verified": False,
        "secret_material_repository_absence_verified": False,
        "runtime_credential_injection_boundary_verified": False,
        "provider_authentication_probe_performed": False,
        "provider_authentication_observation_present": False,
        "provider_authentication_accepted": False,
        "all_checks_passed": False,
        "reason_codes": RESULT_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1(**fields)


def _evidence(**overrides: object) -> ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    reconciliation = get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    fields = {
        "schema_version": "phase11-shadow-pilot-credential-configuration-verification-boundary-v1",
        "evidence_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "locked_repository_baseline": BASELINE,
        "locked_phase09_baseline": PHASE09,
        "credential_safe_gate_reference": gate.evidence_reference,
        "credential_safe_gate_identity": gate.identity,
        "blocked_readiness_reconciliation_reference": reconciliation.evidence_reference,
        "blocked_readiness_reconciliation_identity": reconciliation.identity,
        "current_runtime_integrity_reference": runtime.evidence_reference,
        "current_runtime_integrity_identity": runtime.identity,
        "pricing_revalidation_boundary_reference": pricing.evidence_reference,
        "pricing_revalidation_boundary_identity": pricing.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "boundary_state": ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1.REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED,
        "request": _request(),
        "result_boundary": _result(),
        "verification_descriptor_defined": True,
        "verification_execution_authorized": False,
        "verification_started": False,
        "verification_result_present": False,
        "verification_completed": False,
        "credential_configuration_verified": False,
        "credential_reference_access_authorized": False,
        "credential_reference_access_observed": False,
        "secret_material_access_authorized": False,
        "secret_material_access_observed": False,
        "secret_material_present": False,
        "environment_access_authorized": False,
        "environment_access_observed": False,
        "filesystem_access_authorized": False,
        "filesystem_access_observed": False,
        "network_access_authorized": False,
        "network_access_observed": False,
        "provider_authentication_probe_authorized": False,
        "provider_authentication_probe_performed": False,
        "provider_authentication_request_created": False,
        "provider_authentication_observation_present": False,
        "provider_authentication_accepted": False,
        "credential_configuration_write_authorized": False,
        "credential_configuration_modified": False,
        "pricing_revalidation_execution_authorized": False,
        "provider_request_created": False,
        "pre_call_reservation_created": False,
        "ledger_entry_created": False,
        "runtime_invocation_authorized": False,
        "provider_call_authorized": False,
        "provider_transmission_authorized": False,
        "run_size_authorized": False,
        "manifest_activation_authorized": False,
        "launch_authorized": False,
        "production_authorized": False,
        "launch_readiness": ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "reason_codes": EVIDENCE_REASONS,
    }
    fields.update(overrides)
    return ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1(**fields)


def _reject(factory: object, **overrides: object) -> None:
    with pytest.raises(ShadowPhase11CredentialConfigurationVerificationBoundaryValidationError):
        factory(**overrides)


def test_closed_states_and_check_kinds_are_exact():
    assert tuple(ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1) == (
        ShadowPhase11CredentialConfigurationVerificationBoundaryStateV1.REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED,
    )
    assert tuple(ShadowPhase11CredentialConfigurationVerificationResultStateV1) == (
        ShadowPhase11CredentialConfigurationVerificationResultStateV1.RESULT_ABSENT_NOT_EXECUTED,
    )
    assert tuple(ShadowPhase11CredentialConfigurationVerificationCheckKindV1) == CHECKS
    for contract in (
        ShadowPhase11CredentialConfigurationVerificationRequestV1,
        ShadowPhase11CredentialConfigurationVerificationResultBoundaryV1,
        ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1,
    ):
        assert getattr(contract, "__slots__") and "__dict__" not in contract.__slots__


def test_request_is_secret_free_and_binds_exact_roles_models_checks_and_zero_access():
    request = _request(provider_roles=tuple(reversed(ROLES)), check_kinds=tuple(reversed(CHECKS)), reason_codes=tuple(reversed(REQUEST_REASONS)))
    assert request.provider_roles == ROLES and request.check_kinds == CHECKS
    assert request.reason_codes == REQUEST_REASONS
    assert (request.primary_model_identifier, request.l1_model_identifier, request.l2_model_identifier) == ("deepseek-v4-pro", "claude-sonnet-5", "claude-opus-4-8")
    assert request.verification_descriptor_defined is True
    assert not any(getattr(request, name) for name in (
        "verification_execution_authorized", "credential_reference_access_authorized", "secret_material_access_authorized", "environment_access_authorized", "filesystem_access_authorized", "network_access_authorized", "provider_authentication_probe_authorized", "provider_authentication_request_created", "credential_configuration_write_authorized", "actual_credential_reference_names_present", "secret_material_present",
    ))


def test_result_boundary_is_absent_unexecuted_and_has_no_secret_or_authentication_observation():
    result = _result(reason_codes=tuple(reversed(RESULT_REASONS)))
    assert result.result_state is ShadowPhase11CredentialConfigurationVerificationResultStateV1.RESULT_ABSENT_NOT_EXECUTED
    assert result.reason_codes == RESULT_REASONS
    assert result.result_reference is None and result.result_identity is None
    assert not any(getattr(result, name) for name in (
        "result_present", "verification_started", "verification_completed", "credential_references_resolved", "secret_material_loaded", "environment_configuration_observed", "filesystem_configuration_observed", "primary_provider_configuration_verified", "l1_provider_configuration_verified", "l2_provider_configuration_verified", "secret_material_repository_absence_verified", "runtime_credential_injection_boundary_verified", "provider_authentication_probe_performed", "provider_authentication_observation_present", "provider_authentication_accepted", "all_checks_passed",
    ))


def test_evidence_links_exact_upstreams_and_preserves_unverified_zero_authority():
    evidence = _evidence(reason_codes=tuple(reversed(EVIDENCE_REASONS)))
    assert evidence.locked_repository_baseline == BASELINE and evidence.reason_codes == EVIDENCE_REASONS
    assert evidence.request.identity == _request().identity and evidence.result_boundary.identity == _result().identity
    assert evidence.verification_descriptor_defined is True
    assert evidence.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert evidence.production_effect == "NONE" and evidence.zero_production_proof == "PROVEN_NONE"
    assert not any(getattr(evidence, name) for name in (
        "verification_execution_authorized", "verification_started", "verification_result_present", "verification_completed", "credential_configuration_verified", "credential_reference_access_authorized", "credential_reference_access_observed", "secret_material_access_authorized", "secret_material_access_observed", "secret_material_present", "environment_access_authorized", "environment_access_observed", "filesystem_access_authorized", "filesystem_access_observed", "network_access_authorized", "network_access_observed", "provider_authentication_probe_authorized", "provider_authentication_probe_performed", "provider_authentication_request_created", "provider_authentication_observation_present", "provider_authentication_accepted", "credential_configuration_write_authorized", "credential_configuration_modified", "pricing_revalidation_execution_authorized", "provider_request_created", "pre_call_reservation_created", "ledger_entry_created", "runtime_invocation_authorized", "provider_call_authorized", "provider_transmission_authorized", "run_size_authorized", "manifest_activation_authorized", "launch_authorized", "production_authorized",
    ))


def test_constructors_reject_tampering_unknown_fields_and_all_access_execution_or_result_claims():
    for name, value in (
        ("check_kinds", CHECKS[:-1]), ("check_kinds", CHECKS + (CHECKS[0],)), ("check_kinds", ("UNKNOWN",)), ("provider_roles", ROLES[:-1]), ("provider_roles", (ROLES[0], ROLES[0], ROLES[2])), ("primary_model_identifier", "other"), ("verification_descriptor_defined", False), ("verification_execution_authorized", True), ("credential_reference_access_authorized", True), ("secret_material_access_authorized", True), ("environment_access_authorized", True), ("filesystem_access_authorized", True), ("network_access_authorized", True), ("provider_authentication_probe_authorized", True), ("provider_authentication_request_created", True), ("credential_configuration_write_authorized", True), ("actual_credential_reference_names_present", True), ("secret_material_present", True), ("reason_codes", REQUEST_REASONS[:-1]), ("reason_codes", REQUEST_REASONS + ("UNKNOWN",)), ("request_id", "0" * 64),
    ):
        _reject(_request, **{name: value})
    _reject(_request, unknown_field="reject")
    for name, value in (
        ("result_state", "VERIFIED"), ("result_present", True), ("result_reference", "RESULT"), ("result_identity", "0" * 64), ("verification_started", True), ("verification_completed", True), ("credential_references_resolved", True), ("secret_material_loaded", True), ("environment_configuration_observed", True), ("filesystem_configuration_observed", True), ("primary_provider_configuration_verified", True), ("l1_provider_configuration_verified", True), ("l2_provider_configuration_verified", True), ("secret_material_repository_absence_verified", True), ("runtime_credential_injection_boundary_verified", True), ("provider_authentication_probe_performed", True), ("provider_authentication_observation_present", True), ("provider_authentication_accepted", True), ("all_checks_passed", True), ("reason_codes", RESULT_REASONS[:-1]), ("reason_codes", RESULT_REASONS + ("UNKNOWN",)), ("result_boundary_id", "0" * 64),
    ):
        _reject(_result, **{name: value})
    _reject(_result, unknown_field="reject")
    for name, value in (
        ("locked_repository_baseline", "0" * 40), ("credential_safe_gate_identity", "0" * 64), ("blocked_readiness_reconciliation_identity", "0" * 64), ("current_runtime_integrity_identity", "0" * 64), ("pricing_revalidation_boundary_identity", "0" * 64), ("reservation_bound_identity", "0" * 64), ("boundary_state", "AUTHORIZED"), ("verification_descriptor_defined", False), ("verification_execution_authorized", True), ("credential_configuration_verified", True), ("credential_reference_access_authorized", True), ("secret_material_access_authorized", True), ("environment_access_authorized", True), ("filesystem_access_authorized", True), ("network_access_authorized", True), ("provider_authentication_probe_authorized", True), ("provider_authentication_request_created", True), ("credential_configuration_write_authorized", True), ("pricing_revalidation_execution_authorized", True), ("provider_request_created", True), ("pre_call_reservation_created", True), ("ledger_entry_created", True), ("runtime_invocation_authorized", True), ("provider_call_authorized", True), ("provider_transmission_authorized", True), ("run_size_authorized", True), ("manifest_activation_authorized", True), ("launch_authorized", True), ("production_authorized", True), ("launch_readiness", "READY"), ("production_effect", "SENT"), ("zero_production_proof", "NOT_PROVEN"), ("reason_codes", EVIDENCE_REASONS[:-1]), ("reason_codes", EVIDENCE_REASONS + ("UNKNOWN",)), ("evidence_id", "0" * 64),
    ):
        _reject(_evidence, **{name: value})
    _reject(_evidence, unknown_field="reject")


def test_canonical_identity_converges_diverges_and_future_module_has_no_secret_or_operational_surface():
    first = _evidence(reason_codes=tuple(reversed(EVIDENCE_REASONS)))
    second = _evidence(reason_codes=EVIDENCE_REASONS)
    payload = {name: getattr(first, name) for name in first.__dataclass_fields__ if name != "evidence_id"}
    variant = dict(payload)
    variant["verification_execution_authorized"] = True
    assert first.identity == second.identity
    assert sha256_hex(canonical_json_bytes(payload)) == first.identity
    assert sha256_hex(canonical_json_bytes(variant)) != first.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    evidence = get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1()
    assert evidence.identity == get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1().identity == _evidence().identity
    module = ast.parse(Path(FUTURE_PATH).read_text(encoding="utf-8"))
    forbidden_modules = {"os", "pathlib", "dotenv", "keyring", "requests", "httpx", "urllib", "socket", "subprocess", "threading", "multiprocessing", "concurrent", "asyncio", "pytest", "boto3", "google", "azure", "ccxt"}
    forbidden_names = {"open", "getenv", "environ", "resolve_provider_credential", "material_for_adapter", "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1", "reserve_call", "commit_usage", "sleep", "wait", "float", "now", "utcnow", "time"}
    secret_fragments = {"api_key", "authorization", "bearer", "password", "secret_store", "credential_path", ".env"}
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    strings = {node.value.lower() for node in ast.walk(module) if isinstance(node, ast.Constant) and type(node.value) is str}
    assert not imported & forbidden_modules and not names & forbidden_names
    assert not any(fragment in value for fragment in secret_fragments for value in strings)


def test_public_accessor_type_is_exact():
    assert type(get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1()) is ShadowPhase11CredentialConfigurationVerificationBoundaryEvidenceV1
