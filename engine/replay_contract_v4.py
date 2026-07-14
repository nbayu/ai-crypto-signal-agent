"""Immutable, network-free validation for executable Replay V4 bundles."""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping


REPLAY_BUNDLE_SCHEMA_VERSION = 2

_TOP_LEVEL_REQUIRED = frozenset(
    {
        "schema_version",
        "source_commit",
        "recorded_at",
        "fixed_execution_time",
        "execution_configuration",
        "scanner_results",
        "recorded_open_interest",
        "recorded_validator_response",
        "recorded_validator_usage",
        "pre_delivery_closed_candles",
        "expected_semantic_contract",
    }
)
_EXECUTION_CONFIGURATION_KEYS = frozenset({"timeframe", "lookback", "limit"})
_SCANNER_RESULT_KEYS = frozenset(
    {
        "symbol",
        "score",
        "direction",
        "entry",
        "stop_loss",
        "take_profit",
        "reference_price",
        "reference_candle_at",
        "golden_zone",
        "trend",
        "bos",
        "choch",
        "volume_ratio",
        "volume_v2_status",
    }
)
_GOLDEN_ZONE_KEYS = frozenset(
    {
        "direction",
        "swing_low_index",
        "swing_high_index",
        "swing_low_at",
        "swing_high_at",
        "swing_low",
        "swing_high",
        "levels",
        "entry_zone",
        "take_profit",
        "stop_loss",
    }
)
_GOLDEN_LEVEL_KEYS = frozenset({"-0.27", "0.0", "0.5", "0.618", "0.786", "1.0"})
_ENTRY_ZONE_KEYS = frozenset({"level_from", "level_to", "price_low", "price_high"})
_TARGET_KEYS = frozenset({"level", "price"})
_OPEN_INTEREST_KEYS = frozenset(
    {"current_oi", "previous_oi", "oi_change_pct", "oi_score", "data_status"}
)
_VALIDATOR_RESPONSE_KEYS = frozenset({"content"})
_VALIDATOR_CONTENT_KEYS = frozenset({"validations"})
_VALIDATION_KEYS = frozenset(
    {"symbol", "status", "false_breakout_risk", "confluence", "reason_code"}
)
_VALIDATOR_USAGE_KEYS = frozenset(
    {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cache_hit_tokens",
        "cache_miss_tokens",
    }
)
_CANDLE_KEYS = frozenset({"open_time", "open", "high", "low", "close", "volume"})
_SEMANTIC_CONTRACT_KEYS = frozenset({"classification", "boundary"})
_PROHIBITED_KEYS = frozenset(
    {
        "api_key",
        "secret",
        "password",
        "token",
        "telegram_bot_token",
        "authorization",
        "endpoint",
        "base_url",
        "provider_url",
        "quota_state_path",
        "worker_state_path",
        "production_output_path",
        "production_path",
        "output_path",
        "latest_path",
    }
)
_COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40}")
_DIRECTIONS = frozenset({"BULLISH", "BEARISH"})
_TRENDS = frozenset({"UPTREND", "DOWNTREND"})
_VOLUME_STATUSES = frozenset({"OK", "INSUFFICIENT_DATA", "INVALID_AVERAGE"})
_OI_STATUSES = frozenset({"OK", "API_ERROR", "INVALID_RESPONSE", "INVALID_BASE"})
_VALIDATION_STATUSES = frozenset({"CLEAR", "CONFLICT", "HIGH_RISK"})
_FALSE_BREAKOUT_RISKS = frozenset({"LOW", "MEDIUM", "HIGH"})
_CONFLUENCE_VALUES = frozenset({"STRONG", "MODERATE", "WEAK"})
_REASON_CODES = frozenset(
    {
        "ALIGNED",
        "STRUCTURE_REVERSAL_CONFLICT",
        "WEAK_VOLUME",
        "WEAK_OI",
        "WEAK_PARTICIPATION",
        "MIXED_PARTICIPATION",
        "DATA_UNAVAILABLE",
        "BREAKOUT_UNCONFIRMED",
        "MULTIPLE_CONFLICTS",
    }
)
_FIBONACCI_LEVELS = (-0.27, 0.0, 0.5, 0.618, 0.786, 1.0)


