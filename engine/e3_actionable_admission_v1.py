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
from engine.e3_executable_price_snapshot_v1 import (
    E3ExecutablePriceSnapshotV1,
)
from engine.e3_price_zone_admission_v1 import (
    E3PriceZoneAdmissionV1,
)
from engine.e3_mode_trigger_evidence_v1 import (
    E3ModeTriggerEvidenceV1,
)
from engine.e3_setup_lifecycle_v1 import (
    E3LifecycleResultV1,
)

__all__ = (
    "E3ActionableAdmissionResultV1",
    "build_e3_actionable_admission",
)

SCHEMA_VERSION = "e3-actionable-admission-v1"
POLICY_VERSION = "e3-detached-actionable-admission-v1"
DECISION_PASS = "PASS_ACTIONABLE_ADMISSION"
DECISION_HOLD = "HOLD_ACTIONABLE_ADMISSION"
REASON_PASS = "PASS_ACTIONABLE_ADMISSION"
REASON_GEOMETRY_IDENTITY = "HOLD_ACTIONABLE_GEOMETRY_IDENTITY_MISMATCH"
REASON_TARGETS_IDENTITY = "HOLD_ACTIONABLE_TARGETS_IDENTITY_MISMATCH"
REASON_SNAPSHOT_IDENTITY = "HOLD_ACTIONABLE_SNAPSHOT_IDENTITY_MISMATCH"
REASON_ADMISSION_IDENTITY = "HOLD_ACTIONABLE_PRICE_ADMISSION_IDENTITY_MISMATCH"
REASON_TRIGGER_IDENTITY = "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_IDENTITY_MISMATCH"
REASON_LIFECYCLE_IDENTITY = "HOLD_ACTIONABLE_LIFECYCLE_IDENTITY_MISMATCH"
REASON_MODE_LINEAGE = "HOLD_ACTIONABLE_MODE_LINEAGE_MISMATCH"
REASON_SYMBOL = "HOLD_ACTIONABLE_SYMBOL_MISMATCH"
REASON_SIDE = "HOLD_ACTIONABLE_SIDE_MISMATCH"
REASON_STRUCTURE_TIMEFRAME = "HOLD_ACTIONABLE_STRUCTURE_TIMEFRAME_MISMATCH"
REASON_STRUCTURE_GENERATION = "HOLD_ACTIONABLE_STRUCTURE_GENERATION_MISMATCH"
REASON_TARGETS_NOT_READY = "HOLD_ACTIONABLE_TARGETS_NOT_READY"
REASON_PRICE_OUTSIDE_ZONE = "HOLD_ACTIONABLE_PRICE_OUTSIDE_ZONE"
REASON_PRICE_STALE = "HOLD_ACTIONABLE_PRICE_STALE"
REASON_PRICE_SPREAD = "HOLD_ACTIONABLE_PRICE_SPREAD"
REASON_PRICE_SLIPPAGE = "HOLD_ACTIONABLE_PRICE_SLIPPAGE"
REASON_PRICE_NOT_PASS = "HOLD_ACTIONABLE_PRICE_ADMISSION_NOT_PASS"
REASON_TRIGGER_FUTURE = "HOLD_ACTIONABLE_TRIGGER_FUTURE"
REASON_TRIGGER_STALE = "HOLD_ACTIONABLE_TRIGGER_STALE"
REASON_TRIGGER_NOT_PASS = "HOLD_ACTIONABLE_TRIGGER_EVIDENCE_NOT_PASS"
REASON_STRUCTURE_INVALIDATED = "HOLD_ACTIONABLE_STRUCTURE_INVALIDATED"
REASON_PRICE_LEFT_ZONE = "HOLD_ACTIONABLE_PRICE_LEFT_ZONE"
REASON_TRIGGER_LOST = "HOLD_ACTIONABLE_TRIGGER_LOST"
REASON_LIFECYCLE_IDENTITY_HOLD = "HOLD_ACTIONABLE_LIFECYCLE_IDENTITY_HOLD"
REASON_ILLEGAL_TRANSITION = "HOLD_ACTIONABLE_ILLEGAL_TRANSITION"
REASON_LIFECYCLE_NOT_ACTIONABLE = "HOLD_ACTIONABLE_LIFECYCLE_NOT_ACTIONABLE"
ERROR = "invalid E3 actionable admission"

