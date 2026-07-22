"""Focused fake-only tests for the pure one-shot Telegram probe harness."""
from __future__ import annotations

import inspect

import pytest

import engine.one_shot_telegram_identity_probe_harness_v1 as module
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
    INJECTED_SECRET_RESOLVER,
    TELEGRAM_CREDENTIAL_NAME,
    ControlledCredentialMetadataV1,
)
from engine.one_shot_telegram_identity_probe_harness_v1 import (
    run_one_shot_telegram_identity_probe,
)


_TIMESTAMP = "2026-07-22T00:00:00Z"
_SECRET = "opaque-fake-secret"


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
        source_kind=INJECTED_SECRET_RESOLVER,
        required=True,
        available=True,
        readable=True,
        non_empty=True,
        reason=CONTROLLED_CREDENTIAL_METADATA_VALID,
    )


def test_public_function_has_the_exact_keyword_only_signature() -> None:
    signature = inspect.signature(run_one_shot_telegram_identity_probe)
    assert tuple(signature.parameters) == (
        "authorization",
        "credential_metadata",
        "secret_reader",
        "probed_at",
        "composition",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert signature.parameters["composition"].default is None


def test_public_function_has_no_forbidden_inputs() -> None:
    names = set(inspect.signature(run_one_shot_telegram_identity_probe).parameters)
    forbidden = {
        "token", "credential_resolver", "telegram_identity_probe", "adapter",
        "adapter_factory", "destination", "destination_id", "channel", "allowlist",
        "message_thread_id", "component_versions", "active_ledger_path",
        "expected_active_ledger_revision", "candidate", "publication", "output_stream",
        "logger", "exit_code", "timeout", "runtime", "launcher", "service", "systemd",
    }
    assert not names.intersection(forbidden)


def test_supplied_composition_forwards_inputs_and_returns_exact_result() -> None:
    received: dict[str, object] = {}
    result = object()
    authorization = object()
    metadata = object()
    timestamp = object()

    def composition(**kwargs: object) -> object:
        received.update(kwargs)
        return result

    returned = run_one_shot_telegram_identity_probe(
        authorization=authorization,
        credential_metadata=metadata,
        secret_reader=lambda: _SECRET,
        probed_at=timestamp,
        composition=composition,
    )
    assert returned is result
    assert received["authorization"] is authorization
    assert received["credential_metadata"] is metadata
    assert received["probed_at"] is timestamp
    assert received["credential_resolver"] is not None


def test_supplied_composition_prevents_default_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_default() -> object:
        raise AssertionError("default composition must not be created")

    monkeypatch.setattr(module, "ControlledTelegramIdentityProbeCompositionV1", forbidden_default)
    result = object()
    returned = run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=lambda: _SECRET,
        probed_at=object(),
        composition=lambda **_: result,
    )
    assert returned is result


def test_default_composition_is_created_once_and_called_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    result = object()

    class FakeComposition:
        def __call__(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return result

    created: list[object] = []

    def factory() -> FakeComposition:
        instance = FakeComposition()
        created.append(instance)
        return instance

    monkeypatch.setattr(module, "ControlledTelegramIdentityProbeCompositionV1", factory)
    returned = run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=lambda: _SECRET,
        probed_at=object(),
    )
    assert returned is result
    assert len(created) == len(calls) == 1


def test_local_resolver_has_exact_keyword_only_contract_and_reads_once() -> None:
    received: list[object] = []
    result = object()

    def composition(**kwargs: object) -> object:
        resolver = kwargs["credential_resolver"]
        signature = inspect.signature(resolver)
        assert tuple(signature.parameters) == ("credential_name", "source_kind")
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in signature.parameters.values()
        )
        received.append(resolver(
            credential_name="telegram_bot_token",
            source_kind="INJECTED_SECRET_RESOLVER",
        ))
        return result

    returned = run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=lambda: _SECRET,
        probed_at=object(),
        composition=composition,
    )
    assert returned is result
    assert received == [_SECRET]


@pytest.mark.parametrize(
    ("credential_name", "source_kind"),
    (
        ("wrong", "INJECTED_SECRET_RESOLVER"),
        ("telegram_bot_token", "wrong"),
    ),
)
def test_invalid_resolver_identity_does_not_read_secret(
    credential_name: str, source_kind: str
) -> None:
    reader_calls: list[object] = []

    def composition(**kwargs: object) -> object:
        with pytest.raises(Exception):
            kwargs["credential_resolver"](
                credential_name=credential_name,
                source_kind=source_kind,
            )
        return object()

    run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=lambda: reader_calls.append(object()),
        probed_at=object(),
        composition=composition,
    )
    assert reader_calls == []


