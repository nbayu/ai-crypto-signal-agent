"""Pure immutable E5 technical-review payload and token preflight contracts."""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from hashlib import sha256
import json
import re
from typing import Final, Mapping

from engine.canonical_pair_v1 import normalize_pair
from engine.e3_actionable_admission_v1 import E3ActionableAdmissionResultV1
from engine.e4_duplicate_protection_composition_v1 import (
    E4DuplicateProtectionCompositionResultV1,
)
from engine.e4_thesis_fingerprint_v1 import (
    E4ThesisFingerprintV1,
    build_e4_thesis_fingerprint,
)
from engine.e4_thesis_history_v1 import E4ThesisHistoryV1
from engine.mode_profile_v1 import ModeProfileV1, get_mode_profile
from engine.mode_scan_execution_evidence_v1 import (
    ModeOiExecutionEvidenceV1,
    ModeScanExecutionResultV1,
    ModeTimeframeExecutionEvidenceV1,
)
from engine.news_event_contract_v1 import NormalizedNewsEventV1
from engine.news_risk_object_v1 import NewsRiskObjectV1
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)


E5_PROVIDER_MODEL_PRICE_BINDING_VERSION: Final = (
    "e5-provider-model-price-binding-v1"
)
E5_PROVIDER_MODEL_PRICE_BINDING_V2_VERSION: Final = (
    "e5-provider-model-price-binding-v2"
)
E5_TECHNICAL_REVIEW_PAYLOAD_VERSION: Final = (
    "e5-technical-review-payload-v1"
)
E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_VERSION: Final = (
    "e5-technical-review-token-preflight-v1"
)

E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS: Final = (
    "mode",
    "relevant_timeframes",
    "executable_price",
    "exchange_timestamp",
    "golden_zone",
    "anchors",
    "stop_geometry",
    "target_geometry",
    "net_rr",
    "trigger_type",
    "trigger_age",
    "lifecycle_state",
    "thesis_fingerprint",
    "prior_publication_identity",
    "prior_history_identity",
    "liquidity_evidence",
    "volume_evidence",
    "open_interest_evidence",
    "news_and_contradiction_quality",
)

PASS_TOKEN_BUDGET: Final = "PASS_TOKEN_BUDGET"
HOLD_INPUT_TOKEN_LIMIT: Final = "HOLD_INPUT_TOKEN_LIMIT"
HOLD_OUTPUT_TOKEN_LIMIT: Final = "HOLD_OUTPUT_TOKEN_LIMIT"
E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_DECISION_CODES: Final = (
    PASS_TOKEN_BUDGET,
    HOLD_INPUT_TOKEN_LIMIT,
    HOLD_OUTPUT_TOKEN_LIMIT,
)

_ERROR: Final = "invalid E5 technical review payload"
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_MODES: Final = ("SWING", "INTRADAY", "SCALP")
_TIMEFRAMES: Final = ("1w", "1d", "4h", "1h", "15m", "5m", "3m")

_FROZEN_BINDING_VALUES: Final = {
    "binding_version": E5_PROVIDER_MODEL_PRICE_BINDING_VERSION,
    "deepseek_model_id": "deepseek-v4-pro",
    "deepseek_input_hard_limit_tokens": 4000,
    "deepseek_output_hard_limit_tokens": 500,
    "deepseek_provider_attempts": 1,
    "deepseek_retry_count": 0,
    "deepseek_cache_hit_input_usd_per_mtok": "0.003625",
    "deepseek_cache_miss_input_usd_per_mtok": "0.435",
    "deepseek_output_usd_per_mtok": "0.87",
    "deepseek_pre_ga_unpinned_risk_accepted": True,
    "claude_l1_model_id": "claude-sonnet-5",
    "claude_l1_input_hard_limit_tokens": 4000,
    "claude_l1_output_hard_limit_tokens": 500,
    "claude_l1_timeout_seconds": 10,
    "claude_l1_provider_attempts": 1,
    "claude_l1_retry_count": 0,
    "claude_l1_base_input_usd_per_mtok": "3",
    "claude_l1_output_usd_per_mtok": "15",
    "claude_l1_max_cost_micro_usd": 19500,
    "claude_l2_model_id": "claude-fable-5",
    "claude_l2_input_hard_limit_tokens": 6000,
    "claude_l2_output_hard_limit_tokens": 800,
    "claude_l2_timeout_seconds": 20,
    "claude_l2_provider_attempts": 1,
    "claude_l2_retry_count": 0,
    "claude_l2_base_input_usd_per_mtok": "10",
    "claude_l2_output_usd_per_mtok": "50",
    "claude_l2_max_cost_micro_usd": 100000,
    "shared_l1_l2_daily_logical_review_ceiling": 9,
    "l2_daily_logical_review_ceiling": 3,
    "maximum_daily_cost_micro_usd": 417000,
    "claude_mythos_limited_availability_accepted": False,
    "latest_alias_allowed": False,
    "cross_provider_substitution_allowed": False,
    "malformed_response_prompt_repair_allowed": False,
    "stale_result_reuse_allowed": False,
    "same_invocation_retry_allowed": False,
    "price_artifact_maximum_age_days": 30,
    "deepseek_models_artifact_sha256": (
        "cc58ecae320965aa248bfe54ecf2fb0c7cbb64b44692f96f55089599a81278f5"
    ),
    "deepseek_pricing_artifact_sha256": (
        "4c0ad750134543b515a8c7435f2bdda0f7b0f04582bf7546c0045cab47ef245e"
    ),
    "deepseek_updates_artifact_sha256": (
        "144a324a536da41b142d134112905669282a893eb6af081920373d672d5fbfc7"
    ),
    "claude_models_artifact_sha256": (
        "4145151ccbda647f67e4a8ae307559bf6040e3dd5cb6111569076e738c0dbfa8"
    ),
    "claude_pricing_artifact_sha256": (
        "79d551dd56ebd7caec99833c3740f2c93cb58a64f35dbf87947bf80de11ae78a"
    ),
    "claude_deprecations_artifact_sha256": (
        "7c7ce500f1d2a3af8963b40181bf34b54f3e28ed1f73c0650f39bcae4ff9367b"
    ),
}

