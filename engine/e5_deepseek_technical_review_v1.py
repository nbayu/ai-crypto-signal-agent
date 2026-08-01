"""Pure DeepSeek structured technical-review and D6 adjudication contracts."""

from __future__ import annotations

from dataclasses import dataclass, fields
from hashlib import sha256
import json
import re
from typing import Final, Mapping
import unicodedata

from engine.e5_technical_review_payload_v1 import (
    E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    E5TechnicalReviewPayloadV1,
    get_owner_frozen_e5_provider_model_price_binding_v3,
)


E5_DEEPSEEK_STRUCTURED_REVIEW_VERSION: Final = (
    "e5-deepseek-structured-review-v1"
)
E5_DEEPSEEK_TECHNICAL_REVIEW_POLICY_VERSION: Final = (
    "e5-deepseek-technical-review-policy-v1"
)
E5_DEEPSEEK_ADJUDICATION_VERSION: Final = "e5-deepseek-adjudication-v1"

CLEAR: Final = "CLEAR"
CAUTION: Final = "CAUTION"
HOLD: Final = "HOLD"
DEEPSEEK_REVIEW_DECISIONS: Final = (CLEAR, CAUTION, HOLD)

CLEAR_NO_MATERIAL_CONFLICT: Final = "CLEAR_NO_MATERIAL_CONFLICT"
CAUTION_LIMITED_EVIDENCE: Final = "CAUTION_LIMITED_EVIDENCE"
CAUTION_NONCRITICAL_CONTRADICTION: Final = (
    "CAUTION_NONCRITICAL_CONTRADICTION"
)
CAUTION_EVIDENCE_QUALITY_CONCERN: Final = (
    "CAUTION_EVIDENCE_QUALITY_CONCERN"
)
HOLD_MATERIAL_CONTRADICTION: Final = "HOLD_MATERIAL_CONTRADICTION"
HOLD_CRITICAL_AMBIGUITY: Final = "HOLD_CRITICAL_AMBIGUITY"
HOLD_CRITICAL_EVIDENCE_DEFICIT: Final = "HOLD_CRITICAL_EVIDENCE_DEFICIT"
HOLD_CRITICAL_MATERIAL_RISK: Final = "HOLD_CRITICAL_MATERIAL_RISK"

DEEPSEEK_REASON_CODES: Final = (
    CLEAR_NO_MATERIAL_CONFLICT,
    CAUTION_LIMITED_EVIDENCE,
    CAUTION_NONCRITICAL_CONTRADICTION,
    CAUTION_EVIDENCE_QUALITY_CONCERN,
    HOLD_MATERIAL_CONTRADICTION,
    HOLD_CRITICAL_AMBIGUITY,
    HOLD_CRITICAL_EVIDENCE_DEFICIT,
    HOLD_CRITICAL_MATERIAL_RISK,
)

CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE: Final = (
    "CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE"
)
CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE: Final = (
    "CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE"
)
STOP_DETERMINISTIC_HARD_GATE: Final = "STOP_DETERMINISTIC_HARD_GATE"
STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR: Final = (
    "STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR"
)
STOP_DEEPSEEK_HOLD: Final = "STOP_DEEPSEEK_HOLD"

DEEPSEEK_ADJUDICATION_OUTCOME_CODES: Final = (
    CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE,
    CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE,
    STOP_DETERMINISTIC_HARD_GATE,
    STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR,
    STOP_DEEPSEEK_HOLD,
)

_ERROR: Final = "invalid E5 DeepSeek technical review"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_REVIEW_MAPPING_KEYS: Final = frozenset(
    (
        "review_version",
        "payload_sha256",
        "model_id",
        "decision",
        "reason_codes",
        "concise_reason",
        "reviewed_evidence_fields",
        "review_sha256",
    )
)
_CAUTION_CODES: Final = DEEPSEEK_REASON_CODES[1:4]
_HOLD_CODES: Final = DEEPSEEK_REASON_CODES[4:]


def _fail() -> None:
    raise ValueError(_ERROR) from None


def _require(condition: bool) -> None:
    if not condition:
        _fail()


def _canonical_json(mapping: Mapping[str, object]) -> str:
    try:
        return json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except Exception:
        _fail()


def _hash_mapping(mapping: Mapping[str, object]) -> str:
    return sha256(_canonical_json(mapping).encode("utf-8")).hexdigest()


def _valid_sha256(value: object) -> bool:
    return type(value) is str and _SHA256_PATTERN.fullmatch(value) is not None


