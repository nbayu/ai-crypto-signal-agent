"""Pure Phase 10 contracts for source capture and normalized news events."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit


SOURCE_SCHEMA_VERSION = "news-source-schema-v1"
EVENT_SCHEMA_VERSION = "news-event-schema-v1"

__all__ = [
    "NewsEventContractError",
    "SOURCE_SCHEMA_VERSION",
    "EVENT_SCHEMA_VERSION",
    "SourceDescriptorV1",
    "RawNewsCaptureV1",
    "NormalizedNewsEventV1",
    "canonical_json_bytes",
    "sha256_hex",
    "build_event_id",
    "build_event_version_id",
    "build_event_snapshot_id",
]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC = timezone.utc

_SOURCE_FIELDS = frozenset(
    {
        "source_namespace",
        "source_id",
        "source_type",
        "canonical_source_uri",
        "publisher_identity",
        "credibility_tier",
        "publication_timestamp_utc",
        "capture_timestamp_utc",
        "point_in_time_timestamp_utc",
        "content_type",
        "language",
        "raw_content_sha256",
        "source_metadata",
        "source_health_status",
        "schema_version",
    }
)
_RAW_CAPTURE_FIELDS = frozenset(
    {
        "source",
        "raw_title",
        "raw_body",
        "raw_language",
        "raw_content_sha256",
        "capture_payload_sha256",
        "captured_at_utc",
        "schema_version",
    }
)
_EVENT_INPUT_FIELDS = frozenset(
    {
        "event_namespace",
        "authoritative_source_namespace",
        "authoritative_source_event_id",
        "deterministic_source_key",
        "normalized_primary_subject",
        "canonical_event_class",
        "normalized_title",
        "normalized_body",
        "normalized_language",
        "publication_timestamp_utc",
        "point_in_time_timestamp_utc",
        "material_source_metadata",
        "previous_event_version_id",
        "event_version_number",
        "source_snapshot_ref",
        "schema_version",
        "event_id",
        "event_version_id",
        "event_snapshot_id",
    }
)
_EVENT_REQUIRED_INPUT_FIELDS = _EVENT_INPUT_FIELDS - {
    "event_id",
    "event_version_id",
    "event_snapshot_id",
}


class NewsEventContractError(ValueError):
    """Raised when a Phase 10 event-contract value violates its schema."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON for the closed contract domain."""

    normalized = _canonical_value(value, allow_datetime=True)
    try:
        encoded = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise NewsEventContractError("value is not canonical JSON") from exc
    return encoded.encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    """Return the lowercase SHA-256 hexadecimal digest of bytes only."""

    if not isinstance(payload, bytes):
        raise NewsEventContractError("SHA-256 payload must be bytes")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, init=False)
