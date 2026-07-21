"""Focused pure-contract tests for controlled Telegram configuration."""
from __future__ import annotations

from dataclasses import fields
import pytest

import engine.controlled_telegram_production_configuration_v1 as configuration_module
from engine.controlled_telegram_production_configuration_v1 import (
    CREDENTIAL_METADATA_UNAVAILABLE,
    CONTROLLED_CREDENTIAL_METADATA_VALID,
    CONTROLLED_TELEGRAM_CONFIGURATION_VALID,
    DESTINATION_DISABLED,
    DESTINATION_NOT_ALLOWLISTED,
    FAIL_CLOSED,
    INJECTED_SECRET_RESOLVER,
    INVALID_ACTIVE_LEDGER_INPUT,
    INVALID_COMPONENT_VERSIONS,
    INVALID_CREDENTIAL_METADATA,
    SYSTEMD_CREDENTIAL,
    TELEGRAM_CHANNEL,
    TELEGRAM_CREDENTIAL_NAME,
    ControlledCredentialMetadataV1,
    ControlledTelegramDestinationV1,
    ControlledTelegramProductionConfigurationResultV1,
    ControlledTelegramProductionConfigurationV1,
    inspect_controlled_credential_metadata,
    validate_controlled_telegram_production_configuration,
)


def _credential(**changes: object) -> ControlledCredentialMetadataV1:
    values: dict[str, object] = {
        "credential_name": TELEGRAM_CREDENTIAL_NAME,
        "source_kind": SYSTEMD_CREDENTIAL,
        "required": True,
        "available": True,
        "readable": True,
        "non_empty": True,
        "reason": CONTROLLED_CREDENTIAL_METADATA_VALID,
    }
    values.update(changes)
    return ControlledCredentialMetadataV1(**values)


def _destination(**changes: object) -> ControlledTelegramDestinationV1:
    values: dict[str, object] = {
        "channel": TELEGRAM_CHANNEL,
        "destination_id": "chat:-1001234567890",
        "message_thread_id": None,
        "enabled": True,
        "allowlisted": True,
        "reason": CONTROLLED_TELEGRAM_CONFIGURATION_VALID,
    }
    values.update(changes)
    return ControlledTelegramDestinationV1(**values)


def _configuration(**changes: object) -> ControlledTelegramProductionConfigurationV1:
    values: dict[str, object] = {
        "credential": _credential(),
        "destination": _destination(),
        "component_versions": {"adapter": "v1", "cycle": "v1"},
        "active_ledger_path": "controlled-active-ledger",
        "expected_active_ledger_revision": 0,
    }
    values.update(changes)
    return ControlledTelegramProductionConfigurationV1(**values)


def _valid_result() -> ControlledTelegramProductionConfigurationResultV1:
    return validate_controlled_telegram_production_configuration(
        configuration=_configuration(),
        allowed_destination_ids=("chat:-1001234567890",),
        expected_component_versions={"adapter": "v1", "cycle": "v1"},
    )


def test_dataclass_schemas_are_frozen_slotted_and_ordered() -> None:
    assert tuple(field.name for field in fields(ControlledCredentialMetadataV1)) == (
        "credential_name", "source_kind", "required", "available", "readable", "non_empty", "reason"
    )
    assert tuple(field.name for field in fields(ControlledTelegramDestinationV1)) == (
        "channel", "destination_id", "message_thread_id", "enabled", "allowlisted", "reason"
    )
    assert tuple(field.name for field in fields(ControlledTelegramProductionConfigurationV1)) == (
        "credential", "destination", "component_versions", "active_ledger_path", "expected_active_ledger_revision"
    )
    assert tuple(field.name for field in fields(ControlledTelegramProductionConfigurationResultV1)) == (
        "result", "credential_metadata_valid", "credential_available", "destination_valid", "destination_allowlisted", "component_versions_valid", "active_ledger_input_valid", "expected_revision_valid", "ready", "reason"
    )
    for value in (_credential(), _destination(), _configuration(), _valid_result()):
        assert hasattr(type(value), "__slots__")
        with pytest.raises((AttributeError, TypeError)):
            setattr(value, "reason", "changed")


def test_serialization_is_deterministic_detached_and_sanitized() -> None:
    configuration = _configuration()
    first = configuration.to_dict()
    second = configuration.to_dict()
    assert first == second
    first["component_versions"]["adapter"] = "changed"
    assert configuration.component_versions["adapter"] == "v1"
    sanitized = configuration.to_sanitized_dict()
    assert "destination_id" not in repr(sanitized)
    assert "message_thread_id" not in repr(sanitized)
    assert "active_ledger_path" not in sanitized
    assert _destination().to_sanitized_dict() == {
        "channel": TELEGRAM_CHANNEL,
        "destination_kind": "chat",
        "enabled": True,
        "allowlisted": True,
        "reason": CONTROLLED_TELEGRAM_CONFIGURATION_VALID,
    }


@pytest.mark.parametrize(
    ("changes", "classification"),
    (
        ({"available": False, "reason": CREDENTIAL_METADATA_UNAVAILABLE}, CREDENTIAL_METADATA_UNAVAILABLE),
        ({"readable": False, "reason": CREDENTIAL_METADATA_UNAVAILABLE}, CREDENTIAL_METADATA_UNAVAILABLE),
        ({"non_empty": False, "reason": CREDENTIAL_METADATA_UNAVAILABLE}, CREDENTIAL_METADATA_UNAVAILABLE),
    ),
)
def test_metadata_availability_is_pure_and_fail_closed(changes: dict[str, object], classification: str) -> None:
    result = inspect_controlled_credential_metadata(credential_metadata=_credential(**changes))
    assert result.result == classification
    assert result.credential_metadata_valid is True
    assert result.credential_available is False
    assert result.ready is False


