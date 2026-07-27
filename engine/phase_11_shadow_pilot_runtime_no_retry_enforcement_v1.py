"""Immutable Phase 11 pilot-profile one-attempt/no-retry evidence.

This module stores static, repository-owned observations only.  It does not
import or execute the provider runtime, inspect source files or Git, access
configuration or credentials, or grant operational authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
    ShadowPhase11PilotProviderRoleV1,
)


_PROBE_SCHEMA = "phase11-shadow-pilot-runtime-no-retry-probe-result-v1"
_EVIDENCE_SCHEMA = "phase11-shadow-pilot-runtime-no-retry-enforcement-v1"
_EVIDENCE_REFERENCE = "PHASE_11_PILOT_RUNTIME_NO_RETRY_ENFORCEMENT_001"
_GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
_GATE_IDENTITY = "29a07dc2cb644aeb4dbdc9dc00e4da79b5fa3d1486e98dabdcadb1e40140debb"
_REPOSITORY_BASELINE = "f4ff152d10c18cb41488c963eeb27c7db973f79a"
_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"
_RUNTIME_PATH = "engine/phase_11_shadow_provider_runtime_v1.py"
_RUNTIME_SHA256 = "853bd420bef56bd560abf2e65baccc8e33f17d549bfd60a4b4ace5917b56cf38"
_RUNTIME_BLOB = "572a6716836e723287b4aa2a835ed985378fbf6a"
_RUNTIME_BYTE_LENGTH = 38310
_RUNTIME_CLASS = "ShadowProviderRuntimeV1"
_RUNTIME_METHOD = "invoke"
_HASH64 = re.compile(r"^[0-9a-f]{64}$")
_HASH40 = re.compile(r"^[0-9a-f]{40}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")


class ShadowPhase11RuntimeNoRetryEnforcementValidationError(ValueError):
    """Raised when static pilot-profile enforcement evidence is invalid."""


class ShadowPhase11RuntimeNoRetryEnforcementStateV1(StrEnum):
    """The sole enforcement claim authorized by this evidence."""

    VERIFIED_ONE_ATTEMPT_NO_RETRY_FOR_PILOT_PROFILE = (
        "VERIFIED_ONE_ATTEMPT_NO_RETRY_FOR_PILOT_PROFILE"
    )


class ShadowPhase11RuntimeNoRetryProbeKindV1(StrEnum):
    """The complete deterministic probe set frozen by the RED."""

    SUCCESS = "SUCCESS"
    RETRYABLE_TIMEOUT = "RETRYABLE_TIMEOUT"
    RETRYABLE_TRANSPORT_FAILURE = "RETRYABLE_TRANSPORT_FAILURE"


_PROBE_ORDER = {
    ShadowPhase11RuntimeNoRetryProbeKindV1.SUCCESS: 0,
    ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TIMEOUT: 1,
    ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TRANSPORT_FAILURE: 2,
}
_PROBE_OUTCOMES = {
    ShadowPhase11RuntimeNoRetryProbeKindV1.SUCCESS: "SUCCESS",
    ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TIMEOUT: "TIMEOUT",
    ShadowPhase11RuntimeNoRetryProbeKindV1.RETRYABLE_TRANSPORT_FAILURE:
        "TRANSPORT_FAILURE",
}


def _canonical_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic canonical UTF-8 JSON."""

    try:
        rendered = json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        escaped = "".join(
            character
            if ord(character) < 128
            else "".join(
                f"\\x{byte:02x}" for byte in character.encode("utf-8")
            )
            for character in rendered
        )
        return escaped.encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            "non-canonical evidence value"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return lowercase SHA-256 for exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            "sha256 input must be bytes"
        )
    return sha256(value).hexdigest()


def _identity(material: Mapping[str, Any], supplied: Any, label: str) -> str:
    result = sha256_hex(canonical_json_bytes(material))
    if supplied is not None:
        if (
            type(supplied) is not str
            or _HASH64.fullmatch(supplied) is None
            or supplied != result
        ):
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                f"{label} mismatch"
            )
    return result


