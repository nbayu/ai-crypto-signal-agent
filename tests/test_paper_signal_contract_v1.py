import copy
import hashlib
import json
import math

import pytest

from engine.paper_signal_contract_v1 import (
    PAPER_SIGNAL_CLASSIFICATION,
    PAPER_SIGNAL_EXECUTION_BOUNDARY,
    PAPER_SIGNAL_SCHEMA_NAME,
    PAPER_SIGNAL_SCHEMA_VERSION,
    PaperSignalContractError,
    build_paper_observation_id,
    canonical_json_bytes,
    validate_entry_touch_candle,
    validate_evidence,
    validate_observation_window,
    validate_source_publication_ref,
)


SIGNAL_ID = "SCP-20260715-001"
DELIVERY_ID = "delivery-001"
SOURCE_HASH = "a" * 64
GEOMETRY_HASH = "b" * 64
CANDLE_HASH = "c" * 64
EVENT_HASH = "d" * 64


def source_publication_ref(**overrides):
    value = {
        "signal_id": SIGNAL_ID,
        "delivery_id": DELIVERY_ID,
        "mode": "SCALP",
        "published_at": "2026-07-15T12:00:00Z",
        "source_payload_hash": SOURCE_HASH,
    }
    value.update(overrides)
    return value


def entry_touch_candle(**overrides):
    value = {
        "symbol": "BTCUSDT",
        "interval": "5m",
        "open_time": "2026-07-15T12:00:00Z",
        "close_time": "2026-07-15T12:05:00Z",
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 103.0,
        "is_closed": True,
        "source": "BINANCE_LIVE",
    }
    value.update(overrides)
    return value


def evidence(**overrides):
    value = {
        "signal_geometry_hash": GEOMETRY_HASH,
        "closed_candle_hashes": [CANDLE_HASH],
        "observation_event_hashes": [EVENT_HASH],
    }
    value.update(overrides)
    return value


def expected_observation_id(source):
    identity_payload = {
        "schema_version": 1,
        "signal_id": source["signal_id"],
        "delivery_id": source["delivery_id"],
        "mode": source["mode"],
        "source_payload_hash": source["source_payload_hash"],
    }
    encoded = json.dumps(
        identity_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "PSO-" + hashlib.sha256(encoded).hexdigest()


def test_frozen_schema_and_boundary_constants():
    assert PAPER_SIGNAL_SCHEMA_VERSION == 1
    assert type(PAPER_SIGNAL_SCHEMA_VERSION) is int
    assert PAPER_SIGNAL_SCHEMA_NAME == "paper-signal-observation"
    assert PAPER_SIGNAL_CLASSIFICATION == "PAPER_SIGNAL"
    assert (
        PAPER_SIGNAL_EXECUTION_BOUNDARY
        == "LIVE_MARKET_OBSERVATION_NO_CAPITAL"
    )


def test_canonical_json_is_utf8_sorted_compact_and_deterministic():
    left = {"z": "nilai", "a": {"d": 4, "b": 2}}
    right = {"a": {"b": 2, "d": 4}, "z": "nilai"}

    encoded_left = canonical_json_bytes(left)
    encoded_right = canonical_json_bytes(right)

    assert encoded_left == encoded_right
    assert encoded_left == (
        '{"a":{"b":2,"d":4},"z":"nilai"}'.encode("utf-8")
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_canonical_json_rejects_non_finite_numbers(value):
    with pytest.raises(PaperSignalContractError):
        canonical_json_bytes({"value": value})


def test_canonical_json_does_not_mutate_input():
    payload = {"nested": {"items": [3, 2, 1]}}
    original = copy.deepcopy(payload)

    canonical_json_bytes(payload)

    assert payload == original


def test_source_publication_ref_accepts_exact_contract():
    source = source_publication_ref()

    validated = validate_source_publication_ref(source)

    assert validated == source
    assert validated is not source


@pytest.mark.parametrize(
    "missing",
    [
        "signal_id",
        "delivery_id",
        "mode",
        "published_at",
        "source_payload_hash",
    ],
)
def test_source_publication_ref_rejects_missing_fields(missing):
    source = source_publication_ref()
    source.pop(missing)

    with pytest.raises(PaperSignalContractError):
        validate_source_publication_ref(source)


def test_source_publication_ref_rejects_unknown_fields():
    source = source_publication_ref(unexpected="value")

    with pytest.raises(PaperSignalContractError):
        validate_source_publication_ref(source)


@pytest.mark.parametrize("mode", ["swing", "intraday", "scalp", "OTHER", ""])
def test_source_publication_ref_rejects_noncanonical_modes(mode):
    with pytest.raises(PaperSignalContractError):
        validate_source_publication_ref(
            source_publication_ref(mode=mode)
        )


@pytest.mark.parametrize("mode", ["SWING", "INTRADAY", "SCALP"])
def test_source_publication_ref_accepts_exact_mode_enum(mode):
    validated = validate_source_publication_ref(
        source_publication_ref(mode=mode)
    )

    assert validated["mode"] == mode


@pytest.mark.parametrize(
    "value",
    [
        "",
        "A" * 64,
        "a" * 63,
        "a" * 65,
        "g" * 64,
        123,
        None,
    ],
)
def test_source_publication_ref_rejects_invalid_source_hash(value):
    with pytest.raises(PaperSignalContractError):
        validate_source_publication_ref(
            source_publication_ref(source_payload_hash=value)
        )


@pytest.mark.parametrize(
    "field",
    ["signal_id", "delivery_id"],
)
@pytest.mark.parametrize("value", ["", "   ", None, 123])
def test_source_publication_ref_rejects_invalid_opaque_ids(field, value):
    with pytest.raises(PaperSignalContractError):
        validate_source_publication_ref(
            source_publication_ref(**{field: value})
        )


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-07-15T12:00:00",
        "2026-07-15 12:00:00Z",
        "2026-07-15T19:00:00+07:00",
        "",
        None,
    ],
)
def test_source_publication_ref_requires_iso_utc_timestamp(timestamp):
    with pytest.raises(PaperSignalContractError):
        validate_source_publication_ref(
            source_publication_ref(published_at=timestamp)
        )


