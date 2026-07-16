import copy
import importlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from engine.production_signal_contract_v1 import (
    build_completed_publication, build_delivery_id, build_no_trade_evaluation,
    build_publication_intent, build_publication_payload, build_signal_geometry,
    build_signal_id, canonical_json_bytes,
)

MODULE_NAME = "engine.production_signal_artifact_v1"

def source_envelope(outcome_kind="PUBLISHED_SIGNAL", source_evaluation_id="eval-001"):
    setups = [{"symbol":"BTCUSDT","side":"LONG","entry_zone":{"min":100.0,"max":101.0},"stop_loss":95.0,"take_profit":{"tp1":110.0,"tp2":120.0},"valid_until":"2026-07-20T12:00:00Z","strategy_version":"master-engine-v4","source_payload_hash":"a"*64}] if outcome_kind == "PUBLISHED_SIGNAL" else []
    return {"schema_version":1,"schema_name":"production-signal-input","source_commit":"1"*40,"source_evaluation_id":source_evaluation_id,"mode":"SCALP","evaluated_at":"2026-07-16T12:00:00Z","production_evidence_ref":{"manifest_hash":"b"*64,"manifest_path":"production_run_v4_001/manifest.json"},"outcome_kind":outcome_kind,"eligible_setups":setups,"component_versions":{"master_engine":"master-engine-v4","pre_delivery":"pre-delivery-v4","production_signal_contract":"production-signal-contract-v1"}}

def _hash(v):
    import hashlib
    return hashlib.sha256(canonical_json_bytes(v)).hexdigest()

def build_intent(destination_id="chat:123"):
    e=source_envelope(); s=e["eligible_setups"][0]; g=build_signal_geometry(s); gh=_hash(g)
    sid=build_signal_id(source_envelope=e,signal_geometry_hash=gh,source_payload_hash=s["source_payload_hash"])
    p=build_publication_payload(source_envelope=e,signal_id=sid,signal_geometry=g); ph=_hash(p)
    did=build_delivery_id(signal_id=sid,channel="telegram",destination_id=destination_id,publication_payload_hash=ph)
    return build_publication_intent(source_envelope=e,signal_id=sid,delivery_id=did,published_at="2026-07-16T12:01:00Z",channel="telegram",destination_id=destination_id,signal_geometry=g,signal_geometry_hash=gh,publication_payload=p,publication_payload_hash=ph,source_payload_hash=s["source_payload_hash"])

def success(i):
    return build_completed_publication(intent=i,delivery_receipt={"channel":i["channel"],"destination_id":i["destination_id"],"external_delivery_id":"telegram-message-001","delivered_at":"2026-07-16T12:01:01Z"},failure=None)

def failure(i):
    return build_completed_publication(intent=i,delivery_receipt=None,failure={"primary_code":"DELIVERY_ADAPTER_FAILED","component":"delivery_adapter","message":"delivery adapter failed"})

def no_trade(): return build_no_trade_evaluation(source_envelope=source_envelope("NO_TRADE"), recorded_at="2026-07-16T12:01:00Z")
def bytes_for(v): return canonical_json_bytes(v)+b"\n"

@pytest.fixture
def artifact_module(): return importlib.import_module(MODULE_NAME)

def test_exports_required_artifact_surface(artifact_module):
    assert {"ProductionSignalArtifactError","publish_publication_intent","publish_completed_publication","publish_no_trade_evaluation","read_publication_artifact"}.issubset(vars(artifact_module))

def test_publishes_intent_to_canonical_path(artifact_module,tmp_path):
    i=build_intent(); p=artifact_module.publish_publication_intent(publication_root=tmp_path/"production_signal",payload=i)
    assert p == (tmp_path/"production_signal"/"publications"/i["signal_id"]/f'{i["delivery_id"]}.json').resolve(); assert p.read_bytes()==bytes_for(i)

def test_publication_does_not_mutate_input(artifact_module,tmp_path):
    i=build_intent(); original=copy.deepcopy(i); artifact_module.publish_publication_intent(publication_root=tmp_path/"production_signal",payload=i); assert i==original

def test_identical_intent_publication_is_idempotent(artifact_module,tmp_path):
    i=build_intent(); r=tmp_path/"production_signal"; a=artifact_module.publish_publication_intent(publication_root=r,payload=i); b=artifact_module.publish_publication_intent(publication_root=r,payload=copy.deepcopy(i)); assert a==b and b.read_bytes()==bytes_for(i)

