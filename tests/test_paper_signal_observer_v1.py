import copy

import pytest

from engine.paper_signal_contract_v1 import PaperSignalContractError
from engine.paper_signal_observer_v1 import (
    FILL_OBSERVATION_AMBIGUOUS,
    FILL_OBSERVATION_ENTRY_ZONE_TOUCHED,
    FILL_OBSERVATION_EXPIRED_UNTOUCHED,
    FILL_OBSERVATION_INVALIDATED_BEFORE_ENTRY,
    FILL_OBSERVATION_NOT_OBSERVED,
    FILL_OBSERVATION_TARGET_REACHED_BEFORE_ENTRY,
    OBSERVATION_CANCELLED,
    OBSERVATION_ENTRY_ZONE_TOUCHED,
    OBSERVATION_EXPIRED_UNTOUCHED,
    OBSERVATION_INVALIDATED_BEFORE_ENTRY,
    OBSERVATION_OBSERVING,
    OBSERVATION_AMBIGUOUS,
    OBSERVATION_TARGET_REACHED_BEFORE_ENTRY,
    observe_paper_signal,
)


def source_publication(**overrides):
    value = {
        "source_publication_ref": {
            "signal_id": "SCP-20260715-001",
            "delivery_id": "delivery-001",
            "mode": "SCALP",
            "published_at": "2026-07-15T12:00:00Z",
            "source_payload_hash": "a" * 64,
        },
        "symbol": "BTCUSDT",
        "side": "LONG",
        "valid_until": "2026-07-15T13:00:00Z",
        "entry_zone": {
            "min": 100.0,
            "max": 102.0,
        },
        "stop_loss": 95.0,
        "take_profit": {
            "tp1": 110.0,
            "tp2": 120.0,
        },
        "signal_geometry_hash": "b" * 64,
        "strategy_version": "master-engine-v2",
        "orchestration_policy_version": "signal-agent-blueprint-v1",
    }
    value.update(overrides)
    return value


def candle(
    *,
    open_time,
    close_time,
    open_price=103.0,
    high=104.0,
    low=102.5,
    close=103.5,
    is_closed=True,
):
    return {
        "symbol": "BTCUSDT",
        "interval": "5m",
        "open_time": open_time,
        "close_time": close_time,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "is_closed": is_closed,
        "source": "BINANCE_LIVE",
    }


def observe(
    *,
    publication=None,
    candles=None,
    observed_from="2026-07-15T12:00:00Z",
    observed_until="2026-07-15T12:30:00Z",
    cancellation=None,
):
    return observe_paper_signal(
        publication=publication or source_publication(),
        closed_candles=candles or [],
        observed_from=observed_from,
        observed_until=observed_until,
        created_at=observed_until,
        observer_version="paper-observer-v1",
        cancellation=cancellation,
    )


def test_no_terminal_event_remains_observing():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T12:00:00Z",
                close_time="2026-07-15T12:05:00Z",
            )
        ]
    )

    assert result["observation_state"] == OBSERVATION_OBSERVING
    assert (
        result["fill_observation_status"]
        == FILL_OBSERVATION_NOT_OBSERVED
    )
    assert result["entry_touched_at"] is None
    assert result["entry_touch_candle"] is None
    assert result["terminal_reason"] is None


def test_entry_zone_touch_is_observation_not_fill():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T12:05:00Z",
                close_time="2026-07-15T12:10:00Z",
                open_price=103.0,
                high=104.0,
                low=101.0,
                close=102.5,
            )
        ]
    )

    assert (
        result["observation_state"]
        == OBSERVATION_ENTRY_ZONE_TOUCHED
    )
    assert (
        result["fill_observation_status"]
        == FILL_OBSERVATION_ENTRY_ZONE_TOUCHED
    )
    assert result["entry_touched_at"] == "2026-07-15T12:10:00Z"
    assert result["entry_touch_candle"]["low"] == 101.0

    prohibited = {
        "filled_at",
        "fill_price",
        "executed_entry",
        "position_opened",
        "position_state",
    }
    assert prohibited.isdisjoint(result)


def test_entry_touch_does_not_create_authoritative_active_state():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T12:05:00Z",
                close_time="2026-07-15T12:10:00Z",
                high=103.0,
                low=100.0,
                close=101.0,
            )
        ]
    )

    assert result["observation_state"] == "ENTRY_ZONE_TOUCHED"
    assert "ACTIVE" not in result.values()
    assert "authoritative_position_transition" not in result


def test_target_before_entry_is_terminal_observation():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T12:05:00Z",
                close_time="2026-07-15T12:10:00Z",
                open_price=106.0,
                high=111.0,
                low=105.0,
                close=109.0,
            )
        ]
    )

    assert (
        result["observation_state"]
        == OBSERVATION_TARGET_REACHED_BEFORE_ENTRY
    )
    assert (
        result["fill_observation_status"]
        == FILL_OBSERVATION_TARGET_REACHED_BEFORE_ENTRY
    )
    assert result["entry_touched_at"] is None


