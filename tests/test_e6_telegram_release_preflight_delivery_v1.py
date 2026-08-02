import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import socket
import ssl
import warnings

import httpx
import pytest

import engine.e6_telegram_release_preflight_delivery_v1 as subject


HEAD = "ad508d2ad349e66651eead7450670ddee1890dee"
DESTINATION_ID = -1001234567890
REQUESTED_AT = "2026-08-02T12:00:00Z"
DELIVERED_AT = datetime(2026, 8, 2, 12, 0, 1, tzinfo=timezone.utc)
SYNTHETIC_TOKEN = "fixture-only-telegram-token"
RAW_SECRET = "raw-telegram-description-or-exception-secret"
EXPECTED_MESSAGE = "\n".join(
    (
        "AI Crypto Signal Agent E6 Telegram test delivery.",
        "This is a non-trading release preflight.",
        "No trading action is required.",
        "Candidate: ad508d2ad349",
    )
)


def _request(**changes):
    values = {
        "candidate_head": HEAD,
        "destination_id": DESTINATION_ID,
        "requested_at": REQUESTED_AT,
    }
    values.update(changes)
    return subject.E6TelegramReleasePreflightRequestV1(**values)


def _mapping(**changes):
    value = {
        "ok": True,
        "result": {
            "message_id": 913,
            "chat": {"id": DESTINATION_ID},
        },
    }
    value.update(changes)
    return value


def _response(mapping=None, *, status=200, content=None):
    if content is None:
        content = json.dumps(
            _mapping() if mapping is None else mapping,
            separators=(",", ":"),
        ).encode("utf-8")
    return httpx.Response(
        status,
        headers={"Content-Type": "application/json"},
        content=content,
    )


def _adapter(handler, captured=None):
    if captured is None:
        captured = {}

    def counted_handler(http_request):
        captured["attempt_count"] = captured.get("attempt_count", 0) + 1
        captured["request"] = http_request
        return handler(http_request)

    def client_factory(**policy):
        captured["client_factory_count"] = captured.get("client_factory_count", 0) + 1
        captured["policy"] = policy
        return httpx.Client(
            transport=httpx.MockTransport(counted_handler),
            timeout=httpx.Timeout(policy["timeout_seconds"]),
            follow_redirects=policy["follow_redirects"],
            trust_env=policy["trust_env"],
            http2=policy["http2"],
        )

    adapter = subject.E6TelegramReleasePreflightDeliveryAdapterV1(
        bot_token=SYNTHETIC_TOKEN,
        http_client_factory=client_factory,
        now_provider=lambda: DELIVERED_AT,
    )
    return adapter, captured


def _assert_failure(handler, classification):
    adapter, captured = _adapter(handler)
    with pytest.raises(subject.E6TelegramReleasePreflightDeliveryErrorV1) as caught:
        adapter(_request())
    assert caught.value.classification == classification
    assert str(caught.value) == classification
    assert caught.value.attempt_count == 1
    assert caught.value.automatic_retry_count == 0
    assert captured["attempt_count"] == 1
    assert captured["client_factory_count"] == 1
    return caught.value


def test_request_receipt_and_adapter_are_frozen_slotted_and_versioned():
    request = _request()
    adapter, _ = _adapter(lambda _: _response())
    receipt = adapter(request)
    for value in (request, receipt, adapter):
        assert is_dataclass(value)
        assert value.__dataclass_params__.frozen is True
        assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        request.candidate_head = "0" * 40
    with pytest.raises(FrozenInstanceError):
        receipt.delivered = False
    assert request.request_version == subject.REQUEST_VERSION
    assert request.request_schema == subject.REQUEST_SCHEMA
    assert receipt.receipt_version == subject.RECEIPT_VERSION
    assert receipt.receipt_schema == subject.RECEIPT_SCHEMA


