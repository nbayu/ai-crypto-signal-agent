import ast
import copy
import hashlib
import importlib
import inspect
import json
import os
import socket
import sys
from dataclasses import FrozenInstanceError
from importlib import util as importlib_util
from pathlib import Path
from types import MappingProxyType

import pandas as pd
import pytest
import requests

import engine.binance_client as binance_module
import engine.deepseek_validator_v4 as deepseek_module
import engine.master_engine_v4 as master_module
import engine.pre_delivery_flow_v4 as flow_module
import engine.pre_delivery_market_data_v4 as market_data_module
import engine.pre_delivery_validator_v4 as delivery_validator_module
import engine.quota_slot_worker_v4 as quota_worker_module
import engine.scanner as scanner_module
import engine.stateful_worker_v4 as stateful_worker_module
import engine.telegram_sdk_runner_v4 as telegram_runner_module
import engine.validated_pipeline_v4 as pipeline_module
import engine.validation_payload_v2 as payload_module
from engine.replay_contract_v4 import (
    calculate_replay_bundle_hash_v4,
    derive_replay_fixture_id_v4,
    derive_replay_id_v4,
    load_replay_bundle_v4,
)
import engine.replay_runner_v4 as runner_module
from engine.replay_runner_v4 import (
    ReplayExecutionError,
    ReplayExecutionResultV4,
    run_replay_v4,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "replay_v4"
    / "valid_bundle_v2.json"
)
FIXTURE_SHA256 = (
    "5a91fc2edc25d09b88678c73353c0e0a"
    "b8ecedf79c22544489e9613dbc62290f"
)
CLASSIFICATION = "REPLAY"
BOUNDARY = "MASTER_ENGINE_RECORDED_INPUT"
MASTER_DEPENDENCIES = {
    "scanner",
    "pipeline",
    "snapshot_saver",
    "outcome_saver",
    "watchlist_saver",
    "pre_delivery_runner",
    "closed_candle_provider",
    "production_evidence_saver",
    "now_provider",
}
PROTECTED_ROOT_COMPONENTS = (
    "production_run_v4",
    "production_evidence_v4",
    "validated_snapshots_v4",
    "v4_outcomes",
    "top5_watchlist_v4",
    "pre_delivery_v4",
    "pine_delivery_v4",
    "quota_slot_v4",
    "worker_state_v4",
    "forward-test",
    "telegram",
)


@pytest.fixture
def bundle():
    return load_replay_bundle_v4(FIXTURE_PATH)


def _fail_if_called(name):
    def fail(*args, **kwargs):
        raise AssertionError(f"protected dependency called: {name}")

    return fail


def _thaw(value):
    if isinstance(value, dict) or isinstance(value, MappingProxyType):
        return {key: _thaw(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw(nested) for nested in value]
    return value


def _path_is_beneath(path, root):
    return Path(path).resolve().is_relative_to(Path(root).resolve())


def _directory_tree_state(root):
    root = Path(root)
    state = []
    for path in (root, *sorted(root.rglob("*"))):
        relative = "." if path == root else path.relative_to(root).as_posix()
        metadata = path.lstat()
        if path.is_symlink():
            kind = "symlink"
            content = os.readlink(path)
        elif path.is_file():
            kind = "file"
            content = path.read_bytes()
        elif path.is_dir():
            kind = "directory"
            content = None
        else:
            kind = "other"
            content = None
        state.append((relative, kind, content, metadata.st_mtime_ns))
    return tuple(state)


def _assert_runner_output_root_is_rejected(bundle, output_root, target_root):
    output_root = Path(output_root)
    target_root = Path(target_root)
    master_calls = []
    target_before = _directory_tree_state(target_root)
    root_existed = os.path.lexists(output_root)
    root_was_symlink = output_root.is_symlink()
    link_target = os.readlink(output_root) if root_was_symlink else None

    def forbidden_master(**dependencies):
        master_calls.append(dependencies)
        raise AssertionError("master engine must not run for invalid root")

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            output_root,
            master_engine_runner=forbidden_master,
        )

    assert str(exc_info.value) == "Invalid replay output root"
    assert str(output_root) not in str(exc_info.value)
    assert str(target_root) not in str(exc_info.value)
    assert master_calls == []
    assert os.path.lexists(output_root) is root_existed
    if root_was_symlink:
        assert output_root.is_symlink()
        assert os.readlink(output_root) == link_target
    assert _directory_tree_state(target_root) == target_before
    assert not tuple(target_root.rglob("replay_*.json"))
    assert not tuple(target_root.rglob("replay_*.txt"))
    assert not tuple(target_root.rglob("latest*"))


