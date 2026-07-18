"""Immutable Phase 11 successor blocked-readiness reconciliation evidence.

This module reconciles static lineage facts only.  It does not mutate the
historical gate, execute a runtime or provider, create executable input,
activate a manifest, reserve funds, or grant operational authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    ShadowPhase11CredentialSafeLaunchGateStateV1,
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1 import (
    get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1,
)
from engine.phase_11_shadow_pilot_input_run_manifest_readiness_v1 import (
    ShadowPhase11PilotInputReadinessStateV1,
    ShadowPhase11PilotManifestReadinessStateV1,
    get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotPricingRevalidationStatusV1,
)
from engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1 import (
    ShadowPhase11PreCallReservationStateV1,
    get_phase_11_shadow_pilot_pre_call_reservation_bound_v1,
)
from engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1 import (
    get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1,
)


_SCHEMA = "phase11-shadow-pilot-blocked-readiness-reconciliation-v1"
_EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_BLOCKED_READINESS_RECONCILIATION_001"
)
_REPOSITORY_BASELINE = "b4ddee91d1eae0ffe5ce4597aace61449a154491"
_PHASE09_BASELINE = "a84375fa85c2f318944adfe57aaabac6e43c219c"
_GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
_GATE_IDENTITY = (
    "77b7bbb6782a4710b04abd16547ba5fd94e8311d09cad0cd0187fc7b8313c06b"
)
_RUNTIME_REFERENCE = (
    "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
)
_RUNTIME_IDENTITY = (
    "72342b2390f32463f6d5104f47d3dc29ff5067349daec61a4fe5565de725b51e"
)
_READINESS_REFERENCE = (
    "PHASE_11_PILOT_INPUT_RUN_MANIFEST_READINESS_001"
)
_READINESS_IDENTITY = (
    "9dffc3370346370284fe5a630a32e78be6def065428060ce70eea8cddf0fd228"
)
_INPUT_SET_IDENTITY = (
    "1be1ead19357168a8dbae5b1018b6a2f484fd2a01723e63d4e4b06b790624f0c"
)
_MANIFEST_IDENTITY = (
    "d96e281f574beff0e767ab94bf4d7a04d3d180291e4ad16a0069fcd277ac060a"
)
_PRICING_REFERENCE = "PHASE_11_PILOT_PRICING_COST_BOUND_EVIDENCE_001"
_PRICING_IDENTITY = (
    "9b986028159efa107da3d2625422ad937d19a65631e5ea95926e006f28329d31"
)
_RESERVATION_REFERENCE = "PHASE_11_PILOT_PRE_CALL_RESERVATION_BOUND_001"
_RESERVATION_IDENTITY = (
    "424a3a332c31a3143ee3a4b6ab8b37b7ec440ea0fcf3c6a01566e451bb11cb70"
)
_HISTORICAL_BLOCKERS = (
    "AUTHENTICATION_TERMINAL_CLASSIFICATION_NOT_VERIFIED",
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "PILOT_INPUT_ABSENT",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "RUN_MANIFEST_ABSENT",
    "RUNTIME_NO_RETRY_ENFORCEMENT_NOT_VERIFIED",
)
_SUCCESSOR_BLOCKERS = (
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
_HASH = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ShadowPhase11BlockedReadinessReconciliationValidationError(ValueError):
    """Raised when successor blocked-readiness evidence is invalid."""


class ShadowPhase11BlockedReadinessReconciliationStateV1(StrEnum):
    """The sole successor reconciliation state."""

    RECONCILED_SUCCESSOR_READINESS_BLOCKED = (
        "RECONCILED_SUCCESSOR_READINESS_BLOCKED"
    )


class ShadowPhase11BlockedReadinessPredecessorStatusV1(StrEnum):
    """The historical gate is lineage only."""

    HISTORICAL_BLOCKED_GATE_PREDECESSOR_ONLY = (
        "HISTORICAL_BLOCKED_GATE_PREDECESSOR_ONLY"
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
    raise ShadowPhase11BlockedReadinessReconciliationValidationError(
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
        raise ShadowPhase11BlockedReadinessReconciliationValidationError(
            "value is not canonical JSON"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return lowercase SHA-256 for exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11BlockedReadinessReconciliationValidationError(
            "sha256 input must be bytes"
        )
    return sha256(value).hexdigest()


def _exact(value: Any, expected: Any, field_name: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ShadowPhase11BlockedReadinessReconciliationValidationError(
            f"{field_name} must equal the locked value"
        )


def _exact_bool(value: Any, expected: bool, field_name: str) -> None:
    if type(value) is not bool or value is not expected:
        raise ShadowPhase11BlockedReadinessReconciliationValidationError(
            f"{field_name} must be {expected}"
        )


def _canonical_codes(
    value: Any,
    expected: tuple[str, ...] | None,
    field_name: str,
) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowPhase11BlockedReadinessReconciliationValidationError(
            f"{field_name} must be a non-empty sequence"
        )
    if any(
        type(code) is not str or _REASON.fullmatch(code) is None
        for code in value
    ):
        raise ShadowPhase11BlockedReadinessReconciliationValidationError(
            f"{field_name} contains an invalid code"
        )
    if len(set(value)) != len(value):
        raise ShadowPhase11BlockedReadinessReconciliationValidationError(
            f"{field_name} must contain unique codes"
        )
    normalized = tuple(sorted(value))
    if expected is not None:
        if set(normalized) != set(expected) or len(normalized) != len(expected):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                f"{field_name} does not match the exact required set"
            )
        return expected
    return normalized


def _payload(
    evidence: "ShadowPhase11BlockedReadinessReconciliationEvidenceV1",
) -> dict[str, Any]:
    return {
        name: getattr(evidence, name)
        for name in evidence.__dataclass_fields__
        if name != "evidence_id"
    }


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11BlockedReadinessReconciliationEvidenceV1:
    """Immutable, blocked, zero-authority successor lineage evidence."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    reconciliation_state: ShadowPhase11BlockedReadinessReconciliationStateV1
    historical_gate_reference: str
    historical_gate_identity: str
    historical_gate_state: ShadowPhase11CredentialSafeLaunchGateStateV1
    historical_gate_blocker_codes: tuple[str, ...]
    historical_pilot_input_present: bool
    historical_run_manifest_present: bool
    predecessor_status: ShadowPhase11BlockedReadinessPredecessorStatusV1
    historical_gate_mutated: bool
    historical_gate_transitioned: bool
    historical_gate_current_readiness_authority: bool
    current_runtime_integrity_reference: str
    current_runtime_integrity_identity: str
    readiness_evidence_reference: str
    readiness_evidence_identity: str
    candidate_input_set_identity: str
    proposed_manifest_identity: str
    input_readiness_state: ShadowPhase11PilotInputReadinessStateV1
    manifest_readiness_state: ShadowPhase11PilotManifestReadinessStateV1
    successor_current_runtime_integrity_recognized: bool
    successor_candidate_input_metadata_defined: bool
    successor_proposed_manifest_defined: bool
    executable_input_content_present: bool
    proposed_manifest_activated: bool
    credential_configuration_verified: bool
    pricing_evidence_reference: str
    pricing_evidence_identity: str
    pricing_revalidation_required: bool
    pricing_revalidation_status: ShadowPhase11PilotPricingRevalidationStatusV1
    pricing_revalidation_completed: bool
    reservation_bound_reference: str
    reservation_bound_identity: str
    pre_call_reservation_required: bool
    pre_call_reservation_state: ShadowPhase11PreCallReservationStateV1
    pre_call_reservation_created: bool
    ledger_entry_created: bool
    provider_request_created: bool
    runtime_invocation_authorized: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    run_size_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    successor_blocker_codes: tuple[str, ...]
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
        historical_gate_reference: str,
        historical_gate_identity: str,
        historical_gate_state: ShadowPhase11CredentialSafeLaunchGateStateV1,
        historical_gate_blocker_codes: tuple[str, ...],
        historical_pilot_input_present: bool,
        historical_run_manifest_present: bool,
        predecessor_status: ShadowPhase11BlockedReadinessPredecessorStatusV1,
        historical_gate_mutated: bool,
        historical_gate_transitioned: bool,
        historical_gate_current_readiness_authority: bool,
        current_runtime_integrity_reference: str,
        current_runtime_integrity_identity: str,
        readiness_evidence_reference: str,
        readiness_evidence_identity: str,
        candidate_input_set_identity: str,
        proposed_manifest_identity: str,
        input_readiness_state: ShadowPhase11PilotInputReadinessStateV1,
        manifest_readiness_state: ShadowPhase11PilotManifestReadinessStateV1,
        successor_current_runtime_integrity_recognized: bool,
        successor_candidate_input_metadata_defined: bool,
        successor_proposed_manifest_defined: bool,
        executable_input_content_present: bool,
        proposed_manifest_activated: bool,
        credential_configuration_verified: bool,
        pricing_evidence_reference: str,
        pricing_evidence_identity: str,
        pricing_revalidation_required: bool,
        pricing_revalidation_status: ShadowPhase11PilotPricingRevalidationStatusV1,
        pricing_revalidation_completed: bool,
        reservation_bound_reference: str,
        reservation_bound_identity: str,
        pre_call_reservation_required: bool,
        pre_call_reservation_state: ShadowPhase11PreCallReservationStateV1,
        pre_call_reservation_created: bool,
        ledger_entry_created: bool,
        provider_request_created: bool,
        runtime_invocation_authorized: bool,
        provider_call_authorized: bool,
        provider_transmission_authorized: bool,
        run_size_authorized: bool,
        launch_authorized: bool,
        production_authorized: bool,
        launch_readiness: ShadowPhase11PilotLaunchReadinessV1,
        successor_blocker_codes: tuple[str, ...],
        production_effect: str,
        zero_production_effect_proof: str,
        reason_codes: tuple[str, ...],
        **unknown_fields: Any,
    ) -> None:
        if unknown_fields:
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "unknown reconciliation evidence fields are forbidden"
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
                "historical_gate_reference",
                historical_gate_reference,
                _GATE_REFERENCE,
            ),
            (
                "historical_gate_identity",
                historical_gate_identity,
                _GATE_IDENTITY,
            ),
            (
                "current_runtime_integrity_reference",
                current_runtime_integrity_reference,
                _RUNTIME_REFERENCE,
            ),
            (
                "current_runtime_integrity_identity",
                current_runtime_integrity_identity,
                _RUNTIME_IDENTITY,
            ),
            (
                "readiness_evidence_reference",
                readiness_evidence_reference,
                _READINESS_REFERENCE,
            ),
            (
                "readiness_evidence_identity",
                readiness_evidence_identity,
                _READINESS_IDENTITY,
            ),
            (
                "candidate_input_set_identity",
                candidate_input_set_identity,
                _INPUT_SET_IDENTITY,
            ),
            (
                "proposed_manifest_identity",
                proposed_manifest_identity,
                _MANIFEST_IDENTITY,
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
                "reservation_bound_reference",
                reservation_bound_reference,
                _RESERVATION_REFERENCE,
            ),
            (
                "reservation_bound_identity",
                reservation_bound_identity,
                _RESERVATION_IDENTITY,
            ),
        ):
            _exact(value, expected, field_name)
        if (
            historical_gate_state
            is not ShadowPhase11CredentialSafeLaunchGateStateV1.BLOCKED
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "historical_gate_state must remain BLOCKED"
            )
        if (
            type(historical_gate_blocker_codes) not in (tuple, list)
            or tuple(historical_gate_blocker_codes) != _HISTORICAL_BLOCKERS
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "historical_gate_blocker_codes must preserve predecessor facts"
            )
        historical_blockers = _HISTORICAL_BLOCKERS
        if (
            predecessor_status
            is not ShadowPhase11BlockedReadinessPredecessorStatusV1
            .HISTORICAL_BLOCKED_GATE_PREDECESSOR_ONLY
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "predecessor_status must remain historical-only"
            )
        if (
            input_readiness_state
            is not ShadowPhase11PilotInputReadinessStateV1
            .CANDIDATE_INPUT_DEFINED_NOT_AUTHORIZED
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "input_readiness_state must remain non-authorizing"
            )
        if (
            manifest_readiness_state
            is not ShadowPhase11PilotManifestReadinessStateV1
            .PROPOSED_MANIFEST_DEFINED_NOT_ACTIVATED
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "manifest_readiness_state must remain non-activated"
            )
        if (
            pricing_revalidation_status
            is not ShadowPhase11PilotPricingRevalidationStatusV1
            .REQUIRED_NOT_COMPLETED
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "pricing revalidation must remain incomplete"
            )
        if (
            pre_call_reservation_state
            is not ShadowPhase11PreCallReservationStateV1.BOUND_NOT_RESERVED
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "pre-call reservation must remain uncreated"
            )
        if (
            launch_readiness
            is not ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "launch readiness must remain blocked"
            )

        for field_name, value in (
            ("historical_pilot_input_present", historical_pilot_input_present),
            (
                "historical_run_manifest_present",
                historical_run_manifest_present,
            ),
            ("historical_gate_mutated", historical_gate_mutated),
            ("historical_gate_transitioned", historical_gate_transitioned),
            (
                "historical_gate_current_readiness_authority",
                historical_gate_current_readiness_authority,
            ),
            (
                "executable_input_content_present",
                executable_input_content_present,
            ),
            ("proposed_manifest_activated", proposed_manifest_activated),
            (
                "credential_configuration_verified",
                credential_configuration_verified,
            ),
            (
                "pricing_revalidation_completed",
                pricing_revalidation_completed,
            ),
            ("pre_call_reservation_created", pre_call_reservation_created),
            ("ledger_entry_created", ledger_entry_created),
            ("provider_request_created", provider_request_created),
            ("runtime_invocation_authorized", runtime_invocation_authorized),
            ("provider_call_authorized", provider_call_authorized),
            (
                "provider_transmission_authorized",
                provider_transmission_authorized,
            ),
            ("run_size_authorized", run_size_authorized),
            ("launch_authorized", launch_authorized),
            ("production_authorized", production_authorized),
        ):
            _exact_bool(value, False, field_name)
        for field_name, value in (
            (
                "successor_current_runtime_integrity_recognized",
                successor_current_runtime_integrity_recognized,
            ),
            (
                "successor_candidate_input_metadata_defined",
                successor_candidate_input_metadata_defined,
            ),
            (
                "successor_proposed_manifest_defined",
                successor_proposed_manifest_defined,
            ),
            ("pricing_revalidation_required", pricing_revalidation_required),
            ("pre_call_reservation_required", pre_call_reservation_required),
        ):
            _exact_bool(value, True, field_name)
        _exact(production_effect, "NONE", "production_effect")
        _exact(
            zero_production_effect_proof,
            "PROVEN_NONE",
            "zero_production_effect_proof",
        )
        successor_blockers = _canonical_codes(
            successor_blocker_codes,
            _SUCCESSOR_BLOCKERS,
            "successor_blocker_codes",
        )
        normalized_reasons = _canonical_codes(
            reason_codes,
            None,
            "reason_codes",
        )

        values = {
            "schema_version": schema_version,
            "evidence_reference": evidence_reference,
            "locked_repository_baseline": locked_repository_baseline,
            "locked_phase09_baseline": locked_phase09_baseline,
            "reconciliation_state": (
                ShadowPhase11BlockedReadinessReconciliationStateV1
                .RECONCILED_SUCCESSOR_READINESS_BLOCKED
            ),
            "historical_gate_reference": historical_gate_reference,
            "historical_gate_identity": historical_gate_identity,
            "historical_gate_state": historical_gate_state,
            "historical_gate_blocker_codes": historical_blockers,
            "historical_pilot_input_present": historical_pilot_input_present,
            "historical_run_manifest_present": (
                historical_run_manifest_present
            ),
            "predecessor_status": predecessor_status,
            "historical_gate_mutated": historical_gate_mutated,
            "historical_gate_transitioned": historical_gate_transitioned,
            "historical_gate_current_readiness_authority": (
                historical_gate_current_readiness_authority
            ),
            "current_runtime_integrity_reference": (
                current_runtime_integrity_reference
            ),
            "current_runtime_integrity_identity": (
                current_runtime_integrity_identity
            ),
            "readiness_evidence_reference": readiness_evidence_reference,
            "readiness_evidence_identity": readiness_evidence_identity,
            "candidate_input_set_identity": candidate_input_set_identity,
            "proposed_manifest_identity": proposed_manifest_identity,
            "input_readiness_state": input_readiness_state,
            "manifest_readiness_state": manifest_readiness_state,
            "successor_current_runtime_integrity_recognized": (
                successor_current_runtime_integrity_recognized
            ),
            "successor_candidate_input_metadata_defined": (
                successor_candidate_input_metadata_defined
            ),
            "successor_proposed_manifest_defined": (
                successor_proposed_manifest_defined
            ),
            "executable_input_content_present": (
                executable_input_content_present
            ),
            "proposed_manifest_activated": proposed_manifest_activated,
            "credential_configuration_verified": (
                credential_configuration_verified
            ),
            "pricing_evidence_reference": pricing_evidence_reference,
            "pricing_evidence_identity": pricing_evidence_identity,
            "pricing_revalidation_required": pricing_revalidation_required,
            "pricing_revalidation_status": pricing_revalidation_status,
            "pricing_revalidation_completed": (
                pricing_revalidation_completed
            ),
            "reservation_bound_reference": reservation_bound_reference,
            "reservation_bound_identity": reservation_bound_identity,
            "pre_call_reservation_required": pre_call_reservation_required,
            "pre_call_reservation_state": pre_call_reservation_state,
            "pre_call_reservation_created": pre_call_reservation_created,
            "ledger_entry_created": ledger_entry_created,
            "provider_request_created": provider_request_created,
            "runtime_invocation_authorized": runtime_invocation_authorized,
            "provider_call_authorized": provider_call_authorized,
            "provider_transmission_authorized": (
                provider_transmission_authorized
            ),
            "run_size_authorized": run_size_authorized,
            "launch_authorized": launch_authorized,
            "production_authorized": production_authorized,
            "launch_readiness": launch_readiness,
            "successor_blocker_codes": successor_blockers,
            "production_effect": production_effect,
            "zero_production_effect_proof": zero_production_effect_proof,
            "reason_codes": normalized_reasons,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)
        computed = sha256_hex(canonical_json_bytes(_payload(self)))
        if (
            evidence_id is not None
            and (type(evidence_id) is not str or evidence_id != computed)
        ):
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "evidence_id does not match canonical material"
            )
        if _HASH.fullmatch(computed) is None:
            raise ShadowPhase11BlockedReadinessReconciliationValidationError(
                "evidence identity computation failed"
            )
        object.__setattr__(self, "evidence_id", computed)

    @property
    def identity(self) -> str:
        return self.evidence_id