@pytest.mark.parametrize("source_kind", (SYSTEMD_CREDENTIAL, INJECTED_SECRET_RESOLVER))
def test_only_allowed_metadata_sources_are_accepted(source_kind: str) -> None:
    assert _credential(source_kind=source_kind).source_kind == source_kind


@pytest.mark.parametrize(
    "changes",
    (
        {"credential_name": "deepseek_api_key"},
        {"credential_name": "anthropic_api_key"},
        {"credential_name": "TELEGRAM_BOT_TOKEN"},
        {"source_kind": "ENVIRONMENT"},
        {"required": 1},
        {"available": 1},
        {"readable": 1},
        {"non_empty": 1},
    ),
)
def test_invalid_metadata_values_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _credential(**changes)


@pytest.mark.parametrize("identifier", ("chat:123", "chat:-1001234567890"))
def test_canonical_chat_destinations_are_accepted(identifier: str) -> None:
    assert _destination(destination_id=identifier).destination_id == identifier


@pytest.mark.parametrize(
    "changes",
    (
        {"destination_id": "chat:0"},
        {"destination_id": "chat:+123"},
        {"destination_id": "chat:00123"},
        {"destination_id": "chat:-00123"},
        {"destination_id": "chat: 123"},
        {"destination_id": "@channelname"},
        {"destination_id": "group:123"},
        {"channel": "other"},
        {"message_thread_id": 1},
        {"enabled": 1},
        {"allowlisted": 1},
    ),
)
def test_noncanonical_destinations_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _destination(**changes)


def test_explicit_allowlist_is_authoritative() -> None:
    configuration = _configuration(destination=_destination(allowlisted=False))
    accepted = validate_controlled_telegram_production_configuration(
        configuration=configuration,
        allowed_destination_ids=("chat:-1001234567890",),
        expected_component_versions={"adapter": "v1", "cycle": "v1"},
    )
    denied = validate_controlled_telegram_production_configuration(
        configuration=_configuration(),
        allowed_destination_ids=("chat:123",),
        expected_component_versions={"adapter": "v1", "cycle": "v1"},
    )
    assert accepted.ready is True
    assert denied.result == DESTINATION_NOT_ALLOWLISTED
    assert denied.destination_valid is True
    assert denied.destination_allowlisted is False


@pytest.mark.parametrize(
    ("configuration", "expected", "classification"),
    (
        (_configuration(destination=_destination(enabled=False, reason=DESTINATION_DISABLED)), {"adapter": "v1", "cycle": "v1"}, DESTINATION_DISABLED),
        (_configuration(), {"adapter": "v1"}, INVALID_COMPONENT_VERSIONS),
        (_configuration(), {"adapter": "v1", "cycle": "changed"}, INVALID_COMPONENT_VERSIONS),
        (_configuration(), {}, INVALID_COMPONENT_VERSIONS),
    ),
)
def test_first_failure_after_metadata_is_deterministic(
    configuration: ControlledTelegramProductionConfigurationV1,
    expected: dict[str, str],
    classification: str,
) -> None:
    result = validate_controlled_telegram_production_configuration(
        configuration=configuration,
        allowed_destination_ids=("chat:-1001234567890",),
        expected_component_versions=expected,
    )
    assert result.result == classification
    assert result.ready is False
    assert result.reason == classification


def test_valid_configuration_has_all_readiness_booleans() -> None:
    result = _valid_result()
    assert result.to_dict() == {
        "result": CONTROLLED_TELEGRAM_CONFIGURATION_VALID,
        "credential_metadata_valid": True,
        "credential_available": True,
        "destination_valid": True,
        "destination_allowlisted": True,
        "component_versions_valid": True,
        "active_ledger_input_valid": True,
        "expected_revision_valid": True,
        "ready": True,
        "reason": CONTROLLED_TELEGRAM_CONFIGURATION_VALID,
    }


def test_component_inputs_are_detached_and_ledger_input_is_opaque() -> None:
    components = {"adapter": "v1", "cycle": "v1"}
    configuration = _configuration(component_versions=components, active_ledger_path="opaque-ledger")
    components["adapter"] = "changed"
    assert configuration.component_versions["adapter"] == "v1"
    assert "opaque-ledger" not in repr(_valid_result())
    with pytest.raises(ValueError):
        _configuration(active_ledger_path="   ")
    with pytest.raises(ValueError):
        _configuration(active_ledger_path=object())
    assert _configuration(expected_active_ledger_revision=7).expected_active_ledger_revision == 7
    with pytest.raises(ValueError):
        _configuration(expected_active_ledger_revision=True)
    with pytest.raises(ValueError):
        _configuration(expected_active_ledger_revision=-1)


def test_invalid_public_inputs_fail_closed_without_disclosure() -> None:
    metadata = inspect_controlled_credential_metadata(credential_metadata=object())
    configuration = validate_controlled_telegram_production_configuration(
        configuration=object(),
        allowed_destination_ids=("chat:-1001234567890",),
        expected_component_versions={"adapter": "v1"},
    )
    assert metadata.result == INVALID_CREDENTIAL_METADATA
    assert configuration.result == FAIL_CLOSED
    for result in (metadata, configuration, _valid_result()):
        rendered = repr(result.to_dict())
        assert "chat:-1001234567890" not in rendered
        assert "opaque-ledger" not in rendered


def test_module_remains_pure_and_gate_neutral() -> None:
    forbidden = (
        "requests", "socket", "subprocess", "send_message", "scan_market",
        "run_master_engine", "run_production_signal_service_v1",
    )
    assert not any(item in configuration_module.__dict__ for item in forbidden)
