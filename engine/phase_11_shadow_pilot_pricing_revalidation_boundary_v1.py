"""Immutable static Phase 11 pricing-revalidation request/result boundary."""

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
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)
from engine.phase_11_shadow_pilot_pricing_freshness_policy_v1 import (
    get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1,
)


_BASELINE = "a664af4f6efdc32e1b669bc9931d5850ae5c9a3f"
_PHASE09 = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_REQUEST_REFERENCE = "PHASE_11_PILOT_PRICING_REVALIDATION_REQUEST_001"
_RESULT_REFERENCE = (
    "PHASE_11_PILOT_PRICING_REVALIDATION_RESULT_BOUNDARY_001"
)
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001"
_POLICY_REFERENCE = "PHASE_11_PILOT_PRICING_FRESHNESS_POLICY_001"
_POLICY_IDENTITY = (
    "2e63c1ee2b4912d9361a1b4793fbb1f866bdada4bbfd89a1691074d92757d603"
)
_PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
_PRICING_IDENTITY = (
    "2ffbb1d04538bbf481d287b9629757fcde17a3d59779a1cef367e1752d673014"
)
_RECONCILIATION_REFERENCE = (
    "PHASE_11_PILOT_BLOCKED_READINESS_RECONCILIATION_001"
)
_RECONCILIATION_IDENTITY = (
    "92e9773c94cf8263202976e9c6d6f9c62a7e66b8de59ada63992056a4e9a2bd0"
)
_GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
_GATE_IDENTITY = (
    "29a07dc2cb644aeb4dbdc9dc00e4da79b5fa3d1486e98dabdcadb1e40140debb"
)
_RESERVATION_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
_RESERVATION_IDENTITY = (
    "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4"
)
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")

_REQUEST_REASONS = tuple(
    sorted(
        (
            "EXACT_REVALIDATION_CHECKS_DEFINED",
            "NO_CREDENTIAL_AUTHORITY",
            "NO_CURRENT_TIME_AUTHORITY",
            "NO_NETWORK_AUTHORITY",
            "NO_PROVIDER_PRICING_REQUEST",
            "PRICING_REVALIDATION_EXECUTION_NOT_AUTHORIZED",
            "REPOSITORY_OWNED_REQUEST_DESCRIPTOR",
        )
    )
)
_RESULT_REASONS = tuple(
    sorted(
        (
            "NO_FRESH_SOURCE_OBSERVATION",
            "NO_RESULT_IDENTITY",
            "NO_RESULT_REFERENCE",
            "PRICING_REVALIDATION_NOT_STARTED",
            "RESULT_ABSENT_NOT_EXECUTED",
        )
    )
)
_EVIDENCE_REASONS = tuple(
    sorted(
        (
            "NO_OPERATIONAL_AUTHORITY",
            "NO_PRICING_LOOKUP_AUTHORITY",
            "PRICING_REVALIDATION_EXECUTION_NOT_AUTHORIZED",
            "PRICING_REVALIDATION_INCOMPLETE",
            "PRICING_REVALIDATION_REQUEST_DEFINED",
            "PRICING_REVALIDATION_RESULT_ABSENT",
            "ZERO_REUSE_POLICY_ACTIVE",
        )
    )
)


class ShadowPhase11PricingRevalidationBoundaryValidationError(ValueError):
    """Raised when static pricing-revalidation boundary evidence is invalid."""


class ShadowPhase11PricingRevalidationBoundaryStateV1(StrEnum):
    REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED = (
        "REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED"
    )


class ShadowPhase11PricingRevalidationResultStateV1(StrEnum):
    RESULT_ABSENT_NOT_EXECUTED = "RESULT_ABSENT_NOT_EXECUTED"


class ShadowPhase11PricingRevalidationCheckKindV1(StrEnum):
    PROVIDER_MODEL_IDENTIFIERS = "PROVIDER_MODEL_IDENTIFIERS"
    PROVIDER_CONTEXT_AND_OUTPUT_LIMITS = "PROVIDER_CONTEXT_AND_OUTPUT_LIMITS"
    PROVIDER_INPUT_AND_OUTPUT_PRICING = "PROVIDER_INPUT_AND_OUTPUT_PRICING"
    WORST_CASE_ROUTE_COST = "WORST_CASE_ROUTE_COST"
    CONSERVATIVE_CANDIDATE_CAPACITY = "CONSERVATIVE_CANDIDATE_CAPACITY"


