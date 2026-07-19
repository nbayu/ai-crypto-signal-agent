"""Immutable static Phase 11 final blocker consolidation.

This module classifies existing immutable blocker metadata only.  It resolves
no blocker, grants no authority, creates no operational boundary, and performs
no content, filesystem, provider, reservation, ledger, or runtime operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_final_successor_lineage_reconciliation_v1 import (
    get_phase_11_shadow_pilot_final_successor_lineage_reconciliation_evidence_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)


_SCHEMA = "phase11-shadow-pilot-final-blocker-consolidation-v1"
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_FINAL_BLOCKER_CONSOLIDATION_001"
_REPOSITORY_BASELINE = "ea3091b4487643cc9333372e3c02bc40611da066"
_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_LINEAGE_REFERENCE = (
    "PHASE_11_PILOT_FINAL_SUCCESSOR_LINEAGE_RECONCILIATION_001"
)
_LINEAGE_IDENTITY = (
    "331f2d27625029e7da91ad58d070526db8ba816e2bbc4fb3d22366a4abe770ec"
)


class ShadowPhase11FinalBlockerConsolidationValidationError(ValueError):
    """Raised when final blocker-consolidation evidence is invalid."""


class ShadowPhase11FinalBlockerClassV1(StrEnum):
    """Closed Phase 11 blocker-disposition vocabulary."""

    SHADOW_GOVERNANCE_BLOCKER = "SHADOW_GOVERNANCE_BLOCKER"
    DEFERRED_POST_PHASE_11_PREREQUISITE = (
        "DEFERRED_POST_PHASE_11_PREREQUISITE"
    )
    EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY = (
        "EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY"
    )


class ShadowPhase11FinalBlockerConsolidationStateV1(StrEnum):
    """The sole permitted consolidation state."""

    ACTIVE_BLOCKERS_CLASSIFIED_NO_AUTHORITY_GRANTED = (
        "ACTIVE_BLOCKERS_CLASSIFIED_NO_AUTHORITY_GRANTED"
    )


_CLASS_BY_CODE = {
    "CONTENT_ACCESS_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER
    ),
    "CONTENT_HASHING_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER
    ),
    "FILESYSTEM_READ_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER
    ),
    "INTEGRITY_INSPECTION_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER
    ),
    "INTEGRITY_VERIFICATION_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER
    ),
    "RESULT_ACCEPTANCE_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER
    ),
    "CONTENT_CREATION_AUTHORITY_NOT_GRANTED": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "CONTENT_INTEGRITY_NOT_VERIFIED": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "CONTENT_NOT_ACCEPTED": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "EXECUTABLE_CONTENT_IDENTITY_ABSENT": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "EXECUTABLE_INPUT_CONTENT_ABSENT": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "INTEGRITY_RESULT_ABSENT": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "MANIFEST_ACTIVATION_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "PRE_CALL_RESERVATION_NOT_CREATED": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "PRICING_REVALIDATION_INCOMPLETE": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "PROVIDER_REQUEST_NOT_CREATED": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "RUNTIME_INVOCATION_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1
        .DEFERRED_POST_PHASE_11_PREREQUISITE
    ),
    "LAUNCH_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1
        .EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY
    ),
    "RUN_SIZE_NOT_AUTHORIZED": (
        ShadowPhase11FinalBlockerClassV1
        .EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY
    ),
}
_BLOCKERS = tuple(sorted(_CLASS_BY_CODE))
_RATIONALE_BY_CLASS = {
    ShadowPhase11FinalBlockerClassV1.SHADOW_GOVERNANCE_BLOCKER: (
        "SHADOW_GOVERNANCE_BOUNDARY_PRESERVED"
    ),
    ShadowPhase11FinalBlockerClassV1.DEFERRED_POST_PHASE_11_PREREQUISITE: (
        "POST_PHASE_11_PREREQUISITE_DEFERRED"
    ),
    ShadowPhase11FinalBlockerClassV1
    .EXPLICITLY_ABSENT_LAUNCH_OR_PRODUCTION_AUTHORITY: (
        "LAUNCH_OR_PRODUCTION_AUTHORITY_ABSENT"
    ),
}
_REASONS = tuple(
    sorted(
        (
            "FINAL_SUCCESSOR_LINEAGE_LINKED",
            "ALL_ACTIVE_BLOCKERS_CLASSIFIED",
            "NO_BLOCKER_RESOLVED_BY_CLASSIFICATION",
            "SHADOW_GOVERNANCE_BOUNDARIES_PRESERVED",
            "POST_PHASE_11_PREREQUISITES_DEFERRED",
            "LAUNCH_AND_PRODUCTION_AUTHORITIES_EXPLICITLY_ABSENT",
            "NO_EXECUTION_AUTHORITY_GRANTED",
            "PHASE_11_COMPLETION_NOT_IMPLIED",
            "PHASE_12_ACTIVATION_NOT_IMPLIED",
            "READINESS_REMAINS_BLOCKED",
            "NO_PRODUCTION_EFFECT",
        )
    )
)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if type(value) is ShadowPhase11FinalBlockerDispositionV1:
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
    raise ShadowPhase11FinalBlockerConsolidationValidationError(
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
        raise ShadowPhase11FinalBlockerConsolidationValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11FinalBlockerConsolidationValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11FinalBlockerConsolidationValidationError(
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
        raise ShadowPhase11FinalBlockerConsolidationValidationError(
            f"invalid {label}"
        )
    return expected


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11FinalBlockerDispositionV1:
    """Immutable classification of one active blocker."""

    blocker_code: str
    blocker_class: ShadowPhase11FinalBlockerClassV1
    blocker_active: bool
    blocker_resolved: bool
    execution_deferred: bool
    execution_authorized: bool
    grants_launch_authority: bool
    grants_production_authority: bool
    rationale_code: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != frozenset(self.__dataclass_fields__):
            raise ShadowPhase11FinalBlockerConsolidationValidationError(
                "invalid disposition fields"
            )
        blocker_code = values["blocker_code"]
        if type(blocker_code) is not str or blocker_code not in _CLASS_BY_CODE:
            raise ShadowPhase11FinalBlockerConsolidationValidationError(
                "invalid blocker_code"
            )
        blocker_class = values["blocker_class"]
        if type(blocker_class) is not ShadowPhase11FinalBlockerClassV1:
            raise ShadowPhase11FinalBlockerConsolidationValidationError(
                "invalid blocker_class"
            )
        locked_values = {
            "blocker_code": blocker_code,
            "blocker_class": blocker_class,
            "blocker_active": True,
            "blocker_resolved": False,
            "execution_deferred": (
                blocker_class
                is ShadowPhase11FinalBlockerClassV1
                .DEFERRED_POST_PHASE_11_PREREQUISITE
            ),
            "execution_authorized": False,
            "grants_launch_authority": False,
            "grants_production_authority": False,
            "rationale_code": _RATIONALE_BY_CLASS[blocker_class],
        }
        for name, expected in locked_values.items():
            object.__setattr__(
                self,
                name,
                _exact(values[name], expected, name),
            )


def _dispositions(value: Any) -> tuple[ShadowPhase11FinalBlockerDispositionV1, ...]:
    if (
        type(value) not in (tuple, list)
        or len(value) != len(_BLOCKERS)
        or any(
            type(item) is not ShadowPhase11FinalBlockerDispositionV1
            for item in value
        )
        or len({item.blocker_code for item in value}) != len(_BLOCKERS)
        or {item.blocker_code for item in value} != set(_BLOCKERS)
        or any(
            item.blocker_class is not _CLASS_BY_CODE[item.blocker_code]
            for item in value
        )
    ):
        raise ShadowPhase11FinalBlockerConsolidationValidationError(
            "invalid dispositions"
        )
    return tuple(sorted(value, key=lambda item: item.blocker_code))


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11FinalBlockerConsolidationEvidenceV1:
    """Immutable final blocker-consolidation evidence."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    final_successor_lineage_reference: str
    final_successor_lineage_identity: str
    consolidation_state: ShadowPhase11FinalBlockerConsolidationStateV1
    blocker_codes: tuple[str, ...]
    dispositions: tuple[ShadowPhase11FinalBlockerDispositionV1, ...]
    total_active_blockers: int
    total_classified_blockers: int
    total_resolved_blockers: int
    total_execution_authorized_blockers: int
    all_blockers_classified: bool
    all_blockers_remain_active: bool
    classification_changes_current_state: bool
    classification_grants_operational_authority: bool
    classification_grants_launch_authority: bool
    classification_grants_production_authority: bool
    phase_11_completion_implied: bool
    phase_12_activation_implied: bool
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
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        expected_fields = frozenset(self.__dataclass_fields__)
        if frozenset(values) != expected_fields:
            raise ShadowPhase11FinalBlockerConsolidationValidationError(
                "invalid evidence fields"
            )
        locked_values = {
            "schema_version": _SCHEMA,
            "evidence_reference": _EVIDENCE_REFERENCE,
            "locked_repository_baseline": _REPOSITORY_BASELINE,
            "locked_phase09_baseline": _PHASE09_BASELINE,
            "final_successor_lineage_reference": _LINEAGE_REFERENCE,
            "final_successor_lineage_identity": _LINEAGE_IDENTITY,
            "consolidation_state": (
                ShadowPhase11FinalBlockerConsolidationStateV1
                .ACTIVE_BLOCKERS_CLASSIFIED_NO_AUTHORITY_GRANTED
            ),
            "total_active_blockers": 20,
            "total_classified_blockers": 20,
            "total_resolved_blockers": 0,
            "total_execution_authorized_blockers": 0,
            "all_blockers_classified": True,
            "all_blockers_remain_active": True,
            "launch_readiness": (
                ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
            ),
            "production_effect": "NONE",
            "zero_production_proof": "PROVEN_NONE",
        }
        excluded_fields = {
            "evidence_id",
            "blocker_codes",
            "dispositions",
            "reason_codes",
        }
        false_fields = expected_fields - set(locked_values) - excluded_fields
        normalized = {
            name: _exact(values[name], expected, name)
            for name, expected in locked_values.items()
        }
        for name in false_fields:
            normalized[name] = _exact(values[name], False, name)
        normalized["blocker_codes"] = _codes(
            values["blocker_codes"],
            _BLOCKERS,
            "blocker_codes",
        )
        normalized["dispositions"] = _dispositions(values["dispositions"])
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
            raise ShadowPhase11FinalBlockerConsolidationValidationError(
                "supplied evidence identity does not match"
            )
        object.__setattr__(self, "evidence_id", identity)

    @property
    def identity(self) -> str:
        """Return the canonical evidence identity."""

        return self.evidence_id


