"""Immutable Phase 11 zero-reuse pricing-evidence freshness policy.

This module stores static repository-owned policy metadata only. It does not
read a clock, retrieve pricing, access credentials, reserve funds, invoke a
runtime, activate a manifest, or grant operational authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_blocked_readiness_reconciliation_v1 import (
    get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1,
)
from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)


_SCHEMA = "phase11-shadow-pilot-pricing-freshness-policy-v1"
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRICING_FRESHNESS_POLICY_001"
_REPOSITORY_BASELINE = "e896fc134a6b34d8dc146d6f1e307beab032df33"
_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
_PRICING_IDENTITY = (
    "9b986028159efa107da3d2625422ad937d19a65631e5ea95926e006f28329d31"
)
_RECONCILIATION_REFERENCE = (
    "PHASE_11_PILOT_BLOCKED_READINESS_RECONCILIATION_001"
)
_RECONCILIATION_IDENTITY = (
    "4cc8db3264a57480af050d286d9fd1acd5935841f94f4034d7a3cece661a9b4c"
)
_GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
_GATE_IDENTITY = (
    "77b7bbb6782a4710b04abd16547ba5fd94e8311d09cad0cd0187fc7b8313c06b"
)
_REASONS = tuple(
    sorted(
        (
            "ZERO_REUSE_WINDOW_DEFINED",
            "CACHED_PRICING_EVIDENCE_REUSE_NOT_AUTHORIZED",
            "LAUNCH_TIME_PRICING_REVALIDATION_REQUIRED",
            "PRICING_REVALIDATION_NOT_COMPLETED",
            "CURRENT_TIME_ACCESS_NOT_REQUIRED",
            "NO_PRICING_LOOKUP_AUTHORITY",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ShadowPhase11PricingFreshnessPolicyValidationError(ValueError):
    """Raised when static pricing-freshness policy evidence is invalid."""


class ShadowPhase11PricingFreshnessPolicyStateV1(StrEnum):
    """The sole authorized pricing-freshness policy state."""

    ZERO_REUSE_WINDOW_REVALIDATION_REQUIRED = (
        "ZERO_REUSE_WINDOW_REVALIDATION_REQUIRED"
    )


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowPhase11PricingFreshnessPolicyValidationError(
                "canonical Decimal must be finite"
            )
        return _canonical_decimal(value)
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if type(value) in (tuple, list):
        return [_canonical_value(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShadowPhase11PricingFreshnessPolicyValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes."""

    try:
        encoded = json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return b"".join(
            bytes((item,))
            if item < 128
            else f"\\x{item:02x}".encode("ascii")
            for item in encoded
        )
    except (TypeError, ValueError) as error:
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return lowercase SHA-256 for exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            "sha256 input must be bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, field_name: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            f"{field_name} must equal the locked value"
        )


def _exact_false(value: Any, field_name: str) -> None:
    if type(value) is not bool or value is not False:
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            f"{field_name} must remain false"
        )


def _exact_true(value: Any, field_name: str) -> None:
    if type(value) is not bool or value is not True:
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            f"{field_name} must remain true"
        )


def _reason_codes(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            "reason_codes must be a non-empty sequence"
        )
    if any(
        type(code) is not str or _REASON.fullmatch(code) is None
        for code in value
    ):
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            "reason_codes contain invalid values"
        )
    if len(set(value)) != len(value):
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            "reason_codes must be unique"
        )
    normalized = tuple(sorted(value))
    if (
        len(normalized) != len(_REASONS)
        or set(normalized) != set(_REASONS)
    ):
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            "reason_codes must match the exact required set"
        )
    return _REASONS


