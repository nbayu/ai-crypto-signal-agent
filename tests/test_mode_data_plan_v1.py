"""Focused tests for mode-owned data plans and audit lineage."""

import ast
import dataclasses
from pathlib import Path

import pytest

from engine.mode_data_plan_v1 import (
    LIVE_PRICE_BOUNDARY,
    MODE_DATA_PLAN_POLICY_VERSION,
    MODE_LINEAGE_AUDIT_SCHEMA_VERSION,
    ROUTING_MODE_AUTHORITY,
    ModeDataPlanValidationError,
    all_mode_data_plans,
    build_mode_audit_lineage,
    build_mode_data_plan,
)


EXPECTED_REQUIREMENTS = {
    "SWING": (
        ("CONTEXT", "1w", True),
        ("CONTEXT", "1d", True),
        ("BIAS", "4h", True),
        ("STRUCTURE", "1h", True),
        ("TRIGGER", "15m", True),
    ),
    "INTRADAY": (
        ("CONTEXT", "1d", True),
        ("CONTEXT", "4h", True),
        ("BIAS", "1h", True),
        ("STRUCTURE", "15m", True),
        ("TRIGGER", "5m", True),
    ),
    "SCALP": (
        ("OPTIONAL_CONTEXT", "1h", False),
        ("BIAS", "15m", True),
        ("STRUCTURE", "5m", True),
        ("TRIGGER", "3m", True),
    ),
}


@pytest.fixture(params=("SWING", "INTRADAY", "SCALP"))
def mode(request):
    return request.param


def test_all_plans_exist_in_fixed_mode_order():
    plans = all_mode_data_plans()

    assert tuple(plan.mode for plan in plans) == (
        "SWING",
        "INTRADAY",
        "SCALP",
    )
    assert all(
        plan.policy_version == MODE_DATA_PLAN_POLICY_VERSION
        for plan in plans
    )


def test_each_mode_owns_exact_timeframe_requirements(mode):
    plan = build_mode_data_plan(mode)

    actual = tuple(
        (
            requirement.purpose,
            requirement.timeframe,
            requirement.required,
        )
        for requirement in plan.timeframe_requirements
    )

    assert actual == EXPECTED_REQUIREMENTS[mode]


def test_all_market_structure_inputs_are_closed_candle_only(mode):
    plan = build_mode_data_plan(mode)

    assert all(
        requirement.closed_candle_only is True
        for requirement in plan.timeframe_requirements
    )


def test_live_price_admission_is_an_explicit_separate_boundary(mode):
    plan = build_mode_data_plan(mode)

    assert plan.live_price_boundary == LIVE_PRICE_BOUNDARY
    assert (
        plan.live_price_boundary
        == "SEPARATE_FRESH_PRICE_ADMISSION_V1"
    )
    assert not any(
        requirement.purpose == "LIVE_PRICE"
        for requirement in plan.timeframe_requirements
    )


def test_routing_authority_has_no_default_swing_fallback(mode):
    plan = build_mode_data_plan(mode)

    assert plan.routing_mode_authority == ROUTING_MODE_AUTHORITY
    assert plan.routing_mode_authority == "EXACT_CALLER_MODE_PROFILE"


def test_no_catchup_retry_forced_scan_or_shadow_publication(mode):
    plan = build_mode_data_plan(mode)

    assert plan.one_mode_job_per_due_window is True
    assert plan.global_nonoverlap_required is True
    assert plan.missed_run_catchup_allowed is False
    assert plan.immediate_retry_allowed is False
    assert plan.manual_forced_scan_allowed is False
    assert plan.publication_from_shadow_allowed is False


def test_modes_cannot_borrow_other_mode_requirements():
    swing = build_mode_data_plan("SWING")
    scalp = build_mode_data_plan("SCALP")

    with pytest.raises(ModeDataPlanValidationError):
        dataclasses.replace(
            swing,
            timeframe_requirements=scalp.timeframe_requirements,
        )

    with pytest.raises(ModeDataPlanValidationError):
        dataclasses.replace(scalp, mode="SWING")


@pytest.mark.parametrize(
    "bad_mode",
    ("swing", "UNKNOWN", "", 1, True, None),
)
def test_invalid_mode_fails_closed(bad_mode):
    with pytest.raises(ModeDataPlanValidationError):
        build_mode_data_plan(bad_mode)

    with pytest.raises(ModeDataPlanValidationError):
        build_mode_audit_lineage(bad_mode)


def test_plan_containers_and_requirements_are_immutable():
    plan = build_mode_data_plan("SWING")
    requirement = plan.timeframe_requirements[0]

    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.mode = "SCALP"

    with pytest.raises(dataclasses.FrozenInstanceError):
        requirement.timeframe = "1d"

    with pytest.raises(TypeError):
        plan.timeframe_requirements[0] = requirement


