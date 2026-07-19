"""Immutable Phase 11 executable-input successor reconciliation.

This module records static lineage and blocked-readiness facts only.  It does
not read source content, create executable input, modify a manifest, inspect
credentials or pricing, reserve funds, contact a provider, or grant runtime,
transmission, run-size, launch, or production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)


_SCHEMA = (
    "phase11-shadow-pilot-successor-executable-input-"
    "boundary-reconciliation-v1"
)
_EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_SUCCESSOR_EXECUTABLE_INPUT_"
    "BOUNDARY_RECONCILIATION_001"
)
_REPOSITORY_BASELINE = "55c9fda8c6decc974528f86b3306ff7a9dfa8200"
_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_PREDECESSOR_REFERENCE = (
    "PHASE_11_PILOT_SUCCESSOR_BLOCKED_READINESS_"
    "BOUNDARY_RECONCILIATION_001"
)
_PREDECESSOR_IDENTITY = (
    "e5873183a2d289283d9fc2849cb28e86aaf1a69bbd8ac5e9f7709877c9496446"
)
_EXECUTABLE_INPUT_BOUNDARY_REFERENCE = (
    "PHASE_11_PILOT_EXECUTABLE_INPUT_CREATION_BOUNDARY_001"
)
_EXECUTABLE_INPUT_BOUNDARY_IDENTITY = (
    "f82aef927d6d0e4c0e021e597bd8fcba8ed9426e5c56ad551947ea1052f1c097"
)
_PRICING_BOUNDARY_REFERENCE = (
    "PHASE_11_PILOT_PRICING_REVALIDATION_BOUNDARY_001"
)
_PRICING_BOUNDARY_IDENTITY = (
    "33d25cac84df17608b41008b4c91160dd57354e059f1ae6f6a711db2a3beed59"
)
_CREDENTIAL_BOUNDARY_REFERENCE = (
    "PHASE_11_PILOT_CREDENTIAL_CONFIGURATION_"
    "VERIFICATION_BOUNDARY_001"
)
_CREDENTIAL_BOUNDARY_IDENTITY = (
    "f4b9ef09b6e17875a484d833525ccc3410049fc885f20c149f4df7445515fc91"
)
_READINESS_REFERENCE = "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
_READINESS_IDENTITY = (
    "9dffc3370346370284fe5a630a32e78be6def065428060ce70eea8cddf0fd228"
)
_CANDIDATE_INPUT_SET_IDENTITY = (
    "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
)
_PROPOSED_MANIFEST_REFERENCE = "PHASE_11_PILOT_PROPOSED_RUN_MANIFEST_001"
_PROPOSED_MANIFEST_IDENTITY = (
    "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
)
_RUNTIME_REFERENCE = "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
_RUNTIME_IDENTITY = (
    "72342b2390f32463f6d5104f47d3dc29ff5067349daec61a4fe5565de725b51e"
)
_RESERVATION_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
_RESERVATION_IDENTITY = (
    "424a3a332c31a3143ee3a4b6ab8b37b7ec440ea0fcf3c6a01566e451bb11cb70"
)
_BLOCKERS = tuple(
    sorted(
        (
            "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
            "EXECUTABLE_INPUT_CONTENT_ABSENT",
            "LAUNCH_NOT_AUTHORIZED",
            "PRE_CALL_RESERVATION_NOT_CREATED",
            "PRICING_REVALIDATION_INCOMPLETE",
            "PROPOSED_MANIFEST_NOT_ACTIVATED",
            "PROVIDER_REQUEST_NOT_CREATED",
            "RUN_SIZE_NOT_AUTHORIZED",
            "RUNTIME_INVOCATION_NOT_AUTHORIZED",
        )
    )
)
_REASONS = tuple(
    sorted(
        (
            "PREDECESSOR_SUCCESSOR_RECONCILIATION_PRESERVED",
            "EXECUTABLE_INPUT_BOUNDARY_LINKED",
            "EXECUTABLE_INPUT_DESCRIPTOR_RECOGNIZED",
            "EXECUTABLE_INPUT_CREATION_NOT_EXECUTED",
            "EXECUTABLE_INPUT_CONTENT_REMAINS_ABSENT",
            "PROPOSED_MANIFEST_REMAINS_INACTIVE",
            "NO_OPERATIONAL_AUTHORITY",
        )
    )
)
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
    ValueError
):
    """Raised when executable-input successor evidence is invalid."""


class ShadowPhase11SuccessorExecutableInputBoundaryReconciliationStateV1(
    StrEnum
):
    """The sole permitted executable-input reconciliation state."""

    EXECUTABLE_INPUT_BOUNDARY_RECONCILED_READINESS_BLOCKED = (
        "EXECUTABLE_INPUT_BOUNDARY_RECONCILED_READINESS_BLOCKED"
    )


class ShadowPhase11SuccessorExecutableInputPredecessorStatusV1(StrEnum):
    """The sole permitted predecessor-lineage status."""

    PREDECESSOR_SUCCESSOR_RECONCILIATION_PRESERVED = (
        "PREDECESSOR_SUCCESSOR_RECONCILIATION_PRESERVED"
    )


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
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
    raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
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
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            "sha256 input must be exact bytes"
        )
    return sha256(value).hexdigest()


def _exact_fields(values: Mapping[str, Any], expected: frozenset[str]) -> None:
    if frozenset(values) != expected:
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            "invalid evidence fields"
        )


def _exact(value: Any, expected: Any, label: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            f"invalid {label}"
        )
    return value


def _exact_bool(value: Any, expected: bool, label: str) -> bool:
    if type(value) is not bool or value is not expected:
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            f"invalid {label}"
        )
    return value


def _canonical_codes(
    value: Any,
    expected: tuple[str, ...],
    label: str,
) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            f"invalid {label}"
        )
    if any(
        type(code) is not str or _CODE.fullmatch(code) is None
        for code in value
    ):
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            f"invalid {label}"
        )
    if len(set(value)) != len(value):
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            f"duplicate {label}"
        )
    normalized = tuple(sorted(value))
    if normalized != expected:
        raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
            f"incorrect {label}"
        )
    return normalized


_EVIDENCE_FIELDS = frozenset(
    (
        "schema_version",
        "evidence_id",
        "evidence_reference",
        "locked_repository_baseline",
        "locked_phase09_baseline",
        "reconciliation_state",
        "predecessor_status",
        "predecessor_successor_reconciliation_reference",
        "predecessor_successor_reconciliation_identity",
        "predecessor_successor_reconciliation_mutated",
        "predecessor_successor_reconciliation_transitioned",
        "predecessor_successor_reconciliation_current_authority",
        "executable_input_creation_boundary_reference",
        "executable_input_creation_boundary_identity",
        "executable_input_creation_descriptor_defined",
        "executable_input_creation_execution_authorized",
        "executable_input_creation_started",
        "executable_input_creation_result_present",
        "executable_input_creation_completed",
        "source_content_access_observed",
        "filesystem_write_observed",
        "executable_content_generated",
        "executable_content_serialized",
        "executable_input_content_present",
        "content_integrity_verified",
        "proposed_manifest_modified",
        "proposed_manifest_activated",
        "pricing_revalidation_boundary_reference",
        "pricing_revalidation_boundary_identity",
        "pricing_revalidation_descriptor_defined",
        "pricing_revalidation_execution_authorized",
        "pricing_revalidation_started",
        "pricing_revalidation_result_present",
        "pricing_revalidation_completed",
        "fresh_provider_pricing_observed",
        "credential_verification_boundary_reference",
        "credential_verification_boundary_identity",
        "credential_verification_descriptor_defined",
        "credential_verification_execution_authorized",
        "credential_verification_started",
        "credential_verification_result_present",
        "credential_verification_completed",
        "credential_configuration_verified",
        "credential_or_secret_access_observed",
        "environment_access_observed",
        "filesystem_access_observed",
        "network_access_observed",
        "provider_authentication_probe_performed",
        "input_run_manifest_readiness_reference",
        "input_run_manifest_readiness_identity",
        "candidate_input_set_identity",
        "proposed_manifest_reference",
        "proposed_manifest_identity",
        "current_runtime_integrity_reference",
        "current_runtime_integrity_identity",
        "reservation_bound_reference",
        "reservation_bound_identity",
        "candidate_input_metadata_defined",
        "proposed_manifest_defined",
        "pre_call_reservation_created",
        "ledger_entry_created",
        "provider_request_created",
        "runtime_invocation_authorized",
        "provider_call_authorized",
        "provider_transmission_authorized",
        "run_size_authorized",
        "manifest_activation_authorized",
        "launch_authorized",
        "production_authorized",
        "launch_readiness",
        "production_effect",
        "zero_production_proof",
        "blocker_codes",
        "reason_codes",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1:
    """Immutable executable-input successor reconciliation evidence."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    reconciliation_state: (
        ShadowPhase11SuccessorExecutableInputBoundaryReconciliationStateV1
    )
    predecessor_status: ShadowPhase11SuccessorExecutableInputPredecessorStatusV1
    predecessor_successor_reconciliation_reference: str
    predecessor_successor_reconciliation_identity: str
    predecessor_successor_reconciliation_mutated: bool
    predecessor_successor_reconciliation_transitioned: bool
    predecessor_successor_reconciliation_current_authority: bool
    executable_input_creation_boundary_reference: str
    executable_input_creation_boundary_identity: str
    executable_input_creation_descriptor_defined: bool
    executable_input_creation_execution_authorized: bool
    executable_input_creation_started: bool
    executable_input_creation_result_present: bool
    executable_input_creation_completed: bool
    source_content_access_observed: bool
    filesystem_write_observed: bool
    executable_content_generated: bool
    executable_content_serialized: bool
    executable_input_content_present: bool
    content_integrity_verified: bool
    proposed_manifest_modified: bool
    proposed_manifest_activated: bool
    pricing_revalidation_boundary_reference: str
    pricing_revalidation_boundary_identity: str
    pricing_revalidation_descriptor_defined: bool
    pricing_revalidation_execution_authorized: bool
    pricing_revalidation_started: bool
    pricing_revalidation_result_present: bool
    pricing_revalidation_completed: bool
    fresh_provider_pricing_observed: bool
    credential_verification_boundary_reference: str
    credential_verification_boundary_identity: str
    credential_verification_descriptor_defined: bool
    credential_verification_execution_authorized: bool
    credential_verification_started: bool
    credential_verification_result_present: bool
    credential_verification_completed: bool
    credential_configuration_verified: bool
    credential_or_secret_access_observed: bool
    environment_access_observed: bool
    filesystem_access_observed: bool
    network_access_observed: bool
    provider_authentication_probe_performed: bool
    input_run_manifest_readiness_reference: str
    input_run_manifest_readiness_identity: str
    candidate_input_set_identity: str
    proposed_manifest_reference: str
    proposed_manifest_identity: str
    current_runtime_integrity_reference: str
    current_runtime_integrity_identity: str
    reservation_bound_reference: str
    reservation_bound_identity: str
    candidate_input_metadata_defined: bool
    proposed_manifest_defined: bool
    pre_call_reservation_created: bool
    ledger_entry_created: bool
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
    zero_production_proof: str
    blocker_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __init__(self, **values: Any) -> None:
        _exact_fields(values, _EVIDENCE_FIELDS)

        locked_values = {
            "schema_version": _SCHEMA,
            "evidence_reference": _EVIDENCE_REFERENCE,
            "locked_repository_baseline": _REPOSITORY_BASELINE,
            "locked_phase09_baseline": _PHASE09_BASELINE,
            "reconciliation_state": (
                ShadowPhase11SuccessorExecutableInputBoundaryReconciliationStateV1
                .EXECUTABLE_INPUT_BOUNDARY_RECONCILED_READINESS_BLOCKED
            ),
            "predecessor_status": (
                ShadowPhase11SuccessorExecutableInputPredecessorStatusV1
                .PREDECESSOR_SUCCESSOR_RECONCILIATION_PRESERVED
            ),
            "predecessor_successor_reconciliation_reference": (
                _PREDECESSOR_REFERENCE
            ),
            "predecessor_successor_reconciliation_identity": (
                _PREDECESSOR_IDENTITY
            ),
            "executable_input_creation_boundary_reference": (
                _EXECUTABLE_INPUT_BOUNDARY_REFERENCE
            ),
            "executable_input_creation_boundary_identity": (
                _EXECUTABLE_INPUT_BOUNDARY_IDENTITY
            ),
            "pricing_revalidation_boundary_reference": (
                _PRICING_BOUNDARY_REFERENCE
            ),
            "pricing_revalidation_boundary_identity": (
                _PRICING_BOUNDARY_IDENTITY
            ),
            "credential_verification_boundary_reference": (
                _CREDENTIAL_BOUNDARY_REFERENCE
            ),
            "credential_verification_boundary_identity": (
                _CREDENTIAL_BOUNDARY_IDENTITY
            ),
            "input_run_manifest_readiness_reference": _READINESS_REFERENCE,
            "input_run_manifest_readiness_identity": _READINESS_IDENTITY,
            "candidate_input_set_identity": _CANDIDATE_INPUT_SET_IDENTITY,
            "proposed_manifest_reference": _PROPOSED_MANIFEST_REFERENCE,
            "proposed_manifest_identity": _PROPOSED_MANIFEST_IDENTITY,
            "current_runtime_integrity_reference": _RUNTIME_REFERENCE,
            "current_runtime_integrity_identity": _RUNTIME_IDENTITY,
            "reservation_bound_reference": _RESERVATION_REFERENCE,
            "reservation_bound_identity": _RESERVATION_IDENTITY,
            "launch_readiness": (
                ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
            ),
            "production_effect": "NONE",
            "zero_production_proof": "PROVEN_NONE",
        }
        true_fields = (
            "executable_input_creation_descriptor_defined",
            "pricing_revalidation_descriptor_defined",
            "credential_verification_descriptor_defined",
            "candidate_input_metadata_defined",
            "proposed_manifest_defined",
        )
        false_fields = (
            "predecessor_successor_reconciliation_mutated",
            "predecessor_successor_reconciliation_transitioned",
            "predecessor_successor_reconciliation_current_authority",
            "executable_input_creation_execution_authorized",
            "executable_input_creation_started",
            "executable_input_creation_result_present",
            "executable_input_creation_completed",
            "source_content_access_observed",
            "filesystem_write_observed",
            "executable_content_generated",
            "executable_content_serialized",
            "executable_input_content_present",
            "content_integrity_verified",
            "proposed_manifest_modified",
            "proposed_manifest_activated",
            "pricing_revalidation_execution_authorized",
            "pricing_revalidation_started",
            "pricing_revalidation_result_present",
            "pricing_revalidation_completed",
            "fresh_provider_pricing_observed",
            "credential_verification_execution_authorized",
            "credential_verification_started",
            "credential_verification_result_present",
            "credential_verification_completed",
            "credential_configuration_verified",
            "credential_or_secret_access_observed",
            "environment_access_observed",
            "filesystem_access_observed",
            "network_access_observed",
            "provider_authentication_probe_performed",
            "pre_call_reservation_created",
            "ledger_entry_created",
            "provider_request_created",
            "runtime_invocation_authorized",
            "provider_call_authorized",
            "provider_transmission_authorized",
            "run_size_authorized",
            "manifest_activation_authorized",
            "launch_authorized",
            "production_authorized",
        )
        normalized = {
            name: _exact(values[name], expected, name)
            for name, expected in locked_values.items()
        }
        normalized.update(
            {
                name: _exact_bool(values[name], True, name)
                for name in true_fields
            }
        )
        normalized.update(
            {
                name: _exact_bool(values[name], False, name)
                for name in false_fields
            }
        )
        normalized["blocker_codes"] = _canonical_codes(
            values["blocker_codes"],
            _BLOCKERS,
            "blocker codes",
        )
        normalized["reason_codes"] = _canonical_codes(
            values["reason_codes"],
            _REASONS,
            "reason codes",
        )

        for name in _EVIDENCE_FIELDS - {"evidence_id"}:
            object.__setattr__(self, name, normalized[name])

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
            raise ShadowPhase11SuccessorExecutableInputBoundaryReconciliationValidationError(
                "supplied evidence identity does not match"
            )
        object.__setattr__(self, "evidence_id", identity)

    @property
    def identity(self) -> str:
        """Return the canonical evidence identity."""

        return self.evidence_id


