import ast
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
import json
import math
from pathlib import Path

import pytest

from engine.mode_data_plan_v1 import (
    build_mode_audit_lineage,
    build_mode_data_plan,
)
from engine.mode_fetch_budget_cadence_v1 import (
    build_discovery_universe_policy,
    build_mode_fetch_budget,
)
from engine.mode_profile_v1 import all_mode_profiles
from engine.mode_router_v1 import build_mode_scan_request
from engine.mode_scan_execution_plan_v1 import (
    CACHE_KEY_DYNAMIC_FIELD,
    CACHE_KEY_FIELDS,
    CANDLE_SUFFICIENCY_POLICY,
    DEVELOPING_CANDLE_POLICY,
    EXECUTION_STATE,
    LIVE_PRICE_BOUNDARY,
    MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
    MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION,
    MODE_SCAN_EXECUTION_PLAN_SCHEMA_VERSION,
    MODE_SYMBOL_EXECUTION_PLAN_SCHEMA_VERSION,
    MODE_TIMEFRAME_FETCH_PLAN_SCHEMA_VERSION,
    ModeMarketSnapshotEntryV1,
    ModeScanExecutionPlanV1,
    ModeScanExecutionPlanValidationError,
    ModeSymbolExecutionPlanV1,
    ModeTimeframeFetchPlanV1,
    build_mode_scan_execution_plan,
)


ENGINE_PATH = (
    Path(__file__).parents[1]
    / "engine"
    / "mode_scan_execution_plan_v1.py"
)
ERROR_MESSAGE = "invalid mode scan execution plan"
MODES = tuple(profile.mode for profile in all_mode_profiles())


class TextSubclass(str):
    pass


class EqualitySpoof:
    def __eq__(self, _other):
        return True


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def market(
    symbol="BTC/USDT:USDT",
    volume=1000.0,
    **changes,
):
    values = {
        "schema_version":
            MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION,
        "canonical_symbol": symbol,
        "quote_asset": "USDT",
        "settle_asset": "USDT",
        "market_kind": "swap",
        "active": True,
        "linear": True,
        "perpetual": True,
        "quote_volume_24h": volume,
    }
    values.update(changes)
    return ModeMarketSnapshotEntryV1(**values)


def markets(count, *, equal_volume=False):
    return [
        market(
            f"S{index:04d}/USDT:USDT",
            1000.0 if equal_volume else float(count - index),
        )
        for index in range(count)
    ]


def request(mode=None, due_window_id="window-1"):
    selected = MODES[0] if mode is None else mode
    return build_mode_scan_request(
        mode=selected,
        due_window_id=due_window_id,
    )


def plan(
    mode=None,
    *,
    snapshot=None,
    include_optional_context=False,
):
    return build_mode_scan_execution_plan(
        request=request(mode),
        market_snapshot=(
            [market()] if snapshot is None else snapshot
        ),
        include_optional_context=include_optional_context,
    )


def assert_invalid(call):
    with pytest.raises(
        ModeScanExecutionPlanValidationError,
        match=f"^{ERROR_MESSAGE}$",
    ):
        call()


def reconstruct_plan(value, **changes):
    mapping = value.to_mapping()
    canonical_mapping = canonical_json(mapping)
    assert json.loads(canonical_mapping) == mapping
    mapping.update(changes)
    full = []
    for item in mapping["full_evaluation_symbols"]:
        fetches = tuple(
            ModeTimeframeFetchPlanV1(
                **{
                    **fetch,
                    "cache_key_fields": tuple(
                        fetch["cache_key_fields"]
                    ),
                }
            )
            for fetch in item["candle_fetches"]
        )
        full.append(
            ModeSymbolExecutionPlanV1(
                **{
                    **item,
                    "candle_fetches": fetches,
                }
            )
        )
    mapping["full_evaluation_symbols"] = tuple(full)
    mapping["discovery_symbols"] = tuple(
        mapping["discovery_symbols"]
    )
    mapping["cache_key_fields"] = tuple(
        mapping["cache_key_fields"]
    )
    return ModeScanExecutionPlanV1(**mapping)


