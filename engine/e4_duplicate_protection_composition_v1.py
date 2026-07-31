"""Detached E3-to-E4 duplicate-protection composition evidence."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Final

from engine.e3_actionable_admission_v1 import (
    E3ActionableAdmissionResultV1,
)
from engine.e4_publication_idempotency_guard_v1 import (
    CLAIM_SUPPRESSED_BY_RESET_POLICY,
    CLAIM_SUPPRESSED_EXISTING_THESIS,
    CLAIM_WON_INITIAL_THESIS,
    CLAIM_WON_RESET_THESIS,
    E4PublicationIdempotencyResultV1,
    claim_e4_publication_intent_v1,
)
from engine.e4_thesis_fingerprint_v1 import (
    E4ThesisFingerprintV1,
    build_e4_thesis_fingerprint,
)
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)


__all__ = (
    "E4_DUPLICATE_PROTECTION_COMPOSITION_VERSION",
    "DUPLICATE_PROTECTION_DECISION_CODES",
    "ALLOW_INITIAL_THESIS_PUBLICATION_INTENT",
    "ALLOW_RESET_THESIS_PUBLICATION_INTENT",
    "SUPPRESS_EXISTING_THESIS",
    "SUPPRESS_BY_RESET_POLICY",
    "HOLD_ACTIONABLE_ADMISSION_REQUIRED",
    "E4DuplicateProtectionCompositionResultV1",
    "compose_e4_duplicate_protection_v1",
)


E4_DUPLICATE_PROTECTION_COMPOSITION_VERSION: Final = (
    "e4-duplicate-protection-composition-v1"
)

ALLOW_INITIAL_THESIS_PUBLICATION_INTENT: Final = (
    "ALLOW_INITIAL_THESIS_PUBLICATION_INTENT"
)
ALLOW_RESET_THESIS_PUBLICATION_INTENT: Final = (
    "ALLOW_RESET_THESIS_PUBLICATION_INTENT"
)
SUPPRESS_EXISTING_THESIS: Final = "SUPPRESS_EXISTING_THESIS"
SUPPRESS_BY_RESET_POLICY: Final = "SUPPRESS_BY_RESET_POLICY"
HOLD_ACTIONABLE_ADMISSION_REQUIRED: Final = (
    "HOLD_ACTIONABLE_ADMISSION_REQUIRED"
)

DUPLICATE_PROTECTION_DECISION_CODES: Final = (
    ALLOW_INITIAL_THESIS_PUBLICATION_INTENT,
    ALLOW_RESET_THESIS_PUBLICATION_INTENT,
    SUPPRESS_EXISTING_THESIS,
    SUPPRESS_BY_RESET_POLICY,
    HOLD_ACTIONABLE_ADMISSION_REQUIRED,
)


_ERROR: Final = "invalid E4 duplicate protection composition"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_GUARD_TRANSLATION: Final = {
    CLAIM_WON_INITIAL_THESIS: (
        True,
        ALLOW_INITIAL_THESIS_PUBLICATION_INTENT,
    ),
    CLAIM_WON_RESET_THESIS: (
        True,
        ALLOW_RESET_THESIS_PUBLICATION_INTENT,
    ),
    CLAIM_SUPPRESSED_EXISTING_THESIS: (
        False,
        SUPPRESS_EXISTING_THESIS,
    ),
    CLAIM_SUPPRESSED_BY_RESET_POLICY: (
        False,
        SUPPRESS_BY_RESET_POLICY,
    ),
}


def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _canonical_json(mapping: dict[str, object]) -> str:
    return json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash_mapping(mapping: dict[str, object]) -> str:
    return sha256(_canonical_json(mapping).encode("utf-8")).hexdigest()


def _fingerprint(value: object) -> E4ThesisFingerprintV1:
    _require(type(value) is E4ThesisFingerprintV1)
    value.__post_init__()
    return value


def _guard_result(value: object) -> E4PublicationIdempotencyResultV1:
    _require(type(value) is E4PublicationIdempotencyResultV1)
    value.__post_init__()
    return value


def _composition_preimage(
    result: "E4DuplicateProtectionCompositionResultV1",
) -> dict[str, object]:
    return {
        "composition_version": result.composition_version,
        "actionable_admission_sha256": (
            result.actionable_admission_sha256
        ),
        "actionable_admitted": result.actionable_admitted,
        "fingerprint": (
            result.fingerprint.to_mapping()
            if result.fingerprint is not None
            else None
        ),
        "publication_guard_result": (
            result.publication_guard_result.to_mapping()
            if result.publication_guard_result is not None
            else None
        ),
        "publication_intent_allowed": result.publication_intent_allowed,
        "decision_code": result.decision_code,
    }


@dataclass(frozen=True, slots=True)
class E4DuplicateProtectionCompositionResultV1:
    composition_version: str
    actionable_admission_sha256: str
    actionable_admitted: bool
    fingerprint: E4ThesisFingerprintV1 | None
    publication_guard_result: E4PublicationIdempotencyResultV1 | None
    publication_intent_allowed: bool
    decision_code: str
    composition_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.composition_version) is str)
            _require(
                self.composition_version
                == E4_DUPLICATE_PROTECTION_COMPOSITION_VERSION
            )
            _require(type(self.actionable_admission_sha256) is str)
            _require(
                _SHA256_PATTERN.fullmatch(
                    self.actionable_admission_sha256
                )
                is not None
            )
            _require(type(self.actionable_admitted) is bool)
            _require(type(self.publication_intent_allowed) is bool)
            _require(type(self.decision_code) is str)
            _require(self.decision_code in DUPLICATE_PROTECTION_DECISION_CODES)

            if self.decision_code == HOLD_ACTIONABLE_ADMISSION_REQUIRED:
                _require(self.actionable_admitted is False)
                _require(self.fingerprint is None)
                _require(self.publication_guard_result is None)
                _require(self.publication_intent_allowed is False)
            else:
                _require(self.actionable_admitted is True)
                fingerprint = _fingerprint(self.fingerprint)
                guard = _guard_result(self.publication_guard_result)
                _require(guard.publication_success_recorded is False)
                _require(
                    guard.candidate_identity_sha256
                    == fingerprint.identity_sha256
                )
                _require(guard.canonical_pair == fingerprint.canonical_pair)
                _require(guard.result_code in _GUARD_TRANSLATION)
                expected_allowed, expected_decision = _GUARD_TRANSLATION[
                    guard.result_code
                ]
                _require(guard.claim_won is expected_allowed)
                _require(
                    self.publication_intent_allowed is expected_allowed
                )
                _require(self.decision_code == expected_decision)

            _require(type(self.composition_sha256) is str)
            _require(
                _SHA256_PATTERN.fullmatch(self.composition_sha256)
                is not None
            )
            _require(
                self.composition_sha256
                == _hash_mapping(_composition_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_composition_preimage(self),
            "composition_sha256": self.composition_sha256,
        }

    def canonical_composition_json(self) -> str:
        return _canonical_json(_composition_preimage(self))


def _build_result(
    *,
    actionable_admission_sha256: str,
    actionable_admitted: bool,
    fingerprint: E4ThesisFingerprintV1 | None,
    publication_guard_result: E4PublicationIdempotencyResultV1 | None,
    publication_intent_allowed: bool,
    decision_code: str,
) -> E4DuplicateProtectionCompositionResultV1:
    mapping: dict[str, object] = {
        "composition_version": E4_DUPLICATE_PROTECTION_COMPOSITION_VERSION,
        "actionable_admission_sha256": actionable_admission_sha256,
        "actionable_admitted": actionable_admitted,
        "fingerprint": fingerprint,
        "publication_guard_result": publication_guard_result,
        "publication_intent_allowed": publication_intent_allowed,
        "decision_code": decision_code,
    }
    preimage = {
        **mapping,
        "fingerprint": (
            fingerprint.to_mapping() if fingerprint is not None else None
        ),
        "publication_guard_result": (
            publication_guard_result.to_mapping()
            if publication_guard_result is not None
            else None
        ),
    }
    return E4DuplicateProtectionCompositionResultV1(
        **mapping,
        composition_sha256=_hash_mapping(preimage),
    )


def compose_e4_duplicate_protection_v1(
    *,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    authorized_store_root: Path,
    store_path: Path,
    price_exited_zone: bool,
) -> E4DuplicateProtectionCompositionResultV1:
    try:
        _require(type(actionable_admission) is E3ActionableAdmissionResultV1)
        actionable_admission.__post_init__()
        _require(type(candidate_authority) is ProductionCandidateAuthorityV1)
        candidate_authority.__post_init__()
        _require(isinstance(authorized_store_root, Path))
        _require(isinstance(store_path, Path))
        _require(type(price_exited_zone) is bool)

        if not actionable_admission.actionable_admitted:
            return _build_result(
                actionable_admission_sha256=(
                    actionable_admission.actionable_admission_sha256
                ),
                actionable_admitted=False,
                fingerprint=None,
                publication_guard_result=None,
                publication_intent_allowed=False,
                decision_code=HOLD_ACTIONABLE_ADMISSION_REQUIRED,
            )

        fingerprint = build_e4_thesis_fingerprint(
            geometry=actionable_admission.geometry,
            structural_targets=actionable_admission.structural_targets,
            executable_price_snapshot=(
                actionable_admission.executable_price_snapshot
            ),
            mode_trigger_evidence=(
                actionable_admission.mode_trigger_evidence
            ),
            production_candidate_authority=candidate_authority,
        )
        guard = claim_e4_publication_intent_v1(
            authorized_store_root=authorized_store_root,
            store_path=store_path,
            candidate_fingerprint=fingerprint,
            price_exited_zone=price_exited_zone,
        )
        _guard_result(guard)
        _require(guard.result_code in _GUARD_TRANSLATION)
        publication_intent_allowed, decision_code = _GUARD_TRANSLATION[
            guard.result_code
        ]
        return _build_result(
            actionable_admission_sha256=(
                actionable_admission.actionable_admission_sha256
            ),
            actionable_admitted=True,
            fingerprint=fingerprint,
            publication_guard_result=guard,
            publication_intent_allowed=publication_intent_allowed,
            decision_code=decision_code,
        )
    except Exception:
        _fail()
