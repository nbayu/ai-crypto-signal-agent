"""Deterministic, network-isolated Replay V4 master-engine composition."""

from dataclasses import dataclass
from datetime import datetime
import inspect
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import pandas as pd

import engine.replay_contract_v4 as replay_contract_module
from engine.master_engine_v4 import run_master_engine_v4
from engine.outcome_tracker_v4 import build_outcome_snapshot
from engine.pre_delivery_flow_v4 import run_pre_delivery_flow
from engine.replay_contract_v4 import (
    REPLAY_BUNDLE_SCHEMA_VERSION,
    ReplayBundleV4,
    calculate_replay_bundle_hash_v4,
    derive_replay_fixture_id_v4,
    derive_replay_id_v4,
)
from engine.top5_watchlist_artifact_v4 import (
    build_top5_watchlist_artifact,
)
from engine.tradingview_watchlist_export_v4 import (
    build_tradingview_watchlist,
)
from engine.validated_pipeline_v4 import run_validated_pipeline_v4


_CLASSIFICATION = "REPLAY"
_BOUNDARY = "MASTER_ENGINE_RECORDED_INPUT"
_PROTECTED_RELATIVE_ROOTS = frozenset(
    {
        "data/validated_snapshots_v4",
        "data/v4_outcomes",
        "data/top5_watchlist_v4",
        "data/pre_delivery_v4",
        "data/pine_delivery_v4",
        "data/production_evidence_v4",
        "data/quota_slot_v4",
        "data/worker_state_v4",
    }
)


class ReplayExecutionError(RuntimeError):
    """Raised when a replay cannot execute safely and deterministically."""


@dataclass(frozen=True)
class ReplayExecutionResultV4:
    replay_id: str
    fixture_id: str
    bundle_hash: str
    fixed_execution_time: str
    output_root: Path
    normalized_master_result: Mapping[str, Any]
    classification: str
    boundary: str


def run_replay_v4(
    bundle,
    output_root,
    *,
    master_engine_runner=None,
):
    """Run one validated replay through the real master-engine boundary."""
    _validate_bundle(bundle)
    root = _validate_output_root(output_root)
    if master_engine_runner is not None and not callable(master_engine_runner):
        raise ReplayExecutionError("Invalid replay master-engine runner")

    resolved_master_engine_runner = (
        run_master_engine_v4
        if master_engine_runner is None
        else master_engine_runner
    )
    fixed_now = _parse_fixed_execution_time(bundle.fixed_execution_time)
    replay_id = derive_replay_id_v4(bundle)
    fixture_id = derive_replay_fixture_id_v4(bundle)
    bundle_hash = calculate_replay_bundle_hash_v4(bundle)

    scanner = _build_scanner_provider(bundle)
    oi_provider = _build_oi_provider(bundle)
    validator = _build_validator_provider(bundle)
    closed_candle_provider = _build_closed_candle_provider(bundle)
    pipeline = _build_pipeline(validator, oi_provider)

    root.mkdir(parents=True, exist_ok=True)
    paths = _ReplayPaths(root)
    snapshot_saver = _build_snapshot_saver(paths)
    outcome_saver = _build_outcome_saver(paths, bundle.fixed_execution_time)
    watchlist_saver = _build_watchlist_saver(paths, fixed_now)
    pre_delivery_runner = _build_pre_delivery_runner(paths)
    evidence_saver = _build_evidence_saver(
        paths,
        replay_id=replay_id,
        fixture_id=fixture_id,
        bundle_hash=bundle_hash,
    )

    try:
        master_result = _invoke_master_engine(
            resolved_master_engine_runner,
            {
                "scanner": scanner,
                "pipeline": pipeline,
                "snapshot_saver": snapshot_saver,
                "outcome_saver": outcome_saver,
                "watchlist_saver": watchlist_saver,
                "pre_delivery_runner": pre_delivery_runner,
                "closed_candle_provider": closed_candle_provider,
                "production_evidence_saver": evidence_saver,
                "now_provider": lambda: fixed_now,
            },
        )
    except ReplayExecutionError:
        raise
    except Exception as exc:
        raise ReplayExecutionError(
            "Replay master-engine execution failed"
        ) from exc

    return ReplayExecutionResultV4(
        replay_id=replay_id,
        fixture_id=fixture_id,
        bundle_hash=bundle_hash,
        fixed_execution_time=bundle.fixed_execution_time,
        output_root=root,
        normalized_master_result=_freeze(
            _normalize_master_result(master_result, root)
        ),
        classification=_CLASSIFICATION,
        boundary=_BOUNDARY,
    )