def _validate_payload(value: object) -> E5TechnicalReviewPayloadV1:
    _require(type(value) is E5TechnicalReviewPayloadV1)
    value.__post_init__()
    binding = get_owner_frozen_e5_provider_model_price_binding_v3()
    _require(value.provider_binding_sha256 == binding.binding_sha256)
    return value


def _validate_decision(value: object) -> str:
    _require(type(value) is str and value in DEEPSEEK_REVIEW_DECISIONS)
    return value


def _validate_reason_codes(
    decision: object,
    value: object,
) -> tuple[str, ...]:
    canonical_decision = _validate_decision(decision)
    _require(type(value) is tuple and bool(value))
    _require(all(type(code) is str for code in value))
    _require(len(set(value)) == len(value))
    if canonical_decision == CLEAR:
        _require(value == (CLEAR_NO_MATERIAL_CONFLICT,))
    elif canonical_decision == CAUTION:
        _require(all(code in _CAUTION_CODES for code in value))
        _require(value == tuple(code for code in _CAUTION_CODES if code in value))
    else:
        _require(all(code in _HOLD_CODES for code in value))
        _require(value == tuple(code for code in _HOLD_CODES if code in value))
    return value


def _validate_concise_reason(value: object) -> str:
    _require(type(value) is str)
    _require(1 <= len(value) <= 280)
    _require(value == value.strip())
    _require(len(value.splitlines()) == 1)
    _require("\x00" not in value and "\r" not in value)
    _require("\n" not in value and "\t" not in value)
    _require(all(unicodedata.category(character) != "Cc" for character in value))
    _require(unicodedata.normalize("NFC", value) == value)
    return value


def _validate_reviewed_fields(value: object) -> tuple[str, ...]:
    _require(type(value) is tuple and bool(value))
    _require(all(type(field) is str for field in value))
    _require(len(set(value)) == len(value))
    _require(all(field in E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS for field in value))
    expected = tuple(
        field for field in E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS if field in value
    )
    _require(value == expected)
    return value


def _review_preimage(
    review: "E5DeepSeekStructuredReviewV1",
) -> dict[str, object]:
    return {
        "review_version": review.review_version,
        "payload_sha256": review.payload_sha256,
        "model_id": review.model_id,
        "decision": review.decision,
        "reason_codes": list(review.reason_codes),
        "concise_reason": review.concise_reason,
        "reviewed_evidence_fields": list(review.reviewed_evidence_fields),
    }


@dataclass(frozen=True, slots=True)
class E5DeepSeekStructuredReviewV1:
    review_version: str
    payload_sha256: str
    model_id: str
    decision: str
    reason_codes: tuple[str, ...]
    concise_reason: str
    reviewed_evidence_fields: tuple[str, ...]
    review_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.review_version) is str)
            _require(
                self.review_version == E5_DEEPSEEK_STRUCTURED_REVIEW_VERSION
            )
            _require(_valid_sha256(self.payload_sha256))
            binding = get_owner_frozen_e5_provider_model_price_binding_v3()
            _require(type(self.model_id) is str)
            _require(self.model_id == binding.deepseek_model_id)
            _require(not self.model_id.casefold().endswith("latest"))
            _validate_reason_codes(self.decision, self.reason_codes)
            _validate_concise_reason(self.concise_reason)
            _validate_reviewed_fields(self.reviewed_evidence_fields)
            _require(_valid_sha256(self.review_sha256))
            _require(self.review_sha256 == _hash_mapping(_review_preimage(self)))
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_review_preimage(self),
            "review_sha256": self.review_sha256,
        }

    def canonical_review_json(self) -> str:
        return _canonical_json(_review_preimage(self))


def build_e5_deepseek_structured_review_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    model_id: str,
    decision: str,
    reason_codes: tuple[str, ...],
    concise_reason: str,
    reviewed_evidence_fields: tuple[str, ...],
) -> E5DeepSeekStructuredReviewV1:
    try:
        verified_payload = _validate_payload(payload)
        binding = get_owner_frozen_e5_provider_model_price_binding_v3()
        _require(type(model_id) is str and model_id == binding.deepseek_model_id)
        data: dict[str, object] = {
            "review_version": E5_DEEPSEEK_STRUCTURED_REVIEW_VERSION,
            "payload_sha256": verified_payload.payload_sha256,
            "model_id": model_id,
            "decision": decision,
            "reason_codes": reason_codes,
            "concise_reason": concise_reason,
            "reviewed_evidence_fields": reviewed_evidence_fields,
        }
        temporary = object.__new__(E5DeepSeekStructuredReviewV1)
        for name, value in data.items():
            object.__setattr__(temporary, name, value)
        return E5DeepSeekStructuredReviewV1(
            **data,
            review_sha256=_hash_mapping(_review_preimage(temporary)),
        )
    except Exception:
        _fail()