class SourceDescriptorV1:
    source_namespace: str
    source_id: str
    source_type: str
    canonical_source_uri: str
    publisher_identity: str
    credibility_tier: str
    publication_timestamp_utc: datetime
    capture_timestamp_utc: datetime
    point_in_time_timestamp_utc: datetime
    content_type: str
    language: str
    raw_content_sha256: str
    source_metadata: Mapping[str, Any]
    source_health_status: str
    schema_version: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _SOURCE_FIELDS, "source descriptor")

        source_namespace = _require_string(
            values["source_namespace"], "source_namespace"
        )
        source_id = _require_string(values["source_id"], "source_id")
        source_type = _require_string(values["source_type"], "source_type")
        uri = _require_uri(values["canonical_source_uri"])
        publisher_identity = _require_string(
            values["publisher_identity"], "publisher_identity"
        )
        credibility_tier = _require_string(
            values["credibility_tier"], "credibility_tier"
        )
        published_at = _require_utc_datetime(
            values["publication_timestamp_utc"],
            "publication_timestamp_utc",
        )
        capture = _require_utc_datetime(
            values["capture_timestamp_utc"], "capture_timestamp_utc"
        )
        point_in_time = _require_utc_datetime(
            values["point_in_time_timestamp_utc"],
            "point_in_time_timestamp_utc",
        )
        if published_at > capture:
            raise NewsEventContractError(
                "publication_timestamp_utc must not follow capture_timestamp_utc"
            )
        if capture > point_in_time:
            raise NewsEventContractError(
                "capture_timestamp_utc must not follow point_in_time_timestamp_utc"
            )

        content_type = _require_string(
            values["content_type"], "content_type"
        )
        language = _require_string(values["language"], "language")
        raw_hash = _require_hash(
            values["raw_content_sha256"], "raw_content_sha256"
        )
        metadata = _freeze_json_mapping(
            values["source_metadata"], "source_metadata"
        )
        health_status = _require_string(
            values["source_health_status"], "source_health_status"
        )
        if values["schema_version"] != SOURCE_SCHEMA_VERSION:
            raise NewsEventContractError("invalid source schema_version")

        object.__setattr__(self, "source_namespace", source_namespace)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "canonical_source_uri", uri)
        object.__setattr__(self, "publisher_identity", publisher_identity)
        object.__setattr__(self, "credibility_tier", credibility_tier)
        object.__setattr__(self, "publication_timestamp_utc", published_at)
        object.__setattr__(self, "capture_timestamp_utc", capture)
        object.__setattr__(self, "point_in_time_timestamp_utc", point_in_time)
        object.__setattr__(self, "content_type", content_type)
        object.__setattr__(self, "language", language)
        object.__setattr__(self, "raw_content_sha256", raw_hash)
        object.__setattr__(self, "source_metadata", metadata)
        object.__setattr__(self, "source_health_status", health_status)
        object.__setattr__(self, "schema_version", SOURCE_SCHEMA_VERSION)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "source_namespace": self.source_namespace,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "canonical_source_uri": self.canonical_source_uri,
            "publisher_identity": self.publisher_identity,
            "credibility_tier": self.credibility_tier,
            "publication_timestamp_utc": _datetime_text(
                self.publication_timestamp_utc
            ),
            "capture_timestamp_utc": _datetime_text(self.capture_timestamp_utc),
            "point_in_time_timestamp_utc": _datetime_text(
                self.point_in_time_timestamp_utc
            ),
            "content_type": self.content_type,
            "language": self.language,
            "raw_content_sha256": self.raw_content_sha256,
            "source_metadata": _thaw_json(self.source_metadata),
            "source_health_status": self.source_health_status,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, init=False)
class RawNewsCaptureV1:
    source: SourceDescriptorV1
    raw_title: str
    raw_body: str
    raw_language: str
    raw_content_sha256: str
    capture_payload_sha256: str
    captured_at_utc: datetime
    schema_version: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RAW_CAPTURE_FIELDS, "raw news capture")
        source = values["source"]
        if not isinstance(source, SourceDescriptorV1):
            raise NewsEventContractError("source must be SourceDescriptorV1")

        raw_title = _require_string(values["raw_title"], "raw_title")
        raw_body = _require_string(values["raw_body"], "raw_body")
        raw_language = _require_string(values["raw_language"], "raw_language")
        raw_hash = _require_hash(
            values["raw_content_sha256"], "raw_content_sha256"
        )
        expected_raw_hash = sha256_hex(raw_body.encode("utf-8"))
        if raw_hash != expected_raw_hash:
            raise NewsEventContractError("raw_content_sha256 does not match raw_body")
        if raw_hash != source.raw_content_sha256:
            raise NewsEventContractError("raw_content_sha256 does not match source")

        captured_at = _require_utc_datetime(
            values["captured_at_utc"], "captured_at_utc"
        )
        if captured_at != source.capture_timestamp_utc:
            raise NewsEventContractError(
                "captured_at_utc must equal source capture_timestamp_utc"
            )
        if values["schema_version"] != EVENT_SCHEMA_VERSION:
            raise NewsEventContractError("invalid raw capture schema_version")

        capture_hash = _require_hash(
            values["capture_payload_sha256"], "capture_payload_sha256"
        )
        expected_capture_hash = sha256_hex(
            canonical_json_bytes(
                {
                    "source": source.to_mapping(),
                    "raw_title": raw_title,
                    "raw_body": raw_body,
                    "raw_language": raw_language,
                    "raw_content_sha256": raw_hash,
                    "captured_at_utc": captured_at,
                    "schema_version": EVENT_SCHEMA_VERSION,
                }
            )
        )
        if capture_hash != expected_capture_hash:
            raise NewsEventContractError(
                "capture_payload_sha256 does not match capture payload"
            )

        object.__setattr__(self, "source", source)
        object.__setattr__(self, "raw_title", raw_title)
        object.__setattr__(self, "raw_body", raw_body)
        object.__setattr__(self, "raw_language", raw_language)
        object.__setattr__(self, "raw_content_sha256", raw_hash)
        object.__setattr__(self, "capture_payload_sha256", capture_hash)
        object.__setattr__(self, "captured_at_utc", captured_at)
        object.__setattr__(self, "schema_version", EVENT_SCHEMA_VERSION)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "source": self.source.to_mapping(),
            "raw_title": self.raw_title,
            "raw_body": self.raw_body,
            "raw_language": self.raw_language,
            "raw_content_sha256": self.raw_content_sha256,
            "capture_payload_sha256": self.capture_payload_sha256,
            "captured_at_utc": _datetime_text(self.captured_at_utc),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, init=False)
