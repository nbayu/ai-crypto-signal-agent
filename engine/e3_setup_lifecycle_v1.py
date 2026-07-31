import dataclasses
import hashlib
import json
import re
import typing

from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
)
from engine.e3_structural_targets_v1 import (
    E3StructuralTargetsV1,
)
from engine.e3_price_zone_admission_v1 import (
    E3PriceZoneAdmissionV1,
)
from engine.e3_mode_trigger_evidence_v1 import (
    E3ModeTriggerEvidenceV1,
)

__all__ = (
    "E3LifecycleResultV1",
    "build_e3_setup_lifecycle",
)

SCHEMA_VERSION = "e3-setup-lifecycle-v1"
POLICY_VERSION = "e3-deterministic-setup-lifecycle-v1"
STATE_DISCOVERED = "DISCOVERED"
STATE_ARMED = "ARMED"
STATE_ACTIONABLE = "ACTIONABLE"
STATE_INVALIDATED = "INVALIDATED"
DECISION_PASS = "PASS_LIFECYCLE"
DECISION_HOLD = "HOLD_LIFECYCLE"
REASON_DISCOVERED = "PASS_LIFECYCLE_DISCOVERED"
REASON_ARMED_WAITING_PRICE = "PASS_LIFECYCLE_ARMED_WAITING_PRICE"
REASON_ARMED_WAITING_TRIGGER = "PASS_LIFECYCLE_ARMED_WAITING_TRIGGER"
REASON_ACTIONABLE = "PASS_LIFECYCLE_ACTIONABLE"
REASON_ACTIONABLE_STABLE = "PASS_LIFECYCLE_ACTIONABLE_STABLE"
REASON_INVALIDATED_TERMINAL = "PASS_LIFECYCLE_INVALIDATED_TERMINAL"
REASON_INVALIDATED_STRUCTURE = "PASS_LIFECYCLE_INVALIDATED_STRUCTURE"
REASON_INVALIDATED_PRICE_STALE = "PASS_LIFECYCLE_INVALIDATED_PRICE_STALE"
REASON_INVALIDATED_PRICE_SPREAD = "PASS_LIFECYCLE_INVALIDATED_PRICE_SPREAD"
REASON_INVALIDATED_PRICE_SLIPPAGE = "PASS_LIFECYCLE_INVALIDATED_PRICE_SLIPPAGE"
REASON_INVALIDATED_PRICE_LEFT_ZONE = "PASS_LIFECYCLE_INVALIDATED_PRICE_LEFT_ZONE"
REASON_INVALIDATED_TRIGGER_FUTURE = "PASS_LIFECYCLE_INVALIDATED_TRIGGER_FUTURE"
REASON_INVALIDATED_TRIGGER_STALE = "PASS_LIFECYCLE_INVALIDATED_TRIGGER_STALE"
REASON_INVALIDATED_TRIGGER_LOST = "PASS_LIFECYCLE_INVALIDATED_TRIGGER_LOST"
REASON_GEOMETRY_IDENTITY = "HOLD_LIFECYCLE_GEOMETRY_IDENTITY_MISMATCH"
REASON_TARGETS_IDENTITY = "HOLD_LIFECYCLE_TARGETS_IDENTITY_MISMATCH"
REASON_ADMISSION_IDENTITY = "HOLD_LIFECYCLE_PRICE_ADMISSION_IDENTITY_MISMATCH"
REASON_TRIGGER_IDENTITY = "HOLD_LIFECYCLE_TRIGGER_EVIDENCE_IDENTITY_MISMATCH"
REASON_MODE_LINEAGE = "HOLD_LIFECYCLE_MODE_LINEAGE_MISMATCH"
REASON_SYMBOL = "HOLD_LIFECYCLE_SYMBOL_MISMATCH"
REASON_SIDE = "HOLD_LIFECYCLE_SIDE_MISMATCH"
REASON_STRUCTURE_TIMEFRAME = "HOLD_LIFECYCLE_STRUCTURE_TIMEFRAME_MISMATCH"
REASON_STRUCTURE_GENERATION = "HOLD_LIFECYCLE_STRUCTURE_GENERATION_MISMATCH"
REASON_ILLEGAL_TRANSITION = "HOLD_LIFECYCLE_ILLEGAL_TRANSITION"
ERROR = "invalid E3 setup lifecycle"

