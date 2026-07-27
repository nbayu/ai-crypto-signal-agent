"""Immutable Phase 11 current adapter/runtime integrity evidence.

This module stores static, repository-owned observations only. It does not
execute the adapter or runtime, inspect source files or Git, access
configuration or credentials, or grant operational authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from engine.phase_11_provider_transport_adapters_v1 import AdapterFailureV1
from engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1 import (
    get_phase_11_shadow_pilot_credential_safe_launch_gate_v1,
)
from engine.phase_11_shadow_pilot_model_cost_authority_v1 import (
    ShadowPhase11PilotLaunchReadinessV1,
)
from engine.phase_11_shadow_pilot_runtime_no_retry_enforcement_v1 import (
    get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1,
)
from engine.phase_11_shadow_provider_runtime_v1 import (
    RuntimeFailureV1,
    TransportOutcomeV1,
)


_PROBE_SCHEMA = (
    "phase11-shadow-pilot-current-runtime-integrity-probe-result-v1"
)
_EVIDENCE_SCHEMA = (
    "phase11-shadow-pilot-current-runtime-integrity-evidence-v1"
)
_EVIDENCE_REFERENCE = (
    "PHASE_11_PILOT_CURRENT_RUNTIME_INTEGRITY_EVIDENCE_001"
)
_GATE_REFERENCE = "PHASE_11_PILOT_CREDENTIAL_SAFE_LAUNCH_GATE_001"
_GATE_IDENTITY = (
    "29a07dc2cb644aeb4dbdc9dc00e4da79b5fa3d1486e98dabdcadb1e40140debb"
)
_PREDECESSOR_REFERENCE = "PHASE_11_PILOT_RUNTIME_NO_RETRY_ENFORCEMENT_001"
_PREDECESSOR_IDENTITY = (
    "06948d6739d6e0c2a48782a866ca3ef4e084cf49ccba7017f5f6c054603fcdd1"
)
_REPOSITORY_BASELINE = "070ff7528df0ec16eb6ed01be5c43d9085408986"
_PHASE09_BASELINE = "e50041f7296bd9e042f749b6a98393b3df9747a1"

_ADAPTER_PATH = "engine/phase_11_provider_transport_adapters_v1.py"
_ADAPTER_SHA256 = (
    "09e71d22926f8855813e238675336e0f426c9209659804a30ee3a6e0a4025d07"
)
_ADAPTER_BLOB = "e7c42427159c8335d84de691cc2474852c8fcb99"
_ADAPTER_BYTE_LENGTH = 25425
_ADAPTER_FAILURE_ENUM = "AdapterFailureV1"
_ADAPTER_TERMINAL_BOUNDARY = "_TERMINAL_OUTCOMES"

_RUNTIME_PATH = "engine/phase_11_shadow_provider_runtime_v1.py"
_RUNTIME_SHA256 = (
    "f1c52caf771cfa5b753f6bc5f2ebda5024d677549ae6dc09c66318fd9ff72e1d"
)
_RUNTIME_BLOB = "6e128cc66e0fd87179dad392d633364f425e965d"
_RUNTIME_BYTE_LENGTH = 38679
_RUNTIME_OUTCOME_ENUM = "TransportOutcomeV1"
_RUNTIME_FAILURE_ENUM = "RuntimeFailureV1"
_RUNTIME_CLASS = "ShadowProviderRuntimeV1"
_RUNTIME_METHOD = "invoke"

_HISTORICAL_RUNTIME_SHA256 = (
    "853bd420bef56bd560abf2e65baccc8e33f17d549bfd60a4b4ace5917b56cf38"
)
_HISTORICAL_RUNTIME_BLOB = "572a6716836e723287b4aa2a835ed985378fbf6a"
_HISTORICAL_RUNTIME_BYTE_LENGTH = 38310

_HASH64 = re.compile(r"^[0-9a-f]{64}$")
_HASH40 = re.compile(r"^[0-9a-f]{40}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")


class ShadowPhase11CurrentRuntimeIntegrityValidationError(ValueError):
    """Raised when current-source integrity evidence is invalid."""


class ShadowPhase11CurrentRuntimeIntegrityStateV1(StrEnum):
    """The sole current-source integrity claim authorized here."""

    VERIFIED_CURRENT_ADAPTER_AND_RUNTIME_FOR_PILOT_PROFILE = (
        "VERIFIED_CURRENT_ADAPTER_AND_RUNTIME_FOR_PILOT_PROFILE"
    )


class ShadowPhase11CurrentRuntimePredecessorStatusV1(StrEnum):
    """The predecessor is lineage evidence, not current-source authority."""

    HISTORICAL_PREDECESSOR_ONLY = "HISTORICAL_PREDECESSOR_ONLY"


class ShadowPhase11CurrentRuntimeIntegrityProbeKindV1(StrEnum):
    """The complete deterministic current-runtime probe set."""

    SUCCESS = "SUCCESS"
    RETRYABLE_TIMEOUT = "RETRYABLE_TIMEOUT"
    RETRYABLE_TRANSPORT_FAILURE = "RETRYABLE_TRANSPORT_FAILURE"
    AUTHENTICATION_REJECTED = "AUTHENTICATION_REJECTED"
    UNKNOWN_NORMALIZED_OUTCOME = "UNKNOWN_NORMALIZED_OUTCOME"


_PROBE_ORDER = {
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.SUCCESS: 0,
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TIMEOUT: 1,
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1
    .RETRYABLE_TRANSPORT_FAILURE: 2,
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.AUTHENTICATION_REJECTED: 3,
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1
    .UNKNOWN_NORMALIZED_OUTCOME: 4,
}

_PROBE_MAPPINGS = {
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.SUCCESS: (
        "SUCCESS_RESPONSE",
        None,
        TransportOutcomeV1.SUCCESS,
        None,
        False,
        False,
        False,
    ),
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.RETRYABLE_TIMEOUT: (
        "TIMEOUT_EXCEPTION",
        None,
        TransportOutcomeV1.TIMEOUT,
        RuntimeFailureV1.TIMEOUT,
        True,
        False,
        False,
    ),
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1
    .RETRYABLE_TRANSPORT_FAILURE: (
        "TRANSPORT_EXCEPTION",
        None,
        TransportOutcomeV1.TRANSPORT_FAILURE,
        RuntimeFailureV1.TRANSPORT_FAILURE,
        True,
        False,
        False,
    ),
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1.AUTHENTICATION_REJECTED: (
        "AUTHENTICATION_REJECTED",
        AdapterFailureV1.AUTHENTICATION_REJECTED,
        TransportOutcomeV1.AUTHENTICATION_FAILURE,
        RuntimeFailureV1.AUTHENTICATION_FAILURE,
        False,
        False,
        True,
    ),
    ShadowPhase11CurrentRuntimeIntegrityProbeKindV1
    .UNKNOWN_NORMALIZED_OUTCOME: (
        "UNRECOGNIZED_NORMALIZED_OUTCOME",
        None,
        TransportOutcomeV1.MALFORMED_RESPONSE,
        RuntimeFailureV1.MALFORMED_RESPONSE,
        False,
        True,
        False,
    ),
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
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
            "non-canonical evidence value"
        ) from error


def sha256_hex(value: bytes) -> str:
    """Return lowercase SHA-256 for exact bytes."""

    if type(value) is not bytes:
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
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
            raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                f"{label} mismatch"
            )
    return result


def _exact_text(name: str, value: Any, expected: str) -> str:
    if type(value) is not str or value != expected:
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
            f"invalid {name}"
        )
    return value


def _exact_bool(name: str, value: Any, expected: bool) -> bool:
    if type(value) is not bool or value is not expected:
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
            f"invalid {name}"
        )
    return value


def _exact_int(name: str, value: Any, expected: int) -> int:
    if type(value) is not int or value != expected:
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
            f"invalid {name}"
        )
    return value


def _exact_enum(name: str, value: Any, expected: Any) -> Any:
    if type(value) is not type(expected) or value is not expected:
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
            f"invalid {name}"
        )
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
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
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
            "invalid reason_codes"
        )
    return result


_PROBE_FIELDS = frozenset(
    (
        "schema_version",
        "probe_id",
        "probe_kind",
        "normalized_input_category",
        "adapter_failure",
        "runtime_outcome",
        "runtime_failure",
        "configured_maximum_attempts",
        "observed_transport_invocation_count",
        "observed_runtime_attempt_count",
        "terminal_for_configured_profile",
        "retryable_under_generic_runtime_behavior",
        "second_transport_invocation_observed",
        "retry_delay_observed",
        "generic_fallback_observed",
        "authentication_terminal_mapping_observed",
        "network_access_observed",
        "credential_access_observed",
        "environment_access_observed",
        "account_access_observed",
        "billing_access_observed",
        "ledger_mutation_observed",
        "reservation_creation_observed",
        "production_effect",
        "zero_production_effect_proof",
        "reason_codes",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11CurrentRuntimeIntegrityProbeResultV1:
    """One immutable, static current-runtime probe observation."""

    schema_version: str
    probe_id: str
    probe_kind: ShadowPhase11CurrentRuntimeIntegrityProbeKindV1
    normalized_input_category: str
    adapter_failure: AdapterFailureV1 | None
    runtime_outcome: TransportOutcomeV1
    runtime_failure: RuntimeFailureV1 | None
    configured_maximum_attempts: int
    observed_transport_invocation_count: int
    observed_runtime_attempt_count: int
    terminal_for_configured_profile: bool
    retryable_under_generic_runtime_behavior: bool
    second_transport_invocation_observed: bool
    retry_delay_observed: bool
    generic_fallback_observed: bool
    authentication_terminal_mapping_observed: bool
    network_access_observed: bool
    credential_access_observed: bool
    environment_access_observed: bool
    account_access_observed: bool
    billing_access_observed: bool
    ledger_mutation_observed: bool
    reservation_creation_observed: bool
    production_effect: str
    zero_production_effect_proof: str
    reason_codes: tuple[str, ...]

    def __init__(self, **fields: Any) -> None:
        if frozenset(fields) != _PROBE_FIELDS:
            raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                "invalid probe fields"
            )
        kind = fields["probe_kind"]
        if type(kind) is not ShadowPhase11CurrentRuntimeIntegrityProbeKindV1:
            raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                "invalid probe_kind"
            )
        (
            category,
            adapter_failure,
            runtime_outcome,
            runtime_failure,
            retryable,
            generic_fallback,
            authentication_mapping,
        ) = _PROBE_MAPPINGS[kind]
        reasons = _reason_codes(fields["reason_codes"])
        values = {
            "schema_version": _exact_text(
                "schema_version", fields["schema_version"], _PROBE_SCHEMA
            ),
            "probe_kind": kind,
            "normalized_input_category": _exact_text(
                "normalized_input_category",
                fields["normalized_input_category"],
                category,
            ),
            "adapter_failure": _exact_enum(
                "adapter_failure",
                fields["adapter_failure"],
                adapter_failure,
            )
            if adapter_failure is not None
            else (
                None
                if fields["adapter_failure"] is None
                else self._invalid("adapter_failure")
            ),
            "runtime_outcome": _exact_enum(
                "runtime_outcome",
                fields["runtime_outcome"],
                runtime_outcome,
            ),
            "runtime_failure": _exact_enum(
                "runtime_failure",
                fields["runtime_failure"],
                runtime_failure,
            )
            if runtime_failure is not None
            else (
                None
                if fields["runtime_failure"] is None
                else self._invalid("runtime_failure")
            ),
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
            "observed_runtime_attempt_count": _exact_int(
                "observed_runtime_attempt_count",
                fields["observed_runtime_attempt_count"],
                1,
            ),
            "terminal_for_configured_profile": _exact_bool(
                "terminal_for_configured_profile",
                fields["terminal_for_configured_profile"],
                True,
            ),
            "retryable_under_generic_runtime_behavior": _exact_bool(
                "retryable_under_generic_runtime_behavior",
                fields["retryable_under_generic_runtime_behavior"],
                retryable,
            ),
            "second_transport_invocation_observed": _exact_bool(
                "second_transport_invocation_observed",
                fields["second_transport_invocation_observed"],
                False,
            ),
            "retry_delay_observed": _exact_bool(
                "retry_delay_observed",
                fields["retry_delay_observed"],
                False,
            ),
            "generic_fallback_observed": _exact_bool(
                "generic_fallback_observed",
                fields["generic_fallback_observed"],
                generic_fallback,
            ),
            "authentication_terminal_mapping_observed": _exact_bool(
                "authentication_terminal_mapping_observed",
                fields["authentication_terminal_mapping_observed"],
                authentication_mapping,
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
            "environment_access_observed": _exact_bool(
                "environment_access_observed",
                fields["environment_access_observed"],
                False,
            ),
            "account_access_observed": _exact_bool(
                "account_access_observed",
                fields["account_access_observed"],
                False,
            ),
            "billing_access_observed": _exact_bool(
                "billing_access_observed",
                fields["billing_access_observed"],
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
            name: item.value if isinstance(item, StrEnum) else item
            for name, item in values.items()
        }
        probe_id = _identity(
            material, fields["probe_id"], "probe identity"
        )
        for name, item in {"probe_id": probe_id, **values}.items():
            object.__setattr__(self, name, item)

    @staticmethod
    def _invalid(name: str) -> None:
        raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
            f"invalid {name}"
        )

    @property
    def identity(self) -> str:
        return self.probe_id

    @property
    def identity_material(self) -> Mapping[str, Any]:
        return {
            name: (
                item.value
                if isinstance(item, StrEnum)
                else item
            )
            for name, item in (
                ("schema_version", self.schema_version),
                ("probe_kind", self.probe_kind),
                ("normalized_input_category", self.normalized_input_category),
                ("adapter_failure", self.adapter_failure),
                ("runtime_outcome", self.runtime_outcome),
                ("runtime_failure", self.runtime_failure),
                (
                    "configured_maximum_attempts",
                    self.configured_maximum_attempts,
                ),
                (
                    "observed_transport_invocation_count",
                    self.observed_transport_invocation_count,
                ),
                (
                    "observed_runtime_attempt_count",
                    self.observed_runtime_attempt_count,
                ),
                (
                    "terminal_for_configured_profile",
                    self.terminal_for_configured_profile,
                ),
                (
                    "retryable_under_generic_runtime_behavior",
                    self.retryable_under_generic_runtime_behavior,
                ),
                (
                    "second_transport_invocation_observed",
                    self.second_transport_invocation_observed,
                ),
                ("retry_delay_observed", self.retry_delay_observed),
                ("generic_fallback_observed", self.generic_fallback_observed),
                (
                    "authentication_terminal_mapping_observed",
                    self.authentication_terminal_mapping_observed,
                ),
                ("network_access_observed", self.network_access_observed),
                (
                    "credential_access_observed",
                    self.credential_access_observed,
                ),
                (
                    "environment_access_observed",
                    self.environment_access_observed,
                ),
                ("account_access_observed", self.account_access_observed),
                ("billing_access_observed", self.billing_access_observed),
                ("ledger_mutation_observed", self.ledger_mutation_observed),
                (
                    "reservation_creation_observed",
                    self.reservation_creation_observed,
                ),
                ("production_effect", self.production_effect),
                (
                    "zero_production_effect_proof",
                    self.zero_production_effect_proof,
                ),
                ("reason_codes", self.reason_codes),
            )
        }


_EVIDENCE_FIELDS = frozenset(
    (
        "schema_version",
        "evidence_id",
        "evidence_reference",
        "credential_safe_gate_reference",
        "credential_safe_gate_identity",
        "predecessor_evidence_reference",
        "predecessor_evidence_identity",
        "predecessor_status",
        "predecessor_current_source_authority",
        "locked_repository_baseline",
        "locked_phase09_baseline",
        "adapter_source_path",
        "adapter_source_sha256",
        "adapter_git_blob_identity",
        "adapter_source_byte_length",
        "adapter_failure_enum_name",
        "adapter_terminal_boundary_name",
        "runtime_source_path",
        "runtime_source_sha256",
        "runtime_git_blob_identity",
        "runtime_source_byte_length",
        "runtime_outcome_enum_name",
        "runtime_failure_enum_name",
        "runtime_class_name",
        "runtime_invocation_method",
        "integrity_state",
        "pilot_maximum_attempts",
        "runtime_one_attempt_no_retry_verified",
        "authentication_terminal_classification_verified",
        "generic_unknown_fallback_verified",
        "generic_timeout_retry_capability_preserved",
        "generic_transport_failure_retry_capability_preserved",
        "generic_runtime_retry_capability_removed",
        "authentication_above_one_configured_maximum_attempts",
        "authentication_above_one_observed_transport_invocation_count",
        "authentication_above_one_observed_runtime_attempt_count",
        "authentication_above_one_second_transport_invocation_observed",
        "authentication_above_one_retry_delay_observed",
        "probe_results",
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
        "production_effect",
        "zero_production_effect_proof",
        "reason_codes",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ShadowPhase11CurrentRuntimeIntegrityEvidenceV1:
    """Static current-source integrity evidence for the pilot profile."""

    schema_version: str
    evidence_id: str
    evidence_reference: str
    credential_safe_gate_reference: str
    credential_safe_gate_identity: str
    predecessor_evidence_reference: str
    predecessor_evidence_identity: str
    predecessor_status: ShadowPhase11CurrentRuntimePredecessorStatusV1
    predecessor_current_source_authority: bool
    locked_repository_baseline: str
    locked_phase09_baseline: str
    adapter_source_path: str
    adapter_source_sha256: str
    adapter_git_blob_identity: str
    adapter_source_byte_length: int
    adapter_failure_enum_name: str
    adapter_terminal_boundary_name: str
    runtime_source_path: str
    runtime_source_sha256: str
    runtime_git_blob_identity: str
    runtime_source_byte_length: int
    runtime_outcome_enum_name: str
    runtime_failure_enum_name: str
    runtime_class_name: str
    runtime_invocation_method: str
    integrity_state: ShadowPhase11CurrentRuntimeIntegrityStateV1
    pilot_maximum_attempts: int
    runtime_one_attempt_no_retry_verified: bool
    authentication_terminal_classification_verified: bool
    generic_unknown_fallback_verified: bool
    generic_timeout_retry_capability_preserved: bool
    generic_transport_failure_retry_capability_preserved: bool
    generic_runtime_retry_capability_removed: bool
    authentication_above_one_configured_maximum_attempts: int
    authentication_above_one_observed_transport_invocation_count: int
    authentication_above_one_observed_runtime_attempt_count: int
    authentication_above_one_second_transport_invocation_observed: bool
    authentication_above_one_retry_delay_observed: bool
    probe_results: tuple[
        ShadowPhase11CurrentRuntimeIntegrityProbeResultV1, ...
    ]
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
    production_effect: str
    zero_production_effect_proof: str
    reason_codes: tuple[str, ...]

    def __init__(self, **fields: Any) -> None:
        if frozenset(fields) != _EVIDENCE_FIELDS:
            raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                "invalid evidence fields"
            )
        gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
        predecessor = (
            get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1()
        )
        if (
            gate.evidence_reference != _GATE_REFERENCE
            or gate.identity != _GATE_IDENTITY
        ):
            raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                "committed gate identity mismatch"
            )
        if (
            predecessor.evidence_reference != _PREDECESSOR_REFERENCE
            or predecessor.identity != _PREDECESSOR_IDENTITY
            or predecessor.runtime_source_sha256
            != _HISTORICAL_RUNTIME_SHA256
            or predecessor.runtime_git_blob_identity
            != _HISTORICAL_RUNTIME_BLOB
            or predecessor.runtime_source_byte_length
            != _HISTORICAL_RUNTIME_BYTE_LENGTH
            or predecessor.runtime_source_sha256 == _RUNTIME_SHA256
            or predecessor.runtime_git_blob_identity == _RUNTIME_BLOB
            or predecessor.runtime_source_byte_length == _RUNTIME_BYTE_LENGTH
        ):
            raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                "historical predecessor mismatch"
            )
        probes_value = fields["probe_results"]
        if type(probes_value) not in (tuple, list):
            raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                "invalid probe_results"
            )
        probes = tuple(probes_value)
        if (
            len(probes) != len(_PROBE_ORDER)
            or any(
                type(item)
                is not ShadowPhase11CurrentRuntimeIntegrityProbeResultV1
                for item in probes
            )
            or len({item.probe_kind for item in probes}) != len(_PROBE_ORDER)
            or set(item.probe_kind for item in probes) != set(_PROBE_ORDER)
        ):
            raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                "invalid probe set"
            )
        probes = tuple(
            sorted(probes, key=lambda item: _PROBE_ORDER[item.probe_kind])
        )
        for name, value, pattern, expected in (
            (
                "adapter_source_sha256",
                fields["adapter_source_sha256"],
                _HASH64,
                _ADAPTER_SHA256,
            ),
            (
                "adapter_git_blob_identity",
                fields["adapter_git_blob_identity"],
                _HASH40,
                _ADAPTER_BLOB,
            ),
            (
                "runtime_source_sha256",
                fields["runtime_source_sha256"],
                _HASH64,
                _RUNTIME_SHA256,
            ),
            (
                "runtime_git_blob_identity",
                fields["runtime_git_blob_identity"],
                _HASH40,
                _RUNTIME_BLOB,
            ),
        ):
            if (
                type(value) is not str
                or pattern.fullmatch(value) is None
                or value != expected
            ):
                raise ShadowPhase11CurrentRuntimeIntegrityValidationError(
                    f"invalid {name}"
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
            "predecessor_evidence_reference": _exact_text(
                "predecessor_evidence_reference",
                fields["predecessor_evidence_reference"],
                predecessor.evidence_reference,
            ),
            "predecessor_evidence_identity": _exact_text(
                "predecessor_evidence_identity",
                fields["predecessor_evidence_identity"],
                predecessor.identity,
            ),
            "predecessor_status": _exact_enum(
                "predecessor_status",
                fields["predecessor_status"],
                ShadowPhase11CurrentRuntimePredecessorStatusV1
                .HISTORICAL_PREDECESSOR_ONLY,
            ),
            "predecessor_current_source_authority": _exact_bool(
                "predecessor_current_source_authority",
                fields["predecessor_current_source_authority"],
                False,
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
            "adapter_source_path": _exact_text(
                "adapter_source_path",
                fields["adapter_source_path"],
                _ADAPTER_PATH,
            ),
            "adapter_source_sha256": fields["adapter_source_sha256"],
            "adapter_git_blob_identity":
                fields["adapter_git_blob_identity"],
            "adapter_source_byte_length": _exact_int(
                "adapter_source_byte_length",
                fields["adapter_source_byte_length"],
                _ADAPTER_BYTE_LENGTH,
            ),
            "adapter_failure_enum_name": _exact_text(
                "adapter_failure_enum_name",
                fields["adapter_failure_enum_name"],
                _ADAPTER_FAILURE_ENUM,
            ),
            "adapter_terminal_boundary_name": _exact_text(
                "adapter_terminal_boundary_name",
                fields["adapter_terminal_boundary_name"],
                _ADAPTER_TERMINAL_BOUNDARY,
            ),
            "runtime_source_path": _exact_text(
                "runtime_source_path",
                fields["runtime_source_path"],
                _RUNTIME_PATH,
            ),
            "runtime_source_sha256": fields["runtime_source_sha256"],
            "runtime_git_blob_identity": fields["runtime_git_blob_identity"],
            "runtime_source_byte_length": _exact_int(
                "runtime_source_byte_length",
                fields["runtime_source_byte_length"],
                _RUNTIME_BYTE_LENGTH,
            ),
            "runtime_outcome_enum_name": _exact_text(
                "runtime_outcome_enum_name",
                fields["runtime_outcome_enum_name"],
                _RUNTIME_OUTCOME_ENUM,
            ),
            "runtime_failure_enum_name": _exact_text(
                "runtime_failure_enum_name",
                fields["runtime_failure_enum_name"],
                _RUNTIME_FAILURE_ENUM,
            ),
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
            "integrity_state": _exact_enum(
                "integrity_state",
                fields["integrity_state"],
                ShadowPhase11CurrentRuntimeIntegrityStateV1
                .VERIFIED_CURRENT_ADAPTER_AND_RUNTIME_FOR_PILOT_PROFILE,
            ),
            "pilot_maximum_attempts": _exact_int(
                "pilot_maximum_attempts",
                fields["pilot_maximum_attempts"],
                gate.maximum_attempts,
            ),
            "runtime_one_attempt_no_retry_verified": _exact_bool(
                "runtime_one_attempt_no_retry_verified",
                fields["runtime_one_attempt_no_retry_verified"],
                True,
            ),
            "authentication_terminal_classification_verified": _exact_bool(
                "authentication_terminal_classification_verified",
                fields["authentication_terminal_classification_verified"],
                True,
            ),
            "generic_unknown_fallback_verified": _exact_bool(
                "generic_unknown_fallback_verified",
                fields["generic_unknown_fallback_verified"],
                True,
            ),
            "generic_timeout_retry_capability_preserved": _exact_bool(
                "generic_timeout_retry_capability_preserved",
                fields["generic_timeout_retry_capability_preserved"],
                True,
            ),
            "generic_transport_failure_retry_capability_preserved":
                _exact_bool(
                    "generic_transport_failure_retry_capability_preserved",
                    fields[
                        "generic_transport_failure_retry_capability_preserved"
                    ],
                    True,
                ),
            "generic_runtime_retry_capability_removed": _exact_bool(
                "generic_runtime_retry_capability_removed",
                fields["generic_runtime_retry_capability_removed"],
                False,
            ),
            "authentication_above_one_configured_maximum_attempts":
                _exact_int(
                    "authentication_above_one_configured_maximum_attempts",
                    fields[
                        "authentication_above_one_configured_maximum_attempts"
                    ],
                    2,
                ),
            "authentication_above_one_observed_transport_invocation_count":
                _exact_int(
                    "authentication_above_one_observed_transport_invocation_count",
                    fields[
                        "authentication_above_one_observed_transport_invocation_count"
                    ],
                    1,
                ),
            "authentication_above_one_observed_runtime_attempt_count":
                _exact_int(
                    "authentication_above_one_observed_runtime_attempt_count",
                    fields[
                        "authentication_above_one_observed_runtime_attempt_count"
                    ],
                    1,
                ),
            "authentication_above_one_second_transport_invocation_observed":
                _exact_bool(
                    "authentication_above_one_second_transport_invocation_observed",
                    fields[
                        "authentication_above_one_second_transport_invocation_observed"
                    ],
                    False,
                ),
            "authentication_above_one_retry_delay_observed": _exact_bool(
                "authentication_above_one_retry_delay_observed",
                fields["authentication_above_one_retry_delay_observed"],
                False,
            ),
            "probe_results": probes,
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
                tuple(item.identity_material for item in value)
                if name == "probe_results"
                else value.value
                if isinstance(value, StrEnum)
                else value
            )
            for name, value in values.items()
        }
        evidence_id = _identity(
            material, fields["evidence_id"], "evidence identity"
        )
        for name, item in {"evidence_id": evidence_id, **values}.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.evidence_id


def _static_probe(
    kind: ShadowPhase11CurrentRuntimeIntegrityProbeKindV1,
) -> ShadowPhase11CurrentRuntimeIntegrityProbeResultV1:
    (
        category,
        adapter_failure,
        runtime_outcome,
        runtime_failure,
        retryable,
        generic_fallback,
        authentication_mapping,
    ) = _PROBE_MAPPINGS[kind]
    return ShadowPhase11CurrentRuntimeIntegrityProbeResultV1(
        schema_version=_PROBE_SCHEMA,
        probe_id=None,
        probe_kind=kind,
        normalized_input_category=category,
        adapter_failure=adapter_failure,
        runtime_outcome=runtime_outcome,
        runtime_failure=runtime_failure,
        configured_maximum_attempts=1,
        observed_transport_invocation_count=1,
        observed_runtime_attempt_count=1,
        terminal_for_configured_profile=True,
        retryable_under_generic_runtime_behavior=retryable,
        second_transport_invocation_observed=False,
        retry_delay_observed=False,
        generic_fallback_observed=generic_fallback,
        authentication_terminal_mapping_observed=authentication_mapping,
        network_access_observed=False,
        credential_access_observed=False,
        environment_access_observed=False,
        account_access_observed=False,
        billing_access_observed=False,
        ledger_mutation_observed=False,
        reservation_creation_observed=False,
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
        reason_codes=("CURRENT_RUNTIME_PROBE",),
    )


def _concrete_evidence() -> ShadowPhase11CurrentRuntimeIntegrityEvidenceV1:
    gate = get_phase_11_shadow_pilot_credential_safe_launch_gate_v1()
    predecessor = (
        get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1()
    )
    return ShadowPhase11CurrentRuntimeIntegrityEvidenceV1(
        schema_version=_EVIDENCE_SCHEMA,
        evidence_id=None,
        evidence_reference=_EVIDENCE_REFERENCE,
        credential_safe_gate_reference=gate.evidence_reference,
        credential_safe_gate_identity=gate.identity,
        predecessor_evidence_reference=predecessor.evidence_reference,
        predecessor_evidence_identity=predecessor.identity,
        predecessor_status=(
            ShadowPhase11CurrentRuntimePredecessorStatusV1
            .HISTORICAL_PREDECESSOR_ONLY
        ),
        predecessor_current_source_authority=False,
        locked_repository_baseline=_REPOSITORY_BASELINE,
        locked_phase09_baseline=_PHASE09_BASELINE,
        adapter_source_path=_ADAPTER_PATH,
        adapter_source_sha256=_ADAPTER_SHA256,
        adapter_git_blob_identity=_ADAPTER_BLOB,
        adapter_source_byte_length=_ADAPTER_BYTE_LENGTH,
        adapter_failure_enum_name=_ADAPTER_FAILURE_ENUM,
        adapter_terminal_boundary_name=_ADAPTER_TERMINAL_BOUNDARY,
        runtime_source_path=_RUNTIME_PATH,
        runtime_source_sha256=_RUNTIME_SHA256,
        runtime_git_blob_identity=_RUNTIME_BLOB,
        runtime_source_byte_length=_RUNTIME_BYTE_LENGTH,
        runtime_outcome_enum_name=_RUNTIME_OUTCOME_ENUM,
        runtime_failure_enum_name=_RUNTIME_FAILURE_ENUM,
        runtime_class_name=_RUNTIME_CLASS,
        runtime_invocation_method=_RUNTIME_METHOD,
        integrity_state=(
            ShadowPhase11CurrentRuntimeIntegrityStateV1
            .VERIFIED_CURRENT_ADAPTER_AND_RUNTIME_FOR_PILOT_PROFILE
        ),
        pilot_maximum_attempts=gate.maximum_attempts,
        runtime_one_attempt_no_retry_verified=True,
        authentication_terminal_classification_verified=True,
        generic_unknown_fallback_verified=True,
        generic_timeout_retry_capability_preserved=True,
        generic_transport_failure_retry_capability_preserved=True,
        generic_runtime_retry_capability_removed=False,
        authentication_above_one_configured_maximum_attempts=2,
        authentication_above_one_observed_transport_invocation_count=1,
        authentication_above_one_observed_runtime_attempt_count=1,
        authentication_above_one_second_transport_invocation_observed=False,
        authentication_above_one_retry_delay_observed=False,
        probe_results=tuple(
            _static_probe(kind)
            for kind in ShadowPhase11CurrentRuntimeIntegrityProbeKindV1
        ),
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
        production_effect="NONE",
        zero_production_effect_proof="PROVEN_NONE",
        reason_codes=("CURRENT_SOURCE_INTEGRITY_VERIFIED",),
    )


_CONCRETE_EVIDENCE = _concrete_evidence()


def get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1(
) -> ShadowPhase11CurrentRuntimeIntegrityEvidenceV1:
    """Return the immutable current-source integrity evidence."""

    return _CONCRETE_EVIDENCE
