"""Detached deterministic provider invocation and D8 failure contracts."""

from __future__ import annotations

from dataclasses import dataclass, fields
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Callable, Final, Mapping
import unicodedata

from engine.e5_claude_review_router_v1 import (
    BLOCK_DUPLICATE_LOGICAL_REVIEW,
    BLOCK_L2_DAILY_REVIEW_CEILING,
    BLOCK_SHARED_DAILY_REVIEW_CEILING,
    HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED,
    PASS_CLAUDE_TOKEN_BUDGET,
    ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE,
    ROUTE_L0_NO_CLAUDE_REQUIRED,
    ROUTE_L1_CLAUDE_REVIEW_REQUIRED,
    ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED,
    E5ClaudeReviewRouteResultV1,
    E5ClaudeTokenPreflightResultV1,
    L0,
    L1,
    L2,
)
from engine.e5_deepseek_technical_review_v1 import (
    E5_DEEPSEEK_STRUCTURED_REVIEW_VERSION,
    E5DeepSeekStructuredReviewV1,
    E5DeepSeekTechnicalReviewAdjudicationV1,
    reconstruct_e5_deepseek_structured_review_v1,
)
from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
    E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    HOLD_INPUT_TOKEN_LIMIT,
    HOLD_OUTPUT_TOKEN_LIMIT,
    PASS_TOKEN_BUDGET,
    E5TechnicalReviewPayloadV1,
    E5TechnicalReviewTokenPreflightResultV1,
    get_owner_frozen_e5_provider_model_price_binding_v4,
)


E5_PROVIDER_REQUEST_VERSION: Final = "e5-provider-request-v1"
E5_PROVIDER_ATTEMPT_OBSERVATION_VERSION: Final = (
    "e5-provider-attempt-observation-v1"
)
E5_CLAUDE_ESCALATION_REVIEW_VERSION: Final = (
    "e5-claude-escalation-review-v1"
)
E5_PROVIDER_INVOCATION_RESULT_VERSION: Final = (
    "e5-provider-invocation-result-v1"
)
E5_PROVIDER_ACCEPTED_RESPONSE_EXECUTION_VERSION: Final = (
    "e5-provider-accepted-response-execution-v1"
)
E5_PROVIDER_PRE_NETWORK_FAILURE_V1_VERSION: Final = (
    "e5-provider-pre-network-failure-v1"
)

ACTIVE_PROVIDER_BINDING_SHA256: Final = (
    "4a31dbcb7a0c4daed3215dbe8817002c24b2ead30e7092096c992b322e0fe1d9"
)

DEEPSEEK: Final = "DEEPSEEK"
ANTHROPIC: Final = "ANTHROPIC"
E5_PROVIDERS: Final = (DEEPSEEK, ANTHROPIC)
PROVIDER_COUNT: Final = 2

DEEPSEEK_TECHNICAL_REVIEW: Final = "DEEPSEEK_TECHNICAL_REVIEW"
CLAUDE_L1_ESCALATION_REVIEW: Final = "CLAUDE_L1_ESCALATION_REVIEW"
CLAUDE_L2_ESCALATION_REVIEW: Final = "CLAUDE_L2_ESCALATION_REVIEW"
E5_INVOCATION_ROLES: Final = (
    DEEPSEEK_TECHNICAL_REVIEW,
    CLAUDE_L1_ESCALATION_REVIEW,
    CLAUDE_L2_ESCALATION_REVIEW,
)
INVOCATION_ROLE_COUNT: Final = 3

HOLD_PROVIDER_TIMEOUT: Final = "HOLD_PROVIDER_TIMEOUT"
HOLD_PROVIDER_UNAVAILABLE: Final = "HOLD_PROVIDER_UNAVAILABLE"
HOLD_PROVIDER_CONFIGURATION: Final = "HOLD_PROVIDER_CONFIGURATION"
HOLD_MODEL_BINDING: Final = "HOLD_MODEL_BINDING"
HOLD_INVALID_RESPONSE: Final = "HOLD_INVALID_RESPONSE"
HOLD_TOKEN_LIMIT: Final = "HOLD_TOKEN_LIMIT"
HOLD_BUDGET_BLOCKED: Final = "HOLD_BUDGET_BLOCKED"
HOLD_ESCALATION_INCOMPLETE: Final = "HOLD_ESCALATION_INCOMPLETE"
E5_D8_FAILURE_CODES: Final = (
    HOLD_PROVIDER_TIMEOUT,
    HOLD_PROVIDER_UNAVAILABLE,
    HOLD_PROVIDER_CONFIGURATION,
    HOLD_MODEL_BINDING,
    HOLD_INVALID_RESPONSE,
    HOLD_TOKEN_LIMIT,
    HOLD_BUDGET_BLOCKED,
    HOLD_ESCALATION_INCOMPLETE,
)
D8_FAILURE_CODE_COUNT: Final = 8

PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED: Final = (
    "PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED"
)
PASS_L0_NO_CLAUDE_REQUIRED: Final = "PASS_L0_NO_CLAUDE_REQUIRED"
PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED: Final = (
    "PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED"
)
E5_PROVIDER_INVOCATION_SUCCESS_CODES: Final = (
    PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED,
    PASS_L0_NO_CLAUDE_REQUIRED,
    PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED,
)
SUCCESS_CODE_COUNT: Final = 3

PROVIDER_FAILURE_DEFAULT: Final = "FAIL_CLOSED_NO_PUBLICATION"

SUCCESS: Final = "SUCCESS"
TIMEOUT: Final = "TIMEOUT"
TEMPORARILY_UNAVAILABLE: Final = "TEMPORARILY_UNAVAILABLE"
AUTHENTICATION_OR_PERMISSION_FAILURE: Final = (
    "AUTHENTICATION_OR_PERMISSION_FAILURE"
)
UNSUPPORTED_MODEL: Final = "UNSUPPORTED_MODEL"
MALFORMED_OR_SCHEMA_INVALID_RESPONSE: Final = (
    "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"
)
TOKEN_LIMIT_EXCEEDED: Final = "TOKEN_LIMIT_EXCEEDED"
BUDGET_BLOCKED: Final = "BUDGET_BLOCKED"
E5_TRANSPORT_OUTCOME_CODES: Final = (
    SUCCESS,
    TIMEOUT,
    TEMPORARILY_UNAVAILABLE,
    AUTHENTICATION_OR_PERMISSION_FAILURE,
    UNSUPPORTED_MODEL,
    MALFORMED_OR_SCHEMA_INVALID_RESPONSE,
    TOKEN_LIMIT_EXCEEDED,
    BUDGET_BLOCKED,
)
TRANSPORT_OUTCOME_CODE_COUNT: Final = 8
MAXIMUM_PROVIDER_ATTEMPTS: Final = 1
RETRY_COUNT: Final = 0

_ERROR: Final = "invalid E5 provider invocation boundary"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_MAPPING_PROXY_TYPE: Final = type(MappingProxyType({}))
_CLAUDE_REVIEW_MAPPING_KEYS: Final = frozenset(
    (
        "review_version",
        "provider_binding_sha256",
        "payload_sha256",
        "route_sha256",
        "route",
        "model_id",
        "review_summary",
        "reviewed_evidence_fields",
        "review_sha256",
    )
)
_CREDENTIAL_KEYS: Final = frozenset(
    (
        "api_key",
        "authorization",
        "authorization_header",
        "credential",
        "credentials",
        "account_identifier",
        "secret",
        "token_secret",
    )
)
_TRANSPORT_FAILURE_MAP: Final = {
    TIMEOUT: HOLD_PROVIDER_TIMEOUT,
    TEMPORARILY_UNAVAILABLE: HOLD_PROVIDER_UNAVAILABLE,
    AUTHENTICATION_OR_PERMISSION_FAILURE: HOLD_PROVIDER_CONFIGURATION,
    UNSUPPORTED_MODEL: HOLD_MODEL_BINDING,
    MALFORMED_OR_SCHEMA_INVALID_RESPONSE: HOLD_INVALID_RESPONSE,
    TOKEN_LIMIT_EXCEEDED: HOLD_TOKEN_LIMIT,
    BUDGET_BLOCKED: HOLD_BUDGET_BLOCKED,
}
_PRE_NETWORK_CONFIGURATION_DETAIL_CODES: Final = (
    "RUNTIME_CONFIGURATION_INVALID",
    "CREDENTIAL_MISSING",
    "CREDENTIAL_EMPTY",
    "REQUEST_CONTRACT_INVALID",
    "REQUEST_SERIALIZATION_FAILED",
    "HTTP_CLIENT_CONFIGURATION_INVALID",
)
_PRE_NETWORK_UNAVAILABLE_DETAIL_CODES: Final = (
    "HTTP_CLIENT_TEMPORARILY_UNAVAILABLE_BEFORE_SEND",
    "PRE_SEND_CLIENT_FAILURE",
)