def _invoke_like_master_engine(dependencies):
    results = dependencies["scanner"]()
    out = dependencies["pipeline"](results)
    now = dependencies["now_provider"]()
    validated_at = now.isoformat()
    snapshot_path = dependencies["snapshot_saver"](out, now=now)
    outcome_path = dependencies["outcome_saver"](out["final_top5"])
    watchlist_path = dependencies["watchlist_saver"](out["final_top5"])
    delivery_out = dependencies["pre_delivery_runner"](
        watchlist_path,
        "data/top5_watchlist_v4/tradingview_watchlist.txt",
        closed_candle_provider=dependencies["closed_candle_provider"],
        validated_at=validated_at,
    )
    evidence_path = dependencies["production_evidence_saver"](
        created_at=validated_at,
        validated_snapshot_path=snapshot_path,
        outcome_entry_path=outcome_path,
        raw_top5_path=watchlist_path,
        pre_delivery_path=delivery_out["delivery_artifact_path"],
        tradingview_watchlist_path=delivery_out["tradingview_watchlist_path"],
    )
    return {
        "results": results,
        "out": out,
        "snapshot_path": snapshot_path,
        "outcome_path": outcome_path,
        "watchlist_path": watchlist_path,
        "delivery_out": delivery_out,
        "evidence_path": evidence_path,
    }


def _json_documents(root):
    documents = []
    for path in sorted(Path(root).rglob("*.json")):
        try:
            documents.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except json.JSONDecodeError:
            continue
    return documents


def _find_document(root, predicate):
    matches = [item for item in _json_documents(root) if predicate(item[1])]
    assert len(matches) == 1
    return matches[0]


def test_public_api_and_signature_are_frozen():
    assert issubclass(ReplayExecutionError, Exception)
    assert inspect.isclass(ReplayExecutionResultV4)
    assert str(inspect.signature(run_replay_v4)) == (
        "(bundle, output_root, *, master_engine_runner=None)"
    )


def test_validated_bundle_is_required_and_raw_mapping_fails_before_output(
    tmp_path,
):
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    original = copy.deepcopy(raw)
    output_root = tmp_path / "must-not-exist"
    calls = []

    with pytest.raises(ReplayExecutionError) as first:
        run_replay_v4(
            raw,
            output_root,
            master_engine_runner=lambda **kwargs: calls.append(kwargs),
        )
    with pytest.raises(ReplayExecutionError) as repeated:
        run_replay_v4(raw, output_root)

    assert str(first.value) == str(repeated.value)
    assert raw == original
    assert calls == []
    assert not output_root.exists()


@pytest.mark.parametrize("invalid_root", [None, "", 0, False, object()])
def test_invalid_output_root_fails_before_master_engine(bundle, invalid_root):
    calls = []

    with pytest.raises(ReplayExecutionError):
        run_replay_v4(
            bundle,
            invalid_root,
            master_engine_runner=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []


def test_file_output_root_is_rejected_before_master_engine(bundle, tmp_path):
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("sentinel", encoding="utf-8")
    calls = []

    with pytest.raises(ReplayExecutionError):
        run_replay_v4(
            bundle,
            output_file,
            master_engine_runner=lambda **kwargs: calls.append(kwargs),
        )

    assert output_file.read_text(encoding="utf-8") == "sentinel"
    assert calls == []


@pytest.mark.parametrize(
    "protected_root",
    [
        Path("data/validated_snapshots_v4"),
        Path("data/v4_outcomes"),
        Path("data/top5_watchlist_v4"),
        Path("data/pre_delivery_v4"),
        Path("data/pine_delivery_v4"),
        Path("data/production_evidence_v4"),
        Path("data/quota_slot_v4"),
        Path("data/worker_state_v4"),
    ],
)
def test_protected_production_and_state_roots_are_rejected(
    bundle,
    protected_root,
):
    calls = []

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            protected_root,
            master_engine_runner=lambda **kwargs: calls.append(kwargs),
        )

    assert calls == []
    assert str(protected_root) not in str(exc_info.value)


@pytest.mark.parametrize("protected_component", PROTECTED_ROOT_COMPONENTS)
def test_representative_protected_root_components_fail_before_execution(
    bundle,
    tmp_path,
    protected_component,
):
    target = tmp_path / "protected" / protected_component
    target.mkdir(parents=True)
    sentinel = target / "sentinel.bin"
    sentinel.write_bytes(b"protected-state-must-not-change")
    output_root = target / "replay-output"
    assert not output_root.exists()

    _assert_runner_output_root_is_rejected(bundle, output_root, target)

    assert sentinel.read_bytes() == b"protected-state-must-not-change"


