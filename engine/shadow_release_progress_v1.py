"""Pure Phase 08 Shadow Release progress and readiness derivation."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from engine.shadow_release_artifact_v1 import (
    ShadowReleaseArtifactError,
    _validate_completed_run,
)
from engine.shadow_release_contract_v1 import canonical_json_bytes


SHADOW_RELEASE_PROGRESS_SCHEMA_VERSION = 1
SHADOW_RELEASE_PROGRESS_SCHEMA_NAME = "shadow-release-progress"
SHADOW_RELEASE_PROGRESS_CLASSIFICATION = "SHADOW_RELEASE"
SHADOW_RELEASE_PROGRESS_EXECUTION_BOUNDARY = (
    "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
)
SHADOW_RELEASE_PROGRESS_CAPITAL_EXPOSURE = "NONE"
SHADOW_RELEASE_PROGRESS_ORDER_EXECUTION = "PROHIBITED"

MINIMUM_SUCCESSFUL_MATCH_TOTAL = 100
MINIMUM_SUCCESSFUL_MATCHES_PER_ENABLED_MODE = 30
MINIMUM_UNIQUE_EVALUATION_CYCLES_PER_ENABLED_MODE = 30
MINIMUM_OBSERVED_RUNTIME_SPAN_DAYS = 14

_MODES = ("SWING", "INTRADAY", "SCALP")
_OUTCOME_KINDS = ("PUBLISHED_SIGNAL", "NO_TRADE")
_OUTCOME_STATES = ("MATCH", "MISMATCH", "FAILED")
_MISMATCH_CODES = (
    "DECISION_MISMATCH",
    "PUBLICATION_MISMATCH",
    "LIFECYCLE_MISMATCH",
    "NO_TRADE_MISMATCH",
    "NONDETERMINISM_DETECTED",
    "EVIDENCE_HASH_MISMATCH",
)
_FAILURE_CODES = (
    "INPUT_CONTRACT_REJECTED",
    "SOURCE_AUTHORITY_MISSING",
    "COMPONENT_VERSION_UNSUPPORTED",
    "SHADOW_EXECUTION_FAILED",
    "ARTIFACT_PUBLICATION_FAILED",
    "ROOT_ISOLATION_VIOLATION",
    "IDENTITY_COLLISION",
    "CONCURRENCY_CONFLICT",
)
_CRITICAL_FAILURE_CODES = frozenset(
    {
        "ROOT_ISOLATION_VIOLATION",
        "IDENTITY_COLLISION",
        "CONCURRENCY_CONFLICT",
    }
)
_LIFECYCLE_SURFACES = (
    "publication",
    "entry_eligibility",
    "cancellation",
    "entry_touch",
    "tp_sl_ordering",
    "acknowledgment",
    "no_trade",
    "terminal_state",
)
_PROGRESS_FIELDS = frozenset(
    {
        "schema_version",
        "schema_name",
        "classification",
        "execution_boundary",
        "capital_exposure",
        "order_execution",
        "position_authority",
        "enabled_modes",
        "completed_run_total",
        "official_serialized_run_total",
        "successful_match_total",
        "match_count",
        "mismatch_count",
        "failed_count",
        "outcome_count_by_kind",
        "outcome_count_by_state",
        "successful_match_count_by_enabled_mode",
        "unique_evaluation_cycle_count_by_enabled_mode",
        "evaluation_coverage_by_mode",
        "official_shadow_run_identities",
        "mismatch_count_by_primary_code",
        "failure_count_by_primary_code",
        "observed_runtime_span_days",
        "critical_defect_count",
        "evidence_incomplete_count",
        "shadow_release_readiness",
        "content_hash",
    }
)
_COVERAGE_FIELDS = frozenset(
    {
        "completed_run_count",
        "published_signal_run_count",
        "no_trade_cycle_count",
        "unique_evaluation_cycle_count",
        "lifecycle_surface_count",
    }
)
_IDENTITY_FIELDS = frozenset(
    {
        "shadow_run_id",
        "signal_id",
        "delivery_id",
        "source_evaluation_id",
        "mode",
        "market_identity",
        "content_hash",
    }
)
_FORBIDDEN_FIELDS = frozenset(
    {
        "exchange_credentials",
        "private_endpoint",
        "order_payload",
        "position_size",
        "account_state",
        "balance_state",
        "portfolio_state",
        "exchange_execution",
        "telegram_ledger",
        "replay_output_root",
        "paper_signal_output_root",
        "production_evidence_mutation",
        "api_secret",
        "private_key",
    }
)


class ShadowReleaseProgressError(ValueError):
    """Raised when progress evidence violates the Phase 08 freeze."""


def build_shadow_release_progress(
    *,
    enabled_modes: Sequence[str],
    completed_runs: Sequence[Mapping[str, Any]],
    critical_defect_count: int,
    content_hash: Any = None,
    shadow_release_readiness: Any = None,
) -> dict[str, Any]:
    """Aggregate completed shadow evidence and derive release readiness."""

    if content_hash is not None:
        raise ShadowReleaseProgressError("content_hash is derived")
    if shadow_release_readiness is not None:
        raise ShadowReleaseProgressError("readiness is derived")

    modes = _validate_enabled_modes(enabled_modes)
    external_defects = _nonnegative_integer(
        critical_defect_count, "critical defect count"
    )
    runs = _validate_and_deduplicate_runs(completed_runs)

    state_counts = {state: 0 for state in _OUTCOME_STATES}
    kind_counts = {kind: 0 for kind in _OUTCOME_KINDS}
    mismatch_counts = {code: 0 for code in _MISMATCH_CODES}
    failure_counts = {code: 0 for code in _FAILURE_CODES}
    successful_by_mode = {mode: 0 for mode in modes}
    cycle_ids_by_mode = {mode: set() for mode in _MODES}
    coverage = {mode: _empty_coverage() for mode in _MODES}
    official_identities = []
    successful_timestamps: list[datetime] = []
    derived_critical = 0

    for run in runs:
        mode = run["mode"]
        state = run["comparison"]["outcome"]
        kind = run["outcome_kind"]
        state_counts[state] += 1
        kind_counts[kind] += 1
        cycle_ids_by_mode[mode].add(run["source_evaluation_id"])

        mode_coverage = coverage[mode]
        mode_coverage["completed_run_count"] += 1
        if kind == "PUBLISHED_SIGNAL":
            mode_coverage["published_signal_run_count"] += 1
            official_identities.append(_official_identity(run))
        else:
            mode_coverage["no_trade_cycle_count"] += 1
        _record_lifecycle_coverage(mode_coverage, run)

        if state == "MATCH":
            successful_timestamps.append(
                _parse_utc(run["evaluation_completed_at"])
            )
            if kind == "PUBLISHED_SIGNAL" and mode in successful_by_mode:
                successful_by_mode[mode] += 1
        elif state == "MISMATCH":
            code = run["comparison"]["primary_code"]
            if code not in mismatch_counts:
                raise ShadowReleaseProgressError(
                    "invalid mismatch classification"
                )
            mismatch_counts[code] += 1
            derived_critical += 1
        else:
            code = run["failure"]["primary_code"]
            if code not in failure_counts:
                raise ShadowReleaseProgressError(
                    "invalid failure classification"
                )
            failure_counts[code] += 1
            if code in _CRITICAL_FAILURE_CODES:
                derived_critical += 1

    for mode in _MODES:
        coverage[mode]["unique_evaluation_cycle_count"] = len(
            cycle_ids_by_mode[mode]
        )

    successful_total = sum(
        1
        for run in runs
        if run["comparison"]["outcome"] == "MATCH"
        and run["outcome_kind"] == "PUBLISHED_SIGNAL"
    )
    observed_span = _observed_runtime_span_days(successful_timestamps)
    critical_total = external_defects + derived_critical
    incomplete_total = 0
    unique_cycles_enabled = {
        mode: len(cycle_ids_by_mode[mode]) for mode in modes
    }
    readiness = _derive_readiness(
        enabled_modes=modes,
        successful_match_total=successful_total,
        successful_by_mode=successful_by_mode,
        unique_cycles_by_mode=unique_cycles_enabled,
        observed_runtime_span_days=observed_span,
        mismatch_count=state_counts["MISMATCH"],
        critical_defect_count=critical_total,
        evidence_incomplete_count=incomplete_total,
    )

    payload = {
        "schema_version": SHADOW_RELEASE_PROGRESS_SCHEMA_VERSION,
        "schema_name": SHADOW_RELEASE_PROGRESS_SCHEMA_NAME,
        "classification": SHADOW_RELEASE_PROGRESS_CLASSIFICATION,
        "execution_boundary": SHADOW_RELEASE_PROGRESS_EXECUTION_BOUNDARY,
        "capital_exposure": SHADOW_RELEASE_PROGRESS_CAPITAL_EXPOSURE,
        "order_execution": SHADOW_RELEASE_PROGRESS_ORDER_EXECUTION,
        "position_authority": "NONE",
        "enabled_modes": list(modes),
        "completed_run_total": len(runs),
        "official_serialized_run_total": kind_counts["PUBLISHED_SIGNAL"],
        "successful_match_total": successful_total,
        "match_count": state_counts["MATCH"],
        "mismatch_count": state_counts["MISMATCH"],
        "failed_count": state_counts["FAILED"],
        "outcome_count_by_kind": kind_counts,
        "outcome_count_by_state": state_counts,
        "successful_match_count_by_enabled_mode": successful_by_mode,
        "unique_evaluation_cycle_count_by_enabled_mode": (
            unique_cycles_enabled
        ),
        "evaluation_coverage_by_mode": coverage,
        "official_shadow_run_identities": sorted(
            official_identities, key=lambda item: item["shadow_run_id"]
        ),
        "mismatch_count_by_primary_code": mismatch_counts,
        "failure_count_by_primary_code": failure_counts,
        "observed_runtime_span_days": observed_span,
        "critical_defect_count": critical_total,
        "evidence_incomplete_count": incomplete_total,
        "shadow_release_readiness": readiness,
    }
    payload["content_hash"] = _hash_payload(payload)
    return payload


def validate_shadow_release_progress(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and detach one derived Shadow Release progress contract."""

    progress = _exact_mapping(value, _PROGRESS_FIELDS, "progress")
    _reject_forbidden_fields(progress)
    if type(progress["schema_version"]) is not int or (
        progress["schema_version"] != SHADOW_RELEASE_PROGRESS_SCHEMA_VERSION
    ):
        raise ShadowReleaseProgressError("invalid progress schema version")
    for field, expected in (
        ("schema_name", SHADOW_RELEASE_PROGRESS_SCHEMA_NAME),
        ("classification", SHADOW_RELEASE_PROGRESS_CLASSIFICATION),
        ("execution_boundary", SHADOW_RELEASE_PROGRESS_EXECUTION_BOUNDARY),
        ("capital_exposure", SHADOW_RELEASE_PROGRESS_CAPITAL_EXPOSURE),
        ("order_execution", SHADOW_RELEASE_PROGRESS_ORDER_EXECUTION),
        ("position_authority", "NONE"),
    ):
        if progress[field] != expected:
            raise ShadowReleaseProgressError(f"invalid progress {field}")

    modes = _validate_enabled_modes(progress["enabled_modes"])
    for field in (
        "completed_run_total",
        "official_serialized_run_total",
        "successful_match_total",
        "match_count",
        "mismatch_count",
        "failed_count",
        "observed_runtime_span_days",
        "critical_defect_count",
        "evidence_incomplete_count",
    ):
        _nonnegative_integer(progress[field], field)

    state_counts = _validate_count_map(
        progress["outcome_count_by_state"], _OUTCOME_STATES, "outcome state"
    )
    kind_counts = _validate_count_map(
        progress["outcome_count_by_kind"], _OUTCOME_KINDS, "outcome kind"
    )
    mismatch_counts = _validate_count_map(
        progress["mismatch_count_by_primary_code"],
        _MISMATCH_CODES,
        "mismatch",
    )
    failure_counts = _validate_count_map(
        progress["failure_count_by_primary_code"],
        _FAILURE_CODES,
        "failure",
    )
    successful_by_mode = _validate_count_map(
        progress["successful_match_count_by_enabled_mode"], modes, "mode"
    )
    unique_by_mode = _validate_count_map(
        progress["unique_evaluation_cycle_count_by_enabled_mode"],
        modes,
        "evaluation mode",
    )
    _validate_coverage(progress["evaluation_coverage_by_mode"])
    _validate_official_identities(progress["official_shadow_run_identities"])

    if sum(state_counts.values()) != progress["completed_run_total"]:
        raise ShadowReleaseProgressError("completed total mismatch")
    if sum(kind_counts.values()) != progress["completed_run_total"]:
        raise ShadowReleaseProgressError("outcome kind total mismatch")
    if state_counts["MATCH"] != progress["match_count"] or (
        state_counts["MISMATCH"] != progress["mismatch_count"]
    ) or state_counts["FAILED"] != progress["failed_count"]:
        raise ShadowReleaseProgressError("outcome state count mismatch")
    if sum(mismatch_counts.values()) != progress["mismatch_count"]:
        raise ShadowReleaseProgressError("mismatch classification total mismatch")
    if sum(failure_counts.values()) != progress["failed_count"]:
        raise ShadowReleaseProgressError("failure classification total mismatch")

    derived_readiness = _derive_readiness(
        enabled_modes=modes,
        successful_match_total=progress["successful_match_total"],
        successful_by_mode=successful_by_mode,
        unique_cycles_by_mode=unique_by_mode,
        observed_runtime_span_days=progress["observed_runtime_span_days"],
        mismatch_count=progress["mismatch_count"],
        critical_defect_count=progress["critical_defect_count"],
        evidence_incomplete_count=progress["evidence_incomplete_count"],
    )
    if type(progress["shadow_release_readiness"]) is not bool or (
        progress["shadow_release_readiness"] != derived_readiness
    ):
        raise ShadowReleaseProgressError("invalid derived readiness")

    supplied_hash = progress["content_hash"]
    if not isinstance(supplied_hash, str) or len(supplied_hash) != 64:
        raise ShadowReleaseProgressError("invalid progress content hash")
    content = {
        key: copy.deepcopy(item)
        for key, item in progress.items()
        if key != "content_hash"
    }
    if supplied_hash != _hash_payload(content):
        raise ShadowReleaseProgressError("progress content hash mismatch")
    canonical_json_bytes(progress)
    return copy.deepcopy(progress)


