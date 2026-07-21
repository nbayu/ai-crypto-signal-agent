"""Bounded, injected Telegram identity confirmation with no retained secret material."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from engine.controlled_telegram_production_configuration_v1 import (
    INJECTED_SECRET_RESOLVER,
    SYSTEMD_CREDENTIAL,
    TELEGRAM_CREDENTIAL_NAME as _CONFIGURATION_CREDENTIAL_NAME,
    ControlledCredentialMetadataV1,
)


TELEGRAM_CREDENTIAL_NAME = "telegram_bot_token"

ACTIVATION_GATE_CLOSED = "ACTIVATION_GATE_CLOSED"
WORKLOAD_GATE_CLOSED = "WORKLOAD_GATE_CLOSED"
CREDENTIAL_GATE_CLOSED = "CREDENTIAL_GATE_CLOSED"
NETWORK_GATE_CLOSED = "NETWORK_GATE_CLOSED"
INVALID_TELEGRAM_CONFIGURATION = "INVALID_TELEGRAM_CONFIGURATION"
INVALID_PROBE_TIMESTAMP = "INVALID_PROBE_TIMESTAMP"
CREDENTIAL_METADATA_UNAVAILABLE = "CREDENTIAL_METADATA_UNAVAILABLE"
CREDENTIAL_RESOLUTION_FAILED = "CREDENTIAL_RESOLUTION_FAILED"
CREDENTIAL_VALUE_INVALID = "CREDENTIAL_VALUE_INVALID"
TELEGRAM_IDENTITY_PROBE_FAILED = "TELEGRAM_IDENTITY_PROBE_FAILED"
TELEGRAM_IDENTITY_CONFIRMED = "TELEGRAM_IDENTITY_CONFIRMED"
FAIL_CLOSED = "FAIL_CLOSED"

_CLASSIFICATIONS = frozenset(
    (
        ACTIVATION_GATE_CLOSED,
        WORKLOAD_GATE_CLOSED,
        CREDENTIAL_GATE_CLOSED,
        NETWORK_GATE_CLOSED,
        INVALID_TELEGRAM_CONFIGURATION,
        INVALID_PROBE_TIMESTAMP,
        CREDENTIAL_METADATA_UNAVAILABLE,
        CREDENTIAL_RESOLUTION_FAILED,
        CREDENTIAL_VALUE_INVALID,
        TELEGRAM_IDENTITY_PROBE_FAILED,
        TELEGRAM_IDENTITY_CONFIRMED,
        FAIL_CLOSED,
    )
)
_SOURCE_KINDS = frozenset((SYSTEMD_CREDENTIAL, INJECTED_SECRET_RESOLVER))
_UTC_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
_GATES = (
    ("activation_authorized", ACTIVATION_GATE_CLOSED),
    ("workload_authorized", WORKLOAD_GATE_CLOSED),
    ("credential_authorized", CREDENTIAL_GATE_CLOSED),
    ("network_authorized", NETWORK_GATE_CLOSED),
)


class ControlledTelegramIdentityProbeError(ValueError):
    """Fixed local validation failure without caller data."""


def _reject() -> None:
    raise ControlledTelegramIdentityProbeError(FAIL_CLOSED)


def _strict_bool(value: object) -> bool:
    if type(value) is not bool:
        _reject()
    return value


@dataclass(frozen=True, slots=True)
class ControlledTelegramIdentityProbeAuthorizationV1:
    """Explicit, closed-by-default authority for one identity confirmation."""

    activation_authorized: bool = False
    workload_authorized: bool = False
    credential_authorized: bool = False
    network_authorized: bool = False

    def __post_init__(self) -> None:
        _strict_bool(self.activation_authorized)
        _strict_bool(self.workload_authorized)
        _strict_bool(self.credential_authorized)
        _strict_bool(self.network_authorized)

    def to_dict(self) -> dict[str, bool]:
        return {
            "activation_authorized": self.activation_authorized,
            "workload_authorized": self.workload_authorized,
            "credential_authorized": self.credential_authorized,
            "network_authorized": self.network_authorized,
        }


@dataclass(frozen=True, slots=True)
class ControlledTelegramIdentityProbeResultV1:
    result: str
    gate: str
    configuration_valid: bool
    credential_metadata_valid: bool
    credential_resolution_attempted: bool
    credential_resolved: bool
    network_probe_attempted: bool
    bot_identity_confirmed: bool
    probe_timestamp: str
    reason: str

    def __post_init__(self) -> None:
        if self.result not in _CLASSIFICATIONS or self.reason != self.result:
            _reject()
        if self.gate not in _CLASSIFICATIONS and self.gate != "":
            _reject()
        for value in (
            self.configuration_valid,
            self.credential_metadata_valid,
            self.credential_resolution_attempted,
            self.credential_resolved,
            self.network_probe_attempted,
            self.bot_identity_confirmed,
        ):
            _strict_bool(value)
        if not isinstance(self.probe_timestamp, str):
            _reject()

    def to_dict(self) -> dict[str, object]:
        return {
            "result": self.result,
            "gate": self.gate,
            "configuration_valid": self.configuration_valid,
            "credential_metadata_valid": self.credential_metadata_valid,
            "credential_resolution_attempted": self.credential_resolution_attempted,
            "credential_resolved": self.credential_resolved,
            "network_probe_attempted": self.network_probe_attempted,
            "bot_identity_confirmed": self.bot_identity_confirmed,
            "probe_timestamp": self.probe_timestamp,
            "reason": self.reason,
        }


def _result(
    classification: str,
    *,
    gate: str = "",
    configuration_valid: bool = False,
    credential_metadata_valid: bool = False,
    credential_resolution_attempted: bool = False,
    credential_resolved: bool = False,
    network_probe_attempted: bool = False,
    bot_identity_confirmed: bool = False,
    probe_timestamp: str = "",
) -> ControlledTelegramIdentityProbeResultV1:
    return ControlledTelegramIdentityProbeResultV1(
        result=classification,
        gate=gate,
        configuration_valid=configuration_valid,
        credential_metadata_valid=credential_metadata_valid,
        credential_resolution_attempted=credential_resolution_attempted,
        credential_resolved=credential_resolved,
        network_probe_attempted=network_probe_attempted,
        bot_identity_confirmed=bot_identity_confirmed,
        probe_timestamp=probe_timestamp,
        reason=classification,
    )


def _authorization(value: object) -> ControlledTelegramIdentityProbeAuthorizationV1:
    if not isinstance(value, ControlledTelegramIdentityProbeAuthorizationV1):
        _reject()
    for field, _ in _GATES:
        _strict_bool(getattr(value, field))
    return value


def _closed_gate(
    authorization: ControlledTelegramIdentityProbeAuthorizationV1,
) -> str | None:
    for field, classification in _GATES:
        if getattr(authorization, field) is not True:
            return classification
    return None


def _timestamp(value: object) -> str | None:
    if not isinstance(value, str) or _UTC_TIMESTAMP.fullmatch(value) is None:
        return None
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    return value


def _metadata_status(value: object) -> str:
    if not isinstance(value, ControlledCredentialMetadataV1):
        return INVALID_TELEGRAM_CONFIGURATION
    if (
        value.credential_name != TELEGRAM_CREDENTIAL_NAME
        or _CONFIGURATION_CREDENTIAL_NAME != TELEGRAM_CREDENTIAL_NAME
        or value.source_kind not in _SOURCE_KINDS
        or any(
            type(item) is not bool
            for item in (
                value.required,
                value.available,
                value.readable,
                value.non_empty,
            )
        )
    ):
        return INVALID_TELEGRAM_CONFIGURATION
    if not all(
        (
            value.required is True,
            value.available is True,
            value.readable is True,
            value.non_empty is True,
        )
    ):
        return CREDENTIAL_METADATA_UNAVAILABLE
    return TELEGRAM_IDENTITY_CONFIRMED


def run_controlled_telegram_identity_probe(
    *,
    authorization: object,
    credential_metadata: object,
    credential_resolver: object,
    telegram_identity_probe: object,
    probed_at: object,
) -> ControlledTelegramIdentityProbeResultV1:
    """Run one authorized, metadata-bound identity confirmation."""

    try:
        approved = _authorization(authorization)
    except Exception:
        return _result(FAIL_CLOSED, gate=FAIL_CLOSED)

    closed = _closed_gate(approved)
    if closed is not None:
        return _result(closed, gate=closed)

    timestamp = _timestamp(probed_at)
    if timestamp is None:
        return _result(INVALID_PROBE_TIMESTAMP)

    metadata_status = _metadata_status(credential_metadata)
    if metadata_status == INVALID_TELEGRAM_CONFIGURATION:
        return _result(INVALID_TELEGRAM_CONFIGURATION)
    if metadata_status == CREDENTIAL_METADATA_UNAVAILABLE:
        return _result(
            CREDENTIAL_METADATA_UNAVAILABLE,
            configuration_valid=True,
            credential_metadata_valid=True,
        )

    if not callable(credential_resolver):
        return _result(
            CREDENTIAL_RESOLUTION_FAILED,
            configuration_valid=True,
            credential_metadata_valid=True,
        )
    try:
        resolved_token = credential_resolver(
            credential_name=TELEGRAM_CREDENTIAL_NAME,
            source_kind=credential_metadata.source_kind,
        )
    except Exception:
        return _result(
            CREDENTIAL_RESOLUTION_FAILED,
            configuration_valid=True,
            credential_metadata_valid=True,
            credential_resolution_attempted=True,
        )

    if not isinstance(resolved_token, str) or not resolved_token.strip():
        return _result(
            CREDENTIAL_VALUE_INVALID,
            configuration_valid=True,
            credential_metadata_valid=True,
            credential_resolution_attempted=True,
        )

    if not callable(telegram_identity_probe):
        return _result(
            TELEGRAM_IDENTITY_PROBE_FAILED,
            configuration_valid=True,
            credential_metadata_valid=True,
            credential_resolution_attempted=True,
            credential_resolved=True,
        )
    try:
        confirmed = telegram_identity_probe(token=resolved_token)
    except Exception:
        return _result(
            TELEGRAM_IDENTITY_PROBE_FAILED,
            configuration_valid=True,
            credential_metadata_valid=True,
            credential_resolution_attempted=True,
            credential_resolved=True,
            network_probe_attempted=True,
        )

    if confirmed is not True:
        return _result(
            TELEGRAM_IDENTITY_PROBE_FAILED,
            configuration_valid=True,
            credential_metadata_valid=True,
            credential_resolution_attempted=True,
            credential_resolved=True,
            network_probe_attempted=True,
        )
    return _result(
        TELEGRAM_IDENTITY_CONFIRMED,
        configuration_valid=True,
        credential_metadata_valid=True,
        credential_resolution_attempted=True,
        credential_resolved=True,
        network_probe_attempted=True,
        bot_identity_confirmed=True,
        probe_timestamp=timestamp,
    )