@dataclass(frozen=True, slots=True)
class E5ProviderPreNetworkFailureV1(Exception):
    failure_version: str
    failure_classification: str
    safe_detail_code: str

    def __post_init__(self) -> None:
        try:
            _require(
                type(self.failure_version) is str
                and self.failure_version
                == E5_PROVIDER_PRE_NETWORK_FAILURE_V1_VERSION
            )
            _require(type(self.failure_classification) is str)
            _require(type(self.safe_detail_code) is str)
            if self.safe_detail_code in _PRE_NETWORK_CONFIGURATION_DETAIL_CODES:
                _require(
                    self.failure_classification
                    == HOLD_PROVIDER_CONFIGURATION
                )
            elif self.safe_detail_code in _PRE_NETWORK_UNAVAILABLE_DETAIL_CODES:
                _require(
                    self.failure_classification == HOLD_PROVIDER_UNAVAILABLE
                )
            else:
                _fail()
        except Exception:
            _fail()


def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _canonical_json(mapping: Mapping[str, object]) -> str:
    try:
        return json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except Exception:
        _fail()


def _hash_mapping(mapping: Mapping[str, object]) -> str:
    return sha256(_canonical_json(mapping).encode("utf-8")).hexdigest()


def _valid_sha256(value: object) -> bool:
    return type(value) is str and _SHA256_PATTERN.fullmatch(value) is not None


def _active_binding():
    binding = get_owner_frozen_e5_provider_model_price_binding_v4()
    _require(
        binding.binding_version == E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION
    )
    _require(binding.binding_sha256 == ACTIVE_PROVIDER_BINDING_SHA256)
    _require(binding.deepseek_model_id == "deepseek-v4-pro")
    _require(binding.deepseek_input_hard_limit_tokens == 4000)
    _require(binding.deepseek_output_hard_limit_tokens == 500)
    _require(binding.deepseek_provider_attempts == 1)
    _require(binding.deepseek_retry_count == 0)
    _require(binding.deepseek_timeout_seconds == 60)
    _require(binding.claude_l1_model_id == "claude-opus-5")
    _require(binding.claude_l1_input_hard_limit_tokens == 4000)
    _require(binding.claude_l1_output_hard_limit_tokens == 500)
    _require(binding.claude_l1_timeout_seconds == 10)
    _require(binding.claude_l1_provider_attempts == 1)
    _require(binding.claude_l1_retry_count == 0)
    _require(binding.claude_l1_max_cost_micro_usd == 32500)
    _require(binding.claude_l2_model_id == "claude-fable-5")
    _require(binding.claude_l2_input_hard_limit_tokens == 6000)
    _require(binding.claude_l2_output_hard_limit_tokens == 800)
    _require(binding.claude_l2_timeout_seconds == 20)
    _require(binding.claude_l2_provider_attempts == 1)
    _require(binding.claude_l2_retry_count == 0)
    _require(binding.claude_l2_max_cost_micro_usd == 100000)
    _require(binding.latest_alias_allowed is False)
    _require(binding.cross_provider_substitution_allowed is False)
    _require(binding.malformed_response_prompt_repair_allowed is False)
    _require(binding.stale_result_reuse_allowed is False)
    _require(binding.same_invocation_retry_allowed is False)
    _require(binding.deepseek_thinking_mode == "disabled")
    _require(binding.deepseek_reasoning_effort == "none")
    _require(binding.claude_l1_thinking_mode == "disabled")
    _require(binding.claude_l1_effort == "high")
    _require(binding.claude_l2_thinking_mode == "always_on_adaptive")
    _require(binding.claude_l2_effort == "high")
    _require(
        binding.billed_cost_semantics
        == "LOCALLY_DERIVED_DETERMINISTIC_COST_USING_VALIDATED_PROVIDER_"
        "USAGE_AND_OWNER_FROZEN_BINDING_PRICES"
    )
    _require(
        binding.claude_cache_input_cost_policy
        == "CACHE_NOT_REQUESTED_REQUIRE_CACHE_CREATION_AND_CACHE_READ_"
        "COUNTS_BOTH_ZERO_UNTIL_DISTINCT_CACHE_PRICES_ARE_OWNER_FROZEN"
    )
    _require(
        binding.provider_output_limit_activation_status
        == "NON_PRODUCTION_CANARY_CANDIDATES_NOT_PRODUCTION_PROVEN"
    )
    return binding


def _validate_active_payload(value: object) -> E5TechnicalReviewPayloadV1:
    _require(type(value) is E5TechnicalReviewPayloadV1)
    value.__post_init__()
    _require(value.provider_binding_sha256 == _active_binding().binding_sha256)
    return value


def _validate_json_value(value: object) -> None:
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is list:
        for item in value:
            _validate_json_value(item)
        return
    if type(value) is dict:
        _require(all(type(key) is str for key in value))
        for item in value.values():
            _validate_json_value(item)
        return
    _fail()


def _freeze_json_mapping(mapping: Mapping[str, object]):
    _require(type(mapping) is dict)
    _validate_json_value(mapping)
    return MappingProxyType(
        {
            key: _freeze_json_value(mapping[key])
            for key in sorted(mapping)
        }
    )


def _freeze_json_value(value: object) -> object:
    if type(value) is dict:
        return _freeze_json_mapping(value)
    if type(value) is list:
        return tuple(_freeze_json_value(item) for item in value)
    _require(value is None or type(value) in (str, int, bool))
    return value


def _thaw_json_value(value: object) -> object:
    if type(value) is _MAPPING_PROXY_TYPE:
        return {
            key: _thaw_json_value(item)
            for key, item in value.items()
        }
    if type(value) is tuple:
        return [_thaw_json_value(item) for item in value]
    _require(value is None or type(value) in (str, int, bool))
    return value


def _contains_credential_key(value: object) -> bool:
    if type(value) is dict:
        if any(key.casefold() in _CREDENTIAL_KEYS for key in value):
            return True
        return any(_contains_credential_key(item) for item in value.values())
    if type(value) is list:
        return any(_contains_credential_key(item) for item in value)
    return False


def _request_preimage(request: "E5ProviderRequestV1") -> dict[str, object]:
    return {
        field.name: getattr(request, field.name)
        for field in fields(E5ProviderRequestV1)
        if field.name != "request_sha256"
    }


def _role_profile(invocation_role: str) -> tuple[object, ...]:
    binding = _active_binding()
    if invocation_role == DEEPSEEK_TECHNICAL_REVIEW:
        return (
            DEEPSEEK,
            None,
            binding.deepseek_model_id,
            binding.deepseek_input_hard_limit_tokens,
            binding.deepseek_output_hard_limit_tokens,
            binding.deepseek_timeout_seconds,
            binding.deepseek_provider_attempts,
            binding.deepseek_retry_count,
            0,
            E5_DEEPSEEK_STRUCTURED_REVIEW_VERSION,
        )
    if invocation_role == CLAUDE_L1_ESCALATION_REVIEW:
        return (
            ANTHROPIC,
            L1,
            binding.claude_l1_model_id,
            binding.claude_l1_input_hard_limit_tokens,
            binding.claude_l1_output_hard_limit_tokens,
            binding.claude_l1_timeout_seconds,
            binding.claude_l1_provider_attempts,
            binding.claude_l1_retry_count,
            binding.claude_l1_max_cost_micro_usd,
            E5_CLAUDE_ESCALATION_REVIEW_VERSION,
        )
    _require(invocation_role == CLAUDE_L2_ESCALATION_REVIEW)
    return (
        ANTHROPIC,
        L2,
        binding.claude_l2_model_id,
        binding.claude_l2_input_hard_limit_tokens,
        binding.claude_l2_output_hard_limit_tokens,
        binding.claude_l2_timeout_seconds,
        binding.claude_l2_provider_attempts,
        binding.claude_l2_retry_count,
        binding.claude_l2_max_cost_micro_usd,
        E5_CLAUDE_ESCALATION_REVIEW_VERSION,
    )