_PRICE_PASS = "PASS_PRICE_ADMISSION"
_PRICE_STALE = "HOLD_PRICE_STALE"
_PRICE_SPREAD = "HOLD_PRICE_SPREAD"
_PRICE_SLIPPAGE = "HOLD_PRICE_SLIPPAGE"
_PRICE_OUTSIDE = "HOLD_PRICE_OUTSIDE_ZONE"
_TRIGGER_PASS = "PASS_TRIGGER_EVIDENCE"
_TRIGGER_FUTURE = "HOLD_TRIGGER_FUTURE"
_TRIGGER_STALE = "HOLD_TRIGGER_STALE"
_STATES: typing.Final[tuple[str, str, str, str]] = (
    STATE_DISCOVERED,
    STATE_ARMED,
    STATE_ACTIONABLE,
    STATE_INVALIDATED,
)
_SHA256_PATTERN: typing.Final[str] = r"[0-9a-f]{64}"


@dataclasses.dataclass(frozen=True, slots=True)
class E3LifecycleResultV1:
    schema_version: str
    policy_version: str
    previous_state: str
    requested_state: str
    expected_state: str
    resulting_state: str
    geometry: E3GoldenZoneGeometryV1
    structural_targets: E3StructuralTargetsV1
    price_zone_admission: E3PriceZoneAdmissionV1
    mode_trigger_evidence: E3ModeTriggerEvidenceV1
    structure_valid: bool
    geometry_identity_matches: bool
    targets_identity_matches: bool
    admission_identity_matches: bool
    trigger_identity_matches: bool
    mode_lineage_matches: bool
    symbol_matches: bool
    side_matches: bool
    structure_timeframe_matches: bool
    structure_generation_matches: bool
    targets_ready: bool
    price_admission_pass: bool
    trigger_evidence_pass: bool
    transition_legal: bool
    actionable_ready: bool
    decision: str
    reason_code: str
    lifecycle_sha256: str

    def __post_init__(self) -> None:
        try:
            _validate_result(self)
        except Exception:
            raise ValueError(ERROR) from None

    def to_mapping(self) -> dict[str, object]:
        return _result_mapping(self)


def _valid_sha256(value: object) -> bool:
    return type(value) is str and re.fullmatch(_SHA256_PATTERN, value) is not None


def _validate_dependency(value: object, expected_type: type[object]) -> None:
    if type(value) is not expected_type:
        raise ValueError(ERROR)
    value.__post_init__()