def test_second_valid_resolver_call_is_rejected_without_second_read() -> None:
    reader_calls: list[tuple[object, ...]] = []

    def reader(*args: object) -> str:
        reader_calls.append(args)
        return _SECRET

    def composition(**kwargs: object) -> object:
        resolver = kwargs["credential_resolver"]
        assert resolver(
            credential_name="telegram_bot_token",
            source_kind="INJECTED_SECRET_RESOLVER",
        ) == _SECRET
        with pytest.raises(Exception):
            resolver(
                credential_name="telegram_bot_token",
                source_kind="INJECTED_SECRET_RESOLVER",
            )
        return object()

    run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=reader,
        probed_at=object(),
        composition=composition,
    )
    assert reader_calls == [()]


@pytest.mark.parametrize("value", (_SECRET, b"fake-bytes", object()))
def test_resolver_returns_reader_value_unchanged(value: object) -> None:
    received: list[object] = []

    def composition(**kwargs: object) -> object:
        received.append(kwargs["credential_resolver"](
            credential_name="telegram_bot_token",
            source_kind="INJECTED_SECRET_RESOLVER",
        ))
        return object()

    run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=lambda: value,
        probed_at=object(),
        composition=composition,
    )
    assert received == [value]


def test_reader_exception_reaches_the_supplied_composition() -> None:
    error = RuntimeError("fake-reader-failure")

    def reader() -> object:
        raise error

    def composition(**kwargs: object) -> object:
        with pytest.raises(RuntimeError) as caught:
            kwargs["credential_resolver"](
                credential_name="telegram_bot_token",
                source_kind="INJECTED_SECRET_RESOLVER",
            )
        assert caught.value is error
        return object()

    run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=reader,
        probed_at=object(),
        composition=composition,
    )


def test_composition_exception_is_not_caught_by_harness() -> None:
    error = RuntimeError("fake-composition-failure")

    def composition(**_: object) -> object:
        raise error

    with pytest.raises(RuntimeError) as caught:
        run_one_shot_telegram_identity_probe(
            authorization=object(),
            credential_metadata=object(),
            secret_reader=lambda: _SECRET,
            probed_at=object(),
            composition=composition,
        )
    assert caught.value is error


def test_rejected_resolver_uses_a_fixed_nonleaking_exception() -> None:
    captured: list[BaseException] = []

    def composition(**kwargs: object) -> object:
        try:
            kwargs["credential_resolver"](
                credential_name="wrong",
                source_kind="wrong",
            )
        except Exception as error:
            captured.append(error)
        return object()

    run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=lambda: _SECRET,
        probed_at=object(),
        composition=composition,
    )
    assert len(captured) == 1
    assert str(captured[0]) == ""
    assert _SECRET not in repr(captured[0])


def test_base_exception_from_reader_is_not_caught_by_harness() -> None:
    def composition(**kwargs: object) -> object:
        kwargs["credential_resolver"](
            credential_name="telegram_bot_token",
            source_kind="INJECTED_SECRET_RESOLVER",
        )
        return object()

    with pytest.raises(KeyboardInterrupt):
        run_one_shot_telegram_identity_probe(
            authorization=object(),
            credential_metadata=object(),
            secret_reader=lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
            probed_at=object(),
            composition=composition,
        )


@pytest.mark.parametrize("closed", ("activation", "workload", "credential", "network"))
def test_closed_gates_do_not_invoke_reader(closed: str) -> None:
    values = {
        "activation_authorized": True,
        "workload_authorized": True,
        "credential_authorized": True,
        "network_authorized": True,
    }
    values[f"{closed}_authorized"] = False
    reader_calls: list[object] = []
    composition = ControlledTelegramIdentityProbeCompositionV1(
        _adapter=lambda **_: (_ for _ in ()).throw(AssertionError("adapter called"))
    )
    result = run_one_shot_telegram_identity_probe(
        authorization=_authorization(**values),
        credential_metadata=_metadata(),
        secret_reader=lambda: reader_calls.append(object()),
        probed_at=_TIMESTAMP,
        composition=composition,
    )
    expected = {
        "activation": ACTIVATION_GATE_CLOSED,
        "workload": WORKLOAD_GATE_CLOSED,
        "credential": CREDENTIAL_GATE_CLOSED,
        "network": NETWORK_GATE_CLOSED,
    }
    assert result.result == expected[closed]
    assert reader_calls == []