_CHECKS = tuple(ShadowPhase11PricingRevalidationCheckKindV1)


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ShadowPhase11PricingRevalidationBoundaryValidationError(
                "canonical Decimal must be finite"
            )
        return _canonical_decimal(value)
    if type(value) in (
        ShadowPhase11PricingRevalidationRequestV1,
        ShadowPhase11PricingRevalidationResultBoundaryV1,
    ):
        return value.identity
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
    raise ShadowPhase11PricingRevalidationBoundaryValidationError(
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
        raise ShadowPhase11PricingRevalidationBoundaryValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    if type(value) is not bytes:
        raise ShadowPhase11PricingRevalidationBoundaryValidationError(
            "sha256 input must be bytes"
        )
    return sha256(value).hexdigest()


def _exact_fields(
    values: dict[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    if frozenset(values) != expected:
        raise ShadowPhase11PricingRevalidationBoundaryValidationError(
            f"invalid {label} fields"
        )


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11PricingRevalidationBoundaryValidationError(
            f"invalid {label}"
        )
    return value


def _false(value: Any, label: str) -> bool:
    return _exact(value, False, label)


def _true(value: Any, label: str) -> bool:
    return _exact(value, True, label)


def _codes(value: Any, expected: tuple[str, ...], label: str) -> tuple[str, ...]:
    if (
        type(value) not in (tuple, list)
        or any(
            type(item) is not str or _REASON.fullmatch(item) is None
            for item in value
        )
        or len(set(value)) != len(value)
        or len(value) != len(expected)
        or set(value) != set(expected)
    ):
        raise ShadowPhase11PricingRevalidationBoundaryValidationError(
            f"invalid {label}"
        )
    return expected


def _checks(value: Any) -> tuple[ShadowPhase11PricingRevalidationCheckKindV1, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(_CHECKS)
        or any(
            type(item) is not ShadowPhase11PricingRevalidationCheckKindV1
            for item in value
        )
        or len(set(value)) != len(value)
        or set(value) != set(_CHECKS)
    ):
        raise ShadowPhase11PricingRevalidationBoundaryValidationError(
            "invalid check_kinds"
        )
    return _CHECKS


def _identity(
    instance: Any,
    identity_field: str,
    supplied: Any,
) -> str:
    payload = {
        name: getattr(instance, name)
        for name in instance.__dataclass_fields__
        if name != identity_field
    }
    computed = sha256_hex(canonical_json_bytes(payload))
    if (
        supplied is not None
        and (type(supplied) is not str or supplied != computed)
    ):
        raise ShadowPhase11PricingRevalidationBoundaryValidationError(
            f"{identity_field} does not match canonical material"
        )
    if _HASH.fullmatch(computed) is None:
        raise ShadowPhase11PricingRevalidationBoundaryValidationError(
            "identity computation failed"
        )
    object.__setattr__(instance, identity_field, computed)
    return computed


_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "request_reference",
        "pricing_freshness_policy_reference",
        "pricing_freshness_policy_identity",
        "pricing_evidence_reference",
        "pricing_evidence_identity",
        "check_kinds",
        "primary_model_identifier",
        "l1_model_identifier",
        "l2_model_identifier",
        "maximum_input_tokens",
        "maximum_output_tokens",
        "maximum_attempts",
        "hard_cap_micro_usd",
        "reserve_micro_usd",
        "maximum_spendable_micro_usd",
        "worst_case_routed_item_micro_usd",
        "conservative_candidate_capacity",
        "request_defined",
        "execution_authorized",
        "network_access_authorized",
        "credential_access_authorized",
        "current_time_access_authorized",
        "provider_pricing_request_created",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11PricingRevalidationRequestV1:
    schema_version: str
    request_id: str
    request_reference: str
    pricing_freshness_policy_reference: str
    pricing_freshness_policy_identity: str
    pricing_evidence_reference: str
    pricing_evidence_identity: str
    check_kinds: tuple[ShadowPhase11PricingRevalidationCheckKindV1, ...]
    primary_model_identifier: str
    l1_model_identifier: str
    l2_model_identifier: str
    maximum_input_tokens: int
    maximum_output_tokens: int
    maximum_attempts: int
    hard_cap_micro_usd: Decimal
    reserve_micro_usd: Decimal
    maximum_spendable_micro_usd: Decimal
    worst_case_routed_item_micro_usd: Decimal
    conservative_candidate_capacity: int
    request_defined: bool
    execution_authorized: bool
    network_access_authorized: bool
    credential_access_authorized: bool
    current_time_access_authorized: bool
    provider_pricing_request_created: bool
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _REQUEST_FIELDS, "request")
        normalized = dict(values)
        for name, expected in (
            ("schema_version", "phase11-shadow-pilot-pricing-revalidation-request-v1"),
            ("request_reference", _REQUEST_REFERENCE),
            ("pricing_freshness_policy_reference", _POLICY_REFERENCE),
            ("pricing_freshness_policy_identity", _POLICY_IDENTITY),
            ("pricing_evidence_reference", _PRICING_REFERENCE),
            ("pricing_evidence_identity", _PRICING_IDENTITY),
            ("primary_model_identifier", "deepseek-v4-pro"),
            ("l1_model_identifier", "claude-sonnet-5"),
            ("l2_model_identifier", "claude-opus-4-8"),
            ("maximum_input_tokens", 16000),
            ("maximum_output_tokens", 2000),
            ("maximum_attempts", 1),
            ("hard_cap_micro_usd", Decimal("5000000")),
            ("reserve_micro_usd", Decimal("500000")),
            ("maximum_spendable_micro_usd", Decimal("4500000")),
            ("worst_case_routed_item_micro_usd", Decimal("216700")),
            ("conservative_candidate_capacity", 20),
        ):
            normalized[name] = _exact(values[name], expected, name)
        normalized["check_kinds"] = _checks(values["check_kinds"])
        normalized["request_defined"] = _true(
            values["request_defined"], "request_defined"
        )
        for name in (
            "execution_authorized",
            "network_access_authorized",
            "credential_access_authorized",
            "current_time_access_authorized",
            "provider_pricing_request_created",
        ):
            normalized[name] = _false(values[name], name)
        normalized["reason_codes"] = _codes(
            values["reason_codes"], _REQUEST_REASONS, "request reason_codes"
        )
        supplied = values["request_id"]
        for name in self.__dataclass_fields__:
            if name != "request_id":
                object.__setattr__(self, name, normalized[name])
        _identity(self, "request_id", supplied)

    @property
    def identity(self) -> str:
        return self.request_id


_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "result_boundary_id",
        "result_boundary_reference",
        "request_reference",
        "request_identity",
        "result_state",
        "result_present",
        "result_reference",
        "result_identity",
        "pricing_revalidation_started",
        "pricing_revalidation_completed",
        "fresh_source_observations_present",
        "source_observation_timestamp_present",
        "provider_model_identifiers_revalidated",
        "context_and_output_limits_revalidated",
        "pricing_values_revalidated",
        "worst_case_route_cost_revalidated",
        "conservative_candidate_capacity_revalidated",
        "all_checks_passed",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11PricingRevalidationResultBoundaryV1:
    schema_version: str
    result_boundary_id: str
    result_boundary_reference: str
    request_reference: str
    request_identity: str
    result_state: ShadowPhase11PricingRevalidationResultStateV1
    result_present: bool
    result_reference: None
    result_identity: None
    pricing_revalidation_started: bool
    pricing_revalidation_completed: bool
    fresh_source_observations_present: bool
    source_observation_timestamp_present: bool
    provider_model_identifiers_revalidated: bool
    context_and_output_limits_revalidated: bool
    pricing_values_revalidated: bool
    worst_case_route_cost_revalidated: bool
    conservative_candidate_capacity_revalidated: bool
    all_checks_passed: bool
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _RESULT_FIELDS, "result boundary")
        normalized = dict(values)
        for name, expected in (
            (
                "schema_version",
                "phase11-shadow-pilot-pricing-revalidation-result-boundary-v1",
            ),
            ("result_boundary_reference", _RESULT_REFERENCE),
            ("request_reference", _REQUEST_REFERENCE),
            ("request_identity", _REQUEST.identity),
            (
                "result_state",
                ShadowPhase11PricingRevalidationResultStateV1
                .RESULT_ABSENT_NOT_EXECUTED,
            ),
            ("result_reference", None),
            ("result_identity", None),
        ):
            normalized[name] = _exact(values[name], expected, name)
        for name in (
            "result_present",
            "pricing_revalidation_started",
            "pricing_revalidation_completed",
            "fresh_source_observations_present",
            "source_observation_timestamp_present",
            "provider_model_identifiers_revalidated",
            "context_and_output_limits_revalidated",
            "pricing_values_revalidated",
            "worst_case_route_cost_revalidated",
            "conservative_candidate_capacity_revalidated",
            "all_checks_passed",
        ):
            normalized[name] = _false(values[name], name)
        normalized["reason_codes"] = _codes(
            values["reason_codes"], _RESULT_REASONS, "result reason_codes"
        )
        supplied = values["result_boundary_id"]
        for name in self.__dataclass_fields__:
            if name != "result_boundary_id":
                object.__setattr__(self, name, normalized[name])
        _identity(self, "result_boundary_id", supplied)

    @property
    def identity(self) -> str:
        return self.result_boundary_id


_EVIDENCE_FALSE_FIELDS = (
    "pricing_revalidation_execution_authorized",
    "pricing_revalidation_started",
    "pricing_revalidation_result_present",
    "pricing_revalidation_completed",
    "current_time_access_required",
    "current_time_access_observed",
    "timestamp_bound",
    "fresh_provider_pricing_observed",
    "credential_configuration_verified",
    "provider_pricing_request_created",
    "provider_request_created",
    "pre_call_reservation_created",
    "ledger_entry_created",
    "runtime_invocation_authorized",
    "provider_call_authorized",
    "provider_transmission_authorized",
    "run_size_authorized",
    "manifest_activation_authorized",
    "launch_authorized",
    "production_authorized",
)
_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_id",
        "evidence_reference",
        "locked_repository_baseline",
        "locked_phase09_baseline",
        "pricing_freshness_policy_reference",
        "pricing_freshness_policy_identity",
        "pricing_evidence_reference",
        "pricing_evidence_identity",
        "blocked_readiness_reconciliation_reference",
        "blocked_readiness_reconciliation_identity",
        "credential_safe_gate_reference",
        "credential_safe_gate_identity",
        "reservation_bound_reference",
        "reservation_bound_identity",
        "boundary_state",
        "request",
        "result_boundary",
        "pricing_revalidation_request_defined",
        *_EVIDENCE_FALSE_FIELDS,
        "launch_readiness",
        "production_effect",
        "zero_production_effect_proof",
        "reason_codes",
    }
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11PricingRevalidationBoundaryEvidenceV1:
    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    pricing_freshness_policy_reference: str
    pricing_freshness_policy_identity: str
    pricing_evidence_reference: str
    pricing_evidence_identity: str
    blocked_readiness_reconciliation_reference: str
    blocked_readiness_reconciliation_identity: str
    credential_safe_gate_reference: str
    credential_safe_gate_identity: str
    reservation_bound_reference: str
    reservation_bound_identity: str
    boundary_state: ShadowPhase11PricingRevalidationBoundaryStateV1
    request: ShadowPhase11PricingRevalidationRequestV1
    result_boundary: ShadowPhase11PricingRevalidationResultBoundaryV1
    pricing_revalidation_request_defined: bool
    pricing_revalidation_execution_authorized: bool
    pricing_revalidation_started: bool
    pricing_revalidation_result_present: bool
    pricing_revalidation_completed: bool
    current_time_access_required: bool
    current_time_access_observed: bool
    timestamp_bound: bool
    fresh_provider_pricing_observed: bool
    credential_configuration_verified: bool
    provider_pricing_request_created: bool
    provider_request_created: bool
    pre_call_reservation_created: bool
    ledger_entry_created: bool
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

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _EVIDENCE_FIELDS, "evidence")
        normalized = dict(values)
        for name, expected in (
            ("schema_version", "phase11-shadow-pilot-pricing-revalidation-boundary-v1"),
            ("evidence_reference", _EVIDENCE_REFERENCE),
            ("locked_repository_baseline", _BASELINE),
            ("locked_phase09_baseline", _PHASE09),
            ("pricing_freshness_policy_reference", _POLICY_REFERENCE),
            ("pricing_freshness_policy_identity", _POLICY_IDENTITY),
            ("pricing_evidence_reference", _PRICING_REFERENCE),
            ("pricing_evidence_identity", _PRICING_IDENTITY),
            (
                "blocked_readiness_reconciliation_reference",
                _RECONCILIATION_REFERENCE,
            ),
            (
                "blocked_readiness_reconciliation_identity",
                _RECONCILIATION_IDENTITY,
            ),
            ("credential_safe_gate_reference", _GATE_REFERENCE),
            ("credential_safe_gate_identity", _GATE_IDENTITY),
            ("reservation_bound_reference", _RESERVATION_REFERENCE),
            ("reservation_bound_identity", _RESERVATION_IDENTITY),
            (
                "boundary_state",
                ShadowPhase11PricingRevalidationBoundaryStateV1
                .REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED,
            ),
            ("launch_readiness", ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH),
            ("production_effect", "NONE"),
            ("zero_production_effect_proof", "PROVEN_NONE"),
        ):
            normalized[name] = _exact(values[name], expected, name)
        if (
            type(values["request"]) is not ShadowPhase11PricingRevalidationRequestV1
            or values["request"].identity != _REQUEST.identity
        ):
            raise ShadowPhase11PricingRevalidationBoundaryValidationError(
                "invalid request"
            )
        if (
            type(values["result_boundary"])
            is not ShadowPhase11PricingRevalidationResultBoundaryV1
            or values["result_boundary"].identity != _RESULT.identity
        ):
            raise ShadowPhase11PricingRevalidationBoundaryValidationError(
                "invalid result_boundary"
            )
        normalized["pricing_revalidation_request_defined"] = _true(
            values["pricing_revalidation_request_defined"],
            "pricing_revalidation_request_defined",
        )
        for name in _EVIDENCE_FALSE_FIELDS:
            normalized[name] = _false(values[name], name)
        normalized["reason_codes"] = _codes(
            values["reason_codes"], _EVIDENCE_REASONS, "evidence reason_codes"
        )
        supplied = values["evidence_id"]
        for name in self.__dataclass_fields__:
            if name != "evidence_id":
                object.__setattr__(self, name, normalized[name])
        _identity(self, "evidence_id", supplied)

    @property
    def identity(self) -> str:
        return self.evidence_id