_FROZEN_BINDING_V2_VALUES: Final = {
    **_FROZEN_BINDING_VALUES,
    "binding_version": E5_PROVIDER_MODEL_PRICE_BINDING_V2_VERSION,
    "claude_l1_model_id": "claude-opus-5",
    "claude_l1_base_input_usd_per_mtok": "5",
    "claude_l1_output_usd_per_mtok": "25",
    "claude_l1_max_cost_micro_usd": 32500,
    "maximum_daily_cost_micro_usd": 495000,
}

_PAYLOAD_MAPPING_KEYS: Final = {
    "executable_price": (
        "admission_sha256",
        "executable_price_source",
        "executable_price_tick",
        "snapshot_sha256",
    ),
    "exchange_timestamp": (
        "exchange_timestamp",
        "quote_generation_id",
        "snapshot_sha256",
        "venue",
    ),
    "golden_zone": (
        "geometry_sha256",
        "high_tick",
        "low_tick",
    ),
    "anchors": (
        "anchor_high_at",
        "anchor_high_tick",
        "anchor_low_at",
        "anchor_low_tick",
    ),
    "stop_geometry": (
        "risk_distance_ticks",
        "stop_loss_tick",
        "worst_entry_tick",
    ),
    "target_geometry": (
        "targets_sha256",
        "tp1",
        "tp2",
    ),
    "net_rr": (
        "tp1_rr_denominator",
        "tp1_rr_numerator",
        "tp2_rr_denominator",
        "tp2_rr_numerator",
    ),
    "trigger_age": (
        "evaluation_timestamp",
        "maximum_trigger_age_seconds",
        "trigger_age_seconds",
        "trigger_candle_close_at",
        "trigger_evidence_sha256",
        "trigger_fresh",
    ),
    "lifecycle_state": (
        "lifecycle_sha256",
        "resulting_state",
    ),
    "thesis_fingerprint": (
        "fingerprint_version",
        "identity",
        "identity_sha256",
    ),
    "prior_publication_identity": (
        "current_identity_sha256",
        "current_publication_succeeded",
        "current_state",
        "latest_event_sha256",
    ),
    "prior_history_identity": (
        "fingerprint_history",
        "history_sha256",
        "revision",
    ),
    "liquidity_evidence": (
        "targets_sha256",
        "tp1_destination_id",
        "tp1_destination_kind",
        "tp2_destination_id",
        "tp2_destination_kind",
    ),
    "volume_evidence": (
        "evaluator_payload_sha256",
        "mode_execution_sha256",
        "volume_ratio",
        "volume_v2_status",
    ),
    "open_interest_evidence": (
        "evidence_sha256",
        "newest_age_seconds",
        "newest_close_at",
        "observation_count",
        "observations",
        "observations_sha256",
        "observed_at",
        "period",
    ),
    "news_and_contradiction_quality": (
        "evidence_refs",
        "event_snapshot_ids",
        "event_version_ids",
        "final_contradiction_state",
        "final_evidence_state",
        "final_material_risk_state",
        "final_source_state",
        "news_risk_object_id",
        "reason_codes",
        "risk_classification",
    ),
}


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


