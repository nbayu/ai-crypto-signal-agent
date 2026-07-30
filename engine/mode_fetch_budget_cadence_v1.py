"""Pure E2 fetch-budget, cache-identity, and cadence contracts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Final

from engine.mode_data_plan_v1 import (
    ModeDataPlanV1,
    build_mode_data_plan,
)
from engine.mode_profile_v1 import (
    ModeProfileV1,
    all_mode_profiles,
    get_mode_profile,
)


MODE_FETCH_CADENCE_POLICY_VERSION: Final = (
    "mode-fetch-cadence-policy-v1"
)
DISCOVERY_POLICY_SCHEMA_VERSION: Final = "discovery-policy-v1"
MODE_TIMEFRAME_FETCH_SCHEMA_VERSION: Final = "mode-timeframe-fetch-v1"
MODE_FETCH_BUDGET_SCHEMA_VERSION: Final = "mode-fetch-budget-v1"
ARMED_MONITOR_BUDGET_SCHEMA_VERSION: Final = "armed-monitor-budget-v1"
MODE_CACHE_KEY_SCHEMA_VERSION: Final = "mode-cache-key-v1"
MODE_CADENCE_JOB_SCHEMA_VERSION: Final = "mode-cadence-job-v1"
CADENCE_DUE_JOB_SCHEMA_VERSION: Final = "cadence-due-job-v1"
CADENCE_DUE_WINDOW_SCHEMA_VERSION: Final = "cadence-due-window-v1"
DAILY_CADENCE_PLAN_SCHEMA_VERSION: Final = "daily-cadence-plan-v1"
CADENCE_START_DECISION_SCHEMA_VERSION: Final = "cadence-start-decision-v1"

DISCOVERY_UNIVERSE_MAX_SYMBOLS: Final = 500
MODE_FULL_EVALUATION_MAX_SYMBOLS: Final = 100
ARMED_MONITOR_MAX_SYMBOLS_PER_MODE: Final = 5
MAX_JOB_START_DELAY_SECONDS: Final = 60

DISCOVERY_MARKET_TYPE: Final = "ACTIVE_USDT_LINEAR_PERPETUAL"
DISCOVERY_TRUNCATION_ORDER: Final = (
    "QUOTE_VOLUME_24H_DESC_THEN_CANONICAL_SYMBOL_ASC"
)
LIVE_PRICE_BOUNDARY: Final = "SEPARATE_FRESH_PRICE_ADMISSION_V1"
ARMED_HIGHER_CONTEXT_SOURCE: Final = (
    "CURRENT_MODE_OWNED_CLOSED_CANDLE_CACHE"
)
ARMED_STALE_ACTION: Final = "FAIL_CLOSED_SKIP_DUE_WINDOW"
SKIPPED_START_DELAY_REASON: Final = (
    "SKIPPED_GLOBAL_NONOVERLAP_START_DELAY"
)
ADMITTED_REASON: Final = "ADMITTED"
BASE_JOB_KIND: Final = "BASE_EVALUATION"
ARMED_JOB_KIND: Final = "ARMED_MONITOR"

MARKET_LEVEL_REQUEST_COUNT: Final = 2
MARKET_LEVEL_IP_WEIGHT: Final = 41
PER_SYMBOL_OI_HISTORY_REQUEST_COUNT: Final = 1
PER_SYMBOL_OI_HISTORY_IP_WEIGHT: Final = 0
SECONDS_PER_UTC_DAY: Final = 24 * 60 * 60

_PURPOSE_FETCH_POLICY: Final = {
    "CONTEXT": (50, 51, 1),
    "OPTIONAL_CONTEXT": (50, 51, 1),
    "BIAS": (50, 51, 1),
    "STRUCTURE": (300, 301, 2),
    "TRIGGER": (300, 301, 2),
}
_TIMEFRAME_SECONDS: Final = {
    "1w": 7 * 24 * 60 * 60,
    "1d": 24 * 60 * 60,
    "4h": 4 * 60 * 60,
    "1h": 60 * 60,
    "15m": 15 * 60,
    "5m": 5 * 60,
    "3m": 3 * 60,
}
_CANONICAL_SYMBOL: Final = re.compile(
    r"[A-Z0-9]+/[A-Z0-9]+(?::[A-Z0-9]+)?"
)
_SAFE_TEXT: Final = re.compile(r"[A-Za-z0-9._:+-]{1,128}")
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")


class ModeFetchCadenceValidationError(ValueError):
    """Sanitized validation failure for this pure contract boundary."""


def _invalid() -> None:
    raise ModeFetchCadenceValidationError(
        "invalid mode fetch cadence contract"
    ) from None


def _constant(value: object, expected: str) -> str:
    if type(value) is not str or value != expected:
        _invalid()
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        _invalid()
    return value


def _integer(
    value: object,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if type(value) is not int:
        _invalid()
    if minimum is not None and value < minimum:
        _invalid()
    if maximum is not None and value > maximum:
        _invalid()
    return value


def _text(value: object) -> str:
    if type(value) is not str or not value or value != value.strip():
        _invalid()
    return value


def _safe_text(value: object) -> str:
    value = _text(value)
    if _SAFE_TEXT.fullmatch(value) is None:
        _invalid()
    return value


def _canonical_symbol(value: object) -> str:
    value = _text(value)
    if _CANONICAL_SYMBOL.fullmatch(value) is None:
        _invalid()
    return value


def _sha256(value: object) -> str:
    if type(value) is not str or _SHA256_HEX.fullmatch(value) is None:
        _invalid()
    return value


def _profile(mode: object) -> ModeProfileV1:
    try:
        return get_mode_profile(mode)
    except Exception:
        _invalid()


def _plan(mode: object) -> ModeDataPlanV1:
    try:
        plan = build_mode_data_plan(mode)
    except Exception:
        _invalid()
    if type(plan) is not ModeDataPlanV1:
        _invalid()
    return plan


def _timeframe_seconds(timeframe: object) -> int:
    timeframe = _text(timeframe)
    try:
        return _TIMEFRAME_SECONDS[timeframe]
    except KeyError:
        _invalid()


def _closed_candle_close_at(
    value: object,
    timeframe: object,
) -> str:
    text = _text(value)
    timeframe_value = _text(timeframe)
    timeframe_seconds = _timeframe_seconds(timeframe_value)
    try:
        parsed = datetime.strptime(
            text,
            "%Y-%m-%dT%H:%M:%SZ",
        ).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        _invalid()
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        _invalid()
    epoch = datetime(
        1970,
        1,
        5 if timeframe_value == "1w" else 1,
        tzinfo=timezone.utc,
    )
    elapsed_seconds = int((parsed - epoch).total_seconds())
    if elapsed_seconds % timeframe_seconds != 0:
        _invalid()
    return text


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except Exception:
        _invalid()


def _hash_mapping(value: dict[str, object]) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _tuple_of_strings(value: object) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        _invalid()
    result = tuple(value)
    if any(type(item) is not str for item in result):
        _invalid()
    return result


def _fetch_specs(
    *,
    mode: object,
    include_optional_context: object,
) -> tuple[dict[str, object], ...]:
    profile = _profile(mode)
    plan = _plan(profile.mode)
    include_optional = _boolean(include_optional_context)
    if include_optional and not profile.optional_context_timeframes:
        _invalid()
    grouped: dict[str, dict[str, object]] = {}
    order: list[str] = []

    for requirement in plan.timeframe_requirements:
        if type(requirement.required) is not bool:
            _invalid()
        if not requirement.required and not include_optional:
            continue
        try:
            closed_count, raw_limit, weight = _PURPOSE_FETCH_POLICY[
                requirement.purpose
            ]
        except KeyError:
            _invalid()
        if requirement.timeframe not in grouped:
            grouped[requirement.timeframe] = {
                "timeframe": requirement.timeframe,
                "purposes": [],
                "required": requirement.required,
                "closed_candle_only": requirement.closed_candle_only,
                "closed_candle_count": closed_count,
                "raw_fetch_limit": raw_limit,
                "request_count": 1,
                "ip_weight": weight,
            }
            order.append(requirement.timeframe)
        current = grouped[requirement.timeframe]
        current["purposes"].append(requirement.purpose)
        current["required"] = bool(
            current["required"] or requirement.required
        )
        current["closed_candle_only"] = bool(
            current["closed_candle_only"]
            and requirement.closed_candle_only
        )
        current["closed_candle_count"] = max(
            int(current["closed_candle_count"]),
            closed_count,
        )
        current["raw_fetch_limit"] = max(
            int(current["raw_fetch_limit"]),
            raw_limit,
        )
        current["ip_weight"] = max(
            int(current["ip_weight"]),
            weight,
        )

    result = []
    for timeframe in order:
        item = dict(grouped[timeframe])
        item["purposes"] = tuple(item["purposes"])
        result.append(item)
    return tuple(result)


def _job_due_map(
    job: ModeCadenceJobV1,
) -> dict[int, tuple[str, ...]]:
    updates: dict[int, list[str]] = defaultdict(list)
    for timeframe in job.source_timeframes:
        cadence = _timeframe_seconds(timeframe)
        for close_second in range(0, SECONDS_PER_UTC_DAY, cadence):
            due_second = close_second + job.offset_seconds
            if due_second < SECONDS_PER_UTC_DAY:
                updates[due_second].append(timeframe)
    return {
        second: tuple(
            timeframe
            for timeframe in job.source_timeframes
            if timeframe in due_timeframes
        )
        for second, due_timeframes in sorted(updates.items())
    }


def _job_priority(job: ModeCadenceJobV1) -> tuple[int, int, str]:
    return (
        0 if job.armed_conditional else 1,
        job.mode_priority_seconds,
        job.job_id,
    )


@dataclass(frozen=True, slots=True)
class DiscoveryUniversePolicyV1:
    schema_version: str
    policy_version: str
    max_symbols: int
    market_type: str
    truncation_order: str
    truncation_must_be_audited: bool
    unbounded_universe_prohibited: bool

    def __post_init__(self) -> None:
        try:
            _constant(self.schema_version, DISCOVERY_POLICY_SCHEMA_VERSION)
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            if _integer(self.max_symbols) != DISCOVERY_UNIVERSE_MAX_SYMBOLS:
                _invalid()
            _constant(self.market_type, DISCOVERY_MARKET_TYPE)
            _constant(self.truncation_order, DISCOVERY_TRUNCATION_ORDER)
            if not _boolean(self.truncation_must_be_audited):
                _invalid()
            if not _boolean(self.unbounded_universe_prohibited):
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "max_symbols": self.max_symbols,
            "market_type": self.market_type,
            "truncation_order": self.truncation_order,
            "truncation_must_be_audited": self.truncation_must_be_audited,
            "unbounded_universe_prohibited": self.unbounded_universe_prohibited,
        }


@dataclass(frozen=True, slots=True)
class ModeTimeframeFetchV1:
    schema_version: str
    policy_version: str
    mode: str
    timeframe: str
    purposes: tuple[str, ...]
    required: bool
    closed_candle_only: bool
    closed_candle_count: int
    raw_fetch_limit: int
    request_count: int
    ip_weight: int

    def __post_init__(self) -> None:
        try:
            _constant(
                self.schema_version,
                MODE_TIMEFRAME_FETCH_SCHEMA_VERSION,
            )
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            profile = _profile(self.mode)
            plan = _plan(profile.mode)
            _timeframe_seconds(self.timeframe)
            purposes = _tuple_of_strings(self.purposes)
            object.__setattr__(self, "purposes", purposes)
            if not purposes or len(set(purposes)) != len(purposes):
                _invalid()
            matching = tuple(
                requirement
                for requirement in plan.timeframe_requirements
                if requirement.timeframe == self.timeframe
                and requirement.purpose in purposes
            )
            if tuple(item.purpose for item in matching) != purposes:
                _invalid()
            expected_required = any(item.required for item in matching)
            expected_closed_only = all(
                item.closed_candle_only for item in matching
            )
            policies = tuple(
                _PURPOSE_FETCH_POLICY[item.purpose]
                for item in matching
            )
            if not policies:
                _invalid()
            expected_closed_count = max(item[0] for item in policies)
            expected_raw_limit = max(item[1] for item in policies)
            expected_weight = max(item[2] for item in policies)
            if _boolean(self.required) != expected_required:
                _invalid()
            if _boolean(self.closed_candle_only) != expected_closed_only:
                _invalid()
            if not self.closed_candle_only:
                _invalid()
            if _integer(self.closed_candle_count) != expected_closed_count:
                _invalid()
            if _integer(self.raw_fetch_limit) != expected_raw_limit:
                _invalid()
            if self.raw_fetch_limit != self.closed_candle_count + 1:
                _invalid()
            if _integer(self.request_count) != 1:
                _invalid()
            if _integer(self.ip_weight) != expected_weight:
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "timeframe": self.timeframe,
            "purposes": list(self.purposes),
            "required": self.required,
            "closed_candle_only": self.closed_candle_only,
            "closed_candle_count": self.closed_candle_count,
            "raw_fetch_limit": self.raw_fetch_limit,
            "request_count": self.request_count,
            "ip_weight": self.ip_weight,
        }


@dataclass(frozen=True, slots=True)
class ModeFetchBudgetV1:
    schema_version: str
    policy_version: str
    mode: str
    mode_data_plan_version: str
    include_optional_context: bool
    symbol_count: int
    discovery_universe_max_symbols: int
    full_evaluation_max_symbols: int
    market_level_request_count: int
    market_level_ip_weight: int
    per_symbol_ohlcv_request_count: int
    per_symbol_oi_history_request_count: int
    per_symbol_request_count: int
    per_symbol_ip_weight: int
    total_request_count: int
    total_ip_weight: int
    oi_history_request_count: int
    timeframe_fetches: tuple[ModeTimeframeFetchV1, ...]

    def __post_init__(self) -> None:
        try:
            _constant(self.schema_version, MODE_FETCH_BUDGET_SCHEMA_VERSION)
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            profile = _profile(self.mode)
            plan = _plan(profile.mode)
            _constant(self.mode_data_plan_version, plan.policy_version)
            include_optional = _boolean(self.include_optional_context)
            symbol_count = _integer(
                self.symbol_count,
                minimum=1,
                maximum=MODE_FULL_EVALUATION_MAX_SYMBOLS,
            )
            if (
                _integer(self.discovery_universe_max_symbols)
                != DISCOVERY_UNIVERSE_MAX_SYMBOLS
            ):
                _invalid()
            if (
                _integer(self.full_evaluation_max_symbols)
                != MODE_FULL_EVALUATION_MAX_SYMBOLS
            ):
                _invalid()
            if _integer(self.market_level_request_count) != 2:
                _invalid()
            if _integer(self.market_level_ip_weight) != 41:
                _invalid()
            if type(self.timeframe_fetches) not in (tuple, list):
                _invalid()
            fetches = tuple(self.timeframe_fetches)
            object.__setattr__(self, "timeframe_fetches", fetches)
            expected_specs = _fetch_specs(
                mode=profile.mode,
                include_optional_context=include_optional,
            )
            if len(fetches) != len(expected_specs):
                _invalid()
            for fetch, spec in zip(fetches, expected_specs, strict=True):
                if type(fetch) is not ModeTimeframeFetchV1:
                    _invalid()
                if fetch.mode != profile.mode:
                    _invalid()
                comparable = {
                    key: getattr(fetch, key)
                    for key in (
                        "timeframe",
                        "purposes",
                        "required",
                        "closed_candle_only",
                        "closed_candle_count",
                        "raw_fetch_limit",
                        "request_count",
                        "ip_weight",
                    )
                }
                if _canonical_json(comparable) != _canonical_json(spec):
                    _invalid()
            ohlcv_requests = len(fetches)
            per_symbol_requests = (
                ohlcv_requests + PER_SYMBOL_OI_HISTORY_REQUEST_COUNT
            )
            per_symbol_weight = sum(item.ip_weight for item in fetches)
            if _integer(self.per_symbol_ohlcv_request_count) != ohlcv_requests:
                _invalid()
            if (
                _integer(self.per_symbol_oi_history_request_count)
                != PER_SYMBOL_OI_HISTORY_REQUEST_COUNT
            ):
                _invalid()
            if _integer(self.per_symbol_request_count) != per_symbol_requests:
                _invalid()
            if _integer(self.per_symbol_ip_weight) != per_symbol_weight:
                _invalid()
            if (
                _integer(self.total_request_count)
                != MARKET_LEVEL_REQUEST_COUNT
                + per_symbol_requests * symbol_count
            ):
                _invalid()
            if (
                _integer(self.total_ip_weight)
                != MARKET_LEVEL_IP_WEIGHT
                + per_symbol_weight * symbol_count
            ):
                _invalid()
            if _integer(self.oi_history_request_count) != symbol_count:
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "mode_data_plan_version": self.mode_data_plan_version,
            "include_optional_context": self.include_optional_context,
            "symbol_count": self.symbol_count,
            "discovery_universe_max_symbols": self.discovery_universe_max_symbols,
            "full_evaluation_max_symbols": self.full_evaluation_max_symbols,
            "market_level_request_count": self.market_level_request_count,
            "market_level_ip_weight": self.market_level_ip_weight,
            "per_symbol_ohlcv_request_count": self.per_symbol_ohlcv_request_count,
            "per_symbol_oi_history_request_count": self.per_symbol_oi_history_request_count,
            "per_symbol_request_count": self.per_symbol_request_count,
            "per_symbol_ip_weight": self.per_symbol_ip_weight,
            "total_request_count": self.total_request_count,
            "total_ip_weight": self.total_ip_weight,
            "oi_history_request_count": self.oi_history_request_count,
            "timeframe_fetches": [
                item.to_mapping() for item in self.timeframe_fetches
            ],
        }


@dataclass(frozen=True, slots=True)
class ArmedMonitorBudgetV1:
    schema_version: str
    policy_version: str
    mode: str
    mode_data_plan_version: str
    symbol_count: int
    max_symbols: int
    trigger_timeframe: str
    closed_candle_count: int
    raw_fetch_limit: int
    request_count: int
    ip_weight: int
    higher_context_source: str
    cache_missing_or_stale_action: str
    full_universe_fallback_allowed: bool
    full_mode_rescan_fallback_allowed: bool
    retry_count: int

    def __post_init__(self) -> None:
        try:
            _constant(
                self.schema_version,
                ARMED_MONITOR_BUDGET_SCHEMA_VERSION,
            )
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            profile = _profile(self.mode)
            plan = _plan(profile.mode)
            _constant(self.mode_data_plan_version, plan.policy_version)
            symbol_count = _integer(
                self.symbol_count,
                minimum=1,
                maximum=ARMED_MONITOR_MAX_SYMBOLS_PER_MODE,
            )
            if _integer(self.max_symbols) != ARMED_MONITOR_MAX_SYMBOLS_PER_MODE:
                _invalid()
            _constant(self.trigger_timeframe, profile.trigger_timeframe)
            trigger_policy = _PURPOSE_FETCH_POLICY["TRIGGER"]
            if _integer(self.closed_candle_count) != trigger_policy[0]:
                _invalid()
            if _integer(self.raw_fetch_limit) != trigger_policy[1]:
                _invalid()
            if self.raw_fetch_limit != self.closed_candle_count + 1:
                _invalid()
            if _integer(self.request_count) != symbol_count:
                _invalid()
            if _integer(self.ip_weight) != trigger_policy[2] * symbol_count:
                _invalid()
            _constant(self.higher_context_source, ARMED_HIGHER_CONTEXT_SOURCE)
            _constant(self.cache_missing_or_stale_action, ARMED_STALE_ACTION)
            if _boolean(self.full_universe_fallback_allowed):
                _invalid()
            if _boolean(self.full_mode_rescan_fallback_allowed):
                _invalid()
            if _integer(self.retry_count) != 0:
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__slots__
        }


@dataclass(frozen=True, slots=True)
class ModeOwnedCacheKeyV1:
    schema_version: str
    policy_version: str
    mode: str
    canonical_symbol: str
    timeframe: str
    closed_candle_close_at: str
    mode_data_plan_version: str
    cache_key_sha256: str

    def __post_init__(self) -> None:
        try:
            _constant(self.schema_version, MODE_CACHE_KEY_SCHEMA_VERSION)
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            profile = _profile(self.mode)
            plan = _plan(profile.mode)
            _canonical_symbol(self.canonical_symbol)
            _constant(self.mode_data_plan_version, plan.policy_version)
            timeframe = _text(self.timeframe)
            close_at = _closed_candle_close_at(
                self.closed_candle_close_at,
                timeframe,
            )
            allowed_timeframes = {
                item.timeframe for item in plan.timeframe_requirements
            }
            if timeframe not in allowed_timeframes:
                _invalid()
            expected = _hash_mapping(
                {
                    "mode": profile.mode,
                    "canonical_symbol": self.canonical_symbol,
                    "timeframe": timeframe,
                    "closed_candle_close_at": close_at,
                    "mode_data_plan_version": plan.policy_version,
                }
            )
            if _sha256(self.cache_key_sha256) != expected:
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__slots__
        }


@dataclass(frozen=True, slots=True)
class ModeCadenceJobV1:
    schema_version: str
    policy_version: str
    job_id: str
    mode: str
    job_kind: str
    armed_conditional: bool
    source_timeframes: tuple[str, ...]
    offset_seconds: int
    due_windows_per_utc_day: int
    mode_priority_seconds: int
    one_mode_job_per_due_window: bool
    global_nonoverlap_required: bool
    missed_run_catchup_allowed: bool
    immediate_retry_allowed: bool
    manual_forced_scan_allowed: bool
    publication_from_shadow_allowed: bool

    def __post_init__(self) -> None:
        try:
            _constant(self.schema_version, MODE_CADENCE_JOB_SCHEMA_VERSION)
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            profile = _profile(self.mode)
            job_kind = _text(self.job_kind)
            if job_kind not in (BASE_JOB_KIND, ARMED_JOB_KIND):
                _invalid()
            expected_id = f"{profile.mode}:{job_kind}"
            _constant(self.job_id, expected_id)
            if job_kind == BASE_JOB_KIND:
                expected_armed = False
                expected_timeframes = profile.structure_evaluation_timeframes
                expected_offset = profile.structure_evaluation_offset_seconds
            else:
                expected_armed = True
                expected_timeframes = (profile.armed_monitor_timeframe,)
                expected_offset = profile.armed_monitor_offset_seconds
            if _boolean(self.armed_conditional) != expected_armed:
                _invalid()
            source_timeframes = _tuple_of_strings(
                self.source_timeframes
            )
            object.__setattr__(
                self,
                "source_timeframes",
                source_timeframes,
            )
            if source_timeframes != expected_timeframes:
                _invalid()
            if _integer(self.offset_seconds, minimum=1) != expected_offset:
                _invalid()
            for timeframe in self.source_timeframes:
                _timeframe_seconds(timeframe)
            expected_count = len(_job_due_map_unvalidated(
                self.source_timeframes,
                self.offset_seconds,
            ))
            if _integer(self.due_windows_per_utc_day) != expected_count:
                _invalid()
            expected_priority = _timeframe_seconds(profile.trigger_timeframe)
            if _integer(self.mode_priority_seconds) != expected_priority:
                _invalid()
            invariants = (
                (self.one_mode_job_per_due_window, True),
                (self.global_nonoverlap_required, True),
                (self.missed_run_catchup_allowed, False),
                (self.immediate_retry_allowed, False),
                (self.manual_forced_scan_allowed, False),
                (self.publication_from_shadow_allowed, False),
            )
            for actual, expected in invariants:
                if _boolean(actual) is not expected:
                    _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "job_id": self.job_id,
            "mode": self.mode,
            "job_kind": self.job_kind,
            "armed_conditional": self.armed_conditional,
            "source_timeframes": list(self.source_timeframes),
            "offset_seconds": self.offset_seconds,
            "due_windows_per_utc_day": self.due_windows_per_utc_day,
            "mode_priority_seconds": self.mode_priority_seconds,
            "one_mode_job_per_due_window": self.one_mode_job_per_due_window,
            "global_nonoverlap_required": self.global_nonoverlap_required,
            "missed_run_catchup_allowed": self.missed_run_catchup_allowed,
            "immediate_retry_allowed": self.immediate_retry_allowed,
            "manual_forced_scan_allowed": self.manual_forced_scan_allowed,
            "publication_from_shadow_allowed": self.publication_from_shadow_allowed,
        }


def _job_due_map_unvalidated(
    source_timeframes: tuple[str, ...],
    offset_seconds: int,
) -> dict[int, tuple[str, ...]]:
    updates: dict[int, list[str]] = defaultdict(list)
    for timeframe in source_timeframes:
        cadence = _timeframe_seconds(timeframe)
        for close_second in range(0, SECONDS_PER_UTC_DAY, cadence):
            due_second = close_second + offset_seconds
            if due_second < SECONDS_PER_UTC_DAY:
                updates[due_second].append(timeframe)
    return {
        second: tuple(
            timeframe
            for timeframe in source_timeframes
            if timeframe in due_timeframes
        )
        for second, due_timeframes in sorted(updates.items())
    }


@dataclass(frozen=True, slots=True)
class CadenceDueJobV1:
    schema_version: str
    policy_version: str
    job_id: str
    mode: str
    job_kind: str
    due_timeframes: tuple[str, ...]
    armed_conditional: bool

    def __post_init__(self) -> None:
        try:
            _constant(self.schema_version, CADENCE_DUE_JOB_SCHEMA_VERSION)
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            job = _cadence_job(self.mode, self.job_kind)
            _constant(self.job_id, job.job_id)
            due_timeframes = _tuple_of_strings(self.due_timeframes)
            object.__setattr__(
                self,
                "due_timeframes",
                due_timeframes,
            )
            if not due_timeframes:
                _invalid()
            if len(set(due_timeframes)) != len(due_timeframes):
                _invalid()
            canonical_subset = tuple(
                timeframe
                for timeframe in job.source_timeframes
                if timeframe in due_timeframes
            )
            if due_timeframes != canonical_subset:
                _invalid()
            if _boolean(self.armed_conditional) != job.armed_conditional:
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "job_id": self.job_id,
            "mode": self.mode,
            "job_kind": self.job_kind,
            "due_timeframes": list(self.due_timeframes),
            "armed_conditional": self.armed_conditional,
        }


@dataclass(frozen=True, slots=True)
class CadenceDueWindowV1:
    schema_version: str
    policy_version: str
    due_second_utc: int
    ordered_jobs: tuple[CadenceDueJobV1, ...]
    collision_count: int
    global_nonoverlap_required: bool

    def __post_init__(self) -> None:
        try:
            _constant(self.schema_version, CADENCE_DUE_WINDOW_SCHEMA_VERSION)
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            _integer(
                self.due_second_utc,
                minimum=0,
                maximum=SECONDS_PER_UTC_DAY - 1,
            )
            if type(self.ordered_jobs) not in (tuple, list):
                _invalid()
            jobs = tuple(self.ordered_jobs)
            object.__setattr__(self, "ordered_jobs", jobs)
            if not jobs or any(type(item) is not CadenceDueJobV1 for item in jobs):
                _invalid()
            if len({item.job_id for item in jobs}) != len(jobs):
                _invalid()
            canonical_jobs = tuple(
                sorted(
                    jobs,
                    key=lambda item: _job_priority(
                        _cadence_job(item.mode, item.job_kind)
                    ),
                )
            )
            if jobs != canonical_jobs:
                _invalid()
            for due_job in jobs:
                canonical_job = _cadence_job(
                    due_job.mode,
                    due_job.job_kind,
                )
                due_map = _job_due_map(canonical_job)
                if self.due_second_utc not in due_map:
                    _invalid()
                if (
                    due_job.due_timeframes
                    != due_map[self.due_second_utc]
                ):
                    _invalid()
            if _integer(self.collision_count) != max(0, len(jobs) - 1):
                _invalid()
            if not _boolean(self.global_nonoverlap_required):
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "due_second_utc": self.due_second_utc,
            "ordered_jobs": [item.to_mapping() for item in self.ordered_jobs],
            "collision_count": self.collision_count,
            "global_nonoverlap_required": self.global_nonoverlap_required,
        }


@dataclass(frozen=True, slots=True)
class DailyCadencePlanV1:
    schema_version: str
    policy_version: str
    armed_modes: tuple[str, ...]
    logical_mode_job_count: int
    unique_due_timestamp_count: int
    collision_timestamp_count: int
    windows: tuple[CadenceDueWindowV1, ...]

    def __post_init__(self) -> None:
        try:
            _constant(self.schema_version, DAILY_CADENCE_PLAN_SCHEMA_VERSION)
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            armed_modes = _canonical_modes(self.armed_modes)
            object.__setattr__(self, "armed_modes", armed_modes)
            if type(self.windows) not in (tuple, list):
                _invalid()
            windows = tuple(self.windows)
            object.__setattr__(self, "windows", windows)
            if any(type(item) is not CadenceDueWindowV1 for item in windows):
                _invalid()
            due_seconds = tuple(
                item.due_second_utc for item in windows
            )
            if due_seconds != tuple(sorted(due_seconds)):
                _invalid()
            if len(set(due_seconds)) != len(due_seconds):
                _invalid()
            actual_signature = tuple(
                (
                    window.due_second_utc,
                    tuple(
                        (job.job_id, job.due_timeframes)
                        for job in window.ordered_jobs
                    ),
                )
                for window in windows
            )
            if actual_signature != _daily_window_signature(armed_modes):
                _invalid()
            logical_count = sum(len(item.ordered_jobs) for item in windows)
            collision_count = sum(
                len(item.ordered_jobs) > 1 for item in windows
            )
            if _integer(self.logical_mode_job_count) != logical_count:
                _invalid()
            if _integer(self.unique_due_timestamp_count) != len(windows):
                _invalid()
            if _integer(self.collision_timestamp_count) != collision_count:
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "armed_modes": list(self.armed_modes),
            "logical_mode_job_count": self.logical_mode_job_count,
            "unique_due_timestamp_count": self.unique_due_timestamp_count,
            "collision_timestamp_count": self.collision_timestamp_count,
            "windows": [item.to_mapping() for item in self.windows],
        }


@dataclass(frozen=True, slots=True)
class CadenceStartDecisionV1:
    schema_version: str
    policy_version: str
    delay_seconds: int
    max_delay_seconds: int
    admitted: bool
    reason_code: str
    retry_count: int
    catchup_allowed: bool
    parallel_mode_job_allowed: bool

    def __post_init__(self) -> None:
        try:
            _constant(
                self.schema_version,
                CADENCE_START_DECISION_SCHEMA_VERSION,
            )
            _constant(self.policy_version, MODE_FETCH_CADENCE_POLICY_VERSION)
            delay = _integer(self.delay_seconds, minimum=0)
            if _integer(self.max_delay_seconds) != MAX_JOB_START_DELAY_SECONDS:
                _invalid()
            expected_admitted = delay <= MAX_JOB_START_DELAY_SECONDS
            if _boolean(self.admitted) != expected_admitted:
                _invalid()
            _constant(
                self.reason_code,
                ADMITTED_REASON
                if expected_admitted
                else SKIPPED_START_DELAY_REASON,
            )
            if _integer(self.retry_count) != 0:
                _invalid()
            if _boolean(self.catchup_allowed):
                _invalid()
            if _boolean(self.parallel_mode_job_allowed):
                _invalid()
        except ModeFetchCadenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__slots__
        }


def build_discovery_universe_policy() -> DiscoveryUniversePolicyV1:
    return DiscoveryUniversePolicyV1(
        schema_version=DISCOVERY_POLICY_SCHEMA_VERSION,
        policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
        max_symbols=DISCOVERY_UNIVERSE_MAX_SYMBOLS,
        market_type=DISCOVERY_MARKET_TYPE,
        truncation_order=DISCOVERY_TRUNCATION_ORDER,
        truncation_must_be_audited=True,
        unbounded_universe_prohibited=True,
    )


def build_mode_fetch_budget(
    *,
    mode: object,
    symbol_count: object,
    include_optional_context: object,
) -> ModeFetchBudgetV1:
    try:
        profile = _profile(mode)
        plan = _plan(profile.mode)
        include_optional = _boolean(include_optional_context)
        count = _integer(
            symbol_count,
            minimum=1,
            maximum=MODE_FULL_EVALUATION_MAX_SYMBOLS,
        )
        specs = _fetch_specs(
            mode=profile.mode,
            include_optional_context=include_optional,
        )
        fetches = tuple(
            ModeTimeframeFetchV1(
                schema_version=MODE_TIMEFRAME_FETCH_SCHEMA_VERSION,
                policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
                mode=profile.mode,
                timeframe=str(spec["timeframe"]),
                purposes=tuple(spec["purposes"]),
                required=bool(spec["required"]),
                closed_candle_only=bool(spec["closed_candle_only"]),
                closed_candle_count=int(spec["closed_candle_count"]),
                raw_fetch_limit=int(spec["raw_fetch_limit"]),
                request_count=int(spec["request_count"]),
                ip_weight=int(spec["ip_weight"]),
            )
            for spec in specs
        )
        per_symbol_requests = len(fetches) + 1
        per_symbol_weight = sum(item.ip_weight for item in fetches)
        return ModeFetchBudgetV1(
            schema_version=MODE_FETCH_BUDGET_SCHEMA_VERSION,
            policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
            mode=profile.mode,
            mode_data_plan_version=plan.policy_version,
            include_optional_context=include_optional,
            symbol_count=count,
            discovery_universe_max_symbols=DISCOVERY_UNIVERSE_MAX_SYMBOLS,
            full_evaluation_max_symbols=MODE_FULL_EVALUATION_MAX_SYMBOLS,
            market_level_request_count=MARKET_LEVEL_REQUEST_COUNT,
            market_level_ip_weight=MARKET_LEVEL_IP_WEIGHT,
            per_symbol_ohlcv_request_count=len(fetches),
            per_symbol_oi_history_request_count=1,
            per_symbol_request_count=per_symbol_requests,
            per_symbol_ip_weight=per_symbol_weight,
            total_request_count=2 + per_symbol_requests * count,
            total_ip_weight=41 + per_symbol_weight * count,
            oi_history_request_count=count,
            timeframe_fetches=fetches,
        )
    except ModeFetchCadenceValidationError:
        raise
    except Exception:
        _invalid()


def build_armed_monitor_budget(
    *,
    mode: object,
    symbol_count: object,
) -> ArmedMonitorBudgetV1:
    try:
        profile = _profile(mode)
        plan = _plan(profile.mode)
        count = _integer(
            symbol_count,
            minimum=1,
            maximum=ARMED_MONITOR_MAX_SYMBOLS_PER_MODE,
        )
        closed_count, raw_limit, weight = _PURPOSE_FETCH_POLICY["TRIGGER"]
        return ArmedMonitorBudgetV1(
            schema_version=ARMED_MONITOR_BUDGET_SCHEMA_VERSION,
            policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
            mode=profile.mode,
            mode_data_plan_version=plan.policy_version,
            symbol_count=count,
            max_symbols=ARMED_MONITOR_MAX_SYMBOLS_PER_MODE,
            trigger_timeframe=profile.trigger_timeframe,
            closed_candle_count=closed_count,
            raw_fetch_limit=raw_limit,
            request_count=count,
            ip_weight=weight * count,
            higher_context_source=ARMED_HIGHER_CONTEXT_SOURCE,
            cache_missing_or_stale_action=ARMED_STALE_ACTION,
            full_universe_fallback_allowed=False,
            full_mode_rescan_fallback_allowed=False,
            retry_count=0,
        )
    except ModeFetchCadenceValidationError:
        raise
    except Exception:
        _invalid()


def build_mode_owned_cache_key(
    *,
    mode: object,
    canonical_symbol: object,
    timeframe: object,
    closed_candle_close_at: object,
) -> ModeOwnedCacheKeyV1:
    try:
        profile = _profile(mode)
        plan = _plan(profile.mode)
        symbol = _canonical_symbol(canonical_symbol)
        timeframe_value = _text(timeframe)
        close_at = _closed_candle_close_at(
            closed_candle_close_at,
            timeframe_value,
        )
        allowed = {item.timeframe for item in plan.timeframe_requirements}
        if timeframe_value not in allowed:
            _invalid()
        mapping = {
            "mode": profile.mode,
            "canonical_symbol": symbol,
            "timeframe": timeframe_value,
            "closed_candle_close_at": close_at,
            "mode_data_plan_version": plan.policy_version,
        }
        return ModeOwnedCacheKeyV1(
            schema_version=MODE_CACHE_KEY_SCHEMA_VERSION,
            policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
            mode=profile.mode,
            canonical_symbol=symbol,
            timeframe=timeframe_value,
            closed_candle_close_at=close_at,
            mode_data_plan_version=plan.policy_version,
            cache_key_sha256=_hash_mapping(mapping),
        )
    except ModeFetchCadenceValidationError:
        raise
    except Exception:
        _invalid()


def _cadence_job(mode: object, job_kind: object) -> ModeCadenceJobV1:
    profile = _profile(mode)
    kind = _text(job_kind)
    if kind == BASE_JOB_KIND:
        armed = False
        timeframes = profile.structure_evaluation_timeframes
        offset = profile.structure_evaluation_offset_seconds
    elif kind == ARMED_JOB_KIND:
        armed = True
        timeframes = (profile.armed_monitor_timeframe,)
        offset = profile.armed_monitor_offset_seconds
    else:
        _invalid()
    due_count = len(_job_due_map_unvalidated(timeframes, offset))
    return ModeCadenceJobV1(
        schema_version=MODE_CADENCE_JOB_SCHEMA_VERSION,
        policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
        job_id=f"{profile.mode}:{kind}",
        mode=profile.mode,
        job_kind=kind,
        armed_conditional=armed,
        source_timeframes=timeframes,
        offset_seconds=offset,
        due_windows_per_utc_day=due_count,
        mode_priority_seconds=_timeframe_seconds(profile.trigger_timeframe),
        one_mode_job_per_due_window=True,
        global_nonoverlap_required=True,
        missed_run_catchup_allowed=False,
        immediate_retry_allowed=False,
        manual_forced_scan_allowed=False,
        publication_from_shadow_allowed=False,
    )


def all_mode_cadence_jobs() -> tuple[ModeCadenceJobV1, ...]:
    jobs = []
    for profile in all_mode_profiles():
        jobs.append(_cadence_job(profile.mode, BASE_JOB_KIND))
        jobs.append(_cadence_job(profile.mode, ARMED_JOB_KIND))
    return tuple(jobs)


def _canonical_modes(value: object) -> tuple[str, ...]:
    if type(value) not in (tuple, list, set, frozenset):
        _invalid()
    raw = tuple(value)
    if any(type(item) is not str for item in raw):
        _invalid()
    if len(set(raw)) != len(raw):
        _invalid()
    selected = set(raw)
    canonical = tuple(
        profile.mode
        for profile in all_mode_profiles()
        if profile.mode in selected
    )
    if len(canonical) != len(selected):
        _invalid()
    return canonical


def _daily_window_signature(
    armed_modes: tuple[str, ...],
) -> tuple[tuple[int, tuple[tuple[str, tuple[str, ...]], ...]], ...]:
    armed_set = set(armed_modes)
    selected_jobs = []
    for profile in all_mode_profiles():
        selected_jobs.append(_cadence_job(profile.mode, BASE_JOB_KIND))
        if profile.mode in armed_set:
            selected_jobs.append(
                _cadence_job(profile.mode, ARMED_JOB_KIND)
            )
    by_second: dict[
        int,
        list[tuple[ModeCadenceJobV1, tuple[str, ...]]],
    ] = defaultdict(list)
    for job in selected_jobs:
        for due_second, due_timeframes in _job_due_map(job).items():
            by_second[due_second].append((job, due_timeframes))
    return tuple(
        (
            due_second,
            tuple(
                (job.job_id, due_timeframes)
                for job, due_timeframes in sorted(
                    by_second[due_second],
                    key=lambda item: _job_priority(item[0]),
                )
            ),
        )
        for due_second in sorted(by_second)
    )


def build_daily_cadence_plan(
    *,
    armed_modes: object,
) -> DailyCadencePlanV1:
    try:
        canonical_armed_modes = _canonical_modes(armed_modes)
        armed_set = set(canonical_armed_modes)
        selected_jobs = []
        for profile in all_mode_profiles():
            selected_jobs.append(_cadence_job(profile.mode, BASE_JOB_KIND))
            if profile.mode in armed_set:
                selected_jobs.append(
                    _cadence_job(profile.mode, ARMED_JOB_KIND)
                )
        by_second: dict[int, list[tuple[ModeCadenceJobV1, tuple[str, ...]]]] = (
            defaultdict(list)
        )
        for job in selected_jobs:
            for due_second, due_timeframes in _job_due_map(job).items():
                by_second[due_second].append((job, due_timeframes))
        windows = []
        for due_second in sorted(by_second):
            occurrences = sorted(
                by_second[due_second],
                key=lambda item: _job_priority(item[0]),
            )
            due_jobs = tuple(
                CadenceDueJobV1(
                    schema_version=CADENCE_DUE_JOB_SCHEMA_VERSION,
                    policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
                    job_id=job.job_id,
                    mode=job.mode,
                    job_kind=job.job_kind,
                    due_timeframes=due_timeframes,
                    armed_conditional=job.armed_conditional,
                )
                for job, due_timeframes in occurrences
            )
            windows.append(
                CadenceDueWindowV1(
                    schema_version=CADENCE_DUE_WINDOW_SCHEMA_VERSION,
                    policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
                    due_second_utc=due_second,
                    ordered_jobs=due_jobs,
                    collision_count=max(0, len(due_jobs) - 1),
                    global_nonoverlap_required=True,
                )
            )
        windows_tuple = tuple(windows)
        return DailyCadencePlanV1(
            schema_version=DAILY_CADENCE_PLAN_SCHEMA_VERSION,
            policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
            armed_modes=canonical_armed_modes,
            logical_mode_job_count=sum(
                len(item.ordered_jobs) for item in windows_tuple
            ),
            unique_due_timestamp_count=len(windows_tuple),
            collision_timestamp_count=sum(
                len(item.ordered_jobs) > 1 for item in windows_tuple
            ),
            windows=windows_tuple,
        )
    except ModeFetchCadenceValidationError:
        raise
    except Exception:
        _invalid()


def admit_cadence_start(
    *,
    delay_seconds: object,
) -> CadenceStartDecisionV1:
    try:
        delay = _integer(delay_seconds, minimum=0)
        admitted = delay <= MAX_JOB_START_DELAY_SECONDS
        return CadenceStartDecisionV1(
            schema_version=CADENCE_START_DECISION_SCHEMA_VERSION,
            policy_version=MODE_FETCH_CADENCE_POLICY_VERSION,
            delay_seconds=delay,
            max_delay_seconds=MAX_JOB_START_DELAY_SECONDS,
            admitted=admitted,
            reason_code=(
                ADMITTED_REASON
                if admitted
                else SKIPPED_START_DELAY_REASON
            ),
            retry_count=0,
            catchup_allowed=False,
            parallel_mode_job_allowed=False,
        )
    except ModeFetchCadenceValidationError:
        raise
    except Exception:
        _invalid()
