"""Pure deterministic normalization for Phase 10 news captures."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from engine.news_event_contract_v1 import (
    EVENT_SCHEMA_VERSION,
    NewsEventContractError,
    NormalizedNewsEventV1,
    RawNewsCaptureV1,
    SourceDescriptorV1,
    canonical_json_bytes,
    sha256_hex,
)


NORMALIZATION_POLICY_VERSION = "news-normalization-policy-v1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}$")
_SCRIPT = re.compile(r"^[A-Za-z]{4}$")
_REGION = re.compile(r"^(?:[A-Za-z]{2}|[0-9]{3})$")
_TEXT_FIELDS = frozenset(
    {
        "raw_sha256",
        "normalized_text",
        "normalized_sha256",
        "normalization_policy_version",
    }
)
_RESULT_FIELDS = frozenset(
    {
        "normalization_policy_version",
        "source_snapshot_ref",
        "normalized_title",
        "normalized_body",
        "normalized_language",
        "normalized_content_sha256",
        "material_source_metadata",
        "material_source_metadata_sha256",
        "normalized_event",
    }
)


class NewsNormalizationError(ValueError):
    """Raised when deterministic news normalization rejects an input."""


def normalize_unicode_text(value: Any) -> str:
    """Normalize one exact string to Unicode NFC without semantic changes."""

    if type(value) is not str:
        raise NewsNormalizationError("text must be an exact string")
    return unicodedata.normalize("NFC", value)


def normalize_line_endings(value: Any) -> str:
    """Normalize CRLF and CR line endings to LF without trimming text."""

    text = normalize_unicode_text(value)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_identifier(value: Any) -> str:
    """Validate an identifier while applying NFC only."""

    identifier = normalize_unicode_text(value)
    if not identifier or identifier != identifier.strip():
        raise NewsNormalizationError(
            "identifier must be non-empty without surrounding whitespace"
        )
    return identifier


def normalize_language_tag(value: Any) -> str:
    """Apply the frozen conservative BCP-47-style language formatting."""

    tag = normalize_identifier(value)
    if "_" in tag or "--" in tag:
        raise NewsNormalizationError("language tag has invalid separators")

    parts = tag.split("-")
    if any(not part for part in parts):
        raise NewsNormalizationError("language tag has empty subtag")

    if parts[0].casefold() == "x":
        if len(parts) < 2 or any(not part.isalnum() for part in parts[1:]):
            raise NewsNormalizationError("language tag is invalid")
        return "-".join(["x", *(part.casefold() for part in parts[1:])])

    if _LANGUAGE.fullmatch(parts[0]) is None:
        raise NewsNormalizationError("language tag primary subtag is invalid")

    normalized = [parts[0].casefold()]
    remaining = parts[1:]
    if remaining and _SCRIPT.fullmatch(remaining[0]) is not None:
        normalized.append(remaining.pop(0).title())
    if remaining and _REGION.fullmatch(remaining[0]) is not None:
        region = remaining.pop(0)
        normalized.append(region.upper() if region.isalpha() else region)
    if remaining:
        raise NewsNormalizationError("language tag contains unsupported subtags")
    return "-".join(normalized)


def normalize_canonical_uri(value: Any) -> str:
    """Conservatively normalize a HTTP(S) URI without network activity."""

    uri = normalize_identifier(value)
    try:
        parsed = urlsplit(uri)
        port = parsed.port
    except ValueError as exc:
        raise NewsNormalizationError("canonical URI is invalid") from exc

    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"}:
        raise NewsNormalizationError("canonical URI scheme is unsupported")
    if not parsed.hostname:
        raise NewsNormalizationError("canonical URI host is required")
    if parsed.fragment:
        raise NewsNormalizationError("canonical URI fragments are prohibited")
    if parsed.username is not None or parsed.password is not None:
        raise NewsNormalizationError("canonical URI user information is prohibited")

    host = parsed.hostname.casefold()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    include_port = port is not None and not (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    )
    netloc = host if not include_port else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))


def normalize_metadata(value: Any) -> dict[str, Any]:
    """Return a detached canonical JSON-compatible metadata mapping."""

    if not isinstance(value, Mapping):
        raise NewsNormalizationError("metadata must be a mapping")
    try:
        canonical = canonical_json_bytes(_normalize_metadata_value(value))
    except NewsEventContractError as exc:
        raise NewsNormalizationError("metadata is not canonical JSON") from exc
    # Round-trip through canonical JSON gives key-order-independent detached data.
    import json

    return json.loads(canonical.decode("utf-8"))


def build_normalized_content_sha256(
    *,
    normalized_title: Any,
    normalized_body: Any,
    normalized_language: Any,
) -> str:
    """Hash only the normalized title, body, and language fields."""

    payload = {
        "normalized_title": _require_text(normalized_title, "normalized_title"),
        "normalized_body": _require_text(normalized_body, "normalized_body"),
        "normalized_language": _require_text(
            normalized_language, "normalized_language"
        ),
    }
    return sha256_hex(canonical_json_bytes(payload))


def build_material_source_metadata_sha256(value: Any) -> str:
    """Hash caller-supplied material source metadata without heuristics."""

    return sha256_hex(canonical_json_bytes(normalize_metadata(value)))


def build_source_snapshot_ref(
    *,
    source: Any,
    raw_capture: Any,
    point_in_time_timestamp_utc: Any,
    normalization_policy_version: Any,
) -> dict[str, Any]:
    """Build a closed reference to immutable source and capture facts."""

    if not isinstance(source, SourceDescriptorV1):
        raise NewsNormalizationError("source must be SourceDescriptorV1")
    if not isinstance(raw_capture, RawNewsCaptureV1):
        raise NewsNormalizationError("raw_capture must be RawNewsCaptureV1")
    if raw_capture.source != source:
        raise NewsNormalizationError("raw_capture source must match source")
    _require_policy_version(normalization_policy_version)
    timestamp = _require_datetime(point_in_time_timestamp_utc)

    reference = {
        "source_namespace": source.source_namespace,
        "source_id": source.source_id,
        "raw_content_sha256": raw_capture.raw_content_sha256,
        "capture_payload_sha256": raw_capture.capture_payload_sha256,
        "point_in_time_timestamp_utc": _timestamp_text(timestamp),
        "source_schema_version": source.schema_version,
        "normalization_policy_version": NORMALIZATION_POLICY_VERSION,
    }
    reference["source_snapshot_ref_id"] = sha256_hex(
        canonical_json_bytes(reference)
    )
    return reference


@dataclass(frozen=True, init=False)
class NormalizedTextV1:
    """Immutable normalization evidence for one text field."""

    raw_sha256: str
    normalized_text: str
    normalized_sha256: str
    normalization_policy_version: str

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _TEXT_FIELDS, "normalized text")
        raw_hash = _require_hash(values["raw_sha256"], "raw_sha256")
        text = _require_text(values["normalized_text"], "normalized_text")
        normalized_hash = _require_hash(
            values["normalized_sha256"], "normalized_sha256"
        )
        _require_policy_version(values["normalization_policy_version"])
        if normalized_hash != sha256_hex(text.encode("utf-8")):
            raise NewsNormalizationError(
                "normalized_sha256 does not match normalized_text"
            )
        object.__setattr__(self, "raw_sha256", raw_hash)
        object.__setattr__(self, "normalized_text", text)
        object.__setattr__(self, "normalized_sha256", normalized_hash)
        object.__setattr__(
            self,
            "normalization_policy_version",
            NORMALIZATION_POLICY_VERSION,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "raw_sha256": self.raw_sha256,
            "normalized_text": self.normalized_text,
            "normalized_sha256": self.normalized_sha256,
            "normalization_policy_version": self.normalization_policy_version,
        }


@dataclass(frozen=True, init=False)
class NormalizationResultV1:
    """Closed immutable output of deterministic capture normalization."""

    normalization_policy_version: str
    source_snapshot_ref: Mapping[str, Any]
    normalized_title: NormalizedTextV1
    normalized_body: NormalizedTextV1
    normalized_language: str
    normalized_content_sha256: str
    material_source_metadata: Mapping[str, Any]
    material_source_metadata_sha256: str
    normalized_event: NormalizedNewsEventV1

    def __init__(self, **values: Any) -> None:
        _require_exact_fields(values, _RESULT_FIELDS, "normalization result")
        _require_policy_version(values["normalization_policy_version"])
        title = values["normalized_title"]
        body = values["normalized_body"]
        if not isinstance(title, NormalizedTextV1):
            raise NewsNormalizationError("normalized_title must be NormalizedTextV1")
        if not isinstance(body, NormalizedTextV1):
            raise NewsNormalizationError("normalized_body must be NormalizedTextV1")
        language = normalize_language_tag(values["normalized_language"])
        content_hash = _require_hash(
            values["normalized_content_sha256"], "normalized_content_sha256"
        )
        expected_content_hash = build_normalized_content_sha256(
            normalized_title=title.normalized_text,
            normalized_body=body.normalized_text,
            normalized_language=language,
        )
        if content_hash != expected_content_hash:
            raise NewsNormalizationError("normalized_content_sha256 is invalid")

        metadata = normalize_metadata(values["material_source_metadata"])
        metadata_hash = _require_hash(
            values["material_source_metadata_sha256"],
            "material_source_metadata_sha256",
        )
        if metadata_hash != build_material_source_metadata_sha256(metadata):
            raise NewsNormalizationError("material_source_metadata_sha256 is invalid")
        snapshot_ref = _freeze_mapping(
            values["source_snapshot_ref"], "source_snapshot_ref"
        )
        event = values["normalized_event"]
        if not isinstance(event, NormalizedNewsEventV1):
            raise NewsNormalizationError("normalized_event must be NormalizedNewsEventV1")
        if event.normalized_title != title.normalized_text:
            raise NewsNormalizationError("normalized_event title is inconsistent")
        if event.normalized_body != body.normalized_text:
            raise NewsNormalizationError("normalized_event body is inconsistent")
        if event.normalized_language != language:
            raise NewsNormalizationError("normalized_event language is inconsistent")
        if event.material_source_metadata != _freeze_json(metadata):
            raise NewsNormalizationError("normalized_event metadata is inconsistent")
        if event.source_snapshot_ref != snapshot_ref:
            raise NewsNormalizationError("normalized_event source reference is inconsistent")

        object.__setattr__(
            self,
            "normalization_policy_version",
            NORMALIZATION_POLICY_VERSION,
        )
        object.__setattr__(self, "source_snapshot_ref", snapshot_ref)
        object.__setattr__(self, "normalized_title", title)
        object.__setattr__(self, "normalized_body", body)
        object.__setattr__(self, "normalized_language", language)
        object.__setattr__(self, "normalized_content_sha256", content_hash)
        object.__setattr__(self, "material_source_metadata", _freeze_json(metadata))
        object.__setattr__(self, "material_source_metadata_sha256", metadata_hash)
        object.__setattr__(self, "normalized_event", event)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "normalization_policy_version": self.normalization_policy_version,
            "source_snapshot_ref": _thaw_json(self.source_snapshot_ref),
            "normalized_title": self.normalized_title,
            "normalized_body": self.normalized_body,
            "normalized_language": self.normalized_language,
            "normalized_content_sha256": self.normalized_content_sha256,
            "material_source_metadata": _thaw_json(self.material_source_metadata),
            "material_source_metadata_sha256": (
                self.material_source_metadata_sha256
            ),
            "normalized_event": self.normalized_event,
        }


def normalize_news_capture(
    *,
    capture: Any,
    event_namespace: Any = None,
    authoritative_source_event_id: Any = None,
    deterministic_source_key: Any = None,
    normalized_primary_subject: Any = None,
    canonical_event_class: Any = None,
    material_source_metadata: Any = None,
    previous_event_version_id: Any = None,
    event_version_number: Any = None,
) -> NormalizationResultV1:
    """Normalize one capture using explicit non-semantic event inputs."""

    if not isinstance(capture, RawNewsCaptureV1):
        raise NewsNormalizationError("capture must be RawNewsCaptureV1")
    required = {
        "event_namespace": event_namespace,
        "normalized_primary_subject": normalized_primary_subject,
        "canonical_event_class": canonical_event_class,
        "material_source_metadata": material_source_metadata,
        "event_version_number": event_version_number,
    }
    if any(value is None for value in required.values()):
        raise NewsNormalizationError("explicit normalization event inputs are required")

    title = _normalized_text(capture.raw_title)
    body = _normalized_text(capture.raw_body)
    language = normalize_language_tag(capture.raw_language)
    metadata = normalize_metadata(material_source_metadata)
    content_hash = build_normalized_content_sha256(
        normalized_title=title.normalized_text,
        normalized_body=body.normalized_text,
        normalized_language=language,
    )
    metadata_hash = build_material_source_metadata_sha256(metadata)
    reference = build_source_snapshot_ref(
        source=capture.source,
        raw_capture=capture,
        point_in_time_timestamp_utc=capture.source.point_in_time_timestamp_utc,
        normalization_policy_version=NORMALIZATION_POLICY_VERSION,
    )
    try:
        event = NormalizedNewsEventV1(
            event_namespace=normalize_identifier(event_namespace),
            authoritative_source_namespace=normalize_identifier(
                capture.source.source_namespace
            ),
            authoritative_source_event_id=authoritative_source_event_id,
            deterministic_source_key=deterministic_source_key,
            normalized_primary_subject=normalize_identifier(
                normalized_primary_subject
            ),
            canonical_event_class=normalize_identifier(canonical_event_class),
            normalized_title=title.normalized_text,
            normalized_body=body.normalized_text,
            normalized_language=language,
            publication_timestamp_utc=capture.source.publication_timestamp_utc,
            point_in_time_timestamp_utc=(
                capture.source.point_in_time_timestamp_utc
            ),
            material_source_metadata=metadata,
            previous_event_version_id=previous_event_version_id,
            event_version_number=event_version_number,
            source_snapshot_ref=reference,
            schema_version=EVENT_SCHEMA_VERSION,
        )
    except NewsEventContractError as exc:
        raise NewsNormalizationError("normalized event validation failed") from exc

    return NormalizationResultV1(
        normalization_policy_version=NORMALIZATION_POLICY_VERSION,
        source_snapshot_ref=reference,
        normalized_title=title,
        normalized_body=body,
        normalized_language=language,
        normalized_content_sha256=content_hash,
        material_source_metadata=metadata,
        material_source_metadata_sha256=metadata_hash,
        normalized_event=event,
    )


def _normalized_text(raw_text: str) -> NormalizedTextV1:
    normalized = normalize_line_endings(normalize_unicode_text(raw_text)).strip()
    return NormalizedTextV1(
        raw_sha256=sha256_hex(raw_text.encode("utf-8")),
        normalized_text=normalized,
        normalized_sha256=sha256_hex(normalized.encode("utf-8")),
        normalization_policy_version=NORMALIZATION_POLICY_VERSION,
    )


def _normalize_metadata_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise NewsNormalizationError("metadata keys must be strings")
            result[key] = _normalize_metadata_value(item)
        return result
    if isinstance(value, list):
        return [_normalize_metadata_value(item) for item in value]
    raise NewsNormalizationError("metadata contains unsupported value")


def _require_exact_fields(
    values: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    if frozenset(values) != expected:
        raise NewsNormalizationError(f"invalid {label} fields")


def _require_hash(value: Any, field: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise NewsNormalizationError(f"{field} must be lowercase SHA-256")
    return value


def _require_policy_version(value: Any) -> str:
    if value != NORMALIZATION_POLICY_VERSION:
        raise NewsNormalizationError("invalid normalization_policy_version")
    return NORMALIZATION_POLICY_VERSION


def _require_text(value: Any, field: str) -> str:
    if type(value) is not str:
        raise NewsNormalizationError(f"{field} must be an exact string")
    return value


def _require_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise NewsNormalizationError("point_in_time_timestamp_utc must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise NewsNormalizationError("point_in_time_timestamp_utc must be UTC")
    if value.utcoffset().total_seconds() != 0:
        raise NewsNormalizationError("point_in_time_timestamp_utc must be UTC")
    return value.astimezone(value.tzinfo)


def _timestamp_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _freeze_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NewsNormalizationError(f"{field} must be a mapping")
    return _freeze_json(normalize_metadata(value))


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
