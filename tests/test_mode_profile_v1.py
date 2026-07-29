"""Focused contract tests for immutable mode profiles."""

import ast
import dataclasses
from pathlib import Path

import pytest

from engine.mode_profile_v1 import (
    MODE_PROFILE_POLICY_VERSION,
    ModeProfileV1,
    ModeProfileValidationError,
    all_mode_profiles,
    get_mode_profile,
    validate_mode_lineage,
)


@pytest.fixture(params=("SWING", "INTRADAY", "SCALP"))
def profile(request):
    return get_mode_profile(request.param)


def _valid_lineage(profile):
    return {
        "mode": profile.mode,
        "context_timeframes": profile.context_timeframes,
        "optional_context_timeframes": profile.optional_context_timeframes,
        "bias_timeframe": profile.bias_timeframe,
        "structure_timeframe": profile.structure_timeframe,
        "trigger_timeframe": profile.trigger_timeframe,
        "trigger_candle_closed": True,
    }


def test_profiles_exist_in_fixed_order():
    profiles = all_mode_profiles()

    assert tuple(profile.mode for profile in profiles) == ("SWING", "INTRADAY", "SCALP")
    assert len(profiles) == 3
    assert all(profile.policy_version == MODE_PROFILE_POLICY_VERSION for profile in profiles)


@pytest.mark.parametrize(
    ("mode", "context", "optional_context", "bias", "structure", "trigger"),
    (
        ("SWING", ("1w", "1d"), (), "4h", "1h", "15m"),
        ("INTRADAY", ("1d", "4h"), (), "1h", "15m", "5m"),
        ("SCALP", (), ("1h",), "15m", "5m", "3m"),
    ),
)
def test_exact_mode_lineages(mode, context, optional_context, bias, structure, trigger):
    profile = get_mode_profile(mode)

    assert profile.context_timeframes == context
    assert profile.optional_context_timeframes == optional_context
    assert profile.bias_timeframe == bias
    assert profile.structure_timeframe == structure
    assert profile.trigger_timeframe == trigger
    assert validate_mode_lineage(**_valid_lineage(profile)) is profile


def test_scalp_one_minute_trigger_is_rejected():
    fields = _valid_lineage(get_mode_profile("SCALP"))
    fields["trigger_timeframe"] = "1m"

    with pytest.raises(ModeProfileValidationError):
        validate_mode_lineage(**fields)


def test_developing_trigger_candle_is_rejected_for_every_mode(profile):
    fields = _valid_lineage(profile)
    fields["trigger_candle_closed"] = False

    with pytest.raises(ModeProfileValidationError):
        validate_mode_lineage(**fields)


def test_modes_cannot_borrow_each_others_lineage(profile):
    for other in all_mode_profiles():
        if other is profile:
            continue
        for field_name in (
            "context_timeframes",
            "optional_context_timeframes",
            "bias_timeframe",
            "structure_timeframe",
            "trigger_timeframe",
        ):
            if getattr(other, field_name) == getattr(profile, field_name):
                continue
            fields = _valid_lineage(profile)
            fields[field_name] = getattr(other, field_name)
            with pytest.raises(ModeProfileValidationError):
                validate_mode_lineage(**fields)


def test_exact_cadence_values():
    profiles = {profile.mode: profile for profile in all_mode_profiles()}

    assert [profiles[mode].maximum_trigger_age_seconds for mode in profiles] == [900, 300, 180]
    assert [profiles[mode].structure_evaluation_offset_seconds for mode in profiles] == [60, 20, 10]
    assert [profiles[mode].armed_monitor_offset_seconds for mode in profiles] == [20, 10, 5]


def test_shared_lock_flags_are_fixed(profile):
    assert profile.trigger_candle_closed_only is True
    assert profile.developing_candle_allowed is False
    assert profile.one_mode_job_per_due_window is True
    assert profile.global_nonoverlap_required is True
    assert profile.missed_run_catchup_allowed is False
    assert profile.immediate_retry_allowed is False
    assert profile.manual_forced_scan_allowed is False
    assert profile.publication_from_shadow_allowed is False


def test_profiles_and_caller_containers_are_immutable_and_canonical():
    profile = get_mode_profile("SWING")
    caller_context = ["1w", "1d"]
    candidate = dataclasses.replace(profile, context_timeframes=caller_context)
    caller_context.append("4h")

    assert candidate.context_timeframes == ("1w", "1d")
    assert get_mode_profile("SWING") is profile
    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.mode = "SCALP"
    with pytest.raises(TypeError):
        profile.context_timeframes[0] = "1d"


@pytest.mark.parametrize("bad_mode", ("swing", "UNKNOWN", 1, True, None))
def test_invalid_mode_values_fail_closed(bad_mode):
    with pytest.raises(ModeProfileValidationError):
        get_mode_profile(bad_mode)


def test_invalid_types_unknowns_duplicates_and_cadence_values_fail_closed():
    fields = _valid_lineage(get_mode_profile("INTRADAY"))
    invalid_variants = (
        {**fields, "context_timeframes": ("1d", "1d")},
        {**fields, "context_timeframes": ("1d", "2h")},
        {**fields, "context_timeframes": "1d"},
        {**fields, "bias_timeframe": "2h"},
        {**fields, "trigger_candle_closed": 1},
        {**fields, "unknown_field": "value"},
    )
    for variant in invalid_variants:
        with pytest.raises(ModeProfileValidationError):
            validate_mode_lineage(**variant)

    profile = get_mode_profile("SWING")
    for invalid_cadence in (True, 0, -1, 1.0, float("nan"), float("inf")):
        with pytest.raises(ModeProfileValidationError):
            dataclasses.replace(profile, maximum_trigger_age_seconds=invalid_cadence)


def test_source_has_no_prohibited_imports_or_operational_calls():
    source_path = Path(__file__).parents[1] / "engine" / "mode_profile_v1.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    prohibited_modules = {
        "ccxt",
        "requests",
        "httpx",
        "socket",
        "telegram",
        "subprocess",
        "pathlib",
        "os",
        "threading",
        "asyncio",
    }
    imports = set()
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            calls.append(ast.unparse(node.func))

    assert not imports & prohibited_modules
    assert not {"open", "system", "run", "Popen", "connect"} & set(calls)