def test_direct_output_root_symlink_to_external_directory_is_rejected(
    bundle,
    tmp_path,
):
    target = tmp_path / "external-target"
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("external target unchanged", encoding="utf-8")
    caller = tmp_path / "caller"
    caller.mkdir()
    output_root = caller / "output-alias"
    output_root.symlink_to(target, target_is_directory=True)

    _assert_runner_output_root_is_rejected(bundle, output_root, target)

    assert sentinel.read_text(encoding="utf-8") == "external target unchanged"


def test_direct_output_root_symlink_to_protected_directory_is_rejected(
    bundle,
    tmp_path,
):
    target = tmp_path / "data" / "pre_delivery_v4"
    target.mkdir(parents=True)
    sentinel = target / "sentinel.json"
    sentinel.write_text('{"production":"sentinel"}', encoding="utf-8")
    caller = tmp_path / "caller"
    caller.mkdir()
    output_root = caller / "output-alias"
    output_root.symlink_to(target, target_is_directory=True)

    _assert_runner_output_root_is_rejected(bundle, output_root, target)

    assert sentinel.read_text(encoding="utf-8") == (
        '{"production":"sentinel"}'
    )


def test_nonexistent_output_leaf_beneath_immediate_symlink_is_rejected(
    bundle,
    tmp_path,
):
    target = tmp_path / "external-target"
    target.mkdir()
    sentinel = target / "sentinel.bin"
    sentinel.write_bytes(b"unchanged")
    caller = tmp_path / "caller"
    caller.mkdir()
    alias = caller / "alias"
    alias.symlink_to(target, target_is_directory=True)
    output_root = alias / "nonexistent-output"
    assert not output_root.exists()

    _assert_runner_output_root_is_rejected(bundle, output_root, target)

    assert sentinel.read_bytes() == b"unchanged"


def test_deep_output_root_ancestry_checks_every_symlink_component(
    bundle,
    tmp_path,
):
    target = tmp_path / "external-target"
    target.mkdir()
    sentinel = target / "sentinel.bin"
    sentinel.write_bytes(b"unchanged")
    caller = tmp_path / "caller" / "safe" / "deeper"
    caller.mkdir(parents=True)
    alias = caller / "alias"
    alias.symlink_to(target, target_is_directory=True)
    output_root = alias / "nested" / "nonexistent-output"
    assert not output_root.exists()

    _assert_runner_output_root_is_rejected(bundle, output_root, target)

    assert sentinel.read_bytes() == b"unchanged"


@pytest.mark.parametrize(
    "protected_component",
    ["pre_delivery_v4", "forward-test", "telegram"],
)
def test_harmless_output_alias_to_protected_target_is_rejected(
    bundle,
    tmp_path,
    protected_component,
):
    target = tmp_path / "protected" / protected_component
    target.mkdir(parents=True)
    sentinel = target / "sentinel.bin"
    sentinel.write_bytes(b"protected-target-unchanged")
    caller = tmp_path / "caller"
    caller.mkdir()
    alias = caller / "cache"
    alias.symlink_to(target, target_is_directory=True)
    output_root = alias / "output"
    assert not output_root.exists()

    _assert_runner_output_root_is_rejected(bundle, output_root, target)

    assert sentinel.read_bytes() == b"protected-target-unchanged"


def test_ordinary_nested_output_root_without_symlinks_is_allowed(
    bundle,
    tmp_path,
):
    output_root = tmp_path / "caller" / "safe" / "nested" / "replay-output"

    result = run_replay_v4(
        bundle,
        output_root,
        master_engine_runner=_invoke_like_master_engine,
    )

    assert result.classification == CLASSIFICATION
    assert result.boundary == BOUNDARY
    assert Path(result.output_root) == output_root.resolve()
    assert all(
        _path_is_beneath(path, output_root)
        for path in output_root.rglob("*")
        if path.is_file()
    )


def test_master_engine_runner_is_keyword_only_and_must_be_callable(
    bundle,
    tmp_path,
):
    with pytest.raises(TypeError):
        run_replay_v4(bundle, tmp_path, object())

    with pytest.raises(ReplayExecutionError):
        run_replay_v4(bundle, tmp_path, master_engine_runner=object())


def test_runner_invokes_injected_master_once_with_complete_dependencies(
    bundle,
    tmp_path,
):
    calls = []

    def master_engine_probe(**dependencies):
        calls.append(dependencies)
        return _invoke_like_master_engine(dependencies)

    result = run_replay_v4(
        bundle,
        tmp_path / "replay-output",
        master_engine_runner=master_engine_probe,
    )

    assert len(calls) == 1
    assert set(calls[0]) == MASTER_DEPENDENCIES
    assert isinstance(result, ReplayExecutionResultV4)


