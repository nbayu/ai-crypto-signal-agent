"""Detached composition of one routed mode scan and validation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import Final

from engine.mode_profile_v1 import ModeProfileV1, get_mode_profile
from engine.mode_router_v1 import (
    ModeRoutedCandidateV1,
    ModeRouteResultV1,
    ModeScanRequestV1,
    route_mode_scan,
)
from engine.mode_scan_execution_plan_v1 import (
    ModeMarketSnapshotEntryV1,
    ModeScanExecutionPlanV1,
    ModeSymbolExecutionPlanV1,
    ModeTimeframeFetchPlanV1,
    build_mode_scan_execution_plan,
)
from engine.mode_scan_execution_evidence_v1 import (
    ModeExecutionCandidateRowV1,
    ModeScanExecutionResultV1,
    ModeSymbolExecutionOutcomeV1,
)
from engine.mode_scan_executor_v1 import execute_mode_scan_plan
from engine.mode_validation_pipeline_adapter_v1 import (
    ModeValidatedCandidateV1,
    ModeValidationPipelineResultV1,
    run_mode_validation_pipeline,
)


MODE_SCAN_COMPOSITION_POLICY_VERSION: Final = (
    "mode-scan-composition-policy-v1"
)
MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION: Final = (
    "mode-scan-composition-result-v1"
)

__all__ = (
    "MODE_SCAN_COMPOSITION_POLICY_VERSION",
    "MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION",
    "ModeScanCompositionValidationError",
    "ModeScanCompositionResultV1",
    "compose_mode_scan_pipeline",
)

_SAFE_IDENTIFIER: Final = re.compile(r"[A-Za-z0-9._:+-]{1,128}")
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
_UTC_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"
_SCANNER_ROW_KEYS: Final = (
    "candidate_id",
    "mode",
    "symbol",
    "mode_lineage_sha256",
    "payload",
)


class ModeScanCompositionValidationError(ValueError):
    """Sanitized failure for the detached composition boundary."""


def _invalid() -> None:
    raise ModeScanCompositionValidationError(
        "invalid mode scan composition"
    ) from None


def _canonical_mode(value: object) -> tuple[str, ModeProfileV1]:
    try:
        profile = get_mode_profile(value)
    except Exception:
        _invalid()
    if (
        type(profile) is not ModeProfileV1
        or type(value) is not str
        or profile.mode != value
    ):
        _invalid()
    return profile.mode, profile


def _safe_identifier(value: object) -> str:
    if (
        type(value) is not str
        or _SAFE_IDENTIFIER.fullmatch(value) is None
    ):
        _invalid()
    return value


def _sha256_hex(value: object) -> str:
    if (
        type(value) is not str
        or _SHA256_HEX.fullmatch(value) is None
    ):
        _invalid()
    return value


def _canonical_observed_at(value: object) -> str:
    if (
        type(value) is not str
        or len(value) != 20
        or value[4] != "-"
        or value[7] != "-"
        or value[10] != "T"
        or value[13] != ":"
        or value[16] != ":"
        or value[19] != "Z"
    ):
        _invalid()
    try:
        parsed = datetime.strptime(value, _UTC_FORMAT)
    except (TypeError, ValueError):
        _invalid()
    if parsed.strftime(_UTC_FORMAT) != value:
        _invalid()
    return value


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except Exception:
        _invalid()


def _hash_mapping(value: dict[str, object]) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _copy_snapshot(
    value: object,
) -> tuple[ModeMarketSnapshotEntryV1, ...]:
    if type(value) is not tuple or not value:
        _invalid()
    copied = []
    for item in value:
        if type(item) is not ModeMarketSnapshotEntryV1:
            _invalid()
        try:
            mapping = item.to_mapping()
            if type(mapping) is not dict:
                _invalid()
            reconstructed = ModeMarketSnapshotEntryV1(**mapping)
            if reconstructed.to_mapping() != mapping:
                _invalid()
            copied.append(reconstructed)
        except ModeScanCompositionValidationError:
            raise
        except Exception:
            _invalid()
    result = tuple(copied)
    if not any(
        item.active is True
        and item.quote_asset == "USDT"
        and item.settle_asset == "USDT"
        and item.market_kind == "swap"
        and item.linear is True
        and item.perpetual is True
        for item in result
    ):
        _invalid()
    return result


def _copy_timeframe_plan(
    value: object,
) -> ModeTimeframeFetchPlanV1:
    if type(value) is not ModeTimeframeFetchPlanV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        cache_fields = mapping.get("cache_key_fields")
        if type(cache_fields) is not list:
            _invalid()
        reconstructed = ModeTimeframeFetchPlanV1(
            **{
                **mapping,
                "cache_key_fields": tuple(cache_fields),
            }
        )
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_symbol_plan(
    value: object,
) -> ModeSymbolExecutionPlanV1:
    if type(value) is not ModeSymbolExecutionPlanV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        fetch_values = mapping.get("candle_fetches")
        if type(fetch_values) is not list:
            _invalid()
        fetches = tuple(
            _copy_timeframe_plan(item)
            for item in value.candle_fetches
        )
        if len(fetches) != len(fetch_values):
            _invalid()
        reconstructed = ModeSymbolExecutionPlanV1(
            **{
                **mapping,
                "candle_fetches": fetches,
            }
        )
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_plan(value: object) -> ModeScanExecutionPlanV1:
    if type(value) is not ModeScanExecutionPlanV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        discovery_values = mapping.get("discovery_symbols")
        symbol_values = mapping.get("full_evaluation_symbols")
        cache_fields = mapping.get("cache_key_fields")
        if (
            type(discovery_values) is not list
            or type(symbol_values) is not list
            or type(cache_fields) is not list
        ):
            _invalid()
        symbols = tuple(
            _copy_symbol_plan(item)
            for item in value.full_evaluation_symbols
        )
        if len(symbols) != len(symbol_values):
            _invalid()
        reconstructed = ModeScanExecutionPlanV1(
            **{
                **mapping,
                "discovery_symbols": tuple(discovery_values),
                "full_evaluation_symbols": symbols,
                "cache_key_fields": tuple(cache_fields),
            }
        )
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_execution_candidate(
    value: object,
) -> ModeExecutionCandidateRowV1:
    if type(value) is not ModeExecutionCandidateRowV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        reconstructed = ModeExecutionCandidateRowV1(**mapping)
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_execution_outcome(
    value: object,
) -> ModeSymbolExecutionOutcomeV1:
    if type(value) is not ModeSymbolExecutionOutcomeV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        timeframe_hashes = mapping.get(
            "timeframe_evidence_sha256s"
        )
        candidate_value = mapping.get("candidate_row")
        if type(timeframe_hashes) is not list:
            _invalid()
        if candidate_value is None:
            candidate = None
        elif type(candidate_value) is dict:
            candidate = ModeExecutionCandidateRowV1(
                **candidate_value
            )
        else:
            _invalid()
        reconstructed = ModeSymbolExecutionOutcomeV1(
            **{
                **mapping,
                "timeframe_evidence_sha256s": tuple(
                    timeframe_hashes
                ),
                "candidate_row": candidate,
            }
        )
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_execution_result(
    value: object,
) -> ModeScanExecutionResultV1:
    if type(value) is not ModeScanExecutionResultV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        symbol_order = mapping.get("planned_symbol_order")
        timeframe_counts = mapping.get("planned_timeframe_counts")
        outcome_values = mapping.get("outcomes")
        candidate_values = mapping.get("candidates")
        if (
            type(symbol_order) is not list
            or type(timeframe_counts) is not list
            or type(outcome_values) is not list
            or type(candidate_values) is not list
        ):
            _invalid()
        outcomes = tuple(
            _copy_execution_outcome(item)
            for item in value.outcomes
        )
        candidates = tuple(
            _copy_execution_candidate(item)
            for item in value.candidates
        )
        if (
            len(outcomes) != len(outcome_values)
            or len(candidates) != len(candidate_values)
        ):
            _invalid()
        reconstructed = ModeScanExecutionResultV1(
            **{
                **mapping,
                "planned_symbol_order": tuple(symbol_order),
                "planned_timeframe_counts": tuple(
                    timeframe_counts
                ),
                "outcomes": outcomes,
                "candidates": candidates,
            }
        )
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_route_candidate(
    value: object,
) -> ModeRoutedCandidateV1:
    if type(value) is not ModeRoutedCandidateV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        reconstructed = ModeRoutedCandidateV1(**mapping)
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_route_result(value: object) -> ModeRouteResultV1:
    if type(value) is not ModeRouteResultV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        candidate_values = mapping.get("candidates")
        if type(candidate_values) is not list:
            _invalid()
        candidates = tuple(
            _copy_route_candidate(item)
            for item in value.candidates
        )
        if len(candidates) != len(candidate_values):
            _invalid()
        reconstructed = ModeRouteResultV1(
            **{
                **mapping,
                "candidates": candidates,
            }
        )
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_validated_candidate(
    value: object,
) -> ModeValidatedCandidateV1:
    if type(value) is not ModeValidatedCandidateV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        reconstructed = ModeValidatedCandidateV1(**mapping)
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _copy_validation_result(
    value: object,
) -> ModeValidationPipelineResultV1:
    if type(value) is not ModeValidationPipelineResultV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        controlled_values = mapping.get("controlled_top10")
        final_values = mapping.get("final_top5")
        if (
            type(controlled_values) is not list
            or type(final_values) is not list
        ):
            _invalid()
        controlled = tuple(
            _copy_validated_candidate(item)
            for item in value.controlled_top10
        )
        final = tuple(
            _copy_validated_candidate(item)
            for item in value.final_top5
        )
        if (
            len(controlled) != len(controlled_values)
            or len(final) != len(final_values)
        ):
            _invalid()
        reconstructed = ModeValidationPipelineResultV1(
            **{
                **mapping,
                "controlled_top10": controlled,
                "final_top5": final,
            }
        )
        if reconstructed.to_mapping() != mapping:
            _invalid()
        return reconstructed
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()


def _execution_route_candidate_parity(
    execution: ModeScanExecutionResultV1,
    route: ModeRouteResultV1,
) -> None:
    if len(execution.candidates) != len(route.candidates):
        _invalid()
    for executed, routed in zip(
        execution.candidates,
        route.candidates,
        strict=True,
    ):
        if (
            executed.candidate_id != routed.candidate_id
            or executed.mode != routed.mode
            or executed.symbol != routed.symbol
            or executed.mode_lineage_sha256
            != routed.mode_lineage_sha256
            or executed.payload_json != routed.payload_json
            or executed.payload_sha256 != routed.payload_sha256
        ):
            _invalid()


def _candidate_identity(value: object) -> tuple[str, str, str, str]:
    if type(value) is ModeRoutedCandidateV1:
        return (
            value.candidate_id,
            value.mode,
            value.symbol,
            value.mode_lineage_sha256,
        )
    if type(value) is ModeValidatedCandidateV1:
        return (
            value.candidate_id,
            value.mode,
            value.symbol,
            value.mode_lineage_sha256,
        )
    _invalid()


def _ordered_identity_subsequence(
    values: tuple[ModeValidatedCandidateV1, ...],
    owners: tuple[
        ModeRoutedCandidateV1 | ModeValidatedCandidateV1,
        ...,
    ],
) -> None:
    owner_positions = {
        _candidate_identity(item): index
        for index, item in enumerate(owners)
    }
    prior = -1
    for item in values:
        identity = _candidate_identity(item)
        if identity not in owner_positions:
            _invalid()
        position = owner_positions[identity]
        if position <= prior:
            _invalid()
        prior = position


def _validate_composed_parity(
    *,
    mode: str,
    due_window_id: str,
    lineage: str,
    observed_at: str,
    include_optional_context: bool,
    plan: ModeScanExecutionPlanV1,
    execution: ModeScanExecutionResultV1,
    route: ModeRouteResultV1,
    validation: ModeValidationPipelineResultV1,
) -> None:
    if (
        plan.mode != mode
        or execution.mode != mode
        or route.mode != mode
        or validation.mode != mode
        or plan.due_window_id != due_window_id
        or route.due_window_id != due_window_id
        or validation.due_window_id != due_window_id
        or plan.mode_lineage_sha256 != lineage
        or execution.mode_lineage_sha256 != lineage
        or route.mode_lineage_sha256 != lineage
        or validation.mode_lineage_sha256 != lineage
        or execution.plan_sha256 != plan.plan_sha256
        or execution.observed_at != observed_at
        or plan.include_optional_context
        is not include_optional_context
        or type(execution.retry_count) is not int
        or execution.retry_count != 0
        or type(route.scanner_invocation_count) is not int
        or route.scanner_invocation_count != 1
        or type(route.retry_count) is not int
        or route.retry_count != 0
        or type(validation.pipeline_invocation_count) is not int
        or validation.pipeline_invocation_count != 1
        or type(validation.retry_count) is not int
        or validation.retry_count != 0
        or validation.input_candidate_count
        != len(route.candidates)
        or validation.controlled_candidate_count
        != len(validation.controlled_top10)
        or validation.final_candidate_count
        != len(validation.final_top5)
    ):
        _invalid()
    planned_symbols = tuple(
        item.canonical_symbol
        for item in plan.full_evaluation_symbols
    )
    planned_timeframes = tuple(
        len(item.candle_fetches)
        for item in plan.full_evaluation_symbols
    )
    if (
        execution.planned_symbol_order != planned_symbols
        or execution.planned_timeframe_counts
        != planned_timeframes
    ):
        _invalid()
    for candidate in execution.candidates:
        if (
            candidate.plan_sha256 != plan.plan_sha256
            or candidate.mode != mode
            or candidate.mode_lineage_sha256 != lineage
        ):
            _invalid()
    for candidate in route.candidates:
        if (
            candidate.mode != mode
            or candidate.mode_lineage_sha256 != lineage
        ):
            _invalid()
    for candidate in (
        *validation.controlled_top10,
        *validation.final_top5,
    ):
        if (
            candidate.mode != mode
            or candidate.mode_lineage_sha256 != lineage
        ):
            _invalid()
    _execution_route_candidate_parity(execution, route)
    _ordered_identity_subsequence(
        validation.controlled_top10,
        route.candidates,
    )
    _ordered_identity_subsequence(
        validation.final_top5,
        validation.controlled_top10,
    )
    if validation.input_route_sha256 != _hash_mapping(
        route.to_mapping()
    ):
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeScanCompositionResultV1:
    schema_version: str
    policy_version: str
    mode: str
    due_window_id: str
    mode_lineage_sha256: str
    observed_at: str
    include_optional_context: bool
    execution_plan: ModeScanExecutionPlanV1
    execution_result: ModeScanExecutionResultV1
    route_result: ModeRouteResultV1
    validation_result: ModeValidationPipelineResultV1
    composition_sha256: str

    def __post_init__(self) -> None:
        try:
            if (
                type(self.schema_version) is not str
                or self.schema_version
                != MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION
                or type(self.policy_version) is not str
                or self.policy_version
                != MODE_SCAN_COMPOSITION_POLICY_VERSION
            ):
                _invalid()
            mode, _profile = _canonical_mode(self.mode)
            due_window_id = _safe_identifier(self.due_window_id)
            lineage = _sha256_hex(self.mode_lineage_sha256)
            observed_at = _canonical_observed_at(self.observed_at)
            if type(self.include_optional_context) is not bool:
                _invalid()
            plan = _copy_plan(self.execution_plan)
            execution = _copy_execution_result(
                self.execution_result
            )
            route = _copy_route_result(self.route_result)
            validation = _copy_validation_result(
                self.validation_result
            )
            _validate_composed_parity(
                mode=mode,
                due_window_id=due_window_id,
                lineage=lineage,
                observed_at=observed_at,
                include_optional_context=(
                    self.include_optional_context
                ),
                plan=plan,
                execution=execution,
                route=route,
                validation=validation,
            )
            object.__setattr__(self, "execution_plan", plan)
            object.__setattr__(
                self,
                "execution_result",
                execution,
            )
            object.__setattr__(self, "route_result", route)
            object.__setattr__(
                self,
                "validation_result",
                validation,
            )
            supplied_hash = _sha256_hex(
                self.composition_sha256
            )
            if supplied_hash != _hash_mapping(
                self._content_mapping()
            ):
                _invalid()
        except ModeScanCompositionValidationError:
            raise
        except Exception:
            _invalid()

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "due_window_id": self.due_window_id,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "observed_at": self.observed_at,
            "include_optional_context":
                self.include_optional_context,
            "execution_plan": self.execution_plan.to_mapping(),
            "execution_result":
                self.execution_result.to_mapping(),
            "route_result": self.route_result.to_mapping(),
            "validation_result":
                self.validation_result.to_mapping(),
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["composition_sha256"] = self.composition_sha256
        return mapping


def compose_mode_scan_pipeline(
    *,
    mode,
    due_window_id,
    market_snapshot,
    include_optional_context,
    observed_at,
    candle_fetcher,
    oi_fetcher,
    technical_evaluator,
    pipeline,
) -> ModeScanCompositionResultV1:
    """Compose one detached router-owned scan and validation call."""

    try:
        canonical_mode, profile = _canonical_mode(mode)
        canonical_due_window_id = _safe_identifier(due_window_id)
        snapshot = _copy_snapshot(market_snapshot)
        if type(include_optional_context) is not bool:
            _invalid()
        if (
            include_optional_context
            and not profile.optional_context_timeframes
        ):
            _invalid()
        canonical_observed_at = _canonical_observed_at(
            observed_at
        )
        if (
            not callable(candle_fetcher)
            or not callable(oi_fetcher)
            or not callable(technical_evaluator)
            or not callable(pipeline)
        ):
            _invalid()

        scanner_invocation_count = 0
        captured_execution_plan = None
        captured_execution_result = None

        def _scanner(*, request):
            nonlocal scanner_invocation_count
            nonlocal captured_execution_plan
            nonlocal captured_execution_result

            if scanner_invocation_count != 0:
                _invalid()
            scanner_invocation_count += 1
            if (
                type(request) is not ModeScanRequestV1
                or request.mode != canonical_mode
                or request.due_window_id
                != canonical_due_window_id
            ):
                _invalid()
            request_lineage = _sha256_hex(
                request.mode_audit_lineage.lineage_sha256
            )
            built_plan = build_mode_scan_execution_plan(
                request=request,
                market_snapshot=snapshot,
                include_optional_context=(
                    include_optional_context
                ),
            )
            plan = _copy_plan(built_plan)
            expected_snapshot_hash = hashlib.sha256(
                _canonical_json(
                    [item.to_mapping() for item in snapshot]
                ).encode("utf-8")
            ).hexdigest()
            if (
                plan.mode != canonical_mode
                or plan.due_window_id
                != canonical_due_window_id
                or plan.mode_lineage_sha256 != request_lineage
                or plan.include_optional_context
                is not include_optional_context
                or plan.market_snapshot_count != len(snapshot)
                or plan.market_snapshot_sha256
                != expected_snapshot_hash
                or type(plan.execution_performed) is not bool
                or plan.execution_performed is not False
                or type(plan.actual_network_call_count) is not int
                or plan.actual_network_call_count != 0
                or type(plan.actual_candidate_count) is not int
                or plan.actual_candidate_count != 0
                or type(
                    plan.validation_pipeline_invocation_count
                ) is not int
                or plan.validation_pipeline_invocation_count != 0
                or type(plan.retry_count) is not int
                or plan.retry_count != 0
            ):
                _invalid()
            executed = execute_mode_scan_plan(
                plan=plan,
                observed_at=canonical_observed_at,
                candle_fetcher=candle_fetcher,
                oi_fetcher=oi_fetcher,
                technical_evaluator=technical_evaluator,
            )
            execution = _copy_execution_result(executed)
            planned_symbols = tuple(
                item.canonical_symbol
                for item in plan.full_evaluation_symbols
            )
            planned_timeframes = tuple(
                len(item.candle_fetches)
                for item in plan.full_evaluation_symbols
            )
            if (
                execution.plan_sha256 != plan.plan_sha256
                or execution.mode != canonical_mode
                or execution.mode_lineage_sha256
                != request_lineage
                or execution.observed_at
                != canonical_observed_at
                or type(execution.retry_count) is not int
                or execution.retry_count != 0
                or execution.planned_symbol_order
                != planned_symbols
                or execution.planned_timeframe_counts
                != planned_timeframes
            ):
                _invalid()
            scanner_rows = tuple(
                candidate.to_scanner_row()
                for candidate in execution.candidates
            )
            if type(scanner_rows) is not tuple:
                _invalid()
            for candidate, row in zip(
                execution.candidates,
                scanner_rows,
                strict=True,
            ):
                if (
                    type(row) is not dict
                    or tuple(row) != _SCANNER_ROW_KEYS
                    or row["candidate_id"]
                    != candidate.candidate_id
                    or row["mode"] != candidate.mode
                    or row["symbol"] != candidate.symbol
                    or row["mode_lineage_sha256"]
                    != candidate.mode_lineage_sha256
                    or type(row["payload"]) is not dict
                    or _canonical_json(row["payload"])
                    != candidate.payload_json
                ):
                    _invalid()
            captured_execution_plan = plan
            captured_execution_result = execution
            return scanner_rows

        routed = route_mode_scan(
            mode=canonical_mode,
            due_window_id=canonical_due_window_id,
            scanner=_scanner,
        )
        route = _copy_route_result(routed)
        if (
            scanner_invocation_count != 1
            or type(captured_execution_plan)
            is not ModeScanExecutionPlanV1
            or type(captured_execution_result)
            is not ModeScanExecutionResultV1
        ):
            _invalid()
        plan = captured_execution_plan
        execution = captured_execution_result
        lineage = plan.mode_lineage_sha256
        if (
            route.mode != canonical_mode
            or route.due_window_id != canonical_due_window_id
            or route.mode_lineage_sha256 != lineage
            or type(route.scanner_invocation_count) is not int
            or route.scanner_invocation_count != 1
            or type(route.retry_count) is not int
            or route.retry_count != 0
        ):
            _invalid()
        _execution_route_candidate_parity(execution, route)

        validated = run_mode_validation_pipeline(
            route_result=route,
            pipeline=pipeline,
        )
        validation = _copy_validation_result(validated)
        _validate_composed_parity(
            mode=canonical_mode,
            due_window_id=canonical_due_window_id,
            lineage=lineage,
            observed_at=canonical_observed_at,
            include_optional_context=include_optional_context,
            plan=plan,
            execution=execution,
            route=route,
            validation=validation,
        )
        content = {
            "schema_version":
                MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION,
            "policy_version":
                MODE_SCAN_COMPOSITION_POLICY_VERSION,
            "mode": canonical_mode,
            "due_window_id": canonical_due_window_id,
            "mode_lineage_sha256": lineage,
            "observed_at": canonical_observed_at,
            "include_optional_context":
                include_optional_context,
            "execution_plan": plan.to_mapping(),
            "execution_result": execution.to_mapping(),
            "route_result": route.to_mapping(),
            "validation_result": validation.to_mapping(),
        }
        result = ModeScanCompositionResultV1(
            schema_version=(
                MODE_SCAN_COMPOSITION_RESULT_SCHEMA_VERSION
            ),
            policy_version=MODE_SCAN_COMPOSITION_POLICY_VERSION,
            mode=canonical_mode,
            due_window_id=canonical_due_window_id,
            mode_lineage_sha256=lineage,
            observed_at=canonical_observed_at,
            include_optional_context=include_optional_context,
            execution_plan=plan,
            execution_result=execution,
            route_result=route,
            validation_result=validation,
            composition_sha256=_hash_mapping(content),
        )
        if type(result) is not ModeScanCompositionResultV1:
            _invalid()
        return result
    except ModeScanCompositionValidationError:
        raise
    except Exception:
        _invalid()
