import copy
import importlib
import json
from pathlib import Path

import pytest

MODULE_NAME = "engine.production_signal_service_v1"

@pytest.fixture
def service_module(): return importlib.import_module(MODULE_NAME)

def published_source(source_evaluation_id="eval-001"):
    return {"schema_version":1,"schema_name":"production-signal-input","source_commit":"1"*40,"source_evaluation_id":source_evaluation_id,"mode":"SCALP","evaluated_at":"2026-07-16T12:00:00Z","production_evidence_ref":{"manifest_hash":"b"*64,"manifest_path":"production_run_v4_001/manifest.json"},"outcome_kind":"PUBLISHED_SIGNAL","eligible_setups":[{"symbol":"BTCUSDT","side":"LONG","entry_zone":{"min":100.0,"max":101.0},"stop_loss":95.0,"take_profit":{"tp1":110.0,"tp2":120.0},"valid_until":"2026-07-20T12:00:00Z","strategy_version":"master-engine-v4","source_payload_hash":"a"*64}],"component_versions":versions()}

def no_trade_source():
    p=published_source("eval-no-trade-001"); p["outcome_kind"]="NO_TRADE"; p["eligible_setups"]=[]; return p

def versions(): return {"master_engine":"master-engine-v4","pre_delivery":"pre-delivery-v4","production_signal_contract":"production-signal-contract-v1","production_signal_artifact":"production-signal-artifact-v1","production_signal_service":"production-signal-service-v1"}
def receipt(destination_id="chat:123"): return {"channel":"telegram","destination_id":destination_id,"external_delivery_id":"telegram-message-001","delivered_at":"2026-07-16T12:01:01Z"}
_DEFAULT=object()
def call(module,root,source=None,adapter=_DEFAULT,**kwargs): return module.run_production_signal_service_v1(source_envelope=source or published_source(),publication_root=root,channel=kwargs.get("channel","telegram"),destination_id=kwargs.get("destination_id","chat:123"),published_at=kwargs.get("published_at","2026-07-16T12:01:00Z"),delivery_adapter=kwargs.get("delivery_adapter", adapter if adapter is not _DEFAULT else (lambda payload,**opts:receipt(opts["destination_id"]))),component_versions=kwargs.get("component_versions",versions()))

def test_exports_required_service_surface(service_module): assert {"ProductionSignalServiceError","run_production_signal_service_v1"}.issubset(vars(service_module))

def test_success_persists_intent_before_adapter(service_module,tmp_path):
    root=tmp_path/"production_signal"; calls=[]
    def adapter(payload,*,channel,destination_id):
        files=list(root.rglob("*.json")); assert len(files)==1
        persisted=json.loads(files[0].read_text()); assert persisted["delivery_state"]=="INTENT_PERSISTED" and persisted["publication_payload"]==payload; calls.append(1); return receipt(destination_id)
    result=call(service_module,root,adapter=adapter); assert calls==[1] and result["publication"]["delivery_state"]=="DELIVERY_SUCCEEDED" and result["artifact_path"].exists()

def test_adapter_receives_closed_structured_payload(service_module,tmp_path):
    captured={}
    def adapter(payload,**options): captured.update(payload=copy.deepcopy(payload),**options); return receipt(options["destination_id"])
    call(service_module,tmp_path/"production_signal",adapter=adapter)
    assert set(captured["payload"])=={"signal_id","mode","symbol","side","entry_zone","stop_loss","take_profit","valid_until","strategy_version","source_evaluation_id"}

def test_failure_persists_sanitized_completion_without_retry(service_module,tmp_path):
    calls=[]
    def adapter(*args,**kwargs): calls.append(1); raise RuntimeError("Traceback /home/secret bot_token=abc")
    r=call(service_module,tmp_path/"production_signal",adapter=adapter); assert calls==[1] and r["publication"]["delivery_state"]=="DELIVERY_FAILED" and r["publication"]["failure"]=={"primary_code":"DELIVERY_ADAPTER_FAILED","component":"delivery_adapter","message":"delivery adapter failed"}
    assert "bot_token" not in r["artifact_path"].read_text()

