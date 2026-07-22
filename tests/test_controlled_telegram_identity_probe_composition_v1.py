"""Focused fake-only tests for controlled Telegram identity probe composition."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
import inspect

import pytest

import engine.controlled_telegram_identity_probe_composition_v1 as module
from engine.bounded_telegram_sdk_identity_adapter_v1 import (
    BoundedTelegramSdkIdentityProbeV1,
)
from engine.controlled_telegram_identity_probe_composition_v1 import (
    ControlledTelegramIdentityProbeCompositionV1,
)
from engine.controlled_telegram_identity_probe_v1 import (
    ACTIVATION_GATE_CLOSED,
    CREDENTIAL_GATE_CLOSED,
    CREDENTIAL_RESOLUTION_FAILED,
    CREDENTIAL_VALUE_INVALID,
    NETWORK_GATE_CLOSED,
    TELEGRAM_IDENTITY_CONFIRMED,
    TELEGRAM_IDENTITY_PROBE_FAILED,
    WORKLOAD_GATE_CLOSED,
    ControlledTelegramIdentityProbeAuthorizationV1,
)
from engine.controlled_telegram_production_configuration_v1 import (
    CONTROLLED_CREDENTIAL_METADATA_VALID,
    SYSTEMD_CREDENTIAL,
    TELEGRAM_CREDENTIAL_NAME,
    ControlledCredentialMetadataV1,
)


_TIMESTAMP = "2026-07-22T00:00:00Z"
_TOKEN = "opaque-fake-token"


def _authorization(**changes: object) -> ControlledTelegramIdentityProbeAuthorizationV1:
    values: dict[str, object] = {
        "activation_authorized": True,
        "workload_authorized": True,
        "credential_authorized": True,
        "network_authorized": True,
    }
    values.update(changes)
    return ControlledTelegramIdentityProbeAuthorizationV1(**values)


def _metadata() -> ControlledCredentialMetadataV1:
    return ControlledCredentialMetadataV1(
        credential_name=TELEGRAM_CREDENTIAL_NAME,
        source_kind=SYSTEMD_CREDENTIAL,
        required=True,
        available=True,
        readable=True,
        non_empty=True,
        reason=CONTROLLED_CREDENTIAL_METADATA_VALID,
    )


def test_composition_type_is_frozen_slotted_dataclass_with_one_private_field() -> None:
    composition = ControlledTelegramIdentityProbeCompositionV1()
    adapter_field, = fields(ControlledTelegramIdentityProbeCompositionV1)
    assert is_dataclass(ControlledTelegramIdentityProbeCompositionV1)
    assert not hasattr(composition, "__dict__")
    assert tuple(field.name for field in fields(ControlledTelegramIdentityProbeCompositionV1)) == (
        "_adapter",
    )
    assert not [field.name for field in fields(ControlledTelegramIdentityProbeCompositionV1) if not field.name.startswith("_")]
    assert adapter_field.repr is False
    with pytest.raises((AttributeError, TypeError)):
        composition._adapter = object()  # type: ignore[misc]


def test_default_adapter_is_bounded_and_not_exposed_in_repr() -> None:
    composition = ControlledTelegramIdentityProbeCompositionV1()
    assert isinstance(composition._adapter, BoundedTelegramSdkIdentityProbeV1)
    assert "_adapter" not in repr(composition)
    assert _TOKEN not in repr(composition)


def test_callable_signature_is_exact_and_keyword_only() -> None:
    signature = inspect.signature(ControlledTelegramIdentityProbeCompositionV1.__call__)
    assert tuple(signature.parameters) == (
        "self",
        "authorization",
        "credential_metadata",
        "credential_resolver",
        "probed_at",
    )
    assert tuple(parameter.kind for parameter in signature.parameters.values()) == (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
    )


def test_callable_has_no_forbidden_inputs() -> None:
    names = set(inspect.signature(ControlledTelegramIdentityProbeCompositionV1.__call__).parameters)
    forbidden = {
        "token", "telegram_identity_probe", "adapter", "adapter_factory", "destination",
        "destination_id", "channel", "allowlist", "message_thread_id", "component_versions",
        "active_ledger_path", "expected_active_ledger_revision", "candidate", "publication",
        "runtime", "launcher", "service", "systemd", "timeout_seconds",
    }
    assert not names.intersection(forbidden)


def test_composition_forwards_exact_objects_once_without_calling_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}
    result = object()
    authorization = object()
    metadata = object()
    resolver = object()
    timestamp = object()
    adapter_calls: list[object] = []

    def adapter(**_: object) -> bool:
        adapter_calls.append(object())
        return True

    def executor(**kwargs: object) -> object:
        received.update(kwargs)
        return result

    monkeypatch.setattr(module, "run_controlled_telegram_identity_probe", executor)
    composition = ControlledTelegramIdentityProbeCompositionV1(_adapter=adapter)
    returned = composition(
        authorization=authorization,
        credential_metadata=metadata,
        credential_resolver=resolver,
        probed_at=timestamp,
    )
    assert returned is result
    assert received == {
        "authorization": authorization,
        "credential_metadata": metadata,
        "credential_resolver": resolver,
        "telegram_identity_probe": adapter,
        "probed_at": timestamp,
    }
    assert adapter_calls == []


def test_executor_exception_is_not_caught_or_stringified(monkeypatch: pytest.MonkeyPatch) -> None:
    error = RuntimeError(_TOKEN)

    def executor(**_: object) -> object:
        raise error

    monkeypatch.setattr(module, "run_controlled_telegram_identity_probe", executor)
    with pytest.raises(RuntimeError) as caught:
        ControlledTelegramIdentityProbeCompositionV1()(
            authorization=object(),
            credential_metadata=object(),
            credential_resolver=object(),
            probed_at=object(),
        )
    assert caught.value is error


def test_opaque_authorization_and_metadata_are_not_inspected(monkeypatch: pytest.MonkeyPatch) -> None:
    result = object()

    class Opaque:
        def __getattribute__(self, name: str) -> object:
            raise AssertionError(f"unexpected composition inspection: {name}")

    monkeypatch.setattr(module, "run_controlled_telegram_identity_probe", lambda **_: result)
    returned = ControlledTelegramIdentityProbeCompositionV1()(
        authorization=Opaque(),
        credential_metadata=Opaque(),
        credential_resolver=object(),
        probed_at=object(),
    )
    assert returned is result


def test_custom_adapter_is_forwarded_without_fallback_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[object] = []
    adapter = object()

    def executor(**kwargs: object) -> object:
        received.append(kwargs["telegram_identity_probe"])
        return object()

    monkeypatch.setattr(module, "run_controlled_telegram_identity_probe", executor)
    ControlledTelegramIdentityProbeCompositionV1(_adapter=adapter)(
        authorization=object(),
        credential_metadata=object(),
        credential_resolver=object(),
        probed_at=object(),
    )
    assert received == [adapter]


def test_executor_call_count_is_one_per_composition_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def executor(**kwargs: object) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(module, "run_controlled_telegram_identity_probe", executor)
    ControlledTelegramIdentityProbeCompositionV1()(
        authorization=object(),
        credential_metadata=object(),
        credential_resolver=object(),
        probed_at=object(),
    )
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("changes", "classification"),
    (
        ({"activation_authorized": False}, ACTIVATION_GATE_CLOSED),
        ({"workload_authorized": False}, WORKLOAD_GATE_CLOSED),
        ({"credential_authorized": False}, CREDENTIAL_GATE_CLOSED),
        ({"network_authorized": False}, NETWORK_GATE_CLOSED),
    ),
)
def test_closed_gates_remain_executor_owned_and_do_not_call_dependencies(
    changes: dict[str, object], classification: str
) -> None:
    resolver_calls: list[dict[str, object]] = []
    adapter_calls: list[dict[str, object]] = []

    def resolver(**kwargs: object) -> str:
        resolver_calls.append(kwargs)
        return _TOKEN

    def adapter(**kwargs: object) -> bool:
        adapter_calls.append(kwargs)
        return True

    result = ControlledTelegramIdentityProbeCompositionV1(_adapter=adapter)(
        authorization=_authorization(**changes),
        credential_metadata=_metadata(),
        credential_resolver=resolver,
        probed_at=_TIMESTAMP,
    )
    assert (result.result, result.gate) == (classification, classification)
    assert resolver_calls == []
    assert adapter_calls == []


@pytest.mark.parametrize(
    ("resolver_outcome", "adapter_outcome", "classification"),
    (
        (RuntimeError(_TOKEN), True, CREDENTIAL_RESOLUTION_FAILED),
        ("", True, CREDENTIAL_VALUE_INVALID),
        (_TOKEN, RuntimeError(_TOKEN), TELEGRAM_IDENTITY_PROBE_FAILED),
        (_TOKEN, True, TELEGRAM_IDENTITY_CONFIRMED),
    ),
)
def test_executor_classifications_and_single_dependency_calls_are_preserved(
    resolver_outcome: object, adapter_outcome: object, classification: str
) -> None:
    resolver_calls: list[dict[str, object]] = []
    adapter_calls: list[dict[str, object]] = []

    def resolver(**kwargs: object) -> object:
        resolver_calls.append(kwargs)
        if isinstance(resolver_outcome, BaseException):
            raise resolver_outcome
        return resolver_outcome

    def adapter(**kwargs: object) -> bool:
        adapter_calls.append(kwargs)
        if isinstance(adapter_outcome, BaseException):
            raise adapter_outcome
        return adapter_outcome is True

    composition = ControlledTelegramIdentityProbeCompositionV1(_adapter=adapter)
    result = composition(
        authorization=_authorization(),
        credential_metadata=_metadata(),
        credential_resolver=resolver,
        probed_at=_TIMESTAMP,
    )
    assert result.result == classification
    assert len(resolver_calls) == 1
    assert len(adapter_calls) == (1 if resolver_outcome == _TOKEN else 0)
    assert result.probe_timestamp == (_TIMESTAMP if classification == TELEGRAM_IDENTITY_CONFIRMED else "")
    assert _TOKEN not in repr(composition) + repr(result) + repr(fields(composition))


def test_caller_timestamp_is_forwarded_without_generation_or_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamp = object()
    received: list[object] = []

    def executor(**kwargs: object) -> object:
        received.append(kwargs["probed_at"])
        return object()

    monkeypatch.setattr(module, "run_controlled_telegram_identity_probe", executor)
    ControlledTelegramIdentityProbeCompositionV1()(
        authorization=object(),
        credential_metadata=object(),
        credential_resolver=object(),
        probed_at=timestamp,
    )
    assert received == [timestamp]


def test_composition_has_no_forbidden_operational_module_surface() -> None:
    forbidden = {
        "asyncio", "logging", "os", "pathlib", "subprocess", "datetime", "time", "uuid",
        "hashlib", "telegram", "Bot", "HTTPXRequest", "destination", "ledger", "publication",
        "provider", "launcher", "runtime", "systemd",
    }
    assert not forbidden.intersection(module.__dict__)


def test_composition_retains_no_invocation_state_or_result_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "run_controlled_telegram_identity_probe", lambda **_: object())
    composition = ControlledTelegramIdentityProbeCompositionV1()
    composition(
        authorization=object(),
        credential_metadata=object(),
        credential_resolver=object(),
        probed_at=object(),
    )
    assert tuple(field.name for field in fields(composition)) == ("_adapter",)


def test_default_composition_reuses_its_one_owned_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    adapters: list[object] = []

    def executor(**kwargs: object) -> object:
        adapters.append(kwargs["telegram_identity_probe"])
        return object()

    monkeypatch.setattr(module, "run_controlled_telegram_identity_probe", executor)
    composition = ControlledTelegramIdentityProbeCompositionV1()
    for _ in range(2):
        composition(
            authorization=object(),
            credential_metadata=object(),
            credential_resolver=object(),
            probed_at=object(),
        )
    assert adapters == [composition._adapter, composition._adapter]