@pytest.mark.parametrize(
    "head",
    (
        "",
        "a" * 39,
        "a" * 41,
        "A" * 40,
        "g" * 40,
        "ad508d2ad349e66651eead7450670ddee1890de-",
        1,
        None,
    ),
)
def test_candidate_head_requires_exact_40_lowercase_hex(head):
    with pytest.raises(ValueError, match="invalid E6 Telegram release preflight request"):
        _request(candidate_head=head)


@pytest.mark.parametrize("destination_id", (True, False, 0, "-1001", 1.0, None))
def test_destination_requires_an_integer_and_rejects_booleans(destination_id):
    with pytest.raises(ValueError, match="invalid E6 Telegram release preflight request"):
        _request(destination_id=destination_id)


@pytest.mark.parametrize(
    "requested_at",
    (
        "2026-08-02T12:00:00+00:00",
        "2026-08-02T12:00:00.000Z",
        "2026-08-02T12:00:00z",
        "2026-02-30T12:00:00Z",
        "",
    ),
)
def test_requested_at_requires_normalized_second_precision_utc(requested_at):
    with pytest.raises(ValueError, match="invalid E6 Telegram release preflight request"):
        _request(requested_at=requested_at)


def test_fixed_message_is_exact_benign_and_has_only_candidate_prefix():
    message = subject.build_e6_telegram_release_preflight_message_v1(_request())
    assert message == EXPECTED_MESSAGE
    assert HEAD[:12] in message
    assert HEAD[12:] not in message
    lowered = message.casefold()
    for forbidden in (
        "pair:",
        "symbol:",
        "direction:",
        "entry:",
        "stop:",
        "target:",
        "leverage:",
        "owner approval",
        "provider output",
        "account",
        "exchange",
    ):
        assert forbidden not in lowered


def test_no_arbitrary_text_request_field_or_general_raw_text_call_exists():
    request_fields = tuple(field.name for field in fields(subject.E6TelegramReleasePreflightRequestV1))
    assert request_fields == (
        "candidate_head",
        "destination_id",
        "requested_at",
        "request_version",
        "request_schema",
        "message_class",
        "request_identity_sha256",
    )
    assert "text" not in inspect.signature(subject.E6TelegramReleasePreflightRequestV1).parameters
    assert tuple(inspect.signature(subject.build_e6_telegram_release_preflight_message_v1).parameters) == (
        "request",
    )
    assert tuple(inspect.signature(subject.E6TelegramReleasePreflightDeliveryAdapterV1.__call__).parameters) == (
        "self",
        "request",
    )


def test_adapter_construction_is_passive_and_token_is_absent_from_repr():
    calls = []

    def forbidden_factory(**_):
        calls.append(1)
        raise AssertionError

    adapter = subject.E6TelegramReleasePreflightDeliveryAdapterV1(
        bot_token=SYNTHETIC_TOKEN,
        http_client_factory=forbidden_factory,
    )
    assert calls == []
    assert SYNTHETIC_TOKEN not in repr(adapter)
    assert "bot_token" not in repr(adapter)
    assert all("token" not in field.name for field in fields(subject.E6TelegramReleasePreflightRequestV1))
    assert all("token" not in field.name for field in fields(subject.E6TelegramReleasePreflightReceiptV1))


def test_success_is_exactly_one_post_with_fixed_body_and_client_policy():
    adapter, captured = _adapter(lambda _: _response())
    receipt = adapter(_request())
    sent = captured["request"]
    assert sent.method == "POST"
    assert str(sent.url) == f"https://api.telegram.org/bot{SYNTHETIC_TOKEN}/sendMessage"
    body = json.loads(sent.content)
    assert set(body) == {"chat_id", "text", "disable_notification"}
    assert body == {
        "chat_id": DESTINATION_ID,
        "text": EXPECTED_MESSAGE,
        "disable_notification": True,
    }
    assert "parse_mode" not in body
    assert captured["attempt_count"] == 1
    assert captured["client_factory_count"] == 1
    assert captured["policy"] == {
        "timeout_seconds": 10,
        "follow_redirects": False,
        "trust_env": False,
        "http2": False,
        "maximum_attempts": 1,
    }
    assert receipt.classification == subject.PASS_TELEGRAM_AUTH_DESTINATION_AND_DELIVERY
    assert receipt.delivered is True
    assert receipt.http_status == 200
    assert receipt.external_delivery_id == "913"
    assert receipt.returned_chat_id_match is True
    assert receipt.attempt_count == 1
    assert receipt.automatic_retry_count == 0
    assert receipt.delivered_at == "2026-08-02T12:00:01Z"