PUBLIC_FIELDS = {
    ModeMarketSnapshotEntryV1: (
        "schema_version",
        "canonical_symbol",
        "quote_asset",
        "settle_asset",
        "market_kind",
        "active",
        "linear",
        "perpetual",
        "quote_volume_24h",
    ),
    ModeTimeframeFetchPlanV1: (
        "schema_version",
        "policy_version",
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "timeframe",
        "role",
        "optional_context",
        "closed_candle_limit",
        "raw_fetch_limit",
        "developing_candle_policy",
        "candle_sufficiency_policy",
        "cache_key_fields",
        "cache_key_dynamic_field",
    ),
    ModeSymbolExecutionPlanV1: (
        "schema_version",
        "policy_version",
        "mode",
        "mode_lineage_sha256",
        "canonical_symbol",
        "quote_volume_24h",
        "discovery_rank",
        "full_evaluation_rank",
        "open_interest_history_request_count",
        "candle_fetches",
    ),
    ModeScanExecutionPlanV1: (
        "schema_version",
        "policy_version",
        "mode",
        "due_window_id",
        "mode_lineage_sha256",
        "include_optional_context",
        "market_snapshot_sha256",
        "market_snapshot_count",
        "eligible_market_count",
        "discovery_symbol_count",
        "discovery_truncated_count",
        "full_evaluation_symbol_count",
        "full_evaluation_truncated_count",
        "discovery_symbols",
        "full_evaluation_symbols",
        "discovery_policy_json",
        "discovery_policy_sha256",
        "fetch_budget_json",
        "fetch_budget_sha256",
        "cache_key_fields",
        "cache_key_dynamic_field",
        "live_price_boundary",
        "execution_state",
        "execution_performed",
        "actual_network_call_count",
        "actual_candidate_count",
        "validation_pipeline_invocation_count",
        "retry_count",
        "plan_sha256",
    ),
}


@pytest.mark.parametrize("data_class", PUBLIC_FIELDS)
def test_public_dataclasses_are_frozen_slotted_with_exact_fields(
    data_class,
):
    assert data_class.__dataclass_params__.frozen is True
    assert "__dict__" not in data_class.__dict__
    assert tuple(field.name for field in fields(data_class)) == (
        PUBLIC_FIELDS[data_class]
    )


def test_frozen_instances_reject_normal_mutation():
    entry = market()
    with pytest.raises(FrozenInstanceError):
        entry.active = False
    result = plan()
    with pytest.raises(FrozenInstanceError):
        result.retry_count = 1


def test_public_function_has_exact_keyword_only_signature_and_no_defaults():
    signature = inspect.signature(build_mode_scan_execution_plan)
    assert tuple(signature.parameters) == (
        "request",
        "market_snapshot",
        "include_optional_context",
    )
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty


@pytest.mark.parametrize("mode", MODES)
def test_all_canonical_modes_build_exact_bound_plan(mode):
    result = plan(mode)
    assert result.mode == mode
    assert result.mode_lineage_sha256 == (
        build_mode_audit_lineage(mode).lineage_sha256
    )
    assert result.due_window_id == "window-1"
    assert result.execution_state == EXECUTION_STATE


@pytest.mark.parametrize("attribute", [
    "schema_version",
    "router_policy_version",
    "mode",
    "mode_profile",
    "mode_data_plan",
    "mode_audit_lineage",
])
def test_hostile_request_mutation_fails_closed(attribute):
    value = request()
    replacement = (
        "invalid"
        if attribute not in (
            "mode_profile",
            "mode_data_plan",
            "mode_audit_lineage",
        )
        else object()
    )
    object.__setattr__(value, attribute, replacement)
    assert_invalid(
        lambda: build_mode_scan_execution_plan(
            request=value,
            market_snapshot=[market()],
            include_optional_context=False,
        )
    )


def test_non_exact_request_type_fails_closed():
    class RequestSubclass(type(request())):
        pass

    assert_invalid(
        lambda: build_mode_scan_execution_plan(
            request=object(),
            market_snapshot=[market()],
            include_optional_context=False,
        )
    )


@pytest.mark.parametrize("bad", [
    " ",
    "window/1",
    "x" * 129,
    TextSubclass("window-1"),
    EqualitySpoof(),
])
def test_hostile_due_window_identifier_fails_closed(bad):
    value = request()
    object.__setattr__(value, "due_window_id", bad)
    assert_invalid(
        lambda: build_mode_scan_execution_plan(
            request=value,
            market_snapshot=[market()],
            include_optional_context=False,
        )
    )