def _derive(
    *,
    previous_state: object,
    requested_state: object,
    geometry: object,
    structural_targets: object,
    price_zone_admission: object,
    mode_trigger_evidence: object,
    structure_valid: object,
) -> dict[str, object]:
    if type(previous_state) is not str or previous_state not in _STATES:
        raise ValueError(ERROR)
    if type(requested_state) is not str or requested_state not in _STATES:
        raise ValueError(ERROR)
    if type(structure_valid) is not bool:
        raise ValueError(ERROR)

    _validate_dependency(geometry, E3GoldenZoneGeometryV1)
    _validate_dependency(structural_targets, E3StructuralTargetsV1)
    _validate_dependency(price_zone_admission, E3PriceZoneAdmissionV1)
    _validate_dependency(mode_trigger_evidence, E3ModeTriggerEvidenceV1)

    targets_geometry_identity = structural_targets.geometry is geometry
    admission_geometry_identity = price_zone_admission.geometry is geometry
    snapshot_geometry_identity = price_zone_admission.snapshot.geometry is geometry
    trigger_geometry_identity = mode_trigger_evidence.geometry is geometry

    geometry_identity_matches = (
        targets_geometry_identity
        and admission_geometry_identity
        and snapshot_geometry_identity
        and trigger_geometry_identity
    )
    targets_identity_matches = targets_geometry_identity and _valid_sha256(
        structural_targets.targets_sha256
    )
    admission_identity_matches = (
        admission_geometry_identity
        and snapshot_geometry_identity
        and price_zone_admission.zone_low_tick == geometry.golden_zone_low_tick
        and price_zone_admission.zone_high_tick == geometry.golden_zone_high_tick
    )
    trigger_identity_matches = trigger_geometry_identity
    mode_lineage_matches = (
        mode_trigger_evidence.mode == geometry.mode
        and mode_trigger_evidence.mode_lineage_sha256 == geometry.mode_lineage_sha256
        and mode_trigger_evidence.mode_matches is True
        and mode_trigger_evidence.mode_lineage_matches is True
    )
    symbol_matches = (
        mode_trigger_evidence.canonical_symbol == geometry.canonical_symbol
        and mode_trigger_evidence.symbol_matches is True
    )
    side_matches = (
        mode_trigger_evidence.side == geometry.side
        and mode_trigger_evidence.side_matches is True
    )
    structure_timeframe_matches = (
        mode_trigger_evidence.structure_timeframe == geometry.structure_timeframe
        and mode_trigger_evidence.structure_timeframe_matches is True
    )
    structure_generation_matches = (
        mode_trigger_evidence.structure_generation_id == geometry.structure_generation_id
        and mode_trigger_evidence.structure_generation_matches is True
    )

    targets_ready = (
        targets_geometry_identity
        and structural_targets.tp1_destination_id != structural_targets.tp2_destination_id
        and structural_targets.tp1_tick != structural_targets.tp2_tick
        and _valid_sha256(structural_targets.targets_sha256)
    )
    price_admission_pass = (
        price_zone_admission.decision == _PRICE_PASS
        and price_zone_admission.reason_code == _PRICE_PASS
        and price_zone_admission.age_within_limit is True
        and price_zone_admission.spread_within_limit is True
        and price_zone_admission.slippage_within_limit is True
        and price_zone_admission.inside_zone is True
        and admission_identity_matches
    )
    trigger_evidence_pass = (
        mode_trigger_evidence.decision == _TRIGGER_PASS
        and mode_trigger_evidence.reason_code == _TRIGGER_PASS
        and mode_trigger_evidence.trigger_candle_closed is True
        and mode_trigger_evidence.trigger_rule_satisfied is True
        and mode_trigger_evidence.trigger_close_aligned is True
        and mode_trigger_evidence.trigger_not_future is True
        and mode_trigger_evidence.trigger_fresh is True
        and mode_trigger_evidence.mode_matches is True
        and mode_trigger_evidence.mode_lineage_matches is True
        and mode_trigger_evidence.symbol_matches is True
        and mode_trigger_evidence.side_matches is True
        and mode_trigger_evidence.structure_timeframe_matches is True
        and mode_trigger_evidence.structure_generation_matches is True
        and mode_trigger_evidence.trigger_timeframe_matches is True
        and mode_trigger_evidence.trigger_rule_matches is True
        and trigger_identity_matches
        and mode_lineage_matches
        and symbol_matches
        and side_matches
        and structure_timeframe_matches
        and structure_generation_matches
    )
    actionable_ready = (
        structure_valid is True
        and geometry_identity_matches
        and targets_identity_matches
        and admission_identity_matches
        and trigger_identity_matches
        and mode_lineage_matches
        and symbol_matches
        and side_matches
        and structure_timeframe_matches
        and structure_generation_matches
        and targets_ready
        and price_admission_pass
        and trigger_evidence_pass
    )

    booleans = {
        "geometry_identity_matches": geometry_identity_matches,
        "targets_identity_matches": targets_identity_matches,
        "admission_identity_matches": admission_identity_matches,
        "trigger_identity_matches": trigger_identity_matches,
        "mode_lineage_matches": mode_lineage_matches,
        "symbol_matches": symbol_matches,
        "side_matches": side_matches,
        "structure_timeframe_matches": structure_timeframe_matches,
        "structure_generation_matches": structure_generation_matches,
        "targets_ready": targets_ready,
        "price_admission_pass": price_admission_pass,
        "trigger_evidence_pass": trigger_evidence_pass,
    }

    identity_priority = (
        (geometry_identity_matches, REASON_GEOMETRY_IDENTITY),
        (targets_identity_matches, REASON_TARGETS_IDENTITY),
        (admission_identity_matches, REASON_ADMISSION_IDENTITY),
        (trigger_identity_matches, REASON_TRIGGER_IDENTITY),
        (mode_lineage_matches, REASON_MODE_LINEAGE),
        (symbol_matches, REASON_SYMBOL),
        (side_matches, REASON_SIDE),
        (structure_timeframe_matches, REASON_STRUCTURE_TIMEFRAME),
        (structure_generation_matches, REASON_STRUCTURE_GENERATION),
    )
    for identity_matches, mismatch_reason in identity_priority:
        if not identity_matches:
            return {
                **booleans,
                "expected_state": previous_state,
                "resulting_state": previous_state,
                "transition_legal": False,
                "actionable_ready": False,
                "decision": DECISION_HOLD,
                "reason_code": mismatch_reason,
            }

    if previous_state == STATE_INVALIDATED:
        expected_state = STATE_INVALIDATED
        success_reason = REASON_INVALIDATED_TERMINAL
    elif structure_valid is False:
        expected_state = STATE_INVALIDATED
        success_reason = REASON_INVALIDATED_STRUCTURE
    elif price_zone_admission.reason_code == _PRICE_STALE:
        expected_state = STATE_INVALIDATED
        success_reason = REASON_INVALIDATED_PRICE_STALE
    elif price_zone_admission.reason_code == _PRICE_SPREAD:
        expected_state = STATE_INVALIDATED
        success_reason = REASON_INVALIDATED_PRICE_SPREAD
    elif price_zone_admission.reason_code == _PRICE_SLIPPAGE:
        expected_state = STATE_INVALIDATED
        success_reason = REASON_INVALIDATED_PRICE_SLIPPAGE
    elif mode_trigger_evidence.reason_code == _TRIGGER_FUTURE:
        expected_state = STATE_INVALIDATED
        success_reason = REASON_INVALIDATED_TRIGGER_FUTURE
    elif mode_trigger_evidence.reason_code == _TRIGGER_STALE:
        expected_state = STATE_INVALIDATED
        success_reason = REASON_INVALIDATED_TRIGGER_STALE
    elif previous_state == STATE_DISCOVERED:
        if price_zone_admission.reason_code == _PRICE_OUTSIDE:
            expected_state = STATE_DISCOVERED
            success_reason = REASON_DISCOVERED
        elif price_admission_pass and actionable_ready:
            expected_state = STATE_ACTIONABLE
            success_reason = REASON_ACTIONABLE
        elif price_admission_pass and not trigger_evidence_pass:
            expected_state = STATE_ARMED
            success_reason = REASON_ARMED_WAITING_TRIGGER
        else:
            raise ValueError(ERROR)
    elif previous_state == STATE_ARMED:
        if price_zone_admission.reason_code == _PRICE_OUTSIDE:
            expected_state = STATE_ARMED
            success_reason = REASON_ARMED_WAITING_PRICE
        elif price_admission_pass and actionable_ready:
            expected_state = STATE_ACTIONABLE
            success_reason = REASON_ACTIONABLE
        elif price_admission_pass and not trigger_evidence_pass:
            expected_state = STATE_ARMED
            success_reason = REASON_ARMED_WAITING_TRIGGER
        else:
            raise ValueError(ERROR)
    elif previous_state == STATE_ACTIONABLE:
        if actionable_ready:
            expected_state = STATE_ACTIONABLE
            success_reason = REASON_ACTIONABLE_STABLE
        elif price_zone_admission.reason_code == _PRICE_OUTSIDE:
            expected_state = STATE_INVALIDATED
            success_reason = REASON_INVALIDATED_PRICE_LEFT_ZONE
        elif price_admission_pass and not trigger_evidence_pass:
            expected_state = STATE_INVALIDATED
            success_reason = REASON_INVALIDATED_TRIGGER_LOST
        else:
            raise ValueError(ERROR)
    else:
        raise ValueError(ERROR)

    transition_legal = requested_state == expected_state
    if transition_legal:
        resulting_state = expected_state
        decision = DECISION_PASS
        reason_code = success_reason
    else:
        resulting_state = (
            STATE_INVALIDATED if expected_state == STATE_INVALIDATED else previous_state
        )
        decision = DECISION_HOLD
        reason_code = REASON_ILLEGAL_TRANSITION

    return {
        **booleans,
        "expected_state": expected_state,
        "resulting_state": resulting_state,
        "transition_legal": transition_legal,
        "actionable_ready": actionable_ready,
        "decision": decision,
        "reason_code": reason_code,
    }


