"""Pure immutable plan for one mode-owned market scan execution."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Final

from engine.mode_data_plan_v1 import (
    ModeAuditLineageV1,
    ModeDataPlanV1,
    build_mode_audit_lineage,
    build_mode_data_plan,
)
from engine.mode_fetch_budget_cadence_v1 import (
    MODE_FULL_EVALUATION_MAX_SYMBOLS,
    DiscoveryUniversePolicyV1,
    ModeFetchBudgetV1,
    ModeTimeframeFetchV1,
    build_discovery_universe_policy,
    build_mode_fetch_budget,
)
from engine.mode_profile_v1 import (
    ModeProfileV1,
    all_mode_profiles,
    get_mode_profile,
)
from engine.mode_router_v1 import (
    MODE_ROUTER_POLICY_VERSION,
    MODE_SCAN_REQUEST_SCHEMA_VERSION,
    ModeScanRequestV1,
)


MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION: Final = (
    "mode-scan-execution-plan-policy-v1"
)
MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION: Final = (
    "mode-market-snapshot-entry-v1"
)
MODE_TIMEFRAME_FETCH_PLAN_SCHEMA_VERSION: Final = (
    "mode-timeframe-fetch-plan-v1"
)
MODE_SYMBOL_EXECUTION_PLAN_SCHEMA_VERSION: Final = (
    "mode-symbol-execution-plan-v1"
)
MODE_SCAN_EXECUTION_PLAN_SCHEMA_VERSION: Final = (
    "mode-scan-execution-plan-v1"
)

DEVELOPING_CANDLE_POLICY: Final = (
    "DROP_FINAL_DEVELOPING_CANDLE"
)
CANDLE_SUFFICIENCY_POLICY: Final = (
    "FAIL_CLOSED_NO_SHORTER_TIMEFRAME_FALLBACK"
)
CACHE_KEY_FIELDS: Final = (
    "mode",
    "canonical_symbol",
    "timeframe",
    "closed_candle_close_at",
    "mode_data_plan_version",
)
CACHE_KEY_DYNAMIC_FIELD: Final = "closed_candle_close_at"
LIVE_PRICE_BOUNDARY: Final = "SEPARATE_FRESH_PRICE_ADMISSION"
EXECUTION_STATE: Final = "PLAN_ONLY_NOT_EXECUTED"

_LOW_TIER_FETCH_LIMITS: Final = (50, 51)
_HIGH_TIER_FETCH_LIMITS: Final = (300, 301)
_LOW_TIER_PURPOSES: Final = frozenset(
    ("CONTEXT", "OPTIONAL_CONTEXT", "BIAS")
)
_HIGH_TIER_PURPOSES: Final = frozenset(
    ("STRUCTURE", "TRIGGER")
)
_CANONICAL_FETCH_PURPOSES: Final = (
    _LOW_TIER_PURPOSES | _HIGH_TIER_PURPOSES
)

_CANONICAL_MODES: Final = tuple(
    profile.mode for profile in all_mode_profiles()
)
_SAFE_IDENTIFIER: Final = re.compile(
    r"[A-Za-z0-9._:+-]{1,128}"
)
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")


class ModeScanExecutionPlanValidationError(ValueError):
    """Sanitized failure for the pure execution-plan boundary."""


def _invalid() -> None:
    raise ModeScanExecutionPlanValidationError(
        "invalid mode scan execution plan"
    ) from None


def _exact_constant(value: object, expected: str) -> str:
    if type(value) is not str or value != expected:
        _invalid()
    return value


def _text(value: object) -> str:
    if type(value) is not str:
        _invalid()
    return value


def _canonical_symbol(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 128
        or value != value.strip()
    ):
        _invalid()
    return value


def _safe_identifier(value: object) -> str:
    if (
        type(value) is not str
        or _SAFE_IDENTIFIER.fullmatch(value) is None
    ):
        _invalid()
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        _invalid()
    return value


def _integer(
    value: object,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if type(value) is not int or value < minimum:
        _invalid()
    if maximum is not None and value > maximum:
        _invalid()
    return value


def _finite_nonnegative(value: object) -> int | float:
    if type(value) not in (int, float):
        _invalid()
    if not math.isfinite(value) or value < 0:
        _invalid()
    if type(value) is float and value == 0.0:
        return 0.0
    return value


def _sha256_hex(value: object) -> str:
    if (
        type(value) is not str
        or _SHA256_HEX.fullmatch(value) is None
    ):
        _invalid()
    return value


def _canonical_mode(value: object) -> str:
    if type(value) is not str or value not in _CANONICAL_MODES:
        _invalid()
    try:
        profile = get_mode_profile(value)
    except Exception:
        _invalid()
    if type(profile) is not ModeProfileV1 or profile.mode != value:
        _invalid()
    return profile.mode


def _expected_lineage(mode: str) -> str:
    try:
        lineage = build_mode_audit_lineage(mode)
    except Exception:
        _invalid()
    if type(lineage) is not ModeAuditLineageV1:
        _invalid()
    return _sha256_hex(lineage.lineage_sha256)


def _validate_json_value(value: object) -> None:
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        if not math.isfinite(value):
            _invalid()
        return
    if type(value) is list:
        for item in value:
            _validate_json_value(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _invalid()
            _validate_json_value(item)
        return
    _invalid()


def _canonical_json(value: object) -> str:
    _validate_json_value(value)
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


def _canonical_mapping_json(value: object) -> str:
    if type(value) is not dict:
        _invalid()
    return _canonical_json(value)


def _decoded_mapping(value: object) -> dict[str, Any]:
    if type(value) is not str:
        _invalid()
    try:
        decoded = json.loads(value)
    except Exception:
        _invalid()
    if type(decoded) is not dict:
        _invalid()
    if _canonical_mapping_json(decoded) != value:
        _invalid()
    return decoded


def _hash_json(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _exact_cache_fields(value: object) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or any(type(item) is not str for item in value)
        or value != CACHE_KEY_FIELDS
    ):
        _invalid()
    return value


def _selected_requirements(
    plan: ModeDataPlanV1,
    include_optional_context: bool,
) -> tuple[tuple[str, str, bool], ...]:
    selected = []
    by_timeframe: dict[str, list[object]] = {}
    order: list[str] = []
    for requirement in plan.timeframe_requirements:
        if not requirement.required and not include_optional_context:
            continue
        if requirement.timeframe not in by_timeframe:
            by_timeframe[requirement.timeframe] = []
            order.append(requirement.timeframe)
        by_timeframe[requirement.timeframe].append(requirement)
    for timeframe in order:
        requirements = by_timeframe[timeframe]
        selected.append(
            (
                timeframe,
                "+".join(
                    requirement.purpose
                    for requirement in requirements
                ),
                any(
                    not requirement.required
                    for requirement in requirements
                ),
            )
        )
    return tuple(selected)


def _canonical_timeframe_fetch_limits(
    role: object,
) -> tuple[int, int]:
    if type(role) is not str or not role:
        _invalid()
    purposes = tuple(role.split("+"))
    if (
        not purposes
        or any(not purpose for purpose in purposes)
        or len(set(purposes)) != len(purposes)
        or any(
            purpose not in _CANONICAL_FETCH_PURPOSES
            for purpose in purposes
        )
    ):
        _invalid()
    if any(
        purpose in _HIGH_TIER_PURPOSES
        for purpose in purposes
    ):
        return _HIGH_TIER_FETCH_LIMITS
    if all(
        purpose in _LOW_TIER_PURPOSES
        for purpose in purposes
    ):
        return _LOW_TIER_FETCH_LIMITS
    _invalid()


def _copy_fetch(
    value: ModeTimeframeFetchPlanV1,
) -> ModeTimeframeFetchPlanV1:
    mapping = value.to_mapping()
    mapping["cache_key_fields"] = tuple(
        mapping["cache_key_fields"]
    )
    return ModeTimeframeFetchPlanV1(**mapping)


def _copy_symbol_plan(
    value: ModeSymbolExecutionPlanV1,
) -> ModeSymbolExecutionPlanV1:
    mapping = value.to_mapping()
    mapping["candle_fetches"] = tuple(
        ModeTimeframeFetchPlanV1(
            **{
                **item,
                "cache_key_fields": tuple(
                    item["cache_key_fields"]
                ),
            }
        )
        for item in mapping["candle_fetches"]
    )
    return ModeSymbolExecutionPlanV1(**mapping)


def _discovery_policy_from_json(
    value: object,
) -> DiscoveryUniversePolicyV1:
    mapping = _decoded_mapping(value)
    try:
        policy = DiscoveryUniversePolicyV1(**mapping)
    except Exception:
        _invalid()
    if type(policy) is not DiscoveryUniversePolicyV1:
        _invalid()
    return policy


def _fetch_budget_from_json(
    value: object,
) -> ModeFetchBudgetV1:
    mapping = _decoded_mapping(value)
    fetch_values = mapping.get("timeframe_fetches")
    if type(fetch_values) is not list:
        _invalid()
    try:
        fetches = tuple(
            ModeTimeframeFetchV1(
                **{
                    **item,
                    "purposes": tuple(item["purposes"]),
                }
            )
            for item in fetch_values
            if type(item) is dict
        )
        if len(fetches) != len(fetch_values):
            _invalid()
        budget = ModeFetchBudgetV1(
            **{
                **mapping,
                "timeframe_fetches": fetches,
            }
        )
    except ModeScanExecutionPlanValidationError:
        raise
    except Exception:
        _invalid()
    if type(budget) is not ModeFetchBudgetV1:
        _invalid()
    return budget


def _validated_request(
    request: object,
) -> tuple[
    ModeScanRequestV1,
    ModeProfileV1,
    ModeDataPlanV1,
    ModeAuditLineageV1,
]:
    if type(request) is not ModeScanRequestV1:
        _invalid()
    try:
        _exact_constant(
            request.schema_version,
            MODE_SCAN_REQUEST_SCHEMA_VERSION,
        )
        _exact_constant(
            request.router_policy_version,
            MODE_ROUTER_POLICY_VERSION,
        )
        profile = get_mode_profile(request.mode)
        plan = build_mode_data_plan(profile.mode)
        lineage = build_mode_audit_lineage(profile.mode)
    except ModeScanExecutionPlanValidationError:
        raise
    except Exception:
        _invalid()
    if (
        type(profile) is not ModeProfileV1
        or type(plan) is not ModeDataPlanV1
        or type(lineage) is not ModeAuditLineageV1
        or request.mode_profile is not profile
        or type(request.mode_data_plan) is not ModeDataPlanV1
        or type(request.mode_audit_lineage) is not ModeAuditLineageV1
        or _canonical_mapping_json(
            request.mode_data_plan.to_mapping()
        )
        != _canonical_mapping_json(plan.to_mapping())
        or _canonical_mapping_json(
            request.mode_audit_lineage.to_mapping()
        )
        != _canonical_mapping_json(lineage.to_mapping())
        or request.mode_data_plan.mode != profile.mode
        or request.mode_audit_lineage.mode != profile.mode
        or request.mode_audit_lineage.lineage_sha256
        != lineage.lineage_sha256
    ):
        _invalid()
    _safe_identifier(request.due_window_id)
    return request, profile, plan, lineage


@dataclass(frozen=True, slots=True)
class ModeMarketSnapshotEntryV1:
    schema_version: str
    canonical_symbol: str
    quote_asset: str
    settle_asset: str
    market_kind: str
    active: bool
    linear: bool
    perpetual: bool
    quote_volume_24h: int | float

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
            )
            object.__setattr__(
                self,
                "canonical_symbol",
                _canonical_symbol(self.canonical_symbol),
            )
            _text(self.quote_asset)
            _text(self.settle_asset)
            _text(self.market_kind)
            _boolean(self.active)
            _boolean(self.linear)
            _boolean(self.perpetual)
            object.__setattr__(
                self,
                "quote_volume_24h",
                _finite_nonnegative(self.quote_volume_24h),
            )
        except ModeScanExecutionPlanValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "canonical_symbol": self.canonical_symbol,
            "quote_asset": self.quote_asset,
            "settle_asset": self.settle_asset,
            "market_kind": self.market_kind,
            "active": self.active,
            "linear": self.linear,
            "perpetual": self.perpetual,
            "quote_volume_24h": self.quote_volume_24h,
        }


def _validated_market_entry(
    value: object,
) -> ModeMarketSnapshotEntryV1:
    if type(value) is not ModeMarketSnapshotEntryV1:
        _invalid()
    try:
        return ModeMarketSnapshotEntryV1(**value.to_mapping())
    except ModeScanExecutionPlanValidationError:
        raise
    except Exception:
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeTimeframeFetchPlanV1:
    schema_version: str
    policy_version: str
    mode: str
    mode_lineage_sha256: str
    canonical_symbol: str
    timeframe: str
    role: str
    optional_context: bool
    closed_candle_limit: int
    raw_fetch_limit: int
    developing_candle_policy: str
    candle_sufficiency_policy: str
    cache_key_fields: tuple[str, ...]
    cache_key_dynamic_field: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_TIMEFRAME_FETCH_PLAN_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION,
            )
            mode = _canonical_mode(self.mode)
            expected_lineage = _expected_lineage(mode)
            if (
                _sha256_hex(self.mode_lineage_sha256)
                != expected_lineage
            ):
                _invalid()
            _canonical_symbol(self.canonical_symbol)
            timeframe = _text(self.timeframe)
            role = _text(self.role)
            optional = _boolean(self.optional_context)
            plan = build_mode_data_plan(mode)
            selected = _selected_requirements(plan, optional)
            expected = {
                item_timeframe: (item_role, item_optional)
                for item_timeframe, item_role, item_optional
                in selected
            }
            if (
                timeframe not in expected
                or expected[timeframe] != (role, optional)
            ):
                _invalid()
            closed_limit = _integer(
                self.closed_candle_limit,
                minimum=1,
            )
            raw_limit = _integer(
                self.raw_fetch_limit,
                minimum=1,
            )
            expected_closed_limit, expected_raw_limit = (
                _canonical_timeframe_fetch_limits(role)
            )
            if (
                raw_limit != closed_limit + 1
                or closed_limit != expected_closed_limit
                or raw_limit != expected_raw_limit
            ):
                _invalid()
            _exact_constant(
                self.developing_candle_policy,
                DEVELOPING_CANDLE_POLICY,
            )
            _exact_constant(
                self.candle_sufficiency_policy,
                CANDLE_SUFFICIENCY_POLICY,
            )
            _exact_cache_fields(self.cache_key_fields)
            _exact_constant(
                self.cache_key_dynamic_field,
                CACHE_KEY_DYNAMIC_FIELD,
            )
        except ModeScanExecutionPlanValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "canonical_symbol": self.canonical_symbol,
            "timeframe": self.timeframe,
            "role": self.role,
            "optional_context": self.optional_context,
            "closed_candle_limit": self.closed_candle_limit,
            "raw_fetch_limit": self.raw_fetch_limit,
            "developing_candle_policy":
                self.developing_candle_policy,
            "candle_sufficiency_policy":
                self.candle_sufficiency_policy,
            "cache_key_fields": list(self.cache_key_fields),
            "cache_key_dynamic_field":
                self.cache_key_dynamic_field,
        }


@dataclass(frozen=True, slots=True)
class ModeSymbolExecutionPlanV1:
    schema_version: str
    policy_version: str
    mode: str
    mode_lineage_sha256: str
    canonical_symbol: str
    quote_volume_24h: int | float
    discovery_rank: int
    full_evaluation_rank: int
    open_interest_history_request_count: int
    candle_fetches: tuple[ModeTimeframeFetchPlanV1, ...]

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_SYMBOL_EXECUTION_PLAN_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION,
            )
            mode = _canonical_mode(self.mode)
            expected_lineage = _expected_lineage(mode)
            if (
                _sha256_hex(self.mode_lineage_sha256)
                != expected_lineage
            ):
                _invalid()
            symbol = _canonical_symbol(self.canonical_symbol)
            object.__setattr__(
                self,
                "quote_volume_24h",
                _finite_nonnegative(self.quote_volume_24h),
            )
            _integer(self.discovery_rank, minimum=1)
            _integer(
                self.full_evaluation_rank,
                minimum=1,
                maximum=MODE_FULL_EVALUATION_MAX_SYMBOLS,
            )
            if (
                type(self.open_interest_history_request_count)
                is not int
                or self.open_interest_history_request_count != 1
            ):
                _invalid()
            if type(self.candle_fetches) not in (list, tuple):
                _invalid()
            copied = tuple(
                _copy_fetch(item)
                for item in self.candle_fetches
                if type(item) is ModeTimeframeFetchPlanV1
            )
            if len(copied) != len(self.candle_fetches):
                _invalid()
            object.__setattr__(self, "candle_fetches", copied)
            if not copied:
                _invalid()
            timeframes = tuple(item.timeframe for item in copied)
            if len(set(timeframes)) != len(timeframes):
                _invalid()
            include_optional = any(
                item.optional_context for item in copied
            )
            plan = build_mode_data_plan(mode)
            expected = _selected_requirements(
                plan,
                include_optional,
            )
            actual = tuple(
                (
                    item.timeframe,
                    item.role,
                    item.optional_context,
                )
                for item in copied
            )
            if actual != expected:
                _invalid()
            for item in copied:
                if (
                    item.mode != mode
                    or item.mode_lineage_sha256
                    != expected_lineage
                    or item.canonical_symbol != symbol
                ):
                    _invalid()
        except ModeScanExecutionPlanValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "canonical_symbol": self.canonical_symbol,
            "quote_volume_24h": self.quote_volume_24h,
            "discovery_rank": self.discovery_rank,
            "full_evaluation_rank": self.full_evaluation_rank,
            "open_interest_history_request_count":
                self.open_interest_history_request_count,
            "candle_fetches": [
                item.to_mapping()
                for item in self.candle_fetches
            ],
        }


@dataclass(frozen=True, slots=True)
class ModeScanExecutionPlanV1:
    schema_version: str
    policy_version: str
    mode: str
    due_window_id: str
    mode_lineage_sha256: str
    include_optional_context: bool
    market_snapshot_sha256: str
    market_snapshot_count: int
    eligible_market_count: int
    discovery_symbol_count: int
    discovery_truncated_count: int
    full_evaluation_symbol_count: int
    full_evaluation_truncated_count: int
    discovery_symbols: tuple[str, ...]
    full_evaluation_symbols: tuple[
        ModeSymbolExecutionPlanV1,
        ...,
    ]
    discovery_policy_json: str
    discovery_policy_sha256: str
    fetch_budget_json: str
    fetch_budget_sha256: str
    cache_key_fields: tuple[str, ...]
    cache_key_dynamic_field: str
    live_price_boundary: str
    execution_state: str
    execution_performed: bool
    actual_network_call_count: int
    actual_candidate_count: int
    validation_pipeline_invocation_count: int
    retry_count: int
    plan_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_SCAN_EXECUTION_PLAN_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION,
            )
            mode = _canonical_mode(self.mode)
            expected_lineage = _expected_lineage(mode)
            _safe_identifier(self.due_window_id)
            if (
                _sha256_hex(self.mode_lineage_sha256)
                != expected_lineage
            ):
                _invalid()
            include_optional = _boolean(
                self.include_optional_context
            )
            _sha256_hex(self.market_snapshot_sha256)
            snapshot_count = _integer(
                self.market_snapshot_count,
                minimum=0,
            )
            eligible_count = _integer(
                self.eligible_market_count,
                minimum=0,
            )
            discovery_count = _integer(
                self.discovery_symbol_count,
                minimum=1,
            )
            discovery_truncated = _integer(
                self.discovery_truncated_count,
                minimum=0,
            )
            full_count = _integer(
                self.full_evaluation_symbol_count,
                minimum=1,
                maximum=MODE_FULL_EVALUATION_MAX_SYMBOLS,
            )
            full_truncated = _integer(
                self.full_evaluation_truncated_count,
                minimum=0,
            )
            policy = _discovery_policy_from_json(
                self.discovery_policy_json
            )
            if (
                _sha256_hex(self.discovery_policy_sha256)
                != _hash_json(self.discovery_policy_json)
            ):
                _invalid()
            budget = _fetch_budget_from_json(
                self.fetch_budget_json
            )
            if (
                _sha256_hex(self.fetch_budget_sha256)
                != _hash_json(self.fetch_budget_json)
                or budget.mode != mode
                or budget.include_optional_context
                is not include_optional
                or budget.symbol_count != full_count
            ):
                _invalid()
            if (
                snapshot_count < eligible_count
                or eligible_count < discovery_count
                or discovery_count < full_count
                or discovery_count > policy.max_symbols
                or discovery_truncated
                != eligible_count - discovery_count
                or full_truncated != discovery_count - full_count
            ):
                _invalid()
            if type(self.discovery_symbols) not in (list, tuple):
                _invalid()
            discovery_symbols = tuple(
                _canonical_symbol(item)
                for item in self.discovery_symbols
            )
            object.__setattr__(
                self,
                "discovery_symbols",
                discovery_symbols,
            )
            if (
                len(discovery_symbols) != discovery_count
                or len(set(discovery_symbols))
                != len(discovery_symbols)
            ):
                _invalid()
            if (
                type(self.full_evaluation_symbols)
                not in (list, tuple)
            ):
                _invalid()
            full_symbols = tuple(
                _copy_symbol_plan(item)
                for item in self.full_evaluation_symbols
                if type(item) is ModeSymbolExecutionPlanV1
            )
            if len(full_symbols) != len(
                self.full_evaluation_symbols
            ):
                _invalid()
            object.__setattr__(
                self,
                "full_evaluation_symbols",
                full_symbols,
            )
            if len(full_symbols) != full_count:
                _invalid()
            nested_symbols: set[str] = set()
            nested_discovery_ranks: set[int] = set()
            nested_full_ranks: set[int] = set()
            prior_order: tuple[int | float, str] | None = None
            budget_fetches = budget.timeframe_fetches
            for rank, item in enumerate(full_symbols, start=1):
                if (
                    item.mode != mode
                    or item.mode_lineage_sha256
                    != expected_lineage
                    or item.canonical_symbol
                    != discovery_symbols[rank - 1]
                    or item.discovery_rank != rank
                    or item.full_evaluation_rank != rank
                    or item.canonical_symbol in nested_symbols
                    or item.discovery_rank
                    in nested_discovery_ranks
                    or item.full_evaluation_rank
                    in nested_full_ranks
                    or item.open_interest_history_request_count
                    != 1
                    or len(item.candle_fetches)
                    != len(budget_fetches)
                ):
                    _invalid()
                for planned, budgeted in zip(
                    item.candle_fetches,
                    budget_fetches,
                    strict=True,
                ):
                    if (
                        planned.timeframe
                        != budgeted.timeframe
                        or planned.role
                        != "+".join(budgeted.purposes)
                        or planned.optional_context
                        != any(
                            not requirement.required
                            and requirement.timeframe
                            == budgeted.timeframe
                            and requirement.purpose
                            in budgeted.purposes
                            for requirement
                            in build_mode_data_plan(
                                mode
                            ).timeframe_requirements
                        )
                        or planned.closed_candle_limit
                        != budgeted.closed_candle_count
                        or planned.raw_fetch_limit
                        != budgeted.raw_fetch_limit
                    ):
                        _invalid()
                current_order = (
                    -item.quote_volume_24h,
                    item.canonical_symbol,
                )
                if (
                    prior_order is not None
                    and current_order < prior_order
                ):
                    _invalid()
                prior_order = current_order
                nested_symbols.add(item.canonical_symbol)
                nested_discovery_ranks.add(item.discovery_rank)
                nested_full_ranks.add(item.full_evaluation_rank)
            if tuple(
                item.canonical_symbol for item in full_symbols
            ) != discovery_symbols[:full_count]:
                _invalid()
            _exact_cache_fields(self.cache_key_fields)
            _exact_constant(
                self.cache_key_dynamic_field,
                CACHE_KEY_DYNAMIC_FIELD,
            )
            _exact_constant(
                self.live_price_boundary,
                LIVE_PRICE_BOUNDARY,
            )
            _exact_constant(
                self.execution_state,
                EXECUTION_STATE,
            )
            if _boolean(self.execution_performed) is not False:
                _invalid()
            for value in (
                self.actual_network_call_count,
                self.actual_candidate_count,
                self.validation_pipeline_invocation_count,
                self.retry_count,
            ):
                if type(value) is not int or value != 0:
                    _invalid()
            supplied_plan_hash = _sha256_hex(self.plan_sha256)
            if supplied_plan_hash != _hash_json(
                _canonical_mapping_json(
                    self._content_mapping()
                )
            ):
                _invalid()
        except ModeScanExecutionPlanValidationError:
            raise
        except Exception:
            _invalid()

    def discovery_policy_copy(self) -> dict[str, Any]:
        return _decoded_mapping(self.discovery_policy_json)

    def fetch_budget_copy(self) -> dict[str, Any]:
        return _decoded_mapping(self.fetch_budget_json)

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "due_window_id": self.due_window_id,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "include_optional_context":
                self.include_optional_context,
            "market_snapshot_sha256":
                self.market_snapshot_sha256,
            "market_snapshot_count": self.market_snapshot_count,
            "eligible_market_count": self.eligible_market_count,
            "discovery_symbol_count":
                self.discovery_symbol_count,
            "discovery_truncated_count":
                self.discovery_truncated_count,
            "full_evaluation_symbol_count":
                self.full_evaluation_symbol_count,
            "full_evaluation_truncated_count":
                self.full_evaluation_truncated_count,
            "discovery_symbols": list(self.discovery_symbols),
            "full_evaluation_symbols": [
                item.to_mapping()
                for item in self.full_evaluation_symbols
            ],
            "discovery_policy_json":
                self.discovery_policy_json,
            "discovery_policy_sha256":
                self.discovery_policy_sha256,
            "fetch_budget_json": self.fetch_budget_json,
            "fetch_budget_sha256": self.fetch_budget_sha256,
            "cache_key_fields": list(self.cache_key_fields),
            "cache_key_dynamic_field":
                self.cache_key_dynamic_field,
            "live_price_boundary": self.live_price_boundary,
            "execution_state": self.execution_state,
            "execution_performed": self.execution_performed,
            "actual_network_call_count":
                self.actual_network_call_count,
            "actual_candidate_count":
                self.actual_candidate_count,
            "validation_pipeline_invocation_count":
                self.validation_pipeline_invocation_count,
            "retry_count": self.retry_count,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["plan_sha256"] = self.plan_sha256
        return mapping


def build_mode_scan_execution_plan(
    *,
    request: object,
    market_snapshot: object,
    include_optional_context: object,
) -> ModeScanExecutionPlanV1:
    """Build one deterministic plan without executing any dependency."""

    try:
        request, profile, plan, lineage = _validated_request(
            request
        )
        include_optional = _boolean(include_optional_context)
        optional_available = any(
            not requirement.required
            for requirement in plan.timeframe_requirements
        )
        if include_optional and not optional_available:
            _invalid()
        if type(market_snapshot) not in (list, tuple):
            _invalid()
        snapshot = tuple(
            _validated_market_entry(item)
            for item in market_snapshot
        )
        snapshot_symbols = tuple(
            item.canonical_symbol for item in snapshot
        )
        if len(set(snapshot_symbols)) != len(snapshot_symbols):
            _invalid()
        snapshot_json = _canonical_json(
            [item.to_mapping() for item in snapshot]
        )
        snapshot_hash = _hash_json(snapshot_json)

        eligible = tuple(
            item
            for item in snapshot
            if (
                item.active is True
                and item.quote_asset == "USDT"
                and item.settle_asset == "USDT"
                and item.market_kind == "swap"
                and item.linear is True
                and item.perpetual is True
            )
        )
        if not eligible:
            _invalid()
        ordered = tuple(
            sorted(
                eligible,
                key=lambda item: (
                    -item.quote_volume_24h,
                    item.canonical_symbol,
                ),
            )
        )
        discovery_policy = build_discovery_universe_policy()
        if type(discovery_policy) is not DiscoveryUniversePolicyV1:
            _invalid()
        discovered = ordered[:discovery_policy.max_symbols]
        full_entries = discovered[
            :MODE_FULL_EVALUATION_MAX_SYMBOLS
        ]
        fetch_budget = build_mode_fetch_budget(
            mode=profile.mode,
            symbol_count=len(full_entries),
            include_optional_context=include_optional,
        )
        if type(fetch_budget) is not ModeFetchBudgetV1:
            _invalid()
        discovery_policy_json = _canonical_mapping_json(
            discovery_policy.to_mapping()
        )
        fetch_budget_json = _canonical_mapping_json(
            fetch_budget.to_mapping()
        )

        symbol_plans = []
        for rank, entry in enumerate(full_entries, start=1):
            candle_fetches = []
            for budgeted in fetch_budget.timeframe_fetches:
                optional_context = any(
                    not requirement.required
                    and requirement.timeframe
                    == budgeted.timeframe
                    and requirement.purpose
                    in budgeted.purposes
                    for requirement
                    in plan.timeframe_requirements
                )
                candle_fetches.append(
                    ModeTimeframeFetchPlanV1(
                        schema_version=(
                            MODE_TIMEFRAME_FETCH_PLAN_SCHEMA_VERSION
                        ),
                        policy_version=(
                            MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION
                        ),
                        mode=profile.mode,
                        mode_lineage_sha256=(
                            lineage.lineage_sha256
                        ),
                        canonical_symbol=entry.canonical_symbol,
                        timeframe=budgeted.timeframe,
                        role="+".join(budgeted.purposes),
                        optional_context=optional_context,
                        closed_candle_limit=(
                            budgeted.closed_candle_count
                        ),
                        raw_fetch_limit=budgeted.raw_fetch_limit,
                        developing_candle_policy=(
                            DEVELOPING_CANDLE_POLICY
                        ),
                        candle_sufficiency_policy=(
                            CANDLE_SUFFICIENCY_POLICY
                        ),
                        cache_key_fields=CACHE_KEY_FIELDS,
                        cache_key_dynamic_field=(
                            CACHE_KEY_DYNAMIC_FIELD
                        ),
                    )
                )
            symbol_plans.append(
                ModeSymbolExecutionPlanV1(
                    schema_version=(
                        MODE_SYMBOL_EXECUTION_PLAN_SCHEMA_VERSION
                    ),
                    policy_version=(
                        MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION
                    ),
                    mode=profile.mode,
                    mode_lineage_sha256=lineage.lineage_sha256,
                    canonical_symbol=entry.canonical_symbol,
                    quote_volume_24h=entry.quote_volume_24h,
                    discovery_rank=rank,
                    full_evaluation_rank=rank,
                    open_interest_history_request_count=1,
                    candle_fetches=tuple(candle_fetches),
                )
            )

        content: dict[str, object] = {
            "schema_version":
                MODE_SCAN_EXECUTION_PLAN_SCHEMA_VERSION,
            "policy_version":
                MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION,
            "mode": profile.mode,
            "due_window_id": request.due_window_id,
            "mode_lineage_sha256": lineage.lineage_sha256,
            "include_optional_context": include_optional,
            "market_snapshot_sha256": snapshot_hash,
            "market_snapshot_count": len(snapshot),
            "eligible_market_count": len(eligible),
            "discovery_symbol_count": len(discovered),
            "discovery_truncated_count":
                len(eligible) - len(discovered),
            "full_evaluation_symbol_count": len(full_entries),
            "full_evaluation_truncated_count":
                len(discovered) - len(full_entries),
            "discovery_symbols": [
                item.canonical_symbol for item in discovered
            ],
            "full_evaluation_symbols": [
                item.to_mapping() for item in symbol_plans
            ],
            "discovery_policy_json": discovery_policy_json,
            "discovery_policy_sha256":
                _hash_json(discovery_policy_json),
            "fetch_budget_json": fetch_budget_json,
            "fetch_budget_sha256":
                _hash_json(fetch_budget_json),
            "cache_key_fields": list(CACHE_KEY_FIELDS),
            "cache_key_dynamic_field":
                CACHE_KEY_DYNAMIC_FIELD,
            "live_price_boundary": LIVE_PRICE_BOUNDARY,
            "execution_state": EXECUTION_STATE,
            "execution_performed": False,
            "actual_network_call_count": 0,
            "actual_candidate_count": 0,
            "validation_pipeline_invocation_count": 0,
            "retry_count": 0,
        }
        plan_hash = _hash_json(_canonical_mapping_json(content))
        return ModeScanExecutionPlanV1(
            **{
                **content,
                "discovery_symbols": tuple(
                    content["discovery_symbols"]
                ),
                "full_evaluation_symbols":
                    tuple(symbol_plans),
                "cache_key_fields": CACHE_KEY_FIELDS,
                "plan_sha256": plan_hash,
            }
        )
    except ModeScanExecutionPlanValidationError:
        raise
    except Exception:
        _invalid()
