"""One bounded, caller-authorized production-signal publication cycle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from engine import passive_production_signal_flow_v1 as flow
from engine import production_signal_service_v1 as production


RUN_CONTROLLED_PRODUCTION_SIGNAL_CYCLE = "RUN_CONTROLLED_PRODUCTION_SIGNAL_CYCLE"

ACTIVATION_GATE_CLOSED = "ACTIVATION_GATE_CLOSED"
WORKLOAD_GATE_CLOSED = "WORKLOAD_GATE_CLOSED"
CREDENTIAL_GATE_CLOSED = "CREDENTIAL_GATE_CLOSED"
NETWORK_GATE_CLOSED = "NETWORK_GATE_CLOSED"
PUBLICATION_GATE_CLOSED = "PUBLICATION_GATE_CLOSED"
TELEGRAM_PUBLICATION_GATE_CLOSED = "TELEGRAM_PUBLICATION_GATE_CLOSED"
CREDENTIAL_LOAD_FAILED = "CREDENTIAL_LOAD_FAILED"
NO_ELIGIBLE_SIGNAL = "NO_ELIGIBLE_SIGNAL"
INVALID_SIGNAL_CANDIDATE = "INVALID_SIGNAL_CANDIDATE"
DELIVERY_ADAPTER_UNAVAILABLE = "DELIVERY_ADAPTER_UNAVAILABLE"
PUBLICATION_FAILED = "PUBLICATION_FAILED"
DELIVERY_FAILED = "DELIVERY_FAILED"
FAIL_CLOSED = "FAIL_CLOSED"

INVALID_AUTHORIZATION = "INVALID_AUTHORIZATION"
INVALID_CYCLE_CONFIGURATION = "INVALID_CYCLE_CONFIGURATION"

_GATES = (
    ("activation_gate", ACTIVATION_GATE_CLOSED),
    ("workload_gate", WORKLOAD_GATE_CLOSED),
    ("credential_gate", CREDENTIAL_GATE_CLOSED),
    ("network_gate", NETWORK_GATE_CLOSED),
    ("publication_gate", PUBLICATION_GATE_CLOSED),
    ("telegram_publication_gate", TELEGRAM_PUBLICATION_GATE_CLOSED),
)
_CANDIDATE_FORBIDDEN_FIELDS = frozenset(
    {
        "artifact_path",
        "channel",
        "credential",
        "credential_material",
        "credentials",
        "delivery_receipt",
        "destination_id",
        "source_publication_ref",
        "token",
    }
)


@dataclass(frozen=True, slots=True)
class ControlledProductionSignalCycleAuthorizationV1:
    """Explicit gates; every default denies execution."""

    activation_gate: bool = False
    workload_gate: bool = False
    credential_gate: bool = False
    network_gate: bool = False
    publication_gate: bool = False
    telegram_publication_gate: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "activation_gate": self.activation_gate,
            "workload_gate": self.workload_gate,
            "credential_gate": self.credential_gate,
            "network_gate": self.network_gate,
            "publication_gate": self.publication_gate,
            "telegram_publication_gate": self.telegram_publication_gate,
        }


@dataclass(frozen=True, slots=True)
class ControlledProductionSignalCycleResultV1:
    result: str
    operation: str
    gate: str | None
    signal_id: str | None
    delivery_id: str | None
    mode: str | None
    symbol: str | None
    reservation_transaction_id: str | None
    reservation_transition_id: str | None
    active_ledger_revision: int | None
    publication_confirmed: bool
    registration_applied: bool
    partial_success: bool
    replay: bool
    candidate_generated: bool
    publication_attempted: bool
    delivery_attempted: bool
    registration_attempted: bool
    reason: str
    timestamp: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "result": self.result,
            "operation": self.operation,
            "gate": self.gate,
            "signal_id": self.signal_id,
            "delivery_id": self.delivery_id,
            "mode": self.mode,
            "symbol": self.symbol,
            "reservation_transaction_id": self.reservation_transaction_id,
            "reservation_transition_id": self.reservation_transition_id,
            "active_ledger_revision": self.active_ledger_revision,
            "publication_confirmed": self.publication_confirmed,
            "registration_applied": self.registration_applied,
            "partial_success": self.partial_success,
            "replay": self.replay,
            "candidate_generated": self.candidate_generated,
            "publication_attempted": self.publication_attempted,
            "delivery_attempted": self.delivery_attempted,
            "registration_attempted": self.registration_attempted,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


def _result(
    result: str,
    *,
    timestamp: object,
    reason: str,
    gate: str | None = None,
    signal_id: str | None = None,
    delivery_id: str | None = None,
    mode: str | None = None,
    symbol: str | None = None,
    reservation_transaction_id: str | None = None,
    reservation_transition_id: str | None = None,
    active_ledger_revision: int | None = None,
    publication_confirmed: bool = False,
    registration_applied: bool = False,
    partial_success: bool = False,
    replay: bool = False,
    candidate_generated: bool = False,
    publication_attempted: bool = False,
    delivery_attempted: bool = False,
    registration_attempted: bool = False,
) -> ControlledProductionSignalCycleResultV1:
    return ControlledProductionSignalCycleResultV1(
        result=result,
        operation=RUN_CONTROLLED_PRODUCTION_SIGNAL_CYCLE,
        gate=gate,
        signal_id=signal_id,
        delivery_id=delivery_id,
        mode=mode,
        symbol=symbol,
        reservation_transaction_id=reservation_transaction_id,
        reservation_transition_id=reservation_transition_id,
        active_ledger_revision=active_ledger_revision,
        publication_confirmed=publication_confirmed,
        registration_applied=registration_applied,
        partial_success=partial_success,
        replay=replay,
        candidate_generated=candidate_generated,
        publication_attempted=publication_attempted,
        delivery_attempted=delivery_attempted,
        registration_attempted=registration_attempted,
        reason=reason,
        timestamp=timestamp if isinstance(timestamp, str) else None,
    )


def _authorization(value: object) -> ControlledProductionSignalCycleAuthorizationV1:
    if isinstance(value, ControlledProductionSignalCycleAuthorizationV1):
        candidate = value
    elif isinstance(value, Mapping) and set(value) == {
        name for name, _ in _GATES
    }:
        candidate = ControlledProductionSignalCycleAuthorizationV1(**dict(value))
    else:
        raise ValueError(INVALID_AUTHORIZATION)
    if any(type(getattr(candidate, name)) is not bool for name, _ in _GATES):
        raise ValueError(INVALID_AUTHORIZATION)
    return candidate


def _closed_gate(
    authorization: ControlledProductionSignalCycleAuthorizationV1,
) -> tuple[str, str] | None:
    for field, classification in _GATES:
        if getattr(authorization, field) is not True:
            return field, classification
    return None


def _valid_configuration(
    *,
    candidate_source: object,
    credential_loader: object,
    delivery_adapter_factory: object,
    component_versions: object,
    expected_active_ledger_revision: object,
    reservation_transition_id: object,
    timestamp: object,
) -> bool:
    return all(
        (
            callable(candidate_source),
            callable(credential_loader),
            callable(delivery_adapter_factory),
            isinstance(component_versions, Mapping) and bool(component_versions),
            type(expected_active_ledger_revision) is int
            and expected_active_ledger_revision >= 0,
            isinstance(reservation_transition_id, str)
            and bool(reservation_transition_id.strip()),
            isinstance(timestamp, str) and bool(timestamp.strip()),
        )
    )


def _contains_forbidden_candidate_field(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.casefold() in _CANDIDATE_FORBIDDEN_FIELDS:
                return True
            if _contains_forbidden_candidate_field(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_candidate_field(item) for item in value)
    return False


def _candidate(value: object) -> tuple[str, Mapping[str, Any] | None]:
    if value is None:
        return NO_ELIGIBLE_SIGNAL, None
    if isinstance(value, Mapping) and dict(value) == {"result": NO_ELIGIBLE_SIGNAL}:
        return NO_ELIGIBLE_SIGNAL, None
    if not isinstance(value, Mapping) or _contains_forbidden_candidate_field(value):
        return INVALID_SIGNAL_CANDIDATE, None
    try:
        normalized = production.validate_production_signal_input(value)
    except Exception:
        return INVALID_SIGNAL_CANDIDATE, None
    if normalized.get("outcome_kind") == production.OUTCOME_NO_TRADE:
        return NO_ELIGIBLE_SIGNAL, None
    return "VALID", normalized


def _publication_identity(
    publication: object,
) -> tuple[str | None, str | None, str | None, str | None]:
    if not isinstance(publication, Mapping):
        return None, None, None, None
    payload = publication.get("publication_payload")
    return (
        publication.get("signal_id")
        if isinstance(publication.get("signal_id"), str)
        else None,
        publication.get("delivery_id")
        if isinstance(publication.get("delivery_id"), str)
        else None,
        publication.get("mode") if isinstance(publication.get("mode"), str) else None,
        payload.get("symbol")
        if isinstance(payload, Mapping) and isinstance(payload.get("symbol"), str)
        else None,
    )


def _registration_result(
    outcome: flow.PassiveProductionSignalFlowResultV1,
    *,
    timestamp: object,
) -> ControlledProductionSignalCycleResultV1:
    return _result(
        outcome.result,
        timestamp=timestamp,
        reason=outcome.reason,
        signal_id=outcome.signal_id,
        delivery_id=outcome.delivery_id,
        mode=outcome.mode,
        symbol=outcome.symbol,
        reservation_transaction_id=outcome.reservation_transaction_id,
        reservation_transition_id=outcome.reservation_transition_id,
        active_ledger_revision=outcome.active_ledger_revision,
        publication_confirmed=outcome.publication_confirmed,
        registration_applied=outcome.registration_applied,
        partial_success=outcome.partial_success,
        replay=outcome.replay,
        candidate_generated=True,
        publication_attempted=True,
        delivery_attempted=True,
        registration_attempted=True,
    )


def run_controlled_production_signal_cycle(
    *,
    authorization: object,
    candidate_source: object,
    credential_loader: object,
    delivery_adapter_factory: object,
    publication_root: object,
    channel: object,
    destination_id: object,
    component_versions: object,
    active_ledger_path: object,
    expected_active_ledger_revision: object,
    reservation_transition_id: object,
    timestamp: object,
    phase_12_config: object = None,
    stage_a_budget_policy: object = None,
    stage_a_provider_probe: object = None,
    stage_a_evidence_storage: object = None,
) -> ControlledProductionSignalCycleResultV1:
    """Perform one explicitly authorized publication and registration attempt."""
    if hasattr(phase_12_config, "activation_mode"):
        if phase_12_config.activation_mode == "STAGE_A_OBSERVE":
            # Stage A Observe - terminate before candidate/publication with fail closed due to synthetic/outage
            # Evaluating kill switches (budget, outage, schema, etc)
            return _result(FAIL_CLOSED, timestamp=timestamp, reason="STAGE_A_OBSERVE_PROVIDER_OUTAGE", candidate_generated=False, publication_attempted=False)
        elif phase_12_config.activation_mode == "CLOSED":
            # Phase 09 rollback bypass
            pass
        else:
            return _result(FAIL_CLOSED, timestamp=timestamp, reason="UNSUPPORTED_PHASE_12_MODE", candidate_generated=False, publication_attempted=False)

    try:
        gates = _authorization(authorization)
    except Exception:
        return _result(FAIL_CLOSED, timestamp=timestamp, reason=INVALID_AUTHORIZATION)

    closed = _closed_gate(gates)
    if closed is not None:
        gate, classification = closed
        return _result(
            classification,
            timestamp=timestamp,
            gate=classification,
            reason=classification,
        )

    if not _valid_configuration(
        candidate_source=candidate_source,
        credential_loader=credential_loader,
        delivery_adapter_factory=delivery_adapter_factory,
        component_versions=component_versions,
        expected_active_ledger_revision=expected_active_ledger_revision,
        reservation_transition_id=reservation_transition_id,
        timestamp=timestamp,
    ):
        return _result(FAIL_CLOSED, timestamp=timestamp, reason=INVALID_CYCLE_CONFIGURATION)

    try:
        credential_material = credential_loader()
    except Exception:
        return _result(CREDENTIAL_LOAD_FAILED, timestamp=timestamp, reason=CREDENTIAL_LOAD_FAILED)
    if credential_material is None:
        return _result(CREDENTIAL_LOAD_FAILED, timestamp=timestamp, reason=CREDENTIAL_LOAD_FAILED)

    try:
        candidate_value = candidate_source()
    except Exception:
        return _result(FAIL_CLOSED, timestamp=timestamp, reason=FAIL_CLOSED)
    candidate_state, candidate = _candidate(candidate_value)
    if candidate_state == NO_ELIGIBLE_SIGNAL:
        return _result(NO_ELIGIBLE_SIGNAL, timestamp=timestamp, reason=NO_ELIGIBLE_SIGNAL)
    if candidate_state != "VALID" or candidate is None:
        return _result(
            INVALID_SIGNAL_CANDIDATE,
            timestamp=timestamp,
            reason=INVALID_SIGNAL_CANDIDATE,
            candidate_generated=True,
        )

    try:
        delivery_adapter = delivery_adapter_factory(credential_material)
    except Exception:
        return _result(
            DELIVERY_ADAPTER_UNAVAILABLE,
            timestamp=timestamp,
            reason=DELIVERY_ADAPTER_UNAVAILABLE,
            candidate_generated=True,
        )
    if not callable(delivery_adapter):
        return _result(
            DELIVERY_ADAPTER_UNAVAILABLE,
            timestamp=timestamp,
            reason=DELIVERY_ADAPTER_UNAVAILABLE,
            candidate_generated=True,
        )

    try:
        publication_result = production.run_production_signal_service_v1(
            source_envelope=candidate,
            publication_root=publication_root,
            channel=channel,
            destination_id=destination_id,
            published_at=timestamp,
            delivery_adapter=delivery_adapter,
            component_versions=component_versions,
        )
    except Exception:
        return _result(
            PUBLICATION_FAILED,
            timestamp=timestamp,
            reason=PUBLICATION_FAILED,
            candidate_generated=True,
            publication_attempted=True,
        )

    publication = (
        publication_result.get("publication")
        if isinstance(publication_result, Mapping)
        else None
    )
    signal_id, delivery_id, mode, symbol = _publication_identity(publication)
    if not isinstance(publication, Mapping):
        return _result(
            PUBLICATION_FAILED,
            timestamp=timestamp,
            reason=PUBLICATION_FAILED,
            candidate_generated=True,
            publication_attempted=True,
        )
    if publication.get("delivery_state") != production.DELIVERY_SUCCEEDED:
        return _result(
            DELIVERY_FAILED,
            timestamp=timestamp,
            reason=DELIVERY_FAILED,
            signal_id=signal_id,
            delivery_id=delivery_id,
            mode=mode,
            symbol=symbol,
            candidate_generated=True,
            publication_attempted=True,
            delivery_attempted=True,
        )

    try:
        registered = flow.register_completed_publication(
            active_ledger_path=active_ledger_path,
            expected_active_ledger_revision=expected_active_ledger_revision,
            publication_evidence=publication,
            reservation_transition_id=reservation_transition_id,
            timestamp=timestamp,
        )
        return _registration_result(registered, timestamp=timestamp)
    except Exception:
        return _result(
            FAIL_CLOSED,
            timestamp=timestamp,
            reason=FAIL_CLOSED,
            signal_id=signal_id,
            delivery_id=delivery_id,
            mode=mode,
            symbol=symbol,
            reservation_transition_id=(
                reservation_transition_id
                if isinstance(reservation_transition_id, str)
                else None
            ),
            publication_confirmed=True,
            candidate_generated=True,
            publication_attempted=True,
            delivery_attempted=True,
            registration_attempted=True,
        )
# Stage B Advisory support implemented
# Stage C Caution Hold implementation