def _validate_and_deduplicate_runs(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise ShadowReleaseProgressError("completed runs must be a sequence")
    by_identity: dict[str, dict[str, Any]] = {}
    canonical_by_identity: dict[str, bytes] = {}
    for item in value:
        try:
            run = _validate_completed_run(item)
        except ShadowReleaseArtifactError as exc:
            raise ShadowReleaseProgressError(
                "completed shadow evidence rejected"
            ) from None
        identity = run["shadow_run_id"]
        canonical = canonical_json_bytes(run)
        if identity in by_identity:
            if canonical_by_identity[identity] != canonical:
                raise ShadowReleaseProgressError(
                    "conflicting duplicate shadow identity"
                )
            continue
        by_identity[identity] = run
        canonical_by_identity[identity] = canonical
    return [by_identity[key] for key in sorted(by_identity)]


def _validate_enabled_modes(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise ShadowReleaseProgressError("enabled modes must be a sequence")
    provided = list(value)
    if not provided or any(mode not in _MODES for mode in provided):
        raise ShadowReleaseProgressError("invalid enabled modes")
    if len(set(provided)) != len(provided):
        raise ShadowReleaseProgressError("duplicate enabled modes")
    return tuple(mode for mode in _MODES if mode in provided)


def _empty_coverage() -> dict[str, Any]:
    return {
        "completed_run_count": 0,
        "published_signal_run_count": 0,
        "no_trade_cycle_count": 0,
        "unique_evaluation_cycle_count": 0,
        "lifecycle_surface_count": {
            surface: 0 for surface in _LIFECYCLE_SURFACES
        },
    }


def _record_lifecycle_coverage(
    mode_coverage: dict[str, Any], run: Mapping[str, Any]
) -> None:
    lifecycle = run["observed_decision"]["lifecycle"]
    counts = mode_coverage["lifecycle_surface_count"]
    for surface in _LIFECYCLE_SURFACES:
        if surface == "no_trade":
            if run["outcome_kind"] == "NO_TRADE":
                counts[surface] += 1
        elif surface in lifecycle:
            counts[surface] += 1


def _official_identity(run: Mapping[str, Any]) -> dict[str, Any]:
    source = run["source_publication_ref"]
    return {
        "shadow_run_id": run["shadow_run_id"],
        "signal_id": source["signal_id"],
        "delivery_id": source["delivery_id"],
        "source_evaluation_id": run["source_evaluation_id"],
        "mode": run["mode"],
        "market_identity": copy.deepcopy(run["market_identity"]),
        "content_hash": run["content_hash"],
    }


def _observed_runtime_span_days(values: Sequence[datetime]) -> int:
    if len(values) < 2:
        return 0
    delta = max(values) - min(values)
    return delta.days


def _derive_readiness(
    *,
    enabled_modes: Sequence[str],
    successful_match_total: int,
    successful_by_mode: Mapping[str, int],
    unique_cycles_by_mode: Mapping[str, int],
    observed_runtime_span_days: int,
    mismatch_count: int,
    critical_defect_count: int,
    evidence_incomplete_count: int,
) -> bool:
    return bool(
        successful_match_total >= MINIMUM_SUCCESSFUL_MATCH_TOTAL
        and all(
            successful_by_mode[mode]
            >= MINIMUM_SUCCESSFUL_MATCHES_PER_ENABLED_MODE
            for mode in enabled_modes
        )
        and all(
            unique_cycles_by_mode[mode]
            >= MINIMUM_UNIQUE_EVALUATION_CYCLES_PER_ENABLED_MODE
            for mode in enabled_modes
        )
        and observed_runtime_span_days >= MINIMUM_OBSERVED_RUNTIME_SPAN_DAYS
        and mismatch_count == 0
        and critical_defect_count == 0
        and evidence_incomplete_count == 0
    )


def _validate_count_map(
    value: Any, keys: Sequence[str], label: str
) -> dict[str, int]:
    expected = frozenset(keys)
    mapping = _exact_mapping(value, expected, f"{label} counts")
    for key, count in mapping.items():
        _nonnegative_integer(count, f"{label} count {key}")
    return mapping


def _validate_coverage(value: Any) -> None:
    coverage = _exact_mapping(
        value, frozenset(_MODES), "evaluation coverage"
    )
    for mode, item in coverage.items():
        mode_coverage = _exact_mapping(item, _COVERAGE_FIELDS, mode)
        for field in (
            "completed_run_count",
            "published_signal_run_count",
            "no_trade_cycle_count",
            "unique_evaluation_cycle_count",
        ):
            _nonnegative_integer(mode_coverage[field], f"{mode} {field}")
        _validate_count_map(
            mode_coverage["lifecycle_surface_count"],
            _LIFECYCLE_SURFACES,
            f"{mode} lifecycle",
        )


def _validate_official_identities(value: Any) -> None:
    if not isinstance(value, list):
        raise ShadowReleaseProgressError(
            "official shadow identities must be a list"
        )
    previous = None
    for item in value:
        identity = _exact_mapping(
            item, _IDENTITY_FIELDS, "official shadow identity"
        )
        for field in (
            "shadow_run_id",
            "signal_id",
            "delivery_id",
            "source_evaluation_id",
            "mode",
            "content_hash",
        ):
            if not isinstance(identity[field], str) or not identity[field]:
                raise ShadowReleaseProgressError(
                    "invalid official shadow identity"
                )
        if identity["mode"] not in _MODES or not isinstance(
            identity["market_identity"], Mapping
        ):
            raise ShadowReleaseProgressError(
                "invalid official shadow identity authority"
            )
        current = identity["shadow_run_id"]
        if previous is not None and current <= previous:
            raise ShadowReleaseProgressError(
                "official identities are not canonical"
            )
        previous = current


def _exact_mapping(
    value: Any, fields: frozenset[str], label: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or frozenset(value.keys()) != fields:
        raise ShadowReleaseProgressError(
            f"{label} fields do not match the frozen contract"
        )
    return copy.deepcopy(dict(value))


def _nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ShadowReleaseProgressError(f"{label} must be non-negative integer")
    return value


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ShadowReleaseProgressError("invalid serialized UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        raise ShadowReleaseProgressError(
            "invalid serialized UTC timestamp"
        ) from None
    if parsed.tzinfo != timezone.utc:
        raise ShadowReleaseProgressError("invalid serialized UTC timestamp")
    return parsed


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.casefold() in _FORBIDDEN_FIELDS:
                raise ShadowReleaseProgressError(
                    "forbidden execution authority field"
                )
            _reject_forbidden_fields(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_forbidden_fields(item)