def test_receipt_exposes_no_requested_or_returned_chat_identifier():
    adapter, _ = _adapter(lambda _: _response())
    receipt = adapter(_request())
    receipt_fields = {field.name for field in fields(receipt)}
    assert "destination_id" not in receipt_fields
    assert "requested_chat_id" not in receipt_fields
    assert "returned_chat_id" not in receipt_fields
    assert str(DESTINATION_ID) not in repr(receipt)


def test_returned_chat_id_mismatch_fails_closed_once():
    mapping = _mapping()
    mapping["result"]["chat"]["id"] = DESTINATION_ID - 1
    _assert_failure(
        lambda _: _response(mapping),
        subject.HOLD_TELEGRAM_RETURNED_CHAT_ID_MISMATCH,
    )


def test_invalid_json_fails_closed_once():
    _assert_failure(
        lambda _: _response(content=b"not-json"),
        subject.HOLD_TELEGRAM_RESPONSE_NOT_JSON,
    )


@pytest.mark.parametrize(
    "mapping",
    (
        [],
        {},
        {"ok": False, "description": RAW_SECRET},
        {"ok": True},
        {"ok": True, "result": None},
        {"ok": True, "result": {}},
        {"ok": True, "result": {"message_id": True, "chat": {"id": DESTINATION_ID}}},
        {"ok": True, "result": {"message_id": 0, "chat": {"id": DESTINATION_ID}}},
        {"ok": True, "result": {"message_id": 1}},
        {"ok": True, "result": {"message_id": 1, "chat": None}},
        {"ok": True, "result": {"message_id": 1, "chat": {}}},
        {"ok": True, "result": {"message_id": 1, "chat": {"id": True}}},
        {"ok": True, "result": {"message_id": 1, "chat": {"id": str(DESTINATION_ID)}}},
    ),
)
def test_missing_or_invalid_success_schema_fails_closed_once(mapping):
    error = _assert_failure(
        lambda _: _response(mapping),
        subject.HOLD_TELEGRAM_RESPONSE_SCHEMA_INVALID,
    )
    assert RAW_SECRET not in str(error)
    assert RAW_SECRET not in repr(error)


@pytest.mark.parametrize(
    ("status", "classification"),
    (
        (401, subject.HOLD_TELEGRAM_AUTHENTICATION_REJECTED),
        (403, subject.HOLD_TELEGRAM_BOT_BLOCKED_OR_FORBIDDEN),
        (400, subject.HOLD_TELEGRAM_DESTINATION_INVALID_OR_UNAVAILABLE),
        (404, subject.HOLD_TELEGRAM_DESTINATION_INVALID_OR_UNAVAILABLE),
        (429, subject.HOLD_TELEGRAM_RATE_LIMIT),
        (500, subject.HOLD_TELEGRAM_SERVER_ERROR),
        (503, subject.HOLD_TELEGRAM_SERVER_ERROR),
        (418, subject.HOLD_TELEGRAM_INVALID_REQUEST_CONTRACT),
    ),
)
def test_http_status_failures_are_fixed_sanitized_and_never_retried(status, classification):
    error = _assert_failure(
        lambda _: _response(
            {"ok": False, "description": RAW_SECRET},
            status=status,
        ),
        classification,
    )
    assert RAW_SECRET not in str(error)
    assert RAW_SECRET not in repr(error)
    assert SYNTHETIC_TOKEN not in repr(error)
    assert str(DESTINATION_ID) not in repr(error)


