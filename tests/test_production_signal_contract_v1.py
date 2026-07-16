import copy
import hashlib
import importlib
import json
import math

import pytest


MODULE_NAME = "engine.production_signal_contract_v1"


def _module():
    return importlib.import_module(MODULE_NAME)


def sha256(value):
    module = _module()
    return hashlib.sha256(module.canonical_json_bytes(value)).hexdigest()


def source_envelope(**overrides):
    setup = {
        "symbol": "BTCUSDT", "side": "LONG",
        "entry_zone": {"min": 100.0, "max": 101.0},
        "stop_loss": 95.0, "take_profit": {"tp1": 110.0, "tp2": 120.0},
        "valid_until": "2026-07-20T12:00:00Z",
        "strategy_version": "master-engine-v4", "source_payload_hash": "a" * 64,
    }
    payload = {
        "schema_version": 1, "schema_name": "production-signal-input",
        "source_commit": "1" * 40, "source_evaluation_id": "eval-001",
        "mode": "SCALP", "evaluated_at": "2026-07-16T12:00:00Z",
        "production_evidence_ref": {
            "manifest_hash": "b" * 64,
            "manifest_path": "production_run_v4_001/manifest.json",
        },
        "outcome_kind": "PUBLISHED_SIGNAL", "eligible_setups": [setup],
        "component_versions": {
            "master_engine": "master-engine-v4",
            "pre_delivery": "pre-delivery-v4",
            "production_signal_contract": "production-signal-contract-v1",
        },
    }
    payload.update(overrides)
    return payload


def no_trade_envelope(**overrides):
    payload = source_envelope(outcome_kind="NO_TRADE", eligible_setups=[])
    payload.update(overrides)
    return payload


def test_module_does_not_exist_before_green_implementation():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(MODULE_NAME)


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_contract_exports_required_surface():
    module = _module()
    required = {
        "ProductionSignalContractError", "canonical_json_bytes",
        "validate_production_signal_input", "build_signal_geometry",
        "build_publication_payload", "build_signal_id", "build_delivery_id",
        "build_source_publication_ref", "build_publication_intent",
        "build_completed_publication", "build_no_trade_evaluation",
    }
    assert required.issubset(set(vars(module)))


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_canonical_json_is_sorted_compact_utf8_and_deterministic():
    module = _module()
    payload = {"z": "é", "a": [3, 2, 1]}
    expected = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    assert module.canonical_json_bytes(payload) == expected
    assert module.canonical_json_bytes(payload) == expected


@pytest.mark.skip(reason="activated after GREEN module exists")
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_canonical_json_rejects_non_finite_numbers(value):
    module = _module()
    with pytest.raises(module.ProductionSignalContractError):
        module.canonical_json_bytes({"value": value})


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_validates_and_detaches_exact_published_signal_input():
    module = _module()
    payload = source_envelope()
    original = copy.deepcopy(payload)
    validated = module.validate_production_signal_input(payload)
    assert validated == original
    assert validated is not payload
    assert validated["eligible_setups"] is not payload["eligible_setups"]
    validated["eligible_setups"][0]["symbol"] = "ETHUSDT"
    assert payload == original


@pytest.mark.skip(reason="activated after GREEN module exists")
@pytest.mark.parametrize("mutator", [
    lambda value: value.pop("mode"), lambda value: value.update(extra="forbidden"),
    lambda value: value.update(schema_version=True), lambda value: value.update(schema_version=2),
    lambda value: value.update(schema_name="wrong"), lambda value: value.update(source_commit="abc"),
    lambda value: value.update(source_evaluation_id=""), lambda value: value.update(mode="scalp"),
    lambda value: value.update(evaluated_at="2026-07-16 12:00:00"),
    lambda value: value.update(outcome_kind="ORDER"), lambda value: value.update(eligible_setups={}),
    lambda value: value.update(component_versions=[]),
])
def test_rejects_invalid_input_envelope(mutator):
    module = _module()
    payload = source_envelope()
    mutator(payload)
    with pytest.raises(module.ProductionSignalContractError):
        module.validate_production_signal_input(payload)


@pytest.mark.skip(reason="activated after GREEN module exists")
@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
def test_accepts_exact_modes(mode):
    module = _module()
    assert module.validate_production_signal_input(source_envelope(mode=mode))["mode"] == mode


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_published_signal_requires_exactly_one_setup():
    module = _module()
    for setups in ([], source_envelope()["eligible_setups"] * 2):
        with pytest.raises(module.ProductionSignalContractError):
            module.validate_production_signal_input(source_envelope(eligible_setups=setups))


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_no_trade_requires_empty_setups():
    module = _module()
    assert module.validate_production_signal_input(no_trade_envelope())["eligible_setups"] == []
    with pytest.raises(module.ProductionSignalContractError):
        module.validate_production_signal_input(no_trade_envelope(
            eligible_setups=source_envelope()["eligible_setups"]))