def test_fake_success_and_reader_failure_preserve_executor_results() -> None:
    adapter_calls: list[dict[str, object]] = []
    composition = ControlledTelegramIdentityProbeCompositionV1(
        _adapter=lambda **kwargs: adapter_calls.append(kwargs) is None
    )
    success = run_one_shot_telegram_identity_probe(
        authorization=_authorization(),
        credential_metadata=_metadata(),
        secret_reader=lambda: _SECRET,
        probed_at=_TIMESTAMP,
        composition=composition,
    )
    failure = run_one_shot_telegram_identity_probe(
        authorization=_authorization(),
        credential_metadata=_metadata(),
        secret_reader=lambda: (_ for _ in ()).throw(RuntimeError("fake")),
        probed_at=_TIMESTAMP,
        composition=composition,
    )
    assert success.result == TELEGRAM_IDENTITY_CONFIRMED
    assert failure.result == CREDENTIAL_RESOLUTION_FAILED
    assert len(adapter_calls) == 1
    assert _SECRET not in repr(success) + repr(failure) + repr(composition)


def test_invalid_secret_value_preserves_credential_value_invalid_classification() -> None:
    invalid_value = b"fake-invalid-secret"
    reader_calls: list[object] = []
    adapter_calls: list[dict[str, object]] = []
    composition = ControlledTelegramIdentityProbeCompositionV1(
        _adapter=lambda **kwargs: adapter_calls.append(kwargs) is None
    )
    result = run_one_shot_telegram_identity_probe(
        authorization=_authorization(),
        credential_metadata=_metadata(),
        secret_reader=lambda: reader_calls.append(object()) or invalid_value,
        probed_at=_TIMESTAMP,
        composition=composition,
    )
    assert (result.result, result.reason) == (
        CREDENTIAL_VALUE_INVALID,
        CREDENTIAL_VALUE_INVALID,
    )
    assert result.credential_resolution_attempted is True
    assert result.credential_resolved is False
    assert result.network_probe_attempted is False
    assert result.bot_identity_confirmed is False
    assert result.probe_timestamp == ""
    assert len(reader_calls) == 1
    assert adapter_calls == []
    assert b"fake-invalid-secret" not in repr(result).encode()
    assert b"fake-invalid-secret" not in repr(result.to_dict()).encode()


@pytest.mark.parametrize("outcome", (False, RuntimeError("fake-adapter-failure")))
def test_adapter_failure_preserves_telegram_identity_probe_failed_classification(
    outcome: object,
) -> None:
    reader_calls: list[object] = []
    adapter_calls: list[dict[str, object]] = []

    def adapter(**kwargs: object) -> bool:
        adapter_calls.append(kwargs)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome is True

    result = run_one_shot_telegram_identity_probe(
        authorization=_authorization(),
        credential_metadata=_metadata(),
        secret_reader=lambda: reader_calls.append(object()) or _SECRET,
        probed_at=_TIMESTAMP,
        composition=ControlledTelegramIdentityProbeCompositionV1(_adapter=adapter),
    )
    assert (result.result, result.reason) == (
        TELEGRAM_IDENTITY_PROBE_FAILED,
        TELEGRAM_IDENTITY_PROBE_FAILED,
    )
    assert result.credential_resolution_attempted is True
    assert result.credential_resolved is True
    assert result.network_probe_attempted is True
    assert result.bot_identity_confirmed is False
    assert result.probe_timestamp == ""
    assert len(reader_calls) == len(adapter_calls) == 1
    assert _SECRET not in repr(result) + repr(result.to_dict())
    assert "fake-adapter-failure" not in repr(result) + repr(result.to_dict())


def test_harness_module_has_no_operational_public_surface() -> None:
    forbidden = {
        "asyncio", "getpass", "argparse", "sys", "json", "logging", "os", "pathlib",
        "subprocess", "datetime", "time", "telegram", "Bot", "HTTPXRequest", "input",
        "destination", "ledger", "publication", "provider", "launcher", "runtime", "systemd",
    }
    assert not forbidden.intersection(module.__dict__)
    assert _SECRET not in repr(module.__dict__)


def test_harness_has_no_persistent_invocation_state() -> None:
    result = object()
    run_one_shot_telegram_identity_probe(
        authorization=object(),
        credential_metadata=object(),
        secret_reader=lambda: _SECRET,
        probed_at=object(),
        composition=lambda **_: result,
    )
    assert not {"authorization", "credential_metadata", "secret_reader", "probed_at", "result"}.intersection(module.__dict__)
