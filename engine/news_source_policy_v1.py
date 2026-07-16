"""Pure deterministic policy evaluation for Phase 10 source facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit

from engine.news_event_contract_v1 import RawNewsCaptureV1


SOURCE_POLICY_VERSION = "news-source-policy-v1"

__all__ = (
    "NewsSourcePolicyError",
    "SOURCE_POLICY_VERSION",
    "SourcePolicyConfigV1",
    "SourcePolicyDecisionV1",
    "evaluate_source_policy",
)


_DECISIONS = frozenset(("ELIGIBLE", "INELIGIBLE", "BLOCKED", "INVALID"))
_CREDIBILITY_RANK = {
    "TIER_1": 0,
    "TIER_2": 1,
    "TIER_3": 2,
    "TIER_4": 3,
}
_SOURCE_HEALTH = frozenset(
    ("HEALTHY", "DEGRADED", "UNVERIFIED", "BLOCKED", "FAILED")
)
_CONFIG_HEALTH = frozenset(("HEALTHY", "DEGRADED", "UNVERIFIED"))
_REASON_ORDER = (
    "SOURCE_TYPE_BLOCKED",
    "SOURCE_NAMESPACE_BLOCKED",
    "PUBLISHER_BLOCKED",
    "SOURCE_TYPE_NOT_ALLOWED",
    "SOURCE_NAMESPACE_NOT_ALLOWED",
    "PUBLISHER_NOT_ALLOWED",
    "CREDIBILITY_TIER_BELOW_MINIMUM",
    "SOURCE_HEALTH_UNACCEPTABLE",
    "CONTENT_TYPE_NOT_ALLOWED",
    "URI_SCHEME_NOT_ALLOWED",
    "PUBLICATION_TIMESTAMP_IN_FUTURE",
    "POINT_IN_TIME_INVALID",
    "SOURCE_TOO_OLD",
    "CAPTURE_DELAY_EXCEEDED",
)
_REASONS = frozenset(
    _REASON_ORDER
    + (
        "SOURCE_ELIGIBLE",
        "POLICY_CONFIGURATION_INVALID",
        "SOURCE_CONTRACT_INVALID",
    )
)
_CONFIG_FIELDS = frozenset(
    (
        "allowed_source_types",
        "blocked_source_types",
        "allowed_source_namespaces",
        "blocked_source_namespaces",
        "allowed_publishers",
        "blocked_publishers",
        "minimum_credibility_tier",
        "acceptable_source_health_statuses",
        "allowed_content_types",
        "allowed_uri_schemes",
        "maximum_source_age_seconds",
        "maximum_capture_delay_seconds",
        "policy_version",
    )
)
_DECISION_FIELDS = frozenset(
    (
        "policy_version",
        "decision",
        "primary_reason_code",
        "reason_codes",
        "evaluated_source_snapshot_ref",
        "evaluation_timestamp_utc",
        "source_namespace",
        "source_id",
    )
)


class NewsSourcePolicyError(ValueError):
    """Raised when a source-policy input violates the closed contract."""


@dataclass(frozen=True, init=False)
class SourcePolicyConfigV1:
    allowed_source_types: tuple[str, ...]
    blocked_source_types: tuple[str, ...]
    allowed_source_namespaces: tuple[str, ...]
    blocked_source_namespaces: tuple[str, ...]
    allowed_publishers: tuple[str, ...]
    blocked_publishers: tuple[str, ...]
    minimum_credibility_tier: str
    acceptable_source_health_statuses: tuple[str, ...]
    allowed_content_types: tuple[str, ...]
    allowed_uri_schemes: tuple[str, ...]
    maximum_source_age_seconds: int | None
    maximum_capture_delay_seconds: int | None
    policy_version: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _CONFIG_FIELDS, "source policy config")
        if values["policy_version"] != SOURCE_POLICY_VERSION:
            raise NewsSourcePolicyError("invalid policy_version")

        source_types = _freeze_strings(
            values["allowed_source_types"], "allowed_source_types"
        )
        blocked_source_types = _freeze_strings(
            values["blocked_source_types"], "blocked_source_types"
        )
        namespaces = _freeze_strings(
            values["allowed_source_namespaces"], "allowed_source_namespaces"
        )
        blocked_namespaces = _freeze_strings(
            values["blocked_source_namespaces"], "blocked_source_namespaces"
        )
        publishers = _freeze_strings(
            values["allowed_publishers"], "allowed_publishers"
        )
        blocked_publishers = _freeze_strings(
            values["blocked_publishers"], "blocked_publishers"
        )
        tier = _require_credibility_tier(
            values["minimum_credibility_tier"], "minimum_credibility_tier"
        )
        health = _freeze_health(values["acceptable_source_health_statuses"])
        content_types = _freeze_strings(
            values["allowed_content_types"], "allowed_content_types"
        )
        schemes = _freeze_uri_schemes(values["allowed_uri_schemes"])
        maximum_age = _require_duration(
            values["maximum_source_age_seconds"], "maximum_source_age_seconds"
        )
        maximum_delay = _require_duration(
            values["maximum_capture_delay_seconds"],
            "maximum_capture_delay_seconds",
        )

        object.__setattr__(self, "allowed_source_types", source_types)
        object.__setattr__(self, "blocked_source_types", blocked_source_types)
        object.__setattr__(self, "allowed_source_namespaces", namespaces)
        object.__setattr__(self, "blocked_source_namespaces", blocked_namespaces)
        object.__setattr__(self, "allowed_publishers", publishers)
        object.__setattr__(self, "blocked_publishers", blocked_publishers)
        object.__setattr__(self, "minimum_credibility_tier", tier)
        object.__setattr__(self, "acceptable_source_health_statuses", health)
        object.__setattr__(self, "allowed_content_types", content_types)
        object.__setattr__(self, "allowed_uri_schemes", schemes)
        object.__setattr__(self, "maximum_source_age_seconds", maximum_age)
        object.__setattr__(self, "maximum_capture_delay_seconds", maximum_delay)
        object.__setattr__(self, "policy_version", SOURCE_POLICY_VERSION)


@dataclass(frozen=True, init=False)
class SourcePolicyDecisionV1:
    policy_version: str
    decision: str
    primary_reason_code: str
    reason_codes: tuple[str, ...]
    evaluated_source_snapshot_ref: Mapping[str, Any]
    evaluation_timestamp_utc: datetime
    source_namespace: str
    source_id: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _DECISION_FIELDS, "source policy decision")
        if values["policy_version"] != SOURCE_POLICY_VERSION:
            raise NewsSourcePolicyError("invalid policy_version")
        decision = values["decision"]
        if decision not in _DECISIONS:
            raise NewsSourcePolicyError("invalid decision")
        reasons = _normalize_reasons(values["reason_codes"])
        primary = values["primary_reason_code"]
        if not isinstance(primary, str) or primary not in _REASONS:
            raise NewsSourcePolicyError("invalid primary_reason_code")
        if not reasons or primary != reasons[0]:
            raise NewsSourcePolicyError("primary_reason_code must be first reason")
        if decision == "ELIGIBLE":
            if reasons != ("SOURCE_ELIGIBLE",):
                raise NewsSourcePolicyError("eligible decision requires SOURCE_ELIGIBLE")
        elif "SOURCE_ELIGIBLE" in reasons:
            raise NewsSourcePolicyError("non-eligible decision cannot be eligible")

        snapshot_ref = _freeze_snapshot_ref(
            values["evaluated_source_snapshot_ref"]
        )
        timestamp = _require_utc_datetime(
            values["evaluation_timestamp_utc"], "evaluation_timestamp_utc"
        )
        source_namespace = _require_string(
            values["source_namespace"], "source_namespace"
        )
        source_id = _require_string(values["source_id"], "source_id")

        object.__setattr__(self, "policy_version", SOURCE_POLICY_VERSION)
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "primary_reason_code", primary)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "evaluated_source_snapshot_ref", snapshot_ref)
        object.__setattr__(self, "evaluation_timestamp_utc", timestamp)
        object.__setattr__(self, "source_namespace", source_namespace)
        object.__setattr__(self, "source_id", source_id)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "decision": self.decision,
            "primary_reason_code": self.primary_reason_code,
            "reason_codes": self.reason_codes,
            "evaluated_source_snapshot_ref": dict(
                self.evaluated_source_snapshot_ref
            ),
            "evaluation_timestamp_utc": self.evaluation_timestamp_utc,
            "source_namespace": self.source_namespace,
            "source_id": self.source_id,
        }


def evaluate_source_policy(
    *,
    source_snapshot: Any,
    config: Any,
    evaluation_timestamp_utc: Any,
) -> SourcePolicyDecisionV1:
    """Evaluate immutable supplied source facts against one closed policy."""

    if type(source_snapshot) is not RawNewsCaptureV1:
        raise NewsSourcePolicyError("source_snapshot must be RawNewsCaptureV1")
    if type(config) is not SourcePolicyConfigV1:
        raise NewsSourcePolicyError("config must be SourcePolicyConfigV1")
    evaluation = _require_utc_datetime(
        evaluation_timestamp_utc, "evaluation_timestamp_utc"
    )
    source = source_snapshot.source
    snapshot_ref = _source_snapshot_ref(source_snapshot)

    block_reasons = _hard_block_reasons(source, config)
    if block_reasons:
        return _decision(
            "BLOCKED", block_reasons, config, snapshot_ref, evaluation, source
        )

    ordinary_reasons = _ordinary_reasons(source, config, evaluation)
    if ordinary_reasons:
        state = (
            "INVALID"
            if any(
                reason
                in {
                    "PUBLICATION_TIMESTAMP_IN_FUTURE",
                    "POINT_IN_TIME_INVALID",
                }
                for reason in ordinary_reasons
            )
            else "INELIGIBLE"
        )
        return _decision(
            state, ordinary_reasons, config, snapshot_ref, evaluation, source
        )
    return _decision(
        "ELIGIBLE", ("SOURCE_ELIGIBLE",), config, snapshot_ref, evaluation, source
    )


def _hard_block_reasons(source: Any, config: SourcePolicyConfigV1) -> tuple[str, ...]:
    reasons: list[str] = []
    if source.source_type in config.blocked_source_types:
        reasons.append("SOURCE_TYPE_BLOCKED")
    if source.source_namespace in config.blocked_source_namespaces:
        reasons.append("SOURCE_NAMESPACE_BLOCKED")
    if source.publisher_identity in config.blocked_publishers:
        reasons.append("PUBLISHER_BLOCKED")
    return _ordered_reasons(reasons)


def _ordinary_reasons(
    source: Any,
    config: SourcePolicyConfigV1,
    evaluation: datetime,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if config.allowed_source_types and source.source_type not in config.allowed_source_types:
        reasons.append("SOURCE_TYPE_NOT_ALLOWED")
    if (
        config.allowed_source_namespaces
        and source.source_namespace not in config.allowed_source_namespaces
    ):
        reasons.append("SOURCE_NAMESPACE_NOT_ALLOWED")
    if config.allowed_publishers and source.publisher_identity not in config.allowed_publishers:
        reasons.append("PUBLISHER_NOT_ALLOWED")

    source_tier = source.credibility_tier
    if (
        source_tier not in _CREDIBILITY_RANK
        or _CREDIBILITY_RANK[source_tier]
        > _CREDIBILITY_RANK[config.minimum_credibility_tier]
    ):
        reasons.append("CREDIBILITY_TIER_BELOW_MINIMUM")
    if (
        source.source_health_status not in _SOURCE_HEALTH
        or source.source_health_status not in config.acceptable_source_health_statuses
    ):
        reasons.append("SOURCE_HEALTH_UNACCEPTABLE")
    if source.content_type not in config.allowed_content_types:
        reasons.append("CONTENT_TYPE_NOT_ALLOWED")
    if _uri_scheme(source.canonical_source_uri) not in config.allowed_uri_schemes:
        reasons.append("URI_SCHEME_NOT_ALLOWED")

    if source.publication_timestamp_utc > evaluation:
        reasons.append("PUBLICATION_TIMESTAMP_IN_FUTURE")
    if source.point_in_time_timestamp_utc < source.publication_timestamp_utc:
        reasons.append("POINT_IN_TIME_INVALID")
    if (
        config.maximum_source_age_seconds is not None
        and evaluation - source.publication_timestamp_utc
        > timedelta(seconds=config.maximum_source_age_seconds)
    ):
        reasons.append("SOURCE_TOO_OLD")
    if (
        config.maximum_capture_delay_seconds is not None
        and source.capture_timestamp_utc - source.publication_timestamp_utc
        > timedelta(seconds=config.maximum_capture_delay_seconds)
    ):
        reasons.append("CAPTURE_DELAY_EXCEEDED")
    return _ordered_reasons(reasons)


def _decision(
    state: str,
    reasons: tuple[str, ...],
    config: SourcePolicyConfigV1,
    snapshot_ref: Mapping[str, Any],
    evaluation: datetime,
    source: Any,
) -> SourcePolicyDecisionV1:
    ordered = _ordered_reasons(reasons)
    return SourcePolicyDecisionV1(
        policy_version=config.policy_version,
        decision=state,
        primary_reason_code=ordered[0],
        reason_codes=ordered,
        evaluated_source_snapshot_ref=snapshot_ref,
        evaluation_timestamp_utc=evaluation,
        source_namespace=source.source_namespace,
        source_id=source.source_id,
    )


def _source_snapshot_ref(source_snapshot: RawNewsCaptureV1) -> Mapping[str, Any]:
    source = source_snapshot.source
    return MappingProxyType(
        {
            "source_namespace": source.source_namespace,
            "source_id": source.source_id,
            "raw_content_sha256": source_snapshot.raw_content_sha256,
            "capture_payload_sha256": source_snapshot.capture_payload_sha256,
            "point_in_time_timestamp_utc": _datetime_text(
                source.point_in_time_timestamp_utc
            ),
            "source_schema_version": source.schema_version,
            "policy_version": SOURCE_POLICY_VERSION,
        }
    )


def _require_exact_fields(
    values: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    if not isinstance(values, Mapping) or frozenset(values) != expected:
        raise NewsSourcePolicyError("invalid " + label + " fields")


def _freeze_strings(value: Any, field: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise NewsSourcePolicyError(field + " must be a collection")
    try:
        items = tuple(value)
    except TypeError as exc:
        raise NewsSourcePolicyError(field + " must be a collection") from exc
    return tuple(sorted({_require_string(item, field) for item in items}))


def _freeze_health(value: Any) -> tuple[str, ...]:
    items = _freeze_strings(value, "acceptable_source_health_statuses")
    if any(item not in _CONFIG_HEALTH for item in items):
        raise NewsSourcePolicyError("invalid acceptable_source_health_statuses")
    return items


def _freeze_uri_schemes(value: Any) -> tuple[str, ...]:
    items = _freeze_strings(value, "allowed_uri_schemes")
    if any(item not in {"http", "https"} for item in items):
        raise NewsSourcePolicyError("invalid allowed_uri_schemes")
    return items


def _require_duration(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise NewsSourcePolicyError(field + " must be a non-negative integer")
    if value < 0:
        raise NewsSourcePolicyError(field + " must be non-negative")
    return value


def _require_credibility_tier(value: Any, field: str) -> str:
    value = _require_string(value, field)
    if value not in _CREDIBILITY_RANK:
        raise NewsSourcePolicyError("invalid " + field)
    return value


def _require_string(value: Any, field: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise NewsSourcePolicyError(field + " must be a non-empty string")
    return value


def _require_utc_datetime(value: Any, field: str) -> datetime:
    if type(value) is not datetime:
        raise NewsSourcePolicyError(field + " must be a datetime")
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        raise NewsSourcePolicyError(field + " must be timezone-aware")
    if offset != timedelta(0):
        raise NewsSourcePolicyError(field + " must use UTC")
    return value.astimezone(timezone.utc)


def _uri_scheme(value: str) -> str:
    try:
        return urlsplit(value).scheme
    except ValueError as exc:
        raise NewsSourcePolicyError("invalid canonical_source_uri") from exc


def _ordered_reasons(reasons: Any) -> tuple[str, ...]:
    values = set(reasons)
    if not values:
        return ()
    if "SOURCE_ELIGIBLE" in values:
        if values != {"SOURCE_ELIGIBLE"}:
            raise NewsSourcePolicyError("SOURCE_ELIGIBLE cannot be combined")
        return ("SOURCE_ELIGIBLE",)
    if any(reason not in _REASONS for reason in values):
        raise NewsSourcePolicyError("invalid reason_codes")
    return tuple(reason for reason in _REASON_ORDER if reason in values)


def _normalize_reasons(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise NewsSourcePolicyError("reason_codes must be a collection")
    try:
        supplied = tuple(value)
    except TypeError as exc:
        raise NewsSourcePolicyError("reason_codes must be a collection") from exc
    if any(not isinstance(reason, str) for reason in supplied):
        raise NewsSourcePolicyError("invalid reason_codes")
    normalized = _ordered_reasons(supplied)
    if tuple(supplied) != normalized:
        raise NewsSourcePolicyError("reason_codes must use canonical order")
    return normalized


def _freeze_snapshot_ref(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NewsSourcePolicyError("evaluated_source_snapshot_ref must be a mapping")
    frozen: dict[str, Any] = {}
    for key, item in value.items():
        if type(key) is not str:
            raise NewsSourcePolicyError("evaluated_source_snapshot_ref has invalid key")
        if type(item) not in (str, int, bool) and item is not None:
            raise NewsSourcePolicyError("evaluated_source_snapshot_ref has invalid value")
        frozen[key] = item
    return MappingProxyType(dict(sorted(frozen.items())))


def _datetime_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
