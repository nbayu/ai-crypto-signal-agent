"""Immutable, side-effect-free mode lineage and cadence definitions."""

from dataclasses import dataclass
from typing import Final


MODE_PROFILE_POLICY_VERSION: Final = "mode-profile-policy-v1"


class ModeProfileValidationError(ValueError):
    """Raised when a mode profile request does not satisfy this contract."""


_SUPPORTED_MODES: Final = ("SWING", "INTRADAY", "SCALP")
_KNOWN_TIMEFRAMES: Final = frozenset(("1w", "1d", "4h", "1h", "15m", "5m", "3m"))


def _invalid() -> None:
    raise ModeProfileValidationError("invalid mode profile request")


def _require_positive_integer(value: object) -> int:
    if type(value) is not int or value <= 0:
        _invalid()
    return value


def _require_boolean(value: object) -> bool:
    if type(value) is not bool:
        _invalid()
    return value


def _require_timeframe(value: object) -> str:
    if type(value) is not str or value not in _KNOWN_TIMEFRAMES:
        _invalid()
    return value


def _normalize_timeframes(value: object) -> tuple[str, ...]:
    if type(value) not in (tuple, list):
        _invalid()
    timeframes = tuple(_require_timeframe(item) for item in value)
    if len(timeframes) != len(set(timeframes)):
        _invalid()
    return timeframes


@dataclass(frozen=True, slots=True)
class ModeProfileV1:
    """The complete, immutable lineage and logical-cadence contract for one mode."""

    policy_version: str
    mode: str
    context_timeframes: tuple[str, ...]
    optional_context_timeframes: tuple[str, ...]
    bias_timeframe: str
    structure_timeframe: str
    trigger_timeframe: str
    trigger_rule: str
    trigger_candle_closed_only: bool
    developing_candle_allowed: bool
    maximum_trigger_age_seconds: int
    structure_evaluation_timeframes: tuple[str, ...]
    structure_evaluation_offset_seconds: int
    armed_monitor_timeframe: str
    armed_monitor_offset_seconds: int
    update_higher_context_when_due: bool
    one_mode_job_per_due_window: bool
    global_nonoverlap_required: bool
    missed_run_catchup_allowed: bool
    immediate_retry_allowed: bool
    manual_forced_scan_allowed: bool
    publication_from_shadow_allowed: bool

    def __post_init__(self) -> None:
        if self.policy_version != MODE_PROFILE_POLICY_VERSION:
            _invalid()
        if type(self.mode) is not str or self.mode not in _SUPPORTED_MODES:
            _invalid()
        if type(self.trigger_rule) is not str or not self.trigger_rule:
            _invalid()

        object.__setattr__(self, "context_timeframes", _normalize_timeframes(self.context_timeframes))
        object.__setattr__(
            self,
            "optional_context_timeframes",
            _normalize_timeframes(self.optional_context_timeframes),
        )
        object.__setattr__(self, "bias_timeframe", _require_timeframe(self.bias_timeframe))
        object.__setattr__(self, "structure_timeframe", _require_timeframe(self.structure_timeframe))
        object.__setattr__(self, "trigger_timeframe", _require_timeframe(self.trigger_timeframe))
        object.__setattr__(
            self,
            "maximum_trigger_age_seconds",
            _require_positive_integer(self.maximum_trigger_age_seconds),
        )
        object.__setattr__(
            self,
            "structure_evaluation_timeframes",
            _normalize_timeframes(self.structure_evaluation_timeframes),
        )
        object.__setattr__(
            self,
            "structure_evaluation_offset_seconds",
            _require_positive_integer(self.structure_evaluation_offset_seconds),
        )
        object.__setattr__(self, "armed_monitor_timeframe", _require_timeframe(self.armed_monitor_timeframe))
        object.__setattr__(
            self,
            "armed_monitor_offset_seconds",
            _require_positive_integer(self.armed_monitor_offset_seconds),
        )
        for field_name in (
            "trigger_candle_closed_only",
            "developing_candle_allowed",
            "update_higher_context_when_due",
            "one_mode_job_per_due_window",
            "global_nonoverlap_required",
            "missed_run_catchup_allowed",
            "immediate_retry_allowed",
            "manual_forced_scan_allowed",
            "publication_from_shadow_allowed",
        ):
            _require_boolean(getattr(self, field_name))