def reconstruct_e5_deepseek_structured_review_v1(
    mapping: Mapping[str, object],
) -> E5DeepSeekStructuredReviewV1:
    try:
        _require(type(mapping) is dict)
        _require(frozenset(mapping) == _REVIEW_MAPPING_KEYS)
        _require(type(mapping["reason_codes"]) is list)
        _require(type(mapping["reviewed_evidence_fields"]) is list)
        return E5DeepSeekStructuredReviewV1(
            review_version=mapping["review_version"],
            payload_sha256=mapping["payload_sha256"],
            model_id=mapping["model_id"],
            decision=mapping["decision"],
            reason_codes=tuple(mapping["reason_codes"]),
            concise_reason=mapping["concise_reason"],
            reviewed_evidence_fields=tuple(mapping["reviewed_evidence_fields"]),
            review_sha256=mapping["review_sha256"],
        )
    except Exception:
        _fail()


def _adjudication_preimage(
    result: "E5DeepSeekTechnicalReviewAdjudicationV1",
) -> dict[str, object]:
    return {
        field.name: (
            list(getattr(result, field.name))
            if field.name == "reason_codes"
            else getattr(result, field.name)
        )
        for field in fields(E5DeepSeekTechnicalReviewAdjudicationV1)
        if field.name != "adjudication_sha256"
    }


def _expected_effects(
    *,
    review_decision: str,
    deterministic_hard_gates_passed: bool,
    final_score: int,
    mode_score_floor: int,
) -> tuple[bool, bool, bool, bool, str]:
    if review_decision == HOLD:
        return False, True, True, True, STOP_DEEPSEEK_HOLD
    if deterministic_hard_gates_passed is False:
        return False, True, False, False, STOP_DETERMINISTIC_HARD_GATE
    if review_decision == CLEAR:
        return True, False, False, False, (
            CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE
        )
    if final_score > mode_score_floor:
        return True, False, False, False, (
            CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE
        )
    return False, True, False, False, STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR


