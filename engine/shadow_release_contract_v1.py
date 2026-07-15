"""Pure canonical contract primitives for Phase 08 Shadow Release."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Mapping


SHADOW_RELEASE_SCHEMA_VERSION = 1
SHADOW_RELEASE_SCHEMA_NAME = "shadow-release-run"
SHADOW_RELEASE_CLASSIFICATION = "SHADOW_RELEASE"
SHADOW_RELEASE_EXECUTION_BOUNDARY = (
    "LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL"
)
SHADOW_RELEASE_CAPITAL_EXPOSURE = "NONE"
SHADOW_RELEASE_ORDER_EXECUTION = "PROHIBITED"

_INPUT_SCHEMA_NAME = "shadow-release-input"
_ALLOWED_MODES = frozenset({"SWING", "INTRADAY", "SCALP"})
_ALLOWED_OUTCOME_KINDS = frozenset({"PUBLISHED_SIGNAL", "NO_TRADE"})
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)

_INPUT_FIELDS = frozenset(
    {
        "schema_version",
        "schema_name",
        "classification",
        "execution_boundary",
        "source_commit",
        "source_evaluation_id",
        "mode",
        "market_identity",
        "captured_at",
        "evaluation_started_at",
        "evaluation_completed_at",
        "serialized_inputs",
        "serialized_input_hash",
        "expected_decision",
        "expected_decision_hash",
        "source_publication_ref",
        "signal_geometry",
        "lifecycle_trace",
        "outcome_kind",
    }
)
_MARKET_FIELDS = frozenset(
    {
        "venue",
        "symbol",
        "interval",
        "market_data_source",
        "market_input_hash",
    }
)
_SOURCE_FIELDS = frozenset(
    {
        "signal_id",
        "delivery_id",
        "mode",
        "published_at",
        "source_payload_hash",
    }
)
_GEOMETRY_FIELDS = frozenset(
    {
        "symbol",
        "side",
        "entry_zone",
        "stop_loss",
        "take_profit",
        "valid_until",
    }
)
_LIFECYCLE_FIELDS = frozenset(
    {
        "publication",
        "entry_eligibility",
        "cancellation",
        "entry_touch",
        "tp_sl_ordering",
        "acknowledgment",
        "terminal_state",
    }
)
_PROJECTION_FIELDS = frozenset(
    {
        "validated_pipeline",
        "outcome_snapshot",
        "watchlist",
        "pre_delivery",
        "tradingview_watchlist",
        "pine_bridge",
        "pine_delivery_payload",
        "publication",
        "lifecycle",
    }
)
_NONSEMANTIC_METADATA_FIELDS = frozenset(
    {
        "artifact_path",
        "temporary_path",
        "worker_run_id",
        "telegram_update_id",
        "process_id",
        "filesystem_timestamp",
        "transport_attempt_id",
    }
)
_COMPONENT_VERSION_FIELDS = frozenset(
    {
        "master_engine",
        "validated_pipeline",
        "pre_delivery",
        "shadow_contract",
        "shadow_runner",
    }
)
_FAILURE_FIELDS = frozenset({"primary_code", "component", "message"})
_FAILURE_CODES = frozenset(
    {
        "INPUT_CONTRACT_REJECTED",
        "SOURCE_AUTHORITY_MISSING",
        "COMPONENT_VERSION_UNSUPPORTED",
        "SHADOW_EXECUTION_FAILED",
        "ARTIFACT_PUBLICATION_FAILED",
        "ROOT_ISOLATION_VIOLATION",
        "IDENTITY_COLLISION",
        "CONCURRENCY_CONFLICT",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "exchange_credentials",
        "private_endpoint",
        "order_payload",
        "position_size",
        "account_state",
        "balance_state",
        "portfolio_state",
        "exchange_execution",
        "api_secret",
        "private_key",
    }
)


class ShadowReleaseContractError(ValueError):
    """Raised when serialized Phase 08 evidence violates the freeze."""


def canonical_json_bytes(payload: Any) -> bytes:
    """Return deterministic UTF-8 canonical JSON bytes."""

    _reject_non_finite(payload)
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise ShadowReleaseContractError(
            "payload is not canonical JSON"
        ) from exc
    return encoded.encode("utf-8")


def validate_shadow_input_envelope(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and detach one authoritative serialized input envelope."""

    envelope = _require_exact_mapping(value, _INPUT_FIELDS, "input envelope")
    _reject_forbidden_fields(envelope)

    if type(envelope["schema_version"]) is not int or (
        envelope["schema_version"] != SHADOW_RELEASE_SCHEMA_VERSION
    ):
        raise ShadowReleaseContractError("invalid input schema version")
    if envelope["schema_name"] != _INPUT_SCHEMA_NAME:
        raise ShadowReleaseContractError("invalid input schema name")
    if envelope["classification"] != SHADOW_RELEASE_CLASSIFICATION:
        raise ShadowReleaseContractError("invalid input classification")
    if (
        envelope["execution_boundary"]
        != SHADOW_RELEASE_EXECUTION_BOUNDARY
    ):
        raise ShadowReleaseContractError("invalid input execution boundary")

    _require_commit(envelope["source_commit"], "source_commit")
    _require_nonempty_string(
        envelope["source_evaluation_id"], "source_evaluation_id"
    )
    _require_mode(envelope["mode"])
    _validate_market_identity(envelope["market_identity"])

    captured = _parse_utc(envelope["captured_at"], "captured_at")
    evaluation_started = _parse_utc(
        envelope["evaluation_started_at"], "evaluation_started_at"
    )
    evaluation_completed = _parse_utc(
        envelope["evaluation_completed_at"], "evaluation_completed_at"
    )
    if evaluation_completed < evaluation_started:
        raise ShadowReleaseContractError(
            "evaluation completion precedes evaluation start"
        )
    if captured < evaluation_completed:
        raise ShadowReleaseContractError(
            "captured_at precedes evaluation completion"
        )

    _require_mapping(envelope["serialized_inputs"], "serialized_inputs")
    canonical_json_bytes(envelope["serialized_inputs"])
    _require_sha256(envelope["serialized_input_hash"], "serialized_input_hash")
    _validate_semantic_projection(envelope["expected_decision"])
    _require_sha256(
        envelope["expected_decision_hash"], "expected_decision_hash"
    )

    outcome_kind = envelope["outcome_kind"]
    if outcome_kind not in _ALLOWED_OUTCOME_KINDS:
        raise ShadowReleaseContractError("invalid outcome kind")

    if outcome_kind == "PUBLISHED_SIGNAL":
        if envelope["source_publication_ref"] is None:
            raise ShadowReleaseContractError(
                "authoritative source publication identity is required"
            )
        if envelope["signal_geometry"] is None:
            raise ShadowReleaseContractError(
                "authoritative signal geometry is required"
            )
        _validate_source_publication_ref(envelope["source_publication_ref"])
        _validate_signal_geometry(envelope["signal_geometry"])
    else:
        if envelope["source_publication_ref"] is not None or (
            envelope["signal_geometry"] is not None
        ):
            raise ShadowReleaseContractError(
                "NO_TRADE must not contain publication identity"
            )
        if envelope["expected_decision"].get("publication") is not None:
            raise ShadowReleaseContractError(
                "NO_TRADE expected decision contains publication identity"
            )

    _validate_lifecycle(envelope["lifecycle_trace"])
    canonical_json_bytes(envelope)
    return copy.deepcopy(envelope)


