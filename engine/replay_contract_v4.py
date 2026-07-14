"""Immutable, network-free validation for recorded Replay V4 bundles."""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping


REPLAY_BUNDLE_SCHEMA_VERSION = 1

_TOP_LEVEL_REQUIRED = frozenset(
    {
        "schema_version",
        "source_commit",
        "recorded_at",
        "fixed_execution_time",
        "execution_configuration",
        "scanner_results",
        "recorded_validator_response",
        "pre_delivery_closed_candles",
        "expected_semantic_contract",
    }
)
_TOP_LEVEL_OPTIONAL = frozenset({"recorded_validator_usage"})
_EXECUTION_CONFIGURATION_KEYS = frozenset({"timeframe", "lookback", "limit"})
_SCANNER_RESULT_KEYS = frozenset(
    {"symbol", "score", "direction", "entry", "stop_loss", "take_profit"}
)
_VALIDATOR_RESPONSE_KEYS = frozenset({"content", "decision"})
_VALIDATOR_USAGE_KEYS = frozenset(
    {"prompt_tokens", "completion_tokens", "total_tokens"}
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
        "quota_state_path",
        "worker_state_path",
        "production_output_path",
        "production_path",
        "output_path",
    }
)
_COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40}")


class ReplayBundleValidationError(ValueError):
    """Raised when a replay bundle is invalid or unsafe to use."""


@dataclass(frozen=True)
class ReplayBundleV4:
    schema_version: int
    source_commit: str
    recorded_at: str
    fixed_execution_time: str
    execution_configuration: Mapping[str, Any]
    scanner_results: tuple[Mapping[str, Any], ...]
    recorded_validator_response: Mapping[str, Any]
    recorded_validator_usage: Mapping[str, Any] | None
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
    """Validate an injected replay mapping and return an immutable contract."""
    _require_mapping(bundle)
    _reject_prohibited_keys(bundle)
    _require_exact_keys(bundle, _TOP_LEVEL_REQUIRED, _TOP_LEVEL_OPTIONAL)

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
    validator_response = _validate_validator_response(
        bundle["recorded_validator_response"]
    )
    validator_usage = _validate_validator_usage(
        bundle.get("recorded_validator_usage", _MISSING)
    )
    candles = _validate_pre_delivery_candles(
        bundle["pre_delivery_closed_candles"],
        scanner_results,
    )
    semantic_contract = _validate_semantic_contract(
        bundle["expected_semantic_contract"]
    )

    return ReplayBundleV4(
        schema_version=schema_version,
        source_commit=source_commit,
        recorded_at=recorded_at,
        fixed_execution_time=fixed_execution_time,
        execution_configuration=_freeze(execution_configuration),
        scanner_results=tuple(_freeze(row) for row in scanner_results),
        recorded_validator_response=_freeze(validator_response),
        recorded_validator_usage=(
            None if validator_usage is None else _freeze(validator_usage)
        ),
        pre_delivery_closed_candles=_freeze(candles),
        expected_semantic_contract=_freeze(semantic_contract),
    )


def canonicalize_replay_bundle_v4(bundle) -> bytes:
    """Return deterministic UTF-8 JSON bytes for validated semantic content."""
    validated = _as_validated_bundle(bundle)
    semantic_content = _semantic_content(validated)
    return json.dumps(
        semantic_content,
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
    digest = calculate_replay_bundle_hash_v4(bundle)
    return f"fixture-v4-{digest[:24]}"


def derive_replay_id_v4(bundle) -> str:
    """Derive a stable replay-run identity in a distinct hash domain."""
    digest = hashlib.sha256(
        b"replay-v4\x00" + canonicalize_replay_bundle_v4(bundle)
    ).hexdigest()
    return f"replay-v4-{digest[:24]}"


_MISSING = object()


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
        "recorded_validator_response": _thaw(bundle.recorded_validator_response),
        "recorded_validator_usage": _thaw(bundle.recorded_validator_usage),
        "pre_delivery_closed_candles": _thaw(bundle.pre_delivery_closed_candles),
        "expected_semantic_contract": _thaw(bundle.expected_semantic_contract),
    }


