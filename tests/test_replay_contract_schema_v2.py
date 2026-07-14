import ast
import copy
import importlib
import json
import math
import re
from pathlib import Path

import pytest

from engine.replay_contract_v4 import (
    REPLAY_BUNDLE_SCHEMA_VERSION,
    ReplayBundleV4,
    ReplayBundleValidationError,
    calculate_replay_bundle_hash_v4,
    canonicalize_replay_bundle_v4,
    derive_replay_fixture_id_v4,
    derive_replay_id_v4,
    load_replay_bundle_v4,
    validate_replay_bundle_v4,
)


FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "replay_v4"
V1_FIXTURE_PATH = FIXTURE_DIRECTORY / "valid_bundle_v1.json"
V2_FIXTURE_PATH = FIXTURE_DIRECTORY / "valid_bundle_v2.json"

SCANNER_KEYS = {
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
GOLDEN_ZONE_KEYS = {
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
GOLDEN_LEVEL_KEYS = {"-0.27", "0.0", "0.5", "0.618", "0.786", "1.0"}
OI_KEYS = {
    "current_oi",
    "previous_oi",
    "oi_change_pct",
    "oi_score",
    "data_status",
}
VALIDATION_KEYS = {
    "symbol",
    "status",
    "false_breakout_risk",
    "confluence",
    "reason_code",
}
USAGE_KEYS = {
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cache_hit_tokens",
    "cache_miss_tokens",
}


def _raw_v2():
    return json.loads(V2_FIXTURE_PATH.read_text(encoding="utf-8"))


def _raw_v1():
    return json.loads(V1_FIXTURE_PATH.read_text(encoding="utf-8"))


def _validated_v2():
    return validate_replay_bundle_v4(_raw_v2())


def _assert_invalid(mutator):
    candidate = _raw_v2()
    mutator(candidate)
    with pytest.raises(ReplayBundleValidationError):
        validate_replay_bundle_v4(candidate)


def _validations(bundle):
    return json.loads(bundle["recorded_validator_response"]["content"])[
        "validations"
    ]


def _replace_validations(bundle, validations):
    bundle["recorded_validator_response"]["content"] = json.dumps(
        {"validations": validations},
        sort_keys=True,
        separators=(",", ":"),
    )


def _reverse_mappings(value):
    if isinstance(value, dict):
        return {
            key: _reverse_mappings(value[key])
            for key in reversed(list(value))
        }
    if isinstance(value, list):
        return [_reverse_mappings(item) for item in value]
    return value


def test_schema_v2_is_the_only_public_executable_version():
    assert REPLAY_BUNDLE_SCHEMA_VERSION == 2
    bundle = _validated_v2()

    assert isinstance(bundle, ReplayBundleV4)
    assert bundle.schema_version == 2


def test_schema_v1_is_legacy_and_rejected_without_mutation():
    source_before = V1_FIXTURE_PATH.read_bytes()

    with pytest.raises(ReplayBundleValidationError):
        validate_replay_bundle_v4(_raw_v1())
    with pytest.raises(ReplayBundleValidationError):
        load_replay_bundle_v4(V1_FIXTURE_PATH)

    assert V1_FIXTURE_PATH.read_bytes() == source_before


@pytest.mark.parametrize("version", [0, 1, 3, -1, True, "2", None])
def test_unsupported_or_mistyped_schema_versions_fail_closed(version):
    _assert_invalid(lambda bundle: bundle.update(schema_version=version))


def test_missing_schema_version_fails_closed():
    _assert_invalid(lambda bundle: bundle.pop("schema_version"))


def test_canonical_schema_v2_retains_version_and_complete_content():
    canonical = canonicalize_replay_bundle_v4(_raw_v2())
    payload = json.loads(canonical)

    assert payload["schema_version"] == 2
    assert "recorded_open_interest" in payload
    assert set(payload["scanner_results"][0]) == SCANNER_KEYS


def test_valid_v2_fixture_exposes_complete_recorded_boundary():
    bundle = _validated_v2()
    scanner_symbols = {row["symbol"] for row in bundle.scanner_results}

    assert scanner_symbols == {"BTC/USDT:USDT", "ETH/USDT:USDT"}
    assert set(bundle.recorded_open_interest) == scanner_symbols
    assert set(bundle.recorded_validator_usage) == USAGE_KEYS
    assert {
        row["symbol"]
        for row in json.loads(bundle.recorded_validator_response["content"])[
            "validations"
        ]
    } == scanner_symbols


@pytest.mark.parametrize("field", sorted(SCANNER_KEYS))
def test_every_complete_scanner_field_is_required(field):
    _assert_invalid(lambda bundle: bundle["scanner_results"][0].pop(field))


def test_scanner_rows_reject_unknown_and_null_fields():
    _assert_invalid(
        lambda bundle: bundle["scanner_results"][0].update(unexpected="x")
    )
    _assert_invalid(
        lambda bundle: bundle["scanner_results"][0].update(reference_price=None)
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reference_price", True),
        ("reference_price", math.inf),
        ("score", math.nan),
        ("volume_ratio", "1.6"),
        ("volume_ratio", False),
        ("trend", "RANGING"),
        ("bos", 1),
        ("choch", 0),
        ("volume_v2_status", "LIVE_FALLBACK"),
    ],
)
def test_scanner_pipeline_fields_are_strictly_typed(field, value):
    _assert_invalid(
        lambda bundle: bundle["scanner_results"][0].update({field: value})
    )


@pytest.mark.parametrize(
    "timestamp",
    ["2026-07-13T08:00:00", "not-a-time", 123, None],
)
def test_reference_candle_timestamp_is_timezone_aware(timestamp):
    _assert_invalid(
        lambda bundle: bundle["scanner_results"][0].update(
            reference_candle_at=timestamp
        )
    )


def test_scanner_symbols_are_unique_and_equal_scores_use_symbol_tie_breaker():
    duplicate = _raw_v2()
    duplicate["scanner_results"][1]["symbol"] = "BTC/USDT:USDT"
    with pytest.raises(ReplayBundleValidationError):
        validate_replay_bundle_v4(duplicate)

    tied = _raw_v2()
    for row in tied["scanner_results"]:
        row["score"] = 90.0
    tied["scanner_results"].reverse()
    validated = validate_replay_bundle_v4(tied)
    assert [row["symbol"] for row in validated.scanner_results] == [
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
    ]


def test_valid_golden_zone_retains_complete_production_shape():
    zone = _validated_v2().scanner_results[0]["golden_zone"]

    assert set(zone) == GOLDEN_ZONE_KEYS
    assert set(zone["levels"]) == GOLDEN_LEVEL_KEYS
    assert set(zone["entry_zone"]) == {
        "level_from",
        "level_to",
        "price_low",
        "price_high",
    }
    assert set(zone["take_profit"]) == {"level", "price"}
    assert set(zone["stop_loss"]) == {"level", "price"}


@pytest.mark.parametrize(
    ("section", "field"),
    [
        (None, "swing_low_at"),
        (None, "swing_high_index"),
        ("levels", "0.786"),
        ("entry_zone", "price_low"),
        ("take_profit", "level"),
        ("stop_loss", "price"),
    ],
)
def test_golden_zone_missing_nested_fields_fail_closed(section, field):
    def mutate(bundle):
        zone = bundle["scanner_results"][0]["golden_zone"]
        (zone if section is None else zone[section]).pop(field)

    _assert_invalid(mutate)


@pytest.mark.parametrize(
    "section",
    [None, "levels", "entry_zone", "take_profit", "stop_loss"],
)
def test_golden_zone_unknown_nested_fields_fail_closed(section):
    def mutate(bundle):
        zone = bundle["scanner_results"][0]["golden_zone"]
        (zone if section is None else zone[section])["unexpected"] = 1

    _assert_invalid(mutate)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda zone: zone.update(swing_low=True),
        lambda zone: zone.update(swing_high=math.inf),
        lambda zone: zone.update(swing_low_index=False),
        lambda zone: zone["levels"].update({"0.5": math.nan}),
        lambda zone: zone["entry_zone"].update(price_low=True),
        lambda zone: zone["take_profit"].update(price=math.inf),
        lambda zone: zone["stop_loss"].update(level=False),
    ],
)
def test_golden_zone_nested_numbers_are_finite_and_not_boolean(mutator):
    _assert_invalid(
        lambda bundle: mutator(bundle["scanner_results"][0]["golden_zone"])
    )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda zone: zone.update(swing_high=zone["swing_low"]),
        lambda zone: zone["entry_zone"].update(
            price_low=zone["entry_zone"]["price_high"] + 1
        ),
        lambda zone: zone.update(direction="BEARISH"),
        lambda zone: zone.update(swing_low_at="2026-07-12T00:00:00"),
    ],
)
def test_golden_zone_impossible_or_inconsistent_values_fail_closed(mutator):
    _assert_invalid(
        lambda bundle: mutator(bundle["scanner_results"][0]["golden_zone"])
    )


