"""Pure immutable evidence contracts for a planned mode scan execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from typing import Any, Final

from engine.mode_data_plan_v1 import (
    ModeAuditLineageV1,
    build_mode_audit_lineage,
)
from engine.mode_fetch_budget_cadence_v1 import (
    ModeOwnedCacheKeyV1,
    build_mode_owned_cache_key,
)
from engine.mode_profile_v1 import (
    ModeProfileV1,
    all_mode_profiles,
    get_mode_profile,
)
from engine.mode_scan_execution_plan_v1 import (
    CACHE_KEY_DYNAMIC_FIELD,
    CACHE_KEY_FIELDS,
    CANDLE_SUFFICIENCY_POLICY,
    DEVELOPING_CANDLE_POLICY,
    MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION,
    MODE_SCAN_EXECUTION_PLAN_SCHEMA_VERSION,
    MODE_SYMBOL_EXECUTION_PLAN_SCHEMA_VERSION,
    MODE_TIMEFRAME_FETCH_PLAN_SCHEMA_VERSION,
    ModeScanExecutionPlanV1,
    ModeSymbolExecutionPlanV1,
    ModeTimeframeFetchPlanV1,
)


MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION: Final = (
    "mode-scan-execution-evidence-policy-v1"
)
MODE_UTC_CANDLE_SCHEMA_VERSION: Final = "mode-utc-candle-v1"
MODE_TIMEFRAME_EXECUTION_EVIDENCE_SCHEMA_VERSION: Final = (
    "mode-timeframe-execution-evidence-v1"
)
MODE_OI_OBSERVATION_SCHEMA_VERSION: Final = "mode-oi-observation-v1"
MODE_OI_EXECUTION_EVIDENCE_SCHEMA_VERSION: Final = (
    "mode-oi-execution-evidence-v1"
)
MODE_TECHNICAL_EVALUATOR_PAYLOAD_SCHEMA_VERSION: Final = (
    "mode-technical-evaluator-payload-v1"
)
MODE_EXECUTION_CANDIDATE_ROW_SCHEMA_VERSION: Final = (
    "mode-execution-candidate-row-v1"
)
MODE_SYMBOL_EXECUTION_OUTCOME_SCHEMA_VERSION: Final = (
    "mode-symbol-execution-outcome-v1"
)
MODE_SCAN_EXECUTION_RESULT_SCHEMA_VERSION: Final = (
    "mode-scan-execution-result-v1"
)

OUTCOME_CANDIDATE: Final = "CANDIDATE"
OUTCOME_NO_CANDIDATE: Final = "NO_CANDIDATE"
OUTCOME_SKIPPED: Final = "SKIPPED"

REASON_CANDIDATE_ACCEPTED: Final = "CANDIDATE_ACCEPTED"
REASON_NO_CANDIDATE: Final = "NO_CANDIDATE"
REASON_CANDLE_BOUNDARY_EXCEPTION: Final = "CANDLE_BOUNDARY_EXCEPTION"
REASON_CANDLE_EVIDENCE_INVALID: Final = "CANDLE_EVIDENCE_INVALID"
REASON_OI_BOUNDARY_EXCEPTION: Final = "OI_BOUNDARY_EXCEPTION"
REASON_OI_EVIDENCE_INVALID: Final = "OI_EVIDENCE_INVALID"
REASON_EVALUATOR_EXCEPTION: Final = "EVALUATOR_EXCEPTION"
REASON_EVALUATOR_RESULT_INVALID: Final = "EVALUATOR_RESULT_INVALID"

_OUTCOME_KINDS: Final = frozenset(
    (OUTCOME_CANDIDATE, OUTCOME_NO_CANDIDATE, OUTCOME_SKIPPED)
)
_FAILURE_REASONS: Final = frozenset(
    (
        REASON_CANDLE_BOUNDARY_EXCEPTION,
        REASON_CANDLE_EVIDENCE_INVALID,
        REASON_OI_BOUNDARY_EXCEPTION,
        REASON_OI_EVIDENCE_INVALID,
        REASON_EVALUATOR_EXCEPTION,
        REASON_EVALUATOR_RESULT_INVALID,
    )
)
_CANDLE_FAILURE_REASONS: Final = frozenset(
    (
        REASON_CANDLE_BOUNDARY_EXCEPTION,
        REASON_CANDLE_EVIDENCE_INVALID,
    )
)
_OI_FAILURE_REASONS: Final = frozenset(
    (REASON_OI_BOUNDARY_EXCEPTION, REASON_OI_EVIDENCE_INVALID)
)
_EVALUATOR_FAILURE_REASONS: Final = frozenset(
    (REASON_EVALUATOR_EXCEPTION, REASON_EVALUATOR_RESULT_INVALID)
)

_TIMEFRAME_SECONDS: Final = {
    "1w": 604800,
    "1d": 86400,
    "4h": 14400,
    "1h": 3600,
    "15m": 900,
    "5m": 300,
    "3m": 180,
}
_CANONICAL_MODES: Final = tuple(
    profile.mode for profile in all_mode_profiles()
)
_UTC_TIMESTAMP: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
_SAFE_IDENTIFIER: Final = re.compile(r"[A-Za-z0-9._:+-]{1,128}")
_E2C1_IDENTIFIER: Final = re.compile(r"e2c1:[0-9a-f]{64}")

_TECHNICAL_PAYLOAD_KEYS: Final = frozenset(
    (
        "score",
        "trend",
        "bos",
        "choch",
        "reference_price",
        "reference_candle_at",
        "volume_ratio",
        "volume_v2_status",
        "golden_zone",
    )
)
_ADAPTER_IDENTITY_KEYS: Final = frozenset(
    (
        "schema_version",
        "policy_version",
        "candidate_id",
        "symbol",
        "mode",
        "mode_lineage_sha256",
        "payload_json",
        "payload_sha256",
        "pipeline_stage",
        "pipeline_rank",
    )
)


class ModeScanExecutionEvidenceValidationError(ValueError):
    """Sanitized failure for immutable mode-execution evidence."""


def _invalid() -> None:
    raise ModeScanExecutionEvidenceValidationError(
        "invalid mode scan execution evidence"
    ) from None


def _exact_constant(value: object, expected: str) -> str:
    if type(value) is not str or value != expected:
        _invalid()
    return value


def _text(
    value: object,
    *,
    maximum: int | None = None,
) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or (maximum is not None and len(value) > maximum)
    ):
        _invalid()
    return value


def _canonical_symbol(value: object) -> str:
    return _text(value, maximum=128)


def _safe_identifier(value: object) -> str:
    if (
        type(value) is not str
        or _SAFE_IDENTIFIER.fullmatch(value) is None
    ):
        _invalid()
    return value


def _sha256_hex(value: object) -> str:
    if (
        type(value) is not str
        or _SHA256_HEX.fullmatch(value) is None
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
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if type(value) is not int or value < minimum:
        _invalid()
    if maximum is not None and value > maximum:
        _invalid()
    return value


def _finite(
    value: object,
    *,
    minimum: int | float | None = None,
    strict_minimum: bool = False,
) -> int | float:
    if type(value) not in (int, float) or not math.isfinite(value):
        _invalid()
    if minimum is not None:
        if strict_minimum and value <= minimum:
            _invalid()
        if not strict_minimum and value < minimum:
            _invalid()
    if type(value) is float and value == 0.0:
        return 0.0
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


def _validate_json_value(
    value: object,
    *,
    prohibit_identity_keys: bool = False,
) -> None:
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        if not math.isfinite(value):
            _invalid()
        return
    if type(value) is list:
        for item in value:
            _validate_json_value(
                item,
                prohibit_identity_keys=prohibit_identity_keys,
            )
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _invalid()
            if prohibit_identity_keys and key in _ADAPTER_IDENTITY_KEYS:
                _invalid()
            _validate_json_value(
                item,
                prohibit_identity_keys=prohibit_identity_keys,
            )
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


def _canonical_dict_json(value: object) -> str:
    if type(value) is not dict:
        _invalid()
    return _canonical_json(value)


def _decoded_dict(value: object) -> dict[str, Any]:
    if type(value) is not str:
        _invalid()
    try:
        decoded = json.loads(value)
    except Exception:
        _invalid()
    if (
        type(decoded) is not dict
        or _canonical_dict_json(decoded) != value
    ):
        _invalid()
    return decoded


def _hash_json(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_mapping(value: dict[str, object]) -> str:
    return _hash_json(_canonical_dict_json(value))


def _hash_sequence(value: list[dict[str, object]]) -> str:
    return _hash_json(_canonical_json(value))


def _utc_datetime(value: object) -> datetime:
    if (
        type(value) is not str
        or len(value) != 20
        or _UTC_TIMESTAMP.fullmatch(value) is None
    ):
        _invalid()
    try:
        parsed = datetime.strptime(
            value,
            "%Y-%m-%dT%H:%M:%SZ",
        ).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        _invalid()
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _invalid()
    return parsed


def _utc_text(value: object) -> str:
    _utc_datetime(value)
    return value


def _timeframe(value: object) -> str:
    value = _text(value)
    if value not in _TIMEFRAME_SECONDS:
        _invalid()
    return value


def _aligned_open_time(value: object, timeframe: object) -> datetime:
    text = _utc_text(value)
    timeframe_value = _timeframe(timeframe)
    parsed = _utc_datetime(text)
    epoch = datetime(
        1970,
        1,
        5 if timeframe_value == "1w" else 1,
        tzinfo=timezone.utc,
    )
    elapsed = int((parsed - epoch).total_seconds())
    if elapsed % _TIMEFRAME_SECONDS[timeframe_value] != 0:
        _invalid()
    return parsed


def _canonical_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _copy_timeframe_plan(
    value: object,
) -> ModeTimeframeFetchPlanV1:
    if type(value) is not ModeTimeframeFetchPlanV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        mapping["cache_key_fields"] = tuple(
            mapping["cache_key_fields"]
        )
        return ModeTimeframeFetchPlanV1(**mapping)
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


def _copy_symbol_plan(
    value: object,
) -> ModeSymbolExecutionPlanV1:
    if type(value) is not ModeSymbolExecutionPlanV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        fetches = mapping.get("candle_fetches")
        if type(fetches) is not list:
            _invalid()
        mapping["candle_fetches"] = tuple(
            ModeTimeframeFetchPlanV1(
                **{
                    **item,
                    "cache_key_fields": tuple(
                        item["cache_key_fields"]
                    ),
                }
            )
            for item in fetches
            if type(item) is dict
        )
        if len(mapping["candle_fetches"]) != len(fetches):
            _invalid()
        return ModeSymbolExecutionPlanV1(**mapping)
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


def _copy_plan(value: object) -> ModeScanExecutionPlanV1:
    if type(value) is not ModeScanExecutionPlanV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        symbol_values = mapping.get("full_evaluation_symbols")
        if type(symbol_values) is not list:
            _invalid()
        symbols = []
        for item in symbol_values:
            if type(item) is not dict:
                _invalid()
            fetch_values = item.get("candle_fetches")
            if type(fetch_values) is not list:
                _invalid()
            fetches = tuple(
                ModeTimeframeFetchPlanV1(
                    **{
                        **fetch,
                        "cache_key_fields": tuple(
                            fetch["cache_key_fields"]
                        ),
                    }
                )
                for fetch in fetch_values
                if type(fetch) is dict
            )
            if len(fetches) != len(fetch_values):
                _invalid()
            symbols.append(
                ModeSymbolExecutionPlanV1(
                    **{
                        **item,
                        "candle_fetches": fetches,
                    }
                )
            )
        mapping["discovery_symbols"] = tuple(
            mapping["discovery_symbols"]
        )
        mapping["full_evaluation_symbols"] = tuple(symbols)
        mapping["cache_key_fields"] = tuple(
            mapping["cache_key_fields"]
        )
        return ModeScanExecutionPlanV1(**mapping)
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeUtcCandleV1:
    schema_version: str
    timeframe: str
    open_time: str
    close_time: str
    open: int | float
    high: int | float
    low: int | float
    close: int | float
    volume: int | float

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_UTC_CANDLE_SCHEMA_VERSION,
            )
            timeframe = _timeframe(self.timeframe)
            opened = _aligned_open_time(self.open_time, timeframe)
            closed = _utc_datetime(self.close_time)
            if closed != opened + timedelta(
                seconds=_TIMEFRAME_SECONDS[timeframe]
            ):
                _invalid()
            open_value = _finite(
                self.open,
                minimum=0,
                strict_minimum=True,
            )
            high_value = _finite(
                self.high,
                minimum=0,
                strict_minimum=True,
            )
            low_value = _finite(
                self.low,
                minimum=0,
                strict_minimum=True,
            )
            close_value = _finite(
                self.close,
                minimum=0,
                strict_minimum=True,
            )
            volume_value = _finite(self.volume, minimum=0)
            if (
                high_value < max(
                    open_value,
                    close_value,
                    low_value,
                )
                or low_value > min(
                    open_value,
                    close_value,
                    high_value,
                )
            ):
                _invalid()
            object.__setattr__(self, "open", open_value)
            object.__setattr__(self, "high", high_value)
            object.__setattr__(self, "low", low_value)
            object.__setattr__(self, "close", close_value)
            object.__setattr__(self, "volume", volume_value)
        except ModeScanExecutionEvidenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "timeframe": self.timeframe,
            "open_time": self.open_time,
            "close_time": self.close_time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


def _copy_candle(value: object) -> ModeUtcCandleV1:
    if type(value) is not ModeUtcCandleV1:
        _invalid()
    try:
        return ModeUtcCandleV1(**value.to_mapping())
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeTimeframeExecutionEvidenceV1:
    schema_version: str
    policy_version: str
    mode: str
    mode_lineage_sha256: str
    canonical_symbol: str
    timeframe: str
    role: str
    optional_context: bool
    observed_at: str
    raw_fetch_limit: int
    closed_candle_limit: int
    raw_candles: tuple[ModeUtcCandleV1, ...]
    developing_candle_dropped: bool
    closed_candle_count: int
    closed_candles_sha256: str
    closed_candle_close_at: str
    cache_key_json: str
    cache_key_sha256: str
    evidence_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_TIMEFRAME_EXECUTION_EVIDENCE_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            )
            mode = _canonical_mode(self.mode)
            lineage = _expected_lineage(mode)
            if _sha256_hex(self.mode_lineage_sha256) != lineage:
                _invalid()
            symbol = _canonical_symbol(self.canonical_symbol)
            observed = _utc_datetime(self.observed_at)
            timeframe_plan = ModeTimeframeFetchPlanV1(
                schema_version=MODE_TIMEFRAME_FETCH_PLAN_SCHEMA_VERSION,
                policy_version=MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION,
                mode=mode,
                mode_lineage_sha256=lineage,
                canonical_symbol=symbol,
                timeframe=self.timeframe,
                role=self.role,
                optional_context=self.optional_context,
                closed_candle_limit=self.closed_candle_limit,
                raw_fetch_limit=self.raw_fetch_limit,
                developing_candle_policy=DEVELOPING_CANDLE_POLICY,
                candle_sufficiency_policy=CANDLE_SUFFICIENCY_POLICY,
                cache_key_fields=CACHE_KEY_FIELDS,
                cache_key_dynamic_field=CACHE_KEY_DYNAMIC_FIELD,
            )
            raw_limit = _integer(
                self.raw_fetch_limit,
                minimum=1,
            )
            closed_limit = _integer(
                self.closed_candle_limit,
                minimum=1,
            )
            if raw_limit != closed_limit + 1:
                _invalid()
            if type(self.raw_candles) not in (list, tuple):
                _invalid()
            candles = tuple(
                _copy_candle(item)
                for item in self.raw_candles
            )
            object.__setattr__(self, "raw_candles", candles)
            if len(candles) != raw_limit:
                _invalid()
            if any(
                candle.timeframe != timeframe_plan.timeframe
                for candle in candles
            ):
                _invalid()
            open_times = tuple(
                _utc_datetime(candle.open_time)
                for candle in candles
            )
            close_times = tuple(
                _utc_datetime(candle.close_time)
                for candle in candles
            )
            if (
                len(set(open_times)) != len(open_times)
                or len(set(close_times)) != len(close_times)
            ):
                _invalid()
            for index in range(1, len(candles)):
                if (
                    open_times[index] <= open_times[index - 1]
                    or open_times[index] != close_times[index - 1]
                ):
                    _invalid()
            developing = candles[-1]
            developing_open = open_times[-1]
            developing_close = close_times[-1]
            if not (
                developing_open <= observed < developing_close
            ):
                _invalid()
            if _boolean(self.developing_candle_dropped) is not True:
                _invalid()
            closed_candles = candles[:-1]
            if (
                len(closed_candles) != closed_limit
                or _integer(self.closed_candle_count, minimum=1)
                != closed_limit
                or close_times[-2] != developing_open
            ):
                _invalid()
            close_at = _utc_text(self.closed_candle_close_at)
            if close_at != closed_candles[-1].close_time:
                _invalid()
            closed_hash = _hash_sequence(
                [item.to_mapping() for item in closed_candles]
            )
            if (
                _sha256_hex(self.closed_candles_sha256)
                != closed_hash
            ):
                _invalid()
            cache_mapping = _decoded_dict(self.cache_key_json)
            cache_key = ModeOwnedCacheKeyV1(**cache_mapping)
            if (
                cache_key.mode != mode
                or cache_key.canonical_symbol != symbol
                or cache_key.timeframe != timeframe_plan.timeframe
                or cache_key.closed_candle_close_at != close_at
                or _sha256_hex(self.cache_key_sha256)
                != cache_key.cache_key_sha256
            ):
                _invalid()
            if (
                _sha256_hex(self.evidence_sha256)
                != _hash_mapping(self._content_mapping())
            ):
                _invalid()
        except ModeScanExecutionEvidenceValidationError:
            raise
        except Exception:
            _invalid()

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "canonical_symbol": self.canonical_symbol,
            "timeframe": self.timeframe,
            "role": self.role,
            "optional_context": self.optional_context,
            "observed_at": self.observed_at,
            "raw_fetch_limit": self.raw_fetch_limit,
            "closed_candle_limit": self.closed_candle_limit,
            "raw_candles": [
                candle.to_mapping() for candle in self.raw_candles
            ],
            "developing_candle_dropped":
                self.developing_candle_dropped,
            "closed_candle_count": self.closed_candle_count,
            "closed_candles_sha256": self.closed_candles_sha256,
            "closed_candle_close_at": self.closed_candle_close_at,
            "cache_key_json": self.cache_key_json,
            "cache_key_sha256": self.cache_key_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["evidence_sha256"] = self.evidence_sha256
        return mapping


@dataclass(frozen=True, slots=True)
class ModeOiObservationV1:
    schema_version: str
    close_time: str
    open_interest: int | float

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_OI_OBSERVATION_SCHEMA_VERSION,
            )
            closed = _utc_datetime(self.close_time)
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            if int((closed - epoch).total_seconds()) % 300 != 0:
                _invalid()
            object.__setattr__(
                self,
                "open_interest",
                _finite(self.open_interest, minimum=0),
            )
        except ModeScanExecutionEvidenceValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "close_time": self.close_time,
            "open_interest": self.open_interest,
        }


def _copy_oi_observation(value: object) -> ModeOiObservationV1:
    if type(value) is not ModeOiObservationV1:
        _invalid()
    try:
        return ModeOiObservationV1(**value.to_mapping())
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeOiExecutionEvidenceV1:
    schema_version: str
    policy_version: str
    mode: str
    mode_lineage_sha256: str
    canonical_symbol: str
    observed_at: str
    period: str
    request_invocation_count: int
    observations: tuple[ModeOiObservationV1, ...]
    observation_count: int
    newest_close_at: str
    newest_age_seconds: int
    observations_sha256: str
    evidence_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_OI_EXECUTION_EVIDENCE_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            )
            mode = _canonical_mode(self.mode)
            lineage = _expected_lineage(mode)
            if _sha256_hex(self.mode_lineage_sha256) != lineage:
                _invalid()
            _canonical_symbol(self.canonical_symbol)
            observed = _utc_datetime(self.observed_at)
            _exact_constant(self.period, "5m")
            if (
                type(self.request_invocation_count) is not int
                or self.request_invocation_count != 1
            ):
                _invalid()
            if type(self.observations) not in (list, tuple):
                _invalid()
            observations = tuple(
                _copy_oi_observation(item)
                for item in self.observations
            )
            object.__setattr__(
                self,
                "observations",
                observations,
            )
            count = _integer(
                self.observation_count,
                minimum=2,
                maximum=1000,
            )
            if len(observations) != count:
                _invalid()
            times = tuple(
                _utc_datetime(item.close_time)
                for item in observations
            )
            if len(set(times)) != len(times):
                _invalid()
            for index in range(1, len(times)):
                if times[index] - times[index - 1] != timedelta(
                    seconds=300
                ):
                    _invalid()
            newest = _utc_text(self.newest_close_at)
            if newest != observations[-1].close_time:
                _invalid()
            age = int((observed - times[-1]).total_seconds())
            if (
                times[-1] > observed
                or _integer(
                    self.newest_age_seconds,
                    minimum=0,
                    maximum=300,
                )
                != age
            ):
                _invalid()
            observations_hash = _hash_sequence(
                [item.to_mapping() for item in observations]
            )
            if (
                _sha256_hex(self.observations_sha256)
                != observations_hash
            ):
                _invalid()
            if (
                _sha256_hex(self.evidence_sha256)
                != _hash_mapping(self._content_mapping())
            ):
                _invalid()
        except ModeScanExecutionEvidenceValidationError:
            raise
        except Exception:
            _invalid()

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "canonical_symbol": self.canonical_symbol,
            "observed_at": self.observed_at,
            "period": self.period,
            "request_invocation_count":
                self.request_invocation_count,
            "observations": [
                item.to_mapping() for item in self.observations
            ],
            "observation_count": self.observation_count,
            "newest_close_at": self.newest_close_at,
            "newest_age_seconds": self.newest_age_seconds,
            "observations_sha256": self.observations_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["evidence_sha256"] = self.evidence_sha256
        return mapping


def _validated_technical_payload(
    value: object,
    *,
    trigger_candle_close_at: object,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _TECHNICAL_PAYLOAD_KEYS:
        _invalid()
    trigger = _utc_text(trigger_candle_close_at)
    _finite(value["score"], minimum=0)
    if value["score"] > 100:
        _invalid()
    _text(value["trend"], maximum=64)
    _boolean(value["bos"])
    _boolean(value["choch"])
    _finite(
        value["reference_price"],
        minimum=0,
        strict_minimum=True,
    )
    reference_at = _utc_text(value["reference_candle_at"])
    if reference_at != trigger:
        _invalid()
    if value["volume_ratio"] is not None:
        _finite(value["volume_ratio"], minimum=0)
    if value["volume_v2_status"] is not None:
        _text(value["volume_v2_status"], maximum=64)
    golden_zone = value["golden_zone"]
    if golden_zone is not None:
        if type(golden_zone) is not dict:
            _invalid()
        _validate_json_value(
            golden_zone,
            prohibit_identity_keys=True,
        )
    _validate_json_value(value)
    return value


@dataclass(frozen=True, slots=True)
class ModeTechnicalEvaluatorPayloadV1:
    schema_version: str
    policy_version: str
    trigger_candle_close_at: str
    payload_json: str
    payload_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_TECHNICAL_EVALUATOR_PAYLOAD_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            )
            trigger = _utc_text(self.trigger_candle_close_at)
            payload = _decoded_dict(self.payload_json)
            _validated_technical_payload(
                payload,
                trigger_candle_close_at=trigger,
            )
            if (
                _sha256_hex(self.payload_sha256)
                != _hash_json(self.payload_json)
            ):
                _invalid()
        except ModeScanExecutionEvidenceValidationError:
            raise
        except Exception:
            _invalid()

    def payload_copy(self) -> dict[str, Any]:
        return _decoded_dict(self.payload_json)

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "trigger_candle_close_at":
                self.trigger_candle_close_at,
            "payload_json": self.payload_json,
            "payload_sha256": self.payload_sha256,
        }


def _copy_evaluator_payload(
    value: object,
) -> ModeTechnicalEvaluatorPayloadV1:
    if type(value) is not ModeTechnicalEvaluatorPayloadV1:
        _invalid()
    try:
        return ModeTechnicalEvaluatorPayloadV1(**value.to_mapping())
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


def _expected_candidate_id(
    *,
    plan_sha256: object,
    mode: object,
    mode_lineage_sha256: object,
    canonical_symbol: object,
    reference_candle_at: object,
    payload_sha256: object,
) -> str:
    plan_hash = _sha256_hex(plan_sha256)
    canonical_mode = _canonical_mode(mode)
    lineage = _sha256_hex(mode_lineage_sha256)
    if lineage != _expected_lineage(canonical_mode):
        _invalid()
    symbol = _canonical_symbol(canonical_symbol)
    reference_at = _utc_text(reference_candle_at)
    payload_hash = _sha256_hex(payload_sha256)
    digest = _hash_mapping(
        {
            "executor_policy_version":
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            "plan_sha256": plan_hash,
            "mode": canonical_mode,
            "mode_lineage_sha256": lineage,
            "canonical_symbol": symbol,
            "reference_candle_at": reference_at,
            "payload_sha256": payload_hash,
        }
    )
    return f"e2c1:{digest}"


@dataclass(frozen=True, slots=True)
class ModeExecutionCandidateRowV1:
    schema_version: str
    policy_version: str
    plan_sha256: str
    candidate_id: str
    mode: str
    symbol: str
    mode_lineage_sha256: str
    reference_candle_at: str
    payload_json: str
    payload_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_EXECUTION_CANDIDATE_ROW_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            )
            plan_hash = _sha256_hex(self.plan_sha256)
            mode = _canonical_mode(self.mode)
            lineage = _expected_lineage(mode)
            if _sha256_hex(self.mode_lineage_sha256) != lineage:
                _invalid()
            symbol = _canonical_symbol(self.symbol)
            reference_at = _utc_text(self.reference_candle_at)
            payload = ModeTechnicalEvaluatorPayloadV1(
                schema_version=(
                    MODE_TECHNICAL_EVALUATOR_PAYLOAD_SCHEMA_VERSION
                ),
                policy_version=(
                    MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION
                ),
                trigger_candle_close_at=reference_at,
                payload_json=self.payload_json,
                payload_sha256=self.payload_sha256,
            )
            expected = _expected_candidate_id(
                plan_sha256=plan_hash,
                mode=mode,
                mode_lineage_sha256=lineage,
                canonical_symbol=symbol,
                reference_candle_at=reference_at,
                payload_sha256=payload.payload_sha256,
            )
            if (
                type(self.candidate_id) is not str
                or _E2C1_IDENTIFIER.fullmatch(self.candidate_id) is None
                or _safe_identifier(self.candidate_id)
                != expected
            ):
                _invalid()
        except ModeScanExecutionEvidenceValidationError:
            raise
        except Exception:
            _invalid()

    def payload_copy(self) -> dict[str, Any]:
        return _decoded_dict(self.payload_json)

    def to_scanner_row(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "mode": self.mode,
            "symbol": self.symbol,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "payload": self.payload_copy(),
        }

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "plan_sha256": self.plan_sha256,
            "candidate_id": self.candidate_id,
            "mode": self.mode,
            "symbol": self.symbol,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "reference_candle_at": self.reference_candle_at,
            "payload_json": self.payload_json,
            "payload_sha256": self.payload_sha256,
        }


def _copy_candidate_row(
    value: object,
) -> ModeExecutionCandidateRowV1:
    if type(value) is not ModeExecutionCandidateRowV1:
        _invalid()
    try:
        return ModeExecutionCandidateRowV1(**value.to_mapping())
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeSymbolExecutionOutcomeV1:
    schema_version: str
    policy_version: str
    mode: str
    mode_lineage_sha256: str
    canonical_symbol: str
    full_evaluation_rank: int
    outcome_kind: str
    reason_code: str
    timeframe_evidence_sha256s: tuple[str, ...]
    oi_evidence_sha256: str | None
    evaluator_payload_sha256: str | None
    candidate_row: ModeExecutionCandidateRowV1 | None

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_SYMBOL_EXECUTION_OUTCOME_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            )
            mode = _canonical_mode(self.mode)
            lineage = _expected_lineage(mode)
            if _sha256_hex(self.mode_lineage_sha256) != lineage:
                _invalid()
            symbol = _canonical_symbol(self.canonical_symbol)
            _integer(self.full_evaluation_rank, minimum=1)
            kind = _text(self.outcome_kind)
            reason = _text(self.reason_code)
            if kind not in _OUTCOME_KINDS:
                _invalid()
            if type(self.timeframe_evidence_sha256s) not in (
                list,
                tuple,
            ):
                _invalid()
            timeframe_hashes = tuple(
                _sha256_hex(item)
                for item in self.timeframe_evidence_sha256s
            )
            object.__setattr__(
                self,
                "timeframe_evidence_sha256s",
                timeframe_hashes,
            )
            if len(set(timeframe_hashes)) != len(timeframe_hashes):
                _invalid()
            oi_hash = (
                None
                if self.oi_evidence_sha256 is None
                else _sha256_hex(self.oi_evidence_sha256)
            )
            evaluator_hash = (
                None
                if self.evaluator_payload_sha256 is None
                else _sha256_hex(self.evaluator_payload_sha256)
            )
            candidate = (
                None
                if self.candidate_row is None
                else _copy_candidate_row(self.candidate_row)
            )
            object.__setattr__(self, "candidate_row", candidate)
            if kind == OUTCOME_CANDIDATE:
                if (
                    reason != REASON_CANDIDATE_ACCEPTED
                    or not timeframe_hashes
                    or oi_hash is None
                    or evaluator_hash is None
                    or candidate is None
                    or candidate.mode != mode
                    or candidate.mode_lineage_sha256 != lineage
                    or candidate.symbol != symbol
                    or candidate.payload_sha256 != evaluator_hash
                ):
                    _invalid()
            elif kind == OUTCOME_NO_CANDIDATE:
                if (
                    reason != REASON_NO_CANDIDATE
                    or not timeframe_hashes
                    or oi_hash is None
                    or evaluator_hash is not None
                    or candidate is not None
                ):
                    _invalid()
            else:
                if (
                    reason not in _FAILURE_REASONS
                    or evaluator_hash is not None
                    or candidate is not None
                ):
                    _invalid()
                if (
                    reason in _CANDLE_FAILURE_REASONS
                    and oi_hash is not None
                ):
                    _invalid()
                if (
                    reason in _OI_FAILURE_REASONS
                    and not timeframe_hashes
                ):
                    _invalid()
                if (
                    reason in _EVALUATOR_FAILURE_REASONS
                    and (not timeframe_hashes or oi_hash is None)
                ):
                    _invalid()
        except ModeScanExecutionEvidenceValidationError:
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
            "full_evaluation_rank": self.full_evaluation_rank,
            "outcome_kind": self.outcome_kind,
            "reason_code": self.reason_code,
            "timeframe_evidence_sha256s": list(
                self.timeframe_evidence_sha256s
            ),
            "oi_evidence_sha256": self.oi_evidence_sha256,
            "evaluator_payload_sha256":
                self.evaluator_payload_sha256,
            "candidate_row": (
                None
                if self.candidate_row is None
                else self.candidate_row.to_mapping()
            ),
        }


def _copy_outcome(
    value: object,
) -> ModeSymbolExecutionOutcomeV1:
    if type(value) is not ModeSymbolExecutionOutcomeV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        candidate = mapping["candidate_row"]
        mapping["timeframe_evidence_sha256s"] = tuple(
            mapping["timeframe_evidence_sha256s"]
        )
        mapping["candidate_row"] = (
            None
            if candidate is None
            else ModeExecutionCandidateRowV1(**candidate)
        )
        return ModeSymbolExecutionOutcomeV1(**mapping)
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeScanExecutionResultV1:
    schema_version: str
    policy_version: str
    plan_sha256: str
    mode: str
    mode_lineage_sha256: str
    observed_at: str
    planned_symbol_order: tuple[str, ...]
    planned_timeframe_counts: tuple[int, ...]
    planned_candle_call_count: int
    planned_oi_call_count: int
    planned_evaluator_invocation_count: int
    planned_executor_request_count: int
    planned_executor_ip_weight: int
    actual_candle_call_count: int
    actual_oi_call_count: int
    actual_evaluator_invocation_count: int
    actual_executor_request_count: int
    actual_executor_ip_weight: int
    candidate_count: int
    no_candidate_count: int
    skipped_count: int
    retry_count: int
    outcomes: tuple[ModeSymbolExecutionOutcomeV1, ...]
    candidates: tuple[ModeExecutionCandidateRowV1, ...]
    execution_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_SCAN_EXECUTION_RESULT_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            )
            plan_hash = _sha256_hex(self.plan_sha256)
            mode = _canonical_mode(self.mode)
            lineage = _expected_lineage(mode)
            if _sha256_hex(self.mode_lineage_sha256) != lineage:
                _invalid()
            _utc_text(self.observed_at)
            if type(self.planned_symbol_order) not in (list, tuple):
                _invalid()
            symbols = tuple(
                _canonical_symbol(item)
                for item in self.planned_symbol_order
            )
            object.__setattr__(
                self,
                "planned_symbol_order",
                symbols,
            )
            if not symbols or len(set(symbols)) != len(symbols):
                _invalid()
            if type(self.planned_timeframe_counts) not in (
                list,
                tuple,
            ):
                _invalid()
            timeframe_counts = tuple(
                _integer(item, minimum=1)
                for item in self.planned_timeframe_counts
            )
            object.__setattr__(
                self,
                "planned_timeframe_counts",
                timeframe_counts,
            )
            if len(timeframe_counts) != len(symbols):
                _invalid()
            planned_candles = _integer(
                self.planned_candle_call_count,
                minimum=1,
            )
            planned_oi = _integer(
                self.planned_oi_call_count,
                minimum=1,
            )
            planned_evaluator = _integer(
                self.planned_evaluator_invocation_count,
                minimum=1,
            )
            planned_requests = _integer(
                self.planned_executor_request_count,
                minimum=1,
            )
            planned_weight = _integer(
                self.planned_executor_ip_weight,
                minimum=0,
            )
            if (
                planned_candles != sum(timeframe_counts)
                or planned_oi != len(symbols)
                or planned_evaluator != len(symbols)
                or planned_requests != planned_candles + planned_oi
            ):
                _invalid()
            actual_candles = _integer(
                self.actual_candle_call_count,
                minimum=0,
            )
            actual_oi = _integer(
                self.actual_oi_call_count,
                minimum=0,
            )
            actual_evaluator = _integer(
                self.actual_evaluator_invocation_count,
                minimum=0,
            )
            actual_requests = _integer(
                self.actual_executor_request_count,
                minimum=0,
            )
            actual_weight = _integer(
                self.actual_executor_ip_weight,
                minimum=0,
            )
            if (
                actual_requests != actual_candles + actual_oi
                or actual_candles > planned_candles
                or actual_oi > planned_oi
                or actual_evaluator > planned_evaluator
                or actual_requests > planned_requests
                or actual_weight > planned_weight
            ):
                _invalid()
            if type(self.retry_count) is not int or self.retry_count != 0:
                _invalid()
            if type(self.outcomes) not in (list, tuple):
                _invalid()
            outcomes = tuple(
                _copy_outcome(item) for item in self.outcomes
            )
            object.__setattr__(self, "outcomes", outcomes)
            if len(outcomes) != len(symbols):
                _invalid()
            for rank, (symbol, outcome) in enumerate(
                zip(symbols, outcomes, strict=True),
                start=1,
            ):
                if (
                    outcome.mode != mode
                    or outcome.mode_lineage_sha256 != lineage
                    or outcome.canonical_symbol != symbol
                    or outcome.full_evaluation_rank != rank
                ):
                    _invalid()
            candidate_count = sum(
                item.outcome_kind == OUTCOME_CANDIDATE
                for item in outcomes
            )
            no_candidate_count = sum(
                item.outcome_kind == OUTCOME_NO_CANDIDATE
                for item in outcomes
            )
            skipped_count = sum(
                item.outcome_kind == OUTCOME_SKIPPED
                for item in outcomes
            )
            if (
                _integer(self.candidate_count, minimum=0)
                != candidate_count
                or _integer(self.no_candidate_count, minimum=0)
                != no_candidate_count
                or _integer(self.skipped_count, minimum=0)
                != skipped_count
                or candidate_count + no_candidate_count + skipped_count
                != len(outcomes)
            ):
                _invalid()
            expected_evaluator_calls = sum(
                item.outcome_kind
                in (OUTCOME_CANDIDATE, OUTCOME_NO_CANDIDATE)
                or item.reason_code in _EVALUATOR_FAILURE_REASONS
                for item in outcomes
            )
            expected_oi_calls = sum(
                item.reason_code not in _CANDLE_FAILURE_REASONS
                for item in outcomes
            )
            if (
                actual_evaluator != expected_evaluator_calls
                or actual_oi != expected_oi_calls
            ):
                _invalid()
            if type(self.candidates) not in (list, tuple):
                _invalid()
            candidates = tuple(
                _copy_candidate_row(item)
                for item in self.candidates
            )
            object.__setattr__(self, "candidates", candidates)
            expected_candidates = tuple(
                item.candidate_row
                for item in outcomes
                if item.outcome_kind == OUTCOME_CANDIDATE
            )
            if (
                len(candidates) != candidate_count
                or tuple(
                    item.to_mapping() for item in candidates
                )
                != tuple(
                    item.to_mapping()
                    for item in expected_candidates
                    if item is not None
                )
            ):
                _invalid()
            candidate_ids: set[str] = set()
            candidate_symbols: set[str] = set()
            for candidate in candidates:
                if (
                    candidate.plan_sha256 != plan_hash
                    or candidate.mode != mode
                    or candidate.mode_lineage_sha256 != lineage
                    or candidate.candidate_id in candidate_ids
                    or candidate.symbol in candidate_symbols
                ):
                    _invalid()
                candidate_ids.add(candidate.candidate_id)
                candidate_symbols.add(candidate.symbol)
            if (
                _sha256_hex(self.execution_sha256)
                != _hash_mapping(self._content_mapping())
            ):
                _invalid()
        except ModeScanExecutionEvidenceValidationError:
            raise
        except Exception:
            _invalid()

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "plan_sha256": self.plan_sha256,
            "mode": self.mode,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "observed_at": self.observed_at,
            "planned_symbol_order": list(self.planned_symbol_order),
            "planned_timeframe_counts": list(
                self.planned_timeframe_counts
            ),
            "planned_candle_call_count":
                self.planned_candle_call_count,
            "planned_oi_call_count": self.planned_oi_call_count,
            "planned_evaluator_invocation_count":
                self.planned_evaluator_invocation_count,
            "planned_executor_request_count":
                self.planned_executor_request_count,
            "planned_executor_ip_weight":
                self.planned_executor_ip_weight,
            "actual_candle_call_count":
                self.actual_candle_call_count,
            "actual_oi_call_count": self.actual_oi_call_count,
            "actual_evaluator_invocation_count":
                self.actual_evaluator_invocation_count,
            "actual_executor_request_count":
                self.actual_executor_request_count,
            "actual_executor_ip_weight":
                self.actual_executor_ip_weight,
            "candidate_count": self.candidate_count,
            "no_candidate_count": self.no_candidate_count,
            "skipped_count": self.skipped_count,
            "retry_count": self.retry_count,
            "outcomes": [
                item.to_mapping() for item in self.outcomes
            ],
            "candidates": [
                item.to_mapping() for item in self.candidates
            ],
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["execution_sha256"] = self.execution_sha256
        return mapping


def build_mode_timeframe_execution_evidence(
    *,
    timeframe_plan: object,
    observed_at: object,
    raw_candles: object,
) -> ModeTimeframeExecutionEvidenceV1:
    try:
        plan = _copy_timeframe_plan(timeframe_plan)
        observed = _utc_text(observed_at)
        if type(raw_candles) not in (list, tuple):
            _invalid()
        candles = tuple(_copy_candle(item) for item in raw_candles)
        if len(candles) != plan.raw_fetch_limit:
            _invalid()
        closed = candles[:-1]
        closed_hash = _hash_sequence(
            [item.to_mapping() for item in closed]
        )
        close_at = closed[-1].close_time
        cache_key = build_mode_owned_cache_key(
            mode=plan.mode,
            canonical_symbol=plan.canonical_symbol,
            timeframe=plan.timeframe,
            closed_candle_close_at=close_at,
        )
        if type(cache_key) is not ModeOwnedCacheKeyV1:
            _invalid()
        cache_json = _canonical_dict_json(cache_key.to_mapping())
        content: dict[str, object] = {
            "schema_version":
                MODE_TIMEFRAME_EXECUTION_EVIDENCE_SCHEMA_VERSION,
            "policy_version":
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            "mode": plan.mode,
            "mode_lineage_sha256": plan.mode_lineage_sha256,
            "canonical_symbol": plan.canonical_symbol,
            "timeframe": plan.timeframe,
            "role": plan.role,
            "optional_context": plan.optional_context,
            "observed_at": observed,
            "raw_fetch_limit": plan.raw_fetch_limit,
            "closed_candle_limit": plan.closed_candle_limit,
            "raw_candles": [
                item.to_mapping() for item in candles
            ],
            "developing_candle_dropped": True,
            "closed_candle_count": len(closed),
            "closed_candles_sha256": closed_hash,
            "closed_candle_close_at": close_at,
            "cache_key_json": cache_json,
            "cache_key_sha256": cache_key.cache_key_sha256,
        }
        return ModeTimeframeExecutionEvidenceV1(
            **{
                **content,
                "raw_candles": candles,
                "evidence_sha256": _hash_mapping(content),
            }
        )
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


def build_mode_oi_execution_evidence(
    *,
    mode: object,
    mode_lineage_sha256: object,
    canonical_symbol: object,
    observed_at: object,
    observations: object,
    request_invocation_count: object,
) -> ModeOiExecutionEvidenceV1:
    try:
        canonical_mode = _canonical_mode(mode)
        lineage = _sha256_hex(mode_lineage_sha256)
        if lineage != _expected_lineage(canonical_mode):
            _invalid()
        symbol = _canonical_symbol(canonical_symbol)
        observed = _utc_text(observed_at)
        if type(request_invocation_count) is not int:
            _invalid()
        if type(observations) not in (list, tuple):
            _invalid()
        copied = tuple(
            _copy_oi_observation(item) for item in observations
        )
        if not copied:
            _invalid()
        newest = copied[-1].close_time
        age = int(
            (
                _utc_datetime(observed)
                - _utc_datetime(newest)
            ).total_seconds()
        )
        observations_hash = _hash_sequence(
            [item.to_mapping() for item in copied]
        )
        content: dict[str, object] = {
            "schema_version":
                MODE_OI_EXECUTION_EVIDENCE_SCHEMA_VERSION,
            "policy_version":
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            "mode": canonical_mode,
            "mode_lineage_sha256": lineage,
            "canonical_symbol": symbol,
            "observed_at": observed,
            "period": "5m",
            "request_invocation_count": request_invocation_count,
            "observations": [
                item.to_mapping() for item in copied
            ],
            "observation_count": len(copied),
            "newest_close_at": newest,
            "newest_age_seconds": age,
            "observations_sha256": observations_hash,
        }
        return ModeOiExecutionEvidenceV1(
            **{
                **content,
                "observations": copied,
                "evidence_sha256": _hash_mapping(content),
            }
        )
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


def build_mode_technical_evaluator_payload(
    *,
    trigger_candle_close_at: object,
    score: object,
    trend: object,
    bos: object,
    choch: object,
    reference_price: object,
    reference_candle_at: object,
    volume_ratio: object,
    volume_v2_status: object,
    golden_zone: object,
) -> ModeTechnicalEvaluatorPayloadV1:
    try:
        trigger = _utc_text(trigger_candle_close_at)
        payload = {
            "score": score,
            "trend": trend,
            "bos": bos,
            "choch": choch,
            "reference_price": reference_price,
            "reference_candle_at": reference_candle_at,
            "volume_ratio": volume_ratio,
            "volume_v2_status": volume_v2_status,
            "golden_zone": golden_zone,
        }
        _validated_technical_payload(
            payload,
            trigger_candle_close_at=trigger,
        )
        payload_json = _canonical_dict_json(payload)
        return ModeTechnicalEvaluatorPayloadV1(
            schema_version=(
                MODE_TECHNICAL_EVALUATOR_PAYLOAD_SCHEMA_VERSION
            ),
            policy_version=(
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION
            ),
            trigger_candle_close_at=trigger,
            payload_json=payload_json,
            payload_sha256=_hash_json(payload_json),
        )
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


def build_e2_candidate_id(
    *,
    plan_sha256: object,
    mode: object,
    mode_lineage_sha256: object,
    canonical_symbol: object,
    reference_candle_at: object,
    payload_sha256: object,
) -> str:
    try:
        return _expected_candidate_id(
            plan_sha256=plan_sha256,
            mode=mode,
            mode_lineage_sha256=mode_lineage_sha256,
            canonical_symbol=canonical_symbol,
            reference_candle_at=reference_candle_at,
            payload_sha256=payload_sha256,
        )
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


def build_mode_execution_candidate_row(
    *,
    plan: object,
    symbol_plan: object,
    evaluator_payload: object,
    trigger_candle_close_at: object,
) -> ModeExecutionCandidateRowV1:
    try:
        copied_plan = _copy_plan(plan)
        copied_symbol = _copy_symbol_plan(symbol_plan)
        matching = tuple(
            item
            for item in copied_plan.full_evaluation_symbols
            if item.full_evaluation_rank
            == copied_symbol.full_evaluation_rank
        )
        if (
            len(matching) != 1
            or _canonical_dict_json(matching[0].to_mapping())
            != _canonical_dict_json(copied_symbol.to_mapping())
        ):
            _invalid()
        payload = _copy_evaluator_payload(evaluator_payload)
        trigger = _utc_text(trigger_candle_close_at)
        if payload.trigger_candle_close_at != trigger:
            _invalid()
        candidate_id = _expected_candidate_id(
            plan_sha256=copied_plan.plan_sha256,
            mode=copied_plan.mode,
            mode_lineage_sha256=(
                copied_plan.mode_lineage_sha256
            ),
            canonical_symbol=copied_symbol.canonical_symbol,
            reference_candle_at=trigger,
            payload_sha256=payload.payload_sha256,
        )
        return ModeExecutionCandidateRowV1(
            schema_version=(
                MODE_EXECUTION_CANDIDATE_ROW_SCHEMA_VERSION
            ),
            policy_version=(
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION
            ),
            plan_sha256=copied_plan.plan_sha256,
            candidate_id=candidate_id,
            mode=copied_plan.mode,
            symbol=copied_symbol.canonical_symbol,
            mode_lineage_sha256=(
                copied_plan.mode_lineage_sha256
            ),
            reference_candle_at=trigger,
            payload_json=payload.payload_json,
            payload_sha256=payload.payload_sha256,
        )
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()


def build_mode_scan_execution_result(
    *,
    plan: object,
    observed_at: object,
    outcomes: object,
    actual_candle_call_count: object,
    actual_oi_call_count: object,
    actual_evaluator_invocation_count: object,
    actual_executor_ip_weight: object,
) -> ModeScanExecutionResultV1:
    try:
        copied_plan = _copy_plan(plan)
        observed = _utc_text(observed_at)
        if type(outcomes) not in (list, tuple):
            _invalid()
        copied_outcomes = tuple(
            _copy_outcome(item) for item in outcomes
        )
        symbol_order = tuple(
            item.canonical_symbol
            for item in copied_plan.full_evaluation_symbols
        )
        timeframe_counts = tuple(
            len(item.candle_fetches)
            for item in copied_plan.full_evaluation_symbols
        )
        planned_candles = sum(timeframe_counts)
        planned_oi = len(symbol_order)
        budget = copied_plan.fetch_budget_copy()
        planned_requests = (
            budget["total_request_count"]
            - budget["market_level_request_count"]
        )
        planned_weight = (
            budget["total_ip_weight"]
            - budget["market_level_ip_weight"]
        )
        actual_candles = _integer(
            actual_candle_call_count,
            minimum=0,
        )
        actual_oi = _integer(actual_oi_call_count, minimum=0)
        actual_evaluator = _integer(
            actual_evaluator_invocation_count,
            minimum=0,
        )
        actual_weight = _integer(
            actual_executor_ip_weight,
            minimum=0,
        )
        candidates = tuple(
            item.candidate_row
            for item in copied_outcomes
            if item.outcome_kind == OUTCOME_CANDIDATE
            and item.candidate_row is not None
        )
        content: dict[str, object] = {
            "schema_version":
                MODE_SCAN_EXECUTION_RESULT_SCHEMA_VERSION,
            "policy_version":
                MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
            "plan_sha256": copied_plan.plan_sha256,
            "mode": copied_plan.mode,
            "mode_lineage_sha256":
                copied_plan.mode_lineage_sha256,
            "observed_at": observed,
            "planned_symbol_order": list(symbol_order),
            "planned_timeframe_counts": list(timeframe_counts),
            "planned_candle_call_count": planned_candles,
            "planned_oi_call_count": planned_oi,
            "planned_evaluator_invocation_count":
                len(symbol_order),
            "planned_executor_request_count": planned_requests,
            "planned_executor_ip_weight": planned_weight,
            "actual_candle_call_count": actual_candles,
            "actual_oi_call_count": actual_oi,
            "actual_evaluator_invocation_count":
                actual_evaluator,
            "actual_executor_request_count":
                actual_candles + actual_oi,
            "actual_executor_ip_weight": actual_weight,
            "candidate_count": sum(
                item.outcome_kind == OUTCOME_CANDIDATE
                for item in copied_outcomes
            ),
            "no_candidate_count": sum(
                item.outcome_kind == OUTCOME_NO_CANDIDATE
                for item in copied_outcomes
            ),
            "skipped_count": sum(
                item.outcome_kind == OUTCOME_SKIPPED
                for item in copied_outcomes
            ),
            "retry_count": 0,
            "outcomes": [
                item.to_mapping() for item in copied_outcomes
            ],
            "candidates": [
                item.to_mapping() for item in candidates
            ],
        }
        return ModeScanExecutionResultV1(
            **{
                **content,
                "planned_symbol_order": symbol_order,
                "planned_timeframe_counts": timeframe_counts,
                "outcomes": copied_outcomes,
                "candidates": candidates,
                "execution_sha256": _hash_mapping(content),
            }
        )
    except ModeScanExecutionEvidenceValidationError:
        raise
    except Exception:
        _invalid()
