"""Immutable, non-secret activation metadata for the E6 operational package."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
import posixpath
import re
from typing import Final


E6_ACTIVATION_CONFIGURATION_SCHEMA_V1: Final = (
    "e6-activation-configuration-v1"
)
E6_SERVICE_USER_V1: Final = "ai-crypto-signal-agent"
E6_SERVICE_GROUP_V1: Final = "ai-crypto-signal-agent"

_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_EXPECTED_KEYS = (
    "E6_ACTIVATION_SCHEMA_VERSION",
    "E6_RELEASE_COMMIT",
    "E6_RELEASE_TREE",
    "E6_TRUSTED_CHECKPOINT_COMMIT",
    "E6_RELEASE_ROOT",
    "E6_RELEASE_REFERENCE_PATH",
    "E6_CREDENTIAL_METADATA_PATH",
    "E6_OWNER_CONTROL_STATE_PATH",
    "E6_SERVICE_USER",
    "E6_SERVICE_GROUP",
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
_BOOLEAN_KEYS = _EXPECTED_KEYS[10:18] + _EXPECTED_KEYS[19:]
_ERROR_CODES = frozenset(
    {
        "ACTIVATION_CONFIGURATION_TYPE_INVALID",
        "ACTIVATION_CONFIGURATION_KEYS_INVALID",
        "ACTIVATION_CONFIGURATION_VALUE_INVALID",
        "ACTIVATION_CONFIGURATION_SCHEMA_INVALID",
        "ACTIVATION_CONFIGURATION_IDENTITY_INVALID",
        "ACTIVATION_CONFIGURATION_PATH_INVALID",
        "ACTIVATION_CONFIGURATION_SERVICE_IDENTITY_INVALID",
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


def _absolute_metadata_path(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or "\x00" in value
        or "\n" in value
        or "\r" in value
        or not value.startswith("/")
        or value == "/"
        or posixpath.normpath(value) != value
    ):
        _fail("ACTIVATION_CONFIGURATION_PATH_INVALID")
    return value


def _boolean(value: object) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    _fail("ACTIVATION_CONFIGURATION_BOOLEAN_INVALID")


@dataclass(frozen=True, slots=True)
class E6ActivationConfigurationV1:
    """Serializable activation metadata; every effect gate defaults closed."""

    schema_version: str
    release_commit: str
    release_tree: str
    trusted_checkpoint_commit: str
    release_root: str
    release_reference_path: str
    credential_metadata_path: str
    owner_control_state_path: str
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
        for identity in (
            self.release_commit,
            self.release_tree,
            self.trusted_checkpoint_commit,
        ):
            if type(identity) is not str or _SHA1.fullmatch(identity) is None:
                _fail("ACTIVATION_CONFIGURATION_IDENTITY_INVALID")
        release_root = _absolute_metadata_path(self.release_root)
        if posixpath.basename(release_root) != self.release_commit:
            _fail("ACTIVATION_CONFIGURATION_IDENTITY_INVALID")
        for path in (
            self.release_reference_path,
            self.credential_metadata_path,
            self.owner_control_state_path,
        ):
            _absolute_metadata_path(path)
        if (
            self.service_user != E6_SERVICE_USER_V1
            or self.service_group != E6_SERVICE_GROUP_V1
        ):
            _fail("ACTIVATION_CONFIGURATION_SERVICE_IDENTITY_INVALID")
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
        if type(self.automatic_retry_count) is not int:
            _fail("ACTIVATION_CONFIGURATION_RETRY_INVALID")
        if self.automatic_retry_count != 0:
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

    def to_mapping(self) -> dict[str, object]:
        """Return deterministic plain data without reading any external state."""

        return {field.name: getattr(self, field.name) for field in fields(self)}


def load_e6_activation_configuration_v1(
    configuration: Mapping[str, str],
) -> E6ActivationConfigurationV1:
    """Validate one exact injected metadata mapping without reading secrets."""

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
    parsed_booleans = {key: _boolean(values[key]) for key in _BOOLEAN_KEYS}
    if values["E6_AUTOMATIC_RETRY_COUNT"] != "0":
        _fail("ACTIVATION_CONFIGURATION_RETRY_INVALID")
    return E6ActivationConfigurationV1(
        schema_version=values["E6_ACTIVATION_SCHEMA_VERSION"],
        release_commit=values["E6_RELEASE_COMMIT"],
        release_tree=values["E6_RELEASE_TREE"],
        trusted_checkpoint_commit=values["E6_TRUSTED_CHECKPOINT_COMMIT"],
        release_root=values["E6_RELEASE_ROOT"],
        release_reference_path=values["E6_RELEASE_REFERENCE_PATH"],
        credential_metadata_path=values["E6_CREDENTIAL_METADATA_PATH"],
        owner_control_state_path=values["E6_OWNER_CONTROL_STATE_PATH"],
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
