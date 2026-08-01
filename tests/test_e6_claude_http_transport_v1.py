from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
from pathlib import Path

import httpx
import pytest

import engine.e5_claude_review_router_v1 as router
import engine.e5_provider_invocation_boundary_v1 as boundary
import engine.e6_claude_http_transport_v1 as subject
from engine.e5_technical_review_payload_v1 import (
    E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
)
from test_e5_claude_review_router_v1 import (
    UTC_DAY,
    _payload,
    _review_and_adjudication,
)


SYNTHETIC_KEY = "synthetic-claude-test-key"


def _unsafe_clone(value, **changes):
    clone = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return clone


def _canonical_hash(mapping):
    return hashlib.sha256(
        json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _chain(tmp_path, route="L1", *, name="claude-transport"):
    decision = "CAUTION" if route == "L1" else "HOLD"
    payload = _payload(tmp_path, name=f"{name}-{route}")
    review, adjudication = _review_and_adjudication(payload, decision)
    usage = router.create_empty_e5_claude_daily_usage_v1(utc_day=UTC_DAY)
    route_result = router.route_e5_claude_review_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        daily_usage=usage,
    )
    preflight = router.preflight_e5_claude_review_v1(
        route_result=route_result,
        measured_input_tokens=10,
        requested_output_tokens=20,
    )
    request = boundary.build_e5_claude_provider_request_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route_result,
        token_preflight=preflight,
    )
    return payload, review, adjudication, route_result, preflight, request


def _review_mapping(payload, route_result):
    preimage = {
        "review_version": boundary.E5_CLAUDE_ESCALATION_REVIEW_VERSION,
        "provider_binding_sha256": boundary.ACTIVE_PROVIDER_BINDING_SHA256,
        "payload_sha256": payload.payload_sha256,
        "route_sha256": route_result.route_sha256,
        "route": route_result.route,
        "model_id": route_result.model_id,
        "review_summary": "Bounded Claude transport review.",
        "reviewed_evidence_fields": list(E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS),
    }
    return {**preimage, "review_sha256": _canonical_hash(preimage)}


def _success_mapping(payload, route_result, **changes):
    review_text = json.dumps(
        _review_mapping(payload, route_result),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    content = [{"type": "text", "text": review_text}]
    if route_result.route == "L2":
        content.insert(0, {"type": "thinking", "thinking": "never retain this"})
    mapping = {
        "type": "message",
        "role": "assistant",
        "model": route_result.model_id,
        "content": content,
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 10,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "output_tokens": 2,
            "output_tokens_details": {"thinking_tokens": 1},
        },
    }
    mapping.update(changes)
    return mapping


def _json_response(mapping, *, status=200, headers=None):
    response_headers = {"Content-Type": "application/json"}
    if headers is not None:
        response_headers.update(headers)
    return httpx.Response(
        status,
        headers=response_headers,
        content=json.dumps(mapping, separators=(",", ":")).encode("utf-8"),
    )


def _install_mock_client(monkeypatch, handler, captured=None):
    if captured is None:
        captured = {}

    def build_client(configuration, timeout_seconds):
        captured["configuration"] = configuration
        captured["timeout_seconds"] = timeout_seconds
        captured["client_build_count"] = captured.get("client_build_count", 0) + 1
        return httpx.Client(
            transport=httpx.MockTransport(handler),
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            http2=False,
        )

    monkeypatch.setattr(subject, "_build_httpx_client", build_client)
    return captured


def _invoke(monkeypatch, request, handler, captured=None):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SYNTHETIC_KEY)
    captured = _install_mock_client(monkeypatch, handler, captured)
    observation = subject.get_e6_claude_http_transport_v1()(request)
    return observation, captured


def test_exact_frozen_slotted_direct_callable_contract_and_factory():
    transport = subject.get_e6_claude_http_transport_v1()
    assert type(transport) is subject.E6ClaudeHttpTransportV1
    assert is_dataclass(transport)
    assert transport.__dataclass_params__.frozen is True
    assert tuple(field.name for field in fields(transport)) == (
        "runtime_configuration",
    )
    assert not hasattr(transport, "__dict__")
    assert callable(transport)
    assert "__call__" in type(transport).__dict__
    assert "call" not in type(transport).__dict__
    with pytest.raises(FrozenInstanceError):
        transport.runtime_configuration = None  # type: ignore[misc]
    assert subject.__all__ == (
        "E6ClaudeHttpTransportV1",
        "get_e6_claude_http_transport_v1",
    )


