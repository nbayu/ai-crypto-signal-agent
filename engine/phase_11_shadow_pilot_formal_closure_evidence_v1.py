"""Immutable formal Phase 11 shadow-governance closure evidence.

This module records static closure evidence only.  It does not authorize or
record Phase 11 completion, activate Phase 12, resolve blockers, or perform
any content, filesystem, provider, reservation, ledger, or runtime action.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_final_blocker_consolidation_v1 import (
    get_phase_11_shadow_pilot_final_blocker_consolidation_evidence_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)


_SCHEMA = "phase11-shadow-pilot-formal-closure-evidence-v1"
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_FORMAL_CLOSURE_EVIDENCE_001"
_REPOSITORY_BASELINE = "33cef0fa294b02aa9472013010cb63faef3f581a"
_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_LINEAGE_REFERENCE = (
    "PHASE_11_PILOT_FINAL_SUCCESSOR_LINEAGE_RECONCILIATION_001"
)
_LINEAGE_IDENTITY = (
    "331f2d27625029e7da91ad58d070526db8ba816e2bbc4fb3d22366a4abe770ec"
)
_CONSOLIDATION_REFERENCE = "PHASE_11_PILOT_FINAL_BLOCKER_CONSOLIDATION_001"
_CONSOLIDATION_IDENTITY = (
    "52eb3ae03597a61f1fbee9fdbe4a8ebf8523139c2ddd07d24213e25ea8045e08"
)
_CRITERIA = tuple(
    sorted(
        (
            "IMMUTABLE_GOVERNANCE_EVIDENCE_COMPLETE",
            "OPERATIONAL_EXECUTION_EXCLUDED",
            "BUDGET_COST_ATTEMPT_AND_ROUTE_BOUNDS_EXPLICIT",
            "PROVIDER_AND_CREDENTIAL_ACCESS_SEPARATED",
            "EXECUTABLE_CONTENT_AND_IDENTITY_ABSENT",
            "INSPECTION_VERIFICATION_AND_ACCEPTANCE_DENIED",
            "PROPOSED_MANIFEST_DEFINED_AND_INACTIVE",
            "RESERVATION_PROVIDER_REQUEST_AND_RUNTIME_ABSENT",
            "LAUNCH_AND_PRODUCTION_AUTHORITY_ABSENT",
            "ACTIVE_BLOCKER_DISPOSITIONS_COMPLETE",
            "FINAL_STATIC_LINEAGE_COMPLETE",
            "ZERO_PRODUCTION_PROOF_INTACT",
        )
    )
)
_BLOCKERS = tuple(
    sorted(
        (
            "CONTENT_ACCESS_NOT_AUTHORIZED",
            "CONTENT_CREATION_AUTHORITY_NOT_GRANTED",
            "CONTENT_HASHING_NOT_AUTHORIZED",
            "CONTENT_INTEGRITY_NOT_VERIFIED",
            "CONTENT_NOT_ACCEPTED",
            "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
            "EXECUTABLE_CONTENT_IDENTITY_ABSENT",
            "EXECUTABLE_INPUT_CONTENT_ABSENT",
            "FILESYSTEM_READ_NOT_AUTHORIZED",
            "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
            "INTEGRITY_RESULT_ABSENT",
            "INTEGRITY_VERIFICATION_NOT_AUTHORIZED",
            "LAUNCH_NOT_AUTHORIZED",
            "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
            "PRE_CALL_RESERVATION_NOT_CREATED",
            "PRICING_REVALIDATION_INCOMPLETE",
            "PROVIDER_REQUEST_NOT_CREATED",
            "RESULT_ACCEPTANCE_NOT_AUTHORIZED",
            "RUNTIME_INVOCATION_NOT_AUTHORIZED",
            "RUN_SIZE_NOT_AUTHORIZED",
        )
    )
)
_REASONS = tuple(
    sorted(
        (
            "CLOSURE_READINESS_AUDIT_PASSED",
            "SHADOW_GOVERNANCE_OBJECTIVES_SATISFIED",
            "FINAL_SUCCESSOR_LINEAGE_RECONCILED",
            "FINAL_BLOCKER_CONSOLIDATION_COMPLETE",
            "ALL_ACTIVE_BLOCKERS_REMAIN_CLASSIFIED",
            "NO_BLOCKER_RESOLVED_BY_CLOSURE_EVIDENCE",
            "DEFERRED_PREREQUISITES_REMAIN_UNAUTHORIZED",
            "LAUNCH_READINESS_REMAINS_BLOCKED",
            "PRODUCTION_EFFECT_REMAINS_NONE",
            "PHASE_11_COMPLETION_NOT_AUTHORIZED",
            "PHASE_12_ACTIVATION_NOT_AUTHORIZED",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)
_TRUE_FIELDS = (
    "phase_11_shadow_governance_objectives_satisfied",
    "closure_readiness_audit_passed",
    "formal_closure_evidence_recorded",
    "final_lineage_reconciled",
    "final_blocker_consolidation_complete",
    "all_active_blockers_classified",
    "zero_production_proof_intact",
)


class ShadowPhase11FormalClosureEvidenceValidationError(ValueError):
    """Raised when formal Phase 11 closure evidence is invalid."""


class ShadowPhase11FormalClosureStateV1(StrEnum):
    """The sole permitted formal closure-evidence state."""

    CLOSURE_EVIDENCE_RECORDED_COMPLETION_NOT_AUTHORIZED = (
        "CLOSURE_EVIDENCE_RECORDED_COMPLETION_NOT_AUTHORIZED"
    )


class ShadowPhase11FormalClosureOutcomeV1(StrEnum):
    """The sole permitted shadow-governance closure outcome."""

    SHADOW_GOVERNANCE_OBJECTIVES_SATISFIED = (
        "SHADOW_GOVERNANCE_OBJECTIVES_SATISFIED"
    )


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if type(value) is ShadowPhase11FormalClosureSuccessCriterionV1:
        return {
            name: _canonical_value(getattr(value, name))
            for name in value.__dataclass_fields__
        }
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
    raise ShadowPhase11FormalClosureEvidenceValidationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes."""

    try:
        return json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowPhase11FormalClosureEvidenceValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11FormalClosureEvidenceValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11FormalClosureEvidenceValidationError(
            f"invalid {label}"
        )
    return value


