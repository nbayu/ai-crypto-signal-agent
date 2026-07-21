"""Focused fake-only tests for the bounded Telegram identity confirmation."""
from __future__ import annotations

from dataclasses import fields
from datetime import datetime

import pytest

from engine.controlled_telegram_production_configuration_v1 import (
    CONTROLLED_CREDENTIAL_METADATA_VALID,
    CREDENTIAL_METADATA_UNAVAILABLE,
    SYSTEMD_CREDENTIAL,
    TELEGRAM_CREDENTIAL_NAME,
    ControlledCredentialMetadataV1,
)
from engine.controlled_telegram_identity_probe_v1 import (
    ACTIVATION_GATE_CLOSED,
    CREDENTIAL_GATE_CLOSED,
    CREDENTIAL_METADATA_UNAVAILABLE as PROBE_CREDENTIAL_METADATA_UNAVAILABLE,
    CREDENTIAL_RESOLUTION_FAILED,
    CREDENTIAL_VALUE_INVALID,
    FAIL_CLOSED,
    INVALID_PROBE_TIMESTAMP,
    INVALID_TELEGRAM_CONFIGURATION,
    NETWORK_GATE_CLOSED,
    TELEGRAM_IDENTITY_CONFIRMED,
    TELEGRAM_IDENTITY_PROBE_FAILED,
    WORKLOAD_GATE_CLOSED,
    ControlledTelegramIdentityProbeAuthorizationV1,
    ControlledTelegramIdentityProbeResultV1,
    run_controlled_telegram_identity_probe,
)


_TIMESTAMP = "2026-07-22T00:00:00Z"
_TOKEN = "opaque-test-value"


def _authorization(**changes: object) -> ControlledTelegramIdentityProbeAuthorizationV1:
    values: dict[str, object] = {
        "activation_authorized": True,
        "workload_authorized": True,
        "credential_authorized": True,
        "network_authorized": True,
    }
    values.update(changes)
    return ControlledTelegramIdentityProbeAuthorizationV1(**values)


def _metadata(**changes: object) -> ControlledCredentialMetadataV1:
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


def _run(**changes: object) -> ControlledTelegramIdentityProbeResultV1:
    values: dict[str, object] = {
        "authorization": _authorization(),
        "credential_metadata": _metadata(),
        "credential_resolver": lambda **_: _TOKEN,
        "telegram_identity_probe": lambda **_: True,
        "probed_at": _TIMESTAMP,
    }
    values.update(changes)
    return run_controlled_telegram_identity_probe(**values)


def test_public_dataclass_schemas_are_frozen_slotted_and_deterministic() -> None:
    assert tuple(field.name for field in fields(ControlledTelegramIdentityProbeAuthorizationV1)) == (
        "activation_authorized", "workload_authorized", "credential_authorized", "network_authorized"
    )
    assert tuple(field.name for field in fields(ControlledTelegramIdentityProbeResultV1)) == (
        "result", "gate", "configuration_valid", "credential_metadata_valid",
        "credential_resolution_attempted", "credential_resolved", "network_probe_attempted",
        "bot_identity_confirmed", "probe_timestamp", "reason",
    )
    closed = ControlledTelegramIdentityProbeAuthorizationV1()
    assert closed.to_dict() == {
        "activation_authorized": False,
        "workload_authorized": False,
        "credential_authorized": False,
        "network_authorized": False,
    }
    with pytest.raises((AttributeError, TypeError)):
        closed.network_authorized = True  # type: ignore[misc]
    result = _run()
    assert result.to_dict() == result.to_dict()
    with pytest.raises((AttributeError, TypeError)):
        result.reason = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("changes", "classification"),
    (
        ({"activation_authorized": False}, ACTIVATION_GATE_CLOSED),
        ({"workload_authorized": False}, WORKLOAD_GATE_CLOSED),
        ({"credential_authorized": False}, CREDENTIAL_GATE_CLOSED),
        ({"network_authorized": False}, NETWORK_GATE_CLOSED),
    ),
)
def test_closed_gates_win_in_order_and_call_no_dependencies(
    changes: dict[str, object], classification: str
) -> None:
    calls: list[str] = []
    result = _run(
        authorization=_authorization(**changes),
        credential_resolver=lambda **_: calls.append("resolver"),
        telegram_identity_probe=lambda **_: calls.append("probe"),
        probed_at=object(),
        credential_metadata=object(),
    )
    assert result.result == classification
    assert result.gate == classification
    assert calls == []
    assert result.to_dict() == {
        "result": classification,
        "gate": classification,
        "configuration_valid": False,
        "credential_metadata_valid": False,
        "credential_resolution_attempted": False,
        "credential_resolved": False,
        "network_probe_attempted": False,
        "bot_identity_confirmed": False,
        "probe_timestamp": "",
        "reason": classification,
    }


@pytest.mark.parametrize(
    "value",
    (
        "2026-07-22T00:00:00", "2026-02-30T00:00:00Z", "2026-07-22T00:00:00+00:00",
        "2026-07-22T00:00:00z", " 2026-07-22T00:00:00Z", datetime(2026, 7, 22),
    ),
)
def test_timestamp_is_caller_owned_and_checked_after_gates(value: object) -> None:
    calls: list[str] = []
    result = _run(
        probed_at=value,
        credential_resolver=lambda **_: calls.append("resolver"),
        telegram_identity_probe=lambda **_: calls.append("probe"),
    )
    assert result.result == INVALID_PROBE_TIMESTAMP
    assert result.probe_timestamp == ""
    assert calls == []
    assert _run(probed_at="2026-07-22T00:00:00.123Z").probe_timestamp == "2026-07-22T00:00:00.123Z"