@pytest.mark.parametrize(
    ("route", "model", "limit", "timeout", "thinking_present"),
    (
        ("L1", "claude-opus-5", 500, 10, True),
        ("L2", "claude-fable-5", 800, 20, False),
    ),
)
def test_exact_l1_l2_request_headers_body_and_success(
    tmp_path,
    monkeypatch,
    route,
    model,
    limit,
    timeout,
    thinking_present,
):
    payload, _, _, route_result, _, request = _chain(tmp_path, route)
    captured = {"send_count": 0}

    def handler(http_request):
        captured["send_count"] += 1
        captured["request"] = http_request
        return _json_response(_success_mapping(payload, route_result))

    observation, captured = _invoke(monkeypatch, request, handler, captured)
    sent = captured["request"]
    body = json.loads(sent.content)
    assert str(sent.url) == "https://api.anthropic.com/v1/messages"
    assert sent.method == "POST"
    assert sent.headers["x-api-key"] == SYNTHETIC_KEY
    assert sent.headers["anthropic-version"] == "2023-06-01"
    assert sent.headers["Content-Type"] == "application/json"
    assert sent.headers["Accept"] == "application/json"
    assert body["model"] == model
    assert body["messages"] == [
        {"role": "user", "content": request.canonical_input_json}
    ]
    assert body["max_tokens"] == limit
    assert body["stream"] is False
    assert body["output_config"] == {"effort": "high"}
    assert ("thinking" in body) is thinking_present
    if thinking_present:
        assert body["thinking"] == {"type": "disabled"}
    assert sent.content == json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert captured["timeout_seconds"] == timeout
    assert captured["client_build_count"] == 1
    assert captured["send_count"] == 1
    assert observation.transport_outcome == "SUCCESS"
    assert observation.attempt_number == 1
    assert observation.request_sha256 == request.request_sha256
    assert observation.measured_input_tokens == 10
    assert observation.measured_output_tokens == 2
    expected = (
        Decimal(10) * Decimal("5") + Decimal(2) * Decimal("25")
        if route == "L1"
        else Decimal(10) * Decimal("10") + Decimal(2) * Decimal("50")
    )
    assert observation.billed_cost_micro_usd == int(
        expected.to_integral_value(rounding=ROUND_CEILING)
    )
    assert "never retain this" not in repr(observation)


@pytest.mark.parametrize(
    ("credential", "detail"),
    ((None, "CREDENTIAL_MISSING"), ("", "CREDENTIAL_EMPTY"), ("   ", "CREDENTIAL_EMPTY")),
)
def test_missing_or_empty_credential_is_pre_network_zero_attempt(
    tmp_path,
    monkeypatch,
    credential,
    detail,
):
    *_, request = _chain(tmp_path, "L1", name=f"credential-{detail}")
    calls = []
    if credential is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANTHROPIC_API_KEY", credential)
    _install_mock_client(monkeypatch, lambda req: calls.append(req))
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_claude_http_transport_v1()(request)
    assert captured.value.failure_classification == "HOLD_PROVIDER_CONFIGURATION"
    assert captured.value.safe_detail_code == detail
    assert calls == []


