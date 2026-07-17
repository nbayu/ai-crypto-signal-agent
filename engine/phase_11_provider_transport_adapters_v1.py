"""Deterministic provider transport adapters for Phase 11 shadow review.

The adapters translate the generic runtime's sanitized request mapping to one
explicitly supplied client call.  They do not discover clients, credentials,
configuration, or authority and perform no retry, persistence, or production
action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Protocol

from engine.ai_review_payload_projector_v1 import (
    ClaudeReviewPayloadV1,
    DeepSeekReviewPayloadV1,
)
from engine.phase_11_provider_credential_boundary_v1 import (
    EphemeralProviderCredentialV1,
    ProviderCredentialResolutionV1,
)


UTC = timezone.utc
_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_UTC_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)

_ENDPOINT_MODELS = {
    ("DEEPSEEK", "DEEPSEEK_PRIMARY"): "synthetic-deepseek-primary",
    ("ANTHROPIC", "CLAUDE_SONNET_L1"): "synthetic-anthropic-sonnet",
    ("ANTHROPIC", "CLAUDE_OPUS_L2"): "synthetic-anthropic-opus",
}
_ROUTES = {
    ("DEEPSEEK", "DEEPSEEK_PRIMARY"): frozenset(("L0", "L1", "L2")),
    ("ANTHROPIC", "CLAUDE_SONNET_L1"): frozenset(("L1",)),
    ("ANTHROPIC", "CLAUDE_OPUS_L2"): frozenset(("L2", "L1_TO_L2")),
}


class AdapterStatusV1(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AdapterFailureV1(StrEnum):
    NONE = "NONE"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    UNCERTAIN_TRANSPORT_OUTCOME = "UNCERTAIN_TRANSPORT_OUTCOME"


class ProviderTransportAdapterValidationError(ValueError):
    """Raised when safe adapter metadata is invalid."""


def _decimal_text(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return _timestamp(value, "timestamp")
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON for safe structured evidence."""

    try:
        return json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ProviderTransportAdapterValidationError(
            "non-canonical adapter metadata"
        ) from error


def lowercase_sha256(value: Any) -> str:
    """Return lowercase SHA-256 over canonical structured JSON."""

    return sha256(canonical_json_bytes(value)).hexdigest()


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ProviderTransportAdapterValidationError(f"invalid {label}")
    return value