@pytest.mark.parametrize(
    ("exception_factory", "classification"),
    (
        (lambda request: socket.gaierror(RAW_SECRET), subject.HOLD_TELEGRAM_DNS_FAILURE),
        (lambda request: ssl.SSLError(RAW_SECRET), subject.HOLD_TELEGRAM_TLS_FAILURE),
        (
            lambda request: httpx.ConnectTimeout(RAW_SECRET, request=request),
            subject.HOLD_TELEGRAM_CONNECT_TIMEOUT,
        ),
        (
            lambda request: httpx.ReadTimeout(RAW_SECRET, request=request),
            subject.HOLD_TELEGRAM_READ_TIMEOUT,
        ),
        (
            lambda request: httpx.NetworkError(RAW_SECRET, request=request),
            subject.HOLD_TELEGRAM_NETWORK_FAILURE,
        ),
    ),
)
def test_network_failures_are_distinct_sanitized_one_attempt_zero_retry(
    exception_factory,
    classification,
):
    def fail(http_request):
        raise exception_factory(http_request)

    error = _assert_failure(fail, classification)
    assert RAW_SECRET not in str(error)
    assert RAW_SECRET not in repr(error)


def test_wrapped_dns_and_tls_causes_are_classified_without_message_inspection():
    for cause, classification in (
        (socket.gaierror(RAW_SECRET), subject.HOLD_TELEGRAM_DNS_FAILURE),
        (ssl.SSLError(RAW_SECRET), subject.HOLD_TELEGRAM_TLS_FAILURE),
    ):
        def fail(http_request, nested=cause):
            try:
                raise nested
            except Exception as inner:
                raise httpx.ConnectError(RAW_SECRET, request=http_request) from inner

        _assert_failure(fail, classification)


def test_request_and_receipt_identities_are_deterministic_and_bound():
    first_request = _request()
    second_request = _request()
    assert first_request.request_identity_sha256 == second_request.request_identity_sha256
    assert len(first_request.request_identity_sha256) == 64
    first_adapter, _ = _adapter(lambda _: _response())
    second_adapter, _ = _adapter(lambda _: _response())
    first_receipt = first_adapter(first_request)
    second_receipt = second_adapter(second_request)
    assert first_receipt.request_identity_sha256 == first_request.request_identity_sha256
    assert first_receipt.receipt_identity_sha256 == second_receipt.receipt_identity_sha256
    assert len(first_receipt.receipt_identity_sha256) == 64


def test_authority_constants_import_boundary_and_one_attempt_source_are_exact():
    assert subject.TELEGRAM_PREFLIGHT_PUBLICATION_AUTHORITY == "NO"
    assert subject.TELEGRAM_PREFLIGHT_OWNER_DECISION_AUTHORITY == "NO"
    assert subject.TELEGRAM_PREFLIGHT_ENTRY_ACTIVE_AUTHORITY == "NO"
    assert subject.TELEGRAM_PREFLIGHT_EXCHANGE_AUTHORITY == "NO"
    assert subject.TELEGRAM_PREFLIGHT_GENERAL_RAW_TEXT_AUTHORITY == "NO"
    assert subject.MAX_ATTEMPTS == 1
    assert subject.AUTOMATIC_RETRY_COUNT == 0
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    forbidden_fragments = (
        "owner_state",
        "ledger",
        "slot",
        "pair_lock",
        "exchange",
        "provider",
        "orchestrator",
        "service_composition",
        "service_cycle",
    )
    assert not any(
        fragment in module
        for module in imported_modules
        for fragment in forbidden_fragments
    )
    assert "HTTPTransport(retries=0)" in source
    assert source.count("client.post(") == 1
    assert "while " not in source
    assert "time.sleep" not in source
    assert "getMe" not in source
    assert "getChat" not in source
    assert "getUpdates" not in source
    assert "deleteMessage" not in source
    assert "editMessage" not in source


def test_contract_emits_no_warning():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        adapter, _ = _adapter(lambda _: _response())
        adapter(_request())
    assert captured == []