@pytest.mark.parametrize(
    "master_result",
    [
        pytest.param({"metric": float("nan")}, id="nan"),
        pytest.param({"metric": float("inf")}, id="positive-infinity"),
        pytest.param({"metric": float("-inf")}, id="negative-infinity"),
        pytest.param(
            {"one": {"two": [0, {"three": float("nan")}]}},
            id="deeply-nested-non-finite",
        ),
    ],
)
def test_injected_master_non_finite_result_fails_without_success(
    bundle,
    tmp_path,
    master_result,
):
    output_root = tmp_path / "replay-output"
    calls = []

    def master_engine_probe(**dependencies):
        calls.append(dependencies)
        return copy.deepcopy(master_result)

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            output_root,
            master_engine_runner=master_engine_probe,
        )

    assert str(exc_info.value) == "Replay master-engine execution failed"
    assert "nan" not in str(exc_info.value).casefold()
    assert "infinity" not in str(exc_info.value).casefold()
    assert len(calls) == 1
    assert set(calls[0]) == MASTER_DEPENDENCIES
    assert not tuple(output_root.rglob("replay_*.json"))
    assert not tuple(output_root.rglob("replay_*.txt"))
    assert not tuple(output_root.rglob("replay_manifest.json"))
    assert not tuple(output_root.rglob("latest*"))


def test_injected_master_finite_nested_result_remains_valid(bundle, tmp_path):
    finite_result = {
        "values": [0.0, -0.0, 1.25, -2.5, 1.7976931348623157e308],
        "nested": {"finite": [42.125, -999.75]},
    }
    calls = []

    def master_engine_probe(**dependencies):
        calls.append(dependencies)
        return copy.deepcopy(finite_result)

    result = run_replay_v4(
        bundle,
        tmp_path / "replay-output",
        master_engine_runner=master_engine_probe,
    )

    assert len(calls) == 1
    assert _thaw(result.normalized_master_result) == finite_result
    assert result.classification == CLASSIFICATION
    assert result.boundary == BOUNDARY


def test_scanner_provider_returns_fresh_mutable_normalized_rows(
    bundle,
    tmp_path,
):
    observations = {}
    probe_complete = RuntimeError("scanner probe complete")

    def master_engine_probe(**dependencies):
        first = dependencies["scanner"]()
        second = dependencies["scanner"]()
        observations["first"] = first
        observations["second"] = second
        first[0]["golden_zone"]["levels"]["0.5"] = -1
        raise probe_complete

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            tmp_path / "replay-output",
            master_engine_runner=master_engine_probe,
        )

    assert exc_info.value.__cause__ is probe_complete
    first = observations["first"]
    second = observations["second"]
    assert first is not second
    assert first[0] is not second[0]
    assert isinstance(first, list)
    assert isinstance(first[0], dict)
    assert isinstance(first[0]["golden_zone"], dict)
    assert second[0]["golden_zone"]["levels"]["0.5"] == 60500.0
    assert [row["symbol"] for row in second] == [
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
    ]
    assert bundle.scanner_results[0]["golden_zone"]["levels"]["0.5"] == 60500.0


def test_pipeline_composition_consumes_recorded_oi_and_validator_once(
    bundle,
    tmp_path,
    monkeypatch,
):
    real_pipeline = pipeline_module.run_validated_pipeline_v4
    pipeline_calls = []
    validator_calls = []
    oi_calls = []

    def pipeline_spy(results, *, validator=None, oi_provider=None):
        pipeline_calls.append(results)
        assert callable(validator)
        assert callable(oi_provider)

        def validator_spy(candidates):
            validator_calls.append(copy.deepcopy(candidates))
            return validator(candidates)

        def oi_spy(symbol):
            oi_calls.append(symbol)
            return oi_provider(symbol)

        return real_pipeline(
            results,
            validator=validator_spy,
            oi_provider=oi_spy,
        )

    monkeypatch.setattr(runner_module, "run_validated_pipeline_v4", pipeline_spy)
    monkeypatch.setattr(
        pipeline_module,
        "validate_candidates",
        _fail_if_called("live validator"),
    )
    monkeypatch.setattr(
        payload_module,
        "open_interest_metrics_v2",
        _fail_if_called("live OI provider"),
    )
    captured = {}
    probe_complete = RuntimeError("pipeline probe complete")

    def master_engine_probe(**dependencies):
        captured["out"] = dependencies["pipeline"](
            dependencies["scanner"]()
        )
        raise probe_complete

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            tmp_path / "replay-output",
            master_engine_runner=master_engine_probe,
        )

    assert exc_info.value.__cause__ is probe_complete
    assert len(pipeline_calls) == 1
    assert len(validator_calls) == 1
    assert oi_calls == ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    assert [row["symbol"] for row in validator_calls[0]] == oi_calls
    assert [row["participation"] for row in validator_calls[0]] == [
        "STRONG",
        "STRONG",
    ]
    assert captured["out"]["usage"] == _thaw(bundle.recorded_validator_usage)
    assert [row["symbol"] for row in captured["out"]["final_top5"]] == oi_calls


