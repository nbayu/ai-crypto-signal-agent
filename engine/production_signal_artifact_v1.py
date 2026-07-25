"""Fail-closed Phase 09 production-signal artifact publication."""
from __future__ import annotations
import copy, hashlib, json, os, re, stat, tempfile, time
from pathlib import Path
from typing import Any, Mapping
from engine.production_signal_contract_v1 import (
    DELIVERY_FAILED, DELIVERY_INTENT_PERSISTED, DELIVERY_SUCCEEDED,
    OUTCOME_NO_TRADE, PRODUCTION_SIGNAL_EVALUATION_SCHEMA,
    PRODUCTION_SIGNAL_SCHEMA_VERSION, ProductionSignalContractError,
    canonical_json_bytes,
)

PUBLICATION_DIRECTORY="publications"; EVALUATION_DIRECTORY="evaluations"; LOCK_DIRECTORY=".locks"
_PROTECTED={"replay","replay_artifacts","production_evidence_v4","validated_snapshots_v4","v4_outcomes","top5_watchlist_v4","pre_delivery_v4","pine_delivery_v4","telegram_state","worker_state_v4","quota_slot_v4","position_ledger","paper_signal","shadow_release"}
_ID=re.compile(r"^PSG-[0-9a-f]{64}$"); _DID=re.compile(r"^PDL-[0-9a-f]{64}$"); _EID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

class ProductionSignalArtifactError(RuntimeError): pass

def _fail(fn):
    try: return fn()
    except ProductionSignalArtifactError: raise
    except (ProductionSignalContractError, TypeError, ValueError, OSError, json.JSONDecodeError) as e: raise ProductionSignalArtifactError("invalid production signal artifact") from e

def _validate_pub(p):
    if not isinstance(p, Mapping) or p.get("schema_name") != "production-signal-publication": raise ProductionSignalArtifactError("invalid publication")
    x=copy.deepcopy(dict(p))
    required={"schema_version","schema_name","classification","execution_boundary","capital_exposure","order_execution","position_authority","source_commit","source_evaluation_id","mode","outcome_kind","signal_id","delivery_id","published_at","channel","destination_id","signal_geometry","signal_geometry_hash","publication_payload","publication_payload_hash","source_payload_hash","source_publication_ref","delivery_state","delivery_receipt","failure","component_versions","content_hash"}
    if set(x)!=required or x.get("schema_version")!=1 or not _ID.fullmatch(str(x.get("signal_id"))) or not _DID.fullmatch(str(x.get("delivery_id"))): raise ProductionSignalArtifactError("invalid publication")
    if x.get("delivery_state") not in {DELIVERY_INTENT_PERSISTED,DELIVERY_SUCCEEDED,DELIVERY_FAILED}: raise ProductionSignalArtifactError("invalid publication state")
    if x.get("delivery_state")==DELIVERY_INTENT_PERSISTED and (x.get("delivery_receipt") is not None or x.get("failure") is not None): raise ProductionSignalArtifactError("invalid publication intent")
    if x.get("delivery_state")==DELIVERY_SUCCEEDED and (x.get("delivery_receipt") is None or x.get("failure") is not None): raise ProductionSignalArtifactError("invalid publication completion")
    if x.get("delivery_state")==DELIVERY_FAILED and (x.get("delivery_receipt") is not None or x.get("failure") is None): raise ProductionSignalArtifactError("invalid publication failure")
    if not isinstance(x.get("content_hash"),str) or hashlib.sha256(canonical_json_bytes({k:v for k,v in x.items() if k!="content_hash"})).hexdigest()!=x["content_hash"]: raise ProductionSignalArtifactError("publication content hash mismatch")
    return x

def _root(value, existing=False):
    root=Path(value)
    if not root.name or root.name.casefold() in _PROTECTED: raise ProductionSignalArtifactError("protected production signal root")
    _no_symlink(root)
    if existing:
        if not root.exists() or not root.is_dir(): raise ProductionSignalArtifactError("production signal root is not a directory")
    elif root.exists():
        if root.is_symlink() or not root.is_dir(): raise ProductionSignalArtifactError("production signal root is not a directory")
    else:
        try: root.mkdir(parents=True)
        except FileExistsError:
            if root.is_symlink() or not root.is_dir(): raise ProductionSignalArtifactError("production signal root is not a directory")
    _no_symlink(root); return root.resolve()