@pytest.mark.parametrize("bad", [0, 1, None, "false", EqualitySpoof()])
def test_optional_context_requires_exact_boolean(bad):
    assert_invalid(
        lambda: build_mode_scan_execution_plan(
            request=request(),
            market_snapshot=[market()],
            include_optional_context=bad,
        )
    )


def test_modes_without_optional_context_reject_true():
    modes = [
        profile.mode
        for profile in all_mode_profiles()
        if not profile.optional_context_timeframes
    ]
    assert modes
    for mode in modes:
        assert_invalid(
            lambda mode=mode: plan(
                mode,
                include_optional_context=True,
            )
        )


def test_optional_owner_explicitly_excludes_and_includes_context():
    profile = next(
        item
        for item in all_mode_profiles()
        if item.optional_context_timeframes
    )
    excluded = plan(
        profile.mode,
        include_optional_context=False,
    )
    included = plan(
        profile.mode,
        include_optional_context=True,
    )
    excluded_timeframes = tuple(
        item.timeframe
        for item
        in excluded.full_evaluation_symbols[0].candle_fetches
    )
    included_timeframes = tuple(
        item.timeframe
        for item
        in included.full_evaluation_symbols[0].candle_fetches
    )
    assert not set(profile.optional_context_timeframes).intersection(
        excluded_timeframes
    )
    assert set(profile.optional_context_timeframes).issubset(
        included_timeframes
    )


def test_engine_implementation_has_no_literal_mode_names():
    parsed = ast.parse(ENGINE_PATH.read_text())
    values = {
        node.value
        for node in ast.walk(parsed)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    }
    assert not set(MODES).intersection(values)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("schema_version", "bad"),
        ("canonical_symbol", ""),
        ("canonical_symbol", " BTC/USDT"),
        ("canonical_symbol", "BTC/USDT "),
        ("canonical_symbol", "x" * 129),
        ("canonical_symbol", TextSubclass("BTC/USDT")),
        ("quote_asset", TextSubclass("USDT")),
        ("settle_asset", EqualitySpoof()),
        ("market_kind", TextSubclass("swap")),
        ("active", 1),
        ("linear", 1),
        ("perpetual", 1),
        ("quote_volume_24h", True),
        ("quote_volume_24h", float("nan")),
        ("quote_volume_24h", float("inf")),
        ("quote_volume_24h", float("-inf")),
        ("quote_volume_24h", -1),
    ],
)
def test_snapshot_entry_validation_is_exact(field, bad):
    values = market().to_mapping()
    values[field] = bad
    assert_invalid(lambda: ModeMarketSnapshotEntryV1(**values))


def test_negative_zero_is_normalized_to_positive_zero():
    entry = market(volume=-0.0)
    assert entry.quote_volume_24h == 0.0
    assert math.copysign(1.0, entry.quote_volume_24h) == 1.0


@pytest.mark.parametrize("bad", [None, {}, set(), (market(), object())])
def test_market_snapshot_requires_exact_collection_and_entries(bad):
    assert_invalid(
        lambda: build_mode_scan_execution_plan(
            request=request(),
            market_snapshot=bad,
            include_optional_context=False,
        )
    )


def test_duplicate_market_symbols_rejected_before_filtering():
    snapshot = [
        market("DUP/USDT:USDT", active=True),
        market("DUP/USDT:USDT", active=False),
    ]
    assert_invalid(lambda: plan(snapshot=snapshot))


@pytest.mark.parametrize(
    "change",
    [
        {"active": False},
        {"quote_asset": "USD"},
        {"settle_asset": "USD"},
        {"market_kind": "spot"},
        {"linear": False},
        {"perpetual": False},
    ],
)
def test_ineligible_market_filters_are_exact(change):
    snapshot = [
        market("BAD/USDT:USDT", 9999, **change),
        market("GOOD/USDT:USDT", 1),
    ]
    result = plan(snapshot=snapshot)
    assert result.market_snapshot_count == 2
    assert result.eligible_market_count == 1
    assert result.discovery_symbols == ("GOOD/USDT:USDT",)


