import copy
import importlib
import json
import math
from pathlib import Path

import pytest

from engine.replay_contract_v4 import (
    REPLAY_BUNDLE_SCHEMA_VERSION,
    ReplayBundleValidationError,
    ReplayBundleV4,
    calculate_replay_bundle_hash_v4,
    canonicalize_replay_bundle_v4,
    derive_replay_fixture_id_v4,
    derive_replay_id_v4,
    load_replay_bundle_v4,
    validate_replay_bundle_v4,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "replay_v4"
    / "valid_bundle_v1.json"
)


def _raw_bundle():
    return json.loads(FIXTURE_PATH.read_text())


def _validated_bundle():
    return validate_replay_bundle_v4(_raw_bundle())


def _assert_invalid(mutator):
    candidate = _raw_bundle()
    mutator(candidate)
    with pytest.raises(ReplayBundleValidationError):
        validate_replay_bundle_v4(candidate)


def test_public_schema_version_and_valid_bundle_contract():
    assert REPLAY_BUNDLE_SCHEMA_VERSION == 1
    bundle = _validated_bundle()

    assert isinstance(bundle, ReplayBundleV4)
    assert bundle.schema_version == 1
    assert bundle.source_commit == _raw_bundle()["source_commit"]
    assert bundle.scanner_results
    assert bundle.recorded_validator_response
    assert bundle.pre_delivery_closed_candles


def test_valid_bundle_preserves_source_bytes_and_returns_immutable_contract():
    source_before = FIXTURE_PATH.read_bytes()
    bundle = load_replay_bundle_v4(FIXTURE_PATH)

    assert FIXTURE_PATH.read_bytes() == source_before
    with pytest.raises((AttributeError, TypeError)):
        bundle.source_commit = "changed"
    with pytest.raises((AttributeError, TypeError)):
        bundle.scanner_results[0]["score"] = 0


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value.pop("schema_version"),
        lambda value: value.update(schema_version=2),
        lambda value: value.update(schema_version=True),
        lambda value: value.update(schema_version="1"),
        lambda value: value.update(unexpected="field"),
        lambda value: value.pop("scanner_results"),
        lambda value: value.update(recorded_at=None),
        lambda value: value.update(fixed_execution_time=None),
    ],
)
def test_invalid_top_level_schema_values_fail_closed(mutator):
    _assert_invalid(mutator)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_commit", ""),
        ("source_commit", "not-a-commit"),
        ("source_commit", 123),
        ("recorded_at", "2026-07-14T10:00:00"),
        ("fixed_execution_time", "not-a-timestamp"),
    ],
)
def test_source_metadata_and_timestamps_are_strict(field, value):
    _assert_invalid(lambda bundle: bundle.update({field: value}))


def test_identity_and_hash_derivation_are_deterministic_and_content_based():
    first_raw = _raw_bundle()
    second_raw = copy.deepcopy(first_raw)
    first = _validated_bundle()
    second = validate_replay_bundle_v4(second_raw)

    assert derive_replay_fixture_id_v4(first_raw) == (
        derive_replay_fixture_id_v4(second_raw)
    )
    assert derive_replay_id_v4(first) == derive_replay_id_v4(second)
    assert calculate_replay_bundle_hash_v4(first) == (
        calculate_replay_bundle_hash_v4(second)
    )

    changed = copy.deepcopy(first_raw)
    changed["scanner_results"][0]["score"] += 1
    changed_bundle = validate_replay_bundle_v4(changed)

    assert derive_replay_fixture_id_v4(changed) != (
        derive_replay_fixture_id_v4(first_raw)
    )
    assert calculate_replay_bundle_hash_v4(changed_bundle) != (
        calculate_replay_bundle_hash_v4(first)
    )