def _data_from_result(result: E3LifecycleResultV1) -> dict[str, object]:
    return {
        field.name: getattr(result, field.name)
        for field in dataclasses.fields(E3LifecycleResultV1)
    }


def _mapping_from_data(data: dict[str, object], include_hash: bool) -> dict[str, object]:
    mapping: dict[str, object] = {
        "schema_version": data["schema_version"],
        "policy_version": data["policy_version"],
        "previous_state": data["previous_state"],
        "requested_state": data["requested_state"],
        "expected_state": data["expected_state"],
        "resulting_state": data["resulting_state"],
        "geometry": data["geometry"].to_mapping(),
        "structural_targets": data["structural_targets"].to_mapping(),
        "price_zone_admission": data["price_zone_admission"].to_mapping(),
        "mode_trigger_evidence": data["mode_trigger_evidence"].to_mapping(),
        "structure_valid": data["structure_valid"],
        "geometry_identity_matches": data["geometry_identity_matches"],
        "targets_identity_matches": data["targets_identity_matches"],
        "admission_identity_matches": data["admission_identity_matches"],
        "trigger_identity_matches": data["trigger_identity_matches"],
        "mode_lineage_matches": data["mode_lineage_matches"],
        "symbol_matches": data["symbol_matches"],
        "side_matches": data["side_matches"],
        "structure_timeframe_matches": data["structure_timeframe_matches"],
        "structure_generation_matches": data["structure_generation_matches"],
        "targets_ready": data["targets_ready"],
        "price_admission_pass": data["price_admission_pass"],
        "trigger_evidence_pass": data["trigger_evidence_pass"],
        "transition_legal": data["transition_legal"],
        "actionable_ready": data["actionable_ready"],
        "decision": data["decision"],
        "reason_code": data["reason_code"],
    }
    if include_hash:
        mapping["lifecycle_sha256"] = data["lifecycle_sha256"]
    return mapping


