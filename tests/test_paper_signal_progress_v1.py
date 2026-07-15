import copy
import math

import pytest

from engine.paper_signal_contract_v1 import PaperSignalContractError
from engine.paper_signal_progress_v1 import (
    PAPER_SIGNAL_PROGRESS_SCHEMA_NAME,
    PAPER_SIGNAL_PROGRESS_SCHEMA_VERSION,
    build_evaluation_cycle,
    build_paper_signal_progress,
)


MODE_ORDER = ["SWING", "INTRADAY", "SCALP"]


def source_publication(
    *,
    signal_id="SCP-20260715-001",
    delivery_id="delivery-001",
    mode="SCALP",
    source_hash=None,
    classification="PAPER_SIGNAL",
):
    return {
        "signal_id": signal_id,
        "delivery_id": delivery_id,
        "mode": mode,
        "published_at": "2026-07-15T12:00:00Z",
        "source_payload_hash": source_hash or ("a" * 64),
        "classification": classification,
    }


def evaluation_cycle(
    *,
    source_evaluation_id="eval-001",
    mode="SCALP",
    evaluated_at="2026-07-15T12:00:00Z",
    signal_ids=None,
    rejection_reasons=None,
):
    return {
        "schema_version": 1,
        "source_evaluation_id": source_evaluation_id,
        "mode": mode,
        "evaluated_at": evaluated_at,
        "official_alert_signal_ids": signal_ids or [],
        "rejection_reasons": rejection_reasons or {},
    }


def observation(
    *,
    signal_id="SCP-20260715-001",
    mode="SCALP",
    state="ENTRY_ZONE_TOUCHED",
    acknowledgment=None,
):
    return {
        "signal_id": signal_id,
        "mode": mode,
        "observation_state": state,
        "acknowledgment": acknowledgment,
        "classification": "PAPER_SIGNAL",
    }


def acknowledgment(latency_ms=1250):
    return {
        "signal_id": "SCP-20260715-001",
        "delivery_id": "delivery-001",
        "event_id": "ack-001",
        "event_type": "ENTRY_REPORTED",
        "published_at": "2026-07-15T12:00:00Z",
        "acknowledged_at": "2026-07-15T12:00:01.250Z",
        "acknowledgment_latency_ms": latency_ms,
        "source": "TELEGRAM_USER_REPORT",
    }


def build_progress(
    *,
    enabled_modes=None,
    publications=None,
    cycles=None,
    observations=None,
    defects=0,
    generated_at="2026-07-15T13:00:00Z",
):
    return build_paper_signal_progress(
        enabled_modes=enabled_modes or ["SCALP"],
        source_publications=publications or [],
        evaluation_cycles=cycles or [],
        observations=observations or [],
        critical_lifecycle_defect_count=defects,
        generated_at=generated_at,
    )


def test_progress_schema_constants_are_frozen():
    assert PAPER_SIGNAL_PROGRESS_SCHEMA_VERSION == 1
    assert type(PAPER_SIGNAL_PROGRESS_SCHEMA_VERSION) is int
    assert PAPER_SIGNAL_PROGRESS_SCHEMA_NAME == "paper-signal-progress"


def test_build_no_trade_evaluation_cycle():
    result = build_evaluation_cycle(
        source_evaluation_id="eval-001",
        mode="SCALP",
        evaluated_at="2026-07-15T12:00:00Z",
        official_alert_signal_ids=[],
        rejection_reasons={
            "REJECT_NO_TRIGGER": 3,
            "REJECT_NET_RR": 1,
        },
    )

    assert result["source_evaluation_id"] == "eval-001"
    assert result["mode"] == "SCALP"
    assert result["official_alert_signal_ids"] == []
    assert result["rejection_reasons"] == {
        "REJECT_NET_RR": 1,
        "REJECT_NO_TRIGGER": 3,
    }
    assert len(result["content_hash"]) == 64


def test_build_official_alert_evaluation_cycle():
    result = build_evaluation_cycle(
        source_evaluation_id="eval-002",
        mode="SWING",
        evaluated_at="2026-07-15T12:00:00Z",
        official_alert_signal_ids=[
            "SWG-002",
            "SWG-001",
        ],
        rejection_reasons={},
    )

    assert result["official_alert_signal_ids"] == [
        "SWG-001",
        "SWG-002",
    ]