def test_invalidation_before_entry_is_terminal_observation():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T12:05:00Z",
                close_time="2026-07-15T12:10:00Z",
                open_price=98.0,
                high=99.0,
                low=94.0,
                close=96.0,
            )
        ]
    )

    assert (
        result["observation_state"]
        == OBSERVATION_INVALIDATED_BEFORE_ENTRY
    )
    assert (
        result["fill_observation_status"]
        == FILL_OBSERVATION_INVALIDATED_BEFORE_ENTRY
    )
    assert result["entry_touched_at"] is None


def test_entry_and_target_same_candle_is_ambiguous():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T12:05:00Z",
                close_time="2026-07-15T12:10:00Z",
                open_price=105.0,
                high=111.0,
                low=101.0,
                close=108.0,
            )
        ]
    )

    assert result["observation_state"] == OBSERVATION_AMBIGUOUS
    assert (
        result["fill_observation_status"]
        == FILL_OBSERVATION_AMBIGUOUS
    )


def test_entry_and_invalidation_same_candle_is_ambiguous():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T12:05:00Z",
                close_time="2026-07-15T12:10:00Z",
                open_price=100.0,
                high=103.0,
                low=94.0,
                close=98.0,
            )
        ]
    )

    assert result["observation_state"] == OBSERVATION_AMBIGUOUS


def test_target_and_invalidation_same_candle_before_entry_is_ambiguous():
    publication = source_publication(
        entry_zone={"min": 104.0, "max": 106.0}
    )

    result = observe(
        publication=publication,
        candles=[
            candle(
                open_time="2026-07-15T12:05:00Z",
                close_time="2026-07-15T12:10:00Z",
                open_price=103.0,
                high=111.0,
                low=94.0,
                close=100.0,
            )
        ],
    )

    assert result["observation_state"] == OBSERVATION_AMBIGUOUS


def test_first_chronological_terminal_event_wins():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T12:10:00Z",
                close_time="2026-07-15T12:15:00Z",
                open_price=106.0,
                high=111.0,
                low=105.0,
                close=110.0,
            ),
            candle(
                open_time="2026-07-15T12:00:00Z",
                close_time="2026-07-15T12:05:00Z",
                open_price=103.0,
                high=104.0,
                low=101.0,
                close=102.0,
            ),
        ]
    )

    assert (
        result["observation_state"]
        == OBSERVATION_ENTRY_ZONE_TOUCHED
    )
    assert result["entry_touched_at"] == "2026-07-15T12:05:00Z"


def test_candle_before_publication_is_ignored():
    result = observe(
        candles=[
            candle(
                open_time="2026-07-15T11:50:00Z",
                close_time="2026-07-15T11:55:00Z",
                high=111.0,
                low=94.0,
                close=100.0,
            )
        ]
    )

    assert result["observation_state"] == OBSERVATION_OBSERVING


def test_candle_after_observation_window_is_rejected():
    with pytest.raises(PaperSignalContractError):
        observe(
            observed_until="2026-07-15T12:10:00Z",
            candles=[
                candle(
                    open_time="2026-07-15T12:10:00Z",
                    close_time="2026-07-15T12:15:00Z",
                )
            ],
        )


def test_open_candle_is_rejected():
    with pytest.raises(PaperSignalContractError):
        observe(
            candles=[
                candle(
                    open_time="2026-07-15T12:00:00Z",
                    close_time="2026-07-15T12:05:00Z",
                    is_closed=False,
                )
            ]
        )


def test_duplicate_candle_identity_is_rejected():
    duplicate = candle(
        open_time="2026-07-15T12:00:00Z",
        close_time="2026-07-15T12:05:00Z",
    )

    with pytest.raises(PaperSignalContractError):
        observe(candles=[duplicate, copy.deepcopy(duplicate)])


def test_expiry_without_prior_event_is_terminal():
    result = observe(
        observed_until="2026-07-15T13:00:01Z",
        candles=[],
    )

    assert (
        result["observation_state"]
        == OBSERVATION_EXPIRED_UNTOUCHED
    )
    assert (
        result["fill_observation_status"]
        == FILL_OBSERVATION_EXPIRED_UNTOUCHED
    )


def test_exact_valid_until_is_not_expired():
    result = observe(
        observed_until="2026-07-15T13:00:00Z",
        candles=[],
    )

    assert result["observation_state"] == OBSERVATION_OBSERVING


def test_authoritative_cancellation_is_recorded_without_position_mutation():
    result = observe(
        observed_until="2026-07-15T12:20:00Z",
        cancellation={
            "event_id": "cancel-001",
            "reason_code": "CANCEL_NEWS_BLOCK",
            "cancelled_at": "2026-07-15T12:10:00Z",
            "source": "SIGNAL_LIFECYCLE_STORE",
        },
    )

    assert result["observation_state"] == OBSERVATION_CANCELLED
    assert (
        result["fill_observation_status"]
        == FILL_OBSERVATION_NOT_OBSERVED
    )
    assert result["cancellation"]["event_id"] == "cancel-001"
    assert "position_state" not in result