def _exact_text(name: str, value: Any, expected: str) -> str:
    if type(value) is not str or value != expected:
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            f"invalid {name}"
        )
    return value


def _exact_bool(name: str, value: Any, expected: bool) -> bool:
    if type(value) is not bool or value is not expected:
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            f"invalid {name}"
        )
    return value


def _exact_int(name: str, value: Any, expected: int) -> int:
    if type(value) is not int or value != expected:
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            f"invalid {name}"
        )
    return value


def _exact_enum(name: str, value: Any, expected: Any) -> Any:
    if type(value) is not type(expected) or value is not expected:
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            f"invalid {name}"
        )
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            "invalid reason_codes"
        )
    result = tuple(sorted(value))
    if (
        len(set(result)) != len(result)
        or any(
            type(item) is not str or _REASON.fullmatch(item) is None
            for item in result
        )
    ):
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            "invalid reason_codes"
        )
    return result


def _outcome_text(value: Any) -> str:
    text = value.value if isinstance(value, StrEnum) else value
    if type(text) is not str:
        raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
            "invalid runtime_outcome"
        )
    return text


_PROBE_FIELDS = frozenset(
    (
        "schema_version",
        "probe_id",
        "probe_kind",
        "provider",
        "role",
        "runtime_outcome",
        "configured_maximum_attempts",
        "observed_transport_invocation_count",
        "observed_attempt_count",
        "second_transport_invocation_observed",
        "retry_delay_observed",
        "network_access_observed",
        "credential_access_observed",
        "account_access_observed",
        "ledger_mutation_observed",
        "reservation_creation_observed",
        "production_effect",
        "zero_production_effect_proof",
        "reason_codes",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11RuntimeNoRetryProbeResultV1:
    """Immutable result of one deterministic, in-memory runtime probe."""

    schema_version: str
    probe_id: str
    probe_kind: ShadowPhase11RuntimeNoRetryProbeKindV1
    provider: str
    role: ShadowPhase11PilotProviderRoleV1
    runtime_outcome: Any
    configured_maximum_attempts: int
    observed_transport_invocation_count: int
    observed_attempt_count: int
    second_transport_invocation_observed: bool
    retry_delay_observed: bool
    network_access_observed: bool
    credential_access_observed: bool
    account_access_observed: bool
    ledger_mutation_observed: bool
    reservation_creation_observed: bool
    production_effect: str
    zero_production_effect_proof: str
    reason_codes: tuple[str, ...]

    def __init__(self, **fields: Any) -> None:
        if frozenset(fields) != _PROBE_FIELDS:
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "invalid probe fields"
            )
        kind = fields["probe_kind"]
        if type(kind) is not ShadowPhase11RuntimeNoRetryProbeKindV1:
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "invalid probe_kind"
            )
        outcome = _outcome_text(fields["runtime_outcome"])
        if outcome != _PROBE_OUTCOMES[kind]:
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "probe outcome mismatch"
            )
        reasons = _reason_codes(fields["reason_codes"])
        values = {
            "schema_version": _exact_text(
                "schema_version", fields["schema_version"], _PROBE_SCHEMA
            ),
            "probe_kind": kind,
            "provider": _exact_text(
                "provider", fields["provider"], "DEEPSEEK"
            ),
            "role": _exact_enum(
                "role",
                fields["role"],
                ShadowPhase11PilotProviderRoleV1.PRIMARY,
            ),
            "runtime_outcome": fields["runtime_outcome"],
            "configured_maximum_attempts": _exact_int(
                "configured_maximum_attempts",
                fields["configured_maximum_attempts"],
                1,
            ),
            "observed_transport_invocation_count": _exact_int(
                "observed_transport_invocation_count",
                fields["observed_transport_invocation_count"],
                1,
            ),
            "observed_attempt_count": _exact_int(
                "observed_attempt_count", fields["observed_attempt_count"], 1
            ),
            "second_transport_invocation_observed": _exact_bool(
                "second_transport_invocation_observed",
                fields["second_transport_invocation_observed"],
                False,
            ),
            "retry_delay_observed": _exact_bool(
                "retry_delay_observed", fields["retry_delay_observed"], False
            ),
            "network_access_observed": _exact_bool(
                "network_access_observed",
                fields["network_access_observed"],
                False,
            ),
            "credential_access_observed": _exact_bool(
                "credential_access_observed",
                fields["credential_access_observed"],
                False,
            ),
            "account_access_observed": _exact_bool(
                "account_access_observed",
                fields["account_access_observed"],
                False,
            ),
            "ledger_mutation_observed": _exact_bool(
                "ledger_mutation_observed",
                fields["ledger_mutation_observed"],
                False,
            ),
            "reservation_creation_observed": _exact_bool(
                "reservation_creation_observed",
                fields["reservation_creation_observed"],
                False,
            ),
            "production_effect": _exact_text(
                "production_effect", fields["production_effect"], "NONE"
            ),
            "zero_production_effect_proof": _exact_text(
                "zero_production_effect_proof",
                fields["zero_production_effect_proof"],
                "PROVEN_NONE",
            ),
            "reason_codes": reasons,
        }
        material = {
            name: (
                item.value
                if isinstance(item, StrEnum)
                else item
            )
            for name, item in values.items()
        }
        material["runtime_outcome"] = outcome
        probe_id = _identity(
            material, fields["probe_id"], "probe identity"
        )
        normalized = {"probe_id": probe_id, **values}
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.probe_id

    @property
    def identity_material(self) -> Mapping[str, Any]:
        return {
            "schema_version": self.schema_version,
            "probe_kind": self.probe_kind.value,
            "provider": self.provider,
            "role": self.role.value,
            "runtime_outcome": _outcome_text(self.runtime_outcome),
            "configured_maximum_attempts":
                self.configured_maximum_attempts,
            "observed_transport_invocation_count":
                self.observed_transport_invocation_count,
            "observed_attempt_count": self.observed_attempt_count,
            "second_transport_invocation_observed":
                self.second_transport_invocation_observed,
            "retry_delay_observed": self.retry_delay_observed,
            "network_access_observed": self.network_access_observed,
            "credential_access_observed": self.credential_access_observed,
            "account_access_observed": self.account_access_observed,
            "ledger_mutation_observed": self.ledger_mutation_observed,
            "reservation_creation_observed":
                self.reservation_creation_observed,
            "production_effect": self.production_effect,
            "zero_production_effect_proof":
                self.zero_production_effect_proof,
            "reason_codes": self.reason_codes,
        }