def build_shadow_run_id(source_envelope: Mapping[str, Any]) -> str:
    """Derive the deterministic shadow identity from serialized authority."""

    envelope = validate_shadow_input_envelope(source_envelope)
    identity_payload = {
        "schema_version": SHADOW_RELEASE_SCHEMA_VERSION,
        "source_commit": envelope["source_commit"],
        "source_evaluation_id": envelope["source_evaluation_id"],
        "mode": envelope["mode"],
        "market_identity": copy.deepcopy(envelope["market_identity"]),
        "outcome_kind": envelope["outcome_kind"],
        "source_publication_ref": copy.deepcopy(
            envelope["source_publication_ref"]
        ),
        "serialized_input_hash": envelope["serialized_input_hash"],
        "expected_decision_hash": envelope["expected_decision_hash"],
    }
    return "SHR-" + _hash_payload(identity_payload)


def compare_semantic_projections(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare two closed decision projections using exact semantics."""

    expected_projection = _validate_semantic_projection(
        expected, strict_lifecycle=False
    )
    observed_projection = _validate_semantic_projection(
        observed, strict_lifecycle=False
    )
    expected_semantic = _without_operational_metadata(expected_projection)
    observed_semantic = _without_operational_metadata(observed_projection)

    if canonical_json_bytes(expected_semantic) == canonical_json_bytes(
        observed_semantic
    ):
        return _comparison("MATCH", None)

    expected_no_trade = _is_no_trade(expected_semantic)
    observed_no_trade = _is_no_trade(observed_semantic)
    if expected_no_trade != observed_no_trade:
        return _comparison("MISMATCH", "NO_TRADE_MISMATCH")

    publication_fields = (
        "publication",
        "pre_delivery",
        "tradingview_watchlist",
        "pine_bridge",
        "pine_delivery_payload",
    )
    if any(
        expected_semantic[field] != observed_semantic[field]
        for field in publication_fields
    ):
        return _comparison("MISMATCH", "PUBLICATION_MISMATCH")

    if expected_semantic["lifecycle"] != observed_semantic["lifecycle"]:
        return _comparison("MISMATCH", "LIFECYCLE_MISMATCH")

    return _comparison("MISMATCH", "DECISION_MISMATCH")


def build_shadow_run_contract(
    *,
    source_envelope: Mapping[str, Any],
    observed_decision: Mapping[str, Any],
    component_versions: Mapping[str, Any],
    started_at: str,
    completed_at: str,
    failure: Mapping[str, Any] | None,
    content_hash: Any = None,
) -> dict[str, Any]:
    """Build one immutable completed Shadow Release evidence object."""

    if content_hash is not None:
        raise ShadowReleaseContractError("content_hash is derived")

    envelope = validate_shadow_input_envelope(source_envelope)
    observed = _validate_semantic_projection(observed_decision)
    versions = _validate_component_versions(component_versions)
    started = _parse_utc(started_at, "started_at")
    completed = _parse_utc(completed_at, "completed_at")
    if completed < started:
        raise ShadowReleaseContractError("completed_at precedes started_at")
    duration_microseconds = _delta_microseconds(completed - started)
    if duration_microseconds % 1000 != 0:
        raise ShadowReleaseContractError(
            "operational duration is not an exact millisecond"
        )

    comparison = compare_semantic_projections(
        envelope["expected_decision"], observed
    )
    validated_failure = None
    if failure is not None:
        validated_failure = _validate_failure(failure)
        comparison = _comparison(
            "FAILED", validated_failure["primary_code"]
        )

    payload = {
        "schema_version": SHADOW_RELEASE_SCHEMA_VERSION,
        "schema_name": SHADOW_RELEASE_SCHEMA_NAME,
        "classification": SHADOW_RELEASE_CLASSIFICATION,
        "execution_boundary": SHADOW_RELEASE_EXECUTION_BOUNDARY,
        "capital_exposure": SHADOW_RELEASE_CAPITAL_EXPOSURE,
        "order_execution": SHADOW_RELEASE_ORDER_EXECUTION,
        "position_authority": "NONE",
        "shadow_run_id": build_shadow_run_id(envelope),
        "source_commit": envelope["source_commit"],
        "source_evaluation_id": envelope["source_evaluation_id"],
        "mode": envelope["mode"],
        "market_identity": copy.deepcopy(envelope["market_identity"]),
        "outcome_kind": envelope["outcome_kind"],
        "source_publication_ref": copy.deepcopy(
            envelope["source_publication_ref"]
        ),
        "serialized_input_hash": envelope["serialized_input_hash"],
        "expected_decision": copy.deepcopy(envelope["expected_decision"]),
        "expected_decision_hash": envelope["expected_decision_hash"],
        "observed_decision": copy.deepcopy(observed),
        "observed_decision_hash": _hash_payload(
            _without_operational_metadata(observed)
        ),
        "comparison": comparison,
        "component_versions": versions,
        "evaluation_started_at": envelope["evaluation_started_at"],
        "evaluation_completed_at": envelope["evaluation_completed_at"],
        "started_at": started_at,
        "completed_at": completed_at,
        "operational_duration_ms": duration_microseconds // 1000,
        "failure": validated_failure,
    }
    payload["content_hash"] = _hash_payload(payload)
    return payload


def _validate_market_identity(value: Any) -> dict[str, Any]:
    market = _require_exact_mapping(value, _MARKET_FIELDS, "market identity")
    for field in ("venue", "symbol", "interval", "market_data_source"):
        _require_nonempty_string(market[field], field)
    _require_sha256(market["market_input_hash"], "market_input_hash")
    return market


def _validate_source_publication_ref(value: Any) -> dict[str, Any]:
    source = _require_exact_mapping(
        value, _SOURCE_FIELDS, "source publication reference"
    )
    for field in ("signal_id", "delivery_id"):
        text = _require_nonempty_string(source[field], field)
        if "process" in text.casefold() or "guessed" in text.casefold():
            raise ShadowReleaseContractError(
                "source identity must be authoritative serialized input"
            )
    _require_mode(source["mode"])
    _parse_utc(source["published_at"], "published_at")
    _require_sha256(source["source_payload_hash"], "source_payload_hash")
    return source


def _validate_signal_geometry(value: Any) -> dict[str, Any]:
    geometry = _require_exact_mapping(
        value, _GEOMETRY_FIELDS, "signal geometry"
    )
    _require_nonempty_string(geometry["symbol"], "geometry.symbol")
    if geometry["side"] not in {"LONG", "SHORT"}:
        raise ShadowReleaseContractError("invalid signal side")
    entry_zone = _require_exact_mapping(
        geometry["entry_zone"], frozenset({"min", "max"}), "entry zone"
    )
    targets = _require_exact_mapping(
        geometry["take_profit"], frozenset({"tp1", "tp2"}), "take profit"
    )
    for field, number in (
        ("entry_zone.min", entry_zone["min"]),
        ("entry_zone.max", entry_zone["max"]),
        ("stop_loss", geometry["stop_loss"]),
        ("take_profit.tp1", targets["tp1"]),
        ("take_profit.tp2", targets["tp2"]),
    ):
        _require_finite_number(number, field)
    _parse_utc(geometry["valid_until"], "valid_until")
    return geometry


def _validate_lifecycle(value: Any) -> dict[str, Any]:
    lifecycle = _require_exact_mapping(value, _LIFECYCLE_FIELDS, "lifecycle")
    for field in (
        "publication",
        "entry_eligibility",
        "entry_touch",
        "tp_sl_ordering",
        "terminal_state",
    ):
        _require_nonempty_string(lifecycle[field], f"lifecycle.{field}")
    for field in ("cancellation", "acknowledgment"):
        item = lifecycle[field]
        if item is not None and not isinstance(item, Mapping):
            raise ShadowReleaseContractError(
                f"lifecycle.{field} must be an object or null"
            )
    return lifecycle


def _validate_semantic_projection(
    value: Any, *, strict_lifecycle: bool = True
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ShadowReleaseContractError("semantic projection must be an object")
    actual = frozenset(value.keys())
    allowed = _PROJECTION_FIELDS | {"operational_metadata"}
    if not _PROJECTION_FIELDS.issubset(actual) or not actual.issubset(allowed):
        raise ShadowReleaseContractError(
            "semantic projection fields do not match the frozen contract"
        )
    projection = copy.deepcopy(dict(value))
    _reject_forbidden_fields(projection)
    if strict_lifecycle:
        _validate_lifecycle(projection["lifecycle"])
    else:
        _require_exact_mapping(
            projection["lifecycle"], _LIFECYCLE_FIELDS, "lifecycle"
        )
    publication = projection["publication"]
    if publication is not None:
        _validate_source_publication_ref(publication)
    if "operational_metadata" in projection:
        metadata = _require_mapping(
            projection["operational_metadata"], "operational metadata"
        )
        if not frozenset(metadata).issubset(_NONSEMANTIC_METADATA_FIELDS):
            raise ShadowReleaseContractError(
                "operational metadata contains semantic fields"
            )
    canonical_json_bytes(projection)
    return projection


def _validate_component_versions(value: Any) -> dict[str, Any]:
    versions = _require_exact_mapping(
        value, _COMPONENT_VERSION_FIELDS, "component versions"
    )
    for field, version in versions.items():
        _require_nonempty_string(version, f"component_versions.{field}")
    return versions


def _validate_failure(value: Any) -> dict[str, Any]:
    failure = _require_exact_mapping(value, _FAILURE_FIELDS, "failure")
    if failure["primary_code"] not in _FAILURE_CODES:
        raise ShadowReleaseContractError("invalid failure classification")
    _require_nonempty_string(failure["component"], "failure.component")
    message = _require_nonempty_string(failure["message"], "failure.message")
    lowered = message.casefold()
    if any(marker in lowered for marker in ("token=", "secret", "credential")):
        raise ShadowReleaseContractError("failure evidence contains secret data")
    return failure


def _without_operational_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key != "operational_metadata"
    }


def _is_no_trade(value: Mapping[str, Any]) -> bool:
    return value["publication"] is None or (
        value["lifecycle"].get("publication") == "NO_TRADE"
    )


def _comparison(outcome: str, primary_code: str | None) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "primary_code": primary_code,
        "secondary_codes": [],
    }


def _require_exact_mapping(
    value: Any, fields: frozenset[str], label: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ShadowReleaseContractError(f"{label} must be an object")
    if frozenset(value.keys()) != fields:
        raise ShadowReleaseContractError(
            f"{label} fields do not match the frozen contract"
        )
    return copy.deepcopy(dict(value))


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ShadowReleaseContractError(f"{label} must be an object")
    return copy.deepcopy(dict(value))


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShadowReleaseContractError(f"{field} must be a non-empty string")
    return value


def _require_mode(value: Any) -> str:
    if value not in _ALLOWED_MODES:
        raise ShadowReleaseContractError("invalid shadow mode")
    return value


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ShadowReleaseContractError(f"{field} must be lowercase SHA-256")
    return value


def _require_commit(value: Any, field: str) -> str:
    if not isinstance(value, str) or _COMMIT_PATTERN.fullmatch(value) is None:
        raise ShadowReleaseContractError(f"{field} must be a full commit hash")
    return value


def _require_finite_number(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShadowReleaseContractError(f"{field} must be finite numeric")
    if not math.isfinite(value):
        raise ShadowReleaseContractError(f"{field} must be finite numeric")
    return value


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or _UTC_PATTERN.fullmatch(value) is None:
        raise ShadowReleaseContractError(f"{field} must be ISO-8601 UTC")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ShadowReleaseContractError(
            f"{field} must be valid ISO-8601 UTC"
        ) from exc
    if parsed.tzinfo != timezone.utc:
        raise ShadowReleaseContractError(f"{field} must use UTC")
    return parsed


def _delta_microseconds(delta: Any) -> int:
    return (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.casefold() in _FORBIDDEN_KEYS:
                raise ShadowReleaseContractError(
                    "forbidden execution or account authority field"
                )
            _reject_forbidden_fields(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_forbidden_fields(item)


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ShadowReleaseContractError("non-finite values are prohibited")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_non_finite(key)
            _reject_non_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_non_finite(item)
