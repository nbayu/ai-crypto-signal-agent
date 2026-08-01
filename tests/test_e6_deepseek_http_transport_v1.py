from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
from types import MappingProxyType

import httpx
import pytest

import engine.e5_provider_invocation_boundary_v1 as boundary
import engine.e5_technical_review_payload_v1 as payload_contract
import engine.e6_deepseek_http_transport_v1 as subject
from test_e5_claude_review_router_v1 import _payload, _review_and_adjudication


SYNTHETIC_KEY = "synthetic-deepseek-test-key"


def _unsafe_clone(value, **changes):
    clone = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return clone


def _request_and_review(tmp_path, *, name="deepseek-transport"):
    payload = _payload(tmp_path, name=name)
    review, _ = _review_and_adjudication(payload, "CLEAR")
    preflight = payload_contract.preflight_e5_technical_review_payload_v1(
        payload=payload,
        measured_input_tokens=10,
        requested_output_tokens=20,
    )
    request = boundary.build_e5_deepseek_provider_request_v1(
        payload=payload,
        token_preflight=preflight,
    )
    return request, review


def _success_mapping(review, **changes):
    mapping = {
        "model": "deepseek-v4-pro",
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        review.to_mapping(),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 2,
            "prompt_cache_hit_tokens": 4,
            "prompt_cache_miss_tokens": 6,
            "completion_tokens_details": {"reasoning_tokens": 1},
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
    monkeypatch.setenv("DEEPSEEK_API_KEY", SYNTHETIC_KEY)
    captured = _install_mock_client(monkeypatch, handler, captured)
    observation = subject.get_e6_deepseek_http_transport_v1()(request)
    return observation, captured


def test_exact_frozen_slotted_direct_callable_contract_and_factory():
    transport = subject.get_e6_deepseek_http_transport_v1()
    assert type(transport) is subject.E6DeepSeekHttpTransportV1
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
        "E6DeepSeekHttpTransportV1",
        "get_e6_deepseek_http_transport_v1",
    )