def test_evaluation_cycle_rejects_duplicate_signal_ids():
    with pytest.raises(PaperSignalContractError):
        build_evaluation_cycle(
            source_evaluation_id="eval-001",
            mode="SCALP",
            evaluated_at="2026-07-15T12:00:00Z",
            official_alert_signal_ids=["SCP-001", "SCP-001"],
            rejection_reasons={},
        )


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
def test_evaluation_cycle_accepts_exact_modes(mode):
    result = build_evaluation_cycle(
        source_evaluation_id="eval-001",
        mode=mode,
        evaluated_at="2026-07-15T12:00:00Z",
        official_alert_signal_ids=[],
        rejection_reasons={},
    )

    assert result["mode"] == mode


@pytest.mark.parametrize("mode", ["swing", "scalp", "OTHER", "", None])
def test_evaluation_cycle_rejects_invalid_modes(mode):
    with pytest.raises(PaperSignalContractError):
        build_evaluation_cycle(
            source_evaluation_id="eval-001",
            mode=mode,
            evaluated_at="2026-07-15T12:00:00Z",
            official_alert_signal_ids=[],
            rejection_reasons={},
        )


@pytest.mark.parametrize(
    "value",
    [True, -1, 1.5, math.nan, math.inf, "1"],
)
def test_evaluation_cycle_rejects_invalid_rejection_counts(value):
    with pytest.raises(PaperSignalContractError):
        build_evaluation_cycle(
            source_evaluation_id="eval-001",
            mode="SCALP",
            evaluated_at="2026-07-15T12:00:00Z",
            official_alert_signal_ids=[],
            rejection_reasons={"REJECT_NO_TRIGGER": value},
        )


def test_progress_counts_unique_official_signal_identity():
    publications = [
        source_publication(),
        copy.deepcopy(source_publication()),
        source_publication(
            signal_id="SCP-20260715-002",
            delivery_id="delivery-002",
            source_hash="b" * 64,
        ),
    ]

    result = build_progress(publications=publications)

    assert result["official_signal_total"] == 2
    assert result["official_signal_count_by_mode"] == {
        "SWING": 0,
        "INTRADAY": 0,
        "SCALP": 2,
    }


def test_conflicting_official_signal_identity_is_rejected():
    publications = [
        source_publication(),
        source_publication(source_hash="b" * 64),
    ]

    with pytest.raises(PaperSignalContractError):
        build_progress(publications=publications)


def test_replay_publication_never_counts():
    with pytest.raises(PaperSignalContractError):
        build_progress(
            publications=[
                source_publication(classification="REPLAY")
            ]
        )


def test_enabled_modes_are_canonical_ordered_and_unique():
    result = build_progress(
        enabled_modes=["SCALP", "SWING"],
    )

    assert result["enabled_modes"] == ["SWING", "SCALP"]


def test_duplicate_enabled_modes_are_rejected():
    with pytest.raises(PaperSignalContractError):
        build_progress(
            enabled_modes=["SCALP", "SCALP"],
        )


def test_at_least_one_mode_must_be_enabled():
    with pytest.raises(PaperSignalContractError):
        build_paper_signal_progress(
            enabled_modes=[],
            source_publications=[],
            evaluation_cycles=[],
            observations=[],
            critical_lifecycle_defect_count=0,
            generated_at="2026-07-15T13:00:00Z",
        )


def test_no_trade_coverage_ratio_is_null_without_cycles():
    result = build_progress()

    coverage = result["evaluation_coverage_by_mode"]["SCALP"]

    assert coverage == {
        "evaluation_cycles": 0,
        "official_alert_cycles": 0,
        "no_trade_cycles": 0,
        "no_trade_coverage_ratio": None,
        "top_rejection_reasons": {},
    }


