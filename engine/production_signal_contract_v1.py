"""Canonical Phase 09 Production Signal Service contract primitives."""
from __future__ import annotations

import copy, hashlib, json, math, re
from datetime import datetime, timezone
from typing import Any, Mapping

from engine.paper_signal_contract_v1 import PaperSignalContractError, validate_source_publication_ref

PRODUCTION_SIGNAL_SCHEMA_VERSION = 1
PRODUCTION_SIGNAL_INPUT_SCHEMA = "production-signal-input"
PRODUCTION_SIGNAL_PUBLICATION_SCHEMA = "production-signal-publication"
PRODUCTION_SIGNAL_EVALUATION_SCHEMA = "production-signal-evaluation"
PRODUCTION_SIGNAL_CLASSIFICATION = "PRODUCTION_SIGNAL"
PRODUCTION_SIGNAL_EXECUTION_BOUNDARY = "LIVE_SIGNAL_PUBLICATION_NO_CAPITAL"
PRODUCTION_SIGNAL_CAPITAL_EXPOSURE = "NONE"
PRODUCTION_SIGNAL_ORDER_EXECUTION = "PROHIBITED"
PRODUCTION_SIGNAL_POSITION_AUTHORITY = "TELEGRAM_USER_REPORT"
OUTCOME_PUBLISHED_SIGNAL = "PUBLISHED_SIGNAL"
OUTCOME_NO_TRADE = "NO_TRADE"
DELIVERY_INTENT_PERSISTED = "INTENT_PERSISTED"
DELIVERY_SUCCEEDED = "DELIVERY_SUCCEEDED"
DELIVERY_FAILED = "DELIVERY_FAILED"
_MODES = {"SWING", "INTRADAY", "SCALP"}
_SHA = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_FORBIDDEN = {"api_secret", "private_key", "bot_token", "exchange_credentials", "order_payload", "position_size", "wallet", "balance", "balance_state", "account_state", "portfolio_state", "exchange_execution", "private_endpoint"}

class ProductionSignalContractError(ValueError):
    pass

def _forbidden(v):
    if isinstance(v, Mapping):
        for k, x in v.items():
            if isinstance(k, str) and k.casefold() in _FORBIDDEN:
                raise ProductionSignalContractError(f"forbidden field: {k}")
            _forbidden(x)
    elif isinstance(v, (list, tuple)):
        for x in v: _forbidden(x)