@dataclass(frozen=True, slots=True)
class E5ProviderRequestV1:
    request_version: str
    provider_binding_sha256: str
    provider: str
    invocation_role: str
    payload_sha256: str
    upstream_identity_sha256: str
    route: str | None
    model_id: str
    input_hard_limit_tokens: int
    output_hard_limit_tokens: int
    timeout_seconds: int | None
    provider_attempts: int
    retry_count: int
    maximum_review_cost_micro_usd: int
    expected_response_schema_version: str
    canonical_input_json: str
    request_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(self.request_version == E5_PROVIDER_REQUEST_VERSION)
            _require(self.provider_binding_sha256 == _active_binding().binding_sha256)
            _require(type(self.invocation_role) is str)
            _require(self.invocation_role in E5_INVOCATION_ROLES)
            expected = _role_profile(self.invocation_role)
            actual = (
                self.provider,
                self.route,
                self.model_id,
                self.input_hard_limit_tokens,
                self.output_hard_limit_tokens,
                self.timeout_seconds,
                self.provider_attempts,
                self.retry_count,
                self.maximum_review_cost_micro_usd,
                self.expected_response_schema_version,
            )
            _require(actual == expected)
            _require(_valid_sha256(self.payload_sha256))
            _require(_valid_sha256(self.upstream_identity_sha256))
            for value in (
                self.input_hard_limit_tokens,
                self.output_hard_limit_tokens,
                self.provider_attempts,
                self.retry_count,
                self.maximum_review_cost_micro_usd,
            ):
                _require(type(value) is int and value >= 0)
            _require(
                self.timeout_seconds is None
                or (type(self.timeout_seconds) is int and self.timeout_seconds > 0)
            )
            _require(self.provider_attempts == 1 and self.retry_count == 0)
            _require(type(self.canonical_input_json) is str)
            parsed = json.loads(self.canonical_input_json)
            _require(type(parsed) is dict)
            _validate_json_value(parsed)
            _require(_canonical_json(parsed) == self.canonical_input_json)
            _require(not _contains_credential_key(parsed))
            if self.invocation_role == DEEPSEEK_TECHNICAL_REVIEW:
                _require(self.upstream_identity_sha256 == self.payload_sha256)
                _require(parsed.get("payload_sha256") == self.payload_sha256)
            else:
                _require(self.upstream_identity_sha256 != self.payload_sha256)
                _require(
                    frozenset(parsed)
                    == frozenset(
                        (
                            "payload",
                            "deepseek_review",
                            "deepseek_adjudication",
                            "claude_route_result",
                        )
                    )
                )
                _require(
                    parsed["payload"].get("payload_sha256")
                    == self.payload_sha256
                )
                _require(
                    parsed["claude_route_result"].get("route_sha256")
                    == self.upstream_identity_sha256
                )
            _require(_valid_sha256(self.request_sha256))
            _require(
                self.request_sha256 == _hash_mapping(_request_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {**_request_preimage(self), "request_sha256": self.request_sha256}

    def canonical_request_json(self) -> str:
        return _canonical_json(_request_preimage(self))


def _build_request(data: dict[str, object]) -> E5ProviderRequestV1:
    temporary = object.__new__(E5ProviderRequestV1)
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E5ProviderRequestV1(
        **data,
        request_sha256=_hash_mapping(_request_preimage(temporary)),
    )


def _validate_deepseek_preflight(
    *,
    payload: E5TechnicalReviewPayloadV1,
    token_preflight: object,
) -> E5TechnicalReviewTokenPreflightResultV1:
    _require(type(token_preflight) is E5TechnicalReviewTokenPreflightResultV1)
    token_preflight.__post_init__()
    binding = _active_binding()
    _require(token_preflight.payload_sha256 == payload.payload_sha256)
    _require(token_preflight.model_id == binding.deepseek_model_id)
    _require(
        token_preflight.input_hard_limit_tokens
        == binding.deepseek_input_hard_limit_tokens
    )
    _require(
        token_preflight.output_hard_limit_tokens
        == binding.deepseek_output_hard_limit_tokens
    )
    return token_preflight


def build_e5_deepseek_provider_request_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    token_preflight: E5TechnicalReviewTokenPreflightResultV1,
) -> E5ProviderRequestV1:
    try:
        verified_payload = _validate_active_payload(payload)
        verified_preflight = _validate_deepseek_preflight(
            payload=verified_payload,
            token_preflight=token_preflight,
        )
        _require(verified_preflight.within_limits is True)
        _require(verified_preflight.decision_code == PASS_TOKEN_BUDGET)
        profile = _role_profile(DEEPSEEK_TECHNICAL_REVIEW)
        data: dict[str, object] = {
            "request_version": E5_PROVIDER_REQUEST_VERSION,
            "provider_binding_sha256": verified_payload.provider_binding_sha256,
            "provider": profile[0],
            "invocation_role": DEEPSEEK_TECHNICAL_REVIEW,
            "payload_sha256": verified_payload.payload_sha256,
            "upstream_identity_sha256": verified_payload.payload_sha256,
            "route": profile[1],
            "model_id": profile[2],
            "input_hard_limit_tokens": profile[3],
            "output_hard_limit_tokens": profile[4],
            "timeout_seconds": profile[5],
            "provider_attempts": profile[6],
            "retry_count": profile[7],
            "maximum_review_cost_micro_usd": profile[8],
            "expected_response_schema_version": profile[9],
            "canonical_input_json": _canonical_json(
                verified_payload.to_mapping()
            ),
        }
        return _build_request(data)
    except Exception:
        _fail()


def _validate_claude_lineage(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deepseek_review: object,
    deepseek_adjudication: object,
    route_result: object,
) -> tuple[
    E5DeepSeekStructuredReviewV1,
    E5DeepSeekTechnicalReviewAdjudicationV1,
    E5ClaudeReviewRouteResultV1,
]:
    _require(type(deepseek_review) is E5DeepSeekStructuredReviewV1)
    deepseek_review.__post_init__()
    _require(
        type(deepseek_adjudication)
        is E5DeepSeekTechnicalReviewAdjudicationV1
    )
    deepseek_adjudication.__post_init__()
    _require(type(route_result) is E5ClaudeReviewRouteResultV1)
    route_result.__post_init__()
    _require(deepseek_review.payload_sha256 == payload.payload_sha256)
    _require(deepseek_adjudication.payload_sha256 == payload.payload_sha256)
    _require(route_result.payload_sha256 == payload.payload_sha256)
    _require(
        deepseek_adjudication.review_sha256 == deepseek_review.review_sha256
    )
    _require(route_result.deepseek_review_sha256 == deepseek_review.review_sha256)
    _require(
        route_result.deepseek_adjudication_sha256
        == deepseek_adjudication.adjudication_sha256
    )
    _require(route_result.provider_binding_sha256 == payload.provider_binding_sha256)
    return deepseek_review, deepseek_adjudication, route_result


def _validate_claude_preflight(
    *,
    route_result: E5ClaudeReviewRouteResultV1,
    token_preflight: object,
) -> E5ClaudeTokenPreflightResultV1:
    _require(type(token_preflight) is E5ClaudeTokenPreflightResultV1)
    token_preflight.__post_init__()
    _require(token_preflight.provider_binding_sha256 == ACTIVE_PROVIDER_BINDING_SHA256)
    _require(token_preflight.payload_sha256 == route_result.payload_sha256)
    _require(token_preflight.route_sha256 == route_result.route_sha256)
    _require(token_preflight.route == route_result.route)
    return token_preflight


def build_e5_claude_provider_request_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deepseek_review: E5DeepSeekStructuredReviewV1,
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1,
    route_result: E5ClaudeReviewRouteResultV1,
    token_preflight: E5ClaudeTokenPreflightResultV1,
) -> E5ProviderRequestV1:
    try:
        verified_payload = _validate_active_payload(payload)
        review, adjudication, route = _validate_claude_lineage(
            payload=verified_payload,
            deepseek_review=deepseek_review,
            deepseek_adjudication=deepseek_adjudication,
            route_result=route_result,
        )
        preflight = _validate_claude_preflight(
            route_result=route,
            token_preflight=token_preflight,
        )
        _require(
            route.decision_code
            in (
                ROUTE_L1_CLAUDE_REVIEW_REQUIRED,
                ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED,
            )
        )
        _require(route.claude_required is True and route.route in (L1, L2))
        _require(preflight.within_limits is True)
        _require(preflight.decision_code == PASS_CLAUDE_TOKEN_BUDGET)
        role = (
            CLAUDE_L1_ESCALATION_REVIEW
            if route.route == L1
            else CLAUDE_L2_ESCALATION_REVIEW
        )
        profile = _role_profile(role)
        _require(route.model_id == profile[2])
        _require(preflight.model_id == profile[2])
        _require(route.input_hard_limit_tokens == profile[3])
        _require(route.output_hard_limit_tokens == profile[4])
        canonical_input = {
            "payload": verified_payload.to_mapping(),
            "deepseek_review": review.to_mapping(),
            "deepseek_adjudication": adjudication.to_mapping(),
            "claude_route_result": route.to_mapping(),
        }
        data: dict[str, object] = {
            "request_version": E5_PROVIDER_REQUEST_VERSION,
            "provider_binding_sha256": verified_payload.provider_binding_sha256,
            "provider": profile[0],
            "invocation_role": role,
            "payload_sha256": verified_payload.payload_sha256,
            "upstream_identity_sha256": route.route_sha256,
            "route": profile[1],
            "model_id": profile[2],
            "input_hard_limit_tokens": profile[3],
            "output_hard_limit_tokens": profile[4],
            "timeout_seconds": profile[5],
            "provider_attempts": profile[6],
            "retry_count": profile[7],
            "maximum_review_cost_micro_usd": profile[8],
            "expected_response_schema_version": profile[9],
            "canonical_input_json": _canonical_json(canonical_input),
        }
        return _build_request(data)
    except Exception:
        _fail()


