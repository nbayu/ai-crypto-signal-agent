"""Deterministic in-process runner for Phase 08 Shadow Release."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from engine.shadow_release_contract_v1 import (
    ShadowReleaseContractError,
    build_shadow_run_contract,
    build_shadow_run_id,
    validate_shadow_input_envelope,
)


class ShadowReleaseRunnerError(ValueError):
    """Raised when runner input cannot produce canonical shadow evidence."""


def run_shadow_release_v1(
    *,
    source_envelope: Mapping[str, Any],
    shadow_run_id: str,
    expected_adapter: Callable[[dict[str, Any]], Any],
    observed_adapter: Callable[[dict[str, Any]], Any],
    component_versions: Mapping[str, Any],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Run each injected adapter once and build canonical shadow evidence."""

    envelope = _validated_envelope(source_envelope)
    canonical_run_id = _canonical_run_id(envelope)
    if shadow_run_id != canonical_run_id:
        raise ShadowReleaseRunnerError(
            "shadow_run_id does not match serialized source authority"
        )

    _require_adapter(expected_adapter, "expected_adapter")
    _require_adapter(observed_adapter, "observed_adapter")

    try:
        expected_decision = expected_adapter(copy.deepcopy(envelope))
    except Exception:
        return _failed_evidence(
            source_envelope=envelope,
            observed_decision=envelope["expected_decision"],
            component_versions=component_versions,
            started_at=started_at,
            completed_at=completed_at,
            component="expected_adapter",
        )
    expected_decision = _require_projection(
        expected_decision, "expected_adapter"
    )

    try:
        observed_decision = observed_adapter(copy.deepcopy(envelope))
    except Exception:
        runtime_envelope = copy.deepcopy(envelope)
        runtime_envelope["expected_decision"] = expected_decision
        return _failed_evidence(
            source_envelope=runtime_envelope,
            observed_decision=expected_decision,
            component_versions=component_versions,
            started_at=started_at,
            completed_at=completed_at,
            component="observed_adapter",
        )
    observed_decision = _require_projection(
        observed_decision, "observed_adapter"
    )

    runtime_envelope = copy.deepcopy(envelope)
    runtime_envelope["expected_decision"] = expected_decision
    return _build_contract(
        source_envelope=runtime_envelope,
        observed_decision=observed_decision,
        component_versions=component_versions,
        started_at=started_at,
        completed_at=completed_at,
        failure=None,
    )


def _validated_envelope(value: Any) -> dict[str, Any]:
    try:
        return validate_shadow_input_envelope(value)
    except ShadowReleaseContractError as exc:
        raise ShadowReleaseRunnerError(
            "serialized source envelope was rejected"
        ) from exc


def _canonical_run_id(envelope: Mapping[str, Any]) -> str:
    try:
        return build_shadow_run_id(envelope)
    except ShadowReleaseContractError as exc:
        raise ShadowReleaseRunnerError(
            "serialized shadow identity was rejected"
        ) from exc


def _require_adapter(value: Any, label: str) -> None:
    if not callable(value):
        raise ShadowReleaseRunnerError(f"{label} must be callable")


def _require_projection(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ShadowReleaseRunnerError(
            f"{label} returned an invalid semantic projection"
        )
    return copy.deepcopy(dict(value))


def _failed_evidence(
    *,
    source_envelope: Mapping[str, Any],
    observed_decision: Mapping[str, Any],
    component_versions: Mapping[str, Any],
    started_at: str,
    completed_at: str,
    component: str,
) -> dict[str, Any]:
    return _build_contract(
        source_envelope=source_envelope,
        observed_decision=observed_decision,
        component_versions=component_versions,
        started_at=started_at,
        completed_at=completed_at,
        failure={
            "primary_code": "SHADOW_EXECUTION_FAILED",
            "component": component,
            "message": "adapter execution failed",
        },
    )


def _build_contract(**arguments: Any) -> dict[str, Any]:
    try:
        return build_shadow_run_contract(**arguments)
    except ShadowReleaseContractError as exc:
        raise ShadowReleaseRunnerError(
            "canonical shadow contract build failed"
        ) from exc