def test_golden_zone_mapping_order_is_canonical_and_changes_are_semantic():
    original = _raw_v2()
    reordered = _reverse_mappings(original)
    assert canonicalize_replay_bundle_v4(original) == (
        canonicalize_replay_bundle_v4(reordered)
    )

    changed = copy.deepcopy(original)
    zone = changed["scanner_results"][0]["golden_zone"]
    zone["swing_low_at"] = "2026-07-11T20:00:00+00:00"
    assert calculate_replay_bundle_hash_v4(changed) != (
        calculate_replay_bundle_hash_v4(original)
    )
    assert derive_replay_id_v4(changed) != derive_replay_id_v4(original)


def test_recorded_oi_has_exact_scanner_symbol_coverage():
    _assert_invalid(lambda bundle: bundle.pop("recorded_open_interest"))
    _assert_invalid(lambda bundle: bundle.update(recorded_open_interest={}))
    _assert_invalid(
        lambda bundle: bundle["recorded_open_interest"].pop("ETH/USDT:USDT")
    )
    _assert_invalid(
        lambda bundle: bundle["recorded_open_interest"].update(
            {"XRP/USDT:USDT": copy.deepcopy(
                bundle["recorded_open_interest"]["BTC/USDT:USDT"]
            )}
        )
    )


