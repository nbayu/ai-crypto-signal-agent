"""Detached sequential executor for an already-validated mode scan plan."""

from __future__ import annotations

from datetime import datetime
from typing import Final

from engine.mode_fetch_budget_cadence_v1 import (
    ModeFetchBudgetV1,
    ModeTimeframeFetchV1,
    PER_SYMBOL_OI_HISTORY_IP_WEIGHT,
)
from engine.mode_profile_v1 import ModeProfileV1, get_mode_profile
from engine.mode_scan_execution_evidence_v1 import (
    MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
    MODE_SYMBOL_EXECUTION_OUTCOME_SCHEMA_VERSION,
    OUTCOME_CANDIDATE,
    OUTCOME_NO_CANDIDATE,
    OUTCOME_SKIPPED,
    REASON_CANDIDATE_ACCEPTED,
    REASON_CANDLE_BOUNDARY_EXCEPTION,
    REASON_CANDLE_EVIDENCE_INVALID,
    REASON_EVALUATOR_EXCEPTION,
    REASON_EVALUATOR_RESULT_INVALID,
    REASON_NO_CANDIDATE,
    REASON_OI_BOUNDARY_EXCEPTION,
    REASON_OI_EVIDENCE_INVALID,
    ModeOiExecutionEvidenceV1,
    ModeOiObservationV1,
    ModeScanExecutionResultV1,
    ModeSymbolExecutionOutcomeV1,
    ModeTechnicalEvaluatorPayloadV1,
    ModeTimeframeExecutionEvidenceV1,
    ModeUtcCandleV1,
    build_mode_execution_candidate_row,
    build_mode_oi_execution_evidence,
    build_mode_scan_execution_result,
    build_mode_timeframe_execution_evidence,
)
from engine.mode_scan_execution_plan_v1 import (
    ModeScanExecutionPlanV1,
    ModeSymbolExecutionPlanV1,
    ModeTimeframeFetchPlanV1,
)


MODE_SCAN_EXECUTOR_POLICY_VERSION: Final = (
    "mode-scan-executor-policy-v1"
)

__all__ = (
    "MODE_SCAN_EXECUTOR_POLICY_VERSION",
    "ModeScanExecutorValidationError",
    "execute_mode_scan_plan",
)

_TRIGGER_ROLE: Final = "TRIGGER"
_OI_PERIOD: Final = "5m"
_UTC_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"


class ModeScanExecutorValidationError(ValueError):
    """Sanitized boundary error for whole-execution failures."""


def _invalid() -> None:
    raise ModeScanExecutorValidationError(
        "invalid mode scan executor"
    ) from None


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
        return ModeTimeframeFetchPlanV1(
            **{
                **mapping,
                "cache_key_fields": tuple(cache_fields),
            }
        )
    except ModeScanExecutorValidationError:
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
        fetches = []
        for item in fetch_values:
            if type(item) is not dict:
                _invalid()
            cache_fields = item.get("cache_key_fields")
            if type(cache_fields) is not list:
                _invalid()
            fetches.append(
                ModeTimeframeFetchPlanV1(
                    **{
                        **item,
                        "cache_key_fields": tuple(cache_fields),
                    }
                )
            )
        return ModeSymbolExecutionPlanV1(
            **{
                **mapping,
                "candle_fetches": tuple(fetches),
            }
        )
    except ModeScanExecutorValidationError:
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
        symbols = []
        for item in symbol_values:
            if type(item) is not dict:
                _invalid()
            fetch_values = item.get("candle_fetches")
            if type(fetch_values) is not list:
                _invalid()
            fetches = []
            for fetch in fetch_values:
                if type(fetch) is not dict:
                    _invalid()
                nested_cache_fields = fetch.get("cache_key_fields")
                if type(nested_cache_fields) is not list:
                    _invalid()
                fetches.append(
                    ModeTimeframeFetchPlanV1(
                        **{
                            **fetch,
                            "cache_key_fields": tuple(
                                nested_cache_fields
                            ),
                        }
                    )
                )
            symbols.append(
                ModeSymbolExecutionPlanV1(
                    **{
                        **item,
                        "candle_fetches": tuple(fetches),
                    }
                )
            )
        return ModeScanExecutionPlanV1(
            **{
                **mapping,
                "discovery_symbols": tuple(discovery_values),
                "full_evaluation_symbols": tuple(symbols),
                "cache_key_fields": tuple(cache_fields),
            }
        )
    except ModeScanExecutorValidationError:
        raise
    except Exception:
        _invalid()


