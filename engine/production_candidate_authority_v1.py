"""Detached caller authority and a pure adapter-backed candidate source."""
from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from engine.master_engine_production_candidate_adapter_v1 import (
    NO_ELIGIBLE_SIGNAL,
    PRODUCTION_CANDIDATE_READY,
    adapt_master_engine_result_to_production_candidate,
)


INVALID_SOURCE_AUTHORITY = "INVALID_SOURCE_AUTHORITY"
INVALID_CANDIDATE_SOURCE = "INVALID_CANDIDATE_SOURCE"
INVALID_SIGNAL_CANDIDATE = "INVALID_SIGNAL_CANDIDATE"

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_SENSITIVE_TEXT = ("credential", "password", "secret", "token")
_MAX_EVALUATION_ID_LENGTH = 128
_MAX_STRATEGY_VERSION_LENGTH = 128


class ProductionCandidateAuthorityValidationError(ValueError):
    """A fixed, non-disclosing authority validation error."""


class AdapterBackedProductionCandidateSourceValidationError(ValueError):
    """A fixed, non-disclosing source construction error."""


def _invalid_authority() -> None:
    raise ProductionCandidateAuthorityValidationError(INVALID_SOURCE_AUTHORITY)


def _nonblank_text(value: object, *, maximum: int) -> str | None:
    if not isinstance(value, str) or not value or value != value.strip():
        return None
    if len(value) > maximum or _CONTROL.search(value) is not None:
        return None
    return value


def _evaluation_id(value: object) -> str | None:
    text = _nonblank_text(value, maximum=_MAX_EVALUATION_ID_LENGTH)
    if text is None or "/" in text or "\\" in text:
        return None
    if any(marker in text.casefold() for marker in _SENSITIVE_TEXT):
        return None
    return text


def _logical_manifest_path(value: object) -> str | None:
    text = _nonblank_text(value, maximum=_MAX_EVALUATION_ID_LENGTH)
    if text is None or text.startswith(("/", "\\")):
        return None
    if _WINDOWS_ABSOLUTE.fullmatch(text) is not None:
        return None
    if any(part == ".." for part in text.replace("\\", "/").split("/")):
        return None
    return text


def _utc_text(value: object) -> str | None:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        return None
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return None
    return value