def test_invalid_route_request_is_rejected_before_credential_read(tmp_path, monkeypatch):
    *_, request = _chain(tmp_path, "L1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    invalid = _unsafe_clone(request, route="L2")
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_claude_http_transport_v1()(invalid)
    assert captured.value.safe_detail_code == "REQUEST_CONTRACT_INVALID"


@pytest.mark.parametrize(
    "changes",
    (
        {"provider": "DEEPSEEK"},
        {"invocation_role": "CLAUDE_L2_ESCALATION_REVIEW"},
        {"provider_binding_sha256": "0" * 64},
        {"route": "L2"},
        {"model_id": "wrong-model"},
        {"output_hard_limit_tokens": 501},
        {"timeout_seconds": 11},
        {"provider_attempts": 2},
        {"retry_count": 1},
    ),
)
def test_every_fixed_l1_request_policy_value_is_validated_before_credential_read(
    tmp_path,
    monkeypatch,
    changes,
):
    *_, request = _chain(tmp_path, "L1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_claude_http_transport_v1()(
            _unsafe_clone(request, **changes)
        )
    assert captured.value.safe_detail_code == "REQUEST_CONTRACT_INVALID"


def test_serialization_and_client_configuration_failures_are_pre_network(
    tmp_path,
    monkeypatch,
):
    *_, request = _chain(tmp_path, "L1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", SYNTHETIC_KEY)
    real_dumps = json.dumps

    def fail_transport_body_serialization(mapping, *args, **kwargs):
        if type(mapping) is dict and {"messages", "max_tokens", "output_config"} <= set(mapping):
            raise TypeError
        return real_dumps(mapping, *args, **kwargs)

    monkeypatch.setattr(subject.json, "dumps", fail_transport_body_serialization)
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_claude_http_transport_v1()(request)
    assert captured.value.safe_detail_code == "REQUEST_SERIALIZATION_FAILED"

    monkeypatch.undo()
    monkeypatch.setenv("ANTHROPIC_API_KEY", SYNTHETIC_KEY)
    monkeypatch.setattr(
        subject,
        "_build_httpx_client",
        lambda *args: (_ for _ in ()).throw(TypeError()),
    )
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_claude_http_transport_v1()(request)
    assert captured.value.safe_detail_code == "HTTP_CLIENT_CONFIGURATION_INVALID"


@pytest.mark.parametrize(
    "exception_type",
    (
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ),
)
def test_every_timeout_exception_is_one_sanitized_attempt(
    tmp_path,
    monkeypatch,
    exception_type,
):
    *_, request = _chain(tmp_path, "L1", name=exception_type.__name__)

    def handler(http_request):
        raise exception_type("synthetic timeout", request=http_request)

    observation, _ = _invoke(monkeypatch, request, handler)
    assert observation.transport_outcome == "TIMEOUT"
    assert observation.attempt_number == 1
    assert observation.response_mapping is None


@pytest.mark.parametrize(
    "exception_type",
    (
        httpx.NetworkError,
        httpx.ConnectError,
        httpx.ReadError,
        httpx.WriteError,
        httpx.CloseError,
        httpx.ProtocolError,
        httpx.LocalProtocolError,
        httpx.RemoteProtocolError,
        httpx.ProxyError,
        httpx.UnsupportedProtocol,
    ),
)
def test_non_timeout_transport_errors_are_temporarily_unavailable_once(
    tmp_path,
    monkeypatch,
    exception_type,
):
    *_, request = _chain(tmp_path, "L2", name=exception_type.__name__)

    def handler(http_request):
        raise exception_type("synthetic transport failure", request=http_request)

    observation, _ = _invoke(monkeypatch, request, handler)
    assert observation.transport_outcome == "TEMPORARILY_UNAVAILABLE"
    assert observation.attempt_number == 1
    assert observation.measured_input_tokens == 0
    assert observation.measured_output_tokens == 0
    assert observation.billed_cost_micro_usd == 0


@pytest.mark.parametrize(
    ("status", "outcome"),
    (
        (400, "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"),
        (401, "AUTHENTICATION_OR_PERMISSION_FAILURE"),
        (402, "BUDGET_BLOCKED"),
        (403, "AUTHENTICATION_OR_PERMISSION_FAILURE"),
        (404, "UNSUPPORTED_MODEL"),
        (405, "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"),
        (408, "TIMEOUT"),
        (409, "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"),
        (410, "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"),
        (413, "TOKEN_LIMIT_EXCEEDED"),
        (415, "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"),
        (418, "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"),
        (422, "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"),
        (429, "TEMPORARILY_UNAVAILABLE"),
        (500, "TEMPORARILY_UNAVAILABLE"),
        (501, "TEMPORARILY_UNAVAILABLE"),
        (502, "TEMPORARILY_UNAVAILABLE"),
        (503, "TEMPORARILY_UNAVAILABLE"),
        (504, "TIMEOUT"),
        (529, "TEMPORARILY_UNAVAILABLE"),
    ),
)
def test_exact_http_status_matrix_including_402(tmp_path, monkeypatch, status, outcome):
    *_, request = _chain(tmp_path, "L1", name=f"status-{status}")
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: httpx.Response(status, content=b"{}"),
    )
    assert observation.transport_outcome == outcome
    assert observation.attempt_number == 1
    assert observation.response_mapping is None
    assert observation.response_digest_sha256 is None
    assert not hasattr(observation, "final_result_code")


