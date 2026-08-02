import copy
import hashlib
import inspect
import json
import re
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import engine.master_engine_v4 as master_module
import engine.run_production_signal_v1 as entrypoint_module
from engine import controlled_production_signal_cycle_v1 as controlled
from engine.phase09r_observability_v1 import (
    BOUNDARY_NO,
    MASTER_ENGINE_SETUP_CONSTRUCTION_FAILED,
    Phase09RExit7Failure,
)
from engine.production_signal_contract_v1 import (
    validate_production_signal_input,
)


SOURCE_COMMIT = "4" * 40
SOURCE_ENVELOPE_FIELDS = {
    "schema_version",
    "schema_name",
    "source_commit",
    "source_evaluation_id",
    "mode",
    "evaluated_at",
    "production_evidence_ref",
    "outcome_kind",
    "eligible_setups",
    "component_versions",
}
ELIGIBLE_SETUP_FIELDS = {
    "symbol",
    "side",
    "entry_zone",
    "stop_loss",
    "take_profit",
    "valid_until",
    "strategy_version",
    "source_payload_hash",
}


class UnreachableAdapter:
    def __init__(self):
        self.calls = 0
        self.rejection_reason = None
        self.malformed_receipt = False

    def __call__(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Telegram adapter must remain unreachable")


class UnsupportedValue:
    marker = "UNSUPPORTED_VALUE_CONTENT_MUST_NOT_APPEAR"

    def __init__(self):
        self.str_calls = 0
        self.repr_calls = 0

    def __str__(self):
        self.str_calls += 1
        raise AssertionError("str fallback must not be used")

    def __repr__(self):
        self.repr_calls += 1
        raise AssertionError("repr fallback must not be used")


def _live_shaped_candidate():
    return {
        "symbol": "SYNTHETIC_PAIR",
        "reference_candle_at": "2040-01-02T00:00:00Z",
        "reference_price": 10.5,
        "golden_zone": {
            "direction": "BULLISH",
            "swing_low_index": 2,
            "swing_high_index": 7,
            "swing_low_at": pd.Timestamp(
                "2040-01-02T03:04:05.123456789+02:30"
            ),
            "swing_high_at": pd.Timestamp(
                "2040-01-03T04:05:06.987654321+02:30"
            ),
            "swing_low": 8.0,
            "swing_high": 14.0,
            "levels": {
                "lower": 9.0,
                "upper": 13.0,
            },
            "entry_zone": {
                "price_low": 10.0,
                "price_high": 11.0,
            },
            "stop_loss": {
                "price": 9.0,
            },
            "take_profit": {
                "price": 12.0,
            },
        },
        "python_score": 90.0,
        "final_rank_score": 91.0,
        "bos": True,
        "choch": False,
        "metadata": {
            "flags": [True, None, "synthetic"],
        },
    }


def _live_shaped_out(candidate=None):
    selected = candidate or _live_shaped_candidate()
    return {
        "controlled_top10": [selected],
        "final_top5": [selected],
        "usage": {},
    }


def _reverse_mappings(value):
    if isinstance(value, dict):
        return {
            key: _reverse_mappings(item)
            for key, item in reversed(list(value.items()))
        }
    if isinstance(value, list):
        return [_reverse_mappings(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_reverse_mappings(item) for item in value)
    return value


def _master_fakes(tmp_path, out):
    evidence_path = tmp_path / "synthetic-evidence.json"
    evidence_path.write_bytes(b"{}\n")
    return {
        "scanner": lambda: object(),
        "pipeline": lambda _scanner_result: out,
        "snapshot_saver": lambda _out, now: tmp_path / "snapshot.json",
        "outcome_saver": lambda _top5, **kwargs: tmp_path / "outcome.json",
        "watchlist_saver": lambda _top5: tmp_path / "top-five.json",
        "pre_delivery_runner": lambda *args, **kwargs: {
            "delivery_artifact_path": tmp_path / "pre-delivery.json",
            "tradingview_watchlist_path": tmp_path / "watchlist.txt",
        },
        "closed_candle_provider": lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("closed-candle provider must remain unreachable")
        ),
        "production_evidence_saver": lambda **kwargs: evidence_path,
        "now_provider": lambda: datetime(2040, 1, 4, 5, 6, 7),
    }


def _run_master_with_capture(
    tmp_path,
    monkeypatch,
    out,
    adapter,
):
    service_calls = []

    def capture_service(**kwargs):
        service_calls.append(kwargs)
        return {"status": "SYNTHETIC_CAPTURED"}

    monkeypatch.setattr(
        master_module,
        "run_production_signal_service_v1",
        capture_service,
    )
    monkeypatch.setattr(
        master_module.subprocess,
        "check_output",
        lambda *args, **kwargs: (SOURCE_COMMIT + "\n").encode("ascii"),
    )
    result = master_module.run_master_engine_v4(
        outcome_invocation_id="a" * 32,
        **_master_fakes(tmp_path, out),
        enable_publication=True,
        delivery_adapter=adapter,
        destination_id="SYNTHETIC_DESTINATION",
        publication_root=tmp_path / "publications",
    )
    return result, service_calls


def test_proven_live_shape_reaches_service_with_canonical_timestamps(
    tmp_path,
    monkeypatch,
    capsys,
):
    candidate = _live_shaped_candidate()
    original = copy.deepcopy(candidate)
    out = _live_shaped_out(candidate)
    adapter = UnreachableAdapter()

    result, service_calls = _run_master_with_capture(
        tmp_path,
        monkeypatch,
        out,
        adapter,
    )

    assert len(service_calls) == 1
    assert adapter.calls == 0
    assert result["production_signal_out"] == {
        "status": "SYNTHETIC_CAPTURED"
    }
    source = service_calls[0]["source_envelope"]
    assert set(source) == SOURCE_ENVELOPE_FIELDS
    assert len(source["eligible_setups"]) == 1
    assert set(source["eligible_setups"][0]) == ELIGIBLE_SETUP_FIELDS
    json.dumps(source["eligible_setups"], allow_nan=False)
    assert validate_production_signal_input(source) == source

    normalized = master_module._normalize_eligible_setup(candidate)
    assert normalized["golden_zone"]["swing_high_at"] == (
        original["golden_zone"]["swing_high_at"].isoformat()
    )
    assert normalized["golden_zone"]["swing_low_at"] == (
        original["golden_zone"]["swing_low_at"].isoformat()
    )
    assert isinstance(candidate["golden_zone"]["swing_high_at"], pd.Timestamp)
    assert isinstance(candidate["golden_zone"]["swing_low_at"], pd.Timestamp)
    assert candidate == original
    assert capsys.readouterr().err == ""


def test_normalization_returns_a_recursive_copy_without_mutating_input():
    candidate = _live_shaped_candidate()
    original = copy.deepcopy(candidate)

    normalized = master_module._normalize_eligible_setup(candidate)

    assert candidate == original
    assert normalized is not candidate
    assert normalized["golden_zone"] is not candidate["golden_zone"]
    assert normalized["metadata"] is not candidate["metadata"]
    assert normalized["metadata"]["flags"] is not candidate["metadata"]["flags"]
    assert isinstance(candidate["golden_zone"]["swing_high_at"], pd.Timestamp)
    assert isinstance(normalized["golden_zone"]["swing_high_at"], str)


def test_hash_is_deterministic_across_evaluations_and_mapping_order():
    candidate = _live_shaped_candidate()
    reordered = _reverse_mappings(candidate)

    first = master_module._hash_payload(
        master_module._normalize_eligible_setup(candidate)
    )
    second = master_module._hash_payload(
        master_module._normalize_eligible_setup(candidate)
    )
    reordered_hash = master_module._hash_payload(
        master_module._normalize_eligible_setup(reordered)
    )

    assert first == second == reordered_hash


def test_json_native_hash_matches_pre_remediation_expression_exactly():
    payload = {
        "symbol": "SYNTHETIC_PAIR",
        "active": True,
        "optional": None,
        "score": 91.25,
        "nested": {
            "values": [1, 2, 3],
            "label": "synthetic",
        },
    }
    baseline = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    normalized = master_module._normalize_eligible_setup(payload)

    assert normalized == payload
    assert normalized is not payload
    assert master_module._hash_payload(normalized) == baseline


def test_nested_list_and_tuple_timestamps_normalize_without_reordering():
    first = pd.Timestamp("2041-02-03T04:05:06.123456789Z")
    second = pd.Timestamp("2041-02-04T05:06:07.987654321Z")
    payload = {
        "list_values": ["before", first, "after"],
        "tuple_values": (second, 7, False),
    }

    normalized = master_module._normalize_eligible_setup(payload)

    assert normalized["list_values"] == ["before", first.isoformat(), "after"]
    assert normalized["tuple_values"] == (second.isoformat(), 7, False)
    assert type(normalized["list_values"]) is list
    assert type(normalized["tuple_values"]) is tuple


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        b"bytes",
        {"set-member"},
        Decimal("1.25"),
        np.array([1, 2]),
        pd.Series([1, 2]),
        pd.DataFrame({"column": [1]}),
        UnsupportedValue(),
    ],
)
def test_unsupported_types_and_nonfinite_floats_fail_closed(value):
    with pytest.raises(TypeError):
        master_module._normalize_eligible_setup({"unsupported": value})


