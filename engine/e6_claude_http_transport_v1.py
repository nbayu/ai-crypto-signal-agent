"""Exact synchronous Claude HTTP transport for the committed E5 port."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import json
import os
from typing import Final

import httpx

from engine.e5_provider_invocation_boundary_v1 import (
    ACTIVE_PROVIDER_BINDING_SHA256,
    ANTHROPIC,
    AUTHENTICATION_OR_PERMISSION_FAILURE,
    BUDGET_BLOCKED,
    CLAUDE_L1_ESCALATION_REVIEW,
    CLAUDE_L2_ESCALATION_REVIEW,
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
    reconstruct_e5_claude_escalation_review_v1,
)
from engine.e5_technical_review_payload_v1 import (
    get_owner_frozen_e5_provider_model_price_binding_v4,
)
from engine.e6_provider_runtime_configuration_v1 import (
    E6ProviderRuntimeConfigurationV1,
    get_owner_frozen_e6_provider_runtime_configuration_v1,
)


_L1: Final = "L1"
_L2: Final = "L2"
_L1_MODEL: Final = "claude-opus-5"
_L2_MODEL: Final = "claude-fable-5"
_L1_OUTPUT_LIMIT: Final = 500
_L2_OUTPUT_LIMIT: Final = 800
_L1_TIMEOUT_SECONDS: Final = 10
_L2_TIMEOUT_SECONDS: Final = 20
_EFFORT: Final = "high"


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
        if request.provider != ANTHROPIC:
            raise ValueError
        if request.route == _L1:
            expected = (
                CLAUDE_L1_ESCALATION_REVIEW,
                _L1_MODEL,
                _L1_OUTPUT_LIMIT,
                _L1_TIMEOUT_SECONDS,
                "disabled",
                _EFFORT,
            )
            actual = (
                request.invocation_role,
                request.model_id,
                request.output_hard_limit_tokens,
                request.timeout_seconds,
                binding.claude_l1_thinking_mode,
                binding.claude_l1_effort,
            )
        elif request.route == _L2:
            expected = (
                CLAUDE_L2_ESCALATION_REVIEW,
                _L2_MODEL,
                _L2_OUTPUT_LIMIT,
                _L2_TIMEOUT_SECONDS,
                "always_on_adaptive",
                _EFFORT,
            )
            actual = (
                request.invocation_role,
                request.model_id,
                request.output_hard_limit_tokens,
                request.timeout_seconds,
                binding.claude_l2_thinking_mode,
                binding.claude_l2_effort,
            )
        else:
            raise ValueError
        if (
            actual != expected
            or request.provider_binding_sha256 != ACTIVE_PROVIDER_BINDING_SHA256
            or request.provider_attempts != 1
            or request.retry_count != 0
            or binding.binding_sha256 != request.provider_binding_sha256
        ):
            raise ValueError
        return request
    except Exception:
        raise _configuration_failure("REQUEST_CONTRACT_INVALID") from None


def _credential(configuration: E6ProviderRuntimeConfigurationV1) -> str:
    name = configuration.claude_api_key_environment_variable
    if name not in os.environ:
        raise _configuration_failure("CREDENTIAL_MISSING")
    value = os.environ[name]
    if not value.strip():
        raise _configuration_failure("CREDENTIAL_EMPTY")
    return value


def _canonical_body(request: E5ProviderRequestV1) -> bytes:
    mapping: dict[str, object] = {
        "model": request.model_id,
        "messages": [
            {
                "role": "user",
                "content": request.canonical_input_json,
            }
        ],
        "max_tokens": request.output_hard_limit_tokens,
        "stream": False,
        "output_config": {"effort": _EFFORT},
    }
    if request.route == _L1:
        mapping["thinking"] = {"type": "disabled"}
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


def _usage(mapping: dict[str, object]) -> tuple[int, int]:
    usage = mapping.get("usage")
    if type(usage) is not dict:
        raise _InvalidResponse
    input_tokens = _exact_count(usage.get("input_tokens"))
    cache_creation = _exact_count(usage.get("cache_creation_input_tokens"))
    cache_read = _exact_count(usage.get("cache_read_input_tokens"))
    output_tokens = _exact_count(usage.get("output_tokens"))
    if cache_creation != 0 or cache_read != 0:
        raise _InvalidResponse
    details = usage.get("output_tokens_details")
    if details is not None:
        if type(details) is not dict:
            raise _InvalidResponse
        thinking = details.get("thinking_tokens")
        if thinking is not None and _exact_count(thinking) > output_tokens:
            raise _InvalidResponse
    return input_tokens + cache_creation + cache_read, output_tokens


def _cost_micro_usd(route: str, input_tokens: int, output_tokens: int) -> int:
    if route == _L1:
        input_price = Decimal("5")
        output_price = Decimal("25")
    else:
        input_price = Decimal("10")
        output_price = Decimal("50")
    cost = Decimal(input_tokens) * input_price + Decimal(output_tokens) * output_price
    return int(cost.to_integral_value(rounding=ROUND_CEILING))


def _content_text(mapping: dict[str, object], route: str) -> str:
    content = mapping.get("content")
    if type(content) is not list or not content:
        raise _InvalidResponse
    text_values: list[str] = []
    for block in content:
        if type(block) is not dict:
            raise _InvalidResponse
        block_type = block.get("type")
        if block_type == "text":
            text = block.get("text")
            if type(text) is not str or not text:
                raise _InvalidResponse
            text_values.append(text)
        elif block_type == "thinking" and route == _L2:
            continue
        else:
            raise _InvalidResponse
    if len(text_values) != 1:
        raise _InvalidResponse
    return text_values[0]


def _success_observation(
    request: E5ProviderRequestV1,
    mapping: dict[str, object],
) -> E5ProviderAttemptObservationV1:
    if mapping.get("model") != request.model_id:
        raise _ModelMismatch
    if mapping.get("type") != "message" or mapping.get("role") != "assistant":
        raise _InvalidResponse
    text = _content_text(mapping, request.route)
    measured_input, measured_output = _usage(mapping)
    stop_reason = mapping.get("stop_reason")
    if stop_reason == "max_tokens" or measured_output > request.output_hard_limit_tokens:
        raise _TokenLimit
    if stop_reason != "end_turn":
        raise _InvalidResponse
    review_mapping = _strict_json_object(text)
    try:
        review = reconstruct_e5_claude_escalation_review_v1(review_mapping)
    except Exception:
        raise _InvalidResponse from None
    if (
        review.provider_binding_sha256 != request.provider_binding_sha256
        or review.payload_sha256 != request.payload_sha256
        or review.route_sha256 != request.upstream_identity_sha256
        or review.route != request.route
        or review.model_id != request.model_id
    ):
        raise _InvalidResponse
    return build_e5_provider_attempt_observation_v1(
        request=request,
        transport_outcome=SUCCESS,
        response_mapping=review.to_mapping(),
        measured_input_tokens=measured_input,
        measured_output_tokens=measured_output,
        billed_cost_micro_usd=_cost_micro_usd(
            request.route,
            measured_input,
            measured_output,
        ),
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
class E6ClaudeHttpTransportV1:
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
            "x-api-key": credential,
            "anthropic-version": configuration.claude_api_version,
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
                        configuration.claude_endpoint,
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


def get_e6_claude_http_transport_v1() -> E6ClaudeHttpTransportV1:
    return E6ClaudeHttpTransportV1(
        runtime_configuration=(
            get_owner_frozen_e6_provider_runtime_configuration_v1()
        )
    )


__all__ = (
    "E6ClaudeHttpTransportV1",
    "get_e6_claude_http_transport_v1",
)