def _hash_data(data: dict[str, object]) -> str:
    payload = json.dumps(
        _mapping_from_data(data, False),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _result_mapping(result: E3LifecycleResultV1) -> dict[str, object]:
    return _mapping_from_data(_data_from_result(result), True)


def _validate_result(result: E3LifecycleResultV1) -> None:
    string_fields = (
        "schema_version",
        "policy_version",
        "previous_state",
        "requested_state",
        "expected_state",
        "resulting_state",
        "decision",
        "reason_code",
        "lifecycle_sha256",
    )
    boolean_fields = (
        "structure_valid",
        "geometry_identity_matches",
        "targets_identity_matches",
        "admission_identity_matches",
        "trigger_identity_matches",
        "mode_lineage_matches",
        "symbol_matches",
        "side_matches",
        "structure_timeframe_matches",
        "structure_generation_matches",
        "targets_ready",
        "price_admission_pass",
        "trigger_evidence_pass",
        "transition_legal",
        "actionable_ready",
    )
    for name in string_fields:
        if type(getattr(result, name)) is not str:
            raise ValueError(ERROR)
    for name in boolean_fields:
        if type(getattr(result, name)) is not bool:
            raise ValueError(ERROR)
    if result.schema_version != SCHEMA_VERSION or result.policy_version != POLICY_VERSION:
        raise ValueError(ERROR)
    if not _valid_sha256(result.lifecycle_sha256):
        raise ValueError(ERROR)

    derived = _derive(
        previous_state=result.previous_state,
        requested_state=result.requested_state,
        geometry=result.geometry,
        structural_targets=result.structural_targets,
        price_zone_admission=result.price_zone_admission,
        mode_trigger_evidence=result.mode_trigger_evidence,
        structure_valid=result.structure_valid,
    )
    for name, expected in derived.items():
        actual = getattr(result, name)
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError(ERROR)
    if _hash_data(_data_from_result(result)) != result.lifecycle_sha256:
        raise ValueError(ERROR)


def build_e3_setup_lifecycle(
    *,
    previous_state,
    requested_state,
    geometry,
    structural_targets,
    price_zone_admission,
    mode_trigger_evidence,
    structure_valid,
) -> E3LifecycleResultV1:
    try:
        derived = _derive(
            previous_state=previous_state,
            requested_state=requested_state,
            geometry=geometry,
            structural_targets=structural_targets,
            price_zone_admission=price_zone_admission,
            mode_trigger_evidence=mode_trigger_evidence,
            structure_valid=structure_valid,
        )
        data: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "previous_state": previous_state,
            "requested_state": requested_state,
            "expected_state": derived["expected_state"],
            "resulting_state": derived["resulting_state"],
            "geometry": geometry,
            "structural_targets": structural_targets,
            "price_zone_admission": price_zone_admission,
            "mode_trigger_evidence": mode_trigger_evidence,
            "structure_valid": structure_valid,
            "geometry_identity_matches": derived["geometry_identity_matches"],
            "targets_identity_matches": derived["targets_identity_matches"],
            "admission_identity_matches": derived["admission_identity_matches"],
            "trigger_identity_matches": derived["trigger_identity_matches"],
            "mode_lineage_matches": derived["mode_lineage_matches"],
            "symbol_matches": derived["symbol_matches"],
            "side_matches": derived["side_matches"],
            "structure_timeframe_matches": derived["structure_timeframe_matches"],
            "structure_generation_matches": derived["structure_generation_matches"],
            "targets_ready": derived["targets_ready"],
            "price_admission_pass": derived["price_admission_pass"],
            "trigger_evidence_pass": derived["trigger_evidence_pass"],
            "transition_legal": derived["transition_legal"],
            "actionable_ready": derived["actionable_ready"],
            "decision": derived["decision"],
            "reason_code": derived["reason_code"],
        }
        data["lifecycle_sha256"] = _hash_data(data)
        return E3LifecycleResultV1(**data)
    except Exception:
        raise ValueError(ERROR) from None