@pytest.mark.parametrize("bad",[{"channel":"email","destination_id":"chat:123","external_delivery_id":"m","delivered_at":"2026-07-16T12:01:01Z"},{"channel":"telegram","destination_id":"chat:999","external_delivery_id":"m","delivered_at":"2026-07-16T12:01:01Z"},{"channel":"telegram","destination_id":"chat:123","external_delivery_id":"m","delivered_at":"2026-07-16T12:00:59Z"}])
def test_invalid_receipt_fails_closed(service_module,tmp_path,bad):
    with pytest.raises(service_module.ProductionSignalServiceError): call(service_module,tmp_path/"production_signal",adapter=lambda *args,**kwargs:copy.deepcopy(bad))

@pytest.mark.parametrize("failing",[False,True])
def test_completed_identity_is_idempotent_without_adapter(service_module,tmp_path,failing):
    root=tmp_path/"production_signal"; calls=[]
    def first(*args,**kwargs):
        calls.append(1)
        if failing: raise RuntimeError("failure")
        return receipt()
    a=call(service_module,root,adapter=first)
    b=call(service_module,root,adapter=lambda *args,**kwargs:pytest.fail("automatic retry"))
    assert calls==[1] and a["publication"]==b["publication"] and a["artifact_path"]==b["artifact_path"]

def test_distinct_destination_has_distinct_delivery(service_module,tmp_path):
    root=tmp_path/"production_signal"; a=call(service_module,root,adapter=lambda p,**k:receipt("chat:123")); b=call(service_module,root,destination_id="chat:999",adapter=lambda p,**k:receipt("chat:999")); assert a["publication"]["signal_id"]==b["publication"]["signal_id"] and a["publication"]["delivery_id"]!=b["publication"]["delivery_id"]

def test_no_trade_never_calls_adapter_and_is_idempotent(service_module,tmp_path):
    root=tmp_path/"production_signal"; forbidden=lambda *args,**kwargs:pytest.fail("NO_TRADE adapter call")
    a=call(service_module,root,source=no_trade_source(),adapter=forbidden); b=call(service_module,root,source=copy.deepcopy(no_trade_source()),adapter=forbidden)
    assert a["publication"] is None and a["source_publication_ref"] is None and a["evaluation"]["outcome_kind"]=="NO_TRADE" and b["evaluation"]==a["evaluation"]

@pytest.mark.parametrize("field,value",[("channel",""),("destination_id",""),("published_at","2026-07-16 12:01:00"),("delivery_adapter",None),("component_versions",{})])
def test_invalid_configuration_fails_before_writing(service_module,tmp_path,field,value):
    root=tmp_path/"production_signal"; options={field:value}
    with pytest.raises(service_module.ProductionSignalServiceError): call(service_module,root,**options)
    assert not root.exists()

def test_invalid_source_and_component_mismatch_fail_before_write(service_module,tmp_path):
    bad=published_source(); bad["mode"]="scalp"
    with pytest.raises(service_module.ProductionSignalServiceError): call(service_module,tmp_path/"one",source=bad)
    v=versions(); v["master_engine"]="conflict"
    with pytest.raises(service_module.ProductionSignalServiceError): call(service_module,tmp_path/"two",component_versions=v)

def test_inputs_are_not_mutated(service_module,tmp_path):
    s=published_source(); v=versions(); os=copy.deepcopy(s); ov=copy.deepcopy(v); call(service_module,tmp_path/"production_signal",source=s,component_versions=v); assert s==os and v==ov

def test_service_has_no_transport_environment_or_retry_code(service_module):
    source=Path(service_module.__file__).read_text(); forbidden=("import telegram","from telegram","import ccxt","from ccxt","import binance","from binance","import requests","from requests","import httpx","from httpx","os.environ","os.getenv","while True","retry","backoff"); assert not any(x in source.casefold() for x in forbidden)
