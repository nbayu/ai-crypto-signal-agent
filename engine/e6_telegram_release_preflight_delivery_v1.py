"""Isolated one-attempt delivery for the fixed E6 Telegram release preflight."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import socket
import ssl
from typing import Callable, Final

import httpx


MODULE_VERSION: Final = "e6-telegram-release-preflight-delivery-v1"
MODULE_SCHEMA: Final = "ai-crypto-signal-agent.e6-telegram-release-preflight-delivery.v1"
REQUEST_VERSION: Final = "e6-telegram-release-preflight-request-v1"
REQUEST_SCHEMA: Final = "E6TelegramReleasePreflightRequestV1"
RECEIPT_VERSION: Final = "e6-telegram-release-preflight-receipt-v1"
RECEIPT_SCHEMA: Final = "E6TelegramReleasePreflightReceiptV1"

MESSAGE_CLASS: Final = "FIXED_BENIGN_NON_TRADING_RELEASE_PREFLIGHT"
CHANNEL: Final = "TELEGRAM"
HTTP_METHOD: Final = "POST"
ENDPOINT_TEMPLATE: Final = "https://api.telegram.org/bot{token}/sendMessage"
PARSE_MODE: Final = "NONE"
DISABLE_NOTIFICATION: Final = True
DEFAULT_TIMEOUT_SECONDS: Final = 10
MAX_ATTEMPTS: Final = 1
AUTOMATIC_RETRY_COUNT: Final = 0

PASS_TELEGRAM_AUTH_DESTINATION_AND_DELIVERY: Final = (
    "PASS_TELEGRAM_AUTH_DESTINATION_AND_DELIVERY"
)
HOLD_TELEGRAM_AUTHENTICATION_REJECTED: Final = (
    "HOLD_TELEGRAM_AUTHENTICATION_REJECTED"
)
HOLD_TELEGRAM_BOT_BLOCKED_OR_FORBIDDEN: Final = (
    "HOLD_TELEGRAM_BOT_BLOCKED_OR_FORBIDDEN"
)
HOLD_TELEGRAM_DESTINATION_INVALID_OR_UNAVAILABLE: Final = (
    "HOLD_TELEGRAM_DESTINATION_INVALID_OR_UNAVAILABLE"
)
HOLD_TELEGRAM_RATE_LIMIT: Final = "HOLD_TELEGRAM_RATE_LIMIT"
HOLD_TELEGRAM_INVALID_REQUEST_CONTRACT: Final = (
    "HOLD_TELEGRAM_INVALID_REQUEST_CONTRACT"
)
HOLD_TELEGRAM_SERVER_ERROR: Final = "HOLD_TELEGRAM_SERVER_ERROR"
HOLD_TELEGRAM_DNS_FAILURE: Final = "HOLD_TELEGRAM_DNS_FAILURE"
HOLD_TELEGRAM_TLS_FAILURE: Final = "HOLD_TELEGRAM_TLS_FAILURE"
HOLD_TELEGRAM_CONNECT_TIMEOUT: Final = "HOLD_TELEGRAM_CONNECT_TIMEOUT"
HOLD_TELEGRAM_READ_TIMEOUT: Final = "HOLD_TELEGRAM_READ_TIMEOUT"
HOLD_TELEGRAM_NETWORK_FAILURE: Final = "HOLD_TELEGRAM_NETWORK_FAILURE"
HOLD_TELEGRAM_RESPONSE_NOT_JSON: Final = "HOLD_TELEGRAM_RESPONSE_NOT_JSON"
HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID: Final = (
    "HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID"
)
HOLD_TELEGRAM_RETURNED_CHAT_ID_MISMATCH: Final = (
    "HOLD_TELEGRAM_RETURNED_CHAT_ID_MISMATCH"
)

TELEGRAM_PREFLIGHT_PUBLICATION_AUTHORITY: Final = "NO"
TELEGRAM_PREFLIGHT_OWNER_DECISION_AUTHORITY: Final = "NO"
TELEGRAM_PREFLIGHT_ENTRY_ACTIVE_AUTHORITY: Final = "NO"
TELEGRAM_PREFLIGHT_EXCHANGE_AUTHORITY: Final = "NO"
TELEGRAM_PREFLIGHT_GENERAL_RAW_TEXT_AUTHORITY: Final = "NO"

_REQUEST_ERROR: Final = "invalid E6 Telegram release preflight request"
_RECEIPT_ERROR: Final = "invalid E6 Telegram release preflight receipt"
_ADAPTER_ERROR: Final = "invalid E6 Telegram release preflight adapter"
_HEAD_PATTERN: Final = re.compile(r"[0-9a-f]{40}")
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_UTC_PATTERN: Final = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

_FAILURE_CLASSIFICATIONS: Final = frozenset(
    {
        HOLD_TELEGRAM_AUTHENTICATION_REJECTED,
        HOLD_TELEGRAM_BOT_BLOCKED_OR_FORBIDDEN,
        HOLD_TELEGRAM_DESTINATION_INVALID_OR_UNAVAILABLE,
        HOLD_TELEGRAM_RATE_LIMIT,
        HOLD_TELEGRAM_INVALID_REQUEST_CONTRACT,
        HOLD_TELEGRAM_SERVER_ERROR,
        HOLD_TELEGRAM_DNS_FAILURE,
        HOLD_TELEGRAM_TLS_FAILURE,
        HOLD_TELEGRAM_CONNECT_TIMEOUT,
        HOLD_TELEGRAM_READ_TIMEOUT,
        HOLD_TELEGRAM_NETWORK_FAILURE,
        HOLD_TELEGRAM_RESPONSE_NOT_JSON,
        HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID,
        HOLD_TELEGRAM_RETURNED_CHAT_ID_MISMATCH,
    }
)


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except Exception:
        raise ValueError(_REQUEST_ERROR) from None


def _hash_value(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _valid_sha256(value: object) -> bool:
    return type(value) is str and _SHA256_PATTERN.fullmatch(value) is not None


def _valid_utc(value: object) -> bool:
    if type(value) is not str or _UTC_PATTERN.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo == timezone.utc and parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_utc(value: object) -> str:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise E6TelegramReleasePreflightDeliveryErrorV1(
            HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID
        ) from None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _request_preimage(request: "E6TelegramReleasePreflightRequestV1") -> dict[str, object]:
    return {
        "request_version": REQUEST_VERSION,
        "request_schema": REQUEST_SCHEMA,
        "message_class": MESSAGE_CLASS,
        "candidate_head": request.candidate_head,
        "destination_id": request.destination_id,
        "requested_at": request.requested_at,
    }


@dataclass(frozen=True, slots=True)
class E6TelegramReleasePreflightRequestV1:
    """A fixed-purpose request with no caller-controlled message or credential."""

    candidate_head: str
    destination_id: int
    requested_at: str
    request_version: str = field(init=False, default=REQUEST_VERSION)
    request_schema: str = field(init=False, default=REQUEST_SCHEMA)
    message_class: str = field(init=False, default=MESSAGE_CLASS)
    request_identity_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            if (
                type(self.candidate_head) is not str
                or _HEAD_PATTERN.fullmatch(self.candidate_head) is None
                or type(self.destination_id) is not int
                or self.destination_id == 0
                or not _valid_utc(self.requested_at)
            ):
                raise ValueError
            object.__setattr__(
                self,
                "request_identity_sha256",
                _hash_value(_request_preimage(self)),
            )
        except Exception:
            raise ValueError(_REQUEST_ERROR) from None


def build_e6_telegram_release_preflight_message_v1(
    request: E6TelegramReleasePreflightRequestV1,
) -> str:
    """Build the sole message this contract has authority to send."""

    if type(request) is not E6TelegramReleasePreflightRequestV1:
        raise ValueError(_REQUEST_ERROR) from None
    request.__post_init__()
    return "\n".join(
        (
            "AI Crypto Signal Agent E6 Telegram test delivery.",
            "This is a non-trading release preflight.",
            "No trading action is required.",
            f"Candidate: {request.candidate_head[:12]}",
        )
    )


def _receipt_preimage(receipt: "E6TelegramReleasePreflightReceiptV1") -> dict[str, object]:
    return {
        "receipt_version": RECEIPT_VERSION,
        "receipt_schema": RECEIPT_SCHEMA,
        "request_identity_sha256": receipt.request_identity_sha256,
        "channel": CHANNEL,
        "classification": PASS_TELEGRAM_AUTH_DESTINATION_AND_DELIVERY,
        "delivered": True,
        "http_status": receipt.http_status,
        "external_delivery_id": receipt.external_delivery_id,
        "returned_chat_id_match": receipt.returned_chat_id_match,
        "attempt_count": receipt.attempt_count,
        "automatic_retry_count": receipt.automatic_retry_count,
        "delivered_at": receipt.delivered_at,
    }


@dataclass(frozen=True, slots=True)
class E6TelegramReleasePreflightReceiptV1:
    """Sanitized PASS receipt; chat identifiers never cross this boundary."""

    request_identity_sha256: str
    http_status: int
    external_delivery_id: str
    returned_chat_id_match: bool
    attempt_count: int
    automatic_retry_count: int
    delivered_at: str
    receipt_version: str = field(init=False, default=RECEIPT_VERSION)
    receipt_schema: str = field(init=False, default=RECEIPT_SCHEMA)
    channel: str = field(init=False, default=CHANNEL)
    classification: str = field(
        init=False,
        default=PASS_TELEGRAM_AUTH_DESTINATION_AND_DELIVERY,
    )
    delivered: bool = field(init=False, default=True)
    receipt_identity_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            if (
                not _valid_sha256(self.request_identity_sha256)
                or type(self.http_status) is not int
                or not 200 <= self.http_status <= 299
                or type(self.external_delivery_id) is not str
                or not self.external_delivery_id.isdecimal()
                or int(self.external_delivery_id) <= 0
                or self.returned_chat_id_match is not True
                or self.attempt_count != MAX_ATTEMPTS
                or self.automatic_retry_count != AUTOMATIC_RETRY_COUNT
                or not _valid_utc(self.delivered_at)
            ):
                raise ValueError
            object.__setattr__(
                self,
                "receipt_identity_sha256",
                _hash_value(_receipt_preimage(self)),
            )
        except Exception:
            raise ValueError(_RECEIPT_ERROR) from None


class E6TelegramReleasePreflightDeliveryErrorV1(RuntimeError):
    """Fixed public failure evidence with no raw transport or Telegram detail."""

    __slots__ = ("classification", "attempt_count", "automatic_retry_count")

    def __init__(self, classification: str) -> None:
        if classification not in _FAILURE_CLASSIFICATIONS:
            classification = HOLD_TELEGRAM_NETWORK_FAILURE
        self.classification = classification
        self.attempt_count = MAX_ATTEMPTS
        self.automatic_retry_count = AUTOMATIC_RETRY_COUNT
        super().__init__(classification)


def _delivery_failure(classification: str) -> None:
    raise E6TelegramReleasePreflightDeliveryErrorV1(classification) from None


def _build_httpx_client(
    *,
    timeout_seconds: int,
    follow_redirects: bool,
    trust_env: bool,
    http2: bool,
    maximum_attempts: int,
) -> httpx.Client:
    if (
        timeout_seconds != DEFAULT_TIMEOUT_SECONDS
        or follow_redirects is not False
        or trust_env is not False
        or http2 is not False
        or maximum_attempts != MAX_ATTEMPTS
    ):
        raise ValueError(_ADAPTER_ERROR) from None
    return httpx.Client(
        transport=httpx.HTTPTransport(retries=0),
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=False,
        trust_env=False,
        http2=False,
    )


def _chain_contains(error: BaseException, exception_type: type[BaseException]) -> bool:
    current: BaseException | None = error
    seen: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            return False
        if isinstance(current, exception_type):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


def _status_failure(status_code: int) -> str:
    if status_code == 401:
        return HOLD_TELEGRAM_AUTHENTICATION_REJECTED
    if status_code == 403:
        return HOLD_TELEGRAM_BOT_BLOCKED_OR_FORBIDDEN
    if status_code in (400, 404):
        return HOLD_TELEGRAM_DESTINATION_INVALID_OR_UNAVAILABLE
    if status_code == 429:
        return HOLD_TELEGRAM_RATE_LIMIT
    if 500 <= status_code <= 599:
        return HOLD_TELEGRAM_SERVER_ERROR
    return HOLD_TELEGRAM_INVALID_REQUEST_CONTRACT


@dataclass(frozen=True, slots=True)
class E6TelegramReleasePreflightDeliveryAdapterV1:
    """Passive fixed-message adapter with one POST attempt and no retry."""

    bot_token: str = field(repr=False)
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    http_client_factory: Callable[..., httpx.Client] = field(
        default=_build_httpx_client,
        repr=False,
        compare=False,
    )
    now_provider: Callable[[], datetime] = field(
        default=_utc_now,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        try:
            if (
                type(self.bot_token) is not str
                or not self.bot_token
                or len(self.bot_token.encode("utf-8")) > 4096
                or any(character in self.bot_token for character in ("\x00", "\r", "\n"))
                or type(self.timeout_seconds) is not int
                or self.timeout_seconds != DEFAULT_TIMEOUT_SECONDS
                or not callable(self.http_client_factory)
                or not callable(self.now_provider)
            ):
                raise ValueError
        except Exception:
            raise ValueError(_ADAPTER_ERROR) from None

    def __call__(
        self,
        request: E6TelegramReleasePreflightRequestV1,
    ) -> E6TelegramReleasePreflightReceiptV1:
        if type(request) is not E6TelegramReleasePreflightRequestV1:
            raise ValueError(_REQUEST_ERROR) from None
        request.__post_init__()
        message = build_e6_telegram_release_preflight_message_v1(request)
        endpoint = ENDPOINT_TEMPLATE.format(token=self.bot_token)
        body = {
            "chat_id": request.destination_id,
            "text": message,
            "disable_notification": True,
        }

        client: httpx.Client | None = None
        try:
            client = self.http_client_factory(
                timeout_seconds=self.timeout_seconds,
                follow_redirects=False,
                trust_env=False,
                http2=False,
                maximum_attempts=MAX_ATTEMPTS,
            )
            response = client.post(endpoint, json=body)
        except httpx.ConnectTimeout:
            _delivery_failure(HOLD_TELEGRAM_CONNECT_TIMEOUT)
        except httpx.ReadTimeout:
            _delivery_failure(HOLD_TELEGRAM_READ_TIMEOUT)
        except socket.gaierror:
            _delivery_failure(HOLD_TELEGRAM_DNS_FAILURE)
        except ssl.SSLError:
            _delivery_failure(HOLD_TELEGRAM_TLS_FAILURE)
        except httpx.ConnectError as error:
            if _chain_contains(error, socket.gaierror):
                _delivery_failure(HOLD_TELEGRAM_DNS_FAILURE)
            if _chain_contains(error, ssl.SSLError):
                _delivery_failure(HOLD_TELEGRAM_TLS_FAILURE)
            _delivery_failure(HOLD_TELEGRAM_NETWORK_FAILURE)
        except (httpx.HTTPError, OSError, Exception):
            _delivery_failure(HOLD_TELEGRAM_NETWORK_FAILURE)
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

        if type(response) is not httpx.Response or type(response.status_code) is not int:
            _delivery_failure(HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID)
        status_code = response.status_code
        if not 200 <= status_code <= 299:
            _delivery_failure(_status_failure(status_code))
        try:
            response_mapping = response.json()
        except Exception:
            _delivery_failure(HOLD_TELEGRAM_RESPONSE_NOT_JSON)
        if type(response_mapping) is not dict or response_mapping.get("ok") is not True:
            _delivery_failure(HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID)
        result = response_mapping.get("result")
        if type(result) is not dict:
            _delivery_failure(HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID)
        message_id = result.get("message_id")
        returned_chat = result.get("chat")
        if (
            type(message_id) is not int
            or message_id <= 0
            or type(returned_chat) is not dict
            or type(returned_chat.get("id")) is not int
        ):
            _delivery_failure(HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID)
        if returned_chat["id"] != request.destination_id:
            _delivery_failure(HOLD_TELEGRAM_RETURNED_CHAT_ID_MISMATCH)

        return E6TelegramReleasePreflightReceiptV1(
            request_identity_sha256=request.request_identity_sha256,
            http_status=status_code,
            external_delivery_id=str(message_id),
            returned_chat_id_match=True,
            attempt_count=MAX_ATTEMPTS,
            automatic_retry_count=AUTOMATIC_RETRY_COUNT,
            delivered_at=_normalized_utc(self.now_provider()),
        )


__all__ = (
    "MODULE_VERSION",
    "MODULE_SCHEMA",
    "MESSAGE_CLASS",
    "HTTP_METHOD",
    "ENDPOINT_TEMPLATE",
    "PARSE_MODE",
    "DISABLE_NOTIFICATION",
    "MAX_ATTEMPTS",
    "AUTOMATIC_RETRY_COUNT",
    "PASS_TELEGRAM_AUTH_DESTINATION_AND_DELIVERY",
    "E6TelegramReleasePreflightRequestV1",
    "E6TelegramReleasePreflightReceiptV1",
    "E6TelegramReleasePreflightDeliveryErrorV1",
    "E6TelegramReleasePreflightDeliveryAdapterV1",
    "build_e6_telegram_release_preflight_message_v1",
    "TELEGRAM_PREFLIGHT_PUBLICATION_AUTHORITY",
    "TELEGRAM_PREFLIGHT_OWNER_DECISION_AUTHORITY",
    "TELEGRAM_PREFLIGHT_ENTRY_ACTIVE_AUTHORITY",
    "TELEGRAM_PREFLIGHT_EXCHANGE_AUTHORITY",
    "TELEGRAM_PREFLIGHT_GENERAL_RAW_TEXT_AUTHORITY",
)
