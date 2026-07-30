"""Pure immutable adapter from mode routing to one validation pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Final

from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_profile_v1 import all_mode_profiles, get_mode_profile
from engine.mode_router_v1 import (
    MODE_ROUTED_CANDIDATE_SCHEMA_VERSION,
    MODE_ROUTER_POLICY_VERSION,
    MODE_ROUTE_RESULT_SCHEMA_VERSION,
    ModeRoutedCandidateV1,
    ModeRouteResultV1,
)


MODE_VALIDATION_PIPELINE_POLICY_VERSION: Final = (
    "mode-validation-pipeline-policy-v1"
)
MODE_VALIDATED_CANDIDATE_SCHEMA_VERSION: Final = (
    "mode-validated-candidate-v1"
)
MODE_VALIDATION_PIPELINE_RESULT_SCHEMA_VERSION: Final = (
    "mode-validation-pipeline-result-v1"
)

CONTROLLED_TOP10: Final = "CONTROLLED_TOP10"
FINAL_TOP5: Final = "FINAL_TOP5"

_CANONICAL_MODES: Final = tuple(
    profile.mode for profile in all_mode_profiles()
)
_SAFE_IDENTIFIER: Final = re.compile(r"[A-Za-z0-9._:+-]{1,128}")
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
_PIPELINE_OUTPUT_KEYS: Final = frozenset(
    ("controlled_top10", "final_top5", "usage")
)
_ADAPTER_OWNED_IDENTITY_KEYS: Final = frozenset(
    (
        "schema_version",
        "policy_version",
        "candidate_id",
        "symbol",
        "mode",
        "mode_lineage_sha256",
        "payload_json",
        "payload_sha256",
        "pipeline_stage",
        "pipeline_rank",
    )
)
_PIPELINE_ROW_PROHIBITED_KEYS: Final = (
    _ADAPTER_OWNED_IDENTITY_KEYS - {"symbol"}
)


class ModeValidationPipelineValidationError(ValueError):
    """Sanitized fail-closed adapter contract failure."""


def _invalid() -> None:
    raise ModeValidationPipelineValidationError(
        "invalid mode validation pipeline"
    ) from None


def _safe_identifier(value: object) -> str:
    if (
        type(value) is not str
        or _SAFE_IDENTIFIER.fullmatch(value) is None
    ):
        _invalid()
    return value


def _symbol(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 128
        or value != value.strip()
    ):
        _invalid()
    return value


def _exact_constant(value: object, expected: str) -> str:
    if type(value) is not str or value != expected:
        _invalid()
    return value


def _sha256_hex(value: object) -> str:
    if (
        type(value) is not str
        or _SHA256_HEX.fullmatch(value) is None
    ):
        _invalid()
    return value


def _canonical_mode(value: object) -> str:
    if type(value) is not str or value not in _CANONICAL_MODES:
        _invalid()
    try:
        profile = get_mode_profile(value)
    except Exception:
        _invalid()
    if type(profile.mode) is not str or profile.mode != value:
        _invalid()
    return profile.mode


def _expected_lineage(mode: str) -> str:
    try:
        lineage = build_mode_audit_lineage(mode).lineage_sha256
    except Exception:
        _invalid()
    return _sha256_hex(lineage)


def _exact_integer(
    value: object,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if type(value) is not int or value < minimum:
        _invalid()
    if maximum is not None and value > maximum:
        _invalid()
    return value


def _validate_json_value(value: object) -> None:
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        if not math.isfinite(value):
            _invalid()
        return
    if type(value) is list:
        for item in value:
            _validate_json_value(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _invalid()
            _validate_json_value(item)
        return
    _invalid()


def _canonical_json(value: object) -> str:
    _validate_json_value(value)
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


def _canonical_dict_json(value: object) -> str:
    if type(value) is not dict:
        _invalid()
    return _canonical_json(value)


def _decoded_dict(payload_json: object) -> dict[str, Any]:
    if type(payload_json) is not str:
        _invalid()
    try:
        value = json.loads(payload_json)
    except Exception:
        _invalid()
    if type(value) is not dict:
        _invalid()
    if _canonical_dict_json(value) != payload_json:
        _invalid()
    return value


def _hash_json(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _validate_payload_keys(
    payload: dict[str, Any],
    prohibited_keys: frozenset[str],
) -> None:
    if any(key in prohibited_keys for key in payload):
        _invalid()


def _pipeline_row(
    value: object,
) -> tuple[str, dict[str, Any], str]:
    if type(value) is not dict:
        _invalid()
    row_json = _canonical_dict_json(value)
    row = _decoded_dict(row_json)
    if "symbol" not in row:
        _invalid()
    symbol = _symbol(row["symbol"])
    _validate_payload_keys(row, _PIPELINE_ROW_PROHIBITED_KEYS)
    del row["symbol"]
    payload_json = _canonical_dict_json(row)
    return symbol, row, payload_json


@dataclass(frozen=True, slots=True)
class ModeValidatedCandidateV1:
    """One canonical validation-stage row with route-owned identity."""

    schema_version: str
    policy_version: str
    candidate_id: str
    mode: str
    symbol: str
    mode_lineage_sha256: str
    pipeline_stage: str
    pipeline_rank: int
    payload_json: str
    payload_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_VALIDATED_CANDIDATE_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_VALIDATION_PIPELINE_POLICY_VERSION,
            )
            mode = _canonical_mode(self.mode)
            expected_lineage = _expected_lineage(mode)
            _safe_identifier(self.candidate_id)
            _symbol(self.symbol)
            if (
                _sha256_hex(self.mode_lineage_sha256)
                != expected_lineage
            ):
                _invalid()
            if type(self.pipeline_stage) is not str:
                _invalid()
            if self.pipeline_stage == CONTROLLED_TOP10:
                maximum_rank = 10
            elif self.pipeline_stage == FINAL_TOP5:
                maximum_rank = 5
            else:
                _invalid()
            _exact_integer(
                self.pipeline_rank,
                minimum=1,
                maximum=maximum_rank,
            )
            payload = _decoded_dict(self.payload_json)
            _validate_payload_keys(
                payload,
                _ADAPTER_OWNED_IDENTITY_KEYS,
            )
            if (
                _sha256_hex(self.payload_sha256)
                != _hash_json(self.payload_json)
            ):
                _invalid()
        except ModeValidationPipelineValidationError:
            raise
        except Exception:
            _invalid()

    def payload_copy(self) -> dict[str, Any]:
        """Return a fresh decoded pipeline payload."""

        return _decoded_dict(self.payload_json)

    def to_mapping(self) -> dict[str, object]:
        """Return a fresh deterministic mapping of all candidate fields."""

        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "candidate_id": self.candidate_id,
            "mode": self.mode,
            "symbol": self.symbol,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "pipeline_stage": self.pipeline_stage,
            "pipeline_rank": self.pipeline_rank,
            "payload_json": self.payload_json,
            "payload_sha256": self.payload_sha256,
        }


@dataclass(frozen=True, slots=True)
class ModeValidationPipelineResultV1:
    """Immutable result of exactly one injected validation pipeline call."""

    schema_version: str
    policy_version: str
    mode: str
    due_window_id: str
    mode_lineage_sha256: str
    input_route_sha256: str
    pipeline_invocation_count: int
    retry_count: int
    input_candidate_count: int
    controlled_candidate_count: int
    final_candidate_count: int
    controlled_top10: tuple[ModeValidatedCandidateV1, ...]
    final_top5: tuple[ModeValidatedCandidateV1, ...]
    usage_json: str
    usage_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_VALIDATION_PIPELINE_RESULT_SCHEMA_VERSION,
            )
            _exact_constant(
                self.policy_version,
                MODE_VALIDATION_PIPELINE_POLICY_VERSION,
            )
            mode = _canonical_mode(self.mode)
            expected_lineage = _expected_lineage(mode)
            _safe_identifier(self.due_window_id)
            if (
                _sha256_hex(self.mode_lineage_sha256)
                != expected_lineage
            ):
                _invalid()
            _sha256_hex(self.input_route_sha256)
            if (
                type(self.pipeline_invocation_count) is not int
                or self.pipeline_invocation_count != 1
            ):
                _invalid()
            if (
                type(self.retry_count) is not int
                or self.retry_count != 0
            ):
                _invalid()
            input_count = _exact_integer(
                self.input_candidate_count,
                minimum=0,
            )
            controlled_count = _exact_integer(
                self.controlled_candidate_count,
                minimum=0,
                maximum=10,
            )
            final_count = _exact_integer(
                self.final_candidate_count,
                minimum=0,
                maximum=5,
            )
            if controlled_count != min(input_count, 10):
                _invalid()

            if type(self.controlled_top10) not in (list, tuple):
                _invalid()
            if type(self.final_top5) not in (list, tuple):
                _invalid()
            controlled = tuple(self.controlled_top10)
            final = tuple(self.final_top5)
            object.__setattr__(self, "controlled_top10", controlled)
            object.__setattr__(self, "final_top5", final)
            if (
                len(controlled) != controlled_count
                or len(final) != final_count
                or final_count > controlled_count
            ):
                _invalid()

            controlled_positions: dict[str, int] = {}
            controlled_by_symbol: dict[
                str, ModeValidatedCandidateV1
            ] = {}
            controlled_candidate_ids: set[str] = set()
            for rank, candidate in enumerate(controlled, start=1):
                if type(candidate) is not ModeValidatedCandidateV1:
                    _invalid()
                _exact_constant(
                    candidate.schema_version,
                    MODE_VALIDATED_CANDIDATE_SCHEMA_VERSION,
                )
                _exact_constant(
                    candidate.policy_version,
                    MODE_VALIDATION_PIPELINE_POLICY_VERSION,
                )
                candidate_mode = _canonical_mode(candidate.mode)
                candidate_lineage = _sha256_hex(
                    candidate.mode_lineage_sha256
                )
                candidate_id = _safe_identifier(
                    candidate.candidate_id
                )
                symbol = _symbol(candidate.symbol)
                if (
                    candidate_mode != mode
                    or candidate_lineage != expected_lineage
                    or type(candidate.pipeline_stage) is not str
                    or candidate.pipeline_stage != CONTROLLED_TOP10
                    or type(candidate.pipeline_rank) is not int
                    or candidate.pipeline_rank != rank
                    or symbol in controlled_positions
                    or candidate_id in controlled_candidate_ids
                ):
                    _invalid()
                payload = _decoded_dict(candidate.payload_json)
                _validate_payload_keys(
                    payload,
                    _ADAPTER_OWNED_IDENTITY_KEYS,
                )
                if (
                    _sha256_hex(candidate.payload_sha256)
                    != _hash_json(candidate.payload_json)
                ):
                    _invalid()
                controlled_positions[symbol] = rank
                controlled_by_symbol[symbol] = candidate
                controlled_candidate_ids.add(candidate_id)

            last_position = 0
            final_symbols: set[str] = set()
            final_candidate_ids: set[str] = set()
            for rank, candidate in enumerate(final, start=1):
                if type(candidate) is not ModeValidatedCandidateV1:
                    _invalid()
                _exact_constant(
                    candidate.schema_version,
                    MODE_VALIDATED_CANDIDATE_SCHEMA_VERSION,
                )
                _exact_constant(
                    candidate.policy_version,
                    MODE_VALIDATION_PIPELINE_POLICY_VERSION,
                )
                candidate_mode = _canonical_mode(candidate.mode)
                candidate_lineage = _sha256_hex(
                    candidate.mode_lineage_sha256
                )
                candidate_id = _safe_identifier(
                    candidate.candidate_id
                )
                symbol = _symbol(candidate.symbol)
                if (
                    candidate_mode != mode
                    or candidate_lineage != expected_lineage
                    or type(candidate.pipeline_stage) is not str
                    or candidate.pipeline_stage != FINAL_TOP5
                    or type(candidate.pipeline_rank) is not int
                    or candidate.pipeline_rank != rank
                    or symbol in final_symbols
                    or symbol not in controlled_by_symbol
                    or candidate_id in final_candidate_ids
                ):
                    _invalid()
                controlled_candidate = controlled_by_symbol[
                    symbol
                ]
                position = controlled_positions[symbol]
                payload = _decoded_dict(candidate.payload_json)
                _validate_payload_keys(
                    payload,
                    _ADAPTER_OWNED_IDENTITY_KEYS,
                )
                if (
                    position <= last_position
                    or candidate_id
                    != controlled_candidate.candidate_id
                    or candidate.payload_json
                    != controlled_candidate.payload_json
                    or candidate.payload_sha256
                    != controlled_candidate.payload_sha256
                    or _sha256_hex(candidate.payload_sha256)
                    != _hash_json(candidate.payload_json)
                ):
                    _invalid()
                final_symbols.add(symbol)
                final_candidate_ids.add(candidate_id)
                last_position = position

            usage = _decoded_dict(self.usage_json)
            if (
                _sha256_hex(self.usage_sha256)
                != _hash_json(self.usage_json)
            ):
                _invalid()
            _canonical_dict_json(usage)
        except ModeValidationPipelineValidationError:
            raise
        except Exception:
            _invalid()

    def usage_copy(self) -> dict[str, Any]:
        """Return a fresh decoded usage object."""

        return _decoded_dict(self.usage_json)

    def to_mapping(self) -> dict[str, object]:
        """Return a detached deterministic mapping of the result."""

        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "mode": self.mode,
            "due_window_id": self.due_window_id,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "input_route_sha256": self.input_route_sha256,
            "pipeline_invocation_count":
                self.pipeline_invocation_count,
            "retry_count": self.retry_count,
            "input_candidate_count": self.input_candidate_count,
            "controlled_candidate_count":
                self.controlled_candidate_count,
            "final_candidate_count": self.final_candidate_count,
            "controlled_top10": [
                candidate.to_mapping()
                for candidate in self.controlled_top10
            ],
            "final_top5": [
                candidate.to_mapping()
                for candidate in self.final_top5
            ],
            "usage_json": self.usage_json,
            "usage_sha256": self.usage_sha256,
        }


def _validated_route_candidates(
    route_result: ModeRouteResultV1,
) -> tuple[
    tuple[ModeRoutedCandidateV1, ...],
    dict[str, ModeRoutedCandidateV1],
]:
    mode = _canonical_mode(route_result.mode)
    expected_lineage = _expected_lineage(mode)
    _exact_constant(
        route_result.schema_version,
        MODE_ROUTE_RESULT_SCHEMA_VERSION,
    )
    _exact_constant(
        route_result.router_policy_version,
        MODE_ROUTER_POLICY_VERSION,
    )
    _safe_identifier(route_result.due_window_id)
    if (
        _sha256_hex(route_result.mode_lineage_sha256)
        != expected_lineage
    ):
        _invalid()
    if (
        type(route_result.scanner_invocation_count) is not int
        or route_result.scanner_invocation_count != 1
        or type(route_result.retry_count) is not int
        or route_result.retry_count != 0
        or type(route_result.candidates) is not tuple
    ):
        _invalid()

    candidates = tuple(route_result.candidates)
    candidate_ids: set[str] = set()
    by_symbol: dict[str, ModeRoutedCandidateV1] = {}
    for candidate in candidates:
        if type(candidate) is not ModeRoutedCandidateV1:
            _invalid()
        _exact_constant(
            candidate.schema_version,
            MODE_ROUTED_CANDIDATE_SCHEMA_VERSION,
        )
        candidate_id = _safe_identifier(candidate.candidate_id)
        symbol = _symbol(candidate.symbol)
        if (
            _canonical_mode(candidate.mode) != mode
            or _sha256_hex(candidate.mode_lineage_sha256)
            != expected_lineage
            or candidate_id in candidate_ids
            or symbol in by_symbol
        ):
            _invalid()
        payload = _decoded_dict(candidate.payload_json)
        _validate_payload_keys(
            payload,
            _ADAPTER_OWNED_IDENTITY_KEYS,
        )
        if (
            _sha256_hex(candidate.payload_sha256)
            != _hash_json(candidate.payload_json)
        ):
            _invalid()
        candidate_ids.add(candidate_id)
        by_symbol[symbol] = candidate
    return candidates, by_symbol


def _validated_pipeline_output(
    value: object,
) -> tuple[list[object] | tuple[object, ...], list[object] | tuple[object, ...], str]:
    if type(value) is not dict:
        _invalid()
    if (
        any(type(key) is not str for key in value)
        or frozenset(value) != _PIPELINE_OUTPUT_KEYS
    ):
        _invalid()
    controlled = value["controlled_top10"]
    final = value["final_top5"]
    usage = value["usage"]
    if type(controlled) not in (list, tuple):
        _invalid()
    if type(final) not in (list, tuple):
        _invalid()
    usage_json = _canonical_dict_json(usage)
    return controlled, final, usage_json


def _validated_candidate(
    *,
    routed: ModeRoutedCandidateV1,
    stage: str,
    rank: int,
    payload_json: str,
) -> ModeValidatedCandidateV1:
    return ModeValidatedCandidateV1(
        schema_version=MODE_VALIDATED_CANDIDATE_SCHEMA_VERSION,
        policy_version=MODE_VALIDATION_PIPELINE_POLICY_VERSION,
        candidate_id=routed.candidate_id,
        mode=routed.mode,
        symbol=routed.symbol,
        mode_lineage_sha256=routed.mode_lineage_sha256,
        pipeline_stage=stage,
        pipeline_rank=rank,
        payload_json=payload_json,
        payload_sha256=_hash_json(payload_json),
    )


def run_mode_validation_pipeline(
    *,
    route_result: object,
    pipeline: Callable[[list[dict[str, Any]]], object],
) -> ModeValidationPipelineResultV1:
    """Invoke one injected pipeline and reattach exact routed identity."""

    if type(route_result) is not ModeRouteResultV1:
        _invalid()
    if not callable(pipeline):
        _invalid()

    try:
        candidates, routed_by_symbol = _validated_route_candidates(
            route_result
        )
        route_json = _canonical_dict_json(route_result.to_mapping())
        input_route_sha256 = _hash_json(route_json)

        pipeline_input: list[dict[str, Any]] = []
        for candidate in candidates:
            row = candidate.payload_copy()
            _validate_payload_keys(
                row,
                _ADAPTER_OWNED_IDENTITY_KEYS,
            )
            row["symbol"] = candidate.symbol
            pipeline_input.append(row)

        try:
            pipeline_output = pipeline(pipeline_input)
        except Exception:
            _invalid()

        controlled_rows, final_rows, usage_json = (
            _validated_pipeline_output(pipeline_output)
        )
        expected_controlled_count = min(len(candidates), 10)
        if (
            len(controlled_rows) != expected_controlled_count
            or len(controlled_rows) > 10
            or len(final_rows) > 5
        ):
            _invalid()

        controlled: list[ModeValidatedCandidateV1] = []
        controlled_payloads: dict[str, str] = {}
        controlled_positions: dict[str, int] = {}
        for rank, row_value in enumerate(controlled_rows, start=1):
            symbol, _payload, payload_json = _pipeline_row(row_value)
            if (
                symbol not in routed_by_symbol
                or symbol in controlled_payloads
            ):
                _invalid()
            controlled_payloads[symbol] = payload_json
            controlled_positions[symbol] = rank
            controlled.append(
                _validated_candidate(
                    routed=routed_by_symbol[symbol],
                    stage=CONTROLLED_TOP10,
                    rank=rank,
                    payload_json=payload_json,
                )
            )

        final: list[ModeValidatedCandidateV1] = []
        final_symbols: set[str] = set()
        last_controlled_position = 0
        for rank, row_value in enumerate(final_rows, start=1):
            symbol, _payload, payload_json = _pipeline_row(row_value)
            if (
                symbol not in routed_by_symbol
                or symbol not in controlled_payloads
                or symbol in final_symbols
                or payload_json != controlled_payloads[symbol]
            ):
                _invalid()
            controlled_position = controlled_positions[symbol]
            if controlled_position <= last_controlled_position:
                _invalid()
            final_symbols.add(symbol)
            last_controlled_position = controlled_position
            final.append(
                _validated_candidate(
                    routed=routed_by_symbol[symbol],
                    stage=FINAL_TOP5,
                    rank=rank,
                    payload_json=payload_json,
                )
            )

        return ModeValidationPipelineResultV1(
            schema_version=(
                MODE_VALIDATION_PIPELINE_RESULT_SCHEMA_VERSION
            ),
            policy_version=MODE_VALIDATION_PIPELINE_POLICY_VERSION,
            mode=route_result.mode,
            due_window_id=route_result.due_window_id,
            mode_lineage_sha256=route_result.mode_lineage_sha256,
            input_route_sha256=input_route_sha256,
            pipeline_invocation_count=1,
            retry_count=0,
            input_candidate_count=len(candidates),
            controlled_candidate_count=len(controlled),
            final_candidate_count=len(final),
            controlled_top10=tuple(controlled),
            final_top5=tuple(final),
            usage_json=usage_json,
            usage_sha256=_hash_json(usage_json),
        )
    except ModeValidationPipelineValidationError:
        raise
    except Exception:
        _invalid()
