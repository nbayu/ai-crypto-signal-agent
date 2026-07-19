"""Pure fail-closed Phase 12 reservation and usage-ledger evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal


_STATES = (
    "PROPOSED", "RESERVED", "TRANSMISSION_PENDING", "CONSUMED", "RELEASED", "EXPIRED",
    "UNCERTAIN", "RECONCILED",
)
_TERMINAL_STATES = ("CONSUMED", "RELEASED", "EXPIRED", "RECONCILED")
_ALLOWED_TRANSITIONS = (
    ("PROPOSED", "RESERVED"),
    ("RESERVED", "TRANSMISSION_PENDING"),
    ("RESERVED", "RELEASED"),
    ("RESERVED", "EXPIRED"),
    ("TRANSMISSION_PENDING", "CONSUMED"),
    ("TRANSMISSION_PENDING", "UNCERTAIN"),
    ("UNCERTAIN", "RECONCILED"),
)
_EVENT_TYPES = (
    "RESERVATION_PROPOSED", "RESERVATION_CREATED", "TRANSMISSION_PENDING", "USAGE_CONSUMED",
    "RESERVATION_RELEASED", "RESERVATION_EXPIRED", "OUTCOME_UNCERTAIN", "OUTCOME_RECONCILED",
)


@dataclass(frozen=True, slots=True)
class ReservationRequestV1:
    reservation_request_id: str
    reservation_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    pricing_observation_id: str
    pricing_policy_id: str
    provider_id: str
    route_id: str
    model_id: str
    currency: str
    estimated_cost: Decimal
    request_cost_ceiling: Decimal
    run_cost_ceiling: Decimal
    current_run_reserved_cost: Decimal
    requested_at: datetime
    expires_at: datetime
    provider_request_constructed: bool
    pricing_revalidated: bool
    pricing_within_limits: bool
    reservation_authorized: bool


@dataclass(frozen=True, slots=True)
class ReservationPolicyV1:
    policy_id: str
    policy_version: str
    required_currency: str
    maximum_reservation_lifetime_seconds: int
    require_constructed_provider_request: bool
    require_pricing_revalidation: bool
    require_pricing_within_limits: bool
    require_request_identity: bool
    require_idempotency_identity: bool
    require_payload_identity: bool
    require_unique_reservation_id: bool
    require_unique_request_id: bool
    require_unique_ledger_event_id: bool
    append_only_ledger: bool
    allow_reservation_creation: bool
    allow_reservation_settlement: bool
    allow_reservation_cancellation: bool
    allow_uncertain_outcome_recording: bool
    allow_reconciliation: bool
    allow_ledger_mutation: bool
    provider_transmission_authorized: bool
    provider_execution_authorized: bool
    fail_closed: bool


@dataclass(frozen=True, slots=True)
class ReservationFailureV1:
    failure_code: str
    safe_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class ReservationRecordV1:
    reservation_id: str
    reservation_request_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    provider_id: str
    route_id: str
    model_id: str
    currency: str
    reserved_amount: Decimal
    consumed_amount: Decimal
    released_amount: Decimal
    state: str
    created_at: datetime
    expires_at: datetime
    last_event_id: str
    reservation_created: bool
    ledger_mutated: bool
    provider_contacted: bool
    transmitted: bool
    provider_execution_authorized: bool


@dataclass(frozen=True, slots=True)
class UsageLedgerEventV1:
    event_id: str
    reservation_id: str
    request_id: str
    event_type: str
    prior_state: str
    next_state: str
    currency: str
    amount: Decimal
    occurred_at: datetime
    reconciliation_status: str
    immutable_event_identity: str
    append_only: bool
    ledger_mutation_authorized: bool
    provider_contacted: bool
    execution_authorized: bool


@dataclass(frozen=True, slots=True)
class ReservationTransitionResultV1:
    reservation_id: str
    prior_state: str
    requested_state: str
    transition_valid: bool
    failure_codes: tuple[str, ...]
    resulting_record: ReservationRecordV1 | None
    ledger_event: UsageLedgerEventV1 | None
    reservation_created: bool
    ledger_mutated: bool
    provider_contacted: bool
    transmitted: bool
    provider_execution_authorized: bool


@dataclass(frozen=True, slots=True)
class ReservationAuditEvidenceV1:
    reservation_request_id: str
    reservation_id: str
    request_id: str
    idempotency_key: str
    payload_identity: str
    pricing_observation_id: str
    pricing_policy_id: str
    provider_id: str
    route_id: str
    model_id: str
    currency: str
    estimated_cost: Decimal
    request_cost_ceiling: Decimal
    run_cost_ceiling: Decimal
    current_run_reserved_cost: Decimal
    requested_at: datetime
    expires_at: datetime
    policy_id: str
    state: str
    failure_codes: tuple[str, ...]
    reservation_created: bool
    ledger_mutated: bool
    provider_contacted: bool
    transmitted: bool
    provider_execution_authorized: bool


def _add(codes: tuple[str, ...], code: str) -> tuple[str, ...]:
    return codes if code in codes else codes + (code,)


def _ordered(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(codes))


def _identity_valid(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and "*" not in value


def _decimal_valid(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value >= Decimal("0")


def _utc(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo == UTC


def _result(
    reservation_id: object, prior_state: object, requested_state: object, codes: tuple[str, ...]
) -> ReservationTransitionResultV1:
    return ReservationTransitionResultV1(
        reservation_id if isinstance(reservation_id, str) else "",
        prior_state if isinstance(prior_state, str) else "",
        requested_state if isinstance(requested_state, str) else "",
        False,
        _ordered(codes),
        None,
        None,
        False,
        False,
        False,
        False,
        False,
    )


def _request_failures(
    reservation_request: ReservationRequestV1, policy: ReservationPolicyV1, evaluation_at: datetime
) -> tuple[str, ...]:
    codes: tuple[str, ...] = ()
    identity_codes = (
        (reservation_request.reservation_request_id, "RESERVATION_REQUEST_ID_EMPTY"),
        (reservation_request.reservation_id, "RESERVATION_ID_EMPTY"),
        (reservation_request.request_id, "REQUEST_ID_EMPTY"),
        (reservation_request.idempotency_key, "IDEMPOTENCY_KEY_EMPTY"),
        (reservation_request.payload_identity, "PAYLOAD_IDENTITY_EMPTY"),
        (reservation_request.pricing_observation_id, "PRICING_OBSERVATION_ID_EMPTY"),
        (reservation_request.pricing_policy_id, "PRICING_POLICY_ID_EMPTY"),
        (reservation_request.provider_id, "PROVIDER_ID_EMPTY"),
        (reservation_request.route_id, "ROUTE_ID_EMPTY"),
        (reservation_request.model_id, "MODEL_ID_EMPTY"),
        (policy.policy_id, "POLICY_ID_EMPTY"),
        (policy.policy_version, "POLICY_VERSION_EMPTY"),
    )
    for value, empty_code in identity_codes:
        if not isinstance(value, str) or not value:
            codes = _add(codes, empty_code)
        elif not _identity_valid(value):
            codes = _add(codes, "IDENTIFIER_NOT_NORMALIZED")
    monetary_values = (
        reservation_request.estimated_cost,
        reservation_request.request_cost_ceiling,
        reservation_request.run_cost_ceiling,
        reservation_request.current_run_reserved_cost,
    )
    if not all(_decimal_valid(value) for value in monetary_values):
        codes = _add(codes, "MONETARY_VALUE_INVALID")
        codes = _add(codes, "ESTIMATED_COST_INVALID")
    else:
        if reservation_request.estimated_cost > reservation_request.request_cost_ceiling:
            codes = _add(codes, "REQUEST_COST_CEILING_EXCEEDED")
        if reservation_request.current_run_reserved_cost + reservation_request.estimated_cost > reservation_request.run_cost_ceiling:
            codes = _add(codes, "RUN_COST_CEILING_EXCEEDED")
    if reservation_request.currency != policy.required_currency:
        codes = _add(codes, "CURRENCY_NOT_ALLOWED")
    if not _utc(reservation_request.requested_at) or not _utc(reservation_request.expires_at) or not _utc(evaluation_at):
        codes = _add(codes, "TIMEZONE_NOT_UTC")
    elif reservation_request.requested_at >= reservation_request.expires_at:
        codes = _add(codes, "REQUEST_TIME_INVALID")
        codes = _add(codes, "RESERVATION_LIFETIME_INVALID")
    else:
        lifetime = (reservation_request.expires_at - reservation_request.requested_at).total_seconds()
        if lifetime <= 0 or not isinstance(policy.maximum_reservation_lifetime_seconds, int) or isinstance(policy.maximum_reservation_lifetime_seconds, bool) or lifetime > policy.maximum_reservation_lifetime_seconds:
            codes = _add(codes, "RESERVATION_LIFETIME_INVALID")
        if evaluation_at >= reservation_request.expires_at:
            codes = _add(codes, "RESERVATION_EXPIRED")
    if policy.require_constructed_provider_request and reservation_request.provider_request_constructed is not True:
        codes = _add(codes, "REQUEST_NOT_CONSTRUCTED")
    if policy.require_pricing_revalidation and reservation_request.pricing_revalidated is not True:
        codes = _add(codes, "PRICING_NOT_REVALIDATED")
    if policy.require_pricing_within_limits and reservation_request.pricing_within_limits is not True:
        codes = _add(codes, "PRICING_LIMIT_NOT_SATISFIED")
    if reservation_request.reservation_authorized is not True:
        codes = _add(codes, "RESERVATION_NOT_AUTHORIZED")
    if policy.allow_reservation_creation is not True:
        codes = _add(codes, "RESERVATION_CREATION_NOT_AUTHORIZED")
    if policy.allow_ledger_mutation is not True:
        codes = _add(codes, "LEDGER_MUTATION_NOT_AUTHORIZED")
    if policy.provider_transmission_authorized is not True:
        codes = _add(codes, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED")
    if policy.provider_execution_authorized is not True:
        codes = _add(codes, "PROVIDER_EXECUTION_NOT_AUTHORIZED")
    return codes


def evaluate_reservation_request_v1(
    reservation_request: ReservationRequestV1, policy: ReservationPolicyV1, evaluation_at: datetime
) -> ReservationTransitionResultV1:
    """Evaluate a proposed reservation without creating or storing it."""
    return _result(
        reservation_request.reservation_id,
        "PROPOSED",
        "RESERVED",
        _request_failures(reservation_request, policy, evaluation_at),
    )


def _record_failures(record: ReservationRecordV1, occurred_at: datetime) -> tuple[str, ...]:
    codes: tuple[str, ...] = ()
    if record.state not in _STATES:
        codes = _add(codes, "STATE_INVALID")
    if not _utc(record.created_at) or not _utc(record.expires_at) or not _utc(occurred_at):
        codes = _add(codes, "TIMEZONE_NOT_UTC")
    elif record.created_at >= record.expires_at:
        codes = _add(codes, "EXPIRY_TIME_INVALID")
    elif occurred_at >= record.expires_at:
        codes = _add(codes, "RESERVATION_EXPIRED")
    amounts = (record.reserved_amount, record.consumed_amount, record.released_amount)
    if not all(_decimal_valid(value) for value in amounts):
        codes = _add(codes, "MONETARY_VALUE_INVALID")
    else:
        if record.consumed_amount > record.reserved_amount:
            codes = _add(codes, "CONSUMED_AMOUNT_EXCEEDS_RESERVED")
        if record.released_amount > record.reserved_amount:
            codes = _add(codes, "RELEASED_AMOUNT_EXCEEDS_RESERVED")
        if record.consumed_amount + record.released_amount > record.reserved_amount:
            codes = _add(codes, "SETTLEMENT_TOTAL_EXCEEDS_RESERVED")
    return codes


def apply_reservation_transition_v1(
    record: ReservationRecordV1,
    policy: ReservationPolicyV1,
    requested_state: str,
    event_id: str,
    occurred_at: datetime,
) -> ReservationTransitionResultV1:
    """Evaluate one requested transition without changing evidence or storage."""
    codes = _record_failures(record, occurred_at)
    if not _identity_valid(event_id):
        codes = _add(codes, "EVENT_ID_EMPTY" if not isinstance(event_id, str) or not event_id else "IDENTIFIER_NOT_NORMALIZED")
    if record.state in _TERMINAL_STATES:
        codes = _add(codes, "TERMINAL_STATE_TRANSITION_FORBIDDEN")
    elif requested_state not in _STATES:
        codes = _add(codes, "STATE_INVALID")
    elif (record.state, requested_state) not in _ALLOWED_TRANSITIONS:
        codes = _add(codes, "TRANSITION_NOT_ALLOWED")
    if requested_state == "RESERVED" and policy.allow_reservation_creation is not True:
        codes = _add(codes, "RESERVATION_CREATION_NOT_AUTHORIZED")
    if requested_state == "CONSUMED" and policy.allow_reservation_settlement is not True:
        codes = _add(codes, "SETTLEMENT_NOT_AUTHORIZED")
    if requested_state == "RELEASED" and policy.allow_reservation_cancellation is not True:
        codes = _add(codes, "CANCELLATION_NOT_AUTHORIZED")
    if requested_state == "UNCERTAIN" and policy.allow_uncertain_outcome_recording is not True:
        codes = _add(codes, "UNCERTAIN_OUTCOME_NOT_AUTHORIZED")
    if requested_state == "RECONCILED" and policy.allow_reconciliation is not True:
        codes = _add(codes, "RECONCILIATION_NOT_AUTHORIZED")
    if policy.allow_ledger_mutation is not True:
        codes = _add(codes, "LEDGER_MUTATION_NOT_AUTHORIZED")
    if policy.provider_transmission_authorized is not True:
        codes = _add(codes, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED")
    if policy.provider_execution_authorized is not True:
        codes = _add(codes, "PROVIDER_EXECUTION_NOT_AUTHORIZED")
    return _result(record.reservation_id, record.state, requested_state, codes)


def build_reservation_audit_evidence_v1(
    reservation_request: ReservationRequestV1,
    policy: ReservationPolicyV1,
    transition_result: ReservationTransitionResultV1,
) -> ReservationAuditEvidenceV1:
    """Build immutable non-operational evidence for a reservation evaluation."""
    if reservation_request.reservation_id != transition_result.reservation_id or not _identity_valid(policy.policy_id):
        raise ValueError("identity mismatch")
    return ReservationAuditEvidenceV1(
        reservation_request.reservation_request_id,
        reservation_request.reservation_id,
        reservation_request.request_id,
        reservation_request.idempotency_key,
        reservation_request.payload_identity,
        reservation_request.pricing_observation_id,
        reservation_request.pricing_policy_id,
        reservation_request.provider_id,
        reservation_request.route_id,
        reservation_request.model_id,
        reservation_request.currency,
        reservation_request.estimated_cost,
        reservation_request.request_cost_ceiling,
        reservation_request.run_cost_ceiling,
        reservation_request.current_run_reserved_cost,
        reservation_request.requested_at,
        reservation_request.expires_at,
        policy.policy_id,
        transition_result.prior_state,
        transition_result.failure_codes,
        False,
        False,
        False,
        False,
        False,
    )
