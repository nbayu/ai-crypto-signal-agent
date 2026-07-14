import copy
import hashlib
import importlib
import json
import math
from pathlib import Path

import pytest

import engine.replay_contract_v4 as replay_contract_module
from engine.replay_contract_v4 import (
    REPLAY_BUNDLE_SCHEMA_VERSION,
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


def _assert_invalid(mutator):
    candidate = _raw_bundle()
    mutator(candidate)
    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        validate_replay_bundle_v4(candidate)


def test_public_schema_version_is_two_and_v1_fixture_is_legacy():
    historical = _raw_bundle()
    source_before = copy.deepcopy(historical)

    assert REPLAY_BUNDLE_SCHEMA_VERSION == 2
    assert historical["schema_version"] == 1

    failures = []
    for _ in range(2):
        with pytest.raises(
            replay_contract_module.ReplayBundleValidationError
        ) as exc_info:
            validate_replay_bundle_v4(historical)
        failures.append(str(exc_info.value))

    assert failures == ["Invalid replay bundle", "Invalid replay bundle"]
    assert "migrat" not in failures[0].casefold()
    assert "upgrad" not in failures[0].casefold()
    assert historical == source_before


def test_v1_fixture_bytes_are_preserved_when_loading_is_rejected():
    source_before = FIXTURE_PATH.read_bytes()

    assert json.loads(source_before)["schema_version"] == 1
    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        load_replay_bundle_v4(FIXTURE_PATH)
    assert FIXTURE_PATH.read_bytes() == source_before


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


def test_v1_canonicalization_and_identity_are_not_executable():
    historical = _raw_bundle()
    source_before = copy.deepcopy(historical)
    operations = (
        canonicalize_replay_bundle_v4,
        calculate_replay_bundle_hash_v4,
        derive_replay_fixture_id_v4,
        derive_replay_id_v4,
    )

    for operation in operations:
        with pytest.raises(replay_contract_module.ReplayBundleValidationError):
            operation(historical)

    assert historical == source_before


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


def test_v1_scanner_rows_remain_historical_but_are_not_executable():
    bundle = _raw_bundle()
    bundle["scanner_results"][0]["score"] = 90
    bundle["scanner_results"][1]["score"] = 90
    bundle["scanner_results"].reverse()
    source_before = copy.deepcopy(bundle)

    assert [row["symbol"] for row in bundle["scanner_results"]] == [
        "ETH/USDT:USDT",
        "BTC/USDT:USDT",
    ]
    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        validate_replay_bundle_v4(bundle)
    assert bundle == source_before


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


def test_v1_optional_usage_shape_does_not_restore_execution():
    bundle = _raw_bundle()
    bundle.pop("recorded_validator_usage")
    source_before = copy.deepcopy(bundle)

    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        validate_replay_bundle_v4(bundle)
    assert bundle == source_before
    assert "recorded_validator_usage" not in bundle
    assert "recorded_open_interest" not in bundle


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


def test_v1_raw_json_is_stable_but_active_canonicalization_rejects_it():
    original = _raw_bundle()
    reordered = {
        key: original[key]
        for key in reversed(list(original))
    }
    original_before = copy.deepcopy(original)
    reordered_before = copy.deepcopy(reordered)

    raw_original = json.dumps(original, sort_keys=True, separators=(",", ":"))
    raw_reordered = json.dumps(reordered, sort_keys=True, separators=(",", ":"))
    assert raw_original == raw_reordered

    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        canonicalize_replay_bundle_v4(original)
    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        canonicalize_replay_bundle_v4(reordered)
    assert original == original_before
    assert reordered == reordered_before


def test_v1_raw_fixture_hash_is_stable_but_replay_hashing_is_rejected():
    source_before = FIXTURE_PATH.read_bytes()
    digest = hashlib.sha256(source_before).hexdigest()

    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(character in "0123456789abcdef" for character in digest)
    assert hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest() == digest

    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        calculate_replay_bundle_hash_v4(_raw_bundle())
    assert FIXTURE_PATH.read_bytes() == source_before


def test_loading_v1_json_rejects_without_creating_output_paths(tmp_path):
    source = tmp_path / "bundle.json"
    source.write_bytes(FIXTURE_PATH.read_bytes())
    source_before = source.read_bytes()

    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        load_replay_bundle_v4(source)

    assert source.read_bytes() == source_before
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("payload", ["{", "[]", "null"])
def test_file_loading_fails_closed_for_invalid_json_or_top_level(payload, tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(payload)

    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        load_replay_bundle_v4(path)


def test_file_loading_rejects_missing_file_and_directory(tmp_path):
    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        load_replay_bundle_v4(tmp_path / "missing.json")

    directory = tmp_path / "bundle-directory"
    directory.mkdir()
    with pytest.raises(replay_contract_module.ReplayBundleValidationError):
        load_replay_bundle_v4(directory)


def test_v1_rejection_does_not_mutate_source_or_touch_output_paths(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    historical = _raw_bundle()
    source_before = copy.deepcopy(historical)

    for _ in range(2):
        with pytest.raises(replay_contract_module.ReplayBundleValidationError):
            validate_replay_bundle_v4(historical)

    assert historical == source_before
    assert historical["schema_version"] == 1
    assert "recorded_open_interest" not in historical
    assert all(
        "reference_price" not in row
        for row in historical["scanner_results"]
    )
    assert "cache_hit_tokens" not in historical["recorded_validator_usage"]
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