def _finite(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return value


def _evidence(value: object) -> Mapping[str, str] | None:
    if not isinstance(value, Mapping) or set(value) != {"manifest_hash", "manifest_path"}:
        return None
    manifest_hash = value.get("manifest_hash")
    manifest_path = _logical_manifest_path(value.get("manifest_path"))
    if not isinstance(manifest_hash, str) or _HASH.fullmatch(manifest_hash) is None:
        return None
    if manifest_path is None:
        return None
    return MappingProxyType({"manifest_hash": manifest_hash, "manifest_path": manifest_path})


def _versions(value: object) -> Mapping[str, str] | None:
    if not isinstance(value, Mapping) or not value:
        return None
    normalized: dict[str, str] = {}
    for key, item in value.items():
        valid_key = _nonblank_text(key, maximum=_MAX_STRATEGY_VERSION_LENGTH)
        valid_value = _nonblank_text(item, maximum=_MAX_STRATEGY_VERSION_LENGTH)
        if valid_key is None or valid_value is None:
            return None
        normalized[valid_key] = valid_value
    if len(normalized) != len(value):
        return None
    return MappingProxyType(dict(sorted(normalized.items())))


def _contains_callable(value: object) -> bool:
    if callable(value):
        return True
    if isinstance(value, Mapping):
        return any(_contains_callable(key) or _contains_callable(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_callable(item) for item in value)
    return False


@dataclass(frozen=True, slots=True)
class ProductionCandidateAuthorityV1:
    """Strict, caller-owned production authority with detached nested mappings."""

    source_commit: str
    source_evaluation_id: str
    production_evidence_ref: Mapping[str, str]
    component_versions: Mapping[str, str]
    tp2: int | float
    valid_until: str
    strategy_version: str
    source_payload_hash: str

    def __post_init__(self) -> None:
        try:
            if not isinstance(self.source_commit, str) or _COMMIT.fullmatch(self.source_commit) is None:
                _invalid_authority()
            evaluation_id = _evaluation_id(self.source_evaluation_id)
            evidence = _evidence(self.production_evidence_ref)
            versions = _versions(self.component_versions)
            target = _finite(self.tp2)
            valid_until = _utc_text(self.valid_until)
            strategy_version = _nonblank_text(
                self.strategy_version,
                maximum=_MAX_STRATEGY_VERSION_LENGTH,
            )
            if (
                evaluation_id is None
                or evidence is None
                or versions is None
                or target is None
                or valid_until is None
                or strategy_version is None
                or not isinstance(self.source_payload_hash, str)
                or _HASH.fullmatch(self.source_payload_hash) is None
            ):
                _invalid_authority()
        except ProductionCandidateAuthorityValidationError:
            raise
        except Exception as exc:
            raise ProductionCandidateAuthorityValidationError(
                INVALID_SOURCE_AUTHORITY
            ) from exc
        object.__setattr__(self, "source_evaluation_id", evaluation_id)
        object.__setattr__(self, "production_evidence_ref", evidence)
        object.__setattr__(self, "component_versions", versions)
        object.__setattr__(self, "tp2", target)
        object.__setattr__(self, "valid_until", valid_until)
        object.__setattr__(self, "strategy_version", strategy_version)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_commit": self.source_commit,
            "source_evaluation_id": self.source_evaluation_id,
            "production_evidence_ref": dict(self.production_evidence_ref),
            "component_versions": dict(self.component_versions),
            "tp2": self.tp2,
            "valid_until": self.valid_until,
            "strategy_version": self.strategy_version,
            "source_payload_hash": self.source_payload_hash,
        }


@dataclass(frozen=True, slots=True)
class AdapterBackedProductionCandidateSourceV1:
    """A bounded candidate source that invokes only the pure adapter."""

    master_engine_result: Mapping[str, Any] = field(repr=False)
    selected_symbol: str
    mode: str
    evaluated_at: str
    authority: ProductionCandidateAuthorityV1

    def __post_init__(self) -> None:
        try:
            if (
                not isinstance(self.master_engine_result, Mapping)
                or _contains_callable(self.master_engine_result)
                or not isinstance(self.selected_symbol, str)
                or not isinstance(self.mode, str)
                or not isinstance(self.evaluated_at, str)
                or not isinstance(self.authority, ProductionCandidateAuthorityV1)
            ):
                raise AdapterBackedProductionCandidateSourceValidationError(
                    INVALID_CANDIDATE_SOURCE
                )
            detached = copy.deepcopy(dict(self.master_engine_result))
        except AdapterBackedProductionCandidateSourceValidationError:
            raise
        except Exception as exc:
            raise AdapterBackedProductionCandidateSourceValidationError(
                INVALID_CANDIDATE_SOURCE
            ) from exc
        object.__setattr__(self, "master_engine_result", detached)

    def __call__(self) -> Mapping[str, Any]:
        """Return exactly one controlled-cycle candidate-source value."""
        try:
            authority = self.authority.to_dict()
            outcome = adapt_master_engine_result_to_production_candidate(
                master_engine_result=copy.deepcopy(dict(self.master_engine_result)),
                selected_symbol=self.selected_symbol,
                mode=self.mode,
                evaluated_at=self.evaluated_at,
                production_provenance={
                    "source_commit": authority["source_commit"],
                    "source_evaluation_id": authority["source_evaluation_id"],
                    "production_evidence_ref": copy.deepcopy(
                        authority["production_evidence_ref"]
                    ),
                    "component_versions": copy.deepcopy(authority["component_versions"]),
                },
                setup_authority={
                    "tp2": authority["tp2"],
                    "valid_until": authority["valid_until"],
                    "strategy_version": authority["strategy_version"],
                    "source_payload_hash": authority["source_payload_hash"],
                },
            )
            if getattr(outcome, "result", None) == PRODUCTION_CANDIDATE_READY:
                candidate = getattr(outcome, "candidate", None)
                if isinstance(candidate, Mapping):
                    return copy.deepcopy(dict(candidate))
            if getattr(outcome, "result", None) == NO_ELIGIBLE_SIGNAL:
                return {"result": NO_ELIGIBLE_SIGNAL}
        except Exception:
            return {"result": INVALID_SIGNAL_CANDIDATE}
        return {"result": INVALID_SIGNAL_CANDIDATE}


def build_adapter_backed_production_candidate_source(
    *,
    master_engine_result: object,
    selected_symbol: object,
    mode: object,
    evaluated_at: object,
    authority: object,
) -> AdapterBackedProductionCandidateSourceV1:
    """Build a detached source without invoking the adapter or any runtime dependency."""
    try:
        return AdapterBackedProductionCandidateSourceV1(
            master_engine_result=master_engine_result,
            selected_symbol=selected_symbol,
            mode=mode,
            evaluated_at=evaluated_at,
            authority=authority,
        )
    except AdapterBackedProductionCandidateSourceValidationError:
        raise
    except Exception as exc:
        raise AdapterBackedProductionCandidateSourceValidationError(
            INVALID_CANDIDATE_SOURCE
        ) from exc