@pytest.mark.parametrize("field", sorted(OI_KEYS))
def test_recorded_oi_exact_provider_fields_are_required(field):
    _assert_invalid(
        lambda bundle: bundle["recorded_open_interest"][
            "BTC/USDT:USDT"
        ].pop(field)
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_oi", True),
        ("previous_oi", math.inf),
        ("oi_change_pct", math.nan),
        ("oi_score", False),
        ("data_status", "LIVE_FALLBACK"),
    ],
)
def test_recorded_oi_values_are_finite_and_provider_compatible(field, value):
    _assert_invalid(
        lambda bundle: bundle["recorded_open_interest"][
            "BTC/USDT:USDT"
        ].update({field: value})
    )


def test_recorded_oi_rejects_unknown_or_live_provider_fields():
    for field in ("participation", "provider_url", "endpoint", "api_key"):
        _assert_invalid(
            lambda bundle, field=field: bundle["recorded_open_interest"][
                "BTC/USDT:USDT"
            ].update({field: "forbidden"})
        )


def test_recorded_validator_response_covers_exact_scanner_candidates():
    bundle = _raw_v2()
    assert set(bundle["recorded_validator_response"]) == {"content"}
    assert {row["symbol"] for row in _validations(bundle)} == {
        row["symbol"] for row in bundle["scanner_results"]
    }
    assert all(set(row) == VALIDATION_KEYS for row in _validations(bundle))
    _validated_v2()