def test_recorded_oi_unknown_symbol_fails_closed_without_live_fallback(
    bundle,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        payload_module,
        "open_interest_metrics_v2",
        _fail_if_called("live OI provider"),
    )

    def master_engine_probe(**dependencies):
        rows = dependencies["scanner"]()
        rows[0]["symbol"] = "UNKNOWN/USDT:USDT"
        dependencies["pipeline"](rows)

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            tmp_path / "replay-output",
            master_engine_runner=master_engine_probe,
        )

    assert "UNKNOWN/USDT:USDT" not in str(exc_info.value)


def test_recorded_candle_provider_returns_fresh_production_dataframes(
    bundle,
    tmp_path,
):
    observations = {}
    probe_complete = RuntimeError("candle probe complete")

    def master_engine_probe(**dependencies):
        provider = dependencies["closed_candle_provider"]
        first = provider("BTC/USDT:USDT")
        second = provider("BTC/USDT:USDT")
        observations["first"] = first
        observations["second"] = second
        first.loc[0, "close"] = -1
        raise probe_complete

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            tmp_path / "replay-output",
            master_engine_runner=master_engine_probe,
        )

    assert exc_info.value.__cause__ is probe_complete
    first = observations["first"]
    second = observations["second"]
    assert isinstance(first, pd.DataFrame)
    assert first is not second
    assert list(first.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert second["timestamp"].is_monotonic_increasing
    assert second.loc[0, "close"] == 60500.0
    assert second["timestamp"].dt.tz is not None


def test_recorded_candle_unknown_symbol_fails_closed(bundle, tmp_path):
    def master_engine_probe(**dependencies):
        dependencies["closed_candle_provider"]("UNKNOWN/USDT:USDT")

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            tmp_path / "replay-output",
            master_engine_runner=master_engine_probe,
        )

    assert "UNKNOWN/USDT:USDT" not in str(exc_info.value)


def test_fixed_clock_is_timezone_aware_stable_and_controls_watchlist(
    bundle,
    tmp_path,
):
    fixed_values = []

    def master_engine_probe(**dependencies):
        fixed_values.extend(
            [dependencies["now_provider"](), dependencies["now_provider"]()]
        )
        return _invoke_like_master_engine(dependencies)

    output_root = tmp_path / "replay-output"
    run_replay_v4(
        bundle,
        output_root,
        master_engine_runner=master_engine_probe,
    )

    assert fixed_values[0] == fixed_values[1]
    assert fixed_values[0].tzinfo is not None
    assert fixed_values[0].utcoffset() is not None
    assert fixed_values[0].isoformat() == bundle.fixed_execution_time
    _, watchlist = _find_document(
        output_root,
        lambda document: (
            isinstance(document, dict)
            and "generated_at" in document
            and "setups" in document
            and "evaluations" not in document
        ),
    )
    assert watchlist["generated_at"] == bundle.fixed_execution_time


def test_result_is_immutable_classified_and_uses_contract_identity(
    bundle,
    tmp_path,
):
    output_root = tmp_path / "replay-output"
    result = run_replay_v4(
        bundle,
        output_root,
        master_engine_runner=_invoke_like_master_engine,
    )

    assert result.replay_id == derive_replay_id_v4(bundle)
    assert result.fixture_id == derive_replay_fixture_id_v4(bundle)
    assert result.bundle_hash == calculate_replay_bundle_hash_v4(bundle)
    assert result.fixed_execution_time == bundle.fixed_execution_time
    assert Path(result.output_root).resolve() == output_root.resolve()
    assert result.classification == CLASSIFICATION
    assert result.boundary == BOUNDARY
    assert isinstance(result.normalized_master_result, MappingProxyType)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.classification = "PRODUCTION"
    with pytest.raises(TypeError):
        result.normalized_master_result["out"] = {}

    normalized_text = json.dumps(
        _thaw(result.normalized_master_result),
        sort_keys=True,
    )
    assert "production evidence" not in normalized_text.casefold()
    assert "profit" not in normalized_text.casefold()
    assert "raw scanner replay" not in normalized_text.casefold()