def _observation_preimage(
    observation: "E5ProviderAttemptObservationV1",
) -> dict[str, object]:
    response = (
        None
        if observation.response_mapping is None
        else _thaw_json_value(observation.response_mapping)
    )
    return {
        "observation_version": observation.observation_version,
        "request_sha256": observation.request_sha256,
        "provider": observation.provider,
        "model_id": observation.model_id,
        "attempt_number": observation.attempt_number,
        "transport_outcome": observation.transport_outcome,
        "response_mapping": response,
        "response_digest_sha256": observation.response_digest_sha256,
        "measured_input_tokens": observation.measured_input_tokens,
        "measured_output_tokens": observation.measured_output_tokens,
        "billed_cost_micro_usd": observation.billed_cost_micro_usd,
    }


@dataclass(frozen=True, slots=True)
class E5ProviderAttemptObservationV1:
    observation_version: str
    request_sha256: str
    provider: str
    model_id: str
    attempt_number: int
    transport_outcome: str
    response_mapping: Mapping[str, object] | None
    response_digest_sha256: str | None
    measured_input_tokens: int
    measured_output_tokens: int
    billed_cost_micro_usd: int
    observation_sha256: str

    def __post_init__(self) -> None:
        try:
            binding = _active_binding()
            _require(
                self.observation_version
                == E5_PROVIDER_ATTEMPT_OBSERVATION_VERSION
            )
            _require(_valid_sha256(self.request_sha256))
            _require(type(self.provider) is str and self.provider in E5_PROVIDERS)
            expected_models = (
                (binding.deepseek_model_id,)
                if self.provider == DEEPSEEK
                else (binding.claude_l1_model_id, binding.claude_l2_model_id)
            )
            _require(type(self.model_id) is str and self.model_id in expected_models)
            _require(type(self.attempt_number) is int and self.attempt_number == 1)
            _require(
                type(self.transport_outcome) is str
                and self.transport_outcome in E5_TRANSPORT_OUTCOME_CODES
            )
            for value in (
                self.measured_input_tokens,
                self.measured_output_tokens,
                self.billed_cost_micro_usd,
            ):
                _require(type(value) is int and value >= 0)
            if self.transport_outcome == SUCCESS:
                _require(type(self.response_mapping) is _MAPPING_PROXY_TYPE)
                thawed = _thaw_json_value(self.response_mapping)
                _require(type(thawed) is dict)
                _validate_json_value(thawed)
                _require(_valid_sha256(self.response_digest_sha256))
                _require(
                    self.response_digest_sha256 == _hash_mapping(thawed)
                )
            else:
                _require(self.response_mapping is None)
                _require(self.response_digest_sha256 is None)
            _require(_valid_sha256(self.observation_sha256))
            _require(
                self.observation_sha256
                == _hash_mapping(_observation_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_observation_preimage(self),
            "observation_sha256": self.observation_sha256,
        }

    def canonical_observation_json(self) -> str:
        return _canonical_json(_observation_preimage(self))


def build_e5_provider_attempt_observation_v1(
    *,
    request: E5ProviderRequestV1,
    transport_outcome: str,
    response_mapping: Mapping[str, object] | None,
    measured_input_tokens: int,
    measured_output_tokens: int,
    billed_cost_micro_usd: int,
    provider: str | None = None,
    model_id: str | None = None,
    request_sha256: str | None = None,
) -> E5ProviderAttemptObservationV1:
    try:
        _require(type(request) is E5ProviderRequestV1)
        request.__post_init__()
        _require(
            type(transport_outcome) is str
            and transport_outcome in E5_TRANSPORT_OUTCOME_CODES
        )
        frozen_response = (
            None
            if response_mapping is None
            else _freeze_json_mapping(response_mapping)
        )
        thawed = (
            None
            if frozen_response is None
            else _thaw_json_value(frozen_response)
        )
        response_digest = (
            None if thawed is None else _hash_mapping(thawed)
        )
        data: dict[str, object] = {
            "observation_version": E5_PROVIDER_ATTEMPT_OBSERVATION_VERSION,
            "request_sha256": (
                request.request_sha256
                if request_sha256 is None
                else request_sha256
            ),
            "provider": request.provider if provider is None else provider,
            "model_id": request.model_id if model_id is None else model_id,
            "attempt_number": 1,
            "transport_outcome": transport_outcome,
            "response_mapping": frozen_response,
            "response_digest_sha256": response_digest,
            "measured_input_tokens": measured_input_tokens,
            "measured_output_tokens": measured_output_tokens,
            "billed_cost_micro_usd": billed_cost_micro_usd,
        }
        temporary = object.__new__(E5ProviderAttemptObservationV1)
        for name, value in data.items():
            object.__setattr__(temporary, name, value)
        return E5ProviderAttemptObservationV1(
            **data,
            observation_sha256=_hash_mapping(_observation_preimage(temporary)),
        )
    except Exception:
        _fail()


def _validate_review_summary(value: object) -> None:
    _require(type(value) is str and bool(value))
    _require(value.strip() == value)
    _require(not any(unicodedata.category(character) == "Cc" for character in value))


def _validate_reviewed_fields(value: object) -> None:
    _require(type(value) is tuple and bool(value))
    _require(all(type(item) is str for item in value))
    _require(len(set(value)) == len(value))
    allowed = E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS
    _require(all(item in allowed for item in value))
    _require(tuple(sorted(value, key=allowed.index)) == value)


def _claude_review_preimage(
    review: "E5ClaudeEscalationReviewV1",
) -> dict[str, object]:
    return {
        "review_version": review.review_version,
        "provider_binding_sha256": review.provider_binding_sha256,
        "payload_sha256": review.payload_sha256,
        "route_sha256": review.route_sha256,
        "route": review.route,
        "model_id": review.model_id,
        "review_summary": review.review_summary,
        "reviewed_evidence_fields": list(review.reviewed_evidence_fields),
    }


@dataclass(frozen=True, slots=True)
class E5ClaudeEscalationReviewV1:
    review_version: str
    provider_binding_sha256: str
    payload_sha256: str
    route_sha256: str
    route: str
    model_id: str
    review_summary: str
    reviewed_evidence_fields: tuple[str, ...]
    review_sha256: str

    def __post_init__(self) -> None:
        try:
            binding = _active_binding()
            _require(self.review_version == E5_CLAUDE_ESCALATION_REVIEW_VERSION)
            _require(self.provider_binding_sha256 == binding.binding_sha256)
            _require(_valid_sha256(self.payload_sha256))
            _require(_valid_sha256(self.route_sha256))
            _require(type(self.route) is str and self.route in (L1, L2))
            expected_model = (
                binding.claude_l1_model_id
                if self.route == L1
                else binding.claude_l2_model_id
            )
            _require(type(self.model_id) is str and self.model_id == expected_model)
            _validate_review_summary(self.review_summary)
            _validate_reviewed_fields(self.reviewed_evidence_fields)
            _require(_valid_sha256(self.review_sha256))
            _require(
                self.review_sha256
                == _hash_mapping(_claude_review_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_claude_review_preimage(self),
            "review_sha256": self.review_sha256,
        }

    def canonical_review_json(self) -> str:
        return _canonical_json(_claude_review_preimage(self))


def reconstruct_e5_claude_escalation_review_v1(
    mapping: Mapping[str, object],
) -> E5ClaudeEscalationReviewV1:
    try:
        _require(type(mapping) is dict)
        _require(frozenset(mapping) == _CLAUDE_REVIEW_MAPPING_KEYS)
        _require(type(mapping["reviewed_evidence_fields"]) is list)
        return E5ClaudeEscalationReviewV1(
            review_version=mapping["review_version"],
            provider_binding_sha256=mapping["provider_binding_sha256"],
            payload_sha256=mapping["payload_sha256"],
            route_sha256=mapping["route_sha256"],
            route=mapping["route"],
            model_id=mapping["model_id"],
            review_summary=mapping["review_summary"],
            reviewed_evidence_fields=tuple(mapping["reviewed_evidence_fields"]),
            review_sha256=mapping["review_sha256"],
        )
    except Exception:
        _fail()


def _result_preimage(
    result: "E5ProviderInvocationResultV1",
) -> dict[str, object]:
    return {
        field.name: getattr(result, field.name)
        for field in fields(E5ProviderInvocationResultV1)
        if field.name != "result_sha256"
    }


@dataclass(frozen=True, slots=True)
class E5ProviderInvocationResultV1:
    result_version: str
    provider_binding_sha256: str
    payload_sha256: str
    route_sha256: str | None
    provider: str | None
    invocation_role: str | None
    model_id: str | None
    request_sha256: str | None
    transport_invoked: bool
    provider_attempt_count: int
    retry_count: int
    underlying_failure_code: str | None
    final_result_code: str
    accepted_response_sha256: str | None
    response_digest_sha256: str | None
    publication_allowed: bool
    telegram_send_allowed: bool
    slot_mutation_allowed: bool
    pair_lock_mutation_allowed: bool
    retry_allowed: bool
    fallback_allowed: bool
    stale_result_reuse_allowed: bool
    result_sha256: str

    def __post_init__(self) -> None:
        try:
            binding = _active_binding()
            _require(self.result_version == E5_PROVIDER_INVOCATION_RESULT_VERSION)
            _require(self.provider_binding_sha256 == binding.binding_sha256)
            _require(_valid_sha256(self.payload_sha256))
            _require(self.route_sha256 is None or _valid_sha256(self.route_sha256))
            _require(self.provider is None or self.provider in E5_PROVIDERS)
            _require(
                self.invocation_role is None
                or self.invocation_role in E5_INVOCATION_ROLES
            )
            _require(type(self.model_id) is str or self.model_id is None)
            _require(self.request_sha256 is None or _valid_sha256(self.request_sha256))
            _require(type(self.transport_invoked) is bool)
            _require(
                type(self.provider_attempt_count) is int
                and self.provider_attempt_count in (0, 1)
            )
            _require(type(self.retry_count) is int and self.retry_count == 0)
            _require(
                self.transport_invoked == (self.provider_attempt_count == 1)
            )
            _require(
                (self.request_sha256 is not None) == self.transport_invoked
            )
            _require(
                self.underlying_failure_code is None
                or self.underlying_failure_code in E5_D8_FAILURE_CODES
            )
            _require(
                self.final_result_code
                in (*E5_D8_FAILURE_CODES, *E5_PROVIDER_INVOCATION_SUCCESS_CODES)
            )
            _require(
                self.accepted_response_sha256 is None
                or _valid_sha256(self.accepted_response_sha256)
            )
            _require(
                self.response_digest_sha256 is None
                or _valid_sha256(self.response_digest_sha256)
            )
            for authority in (
                self.publication_allowed,
                self.telegram_send_allowed,
                self.slot_mutation_allowed,
                self.pair_lock_mutation_allowed,
                self.retry_allowed,
                self.fallback_allowed,
                self.stale_result_reuse_allowed,
            ):
                _require(type(authority) is bool and authority is False)
            if self.final_result_code == PASS_L0_NO_CLAUDE_REQUIRED:
                _require(self.route_sha256 is not None)
                _require(self.provider is None)
                _require(self.invocation_role is None)
                _require(self.model_id is None)
                _require(self.transport_invoked is False)
                _require(self.underlying_failure_code is None)
                _require(self.accepted_response_sha256 is None)
                _require(self.response_digest_sha256 is None)
            elif self.final_result_code in (
                PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED,
                PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED,
            ):
                _require(self.transport_invoked is True)
                _require(self.underlying_failure_code is None)
                _require(_valid_sha256(self.accepted_response_sha256))
                _require(_valid_sha256(self.response_digest_sha256))
                if (
                    self.final_result_code
                    == PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED
                ):
                    _require(
                        self.invocation_role == DEEPSEEK_TECHNICAL_REVIEW
                    )
                else:
                    _require(
                        self.invocation_role
                        in (
                            CLAUDE_L1_ESCALATION_REVIEW,
                            CLAUDE_L2_ESCALATION_REVIEW,
                        )
                    )
            else:
                _require(self.underlying_failure_code in E5_D8_FAILURE_CODES)
                _require(self.accepted_response_sha256 is None)
            if self.invocation_role == DEEPSEEK_TECHNICAL_REVIEW:
                _require(self.route_sha256 is None)
                _require(self.provider == DEEPSEEK)
                _require(self.model_id == binding.deepseek_model_id)
            elif self.invocation_role == CLAUDE_L1_ESCALATION_REVIEW:
                _require(self.route_sha256 is not None)
                _require(self.provider == ANTHROPIC)
                _require(self.model_id == binding.claude_l1_model_id)
            elif self.invocation_role == CLAUDE_L2_ESCALATION_REVIEW:
                _require(self.route_sha256 is not None)
                _require(self.provider == ANTHROPIC)
                _require(self.model_id == binding.claude_l2_model_id)
            _require(_valid_sha256(self.result_sha256))
            _require(self.result_sha256 == _hash_mapping(_result_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {**_result_preimage(self), "result_sha256": self.result_sha256}

    def canonical_result_json(self) -> str:
        return _canonical_json(_result_preimage(self))


def _execution_preimage(
    execution: "E5ProviderAcceptedResponseExecutionV1",
) -> dict[str, object]:
    return {
        "execution_version": execution.execution_version,
        "invocation_result": execution.invocation_result.to_mapping(),
        "accepted_deepseek_review": (
            None
            if execution.accepted_deepseek_review is None
            else execution.accepted_deepseek_review.to_mapping()
        ),
        "accepted_claude_review": (
            None
            if execution.accepted_claude_review is None
            else execution.accepted_claude_review.to_mapping()
        ),
    }


@dataclass(frozen=True, slots=True)
class E5ProviderAcceptedResponseExecutionV1:
    execution_version: str
    invocation_result: E5ProviderInvocationResultV1
    accepted_deepseek_review: E5DeepSeekStructuredReviewV1 | None
    accepted_claude_review: E5ClaudeEscalationReviewV1 | None
    execution_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                self.execution_version
                == E5_PROVIDER_ACCEPTED_RESPONSE_EXECUTION_VERSION
            )
            _require(type(self.invocation_result) is E5ProviderInvocationResultV1)
            self.invocation_result.__post_init__()
            _require(
                not (
                    self.accepted_deepseek_review is not None
                    and self.accepted_claude_review is not None
                )
            )
            result = self.invocation_result
            if (
                result.final_result_code
                == PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED
            ):
                _require(
                    type(self.accepted_deepseek_review)
                    is E5DeepSeekStructuredReviewV1
                )
                _require(self.accepted_claude_review is None)
                review = self.accepted_deepseek_review
                review.__post_init__()
                _require(result.provider == DEEPSEEK)
                _require(result.invocation_role == DEEPSEEK_TECHNICAL_REVIEW)
                _require(result.route_sha256 is None)
                _require(result.request_sha256 is not None)
                _require(result.response_digest_sha256 is not None)
                _require(review.payload_sha256 == result.payload_sha256)
                _require(review.model_id == result.model_id)
                _require(review.review_sha256 == result.accepted_response_sha256)
            elif (
                result.final_result_code
                == PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED
            ):
                _require(self.accepted_deepseek_review is None)
                _require(
                    type(self.accepted_claude_review)
                    is E5ClaudeEscalationReviewV1
                )
                review = self.accepted_claude_review
                review.__post_init__()
                _require(result.provider == ANTHROPIC)
                _require(
                    result.invocation_role
                    in (
                        CLAUDE_L1_ESCALATION_REVIEW,
                        CLAUDE_L2_ESCALATION_REVIEW,
                    )
                )
                _require(result.route_sha256 is not None)
                _require(result.request_sha256 is not None)
                _require(result.response_digest_sha256 is not None)
                _require(review.provider_binding_sha256 == result.provider_binding_sha256)
                _require(review.payload_sha256 == result.payload_sha256)
                _require(review.route_sha256 == result.route_sha256)
                _require(review.model_id == result.model_id)
                _require(review.review_sha256 == result.accepted_response_sha256)
            else:
                _require(self.accepted_deepseek_review is None)
                _require(self.accepted_claude_review is None)
                _require(result.accepted_response_sha256 is None)
            _require(_valid_sha256(self.execution_sha256))
            _require(
                self.execution_sha256
                == _hash_mapping(_execution_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_execution_preimage(self),
            "execution_sha256": self.execution_sha256,
        }

    def canonical_execution_json(self) -> str:
        return _canonical_json(_execution_preimage(self))


def _build_execution(
    *,
    invocation_result: E5ProviderInvocationResultV1,
    accepted_deepseek_review: E5DeepSeekStructuredReviewV1 | None = None,
    accepted_claude_review: E5ClaudeEscalationReviewV1 | None = None,
) -> E5ProviderAcceptedResponseExecutionV1:
    data: dict[str, object] = {
        "execution_version": E5_PROVIDER_ACCEPTED_RESPONSE_EXECUTION_VERSION,
        "invocation_result": invocation_result,
        "accepted_deepseek_review": accepted_deepseek_review,
        "accepted_claude_review": accepted_claude_review,
    }
    temporary = object.__new__(E5ProviderAcceptedResponseExecutionV1)
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E5ProviderAcceptedResponseExecutionV1(
        **data,
        execution_sha256=_hash_mapping(_execution_preimage(temporary)),
    )


def _build_result(
    *,
    payload_sha256: str,
    route_sha256: str | None,
    provider: str | None,
    invocation_role: str | None,
    model_id: str | None,
    request_sha256: str | None,
    transport_invoked: bool,
    underlying_failure_code: str | None,
    final_result_code: str,
    accepted_response_sha256: str | None = None,
    response_digest_sha256: str | None = None,
) -> E5ProviderInvocationResultV1:
    data: dict[str, object] = {
        "result_version": E5_PROVIDER_INVOCATION_RESULT_VERSION,
        "provider_binding_sha256": ACTIVE_PROVIDER_BINDING_SHA256,
        "payload_sha256": payload_sha256,
        "route_sha256": route_sha256,
        "provider": provider,
        "invocation_role": invocation_role,
        "model_id": model_id,
        "request_sha256": request_sha256,
        "transport_invoked": transport_invoked,
        "provider_attempt_count": 1 if transport_invoked else 0,
        "retry_count": 0,
        "underlying_failure_code": underlying_failure_code,
        "final_result_code": final_result_code,
        "accepted_response_sha256": accepted_response_sha256,
        "response_digest_sha256": response_digest_sha256,
        "publication_allowed": False,
        "telegram_send_allowed": False,
        "slot_mutation_allowed": False,
        "pair_lock_mutation_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "stale_result_reuse_allowed": False,
    }
    temporary = object.__new__(E5ProviderInvocationResultV1)
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E5ProviderInvocationResultV1(
        **data,
        result_sha256=_hash_mapping(_result_preimage(temporary)),
    )


def _deepseek_result(
    *,
    payload: E5TechnicalReviewPayloadV1,
    request: E5ProviderRequestV1 | None,
    cause: str | None,
    final: str,
    accepted: str | None = None,
    response_digest: str | None = None,
) -> E5ProviderInvocationResultV1:
    binding = _active_binding()
    return _build_result(
        payload_sha256=payload.payload_sha256,
        route_sha256=None,
        provider=DEEPSEEK,
        invocation_role=DEEPSEEK_TECHNICAL_REVIEW,
        model_id=binding.deepseek_model_id,
        request_sha256=None if request is None else request.request_sha256,
        transport_invoked=request is not None,
        underlying_failure_code=cause,
        final_result_code=final,
        accepted_response_sha256=accepted,
        response_digest_sha256=response_digest,
    )


def _claude_result(
    *,
    payload: E5TechnicalReviewPayloadV1,
    route: E5ClaudeReviewRouteResultV1,
    request: E5ProviderRequestV1 | None,
    cause: str | None,
    final: str,
    accepted: str | None = None,
    response_digest: str | None = None,
) -> E5ProviderInvocationResultV1:
    if route.route == L0:
        provider = None
        role = None
        model = None
    else:
        provider = ANTHROPIC
        role = (
            CLAUDE_L1_ESCALATION_REVIEW
            if route.route == L1
            else CLAUDE_L2_ESCALATION_REVIEW
        )
        model = _role_profile(role)[2]
    return _build_result(
        payload_sha256=payload.payload_sha256,
        route_sha256=route.route_sha256,
        provider=provider,
        invocation_role=role,
        model_id=model,
        request_sha256=None if request is None else request.request_sha256,
        transport_invoked=request is not None,
        underlying_failure_code=cause,
        final_result_code=final,
        accepted_response_sha256=accepted,
        response_digest_sha256=response_digest,
    )


def _validate_observation_identity(
    *,
    observation: object,
    request: E5ProviderRequestV1,
) -> tuple[E5ProviderAttemptObservationV1 | None, str | None]:
    if type(observation) is not E5ProviderAttemptObservationV1:
        return None, HOLD_INVALID_RESPONSE
    if (
        observation.provider != request.provider
        or observation.model_id != request.model_id
    ):
        return None, HOLD_MODEL_BINDING
    try:
        observation.__post_init__()
    except Exception:
        return None, HOLD_INVALID_RESPONSE
    if observation.request_sha256 != request.request_sha256:
        return observation, HOLD_INVALID_RESPONSE
    return observation, None


def _execute_e5_deepseek_review_once_core_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    token_preflight: E5TechnicalReviewTokenPreflightResultV1,
    transport: Callable[[E5ProviderRequestV1], E5ProviderAttemptObservationV1],
) -> E5ProviderAcceptedResponseExecutionV1:
    try:
        verified_payload = _validate_active_payload(payload)
        preflight = _validate_deepseek_preflight(
            payload=verified_payload,
            token_preflight=token_preflight,
        )
        _require(callable(transport))
        if preflight.decision_code in (HOLD_INPUT_TOKEN_LIMIT, HOLD_OUTPUT_TOKEN_LIMIT):
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=None,
                    cause=HOLD_TOKEN_LIMIT,
                    final=HOLD_TOKEN_LIMIT,
                )
            )
        request = build_e5_deepseek_provider_request_v1(
            payload=verified_payload,
            token_preflight=preflight,
        )
        try:
            raw_observation = transport(request)
        except E5ProviderPreNetworkFailureV1 as failure:
            failure.__post_init__()
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=None,
                    cause=failure.failure_classification,
                    final=failure.failure_classification,
                )
            )
        except Exception:
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=request,
                    cause=HOLD_PROVIDER_UNAVAILABLE,
                    final=HOLD_PROVIDER_UNAVAILABLE,
                )
            )
        observation, identity_failure = _validate_observation_identity(
            observation=raw_observation,
            request=request,
        )
        if identity_failure is not None:
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=request,
                    cause=identity_failure,
                    final=identity_failure,
                    response_digest=(
                        raw_observation.response_digest_sha256
                        if type(raw_observation)
                        is E5ProviderAttemptObservationV1
                        else None
                    ),
                )
            )
        _require(observation is not None)
        if observation.transport_outcome != SUCCESS:
            cause = _TRANSPORT_FAILURE_MAP[observation.transport_outcome]
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=request,
                    cause=cause,
                    final=cause,
                )
            )
        if (
            observation.measured_input_tokens > request.input_hard_limit_tokens
            or observation.measured_output_tokens > request.output_hard_limit_tokens
        ):
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=request,
                    cause=HOLD_TOKEN_LIMIT,
                    final=HOLD_TOKEN_LIMIT,
                    response_digest=observation.response_digest_sha256,
                )
            )
        mapping = _thaw_json_value(observation.response_mapping)
        _require(type(mapping) is dict)
        if mapping.get("model_id") != request.model_id:
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=request,
                    cause=HOLD_MODEL_BINDING,
                    final=HOLD_MODEL_BINDING,
                    response_digest=observation.response_digest_sha256,
                )
            )
        try:
            review = reconstruct_e5_deepseek_structured_review_v1(mapping)
        except Exception:
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=request,
                    cause=HOLD_INVALID_RESPONSE,
                    final=HOLD_INVALID_RESPONSE,
                    response_digest=observation.response_digest_sha256,
                )
            )
        if review.payload_sha256 != verified_payload.payload_sha256:
            return _build_execution(
                invocation_result=_deepseek_result(
                    payload=verified_payload,
                    request=request,
                    cause=HOLD_INVALID_RESPONSE,
                    final=HOLD_INVALID_RESPONSE,
                    response_digest=observation.response_digest_sha256,
                )
            )
        return _build_execution(
            invocation_result=_deepseek_result(
                payload=verified_payload,
                request=request,
                cause=None,
                final=PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED,
                accepted=review.review_sha256,
                response_digest=observation.response_digest_sha256,
            ),
            accepted_deepseek_review=review,
        )
    except Exception:
        _fail()


