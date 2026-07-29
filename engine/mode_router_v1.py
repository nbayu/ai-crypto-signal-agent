"""Pure, deterministic routing boundary for one exact mode scan."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final

from engine.mode_data_plan_v1 import (
    ModeAuditLineageV1,
    ModeDataPlanV1,
    build_mode_audit_lineage,
    build_mode_data_plan,
)
from engine.mode_profile_v1 import (
    ModeProfileV1,
    get_mode_profile,
)


MODE_ROUTER_POLICY_VERSION: Final = "mode-router-policy-v1"
MODE_SCAN_REQUEST_SCHEMA_VERSION: Final = "mode-scan-request-v1"
MODE_ROUTED_CANDIDATE_SCHEMA_VERSION: Final = (
    "mode-routed-candidate-v1"
)
MODE_ROUTE_RESULT_SCHEMA_VERSION: Final = "mode-route-result-v1"

_SAFE_IDENTIFIER: Final = re.compile(r"[A-Za-z0-9._:+-]{1,128}")
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
_CANDIDATE_INPUT_KEYS: Final = frozenset(
    (
        "candidate_id",
        "mode",
        "symbol",
        "mode_lineage_sha256",
        "payload",
    )
)


class ModeRouterValidationError(ValueError):
    """Sanitized failure raised by the mode-router boundary."""


def _invalid() -> None:
    raise ModeRouterValidationError("invalid mode route") from None


def _exact_constant(value: object, expected: str) -> str:
    if type(value) is not str or value != expected:
        _invalid()
    return value


def _canonical_profile(mode: object) -> ModeProfileV1:
    try:
        return get_mode_profile(mode)
    except Exception:
        _invalid()


def _safe_identifier(value: object) -> str:
    if (
        type(value) is not str
        or _SAFE_IDENTIFIER.fullmatch(value) is None
    ):
        _invalid()
    return value


def _symbol(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 128
        or value != value.strip()
    ):
        _invalid()
    return value


def _lineage_sha256(value: object) -> str:
    if type(value) is not str or _SHA256_HEX.fullmatch(value) is None:
        _invalid()
    return value


def _validate_json_value(value: object) -> None:
    if value is None or type(value) in (str, int, float, bool):
        return
    if type(value) is list:
        for item in value:
            _validate_json_value(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _invalid()
            _validate_json_value(item)
        return
    _invalid()


def _canonical_payload_json(payload: object) -> str:
    if type(payload) is not dict:
        _invalid()
    _validate_json_value(payload)
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except Exception:
        _invalid()


def _decoded_payload(payload_json: str) -> dict[str, Any]:
    try:
        decoded = json.loads(payload_json)
        if type(decoded) is not dict:
            _invalid()
        return decoded
    except ModeRouterValidationError:
        raise
    except Exception:
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeScanRequestV1:
    """Canonical immutable request supplied to one injected scanner."""

    schema_version: str
    router_policy_version: str
    mode: str
    due_window_id: str
    mode_profile: ModeProfileV1
    mode_data_plan: ModeDataPlanV1
    mode_audit_lineage: ModeAuditLineageV1

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_SCAN_REQUEST_SCHEMA_VERSION,
            )
            _exact_constant(
                self.router_policy_version,
                MODE_ROUTER_POLICY_VERSION,
            )

            profile = _canonical_profile(self.mode)
            if self.mode_profile is not profile:
                _invalid()

            plan = build_mode_data_plan(profile.mode)
            if (
                type(self.mode_data_plan) is not ModeDataPlanV1
                or _canonical_payload_json(
                    self.mode_data_plan.to_mapping()
                )
                != _canonical_payload_json(plan.to_mapping())
            ):
                _invalid()

            lineage = build_mode_audit_lineage(profile.mode)
            if (
                type(self.mode_audit_lineage) is not ModeAuditLineageV1
                or _canonical_payload_json(
                    self.mode_audit_lineage.to_mapping()
                )
                != _canonical_payload_json(lineage.to_mapping())
            ):
                _invalid()

            if (
                self.mode_data_plan.mode != profile.mode
                or self.mode_audit_lineage.mode != profile.mode
                or self.mode_data_plan.profile_policy_version
                != profile.policy_version
                or self.mode_audit_lineage.mode_profile_version
                != profile.policy_version
                or self.mode_audit_lineage.mode_data_plan_version
                != self.mode_data_plan.policy_version
            ):
                _invalid()

            _safe_identifier(self.due_window_id)
        except ModeRouterValidationError:
            raise
        except Exception:
            _invalid()


@dataclass(frozen=True, slots=True)
class ModeRoutedCandidateV1:
    """Validated candidate with an immutable canonical payload."""

    schema_version: str
    candidate_id: str
    mode: str
    symbol: str
    mode_lineage_sha256: str
    payload_json: str
    payload_sha256: str

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_ROUTED_CANDIDATE_SCHEMA_VERSION,
            )

            profile = _canonical_profile(self.mode)
            expected_lineage = build_mode_audit_lineage(
                profile.mode
            ).lineage_sha256

            _safe_identifier(self.candidate_id)
            _symbol(self.symbol)
            if (
                _lineage_sha256(self.mode_lineage_sha256)
                != expected_lineage
            ):
                _invalid()
            if type(self.payload_json) is not str:
                _invalid()

            payload = _decoded_payload(self.payload_json)
            if _canonical_payload_json(payload) != self.payload_json:
                _invalid()
            if (
                "mode" in payload
                and payload["mode"] != profile.mode
            ):
                _invalid()
            if (
                "mode_lineage_sha256" in payload
                and payload["mode_lineage_sha256"]
                != expected_lineage
            ):
                _invalid()

            expected_payload_hash = hashlib.sha256(
                self.payload_json.encode("utf-8")
            ).hexdigest()
            if (
                _lineage_sha256(self.payload_sha256)
                != expected_payload_hash
            ):
                _invalid()
        except ModeRouterValidationError:
            raise
        except Exception:
            _invalid()

    def payload_copy(self) -> dict[str, Any]:
        """Return a newly decoded payload without exposing internal state."""

        return _decoded_payload(self.payload_json)

    def to_mapping(self) -> dict[str, object]:
        """Return a deterministic fresh mapping of candidate fields."""

        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "mode": self.mode,
            "symbol": self.symbol,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "payload_json": self.payload_json,
            "payload_sha256": self.payload_sha256,
        }


def _routed_candidate(
    *,
    request: ModeScanRequestV1,
    candidate_input: object,
) -> ModeRoutedCandidateV1:
    if not isinstance(candidate_input, Mapping):
        _invalid()
    try:
        if (
            len(candidate_input) != len(_CANDIDATE_INPUT_KEYS)
            or frozenset(candidate_input.keys())
            != _CANDIDATE_INPUT_KEYS
        ):
            _invalid()

        candidate_id = candidate_input["candidate_id"]
        mode = candidate_input["mode"]
        symbol = candidate_input["symbol"]
        lineage_sha256 = candidate_input["mode_lineage_sha256"]
        payload = candidate_input["payload"]

        if type(mode) is not str or mode != request.mode:
            _invalid()
        if lineage_sha256 != request.mode_audit_lineage.lineage_sha256:
            _invalid()

        payload_json = _canonical_payload_json(payload)
        return ModeRoutedCandidateV1(
            schema_version=MODE_ROUTED_CANDIDATE_SCHEMA_VERSION,
            candidate_id=_safe_identifier(candidate_id),
            mode=request.mode,
            symbol=_symbol(symbol),
            mode_lineage_sha256=_lineage_sha256(lineage_sha256),
            payload_json=payload_json,
            payload_sha256=hashlib.sha256(
                payload_json.encode("utf-8")
            ).hexdigest(),
        )
    except ModeRouterValidationError:
        raise
    except Exception:
        _invalid()


@dataclass(frozen=True, slots=True)
class ModeRouteResultV1:
    """Immutable result of exactly one scanner invocation."""

    schema_version: str
    router_policy_version: str
    mode: str
    due_window_id: str
    mode_lineage_sha256: str
    scanner_invocation_count: int
    retry_count: int
    candidates: tuple[ModeRoutedCandidateV1, ...]

    def __post_init__(self) -> None:
        try:
            _exact_constant(
                self.schema_version,
                MODE_ROUTE_RESULT_SCHEMA_VERSION,
            )
            _exact_constant(
                self.router_policy_version,
                MODE_ROUTER_POLICY_VERSION,
            )

            profile = _canonical_profile(self.mode)
            expected_lineage = build_mode_audit_lineage(
                profile.mode
            ).lineage_sha256

            _safe_identifier(self.due_window_id)
            if (
                _lineage_sha256(self.mode_lineage_sha256)
                != expected_lineage
            ):
                _invalid()
            if (
                type(self.scanner_invocation_count) is not int
                or self.scanner_invocation_count != 1
            ):
                _invalid()
            if (
                type(self.retry_count) is not int
                or self.retry_count != 0
            ):
                _invalid()
            if type(self.candidates) not in (list, tuple):
                _invalid()

            candidates = tuple(self.candidates)
            object.__setattr__(self, "candidates", candidates)
            candidate_ids: set[str] = set()
            for candidate in candidates:
                if type(candidate) is not ModeRoutedCandidateV1:
                    _invalid()
                if (
                    candidate.mode != profile.mode
                    or candidate.mode_lineage_sha256
                    != expected_lineage
                    or candidate.candidate_id in candidate_ids
                ):
                    _invalid()
                candidate_ids.add(candidate.candidate_id)
        except ModeRouterValidationError:
            raise
        except Exception:
            _invalid()

    def to_mapping(self) -> dict[str, object]:
        """Return deterministic fresh result and candidate containers."""

        return {
            "schema_version": self.schema_version,
            "router_policy_version": self.router_policy_version,
            "mode": self.mode,
            "due_window_id": self.due_window_id,
            "mode_lineage_sha256": self.mode_lineage_sha256,
            "scanner_invocation_count":
                self.scanner_invocation_count,
            "retry_count": self.retry_count,
            "candidates": [
                candidate.to_mapping()
                for candidate in self.candidates
            ],
        }


def build_mode_scan_request(
    *,
    mode: object,
    due_window_id: object,
) -> ModeScanRequestV1:
    """Build one canonical request from exact caller-owned route inputs."""

    try:
        profile = _canonical_profile(mode)
        return ModeScanRequestV1(
            schema_version=MODE_SCAN_REQUEST_SCHEMA_VERSION,
            router_policy_version=MODE_ROUTER_POLICY_VERSION,
            mode=profile.mode,
            due_window_id=_safe_identifier(due_window_id),
            mode_profile=profile,
            mode_data_plan=build_mode_data_plan(profile.mode),
            mode_audit_lineage=build_mode_audit_lineage(
                profile.mode
            ),
        )
    except ModeRouterValidationError:
        raise
    except Exception:
        _invalid()


def route_mode_scan(
    *,
    mode: object,
    due_window_id: object,
    scanner: Callable[..., object],
) -> ModeRouteResultV1:
    """Invoke one injected scanner once and validate its routed output."""

    request = build_mode_scan_request(
        mode=mode,
        due_window_id=due_window_id,
    )
    if not callable(scanner):
        _invalid()

    try:
        scanner_output = scanner(request=request)
    except Exception:
        _invalid()

    if type(scanner_output) not in (list, tuple):
        _invalid()

    try:
        candidates = tuple(
            _routed_candidate(
                request=request,
                candidate_input=candidate_input,
            )
            for candidate_input in scanner_output
        )
        return ModeRouteResultV1(
            schema_version=MODE_ROUTE_RESULT_SCHEMA_VERSION,
            router_policy_version=MODE_ROUTER_POLICY_VERSION,
            mode=request.mode,
            due_window_id=request.due_window_id,
            mode_lineage_sha256=(
                request.mode_audit_lineage.lineage_sha256
            ),
            scanner_invocation_count=1,
            retry_count=0,
            candidates=candidates,
        )
    except ModeRouterValidationError:
        raise
    except Exception:
        _invalid()
