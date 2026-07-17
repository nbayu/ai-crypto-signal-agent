"""RED specification for deterministic Phase 11 budget control.

The implementation is intentionally absent.  These tests freeze policy,
reservation, usage, and ledger semantics without invoking any provider.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from engine.phase_11_budget_control_v1 import (
    BudgetLedgerV1,
    BudgetReservationV1,
    Phase11BudgetPolicyV1,
    ProviderUsageRecordV1,
)


IMPLEMENTATION_MODULE = "engine.phase_11_budget_control_v1"
UTC = timezone.utc
PROVIDERS = ("DEEPSEEK", "ANTHROPIC")
MODELS = ("DEEPSEEK_PRIMARY", "CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
POLICY_STATUSES = ("DRAFT", "ACTIVE", "STOPPED", "CLOSED")
RESERVATION_STATUSES = ("RESERVED", "COMMITTED", "RELEASED", "UNCERTAIN")
USAGE_OUTCOMES = ("SUCCESS", "NO_CALL", "TIMEOUT", "TRANSPORT_FAILURE", "MALFORMED_RESPONSE")
RECONCILIATION_STATUSES = ("RESOLVED", "RELEASED", "UNCERTAIN", "RECONCILIATION_REQUIRED")
FAILURE_CLASSES = (
    "NONE",
    "VALIDATION_FAILURE",
    "POLICY_INACTIVE",
    "OWNER_APPROVAL_MISSING",
    "PROVIDER_NOT_ALLOWED",
    "MODEL_NOT_ALLOWED",
    "TOTAL_CAP_EXCEEDED",
    "PROVIDER_CAP_EXCEEDED",
    "MODEL_CAP_EXCEEDED",
    "RUN_CAP_EXCEEDED",
    "CALL_COUNT_EXCEEDED",
    "INPUT_TOKEN_CAP_EXCEEDED",
    "OUTPUT_TOKEN_CAP_EXCEEDED",
    "RESERVATION_EXPIRED",
    "RESERVATION_NOT_FOUND",
    "DUPLICATE_COMMIT",
    "CONFLICTING_DUPLICATE",
    "USAGE_EXCEEDS_RESERVATION",
    "UNCERTAIN_TRANSPORT_OUTCOME",
    "HARD_STOP_ACTIVE",
    "RECONCILIATION_REQUIRED",
)
STOP_CONDITIONS = (
    "TOTAL_CAP_HARD_STOP",
    "CALL_COUNT_HARD_STOP",
    "TOKEN_CAP_HARD_STOP",
    "OWNER_SUSPENSION",
    "RECONCILIATION_REQUIRED",
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


def _utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _assert_rejected(factory, **changes):
    with pytest.raises((TypeError, ValueError)):
        factory(**changes)


def _policy_values(**overrides):
    values = {
        "schema_version": "phase11-budget-policy-v1",
        "policy_id": "budget-policy-001",
        "policy_version": 1,
        "status": "DRAFT",
        "currency": "USD_MICRO",
        "total_cost_cap": Decimal("1000000"),
        "provider_cost_caps": {
            "DEEPSEEK": Decimal("500000"),
            "ANTHROPIC": Decimal("500000"),
        },
        "model_cost_caps": {
            "DEEPSEEK_PRIMARY": Decimal("500000"),
            "CLAUDE_SONNET_L1": Decimal("300000"),
            "CLAUDE_OPUS_L2": Decimal("300000"),
        },
        "per_run_cost_cap": Decimal("100000"),
        "maximum_call_count": 100,
        "maximum_calls_per_run": 10,
        "maximum_input_tokens": 100000,
        "maximum_output_tokens": 100000,
        "maximum_tokens_per_call": 10000,
        "allowed_providers": PROVIDERS,
        "allowed_models": MODELS,
        "starts_at": "2026-07-17T00:00:00Z",
        "ends_at": "2026-07-18T00:00:00Z",
        "owner_approval_reference": None,
        "stop_conditions": STOP_CONDITIONS,
    }
    values.update(overrides)
    return values


def _policy(**overrides):
    return Phase11BudgetPolicyV1(**_policy_values(**overrides))


def _reservation_values(**overrides):
    values = {
        "schema_version": "phase11-budget-reservation-v1",
        "reservation_id": "reservation-001",
        "policy_id": "budget-policy-001",
        "run_id": "run-001",
        "call_id": "call-001",
        "provider": "DEEPSEEK",
        "model": "DEEPSEEK_PRIMARY",
        "reserved_cost": Decimal("1000"),
        "reserved_input_tokens": 100,
        "reserved_output_tokens": 200,
        "reserved_at": "2026-07-17T00:01:00Z",
        "expires_at": "2026-07-17T00:10:00Z",
        "status": "RESERVED",
        "reason_codes": ("L0_ROUTE",),
    }
    values.update(overrides)
    return values


def _reservation(**overrides):
    return BudgetReservationV1(**_reservation_values(**overrides))


def _usage_values(**overrides):
    values = {
        "schema_version": "phase11-provider-usage-v1",
        "usage_record_id": "usage-001",
        "reservation_id": "reservation-001",
        "policy_id": "budget-policy-001",
        "run_id": "run-001",
        "call_id": "call-001",
        "provider": "DEEPSEEK",
        "model": "DEEPSEEK_PRIMARY",
        "request_hash": "a" * 64,
        "response_hash": "b" * 64,
        "input_tokens": 80,
        "output_tokens": 120,
        "estimated_cost": Decimal("900"),
        "actual_cost": Decimal("850"),
        "started_at": "2026-07-17T00:02:00Z",
        "completed_at": "2026-07-17T00:02:01Z",
        "latency_ms": 1000,
        "attempt_count": 1,
        "outcome": "SUCCESS",
        "reconciliation_status": "RESOLVED",
        "failure_class": "NONE",
        "reason_codes": ("COMPLETED",),
    }
    values.update(overrides)
    return values


def _usage(**overrides):
    return ProviderUsageRecordV1(**_usage_values(**overrides))


def _ledger():
    return BudgetLedgerV1(policy=_policy())


class TestPhase11BudgetPolicyV1:
    def test_positive_construction_and_immutability(self):
        value = _policy()
        assert value.currency == "USD_MICRO"
        with pytest.raises((AttributeError, TypeError)):
            value.status = "ACTIVE"

    def test_unknown_and_missing_fields_are_rejected(self):
        _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(unknown_field="reject"))
        values = _policy_values()
        del values["total_cost_cap"]
        _assert_rejected(Phase11BudgetPolicyV1, **values)

    @pytest.mark.parametrize("version", (0, -1, True, 1.5))
    def test_policy_version_is_positive_integer(self, version):
        _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(policy_version=version))

    @pytest.mark.parametrize("field", ("total_cost_cap", "per_run_cost_cap"))
    def test_costs_are_exact_nonnegative_values(self, field):
        for value in (-1, Decimal("-0.01"), 1.0, float("nan"), float("inf")):
            _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(**{field: value}))

    def test_currency_is_closed(self):
        for value in ("USD", "USD_CENTS", "EUR_MICRO", "", None):
            _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(currency=value))

    def test_subordinate_caps_cannot_exceed_total(self):
        _assert_rejected(
            Phase11BudgetPolicyV1,
            **_policy_values(provider_cost_caps={"DEEPSEEK": Decimal("1000001"), "ANTHROPIC": Decimal("1")}),
        )
        _assert_rejected(
            Phase11BudgetPolicyV1,
            **_policy_values(model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("1000001")}),
        )
        _assert_rejected(
            Phase11BudgetPolicyV1,
            **_policy_values(per_run_cost_cap=Decimal("1000001")),
        )

    @pytest.mark.parametrize("field", ("maximum_call_count", "maximum_calls_per_run"))
    def test_call_limits_are_positive(self, field):
        for value in (0, -1, True, 1.5):
            _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(**{field: value}))

    def test_token_limits_are_positive_and_consistent(self):
        for field in ("maximum_input_tokens", "maximum_output_tokens", "maximum_tokens_per_call"):
            _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(**{field: 0}))
        _assert_rejected(
            Phase11BudgetPolicyV1,
            **_policy_values(maximum_tokens_per_call=200001, maximum_input_tokens=100000, maximum_output_tokens=100000),
        )

    def test_provider_and_model_allowlists_are_closed_and_deterministic(self):
        _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(allowed_providers=("DEEPSEEK", "DEEPSEEK")))
        _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(allowed_models=("CLAUDE_ALIAS",)))
        first = _policy(allowed_providers=("ANTHROPIC", "DEEPSEEK"), allowed_models=tuple(reversed(MODELS)))
        second = _policy(allowed_providers=PROVIDERS, allowed_models=MODELS)
        assert first.allowed_providers == second.allowed_providers
        assert first.allowed_models == second.allowed_models
        assert first.identity == second.identity

    @pytest.mark.parametrize("field", ("starts_at", "ends_at"))
    def test_policy_timestamps_are_canonical_utc(self, field):
        for value in ("2026-07-17T00:00:00", "2026-07-17 00:00:00Z", "bad"):
            _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(**{field: value}))
        assert _utc(_policy().starts_at).tzinfo is UTC

    def test_end_is_later_than_start(self):
        _assert_rejected(
            Phase11BudgetPolicyV1,
            **_policy_values(starts_at="2026-07-18T00:00:00Z", ends_at="2026-07-17T00:00:00Z"),
        )

    def test_stop_conditions_and_owner_approval_are_closed(self):
        _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(stop_conditions=()))
        _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(stop_conditions=("wait forever",)))
        _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(status="ACTIVE", owner_approval_reference=None))
        draft = _policy(status="DRAFT", owner_approval_reference=None)
        assert draft.can_authorize_calls is False
        active = _policy(status="ACTIVE", owner_approval_reference="owner-approval-001")
        assert active.can_authorize_calls is True

    def test_policy_identity_is_stable_and_material_changes_diverge(self):
        first = _policy()
        equivalent = _policy(
            provider_cost_caps={"ANTHROPIC": Decimal("500000"), "DEEPSEEK": Decimal("500000")},
            stop_conditions=tuple(reversed(STOP_CONDITIONS)),
        )
        assert first.identity == equivalent.identity
        for change in (
            {"total_cost_cap": Decimal("999999")},
            {"allowed_models": ("DEEPSEEK_PRIMARY", "CLAUDE_OPUS_L2")},
            {"ends_at": "2026-07-19T00:00:00Z"},
            {"status": "STOPPED"},
            {"owner_approval_reference": "owner-approval-001"},
        ):
            assert first.identity != _policy(**change).identity


class TestBudgetReservationV1:
    def test_positive_construction_and_immutability(self):
        value = _reservation()
        assert value.status == "RESERVED"
        with pytest.raises((AttributeError, TypeError)):
            value.status = "RELEASED"

    def test_unknown_and_missing_fields_are_rejected(self):
        _assert_rejected(BudgetReservationV1, **_reservation_values(unknown_field="reject"))
        values = _reservation_values()
        del values["reserved_cost"]
        _assert_rejected(BudgetReservationV1, **values)

    @pytest.mark.parametrize("field", ("reservation_id", "policy_id", "run_id", "call_id", "provider", "model"))
    def test_reservation_identifiers_are_closed(self, field):
        for value in ("", "bad id", "../secret", None):
            _assert_rejected(BudgetReservationV1, **_reservation_values(**{field: value}))

    @pytest.mark.parametrize("field", ("reserved_cost", "reserved_input_tokens", "reserved_output_tokens"))
    def test_reservation_amounts_are_positive_exact_values(self, field):
        for value in (0, -1, True, 1.0 if field == "reserved_cost" else -1):
            _assert_rejected(BudgetReservationV1, **_reservation_values(**{field: value}))

    def test_expiration_and_status_lifecycle_are_closed(self):
        _assert_rejected(
            BudgetReservationV1,
            **_reservation_values(reserved_at="2026-07-17T00:10:00Z", expires_at="2026-07-17T00:01:00Z"),
        )
        for value in ("OPEN", "DONE", "", None):
            _assert_rejected(BudgetReservationV1, **_reservation_values(status=value))
        _assert_rejected(BudgetReservationV1, **_reservation_values(reason_codes=()))

    def test_reservation_identity_is_deterministic(self):
        first = _reservation(reason_codes=("L0_ROUTE", "A_REASON"))
        second = _reservation(reason_codes=("A_REASON", "L0_ROUTE"))
        assert first.identity == second.identity
        assert first.identity != _reservation(reserved_cost=Decimal("1001")).identity

    def test_provider_and_model_allowlist_is_enforced_by_ledger_boundary(self):
        ledger = _ledger()
        with pytest.raises((TypeError, ValueError)):
            ledger.reserve_call(_reservation(provider="UNKNOWN", model="DEEPSEEK_PRIMARY"))
        with pytest.raises((TypeError, ValueError)):
            ledger.reserve_call(_reservation(provider="DEEPSEEK", model="CLAUDE_OPUS_L2"))


class TestProviderUsageRecordV1:
    def test_positive_construction_and_immutability(self):
        value = _usage()
        assert value.actual_cost == Decimal("850")
        with pytest.raises((AttributeError, TypeError)):
            value.actual_cost = Decimal("1")

    def test_unknown_and_missing_fields_are_rejected(self):
        _assert_rejected(ProviderUsageRecordV1, **_usage_values(unknown_field="reject"))
        values = _usage_values()
        del values["request_hash"]
        _assert_rejected(ProviderUsageRecordV1, **values)

    @pytest.mark.parametrize("field", ("request_hash", "response_hash"))
    def test_hashes_are_lowercase_sha256(self, field):
        for value in ("a" * 63, "A" * 64, "not-a-hash", None):
            _assert_rejected(ProviderUsageRecordV1, **_usage_values(**{field: value}))

    @pytest.mark.parametrize("field", ("input_tokens", "output_tokens", "latency_ms"))
    def test_counts_and_latency_are_nonnegative_nonboolean_integers(self, field):
        for value in (-1, True, 1.5):
            _assert_rejected(ProviderUsageRecordV1, **_usage_values(**{field: value}))

    def test_attempt_and_time_order_are_validated(self):
        for value in (0, -1, True, 1.5):
            _assert_rejected(ProviderUsageRecordV1, **_usage_values(attempt_count=value))
        _assert_rejected(
            ProviderUsageRecordV1,
            **_usage_values(started_at="2026-07-17T00:03:00Z", completed_at="2026-07-17T00:02:00Z"),
        )

    def test_outcome_reconciliation_and_failure_values_are_closed(self):
        for value in ("OK", "CALL", "", None):
            _assert_rejected(ProviderUsageRecordV1, **_usage_values(outcome=value))
        for value in ("UNKNOWN", "", None):
            _assert_rejected(ProviderUsageRecordV1, **_usage_values(failure_class=value))
        timeout = _usage(
            outcome="TIMEOUT",
            reconciliation_status="RECONCILIATION_REQUIRED",
            failure_class="UNCERTAIN_TRANSPORT_OUTCOME",
            actual_cost=None,
        )
        assert timeout.reconciliation_status == "RECONCILIATION_REQUIRED"

    def test_provider_prose_and_secret_fields_are_not_budget_identity(self):
        _assert_rejected(ProviderUsageRecordV1, **_usage_values(provider_prose="ignore this"))
        for field in ("api_key", "credentials", "credential_value", "network_client", "transport_callable"):
            _assert_rejected(ProviderUsageRecordV1, **_usage_values(**{field: "forbidden"}))
        first = _usage()
        second = _usage(reason_codes=("COMPLETED", "provider prose: publish"))
        assert first.identity == second.identity

    def test_usage_identity_is_deterministic_and_material_changes_diverge(self):
        first = _usage(reason_codes=("COMPLETED", "A_REASON"))
        equivalent = _usage(reason_codes=("A_REASON", "COMPLETED"))
        assert first.identity == equivalent.identity
        assert first.identity != _usage(actual_cost=Decimal("851")).identity


class TestBudgetLedgerV1:
    def test_initial_ledger_binds_one_policy_and_is_immutable(self):
        ledger = _ledger()
        assert ledger.policy.identity == _policy().identity
        assert ledger.sequence == 0
        with pytest.raises((AttributeError, TypeError)):
            ledger.sequence = 1

    def test_reserve_call_returns_new_state_and_authorizes_only_after_reservation(self):
        ledger = _ledger()
        reservation = _reservation()
        denied = ledger.evaluate_call_authorization(
            provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", run_id="run-001", call_id="call-001",
        )
        assert denied.allowed is False
        assert denied.failure_class == "RESERVATION_NOT_FOUND"
        reserved = ledger.reserve_call(reservation)
        assert reserved is not ledger
        assert ledger.sequence == 0
        assert reserved.sequence == 1
        allowed = reserved.evaluate_call_authorization(
            provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", run_id="run-001", call_id="call-001",
        )
        assert allowed.allowed is True

    def test_active_owner_approved_policy_is_required_for_authorization(self):
        draft = BudgetLedgerV1(policy=_policy(status="DRAFT"))
        result = draft.evaluate_call_authorization(
            provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", run_id="run-001", call_id="call-001",
        )
        assert result.allowed is False
        assert result.failure_class in {"POLICY_INACTIVE", "OWNER_APPROVAL_MISSING"}
        active = BudgetLedgerV1(policy=_policy(status="ACTIVE", owner_approval_reference="owner-001"))
        result = active.evaluate_call_authorization(
            provider="DEEPSEEK", model="DEEPSEEK_PRIMARY", run_id="run-001", call_id="call-001",
        )
        assert result.allowed is False

    @pytest.mark.parametrize("field", ("total_cost_cap", "per_run_cost_cap"))
    def test_hard_cost_caps_deny_before_reservation(self, field):
        policy = _policy(**{field: Decimal("500")})
        ledger = BudgetLedgerV1(policy=policy)
        with pytest.raises((TypeError, ValueError)):
            ledger.reserve_call(_reservation(reserved_cost=Decimal("501")))

    def test_provider_and_model_caps_deny_before_transport(self):
        policy = _policy(
            provider_cost_caps={"DEEPSEEK": Decimal("500"), "ANTHROPIC": Decimal("500000")},
            model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("500"), "CLAUDE_SONNET_L1": Decimal("300000"), "CLAUDE_OPUS_L2": Decimal("300000")},
        )
        ledger = BudgetLedgerV1(policy=policy)
        with pytest.raises((TypeError, ValueError)):
            ledger.reserve_call(_reservation(reserved_cost=Decimal("501")))

    def test_call_and_token_limits_are_enforced(self):
        policy = _policy(maximum_call_count=1, maximum_calls_per_run=1, maximum_tokens_per_call=100)
        ledger = BudgetLedgerV1(policy=policy)
        with pytest.raises((TypeError, ValueError)):
            ledger.reserve_call(_reservation(reserved_input_tokens=100, reserved_output_tokens=1))
        reserved = ledger.reserve_call(_reservation(reserved_input_tokens=50, reserved_output_tokens=50))
        with pytest.raises((TypeError, ValueError)):
            reserved.reserve_call(_reservation(reservation_id="reservation-002", call_id="call-002"))

    def test_duplicate_reservations_are_idempotent_or_conflicting(self):
        ledger = _ledger()
        reservation = _reservation()
        first = ledger.reserve_call(reservation)
        same = first.reserve_call(reservation)
        assert same.identity == first.identity
        with pytest.raises((TypeError, ValueError)):
            first.reserve_call(_reservation(reserved_cost=Decimal("1001")))

    def test_release_is_new_state_and_deterministic(self):
        reserved = _ledger().reserve_call(_reservation())
        released = reserved.release_reservation("reservation-001")
        assert released is not reserved
        assert released.reserved_cost == Decimal("0")
        assert released.released_reservations == ("reservation-001",)
        with pytest.raises((TypeError, ValueError)):
            released.release_reservation("missing-reservation")

    def test_commit_usage_binds_reservation_and_cannot_repeat(self):
        reserved = _ledger().reserve_call(_reservation())
        committed = reserved.commit_usage(_usage())
        assert committed.committed_cost == Decimal("850")
        assert committed.committed_input_tokens == 80
        assert committed.committed_output_tokens == 120
        with pytest.raises((TypeError, ValueError)):
            committed.commit_usage(_usage())
        with pytest.raises((TypeError, ValueError)):
            reserved.commit_usage(_usage(reservation_id="missing-reservation"))

    def test_no_call_releases_without_usage_and_uncertain_usage_is_conservative(self):
        reserved = _ledger().reserve_call(_reservation())
        released = reserved.release_reservation("reservation-001")
        assert released.committed_cost == Decimal("0")
        uncertain = _usage(
            outcome="TRANSPORT_FAILURE",
            reconciliation_status="RECONCILIATION_REQUIRED",
            failure_class="UNCERTAIN_TRANSPORT_OUTCOME",
            actual_cost=None,
        )
        reconciled = reserved.reconcile_uncertain_usage(uncertain)
        assert reconciled.reserved_cost >= Decimal("1000")
        assert reconciled.circuit_or_stop_state in {"RECONCILIATION_REQUIRED", "HARD_STOP"}

    def test_usage_exceeding_reservation_fails_closed(self):
        reserved = _ledger().reserve_call(_reservation())
        with pytest.raises((TypeError, ValueError)):
            reserved.commit_usage(_usage(actual_cost=Decimal("1001")))

    def test_expired_reservation_cannot_commit_as_success(self):
        expired = _ledger().reserve_call(_reservation(expires_at="2026-07-17T00:02:00Z"))
        with pytest.raises((TypeError, ValueError)):
            expired.commit_usage(_usage(completed_at="2026-07-17T00:03:00Z"))

    def test_terminal_stop_cannot_reopen(self):
        stopped = _ledger().activate_hard_stop("TOTAL_CAP_HARD_STOP")
        assert stopped.circuit_or_stop_state == "HARD_STOP"
        with pytest.raises((TypeError, ValueError)):
            stopped.reserve_call(_reservation(reservation_id="reservation-002", call_id="call-002"))
        with pytest.raises((TypeError, ValueError)):
            stopped.clear_hard_stop()

    def test_ledger_identity_is_deterministic_and_history_is_immutable(self):
        original = _ledger()
        first = original.reserve_call(_reservation())
        second = _ledger().reserve_call(_reservation())
        assert original.sequence == 0
        assert first.identity == second.identity
        assert original.identity != first.identity


class TestRoutingAndBudgetInteraction:
    def test_l0_reserves_deepseek_only(self):
        ledger = _ledger().reserve_route("L0", "run-001", "call-001")
        assert ledger.reservations[0].provider == "DEEPSEEK"
        assert all(item.model != "CLAUDE_SONNET_L1" and item.model != "CLAUDE_OPUS_L2" for item in ledger.reservations)

    def test_l1_and_l2_use_exact_tiers_without_substitution(self):
        l1 = _ledger().reserve_route("L1", "run-001", "call-001")
        l2 = _ledger().reserve_route("L2", "run-001", "call-001")
        assert any(item.model == "CLAUDE_SONNET_L1" for item in l1.reservations)
        assert all(item.model != "CLAUDE_OPUS_L2" for item in l1.reservations)
        assert any(item.model == "CLAUDE_OPUS_L2" for item in l2.reservations)
        assert all(item.model != "CLAUDE_SONNET_L1" for item in l2.reservations)

    def test_l1_to_l2_requires_separate_reservation_and_no_model_shopping(self):
        l1 = _ledger().reserve_route("L1", "run-001", "call-001")
        escalated = l1.reserve_escalation("L1_TO_L2", "call-002")
        assert any(item.model == "CLAUDE_OPUS_L2" for item in escalated.reservations)
        with pytest.raises((TypeError, ValueError)):
            l1.reserve_route("CHEAPER_SUBSTITUTE", "run-001", "call-003")

    def test_unaffordable_required_tier_denies_before_callable(self):
        policy = _policy(model_cost_caps={"DEEPSEEK_PRIMARY": Decimal("500000"), "CLAUDE_SONNET_L1": Decimal("1"), "CLAUDE_OPUS_L2": Decimal("1")})
        with pytest.raises((TypeError, ValueError)):
            BudgetLedgerV1(policy=policy).reserve_route("L1", "run-001", "call-001")


class TestBudgetMoneyAndFailureValues:
    def test_decimal_arithmetic_is_exact_and_canonical(self):
        first = _policy(total_cost_cap=Decimal("0.10"), per_run_cost_cap=Decimal("0.10"))
        second = _policy(total_cost_cap=Decimal("0.100"), per_run_cost_cap=Decimal("0.100"))
        assert first.identity == second.identity
        for value in (Decimal("-0"), Decimal("NaN"), Decimal("Infinity"), 0.1):
            _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(total_cost_cap=value))

    def test_failure_class_vocabulary_is_closed(self):
        for value in ("UNKNOWN", "provider said retry", "", None):
            _assert_rejected(ProviderUsageRecordV1, **_usage_values(failure_class=value))
        for value in FAILURE_CLASSES:
            record = _usage(failure_class=value, outcome="SUCCESS" if value == "NONE" else "TIMEOUT", reconciliation_status="RESOLVED" if value == "NONE" else "RECONCILIATION_REQUIRED", actual_cost=Decimal("850") if value == "NONE" else None)
            assert record.failure_class == value


class TestBudgetAuthorityExclusions:
    @pytest.mark.parametrize(
        "field",
        (
            "api_key", "credentials", "credential_value", "provider_transport",
            "network_client", "http_request", "production_candidate", "ProductionSignal",
            "publication", "telegram", "account", "balance", "position", "capital",
            "exchange", "order", "trading",
        ),
    )
    def test_all_contracts_reject_authority_fields(self, field):
        _assert_rejected(Phase11BudgetPolicyV1, **_policy_values(**{field: "forbidden"}))
        _assert_rejected(BudgetReservationV1, **_reservation_values(**{field: "forbidden"}))
        _assert_rejected(ProviderUsageRecordV1, **_usage_values(**{field: "forbidden"}))

    def test_ledger_exposes_no_callable_authority_fields(self):
        ledger = _ledger()
        fields = set(vars(ledger)) if hasattr(ledger, "__dict__") else set()
        assert not any("transport" in field.casefold() for field in fields)
        assert not any("credential" in field.casefold() for field in fields)


def _ast_dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _ast_identifiers(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return names


def test_implementation_has_only_deterministic_standard_library_dependencies():
    module = __import__(IMPLEMENTATION_MODULE, fromlist=["*"])
    tree = ast.parse(inspect.getsource(module))
    allowed = {"__future__", "ast", "dataclasses", "datetime", "decimal", "enum", "hashlib", "json", "re", "types", "typing"}
    forbidden = {"requests", "httpx", "urllib", "socket", "subprocess", "dotenv", "telegram", "ccxt", "master_engine_v4", "production_signal_service_v1", "telegram_sdk_runner_v4", "deepseek_validator_v4"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root in allowed
                assert root not in forbidden
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root in allowed
            assert root not in forbidden


def test_implementation_has_no_environment_or_authority_access():
    module = __import__(IMPLEMENTATION_MODULE, fromlist=["*"])
    tree = ast.parse(inspect.getsource(module))
    forbidden_names = {"account", "balance", "position", "capital", "exchange", "order", "trading", "api_key", "credential", "credentials", "transport", "provider_transport", "telegram", "publication", "production_signal", "quota"}
    assert not (_ast_identifiers(tree) & forbidden_names)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert _ast_dotted_name(node) not in {"os.environ", "os.getenv"}
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            assert all(alias.name not in {"environ", "getenv"} for alias in node.names)
        elif isinstance(node, ast.Call):
            assert (_ast_dotted_name(node.func) or (node.func.id if isinstance(node.func, ast.Name) else None)) not in {"getenv", "load_dotenv"}


def test_disposition_is_not_a_forbidden_authority_identifier():
    module = __import__(IMPLEMENTATION_MODULE, fromlist=["*"])
    tree = ast.parse(inspect.getsource(module))
    assert "disposition" in _ast_identifiers(tree)


def test_no_budget_implementation_module_is_absent_from_red_slice():
    path = Path(__file__).parents[1] / "engine" / "phase_11_budget_control_v1.py"
    assert not path.exists(), "RED slice must not create the implementation module"
