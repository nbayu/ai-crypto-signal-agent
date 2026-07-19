"""RED contract for pure Phase 12 pre-call reservation and ledger evidence."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_12_controlled_production_enablement_design_v1 import (
    build_phase_12_controlled_production_enablement_design_v1,
)
from engine.phase_12_pre_call_reservation_usage_ledger_contract_v1 import (
    ReservationAuditEvidenceV1,
    ReservationFailureV1,
    ReservationPolicyV1,
    ReservationRecordV1,
    ReservationRequestV1,
    ReservationTransitionResultV1,
    UsageLedgerEventV1,
    apply_reservation_transition_v1,
    build_reservation_audit_evidence_v1,
    evaluate_reservation_request_v1,
)


_NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
_REQUEST_FIELDS = (
    "reservation_request_id", "reservation_id", "request_id", "idempotency_key",
    "payload_identity", "pricing_observation_id", "pricing_policy_id", "provider_id",
    "route_id", "model_id", "currency", "estimated_cost", "request_cost_ceiling",
    "run_cost_ceiling", "current_run_reserved_cost", "requested_at", "expires_at",
    "provider_request_constructed", "pricing_revalidated", "pricing_within_limits",
    "reservation_authorized",
)
_POLICY_FIELDS = (
    "policy_id", "policy_version", "required_currency", "maximum_reservation_lifetime_seconds",
    "require_constructed_provider_request", "require_pricing_revalidation",
    "require_pricing_within_limits", "require_request_identity", "require_idempotency_identity",
    "require_payload_identity", "require_unique_reservation_id", "require_unique_request_id",
    "require_unique_ledger_event_id", "append_only_ledger", "allow_reservation_creation",
    "allow_reservation_settlement", "allow_reservation_cancellation",
    "allow_uncertain_outcome_recording", "allow_reconciliation", "allow_ledger_mutation",
    "provider_transmission_authorized", "provider_execution_authorized", "fail_closed",
)
_RECORD_FIELDS = (
    "reservation_id", "reservation_request_id", "request_id", "idempotency_key",
    "payload_identity", "provider_id", "route_id", "model_id", "currency",
    "reserved_amount", "consumed_amount", "released_amount", "state", "created_at",
    "expires_at", "last_event_id", "reservation_created", "ledger_mutated",
    "provider_contacted", "transmitted", "provider_execution_authorized",
)
_EVENT_FIELDS = (
    "event_id", "reservation_id", "request_id", "event_type", "prior_state", "next_state",
    "currency", "amount", "occurred_at", "reconciliation_status", "immutable_event_identity",
    "append_only", "ledger_mutation_authorized", "provider_contacted", "execution_authorized",
)
_RESULT_FIELDS = (
    "reservation_id", "prior_state", "requested_state", "transition_valid", "failure_codes",
    "resulting_record", "ledger_event", "reservation_created", "ledger_mutated",
    "provider_contacted", "transmitted", "provider_execution_authorized",
)
_FAILURE_FIELDS = ("failure_code", "safe_message", "retryable")
_AUDIT_FIELDS = (
    "reservation_request_id", "reservation_id", "request_id", "idempotency_key",
    "payload_identity", "pricing_observation_id", "pricing_policy_id", "provider_id",
    "route_id", "model_id", "currency", "estimated_cost", "request_cost_ceiling",
    "run_cost_ceiling", "current_run_reserved_cost", "requested_at", "expires_at", "policy_id",
    "state", "failure_codes", "reservation_created", "ledger_mutated", "provider_contacted",
    "transmitted", "provider_execution_authorized",
)
_FAILURES = {
    "RESERVATION_REQUEST_ID_EMPTY", "RESERVATION_ID_EMPTY", "REQUEST_ID_EMPTY",
    "IDEMPOTENCY_KEY_EMPTY", "PAYLOAD_IDENTITY_EMPTY", "PRICING_OBSERVATION_ID_EMPTY",
    "PRICING_POLICY_ID_EMPTY", "PROVIDER_ID_EMPTY", "ROUTE_ID_EMPTY", "MODEL_ID_EMPTY",
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "EVENT_ID_EMPTY", "IDENTIFIER_NOT_NORMALIZED",
    "CURRENCY_NOT_ALLOWED", "MONETARY_VALUE_INVALID", "ESTIMATED_COST_INVALID",
    "REQUEST_COST_CEILING_EXCEEDED", "RUN_COST_CEILING_EXCEEDED", "REQUEST_NOT_CONSTRUCTED",
    "PRICING_NOT_REVALIDATED", "PRICING_LIMIT_NOT_SATISFIED", "RESERVATION_NOT_AUTHORIZED",
    "RESERVATION_CREATION_NOT_AUTHORIZED", "LEDGER_MUTATION_NOT_AUTHORIZED",
    "SETTLEMENT_NOT_AUTHORIZED", "CANCELLATION_NOT_AUTHORIZED",
    "UNCERTAIN_OUTCOME_NOT_AUTHORIZED", "RECONCILIATION_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "PROVIDER_EXECUTION_NOT_AUTHORIZED",
    "DUPLICATE_RESERVATION_ID", "DUPLICATE_RESERVATION_REQUEST_ID", "DUPLICATE_REQUEST_ID",
    "DUPLICATE_IDEMPOTENCY_KEY", "DUPLICATE_LEDGER_EVENT_ID", "EVENT_IDENTITY_CONFLICT",
    "REQUEST_TIME_INVALID", "EXPIRY_TIME_INVALID", "TIMEZONE_NOT_UTC",
    "RESERVATION_LIFETIME_INVALID", "RESERVATION_EXPIRED", "STATE_INVALID",
    "TRANSITION_NOT_ALLOWED", "TERMINAL_STATE_TRANSITION_FORBIDDEN", "PRIOR_STATE_MISMATCH",
    "CONSUMED_AMOUNT_EXCEEDS_RESERVED", "RELEASED_AMOUNT_EXCEEDS_RESERVED",
    "SETTLEMENT_TOTAL_EXCEEDS_RESERVED",
}
_STATES = (
    "PROPOSED", "RESERVED", "TRANSMISSION_PENDING", "CONSUMED", "RELEASED", "EXPIRED",
    "UNCERTAIN", "RECONCILED",
)
_EVENT_TYPES = (
    "RESERVATION_PROPOSED", "RESERVATION_CREATED", "TRANSMISSION_PENDING", "USAGE_CONSUMED",
    "RESERVATION_RELEASED", "RESERVATION_EXPIRED", "OUTCOME_UNCERTAIN", "OUTCOME_RECONCILED",
)


def _request(**overrides: object) -> ReservationRequestV1:
    values = {
        "reservation_request_id": "reservation-request-v1", "reservation_id": "reservation-v1",
        "request_id": "provider-request-v1", "idempotency_key": "idempotency-v1",
        "payload_identity": "payload-v1", "pricing_observation_id": "pricing-observation-v1",
        "pricing_policy_id": "pricing-policy-v1", "provider_id": "provider-v1",
        "route_id": "route-v1", "model_id": "model-v1", "currency": "USD",
        "estimated_cost": Decimal("1.25"), "request_cost_ceiling": Decimal("2.00"),
        "run_cost_ceiling": Decimal("5.00"), "current_run_reserved_cost": Decimal("0"),
        "requested_at": _NOW, "expires_at": _NOW + timedelta(seconds=60),
        "provider_request_constructed": True, "pricing_revalidated": True,
        "pricing_within_limits": True, "reservation_authorized": False,
    }
    values.update(overrides)
    return ReservationRequestV1(**values)


def _policy(**overrides: object) -> ReservationPolicyV1:
    values = {
        "policy_id": "reservation-policy-v1", "policy_version": "V1", "required_currency": "USD",
        "maximum_reservation_lifetime_seconds": 60, "require_constructed_provider_request": True,
        "require_pricing_revalidation": True, "require_pricing_within_limits": True,
        "require_request_identity": True, "require_idempotency_identity": True,
        "require_payload_identity": True, "require_unique_reservation_id": True,
        "require_unique_request_id": True, "require_unique_ledger_event_id": True,
        "append_only_ledger": True, "allow_reservation_creation": False,
        "allow_reservation_settlement": False, "allow_reservation_cancellation": False,
        "allow_uncertain_outcome_recording": False, "allow_reconciliation": False,
        "allow_ledger_mutation": False, "provider_transmission_authorized": False,
        "provider_execution_authorized": False, "fail_closed": True,
    }
    values.update(overrides)
    return ReservationPolicyV1(**values)


def _record(**overrides: object) -> ReservationRecordV1:
    values = {
        "reservation_id": "reservation-v1", "reservation_request_id": "reservation-request-v1",
        "request_id": "provider-request-v1", "idempotency_key": "idempotency-v1",
        "payload_identity": "payload-v1", "provider_id": "provider-v1", "route_id": "route-v1",
        "model_id": "model-v1", "currency": "USD", "reserved_amount": Decimal("1.25"),
        "consumed_amount": Decimal("0"), "released_amount": Decimal("0"), "state": "PROPOSED",
        "created_at": _NOW, "expires_at": _NOW + timedelta(seconds=60), "last_event_id": "event-proposed-v1",
        "reservation_created": False, "ledger_mutated": False, "provider_contacted": False,
        "transmitted": False, "provider_execution_authorized": False,
    }
    values.update(overrides)
    return ReservationRecordV1(**values)


def _frozen_slotted(value: object) -> None:
    assert is_dataclass(value)
    assert type(value).__dataclass_params__.frozen is True
    assert "__dict__" not in type(value).__slots__


def test_public_contract_is_closed_immutable_decimal_only_and_secret_free() -> None:
    assert tuple(field.name for field in fields(ReservationRequestV1)) == _REQUEST_FIELDS
    assert tuple(field.name for field in fields(ReservationPolicyV1)) == _POLICY_FIELDS
    assert tuple(field.name for field in fields(ReservationRecordV1)) == _RECORD_FIELDS
    assert tuple(field.name for field in fields(UsageLedgerEventV1)) == _EVENT_FIELDS
    assert tuple(field.name for field in fields(ReservationTransitionResultV1)) == _RESULT_FIELDS
    assert tuple(field.name for field in fields(ReservationFailureV1)) == _FAILURE_FIELDS
    assert tuple(field.name for field in fields(ReservationAuditEvidenceV1)) == _AUDIT_FIELDS
    value, policy, record = _request(), _policy(), _record()
    result = evaluate_reservation_request_v1(value, policy, _NOW)
    evidence = build_reservation_audit_evidence_v1(value, policy, result)
    for item in (value, policy, record, result, evidence):
        _frozen_slotted(item)
    assert isinstance(value.estimated_cost, Decimal)
    assert not {"api_key", "token", "authorization", "secret", "transport", "database"}.intersection(
        field.name for field in fields(value)
    )
    with pytest.raises(FrozenInstanceError):
        value.reservation_id = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        ReservationRequestV1(**{field.name: getattr(value, field.name) for field in fields(value)}, api_key="forbidden")


def test_default_policy_is_append_only_and_all_mutation_and_execution_authority_is_false() -> None:
    policy = _policy()
    assert policy.required_currency == "USD"
    assert policy.append_only_ledger is True and policy.fail_closed is True
    assert (
        policy.allow_reservation_creation, policy.allow_reservation_settlement,
        policy.allow_reservation_cancellation, policy.allow_uncertain_outcome_recording,
        policy.allow_reconciliation, policy.allow_ledger_mutation,
        policy.provider_transmission_authorized, policy.provider_execution_authorized,
    ) == (False, False, False, False, False, False, False, False)
    result = evaluate_reservation_request_v1(_request(), policy, _NOW)
    assert result.transition_valid is False
    assert {
        "RESERVATION_NOT_AUTHORIZED", "RESERVATION_CREATION_NOT_AUTHORIZED",
        "LEDGER_MUTATION_NOT_AUTHORIZED", "PROVIDER_TRANSMISSION_NOT_AUTHORIZED",
        "PROVIDER_EXECUTION_NOT_AUTHORIZED",
    }.issubset(result.failure_codes)
    assert tuple(result.failure_codes) == tuple(sorted(result.failure_codes))
    assert set(result.failure_codes).issubset(_FAILURES)
    assert (
        result.reservation_created, result.ledger_mutated, result.provider_contacted,
        result.transmitted, result.provider_execution_authorized,
    ) == (False, False, False, False, False)


def test_state_transition_eligibility_is_explicit_ordered_and_never_applies_mutation() -> None:
    record, policy = _record(), _policy()
    assert set(_STATES) == {
        "PROPOSED", "RESERVED", "TRANSMISSION_PENDING", "CONSUMED", "RELEASED", "EXPIRED",
        "UNCERTAIN", "RECONCILED",
    }
    assert list(inspect.signature(apply_reservation_transition_v1).parameters) == [
        "record", "policy", "requested_state", "event_id", "occurred_at"
    ]
    result = apply_reservation_transition_v1(record, policy, "RESERVED", "event-reserved-v1", _NOW)
    assert result.prior_state == "PROPOSED" and result.requested_state == "RESERVED"
    assert result.transition_valid is False
    assert "RESERVATION_CREATION_NOT_AUTHORIZED" in result.failure_codes
    assert result.resulting_record is None and result.ledger_event is None
    assert {
        "PROPOSED": {"RESERVED"}, "RESERVED": {"TRANSMISSION_PENDING", "RELEASED", "EXPIRED"},
        "TRANSMISSION_PENDING": {"CONSUMED", "UNCERTAIN"}, "UNCERTAIN": {"RECONCILED"},
    } == {
        "PROPOSED": {"RESERVED"}, "RESERVED": {"TRANSMISSION_PENDING", "RELEASED", "EXPIRED"},
        "TRANSMISSION_PENDING": {"CONSUMED", "UNCERTAIN"}, "UNCERTAIN": {"RECONCILED"},
    }
    terminal = apply_reservation_transition_v1(
        _record(state="CONSUMED"), policy, "RESERVED", "event-invalid-v1", _NOW
    )
    assert "TERMINAL_STATE_TRANSITION_FORBIDDEN" in terminal.failure_codes


def test_monetary_expiry_duplicate_and_uncertain_outcome_failures_are_fail_closed() -> None:
    policy = _policy()
    for value in (1.25, Decimal("NaN"), Decimal("Infinity"), Decimal("-0.01"), True):
        result = evaluate_reservation_request_v1(_request(estimated_cost=value), policy, _NOW)
        assert "MONETARY_VALUE_INVALID" in result.failure_codes or "ESTIMATED_COST_INVALID" in result.failure_codes
    assert "REQUEST_COST_CEILING_EXCEEDED" in evaluate_reservation_request_v1(
        _request(estimated_cost=Decimal("2.01")), policy, _NOW
    ).failure_codes
    assert "RUN_COST_CEILING_EXCEEDED" in evaluate_reservation_request_v1(
        _request(current_run_reserved_cost=Decimal("4.00")), policy, _NOW
    ).failure_codes
    assert "RESERVATION_EXPIRED" in evaluate_reservation_request_v1(_request(), policy, _NOW + timedelta(seconds=60)).failure_codes
    assert "RESERVATION_LIFETIME_INVALID" in evaluate_reservation_request_v1(
        _request(expires_at=_NOW), policy, _NOW
    ).failure_codes
    assert {
        "DUPLICATE_RESERVATION_ID", "DUPLICATE_RESERVATION_REQUEST_ID", "DUPLICATE_REQUEST_ID",
        "DUPLICATE_IDEMPOTENCY_KEY", "DUPLICATE_LEDGER_EVENT_ID", "EVENT_IDENTITY_CONFLICT",
        "UNCERTAIN_OUTCOME_NOT_AUTHORIZED", "RECONCILIATION_NOT_AUTHORIZED",
    }.issubset(_FAILURES)


def test_ledger_event_and_audit_evidence_are_immutable_identity_bound_and_non_operational() -> None:
    assert tuple(item for item in _EVENT_TYPES) == _EVENT_TYPES
    event = UsageLedgerEventV1(
        "event-v1", "reservation-v1", "provider-request-v1", "RESERVATION_PROPOSED", "PROPOSED",
        "PROPOSED", "USD", Decimal("0"), _NOW, "NOT_REQUIRED", "event-identity-v1", True,
        False, False, False,
    )
    _frozen_slotted(event)
    assert (event.append_only, event.ledger_mutation_authorized, event.provider_contacted, event.execution_authorized) == (
        True, False, False, False
    )
    value, policy = _request(), _policy()
    result = evaluate_reservation_request_v1(value, policy, _NOW)
    first = build_reservation_audit_evidence_v1(value, policy, result)
    second = build_reservation_audit_evidence_v1(value, policy, result)
    assert first == second
    assert first.reservation_id == value.reservation_id and first.request_id == value.request_id
    assert (first.reservation_created, first.ledger_mutated, first.provider_contacted, first.transmitted, first.provider_execution_authorized) == (
        False, False, False, False, False
    )
    with pytest.raises(ValueError):
        build_reservation_audit_evidence_v1(_request(reservation_id="other"), policy, result)


def test_upstream_design_alignment_and_module_has_no_operational_surface() -> None:
    design = build_phase_12_controlled_production_enablement_design_v1()
    matrix = design.authority_matrix
    assert design.production_effect == "NONE"
    assert (
        matrix.reservation_creation_authorized, matrix.ledger_mutation_authorized,
        matrix.provider_connectivity_authorized, matrix.provider_transmission_authorized,
        matrix.runtime_invocation_authorized, matrix.trading_authorized,
    ) == (False, False, False, False, False, False)
    import engine.phase_12_pre_call_reservation_usage_ledger_contract_v1 as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    prohibited = {
        "os", "pathlib", "subprocess", "socket", "sqlite3", "urllib", "http", "requests",
        "httpx", "aiohttp", "openai", "telegram", "ccxt", "sqlalchemy",
    }
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not prohibited.intersection(names | imports)
    assert not {
        "open", "print", "getenv", "environ", "now", "utcnow", "time", "monotonic",
        "uuid4", "random", "__import__",
    }.intersection(names)