def _make_disposition(
    blocker_code: str,
) -> ShadowPhase11FinalBlockerDispositionV1:
    blocker_class = _CLASS_BY_CODE[blocker_code]
    return ShadowPhase11FinalBlockerDispositionV1(
        blocker_code=blocker_code,
        blocker_class=blocker_class,
        blocker_active=True,
        blocker_resolved=False,
        execution_deferred=(
            blocker_class
            is ShadowPhase11FinalBlockerClassV1
            .DEFERRED_POST_PHASE_11_PREREQUISITE
        ),
        execution_authorized=False,
        grants_launch_authority=False,
        grants_production_authority=False,
        rationale_code=_RATIONALE_BY_CLASS[blocker_class],
    )


def get_phase_11_shadow_pilot_final_blocker_consolidation_evidence_v1(
) -> ShadowPhase11FinalBlockerConsolidationEvidenceV1:
    """Return immutable final blocker-classification evidence."""

    final_lineage = (
        get_phase_11_shadow_pilot_final_successor_lineage_reconciliation_evidence_v1()
    )
    values: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "evidence_id": None,
        "evidence_reference": _EVIDENCE_REFERENCE,
        "locked_repository_baseline": _REPOSITORY_BASELINE,
        "locked_phase09_baseline": _PHASE09_BASELINE,
        "final_successor_lineage_reference": final_lineage.evidence_reference,
        "final_successor_lineage_identity": final_lineage.identity,
        "consolidation_state": (
            ShadowPhase11FinalBlockerConsolidationStateV1
            .ACTIVE_BLOCKERS_CLASSIFIED_NO_AUTHORITY_GRANTED
        ),
        "blocker_codes": final_lineage.blocker_codes,
        "dispositions": tuple(
            _make_disposition(code) for code in final_lineage.blocker_codes
        ),
        "total_active_blockers": 20,
        "total_classified_blockers": 20,
        "total_resolved_blockers": 0,
        "total_execution_authorized_blockers": 0,
        "all_blockers_classified": True,
        "all_blockers_remain_active": True,
        "launch_readiness": (
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        "production_effect": "NONE",
        "zero_production_proof": "PROVEN_NONE",
        "reason_codes": _REASONS,
    }
    for name in (
        ShadowPhase11FinalBlockerConsolidationEvidenceV1
        .__dataclass_fields__
    ):
        values.setdefault(name, False)
    return ShadowPhase11FinalBlockerConsolidationEvidenceV1(**values)
