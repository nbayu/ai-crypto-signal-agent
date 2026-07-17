"""RED contract specification for the first Phase 11 runtime slice.

The implementation is intentionally absent in this step.  These tests define
the public immutable contracts for approved captures, detached Phase 09
projections, shadow inputs, and sample plans.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.phase_11_shadow_input_contracts_v1 import (
    ApprovedNewsCaptureV1,
    Phase09ControlProjectionV1,
    ShadowEvaluationInputV1,
    ShadowSamplePlanV1,
)


IMPLEMENTATION_MODULE = "engine.phase_11_shadow_input_contracts_v1"
UTC = timezone.utc
EVENT_CLASSES = (
    "CLEAN_ROUTINE",
    "MODERATE_AMBIGUITY",
    "CRITICAL_AMBIGUITY",
    "SOURCE_DISAGREEMENT",
    "MAPPING_AMBIGUITY",
    "EXPLOIT_SECURITY",
    "DELISTING",
    "LEGAL_REGULATORY",
    "SOLVENCY_EXCHANGE_RISK",
    "SUSPECTED_MANIPULATION",
    "SYSTEMIC_CROSS_MARKET",
    "MALFORMED_PROVIDER_OUTPUT",
    "TIMEOUT_OUTAGE",
    "BUDGET_EXHAUSTION",
    "DUPLICATE_UPDATE_LINEAGE",
    "PROMPT_INJECTION_ADVERSARIAL",
)
CAPTURE_CLASSIFICATIONS = ("FIXTURE", "RECORDED_LIVE_CAPTURE")
CONTENT_ORIGINS = ("SYNTHETIC_FIXTURE", "RECORDED_SOURCE")
DISPOSITIONS = ("PUBLISHED_SIGNAL", "NO_TRADE")
PLAN_STATUSES = ("DRAFT", "APPROVED", "ACTIVE", "CLOSED", "STOPPED")
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "requests", "httpx", "urllib", "socket", "subprocess", "dotenv",
        "telegram", "ccxt", "master_engine_v4", "production_signal_service_v1",
        "telegram_sdk_runner_v4", "deepseek_validator_v4",
    }
)
FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "account", "account_id", "balance", "position", "position_id", "capital",
        "exchange", "exchange_id", "order", "order_id", "trading", "api_key",
        "credential", "credentials", "transport", "provider_transport", "telegram",
        "publication", "production_signal", "quota",
    }
)


def _canonical_bytes(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value):
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _authority_payload(payload):
    if isinstance(payload, dict):
        return {
            key: _authority_payload(value)
            for key, value in payload.items()
            if key not in {"provider_explanation", "provider_prose", "free_form_provider_prose"}
        }
    if isinstance(payload, (list, tuple)):
        return [_authority_payload(value) for value in payload]
    return payload


def _capture_identity(values):
    material = {
        key: _authority_payload(value)
        for key, value in values.items()
        if key not in {"capture_id", "normalized_payload_hash"}
    }
    return _sha(material)


def _utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _payload():
    return {
        "event_class": "CLEAN_ROUTINE",
        "headline": "A bounded event fixture",
        "facts": {"material": False, "entities": ["entity-alpha"]},
    }


def _lineage():
    return (
        {
            "event_id": "event-001",
            "event_version": 1,
            "relation": "ORIGIN",
        },
    )


def _capture_values(**overrides):
    payload = _payload()
    values = {
        "schema_version": "approved-news-capture-v1",
        "event_id": "event-001",
        "event_version": 1,
        "source_id": "source-001",
        "source_type": "REGULATED_FEED",
        "source_timestamp": "2026-07-17T00:00:00Z",
        "captured_at": "2026-07-17T00:01:00Z",
        "point_in_time_cutoff": "2026-07-17T00:02:00Z",
        "normalized_payload": payload,
        "normalized_payload_hash": _sha(payload),
        "event_lineage": _lineage(),
        "capture_classification": "FIXTURE",
        "content_origin": "SYNTHETIC_FIXTURE",
        "evidence_refs": ("evidence-001",),
    }
    values.update(overrides)
    if "capture_id" not in overrides:
        values["capture_id"] = _capture_identity(values)
    return values


def _capture(**overrides):
    return ApprovedNewsCaptureV1(**_capture_values(**overrides))


def _projection_values(**overrides):
    values = {
        "schema_version": "phase09-control-projection-v1",
        "projection_id": "projection-001",
        "production_evaluation_id": "evaluation-001",
        "event_id": "event-001",
        "candidate_id": "candidate-001",
        "disposition": "NO_TRADE",
        "reason_codes": ("NO_ELIGIBLE_SETUP",),
        "evidence_refs": ("control-evidence-001",),
        "evaluated_at": "2026-07-17T00:03:00Z",
        "source_artifact_hash": "a" * 64,
    }
    values.update(overrides)
    return values


def _projection(**overrides):
    return Phase09ControlProjectionV1(**_projection_values(**overrides))


def _plan_values(**overrides):
    values = {
        "schema_version": "shadow-sample-plan-v1",
        "sample_plan_id": "sample-plan-001",
        "plan_version": 1,
        "status": "DRAFT",
        "event_class_targets": {event_class: 1 for event_class in EVENT_CLASSES},
        "minimum_l1_count": 1,
        "minimum_l2_count": 1,
        "maximum_total_samples": 32,
        "maximum_live_samples": 0,
        "allowed_capture_classifications": ("FIXTURE",),
        "stop_conditions": (
            "BUDGET_HARD_STOP",
            "CRITICAL_AUTHORITY_FAILURE",
            "MAXIMUM_SAMPLE_COUNT",
        ),
        "starts_at": "2026-07-17T01:00:00Z",
        "ends_at": "2026-07-18T01:00:00Z",
        "owner_approval_reference": None,
    }
    values.update(overrides)
    return values


def _plan(**overrides):
    return ShadowSamplePlanV1(**_plan_values(**overrides))


def _shadow_values(**overrides):
    values = {
        "schema_version": "shadow-evaluation-input-v1",
        "shadow_input_id": "shadow-input-001",
        "approved_news_capture": _capture(),
        "phase_09_control_projection": _projection(),
        "sample_plan_id": "sample-plan-001",
        "policy_version": "phase11-policy-v1",
        "created_at": "2026-07-17T00:04:00Z",
    }
    values.update(overrides)
    return values


def _shadow(**overrides):
    return ShadowEvaluationInputV1(**_shadow_values(**overrides))


def _identity(value):
    for name in ("identity", "object_id", "capture_id", "projection_id", "shadow_input_id", "sample_plan_id"):
        if hasattr(value, name):
            return getattr(value, name)
    raise AssertionError("contract exposes no identity property")


def _assert_rejected(factory, **changes):
    with pytest.raises((TypeError, ValueError)):
        factory(**changes)


class TestApprovedNewsCaptureV1:
    def test_positive_construction_and_immutability(self):
        value = _capture()
        assert value.event_id == "event-001"
        with pytest.raises((AttributeError, TypeError)):
            value.event_id = "event-002"

    def test_unknown_and_missing_fields_are_rejected(self):
        values = _capture_values(unknown_field="reject")
        _assert_rejected(ApprovedNewsCaptureV1, **values)
        values = _capture_values()
        del values["source_id"]
        _assert_rejected(ApprovedNewsCaptureV1, **values)

    @pytest.mark.parametrize(
        "field",
        [
            "capture_id",
            "event_id",
            "source_id",
            "source_type",
        ],
    )
    def test_identifiers_must_not_be_blank(self, field):
        _assert_rejected(ApprovedNewsCaptureV1, **_capture_values(**{field: "  "}))

    @pytest.mark.parametrize(
        "field",
        ["source_timestamp", "captured_at", "point_in_time_cutoff"],
    )
    def test_timestamps_are_canonical_utc(self, field):
        for value in ("2026-07-17T00:00:00", "2026-07-17 00:00:00Z", "not-a-time"):
            _assert_rejected(ApprovedNewsCaptureV1, **_capture_values(**{field: value}))
        value = _capture()
        assert value.source_timestamp.endswith("Z")
        assert _utc(value.captured_at).tzinfo is UTC

    def test_source_capture_and_cutoff_order_is_fail_closed(self):
        _assert_rejected(
            ApprovedNewsCaptureV1,
            **_capture_values(
                source_timestamp="2026-07-17T00:02:00Z",
                captured_at="2026-07-17T00:01:00Z",
            ),
        )
        _assert_rejected(
            ApprovedNewsCaptureV1,
            **_capture_values(
                captured_at="2026-07-17T00:03:00Z",
                point_in_time_cutoff="2026-07-17T00:02:00Z",
            ),
        )

    def test_event_version_is_positive(self):
        for version in (0, -1, True, 1.5):
            _assert_rejected(ApprovedNewsCaptureV1, **_capture_values(event_version=version))

    def test_duplicate_lineage_entries_are_rejected(self):
        duplicate = {
            "event_id": "event-001",
            "event_version": 1,
            "relation": "ORIGIN",
        }
        _assert_rejected(
            ApprovedNewsCaptureV1,
            **_capture_values(event_lineage=(duplicate, duplicate)),
        )

    def test_lineage_is_canonicalized_deterministically(self):
        first = _capture(
            event_lineage=(
                {"event_id": "event-002", "event_version": 2, "relation": "UPDATE"},
                {"event_id": "event-001", "event_version": 1, "relation": "ORIGIN"},
            )
        )
        second = _capture(
            event_lineage=(
                {"event_id": "event-001", "event_version": 1, "relation": "ORIGIN"},
                {"event_id": "event-002", "event_version": 2, "relation": "UPDATE"},
            )
        )
        assert first.event_lineage == second.event_lineage
        assert _identity(first) == _identity(second)

    @pytest.mark.parametrize("classification", ("LIVE", "SCRAPED", "", None))
    def test_capture_classification_is_closed(self, classification):
        _assert_rejected(
            ApprovedNewsCaptureV1,
            **_capture_values(capture_classification=classification),
        )

    @pytest.mark.parametrize("origin", ("UNKNOWN", "PROVIDER", "", None))
    def test_content_origin_is_closed(self, origin):
        _assert_rejected(ApprovedNewsCaptureV1, **_capture_values(content_origin=origin))

    def test_payload_hash_must_match_canonical_payload_bytes(self):
        _assert_rejected(
            ApprovedNewsCaptureV1,
            **_capture_values(normalized_payload_hash="0" * 64),
        )

    def test_capture_id_is_lowercase_sha256_of_authoritative_fields(self):
        values = _capture_values()
        assert values["capture_id"] == _capture_identity(values)
        assert len(values["capture_id"]) == 64
        assert values["capture_id"] == values["capture_id"].lower()

    @pytest.mark.parametrize("capture_id", ("capture-001", "A" * 64, "f" * 64))
    def test_capture_id_rejects_noncanonical_or_forged_digest(self, capture_id):
        _assert_rejected(ApprovedNewsCaptureV1, **_capture_values(capture_id=capture_id))

    def test_forged_event_identity_is_rejected(self):
        _assert_rejected(
            ApprovedNewsCaptureV1,
            **_capture_values(event_id="event-forged"),
        )

    def test_equivalent_semantics_converge_and_material_changes_diverge(self):
        first = _capture()
        equivalent = _capture(
            normalized_payload={"facts": {"entities": ["entity-alpha"], "material": False}, "headline": "A bounded event fixture"}
        )
        changed = _capture(normalized_payload={**_payload(), "severity": "MATERIAL"}, normalized_payload_hash=_sha({**_payload(), "severity": "MATERIAL"}))
        assert _identity(first) == _identity(equivalent)
        assert _identity(first) != _identity(changed)

    def test_provider_prose_is_not_authority_identity(self):
        first = _capture()
        second_payload = {**_payload(), "provider_explanation": "publish immediately"}
        second = _capture(
            normalized_payload=second_payload,
            normalized_payload_hash=_sha(second_payload),
        )
        assert _identity(first) == _identity(second)

    @pytest.mark.parametrize(
        "field",
        [
            "production_mutation",
            "publication",
            "telegram",
            "account",
            "balance",
            "position",
            "capital",
            "exchange",
            "order",
            "trading",
            "api_key",
            "credential_material",
            "provider_transport",
        ],
    )
    def test_authority_fields_are_rejected(self, field):
        _assert_rejected(ApprovedNewsCaptureV1, **_capture_values(**{field: "forbidden"}))


class TestPhase09ControlProjectionV1:
    def test_positive_construction_and_immutability(self):
        value = _projection()
        assert value.disposition == "NO_TRADE"
        with pytest.raises((AttributeError, TypeError)):
            value.disposition = "PUBLISHED_SIGNAL"

    @pytest.mark.parametrize("disposition", ("BUY", "SELL", "PUBLISH", "", None))
    def test_disposition_is_limited_to_phase09_control_values(self, disposition):
        _assert_rejected(Phase09ControlProjectionV1, **_projection_values(disposition=disposition))

    @pytest.mark.parametrize(
        "field",
        [
            "strategy_mutation",
            "publication_payload",
            "telegram",
            "account",
            "balance",
            "position",
            "capital",
            "exchange",
            "order",
            "trading",
            "api_key",
            "credential_material",
            "provider_transport",
        ],
    )
    def test_projection_rejects_strategy_and_authority_fields(self, field):
        _assert_rejected(Phase09ControlProjectionV1, **_projection_values(**{field: "forbidden"}))

    def test_reason_codes_and_evidence_refs_are_deterministic_and_bounded(self):
        first = _projection(
            reason_codes=("Z_REASON", "A_REASON", "Z_REASON"),
            evidence_refs=("ref-2", "ref-1", "ref-2"),
        )
        second = _projection(
            reason_codes=("A_REASON", "Z_REASON"),
            evidence_refs=("ref-1", "ref-2"),
        )
        assert first.reason_codes == second.reason_codes
        assert first.evidence_refs == second.evidence_refs
        assert _identity(first) == _identity(second)
        _assert_rejected(
            Phase09ControlProjectionV1,
            **_projection_values(evidence_refs=tuple(f"ref-{i}" for i in range(100))),
        )

    @pytest.mark.parametrize("evaluated_at", ("2026-07-17T00:03:00", "bad", "2026-07-17 00:03:00Z"))
    def test_evaluated_at_is_canonical_utc(self, evaluated_at):
        _assert_rejected(Phase09ControlProjectionV1, **_projection_values(evaluated_at=evaluated_at))

    def test_source_artifact_hash_is_required_and_validated(self):
        for value in (None, "", "not-a-hash", "A" * 64, "a" * 63):
            _assert_rejected(Phase09ControlProjectionV1, **_projection_values(source_artifact_hash=value))

    def test_identity_is_stable_and_diverges_on_material_control_change(self):
        first = _projection()
        equivalent = _projection(
            reason_codes=("NO_ELIGIBLE_SETUP",),
            evidence_refs=("control-evidence-001",),
        )
        changed = _projection(disposition="PUBLISHED_SIGNAL")
        assert _identity(first) == _identity(equivalent)
        assert _identity(first) != _identity(changed)


class TestShadowEvaluationInputV1:
    def test_positive_construction_and_immutability(self):
        value = _shadow()
        assert value.sample_plan_id == "sample-plan-001"
        with pytest.raises((AttributeError, TypeError)):
            value.sample_plan_id = "other-plan"

    def test_children_must_be_exact_valid_contract_instances(self):
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(approved_news_capture=_capture_values()))
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(phase_09_control_projection=_projection_values()))
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(approved_news_capture=None))
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(phase_09_control_projection=None))

    def test_child_identities_are_bound_into_parent_identity(self):
        first = _shadow()
        changed_capture = _capture(source_id="source-002")
        changed = _shadow(approved_news_capture=changed_capture)
        assert _identity(first) != _identity(changed)
        changed_projection = _projection(disposition="PUBLISHED_SIGNAL")
        changed_again = _shadow(phase_09_control_projection=changed_projection)
        assert _identity(first) != _identity(changed_again)

    def test_mismatched_event_binding_is_rejected(self):
        projection = _projection(event_id="event-999")
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(phase_09_control_projection=projection))

    @pytest.mark.parametrize("sample_plan_id", ("", "bad id", "../plan", None))
    def test_sample_plan_id_is_closed(self, sample_plan_id):
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(sample_plan_id=sample_plan_id))

    @pytest.mark.parametrize("policy_version", ("", "latest", "phase10", None))
    def test_policy_version_is_closed(self, policy_version):
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(policy_version=policy_version))

    @pytest.mark.parametrize("created_at", ("2026-07-17T00:04:00", "bad", "2026-07-17 00:04:00Z"))
    def test_created_at_is_canonical_utc(self, created_at):
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(created_at=created_at))

    def test_equivalent_inputs_converge_and_material_child_changes_diverge(self):
        first = _shadow()
        equivalent = _shadow(
            approved_news_capture=_capture(),
            phase_09_control_projection=_projection(),
        )
        changed = _shadow(policy_version="phase11-policy-v2")
        assert _identity(first) == _identity(equivalent)
        assert _identity(first) != _identity(changed)

    @pytest.mark.parametrize(
        "field",
        [
            "production_effect",
            "runtime_authority",
            "publication",
            "telegram",
            "account",
            "balance",
            "position",
            "capital",
            "exchange",
            "order",
            "trading",
            "api_key",
            "credential_material",
            "provider_transport",
        ],
    )
    def test_parent_rejects_production_and_runtime_authority_fields(self, field):
        _assert_rejected(ShadowEvaluationInputV1, **_shadow_values(**{field: "forbidden"}))


class TestShadowSamplePlanV1:
    def test_positive_construction_and_immutability(self):
        value = _plan()
        assert set(value.event_class_targets) == set(EVENT_CLASSES)
        with pytest.raises((AttributeError, TypeError)):
            value.plan_version = 2

    @pytest.mark.parametrize("plan_version", (0, -1, True, 1.5))
    def test_plan_version_is_positive_integer(self, plan_version):
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(plan_version=plan_version))

    @pytest.mark.parametrize("status", ("PROPOSED", "RUNNING", "DONE", "", None))
    def test_status_is_closed(self, status):
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(status=status))

    def test_every_required_event_class_appears_exactly_once(self):
        missing = dict(_plan_values()["event_class_targets"])
        del missing[EVENT_CLASSES[0]]
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(event_class_targets=missing))
        duplicate_pairs = list(_plan_values()["event_class_targets"].items()) + [(EVENT_CLASSES[0], 1)]
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(event_class_targets=duplicate_pairs))

    def test_target_counts_are_nonnegative_integers(self):
        for bad in (-1, True, 1.5, "1"):
            targets = dict(_plan_values()["event_class_targets"])
            targets[EVENT_CLASSES[0]] = bad
            _assert_rejected(ShadowSamplePlanV1, **_plan_values(event_class_targets=targets))

    def test_unknown_event_classes_are_rejected(self):
        targets = dict(_plan_values()["event_class_targets"])
        targets["UNKNOWN_EVENT_CLASS"] = 1
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(event_class_targets=targets))

    def test_totals_and_coverage_limits_are_internally_consistent(self):
        targets = {event_class: 3 for event_class in EVENT_CLASSES}
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(
                event_class_targets=targets,
                maximum_total_samples=10,
            ),
        )
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(minimum_l1_count=33, maximum_total_samples=32),
        )
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(minimum_l2_count=33, maximum_total_samples=32),
        )
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(maximum_live_samples=33, maximum_total_samples=32),
        )

    @pytest.mark.parametrize("field", ("starts_at", "ends_at"))
    def test_plan_timestamps_are_canonical_utc(self, field):
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(**{field: "2026-07-17T01:00:00"}))

    def test_end_is_later_than_start(self):
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(
                starts_at="2026-07-18T01:00:00Z",
                ends_at="2026-07-17T01:00:00Z",
            ),
        )

    def test_stop_conditions_are_bounded_and_deterministic(self):
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(stop_conditions=()))
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(stop_conditions=("wait forever",)))
        first = _plan(stop_conditions=("MAXIMUM_SAMPLE_COUNT", "BUDGET_HARD_STOP"))
        second = _plan(stop_conditions=("BUDGET_HARD_STOP", "MAXIMUM_SAMPLE_COUNT"))
        assert first.stop_conditions == second.stop_conditions
        assert _identity(first) == _identity(second)

    def test_approval_is_required_for_approved_or_live_capable_plan(self):
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(status="APPROVED", owner_approval_reference=None),
        )
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(maximum_live_samples=1, owner_approval_reference=None),
        )
        draft = _plan(status="DRAFT", maximum_live_samples=0)
        assert draft.owner_approval_reference is None

    def test_allowed_capture_classifications_are_closed(self):
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(allowed_capture_classifications=("SCRAPED",)),
        )
        _assert_rejected(
            ShadowSamplePlanV1,
            **_plan_values(allowed_capture_classifications=("FIXTURE", "FIXTURE")),
        )

    def test_identity_is_deterministic_and_material_changes_diverge(self):
        first = _plan()
        equivalent = _plan(
            event_class_targets=dict(_plan_values()["event_class_targets"]),
            stop_conditions=(
                "MAXIMUM_SAMPLE_COUNT",
                "CRITICAL_AUTHORITY_FAILURE",
                "BUDGET_HARD_STOP",
            ),
        )
        changed_target = dict(_plan_values()["event_class_targets"])
        changed_target["CRITICAL_AMBIGUITY"] = 2
        changed = _plan(event_class_targets=changed_target)
        assert _identity(first) == _identity(equivalent)
        assert _identity(first) != _identity(changed)
        assert _identity(first) != _identity(_plan(plan_version=2))
        assert _identity(first) != _identity(_plan(status="STOPPED"))
        assert _identity(first) != _identity(_plan(ends_at="2026-07-19T01:00:00Z"))

    @pytest.mark.parametrize(
        "field",
        [
            "production_mutation",
            "publication",
            "telegram",
            "account",
            "balance",
            "position",
            "capital",
            "exchange",
            "order",
            "trading",
            "api_key",
            "credential_material",
            "provider_transport",
        ],
    )
    def test_plan_rejects_authority_fields(self, field):
        _assert_rejected(ShadowSamplePlanV1, **_plan_values(**{field: "forbidden"}))


def test_contract_objects_are_value_equal_when_semantically_equivalent():
    assert _capture() == _capture()
    assert _projection() == _projection()
    assert _shadow() == _shadow()
    assert _plan() == _plan()


def test_contract_objects_do_not_expose_provider_transport_callables():
    for contract in (_capture(), _projection(), _shadow(), _plan()):
        fields = set(vars(contract)) if hasattr(contract, "__dict__") else set()
        assert not any("transport" in field.casefold() for field in fields)
        assert not any(callable(value) for value in fields.values()) if isinstance(fields, dict) else True


def test_implementation_has_only_allowed_deterministic_dependencies():
    module = __import__(IMPLEMENTATION_MODULE, fromlist=["*"])
    source = inspect.getsource(module)
    tree = ast.parse(source)
    allowed_roots = {
        "__future__",
        "ast",
        "dataclasses",
        "datetime",
        "enum",
        "hashlib",
        "json",
        "re",
        "types",
        "typing",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed_roots
                assert alias.name.split(".")[0] not in FORBIDDEN_IMPORT_ROOTS
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root in allowed_roots
            assert root not in FORBIDDEN_IMPORT_ROOTS


def _ast_identifier_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _ast_dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def test_implementation_source_has_no_runtime_authority_references():
    module = __import__(IMPLEMENTATION_MODULE, fromlist=["*"])
    tree = ast.parse(inspect.getsource(module))
    identifiers = _ast_identifier_names(tree)
    assert not (identifiers & FORBIDDEN_IDENTIFIERS)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            dotted = _ast_dotted_name(node)
            assert dotted not in {"os.environ", "os.getenv"}
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            assert all(alias.name != "getenv" for alias in node.names)
        elif isinstance(node, ast.Call):
            name = _ast_dotted_name(node.func) or (node.func.id if isinstance(node.func, ast.Name) else None)
            assert name not in {"getenv", "load_dotenv", "dotenv_values"}


def test_no_phase11_implementation_module_exists_in_this_red_slice():
    path = Path(__file__).parents[1] / "engine" / "phase_11_shadow_input_contracts_v1.py"
    assert not path.exists(), "RED slice must not create the implementation module"