@pytest.mark.parametrize(
    "field",
    ("credential_name", "source_kind", "required", "available", "readable", "non_empty"),
)
def test_malformed_metadata_fails_before_resolution(field: str) -> None:
    metadata = _metadata()
    object.__setattr__(metadata, field, "wrong" if field in {"credential_name", "source_kind"} else 1)
    calls: list[str] = []
    result = _run(
        credential_metadata=metadata,
        credential_resolver=lambda **_: calls.append("resolver"),
    )
    assert result.result == INVALID_TELEGRAM_CONFIGURATION
    assert calls == []


@pytest.mark.parametrize("field", ("available", "readable", "non_empty"))
def test_unavailable_metadata_is_sanitized(field: str) -> None:
    metadata = _metadata(reason=CREDENTIAL_METADATA_UNAVAILABLE)
    object.__setattr__(metadata, field, False)
    result = _run(credential_metadata=metadata)
    assert result.result == PROBE_CREDENTIAL_METADATA_UNAVAILABLE
    assert result.configuration_valid is True
    assert result.credential_metadata_valid is True
    assert result.credential_resolution_attempted is False


def test_resolver_receives_only_logical_credential_metadata() -> None:
    received: dict[str, object] = {}

    def resolver(**kwargs: object) -> str:
        received.update(kwargs)
        return _TOKEN

    result = _run(credential_resolver=resolver)
    assert result.result == TELEGRAM_IDENTITY_CONFIRMED
    assert received == {
        "credential_name": TELEGRAM_CREDENTIAL_NAME,
        "source_kind": SYSTEMD_CREDENTIAL,
    }


@pytest.mark.parametrize("value", (None, "", "   ", b"x", {"value": _TOKEN}, 1, True))
def test_invalid_resolver_values_never_reach_probe(value: object) -> None:
    calls: list[str] = []
    result = _run(
        credential_resolver=lambda **_: value,
        telegram_identity_probe=lambda **_: calls.append("probe"),
    )
    assert result.result == CREDENTIAL_VALUE_INVALID
    assert result.credential_resolution_attempted is True
    assert result.credential_resolved is False
    assert calls == []


def test_resolver_failure_is_single_attempt_and_redacted() -> None:
    calls: list[str] = []

    def resolver(**_: object) -> str:
        calls.append("resolver")
        raise RuntimeError(_TOKEN)

    result = _run(credential_resolver=resolver)
    assert result.result == CREDENTIAL_RESOLUTION_FAILED
    assert calls == ["resolver"]
    assert _TOKEN not in repr(result) + repr(result.to_dict())


@pytest.mark.parametrize("outcome", (False, None, "yes", 1, {"ok": True}))
def test_only_explicit_true_confirms_identity(outcome: object) -> None:
    calls: list[dict[str, object]] = []

    def probe(**kwargs: object) -> object:
        calls.append(kwargs)
        return outcome

    result = _run(telegram_identity_probe=probe)
    assert result.result == TELEGRAM_IDENTITY_PROBE_FAILED
    assert calls == [{"token": _TOKEN}]
    assert result.network_probe_attempted is True
    assert result.bot_identity_confirmed is False


def test_probe_exception_is_single_attempt_and_sanitized() -> None:
    calls: list[str] = []

    def probe(**_: object) -> bool:
        calls.append("probe")
        raise RuntimeError(_TOKEN)

    result = _run(telegram_identity_probe=probe)
    assert result.result == TELEGRAM_IDENTITY_PROBE_FAILED
    assert calls == ["probe"]
    assert _TOKEN not in repr(result) + repr(result.to_dict())


def test_success_retains_only_status_and_caller_timestamp() -> None:
    metadata = _metadata()
    authorization = _authorization()
    result = _run(credential_metadata=metadata, authorization=authorization)
    assert result.to_dict() == {
        "result": TELEGRAM_IDENTITY_CONFIRMED,
        "gate": "",
        "configuration_valid": True,
        "credential_metadata_valid": True,
        "credential_resolution_attempted": True,
        "credential_resolved": True,
        "network_probe_attempted": True,
        "bot_identity_confirmed": True,
        "probe_timestamp": _TIMESTAMP,
        "reason": TELEGRAM_IDENTITY_CONFIRMED,
    }
    assert _TOKEN not in repr(result) + repr(result.to_dict())
    assert metadata == _metadata()
    assert authorization == _authorization()


def test_invalid_authorization_and_noncallable_dependencies_fail_closed() -> None:
    invalid = _run(authorization=object())
    resolver = _run(credential_resolver=object())
    probe = _run(telegram_identity_probe=object())
    assert (invalid.result, invalid.gate) == (FAIL_CLOSED, FAIL_CLOSED)
    assert resolver.result == CREDENTIAL_RESOLUTION_FAILED
    assert resolver.credential_resolution_attempted is False
    assert probe.result == TELEGRAM_IDENTITY_PROBE_FAILED
    assert probe.network_probe_attempted is False


def test_module_surface_stays_bounded_and_sdk_free() -> None:
    forbidden = {
        "requests", "socket", "subprocess", "send_message", "get_chat",
        "run_production_signal_service_v1", "register_completed_publication",
        "run_master_engine_v4", "initialize_ledger",
    }
    import engine.controlled_telegram_identity_probe_v1 as module

    assert not forbidden.intersection(module.__dict__)