def _make_evidence(
) -> ShadowPhase11BlockedReadinessReconciliationEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    runtime = get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1()
    readiness = (
        get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1()
    )
    pricing = get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1()
    reservation = get_phase_11_shadow_pilot_pre_call_reservation_bound_v1()
    return ShadowPhase11BlockedReadinessReconciliationEvidenceV1(
        schema_version=_SCHEMA,
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        locked_repository_baseline=_REPOSITORY_BASELINE,
        locked_phase09_baseline=_PHASE09_BASELINE,
        historical_gate_reference=gate.evidence_reference,
        historical_gate_identity=gate.identity,
        historical_gate_state=gate.gate_state,
        historical_gate_blocker_codes=gate.blocker_codes,
        historical_pilot_input_present=gate.pilot_input_present,
        historical_run_manifest_present=gate.run_manifest_present,
        predecessor_status=(
            ShadowPhase11BlockedReadinessPredecessorStatusV1
            .HISTORICAL_BLOCKED_GATE_PREDECESSOR_ONLY
        ),
        historical_gate_mutated=False,
        historical_gate_transitioned=False,
        historical_gate_current_readiness_authority=False,
        current_runtime_integrity_reference=runtime.evidence_reference,
        current_runtime_integrity_identity=runtime.identity,
        readiness_evidence_reference=readiness.evidence_reference,
        readiness_evidence_identity=readiness.identity,
        candidate_input_set_identity=(
            readiness.proposed_manifest.candidate_input_set_identity
        ),
        proposed_manifest_identity=readiness.proposed_manifest.identity,
        input_readiness_state=readiness.input_readiness_state,
        manifest_readiness_state=readiness.manifest_readiness_state,
        successor_current_runtime_integrity_recognized=True,
        successor_candidate_input_metadata_defined=(
            readiness.candidate_input_defined
        ),
        successor_proposed_manifest_defined=readiness.run_manifest_defined,
        executable_input_content_present=(
            readiness.executable_input_content_present
        ),
        proposed_manifest_activated=readiness.run_manifest_activated,
        credential_configuration_verified=False,
        pricing_evidence_reference=pricing.evidence_reference,
        pricing_evidence_identity=pricing.identity,
        pricing_revalidation_required=True,
        pricing_revalidation_status=pricing.pricing_revalidation_status,
        pricing_revalidation_completed=False,
        reservation_bound_reference=reservation.evidence_reference,
        reservation_bound_identity=reservation.identity,
        pre_call_reservation_required=True,
        pre_call_reservation_state=reservation.reservation_state,
        pre_call_reservation_created=False,
        ledger_entry_created=False,
        provider_request_created=False,
        runtime_invocation_authorized=False,
        provider_call_authorized=False,
        provider_transmission_authorized=False,
        run_size_authorized=False,
        launch_authorized=False,
        production_authorized=False,
        launch_readiness=(
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        successor_blocker_codes=_SUCCESSOR_BLOCKERS,
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
        reason_codes=("SUCCESSOR_READINESS_RECONCILED_BLOCKED",),
    )


_EVIDENCE = _make_evidence()


def get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1(
) -> ShadowPhase11BlockedReadinessReconciliationEvidenceV1:
    """Return immutable successor blocked-readiness reconciliation."""

    return _EVIDENCE


__all__ = (
    "ShadowPhase11BlockedReadinessPredecessorStatusV1",
    "ShadowPhase11BlockedReadinessReconciliationEvidenceV1",
    "ShadowPhase11BlockedReadinessReconciliationStateV1",
    "ShadowPhase11BlockedReadinessReconciliationValidationError",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1",
    "sha256_hex",
)