def test_exact_request_headers_canonical_body_client_policy_and_success(
    tmp_path,
    monkeypatch,
):
    request, review = _request_and_review(tmp_path)
    captured = {"send_count": 0}

    def handler(http_request):
        captured["send_count"] += 1
        captured["request"] = http_request
        return _json_response(_success_mapping(review))

    observation, captured = _invoke(monkeypatch, request, handler, captured)
    sent = captured["request"]
    expected_mapping = {
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": request.canonical_input_json}],
        "max_tokens": 500,
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    expected_bytes = json.dumps(
        expected_mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert str(sent.url) == "https://api.deepseek.com/chat/completions"
    assert sent.method == "POST"
    assert sent.headers["Authorization"] == f"Bearer {SYNTHETIC_KEY}"
    assert sent.headers["Content-Type"] == "application/json"
    assert sent.headers["Accept"] == "application/json"
    assert sent.content == expected_bytes
    assert b"\n" not in sent.content
    assert set(json.loads(sent.content)) == {
        "model",
        "messages",
        "max_tokens",
        "stream",
        "thinking",
    }
    assert "reasoning_effort" not in json.loads(sent.content)
    assert captured["timeout_seconds"] == 60
    assert captured["client_build_count"] == 1
    assert captured["send_count"] == 1
    assert observation.transport_outcome == "SUCCESS"
    assert observation.attempt_number == 1
    assert observation.request_sha256 == request.request_sha256
    expected_response_mapping = review.to_mapping()
    expected_response_mapping["reason_codes"] = tuple(
        expected_response_mapping["reason_codes"]
    )
    expected_response_mapping["reviewed_evidence_fields"] = tuple(
        expected_response_mapping["reviewed_evidence_fields"]
    )
    assert type(observation.response_mapping) is MappingProxyType
    assert dict(observation.response_mapping) == expected_response_mapping
    assert observation.measured_input_tokens == 10
    assert observation.measured_output_tokens == 2
    expected_cost = int(
        (
            Decimal(4) * Decimal("0.003625")
            + Decimal(6) * Decimal("0.435")
            + Decimal(2) * Decimal("0.87")
        ).to_integral_value(rounding=ROUND_CEILING)
    )
    assert observation.billed_cost_micro_usd == expected_cost


@pytest.mark.parametrize(
    ("credential", "detail"),
    ((None, "CREDENTIAL_MISSING"), ("", "CREDENTIAL_EMPTY"), ("   ", "CREDENTIAL_EMPTY")),
)
def test_missing_or_empty_credential_is_typed_pre_network_zero_attempt(
    tmp_path,
    monkeypatch,
    credential,
    detail,
):
    request, _ = _request_and_review(tmp_path, name=f"credential-{detail}")
    calls = []
    if credential is None:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    else:
        monkeypatch.setenv("DEEPSEEK_API_KEY", credential)
    _install_mock_client(monkeypatch, lambda req: calls.append(req))
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_deepseek_http_transport_v1()(request)
    assert captured.value.failure_classification == "HOLD_PROVIDER_CONFIGURATION"
    assert captured.value.safe_detail_code == detail
    assert calls == []


def test_invalid_request_serialization_and_client_failures_are_pre_network(
    tmp_path,
    monkeypatch,
):
    request, _ = _request_and_review(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    invalid = _unsafe_clone(request, model_id="wrong-model")
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_deepseek_http_transport_v1()(invalid)
    assert captured.value.safe_detail_code == "REQUEST_CONTRACT_INVALID"

    monkeypatch.setenv("DEEPSEEK_API_KEY", SYNTHETIC_KEY)
    real_dumps = json.dumps

    def fail_transport_body_serialization(mapping, *args, **kwargs):
        if type(mapping) is dict and {"messages", "max_tokens", "thinking"} <= set(mapping):
            raise TypeError
        return real_dumps(mapping, *args, **kwargs)

    monkeypatch.setattr(subject.json, "dumps", fail_transport_body_serialization)
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_deepseek_http_transport_v1()(request)
    assert captured.value.safe_detail_code == "REQUEST_SERIALIZATION_FAILED"
    monkeypatch.undo()
    monkeypatch.setenv("DEEPSEEK_API_KEY", SYNTHETIC_KEY)
    monkeypatch.setattr(subject, "_build_httpx_client", lambda *args: (_ for _ in ()).throw(TypeError()))
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_deepseek_http_transport_v1()(request)
    assert captured.value.safe_detail_code == "HTTP_CLIENT_CONFIGURATION_INVALID"


@pytest.mark.parametrize(
    "changes",
    (
        {"provider": "ANTHROPIC"},
        {"invocation_role": "CLAUDE_L1_ESCALATION_REVIEW"},
        {"provider_binding_sha256": "0" * 64},
        {"route": "L1"},
        {"model_id": "wrong-model"},
        {"output_hard_limit_tokens": 501},
        {"timeout_seconds": 61},
        {"provider_attempts": 2},
        {"retry_count": 1},
    ),
)
def test_every_fixed_request_policy_value_is_validated_before_credential_read(
    tmp_path,
    monkeypatch,
    changes,
):
    request, _ = _request_and_review(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(boundary.E5ProviderPreNetworkFailureV1) as captured:
        subject.get_e6_deepseek_http_transport_v1()(
            _unsafe_clone(request, **changes)
        )
    assert captured.value.safe_detail_code == "REQUEST_CONTRACT_INVALID"


@pytest.mark.parametrize(
    "choices",
    (
        None,
        [],
        [{"message": {"content": "{}"}, "finish_reason": "stop"}] * 2,
        [{}],
        [{"message": {}, "finish_reason": "stop"}],
        [{"message": {"content": ""}, "finish_reason": "stop"}],
    ),
)
def test_ambiguous_or_empty_choices_and_content_fail_closed(
    tmp_path,
    monkeypatch,
    choices,
):
    request, review = _request_and_review(tmp_path)
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: _json_response(_success_mapping(review, choices=choices)),
    )
    assert observation.transport_outcome == "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"


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
    request, _ = _request_and_review(tmp_path, name=exception_type.__name__)

    def handler(http_request):
        raise exception_type("synthetic timeout", request=http_request)

    observation, _ = _invoke(monkeypatch, request, handler)
    assert observation.transport_outcome == "TIMEOUT"
    assert observation.attempt_number == 1
    assert observation.response_mapping is None
    assert observation.response_digest_sha256 is None


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
def test_every_non_timeout_transport_error_is_temporarily_unavailable_once(
    tmp_path,
    monkeypatch,
    exception_type,
):
    request, _ = _request_and_review(tmp_path, name=exception_type.__name__)

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
def test_exact_frozen_http_status_matrix(tmp_path, monkeypatch, status, outcome):
    request, _ = _request_and_review(tmp_path, name=f"status-{status}")
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: httpx.Response(status, content=b"{}"),
    )
    assert observation.transport_outcome == outcome
    assert observation.attempt_number == 1
    assert observation.response_mapping is None
    assert observation.response_digest_sha256 is None
    assert observation.measured_input_tokens == 0
    assert observation.measured_output_tokens == 0
    assert observation.billed_cost_micro_usd == 0


def test_model_finish_and_output_limit_fail_closed(tmp_path, monkeypatch):
    request, review = _request_and_review(tmp_path)
    cases = (
        (_success_mapping(review, model="wrong-model"), "UNSUPPORTED_MODEL"),
        (
            _success_mapping(
                review,
                choices=[
                    {
                        "message": {"content": "{}"},
                        "finish_reason": "length",
                    }
                ],
            ),
            "TOKEN_LIMIT_EXCEEDED",
        ),
        (
            _success_mapping(
                review,
                choices=[
                    {
                        "message": {"content": "{}"},
                        "finish_reason": "content_filter",
                    }
                ],
            ),
            "MALFORMED_OR_SCHEMA_INVALID_RESPONSE",
        ),
    )
    for mapping, expected in cases:
        observation, _ = _invoke(
            monkeypatch,
            request,
            lambda _, mapping=mapping: _json_response(mapping),
        )
        assert observation.transport_outcome == expected


@pytest.mark.parametrize(
    "usage_change",
    (
        {"prompt_tokens": True},
        {"prompt_tokens": -1},
        {"completion_tokens": "2"},
        {"prompt_cache_hit_tokens": 11},
        {"completion_tokens_details": {"reasoning_tokens": 3}},
    ),
)
def test_invalid_usage_and_reasoning_accounting_fail_closed(
    tmp_path,
    monkeypatch,
    usage_change,
):
    request, review = _request_and_review(tmp_path)
    mapping = _success_mapping(review)
    mapping["usage"] = {**mapping["usage"], **usage_change}
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: _json_response(mapping),
    )
    assert observation.transport_outcome == "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"


def test_output_usage_above_bound_is_token_limit(tmp_path, monkeypatch):
    request, review = _request_and_review(tmp_path)
    mapping = _success_mapping(review)
    mapping["usage"] = {
        **mapping["usage"],
        "completion_tokens": 501,
        "completion_tokens_details": {"reasoning_tokens": 1},
    }
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: _json_response(mapping),
    )
    assert observation.transport_outcome == "TOKEN_LIMIT_EXCEEDED"