def execute_e5_deepseek_review_once_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    token_preflight: E5TechnicalReviewTokenPreflightResultV1,
    transport: Callable[[E5ProviderRequestV1], E5ProviderAttemptObservationV1],
) -> E5ProviderAcceptedResponseExecutionV1:
    return _execute_e5_deepseek_review_once_core_v1(
        payload=payload,
        token_preflight=token_preflight,
        transport=transport,
    )


def invoke_e5_deepseek_review_once_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    token_preflight: E5TechnicalReviewTokenPreflightResultV1,
    transport: Callable[[E5ProviderRequestV1], E5ProviderAttemptObservationV1],
) -> E5ProviderInvocationResultV1:
    return execute_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=token_preflight,
        transport=transport,
    ).invocation_result


def _claude_provider_failure_result(
    *,
    payload: E5TechnicalReviewPayloadV1,
    route: E5ClaudeReviewRouteResultV1,
    request: E5ProviderRequestV1 | None,
    cause: str,
    response_digest: str | None = None,
) -> E5ProviderInvocationResultV1:
    return _claude_result(
        payload=payload,
        route=route,
        request=request,
        cause=cause,
        final=HOLD_ESCALATION_INCOMPLETE,
        response_digest=response_digest,
    )


def _execute_e5_claude_review_once_core_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deepseek_review: E5DeepSeekStructuredReviewV1,
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1,
    route_result: E5ClaudeReviewRouteResultV1,
    token_preflight: E5ClaudeTokenPreflightResultV1,
    transport: Callable[[E5ProviderRequestV1], E5ProviderAttemptObservationV1],
) -> E5ProviderAcceptedResponseExecutionV1:
    try:
        verified_payload = _validate_active_payload(payload)
        review, adjudication, route = _validate_claude_lineage(
            payload=verified_payload,
            deepseek_review=deepseek_review,
            deepseek_adjudication=deepseek_adjudication,
            route_result=route_result,
        )
        preflight = _validate_claude_preflight(
            route_result=route,
            token_preflight=token_preflight,
        )
        _require(callable(transport))
        if route.decision_code in (
            ROUTE_L0_NO_CLAUDE_REQUIRED,
            ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE,
        ):
            _require(route.route == L0)
            _require(preflight.decision_code == HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED)
            return _build_execution(
                invocation_result=_claude_result(
                    payload=verified_payload,
                    route=route,
                    request=None,
                    cause=None,
                    final=PASS_L0_NO_CLAUDE_REQUIRED,
                )
            )
        if route.decision_code == BLOCK_DUPLICATE_LOGICAL_REVIEW:
            return _build_execution(
                invocation_result=_claude_result(
                    payload=verified_payload,
                    route=route,
                    request=None,
                    cause=HOLD_ESCALATION_INCOMPLETE,
                    final=HOLD_ESCALATION_INCOMPLETE,
                )
            )
        if route.decision_code in (
            BLOCK_SHARED_DAILY_REVIEW_CEILING,
            BLOCK_L2_DAILY_REVIEW_CEILING,
        ):
            return _build_execution(
                invocation_result=_claude_result(
                    payload=verified_payload,
                    route=route,
                    request=None,
                    cause=HOLD_BUDGET_BLOCKED,
                    final=HOLD_BUDGET_BLOCKED,
                )
            )
        _require(
            route.decision_code
            in (
                ROUTE_L1_CLAUDE_REVIEW_REQUIRED,
                ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED,
            )
        )
        if preflight.decision_code != PASS_CLAUDE_TOKEN_BUDGET:
            return _build_execution(
                invocation_result=_claude_result(
                    payload=verified_payload,
                    route=route,
                    request=None,
                    cause=HOLD_TOKEN_LIMIT,
                    final=HOLD_TOKEN_LIMIT,
                )
            )
        request = build_e5_claude_provider_request_v1(
            payload=verified_payload,
            deepseek_review=review,
            deepseek_adjudication=adjudication,
            route_result=route,
            token_preflight=preflight,
        )
        try:
            raw_observation = transport(request)
        except E5ProviderPreNetworkFailureV1 as failure:
            failure.__post_init__()
            return _build_execution(
                invocation_result=_claude_provider_failure_result(
                    payload=verified_payload,
                    route=route,
                    request=None,
                    cause=failure.failure_classification,
                )
            )
        except Exception:
            return _build_execution(
                invocation_result=_claude_provider_failure_result(
                    payload=verified_payload,
                    route=route,
                    request=request,
                    cause=HOLD_PROVIDER_UNAVAILABLE,
                )
            )
        observation, identity_failure = _validate_observation_identity(
            observation=raw_observation,
            request=request,
        )
        if identity_failure is not None:
            return _build_execution(
                invocation_result=_claude_provider_failure_result(
                    payload=verified_payload,
                    route=route,
                    request=request,
                    cause=identity_failure,
                    response_digest=(
                        raw_observation.response_digest_sha256
                        if type(raw_observation)
                        is E5ProviderAttemptObservationV1
                        else None
                    ),
                )
            )
        _require(observation is not None)
        if observation.transport_outcome != SUCCESS:
            cause = _TRANSPORT_FAILURE_MAP[observation.transport_outcome]
            return _build_execution(
                invocation_result=_claude_provider_failure_result(
                    payload=verified_payload,
                    route=route,
                    request=request,
                    cause=cause,
                )
            )
        if observation.billed_cost_micro_usd > request.maximum_review_cost_micro_usd:
            return _build_execution(
                invocation_result=_claude_result(
                    payload=verified_payload,
                    route=route,
                    request=request,
                    cause=HOLD_BUDGET_BLOCKED,
                    final=HOLD_BUDGET_BLOCKED,
                    response_digest=observation.response_digest_sha256,
                )
            )
        if (
            observation.measured_input_tokens > request.input_hard_limit_tokens
            or observation.measured_output_tokens > request.output_hard_limit_tokens
        ):
            return _build_execution(
                invocation_result=_claude_provider_failure_result(
                    payload=verified_payload,
                    route=route,
                    request=request,
                    cause=HOLD_TOKEN_LIMIT,
                    response_digest=observation.response_digest_sha256,
                )
            )
        mapping = _thaw_json_value(observation.response_mapping)
        _require(type(mapping) is dict)
        if mapping.get("model_id") != request.model_id:
            return _build_execution(
                invocation_result=_claude_provider_failure_result(
                    payload=verified_payload,
                    route=route,
                    request=request,
                    cause=HOLD_MODEL_BINDING,
                    response_digest=observation.response_digest_sha256,
                )
            )
        try:
            claude_review = reconstruct_e5_claude_escalation_review_v1(mapping)
        except Exception:
            return _build_execution(
                invocation_result=_claude_provider_failure_result(
                    payload=verified_payload,
                    route=route,
                    request=request,
                    cause=HOLD_INVALID_RESPONSE,
                    response_digest=observation.response_digest_sha256,
                )
            )
        if (
            claude_review.payload_sha256 != verified_payload.payload_sha256
            or claude_review.route_sha256 != route.route_sha256
            or claude_review.route != route.route
            or claude_review.provider_binding_sha256
            != verified_payload.provider_binding_sha256
        ):
            return _build_execution(
                invocation_result=_claude_provider_failure_result(
                    payload=verified_payload,
                    route=route,
                    request=request,
                    cause=HOLD_INVALID_RESPONSE,
                    response_digest=observation.response_digest_sha256,
                )
            )
        return _build_execution(
            invocation_result=_claude_result(
                payload=verified_payload,
                route=route,
                request=request,
                cause=None,
                final=PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED,
                accepted=claude_review.review_sha256,
                response_digest=observation.response_digest_sha256,
            ),
            accepted_claude_review=claude_review,
        )
    except Exception:
        _fail()


