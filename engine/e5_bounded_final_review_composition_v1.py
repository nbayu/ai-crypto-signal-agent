"""Detached deterministic composition for bounded E5 final-review evidence."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Callable, Final, Mapping

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
    E5ClaudeDailyUsageV1,
    E5ClaudeReviewRouteResultV1,
    E5ClaudeTokenPreflightResultV1,
    L0,
    L1,
    L2,
    preflight_e5_claude_review_v1,
    reconstruct_e5_claude_daily_usage_v1,
    route_e5_claude_review_v1,
)
from engine.e5_deepseek_technical_review_v1 import (
    CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE,
    CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE,
    STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR,
    STOP_DEEPSEEK_HOLD,
    STOP_DETERMINISTIC_HARD_GATE,
    E5DeepSeekStructuredReviewV1,
    E5DeepSeekTechnicalReviewAdjudicationV1,
    adjudicate_e5_deepseek_technical_review_v1,
    reconstruct_e5_deepseek_structured_review_v1,
)
from engine.e5_provider_invocation_boundary_v1 import (
    ACTIVE_PROVIDER_BINDING_SHA256,
    E5_D8_FAILURE_CODES,
    HOLD_BUDGET_BLOCKED,
    HOLD_ESCALATION_INCOMPLETE,
    HOLD_TOKEN_LIMIT,
    PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED,
    PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED,
    PASS_L0_NO_CLAUDE_REQUIRED,
    E5ClaudeEscalationReviewV1,
    E5ProviderAttemptObservationV1,
    E5ProviderInvocationResultV1,
    E5ProviderRequestV1,
    execute_e5_claude_review_once_v1,
    execute_e5_deepseek_review_once_v1,
)
from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V2_VERSION,
    HOLD_INPUT_TOKEN_LIMIT,
    HOLD_OUTPUT_TOKEN_LIMIT,
    PASS_TOKEN_BUDGET,
    E5TechnicalReviewPayloadV1,
    E5TechnicalReviewTokenPreflightResultV1,
    get_owner_frozen_e5_provider_model_price_binding_v2,
    preflight_e5_technical_review_payload_v1,
    reconstruct_e5_technical_review_payload_v1,
)


E5_BOUNDED_FINAL_REVIEW_COMPOSITION_VERSION: Final = (
    "e5-bounded-final-review-composition-v1"
)
E5_BOUNDED_FINAL_REVIEW_PREPARED_STAGE_VERSION: Final = (
    "e5-bounded-final-review-prepared-stage-v1"
)

PRE_CLAUDE_BLOCK_DEEPSEEK_TOKEN_PREFLIGHT: Final = (
    "PRE_CLAUDE_BLOCK_DEEPSEEK_TOKEN_PREFLIGHT"
)
PRE_CLAUDE_BLOCK_DEEPSEEK_INVOCATION: Final = (
    "PRE_CLAUDE_BLOCK_DEEPSEEK_INVOCATION"
)
PRE_CLAUDE_BLOCK_D6_DETERMINISTIC_POLICY: Final = (
    "PRE_CLAUDE_BLOCK_D6_DETERMINISTIC_POLICY"
)
PRE_CLAUDE_BLOCK_D7_CLAUDE_ROUTING: Final = (
    "PRE_CLAUDE_BLOCK_D7_CLAUDE_ROUTING"
)
PRE_CLAUDE_L0_NO_CLAUDE: Final = "PRE_CLAUDE_L0_NO_CLAUDE"
PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED: Final = (
    "PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED"
)
PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED: Final = (
    "PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED"
)
E5_PRE_CLAUDE_OUTCOME_CODES: Final = (
    PRE_CLAUDE_BLOCK_DEEPSEEK_TOKEN_PREFLIGHT,
    PRE_CLAUDE_BLOCK_DEEPSEEK_INVOCATION,
    PRE_CLAUDE_BLOCK_D6_DETERMINISTIC_POLICY,
    PRE_CLAUDE_BLOCK_D7_CLAUDE_ROUTING,
    PRE_CLAUDE_L0_NO_CLAUDE,
    PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED,
    PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED,
)
PRE_CLAUDE_OUTCOME_CODE_COUNT: Final = 7
PREPARED_STAGE_FIELD_COUNT: Final = 15

CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE: Final = (
    "CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE"
)
CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE: Final = (
    "CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE"
)
BLOCK_DEEPSEEK_TOKEN_PREFLIGHT: Final = "BLOCK_DEEPSEEK_TOKEN_PREFLIGHT"
BLOCK_DEEPSEEK_INVOCATION: Final = "BLOCK_DEEPSEEK_INVOCATION"
BLOCK_D6_DETERMINISTIC_POLICY: Final = "BLOCK_D6_DETERMINISTIC_POLICY"
BLOCK_D7_CLAUDE_ROUTING: Final = "BLOCK_D7_CLAUDE_ROUTING"
BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT: Final = (
    "BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT"
)
BLOCK_D8_CLAUDE_INVOCATION: Final = "BLOCK_D8_CLAUDE_INVOCATION"
BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE: Final = (
    "BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE"
)

E5_BOUNDED_FINAL_REVIEW_OUTCOME_CODES: Final = (
    CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE,
    CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE,
    BLOCK_DEEPSEEK_TOKEN_PREFLIGHT,
    BLOCK_DEEPSEEK_INVOCATION,
    BLOCK_D6_DETERMINISTIC_POLICY,
    BLOCK_D7_CLAUDE_ROUTING,
    BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT,
    BLOCK_D8_CLAUDE_INVOCATION,
    BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE,
)
FINAL_OUTCOME_CODE_COUNT: Final = 9
COMPOSITION_FIELD_COUNT: Final = 25

_CONTINUE_CODES: Final = frozenset(
    (
        CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE,
        CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE,
    )
)
_D6_BLOCK_CODES: Final = frozenset(
    (STOP_DETERMINISTIC_HARD_GATE, STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR)
)
_ROUTE_BLOCK_CODES: Final = frozenset(
    (
        BLOCK_DUPLICATE_LOGICAL_REVIEW,
        BLOCK_SHARED_DAILY_REVIEW_CEILING,
        BLOCK_L2_DAILY_REVIEW_CEILING,
    )
)
_ALLOWED_ROUTE_CODES: Final = frozenset(
    (
        ROUTE_L1_CLAUDE_REVIEW_REQUIRED,
        ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED,
    )
)
_ERROR: Final = "invalid E5 bounded final review composition"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")


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
    binding = get_owner_frozen_e5_provider_model_price_binding_v2()
    _require(
        binding.binding_version == E5_PROVIDER_MODEL_PRICE_BINDING_V2_VERSION
    )
    _require(binding.binding_sha256 == ACTIVE_PROVIDER_BINDING_SHA256)
    return binding


def _validate_payload(value: object) -> E5TechnicalReviewPayloadV1:
    _require(type(value) is E5TechnicalReviewPayloadV1)
    value.__post_init__()
    _require(value.provider_binding_sha256 == _active_binding().binding_sha256)
    return value


def _validate_usage(value: object) -> E5ClaudeDailyUsageV1:
    _require(type(value) is E5ClaudeDailyUsageV1)
    value.__post_init__()
    return value


def _payload_utc_day(payload: E5TechnicalReviewPayloadV1) -> str:
    trigger_age = payload.to_mapping()["trigger_age"]
    _require(type(trigger_age) is dict)
    timestamp = trigger_age.get("evaluation_timestamp")
    _require(type(timestamp) is str)
    _require(
        re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
            timestamp,
        )
        is not None
    )
    return timestamp[:10]


def _nested_mapping(value: object) -> object:
    return None if value is None else value.to_mapping()


def _composition_preimage(
    result: "E5BoundedFinalReviewCompositionV1",
) -> dict[str, object]:
    return {
        "composition_version": result.composition_version,
        "provider_binding_sha256": result.provider_binding_sha256,
        "payload_sha256": result.payload_sha256,
        "deepseek_token_preflight": result.deepseek_token_preflight.to_mapping(),
        "deepseek_invocation_result": result.deepseek_invocation_result.to_mapping(),
        "accepted_deepseek_review": _nested_mapping(
            result.accepted_deepseek_review
        ),
        "deepseek_adjudication": _nested_mapping(result.deepseek_adjudication),
        "claude_route_result": _nested_mapping(result.claude_route_result),
        "claude_token_preflight": _nested_mapping(result.claude_token_preflight),
        "claude_invocation_result": _nested_mapping(
            result.claude_invocation_result
        ),
        "accepted_claude_review": _nested_mapping(result.accepted_claude_review),
        "usage_before": result.usage_before.to_mapping(),
        "usage_after": result.usage_after.to_mapping(),
        "underlying_d8_cause": result.underlying_d8_cause,
        "final_outcome_code": result.final_outcome_code,
        "may_continue_to_python_final_gate": (
            result.may_continue_to_python_final_gate
        ),
        "publication_blocked": result.publication_blocked,
        "deepseek_provider_attempt_count": result.deepseek_provider_attempt_count,
        "claude_provider_attempt_count": result.claude_provider_attempt_count,
        "retry_count": result.retry_count,
        "publication_allowed": result.publication_allowed,
        "telegram_send_allowed": result.telegram_send_allowed,
        "slot_mutation_allowed": result.slot_mutation_allowed,
        "pair_lock_mutation_allowed": result.pair_lock_mutation_allowed,
    }


def _expected_outcome(
    result: "E5BoundedFinalReviewCompositionV1",
) -> tuple[str, bool, bool, str | None]:
    deep_preflight = result.deepseek_token_preflight
    deep_result = result.deepseek_invocation_result
    if deep_preflight.decision_code != PASS_TOKEN_BUDGET:
        return (
            BLOCK_DEEPSEEK_TOKEN_PREFLIGHT,
            False,
            True,
            deep_result.underlying_failure_code,
        )
    if deep_result.final_result_code != PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED:
        return (
            BLOCK_DEEPSEEK_INVOCATION,
            False,
            True,
            deep_result.underlying_failure_code,
        )
    adjudication = result.deepseek_adjudication
    route = result.claude_route_result
    claude_preflight = result.claude_token_preflight
    claude_result = result.claude_invocation_result
    _require(adjudication is not None)
    _require(route is not None)
    _require(claude_preflight is not None)
    _require(claude_result is not None)
    if adjudication.outcome_code in _D6_BLOCK_CODES:
        return BLOCK_D6_DETERMINISTIC_POLICY, False, True, None
    if route.decision_code in _ROUTE_BLOCK_CODES:
        return (
            BLOCK_D7_CLAUDE_ROUTING,
            False,
            True,
            claude_result.underlying_failure_code,
        )
    if route.decision_code == ROUTE_L0_NO_CLAUDE_REQUIRED:
        return CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE, True, False, None
    _require(route.decision_code in _ALLOWED_ROUTE_CODES)
    if claude_preflight.decision_code != PASS_CLAUDE_TOKEN_BUDGET:
        return BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT, False, True, HOLD_TOKEN_LIMIT
    if claude_result.final_result_code != PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED:
        cause = (
            claude_result.underlying_failure_code
            if claude_result.underlying_failure_code is not None
            else claude_result.final_result_code
        )
        return BLOCK_D8_CLAUDE_INVOCATION, False, True, cause
    if route.route == L1:
        return (
            CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE,
            True,
            False,
            None,
        )
    _require(route.route == L2)
    return BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE, False, True, None


def _prepared_stage_preimage(
    stage: "E5BoundedFinalReviewPreparedStageV1",
) -> dict[str, object]:
    return {
        "prepared_stage_version": stage.prepared_stage_version,
        "provider_binding_sha256": stage.provider_binding_sha256,
        "payload": stage.payload.to_mapping(),
        "payload_sha256": stage.payload_sha256,
        "deepseek_token_preflight": stage.deepseek_token_preflight.to_mapping(),
        "deepseek_invocation_result": (
            stage.deepseek_invocation_result.to_mapping()
        ),
        "accepted_deepseek_review": _nested_mapping(
            stage.accepted_deepseek_review
        ),
        "deepseek_adjudication": _nested_mapping(stage.deepseek_adjudication),
        "claude_route_result": _nested_mapping(stage.claude_route_result),
        "usage_before": stage.usage_before.to_mapping(),
        "usage_after": stage.usage_after.to_mapping(),
        "pre_claude_outcome_code": stage.pre_claude_outcome_code,
        "deepseek_provider_attempt_count": (
            stage.deepseek_provider_attempt_count
        ),
        "retry_count": stage.retry_count,
    }


def _expected_pre_claude_outcome(
    stage: "E5BoundedFinalReviewPreparedStageV1",
) -> str:
    if stage.deepseek_token_preflight.decision_code != PASS_TOKEN_BUDGET:
        return PRE_CLAUDE_BLOCK_DEEPSEEK_TOKEN_PREFLIGHT
    if (
        stage.deepseek_invocation_result.final_result_code
        != PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED
    ):
        return PRE_CLAUDE_BLOCK_DEEPSEEK_INVOCATION
    adjudication = stage.deepseek_adjudication
    route = stage.claude_route_result
    _require(adjudication is not None)
    _require(route is not None)
    if adjudication.outcome_code in _D6_BLOCK_CODES:
        return PRE_CLAUDE_BLOCK_D6_DETERMINISTIC_POLICY
    if route.decision_code in _ROUTE_BLOCK_CODES:
        return PRE_CLAUDE_BLOCK_D7_CLAUDE_ROUTING
    if route.decision_code == ROUTE_L0_NO_CLAUDE_REQUIRED:
        return PRE_CLAUDE_L0_NO_CLAUDE
    if route.decision_code == ROUTE_L1_CLAUDE_REVIEW_REQUIRED:
        return PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED
    _require(
        route.decision_code
        == ROUTE_L2_CLAUDE_REVIEW_REQUIRED_DEEPSEEK_HOLD_PRESERVED
    )
    return PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED


@dataclass(frozen=True, slots=True)
class E5BoundedFinalReviewPreparedStageV1:
    prepared_stage_version: str
    provider_binding_sha256: str
    payload: E5TechnicalReviewPayloadV1
    payload_sha256: str
    deepseek_token_preflight: E5TechnicalReviewTokenPreflightResultV1
    deepseek_invocation_result: E5ProviderInvocationResultV1
    accepted_deepseek_review: E5DeepSeekStructuredReviewV1 | None
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1 | None
    claude_route_result: E5ClaudeReviewRouteResultV1 | None
    usage_before: E5ClaudeDailyUsageV1
    usage_after: E5ClaudeDailyUsageV1
    pre_claude_outcome_code: str
    deepseek_provider_attempt_count: int
    retry_count: int
    prepared_stage_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                self.prepared_stage_version
                == E5_BOUNDED_FINAL_REVIEW_PREPARED_STAGE_VERSION
            )
            _require(
                self.provider_binding_sha256
                == ACTIVE_PROVIDER_BINDING_SHA256
            )
            payload = _validate_payload(self.payload)
            _require(self.payload_sha256 == payload.payload_sha256)
            _require(
                type(self.deepseek_token_preflight)
                is E5TechnicalReviewTokenPreflightResultV1
            )
            self.deepseek_token_preflight.__post_init__()
            _require(
                self.deepseek_token_preflight.payload_sha256
                == self.payload_sha256
            )
            _require(
                type(self.deepseek_invocation_result)
                is E5ProviderInvocationResultV1
            )
            self.deepseek_invocation_result.__post_init__()
            _require(
                self.deepseek_invocation_result.provider_binding_sha256
                == self.provider_binding_sha256
            )
            _require(
                self.deepseek_invocation_result.payload_sha256
                == self.payload_sha256
            )
            usage_before = _validate_usage(self.usage_before)
            usage_after = _validate_usage(self.usage_after)
            _require(usage_before.utc_day == _payload_utc_day(payload))
            _require(usage_after.utc_day == usage_before.utc_day)
            _require(type(self.deepseek_provider_attempt_count) is int)
            _require(self.deepseek_provider_attempt_count in (0, 1))
            _require(
                self.deepseek_provider_attempt_count
                == self.deepseek_invocation_result.provider_attempt_count
            )
            _require(type(self.retry_count) is int and self.retry_count == 0)
            has_review = self.accepted_deepseek_review is not None
            _require(has_review == (self.deepseek_adjudication is not None))
            _require(has_review == (self.claude_route_result is not None))
            if not has_review:
                _require(
                    self.deepseek_invocation_result.final_result_code
                    != PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED
                )
                _require(usage_after == usage_before)
            else:
                review = self.accepted_deepseek_review
                adjudication = self.deepseek_adjudication
                route = self.claude_route_result
                _require(type(review) is E5DeepSeekStructuredReviewV1)
                _require(
                    type(adjudication)
                    is E5DeepSeekTechnicalReviewAdjudicationV1
                )
                _require(type(route) is E5ClaudeReviewRouteResultV1)
                review.__post_init__()
                adjudication.__post_init__()
                route.__post_init__()
                _require(
                    self.deepseek_invocation_result.final_result_code
                    == PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED
                )
                _require(
                    self.deepseek_invocation_result.accepted_response_sha256
                    == review.review_sha256
                )
                _require(review.payload_sha256 == self.payload_sha256)
                _require(adjudication.payload_sha256 == self.payload_sha256)
                _require(adjudication.review_sha256 == review.review_sha256)
                _require(route.payload_sha256 == self.payload_sha256)
                _require(
                    route.provider_binding_sha256
                    == self.provider_binding_sha256
                )
                _require(route.deepseek_review_sha256 == review.review_sha256)
                _require(
                    route.deepseek_adjudication_sha256
                    == adjudication.adjudication_sha256
                )
                _require(route.usage_before_sha256 == usage_before.usage_sha256)
                _require(route.usage_after == usage_after)
                if route.decision_code in _ALLOWED_ROUTE_CODES:
                    _require(usage_after != usage_before)
                else:
                    _require(usage_after == usage_before)
            _require(
                self.pre_claude_outcome_code in E5_PRE_CLAUDE_OUTCOME_CODES
            )
            _require(
                self.pre_claude_outcome_code
                == _expected_pre_claude_outcome(self)
            )
            _require(_valid_sha256(self.prepared_stage_sha256))
            _require(
                self.prepared_stage_sha256
                == _hash_mapping(_prepared_stage_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_prepared_stage_preimage(self),
            "prepared_stage_sha256": self.prepared_stage_sha256,
        }

    def canonical_prepared_stage_json(self) -> str:
        return _canonical_json(_prepared_stage_preimage(self))


def _reconstruct_preflight(
    mapping: object,
) -> E5TechnicalReviewTokenPreflightResultV1:
    _require(type(mapping) is dict)
    expected = frozenset(
        (
            "preflight_version",
            "payload_sha256",
            "model_id",
            "measured_input_tokens",
            "requested_output_tokens",
            "input_hard_limit_tokens",
            "output_hard_limit_tokens",
            "within_limits",
            "decision_code",
            "preflight_sha256",
        )
    )
    _require(frozenset(mapping) == expected)
    return E5TechnicalReviewTokenPreflightResultV1(**mapping)


def _reconstruct_invocation_result(
    mapping: object,
) -> E5ProviderInvocationResultV1:
    _require(type(mapping) is dict)
    expected = frozenset(
        (
            "result_version",
            "provider_binding_sha256",
            "payload_sha256",
            "route_sha256",
            "provider",
            "invocation_role",
            "model_id",
            "request_sha256",
            "transport_invoked",
            "provider_attempt_count",
            "retry_count",
            "underlying_failure_code",
            "final_result_code",
            "accepted_response_sha256",
            "response_digest_sha256",
            "publication_allowed",
            "telegram_send_allowed",
            "slot_mutation_allowed",
            "pair_lock_mutation_allowed",
            "retry_allowed",
            "fallback_allowed",
            "stale_result_reuse_allowed",
            "result_sha256",
        )
    )
    _require(frozenset(mapping) == expected)
    return E5ProviderInvocationResultV1(**mapping)


def _reconstruct_adjudication(
    mapping: object,
) -> E5DeepSeekTechnicalReviewAdjudicationV1:
    _require(type(mapping) is dict)
    expected = frozenset(
        (
            "adjudication_version",
            "policy_version",
            "payload_sha256",
            "model_id",
            "review_decision",
            "reason_codes",
            "review_sha256",
            "pre_review_score",
            "score_penalty",
            "final_score",
            "mode_score_floor",
            "deterministic_hard_gates_passed",
            "may_continue_to_python_final_gate",
            "publication_blocked",
            "hold_blocks_current_trigger_generation",
            "hold_retains_armed_when_lifecycle_valid",
            "outcome_code",
            "adjudication_sha256",
        )
    )
    _require(frozenset(mapping) == expected)
    _require(type(mapping["reason_codes"]) is list)
    data = dict(mapping)
    data["reason_codes"] = tuple(mapping["reason_codes"])
    return E5DeepSeekTechnicalReviewAdjudicationV1(**data)


def _reconstruct_route(mapping: object) -> E5ClaudeReviewRouteResultV1:
    _require(type(mapping) is dict)
    expected = frozenset(
        (
            "router_version",
            "provider_binding_sha256",
            "payload_sha256",
            "deepseek_review_sha256",
            "deepseek_adjudication_sha256",
            "route",
            "claude_required",
            "model_id",
            "input_hard_limit_tokens",
            "output_hard_limit_tokens",
            "timeout_seconds",
            "provider_attempts",
            "retry_count",
            "maximum_review_cost_micro_usd",
            "deepseek_publication_block_preserved",
            "usage_before_sha256",
            "usage_after",
            "decision_code",
            "route_sha256",
        )
    )
    _require(frozenset(mapping) == expected)
    data = dict(mapping)
    data["usage_after"] = reconstruct_e5_claude_daily_usage_v1(
        mapping["usage_after"]
    )
    return E5ClaudeReviewRouteResultV1(**data)


def reconstruct_e5_bounded_final_review_prepared_stage_v1(
    mapping: Mapping[str, object],
) -> E5BoundedFinalReviewPreparedStageV1:
    try:
        expected = frozenset(
            (
                "prepared_stage_version",
                "provider_binding_sha256",
                "payload",
                "payload_sha256",
                "deepseek_token_preflight",
                "deepseek_invocation_result",
                "accepted_deepseek_review",
                "deepseek_adjudication",
                "claude_route_result",
                "usage_before",
                "usage_after",
                "pre_claude_outcome_code",
                "deepseek_provider_attempt_count",
                "retry_count",
                "prepared_stage_sha256",
            )
        )
        _require(type(mapping) is dict)
        _require(frozenset(mapping) == expected)
        review_mapping = mapping["accepted_deepseek_review"]
        adjudication_mapping = mapping["deepseek_adjudication"]
        route_mapping = mapping["claude_route_result"]
        review = (
            None
            if review_mapping is None
            else reconstruct_e5_deepseek_structured_review_v1(review_mapping)
        )
        adjudication = (
            None
            if adjudication_mapping is None
            else _reconstruct_adjudication(adjudication_mapping)
        )
        route = (
            None if route_mapping is None else _reconstruct_route(route_mapping)
        )
        return E5BoundedFinalReviewPreparedStageV1(
            prepared_stage_version=mapping["prepared_stage_version"],
            provider_binding_sha256=mapping["provider_binding_sha256"],
            payload=reconstruct_e5_technical_review_payload_v1(
                mapping["payload"]
            ),
            payload_sha256=mapping["payload_sha256"],
            deepseek_token_preflight=_reconstruct_preflight(
                mapping["deepseek_token_preflight"]
            ),
            deepseek_invocation_result=_reconstruct_invocation_result(
                mapping["deepseek_invocation_result"]
            ),
            accepted_deepseek_review=review,
            deepseek_adjudication=adjudication,
            claude_route_result=route,
            usage_before=reconstruct_e5_claude_daily_usage_v1(
                mapping["usage_before"]
            ),
            usage_after=reconstruct_e5_claude_daily_usage_v1(
                mapping["usage_after"]
            ),
            pre_claude_outcome_code=mapping["pre_claude_outcome_code"],
            deepseek_provider_attempt_count=(
                mapping["deepseek_provider_attempt_count"]
            ),
            retry_count=mapping["retry_count"],
            prepared_stage_sha256=mapping["prepared_stage_sha256"],
        )
    except Exception:
        _fail()


def _build_prepared_stage(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deepseek_token_preflight: E5TechnicalReviewTokenPreflightResultV1,
    deepseek_invocation_result: E5ProviderInvocationResultV1,
    accepted_deepseek_review: E5DeepSeekStructuredReviewV1 | None,
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1 | None,
    claude_route_result: E5ClaudeReviewRouteResultV1 | None,
    usage_before: E5ClaudeDailyUsageV1,
    usage_after: E5ClaudeDailyUsageV1,
) -> E5BoundedFinalReviewPreparedStageV1:
    temporary = object.__new__(E5BoundedFinalReviewPreparedStageV1)
    data: dict[str, object] = {
        "prepared_stage_version": (
            E5_BOUNDED_FINAL_REVIEW_PREPARED_STAGE_VERSION
        ),
        "provider_binding_sha256": ACTIVE_PROVIDER_BINDING_SHA256,
        "payload": payload,
        "payload_sha256": payload.payload_sha256,
        "deepseek_token_preflight": deepseek_token_preflight,
        "deepseek_invocation_result": deepseek_invocation_result,
        "accepted_deepseek_review": accepted_deepseek_review,
        "deepseek_adjudication": deepseek_adjudication,
        "claude_route_result": claude_route_result,
        "usage_before": usage_before,
        "usage_after": usage_after,
        "deepseek_provider_attempt_count": (
            deepseek_invocation_result.provider_attempt_count
        ),
        "retry_count": 0,
    }
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    object.__setattr__(
        temporary,
        "pre_claude_outcome_code",
        _expected_pre_claude_outcome(temporary),
    )
    data["pre_claude_outcome_code"] = temporary.pre_claude_outcome_code
    return E5BoundedFinalReviewPreparedStageV1(
        **data,
        prepared_stage_sha256=_hash_mapping(
            _prepared_stage_preimage(temporary)
        ),
    )


@dataclass(frozen=True, slots=True)
class E5BoundedFinalReviewCompositionV1:
    composition_version: str
    provider_binding_sha256: str
    payload_sha256: str
    deepseek_token_preflight: E5TechnicalReviewTokenPreflightResultV1
    deepseek_invocation_result: E5ProviderInvocationResultV1
    accepted_deepseek_review: E5DeepSeekStructuredReviewV1 | None
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1 | None
    claude_route_result: E5ClaudeReviewRouteResultV1 | None
    claude_token_preflight: E5ClaudeTokenPreflightResultV1 | None
    claude_invocation_result: E5ProviderInvocationResultV1 | None
    accepted_claude_review: E5ClaudeEscalationReviewV1 | None
    usage_before: E5ClaudeDailyUsageV1
    usage_after: E5ClaudeDailyUsageV1
    underlying_d8_cause: str | None
    final_outcome_code: str
    may_continue_to_python_final_gate: bool
    publication_blocked: bool
    deepseek_provider_attempt_count: int
    claude_provider_attempt_count: int
    retry_count: int
    publication_allowed: bool
    telegram_send_allowed: bool
    slot_mutation_allowed: bool
    pair_lock_mutation_allowed: bool
    composition_sha256: str

    def __post_init__(self) -> None:
        try:
            binding = _active_binding()
            _require(
                self.composition_version
                == E5_BOUNDED_FINAL_REVIEW_COMPOSITION_VERSION
            )
            _require(self.provider_binding_sha256 == binding.binding_sha256)
            _require(_valid_sha256(self.payload_sha256))
            _require(
                type(self.deepseek_token_preflight)
                is E5TechnicalReviewTokenPreflightResultV1
            )
            self.deepseek_token_preflight.__post_init__()
            _require(
                self.deepseek_token_preflight.payload_sha256
                == self.payload_sha256
            )
            _require(
                type(self.deepseek_invocation_result)
                is E5ProviderInvocationResultV1
            )
            self.deepseek_invocation_result.__post_init__()
            _require(
                self.deepseek_invocation_result.payload_sha256
                == self.payload_sha256
            )
            _require(
                self.deepseek_invocation_result.provider_binding_sha256
                == self.provider_binding_sha256
            )
            usage_before = _validate_usage(self.usage_before)
            usage_after = _validate_usage(self.usage_after)
            _require(usage_before.utc_day == usage_after.utc_day)
            for value in (
                self.deepseek_provider_attempt_count,
                self.claude_provider_attempt_count,
                self.retry_count,
            ):
                _require(type(value) is int)
            _require(self.deepseek_provider_attempt_count in (0, 1))
            _require(self.claude_provider_attempt_count in (0, 1))
            _require(self.retry_count == 0)
            _require(
                self.deepseek_provider_attempt_count
                == self.deepseek_invocation_result.provider_attempt_count
            )
            if self.deepseek_token_preflight.decision_code != PASS_TOKEN_BUDGET:
                _require(
                    self.deepseek_invocation_result.final_result_code
                    == HOLD_TOKEN_LIMIT
                )
                _require(self.deepseek_provider_attempt_count == 0)
            _require(
                type(self.may_continue_to_python_final_gate) is bool
            )
            _require(type(self.publication_blocked) is bool)
            for authority in (
                self.publication_allowed,
                self.telegram_send_allowed,
                self.slot_mutation_allowed,
                self.pair_lock_mutation_allowed,
            ):
                _require(type(authority) is bool and authority is False)
            _require(
                self.underlying_d8_cause is None
                or self.underlying_d8_cause in E5_D8_FAILURE_CODES
            )
            _require(
                self.final_outcome_code
                in E5_BOUNDED_FINAL_REVIEW_OUTCOME_CODES
            )

            has_review = self.accepted_deepseek_review is not None
            has_adjudication = self.deepseek_adjudication is not None
            has_route = self.claude_route_result is not None
            _require(has_review == has_adjudication == has_route)
            if not has_review:
                _require(self.claude_token_preflight is None)
                _require(self.claude_invocation_result is None)
                _require(self.accepted_claude_review is None)
                _require(usage_after == usage_before)
                _require(self.claude_provider_attempt_count == 0)
            else:
                review = self.accepted_deepseek_review
                adjudication = self.deepseek_adjudication
                route = self.claude_route_result
                _require(type(review) is E5DeepSeekStructuredReviewV1)
                _require(
                    type(adjudication)
                    is E5DeepSeekTechnicalReviewAdjudicationV1
                )
                _require(type(route) is E5ClaudeReviewRouteResultV1)
                review.__post_init__()
                adjudication.__post_init__()
                route.__post_init__()
                _require(
                    self.deepseek_invocation_result.final_result_code
                    == PASS_DEEPSEEK_STRUCTURED_REVIEW_ACCEPTED
                )
                _require(
                    self.deepseek_invocation_result.accepted_response_sha256
                    == review.review_sha256
                )
                _require(review.payload_sha256 == self.payload_sha256)
                _require(adjudication.payload_sha256 == self.payload_sha256)
                _require(adjudication.review_sha256 == review.review_sha256)
                _require(route.payload_sha256 == self.payload_sha256)
                _require(route.provider_binding_sha256 == self.provider_binding_sha256)
                _require(route.deepseek_review_sha256 == review.review_sha256)
                _require(
                    route.deepseek_adjudication_sha256
                    == adjudication.adjudication_sha256
                )
                _require(route.usage_before_sha256 == usage_before.usage_sha256)
                _require(route.usage_after == usage_after)
                _require(
                    type(self.claude_token_preflight)
                    is E5ClaudeTokenPreflightResultV1
                )
                self.claude_token_preflight.__post_init__()
                _require(
                    self.claude_token_preflight.provider_binding_sha256
                    == self.provider_binding_sha256
                )
                _require(
                    self.claude_token_preflight.payload_sha256
                    == self.payload_sha256
                )
                _require(
                    self.claude_token_preflight.route_sha256
                    == route.route_sha256
                )
                _require(
                    type(self.claude_invocation_result)
                    is E5ProviderInvocationResultV1
                )
                self.claude_invocation_result.__post_init__()
                _require(
                    self.claude_invocation_result.provider_binding_sha256
                    == self.provider_binding_sha256
                )
                _require(
                    self.claude_invocation_result.payload_sha256
                    == self.payload_sha256
                )
                _require(
                    self.claude_invocation_result.route_sha256
                    == route.route_sha256
                )
                _require(
                    self.claude_provider_attempt_count
                    == self.claude_invocation_result.provider_attempt_count
                )
                if route.decision_code in (
                    ROUTE_L0_NO_CLAUDE_REQUIRED,
                    ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE,
                    *_ROUTE_BLOCK_CODES,
                ):
                    _require(
                        self.claude_token_preflight.decision_code
                        == HOLD_CLAUDE_ROUTE_NOT_AUTHORIZED
                    )
                    _require(
                        self.claude_token_preflight.measured_input_tokens == 0
                    )
                    _require(
                        self.claude_token_preflight.requested_output_tokens == 0
                    )
                    _require(self.claude_provider_attempt_count == 0)
                if route.decision_code in (
                    ROUTE_L0_NO_CLAUDE_REQUIRED,
                    ROUTE_L0_DETERMINISTIC_BLOCK_NO_CLAUDE,
                ):
                    _require(
                        self.claude_invocation_result.final_result_code
                        == PASS_L0_NO_CLAUDE_REQUIRED
                    )
                elif route.decision_code == BLOCK_DUPLICATE_LOGICAL_REVIEW:
                    _require(
                        self.claude_invocation_result.final_result_code
                        == HOLD_ESCALATION_INCOMPLETE
                    )
                elif route.decision_code in (
                    BLOCK_SHARED_DAILY_REVIEW_CEILING,
                    BLOCK_L2_DAILY_REVIEW_CEILING,
                ):
                    _require(
                        self.claude_invocation_result.final_result_code
                        == HOLD_BUDGET_BLOCKED
                    )
                elif self.claude_token_preflight.decision_code != (
                    PASS_CLAUDE_TOKEN_BUDGET
                ):
                    _require(
                        self.claude_invocation_result.final_result_code
                        == HOLD_TOKEN_LIMIT
                    )
                    _require(self.claude_provider_attempt_count == 0)
                else:
                    _require(self.claude_provider_attempt_count == 1)
                if self.accepted_claude_review is None:
                    _require(
                        self.claude_invocation_result.final_result_code
                        != PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED
                    )
                else:
                    claude_review = self.accepted_claude_review
                    _require(type(claude_review) is E5ClaudeEscalationReviewV1)
                    claude_review.__post_init__()
                    _require(
                        self.claude_invocation_result.final_result_code
                        == PASS_CLAUDE_ESCALATION_REVIEW_ACCEPTED
                    )
                    _require(
                        self.claude_invocation_result.accepted_response_sha256
                        == claude_review.review_sha256
                    )
                    _require(claude_review.payload_sha256 == self.payload_sha256)
                    _require(claude_review.route_sha256 == route.route_sha256)
                    _require(
                        claude_review.provider_binding_sha256
                        == self.provider_binding_sha256
                    )

            expected = _expected_outcome(self)
            _require(
                (
                    self.final_outcome_code,
                    self.may_continue_to_python_final_gate,
                    self.publication_blocked,
                    self.underlying_d8_cause,
                )
                == expected
            )
            _require(
                self.may_continue_to_python_final_gate
                == (self.final_outcome_code in _CONTINUE_CODES)
            )
            _require(_valid_sha256(self.composition_sha256))
            _require(
                self.composition_sha256
                == _hash_mapping(_composition_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_composition_preimage(self),
            "composition_sha256": self.composition_sha256,
        }

    def canonical_composition_json(self) -> str:
        return _canonical_json(_composition_preimage(self))


def _build_composition(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deepseek_token_preflight: E5TechnicalReviewTokenPreflightResultV1,
    deepseek_invocation_result: E5ProviderInvocationResultV1,
    accepted_deepseek_review: E5DeepSeekStructuredReviewV1 | None,
    deepseek_adjudication: E5DeepSeekTechnicalReviewAdjudicationV1 | None,
    claude_route_result: E5ClaudeReviewRouteResultV1 | None,
    claude_token_preflight: E5ClaudeTokenPreflightResultV1 | None,
    claude_invocation_result: E5ProviderInvocationResultV1 | None,
    accepted_claude_review: E5ClaudeEscalationReviewV1 | None,
    usage_before: E5ClaudeDailyUsageV1,
    usage_after: E5ClaudeDailyUsageV1,
) -> E5BoundedFinalReviewCompositionV1:
    temporary = object.__new__(E5BoundedFinalReviewCompositionV1)
    base: dict[str, object] = {
        "composition_version": E5_BOUNDED_FINAL_REVIEW_COMPOSITION_VERSION,
        "provider_binding_sha256": ACTIVE_PROVIDER_BINDING_SHA256,
        "payload_sha256": payload.payload_sha256,
        "deepseek_token_preflight": deepseek_token_preflight,
        "deepseek_invocation_result": deepseek_invocation_result,
        "accepted_deepseek_review": accepted_deepseek_review,
        "deepseek_adjudication": deepseek_adjudication,
        "claude_route_result": claude_route_result,
        "claude_token_preflight": claude_token_preflight,
        "claude_invocation_result": claude_invocation_result,
        "accepted_claude_review": accepted_claude_review,
        "usage_before": usage_before,
        "usage_after": usage_after,
        "deepseek_provider_attempt_count": (
            deepseek_invocation_result.provider_attempt_count
        ),
        "claude_provider_attempt_count": (
            0
            if claude_invocation_result is None
            else claude_invocation_result.provider_attempt_count
        ),
        "retry_count": 0,
        "publication_allowed": False,
        "telegram_send_allowed": False,
        "slot_mutation_allowed": False,
        "pair_lock_mutation_allowed": False,
    }
    for name, value in base.items():
        object.__setattr__(temporary, name, value)
    outcome = _expected_outcome(temporary)
    outcome_data: dict[str, object] = {
        "underlying_d8_cause": outcome[3],
        "final_outcome_code": outcome[0],
        "may_continue_to_python_final_gate": outcome[1],
        "publication_blocked": outcome[2],
    }
    data = {**base, **outcome_data}
    for name, value in outcome_data.items():
        object.__setattr__(temporary, name, value)
    return E5BoundedFinalReviewCompositionV1(
        **data,
        composition_sha256=_hash_mapping(_composition_preimage(temporary)),
    )


def _validate_prepare_inputs(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deterministic_hard_gates_passed: bool,
    pre_review_score: int,
    mode_score_floor: int,
    daily_usage: E5ClaudeDailyUsageV1,
    deepseek_measured_input_tokens: int,
    deepseek_requested_output_tokens: int,
    deepseek_transport: Callable[
        [E5ProviderRequestV1], E5ProviderAttemptObservationV1
    ],
) -> tuple[E5TechnicalReviewPayloadV1, E5ClaudeDailyUsageV1]:
    verified_payload = _validate_payload(payload)
    usage_before = _validate_usage(daily_usage)
    _require(usage_before.utc_day == _payload_utc_day(verified_payload))
    _require(type(deterministic_hard_gates_passed) is bool)
    _require(type(pre_review_score) is int)
    _require(type(mode_score_floor) is int)
    _require(
        type(deepseek_measured_input_tokens) is int
        and deepseek_measured_input_tokens >= 0
    )
    _require(
        type(deepseek_requested_output_tokens) is int
        and deepseek_requested_output_tokens >= 0
    )
    _require(callable(deepseek_transport))
    return verified_payload, usage_before


def _prepare_e5_bounded_final_review_core_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deterministic_hard_gates_passed: bool,
    pre_review_score: int,
    mode_score_floor: int,
    daily_usage: E5ClaudeDailyUsageV1,
    deepseek_measured_input_tokens: int,
    deepseek_requested_output_tokens: int,
    deepseek_transport: Callable[
        [E5ProviderRequestV1], E5ProviderAttemptObservationV1
    ],
) -> E5BoundedFinalReviewPreparedStageV1:
    deepseek_preflight = preflight_e5_technical_review_payload_v1(
        payload=payload,
        measured_input_tokens=deepseek_measured_input_tokens,
        requested_output_tokens=deepseek_requested_output_tokens,
    )
    deepseek_execution = execute_e5_deepseek_review_once_v1(
        payload=payload,
        token_preflight=deepseek_preflight,
        transport=deepseek_transport,
    )
    deepseek_result = deepseek_execution.invocation_result
    deepseek_review = deepseek_execution.accepted_deepseek_review
    if deepseek_review is None:
        return _build_prepared_stage(
            payload=payload,
            deepseek_token_preflight=deepseek_preflight,
            deepseek_invocation_result=deepseek_result,
            accepted_deepseek_review=None,
            deepseek_adjudication=None,
            claude_route_result=None,
            usage_before=daily_usage,
            usage_after=daily_usage,
        )
    adjudication = adjudicate_e5_deepseek_technical_review_v1(
        payload=payload,
        review=deepseek_review,
        deterministic_hard_gates_passed=deterministic_hard_gates_passed,
        pre_review_score=pre_review_score,
        mode_score_floor=mode_score_floor,
    )
    route = route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=deepseek_review,
        deepseek_adjudication=adjudication,
        daily_usage=daily_usage,
    )
    usage_after = (
        route.usage_after
        if route.decision_code in _ALLOWED_ROUTE_CODES
        else daily_usage
    )
    return _build_prepared_stage(
        payload=payload,
        deepseek_token_preflight=deepseek_preflight,
        deepseek_invocation_result=deepseek_result,
        accepted_deepseek_review=deepseek_review,
        deepseek_adjudication=adjudication,
        claude_route_result=route,
        usage_before=daily_usage,
        usage_after=usage_after,
    )


def prepare_e5_bounded_final_review_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deterministic_hard_gates_passed: bool,
    pre_review_score: int,
    mode_score_floor: int,
    daily_usage: E5ClaudeDailyUsageV1,
    deepseek_measured_input_tokens: int,
    deepseek_requested_output_tokens: int,
    deepseek_transport: Callable[
        [E5ProviderRequestV1], E5ProviderAttemptObservationV1
    ],
) -> E5BoundedFinalReviewPreparedStageV1:
    try:
        verified_payload, usage_before = _validate_prepare_inputs(
            payload=payload,
            deterministic_hard_gates_passed=deterministic_hard_gates_passed,
            pre_review_score=pre_review_score,
            mode_score_floor=mode_score_floor,
            daily_usage=daily_usage,
            deepseek_measured_input_tokens=deepseek_measured_input_tokens,
            deepseek_requested_output_tokens=deepseek_requested_output_tokens,
            deepseek_transport=deepseek_transport,
        )
        return _prepare_e5_bounded_final_review_core_v1(
            payload=verified_payload,
            deterministic_hard_gates_passed=deterministic_hard_gates_passed,
            pre_review_score=pre_review_score,
            mode_score_floor=mode_score_floor,
            daily_usage=usage_before,
            deepseek_measured_input_tokens=deepseek_measured_input_tokens,
            deepseek_requested_output_tokens=deepseek_requested_output_tokens,
            deepseek_transport=deepseek_transport,
        )
    except Exception:
        _fail()


def _resume_e5_bounded_final_review_core_v1(
    *,
    prepared_stage: E5BoundedFinalReviewPreparedStageV1,
    confirmed_usage_after_sha256: str | None,
    claude_measured_input_tokens: int | None,
    claude_requested_output_tokens: int | None,
    claude_transport: Callable[
        [E5ProviderRequestV1], E5ProviderAttemptObservationV1
    ],
) -> E5BoundedFinalReviewCompositionV1:
    route = prepared_stage.claude_route_result
    if route is None:
        _require(confirmed_usage_after_sha256 is None)
        return _build_composition(
            payload=prepared_stage.payload,
            deepseek_token_preflight=prepared_stage.deepseek_token_preflight,
            deepseek_invocation_result=prepared_stage.deepseek_invocation_result,
            accepted_deepseek_review=None,
            deepseek_adjudication=None,
            claude_route_result=None,
            claude_token_preflight=None,
            claude_invocation_result=None,
            accepted_claude_review=None,
            usage_before=prepared_stage.usage_before,
            usage_after=prepared_stage.usage_before,
        )
    review = prepared_stage.accepted_deepseek_review
    adjudication = prepared_stage.deepseek_adjudication
    _require(type(review) is E5DeepSeekStructuredReviewV1)
    _require(
        type(adjudication) is E5DeepSeekTechnicalReviewAdjudicationV1
    )
    allowed_route = route.decision_code in _ALLOWED_ROUTE_CODES
    if allowed_route:
        _require(_valid_sha256(confirmed_usage_after_sha256))
        _require(
            confirmed_usage_after_sha256
            == prepared_stage.usage_after.usage_sha256
        )
        _require(
            type(claude_measured_input_tokens) is int
            and claude_measured_input_tokens >= 0
        )
        _require(
            type(claude_requested_output_tokens) is int
            and claude_requested_output_tokens >= 0
        )
        measured = claude_measured_input_tokens
        requested = claude_requested_output_tokens
    else:
        _require(confirmed_usage_after_sha256 is None)
        _require(claude_measured_input_tokens is None)
        _require(claude_requested_output_tokens is None)
        measured = 0
        requested = 0
    claude_preflight = preflight_e5_claude_review_v1(
        route_result=route,
        measured_input_tokens=measured,
        requested_output_tokens=requested,
    )
    claude_execution = execute_e5_claude_review_once_v1(
        payload=prepared_stage.payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route,
        token_preflight=claude_preflight,
        transport=claude_transport,
    )
    return _build_composition(
        payload=prepared_stage.payload,
        deepseek_token_preflight=prepared_stage.deepseek_token_preflight,
        deepseek_invocation_result=prepared_stage.deepseek_invocation_result,
        accepted_deepseek_review=review,
        deepseek_adjudication=adjudication,
        claude_route_result=route,
        claude_token_preflight=claude_preflight,
        claude_invocation_result=claude_execution.invocation_result,
        accepted_claude_review=claude_execution.accepted_claude_review,
        usage_before=prepared_stage.usage_before,
        usage_after=prepared_stage.usage_after,
    )


def resume_e5_bounded_final_review_v1(
    *,
    prepared_stage: E5BoundedFinalReviewPreparedStageV1,
    confirmed_usage_after_sha256: str | None,
    claude_measured_input_tokens: int | None,
    claude_requested_output_tokens: int | None,
    claude_transport: Callable[
        [E5ProviderRequestV1], E5ProviderAttemptObservationV1
    ],
) -> E5BoundedFinalReviewCompositionV1:
    try:
        _require(type(prepared_stage) is E5BoundedFinalReviewPreparedStageV1)
        reconstructed = reconstruct_e5_bounded_final_review_prepared_stage_v1(
            prepared_stage.to_mapping()
        )
        _require(reconstructed == prepared_stage)
        _require(callable(claude_transport))
        counts_none = (
            claude_measured_input_tokens is None
            and claude_requested_output_tokens is None
        )
        counts_ints = (
            type(claude_measured_input_tokens) is int
            and claude_measured_input_tokens >= 0
            and type(claude_requested_output_tokens) is int
            and claude_requested_output_tokens >= 0
        )
        _require(counts_none or counts_ints)
        return _resume_e5_bounded_final_review_core_v1(
            prepared_stage=reconstructed,
            confirmed_usage_after_sha256=confirmed_usage_after_sha256,
            claude_measured_input_tokens=claude_measured_input_tokens,
            claude_requested_output_tokens=claude_requested_output_tokens,
            claude_transport=claude_transport,
        )
    except Exception:
        _fail()


def compose_e5_bounded_final_review_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deterministic_hard_gates_passed: bool,
    pre_review_score: int,
    mode_score_floor: int,
    daily_usage: E5ClaudeDailyUsageV1,
    deepseek_measured_input_tokens: int,
    deepseek_requested_output_tokens: int,
    deepseek_transport: Callable[
        [E5ProviderRequestV1], E5ProviderAttemptObservationV1
    ],
    claude_measured_input_tokens: int | None,
    claude_requested_output_tokens: int | None,
    claude_transport: Callable[
        [E5ProviderRequestV1], E5ProviderAttemptObservationV1
    ],
) -> E5BoundedFinalReviewCompositionV1:
    try:
        verified_payload, usage_before = _validate_prepare_inputs(
            payload=payload,
            deterministic_hard_gates_passed=deterministic_hard_gates_passed,
            pre_review_score=pre_review_score,
            mode_score_floor=mode_score_floor,
            daily_usage=daily_usage,
            deepseek_measured_input_tokens=deepseek_measured_input_tokens,
            deepseek_requested_output_tokens=deepseek_requested_output_tokens,
            deepseek_transport=deepseek_transport,
        )
        claude_counts_are_none = (
            claude_measured_input_tokens is None
            and claude_requested_output_tokens is None
        )
        claude_counts_are_ints = (
            type(claude_measured_input_tokens) is int
            and claude_measured_input_tokens >= 0
            and type(claude_requested_output_tokens) is int
            and claude_requested_output_tokens >= 0
        )
        _require(claude_counts_are_none or claude_counts_are_ints)
        _require(callable(claude_transport))

        prepared_stage = _prepare_e5_bounded_final_review_core_v1(
            payload=verified_payload,
            deterministic_hard_gates_passed=deterministic_hard_gates_passed,
            pre_review_score=pre_review_score,
            mode_score_floor=mode_score_floor,
            daily_usage=usage_before,
            deepseek_measured_input_tokens=deepseek_measured_input_tokens,
            deepseek_requested_output_tokens=deepseek_requested_output_tokens,
            deepseek_transport=deepseek_transport,
        )
        allowed_route = (
            prepared_stage.claude_route_result is not None
            and prepared_stage.claude_route_result.decision_code
            in _ALLOWED_ROUTE_CODES
        )
        confirmed = (
            prepared_stage.usage_after.usage_sha256
            if allowed_route
            else None
        )
        return _resume_e5_bounded_final_review_core_v1(
            prepared_stage=prepared_stage,
            confirmed_usage_after_sha256=confirmed,
            claude_measured_input_tokens=claude_measured_input_tokens,
            claude_requested_output_tokens=claude_requested_output_tokens,
            claude_transport=claude_transport,
        )
    except Exception:
        _fail()


__all__ = (
    "E5_BOUNDED_FINAL_REVIEW_COMPOSITION_VERSION",
    "E5_BOUNDED_FINAL_REVIEW_PREPARED_STAGE_VERSION",
    "PRE_CLAUDE_BLOCK_DEEPSEEK_TOKEN_PREFLIGHT",
    "PRE_CLAUDE_BLOCK_DEEPSEEK_INVOCATION",
    "PRE_CLAUDE_BLOCK_D6_DETERMINISTIC_POLICY",
    "PRE_CLAUDE_BLOCK_D7_CLAUDE_ROUTING",
    "PRE_CLAUDE_L0_NO_CLAUDE",
    "PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED",
    "PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED",
    "E5_PRE_CLAUDE_OUTCOME_CODES",
    "PRE_CLAUDE_OUTCOME_CODE_COUNT",
    "PREPARED_STAGE_FIELD_COUNT",
    "CONTINUE_CLEAR_L0_TO_PYTHON_FINAL_GATE",
    "CONTINUE_CAUTION_L1_ACCEPTED_TO_PYTHON_FINAL_GATE",
    "BLOCK_DEEPSEEK_TOKEN_PREFLIGHT",
    "BLOCK_DEEPSEEK_INVOCATION",
    "BLOCK_D6_DETERMINISTIC_POLICY",
    "BLOCK_D7_CLAUDE_ROUTING",
    "BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT",
    "BLOCK_D8_CLAUDE_INVOCATION",
    "BLOCK_DEEPSEEK_HOLD_L2_EVIDENCE_COMPLETE",
    "E5_BOUNDED_FINAL_REVIEW_OUTCOME_CODES",
    "FINAL_OUTCOME_CODE_COUNT",
    "COMPOSITION_FIELD_COUNT",
    "E5BoundedFinalReviewPreparedStageV1",
    "E5BoundedFinalReviewCompositionV1",
    "reconstruct_e5_bounded_final_review_prepared_stage_v1",
    "prepare_e5_bounded_final_review_v1",
    "resume_e5_bounded_final_review_v1",
    "compose_e5_bounded_final_review_v1",
)