@pytest.mark.skip(reason="activated after GREEN module exists")
@pytest.mark.parametrize("mutator", [
    lambda setup: setup.update(symbol=""), lambda setup: setup.update(side="BUY"),
    lambda setup: setup.update(entry_zone={"min": 102.0, "max": 101.0}),
    lambda setup: setup.update(entry_zone={"min": True, "max": 101.0}),
    lambda setup: setup.update(stop_loss=math.inf),
    lambda setup: setup.update(take_profit={"tp1": 110.0}),
    lambda setup: setup.update(valid_until="2026-07-20T12:00:00"),
    lambda setup: setup.update(strategy_version=""), lambda setup: setup.update(source_payload_hash="ABC"),
    lambda setup: setup.update(extra="forbidden"),
])
def test_rejects_invalid_signal_geometry(mutator):
    module = _module()
    payload = source_envelope()
    mutator(payload["eligible_setups"][0])
    with pytest.raises(module.ProductionSignalContractError):
        module.validate_production_signal_input(payload)


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_builds_closed_signal_geometry():
    module = _module()
    geometry = module.build_signal_geometry(source_envelope()["eligible_setups"][0])
    assert geometry == {
        "symbol": "BTCUSDT", "side": "LONG",
        "entry_zone": {"min": 100.0, "max": 101.0}, "stop_loss": 95.0,
        "take_profit": {"tp1": 110.0, "tp2": 120.0},
        "valid_until": "2026-07-20T12:00:00Z",
    }


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_signal_id_is_deterministic_and_decision_derived():
    module = _module(); envelope = source_envelope()
    geometry_hash = sha256(module.build_signal_geometry(envelope["eligible_setups"][0]))
    first = module.build_signal_id(source_envelope=envelope, signal_geometry_hash=geometry_hash,
                                   source_payload_hash="a" * 64)
    second = module.build_signal_id(source_envelope=copy.deepcopy(envelope), signal_geometry_hash=geometry_hash,
                                    source_payload_hash="a" * 64)
    assert first == second and first.startswith("PSG-") and len(first) == 68
    assert module.build_signal_id(source_envelope=source_envelope(source_evaluation_id="eval-002"),
                                  signal_geometry_hash=geometry_hash, source_payload_hash="a" * 64) != first


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_publication_payload_contains_only_authoritative_fields():
    module = _module(); envelope = source_envelope()
    geometry = module.build_signal_geometry(envelope["eligible_setups"][0])
    signal_id = module.build_signal_id(source_envelope=envelope, signal_geometry_hash=sha256(geometry),
                                       source_payload_hash="a" * 64)
    payload = module.build_publication_payload(source_envelope=envelope, signal_id=signal_id,
                                               signal_geometry=geometry)
    assert set(payload) == {"signal_id", "mode", "symbol", "side", "entry_zone", "stop_loss",
                            "take_profit", "valid_until", "strategy_version", "source_evaluation_id"}
    assert payload["signal_id"] == signal_id and payload["mode"] == "SCALP"


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_delivery_id_is_deterministic_and_destination_scoped():
    module = _module(); publication_payload = {"signal_id": "PSG-" + "1" * 64}
    payload_hash = sha256(publication_payload)
    first = module.build_delivery_id(signal_id=publication_payload["signal_id"], channel="telegram",
                                     destination_id="chat:123", publication_payload_hash=payload_hash)
    second = module.build_delivery_id(signal_id=publication_payload["signal_id"], channel="telegram",
                                      destination_id="chat:123", publication_payload_hash=payload_hash)
    assert first == second and first.startswith("PDL-") and len(first) == 68
    assert module.build_delivery_id(signal_id=publication_payload["signal_id"], channel="telegram",
                                   destination_id="chat:999", publication_payload_hash=payload_hash) != first


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_builds_phase_07_compatible_source_publication_reference():
    module = _module()
    reference = module.build_source_publication_ref(signal_id="PSG-" + "1" * 64,
        delivery_id="PDL-" + "2" * 64, mode="SCALP", published_at="2026-07-16T12:01:00Z",
        source_payload_hash="a" * 64)
    assert reference == {"signal_id": "PSG-" + "1" * 64, "delivery_id": "PDL-" + "2" * 64,
                        "mode": "SCALP", "published_at": "2026-07-16T12:01:00Z",
                        "source_payload_hash": "a" * 64}
    from engine.paper_signal_contract_v1 import validate_source_publication_ref
    assert validate_source_publication_ref(reference) == reference


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_builds_intent_with_exact_no_capital_boundary():
    module = _module(); envelope = source_envelope()
    geometry = module.build_signal_geometry(envelope["eligible_setups"][0]); gh = sha256(geometry)
    signal_id = module.build_signal_id(source_envelope=envelope, signal_geometry_hash=gh,
                                       source_payload_hash="a" * 64)
    publication_payload = module.build_publication_payload(source_envelope=envelope, signal_id=signal_id,
                                                            signal_geometry=geometry); ph = sha256(publication_payload)
    delivery_id = module.build_delivery_id(signal_id=signal_id, channel="telegram", destination_id="chat:123",
                                           publication_payload_hash=ph)
    intent = module.build_publication_intent(source_envelope=envelope, signal_id=signal_id, delivery_id=delivery_id,
        published_at="2026-07-16T12:01:00Z", channel="telegram", destination_id="chat:123",
        signal_geometry=geometry, signal_geometry_hash=gh, publication_payload=publication_payload,
        publication_payload_hash=ph, source_payload_hash="a" * 64)
    assert intent["schema_name"] == "production-signal-publication"
    assert intent["classification"] == "PRODUCTION_SIGNAL"
    assert intent["execution_boundary"] == "LIVE_SIGNAL_PUBLICATION_NO_CAPITAL"
    assert intent["capital_exposure"] == "NONE" and intent["order_execution"] == "PROHIBITED"
    assert intent["position_authority"] == "TELEGRAM_USER_REPORT"
    assert intent["delivery_state"] == "INTENT_PERSISTED" and intent["delivery_receipt"] is None
    assert intent["failure"] is None


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_completed_success_preserves_identity_and_adds_receipt():
    module = _module(); envelope = source_envelope(); geometry = module.build_signal_geometry(envelope["eligible_setups"][0])
    gh = sha256(geometry); signal_id = module.build_signal_id(source_envelope=envelope, signal_geometry_hash=gh, source_payload_hash="a" * 64)
    publication_payload = module.build_publication_payload(source_envelope=envelope, signal_id=signal_id, signal_geometry=geometry)
    ph = sha256(publication_payload); delivery_id = module.build_delivery_id(signal_id=signal_id, channel="telegram", destination_id="chat:123", publication_payload_hash=ph)
    intent = module.build_publication_intent(source_envelope=envelope, signal_id=signal_id, delivery_id=delivery_id, published_at="2026-07-16T12:01:00Z", channel="telegram", destination_id="chat:123", signal_geometry=geometry, signal_geometry_hash=gh, publication_payload=publication_payload, publication_payload_hash=ph, source_payload_hash="a" * 64)
    completed = module.build_completed_publication(intent=intent, delivery_receipt={"channel": "telegram", "destination_id": "chat:123", "external_delivery_id": "telegram-message-001", "delivered_at": "2026-07-16T12:01:01Z"}, failure=None)
    assert completed["delivery_state"] == "DELIVERY_SUCCEEDED" and completed["signal_id"] == signal_id and completed["delivery_id"] == delivery_id
    assert completed["failure"] is None and len(completed["content_hash"]) == 64


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_completed_failure_is_closed_and_sanitized():
    module = _module(); envelope = source_envelope(); geometry = module.build_signal_geometry(envelope["eligible_setups"][0]); gh = sha256(geometry)
    signal_id = module.build_signal_id(source_envelope=envelope, signal_geometry_hash=gh, source_payload_hash="a" * 64)
    publication_payload = module.build_publication_payload(source_envelope=envelope, signal_id=signal_id, signal_geometry=geometry); ph = sha256(publication_payload)
    delivery_id = module.build_delivery_id(signal_id=signal_id, channel="telegram", destination_id="chat:123", publication_payload_hash=ph)
    intent = module.build_publication_intent(source_envelope=envelope, signal_id=signal_id, delivery_id=delivery_id, published_at="2026-07-16T12:01:00Z", channel="telegram", destination_id="chat:123", signal_geometry=geometry, signal_geometry_hash=gh, publication_payload=publication_payload, publication_payload_hash=ph, source_payload_hash="a" * 64)
    completed = module.build_completed_publication(intent=intent, delivery_receipt=None, failure={"primary_code": "DELIVERY_ADAPTER_FAILED", "component": "delivery_adapter", "message": "delivery adapter failed"})
    assert completed["delivery_state"] == "DELIVERY_FAILED" and completed["delivery_receipt"] is None
    assert completed["failure"] == {"primary_code": "DELIVERY_ADAPTER_FAILED", "component": "delivery_adapter", "message": "delivery adapter failed"}


@pytest.mark.skip(reason="activated after GREEN module exists")
def test_no_trade_evaluation_has_no_signal_or_delivery_identity():
    module = _module()
    result = module.build_no_trade_evaluation(source_envelope=no_trade_envelope(), recorded_at="2026-07-16T12:01:00Z")
    assert result["schema_name"] == "production-signal-evaluation" and result["outcome_kind"] == "NO_TRADE"
    assert result["signal_id"] is None and result["delivery_id"] is None and result["source_publication_ref"] is None
    assert result["delivery_state"] is None and len(result["content_hash"]) == 64


@pytest.mark.skip(reason="activated after GREEN module exists")
@pytest.mark.parametrize("forbidden_key", ["api_secret", "private_key", "bot_token", "exchange_credentials", "order_payload", "position_size", "wallet", "balance"])
def test_rejects_forbidden_sensitive_or_capital_fields(forbidden_key):
    module = _module(); payload = source_envelope(); payload[forbidden_key] = "secret"
    with pytest.raises(module.ProductionSignalContractError):
        module.validate_production_signal_input(payload)