def test_no_trade_coverage_is_calculated_per_mode():
    cycles = [
        build_evaluation_cycle(
            source_evaluation_id="eval-001",
            mode="SCALP",
            evaluated_at="2026-07-15T12:00:00Z",
            official_alert_signal_ids=[],
            rejection_reasons={"REJECT_NO_TRIGGER": 2},
        ),
        build_evaluation_cycle(
            source_evaluation_id="eval-002",
            mode="SCALP",
            evaluated_at="2026-07-15T12:05:00Z",
            official_alert_signal_ids=["SCP-001"],
            rejection_reasons={},
        ),
        build_evaluation_cycle(
            source_evaluation_id="eval-003",
            mode="SCALP",
            evaluated_at="2026-07-15T12:10:00Z",
            official_alert_signal_ids=[],
            rejection_reasons={
                "REJECT_NO_TRIGGER": 1,
                "REJECT_NET_RR": 4,
            },
        ),
    ]

    result = build_progress(cycles=cycles)
    coverage = result["evaluation_coverage_by_mode"]["SCALP"]

    assert coverage["evaluation_cycles"] == 3
    assert coverage["official_alert_cycles"] == 1
    assert coverage["no_trade_cycles"] == 2
    assert coverage["no_trade_coverage_ratio"] == pytest.approx(2 / 3)
    assert coverage["top_rejection_reasons"] == {
        "REJECT_NET_RR": 4,
        "REJECT_NO_TRIGGER": 3,
    }


def test_identical_duplicate_evaluation_cycle_is_idempotent():
    cycle = build_evaluation_cycle(
        source_evaluation_id="eval-001",
        mode="SCALP",
        evaluated_at="2026-07-15T12:00:00Z",
        official_alert_signal_ids=[],
        rejection_reasons={},
    )

    result = build_progress(
        cycles=[cycle, copy.deepcopy(cycle)]
    )

    assert (
        result["evaluation_coverage_by_mode"]["SCALP"][
            "evaluation_cycles"
        ]
        == 1
    )


def test_conflicting_evaluation_cycle_reuse_is_rejected():
    first = build_evaluation_cycle(
        source_evaluation_id="eval-001",
        mode="SCALP",
        evaluated_at="2026-07-15T12:00:00Z",
        official_alert_signal_ids=[],
        rejection_reasons={},
    )
    conflicting = copy.deepcopy(first)
    conflicting["evaluated_at"] = "2026-07-15T12:01:00Z"
    conflicting["content_hash"] = "f" * 64

    with pytest.raises(PaperSignalContractError):
        build_progress(cycles=[first, conflicting])


def test_observation_state_distribution_is_deterministic():
    result = build_progress(
        observations=[
            observation(state="ENTRY_ZONE_TOUCHED"),
            observation(
                signal_id="SCP-20260715-002",
                state="EXPIRED_UNTOUCHED",
            ),
            observation(
                signal_id="SCP-20260715-003",
                state="ENTRY_ZONE_TOUCHED",
            ),
        ]
    )

    assert result["observation_state_distribution"] == {
        "ENTRY_ZONE_TOUCHED": 2,
        "EXPIRED_UNTOUCHED": 1,
    }


def test_acknowledgment_summary_reports_coverage_and_latency():
    result = build_progress(
        publications=[source_publication()],
        observations=[
            observation(
                acknowledgment=acknowledgment(1250)
            )
        ],
    )

    assert result["acknowledgment_summary"] == {
        "official_signal_count": 1,
        "acknowledged_signal_count": 1,
        "acknowledgment_coverage_ratio": 1.0,
        "latency_ms": {
            "minimum": 1250,
            "maximum": 1250,
            "mean": 1250,
        },
    }


def test_acknowledgment_summary_is_null_without_acknowledgments():
    result = build_progress(
        publications=[source_publication()],
    )

    assert result["acknowledgment_summary"] == {
        "official_signal_count": 1,
        "acknowledged_signal_count": 0,
        "acknowledgment_coverage_ratio": 0.0,
        "latency_ms": {
            "minimum": None,
            "maximum": None,
            "mean": None,
        },
    }


def make_publications(mode, count):
    prefix = {
        "SWING": "SWG",
        "INTRADAY": "INT",
        "SCALP": "SCP",
    }[mode]

    return [
        source_publication(
            signal_id=f"{prefix}-20260715-{index:03d}",
            delivery_id=f"{mode.lower()}-delivery-{index:03d}",
            mode=mode,
            source_hash=f"{index:064x}",
        )
        for index in range(1, count + 1)
    ]


