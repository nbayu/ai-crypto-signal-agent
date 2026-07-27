"""Sanitized Phase 09R exit-code 7 observability."""

from __future__ import annotations

import json
import sys
from typing import Final


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


class Phase09RExit7Failure(RuntimeError):
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