_MODE_PROFILES: Final = (
    ModeProfileV1(
        policy_version=MODE_PROFILE_POLICY_VERSION,
        mode="SWING",
        context_timeframes=("1w", "1d"),
        optional_context_timeframes=(),
        bias_timeframe="4h",
        structure_timeframe="1h",
        trigger_timeframe="15m",
        trigger_rule="closed 15m BOS/CHOCH or reclaim aligned with 1h structure and 4h bias",
        trigger_candle_closed_only=True,
        developing_candle_allowed=False,
        maximum_trigger_age_seconds=900,
        structure_evaluation_timeframes=("4h",),
        structure_evaluation_offset_seconds=60,
        armed_monitor_timeframe="15m",
        armed_monitor_offset_seconds=20,
        update_higher_context_when_due=True,
        one_mode_job_per_due_window=True,
        global_nonoverlap_required=True,
        missed_run_catchup_allowed=False,
        immediate_retry_allowed=False,
        manual_forced_scan_allowed=False,
        publication_from_shadow_allowed=False,
    ),
    ModeProfileV1(
        policy_version=MODE_PROFILE_POLICY_VERSION,
        mode="INTRADAY",
        context_timeframes=("1d", "4h"),
        optional_context_timeframes=(),
        bias_timeframe="1h",
        structure_timeframe="15m",
        trigger_timeframe="5m",
        trigger_rule="closed 5m BOS/CHOCH or reclaim aligned with 15m structure and 1h bias",
        trigger_candle_closed_only=True,
        developing_candle_allowed=False,
        maximum_trigger_age_seconds=300,
        structure_evaluation_timeframes=("1h", "15m"),
        structure_evaluation_offset_seconds=20,
        armed_monitor_timeframe="5m",
        armed_monitor_offset_seconds=10,
        update_higher_context_when_due=False,
        one_mode_job_per_due_window=True,
        global_nonoverlap_required=True,
        missed_run_catchup_allowed=False,
        immediate_retry_allowed=False,
        manual_forced_scan_allowed=False,
        publication_from_shadow_allowed=False,
    ),
    ModeProfileV1(
        policy_version=MODE_PROFILE_POLICY_VERSION,
        mode="SCALP",
        context_timeframes=(),
        optional_context_timeframes=("1h",),
        bias_timeframe="15m",
        structure_timeframe="5m",
        trigger_timeframe="3m",
        trigger_rule=(
            "closed 3m liquidity sweep/reclaim followed by micro-BOS aligned with "
            "5m structure and 15m bias"
        ),
        trigger_candle_closed_only=True,
        developing_candle_allowed=False,
        maximum_trigger_age_seconds=180,
        structure_evaluation_timeframes=("15m", "5m"),
        structure_evaluation_offset_seconds=10,
        armed_monitor_timeframe="3m",
        armed_monitor_offset_seconds=5,
        update_higher_context_when_due=False,
        one_mode_job_per_due_window=True,
        global_nonoverlap_required=True,
        missed_run_catchup_allowed=False,
        immediate_retry_allowed=False,
        manual_forced_scan_allowed=False,
        publication_from_shadow_allowed=False,
    ),
)
_PROFILE_BY_MODE: Final = {profile.mode: profile for profile in _MODE_PROFILES}


def get_mode_profile(mode: object) -> ModeProfileV1:
    """Return the canonical immutable profile for an exact supported mode."""
    if type(mode) is not str or mode not in _PROFILE_BY_MODE:
        _invalid()
    return _PROFILE_BY_MODE[mode]


def all_mode_profiles() -> tuple[ModeProfileV1, ...]:
    """Return every canonical profile in the contract's fixed mode order."""
    return _MODE_PROFILES


def validate_mode_lineage(
    mode: object,
    context_timeframes: object,
    optional_context_timeframes: object,
    bias_timeframe: object,
    structure_timeframe: object,
    trigger_timeframe: object,
    trigger_candle_closed: object,
    **unknown_fields: object,
) -> ModeProfileV1:
    """Fail closed unless every supplied lineage field exactly matches its mode."""
    if unknown_fields:
        _invalid()
    profile = get_mode_profile(mode)
    if (
        _normalize_timeframes(context_timeframes) != profile.context_timeframes
        or _normalize_timeframes(optional_context_timeframes)
        != profile.optional_context_timeframes
        or _require_timeframe(bias_timeframe) != profile.bias_timeframe
        or _require_timeframe(structure_timeframe) != profile.structure_timeframe
        or _require_timeframe(trigger_timeframe) != profile.trigger_timeframe
        or _require_boolean(trigger_candle_closed) is not True
    ):
        _invalid()
    return profile