def test_observation_id_matches_frozen_identity_formula():
    source = source_publication_ref()

    assert build_paper_observation_id(source) == expected_observation_id(
        source
    )


def test_observation_id_is_deterministic_and_source_is_immutable():
    source = source_publication_ref()
    original = copy.deepcopy(source)

    first = build_paper_observation_id(source)
    second = build_paper_observation_id(copy.deepcopy(source))

    assert first == second
    assert source == original
    assert first.startswith("PSO-")
    assert len(first) == 68


@pytest.mark.parametrize(
    "changed_field,changed_value",
    [
        ("signal_id", "SCP-20260715-002"),
        ("delivery_id", "delivery-002"),
        ("mode", "SWING"),
        ("source_payload_hash", "e" * 64),
    ],
)
def test_observation_id_changes_when_identity_changes(
    changed_field,
    changed_value,
):
    baseline = source_publication_ref()
    changed = source_publication_ref(
        **{changed_field: changed_value}
    )

    assert build_paper_observation_id(
        baseline
    ) != build_paper_observation_id(changed)


def test_observation_window_accepts_exact_deterministic_boundary():
    result = validate_observation_window(
        published_at="2026-07-15T12:00:00Z",
        observed_from="2026-07-15T12:00:00Z",
        observed_until="2026-07-15T13:00:00Z",
        valid_until="2026-07-15T14:00:00Z",
    )

    assert result == {
        "published_at": "2026-07-15T12:00:00Z",
        "observed_from": "2026-07-15T12:00:00Z",
        "observed_until": "2026-07-15T13:00:00Z",
        "valid_until": "2026-07-15T14:00:00Z",
    }


def test_observation_window_rejects_start_before_publication():
    with pytest.raises(PaperSignalContractError):
        validate_observation_window(
            published_at="2026-07-15T12:00:00Z",
            observed_from="2026-07-15T11:59:59Z",
            observed_until="2026-07-15T13:00:00Z",
            valid_until="2026-07-15T14:00:00Z",
        )


def test_observation_window_rejects_end_before_start():
    with pytest.raises(PaperSignalContractError):
        validate_observation_window(
            published_at="2026-07-15T12:00:00Z",
            observed_from="2026-07-15T13:00:00Z",
            observed_until="2026-07-15T12:59:59Z",
            valid_until="2026-07-15T14:00:00Z",
        )


def test_entry_touch_candle_accepts_exact_closed_candle():
    candle = entry_touch_candle()

    validated = validate_entry_touch_candle(
        candle,
        expected_symbol="BTCUSDT",
    )

    assert validated == candle
    assert validated is not candle


def test_entry_touch_candle_rejects_open_candle():
    with pytest.raises(PaperSignalContractError):
        validate_entry_touch_candle(
            entry_touch_candle(is_closed=False),
            expected_symbol="BTCUSDT",
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("open", math.nan),
        ("high", math.inf),
        ("low", -math.inf),
        ("close", True),
    ],
)
def test_entry_touch_candle_rejects_nonfinite_or_boolean_ohlc(
    field,
    value,
):
    with pytest.raises(PaperSignalContractError):
        validate_entry_touch_candle(
            entry_touch_candle(**{field: value}),
            expected_symbol="BTCUSDT",
        )


def test_entry_touch_candle_rejects_invalid_high_low_geometry():
    with pytest.raises(PaperSignalContractError):
        validate_entry_touch_candle(
            entry_touch_candle(high=102.0, close=103.0),
            expected_symbol="BTCUSDT",
        )

    with pytest.raises(PaperSignalContractError):
        validate_entry_touch_candle(
            entry_touch_candle(low=101.0, open=100.0),
            expected_symbol="BTCUSDT",
        )


def test_entry_touch_candle_rejects_symbol_mismatch():
    with pytest.raises(PaperSignalContractError):
        validate_entry_touch_candle(
            entry_touch_candle(symbol="ETHUSDT"),
            expected_symbol="BTCUSDT",
        )


def test_evidence_accepts_exact_hash_contract():
    value = evidence()

    validated = validate_evidence(value)

    assert validated == value
    assert validated is not value
    assert validated["closed_candle_hashes"] is not value[
        "closed_candle_hashes"
    ]


@pytest.mark.parametrize(
    "field",
    [
        "signal_geometry_hash",
        "closed_candle_hashes",
        "observation_event_hashes",
    ],
)
def test_evidence_rejects_missing_fields(field):
    value = evidence()
    value.pop(field)

    with pytest.raises(PaperSignalContractError):
        validate_evidence(value)


def test_evidence_rejects_unknown_fields():
    with pytest.raises(PaperSignalContractError):
        validate_evidence(evidence(account_balance=1000))


@pytest.mark.parametrize(
    "field",
    ["closed_candle_hashes", "observation_event_hashes"],
)
def test_evidence_rejects_duplicate_hashes(field):
    value = evidence(**{field: [CANDLE_HASH, CANDLE_HASH]})

    with pytest.raises(PaperSignalContractError):
        validate_evidence(value)


def test_evidence_allows_empty_hash_arrays():
    validated = validate_evidence(
        evidence(
            closed_candle_hashes=[],
            observation_event_hashes=[],
        )
    )

    assert validated["closed_candle_hashes"] == []
    assert validated["observation_event_hashes"] == []
