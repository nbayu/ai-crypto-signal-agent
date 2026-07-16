"""Phase 09 production-signal publication orchestration."""

from __future__ import annotations

import copy
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from engine.production_signal_artifact_v1 import (
    ProductionSignalArtifactError,
    publish_completed_publication,
    publish_no_trade_evaluation,
    publish_publication_intent,
    read_publication_artifact,
)
from engine.production_signal_contract_v1 import (
    DELIVERY_FAILED,
    DELIVERY_INTENT_PERSISTED,
    DELIVERY_SUCCEEDED,
    OUTCOME_NO_TRADE,
    ProductionSignalContractError,
    build_completed_publication,
    build_delivery_id,
    build_no_trade_evaluation,
    build_publication_intent,
    build_publication_payload,
    build_signal_geometry,
    build_signal_id,
    canonical_json_bytes,
    validate_production_signal_input,
)


_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
_RECEIPT_FIELDS = frozenset(
    {"channel", "destination_id", "external_delivery_id", "delivered_at"}
)
_SANITIZED_FAILURE = {
    "primary_code": "DELIVERY_ADAPTER_FAILED",
    "component": "delivery_adapter",
    "message": "delivery adapter failed",
}


class ProductionSignalServiceError(RuntimeError):
    """Raised when production-signal orchestration fails closed."""


