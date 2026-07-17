"""Immutable Phase 11 shadow-input value contracts.

This module validates and canonicalizes detached shadow evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any, Mapping


UTC = timezone.utc
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_POLICY_VERSION_RE = re.compile(r"^phase11-policy-v[1-9][0-9]*$")
_REASON_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

EVENT_CLASSES = (
    "CLEAN_ROUTINE",
    "MODERATE_AMBIGUITY",
    "CRITICAL_AMBIGUITY",
    "SOURCE_DISAGREEMENT",
    "MAPPING_AMBIGUITY",
    "EXPLOIT_SECURITY",
    "DELISTING",
    "LEGAL_REGULATORY",
    "SOLVENCY_EXCHANGE_RISK",
    "SUSPECTED_MANIPULATION",
    "SYSTEMIC_CROSS_MARKET",
    "MALFORMED_PROVIDER_OUTPUT",
    "TIMEOUT_OUTAGE",
    "BUDGET_EXHAUSTION",
    "DUPLICATE_UPDATE_LINEAGE",
    "PROMPT_INJECTION_ADVERSARIAL",
)
CAPTURE_CLASSIFICATIONS = ("FIXTURE", "RECORDED_LIVE_CAPTURE")
CONTENT_ORIGINS = ("SYNTHETIC_FIXTURE", "RECORDED_SOURCE")
DISPOSITIONS = ("PUBLISHED_SIGNAL", "NO_TRADE")
PLAN_STATUSES = ("DRAFT", "APPROVED", "ACTIVE", "CLOSED", "STOPPED")
STOP_CONDITIONS = (
    "BUDGET_HARD_STOP",
    "CALL_COUNT_HARD_STOP",
    "TOKEN_HARD_STOP",
    "CRITICAL_AUTHORITY_FAILURE",
    "CRITICAL_SECURITY_FAILURE",
    "MAXIMUM_SAMPLE_COUNT",
    "IDENTITY_CHAIN_FAILURE",
    "EVIDENCE_ROOT_INTEGRITY_FAILURE",
    "BUDGET_UNCERTAINTY",
    "UNAUTHORIZED_CONFIGURATION",
    "OWNER_SUSPENSION",
)


class ShadowInputValidationError(ValueError):
    """Raised when a Phase 11 shadow-input value is invalid."""


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _thaw(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ShadowInputValidationError("value is not canonical JSON") from error


def _digest(value: Any) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        frozen = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ShadowInputValidationError("JSON object keys must be strings")
            frozen[key] = _freeze_json(item)
        _canonical_bytes(frozen)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        frozen = tuple(_freeze_json(item) for item in value)
        _canonical_bytes(frozen)
        return frozen
    if value is None or isinstance(value, (str, int, float, bool)):
        _canonical_bytes(value)
        return value
    raise ShadowInputValidationError("value is not JSON-compatible")


def _canonical_timestamp(value: Any, field_name: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ShadowInputValidationError(f"{field_name} must be timezone-aware")
        parsed = value.astimezone(UTC)
    elif isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value
    ):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ShadowInputValidationError(f"{field_name} is invalid") from error
    else:
        raise ShadowInputValidationError(f"{field_name} must be canonical UTC")
    canonical = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return canonical.replace("+00:00", "Z").replace(".000000Z", "Z")


def _as_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ShadowInputValidationError(f"{field_name} is invalid")
    return value


def _hash(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ShadowInputValidationError(f"{field_name} must be lowercase SHA-256")
    return value


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ShadowInputValidationError(f"{field_name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ShadowInputValidationError(f"{field_name} must be a non-negative integer")
    return value


def _unique_identifiers(value: Any, field_name: str, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or len(value) > maximum:
        raise ShadowInputValidationError(f"{field_name} is invalid")
    return tuple(sorted({_identifier(item, field_name) for item in value}))


def _closed_values(value: Any, field_name: str, allowed: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value or len(value) > len(allowed):
        raise ShadowInputValidationError(f"{field_name} is invalid")
    if any(item not in allowed for item in value) or len(set(value)) != len(value):
        raise ShadowInputValidationError(f"{field_name} is invalid")
    return tuple(sorted(value))


def _without_provider_prose(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _without_provider_prose(item)
            for key, item in value.items()
            if key not in {"provider_explanation", "provider_prose", "free_form_provider_prose"}
        }
    if isinstance(value, tuple):
        return [_without_provider_prose(item) for item in value]
    return value


def _canonical_lineage(value: Any, event_id: str, event_version: int) -> tuple[MappingProxyType, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ShadowInputValidationError("event_lineage is invalid")
    entries = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"event_id", "event_version", "relation"}:
            raise ShadowInputValidationError("event_lineage entry is invalid")
        entry = {
            "event_id": _identifier(item["event_id"], "event_lineage event_id"),
            "event_version": _positive_int(item["event_version"], "event_lineage event_version"),
            "relation": _identifier(item["relation"], "event_lineage relation"),
        }
        entries.append(entry)
    entry_keys = [_canonical_bytes(item) for item in entries]
    if len(set(entry_keys)) != len(entry_keys):
        raise ShadowInputValidationError("event_lineage contains duplicates")
    if not any(
        item["event_id"] == event_id
        and item["event_version"] == event_version
        and item["relation"] == "ORIGIN"
        for item in entries
    ):
        raise ShadowInputValidationError("event_lineage does not bind event identity")
    return tuple(MappingProxyType(item) for item in sorted(entries, key=_canonical_bytes))


def _capture_material(
    schema_version: str,
    event_id: str,
    event_version: int,
    source_id: str,
    source_type: str,
    source_timestamp: str,
    captured_at: str,
    point_in_time_cutoff: str,
    normalized_payload: Any,
    event_lineage: Any,
    capture_classification: str,
    content_origin: str,
    evidence_refs: Any,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "event_id": event_id,
        "event_version": event_version,
        "source_id": source_id,
        "source_type": source_type,
        "source_timestamp": source_timestamp,
        "captured_at": captured_at,
        "point_in_time_cutoff": point_in_time_cutoff,
        "normalized_payload": _without_provider_prose(normalized_payload),
        "event_lineage": event_lineage,
        "capture_classification": capture_classification,
        "content_origin": content_origin,
        "evidence_refs": evidence_refs,
    }


@dataclass(frozen=True, slots=True)
class ApprovedNewsCaptureV1:
    schema_version: str
    capture_id: str
    event_id: str
    event_version: int
    source_id: str
    source_type: str
    source_timestamp: Any
    captured_at: Any
    point_in_time_cutoff: Any
    normalized_payload: Any
    normalized_payload_hash: str
    event_lineage: Any
    capture_classification: str
    content_origin: str
    evidence_refs: Any
    _identity: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != "approved-news-capture-v1":
            raise ShadowInputValidationError("schema_version is unsupported")
        event_id = _identifier(self.event_id, "event_id")
        event_version = _positive_int(self.event_version, "event_version")
        source_id = _identifier(self.source_id, "source_id")
        source_type = _identifier(self.source_type, "source_type")
        source_timestamp = _canonical_timestamp(self.source_timestamp, "source_timestamp")
        captured_at = _canonical_timestamp(self.captured_at, "captured_at")
        point_in_time_cutoff = _canonical_timestamp(self.point_in_time_cutoff, "point_in_time_cutoff")
        if _as_timestamp(source_timestamp) > _as_timestamp(captured_at):
            raise ShadowInputValidationError("source_timestamp is after captured_at")
        if _as_timestamp(captured_at) > _as_timestamp(point_in_time_cutoff):
            raise ShadowInputValidationError("captured_at is after point_in_time_cutoff")
        if self.capture_classification not in CAPTURE_CLASSIFICATIONS:
            raise ShadowInputValidationError("capture_classification is unsupported")
        if self.content_origin not in CONTENT_ORIGINS:
            raise ShadowInputValidationError("content_origin is unsupported")
        normalized_payload = _freeze_json(self.normalized_payload)
        normalized_payload_hash = _hash(self.normalized_payload_hash, "normalized_payload_hash")
        if _digest(normalized_payload) != normalized_payload_hash:
            raise ShadowInputValidationError("normalized_payload_hash does not match normalized_payload")
        event_lineage = _canonical_lineage(self.event_lineage, event_id, event_version)
        evidence_refs = _unique_identifiers(self.evidence_refs, "evidence_refs", 32)
        capture_id = _hash(self.capture_id, "capture_id")
        supplied_material = _capture_material(
            self.schema_version,
            event_id,
            event_version,
            source_id,
            source_type,
            source_timestamp,
            captured_at,
            point_in_time_cutoff,
            normalized_payload,
            self.event_lineage,
            self.capture_classification,
            self.content_origin,
            self.evidence_refs,
        )
        if _digest(supplied_material) != capture_id:
            raise ShadowInputValidationError("capture_id does not match capture material")
        canonical_material = _capture_material(
            self.schema_version,
            event_id,
            event_version,
            source_id,
            source_type,
            source_timestamp,
            captured_at,
            point_in_time_cutoff,
            normalized_payload,
            event_lineage,
            self.capture_classification,
            self.content_origin,
            evidence_refs,
        )
        object.__setattr__(self, "capture_id", capture_id)
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "event_version", event_version)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "source_timestamp", source_timestamp)
        object.__setattr__(self, "captured_at", captured_at)
        object.__setattr__(self, "point_in_time_cutoff", point_in_time_cutoff)
        object.__setattr__(self, "normalized_payload", normalized_payload)
        object.__setattr__(self, "normalized_payload_hash", normalized_payload_hash)
        object.__setattr__(self, "event_lineage", event_lineage)
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "_identity", _digest(canonical_material))

    @property
    def identity(self) -> str:
        return self._identity


@dataclass(frozen=True, slots=True)
class Phase09ControlProjectionV1:
    schema_version: str
    projection_id: str
    production_evaluation_id: str
    event_id: str
    candidate_id: str
    disposition: str
    reason_codes: Any
    evidence_refs: Any
    evaluated_at: Any
    source_artifact_hash: str
    _identity: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != "phase09-control-projection-v1":
            raise ShadowInputValidationError("schema_version is unsupported")
        projection_id = _identifier(self.projection_id, "projection_id")
        production_evaluation_id = _identifier(self.production_evaluation_id, "production_evaluation_id")
        event_id = _identifier(self.event_id, "event_id")
        candidate_id = _identifier(self.candidate_id, "candidate_id")
        if self.disposition not in DISPOSITIONS:
            raise ShadowInputValidationError("disposition is unsupported")
        reason_codes = _unique_identifiers(self.reason_codes, "reason_codes", 32)
        if not reason_codes or any(not _REASON_CODE_RE.fullmatch(item) for item in reason_codes):
            raise ShadowInputValidationError("reason_codes are invalid")
        evidence_refs = _unique_identifiers(self.evidence_refs, "evidence_refs", 32)
        if not evidence_refs:
            raise ShadowInputValidationError("evidence_refs are required")
        evaluated_at = _canonical_timestamp(self.evaluated_at, "evaluated_at")
        source_artifact_hash = _hash(self.source_artifact_hash, "source_artifact_hash")
        material = {
            "schema_version": self.schema_version,
            "production_evaluation_id": production_evaluation_id,
            "event_id": event_id,
            "candidate_id": candidate_id,
            "disposition": self.disposition,
            "reason_codes": reason_codes,
            "evidence_refs": evidence_refs,
            "evaluated_at": evaluated_at,
            "source_artifact_hash": source_artifact_hash,
        }
        object.__setattr__(self, "projection_id", projection_id)
        object.__setattr__(self, "production_evaluation_id", production_evaluation_id)
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "reason_codes", reason_codes)
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "evaluated_at", evaluated_at)
        object.__setattr__(self, "source_artifact_hash", source_artifact_hash)
        object.__setattr__(self, "_identity", _digest(material))

    @property
    def identity(self) -> str:
        return self._identity


@dataclass(frozen=True, slots=True)
class ShadowEvaluationInputV1:
    schema_version: str
    shadow_input_id: str
    approved_news_capture: ApprovedNewsCaptureV1
    phase_09_control_projection: Phase09ControlProjectionV1
    sample_plan_id: str
    policy_version: str
    created_at: Any
    _identity: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != "shadow-evaluation-input-v1":
            raise ShadowInputValidationError("schema_version is unsupported")
        shadow_input_id = _identifier(self.shadow_input_id, "shadow_input_id")
        if type(self.approved_news_capture) is not ApprovedNewsCaptureV1:
            raise ShadowInputValidationError("approved_news_capture is invalid")
        if type(self.phase_09_control_projection) is not Phase09ControlProjectionV1:
            raise ShadowInputValidationError("phase_09_control_projection is invalid")
        if self.approved_news_capture.event_id != self.phase_09_control_projection.event_id:
            raise ShadowInputValidationError("child event identities do not match")
        sample_plan_id = _identifier(self.sample_plan_id, "sample_plan_id")
        if not isinstance(self.policy_version, str) or not _POLICY_VERSION_RE.fullmatch(self.policy_version):
            raise ShadowInputValidationError("policy_version is invalid")
        created_at = _canonical_timestamp(self.created_at, "created_at")
        material = {
            "schema_version": self.schema_version,
            "capture_identity": self.approved_news_capture.identity,
            "control_identity": self.phase_09_control_projection.identity,
            "sample_plan_id": sample_plan_id,
            "policy_version": self.policy_version,
            "created_at": created_at,
        }
        object.__setattr__(self, "shadow_input_id", shadow_input_id)
        object.__setattr__(self, "sample_plan_id", sample_plan_id)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "_identity", _digest(material))

    @property
    def identity(self) -> str:
        return self._identity


def _target_pairs(value: Any) -> list[tuple[Any, Any]]:
    if isinstance(value, Mapping):
        return list(value.items())
    if not isinstance(value, (list, tuple)):
        raise ShadowInputValidationError("event_class_targets is invalid")
    pairs = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ShadowInputValidationError("event_class_targets is invalid")
        pairs.append((item[0], item[1]))
    return pairs


@dataclass(frozen=True, slots=True)
class ShadowSamplePlanV1:
    schema_version: str
    sample_plan_id: str
    plan_version: int
    status: str
    event_class_targets: Any
    minimum_l1_count: int
    minimum_l2_count: int
    maximum_total_samples: int
    maximum_live_samples: int
    allowed_capture_classifications: Any
    stop_conditions: Any
    starts_at: Any
    ends_at: Any
    owner_approval_reference: Any
    _identity: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != "shadow-sample-plan-v1":
            raise ShadowInputValidationError("schema_version is unsupported")
        sample_plan_id = _identifier(self.sample_plan_id, "sample_plan_id")
        plan_version = _positive_int(self.plan_version, "plan_version")
        if self.status not in PLAN_STATUSES:
            raise ShadowInputValidationError("status is unsupported")
        pairs = _target_pairs(self.event_class_targets)
        labels = [item[0] for item in pairs]
        if len(set(labels)) != len(labels) or set(labels) != set(EVENT_CLASSES):
            raise ShadowInputValidationError("event_class_targets must contain every event class exactly once")
        targets = {}
        for label, count in pairs:
            if label not in EVENT_CLASSES:
                raise ShadowInputValidationError("event_class_targets contains an unknown event class")
            targets[label] = _nonnegative_int(count, "event_class_targets count")
        maximum_total_samples = _nonnegative_int(self.maximum_total_samples, "maximum_total_samples")
        maximum_live_samples = _nonnegative_int(self.maximum_live_samples, "maximum_live_samples")
        minimum_l1_count = _nonnegative_int(self.minimum_l1_count, "minimum_l1_count")
        minimum_l2_count = _nonnegative_int(self.minimum_l2_count, "minimum_l2_count")
        if sum(targets.values()) > maximum_total_samples:
            raise ShadowInputValidationError("event_class_targets exceed maximum_total_samples")
        if minimum_l1_count > maximum_total_samples or minimum_l2_count > maximum_total_samples:
            raise ShadowInputValidationError("minimum coverage exceeds maximum_total_samples")
        if maximum_live_samples > maximum_total_samples:
            raise ShadowInputValidationError("maximum_live_samples exceeds maximum_total_samples")
        allowed_capture_classifications = _closed_values(
            self.allowed_capture_classifications,
            "allowed_capture_classifications",
            CAPTURE_CLASSIFICATIONS,
        )
        if not isinstance(self.stop_conditions, (list, tuple)) or not self.stop_conditions:
            raise ShadowInputValidationError("stop_conditions is invalid")
        if len(self.stop_conditions) > len(STOP_CONDITIONS) or len(set(self.stop_conditions)) != len(self.stop_conditions):
            raise ShadowInputValidationError("stop_conditions is invalid")
        if any(item not in STOP_CONDITIONS for item in self.stop_conditions):
            raise ShadowInputValidationError("stop_conditions is unsupported")
        stop_conditions = tuple(sorted(self.stop_conditions))
        starts_at = _canonical_timestamp(self.starts_at, "starts_at")
        ends_at = _canonical_timestamp(self.ends_at, "ends_at")
        if _as_timestamp(ends_at) <= _as_timestamp(starts_at):
            raise ShadowInputValidationError("ends_at must be later than starts_at")
        if self.owner_approval_reference is None:
            owner_approval_reference = None
        else:
            owner_approval_reference = _identifier(self.owner_approval_reference, "owner_approval_reference")
        if (self.status == "APPROVED" or maximum_live_samples > 0) and owner_approval_reference is None:
            raise ShadowInputValidationError("owner_approval_reference is required")
        canonical_targets = MappingProxyType({label: targets[label] for label in sorted(EVENT_CLASSES)})
        material = {
            "schema_version": self.schema_version,
            "plan_version": plan_version,
            "status": self.status,
            "event_class_targets": canonical_targets,
            "minimum_l1_count": minimum_l1_count,
            "minimum_l2_count": minimum_l2_count,
            "maximum_total_samples": maximum_total_samples,
            "maximum_live_samples": maximum_live_samples,
            "allowed_capture_classifications": allowed_capture_classifications,
            "stop_conditions": stop_conditions,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "owner_approval_reference": owner_approval_reference,
        }
        object.__setattr__(self, "sample_plan_id", sample_plan_id)
        object.__setattr__(self, "plan_version", plan_version)
        object.__setattr__(self, "event_class_targets", canonical_targets)
        object.__setattr__(self, "minimum_l1_count", minimum_l1_count)
        object.__setattr__(self, "minimum_l2_count", minimum_l2_count)
        object.__setattr__(self, "maximum_total_samples", maximum_total_samples)
        object.__setattr__(self, "maximum_live_samples", maximum_live_samples)
        object.__setattr__(self, "allowed_capture_classifications", allowed_capture_classifications)
        object.__setattr__(self, "stop_conditions", stop_conditions)
        object.__setattr__(self, "starts_at", starts_at)
        object.__setattr__(self, "ends_at", ends_at)
        object.__setattr__(self, "owner_approval_reference", owner_approval_reference)
        object.__setattr__(self, "_identity", _digest(material))

    @property
    def identity(self) -> str:
        return self._identity
