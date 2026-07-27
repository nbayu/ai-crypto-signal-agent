import json
import math
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from pandas import Timestamp

from engine.scanner import scan_market
from engine.validated_pipeline_v4 import run_validated_pipeline_v4
from engine.outcome_tracker_v4 import save_outcome_snapshot
from engine.top5_watchlist_artifact_v4 import (
    save_top5_watchlist_artifact,
)
from engine.pre_delivery_flow_v4 import (
    run_pre_delivery_flow,
)
from engine.pre_delivery_market_data_v4 import (
    get_closed_ohlcv_for_pre_delivery,
)
from engine.production_evidence_v4 import (
    save_production_evidence,
)
from engine.production_signal_service_v1 import run_production_signal_service_v1
from engine.phase09r_observability_v1 import (
    BOUNDARY_NO,
    BOUNDARY_UNKNOWN,
    MASTER_ENGINE_SETUP_CONSTRUCTION_FAILED,
    MASTER_ENGINE_SOURCE_ENVELOPE_FAILED,
    PRODUCTION_SIGNAL_SERVICE_FAILED,
    Phase09RExit7Failure,
    classified_failure,
)
import hashlib
import subprocess

def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

def _hash_payload(v) -> str:
    import json
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _normalize_eligible_setup(value):
    if value is None or type(value) in (bool, int, str):
        return value

    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError("eligible setup contains a non-finite float")
        return value

    if type(value) is Timestamp:
        return value.isoformat()

    if isinstance(value, Mapping):
        normalized = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("eligible setup mapping keys must be strings")
            normalized[key] = _normalize_eligible_setup(item)
        return normalized

    if type(value) is list:
        return [
            _normalize_eligible_setup(item)
            for item in value
        ]

    if type(value) is tuple:
        return tuple(
            _normalize_eligible_setup(item)
            for item in value
        )

    raise TypeError("eligible setup contains an unsupported value type")



def save_validated_snapshot_v4(out, *, directory=None, now=None):
    if directory is None:
        directory = Path("data/validated_snapshots_v4")

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    if now is None:
        now = datetime.now()

    timestamp = now.strftime("%Y%m%d_%H%M%S")
    path = directory / f"validated_v4_{timestamp}.json"

    path.write_text(
        json.dumps(
            out,
            indent=2,
            default=str,
        )
    )

    return path


