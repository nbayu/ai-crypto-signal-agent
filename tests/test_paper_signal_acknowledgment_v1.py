import copy

import pytest

from engine.paper_signal_contract_v1 import PaperSignalContractError
from engine.paper_signal_acknowledgment_v1 import (
    ACKNOWLEDGMENT_ENTRY_REPORTED,
    ACKNOWLEDGMENT_SKIP_REPORTED,
    apply_acknowledgment_to_observation,
    build_acknowledgment,
    merge_acknowledgment,
)


def source_publication_ref(**overrides):
    value = {
        "signal_id": "SCP-20260715-001",
        "delivery_id": "delivery-001",
        "mode": "SCALP",
        "published_at": "2026-07-15T12:00:00Z",
        "source_payload_hash": "a" * 64,
    }
    value.update(overrides)
    return value


def acknowledgment_event(**overrides):
    value = {
        "event_id": "ack-001",
        "event_type": "ENTRY_REPORTED",
        "acknowledged_at": "2026-07-15T12:00:01.250Z",
        "source": "TELEGRAM_USER_REPORT",
    }
    value.update(overrides)
    return value


def canonical_acknowledgment(**overrides):
    value = {
        "signal_id": "SCP-20260715-001",
        "delivery_id": "delivery-001",
        "event_id": "ack-001",
        "event_type": "ENTRY_REPORTED",
        "published_at": "2026-07-15T12:00:00Z",
        "acknowledged_at": "2026-07-15T12:00:01.250Z",
        "acknowledgment_latency_ms": 1250,
        "source": "TELEGRAM_USER_REPORT",
    }
    value.update(overrides)
    return value


def observation(**overrides):
    value = {
        "schema_version": 1,
        "schema_name": "paper-signal-observation",
        "paper_observation_id": "PSO-" + ("b" * 64),
        "signal_id": "SCP-20260715-001",
        "mode": "SCALP",
        "classification": "PAPER_SIGNAL",
        "execution_boundary": "LIVE_MARKET_OBSERVATION_NO_CAPITAL",
        "capital_exposure": "NONE",
        "order_execution": "PROHIBITED",
        "position_authority": "TELEGRAM_USER_REPORT",
        "source_publication_ref": source_publication_ref(),
        "strategy_version": "master-engine-v2",
        "orchestration_policy_version": "signal-agent-blueprint-v1",
        "observer_version": "paper-observer-v1",
        "signal_geometry": {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_zone": {"min": 100.0, "max": 102.0},
            "stop_loss": 95.0,
            "take_profit": {"tp1": 110.0, "tp2": 120.0},
            "valid_until": "2026-07-15T13:00:00Z",
        },
        "observed_from": "2026-07-15T12:00:00Z",
        "observed_until": "2026-07-15T12:10:00Z",
        "observation_state": "ENTRY_ZONE_TOUCHED",
        "fill_observation_status": "ENTRY_ZONE_TOUCHED",
        "entry_touched_at": "2026-07-15T12:05:00Z",
        "entry_touch_candle": None,
        "acknowledgment": None,
        "cancellation": None,
        "terminal_reason": "ENTRY_ZONE_TOUCHED",
        "evidence": {
            "signal_geometry_hash": "c" * 64,
            "closed_candle_hashes": [],
            "observation_event_hashes": [],
        },
        "created_at": "2026-07-15T12:10:00Z",
        "content_hash": "d" * 64,
    }
    value.update(overrides)
    return value


def test_frozen_acknowledgment_event_constants():
    assert ACKNOWLEDGMENT_ENTRY_REPORTED == "ENTRY_REPORTED"
    assert ACKNOWLEDGMENT_SKIP_REPORTED == "SKIP_REPORTED"


def test_build_entry_acknowledgment_with_exact_millisecond_latency():
    result = build_acknowledgment(
        source_publication_ref=source_publication_ref(),
        event=acknowledgment_event(),
    )

    assert result == canonical_acknowledgment()


def test_build_skip_acknowledgment():
    result = build_acknowledgment(
        source_publication_ref=source_publication_ref(),
        event=acknowledgment_event(
            event_type="SKIP_REPORTED",
            acknowledged_at="2026-07-15T12:00:02Z",
        ),
    )

    assert result["signal_id"] == "SCP-20260715-001"
    assert result["delivery_id"] == "delivery-001"
    assert result["event_type"] == "SKIP_REPORTED"
    assert result["acknowledgment_latency_ms"] == 2000


@pytest.mark.parametrize(
    "event_type",
    [
        "CLOSE_REPORTED",
        "STATUS_REQUESTED",
        "ENTRY",
        "SKIP",
        "entry_reported",
        "",
        None,
    ],
)
def test_rejects_non_acknowledgment_event_types(event_type):
    with pytest.raises(PaperSignalContractError):
        build_acknowledgment(
            source_publication_ref=source_publication_ref(),
            event=acknowledgment_event(event_type=event_type),
        )


