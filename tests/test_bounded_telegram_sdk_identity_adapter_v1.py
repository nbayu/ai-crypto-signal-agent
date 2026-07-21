"""Fake-only tests for the bounded Telegram SDK identity adapter."""
from __future__ import annotations

import asyncio
from dataclasses import fields
import inspect
import math

import pytest

import engine.bounded_telegram_sdk_identity_adapter_v1 as module
from engine.bounded_telegram_sdk_identity_adapter_v1 import (
    BoundedTelegramSdkIdentityProbeV1,
)


_TOKEN = "opaque-test-token"


class _IdentityTrap:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(name)


class _FakeSession:
    def __init__(
        self,
        *,
        entry_error: Exception | None = None,
        exit_error: Exception | None = None,
    ) -> None:
        self.entry_calls = 0
        self.exit_calls = 0
        self._entry_error = entry_error
        self._exit_error = exit_error

    async def __aenter__(self) -> object:
        self.entry_calls += 1
        if self._entry_error is not None:
            raise self._entry_error
        return _IdentityTrap()

    async def __aexit__(self, exc_type: object, exc: object, trace: object) -> None:
        self.exit_calls += 1
        if self._exit_error is not None:
            raise self._exit_error


class _FakeFactory:
    def __init__(self, result: object | Exception) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> object:
        self.calls.append(dict(kwargs))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _adapter(
    result: object | Exception = None,
    **changes: object,
) -> tuple[BoundedTelegramSdkIdentityProbeV1, _FakeFactory]:
    factory = _FakeFactory(_FakeSession() if result is None else result)
    values: dict[str, object] = {"_factory": factory}
    values.update(changes)
    return BoundedTelegramSdkIdentityProbeV1(**values), factory


def test_type_schema_defaults_and_callable_signature_are_exact() -> None:
    adapter = BoundedTelegramSdkIdentityProbeV1()
    assert tuple(field.name for field in fields(adapter)) == (
        "timeout_seconds",
        "pool_timeout_seconds",
        "_factory",
    )
    assert [field.name for field in fields(adapter) if not field.name.startswith("_")] == [
        "timeout_seconds",
        "pool_timeout_seconds",
    ]
    assert adapter.timeout_seconds == 5.0
    assert adapter.pool_timeout_seconds == 1.0
    assert not hasattr(adapter, "__dict__")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in inspect.signature(adapter.__call__).parameters.values()
    )
    with pytest.raises((AttributeError, TypeError)):
        adapter.timeout_seconds = 2.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    (
        {"timeout_seconds": True},
        {"pool_timeout_seconds": False},
        {"timeout_seconds": 0},
        {"pool_timeout_seconds": -1},
        {"timeout_seconds": math.nan},
        {"pool_timeout_seconds": math.inf},
        {"timeout_seconds": "5"},
        {"pool_timeout_seconds": object()},
    ),
)
def test_timeout_values_are_strict_positive_and_finite(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError) as error:
        BoundedTelegramSdkIdentityProbeV1(**changes)
    assert str(error.value) == "INVALID_TIMEOUT"


@pytest.mark.parametrize(
    "token",
    ("", "   ", b"value", True, {"value": _TOKEN}, 1, object()),
)
def test_invalid_tokens_fail_before_factory_access(token: object) -> None:
    adapter, factory = _adapter()
    assert adapter(token=token) is False
    assert factory.calls == []


def test_valid_token_is_forwarded_unchanged_once_with_exact_timeouts() -> None:
    session = _FakeSession()
    adapter, factory = _adapter(
        session,
        timeout_seconds=7.5,
        pool_timeout_seconds=2,
    )
    assert adapter(token=_TOKEN) is True
    assert factory.calls == [
        {
            "token": _TOKEN,
            "timeout_seconds": 7.5,
            "pool_timeout_seconds": 2,
        }
    ]
    assert session.entry_calls == 1
    assert session.exit_calls == 1


def test_identity_data_is_not_inspected_or_retained() -> None:
    session = _FakeSession()
    adapter, _ = _adapter(session)
    assert adapter(token=_TOKEN) is True
    assert session.entry_calls == 1
    assert session.exit_calls == 1
    assert _TOKEN not in repr(adapter)
    assert "token" not in {field.name for field in fields(adapter)}


@pytest.mark.parametrize(
    "result",
    (
        RuntimeError(_TOKEN),
        _FakeSession(entry_error=RuntimeError(_TOKEN)),
        _FakeSession(exit_error=RuntimeError(_TOKEN)),
        object(),
    ),
)
def test_factory_or_context_failures_are_literal_false_and_sanitized(
    result: object | Exception,
) -> None:
    adapter, factory = _adapter(result)
    assert adapter(token=_TOKEN) is False
    assert len(factory.calls) == 1
    assert _TOKEN not in repr(adapter)


def test_failures_are_not_retried_or_routed_to_a_fallback() -> None:
    adapter, factory = _adapter(RuntimeError(_TOKEN))
    assert adapter(token=_TOKEN) is False
    assert len(factory.calls) == 1


def test_timeout_style_failure_and_repeated_results_stay_deterministic() -> None:
    adapter, factory = _adapter(TimeoutError(_TOKEN))
    assert adapter(token=_TOKEN) is False
    assert adapter(token=_TOKEN) is False
    assert len(factory.calls) == 2


def test_running_loop_fails_before_factory_or_coroutine_creation() -> None:
    adapter, factory = _adapter()

    async def within_loop() -> None:
        assert adapter(token=_TOKEN) is False

    asyncio.run(within_loop())
    assert factory.calls == []


def test_adapter_has_no_operational_or_persistent_surface() -> None:
    source = inspect.getsource(module)
    forbidden = (
        "telegram.ext",
        "ApplicationBuilder",
        "send_message",
        "get_chat",
        "destination_id",
        "message_thread_id",
        "subprocess",
        "threading",
        "logging",
        "print(",
        "time.time",
        "run_forever",
        "start_polling",
    )
    assert not any(item in source for item in forbidden)
    assert "self.token" not in source
    assert ".initialize(" not in source
    assert ".get_me(" not in source
    assert ".shutdown(" not in source