def test_volume_descending_and_symbol_ascending_tie_break():
    snapshot = [
        market("Z/USDT:USDT", 10),
        market("B/USDT:USDT", 20),
        market("A/USDT:USDT", 20),
        market("C/USDT:USDT", 5),
    ]
    result = plan(snapshot=snapshot)
    assert result.discovery_symbols == (
        "A/USDT:USDT",
        "B/USDT:USDT",
        "Z/USDT:USDT",
        "C/USDT:USDT",
    )


def test_discovery_and_full_evaluation_bounds_and_counts():
    result = plan(snapshot=markets(600))
    assert result.market_snapshot_count == 600
    assert result.eligible_market_count == 600
    assert result.discovery_symbol_count == 500
    assert result.discovery_truncated_count == 100
    assert result.full_evaluation_symbol_count == 100
    assert result.full_evaluation_truncated_count == 400
    assert len(result.discovery_symbols) == 500
    assert len(result.full_evaluation_symbols) == 100


def test_empty_snapshot_fails_closed_under_committed_positive_budget_bound():
    assert_invalid(lambda: plan(snapshot=[]))


def test_all_ineligible_snapshot_fails_closed():
    assert_invalid(
        lambda: plan(
            snapshot=[market(active=False)]
        )
    )


def test_snapshot_list_and_nested_entry_mutation_cannot_change_plan():
    entry = market()
    snapshot = [entry]
    result = plan(snapshot=snapshot)
    original = result.to_mapping()
    snapshot.append(market("ETH/USDT:USDT", 500))
    object.__setattr__(
        entry,
        "canonical_symbol",
        "MUTATED/USDT:USDT",
    )
    object.__setattr__(entry, "quote_volume_24h", 999999)
    assert result.to_mapping() == original


def test_snapshot_hash_uses_complete_caller_order_before_filtering():
    snapshot = [
        market("B/USDT:USDT", 2),
        market("A/USDT:USDT", 1, active=False),
    ]
    result = plan(snapshot=snapshot)
    expected = digest(
        canonical_json([item.to_mapping() for item in snapshot])
    )
    assert result.market_snapshot_sha256 == expected


@pytest.mark.parametrize("mode", MODES)
def test_deterministic_replay_mapping_and_hashes(mode):
    snapshot = markets(5)
    first = plan(mode, snapshot=snapshot)
    second = plan(mode, snapshot=list(snapshot))
    assert first == second
    assert first.to_mapping() == second.to_mapping()
    assert first.plan_sha256 == second.plan_sha256
    content = first.to_mapping()
    supplied = content.pop("plan_sha256")
    assert supplied == digest(canonical_json(content))


def test_discovery_policy_json_and_hash_are_exact():
    result = plan()
    expected_json = canonical_json(
        build_discovery_universe_policy().to_mapping()
    )
    assert result.discovery_policy_json == expected_json
    assert result.discovery_policy_sha256 == digest(expected_json)
    assert result.discovery_policy_copy() == json.loads(expected_json)


@pytest.mark.parametrize("mode", MODES)
def test_fetch_budget_json_and_hash_are_exact(mode):
    result = plan(mode)
    expected = build_mode_fetch_budget(
        mode=mode,
        symbol_count=1,
        include_optional_context=False,
    )
    expected_json = canonical_json(expected.to_mapping())
    assert result.fetch_budget_json == expected_json
    assert result.fetch_budget_sha256 == digest(expected_json)
    assert result.fetch_budget_copy() == expected.to_mapping()


@pytest.mark.parametrize(
    ("mode_index", "include_optional", "requests", "weight"),
    [
        (0, False, 602, 741),
        (1, False, 602, 741),
        (2, False, 402, 541),
        (2, True, 502, 641),
    ],
)
def test_owner_frozen_n100_budget_values(
    mode_index,
    include_optional,
    requests,
    weight,
):
    mode = MODES[mode_index]
    profile = all_mode_profiles()[mode_index]
    if include_optional and not profile.optional_context_timeframes:
        pytest.fail("invalid owner-frozen fixture")
    result = plan(
        mode,
        snapshot=markets(100),
        include_optional_context=include_optional,
    )
    budget = result.fetch_budget_copy()
    assert budget["total_request_count"] == requests
    assert budget["total_ip_weight"] == weight