def test_cancellation_before_later_entry_touch_wins():
    result = observe(
        cancellation={
            "event_id": "cancel-001",
            "reason_code": "CANCEL_NEWS_BLOCK",
            "cancelled_at": "2026-07-15T12:06:00Z",
            "source": "SIGNAL_LIFECYCLE_STORE",
        },
        candles=[
            candle(
                open_time="2026-07-15T12:05:00Z",
                close_time="2026-07-15T12:10:00Z",
                high=103.0,
                low=101.0,
                close=102.0,
            )
        ],
    )

    assert result["observation_state"] == OBSERVATION_CANCELLED


def test_entry_touch_before_later_cancellation_wins():
    result = observe(
        cancellation={
            "event_id": "cancel-001",
            "reason_code": "CANCEL_NEWS_BLOCK",
            "cancelled_at": "2026-07-15T12:11:00Z",
            "source": "SIGNAL_LIFECYCLE_STORE",
        },
        candles=[
            candle(
                open_time="2026-07-15T12:00:00Z",
                close_time="2026-07-15T12:05:00Z",
                high=103.0,
                low=101.0,
                close=102.0,
            )
        ],
    )

    assert (
        result["observation_state"]
        == OBSERVATION_ENTRY_ZONE_TOUCHED
    )


def test_observer_does_not_mutate_publication_candles_or_cancellation():
    publication = source_publication()
    candles = [
        candle(
            open_time="2026-07-15T12:00:00Z",
            close_time="2026-07-15T12:05:00Z",
        )
    ]
    cancellation = {
        "event_id": "cancel-001",
        "reason_code": "CANCEL_DATA_STALE",
        "cancelled_at": "2026-07-15T12:20:00Z",
        "source": "SIGNAL_LIFECYCLE_STORE",
    }

    original_publication = copy.deepcopy(publication)
    original_candles = copy.deepcopy(candles)
    original_cancellation = copy.deepcopy(cancellation)

    observe(
        publication=publication,
        candles=candles,
        cancellation=cancellation,
    )

    assert publication == original_publication
    assert candles == original_candles
    assert cancellation == original_cancellation


def test_result_does_not_alias_mutable_inputs():
    publication = source_publication()
    candles = [
        candle(
            open_time="2026-07-15T12:00:00Z",
            close_time="2026-07-15T12:05:00Z",
            high=103.0,
            low=101.0,
            close=102.0,
        )
    ]

    result = observe(publication=publication, candles=candles)

    publication["entry_zone"]["min"] = 1.0
    candles[0]["low"] = 1.0

    assert result["signal_geometry"]["entry_zone"]["min"] == 100.0
    assert result["entry_touch_candle"]["low"] == 101.0


def test_observer_output_is_deterministic_for_identical_inputs():
    kwargs = {
        "publication": source_publication(),
        "candles": [
            candle(
                open_time="2026-07-15T12:00:00Z",
                close_time="2026-07-15T12:05:00Z",
            )
        ],
    }

    first = observe(**copy.deepcopy(kwargs))
    second = observe(**copy.deepcopy(kwargs))

    assert first == second
    assert first["content_hash"] == second["content_hash"]


@pytest.mark.parametrize(
    "side,publication,candles,expected_state",
    [
        (
            "LONG",
            source_publication(side="LONG"),
            [
                candle(
                    open_time="2026-07-15T12:00:00Z",
                    close_time="2026-07-15T12:05:00Z",
                    high=111.0,
                    low=105.0,
                    close=109.0,
                )
            ],
            OBSERVATION_TARGET_REACHED_BEFORE_ENTRY,
        ),
        (
            "SHORT",
            source_publication(
                side="SHORT",
                entry_zone={"min": 108.0, "max": 110.0},
                stop_loss=115.0,
                take_profit={"tp1": 100.0, "tp2": 95.0},
            ),
            [
                candle(
                    open_time="2026-07-15T12:00:00Z",
                    close_time="2026-07-15T12:05:00Z",
                    open_price=104.0,
                    high=105.0,
                    low=99.0,
                    close=101.0,
                )
            ],
            OBSERVATION_TARGET_REACHED_BEFORE_ENTRY,
        ),
    ],
)
def test_target_detection_is_side_aware(
    side,
    publication,
    candles,
    expected_state,
):
    assert publication["side"] == side

    result = observe(
        publication=publication,
        candles=candles,
    )

    assert result["observation_state"] == expected_state


@pytest.mark.parametrize("side", ["BUY", "SELL", "long", "", None])
def test_invalid_side_is_rejected(side):
    with pytest.raises(PaperSignalContractError):
        observe(publication=source_publication(side=side))


def test_replay_classified_publication_is_rejected():
    publication = source_publication()
    publication["classification"] = "REPLAY"

    with pytest.raises(PaperSignalContractError):
        observe(publication=publication)


def test_account_and_execution_fields_are_rejected():
    publication = source_publication()
    publication["position_size"] = 1.0

    with pytest.raises(PaperSignalContractError):
        observe(publication=publication)
