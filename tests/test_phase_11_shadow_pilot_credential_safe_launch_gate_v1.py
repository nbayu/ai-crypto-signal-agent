"""RED contract for immutable Phase 11 credential-safe launch-gate evidence.

The future contract records a blocked, secret-free launch posture only.  It
must not resolve credentials, inspect configuration, contact providers, or
create any reservation, manifest, launch, or production authority.
"""

from __future__ import annotations

import ast
import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotPricingRevalidationStatusV1,
    ShadowPhase11PilotProviderRoleV1,
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    ShadowPhase11PreCallReservationStateV1,
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)
from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    ShadowPhase11CredentialRequirementV1,
    ShadowPhase11CredentialSafeLaunchGateStateV1,
    ShadowPhase11CredentialSafeLaunchGateV1,
    ShadowPhase11CredentialSafeLaunchGateValidationError,
    ShadowPhase11CredentialVerificationStateV1,
    canonical_json_bytes,
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
    sha256_hex,
)


LOCKED_REPOSITORY_BASELINE = "5ec5c39b542a573a142eff60c8c9bbc1ec7925b3"
LOCKED_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"
EVIDENCE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
PRICING_EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
RESERVATION_BOUND_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
BUDGET_AUTHORIZATION_REFERENCE = "PHASE_11_SHADOW_PILOT_BUDGET_USD_5_001"
MODEL_COST_AUTHORIZATION_REFERENCE = "PHASE_11_PILOT_MODEL_COST_BOUNDS_001"
ZERO_MICRO_USD = Decimal("0")
BLOCKERS = (
    "AUTHENTICATION_TERMINAL_CLASSIFICATION_NOT_VERIFIED",
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "PILOT_INPUT_ABSENT",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "RUN_MANIFEST_ABSENT",
    "RUNTIME_NO_RETRY_ENFORCEMENT_NOT_VERIFIED",
)


def _pricing_evidence():
    return get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()


def _reservation_bound():
    return get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()


def _requirement(provider: str = "DEEPSEEK", **overrides: object):
    template = {
        "DEEPSEEK": (ShadowPhase11PilotProviderRoleV1.PRIMARY,),
        "ANTHROPIC": (
            ShadowPhase11PilotProviderRoleV1.L1,
            ShadowPhase11PilotProviderRoleV1.L2,
        ),
    }
    values = {
        "schema_version": "phase11-shadow-pilot-credential-requirement-v1",
        "requirement_id": None,
        "provider": provider,
        "roles": template.get(provider, template["DEEPSEEK"]),
        "credential_required": True,
        "verification_state": ShadowPhase11CredentialVerificationStateV1.NOT_VERIFIED,
        "credential_reference_present": False,
        "credential_material_present": False,
        "credential_access_attempted": False,
        "account_access_attempted": False,
        "credential_validation_endpoint_called": False,
        "provider_call_authorized": False,
        "maximum_attempts": 1,
        "provider_retry_authorized": False,
        "credential_retry_authorized": False,
        "authentication_retry_authorized": False,
        "credential_failure_terminal_required": True,
        "authentication_failure_terminal_required": True,
        "reason_codes": ("CREDENTIAL_CONFIGURATION_NOT_VERIFIED",),
    }
    values.update(overrides)
    return ShadowPhase11CredentialRequirementV1(**values)


def _reject_requirement(provider: str = "DEEPSEEK", **overrides: object):
    with pytest.raises(ShadowPhase11CredentialSafeLaunchGateValidationError):
        _requirement(provider, **overrides)