def _hash_value(value: Any, label: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ProviderTransportAdapterValidationError(f"invalid {label}")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ProviderTransportAdapterValidationError(f"invalid {label}")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ProviderTransportAdapterValidationError(f"invalid {label}")
    return value


def _money(value: Any, label: str) -> Decimal:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise ProviderTransportAdapterValidationError(f"invalid {label}")
    return Decimal("0") if value == 0 else value.normalize()


def _timestamp(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ProviderTransportAdapterValidationError(f"invalid {label}")
        parsed = value.astimezone(UTC)
    elif type(value) is str and _UTC_TEXT.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ProviderTransportAdapterValidationError(
                f"invalid {label}"
            ) from error
    else:
        raise ProviderTransportAdapterValidationError(f"invalid {label}")
    normalized = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    return normalized.replace("+00:00", "Z").replace(".000000Z", "Z")


def _parsed(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reasons(value: Any) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or not value:
        raise ProviderTransportAdapterValidationError("invalid reason_codes")
    reasons = tuple(sorted(value))
    if (
        len(set(reasons)) != len(reasons)
        or any(
            type(item) is not str or _REASON.fullmatch(item) is None
            for item in reasons
        )
    ):
        raise ProviderTransportAdapterValidationError("invalid reason_codes")
    return reasons


_ENDPOINT_FIELDS = frozenset(
    (
        "schema_version",
        "binding_identity",
        "provider",
        "contract_model",
        "provider_model_identifier",
        "adapter_version",
        "request_schema_version",
        "response_schema_version",
        "valid_from",
        "valid_until",
    )
)


@dataclass(frozen=True, init=False, slots=True)
class ProviderEndpointBindingV1:
    schema_version: str
    binding_identity: str
    provider: str
    contract_model: str
    provider_model_identifier: str
    adapter_version: str
    request_schema_version: str
    response_schema_version: str
    valid_from: str
    valid_until: str

    def __init__(self, **values: Any) -> None:
        if frozenset(values) != _ENDPOINT_FIELDS:
            raise ProviderTransportAdapterValidationError(
                "invalid endpoint binding fields"
            )
        if (
            values["schema_version"]
            != "phase11-provider-endpoint-binding-v1"
        ):
            raise ProviderTransportAdapterValidationError(
                "unsupported endpoint binding schema"
            )
        provider = values["provider"]
        model = values["contract_model"]
        expected_identifier = _ENDPOINT_MODELS.get((provider, model))
        identifier = _identifier(
            values["provider_model_identifier"],
            "provider_model_identifier",
        )
        if expected_identifier is None or identifier != expected_identifier:
            raise ProviderTransportAdapterValidationError(
                "endpoint provider model mismatch"
            )
        if (
            values["adapter_version"]
            != "phase11-provider-transport-adapter-v1"
            or values["request_schema_version"]
            != "phase10-review-schema-v1"
            or values["response_schema_version"]
            != "phase11-shadow-provider-transport-response-v1"
        ):
            raise ProviderTransportAdapterValidationError(
                "unsupported endpoint contract version"
            )
        valid_from = _timestamp(values["valid_from"], "valid_from")
        valid_until = _timestamp(values["valid_until"], "valid_until")
        if _parsed(valid_until) < _parsed(valid_from):
            raise ProviderTransportAdapterValidationError(
                "invalid endpoint validity interval"
            )
        material = {
            "schema_version": values["schema_version"],
            "provider": provider,
            "contract_model": model,
            "provider_model_identifier": identifier,
            "adapter_version": values["adapter_version"],
            "request_schema_version": values["request_schema_version"],
            "response_schema_version": values["response_schema_version"],
            "valid_from": valid_from,
            "valid_until": valid_until,
        }
        identity = lowercase_sha256(material)
        supplied = _hash_value(
            values["binding_identity"], "binding_identity", optional=True
        )
        if supplied is not None and supplied != identity:
            raise ProviderTransportAdapterValidationError(
                "endpoint binding identity mismatch"
            )
        normalized = dict(values)
        normalized.update(
            binding_identity=identity,
            provider=provider,
            contract_model=model,
            provider_model_identifier=identifier,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        for name, item in normalized.items():
            object.__setattr__(self, name, item)

    @property
    def identity(self) -> str:
        return self.binding_identity


class DeepSeekClientProtocolV1(Protocol):
    def complete(self, **values: Any) -> Any: ...


class AnthropicClientProtocolV1(Protocol):
    def complete(self, **values: Any) -> Any: ...


_RUNTIME_REQUEST_FIELDS = frozenset(
    (
        "provider",
        "model",
        "route",
        "invocation_id",
        "attempt_number",
        "attempt_reservation_id",
        "call_id",
        "request_hash",
        "review_request",
    )
)
_CLIENT_RESPONSE_FIELDS = frozenset(
    (
        "schema_version",
        "status",
        "provider",
        "provider_model_identifier",
        "invocation_id",
        "attempt_reservation_id",
        "call_id",
        "request_hash",
        "provider_review_identity",
        "structured_verdict",
        "reason_codes",
        "input_tokens",
        "output_tokens",
        "estimated_cost",
        "actual_cost",
        "started_at",
        "completed_at",
        "provider_timestamp",
        "latency_ms",
    )
)
_TERMINAL_OUTCOMES = frozenset(
    (
        "PROVIDER_UNAVAILABLE",
        "MALFORMED_RESPONSE",
        "SCHEMA_MISMATCH",
        "UNCERTAIN_TRANSPORT_OUTCOME",
    )
)
_SECRET_RESPONSE_KEYS = frozenset(
    (
        "api_key",
        "secret",
        "secret_value",
        "raw_secret",
        "token_value",
        "bearer_token",
        "authorization_header",
        "password",
        "private_key",
        "client_secret",
    )
)


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in _SECRET_RESPONSE_KEYS or _contains_secret_key(item)
            for key, item in value.items()
        )
    if isinstance(value, (tuple, list)):
        return any(_contains_secret_key(item) for item in value)
    return False


class _BaseShadowTransportAdapterV1:
    __slots__ = (
        "endpoint_binding",
        "review_request",
        "credential_resolution",
        "attempted_at",
        "_client",
        "_identity",
        "_sealed",
    )

    endpoint_binding: ProviderEndpointBindingV1
    review_request: DeepSeekReviewPayloadV1 | ClaudeReviewPayloadV1
    credential_resolution: ProviderCredentialResolutionV1
    attempted_at: str
    _client: Any
    _identity: str
    _sealed: bool

    expected_provider: str
    expected_payload_type: type
    allowed_models: frozenset[str]

    def __init__(self, **values: Any) -> None:
        expected_fields = frozenset(
            (
                "endpoint_binding",
                "review_request",
                "credential_resolution",
                "attempted_at",
                "client",
            )
        )
        if frozenset(values) != expected_fields:
            raise ProviderTransportAdapterValidationError(
                "invalid adapter fields"
            )
        endpoint = values["endpoint_binding"]
        payload = values["review_request"]
        resolution = values["credential_resolution"]
        if type(endpoint) is not ProviderEndpointBindingV1:
            raise ProviderTransportAdapterValidationError(
                "invalid endpoint binding"
            )
        if (
            endpoint.provider != self.expected_provider
            or endpoint.contract_model not in self.allowed_models
        ):
            raise ProviderTransportAdapterValidationError(
                "adapter endpoint mismatch"
            )
        if type(payload) is not self.expected_payload_type:
            raise ProviderTransportAdapterValidationError(
                "adapter payload mismatch"
            )
        if type(resolution) is not ProviderCredentialResolutionV1:
            raise ProviderTransportAdapterValidationError(
                "invalid credential resolution"
            )
        if (
            resolution.status != "RESOLVED"
            or resolution.failure_class != "NONE"
            or type(resolution.ephemeral_credential)
            is not EphemeralProviderCredentialV1
            or resolution.provider != self.expected_provider
            or resolution.credential_reference_identity
            != resolution.credential_reference.identity
            or resolution.credential_version
            != resolution.credential_reference.credential_version
            or resolution.ephemeral_credential.provider
            != self.expected_provider
            or resolution.ephemeral_credential.credential_reference_identity
            != resolution.credential_reference_identity
            or resolution.ephemeral_credential.credential_version
            != resolution.credential_version
            or resolution.rotation_required
        ):
            raise ProviderTransportAdapterValidationError(
                "credential resolution not usable"
            )
        attempted_at = _timestamp(values["attempted_at"], "attempted_at")
        moment = _parsed(attempted_at)
        if not (
            _parsed(endpoint.valid_from)
            <= moment
            <= _parsed(endpoint.valid_until)
        ):
            raise ProviderTransportAdapterValidationError(
                "endpoint binding not valid at attempt"
            )
        reference = resolution.credential_reference
        if not (
            _parsed(reference.valid_from)
            <= moment
            <= _parsed(resolution.valid_until)
            and _parsed(resolution.resolved_at) <= moment
        ):
            raise ProviderTransportAdapterValidationError(
                "credential not valid at attempt"
            )
        client_method = getattr(values["client"], "complete", None)
        if not callable(client_method):
            raise ProviderTransportAdapterValidationError(
                "invalid provider client"
            )
        identity = lowercase_sha256(
            {
                "schema_version": "phase11-provider-transport-adapter-v1",
                "adapter_type": type(self).__name__,
                "endpoint_binding_identity": endpoint.identity,
                "review_request_identity": payload.payload_sha256,
                "credential_resolution_identity": resolution.identity,
                "attempted_at": attempted_at,
                "production_effect": "NONE",
            }
        )
        object.__setattr__(self, "endpoint_binding", endpoint)
        object.__setattr__(self, "review_request", payload)
        object.__setattr__(self, "credential_resolution", resolution)
        object.__setattr__(self, "attempted_at", attempted_at)
        object.__setattr__(self, "_client", values["client"])
        object.__setattr__(self, "_identity", identity)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("provider transport adapter is immutable")
        object.__setattr__(self, name, value)

    @property
    def identity(self) -> str:
        return self._identity

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"endpoint_binding={self.endpoint_binding!r}, "
            f"review_request_identity={self.review_request.payload_sha256!r}, "
            f"credential_resolution_identity="
            f"{self.credential_resolution.identity!r}, "
            f"attempted_at={self.attempted_at!r}, "
            f"identity={self.identity!r}, material=<redacted>)"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def _valid_request(self, request: Any, timeout_ms: Any) -> bool:
        if (
            not isinstance(request, Mapping)
            or frozenset(request) != _RUNTIME_REQUEST_FIELDS
            or type(timeout_ms) is not int
            or timeout_ms <= 0
        ):
            return False
        endpoint = self.endpoint_binding
        if (
            request["provider"] != endpoint.provider
            or request["model"] != endpoint.contract_model
            or request["route"]
            not in _ROUTES[(endpoint.provider, endpoint.contract_model)]
            or type(request["attempt_number"]) is not int
            or request["attempt_number"] <= 0
        ):
            return False
        try:
            invocation_id = _hash_value(
                request["invocation_id"], "invocation_id"
            )
            attempt_id = _hash_value(
                request["attempt_reservation_id"],
                "attempt_reservation_id",
            )
            call_id = _identifier(request["call_id"], "call_id")
            request_hash = _hash_value(
                request["request_hash"], "request_hash"
            )
        except ProviderTransportAdapterValidationError:
            return False
        if (
            invocation_id != request["invocation_id"]
            or attempt_id != request["attempt_reservation_id"]
            or call_id != request["call_id"]
            or request_hash != self.review_request.payload_sha256
            or not isinstance(request["review_request"], Mapping)
            or dict(request["review_request"])
            != self.review_request.to_mapping()
        ):
            return False
        return True

    def __call__(self, request: Mapping[str, Any], timeout_ms: int) -> Any:
        if not self._valid_request(request, timeout_ms):
            return {"outcome": "MALFORMED_RESPONSE"}
        ephemeral_material: bytes | str | None = None
        try:
            ephemeral_material = (
                self.credential_resolution.ephemeral_credential
                .material_for_adapter()
            )
            client_response = self._client.complete(
                provider_model_identifier=(
                    self.endpoint_binding.provider_model_identifier
                ),
                payload=self.review_request.to_mapping(),
                timeout_ms=timeout_ms,
                invocation_id=request["invocation_id"],
                attempt_reservation_id=request["attempt_reservation_id"],
                call_id=request["call_id"],
                request_hash=request["request_hash"],
                credential_material=ephemeral_material,
            )
        except TimeoutError:
            return {"outcome": "TIMEOUT"}
        except ConnectionError:
            return {"outcome": "TRANSPORT_FAILURE"}
        except Exception:
            return {"outcome": "TRANSPORT_FAILURE"}
        finally:
            ephemeral_material = None
        return self._translate_response(client_response, request)

    def _translate_response(
        self, response: Any, request: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        try:
            if (
                not isinstance(response, Mapping)
                or frozenset(response) != _CLIENT_RESPONSE_FIELDS
                or _contains_secret_key(response)
                or response["schema_version"]
                != "phase11-provider-client-response-v1"
            ):
                raise ProviderTransportAdapterValidationError(
                    "invalid client response"
                )
            status = response["status"]
            if status in _TERMINAL_OUTCOMES:
                return {"outcome": status}
            if status != "SUCCESS":
                raise ProviderTransportAdapterValidationError(
                    "invalid client response status"
                )
            endpoint = self.endpoint_binding
            if (
                response["provider"] != endpoint.provider
                or response["provider_model_identifier"]
                != endpoint.provider_model_identifier
                or response["invocation_id"] != request["invocation_id"]
                or response["attempt_reservation_id"]
                != request["attempt_reservation_id"]
                or response["call_id"] != request["call_id"]
                or response["request_hash"] != request["request_hash"]
            ):
                raise ProviderTransportAdapterValidationError(
                    "client response identity mismatch"
                )
            review_identity = _hash_value(
                response["provider_review_identity"],
                "provider_review_identity",
            )
            if (
                not isinstance(response["structured_verdict"], Mapping)
                or dict(response["structured_verdict"])
                != {"verdict": "ADVISORY_REVIEW"}
            ):
                raise ProviderTransportAdapterValidationError(
                    "invalid structured verdict"
                )
            verdict = {"verdict": "ADVISORY_REVIEW"}
            reasons = _reasons(response["reason_codes"])
            input_tokens = _nonnegative(
                response["input_tokens"], "input_tokens"
            )
            output_tokens = _nonnegative(
                response["output_tokens"], "output_tokens"
            )
            estimated = _money(
                response["estimated_cost"], "estimated_cost"
            )
            actual = _money(response["actual_cost"], "actual_cost")
            started_at = _timestamp(response["started_at"], "started_at")
            completed_at = _timestamp(
                response["completed_at"], "completed_at"
            )
            provider_timestamp = _timestamp(
                response["provider_timestamp"], "provider_timestamp"
            )
            if _parsed(completed_at) < _parsed(started_at):
                raise ProviderTransportAdapterValidationError(
                    "invalid client response timing"
                )
            latency_ms = _nonnegative(response["latency_ms"], "latency_ms")
            translated = {
                "outcome": "SUCCESS",
                "provider": endpoint.provider,
                "model": endpoint.contract_model,
                "invocation_id": request["invocation_id"],
                "attempt_reservation_id": request["attempt_reservation_id"],
                "attempt_count": request["attempt_number"],
                "request_hash": request["request_hash"],
                "prompt_version": "phase11-prompt-v1",
                "provider_review_schema_version": (
                    endpoint.request_schema_version
                ),
                "provider_review_identity": review_identity,
                "structured_verdict": verdict,
                "reason_codes": reasons,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": estimated,
                "actual_cost": actual,
                "started_at": started_at,
                "completed_at": completed_at,
                "latency_ms": latency_ms,
                "provider_timestamp": provider_timestamp,
            }
            translated["response_hash"] = lowercase_sha256(translated)
            return translated
        except ProviderTransportAdapterValidationError:
            return {"outcome": "MALFORMED_RESPONSE"}


class DeepSeekShadowTransportAdapterV1(
    _BaseShadowTransportAdapterV1
):
    expected_provider = "DEEPSEEK"
    expected_payload_type = DeepSeekReviewPayloadV1
    allowed_models = frozenset(("DEEPSEEK_PRIMARY",))


class AnthropicShadowTransportAdapterV1(
    _BaseShadowTransportAdapterV1
):
    expected_provider = "ANTHROPIC"
    expected_payload_type = ClaudeReviewPayloadV1
    allowed_models = frozenset(
        ("CLAUDE_SONNET_L1", "CLAUDE_OPUS_L2")
    )


__all__ = (
    "AdapterFailureV1",
    "AdapterStatusV1",
    "AnthropicClientProtocolV1",
    "AnthropicShadowTransportAdapterV1",
    "DeepSeekClientProtocolV1",
    "DeepSeekShadowTransportAdapterV1",
    "ProviderEndpointBindingV1",
    "ProviderTransportAdapterValidationError",
    "canonical_json_bytes",
    "lowercase_sha256",
)