@pytest.mark.parametrize("mode", MODES)
def test_required_timeframe_order_roles_and_limits_match_budget(mode):
    result = plan(mode)
    symbol_plan = result.full_evaluation_symbols[0]
    budget = build_mode_fetch_budget(
        mode=mode,
        symbol_count=1,
        include_optional_context=False,
    )
    assert tuple(
        item.timeframe for item in symbol_plan.candle_fetches
    ) == tuple(
        item.timeframe for item in budget.timeframe_fetches
    )
    for planned, expected in zip(
        symbol_plan.candle_fetches,
        budget.timeframe_fetches,
        strict=True,
    ):
        assert planned.role == "+".join(expected.purposes)
        assert planned.closed_candle_limit == (
            expected.closed_candle_count
        )
        assert planned.raw_fetch_limit == expected.raw_fetch_limit
        assert planned.raw_fetch_limit == (
            planned.closed_candle_limit + 1
        )


@pytest.mark.parametrize("mode", MODES)
def test_fetch_policies_cache_contract_and_nested_parity(mode):
    result = plan(mode)
    item = result.full_evaluation_symbols[0]
    assert item.mode == mode
    assert item.canonical_symbol == result.discovery_symbols[0]
    assert item.mode_lineage_sha256 == result.mode_lineage_sha256
    assert item.open_interest_history_request_count == 1
    assert len({
        fetch.timeframe for fetch in item.candle_fetches
    }) == len(item.candle_fetches)
    for fetch in item.candle_fetches:
        assert fetch.mode == mode
        assert fetch.canonical_symbol == item.canonical_symbol
        assert fetch.mode_lineage_sha256 == (
            result.mode_lineage_sha256
        )
        assert fetch.developing_candle_policy == (
            DEVELOPING_CANDLE_POLICY
        )
        assert fetch.candle_sufficiency_policy == (
            CANDLE_SUFFICIENCY_POLICY
        )
        assert fetch.cache_key_fields == CACHE_KEY_FIELDS
        assert fetch.cache_key_dynamic_field == (
            CACHE_KEY_DYNAMIC_FIELD
        )


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("schema_version", "invalid"),
        ("policy_version", "invalid"),
        ("mode", TextSubclass(MODES[0])),
        ("mode_lineage_sha256", "0" * 64),
        ("canonical_symbol", TextSubclass("BTC/USDT:USDT")),
        ("timeframe", TextSubclass("4h")),
        ("role", EqualitySpoof()),
        ("optional_context", 0),
        ("closed_candle_limit", True),
        ("raw_fetch_limit", True),
        ("developing_candle_policy", "invalid"),
        ("candle_sufficiency_policy", "invalid"),
        ("cache_key_fields", list(CACHE_KEY_FIELDS)),
        ("cache_key_dynamic_field", TextSubclass(
            CACHE_KEY_DYNAMIC_FIELD
        )),
    ],
)
def test_timeframe_fetch_plan_direct_validation_is_exact(field, bad):
    item = plan().full_evaluation_symbols[0].candle_fetches[0]
    assert_invalid(lambda: replace(item, **{field: bad}))


def test_timeframe_fetch_raw_limit_must_equal_closed_plus_one():
    item = plan().full_evaluation_symbols[0].candle_fetches[0]
    assert_invalid(
        lambda: replace(
            item,
            raw_fetch_limit=item.closed_candle_limit + 2,
        )
    )


def test_direct_low_tier_timeframe_fetch_rejects_noncanonical_plus_one_pairs():
    item = next(
        fetch
        for fetch in plan().full_evaluation_symbols[0].candle_fetches
        if fetch.closed_candle_limit == 50
    )
    assert (
        item.closed_candle_limit,
        item.raw_fetch_limit,
    ) == (50, 51)
    for closed_limit, raw_limit in ((51, 52), (300, 301)):
        assert_invalid(
            lambda: replace(
                item,
                closed_candle_limit=closed_limit,
                raw_fetch_limit=raw_limit,
            )
        )


def test_direct_high_tier_timeframe_fetch_rejects_noncanonical_plus_one_pairs():
    item = next(
        fetch
        for fetch in plan().full_evaluation_symbols[0].candle_fetches
        if fetch.closed_candle_limit == 300
    )
    assert (
        item.closed_candle_limit,
        item.raw_fetch_limit,
    ) == (300, 301)
    for closed_limit, raw_limit in ((50, 51), (299, 300)):
        assert_invalid(
            lambda: replace(
                item,
                closed_candle_limit=closed_limit,
                raw_fetch_limit=raw_limit,
            )
        )


