import json
import httpx
from datetime import datetime, timezone
import uuid

from engine.quota_slot_worker_v4 import run_quota_slot_worker_v4
from engine.quota_slot_engine_v4 import QuotaSlotRejected

class Phase09RTelegramDeliveryAdapterV1:
    def __init__(
        self,
        config,
        *,
        quota_now_provider=None,
        reservation_id_provider=None,
    ):
        self.config = config
        self.quota_now_provider = quota_now_provider or (lambda: datetime.now(timezone.utc))
        self.reservation_id_provider = reservation_id_provider or (lambda: str(uuid.uuid4()))
        self.rejection_reason = None
        self.malformed_receipt = False

    def __call__(self, payload, channel, destination_id):
        if channel != "TELEGRAM":
            raise ValueError("Unsupported channel")

        def do_delivery(*, state_path):
            text = json.dumps(payload, separators=(',', ':'))
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

            return {
                "channel": channel,
                "destination_id": destination_id,
                "external_delivery_id": str(message_id),
                "delivered_at": self.quota_now_provider().strftime("%Y-%m-%dT%H:%M:%SZ")
            }

        try:
            result = run_quota_slot_worker_v4(
                subject_id="autonomous:production_signal:v1",
                window_id=self.config.window_id,
                quota_limit=self.config.quota_limit,
                slot_capacity=self.config.slot_capacity,
                quota_state_path=self.config.quota_state_path,
                worker_state_path=self.config.worker_state_path,
                quota_now_provider=self.quota_now_provider,
                reservation_id_provider=self.reservation_id_provider,
                worker=do_delivery,
            )
        except QuotaSlotRejected as exc:
            self.rejection_reason = exc.reason_code
            raise

        return result["worker_result"]
