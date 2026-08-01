"""Pure deterministic Claude escalation routing, usage, and preflight contracts."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from hashlib import sha256
import json
import re
from typing import Final, Mapping

from engine.e5_deepseek_technical_review_v1 import (
    CAUTION,
    CLEAR,
    HOLD,
    CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE,
    CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE,
    STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR,
    STOP_DEEPSEEK_HOLD,
    STOP_DETERMINISTIC_HARD_GATE,
    E5DeepSeekStructuredReviewV1,
    E5DeepSeekTechnicalReviewAdjudicationV1,
)
from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
    E5TechnicalReviewPayloadV1,
    get_owner_frozen_e5_provider_model_price_binding_v4,
)


E5_CLAUDE_REVIEW_ROUTER_VERSION: Final = "e5-claude-review-router-v1"
E5_CLAUDE_DAILY_USAGE_VERSION: Final = "e5-claude-daily-usage-v1"
E5_CLAUDE_TOKEN_PREFLIGHT_VERSION: Final = "e5-claude-token-preflight-v1"

ACTIVE_PROVIDER_BINDING_SHA256: Final = (
    "4a31dbcb7a0c4daed3215dbe8817002c24b2ead30e7092096c992b322e0fe1d9"
)

L0: Final = "L0"
L1: Final = "L1"
L2: Final = "L2"
CLAUDE_ROUTES: Final = (L0, L1, L2)

ROUTE_L0_NO_CLAUDE_REQUIRED: Final = "ROUTE_L0_NO_CLAUDE_REQUIRED"
ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE: Final = (
    "ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE"
)
ROUTE_L1_CLAUDE_REVIEW_REQUIRED: Final = (
    "ROUTE_L1_CLAUDE_REVIEW_REQUIRED"
)
ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED: Final = (
    "ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED"
)
BLOCK_DUPLICATE_LOGICAL_REVIEW: Final = "BLOCK_DUPLICATE_LOGICAL_REVIEW"
BLOCK_SHARED_DAILY_REVIEW_CEILING: Final = (
    "BLOCK_SHARED_DAILY_REVIEW_CEILING"
)
BLOCK_L2_DAILY_REVIEW_CEILING: Final = "BLOCK_L2_DAILY_REVIEW_CEILING"

E5_CLAUDE_ROUTER_DECISION_CODES: Final = (
    ROUTE_L0_NO_CLAUDE_REQUIRED,
    ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE,
    ROUTE_L1_CLAUDE_REVIEW_REQUIRED,
    ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED,
    BLOCK_DUPLICATE_LOGICAL_REVIEW,
    BLOCK_SHARED_DAILY_REVIEW_CEILING,
    BLOCK_L2_DAILY_REVIEW_CEILING,
)

PASS_CLAUDE_TOKEN_BUDGET: Final = "PASS_CLAUDE_TOKEN_BUDGET"
HOLD_CLAUDE_INPUT_TOKEN_LIMIT: Final = "HOLD_CLAUDE_INPUT_TOKEN_LIMIT"
HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT: Final = "HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT"
HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED: Final = (
    "HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED"
)
E5_CLAUDE_TOKEN_PREFLIGHT_DECISION_CODES: Final = (
    PASS_CLAUDE_TOKEN_BUDGET,
    HOLD_CLAUDE_INPUT_TOKEN_LIMIT,
    HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT,
    HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED,
)

CLAUDE_L1_MODEL_ID: Final = "claude-opus-5"
CLAUDE_L2_MODEL_ID: Final = "claude-fable-5"
CLAUDE_L1_MAXIMUM_REVIEW_COST_MICRO_USD: Final = 32500
CLAUDE_L2_MAXIMUM_REVIEW_COST_MICRO_USD: Final = 100000
SHARED_DAILY_LOGICAL_REVIEW_CEILING: Final = 9
L2_DAILY_LOGICAL_REVIEW_CEILING: Final = 3
MAXIMUM_DAILY_COST_MICRO_USD: Final = 495000

_ERROR: Final = "invalid E5 Claude review router"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_UTC_DAY_PATTERN: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_UTC_TIMESTAMP_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_USAGE_MAPPING_KEYS: Final = frozenset(
    (
        "usage_version",
        "utc_day",
        "l1_reviewed_payload_sha256s",
        "l2_reviewed_payload_sha256s",
        "committed_maximum_cost_micro_usd",
        "usage_sha256",
    )
)
_BLOCK_DECISION_CODES: Final = E5_CLAUDE_ROUTER_DECISION_CODES[4:]


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
    _require(binding.claude_l1_model_id == CLAUDE_L1_MODEL_ID)
    _require(binding.claude_l1_input_hard_limit_tokens == 4000)
    _require(binding.claude_l1_output_hard_limit_tokens == 500)
    _require(binding.claude_l1_timeout_seconds == 10)
    _require(binding.claude_l1_provider_attempts == 1)
    _require(binding.claude_l1_retry_count == 0)
    _require(
        binding.claude_l1_max_cost_micro_usd
        == CLAUDE_L1_MAXIMUM_REVIEW_COST_MICRO_USD
    )
    _require(binding.claude_l2_model_id == CLAUDE_L2_MODEL_ID)
    _require(binding.claude_l2_input_hard_limit_tokens == 6000)
    _require(binding.claude_l2_output_hard_limit_tokens == 800)
    _require(binding.claude_l2_timeout_seconds == 20)
    _require(binding.claude_l2_provider_attempts == 1)
    _require(binding.claude_l2_retry_count == 0)
    _require(
        binding.claude_l2_max_cost_micro_usd
        == CLAUDE_L2_MAXIMUM_REVIEW_COST_MICRO_USD
    )
    _require(
        binding.shared_l1_l2_daily_logical_review_ceiling
        == SHARED_DAILY_LOGICAL_REVIEW_CEILING
    )
    _require(
        binding.l2_daily_logical_review_ceiling
        == L2_DAILY_LOGICAL_REVIEW_CEILING
    )
    _require(
        binding.maximum_daily_cost_micro_usd
        == MAXIMUM_DAILY_COST_MICRO_USD
    )
    _require(binding.latest_alias_allowed is False)
    _require(binding.cross_provider_substitution_allowed is False)
    _require(binding.malformed_response_prompt_repair_allowed is False)
    _require(binding.stale_result_reuse_allowed is False)
    _require(binding.same_invocation_retry_allowed is False)
    _require(binding.claude_l1_thinking_mode == "disabled")
    _require(binding.claude_l1_effort == "high")
    _require(binding.claude_l2_thinking_mode == "always_on_adaptive")
    _require(binding.claude_l2_effort == "high")
    _require(
        binding.provider_output_limit_activation_status
        == "NON_PRODUCTION_CANARY_CANDIDATES_NOT_PRODUCTION_PROVEN"
    )
    return binding


def _validate_utc_day(value: object) -> str:
    _require(type(value) is str and _UTC_DAY_PATTERN.fullmatch(value) is not None)
    try:
        parsed = date.fromisoformat(value)
    except Exception:
        _fail()
    _require(parsed.isoformat() == value)
    return value


def _payload_utc_day(payload: E5TechnicalReviewPayloadV1) -> str:
    trigger_age = payload.to_mapping()["trigger_age"]
    _require(type(trigger_age) is dict)
    timestamp = trigger_age.get("evaluation_timestamp")
    _require(
        type(timestamp) is str
        and _UTC_TIMESTAMP_PATTERN.fullmatch(timestamp) is not None
    )
    try:
        parsed = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        _fail()
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == timestamp)
    return timestamp[:10]


def _validate_payload(value: object) -> E5TechnicalReviewPayloadV1:
    _require(type(value) is E5TechnicalReviewPayloadV1)
    value.__post_init__()
    binding = _active_binding()
    _require(value.provider_binding_sha256 == binding.binding_sha256)
    return value


def _usage_preimage(usage: "E5ClaudeDailyUsageV1") -> dict[str, object]:
    return {
        "usage_version": usage.usage_version,
        "utc_day": usage.utc_day,
        "l1_reviewed_payload_sha256s": list(
            usage.l1_reviewed_payload_sha256s
        ),
        "l2_reviewed_payload_sha256s": list(
            usage.l2_reviewed_payload_sha256s
        ),
        "committed_maximum_cost_micro_usd": (
            usage.committed_maximum_cost_micro_usd
        ),
    }


@dataclass(frozen=True, slots=True)
class E5ClaudeDailyUsageV1:
    usage_version: str
    utc_day: str
    l1_reviewed_payload_sha256s: tuple[str, ...]
    l2_reviewed_payload_sha256s: tuple[str, ...]
    committed_maximum_cost_micro_usd: int
    usage_sha256: str

    def __post_init__(self) -> None:
        try:
            _active_binding()
            _require(type(self.usage_version) is str)
            _require(self.usage_version == E5_CLAUDE_DAILY_USAGE_VERSION)
            _validate_utc_day(self.utc_day)
            _require(type(self.l1_reviewed_payload_sha256s) is tuple)
            _require(type(self.l2_reviewed_payload_sha256s) is tuple)
            combined = (
                self.l1_reviewed_payload_sha256s
                + self.l2_reviewed_payload_sha256s
            )
            _require(all(_valid_sha256(identity) for identity in combined))
            _require(len(set(combined)) == len(combined))
            _require(
                len(combined) <= SHARED_DAILY_LOGICAL_REVIEW_CEILING
            )
            _require(
                len(self.l2_reviewed_payload_sha256s)
                <= L2_DAILY_LOGICAL_REVIEW_CEILING
            )
            _require(
                type(self.committed_maximum_cost_micro_usd) is int
                and self.committed_maximum_cost_micro_usd >= 0
            )
            expected_cost = (
                len(self.l1_reviewed_payload_sha256s)
                * CLAUDE_L1_MAXIMUM_REVIEW_COST_MICRO_USD
                + len(self.l2_reviewed_payload_sha256s)
                * CLAUDE_L2_MAXIMUM_REVIEW_COST_MICRO_USD
            )
            _require(self.committed_maximum_cost_micro_usd == expected_cost)
            _require(expected_cost <= MAXIMUM_DAILY_COST_MICRO_USD)
            _require(_valid_sha256(self.usage_sha256))
            _require(
                self.usage_sha256 == _hash_mapping(_usage_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_usage_preimage(self),
            "usage_sha256": self.usage_sha256,
        }

    def canonical_usage_json(self) -> str:
        return _canonical_json(_usage_preimage(self))


def _build_usage(
    *,
    utc_day: str,
    l1_identities: tuple[str, ...],
    l2_identities: tuple[str, ...],
) -> E5ClaudeDailyUsageV1:
    committed_cost = (
        len(l1_identities) * CLAUDE_L1_MAXIMUM_REVIEW_COST_MICRO_USD
        + len(l2_identities) * CLAUDE_L2_MAXIMUM_REVIEW_COST_MICRO_USD
    )
    data: dict[str, object] = {
        "usage_version": E5_CLAUDE_DAILY_USAGE_VERSION,
        "utc_day": utc_day,
        "l1_reviewed_payload_sha256s": l1_identities,
        "l2_reviewed_payload_sha256s": l2_identities,
        "committed_maximum_cost_micro_usd": committed_cost,
    }
    temporary = object.__new__(E5ClaudeDailyUsageV1)
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E5ClaudeDailyUsageV1(
        **data,
        usage_sha256=_hash_mapping(_usage_preimage(temporary)),
    )


def create_empty_e5_claude_daily_usage_v1(
    *,
    utc_day: str,
) -> E5ClaudeDailyUsageV1:
    try:
        return _build_usage(
            utc_day=utc_day,
            l1_identities=(),
            l2_identities=(),
        )
    except Exception:
        _fail()


def reconstruct_e5_claude_daily_usage_v1(
    mapping: Mapping[str, object],
) -> E5ClaudeDailyUsageV1:
    try:
        _require(type(mapping) is dict)
        _require(frozenset(mapping) == _USAGE_MAPPING_KEYS)
        _require(type(mapping["l1_reviewed_payload_sha256s"]) is list)
        _require(type(mapping["l2_reviewed_payload_sha256s"]) is list)
        return E5ClaudeDailyUsageV1(
            usage_version=mapping["usage_version"],
            utc_day=mapping["utc_day"],
            l1_reviewed_payload_sha256s=tuple(
                mapping["l1_reviewed_payload_sha256s"]
            ),
            l2_reviewed_payload_sha256s=tuple(
                mapping["l2_reviewed_payload_sha256s"]
            ),
            committed_maximum_cost_micro_usd=(
                mapping["committed_maximum_cost_micro_usd"]
            ),
            usage_sha256=mapping["usage_sha256"],
        )
    except Exception:
        _fail()


def _route_preimage(
    result: "E5ClaudeReviewRouteResultV1",
) -> dict[str, object]:
    return {
        field.name: (
            result.usage_after.to_mapping()
            if field.name == "usage_after"
            else getattr(result, field.name)
        )
        for field in fields(E5ClaudeReviewRouteResultV1)
        if field.name != "route_sha256"
    }


def _zero_resource_profile(result: "E5ClaudeReviewRouteResultV1") -> None:
    _require(result.claude_required is False)
    _require(result.model_id is None)
    _require(result.input_hard_limit_tokens == 0)
    _require(result.output_hard_limit_tokens == 0)
    _require(result.timeout_seconds == 0)
    _require(result.provider_attempts == 0)
    _require(result.retry_count == 0)
    _require(result.maximum_review_cost_micro_usd == 0)


def _allowed_resource_profile(
    result: "E5ClaudeReviewRouteResultV1",
) -> None:
    binding = _active_binding()
    _require(result.claude_required is True)
    if result.route == L1:
        expected = (
            binding.claude_l1_model_id,
            binding.claude_l1_input_hard_limit_tokens,
            binding.claude_l1_output_hard_limit_tokens,
            binding.claude_l1_timeout_seconds,
            binding.claude_l1_provider_attempts,
            binding.claude_l1_retry_count,
            binding.claude_l1_max_cost_micro_usd,
        )
    else:
        _require(result.route == L2)
        expected = (
            binding.claude_l2_model_id,
            binding.claude_l2_input_hard_limit_tokens,
            binding.claude_l2_output_hard_limit_tokens,
            binding.claude_l2_timeout_seconds,
            binding.claude_l2_provider_attempts,
            binding.claude_l2_retry_count,
            binding.claude_l2_max_cost_micro_usd,
        )
    actual = (
        result.model_id,
        result.input_hard_limit_tokens,
        result.output_hard_limit_tokens,
        result.timeout_seconds,
        result.provider_attempts,
        result.retry_count,
        result.maximum_review_cost_micro_usd,
    )
    _require(actual == expected)


@dataclass(frozen=True, slots=True)
class E5ClaudeReviewRouteResultV1:
    router_version: str
    provider_binding_sha256: str
    payload_sha256: str
    deepseek_review_sha256: str
    deepseek_adjudication_sha256: str
    route: str
    claude_required: bool
    model_id: str | None
    input_hard_limit_tokens: int
    output_hard_limit_tokens: int
    timeout_seconds: int
    provider_attempts: int
    retry_count: int
    maximum_review_cost_micro_usd: int
    deepseek_publication_block_preserved: bool
    usage_before_sha256: str
    usage_after: E5ClaudeDailyUsageV1
    decision_code: str
    route_sha256: str

    def __post_init__(self) -> None:
        try:
            binding = _active_binding()
            _require(type(self.router_version) is str)
            _require(self.router_version == E5_CLAUDE_REVIEW_ROUTER_VERSION)
            _require(self.provider_binding_sha256 == binding.binding_sha256)
            _require(_valid_sha256(self.payload_sha256))
            _require(_valid_sha256(self.deepseek_review_sha256))
            _require(_valid_sha256(self.deepseek_adjudication_sha256))
            _require(type(self.route) is str and self.route in CLAUDE_ROUTES)
            _require(type(self.claude_required) is bool)
            _require(type(self.model_id) is str or self.model_id is None)
            for value in (
                self.input_hard_limit_tokens,
                self.output_hard_limit_tokens,
                self.timeout_seconds,
                self.provider_attempts,
                self.retry_count,
                self.maximum_review_cost_micro_usd,
            ):
                _require(type(value) is int and value >= 0)
            _require(type(self.deepseek_publication_block_preserved) is bool)
            _require(_valid_sha256(self.usage_before_sha256))
            _require(type(self.usage_after) is E5ClaudeDailyUsageV1)
            self.usage_after.__post_init__()
            _require(
                type(self.decision_code) is str
                and self.decision_code in E5_CLAUDE_ROUTER_DECISION_CODES
            )
            if self.decision_code == ROUTE_L0_NO_CLAUDE_REQUIRED:
                _require(self.route == L0)
                _zero_resource_profile(self)
                _require(self.deepseek_publication_block_preserved is False)
                _require(self.usage_after.usage_sha256 == self.usage_before_sha256)
            elif self.decision_code == ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE:
                _require(self.route == L0)
                _zero_resource_profile(self)
                _require(self.deepseek_publication_block_preserved is True)
                _require(self.usage_after.usage_sha256 == self.usage_before_sha256)
            elif self.decision_code == ROUTE_L1_CLAUDE_REVIEW_REQUIRED:
                _require(self.route == L1)
                _allowed_resource_profile(self)
                _require(self.deepseek_publication_block_preserved is False)
                _require(
                    self.usage_after.l1_reviewed_payload_sha256s[-1]
                    == self.payload_sha256
                )
                _require(self.usage_after.usage_sha256 != self.usage_before_sha256)
            elif (
                self.decision_code
                == ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED
            ):
                _require(self.route == L2)
                _allowed_resource_profile(self)
                _require(self.deepseek_publication_block_preserved is True)
                _require(
                    self.usage_after.l2_reviewed_payload_sha256s[-1]
                    == self.payload_sha256
                )
                _require(self.usage_after.usage_sha256 != self.usage_before_sha256)
            else:
                _require(self.decision_code in _BLOCK_DECISION_CODES)
                _require(self.route in (L1, L2))
                if self.decision_code == BLOCK_L2_DAILY_REVIEW_CEILING:
                    _require(self.route == L2)
                _zero_resource_profile(self)
                _require(
                    self.deepseek_publication_block_preserved
                    == (self.route == L2)
                )
                _require(self.usage_after.usage_sha256 == self.usage_before_sha256)
            _require(_valid_sha256(self.route_sha256))
            _require(self.route_sha256 == _hash_mapping(_route_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_route_preimage(self),
            "route_sha256": self.route_sha256,
        }

    def canonical_route_json(self) -> str:
        return _canonical_json(_route_preimage(self))


def _route_profile(
    route: str,
    *,
    claude_required: bool,
) -> tuple[str | None, int, int, int, int, int, int]:
    if not claude_required:
        return None, 0, 0, 0, 0, 0, 0
    binding = _active_binding()
    if route == L1:
        return (
            binding.claude_l1_model_id,
            binding.claude_l1_input_hard_limit_tokens,
            binding.claude_l1_output_hard_limit_tokens,
            binding.claude_l1_timeout_seconds,
            binding.claude_l1_provider_attempts,
            binding.claude_l1_retry_count,
            binding.claude_l1_max_cost_micro_usd,
        )
    _require(route == L2)
    return (
        binding.claude_l2_model_id,
        binding.claude_l2_input_hard_limit_tokens,
        binding.claude_l2_output_hard_limit_tokens,
        binding.claude_l2_timeout_seconds,
        binding.claude_l2_provider_attempts,
        binding.claude_l2_retry_count,
        binding.claude_l2_max_cost_micro_usd,
    )


def _build_route_result(
    *,
    payload: E5TechnicalReviewPayloadV1,
    review: E5DeepSeekStructuredReviewV1,
    adjudication: E5DeepSeekTechnicalReviewAdjudicationV1,
    route: str,
    claude_required: bool,
    usage_before: E5ClaudeDailyUsageV1,
    usage_after: E5ClaudeDailyUsageV1,
    decision_code: str,
) -> E5ClaudeReviewRouteResultV1:
    binding = _active_binding()
    profile = _route_profile(route, claude_required=claude_required)
    data: dict[str, object] = {
        "router_version": E5_CLAUDE_REVIEW_ROUTER_VERSION,
        "provider_binding_sha256": binding.binding_sha256,
        "payload_sha256": payload.payload_sha256,
        "deepseek_review_sha256": review.review_sha256,
        "deepseek_adjudication_sha256": adjudication.adjudication_sha256,
        "route": route,
        "claude_required": claude_required,
        "model_id": profile[0],
        "input_hard_limit_tokens": profile[1],
        "output_hard_limit_tokens": profile[2],
        "timeout_seconds": profile[3],
        "provider_attempts": profile[4],
        "retry_count": profile[5],
        "maximum_review_cost_micro_usd": profile[6],
        "deepseek_publication_block_preserved": adjudication.publication_blocked,
        "usage_before_sha256": usage_before.usage_sha256,
        "usage_after": usage_after,
        "decision_code": decision_code,
    }
    temporary = object.__new__(E5ClaudeReviewRouteResultV1)
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E5ClaudeReviewRouteResultV1(
        **data,
        route_sha256=_hash_mapping(_route_preimage(temporary)),
    )


def _validate_deepseek_lineage(
    *,
    payload: E5TechnicalReviewPayloadV1,
    review: object,
    adjudication: object,
) -> tuple[E5DeepSeekStructuredReviewV1, E5DeepSeekTechnicalReviewAdjudicationV1]:
    _require(type(review) is E5DeepSeekStructuredReviewV1)
    review.__post_init__()
    _require(type(adjudication) is E5DeepSeekTechnicalReviewAdjudicationV1)
    adjudication.__post_init__()
    _require(review.payload_sha256 == payload.payload_sha256)
    _require(adjudication.payload_sha256 == payload.payload_sha256)
    _require(adjudication.review_sha256 == review.review_sha256)
    _require(adjudication.model_id == review.model_id)
    _require(adjudication.review_decision == review.decision)
    _require(adjudication.reason_codes == review.reason_codes)
    return review, adjudication


def _required_route(
    review: E5DeepSeekStructuredReviewV1,
    adjudication: E5DeepSeekTechnicalReviewAdjudicationV1,
) -> tuple[str, str]:
    combination = (review.decision, adjudication.outcome_code)
    if combination == (CLEAR, CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE):
        return L0, ROUTE_L0_NO_CLAUDE_REQUIRED
    if combination == (CAUTION, CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE):
        return L1, ROUTE_L1_CLAUDE_REVIEW_REQUIRED
    if combination == (HOLD, STOP_DEEPSEEK_HOLD):
        return (
            L2,
            ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED,
        )
    if combination in (
        (CLEAR, STOP_DETERMINISTIC_HARD_GATE),
        (CAUTION, STOP_DETERMINISTIC_HARD_GATE),
        (CAUTION, STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR),
    ):
        return L0, ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE
    _fail()


def route_e5_claude_review_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deepseek_review: E5DeepSeekStructuredReviewV1,
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1,
    daily_usage: E5ClaudeDailyUsageV1,
) -> E5ClaudeReviewRouteResultV1:
    try:
        verified_payload = _validate_payload(payload)
        review, adjudication = _validate_deepseek_lineage(
            payload=verified_payload,
            review=deepseek_review,
            adjudication=deepseek_adjudication,
        )
        _require(type(daily_usage) is E5ClaudeDailyUsageV1)
        daily_usage.__post_init__()
        _require(daily_usage.utc_day == _payload_utc_day(verified_payload))
        route, allowed_decision = _required_route(review, adjudication)
        if route == L0:
            return _build_route_result(
                payload=verified_payload,
                review=review,
                adjudication=adjudication,
                route=L0,
                claude_required=False,
                usage_before=daily_usage,
                usage_after=daily_usage,
                decision_code=allowed_decision,
            )

        combined = (
            daily_usage.l1_reviewed_payload_sha256s
            + daily_usage.l2_reviewed_payload_sha256s
        )
        if verified_payload.payload_sha256 in combined:
            decision_code = BLOCK_DUPLICATE_LOGICAL_REVIEW
        elif len(combined) >= SHARED_DAILY_LOGICAL_REVIEW_CEILING:
            decision_code = BLOCK_SHARED_DAILY_REVIEW_CEILING
        elif (
            route == L2
            and len(daily_usage.l2_reviewed_payload_sha256s)
            >= L2_DAILY_LOGICAL_REVIEW_CEILING
        ):
            decision_code = BLOCK_L2_DAILY_REVIEW_CEILING
        else:
            if route == L1:
                usage_after = _build_usage(
                    utc_day=daily_usage.utc_day,
                    l1_identities=(
                        *daily_usage.l1_reviewed_payload_sha256s,
                        verified_payload.payload_sha256,
                    ),
                    l2_identities=daily_usage.l2_reviewed_payload_sha256s,
                )
            else:
                usage_after = _build_usage(
                    utc_day=daily_usage.utc_day,
                    l1_identities=daily_usage.l1_reviewed_payload_sha256s,
                    l2_identities=(
                        *daily_usage.l2_reviewed_payload_sha256s,
                        verified_payload.payload_sha256,
                    ),
                )
            return _build_route_result(
                payload=verified_payload,
                review=review,
                adjudication=adjudication,
                route=route,
                claude_required=True,
                usage_before=daily_usage,
                usage_after=usage_after,
                decision_code=allowed_decision,
            )

        return _build_route_result(
            payload=verified_payload,
            review=review,
            adjudication=adjudication,
            route=route,
            claude_required=False,
            usage_before=daily_usage,
            usage_after=daily_usage,
            decision_code=decision_code,
        )
    except Exception:
        _fail()


def _preflight_preimage(
    result: "E5ClaudeTokenPreflightResultV1",
) -> dict[str, object]:
    return {
        field.name: getattr(result, field.name)
        for field in fields(E5ClaudeTokenPreflightResultV1)
        if field.name != "preflight_sha256"
    }


@dataclass(frozen=True, slots=True)
class E5ClaudeTokenPreflightResultV1:
    preflight_version: str
    provider_binding_sha256: str
    route_sha256: str
    payload_sha256: str
    route: str
    model_id: str | None
    measured_input_tokens: int
    requested_output_tokens: int
    input_hard_limit_tokens: int
    output_hard_limit_tokens: int
    within_limits: bool
    decision_code: str
    preflight_sha256: str

    def __post_init__(self) -> None:
        try:
            binding = _active_binding()
            _require(type(self.preflight_version) is str)
            _require(self.preflight_version == E5_CLAUDE_TOKEN_PREFLIGHT_VERSION)
            _require(self.provider_binding_sha256 == binding.binding_sha256)
            _require(_valid_sha256(self.route_sha256))
            _require(_valid_sha256(self.payload_sha256))
            _require(type(self.route) is str and self.route in CLAUDE_ROUTES)
            _require(type(self.model_id) is str or self.model_id is None)
            for value in (
                self.measured_input_tokens,
                self.requested_output_tokens,
                self.input_hard_limit_tokens,
                self.output_hard_limit_tokens,
            ):
                _require(type(value) is int and value >= 0)
            _require(type(self.within_limits) is bool)
            if self.model_id is None:
                _require(self.input_hard_limit_tokens == 0)
                _require(self.output_hard_limit_tokens == 0)
                expected = (False, HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED)
            else:
                if self.route == L1:
                    _require(self.model_id == binding.claude_l1_model_id)
                    _require(
                        self.input_hard_limit_tokens
                        == binding.claude_l1_input_hard_limit_tokens
                    )
                    _require(
                        self.output_hard_limit_tokens
                        == binding.claude_l1_output_hard_limit_tokens
                    )
                else:
                    _require(self.route == L2)
                    _require(self.model_id == binding.claude_l2_model_id)
                    _require(
                        self.input_hard_limit_tokens
                        == binding.claude_l2_input_hard_limit_tokens
                    )
                    _require(
                        self.output_hard_limit_tokens
                        == binding.claude_l2_output_hard_limit_tokens
                    )
                if self.measured_input_tokens > self.input_hard_limit_tokens:
                    expected = (False, HOLD_CLAUDE_INPUT_TOKEN_LIMIT)
                elif self.requested_output_tokens > self.output_hard_limit_tokens:
                    expected = (False, HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT)
                else:
                    expected = (True, PASS_CLAUDE_TOKEN_BUDGET)
            _require((self.within_limits, self.decision_code) == expected)
            _require(
                self.decision_code in E5_CLAUDE_TOKEN_PREFLIGHT_DECISION_CODES
            )
            _require(_valid_sha256(self.preflight_sha256))
            _require(
                self.preflight_sha256
                == _hash_mapping(_preflight_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_preflight_preimage(self),
            "preflight_sha256": self.preflight_sha256,
        }

    def canonical_preflight_json(self) -> str:
        return _canonical_json(_preflight_preimage(self))


def preflight_e5_claude_review_v1(
    *,
    route_result: E5ClaudeReviewRouteResultV1,
    measured_input_tokens: int,
    requested_output_tokens: int,
) -> E5ClaudeTokenPreflightResultV1:
    try:
        _require(type(route_result) is E5ClaudeReviewRouteResultV1)
        route_result.__post_init__()
        _require(type(measured_input_tokens) is int and measured_input_tokens >= 0)
        _require(type(requested_output_tokens) is int and requested_output_tokens >= 0)
        authorized = (
            route_result.claude_required is True
            and route_result.decision_code
            in (
                ROUTE_L1_CLAUDE_REVIEW_REQUIRED,
                ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED,
            )
        )
        if not authorized:
            model_id = None
            input_limit = 0
            output_limit = 0
            within_limits = False
            decision_code = HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED
        else:
            model_id = route_result.model_id
            input_limit = route_result.input_hard_limit_tokens
            output_limit = route_result.output_hard_limit_tokens
            if measured_input_tokens > input_limit:
                within_limits = False
                decision_code = HOLD_CLAUDE_INPUT_TOKEN_LIMIT
            elif requested_output_tokens > output_limit:
                within_limits = False
                decision_code = HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT
            else:
                within_limits = True
                decision_code = PASS_CLAUDE_TOKEN_BUDGET
        data: dict[str, object] = {
            "preflight_version": E5_CLAUDE_TOKEN_PREFLIGHT_VERSION,
            "provider_binding_sha256": route_result.provider_binding_sha256,
            "route_sha256": route_result.route_sha256,
            "payload_sha256": route_result.payload_sha256,
            "route": route_result.route,
            "model_id": model_id,
            "measured_input_tokens": measured_input_tokens,
            "requested_output_tokens": requested_output_tokens,
            "input_hard_limit_tokens": input_limit,
            "output_hard_limit_tokens": output_limit,
            "within_limits": within_limits,
            "decision_code": decision_code,
        }
        temporary = object.__new__(E5ClaudeTokenPreflightResultV1)
        for name, value in data.items():
            object.__setattr__(temporary, name, value)
        return E5ClaudeTokenPreflightResultV1(
            **data,
            preflight_sha256=_hash_mapping(_preflight_preimage(temporary)),
        )
    except Exception:
        _fail()


__all__ = (
    "E5_CLAUDE_REVIEW_ROUTER_VERSION",
    "E5_CLAUDE_DAILY_USAGE_VERSION",
    "E5_CLAUDE_TOKEN_PREFLIGHT_VERSION",
    "ACTIVE_PROVIDER_BINDING_SHA256",
    "L0",
    "L1",
    "L2",
    "CLAUDE_ROUTES",
    "ROUTE_L0_NO_CLAUDE_REQUIRED",
    "ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE",
    "ROUTE_L1_CLAUDE_REVIEW_REQUIRED",
    "ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED",
    "BLOCK_DUPLICATE_LOGICAL_REVIEW",
    "BLOCK_SHARED_DAILY_REVIEW_CEILING",
    "BLOCK_L2_DAILY_REVIEW_CEILING",
    "E5_CLAUDE_ROUTER_DECISION_CODES",
    "PASS_CLAUDE_TOKEN_BUDGET",
    "HOLD_CLAUDE_INPUT_TOKEN_LIMIT",
    "HOLD_CLAUDE_OUTPUT_TOKEN_LIMIT",
    "HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED",
    "E5_CLAUDE_TOKEN_PREFLIGHT_DECISION_CODES",
    "CLAUDE_L1_MODEL_ID",
    "CLAUDE_L2_MODEL_ID",
    "CLAUDE_L1_MAXIMUM_REVIEW_COST_MICRO_USD",
    "CLAUDE_L2_MAXIMUM_REVIEW_COST_MICRO_USD",
    "SHARED_DAILY_LOGICAL_REVIEW_CEILING",
    "L2_DAILY_LOGICAL_REVIEW_CEILING",
    "MAXIMUM_DAILY_COST_MICRO_USD",
    "E5ClaudeDailyUsageV1",
    "E5ClaudeReviewRouteResultV1",
    "E5ClaudeTokenPreflightResultV1",
    "create_empty_e5_claude_daily_usage_v1",
    "reconstruct_e5_claude_daily_usage_v1",
    "route_e5_claude_review_v1",
    "preflight_e5_claude_review_v1",
)