def _codes(
    value: Any,
    expected: tuple[str, ...],
    label: str,
) -> tuple[str, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(expected)
        or any(type(item) is not str for item in value)
        or len(set(value)) != len(value)
        or set(value) != set(expected)
    ):
        raise ShadowPhase11FormalClosureEvidenceValidationError(
            f"invalid {label}"
        )
    return expected


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11FormalClosureSuccessCriterionV1:
    """Immutable record of one satisfied shadow-governance objective."""

    criterion_code: str
    satisfied: bool
    evidence_recorded: bool
    grants_operational_authority: bool
    grants_launch_authority: bool
    grants_production_authority: bool

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != frozenset(self.__dataclass_fields__):
            raise ShadowPhase11FormalClosureEvidenceValidationError(
                "invalid criterion fields"
            )
        criterion_code = values["criterion_code"]
        if type(criterion_code) is not str or criterion_code not in _CRITERIA:
            raise ShadowPhase11FormalClosureEvidenceValidationError(
                "invalid criterion_code"
            )
        locked_values = {
            "criterion_code": criterion_code,
            "satisfied": True,
            "evidence_recorded": True,
            "grants_operational_authority": False,
            "grants_launch_authority": False,
            "grants_production_authority": False,
        }
        for name, expected in locked_values.items():
            object.__setattr__(
                self,
                name,
                _exact(values[name], expected, name),
            )