@pytest.mark.parametrize(
    "content",
    [
        "{",
        "[]",
        "{}",
        '{"final_top5":[]}',
        '{"validations":"not-a-list"}',
    ],
)
def test_validator_content_must_be_raw_complete_provider_json(content):
    _assert_invalid(
        lambda bundle: bundle.update(
            recorded_validator_response={"content": content}
        )
    )


def test_validator_candidate_coverage_rejects_duplicate_missing_and_extra():
    duplicate = _raw_v2()
    rows = _validations(duplicate)
    _replace_validations(duplicate, [rows[0], copy.deepcopy(rows[0])])
    with pytest.raises(ReplayBundleValidationError):
        validate_replay_bundle_v4(duplicate)

    missing = _raw_v2()
    _replace_validations(missing, _validations(missing)[:1])
    with pytest.raises(ReplayBundleValidationError):
        validate_replay_bundle_v4(missing)

    extra = _raw_v2()
    rows = _validations(extra)
    added = {**rows[0], "symbol": "XRP/USDT:USDT"}
    _replace_validations(extra, [*rows, added])
    with pytest.raises(ReplayBundleValidationError):
        validate_replay_bundle_v4(extra)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda row: row.pop("reason_code"),
        lambda row: row.update(unexpected="x"),
        lambda row: row.update(status="UNKNOWN"),
        lambda row: row.update(false_breakout_risk="EXTREME"),
        lambda row: row.update(confluence="NONE"),
        lambda row: row.update(reason_code=""),
    ],
)
def test_validator_entries_are_strict_production_control_inputs(mutator):
    def mutate(bundle):
        rows = _validations(bundle)
        mutator(rows[0])
        _replace_validations(bundle, rows)

    _assert_invalid(mutate)


def test_complete_validator_usage_is_retained():
    usage = _validated_v2().recorded_validator_usage

    assert set(usage) == USAGE_KEYS
    assert usage["total_tokens"] == (
        usage["prompt_tokens"] + usage["completion_tokens"]
    )


@pytest.mark.parametrize("field", sorted(USAGE_KEYS))
def test_every_validator_usage_field_is_required(field):
    _assert_invalid(lambda bundle: bundle["recorded_validator_usage"].pop(field))


@pytest.mark.parametrize("field", sorted(USAGE_KEYS))
def test_validator_usage_rejects_boolean_and_negative_values(field):
    _assert_invalid(
        lambda bundle: bundle["recorded_validator_usage"].update({field: True})
    )
    _assert_invalid(
        lambda bundle: bundle["recorded_validator_usage"].update({field: -1})
    )


def test_validator_usage_rejects_unknown_fields_and_inconsistent_total():
    _assert_invalid(
        lambda bundle: bundle["recorded_validator_usage"].update(extra=0)
    )
    _assert_invalid(
        lambda bundle: bundle["recorded_validator_usage"].update(
            total_tokens=151
        )
    )