def _gate(**overrides: object):
    pricing = _pricing_evidence()
    reservation = _reservation_bound()
    values = {
        "schema_version": "phase11-shadow-pilot-credential-safe-launch-gate-v1",
        "gate_id": None,
        "evidence_reference": EVIDENCE_REFERENCE,
        "pricing_evidence_reference": pricing.evidence_reference,
        "pricing_evidence_identity": pricing.identity,
        "reservation_bound_reference": reservation.evidence_reference,
        "reservation_bound_identity": reservation.identity,
        "budget_authorization_reference": BUDGET_AUTHORIZATION_REFERENCE,
        "model_cost_authorization_reference": MODEL_COST_AUTHORIZATION_REFERENCE,
        "locked_repository_baseline": LOCKED_REPOSITORY_BASELINE,
        "locked_phase09_baseline": LOCKED_PHASE09_BASELINE,
        "credential_requirements": (_requirement("DEEPSEEK"), _requirement("ANTHROPIC")),
        "gate_state": ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED,
        "credential_configuration_verified": False,
        "credential_material_accessed": False,
        "account_state_accessed": False,
        "credential_validation_endpoint_called": False,
        "provider_call_authorized": False,
        "provider_transmission_authorized": False,
        "run_size_authorized": False,
        "reservation_creation_authorized": False,
        "ledger_mutation_authorized": False,
        "launch_authorized": False,
        "production_authorized": False,
        "maximum_attempts": 1,
        "provider_retry_authorized": False,
        "credential_retry_authorized": False,
        "authentication_retry_authorized": False,
        "credential_failure_terminal_required": True,
        "authentication_failure_terminal_required": True,
        "pricing_revalidation_required_before_reservation_use": True,
        "launch_time_pricing_revalidation_required": True,
        "fixed_freshness_window_defined": False,
        "pricing_revalidation_status": pricing.pricing_revalidation_status,
        "reservation_state": reservation.reservation_state,
        "reservation_required_before_provider_transmission": True,
        "budget_reserved_micro_usd": ZERO_MICRO_USD,
        "budget_consumed_micro_usd": ZERO_MICRO_USD,
        "pilot_input_present": False,
        "run_manifest_present": False,
        "runtime_no_retry_enforcement_verified": False,
        "authentication_terminal_classification_verified": False,
        "launch_readiness": pricing.launch_readiness,
        "production_effect": pricing.production_effect,
        "zero_production_effect_proof": pricing.zero_production_effect_proof,
        "blocker_codes": BLOCKERS,
        "reason_codes": ("CREDENTIAL_SAFE_GATE_BLOCKED",),
    }
    values.update(overrides)
    return ShadowPhase11CredentialSafeLaunchGateV1(**values)


def _reject_gate(**overrides: object):
    with pytest.raises(ShadowPhase11CredentialSafeLaunchGateValidationError):
        _gate(**overrides)


def test_closed_gate_and_verification_enums_are_blocked_only():
    assert tuple(ShadowPhase11CredentialVerificationStateV1) == (
        ShadowPhase11CredentialVerificationStateV1.NOT_VERIFIED,
    )
    assert tuple(ShadowPhase11CredentialSafeLaunchGateStateV1) == (
        ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED,
    )
    assert ShadowPhase11CredentialVerificationStateV1.NOT_VERIFIED.value == "NOT_VERIFIED"
    assert ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED.value == "BLOCKED"


def test_exact_secret_free_deepseek_and_anthropic_requirements_are_immutable():
    deepseek = _requirement("DEEPSEEK")
    anthropic = _requirement("ANTHROPIC")
    assert deepseek.provider == "DEEPSEEK"
    assert deepseek.roles == (ShadowPhase11PilotProviderRoleV1.PRIMARY,)
    assert anthropic.provider == "ANTHROPIC"
    assert anthropic.roles == (
        ShadowPhase11PilotProviderRoleV1.L1,
        ShadowPhase11PilotProviderRoleV1.L2,
    )
    assert _requirement(
        "ANTHROPIC",
        roles=(
            ShadowPhase11PilotProviderRoleV1.L2,
            ShadowPhase11PilotProviderRoleV1.L1,
        ),
    ).identity == anthropic.identity
    for requirement in (deepseek, anthropic):
        assert requirement.credential_required is True
        assert requirement.verification_state is ShadowPhase11CredentialVerificationStateV1.NOT_VERIFIED
        assert requirement.maximum_attempts == 1
        assert requirement.credential_failure_terminal_required is True
        assert requirement.authentication_failure_terminal_required is True
        assert not any((
            requirement.credential_reference_present,
            requirement.credential_material_present,
            requirement.credential_access_attempted,
            requirement.account_access_attempted,
            requirement.credential_validation_endpoint_called,
            requirement.provider_call_authorized,
            requirement.provider_retry_authorized,
            requirement.credential_retry_authorized,
            requirement.authentication_retry_authorized,
        ))
    forbidden_fields = {
        "api_key", "token", "secret", "credential_value", "password",
        "authorization_header", "environment_variable_name", "secret_store_path",
        "account_id", "organization_id", "project_id",
    }
    assert not set(deepseek.__dataclass_fields__) & forbidden_fields
    with pytest.raises((AttributeError, TypeError)):
        deepseek.provider = "ANTHROPIC"