def _no_symlink(path):
    cur=path
    while True:
        try:
            if stat.S_ISLNK(cur.lstat().st_mode): raise ProductionSignalArtifactError("symlink artifact paths are prohibited")
        except FileNotFoundError: pass
        parent=cur.parent
        if parent==cur: return
        cur=parent

def _dir(root,name):
    p=root/name; _no_symlink(p)
    if p.exists():
        if p.is_symlink() or not p.is_dir(): raise ProductionSignalArtifactError("artifact path must be a directory")
    else:
        try: p.mkdir()
        except FileExistsError:
            if p.is_symlink() or not p.is_dir(): raise ProductionSignalArtifactError("artifact path must be a directory")
    return p.resolve()

def _dest(p):
    _no_symlink(p)
    if p.exists() and (p.is_symlink() or not p.is_file()): raise ProductionSignalArtifactError("artifact destination is not a regular file")

def _lock(path):
    _no_symlink(path)
    for _ in range(2000):
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(fd,b"production-signal-lock-v1\n"); os.fsync(fd); return fd
        except FileExistsError: time.sleep(.001)
        except OSError as e: raise ProductionSignalArtifactError("publication lock failed") from e
    raise ProductionSignalArtifactError("publication concurrency conflict")

def _unlock(fd,path):
    if fd is not None:
        try: os.close(fd)
        except OSError: pass
        try: path.unlink(missing_ok=True)
        except OSError: pass

def _fsync_dir(p):
    fd=None
    try: fd=os.open(p,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)); os.fsync(fd)
    except OSError as e: raise ProductionSignalArtifactError("artifact directory synchronization failed") from e
    finally:
        if fd is not None: os.close(fd)

def _write(p,data,replace=False):
    fd=None; tmp=None
    try:
        fd,name=tempfile.mkstemp(prefix="."+p.name+".",suffix=".tmp",dir=p.parent); tmp=Path(name)
        with os.fdopen(fd,"wb") as f: fd=None; f.write(data); f.flush(); os.fsync(f.fileno())
        if replace: os.replace(tmp,p); tmp=None
        else:
            try: os.link(tmp,p)
            except FileExistsError: raise ProductionSignalArtifactError("publication identity collision")
        _fsync_dir(p.parent); return p.resolve()
    except ProductionSignalArtifactError: raise
    except OSError as e: raise ProductionSignalArtifactError("artifact publication failed") from e
    finally:
        if fd is not None:
            try: os.close(fd)
            except OSError: pass
        if tmp is not None:
            try: tmp.unlink(missing_ok=True)
            except OSError: pass

def _bytes(v):
    try: return canonical_json_bytes(v)+b"\n"
    except ProductionSignalContractError as e: raise ProductionSignalArtifactError("artifact payload is not canonical JSON") from e

def _publish(p,root,completed=False):
    r=_root(root); pd=_dir(r,PUBLICATION_DIRECTORY); sd=pd/p["signal_id"]; _no_symlink(sd)
    if sd.exists() and (sd.is_symlink() or not sd.is_dir()): raise ProductionSignalArtifactError("signal directory invalid")
    if not sd.exists():
        try: sd.mkdir()
        except FileExistsError:
            if sd.is_symlink() or not sd.is_dir(): raise ProductionSignalArtifactError("signal directory invalid")
    lockdir=_dir(r,LOCK_DIRECTORY); dest=sd/(p["delivery_id"]+".json"); lp=lockdir/(p["delivery_id"]+".lock"); data=_bytes(p); fd=None
    try:
        fd=_lock(lp); _dest(dest)
        if dest.exists():
            old=dest.read_bytes()
            if old==data: return dest.resolve()
            if not completed: raise ProductionSignalArtifactError("publication identity collision")
            try: installed=json.loads(old[:-1].decode())
            except Exception as e: raise ProductionSignalArtifactError("existing publication is invalid") from e
            if installed.get("delivery_state") in {DELIVERY_SUCCEEDED,DELIVERY_FAILED}: raise ProductionSignalArtifactError("publication identity collision")
            if installed.get("delivery_state") != DELIVERY_INTENT_PERSISTED: raise ProductionSignalArtifactError("matching publication intent is invalid")
            authority=lambda x:{k:v for k,v in x.items() if k not in {"delivery_state","delivery_receipt","failure","content_hash"}}
            if canonical_json_bytes(authority(installed))!=canonical_json_bytes(authority(p)): raise ProductionSignalArtifactError("completion does not match publication intent")
            return _write(dest,data,True)
        if completed: raise ProductionSignalArtifactError("matching publication intent does not exist")
        return _write(dest,data)
    finally: _unlock(fd,lp)