def _copy_fetch_budget(plan: ModeScanExecutionPlanV1) -> ModeFetchBudgetV1:
    try:
        mapping = plan.fetch_budget_copy()
        if type(mapping) is not dict:
            _invalid()
        fetch_values = mapping.get("timeframe_fetches")
        if type(fetch_values) is not list:
            _invalid()
        fetches = []
        for item in fetch_values:
            if type(item) is not dict:
                _invalid()
            purposes = item.get("purposes")
            if type(purposes) is not list:
                _invalid()
            fetches.append(
                ModeTimeframeFetchV1(
                    **{
                        **item,
                        "purposes": tuple(purposes),
                    }
                )
            )
        return ModeFetchBudgetV1(
            **{
                **mapping,
                "timeframe_fetches": tuple(fetches),
            }
        )
    except ModeScanExecutorValidationError:
        raise
    except Exception:
        _invalid()


def _matching_budget_row(
    timeframe_plan: ModeTimeframeFetchPlanV1,
    budget: ModeFetchBudgetV1,
) -> ModeTimeframeFetchV1:
    matches = tuple(
        row
        for row in budget.timeframe_fetches
        if (
            row.mode == timeframe_plan.mode
            and row.timeframe == timeframe_plan.timeframe
            and "+".join(row.purposes) == timeframe_plan.role
            and row.closed_candle_count
            == timeframe_plan.closed_candle_limit
            and row.raw_fetch_limit == timeframe_plan.raw_fetch_limit
            and row.request_count == 1
        )
    )
    if len(matches) != 1:
        _invalid()
    return matches[0]


def _validated_inputs(
    *,
    plan: object,
    observed_at: object,
    candle_fetcher: object,
    oi_fetcher: object,
    technical_evaluator: object,
) -> tuple[
    ModeScanExecutionPlanV1,
    str,
    tuple[tuple[int, ...], ...],
]:
    copied_plan = _copy_plan(plan)
    observed = _canonical_observed_at(observed_at)
    if (
        not callable(candle_fetcher)
        or not callable(oi_fetcher)
        or not callable(technical_evaluator)
    ):
        _invalid()
    budget = _copy_fetch_budget(copied_plan)
    profile = get_mode_profile(copied_plan.mode)
    if type(profile) is not ModeProfileV1:
        _invalid()
    if (
        budget.mode != copied_plan.mode
        or budget.include_optional_context
        is not copied_plan.include_optional_context
        or budget.symbol_count
        != len(copied_plan.full_evaluation_symbols)
        or PER_SYMBOL_OI_HISTORY_IP_WEIGHT != 0
    ):
        _invalid()

    symbol_weights = []
    for rank, symbol_plan in enumerate(
        copied_plan.full_evaluation_symbols,
        start=1,
    ):
        if (
            symbol_plan.full_evaluation_rank != rank
            or symbol_plan.open_interest_history_request_count != 1
        ):
            _invalid()
        trigger_rows = tuple(
            row
            for row in symbol_plan.candle_fetches
            if row.role == _TRIGGER_ROLE
        )
        if (
            len(trigger_rows) != 1
            or trigger_rows[0].timeframe
            != profile.trigger_timeframe
        ):
            _invalid()
        weights = tuple(
            _matching_budget_row(row, budget).ip_weight
            for row in symbol_plan.candle_fetches
        )
        symbol_weights.append(weights)

    planned_candle_calls = sum(
        len(item) for item in symbol_weights
    )
    planned_oi_calls = len(copied_plan.full_evaluation_symbols)
    planned_requests = (
        budget.total_request_count
        - budget.market_level_request_count
    )
    planned_weight = (
        budget.total_ip_weight
        - budget.market_level_ip_weight
    )
    if (
        planned_requests
        != planned_candle_calls + planned_oi_calls
        or planned_weight
        != sum(sum(item) for item in symbol_weights)
    ):
        _invalid()
    return copied_plan, observed, tuple(symbol_weights)