def test_execution_configuration_is_strictly_typed():
    _assert_invalid(lambda bundle: bundle.pop("execution_configuration"))
    _assert_invalid(
        lambda bundle: bundle.update(execution_configuration=[])
    )
    _assert_invalid(
        lambda bundle: bundle["execution_configuration"].pop("timeframe")
    )
    _assert_invalid(
        lambda bundle: bundle["execution_configuration"].update(timeframe=" ")
    )
    _assert_invalid(
        lambda bundle: bundle["execution_configuration"].update(lookback=0)
    )
    _assert_invalid(
        lambda bundle: bundle["execution_configuration"].update(limit=True)
    )
    _assert_invalid(
        lambda bundle: bundle["execution_configuration"].update(extra=1)
    )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: bundle.update(scanner_results={}),
        lambda bundle: bundle.update(scanner_results=[]),
        lambda bundle: bundle["scanner_results"].__setitem__(0, []),
        lambda bundle: bundle["scanner_results"][0].pop("symbol"),
        lambda bundle: bundle["scanner_results"][0].update(symbol=" "),
        lambda bundle: bundle["scanner_results"][0].update(direction="SIDEWAYS"),
        lambda bundle: bundle["scanner_results"][0].update(score=True),
        lambda bundle: bundle["scanner_results"][0].update(score="91.5"),
        lambda bundle: bundle["scanner_results"][0].update(entry=math.nan),
    ],
)
def test_scanner_result_rows_fail_closed_when_malformed(mutator):
    _assert_invalid(mutator)


def test_scanner_result_equal_scores_use_symbol_tie_breaker():
    bundle = _raw_bundle()
    bundle["scanner_results"][0]["score"] = 90
    bundle["scanner_results"][1]["score"] = 90
    bundle["scanner_results"].reverse()

    validated = validate_replay_bundle_v4(bundle)

    assert [row["symbol"] for row in validated.scanner_results] == [
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
    ]


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: bundle.pop("recorded_validator_response"),
        lambda bundle: bundle.update(recorded_validator_response=[]),
        lambda bundle: bundle["recorded_validator_response"].pop("content"),
        lambda bundle: bundle["recorded_validator_response"].update(content=""),
        lambda bundle: bundle["recorded_validator_response"].update(decision=" "),
        lambda bundle: bundle["recorded_validator_response"].update(extra="x"),
    ],
)
def test_recorded_validator_response_is_required_and_strict(mutator):
    _assert_invalid(mutator)


def test_recorded_validator_usage_is_optional_and_normalizes_to_none():
    bundle = _raw_bundle()
    bundle.pop("recorded_validator_usage")

    validated = validate_replay_bundle_v4(bundle)

    assert validated.recorded_validator_usage is None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: bundle["recorded_validator_usage"].update(prompt_tokens=-1),
        lambda bundle: bundle["recorded_validator_usage"].update(completion_tokens=True),
        lambda bundle: bundle["recorded_validator_usage"].update(total_tokens=151),
        lambda bundle: bundle["recorded_validator_usage"].update(extra=1),
    ],
)
def test_recorded_validator_usage_rejects_invalid_values(mutator):
    _assert_invalid(mutator)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: bundle.pop("pre_delivery_closed_candles"),
        lambda bundle: bundle.update(pre_delivery_closed_candles=[]),
        lambda bundle: bundle["pre_delivery_closed_candles"].pop("ETH/USDT:USDT"),
        lambda bundle: bundle["pre_delivery_closed_candles"].update(XRP=[]),
        lambda bundle: bundle["pre_delivery_closed_candles"]["BTC/USDT:USDT"].clear(),
        lambda bundle: bundle["pre_delivery_closed_candles"]["BTC/USDT:USDT"][0].update(volume=-1),
        lambda bundle: bundle["pre_delivery_closed_candles"]["BTC/USDT:USDT"][0].update(high=58000),
        lambda bundle: bundle["pre_delivery_closed_candles"]["BTC/USDT:USDT"][1].update(open_time="2026-07-13T04:00:00"),
    ],
)
def test_pre_delivery_candles_are_complete_and_validated(mutator):
    _assert_invalid(mutator)