@pytest.mark.parametrize("route", ("L1", "L2"))
def test_model_stop_and_output_limit_fail_closed(tmp_path, monkeypatch, route):
    payload, _, _, route_result, _, request = _chain(tmp_path, route)
    mappings = (
        (_success_mapping(payload, route_result, model="wrong-model"), "UNSUPPORTED_MODEL"),
        (
            _success_mapping(payload, route_result, stop_reason="max_tokens"),
            "TOKEN_LIMIT_EXCEEDED",
        ),
        (
            _success_mapping(payload, route_result, stop_reason="tool_use"),
            "MALFORMED_OR_SCHEMA_INVALID_RESPONSE",
        ),
    )
    for mapping, expected in mappings:
        observation, _ = _invoke(
            monkeypatch,
            request,
            lambda _, mapping=mapping: _json_response(mapping),
        )
        assert observation.transport_outcome == expected


@pytest.mark.parametrize(
    ("route", "content"),
    (
        ("L1", []),
        ("L1", [{"type": "thinking", "thinking": "x"}, {"type": "text", "text": "{}"}]),
        ("L1", [{"type": "text", "text": "{}"}, {"type": "text", "text": "{}"}]),
        ("L2", [{"type": "tool_use", "name": "x"}]),
        ("L2", [{"type": "unknown"}]),
    ),
)
def test_content_block_rules_reject_empty_thinking_tool_and_ambiguity(
    tmp_path,
    monkeypatch,
    route,
    content,
):
    payload, _, _, route_result, _, request = _chain(tmp_path, route)
    mapping = _success_mapping(payload, route_result, content=content)
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: _json_response(mapping),
    )
    assert observation.transport_outcome == "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"


@pytest.mark.parametrize(
    "usage_change",
    (
        {"input_tokens": True},
        {"input_tokens": -1},
        {"output_tokens": "2"},
        {"cache_creation_input_tokens": 1},
        {"cache_read_input_tokens": 1},
        {"output_tokens_details": {"thinking_tokens": 3}},
    ),
)
def test_usage_cache_and_thinking_rules_fail_closed(
    tmp_path,
    monkeypatch,
    usage_change,
):
    payload, _, _, route_result, _, request = _chain(tmp_path, "L2")
    mapping = _success_mapping(payload, route_result)
    mapping["usage"] = {**mapping["usage"], **usage_change}
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: _json_response(mapping),
    )
    assert observation.transport_outcome == "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"


def test_output_usage_above_route_bound_is_token_limit(tmp_path, monkeypatch):
    payload, _, _, route_result, _, request = _chain(tmp_path, "L1")
    mapping = _success_mapping(payload, route_result)
    mapping["usage"] = {
        **mapping["usage"],
        "output_tokens": 501,
        "output_tokens_details": {"thinking_tokens": 1},
    }
    observation, _ = _invoke(monkeypatch, request, lambda _: _json_response(mapping))
    assert observation.transport_outcome == "TOKEN_LIMIT_EXCEEDED"


@pytest.mark.parametrize(
    ("content_type", "content"),
    (
        ("text/plain", b"{}"),
        ("application/json; charset=latin-1", b"{}"),
        ("application/json", b"\xff"),
        ("application/json", b'{"a":1,"a":2}'),
        ("application/json", b'{"value":-Infinity}'),
        ("application/json", b"{} trailing"),
        ("application/json", b"[]"),
    ),
)
def test_strict_outer_json_media_and_utf8_boundary(
    tmp_path,
    monkeypatch,
    content_type,
    content,
):
    *_, request = _chain(tmp_path, "L1")
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: httpx.Response(
            200,
            headers={"Content-Type": content_type},
            content=content,
        ),
    )
    assert observation.transport_outcome == "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"


def test_content_length_and_one_mebibyte_boundaries(tmp_path, monkeypatch):
    *_, request = _chain(tmp_path, "L1")
    responses = (
        httpx.Response(200, headers={"Content-Length": "invalid"}, content=b"{}"),
        httpx.Response(
            200,
            headers=[("Content-Length", "1"), ("Content-Length", "2")],
            content=b"{}",
        ),
        httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            content=b"x" * 1048577,
        ),
    )
    for response in responses:
        observation, _ = _invoke(monkeypatch, request, lambda _, response=response: response)
        assert observation.transport_outcome == "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"