def _outcome(
    *,
    plan: ModeScanExecutionPlanV1,
    symbol_plan: ModeSymbolExecutionPlanV1,
    outcome_kind: str,
    reason_code: str,
    timeframe_hashes: tuple[str, ...],
    oi_hash: str | None,
    evaluator_hash: str | None,
    candidate_row: object,
) -> ModeSymbolExecutionOutcomeV1:
    return ModeSymbolExecutionOutcomeV1(
        schema_version=MODE_SYMBOL_EXECUTION_OUTCOME_SCHEMA_VERSION,
        policy_version=MODE_SCAN_EXECUTION_EVIDENCE_POLICY_VERSION,
        mode=plan.mode,
        mode_lineage_sha256=plan.mode_lineage_sha256,
        canonical_symbol=symbol_plan.canonical_symbol,
        full_evaluation_rank=symbol_plan.full_evaluation_rank,
        outcome_kind=outcome_kind,
        reason_code=reason_code,
        timeframe_evidence_sha256s=timeframe_hashes,
        oi_evidence_sha256=oi_hash,
        evaluator_payload_sha256=evaluator_hash,
        candidate_row=candidate_row,
    )


def _copy_evaluator_payload(
    value: object,
) -> ModeTechnicalEvaluatorPayloadV1:
    if type(value) is not ModeTechnicalEvaluatorPayloadV1:
        _invalid()
    try:
        mapping = value.to_mapping()
        if type(mapping) is not dict:
            _invalid()
        return ModeTechnicalEvaluatorPayloadV1(**mapping)
    except ModeScanExecutorValidationError:
        raise
    except Exception:
        _invalid()


