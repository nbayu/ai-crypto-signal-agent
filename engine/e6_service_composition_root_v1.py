"""Default-deny service boundary for one eligible E6 Telegram delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Callable, Mapping

from engine.controlled_production_signal_cycle_v1 import (
    _GATES,
    ControlledProductionSignalCycleAuthorizationV1,
)
from engine.e6_integrated_orchestrator_v1 import (
    COMPLETE as ORCHESTRATOR_COMPLETE,
    STAGE_10_COMPLETE,
    E6IntegratedOrchestratorPortsV1,
    E6IntegratedOrchestratorRequestV1,
    E6IntegratedOrchestratorResultV1,
    run_e6_integrated_orchestrator_v1,
)
from engine.e6_owner_state_lifecycle_binding_v1 import (
    CREATED,
    IDEMPOTENT_REPLAY as OWNER_IDEMPOTENT_REPLAY,
    E6OwnerStateLifecycleBindingResultV1,
)
from engine.e6_publication_eligibility_v1 import (
    ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE,
    E6PublicationEligibilityResultV1,
)
from engine.e6_publication_envelope_v1 import E6PublicationEnvelopeV1
from engine.e6_telegram_human_formatter_v1 import format_e6_signal_message_v1
from engine.phase09r_telegram_delivery_adapter_v1 import E6TelegramDeliveryRequestV1
from engine.production_signal_contract_v1 import build_delivery_id


E6_SERVICE_CYCLE_VERSION = "e6-service-cycle-v1"
E6_SERVICE_CYCLE_SCHEMA = "ai-crypto-signal-agent.e6-service-cycle.v1"

DRY = "DRY"
HOLD = "HOLD"
DELIVERED = "DELIVERED"
IDEMPOTENT_REPLAY = "IDEMPOTENT_REPLAY"

STAGE_1_VALIDATE_ROOT_REQUEST_AND_AUTHORIZATION = (
    "STAGE_1_VALIDATE_ROOT_REQUEST_AND_AUTHORIZATION"
)
STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION = (
    "STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION"
)
STAGE_3_REQUIRE_EXACT_E6_ELIGIBILITY = "STAGE_3_REQUIRE_EXACT_E6_ELIGIBILITY"
STAGE_4_DELIVERY_IDEMPOTENCY_PREFLIGHT = (
    "STAGE_4_DELIVERY_IDEMPOTENCY_PREFLIGHT"
)
STAGE_5_ONE_TELEGRAM_ATTEMPT = "STAGE_5_ONE_TELEGRAM_ATTEMPT"
STAGE_6_COMPLETE_DELIVERY_EVIDENCE = "STAGE_6_COMPLETE_DELIVERY_EVIDENCE"

INVALID_ROOT_OR_REQUEST = "INVALID_ROOT_OR_REQUEST"
E6_ACTIVATION_NOT_AUTHORIZED = "E6_ACTIVATION_NOT_AUTHORIZED"
E6_NETWORK_NOT_AUTHORIZED = "E6_NETWORK_NOT_AUTHORIZED"
E6_PUBLICATION_NOT_AUTHORIZED = "E6_PUBLICATION_NOT_AUTHORIZED"
E6_ORCHESTRATOR_FAILED = "E6_ORCHESTRATOR_FAILED"
E6_ORCHESTRATOR_TERMINAL = "E6_ORCHESTRATOR_TERMINAL"
E6_ELIGIBILITY_OR_LINEAGE_INVALID = "E6_ELIGIBILITY_OR_LINEAGE_INVALID"
E6_DELIVERY_REPLAY_CONFLICT = "E6_DELIVERY_REPLAY_CONFLICT"
TELEGRAM_DELIVERY_FAILED = "TELEGRAM_DELIVERY_FAILED"
DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
IDEMPOTENT_COMPLETED_REPLAY = "IDEMPOTENT_COMPLETED_REPLAY"
NOT_ATTEMPTED = "NOT_ATTEMPTED"

_DISPOSITIONS = frozenset({DRY, HOLD, DELIVERED, IDEMPOTENT_REPLAY})
_STAGES = frozenset(
    {
        STAGE_1_VALIDATE_ROOT_REQUEST_AND_AUTHORIZATION,
        STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
        STAGE_3_REQUIRE_EXACT_E6_ELIGIBILITY,
        STAGE_4_DELIVERY_IDEMPOTENCY_PREFLIGHT,
        STAGE_5_ONE_TELEGRAM_ATTEMPT,
        STAGE_6_COMPLETE_DELIVERY_EVIDENCE,
    }
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("invalid E6 service composition")


@dataclass(frozen=True, slots=True)
class E6ServiceCompositionRootV1:
    """Injected effect ports plus nine separate false-by-default decisions."""

    orchestrator: Callable[..., object] = run_e6_integrated_orchestrator_v1
    telegram_delivery: Callable[..., object] | None = None
    authorization: ControlledProductionSignalCycleAuthorizationV1 = field(
        default_factory=ControlledProductionSignalCycleAuthorizationV1
    )
    e6_activation_authorized: bool = False
    network_authorized: bool = False
    publication_authorized: bool = False

    def __post_init__(self) -> None:
        _require(callable(self.orchestrator))
        _require(self.telegram_delivery is None or callable(self.telegram_delivery))
        _require(
            type(self.authorization)
            is ControlledProductionSignalCycleAuthorizationV1
        )
        for name, _classification in _GATES:
            _require(type(getattr(self.authorization, name)) is bool)
        for decision in (
            self.e6_activation_authorized,
            self.network_authorized,
            self.publication_authorized,
        ):
            _require(type(decision) is bool)


@dataclass(frozen=True, slots=True)
class E6ServiceCycleRequestV1:
    orchestrator_request: E6IntegratedOrchestratorRequestV1
    orchestrator_ports: E6IntegratedOrchestratorPortsV1
    channel: str
    destination_id: str

    def __post_init__(self) -> None:
        _require(type(self.orchestrator_request) is E6IntegratedOrchestratorRequestV1)
        _require(type(self.orchestrator_ports) is E6IntegratedOrchestratorPortsV1)
        self.orchestrator_request.__post_init__()
        self.orchestrator_ports.__post_init__()
        _require(self.channel == "TELEGRAM")
        _require(type(self.destination_id) is str and bool(self.destination_id.strip()))


@dataclass(frozen=True, slots=True)
class E6ServiceCycleResultV1:
    result_version: str
    result_schema: str
    disposition: str
    terminal_stage: str
    reason_code: str
    gate_decisions: tuple[tuple[str, bool], ...]
    e6_activation_authorized: bool
    network_authorized: bool
    publication_authorized: bool
    orchestrator_disposition: str | None
    orchestrator_request_sha256: str | None
    orchestrator_correlation_sha256: str | None
    eligibility_sha256: str | None
    envelope_sha256: str | None
    publication_identity_sha256: str | None
    thesis_fingerprint_sha256: str | None
    signal_id: str | None
    delivery_id: str | None
    owner_lifecycle_binding_disposition: str | None
    owner_registration_applied: bool
    owner_registration_replay: bool
    telegram_attempt_count: int
    delivery_completion_disposition: str
    deepseek_provider_attempt_count: int
    claude_provider_attempt_count: int
    publication_artifact_effect_count: int
    telegram_send_attempt_effect_count: int
    owner_decision_count: int
    entry_active_mutation_count: int
    slot_mutation_count: int
    pair_lock_mutation_count: int
    exchange_order_count: int

    def __post_init__(self) -> None:
        _require(self.result_version == E6_SERVICE_CYCLE_VERSION)
        _require(self.result_schema == E6_SERVICE_CYCLE_SCHEMA)
        _require(self.disposition in _DISPOSITIONS)
        _require(self.terminal_stage in _STAGES)
        _require(type(self.reason_code) is str and bool(self.reason_code))
        _require(tuple(name for name, _ in self.gate_decisions) == tuple(
            name for name, _ in _GATES
        ))
        _require(all(type(value) is bool for _, value in self.gate_decisions))
        for decision in (
            self.e6_activation_authorized,
            self.network_authorized,
            self.publication_authorized,
            self.owner_registration_applied,
            self.owner_registration_replay,
        ):
            _require(type(decision) is bool)
        for identity in (
            self.orchestrator_request_sha256,
            self.orchestrator_correlation_sha256,
            self.eligibility_sha256,
            self.envelope_sha256,
            self.publication_identity_sha256,
            self.thesis_fingerprint_sha256,
        ):
            _require(identity is None or _SHA256.fullmatch(identity) is not None)
        for count in (
            self.telegram_attempt_count,
            self.deepseek_provider_attempt_count,
            self.claude_provider_attempt_count,
            self.publication_artifact_effect_count,
            self.telegram_send_attempt_effect_count,
            self.owner_decision_count,
            self.entry_active_mutation_count,
            self.slot_mutation_count,
            self.pair_lock_mutation_count,
            self.exchange_order_count,
        ):
            _require(type(count) is int and count >= 0)
        _require(self.telegram_attempt_count in (0, 1))
        _require(self.telegram_send_attempt_effect_count == self.telegram_attempt_count)
        _require(self.deepseek_provider_attempt_count in (0, 1))
        _require(self.claude_provider_attempt_count in (0, 1))
        _require(self.publication_artifact_effect_count == 0)
        _require(
            self.owner_decision_count
            == self.entry_active_mutation_count
            == self.slot_mutation_count
            == self.pair_lock_mutation_count
            == self.exchange_order_count
            == 0
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in self.__slots__
        }


def _gate_decisions(
    authorization: ControlledProductionSignalCycleAuthorizationV1,
) -> tuple[tuple[str, bool], ...]:
    return tuple((name, getattr(authorization, name)) for name, _ in _GATES)


def _result(
    *,
    root: E6ServiceCompositionRootV1,
    disposition: str,
    terminal_stage: str,
    reason_code: str,
    orchestrator: E6IntegratedOrchestratorResultV1 | None = None,
    delivery_completion_disposition: str = NOT_ATTEMPTED,
    telegram_attempt_count: int = 0,
) -> E6ServiceCycleResultV1:
    eligibility = None if orchestrator is None else orchestrator.publication_eligibility
    envelope = None if orchestrator is None else orchestrator.publication_envelope
    owner = None if orchestrator is None else orchestrator.owner_lifecycle_binding
    return E6ServiceCycleResultV1(
        result_version=E6_SERVICE_CYCLE_VERSION,
        result_schema=E6_SERVICE_CYCLE_SCHEMA,
        disposition=disposition,
        terminal_stage=terminal_stage,
        reason_code=reason_code,
        gate_decisions=_gate_decisions(root.authorization),
        e6_activation_authorized=root.e6_activation_authorized,
        network_authorized=root.network_authorized,
        publication_authorized=root.publication_authorized,
        orchestrator_disposition=(None if orchestrator is None else orchestrator.disposition),
        orchestrator_request_sha256=(
            None if orchestrator is None else orchestrator.request_sha256
        ),
        orchestrator_correlation_sha256=(
            None if orchestrator is None else orchestrator.correlation_sha256
        ),
        eligibility_sha256=(
            None if eligibility is None else eligibility.publication_eligibility_sha256
        ),
        envelope_sha256=(
            None if envelope is None else envelope.publication_envelope_sha256
        ),
        publication_identity_sha256=(
            None if envelope is None else envelope.publication_identity_sha256
        ),
        thesis_fingerprint_sha256=(
            None if envelope is None else envelope.thesis_fingerprint_sha256
        ),
        signal_id=None if envelope is None else envelope.signal_id,
        delivery_id=(None if owner is None else owner.binding.delivery_id),
        owner_lifecycle_binding_disposition=(
            None if owner is None else owner.classification
        ),
        owner_registration_applied=(
            False if owner is None else owner.registration_applied
        ),
        owner_registration_replay=False if owner is None else owner.replay,
        telegram_attempt_count=telegram_attempt_count,
        delivery_completion_disposition=delivery_completion_disposition,
        deepseek_provider_attempt_count=(
            0 if orchestrator is None else orchestrator.deepseek_provider_attempt_count
        ),
        claude_provider_attempt_count=(
            0 if orchestrator is None else orchestrator.claude_provider_attempt_count
        ),
        publication_artifact_effect_count=0,
        telegram_send_attempt_effect_count=telegram_attempt_count,
        owner_decision_count=0,
        entry_active_mutation_count=0,
        slot_mutation_count=0,
        pair_lock_mutation_count=0,
        exchange_order_count=0,
    )


def _strict_complete(
    request: E6ServiceCycleRequestV1,
    result: object,
) -> E6IntegratedOrchestratorResultV1:
    _require(type(result) is E6IntegratedOrchestratorResultV1)
    result.__post_init__()
    _require(result.disposition == ORCHESTRATOR_COMPLETE)
    _require(result.terminal_stage == STAGE_10_COMPLETE)
    _require(result.reason_code == ORCHESTRATOR_COMPLETE)
    _require(result.request_sha256 == request.orchestrator_request.request_sha256)
    eligibility = result.publication_eligibility
    envelope = result.publication_envelope
    owner = result.owner_lifecycle_binding
    _require(type(eligibility) is E6PublicationEligibilityResultV1)
    _require(type(envelope) is E6PublicationEnvelopeV1)
    _require(type(owner) is E6OwnerStateLifecycleBindingResultV1)
    eligibility.__post_init__()
    envelope.__post_init__()
    owner.__post_init__()
    _require(eligibility.eligible_to_build_publication_envelope is True)
    _require(
        eligibility.publication_eligibility_decision_code
        == ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE
    )
    _require(type(result.rendered_message) is str and bool(result.rendered_message.strip()))
    _require(result.rendered_message == format_e6_signal_message_v1(envelope))
    _require(envelope.publication_eligibility_sha256 == eligibility.publication_eligibility_sha256)
    _require(envelope.publication_identity_sha256 == eligibility.publication_identity_sha256)
    _require(envelope.thesis_fingerprint_sha256 == eligibility.thesis_fingerprint_sha256)
    _require(envelope.signal_id == request.orchestrator_request.publication_signal_id)
    _require(envelope.source_payload_hash == request.orchestrator_request.publication_source_payload_hash)
    _require(envelope.mode == request.orchestrator_request.publication_mode)
    binding = owner.binding
    _require(binding.publication_envelope_sha256 == envelope.publication_envelope_sha256)
    _require(binding.publication_identity_sha256 == envelope.publication_identity_sha256)
    _require(binding.thesis_fingerprint_sha256 == envelope.thesis_fingerprint_sha256)
    _require(binding.signal_id == envelope.signal_id)
    _require(binding.delivery_id == request.orchestrator_request.publication_delivery_id)
    _require(
        binding.delivery_id
        == build_delivery_id(
            signal_id=envelope.signal_id,
            channel=request.channel,
            destination_id=request.destination_id,
            publication_payload_hash=binding.publication_payload_hash,
        )
    )
    _require(owner.classification in {CREATED, OWNER_IDEMPOTENT_REPLAY})
    return result


def _validated_receipt(
    value: object,
    *,
    channel: str,
    destination_id: str,
    published_at: str,
) -> Mapping[str, object]:
    _require(isinstance(value, Mapping))
    _require(set(value) == {"channel", "destination_id", "external_delivery_id", "delivered_at"})
    _require(value["channel"] == channel)
    _require(str(value["destination_id"]) == destination_id)
    _require(type(value["external_delivery_id"]) is str and bool(value["external_delivery_id"].strip()))
    delivered_at = value["delivered_at"]
    _require(type(delivered_at) is str and _UTC.fullmatch(delivered_at) is not None)
    parsed = datetime.fromisoformat(delivered_at.removesuffix("Z") + "+00:00")
    _require(parsed.tzinfo == timezone.utc)
    publication_time = datetime.fromisoformat(
        published_at.removesuffix("Z") + "+00:00"
    )
    _require(publication_time.tzinfo == timezone.utc)
    _require(parsed >= publication_time)
    return value


def run_e6_service_cycle_v1(
    *,
    root: E6ServiceCompositionRootV1,
    request: E6ServiceCycleRequestV1,
) -> E6ServiceCycleResultV1:
    """Run one default-deny E6 cycle with at most one Telegram attempt."""

    _require(type(root) is E6ServiceCompositionRootV1)
    root.__post_init__()
    try:
        _require(type(request) is E6ServiceCycleRequestV1)
        request.__post_init__()
    except Exception:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_1_VALIDATE_ROOT_REQUEST_AND_AUTHORIZATION,
            reason_code=INVALID_ROOT_OR_REQUEST,
        )

    for name, classification in _GATES:
        if getattr(root.authorization, name) is not True:
            return _result(
                root=root,
                disposition=DRY,
                terminal_stage=STAGE_1_VALIDATE_ROOT_REQUEST_AND_AUTHORIZATION,
                reason_code=classification,
            )
    for decision, reason in (
        (root.e6_activation_authorized, E6_ACTIVATION_NOT_AUTHORIZED),
        (root.network_authorized, E6_NETWORK_NOT_AUTHORIZED),
        (root.publication_authorized, E6_PUBLICATION_NOT_AUTHORIZED),
    ):
        if decision is not True:
            return _result(
                root=root,
                disposition=DRY,
                terminal_stage=STAGE_1_VALIDATE_ROOT_REQUEST_AND_AUTHORIZATION,
                reason_code=reason,
            )
    if root.telegram_delivery is None:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_1_VALIDATE_ROOT_REQUEST_AND_AUTHORIZATION,
            reason_code=INVALID_ROOT_OR_REQUEST,
        )

    try:
        raw_orchestrator = root.orchestrator(
            request=request.orchestrator_request,
            ports=request.orchestrator_ports,
        )
    except Exception:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
            reason_code=E6_ORCHESTRATOR_FAILED,
        )
    if type(raw_orchestrator) is not E6IntegratedOrchestratorResultV1:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
            reason_code=E6_ORCHESTRATOR_FAILED,
        )
    try:
        raw_orchestrator.__post_init__()
    except Exception:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
            reason_code=E6_ORCHESTRATOR_FAILED,
        )
    if raw_orchestrator.disposition != ORCHESTRATOR_COMPLETE:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
            reason_code=E6_ORCHESTRATOR_TERMINAL,
            orchestrator=raw_orchestrator,
        )

    try:
        orchestrator = _strict_complete(request, raw_orchestrator)
    except Exception:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_3_REQUIRE_EXACT_E6_ELIGIBILITY,
            reason_code=E6_ELIGIBILITY_OR_LINEAGE_INVALID,
        )

    owner = orchestrator.owner_lifecycle_binding
    if owner.classification == OWNER_IDEMPOTENT_REPLAY:
        return _result(
            root=root,
            disposition=IDEMPOTENT_REPLAY,
            terminal_stage=STAGE_4_DELIVERY_IDEMPOTENCY_PREFLIGHT,
            reason_code=IDEMPOTENT_COMPLETED_REPLAY,
            orchestrator=orchestrator,
            delivery_completion_disposition=IDEMPOTENT_COMPLETED_REPLAY,
        )
    if owner.classification != CREATED:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_4_DELIVERY_IDEMPOTENCY_PREFLIGHT,
            reason_code=E6_DELIVERY_REPLAY_CONFLICT,
            orchestrator=orchestrator,
        )

    delivery_request = E6TelegramDeliveryRequestV1(
        rendered_message=orchestrator.rendered_message,
        publication_eligibility=orchestrator.publication_eligibility,
        publication_envelope=orchestrator.publication_envelope,
        owner_lifecycle_binding=owner,
        delivery_id=owner.binding.delivery_id,
    )
    try:
        receipt = root.telegram_delivery(
            delivery_request,
            channel=request.channel,
            destination_id=request.destination_id,
        )
        _validated_receipt(
            receipt,
            channel=request.channel,
            destination_id=request.destination_id,
            published_at=request.orchestrator_request.publication_published_at,
        )
    except Exception:
        return _result(
            root=root,
            disposition=HOLD,
            terminal_stage=STAGE_5_ONE_TELEGRAM_ATTEMPT,
            reason_code=TELEGRAM_DELIVERY_FAILED,
            orchestrator=orchestrator,
            delivery_completion_disposition=TELEGRAM_DELIVERY_FAILED,
            telegram_attempt_count=1,
        )
    return _result(
        root=root,
        disposition=DELIVERED,
        terminal_stage=STAGE_6_COMPLETE_DELIVERY_EVIDENCE,
        reason_code=DELIVERY_COMPLETED,
        orchestrator=orchestrator,
        delivery_completion_disposition=DELIVERY_COMPLETED,
        telegram_attempt_count=1,
    )


__all__ = (
    "E6ServiceCompositionRootV1",
    "E6ServiceCycleRequestV1",
    "E6ServiceCycleResultV1",
    "run_e6_service_cycle_v1",
)