def test_fixture_and_bundle_are_unchanged_after_execution(bundle, tmp_path):
    fixture_before = FIXTURE_PATH.read_bytes()
    scanner_before = _thaw(bundle.scanner_results)
    contract_module = importlib.import_module("engine.replay_contract_v4")
    assert isinstance(bundle, contract_module.ReplayBundleV4)
    assert hashlib.sha256(fixture_before).hexdigest() == FIXTURE_SHA256

    run_replay_v4(
        bundle,
        tmp_path / "replay-output",
        master_engine_runner=_invoke_like_master_engine,
    )

    assert FIXTURE_PATH.read_bytes() == fixture_before
    assert _thaw(bundle.scanner_results) == scanner_before


def test_master_engine_failure_is_wrapped_once_with_original_cause(
    bundle,
    tmp_path,
):
    failure = RuntimeError("synthetic master failure")
    calls = []

    def failing_master(**dependencies):
        calls.append(dependencies)
        raise failure

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            tmp_path / "replay-output",
            master_engine_runner=failing_master,
        )

    assert len(calls) == 1
    assert exc_info.value.__cause__ is failure
    assert "synthetic master failure" not in str(exc_info.value)


def test_pre_delivery_saver_failure_stops_exporter_and_pine(
    bundle,
    tmp_path,
    monkeypatch,
):
    real_flow = flow_module.run_pre_delivery_flow
    calls = []
    failure = OSError("synthetic delivery failure")

    def flow_spy(
        source_path,
        tradingview_output_path,
        *,
        closed_candle_provider,
        validated_at,
        delivery_artifact_saver,
        tradingview_exporter,
        pine_delivery_saver,
    ):
        def failing_delivery_saver(artifact):
            calls.append("delivery")
            raise failure

        def exporter_spy(*args):
            calls.append("tradingview")
            return tradingview_exporter(*args)

        def pine_spy(*args):
            calls.append("pine")
            return pine_delivery_saver(*args)

        return real_flow(
            source_path,
            tradingview_output_path,
            closed_candle_provider=closed_candle_provider,
            validated_at=validated_at,
            delivery_artifact_saver=failing_delivery_saver,
            tradingview_exporter=exporter_spy,
            pine_delivery_saver=pine_spy,
        )

    monkeypatch.setattr(runner_module, "run_pre_delivery_flow", flow_spy)

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            tmp_path / "replay-output",
            master_engine_runner=master_module.run_master_engine_v4,
        )

    assert exc_info.value.__cause__ is failure
    assert calls == ["delivery"]


def test_evidence_failure_occurs_after_real_master_artifacts_and_is_wrapped(
    bundle,
    tmp_path,
):
    failure = OSError("synthetic replay evidence failure")
    calls = []

    def master_with_failing_evidence(**dependencies):
        def failing_evidence(**kwargs):
            calls.append(kwargs)
            raise failure

        dependencies["production_evidence_saver"] = failing_evidence
        return master_module.run_master_engine_v4(**dependencies)

    with pytest.raises(ReplayExecutionError) as exc_info:
        run_replay_v4(
            bundle,
            tmp_path / "replay-output",
            master_engine_runner=master_with_failing_evidence,
        )

    assert exc_info.value.__cause__ is failure
    assert len(calls) == 1
    assert set(calls[0]) == {
        "created_at",
        "validated_snapshot_path",
        "outcome_entry_path",
        "raw_top5_path",
        "pre_delivery_path",
        "tradingview_watchlist_path",
    }