def test_usage_cache_metadata_participates_in_canonical_hash():
    original = _raw_v2()
    changed = copy.deepcopy(original)
    changed["recorded_validator_usage"]["cache_hit_tokens"] += 1

    assert calculate_replay_bundle_hash_v4(changed) != (
        calculate_replay_bundle_hash_v4(original)
    )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: bundle["pre_delivery_closed_candles"].pop(
            "ETH/USDT:USDT"
        ),
        lambda bundle: bundle["pre_delivery_closed_candles"].update(
            {"XRP/USDT:USDT": []}
        ),
        lambda bundle: bundle["pre_delivery_closed_candles"][
            "BTC/USDT:USDT"
        ].clear(),
        lambda bundle: bundle["pre_delivery_closed_candles"][
            "BTC/USDT:USDT"
        ][0].update(volume=-1),
        lambda bundle: bundle["pre_delivery_closed_candles"][
            "BTC/USDT:USDT"
        ][0].update(close=math.inf),
        lambda bundle: bundle["pre_delivery_closed_candles"][
            "BTC/USDT:USDT"
        ][0].update(high=True),
        lambda bundle: bundle["pre_delivery_closed_candles"][
            "BTC/USDT:USDT"
        ][1].update(open_time="2026-07-13T12:00:00+00:00"),
        lambda bundle: bundle["pre_delivery_closed_candles"][
            "BTC/USDT:USDT"
        ][0].update(provider_url="https://example.invalid"),
    ],
)
def test_recorded_candles_are_complete_ordered_and_network_free(mutator):
    _assert_invalid(mutator)


def test_v2_validated_contract_is_deeply_immutable_and_source_is_unchanged():
    source = _raw_v2()
    source_before = copy.deepcopy(source)
    bundle = validate_replay_bundle_v4(source)

    assert source == source_before
    mutations = [
        lambda: setattr(bundle, "schema_version", 3),
        lambda: bundle.scanner_results[0].__setitem__("score", 0),
        lambda: bundle.scanner_results[0]["golden_zone"]["levels"].__setitem__(
            "0.5", 0
        ),
        lambda: bundle.recorded_open_interest.__setitem__("X", {}),
        lambda: bundle.recorded_validator_response.__setitem__("content", "{}"),
        lambda: bundle.recorded_validator_usage.__setitem__("total_tokens", 0),
        lambda: bundle.pre_delivery_closed_candles[
            "BTC/USDT:USDT"
        ][0].__setitem__("close", 0),
    ]
    for mutation in mutations:
        with pytest.raises((AttributeError, TypeError)):
            mutation()


def test_canonicalization_is_stable_and_does_not_mutate_source():
    original = _raw_v2()
    original_before = copy.deepcopy(original)
    reordered = _reverse_mappings(original)

    canonical = canonicalize_replay_bundle_v4(original)
    assert canonical == canonicalize_replay_bundle_v4(reordered)
    assert original == original_before
    assert isinstance(canonical, bytes)
    assert canonical.decode("utf-8")
    assert b"\n" not in canonical
    assert b": " not in canonical


def test_validator_entry_order_is_normalized_to_scanner_order():
    original = _raw_v2()
    reversed_response = copy.deepcopy(original)
    _replace_validations(
        reversed_response,
        list(reversed(_validations(reversed_response))),
    )

    assert canonicalize_replay_bundle_v4(original) == (
        canonicalize_replay_bundle_v4(reversed_response)
    )


def test_v2_hash_and_identity_are_stable_distinct_and_content_derived():
    first = _raw_v2()
    second = copy.deepcopy(first)
    digest = calculate_replay_bundle_hash_v4(first)
    fixture_id = derive_replay_fixture_id_v4(first)
    replay_id = derive_replay_id_v4(first)

    assert digest == calculate_replay_bundle_hash_v4(second)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert fixture_id == derive_replay_fixture_id_v4(second)
    assert replay_id == derive_replay_id_v4(second)
    assert fixture_id != replay_id


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: bundle["scanner_results"][0].update(score=92.0),
        lambda bundle: bundle["scanner_results"][0]["golden_zone"].update(
            swing_low_at="2026-07-11T20:00:00+00:00"
        ),
        lambda bundle: bundle["recorded_open_interest"][
            "BTC/USDT:USDT"
        ].update(current_oi=1006.0),
        lambda bundle: _replace_validations(
            bundle,
            [
                {
                    **row,
                    "status": "CONFLICT",
                    "false_breakout_risk": "MEDIUM",
                    "confluence": "MODERATE",
                    "reason_code": "MULTIPLE_CONFLICTS",
                }
                if row["symbol"] == "BTC/USDT:USDT"
                else row
                for row in _validations(bundle)
            ],
        ),
        lambda bundle: bundle["recorded_validator_usage"].update(
            cache_miss_tokens=81
        ),
        lambda bundle: bundle["pre_delivery_closed_candles"][
            "BTC/USDT:USDT"
        ][0].update(volume=1101.0),
        lambda bundle: bundle.update(
            fixed_execution_time="2026-07-14T10:06:00+00:00"
        ),
        lambda bundle: bundle["execution_configuration"].update(limit=101),
    ],
)
def test_every_v2_semantic_domain_changes_hash_and_replay_identity(mutator):
    original = _raw_v2()
    changed = copy.deepcopy(original)
    mutator(changed)

    assert calculate_replay_bundle_hash_v4(changed) != (
        calculate_replay_bundle_hash_v4(original)
    )
    assert derive_replay_id_v4(changed) != derive_replay_id_v4(original)