class NormalizedNewsEventV1:
    event_namespace: str
    authoritative_source_namespace: str
    authoritative_source_event_id: str | None
    deterministic_source_key: str | None
    normalized_primary_subject: str
    canonical_event_class: str
    normalized_title: str
    normalized_body: str
    normalized_language: str
    publication_timestamp_utc: datetime
    point_in_time_timestamp_utc: datetime
    material_source_metadata: Mapping[str, Any]
    previous_event_version_id: str | None
    event_version_number: int
    source_snapshot_ref: Mapping[str, Any]
    schema_version: str
    event_id: str
    event_version_id: str
    event_snapshot_id: str

    def __init__(self, **values: Any) -> None:
        _require_event_fields(values)
        if values["schema_version"] != EVENT_SCHEMA_VERSION:
            raise NewsEventContractError("invalid event schema_version")

        event_namespace = _require_string(
            values["event_namespace"], "event_namespace"
        )
        source_namespace = _require_string(
            values["authoritative_source_namespace"],
            "authoritative_source_namespace",
        )
        source_event_id = _require_optional_string(
            values["authoritative_source_event_id"],
            "authoritative_source_event_id",
        )
        source_key = _require_optional_string(
            values["deterministic_source_key"],
            "deterministic_source_key",
        )
        subject = _require_string(
            values["normalized_primary_subject"],
            "normalized_primary_subject",
        )
        event_class = _require_string(
            values["canonical_event_class"], "canonical_event_class"
        )
        title = _require_string(values["normalized_title"], "normalized_title")
        body = _require_string(values["normalized_body"], "normalized_body")
        language = _require_string(
            values["normalized_language"], "normalized_language"
        )
        published_at = _require_utc_datetime(
            values["publication_timestamp_utc"],
            "publication_timestamp_utc",
        )
        point_in_time = _require_utc_datetime(
            values["point_in_time_timestamp_utc"],
            "point_in_time_timestamp_utc",
        )
        if published_at > point_in_time:
            raise NewsEventContractError(
                "publication_timestamp_utc must not follow point_in_time_timestamp_utc"
            )
        metadata = _freeze_json_mapping(
            values["material_source_metadata"], "material_source_metadata"
        )
        snapshot_ref = _freeze_json_mapping(
            values["source_snapshot_ref"], "source_snapshot_ref"
        )

        version_number = values["event_version_number"]
        if isinstance(version_number, bool) or not isinstance(version_number, int):
            raise NewsEventContractError("event_version_number must be an integer")
        if version_number < 1:
            raise NewsEventContractError("event_version_number must be positive")

        previous = values["previous_event_version_id"]
        if version_number == 1:
            if previous is not None:
                raise NewsEventContractError(
                    "version 1 must not contain previous_event_version_id"
                )
        else:
            previous = _require_hash(
                previous, "previous_event_version_id"
            )

        derived_event_id = build_event_id(
            event_namespace=event_namespace,
            authoritative_source_namespace=source_namespace,
            authoritative_source_event_id=source_event_id,
            deterministic_source_key=source_key,
            normalized_primary_subject=subject,
            canonical_event_class=event_class,
        )
        _validate_optional_derived_identity(
            values.get("event_id"), derived_event_id, "event_id"
        )

        content_hash = sha256_hex(
            canonical_json_bytes(
                {
                    "normalized_title": title,
                    "normalized_body": body,
                    "normalized_language": language,
                    "previous_event_version_id": previous,
                }
            )
        )
        metadata_hash = sha256_hex(canonical_json_bytes(_thaw_json(metadata)))
        derived_version_id = build_event_version_id(
            event_id=derived_event_id,
            canonical_normalized_content_hash=content_hash,
            publication_timestamp_utc=published_at,
            material_source_metadata_hash=metadata_hash,
            event_schema_version=EVENT_SCHEMA_VERSION,
        )
        _validate_optional_derived_identity(
            values.get("event_version_id"),
            derived_version_id,
            "event_version_id",
        )
        if previous == derived_version_id:
            raise NewsEventContractError(
                "previous_event_version_id must not self-reference"
            )

        snapshot_payload = {
            "event_namespace": event_namespace,
            "authoritative_source_namespace": source_namespace,
            "authoritative_source_event_id": source_event_id,
            "deterministic_source_key": source_key,
            "normalized_primary_subject": subject,
            "canonical_event_class": event_class,
            "normalized_title": title,
            "normalized_body": body,
            "normalized_language": language,
            "publication_timestamp_utc": _datetime_text(published_at),
            "point_in_time_timestamp_utc": _datetime_text(point_in_time),
            "material_source_metadata": _thaw_json(metadata),
            "previous_event_version_id": previous,
            "event_version_number": version_number,
            "source_snapshot_ref": _thaw_json(snapshot_ref),
            "schema_version": EVENT_SCHEMA_VERSION,
            "event_id": derived_event_id,
            "event_version_id": derived_version_id,
        }
        derived_snapshot_id = sha256_hex(canonical_json_bytes(snapshot_payload))
        _validate_optional_derived_identity(
            values.get("event_snapshot_id"),
            derived_snapshot_id,
            "event_snapshot_id",
        )

        object.__setattr__(self, "event_namespace", event_namespace)
        object.__setattr__(
            self, "authoritative_source_namespace", source_namespace
        )
        object.__setattr__(
            self, "authoritative_source_event_id", source_event_id
        )
        object.__setattr__(self, "deterministic_source_key", source_key)
        object.__setattr__(self, "normalized_primary_subject", subject)
        object.__setattr__(self, "canonical_event_class", event_class)
        object.__setattr__(self, "normalized_title", title)
        object.__setattr__(self, "normalized_body", body)
        object.__setattr__(self, "normalized_language", language)
        object.__setattr__(self, "publication_timestamp_utc", published_at)
        object.__setattr__(self, "point_in_time_timestamp_utc", point_in_time)
        object.__setattr__(self, "material_source_metadata", metadata)
        object.__setattr__(self, "previous_event_version_id", previous)
        object.__setattr__(self, "event_version_number", version_number)
        object.__setattr__(self, "source_snapshot_ref", snapshot_ref)
        object.__setattr__(self, "schema_version", EVENT_SCHEMA_VERSION)
        object.__setattr__(self, "event_id", derived_event_id)
        object.__setattr__(self, "event_version_id", derived_version_id)
        object.__setattr__(self, "event_snapshot_id", derived_snapshot_id)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "event_namespace": self.event_namespace,
            "authoritative_source_namespace": (
                self.authoritative_source_namespace
            ),
            "authoritative_source_event_id": self.authoritative_source_event_id,
            "deterministic_source_key": self.deterministic_source_key,
            "normalized_primary_subject": self.normalized_primary_subject,
            "canonical_event_class": self.canonical_event_class,
            "normalized_title": self.normalized_title,
            "normalized_body": self.normalized_body,
            "normalized_language": self.normalized_language,
            "publication_timestamp_utc": _datetime_text(
                self.publication_timestamp_utc
            ),
            "point_in_time_timestamp_utc": _datetime_text(
                self.point_in_time_timestamp_utc
            ),
            "material_source_metadata": _thaw_json(
                self.material_source_metadata
            ),
            "previous_event_version_id": self.previous_event_version_id,
            "event_version_number": self.event_version_number,
            "source_snapshot_ref": _thaw_json(self.source_snapshot_ref),
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "event_version_id": self.event_version_id,
            "event_snapshot_id": self.event_snapshot_id,
        }