def _invoke_master_engine(master_engine_runner, dependencies):
    parameters = tuple(inspect.signature(master_engine_runner).parameters.values())
    if (
        len(parameters) == 1
        and parameters[0].kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }
    ):
        return master_engine_runner(dependencies)
    return master_engine_runner(**dependencies)


@dataclass(frozen=True)
class _ReplayPaths:
    root: Path

    @property
    def snapshot(self) -> Path:
        return self.root / "replay_validated_snapshot.json"

    @property
    def outcome(self) -> Path:
        return self.root / "replay_outcome.json"

    @property
    def watchlist(self) -> Path:
        return self.root / "replay_top5_watchlist.json"

    @property
    def pre_delivery(self) -> Path:
        return self.root / "replay_pre_delivery.json"

    @property
    def tradingview(self) -> Path:
        return self.root / "replay_tradingview_watchlist.txt"

    @property
    def pine_bridge(self) -> Path:
        return self.root / "replay_pine_bridge.json"

    @property
    def pine_payload(self) -> Path:
        return self.root / "replay_pine_payload.txt"

    @property
    def evidence(self) -> Path:
        return self.root / "replay_evidence.json"


def _validate_bundle(bundle) -> None:
    if (
        not isinstance(bundle, replay_contract_module.ReplayBundleV4)
        or bundle.schema_version
        != replay_contract_module.REPLAY_BUNDLE_SCHEMA_VERSION
        or bundle.expected_semantic_contract.get("classification") != _CLASSIFICATION
        or bundle.expected_semantic_contract.get("boundary") != _BOUNDARY
    ):
        raise ReplayExecutionError("Invalid replay bundle")


def _validate_output_root(output_root) -> Path:
    if isinstance(output_root, bool) or not isinstance(output_root, (str, Path)):
        raise ReplayExecutionError("Invalid replay output root")
    if isinstance(output_root, str) and not output_root.strip():
        raise ReplayExecutionError("Invalid replay output root")

    root = Path(output_root)
    if root.exists() and not root.is_dir():
        raise ReplayExecutionError("Invalid replay output root")
    if _is_protected_root(root):
        raise ReplayExecutionError("Invalid replay output root")
    return root.resolve()


def _is_protected_root(root: Path) -> bool:
    try:
        relative = root.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return False
    normalized = relative.as_posix().rstrip("/")
    return any(
        normalized == protected or normalized.startswith(f"{protected}/")
        for protected in _PROTECTED_RELATIVE_ROOTS
    )


def _parse_fixed_execution_time(value: str) -> datetime:
    try:
        fixed_now = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ReplayExecutionError("Invalid replay bundle") from exc
    if fixed_now.tzinfo is None or fixed_now.utcoffset() is None:
        raise ReplayExecutionError("Invalid replay bundle")
    return fixed_now


def _build_scanner_provider(bundle: ReplayBundleV4):
    def scanner():
        return _thaw(bundle.scanner_results)

    return scanner


def _build_oi_provider(bundle: ReplayBundleV4):
    def oi_provider(symbol):
        try:
            metrics = bundle.recorded_open_interest[symbol]
        except (KeyError, TypeError) as exc:
            raise ReplayExecutionError("Replay provider lookup failed") from exc
        return _thaw(metrics)

    return oi_provider


def _build_validator_provider(bundle: ReplayBundleV4):
    def validator(candidates):
        del candidates
        return {
            "content": bundle.recorded_validator_response["content"],
            "usage": _thaw(bundle.recorded_validator_usage),
        }

    return validator