def test_requirement_constructor_rejects_role_access_retry_terminal_and_identity_tampering():
    _reject_requirement("UNKNOWN")
    _reject_requirement("DEEPSEEK", roles=(ShadowPhase11PilotProviderRoleV1.L1,))
    _reject_requirement("ANTHROPIC", roles=(ShadowPhase11PilotProviderRoleV1.PRIMARY,))
    _reject_requirement("DEEPSEEK", roles=())
    _reject_requirement("ANTHROPIC", roles=(ShadowPhase11PilotProviderRoleV1.L1, ShadowPhase11PilotProviderRoleV1.L1))
    _reject_requirement("DEEPSEEK", roles=("UNKNOWN",))
    _reject_requirement(verification_state="VERIFIED")
    for name in (
        "credential_reference_present", "credential_material_present",
        "credential_access_attempted", "account_access_attempted",
        "credential_validation_endpoint_called", "provider_call_authorized",
        "provider_retry_authorized", "credential_retry_authorized",
        "authentication_retry_authorized",
    ):
        _reject_requirement(**{name: True})
    _reject_requirement(maximum_attempts=2)
    _reject_requirement(credential_failure_terminal_required=False)
    _reject_requirement(authentication_failure_terminal_required=False)
    _reject_requirement(requirement_id="0" * 64)
    _reject_requirement(api_key="reject")


def test_concrete_gate_links_committed_evidence_and_retains_exact_blockers():
    pricing = _pricing_evidence()
    reservation = _reservation_bound()
    gate = _gate()
    assert gate.evidence_reference == EVIDENCE_REFERENCE
    assert gate.pricing_evidence_reference == pricing.evidence_reference == PRICING_EVIDENCE_REFERENCE
    assert gate.pricing_evidence_identity == pricing.identity
    assert gate.reservation_bound_reference == reservation.evidence_reference == RESERVATION_BOUND_REFERENCE
    assert gate.reservation_bound_identity == reservation.identity
    assert gate.budget_authorization_reference == BUDGET_AUTHORIZATION_REFERENCE
    assert gate.model_cost_authorization_reference == MODEL_COST_AUTHORIZATION_REFERENCE
    assert gate.locked_repository_baseline == LOCKED_REPOSITORY_BASELINE
    assert gate.locked_phase09_baseline == LOCKED_PHASE09_BASELINE
    assert gate.gate_state is ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED
    assert gate.credential_requirements == (_requirement("DEEPSEEK"), _requirement("ANTHROPIC"))
    assert gate.blocker_codes == BLOCKERS
    assert gate.pricing_revalidation_status is ShadowPhase11PilotPricingRevalidationStatusV1.REQUIRED_NOT_COMPLETED
    assert gate.reservation_state is ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED
    assert gate.launch_readiness is ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
    assert gate.budget_reserved_micro_usd == gate.budget_consumed_micro_usd == ZERO_MICRO_USD
    assert gate.production_effect == "NONE"
    assert gate.zero_production_effect_proof == "PROVEN_NONE"
    assert gate.runtime_no_retry_enforcement_verified is False
    assert gate.authentication_terminal_classification_verified is False