def build_event_id(
    *,
    event_namespace: Any,
    authoritative_source_namespace: Any,
    authoritative_source_event_id: Any,
    deterministic_source_key: Any,
    normalized_primary_subject: Any,
    canonical_event_class: Any,
) -> str:
    """Derive a logical-event identity from its frozen authority fields."""

    event_id = _require_optional_string(
        authoritative_source_event_id, "authoritative_source_event_id"
    )
    source_key = _require_optional_string(
        deterministic_source_key, "deterministic_source_key"
    )
    if (event_id is None) == (source_key is None):
        raise NewsEventContractError(
            "exactly one authoritative source identity is required"
        )

    payload: dict[str, Any] = {
        "event_namespace": _require_string(event_namespace, "event_namespace"),
        "authoritative_source_namespace": _require_string(
            authoritative_source_namespace,
            "authoritative_source_namespace",
        ),
        "normalized_primary_subject": _require_string(
            normalized_primary_subject, "normalized_primary_subject"
        ),
        "canonical_event_class": _require_string(
            canonical_event_class, "canonical_event_class"
        ),
    }
    if event_id is not None:
        payload["authoritative_source_event_id"] = event_id
    else:
        payload["deterministic_source_key"] = source_key
    return sha256_hex(canonical_json_bytes(payload))