def run_master_engine_v4(
    *,
    scanner=scan_market,
    pipeline=run_validated_pipeline_v4,
    snapshot_saver=save_validated_snapshot_v4,
    outcome_saver=save_outcome_snapshot,
    watchlist_saver=save_top5_watchlist_artifact,
    pre_delivery_runner=run_pre_delivery_flow,
    closed_candle_provider=get_closed_ohlcv_for_pre_delivery,
    production_evidence_saver=save_production_evidence,
    now_provider=datetime.now,
    enable_publication=False,
    delivery_adapter=None,
    destination_id=None,
    publication_root=None,
):
    results = scanner()

    out = pipeline(results)

    now = now_provider()
    validated_at = now.isoformat()

    snapshot_path = snapshot_saver(
        out,
        now=now,
    )
    outcome_path = outcome_saver(
        out["final_top5"]
    )
    watchlist_path = watchlist_saver(
        out["final_top5"]
    )
    delivery_out = pre_delivery_runner(
        watchlist_path,
        "data/top5_watchlist_v4/tradingview_watchlist.txt",
        closed_candle_provider=(
            closed_candle_provider
        ),
        validated_at=validated_at,
    )

    delivery_artifact_path = delivery_out[
        "delivery_artifact_path"
    ]
    tradingview_watchlist_path = delivery_out[
        "tradingview_watchlist_path"
    ]

    evidence_path = production_evidence_saver(
        created_at=validated_at,
        validated_snapshot_path=snapshot_path,
        outcome_entry_path=outcome_path,
        raw_top5_path=watchlist_path,
        pre_delivery_path=delivery_artifact_path,
        tradingview_watchlist_path=(
            tradingview_watchlist_path
        ),
    )

    production_signal_out = None
    if enable_publication:
        try:
            source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        except Exception:
            source_commit = "0" * 40

        try:
            top5 = out.get("final_top5", [])
            if not top5:
                outcome_kind = "NO_TRADE"
                eligible_setups = []
            else:
                outcome_kind = "PUBLISHED_SIGNAL"
                setup = top5[0]
                entry_zone_min = setup.get("entry_zone", {}).get("min")
                if entry_zone_min is None and "golden_zone" in setup and "entry_zone" in setup["golden_zone"]:
                    entry_zone_min = setup["golden_zone"]["entry_zone"].get("price_low")

                entry_zone_max = setup.get("entry_zone", {}).get("max")
                if entry_zone_max is None and "golden_zone" in setup and "entry_zone" in setup["golden_zone"]:
                    entry_zone_max = setup["golden_zone"]["entry_zone"].get("price_high")

                stop_loss = setup.get("stop_loss")
                if stop_loss is None and "golden_zone" in setup and "stop_loss" in setup["golden_zone"]:
                    stop_loss = setup["golden_zone"]["stop_loss"].get("price")

                take_profit = setup.get("take_profit")
                if take_profit is None and "golden_zone" in setup and "take_profit" in setup["golden_zone"]:
                    take_profit_price = setup["golden_zone"]["take_profit"].get("price")
                    take_profit = {"tp1": take_profit_price, "tp2": take_profit_price}

                normalized_entry_zone_min = float(entry_zone_min)
                normalized_entry_zone_max = float(entry_zone_max)
                normalized_stop_loss = float(stop_loss)
                normalized_take_profit_tp1 = float(take_profit["tp1"])
                normalized_take_profit_tp2 = float(
                    take_profit.get("tp2", take_profit["tp1"])
                )
                normalized_setup = _normalize_eligible_setup(setup)

                eligible_setups = [{
                    "symbol": normalized_setup["symbol"],
                    "side": normalized_setup.get("side", "LONG"),
                    "entry_zone": {
                        "min": normalized_entry_zone_min,
                        "max": normalized_entry_zone_max,
                    },
                    "stop_loss": normalized_stop_loss,
                    "take_profit": {
                        "tp1": normalized_take_profit_tp1,
                        "tp2": normalized_take_profit_tp2,
                    },
                    "valid_until": normalized_setup.get(
                        "valid_until",
                        "2026-12-31T23:59:59Z",
                    ),
                    "strategy_version": "v4",
                    "source_payload_hash": _hash_payload(normalized_setup)
                }]
        except Exception as exc:
            raise classified_failure(
                failure_stage="ELIGIBLE_SETUP_CONSTRUCTION",
                failure_code=MASTER_ENGINE_SETUP_CONSTRUCTION_FAILED,
                exc=exc,
                telegram_boundary_reached=BOUNDARY_NO,
            ) from None

        try:
            source_envelope = {
                "schema_version": 1,
                "schema_name": "production-signal-input",
                "source_commit": source_commit,
                "source_evaluation_id": f"eval-{now.timestamp()}",
                "mode": "SWING",
                "evaluated_at": now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(datetime, "timezone") else now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "production_evidence_ref": {
                    "manifest_hash": _hash_file(evidence_path),
                    "manifest_path": str(evidence_path)
                },
                "outcome_kind": outcome_kind,
                "eligible_setups": eligible_setups,
                "component_versions": {"master_engine": "v4"}
            }

            # Fix timezone format if naive
            if "Z" not in source_envelope["evaluated_at"]:
                import datetime as dt
                source_envelope["evaluated_at"] = now.replace(tzinfo=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception as exc:
            raise classified_failure(
                failure_stage="SOURCE_ENVELOPE_CONSTRUCTION",
                failure_code=MASTER_ENGINE_SOURCE_ENVELOPE_FAILED,
                exc=exc,
                telegram_boundary_reached=BOUNDARY_NO,
            ) from None



        if delivery_adapter is None or destination_id is None:
            production_signal_out = {"status": "DELIVERY_NOT_CONFIGURED", "receipts": []}
        else:
            try:
                if publication_root is None:
                    publication_root = Path("data/production_signals")
                production_signal_out = run_production_signal_service_v1(
                    source_envelope=source_envelope,
                    publication_root=publication_root,
                    channel="TELEGRAM",
                    destination_id=destination_id,
                    published_at=source_envelope["evaluated_at"],
                    delivery_adapter=delivery_adapter,
                    component_versions={"master_engine": "v4"}
                )
            except Phase09RExit7Failure:
                raise
            except Exception as exc:
                raise classified_failure(
                    failure_stage="PRODUCTION_SIGNAL_SERVICE_INVOCATION",
                    failure_code=PRODUCTION_SIGNAL_SERVICE_FAILED,
                    exc=exc,
                    telegram_boundary_reached=BOUNDARY_UNKNOWN,
                ) from None

    ret = {
        "results": results,
        "out": out,
        "snapshot_path": snapshot_path,
        "outcome_path": outcome_path,
        "watchlist_path": watchlist_path,
        "delivery_out": delivery_out,
        "evidence_path": evidence_path,
    }
    if enable_publication:
        ret["production_signal_out"] = production_signal_out
    return ret