def test_rejects_acknowledgment_before_publication():
    with pytest.raises(PaperSignalContractError):
        build_acknowledgment(
            source_publication_ref=source_publication_ref(),
            event=acknowledgment_event(
                acknowledged_at="2026-07-15T11:59:59.999Z"
            ),
        )


def test_accepts_acknowledgment_exactly_at_publication():
    result = build_acknowledgment(
        source_publication_ref=source_publication_ref(),
        event=acknowledgment_event(
            acknowledged_at="2026-07-15T12:00:00Z"
        ),
    )

    assert result["acknowledgment_latency_ms"] == 0
    assert type(result["acknowledgment_latency_ms"]) is int


@pytest.mark.parametrize(
    "field",
    ["event_id", "event_type", "acknowledged_at", "source"],
)
def test_rejects_missing_event_fields(field):
    event = acknowledgment_event()
    event.pop(field)

    with pytest.raises(PaperSignalContractError):
        build_acknowledgment(
            source_publication_ref=source_publication_ref(),
            event=event,
        )


def test_rejects_unknown_event_fields():
    with pytest.raises(PaperSignalContractError):
        build_acknowledgment(
            source_publication_ref=source_publication_ref(),
            event=acknowledgment_event(chat_id="secret"),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("event_id", ""),
        ("event_id", "   "),
        ("event_id", None),
        ("source", ""),
        ("source", None),
    ],
)
def test_rejects_invalid_event_identity_fields(field, value):
    with pytest.raises(PaperSignalContractError):
        build_acknowledgment(
            source_publication_ref=source_publication_ref(),
            event=acknowledgment_event(**{field: value}),
        )


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-07-15T12:00:01",
        "2026-07-15 12:00:01Z",
        "2026-07-15T19:00:01+07:00",
        "",
        None,
    ],
)
def test_requires_acknowledgment_timestamp_in_utc(timestamp):
    with pytest.raises(PaperSignalContractError):
        build_acknowledgment(
            source_publication_ref=source_publication_ref(),
            event=acknowledgment_event(
                acknowledged_at=timestamp
            ),
        )


def test_source_event_is_not_mutated_or_aliased():
    source = source_publication_ref()
    event = acknowledgment_event()
    original_source = copy.deepcopy(source)
    original_event = copy.deepcopy(event)

    result = build_acknowledgment(
        source_publication_ref=source,
        event=event,
    )

    assert source == original_source
    assert event == original_event

    event["event_id"] = "changed"
    assert result["event_id"] == "ack-001"


def test_identical_duplicate_acknowledgment_is_idempotent():
    existing = canonical_acknowledgment()
    incoming = copy.deepcopy(existing)

    result = merge_acknowledgment(
        existing=existing,
        incoming=incoming,
    )

    assert result == existing
    assert result is not existing


@pytest.mark.parametrize(
    "field,value",
    [
        ("signal_id", "SCP-20260715-002"),
        ("delivery_id", "delivery-002"),
        ("event_id", "ack-002"),
        ("event_type", "SKIP_REPORTED"),
        ("acknowledged_at", "2026-07-15T12:00:02Z"),
        ("acknowledgment_latency_ms", 2000),
        ("source", "OTHER_SOURCE"),
    ],
)
def test_conflicting_second_acknowledgment_is_rejected(field, value):
    existing = canonical_acknowledgment()
    incoming = copy.deepcopy(existing)
    incoming[field] = value

    with pytest.raises(PaperSignalContractError):
        merge_acknowledgment(
            existing=existing,
            incoming=incoming,
        )


def test_none_existing_accepts_first_valid_acknowledgment():
    incoming = canonical_acknowledgment()

    result = merge_acknowledgment(
        existing=None,
        incoming=incoming,
    )

    assert result == incoming
    assert result is not incoming


def test_none_incoming_preserves_existing_acknowledgment():
    existing = canonical_acknowledgment()

    result = merge_acknowledgment(
        existing=existing,
        incoming=None,
    )

    assert result == existing
    assert result is not existing


def test_apply_acknowledgment_updates_observation_copy_only():
    source_observation = observation()
    original = copy.deepcopy(source_observation)
    acknowledgment = canonical_acknowledgment()

    result = apply_acknowledgment_to_observation(
        observation=source_observation,
        acknowledgment=acknowledgment,
        updated_at="2026-07-15T12:11:00Z",
    )

    assert source_observation == original
    assert result is not source_observation
    assert result["acknowledgment"] == acknowledgment
    assert result["content_hash"] != original["content_hash"]


def test_apply_acknowledgment_preserves_observation_state():
    result = apply_acknowledgment_to_observation(
        observation=observation(),
        acknowledgment=canonical_acknowledgment(),
        updated_at="2026-07-15T12:11:00Z",
    )

    assert result["observation_state"] == "ENTRY_ZONE_TOUCHED"
    assert result["fill_observation_status"] == "ENTRY_ZONE_TOUCHED"