def _canonical_decimal(value: object) -> str:
    _require(type(value) is str and bool(value))
    _require("e" not in value.casefold() and not value.startswith("+"))
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        _fail()
    _require(parsed.is_finite() and parsed >= 0)
    canonical = format(parsed, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    _require(canonical == value)
    return value


def _maximum_cost_micro_usd(
    input_tokens: int,
    input_price: str,
    output_tokens: int,
    output_price: str,
) -> int:
    value = (
        Decimal(input_tokens) * Decimal(input_price)
        + Decimal(output_tokens) * Decimal(output_price)
    )
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def _binding_preimage(
    binding: object,
) -> dict[str, object]:
    return {
        field.name: getattr(binding, field.name)
        for field in fields(binding)
        if field.name != "binding_sha256"
    }


def _validate_frozen_binding(
    binding: object,
    frozen_values: Mapping[str, object],
) -> None:
    for name, expected in frozen_values.items():
        actual = getattr(binding, name)
        _require(type(actual) is type(expected) and actual == expected)
    for name in (
        "deepseek_cache_hit_input_usd_per_mtok",
        "deepseek_cache_miss_input_usd_per_mtok",
        "deepseek_output_usd_per_mtok",
        "claude_l1_base_input_usd_per_mtok",
        "claude_l1_output_usd_per_mtok",
        "claude_l2_base_input_usd_per_mtok",
        "claude_l2_output_usd_per_mtok",
    ):
        _canonical_decimal(getattr(binding, name))
    for name in (
        "deepseek_models_artifact_sha256",
        "deepseek_pricing_artifact_sha256",
        "deepseek_updates_artifact_sha256",
        "claude_models_artifact_sha256",
        "claude_pricing_artifact_sha256",
        "claude_deprecations_artifact_sha256",
    ):
        _require(_valid_sha256(getattr(binding, name)))
    _require(not binding.deepseek_model_id.casefold().endswith("latest"))
    _require(not binding.claude_l1_model_id.casefold().endswith("latest"))
    _require(not binding.claude_l2_model_id.casefold().endswith("latest"))
    _require(
        binding.claude_l1_max_cost_micro_usd
        == _maximum_cost_micro_usd(
            binding.claude_l1_input_hard_limit_tokens,
            binding.claude_l1_base_input_usd_per_mtok,
            binding.claude_l1_output_hard_limit_tokens,
            binding.claude_l1_output_usd_per_mtok,
        )
    )
    _require(
        binding.claude_l2_max_cost_micro_usd
        == _maximum_cost_micro_usd(
            binding.claude_l2_input_hard_limit_tokens,
            binding.claude_l2_base_input_usd_per_mtok,
            binding.claude_l2_output_hard_limit_tokens,
            binding.claude_l2_output_usd_per_mtok,
        )
    )
    l1_count = (
        binding.shared_l1_l2_daily_logical_review_ceiling
        - binding.l2_daily_logical_review_ceiling
    )
    _require(
        binding.maximum_daily_cost_micro_usd
        == l1_count * binding.claude_l1_max_cost_micro_usd
        + binding.l2_daily_logical_review_ceiling
        * binding.claude_l2_max_cost_micro_usd
    )
    _require(_valid_sha256(binding.binding_sha256))
    _require(
        binding.binding_sha256 == _hash_mapping(_binding_preimage(binding))
    )


@dataclass(frozen=True, slots=True)
class E5ProviderModelPriceBindingV1:
    binding_version: str
    deepseek_model_id: str
    deepseek_input_hard_limit_tokens: int
    deepseek_output_hard_limit_tokens: int
    deepseek_provider_attempts: int
    deepseek_retry_count: int
    deepseek_cache_hit_input_usd_per_mtok: str
    deepseek_cache_miss_input_usd_per_mtok: str
    deepseek_output_usd_per_mtok: str
    deepseek_pre_ga_unpinned_risk_accepted: bool
    claude_l1_model_id: str
    claude_l1_input_hard_limit_tokens: int
    claude_l1_output_hard_limit_tokens: int
    claude_l1_timeout_seconds: int
    claude_l1_provider_attempts: int
    claude_l1_retry_count: int
    claude_l1_base_input_usd_per_mtok: str
    claude_l1_output_usd_per_mtok: str
    claude_l1_max_cost_micro_usd: int
    claude_l2_model_id: str
    claude_l2_input_hard_limit_tokens: int
    claude_l2_output_hard_limit_tokens: int
    claude_l2_timeout_seconds: int
    claude_l2_provider_attempts: int
    claude_l2_retry_count: int
    claude_l2_base_input_usd_per_mtok: str
    claude_l2_output_usd_per_mtok: str
    claude_l2_max_cost_micro_usd: int
    shared_l1_l2_daily_logical_review_ceiling: int
    l2_daily_logical_review_ceiling: int
    maximum_daily_cost_micro_usd: int
    claude_mythos_limited_availability_accepted: bool
    latest_alias_allowed: bool
    cross_provider_substitution_allowed: bool
    malformed_response_prompt_repair_allowed: bool
    stale_result_reuse_allowed: bool
    same_invocation_retry_allowed: bool
    price_artifact_maximum_age_days: int
    deepseek_models_artifact_sha256: str
    deepseek_pricing_artifact_sha256: str
    deepseek_updates_artifact_sha256: str
    claude_models_artifact_sha256: str
    claude_pricing_artifact_sha256: str
    claude_deprecations_artifact_sha256: str
    binding_sha256: str

    def __post_init__(self) -> None:
        try:
            _validate_frozen_binding(self, _FROZEN_BINDING_VALUES)
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_binding_preimage(self),
            "binding_sha256": self.binding_sha256,
        }

    def canonical_binding_json(self) -> str:
        return _canonical_json(_binding_preimage(self))


@dataclass(frozen=True, slots=True)
class E5ProviderModelPriceBindingV2(E5ProviderModelPriceBindingV1):
    def __post_init__(self) -> None:
        try:
            _validate_frozen_binding(self, _FROZEN_BINDING_V2_VALUES)
        except Exception:
            _fail()


def get_owner_frozen_e5_provider_model_price_binding_v1(
) -> E5ProviderModelPriceBindingV1:
    preimage = dict(_FROZEN_BINDING_VALUES)
    return E5ProviderModelPriceBindingV1(
        **preimage,
        binding_sha256=_hash_mapping(preimage),
    )


def get_owner_frozen_e5_provider_model_price_binding_v2(
) -> E5ProviderModelPriceBindingV2:
    preimage = dict(_FROZEN_BINDING_V2_VALUES)
    return E5ProviderModelPriceBindingV2(
        **preimage,
        binding_sha256=_hash_mapping(preimage),
    )


E5_REGISTERED_PROVIDER_MODEL_PRICE_BINDING_SHA256S: Final = (
    get_owner_frozen_e5_provider_model_price_binding_v1().binding_sha256,
    get_owner_frozen_e5_provider_model_price_binding_v2().binding_sha256,
)


def _freeze_value(value: object) -> object:
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, Mapping):
        _require(all(type(key) is str for key in value))
        return tuple(
            (key, _freeze_value(value[key]))
            for key in sorted(value)
        )
    if type(value) in (tuple, list):
        return tuple(_freeze_value(item) for item in value)
    _fail()


def _validate_frozen_value(value: object) -> None:
    if value is None or type(value) in (str, int, bool):
        return
    _require(type(value) is tuple)
    for item in value:
        if (
            type(item) is tuple
            and len(item) == 2
            and type(item[0]) is str
        ):
            _validate_frozen_value(item[1])
        else:
            _validate_frozen_value(item)


