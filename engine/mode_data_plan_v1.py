"""Deterministic mode-owned market-data plans and shared audit lineage."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Final

from engine.mode_profile_v1 import (
    MODE_PROFILE_POLICY_VERSION,
    ModeProfileV1,
    ModeProfileValidationError,
    all_mode_profiles,
    get_mode_profile,
)


MODE_DATA_PLAN_POLICY_VERSION: Final = "mode-data-plan-policy-v1"
MODE_LINEAGE_AUDIT_SCHEMA_VERSION: Final = "mode-lineage-audit-v1"

LIVE_PRICE_BOUNDARY: Final = "SEPARATE_FRESH_PRICE_ADMISSION_V1"
ROUTING_MODE_AUTHORITY: Final = "EXACT_CALLER_MODE_PROFILE"

_CONTEXT: Final = "CONTEXT"
_OPTIONAL_CONTEXT: Final = "OPTIONAL_CONTEXT"
_BIAS: Final = "BIAS"
_STRUCTURE: Final = "STRUCTURE"
_TRIGGER: Final = "TRIGGER"

_PURPOSES: Final = frozenset(
    (
        _CONTEXT,
        _OPTIONAL_CONTEXT,
        _BIAS,
        _STRUCTURE,
        _TRIGGER,
    )
)

_KNOWN_TIMEFRAMES: Final = frozenset(
    timeframe
    for profile in all_mode_profiles()
    for timeframe in (
        *profile.context_timeframes,
        *profile.optional_context_timeframes,
        profile.bias_timeframe,
        profile.structure_timeframe,
        profile.trigger_timeframe,
        *profile.structure_evaluation_timeframes,
        profile.armed_monitor_timeframe,
    )
)


class ModeDataPlanValidationError(ValueError):
    """Raised when a mode data plan or audit lineage is not canonical."""


def _invalid() -> None:
    raise ModeDataPlanValidationError("invalid mode data plan")


def _require_text(value: object) -> str:
    if type(value) is not str or not value:
        _invalid()
    return value


def _require_boolean(value: object) -> bool:
    if type(value) is not bool:
        _invalid()
    return value


def _require_positive_integer(value: object) -> int:
    if type(value) is not int or value <= 0:
        _invalid()
    return value


def _require_timeframe(value: object) -> str:
    timeframe = _require_text(value)
    if timeframe not in _KNOWN_TIMEFRAMES:
        _invalid()
    return timeframe


def _profile(mode: object) -> ModeProfileV1:
    try:
        return get_mode_profile(mode)
    except ModeProfileValidationError as exc:
        raise ModeDataPlanValidationError(
            "invalid mode data plan"
        ) from exc


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ModeDataPlanValidationError(
            "invalid mode data plan"
        ) from exc


@dataclass(frozen=True, slots=True)
class ModeTimeframeRequirementV1:
    """One closed-candle requirement owned by an exact mode role."""

    purpose: str
    timeframe: str
    required: bool
    closed_candle_only: bool

    def __post_init__(self) -> None:
        if _require_text(self.purpose) not in _PURPOSES:
            _invalid()
        object.__setattr__(
            self,
            "timeframe",
            _require_timeframe(self.timeframe),
        )
        _require_boolean(self.required)
        if _require_boolean(self.closed_candle_only) is not True:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "purpose": self.purpose,
            "timeframe": self.timeframe,
            "required": self.required,
            "closed_candle_only": self.closed_candle_only,
        }


def _expected_requirements(
    profile: ModeProfileV1,
) -> tuple[ModeTimeframeRequirementV1, ...]:
    requirements: list[ModeTimeframeRequirementV1] = []

    requirements.extend(
        ModeTimeframeRequirementV1(
            purpose=_CONTEXT,
            timeframe=timeframe,
            required=True,
            closed_candle_only=True,
        )
        for timeframe in profile.context_timeframes
    )

    requirements.extend(
        ModeTimeframeRequirementV1(
            purpose=_OPTIONAL_CONTEXT,
            timeframe=timeframe,
            required=False,
            closed_candle_only=True,
        )
        for timeframe in profile.optional_context_timeframes
    )

    requirements.extend(
        (
            ModeTimeframeRequirementV1(
                purpose=_BIAS,
                timeframe=profile.bias_timeframe,
                required=True,
                closed_candle_only=True,
            ),
            ModeTimeframeRequirementV1(
                purpose=_STRUCTURE,
                timeframe=profile.structure_timeframe,
                required=True,
                closed_candle_only=True,
            ),
            ModeTimeframeRequirementV1(
                purpose=_TRIGGER,
                timeframe=profile.trigger_timeframe,
                required=True,
                closed_candle_only=True,
            ),
        )
    )

    return tuple(requirements)


def _requirement_tuple(
    value: object,
) -> tuple[ModeTimeframeRequirementV1, ...]:
    if type(value) not in (tuple, list):
        _invalid()

    requirements = tuple(value)
    if not requirements or any(
        type(requirement) is not ModeTimeframeRequirementV1
        for requirement in requirements
    ):
        _invalid()

    return requirements


@dataclass(frozen=True, slots=True)
class ModeDataPlanV1:
    """Canonical data requirements and execution boundaries for one mode."""

    policy_version: str
    mode: str
    profile_policy_version: str
    timeframe_requirements: tuple[ModeTimeframeRequirementV1, ...]
    live_price_boundary: str
    routing_mode_authority: str
    one_mode_job_per_due_window: bool
    global_nonoverlap_required: bool
    missed_run_catchup_allowed: bool
    immediate_retry_allowed: bool
    manual_forced_scan_allowed: bool
    publication_from_shadow_allowed: bool

    def __post_init__(self) -> None:
        if self.policy_version != MODE_DATA_PLAN_POLICY_VERSION:
            _invalid()

        profile = _profile(self.mode)

        if self.profile_policy_version != MODE_PROFILE_POLICY_VERSION:
            _invalid()

        requirements = _requirement_tuple(
            self.timeframe_requirements
        )
        object.__setattr__(
            self,
            "timeframe_requirements",
            requirements,
        )

        if requirements != _expected_requirements(profile):
            _invalid()

        if self.live_price_boundary != LIVE_PRICE_BOUNDARY:
            _invalid()
        if self.routing_mode_authority != ROUTING_MODE_AUTHORITY:
            _invalid()

        expected_flags = {
            "one_mode_job_per_due_window":
                profile.one_mode_job_per_due_window,
            "global_nonoverlap_required":
                profile.global_nonoverlap_required,
            "missed_run_catchup_allowed":
                profile.missed_run_catchup_allowed,
            "immediate_retry_allowed":
                profile.immediate_retry_allowed,
            "manual_forced_scan_allowed":
                profile.manual_forced_scan_allowed,
            "publication_from_shadow_allowed":
                profile.publication_from_shadow_allowed,
        }

        for field_name, expected in expected_flags.items():
            supplied = _require_boolean(
                getattr(self, field_name)
            )
            if supplied is not expected:
                _invalid()

    def to_mapping(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "mode": self.mode,
            "profile_policy_version":
                self.profile_policy_version,
            "timeframe_requirements": [
                requirement.to_mapping()
                for requirement in self.timeframe_requirements
            ],
            "live_price_boundary": self.live_price_boundary,
            "routing_mode_authority":
                self.routing_mode_authority,
            "one_mode_job_per_due_window":
                self.one_mode_job_per_due_window,
            "global_nonoverlap_required":
                self.global_nonoverlap_required,
            "missed_run_catchup_allowed":
                self.missed_run_catchup_allowed,
            "immediate_retry_allowed":
                self.immediate_retry_allowed,
            "manual_forced_scan_allowed":
                self.manual_forced_scan_allowed,
            "publication_from_shadow_allowed":
                self.publication_from_shadow_allowed,
        }


@dataclass(frozen=True, slots=True)
class ModeAuditLineageV1:
    """Shared immutable audit schema proving exact mode ownership."""

    schema_version: str
    mode: str
    mode_profile_version: str
    mode_data_plan_version: str
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
    live_price_boundary: str
    routing_mode_authority: str

    def __post_init__(self) -> None:
        if self.schema_version != MODE_LINEAGE_AUDIT_SCHEMA_VERSION:
            _invalid()

        profile = _profile(self.mode)
        plan = build_mode_data_plan(self.mode)

        expected = {
            "mode_profile_version": profile.policy_version,
            "mode_data_plan_version": plan.policy_version,
            "context_timeframes": profile.context_timeframes,
            "optional_context_timeframes":
                profile.optional_context_timeframes,
            "bias_timeframe": profile.bias_timeframe,
            "structure_timeframe":
                profile.structure_timeframe,
            "trigger_timeframe": profile.trigger_timeframe,
            "trigger_rule": profile.trigger_rule,
            "trigger_candle_closed_only":
                profile.trigger_candle_closed_only,
            "developing_candle_allowed":
                profile.developing_candle_allowed,
            "maximum_trigger_age_seconds":
                profile.maximum_trigger_age_seconds,
            "structure_evaluation_timeframes":
                profile.structure_evaluation_timeframes,
            "structure_evaluation_offset_seconds":
                profile.structure_evaluation_offset_seconds,
            "armed_monitor_timeframe":
                profile.armed_monitor_timeframe,
            "armed_monitor_offset_seconds":
                profile.armed_monitor_offset_seconds,
            "update_higher_context_when_due":
                profile.update_higher_context_when_due,
            "one_mode_job_per_due_window":
                profile.one_mode_job_per_due_window,
            "global_nonoverlap_required":
                profile.global_nonoverlap_required,
            "missed_run_catchup_allowed":
                profile.missed_run_catchup_allowed,
            "immediate_retry_allowed":
                profile.immediate_retry_allowed,
            "manual_forced_scan_allowed":
                profile.manual_forced_scan_allowed,
            "publication_from_shadow_allowed":
                profile.publication_from_shadow_allowed,
            "live_price_boundary": plan.live_price_boundary,
            "routing_mode_authority":
                plan.routing_mode_authority,
        }

        for field_name, expected_value in expected.items():
            supplied_value = getattr(self, field_name)
            if type(expected_value) is bool:
                supplied_value = _require_boolean(supplied_value)
                if supplied_value is not expected_value:
                    _invalid()
            elif supplied_value != expected_value:
                _invalid()

        _require_positive_integer(
            self.maximum_trigger_age_seconds
        )
        _require_positive_integer(
            self.structure_evaluation_offset_seconds
        )
        _require_positive_integer(
            self.armed_monitor_offset_seconds
        )

    def _identity_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "mode_profile_version":
                self.mode_profile_version,
            "mode_data_plan_version":
                self.mode_data_plan_version,
            "context_timeframes":
                list(self.context_timeframes),
            "optional_context_timeframes":
                list(self.optional_context_timeframes),
            "bias_timeframe": self.bias_timeframe,
            "structure_timeframe":
                self.structure_timeframe,
            "trigger_timeframe": self.trigger_timeframe,
            "trigger_rule": self.trigger_rule,
            "trigger_candle_closed_only":
                self.trigger_candle_closed_only,
            "developing_candle_allowed":
                self.developing_candle_allowed,
            "maximum_trigger_age_seconds":
                self.maximum_trigger_age_seconds,
            "structure_evaluation_timeframes":
                list(self.structure_evaluation_timeframes),
            "structure_evaluation_offset_seconds":
                self.structure_evaluation_offset_seconds,
            "armed_monitor_timeframe":
                self.armed_monitor_timeframe,
            "armed_monitor_offset_seconds":
                self.armed_monitor_offset_seconds,
            "update_higher_context_when_due":
                self.update_higher_context_when_due,
            "one_mode_job_per_due_window":
                self.one_mode_job_per_due_window,
            "global_nonoverlap_required":
                self.global_nonoverlap_required,
            "missed_run_catchup_allowed":
                self.missed_run_catchup_allowed,
            "immediate_retry_allowed":
                self.immediate_retry_allowed,
            "manual_forced_scan_allowed":
                self.manual_forced_scan_allowed,
            "publication_from_shadow_allowed":
                self.publication_from_shadow_allowed,
            "live_price_boundary":
                self.live_price_boundary,
            "routing_mode_authority":
                self.routing_mode_authority,
        }

    @property
    def lineage_sha256(self) -> str:
        return sha256(
            _canonical_json_bytes(self._identity_mapping())
        ).hexdigest()

    def to_mapping(self) -> dict[str, object]:
        mapping = self._identity_mapping()
        mapping["lineage_sha256"] = self.lineage_sha256
        return mapping


def build_mode_data_plan(mode: object) -> ModeDataPlanV1:
    """Build the only accepted data plan for an exact mode."""

    profile = _profile(mode)

    return ModeDataPlanV1(
        policy_version=MODE_DATA_PLAN_POLICY_VERSION,
        mode=profile.mode,
        profile_policy_version=profile.policy_version,
        timeframe_requirements=_expected_requirements(profile),
        live_price_boundary=LIVE_PRICE_BOUNDARY,
        routing_mode_authority=ROUTING_MODE_AUTHORITY,
        one_mode_job_per_due_window=
            profile.one_mode_job_per_due_window,
        global_nonoverlap_required=
            profile.global_nonoverlap_required,
        missed_run_catchup_allowed=
            profile.missed_run_catchup_allowed,
        immediate_retry_allowed=
            profile.immediate_retry_allowed,
        manual_forced_scan_allowed=
            profile.manual_forced_scan_allowed,
        publication_from_shadow_allowed=
            profile.publication_from_shadow_allowed,
    )


def all_mode_data_plans() -> tuple[ModeDataPlanV1, ...]:
    """Return canonical plans in fixed mode order."""

    return tuple(
        build_mode_data_plan(profile.mode)
        for profile in all_mode_profiles()
    )


def build_mode_audit_lineage(
    mode: object,
) -> ModeAuditLineageV1:
    """Build the shared mode-lineage audit object."""

    profile = _profile(mode)
    plan = build_mode_data_plan(mode)

    return ModeAuditLineageV1(
        schema_version=MODE_LINEAGE_AUDIT_SCHEMA_VERSION,
        mode=profile.mode,
        mode_profile_version=profile.policy_version,
        mode_data_plan_version=plan.policy_version,
        context_timeframes=profile.context_timeframes,
        optional_context_timeframes=
            profile.optional_context_timeframes,
        bias_timeframe=profile.bias_timeframe,
        structure_timeframe=profile.structure_timeframe,
        trigger_timeframe=profile.trigger_timeframe,
        trigger_rule=profile.trigger_rule,
        trigger_candle_closed_only=
            profile.trigger_candle_closed_only,
        developing_candle_allowed=
            profile.developing_candle_allowed,
        maximum_trigger_age_seconds=
            profile.maximum_trigger_age_seconds,
        structure_evaluation_timeframes=
            profile.structure_evaluation_timeframes,
        structure_evaluation_offset_seconds=
            profile.structure_evaluation_offset_seconds,
        armed_monitor_timeframe=
            profile.armed_monitor_timeframe,
        armed_monitor_offset_seconds=
            profile.armed_monitor_offset_seconds,
        update_higher_context_when_due=
            profile.update_higher_context_when_due,
        one_mode_job_per_due_window=
            profile.one_mode_job_per_due_window,
        global_nonoverlap_required=
            profile.global_nonoverlap_required,
        missed_run_catchup_allowed=
            profile.missed_run_catchup_allowed,
        immediate_retry_allowed=
            profile.immediate_retry_allowed,
        manual_forced_scan_allowed=
            profile.manual_forced_scan_allowed,
        publication_from_shadow_allowed=
            profile.publication_from_shadow_allowed,
        live_price_boundary=plan.live_price_boundary,
        routing_mode_authority=plan.routing_mode_authority,
    )
