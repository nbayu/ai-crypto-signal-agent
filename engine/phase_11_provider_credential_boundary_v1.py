"""Explicit, ephemeral Phase 11 provider credential contracts.

This module validates safe credential metadata and delegates material
resolution only to a caller-supplied resolver.  It performs no discovery,
configuration lookup, provider call, persistence, or production action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Protocol


UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_UTC_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)

_PROVIDERS = frozenset(("DEEPSEEK", "ANTHROPIC"))


class CredentialResolutionStatusV1(StrEnum):
    RESOLVED = "RESOLVED"
    DENIED = "DENIED"


class CredentialFailureV1(StrEnum):
    NONE = "NONE"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    REFERENCE_NOT_FOUND = "REFERENCE_NOT_FOUND"
    PROVIDER_MISMATCH = "PROVIDER_MISMATCH"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    NOT_YET_VALID = "NOT_YET_VALID"
    EXPIRED = "EXPIRED"
    ROTATION_REQUIRED = "ROTATION_REQUIRED"
    RESOLVER_FAILURE = "RESOLVER_FAILURE"
    MALFORMED_RESOLUTION = "MALFORMED_RESOLUTION"
    UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"


class CredentialSourceKindV1(StrEnum):
    EXTERNAL_INJECTION = "EXTERNAL_INJECTION"
    TEST_FIXTURE = "TEST_FIXTURE"


class ProviderCredentialValidationError(ValueError):
    """Raised when credential metadata or resolution evidence fails closed."""


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        return _timestamp(value, "timestamp")
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON for safe metadata."""

    try:
        return json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ProviderCredentialValidationError(
            "non-canonical metadata"
        ) from error


def lowercase_sha256(value: Any) -> str:
    """Hash canonical safe metadata without accepting a prebuilt repr."""

    return sha256(canonical_json_bytes(value)).hexdigest()


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ProviderCredentialValidationError(f"invalid {label}")
    return value