def run_production_signal_service_v1(
    *,
    source_envelope: Mapping[str, Any],
    publication_root: str | Path,
    channel: str,
    destination_id: str,
    published_at: str,
    delivery_adapter: Any,
    component_versions: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one deterministic production-signal publication operation."""

    source, versions, root = _validate_invocation(
        source_envelope=source_envelope,
        publication_root=publication_root,
        channel=channel,
        destination_id=destination_id,
        published_at=published_at,
        delivery_adapter=delivery_adapter,
        component_versions=component_versions,
    )

    if source["outcome_kind"] == OUTCOME_NO_TRADE:
        return _publish_no_trade(
            source=source,
            publication_root=root,
            recorded_at=published_at,
        )

    return _publish_signal(
        source=source,
        publication_root=root,
        channel=channel,
        destination_id=destination_id,
        published_at=published_at,
        delivery_adapter=delivery_adapter,
        component_versions=versions,
    )


def _validate_invocation(
    *,
    source_envelope: Mapping[str, Any],
    publication_root: str | Path,
    channel: str,
    destination_id: str,
    published_at: str,
    delivery_adapter: Any,
    component_versions: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str], Path]:
    if not isinstance(channel, str) or not channel.strip():
        raise ProductionSignalServiceError("invalid service configuration")
    if not isinstance(destination_id, str) or not destination_id.strip():
        raise ProductionSignalServiceError("invalid service configuration")
    _parse_utc(published_at)
    if not callable(delivery_adapter):
        raise ProductionSignalServiceError("invalid service configuration")

    try:
        root = Path(publication_root)
    except (TypeError, ValueError, OSError) as exc:
        raise ProductionSignalServiceError(
            "invalid service configuration"
        ) from exc
    if not root.name:
        raise ProductionSignalServiceError("invalid service configuration")

    versions = _validate_versions(component_versions)
    try:
        source = validate_production_signal_input(
            copy.deepcopy(source_envelope)
        )
    except (ProductionSignalContractError, TypeError, ValueError) as exc:
        raise ProductionSignalServiceError("invalid source contract") from exc

    try:
        source_versions = _validate_versions(source["component_versions"])
    except ProductionSignalServiceError as exc:
        raise ProductionSignalServiceError("invalid source contract") from exc
    if versions != source_versions:
        raise ProductionSignalServiceError("component version mismatch")

    return copy.deepcopy(source), copy.deepcopy(versions), root


def _validate_versions(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise ProductionSignalServiceError("invalid component versions")
    result = copy.deepcopy(dict(value))
    for key, version in result.items():
        if not isinstance(key, str) or not key.strip():
            raise ProductionSignalServiceError("invalid component versions")
        if not isinstance(version, str) or not version.strip():
            raise ProductionSignalServiceError("invalid component versions")
    return result


def _publish_no_trade(
    *,
    source: Mapping[str, Any],
    publication_root: Path,
    recorded_at: str,
) -> dict[str, Any]:
    try:
        evaluation = build_no_trade_evaluation(
            source_envelope=copy.deepcopy(source),
            recorded_at=recorded_at,
        )
    except (ProductionSignalContractError, TypeError, ValueError) as exc:
        raise ProductionSignalServiceError(
            "evaluation contract failure"
        ) from exc

    try:
        artifact_path = publish_no_trade_evaluation(
            publication_root=publication_root,
            payload=copy.deepcopy(evaluation),
        )
    except ProductionSignalArtifactError as exc:
        raise ProductionSignalServiceError(
            "evaluation artifact failure"
        ) from exc

    return {
        "publication": None,
        "evaluation": copy.deepcopy(evaluation),
        "source_publication_ref": None,
        "artifact_path": Path(artifact_path),
    }


def _publish_signal(
    *,
    source: Mapping[str, Any],
    publication_root: Path,
    channel: str,
    destination_id: str,
    published_at: str,
    delivery_adapter: Any,
    component_versions: Mapping[str, str],
) -> dict[str, Any]:
    try:
        setup = copy.deepcopy(source["eligible_setups"][0])
        geometry = build_signal_geometry(setup)
        geometry_hash = _hash_payload(geometry)
        source_payload_hash = setup["source_payload_hash"]
        signal_id = build_signal_id(
            source_envelope=copy.deepcopy(source),
            signal_geometry_hash=geometry_hash,
            source_payload_hash=source_payload_hash,
        )
        publication_payload = build_publication_payload(
            source_envelope=copy.deepcopy(source),
            signal_id=signal_id,
            signal_geometry=copy.deepcopy(geometry),
        )
        publication_payload_hash = _hash_payload(publication_payload)
        delivery_id = build_delivery_id(
            signal_id=signal_id,
            channel=channel,
            destination_id=destination_id,
            publication_payload_hash=publication_payload_hash,
        )
        intent = build_publication_intent(
            source_envelope=copy.deepcopy(source),
            signal_id=signal_id,
            delivery_id=delivery_id,
            published_at=published_at,
            channel=channel,
            destination_id=destination_id,
            signal_geometry=copy.deepcopy(geometry),
            signal_geometry_hash=geometry_hash,
            publication_payload=copy.deepcopy(publication_payload),
            publication_payload_hash=publication_payload_hash,
            source_payload_hash=source_payload_hash,
        )
    except (ProductionSignalContractError, TypeError, ValueError) as exc:
        raise ProductionSignalServiceError(
            "publication contract failure"
        ) from exc

    if intent["component_versions"] != component_versions:
        raise ProductionSignalServiceError("component version mismatch")

    existing = _read_existing(
        publication_root=publication_root,
        signal_id=signal_id,
        delivery_id=delivery_id,
    )
    if existing is not None:
        return _existing_result(existing, intent, publication_root)

    try:
        artifact_path = publish_publication_intent(
            publication_root=publication_root,
            payload=copy.deepcopy(intent),
        )
    except ProductionSignalArtifactError as exc:
        concurrent = _read_existing(
            publication_root=publication_root,
            signal_id=signal_id,
            delivery_id=delivery_id,
        )
        if concurrent is not None:
            return _existing_result(concurrent, intent, publication_root)
        raise ProductionSignalServiceError(
            "publication artifact failure"
        ) from exc

    detached_payload = copy.deepcopy(publication_payload)
    try:
        receipt = delivery_adapter(
            detached_payload,
            channel=channel,
            destination_id=destination_id,
        )
    except Exception:
        completed = _build_completion(
            intent=intent,
            delivery_receipt=None,
            failure=copy.deepcopy(_SANITIZED_FAILURE),
        )
    else:
        validated_receipt = _validate_receipt(
            receipt,
            channel=channel,
            destination_id=destination_id,
            published_at=published_at,
        )
        completed = _build_completion(
            intent=intent,
            delivery_receipt=validated_receipt,
            failure=None,
        )

    try:
        artifact_path = publish_completed_publication(
            publication_root=publication_root,
            payload=copy.deepcopy(completed),
        )
    except ProductionSignalArtifactError as exc:
        raise ProductionSignalServiceError(
            "completion artifact failure"
        ) from exc

    return _completed_result(completed, artifact_path)


def _read_existing(
    *,
    publication_root: Path,
    signal_id: str,
    delivery_id: str,
) -> dict[str, Any] | None:
    destination = (
        publication_root
        / "publications"
        / signal_id
        / f"{delivery_id}.json"
    )
    if not destination.exists() and not destination.is_symlink():
        return None
    try:
        return read_publication_artifact(
            publication_root=publication_root,
            signal_id=signal_id,
            delivery_id=delivery_id,
        )
    except ProductionSignalArtifactError as exc:
        raise ProductionSignalServiceError(
            "existing publication artifact failure"
        ) from exc


def _existing_result(
    publication: Mapping[str, Any],
    expected_intent: Mapping[str, Any],
    publication_root: Path,
) -> dict[str, Any]:
    mutable_fields = {
        "delivery_state",
        "delivery_receipt",
        "failure",
        "content_hash",
    }
    existing_authority = {
        key: copy.deepcopy(value)
        for key, value in publication.items()
        if key not in mutable_fields
    }
    expected_authority = {
        key: copy.deepcopy(value)
        for key, value in expected_intent.items()
        if key not in mutable_fields
    }
    try:
        authority_matches = (
            canonical_json_bytes(existing_authority)
            == canonical_json_bytes(expected_authority)
        )
    except ProductionSignalContractError as exc:
        raise ProductionSignalServiceError(
            "existing publication authority is invalid"
        ) from exc
    if not authority_matches:
        raise ProductionSignalServiceError(
            "publication identity collision"
        )

    state = publication.get("delivery_state")
    if state == DELIVERY_INTENT_PERSISTED:
        raise ProductionSignalServiceError(
            "existing publication is unfinished"
        )
    if state not in {DELIVERY_SUCCEEDED, DELIVERY_FAILED}:
        raise ProductionSignalServiceError(
            "existing publication state is invalid"
        )
    artifact_path = (
        publication_root
        / "publications"
        / publication["signal_id"]
        / f'{publication["delivery_id"]}.json'
    ).resolve()
    return _completed_result(publication, artifact_path)


def _validate_receipt(
    value: Mapping[str, Any],
    *,
    channel: str,
    destination_id: str,
    published_at: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_FIELDS:
        raise ProductionSignalServiceError("invalid delivery receipt")
    receipt = copy.deepcopy(dict(value))
    for field in ("channel", "destination_id", "external_delivery_id"):
        if not isinstance(receipt[field], str) or not receipt[field].strip():
            raise ProductionSignalServiceError("invalid delivery receipt")
    if receipt["channel"] != channel:
        raise ProductionSignalServiceError("invalid delivery receipt")
    if receipt["destination_id"] != destination_id:
        raise ProductionSignalServiceError("invalid delivery receipt")
    delivered_at = _parse_utc(receipt["delivered_at"], receipt=True)
    if delivered_at < _parse_utc(published_at):
        raise ProductionSignalServiceError("invalid delivery receipt")
    return receipt


def _build_completion(
    *,
    intent: Mapping[str, Any],
    delivery_receipt: Mapping[str, Any] | None,
    failure: Mapping[str, Any] | None,
) -> dict[str, Any]:
    try:
        return build_completed_publication(
            intent=copy.deepcopy(intent),
            delivery_receipt=copy.deepcopy(delivery_receipt),
            failure=copy.deepcopy(failure),
        )
    except (ProductionSignalContractError, TypeError, ValueError) as exc:
        raise ProductionSignalServiceError(
            "completion contract failure"
        ) from exc


def _completed_result(
    publication: Mapping[str, Any],
    artifact_path: Path,
) -> dict[str, Any]:
    detached = copy.deepcopy(dict(publication))
    return {
        "publication": detached,
        "evaluation": None,
        "source_publication_ref": copy.deepcopy(
            detached["source_publication_ref"]
        ),
        "artifact_path": Path(artifact_path),
    }


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _parse_utc(value: Any, *, receipt: bool = False) -> datetime:
    if not isinstance(value, str) or _UTC_PATTERN.fullmatch(value) is None:
        message = "invalid delivery receipt" if receipt else "invalid service configuration"
        raise ProductionSignalServiceError(message)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        message = "invalid delivery receipt" if receipt else "invalid service configuration"
        raise ProductionSignalServiceError(message) from exc
    if parsed.tzinfo != timezone.utc:
        message = "invalid delivery receipt" if receipt else "invalid service configuration"
        raise ProductionSignalServiceError(message)
    return parsed