def _make_request() -> ShadowPhase11PricingRevalidationRequestV1:
    policy = get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    return ShadowPhase11PricingRevalidationRequestV1(
        schema_version="phase11-shadow-pilot-pricing-revalidation-request-v1",
        request_id=None,
        request_reference=_REQUEST_REFERENCE,
        pricing_freshness_policy_reference=policy.evidence_reference,
        pricing_freshness_policy_identity=policy.identity,
        pricing_evidence_reference=pricing.evidence_reference,
        pricing_evidence_identity=pricing.identity,
        check_kinds=_CHECKS,
        primary_model_identifier="deepseek-v4-pro",
        l1_model_identifier="claude-sonnet-5",
        l2_model_identifier="claude-opus-4-8",
        maximum_input_tokens=16000,
        maximum_output_tokens=2000,
        maximum_attempts=1,
        hard_cap_micro_usd=pricing.hard_cap_micro_usd,
        reserve_micro_usd=pricing.safety_reserve_micro_usd,
        maximum_spendable_micro_usd=pricing.spendable_cap_micro_usd,
        worst_case_routed_item_micro_usd=(
            pricing.conservative_worst_case_item_cost_micro_usd
        ),
        conservative_candidate_capacity=pricing.mathematical_safe_maximum_items,
        request_defined=True,
        execution_authorized=False,
        network_access_authorized=False,
        credential_access_authorized=False,
        current_time_access_authorized=False,
        provider_pricing_request_created=False,
        reason_codes=_REQUEST_REASONS,
    )