_EVIDENCE_FIELDS = frozenset(
    (
        "schema_version",
        "evidence_id",
        "evidence_reference",
        "credential_safe_gate_reference",
        "credential_safe_gate_identity",
        "locked_repository_baseline",
        "locked_phase09_baseline",
        "runtime_source_path",
        "runtime_source_sha256",
        "runtime_git_blob_identity",
        "runtime_class_name",
        "runtime_invocation_method",
        "enforcement_state",
        "pilot_maximum_attempts",
        "provider_retry_authorized",
        "credential_retry_authorized",
        "authentication_retry_authorized",
        "runtime_no_retry_enforcement_verified",
        "generic_runtime_retry_capability_removed",
        "authentication_terminal_classification_verified",
        "credential_configuration_verified",
        "pricing_revalidation_completed",
        "pre_call_reservation_created",
        "pilot_input_present",
        "run_manifest_present",
        "provider_call_authorized",
        "provider_transmission_authorized",
        "reservation_creation_authorized",
        "ledger_mutation_authorized",
        "run_size_authorized",
        "launch_authorized",
        "production_authorized",
        "launch_readiness",
        "probe_results",
        "production_effect",
        "zero_production_effect_proof",
        "reason_codes",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1:
    """Static enforcement evidence for the locked pilot profile only."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    credential_safe_gate_reference: str
    credential_safe_gate_identity: str
    locked_repository_baseline: str
    locked_phase09_baseline: str
    runtime_source_path: str
    runtime_source_sha256: str
    runtime_git_blob_identity: str
    runtime_source_byte_length: int = field(init=False)
    runtime_class_name: str
    runtime_invocation_method: str
    enforcement_state: ShadowPhase11RuntimeNoRetryEnforcementStateV1
    pilot_maximum_attempts: int
    provider_retry_authorized: bool
    credential_retry_authorized: bool
    authentication_retry_authorized: bool
    runtime_no_retry_enforcement_verified: bool
    generic_runtime_retry_capability_removed: bool
    authentication_terminal_classification_verified: bool
    credential_configuration_verified: bool
    pricing_revalidation_completed: bool
    pre_call_reservation_created: bool
    pilot_input_present: bool
    run_manifest_present: bool
    provider_call_authorized: bool
    provider_transmission_authorized: bool
    reservation_creation_authorized: bool
    ledger_mutation_authorized: bool
    run_size_authorized: bool
    launch_authorized: bool
    production_authorized: bool
    launch_readiness: ShadowPhase11PilotLaunchReadinessV1
    probe_results: tuple[ShadowPhase11RuntimeNoRetryProbeResultV1, ...]
    production_effect: str
    zero_production_effect_proof: str
    reason_codes: tuple[str, ...]

    def __init__(self, **fields: Any) -> None:
        if frozenset(fields) != _EVIDENCE_FIELDS:
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "invalid evidence fields"
            )
        gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
        if (
            gate.evidence_reference != _GATE_REFERENCE
            or gate.identity != _GATE_IDENTITY
        ):
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "committed gate identity mismatch"
            )
        supplied_probes = fields["probe_results"]
        if type(supplied_probes) not in (tuple, list):
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "invalid probe_results"
            )
        probes = tuple(supplied_probes)
        if (
            len(probes) != 3
            or any(
                type(item) is not ShadowPhase11RuntimeNoRetryProbeResultV1
                for item in probes
            )
            or len({item.probe_kind for item in probes}) != 3
            or set(item.probe_kind for item in probes) != set(_PROBE_ORDER)
        ):
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "invalid probe set"
            )
        probes = tuple(sorted(probes, key=lambda item: _PROBE_ORDER[item.probe_kind]))
        source_sha = fields["runtime_source_sha256"]
        blob = fields["runtime_git_blob_identity"]
        if (
            type(source_sha) is not str
            or _HASH64.fullmatch(source_sha) is None
            or source_sha != _RUNTIME_SHA256
        ):
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "invalid runtime_source_sha256"
            )
        if (
            type(blob) is not str
            or _HASH40.fullmatch(blob) is None
            or blob != _RUNTIME_BLOB
        ):
            raise ShadowPhase11RuntimeNoRetryEnforcementValidationError(
                "invalid runtime_git_blob_identity"
            )
        reasons = _reason_codes(fields["reason_codes"])
        values = {
            "schema_version": _exact_text(
                "schema_version", fields["schema_version"], _EVIDENCE_SCHEMA
            ),
            "evidence_reference": _exact_text(
                "evidence_reference",
                fields["evidence_reference"],
                _EVIDENCE_REFERENCE,
            ),
            "credential_safe_gate_reference": _exact_text(
                "credential_safe_gate_reference",
                fields["credential_safe_gate_reference"],
                gate.evidence_reference,
            ),
            "credential_safe_gate_identity": _exact_text(
                "credential_safe_gate_identity",
                fields["credential_safe_gate_identity"],
                gate.identity,
            ),
            "locked_repository_baseline": _exact_text(
                "locked_repository_baseline",
                fields["locked_repository_baseline"],
                _REPOSITORY_BASELINE,
            ),
            "locked_phase09_baseline": _exact_text(
                "locked_phase09_baseline",
                fields["locked_phase09_baseline"],
                _PHASE09_BASELINE,
            ),
            "runtime_source_path": _exact_text(
                "runtime_source_path",
                fields["runtime_source_path"],
                _RUNTIME_PATH,
            ),
            "runtime_source_sha256": source_sha,
            "runtime_git_blob_identity": blob,
            "runtime_class_name": _exact_text(
                "runtime_class_name",
                fields["runtime_class_name"],
                _RUNTIME_CLASS,
            ),
            "runtime_invocation_method": _exact_text(
                "runtime_invocation_method",
                fields["runtime_invocation_method"],
                _RUNTIME_METHOD,
            ),
            "enforcement_state": _exact_enum(
                "enforcement_state",
                fields["enforcement_state"],
                ShadowPhase11RuntimeNoRetryEnforcementStateV1
                .VERIFIED_ONE_ATTEMPT_NO_RETRY_FOR_PILOT_PROFILE,
            ),
            "pilot_maximum_attempts": _exact_int(
                "pilot_maximum_attempts",
                fields["pilot_maximum_attempts"],
                gate.maximum_attempts,
            ),
            "provider_retry_authorized": _exact_bool(
                "provider_retry_authorized",
                fields["provider_retry_authorized"],
                gate.provider_retry_authorized,
            ),
            "credential_retry_authorized": _exact_bool(
                "credential_retry_authorized",
                fields["credential_retry_authorized"],
                gate.credential_retry_authorized,
            ),
            "authentication_retry_authorized": _exact_bool(
                "authentication_retry_authorized",
                fields["authentication_retry_authorized"],
                gate.authentication_retry_authorized,
            ),
            "runtime_no_retry_enforcement_verified": _exact_bool(
                "runtime_no_retry_enforcement_verified",
                fields["runtime_no_retry_enforcement_verified"],
                True,
            ),
            "generic_runtime_retry_capability_removed": _exact_bool(
                "generic_runtime_retry_capability_removed",
                fields["generic_runtime_retry_capability_removed"],
                False,
            ),
            "authentication_terminal_classification_verified": _exact_bool(
                "authentication_terminal_classification_verified",
                fields["authentication_terminal_classification_verified"],
                False,
            ),
            "credential_configuration_verified": _exact_bool(
                "credential_configuration_verified",
                fields["credential_configuration_verified"],
                gate.credential_configuration_verified,
            ),
            "pricing_revalidation_completed": _exact_bool(
                "pricing_revalidation_completed",
                fields["pricing_revalidation_completed"],
                False,
            ),
            "pre_call_reservation_created": _exact_bool(
                "pre_call_reservation_created",
                fields["pre_call_reservation_created"],
                False,
            ),
            "pilot_input_present": _exact_bool(
                "pilot_input_present", fields["pilot_input_present"], False
            ),
            "run_manifest_present": _exact_bool(
                "run_manifest_present", fields["run_manifest_present"], False
            ),
            "provider_call_authorized": _exact_bool(
                "provider_call_authorized",
                fields["provider_call_authorized"],
                gate.provider_call_authorized,
            ),
            "provider_transmission_authorized": _exact_bool(
                "provider_transmission_authorized",
                fields["provider_transmission_authorized"],
                gate.provider_transmission_authorized,
            ),
            "reservation_creation_authorized": _exact_bool(
                "reservation_creation_authorized",
                fields["reservation_creation_authorized"],
                gate.reservation_creation_authorized,
            ),
            "ledger_mutation_authorized": _exact_bool(
                "ledger_mutation_authorized",
                fields["ledger_mutation_authorized"],
                gate.ledger_mutation_authorized,
            ),
            "run_size_authorized": _exact_bool(
                "run_size_authorized",
                fields["run_size_authorized"],
                gate.run_size_authorized,
            ),
            "launch_authorized": _exact_bool(
                "launch_authorized",
                fields["launch_authorized"],
                gate.launch_authorized,
            ),
            "production_authorized": _exact_bool(
                "production_authorized",
                fields["production_authorized"],
                gate.production_authorized,
            ),
            "launch_readiness": _exact_enum(
                "launch_readiness",
                fields["launch_readiness"],
                ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH,
            ),
            "probe_results": probes,
            "production_effect": _exact_text(
                "production_effect", fields["production_effect"], "NONE"
            ),
            "zero_production_effect_proof": _exact_text(
                "zero_production_effect_proof",
                fields["zero_production_effect_proof"],
                "PROVEN_NONE",
            ),
            "reason_codes": reasons,
        }
        material = {
            name: (
                tuple(item.identity_material for item in item_value)
                if name == "probe_results"
                else item_value.value
                if isinstance(item_value, StrEnum)
                else item_value
            )
            for name, item_value in values.items()
        }
        material["runtime_source_byte_length"] = _RUNTIME_BYTE_LENGTH
        evidence_id = _identity(
            material, fields["evidence_id"], "evidence identity"
        )
        normalized = {
            "evidence_id": evidence_id,
            "runtime_source_byte_length": _RUNTIME_BYTE_LENGTH,
            **values,
        }
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.evidence_id


def _static_probe(
    kind: ShadowPhase11RuntimeNoRetryProbeKindV1,
) -> ShadowPhase11RuntimeNoRetryProbeResultV1:
    return ShadowPhase11RuntimeNoRetryProbeResultV1(
        schema_version=_PROBE_SCHEMA,
        probe_id=None,
        probe_kind=kind,
        provider="DEEPSEEK",
        role=ShadowPhase11PilotProviderRoleV1.PRIMARY,
        runtime_outcome=_PROBE_OUTCOMES[kind],
        configured_maximum_attempts=1,
        observed_transport_invocation_count=1,
        observed_attempt_count=1,
        second_transport_invocation_observed=False,
        retry_delay_observed=False,
        network_access_observed=False,
        credential_access_observed=False,
        account_access_observed=False,
        ledger_mutation_observed=False,
        reservation_creation_observed=False,
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
        reason_codes=("ONE_ATTEMPT_NO_RETRY",),
    )


def _concrete_evidence() -> ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    return ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1(
        schema_version=_EVIDENCE_SCHEMA,
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        credential_safe_gate_reference=gate.evidence_reference,
        credential_safe_gate_identity=gate.identity,
        locked_repository_baseline=_REPOSITORY_BASELINE,
        locked_phase09_baseline=_PHASE09_BASELINE,
        runtime_source_path=_RUNTIME_PATH,
        runtime_source_sha256=_RUNTIME_SHA256,
        runtime_git_blob_identity=_RUNTIME_BLOB,
        runtime_class_name=_RUNTIME_CLASS,
        runtime_invocation_method=_RUNTIME_METHOD,
        enforcement_state=(
            ShadowPhase11RuntimeNoRetryEnforcementStateV1
            .VERIFIED_ONE_ATTEMPT_NO_RETRY_FOR_PILOT_PROFILE
        ),
        pilot_maximum_attempts=gate.maximum_attempts,
        provider_retry_authorized=gate.provider_retry_authorized,
        credential_retry_authorized=gate.credential_retry_authorized,
        authentication_retry_authorized=gate.authentication_retry_authorized,
        runtime_no_retry_enforcement_verified=True,
        generic_runtime_retry_capability_removed=False,
        authentication_terminal_classification_verified=False,
        credential_configuration_verified=False,
        pricing_revalidation_completed=False,
        pre_call_reservation_created=False,
        pilot_input_present=False,
        run_manifest_present=False,
        provider_call_authorized=False,
        provider_transmission_authorized=False,
        reservation_creation_authorized=False,
        ledger_mutation_authorized=False,
        run_size_authorized=False,
        launch_authorized=False,
        production_authorized=False,
        launch_readiness=(
            ShadowPhase11PilotLaunchReadinessV1.NOT_READY_FOR_LAUNCH
        ),
        probe_results=tuple(
            _static_probe(kind)
            for kind in ShadowPhase11RuntimeNoRetryProbeKindV1
        ),
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
        reason_codes=("PILOT_PROFILE_ONE_ATTEMPT_VERIFIED",),
    )


_EVIDENCE = _concrete_evidence()


def get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1(
) -> ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1:
    """Return the immutable static one-attempt pilot-profile evidence."""

    return _EVIDENCE


__all__ = (
    "ShadowPhase11RuntimeNoRetryEnforcementEvidenceV1",
    "ShadowPhase11RuntimeNoRetryEnforcementStateV1",
    "ShadowPhase11RuntimeNoRetryEnforcementValidationError",
    "ShadowPhase11RuntimeNoRetryProbeKindV1",
    "ShadowPhase11RuntimeNoRetryProbeResultV1",
    "canonical_json_bytes",
    "get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1",
    "sha256_hex",
)
