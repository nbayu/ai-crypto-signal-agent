"""Atomic detached E4 publication-intent idempotency guard."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Final

from engine.canonical_pair_v1 import normalize_pair
from engine.e4_lifecycle_reset_adjudicator_v1 import (
    E4LifecycleResetDecisionV1,
    adjudicate_e4_lifecycle_reset_v1,
)
from engine.e4_thesis_fingerprint_v1 import E4ThesisFingerprintV1
from engine.e4_thesis_history_store_v1 import (
    _authorize_store_paths_v1,
    _load_document_locked_v1,
    _locked_store_v1,
    _write_history_locked_v1,
)
from engine.e4_thesis_history_v1 import (
    append_e4_thesis_history_event_v1,
    create_e4_thesis_history_v1,
)


__all__ = (
    "E4_PUBLICATION_IDEMPOTENCY_GUARD_VERSION",
    "PUBLICATION_IDEMPOTENCY_RESULT_CODES",
    "CLAIM_WON_INITIAL_THESIS",
    "CLAIM_WON_RESET_THESIS",
    "CLAIM_SUPPRESSED_EXISTING_THESIS",
    "CLAIM_SUPPRESSED_BY_RESET_POLICY",
    "PUBLICATION_SUCCESS_RECORDED",
    "PUBLICATION_SUCCESS_ALREADY_RECORDED",
    "E4PublicationIdempotencyResultV1",
    "claim_e4_publication_intent_v1",
    "record_e4_publication_success_v1",
)


E4_PUBLICATION_IDEMPOTENCY_GUARD_VERSION: Final = (
    "e4-publication-idempotency-guard-v1"
)

CLAIM_WON_INITIAL_THESIS: Final = "CLAIM_WON_INITIAL_THESIS"
CLAIM_WON_RESET_THESIS: Final = "CLAIM_WON_RESET_THESIS"
CLAIM_SUPPRESSED_EXISTING_THESIS: Final = (
    "CLAIM_SUPPRESSED_EXISTING_THESIS"
)
CLAIM_SUPPRESSED_BY_RESET_POLICY: Final = (
    "CLAIM_SUPPRESSED_BY_RESET_POLICY"
)
PUBLICATION_SUCCESS_RECORDED: Final = "PUBLICATION_SUCCESS_RECORDED"
PUBLICATION_SUCCESS_ALREADY_RECORDED: Final = (
    "PUBLICATION_SUCCESS_ALREADY_RECORDED"
)

PUBLICATION_IDEMPOTENCY_RESULT_CODES: Final = (
    CLAIM_WON_INITIAL_THESIS,
    CLAIM_WON_RESET_THESIS,
    CLAIM_SUPPRESSED_EXISTING_THESIS,
    CLAIM_SUPPRESSED_BY_RESET_POLICY,
    PUBLICATION_SUCCESS_RECORDED,
    PUBLICATION_SUCCESS_ALREADY_RECORDED,
)


_ERROR: Final = "invalid E4 publication idempotency guard"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")


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


def _reset(value: object) -> E4LifecycleResetDecisionV1:
    _require(type(value) is E4LifecycleResetDecisionV1)
    value.__post_init__()
    return value


def _result_preimage(
    result: "E4PublicationIdempotencyResultV1",
) -> dict[str, object]:
    return {
        "guard_version": result.guard_version,
        "canonical_pair": result.canonical_pair,
        "candidate_identity_sha256": result.candidate_identity_sha256,
        "claim_won": result.claim_won,
        "publication_success_recorded": result.publication_success_recorded,
        "result_code": result.result_code,
        "reset_decision": (
            result.reset_decision.to_mapping()
            if result.reset_decision is not None
            else None
        ),
        "store_revision_before": result.store_revision_before,
        "store_revision_after": result.store_revision_after,
        "document_sha256_before": result.document_sha256_before,
        "document_sha256_after": result.document_sha256_after,
    }


@dataclass(frozen=True, slots=True)
class E4PublicationIdempotencyResultV1:
    guard_version: str
    canonical_pair: str
    candidate_identity_sha256: str
    claim_won: bool
    publication_success_recorded: bool
    result_code: str
    reset_decision: E4LifecycleResetDecisionV1 | None
    store_revision_before: int | None
    store_revision_after: int
    document_sha256_before: str | None
    document_sha256_after: str
    result_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.guard_version) is str)
            _require(
                self.guard_version
                == E4_PUBLICATION_IDEMPOTENCY_GUARD_VERSION
            )
            _require(type(self.canonical_pair) is str)
            _require(normalize_pair(self.canonical_pair) == self.canonical_pair)
            _require(type(self.candidate_identity_sha256) is str)
            _require(
                _SHA256_PATTERN.fullmatch(self.candidate_identity_sha256)
                is not None
            )
            _require(type(self.claim_won) is bool)
            _require(type(self.publication_success_recorded) is bool)
            _require(type(self.result_code) is str)
            _require(self.result_code in PUBLICATION_IDEMPOTENCY_RESULT_CODES)
            if self.reset_decision is not None:
                _reset(self.reset_decision)
            if self.store_revision_before is not None:
                _require(type(self.store_revision_before) is int)
                _require(self.store_revision_before > 0)
            _require(type(self.store_revision_after) is int)
            _require(self.store_revision_after > 0)
            if self.document_sha256_before is not None:
                _require(type(self.document_sha256_before) is str)
                _require(
                    _SHA256_PATTERN.fullmatch(self.document_sha256_before)
                    is not None
                )
            _require(type(self.document_sha256_after) is str)
            _require(
                _SHA256_PATTERN.fullmatch(self.document_sha256_after)
                is not None
            )
            if self.result_code == CLAIM_WON_INITIAL_THESIS:
                _require(self.claim_won is True)
                _require(self.publication_success_recorded is False)
                _require(self.reset_decision is None)
                _require(self.store_revision_before is None)
                _require(self.document_sha256_before is None)
            elif self.result_code == CLAIM_WON_RESET_THESIS:
                _require(self.claim_won is True)
                _require(self.publication_success_recorded is False)
                decision = _reset(self.reset_decision)
                _require(decision.publication_allowed is True)
                _require(type(self.store_revision_before) is int)
                _require(
                    self.store_revision_after > self.store_revision_before
                )
            elif self.result_code == CLAIM_SUPPRESSED_EXISTING_THESIS:
                _require(self.claim_won is False)
                _require(self.publication_success_recorded is False)
                _require(self.reset_decision is None)
                _require(self.store_revision_before == self.store_revision_after)
                _require(
                    self.document_sha256_before
                    == self.document_sha256_after
                )
            elif self.result_code == CLAIM_SUPPRESSED_BY_RESET_POLICY:
                _require(self.claim_won is False)
                _require(self.publication_success_recorded is False)
                decision = _reset(self.reset_decision)
                _require(decision.publication_allowed is False)
                _require(self.store_revision_before == self.store_revision_after)
                _require(
                    self.document_sha256_before
                    == self.document_sha256_after
                )
            elif self.result_code == PUBLICATION_SUCCESS_RECORDED:
                _require(self.claim_won is False)
                _require(self.publication_success_recorded is True)
                _require(self.reset_decision is None)
                _require(type(self.store_revision_before) is int)
                _require(
                    self.store_revision_after == self.store_revision_before + 1
                )
                _require(
                    self.document_sha256_before
                    != self.document_sha256_after
                )
            else:
                _require(
                    self.result_code
                    == PUBLICATION_SUCCESS_ALREADY_RECORDED
                )
                _require(self.claim_won is False)
                _require(self.publication_success_recorded is True)
                _require(self.reset_decision is None)
                _require(self.store_revision_before == self.store_revision_after)
                _require(
                    self.document_sha256_before
                    == self.document_sha256_after
                )
            _require(type(self.result_sha256) is str)
            _require(_SHA256_PATTERN.fullmatch(self.result_sha256) is not None)
            _require(self.result_sha256 == _hash_mapping(_result_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_result_preimage(self),
            "result_sha256": self.result_sha256,
        }

    def canonical_result_json(self) -> str:
        return _canonical_json(_result_preimage(self))


def _build_result(
    *,
    canonical_pair: str,
    candidate_identity_sha256: str,
    claim_won: bool,
    publication_success_recorded: bool,
    result_code: str,
    reset_decision: E4LifecycleResetDecisionV1 | None,
    store_revision_before: int | None,
    store_revision_after: int,
    document_sha256_before: str | None,
    document_sha256_after: str,
) -> E4PublicationIdempotencyResultV1:
    mapping: dict[str, object] = {
        "guard_version": E4_PUBLICATION_IDEMPOTENCY_GUARD_VERSION,
        "canonical_pair": canonical_pair,
        "candidate_identity_sha256": candidate_identity_sha256,
        "claim_won": claim_won,
        "publication_success_recorded": publication_success_recorded,
        "result_code": result_code,
        "reset_decision": reset_decision,
        "store_revision_before": store_revision_before,
        "store_revision_after": store_revision_after,
        "document_sha256_before": document_sha256_before,
        "document_sha256_after": document_sha256_after,
    }
    preimage = {
        **mapping,
        "reset_decision": (
            reset_decision.to_mapping()
            if reset_decision is not None
            else None
        ),
    }
    return E4PublicationIdempotencyResultV1(
        **mapping,
        result_sha256=_hash_mapping(preimage),
    )


def claim_e4_publication_intent_v1(
    *,
    authorized_store_root: Path,
    store_path: Path,
    candidate_fingerprint: E4ThesisFingerprintV1,
    price_exited_zone: bool,
) -> E4PublicationIdempotencyResultV1:
    try:
        candidate = _fingerprint(candidate_fingerprint)
        _require(type(price_exited_zone) is bool)
        paths = _authorize_store_paths_v1(
            authorized_store_root=authorized_store_root,
            store_path=store_path,
        )
        with _locked_store_v1(paths, exclusive=True):
            current = _load_document_locked_v1(paths)
            if current is None:
                _require(price_exited_zone is False)
                history = create_e4_thesis_history_v1(
                    fingerprint=candidate,
                    initial_state="ACTIONABLE",
                )
                history = append_e4_thesis_history_event_v1(
                    history=history,
                    fingerprint=candidate,
                    state="PUBLISHED_PENDING_ENTRY",
                    publication_succeeded=False,
                    price_exited_zone=False,
                    reset_decision=None,
                )
                committed = _write_history_locked_v1(paths, history)
                return _build_result(
                    canonical_pair=candidate.canonical_pair,
                    candidate_identity_sha256=candidate.identity_sha256,
                    claim_won=True,
                    publication_success_recorded=False,
                    result_code=CLAIM_WON_INITIAL_THESIS,
                    reset_decision=None,
                    store_revision_before=None,
                    store_revision_after=committed.store_revision,
                    document_sha256_before=None,
                    document_sha256_after=committed.document_sha256,
                )

            _require(current.canonical_pair == candidate.canonical_pair)
            history = current.history
            prior_fingerprint = history.events[-1].fingerprint
            decision = adjudicate_e4_lifecycle_reset_v1(
                candidate_fingerprint=candidate,
                prior_fingerprint=prior_fingerprint,
                prior_state=history.current_state,
                price_exited_zone=history.current_price_exited_zone,
            )
            if candidate.identity_sha256 == history.current_identity_sha256:
                return _build_result(
                    canonical_pair=current.canonical_pair,
                    candidate_identity_sha256=candidate.identity_sha256,
                    claim_won=False,
                    publication_success_recorded=False,
                    result_code=CLAIM_SUPPRESSED_EXISTING_THESIS,
                    reset_decision=None,
                    store_revision_before=current.store_revision,
                    store_revision_after=current.store_revision,
                    document_sha256_before=current.document_sha256,
                    document_sha256_after=current.document_sha256,
                )
            _require(price_exited_zone is history.current_price_exited_zone)
            if not decision.publication_allowed:
                return _build_result(
                    canonical_pair=current.canonical_pair,
                    candidate_identity_sha256=candidate.identity_sha256,
                    claim_won=False,
                    publication_success_recorded=False,
                    result_code=CLAIM_SUPPRESSED_BY_RESET_POLICY,
                    reset_decision=decision,
                    store_revision_before=current.store_revision,
                    store_revision_after=current.store_revision,
                    document_sha256_before=current.document_sha256,
                    document_sha256_after=current.document_sha256,
                )
            successor = append_e4_thesis_history_event_v1(
                history=history,
                fingerprint=candidate,
                state="ACTIONABLE",
                publication_succeeded=False,
                price_exited_zone=False,
                reset_decision=decision,
            )
            successor = append_e4_thesis_history_event_v1(
                history=successor,
                fingerprint=candidate,
                state="PUBLISHED_PENDING_ENTRY",
                publication_succeeded=False,
                price_exited_zone=False,
                reset_decision=None,
            )
            committed = _write_history_locked_v1(paths, successor)
            return _build_result(
                canonical_pair=current.canonical_pair,
                candidate_identity_sha256=candidate.identity_sha256,
                claim_won=True,
                publication_success_recorded=False,
                result_code=CLAIM_WON_RESET_THESIS,
                reset_decision=decision,
                store_revision_before=current.store_revision,
                store_revision_after=committed.store_revision,
                document_sha256_before=current.document_sha256,
                document_sha256_after=committed.document_sha256,
            )
    except Exception:
        _fail()


def record_e4_publication_success_v1(
    *,
    authorized_store_root: Path,
    store_path: Path,
    candidate_identity_sha256: str,
) -> E4PublicationIdempotencyResultV1:
    try:
        _require(type(candidate_identity_sha256) is str)
        _require(
            _SHA256_PATTERN.fullmatch(candidate_identity_sha256) is not None
        )
        paths = _authorize_store_paths_v1(
            authorized_store_root=authorized_store_root,
            store_path=store_path,
        )
        with _locked_store_v1(paths, exclusive=True):
            current = _load_document_locked_v1(paths)
            _require(current is not None)
            history = current.history
            _require(
                candidate_identity_sha256
                == history.current_identity_sha256
            )
            _require(history.current_state == "PUBLISHED_PENDING_ENTRY")
            if history.current_publication_succeeded:
                return _build_result(
                    canonical_pair=current.canonical_pair,
                    candidate_identity_sha256=candidate_identity_sha256,
                    claim_won=False,
                    publication_success_recorded=True,
                    result_code=PUBLICATION_SUCCESS_ALREADY_RECORDED,
                    reset_decision=None,
                    store_revision_before=current.store_revision,
                    store_revision_after=current.store_revision,
                    document_sha256_before=current.document_sha256,
                    document_sha256_after=current.document_sha256,
                )
            updated = append_e4_thesis_history_event_v1(
                history=history,
                fingerprint=history.events[-1].fingerprint,
                state="PUBLISHED_PENDING_ENTRY",
                publication_succeeded=True,
                price_exited_zone=history.current_price_exited_zone,
                reset_decision=None,
            )
            committed = _write_history_locked_v1(paths, updated)
            return _build_result(
                canonical_pair=current.canonical_pair,
                candidate_identity_sha256=candidate_identity_sha256,
                claim_won=False,
                publication_success_recorded=True,
                result_code=PUBLICATION_SUCCESS_RECORDED,
                reset_decision=None,
                store_revision_before=current.store_revision,
                store_revision_after=committed.store_revision,
                document_sha256_before=current.document_sha256,
                document_sha256_after=committed.document_sha256,
            )
    except Exception:
        _fail()