_REQUEST = _make_request()


def _make_result() -> ShadowPhase11PricingRevalidationResultBoundaryV1:
    return ShadowPhase11PricingRevalidationResultBoundaryV1(
        schema_version=(
            "phase11-shadow-pilot-pricing-revalidation-result-boundary-v1"
        ),
        result_boundary_id=None,
        result_boundary_reference=_RESULT_REFERENCE,
        request_reference=_REQUEST.request_reference,
        request_identity=_REQUEST.identity,
        result_state=(
            ShadowPhase11PricingRevalidationResultStateV1
            .RESULT_ABSENT_NOT_EXECUTED
        ),
        result_present=False,
        result_reference=None,
        result_identity=None,
        pricing_revalidation_started=False,
        pricing_revalidation_completed=False,
        fresh_source_observations_present=False,
        source_observation_timestamp_present=False,
        provider_model_identifiers_revalidated=False,
        context_and_output_limits_revalidated=False,
        pricing_values_revalidated=False,
        worst_case_route_cost_revalidated=False,
        conservative_candidate_capacity_revalidated=False,
        all_checks_passed=False,
        reason_codes=_RESULT_REASONS,
    )


_RESULT = _make_result()


def _make_evidence() -> ShadowPhase11PricingRevalidationBoundaryEvidenceV1:
    policy = get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1()
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reconciliation = (
        get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1()
    )
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    return ShadowPhase11PricingRevalidationBoundaryEvidenceV1(
        schema_version="phase11-shadow-pilot-pricing-revalidation-boundary-v1",
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        locked_repository_baseline=_BASELINE,
        locked_phase09_baseline=_PHASE09,
        pricing_freshness_policy_reference=policy.evidence_reference,
        pricing_freshness_policy_identity=policy.identity,
        pricing_evidence_reference=pricing.evidence_reference,
        pricing_evidence_identity=pricing.identity,
        blocked_readiness_reconciliation_reference=(
            reconciliation.evidence_reference
        ),
        blocked_readiness_reconciliation_identity=reconciliation.identity,
        credential_safe_gate_reference=gate.evidence_reference,
        credential_safe_gate_identity=gate.identity,
        reservation_bound_reference=reservation.evidence_reference,
        reservation_bound_identity=reservation.identity,
        boundary_state=(
            ShadowPhase11PricingRevalidationBoundaryStateV1
            .REQUEST_DEFINED_RESULT_ABSENT_EXECUTION_NOT_AUTHORIZED
        ),
        request=_REQUEST,
        result_boundary=_RESULT,
        pricing_revalidation_request_defined=True,
        pricing_revalidation_execution_authorized=False,
        pricing_revalidation_started=False,
        pricing_revalidation_result_present=False,
        pricing_revalidation_completed=False,
        current_time_access_required=False,
        current_time_access_observed=False,
        timestamp_bound=False,
        fresh_provider_pricing_observed=False,
        credential_configuration_verified=False,
        provider_pricing_request_created=False,
        provider_request_created=False,
        pre_call_reservation_created=False,
        ledger_entry_created=False,
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
        reason_codes=_EVIDENCE_REASONS,
    )


_EVIDENCE = _make_evidence()


def get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1(
) -> ShadowPhase11PricingRevalidationBoundaryEvidenceV1:
    """Return immutable static pricing-revalidation boundary evidence."""

    return _EVIDENCE


__all__ = (
    "ShadowPhase11PricingRevalidationBoundaryEvidenceV1",
    "ShadowPhase11PricingRevalidationBoundaryStateV1",
    "ShadowPhase11PricingRevalidationBoundaryValidationError",
    "ShadowPhase11PricingRevalidationCheckKindV1",
    "ShadowPhase11PricingRevalidationRequestV1",
    "ShadowPhase11PricingRevalidationResultBoundaryV1",
    "ShadowPhase11PricingRevalidationResultStateV1",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1",
    "sha256_hex",
)