def test_conflicting_intent_identity_is_rejected(artifact_module,tmp_path):
    i=build_intent(); r=tmp_path/"production_signal"; artifact_module.publish_publication_intent(publication_root=r,payload=i); c=copy.deepcopy(i); c["component_versions"]["master_engine"]="conflict"; c.pop("content_hash"); c["content_hash"]=_hash(c)
    with pytest.raises(artifact_module.ProductionSignalArtifactError,match="collision"): artifact_module.publish_publication_intent(publication_root=r,payload=c)

@pytest.mark.parametrize("builder",[success,failure])
def test_completion_replaces_and_is_idempotent(artifact_module,tmp_path,builder):
    i=build_intent(); r=tmp_path/"production_signal"; artifact_module.publish_publication_intent(publication_root=r,payload=i); c=builder(i); a=artifact_module.publish_completed_publication(publication_root=r,payload=c); b=artifact_module.publish_completed_publication(publication_root=r,payload=copy.deepcopy(c)); assert a==b and a.read_bytes()==bytes_for(c)

def test_completion_requires_existing_matching_intent(artifact_module,tmp_path):
    with pytest.raises(artifact_module.ProductionSignalArtifactError,match="intent"): artifact_module.publish_completed_publication(publication_root=tmp_path/"production_signal",payload=success(build_intent()))

def test_completed_record_rejects_conflicting_replacement(artifact_module,tmp_path):
    i=build_intent(); r=tmp_path/"production_signal"; artifact_module.publish_publication_intent(publication_root=r,payload=i); artifact_module.publish_completed_publication(publication_root=r,payload=success(i))
    with pytest.raises(artifact_module.ProductionSignalArtifactError,match="collision"): artifact_module.publish_completed_publication(publication_root=r,payload=failure(i))

def test_no_trade_artifact_and_idempotency(artifact_module,tmp_path):
    e=no_trade(); r=tmp_path/"production_signal"; a=artifact_module.publish_no_trade_evaluation(publication_root=r,payload=e); b=artifact_module.publish_no_trade_evaluation(publication_root=r,payload=copy.deepcopy(e)); assert a==b and a.read_bytes()==bytes_for(e)

@pytest.mark.parametrize("name",["replay","replay_artifacts","production_evidence_v4","validated_snapshots_v4","v4_outcomes","top5_watchlist_v4","pre_delivery_v4","pine_delivery_v4","telegram_state","worker_state_v4","quota_slot_v4","position_ledger","paper_signal","shadow_release"])
def test_rejects_protected_roots(artifact_module,tmp_path,name):
    with pytest.raises(artifact_module.ProductionSignalArtifactError): artifact_module.publish_publication_intent(publication_root=tmp_path/name,payload=build_intent())

def test_rejects_symlink_root(artifact_module,tmp_path):
    target=tmp_path/"actual"; target.mkdir(); alias=tmp_path/"production_signal"; alias.symlink_to(target,target_is_directory=True)
    with pytest.raises(artifact_module.ProductionSignalArtifactError,match="symlink"): artifact_module.publish_publication_intent(publication_root=alias,payload=build_intent())

def test_rejects_non_directory_root(artifact_module,tmp_path):
    r=tmp_path/"production_signal"; r.write_text("x")
    with pytest.raises(artifact_module.ProductionSignalArtifactError): artifact_module.publish_publication_intent(publication_root=r,payload=build_intent())

def test_rejects_invalid_identity_read(artifact_module,tmp_path):
    with pytest.raises(artifact_module.ProductionSignalArtifactError): artifact_module.read_publication_artifact(publication_root=tmp_path/"production_signal",signal_id="../escape",delivery_id="PDL-"+"1"*64)

def test_concurrent_identical_intents_converge(artifact_module,tmp_path):
    i=build_intent(); r=tmp_path/"production_signal"
    with ThreadPoolExecutor(max_workers=4) as x: paths=list(x.map(lambda _: artifact_module.publish_publication_intent(publication_root=r,payload=copy.deepcopy(i)),range(8)))
    assert len(set(paths))==1 and paths[0].read_bytes()==bytes_for(i)

def test_no_temporary_or_lock_files_remain(artifact_module,tmp_path):
    r=tmp_path/"production_signal"; artifact_module.publish_publication_intent(publication_root=r,payload=build_intent()); assert not [p for p in r.rglob("*") if p.is_file() and (".tmp" in p.name or p.suffix==".lock")]

def test_artifact_module_has_no_transport_or_environment_imports(artifact_module):
    source=Path(artifact_module.__file__).read_text(); assert not any(x in source for x in ("import telegram","from telegram","import ccxt","from ccxt","import binance","from binance","import requests","from requests","import httpx","from httpx","os.environ","os.getenv"))