@pytest.mark.parametrize(
    ("content_type", "content"),
    (
        ("text/plain", b"{}"),
        ("application/json; charset=latin-1", b"{}"),
        ("application/json", b"\xff"),
        ("application/json", b'{"a":1,"a":2}'),
        ("application/json", b'{"value":NaN}'),
        ("application/json", b"{} trailing"),
        ("application/json", b"[]"),
    ),
)
def test_strict_outer_response_boundary(tmp_path, monkeypatch, content_type, content):
    request, _ = _request_and_review(tmp_path)
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
    request, _ = _request_and_review(tmp_path)
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
        assert observation.response_mapping is None


@pytest.mark.parametrize(
    "inner_text",
    ("", "[]", "{} trailing", '{"a":1,"a":2}', '{"value":Infinity}'),
)
def test_strict_inner_review_json_and_unambiguous_content(
    tmp_path,
    monkeypatch,
    inner_text,
):
    request, review = _request_and_review(tmp_path)
    mapping = _success_mapping(
        review,
        choices=[
            {
                "message": {"content": inner_text},
                "finish_reason": "stop",
            }
        ],
    )
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: _json_response(mapping),
    )
    assert observation.transport_outcome == "MALFORMED_OR_SCHEMA_INVALID_RESPONSE"


def test_failure_redaction_and_no_authority(tmp_path, monkeypatch, capsys):
    request, _ = _request_and_review(tmp_path)
    observation, _ = _invoke(
        monkeypatch,
        request,
        lambda _: httpx.Response(
            402,
            headers={"X-Secret": SYNTHETIC_KEY},
            content=(f'{{"error":"{SYNTHETIC_KEY}"}}').encode(),
        ),
    )
    assert observation.transport_outcome == "BUDGET_BLOCKED"
    assert observation.response_mapping is None
    assert observation.response_digest_sha256 is None
    assert SYNTHETIC_KEY not in repr(observation)
    assert request.canonical_input_json not in repr(observation)
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


def test_source_freezes_zero_retry_no_backoff_and_no_public_call_method():
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    transport_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "E6DeepSeekHttpTransportV1"
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