def test_contiguous_ranks_and_full_evaluation_exact_prefix():
    result = plan(snapshot=markets(120))
    assert tuple(
        item.discovery_rank
        for item in result.full_evaluation_symbols
    ) == tuple(range(1, 101))
    assert tuple(
        item.full_evaluation_rank
        for item in result.full_evaluation_symbols
    ) == tuple(range(1, 101))
    assert tuple(
        item.canonical_symbol
        for item in result.full_evaluation_symbols
    ) == result.discovery_symbols[:100]


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("market_snapshot_count", True),
        ("eligible_market_count", True),
        ("discovery_symbol_count", True),
        ("discovery_truncated_count", True),
        ("full_evaluation_symbol_count", True),
        ("full_evaluation_truncated_count", True),
    ],
)
def test_outer_count_fields_reject_bool(field, bad):
    result = plan()
    assert_invalid(lambda: replace(result, **{field: bad}))


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("eligible_market_count", 0),
        ("discovery_symbol_count", 2),
        ("discovery_truncated_count", 1),
        ("full_evaluation_symbol_count", 2),
        ("full_evaluation_truncated_count", 1),
    ],
)
def test_outer_count_reconciliation_fails_closed(field, bad):
    result = plan()
    assert_invalid(lambda: replace(result, **{field: bad}))


def test_full_evaluation_prefix_mismatch_rejected():
    result = plan(snapshot=markets(2))
    assert_invalid(
        lambda: replace(
            result,
            discovery_symbols=tuple(
                reversed(result.discovery_symbols)
            ),
        )
    )


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("discovery_rank", True),
        ("full_evaluation_rank", True),
        ("open_interest_history_request_count", True),
        ("open_interest_history_request_count", 0),
        ("quote_volume_24h", True),
    ],
)
def test_symbol_plan_rejects_bool_and_incorrect_numeric_fields(
    field,
    bad,
):
    item = plan().full_evaluation_symbols[0]
    assert_invalid(lambda: replace(item, **{field: bad}))


def test_duplicate_nested_symbol_rejected():
    result = plan(snapshot=markets(2))
    second = result.full_evaluation_symbols[1]
    object.__setattr__(
        second,
        "canonical_symbol",
        result.full_evaluation_symbols[0].canonical_symbol,
    )
    assert_invalid(
        lambda: replace(
            result,
            full_evaluation_symbols=(
                result.full_evaluation_symbols[0],
                second,
            ),
        )
    )


@pytest.mark.parametrize(
    "field",
    ["discovery_rank", "full_evaluation_rank"],
)
def test_duplicate_nested_rank_rejected(field):
    result = plan(snapshot=markets(2))
    second = result.full_evaluation_symbols[1]
    object.__setattr__(second, field, 1)
    assert_invalid(
        lambda: replace(
            result,
            full_evaluation_symbols=(
                result.full_evaluation_symbols[0],
                second,
            ),
        )
    )


def test_duplicate_nested_timeframe_rejected():
    result = plan()
    symbol_plan = result.full_evaluation_symbols[0]
    first, second, *remaining = symbol_plan.candle_fetches
    object.__setattr__(second, "timeframe", first.timeframe)
    assert_invalid(
        lambda: replace(
            symbol_plan,
            candle_fetches=(first, second, *remaining),
        )
    )


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("discovery_policy_json", "{}"),
        ("fetch_budget_json", "{}"),
        ("discovery_policy_json", '{"x":NaN}'),
        ("fetch_budget_json", "[]"),
    ],
)
def test_malformed_policy_or_budget_json_rejected(field, bad):
    result = plan()
    assert_invalid(lambda: replace(result, **{field: bad}))


@pytest.mark.parametrize(
    "field",
    ["discovery_policy_sha256", "fetch_budget_sha256"],
)
def test_policy_and_budget_hash_mismatch_rejected(field):
    result = plan()
    assert_invalid(lambda: replace(result, **{field: "0" * 64}))


