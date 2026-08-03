"""Passive typed inputs for one bounded E6 production dispatch cycle."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Final

from engine.mode_profile_v1 import get_mode_profile
from engine.outcome_tracker_v4 import validate_outcome_invocation_id


E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1: Final = (
    "ai-crypto-signal-agent.e6-no-trade-cycle-request.v1"
)
E6_NO_TRADE_CYCLE_POLICY_V1: Final = "e6-healthy-no-trade-policy-v1"
E6_PRODUCTION_DISPATCH_DECISION_SCHEMA_V1: Final = (
    "ai-crypto-signal-agent.e6-production-dispatch-decision.v1"
)
E6_PRODUCTION_DISPATCH_POLICY_V1: Final = "e6-production-dispatch-policy-v1"

NO_MODE_JOB_DUE: Final = "NO_MODE_JOB_DUE"
DUE_WINDOW_ALREADY_HANDLED: Final = "DUE_WINDOW_ALREADY_HANDLED"
MODE_JOB_SELECTED: Final = "MODE_JOB_SELECTED"
E6_PRODUCTION_DISPATCH_DISPOSITIONS_V1: Final = frozenset(
    {NO_MODE_JOB_DUE, DUE_WINDOW_ALREADY_HANDLED, MODE_JOB_SELECTED}
)

E6_NO_TRADE_REASON_CODES_V1: Final = frozenset(
    {
        "EMPTY_ELIGIBLE_MARKET",
        "E2_ALL_INPUTS_UNAVAILABLE",
        "E2_NO_ELIGIBLE_CANDIDATE",
        "E2_CONTROLLED_TOP10_EMPTY",
        "E2_FINAL_TOP5_EMPTY",
        "E3_GEOMETRY_UNAVAILABLE",
        "E3_STRUCTURAL_DESTINATIONS_INCOMPLETE",
        "E3_EXECUTABLE_QUOTE_INCOMPLETE_OR_STALE",
        "E3_TRIGGER_NOT_CONFIRMED",
        "E3_ACTIONABLE_REJECTED",
        "NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE",
        "E4_DUPLICATE_SUPPRESSED",
        "E5_TECHNICAL_REVIEW_REJECTED",
        "PUBLICATION_INELIGIBLE",
    }
)

_SHA1_PATTERN: Final = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}\Z")
_UTC_PATTERN: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_SAFE_IDENTITY_PATTERN: Final = re.compile(r"[A-Z0-9][A-Z0-9._:+-]{0,159}\Z")
_DUE_WINDOW_OCCURRENCE_ID_PATTERN: Final = re.compile(
    r"e6dw1:[0-9a-f]{64}\Z"
)
_SECRET_MARKERS: Final = (
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
_ERROR_CODE: Final = "INVALID_E6_PRODUCTION_CYCLE_INPUT"


class E6ProductionCycleInputValidationErrorV1(ValueError):
    """Fixed-code rejection for malformed non-secret production inputs."""

    def __init__(self) -> None:
        self.code = _ERROR_CODE
        super().__init__(_ERROR_CODE)


def _invalid() -> None:
    raise E6ProductionCycleInputValidationErrorV1() from None


def _require(condition: bool) -> None:
    if not condition:
        _invalid()


def _source_commit(value: object) -> str:
    _require(type(value) is str and _SHA1_PATTERN.fullmatch(value) is not None)
    return value


def _sha256_hex(value: object) -> str:
    _require(type(value) is str and _SHA256_PATTERN.fullmatch(value) is not None)
    return value


def _utc_timestamp(value: object) -> str:
    _require(type(value) is str and _UTC_PATTERN.fullmatch(value) is not None)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        _invalid()
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return value


def _mode(value: object) -> str:
    try:
        profile = get_mode_profile(value)
    except Exception:
        _invalid()
    _require(profile.mode == value)
    return value


def _safe_identity(value: object) -> str:
    _require(
        type(value) is str
        and value == value.strip()
        and _SAFE_IDENTITY_PATTERN.fullmatch(value) is not None
        and not any(marker in value.casefold() for marker in _SECRET_MARKERS)
    )
    return value


def _due_window_occurrence_id(value: object) -> str:
    _require(
        type(value) is str
        and _DUE_WINDOW_OCCURRENCE_ID_PATTERN.fullmatch(value) is not None
    )
    return value


def _zero(value: object) -> int:
    _require(type(value) is int and value == 0)
    return value


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        _invalid()


def _canonical_sha256(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class E6NoTradeCycleRequestV1:
    """A healthy, mode-bound scan result with no publishable candidate."""

    schema_version: str
    policy_version: str
    source_commit: str
    outcome_invocation_id: str
    mode: str
    due_job_id: str
    due_window_occurrence_id: str
    mode_lineage_sha256: str
    observed_at: str
    reason_code: str
    source_reason_code: str
    scan_composition_sha256: str
    execution_sha256: str
    e3_evidence_sha256: str
    audit_manifest_sha256: str
    provider_attempt_count: int
    telegram_attempt_count: int
    exchange_order_count: int
    slot_mutation_count: int
    pair_lock_mutation_count: int
    entry_active_mutation_count: int
    retry_count: int

    def __post_init__(self) -> None:
        try:
            _require(self.schema_version == E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1)
            _require(self.policy_version == E6_NO_TRADE_CYCLE_POLICY_V1)
            _source_commit(self.source_commit)
            validate_outcome_invocation_id(self.outcome_invocation_id)
            _mode(self.mode)
            _safe_identity(self.due_job_id)
            _due_window_occurrence_id(self.due_window_occurrence_id)
            _sha256_hex(self.mode_lineage_sha256)
            _utc_timestamp(self.observed_at)
            _require(
                type(self.reason_code) is str
                and self.reason_code in E6_NO_TRADE_REASON_CODES_V1
            )
            _safe_identity(self.source_reason_code)
            for value in (
                self.scan_composition_sha256,
                self.execution_sha256,
                self.e3_evidence_sha256,
                self.audit_manifest_sha256,
            ):
                _sha256_hex(value)
            for count in (
                self.provider_attempt_count,
                self.telegram_attempt_count,
                self.exchange_order_count,
                self.slot_mutation_count,
                self.pair_lock_mutation_count,
                self.entry_active_mutation_count,
                self.retry_count,
            ):
                _zero(count)
        except E6ProductionCycleInputValidationErrorV1:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    def canonical_payload(self) -> str:
        """Return canonical JSON containing every authoritative field."""

        return _canonical_json(self.to_mapping())

    def canonical_payload_sha256(self) -> str:
        """Bind every authoritative field to one deterministic digest."""

        return sha256(self.canonical_payload().encode("utf-8")).hexdigest()


def _dispatch_preimage(
    decision: "E6ProductionDispatchDecisionV1",
) -> dict[str, object]:
    return {
        field.name: getattr(decision, field.name)
        for field in fields(E6ProductionDispatchDecisionV1)
        if field.name != "dispatch_evidence_sha256"
    }


@dataclass(frozen=True, slots=True)
class E6ProductionDispatchDecisionV1:
    """Pure-data result of selecting at most one due production mode job."""

    schema_version: str
    policy_version: str
    source_commit: str
    outcome_invocation_id: str
    observed_at: str
    disposition: str
    reason_code: str
    mode: str | None
    due_job_id: str | None
    due_window_occurrence_id: str | None
    mode_lineage_sha256: str | None
    dispatch_evidence_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(
                self.schema_version
                == E6_PRODUCTION_DISPATCH_DECISION_SCHEMA_V1
            )
            _require(self.policy_version == E6_PRODUCTION_DISPATCH_POLICY_V1)
            _source_commit(self.source_commit)
            validate_outcome_invocation_id(self.outcome_invocation_id)
            _utc_timestamp(self.observed_at)
            _require(
                type(self.disposition) is str
                and self.disposition in E6_PRODUCTION_DISPATCH_DISPOSITIONS_V1
                and self.reason_code == self.disposition
            )
            if self.disposition == NO_MODE_JOB_DUE:
                _require(
                    self.mode is None
                    and self.due_job_id is None
                    and self.due_window_occurrence_id is None
                    and self.mode_lineage_sha256 is None
                )
            else:
                _mode(self.mode)
                _safe_identity(self.due_job_id)
                _due_window_occurrence_id(self.due_window_occurrence_id)
                _sha256_hex(self.mode_lineage_sha256)
            _sha256_hex(self.dispatch_evidence_sha256)
            _require(
                self.dispatch_evidence_sha256
                == _canonical_sha256(_dispatch_preimage(self))
            )
        except E6ProductionCycleInputValidationErrorV1:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    def canonical_payload(self) -> str:
        """Return canonical JSON containing every authoritative field."""

        return _canonical_json(self.to_mapping())

    def canonical_payload_sha256(self) -> str:
        """Bind every authoritative field, including its evidence digest."""

        return sha256(self.canonical_payload().encode("utf-8")).hexdigest()


def build_e6_production_dispatch_decision_v1(
    *,
    source_commit: str,
    outcome_invocation_id: str,
    observed_at: str,
    disposition: str,
    reason_code: str,
    mode: str | None = None,
    due_job_id: str | None = None,
    due_window_occurrence_id: str | None = None,
    mode_lineage_sha256: str | None = None,
) -> E6ProductionDispatchDecisionV1:
    """Build one validated decision and derive its evidence digest."""

    provisional = E6ProductionDispatchDecisionV1.__new__(
        E6ProductionDispatchDecisionV1
    )
    values = {
        "schema_version": E6_PRODUCTION_DISPATCH_DECISION_SCHEMA_V1,
        "policy_version": E6_PRODUCTION_DISPATCH_POLICY_V1,
        "source_commit": source_commit,
        "outcome_invocation_id": outcome_invocation_id,
        "observed_at": observed_at,
        "disposition": disposition,
        "reason_code": reason_code,
        "mode": mode,
        "due_job_id": due_job_id,
        "due_window_occurrence_id": due_window_occurrence_id,
        "mode_lineage_sha256": mode_lineage_sha256,
    }
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    object.__setattr__(provisional, "dispatch_evidence_sha256", "0" * 64)
    return E6ProductionDispatchDecisionV1(
        **values,
        dispatch_evidence_sha256=_canonical_sha256(_dispatch_preimage(provisional)),
    )


__all__ = (
    "DUE_WINDOW_ALREADY_HANDLED",
    "E6_NO_TRADE_CYCLE_POLICY_V1",
    "E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1",
    "E6_NO_TRADE_REASON_CODES_V1",
    "E6_PRODUCTION_DISPATCH_DECISION_SCHEMA_V1",
    "E6_PRODUCTION_DISPATCH_DISPOSITIONS_V1",
    "E6_PRODUCTION_DISPATCH_POLICY_V1",
    "E6NoTradeCycleRequestV1",
    "E6ProductionCycleInputValidationErrorV1",
    "E6ProductionDispatchDecisionV1",
    "MODE_JOB_SELECTED",
    "NO_MODE_JOB_DUE",
    "build_e6_production_dispatch_decision_v1",
)
