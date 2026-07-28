import httpx
from datetime import datetime, timezone
import uuid
from engine.telegram_human_formatter_v1 import format_signal_message

class Phase09RTelegramDeliveryAdapterV1:
    def __init__(
        self,
        config,
        *,
        quota_now_provider=None,
        reservation_id_provider=None,
        available_slots_provider=None,
        message_binding_recorder=None,
    ):
        self.config = config
        self.quota_now_provider = quota_now_provider or (lambda: datetime.now(timezone.utc))
        self.reservation_id_provider = reservation_id_provider or (lambda: str(uuid.uuid4()))
        self.available_slots_provider = available_slots_provider or (lambda _style: 3)
        self.message_binding_recorder = message_binding_recorder
        self.rejection_reason = None
        self.malformed_receipt = False

    def __call__(self, payload, channel, destination_id):
        if channel != "TELEGRAM":
            raise ValueError("Unsupported channel")

        def do_delivery(*, state_path):
            text = format_signal_message(
                payload, available_slots=self.available_slots_provider(payload["mode"]),
            )
            if len(text) > self.config.max_response_chars:
                raise RuntimeError("Telegram message exceeds configured maximum")
            url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"

            try:
                resp = httpx.post(
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
                    payload=payload, destination_id=str(destination_id),
                    message_id=int(message_id), timestamp=delivered_at,
                )

            return {
                "channel": channel,
                "destination_id": destination_id,
                "external_delivery_id": str(message_id),
                "delivered_at": delivered_at
            }
        return do_delivery(state_path=None)