def execute_e5_claude_review_once_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deepseek_review: E5DeepSeekStructuredReviewV1,
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1,
    route_result: E5ClaudeReviewRouteResultV1,
    token_preflight: E5ClaudeTokenPreflightResultV1,
    transport: Callable[[E5ProviderRequestV1], E5ProviderAttemptObservationV1],
) -> E5ProviderAcceptedResponseExecutionV1:
    return _execute_e5_claude_review_once_core_v1(
        payload=payload,
        deepseek_review=deepseek_review,
        deepseek_adjudication=deepseek_adjudication,
        route_result=route_result,
        token_preflight=token_preflight,
        transport=transport,
    )


def invoke_e5_claude_review_once_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deepseek_review: E5DeepSeekStructuredReviewV1,
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1,
    route_result: E5ClaudeReviewRouteResultV1,
    token_preflight: E5ClaudeTokenPreflightResultV1,
    transport: Callable[[E5ProviderRequestV1], E5ProviderAttemptObservationV1],
) -> E5ProviderInvocationResultV1:
    return execute_e5_claude_review_once_v1(
        payload=payload,
        deepseek_review=deepseek_review,
        deepseek_adjudication=deepseek_adjudication,
        route_result=route_result,
        token_preflight=token_preflight,
        transport=transport,
    ).invocation_result


