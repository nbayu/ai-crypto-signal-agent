"""Immutable, profile-closed nonsecret activation metadata for E6."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
import re
from typing import Final

from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
)
from engine.e6_deployment_state_binding_v1 import (
    E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
    E6_SERVICE_GROUP_V1,
    E6_SERVICE_USER_V1,
    E6DeploymentStateBindingErrorV1,
    E6DeploymentStateBindingV1,
    build_e6_deployment_state_binding_v1,
)


E6_ACTIVATION_CONFIGURATION_SCHEMA_V1: Final = (
    "e6-activation-configuration-v2"
)

_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_EXPECTED_KEYS = (
    "E6_ACTIVATION_SCHEMA_VERSION",
    "E6_DEPLOYMENT_BINDING_VERSION",
    "E6_DEPLOYMENT_PROFILE",
    "E6_RELEASE_COMMIT",
    "E6_RELEASE_TREE",
    "E6_TRUSTED_CHECKPOINT_COMMIT",
    "E6_RELEASE_ROOT",
    "E6_SERVICE_UNIT",
    "E6_TIMER_UNIT",
    "E6_STATE_ROOT",
    "E6_OWNER_STATE_ROOT",
    "E6_LEDGER_ROOT",
    "E6_ACTIVE_SIGNAL_LEDGER_PATH",
    "E6_OWNER_CONTROL_STATE_PATH",
    "E6_PUBLICATION_ROOT",
    "E6_OPERATIONAL_ARTIFACT_ROOT",
    "E6_RUNTIME_ROOT",
    "E6_RUNTIME_LOCK_PATH",
    "E6_CACHE_ROOT",
    "E6_LOG_POLICY",
    "E6_CONTROL_ROOT",
    "E6_RELEASE_REFERENCE_PATH",
    "E6_ROLLBACK_REFERENCE_PATH",
    "E6_ACCEPTED_RELEASE_MARKER_PATH",
    "E6_KILL_SWITCH_PATH",
    "E6_CONFIGURATION_ROOT",
    "E6_CREDENTIAL_METADATA_PATH",
    "E6_ACTIVATION_CONFIGURATION_PATH",
    "E6_SERVICE_USER",
    "E6_SERVICE_GROUP",
    "E6_PROVIDER_BINDING_VERSION",
    "E6_PROVIDER_BINDING_SHA256",
    "E6_RUNTIME_ENABLED",
    "E6_PROVIDER_ENABLED",
    "E6_ACTIVATION_GATE",
    "E6_WORKLOAD_GATE",
    "E6_CREDENTIAL_GATE",
    "E6_NETWORK_GATE",
    "E6_PUBLICATION_GATE",
    "E6_TELEGRAM_PUBLICATION_GATE",
    "E6_AUTOMATIC_RETRY_COUNT",
    "E6_PROVIDER_SUBSTITUTION_ENABLED",
    "E6_PROMPT_REPAIR_ENABLED",
    "E6_STALE_REVIEW_REUSE_ENABLED",
    "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED",
)
_BOOLEAN_KEYS = (
    "E6_RUNTIME_ENABLED",
    "E6_PROVIDER_ENABLED",
    "E6_ACTIVATION_GATE",
    "E6_WORKLOAD_GATE",
    "E6_CREDENTIAL_GATE",
    "E6_NETWORK_GATE",
    "E6_PUBLICATION_GATE",
    "E6_TELEGRAM_PUBLICATION_GATE",
    "E6_PROVIDER_SUBSTITUTION_ENABLED",
    "E6_PROMPT_REPAIR_ENABLED",
    "E6_STALE_REVIEW_REUSE_ENABLED",
    "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED",
)
_BINDING_KEY_TO_FIELD = (
    ("E6_DEPLOYMENT_BINDING_VERSION", "binding_version"),
    ("E6_DEPLOYMENT_PROFILE", "deployment_profile"),
    ("E6_RELEASE_COMMIT", "release_commit"),
    ("E6_RELEASE_ROOT", "release_root"),
    ("E6_SERVICE_UNIT", "service_unit"),
    ("E6_TIMER_UNIT", "timer_unit"),
    ("E6_STATE_ROOT", "state_root"),
    ("E6_OWNER_STATE_ROOT", "owner_state_root"),
    ("E6_LEDGER_ROOT", "ledger_root"),
    ("E6_ACTIVE_SIGNAL_LEDGER_PATH", "active_ledger_path"),
    ("E6_OWNER_CONTROL_STATE_PATH", "owner_state_path"),
    ("E6_PUBLICATION_ROOT", "publication_root"),
    ("E6_OPERATIONAL_ARTIFACT_ROOT", "operational_artifact_root"),
    ("E6_RUNTIME_ROOT", "runtime_root"),
    ("E6_RUNTIME_LOCK_PATH", "runtime_lock"),
    ("E6_CACHE_ROOT", "cache_root"),
    ("E6_LOG_POLICY", "log_policy"),
    ("E6_CONTROL_ROOT", "control_root"),
    ("E6_RELEASE_REFERENCE_PATH", "install_pointer"),
    ("E6_ROLLBACK_REFERENCE_PATH", "rollback_pointer"),
    ("E6_ACCEPTED_RELEASE_MARKER_PATH", "accepted_marker"),
    ("E6_KILL_SWITCH_PATH", "kill_switch"),
    ("E6_CONFIGURATION_ROOT", "configuration_root"),
    ("E6_CREDENTIAL_METADATA_PATH", "credential_metadata_path"),
    ("E6_ACTIVATION_CONFIGURATION_PATH", "activation_configuration_path"),
    ("E6_SERVICE_USER", "service_user"),
    ("E6_SERVICE_GROUP", "service_group"),
)
_ERROR_CODES = frozenset(
    {
        "ACTIVATION_CONFIGURATION_TYPE_INVALID",
        "ACTIVATION_CONFIGURATION_KEYS_INVALID",
        "ACTIVATION_CONFIGURATION_VALUE_INVALID",
        "ACTIVATION_CONFIGURATION_SCHEMA_INVALID",
        "ACTIVATION_CONFIGURATION_IDENTITY_INVALID",
        "ACTIVATION_CONFIGURATION_BINDING_INVALID",
        "ACTIVATION_CONFIGURATION_SERVICE_IDENTITY_INVALID",
        "ACTIVATION_CONFIGURATION_PROVIDER_BINDING_INVALID",
        "ACTIVATION_CONFIGURATION_BOOLEAN_INVALID",
        "ACTIVATION_CONFIGURATION_RETRY_INVALID",
        "ACTIVATION_CONFIGURATION_SAFETY_INVARIANT_INVALID",
    }
)


class E6ActivationConfigurationErrorV1(ValueError):
    """Fixed-code failure that never renders supplied configuration values."""

    def __init__(self, code: str) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("INVALID_E6_ACTIVATION_CONFIGURATION_ERROR_CODE")
        self.code = code
        super().__init__(code)

    def __repr__(self) -> str:
        return f"E6ActivationConfigurationErrorV1({self.code!r})"


def _fail(code: str) -> None:
    raise E6ActivationConfigurationErrorV1(code) from None


def _boolean(value: object) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    _fail("ACTIVATION_CONFIGURATION_BOOLEAN_INVALID")


@dataclass(frozen=True, slots=True)
class E6ActivationConfigurationV1:
    """One immutable deployment binding plus independently closed effect gates."""

    schema_version: str
    deployment_binding: E6DeploymentStateBindingV1
    release_tree: str
    trusted_checkpoint_commit: str
    provider_binding_version: str
    provider_binding_sha256: str
    service_user: str
    service_group: str
    e6_runtime_enabled: bool = False
    provider_enabled: bool = False
    activation_gate: bool = False
    workload_gate: bool = False
    credential_gate: bool = False
    network_gate: bool = False
    publication_gate: bool = False
    telegram_publication_gate: bool = False
    automatic_retry_count: int = 0
    provider_substitution_enabled: bool = False
    prompt_repair_enabled: bool = False
    stale_review_reuse_enabled: bool = False
    automated_exchange_trading_enabled: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != E6_ACTIVATION_CONFIGURATION_SCHEMA_V1:
            _fail("ACTIVATION_CONFIGURATION_SCHEMA_INVALID")
        if type(self.deployment_binding) is not E6DeploymentStateBindingV1:
            _fail("ACTIVATION_CONFIGURATION_BINDING_INVALID")
        try:
            self.deployment_binding.__post_init__()
        except Exception:
            _fail("ACTIVATION_CONFIGURATION_BINDING_INVALID")
        for identity in (self.release_tree, self.trusted_checkpoint_commit):
            if type(identity) is not str or _SHA1.fullmatch(identity) is None:
                _fail("ACTIVATION_CONFIGURATION_IDENTITY_INVALID")
        if (
            self.service_user != E6_SERVICE_USER_V1
            or self.service_group != E6_SERVICE_GROUP_V1
            or self.service_user != self.deployment_binding.service_user
            or self.service_group != self.deployment_binding.service_group
        ):
            _fail("ACTIVATION_CONFIGURATION_SERVICE_IDENTITY_INVALID")
        if (
            self.provider_binding_version
            != E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION
            or self.provider_binding_sha256
            != E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256
        ):
            _fail("ACTIVATION_CONFIGURATION_PROVIDER_BINDING_INVALID")
        for name in (
            "e6_runtime_enabled",
            "provider_enabled",
            "activation_gate",
            "workload_gate",
            "credential_gate",
            "network_gate",
            "publication_gate",
            "telegram_publication_gate",
            "provider_substitution_enabled",
            "prompt_repair_enabled",
            "stale_review_reuse_enabled",
            "automated_exchange_trading_enabled",
        ):
            if type(getattr(self, name)) is not bool:
                _fail("ACTIVATION_CONFIGURATION_BOOLEAN_INVALID")
        if type(self.automatic_retry_count) is not int or self.automatic_retry_count != 0:
            _fail("ACTIVATION_CONFIGURATION_RETRY_INVALID")
        if any(
            (
                self.provider_substitution_enabled,
                self.prompt_repair_enabled,
                self.stale_review_reuse_enabled,
                self.automated_exchange_trading_enabled,
            )
        ):
            _fail("ACTIVATION_CONFIGURATION_SAFETY_INVARIANT_INVALID")

    @property
    def release_commit(self) -> str:
        return self.deployment_binding.release_commit

    @property
    def release_root(self) -> str:
        return self.deployment_binding.release_root

    @property
    def release_reference_path(self) -> str:
        return self.deployment_binding.install_pointer

    @property
    def credential_metadata_path(self) -> str:
        return self.deployment_binding.credential_metadata_path

    @property
    def owner_control_state_path(self) -> str:
        return self.deployment_binding.owner_state_path

    def to_mapping(self) -> dict[str, object]:
        """Return deterministic plain nonsecret data without external reads."""

        result = {field.name: getattr(self, field.name) for field in fields(self)}
        result["deployment_binding"] = self.deployment_binding.to_mapping()
        return result


def load_e6_activation_configuration_v1(
    configuration: Mapping[str, str],
) -> E6ActivationConfigurationV1:
    """Derive one binding and reject every detached supplied authority value."""

    if not isinstance(configuration, Mapping):
        _fail("ACTIVATION_CONFIGURATION_TYPE_INVALID")
    try:
        keys = tuple(configuration.keys())
        if (
            any(type(key) is not str for key in keys)
            or len(keys) != len(_EXPECTED_KEYS)
            or set(keys) != set(_EXPECTED_KEYS)
        ):
            _fail("ACTIVATION_CONFIGURATION_KEYS_INVALID")
        values = {key: configuration[key] for key in _EXPECTED_KEYS}
    except E6ActivationConfigurationErrorV1:
        raise
    except Exception:
        _fail("ACTIVATION_CONFIGURATION_TYPE_INVALID")
    if any(
        type(value) is not str
        or not value
        or value != value.strip()
        or "\x00" in value
        or "\n" in value
        or "\r" in value
        for value in values.values()
    ):
        _fail("ACTIVATION_CONFIGURATION_VALUE_INVALID")
    if values["E6_ACTIVATION_SCHEMA_VERSION"] != E6_ACTIVATION_CONFIGURATION_SCHEMA_V1:
        _fail("ACTIVATION_CONFIGURATION_SCHEMA_INVALID")
    try:
        binding = build_e6_deployment_state_binding_v1(
            deployment_profile=values["E6_DEPLOYMENT_PROFILE"],
            release_commit=values["E6_RELEASE_COMMIT"],
        )
    except E6DeploymentStateBindingErrorV1:
        _fail("ACTIVATION_CONFIGURATION_BINDING_INVALID")
    for key, field_name in _BINDING_KEY_TO_FIELD:
        expected = getattr(binding, field_name)
        if hasattr(expected, "value"):
            expected = expected.value
        if values[key] != expected:
            _fail("ACTIVATION_CONFIGURATION_BINDING_INVALID")
    if (
        values["E6_PROVIDER_BINDING_VERSION"]
        != E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION
        or values["E6_PROVIDER_BINDING_SHA256"]
        != E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256
    ):
        _fail("ACTIVATION_CONFIGURATION_PROVIDER_BINDING_INVALID")
    parsed_booleans = {key: _boolean(values[key]) for key in _BOOLEAN_KEYS}
    if values["E6_AUTOMATIC_RETRY_COUNT"] != "0":
        _fail("ACTIVATION_CONFIGURATION_RETRY_INVALID")
    return E6ActivationConfigurationV1(
        schema_version=values["E6_ACTIVATION_SCHEMA_VERSION"],
        deployment_binding=binding,
        release_tree=values["E6_RELEASE_TREE"],
        trusted_checkpoint_commit=values["E6_TRUSTED_CHECKPOINT_COMMIT"],
        provider_binding_version=values["E6_PROVIDER_BINDING_VERSION"],
        provider_binding_sha256=values["E6_PROVIDER_BINDING_SHA256"],
        service_user=values["E6_SERVICE_USER"],
        service_group=values["E6_SERVICE_GROUP"],
        e6_runtime_enabled=parsed_booleans["E6_RUNTIME_ENABLED"],
        provider_enabled=parsed_booleans["E6_PROVIDER_ENABLED"],
        activation_gate=parsed_booleans["E6_ACTIVATION_GATE"],
        workload_gate=parsed_booleans["E6_WORKLOAD_GATE"],
        credential_gate=parsed_booleans["E6_CREDENTIAL_GATE"],
        network_gate=parsed_booleans["E6_NETWORK_GATE"],
        publication_gate=parsed_booleans["E6_PUBLICATION_GATE"],
        telegram_publication_gate=parsed_booleans[
            "E6_TELEGRAM_PUBLICATION_GATE"
        ],
        automatic_retry_count=0,
        provider_substitution_enabled=parsed_booleans[
            "E6_PROVIDER_SUBSTITUTION_ENABLED"
        ],
        prompt_repair_enabled=parsed_booleans["E6_PROMPT_REPAIR_ENABLED"],
        stale_review_reuse_enabled=parsed_booleans[
            "E6_STALE_REVIEW_REUSE_ENABLED"
        ],
        automated_exchange_trading_enabled=parsed_booleans[
            "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED"
        ],
    )


__all__ = (
    "E6_ACTIVATION_CONFIGURATION_SCHEMA_V1",
    "E6ActivationConfigurationErrorV1",
    "E6ActivationConfigurationV1",
    "load_e6_activation_configuration_v1",
)