def _identity_payload(
    evidence: "ShadowPhase11PricingFreshnessPolicyEvidenceV1",
) -> dict[str, Any]:
    return {
        name: getattr(evidence, name)
        for name in evidence.__dataclass_fields__
        if name != "evidence_id"
    }


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11PricingFreshnessPolicyEvidenceV1:
    """Immutable zero-reuse policy with no operational authority."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    pricing_evidence_reference: str
    pricing_evidence_identity: str
    blocked_readiness_reconciliation_reference: str
    blocked_readiness_reconciliation_identity: str
    credential_safe_gate_reference: str
    credential_safe_gate_identity: str
    policy_state: ShadowPhase11PricingFreshnessPolicyStateV1
    maximum_reusable_pricing_evidence_age_seconds: int
    positive_reuse_window_authorized: bool
    cached_pricing_evidence_reusable_without_revalidation: bool
    launch_time_pricing_revalidation_required: bool
    pricing_revalidation_completed: bool
    pricing_revalidation_execution_authorized: bool
    current_time_access_required: bool
    current_time_access_observed: bool
    timestamp_bound: bool
    historical_pricing_evidence_preserved: bool
    historical_pricing_evidence_is_launch_current: bool
    hard_cap_micro_usd: Decimal
    reserve_micro_usd: Decimal
    maximum_spendable_micro_usd: Decimal
    worst_case_routed_item_micro_usd: Decimal
    conservative_candidate_capacity: int
    budget_authority_modified: bool
    pricing_values_revalidated: bool
    provider_model_identifiers_revalidated: bool
    credential_configuration_verified: bool
    pre_call_reservation_created: bool
    ledger_entry_created: bool
    provider_pricing_request_created: bool
    provider_request_created: bool
    runtime_invocation_authorized: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    run_size_authorized: bool
    manifest_activation_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    production_effect: str
    zero_production_effect_proof: str
    reason_codes: tuple[str, ...]

    def __init__(
        self,
        *,
        schema_version: str,
        evidence_id: str | None,
        evidence_reference: str,
        locked_repository_baseline: str,
        locked_phase09_baseline: str,
        pricing_evidence_reference: str,
        pricing_evidence_identity: str,
        blocked_readiness_reconciliation_reference: str,
        blocked_readiness_reconciliation_identity: str,
        credential_safe_gate_reference: str,
        credential_safe_gate_identity: str,
        policy_state: ShadowPhase11PricingFreshnessPolicyStateV1,
        maximum_reusable_pricing_evidence_age_seconds: int,
        positive_reuse_window_authorized: bool,
        cached_pricing_evidence_reusable_without_revalidation: bool,
        launch_time_pricing_revalidation_required: bool,
        pricing_revalidation_completed: bool,
        pricing_revalidation_execution_authorized: bool,
        current_time_access_required: bool,
        current_time_access_observed: bool,
        timestamp_bound: bool,
        historical_pricing_evidence_preserved: bool,
        historical_pricing_evidence_is_launch_current: bool,
        hard_cap_micro_usd: Decimal,
        reserve_micro_usd: Decimal,
        maximum_spendable_micro_usd: Decimal,
        worst_case_routed_item_micro_usd: Decimal,
        conservative_candidate_capacity: int,
        budget_authority_modified: bool,
        pricing_values_revalidated: bool,
        provider_model_identifiers_revalidated: bool,
        credential_configuration_verified: bool,
        pre_call_reservation_created: bool,
        ledger_entry_created: bool,
        provider_pricing_request_created: bool,
        provider_request_created: bool,
        runtime_invocation_authorized: bool,
        provider_call_authorized: bool,
        provider_transmission_authorized: bool,
        run_size_authorized: bool,
        manifest_activation_authorized: bool,
        launch_authorized: bool,
        production_authorized: bool,
        launch_readiness: ShadowPhase11PilotLaunchReadinessV1,
        production_effect: str,
        zero_production_effect_proof: str,
        reason_codes: tuple[str, ...],
        **unknown_fields: Any,
    ) -> None:
        if unknown_fields:
            raise ShadowPhase11PricingFreshnessPolicyValidationError(
                "unknown policy evidence fields are forbidden"
            )
        for field_name, value, expected in (
            ("schema_version", schema_version, _SCHEMA),
            ("evidence_reference", evidence_reference, _EVIDENCE_REFERENCE),
            (
                "locked_repository_baseline",
                locked_repository_baseline,
                _REPOSITORY_BASELINE,
            ),
            (
                "locked_phase09_baseline",
                locked_phase09_baseline,
                _PHASE09_BASELINE,
            ),
            (
                "pricing_evidence_reference",
                pricing_evidence_reference,
                _PRICING_REFERENCE,
            ),
            (
                "pricing_evidence_identity",
                pricing_evidence_identity,
                _PRICING_IDENTITY,
            ),
            (
                "blocked_readiness_reconciliation_reference",
                blocked_readiness_reconciliation_reference,
                _RECONCILIATION_REFERENCE,
            ),
            (
                "blocked_readiness_reconciliation_identity",
                blocked_readiness_reconciliation_identity,
                _RECONCILIATION_IDENTITY,
            ),
            (
                "credential_safe_gate_reference",
                credential_safe_gate_reference,
                _GATE_REFERENCE,
            ),
            (
                "credential_safe_gate_identity",
                credential_safe_gate_identity,
                _GATE_IDENTITY,
            ),
            (
                "hard_cap_micro_usd",
                hard_cap_micro_usd,
                Decimal("5000000"),
            ),
            (
                "reserve_micro_usd",
                reserve_micro_usd,
                Decimal("500000"),
            ),
            (
                "maximum_spendable_micro_usd",
                maximum_spendable_micro_usd,
                Decimal("4500000"),
            ),
            (
                "worst_case_routed_item_micro_usd",
                worst_case_routed_item_micro_usd,
                Decimal("216700"),
            ),
            (
                "conservative_candidate_capacity",
                conservative_candidate_capacity,
                20,
            ),
            ("production_effect", production_effect, "NONE"),
            (
                "zero_production_effect_proof",
                zero_production_effect_proof,
                "PROVEN_NONE",
            ),
        ):
            _exact(value, expected, field_name)
        if (
            type(policy_state)
            is not ShadowPhase11PricingFreshnessPolicyStateV1
            or policy_state
            is not ShadowPhase11PricingFreshnessPolicyStateV1
            .ZERO_REUSE_WINDOW_REVALIDATION_REQUIRED
        ):
            raise ShadowPhase11PricingFreshnessPolicyValidationError(
                "policy_state must be the authorized zero-reuse state"
            )
        if (
            type(maximum_reusable_pricing_evidence_age_seconds) is not int
            or maximum_reusable_pricing_evidence_age_seconds != 0
        ):
            raise ShadowPhase11PricingFreshnessPolicyValidationError(
                "maximum reusable pricing-evidence age must be zero"
            )
        _exact_true(
            launch_time_pricing_revalidation_required,
            "launch_time_pricing_revalidation_required",
        )
        _exact_true(
            historical_pricing_evidence_preserved,
            "historical_pricing_evidence_preserved",
        )
        if (
            type(launch_readiness) is not ShadowPhase11PilotLaunchReadinessV1
            or launch_readiness
            is not ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ):
            raise ShadowPhase11PricingFreshnessPolicyValidationError(
                "launch readiness must remain blocked"
            )
        for field_name, value in (
            (
                "positive_reuse_window_authorized",
                positive_reuse_window_authorized,
            ),
            (
                "cached_pricing_evidence_reusable_without_revalidation",
                cached_pricing_evidence_reusable_without_revalidation,
            ),
            (
                "pricing_revalidation_completed",
                pricing_revalidation_completed,
            ),
            (
                "pricing_revalidation_execution_authorized",
                pricing_revalidation_execution_authorized,
            ),
            ("current_time_access_required", current_time_access_required),
            ("current_time_access_observed", current_time_access_observed),
            ("timestamp_bound", timestamp_bound),
            (
                "historical_pricing_evidence_is_launch_current",
                historical_pricing_evidence_is_launch_current,
            ),
            ("budget_authority_modified", budget_authority_modified),
            ("pricing_values_revalidated", pricing_values_revalidated),
            (
                "provider_model_identifiers_revalidated",
                provider_model_identifiers_revalidated,
            ),
            (
                "credential_configuration_verified",
                credential_configuration_verified,
            ),
            (
                "pre_call_reservation_created",
                pre_call_reservation_created,
            ),
            ("ledger_entry_created", ledger_entry_created),
            (
                "provider_pricing_request_created",
                provider_pricing_request_created,
            ),
            ("provider_request_created", provider_request_created),
            (
                "runtime_invocation_authorized",
                runtime_invocation_authorized,
            ),
            ("provider_call_authorized", provider_call_authorized),
            (
                "provider_transmission_authorized",
                provider_transmission_authorized,
            ),
            ("run_size_authorized", run_size_authorized),
            (
                "manifest_activation_authorized",
                manifest_activation_authorized,
            ),
            ("launch_authorized", launch_authorized),
            ("production_authorized", production_authorized),
        ):
            _exact_false(value, field_name)
        normalized_reasons = _reason_codes(reason_codes)
        values = {
            "schema_version": schema_version,
            "evidence_reference": evidence_reference,
            "locked_repository_baseline": locked_repository_baseline,
            "locked_phase09_baseline": locked_phase09_baseline,
            "pricing_evidence_reference": pricing_evidence_reference,
            "pricing_evidence_identity": pricing_evidence_identity,
            "blocked_readiness_reconciliation_reference": (
                blocked_readiness_reconciliation_reference
            ),
            "blocked_readiness_reconciliation_identity": (
                blocked_readiness_reconciliation_identity
            ),
            "credential_safe_gate_reference": (
                credential_safe_gate_reference
            ),
            "credential_safe_gate_identity": credential_safe_gate_identity,
            "policy_state": policy_state,
            "maximum_reusable_pricing_evidence_age_seconds": (
                maximum_reusable_pricing_evidence_age_seconds
            ),
            "positive_reuse_window_authorized": (
                positive_reuse_window_authorized
            ),
            "cached_pricing_evidence_reusable_without_revalidation": (
                cached_pricing_evidence_reusable_without_revalidation
            ),
            "launch_time_pricing_revalidation_required": (
                launch_time_pricing_revalidation_required
            ),
            "pricing_revalidation_completed": pricing_revalidation_completed,
            "pricing_revalidation_execution_authorized": (
                pricing_revalidation_execution_authorized
            ),
            "current_time_access_required": current_time_access_required,
            "current_time_access_observed": current_time_access_observed,
            "timestamp_bound": timestamp_bound,
            "historical_pricing_evidence_preserved": (
                historical_pricing_evidence_preserved
            ),
            "historical_pricing_evidence_is_launch_current": (
                historical_pricing_evidence_is_launch_current
            ),
            "hard_cap_micro_usd": hard_cap_micro_usd,
            "reserve_micro_usd": reserve_micro_usd,
            "maximum_spendable_micro_usd": maximum_spendable_micro_usd,
            "worst_case_routed_item_micro_usd": (
                worst_case_routed_item_micro_usd
            ),
            "conservative_candidate_capacity": (
                conservative_candidate_capacity
            ),
            "budget_authority_modified": budget_authority_modified,
            "pricing_values_revalidated": pricing_values_revalidated,
            "provider_model_identifiers_revalidated": (
                provider_model_identifiers_revalidated
            ),
            "credential_configuration_verified": (
                credential_configuration_verified
            ),
            "pre_call_reservation_created": pre_call_reservation_created,
            "ledger_entry_created": ledger_entry_created,
            "provider_pricing_request_created": (
                provider_pricing_request_created
            ),
            "provider_request_created": provider_request_created,
            "runtime_invocation_authorized": runtime_invocation_authorized,
            "provider_call_authorized": provider_call_authorized,
            "provider_transmission_authorized": (
                provider_transmission_authorized
            ),
            "run_size_authorized": run_size_authorized,
            "manifest_activation_authorized": (
                manifest_activation_authorized
            ),
            "launch_authorized": launch_authorized,
            "production_authorized": production_authorized,
            "launch_readiness": launch_readiness,
            "production_effect": production_effect,
            "zero_production_effect_proof": zero_production_effect_proof,
            "reason_codes": normalized_reasons,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)
        computed = sha256_hex(canonical_json_bytes(_identity_payload(self)))
        if (
            evidence_id is not None
            and (type(evidence_id) is not str or evidence_id != computed)
        ):
            raise ShadowPhase11PricingFreshnessPolicyValidationError(
                "evidence_id does not match canonical material"
            )
        if _HASH.fullmatch(computed) is None:
            raise ShadowPhase11PricingFreshnessPolicyValidationError(
                "evidence identity computation failed"
            )
        object.__setattr__(self, "evidence_id", computed)

    @property
    def identity(self) -> str:
        return self.evidence_id


def _make_evidence() -> ShadowPhase11PricingFreshnessPolicyEvidenceV1:
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reconciliation = (
        get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    )
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    if (
        pricing.fixed_freshness_window_defined is not False
        or pricing.launch_time_pricing_revalidation_required is not True
    ):
        raise ShadowPhase11PricingFreshnessPolicyValidationError(
            "historical pricing freshness facts changed"
        )
    return ShadowPhase11PricingFreshnessPolicyEvidenceV1(
        schema_version=_SCHEMA,
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        locked_repository_baseline=_REPOSITORY_BASELINE,
        locked_phase09_baseline=_PHASE09_BASELINE,
        pricing_evidence_reference=pricing.evidence_reference,
        pricing_evidence_identity=pricing.identity,
        blocked_readiness_reconciliation_reference=(
            reconciliation.evidence_reference
        ),
        blocked_readiness_reconciliation_identity=reconciliation.identity,
        credential_safe_gate_reference=gate.evidence_reference,
        credential_safe_gate_identity=gate.identity,
        policy_state=(
            ShadowPhase11PricingFreshnessPolicyStateV1
            .ZERO_REUSE_WINDOW_REVALIDATION_REQUIRED
        ),
        maximum_reusable_pricing_evidence_age_seconds=0,
        positive_reuse_window_authorized=False,
        cached_pricing_evidence_reusable_without_revalidation=False,
        launch_time_pricing_revalidation_required=True,
        pricing_revalidation_completed=False,
        pricing_revalidation_execution_authorized=False,
        current_time_access_required=False,
        current_time_access_observed=False,
        timestamp_bound=False,
        historical_pricing_evidence_preserved=True,
        historical_pricing_evidence_is_launch_current=False,
        hard_cap_micro_usd=pricing.hard_cap_micro_usd,
        reserve_micro_usd=pricing.safety_reserve_micro_usd,
        maximum_spendable_micro_usd=pricing.spendable_cap_micro_usd,
        worst_case_routed_item_micro_usd=(
            pricing.conservative_worst_case_item_cost_micro_usd
        ),
        conservative_candidate_capacity=(
            pricing.mathematical_safe_maximum_items
        ),
        budget_authority_modified=False,
        pricing_values_revalidated=False,
        provider_model_identifiers_revalidated=False,
        credential_configuration_verified=False,
        pre_call_reservation_created=False,
        ledger_entry_created=False,
        provider_pricing_request_created=False,
        provider_request_created=False,
        runtime_invocation_authorized=False,
        provider_call_authorized=False,
        provider_transmission_authorized=False,
        run_size_authorized=False,
        manifest_activation_authorized=False,
        launch_authorized=False,
        production_authorized=False,
        launch_readiness=(
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
        reason_codes=_REASONS,
    )


_EVIDENCE = _make_evidence()


def get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1(
) -> ShadowPhase11PricingFreshnessPolicyEvidenceV1:
    """Return the immutable zero-reuse pricing-freshness policy."""

    return _EVIDENCE


__all__ = (
    "ShadowPhase11PricingFreshnessPolicyEvidenceV1",
    "ShadowPhase11PricingFreshnessPolicyStateV1",
    "ShadowPhase11PricingFreshnessPolicyValidationError",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1",
    "sha256_hex",
)
