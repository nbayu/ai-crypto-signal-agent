"""Sanitized Phase 09R exit-code 7 observability."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import re
import sys
from typing import Final

from engine.e6_production_cycle_input_v1 import (
    DUE_WINDOW_ALREADY_HANDLED,
    E6_NO_TRADE_REASON_CODES_V1,
    NO_MODE_JOB_DUE,
)
from engine.mode_profile_v1 import get_mode_profile
from engine.outcome_tracker_v4 import validate_outcome_invocation_id


EVENT: Final = "PHASE09R_EXIT7"
SCHEMA_VERSION: Final = 1
EXIT_CODE: Final = 7

BOUNDARY_NO: Final = "NO"
BOUNDARY_YES: Final = "YES"
BOUNDARY_UNKNOWN: Final = "UNKNOWN"
_BOUNDARY_VALUES: Final = frozenset(
    {BOUNDARY_NO, BOUNDARY_YES, BOUNDARY_UNKNOWN}
)

MASTER_ENGINE_SETUP_CONSTRUCTION_FAILED: Final = (
    "MASTER_ENGINE_SETUP_CONSTRUCTION_FAILED"
)
MASTER_ENGINE_SOURCE_ENVELOPE_FAILED: Final = (
    "MASTER_ENGINE_SOURCE_ENVELOPE_FAILED"
)
PRODUCTION_SIGNAL_SERVICE_FAILED: Final = "PRODUCTION_SIGNAL_SERVICE_FAILED"
SERVICE_INVOCATION_INVALID: Final = "SERVICE_INVOCATION_INVALID"
SOURCE_CONTRACT_REJECTED: Final = "SOURCE_CONTRACT_REJECTED"
PUBLICATION_IDENTITY_BUILD_FAILED: Final = (
    "PUBLICATION_IDENTITY_BUILD_FAILED"
)
PUBLICATION_INTENT_PERSIST_FAILED: Final = (
    "PUBLICATION_INTENT_PERSIST_FAILED"
)
DELIVERY_COMPLETION_BUILD_FAILED: Final = (
    "DELIVERY_COMPLETION_BUILD_FAILED"
)
PUBLICATION_COMPLETION_PERSIST_FAILED: Final = (
    "PUBLICATION_COMPLETION_PERSIST_FAILED"
)
PUBLICATION_READBACK_FAILED: Final = "PUBLICATION_READBACK_FAILED"
PRODUCTION_SIGNAL_OUT_MISSING: Final = "PRODUCTION_SIGNAL_OUT_MISSING"
PRODUCTION_SIGNAL_OUT_MALFORMED: Final = "PRODUCTION_SIGNAL_OUT_MALFORMED"
UNKNOWN_PRODUCTION_SIGNAL_OUTCOME: Final = (
    "UNKNOWN_PRODUCTION_SIGNAL_OUTCOME"
)
MASTER_ENGINE_UNCLASSIFIED: Final = "MASTER_ENGINE_UNCLASSIFIED"


class ProductionSignalServiceError(RuntimeError):
    """Base fail-closed error preserved for service API compatibility."""


class Phase09RExit7Failure(ProductionSignalServiceError):
    """Carry only sanitized exit-7 classification fields."""

    __slots__ = (
        "failure_stage",
        "failure_code",
        "exception_class",
        "telegram_boundary_reached",
    )

    def __init__(
        self,
        *,
        failure_stage: str,
        failure_code: str,
        exception_class: str,
        telegram_boundary_reached: str,
    ) -> None:
        super().__init__()
        if telegram_boundary_reached not in _BOUNDARY_VALUES:
            raise ValueError("invalid Telegram-boundary classification")
        self.failure_stage = failure_stage
        self.failure_code = failure_code
        self.exception_class = exception_class
        self.telegram_boundary_reached = telegram_boundary_reached


def classified_failure(
    *,
    failure_stage: str,
    failure_code: str,
    exc: BaseException,
    telegram_boundary_reached: str,
) -> Phase09RExit7Failure:
    """Build a sanitized classification without rendering an exception."""

    return Phase09RExit7Failure(
        failure_stage=failure_stage,
        failure_code=failure_code,
        exception_class=type(exc).__name__,
        telegram_boundary_reached=telegram_boundary_reached,
    )


def emit_exit7_event(failure: Phase09RExit7Failure) -> None:
    """Emit exactly one deterministic compact JSON event to stderr."""

    event = {
        "event": EVENT,
        "schema_version": SCHEMA_VERSION,
        "exit_code": EXIT_CODE,
        "failure_code": failure.failure_code,
        "failure_stage": failure.failure_stage,
        "exception_class": failure.exception_class,
        "telegram_boundary_reached": failure.telegram_boundary_reached,
    }
    sys.stderr.write(
        json.dumps(event, separators=(",", ":"), ensure_ascii=True) + "\n"
    )


E6_PRODUCTION_OBSERVABILITY_SCHEMA_V1: Final = (
    "ai-crypto-signal-agent.e6-production-observability-event.v1"
)
E6_PRODUCTION_CONFIGURATION_BLOCKED_V1: Final = (
    "E6_PRODUCTION_CONFIGURATION_BLOCKED_V1"
)
E6_PRODUCTION_NO_WORK_DUE_V1: Final = "E6_PRODUCTION_NO_WORK_DUE_V1"
E6_PRODUCTION_NO_TRADE_V1: Final = "E6_PRODUCTION_NO_TRADE_V1"
E6_PRODUCTION_IDEMPOTENT_REPLAY_V1: Final = (
    "E6_PRODUCTION_IDEMPOTENT_REPLAY_V1"
)

E6_PRODUCTION_STAGE_CONFIGURATION_V1: Final = "CONFIGURATION"
E6_PRODUCTION_STAGE_DISPATCH_V1: Final = "DISPATCH"
E6_PRODUCTION_STAGE_PRODUCTION_INPUT_V1: Final = "PRODUCTION_INPUT"

E6_PRODUCTION_CONFIGURATION_REASON_CODES_V1: Final = frozenset(
    {
        "ACTIVATION_CONFIGURATION_DISABLED",
        "ACTIVATION_CONFIGURATION_INVALID",
        "ACTIVATION_CONFIGURATION_PARTIAL",
    }
)
_E6_PRODUCTION_EVENT_NAMES_V1: Final = frozenset(
    {
        E6_PRODUCTION_CONFIGURATION_BLOCKED_V1,
        E6_PRODUCTION_NO_WORK_DUE_V1,
        E6_PRODUCTION_NO_TRADE_V1,
        E6_PRODUCTION_IDEMPOTENT_REPLAY_V1,
    }
)
_E6_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}\Z")
_E6_UTC_PATTERN: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z"
)
_E6_SAFE_REASON_PATTERN: Final = re.compile(
    r"[A-Z0-9][A-Z0-9._:+-]{0,159}\Z"
)
_E6_DUE_WINDOW_OCCURRENCE_ID_PATTERN: Final = re.compile(
    r"e6dw1:[0-9a-f]{64}\Z"
)
_E6_SECRET_MARKERS: Final = (
    "api_key",
    "authorization",
    "bearer",
    "bot_token",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)
_E6_OBSERVABILITY_ERROR: Final = "INVALID_E6_PRODUCTION_OBSERVABILITY_EVENT"


class E6ProductionObservabilityValidationErrorV1(ValueError):
    """Fixed-code rejection that cannot render supplied event values."""

    def __init__(self) -> None:
        self.code = _E6_OBSERVABILITY_ERROR
        super().__init__(_E6_OBSERVABILITY_ERROR)


def _invalid_e6_observability_event() -> None:
    raise E6ProductionObservabilityValidationErrorV1() from None


def _require_e6_observability(condition: bool) -> None:
    if not condition:
        _invalid_e6_observability_event()


def _valid_e6_observed_at(value: object) -> None:
    _require_e6_observability(
        type(value) is str and _E6_UTC_PATTERN.fullmatch(value) is not None
    )
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        _invalid_e6_observability_event()
    _require_e6_observability(
        parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value
    )


def _valid_e6_mode(value: object) -> None:
    try:
        profile = get_mode_profile(value)
    except Exception:
        _invalid_e6_observability_event()
    _require_e6_observability(profile.mode == value)


def _valid_e6_safe_reason(value: object) -> None:
    _require_e6_observability(
        type(value) is str
        and value == value.strip()
        and _E6_SAFE_REASON_PATTERN.fullmatch(value) is not None
        and not any(marker in value.casefold() for marker in _E6_SECRET_MARKERS)
    )


def _valid_e6_due_window_occurrence_id(value: object) -> None:
    _require_e6_observability(
        type(value) is str
        and _E6_DUE_WINDOW_OCCURRENCE_ID_PATTERN.fullmatch(value) is not None
    )


@dataclass(frozen=True, slots=True)
class E6ProductionObservabilityEventV1:
    """One compact, typed, secret-safe production lifecycle event."""

    schema_version: str
    event_name: str
    outcome_invocation_id: str
    observed_at: str
    mode: str | None
    due_window_occurrence_id: str | None
    stage: str
    reason_code: str
    source_reason_code: str | None
    evidence_sha256: str
    provider_attempt_count: int
    telegram_attempt_count: int
    retry_count: int

    def __post_init__(self) -> None:
        try:
            _require_e6_observability(
                self.schema_version == E6_PRODUCTION_OBSERVABILITY_SCHEMA_V1
            )
            _require_e6_observability(
                type(self.event_name) is str
                and self.event_name in _E6_PRODUCTION_EVENT_NAMES_V1
            )
            validate_outcome_invocation_id(self.outcome_invocation_id)
            _valid_e6_observed_at(self.observed_at)
            _require_e6_observability(
                type(self.evidence_sha256) is str
                and _E6_SHA256_PATTERN.fullmatch(self.evidence_sha256)
                is not None
            )
            for count in (
                self.provider_attempt_count,
                self.telegram_attempt_count,
                self.retry_count,
            ):
                _require_e6_observability(type(count) is int and count == 0)

            if self.event_name == E6_PRODUCTION_CONFIGURATION_BLOCKED_V1:
                _require_e6_observability(
                    self.stage == E6_PRODUCTION_STAGE_CONFIGURATION_V1
                    and self.reason_code
                    in E6_PRODUCTION_CONFIGURATION_REASON_CODES_V1
                    and self.mode is None
                    and self.due_window_occurrence_id is None
                    and self.source_reason_code is None
                )
            elif self.event_name == E6_PRODUCTION_NO_WORK_DUE_V1:
                _require_e6_observability(
                    self.stage == E6_PRODUCTION_STAGE_DISPATCH_V1
                    and self.reason_code == NO_MODE_JOB_DUE
                    and self.mode is None
                    and self.due_window_occurrence_id is None
                    and self.source_reason_code is None
                )
            elif self.event_name == E6_PRODUCTION_IDEMPOTENT_REPLAY_V1:
                _require_e6_observability(
                    self.stage == E6_PRODUCTION_STAGE_DISPATCH_V1
                    and self.reason_code == DUE_WINDOW_ALREADY_HANDLED
                    and self.mode is not None
                    and self.due_window_occurrence_id is not None
                    and self.source_reason_code is None
                )
                _valid_e6_mode(self.mode)
                _valid_e6_due_window_occurrence_id(
                    self.due_window_occurrence_id
                )
            else:
                _require_e6_observability(
                    self.event_name == E6_PRODUCTION_NO_TRADE_V1
                    and self.stage == E6_PRODUCTION_STAGE_PRODUCTION_INPUT_V1
                    and self.reason_code in E6_NO_TRADE_REASON_CODES_V1
                    and self.mode is not None
                    and self.due_window_occurrence_id is not None
                    and self.source_reason_code is not None
                )
                _valid_e6_mode(self.mode)
                _valid_e6_due_window_occurrence_id(
                    self.due_window_occurrence_id
                )
                _valid_e6_safe_reason(self.source_reason_code)
        except E6ProductionObservabilityValidationErrorV1:
            raise
        except Exception:
            _invalid_e6_observability_event()

    def to_mapping(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )


def emit_e6_production_observability_event_v1(
    event: E6ProductionObservabilityEventV1,
) -> None:
    """Emit exactly one canonical record using the event's fixed route policy."""

    if type(event) is not E6ProductionObservabilityEventV1:
        _invalid_e6_observability_event()
    event.__post_init__()
    stream = (
        sys.stderr
        if event.event_name == E6_PRODUCTION_CONFIGURATION_BLOCKED_V1
        else sys.stdout
    )
    stream.write(event.canonical_json() + "\n")
