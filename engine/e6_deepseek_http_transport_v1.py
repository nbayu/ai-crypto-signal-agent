"""Exact synchronous DeepSeek HTTP transport for the committed E5 port."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import json
import os
from typing import Final

import httpx

from engine.e5_deepseek_technical_review_v1 import (
    reconstruct_e5_deepseek_structured_review_v1,
)
from engine.e5_provider_invocation_boundary_v1 import (
    ACTIVE_PROVIDER_BINDING_SHA256,
    AUTHENTICATION_OR_PERMISSION_FAILURE,
    BUDGET_BLOCKED,
    DEEPSEEK,
    DEEPSEEK_TECHNICAL_REVIEW,
    E5_PROVIDER_PRE_NETWORK_FAILURE_V1_VERSION,
    MALFORMED_OR_SCHEMA_INVALID_RESPONSE,
    SUCCESS,
    TEMPORARILY_UNAVAILABLE,
    TIMEOUT,
    TOKEN_LIMIT_EXCEEDED,
    UNSUPPORTED_MODEL,
    E5ProviderAttemptObservationV1,
    E5ProviderPreNetworkFailureV1,
    E5ProviderRequestV1,
    build_e5_provider_attempt_observation_v1,
)
from engine.e5_technical_review_payload_v1 import (
    get_owner_frozen_e5_provider_model_price_binding_v4,
)
from engine.e6_provider_runtime_configuration_v1 import (
    E6ProviderRuntimeConfigurationV1,
    get_owner_frozen_e6_provider_runtime_configuration_v1,
)


_EXPECTED_MODEL: Final = "deepseek-v4-pro"
_EXPECTED_OUTPUT_LIMIT: Final = 500
_EXPECTED_TIMEOUT_SECONDS: Final = 60
_EXPECTED_ATTEMPTS: Final = 1
_EXPECTED_RETRY_COUNT: Final = 0
_THINKING_MODE: Final = "disabled"
_REASONING_EFFORT: Final = "none"


class _InvalidResponse(Exception):
    pass


class _ModelMismatch(Exception):
    pass


class _TokenLimit(Exception):
    pass


def _pre_network_failure(
    classification: str,
    safe_detail_code: str,
) -> E5ProviderPreNetworkFailureV1:
    return E5ProviderPreNetworkFailureV1(
        failure_version=E5_PROVIDER_PRE_NETWORK_FAILURE_V1_VERSION,
        failure_classification=classification,
        safe_detail_code=safe_detail_code,
    )


def _configuration_failure(safe_detail_code: str) -> E5ProviderPreNetworkFailureV1:
    return _pre_network_failure("HOLD_PROVIDER_CONFIGURATION", safe_detail_code)


def _unavailable_failure(safe_detail_code: str) -> E5ProviderPreNetworkFailureV1:
    return _pre_network_failure("HOLD_PROVIDER_UNAVAILABLE", safe_detail_code)


def _validate_runtime_configuration(
    value: object,
) -> E6ProviderRuntimeConfigurationV1:
    try:
        if type(value) is not E6ProviderRuntimeConfigurationV1:
            raise ValueError
        value.__post_init__()
        if value.provider_binding_sha256 != ACTIVE_PROVIDER_BINDING_SHA256:
            raise ValueError
        return value
    except Exception:
        raise _configuration_failure("RUNTIME_CONFIGURATION_INVALID") from None


def _validate_request(request: object) -> E5ProviderRequestV1:
    try:
        if type(request) is not E5ProviderRequestV1:
            raise ValueError
        request.__post_init__()
        binding = get_owner_frozen_e5_provider_model_price_binding_v4()
        if (
            request.provider != DEEPSEEK
            or request.invocation_role != DEEPSEEK_TECHNICAL_REVIEW
            or request.route is not None
            or request.provider_binding_sha256 != ACTIVE_PROVIDER_BINDING_SHA256
            or request.model_id != _EXPECTED_MODEL
            or request.output_hard_limit_tokens != _EXPECTED_OUTPUT_LIMIT
            or request.timeout_seconds != _EXPECTED_TIMEOUT_SECONDS
            or request.provider_attempts != _EXPECTED_ATTEMPTS
            or request.retry_count != _EXPECTED_RETRY_COUNT
            or binding.binding_sha256 != request.provider_binding_sha256
            or binding.deepseek_model_id != request.model_id
            or binding.deepseek_output_hard_limit_tokens
            != request.output_hard_limit_tokens
            or binding.deepseek_timeout_seconds != request.timeout_seconds
            or binding.deepseek_provider_attempts != request.provider_attempts
            or binding.deepseek_retry_count != request.retry_count
            or binding.deepseek_thinking_mode != _THINKING_MODE
            or binding.deepseek_reasoning_effort != _REASONING_EFFORT
        ):
            raise ValueError
        return request
    except Exception:
        raise _configuration_failure("REQUEST_CONTRACT_INVALID") from None


def _credential(configuration: E6ProviderRuntimeConfigurationV1) -> str:
    name = configuration.deepseek_api_key_environment_variable
    if name not in os.environ:
        raise _configuration_failure("CREDENTIAL_MISSING")
    value = os.environ[name]
    if not value.strip():
        raise _configuration_failure("CREDENTIAL_EMPTY")
    return value


def _canonical_body(request: E5ProviderRequestV1) -> bytes:
    mapping = {
        "model": request.model_id,
        "messages": [
            {
                "role": "user",
                "content": request.canonical_input_json,
            }
        ],
        "max_tokens": request.output_hard_limit_tokens,
        "stream": False,
        "thinking": {"type": _THINKING_MODE},
    }
    try:
        return json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except Exception:
        raise _configuration_failure("REQUEST_SERIALIZATION_FAILED") from None


def _build_httpx_client(
    runtime_configuration: E6ProviderRuntimeConfigurationV1,
    timeout_seconds: int,
) -> httpx.Client:
    transport = httpx.HTTPTransport(retries=0)
    return httpx.Client(
        transport=transport,
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=runtime_configuration.follow_redirects,
        trust_env=runtime_configuration.trust_environment,
        http2=runtime_configuration.http2_enabled,
    )


def _failure_observation(
    request: E5ProviderRequestV1,
    outcome: str,
) -> E5ProviderAttemptObservationV1:
    return build_e5_provider_attempt_observation_v1(
        request=request,
        transport_outcome=outcome,
        response_mapping=None,
        measured_input_tokens=0,
        measured_output_tokens=0,
        billed_cost_micro_usd=0,
    )


def _status_outcome(status_code: int) -> str:
    if status_code in (401, 403):
        return AUTHENTICATION_OR_PERMISSION_FAILURE
    if status_code == 402:
        return BUDGET_BLOCKED
    if status_code == 404:
        return UNSUPPORTED_MODEL
    if status_code in (408, 504):
        return TIMEOUT
    if status_code == 413:
        return TOKEN_LIMIT_EXCEEDED
    if status_code == 429 or (500 <= status_code <= 599 and status_code != 504):
        return TEMPORARILY_UNAVAILABLE
    return MALFORMED_OR_SCHEMA_INVALID_RESPONSE


def _bounded_response_body(response: httpx.Response, maximum_bytes: int) -> bytes:
    declared = response.headers.get_list("content-length", split_commas=True)
    normalized = tuple(item.strip() for item in declared)
    if normalized:
        if (
            any(not item or not item.isdecimal() for item in normalized)
            or len(set(normalized)) != 1
        ):
            raise _InvalidResponse
        if int(normalized[0]) > maximum_bytes:
            raise _InvalidResponse
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        if type(chunk) is not bytes:
            raise _InvalidResponse
        if total + len(chunk) > maximum_bytes:
            raise _InvalidResponse
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def _validate_json_content_type(response: httpx.Response) -> None:
    raw = response.headers.get("content-type")
    if type(raw) is not str:
        raise _InvalidResponse
    parts = tuple(part.strip() for part in raw.split(";"))
    if not parts or parts[0].casefold() != "application/json":
        raise _InvalidResponse
    parameters = parts[1:]
    if len(parameters) > 1:
        raise _InvalidResponse
    if parameters:
        name, separator, value = parameters[0].partition("=")
        charset = value.strip().strip('"').casefold()
        if name.strip().casefold() != "charset" or separator != "=" or charset != "utf-8":
            raise _InvalidResponse


def _reject_nonfinite(_: str) -> object:
    raise _InvalidResponse


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidResponse
        result[key] = value
    return result


def _strict_json_object(text: str) -> dict[str, object]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except _InvalidResponse:
        raise
    except Exception:
        raise _InvalidResponse from None
    if type(value) is not dict:
        raise _InvalidResponse
    return value


def _exact_count(value: object) -> int:
    if type(value) is not int or value < 0:
        raise _InvalidResponse
    return value


def _usage(mapping: dict[str, object]) -> tuple[int, int, int, int]:
    usage = mapping.get("usage")
    if type(usage) is not dict:
        raise _InvalidResponse
    prompt = _exact_count(usage.get("prompt_tokens"))
    completion = _exact_count(usage.get("completion_tokens"))
    cache_hit = _exact_count(usage.get("prompt_cache_hit_tokens"))
    cache_miss = _exact_count(usage.get("prompt_cache_miss_tokens"))
    if prompt != cache_hit + cache_miss:
        raise _InvalidResponse
    details = usage.get("completion_tokens_details")
    if details is not None:
        if type(details) is not dict:
            raise _InvalidResponse
        reasoning = details.get("reasoning_tokens")
        if reasoning is not None and _exact_count(reasoning) > completion:
            raise _InvalidResponse
    return prompt, completion, cache_hit, cache_miss


def _cost_micro_usd(cache_hit: int, cache_miss: int, completion: int) -> int:
    cost = (
        Decimal(cache_hit) * Decimal("0.003625")
        + Decimal(cache_miss) * Decimal("0.435")
        + Decimal(completion) * Decimal("0.87")
    )
    return int(cost.to_integral_value(rounding=ROUND_CEILING))


def _success_observation(
    request: E5ProviderRequestV1,
    mapping: dict[str, object],
) -> E5ProviderAttemptObservationV1:
    if mapping.get("model") != request.model_id:
        raise _ModelMismatch
    choices = mapping.get("choices")
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        raise _InvalidResponse
    choice = choices[0]
    message = choice.get("message")
    if type(message) is not dict:
        raise _InvalidResponse
    content = message.get("content")
    if type(content) is not str or not content:
        raise _InvalidResponse
    prompt, completion, cache_hit, cache_miss = _usage(mapping)
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length" or completion > request.output_hard_limit_tokens:
        raise _TokenLimit
    if finish_reason != "stop":
        raise _InvalidResponse
    review_mapping = _strict_json_object(content)
    try:
        review = reconstruct_e5_deepseek_structured_review_v1(review_mapping)
    except Exception:
        raise _InvalidResponse from None
    if review.payload_sha256 != request.payload_sha256 or review.model_id != request.model_id:
        raise _InvalidResponse
    return build_e5_provider_attempt_observation_v1(
        request=request,
        transport_outcome=SUCCESS,
        response_mapping=review.to_mapping(),
        measured_input_tokens=prompt,
        measured_output_tokens=completion,
        billed_cost_micro_usd=_cost_micro_usd(cache_hit, cache_miss, completion),
    )


def _response_observation(
    request: E5ProviderRequestV1,
    response: httpx.Response,
    configuration: E6ProviderRuntimeConfigurationV1,
) -> E5ProviderAttemptObservationV1:
    try:
        body = _bounded_response_body(
            response,
            configuration.maximum_response_body_bytes,
        )
    except _InvalidResponse:
        return _failure_observation(request, MALFORMED_OR_SCHEMA_INVALID_RESPONSE)
    if response.status_code != 200:
        return _failure_observation(request, _status_outcome(response.status_code))
    try:
        _validate_json_content_type(response)
        text = body.decode("utf-8")
        mapping = _strict_json_object(text)
        return _success_observation(request, mapping)
    except _ModelMismatch:
        return _failure_observation(request, UNSUPPORTED_MODEL)
    except _TokenLimit:
        return _failure_observation(request, TOKEN_LIMIT_EXCEEDED)
    except Exception:
        return _failure_observation(request, MALFORMED_OR_SCHEMA_INVALID_RESPONSE)


@dataclass(frozen=True, slots=True)
class E6DeepSeekHttpTransportV1:
    runtime_configuration: E6ProviderRuntimeConfigurationV1

    def __post_init__(self) -> None:
        _validate_runtime_configuration(self.runtime_configuration)

    def __call__(
        self,
        request: E5ProviderRequestV1,
    ) -> E5ProviderAttemptObservationV1:
        configuration = _validate_runtime_configuration(self.runtime_configuration)
        verified_request = _validate_request(request)
        credential = _credential(configuration)
        body = _canonical_body(verified_request)
        headers = {
            "Authorization": f"Bearer {credential}",
            "Content-Type": configuration.request_content_type,
            "Accept": configuration.response_accept_type,
        }
        try:
            client = _build_httpx_client(
                configuration,
                verified_request.timeout_seconds,
            )
        except (TypeError, ValueError):
            raise _configuration_failure("HTTP_CLIENT_CONFIGURATION_INVALID") from None
        except httpx.TransportError:
            raise _unavailable_failure(
                "HTTP_CLIENT_TEMPORARILY_UNAVAILABLE_BEFORE_SEND"
            ) from None
        except Exception:
            raise _unavailable_failure("PRE_SEND_CLIENT_FAILURE") from None

        send_started = False
        try:
            with client:
                try:
                    prebuilt_request = client.build_request(
                        "POST",
                        configuration.deepseek_endpoint,
                        headers=headers,
                        content=body,
                    )
                except Exception:
                    raise _configuration_failure(
                        "HTTP_CLIENT_CONFIGURATION_INVALID"
                    ) from None
                send_started = True
                response = client.send(prebuilt_request, stream=True)
                try:
                    return _response_observation(
                        verified_request,
                        response,
                        configuration,
                    )
                finally:
                    response.close()
        except E5ProviderPreNetworkFailureV1:
            raise
        except httpx.TimeoutException:
            if not send_started:
                raise _unavailable_failure("PRE_SEND_CLIENT_FAILURE") from None
            return _failure_observation(verified_request, TIMEOUT)
        except httpx.TransportError:
            if not send_started:
                raise _unavailable_failure("PRE_SEND_CLIENT_FAILURE") from None
            return _failure_observation(verified_request, TEMPORARILY_UNAVAILABLE)
        except Exception:
            if not send_started:
                raise _unavailable_failure("PRE_SEND_CLIENT_FAILURE") from None
            return _failure_observation(verified_request, TEMPORARILY_UNAVAILABLE)


def get_e6_deepseek_http_transport_v1() -> E6DeepSeekHttpTransportV1:
    return E6DeepSeekHttpTransportV1(
        runtime_configuration=(
            get_owner_frozen_e6_provider_runtime_configuration_v1()
        )
    )


__all__ = (
    "E6DeepSeekHttpTransportV1",
    "get_e6_deepseek_http_transport_v1",
)
