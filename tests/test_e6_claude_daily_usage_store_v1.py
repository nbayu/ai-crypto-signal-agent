from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import json
import os
from pathlib import Path

import pytest

import engine.e6_claude_daily_usage_store_v1 as subject
from test_e5_claude_review_router_v1 import UTC_DAY, _usage


TIMESTAMP = "2026-07-30T12:00:00Z"
ACTIVE_BINDING_V4_SHA256 = (
    "4a31dbcb7a0c4daed3215dbe8817002c24b2ead30e7092096c992b322e0fe1d9"
)
HISTORICAL_BINDING_V3_SHA256 = (
    "dc2454ffdc7f05978a168f88beaf892e7e04387053a0b91c89da79adccf3778e"
)
RECORD_FIELDS = (
    "store_version",
    "utc_day",
    "provider_binding_sha256",
    "store_generation",
    "prior_usage_sha256",
    "usage",
    "usage_sha256",
    "committed_at",
    "record_sha256",
)


def _sha(index):
    return f"{index:064x}"


def _canonical_hash(mapping):
    return hashlib.sha256(
        json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _file(tmp_path):
    return tmp_path / f"{UTC_DAY}.e6-claude-daily-usage.json"


def _commit(
    tmp_path,
    after,
    *,
    generation=0,
    record_sha=None,
    usage_sha=None,
    timestamp=TIMESTAMP,
):
    if usage_sha is None:
        usage_sha = _usage().usage_sha256
    return subject.compare_and_commit_e6_claude_daily_usage_store_v1(
        authorized_store_root=tmp_path,
        utc_day=UTC_DAY,
        expected_store_generation=generation,
        expected_record_sha256=record_sha,
        expected_usage_sha256=usage_sha,
        proposed_usage_after=after,
        committed_at=timestamp,
    )


def _assert_invalid(call):
    with pytest.raises(
        ValueError,
        match="^invalid E6 Claude daily usage store$",
    ):
        call()


def test_exact_store_contract_record_hash_file_and_mode(tmp_path):
    after = _usage(l1=(_sha(1),))
    record = _commit(tmp_path, after)
    assert subject.E6_CLAUDE_DAILY_USAGE_STORE_VERSION == (
        "e6-claude-daily-usage-store-v1"
    )
    assert subject.STORE_FORMAT == "ONE_CANONICAL_JSON_FILE_PER_UTC_DAY"
    assert subject.STORE_RECORD_FIELD_COUNT == 9
    assert tuple(field.name for field in fields(subject.E6ClaudeDailyUsageStoreRecordV1)) == RECORD_FIELDS
    assert subject.E6ClaudeDailyUsageStoreRecordV1.__dataclass_params__.frozen
    assert "__dict__" not in subject.E6ClaudeDailyUsageStoreRecordV1.__slots__
    assert tuple(record.to_mapping()) == RECORD_FIELDS
    assert record.provider_binding_sha256 == ACTIVE_BINDING_V4_SHA256
    assert _canonical_hash(json.loads(record.canonical_record_json())) == (
        record.record_sha256
    )
    path = _file(tmp_path)
    raw = path.read_bytes()
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert json.loads(raw) == record.to_mapping()
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert (
        subject.reconstruct_e6_claude_daily_usage_store_record_v1(
            record.to_mapping()
        )
        == record
    )
    with pytest.raises(FrozenInstanceError):
        record.store_generation = 2


def test_absent_load_resolves_empty_without_daily_file(tmp_path):
    assert subject.load_e6_claude_daily_usage_store_v1(
        authorized_store_root=tmp_path,
        utc_day=UTC_DAY,
        observed_at=TIMESTAMP,
    ) is None
    usage = subject.resolve_e6_claude_daily_usage_before_v1(
        record=None,
        utc_day=UTC_DAY,
    )
    assert usage == _usage()
    assert not _file(tmp_path).exists()


def test_first_and_subsequent_compare_and_set_preserve_prefixes(tmp_path):
    first_usage = _usage(l1=(_sha(1),))
    first = _commit(tmp_path, first_usage)
    second_usage = _usage(l1=(_sha(1),), l2=(_sha(2),))
    second = _commit(
        tmp_path,
        second_usage,
        generation=first.store_generation,
        record_sha=first.record_sha256,
        usage_sha=first.usage_sha256,
        timestamp="2026-07-30T12:00:01Z",
    )
    assert first.store_generation == 1
    assert first.prior_usage_sha256 == _usage().usage_sha256
    assert second.store_generation == 2
    assert second.prior_usage_sha256 == first.usage_sha256
    assert second.usage.l1_reviewed_payload_sha256s == (_sha(1),)
    assert second.usage.l2_reviewed_payload_sha256s == (_sha(2),)
    loaded = subject.load_e6_claude_daily_usage_store_v1(
        authorized_store_root=tmp_path,
        utc_day=UTC_DAY,
        observed_at="2026-07-30T12:00:02Z",
    )
    assert loaded == second


def test_current_day_v3_record_is_rejected_under_v4_without_rewrite_or_carry(
    tmp_path,
):
    active_record = _commit(tmp_path, _usage(l1=(_sha(1),)))
    historical_mapping = active_record.to_mapping()
    historical_mapping["provider_binding_sha256"] = (
        HISTORICAL_BINDING_V3_SHA256
    )
    preimage = dict(historical_mapping)
    preimage.pop("record_sha256")
    historical_mapping["record_sha256"] = _canonical_hash(preimage)
    historical_raw = (
        json.dumps(
            historical_mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    _file(tmp_path).write_bytes(historical_raw)
    os.chmod(_file(tmp_path), 0o600)

    _assert_invalid(
        lambda: subject.load_e6_claude_daily_usage_store_v1(
            authorized_store_root=tmp_path,
            utc_day=UTC_DAY,
            observed_at="2026-07-30T12:00:01Z",
        )
    )
    assert _file(tmp_path).read_bytes() == historical_raw

    _assert_invalid(
        lambda: _commit(
            tmp_path,
            _usage(l1=(_sha(1), _sha(2))),
            generation=active_record.store_generation,
            record_sha=historical_mapping["record_sha256"],
            usage_sha=active_record.usage_sha256,
            timestamp="2026-07-30T12:00:01Z",
        )
    )
    assert _file(tmp_path).read_bytes() == historical_raw
    unchanged = json.loads(historical_raw)
    assert unchanged["provider_binding_sha256"] == HISTORICAL_BINDING_V3_SHA256
    assert unchanged["store_generation"] == 1
    assert unchanged["usage"]["l1_reviewed_payload_sha256s"] == [_sha(1)]
    assert not hasattr(subject, "invoke_e5_claude_review_once_v1")


@pytest.mark.parametrize(
    "stale",
    ("generation", "record_sha", "usage_sha"),
)
def test_stale_compare_and_set_and_conflicting_reservation_fail_closed(
    tmp_path,
    stale,
):
    first = _commit(tmp_path, _usage(l1=(_sha(1),)))
    values = {
        "generation": first.store_generation,
        "record_sha": first.record_sha256,
        "usage_sha": first.usage_sha256,
    }
    values[stale] = 0 if stale == "generation" else "0" * 64
    _assert_invalid(
        lambda: _commit(
            tmp_path,
            _usage(l1=(_sha(1), _sha(2))),
            **values,
            timestamp="2026-07-30T12:00:01Z",
        )
    )
    assert json.loads(_file(tmp_path).read_text())["record_sha256"] == (
        first.record_sha256
    )


@pytest.mark.parametrize(
    "after",
    (
        _usage(l1=(_sha(1), _sha(2))),
        _usage(l1=(_sha(1),), l2=(_sha(2),)),
    ),
)
def test_first_commit_rejects_multi_append_and_duplicate(after, tmp_path):
    _assert_invalid(lambda: _commit(tmp_path, after))
    assert not _file(tmp_path).exists()


@pytest.mark.parametrize(
    "mutation",
    ("unknown", "missing", "record_hash", "usage_hash", "day", "future"),
)
def test_corruption_unknown_keys_hash_day_and_future_fail_closed(
    tmp_path,
    mutation,
):
    record = _commit(tmp_path, _usage(l1=(_sha(1),)))
    mapping = record.to_mapping()
    observed = "2026-07-30T12:00:02Z"
    if mutation == "unknown":
        mapping["unknown"] = True
    elif mutation == "missing":
        mapping.pop("usage_sha256")
    elif mutation == "record_hash":
        mapping["record_sha256"] = "0" * 64
    elif mutation == "usage_hash":
        mapping["usage_sha256"] = "0" * 64
    elif mutation == "day":
        mapping["utc_day"] = "2026-07-29"
    else:
        mapping["committed_at"] = "2026-07-30T13:00:00Z"
        preimage = dict(mapping)
        preimage.pop("record_sha256")
        mapping["record_sha256"] = _canonical_hash(preimage)
        observed = "2026-07-30T12:59:59Z"
    _file(tmp_path).write_text(
        json.dumps(mapping, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(_file(tmp_path), 0o600)
    _assert_invalid(
        lambda: subject.load_e6_claude_daily_usage_store_v1(
            authorized_store_root=tmp_path,
            utc_day=UTC_DAY,
            observed_at=observed,
        )
    )


@pytest.mark.parametrize("raw", (b"\xff\n", b"{invalid}\n", b"{}"))
def test_malformed_utf8_json_and_missing_final_lf_fail_closed(tmp_path, raw):
    _file(tmp_path).write_bytes(raw)
    os.chmod(_file(tmp_path), 0o600)
    _assert_invalid(
        lambda: subject.load_e6_claude_daily_usage_store_v1(
            authorized_store_root=tmp_path,
            utc_day=UTC_DAY,
            observed_at=TIMESTAMP,
        )
    )


def test_unexplained_temporary_symlink_and_traversal_fail_closed(tmp_path):
    temporary = Path(str(_file(tmp_path)) + ".tmp")
    temporary.write_text("unexplained", encoding="utf-8")
    _assert_invalid(
        lambda: subject.load_e6_claude_daily_usage_store_v1(
            authorized_store_root=tmp_path,
            utc_day=UTC_DAY,
            observed_at=TIMESTAMP,
        )
    )
    temporary.unlink()
    outside = tmp_path.parent / "outside-e6-store"
    outside.mkdir(exist_ok=True)
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    _assert_invalid(
        lambda: subject.E6ClaudeDailyUsageFileStoreV1(
            authorized_store_root=linked
        )
    )
    _assert_invalid(
        lambda: subject.E6ClaudeDailyUsageFileStoreV1(
            authorized_store_root=tmp_path / ".." / tmp_path.name
        )
    )


def test_file_store_port_and_zero_retry_surface(tmp_path):
    store = subject.E6ClaudeDailyUsageFileStoreV1(
        authorized_store_root=tmp_path
    )
    assert isinstance(store, subject.E6ClaudeDailyUsageStorePortV1)
    assert store.load(utc_day=UTC_DAY, observed_at=TIMESTAMP) is None
    record = store.compare_and_commit(
        utc_day=UTC_DAY,
        expected_store_generation=0,
        expected_record_sha256=None,
        expected_usage_sha256=_usage().usage_sha256,
        proposed_usage_after=_usage(l2=(_sha(1),)),
        committed_at=TIMESTAMP,
    )
    assert record.store_generation == 1
    source = Path(subject.__file__).read_text(encoding="utf-8")
    assert "while " not in source
    assert "retry" not in source.casefold()