class ReplayBundleValidationError(ValueError):
    """Raised when a replay bundle is invalid or unsafe to execute."""


@dataclass(frozen=True)
class ReplayBundleV4:
    schema_version: int
    source_commit: str
    recorded_at: str
    fixed_execution_time: str
    execution_configuration: Mapping[str, Any]
    scanner_results: tuple[Mapping[str, Any], ...]
    recorded_open_interest: Mapping[str, Mapping[str, Any]]
    recorded_validator_response: Mapping[str, Any]
    recorded_validator_usage: Mapping[str, Any]
    pre_delivery_closed_candles: Mapping[str, tuple[Mapping[str, Any], ...]]
    expected_semantic_contract: Mapping[str, Any]


def load_replay_bundle_v4(path) -> ReplayBundleV4:
    """Read and validate one JSON replay bundle without writing state."""
    try:
        source_path = Path(path)
        if not source_path.is_file():
            _fail()
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except ReplayBundleValidationError:
        raise
    except (OSError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        _fail()
    return validate_replay_bundle_v4(payload)


def validate_replay_bundle_v4(bundle: Mapping[str, Any]) -> ReplayBundleV4:
    """Validate a Schema V2 mapping and return an immutable replay contract."""
    _require_mapping(bundle)
    _reject_prohibited_keys(bundle)
    _require_exact_keys(bundle, _TOP_LEVEL_REQUIRED)

    schema_version = bundle["schema_version"]
    if type(schema_version) is not int or schema_version != REPLAY_BUNDLE_SCHEMA_VERSION:
        _fail()

    source_commit = _normalize_source_commit(bundle["source_commit"])
    recorded_at = _normalize_timestamp(bundle["recorded_at"])
    fixed_execution_time = _normalize_timestamp(bundle["fixed_execution_time"])
    execution_configuration = _validate_execution_configuration(
        bundle["execution_configuration"]
    )
    scanner_results = _validate_scanner_results(bundle["scanner_results"])
    recorded_open_interest = _validate_recorded_open_interest(
        bundle["recorded_open_interest"], scanner_results
    )
    validator_response = _validate_validator_response(
        bundle["recorded_validator_response"], scanner_results
    )
    validator_usage = _validate_validator_usage(bundle["recorded_validator_usage"])
    candles = _validate_pre_delivery_candles(
        bundle["pre_delivery_closed_candles"], scanner_results
    )
    semantic_contract = _validate_semantic_contract(bundle["expected_semantic_contract"])

    return ReplayBundleV4(
        schema_version=schema_version,
        source_commit=source_commit,
        recorded_at=recorded_at,
        fixed_execution_time=fixed_execution_time,
        execution_configuration=_freeze(execution_configuration),
        scanner_results=tuple(_freeze(row) for row in scanner_results),
        recorded_open_interest=_freeze(recorded_open_interest),
        recorded_validator_response=_freeze(validator_response),
        recorded_validator_usage=_freeze(validator_usage),
        pre_delivery_closed_candles=_freeze(candles),
        expected_semantic_contract=_freeze(semantic_contract),
    )


def canonicalize_replay_bundle_v4(bundle) -> bytes:
    """Return deterministic UTF-8 JSON bytes for Schema V2 semantic content."""
    validated = _as_validated_bundle(bundle)
    return json.dumps(
        _semantic_content(validated),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def calculate_replay_bundle_hash_v4(bundle) -> str:
    """Return the SHA-256 digest of canonical replay semantic content."""
    return hashlib.sha256(canonicalize_replay_bundle_v4(bundle)).hexdigest()


def derive_replay_fixture_id_v4(bundle) -> str:
    """Derive a stable fixture identity from canonical replay content."""
    return f"fixture-v4-{calculate_replay_bundle_hash_v4(bundle)[:24]}"


def derive_replay_id_v4(bundle) -> str:
    """Derive a stable replay-run identity in a distinct hash domain."""
    digest = hashlib.sha256(
        b"replay-v4\x00" + canonicalize_replay_bundle_v4(bundle)
    ).hexdigest()
    return f"replay-v4-{digest[:24]}"


def _as_validated_bundle(bundle) -> ReplayBundleV4:
    if isinstance(bundle, ReplayBundleV4):
        return bundle
    return validate_replay_bundle_v4(bundle)


def _semantic_content(bundle: ReplayBundleV4) -> dict[str, Any]:
    return {
        "schema_version": bundle.schema_version,
        "source_commit": bundle.source_commit,
        "recorded_at": bundle.recorded_at,
        "fixed_execution_time": bundle.fixed_execution_time,
        "execution_configuration": _thaw(bundle.execution_configuration),
        "scanner_results": _thaw(bundle.scanner_results),
        "recorded_open_interest": _thaw(bundle.recorded_open_interest),
        "recorded_validator_response": _thaw(bundle.recorded_validator_response),
        "recorded_validator_usage": _thaw(bundle.recorded_validator_usage),
        "pre_delivery_closed_candles": _thaw(bundle.pre_delivery_closed_candles),
        "expected_semantic_contract": _thaw(bundle.expected_semantic_contract),
    }


def _validate_execution_configuration(value) -> dict[str, Any]:
    _require_mapping(value)
    _require_exact_keys(value, _EXECUTION_CONFIGURATION_KEYS)
    return {
        "timeframe": _nonblank_string(value["timeframe"]),
        "lookback": _positive_integer(value["lookback"]),
        "limit": _positive_integer(value["limit"]),
    }


def _validate_scanner_results(value) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        _fail()

    symbols = set()
    rows = []
    for row in value:
        _require_mapping(row)
        _require_exact_keys(row, _SCANNER_RESULT_KEYS)
        symbol = _nonblank_string(row["symbol"])
        if symbol in symbols:
            _fail()
        symbols.add(symbol)

        direction = row["direction"]
        trend = row["trend"]
        if direction not in _DIRECTIONS or trend not in _TRENDS:
            _fail()
        if type(row["bos"]) is not bool or type(row["choch"]) is not bool:
            _fail()
        volume_status = row["volume_v2_status"]
        if volume_status not in _VOLUME_STATUSES:
            _fail()

        golden_zone = _validate_golden_zone(row["golden_zone"], direction, trend)
        rows.append(
            {
                "symbol": symbol,
                "score": _finite_number(row["score"]),
                "direction": direction,
                "entry": _finite_number(row["entry"]),
                "stop_loss": _finite_number(row["stop_loss"]),
                "take_profit": _finite_number(row["take_profit"]),
                "reference_price": _finite_number(row["reference_price"]),
                "reference_candle_at": _normalize_timestamp(row["reference_candle_at"]),
                "golden_zone": golden_zone,
                "trend": trend,
                "bos": row["bos"],
                "choch": row["choch"],
                "volume_ratio": _finite_number(row["volume_ratio"]),
                "volume_v2_status": volume_status,
            }
        )
    return sorted(rows, key=lambda row: (-row["score"], row["symbol"]))


def _validate_golden_zone(value, direction: str, trend: str) -> dict[str, Any]:
    _require_mapping(value)
    _require_exact_keys(value, _GOLDEN_ZONE_KEYS)
    if value["direction"] != direction:
        _fail()
    if (direction == "BULLISH") != (trend == "UPTREND"):
        _fail()

    swing_low_index = _nonnegative_integer(value["swing_low_index"])
    swing_high_index = _nonnegative_integer(value["swing_high_index"])
    swing_low_at = _normalize_timestamp(value["swing_low_at"])
    swing_high_at = _normalize_timestamp(value["swing_high_at"])
    swing_low = _finite_number(value["swing_low"])
    swing_high = _finite_number(value["swing_high"])
    if swing_high <= swing_low:
        _fail()

    low_time = datetime.fromisoformat(swing_low_at)
    high_time = datetime.fromisoformat(swing_high_at)
    if direction == "BULLISH":
        if swing_low_index >= swing_high_index or low_time >= high_time:
            _fail()
    elif swing_high_index >= swing_low_index or high_time >= low_time:
        _fail()

    levels = _validate_golden_levels(value["levels"], swing_low, swing_high, direction)
    entry_zone = _validate_entry_zone(value["entry_zone"], levels)
    take_profit = _validate_target(value["take_profit"], -0.27, levels)
    stop_loss = _validate_target(value["stop_loss"], 1.0, levels)
    return {
        "direction": direction,
        "swing_low_index": swing_low_index,
        "swing_high_index": swing_high_index,
        "swing_low_at": swing_low_at,
        "swing_high_at": swing_high_at,
        "swing_low": swing_low,
        "swing_high": swing_high,
        "levels": levels,
        "entry_zone": entry_zone,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
    }


def _validate_golden_levels(value, swing_low: float, swing_high: float, direction: str):
    _require_mapping(value)
    _require_exact_keys(value, _GOLDEN_LEVEL_KEYS)
    price_range = swing_high - swing_low
    levels = {}
    for level in _FIBONACCI_LEVELS:
        key = str(level)
        actual = _finite_number(value[key])
        expected = (
            swing_high - (price_range * level)
            if direction == "BULLISH"
            else swing_low + (price_range * level)
        )
        if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-9):
            _fail()
        levels[key] = actual
    return levels


def _validate_entry_zone(value, levels):
    _require_mapping(value)
    _require_exact_keys(value, _ENTRY_ZONE_KEYS)
    level_from = _finite_number(value["level_from"])
    level_to = _finite_number(value["level_to"])
    price_low = _finite_number(value["price_low"])
    price_high = _finite_number(value["price_high"])
    if not math.isclose(level_from, 0.618) or not math.isclose(level_to, 0.786):
        _fail()
    expected_low = min(levels["0.618"], levels["0.786"])
    expected_high = max(levels["0.618"], levels["0.786"])
    if (
        price_low > price_high
        or not math.isclose(price_low, expected_low, rel_tol=1e-12, abs_tol=1e-9)
        or not math.isclose(price_high, expected_high, rel_tol=1e-12, abs_tol=1e-9)
    ):
        _fail()
    return {
        "level_from": level_from,
        "level_to": level_to,
        "price_low": price_low,
        "price_high": price_high,
    }


def _validate_target(value, expected_level: float, levels):
    _require_mapping(value)
    _require_exact_keys(value, _TARGET_KEYS)
    level = _finite_number(value["level"])
    price = _finite_number(value["price"])
    expected_price = levels[str(expected_level)]
    if not math.isclose(level, expected_level) or not math.isclose(
        price, expected_price, rel_tol=1e-12, abs_tol=1e-9
    ):
        _fail()
    return {"level": level, "price": price}


def _validate_recorded_open_interest(value, scanner_results):
    _require_mapping(value)
    expected_symbols = {row["symbol"] for row in scanner_results}
    if not value or set(value) != expected_symbols:
        _fail()
    normalized = {}
    for symbol in sorted(expected_symbols):
        metrics = value[symbol]
        _require_mapping(metrics)
        _require_exact_keys(metrics, _OPEN_INTEREST_KEYS)
        status = metrics["data_status"]
        if status not in _OI_STATUSES:
            _fail()
        current_oi = _finite_number(metrics["current_oi"])
        previous_oi = _finite_number(metrics["previous_oi"])
        oi_score = _finite_number(metrics["oi_score"])
        if current_oi <= 0 or previous_oi <= 0 or not 0 <= oi_score <= 100:
            _fail()
        normalized[symbol] = {
            "current_oi": current_oi,
            "previous_oi": previous_oi,
            "oi_change_pct": _finite_number(metrics["oi_change_pct"]),
            "oi_score": oi_score,
            "data_status": status,
        }
    return normalized


def _validate_validator_response(value, scanner_results):
    _require_mapping(value)
    _require_exact_keys(value, _VALIDATOR_RESPONSE_KEYS)
    content = _nonblank_string(value["content"])
    try:
        parsed = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        _fail()
    _require_mapping(parsed)
    _require_exact_keys(parsed, _VALIDATOR_CONTENT_KEYS)
    validations = parsed["validations"]
    if not isinstance(validations, list):
        _fail()

    expected_symbols = [row["symbol"] for row in scanner_results]
    validation_map = {}
    for validation in validations:
        _require_mapping(validation)
        _require_exact_keys(validation, _VALIDATION_KEYS)
        symbol = _nonblank_string(validation["symbol"])
        if symbol in validation_map:
            _fail()
        if validation["status"] not in _VALIDATION_STATUSES:
            _fail()
        if validation["false_breakout_risk"] not in _FALSE_BREAKOUT_RISKS:
            _fail()
        if validation["confluence"] not in _CONFLUENCE_VALUES:
            _fail()
        if validation["reason_code"] not in _REASON_CODES:
            _fail()
        validation_map[symbol] = {
            "symbol": symbol,
            "status": validation["status"],
            "false_breakout_risk": validation["false_breakout_risk"],
            "confluence": validation["confluence"],
            "reason_code": validation["reason_code"],
        }
    if set(validation_map) != set(expected_symbols):
        _fail()

    normalized = [validation_map[symbol] for symbol in expected_symbols]
    return {
        "content": json.dumps(
            {"validations": normalized}, sort_keys=True, separators=(",", ":")
        )
    }


def _validate_validator_usage(value):
    _require_mapping(value)
    _require_exact_keys(value, _VALIDATOR_USAGE_KEYS)
    normalized = {key: _nonnegative_integer(value[key]) for key in _VALIDATOR_USAGE_KEYS}
    if normalized["total_tokens"] != (
        normalized["prompt_tokens"] + normalized["completion_tokens"]
    ):
        _fail()
    return normalized


def _validate_pre_delivery_candles(value, scanner_results):
    _require_mapping(value)
    expected_symbols = {row["symbol"] for row in scanner_results}
    if set(value) != expected_symbols:
        _fail()

    candles = {}
    for symbol in sorted(expected_symbols):
        sequence = value[symbol]
        if not isinstance(sequence, list) or not sequence:
            _fail()
        normalized_rows = []
        previous_open_time = None
        for row in sequence:
            _require_mapping(row)
            _require_exact_keys(row, _CANDLE_KEYS)
            open_time = _normalize_timestamp(row["open_time"])
            parsed_open_time = datetime.fromisoformat(open_time)
            if previous_open_time is not None and parsed_open_time <= previous_open_time:
                _fail()
            previous_open_time = parsed_open_time
            open_price = _finite_number(row["open"])
            high = _finite_number(row["high"])
            low = _finite_number(row["low"])
            close = _finite_number(row["close"])
            volume = _finite_number(row["volume"])
            if volume < 0 or high < max(open_price, close, low) or low > min(
                open_price, close, high
            ):
                _fail()
            normalized_rows.append(
                {
                    "open_time": open_time,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
            )
        candles[symbol] = tuple(normalized_rows)
    return candles


def _validate_semantic_contract(value):
    _require_mapping(value)
    _require_exact_keys(value, _SEMANTIC_CONTRACT_KEYS)
    if (
        value["classification"] != "REPLAY"
        or value["boundary"] != "MASTER_ENGINE_RECORDED_INPUT"
    ):
        _fail()
    return {"classification": "REPLAY", "boundary": "MASTER_ENGINE_RECORDED_INPUT"}


def _normalize_source_commit(value: Any) -> str:
    if not isinstance(value, str) or not _COMMIT_PATTERN.fullmatch(value):
        _fail()
    return value.lower()


def _normalize_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value:
        _fail()
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        _fail()
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail()
    return parsed.isoformat()


def _nonblank_string(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail()
    return value.strip()


def _positive_integer(value: Any) -> int:
    if type(value) is not int or value <= 0:
        _fail()
    return value


def _nonnegative_integer(value: Any) -> int:
    if type(value) is not int or value < 0:
        _fail()
    return value


def _finite_number(value: Any) -> float:
    if type(value) not in {int, float} or not math.isfinite(value):
        _fail()
    return float(value)


def _require_mapping(value: Any) -> None:
    if not isinstance(value, Mapping):
        _fail()


def _require_exact_keys(value: Mapping[str, Any], required) -> None:
    if set(value) != set(required) or any(value[key] is None for key in required):
        _fail()


def _reject_prohibited_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str) and _normalize_key(key) in _PROHIBITED_KEYS:
                _fail()
            _reject_prohibited_keys(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_prohibited_keys(nested)


def _normalize_key(value: str) -> str:
    return value.casefold().replace("-", "_")


def _freeze(value: Any):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(nested) for key, nested in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(nested) for nested in value)
    return value


def _thaw(value: Any):
    if isinstance(value, Mapping):
        return {key: _thaw(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw(nested) for nested in value]
    return value


def _fail() -> None:
    raise ReplayBundleValidationError("Invalid replay bundle")
