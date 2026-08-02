from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

import httpx

from engine.e6_owner_state_lifecycle_binding_v1 import (
    CREATED,
    E6OwnerStateLifecycleBindingResultV1,
)
from engine.e6_publication_eligibility_v1 import (
    ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE,
    E6PublicationEligibilityResultV1,
)
from engine.e6_publication_envelope_v1 import E6PublicationEnvelopeV1
from engine.e6_telegram_human_formatter_v1 import format_e6_signal_message_v1
from engine.production_signal_contract_v1 import build_delivery_id
from engine.telegram_human_formatter_v1 import format_signal_message


@dataclass(frozen=True, slots=True)
class E6TelegramDeliveryRequestV1:
    """Strict E6 presentation and delivery identity passed to Telegram."""

    rendered_message: str
    publication_eligibility: E6PublicationEligibilityResultV1
    publication_envelope: E6PublicationEnvelopeV1
    owner_lifecycle_binding: E6OwnerStateLifecycleBindingResultV1
    delivery_id: str

    def __post_init__(self) -> None:
        try:
            eligibility = self.publication_eligibility
            envelope = self.publication_envelope
            owner = self.owner_lifecycle_binding
            if type(eligibility) is not E6PublicationEligibilityResultV1:
                raise ValueError
            if type(envelope) is not E6PublicationEnvelopeV1:
                raise ValueError
            if type(owner) is not E6OwnerStateLifecycleBindingResultV1:
                raise ValueError
            eligibility.__post_init__()
            envelope.__post_init__()
            owner.__post_init__()
            if eligibility.eligible_to_build_publication_envelope is not True:
                raise ValueError
            if (
                eligibility.publication_eligibility_decision_code
                != ELIGIBLE_TO_BUILD_PUBLICATION_ENVELOPE
            ):
                raise ValueError
            if envelope.publication_eligibility_sha256 != (
                eligibility.publication_eligibility_sha256
            ):
                raise ValueError
            if envelope.publication_identity_sha256 != (
                eligibility.publication_identity_sha256
            ):
                raise ValueError
            if envelope.thesis_fingerprint_sha256 != (
                eligibility.thesis_fingerprint_sha256
            ):
                raise ValueError
            if owner.classification != CREATED:
                raise ValueError
            binding = owner.binding
            if binding.publication_envelope_sha256 != envelope.publication_envelope_sha256:
                raise ValueError
            if binding.publication_identity_sha256 != envelope.publication_identity_sha256:
                raise ValueError
            if binding.thesis_fingerprint_sha256 != envelope.thesis_fingerprint_sha256:
                raise ValueError
            if binding.signal_id != envelope.signal_id:
                raise ValueError
            if type(self.delivery_id) is not str or self.delivery_id != binding.delivery_id:
                raise ValueError
            if type(self.rendered_message) is not str or not self.rendered_message.strip():
                raise ValueError
            if self.rendered_message != format_e6_signal_message_v1(envelope):
                raise ValueError
        except Exception:
            raise ValueError("invalid E6 Telegram delivery request") from None


class Phase09RTelegramDeliveryAdapterV1:
    def __init__(
        self,
        config,
        *,
        quota_now_provider=None,
        reservation_id_provider=None,
        available_slots_provider=None,
        message_binding_recorder=None,
        http_post=None,
    ):
        self.config = config
        self.quota_now_provider = quota_now_provider or (lambda: datetime.now(timezone.utc))
        self.reservation_id_provider = reservation_id_provider or (lambda: str(uuid.uuid4()))
        self.available_slots_provider = available_slots_provider or (lambda _style: 3)
        self.message_binding_recorder = message_binding_recorder
        self.http_post = http_post
        self.rejection_reason = None
        self.malformed_receipt = False

    def __call__(self, payload, channel, destination_id):
        if channel != "TELEGRAM":
            raise ValueError("Unsupported channel")

        def do_delivery(*, state_path):
            if type(payload) is E6TelegramDeliveryRequestV1:
                payload.__post_init__()
                if payload.delivery_id != build_delivery_id(
                    signal_id=payload.publication_envelope.signal_id,
                    channel=channel,
                    destination_id=str(destination_id),
                    publication_payload_hash=(
                        payload.owner_lifecycle_binding.binding.publication_payload_hash
                    ),
                ):
                    raise ValueError("E6 delivery identity mismatch")
                text = payload.rendered_message
                binding_payload = {
                    "signal_id": payload.publication_envelope.signal_id,
                    "symbol": payload.publication_envelope.canonical_pair,
                    "mode": payload.publication_envelope.mode,
                }
            else:
                text = format_signal_message(
                    payload,
                    available_slots=self.available_slots_provider(payload["mode"]),
                )
                binding_payload = payload
            if len(text) > self.config.max_response_chars:
                raise RuntimeError("Telegram message exceeds configured maximum")
            url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"

            try:
                post = self.http_post or httpx.post
                resp = post(
                    url,
                    json={"chat_id": destination_id, "text": text},
                    timeout=10.0
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                raise RuntimeError("Telegram delivery network failure") from e

            if not data.get("ok"):
                raise RuntimeError(f"Telegram delivery failed")

            result = data.get("result", {})
            message_id = result.get("message_id")
            if message_id is None:
                self.malformed_receipt = True
                raise RuntimeError("Malformed receipt: missing message_id")

            delivered_at = self.quota_now_provider().strftime("%Y-%m-%dT%H:%M:%SZ")
            if self.message_binding_recorder is not None:
                self.message_binding_recorder(
                    payload=binding_payload, destination_id=str(destination_id),
                    message_id=int(message_id), timestamp=delivered_at,
                )

            return {
                "channel": channel,
                "destination_id": destination_id,
                "external_delivery_id": str(message_id),
                "delivered_at": delivered_at
            }
        return do_delivery(state_path=None)


__all__ = (
    "E6TelegramDeliveryRequestV1",
    "Phase09RTelegramDeliveryAdapterV1",
)