def test_plan_hash_mismatch_rejected():
    result = plan()
    assert_invalid(
        lambda: replace(result, plan_sha256="0" * 64)
    )


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("execution_performed", True),
        ("execution_performed", 0),
        ("actual_network_call_count", 1),
        ("actual_network_call_count", False),
        ("actual_candidate_count", 1),
        ("validation_pipeline_invocation_count", 1),
        ("retry_count", 1),
    ],
)
def test_execution_and_retry_invariants_fail_closed(field, bad):
    result = plan()
    assert_invalid(lambda: replace(result, **{field: bad}))


def test_plan_only_zero_execution_and_separate_live_price():
    result = plan()
    assert result.execution_performed is False
    assert result.actual_network_call_count == 0
    assert result.actual_candidate_count == 0
    assert result.validation_pipeline_invocation_count == 0
    assert result.retry_count == 0
    assert result.live_price_boundary == LIVE_PRICE_BOUNDARY


def test_plan_contains_no_routed_candidate_payload():
    mapping = plan().to_mapping()
    serialized = canonical_json(mapping)
    assert "candidate_id" not in serialized
    assert "payload_json" not in serialized
    assert "payload_sha256" not in serialized


def test_mapping_and_payload_copies_are_detached():
    result = plan(snapshot=markets(2))
    mapping = result.to_mapping()
    policy = result.discovery_policy_copy()
    budget = result.fetch_budget_copy()
    mapping["discovery_symbols"].clear()
    mapping["full_evaluation_symbols"][0][
        "candle_fetches"
    ].clear()
    policy["max_symbols"] = 1
    budget["timeframe_fetches"].clear()
    assert result.discovery_symbol_count == 2
    assert result.full_evaluation_symbols[0].candle_fetches
    assert result.discovery_policy_copy()["max_symbols"] == 500
    assert result.fetch_budget_copy()["timeframe_fetches"]


def test_public_versions_and_policy_constants_are_exact():
    assert MODE_SCAN_EXECUTION_PLAN_POLICY_VERSION.endswith("-v1")
    assert MODE_MARKET_SNAPSHOT_ENTRY_SCHEMA_VERSION.endswith("-v1")
    assert MODE_TIMEFRAME_FETCH_PLAN_SCHEMA_VERSION.endswith("-v1")
    assert MODE_SYMBOL_EXECUTION_PLAN_SCHEMA_VERSION.endswith("-v1")
    assert MODE_SCAN_EXECUTION_PLAN_SCHEMA_VERSION.endswith("-v1")
    assert CACHE_KEY_FIELDS == (
        "mode",
        "canonical_symbol",
        "timeframe",
        "closed_candle_close_at",
        "mode_data_plan_version",
    )
    assert CACHE_KEY_DYNAMIC_FIELD == "closed_candle_close_at"


def test_engine_imports_and_calls_are_pure_and_detached():
    parsed = ast.parse(ENGINE_PATH.read_text())
    imports = set()
    for node in parsed.body:
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module)
    assert imports == {
        "__future__",
        "dataclasses",
        "hashlib",
        "json",
        "math",
        "re",
        "typing",
        "engine.mode_data_plan_v1",
        "engine.mode_fetch_budget_cadence_v1",
        "engine.mode_profile_v1",
        "engine.mode_router_v1",
    }
    source = ENGINE_PATH.read_text()
    prohibited = {
        "requests",
        "ccxt",
        "socket",
        "subprocess",
        "urllib",
        "scanner",
        "provider",
        "telegram",
        "exchange",
        "service",
        "run_mode_validation_pipeline",
        "route_mode_scan(",
    }
    lowered = source.casefold()
    assert not {
        item for item in prohibited
        if item.casefold() in lowered
    }


def test_fetch_and_discovery_builders_have_one_source_call_site_each():
    parsed = ast.parse(ENGINE_PATH.read_text())
    calls = [
        node.func.id
        for node in ast.walk(parsed)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    ]
    assert calls.count("build_mode_fetch_budget") == 1
    assert calls.count("build_discovery_universe_policy") == 1


def test_reconstructing_valid_plan_preserves_exact_mapping():
    result = plan(snapshot=markets(3))
    rebuilt = reconstruct_plan(result)
    assert rebuilt == result
    assert rebuilt.to_mapping() == result.to_mapping()
