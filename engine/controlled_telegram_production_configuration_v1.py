"""Pure, fail-closed configuration validation for controlled Telegram publication."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
import re


TELEGRAM_CREDENTIAL_NAME = "telegram_bot_token"
TELEGRAM_CHANNEL = "telegram"
TELEGRAM_DESTINATION_KIND = "chat"

SYSTEMD_CREDENTIAL = "SYSTEMD_CREDENTIAL"
INJECTED_SECRET_RESOLVER = "INJECTED_SECRET_RESOLVER"

CONTROLLED_CREDENTIAL_METADATA_VALID = "CONTROLLED_CREDENTIAL_METADATA_VALID"
CONTROLLED_TELEGRAM_CONFIGURATION_VALID = (
    "CONTROLLED_TELEGRAM_CONFIGURATION_VALID"
)
INVALID_CREDENTIAL_METADATA = "INVALID_CREDENTIAL_METADATA"
CREDENTIAL_METADATA_UNAVAILABLE = "CREDENTIAL_METADATA_UNAVAILABLE"
INVALID_TELEGRAM_CHANNEL = "INVALID_TELEGRAM_CHANNEL"
INVALID_TELEGRAM_DESTINATION = "INVALID_TELEGRAM_DESTINATION"
DESTINATION_DISABLED = "DESTINATION_DISABLED"
DESTINATION_NOT_ALLOWLISTED = "DESTINATION_NOT_ALLOWLISTED"
INVALID_COMPONENT_VERSIONS = "INVALID_COMPONENT_VERSIONS"
INVALID_ACTIVE_LEDGER_INPUT = "INVALID_ACTIVE_LEDGER_INPUT"
INVALID_ACTIVE_LEDGER_REVISION = "INVALID_ACTIVE_LEDGER_REVISION"
FAIL_CLOSED = "FAIL_CLOSED"

_SOURCE_KINDS = frozenset((SYSTEMD_CREDENTIAL, INJECTED_SECRET_RESOLVER))
_CLASSIFICATIONS = frozenset(
    (
        CONTROLLED_CREDENTIAL_METADATA_VALID,
        CONTROLLED_TELEGRAM_CONFIGURATION_VALID,
        INVALID_CREDENTIAL_METADATA,
        CREDENTIAL_METADATA_UNAVAILABLE,
        INVALID_TELEGRAM_CHANNEL,
        INVALID_TELEGRAM_DESTINATION,
        DESTINATION_DISABLED,
        DESTINATION_NOT_ALLOWLISTED,
        INVALID_COMPONENT_VERSIONS,
        INVALID_ACTIVE_LEDGER_INPUT,
        INVALID_ACTIVE_LEDGER_REVISION,
        FAIL_CLOSED,
    )
)
_CHAT_DESTINATION = re.compile(r"^chat:(?:[1-9][0-9]*|-[1-9][0-9]*)$")


class ControlledTelegramProductionConfigurationError(ValueError):
    """Fixed local validation failure without submitted data."""


def _reject() -> None:
    raise ControlledTelegramProductionConfigurationError(FAIL_CLOSED)


def _strict_bool(value: object) -> bool:
    if type(value) is not bool:
        _reject()
    return value


def _nonblank_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        _reject()
    return value


def _versions(value: object) -> MappingProxyType:
    if not isinstance(value, Mapping) or not value:
        _reject()
    detached: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            _reject()
        if not isinstance(item, str) or not item.strip():
            _reject()
        detached[key] = item
    return MappingProxyType(dict(sorted(detached.items())))


def _canonical_destination(value: object) -> str:
    if not isinstance(value, str) or _CHAT_DESTINATION.fullmatch(value) is None:
        _reject()
    return value


def _metadata_is_structurally_valid(value: object) -> bool:
    if not isinstance(value, ControlledCredentialMetadataV1):
        return False
    return (
        value.credential_name == TELEGRAM_CREDENTIAL_NAME
        and value.source_kind in _SOURCE_KINDS
        and all(
            type(item) is bool
            for item in (
                value.required,
                value.available,
                value.readable,
                value.non_empty,
            )
        )
        and value.reason in _CLASSIFICATIONS
    )


def _metadata_is_available(value: ControlledCredentialMetadataV1) -> bool:
    return (
        value.required is True
        and value.available is True
        and value.readable is True
        and value.non_empty is True
    )


def _destination_failure(value: object) -> str | None:
    if not isinstance(value, ControlledTelegramDestinationV1):
        return INVALID_TELEGRAM_DESTINATION
    if value.channel != TELEGRAM_CHANNEL:
        return INVALID_TELEGRAM_CHANNEL
    try:
        _canonical_destination(value.destination_id)
    except Exception:
        return INVALID_TELEGRAM_DESTINATION
    if value.message_thread_id is not None:
        return INVALID_TELEGRAM_DESTINATION
    if type(value.enabled) is not bool or type(value.allowlisted) is not bool:
        return INVALID_TELEGRAM_DESTINATION
    return None


def _allowlist(value: object) -> frozenset[str] | None:
    if not isinstance(value, (tuple, list, frozenset)) or not value:
        return None
    detached: list[str] = []
    try:
        for item in value:
            detached.append(_canonical_destination(item))
    except Exception:
        return None
    if len(detached) != len(set(detached)):
        return None
    return frozenset(detached)


@dataclass(frozen=True, slots=True)
class ControlledCredentialMetadataV1:
    """Credential state only; no secret material or source location is retained."""

    credential_name: str
    source_kind: str
    required: bool
    available: bool
    readable: bool
    non_empty: bool
    reason: str

    def __post_init__(self) -> None:
        if self.credential_name != TELEGRAM_CREDENTIAL_NAME:
            _reject()
        if self.source_kind not in _SOURCE_KINDS:
            _reject()
        _strict_bool(self.required)
        _strict_bool(self.available)
        _strict_bool(self.readable)
        _strict_bool(self.non_empty)
        if self.reason not in _CLASSIFICATIONS:
            _reject()

    def to_dict(self) -> dict[str, object]:
        return {
            "credential_name": self.credential_name,
            "source_kind": self.source_kind,
            "required": self.required,
            "available": self.available,
            "readable": self.readable,
            "non_empty": self.non_empty,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ControlledTelegramDestinationV1:
    """One explicit chat destination for controlled composition."""

    channel: str
    destination_id: str
    message_thread_id: None
    enabled: bool
    allowlisted: bool
    reason: str

    def __post_init__(self) -> None:
        if self.channel != TELEGRAM_CHANNEL:
            _reject()
        _canonical_destination(self.destination_id)
        if self.message_thread_id is not None:
            _reject()
        _strict_bool(self.enabled)
        _strict_bool(self.allowlisted)
        if self.reason not in _CLASSIFICATIONS:
            _reject()

    def to_dict(self) -> dict[str, object]:
        return {
            "channel": self.channel,
            "destination_id": self.destination_id,
            "message_thread_id": self.message_thread_id,
            "enabled": self.enabled,
            "allowlisted": self.allowlisted,
            "reason": self.reason,
        }

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "channel": self.channel,
            "destination_kind": TELEGRAM_DESTINATION_KIND,
            "enabled": self.enabled,
            "allowlisted": self.allowlisted,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ControlledTelegramProductionConfigurationV1:
    """Detached caller-owned values for a later controlled composition."""

    credential: ControlledCredentialMetadataV1
    destination: ControlledTelegramDestinationV1
    component_versions: Mapping[str, str]
    active_ledger_path: str
    expected_active_ledger_revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.credential, ControlledCredentialMetadataV1):
            _reject()
        if not isinstance(self.destination, ControlledTelegramDestinationV1):
            _reject()
        object.__setattr__(self, "component_versions", _versions(self.component_versions))
        object.__setattr__(self, "active_ledger_path", _nonblank_text(self.active_ledger_path))
        if (
            type(self.expected_active_ledger_revision) is not int
            or self.expected_active_ledger_revision < 0
        ):
            _reject()

    def to_dict(self) -> dict[str, object]:
        return {
            "credential": self.credential.to_dict(),
            "destination": self.destination.to_dict(),
            "component_versions": dict(self.component_versions),
            "active_ledger_path": self.active_ledger_path,
            "expected_active_ledger_revision": self.expected_active_ledger_revision,
        }

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "credential": self.credential.to_dict(),
            "destination": self.destination.to_sanitized_dict(),
            "component_versions": dict(self.component_versions),
            "expected_active_ledger_revision": self.expected_active_ledger_revision,
        }


@dataclass(frozen=True, slots=True)
class ControlledTelegramProductionConfigurationResultV1:
    result: str
    credential_metadata_valid: bool
    credential_available: bool
    destination_valid: bool
    destination_allowlisted: bool
    component_versions_valid: bool
    active_ledger_input_valid: bool
    expected_revision_valid: bool
    ready: bool
    reason: str

    def __post_init__(self) -> None:
        if self.result not in _CLASSIFICATIONS or self.reason != self.result:
            _reject()
        for value in (
            self.credential_metadata_valid,
            self.credential_available,
            self.destination_valid,
            self.destination_allowlisted,
            self.component_versions_valid,
            self.active_ledger_input_valid,
            self.expected_revision_valid,
            self.ready,
        ):
            _strict_bool(value)

    def to_dict(self) -> dict[str, object]:
        return {
            "result": self.result,
            "credential_metadata_valid": self.credential_metadata_valid,
            "credential_available": self.credential_available,
            "destination_valid": self.destination_valid,
            "destination_allowlisted": self.destination_allowlisted,
            "component_versions_valid": self.component_versions_valid,
            "active_ledger_input_valid": self.active_ledger_input_valid,
            "expected_revision_valid": self.expected_revision_valid,
            "ready": self.ready,
            "reason": self.reason,
        }


def _result(
    classification: str,
    *,
    credential_metadata_valid: bool = False,
    credential_available: bool = False,
    destination_valid: bool = False,
    destination_allowlisted: bool = False,
    component_versions_valid: bool = False,
    active_ledger_input_valid: bool = False,
    expected_revision_valid: bool = False,
    ready: bool = False,
) -> ControlledTelegramProductionConfigurationResultV1:
    return ControlledTelegramProductionConfigurationResultV1(
        result=classification,
        credential_metadata_valid=credential_metadata_valid,
        credential_available=credential_available,
        destination_valid=destination_valid,
        destination_allowlisted=destination_allowlisted,
        component_versions_valid=component_versions_valid,
        active_ledger_input_valid=active_ledger_input_valid,
        expected_revision_valid=expected_revision_valid,
        ready=ready,
        reason=classification,
    )


def inspect_controlled_credential_metadata(
    *,
    credential_metadata: object,
) -> ControlledTelegramProductionConfigurationResultV1:
    """Validate metadata shape only; this operation has no external effects."""

    try:
        if not _metadata_is_structurally_valid(credential_metadata):
            return _result(INVALID_CREDENTIAL_METADATA)
        if not _metadata_is_available(credential_metadata):
            return _result(
                CREDENTIAL_METADATA_UNAVAILABLE,
                credential_metadata_valid=True,
            )
        return _result(
            CONTROLLED_CREDENTIAL_METADATA_VALID,
            credential_metadata_valid=True,
            credential_available=True,
        )
    except Exception:
        return _result(FAIL_CLOSED)


def validate_controlled_telegram_production_configuration(
    *,
    configuration: object,
    allowed_destination_ids: object,
    expected_component_versions: object,
) -> ControlledTelegramProductionConfigurationResultV1:
    """Apply deterministic, local readiness checks in their required order."""

    try:
        if not isinstance(configuration, ControlledTelegramProductionConfigurationV1):
            return _result(FAIL_CLOSED)

        metadata = configuration.credential
        if not _metadata_is_structurally_valid(metadata):
            return _result(INVALID_CREDENTIAL_METADATA)
        if not _metadata_is_available(metadata):
            return _result(
                CREDENTIAL_METADATA_UNAVAILABLE,
                credential_metadata_valid=True,
            )

        destination = configuration.destination
        destination_failure = _destination_failure(destination)
        if destination_failure is not None:
            return _result(
                destination_failure,
                credential_metadata_valid=True,
                credential_available=True,
            )
        if destination.enabled is not True:
            return _result(
                DESTINATION_DISABLED,
                credential_metadata_valid=True,
                credential_available=True,
                destination_valid=True,
            )
        allowlist = _allowlist(allowed_destination_ids)
        if allowlist is None or destination.destination_id not in allowlist:
            return _result(
                DESTINATION_NOT_ALLOWLISTED,
                credential_metadata_valid=True,
                credential_available=True,
                destination_valid=True,
            )

        try:
            expected_versions = _versions(expected_component_versions)
        except Exception:
            return _result(
                INVALID_COMPONENT_VERSIONS,
                credential_metadata_valid=True,
                credential_available=True,
                destination_valid=True,
                destination_allowlisted=True,
            )
        if dict(configuration.component_versions) != dict(expected_versions):
            return _result(
                INVALID_COMPONENT_VERSIONS,
                credential_metadata_valid=True,
                credential_available=True,
                destination_valid=True,
                destination_allowlisted=True,
            )

        if not isinstance(configuration.active_ledger_path, str) or not configuration.active_ledger_path.strip():
            return _result(
                INVALID_ACTIVE_LEDGER_INPUT,
                credential_metadata_valid=True,
                credential_available=True,
                destination_valid=True,
                destination_allowlisted=True,
                component_versions_valid=True,
            )
        if (
            type(configuration.expected_active_ledger_revision) is not int
            or configuration.expected_active_ledger_revision < 0
        ):
            return _result(
                INVALID_ACTIVE_LEDGER_REVISION,
                credential_metadata_valid=True,
                credential_available=True,
                destination_valid=True,
                destination_allowlisted=True,
                component_versions_valid=True,
                active_ledger_input_valid=True,
            )
        return _result(
            CONTROLLED_TELEGRAM_CONFIGURATION_VALID,
            credential_metadata_valid=True,
            credential_available=True,
            destination_valid=True,
            destination_allowlisted=True,
            component_versions_valid=True,
            active_ledger_input_valid=True,
            expected_revision_valid=True,
            ready=True,
        )
    except Exception:
        return _result(FAIL_CLOSED)
