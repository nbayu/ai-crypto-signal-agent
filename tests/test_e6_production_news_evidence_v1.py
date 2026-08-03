from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect

import pytest

import engine.e6_production_news_evidence_v1 as subject
from test_e5_technical_review_payload_v1 import _event, _risk


IDENTITY = "a" * 64
OBSERVED = "2026-08-03T08:00:00Z"


def test_contract_is_passive_frozen_slotted_and_closed() -> None:
    source = inspect.getsource(subject)
    ast.parse(source)
    for forbidden in ("requests", "ccxt", "Phase11", "shadow", "os.environ"):
        assert forbidden not in source

    evidence = subject.build_e6_production_zero_source_news_evidence_v1(
        candidate_identity_sha256=IDENTITY,
        observed_at=OBSERVED,
    )
    assert type(evidence) is subject.E6ProductionNewsEvidenceV1
    assert evidence.__dataclass_params__.frozen
    assert "__dict__" not in evidence.__slots__
    assert tuple(item.name for item in fields(evidence)) == (
        "schema_version",
        "policy_version",
        "candidate_identity_sha256",
        "scan_scope",
        "declared_source_count",
        "completed_source_count",
        "scan_started_at",
        "scan_completed_at",
        "status",
        "reason_code",
        "normalized_news_events",
        "news_risk_object",
        "publication_capped",
        "news_escalation_allowed",
        "global_coverage_claimed",
        "evidence_sha256",
    )
    with pytest.raises(FrozenInstanceError):
        evidence.status = subject.RELEVANT_NEWS_PRESENT


def test_zero_configured_source_is_exact_bounded_absence_not_global_claim() -> None:
    first = subject.build_e6_production_zero_source_news_evidence_v1(
        candidate_identity_sha256=IDENTITY,
        observed_at=OBSERVED,
    )
    second = subject.build_e6_production_zero_source_news_evidence_v1(
        candidate_identity_sha256=IDENTITY,
        observed_at=OBSERVED,
    )

    assert first.status == subject.NO_RELEVANT_NEWS_AFTER_COMPLETED_BOUNDED_SCAN
    assert first.scan_scope == subject.OPTIONAL_CONFIGURED_CP10_CAPTURE_SET
    assert first.declared_source_count == first.completed_source_count == 0
    assert first.normalized_news_events == ()
    assert first.news_risk_object is None
    assert first.publication_capped is False
    assert first.news_escalation_allowed is False
    assert first.global_coverage_claimed is False
    assert first.reason_code == subject.NO_NEWS_SOURCE_CONFIGURED_OPTIONAL_POLICY
    assert first.to_mapping() == second.to_mapping()
    assert first.evidence_sha256 == second.evidence_sha256
    assert "placeholder" not in first.canonical_evidence_json().casefold()


def test_strict_present_news_preserves_cp10_event_and_risk() -> None:
    event = _event()
    risk = _risk(event)
    evidence = subject.build_e6_production_present_news_evidence_v1(
        candidate_identity_sha256=IDENTITY,
        scan_started_at="2026-07-30T06:20:00Z",
        scan_completed_at="2026-07-30T06:30:00Z",
        declared_source_count=1,
        normalized_news_events=(event,),
        news_risk_object=risk,
    )

    assert evidence.status == subject.RELEVANT_NEWS_PRESENT
    assert evidence.normalized_news_events == (event,)
    assert evidence.normalized_news_events[0] is not event
    assert evidence.news_risk_object == risk
    assert evidence.news_risk_object is not risk
    assert evidence.publication_capped is False
    assert evidence.news_escalation_allowed is False
    evidence.__post_init__()


def test_unavailable_or_incomplete_is_capped_without_fabrication() -> None:
    evidence = subject.build_e6_production_unavailable_news_evidence_v1(
        candidate_identity_sha256=IDENTITY,
        scan_started_at="2026-08-03T07:59:00Z",
        scan_completed_at=OBSERVED,
        declared_source_count=2,
        completed_source_count=1,
    )

    assert evidence.status == subject.NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE
    assert evidence.normalized_news_events == ()
    assert evidence.news_risk_object is None
    assert evidence.publication_capped is True
    assert evidence.news_escalation_allowed is False
    assert evidence.global_coverage_claimed is False


@pytest.mark.parametrize(
    "changes",
    (
        {"candidate_identity_sha256": "A" * 64},
        {"declared_source_count": True},
        {"completed_source_count": 1},
        {"scan_started_at": "2026-08-03T08:00:00+00:00"},
        {"global_coverage_claimed": True},
        {"normalized_news_events": (_event(),)},
        {"publication_capped": True},
        {"news_escalation_allowed": True},
        {"evidence_sha256": "0" * 64},
    ),
)
def test_zero_source_contract_rejects_forgery(changes) -> None:
    evidence = subject.build_e6_production_zero_source_news_evidence_v1(
        candidate_identity_sha256=IDENTITY,
        observed_at=OBSERVED,
    )
    with pytest.raises(subject.E6ProductionNewsEvidenceErrorV1):
        replace(evidence, **changes)


def test_present_and_unavailable_builders_reject_invalid_completion() -> None:
    event = _event()
    with pytest.raises(subject.E6ProductionNewsEvidenceErrorV1):
        subject.build_e6_production_present_news_evidence_v1(
            candidate_identity_sha256=IDENTITY,
            scan_started_at=OBSERVED,
            scan_completed_at=OBSERVED,
            declared_source_count=0,
            normalized_news_events=(event,),
            news_risk_object=_risk(event),
        )
    with pytest.raises(subject.E6ProductionNewsEvidenceErrorV1):
        subject.build_e6_production_unavailable_news_evidence_v1(
            candidate_identity_sha256=IDENTITY,
            scan_started_at=OBSERVED,
            scan_completed_at=OBSERVED,
            declared_source_count=1,
            completed_source_count=1,
        )