__all__ = (
    "E5_PROVIDER_REQUEST_VERSION",
    "E5_PROVIDER_ATTEMPT_OBSERVATION_VERSION",
    "E5_CLAUDE_ESCALATION_REVIEW_VERSION",
    "E5_PROVIDER_INVOCATION_RESULT_VERSION",
    "E5_PROVIDER_ACCEPTED_RESPONSE_EXECUTION_VERSION",
    "E5_PROVIDER_PRE_NETWORK_FAILURE_V1_VERSION",
    "ACTIVE_PROVIDER_BINDING_SHA256",
    "DEEPSEEK",
    "ANTHROPIC",
    "E5_PROVIDERS",
    "PROVIDER_COUNT",
    "DEEPSEEK_TECHNICAL_REVIEW",
    "CLAUDE_L1_ESCALATION_REVIEW",
    "CLAUDE_L2_ESCALATION_REVIEW",
    "E5_INVOCATION_ROLES",
    "INVOCATION_ROLE_COUNT",
    "HOLD_PROVIDER_TIMEOUT",
    "HOLD_PROVIDER_UNAVAILABLE",
    "HOLD_PROVIDER_CONFIGURATION",
    "HOLD_MODEL_BINDING",
    "HOLD_INVALID_RESPONSE",
    "HOLD_TOKEN_LIMIT",
    "HOLD_BUDGET_BLOCKED",
    "HOLD_ESCALATION_INCOMPLETE",
    "E5_D8_FAILURE_CODES",
    "D8_FAILURE_CODE_COUNT",
    "PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED",
    "PASS_L0_NO_CLAUDE_REQUIRED",
    "PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED",
    "E5_PROVIDER_INVOCATION_SUCCESS_CODES",
    "SUCCESS_CODE_COUNT",
    "PROVIDER_FAILURE_DEFAULT",
    "SUCCESS",
    "TIMEOUT",
    "TEMPORARILY_UNAVAILABLE",
    "AUTHENTICATION_OR_PERMISSION_FAILURE",
    "UNSUPPORTED_MODEL",
    "MALFORMED_OR_SCHEMA_INVALID_RESPONSE",
    "TOKEN_LIMIT_EXCEEDED",
    "BUDGET_BLOCKED",
    "E5_TRANSPORT_OUTCOME_CODES",
    "TRANSPORT_OUTCOME_CODE_COUNT",
    "MAXIMUM_PROVIDER_ATTEMPTS",
    "RETRY_COUNT",
    "E5ProviderRequestV1",
    "E5ProviderPreNetworkFailureV1",
    "E5ProviderAttemptObservationV1",
    "E5ClaudeEscalationReviewV1",
    "E5ProviderInvocationResultV1",
    "E5ProviderAcceptedResponseExecutionV1",
    "build_e5_deepseek_provider_request_v1",
    "build_e5_claude_provider_request_v1",
    "build_e5_provider_attempt_observation_v1",
    "reconstruct_e5_claude_escalation_review_v1",
    "execute_e5_deepseek_review_once_v1",
    "execute_e5_claude_review_once_v1",
    "invoke_e5_deepseek_review_once_v1",
    "invoke_e5_claude_review_once_v1",
)