def _thaw_value(value: object) -> object:
    if value is None or type(value) in (str, int, bool):
        return value
    _require(type(value) is tuple)
    if value and all(
        type(item) is tuple
        and len(item) == 2
        and type(item[0]) is str
        for item in value
    ):
        return {item[0]: _thaw_value(item[1]) for item in value}
    return [_thaw_value(item) for item in value]


def _freeze_mapping(
    mapping: Mapping[str, object],
    expected_keys: tuple[str, ...],
) -> tuple[tuple[str, object], ...]:
    _require(type(mapping) is dict)
    _require(set(mapping) == set(expected_keys))
    frozen = _freeze_value(mapping)
    _require(type(frozen) is tuple)
    return frozen


def _validate_frozen_mapping(
    value: object,
    expected_keys: tuple[str, ...],
) -> None:
    _require(type(value) is tuple and bool(value))
    _validate_frozen_value(value)
    mapping = _thaw_value(value)
    _require(type(mapping) is dict)
    _require(set(mapping) == set(expected_keys))


def _payload_preimage(
    payload: "E5TechnicalReviewPayloadV1",
) -> dict[str, object]:
    mapping: dict[str, object] = {
        "payload_version": payload.payload_version,
        "provider_binding_sha256": payload.provider_binding_sha256,
        "mode": payload.mode,
        "relevant_timeframes": list(payload.relevant_timeframes),
        "trigger_type": payload.trigger_type,
    }
    for name in _PAYLOAD_MAPPING_KEYS:
        mapping[name] = _thaw_value(getattr(payload, name))
    return {
        "payload_version": mapping["payload_version"],
        "provider_binding_sha256": mapping["provider_binding_sha256"],
        **{
            name: mapping[name]
            for name in E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS
        },
    }


