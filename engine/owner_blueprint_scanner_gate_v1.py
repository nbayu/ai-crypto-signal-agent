"""Read-only per-style capacity and global active-pair scanner gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from engine import active_signal_ledger_v1 as active
from engine.canonical_pair_v1 import normalize_pair


STYLE_CAPACITY_FULL = "STYLE_CAPACITY_FULL"
GLOBAL_PAIR_ACTIVE = "GLOBAL_PAIR_ACTIVE"
ELIGIBLE = "ELIGIBLE"


@dataclass(frozen=True, slots=True)
class OwnerBlueprintScannerGateDecisionV1:
    eligible: bool
    reason: str
    style: str
    canonical_pair: str
    available_slots: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def style_availability(ledger: Mapping[str, Any]) -> dict[str, int]:
    """Return independently derived available slots for all three styles."""
    return active.inspect_capacity(ledger)["remaining_by_mode"]


def active_canonical_pairs(ledger: Mapping[str, Any]) -> frozenset[str]:
    document = active.validate_ledger(ledger)
    return frozenset(
        normalize_pair(record["symbol"])
        for record in document["signals"].values()
        if record["state"] == active.ENTRY_ACTIVE
    )


def evaluate_candidate(
    ledger: Mapping[str, Any], *, style: str, pair: str,
) -> OwnerBlueprintScannerGateDecisionV1:
    """Suppress full-style or globally active-pair candidates before publication."""
    if style not in active.STYLES:
        raise ValueError(active.STYLE_INVALID)
    canonical = normalize_pair(pair)
    available = style_availability(ledger)[style]
    if available == 0:
        return OwnerBlueprintScannerGateDecisionV1(
            False, STYLE_CAPACITY_FULL, style, canonical, available,
        )
    if canonical in active_canonical_pairs(ledger):
        return OwnerBlueprintScannerGateDecisionV1(
            False, GLOBAL_PAIR_ACTIVE, style, canonical, available,
        )
    return OwnerBlueprintScannerGateDecisionV1(
        True, ELIGIBLE, style, canonical, available,
    )