@pytest.mark.parametrize(
    "inner_text",
    ("", "[]", "{} trailing", '{"a":1,"a":2}', '{"value":NaN}'),
)
def test_strict_inner_review_json_and_lineage(tmp_path, monkeypatch, inner_text):
    payload, _, _, route_result, _, request = _chain(tmp_path, "L2")
    mapping = _success_mapping(
        payload,
        route_result,
        content=[{"type": "text", "text": inner_text}],
    )
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: _json_response(mapping),
    )
    assert observation.transport_outcome == "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"


def test_success_observation_remains_success_when_local_cost_exceeds_cap(
    tmp_path,
    monkeypatch,
):
    payload, _, _, route_result, _, request = _chain(tmp_path, "L1")
    monkeypatch.setattr(
        subject,
        "_cost_micro_usd",
        lambda route, input_tokens, output_tokens: request.maximum_review_cost_micro_usd + 1,
    )
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: _json_response(_success_mapping(payload, route_result)),
    )
    assert observation.transport_outcome == "SUCCESS"
    assert observation.billed_cost_micro_usd == request.maximum_review_cost_micro_usd + 1


def test_existing_invocation_boundary_owns_local_cost_budget_result(
    tmp_path,
    monkeypatch,
):
    payload, review, adjudication, route_result, preflight, request = _chain(
        tmp_path,
        "L1",
        name="local-cost-boundary",
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", SYNTHETIC_KEY)
    monkeypatch.setattr(
        subject,
        "_cost_micro_usd",
        lambda route, input_tokens, output_tokens: request.maximum_review_cost_micro_usd + 1,
    )
    calls = []

    def handler(http_request):
        calls.append(http_request)
        return _json_response(_success_mapping(payload, route_result))

    _install_mock_client(monkeypatch, handler)
    result = boundary.invoke_e5_claude_review_once_v1(
        payload=payload,
        deepseek_review=review,
        deepseek_adjudication=adjudication,
        route_result=route_result,
        token_preflight=preflight,
        transport=subject.get_e6_claude_http_transport_v1(),
    )
    assert len(calls) == 1
    assert result.underlying_failure_code == "HOLD_BUDGET_BLOCKED"
    assert result.final_result_code == "HOLD_BUDGET_BLOCKED"
    assert result.provider_attempt_count == 1
    assert result.retry_count == 0


def test_http_402_is_failure_observation_and_transport_invents_no_final_result(
    tmp_path,
    monkeypatch,
):
    *_, request = _chain(tmp_path, "L2")
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: httpx.Response(402, content=b'{"error":"billing"}'),
    )
    assert observation.transport_outcome == "BUDGET_BLOCKED"
    assert observation.attempt_number == 1
    assert observation.response_mapping is None
    assert observation.response_digest_sha256 is None
    assert not hasattr(observation, "final_result_code")


def test_redaction_zero_authority_and_source_policy(tmp_path, monkeypatch, capsys):
    *_, request = _chain(tmp_path, "L1")
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: httpx.Response(
            403,
            headers={"X-Secret": SYNTHETIC_KEY},
            content=(f'{{"error":"{SYNTHETIC_KEY}"}}').encode(),
        ),
    )
    assert SYNTHETIC_KEY not in repr(observation)
    assert request.canonical_input_json not in repr(observation)
    assert "never retain this" not in repr(observation)
    output = capsys.readouterr()
    assert SYNTHETIC_KEY not in output.out
    assert SYNTHETIC_KEY not in output.err
    assert not any(
        hasattr(observation, name)
        for name in (
            "publication_allowed",
            "telegram_send_allowed",
            "slot_mutation_allowed",
            "pair_lock_mutation_allowed",
            "fallback_allowed",
            "retry_allowed",
        )
    )
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    transport_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "E6ClaudeHttpTransportV1"
    )
    methods = {
        node.name
        for node in transport_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "__call__" in methods
    assert "call" not in methods
    assert "HTTPTransport(retries=0)" in source
    assert "time.sleep" not in source
    assert "backoff" not in source.casefold()
    assert "json=" not in source