def test_real_master_path_executes_canonical_semantics_without_live_access(
    bundle,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    output_root = tmp_path / "replay-output"
    calls = {
        "master": 0,
        "validator": 0,
        "oi": [],
        "classification": 0,
        "control": 0,
        "semantic": 0,
        "top5": 0,
        "candles": [],
        "trend": 0,
        "lifecycle": 0,
        "supersession": 0,
        "pine_bridge": 0,
        "pine_payload": 0,
    }

    real_master = master_module.run_master_engine_v4
    real_pipeline = pipeline_module.run_validated_pipeline_v4
    real_classify = payload_module.classify_participation
    real_control = pipeline_module.apply_validation_control
    real_semantic = pipeline_module.validate_semantic_consistency
    real_top5 = pipeline_module.build_final_top5
    real_flow = flow_module.run_pre_delivery_flow
    real_trend = delivery_validator_module.detect_trend
    real_lifecycle = delivery_validator_module.evaluate_setup_lifecycle
    real_supersession = delivery_validator_module.evaluate_swing_supersession
    real_pine_bridge = flow_module.build_pine_bridge_artifact
    real_pine_payload = flow_module.build_pine_bridge_delivery_payload

    def master_spy(**dependencies):
        calls["master"] += 1
        return real_master(**dependencies)

    def pipeline_spy(results, *, validator=None, oi_provider=None):
        assert callable(validator)
        assert callable(oi_provider)

        def validator_spy(candidates):
            calls["validator"] += 1
            return validator(candidates)

        def oi_spy(symbol):
            calls["oi"].append(symbol)
            return oi_provider(symbol)

        return real_pipeline(
            results,
            validator=validator_spy,
            oi_provider=oi_spy,
        )

    def classify_spy(*args):
        calls["classification"] += 1
        return real_classify(*args)

    def control_spy(candidates, validations, semantic_guard=None):
        calls["control"] += 1
        return real_control(candidates, validations, semantic_guard=semantic_guard)

    def semantic_spy(candidate, validation):
        calls["semantic"] += 1
        return real_semantic(candidate, validation)

    def top5_spy(controlled):
        calls["top5"] += 1
        return real_top5(controlled)

    def flow_spy(
        source_path,
        tradingview_output_path,
        *,
        closed_candle_provider,
        validated_at,
        **savers,
    ):
        def candle_spy(symbol):
            calls["candles"].append(symbol)
            return closed_candle_provider(symbol)

        return real_flow(
            source_path,
            tradingview_output_path,
            closed_candle_provider=candle_spy,
            validated_at=validated_at,
            **savers,
        )

    def trend_spy(candles):
        calls["trend"] += 1
        return real_trend(candles)

    def lifecycle_spy(setup, candles):
        calls["lifecycle"] += 1
        return real_lifecycle(setup, candles)

    def supersession_spy(setup, candles, trend):
        calls["supersession"] += 1
        return real_supersession(setup, candles, trend)

    def pine_bridge_spy(artifact):
        calls["pine_bridge"] += 1
        return real_pine_bridge(artifact)

    def pine_payload_spy(artifact):
        calls["pine_payload"] += 1
        return real_pine_payload(artifact)

    monkeypatch.setattr(runner_module, "run_master_engine_v4", master_spy)
    monkeypatch.setattr(runner_module, "run_validated_pipeline_v4", pipeline_spy)
    monkeypatch.setattr(runner_module, "run_pre_delivery_flow", flow_spy)
    monkeypatch.setattr(payload_module, "classify_participation", classify_spy)
    monkeypatch.setattr(pipeline_module, "apply_validation_control", control_spy)
    monkeypatch.setattr(
        pipeline_module,
        "validate_semantic_consistency",
        semantic_spy,
    )
    monkeypatch.setattr(pipeline_module, "build_final_top5", top5_spy)
    monkeypatch.setattr(delivery_validator_module, "detect_trend", trend_spy)
    monkeypatch.setattr(
        delivery_validator_module,
        "evaluate_setup_lifecycle",
        lifecycle_spy,
    )
    monkeypatch.setattr(
        delivery_validator_module,
        "evaluate_swing_supersession",
        supersession_spy,
    )
    monkeypatch.setattr(flow_module, "build_pine_bridge_artifact", pine_bridge_spy)
    monkeypatch.setattr(
        flow_module,
        "build_pine_bridge_delivery_payload",
        pine_payload_spy,
    )

    monkeypatch.setattr(scanner_module, "scan_market", _fail_if_called("scanner"))
    monkeypatch.setattr(master_module, "scan_market", _fail_if_called("scanner"))
    monkeypatch.setattr(
        pipeline_module,
        "validate_candidates",
        _fail_if_called("live validator"),
    )
    monkeypatch.setattr(deepseek_module, "OpenAI", _fail_if_called("OpenAI"))
    monkeypatch.setattr(
        payload_module,
        "open_interest_metrics_v2",
        _fail_if_called("live OI"),
    )
    monkeypatch.setattr(market_data_module, "get_ohlcv", _fail_if_called("Binance"))
    monkeypatch.setattr(
        master_module,
        "get_closed_ohlcv_for_pre_delivery",
        _fail_if_called("live candles"),
    )
    monkeypatch.setattr(
        master_module,
        "save_production_evidence",
        _fail_if_called("production evidence"),
    )
    monkeypatch.setattr(
        stateful_worker_module,
        "run_master_engine_worker_v4",
        _fail_if_called("stateful worker"),
    )
    monkeypatch.setattr(
        quota_worker_module,
        "run_quota_slot_worker_v4",
        _fail_if_called("quota worker"),
    )
    monkeypatch.setattr(
        telegram_runner_module,
        "run_telegram_polling_v4",
        _fail_if_called("Telegram polling"),
    )
    monkeypatch.setattr(requests, "get", _fail_if_called("requests.get"))
    monkeypatch.setattr(
        socket,
        "create_connection",
        _fail_if_called("socket.create_connection"),
    )
    monkeypatch.setattr(
        binance_module.exchange,
        "fetch_ohlcv",
        _fail_if_called("CCXT fetch_ohlcv"),
    )

    result = run_replay_v4(bundle, output_root)

    assert calls == {
        "master": 1,
        "validator": 1,
        "oi": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
        "classification": 2,
        "control": 1,
        "semantic": 2,
        "top5": 1,
        "candles": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
        "trend": 2,
        "lifecycle": 2,
        "supersession": 2,
        "pine_bridge": 1,
        "pine_payload": 1,
    }
    assert result.classification == CLASSIFICATION
    assert result.boundary == BOUNDARY
    assert not (tmp_path / "data").exists()
    assert all(
        _path_is_beneath(path, output_root)
        for path in output_root.rglob("*")
        if path.is_file()
    )

    _, delivery = _find_document(
        output_root,
        lambda document: isinstance(document, dict) and "evaluations" in document,
    )
    assert delivery["eligible_setup_count"] == 2
    assert [row["lifecycle"]["state"] for row in delivery["evaluations"]] == [
        "ACTIVE",
        "ACTIVE",
    ]
    assert all(
        row["supersession"]["state"] == "NO_REPLACEMENT"
        for row in delivery["evaluations"]
    )

    evidence_matches = [
        (path, document)
        for path, document in _json_documents(output_root)
        if isinstance(document, dict)
        and document.get("classification") == CLASSIFICATION
        and document.get("boundary") == BOUNDARY
    ]
    assert len(evidence_matches) >= 1
    for path, document in evidence_matches:
        assert _path_is_beneath(path, output_root)
        assert "production_run_v4" not in str(path)
        assert document.get("snapshot_type") != "v4_production_evidence"


def test_replay_evidence_saver_receives_real_master_paths(bundle, tmp_path):
    observed = {}

    def master_engine_probe(**dependencies):
        original_evidence = dependencies["production_evidence_saver"]

        def evidence_spy(**kwargs):
            observed.update(kwargs)
            return original_evidence(**kwargs)

        dependencies["production_evidence_saver"] = evidence_spy
        return _invoke_like_master_engine(dependencies)

    output_root = tmp_path / "replay-output"
    result = run_replay_v4(
        bundle,
        output_root,
        master_engine_runner=master_engine_probe,
    )

    assert set(observed) == {
        "created_at",
        "validated_snapshot_path",
        "outcome_entry_path",
        "raw_top5_path",
        "pre_delivery_path",
        "tradingview_watchlist_path",
    }
    assert observed["created_at"] == bundle.fixed_execution_time
    assert all(
        _path_is_beneath(path, output_root)
        for key, path in observed.items()
        if key != "created_at"
    )
    evidence_path = _thaw(result.normalized_master_result)["evidence_path"]
    assert "production_run_v4" not in str(evidence_path)


def test_import_is_side_effect_free_and_has_no_protected_or_ambient_imports(
    tmp_path,
    monkeypatch,
):
    source_path = Path(runner_module.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.casefold() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.casefold())

    forbidden_imports = {
        "engine.stateful_worker_v4",
        "engine.quota_slot_worker_v4",
        "engine.telegram_application_v4",
        "engine.telegram_runtime_v4",
        "engine.telegram_sdk_runner_v4",
        "engine.replay_artifact_v4",
    }
    assert imported.isdisjoint(forbidden_imports)
    assert "datetime.now" not in source
    assert "datetime.utcnow" not in source
    assert "time.time" not in source
    assert "uuid4" not in source
    assert "os.environ" not in source
    assert "getenv" not in source

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "getenv", _fail_if_called("environment"))
    monkeypatch.setattr(
        socket,
        "create_connection",
        _fail_if_called("network"),
    )
    probe_name = "_replay_runner_v4_import_safety_probe"
    spec = importlib_util.spec_from_file_location(probe_name, source_path)
    assert spec is not None and spec.loader is not None
    probe_module = importlib_util.module_from_spec(spec)
    sys.modules[probe_name] = probe_module
    try:
        spec.loader.exec_module(probe_module)
    finally:
        sys.modules.pop(probe_name, None)

    assert list(tmp_path.iterdir()) == []