def test_pre_delivery_candle_times_must_be_strictly_increasing():
    _assert_invalid(
        lambda bundle: bundle["pre_delivery_closed_candles"][
            "BTC/USDT:USDT"
        ][1].update(open_time="2026-07-13T00:00:00+00:00")
    )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: bundle.pop("expected_semantic_contract"),
        lambda bundle: bundle["expected_semantic_contract"].update(
            classification="LIVE"
        ),
        lambda bundle: bundle["expected_semantic_contract"].update(
            boundary="SCANNER"
        ),
        lambda bundle: bundle["expected_semantic_contract"].update(extra="x"),
    ],
)
def test_semantic_metadata_is_frozen(mutator):
    _assert_invalid(mutator)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: bundle.update(api_key="not-allowed"),
        lambda bundle: bundle.update(secret="not-allowed"),
        lambda bundle: bundle["execution_configuration"].update(
            output_path="data/production_evidence_v4"
        ),
        lambda bundle: bundle["execution_configuration"].update(
            quota_state_path="data/quota_slot_v4/quota_slot_state.json"
        ),
        lambda bundle: bundle["execution_configuration"].update(
            worker_state_path="data/worker_state_v4/master_engine_v4_latest.json"
        ),
    ],
)
def test_secrets_and_production_paths_are_prohibited(mutator):
    _assert_invalid(mutator)


def test_canonicalization_is_utf8_stable_and_mapping_order_independent():
    original = _raw_bundle()
    reordered = {
        key: original[key]
        for key in reversed(list(original))
    }

    canonical_original = canonicalize_replay_bundle_v4(original)
    canonical_reordered = canonicalize_replay_bundle_v4(reordered)

    assert isinstance(canonical_original, bytes)
    assert canonical_original == canonical_reordered
    assert canonical_original.decode("utf-8")
    assert b"\n" not in canonical_original
    assert b": " not in canonical_original
    assert b", " not in canonical_original


def test_hash_is_lowercase_sha256_and_changes_with_semantic_input():
    bundle = _validated_bundle()
    digest = calculate_replay_bundle_hash_v4(bundle)

    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(character in "0123456789abcdef" for character in digest)

    changed = copy.deepcopy(_raw_bundle())
    changed["execution_configuration"]["limit"] += 1
    changed_bundle = validate_replay_bundle_v4(changed)
    assert calculate_replay_bundle_hash_v4(changed_bundle) != digest


def test_loading_valid_json_does_not_create_output_paths(tmp_path):
    source = tmp_path / "bundle.json"
    source.write_bytes(FIXTURE_PATH.read_bytes())
    source_before = source.read_bytes()

    loaded = load_replay_bundle_v4(source)

    assert isinstance(loaded, ReplayBundleV4)
    assert source.read_bytes() == source_before
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("payload", ["{", "[]", "null"])
def test_file_loading_fails_closed_for_invalid_json_or_top_level(payload, tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(payload)

    with pytest.raises(ReplayBundleValidationError):
        load_replay_bundle_v4(path)


def test_file_loading_rejects_missing_file_and_directory(tmp_path):
    with pytest.raises(ReplayBundleValidationError):
        load_replay_bundle_v4(tmp_path / "missing.json")

    directory = tmp_path / "bundle-directory"
    directory.mkdir()
    with pytest.raises(ReplayBundleValidationError):
        load_replay_bundle_v4(directory)


def test_validation_does_not_read_environment_or_touch_output_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bundle = validate_replay_bundle_v4(_raw_bundle())

    assert isinstance(bundle, ReplayBundleV4)
    assert list(tmp_path.iterdir()) == []


def test_import_is_side_effect_free_without_network_or_runtime_execution(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("engine.replay_contract_v4")
    importlib.reload(module)

    assert not (tmp_path / "data").exists()
    assert list(tmp_path.iterdir()) == []