@dataclass(frozen=True, slots=True)
class E5TechnicalReviewPayloadV1:
    payload_version: str
    provider_binding_sha256: str
    mode: str
    relevant_timeframes: tuple[str, ...]
    executable_price: tuple[tuple[str, object], ...]
    exchange_timestamp: tuple[tuple[str, object], ...]
    golden_zone: tuple[tuple[str, object], ...]
    anchors: tuple[tuple[str, object], ...]
    stop_geometry: tuple[tuple[str, object], ...]
    target_geometry: tuple[tuple[str, object], ...]
    net_rr: tuple[tuple[str, object], ...]
    trigger_type: str
    trigger_age: tuple[tuple[str, object], ...]
    lifecycle_state: tuple[tuple[str, object], ...]
    thesis_fingerprint: tuple[tuple[str, object], ...]
    prior_publication_identity: tuple[tuple[str, object], ...]
    prior_history_identity: tuple[tuple[str, object], ...]
    liquidity_evidence: tuple[tuple[str, object], ...]
    volume_evidence: tuple[tuple[str, object], ...]
    open_interest_evidence: tuple[tuple[str, object], ...]
    news_and_contradiction_quality: tuple[tuple[str, object], ...]
    payload_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.payload_version) is str)
            _require(
                self.payload_version == E5_TECHNICAL_REVIEW_PAYLOAD_VERSION
            )
            _require(
                type(self.provider_binding_sha256) is str
                and self.provider_binding_sha256
                in E5_REGISTERED_PROVIDER_MODEL_PRICE_BINDING_SHA256S
            )
            _require(type(self.mode) is str and self.mode in _MODES)
            _require(type(self.relevant_timeframes) is tuple)
            _require(bool(self.relevant_timeframes))
            _require(
                all(
                    type(item) is str and item in _TIMEFRAMES
                    for item in self.relevant_timeframes
                )
            )
            _require(
                len(set(self.relevant_timeframes))
                == len(self.relevant_timeframes)
            )
            _require(type(self.trigger_type) is str)
            _require(bool(self.trigger_type) and self.trigger_type.strip() == self.trigger_type)
            for name, expected_keys in _PAYLOAD_MAPPING_KEYS.items():
                _validate_frozen_mapping(getattr(self, name), expected_keys)
            _require(_valid_sha256(self.payload_sha256))
            _require(
                self.payload_sha256 == _hash_mapping(_payload_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_payload_preimage(self),
            "payload_sha256": self.payload_sha256,
        }

    def canonical_payload_json(self) -> str:
        return _canonical_json(_payload_preimage(self))


def reconstruct_e5_technical_review_payload_v1(
    mapping: Mapping[str, object],
) -> E5TechnicalReviewPayloadV1:
    try:
        expected_keys = frozenset(
            (
                "payload_version",
                "provider_binding_sha256",
                *E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS,
                "payload_sha256",
            )
        )
        _require(type(mapping) is dict)
        _require(frozenset(mapping) == expected_keys)
        _require(type(mapping["relevant_timeframes"]) is list)
        data: dict[str, object] = {
            "payload_version": mapping["payload_version"],
            "provider_binding_sha256": mapping["provider_binding_sha256"],
            "mode": mapping["mode"],
            "relevant_timeframes": tuple(mapping["relevant_timeframes"]),
            "trigger_type": mapping["trigger_type"],
        }
        for name, expected_mapping_keys in _PAYLOAD_MAPPING_KEYS.items():
            data[name] = _freeze_mapping(
                mapping[name],
                expected_mapping_keys,
            )
        return E5TechnicalReviewPayloadV1(
            **data,
            payload_sha256=mapping["payload_sha256"],
        )
    except Exception:
        _fail()


def _validate_mode_execution_bundle(
    value: object,
) -> tuple[
    ModeScanExecutionResultV1,
    tuple[ModeTimeframeExecutionEvidenceV1, ...],
    ModeOiExecutionEvidenceV1,
]:
    _require(type(value) is tuple and len(value) == 3)
    result, timeframe_values, oi = value
    _require(type(result) is ModeScanExecutionResultV1)
    result.__post_init__()
    _require(type(timeframe_values) is tuple and bool(timeframe_values))
    for item in timeframe_values:
        _require(type(item) is ModeTimeframeExecutionEvidenceV1)
        item.__post_init__()
    _require(type(oi) is ModeOiExecutionEvidenceV1)
    oi.__post_init__()
    return result, timeframe_values, oi


def _validate_news_risk(value: object) -> NewsRiskObjectV1:
    _require(type(value) is NewsRiskObjectV1)
    reconstructed = NewsRiskObjectV1(
        **{field.name: getattr(value, field.name) for field in fields(value)}
    )
    _require(reconstructed == value)
    return value


def _canonical_number(value: object) -> str | None:
    if value is None:
        return None
    _require(type(value) in (int, float) and type(value) is not bool)
    if type(value) is float:
        _require(value == value and value not in (float("inf"), float("-inf")))
    parsed = Decimal(str(value))
    _require(parsed.is_finite())
    text = format(parsed, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _ordered_timeframes(profile: ModeProfileV1) -> tuple[str, ...]:
    ordered = (
        *profile.context_timeframes,
        *profile.optional_context_timeframes,
        profile.bias_timeframe,
        profile.structure_timeframe,
        profile.trigger_timeframe,
    )
    return tuple(dict.fromkeys(ordered))


def build_e5_technical_review_payload_v1(
    *,
    actionable_admission: E3ActionableAdmissionResultV1,
    candidate_authority: ProductionCandidateAuthorityV1,
    duplicate_protection_result: E4DuplicateProtectionCompositionResultV1,
    thesis_history: E4ThesisHistoryV1,
    mode_profile: ModeProfileV1,
    mode_execution_evidence: tuple[
        ModeScanExecutionResultV1,
        tuple[ModeTimeframeExecutionEvidenceV1, ...],
        ModeOiExecutionEvidenceV1,
    ],
    normalized_news_events: tuple[NormalizedNewsEventV1, ...],
    news_risk_object: NewsRiskObjectV1,
) -> E5TechnicalReviewPayloadV1:
    try:
        _require(type(actionable_admission) is E3ActionableAdmissionResultV1)
        actionable_admission.__post_init__()
        _require(actionable_admission.actionable_admitted is True)
        _require(type(candidate_authority) is ProductionCandidateAuthorityV1)
        candidate_authority.__post_init__()
        _require(
            type(duplicate_protection_result)
            is E4DuplicateProtectionCompositionResultV1
        )
        duplicate_protection_result.__post_init__()
        _require(duplicate_protection_result.actionable_admitted is True)
        _require(duplicate_protection_result.publication_intent_allowed is True)
        _require(
            duplicate_protection_result.actionable_admission_sha256
            == actionable_admission.actionable_admission_sha256
        )
        fingerprint = duplicate_protection_result.fingerprint
        guard = duplicate_protection_result.publication_guard_result
        _require(type(fingerprint) is E4ThesisFingerprintV1)
        fingerprint.__post_init__()
        _require(guard is not None)
        guard.__post_init__()
        _require(guard.candidate_identity_sha256 == fingerprint.identity_sha256)
        rebuilt = build_e4_thesis_fingerprint(
            geometry=actionable_admission.geometry,
            structural_targets=actionable_admission.structural_targets,
            executable_price_snapshot=(
                actionable_admission.executable_price_snapshot
            ),
            mode_trigger_evidence=actionable_admission.mode_trigger_evidence,
            production_candidate_authority=candidate_authority,
        )
        _require(rebuilt.to_mapping() == fingerprint.to_mapping())

        _require(type(thesis_history) is E4ThesisHistoryV1)
        thesis_history.__post_init__()
        _require(
            thesis_history.current_identity_sha256
            == fingerprint.identity_sha256
        )
        _require(type(mode_profile) is ModeProfileV1)
        mode_profile.__post_init__()
        geometry = actionable_admission.geometry
        targets = actionable_admission.structural_targets
        snapshot = actionable_admission.executable_price_snapshot
        admission = actionable_admission.price_zone_admission
        trigger = actionable_admission.mode_trigger_evidence
        lifecycle = actionable_admission.setup_lifecycle
        _require(mode_profile == get_mode_profile(geometry.mode))
        _require(mode_profile.policy_version == geometry.mode_profile_version)
        _require(mode_profile.structure_timeframe == geometry.structure_timeframe)
        _require(mode_profile.trigger_timeframe == trigger.trigger_timeframe)
        _require(mode_profile.trigger_rule == trigger.trigger_rule)

        execution, timeframe_evidence, oi_evidence = (
            _validate_mode_execution_bundle(mode_execution_evidence)
        )
        _require(execution.mode == geometry.mode)
        _require(execution.mode_lineage_sha256 == geometry.mode_lineage_sha256)
        _require(execution.observed_at == trigger.evaluation_timestamp)
        candidates = tuple(
            item
            for item in execution.candidates
            if normalize_pair(item.symbol) == fingerprint.canonical_pair
        )
        _require(len(candidates) == 1)
        candidate = candidates[0]
        _require(candidate.mode == geometry.mode)
        _require(candidate.mode_lineage_sha256 == geometry.mode_lineage_sha256)
        _require(candidate.reference_candle_at == trigger.trigger_candle_close_at)
        outcomes = tuple(
            item
            for item in execution.outcomes
            if normalize_pair(item.canonical_symbol) == fingerprint.canonical_pair
        )
        _require(len(outcomes) == 1)
        outcome = outcomes[0]
        _require(outcome.candidate_row is not None)
        _require(outcome.candidate_row.candidate_id == candidate.candidate_id)
        _require(outcome.evaluator_payload_sha256 == candidate.payload_sha256)
        _require(outcome.oi_evidence_sha256 == oi_evidence.evidence_sha256)

        relevant_timeframes = _ordered_timeframes(mode_profile)
        evidence_by_timeframe = {
            item.timeframe: item for item in timeframe_evidence
        }
        _require(len(evidence_by_timeframe) == len(timeframe_evidence))
        _require(set(evidence_by_timeframe) == set(relevant_timeframes))
        for item in timeframe_evidence:
            _require(item.mode == geometry.mode)
            _require(item.mode_lineage_sha256 == geometry.mode_lineage_sha256)
            _require(normalize_pair(item.canonical_symbol) == fingerprint.canonical_pair)
            _require(item.observed_at == execution.observed_at)
        _require(
            evidence_by_timeframe[trigger.trigger_timeframe].closed_candle_close_at
            == trigger.trigger_candle_close_at
        )
        _require(
            outcome.timeframe_evidence_sha256s
            == tuple(item.evidence_sha256 for item in timeframe_evidence)
        )
        _require(oi_evidence.mode == geometry.mode)
        _require(oi_evidence.mode_lineage_sha256 == geometry.mode_lineage_sha256)
        _require(normalize_pair(oi_evidence.canonical_symbol) == fingerprint.canonical_pair)
        _require(oi_evidence.observed_at == execution.observed_at)

        _require(type(normalized_news_events) is tuple)
        _require(bool(normalized_news_events))
        normalized: list[NormalizedNewsEventV1] = []
        for event in normalized_news_events:
            _require(type(event) is NormalizedNewsEventV1)
            event_mapping = event.to_mapping()
            event_mapping["publication_timestamp_utc"] = (
                event.publication_timestamp_utc
            )
            event_mapping["point_in_time_timestamp_utc"] = (
                event.point_in_time_timestamp_utc
            )
            reconstructed_event = NormalizedNewsEventV1(**event_mapping)
            _require(reconstructed_event == event)
            normalized.append(event)
        normalized.sort(
            key=lambda item: (
                item.point_in_time_timestamp_utc,
                item.event_snapshot_id,
            )
        )
        _require(
            len({item.event_snapshot_id for item in normalized})
            == len(normalized)
        )
        base_asset = fingerprint.canonical_pair.split("/", 1)[0]
        _require(
            all(item.normalized_primary_subject == base_asset for item in normalized)
        )
        risk = _validate_news_risk(news_risk_object)
        _require(risk.event_snapshot_id == normalized[-1].event_snapshot_id)
        _require(risk.event_snapshot_id in risk.evidence_refs)

        evaluator_payload = candidate.payload_copy()
        binding = get_owner_frozen_e5_provider_model_price_binding_v2()
        latest_event = thesis_history.events[-1]
        mappings: dict[str, tuple[tuple[str, object], ...]] = {
            "executable_price": _freeze_mapping(
                {
                    "admission_sha256": admission.admission_sha256,
                    "executable_price_source": admission.executable_price_source,
                    "executable_price_tick": admission.executable_price_tick,
                    "snapshot_sha256": snapshot.snapshot_sha256,
                },
                _PAYLOAD_MAPPING_KEYS["executable_price"],
            ),
            "exchange_timestamp": _freeze_mapping(
                {
                    "exchange_timestamp": snapshot.exchange_timestamp,
                    "quote_generation_id": snapshot.quote_generation_id,
                    "snapshot_sha256": snapshot.snapshot_sha256,
                    "venue": snapshot.venue,
                },
                _PAYLOAD_MAPPING_KEYS["exchange_timestamp"],
            ),
            "golden_zone": _freeze_mapping(
                {
                    "geometry_sha256": geometry.geometry_sha256,
                    "high_tick": geometry.golden_zone_high_tick,
                    "low_tick": geometry.golden_zone_low_tick,
                },
                _PAYLOAD_MAPPING_KEYS["golden_zone"],
            ),
            "anchors": _freeze_mapping(
                {
                    "anchor_high_at": geometry.anchor_high_at,
                    "anchor_high_tick": geometry.anchor_high_tick,
                    "anchor_low_at": geometry.anchor_low_at,
                    "anchor_low_tick": geometry.anchor_low_tick,
                },
                _PAYLOAD_MAPPING_KEYS["anchors"],
            ),
            "stop_geometry": _freeze_mapping(
                {
                    "risk_distance_ticks": targets.risk_distance_ticks,
                    "stop_loss_tick": targets.stop_loss_tick,
                    "worst_entry_tick": targets.worst_entry_tick,
                },
                _PAYLOAD_MAPPING_KEYS["stop_geometry"],
            ),
            "target_geometry": _freeze_mapping(
                {
                    "targets_sha256": targets.targets_sha256,
                    "tp1": {
                        "destination_id": targets.tp1_destination_id,
                        "destination_kind": targets.tp1_destination_kind,
                        "tick": targets.tp1_tick,
                    },
                    "tp2": {
                        "destination_id": targets.tp2_destination_id,
                        "destination_kind": targets.tp2_destination_kind,
                        "tick": targets.tp2_tick,
                    },
                },
                _PAYLOAD_MAPPING_KEYS["target_geometry"],
            ),
            "net_rr": _freeze_mapping(
                {
                    "tp1_rr_denominator": targets.tp1_rr_denominator,
                    "tp1_rr_numerator": targets.tp1_rr_numerator,
                    "tp2_rr_denominator": targets.tp2_rr_denominator,
                    "tp2_rr_numerator": targets.tp2_rr_numerator,
                },
                _PAYLOAD_MAPPING_KEYS["net_rr"],
            ),
            "trigger_age": _freeze_mapping(
                {
                    "evaluation_timestamp": trigger.evaluation_timestamp,
                    "maximum_trigger_age_seconds": (
                        trigger.maximum_trigger_age_seconds
                    ),
                    "trigger_age_seconds": trigger.trigger_age_seconds,
                    "trigger_candle_close_at": trigger.trigger_candle_close_at,
                    "trigger_evidence_sha256": trigger.trigger_evidence_sha256,
                    "trigger_fresh": trigger.trigger_fresh,
                },
                _PAYLOAD_MAPPING_KEYS["trigger_age"],
            ),
            "lifecycle_state": _freeze_mapping(
                {
                    "lifecycle_sha256": lifecycle.lifecycle_sha256,
                    "resulting_state": lifecycle.resulting_state,
                },
                _PAYLOAD_MAPPING_KEYS["lifecycle_state"],
            ),
            "thesis_fingerprint": _freeze_mapping(
                {
                    "fingerprint_version": fingerprint.fingerprint_version,
                    "identity": fingerprint.to_identity_mapping(),
                    "identity_sha256": fingerprint.identity_sha256,
                },
                _PAYLOAD_MAPPING_KEYS["thesis_fingerprint"],
            ),
            "prior_publication_identity": _freeze_mapping(
                {
                    "current_identity_sha256": (
                        thesis_history.current_identity_sha256
                    ),
                    "current_publication_succeeded": (
                        thesis_history.current_publication_succeeded
                    ),
                    "current_state": thesis_history.current_state,
                    "latest_event_sha256": latest_event.event_sha256,
                },
                _PAYLOAD_MAPPING_KEYS["prior_publication_identity"],
            ),
            "prior_history_identity": _freeze_mapping(
                {
                    "fingerprint_history": thesis_history.fingerprint_history,
                    "history_sha256": thesis_history.history_sha256,
                    "revision": thesis_history.revision,
                },
                _PAYLOAD_MAPPING_KEYS["prior_history_identity"],
            ),
            "liquidity_evidence": _freeze_mapping(
                {
                    "targets_sha256": targets.targets_sha256,
                    "tp1_destination_id": targets.tp1_destination_id,
                    "tp1_destination_kind": targets.tp1_destination_kind,
                    "tp2_destination_id": targets.tp2_destination_id,
                    "tp2_destination_kind": targets.tp2_destination_kind,
                },
                _PAYLOAD_MAPPING_KEYS["liquidity_evidence"],
            ),
            "volume_evidence": _freeze_mapping(
                {
                    "evaluator_payload_sha256": candidate.payload_sha256,
                    "mode_execution_sha256": execution.execution_sha256,
                    "volume_ratio": _canonical_number(
                        evaluator_payload["volume_ratio"]
                    ),
                    "volume_v2_status": evaluator_payload["volume_v2_status"],
                },
                _PAYLOAD_MAPPING_KEYS["volume_evidence"],
            ),
            "open_interest_evidence": _freeze_mapping(
                {
                    "evidence_sha256": oi_evidence.evidence_sha256,
                    "newest_age_seconds": oi_evidence.newest_age_seconds,
                    "newest_close_at": oi_evidence.newest_close_at,
                    "observation_count": oi_evidence.observation_count,
                    "observations": tuple(
                        {
                            "close_time": item.close_time,
                            "open_interest": _canonical_number(
                                item.open_interest
                            ),
                        }
                        for item in oi_evidence.observations
                    ),
                    "observations_sha256": oi_evidence.observations_sha256,
                    "observed_at": oi_evidence.observed_at,
                    "period": oi_evidence.period,
                },
                _PAYLOAD_MAPPING_KEYS["open_interest_evidence"],
            ),
            "news_and_contradiction_quality": _freeze_mapping(
                {
                    "evidence_refs": risk.evidence_refs,
                    "event_snapshot_ids": tuple(
                        item.event_snapshot_id for item in normalized
                    ),
                    "event_version_ids": tuple(
                        item.event_version_id for item in normalized
                    ),
                    "final_contradiction_state": (
                        risk.final_contradiction_state
                    ),
                    "final_evidence_state": risk.final_evidence_state,
                    "final_material_risk_state": (
                        risk.final_material_risk_state
                    ),
                    "final_source_state": risk.final_source_state,
                    "news_risk_object_id": risk.news_risk_object_id,
                    "reason_codes": risk.reason_codes,
                    "risk_classification": risk.risk_classification,
                },
                _PAYLOAD_MAPPING_KEYS["news_and_contradiction_quality"],
            ),
        }
        data: dict[str, object] = {
            "payload_version": E5_TECHNICAL_REVIEW_PAYLOAD_VERSION,
            "provider_binding_sha256": binding.binding_sha256,
            "mode": geometry.mode,
            "relevant_timeframes": relevant_timeframes,
            **mappings,
            "trigger_type": trigger.trigger_rule,
        }
        temporary = object.__new__(E5TechnicalReviewPayloadV1)
        for name, value in data.items():
            object.__setattr__(temporary, name, value)
        preimage = _payload_preimage(temporary)
        return E5TechnicalReviewPayloadV1(
            **data,
            payload_sha256=_hash_mapping(preimage),
        )
    except Exception:
        _fail()


def _preflight_preimage(
    result: "E5TechnicalReviewTokenPreflightResultV1",
) -> dict[str, object]:
    return {
        field.name: getattr(result, field.name)
        for field in fields(E5TechnicalReviewTokenPreflightResultV1)
        if field.name != "preflight_sha256"
    }


@dataclass(frozen=True, slots=True)
class E5TechnicalReviewTokenPreflightResultV1:
    preflight_version: str
    payload_sha256: str
    model_id: str
    measured_input_tokens: int
    requested_output_tokens: int
    input_hard_limit_tokens: int
    output_hard_limit_tokens: int
    within_limits: bool
    decision_code: str
    preflight_sha256: str

    def __post_init__(self) -> None:
        try:
            _require(type(self.preflight_version) is str)
            _require(
                self.preflight_version
                == E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_VERSION
            )
            _require(_valid_sha256(self.payload_sha256))
            binding = get_owner_frozen_e5_provider_model_price_binding_v2()
            _require(self.model_id == binding.deepseek_model_id)
            for value in (
                self.measured_input_tokens,
                self.requested_output_tokens,
                self.input_hard_limit_tokens,
                self.output_hard_limit_tokens,
            ):
                _require(type(value) is int and value >= 0)
            _require(
                self.input_hard_limit_tokens
                == binding.deepseek_input_hard_limit_tokens
            )
            _require(
                self.output_hard_limit_tokens
                == binding.deepseek_output_hard_limit_tokens
            )
            if self.measured_input_tokens > self.input_hard_limit_tokens:
                expected = (False, HOLD_INPUT_TOKEN_LIMIT)
            elif self.requested_output_tokens > self.output_hard_limit_tokens:
                expected = (False, HOLD_OUTPUT_TOKEN_LIMIT)
            else:
                expected = (True, PASS_TOKEN_BUDGET)
            _require(type(self.within_limits) is bool)
            _require((self.within_limits, self.decision_code) == expected)
            _require(self.decision_code in E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_DECISION_CODES)
            _require(_valid_sha256(self.preflight_sha256))
            _require(
                self.preflight_sha256
                == _hash_mapping(_preflight_preimage(self))
            )
        except Exception:
            _fail()

    def to_mapping(self) -> dict[str, object]:
        return {
            **_preflight_preimage(self),
            "preflight_sha256": self.preflight_sha256,
        }

    def canonical_preflight_json(self) -> str:
        return _canonical_json(_preflight_preimage(self))


def preflight_e5_technical_review_payload_v1(
    *,
    payload: E5TechnicalReviewPayloadV1,
    measured_input_tokens: int,
    requested_output_tokens: int,
) -> E5TechnicalReviewTokenPreflightResultV1:
    try:
        _require(type(payload) is E5TechnicalReviewPayloadV1)
        payload.__post_init__()
        binding = get_owner_frozen_e5_provider_model_price_binding_v2()
        _require(payload.provider_binding_sha256 == binding.binding_sha256)
        _require(type(measured_input_tokens) is int and measured_input_tokens >= 0)
        _require(type(requested_output_tokens) is int and requested_output_tokens >= 0)
        if measured_input_tokens > binding.deepseek_input_hard_limit_tokens:
            within_limits = False
            decision_code = HOLD_INPUT_TOKEN_LIMIT
        elif requested_output_tokens > binding.deepseek_output_hard_limit_tokens:
            within_limits = False
            decision_code = HOLD_OUTPUT_TOKEN_LIMIT
        else:
            within_limits = True
            decision_code = PASS_TOKEN_BUDGET
        data: dict[str, object] = {
            "preflight_version": E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_VERSION,
            "payload_sha256": payload.payload_sha256,
            "model_id": binding.deepseek_model_id,
            "measured_input_tokens": measured_input_tokens,
            "requested_output_tokens": requested_output_tokens,
            "input_hard_limit_tokens": binding.deepseek_input_hard_limit_tokens,
            "output_hard_limit_tokens": binding.deepseek_output_hard_limit_tokens,
            "within_limits": within_limits,
            "decision_code": decision_code,
        }
        temporary = object.__new__(E5TechnicalReviewTokenPreflightResultV1)
        for name, value in data.items():
            object.__setattr__(temporary, name, value)
        return E5TechnicalReviewTokenPreflightResultV1(
            **data,
            preflight_sha256=_hash_mapping(_preflight_preimage(temporary)),
        )
    except Exception:
        _fail()


__all__ = (
    "E5_PROVIDER_MODEL_PRICE_BINDING_VERSION",
    "E5_PROVIDER_MODEL_PRICE_BINDING_V2_VERSION",
    "E5_TECHNICAL_REVIEW_PAYLOAD_VERSION",
    "E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_VERSION",
    "E5_TECHNICAL_REVIEW_EVIDENCE_FIELDS",
    "PASS_TOKEN_BUDGET",
    "HOLD_INPUT_TOKEN_LIMIT",
    "HOLD_OUTPUT_TOKEN_LIMIT",
    "E5_TECHNICAL_REVIEW_TOKEN_PREFLIGHT_DECISION_CODES",
    "E5_REGISTERED_PROVIDER_MODEL_PRICE_BINDING_SHA256S",
    "E5ProviderModelPriceBindingV1",
    "E5ProviderModelPriceBindingV2",
    "E5TechnicalReviewPayloadV1",
    "E5TechnicalReviewTokenPreflightResultV1",
    "get_owner_frozen_e5_provider_model_price_binding_v1",
    "get_owner_frozen_e5_provider_model_price_binding_v2",
    "build_e5_technical_review_payload_v1",
    "reconstruct_e5_technical_review_payload_v1",
    "preflight_e5_technical_review_payload_v1",
)