_PRICE_PASS = "PASS_PRICE_ADMISSION"
_PRICE_OUTSIDE = "HOLD_PRICE_OUTSIDE_ZONE"
_PRICE_STALE = "HOLD_PRICE_STALE"
_PRICE_SPREAD = "HOLD_PRICE_SPREAD"
_PRICE_SLIPPAGE = "HOLD_PRICE_SLIPPAGE"
_TRIGGER_PASS = "PASS_TRIGGER_EVIDENCE"
_TRIGGER_FUTURE = "HOLD_TRIGGER_FUTURE"
_TRIGGER_STALE = "HOLD_TRIGGER_STALE"
_LIFECYCLE_PASS = "PASS_LIFECYCLE"
_LIFECYCLE_HOLD = "HOLD_LIFECYCLE"
_LIFECYCLE_ACTIONABLE = "PASS_LIFECYCLE_ACTIONABLE"
_LIFECYCLE_ACTIONABLE_STABLE = "PASS_LIFECYCLE_ACTIONABLE_STABLE"
_LIFECYCLE_INVALIDATED_STRUCTURE = "PASS_LIFECYCLE_INVALIDATED_STRUCTURE"
_LIFECYCLE_PRICE_LEFT_ZONE = "PASS_LIFECYCLE_INVALIDATED_PRICE_LEFT_ZONE"
_LIFECYCLE_TRIGGER_LOST = "PASS_LIFECYCLE_INVALIDATED_TRIGGER_LOST"
_LIFECYCLE_ILLEGAL = "HOLD_LIFECYCLE_ILLEGAL_TRANSITION"
_STATE_ACTIONABLE = "ACTIONABLE"
_SHA256_PATTERN: typing.Final[str] = r"[0-9a-f]{64}"
_COMPOSITION_PATTERN: typing.Final[str] = r"adm-[0-9a-f]{64}"


@dataclasses.dataclass(frozen=True, slots=True)
class E3ActionableAdmissionResultV1:
    schema_version: str
    policy_version: str
    geometry: E3GoldenZoneGeometryV1
    structural_targets: E3StructuralTargetsV1
    executable_price_snapshot: E3ExecutablePriceSnapshotV1
    price_zone_admission: E3PriceZoneAdmissionV1
    mode_trigger_evidence: E3ModeTriggerEvidenceV1
    setup_lifecycle: E3LifecycleResultV1
    geometry_identity_matches: bool
    targets_identity_matches: bool
    snapshot_identity_matches: bool
    admission_identity_matches: bool
    trigger_identity_matches: bool
    lifecycle_identity_matches: bool
    mode_lineage_matches: bool
    symbol_matches: bool
    side_matches: bool
    structure_timeframe_matches: bool
    structure_generation_matches: bool
    structure_valid: bool
    targets_ready: bool
    price_admission_pass: bool
    trigger_evidence_pass: bool
    lifecycle_actionable_pass: bool
    actionable_admitted: bool
    decision: str
    reason_code: str
    composition_id: str
    actionable_admission_sha256: str

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


