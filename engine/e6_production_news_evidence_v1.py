"""Passive optional-news evidence for the E6 production composition."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Final

from engine.news_event_contract_v1 import NormalizedNewsEventV1
from engine.news_risk_object_v1 import NewsRiskObjectV1


E6_PRODUCTION_NEWS_EVIDENCE_SCHEMA_V1: Final = (
    "ai-crypto-signal-agent.e6-production-news-evidence.v1"
)
E6_PRODUCTION_NEWS_EVIDENCE_POLICY_V1: Final = (
    "e6-production-optional-news-policy-v1"
)
OPTIONAL_CONFIGURED_CP10_CAPTURE_SET: Final = (
    "OPTIONAL_CONFIGURED_CP10_CAPTURE_SET"
)
RELEVANT_NEWS_PRESENT: Final = "RELEVANT_NEWS_PRESENT"
NO_RELEVANT_NEWS_AFTER_COMPLETED_BOUNDED_SCAN: Final = (
    "NO_RELEVANT_NEWS_AFTER_COMPLETED_BOUNDED_SCAN"
)
NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE: Final = (
    "NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE"
)
NO_NEWS_SOURCE_CONFIGURED_OPTIONAL_POLICY: Final = (
    "NO_NEWS_SOURCE_CONFIGURED_OPTIONAL_POLICY"
)

_STATUSES: Final = frozenset(
    {
        RELEVANT_NEWS_PRESENT,
        NO_RELEVANT_NEWS_AFTER_COMPLETED_BOUNDED_SCAN,
        NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE,
    }
)
_UTC: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_SHA256: Final = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_REASON: Final = re.compile(r"[A-Z0-9][A-Z0-9_]{0,127}\Z")
_ERROR: Final = "INVALID_E6_PRODUCTION_NEWS_EVIDENCE"


class E6ProductionNewsEvidenceErrorV1(ValueError):
    """Fixed-code validation failure with no supplied value rendering."""

    def __init__(self) -> None:
        self.code = _ERROR
        super().__init__(_ERROR)


def _invalid() -> None:
    raise E6ProductionNewsEvidenceErrorV1() from None


def _require(condition: bool) -> None:
    if not condition:
        _invalid()


def _timestamp(value: object) -> str:
    _require(type(value) is str and _UTC.fullmatch(value) is not None)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        _invalid()
    _require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return value


def _risk_mapping(value: NewsRiskObjectV1) -> dict[str, object]:
    return {item.name: getattr(value, item.name) for item in fields(value)}


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        _invalid()


def _digest(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _copy_event(value: object) -> NormalizedNewsEventV1:
    _require(type(value) is NormalizedNewsEventV1)
    mapping = value.to_mapping()
    mapping["publication_timestamp_utc"] = value.publication_timestamp_utc
    mapping["point_in_time_timestamp_utc"] = value.point_in_time_timestamp_utc
    copied = NormalizedNewsEventV1(**mapping)
    _require(copied == value)
    return copied


def _copy_risk(value: object) -> NewsRiskObjectV1:
    _require(type(value) is NewsRiskObjectV1)
    copied = NewsRiskObjectV1(**_risk_mapping(value))
    _require(copied == value)
    return copied


@dataclass(frozen=True, slots=True)
class E6ProductionNewsEvidenceV1:
    schema_version: str
    policy_version: str
    candidate_identity_sha256: str
    scan_scope: str
    declared_source_count: int
    completed_source_count: int
    scan_started_at: str
    scan_completed_at: str
    status: str
    reason_code: str
    normalized_news_events: tuple[NormalizedNewsEventV1, ...]
    news_risk_object: NewsRiskObjectV1 | None
    publication_capped: bool
    news_escalation_allowed: bool
    global_coverage_claimed: bool
    evidence_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(self.schema_version == E6_PRODUCTION_NEWS_EVIDENCE_SCHEMA_V1)
            _require(self.policy_version == E6_PRODUCTION_NEWS_EVIDENCE_POLICY_V1)
            _require(
                type(self.candidate_identity_sha256) is str
                and _SHA256.fullmatch(self.candidate_identity_sha256) is not None
            )
            _require(self.scan_scope == OPTIONAL_CONFIGURED_CP10_CAPTURE_SET)
            _require(
                type(self.declared_source_count) is int
                and self.declared_source_count >= 0
                and type(self.completed_source_count) is int
                and 0 <= self.completed_source_count <= self.declared_source_count
            )
            started = _timestamp(self.scan_started_at)
            completed = _timestamp(self.scan_completed_at)
            _require(started <= completed)
            _require(self.status in _STATUSES)
            _require(
                type(self.reason_code) is str
                and _SAFE_REASON.fullmatch(self.reason_code) is not None
            )
            _require(type(self.normalized_news_events) in (tuple, list))
            normalized = tuple(_copy_event(item) for item in self.normalized_news_events)
            normalized = tuple(
                sorted(
                    normalized,
                    key=lambda item: (
                        item.point_in_time_timestamp_utc,
                        item.event_snapshot_id,
                    ),
                )
            )
            _require(
                len({item.event_snapshot_id for item in normalized}) == len(normalized)
            )
            object.__setattr__(self, "normalized_news_events", normalized)
            for decision in (
                self.publication_capped,
                self.news_escalation_allowed,
                self.global_coverage_claimed,
            ):
                _require(type(decision) is bool)
            _require(self.global_coverage_claimed is False)

            if self.status == RELEVANT_NEWS_PRESENT:
                _require(self.declared_source_count >= 1)
                _require(self.completed_source_count == self.declared_source_count)
                _require(bool(normalized))
                risk = _copy_risk(self.news_risk_object)
                _require(risk.event_snapshot_id == normalized[-1].event_snapshot_id)
                _require(risk.event_snapshot_id in risk.evidence_refs)
                expected_capped = risk.news_gate_recommendation in {
                    "REQUIRE_BLOCK",
                    "FAIL_CLOSED",
                }
                expected_escalation = risk.risk_classification in {
                    "CAUTION",
                    "ELEVATED",
                    "BLOCKING",
                }
                _require(self.publication_capped is expected_capped)
                _require(self.news_escalation_allowed is expected_escalation)
            elif self.status == NO_RELEVANT_NEWS_AFTER_COMPLETED_BOUNDED_SCAN:
                _require(self.completed_source_count == self.declared_source_count)
                _require(normalized == () and self.news_risk_object is None)
                _require(self.publication_capped is False)
                _require(self.news_escalation_allowed is False)
            else:
                _require(self.completed_source_count < self.declared_source_count)
                _require(normalized == () and self.news_risk_object is None)
                _require(self.publication_capped is True)
                _require(self.news_escalation_allowed is False)
            _require(
                type(self.evidence_sha256) is str
                and _SHA256.fullmatch(self.evidence_sha256) is not None
                and self.evidence_sha256 == _digest(self._content_mapping())
            )
        except E6ProductionNewsEvidenceErrorV1:
            raise
        except Exception:
            _invalid()

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "candidate_identity_sha256": self.candidate_identity_sha256,
            "scan_scope": self.scan_scope,
            "declared_source_count": self.declared_source_count,
            "completed_source_count": self.completed_source_count,
            "scan_started_at": self.scan_started_at,
            "scan_completed_at": self.scan_completed_at,
            "status": self.status,
            "reason_code": self.reason_code,
            "normalized_news_events": [item.to_mapping() for item in self.normalized_news_events],
            "news_risk_object": (
                None
                if self.news_risk_object is None
                else _risk_mapping(self.news_risk_object)
            ),
            "publication_capped": self.publication_capped,
            "news_escalation_allowed": self.news_escalation_allowed,
            "global_coverage_claimed": self.global_coverage_claimed,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._content_mapping()
        mapping["evidence_sha256"] = self.evidence_sha256
        return mapping

    def canonical_evidence_json(self) -> str:
        return _canonical_json(self._content_mapping())


def _build(**values: object) -> E6ProductionNewsEvidenceV1:
    normalized_events = tuple(
        sorted(
            (_copy_event(item) for item in values["normalized_news_events"]),
            key=lambda item: (
                item.point_in_time_timestamp_utc,
                item.event_snapshot_id,
            ),
        )
    )
    values["normalized_news_events"] = normalized_events
    temporary = object.__new__(E6ProductionNewsEvidenceV1)
    for name, value in values.items():
        object.__setattr__(temporary, name, value)
    object.__setattr__(temporary, "evidence_sha256", "0" * 64)
    return E6ProductionNewsEvidenceV1(
        **values,
        evidence_sha256=_digest(temporary._content_mapping()),
    )


def build_e6_production_present_news_evidence_v1(
    *,
    candidate_identity_sha256: str,
    scan_started_at: str,
    scan_completed_at: str,
    declared_source_count: int,
    normalized_news_events: tuple[NormalizedNewsEventV1, ...],
    news_risk_object: NewsRiskObjectV1,
    reason_code: str = "RELEVANT_NEWS_VALIDATED",
) -> E6ProductionNewsEvidenceV1:
    risk = _copy_risk(news_risk_object)
    return _build(
        schema_version=E6_PRODUCTION_NEWS_EVIDENCE_SCHEMA_V1,
        policy_version=E6_PRODUCTION_NEWS_EVIDENCE_POLICY_V1,
        candidate_identity_sha256=candidate_identity_sha256,
        scan_scope=OPTIONAL_CONFIGURED_CP10_CAPTURE_SET,
        declared_source_count=declared_source_count,
        completed_source_count=declared_source_count,
        scan_started_at=scan_started_at,
        scan_completed_at=scan_completed_at,
        status=RELEVANT_NEWS_PRESENT,
        reason_code=reason_code,
        normalized_news_events=tuple(normalized_news_events),
        news_risk_object=risk,
        publication_capped=risk.news_gate_recommendation
        in {"REQUIRE_BLOCK", "FAIL_CLOSED"},
        news_escalation_allowed=risk.risk_classification
        in {"CAUTION", "ELEVATED", "BLOCKING"},
        global_coverage_claimed=False,
    )


def build_e6_production_zero_source_news_evidence_v1(
    *,
    candidate_identity_sha256: str,
    observed_at: str,
) -> E6ProductionNewsEvidenceV1:
    return _build(
        schema_version=E6_PRODUCTION_NEWS_EVIDENCE_SCHEMA_V1,
        policy_version=E6_PRODUCTION_NEWS_EVIDENCE_POLICY_V1,
        candidate_identity_sha256=candidate_identity_sha256,
        scan_scope=OPTIONAL_CONFIGURED_CP10_CAPTURE_SET,
        declared_source_count=0,
        completed_source_count=0,
        scan_started_at=observed_at,
        scan_completed_at=observed_at,
        status=NO_RELEVANT_NEWS_AFTER_COMPLETED_BOUNDED_SCAN,
        reason_code=NO_NEWS_SOURCE_CONFIGURED_OPTIONAL_POLICY,
        normalized_news_events=(),
        news_risk_object=None,
        publication_capped=False,
        news_escalation_allowed=False,
        global_coverage_claimed=False,
    )


def build_e6_production_unavailable_news_evidence_v1(
    *,
    candidate_identity_sha256: str,
    scan_started_at: str,
    scan_completed_at: str,
    declared_source_count: int,
    completed_source_count: int,
    reason_code: str = "NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE",
) -> E6ProductionNewsEvidenceV1:
    return _build(
        schema_version=E6_PRODUCTION_NEWS_EVIDENCE_SCHEMA_V1,
        policy_version=E6_PRODUCTION_NEWS_EVIDENCE_POLICY_V1,
        candidate_identity_sha256=candidate_identity_sha256,
        scan_scope=OPTIONAL_CONFIGURED_CP10_CAPTURE_SET,
        declared_source_count=declared_source_count,
        completed_source_count=completed_source_count,
        scan_started_at=scan_started_at,
        scan_completed_at=scan_completed_at,
        status=NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE,
        reason_code=reason_code,
        normalized_news_events=(),
        news_risk_object=None,
        publication_capped=True,
        news_escalation_allowed=False,
        global_coverage_claimed=False,
    )


__all__ = (
    "E6_PRODUCTION_NEWS_EVIDENCE_SCHEMA_V1",
    "E6_PRODUCTION_NEWS_EVIDENCE_POLICY_V1",
    "OPTIONAL_CONFIGURED_CP10_CAPTURE_SET",
    "RELEVANT_NEWS_PRESENT",
    "NO_RELEVANT_NEWS_AFTER_COMPLETED_BOUNDED_SCAN",
    "NEWS_SOURCE_UNAVAILABLE_OR_INCOMPLETE",
    "NO_NEWS_SOURCE_CONFIGURED_OPTIONAL_POLICY",
    "E6ProductionNewsEvidenceErrorV1",
    "E6ProductionNewsEvidenceV1",
    "build_e6_production_present_news_evidence_v1",
    "build_e6_production_zero_source_news_evidence_v1",
    "build_e6_production_unavailable_news_evidence_v1",
)