def _positive_integer(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ProviderCredentialValidationError(f"invalid {label}")
    return value


def _hash_value(value: Any, label: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ProviderCredentialValidationError(f"invalid {label}")
    return value


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ProviderCredentialValidationError(f"invalid {label}")
        parsed = value.astimezone(UTC)
    elif type(value) is str and _UTC_TEXT.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ProviderCredentialValidationError(f"invalid {label}") from error
    else:
        raise ProviderCredentialValidationError(f"invalid {label}")
    normalized = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return normalized.replace("+00:00", "Z").replace(".000000Z", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ProviderCredentialValidationError("invalid reason_codes")
    normalized = tuple(sorted(value))
    if (
        len(set(normalized)) != len(normalized)
        or any(
            type(item) is not str or _REASON.fullmatch(item) is None
            for item in normalized
        )
    ):
        raise ProviderCredentialValidationError("invalid reason_codes")
    return normalized


def _enum_text(value: Any, enum_type: type[StrEnum], label: str) -> str:
    allowed = {item.value for item in enum_type}
    if value not in allowed:
        raise ProviderCredentialValidationError(f"invalid {label}")
    return str(value)


_REFERENCE_FIELDS = frozenset(
    (
        "schema_version",
        "credential_reference_id",
        "provider",
        "credential_version",
        "source_kind",
        "owner_approval_reference",
        "created_at",
        "valid_from",
        "valid_until",
        "rotation_required",
        "reference_identity",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ProviderCredentialReferenceV1:
    schema_version: str
    credential_reference_id: str
    provider: str
    credential_version: int
    source_kind: str
    owner_approval_reference: str
    created_at: str
    valid_from: str
    valid_until: str
    rotation_required: bool
    reference_identity: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _REFERENCE_FIELDS:
            raise ProviderCredentialValidationError(
                "invalid credential reference fields"
            )
        if (
            values["schema_version"]
            != "phase11-provider-credential-reference-v1"
        ):
            raise ProviderCredentialValidationError(
                "unsupported credential reference schema"
            )

        provider = values["provider"]
        if provider not in _PROVIDERS:
            raise ProviderCredentialValidationError("invalid provider")
        reference_id = _identifier(
            values["credential_reference_id"], "credential_reference_id"
        )
        version = _positive_integer(
            values["credential_version"], "credential_version"
        )
        source_kind = _enum_text(
            values["source_kind"], CredentialSourceKindV1, "source_kind"
        )
        approval = _identifier(
            values["owner_approval_reference"], "owner_approval_reference"
        )
        created_at = _timestamp(values["created_at"], "created_at")
        valid_from = _timestamp(values["valid_from"], "valid_from")
        valid_until = _timestamp(values["valid_until"], "valid_until")
        if _parsed(valid_until) < _parsed(valid_from):
            raise ProviderCredentialValidationError("invalid validity interval")
        if type(values["rotation_required"]) is not bool:
            raise ProviderCredentialValidationError("invalid rotation_required")
        rotation_required = values["rotation_required"]

        material = {
            "schema_version": values["schema_version"],
            "credential_reference_id": reference_id,
            "provider": provider,
            "credential_version": version,
            "source_kind": source_kind,
            "owner_approval_reference": approval,
            "created_at": created_at,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "rotation_required": rotation_required,
        }
        identity = lowercase_sha256(material)
        supplied_identity = _hash_value(
            values["reference_identity"],
            "reference_identity",
            optional=True,
        )
        if supplied_identity is not None and supplied_identity != identity:
            raise ProviderCredentialValidationError(
                "credential reference identity mismatch"
            )

        normalized = dict(values)
        normalized.update(
            credential_reference_id=reference_id,
            provider=provider,
            credential_version=version,
            source_kind=source_kind,
            owner_approval_reference=approval,
            created_at=created_at,
            valid_from=valid_from,
            valid_until=valid_until,
            rotation_required=rotation_required,
            reference_identity=identity,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.reference_identity


_EPHEMERAL_FIELDS = frozenset(
    (
        "schema_version",
        "provider",
        "credential_reference",
        "credential_reference_identity",
        "credential_version",
        "material",
    )
)


class EphemeralProviderCredentialV1:
    """Immutable material wrapper with one explicit, non-serializing access."""

    __slots__ = (
        "schema_version",
        "provider",
        "credential_reference",
        "credential_reference_identity",
        "credential_version",
        "_material",
        "_sealed",
    )

    schema_version: str
    provider: str
    credential_reference: ProviderCredentialReferenceV1
    credential_reference_identity: str
    credential_version: int
    _material: bytes | str
    _sealed: bool

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _EPHEMERAL_FIELDS:
            raise ProviderCredentialValidationError(
                "invalid ephemeral credential fields"
            )
        if (
            values["schema_version"]
            != "phase11-ephemeral-provider-credential-v1"
        ):
            raise ProviderCredentialValidationError(
                "unsupported ephemeral credential schema"
            )
        reference = values["credential_reference"]
        if type(reference) is not ProviderCredentialReferenceV1:
            raise ProviderCredentialValidationError(
                "invalid credential reference"
            )
        if values["provider"] != reference.provider:
            raise ProviderCredentialValidationError(
                "credential provider mismatch"
            )
        reference_identity = _hash_value(
            values["credential_reference_identity"],
            "credential_reference_identity",
        )
        if reference_identity != reference.identity:
            raise ProviderCredentialValidationError(
                "credential reference identity mismatch"
            )
        version = _positive_integer(
            values["credential_version"], "credential_version"
        )
        if version != reference.credential_version:
            raise ProviderCredentialValidationError(
                "credential version mismatch"
            )
        supplied_material = values["material"]
        if type(supplied_material) not in (bytes, str):
            raise ProviderCredentialValidationError(
                "invalid credential material type"
            )
        if (
            not supplied_material
            or (
                isinstance(supplied_material, str)
                and not supplied_material.strip()
            )
            or (
                isinstance(supplied_material, bytes)
                and not supplied_material.strip()
            )
        ):
            raise ProviderCredentialValidationError(
                "blank credential material"
            )

        object.__setattr__(self, "schema_version", values["schema_version"])
        object.__setattr__(self, "provider", reference.provider)
        object.__setattr__(self, "credential_reference", reference)
        object.__setattr__(
            self, "credential_reference_identity", reference.identity
        )
        object.__setattr__(self, "credential_version", version)
        object.__setattr__(self, "_material", supplied_material)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ephemeral credential is immutable")

    def material_for_adapter(self) -> bytes | str:
        """Return material only at an explicit, separately authorized boundary."""

        return self._material

    def __repr__(self) -> str:
        return (
            "EphemeralProviderCredentialV1("
            f"provider={self.provider!r}, "
            f"credential_reference_identity="
            f"{self.credential_reference_identity!r}, "
            f"credential_version={self.credential_version!r}, "
            "material=<redacted>)"
        )

    def __str__(self) -> str:
        return self.__repr__()


class ProviderCredentialResolverProtocol(Protocol):
    def resolve(
        self,
        reference: ProviderCredentialReferenceV1,
        resolved_at: str,
    ) -> Any: ...


_RESOLUTION_FIELDS = frozenset(
    (
        "schema_version",
        "resolution_identity",
        "credential_reference",
        "credential_reference_identity",
        "provider",
        "credential_version",
        "status",
        "failure_class",
        "resolved_at",
        "valid_until",
        "rotation_required",
        "reason_codes",
        "ephemeral_credential",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ProviderCredentialResolutionV1:
    schema_version: str
    resolution_identity: str
    credential_reference: ProviderCredentialReferenceV1
    credential_reference_identity: str
    provider: str
    credential_version: int
    status: str
    failure_class: str
    resolved_at: str
    valid_until: str
    rotation_required: bool
    reason_codes: tuple[str, ...]
    ephemeral_credential: EphemeralProviderCredentialV1 | None

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _RESOLUTION_FIELDS:
            raise ProviderCredentialValidationError(
                "invalid credential resolution fields"
            )
        if (
            values["schema_version"]
            != "phase11-provider-credential-resolution-v1"
        ):
            raise ProviderCredentialValidationError(
                "unsupported credential resolution schema"
            )

        reference = values["credential_reference"]
        if type(reference) is not ProviderCredentialReferenceV1:
            raise ProviderCredentialValidationError(
                "invalid credential reference"
            )
        reference_identity = _hash_value(
            values["credential_reference_identity"],
            "credential_reference_identity",
        )
        if reference_identity != reference.identity:
            raise ProviderCredentialValidationError(
                "credential reference identity mismatch"
            )
        if values["provider"] != reference.provider:
            raise ProviderCredentialValidationError(
                "resolution provider mismatch"
            )
        version = _positive_integer(
            values["credential_version"], "credential_version"
        )
        if version != reference.credential_version:
            raise ProviderCredentialValidationError(
                "resolution version mismatch"
            )
        status = _enum_text(
            values["status"],
            CredentialResolutionStatusV1,
            "resolution status",
        )
        failure = _enum_text(
            values["failure_class"], CredentialFailureV1, "failure_class"
        )
        resolved_at = _timestamp(values["resolved_at"], "resolved_at")
        valid_until = _timestamp(values["valid_until"], "valid_until")
        if valid_until != reference.valid_until:
            raise ProviderCredentialValidationError(
                "resolution validity mismatch"
            )
        if (
            type(values["rotation_required"]) is not bool
            or values["rotation_required"] != reference.rotation_required
        ):
            raise ProviderCredentialValidationError(
                "resolution rotation mismatch"
            )
        rotation_required = values["rotation_required"]
        reasons = _reasons(values["reason_codes"])
        credential = values["ephemeral_credential"]

        if status == CredentialResolutionStatusV1.RESOLVED:
            if failure != CredentialFailureV1.NONE:
                raise ProviderCredentialValidationError(
                    "successful resolution carries failure"
                )
            if type(credential) is not EphemeralProviderCredentialV1:
                raise ProviderCredentialValidationError(
                    "successful resolution lacks credential"
                )
            if (
                credential.provider != reference.provider
                or credential.credential_version
                != reference.credential_version
                or credential.credential_reference_identity
                != reference.identity
            ):
                raise ProviderCredentialValidationError(
                    "resolved credential binding mismatch"
                )
            moment = _parsed(resolved_at)
            if (
                moment < _parsed(reference.valid_from)
                or moment > _parsed(reference.valid_until)
                or rotation_required
            ):
                raise ProviderCredentialValidationError(
                    "successful resolution outside authority"
                )
        else:
            if failure == CredentialFailureV1.NONE:
                raise ProviderCredentialValidationError(
                    "denied resolution lacks failure"
                )
            if credential is not None:
                raise ProviderCredentialValidationError(
                    "denied resolution exposes credential"
                )

        material = {
            "schema_version": values["schema_version"],
            "credential_reference_identity": reference.identity,
            "provider": reference.provider,
            "credential_version": version,
            "status": status,
            "failure_class": failure,
            "resolved_at": resolved_at,
            "valid_until": valid_until,
            "rotation_required": rotation_required,
            "reason_codes": reasons,
        }
        identity = lowercase_sha256(material)
        supplied_identity = _hash_value(
            values["resolution_identity"],
            "resolution_identity",
            optional=True,
        )
        if supplied_identity is not None and supplied_identity != identity:
            raise ProviderCredentialValidationError(
                "credential resolution identity mismatch"
            )

        normalized = dict(values)
        normalized.update(
            resolution_identity=identity,
            credential_reference=reference,
            credential_reference_identity=reference.identity,
            provider=reference.provider,
            credential_version=version,
            status=status,
            failure_class=failure,
            resolved_at=resolved_at,
            valid_until=valid_until,
            rotation_required=rotation_required,
            reason_codes=reasons,
            ephemeral_credential=credential,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.resolution_identity


def _resolution(
    reference: ProviderCredentialReferenceV1,
    resolved_at: str,
    *,
    status: str,
    failure: str,
    reasons: tuple[str, ...],
    credential: EphemeralProviderCredentialV1 | None = None,
) -> ProviderCredentialResolutionV1:
    return ProviderCredentialResolutionV1(
        schema_version="phase11-provider-credential-resolution-v1",
        resolution_identity=None,
        credential_reference=reference,
        credential_reference_identity=reference.identity,
        provider=reference.provider,
        credential_version=reference.credential_version,
        status=status,
        failure_class=failure,
        resolved_at=resolved_at,
        valid_until=reference.valid_until,
        rotation_required=reference.rotation_required,
        reason_codes=reasons,
        ephemeral_credential=credential,
    )


def _denied(
    reference: ProviderCredentialReferenceV1,
    resolved_at: str,
    failure: CredentialFailureV1,
) -> ProviderCredentialResolutionV1:
    return _resolution(
        reference,
        resolved_at,
        status=CredentialResolutionStatusV1.DENIED,
        failure=failure,
        reasons=(failure.value,),
    )


def resolve_provider_credential(
    *,
    reference: ProviderCredentialReferenceV1,
    resolver: ProviderCredentialResolverProtocol,
    resolved_at: Any,
) -> ProviderCredentialResolutionV1:
    """Resolve one reference using only the explicitly supplied resolver."""

    if type(reference) is not ProviderCredentialReferenceV1:
        raise ProviderCredentialValidationError("invalid credential reference")
    moment_text = _timestamp(resolved_at, "resolved_at")
    moment = _parsed(moment_text)
    if moment < _parsed(reference.valid_from):
        return _denied(
            reference, moment_text, CredentialFailureV1.NOT_YET_VALID
        )
    if moment > _parsed(reference.valid_until):
        return _denied(reference, moment_text, CredentialFailureV1.EXPIRED)
    if reference.rotation_required:
        return _denied(
            reference, moment_text, CredentialFailureV1.ROTATION_REQUIRED
        )

    resolve_method = getattr(resolver, "resolve", None)
    if not callable(resolve_method):
        raise ProviderCredentialValidationError("invalid credential resolver")
    try:
        candidate = resolve_method(reference, moment_text)
    except Exception:
        return _denied(
            reference, moment_text, CredentialFailureV1.RESOLVER_FAILURE
        )

    if candidate is None:
        return _denied(
            reference, moment_text, CredentialFailureV1.REFERENCE_NOT_FOUND
        )
    if type(candidate) is not EphemeralProviderCredentialV1:
        return _denied(
            reference, moment_text, CredentialFailureV1.MALFORMED_RESOLUTION
        )
    if candidate.provider != reference.provider:
        return _denied(
            reference, moment_text, CredentialFailureV1.PROVIDER_MISMATCH
        )
    if candidate.credential_version != reference.credential_version:
        return _denied(
            reference, moment_text, CredentialFailureV1.VERSION_MISMATCH
        )
    if candidate.credential_reference_identity != reference.identity:
        return _denied(
            reference, moment_text, CredentialFailureV1.IDENTITY_MISMATCH
        )

    return _resolution(
        reference,
        moment_text,
        status=CredentialResolutionStatusV1.RESOLVED,
        failure=CredentialFailureV1.NONE,
        reasons=("CREDENTIAL_RESOLVED",),
        credential=candidate,
    )


__all__ = (
    "CredentialFailureV1",
    "CredentialResolutionStatusV1",
    "CredentialSourceKindV1",
    "EphemeralProviderCredentialV1",
    "ProviderCredentialReferenceV1",
    "ProviderCredentialResolutionV1",
    "ProviderCredentialResolverProtocol",
    "ProviderCredentialValidationError",
    "canonical_json_bytes",
    "lowercase_sha256",
    "resolve_provider_credential",
)