def _success_criteria(
    value: Any,
) -> tuple[ShadowPhase11FormalClosureSuccessCriterionV1, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(_CRITERIA)
        or any(
            type(item) is not ShadowPhase11FormalClosureSuccessCriterionV1
            for item in value
        )
        or len({item.criterion_code for item in value}) != len(_CRITERIA)
        or {item.criterion_code for item in value} != set(_CRITERIA)
    ):
        raise ShadowPhase11FormalClosureEvidenceValidationError(
            "invalid success_criteria"
        )
    return tuple(sorted(value, key=lambda item: item.criterion_code))


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11FormalClosureEvidenceV1:
    """Immutable formal Phase 11 shadow-governance closure evidence."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    closure_state: ShadowPhase11FormalClosureStateV1
    closure_outcome: ShadowPhase11FormalClosureOutcomeV1
    final_successor_lineage_reference: str
    final_successor_lineage_identity: str
    final_blocker_consolidation_reference: str
    final_blocker_consolidation_identity: str
    success_criteria: tuple[ShadowPhase11FormalClosureSuccessCriterionV1, ...]
    phase_11_shadow_governance_objectives_satisfied: bool
    closure_readiness_audit_passed: bool
    formal_closure_evidence_recorded: bool
    final_lineage_reconciled: bool
    final_blocker_consolidation_complete: bool
    all_active_blockers_classified: bool
    zero_production_proof_intact: bool
    total_shadow_governance_objectives: int
    total_satisfied_shadow_governance_objectives: int
    total_active_blockers: int
    total_classified_blockers: int
    total_resolved_blockers: int
    total_execution_authorized_blockers: int
    total_shadow_governance_blockers: int
    total_deferred_post_phase_11_prerequisites: int
    total_explicitly_absent_launch_or_production_authorities: int
    operational_launch_ready: bool
    production_ready: bool
    phase_11_completion_authorized: bool
    phase_11_completion_recorded: bool
    phase_12_activation_ready: bool
    phase_12_activation_authorized: bool
    phase_12_activated: bool
    blocker_resolution_authorized: bool
    deferred_prerequisite_execution_authorized: bool
    classification_changes_current_state: bool
    content_creation_execution_authorized: bool
    content_access_authorized: bool
    filesystem_read_authorized: bool
    filesystem_write_authorized: bool
    content_hashing_authorized: bool
    integrity_inspection_authorized: bool
    integrity_verification_authorized: bool
    result_acceptance_authorized: bool
    manifest_mutation_authorized: bool
    manifest_activation_authorized: bool
    pricing_revalidation_execution_authorized: bool
    credential_verification_execution_authorized: bool
    provider_request_created: bool
    pre_call_reservation_created: bool
    ledger_entry_created: bool
    runtime_invocation_authorized: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    run_size_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    production_effect: str
    zero_production_proof: str
    blocker_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        expected_fields = frozenset(self.__dataclass_fields__)
        if frozenset(values) != expected_fields:
            raise ShadowPhase11FormalClosureEvidenceValidationError(
                "invalid evidence fields"
            )
        locked_values = {
            "schema_version": _SCHEMA,
            "evidence_reference": _EVIDENCE_REFERENCE,
            "locked_repository_baseline": _REPOSITORY_BASELINE,
            "locked_phase09_baseline": _PHASE09_BASELINE,
            "closure_state": (
                ShadowPhase11FormalClosureStateV1
                .CLOSURE_EVIDENCE_RECORDED_COMPLETION_NOT_AUTHORIZED
            ),
            "closure_outcome": (
                ShadowPhase11FormalClosureOutcomeV1
                .SHADOW_GOVERNANCE_OBJECTIVES_SATISFIED
            ),
            "final_successor_lineage_reference": _LINEAGE_REFERENCE,
            "final_successor_lineage_identity": _LINEAGE_IDENTITY,
            "final_blocker_consolidation_reference": _CONSOLIDATION_REFERENCE,
            "final_blocker_consolidation_identity": _CONSOLIDATION_IDENTITY,
            "total_shadow_governance_objectives": 12,
            "total_satisfied_shadow_governance_objectives": 12,
            "total_active_blockers": 20,
            "total_classified_blockers": 20,
            "total_resolved_blockers": 0,
            "total_execution_authorized_blockers": 0,
            "total_shadow_governance_blockers": 6,
            "total_deferred_post_phase_11_prerequisites": 12,
            "total_explicitly_absent_launch_or_production_authorities": 2,
            "launch_readiness": (
                ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
            ),
            "production_effect": "NONE",
            "zero_production_proof": "PROVEN_NONE",
        }
        excluded_fields = {
            "evidence_id",
            "success_criteria",
            "blocker_codes",
            "reason_codes",
            *_TRUE_FIELDS,
        }
        false_fields = expected_fields - set(locked_values) - excluded_fields
        normalized = {
            name: _exact(values[name], expected, name)
            for name, expected in locked_values.items()
        }
        for name in _TRUE_FIELDS:
            normalized[name] = _exact(values[name], True, name)
        for name in false_fields:
            normalized[name] = _exact(values[name], False, name)
        normalized["success_criteria"] = _success_criteria(
            values["success_criteria"]
        )
        normalized["blocker_codes"] = _codes(
            values["blocker_codes"],
            _BLOCKERS,
            "blocker_codes",
        )
        normalized["reason_codes"] = _codes(
            values["reason_codes"],
            _REASONS,
            "reason_codes",
        )

        for name, value in normalized.items():
            object.__setattr__(self, name, value)
        payload = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "evidence_id"
        }
        identity = sha256_hex(canonical_json_bytes(payload))
        supplied_identity = values["evidence_id"]
        if supplied_identity is not None and (
            type(supplied_identity) is not str
            or supplied_identity != identity
        ):
            raise ShadowPhase11FormalClosureEvidenceValidationError(
                "supplied evidence identity does not match"
            )
        object.__setattr__(self, "evidence_id", identity)

    @property
    def identity(self) -> str:
        """Return the canonical evidence identity."""

        return self.evidence_id


def _make_criterion(
    criterion_code: str,
) -> ShadowPhase11FormalClosureSuccessCriterionV1:
    return ShadowPhase11FormalClosureSuccessCriterionV1(
        criterion_code=criterion_code,
        satisfied=True,
        evidence_recorded=True,
        grants_operational_authority=False,
        grants_launch_authority=False,
        grants_production_authority=False,
    )


def get_phase_11_shadow_pilot_formal_closure_evidence_v1(
) -> ShadowPhase11FormalClosureEvidenceV1:
    """Return immutable formal Phase 11 closure evidence."""

    consolidation = (
        get_phase_11_shadow_pilot_final_blocker_consolidation_evidence_v1()
    )
    values: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "evidence_id": None,
        "evidence_reference": _EVIDENCE_REFERENCE,
        "locked_repository_baseline": _REPOSITORY_BASELINE,
        "locked_phase09_baseline": _PHASE09_BASELINE,
        "closure_state": (
            ShadowPhase11FormalClosureStateV1
            .CLOSURE_EVIDENCE_RECORDED_COMPLETION_NOT_AUTHORIZED
        ),
        "closure_outcome": (
            ShadowPhase11FormalClosureOutcomeV1
            .SHADOW_GOVERNANCE_OBJECTIVES_SATISFIED
        ),
        "final_successor_lineage_reference": (
            consolidation.final_successor_lineage_reference
        ),
        "final_successor_lineage_identity": (
            consolidation.final_successor_lineage_identity
        ),
        "final_blocker_consolidation_reference": (
            consolidation.evidence_reference
        ),
        "final_blocker_consolidation_identity": consolidation.identity,
        "success_criteria": tuple(
            _make_criterion(code) for code in _CRITERIA
        ),
        **{name: True for name in _TRUE_FIELDS},
        "total_shadow_governance_objectives": 12,
        "total_satisfied_shadow_governance_objectives": 12,
        "total_active_blockers": consolidation.total_active_blockers,
        "total_classified_blockers": consolidation.total_classified_blockers,
        "total_resolved_blockers": consolidation.total_resolved_blockers,
        "total_execution_authorized_blockers": (
            consolidation.total_execution_authorized_blockers
        ),
        "total_shadow_governance_blockers": 6,
        "total_deferred_post_phase_11_prerequisites": 12,
        "total_explicitly_absent_launch_or_production_authorities": 2,
        "launch_readiness": (
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "blocker_codes": consolidation.blocker_codes,
        "reason_codes": _REASONS,
    }
    for name in ShadowPhase11FormalClosureEvidenceV1.__dataclass_fields__:
        values.setdefault(name, False)
    return ShadowPhase11FormalClosureEvidenceV1(**values)