def publish_publication_intent(*,publication_root,payload):
    p=_validate_pub(payload)
    if p.get("delivery_state")!=DELIVERY_INTENT_PERSISTED: raise ProductionSignalArtifactError("publication payload is not an intent")
    return _publish(p,publication_root)

def publish_completed_publication(*,publication_root,payload):
    p=_validate_pub(payload)
    if p.get("delivery_state") not in {DELIVERY_SUCCEEDED,DELIVERY_FAILED}: raise ProductionSignalArtifactError("publication payload is not completed")
    return _publish(p,publication_root,True)

def _no_trade(p):
    if not isinstance(p,Mapping) or p.get("schema_name")!=PRODUCTION_SIGNAL_EVALUATION_SCHEMA or p.get("outcome_kind")!=OUTCOME_NO_TRADE: raise ProductionSignalArtifactError("invalid NO_TRADE evaluation")
    if p.get("signal_id") is not None or p.get("delivery_id") is not None or p.get("source_publication_ref") is not None or p.get("delivery_state") is not None: raise ProductionSignalArtifactError("NO_TRADE contains publication identity")
    if not isinstance(p.get("source_evaluation_id"),str) or not _EID.fullmatch(p["source_evaluation_id"]): raise ProductionSignalArtifactError("invalid evaluation identity")
    return copy.deepcopy(dict(p))

def publish_no_trade_evaluation(*,publication_root,payload):
    p=_no_trade(payload); r=_root(publication_root); ed=_dir(r,EVALUATION_DIRECTORY); ld=_dir(r,LOCK_DIRECTORY); dest=ed/f'{p["mode"]}__{p["source_evaluation_id"]}.json'; lp=ld/(hashlib.sha256(dest.name.encode()).hexdigest()+".lock"); fd=None
    try:
        fd=_lock(lp); _dest(dest); data=_bytes(p)
        if dest.exists():
            if dest.read_bytes()==data:return dest.resolve()
            raise ProductionSignalArtifactError("NO_TRADE evaluation identity collision")
        return _write(dest,data)
    finally: _unlock(fd,lp)

def read_publication_artifact(*,publication_root,signal_id,delivery_id):
    if not isinstance(signal_id,str) or not _ID.fullmatch(signal_id) or not isinstance(delivery_id,str) or not _DID.fullmatch(delivery_id): raise ProductionSignalArtifactError("invalid production signal identity")
    r=_root(publication_root,True); p=r/PUBLICATION_DIRECTORY/signal_id/(delivery_id+".json"); _no_symlink(p)
    if not p.exists() or not p.is_file(): raise ProductionSignalArtifactError("publication artifact does not exist")
    raw=p.read_bytes()
    if not raw.endswith(b"\n"): raise ProductionSignalArtifactError("publication artifact lacks canonical newline")
    try: value=json.loads(raw[:-1].decode())
    except Exception as e: raise ProductionSignalArtifactError("publication artifact is invalid") from e
    if _bytes(value)!=raw: raise ProductionSignalArtifactError("publication artifact is not canonical")
    p=_validate_pub(value)
    if p["signal_id"]!=signal_id or p["delivery_id"]!=delivery_id: raise ProductionSignalArtifactError("publication artifact identity mismatch")
    return p