def _build_closed_candle_provider(bundle: ReplayBundleV4):
    def closed_candle_provider(symbol):
        try:
            candles = bundle.pre_delivery_closed_candles[symbol]
        except (KeyError, TypeError) as exc:
            raise ReplayExecutionError("Replay provider lookup failed") from exc

        rows = _thaw(candles)
        frame = pd.DataFrame(
            [
                {
                    "timestamp": row["open_time"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                }
                for row in rows
            ],
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        return frame.sort_values("timestamp").reset_index(drop=True)

    return closed_candle_provider


def _build_pipeline(validator, oi_provider):
    def pipeline(results):
        return run_validated_pipeline_v4(
            results,
            validator=validator,
            oi_provider=oi_provider,
        )

    return pipeline


def _build_snapshot_saver(paths: _ReplayPaths):
    def snapshot_saver(out, *, now):
        del now
        _write_json(paths.snapshot, out)
        return paths.snapshot

    return snapshot_saver


def _build_outcome_saver(paths: _ReplayPaths, fixed_execution_time: str):
    def outcome_saver(final_top5):
        _write_json(
            paths.outcome,
            build_outcome_snapshot(
                final_top5,
                captured_at=fixed_execution_time,
            ),
        )
        return paths.outcome

    return outcome_saver


def _build_watchlist_saver(paths: _ReplayPaths, fixed_now: datetime):
    def watchlist_saver(final_top5):
        _write_json(
            paths.watchlist,
            build_top5_watchlist_artifact(
                final_top5,
                now_provider=lambda: fixed_now,
            ),
        )
        return paths.watchlist

    return watchlist_saver


def _build_pre_delivery_runner(paths: _ReplayPaths):
    def delivery_artifact_saver(artifact):
        _write_json(paths.pre_delivery, artifact)
        return paths.pre_delivery

    def tradingview_exporter(source_path, output_path):
        del output_path
        artifact = json.loads(Path(source_path).read_text(encoding="utf-8"))
        paths.tradingview.write_text(
            ",".join(build_tradingview_watchlist(artifact)),
            encoding="utf-8",
        )
        return paths.tradingview

    def pine_delivery_saver(bridge_artifact, delivery_payload):
        _write_json(paths.pine_bridge, bridge_artifact)
        paths.pine_payload.write_text(delivery_payload, encoding="utf-8")
        return paths.pine_bridge, paths.pine_payload

    def pre_delivery_runner(
        source_path,
        tradingview_output_path,
        *,
        closed_candle_provider,
        validated_at,
    ):
        del tradingview_output_path
        return run_pre_delivery_flow(
            source_path,
            paths.tradingview,
            closed_candle_provider=closed_candle_provider,
            validated_at=validated_at,
            delivery_artifact_saver=delivery_artifact_saver,
            tradingview_exporter=tradingview_exporter,
            pine_delivery_saver=pine_delivery_saver,
        )

    return pre_delivery_runner


def _build_evidence_saver(
    paths: _ReplayPaths,
    *,
    replay_id: str,
    fixture_id: str,
    bundle_hash: str,
):
    def evidence_saver(
        *,
        created_at,
        validated_snapshot_path,
        outcome_entry_path,
        raw_top5_path,
        pre_delivery_path,
        tradingview_watchlist_path,
    ):
        _write_json(
            paths.evidence,
            {
                "classification": _CLASSIFICATION,
                "boundary": _BOUNDARY,
                "replay_id": replay_id,
                "fixture_id": fixture_id,
                "bundle_hash": bundle_hash,
                "created_at": created_at,
                "artifacts": {
                    "validated_snapshot": _relative_path(
                        validated_snapshot_path, paths.root
                    ),
                    "outcome_entry": _relative_path(outcome_entry_path, paths.root),
                    "raw_top5": _relative_path(raw_top5_path, paths.root),
                    "pre_delivery": _relative_path(pre_delivery_path, paths.root),
                    "tradingview_watchlist": _relative_path(
                        tradingview_watchlist_path, paths.root
                    ),
                },
            },
        )
        return paths.evidence

    return evidence_saver


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            _thaw(value),
            sort_keys=True,
            separators=(",", ":"),
            default=_serialize_value,
        ),
        encoding="utf-8",
    )


def _serialize_value(value: Any):
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _relative_path(path, root: Path) -> str:
    return str(Path(path).resolve().relative_to(root))


def _normalize_master_result(value: Any, root: Path):
    if isinstance(value, Mapping):
        return {
            _normalize_result_key(key): _normalize_master_result(nested, root)
            for key, nested in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_master_result(nested, root) for nested in value]
    if isinstance(value, Path):
        return _relative_path(value, root)
    return value


def _normalize_result_key(key: Any) -> str:
    if key == "take_profit":
        return "target"
    return str(key)


def _freeze(value: Any):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(nested) for key, nested in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(nested) for nested in value)
    return value


def _thaw(value: Any):
    if isinstance(value, Mapping):
        return {key: _thaw(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw(nested) for nested in value]
    return value