def test_non_string_mapping_keys_fail_closed():
    with pytest.raises(TypeError):
        master_module._normalize_eligible_setup({1: "value"})


def test_unsupported_object_stays_in_setup_stage_and_entrypoint_exit7(
    tmp_path,
    monkeypatch,
    capsys,
):
    unsupported = UnsupportedValue()
    candidate = _live_shaped_candidate()
    candidate["metadata"]["unsupported"] = unsupported
    out = _live_shaped_out(candidate)
    adapter = UnreachableAdapter()
    service_calls = []
    adapter_constructor_calls = []
    config_loader_calls = []
    synthetic_config = SimpleNamespace(
        bot_token="fixture-only-token",
        max_response_chars=4000,
    )
    environment = {
        "TELEGRAM_DESTINATION_ID": "SYNTHETIC_DESTINATION",
        "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(tmp_path / "state.json"),
    }

    monkeypatch.setattr(
        master_module,
        "run_production_signal_service_v1",
        lambda **kwargs: service_calls.append(kwargs),
    )
    monkeypatch.setattr(
        master_module.subprocess,
        "check_output",
        lambda *args, **kwargs: (SOURCE_COMMIT + "\n").encode("ascii"),
    )

    with pytest.raises(Phase09RExit7Failure) as raised:
        master_module.run_master_engine_v4(
            outcome_invocation_id="a" * 32,
            **_master_fakes(tmp_path, out),
            enable_publication=True,
            delivery_adapter=adapter,
            destination_id="SYNTHETIC_DESTINATION",
            publication_root=tmp_path / "publications",
        )
    assert raised.value.failure_stage == "ELIGIBLE_SETUP_CONSTRUCTION"
    assert raised.value.failure_code == MASTER_ENGINE_SETUP_CONSTRUCTION_FAILED
    assert raised.value.exception_class == "TypeError"
    assert raised.value.telegram_boundary_reached == BOUNDARY_NO

    def fail_e6_runtime(**_kwargs):
        raise TypeError(UnsupportedValue.marker)

    def build_adapter(*args, **kwargs):
        adapter_constructor_calls.append((args, kwargs))
        return adapter

    def load_config(value):
        assert value is environment
        config_loader_calls.append(value)
        return synthetic_config

    exit_code = entrypoint_module.main(
        outcome_invocation_id="a" * 32,
        e6_enabled=True,
        authorization=controlled.ControlledProductionSignalCycleAuthorizationV1(
            **{name: True for name, _ in controlled._GATES}
        ),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=fail_e6_runtime,
        environment=environment,
        telegram_config_loader=load_config,
        telegram_delivery_adapter_factory=build_adapter,
    )

    captured = capsys.readouterr()
    assert exit_code == 7
    assert config_loader_calls == [environment]
    assert len(adapter_constructor_calls) == 0
    assert adapter_constructor_calls == []
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event == {
        "event": "PHASE09R_EXIT7",
        "schema_version": 1,
        "exit_code": 7,
        "failure_code": "SERVICE_INVOCATION_INVALID",
        "failure_stage": "E6_RUNTIME_REQUEST_CONSTRUCTION",
        "exception_class": "TypeError",
        "telegram_boundary_reached": "NO",
    }
    assert UnsupportedValue.marker not in captured.err
    assert unsupported.str_calls == 0
    assert unsupported.repr_calls == 0
    assert service_calls == []
    assert adapter.calls == 0


def test_normalization_path_has_no_generic_serializer_fallback():
    normalizer_source = inspect.getsource(
        master_module._normalize_eligible_setup
    )
    hash_source = inspect.getsource(master_module._hash_payload)
    selected_source = normalizer_source + "\n" + hash_source

    assert "default=str" not in selected_source
    assert "default = str" not in selected_source
    assert re.search(r"\bstr\s*\(\s*value", selected_source) is None
    assert re.search(r"\brepr\s*\(", selected_source) is None
    assert "pickle" not in selected_source