def test_audit_lineage_uses_one_shared_schema(mode):
    lineage = build_mode_audit_lineage(mode)
    mapping = lineage.to_mapping()

    assert lineage.schema_version == MODE_LINEAGE_AUDIT_SCHEMA_VERSION
    assert mapping["mode"] == mode
    assert mapping["mode_profile_version"] == "mode-profile-policy-v1"
    assert (
        mapping["mode_data_plan_version"]
        == MODE_DATA_PLAN_POLICY_VERSION
    )
    assert mapping["live_price_boundary"] == LIVE_PRICE_BOUNDARY
    assert mapping["routing_mode_authority"] == ROUTING_MODE_AUTHORITY
    assert len(mapping["lineage_sha256"]) == 64
    assert set(mapping) == {
        "schema_version",
        "mode",
        "mode_profile_version",
        "mode_data_plan_version",
        "context_timeframes",
        "optional_context_timeframes",
        "bias_timeframe",
        "structure_timeframe",
        "trigger_timeframe",
        "trigger_rule",
        "trigger_candle_closed_only",
        "developing_candle_allowed",
        "maximum_trigger_age_seconds",
        "structure_evaluation_timeframes",
        "structure_evaluation_offset_seconds",
        "armed_monitor_timeframe",
        "armed_monitor_offset_seconds",
        "update_higher_context_when_due",
        "one_mode_job_per_due_window",
        "global_nonoverlap_required",
        "missed_run_catchup_allowed",
        "immediate_retry_allowed",
        "manual_forced_scan_allowed",
        "publication_from_shadow_allowed",
        "live_price_boundary",
        "routing_mode_authority",
        "lineage_sha256",
    }


def test_audit_lineage_is_deterministic_and_mode_distinct():
    first = build_mode_audit_lineage("SWING")
    second = build_mode_audit_lineage("SWING")
    intraday = build_mode_audit_lineage("INTRADAY")
    scalp = build_mode_audit_lineage("SCALP")

    assert first.to_mapping() == second.to_mapping()
    assert first.lineage_sha256 == second.lineage_sha256
    assert len(
        {
            first.lineage_sha256,
            intraday.lineage_sha256,
            scalp.lineage_sha256,
        }
    ) == 3


def test_audit_lineage_rejects_cross_mode_or_tampered_fields():
    swing = build_mode_audit_lineage("SWING")

    for field_name, bad_value in (
        ("mode", "SCALP"),
        ("trigger_timeframe", "3m"),
        ("structure_timeframe", "5m"),
        ("missed_run_catchup_allowed", True),
        ("immediate_retry_allowed", True),
        ("manual_forced_scan_allowed", True),
        ("publication_from_shadow_allowed", True),
        ("live_price_boundary", "INLINE_PRICE"),
        ("routing_mode_authority", "DEFAULT_SWING"),
    ):
        with pytest.raises(ModeDataPlanValidationError):
            dataclasses.replace(
                swing,
                **{field_name: bad_value},
            )


@pytest.mark.parametrize(
    ("field_name", "integer_alias"),
    (
        ("trigger_candle_closed_only", 1),
        ("developing_candle_allowed", 0),
        ("update_higher_context_when_due", 1),
        ("one_mode_job_per_due_window", 1),
        ("global_nonoverlap_required", 1),
        ("missed_run_catchup_allowed", 0),
        ("immediate_retry_allowed", 0),
        ("manual_forced_scan_allowed", 0),
        ("publication_from_shadow_allowed", 0),
    ),
)
def test_audit_lineage_rejects_integer_boolean_aliases(
    field_name,
    integer_alias,
):
    lineage = build_mode_audit_lineage("SWING")

    with pytest.raises(ModeDataPlanValidationError):
        dataclasses.replace(
            lineage,
            **{field_name: integer_alias},
        )


def test_mapping_mutation_cannot_change_canonical_lineage():
    lineage = build_mode_audit_lineage("SCALP")
    mapping = lineage.to_mapping()
    original_hash = lineage.lineage_sha256

    mapping["mode"] = "SWING"
    mapping["context_timeframes"].append("1d")

    assert lineage.mode == "SCALP"
    assert lineage.context_timeframes == ()
    assert lineage.lineage_sha256 == original_hash


def test_engine_source_has_no_operational_imports_or_calls():
    source_path = (
        Path(__file__).parents[1]
        / "engine"
        / "mode_data_plan_v1.py"
    )
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
    prohibited_calls = {
        "open",
        "system",
        "run",
        "Popen",
        "connect",
        "send_message",
        "create_order",
        "place_order",
        "fetch_balance",
    }

    imports = set()
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name.split(".", 1)[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert not imports & prohibited_modules
    assert not calls & prohibited_calls
