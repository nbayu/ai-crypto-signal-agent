"""RED specification for deterministic Phase 10 source policy."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path

import pytest

from engine.news_event_contract_v1 import (
    EVENT_SCHEMA_VERSION,
    RawNewsCaptureV1,
    SourceDescriptorV1,
    canonical_json_bytes,
)
from engine.news_source_policy_v1 import (
    SOURCE_POLICY_VERSION,
    NewsSourcePolicyError,
    SourcePolicyConfigV1,
    SourcePolicyDecisionV1,
    evaluate_source_policy,
)


UTC = timezone.utc
PUBLICATION = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
CAPTURE = datetime(2026, 7, 16, 12, 1, tzinfo=UTC)
POINT_IN_TIME = datetime(2026, 7, 16, 12, 2, tzinfo=UTC)
EVALUATION = datetime(2026, 7, 16, 12, 30, tzinfo=UTC)
RAW_BODY = "Fictional source policy content."


def expect_policy_error(callable_object, *args, **kwargs):
    with pytest.raises(NewsSourcePolicyError):
        callable_object(*args, **kwargs)


def source_descriptor(**overrides):
    body_hash = hashlib.sha256(RAW_BODY.encode("utf-8")).hexdigest()
    values = {
        "source_namespace": "fictional-wire",
        "source_id": "source-001",
        "source_type": "NEWSWIRE",
        "canonical_source_uri": "https://example.invalid/news/source-001",
        "publisher_identity": "fictional-publisher",
        "credibility_tier": "TIER_1",
        "publication_timestamp_utc": PUBLICATION,
        "capture_timestamp_utc": CAPTURE,
        "point_in_time_timestamp_utc": POINT_IN_TIME,
        "content_type": "text/plain",
        "language": "en-US",
        "raw_content_sha256": body_hash,
        "source_metadata": {"edition": "source-policy-v1"},
        "source_health_status": "HEALTHY",
        "schema_version": "news-source-schema-v1",
    }
    values.update(overrides)
    return SourceDescriptorV1(**values)


def raw_capture(**overrides):
    source_overrides = overrides.pop("source_overrides", {})
    raw_title = overrides.pop("raw_title", "Fictional source policy headline")
    raw_body = overrides.pop("raw_body", RAW_BODY)
    raw_language = overrides.pop("raw_language", "en-US")
    body_hash = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()
    source = source_descriptor(
        raw_content_sha256=body_hash,
        **source_overrides,
    )
    values = {
        "source": source,
        "raw_title": raw_title,
        "raw_body": raw_body,
        "raw_language": raw_language,
        "raw_content_sha256": body_hash,
        "capture_payload_sha256": "0" * 64,
        "captured_at_utc": source.capture_timestamp_utc,
        "schema_version": EVENT_SCHEMA_VERSION,
    }
    values.update(overrides)
    without_hash = dict(values)
    without_hash.pop("capture_payload_sha256")
    without_hash["source"] = source.to_mapping()
    values["capture_payload_sha256"] = hashlib.sha256(
        canonical_json_bytes(without_hash)
    ).hexdigest()
    return RawNewsCaptureV1(**values)


def config(**overrides):
    values = {
        "allowed_source_types": ["NEWSWIRE"],
        "blocked_source_types": [],
        "allowed_source_namespaces": ["fictional-wire"],
        "blocked_source_namespaces": [],
        "allowed_publishers": ["fictional-publisher"],
        "blocked_publishers": [],
        "minimum_credibility_tier": "TIER_2",
        "acceptable_source_health_statuses": ["HEALTHY"],
        "allowed_content_types": ["text/plain"],
        "allowed_uri_schemes": ["https"],
        "maximum_source_age_seconds": 3600,
        "maximum_capture_delay_seconds": 300,
        "policy_version": SOURCE_POLICY_VERSION,
    }
    values.update(overrides)
    return SourcePolicyConfigV1(**values)


def evaluate(*, source_snapshot=None, policy=None, evaluation=EVALUATION):
    return evaluate_source_policy(
        source_snapshot=(
            raw_capture() if source_snapshot is None else source_snapshot
        ),
        config=config() if policy is None else policy,
        evaluation_timestamp_utc=evaluation,
    )


def assert_decision(decision, expected_state, expected_primary):
    assert decision.decision == expected_state
    assert decision.primary_reason_code == expected_primary
    assert decision.policy_version == SOURCE_POLICY_VERSION
    assert decision.reason_codes


def test_source_policy_version_is_frozen():
    assert SOURCE_POLICY_VERSION == "news-source-policy-v1"


def test_source_policy_config_is_closed_and_immutable():
    values = {
        "allowed_source_types": ["NEWSWIRE"],
        "blocked_source_types": [],
        "allowed_source_namespaces": ["fictional-wire"],
        "blocked_source_namespaces": [],
        "allowed_publishers": ["fictional-publisher"],
        "blocked_publishers": [],
        "minimum_credibility_tier": "TIER_2",
        "acceptable_source_health_statuses": ["HEALTHY"],
        "allowed_content_types": ["text/plain"],
        "allowed_uri_schemes": ["https"],
        "maximum_source_age_seconds": 3600,
        "maximum_capture_delay_seconds": 300,
        "policy_version": SOURCE_POLICY_VERSION,
    }
    source_types = values["allowed_source_types"]
    policy = SourcePolicyConfigV1(**values)
    source_types.append("OTHER")
    assert policy.allowed_source_types == ("NEWSWIRE",)
    with pytest.raises((AttributeError, TypeError)):
        policy.allowed_source_types += ("OTHER",)
    expect_policy_error(
        SourcePolicyConfigV1,
        **{**values, "unexpected": "field"},
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("policy_version", "news-source-policy-v2"),
        ("minimum_credibility_tier", "TIER_9"),
        ("acceptable_source_health_statuses", ["UNKNOWN"]),
        ("allowed_uri_schemes", ["ftp"]),
        ("maximum_source_age_seconds", -1),
        ("maximum_capture_delay_seconds", -1),
        ("maximum_source_age_seconds", True),
        ("maximum_capture_delay_seconds", False),
    ],
)
def test_invalid_policy_configuration_fails_closed(field, value):
    values = config().__dict__.copy()
    values[field] = value
    expect_policy_error(SourcePolicyConfigV1, **values)


def test_policy_configuration_deduplicates_and_orders_collections():
    policy = config(
        allowed_source_types=["NEWSWIRE", "NEWSWIRE"],
        allowed_source_namespaces=["z-wire", "a-wire", "z-wire"],
        allowed_publishers=["publisher-b", "publisher-a"],
        acceptable_source_health_statuses=["HEALTHY", "HEALTHY"],
        allowed_content_types=["text/xml", "text/plain"],
        allowed_uri_schemes=["https", "https"],
    )
    assert policy.allowed_source_types == ("NEWSWIRE",)
    assert policy.allowed_source_namespaces == ("a-wire", "z-wire")
    assert policy.allowed_publishers == ("publisher-a", "publisher-b")
    assert policy.acceptable_source_health_statuses == ("HEALTHY",)
    assert policy.allowed_content_types == ("text/plain", "text/xml")
    assert policy.allowed_uri_schemes == ("https",)


def test_empty_allowlists_permit_all_nonblocked_values():
    policy = config(
        allowed_source_types=[],
        allowed_source_namespaces=[],
        allowed_publishers=[],
    )
    decision = evaluate(policy=policy)
    assert_decision(decision, "ELIGIBLE", "SOURCE_ELIGIBLE")


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("source_type", "EXTERNAL", "SOURCE_TYPE_NOT_ALLOWED"),
        (
            "source_namespace",
            "other-wire",
            "SOURCE_NAMESPACE_NOT_ALLOWED",
        ),
        (
            "publisher_identity",
            "other-publisher",
            "PUBLISHER_NOT_ALLOWED",
        ),
        ("credibility_tier", "TIER_3", "CREDIBILITY_TIER_BELOW_MINIMUM"),
        ("source_health_status", "DEGRADED", "SOURCE_HEALTH_UNACCEPTABLE"),
        ("content_type", "application/json", "CONTENT_TYPE_NOT_ALLOWED"),
    ],
)
def test_ordinary_source_ineligibility_is_deterministic(field, value, reason):
    source = raw_capture(source_overrides={field: value})
    decision = evaluate(source_snapshot=source)
    assert_decision(decision, "INELIGIBLE", reason)
    assert reason in decision.reason_codes


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("blocked_source_types", ["NEWSWIRE"], "SOURCE_TYPE_BLOCKED"),
        (
            "blocked_source_namespaces",
            ["fictional-wire"],
            "SOURCE_NAMESPACE_BLOCKED",
        ),
        (
            "blocked_publishers",
            ["fictional-publisher"],
            "PUBLISHER_BLOCKED",
        ),
    ],
)
def test_explicit_blocklists_produce_hard_block(field, value, reason):
    decision = evaluate(policy=config(**{field: value}))
    assert_decision(decision, "BLOCKED", reason)


def test_blocklist_precedes_allowlist_and_high_credibility():
    source = raw_capture(
        source_overrides={"credibility_tier": "TIER_1"},
    )
    policy = config(
        allowed_source_types=["NEWSWIRE"],
        blocked_source_types=["NEWSWIRE"],
    )
    decision = evaluate(source_snapshot=source, policy=policy)
    assert_decision(decision, "BLOCKED", "SOURCE_TYPE_BLOCKED")


def test_empty_blocklists_block_nothing():
    decision = evaluate(policy=config())
    assert_decision(decision, "ELIGIBLE", "SOURCE_ELIGIBLE")


def test_credibility_tier_order_is_closed_and_deterministic():
    for tier in ("TIER_1", "TIER_2"):
        decision = evaluate(
            source_snapshot=raw_capture(
                source_overrides={"credibility_tier": tier}
            ),
            policy=config(minimum_credibility_tier="TIER_2"),
        )
        assert_decision(decision, "ELIGIBLE", "SOURCE_ELIGIBLE")
    for tier in ("TIER_3", "TIER_4"):
        decision = evaluate(
            source_snapshot=raw_capture(
                source_overrides={"credibility_tier": tier}
            ),
            policy=config(minimum_credibility_tier="TIER_2"),
        )
        assert_decision(
            decision,
            "INELIGIBLE",
            "CREDIBILITY_TIER_BELOW_MINIMUM",
        )


def test_health_status_is_supplied_point_in_time_data_only():
    healthy = evaluate(source_snapshot=raw_capture())
    degraded = evaluate(
        source_snapshot=raw_capture(
            source_overrides={"source_health_status": "DEGRADED"}
        ),
        policy=config(acceptable_source_health_statuses=["DEGRADED"]),
    )
    failed = evaluate(
        source_snapshot=raw_capture(
            source_overrides={"source_health_status": "FAILED"}
        ),
    )
    assert_decision(healthy, "ELIGIBLE", "SOURCE_ELIGIBLE")
    assert_decision(degraded, "ELIGIBLE", "SOURCE_ELIGIBLE")
    assert_decision(failed, "INELIGIBLE", "SOURCE_HEALTH_UNACCEPTABLE")


def test_future_publication_is_invalid_or_blocked_not_eligible():
    source = raw_capture(
        source_overrides={
            "publication_timestamp_utc": EVALUATION + timedelta(seconds=1),
            "capture_timestamp_utc": EVALUATION + timedelta(seconds=2),
            "point_in_time_timestamp_utc": EVALUATION + timedelta(seconds=3),
        }
    )
    decision = evaluate(source_snapshot=source)
    assert decision.decision in {"INVALID", "BLOCKED", "INELIGIBLE"}
    assert "PUBLICATION_TIMESTAMP_IN_FUTURE" in decision.reason_codes


def test_source_age_equal_limit_is_eligible_and_one_second_over_is_not():
    exact_publication = EVALUATION - timedelta(seconds=3600)
    exact = evaluate(
        source_snapshot=raw_capture(
            source_overrides={
                "publication_timestamp_utc": exact_publication,
                "capture_timestamp_utc": exact_publication + timedelta(seconds=1),
                "point_in_time_timestamp_utc": exact_publication + timedelta(seconds=2),
            }
        )
    )
    old = EVALUATION - timedelta(seconds=3601)
    over = evaluate(
        source_snapshot=raw_capture(
            source_overrides={
                "publication_timestamp_utc": old,
                "capture_timestamp_utc": old + timedelta(seconds=1),
                "point_in_time_timestamp_utc": old + timedelta(seconds=2),
            }
        )
    )
    assert_decision(exact, "ELIGIBLE", "SOURCE_ELIGIBLE")
    assert_decision(over, "INELIGIBLE", "SOURCE_TOO_OLD")


def test_capture_delay_equal_limit_is_eligible_and_one_second_over_is_not():
    publication = EVALUATION - timedelta(seconds=300)
    exact = evaluate(
        source_snapshot=raw_capture(
            source_overrides={
                "publication_timestamp_utc": publication,
                "capture_timestamp_utc": publication + timedelta(seconds=300),
                "point_in_time_timestamp_utc": publication + timedelta(seconds=301),
            }
        )
    )
    old_publication = EVALUATION - timedelta(seconds=301)
    over = evaluate(
        source_snapshot=raw_capture(
            source_overrides={
                "publication_timestamp_utc": old_publication,
                "capture_timestamp_utc": old_publication + timedelta(seconds=301),
                "point_in_time_timestamp_utc": old_publication + timedelta(seconds=302),
            }
        )
    )
    assert_decision(exact, "ELIGIBLE", "SOURCE_ELIGIBLE")
    assert "CAPTURE_DELAY_EXCEEDED" in over.reason_codes


def test_source_age_uses_publication_not_capture_timestamp():
    publication = EVALUATION - timedelta(seconds=3601)
    source = raw_capture(
        source_overrides={
            "publication_timestamp_utc": publication,
            "capture_timestamp_utc": EVALUATION,
            "point_in_time_timestamp_utc": EVALUATION + timedelta(seconds=1),
        }
    )
    decision = evaluate(source_snapshot=source)
    assert decision.decision == "INELIGIBLE"
    assert "SOURCE_TOO_OLD" in decision.reason_codes


def test_disabled_limits_use_explicit_none_sentinel():
    policy = config(
        maximum_source_age_seconds=None,
        maximum_capture_delay_seconds=None,
    )
    old = EVALUATION - timedelta(days=365)
    decision = evaluate(
        source_snapshot=raw_capture(
            source_overrides={
                "publication_timestamp_utc": old,
                "capture_timestamp_utc": old + timedelta(seconds=1),
                "point_in_time_timestamp_utc": old + timedelta(seconds=2),
            }
        ),
        policy=policy,
    )
    assert_decision(decision, "ELIGIBLE", "SOURCE_ELIGIBLE")


class ZeroOffsetTz(tzinfo):
    def utcoffset(self, value):
        return timedelta(0)

    def dst(self, value):
        return timedelta(0)

    def tzname(self, value):
        return "CUSTOM-ZERO"


def test_evaluation_timestamp_requires_utc_aware_input():
    custom = datetime(2026, 7, 16, 12, 30, tzinfo=ZeroOffsetTz())
    decision = evaluate(evaluation=custom)
    assert decision.evaluation_timestamp_utc.tzinfo is timezone.utc
    expect_policy_error(
        evaluate_source_policy,
        source_snapshot=raw_capture(),
        config=config(),
        evaluation_timestamp_utc=datetime(2026, 7, 16, 12, 30),
    )
    expect_policy_error(
        evaluate_source_policy,
        source_snapshot=raw_capture(),
        config=config(),
        evaluation_timestamp_utc=(
            datetime(2026, 7, 16, 13, 30, tzinfo=timezone(timedelta(hours=1)))
        ),
    )


def test_evaluation_before_publication_is_not_eligible():
    source = raw_capture()
    decision = evaluate(
        source_snapshot=source,
        evaluation=PUBLICATION - timedelta(seconds=1),
    )
    assert_decision(
        decision,
        "INVALID",
        "PUBLICATION_TIMESTAMP_IN_FUTURE",
    )


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("https://example.invalid/news/source-001", "SOURCE_ELIGIBLE"),
        ("http://example.invalid/news/source-001", "URI_SCHEME_NOT_ALLOWED"),
    ],
)
def test_uri_scheme_is_evaluated_locally(uri, expected):
    source = raw_capture(source_overrides={"canonical_source_uri": uri})
    decision = evaluate(source_snapshot=source)
    assert expected in decision.reason_codes


def test_content_type_is_exact_and_no_body_sniffing_occurs():
    source = raw_capture(source_overrides={"content_type": "application/json"})
    decision = evaluate(source_snapshot=source)
    assert_decision(decision, "INELIGIBLE", "CONTENT_TYPE_NOT_ALLOWED")


def test_decision_is_closed_immutable_and_has_no_authority_fields():
    decision = evaluate()
    assert set(decision.to_mapping()) == {
        "policy_version",
        "decision",
        "primary_reason_code",
        "reason_codes",
        "evaluated_source_snapshot_ref",
        "evaluation_timestamp_utc",
        "source_namespace",
        "source_id",
    }
    with pytest.raises((AttributeError, TypeError)):
        decision.decision = "BLOCKED"
    mapping = decision.to_mapping()
    for field in (
        "provider",
        "model",
        "severity",
        "routing",
        "adjudication",
        "publication",
        "delivery",
        "order",
        "position",
        "capital",
    ):
        mapping[field] = "forbidden"
        expect_policy_error(SourcePolicyDecisionV1, **mapping)
        mapping.pop(field)


def test_eligible_decision_has_only_eligible_reason():
    decision = evaluate()
    assert_decision(decision, "ELIGIBLE", "SOURCE_ELIGIBLE")
    assert decision.reason_codes == ("SOURCE_ELIGIBLE",)


def test_reason_order_is_policy_precedence_not_collection_order():
    source = raw_capture(
        source_overrides={
            "source_namespace": "other-wire",
            "publisher_identity": "other-publisher",
            "credibility_tier": "TIER_4",
            "source_health_status": "FAILED",
            "content_type": "application/json",
        }
    )
    decision = evaluate(source_snapshot=source)
    assert decision.reason_codes == (
        "SOURCE_NAMESPACE_NOT_ALLOWED",
        "PUBLISHER_NOT_ALLOWED",
        "CREDIBILITY_TIER_BELOW_MINIMUM",
        "SOURCE_HEALTH_UNACCEPTABLE",
        "CONTENT_TYPE_NOT_ALLOWED",
    )
    assert decision.primary_reason_code == "SOURCE_NAMESPACE_NOT_ALLOWED"


def test_hard_block_precedes_all_ordinary_failure_reasons():
    source = raw_capture(
        source_overrides={
            "source_health_status": "FAILED",
            "content_type": "application/json",
        }
    )
    decision = evaluate(
        source_snapshot=source,
        policy=config(
            blocked_source_types=["NEWSWIRE"],
        ),
    )
    assert_decision(decision, "BLOCKED", "SOURCE_TYPE_BLOCKED")


def test_identical_evaluations_are_structurally_equal():
    capture_a = raw_capture()
    capture_b = raw_capture()
    assert capture_a is not capture_b
    assert capture_a == capture_b
    first = evaluate(source_snapshot=capture_a, policy=config())
    second = evaluate(
        source_snapshot=capture_b,
        policy=config(),
    )
    assert first == second
    assert first.to_mapping() == second.to_mapping()


def test_decision_retains_detached_source_snapshot_reference():
    capture = raw_capture()
    decision = evaluate(source_snapshot=capture)
    assert decision.evaluated_source_snapshot_ref["source_namespace"] == (
        capture.source.source_namespace
    )
    assert decision.evaluated_source_snapshot_ref["source_id"] == (
        capture.source.source_id
    )
    reference = decision.evaluated_source_snapshot_ref
    with pytest.raises((TypeError, AttributeError)):
        reference["source_id"] = "mutated"


def test_invalid_source_mapping_and_lookalike_are_rejected():
    expect_policy_error(
        evaluate_source_policy,
        source_snapshot=raw_capture().to_mapping(),
        config=config(),
        evaluation_timestamp_utc=EVALUATION,
    )


def test_invalid_source_contract_is_not_swallowed():
    source = raw_capture()
    values = source.to_mapping()
    values["raw_content_sha256"] = "f" * 64
    expect_policy_error(
        evaluate_source_policy,
        source_snapshot=values,
        config=config(),
        evaluation_timestamp_utc=EVALUATION,
    )


def test_policy_configuration_cannot_be_mutated_after_evaluation():
    allowed = ["NEWSWIRE"]
    policy = config(allowed_source_types=allowed)
    decision = evaluate(policy=policy)
    allowed.append("OTHER")
    assert decision == evaluate(policy=policy)


def test_source_policy_module_has_no_provider_or_runtime_imports():
    module = __import__("engine.news_source_policy_v1", fromlist=["*"])
    source = Path(module.__file__).read_text(encoding="utf-8")
    forbidden = (
        "anthropic",
        "openai",
        "httpx",
        "aiohttp",
        "requests",
        "ccxt",
        "telegram",
        "os.environ",
        "getenv",
        "subprocess",
        "socket",
        "datetime.now",
        "utcnow",
        "time.time",
        "uuid",
        "random",
        "MasterEngine",
        "production_signal",
        "paper_signal",
        "shadow_release",
        "quota_slot",
        "replay_runner_v4",
        "deepseek_validator_v4",
    )
    assert not any(item in source for item in forbidden)


def test_source_policy_module_has_no_semantic_or_execution_authority():
    module = __import__("engine.news_source_policy_v1", fromlist=["*"])
    source = Path(module.__file__).read_text(encoding="utf-8")
    forbidden_fields = (
        "side",
        "entry",
        "stop_loss",
        "take_profit",
        "score",
        "ranking",
        "severity",
        "adjudication",
        "prompt_cache",
        "publication",
        "delivery",
        "order",
        "account",
        "position",
        "capital",
    )
    assert not any(f'"{field}"' in source for field in forbidden_fields)