def test_promotion_ready_at_exact_total_and_per_mode_thresholds():
    publications = (
        make_publications("SWING", 30)
        + make_publications("INTRADAY", 30)
        + make_publications("SCALP", 40)
    )

    result = build_progress(
        enabled_modes=MODE_ORDER,
        publications=publications,
        defects=0,
    )

    assert result["official_signal_total"] == 100
    assert result["promotion_readiness"] is True


def test_promotion_blocked_below_total_threshold():
    result = build_progress(
        enabled_modes=["SCALP"],
        publications=make_publications("SCALP", 99),
    )

    assert result["promotion_readiness"] is False


def test_promotion_blocked_when_enabled_mode_below_thirty():
    publications = (
        make_publications("SWING", 29)
        + make_publications("SCALP", 71)
    )

    result = build_progress(
        enabled_modes=["SWING", "SCALP"],
        publications=publications,
    )

    assert result["official_signal_total"] == 100
    assert result["promotion_readiness"] is False


def test_disabled_mode_does_not_require_minimum_sample():
    publications = make_publications("SCALP", 100)

    result = build_progress(
        enabled_modes=["SCALP"],
        publications=publications,
    )

    assert result["promotion_readiness"] is True


def test_any_critical_defect_blocks_promotion():
    result = build_progress(
        enabled_modes=["SCALP"],
        publications=make_publications("SCALP", 100),
        defects=1,
    )

    assert result["promotion_readiness"] is False


@pytest.mark.parametrize(
    "defects",
    [True, -1, 1.5, "1", None],
)
def test_invalid_critical_defect_counts_are_rejected(defects):
    with pytest.raises(PaperSignalContractError):
        build_progress(defects=defects)


def test_promotion_readiness_is_derived_not_caller_supplied():
    with pytest.raises(TypeError):
        build_paper_signal_progress(
            enabled_modes=["SCALP"],
            source_publications=[],
            evaluation_cycles=[],
            observations=[],
            critical_lifecycle_defect_count=0,
            generated_at="2026-07-15T13:00:00Z",
            promotion_readiness=True,
        )


def test_progress_output_is_deterministic():
    kwargs = {
        "enabled_modes": ["SCALP"],
        "publications": make_publications("SCALP", 2),
        "cycles": [
            build_evaluation_cycle(
                source_evaluation_id="eval-001",
                mode="SCALP",
                evaluated_at="2026-07-15T12:00:00Z",
                official_alert_signal_ids=[],
                rejection_reasons={"REJECT_NO_TRIGGER": 1},
            )
        ],
        "observations": [
            observation(),
        ],
    }

    first = build_progress(**copy.deepcopy(kwargs))
    second = build_progress(**copy.deepcopy(kwargs))

    assert first == second
    assert first["content_hash"] == second["content_hash"]


def test_progress_inputs_are_not_mutated():
    publications = make_publications("SCALP", 1)
    cycles = [
        build_evaluation_cycle(
            source_evaluation_id="eval-001",
            mode="SCALP",
            evaluated_at="2026-07-15T12:00:00Z",
            official_alert_signal_ids=[],
            rejection_reasons={},
        )
    ]
    observations = [observation()]

    originals = copy.deepcopy(
        (publications, cycles, observations)
    )

    build_progress(
        publications=publications,
        cycles=cycles,
        observations=observations,
    )

    assert (publications, cycles, observations) == originals


def test_progress_contains_no_performance_or_account_fields():
    result = build_progress()

    prohibited = {
        "win_rate",
        "profit_factor",
        "realized_pnl",
        "unrealized_pnl",
        "equity_curve",
        "portfolio_return",
        "drawdown",
        "position_size",
        "balance",
    }

    assert prohibited.isdisjoint(result)


@pytest.mark.parametrize(
    "generated_at",
    [
        "2026-07-15T13:00:00",
        "2026-07-15 13:00:00Z",
        "2026-07-15T20:00:00+07:00",
        "",
        None,
    ],
)
def test_progress_requires_deterministic_utc_generated_at(
    generated_at,
):
    with pytest.raises(PaperSignalContractError):
        build_progress(generated_at=generated_at)