def test_entry_acknowledgment_does_not_create_active_position_state():
    result = apply_acknowledgment_to_observation(
        observation=observation(),
        acknowledgment=canonical_acknowledgment(),
        updated_at="2026-07-15T12:11:00Z",
    )

    assert result["acknowledgment"]["event_type"] == "ENTRY_REPORTED"
    assert "position_state" not in result
    assert "ACTIVE" not in result.values()
    assert "authoritative_position_transition" not in result


def test_skip_acknowledgment_does_not_mutate_observation_terminal_state():
    result = apply_acknowledgment_to_observation(
        observation=observation(
            observation_state="TARGET_REACHED_BEFORE_ENTRY",
            fill_observation_status="TARGET_REACHED_BEFORE_ENTRY",
            terminal_reason="TARGET_REACHED_BEFORE_ENTRY",
        ),
        acknowledgment=canonical_acknowledgment(
            event_type="SKIP_REPORTED",
            acknowledged_at="2026-07-15T12:00:03Z",
            acknowledgment_latency_ms=3000,
        ),
        updated_at="2026-07-15T12:11:00Z",
    )

    assert (
        result["observation_state"]
        == "TARGET_REACHED_BEFORE_ENTRY"
    )
    assert result["acknowledgment"]["event_type"] == "SKIP_REPORTED"


def test_apply_identical_acknowledgment_is_idempotent():
    acknowledgment = canonical_acknowledgment()

    first = apply_acknowledgment_to_observation(
        observation=observation(),
        acknowledgment=acknowledgment,
        updated_at="2026-07-15T12:11:00Z",
    )

    second = apply_acknowledgment_to_observation(
        observation=first,
        acknowledgment=copy.deepcopy(acknowledgment),
        updated_at="2026-07-15T12:11:00Z",
    )

    assert second == first
    assert second["content_hash"] == first["content_hash"]


def test_apply_conflicting_acknowledgment_is_rejected():
    first = apply_acknowledgment_to_observation(
        observation=observation(),
        acknowledgment=canonical_acknowledgment(),
        updated_at="2026-07-15T12:11:00Z",
    )

    conflicting = canonical_acknowledgment(
        event_id="ack-002",
        event_type="SKIP_REPORTED",
        acknowledged_at="2026-07-15T12:00:02Z",
        acknowledgment_latency_ms=2000,
    )

    with pytest.raises(PaperSignalContractError):
        apply_acknowledgment_to_observation(
            observation=first,
            acknowledgment=conflicting,
            updated_at="2026-07-15T12:12:00Z",
        )


def test_rejects_acknowledgment_for_different_signal_publication():
    with pytest.raises(PaperSignalContractError):
        apply_acknowledgment_to_observation(
            observation=observation(),
            acknowledgment=canonical_acknowledgment(
                signal_id="SCP-20260715-999"
            ),
            updated_at="2026-07-15T12:11:00Z",
        )


def test_rejects_acknowledgment_for_different_delivery():
    with pytest.raises(PaperSignalContractError):
        apply_acknowledgment_to_observation(
            observation=observation(),
            acknowledgment=canonical_acknowledgment(
                delivery_id="delivery-999"
            ),
            updated_at="2026-07-15T12:11:00Z",
        )


def test_rejects_updated_at_before_acknowledgment():
    with pytest.raises(PaperSignalContractError):
        apply_acknowledgment_to_observation(
            observation=observation(),
            acknowledgment=canonical_acknowledgment(),
            updated_at="2026-07-15T12:00:01Z",
        )


def test_rejects_boolean_latency_in_incoming_acknowledgment():
    incoming = canonical_acknowledgment(
        acknowledgment_latency_ms=True
    )

    with pytest.raises(PaperSignalContractError):
        merge_acknowledgment(
            existing=None,
            incoming=incoming,
        )


def test_rejects_latency_inconsistent_with_timestamps():
    incoming = canonical_acknowledgment(
        acknowledgment_latency_ms=999
    )

    with pytest.raises(PaperSignalContractError):
        merge_acknowledgment(
            existing=None,
            incoming=incoming,
        )


def test_rejects_unknown_canonical_acknowledgment_fields():
    incoming = canonical_acknowledgment(hidden_identity="invalid")

    with pytest.raises(PaperSignalContractError):
        merge_acknowledgment(
            existing=None,
            incoming=incoming,
        )


def test_acknowledgment_result_contains_no_transport_or_account_fields():
    result = build_acknowledgment(
        source_publication_ref=source_publication_ref(),
        event=acknowledgment_event(),
    )

    prohibited = {
        "chat_id",
        "telegram_user_id",
        "delivery_latency_ms",
        "position_size",
        "fill_price",
        "filled_at",
        "balance",
        "pnl",
    }
    assert prohibited.isdisjoint(result)
