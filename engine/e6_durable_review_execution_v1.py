"""Durably reserve Claude usage before resuming bounded E5 execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Callable, Final, Mapping

from engine.e5_bounded_final_review_composition_v1 import (
    PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED,
    PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED,
    E5BoundedFinalReviewCompositionV1,
    E5BoundedFinalReviewPreparedStageV1,
    prepare_e5_bounded_final_review_v1,
    resume_e5_bounded_final_review_v1,
)
from engine.e5_claude_review_router_v1 import E5ClaudeDailyUsageV1
from engine.e5_provider_invocation_boundary_v1 import (
    ACTIVE_PROVIDER_BINDING_SHA256,
    E5ProviderAttemptObservationV1,
    E5ProviderRequestV1,
)
from engine.e5_technical_review_payload_v1 import E5TechnicalReviewPayloadV1
from engine.e6_claude_daily_usage_store_v1 import (
    E6ClaudeDailyUsageStorePortV1,
    E6ClaudeDailyUsageStoreRecordV1,
    resolve_e6_claude_daily_usage_before_v1,
)


E6_DURABLE_REVIEW_EXECUTION_VERSION: Final = (
    "e6-durable-review-execution-v1"
)
NO_DURABLE_RESERVATION_REQUIRED: Final = (
    "NO_DURABLE_RESERVATION_REQUIRED"
)
DURABLE_RESERVATION_COMMITTED: Final = "DURABLE_RESERVATION_COMMITTED"
E6_DURABLE_REVIEW_PERSISTENCE_OUTCOMES: Final = (
    NO_DURABLE_RESERVATION_REQUIRED,
    DURABLE_RESERVATION_COMMITTED,
)
DURABLE_EXECUTION_FIELD_COUNT: Final = 20

_ERROR: Final = "invalid E6 durable review execution"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_UTC_TIMESTAMP_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_RESERVATION_CODES: Final = frozenset(
    (
        PRE_CLAUDE_L1_DURABLE_RESERVATION_REQUIRED,
        PRE_CLAUDE_L2_DURABLE_RESERVATION_REQUIRED,
    )
)


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


def _validate_timestamp(value: object) -> str:
    _require(type(value) is str)
    _require(_UTC_TIMESTAMP_PATTERN.fullmatch(value) is not None)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        _fail()
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return value


def _payload_day(payload: E5TechnicalReviewPayloadV1) -> str:
    trigger_age = payload.to_mapping()["trigger_age"]
    _require(type(trigger_age) is dict)
    timestamp = trigger_age.get("evaluation_timestamp")
    return _validate_timestamp(timestamp)[:10]


def _execution_preimage(
    result: "E6DurableReviewExecutionResultV1",
) -> dict[str, object]:
    return {
        "execution_version": result.execution_version,
        "provider_binding_sha256": result.provider_binding_sha256,
        "payload_sha256": result.payload_sha256,
        "prepared_stage_sha256": result.prepared_stage_sha256,
        "usage_before": result.usage_before.to_mapping(),
        "proposed_usage_after": result.proposed_usage_after.to_mapping(),
        "committed_usage_after": (
            None
            if result.committed_usage_after is None
            else result.committed_usage_after.to_mapping()
        ),
        "store_record_sha256": result.store_record_sha256,
        "store_generation": result.store_generation,
        "persistence_outcome": result.persistence_outcome,
        "final_composition": result.final_composition.to_mapping(),
        "deepseek_provider_attempt_count": (
            result.deepseek_provider_attempt_count
        ),
        "claude_provider_attempt_count": result.claude_provider_attempt_count,
        "retry_count": result.retry_count,
        "publication_allowed": result.publication_allowed,
        "telegram_send_allowed": result.telegram_send_allowed,
        "ledger_mutation_allowed": result.ledger_mutation_allowed,
        "slot_mutation_allowed": result.slot_mutation_allowed,
        "pair_lock_mutation_allowed": result.pair_lock_mutation_allowed,
    }


@dataclass(frozen=True, slots=True)
class E6DurableReviewExecutionResultV1:
    execution_version: str
    provider_binding_sha256: str
    payload_sha256: str
    prepared_stage_sha256: str
    usage_before: E5ClaudeDailyUsageV1
    proposed_usage_after: E5ClaudeDailyUsageV1
    committed_usage_after: E5ClaudeDailyUsageV1 | None
    store_record_sha256: str | None
    store_generation: int | None
    persistence_outcome: str
    final_composition: E5BoundedFinalReviewCompositionV1
    deepseek_provider_attempt_count: int
    claude_provider_attempt_count: int
    retry_count: int
    publication_allowed: bool
    telegram_send_allowed: bool
    ledger_mutation_allowed: bool
    slot_mutation_allowed: bool
    pair_lock_mutation_allowed: bool
    execution_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                self.execution_version == E6_DURABLE_REVIEW_EXECUTION_VERSION
            )
            _require(
                self.provider_binding_sha256
                == ACTIVE_PROVIDER_BINDING_SHA256
            )
            _require(_valid_sha256(self.payload_sha256))
            _require(_valid_sha256(self.prepared_stage_sha256))
            _require(type(self.usage_before) is E5ClaudeDailyUsageV1)
            _require(type(self.proposed_usage_after) is E5ClaudeDailyUsageV1)
            self.usage_before.__post_init__()
            self.proposed_usage_after.__post_init__()
            _require(
                self.usage_before.utc_day == self.proposed_usage_after.utc_day
            )
            _require(
                type(self.final_composition)
                is E5BoundedFinalReviewCompositionV1
            )
            self.final_composition.__post_init__()
            _require(
                self.final_composition.payload_sha256 == self.payload_sha256
            )
            _require(self.final_composition.usage_before == self.usage_before)
            _require(
                self.final_composition.usage_after
                == self.proposed_usage_after
            )
            _require(
                self.persistence_outcome
                in E6_DURABLE_REVIEW_PERSISTENCE_OUTCOMES
            )
            if self.persistence_outcome == NO_DURABLE_RESERVATION_REQUIRED:
                _require(self.committed_usage_after is None)
                _require(self.store_record_sha256 is None)
                _require(self.store_generation is None)
                _require(self.proposed_usage_after == self.usage_before)
            else:
                _require(
                    type(self.committed_usage_after) is E5ClaudeDailyUsageV1
                )
                self.committed_usage_after.__post_init__()
                _require(
                    self.committed_usage_after == self.proposed_usage_after
                )
                _require(_valid_sha256(self.store_record_sha256))
                _require(
                    type(self.store_generation) is int
                    and self.store_generation > 0
                )
                _require(self.proposed_usage_after != self.usage_before)
            for count in (
                self.deepseek_provider_attempt_count,
                self.claude_provider_attempt_count,
                self.retry_count,
            ):
                _require(type(count) is int)
            _require(self.deepseek_provider_attempt_count in (0, 1))
            _require(self.claude_provider_attempt_count in (0, 1))
            _require(self.retry_count == 0)
            _require(
                self.deepseek_provider_attempt_count
                == self.final_composition.deepseek_provider_attempt_count
            )
            _require(
                self.claude_provider_attempt_count
                == self.final_composition.claude_provider_attempt_count
            )
            for authority in (
                self.publication_allowed,
                self.telegram_send_allowed,
                self.ledger_mutation_allowed,
                self.slot_mutation_allowed,
                self.pair_lock_mutation_allowed,
            ):
                _require(type(authority) is bool and authority is False)
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


def _build_execution_result(
    *,
    prepared_stage: E5BoundedFinalReviewPreparedStageV1,
    committed_record: E6ClaudeDailyUsageStoreRecordV1 | None,
    persistence_outcome: str,
    final_composition: E5BoundedFinalReviewCompositionV1,
) -> E6DurableReviewExecutionResultV1:
    temporary = object.__new__(E6DurableReviewExecutionResultV1)
    data: dict[str, object] = {
        "execution_version": E6_DURABLE_REVIEW_EXECUTION_VERSION,
        "provider_binding_sha256": ACTIVE_PROVIDER_BINDING_SHA256,
        "payload_sha256": prepared_stage.payload_sha256,
        "prepared_stage_sha256": prepared_stage.prepared_stage_sha256,
        "usage_before": prepared_stage.usage_before,
        "proposed_usage_after": prepared_stage.usage_after,
        "committed_usage_after": (
            None if committed_record is None else committed_record.usage
        ),
        "store_record_sha256": (
            None if committed_record is None else committed_record.record_sha256
        ),
        "store_generation": (
            None if committed_record is None else committed_record.store_generation
        ),
        "persistence_outcome": persistence_outcome,
        "final_composition": final_composition,
        "deepseek_provider_attempt_count": (
            final_composition.deepseek_provider_attempt_count
        ),
        "claude_provider_attempt_count": (
            final_composition.claude_provider_attempt_count
        ),
        "retry_count": 0,
        "publication_allowed": False,
        "telegram_send_allowed": False,
        "ledger_mutation_allowed": False,
        "slot_mutation_allowed": False,
        "pair_lock_mutation_allowed": False,
    }
    for name, value in data.items():
        object.__setattr__(temporary, name, value)
    return E6DurableReviewExecutionResultV1(
        **data,
        execution_sha256=_hash_mapping(_execution_preimage(temporary)),
    )


def execute_e6_durable_review_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    deterministic_hard_gates_passed: bool,
    pre_review_score: int,
    mode_score_floor: int,
    usage_store: E6ClaudeDailyUsageStorePortV1,
    commit_timestamp: str,
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
) -> E6DurableReviewExecutionResultV1:
    try:
        _require(type(payload) is E5TechnicalReviewPayloadV1)
        payload.__post_init__()
        _require(payload.provider_binding_sha256 == ACTIVE_PROVIDER_BINDING_SHA256)
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
        _require(isinstance(usage_store, E6ClaudeDailyUsageStorePortV1))
        _require(callable(usage_store.load))
        _require(callable(usage_store.compare_and_commit))
        _require(callable(deepseek_transport))
        _require(callable(claude_transport))
        timestamp = _validate_timestamp(commit_timestamp)
        utc_day = _payload_day(payload)
        _require(timestamp[:10] == utc_day)

        current = usage_store.load(utc_day=utc_day, observed_at=timestamp)
        _require(
            current is None
            or type(current) is E6ClaudeDailyUsageStoreRecordV1
        )
        if current is not None:
            current.__post_init__()
            _require(current.utc_day == utc_day)
        usage_before = resolve_e6_claude_daily_usage_before_v1(
            record=current,
            utc_day=utc_day,
        )
        prepared = prepare_e5_bounded_final_review_v1(
            payload=payload,
            deterministic_hard_gates_passed=deterministic_hard_gates_passed,
            pre_review_score=pre_review_score,
            mode_score_floor=mode_score_floor,
            daily_usage=usage_before,
            deepseek_measured_input_tokens=deepseek_measured_input_tokens,
            deepseek_requested_output_tokens=deepseek_requested_output_tokens,
            deepseek_transport=deepseek_transport,
        )

        committed_record = None
        if prepared.pre_claude_outcome_code in _RESERVATION_CODES:
            committed_record = usage_store.compare_and_commit(
                utc_day=utc_day,
                expected_store_generation=(
                    0 if current is None else current.store_generation
                ),
                expected_record_sha256=(
                    None if current is None else current.record_sha256
                ),
                expected_usage_sha256=usage_before.usage_sha256,
                proposed_usage_after=prepared.usage_after,
                committed_at=timestamp,
            )
            _require(
                type(committed_record) is E6ClaudeDailyUsageStoreRecordV1
            )
            committed_record.__post_init__()
            _require(committed_record.utc_day == utc_day)
            _require(committed_record.usage == prepared.usage_after)
            _require(
                committed_record.usage_sha256
                == prepared.usage_after.usage_sha256
            )
            _require(
                committed_record.prior_usage_sha256
                == usage_before.usage_sha256
            )
            _require(
                committed_record.store_generation
                == (1 if current is None else current.store_generation + 1)
            )
            confirmed_sha = committed_record.usage_sha256
            persistence_outcome = DURABLE_RESERVATION_COMMITTED
        else:
            _require(prepared.usage_after == prepared.usage_before)
            confirmed_sha = None
            persistence_outcome = NO_DURABLE_RESERVATION_REQUIRED

        final_composition = resume_e5_bounded_final_review_v1(
            prepared_stage=prepared,
            confirmed_usage_after_sha256=confirmed_sha,
            claude_measured_input_tokens=claude_measured_input_tokens,
            claude_requested_output_tokens=claude_requested_output_tokens,
            claude_transport=claude_transport,
        )
        return _build_execution_result(
            prepared_stage=prepared,
            committed_record=committed_record,
            persistence_outcome=persistence_outcome,
            final_composition=final_composition,
        )
    except Exception:
        _fail()


__all__ = (
    "E6_DURABLE_REVIEW_EXECUTION_VERSION",
    "NO_DURABLE_RESERVATION_REQUIRED",
    "DURABLE_RESERVATION_COMMITTED",
    "E6_DURABLE_REVIEW_PERSISTENCE_OUTCOMES",
    "DURABLE_EXECUTION_FIELD_COUNT",
    "E6DurableReviewExecutionResultV1",
    "execute_e6_durable_review_v1",
)