def _canonical_sha256(mapping: dict[str, object]) -> str:
    payload = json.dumps(
        mapping,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _composition_id(
    geometry: E3GoldenZoneGeometryV1,
    structural_targets: E3StructuralTargetsV1,
    executable_price_snapshot: E3ExecutablePriceSnapshotV1,
    price_zone_admission: E3PriceZoneAdmissionV1,
    mode_trigger_evidence: E3ModeTriggerEvidenceV1,
    setup_lifecycle: E3LifecycleResultV1,
) -> str:
    identity_mapping: dict[str, object] = {
        "policy_version": POLICY_VERSION,
        "geometry_sha256": geometry.geometry_sha256,
        "targets_sha256": structural_targets.targets_sha256,
        "snapshot_sha256": executable_price_snapshot.snapshot_sha256,
        "admission_sha256": price_zone_admission.admission_sha256,
        "trigger_generation_id": mode_trigger_evidence.trigger_generation_id,
        "trigger_evidence_sha256": mode_trigger_evidence.trigger_evidence_sha256,
        "lifecycle_sha256": setup_lifecycle.lifecycle_sha256,
        "mode": geometry.mode,
        "mode_lineage_sha256": geometry.mode_lineage_sha256,
        "canonical_symbol": geometry.canonical_symbol,
        "side": geometry.side,
        "structure_timeframe": geometry.structure_timeframe,
        "structure_generation_id": geometry.structure_generation_id,
    }
    return "adm-" + _canonical_sha256(identity_mapping)


def _derive(
    *,
    geometry: object,
    structural_targets: object,
    executable_price_snapshot: object,
    price_zone_admission: object,
    mode_trigger_evidence: object,
    setup_lifecycle: object,
) -> dict[str, object]:
    _validate_dependency(geometry, E3GoldenZoneGeometryV1)
    _validate_dependency(structural_targets, E3StructuralTargetsV1)
    _validate_dependency(executable_price_snapshot, E3ExecutablePriceSnapshotV1)
    _validate_dependency(price_zone_admission, E3PriceZoneAdmissionV1)
    _validate_dependency(mode_trigger_evidence, E3ModeTriggerEvidenceV1)
    _validate_dependency(setup_lifecycle, E3LifecycleResultV1)

    targets_geometry_identity = structural_targets.geometry is geometry
    snapshot_geometry_identity = executable_price_snapshot.geometry is geometry
    admission_geometry_identity = price_zone_admission.geometry is geometry
    admission_snapshot_geometry_identity = price_zone_admission.snapshot.geometry is geometry
    trigger_geometry_identity = mode_trigger_evidence.geometry is geometry
    lifecycle_geometry_identity = setup_lifecycle.geometry is geometry

    geometry_identity_matches = (
        targets_geometry_identity
        and snapshot_geometry_identity
        and admission_geometry_identity
        and admission_snapshot_geometry_identity
        and trigger_geometry_identity
        and lifecycle_geometry_identity
    )
    targets_identity_matches = (
        targets_geometry_identity
        and setup_lifecycle.structural_targets is structural_targets
        and setup_lifecycle.targets_identity_matches is True
    )
    snapshot_identity_matches = (
        snapshot_geometry_identity
        and price_zone_admission.snapshot is executable_price_snapshot
        and admission_snapshot_geometry_identity
    )
    admission_identity_matches = (
        admission_geometry_identity
        and price_zone_admission.snapshot is executable_price_snapshot
        and setup_lifecycle.price_zone_admission is price_zone_admission
        and setup_lifecycle.admission_identity_matches is True
    )
    trigger_identity_matches = (
        trigger_geometry_identity
        and setup_lifecycle.mode_trigger_evidence is mode_trigger_evidence
        and setup_lifecycle.trigger_identity_matches is True
    )
    lifecycle_identity_matches = (
        lifecycle_geometry_identity
        and setup_lifecycle.structural_targets is structural_targets
        and setup_lifecycle.price_zone_admission is price_zone_admission
        and setup_lifecycle.mode_trigger_evidence is mode_trigger_evidence
    )
    mode_lineage_matches = (
        mode_trigger_evidence.mode == geometry.mode
        and mode_trigger_evidence.mode_lineage_sha256 == geometry.mode_lineage_sha256
        and mode_trigger_evidence.mode_matches is True
        and mode_trigger_evidence.mode_lineage_matches is True
        and setup_lifecycle.mode_lineage_matches is True
    )
    symbol_matches = (
        mode_trigger_evidence.canonical_symbol == geometry.canonical_symbol
        and mode_trigger_evidence.symbol_matches is True
        and setup_lifecycle.symbol_matches is True
    )
    side_matches = (
        mode_trigger_evidence.side == geometry.side
        and mode_trigger_evidence.side_matches is True
        and setup_lifecycle.side_matches is True
    )
    structure_timeframe_matches = (
        mode_trigger_evidence.structure_timeframe == geometry.structure_timeframe
        and mode_trigger_evidence.structure_timeframe_matches is True
        and setup_lifecycle.structure_timeframe_matches is True
    )
    structure_generation_matches = (
        mode_trigger_evidence.structure_generation_id == geometry.structure_generation_id
        and mode_trigger_evidence.structure_generation_matches is True
        and setup_lifecycle.structure_generation_matches is True
    )
    structure_valid = setup_lifecycle.structure_valid
    targets_ready = (
        targets_identity_matches
        and setup_lifecycle.targets_ready is True
        and structural_targets.tp1_destination_id != structural_targets.tp2_destination_id
        and structural_targets.tp1_tick != structural_targets.tp2_tick
    )
    price_admission_pass = (
        admission_identity_matches
        and snapshot_identity_matches
        and price_zone_admission.decision == _PRICE_PASS
        and price_zone_admission.reason_code == _PRICE_PASS
        and price_zone_admission.age_within_limit is True
        and price_zone_admission.spread_within_limit is True
        and price_zone_admission.slippage_within_limit is True
        and price_zone_admission.inside_zone is True
        and setup_lifecycle.price_admission_pass is True
    )
    trigger_evidence_pass = (
        trigger_identity_matches
        and mode_lineage_matches
        and symbol_matches
        and side_matches
        and structure_timeframe_matches
        and structure_generation_matches
        and mode_trigger_evidence.decision == _TRIGGER_PASS
        and mode_trigger_evidence.reason_code == _TRIGGER_PASS
        and mode_trigger_evidence.trigger_candle_closed is True
        and mode_trigger_evidence.trigger_rule_satisfied is True
        and mode_trigger_evidence.trigger_close_aligned is True
        and mode_trigger_evidence.trigger_not_future is True
        and mode_trigger_evidence.trigger_fresh is True
        and mode_trigger_evidence.trigger_timeframe_matches is True
        and mode_trigger_evidence.trigger_rule_matches is True
        and setup_lifecycle.trigger_evidence_pass is True
    )
    lifecycle_actionable_pass = (
        lifecycle_identity_matches
        and setup_lifecycle.structure_valid is True
        and setup_lifecycle.geometry_identity_matches is True
        and setup_lifecycle.targets_identity_matches is True
        and setup_lifecycle.admission_identity_matches is True
        and setup_lifecycle.trigger_identity_matches is True
        and setup_lifecycle.mode_lineage_matches is True
        and setup_lifecycle.symbol_matches is True
        and setup_lifecycle.side_matches is True
        and setup_lifecycle.structure_timeframe_matches is True
        and setup_lifecycle.structure_generation_matches is True
        and setup_lifecycle.targets_ready is True
        and setup_lifecycle.price_admission_pass is True
        and setup_lifecycle.trigger_evidence_pass is True
        and setup_lifecycle.transition_legal is True
        and setup_lifecycle.actionable_ready is True
        and setup_lifecycle.expected_state == _STATE_ACTIONABLE
        and setup_lifecycle.resulting_state == _STATE_ACTIONABLE
        and setup_lifecycle.decision == _LIFECYCLE_PASS
        and setup_lifecycle.reason_code in (
            _LIFECYCLE_ACTIONABLE,
            _LIFECYCLE_ACTIONABLE_STABLE,
        )
    )
    actionable_admitted = (
        geometry_identity_matches
        and targets_identity_matches
        and snapshot_identity_matches
        and admission_identity_matches
        and trigger_identity_matches
        and lifecycle_identity_matches
        and mode_lineage_matches
        and symbol_matches
        and side_matches
        and structure_timeframe_matches
        and structure_generation_matches
        and structure_valid
        and targets_ready
        and price_admission_pass
        and trigger_evidence_pass
        and lifecycle_actionable_pass
    )

    booleans = {
        "geometry_identity_matches": geometry_identity_matches,
        "targets_identity_matches": targets_identity_matches,
        "snapshot_identity_matches": snapshot_identity_matches,
        "admission_identity_matches": admission_identity_matches,
        "trigger_identity_matches": trigger_identity_matches,
        "lifecycle_identity_matches": lifecycle_identity_matches,
        "mode_lineage_matches": mode_lineage_matches,
        "symbol_matches": symbol_matches,
        "side_matches": side_matches,
        "structure_timeframe_matches": structure_timeframe_matches,
        "structure_generation_matches": structure_generation_matches,
        "structure_valid": structure_valid,
        "targets_ready": targets_ready,
        "price_admission_pass": price_admission_pass,
        "trigger_evidence_pass": trigger_evidence_pass,
        "lifecycle_actionable_pass": lifecycle_actionable_pass,
        "actionable_admitted": actionable_admitted,
    }

    identity_priority = (
        (geometry_identity_matches, REASON_GEOMETRY_IDENTITY),
        (targets_identity_matches, REASON_TARGETS_IDENTITY),
        (snapshot_identity_matches, REASON_SNAPSHOT_IDENTITY),
        (admission_identity_matches, REASON_ADMISSION_IDENTITY),
        (trigger_identity_matches, REASON_TRIGGER_IDENTITY),
        (lifecycle_identity_matches, REASON_LIFECYCLE_IDENTITY),
        (mode_lineage_matches, REASON_MODE_LINEAGE),
        (symbol_matches, REASON_SYMBOL),
        (side_matches, REASON_SIDE),
        (structure_timeframe_matches, REASON_STRUCTURE_TIMEFRAME),
        (structure_generation_matches, REASON_STRUCTURE_GENERATION),
        (targets_ready, REASON_TARGETS_NOT_READY),
    )
    reason_code = REASON_PASS
    for condition, failure_reason in identity_priority:
        if not condition:
            reason_code = failure_reason
            break
    else:
        if price_zone_admission.reason_code == _PRICE_OUTSIDE:
            reason_code = REASON_PRICE_OUTSIDE_ZONE
        elif price_zone_admission.reason_code == _PRICE_STALE:
            reason_code = REASON_PRICE_STALE
        elif price_zone_admission.reason_code == _PRICE_SPREAD:
            reason_code = REASON_PRICE_SPREAD
        elif price_zone_admission.reason_code == _PRICE_SLIPPAGE:
            reason_code = REASON_PRICE_SLIPPAGE
        elif (
            price_zone_admission.decision != _PRICE_PASS
            or price_zone_admission.reason_code != _PRICE_PASS
            or price_zone_admission.age_within_limit is not True
            or price_zone_admission.spread_within_limit is not True
            or price_zone_admission.slippage_within_limit is not True
            or price_zone_admission.inside_zone is not True
        ):
            reason_code = REASON_PRICE_NOT_PASS
        elif mode_trigger_evidence.reason_code == _TRIGGER_FUTURE:
            reason_code = REASON_TRIGGER_FUTURE
        elif mode_trigger_evidence.reason_code == _TRIGGER_STALE:
            reason_code = REASON_TRIGGER_STALE
        elif (
            mode_trigger_evidence.decision != _TRIGGER_PASS
            or mode_trigger_evidence.reason_code != _TRIGGER_PASS
            or mode_trigger_evidence.trigger_candle_closed is not True
            or mode_trigger_evidence.trigger_rule_satisfied is not True
            or mode_trigger_evidence.trigger_close_aligned is not True
            or mode_trigger_evidence.trigger_not_future is not True
            or mode_trigger_evidence.trigger_fresh is not True
            or mode_trigger_evidence.trigger_timeframe_matches is not True
            or mode_trigger_evidence.trigger_rule_matches is not True
        ):
            reason_code = REASON_TRIGGER_NOT_PASS
        elif (
            setup_lifecycle.structure_valid is False
            or setup_lifecycle.reason_code == _LIFECYCLE_INVALIDATED_STRUCTURE
        ):
            reason_code = REASON_STRUCTURE_INVALIDATED
        elif setup_lifecycle.reason_code == _LIFECYCLE_PRICE_LEFT_ZONE:
            reason_code = REASON_PRICE_LEFT_ZONE
        elif setup_lifecycle.reason_code == _LIFECYCLE_TRIGGER_LOST:
            reason_code = REASON_TRIGGER_LOST
        elif (
            setup_lifecycle.decision == _LIFECYCLE_HOLD
            and setup_lifecycle.reason_code.startswith("HOLD_LIFECYCLE_")
            and setup_lifecycle.reason_code != _LIFECYCLE_ILLEGAL
        ):
            reason_code = REASON_LIFECYCLE_IDENTITY_HOLD
        elif setup_lifecycle.reason_code == _LIFECYCLE_ILLEGAL:
            reason_code = REASON_ILLEGAL_TRANSITION
        elif not lifecycle_actionable_pass:
            reason_code = REASON_LIFECYCLE_NOT_ACTIONABLE
        elif not actionable_admitted:
            raise ValueError(ERROR)

    decision = DECISION_PASS if actionable_admitted else DECISION_HOLD
    if actionable_admitted and reason_code != REASON_PASS:
        raise ValueError(ERROR)
    return {
        **booleans,
        "decision": decision,
        "reason_code": reason_code,
        "composition_id": _composition_id(
            geometry,
            structural_targets,
            executable_price_snapshot,
            price_zone_admission,
            mode_trigger_evidence,
            setup_lifecycle,
        ),
    }


def _data_from_result(result: E3ActionableAdmissionResultV1) -> dict[str, object]:
    return {
        field.name: getattr(result, field.name)
        for field in dataclasses.fields(E3ActionableAdmissionResultV1)
    }


def _mapping_from_data(data: dict[str, object], include_hash: bool) -> dict[str, object]:
    mapping: dict[str, object] = {
        "schema_version": data["schema_version"],
        "policy_version": data["policy_version"],
        "geometry": data["geometry"].to_mapping(),
        "structural_targets": data["structural_targets"].to_mapping(),
        "executable_price_snapshot": data["executable_price_snapshot"].to_mapping(),
        "price_zone_admission": data["price_zone_admission"].to_mapping(),
        "mode_trigger_evidence": data["mode_trigger_evidence"].to_mapping(),
        "setup_lifecycle": data["setup_lifecycle"].to_mapping(),
        "geometry_identity_matches": data["geometry_identity_matches"],
        "targets_identity_matches": data["targets_identity_matches"],
        "snapshot_identity_matches": data["snapshot_identity_matches"],
        "admission_identity_matches": data["admission_identity_matches"],
        "trigger_identity_matches": data["trigger_identity_matches"],
        "lifecycle_identity_matches": data["lifecycle_identity_matches"],
        "mode_lineage_matches": data["mode_lineage_matches"],
        "symbol_matches": data["symbol_matches"],
        "side_matches": data["side_matches"],
        "structure_timeframe_matches": data["structure_timeframe_matches"],
        "structure_generation_matches": data["structure_generation_matches"],
        "structure_valid": data["structure_valid"],
        "targets_ready": data["targets_ready"],
        "price_admission_pass": data["price_admission_pass"],
        "trigger_evidence_pass": data["trigger_evidence_pass"],
        "lifecycle_actionable_pass": data["lifecycle_actionable_pass"],
        "actionable_admitted": data["actionable_admitted"],
        "decision": data["decision"],
        "reason_code": data["reason_code"],
        "composition_id": data["composition_id"],
    }
    if include_hash:
        mapping["actionable_admission_sha256"] = data["actionable_admission_sha256"]
    return mapping


def _hash_data(data: dict[str, object]) -> str:
    return _canonical_sha256(_mapping_from_data(data, False))


def _result_mapping(result: E3ActionableAdmissionResultV1) -> dict[str, object]:
    return _mapping_from_data(_data_from_result(result), True)


def _validate_result(result: E3ActionableAdmissionResultV1) -> None:
    string_fields = (
        "schema_version",
        "policy_version",
        "decision",
        "reason_code",
        "composition_id",
        "actionable_admission_sha256",
    )
    boolean_fields = (
        "geometry_identity_matches",
        "targets_identity_matches",
        "snapshot_identity_matches",
        "admission_identity_matches",
        "trigger_identity_matches",
        "lifecycle_identity_matches",
        "mode_lineage_matches",
        "symbol_matches",
        "side_matches",
        "structure_timeframe_matches",
        "structure_generation_matches",
        "structure_valid",
        "targets_ready",
        "price_admission_pass",
        "trigger_evidence_pass",
        "lifecycle_actionable_pass",
        "actionable_admitted",
    )
    for name in string_fields:
        if type(getattr(result, name)) is not str:
            raise ValueError(ERROR)
    for name in boolean_fields:
        if type(getattr(result, name)) is not bool:
            raise ValueError(ERROR)
    if result.schema_version != SCHEMA_VERSION or result.policy_version != POLICY_VERSION:
        raise ValueError(ERROR)
    if re.fullmatch(_COMPOSITION_PATTERN, result.composition_id) is None:
        raise ValueError(ERROR)
    if not _valid_sha256(result.actionable_admission_sha256):
        raise ValueError(ERROR)
    derived = _derive(
        geometry=result.geometry,
        structural_targets=result.structural_targets,
        executable_price_snapshot=result.executable_price_snapshot,
        price_zone_admission=result.price_zone_admission,
        mode_trigger_evidence=result.mode_trigger_evidence,
        setup_lifecycle=result.setup_lifecycle,
    )
    for name, expected in derived.items():
        actual = getattr(result, name)
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError(ERROR)
    if _hash_data(_data_from_result(result)) != result.actionable_admission_sha256:
        raise ValueError(ERROR)


def build_e3_actionable_admission(
    *,
    geometry,
    structural_targets,
    executable_price_snapshot,
    price_zone_admission,
    mode_trigger_evidence,
    setup_lifecycle,
) -> E3ActionableAdmissionResultV1:
    try:
        derived = _derive(
            geometry=geometry,
            structural_targets=structural_targets,
            executable_price_snapshot=executable_price_snapshot,
            price_zone_admission=price_zone_admission,
            mode_trigger_evidence=mode_trigger_evidence,
            setup_lifecycle=setup_lifecycle,
        )
        data: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "geometry": geometry,
            "structural_targets": structural_targets,
            "executable_price_snapshot": executable_price_snapshot,
            "price_zone_admission": price_zone_admission,
            "mode_trigger_evidence": mode_trigger_evidence,
            "setup_lifecycle": setup_lifecycle,
            **derived,
        }
        data["actionable_admission_sha256"] = _hash_data(data)
        return E3ActionableAdmissionResultV1(**data)
    except Exception:
        raise ValueError(ERROR) from None