def get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1(
) -> ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1:
    """Return the immutable executable-input successor evidence."""

    return ShadowPhase11SuccessorExecutableInputBoundaryReconciliationEvidenceV1(
        schema_version=_SCHEMA,
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        locked_repository_baseline=_REPOSITORY_BASELINE,
        locked_phase09_baseline=_PHASE09_BASELINE,
        reconciliation_state=(
            ShadowPhase11SuccessorExecutableInputBoundaryReconciliationStateV1
            .EXECUTABLE_INPUT_BOUNDARY_RECONCILED_READINESS_BLOCKED
        ),
        predecessor_status=(
            ShadowPhase11SuccessorExecutableInputPredecessorStatusV1
            .PREDECESSOR_SUCCESSOR_RECONCILIATION_PRESERVED
        ),
        predecessor_successor_reconciliation_reference=(
            _PREDECESSOR_REFERENCE
        ),
        predecessor_successor_reconciliation_identity=_PREDECESSOR_IDENTITY,
        predecessor_successor_reconciliation_mutated=False,
        predecessor_successor_reconciliation_transitioned=False,
        predecessor_successor_reconciliation_current_authority=False,
        executable_input_creation_boundary_reference=(
            _EXECUTABLE_INPUT_BOUNDARY_REFERENCE
        ),
        executable_input_creation_boundary_identity=(
            _EXECUTABLE_INPUT_BOUNDARY_IDENTITY
        ),
        executable_input_creation_descriptor_defined=True,
        executable_input_creation_execution_authorized=False,
        executable_input_creation_started=False,
        executable_input_creation_result_present=False,
        executable_input_creation_completed=False,
        source_content_access_observed=False,
        filesystem_write_observed=False,
        executable_content_generated=False,
        executable_content_serialized=False,
        executable_input_content_present=False,
        content_integrity_verified=False,
        proposed_manifest_modified=False,
        proposed_manifest_activated=False,
        pricing_revalidation_boundary_reference=_PRICING_BOUNDARY_REFERENCE,
        pricing_revalidation_boundary_identity=_PRICING_BOUNDARY_IDENTITY,
        pricing_revalidation_descriptor_defined=True,
        pricing_revalidation_execution_authorized=False,
        pricing_revalidation_started=False,
        pricing_revalidation_result_present=False,
        pricing_revalidation_completed=False,
        fresh_provider_pricing_observed=False,
        credential_verification_boundary_reference=(
            _CREDENTIAL_BOUNDARY_REFERENCE
        ),
        credential_verification_boundary_identity=(
            _CREDENTIAL_BOUNDARY_IDENTITY
        ),
        credential_verification_descriptor_defined=True,
        credential_verification_execution_authorized=False,
        credential_verification_started=False,
        credential_verification_result_present=False,
        credential_verification_completed=False,
        credential_configuration_verified=False,
        credential_or_secret_access_observed=False,
        environment_access_observed=False,
        filesystem_access_observed=False,
        network_access_observed=False,
        provider_authentication_probe_performed=False,
        input_run_manifest_readiness_reference=_READINESS_REFERENCE,
        input_run_manifest_readiness_identity=_READINESS_IDENTITY,
        candidate_input_set_identity=_CANDIDATE_INPUT_SET_IDENTITY,
        proposed_manifest_reference=_PROPOSED_MANIFEST_REFERENCE,
        proposed_manifest_identity=_PROPOSED_MANIFEST_IDENTITY,
        current_runtime_integrity_reference=_RUNTIME_REFERENCE,
        current_runtime_integrity_identity=_RUNTIME_IDENTITY,
        reservation_bound_reference=_RESERVATION_REFERENCE,
        reservation_bound_identity=_RESERVATION_IDENTITY,
        candidate_input_metadata_defined=True,
        proposed_manifest_defined=True,
        pre_call_reservation_created=False,
        ledger_entry_created=False,
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
        zero_production_proof="PROVEN_NONE",
        blocker_codes=_BLOCKERS,
        reason_codes=_REASONS,
    )