@pytest.mark.parametrize(
    "field",
    [
        "api_key",
        "secret",
        "password",
        "token",
        "authorization",
        "TELEGRAM_BOT_TOKEN",
        "endpoint",
        "base_url",
        "provider_url",
        "production_path",
        "production_output_path",
        "quota_state_path",
        "worker_state_path",
        "latest_path",
    ],
)
def test_structured_secret_network_and_production_path_keys_are_rejected(field):
    _assert_invalid(
        lambda bundle: bundle["recorded_open_interest"][
            "BTC/USDT:USDT"
        ].update({field: "forbidden"})
    )


def test_harmless_validator_prose_is_not_scanned_for_secret_words():
    bundle = _raw_v2()
    old_symbol = "BTC/USDT:USDT"
    harmless_symbol = "TOKEN/USDT:USDT"
    bundle["scanner_results"][0]["symbol"] = harmless_symbol
    bundle["recorded_open_interest"][harmless_symbol] = (
        bundle["recorded_open_interest"].pop(old_symbol)
    )
    bundle["pre_delivery_closed_candles"][harmless_symbol] = (
        bundle["pre_delivery_closed_candles"].pop(old_symbol)
    )
    rows = _validations(bundle)
    rows[0]["symbol"] = harmless_symbol
    _replace_validations(bundle, rows)

    validate_replay_bundle_v4(bundle)


def test_v2_file_load_preserves_bytes_and_creates_no_output(tmp_path):
    source = tmp_path / "bundle-v2.json"
    source.write_bytes(V2_FIXTURE_PATH.read_bytes())
    source_before = source.read_bytes()

    loaded = load_replay_bundle_v4(source)

    assert isinstance(loaded, ReplayBundleV4)
    assert source.read_bytes() == source_before
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("payload", ["{", "[]", "null"])
def test_v2_file_loading_fails_closed_for_invalid_json(payload, tmp_path):
    source = tmp_path / "invalid.json"
    source.write_text(payload, encoding="utf-8")

    with pytest.raises(ReplayBundleValidationError):
        load_replay_bundle_v4(source)


def test_v2_loading_rejects_missing_file_and_directory(tmp_path):
    with pytest.raises(ReplayBundleValidationError):
        load_replay_bundle_v4(tmp_path / "missing.json")

    directory = tmp_path / "bundle-directory"
    directory.mkdir()
    with pytest.raises(ReplayBundleValidationError):
        load_replay_bundle_v4(directory)


def test_import_remains_standard_library_only_and_side_effect_free(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("engine.replay_contract_v4")
    importlib.reload(module)

    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.casefold() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.casefold())
    forbidden = (
        "requests",
        "socket",
        "ccxt",
        "openai",
        "deepseek",
        "telegram",
        "engine.master_engine_v4",
        "engine.stateful_worker_v4",
        "engine.quota_slot_worker_v4",
    )
    assert all(name not in imports for name in forbidden)
    assert list(tmp_path.iterdir()) == []