def _finite(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ProductionSignalContractError(f"{name} must be finite")
    return v

def _utc(v, name):
    if not isinstance(v, str) or not _UTC.fullmatch(v):
        raise ProductionSignalContractError(f"{name} must be UTC")
    try: return datetime.fromisoformat(v.removesuffix("Z") + "+00:00")
    except ValueError as e: raise ProductionSignalContractError(f"{name} must be UTC") from e

def _str(v, name):
    if not isinstance(v, str) or not v.strip(): raise ProductionSignalContractError(f"{name} must be non-empty")
    return v

def _exact(v, fields, name):
    if not isinstance(v, Mapping) or set(v) != set(fields):
        raise ProductionSignalContractError(f"invalid {name}")
    return copy.deepcopy(dict(v))

def _sha(v, name):
    if not isinstance(v, str) or not _SHA.fullmatch(v): raise ProductionSignalContractError(f"{name} must be SHA-256")
    return v

def canonical_json_bytes(payload: Any) -> bytes:
    _forbidden(payload)
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as e:
        raise ProductionSignalContractError("payload is not valid canonical JSON") from e

def _hash(v): return hashlib.sha256(canonical_json_bytes(v)).hexdigest()

def _setup(v):
    s = _exact(v, {"symbol","side","entry_zone","stop_loss","take_profit","valid_until","strategy_version","source_payload_hash"}, "setup")
    _str(s["symbol"], "symbol")
    if s["side"] not in {"LONG", "SHORT"}: raise ProductionSignalContractError("invalid side")
    z = _exact(s["entry_zone"], {"min","max"}, "entry_zone"); _finite(z["min"], "entry min"); _finite(z["max"], "entry max")
    if z["min"] > z["max"]: raise ProductionSignalContractError("entry zone unordered")
    _finite(s["stop_loss"], "stop_loss")
    tp = _exact(s["take_profit"], {"tp1","tp2"}, "take_profit"); _finite(tp["tp1"], "tp1"); _finite(tp["tp2"], "tp2")
    _utc(s["valid_until"], "valid_until"); _str(s["strategy_version"], "strategy_version"); _sha(s["source_payload_hash"], "source_payload_hash")
    return s

def validate_production_signal_input(value: Mapping[str, Any]) -> dict[str, Any]:
    e = _exact(value, {"schema_version","schema_name","source_commit","source_evaluation_id","mode","evaluated_at","production_evidence_ref","outcome_kind","eligible_setups","component_versions"}, "input")
    _forbidden(e)
    if type(e["schema_version"]) is not int or e["schema_version"] != 1 or e["schema_name"] != PRODUCTION_SIGNAL_INPUT_SCHEMA: raise ProductionSignalContractError("invalid input schema")
    if not isinstance(e["source_commit"], str) or not _COMMIT.fullmatch(e["source_commit"]): raise ProductionSignalContractError("invalid source commit")
    _str(e["source_evaluation_id"], "source_evaluation_id");
    if e["mode"] not in _MODES: raise ProductionSignalContractError("invalid mode")
    _utc(e["evaluated_at"], "evaluated_at")
    r = _exact(e["production_evidence_ref"], {"manifest_hash","manifest_path"}, "evidence ref"); _sha(r["manifest_hash"], "manifest_hash"); _str(r["manifest_path"], "manifest_path")
    if e["outcome_kind"] not in {OUTCOME_PUBLISHED_SIGNAL, OUTCOME_NO_TRADE} or not isinstance(e["eligible_setups"], list): raise ProductionSignalContractError("invalid outcome")
    if e["outcome_kind"] == OUTCOME_PUBLISHED_SIGNAL and len(e["eligible_setups"]) == 1: _setup(e["eligible_setups"][0])
    elif e["outcome_kind"] == OUTCOME_NO_TRADE and not e["eligible_setups"]: pass
    else: raise ProductionSignalContractError("invalid eligible setups")
    if not isinstance(e["component_versions"], Mapping) or not e["component_versions"]: raise ProductionSignalContractError("invalid component versions")
    for k, v in e["component_versions"].items(): _str(k, "component key"); _str(v, "component version")
    canonical_json_bytes(e); return e

def build_signal_geometry(setup):
    s = _setup(setup)
    return {k: copy.deepcopy(s[k]) for k in ("symbol","side","entry_zone","stop_loss","take_profit","valid_until")}

def _signal_id(v):
    if not isinstance(v, str) or not re.fullmatch(r"PSG-[0-9a-f]{64}", v): raise ProductionSignalContractError("invalid signal_id")

def _delivery_id(v):
    if not isinstance(v, str) or not re.fullmatch(r"PDL-[0-9a-f]{64}", v): raise ProductionSignalContractError("invalid delivery_id")

def build_signal_id(*, source_envelope, signal_geometry_hash, source_payload_hash):
    e = validate_production_signal_input(source_envelope)
    if e["outcome_kind"] != OUTCOME_PUBLISHED_SIGNAL: raise ProductionSignalContractError("NO_TRADE has no signal")
    _sha(signal_geometry_hash, "geometry hash"); _sha(source_payload_hash, "source hash"); s = _setup(e["eligible_setups"][0])
    if s["source_payload_hash"] != source_payload_hash: raise ProductionSignalContractError("source hash mismatch")
    return "PSG-" + _hash({"schema_version":1,"source_commit":e["source_commit"],"source_evaluation_id":e["source_evaluation_id"],"mode":e["mode"],"symbol":s["symbol"],"signal_geometry_hash":signal_geometry_hash,"source_payload_hash":source_payload_hash})

def build_publication_payload(*, source_envelope, signal_id, signal_geometry):
    e = validate_production_signal_input(source_envelope); _signal_id(signal_id)
    if e["outcome_kind"] != OUTCOME_PUBLISHED_SIGNAL: raise ProductionSignalContractError("NO_TRADE payload")
    g = build_signal_geometry(e["eligible_setups"][0])
    if dict(signal_geometry) != g: raise ProductionSignalContractError("geometry mismatch")
    s = _setup(e["eligible_setups"][0])
    return {"signal_id":signal_id,"mode":e["mode"],"symbol":g["symbol"],"side":g["side"],"entry_zone":copy.deepcopy(g["entry_zone"]),"stop_loss":g["stop_loss"],"take_profit":copy.deepcopy(g["take_profit"]),"valid_until":g["valid_until"],"strategy_version":s["strategy_version"],"source_evaluation_id":e["source_evaluation_id"]}

def build_delivery_id(*, signal_id, channel, destination_id, publication_payload_hash):
    _signal_id(signal_id); _str(channel,"channel"); _str(destination_id,"destination_id"); _sha(publication_payload_hash,"payload hash")
    return "PDL-" + _hash({"schema_version":1,"signal_id":signal_id,"channel":channel,"destination_id":destination_id,"publication_payload_hash":publication_payload_hash})

def build_source_publication_ref(*, signal_id, delivery_id, mode, published_at, source_payload_hash):
    _signal_id(signal_id); _delivery_id(delivery_id); _str(mode,"mode")
    if mode not in _MODES: raise ProductionSignalContractError("invalid mode")
    _utc(published_at,"published_at"); _sha(source_payload_hash,"source hash")
    ref={"signal_id":signal_id,"delivery_id":delivery_id,"mode":mode,"published_at":published_at,"source_payload_hash":source_payload_hash}
    try: return copy.deepcopy(validate_source_publication_ref(ref))
    except PaperSignalContractError as e: raise ProductionSignalContractError("source reference rejected") from e

def _intent_args(*, source_envelope, signal_id, delivery_id, published_at, channel, destination_id, signal_geometry, signal_geometry_hash, publication_payload, publication_payload_hash, source_payload_hash):
    e=validate_production_signal_input(source_envelope); g=build_signal_geometry(e["eligible_setups"][0]); p=build_publication_payload(source_envelope=e,signal_id=signal_id,signal_geometry=g)
    if dict(signal_geometry)!=g or dict(publication_payload)!=p or _hash(g)!=signal_geometry_hash or _hash(p)!=publication_payload_hash: raise ProductionSignalContractError("publication content mismatch")
    if build_signal_id(source_envelope=e,signal_geometry_hash=signal_geometry_hash,source_payload_hash=source_payload_hash)!=signal_id: raise ProductionSignalContractError("signal identity mismatch")
    did=build_delivery_id(signal_id=signal_id,channel=channel,destination_id=destination_id,publication_payload_hash=publication_payload_hash)
    if did!=delivery_id: raise ProductionSignalContractError("delivery identity mismatch")
    ref=build_source_publication_ref(signal_id=signal_id,delivery_id=delivery_id,mode=e["mode"],published_at=published_at,source_payload_hash=source_payload_hash)
    return e,g,p,ref

def build_publication_intent(*, source_envelope, signal_id, delivery_id, published_at, channel, destination_id, signal_geometry, signal_geometry_hash, publication_payload, publication_payload_hash, source_payload_hash):
    e,g,p,ref=_intent_args(source_envelope=source_envelope,signal_id=signal_id,delivery_id=delivery_id,published_at=published_at,channel=channel,destination_id=destination_id,signal_geometry=signal_geometry,signal_geometry_hash=signal_geometry_hash,publication_payload=publication_payload,publication_payload_hash=publication_payload_hash,source_payload_hash=source_payload_hash)
    x={"schema_version":1,"schema_name":PRODUCTION_SIGNAL_PUBLICATION_SCHEMA,"classification":PRODUCTION_SIGNAL_CLASSIFICATION,"execution_boundary":PRODUCTION_SIGNAL_EXECUTION_BOUNDARY,"capital_exposure":"NONE","order_execution":"PROHIBITED","position_authority":"TELEGRAM_USER_REPORT","source_commit":e["source_commit"],"source_evaluation_id":e["source_evaluation_id"],"mode":e["mode"],"outcome_kind":OUTCOME_PUBLISHED_SIGNAL,"signal_id":signal_id,"delivery_id":delivery_id,"published_at":published_at,"channel":channel,"destination_id":destination_id,"signal_geometry":g,"signal_geometry_hash":signal_geometry_hash,"publication_payload":p,"publication_payload_hash":publication_payload_hash,"source_payload_hash":source_payload_hash,"source_publication_ref":ref,"delivery_state":DELIVERY_INTENT_PERSISTED,"delivery_receipt":None,"failure":None,"component_versions":copy.deepcopy(e["component_versions"])}
    x["content_hash"]=_hash(x); return x

def _failure(v):
    f=_exact(v,{"primary_code","component","message"},"failure"); _str(f["primary_code"],"code"); _str(f["component"],"component"); m=_str(f["message"],"message")
    if any(q in m.casefold() for q in ("traceback","api_secret","private_key","bot_token","sk-live","/home/","\\users\\")): raise ProductionSignalContractError("failure not sanitized")
    return f

def build_completed_publication(*, intent, delivery_receipt, failure):
    if (delivery_receipt is None)==(failure is None): raise ProductionSignalContractError("one outcome required")
    x=copy.deepcopy(dict(intent)); x.pop("content_hash",None)
    if delivery_receipt is not None:
        r=_exact(delivery_receipt,{"channel","destination_id","external_delivery_id","delivered_at"},"receipt"); _str(r["channel"],"channel"); _str(r["destination_id"],"destination_id"); _str(r["external_delivery_id"],"external id"); _utc(r["delivered_at"],"delivered_at")
        x.update(delivery_state=DELIVERY_SUCCEEDED,delivery_receipt=r,failure=None)
    else: x.update(delivery_state=DELIVERY_FAILED,delivery_receipt=None,failure=_failure(failure))
    x["content_hash"]=_hash(x); return x

def build_no_trade_evaluation(*, source_envelope, recorded_at):
    e=validate_production_signal_input(source_envelope)
    if e["outcome_kind"]!=OUTCOME_NO_TRADE: raise ProductionSignalContractError("not NO_TRADE")
    _utc(recorded_at,"recorded_at")
    x={"schema_version":1,"schema_name":PRODUCTION_SIGNAL_EVALUATION_SCHEMA,"classification":PRODUCTION_SIGNAL_CLASSIFICATION,"execution_boundary":PRODUCTION_SIGNAL_EXECUTION_BOUNDARY,"capital_exposure":"NONE","order_execution":"PROHIBITED","position_authority":"TELEGRAM_USER_REPORT","source_commit":e["source_commit"],"source_evaluation_id":e["source_evaluation_id"],"mode":e["mode"],"evaluated_at":e["evaluated_at"],"recorded_at":recorded_at,"production_evidence_ref":copy.deepcopy(e["production_evidence_ref"]),"outcome_kind":OUTCOME_NO_TRADE,"signal_id":None,"delivery_id":None,"source_publication_ref":None,"delivery_state":None,"component_versions":copy.deepcopy(e["component_versions"])}
    x["content_hash"]=_hash(x); return x
