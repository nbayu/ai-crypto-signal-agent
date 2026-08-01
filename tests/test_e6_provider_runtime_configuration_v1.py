from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
from pathlib import Path

import pytest

import engine.e6_provider_runtime_configuration_v1 as subject


EXPECTED_FIELDS = (
    "configuration_version",
    "provider_binding_sha256",
    "deepseek_endpoint",
    "claude_endpoint",
    "deepseek_api_key_environment_variable",
    "claude_api_key_environment_variable",
    "claude_api_version",
    "request_content_type",
    "response_accept_type",
    "follow_redirects",
    "trust_environment",
    "http2_enabled",
    "automatic_retry_count",
    "stream_response_body",
    "maximum_response_body_bytes",
)
EXPECTED_VALUES = (
    "e6-provider-runtime-configuration-v1",
    "4a31dbcb7a0c4daed3215dbe8817002c24b2ead30e7092096c992b322e0fe1d9",
    "https://api.deepseek.com/chat/completions",
    "https://api.anthropic.com/v1/messages",
    "DEEPSEEK_API_KEY",
    "ANTHROPIC_API_KEY",
    "2023-06-01",
    "application/json",
    "application/json",
    False,
    False,
    False,
    0,
    True,
    1048576,
)


def test_exact_version_type_fields_and_values():
    configuration = subject.get_owner_frozen_e6_provider_runtime_configuration_v1()
    assert subject.E6_PROVIDER_RUNTIME_CONFIGURATION_V1_VERSION == (
        "e6-provider-runtime-configuration-v1"
    )
    assert type(configuration) is subject.E6ProviderRuntimeConfigurationV1
    assert is_dataclass(configuration)
    assert configuration.__dataclass_params__.frozen is True
    assert tuple(field.name for field in fields(configuration)) == EXPECTED_FIELDS
    assert len(fields(configuration)) == 15
    assert tuple(getattr(configuration, name) for name in EXPECTED_FIELDS) == (
        EXPECTED_VALUES
    )
    assert hasattr(type(configuration), "__slots__")
    assert not hasattr(configuration, "__dict__")


def test_zero_argument_getter_is_deterministic_and_configuration_is_immutable():
    assert tuple(inspect.signature(
        subject.get_owner_frozen_e6_provider_runtime_configuration_v1
    ).parameters) == ()
    first = subject.get_owner_frozen_e6_provider_runtime_configuration_v1()
    second = subject.get_owner_frozen_e6_provider_runtime_configuration_v1()
    assert first == second
    assert hash(first) == hash(second)
    with pytest.raises(FrozenInstanceError):
        first.deepseek_endpoint = "https://example.invalid"  # type: ignore[misc]
    with pytest.raises(ValueError, match="^invalid E6 provider runtime configuration$"):
        replace(first, automatic_retry_count=1)


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("configuration_version", "e6-provider-runtime-configuration-v2"),
        ("provider_binding_sha256", "0" * 64),
        ("deepseek_endpoint", "https://api.deepseek.com/v1/chat/completions"),
        ("claude_endpoint", "https://api.anthropic.com/messages"),
        ("deepseek_api_key_environment_variable", "OTHER_KEY"),
        ("claude_api_key_environment_variable", "OTHER_KEY"),
        ("claude_api_version", "latest"),
        ("request_content_type", "text/plain"),
        ("response_accept_type", "*/*"),
        ("follow_redirects", True),
        ("trust_environment", True),
        ("http2_enabled", True),
        ("automatic_retry_count", 1),
        ("stream_response_body", False),
        ("maximum_response_body_bytes", 1048577),
    ),
)
def test_every_field_is_exact_value_validated(name, value):
    configuration = subject.get_owner_frozen_e6_provider_runtime_configuration_v1()
    with pytest.raises(ValueError, match="^invalid E6 provider runtime configuration$"):
        replace(configuration, **{name: value})


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("follow_redirects", 0),
        ("trust_environment", 0),
        ("http2_enabled", 0),
        ("automatic_retry_count", False),
        ("stream_response_body", 1),
        ("maximum_response_body_bytes", 1048576.0),
    ),
)
def test_boolean_and_integer_fields_require_exact_builtin_types(name, value):
    configuration = subject.get_owner_frozen_e6_provider_runtime_configuration_v1()
    with pytest.raises(ValueError, match="^invalid E6 provider runtime configuration$"):
        replace(configuration, **{name: value})


def test_public_exports_are_explicit_and_minimal():
    assert subject.__all__ == (
        "E6_PROVIDER_RUNTIME_CONFIGURATION_V1_VERSION",
        "E6ProviderRuntimeConfigurationV1",
        "get_owner_frozen_e6_provider_runtime_configuration_v1",
    )


def test_source_has_no_environment_read_network_call_or_selector():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from_os = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "os"
        for alias in node.names
    }
    os_attribute_names = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    }
    bare_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }
    assert "os" not in imported_roots
    assert "httpx" not in imported_roots
    assert "requests" not in imported_roots
    assert "socket" not in imported_roots
    assert imported_from_os == set()
    assert not {"environ", "getenv"} & os_attribute_names
    assert not {"environ", "getenv"} & bare_names
    assert "selector" not in source.casefold()
    assert "api_key=" not in source.casefold()