def test_gate_rejects_evidence_state_blocker_authority_and_input_tampering():
    _reject_gate(pricing_evidence_reference="PHASE_11_OTHER_PRICING_EVIDENCE_001")
    _reject_gate(pricing_evidence_identity="0" * 64)
    _reject_gate(reservation_bound_reference="PHASE_11_OTHER_RESERVATION_BOUND_001")
    _reject_gate(reservation_bound_identity="0" * 64)
    _reject_gate(locked_repository_baseline="0" * 40)
    _reject_gate(credential_requirements=(_requirement("ANTHROPIC"),))
    _reject_gate(credential_requirements=(_requirement("DEEPSEEK"),))
    _reject_gate(credential_requirements=(_requirement("DEEPSEEK"), _requirement("DEEPSEEK")))
    _reject_gate(gate_state="READY")
    _reject_gate(pricing_revalidation_status="COMPLETED")
    _reject_gate(reservation_state="RESERVED")
    _reject_gate(reservation_required_before_provider_transmission=False)
    _reject_gate(launch_time_pricing_revalidation_required=False)
    _reject_gate(pricing_revalidation_required_before_reservation_use=False)
    _reject_gate(fixed_freshness_window_defined=True)
    _reject_gate(budget_reserved_micro_usd=Decimal("1"))
    _reject_gate(budget_consumed_micro_usd=Decimal("1"))
    _reject_gate(credential_configuration_verified=True)
    _reject_gate(credential_material_accessed=True)
    _reject_gate(account_state_accessed=True)
    _reject_gate(credential_validation_endpoint_called=True)
    _reject_gate(runtime_no_retry_enforcement_verified=True)
    _reject_gate(authentication_terminal_classification_verified=True)
    _reject_gate(maximum_attempts=2)
    _reject_gate(provider_retry_authorized=True)
    _reject_gate(credential_retry_authorized=True)
    _reject_gate(authentication_retry_authorized=True)
    _reject_gate(credential_failure_terminal_required=False)
    _reject_gate(authentication_failure_terminal_required=False)
    _reject_gate(pilot_input_present=True)
    _reject_gate(run_manifest_present=True)
    for name in (
        "provider_call_authorized", "provider_transmission_authorized",
        "run_size_authorized", "reservation_creation_authorized",
        "ledger_mutation_authorized", "launch_authorized", "production_authorized",
    ):
        _reject_gate(**{name: True})
    _reject_gate(launch_readiness="READY_FOR_LAUNCH")
    _reject_gate(production_effect="SENT")
    _reject_gate(zero_production_effect_proof="UNPROVEN")
    _reject_gate(blocker_codes=BLOCKERS[:-1])
    _reject_gate(blocker_codes=BLOCKERS + (BLOCKERS[0],))
    _reject_gate(blocker_codes=BLOCKERS + ("UNKNOWN_BLOCKER",))
    _reject_gate(gate_id="0" * 64)
    _reject_gate(unknown_field="reject")


def test_parent_requirement_order_and_reason_order_converge_and_material_changes_diverge():
    requirements = (_requirement("DEEPSEEK"), _requirement("ANTHROPIC"))
    first = _gate(
        credential_requirements=requirements,
        blocker_codes=BLOCKERS,
        reason_codes=("CREDENTIAL_GATE", "LAUNCH_BLOCKED"),
    )
    second = _gate(
        credential_requirements=tuple(reversed(requirements)),
        blocker_codes=tuple(reversed(BLOCKERS)),
        reason_codes=("LAUNCH_BLOCKED", "CREDENTIAL_GATE"),
    )
    variant = _gate(reason_codes=("CREDENTIAL_GATE_VARIANT",))
    assert first.identity == second.identity
    assert first.identity != variant.identity
    assert canonical_json_bytes({"b": "é", "a": 1}) == b'{"a":1,"b":"\\xc3\\xa9"}'
    assert sha256_hex(b"credential-safe-launch-gate") == hashlib.sha256(b"credential-safe-launch-gate").hexdigest()


def test_zero_argument_accessor_is_deterministic_and_remains_blocked():
    first = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    second = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    assert type(first) is ShadowPhase11CredentialSafeLaunchGateV1
    assert first.identity == second.identity == _gate().identity
    assert first.pricing_evidence_identity == _pricing_evidence().identity
    assert first.reservation_bound_identity == _reservation_bound().identity
    assert first.gate_state is ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED


def test_static_dependency_secret_and_side_effect_boundary():
    module = ast.parse(Path("engine/phase_11_shadow_pilot_credential_safe_launch_gate_v1.py").read_text(encoding="utf-8"))
    forbidden_modules = {
        "os", "pathlib", "dotenv", "requests", "httpx", "urllib", "socket",
        "subprocess", "threading", "multiprocessing", "concurrent", "asyncio",
        "pytest", "keyring", "boto3", "google", "azure", "ccxt",
    }
    forbidden_names = {
        "open", "getenv", "environ", "load_dotenv", "dotenv_values",
        "resolve_provider_credential", "material_for_adapter", "requests", "http",
        "DeepSeekShadowTransportAdapterV1", "AnthropicShadowTransportAdapterV1",
        "ShadowProviderRuntimeV1", "ShadowProviderRunOrchestratorV1", "reserve_call",
        "commit_usage", "release_reservation", "reconcile_uncertain_usage", "telegram",
        "account", "exchange", "order", "position", "trading", "publication",
        "deployment", "persistence", "datetime_now", "utcnow", "float",
    }
    imported = {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module}
    imported |= {alias.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names}
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)}
    assert not imported & forbidden_modules
    assert not names & forbidden_names
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.With)) for node in ast.walk(module))