@dataclass(frozen=True, slots=True)
class E5DeepSeekTechnicalReviewAdjudicationV1:
    adjudication_version: str
    policy_version: str
    payload_sha256: str
    model_id: str
    review_decision: str
    reason_codes: tuple[str, ...]
    review_sha256: str
    pre_review_score: int
    score_penalty: int
    final_score: int
    mode_score_floor: int
    deterministic_hard_gates_passed: bool
    may_continue_to_python_final_gate: bool
    publication_blocked: bool
    hold_blocks_current_trigger_generation: bool
    hold_retains_armed_when_lifecycle_valid: bool
    outcome_code: str
    adjudication_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.adjudication_version) is str)
            _require(self.adjudication_version == E5_DEEPSEEK_ADJUDICATION_VERSION)
            _require(type(self.policy_version) is str)
            _require(
                self.policy_version
                == E5_DEEPSEEK_TECHNICAL_REVIEW_POLICY_VERSION
            )
            _require(_valid_sha256(self.payload_sha256))
            binding = get_owner_frozen_e5_provider_model_price_binding_v3()
            _require(type(self.model_id) is str)
            _require(self.model_id == binding.deepseek_model_id)
            _validate_reason_codes(self.review_decision, self.reason_codes)
            _require(_valid_sha256(self.review_sha256))
            for value in (
                self.pre_review_score,
                self.score_penalty,
                self.final_score,
                self.mode_score_floor,
            ):
                _require(type(value) is int)
            expected_penalty = -3 if self.review_decision == CAUTION else 0
            _require(self.score_penalty == expected_penalty)
            _require(self.final_score == self.pre_review_score + self.score_penalty)
            _require(type(self.deterministic_hard_gates_passed) is bool)
            for value in (
                self.may_continue_to_python_final_gate,
                self.publication_blocked,
                self.hold_blocks_current_trigger_generation,
                self.hold_retains_armed_when_lifecycle_valid,
            ):
                _require(type(value) is bool)
            expected = _expected_effects(
                review_decision=self.review_decision,
                deterministic_hard_gates_passed=(
                    self.deterministic_hard_gates_passed
                ),
                final_score=self.final_score,
                mode_score_floor=self.mode_score_floor,
            )
            actual = (
                self.may_continue_to_python_final_gate,
                self.publication_blocked,
                self.hold_blocks_current_trigger_generation,
                self.hold_retains_armed_when_lifecycle_valid,
                self.outcome_code,
            )
            _require(actual == expected)
            _require(self.outcome_code in DEEPSEEK_ADJUDICATION_OUTCOME_CODES)
            _require(_valid_sha256(self.adjudication_sha256))
            _require(
                self.adjudication_sha256
                == _hash_mapping(_adjudication_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_adjudication_preimage(self),
            "adjudication_sha256": self.adjudication_sha256,
        }

    def canonical_adjudication_json(self) -> str:
        return _canonical_json(_adjudication_preimage(self))


def adjudicate_e5_deepseek_technical_review_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    review: E5DeepSeekStructuredReviewV1,
    deterministic_hard_gates_passed: bool,
    pre_review_score: int,
    mode_score_floor: int,
) -> E5DeepSeekTechnicalReviewAdjudicationV1:
    try:
        verified_payload = _validate_payload(payload)
        _require(type(review) is E5DeepSeekStructuredReviewV1)
        review.__post_init__()
        binding = get_owner_frozen_e5_provider_model_price_binding_v3()
        _require(review.payload_sha256 == verified_payload.payload_sha256)
        _require(review.model_id == binding.deepseek_model_id)
        _require(type(deterministic_hard_gates_passed) is bool)
        _require(type(pre_review_score) is int)
        _require(type(mode_score_floor) is int)
        score_penalty = -3 if review.decision == CAUTION else 0
        final_score = pre_review_score + score_penalty
        effects = _expected_effects(
            review_decision=review.decision,
            deterministic_hard_gates_passed=deterministic_hard_gates_passed,
            final_score=final_score,
            mode_score_floor=mode_score_floor,
        )
        data: dict[str, object] = {
            "adjudication_version": E5_DEEPSEEK_ADJUDICATION_VERSION,
            "policy_version": E5_DEEPSEEK_TECHNICAL_REVIEW_POLICY_VERSION,
            "payload_sha256": verified_payload.payload_sha256,
            "model_id": binding.deepseek_model_id,
            "review_decision": review.decision,
            "reason_codes": review.reason_codes,
            "review_sha256": review.review_sha256,
            "pre_review_score": pre_review_score,
            "score_penalty": score_penalty,
            "final_score": final_score,
            "mode_score_floor": mode_score_floor,
            "deterministic_hard_gates_passed": deterministic_hard_gates_passed,
            "may_continue_to_python_final_gate": effects[0],
            "publication_blocked": effects[1],
            "hold_blocks_current_trigger_generation": effects[2],
            "hold_retains_armed_when_lifecycle_valid": effects[3],
            "outcome_code": effects[4],
        }
        temporary = object.__new__(E5DeepSeekTechnicalReviewAdjudicationV1)
        for name, value in data.items():
            object.__setattr__(temporary, name, value)
        return E5DeepSeekTechnicalReviewAdjudicationV1(
            **data,
            adjudication_sha256=_hash_mapping(
                _adjudication_preimage(temporary)
            ),
        )
    except Exception:
        _fail()


__all__ = (
    "E5_DEEPSEEK_STRUCTURED_REVIEW_VERSION",
    "E5_DEEPSEEK_TECHNICAL_REVIEW_POLICY_VERSION",
    "E5_DEEPSEEK_ADJUDICATION_VERSION",
    "CLEAR",
    "CAUTION",
    "HOLD",
    "DEEPSEEK_REVIEW_DECISIONS",
    "CLEAR_NO_MATERIAL_CONFLICT",
    "CAUTION_LIMITED_EVIDENCE",
    "CAUTION_NONCRITICAL_CONTRADICTION",
    "CAUTION_EVIDENCE_QUALITY_CONCERN",
    "HOLD_MATERIAL_CONTRADICTION",
    "HOLD_CRITICAL_AMBIGUITY",
    "HOLD_CRITICAL_EVIDENCE_DEFICIT",
    "HOLD_CRITICAL_MATERIAL_RISK",
    "DEEPSEEK_REASON_CODES",
    "CONTINUE_CLEAR_TO_PYTHON_FINAL_GATE",
    "CONTINUE_CAUTION_TO_PYTHON_FINAL_GATE",
    "STOP_DETERMINISTIC_HARD_GATE",
    "STOP_CAUTION_AT_OR_BELOW_MODE_FLOOR",
    "STOP_DEEPSEEK_HOLD",
    "DEEPSEEK_ADJUDICATION_OUTCOME_CODES",
    "E5DeepSeekStructuredReviewV1",
    "E5DeepSeekTechnicalReviewAdjudicationV1",
    "build_e5_deepseek_structured_review_v1",
    "reconstruct_e5_deepseek_structured_review_v1",
    "adjudicate_e5_deepseek_technical_review_v1",
)
