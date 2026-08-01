"""Owner-frozen E6 provider runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
    get_owner_frozen_e5_provider_model_price_binding_v4,
)


E6_PROVIDER_RUNTIME_CONFIGURATION_V1_VERSION: Final = (
    "e6-provider-runtime-configuration-v1"
)

_ERROR: Final = "invalid E6 provider runtime configuration"
_FROZEN_VALUES: Final = MappingProxyType({
    "configuration_version": E6_PROVIDER_RUNTIME_CONFIGURATION_V1_VERSION,
    "provider_binding_sha256": E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
    "deepseek_endpoint": "https://api.deepseek.com/chat/completions",
    "claude_endpoint": "https://api.anthropic.com/v1/messages",
    "deepseek_api_key_environment_variable": "DEEPSEEK_API_KEY",
    "claude_api_key_environment_variable": "ANTHROPIC_API_KEY",
    "claude_api_version": "2023-06-01",
    "request_content_type": "application/json",
    "response_accept_type": "application/json",
    "follow_redirects": False,
    "trust_environment": False,
    "http2_enabled": False,
    "automatic_retry_count": 0,
    "stream_response_body": True,
    "maximum_response_body_bytes": 1048576,
})


def _fail() -> None:
    raise ValueError(_ERROR) from None


@dataclass(frozen=True, slots=True)
class E6ProviderRuntimeConfigurationV1:
    configuration_version: str
    provider_binding_sha256: str
    deepseek_endpoint: str
    claude_endpoint: str
    deepseek_api_key_environment_variable: str
    claude_api_key_environment_variable: str
    claude_api_version: str
    request_content_type: str
    response_accept_type: str
    follow_redirects: bool
    trust_environment: bool
    http2_enabled: bool
    automatic_retry_count: int
    stream_response_body: bool
    maximum_response_body_bytes: int

    def __post_init__(self) -> None:
        try:
            for name, expected in _FROZEN_VALUES.items():
                actual = getattr(self, name)
                if type(actual) is not type(expected) or actual != expected:
                    _fail()
            binding = get_owner_frozen_e5_provider_model_price_binding_v4()
            if binding.binding_sha256 != self.provider_binding_sha256:
                _fail()
        except Exception:
            _fail()


def get_owner_frozen_e6_provider_runtime_configuration_v1(
) -> E6ProviderRuntimeConfigurationV1:
    return E6ProviderRuntimeConfigurationV1(**_FROZEN_VALUES)


__all__ = (
    "E6_PROVIDER_RUNTIME_CONFIGURATION_V1_VERSION",
    "E6ProviderRuntimeConfigurationV1",
    "get_owner_frozen_e6_provider_runtime_configuration_v1",
)