def _execute_validated(
    *,
    plan: ModeScanExecutionPlanV1,
    observed_at: str,
    candle_fetcher: object,
    oi_fetcher: object,
    technical_evaluator: object,
    symbol_weights: tuple[tuple[int, ...], ...],
) -> ModeScanExecutionResultV1:
    outcomes = []
    candidate_ids: set[str] = set()
    candidate_symbols: set[str] = set()
    actual_candle_call_count = 0
    actual_oi_call_count = 0
    actual_evaluator_invocation_count = 0
    actual_executor_ip_weight = 0

    for symbol_index, symbol_plan in enumerate(
        plan.full_evaluation_symbols
    ):
        timeframe_evidence = []
        candle_failure_reason = None
        for timeframe_index, timeframe_plan in enumerate(
            symbol_plan.candle_fetches
        ):
            actual_candle_call_count += 1
            actual_executor_ip_weight += (
                symbol_weights[symbol_index][timeframe_index]
            )
            try:
                raw_candles = candle_fetcher(
                    timeframe_plan=timeframe_plan,
                    observed_at=observed_at,
                )
            except Exception:
                candle_failure_reason = (
                    REASON_CANDLE_BOUNDARY_EXCEPTION
                )
                break
            if (
                type(raw_candles) is not tuple
                or any(
                    type(item) is not ModeUtcCandleV1
                    for item in raw_candles
                )
            ):
                candle_failure_reason = (
                    REASON_CANDLE_EVIDENCE_INVALID
                )
                break
            try:
                evidence = (
                    build_mode_timeframe_execution_evidence(
                        timeframe_plan=timeframe_plan,
                        observed_at=observed_at,
                        raw_candles=raw_candles,
                    )
                )
                if (
                    type(evidence)
                    is not ModeTimeframeExecutionEvidenceV1
                ):
                    raise ValueError
            except Exception:
                candle_failure_reason = (
                    REASON_CANDLE_EVIDENCE_INVALID
                )
                break
            timeframe_evidence.append(evidence)

        timeframe_hashes = tuple(
            item.evidence_sha256 for item in timeframe_evidence
        )
        if candle_failure_reason is not None:
            outcomes.append(
                _outcome(
                    plan=plan,
                    symbol_plan=symbol_plan,
                    outcome_kind=OUTCOME_SKIPPED,
                    reason_code=candle_failure_reason,
                    timeframe_hashes=timeframe_hashes,
                    oi_hash=None,
                    evaluator_hash=None,
                    candidate_row=None,
                )
            )
            continue

        actual_oi_call_count += 1
        try:
            observations = oi_fetcher(
                symbol_plan=symbol_plan,
                observed_at=observed_at,
                period=_OI_PERIOD,
            )
        except Exception:
            outcomes.append(
                _outcome(
                    plan=plan,
                    symbol_plan=symbol_plan,
                    outcome_kind=OUTCOME_SKIPPED,
                    reason_code=REASON_OI_BOUNDARY_EXCEPTION,
                    timeframe_hashes=timeframe_hashes,
                    oi_hash=None,
                    evaluator_hash=None,
                    candidate_row=None,
                )
            )
            continue
        if (
            type(observations) is not tuple
            or any(
                type(item) is not ModeOiObservationV1
                for item in observations
            )
        ):
            outcomes.append(
                _outcome(
                    plan=plan,
                    symbol_plan=symbol_plan,
                    outcome_kind=OUTCOME_SKIPPED,
                    reason_code=REASON_OI_EVIDENCE_INVALID,
                    timeframe_hashes=timeframe_hashes,
                    oi_hash=None,
                    evaluator_hash=None,
                    candidate_row=None,
                )
            )
            continue
        try:
            oi_evidence = build_mode_oi_execution_evidence(
                mode=plan.mode,
                mode_lineage_sha256=plan.mode_lineage_sha256,
                canonical_symbol=symbol_plan.canonical_symbol,
                observed_at=observed_at,
                observations=observations,
                request_invocation_count=1,
            )
            if type(oi_evidence) is not ModeOiExecutionEvidenceV1:
                raise ValueError
        except Exception:
            outcomes.append(
                _outcome(
                    plan=plan,
                    symbol_plan=symbol_plan,
                    outcome_kind=OUTCOME_SKIPPED,
                    reason_code=REASON_OI_EVIDENCE_INVALID,
                    timeframe_hashes=timeframe_hashes,
                    oi_hash=None,
                    evaluator_hash=None,
                    candidate_row=None,
                )
            )
            continue

        trigger_matches = tuple(
            evidence
            for timeframe_plan, evidence in zip(
                symbol_plan.candle_fetches,
                timeframe_evidence,
                strict=True,
            )
            if timeframe_plan.role == _TRIGGER_ROLE
        )
        if len(trigger_matches) != 1:
            _invalid()
        trigger_candle_close_at = (
            trigger_matches[0].closed_candle_close_at
        )

        actual_evaluator_invocation_count += 1
        try:
            evaluator_result = technical_evaluator(
                plan=plan,
                symbol_plan=symbol_plan,
                timeframe_evidence=tuple(timeframe_evidence),
                oi_evidence=oi_evidence,
                trigger_candle_close_at=(
                    trigger_candle_close_at
                ),
            )
        except Exception:
            outcomes.append(
                _outcome(
                    plan=plan,
                    symbol_plan=symbol_plan,
                    outcome_kind=OUTCOME_SKIPPED,
                    reason_code=REASON_EVALUATOR_EXCEPTION,
                    timeframe_hashes=timeframe_hashes,
                    oi_hash=oi_evidence.evidence_sha256,
                    evaluator_hash=None,
                    candidate_row=None,
                )
            )
            continue

        if evaluator_result is None:
            outcomes.append(
                _outcome(
                    plan=plan,
                    symbol_plan=symbol_plan,
                    outcome_kind=OUTCOME_NO_CANDIDATE,
                    reason_code=REASON_NO_CANDIDATE,
                    timeframe_hashes=timeframe_hashes,
                    oi_hash=oi_evidence.evidence_sha256,
                    evaluator_hash=None,
                    candidate_row=None,
                )
            )
            continue

        try:
            evaluator_payload = _copy_evaluator_payload(
                evaluator_result
            )
            payload_mapping = evaluator_payload.payload_copy()
            if (
                type(payload_mapping) is not dict
                or evaluator_payload.trigger_candle_close_at
                != trigger_candle_close_at
                or payload_mapping.get("reference_candle_at")
                != trigger_candle_close_at
            ):
                _invalid()
        except Exception:
            outcomes.append(
                _outcome(
                    plan=plan,
                    symbol_plan=symbol_plan,
                    outcome_kind=OUTCOME_SKIPPED,
                    reason_code=REASON_EVALUATOR_RESULT_INVALID,
                    timeframe_hashes=timeframe_hashes,
                    oi_hash=oi_evidence.evidence_sha256,
                    evaluator_hash=None,
                    candidate_row=None,
                )
            )
            continue

        candidate = build_mode_execution_candidate_row(
            plan=plan,
            symbol_plan=symbol_plan,
            evaluator_payload=evaluator_payload,
            trigger_candle_close_at=trigger_candle_close_at,
        )
        if (
            candidate.candidate_id in candidate_ids
            or candidate.symbol in candidate_symbols
        ):
            _invalid()
        candidate_ids.add(candidate.candidate_id)
        candidate_symbols.add(candidate.symbol)
        outcomes.append(
            _outcome(
                plan=plan,
                symbol_plan=symbol_plan,
                outcome_kind=OUTCOME_CANDIDATE,
                reason_code=REASON_CANDIDATE_ACCEPTED,
                timeframe_hashes=timeframe_hashes,
                oi_hash=oi_evidence.evidence_sha256,
                evaluator_hash=evaluator_payload.payload_sha256,
                candidate_row=candidate,
            )
        )

    result = build_mode_scan_execution_result(
        plan=plan,
        observed_at=observed_at,
        outcomes=tuple(outcomes),
        actual_candle_call_count=actual_candle_call_count,
        actual_oi_call_count=actual_oi_call_count,
        actual_evaluator_invocation_count=(
            actual_evaluator_invocation_count
        ),
        actual_executor_ip_weight=actual_executor_ip_weight,
    )
    if type(result) is not ModeScanExecutionResultV1:
        _invalid()
    return result


def execute_mode_scan_plan(
    *,
    plan,
    observed_at,
    candle_fetcher,
    oi_fetcher,
    technical_evaluator,
) -> ModeScanExecutionResultV1:
    """Execute one detached plan with injected, single-attempt boundaries."""

    try:
        copied_plan, observed, symbol_weights = _validated_inputs(
            plan=plan,
            observed_at=observed_at,
            candle_fetcher=candle_fetcher,
            oi_fetcher=oi_fetcher,
            technical_evaluator=technical_evaluator,
        )
        return _execute_validated(
            plan=copied_plan,
            observed_at=observed,
            candle_fetcher=candle_fetcher,
            oi_fetcher=oi_fetcher,
            technical_evaluator=technical_evaluator,
            symbol_weights=symbol_weights,
        )
    except ModeScanExecutorValidationError:
        raise
    except Exception:
        _invalid()