def _validate_execution_configuration(value) -> dict[str, Any]:
    _require_mapping(value)
    _require_exact_keys(value, _EXECUTION_CONFIGURATION_KEYS)

    timeframe = value["timeframe"]
    if not isinstance(timeframe, str) or not timeframe.strip():
        _fail()

    return {
        "timeframe": timeframe.strip(),
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

        symbol = row["symbol"]
        if not isinstance(symbol, str) or not symbol.strip():
            _fail()
        symbol = symbol.strip()
        if symbol in symbols:
            _fail()
        symbols.add(symbol)

        direction = row["direction"]
        if direction not in {"BULLISH", "BEARISH"}:
            _fail()

        rows.append(
            {
                "symbol": symbol,
                "score": _finite_number(row["score"]),
                "direction": direction,
                "entry": _finite_number(row["entry"]),
                "stop_loss": _finite_number(row["stop_loss"]),
                "take_profit": _finite_number(row["take_profit"]),
            }
        )

    return sorted(rows, key=lambda row: (-row["score"], row["symbol"]))


def _validate_validator_response(value) -> dict[str, str]:
    _require_mapping(value)
    _require_exact_keys(value, _VALIDATOR_RESPONSE_KEYS)
    content = _nonblank_string(value["content"])
    decision = _nonblank_string(value["decision"])
    return {"content": content, "decision": decision}


def _validate_validator_usage(value) -> dict[str, int] | None:
    if value is _MISSING:
        return None
    _require_mapping(value)
    _require_exact_keys(value, _VALIDATOR_USAGE_KEYS)
    prompt_tokens = _nonnegative_integer(value["prompt_tokens"])
    completion_tokens = _nonnegative_integer(value["completion_tokens"])
    total_tokens = _nonnegative_integer(value["total_tokens"])
    if total_tokens != prompt_tokens + completion_tokens:
        _fail()
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _validate_pre_delivery_candles(value, scanner_results) -> dict[str, tuple[dict[str, Any], ...]]:
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
            if (
                previous_open_time is not None
                and parsed_open_time <= previous_open_time
            ):
                _fail()
            previous_open_time = parsed_open_time

            open_price = _finite_number(row["open"])
            high = _finite_number(row["high"])
            low = _finite_number(row["low"])
            close = _finite_number(row["close"])
            volume = _finite_number(row["volume"])
            if volume < 0 or high < max(open_price, close, low) or low > min(
                open_price,
                close,
                high,
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


def _validate_semantic_contract(value) -> dict[str, str]:
    _require_mapping(value)
    _require_exact_keys(value, _SEMANTIC_CONTRACT_KEYS)
    if (
        value["classification"] != "REPLAY"
        or value["boundary"] != "MASTER_ENGINE_RECORDED_INPUT"
    ):
        _fail()
    return {
        "classification": "REPLAY",
        "boundary": "MASTER_ENGINE_RECORDED_INPUT",
    }


def _normalize_source_commit(value) -> str:
    if not isinstance(value, str) or not _COMMIT_PATTERN.fullmatch(value):
        _fail()
    return value.lower()


def _normalize_timestamp(value) -> str:
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


def _nonblank_string(value) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail()
    return value.strip()


def _positive_integer(value) -> int:
    if type(value) is not int or value <= 0:
        _fail()
    return value


def _nonnegative_integer(value) -> int:
    if type(value) is not int or value < 0:
        _fail()
    return value


def _finite_number(value) -> float:
    if type(value) not in {int, float} or not math.isfinite(value):
        _fail()
    return float(value)


def _require_mapping(value) -> None:
    if not isinstance(value, Mapping):
        _fail()


def _require_exact_keys(value: Mapping[str, Any], required, optional=frozenset()) -> None:
    keys = set(value)
    if not required <= keys or not keys <= required | optional:
        _fail()
    if any(value[key] is None for key in required):
        _fail()


def _reject_prohibited_keys(value) -> None:
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


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(nested) for key, nested in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(nested) for nested in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw(nested) for nested in value]
    return value


def _fail() -> None:
    raise ReplayBundleValidationError("Invalid replay bundle")