def build_event_version_id(
    *,
    event_id: Any,
    canonical_normalized_content_hash: Any,
    publication_timestamp_utc: Any,
    material_source_metadata_hash: Any,
    event_schema_version: Any,
) -> str:
    """Derive an immutable event-version identity."""

    if not isinstance(event_schema_version, str) or not event_schema_version:
        raise NewsEventContractError("event_schema_version must be a string")
    payload = {
        "event_id": _require_hash(event_id, "event_id"),
        "canonical_normalized_content_hash": _require_hash(
            canonical_normalized_content_hash,
            "canonical_normalized_content_hash",
        ),
        "publication_timestamp_utc": _datetime_text(
            _require_utc_datetime(
                publication_timestamp_utc, "publication_timestamp_utc"
            )
        ),
        "material_source_metadata_hash": _require_hash(
            material_source_metadata_hash,
            "material_source_metadata_hash",
        ),
        "event_schema_version": event_schema_version,
    }
    return sha256_hex(canonical_json_bytes(payload))


def build_event_snapshot_id(*, normalized_event: Any) -> str:
    """Derive the anti-circular snapshot identity of one normalized event."""

    if not isinstance(normalized_event, NormalizedNewsEventV1):
        raise NewsEventContractError(
            "normalized_event must be NormalizedNewsEventV1"
        )
    payload = normalized_event.to_mapping()
    payload.pop("event_snapshot_id")
    return sha256_hex(canonical_json_bytes(payload))


def _require_exact_fields(
    values: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    actual = frozenset(values)
    if actual != expected:
        raise NewsEventContractError(f"invalid {label} fields")


def _require_event_fields(values: Mapping[str, Any]) -> None:
    actual = frozenset(values)
    unknown = actual - _EVENT_INPUT_FIELDS
    missing = _EVENT_REQUIRED_INPUT_FIELDS - actual
    if unknown or missing:
        raise NewsEventContractError("invalid normalized event fields")


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise NewsEventContractError(f"{field} must be a non-empty string")
    return value


def _require_optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, field)


def _require_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise NewsEventContractError(f"{field} must be lowercase SHA-256")
    return value


def _require_uri(value: Any) -> str:
    uri = _require_string(value, "canonical_source_uri")
    parsed = urlsplit(uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise NewsEventContractError("canonical_source_uri is invalid")
    if parsed.fragment:
        raise NewsEventContractError("canonical_source_uri must not contain fragment")
    return uri


def _require_utc_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise NewsEventContractError(f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise NewsEventContractError(f"{field} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise NewsEventContractError(f"{field} must use UTC offset zero")
    return value.astimezone(_UTC)


def _datetime_text(value: datetime) -> str:
    verified = _require_utc_datetime(value, "timestamp")
    return verified.isoformat().replace("+00:00", "Z")


def _canonical_value(value: Any, *, allow_datetime: bool) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise NewsEventContractError("non-finite numbers are prohibited")
        raise NewsEventContractError("binary floating-point values are prohibited")
    if isinstance(value, datetime):
        if allow_datetime:
            return _datetime_text(value)
        raise NewsEventContractError("datetime is not JSON-compatible here")
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise NewsEventContractError("JSON mapping keys must be strings")
            normalized[key] = _canonical_value(
                item, allow_datetime=allow_datetime
            )
        return normalized
    if isinstance(value, list):
        return [_canonical_value(item, allow_datetime=allow_datetime) for item in value]
    if isinstance(value, (bytes, bytearray, tuple, set, frozenset)):
        raise NewsEventContractError("value is not JSON-compatible")
    raise NewsEventContractError("value is not JSON-compatible")


def _freeze_json_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NewsEventContractError(f"{field} must be a mapping")
    normalized = _canonical_value(value, allow_datetime=False)
    return _freeze_json(normalized)


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _validate_optional_derived_identity(
    supplied: Any, derived: str, field: str
) -> None:
    if supplied is None:
        return
    if _require_hash(supplied, field) != derived:
        raise NewsEventContractError(f"{field} does not match derived identity")
